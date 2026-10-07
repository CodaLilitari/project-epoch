#!/usr/bin/env python3
"""Read-only, metadata-only insertion inventory for canonical event $0125.

This is not an event builder, generic event editor, control-flow proof, or PC07
implementation. The reviewed operand schema is deliberately limited to the
selected packet. Unknown opcodes, submodes, target domains and cross-object
branches fail closed. No script, ROM, patch, or decompressed bytes are emitted.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "tools/audit_location_event_items.py"
BANK_PATH = ROOT / "references/ct_disassembly/bank_C0.asm"
PARSER_SHA256 = "cb39dd4485e6330c4f9d5b8817fe8e6a161cb2e965020cb1cd10a3fd30f7812a"
BANK_SHA256 = "b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8"
PACKET_SHA256 = "5ab273bea9f74dc33270f2a9adb2d7a118e00096f8bf854514627f21142ceaa0"
DESIGN_SHA256 = "243b78eeca4b645c749af299ffa679e21d158464f746685f60d53c50afefd37b"
EVENT_ID = 0x125
INSERT_OBJECT = 8
DEFAULT_BODY_SIZE = 160  # Assessed object1 body159 + one-byte generic-loader growth.


class AuditError(RuntimeError):
    """A required, explicitly reviewed remapping premise was not established."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def metadata_digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def load_parser():
    if sha256(PARSER_PATH.read_bytes()) != PARSER_SHA256:
        raise AuditError("location-event parser source drift")
    spec = importlib.util.spec_from_file_location("epoch_remap_v1_parser", PARSER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PARSER = load_parser()

# Independently reviewed target-operand schema; hashes pin the sources, not the
# truth of these semantic interpretations. No 'all other commands are safe'
# fallback exists. Handler addresses are checked against the canonical table.
# Domains concern encoded operands only, not all downstream memory effects.
SCHEMA_GROUPS = (
    ("return_or_yield", {0x00: 0xC05F74, 0xB0: 0xC03002,
                         0xB1: 0xC0353F, 0xB2: 0xC03543}),
    ("direct_object_call", {0x03: 0xC0607E, 0x04: 0xC06109}),
    ("active_role_call", {0x05: 0xC061E9, 0x07: 0xC06214}),
    ("direct_object_property", {0x1F: 0xC05579, 0x7C: 0xC04CEC}),
    ("active_role_coordinates_to_script_memory", {0x22: 0xC065EB}),
    ("relative_branch", {0x10: 0xC062B5, 0x11: 0xC062CB,
                         0x12: 0xC062DE, 0x16: 0xC063E6,
                         0x31: 0xC066BC, 0xD2: 0xC038E8}),
    ("self_property_or_animation", {
        0x0E: 0xC062A4, 0x0F: 0xC05535, 0x17: 0xC05539,
        0x1B: 0xC0553D, 0x1D: 0xC05541, 0x84: 0xC04867,
        0x89: 0xC04B49, 0x8B: 0xC04B74, 0x8E: 0xC04C74,
        0x90: 0xC04CD5, 0x91: 0xC04CE0, 0xA0: 0xC05129,
        0xAA: 0xC02E67, 0xAB: 0xC02E9A, 0xAC: 0xC02F71,
        0xAD: 0xC02F96, 0xAE: 0xC02E8F, 0xB7: 0xC02F01}),
    ("fixed_logical_pc_loader", {
        0x57: 0xC041E4, 0x5C: 0xC041EC, 0x62: 0xC041F4,
        0x68: 0xC041FC, 0x6A: 0xC04204, 0x6C: 0xC0420C,
        0x6D: 0xC04214}),
    ("graphics_source_not_object_id", {0x82: 0xC04590, 0x87: 0xC04876}),
    ("self_palette_mode", {0x88: 0xC04892}),
    ("absolute_memory", {0x48: 0xC06792, 0x4B: 0xC067FB}),
    ("event_or_script_memory", {0x56: 0xC069A6, 0x65: 0xC06B76,
                               0x66: 0xC06BA4, 0x75: 0xC06CBD,
                               0x77: 0xC06CF0}),
    ("dialog_pointer_or_id", {0xB8: 0xC03557, 0xC1: 0xC035B5}),
    ("global_control_or_timing", {0xC8: 0xC03757, 0xE3: 0xC03C05,
                                  0xE7: 0xC03E30, 0xE8: 0xC03C11,
                                  0xF0: 0xC03CD0, 0xF2: 0xC03CFD}),
    ("audio", {0xEA: 0xC03C2F, 0xEB: 0xC03C4C,
               0xEC: 0xC03C98, 0xED: 0xC03CBC}),
    ("implicit_active_roles_and_fixed_builtin_script", {0xD9: 0xC0326C,
                                                        0xDA: 0xC0345A}),
    ("location_transition", {0xDD: 0xC03B1B, 0xDF: 0xC03B98}),
    ("native_scene_submode", {0xFF: 0xC03FAF}),
)
SCHEMA = {op: (domain, handler) for domain, ops in SCHEMA_GROUPS for op, handler in ops.items()}
DIRECT_OPS = {0x03, 0x04, 0x1F, 0x7C}
ROLE_OPS = {0x05, 0x07, 0x22}
BRANCH_OPS = {0x10, 0x11, 0x12, 0x16, 0x31, 0xD2}
CALL_OPS = {0x03, 0x04, 0x05, 0x07}

# Native source spans (start inclusive, end exclusive) for the distinctions.
# This is finite operand evidence; it does not close all callee effects.
SOURCE_SPANS = (
    ("direct_call03", 0xC0607E, 0xC060EB),
    ("direct_call04", 0xC06109, 0xC061A7),
    ("active_role05_07", 0xC061E9, 0xC0622A),
    ("direct_facing", 0xC0554D, 0xC05557),
    ("direct_facing_operand", 0xC05579, 0xC05585),
    ("drawing_operand", 0xC04CD5, 0xC04CF8),
    ("coordinate_role", 0xC065BF, 0xC065F7),
    ("relative10_11", 0xC062B5, 0xC062DD),
    ("relative12", 0xC062DE, 0xC06361),
    ("relative16", 0xC063E6, 0xC06424),
    ("relative31", 0xC066BC, 0xC06705),
    ("relativeD2", 0xC038E8, 0xC03919),
    ("implicit_rolesD9_DA", 0xC0326C, 0xC0353F),
    ("palette88", 0xC04892, 0xC04A4E),
    ("locationDD_DF", 0xC03B1B, 0xC03B9D),
    ("native_sceneFF", 0xC03FAF, 0xC0405D),
    ("event_pointer_and_builtin_loader", 0xC056D4, 0xC05709),
    ("builtin_loader", 0xC05CEC, 0xC05D37),
)


def relocate_offset(offset: int, insertion_offset: int, new_body_size: int) -> int:
    return offset + 32 + (new_body_size if offset >= insertion_offset else 0)


def remap_object_operand(operand: int, count: int, insertion: int) -> int:
    if operand % 2 or not 0 <= operand < 2 * count:
        raise AuditError("direct object operand is not an in-packet doubled index")
    mapped = operand + (2 if operand // 2 >= insertion else 0)
    if mapped > 0xFE:
        raise AuditError("remapped direct object operand overflows")
    return mapped


def role_index(operand: int) -> int:
    if operand not in (0, 2, 4):
        raise AuditError("unreviewed active-party role operand")
    return operand // 2


def branch_target(command) -> int:
    if command.opcode not in BRANCH_OPS:
        raise AuditError("unreviewed branch opcode")
    anchor = command.offset + len(command.payload)
    return anchor + (-1 if command.opcode == 0x11 else 1) * command.payload[-1]


def inspect_packet(packet: bytes, new_body_size: int = DEFAULT_BODY_SIZE, insertion: int = INSERT_OBJECT) -> dict:
    """Inventory existing bytes and hypothetical offset arithmetic, never build bytes.

    Synthetic callers may exercise this reviewed schema, but only audit_rom()
    binds a result to the selected canonical packet. New-object function rows
    and body semantics are deliberately absent and cannot be certified here.
    """
    if type(new_body_size) is not int or new_body_size < 1:
        raise AuditError("new body size must be a positive integer")
    try:
        commands = PARSER.parse_event(EVENT_ID, packet)
    except (PARSER.AuditError, IndexError, ValueError) as exc:
        raise AuditError(f"packet parse failed: {exc}") from exc
    count = packet[0]
    if not 0 <= insertion < count:
        raise AuditError("insertion must precede an existing object")
    if count + 1 > 0x40:
        raise AuditError("object count exceeds parser domain after insertion")
    data = packet[1:]
    rows = [[int.from_bytes(data[o * 32 + f * 2:o * 32 + f * 2 + 2], "little")
             for f in range(16)] for o in range(count)]
    starts = [row[0] for row in rows]
    if starts[0] != count * 32 or any(a >= b for a, b in zip(starts, starts[1:])):
        raise AuditError("unreviewed gaps or shared/empty object bodies")
    ends = starts[1:] + [len(data)]
    boundaries = {command.offset: command for command in commands}
    insert_at = starts[insertion]
    proposed_size = len(packet) + 32 + new_body_size
    # Packet byte0 occupies $7F2000; fixed built-ins begin at $7F3700.
    if proposed_size > 0x1700:
        raise AuditError("hypothetical packet overlaps fixed builtin-script region")
    pointer_groups = []
    for obj, row in enumerate(rows):
        grouped = defaultdict(list)
        for function, target in enumerate(row):
            if target not in boundaries or not starts[obj] <= target < ends[obj]:
                raise AuditError("function pointer is not a command start in its original object")
            grouped[target].append(function)
        for target, functions in sorted(grouped.items()):
            pointer_groups.append([
                obj, obj + (obj >= insertion), functions, target,
                relocate_offset(target, insert_at, new_body_size),
            ])
    direct, roles, branches, absolute, special = [], [], [], [], []
    counts = Counter()
    required_functions = set()
    for command in commands:
        op, payload, obj, offset = command.opcode, command.payload, command.object_id, command.offset
        if op not in SCHEMA:
            raise AuditError(f"unreviewed opcode target domain {op:02X} at {offset:04X}")
        counts[op] += 1
        if op in DIRECT_OPS:
            mapped = remap_object_operand(payload[0], count, insertion)
            function = payload[1] & 15 if op in CALL_OPS else None
            priority = payload[1] >> 4 if op in CALL_OPS else None
            direct.append([obj, offset, op, payload[0] // 2, mapped // 2,
                           payload[0], mapped, function, priority])
        if op in ROLE_OPS:
            role = role_index(payload[0])
            function = payload[1] & 15 if op in CALL_OPS else None
            priority = payload[1] >> 4 if op in CALL_OPS else None
            roles.append([obj, offset, op, payload[0], role, function, priority])
            if role == 2 and function is not None:
                required_functions.add(function)
        if op in BRANCH_OPS:
            if op == 0x12 and payload[2] not in (0, 1, 4, 5):
                raise AuditError("unreviewed opcode12 comparison selector")
            if op == 0x16 and payload[2] not in (0, 6, 0x86):
                raise AuditError("unreviewed opcode16 comparison selector")
            if op == 0xD2 and payload[0] > 6:
                raise AuditError("unreviewed logical PC test domain")
            target = branch_target(command)
            if target not in boundaries or not starts[obj] <= target < ends[obj]:
                raise AuditError("relative branch leaves its original object or targets an operand")
            anchor = offset + len(payload)
            new_anchor = relocate_offset(anchor, insert_at, new_body_size)
            new_target = relocate_offset(target, insert_at, new_body_size)
            expected = (new_anchor - new_target if op == 0x11 else new_target - new_anchor)
            if not 0 <= expected <= 255 or expected != payload[-1]:
                raise AuditError("relative displacement cannot be retained")
            branches.append([obj, offset, op, anchor, target, payload[-1]])
        if op == 0x88:
            if payload[0] not in (0x00, 0x30, 0x8D):
                raise AuditError("unreviewed palette88 submode")
            if payload[0] == 0x8D and (len(payload) != 9 or payload[1:3] != b"\x08\x00"):
                raise AuditError("unreviewed palette88 literal extent")
            special.append([obj, offset, op, "self_palette", payload[0]])
        if op == 0xFF:
            if payload[0] not in (0x83, 0x90, 0x91):
                raise AuditError("unreviewed native-scene FF submode")
            special.append([obj, offset, op, "native_scene", payload[0]])
        if op in (0xD9, 0xDA):
            special.append([obj, offset, op, "implicit_roles_fixed_builtin", None])
        if op in (0xDD, 0xDF):
            special.append([obj, offset, op, "location_transition", None])
        if op in (0x48, 0x4B):
            address = int.from_bytes(payload[:3], "little")
            width = 1 if op == 0x48 else 2
            # This profile admits no selected absolute access to object arrays,
            # role pointers, the decompressed packet, or fixed builtin scripts.
            if (op, address) not in {(0x48, 0x7E2980), (0x48, 0x7E2981),
                                     (0x48, 0x7E2982), (0x4B, 0x7E02AF)}:
                raise AuditError("unreviewed absolute-memory target domain")
            absolute.append([obj, offset, op, address, width])
    return {
        "object_count_before": count, "object_count_after": count + 1,
        "command_count": len(commands),
        "offset_convention": "all offsets exclude packet count byte; table starts at offset0",
        "hypothesis": {
            "insert_new_authored_object_at": insertion,
            "new_body_size": new_body_size,
            "new_body_size_is_layout_parameter_not_authored_implementation": True,
            "old_body_insertion_offset": insert_at,
            "old_offset_to_new": "x + 32 + (new_body_size if x >= insertion_offset else 0)",
            "old_object_to_new": "i + (1 if i >= insertion_object else 0)",
            "decompressed_size_after": proposed_size,
            "maximum_new_body_size_before_builtin_overlap": 0x1700 - len(packet) - 32,
        },
        "opcode_schema_rows": [[op, counts[op], *SCHEMA[op]] for op in sorted(counts)],
        "pointer_group_columns": ["old_object", "new_object", "aliased_functions",
                                   "old_target", "new_target"],
        "function_pointer_groups": pointer_groups,
        "function_pointer_count": count * 16,
        "direct_columns": ["object", "offset", "opcode", "old_target_object",
                           "new_target_object", "old_encoded_operand", "new_encoded_operand",
                           "function_or_null", "priority_or_null"],
        "direct_references": direct,
        "changed_direct_reference_count": sum(row[5] != row[6] for row in direct),
        "role_columns": ["object", "offset", "opcode", "unchanged_operand",
                         "active_role", "function_or_null", "priority_or_null"],
        "active_role_references": roles,
        "candidate_role2_referenced_functions": sorted(required_functions),
        "candidate_role2_function_implementation_status": "not authored or validated",
        "branch_columns": ["object", "offset", "opcode", "displacement_anchor",
                           "target", "unchanged_unsigned_displacement"],
        "branches": branches,
        "branch_count": len(branches),
        "branch_inventory_sha256": metadata_digest(branches),
        "absolute_columns": ["object", "offset", "opcode", "address", "width"],
        "absolute_references": absolute,
        "special_columns": ["object", "offset", "opcode", "domain", "submode_or_null"],
        "special_references": special,
    }


def assess_selected_donors(packet: bytes) -> list[dict]:
    """Assess existing bodies only; return offsets/counts/hashes, never copy bytes.

    This deliberately recognizes exactly two source objects in the pinned
    packet. It is not a generic character-identity patcher.
    """
    commands = PARSER.parse_event(EVENT_ID, packet)
    data = packet[1:]
    roster_reads = [[c.offset, int.from_bytes(c.payload[:3], "little"), c.payload[3]]
                    for c in commands if c.object_id == 0 and c.opcode == 0x48]
    if sorted((address, slot) for _, address, slot in roster_reads) != sorted(
            [(0x7E2980 + i, 7 + i) for i in range(3)] * 2):
        raise AuditError("selected roster-to-script-memory producer changed")
    result = []
    for obj, identity, loader in ((1, 0, 0x57), (3, 2, 0x62)):
        start = int.from_bytes(data[obj * 32:obj * 32 + 2], "little")
        end = int.from_bytes(data[(obj + 1) * 32:(obj + 1) * 32 + 2], "little")
        body_commands = [c for c in commands if c.object_id == obj]
        if body_commands[0].offset != start or body_commands[0].opcode != loader:
            raise AuditError("donor dedicated-loader precondition changed")
        if any(c.opcode in DIRECT_OPS | ROLE_OPS or
               SCHEMA[c.opcode][0] in {"absolute_memory", "event_or_script_memory",
                                       "graphics_source_not_object_id"}
               for c in body_commands):
            raise AuditError("donor has an unreviewed extra target or memory-write domain")
        comparisons = [c for c in body_commands if c.opcode == 0x12]
        identity_sites, retained = [], []
        for command in comparisons:
            slot, literal, comparator, _ = command.payload
            if slot in (7, 8, 9) and literal == identity and comparator == 0:
                identity_sites.append([command.offset, command.offset + 2, slot, identity, 7])
            elif (slot, literal, comparator) == (6, 0, 1):
                retained.append([command.offset, slot, literal, comparator])
            else:
                raise AuditError("unreviewed donor comparison")
        if len(identity_sites) != 13 or len(retained) != 1:
            raise AuditError("donor identity/control comparison census changed")
        relative = [c for c in body_commands if c.opcode in BRANCH_OPS]
        # The changed loader is the first instruction. Both ends of every old
        # branch move by the same +1 within the copied body; no branch enters it.
        if any(not start < c.offset < end or not start < branch_target(c) < end
               for c in relative):
            raise AuditError("loader growth crosses a donor relative-branch endpoint")
        functions = [int.from_bytes(data[obj * 32 + f * 2:obj * 32 + f * 2 + 2], "little")
                     for f in range(16)]
        boundaries = {c.offset for c in body_commands}
        if any(target not in boundaries for target in functions):
            raise AuditError("donor has an external or unaligned function pointer")
        result.append({
            "source_object": obj, "source_logical_identity": identity,
            "source_body_start": start, "source_body_end_exclusive": end,
            "source_body_size": end - start,
            "source_body_sha256": sha256(data[start:end]),
            "command_count": len(body_commands),
            "complete_body_copy_is_assessment_only": True,
            "dedicated_loader_opcode": loader,
            "proposed_generic_loader_opcode": 0x80, "proposed_logical_identity": 7,
            "loader_growth_bytes": 1, "proposed_body_size": end - start + 1,
            "identity_comparison_columns": ["command_offset", "literal_operand_offset",
                                            "script_memory_slot", "old_literal", "proposed_literal"],
            "identity_comparisons": identity_sites,
            "retained_control_comparison_columns": ["offset", "slot", "literal", "comparator"],
            "retained_control_comparisons": retained,
            "roster_read_columns": ["offset", "absolute_roster_address", "script_memory_slot"],
            "roster_read_producers": roster_reads,
            "function_relative_targets_before": [target - start for target in functions],
            "function_relative_targets_proposed": [target - start + (target > start)
                                                   for target in functions],
            "all_functions_source_local": True,
            "direct_object_or_active_role_call_count": 0,
            "unchanged_relative_branch_count": len(relative),
            "dialogue_opcode_C1_count": sum(c.opcode == 0xC1 for c in body_commands),
            "preferred_for_donor0_graphics": obj == 1,
            "limits": ["Source-local functions3..7 exist; execution as logical07 is untested.",
                       "Identity comparisons are distinct from graphics/animation operands; only the thirteen named literals change in this proposal.",
                       "All seven original objects, bodies, identity literals and independent live records must be preserved.",
                       "No transformed packet, copied game payload or new function-pointer bytes are emitted."],
        })
    return result


def audit_rom(rom: bytes, new_body_size: int = DEFAULT_BODY_SIZE) -> dict:
    PARSER.validate_canonical_rom(rom)
    if sha256(BANK_PATH.read_bytes()) != BANK_SHA256:
        raise AuditError("reviewed bankC0 source drift")
    pointer, file_pointer = PARSER.event_pointer(rom, EVENT_ID)
    info = PARSER.decompress_packet(rom, file_pointer)
    if len(info.data) != 2361 or sha256(info.data) != PACKET_SHA256:
        raise AuditError("selected event packet drift")
    inventory = inspect_packet(info.data, new_body_size)
    for op, _, _, expected in inventory["opcode_schema_rows"]:
        position = 0x5D6E + 2 * op
        actual = 0xC00000 | int.from_bytes(rom[position:position + 2], "little")
        if actual != expected:
            raise AuditError(f"opcode {op:02X} handler mismatch")
    aliases = [eid for eid in range(PARSER.EVENT_ID_COUNT)
               if PARSER.event_pointer(rom, eid)[0] == pointer]
    locations = [lid for lid, eid in enumerate(PARSER.location_event_ids(rom)) if eid in aliases]
    if aliases != [EVENT_ID] or locations != [0x1DA]:
        raise AuditError("selected pointer or location alias scope changed")
    source_text = BANK_PATH.read_text().splitlines()
    spans = []
    for name, start, end in SOURCE_SPANS:
        line = next((i + 1 for i, text in enumerate(source_text)
                     if f";{start:06X}|" in text), None)
        if line is None:
            raise AuditError(f"missing source anchor {start:06X}")
        spans.append({"name": name, "start": start, "end_exclusive": end,
                      "source_line": line,
                      "canonical_bytes_sha256": sha256(rom[start & 0x3FFFFF:end & 0x3FFFFF])})
    source_manifest = []
    for path in (Path(__file__), PARSER_PATH, BANK_PATH,
                 ROOT / "tests/test_pc07_selected_event_remap_v1.py"):
        content = path.read_bytes()
        source_manifest.append({"path": path.resolve().relative_to(ROOT).as_posix(),
                                "size": len(content), "sha256": sha256(content)})
    return {
        "schema": "pc07-selected-event-reference-remap-v1",
        "evidence_level": "complete selected-packet static operand inventory; source-conditional semantics",
        "source_manifest": source_manifest,
        "preserved_private_design_sha256": DESIGN_SHA256,
        "rom_sha256": sha256(rom),
        "event_id": EVENT_ID, "compressed_snes_pointer": pointer,
        "compressed_file_pointer": file_pointer,
        "compressed_size": info.compressed_size,
        "decompressed_size": len(info.data), "packet_sha256": sha256(info.data),
        "scope": {"event_pointer_entries_read": PARSER.EVENT_ID_COUNT,
                  "location_records_read": PARSER.LOCATION_COUNT,
                  "packets_decompressed": 1, "event_pointer_aliases": aliases,
                  "location_aliases": locations,
                  "other_event_packets_require_rewrite_for_this_insert": False},
        "source_spans": spans, "inventory": inventory,
        "complete_body_reuse_assessment": assess_selected_donors(info.data),
        "prior_work_reused": [
            {"path": "docs/location_event_item_reference_audit.md", "lines": [30, 60, 444, 447],
             "reuse": "Accepted canonical loader/format/command parser and complete Temporal Redux length comparison; no all-corpus rerun."},
            {"path": "docs/location_event_animation_operand_census_v0.md", "lines": [108, 156],
             "reuse": "Accepted sixteen-entry topology, boundary and alias distinctions; selected-local refusal does not generalize to other packets."},
            {"path": "docs/historical_eighth_character_forum_mapping_audit_2026-08-23.md", "lines": [113, 119],
             "reuse": "Mauron's ordered-PC insertion and doubled drawing-index lead; treated as fallible mapping checked at selected native handlers."},
            {"path": "docs/schala_eighth_character_developer_guide.md", "lines": [1189, 1230, 1514, 1536],
             "reuse": "Existing corpus and identity/graphics/roster gates remain separate; no general playable claim."},
            {"path": "docs/DATA_MAPPING_CORRECTIONS.md", "lines": [1, 18],
             "reuse": "Namespace and provenance discipline; no old annotation promoted on reputation."},
        ],
        "community_implementation_reference": {
            "project": "OnemusCT/temporal-redux", "commit": "365086c1c0a33144b24bff4933998bdff82c9940",
            "url": "https://raw.githubusercontent.com/OnemusCT/temporal-redux/365086c1c0a33144b24bff4933998bdff82c9940/sourcefiles/jetsoftime/ctevent.py",
            "raw_size": 52189, "raw_sha256": "2d27b185f7009a976cf2439cc5a3c7fee6c00aa144920b6f1117f5dec7b558da",
            "existing_local_size": 53674, "existing_local_sha256": "608b2e6788724377b31b792bc17a1cc61de2e4e96f79f24940801db258ea7897",
            "comparison": "Exact bytes equal after CRLF-to-LF normalization; independently fetched raw primary bytes, not inferred from Git ref.",
            "raw_source_lines": {"object_operand_shift": [529, 563], "insert_copy_object": [670, 707]},
            "credit": "Existing insertion, pointer-shift and doubled-object-remap design is reused as an implementation reference, not claimed as new invention or executed here.",
            "known_limits": "Community method warns about inter-object calls and omits opcode1F in its object-remap list. Selected1F targets are below8; selected donor bodies have no inter-object calls.",
            "private_snapshot": "private/research/pc07_field_route_v1/ctevent_365086c_raw.py",
            "runtime_or_import_dependency": False,
        },
        "new_contribution": "Exact selected125 four-site remap,224 pointer occurrence mapping,186 unchanged branches,17 role operand sites, single-packet alias scope, and two complete donor-body identity-comparison assessments.",
        "findings": [
            "Exactly four existing explicit doubled-object operands change; all other selected direct targets retain their identity.",
            "Computed relocation targets preserve all224 existing function-pointer occurrences and alias groups; no function-pointer bytes are written.",
            "All 186 relative branch targets are decoded starts inside their original objects and retain their encoded displacements.",
            "Party-role operands0/2/4 and logical-PC, graphics, script-memory, palette, dialog, audio and location operands are separate domains.",
            "D9/DA use implicit party roles and fixed builtin scripts; those fixed script PCs must not receive packet relocation deltas.",
            "Selected palette88 mode8 data is copied as colors to self palette buffers, not interpreted as packet references.",
            "Role2 call sites request functions3,4,5,6,7; a minimal startup/yield-only PC07 object does not implement the referenced functions.",
            "Existing object1 supplies those scene functions in159 bytes without dialogue; a separate160-byte copied-body proposal requires its loader plus thirteen roster-identity literals to change, not the loader alone.",
            "This selected event can be addressed without rewriting all513 packets, conditional on a separate loader/placement design and construction audit.",
        ],
        "open_obligations": [
            "Construct and independently audit the assessed object1 copy with generic LoadPC07 and thirteen exact identity-literal changes, preserving original object1 and all seven originals.",
            "New-object function-row aliasing, all branch targets in newly authored code, and inserted body lifetime remain unproved.",
            "Runtime role-pointer publication and refresh, donor-qualified graphics adapters, fresh object creation and roster preservation remain untested.",
            "Downstream native scene FF83 and location transitions are outside this operand inventory; no all-path playable behavior claim.",
            "Compressed placement, hook approval, complete-diff guard, event emission and native observation require separate work.",
        ],
        "claims_excluded": ["event construction", "ROM mutation", "native execution",
                            "PC07 playable", "whole-event execution closure", "production allocation"],
        "reproduction": [
            "python -B tools/audit_pc07_selected_event_remap_v1.py --rom <canonical-private-US-Rev0-ROM>",
            "python -B -m unittest discover -s tests -p test_pc07_selected_event_remap_v1.py",
            "Set CT_US_REV0_ROM to the private canonical path to include the pinned-corpus test.",
        ],
    }


def main(argv=None) -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--rom", type=Path, required=True)
    argument_parser.add_argument("--new-body-size", type=int, default=DEFAULT_BODY_SIZE,
                                 help="hypothetical layout parameter only; never emits event bytes")
    args = argument_parser.parse_args(argv)
    try:
        report = audit_rom(args.rom.read_bytes(), args.new_body_size)
    except (AuditError, PARSER.AuditError, OSError) as exc:
        print(f"audit refused: {exc}", file=sys.stderr)
        return 2
    # Compact metadata keeps every reference and branch auditable without raw
    # scripts, strings, palettes, or any other extracted game payload.
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
