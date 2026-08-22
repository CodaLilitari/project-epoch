#!/usr/bin/env python3
"""Inject a deterministic canary into the unused-candidate SRAM gap in a BSV.

RetroArch BSV1 movies embed an initial emulator state. For the pinned
bsnes2014 core, that state contains one literal copy of the 0x2000-byte SRAM
image. This tool replaces only SRAM file offsets 0x1E00-0x1FDF, leaving the
three vanilla 0x0A00-byte save slots and global metadata untouched.

The gap is still a candidate, not approved production storage. The canary is
for a disposable runtime ownership test.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct


BSV_MAGIC = b"BSV1"
BSV_HEADER_SIZE = 16
EXPECTED_SRAM_SIZE = 0x2000
# Pinned bsnes2014 BST1 serializer layout used by the Project Epoch harness.
PINNED_STATE_LENGTH = 329133
PINNED_SRAM_STATE_OFFSET = 0x0258
GAP_OFFSET = 0x1E00
GAP_LENGTH = 0x01E0
METADATA_OFFSET = 0x1FE0
CANARY_SEED = b"Project Epoch Schala SRAM gap canary v1"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_canary() -> bytes:
    return hashlib.shake_256(CANARY_SEED).digest(GAP_LENGTH)


def locate_embedded_state(movie: bytes) -> tuple[int, int]:
    if len(movie) < BSV_HEADER_SIZE or movie[:4] != BSV_MAGIC:
        raise RuntimeError("not a supported BSV1 movie")
    state_size = struct.unpack_from("<I", movie, 12)[0]
    state_start = BSV_HEADER_SIZE
    state_end = state_start + state_size
    if state_end > len(movie):
        raise RuntimeError("embedded savestate extends beyond the movie")
    return state_start, state_end


def inject_canary(movie: bytes, sram: bytes) -> tuple[bytes, int]:
    if len(sram) != EXPECTED_SRAM_SIZE:
        raise RuntimeError(
            f"expected a 0x{EXPECTED_SRAM_SIZE:X}-byte SRAM image"
        )
    if GAP_OFFSET + GAP_LENGTH != METADATA_OFFSET:
        raise AssertionError("gap constants are not contiguous with metadata")

    state_start, state_end = locate_embedded_state(movie)
    state = movie[state_start:state_end]
    first = state.find(sram)
    if first < 0:
        raise RuntimeError("SRAM image not found in embedded savestate")
    if state.find(sram, first + 1) >= 0:
        raise RuntimeError("SRAM image occurs more than once in savestate")

    absolute_gap_start = state_start + first + GAP_OFFSET
    absolute_gap_end = absolute_gap_start + GAP_LENGTH
    patched = bytearray(movie)
    patched[absolute_gap_start:absolute_gap_end] = make_canary()

    differences = [
        index
        for index, (before, after) in enumerate(
            zip(movie, patched, strict=True)
        )
        if before != after
    ]
    expected = set(range(absolute_gap_start, absolute_gap_end))
    if not differences or any(index not in expected for index in differences):
        raise AssertionError("canary edit escaped the candidate SRAM gap")

    return bytes(patched), first


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    parser.add_argument("--srm", required=True, type=pathlib.Path)
    parser.add_argument("-o", "--out", required=True, type=pathlib.Path)
    args = parser.parse_args()

    movie = args.movie.read_bytes()
    sram = args.srm.read_bytes()
    patched, state_sram_offset = inject_canary(movie, sram)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(patched)

    print(f"input_movie_sha256={sha256(movie)}")
    print(f"input_sram_sha256={sha256(sram)}")
    print(f"state_sram_offset=0x{state_sram_offset:X}")
    print(f"gap_offset=0x{GAP_OFFSET:X}")
    print(f"gap_length=0x{GAP_LENGTH:X}")
    print(f"canary_sha256={sha256(make_canary())}")
    print(f"output_movie_sha256={sha256(patched)}")
    print(f"wrote={args.out}")


if __name__ == "__main__":
    main()
