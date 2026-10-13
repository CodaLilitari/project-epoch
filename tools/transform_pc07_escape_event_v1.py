"""Pure, pinned one-byte escape-enabled derivative of accepted event0126.

No ROM, SRAM, patch or extracted packet is emitted. This is an authored
diagnostic event, not evidence that the retail Lavos encounter allows escape.
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
PARENT = ROOT / "tools/transform_pc07_lavos_event_v1.py"
PARENT_SHA256 = "19e28389fee2a471c6e1f7304cdbfbf06e08cf52dcb9a0994fa4400d4722e8d6"
SOURCE_SHA256 = "6999eb3bb0cc4f9b3db8d6d405a8aa4ebe94a0b590b5c8f01c531a31c3bd3bc5"
TARGET_SHA256 = "13879385d478acbdab1c92c1289414fcfb4761e50b4d913928a34964686341c4"
PACKET_SIZE = 1914
FLAG_OFFSET = 0x547


class TransformError(ValueError):
    pass


@dataclass(frozen=True)
class Result:
    packet: bytes
    metadata: dict


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parent():
    if sha(PARENT.read_bytes()) != PARENT_SHA256:
        raise TransformError("accepted event transformer source drift")
    spec = importlib.util.spec_from_file_location("epoch_escape_parent_v1", PARENT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def derive(accepted_packet: bytes) -> Result:
    if (type(accepted_packet) is not bytes or len(accepted_packet) != PACKET_SIZE
            or sha(accepted_packet) != SOURCE_SHA256):
        raise TransformError("requires exact accepted event0126 packet")
    parser = parent().PARSER
    before = parser.parse_event(0x126, accepted_packet)
    battles = [c for c in before if c.opcode == 0xD8]
    if (len(before) != 555 or len(battles) != 1
            or (battles[0].object_id, battles[0].offset, list(battles[0].payload))
            != (9, 0x545, [0x93, 0xE0])):
        raise TransformError("unique battle command identity changed")
    target = bytearray(accepted_packet)
    target[FLAG_OFFSET] = 0x13
    result = bytes(target)
    differences = [i for i, (a, b) in enumerate(zip(accepted_packet, result)) if a != b]
    if differences != [FLAG_OFFSET] or sha(result) != TARGET_SHA256:
        raise TransformError("complete packet diff mismatch")
    after = parser.parse_event(0x126, result)
    if len(after) != len(before):
        raise TransformError("command count changed")
    for old, new in zip(before, after):
        if (old.object_id, old.offset, old.opcode) != (new.object_id, new.offset, new.opcode):
            raise TransformError("command boundaries changed")
        expected = [0x13, 0xE0] if old.opcode == 0xD8 else list(old.payload)
        if list(new.payload) != expected:
            raise TransformError("undeclared command operand change")
    target[FLAG_OFFSET] = 0x93
    if bytes(target) != accepted_packet:
        raise TransformError("inverse does not restore accepted packet")
    return Result(result, {
        "schema": "project-epoch-pc07-escape-event-v1",
        "evidence_level": "verified-static-authored-event-derivative",
        "event_id": 0x126, "packet_size": PACKET_SIZE,
        "source_sha256": SOURCE_SHA256, "target_sha256": TARGET_SHA256,
        "parent_source_sha256": PARENT_SHA256,
        "command_count": len(before), "changed_packet_offsets": differences,
        "battle_object": 9, "battle_command_data_offset": 0x545,
        "first_flags_before": 0x93, "first_flags_after": 0x13,
        "second_flags_unchanged": 0xE0,
        "inverse_exact": True, "all_other_bytes_unchanged": True,
        "native_execution": False, "retail_encounter_escape_claim": False,
        "production_approval": False,
        "reproduction": "python -B tools/transform_pc07_escape_event_v1.py",
    })


def transform_from_rom(rom: bytes) -> Result:
    return derive(parent().transform_from_rom(rom).packet)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rom", type=Path, default=ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc")
    args = ap.parse_args()
    print(json.dumps(transform_from_rom(args.rom.read_bytes()).metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
