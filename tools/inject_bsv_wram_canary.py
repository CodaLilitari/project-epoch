#!/usr/bin/env python3
"""Inject a canary into the proposed relocated-compatibility WRAM block.

RetroArch BSV1 movies embed an initial emulator state. For the pinned
bsnes2014 core, the live Chrono Trigger WRAM image can be anchored by the
loaded Lucca and Magus character records. This tool derives the WRAM base from
that pair and replaces only $7E2CA0-$7E2CEF in a disposable movie state.

The range is still a candidate, not approved production storage. Refuse to
touch it unless every byte is zero in the source state.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct


BSV_MAGIC = b"BSV1"
BSV_HEADER_SIZE = 16
SAVE_SLOT_LENGTH = 0x0A00
RECORD_LENGTH = 0x50
LUCCA_SAVE_OFFSET = 0x02A0
MAGUS_SAVE_OFFSET = 0x03E0
LUCCA_WRAM_OFFSET = 0x26A0
MAGUS_WRAM_OFFSET = 0x27E0
WRAM_RECORD_DELTA = MAGUS_WRAM_OFFSET - LUCCA_WRAM_OFFSET
TARGET_WRAM_OFFSET = 0x2CA0
TARGET_LENGTH = 0x50
CANARY_SEED = b"Project Epoch WRAM 2CA0 compatibility canary v1"
PINNED_STATE_LENGTH = 329133
PINNED_WRAM_STATE_OFFSET = 0x4AA3


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_canary() -> bytes:
    return hashlib.shake_256(CANARY_SEED).digest(TARGET_LENGTH)


def find_all(data: bytes, pattern: bytes) -> list[int]:
    hits: list[int] = []
    start = 0
    while True:
        index = data.find(pattern, start)
        if index < 0:
            return hits
        hits.append(index)
        start = index + 1


def locate_embedded_state(movie: bytes) -> tuple[int, int]:
    if len(movie) < BSV_HEADER_SIZE or movie[:4] != BSV_MAGIC:
        raise RuntimeError("not a supported BSV1 movie")
    state_size = struct.unpack_from("<I", movie, 12)[0]
    state_start = BSV_HEADER_SIZE
    state_end = state_start + state_size
    if state_end > len(movie):
        raise RuntimeError("embedded savestate extends beyond the movie")
    return state_start, state_end


def replace_embedded_state(movie: bytes, state: bytes) -> bytes:
    state_start, state_end = locate_embedded_state(movie)
    if len(state) != state_end - state_start:
        raise RuntimeError("replacement state size does not match BSV state size")
    replaced = bytearray(movie)
    replaced[state_start:state_end] = state
    return bytes(replaced)


def locate_live_wram_base(
    state: bytes,
    sram: bytes,
    *,
    save_slot: int = 1,
) -> int:
    if save_slot not in (1, 2, 3):
        raise RuntimeError("save slot must be 1, 2, or 3")
    slot_base = (save_slot - 1) * SAVE_SLOT_LENGTH
    lucca = sram[
        slot_base + LUCCA_SAVE_OFFSET :
        slot_base + LUCCA_SAVE_OFFSET + RECORD_LENGTH
    ]
    magus = sram[
        slot_base + MAGUS_SAVE_OFFSET :
        slot_base + MAGUS_SAVE_OFFSET + RECORD_LENGTH
    ]
    if len(lucca) != RECORD_LENGTH or len(magus) != RECORD_LENGTH:
        raise RuntimeError("SRAM is too short for the selected slot")
    if lucca == magus:
        raise RuntimeError("source records are identical; WRAM anchor is ambiguous")

    magus_hits = set(find_all(state, magus))
    paired = [
        offset
        for offset in find_all(state, lucca)
        if (
            offset >= LUCCA_WRAM_OFFSET
            and offset + WRAM_RECORD_DELTA in magus_hits
        )
    ]

    if paired:
        # The pinned core serializes more than one save/WRAM copy. Its live
        # WRAM pair is the last matching pair, as independently checked by the
        # state record inspector.
        live_lucca = max(paired)
        wram_base = live_lucca - LUCCA_WRAM_OFFSET
        if state[
            wram_base + MAGUS_WRAM_OFFSET :
            wram_base + MAGUS_WRAM_OFFSET + RECORD_LENGTH
        ] != magus:
            raise AssertionError("derived WRAM base failed the Magus anchor")
        if (
            len(state) == PINNED_STATE_LENGTH
            and wram_base != PINNED_WRAM_STATE_OFFSET
        ):
            raise RuntimeError("record anchor disagrees with pinned state layout")
    elif len(state) == PINNED_STATE_LENGTH:
        # A cold/title-screen movie has no loaded live character records.
        # The exact pinned core/state length has a separately verified fixed
        # 128 KiB WRAM block beginning here.
        wram_base = PINNED_WRAM_STATE_OFFSET
    else:
        raise RuntimeError("could not locate a Lucca/Magus WRAM anchor pair")
    return wram_base


def inject_canary(
    movie: bytes,
    sram: bytes,
    *,
    save_slot: int = 1,
    allow_existing: bool = False,
) -> tuple[bytes, int, int]:
    state_start, state_end = locate_embedded_state(movie)
    state = movie[state_start:state_end]
    wram_base = locate_live_wram_base(state, sram, save_slot=save_slot)
    target_state_offset = wram_base + TARGET_WRAM_OFFSET
    target_end = target_state_offset + TARGET_LENGTH
    if target_end > len(state):
        raise RuntimeError("candidate WRAM block extends beyond embedded state")
    target_before = state[target_state_offset:target_end]
    if target_before == make_canary() and allow_existing:
        return movie, wram_base, target_state_offset
    if any(target_before):
        raise RuntimeError("candidate WRAM block is not all zero in source state")

    absolute_start = state_start + target_state_offset
    absolute_end = absolute_start + TARGET_LENGTH
    patched = bytearray(movie)
    patched[absolute_start:absolute_end] = make_canary()

    differences = [
        index
        for index, (before, after) in enumerate(
            zip(movie, patched, strict=True)
        )
        if before != after
    ]
    expected = set(range(absolute_start, absolute_end))
    if not differences or any(index not in expected for index in differences):
        raise AssertionError("canary edit escaped the candidate WRAM block")
    return bytes(patched), wram_base, target_state_offset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    parser.add_argument("--srm", required=True, type=pathlib.Path)
    parser.add_argument("--slot", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument(
        "--initial-state",
        type=pathlib.Path,
        help="replace the template BSV's equal-sized embedded initial state",
    )
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="accept an initial state that already contains the exact canary",
    )
    parser.add_argument("-o", "--out", required=True, type=pathlib.Path)
    args = parser.parse_args()

    movie = args.movie.read_bytes()
    if args.initial_state is not None:
        movie = replace_embedded_state(movie, args.initial_state.read_bytes())
    sram = args.srm.read_bytes()
    patched, wram_base, target_state_offset = inject_canary(
        movie,
        sram,
        save_slot=args.slot,
        allow_existing=args.allow_existing,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(patched)

    print(f"input_movie_sha256={sha256(movie)}")
    print(f"input_sram_sha256={sha256(sram)}")
    print(f"save_slot={args.slot}")
    print(f"state_wram_base=0x{wram_base:X}")
    print(f"target_wram=7E:{TARGET_WRAM_OFFSET:04X}")
    print(f"target_state_offset=0x{target_state_offset:X}")
    print(f"target_length=0x{TARGET_LENGTH:X}")
    print(f"canary_sha256={sha256(make_canary())}")
    print(f"output_movie_sha256={sha256(patched)}")
    print(f"wrote={args.out}")


if __name__ == "__main__":
    main()
