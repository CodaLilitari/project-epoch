#!/usr/bin/env python3
"""Read-only audit of Schala Focus Pulse action/presentation boundaries.

The audit accepts only the pinned headerless Chrono Trigger US Rev0 ROM.  It
checks source-declared table extents, their SHA-256 preimages, collision
geometry, and bounded selector facts.  It prints hashes, addresses, geometry,
and the documented IDs needed to explain those collisions.  It never emits
table bytes and has no ROM, patch, save, state, trace, or output-file writer.
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
REFERENCE_PATH = (
    ROOT / "references" / "schala_focus_pulse_adapter_boundaries.json"
)
REFERENCE_SIZE: Final = 9_754
REFERENCE_SHA256: Final = (
    "544ae648957407e2992e1e780f5831e5"
    "5243a4cb88413727269bda40ce605318"
)

CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)
SCHEMA: Final = "project-epoch-schala-focus-pulse-boundary-audit-v1"
REFERENCE_SCHEMA: Final = (
    "project-epoch-schala-focus-pulse-adapter-boundaries-v1"
)

LOGICAL_PC_ID: Final = 0x07
FOCUS_ACTION_ID: Final = 0x90
FOCUS_WEAPON_IDS: Final = (0xE8, 0xE9, 0xEA, 0xEB)
FIRST_EXTENSION_SELECTORS: Final = (0x13, 0x14, 0x15)


class FocusPulseBoundaryAuditError(RuntimeError):
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
class WeaponCollisionSpec:
    weapon_id: int
    lookup_start: int
    lookup_end_exclusive: int
    owner_first_record_index: int
    owner_first_record_byte_offset: int


REGION_SPECS: Final = (
    RegionSpec(
        "character_action_records",
        "CharTechIdTables",
        0xCC1BEB,
        0xCC213F,
        124,
        11,
        "8ad6d247d379a78c5a1711a8bd1c11f122aecfe7a4bb43f983a3c2a35ea3d383",
    ),
    RegionSpec(
        "tech_property_records",
        "TechProperty_Rec0",
        0xCC213F,
        0xCC249F,
        72,
        12,
        "ea34414fb3cf715612b8ed8519c190bf9cd522b46af1aaf5737901c1aeec8815",
    ),
    RegionSpec(
        "pc_attack_selector_families",
        "PcAttackAnimIdsA_DATA8_CD4007_PcAttackAnimIdsB",
        0xCD4000,
        0xCD4015,
        21,
        1,
        "89372c122381484720d5abfc94e040a27089e31578a1a0bbb29cd85566167ff9",
    ),
    RegionSpec(
        "weapon_attack_config_records",
        "normal_Attack_weapon_config",
        0xCD4015,
        0xCD45A6,
        95,
        15,
        "7e02fa2b4c77937e8f4655d840852bce0f4f0eead78f735ca4411b1a4331dd5d",
    ),
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
        "normal_attack_animation_offsets",
        "DATA8_CD5EC6",
        0xCD5EC6,
        0xCD5EF0,
        21,
        2,
        "f603c4f7413d2cfe48d7459687f511133ebcfc8f5f0d1a31d5b11d89f3e63256",
    ),
    RegionSpec(
        "tech_animation_pointer_table",
        "TechAnimPtrTable",
        0xCD5EF0,
        0xCD5FF0,
        128,
        2,
        "074a9bca7aaa630085654200634002e8f3c0f251a5c3874a5b1c1237d713a4d1",
    ),
    RegionSpec(
        "normal_attack_graphics_pointers",
        "PointersUnknownCompressedDataL",
        0xD10000,
        0xD10060,
        48,
        2,
        "034bd29b6397df535cc62d650a3a124c62b0ac91203c5b6bf213b1e9d0d18865",
    ),
    RegionSpec(
        "normal_attack_ce_animation_offsets",
        "UNREACH_CD64B0",
        0xCD64B0,
        0xCD656E,
        95,
        2,
        "5faeac58df3154c7ca2ee0ab8fadd88ca3ace0b342ada39ef4e631493202d462",
    ),
    RegionSpec(
        "normal_attack_aux_frame_offsets",
        "DATA8_CD686E",
        0xCD686E,
        0xCD692C,
        95,
        2,
        "c117c513f3b6f45d60c7a023fc198fe2c429e1939ab7b1d8d427b6ffb2f26c25",
    ),
)

WEAPON_COLLISION_SPECS: Final = (
    WeaponCollisionSpec(0xE8, 0xCD4DAD, 0xCD4DBC, 193, 1),
    WeaponCollisionSpec(0xE9, 0xCD4DBC, 0xCD4DCB, 195, 4),
    WeaponCollisionSpec(0xEA, 0xCD4DCB, 0xCD4DDA, 198, 1),
    WeaponCollisionSpec(0xEB, 0xCD4DDA, 0xCD4DE9, 200, 4),
)

ACTION_DIRECT_CONSUMERS: Final = (
    0xC1CB55,
    0xC1CB6E,
    0xC1CB87,
    0xC1CBA0,
    0xC1D546,
    0xC1D593,
    0xC1D5A3,
    0xC1D5CD,
    0xC1D61F,
    0xC1D694,
    0xC1D6A4,
    0xC1D732,
    0xC1F482,
    0xC1F5B7,
)

WEAPON_BRANCHES: Final = (
    (
        "noncritical_9930_zero",
        0,
        (0xC14399, 0xC143A0, 0xC143A7, 0xC143AE, 0xC143B5),
    ),
    (
        "noncritical_9930_nonzero",
        5,
        (0xC143CD, 0xC143D4, 0xC143DB, 0xC143E2, 0xC143E9),
    ),
    (
        "critical_ae9b_bit80",
        10,
        (0xC14360, 0xC14367, 0xC1436E, 0xC14375, 0xC1437C),
    ),
)

BRANCH_DESTINATIONS: Final = (
    0x7E987A,
    0x7E987B,
    0x7E987E,
    0x7E9881,
    0x7E9884,
)

SELECTOR_SOURCE_CONSUMERS: Final = (0xC143C4, 0xC143F8, 0xC1438B)

FANOUT_SPECS: Final = (
    (0x7E987E, "normal_attack_graphics_pointers", 0xC14408, 0x7E987F),
    (0x7E9884, "normal_attack_ce_animation_offsets", 0xC14420, 0x7E9885),
    (0x7E9881, "normal_attack_aux_frame_offsets", 0xC14414, 0x7E9882),
)

CONCLUSIONS: Final = (
    "Raw Focus Pulse action ID 90 cannot index the vanilla 124-record "
    "character-action table.",
    "Focus weapon IDs E8-EB cannot index the vanilla 95-record "
    "equipped-weapon Attack-config table.",
    "The three logical-PC-07 Attack branches cannot receive three new "
    "contiguous normal-Attack selectors in place.",
    "The action record, weapon Attack config, selector resolver, and any new "
    "downstream assets require named expanded descriptors and adapters.",
)

LIMITATIONS: Final = (
    "This audit does not execute logical PC 07 or Focus Pulse.",
    "Selector IDs 13 and 14 are inside the canonical resolver extent but are "
    "not declared free by this audit.",
    "The five branch fields are identified only by their WRAM destinations "
    "and direct fanout; their complete semantic formats remain unproved.",
    "This audit does not approve hooks, expanded allocations, ROM mutation, "
    "patches, or production installation.",
)


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FocusPulseBoundaryAuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _hex2(value: int) -> str:
    return f"{value:02X}"


def _hex6(value: int) -> str:
    return f"{value:06X}"


def _parse_hex(value: Any, width: int, label: str) -> int:
    if (
        not isinstance(value, str)
        or len(value) != width
        or value.upper() != value
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise FocusPulseBoundaryAuditError(
            f"{label} is not {width}-digit uppercase hex"
        )
    return int(value, 16)


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    if set(value) != expected:
        raise FocusPulseBoundaryAuditError(f"{label} keys drifted")


def snes_hirom_to_file(address: int) -> int:
    """Map a canonical $C0-$FF HiROM address into the 4 MiB image."""
    if not 0xC00000 <= address <= 0xFFFFFF:
        raise FocusPulseBoundaryAuditError(
            f"address is outside canonical C0-FF HiROM: ${address:06X}"
        )
    return address & 0x3FFFFF


def _region_map() -> dict[str, RegionSpec]:
    result = {spec.name: spec for spec in REGION_SPECS}
    if len(result) != len(REGION_SPECS):
        raise FocusPulseBoundaryAuditError("duplicate built-in region name")
    return result


def _validate_spec_geometry() -> None:
    regions = _region_map()
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
            raise FocusPulseBoundaryAuditError(
                f"built-in region geometry drifted: {spec.name}"
            )

    action = regions["character_action_records"]
    properties = regions["tech_property_records"]
    action_lookup = action.start + FOCUS_ACTION_ID * action.entry_width
    if (
        action_lookup != 0xCC221B
        or action.start <= action_lookup < action.end_exclusive
        or not properties.start <= action_lookup < properties.end_exclusive
        or (action_lookup - properties.start) // properties.entry_width != 18
        or (action_lookup - properties.start) % properties.entry_width != 4
    ):
        raise FocusPulseBoundaryAuditError(
            "built-in Focus action collision geometry drifted"
        )

    configs = regions["weapon_attack_config_records"]
    enemy = regions["enemy_attack_animation_records"]
    for spec in WEAPON_COLLISION_SPECS:
        actual = configs.start + spec.weapon_id * configs.entry_width
        if (
            actual != spec.lookup_start
            or spec.lookup_end_exclusive
            != spec.lookup_start + configs.entry_width
            or not enemy.start <= spec.lookup_start < enemy.end_exclusive
            or not enemy.start < spec.lookup_end_exclusive <= enemy.end_exclusive
            or (spec.lookup_start - enemy.start) // enemy.entry_width
            != spec.owner_first_record_index
            or (spec.lookup_start - enemy.start) % enemy.entry_width
            != spec.owner_first_record_byte_offset
        ):
            raise FocusPulseBoundaryAuditError(
                f"built-in weapon collision drifted: {_hex2(spec.weapon_id)}"
            )

    resolver = regions["normal_attack_animation_offsets"]
    tech_pointers = regions["tech_animation_pointer_table"]
    for selector in FIRST_EXTENSION_SELECTORS:
        lookup = resolver.start + selector * resolver.entry_width
        if selector < 0x15:
            if not resolver.start <= lookup < resolver.end_exclusive:
                raise FocusPulseBoundaryAuditError(
                    "built-in in-extent selector geometry drifted"
                )
        elif lookup != resolver.end_exclusive or lookup != tech_pointers.start:
            raise FocusPulseBoundaryAuditError(
                "built-in selector collision geometry drifted"
            )

    if (
        len(WEAPON_BRANCHES) != 3
        or {offset for _, offset, _ in WEAPON_BRANCHES} != {0, 5, 10}
        or any(len(consumers) != 5 for _, _, consumers in WEAPON_BRANCHES)
        or len(BRANCH_DESTINATIONS) != 5
    ):
        raise FocusPulseBoundaryAuditError(
            "built-in weapon branch geometry drifted"
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
            "focus_action_collision",
            "weapon_attack_config",
            "normal_attack_selector_boundary",
            "normal_attack_downstream_fanout",
            "verified_static_conclusions",
            "limitations",
        },
        "reference root",
    )
    if (
        contract.get("schema") != REFERENCE_SCHEMA
        or contract.get("version") != 1
        or contract.get("evidence_level") != "verified-static"
    ):
        raise FocusPulseBoundaryAuditError("reference identity drifted")

    scope = contract.get("scope")
    if isinstance(scope, Mapping):
        _require_exact_keys(
            scope,
            {
                "logical_pc_id",
                "basic_action_id",
                "focus_weapon_ids",
                "operation",
                "rom_access",
                "output_policy",
                "rom_save_state_trace_mutation",
                "patch_rom_or_output_file_emission",
            },
            "reference scope",
        )
    if (
        not isinstance(scope, Mapping)
        or scope.get("logical_pc_id") != _hex2(LOGICAL_PC_ID)
        or scope.get("basic_action_id") != _hex2(FOCUS_ACTION_ID)
        or scope.get("focus_weapon_ids")
        != [_hex2(value) for value in FOCUS_WEAPON_IDS]
        or scope.get("operation")
        != "Focus Pulse action and normal-Attack presentation boundary audit"
        or scope.get("rom_access") != "read-only"
        or scope.get("rom_save_state_trace_mutation") is not False
        or scope.get("patch_rom_or_output_file_emission") is not False
        or "never table bytes" not in str(scope.get("output_policy"))
    ):
        raise FocusPulseBoundaryAuditError("reference safety scope drifted")

    rom = contract.get("canonical_rom")
    if isinstance(rom, Mapping):
        _require_exact_keys(
            rom,
            {"identity", "size", "sha256", "mapping"},
            "reference canonical ROM",
        )
    if (
        not isinstance(rom, Mapping)
        or rom.get("identity") != "Chrono Trigger US Rev0 headerless"
        or rom.get("size") != CANONICAL_ROM_SIZE
        or rom.get("sha256") != CANONICAL_ROM_SHA256
        or rom.get("mapping")
        != "C0-FF HiROM address masked to file offset 000000-3FFFFF"
    ):
        raise FocusPulseBoundaryAuditError("reference ROM identity drifted")

    tables = contract.get("regions")
    if not isinstance(tables, list) or len(tables) != len(REGION_SPECS):
        raise FocusPulseBoundaryAuditError("reference region set drifted")
    for row, spec in zip(tables, REGION_SPECS, strict=True):
        if isinstance(row, Mapping):
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
            not isinstance(row, Mapping)
            or row.get("name") != spec.name
            or row.get("label") != spec.label
            or _parse_hex(
                row.get("snes_start"), 6, f"{spec.name}.snes_start"
            )
            != spec.start
            or _parse_hex(
                row.get("snes_end_exclusive"),
                6,
                f"{spec.name}.snes_end_exclusive",
            )
            != spec.end_exclusive
            or row.get("entry_count") != spec.entry_count
            or row.get("entry_width") != spec.entry_width
            or row.get("expected_bytes_sha256") != spec.expected_sha256
        ):
            raise FocusPulseBoundaryAuditError(
                f"reference region contract drifted: {spec.name}"
            )

    action = contract.get("focus_action_collision")
    action_collision = action.get("collision") if isinstance(action, Mapping) else None
    if isinstance(action, Mapping):
        _require_exact_keys(
            action,
            {
                "raw_action_id",
                "index_formula",
                "lookup_snes_address",
                "declared_action_extent_contains_lookup",
                "collision",
                "first_direct_consumer_pc",
                "all_character_action_direct_consumer_pcs",
            },
            "reference Focus action collision",
        )
    if isinstance(action_collision, Mapping):
        _require_exact_keys(
            action_collision,
            {
                "owner_region",
                "owner_record_index",
                "owner_record_byte_offset",
            },
            "reference Focus action collision owner",
        )
    if (
        not isinstance(action, Mapping)
        or action.get("raw_action_id") != _hex2(FOCUS_ACTION_ID)
        or action.get("index_formula") != "CC1BEB + action_id * 11"
        or action.get("lookup_snes_address") != "CC221B"
        or action.get("declared_action_extent_contains_lookup") is not False
        or not isinstance(action_collision, Mapping)
        or action_collision.get("owner_region") != "tech_property_records"
        or action_collision.get("owner_record_index") != 18
        or action_collision.get("owner_record_byte_offset") != 4
        or action.get("first_direct_consumer_pc") != "C1D546"
        or action.get("all_character_action_direct_consumer_pcs")
        != [_hex6(value) for value in ACTION_DIRECT_CONSUMERS]
    ):
        raise FocusPulseBoundaryAuditError(
            "reference Focus action collision drifted"
        )

    weapon = contract.get("weapon_attack_config")
    geometry = (
        weapon.get("record_geometry") if isinstance(weapon, Mapping) else None
    )
    branches = geometry.get("branches") if isinstance(geometry, Mapping) else None
    collisions = (
        weapon.get("focus_weapon_collisions")
        if isinstance(weapon, Mapping)
        else None
    )
    if isinstance(weapon, Mapping):
        _require_exact_keys(
            weapon,
            {
                "index_formula",
                "equipped_weapon_source",
                "index_setup_pc_span",
                "record_geometry",
                "focus_weapon_collisions",
            },
            "reference weapon config",
        )
    if isinstance(geometry, Mapping):
        _require_exact_keys(
            geometry,
            {
                "record_width",
                "branch_count",
                "branch_width",
                "branches",
                "branch_destinations",
            },
            "reference weapon config geometry",
        )
    if (
        not isinstance(weapon, Mapping)
        or weapon.get("index_formula")
        != "CD4015 + equipped_weapon_id * 15"
        or weapon.get("equipped_weapon_source") != "7E1C48 + actor_slot * 5"
        or weapon.get("index_setup_pc_span") != "C14341-C14357"
        or not isinstance(geometry, Mapping)
        or geometry.get("record_width") != 15
        or geometry.get("branch_count") != 3
        or geometry.get("branch_width") != 5
        or geometry.get("branch_destinations")
        != [_hex6(value) for value in BRANCH_DESTINATIONS]
        or not isinstance(branches, list)
        or len(branches) != 3
        or not isinstance(collisions, list)
        or len(collisions) != 4
    ):
        raise FocusPulseBoundaryAuditError(
            "reference weapon config geometry drifted"
        )
    for row, expected in zip(branches, WEAPON_BRANCHES, strict=True):
        name, offset, consumers = expected
        if isinstance(row, Mapping):
            _require_exact_keys(
                row,
                {"name", "record_offset", "direct_consumer_pcs"},
                f"reference weapon branch {name}",
            )
        if (
            not isinstance(row, Mapping)
            or row.get("name") != name
            or row.get("record_offset") != offset
            or row.get("direct_consumer_pcs")
            != [_hex6(value) for value in consumers]
        ):
            raise FocusPulseBoundaryAuditError(
                f"reference weapon branch drifted: {name}"
            )
    for row, expected in zip(collisions, WEAPON_COLLISION_SPECS, strict=True):
        if isinstance(row, Mapping):
            _require_exact_keys(
                row,
                {
                    "weapon_id",
                    "lookup_snes_start",
                    "lookup_snes_end_exclusive",
                    "owner_region",
                    "owner_first_record_index",
                    "owner_first_record_byte_offset",
                },
                "reference Focus weapon collision",
            )
        if (
            not isinstance(row, Mapping)
            or row.get("weapon_id") != _hex2(expected.weapon_id)
            or row.get("lookup_snes_start") != _hex6(expected.lookup_start)
            or row.get("lookup_snes_end_exclusive")
            != _hex6(expected.lookup_end_exclusive)
            or row.get("owner_region") != "enemy_attack_animation_records"
            or row.get("owner_first_record_index")
            != expected.owner_first_record_index
            or row.get("owner_first_record_byte_offset")
            != expected.owner_first_record_byte_offset
        ):
            raise FocusPulseBoundaryAuditError(
                "reference Focus weapon collision drifted"
            )

    selector = contract.get("normal_attack_selector_boundary")
    extension = (
        selector.get("first_three_id_extension")
        if isinstance(selector, Mapping)
        else None
    )
    if isinstance(selector, Mapping):
        _require_exact_keys(
            selector,
            {
                "selector_source_region",
                "selector_source_direct_consumer_pcs",
                "vanilla_selector_min",
                "vanilla_selector_max",
                "vanilla_unique_selector_count",
                "resolver_region",
                "resolver_direct_consumer_pc",
                "required_pc07_branch_selector_count",
                "first_three_id_extension",
            },
            "reference selector boundary",
        )
    if (
        not isinstance(selector, Mapping)
        or selector.get("selector_source_region")
        != "pc_attack_selector_families"
        or selector.get("selector_source_direct_consumer_pcs")
        != [_hex6(value) for value in SELECTOR_SOURCE_CONSUMERS]
        or selector.get("vanilla_selector_min") != "00"
        or selector.get("vanilla_selector_max") != "12"
        or selector.get("vanilla_unique_selector_count") != 19
        or selector.get("resolver_region")
        != "normal_attack_animation_offsets"
        or selector.get("resolver_direct_consumer_pc") != "C1442C"
        or selector.get("required_pc07_branch_selector_count") != 3
        or not isinstance(extension, list)
        or len(extension) != 3
    ):
        raise FocusPulseBoundaryAuditError(
            "reference selector boundary drifted"
        )
    resolver = _region_map()["normal_attack_animation_offsets"]
    for row, selector_id in zip(extension, FIRST_EXTENSION_SELECTORS, strict=True):
        lookup = resolver.start + selector_id * resolver.entry_width
        in_extent = selector_id < 0x15
        if isinstance(row, Mapping):
            expected_keys = {
                "selector_id",
                "lookup_snes_address",
                "in_declared_resolver_extent",
                "classification",
            }
            if not in_extent:
                expected_keys.add("collision")
            _require_exact_keys(
                row,
                expected_keys,
                f"reference extension selector {_hex2(selector_id)}",
            )
        if (
            not isinstance(row, Mapping)
            or row.get("selector_id") != _hex2(selector_id)
            or row.get("lookup_snes_address") != _hex6(lookup)
            or row.get("in_declared_resolver_extent") is not in_extent
            or row.get("classification")
            != ("unproven-not-free" if in_extent else "fallthrough-collision")
        ):
            raise FocusPulseBoundaryAuditError(
                "reference extension selector drifted"
            )
        if not in_extent:
            collision = row.get("collision")
            if isinstance(collision, Mapping):
                _require_exact_keys(
                    collision,
                    {"owner_region", "owner_record_index"},
                    "reference selector collision owner",
                )
            if (
                not isinstance(collision, Mapping)
                or collision.get("owner_region")
                != "tech_animation_pointer_table"
                or collision.get("owner_record_index") != 0
            ):
                raise FocusPulseBoundaryAuditError(
                    "reference selector collision owner drifted"
                )

    fanout = contract.get("normal_attack_downstream_fanout")
    if not isinstance(fanout, list) or len(fanout) != len(FANOUT_SPECS):
        raise FocusPulseBoundaryAuditError("reference fanout set drifted")
    for row, expected in zip(fanout, FANOUT_SPECS, strict=True):
        source, region, consumer, destination = expected
        if isinstance(row, Mapping):
            _require_exact_keys(
                row,
                {
                    "source_config_destination",
                    "region",
                    "direct_consumer_pc",
                    "resolved_destination",
                },
                f"reference fanout {region}",
            )
        if (
            not isinstance(row, Mapping)
            or row.get("source_config_destination") != _hex6(source)
            or row.get("region") != region
            or row.get("direct_consumer_pc") != _hex6(consumer)
            or row.get("resolved_destination") != _hex6(destination)
        ):
            raise FocusPulseBoundaryAuditError(
                f"reference fanout drifted: {region}"
            )

    if contract.get("verified_static_conclusions") != list(CONCLUSIONS):
        raise FocusPulseBoundaryAuditError("reference conclusions drifted")
    if contract.get("limitations") != list(LIMITATIONS):
        raise FocusPulseBoundaryAuditError("reference limitations drifted")
    _validate_spec_geometry()


def load_reference_contract(
    path: Path = REFERENCE_PATH,
) -> Mapping[str, Any]:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise FocusPulseBoundaryAuditError(
            f"cannot read pinned reference contract: {path}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise FocusPulseBoundaryAuditError("reference contract size drifted")
    if _sha256_bytes(source) != REFERENCE_SHA256:
        raise FocusPulseBoundaryAuditError(
            "reference contract SHA-256 drifted"
        )
    try:
        value = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except FocusPulseBoundaryAuditError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FocusPulseBoundaryAuditError(
            "reference contract is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise FocusPulseBoundaryAuditError(
            "reference contract root is not object"
        )
    _validate_reference_contract(value)
    return value


def validate_canonical_rom(rom: bytes) -> dict[str, str | int]:
    if len(rom) != CANONICAL_ROM_SIZE:
        raise FocusPulseBoundaryAuditError(
            f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if sha1 != CANONICAL_ROM_SHA1 or sha256 != CANONICAL_ROM_SHA256:
        raise FocusPulseBoundaryAuditError(
            "ROM hash does not match headerless US Rev0"
        )
    return {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha256": sha256,
    }


def _slice_region(rom: bytes, spec: RegionSpec) -> bytes:
    start = snes_hirom_to_file(spec.start)
    end = snes_hirom_to_file(spec.end_exclusive)
    return rom[start:end]


def audit_rom(
    rom: bytes,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return only bounded hashes, geometry, addresses, and documented IDs."""
    if contract is None:
        contract = load_reference_contract()
    else:
        _validate_reference_contract(contract)
    rom_identity = validate_canonical_rom(rom)
    _validate_spec_geometry()
    regions = _region_map()

    observations: list[dict[str, Any]] = []
    for spec in REGION_SPECS:
        observed = _slice_region(rom, spec)
        observed_sha256 = _sha256_bytes(observed)
        if observed_sha256 != spec.expected_sha256:
            raise FocusPulseBoundaryAuditError(
                f"bounded region bytes drifted: {spec.name}"
            )
        observations.append(
            {
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
        )

    selector_source = _slice_region(
        rom, regions["pc_attack_selector_families"]
    )
    selector_set = set(selector_source)
    if (
        selector_set != set(range(0x13))
        or min(selector_set) != 0
        or max(selector_set) != 0x12
        or len(selector_set) != 19
    ):
        raise FocusPulseBoundaryAuditError(
            "vanilla selector-set fact drifted"
        )

    action = contract["focus_action_collision"]
    weapon = contract["weapon_attack_config"]
    selector = contract["normal_attack_selector_boundary"]
    fanout = contract["normal_attack_downstream_fanout"]

    return {
        "schema": SCHEMA,
        "version": 1,
        "evidence_level": "verified-static",
        "rom": rom_identity,
        "reference_contract": {
            "path": "references/schala_focus_pulse_adapter_boundaries.json",
            "size": REFERENCE_SIZE,
            "sha256": REFERENCE_SHA256,
        },
        "regions": observations,
        "bounded_lookup_facts": {
            "focus_action_collision": {
                "raw_action_id": action["raw_action_id"],
                "lookup_snes_address": action["lookup_snes_address"],
                "declared_action_extent_contains_lookup": False,
                "collision": dict(action["collision"]),
                "first_direct_consumer_pc": action[
                    "first_direct_consumer_pc"
                ],
            },
            "focus_weapon_collisions": [
                dict(row) for row in weapon["focus_weapon_collisions"]
            ],
            "normal_attack_selectors": {
                "vanilla_selector_min": _hex2(min(selector_set)),
                "vanilla_selector_max": _hex2(max(selector_set)),
                "vanilla_unique_selector_count": len(selector_set),
                "required_pc07_branch_selector_count": selector[
                    "required_pc07_branch_selector_count"
                ],
                "first_three_id_extension": [
                    dict(row) for row in selector["first_three_id_extension"]
                ],
            },
        },
        "record_geometry_and_consumers": {
            "character_action_direct_consumer_pcs": list(
                action["all_character_action_direct_consumer_pcs"]
            ),
            "weapon_attack_config": {
                "index_setup_pc_span": weapon["index_setup_pc_span"],
                "record_geometry": dict(weapon["record_geometry"]),
            },
            "selector_source_direct_consumer_pcs": list(
                selector["selector_source_direct_consumer_pcs"]
            ),
            "selector_resolver_direct_consumer_pc": selector[
                "resolver_direct_consumer_pc"
            ],
            "normal_attack_downstream_fanout": [
                dict(row) for row in fanout
            ],
        },
        "conclusion": {
            "expanded_action_descriptor_required": True,
            "expanded_weapon_attack_config_required": True,
            "expanded_selector_resolver_required": True,
            "canonical_in_place_write_approved": False,
            "rom_save_state_trace_mutation_performed": False,
            "patch_rom_or_output_file_emitted": False,
        },
        "limitations": list(contract["limitations"]),
    }


def audit_rom_path(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise FocusPulseBoundaryAuditError(
                f"ROM input is not a regular file: {path}"
            )
        if path.stat().st_size != CANONICAL_ROM_SIZE:
            raise FocusPulseBoundaryAuditError(
                f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
            )
        rom = path.read_bytes()
    except FocusPulseBoundaryAuditError:
        raise
    except OSError as exc:
        raise FocusPulseBoundaryAuditError(
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit_rom_path(args.rom)
    except (FocusPulseBoundaryAuditError, OSError, ValueError) as exc:
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
