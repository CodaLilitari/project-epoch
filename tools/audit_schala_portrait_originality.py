#!/usr/bin/env python3
"""Audit Schala portrait tiles against a bounded canonical-ROM reference.

The audit reads the pinned clean ROM only in memory, verifies its complete
hashes, decodes only the known uncompressed menu-portrait tile range, and
compares the packed Project Epoch portrait assets without writing reference
tiles or pixels to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import build_schala_portraits_v0 as portraits


TOOL_VERSION = "1.0.0"
CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)

# Seven 48x48 portraits, 36 8x8 tiles each, stored as raw SNES 4bpp.
MENU_PORTRAIT_FILE_START = 0x3F0000
MENU_PORTRAIT_FILE_END_EXCLUSIVE = 0x3F1F80
BYTES_PER_4BPP_TILE = 0x20
TRIVIAL_VISIBLE_PIXEL_LIMIT = 2


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def verify_canonical_rom(rom_path: pathlib.Path) -> tuple[bytes, dict[str, Any]]:
    """Read and hash-gate the canonical headerless US ROM."""

    rom = rom_path.read_bytes()
    actual = {
        "size": len(rom),
        "sha1": _sha1(rom),
        "sha256": portraits.sha256(rom),
    }
    if actual["size"] != CANONICAL_ROM_SIZE:
        raise ValueError(
            "canonical ROM size mismatch: "
            f"expected 0x{CANONICAL_ROM_SIZE:X}, got 0x{len(rom):X}"
        )
    if actual["sha1"] != CANONICAL_ROM_SHA1:
        raise ValueError("canonical ROM SHA-1 mismatch")
    if actual["sha256"] != CANONICAL_ROM_SHA256:
        raise ValueError("canonical ROM SHA-256 mismatch")
    return rom, actual


def decode_4bpp_tile_block(block: bytes) -> tuple[tuple[int, ...], ...]:
    """Decode a raw, tile-aligned SNES 4bpp block without persisting it."""

    if len(block) % BYTES_PER_4BPP_TILE:
        raise ValueError("reference block is not aligned to 0x20-byte tiles")
    return tuple(
        portraits.decode_snes_4bpp(
            block[offset : offset + BYTES_PER_4BPP_TILE], 8, 8
        )
        for offset in range(0, len(block), BYTES_PER_4BPP_TILE)
    )


def decode_menu_portrait_tiles(rom: bytes) -> tuple[tuple[int, ...], ...]:
    if len(rom) < MENU_PORTRAIT_FILE_END_EXCLUSIVE:
        raise ValueError("ROM is too short for the menu-portrait range")
    block = rom[
        MENU_PORTRAIT_FILE_START:MENU_PORTRAIT_FILE_END_EXCLUSIVE
    ]
    return decode_4bpp_tile_block(block)


def packed_candidate_assets(
    source_raw: bytes, source: dict[str, Any]
) -> tuple[
    dict[str, tuple[int, int, tuple[int, ...]]],
    dict[str, dict[str, Any]],
]:
    """Build and decode candidates so the audit covers the packed assets."""

    assets = portraits.validate_source(source)
    outputs = portraits.build_outputs(source_raw, source)
    candidates: dict[str, tuple[int, int, tuple[int, ...]]] = {}
    packed_metadata: dict[str, dict[str, Any]] = {}
    for asset_id in sorted(assets):
        width, height, _ = portraits.asset_pixels(assets[asset_id])
        filename = portraits.PACKED_FILENAMES[asset_id]
        packed = outputs[filename]
        candidates[asset_id] = (
            width,
            height,
            portraits.decode_snes_4bpp(packed, width, height),
        )
        packed_metadata[asset_id] = {
            "filename": filename,
            "size": len(packed),
            "sha256": portraits.sha256(packed),
            "tile_count": len(packed) // BYTES_PER_4BPP_TILE,
        }
    return candidates, packed_metadata


def visible_pattern(tile: Sequence[int]) -> tuple[int, ...]:
    """Canonicalize visible color labels while keeping transparent zero fixed.

    Every non-zero palette index is renamed by first occurrence. This compares
    region geometry independent of visible palette-index assignment while
    retaining the background/transparent mask.
    """

    if len(tile) != 64:
        raise ValueError("tile must contain 64 pixels")
    labels: dict[int, int] = {}
    next_label = 1
    result = []
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


def _visible_index_count(tile: Sequence[int]) -> int:
    return len({pixel for pixel in tile if pixel != 0})


def _reference_offset(reference_tile_index: int) -> str:
    return (
        f"0x{MENU_PORTRAIT_FILE_START + reference_tile_index * BYTES_PER_4BPP_TILE:06X}"
    )


def audit_tiles(
    candidate_assets: dict[str, tuple[int, int, Sequence[int]]],
    reference_tiles: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Return metadata-only exact and visible-pattern match records."""

    exact_index: dict[tuple[int, ...], set[int]] = defaultdict(set)
    pattern_index: dict[tuple[int, ...], set[int]] = defaultdict(set)
    excluded_reference_indices = []

    for reference_index, reference in enumerate(reference_tiles):
        reference_tuple = tuple(reference)
        visible = _visible_count(reference_tuple)
        if visible <= TRIVIAL_VISIBLE_PIXEL_LIMIT:
            excluded_reference_indices.append(reference_index)
            continue
        for variant in portraits.tile_variants(reference_tuple):
            exact_index[variant].add(reference_index)
            pattern_index[visible_pattern(variant)].add(reference_index)

    exact_matches = []
    pattern_matches = []
    excluded_candidates = []
    candidate_tile_count = 0
    for asset_id in sorted(candidate_assets):
        width, height, pixels = candidate_assets[asset_id]
        for candidate_index, candidate in enumerate(
            portraits.iter_tiles(pixels, width, height)
        ):
            candidate_tile_count += 1
            visible = _visible_count(candidate)
            if visible <= TRIVIAL_VISIBLE_PIXEL_LIMIT:
                excluded_candidates.append(
                    {
                        "asset_id": asset_id,
                        "candidate_tile_index": candidate_index,
                        "visible_pixel_count": visible,
                    }
                )
                continue

            exact_references = exact_index.get(candidate, set())
            for reference_index in sorted(exact_references):
                exact_matches.append(
                    {
                        "asset_id": asset_id,
                        "candidate_tile_index": candidate_index,
                        "reference_tile_index": reference_index,
                        "reference_file_offset": _reference_offset(
                            reference_index
                        ),
                    }
                )

            pattern_references = pattern_index.get(
                visible_pattern(candidate), set()
            )
            for reference_index in sorted(pattern_references):
                reference = reference_tiles[reference_index]
                also_exact = reference_index in exact_references
                visible_index_count = _visible_index_count(candidate)
                pattern_matches.append(
                    {
                        "asset_id": asset_id,
                        "candidate_tile_index": candidate_index,
                        "reference_tile_index": reference_index,
                        "reference_file_offset": _reference_offset(
                            reference_index
                        ),
                        "also_exact_index_match": also_exact,
                        "visible_pixel_count": visible,
                        "candidate_visible_index_count": visible_index_count,
                        "reference_visible_index_count": (
                            _visible_index_count(reference)
                        ),
                        "false_positive_risk": (
                            "high-single-visible-index"
                            if visible_index_count <= 1
                            else "review-required"
                        ),
                    }
                )

    return {
        "candidate_tile_count": candidate_tile_count,
        "reference_tile_count": len(reference_tiles),
        "trivial_visible_pixel_limit": TRIVIAL_VISIBLE_PIXEL_LIMIT,
        "excluded_candidate_tiles": excluded_candidates,
        "excluded_reference_tile_count": len(excluded_reference_indices),
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
    source_raw, source = portraits.load_json(source_path)
    candidate_assets, packed_metadata = packed_candidate_assets(
        source_raw, source
    )
    reference_tiles = decode_menu_portrait_tiles(rom)
    audit = audit_tiles(candidate_assets, reference_tiles)
    return {
        "schema_version": 1,
        "tool": {
            "path": "tools/audit_schala_portrait_originality.py",
            "version": TOOL_VERSION,
        },
        "evidence": "verified-static",
        "reproduction": (
            "python tools/audit_schala_portrait_originality.py "
            '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
        ),
        "canonical_rom": rom_identity,
        "canonical_source": {
            "path": "assets/source/schala/v0/portrait/"
            "schala_portraits_v0.json",
            "sha256": portraits.sha256(source_raw),
        },
        "packed_candidates": packed_metadata,
        "reference_scope": {
            "description": (
                "known uncompressed seven-character menu portrait tiles"
            ),
            "file_start": f"0x{MENU_PORTRAIT_FILE_START:06X}",
            "file_end_inclusive": (
                f"0x{MENU_PORTRAIT_FILE_END_EXCLUSIVE - 1:06X}"
            ),
            "byte_count": (
                MENU_PORTRAIT_FILE_END_EXCLUSIVE
                - MENU_PORTRAIT_FILE_START
            ),
            "tile_count": len(reference_tiles),
            "coverage_limit": (
                "This bounded audit does not cover compressed NPC graphics, "
                "field sprites, battle sprites, or other ROM regions."
            ),
        },
        "comparison_policy": {
            "transforms": ["identity", "horizontal", "vertical", "combined"],
            "exact_index_comparison": True,
            "visible_pattern_comparison": (
                "Non-zero palette labels are canonicalized; transparent/"
                "background index zero remains fixed."
            ),
            "trivial_exclusion": (
                "Candidate and reference tiles with at most two non-zero "
                "pixels are reported as excluded, not matches."
            ),
            "false_positive_handling": (
                "Visible-pattern matches are review leads, never automatic "
                "proof of copying. Single-visible-index patterns are marked "
                "high risk. Exact matches also require human provenance "
                "review before any conclusion."
            ),
        },
        "audit": audit,
        "copyright_boundary": (
            "No canonical-ROM tile bytes, decoded pixels, or palettes are "
            "included in this report or written by the tool."
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
        "--source", type=pathlib.Path, default=portraits.DEFAULT_SOURCE
    )
    args = parser.parse_args()
    report = build_report(args.rom, args.source)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
