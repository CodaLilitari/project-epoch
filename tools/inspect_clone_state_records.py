#!/usr/bin/env python3
"""Compare Lucca and Magus records in paired bsnes2014 savestates."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


RECORD_LENGTH = 0x50
SAVE_SLOT_LENGTH = 0x0A00
LUCCA_SAVE_OFFSET = 0x02A0
MAGUS_SAVE_OFFSET = 0x03E0
WRAM_RECORD_DELTA = MAGUS_SAVE_OFFSET - LUCCA_SAVE_OFFSET


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_all(data: bytes, pattern: bytes) -> list[int]:
    hits: list[int] = []
    start = 0
    while True:
        index = data.find(pattern, start)
        if index < 0:
            return hits
        hits.append(index)
        start = index + 1


def inspect_states(
    save: bytes,
    static_state: bytes,
    runtime_state: bytes,
    *,
    save_slot: int = 1,
) -> dict[str, object]:
    if save_slot not in (1, 2, 3):
        raise RuntimeError("save slot must be 1, 2, or 3")
    slot_base = (save_slot - 1) * SAVE_SLOT_LENGTH
    lucca_offset = slot_base + LUCCA_SAVE_OFFSET
    magus_offset = slot_base + MAGUS_SAVE_OFFSET
    if len(save) < magus_offset + RECORD_LENGTH:
        raise RuntimeError("save is too short for the Lucca and Magus records")
    if len(static_state) != len(runtime_state):
        raise RuntimeError("savestate sizes differ")

    lucca = save[lucca_offset : lucca_offset + RECORD_LENGTH]
    magus = save[magus_offset : magus_offset + RECORD_LENGTH]
    if lucca == magus:
        raise RuntimeError("save records are identical; clone test is inconclusive")

    static_lucca_hits = find_all(static_state, lucca)
    static_magus_hits = find_all(static_state, magus)
    paired_destinations = [
        offset
        for offset in static_lucca_hits
        if offset + WRAM_RECORD_DELTA in static_magus_hits
    ]
    if not paired_destinations:
        raise RuntimeError("could not locate a Lucca/Magus record pair")

    # bsnes2014 serializes more than one save/WRAM copy. In the pinned core's
    # BST1 layout, the live WRAM pair is the last matching pair.
    live_lucca_offset = max(paired_destinations)
    live_magus_offset = live_lucca_offset + WRAM_RECORD_DELTA
    runtime_lucca = runtime_state[
        live_lucca_offset : live_lucca_offset + RECORD_LENGTH
    ]

    if runtime_lucca == magus:
        status = "cloned"
    elif runtime_lucca == lucca:
        status = "unchanged"
    else:
        status = "mixed-or-unmapped"

    return {
        "save_slot": save_slot,
        "record_length": RECORD_LENGTH,
        "record_difference_bytes": sum(
            left != right for left, right in zip(lucca, magus)
        ),
        "wram_record_delta": WRAM_RECORD_DELTA,
        "static_lucca_hits": static_lucca_hits,
        "static_magus_hits": static_magus_hits,
        "paired_destinations": paired_destinations,
        "live_lucca_state_offset": live_lucca_offset,
        "live_magus_state_offset": live_magus_offset,
        "runtime_lucca_record_status": status,
        "static_state_sha256": sha256(static_state),
        "runtime_state_sha256": sha256(runtime_state),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("save", type=pathlib.Path)
    parser.add_argument("static_state", type=pathlib.Path)
    parser.add_argument("runtime_state", type=pathlib.Path)
    parser.add_argument(
        "--slot",
        type=int,
        choices=(1, 2, 3),
        default=1,
        help="one-based SRAM save slot whose records should be located",
    )
    args = parser.parse_args()
    result = inspect_states(
        args.save.read_bytes(),
        args.static_state.read_bytes(),
        args.runtime_state.read_bytes(),
        save_slot=args.slot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
