#!/usr/bin/env python3
"""Read-only audit of logical PC $07 normal-attack table boundaries.

The audit accepts only the pinned, headerless Chrono Trigger US Rev0 ROM.  It
reads five tiny, source-declared table extents and the four out-of-extent PC
$07 lookup bytes adjacent to them.  It emits table hashes, the five already
documented lookup-byte observations, and boundary metadata--never the table
bytes themselves.  It has no ROM, save, state, patch, or output-file write
path.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Final, Mapping


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = ROOT / "references" / "pc7_attack_adapter_boundaries.json"
REFERENCE_SIZE: Final = 6_227
REFERENCE_SHA256: Final = (
    "f89bbfce542bb16944b62bc00822e7f8"
    "348acb794bedd149f38e7dd02c78caf7"
)

CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)
SCHEMA: Final = "project-epoch-pc7-attack-adapter-boundary-audit-v1"
REFERENCE_SCHEMA: Final = "project-epoch-pc7-attack-adapter-boundaries-v1"
LOGICAL_PC_ID: Final = 0x07


class AttackBoundaryAuditError(RuntimeError):
    """The ROM, source contract, or a bounded table observation drifted."""


@dataclasses.dataclass(frozen=True)
class TableSpec:
    name: str
    label: str
    start: int
    end_exclusive: int
    entry_count: int
    expected_sha256: str
    pc7_address: int
    pc7_expected: int
    pc7_in_extent: bool
    classification: str
    collision_name: str | None
    collision_address: int | None
    collision_index: int | None
    branch_behavior: str | None = None


TABLE_SPECS: Final = (
    TableSpec(
        "basic_attack_action_ids",
        "DATA8_CC2583",
        0xCC2583,
        0xCC258A,
        7,
        "21f85d8e7eb2f1352e04d472e34d8cb8b73a51cbc3b8a92d9eaeedc0ddcbc5a0",
        0xCC258A,
        0x0A,
        False,
        "fallthrough-collision",
        "hp_growth_table",
        0xCC258A,
        0,
    ),
    TableSpec(
        "attack_approach_policy",
        "DATA8_CCF63C",
        0xCCF63C,
        0xCCF644,
        8,
        "03527ae0d299998cfda2084054b7d1762d8cb45d599ffdc244e70486196a892b",
        0xCCF643,
        0xFF,
        True,
        "occupied-in-bounds-vanilla-entry",
        None,
        None,
        None,
        "nonzero-forces-pathfind",
    ),
    TableSpec(
        "pc_attack_anim_ids_a",
        "PcAttackAnimIdsA",
        0xCD4000,
        0xCD4007,
        7,
        "91b65410a211378f328320a4e25b378d1285be8cb5e4d762df0eca1a9bb526ef",
        0xCD4007,
        0x00,
        False,
        "fallthrough-collision",
        "pc_attack_anim_ids_pathfind_success",
        0xCD4007,
        0,
    ),
    TableSpec(
        "pc_attack_anim_ids_pathfind_success",
        "DATA8_CD4007",
        0xCD4007,
        0xCD400E,
        7,
        "cca11a1733c12e166dbc10de09df254ac29cda96813075d28b05cf4fc9a77884",
        0xCD400E,
        0x01,
        False,
        "fallthrough-collision",
        "pc_attack_anim_ids_b_critical",
        0xCD400E,
        0,
    ),
    TableSpec(
        "pc_attack_anim_ids_b_critical",
        "PcAttackAnimIdsB",
        0xCD400E,
        0xCD4015,
        7,
        "844b41e5f124c432dc252f0a02fc0f9473f7c5d66fb5bf47974de3e4b5eaa8ba",
        0xCD4015,
        0x13,
        False,
        "fallthrough-collision",
        "normal_attack_config_record",
        0xCD4015,
        0,
    ),
)


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AttackBoundaryAuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _snes_hex(address: int) -> str:
    return f"{address:06X}"


def _parse_snes_hex(value: Any, label: str) -> int:
    if (
        not isinstance(value, str)
        or len(value) != 6
        or value.upper() != value
    ):
        raise AttackBoundaryAuditError(f"{label} is not six-digit SNES hex")
    try:
        address = int(value, 16)
    except ValueError as exc:
        raise AttackBoundaryAuditError(
            f"{label} is not six-digit SNES hex"
        ) from exc
    if not 0xC00000 <= address <= 0xFFFFFF:
        raise AttackBoundaryAuditError(
            f"{label} is outside canonical C0-FF HiROM"
        )
    return address


def snes_hirom_to_file(address: int) -> int:
    """Map a canonical $C0-$FF HiROM address into the 4 MiB image."""
    if not 0xC00000 <= address <= 0xFFFFFF:
        raise AttackBoundaryAuditError(
            f"address is outside canonical C0-FF HiROM: ${address:06X}"
        )
    return address & 0x3FFFFF


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    if (
        contract.get("schema") != REFERENCE_SCHEMA
        or contract.get("version") != 1
        or contract.get("evidence_level") != "verified-static"
    ):
        raise AttackBoundaryAuditError("reference identity drifted")
    scope = contract.get("scope")
    if (
        not isinstance(scope, Mapping)
        or scope.get("logical_pc_id") != "07"
        or scope.get("rom_access") != "read-only"
        or scope.get("rom_save_state_mutation") is not False
        or scope.get("patch_or_rom_emission") is not False
    ):
        raise AttackBoundaryAuditError("reference safety scope drifted")
    rom = contract.get("canonical_rom")
    if (
        not isinstance(rom, Mapping)
        or rom.get("size") != CANONICAL_ROM_SIZE
        or rom.get("sha1") != CANONICAL_ROM_SHA1
        or rom.get("sha256") != CANONICAL_ROM_SHA256
    ):
        raise AttackBoundaryAuditError("reference ROM identity drifted")
    tables = contract.get("tables")
    if not isinstance(tables, list) or len(tables) != len(TABLE_SPECS):
        raise AttackBoundaryAuditError("reference table set drifted")
    by_name = {
        row.get("name"): row
        for row in tables
        if isinstance(row, Mapping)
    }
    if set(by_name) != {spec.name for spec in TABLE_SPECS}:
        raise AttackBoundaryAuditError("reference table names drifted")

    for spec in TABLE_SPECS:
        row = by_name[spec.name]
        pc7 = row.get("pc07_lookup")
        if (
            row.get("label") != spec.label
            or _parse_snes_hex(
                row.get("snes_start"),
                f"{spec.name}.snes_start",
            )
            != spec.start
            or _parse_snes_hex(
                row.get("snes_end_exclusive"),
                f"{spec.name}.snes_end_exclusive",
            )
            != spec.end_exclusive
            or row.get("entry_count") != spec.entry_count
            or row.get("entry_width") != 1
            or row.get("expected_bytes_sha256") != spec.expected_sha256
            or not isinstance(pc7, Mapping)
            or _parse_snes_hex(
                pc7.get("snes_address"),
                f"{spec.name}.pc07_lookup.snes_address",
            )
            != spec.pc7_address
            or pc7.get("in_declared_extent") is not spec.pc7_in_extent
            or pc7.get("expected_byte_hex")
            != f"{spec.pc7_expected:02x}"
            or pc7.get("classification") != spec.classification
        ):
            raise AttackBoundaryAuditError(
                f"reference table contract drifted: {spec.name}"
            )
        collision = pc7.get("collision")
        if spec.collision_name is None:
            if collision is not None:
                raise AttackBoundaryAuditError(
                    f"unexpected collision contract: {spec.name}"
                )
        elif (
            not isinstance(collision, Mapping)
            or collision.get("name") != spec.collision_name
            or _parse_snes_hex(
                collision.get("snes_address"),
                f"{spec.name}.collision.snes_address",
            )
            != spec.collision_address
            or collision.get("alias_index") != spec.collision_index
        ):
            raise AttackBoundaryAuditError(
                f"collision contract drifted: {spec.name}"
            )
        if (
            spec.branch_behavior is not None
            and pc7.get("branch_behavior") != spec.branch_behavior
        ):
            raise AttackBoundaryAuditError(
                f"branch contract drifted: {spec.name}"
            )


def load_reference_contract(
    path: Path = REFERENCE_PATH,
) -> Mapping[str, Any]:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise AttackBoundaryAuditError(
            f"cannot read pinned reference contract: {path}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise AttackBoundaryAuditError("reference contract size drifted")
    actual = _sha256_bytes(source)
    if actual != REFERENCE_SHA256:
        raise AttackBoundaryAuditError(
            "reference contract SHA-256 drifted"
        )
    try:
        value = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except AttackBoundaryAuditError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AttackBoundaryAuditError(
            "reference contract is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise AttackBoundaryAuditError("reference contract root is not object")
    _validate_reference_contract(value)
    return value


def validate_canonical_rom(rom: bytes) -> dict[str, str | int]:
    if len(rom) != CANONICAL_ROM_SIZE:
        raise AttackBoundaryAuditError(
            f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if sha1 != CANONICAL_ROM_SHA1 or sha256 != CANONICAL_ROM_SHA256:
        raise AttackBoundaryAuditError(
            "ROM hash does not match headerless US Rev0"
        )
    return {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha1": sha1,
        "sha256": sha256,
    }


def _validate_spec_geometry() -> None:
    by_name = {spec.name: spec for spec in TABLE_SPECS}
    if len(by_name) != len(TABLE_SPECS):
        raise AttackBoundaryAuditError("duplicate built-in table name")
    for spec in TABLE_SPECS:
        if (
            spec.end_exclusive - spec.start != spec.entry_count
            or spec.pc7_address != spec.start + LOGICAL_PC_ID
            or len(spec.expected_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in spec.expected_sha256
            )
        ):
            raise AttackBoundaryAuditError(
                f"built-in table geometry drifted: {spec.name}"
            )
        actual_in_extent = spec.start <= spec.pc7_address < spec.end_exclusive
        if actual_in_extent is not spec.pc7_in_extent:
            raise AttackBoundaryAuditError(
                f"built-in PC07 extent classification drifted: {spec.name}"
            )
        if spec.pc7_in_extent:
            if spec.collision_name is not None:
                raise AttackBoundaryAuditError(
                    f"in-bounds table has a collision: {spec.name}"
                )
        elif (
            spec.pc7_address != spec.end_exclusive
            or spec.collision_name is None
            or spec.collision_address != spec.pc7_address
            or spec.collision_index != 0
        ):
            raise AttackBoundaryAuditError(
                f"fallthrough geometry drifted: {spec.name}"
            )
        alias = by_name.get(spec.collision_name or "")
        if alias is not None and alias.start != spec.pc7_address:
            raise AttackBoundaryAuditError(
                f"fallthrough does not alias table start: {spec.name}"
            )


def audit_rom(
    rom: bytes,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the canonical image and return bounded table observations."""
    if contract is None:
        contract = load_reference_contract()
    else:
        _validate_reference_contract(contract)
    rom_identity = validate_canonical_rom(rom)
    _validate_spec_geometry()
    reference_tables = {
        row["name"]: row
        for row in contract["tables"]
    }

    observations: list[dict[str, Any]] = []
    for spec in TABLE_SPECS:
        start = snes_hirom_to_file(spec.start)
        end = snes_hirom_to_file(spec.end_exclusive)
        observed = rom[start:end]
        observed_sha256 = _sha256_bytes(observed)
        if observed_sha256 != spec.expected_sha256:
            raise AttackBoundaryAuditError(
                f"bounded table bytes drifted: {spec.name}"
            )
        pc7_offset = snes_hirom_to_file(spec.pc7_address)
        pc7_value = rom[pc7_offset]
        if pc7_value != spec.pc7_expected:
            raise AttackBoundaryAuditError(
                f"bounded PC07 lookup byte drifted: {spec.name}"
            )
        reference_pc7 = reference_tables[spec.name]["pc07_lookup"]
        pc7_output: dict[str, Any] = {
            "snes_address": _snes_hex(spec.pc7_address),
            "in_declared_extent": spec.pc7_in_extent,
            "observed_byte_hex": f"{pc7_value:02x}",
            "classification": spec.classification,
            "collision": reference_pc7["collision"],
        }
        if spec.branch_behavior is not None:
            pc7_output["branch_behavior"] = spec.branch_behavior
        observations.append(
            {
                "name": spec.name,
                "label": spec.label,
                "evidence_level": "verified-static",
                "extent": {
                    "snes_start": _snes_hex(spec.start),
                    "snes_end_exclusive": _snes_hex(spec.end_exclusive),
                    "entry_count": spec.entry_count,
                    "entry_width": 1,
                },
                "observed_sha256": observed_sha256,
                "pc07_lookup": pc7_output,
            }
        )

    return {
        "schema": SCHEMA,
        "version": 1,
        "evidence_level": "verified-static",
        "rom": rom_identity,
        "reference_contract": {
            "path": "references/pc7_attack_adapter_boundaries.json",
            "size": REFERENCE_SIZE,
            "sha256": REFERENCE_SHA256,
        },
        "logical_pc_id": "07",
        "index_policy": (
            "one-byte direct logical-PC-ID index; no scaling, masking, "
            "bounds check, or ID rewrite"
        ),
        "tables": observations,
        "conclusion": {
            "in_place_eighth_entry_writes_approved": False,
            "expanded_adapter_required": True,
            "rom_save_state_mutation_performed": False,
            "patch_or_rom_emitted": False,
        },
        "limitations": list(contract["limitations"]),
    }


def audit_rom_path(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise AttackBoundaryAuditError(
                f"ROM input is not a regular file: {path}"
            )
        if path.stat().st_size != CANONICAL_ROM_SIZE:
            raise AttackBoundaryAuditError(
                f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
            )
        rom = path.read_bytes()
    except AttackBoundaryAuditError:
        raise
    except OSError as exc:
        raise AttackBoundaryAuditError(f"cannot read ROM input: {path}") from exc
    return audit_rom(rom)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "rom",
        type=Path,
        help="headerless Chrono Trigger US Rev0 ROM; read-only",
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
        result = audit_rom_path(args.rom)
    except (AttackBoundaryAuditError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            result,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
