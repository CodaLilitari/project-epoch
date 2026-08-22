#!/usr/bin/env python3
"""Validate and pack Schala's original progression foundation.

The emitted 0x48-byte descriptor is a Project Epoch overlay format, not a
vanilla 0x50-byte character record. It deliberately leaves the still-unmapped
record bytes, experience binding, runtime stat recomputation, and ROM
allocation to later adapters.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import struct
from typing import Any, Iterable

import validate_schala_items as item_content


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "content"
    / "schala_progression_v0.json"
)

DESCRIPTOR_VERSION = 1
DESCRIPTOR_SIZE = 0x48
LOGICAL_PC_ID = 7
LEVEL_POLICY_MEDIAN_ACTIVE = 1
ELEMENT_SHADOW = 3
NO_ITEM = 0xFF
STAT_NAMES = (
    "power",
    "stamina",
    "speed",
    "hit",
    "evade",
    "magic",
    "magic_defense",
)
KNOWN_RUNTIME_GATES = {
    "record_byte_01_semantics",
    "record_byte_02_semantics",
    "shared_experience_curve_binding",
    "current_stat_recompute",
    "current_attack_and_defense_recompute",
    "expanded_growth_table_readers",
    "expanded_tp_table_reader",
    "recruitment_level_initializer",
    "equipment_record_adapters",
    "save_and_load_round_trip",
    "equal_level_balance_replay",
}


class ProgressionError(ValueError):
    """Raised when the original progression source or descriptor is invalid."""


@dataclasses.dataclass(frozen=True)
class ProgressionDescriptorV1:
    logical_pc_id: int
    level_policy: int
    minimum_level: int
    maximum_level: int
    fallback_level: int
    starting_learned_count: int
    starting_learned_mask: int
    basic_action_id: int
    element_id: int
    equipment_permission_mask: int
    flags: int
    base_hp: int
    base_mp: int
    base_stats: tuple[int, ...]
    hp_growth: tuple[int, ...]
    mp_growth: tuple[int, ...]
    stat_growth: tuple[int, ...]
    tp_step_costs: tuple[int, ...]
    starting_loadout: tuple[int, ...]
    initial_tp_to_next: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def load_content(path: pathlib.Path = SOURCE_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_content(value)
    return value


def _require_int(
    value: Any, field: str, minimum: int, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ProgressionError(
            f"{field} must be an integer from {minimum} through {maximum}"
        )
    return value


def _expected_learned_mask(count: int) -> int:
    if count == 0:
        return 0
    return (0xFF << (8 - count)) & 0xFF


def _flatten_growth_brackets(
    brackets: Any, field: str
) -> tuple[int, ...]:
    if not isinstance(brackets, list) or len(brackets) != 4:
        raise ProgressionError(f"{field} must contain four brackets")
    flattened: list[int] = []
    previous_cap = 0
    for index, bracket in enumerate(brackets):
        if not isinstance(bracket, dict) or set(bracket) != {
            "maximum_level",
            "gain_per_level",
        }:
            raise ProgressionError(
                f"{field}[{index}] must contain maximum_level and "
                "gain_per_level"
            )
        cap = _require_int(
            bracket["maximum_level"],
            f"{field}[{index}].maximum_level",
            1,
            99,
        )
        gain = _require_int(
            bracket["gain_per_level"],
            f"{field}[{index}].gain_per_level",
            1,
            0xFF,
        )
        if cap <= previous_cap:
            raise ProgressionError(f"{field} level caps must increase")
        previous_cap = cap
        flattened.extend((cap, gain))
    if previous_cap != 99:
        raise ProgressionError(f"{field} must end at level 99")
    return tuple(flattened)


def _validate_provenance(content: dict[str, Any]) -> None:
    provenance = content.get("provenance")
    if not isinstance(provenance, dict):
        raise ProgressionError("provenance must be an object")
    for field in (
        "rom_or_npc_data_imported",
        "copied_vanilla_record",
        "copied_vanilla_growth_row",
    ):
        if provenance.get(field) is not False:
            raise ProgressionError(f"{field} must be false")
    basis = provenance.get("authoring_basis")
    if not isinstance(basis, list) or not basis:
        raise ProgressionError("authoring_basis must be non-empty")


def validate_content(content: dict[str, Any]) -> None:
    if content.get("schema_version") != 1:
        raise ProgressionError("schema_version must be 1")
    if content.get("content_id") != "project_epoch_schala_progression_v0":
        raise ProgressionError("unexpected content_id")
    if content.get("logical_pc_id") != LOGICAL_PC_ID:
        raise ProgressionError("logical_pc_id must be 7")
    if content.get("content_origin") != "project-epoch-original":
        raise ProgressionError("content_origin must be project-epoch-original")
    if content.get("rom_encoding_status") != "authoring-only-unmapped":
        raise ProgressionError("progression must remain authoring-only-unmapped")
    _validate_provenance(content)

    policy = content.get("recruitment_level_policy")
    if not isinstance(policy, dict):
        raise ProgressionError("recruitment_level_policy must be an object")
    if policy.get("mode") != "median_active_party_level":
        raise ProgressionError("unsupported recruitment level policy")
    minimum = _require_int(policy.get("minimum"), "minimum level", 1, 99)
    maximum = _require_int(policy.get("maximum"), "maximum level", 1, 99)
    fallback = _require_int(policy.get("fallback"), "fallback level", 1, 99)
    if minimum > maximum or not minimum <= fallback <= maximum:
        raise ProgressionError("level policy bounds are inconsistent")

    level_one = content.get("level_one")
    if not isinstance(level_one, dict):
        raise ProgressionError("level_one must be an object")
    _require_int(level_one.get("hp"), "level-one HP", 1, 999)
    _require_int(level_one.get("mp"), "level-one MP", 1, 99)
    stats = level_one.get("stats")
    if not isinstance(stats, dict) or tuple(stats) != STAT_NAMES:
        raise ProgressionError(
            "level-one stats must use the canonical seven-field order"
        )
    for name in STAT_NAMES:
        maximum_value = 16 if name == "speed" else 99
        _require_int(stats[name], f"level-one {name}", 0, maximum_value)

    growth = content.get("growth")
    if not isinstance(growth, dict):
        raise ProgressionError("growth must be an object")
    _flatten_growth_brackets(growth.get("hp_brackets"), "hp_brackets")
    _flatten_growth_brackets(growth.get("mp_brackets"), "mp_brackets")
    stat_growth = growth.get("stats_per_100_levels")
    if not isinstance(stat_growth, dict) or tuple(stat_growth) != STAT_NAMES:
        raise ProgressionError(
            "stat growth must use the canonical seven-field order"
        )
    for name in STAT_NAMES:
        value = _require_int(
            stat_growth[name], f"{name} growth", 0, 0xFF
        )
        if name == "speed" and value != 0:
            raise ProgressionError("speed growth must remain zero")

    tech = content.get("single_tech_progression")
    if not isinstance(tech, dict):
        raise ProgressionError("single_tech_progression must be an object")
    count = _require_int(
        tech.get("starting_learned_count"), "starting learned count", 0, 8
    )
    mask = _require_int(
        tech.get("starting_learned_mask"), "starting learned mask", 0, 0xFF
    )
    if mask != _expected_learned_mask(count):
        raise ProgressionError(
            "starting learned mask must use the engine's high-bit-first order"
        )
    cumulative = tech.get("cumulative_tp_after_recruitment")
    steps = tech.get("engine_step_costs")
    if not isinstance(cumulative, list) or len(cumulative) != 8:
        raise ProgressionError("cumulative TP must contain eight values")
    if not isinstance(steps, list) or len(steps) != 8:
        raise ProgressionError("engine TP steps must contain eight values")
    cumulative_checked = [
        _require_int(value, f"cumulative TP {index}", 0, 0xFFFF)
        for index, value in enumerate(cumulative)
    ]
    steps_checked = [
        _require_int(value, f"engine TP step {index}", 0, 0xFFFF)
        for index, value in enumerate(steps)
    ]
    if any(cumulative_checked[index] != 0 for index in range(count)):
        raise ProgressionError("starting tech cumulative TP must be zero")
    for index in range(count + 1, 8):
        if cumulative_checked[index] <= cumulative_checked[index - 1]:
            raise ProgressionError(
                "post-recruitment cumulative TP must strictly increase"
            )
    expected_steps = [0] * count
    expected_steps.extend(
        cumulative_checked[index] - cumulative_checked[index - 1]
        for index in range(count, 8)
    )
    if steps_checked != expected_steps:
        raise ProgressionError(
            "engine TP steps must be the cumulative TP deltas"
        )

    loadout = content.get("starting_loadout")
    expected_loadout_keys = (
        "helmet_item_id",
        "armor_item_id",
        "weapon_item_id",
        "accessory_item_id",
    )
    if not isinstance(loadout, dict) or tuple(loadout) != expected_loadout_keys:
        raise ProgressionError(
            "starting loadout must use helmet/armor/weapon/accessory order"
        )
    for field, value in loadout.items():
        if value is not None:
            _require_int(value, field, 0, 0xFF)
    items = item_content.load_content()["items"]
    indexed_items = {entry["item_id"]: entry for entry in items}
    if loadout["weapon_item_id"] != 0xE8:
        raise ProgressionError("starting weapon must be the Glass Focus")
    if indexed_items[0xE8]["design_name"] != "Glass Focus":
        raise ProgressionError("item pack no longer maps $E8 to Glass Focus")
    if loadout["armor_item_id"] != 0xEC:
        raise ProgressionError("starting armor must be the Regent Mantle")
    if indexed_items[0xEC]["design_name"] != "Regent Mantle":
        raise ProgressionError(
            "item pack no longer maps $EC to Regent Mantle"
        )

    identity = content.get("runtime_identity")
    if not isinstance(identity, dict):
        raise ProgressionError("runtime_identity must be an object")
    if identity.get("basic_action_id") != 0x90:
        raise ProgressionError("basic action must be Focus Pulse $90")
    if identity.get("element") != "shadow":
        raise ProgressionError("Schala's v0 element must be Shadow")
    if identity.get("equipment_permission_mask") != 0x01:
        raise ProgressionError("Schala equipment mask must be bit $01")

    gates = content.get("runtime_gates")
    if (
        not isinstance(gates, list)
        or set(gates) != KNOWN_RUNTIME_GATES
        or len(gates) != len(KNOWN_RUNTIME_GATES)
    ):
        raise ProgressionError("runtime_gates must enumerate every known gate")


def descriptor_from_content(
    content: dict[str, Any],
) -> ProgressionDescriptorV1:
    validate_content(content)
    policy = content["recruitment_level_policy"]
    level_one = content["level_one"]
    growth = content["growth"]
    tech = content["single_tech_progression"]
    loadout = content["starting_loadout"]
    identity = content["runtime_identity"]
    return ProgressionDescriptorV1(
        logical_pc_id=content["logical_pc_id"],
        level_policy=LEVEL_POLICY_MEDIAN_ACTIVE,
        minimum_level=policy["minimum"],
        maximum_level=policy["maximum"],
        fallback_level=policy["fallback"],
        starting_learned_count=tech["starting_learned_count"],
        starting_learned_mask=tech["starting_learned_mask"],
        basic_action_id=identity["basic_action_id"],
        element_id=ELEMENT_SHADOW,
        equipment_permission_mask=identity["equipment_permission_mask"],
        flags=0,
        base_hp=level_one["hp"],
        base_mp=level_one["mp"],
        base_stats=tuple(level_one["stats"][name] for name in STAT_NAMES),
        hp_growth=_flatten_growth_brackets(
            growth["hp_brackets"], "hp_brackets"
        ),
        mp_growth=_flatten_growth_brackets(
            growth["mp_brackets"], "mp_brackets"
        ),
        stat_growth=tuple(
            growth["stats_per_100_levels"][name] for name in STAT_NAMES
        ),
        tp_step_costs=tuple(tech["engine_step_costs"]),
        starting_loadout=tuple(
            NO_ITEM if loadout[field] is None else loadout[field]
            for field in (
                "helmet_item_id",
                "armor_item_id",
                "weapon_item_id",
                "accessory_item_id",
            )
        ),
        initial_tp_to_next=tech["engine_step_costs"][
            tech["starting_learned_count"]
        ],
    )


def validate_descriptor(value: ProgressionDescriptorV1) -> None:
    for field in (
        "logical_pc_id",
        "level_policy",
        "minimum_level",
        "maximum_level",
        "fallback_level",
        "starting_learned_count",
        "starting_learned_mask",
        "basic_action_id",
        "element_id",
        "equipment_permission_mask",
        "flags",
        "base_mp",
    ):
        _require_int(getattr(value, field), field, 0, 0xFF)
    _require_int(value.base_hp, "base_hp", 1, 999)
    _require_int(value.initial_tp_to_next, "initial_tp_to_next", 0, 0xFFFF)
    if value.logical_pc_id != LOGICAL_PC_ID:
        raise ProgressionError("descriptor logical ID must be 7")
    if value.level_policy != LEVEL_POLICY_MEDIAN_ACTIVE:
        raise ProgressionError("unknown level policy")
    if (
        value.minimum_level > value.maximum_level
        or not value.minimum_level
        <= value.fallback_level
        <= value.maximum_level
    ):
        raise ProgressionError("descriptor level bounds are inconsistent")
    if value.starting_learned_mask != _expected_learned_mask(
        value.starting_learned_count
    ):
        raise ProgressionError("descriptor learned mask/count disagree")
    if value.basic_action_id != 0x90:
        raise ProgressionError("descriptor basic action must be $90")
    if value.element_id != ELEMENT_SHADOW:
        raise ProgressionError("descriptor element must be Shadow")
    if value.equipment_permission_mask != 0x01:
        raise ProgressionError("descriptor equipment mask must be $01")
    if value.flags:
        raise ProgressionError("descriptor v1 flags are reserved")
    for field, expected_length in (
        ("base_stats", 7),
        ("hp_growth", 8),
        ("mp_growth", 8),
        ("stat_growth", 7),
        ("tp_step_costs", 8),
        ("starting_loadout", 4),
    ):
        values = getattr(value, field)
        if len(values) != expected_length:
            raise ProgressionError(
                f"{field} must contain {expected_length} values"
            )
    for field in (
        "base_stats",
        "hp_growth",
        "mp_growth",
        "stat_growth",
        "starting_loadout",
    ):
        for index, item in enumerate(getattr(value, field)):
            _require_int(item, f"{field}[{index}]", 0, 0xFF)
    for index, item in enumerate(value.tp_step_costs):
        _require_int(item, f"tp_step_costs[{index}]", 0, 0xFFFF)
    if value.initial_tp_to_next != value.tp_step_costs[
        value.starting_learned_count
    ]:
        raise ProgressionError("initial TP does not match learned count")


def encode_descriptor(value: ProgressionDescriptorV1) -> bytes:
    validate_descriptor(value)
    encoded = bytearray(DESCRIPTOR_SIZE)
    encoded[0x00] = DESCRIPTOR_VERSION
    encoded[0x01:0x0C] = bytes(
        (
            value.logical_pc_id,
            value.level_policy,
            value.minimum_level,
            value.maximum_level,
            value.fallback_level,
            value.starting_learned_count,
            value.starting_learned_mask,
            value.basic_action_id,
            value.element_id,
            value.equipment_permission_mask,
            value.flags,
        )
    )
    struct.pack_into("<HH", encoded, 0x0C, value.base_hp, value.base_mp)
    encoded[0x10:0x17] = bytes(value.base_stats)
    encoded[0x18:0x20] = bytes(value.hp_growth)
    encoded[0x20:0x28] = bytes(value.mp_growth)
    encoded[0x28:0x2F] = bytes(value.stat_growth)
    struct.pack_into("<8H", encoded, 0x30, *value.tp_step_costs)
    encoded[0x40:0x44] = bytes(value.starting_loadout)
    struct.pack_into("<H", encoded, 0x44, value.initial_tp_to_next)
    return bytes(encoded)


def decode_descriptor(encoded: bytes) -> ProgressionDescriptorV1:
    if len(encoded) != DESCRIPTOR_SIZE:
        raise ProgressionError(
            f"descriptor must be exactly 0x{DESCRIPTOR_SIZE:X} bytes"
        )
    if encoded[0] != DESCRIPTOR_VERSION:
        raise ProgressionError("unknown descriptor version")
    if encoded[0x17] or encoded[0x2F] or any(encoded[0x46:0x48]):
        raise ProgressionError("descriptor reserved bytes must be zero")
    value = ProgressionDescriptorV1(
        logical_pc_id=encoded[0x01],
        level_policy=encoded[0x02],
        minimum_level=encoded[0x03],
        maximum_level=encoded[0x04],
        fallback_level=encoded[0x05],
        starting_learned_count=encoded[0x06],
        starting_learned_mask=encoded[0x07],
        basic_action_id=encoded[0x08],
        element_id=encoded[0x09],
        equipment_permission_mask=encoded[0x0A],
        flags=encoded[0x0B],
        base_hp=struct.unpack_from("<H", encoded, 0x0C)[0],
        base_mp=struct.unpack_from("<H", encoded, 0x0E)[0],
        base_stats=tuple(encoded[0x10:0x17]),
        hp_growth=tuple(encoded[0x18:0x20]),
        mp_growth=tuple(encoded[0x20:0x28]),
        stat_growth=tuple(encoded[0x28:0x2F]),
        tp_step_costs=struct.unpack_from("<8H", encoded, 0x30),
        starting_loadout=tuple(encoded[0x40:0x44]),
        initial_tp_to_next=struct.unpack_from("<H", encoded, 0x44)[0],
    )
    validate_descriptor(value)
    return value


def select_recruitment_level(
    active_party_levels: Iterable[int], descriptor: ProgressionDescriptorV1
) -> int:
    validate_descriptor(descriptor)
    levels = list(active_party_levels)
    if not levels:
        return descriptor.fallback_level
    if len(levels) > 3:
        raise ProgressionError("active party may contain at most three levels")
    checked = sorted(
        _require_int(value, "active party level", 1, 99)
        for value in levels
    )
    median = checked[len(checked) // 2]
    return min(
        descriptor.maximum_level,
        max(descriptor.minimum_level, median),
    )


def _growth_total(level: int, flattened: tuple[int, ...]) -> int:
    total = 0
    for gained_level in range(2, level + 1):
        for index in range(0, len(flattened), 2):
            if gained_level <= flattened[index]:
                total += flattened[index + 1]
                break
        else:
            raise ProgressionError("growth table does not cover level")
    return total


def project_level(
    level: int, descriptor: ProgressionDescriptorV1
) -> dict[str, Any]:
    validate_descriptor(descriptor)
    level = _require_int(level, "level", 1, 99)
    hp = min(
        999, descriptor.base_hp + _growth_total(level, descriptor.hp_growth)
    )
    mp = min(
        99, descriptor.base_mp + _growth_total(level, descriptor.mp_growth)
    )
    stats: dict[str, int] = {}
    for index, name in enumerate(STAT_NAMES):
        if name == "speed":
            value = descriptor.base_stats[index]
        else:
            value = descriptor.base_stats[index] + (
                descriptor.stat_growth[index] * (level - 1) // 100
            )
        stats[name] = min(99, value)
    return {"level": level, "hp": hp, "mp": mp, "stats": stats}


def manifest(content: dict[str, Any]) -> dict[str, Any]:
    descriptor = descriptor_from_content(content)
    encoded = encode_descriptor(descriptor)
    return {
        "schema_version": 1,
        "content_id": content["content_id"],
        "source_path": SOURCE_PATH.relative_to(ROOT).as_posix(),
        "source_normalized_sha256": sha256(normalized_json_bytes(content)),
        "descriptor_version": DESCRIPTOR_VERSION,
        "descriptor_size": DESCRIPTOR_SIZE,
        "descriptor_sha256": sha256(encoded),
        "format": "project-epoch-progression-overlay-v1",
        "vanilla_character_record": False,
        "rom_installable": False,
        "runtime_gates": content["runtime_gates"],
        "level_projections": {
            str(level): project_level(level, descriptor)
            for level in (30, 35, 37, 45, 50, 99)
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=SOURCE_PATH,
        help="original progression JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        help="optional ignored directory for descriptor and manifest",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = load_content(args.source)
    descriptor = encode_descriptor(descriptor_from_content(content))
    report = manifest(content)
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "schala_progression_overlay_v1.bin").write_bytes(
            descriptor
        )
        (
            args.output_dir / "schala_progression_manifest_v0.json"
        ).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
