#!/usr/bin/env python3
"""Audit Schala gameplay tiles against all seven vanilla PC graphics.

The audit hash-gates the canonical ROM, reads the seven raw playable-character
graphics windows only in memory, and compares them with the deterministically
packed Project Epoch gameplay foundation.  It never writes, renders, or embeds
canonical-ROM tile bytes or decoded pixels.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import build_schala_gameplay_foundation_v0 as gameplay


TOOL_VERSION = "1.0.0"
CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)
PC_GFX_POINTER_TABLE_FILE = 0x242000
BYTES_PER_4BPP_TILE = 0x20
TRIVIAL_VISIBLE_PIXEL_LIMIT = 2


@dataclasses.dataclass(frozen=True)
class ReferenceWindow:
    character: str
    logical_id: int
    snes_start: int
    file_start: int
    file_end_exclusive: int

    @property
    def byte_count(self) -> int:
        return self.file_end_exclusive - self.file_start


@dataclasses.dataclass(frozen=True)
class ReferenceTile:
    character: str
    logical_id: int
    tile_index: int
    file_offset: int
    pixels: tuple[int, ...]


# Physical packet boundaries are exact: each start is selected by the seven
# entries at $E4:2000.  Same-bank packets end at the next PC start; bank-ending
# packets end at the bank boundary.  Ayla ends at $D5:8C00, the earliest
# non-PC graphics pointer in the bounded $E4:2015-$E4:22E7 table.
PC_REFERENCE_WINDOWS = (
    ReferenceWindow("Crono", 0, 0xD272C0, 0x1272C0, 0x130000),
    ReferenceWindow("Marle", 1, 0xD40000, 0x140000, 0x147C40),
    ReferenceWindow("Lucca", 2, 0xD36B40, 0x136B40, 0x140000),
    ReferenceWindow("Robo", 3, 0xD47C40, 0x147C40, 0x150000),
    ReferenceWindow("Frog", 4, 0xD30000, 0x130000, 0x136B40),
    ReferenceWindow("Ayla", 5, 0xD50000, 0x150000, 0x158C00),
    ReferenceWindow("Magus", 6, 0xD20000, 0x120000, 0x1272C0),
)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_canonical_rom(
    rom_path: pathlib.Path,
) -> tuple[bytes, dict[str, Any]]:
    rom = rom_path.read_bytes()
    identity = {
        "size": len(rom),
        "sha1": sha1(rom),
        "sha256": sha256(rom),
    }
    if len(rom) != CANONICAL_ROM_SIZE:
        raise ValueError(
            "canonical ROM size mismatch: "
            f"expected 0x{CANONICAL_ROM_SIZE:X}, got 0x{len(rom):X}"
        )
    if identity["sha1"] != CANONICAL_ROM_SHA1:
        raise ValueError("canonical ROM SHA-1 mismatch")
    if identity["sha256"] != CANONICAL_ROM_SHA256:
        raise ValueError("canonical ROM SHA-256 mismatch")
    verify_pc_pointer_table(rom)
    return rom, identity


def _read_u24_le(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 3 > len(data):
        raise ValueError("24-bit pointer read exceeds input")
    return int.from_bytes(data[offset : offset + 3], "little")


def verify_pc_pointer_table(rom: bytes) -> None:
    expected = tuple(window.snes_start for window in PC_REFERENCE_WINDOWS)
    actual = tuple(
        _read_u24_le(rom, PC_GFX_POINTER_TABLE_FILE + logical_id * 3)
        for logical_id in range(len(expected))
    )
    if actual != expected:
        raise ValueError("playable-character graphics pointer table mismatch")


def validate_reference_windows() -> None:
    for window in PC_REFERENCE_WINDOWS:
        if window.byte_count <= 0:
            raise ValueError(f"{window.character}: empty reference window")
        if window.byte_count % BYTES_PER_4BPP_TILE:
            raise ValueError(
                f"{window.character}: reference window is not tile-aligned"
            )
        if window.file_start != (window.snes_start & 0x3FFFFF):
            raise ValueError(
                f"{window.character}: SNES/file address mapping mismatch"
            )

    ordered = sorted(
        PC_REFERENCE_WINDOWS, key=lambda window: window.file_start
    )
    for previous, current in zip(ordered, ordered[1:]):
        if previous.file_end_exclusive > current.file_start:
            raise ValueError(
                f"{previous.character}/{current.character} windows overlap"
            )


def decode_4bpp_tile_block(block: bytes) -> tuple[tuple[int, ...], ...]:
    if len(block) % BYTES_PER_4BPP_TILE:
        raise ValueError("reference block is not aligned to 0x20-byte tiles")
    return tuple(
        gameplay.decode_snes_4bpp(
            block[offset : offset + BYTES_PER_4BPP_TILE], 8, 8
        )
        for offset in range(0, len(block), BYTES_PER_4BPP_TILE)
    )


def decode_reference_tiles(rom: bytes) -> tuple[ReferenceTile, ...]:
    validate_reference_windows()
    tiles: list[ReferenceTile] = []
    for window in PC_REFERENCE_WINDOWS:
        if window.file_end_exclusive > len(rom):
            raise ValueError(
                f"{window.character}: reference window exceeds ROM"
            )
        block = rom[window.file_start : window.file_end_exclusive]
        for tile_index, pixels in enumerate(decode_4bpp_tile_block(block)):
            tiles.append(
                ReferenceTile(
                    character=window.character,
                    logical_id=window.logical_id,
                    tile_index=tile_index,
                    file_offset=(
                        window.file_start + tile_index * BYTES_PER_4BPP_TILE
                    ),
                    pixels=pixels,
                )
            )
    return tuple(tiles)


def packed_candidate_frames(
    source_raw: bytes, source: dict[str, Any]
) -> tuple[
    dict[str, tuple[int, int, tuple[int, ...]]],
    dict[str, dict[str, Any]],
]:
    frames = gameplay.validate_source(source)
    outputs = gameplay.build_outputs(source_raw, source)
    candidates: dict[str, tuple[int, int, tuple[int, ...]]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for frame_id in sorted(frames):
        width, height, _ = gameplay.frame_pixels(frames[frame_id])
        filename = f"{frame_id}.4bpp"
        packed = outputs[filename]
        candidates[frame_id] = (
            width,
            height,
            gameplay.decode_snes_4bpp(packed, width, height),
        )
        metadata[frame_id] = {
            "filename": filename,
            "size": len(packed),
            "sha256": sha256(packed),
            "tile_count": len(packed) // BYTES_PER_4BPP_TILE,
        }
    return candidates, metadata


def visible_pattern(tile: Sequence[int]) -> tuple[int, ...]:
    """Rename visible palette indices by first use while preserving zero."""

    if len(tile) != 64:
        raise ValueError("tile must contain 64 pixels")
    labels: dict[int, int] = {}
    next_label = 1
    result: list[int] = []
    for pixel in tile:
        if pixel == 0:
            result.append(0)
            continue
        if pixel not in labels:
            labels[pixel] = next_label
            next_label += 1
        result.append(labels[pixel])
    return tuple(result)


def _visible_count(tile: Sequence[int]) -> int:
    return sum(pixel != 0 for pixel in tile)


def _reference_metadata(tile: ReferenceTile) -> dict[str, Any]:
    return {
        "reference_character": tile.character,
        "reference_logical_id": tile.logical_id,
        "reference_tile_index": tile.tile_index,
        "reference_file_offset": f"0x{tile.file_offset:06X}",
    }


def audit_tiles(
    candidate_frames: dict[str, tuple[int, int, Sequence[int]]],
    reference_tiles: Sequence[ReferenceTile],
) -> dict[str, Any]:
    exact_index: dict[tuple[int, ...], set[int]] = defaultdict(set)
    pattern_index: dict[tuple[int, ...], set[int]] = defaultdict(set)
    excluded_reference = 0

    for reference_index, reference in enumerate(reference_tiles):
        if _visible_count(reference.pixels) <= TRIVIAL_VISIBLE_PIXEL_LIMIT:
            excluded_reference += 1
            continue
        for variant in gameplay.tile_variants(reference.pixels):
            exact_index[variant].add(reference_index)
            pattern_index[visible_pattern(variant)].add(reference_index)

    candidate_tile_count = 0
    excluded_candidates = []
    exact_matches = []
    pattern_matches = []
    for frame_id in sorted(candidate_frames):
        width, height, pixels = candidate_frames[frame_id]
        for candidate_index, candidate in enumerate(
            gameplay.iter_tiles(pixels, width, height)
        ):
            candidate_tile_count += 1
            visible = _visible_count(candidate)
            if visible <= TRIVIAL_VISIBLE_PIXEL_LIMIT:
                excluded_candidates.append(
                    {
                        "frame_id": frame_id,
                        "candidate_tile_index": candidate_index,
                        "visible_pixel_count": visible,
                    }
                )
                continue

            exact_references = exact_index.get(candidate, set())
            for reference_index in sorted(exact_references):
                exact_matches.append(
                    {
                        "frame_id": frame_id,
                        "candidate_tile_index": candidate_index,
                        "visible_pixel_count": visible,
                        **_reference_metadata(reference_tiles[reference_index]),
                    }
                )

            for reference_index in sorted(
                pattern_index.get(visible_pattern(candidate), set())
            ):
                pattern_matches.append(
                    {
                        "frame_id": frame_id,
                        "candidate_tile_index": candidate_index,
                        "visible_pixel_count": visible,
                        "also_exact_index_match": (
                            reference_index in exact_references
                        ),
                        **_reference_metadata(reference_tiles[reference_index]),
                    }
                )

    return {
        "candidate_tile_count": candidate_tile_count,
        "reference_tile_count": len(reference_tiles),
        "trivial_visible_pixel_limit": TRIVIAL_VISIBLE_PIXEL_LIMIT,
        "excluded_candidate_tiles": excluded_candidates,
        "excluded_reference_tile_count": excluded_reference,
        "exact_index_matches": exact_matches,
        "visible_pattern_matches": pattern_matches,
        "visible_pattern_only_match_count": sum(
            not match["also_exact_index_match"] for match in pattern_matches
        ),
    }


def build_report(
    rom_path: pathlib.Path, source_path: pathlib.Path
) -> dict[str, Any]:
    rom, rom_identity = verify_canonical_rom(rom_path)
    source_raw, source = gameplay.load_json(source_path)
    candidate_frames, packed_metadata = packed_candidate_frames(
        source_raw, source
    )
    reference_tiles = decode_reference_tiles(rom)
    audit = audit_tiles(candidate_frames, reference_tiles)
    windows = []
    for window in PC_REFERENCE_WINDOWS:
        block = rom[window.file_start : window.file_end_exclusive]
        windows.append(
            {
                "character": window.character,
                "logical_id": window.logical_id,
                "snes_start": f"0x{window.snes_start:06X}",
                "file_start": f"0x{window.file_start:06X}",
                "file_end_exclusive": (
                    f"0x{window.file_end_exclusive:06X}"
                ),
                "byte_count": len(block),
                "tile_count": len(block) // BYTES_PER_4BPP_TILE,
                "sha256": sha256(block),
            }
        )
    return {
        "schema_version": 1,
        "tool": {
            "path": "tools/audit_schala_gameplay_originality.py",
            "version": TOOL_VERSION,
        },
        "evidence": "verified-static",
        "reproduction": (
            "python tools/audit_schala_gameplay_originality.py "
            '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
        ),
        "canonical_rom": rom_identity,
        "canonical_source": {
            "path": (
                "assets/source/schala/v0/gameplay/"
                "schala_gameplay_foundation_v0.json"
            ),
            "sha256": sha256(source_raw),
        },
        "packed_candidates": packed_metadata,
        "reference_scope": {
            "description": (
                "all seven raw playable-character graphics windows selected "
                "by the canonical $E4:2000 pointer table"
            ),
            "windows": windows,
            "tile_count": len(reference_tiles),
            "coverage_limit": (
                "This audit covers the canonical playable-character raw "
                "graphics windows. It does not cover NPC/enemy packets, "
                "portraits, assembly data, animation data, or VFX."
            ),
        },
        "comparison_policy": {
            "transforms": ["identity", "horizontal", "vertical", "combined"],
            "exact_index_comparison": True,
            "visible_pattern_comparison": (
                "Non-zero palette labels are canonicalized; transparent "
                "index zero remains fixed."
            ),
            "trivial_exclusion": (
                "Candidate and reference tiles with at most two non-zero "
                "pixels are reported as excluded, not matches."
            ),
            "interpretation": (
                "A match is a review lead, not proof of copying. Absence of "
                "matches is bounded evidence, not proof against near matches."
            ),
        },
        "audit": audit,
        "copyright_boundary": (
            "No canonical-ROM tile bytes, decoded pixels, palettes, or images "
            "are included in this report or written by the tool."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="Explicit path to the pinned clean headerless US ROM.",
    )
    parser.add_argument(
        "--source", type=pathlib.Path, default=gameplay.DEFAULT_SOURCE
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build_report(args.rom, args.source), indent=2, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
