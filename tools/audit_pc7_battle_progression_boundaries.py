#!/usr/bin/env python3
"""Read-only audit of logical PC $07 post-battle progression boundaries.

The audit accepts only the pinned, headerless Chrono Trigger US Rev0 ROM. It
hashes three bounded code spans and nine small instruction sites that establish
the active-party XP path, reserve XP path, seven-byte battle character-to-slot
map, natural record formula, 75-percent reserve award, and the exclusive $07
loop bound. It emits metadata and hashes only. It has no ROM, save, state,
patch, or output-file write path.
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
REFERENCE_PATH = ROOT / "references" / "pc7_battle_progression_boundaries.json"
REFERENCE_SIZE: Final = 7_139
REFERENCE_SHA256: Final = (
    "446e76beec9576d94c7323c64b871920"
    "3368bf550f4593d00f2b0e07fef03457"
)

CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)
SCHEMA: Final = "project-epoch-pc7-battle-progression-audit-v1"
REFERENCE_SCHEMA: Final = "project-epoch-pc7-battle-progression-boundaries-v1"
LOGICAL_PC_ID: Final = 0x07
VANILLA_PC_COUNT: Final = 0x07
BATTLE_ACTIVE_SLOT_COUNT: Final = 0x03
PC_RECORD_BASE: Final = 0x7E2600
PC_RECORD_STRIDE: Final = 0x50
PC07_NATURAL_RECORD: Final = PC_RECORD_BASE + LOGICAL_PC_ID * PC_RECORD_STRIDE
BATTLE_ID_MAP_BASE: Final = 0x7EB1BE
BATTLE_ID_MAP_END_EXCLUSIVE: Final = BATTLE_ID_MAP_BASE + VANILLA_PC_COUNT
PC07_DIRECT_MAP_ADDRESS: Final = BATTLE_ID_MAP_BASE + LOGICAL_PC_ID
RESERVE_XP_NUMERATOR: Final = 0x0F
RESERVE_XP_DENOMINATOR: Final = 0x14


class BattleProgressionAuditError(RuntimeError):
    """The ROM, source contract, or bounded observation drifted."""


@dataclasses.dataclass(frozen=True, slots=True)
class SpanSpec:
    name: str
    start: int
    end_exclusive: int
    expected_sha256: str
    classification: str


@dataclasses.dataclass(frozen=True, slots=True)
class SiteSpec:
    name: str
    start: int
    size: int
    expected_sha256: str
    claim: str


SPAN_SPECS: Final = (
    SpanSpec(
        "active_party_xp_path",
        0xC1F93E,
        0xC1F9EB,
        "8fffca20160a25e4313ea3f8ceab3cf2331b67782bae53ff04bbd6b31c52e8c4",
        "three-slot active-party XP distribution before reserve scan",
    ),
    SpanSpec(
        "reserve_xp_path",
        0xC1F9EB,
        0xC1FA61,
        "c8a7be320e925d59a7b33e0da6992ce6ca9cd0f8568e7943292f2e564f8656a2",
        "joined-and-not-active logical-ID scan with exclusive upper bound 07",
    ),
    SpanSpec(
        "battle_id_to_slot_rebuild",
        0xFDB284,
        0xFDB2A2,
        "12e4b050874981b04ca2c745a35eefafc5cc38c7baafa00d9cc343b42ced4e71",
        "seven-byte logical-character-ID-to-active-battle-slot map rebuild",
    ),
)

SITE_SPECS: Final = (
    SiteSpec(
        "reserve_scan_call",
        0xC1F9E6,
        3,
        "d1e65188e74e41fe3a4bd58c3a7ae79fcb234dba0bc59fe02f47d48f271872ba",
        "active-party XP path calls the reserve XP routine",
    ),
    SiteSpec(
        "joined_mask_read",
        0xC1F9F8,
        3,
        "097e134e3592c50d8577d489023a2af7bdb64faea7e46bd2f68967b0cc3dab6f",
        "reserve scan reads joined mask 7E29AF",
    ),
    SiteSpec(
        "active_map_read",
        0xC1FA05,
        3,
        "d5a09d5d68bfb7eb4a878fe4b598a0fae12e3a2ec64588f64739044934596181",
        "reserve scan excludes IDs present in map 7EB1BE plus logical ID",
    ),
    SiteSpec(
        "record_stride_and_base",
        0xC1FA0C,
        19,
        "f579410b72d18e55d0be5cb757be5e7f96678853a57243344f2a4ae503bc684b",
        "record pointer is formed as 7E2600 plus logical ID times 0050",
    ),
    SiteSpec(
        "reserve_fraction_numerator",
        0xC1FA28,
        2,
        "6ff6edcb5caeba8ce468c7ac65979f1f387663d8aaaa81beea1de4f436346403",
        "reserve XP numerator is 0F",
    ),
    SiteSpec(
        "reserve_fraction_denominator",
        0xC1FA34,
        3,
        "235f008d88ceaed1f3b3a4e0d96f808b7802924c24c762bd623f3698ebeacdab",
        "reserve XP denominator is 0014, yielding 15 divided by 20 or 75 percent",
    ),
    SiteSpec(
        "reserve_logical_id_bound",
        0xC1FA5A,
        6,
        "b84756b3a1d6d48256020942cc184c2b7e1c1c8adbde4e6f2a964cf3f792bdec",
        "loop continues only while logical ID is below 07",
    ),
    SiteSpec(
        "battle_map_clear_bound",
        0xFDB284,
        11,
        "8688df737dcdd166f32104ac0322d4ec2a51154f5b1925555b3e0b750a667d47",
        "battle character-to-slot map clears exactly seven bytes at 7EB1BE-7EB1C4",
    ),
    SiteSpec(
        "battle_map_active_publish",
        0xFDB291,
        17,
        "4324a2d2efada70d430e1b81208e657cb99ff7f6f89fc3a6dcdb67068337c293",
        "three active battle slots publish their logical IDs into the seven-byte map",
    ),
)


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BattleProgressionAuditError(f"duplicate JSON key: {key}")
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
        raise BattleProgressionAuditError(f"{label} is not six-digit SNES hex")
    try:
        address = int(value, 16)
    except ValueError as exc:
        raise BattleProgressionAuditError(
            f"{label} is not six-digit SNES hex"
        ) from exc
    if not 0xC00000 <= address <= 0xFFFFFF:
        raise BattleProgressionAuditError(
            f"{label} is outside canonical C0-FF HiROM"
        )
    return address


def snes_hirom_to_file(address: int) -> int:
    """Map a canonical $C0-$FF HiROM address into the 4 MiB image."""
    if not 0xC00000 <= address <= 0xFFFFFF:
        raise BattleProgressionAuditError(
            f"address is outside canonical C0-FF HiROM: ${address:06X}"
        )
    return address & 0x3FFFFF


def _validate_hash(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise BattleProgressionAuditError(f"{label} is not lowercase SHA-256")


def _validate_specs() -> None:
    if len({spec.name for spec in SPAN_SPECS}) != len(SPAN_SPECS):
        raise BattleProgressionAuditError("duplicate built-in span name")
    if len({spec.name for spec in SITE_SPECS}) != len(SITE_SPECS):
        raise BattleProgressionAuditError("duplicate built-in site name")
    for spec in SPAN_SPECS:
        if spec.end_exclusive <= spec.start:
            raise BattleProgressionAuditError(
                f"built-in span geometry drifted: {spec.name}"
            )
        _validate_hash(spec.expected_sha256, f"{spec.name}.expected_sha256")
    for spec in SITE_SPECS:
        if spec.size <= 0:
            raise BattleProgressionAuditError(
                f"built-in site geometry drifted: {spec.name}"
            )
        _validate_hash(spec.expected_sha256, f"{spec.name}.expected_sha256")
        if not any(
            span.start <= spec.start
            and spec.start + spec.size <= span.end_exclusive
            for span in SPAN_SPECS
        ):
            raise BattleProgressionAuditError(
                f"instruction site escapes audited spans: {spec.name}"
            )
    if (
        PC07_NATURAL_RECORD != 0x7E2830
        or BATTLE_ID_MAP_END_EXCLUSIVE != 0x7EB1C5
        or PC07_DIRECT_MAP_ADDRESS != BATTLE_ID_MAP_END_EXCLUSIVE
        or RESERVE_XP_NUMERATOR * 100 // RESERVE_XP_DENOMINATOR != 75
    ):
        raise BattleProgressionAuditError("built-in PC07 derivation drifted")


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    if (
        contract.get("schema") != REFERENCE_SCHEMA
        or contract.get("version") != 1
        or contract.get("evidence_level") != "verified-static"
    ):
        raise BattleProgressionAuditError("reference identity drifted")
    scope = contract.get("scope")
    if (
        not isinstance(scope, Mapping)
        or scope.get("logical_pc_id") != "07"
        or scope.get("rom_access") != "read-only"
        or scope.get("rom_save_state_mutation") is not False
        or scope.get("patch_or_rom_emission") is not False
    ):
        raise BattleProgressionAuditError("reference safety scope drifted")
    rom = contract.get("canonical_rom")
    if (
        not isinstance(rom, Mapping)
        or rom.get("size") != CANONICAL_ROM_SIZE
        or rom.get("sha1") != CANONICAL_ROM_SHA1
        or rom.get("sha256") != CANONICAL_ROM_SHA256
    ):
        raise BattleProgressionAuditError("reference ROM identity drifted")

    spans = contract.get("spans")
    if not isinstance(spans, list) or len(spans) != len(SPAN_SPECS):
        raise BattleProgressionAuditError("reference span set drifted")
    span_by_name = {
        row.get("name"): row for row in spans if isinstance(row, Mapping)
    }
    if set(span_by_name) != {spec.name for spec in SPAN_SPECS}:
        raise BattleProgressionAuditError("reference span names drifted")
    for spec in SPAN_SPECS:
        row = span_by_name[spec.name]
        if (
            _parse_snes_hex(row.get("snes_start"), f"{spec.name}.start")
            != spec.start
            or _parse_snes_hex(
                row.get("snes_end_exclusive"), f"{spec.name}.end"
            )
            != spec.end_exclusive
            or row.get("size") != spec.end_exclusive - spec.start
            or row.get("expected_bytes_sha256") != spec.expected_sha256
            or row.get("classification") != spec.classification
        ):
            raise BattleProgressionAuditError(
                f"reference span contract drifted: {spec.name}"
            )

    sites = contract.get("instruction_sites")
    if not isinstance(sites, list) or len(sites) != len(SITE_SPECS):
        raise BattleProgressionAuditError("reference site set drifted")
    site_by_name = {
        row.get("name"): row for row in sites if isinstance(row, Mapping)
    }
    if set(site_by_name) != {spec.name for spec in SITE_SPECS}:
        raise BattleProgressionAuditError("reference site names drifted")
    for spec in SITE_SPECS:
        row = site_by_name[spec.name]
        if (
            _parse_snes_hex(row.get("snes_start"), f"{spec.name}.start")
            != spec.start
            or row.get("size") != spec.size
            or row.get("expected_bytes_sha256") != spec.expected_sha256
            or row.get("claim") != spec.claim
        ):
            raise BattleProgressionAuditError(
                f"reference instruction-site contract drifted: {spec.name}"
            )

    static_sources = contract.get("static_sources")
    if not isinstance(static_sources, list) or len(static_sources) != 2:
        raise BattleProgressionAuditError("reference static-source set drifted")
    expected_sources = {
        "references/ct_disassembly/bank_C1.asm": (
            2_768_817,
            "298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa",
        ),
        "references/ct_disassembly/bank_FD.asm": (
            691_286,
            "0f8a0d59e97de7d60945fdfef1b614217e3d673cca1e14f543234d789a87779e",
        ),
    }
    observed_sources: dict[str, tuple[int, str]] = {}
    for row in static_sources:
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            raise BattleProgressionAuditError("static-source record drifted")
        if row.get("commit") != "eeae27acdb6565e96d1d796a3d60792c250c0aa1":
            raise BattleProgressionAuditError("static-source commit drifted")
        observed_sources[row["path"]] = (row.get("size"), row.get("sha256"))
    if observed_sources != expected_sources:
        raise BattleProgressionAuditError("static-source identities drifted")

    for key in (
        "verified_static_conclusions",
        "adapter_requirements",
        "limitations",
    ):
        value = contract.get(key)
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item for item in value
        ):
            raise BattleProgressionAuditError(f"reference {key} drifted")


def load_reference_contract(path: Path = REFERENCE_PATH) -> Mapping[str, Any]:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise BattleProgressionAuditError(
            f"cannot read pinned reference contract: {path}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise BattleProgressionAuditError("reference contract size drifted")
    if _sha256_bytes(source) != REFERENCE_SHA256:
        raise BattleProgressionAuditError("reference contract SHA-256 drifted")
    try:
        value = json.loads(
            source.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except BattleProgressionAuditError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BattleProgressionAuditError(
            "reference contract is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise BattleProgressionAuditError("reference contract root is not object")
    _validate_reference_contract(value)
    return value


def validate_canonical_rom(rom: bytes) -> dict[str, str | int]:
    if len(rom) != CANONICAL_ROM_SIZE:
        raise BattleProgressionAuditError(
            f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if sha1 != CANONICAL_ROM_SHA1 or sha256 != CANONICAL_ROM_SHA256:
        raise BattleProgressionAuditError(
            "ROM hash does not match headerless US Rev0"
        )
    return {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha1": sha1,
        "sha256": sha256,
    }


def _observe(
    rom: bytes,
    start: int,
    size: int,
    expected_sha256: str,
    label: str,
) -> str:
    file_start = snes_hirom_to_file(start)
    observed = rom[file_start : file_start + size]
    if len(observed) != size:
        raise BattleProgressionAuditError(f"bounded observation truncated: {label}")
    actual = _sha256_bytes(observed)
    if actual != expected_sha256:
        raise BattleProgressionAuditError(f"bounded bytes drifted: {label}")
    return actual


def audit_rom(
    rom: bytes,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the canonical image and return bounded hash observations."""
    if contract is None:
        contract = load_reference_contract()
    else:
        _validate_reference_contract(contract)
    rom_identity = validate_canonical_rom(rom)
    _validate_specs()

    span_observations = [
        {
            "name": spec.name,
            "evidence_level": "verified-static",
            "snes_start": _snes_hex(spec.start),
            "snes_end_exclusive": _snes_hex(spec.end_exclusive),
            "size": spec.end_exclusive - spec.start,
            "observed_sha256": _observe(
                rom,
                spec.start,
                spec.end_exclusive - spec.start,
                spec.expected_sha256,
                spec.name,
            ),
            "classification": spec.classification,
        }
        for spec in SPAN_SPECS
    ]
    site_observations = [
        {
            "name": spec.name,
            "evidence_level": "verified-static",
            "snes_start": _snes_hex(spec.start),
            "size": spec.size,
            "observed_sha256": _observe(
                rom,
                spec.start,
                spec.size,
                spec.expected_sha256,
                spec.name,
            ),
            "claim": spec.claim,
        }
        for spec in SITE_SPECS
    ]

    return {
        "schema": SCHEMA,
        "version": 1,
        "evidence_level": "verified-static",
        "rom": rom_identity,
        "reference_contract": {
            "path": "references/pc7_battle_progression_boundaries.json",
            "size": REFERENCE_SIZE,
            "sha256": REFERENCE_SHA256,
        },
        "logical_pc_id": "07",
        "derived_geometry": {
            "vanilla_logical_ids_processed_by_reserve_scan": [
                f"{value:02X}" for value in range(VANILLA_PC_COUNT)
            ],
            "reserve_scan_exclusive_upper_bound": "07",
            "active_battle_slot_count": BATTLE_ACTIVE_SLOT_COUNT,
            "battle_id_map_start": f"{BATTLE_ID_MAP_BASE:06X}",
            "battle_id_map_end_exclusive": f"{BATTLE_ID_MAP_END_EXCLUSIVE:06X}",
            "pc07_direct_map_address": f"{PC07_DIRECT_MAP_ADDRESS:06X}",
            "pc07_map_lookup_in_initialized_extent": False,
            "pc_record_base": f"{PC_RECORD_BASE:06X}",
            "pc_record_stride": PC_RECORD_STRIDE,
            "pc07_natural_record": f"{PC07_NATURAL_RECORD:06X}",
            "reserve_xp_fraction": {
                "numerator": RESERVE_XP_NUMERATOR,
                "denominator": RESERVE_XP_DENOMINATOR,
                "percent": 75,
            },
        },
        "spans": span_observations,
        "instruction_sites": site_observations,
        "conclusion": {
            "reserve_pc07_supported_by_vanilla": False,
            "extend_bound_only_is_safe": False,
            "explicit_pc07_active_membership_adapter_required": True,
            "valid_v2_publication_gate_required": True,
            "rom_save_state_mutation_performed": False,
            "patch_or_rom_emitted": False,
        },
        "verified_static_conclusions": list(
            contract["verified_static_conclusions"]
        ),
        "adapter_requirements": list(contract["adapter_requirements"]),
        "limitations": list(contract["limitations"]),
    }


def audit_rom_path(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise BattleProgressionAuditError(
                f"ROM input is not a regular file: {path}"
            )
        if path.stat().st_size != CANONICAL_ROM_SIZE:
            raise BattleProgressionAuditError(
                f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
            )
        rom = path.read_bytes()
    except BattleProgressionAuditError:
        raise
    except OSError as exc:
        raise BattleProgressionAuditError(f"cannot read ROM input: {path}") from exc
    return audit_rom(rom)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "rom", type=Path, help="headerless Chrono Trigger US Rev0 ROM; read-only"
    )
    parser.add_argument("--compact", action="store_true", help="print compact JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit_rom_path(args.rom)
    except (BattleProgressionAuditError, OSError, ValueError) as exc:
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
