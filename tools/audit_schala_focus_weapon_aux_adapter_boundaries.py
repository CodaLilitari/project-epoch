#!/usr/bin/env python3
"""Read-only audit of Schala Focus-weapon auxiliary table boundaries.

The audit accepts only the pinned headerless Chrono Trigger US Rev0 ROM.  It
checks the palette-index, swing-SFX, hit-SFX, attack-package-offset, and
weapon-palette payload preimages plus the exact Focus E8-EB collision geometry.
It prints only hashes, addresses, geometry, owners, and bounded lookup facts.
It has no ROM, patch, save, state, trace, or output-file writer.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Final, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = (
    ROOT
    / "references"
    / "schala_focus_weapon_aux_adapter_boundaries.json"
)
REFERENCE_SIZE: Final = 12_908
REFERENCE_SHA256: Final = (
    "19f3e77db5fa7c31ec781100a69725d2"
    "bcb691432981f4800a8831f8cd1f4a99"
)

CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)
SCHEMA: Final = (
    "project-epoch-schala-focus-weapon-aux-boundary-audit-v1"
)
REFERENCE_SCHEMA: Final = (
    "project-epoch-schala-focus-weapon-aux-adapter-boundaries-v1"
)

LOGICAL_PC_ID: Final = 0x07
FOCUS_WEAPON_IDS: Final = (0xE8, 0xE9, 0xEA, 0xEB)
BOUNDARY_OFFSETS: Final = (0x6E0C, 0x6E4A, 0x6E83, 0x6E97, 0x6EAF)
ENEMY_SELECTOR_REFERENCE_COUNTS: Final = (3, 2, 1, 90, 4)


class FocusWeaponAuxBoundaryAuditError(RuntimeError):
    """The ROM, source contract, or a bounded observation drifted."""


@dataclasses.dataclass(frozen=True)
class RegionSpec:
    name: str
    label: str
    start: int
    end_exclusive: int
    entry_count: int
    entry_width: int
    expected_sha256: str


@dataclasses.dataclass(frozen=True)
class PreimageSpec:
    name: str
    start: int
    end_exclusive: int
    expected_sha256: str


@dataclasses.dataclass(frozen=True)
class PaletteCollisionSpec:
    weapon_id: int
    lookup: int
    owner_entry_index: int


@dataclasses.dataclass(frozen=True)
class PackageCollisionSpec:
    weapon_id: int
    lookup: int
    owner_region: str
    owner_selector_id: int
    owner_byte_offset: int


REGION_SPECS: Final = (
    RegionSpec(
        "enemy_attack_animation_records",
        "EnemyAttackAnimRecords",
        0xCD4926,
        0xCD4F26,
        256,
        6,
        "2358920a949949341abba4cdafb46055af6d5ca7e383a78d3643555a40642e5f",
    ),
    RegionSpec(
        "attack_animation_package_offsets",
        "AnimPkgOffsetsAtk",
        0xCD5FF0,
        0xCD61F0,
        256,
        2,
        "31010e7d9b8401a0a2c0309c050d245f432172f85ef2db91efbacf68822a4bd0",
    ),
    RegionSpec(
        "weapon_palette_index_values",
        "WeaponPaletteIndexValues1",
        0xCD6CEC,
        0xCD6D4C,
        96,
        1,
        "577d4ab37d0590ef48603e12da0f8e7380a14f9b91c410ff3fd937cda049fa3a",
    ),
    RegionSpec(
        "weapon_swing_sfx",
        "WeaponSwingSfxTable",
        0xCD6D4C,
        0xCD6DAC,
        96,
        1,
        "a631515921e253c7d8d57cc6ef92e1a1b69a003f58106b73a7f9378417862b2c",
    ),
    RegionSpec(
        "weapon_hit_sfx",
        "WeaponHitSfxTable",
        0xCD6DAC,
        0xCD6E0C,
        96,
        1,
        "1c7dcc41d800438c3b901b16def90bb3254dbcf3b95dc2cb4cafd54c44f5baa1",
    ),
    RegionSpec(
        "weapon_palette_rows",
        "WeaponPalettes6BytesEa",
        0xD14B00,
        0xD14C80,
        64,
        6,
        "67ac2fe29150696822de8ebdd8ba95ccc0b26c3a1670c270ebc903d088c2f24c",
    ),
)

PREIMAGE_SPECS: Final = (
    PreimageSpec(
        "focus_palette_lookup_span",
        0xCD6DD4,
        0xCD6DD8,
        "3989c4e0b53b03fa44fba6af89eeaa5f4347e8496e934ce81364e132cfca25ed",
    ),
    PreimageSpec(
        "focus_swing_sfx_lookup_span",
        0xCD6E34,
        0xCD6E38,
        "f296cd9026a29bc1e026bb22b762d5dec9c722d683ddd1ba9d94c3936527b0d1",
    ),
    PreimageSpec(
        "focus_hit_sfx_lookup_span",
        0xCD6E94,
        0xCD6E98,
        "c5fb00dbbb20935b26bd6452896ecc731efadfa083ac928e3ffe7180cb74df56",
    ),
    PreimageSpec(
        "reachable_enemy_attack_package_00",
        0xCD6E0C,
        0xCD6E4A,
        "56ed45b2793d798c4738a9ec741b16f402d9947ca031cc2a8d51c1c2e7c39167",
    ),
    PreimageSpec(
        "reachable_enemy_attack_package_02",
        0xCD6E83,
        0xCD6E97,
        "b357cf074b9d2e7a427a0fbbdc92169a180c48d8b7cdddbe76be6025e851bb92",
    ),
    PreimageSpec(
        "reachable_enemy_attack_package_03",
        0xCD6E97,
        0xCD6EAF,
        "0c1f1e3e519982d04b9441859693deff12578d1df08277e755345899d20771d8",
    ),
)

PALETTE_COLLISIONS: Final = tuple(
    PaletteCollisionSpec(
        weapon_id,
        0xCD6DD4 + index,
        0x28 + index,
    )
    for index, weapon_id in enumerate(FOCUS_WEAPON_IDS)
)

SWING_COLLISIONS: Final = tuple(
    PackageCollisionSpec(
        weapon_id,
        0xCD6E34 + index,
        "reachable_enemy_attack_package_00",
        0x00,
        0x28 + index,
    )
    for index, weapon_id in enumerate(FOCUS_WEAPON_IDS)
)

HIT_COLLISIONS: Final = (
    PackageCollisionSpec(
        0xE8,
        0xCD6E94,
        "reachable_enemy_attack_package_02",
        0x02,
        0x11,
    ),
    PackageCollisionSpec(
        0xE9,
        0xCD6E95,
        "reachable_enemy_attack_package_02",
        0x02,
        0x12,
    ),
    PackageCollisionSpec(
        0xEA,
        0xCD6E96,
        "reachable_enemy_attack_package_02",
        0x02,
        0x13,
    ),
    PackageCollisionSpec(
        0xEB,
        0xCD6E97,
        "reachable_enemy_attack_package_03",
        0x03,
        0x00,
    ),
)

EXPECTED_SCOPE: Final = {
    "logical_pc_id": "07",
    "focus_weapon_ids": ["E8", "E9", "EA", "EB"],
    "operation": (
        "Focus weapon palette, swing-SFX, hit-SFX, and enemy "
        "Attack-animation package boundary audit"
    ),
    "rom_access": "read-only",
    "source_only": True,
    "production_installable": False,
    "output_policy": (
        "region hashes, addresses, geometry, owners, and bounded lookup "
        "facts only; never table or payload bytes"
    ),
    "rom_save_state_trace_mutation": False,
    "patch_rom_or_output_file_emission": False,
    "allocation_or_hook_approval": False,
}

EXPECTED_CANONICAL_ROM: Final = {
    "identity": "Chrono Trigger US Rev0 headerless",
    "size": CANONICAL_ROM_SIZE,
    "sha256": CANONICAL_ROM_SHA256,
    "mapping": "C0-FF HiROM address masked to file offset 000000-3FFFFF",
}

EXPECTED_PALETTE_CONSUMERS: Final = [
    {
        "name": "battle_weapon_palette_copy",
        "weapon_id_source": "7E1C48 + actor_record_offset",
        "weapon_id_load_pc": "CCE718",
        "palette_index_lookup_pc": "CCE71C",
        "palette_index_region": "weapon_palette_index_values",
        "palette_row_formula": "D14B00 + palette_index * 6",
        "palette_payload_consumer_pc": "CCE739",
        "palette_payload_region": "weapon_palette_rows",
        "palette_copy_width": 6,
    },
    {
        "name": "menu_weapon_palette_record_helper",
        "input_source": "logical_pc_id",
        "character_record_stride": 80,
        "weapon_id_source": "7E2629 + logical_pc_id * $50",
        "weapon_id_load_pc": "C2F606",
        "palette_index_lookup_pc": "C2F610",
        "palette_index_region": "weapon_palette_index_values",
        "palette_row_formula": "D14B00 + palette_index * 6",
        "palette_payload_region": "weapon_palette_rows",
        "palette_copy_width": 6,
        "fixed_source_bank_callers": [
            {
                "helper_call_pc": "C28366",
                "mvn_pc": "C28369",
                "source_bank": "D1",
            },
            {
                "helper_call_pc": "C2F5D6",
                "mvn_pc": "C2F5D9",
                "source_bank": "D1",
            },
        ],
    },
]

EXPECTED_AUDIO_CONSUMERS: Final = {
    "weapon_id_cache": {
        "weapon_id_source": "7E1C48 + actor_record_offset",
        "weapon_id_load_pc": "C14346",
        "cache_destination": "7EA4E7",
        "cache_store_pc": "C14349",
    },
    "commands": [
        {
            "animation_command_id": "7C",
            "kind": "weapon-swing",
            "weapon_id_source": "7EA4E7",
            "weapon_id_load_pc": "C161EB",
            "lookup_region": "weapon_swing_sfx",
            "lookup_pc": "C161EF",
        },
        {
            "animation_command_id": "7D",
            "kind": "weapon-hit",
            "weapon_id_source": "7EA4E7",
            "weapon_id_load_pc": "C161F5",
            "lookup_region": "weapon_hit_sfx",
            "lookup_pc": "C161F9",
        },
    ],
    "common_audio_output": {
        "sfx_id_destination": "7E1E01",
        "sfx_id_store_pc": "C161FD",
        "audio_command_id": "18",
        "audio_command_destination": "7E1E00",
        "audio_command_load_pc": "C16200",
        "audio_command_store_pc": "C16202",
    },
}

EXPECTED_ATTACK_PACKAGE_RESOLUTION: Final = {
    "path": "AE91 >= 3 and AE93 == 0 enemy Attack-animation record path",
    "selector_record_source_region": "enemy_attack_animation_records",
    "selector_record_byte_offset": 0,
    "selector_record_lookup_pc": "C144B4",
    "selector_source": "7E9877",
    "selector_store_pc": "C144B8",
    "selector_load_pc": "C14530",
    "index_formula": "CD5FF0 + selector_id * 2",
    "offset_lookup_pc": "C14535",
    "offset_destination": "7E9878",
    "offset_store_pc": "C14539",
    "package_bank": "CD",
    "first_package_dereference_pc": "C14541",
    "boundary_offsets": [
        {
            "selector_id": f"{selector_id:02X}",
            "stored_offset": f"{stored_offset:04X}",
            "package_snes_start": f"CD{stored_offset:04X}",
        }
        for selector_id, stored_offset in enumerate(BOUNDARY_OFFSETS)
    ],
    "enemy_attack_selector_reference_counts": [
        {
            "selector_id": f"{selector_id:02X}",
            "record_count": record_count,
        }
        for selector_id, record_count in enumerate(
            ENEMY_SELECTOR_REFERENCE_COUNTS
        )
    ],
}

CONCLUSIONS: Final = (
    "Focus weapon IDs E8-EB cannot index any of the three 96-entry "
    "vanilla weapon auxiliary tables in place.",
    "The palette-index overrun aliases occupied weapon-hit SFX entries "
    "28-2B.",
    "The swing- and hit-SFX overruns alias reachable enemy "
    "Attack-animation packages.",
    "Palette rows are six-byte bank-D1 payloads, and both menu callers "
    "hard-code bank D1 for their copies.",
    "Named expanded palette, swing-SFX, and hit-SFX descriptors require "
    "explicit adapters before any Focus weapon can bind them.",
)

LIMITATIONS: Final = (
    "This audit does not execute logical PC 07, Focus Pulse, or a Focus "
    "weapon.",
    "The enemy Attack-animation selector reference counts are bounded static "
    "ownership facts, not a complete semantic decode of the attack packages.",
    "This audit does not assign native palette or SFX IDs and does not bind "
    "any source-only Focus descriptor.",
    "This audit does not approve hooks, expanded allocations, ROM mutation, "
    "patches, or production installation.",
)


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FocusWeaponAuxBoundaryAuditError(
                f"duplicate JSON key: {key}"
            )
        result[key] = value
    return result


def _hex2(value: int) -> str:
    return f"{value:02X}"


def _hex4(value: int) -> str:
    return f"{value:04X}"


def _hex6(value: int) -> str:
    return f"{value:06X}"


def _parse_hex(value: Any, width: int, label: str) -> int:
    if (
        not isinstance(value, str)
        or len(value) != width
        or value.upper() != value
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise FocusWeaponAuxBoundaryAuditError(
            f"{label} is not {width}-digit uppercase hex"
        )
    return int(value, 16)


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    if set(value) != expected:
        raise FocusWeaponAuxBoundaryAuditError(f"{label} keys drifted")


def _require_exact_value(actual: Any, expected: Any, label: str) -> None:
    """Compare JSON-shaped values without accepting bool as an integer."""
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            raise FocusWeaponAuxBoundaryAuditError(f"{label} type drifted")
        _require_exact_keys(actual, set(expected), label)
        for key, expected_child in expected.items():
            _require_exact_value(
                actual[key],
                expected_child,
                f"{label}.{key}",
            )
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise FocusWeaponAuxBoundaryAuditError(f"{label} list drifted")
        for index, (actual_child, expected_child) in enumerate(
            zip(actual, expected, strict=True)
        ):
            _require_exact_value(
                actual_child,
                expected_child,
                f"{label}[{index}]",
            )
        return
    if type(actual) is not type(expected) or actual != expected:
        raise FocusWeaponAuxBoundaryAuditError(f"{label} value drifted")


def snes_hirom_to_file(address: int) -> int:
    """Map a canonical $C0-$FF HiROM address into the 4 MiB image."""
    if type(address) is not int or not 0xC00000 <= address <= 0xFFFFFF:
        raise FocusWeaponAuxBoundaryAuditError(
            f"address is outside canonical C0-FF HiROM: {address!r}"
        )
    return address & 0x3FFFFF


def _region_map() -> dict[str, RegionSpec]:
    result = {spec.name: spec for spec in REGION_SPECS}
    if len(result) != len(REGION_SPECS):
        raise FocusWeaponAuxBoundaryAuditError(
            "duplicate built-in region name"
        )
    return result


def _preimage_map() -> dict[str, PreimageSpec]:
    result = {spec.name: spec for spec in PREIMAGE_SPECS}
    if len(result) != len(PREIMAGE_SPECS):
        raise FocusWeaponAuxBoundaryAuditError(
            "duplicate built-in preimage name"
        )
    return result


def _expected_collision_contract() -> dict[str, Any]:
    return {
        "palette_index": {
            "index_formula": "CD6CEC + equipped_weapon_id",
            "declared_entry_count": 96,
            "bounded_lookup_preimage": "focus_palette_lookup_span",
            "collisions": [
                {
                    "weapon_id": _hex2(row.weapon_id),
                    "lookup_snes_address": _hex6(row.lookup),
                    "declared_table_contains_lookup": False,
                    "owner_region": "weapon_hit_sfx",
                    "owner_entry_index": row.owner_entry_index,
                }
                for row in PALETTE_COLLISIONS
            ],
        },
        "swing_sfx": {
            "index_formula": "CD6D4C + equipped_weapon_id",
            "declared_entry_count": 96,
            "bounded_lookup_preimage": "focus_swing_sfx_lookup_span",
            "collisions": [
                {
                    "weapon_id": _hex2(row.weapon_id),
                    "lookup_snes_address": _hex6(row.lookup),
                    "declared_table_contains_lookup": False,
                    "owner_region": row.owner_region,
                    "owner_selector_id": _hex2(row.owner_selector_id),
                    "owner_byte_offset": row.owner_byte_offset,
                }
                for row in SWING_COLLISIONS
            ],
        },
        "hit_sfx": {
            "index_formula": "CD6DAC + equipped_weapon_id",
            "declared_entry_count": 96,
            "bounded_lookup_preimage": "focus_hit_sfx_lookup_span",
            "collisions": [
                {
                    "weapon_id": _hex2(row.weapon_id),
                    "lookup_snes_address": _hex6(row.lookup),
                    "declared_table_contains_lookup": False,
                    "owner_region": row.owner_region,
                    "owner_selector_id": _hex2(row.owner_selector_id),
                    "owner_byte_offset": row.owner_byte_offset,
                }
                for row in HIT_COLLISIONS
            ],
        },
    }


def _validate_spec_geometry() -> None:
    regions = _region_map()
    preimages = _preimage_map()
    for spec in REGION_SPECS:
        if (
            spec.end_exclusive - spec.start
            != spec.entry_count * spec.entry_width
            or len(spec.expected_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in spec.expected_sha256
            )
        ):
            raise FocusWeaponAuxBoundaryAuditError(
                f"built-in region geometry drifted: {spec.name}"
            )
    for spec in PREIMAGE_SPECS:
        if (
            spec.end_exclusive <= spec.start
            or len(spec.expected_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in spec.expected_sha256
            )
        ):
            raise FocusWeaponAuxBoundaryAuditError(
                f"built-in preimage geometry drifted: {spec.name}"
            )

    palette = regions["weapon_palette_index_values"]
    swing = regions["weapon_swing_sfx"]
    hit = regions["weapon_hit_sfx"]
    enemy_records = regions["enemy_attack_animation_records"]
    if (
        (enemy_records.entry_count, enemy_records.entry_width) != (0x100, 6)
        or (palette.entry_count, palette.entry_width) != (0x60, 1)
        or (swing.entry_count, swing.entry_width) != (0x60, 1)
        or (hit.entry_count, hit.entry_width) != (0x60, 1)
        or palette.end_exclusive != swing.start
        or swing.end_exclusive != hit.start
        or hit.end_exclusive != 0xCD6E0C
    ):
        raise FocusWeaponAuxBoundaryAuditError(
            "built-in auxiliary-table geometry drifted"
        )

    offsets = regions["attack_animation_package_offsets"]
    if (
        (offsets.entry_count, offsets.entry_width) != (0x100, 2)
        or len(BOUNDARY_OFFSETS) != 5
        or tuple(sorted(BOUNDARY_OFFSETS)) != BOUNDARY_OFFSETS
    ):
        raise FocusWeaponAuxBoundaryAuditError(
            "built-in attack-package-offset geometry drifted"
        )
    expected_package_extents = {
        "reachable_enemy_attack_package_00": (
            0xCD0000 + BOUNDARY_OFFSETS[0],
            0xCD0000 + BOUNDARY_OFFSETS[1],
        ),
        "reachable_enemy_attack_package_02": (
            0xCD0000 + BOUNDARY_OFFSETS[2],
            0xCD0000 + BOUNDARY_OFFSETS[3],
        ),
        "reachable_enemy_attack_package_03": (
            0xCD0000 + BOUNDARY_OFFSETS[3],
            0xCD0000 + BOUNDARY_OFFSETS[4],
        ),
    }
    for name, extent in expected_package_extents.items():
        owner = preimages[name]
        if (owner.start, owner.end_exclusive) != extent:
            raise FocusWeaponAuxBoundaryAuditError(
                f"built-in owner extent drifted: {name}"
            )

    if tuple(row.weapon_id for row in PALETTE_COLLISIONS) != FOCUS_WEAPON_IDS:
        raise FocusWeaponAuxBoundaryAuditError(
            "built-in palette collision IDs drifted"
        )
    for row in PALETTE_COLLISIONS:
        expected_lookup = palette.start + row.weapon_id
        if (
            row.lookup != expected_lookup
            or palette.start <= row.lookup < palette.end_exclusive
            or not hit.start <= row.lookup < hit.end_exclusive
            or row.owner_entry_index != row.lookup - hit.start
        ):
            raise FocusWeaponAuxBoundaryAuditError(
                f"built-in palette collision drifted: {_hex2(row.weapon_id)}"
            )

    for table, rows in (
        (swing, SWING_COLLISIONS),
        (hit, HIT_COLLISIONS),
    ):
        if tuple(row.weapon_id for row in rows) != FOCUS_WEAPON_IDS:
            raise FocusWeaponAuxBoundaryAuditError(
                f"built-in {table.name} collision IDs drifted"
            )
        for row in rows:
            owner = preimages[row.owner_region]
            if (
                row.lookup != table.start + row.weapon_id
                or table.start <= row.lookup < table.end_exclusive
                or not owner.start <= row.lookup < owner.end_exclusive
                or row.owner_byte_offset != row.lookup - owner.start
                or row.lookup
                != 0xCD0000 + BOUNDARY_OFFSETS[row.owner_selector_id]
                + row.owner_byte_offset
            ):
                raise FocusWeaponAuxBoundaryAuditError(
                    f"built-in {table.name} collision drifted: "
                    f"{_hex2(row.weapon_id)}"
                )

    for collision_name, expected_start in (
        ("focus_palette_lookup_span", PALETTE_COLLISIONS[0].lookup),
        ("focus_swing_sfx_lookup_span", SWING_COLLISIONS[0].lookup),
        ("focus_hit_sfx_lookup_span", HIT_COLLISIONS[0].lookup),
    ):
        span = preimages[collision_name]
        if (
            span.start != expected_start
            or span.end_exclusive - span.start != len(FOCUS_WEAPON_IDS)
        ):
            raise FocusWeaponAuxBoundaryAuditError(
                f"built-in collision preimage drifted: {collision_name}"
            )


def _validate_reference_contract(contract: Mapping[str, Any]) -> None:
    _require_exact_keys(
        contract,
        {
            "schema",
            "version",
            "evidence_level",
            "scope",
            "canonical_rom",
            "regions",
            "bounded_preimages",
            "palette_consumers",
            "weapon_audio_consumers",
            "attack_package_resolution",
            "focus_lookup_collisions",
            "verified_static_conclusions",
            "limitations",
        },
        "reference root",
    )
    if (
        contract.get("schema") != REFERENCE_SCHEMA
        or type(contract.get("version")) is not int
        or contract.get("version") != 1
        or contract.get("evidence_level") != "verified-static"
    ):
        raise FocusWeaponAuxBoundaryAuditError(
            "reference identity drifted"
        )

    _require_exact_value(contract.get("scope"), EXPECTED_SCOPE, "scope")
    _require_exact_value(
        contract.get("canonical_rom"),
        EXPECTED_CANONICAL_ROM,
        "canonical_rom",
    )

    rows = contract.get("regions")
    if not isinstance(rows, list) or len(rows) != len(REGION_SPECS):
        raise FocusWeaponAuxBoundaryAuditError(
            "reference region set drifted"
        )
    for row, spec in zip(rows, REGION_SPECS, strict=True):
        if not isinstance(row, Mapping):
            raise FocusWeaponAuxBoundaryAuditError(
                f"reference region type drifted: {spec.name}"
            )
        _require_exact_keys(
            row,
            {
                "name",
                "label",
                "snes_start",
                "snes_end_exclusive",
                "entry_count",
                "entry_width",
                "expected_bytes_sha256",
            },
            f"reference region {spec.name}",
        )
        if (
            row.get("name") != spec.name
            or row.get("label") != spec.label
            or _parse_hex(
                row.get("snes_start"),
                6,
                f"{spec.name}.snes_start",
            )
            != spec.start
            or _parse_hex(
                row.get("snes_end_exclusive"),
                6,
                f"{spec.name}.snes_end_exclusive",
            )
            != spec.end_exclusive
            or type(row.get("entry_count")) is not int
            or row.get("entry_count") != spec.entry_count
            or type(row.get("entry_width")) is not int
            or row.get("entry_width") != spec.entry_width
            or row.get("expected_bytes_sha256") != spec.expected_sha256
        ):
            raise FocusWeaponAuxBoundaryAuditError(
                f"reference region contract drifted: {spec.name}"
            )

    spans = contract.get("bounded_preimages")
    if not isinstance(spans, list) or len(spans) != len(PREIMAGE_SPECS):
        raise FocusWeaponAuxBoundaryAuditError(
            "reference preimage set drifted"
        )
    for row, spec in zip(spans, PREIMAGE_SPECS, strict=True):
        if not isinstance(row, Mapping):
            raise FocusWeaponAuxBoundaryAuditError(
                f"reference preimage type drifted: {spec.name}"
            )
        _require_exact_keys(
            row,
            {
                "name",
                "snes_start",
                "snes_end_exclusive",
                "expected_bytes_sha256",
            },
            f"reference preimage {spec.name}",
        )
        if (
            row.get("name") != spec.name
            or _parse_hex(
                row.get("snes_start"),
                6,
                f"{spec.name}.snes_start",
            )
            != spec.start
            or _parse_hex(
                row.get("snes_end_exclusive"),
                6,
                f"{spec.name}.snes_end_exclusive",
            )
            != spec.end_exclusive
            or row.get("expected_bytes_sha256") != spec.expected_sha256
        ):
            raise FocusWeaponAuxBoundaryAuditError(
                f"reference preimage contract drifted: {spec.name}"
            )

    _require_exact_value(
        contract.get("palette_consumers"),
        EXPECTED_PALETTE_CONSUMERS,
        "palette_consumers",
    )
    _require_exact_value(
        contract.get("weapon_audio_consumers"),
        EXPECTED_AUDIO_CONSUMERS,
        "weapon_audio_consumers",
    )
    _require_exact_value(
        contract.get("attack_package_resolution"),
        EXPECTED_ATTACK_PACKAGE_RESOLUTION,
        "attack_package_resolution",
    )
    _require_exact_value(
        contract.get("focus_lookup_collisions"),
        _expected_collision_contract(),
        "focus_lookup_collisions",
    )
    _require_exact_value(
        contract.get("verified_static_conclusions"),
        list(CONCLUSIONS),
        "verified_static_conclusions",
    )
    _require_exact_value(
        contract.get("limitations"),
        list(LIMITATIONS),
        "limitations",
    )
    _validate_spec_geometry()


def load_reference_contract(
    path: Path = REFERENCE_PATH,
) -> Mapping[str, Any]:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise FocusWeaponAuxBoundaryAuditError(
            f"cannot read pinned reference contract: {path}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise FocusWeaponAuxBoundaryAuditError(
            "reference contract size drifted"
        )
    if _sha256_bytes(source) != REFERENCE_SHA256:
        raise FocusWeaponAuxBoundaryAuditError(
            "reference contract SHA-256 drifted"
        )
    try:
        value = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except FocusWeaponAuxBoundaryAuditError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FocusWeaponAuxBoundaryAuditError(
            "reference contract is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise FocusWeaponAuxBoundaryAuditError(
            "reference contract root is not object"
        )
    _validate_reference_contract(value)
    return value


def validate_canonical_rom(rom: bytes) -> dict[str, str | int]:
    if not isinstance(rom, bytes) or len(rom) != CANONICAL_ROM_SIZE:
        raise FocusWeaponAuxBoundaryAuditError(
            f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if sha1 != CANONICAL_ROM_SHA1 or sha256 != CANONICAL_ROM_SHA256:
        raise FocusWeaponAuxBoundaryAuditError(
            "ROM hash does not match headerless US Rev0"
        )
    return {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha256": sha256,
    }


def _slice_snes(rom: bytes, start: int, end_exclusive: int) -> bytes:
    start_offset = snes_hirom_to_file(start)
    end_offset = snes_hirom_to_file(end_exclusive)
    if end_offset <= start_offset:
        raise FocusWeaponAuxBoundaryAuditError(
            "bounded SNES extent does not map forward"
        )
    return rom[start_offset:end_offset]


def _region_observation(rom: bytes, spec: RegionSpec) -> dict[str, Any]:
    observed_sha256 = _sha256_bytes(
        _slice_snes(rom, spec.start, spec.end_exclusive)
    )
    if observed_sha256 != spec.expected_sha256:
        raise FocusWeaponAuxBoundaryAuditError(
            f"bounded region bytes drifted: {spec.name}"
        )
    return {
        "name": spec.name,
        "label": spec.label,
        "evidence_level": "verified-static",
        "extent": {
            "snes_start": _hex6(spec.start),
            "snes_end_exclusive": _hex6(spec.end_exclusive),
            "entry_count": spec.entry_count,
            "entry_width": spec.entry_width,
        },
        "observed_sha256": observed_sha256,
    }


def _preimage_observation(
    rom: bytes,
    spec: PreimageSpec,
) -> dict[str, Any]:
    observed_sha256 = _sha256_bytes(
        _slice_snes(rom, spec.start, spec.end_exclusive)
    )
    if observed_sha256 != spec.expected_sha256:
        raise FocusWeaponAuxBoundaryAuditError(
            f"bounded preimage bytes drifted: {spec.name}"
        )
    return {
        "name": spec.name,
        "evidence_level": "verified-static",
        "extent": {
            "snes_start": _hex6(spec.start),
            "snes_end_exclusive": _hex6(spec.end_exclusive),
            "length": spec.end_exclusive - spec.start,
        },
        "observed_sha256": observed_sha256,
    }


def _observe_boundary_offsets(rom: bytes) -> list[dict[str, str]]:
    offset_region = _region_map()["attack_animation_package_offsets"]
    table = _slice_snes(
        rom,
        offset_region.start,
        offset_region.end_exclusive,
    )
    result: list[dict[str, str]] = []
    for selector_id, expected in enumerate(BOUNDARY_OFFSETS):
        start = selector_id * 2
        observed = int.from_bytes(table[start : start + 2], "little")
        if observed != expected:
            raise FocusWeaponAuxBoundaryAuditError(
                f"attack package boundary offset drifted: "
                f"{_hex2(selector_id)}"
            )
        result.append(
            {
                "selector_id": _hex2(selector_id),
                "stored_offset": _hex4(observed),
                "package_snes_start": _hex6(0xCD0000 + observed),
            }
        )
    return result


def _observe_enemy_selector_reference_counts(
    rom: bytes,
) -> list[dict[str, str | int]]:
    enemy_region = _region_map()["enemy_attack_animation_records"]
    records = _slice_snes(
        rom,
        enemy_region.start,
        enemy_region.end_exclusive,
    )
    if len(records) != enemy_region.entry_count * enemy_region.entry_width:
        raise FocusWeaponAuxBoundaryAuditError(
            "enemy Attack-animation record extent drifted"
        )
    observed_counts = Counter(records[:: enemy_region.entry_width])
    result: list[dict[str, str | int]] = []
    for selector_id, expected_count in enumerate(
        ENEMY_SELECTOR_REFERENCE_COUNTS
    ):
        observed_count = observed_counts[selector_id]
        if observed_count != expected_count:
            raise FocusWeaponAuxBoundaryAuditError(
                "enemy Attack-animation selector reference count drifted: "
                f"{_hex2(selector_id)}"
            )
        result.append(
            {
                "selector_id": _hex2(selector_id),
                "record_count": observed_count,
            }
        )
    return result


def audit_rom(
    rom: bytes,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return only bounded hashes, geometry, addresses, and owners."""
    if contract is None:
        contract = load_reference_contract()
    else:
        _validate_reference_contract(contract)
    rom_identity = validate_canonical_rom(rom)
    _validate_spec_geometry()

    regions = [_region_observation(rom, spec) for spec in REGION_SPECS]
    preimages = [
        _preimage_observation(rom, spec) for spec in PREIMAGE_SPECS
    ]
    boundary_offsets = _observe_boundary_offsets(rom)
    selector_reference_counts = _observe_enemy_selector_reference_counts(rom)
    expected_offsets = contract["attack_package_resolution"][
        "boundary_offsets"
    ]
    if boundary_offsets != expected_offsets:
        raise FocusWeaponAuxBoundaryAuditError(
            "observed boundary-offset report drifted"
        )
    expected_counts = contract["attack_package_resolution"][
        "enemy_attack_selector_reference_counts"
    ]
    if selector_reference_counts != expected_counts:
        raise FocusWeaponAuxBoundaryAuditError(
            "observed enemy selector reference-count report drifted"
        )

    return {
        "schema": SCHEMA,
        "version": 1,
        "evidence_level": "verified-static",
        "rom": rom_identity,
        "reference_contract": {
            "path": (
                "references/"
                "schala_focus_weapon_aux_adapter_boundaries.json"
            ),
            "size": REFERENCE_SIZE,
            "sha256": REFERENCE_SHA256,
        },
        "regions": regions,
        "bounded_preimages": preimages,
        "consumer_geometry": {
            "palette": copy.deepcopy(contract["palette_consumers"]),
            "weapon_audio": copy.deepcopy(
                contract["weapon_audio_consumers"]
            ),
            "attack_package_resolution": {
                key: copy.deepcopy(value)
                for key, value in contract[
                    "attack_package_resolution"
                ].items()
                if key
                not in {
                    "boundary_offsets",
                    "enemy_attack_selector_reference_counts",
                }
            },
        },
        "boundary_offsets": boundary_offsets,
        "enemy_attack_selector_reference_counts": (
            selector_reference_counts
        ),
        "focus_lookup_collisions": copy.deepcopy(
            contract["focus_lookup_collisions"]
        ),
        "conclusion": {
            "expanded_palette_adapter_required": True,
            "expanded_swing_sfx_adapter_required": True,
            "expanded_hit_sfx_adapter_required": True,
            "expanded_palette_payload_bank_adapter_required": True,
            "reachable_enemy_attack_package_collision_proved": True,
            "canonical_in_place_write_approved": False,
            "allocation_or_hook_approved": False,
            "source_only_descriptor_bound": False,
            "rom_save_state_trace_mutation_performed": False,
            "patch_rom_or_output_file_emitted": False,
        },
        "limitations": list(contract["limitations"]),
    }


def audit_rom_path(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise FocusWeaponAuxBoundaryAuditError(
                f"ROM input is not a regular file: {path}"
            )
        if path.stat().st_size != CANONICAL_ROM_SIZE:
            raise FocusWeaponAuxBoundaryAuditError(
                f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
            )
        rom = path.read_bytes()
    except FocusWeaponAuxBoundaryAuditError:
        raise
    except OSError as exc:
        raise FocusWeaponAuxBoundaryAuditError(
            f"cannot read ROM input: {path}"
        ) from exc
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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit_rom_path(args.rom)
    except (
        FocusWeaponAuxBoundaryAuditError,
        OSError,
        ValueError,
    ) as exc:
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
