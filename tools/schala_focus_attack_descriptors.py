#!/usr/bin/env python3
"""Freeze unbound Project Epoch PC-07 Attack and Focus visual descriptors.

These two binary layouts are source-side contracts only. They bind
Project Epoch-owned identities while rejecting every runtime value, pointer,
allocation, or ROM-installable state. No ROM is opened and no binary artifact
is written.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Any


TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import schala_command_layout as commands
import validate_schala_items as items


DESCRIPTOR_VERSION = 1
UNBOUND_STATE = 0

PC_ATTACK_DESCRIPTOR_SIZE = 0x10
FOCUS_VISUAL_DESCRIPTOR_SIZE = 0x18
FOCUS_VISUAL_COUNT = 4
FOCUS_VISUAL_TABLE_SIZE = (
    FOCUS_VISUAL_DESCRIPTOR_SIZE * FOCUS_VISUAL_COUNT
)

SCHALA_PC_ID = 0x07
FOCUS_PULSE_ACTION_ID = 0x90
FIRST_FOCUS_ITEM_ID = 0xE8
LAST_FOCUS_ITEM_ID = 0xEB
MAX_U24 = 0xFFFFFF

ROOT = TOOLS_DIR.parent
PC_ATTACK_BOUNDARY_PATH = (
    ROOT / "references" / "pc7_attack_adapter_boundaries.json"
)
FOCUS_BOUNDARY_PATH = (
    ROOT / "references" / "schala_focus_pulse_adapter_boundaries.json"
)
PC_ATTACK_BOUNDARY_SHA256 = (
    "f89bbfce542bb16944b62bc00822e7f8348acb794bedd149f38e7dd02c78caf7"
)
FOCUS_BOUNDARY_SHA256 = (
    "544ae648957407e2992e1e780f5831e55243a4cb88413727269bda40ce605318"
)

FOCUS_BRANCH_ORDER = (
    "noncritical_9930_zero",
    "noncritical_9930_nonzero",
    "critical_ae9b_bit80",
)
FOCUS_WRAM_DESTINATION_ORDER = (
    "7E987A",
    "7E987B",
    "7E987E",
    "7E9881",
    "7E9884",
)


class FocusDescriptorError(ValueError):
    """Raised when an unbound descriptor violates the frozen schema."""


@dataclasses.dataclass(frozen=True)
class PcAttackDescriptorV1:
    version: int
    logical_pc_id: int
    basic_action_id: int
    binding_state: int
    approach_c14a48_value: int
    selector_9877_noncritical_9930_zero: int
    selector_9877_noncritical_9930_nonzero: int
    selector_9877_critical_ae9b_bit80: int
    expanded_action_record_ptr: int
    expanded_selector_binding_ptr: int
    reserved: bytes = bytes(2)


@dataclasses.dataclass(frozen=True)
class FocusWeaponVisualDescriptorV1:
    version: int
    item_id: int
    focus_visual_id: int
    binding_state: int
    noncritical_9930_zero_values: bytes
    noncritical_9930_nonzero_values: bytes
    critical_ae9b_bit80_values: bytes
    expanded_downstream_binding_ptr: int
    reserved: bytes = bytes(2)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FocusDescriptorError(
                f"duplicate JSON key in boundary contract: {key}"
            )
        result[key] = value
    return result


def _load_boundary_contract(
    path: pathlib.Path,
    expected_sha256: str,
) -> tuple[dict[str, Any], str]:
    try:
        encoded = path.read_bytes()
    except OSError as exc:
        raise FocusDescriptorError(
            f"cannot read boundary contract: {path}"
        ) from exc
    actual_sha256 = sha256(encoded)
    if actual_sha256 != expected_sha256:
        raise FocusDescriptorError(
            f"boundary contract hash drifted: {path.name}"
        )
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FocusDescriptorError(
            f"invalid boundary contract JSON: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise FocusDescriptorError(
            f"boundary contract root must be an object: {path.name}"
        )
    return value, actual_sha256


def validate_boundary_contracts() -> dict[str, str]:
    pc_attack, pc_attack_hash = _load_boundary_contract(
        PC_ATTACK_BOUNDARY_PATH,
        PC_ATTACK_BOUNDARY_SHA256,
    )
    focus, focus_hash = _load_boundary_contract(
        FOCUS_BOUNDARY_PATH,
        FOCUS_BOUNDARY_SHA256,
    )

    if (
        pc_attack.get("schema")
        != "project-epoch-pc7-attack-adapter-boundaries-v1"
        or pc_attack.get("version") != 1
        or pc_attack.get("evidence_level") != "verified-static"
    ):
        raise FocusDescriptorError("PC $07 Attack boundary schema drifted")
    pc_scope = pc_attack.get("scope")
    if not isinstance(pc_scope, dict) or (
        pc_scope.get("logical_pc_id") != "07"
        or pc_scope.get("rom_access") != "read-only"
        or pc_scope.get("rom_save_state_mutation") is not False
        or pc_scope.get("patch_or_rom_emission") is not False
    ):
        raise FocusDescriptorError("PC $07 Attack boundary scope drifted")
    pc_tables = pc_attack.get("tables")
    expected_pc_tables = (
        ("basic_attack_action_ids", "C1BFFF"),
        ("attack_approach_policy", "C14A44"),
        ("pc_attack_anim_ids_a", "C143C4"),
        ("pc_attack_anim_ids_pathfind_success", "C143F8"),
        ("pc_attack_anim_ids_b_critical", "C1438B"),
    )
    if not isinstance(pc_tables, list) or tuple(
        (
            value.get("name"),
            value.get("consumer_instruction_pc"),
        )
        for value in pc_tables
        if isinstance(value, dict)
    ) != expected_pc_tables:
        raise FocusDescriptorError("PC $07 Attack boundary tables drifted")

    if (
        focus.get("schema")
        != "project-epoch-schala-focus-pulse-adapter-boundaries-v1"
        or focus.get("version") != 1
        or focus.get("evidence_level") != "verified-static"
    ):
        raise FocusDescriptorError("Focus boundary schema drifted")
    focus_scope = focus.get("scope")
    if not isinstance(focus_scope, dict) or (
        focus_scope.get("logical_pc_id") != "07"
        or focus_scope.get("basic_action_id") != "90"
        or focus_scope.get("focus_weapon_ids")
        != ["E8", "E9", "EA", "EB"]
        or focus_scope.get("rom_access") != "read-only"
        or focus_scope.get("rom_save_state_trace_mutation") is not False
        or focus_scope.get("patch_rom_or_output_file_emission") is not False
    ):
        raise FocusDescriptorError("Focus boundary scope drifted")
    action_collision = focus.get("focus_action_collision")
    if (
        not isinstance(action_collision, dict)
        or action_collision.get("raw_action_id") != "90"
    ):
        raise FocusDescriptorError("Focus action collision drifted")
    weapon_config = focus.get("weapon_attack_config")
    if not isinstance(weapon_config, dict):
        raise FocusDescriptorError("Focus weapon-config boundary is missing")
    geometry = weapon_config.get("record_geometry")
    if not isinstance(geometry, dict) or (
        geometry.get("record_width") != 15
        or geometry.get("branch_count") != 3
        or geometry.get("branch_width") != 5
        or geometry.get("branch_destinations")
        != list(FOCUS_WRAM_DESTINATION_ORDER)
    ):
        raise FocusDescriptorError("Focus weapon-config geometry drifted")
    branches = geometry.get("branches")
    if not isinstance(branches, list) or tuple(
        value.get("name")
        for value in branches
        if isinstance(value, dict)
    ) != FOCUS_BRANCH_ORDER or tuple(
        value.get("record_offset")
        for value in branches
        if isinstance(value, dict)
    ) != (0, 5, 10) or any(
        not isinstance(value, dict)
        or not isinstance(value.get("direct_consumer_pcs"), list)
        or len(value["direct_consumer_pcs"]) != 5
        for value in branches
    ):
        raise FocusDescriptorError("Focus branch geometry drifted")
    collisions = weapon_config.get("focus_weapon_collisions")
    if not isinstance(collisions, list) or [
        value.get("weapon_id")
        for value in collisions
        if isinstance(value, dict)
    ] != ["E8", "E9", "EA", "EB"]:
        raise FocusDescriptorError("Focus weapon collision set drifted")
    selector_boundary = focus.get("normal_attack_selector_boundary")
    if (
        not isinstance(selector_boundary, dict)
        or selector_boundary.get("required_pc07_branch_selector_count")
        != 3
    ):
        raise FocusDescriptorError("Focus selector boundary drifted")

    return {
        "pc7_attack_adapter_boundaries_sha256": pc_attack_hash,
        "schala_focus_pulse_adapter_boundaries_sha256": focus_hash,
    }


def _require_u8(value: int, field: str) -> None:
    if type(value) is not int or not 0 <= value <= 0xFF:
        raise FocusDescriptorError(f"{field} must fit in one byte")


def _require_u24(value: int, field: str) -> None:
    if type(value) is not int or not 0 <= value <= MAX_U24:
        raise FocusDescriptorError(f"{field} must fit in three bytes")


def _require_zero(value: int, field: str) -> None:
    if value != 0:
        raise FocusDescriptorError(
            f"{field} must remain zero in the unbound v1 schema"
        )


def _require_zero_bytes(value: bytes, size: int, field: str) -> None:
    if not isinstance(value, bytes) or len(value) != size:
        raise FocusDescriptorError(f"{field} must be exactly {size} bytes")
    if any(value):
        raise FocusDescriptorError(
            f"{field} must remain zero in the unbound v1 schema"
        )


def validate_pc_attack_descriptor(value: PcAttackDescriptorV1) -> None:
    for field in (
        "version",
        "logical_pc_id",
        "basic_action_id",
        "binding_state",
        "approach_c14a48_value",
        "selector_9877_noncritical_9930_zero",
        "selector_9877_noncritical_9930_nonzero",
        "selector_9877_critical_ae9b_bit80",
    ):
        _require_u8(getattr(value, field), field)
    _require_u24(
        value.expanded_action_record_ptr,
        "expanded_action_record_ptr",
    )
    _require_u24(
        value.expanded_selector_binding_ptr,
        "expanded_selector_binding_ptr",
    )

    if value.version != DESCRIPTOR_VERSION:
        raise FocusDescriptorError("unknown PC Attack descriptor version")
    if value.logical_pc_id != SCHALA_PC_ID:
        raise FocusDescriptorError("PC Attack descriptor must target PC $07")
    if value.basic_action_id != FOCUS_PULSE_ACTION_ID:
        raise FocusDescriptorError(
            "PC Attack descriptor must bind Focus Pulse action $90"
        )
    if value.binding_state != UNBOUND_STATE:
        raise FocusDescriptorError(
            "PC Attack descriptor must remain explicitly unbound"
        )

    _require_zero(value.approach_c14a48_value, "approach_c14a48_value")
    _require_zero(
        value.selector_9877_noncritical_9930_zero,
        "selector_9877_noncritical_9930_zero",
    )
    _require_zero(
        value.selector_9877_noncritical_9930_nonzero,
        "selector_9877_noncritical_9930_nonzero",
    )
    _require_zero(
        value.selector_9877_critical_ae9b_bit80,
        "selector_9877_critical_ae9b_bit80",
    )
    _require_zero(
        value.expanded_action_record_ptr,
        "expanded_action_record_ptr",
    )
    _require_zero(
        value.expanded_selector_binding_ptr,
        "expanded_selector_binding_ptr",
    )
    _require_zero_bytes(value.reserved, 2, "reserved")


def encode_pc_attack_descriptor(value: PcAttackDescriptorV1) -> bytes:
    validate_pc_attack_descriptor(value)
    encoded = bytearray(PC_ATTACK_DESCRIPTOR_SIZE)
    encoded[0x00] = value.version
    encoded[0x01] = value.logical_pc_id
    encoded[0x02] = value.basic_action_id
    encoded[0x03] = value.binding_state
    encoded[0x04] = value.approach_c14a48_value
    encoded[0x05] = value.selector_9877_noncritical_9930_zero
    encoded[0x06] = value.selector_9877_noncritical_9930_nonzero
    encoded[0x07] = value.selector_9877_critical_ae9b_bit80
    encoded[0x08:0x0B] = value.expanded_action_record_ptr.to_bytes(
        3, "little"
    )
    encoded[0x0B:0x0E] = value.expanded_selector_binding_ptr.to_bytes(
        3, "little"
    )
    encoded[0x0E:0x10] = value.reserved
    return bytes(encoded)


def decode_pc_attack_descriptor(encoded: bytes) -> PcAttackDescriptorV1:
    if len(encoded) != PC_ATTACK_DESCRIPTOR_SIZE:
        raise FocusDescriptorError(
            "PC Attack descriptor must be exactly "
            f"0x{PC_ATTACK_DESCRIPTOR_SIZE:X} bytes"
        )
    value = PcAttackDescriptorV1(
        version=encoded[0x00],
        logical_pc_id=encoded[0x01],
        basic_action_id=encoded[0x02],
        binding_state=encoded[0x03],
        approach_c14a48_value=encoded[0x04],
        selector_9877_noncritical_9930_zero=encoded[0x05],
        selector_9877_noncritical_9930_nonzero=encoded[0x06],
        selector_9877_critical_ae9b_bit80=encoded[0x07],
        expanded_action_record_ptr=int.from_bytes(
            encoded[0x08:0x0B], "little"
        ),
        expanded_selector_binding_ptr=int.from_bytes(
            encoded[0x0B:0x0E], "little"
        ),
        reserved=encoded[0x0E:0x10],
    )
    validate_pc_attack_descriptor(value)
    return value


def validate_focus_visual_descriptor(
    value: FocusWeaponVisualDescriptorV1,
) -> None:
    for field in (
        "version",
        "item_id",
        "focus_visual_id",
        "binding_state",
    ):
        _require_u8(getattr(value, field), field)
    _require_u24(
        value.expanded_downstream_binding_ptr,
        "expanded_downstream_binding_ptr",
    )

    if value.version != DESCRIPTOR_VERSION:
        raise FocusDescriptorError("unknown Focus visual descriptor version")
    if not 0 <= value.focus_visual_id < FOCUS_VISUAL_COUNT:
        raise FocusDescriptorError("Focus visual ID must be 0 through 3")
    if value.item_id != FIRST_FOCUS_ITEM_ID + value.focus_visual_id:
        raise FocusDescriptorError(
            "Focus visual ID must map contiguously to item $E8-$EB"
        )
    if value.binding_state != UNBOUND_STATE:
        raise FocusDescriptorError(
            "Focus visual descriptor must remain explicitly unbound"
        )

    _require_zero_bytes(
        value.noncritical_9930_zero_values,
        5,
        "noncritical_9930_zero_values",
    )
    _require_zero_bytes(
        value.noncritical_9930_nonzero_values,
        5,
        "noncritical_9930_nonzero_values",
    )
    _require_zero_bytes(
        value.critical_ae9b_bit80_values,
        5,
        "critical_ae9b_bit80_values",
    )
    _require_zero(
        value.expanded_downstream_binding_ptr,
        "expanded_downstream_binding_ptr",
    )
    _require_zero_bytes(value.reserved, 2, "reserved")


def encode_focus_visual_descriptor(
    value: FocusWeaponVisualDescriptorV1,
) -> bytes:
    validate_focus_visual_descriptor(value)
    encoded = bytearray(FOCUS_VISUAL_DESCRIPTOR_SIZE)
    encoded[0x00] = value.version
    encoded[0x01] = value.item_id
    encoded[0x02] = value.focus_visual_id
    encoded[0x03] = value.binding_state
    encoded[0x04:0x09] = value.noncritical_9930_zero_values
    encoded[0x09:0x0E] = value.noncritical_9930_nonzero_values
    encoded[0x0E:0x13] = value.critical_ae9b_bit80_values
    encoded[0x13:0x16] = (
        value.expanded_downstream_binding_ptr.to_bytes(3, "little")
    )
    encoded[0x16:0x18] = value.reserved
    return bytes(encoded)


def decode_focus_visual_descriptor(
    encoded: bytes,
) -> FocusWeaponVisualDescriptorV1:
    if len(encoded) != FOCUS_VISUAL_DESCRIPTOR_SIZE:
        raise FocusDescriptorError(
            "Focus visual descriptor must be exactly "
            f"0x{FOCUS_VISUAL_DESCRIPTOR_SIZE:X} bytes"
        )
    value = FocusWeaponVisualDescriptorV1(
        version=encoded[0x00],
        item_id=encoded[0x01],
        focus_visual_id=encoded[0x02],
        binding_state=encoded[0x03],
        noncritical_9930_zero_values=encoded[0x04:0x09],
        noncritical_9930_nonzero_values=encoded[0x09:0x0E],
        critical_ae9b_bit80_values=encoded[0x0E:0x13],
        expanded_downstream_binding_ptr=int.from_bytes(
            encoded[0x13:0x16], "little"
        ),
        reserved=encoded[0x16:0x18],
    )
    validate_focus_visual_descriptor(value)
    return value


def validate_focus_visual_table(
    values: tuple[FocusWeaponVisualDescriptorV1, ...],
) -> None:
    if not isinstance(values, tuple):
        raise FocusDescriptorError(
            "Focus visual table must be an immutable tuple"
        )
    if len(values) != FOCUS_VISUAL_COUNT:
        raise FocusDescriptorError(
            "Focus visual table must contain exactly four records"
        )
    for value in values:
        validate_focus_visual_descriptor(value)
    if tuple(value.item_id for value in values) != tuple(
        range(FIRST_FOCUS_ITEM_ID, LAST_FOCUS_ITEM_ID + 1)
    ):
        raise FocusDescriptorError(
            "Focus visual table item order must be $E8-$EB"
        )
    if tuple(value.focus_visual_id for value in values) != tuple(
        range(FOCUS_VISUAL_COUNT)
    ):
        raise FocusDescriptorError(
            "Focus visual table IDs must be ordered 0 through 3"
        )


def encode_focus_visual_table(
    values: tuple[FocusWeaponVisualDescriptorV1, ...],
) -> bytes:
    validate_focus_visual_table(values)
    encoded = b"".join(
        encode_focus_visual_descriptor(value) for value in values
    )
    if len(encoded) != FOCUS_VISUAL_TABLE_SIZE:
        raise FocusDescriptorError("unexpected Focus visual table size")
    return encoded


def decode_focus_visual_table(
    encoded: bytes,
) -> tuple[FocusWeaponVisualDescriptorV1, ...]:
    if len(encoded) != FOCUS_VISUAL_TABLE_SIZE:
        raise FocusDescriptorError(
            "Focus visual table must be exactly "
            f"0x{FOCUS_VISUAL_TABLE_SIZE:X} bytes"
        )
    values = tuple(
        decode_focus_visual_descriptor(
            encoded[
                index
                * FOCUS_VISUAL_DESCRIPTOR_SIZE : (index + 1)
                * FOCUS_VISUAL_DESCRIPTOR_SIZE
            ]
        )
        for index in range(FOCUS_VISUAL_COUNT)
    )
    validate_focus_visual_table(values)
    return values


def _focus_pulse_command() -> commands.CommandSpec:
    commands.validate_layout()
    matches = tuple(
        command
        for command in commands.COMMANDS
        if command.design_name == "Focus Pulse"
    )
    if len(matches) != 1:
        raise FocusDescriptorError(
            "command source must define exactly one Focus Pulse"
        )
    command = matches[0]
    if (
        command.action_id != FOCUS_PULSE_ACTION_ID
        or command.kind != "basic"
        or command.participants != (SCHALA_PC_ID,)
    ):
        raise FocusDescriptorError("Focus Pulse command identity drifted")
    return command


def _focus_weapon_items() -> tuple[dict[str, Any], ...]:
    content = items.load_content()
    items.validate_content(content)
    source_items = content.get("items")
    if not isinstance(source_items, list):
        raise FocusDescriptorError("item source must contain an item list")
    weapons = tuple(
        item
        for item in source_items
        if isinstance(item, dict) and item.get("logical_class") == "weapon"
    )
    if len(weapons) != FOCUS_VISUAL_COUNT:
        raise FocusDescriptorError(
            "item source must define exactly four Focus weapons"
        )
    if any(type(item.get("item_id")) is not int for item in weapons):
        raise FocusDescriptorError(
            "Focus weapon item IDs must be strict integers"
        )
    if any(
        type(item.get("focus_visual_id")) is not int for item in weapons
    ):
        raise FocusDescriptorError(
            "Focus visual IDs must be strict integers"
        )
    expected_ids = tuple(
        range(FIRST_FOCUS_ITEM_ID, LAST_FOCUS_ITEM_ID + 1)
    )
    if tuple(item.get("item_id") for item in weapons) != expected_ids:
        raise FocusDescriptorError("Focus weapon item IDs drifted")
    if tuple(item.get("focus_visual_id") for item in weapons) != tuple(
        range(FOCUS_VISUAL_COUNT)
    ):
        raise FocusDescriptorError("Focus visual IDs drifted")
    if any(item.get("native_binding") is not None for item in weapons):
        raise FocusDescriptorError(
            "Focus weapon authoring source unexpectedly gained a binding"
        )
    return weapons


def build_unbound_descriptors() -> tuple[
    PcAttackDescriptorV1,
    tuple[FocusWeaponVisualDescriptorV1, ...],
]:
    validate_boundary_contracts()
    command = _focus_pulse_command()
    weapons = _focus_weapon_items()
    attack = PcAttackDescriptorV1(
        version=DESCRIPTOR_VERSION,
        logical_pc_id=SCHALA_PC_ID,
        basic_action_id=command.action_id,
        binding_state=UNBOUND_STATE,
        approach_c14a48_value=0,
        selector_9877_noncritical_9930_zero=0,
        selector_9877_noncritical_9930_nonzero=0,
        selector_9877_critical_ae9b_bit80=0,
        expanded_action_record_ptr=0,
        expanded_selector_binding_ptr=0,
        reserved=bytes(2),
    )
    visuals = tuple(
        FocusWeaponVisualDescriptorV1(
            version=DESCRIPTOR_VERSION,
            item_id=item["item_id"],
            focus_visual_id=item["focus_visual_id"],
            binding_state=UNBOUND_STATE,
            noncritical_9930_zero_values=bytes(5),
            noncritical_9930_nonzero_values=bytes(5),
            critical_ae9b_bit80_values=bytes(5),
            expanded_downstream_binding_ptr=0,
            reserved=bytes(2),
        )
        for item in weapons
    )
    validate_pc_attack_descriptor(attack)
    for visual in visuals:
        validate_focus_visual_descriptor(visual)
    return attack, visuals


def manifest() -> dict[str, object]:
    boundary_hashes = validate_boundary_contracts()
    attack, visuals = build_unbound_descriptors()
    attack_bytes = encode_pc_attack_descriptor(attack)
    visual_table = encode_focus_visual_table(visuals)
    return {
        "schema": "project-epoch-schala-focus-attack-descriptors-v1",
        "version": DESCRIPTOR_VERSION,
        "evidence_level": "verified-static",
        "evidence_scope": (
            "Project Epoch identities and collision geometry only; "
            "the binary layouts remain proposals"
        ),
        "schema_status": "selected-source-only-proposal",
        "underlying_boundary_contracts": [
            "references/pc7_attack_adapter_boundaries.json",
            "references/schala_focus_pulse_adapter_boundaries.json",
        ],
        "underlying_boundary_contract_sha256": boundary_hashes,
        "authoring_sources": [
            "tools/schala_command_layout.py",
            "assets/source/schala/v0/content/schala_item_content_v0.json",
        ],
        "pc_attack": {
            "descriptor_size": len(attack_bytes),
            "descriptor_sha256": sha256(attack_bytes),
            "logical_pc_id": attack.logical_pc_id,
            "basic_action_id": attack.basic_action_id,
            "approach_value_bound": False,
            "selector_values_bound": False,
            "expanded_action_record_pointer_bound": False,
            "expanded_selector_binding_pointer_bound": False,
        },
        "focus_visuals": {
            "descriptor_size": FOCUS_VISUAL_DESCRIPTOR_SIZE,
            "descriptor_count": len(visuals),
            "table_size": len(visual_table),
            "table_sha256": sha256(visual_table),
            "visual_ids": [value.focus_visual_id for value in visuals],
            "item_ids": [value.item_id for value in visuals],
            "branch_order": list(FOCUS_BRANCH_ORDER),
            "wram_destination_order": list(
                FOCUS_WRAM_DESTINATION_ORDER
            ),
            "branch_values_bound": False,
            "expanded_downstream_binding_pointers_bound": False,
        },
        "provenance": {
            "project_epoch_original_identity_data_only": True,
            "canonical_rom_accessed": False,
            "rom_bytes_imported": False,
            "npc_sprite_or_animation_bytes_imported": False,
            "copied_vanilla_records": False,
        },
        "allocation_status": "unbound",
        "runtime_use_policy": "reject-before-any-wram-write",
        "binary_files_emitted": False,
        "rom_installable": False,
    }


def main() -> None:
    print(json.dumps(manifest(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
