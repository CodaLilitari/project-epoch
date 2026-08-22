#!/usr/bin/env python3
"""Audit metadata needed to bind Schala's recruitment content to the engine.

The audit is intentionally non-extractive.  It validates the authored
dependency inventory, pins the reconstructed engine sources, and reads only
small canonical-ROM tables needed to prove dispatch targets and namespace
collisions.  Its report contains addresses, counts, hashes, and classifications
only; it never emits event scripts, dialogue, graphics, or source bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections.abc import ByteString


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "content"
    / "schala_recruitment_content_v0.json"
)
DISASSEMBLY_ROOT = ROOT / "references" / "ct_disassembly"

CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)
CONTENT_SHA256 = (
    "00c750b2f9be163c75d75af947d1ea2a2"
    "ee39d16adfc0640e9292ad487b66412"
)
PINNED_DISASSEMBLY_COMMIT = (
    "eeae27acdb6565e96d1d796a3d60792c250c0aa1"
)
PINNED_SOURCE_HASHES = {
    "bank_C0.asm": (
        "b5b209cd03ae430f095482a429798ee3"
        "600d97af3774841c069d8f9a071140b8"
    ),
    "bank_C1.asm": (
        "298ad8f0ef01097b1018e1cdd154a4e6"
        "3d52b6debaa1d94dd85ecf2b8aaa15aa"
    ),
    "bank_C2.asm": (
        "d96c0d9707d9150dbdb3ad7d995f7ae1"
        "35e87ebb6329691cab2eb86447611032"
    ),
    "bank_FF.asm": (
        "18f30c2a4f547722f30934bde43eb6a6"
        "38d9467aa064e21340aa2065ab71829e"
    ),
}

REQUIRED_BINDING_IDS = (
    "quest_entry_dispatch",
    "quest_unlock_flag",
    "anchor_counter",
    "ward_resolved_flag",
    "recruited_flag",
    "join_grant_guard_flag",
    "new_game_plus_context_query",
    "magus_presence_query",
    "party_capacity_query",
    "logical_pc_07_runtime_record",
    "logical_pc_07_roster_insert",
    "logical_pc_07_active_party_insert",
    "logical_pc_07_reserve_insert",
    "party_exchange_ui",
    "starting_tech_unlocks",
    "starting_loadout_inventory",
    "pendant_shard_inventory",
    "dialogue_text_storage",
    "dialogue_choice_dispatch",
    "silent_palace_map",
    "schala_event_object",
    "schala_original_field_sprite",
    "schala_original_battle_sprite",
    "schala_original_portraits",
    "guest_veil_demonstration",
    "save_sidecar_persistence",
    "new_game_plus_transfer",
    "scene_music",
    "scene_sound_effects",
)

# The classifications describe the result of this bounded audit, not installed
# bindings.  Every authoring JSON binding must remain null.
BINDING_CLASSIFICATIONS = {
    "quest_entry_dispatch": "primitive_proved_allocation_unmapped",
    "quest_unlock_flag": "sidecar_defined_runtime_adapter_required",
    "anchor_counter": "sidecar_defined_runtime_adapter_required",
    "ward_resolved_flag": "sidecar_defined_runtime_adapter_required",
    "recruited_flag": "sidecar_defined_runtime_adapter_required",
    "join_grant_guard_flag": "sidecar_defined_runtime_adapter_required",
    "new_game_plus_context_query": "loader_path_proved_adapter_required",
    "magus_presence_query": "event_primitive_proved",
    "party_capacity_query": "state_proved_no_semantic_event_primitive",
    "logical_pc_07_runtime_record": "candidate_defined_runtime_gates_open",
    "logical_pc_07_roster_insert": "event_primitive_proved_pc7_adapters_required",
    "logical_pc_07_active_party_insert": (
        "event_primitive_proved_open_slot_guard_required"
    ),
    "logical_pc_07_reserve_insert": (
        "event_primitive_proved_pc7_adapters_required"
    ),
    "party_exchange_ui": "launch_path_proved_pc7_menu_adapters_required",
    "starting_tech_unlocks": "storage_defined_semantic_adapter_required",
    "starting_loadout_inventory": "event_primitives_proved_item_adapters_required",
    "pendant_shard_inventory": "event_primitives_proved_item_adapters_required",
    "dialogue_text_storage": "renderer_path_proved_allocation_unmapped",
    "dialogue_choice_dispatch": "event_primitive_proved",
    "silent_palace_map": "loader_path_proved_original_data_unmapped",
    "schala_event_object": "object_path_proved_pc7_graphics_adapter_required",
    "schala_original_field_sprite": "original_source_partial_install_unmapped",
    "schala_original_battle_sprite": "original_source_partial_install_unmapped",
    "schala_original_portraits": "original_source_complete_install_unmapped",
    "guest_veil_demonstration": "battle_launch_proved_guest_cast_unmapped",
    "save_sidecar_persistence": "host_format_defined_runtime_hooks_required",
    "new_game_plus_transfer": "host_policy_defined_runtime_hook_required",
    "scene_music": "event_primitive_proved_selection_unmapped",
    "scene_sound_effects": "event_primitive_proved_selection_unmapped",
}

EVENT_COMMAND_TABLE_FILE = 0x005D6E
EXPECTED_EVENT_TARGETS = {
    0x12: 0x62DE,  # script-memory compare
    0x16: 0x63E6,  # event-memory conditional
    0x1A: 0x6568,  # choice-result branch
    0x48: 0x6792,  # absolute read
    0x4A: 0x67D7,  # absolute immediate write
    0x53: 0x693D,  # event-memory read
    0x56: 0x69A6,  # event-memory write
    0x65: 0x6B76,  # event-memory bit set
    0x71: 0x6C69,  # script-memory increment
    0x80: 0x421E,  # load PC only if joined
    0x81: 0x4476,  # load PC object
    0xB8: 0x3557,  # set dialogue table
    0xBB: 0x3570,  # automatic textbox
    0xC0: 0x3643,  # decision textbox
    0xC1: 0x35B5,  # top textbox
    0xC2: 0x35FC,  # bottom textbox
    0xC3: 0x36AA,  # decision textbox variant
    0xC8: 0x3757,  # overlay request / name-entry event handler
    0xC9: 0x3780,  # item test
    0xCA: 0x37B1,  # item add
    0xCB: 0x37E3,  # item remove
    0xCF: 0x388D,  # roster query
    0xD0: 0x38BE,  # party op 4 / reserve registration
    0xD2: 0x38E8,  # active-party query
    0xD3: 0x3919,  # active-party insertion
    0xD5: 0x3A68,  # equip item
    0xD8: 0x3A83,  # battle launch
    0xE0: 0x3AB7,  # location change
    0xE8: 0x3C11,  # sound effect
    0xEA: 0x3C2F,  # music
}

PARTY_OPERATION_TABLE_FILE = 0x028C5B
EXPECTED_PARTY_TARGETS = (
    0x8C75,
    0x8C79,
    0x8CA2,
    0x8CCF,
    0x8CE5,
    0x8CF7,
    0x8D05,
    0x8D45,
    0x8D63,
    0x8D6A,
    0x8D8F,
    0x8C5A,
    0x8E1E,
)

CHAR_PARTY_FLAG_TABLE_FILE = 0x3FF9BB
EXPECTED_CHAR_PARTY_FLAGS = bytes((0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01))
PC_NAME_ADDR_TABLE_FILE = 0x025FD8
EXPECTED_PC_NAME_ADDRS = (
    0x2C23,
    0x2C29,
    0x2C2F,
    0x2C35,
    0x2C3B,
    0x2C41,
    0x2C47,
    0x0000,
)
SAVE_REGION_TABLE_FILE = 0x3FFA7B
SAVE_REGION_TABLE_LENGTH = 0x28
EXPECTED_SAVE_REGION_TABLE_SHA256 = (
    "30dfb2fbcf65bb8a21f09a2f1048d061"
    "5cf9b5127b02db9e1a94ee66f453d12a"
)
NG_PLUS_LOADER_FILE = 0x3FFAED
NG_PLUS_LOADER_LENGTH = 0xFBD3 - 0xFAED
EXPECTED_NG_PLUS_LOADER_SHA256 = (
    "b61e4ce9bb771450419cdb7ef558af98"
    "180c20ab8bbc83d99f7ea9b142a3cd77"
)

SOURCE_ANCHORS = {
    "bank_C0.asm": (
        "EventScript_RunLocationInitScript:",
        "EventScript_CommandTable:",
        "Dialog_RenderRequest:",
        "EventCmd_OpenNameEntry:",
        "EventCmd_PartyReserveCheck:",
        "EventCmd_IfActivePartyMember:",
        "EventCmd_AddPartyMember:",
        "EventCmd_StartBattle:",
        "EventCmd_PlaySound:",
        "EventCmd_PlayMusic:",
        "Field_EnterPartySwapMenu:",
    ),
    "bank_C1.asm": (
        "Battle_InventoryGoldApiVec:",
        "Battle_Inv_AddItem:",
    ),
    "bank_C2.asm": (
        "MenuOverlay_Launch:",
        "Party_DispatchOp:",
        "Party_AddActiveCharacter:",
        "Party_CheckRosterCharacter:",
        "Party_MarkRosterInactive:",
        "NameEntry_CommitIfValid:",
        "NameEntry_SetupScreen:",
    ),
    "bank_FF.asm": (
        "CharPartyFlagTable = $FFF9BB",
        "SaveSlot_Write:",
        "SaveSlot_LoadRegions:",
        "Loc_FFFAED = $FFFAED",
    ),
}


class AuditError(RuntimeError):
    """Raised when a pinned input or metadata contract has drifted."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _u16(data: ByteString, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise AuditError(f"u16 read outside input at {offset:#x}")
    return data[offset] | (data[offset + 1] << 8)


def validate_content(path: pathlib.Path = CONTENT_PATH) -> dict[str, object]:
    encoded = path.read_bytes()
    digest = _sha256(encoded)
    if digest != CONTENT_SHA256:
        raise AuditError("recruitment content hash does not match pinned v0")
    content = json.loads(encoded)
    bindings = content.get("runtime_bindings")
    if not isinstance(bindings, list):
        raise AuditError("runtime_bindings is not a list")
    ids = tuple(binding.get("binding_id") for binding in bindings)
    if ids != REQUIRED_BINDING_IDS:
        raise AuditError("runtime binding inventory or order changed")
    for binding in bindings:
        binding_id = binding["binding_id"]
        if binding.get("mapping_status") != "unmapped":
            raise AuditError(f"{binding_id}: authoring mapping is no longer null")
        for field in ("engine_address", "event_opcode", "data_table", "encoded_value"):
            if binding.get(field) is not None:
                raise AuditError(f"{binding_id}: {field} must remain null")
    if set(BINDING_CLASSIFICATIONS) != set(REQUIRED_BINDING_IDS):
        raise AuditError("audit classifications do not cover all dependencies")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "binding_count": len(bindings),
        "null_binding_count": len(bindings),
    }


def validate_disassembly_sources() -> dict[str, object]:
    rows: dict[str, object] = {}
    for filename, expected_hash in PINNED_SOURCE_HASHES.items():
        path = DISASSEMBLY_ROOT / filename
        encoded = path.read_bytes()
        digest = _sha256(encoded)
        if digest != expected_hash:
            raise AuditError(f"{filename}: source hash drift")
        text = encoded.decode("utf-8")
        missing = [
            anchor for anchor in SOURCE_ANCHORS[filename] if anchor not in text
        ]
        if missing:
            raise AuditError(f"{filename}: missing source anchors: {missing}")
        rows[filename] = {
            "sha256": digest,
            "anchor_count": len(SOURCE_ANCHORS[filename]),
        }
    return {
        "commit": PINNED_DISASSEMBLY_COMMIT,
        "files": rows,
    }


def validate_canonical_rom(rom: bytes) -> dict[str, object]:
    if len(rom) != CANONICAL_ROM_SIZE:
        raise AuditError(
            f"expected ROM size {CANONICAL_ROM_SIZE:#x}, got {len(rom):#x}"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = _sha256(rom)
    if sha1 != CANONICAL_ROM_SHA1:
        raise AuditError("canonical ROM SHA-1 mismatch")
    if sha256 != CANONICAL_ROM_SHA256:
        raise AuditError("canonical ROM SHA-256 mismatch")
    return {"size": len(rom), "sha1": sha1, "sha256": sha256}


def audit_rom_metadata(rom: ByteString) -> dict[str, object]:
    event_targets = {
        opcode: _u16(rom, EVENT_COMMAND_TABLE_FILE + opcode * 2)
        for opcode in EXPECTED_EVENT_TARGETS
    }
    if event_targets != EXPECTED_EVENT_TARGETS:
        raise AuditError("event command dispatch targets do not match")

    party_targets = tuple(
        _u16(rom, PARTY_OPERATION_TABLE_FILE + index * 2)
        for index in range(len(EXPECTED_PARTY_TARGETS))
    )
    if party_targets != EXPECTED_PARTY_TARGETS:
        raise AuditError("party operation dispatch targets do not match")

    party_flags = bytes(
        rom[
            CHAR_PARTY_FLAG_TABLE_FILE:
            CHAR_PARTY_FLAG_TABLE_FILE + len(EXPECTED_CHAR_PARTY_FLAGS)
        ]
    )
    if party_flags != EXPECTED_CHAR_PARTY_FLAGS:
        raise AuditError("character party-flag table does not match")

    name_addrs = tuple(
        _u16(rom, PC_NAME_ADDR_TABLE_FILE + index * 2)
        for index in range(len(EXPECTED_PC_NAME_ADDRS))
    )
    if name_addrs != EXPECTED_PC_NAME_ADDRS:
        raise AuditError("PC dialogue-name address table does not match")

    save_region_digest = _sha256(
        bytes(
            rom[
                SAVE_REGION_TABLE_FILE:
                SAVE_REGION_TABLE_FILE + SAVE_REGION_TABLE_LENGTH
            ]
        )
    )
    if save_region_digest != EXPECTED_SAVE_REGION_TABLE_SHA256:
        raise AuditError("save-region descriptor table hash does not match")

    ng_plus_digest = _sha256(
        bytes(
            rom[
                NG_PLUS_LOADER_FILE:
                NG_PLUS_LOADER_FILE + NG_PLUS_LOADER_LENGTH
            ]
        )
    )
    if ng_plus_digest != EXPECTED_NG_PLUS_LOADER_SHA256:
        raise AuditError("New Game+ partial-loader hash does not match")

    return {
        "event_dispatch": {
            f"{opcode:02X}": f"$C0:{target:04X}"
            for opcode, target in sorted(event_targets.items())
        },
        "party_dispatch": {
            f"{operation:02X}": f"$C2:{target:04X}"
            for operation, target in enumerate(party_targets)
        },
        "logical_pc_07_party_flag": f"${party_flags[7]:02X}",
        "logical_pc_07_dialogue_name_entry": f"${name_addrs[7]:04X}",
        "vanilla_name_entry_id_07_target": "$7E:2C4D",
        "save_region_descriptor_table": {
            "entry_count": 8,
            "sha256": save_region_digest,
        },
        "new_game_plus_partial_loader": {
            "address": "$FF:FAED-$FF:FBD2",
            "sha256": ng_plus_digest,
        },
    }


def audit(rom_path: pathlib.Path) -> dict[str, object]:
    rom = rom_path.read_bytes()
    return {
        "schema_version": 1,
        "evidence": "verified-static",
        "copyright_boundary": (
            "metadata only; no event, dialogue, graphics, or ROM bytes emitted"
        ),
        "content": validate_content(),
        "disassembly": validate_disassembly_sources(),
        "rom": validate_canonical_rom(rom),
        "engine_metadata": audit_rom_metadata(rom),
        "binding_classifications": {
            binding_id: BINDING_CLASSIFICATIONS[binding_id]
            for binding_id in REQUIRED_BINDING_IDS
        },
        "installed_binding_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="headerless Chrono Trigger US Rev0 ROM",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON instead of indented JSON",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            audit(args.rom),
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
