#!/usr/bin/env python3
"""Inspect vanilla Chrono Trigger US SNES SRAM files without modifying them.

The game stores three 0x0A00-byte slots in an 0x2000-byte SRAM image.  Slot
checksums and magic words live in the final metadata area, outside the slots.
This tool validates those fields and reports a small set of routing anchors
useful for isolated emulator tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


SRAM_SIZE = 0x2000
SLOT_SIZE = 0x0A00
SLOT_COUNT = 3
CHECKSUM_TABLE_OFFSET = 0x1FF0
MAGIC_TABLE_OFFSET = 0x1FF8
SLOT_MAGIC = 0xE41B

ACTIVE_PARTY_OFFSET = 0x0580
ROSTER_LENGTH = 9
SAVE_COUNTER_OFFSET = 0x059C
LOCATION_BLOCK_OFFSET = 0x05F3
EVENT_FLAGS_OFFSET = 0x0603
EPOCH_NAME_OFFSET = 0x05DA
NAME_LENGTH = 6
PC_RECORD_OFFSET = 0x0200
PC_RECORD_SIZE = 0x50
PC_COUNT = 7
PC_LEVEL_OFFSET = 0x12


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def slot_checksum(slot: bytes) -> int:
    """Reproduce SaveSlot_Checksum at $FF:FBE7.

    The 65816 routine visits little-endian words from $09FE down to $0000 and
    carries ADC's carry flag into the following iteration.
    """

    if len(slot) != SLOT_SIZE:
        raise ValueError(f"slot must be exactly 0x{SLOT_SIZE:X} bytes")
    accumulator = 0
    carry = 0
    for offset in range(SLOT_SIZE - 2, -1, -2):
        total = accumulator + read_u16(slot, offset) + carry
        accumulator = total & 0xFFFF
        carry = int(total > 0xFFFF)
    return accumulator


def inspect_slot(sram: bytes, slot_number: int) -> dict[str, object]:
    if slot_number not in range(1, SLOT_COUNT + 1):
        raise ValueError("slot number must be 1, 2, or 3")
    base = (slot_number - 1) * SLOT_SIZE
    slot = sram[base : base + SLOT_SIZE]
    metadata_index = (slot_number - 1) * 2
    stored_checksum = read_u16(
        sram, CHECKSUM_TABLE_OFFSET + metadata_index
    )
    computed_checksum = slot_checksum(slot)
    magic = read_u16(sram, MAGIC_TABLE_OFFSET + metadata_index)
    roster = slot[
        ACTIVE_PARTY_OFFSET : ACTIVE_PARTY_OFFSET + ROSTER_LENGTH
    ]
    levels = [
        slot[
            PC_RECORD_OFFSET
            + pc_id * PC_RECORD_SIZE
            + PC_LEVEL_OFFSET
        ]
        for pc_id in range(PC_COUNT)
    ]
    return {
        "slot": slot_number,
        "slot_offset": base,
        "slot_sha256": sha256(slot),
        "stored_checksum": stored_checksum,
        "computed_checksum": computed_checksum,
        "checksum_matches": stored_checksum == computed_checksum,
        "magic": magic,
        "magic_matches": magic == SLOT_MAGIC,
        "valid": magic == SLOT_MAGIC and stored_checksum == computed_checksum,
        "location_id": read_u16(slot, LOCATION_BLOCK_OFFSET),
        "storyline": slot[EVENT_FLAGS_OFFSET],
        "save_counter": read_u16(slot, SAVE_COUNTER_OFFSET),
        "active_party_hex": roster[:3].hex(),
        "roster_hex": roster.hex(),
        "pc_levels": levels,
        "epoch_name_hex": slot[
            EPOCH_NAME_OFFSET : EPOCH_NAME_OFFSET + NAME_LENGTH
        ].hex(),
    }


def inspect_sram(source: bytes) -> dict[str, object]:
    if len(source) != SRAM_SIZE:
        raise ValueError(
            f"SRAM image must be exactly 0x{SRAM_SIZE:X} bytes, "
            f"got 0x{len(source):X}"
        )
    return {
        "length": len(source),
        "sha256": sha256(source),
        "last_slot_saved": source[0x1FE0],
        "metadata_hex": source[0x1FE0:0x2000].hex(),
        "slots": [
            inspect_slot(source, slot_number)
            for slot_number in range(1, SLOT_COUNT + 1)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srams", nargs="+", type=pathlib.Path)
    parser.add_argument(
        "--require-valid-slot",
        action="store_true",
        help="fail when an image has no checksum-valid save slot",
    )
    args = parser.parse_args()

    failed = False
    for path in args.srams:
        result = inspect_sram(path.read_bytes())
        result["path"] = str(path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.require_valid_slot and not any(
            slot["valid"] for slot in result["slots"]
        ):
            failed = True
    if failed:
        raise SystemExit("one or more SRAM images have no valid slot")


if __name__ == "__main__":
    main()
