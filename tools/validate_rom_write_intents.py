#!/usr/bin/env python3
"""Fail-closed Project Epoch ROM write-intent validation.

The validator never modifies a ROM.  It validates a strict JSON metadata
manifest and can optionally compare existing source/target images read-only.
Canonical vanilla bytes are default-deny: only a private exact-preimage
diagnostic replacement or a trusted exact instruction hook may touch them.
Production data belongs only in a trusted named ExHiROM allocation.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import schala_rom_scaffold as scaffold


VERSION = "1.0.0"
SCHEMA_VERSION = 1

CANONICAL_SOURCE_KIND = "canonical-us-rev0-4mib"
INERT_SOURCE_KIND = "project-epoch-inert-exhirom-8mib"
CANONICAL_SOURCE_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)
INERT_SOURCE_SHA256 = scaffold.EXPECTED_INERT_SCAFFOLD_SHA256
SOURCE_KINDS = {
    CANONICAL_SOURCE_KIND: (
        scaffold.EXPECTED_SOURCE_SIZE,
        CANONICAL_SOURCE_SHA256,
    ),
    INERT_SOURCE_KIND: (scaffold.TARGET_SIZE, INERT_SOURCE_SHA256),
}

BUILD_MODES = frozenset({"production", "private-diagnostic"})
CLASSIFICATIONS = frozenset(
    {
        "private-diagnostic-replacement",
        "exact-instruction-hook",
        "named-expanded-allocation",
        "managed-header-field",
    }
)
PAYLOAD_KINDS = frozenset(
    {"code", "table", "graphics", "palette", "text", "event", "header"}
)
PROVED_EVIDENCE = frozenset({"verified-static", "verified-runtime"})
HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_BYTES_RE = re.compile(r"^(?:[0-9a-f]{2})+$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class WriteIntentError(ValueError):
    """Raised when write metadata or observed image differences fail closed."""


@dataclasses.dataclass(frozen=True)
class Span:
    start: int
    size: int

    @property
    def end(self) -> int:
        return self.start + self.size

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Span") -> bool:
        return self.start <= other.start and other.end <= self.end


@dataclasses.dataclass(frozen=True)
class ProtectedRange:
    range_id: str
    span: Span
    namespace: str
    reason: str


@dataclasses.dataclass(frozen=True)
class KnownTable:
    table_id: str
    span: Span
    reason: str


@dataclasses.dataclass(frozen=True)
class HeaderField:
    field_id: str
    span: Span
    owners: frozenset[str]


@dataclasses.dataclass(frozen=True)
class ApprovedAllocation:
    allocation_id: str
    file_start: int
    size: int
    snes_start: int
    kind: str
    owner: str
    evidence: str
    source_artifact_sha256: str
    consumers: tuple[str, ...]
    alignment: int = 1
    no_bank_cross: bool = True

    @property
    def span(self) -> Span:
        return Span(self.file_start, self.size)

    def as_scaffold_allocation(self) -> scaffold.Allocation:
        return scaffold.Allocation(
            allocation_id=self.allocation_id,
            file_start=self.file_start,
            size=self.size,
            snes_start=self.snes_start,
            kind=self.kind,
            owner=self.owner,
            evidence=self.evidence,
            alignment=self.alignment,
            no_bank_cross=self.no_bank_cross,
        )


@dataclasses.dataclass(frozen=True)
class ApprovedHook:
    hook_id: str
    file_start: int
    preimage_hex: str
    owner: str
    evidence: str
    source_kind: str
    purpose: str

    @property
    def preimage(self) -> bytes:
        return bytes.fromhex(self.preimage_hex)

    @property
    def span(self) -> Span:
        return Span(self.file_start, len(self.preimage))


@dataclasses.dataclass(frozen=True)
class WriteIntent:
    write_id: str
    classification: str
    file_start: int
    size: int
    owner: str
    payload_kind: str
    evidence: str
    preimage_sha256: str
    replacement_sha256: str
    allocation_id: str | None
    hook_id: str | None
    table_id: str | None
    header_field_id: str | None
    replacement_hex: str | None

    @property
    def span(self) -> Span:
        return Span(self.file_start, self.size)


# Current evidence state: no non-inert production allocation and no production
# hook has passed its approval matrix.  These catalogs intentionally remain
# empty until reviewed evidence is promoted in source control.
APPROVED_PRODUCTION_ALLOCATIONS: tuple[ApprovedAllocation, ...] = ()
APPROVED_PRODUCTION_HOOKS: tuple[ApprovedHook, ...] = ()


# Hard denials are narrower than the canonical default-deny policy.  They pin
# retired mistakes and Epoch-owned routing data that must not be made writable
# merely by relabeling a data edit as a hook or diagnostic.
PROTECTED_RANGES = (
    ProtectedRange(
        "enemy_reward_table",
        Span(0x0C5E00, 0x700),
        "vanilla",
        "$CC:5E00-$CC:64FF is occupied EnemyRewardTable data",
    ),
    ProtectedRange(
        "pc07_crono_critical_shared_selector",
        Span(0x0D400E, 1),
        "vanilla-shared",
        "shared PC $07 normal/Crono critical attack selector",
    ),
    ProtectedRange(
        "pc_name_pointer_entry_07_epoch_split",
        Span(0x025FE6, 2),
        "epoch",
        "vanilla PC-name entry 7 is null; Epoch name storage is separate",
    ),
    ProtectedRange(
        "epoch_menu_portrait_data",
        Span(0x3FCE50, 0x20),
        "epoch",
        "existing Epoch menu-portrait data",
    ),
    ProtectedRange(
        "epoch_menu_portrait_pointer",
        Span(0x3FCE86, 2),
        "epoch",
        "existing Epoch menu-portrait pointer",
    ),
    ProtectedRange(
        "graphics_pointer_entries_07_08",
        Span(0x242015, 6),
        "vanilla-npc",
        "low graphics indices 7 and 8 are occupied",
    ),
    ProtectedRange(
        "assembly_pointer_entries_07_08",
        Span(0x242315, 6),
        "vanilla-npc",
        "low assembly indices 7 and 8 are occupied",
    ),
    ProtectedRange(
        "animation_boundary_entries_07_08",
        Span(0x24260E, 4),
        "vanilla-npc",
        "entry 7 is the PC end sentinel; following data is not free",
    ),
    ProtectedRange(
        "aux_animation_entries_07_08",
        Span(0x24280E, 4),
        "vanilla-npc",
        "low auxiliary-animation indices 7 and 8 are occupied",
    ),
    ProtectedRange(
        "palette_pointer_entries_07_08",
        Span(0x242A0E, 4),
        "vanilla-npc",
        "low palette indices 7 and 8 are occupied",
    ),
    ProtectedRange(
        "sprite_descriptor_entries_07_08",
        Span(0x24F023, 10),
        "vanilla-npc",
        "$E4:F023 begins occupied NPC descriptors",
    ),
    ProtectedRange(
        "bank40_boot_and_lowbank_mirror",
        Span(scaffold.BOOT_MIRROR_START, 0x10000),
        "scaffold",
        "bank $40 preserves reset, interrupt, and low-bank data mirrors",
    ),
    ProtectedRange(
        "noncanonical_7e_7f_tail",
        Span(
            scaffold.NONCANONICAL_TAIL_START,
            scaffold.NONCANONICAL_TAIL_END
            - scaffold.NONCANONICAL_TAIL_START,
        ),
        "scaffold",
        "CPU banks $7E/$7F are WRAM; this file tail is not allocatable",
    ),
)


KNOWN_TABLES = (
    KnownTable(
        "pc_graphics_pointer_entries",
        Span(0x242000, 7 * 3),
        "seven playable-PC graphics pointers; NPC entries follow",
    ),
    KnownTable(
        "pc_assembly_pointer_entries",
        Span(0x242300, 7 * 3),
        "seven playable-PC assembly pointers; NPC entries follow",
    ),
    KnownTable(
        "pc_aux_graphics_entries",
        Span(0x242600, 7 * 2),
        "seven playable-PC auxiliary graphics entries",
    ),
    KnownTable(
        "pc_aux_animation_entries",
        Span(0x242800, 7 * 2),
        "seven playable-PC auxiliary animation entries",
    ),
    KnownTable(
        "char_init_records",
        Span(0x0C0000, 0x230),
        "exactly seven vanilla $50-byte records",
    ),
    KnownTable(
        "tech_names",
        Span(0x0C15CF, 0x4FC),
        "116 eleven-byte names; following bytes have another owner",
    ),
    KnownTable(
        "tech_target_modes",
        Span(0x0C1ACB, 0xEA),
        "IDs $00-$74; item/enemy target data follows",
    ),
    KnownTable(
        "character_command_records",
        Span(0x0C1BEB, 0x554),
        "IDs $00-$7B; tech-property data follows",
    ),
    KnownTable(
        "tech_properties",
        Span(0x0C214B, 0x354),
        "72 twelve-byte records; participant lists follow",
    ),
    KnownTable(
        "tech_mp_costs",
        Span(0x0C253B, 0x48),
        "IDs $01-$47; basic-action map follows",
    ),
    KnownTable(
        "basic_action_map",
        Span(0x0C2583, 7),
        "seven entries; HP growth follows",
    ),
    KnownTable(
        "hp_growth",
        Span(0x0C258A, 0x38),
        "seven rows; MP growth follows",
    ),
    KnownTable(
        "mp_growth",
        Span(0x0C25C2, 0x38),
        "seven rows; stat growth follows",
    ),
    KnownTable(
        "stat_growth",
        Span(0x0C25FA, 0x38),
        "eight seven-stat rows; the eighth row is occupied table data",
    ),
    KnownTable(
        "tp_thresholds",
        Span(0x0C26FA, 0x70),
        "seven $10-byte rows; tech-base/count follows",
    ),
    KnownTable(
        "tech_effect_selectors",
        Span(0x0D45AD, 7 * 8 * 7),
        "seven PCs by eight single techs by seven selector bytes",
    ),
    KnownTable(
        "attack_selector_families",
        Span(0x0D4000, 3 * 7),
        "three seven-entry PC selector families",
    ),
    KnownTable(
        "menu_element_icon_map",
        Span(0x02A2C6, 7),
        "seven playable-PC menu element selectors; code follows",
    ),
    KnownTable(
        "full_status_portrait_archive",
        Span(0x3F0000, 7 * 0x480),
        "exactly seven vanilla 36-tile status portraits",
    ),
    KnownTable(
        "pc_portrait_palettes",
        Span(0x3F1F80, 7 * 0x20),
        "seven vanilla playable-PC portrait palettes",
    ),
    KnownTable(
        "lucca_animation",
        Span(0x243880, 0x470),
        "private supported-slot diagnostic replacement envelope",
    ),
    KnownTable(
        "lucca_aux_animation",
        Span(0x24AA20, 0x11C),
        "private supported-slot auxiliary timing replacement envelope",
    ),
)


HEADER_FIELDS = (
    HeaderField(
        "hirom_map_mode",
        Span(scaffold.HIROM_HEADER + scaffold.HEADER_MAP_MODE, 1),
        frozenset({"schala_rom_scaffold"}),
    ),
    HeaderField(
        "hirom_rom_size",
        Span(scaffold.HIROM_HEADER + scaffold.HEADER_ROM_SIZE, 1),
        frozenset({"schala_rom_scaffold"}),
    ),
    HeaderField(
        "hirom_checksum_pair",
        Span(scaffold.HIROM_HEADER + scaffold.HEADER_COMPLEMENT, 4),
        frozenset({"schala_rom_scaffold", "rom_checksum_finalizer"}),
    ),
    HeaderField(
        "exhirom_map_mode",
        Span(scaffold.EXHIROM_HEADER + scaffold.HEADER_MAP_MODE, 1),
        frozenset({"schala_rom_scaffold"}),
    ),
    HeaderField(
        "exhirom_rom_size",
        Span(scaffold.EXHIROM_HEADER + scaffold.HEADER_ROM_SIZE, 1),
        frozenset({"schala_rom_scaffold"}),
    ),
    HeaderField(
        "exhirom_checksum_pair",
        Span(scaffold.EXHIROM_HEADER + scaffold.HEADER_COMPLEMENT, 4),
        frozenset({"schala_rom_scaffold", "rom_checksum_finalizer"}),
    ),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fail(message: str) -> None:
    raise WriteIntentError(message)


def _require_dict(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return value


def _strict_keys(
    value: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    label: str,
) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - set(optional))
    if missing:
        _fail(f"{label} missing keys: {', '.join(missing)}")
    if unknown:
        _fail(f"{label} has unknown keys: {', '.join(unknown)}")


def _require_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{label} must be an integer")
    return value


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        _fail(f"{label} must be a lowercase stable ID")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not HEX_SHA256_RE.fullmatch(value):
        _fail(f"{label} must be a lowercase SHA-256")
    return value


def _require_optional_id(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _require_id(value, label)


def _require_hex_bytes(value: Any, label: str) -> str:
    if not isinstance(value, str) or not HEX_BYTES_RE.fullmatch(value):
        _fail(f"{label} must be nonempty lowercase even-length hex bytes")
    return value


def _catalog_by_id(
    entries: Iterable[ApprovedAllocation | ApprovedHook],
    label: str,
) -> dict[str, ApprovedAllocation | ApprovedHook]:
    result: dict[str, ApprovedAllocation | ApprovedHook] = {}
    for entry in entries:
        entry_id = (
            entry.allocation_id
            if isinstance(entry, ApprovedAllocation)
            else entry.hook_id
        )
        if entry_id in result:
            _fail(f"duplicate trusted {label} ID: {entry_id}")
        result[entry_id] = entry
    return result


def _parse_allocation(value: Any, index: int) -> ApprovedAllocation:
    label = f"allocations[{index}]"
    item = _require_dict(value, label)
    _strict_keys(
        item,
        required={
            "allocation_id",
            "file_start",
            "size",
            "snes_start",
            "kind",
            "owner",
            "evidence",
            "source_artifact_sha256",
            "consumers",
            "alignment",
            "no_bank_cross",
        },
        label=label,
    )
    consumers_raw = item["consumers"]
    if not isinstance(consumers_raw, list) or not consumers_raw:
        _fail(f"{label}.consumers must be a nonempty list")
    consumers = tuple(
        _require_id(consumer, f"{label}.consumers[{i}]")
        for i, consumer in enumerate(consumers_raw)
    )
    if len(set(consumers)) != len(consumers):
        _fail(f"{label}.consumers contains duplicates")
    no_bank_cross = item["no_bank_cross"]
    if not isinstance(no_bank_cross, bool):
        _fail(f"{label}.no_bank_cross must be boolean")
    allocation = ApprovedAllocation(
        allocation_id=_require_id(
            item["allocation_id"], f"{label}.allocation_id"
        ),
        file_start=_require_int(item["file_start"], f"{label}.file_start"),
        size=_require_int(item["size"], f"{label}.size"),
        snes_start=_require_int(item["snes_start"], f"{label}.snes_start"),
        kind=_require_id(item["kind"], f"{label}.kind"),
        owner=_require_id(item["owner"], f"{label}.owner"),
        evidence=_require_id(item["evidence"], f"{label}.evidence"),
        source_artifact_sha256=_require_sha256(
            item["source_artifact_sha256"],
            f"{label}.source_artifact_sha256",
        ),
        consumers=consumers,
        alignment=_require_int(item["alignment"], f"{label}.alignment"),
        no_bank_cross=no_bank_cross,
    )
    if allocation.evidence not in PROVED_EVIDENCE:
        _fail(f"{label}.evidence is not proved")
    try:
        scaffold.validate_allocations((allocation.as_scaffold_allocation(),))
    except ValueError as exc:
        raise WriteIntentError(f"{label}: {exc}") from exc
    return allocation


def _parse_write(value: Any, index: int) -> WriteIntent:
    label = f"writes[{index}]"
    item = _require_dict(value, label)
    _strict_keys(
        item,
        required={
            "write_id",
            "classification",
            "file_start",
            "size",
            "owner",
            "payload_kind",
            "evidence",
            "preimage_sha256",
            "replacement_sha256",
            "allocation_id",
            "hook_id",
            "table_id",
            "header_field_id",
            "replacement_hex",
        },
        label=label,
    )
    classification = _require_id(
        item["classification"], f"{label}.classification"
    )
    if classification not in CLASSIFICATIONS:
        _fail(f"{label}.classification is not allowed")
    payload_kind = _require_id(
        item["payload_kind"], f"{label}.payload_kind"
    )
    if payload_kind not in PAYLOAD_KINDS:
        _fail(f"{label}.payload_kind is not allowed")
    evidence = _require_id(item["evidence"], f"{label}.evidence")
    if evidence not in PROVED_EVIDENCE:
        _fail(f"{label}.evidence is not proved")
    size = _require_int(item["size"], f"{label}.size")
    if size <= 0:
        _fail(f"{label}.size must be positive")
    replacement_hex_raw = item["replacement_hex"]
    replacement_hex = (
        None
        if replacement_hex_raw is None
        else _require_hex_bytes(
            replacement_hex_raw, f"{label}.replacement_hex"
        )
    )
    result = WriteIntent(
        write_id=_require_id(item["write_id"], f"{label}.write_id"),
        classification=classification,
        file_start=_require_int(
            item["file_start"], f"{label}.file_start"
        ),
        size=size,
        owner=_require_id(item["owner"], f"{label}.owner"),
        payload_kind=payload_kind,
        evidence=evidence,
        preimage_sha256=_require_sha256(
            item["preimage_sha256"], f"{label}.preimage_sha256"
        ),
        replacement_sha256=_require_sha256(
            item["replacement_sha256"], f"{label}.replacement_sha256"
        ),
        allocation_id=_require_optional_id(
            item["allocation_id"], f"{label}.allocation_id"
        ),
        hook_id=_require_optional_id(item["hook_id"], f"{label}.hook_id"),
        table_id=_require_optional_id(
            item["table_id"], f"{label}.table_id"
        ),
        header_field_id=_require_optional_id(
            item["header_field_id"], f"{label}.header_field_id"
        ),
        replacement_hex=replacement_hex,
    )
    if result.file_start < 0:
        _fail(f"{label}.file_start must be nonnegative")
    if result.preimage_sha256 == result.replacement_sha256:
        _fail(f"{label} declares no content change")
    return result


def _validate_output_path(mode: str, value: Any) -> str | None:
    if mode == "production":
        if value is not None:
            _fail("production output_path must be null; full ROM output is private")
        return None
    if not isinstance(value, str):
        _fail("private-diagnostic output_path must be a relative private path")
    normalized = pathlib.PurePosixPath(value.replace("\\", "/"))
    if (
        normalized.is_absolute()
        or ".." in normalized.parts
        or len(normalized.parts) < 2
        or normalized.parts[0] != "private"
    ):
        _fail("private-diagnostic output_path must remain below private/")
    if normalized.suffix.lower() not in {".sfc", ".smc"}:
        _fail("private-diagnostic output_path must name a ROM image")
    return normalized.as_posix()


def _validate_protected_overlap(intent: WriteIntent) -> None:
    header = intent.classification == "managed-header-field"
    for protected in PROTECTED_RANGES:
        if not intent.span.overlaps(protected.span):
            continue
        if (
            header
            and protected.range_id == "bank40_boot_and_lowbank_mirror"
        ):
            continue
        _fail(
            f"{intent.write_id} overlaps protected {protected.namespace} "
            f"range {protected.range_id}"
        )


def _validate_diagnostic(
    intent: WriteIntent,
    *,
    mode: str,
    source_kind: str,
) -> None:
    if mode != "private-diagnostic":
        _fail(f"{intent.write_id}: diagnostic replacement is nonproduction only")
    if source_kind != CANONICAL_SOURCE_KIND:
        _fail(
            f"{intent.write_id}: diagnostic replacements require canonical "
            "source identity"
        )
    if intent.span.end > scaffold.EXPECTED_SOURCE_SIZE:
        _fail(f"{intent.write_id}: diagnostic replacement is outside vanilla")
    if (
        intent.allocation_id is not None
        or intent.hook_id is not None
        or intent.header_field_id is not None
        or intent.replacement_hex is not None
    ):
        _fail(f"{intent.write_id}: diagnostic has incompatible binding fields")
    if intent.payload_kind == "table":
        if intent.table_id is None:
            _fail(
                f"{intent.write_id}: table diagnostic requires exact table_id"
            )
        tables = {table.table_id: table for table in KNOWN_TABLES}
        table = tables.get(intent.table_id)
        if table is None:
            _fail(f"{intent.write_id}: unknown table_id {intent.table_id}")
        if not table.span.contains(intent.span):
            _fail(
                f"{intent.write_id}: in-place table extension/cross-boundary "
                f"write rejected for {intent.table_id}"
            )
    elif intent.table_id is not None:
        _fail(f"{intent.write_id}: non-table diagnostic has table_id")


def _validate_hook(
    intent: WriteIntent,
    *,
    source_kind: str,
    hooks: Mapping[str, ApprovedHook | ApprovedAllocation],
) -> None:
    if (
        intent.hook_id is None
        or intent.allocation_id is not None
        or intent.table_id is not None
        or intent.header_field_id is not None
    ):
        _fail(f"{intent.write_id}: exact hook binding fields are invalid")
    if intent.payload_kind != "code":
        _fail(f"{intent.write_id}: exact hook payload must be code")
    if intent.span.end > scaffold.EXPECTED_SOURCE_SIZE:
        _fail(f"{intent.write_id}: exact hook is outside canonical vanilla ROM")
    if intent.replacement_hex is None:
        _fail(f"{intent.write_id}: exact hook requires replacement_hex")
    hook_raw = hooks.get(intent.hook_id)
    if hook_raw is None or not isinstance(hook_raw, ApprovedHook):
        _fail(f"{intent.write_id}: hook {intent.hook_id} is not trusted")
    hook = hook_raw
    if hook.evidence not in PROVED_EVIDENCE:
        _fail(f"{intent.write_id}: trusted hook evidence is not proved")
    if hook.source_kind != source_kind:
        _fail(f"{intent.write_id}: hook source identity does not match")
    if intent.owner != hook.owner:
        _fail(f"{intent.write_id}: hook owner does not match approval")
    if intent.span != hook.span:
        _fail(f"{intent.write_id}: hook span is not the exact approved span")
    if intent.preimage_sha256 != sha256(hook.preimage):
        _fail(f"{intent.write_id}: hook preimage does not match approval")
    replacement = bytes.fromhex(intent.replacement_hex)
    if len(replacement) != intent.size:
        _fail(f"{intent.write_id}: hook replacement length differs from span")
    if sha256(replacement) != intent.replacement_sha256:
        _fail(f"{intent.write_id}: hook replacement hash mismatch")
    for table in KNOWN_TABLES:
        if intent.span.overlaps(table.span):
            _fail(
                f"{intent.write_id}: instruction hook overlaps data table "
                f"{table.table_id}"
            )


def _validate_allocation_write(
    intent: WriteIntent,
    *,
    mode: str,
    source_kind: str,
    allocations: Mapping[str, ApprovedAllocation | ApprovedHook],
) -> None:
    if mode != "production":
        _fail(f"{intent.write_id}: expanded allocation is production-only")
    if source_kind != INERT_SOURCE_KIND:
        _fail(f"{intent.write_id}: expanded writes require inert ExHiROM source")
    if (
        intent.allocation_id is None
        or intent.hook_id is not None
        or intent.table_id is not None
        or intent.header_field_id is not None
        or intent.replacement_hex is not None
    ):
        _fail(f"{intent.write_id}: expanded allocation binding fields invalid")
    allocation_raw = allocations.get(intent.allocation_id)
    if allocation_raw is None or not isinstance(
        allocation_raw, ApprovedAllocation
    ):
        _fail(
            f"{intent.write_id}: allocation {intent.allocation_id} is not trusted"
        )
    allocation = allocation_raw
    if allocation.owner != intent.owner:
        _fail(f"{intent.write_id}: allocation owner does not match approval")
    if intent.write_id not in allocation.consumers:
        _fail(f"{intent.write_id}: allocation does not name this consumer")
    if not allocation.span.contains(intent.span):
        _fail(f"{intent.write_id}: write exceeds its named allocation")
    if allocation.kind == "reserved":
        _fail(f"{intent.write_id}: reserved allocation is not writable")
    if allocation.kind != intent.payload_kind:
        _fail(f"{intent.write_id}: payload kind differs from allocation kind")
    expected_fill_hash = sha256(bytes([scaffold.FILL_BYTE]) * intent.size)
    if intent.preimage_sha256 != expected_fill_hash:
        _fail(f"{intent.write_id}: expanded preimage is not inert $FF fill")


def _validate_header(intent: WriteIntent) -> None:
    if (
        intent.header_field_id is None
        or intent.allocation_id is not None
        or intent.hook_id is not None
        or intent.table_id is not None
        or intent.replacement_hex is not None
    ):
        _fail(f"{intent.write_id}: managed header binding fields are invalid")
    if intent.payload_kind != "header":
        _fail(f"{intent.write_id}: managed header payload must be header")
    fields = {field.field_id: field for field in HEADER_FIELDS}
    field = fields.get(intent.header_field_id)
    if field is None:
        _fail(f"{intent.write_id}: unknown managed header field")
    if intent.span != field.span:
        _fail(f"{intent.write_id}: managed header span is not exact")
    if intent.owner not in field.owners:
        _fail(f"{intent.write_id}: owner cannot manage this header field")


def validate_manifest(
    manifest: Mapping[str, Any],
    *,
    allocation_catalog: Sequence[ApprovedAllocation] = (
        APPROVED_PRODUCTION_ALLOCATIONS
    ),
    hook_catalog: Sequence[ApprovedHook] = APPROVED_PRODUCTION_HOOKS,
) -> dict[str, Any]:
    """Validate strict write metadata without reading or modifying a ROM."""
    root = _require_dict(manifest, "manifest")
    _strict_keys(
        root,
        required={
            "schema_version",
            "manifest_id",
            "build_mode",
            "source_kind",
            "source_size",
            "source_sha256",
            "target_size",
            "target_sha256",
            "output_path",
            "allocations",
            "writes",
        },
        label="manifest",
    )
    if _require_int(root["schema_version"], "schema_version") != SCHEMA_VERSION:
        _fail("unsupported schema_version")
    manifest_id = _require_id(root["manifest_id"], "manifest_id")
    mode = _require_id(root["build_mode"], "build_mode")
    if mode not in BUILD_MODES:
        _fail("build_mode is not allowed")
    source_kind = _require_id(root["source_kind"], "source_kind")
    source_contract = SOURCE_KINDS.get(source_kind)
    if source_contract is None:
        _fail("source_kind is not approved")
    source_size = _require_int(root["source_size"], "source_size")
    source_hash = _require_sha256(root["source_sha256"], "source_sha256")
    if (source_size, source_hash) != source_contract:
        _fail("source size/hash does not match source_kind")
    target_size = _require_int(root["target_size"], "target_size")
    if target_size != source_size:
        _fail("write-intent audit requires equal source/target image sizes")
    target_hash = _require_sha256(root["target_sha256"], "target_sha256")
    _validate_output_path(mode, root["output_path"])
    if mode == "production" and source_kind != INERT_SOURCE_KIND:
        _fail("production manifests must start from the inert ExHiROM scaffold")

    trusted_allocations = _catalog_by_id(
        allocation_catalog, "allocation"
    )
    trusted_hooks = _catalog_by_id(hook_catalog, "hook")

    allocations_raw = root["allocations"]
    if not isinstance(allocations_raw, list):
        _fail("allocations must be a list")
    allocations = tuple(
        _parse_allocation(value, index)
        for index, value in enumerate(allocations_raw)
    )
    if list(allocations) != sorted(
        allocations, key=lambda item: (item.file_start, item.allocation_id)
    ):
        _fail("allocations must be sorted by file_start then allocation_id")
    allocation_ids: set[str] = set()
    for allocation in allocations:
        if allocation.allocation_id in allocation_ids:
            _fail(f"duplicate allocation ID: {allocation.allocation_id}")
        allocation_ids.add(allocation.allocation_id)
        if trusted_allocations.get(allocation.allocation_id) != allocation:
            _fail(
                f"allocation {allocation.allocation_id} does not exactly match "
                "the trusted catalog"
            )
    if allocations:
        try:
            scaffold.validate_allocations(
                tuple(item.as_scaffold_allocation() for item in allocations)
            )
        except ValueError as exc:
            raise WriteIntentError(str(exc)) from exc

    writes_raw = root["writes"]
    if not isinstance(writes_raw, list):
        _fail("writes must be a list")
    writes = tuple(
        _parse_write(value, index) for index, value in enumerate(writes_raw)
    )
    if list(writes) != sorted(
        writes, key=lambda item: (item.file_start, item.write_id)
    ):
        _fail("writes must be sorted by file_start then write_id")

    seen_write_ids: set[str] = set()
    previous: WriteIntent | None = None
    used_allocation_ids: set[str] = set()
    for intent in writes:
        if intent.write_id in seen_write_ids:
            _fail(f"duplicate write ID: {intent.write_id}")
        seen_write_ids.add(intent.write_id)
        if intent.span.end > target_size:
            _fail(f"{intent.write_id}: write lies outside target image")
        if previous is not None and previous.span.end > intent.span.start:
            _fail(f"{previous.write_id} overlaps {intent.write_id}")
        previous = intent

        _validate_protected_overlap(intent)
        if intent.classification == "private-diagnostic-replacement":
            _validate_diagnostic(
                intent, mode=mode, source_kind=source_kind
            )
        elif intent.classification == "exact-instruction-hook":
            _validate_hook(
                intent, source_kind=source_kind, hooks=trusted_hooks
            )
        elif intent.classification == "named-expanded-allocation":
            _validate_allocation_write(
                intent,
                mode=mode,
                source_kind=source_kind,
                allocations=trusted_allocations,
            )
            assert intent.allocation_id is not None
            used_allocation_ids.add(intent.allocation_id)
        elif intent.classification == "managed-header-field":
            _validate_header(intent)
        else:  # pragma: no cover - parser already rejects this.
            _fail(f"{intent.write_id}: undeclared write classification")

    if used_allocation_ids != allocation_ids:
        unused = sorted(allocation_ids - used_allocation_ids)
        missing = sorted(used_allocation_ids - allocation_ids)
        details = []
        if unused:
            details.append(f"unused allocations: {', '.join(unused)}")
        if missing:
            details.append(f"undeclared allocations: {', '.join(missing)}")
        _fail("; ".join(details))
    if writes and source_hash == target_hash:
        _fail("manifest declares writes but source and target hashes are equal")
    if not writes and source_hash != target_hash:
        _fail("different target hash has no declared writes")

    canonical = json.dumps(
        root, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return {
        "schema_version": SCHEMA_VERSION,
        "validator_version": VERSION,
        "validator_sha256": sha256(pathlib.Path(__file__).read_bytes()),
        "status": "metadata-valid",
        "manifest_id": manifest_id,
        "manifest_sha256": sha256(canonical),
        "build_mode": mode,
        "source_kind": source_kind,
        "write_count": len(writes),
        "allocation_count": len(allocations),
        "total_declared_bytes": sum(intent.size for intent in writes),
        "production_allocations_currently_approved": len(
            APPROVED_PRODUCTION_ALLOCATIONS
        ),
        "production_hooks_currently_approved": len(
            APPROVED_PRODUCTION_HOOKS
        ),
        "rom_modified": False,
    }


def _find_covering_intent(
    offset: int, writes: Sequence[WriteIntent], cursor: int
) -> tuple[WriteIntent | None, int]:
    while cursor < len(writes) and writes[cursor].span.end <= offset:
        cursor += 1
    if (
        cursor < len(writes)
        and writes[cursor].span.start <= offset < writes[cursor].span.end
    ):
        return writes[cursor], cursor
    return None, cursor


def _validate_observed_header(intent: WriteIntent, target: bytes) -> None:
    field_id = intent.header_field_id
    assert field_id is not None
    data = target[intent.span.start : intent.span.end]
    if field_id in {"hirom_map_mode", "exhirom_map_mode"}:
        if data != bytes([scaffold.EXHIROM_FAST]):
            _fail(f"{intent.write_id}: managed map mode is not fast ExHiROM")
    elif field_id in {"hirom_rom_size", "exhirom_rom_size"}:
        if data != bytes([scaffold.ROM_SIZE_8_MIB]):
            _fail(f"{intent.write_id}: managed ROM size is not 8 MiB")
    elif field_id in {"hirom_checksum_pair", "exhirom_checksum_pair"}:
        complement = int.from_bytes(data[:2], "little")
        checksum = int.from_bytes(data[2:], "little")
        if complement ^ checksum != 0xFFFF:
            _fail(f"{intent.write_id}: managed checksum pair is invalid")
        if checksum != sum(target) & 0xFFFF:
            _fail(f"{intent.write_id}: managed checksum does not match image")
    else:  # pragma: no cover - metadata validation rejects unknown fields.
        _fail(f"{intent.write_id}: unknown observed header field")


def audit_images(
    manifest: Mapping[str, Any],
    source: bytes,
    target: bytes,
    *,
    allocation_catalog: Sequence[ApprovedAllocation] = (
        APPROVED_PRODUCTION_ALLOCATIONS
    ),
    hook_catalog: Sequence[ApprovedHook] = APPROVED_PRODUCTION_HOOKS,
) -> dict[str, Any]:
    """Read-only exact-preimage and complete-diff audit."""
    report = validate_manifest(
        manifest,
        allocation_catalog=allocation_catalog,
        hook_catalog=hook_catalog,
    )
    if len(source) != manifest["source_size"]:
        _fail("source image size does not match manifest")
    if len(target) != manifest["target_size"]:
        _fail("target image size does not match manifest")
    if sha256(source) != manifest["source_sha256"]:
        _fail("source image SHA-256 does not match manifest")
    if sha256(target) != manifest["target_sha256"]:
        _fail("target image SHA-256 does not match manifest")

    writes = tuple(
        _parse_write(value, index)
        for index, value in enumerate(manifest["writes"])
    )
    changed_by_write = {intent.write_id: 0 for intent in writes}
    for intent in writes:
        before = source[intent.span.start : intent.span.end]
        after = target[intent.span.start : intent.span.end]
        if sha256(before) != intent.preimage_sha256:
            _fail(f"{intent.write_id}: observed preimage hash mismatch")
        if sha256(after) != intent.replacement_sha256:
            _fail(f"{intent.write_id}: observed replacement hash mismatch")
        if intent.classification == "managed-header-field":
            _validate_observed_header(intent, target)

    cursor = 0
    changed_bytes = 0
    for offset, (before, after) in enumerate(zip(source, target, strict=True)):
        if before == after:
            continue
        changed_bytes += 1
        intent, cursor = _find_covering_intent(offset, writes, cursor)
        if intent is None:
            _fail(f"undeclared changed byte at file offset 0x{offset:06X}")
        changed_by_write[intent.write_id] += 1
    for write_id, count in changed_by_write.items():
        if count == 0:
            _fail(f"{write_id}: declared write produces no changed bytes")

    return {
        **report,
        "status": "images-valid",
        "source_sha256": sha256(source),
        "target_sha256": sha256(target),
        "changed_byte_count": changed_bytes,
        "changed_bytes_by_write": dict(sorted(changed_by_write.items())),
        "complete_diff_coverage": True,
        "preimages_verified": True,
        "rom_modified": False,
    }


def validate_original_diagnostic_manifest(manifest, *, workspace_root=None):
    """Separate blank-source contract; never expands the game source catalogs."""
    import original_snes_diagnostic_write_contract_v1 as original
    kwargs = {} if workspace_root is None else {"workspace_root": workspace_root}
    return original.validate_manifest(manifest, **kwargs)


def audit_original_diagnostic_images(manifest, source, target, *, workspace_root=None):
    """Fail-closed original-cartridge intent and complete-diff audit, read-only."""
    import original_snes_diagnostic_write_contract_v1 as original
    kwargs = {} if workspace_root is None else {"workspace_root": workspace_root}
    return original.audit_images(manifest, source, target, **kwargs)


def validate_pc07_private_expanded_manifest(manifest, *, workspace_root=None):
    """Fixed private field-helper contract; no legacy or production expansion."""
    import pc07_private_expanded_write_contract_v1 as diagnostic
    kwargs = {} if workspace_root is None else {"workspace_root": workspace_root}
    return diagnostic.validate_manifest(manifest, **kwargs)


def audit_pc07_private_expanded_images(manifest, source, target, *, workspace_root=None):
    """Audit the pinned inert-source field diagnostic before private emission."""
    import pc07_private_expanded_write_contract_v1 as diagnostic
    kwargs = {} if workspace_root is None else {"workspace_root": workspace_root}
    return diagnostic.audit_images(manifest, source, target, **kwargs)


def validate_pc07_private_first_attack_manifest(manifest, *, workspace_root=None):
    """Fixed private first-Attack contract; no production catalog expansion."""
    import pc07_private_first_attack_write_contract_v1 as diagnostic
    kwargs = {} if workspace_root is None else {"workspace_root": workspace_root}
    return diagnostic.validate_manifest(manifest, **kwargs)


def audit_pc07_private_first_attack_images(manifest, source, target, *, workspace_root=None):
    """Audit all fixed first-Attack sections before private image emission."""
    import pc07_private_first_attack_write_contract_v1 as diagnostic
    kwargs = {} if workspace_root is None else {"workspace_root": workspace_root}
    return diagnostic.audit_images(manifest, source, target, **kwargs)


def validate_pc07_schala_presentation_manifest(manifest):
    """Separate fixed private retail-Schala recipe; production stays empty."""
    import pc07_schala_presentation_write_contract_v1 as presentation
    return presentation.validate_manifest(manifest)


def audit_pc07_schala_presentation_images(manifest, source, target):
    """Audit the entire pinned-source presentation image before emission."""
    import pc07_schala_presentation_write_contract_v1 as presentation
    return presentation.audit_images(manifest, source, target)


def validate_pc07_schala_presentation_v2_manifest(manifest):
    """Separate fixed v2 tile-bank repair; all production catalogs stay empty."""
    import pc07_schala_presentation_write_contract_v2 as presentation
    return presentation.validate_manifest(manifest)


def audit_pc07_schala_presentation_v2_images(manifest, source, target):
    """Audit the complete v2 image, including its exact extra tile-bank hook."""
    import pc07_schala_presentation_write_contract_v2 as presentation
    return presentation.audit_images(manifest, source, target)


def validate_pc07_native_event_manifest(manifest):
    """Fixed private event-source recipe; no production catalog expansion."""
    import pc07_native_event_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_native_event_images(manifest, source, target):
    """Audit the exact inert-source image and all native event-source writes."""
    import pc07_native_event_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_native_save_transition_manifest(manifest):
    """Validate only the separately sealed private native save-transition recipe."""
    import pc07_native_save_transition_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_native_save_transition_images(manifest, source, target):
    """Require its exact inert source, fixed payloads and complete image diff."""
    import pc07_native_save_transition_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_installed_save_table_manifest(manifest):
    """Fixed private ten-region save table; no production catalog expansion."""
    import pc07_installed_save_table_write_contract_v2 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_installed_save_table_images(manifest, source, target):
    """Audit the exact save-only delta before bounded private image emission."""
    import pc07_installed_save_table_write_contract_v2 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_preserved_save_table_manifest(manifest):
    """Fixed private occupied-tail preservation wrapper; production stays empty."""
    import pc07_preserved_save_table_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_preserved_save_table_images(manifest, source, target):
    """Audit the exact wrapper, whole save-call hook and mirrored header pairs."""
    import pc07_preserved_save_table_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_shadow_digest_manifest(manifest):
    """Fixed private post-save digest experiment; production remains unapproved."""
    import pc07_shadow_digest_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_shadow_digest_images(manifest, source, target):
    """Audit its exact whole hook, original components and complete image diff."""
    import pc07_shadow_digest_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=pathlib.Path)
    parser.add_argument("--source", type=pathlib.Path)
    parser.add_argument("--target", type=pathlib.Path)
    args = parser.parse_args()
    if (args.source is None) != (args.target is None):
        parser.error("--source and --target must be supplied together")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.source is None:
        report = validate_manifest(manifest)
    else:
        report = audit_images(
            manifest, args.source.read_bytes(), args.target.read_bytes()
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def validate_pc07_native_sidecar_writer_manifest(manifest):
    """Fixed private native writer delta; no production catalog expansion."""
    import pc07_native_sidecar_writer_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_native_sidecar_writer_images(manifest, source, target):
    """Audit its exact writer, whole JSL hook and complete mirrored image diff."""
    import pc07_native_sidecar_writer_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_native_sidecar_loader_manifest(manifest):
    """Fixed private cold-load delta; no production catalog expansion."""
    import pc07_native_sidecar_loader_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_native_sidecar_loader_images(manifest, source, target):
    """Audit its eight exact spans and complete mirrored image diff."""
    import pc07_native_sidecar_loader_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_schala_persistent_presentation_manifest(manifest):
    """Fixed private Schala presentation on the accepted persistent parent."""
    import pc07_schala_persistent_presentation_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_schala_persistent_presentation_images(manifest, source, target):
    """Audit its 28 exact spans, inherited preservation and complete image diff."""
    import pc07_schala_persistent_presentation_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_party_exchange_manifest(manifest):
    """Exact private exchange composition; an unsealed recipe always refuses."""
    import pc07_party_exchange_write_contract_v1 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_party_exchange_images(manifest, source, target):
    """Audit new menu/field/persistence spans and the complete inherited image."""
    import pc07_party_exchange_write_contract_v1 as diagnostic
    return diagnostic.audit_images(manifest, source, target)


def validate_pc07_party_exchange_v2_manifest(manifest):
    """Separately sealed private page-upload correction; v1 stays frozen."""
    import pc07_party_exchange_write_contract_v2 as diagnostic
    return diagnostic.validate_manifest(manifest)


def audit_pc07_party_exchange_v2_images(manifest, source, target):
    """Require the corrected composition's exact complete image diff."""
    import pc07_party_exchange_write_contract_v2 as diagnostic
    return diagnostic.audit_images(manifest, source, target)
