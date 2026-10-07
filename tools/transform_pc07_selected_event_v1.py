#!/usr/bin/env python3
"""Bounded in-memory event0125 transform; CLI emits metadata only.

Copy canonical object1 into index8 while keeping all seven original PC
objects. The new object's dedicated loader becomes generic LoadPC07 and its
thirteen named roster-identity comparisons become07. This is a private
runtime-staging component, not a ROM/patch builder or general event editor.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "tools/audit_pc07_selected_event_remap_v1.py"
REFERENCE_PATH = ROOT / "references/pc07_selected_event_remap_v1.json"
INVENTORY_SHA256 = "97fb4b6eb1c0fb1e403303c6b692e933f2c01285ced19d037dc5d82c3d3dd15d"
REFERENCE_SHA256 = "aa9c83da8af9a6d249924bcdcdf4e39c346b397d4b5c3372768f3473fb832599"
OBJECT_COUNT = 14
INSERT_OBJECT = 8
INSERT_OFFSET = 0x713
DONOR_START = 0x2C2
DONOR_END = 0x361
NEW_BODY_SIZE = 160
NEW_BODY_START = INSERT_OFFSET + 32
NEW_BODY_END = NEW_BODY_START + NEW_BODY_SIZE
TRANSFORMED_SIZE = 2553
IDENTITY_OPERANDS = (0x2CC, 0x2D4, 0x2DC, 0x2FD, 0x303, 0x309, 0x314,
                     0x31E, 0x326, 0x32E, 0x33D, 0x345, 0x34D)
DIRECT_OPERANDS = ((0x86E, 20, 22), (0x870, 22, 24),
                   (0x874, 20, 22), (0x877, 22, 24))


class TransformError(RuntimeError):
    """The exact accepted source or transformation contract did not hold."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_dependencies():
    if digest(INVENTORY_PATH.read_bytes()) != INVENTORY_SHA256:
        raise TransformError("accepted inventory source drift")
    raw = REFERENCE_PATH.read_bytes()
    if digest(raw) != REFERENCE_SHA256:
        raise TransformError("accepted inventory reference drift")
    reference = json.loads(raw)
    # Validate every accepted source identity, including parser and source
    # disassembly, rather than trusting a boolean in the frozen report.
    for item in reference["source_manifest"]:
        source = (ROOT / item["path"]).read_bytes()
        if len(source) != item["size"] or digest(source) != item["sha256"]:
            raise TransformError(f"accepted source dependency drift: {item['path']}")
    spec = importlib.util.spec_from_file_location("epoch_transform_v1_inventory", INVENTORY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, reference


INVENTORY, REFERENCE = load_dependencies()
PARSER = INVENTORY.PARSER


@dataclass(frozen=True)
class TransformResult:
    # Copyrighted original game payload is returned only to the in-memory
    # caller. It must never be logged, tracked or serialized by this CLI.
    packet: bytes
    metadata: dict


def old_to_new(offset: int) -> int:
    return offset + 32 + (NEW_BODY_SIZE if offset >= INSERT_OFFSET else 0)


def donor_to_new(offset: int) -> int:
    return NEW_BODY_START + offset - DONOR_START + (offset > DONOR_START)


def pointer_rows(data: bytes, count: int) -> list[list[int]]:
    return [[int.from_bytes(data[obj * 32 + f * 2:obj * 32 + f * 2 + 2], "little")
             for f in range(16)] for obj in range(count)]


def validate_source(packet: bytes) -> None:
    if type(packet) is not bytes or len(packet) != 2361 or digest(packet) != INVENTORY.PACKET_SHA256:
        raise TransformError("requires exact canonical event0125 packet")
    if INVENTORY.inspect_packet(packet, NEW_BODY_SIZE) != REFERENCE["inventory"]:
        raise TransformError("selected inventory no longer reproduces")
    donors = INVENTORY.assess_selected_donors(packet)
    if donors != REFERENCE["complete_body_reuse_assessment"]:
        raise TransformError("selected donor assessment no longer reproduces")
    if tuple(row[1] for row in donors[0]["identity_comparisons"]) != IDENTITY_OPERANDS:
        raise TransformError("identity operand contract differs from accepted assessment")
    expected = tuple((row[1] + 1, row[5], row[6])
                     for row in REFERENCE["inventory"]["direct_references"] if row[5] != row[6])
    if expected != DIRECT_OPERANDS:
        raise TransformError("direct-object operand contract differs from accepted assessment")


def inverse_original_projection(candidate: bytes) -> bytes:
    """Project away only the declared insertion and exact old-object edits.

    This helper does not certify the new body's contents. validate_transformation
    checks that body and all pointers independently before using the projection.
    """
    if len(candidate) != TRANSFORMED_SIZE or candidate[0] != OBJECT_COUNT + 1:
        raise TransformError("transformed count or size mismatch")
    data = candidate[1:]
    restored_table = bytearray()
    for obj, row in enumerate(pointer_rows(data, OBJECT_COUNT + 1)):
        if obj == INSERT_OBJECT:
            continue
        for target in row:
            # Original pointers must not enter the newly inserted body.
            if NEW_BODY_START <= target < NEW_BODY_END:
                raise TransformError("original function pointer enters copied body")
            value = target - 32 - (NEW_BODY_SIZE if target >= NEW_BODY_END else 0)
            if not 0 <= value <= 0xFFFF:
                raise TransformError("inverse pointer underflow/overflow")
            restored_table.extend(value.to_bytes(2, "little"))
    restored = restored_table + data[(OBJECT_COUNT + 1) * 32:NEW_BODY_START] + data[NEW_BODY_END:]
    for offset, old, new in DIRECT_OPERANDS:
        if restored[offset] != new:
            raise TransformError("remapped direct operand does not match contract")
        restored[offset] = old
    return bytes([OBJECT_COUNT]) + bytes(restored)


def validate_transformation(original: bytes, candidate: bytes) -> dict:
    """Reconcile actual bytes; do not accept a caller-supplied witness/flag."""
    validate_source(original)
    if type(candidate) is not bytes or len(candidate) != TRANSFORMED_SIZE or candidate[0] != 15:
        raise TransformError("transformed count or size mismatch")
    old_data, data = original[1:], candidate[1:]
    try:
        old_commands = PARSER.parse_event(0x125, original)
        commands = PARSER.parse_event(0x125, candidate)
    except PARSER.AuditError as exc:
        raise TransformError(f"transformed parse failed: {exc}") from exc
    old_rows = pointer_rows(old_data, OBJECT_COUNT)
    rows = pointer_rows(data, OBJECT_COUNT + 1)
    by_offset = {command.offset: command for command in commands}
    for obj, row in enumerate(old_rows):
        mapped_obj = obj + (obj >= INSERT_OBJECT)
        if rows[mapped_obj] != [old_to_new(target) for target in row]:
            raise TransformError("original function-pointer occurrences/aliases changed")
    if rows[INSERT_OBJECT] != [donor_to_new(target) for target in old_rows[1]]:
        raise TransformError("copied function-pointer occurrences/aliases changed")
    # Verify the stronger selected topology, not just parser width acceptance.
    starts = [row[0] for row in rows]
    ends = starts[1:] + [len(data)]
    for obj, row in enumerate(rows):
        if any(target not in by_offset or not starts[obj] <= target < ends[obj] for target in row):
            raise TransformError("candidate function pointer lacks its own-object command boundary")
    body = data[NEW_BODY_START:NEW_BODY_END]
    if len(body) != NEW_BODY_SIZE or body[:2] != bytes([0x80, 7]):
        raise TransformError("copied body does not start with generic LoadPC07")
    # Full donor equality except the named thirteen literals and loader growth.
    for old_offset in range(DONOR_START + 1, DONOR_END):
        expected = 7 if old_offset in IDENTITY_OPERANDS else old_data[old_offset]
        if data[donor_to_new(old_offset)] != expected:
            raise TransformError(f"undeclared copied-body difference at donor offset {old_offset:04X}")
    copied_commands = [command for command in commands if command.object_id == INSERT_OBJECT]
    old_donor_commands = [command for command in old_commands if command.object_id == 1]
    if len(copied_commands) != 60 or len(commands) != 757:
        raise TransformError("unexpected copied or total command census")
    for old_command, command in zip(old_donor_commands, copied_commands):
        expected_opcode = 0x80 if old_command.offset == DONOR_START else old_command.opcode
        if command.offset != donor_to_new(old_command.offset) or command.opcode != expected_opcode:
            raise TransformError("copied command boundaries or loader domain changed")
    original_branch_count = copied_branch_count = 0
    for command in old_commands:
        if command.opcode not in INVENTORY.BRANCH_OPS:
            continue
        mapped = by_offset.get(old_to_new(command.offset))
        if (mapped is None or mapped.opcode != command.opcode or mapped.payload != command.payload or
                INVENTORY.branch_target(mapped) != old_to_new(INVENTORY.branch_target(command))):
            raise TransformError("original branch byte or target changed")
        original_branch_count += 1
        if command.object_id == 1:
            copied = by_offset.get(donor_to_new(command.offset))
            if (copied is None or copied.opcode != command.opcode or
                    copied.payload[-1] != command.payload[-1] or
                    INVENTORY.branch_target(copied) != donor_to_new(INVENTORY.branch_target(command))):
                raise TransformError("copied branch displacement or target changed")
            copied_branch_count += 1
    if (original_branch_count, copied_branch_count) != (186, 19):
        raise TransformError("branch census does not match accepted inventory")
    inverse = inverse_original_projection(candidate)
    if inverse != original:
        raise TransformError("inverse projection does not restore every original packet byte")
    # All doubled-index target operand changes have been reconciled by the
    # inverse; list their actual mapped sites as metadata, not payload.
    direct_changes = [{"old_operand_offset": offset, "new_operand_offset": old_to_new(offset),
                       "old_value": old, "new_value": new} for offset, old, new in DIRECT_OPERANDS]
    identity_changes = [{"donor_operand_offset": offset, "copied_operand_offset": donor_to_new(offset),
                         "old_identity": 0, "new_identity": 7} for offset in IDENTITY_OPERANDS]
    return {
        "schema": "pc07-selected-event-transform-v1",
        "evidence_level": "verified-static bounded in-memory event transformation",
        "event_id": 0x125,
        "source_packet_size": len(original), "source_packet_sha256": digest(original),
        "transformed_packet_size": len(candidate), "transformed_packet_sha256": digest(candidate),
        "original_object_count": 14, "transformed_object_count": 15,
        "source_donor_object": 1, "new_object": INSERT_OBJECT,
        "new_body_size": NEW_BODY_SIZE, "new_body_start": NEW_BODY_START,
        "new_body_end_exclusive": NEW_BODY_END,
        "new_body_sha256": digest(body),
        "loader_change": {"original_opcode": 0x57, "generic_opcode": 0x80,
                          "logical_pc_operand": 7, "growth_bytes": 1},
        "copied_identity_changes": identity_changes,
        "retained_copied_control_comparison": {
            "donor_offset": 0x2EF, "copied_offset": donor_to_new(0x2EF),
            "script_memory_slot": 6, "literal": 0, "comparator": 1},
        "original_direct_operand_changes": direct_changes,
        "original_function_pointer_occurrences": 224,
        "copied_function_pointer_occurrences": 16,
        "copied_function_targets": rows[INSERT_OBJECT],
        "candidate_role2_referenced_functions_present": [3, 4, 5, 6, 7],
        "original_branch_count": original_branch_count, "copied_branch_count": copied_branch_count,
        "original_command_count": len(old_commands), "copied_command_count": len(copied_commands),
        "transformed_command_count": len(commands),
        "inverse_projection_size": len(inverse), "inverse_projection_sha256": digest(inverse),
        "inverse_equality_scope": "Every original packet byte, including all seven original PC bodies, all original sixteen-function alias groups and all original branch displacements.",
        "builtin_region_boundary": 0x7F3700,
        "packet_end_exclusive_if_staged_at_7F2000": 0x7F2000 + len(candidate),
        "accepted_inventory_reference_sha256": REFERENCE_SHA256,
        "accepted_inventory_source_sha256": INVENTORY_SHA256,
        "implementation_reference": REFERENCE["community_implementation_reference"],
        "limits": [
            "Only exact canonical event0125 is accepted; no generic editing or free-space path exists.",
            "The complete copied body is borrowed private game data; only metadata is emitted by the CLI.",
            "The original logicalPC0 and originalPC2 objects remain independent and unchanged after inverse projection; live records are not touched by this transform.",
            "Generic LoadPC07, donor-qualified graphics, roster and runtime role publication require separate staging and observation.",
            "Existing scene functions are copied and decoded, not proved to execute or complete as PC07.",
            "No compressed packet, ROM image, patch, native run, production hook or allocation is produced or approved.",
        ],
    }


def transform_packet(original: bytes) -> TransformResult:
    """Return the exact new packet privately in memory plus reproducible metadata."""
    validate_source(original)
    old_data = original[1:]
    rows = pointer_rows(old_data, OBJECT_COUNT)
    donor = bytearray([0x80, 7]) + bytearray(old_data[DONOR_START + 1:DONOR_END])
    for offset in IDENTITY_OPERANDS:
        position = offset - DONOR_START + 1
        if donor[position] != 0:
            raise TransformError("copied identity preimage mismatch")
        donor[position] = 7
    changed = bytearray(old_data)
    for offset, old, new in DIRECT_OPERANDS:
        if changed[offset] != old:
            raise TransformError("direct operand preimage mismatch")
        changed[offset] = new
    table = bytearray()
    for obj in range(OBJECT_COUNT + 1):
        if obj == INSERT_OBJECT:
            targets = [donor_to_new(target) for target in rows[1]]
        else:
            old_obj = obj - (obj > INSERT_OBJECT)
            targets = [old_to_new(target) for target in rows[old_obj]]
        for target in targets:
            table.extend(target.to_bytes(2, "little"))
    data = table + changed[OBJECT_COUNT * 32:INSERT_OFFSET] + donor + changed[INSERT_OFFSET:]
    packet = bytes([OBJECT_COUNT + 1]) + bytes(data)
    metadata = validate_transformation(original, packet)
    return TransformResult(packet, metadata)


def transform_from_rom(rom: bytes) -> TransformResult:
    PARSER.validate_canonical_rom(rom)
    _, pointer = PARSER.event_pointer(rom, 0x125)
    packet = PARSER.decompress_packet(rom, pointer).data
    return transform_packet(packet)


def make_report(rom: bytes) -> dict:
    result = transform_from_rom(rom)
    report = dict(result.metadata)
    manifest = []
    for path in (Path(__file__), ROOT / "tests/test_pc07_selected_event_transform_v1.py"):
        source = path.read_bytes()
        manifest.append({"path": path.resolve().relative_to(ROOT).as_posix(),
                         "size": len(source), "sha256": digest(source)})
    report["source_manifest"] = manifest
    report["reproduction"] = [
        "python -B tools/transform_pc07_selected_event_v1.py --rom <canonical-private-US-Rev0-ROM>",
        "Set CT_US_REV0_ROM to the private canonical path, then run python -B -m unittest discover -s tests -p test_pc07_selected_event_transform_v1.py",
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
