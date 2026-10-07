#!/usr/bin/env python3
"""Exact in-memory event0126 PC07 insertion; CLI emits metadata only.

Reuse the accepted event0125 parser, pointer layout, doubled-object operand
rules and inverse-projection construction. This destination-specific profile
copies the complete object1 body before original object8. It never emits a
ROM, patch, compressed event or raw game packet.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REUSE_PATH = ROOT / "tools/transform_pc07_selected_event_v1.py"
REUSE_SHA256 = "1213ae3f274ba044608185d9b9e806cf9f6db2cfdb0ab89f70a09de0e2ff1d3a"
REUSE_REFERENCE_PATH = ROOT / "references/pc07_selected_event_transform_v1.json"
REUSE_REFERENCE_SHA256 = "0bb253c1f296e5719b204052588f25254a045a3cc716d32127347b6e304cdd66"
EVENT_ID, LOCATION_ID = 0x126, 0x1DB
PACKET_SIZE = 1801
PACKET_SHA256 = "27f35fd7926516012297d70c9eb585bc4fda007af12e463849edfe89a1c42fa0"
OBJECT_COUNT, INSERT_OBJECT = 14, 8
DONOR_START, DONOR_END = 0x1DB, 0x22B
DONOR_SHA256 = "cc66258cfde6a1a760bc088ecb4c152ac88c1af8c05983dba924db811c203642"
INSERT_OFFSET = 0x446
NEW_BODY_SIZE = 81
NEW_BODY_START = INSERT_OFFSET + 32
NEW_BODY_END = NEW_BODY_START + NEW_BODY_SIZE
TRANSFORMED_SIZE = PACKET_SIZE + 32 + NEW_BODY_SIZE
IDENTITY_OPERANDS = (0x1E0, 0x1EA, 0x1F2, 0x204, 0x20C, 0x215)
DIRECT_OPERANDS = ((0x4C0, 24, 26), (0x4C3, 26, 28),
                   (0x671, 18, 20), (0x674, 20, 22))


class TransformError(RuntimeError):
    """The exact packet, dependencies or declared byte transformation drifted."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def metadata_digest(value) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def load_reuse():
    for path, expected in ((REUSE_PATH, REUSE_SHA256),
                           (REUSE_REFERENCE_PATH, REUSE_REFERENCE_SHA256)):
        if digest(path.read_bytes()) != expected:
            raise TransformError(f"accepted0125 dependency drift: {path.name}")
    spec = importlib.util.spec_from_file_location("epoch_lavos_transform_reuse", REUSE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # This also checks the frozen inventory/reference, parser and source pins.
    spec.loader.exec_module(module)
    return module


REUSE = load_reuse()
PARSER, INVENTORY = REUSE.PARSER, REUSE.INVENTORY
TransformResult = REUSE.TransformResult
pointer_rows = REUSE.pointer_rows

# Only the additional target-operand domains encountered in this packet.
# Existing0125 domains retain their reviewed source interpretation. These are
# encoded-reference classifications, not certificates of downstream effects.
ADDITIONAL_DOMAINS = {
    0x06: ("active_role_call", 0xC061FE),
    0x0D: ("self_movement_flags", 0xC06295),
    0x2E: ("screen_color_setup_mode", 0xC04A4E),
    0x4A: ("absolute_memory_immediate_byte", 0xC067D7),
    0x83: ("enemy_identity_and_battle_slot", 0xC046DF),
    0x8D: ("self_pixel_coordinates", 0xC04C27),
    0x96: ("self_tile_movement", 0xC04F61),
    0xB3: ("self_animation0_loop", 0xC02E87),
    0xD8: ("battle_configuration_flags", 0xC03A83),
    0xE5: ("tile_rectangle_copy", 0xC03DC5),
}
SCHEMA = {**INVENTORY.SCHEMA, **ADDITIONAL_DOMAINS,
          0xE8: ("shared_audio_command", 0xC03C11)}
ROLE_OPS = INVENTORY.ROLE_OPS | {0x06}
CALL_OPS = INVENTORY.CALL_OPS | {0x06}
ABSOLUTE_TARGETS = {
    (0x48, 0x7E2980), (0x48, 0x7E2981), (0x48, 0x7E2982),
    (0x48, 0x7F01EC), (0x4A, 0x000110), (0x4A, 0x7E2A21),
}


def old_to_new(offset: int) -> int:
    return offset + 32 + (NEW_BODY_SIZE if offset >= INSERT_OFFSET else 0)


def donor_to_new(offset: int) -> int:
    return NEW_BODY_START + offset - DONOR_START + (offset > DONOR_START)


def inspect_source(packet: bytes) -> dict:
    """Inspect this exact destination packet, without a new corpus survey."""
    if type(packet) is not bytes or len(packet) != PACKET_SIZE or digest(packet) != PACKET_SHA256:
        raise TransformError("requires exact canonical event0126 packet")
    data = packet[1:]
    commands = PARSER.parse_event(EVENT_ID, packet)
    rows = pointer_rows(data, OBJECT_COUNT)
    starts = [row[0] for row in rows]
    ends = starts[1:] + [len(data)]
    boundaries = {c.offset: c for c in commands}
    if (packet[0] != OBJECT_COUNT or starts[0] != OBJECT_COUNT * 32 or
            any(a >= b for a, b in zip(starts, starts[1:])) or
            (starts[1], ends[1], starts[INSERT_OBJECT]) != (DONOR_START, DONOR_END, INSERT_OFFSET)):
        raise TransformError("selected object-body topology changed")
    for obj, row in enumerate(rows):
        if any(t not in boundaries or not starts[obj] <= t < ends[obj] for t in row):
            raise TransformError("source function pointer leaves its own object or command boundary")
    direct, roles, branches, absolute = [], [], [], []
    for c in commands:
        op, arg = c.opcode, c.payload
        if op not in SCHEMA:
            raise TransformError(f"unknown operand target domain {op:02X}")
        if op in INVENTORY.DIRECT_OPS:
            new = INVENTORY.remap_object_operand(arg[0], OBJECT_COUNT, INSERT_OBJECT)
            direct.append([c.object_id, c.offset, op, arg[0], new])
        if op in ROLE_OPS:
            role = INVENTORY.role_index(arg[0])
            roles.append([c.object_id, c.offset, op, arg[0], role,
                          arg[1] & 15 if op in CALL_OPS else None])
        if op in INVENTORY.BRANCH_OPS:
            target = INVENTORY.branch_target(c)
            if target not in boundaries or not starts[c.object_id] <= target < ends[c.object_id]:
                raise TransformError("source branch leaves its object or enters an operand")
            if (op == 0x12 and arg[2] != 0) or (op == 0x16 and arg[2] != 0x86):
                raise TransformError("unreviewed selected comparison selector")
            if op == 0xD2 and arg[0] > 6:
                raise TransformError("unreviewed original logical-PC test")
            branches.append([c.object_id, c.offset, op, target, arg[-1]])
        if op in (0x48, 0x4A):
            address = int.from_bytes(arg[:3], "little")
            if (op, address) not in ABSOLUTE_TARGETS:
                raise TransformError("unreviewed absolute-memory domain")
            absolute.append([c.object_id, c.offset, op, address])
        if op == 0x88 and (len(arg) != 4 or arg[0] != 0x40):
            raise TransformError("unreviewed selected self-palette mode")
        if op == 0x2E and (len(arg) != 5 or arg[0] not in (0x40, 0x50)):
            raise TransformError("unreviewed selected layer-palette mode")
        if op == 0xFF:
            raise TransformError("native-scene submode not admitted by this profile")
    changed = tuple((off + 1, old, new) for _, off, _, old, new in direct if old != new)
    if changed != DIRECT_OPERANDS or (len(commands), len(branches), len(direct), len(roles)) != (522, 93, 30, 5):
        raise TransformError("selected reference census changed")
    donor = [c for c in commands if c.object_id == 1]
    donor_comparisons = [c for c in donor if c.opcode == 0x12]
    if (digest(data[DONOR_START:DONOR_END]) != DONOR_SHA256 or len(donor) != 33 or
            donor[0].opcode != 0x57 or
            tuple(c.offset + 2 for c in donor_comparisons) != IDENTITY_OPERANDS):
        raise TransformError("selected donor-body contract changed")
    for c in donor:
        if c.opcode in INVENTORY.DIRECT_OPS | ROLE_OPS or c.opcode in (0x48, 0x4A, 0xC1, 0xD2, 0xD8):
            raise TransformError("donor has an unsupported external, dialogue or battle dependency")
        if c.opcode == 0x12 and (c.payload[0] not in (7, 8, 9) or c.payload[1:3] != b"\x00\x00"):
            raise TransformError("donor comparison is not the selected roster identity")
        if c.opcode in INVENTORY.BRANCH_OPS and not DONOR_START < INVENTORY.branch_target(c) < DONOR_END:
            raise TransformError("donor branch crosses the expanded loader")
    producers = [(int.from_bytes(c.payload[:3], "little"), c.payload[3])
                 for c in commands if c.object_id == 0 and c.opcode == 0x48]
    if producers != [(0x7E2980, 7), (0x7E2981, 8), (0x7E2982, 9)]:
        raise TransformError("roster-to-script-memory producers changed")
    opcode_counts = Counter(c.opcode for c in commands)
    return {
        "offset_convention": "data offsets exclude packet count byte",
        "direct_reference_columns": ["object", "offset", "opcode", "old_doubled_target", "new_doubled_target"],
        "direct_references": direct,
        "active_role_columns": ["object", "offset", "opcode", "unchanged_operand", "role", "function"],
        "active_role_references": roles,
        "absolute_columns": ["object", "offset", "opcode", "unchanged_address"],
        "absolute_references": absolute,
        "opcode_domain_rows": [[op, opcode_counts[op], *SCHEMA[op]] for op in sorted(opcode_counts)],
        "branch_count": len(branches), "branch_inventory_sha256": metadata_digest(branches),
        "function_pointer_count": 224,
        "function_pointer_rows_sha256": metadata_digest(rows),
        "donor_command_count": len(donor), "donor_branch_count": len(donor_comparisons),
        "donor_function_relative_targets": [t - DONOR_START for t in rows[1]],
        "donor_body_sha256": DONOR_SHA256,
        "roster_read_producers": [list(row) for row in producers],
        "required_role2_functions": sorted({r[5] for r in roles if r[4] == 2}),
        "battle_command_source": {"object": 8, "offset": 0x4D4},
        "donor_semantics": "Complete placement/movement/facing/animation functions plus the preserved function4 E8 shared-audio side effect; no inter-object calls or dialogue. Six roster-ID comparisons select active-role behavior.",
        "preserved_donor_audio": {"opcode": 0xE8, "source_offset": 0x21C,
                                  "copied_offset": donor_to_new(0x21C),
                                  "function": 4, "handler": 0xC03C11,
                                  "handler_end_exclusive": 0xC03C2F,
                                  "shared_mailbox_addresses": [0x1E01, 0x1E02, 0x1E00],
                                  "native_call": 0xC70004},
        "main_cutscene_policy": "Keep all original logical-PC tests, original-PC calls and dialogue unchanged; only direct object indices shift. No complete PC07 victory/dialogue behavior claim.",
    }


def inverse_original_projection(candidate: bytes) -> bytes:
    if len(candidate) != TRANSFORMED_SIZE or candidate[0] != 15:
        raise TransformError("transformed count or size mismatch")
    data = candidate[1:]
    table = bytearray()
    for obj, row in enumerate(pointer_rows(data, 15)):
        if obj == INSERT_OBJECT:
            continue
        for target in row:
            if NEW_BODY_START <= target < NEW_BODY_END:
                raise TransformError("original function pointer enters new body")
            value = target - 32 - (NEW_BODY_SIZE if target >= NEW_BODY_END else 0)
            if not 0 <= value <= 0xFFFF:
                raise TransformError("inverse function pointer out of range")
            table.extend(value.to_bytes(2, "little"))
    restored = table + data[15 * 32:NEW_BODY_START] + data[NEW_BODY_END:]
    for offset, old, new in DIRECT_OPERANDS:
        if restored[offset] != new:
            raise TransformError("remapped direct operand differs from contract")
        restored[offset] = old
    return bytes([OBJECT_COUNT]) + bytes(restored)


def validate_transformation(original: bytes, candidate: bytes) -> dict:
    source = inspect_source(original)
    if type(candidate) is not bytes or len(candidate) != TRANSFORMED_SIZE or candidate[0] != 15:
        raise TransformError("transformed count or size mismatch")
    old_data, data = original[1:], candidate[1:]
    try:
        old_commands = PARSER.parse_event(EVENT_ID, original)
        commands = PARSER.parse_event(EVENT_ID, candidate)
    except PARSER.AuditError as exc:
        raise TransformError(f"transformed parse failed: {exc}") from exc
    rows, old_rows = pointer_rows(data, 15), pointer_rows(old_data, 14)
    by_offset = {c.offset: c for c in commands}
    for obj, row in enumerate(old_rows):
        if rows[obj + (obj >= INSERT_OBJECT)] != [old_to_new(t) for t in row]:
            raise TransformError("original function-pointer occurrences/aliases changed")
    if rows[INSERT_OBJECT] != [donor_to_new(t) for t in old_rows[1]]:
        raise TransformError("copied function-pointer occurrences/aliases changed")
    starts = [row[0] for row in rows]
    ends = starts[1:] + [len(data)]
    for obj, row in enumerate(rows):
        if any(t not in by_offset or not starts[obj] <= t < ends[obj] for t in row):
            raise TransformError("candidate function pointer leaves its object or command boundary")
    body = data[NEW_BODY_START:NEW_BODY_END]
    if body[:2] != b"\x80\x07":
        raise TransformError("copied loader must be generic LoadPC07")
    for offset in range(DONOR_START + 1, DONOR_END):
        expected = 7 if offset in IDENTITY_OPERANDS else old_data[offset]
        if data[donor_to_new(offset)] != expected:
            raise TransformError(f"undeclared copied-body difference at {offset:04X}")
    copied = [c for c in commands if c.object_id == INSERT_OBJECT]
    donor = [c for c in old_commands if c.object_id == 1]
    if (len(commands), len(copied)) != (555, 33):
        raise TransformError("candidate command census changed")
    for before, after in zip(donor, copied):
        if (after.offset != donor_to_new(before.offset) or
                after.opcode != (0x80 if before.offset == DONOR_START else before.opcode)):
            raise TransformError("copied command boundary or opcode changed")
    for c in old_commands:
        if c.opcode not in INVENTORY.BRANCH_OPS:
            continue
        mapped = by_offset.get(old_to_new(c.offset))
        target = INVENTORY.branch_target(c)
        if (mapped is None or mapped.opcode != c.opcode or mapped.payload != c.payload or
                INVENTORY.branch_target(mapped) != old_to_new(target)):
            raise TransformError("original relative branch changed")
        if c.object_id == 1:
            new = by_offset[donor_to_new(c.offset)]
            if new.payload[-1] != c.payload[-1] or INVENTORY.branch_target(new) != donor_to_new(target):
                raise TransformError("copied relative branch changed")
    inverse = inverse_original_projection(candidate)
    if inverse != original:
        raise TransformError("inverse projection fails exact original-byte preservation")
    return {
        "schema": "pc07-lavos-event-transform-v1",
        "evidence_level": "verified-static bounded in-memory event transformation",
        "event_id": EVENT_ID, "location_id": LOCATION_ID,
        "source_packet_size": len(original), "source_packet_sha256": digest(original),
        "transformed_packet_size": len(candidate), "transformed_packet_sha256": digest(candidate),
        "original_object_count": 14, "transformed_object_count": 15,
        "source_donor_object": 1, "new_object": INSERT_OBJECT,
        "new_body_start": NEW_BODY_START, "new_body_end_exclusive": NEW_BODY_END,
        "new_body_size": NEW_BODY_SIZE, "new_body_sha256": digest(body),
        "loader_change": {"original_opcode": 0x57, "generic_opcode": 0x80,
                          "logical_pc_operand": 7, "growth_bytes": 1},
        "copied_identity_changes": [{"source_operand_offset": o, "new_operand_offset": donor_to_new(o),
                                     "old_identity": 0, "new_identity": 7} for o in IDENTITY_OPERANDS],
        "original_direct_operand_changes": [{"old_operand_offset": o, "new_operand_offset": old_to_new(o),
                                             "old_value": a, "new_value": b} for o, a, b in DIRECT_OPERANDS],
        "original_function_pointer_occurrences": 224, "copied_function_pointer_occurrences": 16,
        "copied_function_targets": rows[INSERT_OBJECT],
        "original_branch_count": 93, "copied_branch_count": 6,
        "original_command_count": 522, "copied_command_count": 33, "transformed_command_count": 555,
        "inverse_projection_size": len(inverse), "inverse_projection_sha256": digest(inverse),
        "inverse_equality_scope": "Every original packet byte after reversing only the four declared doubled-index operand changes and table/body insertion.",
        "packet_end_exclusive_if_staged_at_7F2000": 0x7F2000 + len(candidate),
        "builtin_region_boundary": 0x7F3700,
        "source_inventory": source,
        "accepted0125_transform_sha256": REUSE_SHA256,
        "accepted0125_reference_sha256": REUSE_REFERENCE_SHA256,
        "implementation_reference": REUSE.REFERENCE["community_implementation_reference"],
        "limits": [
            "Only exact canonical event0126 is accepted; event0125 sources and outputs are unchanged.",
            "All seven original PC objects remain intact. New body is a private independent copy; live records are not edited here.",
            "PC07 substitutions are restricted to the new playable object loader and its six declared roster comparisons. Epoch vehicle naming selector07, name buffer, portrait/travel/boarding/save state receive no edits or ownership claim.",
            "Existing main-cutscene tests and dialogue remain tied to their original logical PCs; no all-path PC07 cutscene or victory proof.",
            "Runtime construction, donor-qualified graphics, continuous field handoff, battle initialization and Attack remain separate observations.",
            "No raw event, compressed payload, ROM, patch, native execution or production allocation is emitted or approved.",
        ],
    }


def transform_packet(original: bytes) -> TransformResult:
    inspect_source(original)
    data = original[1:]
    rows = pointer_rows(data, 14)
    donor = bytearray(b"\x80\x07" + data[DONOR_START + 1:DONOR_END])
    for offset in IDENTITY_OPERANDS:
        donor[offset - DONOR_START + 1] = 7
    changed = bytearray(data)
    for offset, old, new in DIRECT_OPERANDS:
        if changed[offset] != old:
            raise TransformError("direct operand preimage mismatch")
        changed[offset] = new
    table = bytearray()
    for obj in range(15):
        targets = ([donor_to_new(t) for t in rows[1]] if obj == INSERT_OBJECT else
                   [old_to_new(t) for t in rows[obj - (obj > INSERT_OBJECT)]])
        for target in targets:
            table.extend(target.to_bytes(2, "little"))
    candidate = bytes([15]) + bytes(table + changed[14 * 32:INSERT_OFFSET] + donor + changed[INSERT_OFFSET:])
    return TransformResult(candidate, validate_transformation(original, candidate))


def transform_from_rom(rom: bytes) -> TransformResult:
    PARSER.validate_canonical_rom(rom)
    if PARSER.location_event_ids(rom)[LOCATION_ID] != EVENT_ID:
        raise TransformError("destination location/event association changed")
    snes, offset = PARSER.event_pointer(rom, EVENT_ID)
    if snes != 0xFAE202:
        raise TransformError("destination event pointer changed")
    packet = PARSER.decompress_packet(rom, offset).data
    source = inspect_source(packet)
    for op, _, _, handler in source["opcode_domain_rows"]:
        start = 0x5D6E + 2 * op
        if 0xC00000 | int.from_bytes(rom[start:start + 2], "little") != handler:
            raise TransformError(f"native handler binding changed for {op:02X}")
    return transform_packet(packet)


def make_report(rom: bytes) -> dict:
    result = transform_from_rom(rom)
    report = dict(result.metadata)
    report["source_manifest"] = []
    for path in (Path(__file__), ROOT / "tests/test_pc07_lavos_event_transform_v1.py",
                 REUSE_PATH, REUSE_REFERENCE_PATH, INVENTORY.PARSER_PATH, INVENTORY.BANK_PATH):
        source = path.read_bytes()
        report["source_manifest"].append({"path": path.resolve().relative_to(ROOT).as_posix(),
                                          "size": len(source), "sha256": digest(source)})
    source_lines = INVENTORY.BANK_PATH.read_text().splitlines()
    report["additional_source_anchors"] = [
        {"opcode": op, "domain": domain, "handler": handler,
         "source_line": next(i + 1 for i, line in enumerate(source_lines)
                             if f";{handler:06X}|" in line)}
        for op, (domain, handler) in sorted({**ADDITIONAL_DOMAINS,
                                            0x88: SCHEMA[0x88], 0xE8: SCHEMA[0xE8]}.items())
    ]
    report["reproduction"] = [
        "python -B tools/transform_pc07_lavos_event_v1.py --rom <canonical-private-US-Rev0-ROM>",
        "Set CT_US_REV0_ROM to the private canonical path, then run python -B -m unittest discover -s tests -p test_pc07_lavos_event_transform_v1.py",
    ]
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = make_report(args.rom.read_bytes())
    except (TransformError, INVENTORY.AuditError, PARSER.AuditError, OSError) as exc:
        print(f"transform refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
