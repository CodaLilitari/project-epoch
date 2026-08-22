#!/usr/bin/env python3
"""Audit the twelve Glass Focus visual assets against canonical PC tiles.

This is a read-only, Focus-specific wrapper over the established playable-PC
tile auditor.  It accepts one explicitly named, hash-gated clean ROM, always
uses the fixed canonical Glass Focus source and manifest, emits JSON only on
standard output, and has no output-file option.  No ROM bytes, decoded
reference pixels, images, patches, or other binary artifacts are emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections.abc import Sequence
from typing import Any

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import audit_schala_gameplay_originality as pc_audit
import validate_schala_glass_focus_pulse_v0 as focus


TOOL_VERSION = "1.0.0"
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_REL = pathlib.Path("tools/audit_schala_glass_focus_originality.py")
SOURCE_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_v0.json"
)
MANIFEST_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_manifest_v0.json"
)
SOURCE_PATH = ROOT / SOURCE_REL
MANIFEST_PATH = ROOT / MANIFEST_REL
REPRODUCTION_COMMAND = (
    "python tools/audit_schala_glass_focus_originality.py "
    '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
)
EXPECTED_COUNTS = {
    "asset_count": 12,
    "candidate_tile_occurrence_count": 174,
    "excluded_candidate_tile_count": 80,
    "compared_candidate_tile_count": 94,
    "reference_tile_count": 7264,
    "excluded_reference_tile_count": 59,
    "compared_reference_tile_count": 7205,
    "exact_index_match_count": 0,
    "visible_pattern_match_count": 0,
}
TRANSFORMS = ("identity", "horizontal", "vertical", "combined")


class GlassFocusOriginalityError(ValueError):
    """Raised when the bounded originality evidence no longer reproduces."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_report_bytes(report: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            report,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _candidate_assets(
    validated: dict[str, Any],
) -> tuple[
    dict[str, tuple[int, int, Sequence[int]]],
    tuple[str, ...],
]:
    candidates: dict[str, tuple[int, int, Sequence[int]]] = {}
    asset_ids: list[str] = []
    for asset_id in focus.FRAME_IDS:
        candidates[asset_id] = focus._parse_pixels(
            validated["frames"][asset_id], focus.FRAME_DIMENSIONS
        )
        asset_ids.append(asset_id)
    for asset_id in focus.INSERT_IDS:
        candidates[asset_id] = focus._parse_pixels(
            validated["inserts"][asset_id], focus.INSERT_DIMENSIONS
        )
        asset_ids.append(asset_id)
    if len(candidates) != len(asset_ids):
        raise GlassFocusOriginalityError("candidate asset IDs are not unique")
    return candidates, tuple(asset_ids)


def _actual_counts(
    asset_ids: Sequence[str], audit: dict[str, Any]
) -> dict[str, int]:
    candidate_total = audit["candidate_tile_count"]
    excluded_candidates = len(audit["excluded_candidate_tiles"])
    reference_total = audit["reference_tile_count"]
    excluded_references = audit["excluded_reference_tile_count"]
    return {
        "asset_count": len(asset_ids),
        "candidate_tile_occurrence_count": candidate_total,
        "excluded_candidate_tile_count": excluded_candidates,
        "compared_candidate_tile_count": candidate_total
        - excluded_candidates,
        "reference_tile_count": reference_total,
        "excluded_reference_tile_count": excluded_references,
        "compared_reference_tile_count": reference_total
        - excluded_references,
        "exact_index_match_count": len(audit["exact_index_matches"]),
        "visible_pattern_match_count": len(
            audit["visible_pattern_matches"]
        ),
    }


def _require_expected_counts(counts: dict[str, int]) -> None:
    if counts != EXPECTED_COUNTS:
        raise GlassFocusOriginalityError(
            f"bounded originality counts drifted: {counts}"
        )


def build_report(rom_path: pathlib.Path) -> dict[str, Any]:
    source_raw, source = focus.load_json(SOURCE_PATH)
    validated = focus.validate_source(source)
    source_report = focus.validation_report(source_raw, source)
    _, manifest = focus.load_json(MANIFEST_PATH)
    focus.verify_manifest_core(manifest, source_raw, source_report)

    rom, rom_identity = pc_audit.verify_canonical_rom(rom_path)
    candidates, asset_ids = _candidate_assets(validated)
    reference_tiles = pc_audit.decode_reference_tiles(rom)
    audit = pc_audit.audit_tiles(candidates, reference_tiles)
    counts = _actual_counts(asset_ids, audit)
    _require_expected_counts(counts)

    tool_path = ROOT / TOOL_REL
    tool_raw = tool_path.read_bytes()
    return {
        "schema_version": 1,
        "tool": {
            "path": TOOL_REL.as_posix(),
            "sha256": sha256(tool_raw),
            "size": len(tool_raw),
            "version": TOOL_VERSION,
        },
        "reproduction": REPRODUCTION_COMMAND,
        "canonical_source": {
            "path": SOURCE_REL.as_posix(),
            "sha256": sha256(source_raw),
            "size": len(source_raw),
        },
        "canonical_rom": rom_identity,
        "candidate_scope": {
            "asset_ids": list(asset_ids),
            "asset_count": counts["asset_count"],
            "tile_occurrence_count": counts[
                "candidate_tile_occurrence_count"
            ],
            "trivial_visible_pixel_limit": (
                pc_audit.TRIVIAL_VISIBLE_PIXEL_LIMIT
            ),
            "excluded_tile_occurrence_count": counts[
                "excluded_candidate_tile_count"
            ],
            "compared_tile_occurrence_count": counts[
                "compared_candidate_tile_count"
            ],
        },
        "reference_scope": {
            "description": (
                "All seven raw playable-character graphics windows selected "
                "by the canonical $E4:2000 pointer table."
            ),
            "tile_count": counts["reference_tile_count"],
            "excluded_trivial_tile_count": counts[
                "excluded_reference_tile_count"
            ],
            "compared_tile_count": counts[
                "compared_reference_tile_count"
            ],
            "coverage_limit": (
                "This audit does not cover NPC or enemy packets, portraits, "
                "assembly data, animation data, or VFX."
            ),
        },
        "comparison_policy": {
            "transforms": list(TRANSFORMS),
            "exact_index_comparison": True,
            "visible_pattern_comparison": (
                "Non-zero palette labels are canonicalized by first use; "
                "transparent index zero remains fixed."
            ),
            "trivial_exclusion": (
                "Candidate and reference tiles with at most two visible "
                "pixels are excluded from comparison."
            ),
        },
        "results": {
            "exact_index_match_count": counts[
                "exact_index_match_count"
            ],
            "visible_pattern_match_count": counts[
                "visible_pattern_match_count"
            ],
        },
        "evidence": "verified-static",
        "npc_originality_claimed": False,
        "files_emitted": False,
        "copyright_boundary": (
            "No canonical-ROM bytes, decoded reference pixels, palettes, "
            "images, or candidate image data are included in this report or "
            "written by this tool."
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
    args = parser.parse_args()
    sys.stdout.buffer.write(canonical_report_bytes(build_report(args.rom)))


if __name__ == "__main__":
    main()
