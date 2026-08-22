#!/usr/bin/env python3
"""Audit playable-PC-associated location-event animation operands.

The audit reads one user-supplied canonical headerless US Rev0 ROM and emits
only aggregate, metadata-only JSON to stdout. It groups all 513 event-table
entries by unique packet pointer, preserves event/location aliases in hashed
internal ledgers, parses each valid packet once, and classifies animation
commands by object-level loader markers. It never writes a ROM, patch,
decompressed packet, script, trace, image, or report file.
"""

from __future__ import annotations

import argparse
import bisect
import collections
import dataclasses
import hashlib
import importlib.util
import json
import pathlib
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final


ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
PARSER_PATH: Final = ROOT / "tools" / "audit_location_event_items.py"
PARSER_EXPECTED_SIZE: Final = 39_560
PARSER_EXPECTED_SHA256: Final = (
    "cb39dd4485e6330c4f9d5b8817fe8e6"
    "a161cb2e965020cb1cd10a3fd30f7812a"
)
COMMAND_SIZE_VECTOR_EXPECTED_SHA256: Final = (
    "95e029ecb6f39753e5a9870035c30cf2"
    "8e540b75e5f107c24753e57780b43f65"
)
SCHEMA_VERSION: Final = 1
AUDITOR_VERSION: Final = "location-event-animation-operands-v0"

COMMAND_TABLE_FILE_OFFSET: Final = 0x005D6E

DEDICATED_PC_LOADERS: Final = {
    0x57: 0,
    0x5C: 1,
    0x62: 2,
    0x6A: 3,
    0x68: 4,
    0x6C: 5,
    0x6D: 6,
}
GENERIC_PC_LOADERS: Final = frozenset((0x80, 0x81))
ALTERNATE_OBJECT_MARKERS: Final = {
    0x82: "npc_loader",
    0x83: "enemy_loader",
    0x87: "graphics_override",
}
ALTERNATE_MARKER_ORDER: Final = (
    "npc_loader",
    "enemy_loader",
    "graphics_override",
)
MIXED_SOURCE_LOADERS: Final = frozenset(("npc_loader", "enemy_loader"))
SOURCE_MARKER_OPCODES: Final = frozenset(
    DEDICATED_PC_LOADERS
) | GENERIC_PC_LOADERS | frozenset(ALTERNATE_OBJECT_MARKERS)
LIFECYCLE_ROLE_MARKERS: Final = {
    0x0A: "remove_or_inactivate_target_object",
    0x0B: "disable_target_object_processing",
    0x0C: "enable_target_object_processing",
    0xD4: "remove_party_member_and_reassign_object_roles",
    0xD6: "conditionally_remove_active_party_object_role",
}

ANIMATION_OPCODE_CONTRACTS: Final = {
    0xAA: {
        "handler": 0x2E67,
        "payload_width": 1,
        "role": "explicit_animation_entrypoint_selector",
        "effective_selector": "payload_0",
        "namespace": "animation_entrypoint",
    },
    0xAB: {
        "handler": 0x2E9A,
        "payload_width": 1,
        "role": "explicit_secondary_animation_entrypoint_selector",
        "effective_selector": "payload_0",
        "namespace": "animation_entrypoint",
    },
    0xAC: {
        "handler": 0x2F71,
        "payload_width": 1,
        "role": "explicit_static_assembly_frame_selector",
        "effective_selector": None,
        "namespace": "static_assembly_frame",
    },
    0xAE: {
        "handler": 0x2E8F,
        "payload_width": 0,
        "role": "reset_animation_to_entrypoint_zero",
        "effective_selector": 0,
        "namespace": "animation_entrypoint",
    },
    0xB3: {
        "handler": 0x2E87,
        "payload_width": 0,
        "role": "loop_animation_entrypoint_zero",
        "effective_selector": 0,
        "namespace": "animation_entrypoint",
    },
    0xB4: {
        "handler": 0x2E8B,
        "payload_width": 0,
        "role": "loop_animation_entrypoint_one",
        "effective_selector": 1,
        "namespace": "animation_entrypoint",
    },
    0xB7: {
        "handler": 0x2F01,
        "payload_width": 2,
        "role": "secondary_animation_entrypoint_and_repeat_control",
        "effective_selector": "payload_0",
        "namespace": "animation_entrypoint_and_repeat_control",
    },
}

DISPATCH_TARGETS: Final = {
    **{
        0x57: 0x41E4,
        0x5C: 0x41EC,
        0x62: 0x41F4,
        0x68: 0x41FC,
        0x6A: 0x4204,
        0x6C: 0x420C,
        0x6D: 0x4214,
        0x80: 0x421E,
        0x81: 0x4476,
        0x82: 0x4590,
        0x83: 0x46DF,
        0x87: 0x4876,
        0x0A: 0x6254,
        0x0B: 0x6269,
        0x0C: 0x6282,
        0xD4: 0x394E,
        0xD6: 0x3A07,
    },
    **{
        opcode: int(contract["handler"])
        for opcode, contract in ANIMATION_OPCODE_CONTRACTS.items()
    },
}

EXPECTED_COMMAND_SIZES: Final = {
    0x57: 1,
    0x5C: 1,
    0x62: 1,
    0x68: 1,
    0x6A: 1,
    0x6C: 1,
    0x6D: 1,
    0x80: 2,
    0x81: 2,
    0x82: 2,
    0x83: 3,
    0x87: 2,
    0x0A: 2,
    0x0B: 2,
    0x0C: 2,
    0xD4: 2,
    0xD6: 2,
    **{
        opcode: int(contract["payload_width"]) + 1
        for opcode, contract in ANIMATION_OPCODE_CONTRACTS.items()
    },
}

HANDLER_SPANS: Final = (
    (
        "animation_handler_family",
        0x002E67,
        0x002F96,
        "2cf746461f3607687fc0038f29663074"
        "523a641b112cf4c5256f4f8f4695f7a1",
    ),
    (
        "animation_selector_shortcuts",
        0x002E67,
        0x002E9A,
        "da9acab1641651b070d5e247b603a643"
        "4ffdfaaaaa5e90c32cba17601cdab466",
    ),
    (
        "secondary_animation_selector_ab",
        0x002E9A,
        0x002F01,
        "d0ba0197f26fe1991ac5d7608e2fd640"
        "af8aaa54ffcdce009df7f2dc63c833b7",
    ),
    (
        "secondary_animation_selector_and_repeat_b7",
        0x002F01,
        0x002F71,
        "84f2a0c4730cc7bfa28b07623037a2a"
        "491fcaa33de1c745ee85a8cf178cf983c",
    ),
    (
        "static_frame_ac",
        0x002F71,
        0x002F94,
        "51ab4cd653aa0a88b0ada64171575973"
        "59056e6d2bddf7cf49b91a437fec1bf5",
    ),
    (
        "secondary_selector_dispatch",
        0x00CA09,
        0x00CA18,
        "585fc11bb3a597573df99edba73dcf0f"
        "f87a04468048617248686d67849859f3",
    ),
    (
        "secondary_selector_pointer",
        0x00CB82,
        0x00CBB1,
        "a2b521aefba060410c1dda19de9bd7c7"
        "34c8d6a375d29d39a511c85cea87f042",
    ),
    (
        "dedicated_pc_loaders",
        0x0041E4,
        0x00421E,
        "5a1ede4bca0645eb62d24f64fa38f792"
        "1e2b34329f750269001c31fa7332991f",
    ),
    (
        "generic_pc_if_party_id_dispatch",
        0x00421E,
        0x00426A,
        "ad0f9cb83ecfda62aab67fab9d48d093"
        "a8d176d48a7dd07eb31a710485ff7792",
    ),
    (
        "generic_pc_loader_header",
        0x004476,
        0x00448D,
        "25b15f34a2efdf67b47e63ca2cefb9c"
        "ed37adb8c60ad380fed5a3f310b9d59ee",
    ),
    (
        "npc_loader_entry",
        0x004590,
        0x004595,
        "45acfb2c7e71774278bc5cf0255e92f"
        "913afacfb5499133ebc3f5fe239ac840f",
    ),
    (
        "enemy_loader_entry",
        0x0046DF,
        0x0046E4,
        "03a91b09bedc79592dcda2faa9068bee"
        "9f802dda5881841b2d3618a5d3e9aa6c",
    ),
    (
        "graphics_override",
        0x004876,
        0x004892,
        "a8c3c979d9ecbd0389d3c859b26f9e78"
        "ab31ca7568b1ae43351886e6284637a8",
    ),
    (
        "object_lifecycle_0a_0c",
        0x006254,
        0x006295,
        "504d4cb6ff28d405e094f4301fabe6df"
        "17187216d2f476e9beb700d3c79be832",
    ),
    (
        "party_role_d4",
        0x00394E,
        0x0039E1,
        "5584da17571803afc1346ce8a5bfd12b"
        "4f1e1c51b6c5e7da0cd44c439a29b94f",
    ),
    (
        "party_role_d6",
        0x003A07,
        0x003A68,
        "eb339c2354d171bd23e4ef127e61a492"
        "17eb91f6af88f675b14418f62aa0a85f",
    ),
    (
        "party_role_d4_d6_family",
        0x00394E,
        0x003A68,
        "eea562f454d046fcc4dd7affe4e9a219"
        "5950e8a970c64dd8dd7f93da8c2aeb4b",
    ),
    (
        "fixed_pc_and_party_aware_80_routes",
        0x0041E4,
        0x004476,
        "7712775d164717d0d4524febe5d9293f"
        "25f59b4bbea48d37976c67b8f9c8c5d6",
    ),
    (
        "direct_pc_81_and_record_load",
        0x004476,
        0x004557,
        "405ddef51a89d3c153ef76b59c6895fa"
        "71b55dadb1a645c6787a8526e6d5d7d8",
    ),
    (
        "common_npc_head_and_82_route",
        0x004557,
        0x0046DF,
        "9222a06401026378dd31ccc3385b0366e"
        "e94cb81e4df9fb3a92f5532c670c6ae",
    ),
    (
        "enemy_83_family",
        0x0046DF,
        0x004867,
        "aec9e16ea3c54cc79f592987dbad1a32"
        "5a717f0956b2b2ff4874694687e1f9da",
    ),
    (
        "event_command_dispatch_table",
        0x005D6E,
        0x005F6E,
        "f1d4a0d5ec807cd1401d44aa43eb36c"
        "6086dcfdc65fd7d2b7ded17f2e35b4f8b",
    ),
)

EXPECTED_CANONICAL_COUNTS: Final = {
    "location_records": 512,
    "pointer_entries": 513,
    "location_referenced_event_ids": 497,
    "unique_packet_pointers": 466,
    "decoded_packet_groups": 462,
    "decoded_event_id_entries": 489,
    "non_script_packet_groups": 4,
    "non_script_event_id_entries": 24,
    "commands_parsed": 145_615,
    "event_id_command_instances": 155_780,
    "objects_parsed": 7_254,
    "animation_objects": 2_744,
    "animation_commands": 10_637,
    "direct_entry_pc_without_nonpc_loader_source_owners": 927,
    "direct_entry_pc_and_nonpc_loader_marker_source_owners": 23,
    "direct_entry_no_pc_marker_source_owners": 1_794,
    "direct_entry_pc_marker_union_source_owners": 950,
    "direct_entry_generic_pc_marker_union_source_owners": 422,
}

EXPECTED_ALL_OPCODE_COUNTS: Final = {
    0xAA: 5_593,
    0xAB: 638,
    0xAC: 2_581,
    0xAE: 1_011,
    0xB3: 278,
    0xB4: 275,
    0xB7: 261,
}
EXPECTED_PC_OPCODE_COUNTS: Final = {
    0xAA: 3_051,
    0xAB: 347,
    0xAC: 1_264,
    0xAE: 684,
    0xB3: 66,
    0xB4: 30,
    0xB7: 182,
}
EXPECTED_PC_ONLY_OPCODE_COUNTS: Final = {
    0xAA: 2_976,
    0xAB: 336,
    0xAC: 1_233,
    0xAE: 667,
    0xB3: 53,
    0xB4: 20,
    0xB7: 168,
}
EXPECTED_PC_AND_NONPC_OPCODE_COUNTS: Final = {
    0xAA: 75,
    0xAB: 11,
    0xAC: 31,
    0xAE: 17,
    0xB3: 13,
    0xB4: 10,
    0xB7: 14,
}
EXPECTED_NO_PC_OPCODE_COUNTS: Final = {
    0xAA: 2_542,
    0xAB: 291,
    0xAC: 1_317,
    0xAE: 327,
    0xB3: 212,
    0xB4: 245,
    0xB7: 79,
}
EXPECTED_GENERIC_OPCODE_COUNTS: Final = {
    0xAA: 1_835,
    0xAB: 185,
    0xAC: 702,
    0xAE: 150,
    0xB3: 9,
    0xB4: 11,
    0xB7: 72,
}
EXPECTED_LOADER_KIND_COUNTS: Final = {
    "dedicated_and_generic": 17,
    "dedicated_only": 528,
    "generic_only": 405,
}
EXPECTED_MIXED_MARKER_COUNTS: Final = {
    "enemy_loader": 2,
    "enemy_loader+graphics_override": 12,
    "npc_loader": 2,
    "npc_loader+enemy_loader+graphics_override": 2,
    "npc_loader+graphics_override": 5,
}
EXPECTED_EVENT_INSTANCE_COUNTS: Final = {
    0xAA: 6_058,
    0xAB: 715,
    0xAC: 2_730,
    0xAE: 1_036,
    0xB3: 294,
    0xB4: 304,
    0xB7: 261,
}
EXPECTED_SELECTOR_DISTINCT_COUNTS: Final = {
    0xAA: 67,
    0xAB: 46,
    0xAC: 229,
    0xAE: 1,
    0xB3: 1,
    0xB4: 1,
    0xB7: 30,
}
EXPECTED_TOPOLOGY_COUNTS: Final = {
    "function_pointer_entries": 116_064,
    "same_start_alias_occurrences": 91_869,
    "nonmonotone_function_pointer_objects": 668,
    "packets_with_nonmonotone_function_pointer_objects": 110,
    "objects_with_cross_owner_entries": 669,
    "objects_without_cross_owner_entries": 6_585,
    "in_owner_open_range_entries": 113_795,
    "backward_cross_owner_entries": 1_864,
    "forward_cross_owner_entries": 321,
    "packet_end_sentinels": 84,
    "nonboundary_entries": 0,
    "zero_length_source_owners": 0,
    "distinct_logical_to_source_owner_relations": 7_967,
    "source_owners_with_multiple_incoming_logical_owners": 172,
    "packets_with_cross_owner_entries": 111,
    "packets_with_packet_end_sentinels": 6,
    "animation_packets_with_cross_owner_entries": 109,
    "animation_packets": 391,
    "animation_source_owners_with_cross_owner_entries": 240,
    "animation_source_owners_without_cross_owner_entries": 2_504,
    "direct_entry_classification_changes_from_physical_owner_only": 14,
    "packet_pointer_alias_groups": 16,
    "packet_pointer_alias_extra_event_ids": 27,
    "unique_decompressed_content_digests": 455,
    "content_equivalence_groups": 4,
    "content_equivalence_extra_packet_pointers": 7,
    "largest_content_equivalence_group": 4,
}
EXPECTED_DIRECT_ENTRY_CONTEXT_COUNTS: Final = {
    "animation_source_owners": 2_744,
    "incoming_logical_owner_associations": 3_299,
    "external_incoming_logical_owner_associations": 555,
    "logical_owners_targeting_animation_source": 3_045,
    "function_pointer_entry_occurrences_targeting_animation_source": 44_701,
    "animation_source_owners_with_external_incoming_owner": 122,
    "animation_source_owners_with_self_only_incoming_owner": 2_622,
    "maximum_incoming_logical_owners": 14,
    "direct_entry_context_source_owner_associations": 3_564,
    "animation_source_owners_with_extended_context_closure": 351,
    "packets_with_extended_context_closure": 93,
    "animation_source_owners_with_marker_union_change": 350,
    "packets_with_marker_union_change": 92,
    "animation_source_owners_without_incoming_owner": 0,
}
EXPECTED_GRAPHICS_OVERRIDE_SOURCE_OWNERS: Final = 461
EXPECTED_DIRECT_ENTRY_GRAPHICS_CONTEXTS: Final = 485
EXPECTED_DIRECT_ENTRY_GRAPHICS_ASSOCIATIONS: Final = 745
EXPECTED_GLOBAL_LOADER_COMMAND_COUNTS: Final = {
    0x57: 257,
    0x5C: 280,
    0x62: 281,
    0x68: 262,
    0x6A: 258,
    0x6C: 257,
    0x6D: 225,
    0x80: 1_029,
    0x81: 139,
    0x82: 1_739,
    0x83: 1_412,
    0x87: 1_170,
}
EXPECTED_DEDICATED_PC_MARKER_ASSOCIATIONS: Final = {
    0: 207,
    1: 156,
    2: 151,
    3: 127,
    4: 131,
    5: 114,
    6: 85,
}
EXPECTED_GENERIC_PC_MARKER_ASSOCIATIONS: Final = {
    0: 120,
    1: 109,
    2: 108,
    3: 99,
    4: 88,
    5: 94,
    6: 66,
}
EXPECTED_ABSOLUTE_REFERENCE_COUNT: Final = 1_511
EXPECTED_IDENTITY_ARRAY_READ_COUNT: Final = 51
IDENTITY_ARRAY_RANGES: Final = (
    (0x7E1000, 0x7E1080),
    (0x7E1100, 0x7E1180),
)

SCOPE_ORDER: Final = (
    "all_encoded_animation_sites",
    "direct_entry_pc_marker_union",
    "direct_entry_pc_without_nonpc_loader_union",
    "direct_entry_pc_and_nonpc_loader_marker_union",
    "direct_entry_generic_pc_marker_union",
    "direct_entry_no_pc_marker_union",
)
PUBLIC_RESULT_SCOPES: Final = (
    "all_encoded_animation_sites",
    "direct_entry_pc_marker_union",
    "direct_entry_pc_and_nonpc_loader_marker_union",
)

EXPECTED_PLACEHOLDER_GROUPS: Final = {
    0xDB7FF2: {
        "event_ids": tuple(range(0x04B, 0x052)),
        "stage": "decompress",
        "reason": "empty_packet",
    },
    0xF6FFFC: {
        "event_ids": tuple(range(0x066, 0x06F)),
        "stage": "decompress",
        "reason": "invalid_lz_distance",
    },
    0xF9AFE9: {
        "event_ids": tuple(range(0x0E7, 0x0EC)),
        "stage": "decompress",
        "reason": "invalid_lz_distance",
    },
    0xFAFAA0: {
        "event_ids": tuple(range(0x140, 0x143)),
        "stage": "decompress",
        "reason": "invalid_lz_distance",
    },
}

# Patched after the report schema is frozen. It intentionally hashes only the
# JSON key/type topology, never report values or ROM-derived byte sequences.
EXPECTED_PUBLIC_SCHEMA_SHA256: Final = (
    "93efc3dceb56a0a920d0c23938d5fb0e"
    "6986198457bd543504ca5bd6e9c2e6ce"
)
EXPECTED_REPORT_SEMANTIC_SHA256: Final = (
    "4bc4130f808d966a1260080a57c96edc"
    "a7df01e9b0fe7f9ec6d71ef1006ce7cd"
)
FORBIDDEN_PUBLIC_KEYS: Final = frozenset(
    {
        "commands",
        "decompressed_data",
        "event_ids",
        "location_ids",
        "operand_tuples",
        "packet_data",
        "payload",
        "raw_bytes",
        "rom_bytes",
        "script_bytes",
        "site_rows",
        "sites",
    }
)


class AnimationOperandAuditError(RuntimeError):
    """Raised when an evidence or publication boundary fails closed."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_pinned_parser():
    raw = PARSER_PATH.read_bytes()
    if len(raw) != PARSER_EXPECTED_SIZE:
        raise AnimationOperandAuditError(
            "location-event parser dependency size drifted"
        )
    if _sha256(raw) != PARSER_EXPECTED_SHA256:
        raise AnimationOperandAuditError(
            "location-event parser dependency hash drifted"
        )
    name = "project_epoch_location_event_parser_v1"
    spec = importlib.util.spec_from_file_location(name, PARSER_PATH)
    if spec is None or spec.loader is None:
        raise AnimationOperandAuditError("cannot load location-event parser")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PARSER = _load_pinned_parser()


@dataclasses.dataclass(frozen=True)
class DecodedPacketGroup:
    snes_pointer: int
    file_pointer: int
    event_aliases: tuple[int, ...]
    location_aliases: tuple[int, ...]
    object_count: int
    compressed_size: int
    decompressed_size: int
    decompressed_sha256: str
    addendum_count: int
    decoded_data: bytes
    commands: tuple[Any, ...]


@dataclasses.dataclass(frozen=True)
class ObjectClassification:
    scope: str
    loader_kind: str | None
    pc_operand_ids: tuple[int, ...]
    dedicated_markers: tuple[tuple[int, int], ...]
    generic_markers: tuple[tuple[int, int], ...]
    invalid_generic_markers: tuple[tuple[int, int], ...]
    alternate_markers: tuple[str, ...]

    @property
    def has_pc_loader(self) -> bool:
        return bool(self.dedicated_markers or self.generic_markers)

    @property
    def has_generic_pc_loader(self) -> bool:
        return bool(self.generic_markers)


@dataclasses.dataclass(frozen=True)
class PacketTopology:
    """Validated physical-owner and logical function-entry topology."""

    object_starts: tuple[int, ...]
    object_ends: tuple[int, ...]
    function_pointers: tuple[tuple[int, ...], ...]
    target_source_owners: tuple[tuple[int, ...], ...]
    incoming_logical_owners: tuple[tuple[int, ...], ...]
    direct_entry_context_source_owners: tuple[tuple[int, ...], ...]
    counts: Mapping[str, int]
    ledger_row: Mapping[str, object]


def _json_hash(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return _sha256(raw)


def _hex_opcode(opcode: int) -> str:
    return f"{opcode:02X}"


def _compress_ranges(values: Iterable[int]) -> list[dict[str, int]]:
    ordered = sorted(set(values))
    if not ordered:
        return []
    rows: list[dict[str, int]] = []
    start = ordered[0]
    end = start
    for value in ordered[1:]:
        if value == end + 1:
            end = value
            continue
        rows.append({"start": start, "end": end})
        start = value
        end = value
    rows.append({"start": start, "end": end})
    return rows


def _value_domain(
    counter: collections.Counter[int],
    *,
    include_ranges: bool = False,
) -> dict[str, object]:
    values = sorted(counter)
    frequency_rows = [[value, counter[value]] for value in values]
    row: dict[str, object] = {
        "occurrences": sum(counter.values()),
        "distinct_values": len(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "frequency_sha256": _json_hash(frequency_rows),
    }
    if include_ranges:
        row["ranges"] = _compress_ranges(values)
    return row


def analyze_packet_topology(group: DecodedPacketGroup) -> PacketTopology:
    """Validate every function pointer without inferring runtime reachability."""

    if not group.decoded_data:
        raise AnimationOperandAuditError("decoded packet is empty")
    object_count = group.decoded_data[0]
    if object_count != group.object_count or not 1 <= object_count <= 0x40:
        raise AnimationOperandAuditError("packet object count drifted")
    script = group.decoded_data[1:]
    table_size = object_count * 32
    if table_size > len(script):
        raise AnimationOperandAuditError("packet pointer table is truncated")
    pointer_values = tuple(
        int.from_bytes(script[offset:offset + 2], "little")
        for offset in range(0, table_size, 2)
    )
    if len(pointer_values) != object_count * 16:
        raise AnimationOperandAuditError("function-pointer count drifted")
    function_pointers = tuple(
        pointer_values[index * 16:(index + 1) * 16]
        for index in range(object_count)
    )
    object_starts = tuple(row[0] for row in function_pointers)
    if any(
        left >= right
        for left, right in zip(object_starts, object_starts[1:])
    ):
        raise AnimationOperandAuditError(
            "function-0 source-owner starts are not strictly increasing"
        )
    if not object_starts or object_starts[0] < table_size:
        raise AnimationOperandAuditError(
            "function-0 source-owner start overlaps the pointer table"
        )
    if object_starts[-1] >= len(script):
        raise AnimationOperandAuditError(
            "final function-0 source-owner start has no encoded command"
        )
    object_ends = object_starts[1:] + (len(script),)

    command_boundaries = {command.offset for command in group.commands}
    if len(command_boundaries) != len(group.commands):
        raise AnimationOperandAuditError(
            "two decoded commands claim the same physical source offset"
        )
    valid_targets = command_boundaries | {len(script)}
    nonboundary = [
        pointer
        for pointer in pointer_values
        if pointer not in valid_targets
    ]
    if nonboundary:
        raise AnimationOperandAuditError(
            "function pointer does not land on a command boundary"
        )

    counts: collections.Counter[str] = collections.Counter()
    target_source_owners: list[tuple[int, ...]] = []
    object_rows: list[dict[str, object]] = []
    for object_id, pointers in enumerate(function_pointers):
        start = object_starts[object_id]
        end = object_ends[object_id]
        if start >= end:
            counts["zero_length_source_owners"] += 1
            raise AnimationOperandAuditError(
                "zero-length physical source owner is not accepted"
            )
        if tuple(sorted(pointers)) != pointers:
            counts["nonmonotone_function_pointer_objects"] += 1
        counts["same_start_alias_occurrences"] += (
            len(pointers) - len(set(pointers))
        )

        targeted_owners: set[int] = set()
        relation_counts: collections.Counter[str] = collections.Counter()
        for pointer in pointers:
            if pointer == len(script):
                relation = "packet_end_sentinels"
            elif start <= pointer < end:
                relation = "in_owner_open_range_entries"
                targeted_owners.add(object_id)
            elif pointer < start:
                relation = "backward_cross_owner_entries"
                target_owner = bisect.bisect_right(object_starts, pointer) - 1
                if target_owner < 0 or not (
                    object_starts[target_owner]
                    <= pointer
                    < object_ends[target_owner]
                ):
                    raise AnimationOperandAuditError(
                        "backward function pointer has no physical owner"
                    )
                targeted_owners.add(target_owner)
            else:
                relation = "forward_cross_owner_entries"
                target_owner = bisect.bisect_right(object_starts, pointer) - 1
                if target_owner < 0 or not (
                    object_starts[target_owner]
                    <= pointer
                    < object_ends[target_owner]
                ):
                    raise AnimationOperandAuditError(
                        "forward function pointer has no physical owner"
                    )
                targeted_owners.add(target_owner)
            counts[relation] += 1
            relation_counts[relation] += 1

        has_cross_owner = bool(
            relation_counts["backward_cross_owner_entries"]
            or relation_counts["forward_cross_owner_entries"]
        )
        counts[
            "objects_with_cross_owner_entries"
            if has_cross_owner
            else "objects_without_cross_owner_entries"
        ] += 1
        target_source_owners.append(tuple(sorted(targeted_owners)))
        object_rows.append(
            {
                "source_object_id": object_id,
                "start": start,
                "end_exclusive": end,
                "function_pointers": list(pointers),
                "target_source_owners": sorted(targeted_owners),
                "relation_counts": dict(sorted(relation_counts.items())),
            }
        )

    incoming_logical_owner_sets: list[set[int]] = [
        set() for _ in range(object_count)
    ]
    for logical_owner_id, targets in enumerate(target_source_owners):
        for target_source_owner_id in targets:
            incoming_logical_owner_sets[target_source_owner_id].add(
                logical_owner_id
            )
    if any(not owners for owners in incoming_logical_owner_sets):
        raise AnimationOperandAuditError(
            "physical source owner has no direct logical function entry"
        )
    incoming_logical_owners = tuple(
        tuple(sorted(owners)) for owners in incoming_logical_owner_sets
    )
    direct_entry_context_source_owners = tuple(
        tuple(
            sorted(
                {
                    context_source_owner_id
                    for logical_owner_id in logical_owner_ids
                    for context_source_owner_id in target_source_owners[
                        logical_owner_id
                    ]
                }
            )
        )
        for logical_owner_ids in incoming_logical_owners
    )

    counts["function_pointer_entries"] = len(pointer_values)
    counts["nonboundary_entries"] = 0
    counts["distinct_logical_to_source_owner_relations"] = sum(
        len(targets) for targets in target_source_owners
    )
    counts["source_owners_with_multiple_incoming_logical_owners"] = sum(
        len(owners) > 1 for owners in incoming_logical_owners
    )
    ledger_row = {
        "packet_pointer": group.snes_pointer,
        "decompressed_sha256": group.decompressed_sha256,
        "object_rows": object_rows,
        "incoming_logical_owners": [
            list(owners) for owners in incoming_logical_owners
        ],
        "direct_entry_context_source_owners": [
            list(owners) for owners in direct_entry_context_source_owners
        ],
    }
    return PacketTopology(
        object_starts=object_starts,
        object_ends=object_ends,
        function_pointers=function_pointers,
        target_source_owners=tuple(target_source_owners),
        incoming_logical_owners=incoming_logical_owners,
        direct_entry_context_source_owners=(
            direct_entry_context_source_owners
        ),
        counts=dict(counts),
        ledger_row=ledger_row,
    )


def direct_entry_marker_commands(
    commands_by_source_owner: Mapping[int, Sequence[Any]],
    topology: PacketTopology,
    source_owner_id: int,
) -> tuple[Any, ...]:
    """Return each direct-entry closure command once per physical owner."""

    if not 0 <= source_owner_id < len(topology.object_starts):
        raise AnimationOperandAuditError("source-owner ID is out of range")
    context_owner_ids = topology.direct_entry_context_source_owners[
        source_owner_id
    ]
    if not context_owner_ids:
        raise AnimationOperandAuditError(
            "source owner has no direct-entry marker context"
        )
    rows: list[Any] = []
    for context_owner_id in context_owner_ids:
        if context_owner_id not in commands_by_source_owner:
            raise AnimationOperandAuditError(
                "direct-entry context source owner was not decoded"
            )
        rows.extend(commands_by_source_owner[context_owner_id])
    return tuple(rows)


def classify_object(commands: Iterable[Any]) -> ObjectClassification:
    dedicated: list[tuple[int, int]] = []
    generic: list[tuple[int, int]] = []
    invalid: list[tuple[int, int]] = []
    alternate_seen: set[str] = set()

    for command in commands:
        if command.opcode in DEDICATED_PC_LOADERS:
            dedicated.append(
                (command.opcode, DEDICATED_PC_LOADERS[command.opcode])
            )
        elif command.opcode in GENERIC_PC_LOADERS:
            if len(command.payload) != 1:
                raise AnimationOperandAuditError(
                    f"generic loader ${command.opcode:02X} payload drifted"
                )
            pc_id = command.payload[0]
            if 0 <= pc_id <= 6:
                generic.append((command.opcode, pc_id))
            else:
                invalid.append((command.opcode, pc_id))
        marker = ALTERNATE_OBJECT_MARKERS.get(command.opcode)
        if marker is not None:
            alternate_seen.add(marker)

    has_pc = bool(dedicated or generic)
    alternate = tuple(
        marker
        for marker in ALTERNATE_MARKER_ORDER
        if marker in alternate_seen
    )
    has_mixed_source_loader = any(
        marker in MIXED_SOURCE_LOADERS for marker in alternate
    )
    if has_pc and not has_mixed_source_loader:
        scope = "pc_without_nonpc_loader_markers"
    elif has_pc:
        scope = "pc_and_nonpc_loader_markers"
    else:
        scope = "no_pc_markers"

    if dedicated and generic:
        loader_kind = "dedicated_and_generic"
    elif dedicated:
        loader_kind = "dedicated_only"
    elif generic:
        loader_kind = "generic_only"
    else:
        loader_kind = None

    pc_operand_ids = tuple(
        sorted({pc_id for _opcode, pc_id in dedicated + generic})
    )
    return ObjectClassification(
        scope=scope,
        loader_kind=loader_kind,
        pc_operand_ids=pc_operand_ids,
        dedicated_markers=tuple(dedicated),
        generic_markers=tuple(generic),
        invalid_generic_markers=tuple(invalid),
        alternate_markers=alternate,
    )


def _validate_engine_contract(rom: bytes) -> dict[str, object]:
    command_size_vector = bytes(PARSER.FIXED_COMMAND_SIZES)
    command_size_vector_sha256 = _sha256(command_size_vector)
    if command_size_vector_sha256 != COMMAND_SIZE_VECTOR_EXPECTED_SHA256:
        raise AnimationOperandAuditError(
            "complete 256-opcode command-size vector drifted"
        )
    dispatch_rows = []
    for opcode, expected_handler in sorted(DISPATCH_TARGETS.items()):
        offset = COMMAND_TABLE_FILE_OFFSET + opcode * 2
        actual_handler = int.from_bytes(rom[offset:offset + 2], "little")
        if actual_handler != expected_handler:
            raise AnimationOperandAuditError(
                f"opcode ${opcode:02X} dispatch target drifted"
            )
        actual_size = PARSER.FIXED_COMMAND_SIZES[opcode]
        expected_size = EXPECTED_COMMAND_SIZES[opcode]
        if actual_size != expected_size:
            raise AnimationOperandAuditError(
                f"opcode ${opcode:02X} command size drifted"
            )
        dispatch_rows.append(
            {
                "opcode": opcode,
                "handler_bank_c0": actual_handler,
                "command_size": actual_size,
            }
        )

    span_rows = []
    for name, start, end_exclusive, expected_hash in HANDLER_SPANS:
        if not 0 <= start < end_exclusive <= len(rom):
            raise AnimationOperandAuditError(
                f"handler span {name} is outside canonical ROM"
            )
        actual_hash = _sha256(rom[start:end_exclusive])
        if actual_hash != expected_hash:
            raise AnimationOperandAuditError(
                f"handler span {name} preimage drifted"
            )
        span_rows.append(
            {
                "name": name,
                "file_start": start,
                "file_end_exclusive": end_exclusive,
                "size": end_exclusive - start,
                "sha256": actual_hash,
            }
        )

    return {
        "command_table_file_offset": COMMAND_TABLE_FILE_OFFSET,
        "command_size_vector_entries": len(command_size_vector),
        "command_size_vector_sha256": command_size_vector_sha256,
        "dispatch_entries": dispatch_rows,
        "handler_spans": span_rows,
    }


def _decode_packet_groups(
    rom: bytes,
) -> tuple[
    list[DecodedPacketGroup],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    location_event_ids = PARSER.location_event_ids(rom)
    locations_by_event: dict[int, list[int]] = collections.defaultdict(list)
    for location_id, event_id in enumerate(location_event_ids):
        locations_by_event[event_id].append(location_id)

    aliases_by_pointer: dict[int, list[int]] = collections.defaultdict(list)
    for event_id in range(PARSER.EVENT_ID_COUNT):
        snes_pointer, _file_pointer = PARSER.event_pointer(rom, event_id)
        aliases_by_pointer[snes_pointer].append(event_id)

    decoded: list[DecodedPacketGroup] = []
    placeholders: list[dict[str, object]] = []
    alias_ledger: list[dict[str, object]] = []
    seen_placeholders: set[int] = set()
    for snes_pointer, event_aliases_list in sorted(
        aliases_by_pointer.items()
    ):
        event_aliases = tuple(sorted(event_aliases_list))
        file_pointer = PARSER.snes_hirom_to_file(snes_pointer)
        event_location_aliases = [
            {
                "event_id": event_id,
                "location_ids": sorted(locations_by_event.get(event_id, [])),
            }
            for event_id in event_aliases
        ]
        location_aliases = tuple(
            sorted(
                location_id
                for event_id in event_aliases
                for location_id in locations_by_event.get(event_id, [])
            )
        )
        expected_placeholder = EXPECTED_PLACEHOLDER_GROUPS.get(snes_pointer)
        if expected_placeholder is not None:
            expected_ids = tuple(expected_placeholder["event_ids"])
            if event_aliases != expected_ids:
                raise AnimationOperandAuditError(
                    "canonical placeholder event aliases drifted"
                )
            try:
                packet = PARSER.decompress_packet(rom, file_pointer)
            except PARSER.AuditError as exc:
                actual_reason = (
                    "invalid_lz_distance"
                    if str(exc).startswith("invalid LZ distance ")
                    else "unexpected_decompression_error"
                )
                if (
                    expected_placeholder["stage"] != "decompress"
                    or expected_placeholder["reason"] != actual_reason
                ):
                    raise AnimationOperandAuditError(
                        "canonical placeholder failure reason drifted"
                    ) from exc
            else:
                actual_reason = "empty_packet" if not packet.data else "decoded"
                if (
                    expected_placeholder["stage"] != "decompress"
                    or expected_placeholder["reason"] != actual_reason
                ):
                    raise AnimationOperandAuditError(
                        "canonical placeholder unexpectedly decoded"
                    )
            row = {
                "snes_pointer": snes_pointer,
                "event_aliases": list(event_aliases),
                "location_aliases": list(location_aliases),
                "event_location_aliases": event_location_aliases,
                "status": "expected_placeholder",
                "stage": expected_placeholder["stage"],
                "reason": expected_placeholder["reason"],
            }
            placeholders.append(row)
            alias_ledger.append(row)
            seen_placeholders.add(snes_pointer)
            continue

        try:
            packet = PARSER.decompress_packet(rom, file_pointer)
        except PARSER.AuditError as exc:
            raise AnimationOperandAuditError(
                "unexpected location-event decompression failure"
            ) from exc
        if not packet.data:
            raise AnimationOperandAuditError(
                "unexpected empty location-event packet"
            )
        try:
            commands = tuple(PARSER.parse_event(event_aliases[0], packet.data))
        except PARSER.AuditError as exc:
            raise AnimationOperandAuditError(
                "unexpected location-event parse failure"
            ) from exc

        group = DecodedPacketGroup(
            snes_pointer=snes_pointer,
            file_pointer=file_pointer,
            event_aliases=event_aliases,
            location_aliases=location_aliases,
            object_count=packet.data[0],
            compressed_size=packet.compressed_size,
            decompressed_size=len(packet.data),
            decompressed_sha256=_sha256(packet.data),
            addendum_count=packet.addendum_count,
            decoded_data=packet.data,
            commands=commands,
        )
        decoded.append(group)
        alias_ledger.append(
            {
                "snes_pointer": snes_pointer,
                "event_aliases": list(event_aliases),
                "location_aliases": list(location_aliases),
                "event_location_aliases": event_location_aliases,
                "status": "decoded",
                "object_count": group.object_count,
                "command_count": len(group.commands),
                "decompressed_sha256": group.decompressed_sha256,
            }
        )

    if seen_placeholders != set(EXPECTED_PLACEHOLDER_GROUPS):
        raise AnimationOperandAuditError(
            "canonical placeholder packet set drifted"
        )
    return decoded, placeholders, alias_ledger


def _scope_members(classification: ObjectClassification) -> tuple[str, ...]:
    class_scope = {
        "pc_without_nonpc_loader_markers": (
            "direct_entry_pc_without_nonpc_loader_union"
        ),
        "pc_and_nonpc_loader_markers": (
            "direct_entry_pc_and_nonpc_loader_marker_union"
        ),
        "no_pc_markers": "direct_entry_no_pc_marker_union",
    }[classification.scope]
    members = ["all_encoded_animation_sites", class_scope]
    if classification.has_pc_loader:
        members.append("direct_entry_pc_marker_union")
    if classification.has_generic_pc_loader:
        members.append("direct_entry_generic_pc_marker_union")
    return tuple(members)


def _effective_selector(opcode: int, payload: bytes) -> int | None:
    source = ANIMATION_OPCODE_CONTRACTS[opcode]["effective_selector"]
    if source == "payload_0":
        return payload[0]
    if source is None:
        return None
    return int(source)


def _distribution_row(
    opcode: int,
    tuples: collections.Counter[tuple[int, ...]],
    event_id_instances: int,
    location_instances: int,
    *,
    include_ranges: bool,
) -> dict[str, object]:
    tuple_rows = [
        [list(operands), tuples[operands]]
        for operands in sorted(tuples)
    ]
    selector_counter: collections.Counter[int] = collections.Counter()
    static_frame_counter: collections.Counter[int] = collections.Counter()
    for operands, count in tuples.items():
        selector = _effective_selector(opcode, bytes(operands))
        if selector is not None:
            selector_counter[selector] += count
        if opcode == 0xAC:
            static_frame_counter[operands[0]] += count
    row: dict[str, object] = {
        "encoded_site_count": sum(tuples.values()),
        "event_id_instance_count": event_id_instances,
        "location_instance_count": location_instances,
        "distinct_operand_tuples": len(tuples),
        "operand_tuple_frequency_sha256": _json_hash(tuple_rows),
    }
    if opcode == 0xAC:
        row["animation_entrypoint_selector_domain"] = None
        row["static_assembly_frame_domain"] = _value_domain(
            static_frame_counter,
            include_ranges=include_ranges,
        )
    else:
        row["animation_entrypoint_selector_domain"] = _value_domain(
            selector_counter,
            include_ranges=include_ranges,
        )
        row["static_assembly_frame_domain"] = None
    if opcode == 0xB7:
        repeat_counter: collections.Counter[int] = collections.Counter()
        for operands, count in tuples.items():
            repeat_counter[operands[1]] += count
        row["repeat_control_domain"] = _value_domain(
            repeat_counter,
            include_ranges=include_ranges,
        )
    else:
        row["repeat_control_domain"] = None
    return row


def _schema_shape(value: Any) -> object:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "str"
    if isinstance(value, Mapping):
        return {
            "object": [
                [key, _schema_shape(child)]
                for key, child in sorted(value.items())
            ]
        }
    if isinstance(value, list):
        return {
            "list_length": len(value),
            "items": [_schema_shape(child) for child in value],
        }
    raise AnimationOperandAuditError(
        f"unsupported report schema type: {type(value).__name__}"
    )


def public_schema_sha256(report: Mapping[str, Any]) -> str:
    return _json_hash(_schema_shape(report))


def public_semantic_sha256(report: Mapping[str, Any]) -> str:
    """Hash all public semantics without creating a tool self-hash cycle."""

    normalized = json.loads(
        json.dumps(report, sort_keys=True, ensure_ascii=True)
    )
    normalized["inputs"]["tool_source"]["size"] = 0
    normalized["inputs"]["tool_source"]["sha256"] = "0" * 64
    normalized["reproduction"]["semantic_content_sha256"] = ""
    return _json_hash(normalized)


def _validate_expected_counts(
    coverage: Mapping[str, int],
    scope_counts: Mapping[str, int],
    opcode_counts: Mapping[str, Mapping[int, int]],
    loader_kind_counts: Mapping[str, int],
    mixed_marker_counts: Mapping[str, int],
) -> None:
    combined = {**coverage, **scope_counts}
    for name, expected in EXPECTED_CANONICAL_COUNTS.items():
        if combined.get(name) != expected:
            raise AnimationOperandAuditError(
                f"canonical count {name} drifted: "
                f"{combined.get(name)!r} != {expected}"
            )
    expected_scoped_opcodes = {
        "all_encoded_animation_sites": EXPECTED_ALL_OPCODE_COUNTS,
        "direct_entry_pc_marker_union": EXPECTED_PC_OPCODE_COUNTS,
        "direct_entry_pc_without_nonpc_loader_union": (
            EXPECTED_PC_ONLY_OPCODE_COUNTS
        ),
        "direct_entry_pc_and_nonpc_loader_marker_union": (
            EXPECTED_PC_AND_NONPC_OPCODE_COUNTS
        ),
        "direct_entry_generic_pc_marker_union": (
            EXPECTED_GENERIC_OPCODE_COUNTS
        ),
        "direct_entry_no_pc_marker_union": EXPECTED_NO_PC_OPCODE_COUNTS,
    }
    for scope, expected_rows in expected_scoped_opcodes.items():
        actual_rows = opcode_counts[scope]
        if dict(actual_rows) != expected_rows:
            raise AnimationOperandAuditError(
                f"canonical opcode counts drifted for {scope}"
            )
    if dict(loader_kind_counts) != EXPECTED_LOADER_KIND_COUNTS:
        raise AnimationOperandAuditError("PC loader-kind counts drifted")
    if dict(mixed_marker_counts) != EXPECTED_MIXED_MARKER_COUNTS:
        raise AnimationOperandAuditError("mixed-source marker counts drifted")


def validate_public_report(report: Mapping[str, Any]) -> None:
    expected_top = {
        "schema_version",
        "auditor_version",
        "status",
        "scope",
        "inputs",
        "alias_topology",
        "command_contract",
        "result_domains",
        "context_classification",
        "ambiguities",
        "reproduction",
        "evidence",
        "coverage",
        "nonclaims",
    }
    if set(report) != expected_top:
        raise AnimationOperandAuditError("top-level report schema drifted")

    def walk(value: Any, key: str | None = None) -> None:
        if key is not None and key.lower() in FORBIDDEN_PUBLIC_KEYS:
            raise AnimationOperandAuditError(
                f"forbidden public-report key: {key}"
            )
        if value is None or isinstance(value, (bool, int)):
            return
        if isinstance(value, str):
            if len(value) > 512:
                raise AnimationOperandAuditError(
                    "oversized public-report string"
                )
            normalized = value.replace("\\", "/").lower()
            if "/private/" in f"/{normalized.strip('/')}" or normalized.startswith(
                "private/"
            ):
                raise AnimationOperandAuditError(
                    "private path leaked into public report"
                )
            if normalized.endswith((".sfc", ".smc", ".srm", ".state")):
                raise AnimationOperandAuditError(
                    "protected artifact path leaked into public report"
                )
            return
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                if not isinstance(child_key, str):
                    raise AnimationOperandAuditError(
                        "non-string public-report key"
                    )
                walk(child, child_key)
            return
        if isinstance(value, list):
            if len(value) > 8 and all(isinstance(item, int) for item in value):
                raise AnimationOperandAuditError(
                    "long numeric byte-like list is not public metadata"
                )
            for child in value:
                walk(child)
            return
        raise AnimationOperandAuditError(
            f"unsupported public-report type: {type(value).__name__}"
        )

    walk(report)

    required_semantics = {
        ("schema_version",): SCHEMA_VERSION,
        ("auditor_version",): AUDITOR_VERSION,
        ("status",): (
            "pass-metadata-only-encoded-census-with-unresolved-contexts"
        ),
        ("scope", "read_only"): True,
        ("scope", "encoded_location_event_census_complete"): True,
        (
            "scope",
            "direct_function_entry_marker_overapprox_complete",
        ): True,
        ("scope", "runtime_context_classification_complete"): False,
        ("scope", "runtime_performed"): False,
        ("scope", "field_location_events_included"): True,
        ("scope", "battle_included"): False,
        ("scope", "menu_included"): False,
        ("scope", "overworld_included"): False,
        ("evidence", "label"): "verified-static",
        ("evidence", "encoded_census_complete"): True,
        (
            "evidence",
            "direct_function_entry_marker_overapprox_complete",
        ): True,
        ("evidence", "contextual_runtime_classification_complete"): False,
        ("evidence", "runtime_performed"): False,
        ("evidence", "canonical_count_gates_pass"): True,
        ("evidence", "metadata_only"): True,
        ("evidence", "rom_installable"): False,
        ("context_classification", "runtime_reachability_resolved"): False,
        (
            "context_classification",
            "direct_function_entry_marker_overapprox_complete",
        ): True,
        ("ambiguities", "loader_lifetime_model_complete"): False,
        ("ambiguities", "graphics_bitfield_path_model_complete"): False,
        ("ambiguities", "indirect_state_writer_model_complete"): False,
        ("reproduction", "canonical_json"): True,
        ("reproduction", "output_mode"): (
            "stdout-only-no-output-path-option"
        ),
    }
    for path, expected in required_semantics.items():
        value: Any = report
        for component in path:
            if not isinstance(value, Mapping) or component not in value:
                raise AnimationOperandAuditError(
                    "required public-report semantic is missing"
                )
            value = value[component]
        if value != expected:
            raise AnimationOperandAuditError(
                "required public-report semantic drifted: " + ".".join(path)
            )

    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise AnimationOperandAuditError("public report inputs are malformed")
    tool_source = inputs.get("tool_source")
    if not isinstance(tool_source, Mapping):
        raise AnimationOperandAuditError(
            "public report tool-source receipt is malformed"
        )
    tool_raw = pathlib.Path(__file__).resolve().read_bytes()
    if tool_source != {
        "path": "tools/audit_location_event_animation_operands_v0.py",
        "size": len(tool_raw),
        "sha256": _sha256(tool_raw),
    }:
        raise AnimationOperandAuditError(
            "public report tool-source receipt drifted"
        )

    schema_hash = public_schema_sha256(report)
    if EXPECTED_PUBLIC_SCHEMA_SHA256 != "TO_BE_PINNED":
        if schema_hash != EXPECTED_PUBLIC_SCHEMA_SHA256:
            raise AnimationOperandAuditError(
                "public report nested schema drifted"
            )
        reproduction = report.get("reproduction")
        if not isinstance(reproduction, Mapping) or (
            reproduction.get("schema_shape_sha256")
            != EXPECTED_PUBLIC_SCHEMA_SHA256
        ):
            raise AnimationOperandAuditError(
                "public report schema receipt drifted"
            )
    semantic_hash = public_semantic_sha256(report)
    if EXPECTED_REPORT_SEMANTIC_SHA256 != "TO_BE_PINNED":
        if semantic_hash != EXPECTED_REPORT_SEMANTIC_SHA256:
            raise AnimationOperandAuditError(
                "public report semantic identity drifted"
            )
        reproduction = report.get("reproduction")
        if not isinstance(reproduction, Mapping) or (
            reproduction.get("semantic_content_sha256")
            != EXPECTED_REPORT_SEMANTIC_SHA256
        ):
            raise AnimationOperandAuditError(
                "public report semantic receipt drifted"
            )


def canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    validate_public_report(report)
    return (
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("ascii")


def build_report(rom: bytes) -> dict[str, object]:
    rom_identity = PARSER.validate_canonical_rom(rom)
    engine_contract = _validate_engine_contract(rom)
    groups, placeholder_groups, alias_ledger = _decode_packet_groups(rom)

    source_owner_scope_counts: collections.Counter[str] = collections.Counter()
    physical_owner_only_counts: collections.Counter[str] = collections.Counter()
    loader_kind_counts: collections.Counter[str] = collections.Counter()
    mixed_marker_counts: collections.Counter[str] = collections.Counter()
    alternate_marker_context_counts: collections.Counter[str] = (
        collections.Counter()
    )
    lifecycle_marker_associations: dict[str, collections.Counter[int]] = {
        scope: collections.Counter() for scope in SCOPE_ORDER
    }
    dedicated_pc_associations: collections.Counter[int] = collections.Counter()
    generic_pc_associations: collections.Counter[int] = collections.Counter()
    opcode_counts: dict[str, collections.Counter[int]] = {
        scope: collections.Counter() for scope in SCOPE_ORDER
    }
    event_instance_counts: dict[str, collections.Counter[int]] = {
        scope: collections.Counter() for scope in SCOPE_ORDER
    }
    location_instance_counts: dict[str, collections.Counter[int]] = {
        scope: collections.Counter() for scope in SCOPE_ORDER
    }
    operand_tuples: dict[
        str, dict[int, collections.Counter[tuple[int, ...]]]
    ] = {
        scope: {
            opcode: collections.Counter()
            for opcode in ANIMATION_OPCODE_CONTRACTS
        }
        for scope in SCOPE_ORDER
    }
    topology_counts: collections.Counter[str] = collections.Counter()
    direct_entry_context_counts: collections.Counter[str] = (
        collections.Counter()
    )
    packets_with_extended_context_closure: set[int] = set()
    packets_with_marker_union_change: set[int] = set()
    topology_ledger: list[Mapping[str, object]] = []
    site_ledger: list[dict[str, object]] = []
    source_owner_ledger: list[dict[str, object]] = []
    classification_change_ledger: list[dict[str, object]] = []
    content_groups: dict[str, list[int]] = collections.defaultdict(list)
    animation_packet_pointers: set[int] = set()
    pc_packet_pointers: set[int] = set()
    generic_pc_packet_pointers: set[int] = set()
    animation_event_aliases: set[int] = set()
    animation_location_aliases: set[int] = set()
    pc_event_aliases: set[int] = set()
    pc_location_aliases: set[int] = set()
    generic_event_aliases: set[int] = set()
    generic_location_aliases: set[int] = set()
    graphics_override_source_owners = 0
    direct_entry_graphics_contexts = 0
    direct_entry_graphics_associations = 0

    all_commands = [
        command
        for group in groups
        for command in group.commands
    ]
    global_loader_counts: collections.Counter[int] = collections.Counter(
        command.opcode
        for command in all_commands
        if command.opcode in EXPECTED_GLOBAL_LOADER_COMMAND_COUNTS
    )
    if dict(global_loader_counts) != EXPECTED_GLOBAL_LOADER_COMMAND_COUNTS:
        raise AnimationOperandAuditError("global loader-command census drifted")
    global_generic_domains: dict[int, collections.Counter[int]] = {
        0x80: collections.Counter(),
        0x81: collections.Counter(),
    }
    graphics_override_operands: collections.Counter[int] = collections.Counter()
    global_lifecycle_counts: collections.Counter[int] = collections.Counter()
    for command in all_commands:
        if command.opcode in EXPECTED_COMMAND_SIZES and (
            len(command.payload) + 1 != EXPECTED_COMMAND_SIZES[command.opcode]
        ):
            raise AnimationOperandAuditError(
                f"opcode ${command.opcode:02X} encoded width drifted"
            )
        if command.opcode in GENERIC_PC_LOADERS:
            pc_id = command.payload[0]
            global_generic_domains[command.opcode][pc_id] += 1
            if not 0 <= pc_id <= 6:
                raise AnimationOperandAuditError(
                    "generic PC-loader operand is outside vanilla $00-$06"
                )
        if command.opcode == 0x87:
            graphics_override_operands[command.payload[0]] += 1
        if command.opcode in LIFECYCLE_ROLE_MARKERS:
            global_lifecycle_counts[command.opcode] += 1
    if (
        len(graphics_override_operands) != 16
        or min(graphics_override_operands) != 0
        or max(graphics_override_operands) != 0x7F
        or graphics_override_operands[0x7F] != 25
    ):
        raise AnimationOperandAuditError(
            "graphics-override operand domain drifted"
        )

    for group in groups:
        content_groups[group.decompressed_sha256].append(group.snes_pointer)
        topology = analyze_packet_topology(group)
        topology_ledger.append(topology.ledger_row)
        topology_counts.update(topology.counts)
        has_cross_owner = bool(
            topology.counts.get("backward_cross_owner_entries", 0)
            or topology.counts.get("forward_cross_owner_entries", 0)
        )
        if has_cross_owner:
            topology_counts["packets_with_cross_owner_entries"] += 1
        if topology.counts.get(
            "nonmonotone_function_pointer_objects", 0
        ):
            topology_counts[
                "packets_with_nonmonotone_function_pointer_objects"
            ] += 1
        if topology.counts.get("packet_end_sentinels", 0):
            topology_counts["packets_with_packet_end_sentinels"] += 1

        commands_by_object: dict[int, list[Any]] = collections.defaultdict(list)
        for command in group.commands:
            commands_by_object[command.object_id].append(command)
        if set(commands_by_object) != set(range(group.object_count)):
            raise AnimationOperandAuditError(
                "decoded physical source-owner coverage is incomplete"
            )
        animation_source_owner_ids = {
            command.object_id
            for command in group.commands
            if command.opcode in ANIMATION_OPCODE_CONTRACTS
        }
        group_has_animation = bool(animation_source_owner_ids)
        if group_has_animation:
            topology_counts["animation_packets"] += 1
            if has_cross_owner:
                topology_counts[
                    "animation_packets_with_cross_owner_entries"
                ] += 1
            logical_owners_targeting_animation = {
                logical_owner_id
                for source_owner_id in animation_source_owner_ids
                for logical_owner_id in topology.incoming_logical_owners[
                    source_owner_id
                ]
            }
            direct_entry_context_counts[
                "logical_owners_targeting_animation_source"
            ] += len(logical_owners_targeting_animation)
            script_end = len(group.decoded_data) - 1
            for pointers in topology.function_pointers:
                for pointer in pointers:
                    if pointer == script_end:
                        continue
                    target_owner_id = (
                        bisect.bisect_right(topology.object_starts, pointer) - 1
                    )
                    if target_owner_id in animation_source_owner_ids:
                        direct_entry_context_counts[
                            "function_pointer_entry_occurrences_targeting_"
                            "animation_source"
                        ] += 1

        for source_object_id in range(group.object_count):
            source_commands = commands_by_object[source_object_id]
            animation_commands = [
                command
                for command in source_commands
                if command.opcode in ANIMATION_OPCODE_CONTRACTS
            ]
            if not animation_commands:
                continue

            source_owner_scope_counts["animation_source_owners"] += 1
            animation_packet_pointers.add(group.snes_pointer)
            animation_event_aliases.update(group.event_aliases)
            animation_location_aliases.update(group.location_aliases)
            if any(command.opcode == 0x87 for command in source_commands):
                graphics_override_source_owners += 1

            outgoing_target_owner_ids = topology.target_source_owners[
                source_object_id
            ]
            incoming_logical_owner_ids = topology.incoming_logical_owners[
                source_object_id
            ]
            context_source_owner_ids = (
                topology.direct_entry_context_source_owners[source_object_id]
            )
            cross_owner_context = any(
                owner_id != source_object_id
                for owner_id in outgoing_target_owner_ids
            )
            direct_entry_context_counts["animation_source_owners"] += 1
            direct_entry_context_counts[
                "incoming_logical_owner_associations"
            ] += len(incoming_logical_owner_ids)
            external_incoming_count = sum(
                logical_owner_id != source_object_id
                for logical_owner_id in incoming_logical_owner_ids
            )
            direct_entry_context_counts[
                "external_incoming_logical_owner_associations"
            ] += external_incoming_count
            if external_incoming_count:
                direct_entry_context_counts[
                    "animation_source_owners_with_external_incoming_owner"
                ] += 1
            else:
                direct_entry_context_counts[
                    "animation_source_owners_with_self_only_incoming_owner"
                ] += 1
            direct_entry_context_counts[
                "maximum_incoming_logical_owners"
            ] = max(
                direct_entry_context_counts[
                    "maximum_incoming_logical_owners"
                ],
                len(incoming_logical_owner_ids),
            )
            direct_entry_context_counts[
                "direct_entry_context_source_owner_associations"
            ] += len(context_source_owner_ids)
            if any(
                owner_id != source_object_id
                for owner_id in context_source_owner_ids
            ):
                direct_entry_context_counts[
                    "animation_source_owners_with_extended_context_closure"
                ] += 1
                packets_with_extended_context_closure.add(group.snes_pointer)
            topology_counts[
                "animation_source_owners_with_cross_owner_entries"
                if cross_owner_context
                else "animation_source_owners_without_cross_owner_entries"
            ] += 1
            marker_commands = direct_entry_marker_commands(
                commands_by_object,
                topology,
                source_object_id,
            )
            classification = classify_object(marker_commands)
            physical_classification = classify_object(source_commands)
            physical_owner_only_counts[physical_classification.scope] += 1
            extra_context_owner_ids = set(context_source_owner_ids) - {
                source_object_id
            }
            if any(
                command.opcode in SOURCE_MARKER_OPCODES
                for owner_id in extra_context_owner_ids
                for command in commands_by_object[owner_id]
            ):
                direct_entry_context_counts[
                    "animation_source_owners_with_marker_union_change"
                ] += 1
                packets_with_marker_union_change.add(group.snes_pointer)
            if classification.scope != physical_classification.scope:
                topology_counts[
                    "direct_entry_classification_changes_from_"
                    "physical_owner_only"
                ] += 1
                classification_change_ledger.append(
                    {
                        "packet_pointer": group.snes_pointer,
                        "source_object_id": source_object_id,
                        "physical_scope": physical_classification.scope,
                        "marker_union_scope": classification.scope,
                    }
                )
            if classification.invalid_generic_markers:
                raise AnimationOperandAuditError(
                    "out-of-domain generic PC marker reached an animation "
                    "source-owner marker union"
                )
            if "graphics_override" in classification.alternate_markers:
                direct_entry_graphics_contexts += 1
            direct_entry_graphics_associations += sum(
                command.opcode == 0x87 for command in marker_commands
            )

            source_owner_scope_counts[classification.scope] += 1
            if classification.has_pc_loader:
                source_owner_scope_counts[
                    "direct_entry_pc_marker_union_source_owners"
                ] += 1
                if classification.loader_kind is None:
                    raise AnimationOperandAuditError(
                        "PC marker union lacks a loader-kind label"
                    )
                loader_kind_counts[classification.loader_kind] += 1
                pc_packet_pointers.add(group.snes_pointer)
                pc_event_aliases.update(group.event_aliases)
                pc_location_aliases.update(group.location_aliases)
            if classification.has_generic_pc_loader:
                source_owner_scope_counts[
                    "direct_entry_generic_pc_marker_union_source_owners"
                ] += 1
                generic_pc_packet_pointers.add(group.snes_pointer)
                generic_event_aliases.update(group.event_aliases)
                generic_location_aliases.update(group.location_aliases)

            for _opcode, pc_id in classification.dedicated_markers:
                dedicated_pc_associations[pc_id] += 1
            for _opcode, pc_id in classification.generic_markers:
                generic_pc_associations[pc_id] += 1
            for marker in classification.alternate_markers:
                alternate_marker_context_counts[
                    f"{classification.scope}:{marker}"
                ] += 1
            if classification.scope == "pc_and_nonpc_loader_markers":
                mixed_marker_counts[
                    "+".join(classification.alternate_markers)
                ] += 1

            members = _scope_members(classification)
            for command in marker_commands:
                if command.opcode in LIFECYCLE_ROLE_MARKERS:
                    for scope_name in members:
                        lifecycle_marker_associations[scope_name][
                            command.opcode
                        ] += 1

            per_source_opcode_counts: collections.Counter[str] = (
                collections.Counter()
            )
            for command in animation_commands:
                contract = ANIMATION_OPCODE_CONTRACTS[command.opcode]
                expected_width = int(contract["payload_width"])
                if len(command.payload) != expected_width:
                    raise AnimationOperandAuditError(
                        f"animation opcode ${command.opcode:02X} "
                        "operand width drifted"
                    )
                operands = tuple(command.payload)
                for scope_name in members:
                    opcode_counts[scope_name][command.opcode] += 1
                    event_instance_counts[scope_name][command.opcode] += len(
                        group.event_aliases
                    )
                    location_instance_counts[scope_name][command.opcode] += len(
                        group.location_aliases
                    )
                    operand_tuples[scope_name][command.opcode][operands] += 1
                per_source_opcode_counts[_hex_opcode(command.opcode)] += 1
                site_ledger.append(
                    {
                        "packet_pointer": group.snes_pointer,
                        "event_aliases": list(group.event_aliases),
                        "location_aliases": list(group.location_aliases),
                        "source_object_id": source_object_id,
                        "event_data_offset": command.offset,
                        "opcode": command.opcode,
                        "operands": list(operands),
                        "marker_union_scope": classification.scope,
                        "loader_kind": classification.loader_kind,
                        "pc_operand_ids": list(classification.pc_operand_ids),
                        "outgoing_target_source_owners": list(
                            outgoing_target_owner_ids
                        ),
                        "incoming_logical_owners": list(
                            incoming_logical_owner_ids
                        ),
                        "direct_entry_context_source_owners": list(
                            context_source_owner_ids
                        ),
                        "alternate_markers": list(
                            classification.alternate_markers
                        ),
                    }
                )

            source_owner_ledger.append(
                {
                    "packet_pointer": group.snes_pointer,
                    "event_aliases": list(group.event_aliases),
                    "location_aliases": list(group.location_aliases),
                    "source_object_id": source_object_id,
                    "outgoing_target_source_owners": list(
                        outgoing_target_owner_ids
                    ),
                    "incoming_logical_owners": list(
                        incoming_logical_owner_ids
                    ),
                    "direct_entry_context_source_owners": list(
                        context_source_owner_ids
                    ),
                    "marker_union_scope": classification.scope,
                    "physical_owner_scope": physical_classification.scope,
                    "loader_kind": classification.loader_kind,
                    "pc_operand_ids": list(classification.pc_operand_ids),
                    "dedicated_markers": [
                        list(row) for row in classification.dedicated_markers
                    ],
                    "generic_markers": [
                        list(row) for row in classification.generic_markers
                    ],
                    "alternate_markers": list(
                        classification.alternate_markers
                    ),
                    "animation_opcode_counts": dict(
                        sorted(per_source_opcode_counts.items())
                    ),
                }
            )

    pointer_alias_groups = [
        group for group in groups if len(group.event_aliases) > 1
    ]
    equivalence_groups = [
        sorted(pointers)
        for pointers in content_groups.values()
        if len(pointers) > 1
    ]
    topology_counts.update(
        {
            "packet_pointer_alias_groups": len(pointer_alias_groups),
            "packet_pointer_alias_extra_event_ids": sum(
                len(group.event_aliases) - 1 for group in pointer_alias_groups
            ),
            "unique_decompressed_content_digests": len(content_groups),
            "content_equivalence_groups": len(equivalence_groups),
            "content_equivalence_extra_packet_pointers": sum(
                len(pointers) - 1 for pointers in equivalence_groups
            ),
            "largest_content_equivalence_group": max(
                map(len, equivalence_groups), default=1
            ),
        }
    )
    direct_entry_context_counts[
        "packets_with_extended_context_closure"
    ] = len(packets_with_extended_context_closure)
    direct_entry_context_counts["packets_with_marker_union_change"] = len(
        packets_with_marker_union_change
    )
    direct_entry_context_counts[
        "animation_source_owners_without_incoming_owner"
    ] = 0
    for name, expected in EXPECTED_TOPOLOGY_COUNTS.items():
        if topology_counts[name] != expected:
            raise AnimationOperandAuditError(
                f"canonical topology count {name} drifted: "
                f"{topology_counts[name]} != {expected}"
            )
    for name, expected in EXPECTED_DIRECT_ENTRY_CONTEXT_COUNTS.items():
        if direct_entry_context_counts[name] != expected:
            raise AnimationOperandAuditError(
                f"direct-entry context count {name} drifted: "
                f"{direct_entry_context_counts[name]} != {expected}"
            )
    if graphics_override_source_owners != EXPECTED_GRAPHICS_OVERRIDE_SOURCE_OWNERS:
        raise AnimationOperandAuditError(
            "animation source-owner graphics-override count drifted"
        )
    if (
        direct_entry_graphics_contexts
        != EXPECTED_DIRECT_ENTRY_GRAPHICS_CONTEXTS
        or direct_entry_graphics_associations
        != EXPECTED_DIRECT_ENTRY_GRAPHICS_ASSOCIATIONS
    ):
        raise AnimationOperandAuditError(
            "direct-entry graphics-override association counts drifted"
        )
    if dict(dedicated_pc_associations) != EXPECTED_DEDICATED_PC_MARKER_ASSOCIATIONS:
        raise AnimationOperandAuditError(
            "dedicated PC marker-association counts drifted"
        )
    if dict(generic_pc_associations) != EXPECTED_GENERIC_PC_MARKER_ASSOCIATIONS:
        raise AnimationOperandAuditError(
            "generic PC marker-association counts drifted"
        )

    absolute_references = PARSER.scan_absolute_memory_references(all_commands)
    identity_array_references = [
        reference
        for reference in absolute_references
        if any(
            reference.address < end_exclusive
            and start < reference.address + reference.width
            for start, end_exclusive in IDENTITY_ARRAY_RANGES
        )
    ]
    identity_array_writes = [
        reference
        for reference in identity_array_references
        if reference.access == "write"
    ]
    if len(absolute_references) != EXPECTED_ABSOLUTE_REFERENCE_COUNT:
        raise AnimationOperandAuditError(
            "absolute-memory reference corpus count drifted"
        )
    if len(identity_array_references) != EXPECTED_IDENTITY_ARRAY_READ_COUNT:
        raise AnimationOperandAuditError(
            "object identity-array absolute-read count drifted"
        )
    if identity_array_writes or any(
        reference.access != "read" or reference.opcode != 0x48
        for reference in identity_array_references
    ):
        raise AnimationOperandAuditError(
            "object identity-array direct-write/read contract drifted"
        )

    coverage = {
        "location_records": PARSER.LOCATION_COUNT,
        "pointer_entries": PARSER.EVENT_ID_COUNT,
        "location_referenced_event_ids": len(
            set(PARSER.location_event_ids(rom))
        ),
        "unique_packet_pointers": len(groups) + len(placeholder_groups),
        "decoded_packet_groups": len(groups),
        "decoded_event_id_entries": sum(
            len(group.event_aliases) for group in groups
        ),
        "non_script_packet_groups": len(placeholder_groups),
        "non_script_event_id_entries": sum(
            len(row["event_aliases"]) for row in placeholder_groups
        ),
        "commands_parsed": len(all_commands),
        "event_id_command_instances": sum(
            len(group.commands) * len(group.event_aliases)
            for group in groups
        ),
        "objects_parsed": sum(group.object_count for group in groups),
        "packet_addenda": sum(group.addendum_count for group in groups),
        "animation_objects": source_owner_scope_counts[
            "animation_source_owners"
        ],
        "animation_commands": len(site_ledger),
        "animation_packet_groups": len(animation_packet_pointers),
        "animation_event_aliases": len(animation_event_aliases),
        "animation_location_aliases": len(animation_location_aliases),
        "pc_marker_animation_packet_groups": len(pc_packet_pointers),
        "pc_marker_animation_event_aliases": len(pc_event_aliases),
        "pc_marker_animation_location_aliases": len(pc_location_aliases),
        "generic_pc_marker_animation_packet_groups": len(
            generic_pc_packet_pointers
        ),
        "generic_pc_marker_animation_event_aliases": len(
            generic_event_aliases
        ),
        "generic_pc_marker_animation_location_aliases": len(
            generic_location_aliases
        ),
        "expected_placeholder_groups": len(EXPECTED_PLACEHOLDER_GROUPS),
        "expected_placeholder_event_ids": sum(
            len(row["event_ids"])
            for row in EXPECTED_PLACEHOLDER_GROUPS.values()
        ),
        "unexpected_decompression_failures": 0,
        "unexpected_parse_failures": 0,
        "alias_ledger_sha256": _json_hash(alias_ledger),
        "placeholder_ledger_sha256": _json_hash(placeholder_groups),
        "topology_ledger_sha256": _json_hash(topology_ledger),
        "animation_source_owner_ledger_sha256": _json_hash(
            source_owner_ledger
        ),
        "animation_site_ledger_sha256": _json_hash(site_ledger),
    }
    scope_counts = {
        "direct_entry_pc_without_nonpc_loader_source_owners": (
            source_owner_scope_counts["pc_without_nonpc_loader_markers"]
        ),
        "direct_entry_pc_and_nonpc_loader_marker_source_owners": (
            source_owner_scope_counts["pc_and_nonpc_loader_markers"]
        ),
        "direct_entry_no_pc_marker_source_owners": source_owner_scope_counts[
            "no_pc_markers"
        ],
        "direct_entry_pc_marker_union_source_owners": (
            source_owner_scope_counts[
                "direct_entry_pc_marker_union_source_owners"
            ]
        ),
        "direct_entry_generic_pc_marker_union_source_owners": (
            source_owner_scope_counts[
                "direct_entry_generic_pc_marker_union_source_owners"
            ]
        ),
    }
    _validate_expected_counts(
        coverage,
        scope_counts,
        opcode_counts,
        loader_kind_counts,
        mixed_marker_counts,
    )
    if dict(event_instance_counts["all_encoded_animation_sites"]) != (
        EXPECTED_EVENT_INSTANCE_COUNTS
    ):
        raise AnimationOperandAuditError(
            "animation event-ID instance counts drifted"
        )
    for opcode, expected_distinct in EXPECTED_SELECTOR_DISTINCT_COUNTS.items():
        tuples = operand_tuples["all_encoded_animation_sites"][opcode]
        if opcode == 0xAC:
            domain = {operands[0] for operands in tuples}
        else:
            domain = {
                _effective_selector(opcode, bytes(operands))
                for operands in tuples
            }
        if None in domain or len(domain) != expected_distinct:
            raise AnimationOperandAuditError(
                f"opcode ${opcode:02X} selector/static domain drifted"
            )

    expected_physical_baseline = {
        "pc_without_nonpc_loader_markers": 939,
        "pc_and_nonpc_loader_markers": 9,
        "no_pc_markers": 1_796,
    }
    if dict(physical_owner_only_counts) != expected_physical_baseline:
        raise AnimationOperandAuditError(
            "physical-owner-only comparison baseline drifted"
        )

    tool_raw = pathlib.Path(__file__).resolve().read_bytes()
    animation_contract_rows = {
        _hex_opcode(opcode): {
            "handler_bank_c0": int(contract["handler"]),
            "total_width": int(contract["payload_width"]) + 1,
            "role": contract["role"],
            "effective_selector": contract["effective_selector"],
            "namespace": contract["namespace"],
        }
        for opcode, contract in sorted(ANIMATION_OPCODE_CONTRACTS.items())
    }
    distribution_rows: dict[str, object] = {}
    for scope_name in PUBLIC_RESULT_SCOPES:
        distribution_rows[scope_name] = {
            "by_opcode": {
                _hex_opcode(opcode): _distribution_row(
                    opcode,
                    operand_tuples[scope_name][opcode],
                    event_instance_counts[scope_name][opcode],
                    location_instance_counts[scope_name][opcode],
                    include_ranges=(
                        scope_name == "all_encoded_animation_sites"
                    ),
                )
                for opcode in sorted(ANIMATION_OPCODE_CONTRACTS)
            }
        }

    content_equivalence_ledger = [
        {
            "decompressed_sha256": digest,
            "packet_pointers": sorted(pointers),
        }
        for digest, pointers in sorted(content_groups.items())
    ]
    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "auditor_version": AUDITOR_VERSION,
        "status": "pass-metadata-only-encoded-census-with-unresolved-contexts",
        "scope": {
            "canonical_variant": "Chrono Trigger US Rev0, headerless",
            "read_only": True,
            "encoded_location_event_census_complete": True,
            "direct_function_entry_marker_overapprox_complete": True,
            "runtime_context_classification_complete": False,
            "runtime_performed": False,
            "field_location_events_included": True,
            "battle_included": False,
            "menu_included": False,
            "overworld_included": False,
        },
        "inputs": {
            "canonical_rom": rom_identity,
            "tool_source": {
                "path": "tools/audit_location_event_animation_operands_v0.py",
                "size": len(tool_raw),
                "sha256": _sha256(tool_raw),
            },
            "parser_dependency": {
                "path": "tools/audit_location_event_items.py",
                "size": PARSER_EXPECTED_SIZE,
                "sha256": PARSER_EXPECTED_SHA256,
            },
            "engine_contract": engine_contract,
            "interpretive_reference": {
                "evidence": "documented",
                "upstream": "https://github.com/dscotton/ct_disassembly",
                "expected_commit": (
                    "eeae27acdb6565e96d1d796a3d60792c250c0aa1"
                ),
                "path": "references/ct_disassembly",
                "auditor_reads_checkout": False,
                "authority": (
                    "labels only; canonical ROM dispatch, code preimages, "
                    "pointer topology, and operands are the byte authority"
                ),
            },
        },
        "coverage": coverage,
        "alias_topology": {
            "counts": {
                name: topology_counts[name]
                for name in sorted(EXPECTED_TOPOLOGY_COUNTS)
            },
            "direct_function_entry_context_counts": {
                name: direct_entry_context_counts[name]
                for name in sorted(EXPECTED_DIRECT_ENTRY_CONTEXT_COUNTS)
            },
            "definitions": {
                "source_owner": (
                    "the physical half-open command span from one function-0 "
                    "start to the next; not a runtime logical object proof"
                ),
                "same_start_alias": (
                    "a repeated function-entry address; never presumed empty"
                ),
                "packet_end_sentinel": (
                    "a one-past-decoded-data target with no physical source "
                    "owner; excluded from the marker union while its runtime "
                    "meaning remains unresolved"
                ),
                "content_equivalence": (
                    "equal decoded-content digest across distinct encoded "
                    "packet pointers; source packets remain separate"
                ),
            },
            "all_function_targets_on_command_or_packet_end_boundaries": True,
            "function_zero_starts_strictly_increasing": True,
            "content_equivalence_ledger_sha256": _json_hash(
                content_equivalence_ledger
            ),
            "classification_change_ledger_sha256": _json_hash(
                classification_change_ledger
            ),
        },
        "command_contract": {
            "animation_opcodes": animation_contract_rows,
            "dedicated_pc_loaders": {
                _hex_opcode(opcode): pc_id
                for opcode, pc_id in sorted(DEDICATED_PC_LOADERS.items())
            },
            "generic_pc_loaders": {
                _hex_opcode(opcode): {
                    "total_width": EXPECTED_COMMAND_SIZES[opcode],
                    "canonical_operand_domain": _value_domain(
                        global_generic_domains[opcode],
                        include_ranges=True,
                    ),
                    "vanilla_pc_domain_minimum": 0,
                    "vanilla_pc_domain_maximum": 6,
                    "outside_domain_policy": "unknown-pc-like-not-project-epoch",
                }
                for opcode in sorted(GENERIC_PC_LOADERS)
            },
            "alternate_loaders": {
                "82": {
                    "role": "npc_loader",
                    "total_width": 2,
                },
                "83": {
                    "role": "enemy_loader",
                    "total_width": 3,
                    "operand_zero": "enemy_id",
                    "operand_one": "graphics_and_cache_slot_flags",
                },
            },
            "graphics_override_87": {
                "total_width": 2,
                "role": "graphics_assignment_override_not_identity_loader",
                "operand_domain": _value_domain(
                    graphics_override_operands,
                    include_ranges=True,
                ),
                "operand_7f_occurrences": graphics_override_operands[0x7F],
                "bitfield_model_status": "not-used-for-runtime-classification",
            },
            "lifecycle_role_markers": {
                _hex_opcode(opcode): {
                    "role": role,
                    "unique_encoded_occurrences": global_lifecycle_counts[
                        opcode
                    ],
                }
                for opcode, role in sorted(LIFECYCLE_ROLE_MARKERS.items())
            },
            "absolute_identity_array_audit": {
                "ranges": [
                    {"start": start, "end_exclusive": end_exclusive}
                    for start, end_exclusive in IDENTITY_ARRAY_RANGES
                ],
                "absolute_references_total": len(absolute_references),
                "identity_array_overlaps": len(identity_array_references),
                "read_overlaps": len(identity_array_references),
                "write_overlaps": 0,
                "overlap_opcode": 0x48,
                "direct_write_gate_pass": True,
                "indirect_or_computed_write_proof_complete": False,
            },
        },
        "result_domains": distribution_rows,
        "context_classification": {
            "method": (
                "retain each encoded animation site once under its physical "
                "source owner; collect every incoming logical owner with a "
                "direct function entry into that source owner; then union "
                "loader markers from each distinct source owner targeted by "
                "those logical owners; exact packet-end targets add no source"
            ),
            "ceiling": (
                "complete only over the sixteen direct function entries per "
                "logical object; site, function, and order false positives "
                "are intentional, while calls, jumps, fallthrough, startup "
                "replay, lifecycle order, and runtime identity stay unresolved"
            ),
            "marker_union_counts": scope_counts,
            "physical_owner_only_comparison_counts": (
                dict(sorted(physical_owner_only_counts.items()))
            ),
            "loader_kind_counts": dict(sorted(loader_kind_counts.items())),
            "mixed_marker_combination_counts": dict(
                sorted(mixed_marker_counts.items())
            ),
            "alternate_marker_context_counts": dict(
                sorted(alternate_marker_context_counts.items())
            ),
            "dedicated_pc_marker_associations": {
                str(pc_id): dedicated_pc_associations[pc_id]
                for pc_id in range(7)
            },
            "generic_pc_marker_associations": {
                str(pc_id): generic_pc_associations[pc_id]
                for pc_id in range(7)
            },
            "global_loader_command_counts": {
                _hex_opcode(opcode): global_loader_counts[opcode]
                for opcode in sorted(global_loader_counts)
            },
            "lifecycle_marker_associations": {
                scope_name: {
                    _hex_opcode(opcode): counter[opcode]
                    for opcode in sorted(LIFECYCLE_ROLE_MARKERS)
                }
                for scope_name, counter in lifecycle_marker_associations.items()
            },
            "animation_source_owners_with_graphics_override": (
                graphics_override_source_owners
            ),
            "direct_entry_contexts_with_graphics_override": (
                direct_entry_graphics_contexts
            ),
            "direct_entry_graphics_override_command_associations": (
                direct_entry_graphics_associations
            ),
            "out_of_domain_generic_pc_markers": 0,
            "runtime_reachability_resolved": False,
            "direct_function_entry_marker_overapprox_complete": True,
        },
        "ambiguities": {
            "logical_function_entries_without_cfg_state_proof": (
                topology_counts["function_pointer_entries"]
            ),
            "encoded_animation_sites_without_runtime_reachability_proof": (
                len(site_ledger)
            ),
            "animation_source_owners_with_cross_owner_targets": (
                topology_counts[
                    "animation_source_owners_with_cross_owner_entries"
                ]
            ),
            "animation_source_owners_with_graphics_override": (
                graphics_override_source_owners
            ),
            "unsupported_control_transfers": "not-evaluated-no-cfg-claim",
            "loader_lifetime_model_complete": False,
            "graphics_bitfield_path_model_complete": False,
            "indirect_state_writer_model_complete": False,
        },
        "reproduction": {
            "command": (
                "python tools/audit_location_event_animation_operands_v0.py "
                "CANONICAL_HEADERLESS_ROM > REPORT_JSON"
            ),
            "output_mode": "stdout-only-no-output-path-option",
            "canonical_json": True,
            "schema_shape_sha256": "",
            "semantic_content_sha256": "",
        },
        "evidence": {
            "label": "verified-static",
            "encoded_census_complete": True,
            "direct_function_entry_marker_overapprox_complete": True,
            "contextual_runtime_classification_complete": False,
            "runtime_performed": False,
            "canonical_count_gates_pass": True,
            "metadata_only": True,
            "rom_installable": False,
            "next_gate": (
                "implement or explicitly defer a closed inter-object control-"
                "flow and loader-lifetime model before using the census as "
                "runtime PC attribution"
            ),
        },
        "nonclaims": [
            "No runtime reachability, story-branch execution, execution frequency, or function-call proof is made.",
            "No encoded animation site is claimed to execute while a playable-PC loader is live; the direct-entry marker overapproximation is syntax-only.",
            "A graphics override does not prove which graphics source or logical identity is effective at an animation site.",
            "Opcode $AC selects the static assembly-frame namespace and is not an animation entrypoint selector.",
            "Opcodes $AB and $B7 select secondary animation entrypoints; $B7 operand two controls repetition/progress and is never an entrypoint selector.",
            "An entrypoint begins at selector times four; four bytes is a pointer stride, not a fixed animation-record length.",
            "No visual-semantic name is assigned to an operand solely from this census.",
            "No complete playable-character animation packet requirement is inferred from encoded field scripts.",
            "No battle, menu, overworld, modified-ROM, save/load, New Game+, recruitment, or Epoch safety result is claimed.",
            "No logical PC $07, Schala runtime, graphics-source $07, naming path, hook, expanded allocation, or ROM installation is approved.",
            "No unused operand or table position is declared free.",
            "No raw ROM, decoded packet, ordered script, site list, trace, image, save, state, emulator binary, or patch is serialized by this report.",
        ],
    }
    report["reproduction"]["schema_shape_sha256"] = public_schema_sha256(  # type: ignore[index]
        report
    )
    report["reproduction"][  # type: ignore[index]
        "semantic_content_sha256"
    ] = public_semantic_sha256(report)
    validate_public_report(report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rom = args.rom.read_bytes()
    sys.stdout.buffer.write(canonical_report_bytes(build_report(rom)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
