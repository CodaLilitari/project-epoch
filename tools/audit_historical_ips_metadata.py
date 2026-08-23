#!/usr/bin/env python3
"""Read-only, payload-free metadata audit for historical IPS patches.

This tool parses IPS records and compares their effective writes with an
optional reference image entirely in memory.  It can report hashes, geometry,
write counts, Project Epoch table/protected-range intersections, and
byte-identical subset relationships.  It never writes a ROM, patched image,
patch, save, state, or output file, and it never serializes patch payload
bytes.

Classic IPS truncate markers are parsed so malformed inputs fail cleanly, but
the audit rejects every truncate-bearing patch.  A size change cannot be
truthfully represented as ordinary address/value writes in the protected-range
and lineage reports this tool promises.

When ``--reference-rom`` is supplied, the CLI accepts only the pinned,
headerless Chrono Trigger US Rev0 image.  The derived target hash is explicitly
a zero-fill IPS projection computed in memory; no target image is emitted.
"""

from __future__ import annotations

import argparse
from array import array
from collections.abc import Iterator, Mapping as MappingABC
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, BinaryIO, Final, Mapping, Sequence

import validate_rom_write_intents as write_guard


SCHEMA: Final = "project-epoch-historical-ips-metadata-audit-v1"
CANONICAL_ROM_SIZE: Final = write_guard.SOURCE_KINDS[
    write_guard.CANONICAL_SOURCE_KIND
][0]
CANONICAL_ROM_SHA256: Final = write_guard.CANONICAL_SOURCE_SHA256
MAX_PATCH_FILE_BYTES: Final = 0x800000
MAX_RECORD_COUNT: Final = 0x10000
MAX_DECLARED_WRITE_BYTES: Final = 0x800000
MAX_PATCH_COUNT: Final = 8
MAX_TOTAL_PATCH_FILE_BYTES: Final = 0x1000000
MAX_TOTAL_DECLARED_WRITE_BYTES: Final = 0x1000000
MAX_TOTAL_EFFECTIVE_WRITE_BYTES: Final = 0x1000000
MAX_RELATION_ADDRESS_VISITS: Final = 0x4000000
MAX_IPS_SIZE: Final = 0x1000000
IPS_HEADER: Final = b"PATCH"
IPS_EOF: Final = b"EOF"

EVIDENCE_SCOPE: Final = (
    "IPS structure, artifact identity, computed write geometry, policy "
    "intersections, and optional pinned-reference comparison only"
)

PROBE_OFFSETS: Final = {
    "pc07_crono_critical_shared_selector": 0x0D400E,
}
_MISSING: Final = object()


class IpsAuditError(ValueError):
    """An IPS input, reference identity, or audit invariant failed closed."""


@dataclasses.dataclass(frozen=True)
class IpsRecord:
    offset: int
    payload: bytes
    encoding: str

    @property
    def end(self) -> int:
        return self.offset + len(self.payload)


class EffectiveWrites(MappingABC[int, int]):
    """Compact final address/value map for one bounded IPS patch."""

    __slots__ = (
        "_maximum_offset_exclusive",
        "_minimum_offset",
        "_offsets",
        "_present",
        "_span_count",
        "_values",
    )

    def __init__(self, records: Sequence[IpsRecord]) -> None:
        highest = max((record.end for record in records), default=0)
        self._values = bytearray(highest)
        self._present = bytearray((highest + 7) // 8)
        self._offsets = array("I")
        self._minimum_offset: int | None = None
        self._maximum_offset_exclusive: int | None = None
        self._span_count = 0
        if self._offsets.itemsize < 3:
            raise IpsAuditError("platform unsigned-int array cannot hold u24")
        for record in records:
            for relative, value in enumerate(record.payload):
                offset = record.offset + relative
                present_index = offset >> 3
                present_mask = 1 << (offset & 7)
                if self._present[present_index] & present_mask == 0:
                    has_left = offset > 0 and offset - 1 in self
                    has_right = offset + 1 in self
                    if has_left and has_right:
                        self._span_count -= 1
                    elif not has_left and not has_right:
                        self._span_count += 1
                    self._present[present_index] |= present_mask
                    self._offsets.append(offset)
                    if (
                        self._minimum_offset is None
                        or offset < self._minimum_offset
                    ):
                        self._minimum_offset = offset
                    if (
                        self._maximum_offset_exclusive is None
                        or offset + 1 > self._maximum_offset_exclusive
                    ):
                        self._maximum_offset_exclusive = offset + 1
                self._values[offset] = value

    @property
    def storage_bytes(self) -> int:
        return (
            len(self._values)
            + len(self._present)
            + len(self._offsets) * self._offsets.itemsize
        )

    @property
    def minimum_offset(self) -> int | None:
        return self._minimum_offset

    @property
    def maximum_offset_exclusive(self) -> int | None:
        return self._maximum_offset_exclusive

    @property
    def span_count(self) -> int:
        return self._span_count

    def __len__(self) -> int:
        return len(self._offsets)

    def __iter__(self) -> Iterator[int]:
        return iter(self._offsets)

    def items(self) -> Iterator[tuple[int, int]]:
        return (
            (offset, self._values[offset]) for offset in self._offsets
        )

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, int) or not 0 <= key < len(self._values):
            return False
        return bool(self._present[key >> 3] & (1 << (key & 7)))

    def __getitem__(self, key: int) -> int:
        if key not in self:
            raise KeyError(key)
        return self._values[key]

    def comparison_counts_to(
        self,
        target: "EffectiveWrites",
    ) -> tuple[int, int, int]:
        identical = 0
        different = 0
        missing = 0
        target_values = target._values
        target_present = target._present
        target_size = len(target_values)
        for offset in self._offsets:
            if (
                offset >= target_size
                or target_present[offset >> 3] & (1 << (offset & 7)) == 0
            ):
                missing += 1
            elif target_values[offset] == self._values[offset]:
                identical += 1
            else:
                different += 1
        return identical, different, missing


@dataclasses.dataclass(frozen=True)
class IpsPatch:
    records: tuple[IpsRecord, ...]
    truncate_size: int | None

    def effective_writes(self) -> EffectiveWrites:
        """Return the final byte at each written offset (last record wins)."""
        return EffectiveWrites(self.records)


def sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _read_u24(source: bytes, cursor: int, label: str) -> tuple[int, int]:
    if cursor + 3 > len(source):
        raise IpsAuditError(f"truncated {label}")
    return int.from_bytes(source[cursor : cursor + 3], "big"), cursor + 3


def _read_u16(source: bytes, cursor: int, label: str) -> tuple[int, int]:
    if cursor + 2 > len(source):
        raise IpsAuditError(f"truncated {label}")
    return int.from_bytes(source[cursor : cursor + 2], "big"), cursor + 2


def parse_ips(source: bytes) -> IpsPatch:
    """Parse one classic IPS file without applying or exporting it."""
    if len(source) > MAX_PATCH_FILE_BYTES:
        raise IpsAuditError("IPS input exceeds file-size budget")
    if not source.startswith(IPS_HEADER):
        raise IpsAuditError("IPS header is not PATCH")
    cursor = len(IPS_HEADER)
    records: list[IpsRecord] = []
    declared_write_bytes = 0
    while True:
        if cursor + 3 > len(source):
            raise IpsAuditError("IPS is missing EOF")
        if source[cursor : cursor + 3] == IPS_EOF:
            cursor += 3
            break
        if len(records) >= MAX_RECORD_COUNT:
            raise IpsAuditError("IPS exceeds record-count budget")
        offset, cursor = _read_u24(source, cursor, "record offset")
        size, cursor = _read_u16(source, cursor, "record size")
        if size:
            if cursor + size > len(source):
                raise IpsAuditError("truncated literal record")
            if declared_write_bytes + size > MAX_DECLARED_WRITE_BYTES:
                raise IpsAuditError("IPS exceeds declared-write budget")
            payload = source[cursor : cursor + size]
            cursor += size
            encoding = "literal"
        else:
            run_size, cursor = _read_u16(source, cursor, "RLE size")
            if run_size == 0:
                raise IpsAuditError("zero-length RLE record")
            if cursor >= len(source):
                raise IpsAuditError("truncated RLE value")
            if (
                declared_write_bytes + run_size
                > MAX_DECLARED_WRITE_BYTES
            ):
                raise IpsAuditError("IPS exceeds declared-write budget")
            payload = bytes([source[cursor]]) * run_size
            cursor += 1
            encoding = "rle"
        if offset + len(payload) > MAX_IPS_SIZE:
            raise IpsAuditError("IPS record exceeds 24-bit address space")
        declared_write_bytes += len(payload)
        records.append(IpsRecord(offset, payload, encoding))

    remainder = len(source) - cursor
    truncate_size: int | None = None
    if remainder == 3:
        truncate_size, cursor = _read_u24(source, cursor, "truncate size")
    elif remainder != 0:
        raise IpsAuditError("unexpected bytes after IPS EOF")
    if cursor != len(source):  # Defensive: all branches above consume exactly.
        raise IpsAuditError("IPS parser did not consume complete input")
    return IpsPatch(tuple(records), truncate_size)


def _coalesced_span_count(writes: Mapping[int, int]) -> int:
    if isinstance(writes, EffectiveWrites):
        return writes.span_count
    return sum(offset - 1 not in writes for offset in writes)


def _range_intersections(
    writes: Mapping[int, int],
    reference: bytes | None,
) -> dict[str, list[dict[str, Any]]]:
    def collect(
        entries: Sequence[write_guard.ProtectedRange]
        | Sequence[write_guard.KnownTable],
        *,
        id_attribute: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in entries:
            effective_write_bytes = 0
            changed = 0 if reference is not None else None
            for offset in range(entry.span.start, entry.span.end):
                value = writes.get(offset, _MISSING)
                if value is _MISSING:
                    continue
                effective_write_bytes += 1
                if changed is not None and (
                    offset >= len(reference) or value != reference[offset]
                ):
                    changed += 1
            if effective_write_bytes == 0:
                continue
            row: dict[str, Any] = {
                "id": getattr(entry, id_attribute),
                "declared_start": f"0x{entry.span.start:06X}",
                "declared_end_exclusive": f"0x{entry.span.end:06X}",
                "effective_write_bytes": effective_write_bytes,
                "changed_reference_bytes": changed,
                "reason": entry.reason,
            }
            if isinstance(entry, write_guard.ProtectedRange):
                row["namespace"] = entry.namespace
            rows.append(row)
        return rows

    return {
        "protected_ranges": collect(
            write_guard.PROTECTED_RANGES,
            id_attribute="range_id",
        ),
        "known_tables": collect(
            write_guard.KNOWN_TABLES,
            id_attribute="table_id",
        ),
    }


def _project_target(
    reference: bytes,
    writes: Mapping[int, int],
) -> bytes:
    highest = max(writes, default=-1) + 1
    target_size = max(len(reference), highest)
    target = bytearray(reference)
    if target_size > len(target):
        target.extend(bytes(target_size - len(target)))
    for offset, value in writes.items():
        target[offset] = value
    return bytes(target)


def audit_patch(
    source: bytes,
    *,
    label: str,
    reference: bytes | None = None,
) -> tuple[dict[str, Any], Mapping[int, int]]:
    """Return payload-free metadata plus internal effective writes."""
    patch = parse_ips(source)
    if patch.truncate_size is not None:
        raise IpsAuditError("IPS truncate records are unsupported by this audit")
    writes = patch.effective_writes()
    minimum = writes.minimum_offset
    maximum_exclusive = writes.maximum_offset_exclusive

    result: dict[str, Any] = {
        "label": label,
        "artifact": {
            "size": len(source),
            "sha256": sha256(source),
        },
        "ips": {
            "record_count": len(patch.records),
            "literal_record_count": sum(
                record.encoding == "literal" for record in patch.records
            ),
            "rle_record_count": sum(
                record.encoding == "rle" for record in patch.records
            ),
            "declared_write_bytes": sum(
                len(record.payload) for record in patch.records
            ),
            "effective_write_bytes": len(writes),
            "overwritten_record_bytes": (
                sum(len(record.payload) for record in patch.records)
                - len(writes)
            ),
            "effective_span_count": _coalesced_span_count(writes),
            "minimum_offset": (
                None if minimum is None else f"0x{minimum:06X}"
            ),
            "maximum_offset_exclusive": (
                None
                if maximum_exclusive is None
                else f"0x{maximum_exclusive:06X}"
            ),
            "truncate_size": patch.truncate_size,
        },
        "probes": {
            name: {
                "offset": f"0x{offset:06X}",
                "covered": offset in writes,
                "changes_reference": (
                    None
                    if reference is None or offset not in writes
                    else offset >= len(reference)
                    or writes[offset] != reference[offset]
                ),
            }
            for name, offset in PROBE_OFFSETS.items()
        },
        "project_epoch_intersections": _range_intersections(
            writes,
            reference,
        ),
    }

    if reference is not None:
        within_count = 0
        changed_within = 0
        same_within = 0
        expansion_count = 0
        nonzero_expansion = 0
        for offset, value in writes.items():
            if offset < len(reference):
                within_count += 1
                if value == reference[offset]:
                    same_within += 1
                else:
                    changed_within += 1
            else:
                expansion_count += 1
                if value != 0:
                    nonzero_expansion += 1
        target = _project_target(reference, writes)
        result["reference_comparison"] = {
            "reference_size": len(reference),
            "reference_sha256": sha256(reference),
            "effective_writes_within_reference": within_count,
            "changed_bytes_within_reference": changed_within,
            "same_value_writes_within_reference": same_within,
            "effective_expansion_writes": expansion_count,
            "nonzero_expansion_writes": nonzero_expansion,
            "zero_expansion_writes": expansion_count - nonzero_expansion,
            "projected_target_size": len(target),
            "projected_target_sha256": sha256(target),
            "projection_semantics": (
                "records applied in order; extension zero-filled; truncate "
                "records refused; target retained in memory only"
            ),
        }
    return result, writes


def compare_writes(
    source_label: str,
    source: Mapping[int, int],
    target_label: str,
    target: Mapping[int, int],
) -> dict[str, Any]:
    if isinstance(source, EffectiveWrites) and isinstance(
        target,
        EffectiveWrites,
    ):
        identical, different, missing = source.comparison_counts_to(target)
    else:
        identical = 0
        different = 0
        missing = 0
        for offset, value in source.items():
            target_value = target.get(offset, _MISSING)
            if target_value is _MISSING:
                missing += 1
            elif target_value == value:
                identical += 1
            else:
                different += 1
    return {
        "source": source_label,
        "target": target_label,
        "source_effective_write_bytes": len(source),
        "identical_address_value_bytes": identical,
        "different_value_same_address_bytes": different,
        "missing_address_bytes": missing,
        "address_subset": missing == 0,
        "address_value_subset": missing == 0 and different == 0,
    }


def _catalog_sha256(
    entries: Sequence[write_guard.ProtectedRange]
    | Sequence[write_guard.KnownTable],
    *,
    id_attribute: str,
) -> str:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        row: dict[str, Any] = {
            "id": getattr(entry, id_attribute),
            "start": entry.span.start,
            "end_exclusive": entry.span.end,
            "reason": entry.reason,
        }
        if isinstance(entry, write_guard.ProtectedRange):
            row["namespace"] = entry.namespace
        rows.append(row)
    canonical = json.dumps(
        rows,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return sha256(canonical)


def audit_many(
    patches: Sequence[tuple[str, bytes]],
    *,
    reference: bytes | None = None,
) -> dict[str, Any]:
    if len(patches) > MAX_PATCH_COUNT:
        raise IpsAuditError("audit exceeds patch-count budget")
    total_patch_file_bytes = sum(len(source) for _, source in patches)
    if total_patch_file_bytes > MAX_TOTAL_PATCH_FILE_BYTES:
        raise IpsAuditError("audit exceeds aggregate input-size budget")
    labels = [label for label, _ in patches]
    if len(labels) != len(set(labels)):
        raise IpsAuditError("patch labels must be unique")
    if reference is not None:
        _validate_canonical_rom(reference)
    reports: list[dict[str, Any]] = []
    writes_by_label: dict[str, Mapping[int, int]] = {}
    total_declared_write_bytes = 0
    total_effective_write_bytes = 0
    for label, source in patches:
        report, writes = audit_patch(
            source,
            label=label,
            reference=reference,
        )
        total_declared_write_bytes += report["ips"]["declared_write_bytes"]
        if total_declared_write_bytes > MAX_TOTAL_DECLARED_WRITE_BYTES:
            raise IpsAuditError("audit exceeds aggregate declared-write budget")
        total_effective_write_bytes += len(writes)
        if total_effective_write_bytes > MAX_TOTAL_EFFECTIVE_WRITE_BYTES:
            raise IpsAuditError("audit exceeds aggregate effective-write budget")
        reports.append(report)
        writes_by_label[label] = writes
    relation_address_visits = (len(labels) - 1) * total_effective_write_bytes
    if relation_address_visits > MAX_RELATION_ADDRESS_VISITS:
        raise IpsAuditError("audit exceeds relation-address-visit budget")
    relations = [
        compare_writes(
            source_label,
            writes_by_label[source_label],
            target_label,
            writes_by_label[target_label],
        )
        for source_label in labels
        for target_label in labels
        if source_label != target_label
    ]
    return {
        "schema": SCHEMA,
        "version": 1,
        "evidence_level": "verified-static",
        "evidence_scope": EVIDENCE_SCOPE,
        "artifact_provenance": "caller-supplied-read-only-input",
        "policy": {
            "write_guard_version": write_guard.VERSION,
            "canonical_source_kind": write_guard.CANONICAL_SOURCE_KIND,
            "canonical_source_sha256": CANONICAL_ROM_SHA256,
            "protected_range_catalog_sha256": _catalog_sha256(
                write_guard.PROTECTED_RANGES,
                id_attribute="range_id",
            ),
            "known_table_catalog_sha256": _catalog_sha256(
                write_guard.KNOWN_TABLES,
                id_attribute="table_id",
            ),
        },
        "resource_budget": {
            "limits": {
                "patch_count": MAX_PATCH_COUNT,
                "patch_file_bytes": MAX_PATCH_FILE_BYTES,
                "record_count_per_patch": MAX_RECORD_COUNT,
                "declared_write_bytes_per_patch": MAX_DECLARED_WRITE_BYTES,
                "aggregate_patch_file_bytes": MAX_TOTAL_PATCH_FILE_BYTES,
                "aggregate_declared_write_bytes": (
                    MAX_TOTAL_DECLARED_WRITE_BYTES
                ),
                "aggregate_effective_write_bytes": (
                    MAX_TOTAL_EFFECTIVE_WRITE_BYTES
                ),
                "relation_address_visits": MAX_RELATION_ADDRESS_VISITS,
            },
            "actual": {
                "patch_count": len(patches),
                "patch_file_bytes": total_patch_file_bytes,
                "declared_write_bytes": total_declared_write_bytes,
                "effective_write_bytes": total_effective_write_bytes,
                "directed_relation_count": len(relations),
                "relation_address_visits": relation_address_visits,
            },
        },
        "safety": {
            "rom_patch_save_or_state_written": False,
            "patched_image_emitted": False,
            "patch_payload_serialized": False,
            "production_hook_or_allocation_approved": False,
        },
        "patches": reports,
        "directed_subset_relations": relations,
    }


def _read_file(
    path: Path,
    label: str,
    *,
    max_bytes: int,
) -> bytes:
    if max_bytes < 0:
        raise IpsAuditError(f"{label} has an invalid read budget")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise IpsAuditError(f"{label} is not a regular file: {path}")
            if opened.st_size > max_bytes:
                raise IpsAuditError(f"{label} exceeds file-size budget")
            return _read_bounded(
                handle,
                label,
                max_bytes=max_bytes,
            )
    except IpsAuditError:
        raise
    except OSError as exc:
        raise IpsAuditError(f"cannot read {label}: {path}") from exc


def _read_bounded(
    handle: BinaryIO,
    label: str,
    *,
    max_bytes: int,
) -> bytes:
    source = handle.read(max_bytes + 1)
    if len(source) > max_bytes:
        raise IpsAuditError(f"{label} exceeds file-size budget")
    return source


def _validate_canonical_rom(source: bytes) -> None:
    if len(source) != CANONICAL_ROM_SIZE:
        raise IpsAuditError(
            f"reference ROM must be exactly 0x{CANONICAL_ROM_SIZE:X} bytes"
        )
    if sha256(source) != CANONICAL_ROM_SHA256:
        raise IpsAuditError("reference ROM is not pinned US Rev0 headerless")


def _read_canonical_rom(path: Path) -> bytes:
    source = _read_file(
        path,
        "reference ROM",
        max_bytes=CANONICAL_ROM_SIZE,
    )
    _validate_canonical_rom(source)
    return source


def _preflight_patch_paths(paths: Sequence[Path]) -> None:
    if len(paths) > MAX_PATCH_COUNT:
        raise IpsAuditError("audit exceeds patch-count budget")
    labels = [path.name for path in paths]
    if len(labels) != len(set(labels)):
        raise IpsAuditError("patch labels must be unique")
    total_size = 0
    for path in paths:
        try:
            if not path.is_file():
                raise IpsAuditError(f"IPS patch is not a regular file: {path}")
            size = path.stat().st_size
        except IpsAuditError:
            raise
        except OSError as exc:
            raise IpsAuditError(f"cannot inspect IPS patch: {path}") from exc
        if size > MAX_PATCH_FILE_BYTES:
            raise IpsAuditError("IPS patch exceeds file-size budget")
        total_size += size
        if total_size > MAX_TOTAL_PATCH_FILE_BYTES:
            raise IpsAuditError("audit exceeds aggregate input-size budget")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "patch",
        nargs="+",
        type=Path,
        help="historical IPS patch(es), read-only",
    )
    parser.add_argument(
        "--reference-rom",
        type=Path,
        help="pinned headerless Chrono Trigger US Rev0 ROM, read-only",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="print compact JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _preflight_patch_paths(args.patch)
        reference = (
            None
            if args.reference_rom is None
            else _read_canonical_rom(args.reference_rom)
        )
        inputs: list[tuple[str, bytes]] = []
        total_read_bytes = 0
        for path in args.patch:
            source = _read_file(
                path,
                "IPS patch",
                max_bytes=MAX_PATCH_FILE_BYTES,
            )
            total_read_bytes += len(source)
            if total_read_bytes > MAX_TOTAL_PATCH_FILE_BYTES:
                raise IpsAuditError("audit exceeds aggregate input-size budget")
            inputs.append((path.name, source))
        report = audit_many(inputs, reference=reference)
    except (IpsAuditError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            report,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
