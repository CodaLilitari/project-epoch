#!/usr/bin/env python3
"""Validate the source-only Project Epoch Glass Focus vertical slice.

The canonical source contains original indexed pixels and two parametric audio
recipes. This validator reads no ROM, save, emulator state, sampled audio, or
extracted game asset. It emits a JSON validation report on standard output and
writes no files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections.abc import Iterable, Sequence
from typing import Any


VALIDATOR_VERSION = "1.0.0"
ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_v0.json"
)
MANIFEST_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_manifest_v0.json"
)
ORIGINALITY_REPORT_REL = pathlib.Path(
    "references/schala_glass_focus_originality_v0.json"
)
GAMEPLAY_REL = pathlib.Path(
    "assets/source/schala/v0/gameplay/"
    "schala_gameplay_foundation_v0.json"
)
ITEM_REL = pathlib.Path(
    "assets/source/schala/v0/content/schala_item_content_v0.json"
)
TECH_REL = pathlib.Path(
    "assets/source/schala/v0/content/schala_tech_content_v0.json"
)
DEFAULT_SOURCE = ROOT / SOURCE_REL
DEFAULT_MANIFEST = ROOT / MANIFEST_REL

SOURCE_CREATED = "2026-07-28"
SOURCE_AUTHOR = "OpenAI Codex"
SOURCE_SCOPE_STATEMENT = (
    "One Glass Focus vertical slice: six dedicated right-facing basic-attack "
    "body frames, six standalone Focus inserts, and two original "
    "deterministic audio recipes. It is not an animation packet, native "
    "sound record, ROM allocation, or runtime binding."
)
VISUAL_AUTHORSHIP_METHOD = (
    "Existing original Project Epoch Schala body rows were reused and "
    "adapted into six new basic-attack poses; the six standalone Focus "
    "inserts were authored independently as hexadecimal palette indices on "
    "clean 16x16 target grids."
)
VISUAL_AUTHORSHIP_STATEMENT = (
    "The existing original Project Epoch Schala gameplay source was opened "
    "and its body pixels were deliberately reused or adapted. No external "
    "layer, ROM, save, emulator state, NPC sprite, vanilla playable-character "
    "sprite, extracted tile, official-art pixel, or concept pixel was "
    "imported, traced, sampled, transformed, or resized."
)
AUDIO_AUTHORSHIP_METHOD = (
    "Integer-only oscillator, seeded-noise, amplitude-envelope, pitch, and "
    "trigger parameters authored specifically for Project Epoch."
)
AUDIO_AUTHORSHIP_STATEMENT = (
    "No recording, sample, ROM sound data, SPC state, BRR block, or existing "
    "game sound parameters were imported or copied."
)
AUDIT_SCOPE = (
    "The twelve Glass Focus visual assets contain 174 candidate tile "
    "occurrences, but only nontrivial tiles are compared: 80 candidates with "
    "at most two visible pixels are excluded and 94 are compared against "
    "7,205 nontrivial references after excluding 59 of the 7,264 raw tiles "
    "in the seven canonical playable-character graphics windows."
)
AUDIT_METHOD = (
    "Metadata-only exact-index and palette-renaming-invariant geometry "
    "comparison, including H/V/HV transforms."
)
AUDIT_COMMAND = (
    "python tools/audit_schala_glass_focus_originality.py "
    '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
)
AUDIT_CORRECTION = (
    "Added and repositioned only Project Epoch-owned impact-arc pixels in "
    "the two reported cells without displaying, exporting, tracing, "
    "sampling, or otherwise viewing reference pixels."
)
MANIFEST_CREATED = "2026-07-28"
MANIFEST_MODIFIED = "2026-07-28"
MANIFEST_AUTHOR = "OpenAI Codex"
MANIFEST_REVIEW_STATUS = (
    "deterministic source validation and bounded canonical playable-PC "
    "metadata audit complete; human visual and audio-design review pending"
)
MANIFEST_PROVENANCE_STATEMENT = (
    "The six body frames truthfully reuse or adapt existing original Project "
    "Epoch Schala body pixels; the six Focus inserts and two integer-only "
    "audio recipes are new Project Epoch source. A metadata-only playable-PC "
    "audit correction changed only Project Epoch-owned impact-arc cells and "
    "now has zero exact or palette-pattern matches without displaying or "
    "exporting reference pixels. No external, ROM, NPC, vanilla-PC, "
    "extracted-tile, sampled-audio, SPC, BRR, or existing-game-SFX data was "
    "imported; NPC originality remains unproved."
)
ORIGINALITY_REPORT_SHA256 = (
    "90f63ef914e40065ff3f2e3c09a5d255833f7efbd4f0168833779e9156d019ec"
)
ORIGINALITY_REPORT_SIZE = 2649

EXPECTED_DEPENDENCY_HASHES = {
    GAMEPLAY_REL.as_posix(): (
        "9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2"
    ),
    ITEM_REL.as_posix(): (
        "f0125b36b225e11b149b35019b7ae19756a8c9ec82cd43067a1637b8702ad205"
    ),
    TECH_REL.as_posix(): (
        "efb2468da3eaa9e8f1ae0cf059a1ee45deac80694b0cc6c1f2ad475ba40ff4a5"
    ),
    "docs/schala_sprite_asset_spec_v0.md": (
        "5157f5ab3eb219e9e2a767ee884a173d386bc6937f62255cbae0681d415b0cb9"
    ),
    "docs/schala_focus_pulse_adapter_architecture.md": (
        "f070017a327629f153d0d0570a33c3d52d744b57e44cfe202e1c98012d1cbe35"
    ),
    "tools/audit_schala_gameplay_originality.py": (
        "77f6724c5a0bfc73e26239337325f0a094920954023978aae97c641a0804f0be"
    ),
    "tools/audit_schala_glass_focus_originality.py": (
        "addbb63ce0d5c92972fc467bc7d0e92f6cab3015f792a9c8da90101c492d8ce7"
    ),
}

EXPECTED_REFERENCE_METADATA = {
    GAMEPLAY_REL.as_posix(): {
        "source_classification": "project-epoch-original-target-grid-source",
        "use": (
            "Original Schala body, material, and indexed-palette vocabulary "
            "only; no vanilla or NPC source."
        ),
    },
    ITEM_REL.as_posix(): {
        "source_classification": "project-epoch-original-content-source",
        "use": "Glass Focus item $E8 and Focus visual 0 identity only.",
    },
    TECH_REL.as_posix(): {
        "source_classification": "project-epoch-original-content-source",
        "use": "Focus Pulse action $90 identity and short-pulse intent only.",
    },
    "docs/schala_sprite_asset_spec_v0.md": {
        "source_classification": "project-asset-specification",
        "use": (
            "40x40 battle-action canvas, four-object envelope, Focus "
            "vocabulary, palette, and provenance requirements."
        ),
    },
    "docs/schala_focus_pulse_adapter_architecture.md": {
        "source_classification": "project-adapter-boundary",
        "use": (
            "Identity-only source boundary; no runtime values, table bytes, "
            "selectors, or pointers imported."
        ),
    },
    "tools/audit_schala_gameplay_originality.py": {
        "source_classification": "project-metadata-only-originality-auditor",
        "use": (
            "Underlying canonical playable-PC exact-index and palette-pattern "
            "comparison implementation only; no Focus-specific or NPC "
            "originality claim."
        ),
    },
    "tools/audit_schala_glass_focus_originality.py": {
        "source_classification": (
            "project-focus-specific-read-only-originality-auditor"
        ),
        "use": (
            "Fixed-source wrapper that compares the six Glass Focus frames "
            "and six inserts against canonical playable-PC tiles; no NPC "
            "originality claim."
        ),
    },
}

FRAME_PHASES = (
    ("schala_battle_basic_attack_draw_f00_v0", "draw"),
    ("schala_battle_basic_attack_open_f01_v0", "open"),
    ("schala_battle_basic_attack_pulse_f02_v0", "pulse"),
    (
        "schala_battle_basic_attack_followthrough_f03_v0",
        "followthrough",
    ),
    ("schala_battle_basic_attack_recoil_f04_v0", "recoil"),
    ("schala_battle_basic_attack_recover_f05_v0", "recover"),
)
FRAME_COMPOSITIONS = (
    (
        "Schala lowers her forward shoulder, opens her palm, and draws a "
        "compact closed crescent above it."
    ),
    (
        "Her wrists cross briefly while the crescent rolls a quarter turn "
        "into a narrow ring."
    ),
    (
        "Schala plants both feet and releases a small open ring with a short "
        "rose-violet pulse."
    ),
    (
        "The ring turns edge-on while Schala follows the pulse with an "
        "extended palm and compressed mantle."
    ),
    (
        "Schala absorbs the recoil into a bent elbow while a small detached "
        "impact arc marks the targetward end."
    ),
    (
        "The Focus contracts to one bright point as Schala lowers her hand "
        "and restores her planted stance."
    ),
)
FRAME_IDS = tuple(value[0] for value in FRAME_PHASES)
PHASES = tuple(value[1] for value in FRAME_PHASES)
INSERT_VOCABULARY = (
    ("glass_focus_closed_crescent_v0", "closed_crescent"),
    ("glass_focus_open_ring_v0", "open_ring"),
    ("glass_focus_quarter_turn_ring_v0", "quarter_turn_ring"),
    ("glass_focus_edge_on_ring_v0", "edge_on_ring"),
    ("glass_focus_collapse_point_v0", "collapse_point"),
    ("glass_focus_impact_arc_v0", "impact_arc"),
)
INSERT_IDS = tuple(value[0] for value in INSERT_VOCABULARY)
AUDIO_IDS = ("focus_swing_v0", "focus_hit_v0")
FRAME_INSERT_IDS = (
    "glass_focus_closed_crescent_v0",
    "glass_focus_quarter_turn_ring_v0",
    "glass_focus_open_ring_v0",
    "glass_focus_edge_on_ring_v0",
    "glass_focus_impact_arc_v0",
    "glass_focus_collapse_point_v0",
)
FRAME_DIMENSIONS = (40, 40)
INSERT_DIMENSIONS = (16, 16)
PALETTE_ID = "schala_gameplay_palette_v0"
FOCUS_INSERT_INDICES = (0, 1, 13, 14, 15)
IMPACT_ARC_CORRECTED_TILE_VISIBLE_COUNTS = {0: 12, 2: 11}
INDEX_ROW = re.compile(r"^[0-9A-F]{8}( [0-9A-F]{8})+$")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
AUDIO_FILE_SUFFIXES = (".wav", ".aiff", ".aif", ".pcm", ".brr", ".spc")


class FocusSourceError(ValueError):
    """Raised when the Glass Focus source violates its source-only contract."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FocusSourceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: pathlib.Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FocusSourceError(f"{path}: invalid UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise FocusSourceError(f"{path}: top level must be an object")
    return raw, parsed


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _require_exact_keys(
    value: dict[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise FocusSourceError(
            f"{label} key set drifted; missing={missing}, extra={extra}"
        )


def _require_int(
    value: Any, label: str, minimum: int, maximum: int
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise FocusSourceError(
            f"{label} must be an integer from {minimum} through {maximum}"
        )
    return value


def _walk(value: Any) -> Iterable[tuple[str | None, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield None, child
            yield from _walk(child)


def _parse_pixels(
    asset: dict[str, Any],
    expected_dimensions: tuple[int, int],
) -> tuple[int, int, tuple[int, ...]]:
    asset_id = asset.get("id")
    width = asset.get("width")
    height = asset.get("height")
    if (width, height) != expected_dimensions:
        raise FocusSourceError(
            f"{asset_id}: expected {expected_dimensions[0]}x"
            f"{expected_dimensions[1]}"
        )
    if (
        asset.get("indexed_color_mode")
        != "4bpp-index-cell-rows"
    ):
        raise FocusSourceError(f"{asset_id}: source must be indexed 4bpp")
    if asset.get("palette_id") != PALETTE_ID:
        raise FocusSourceError(f"{asset_id}: palette dependency drifted")
    rows = asset.get("rows")
    if not isinstance(rows, list) or len(rows) != height:
        raise FocusSourceError(f"{asset_id}: row count does not match height")
    pixels: list[int] = []
    expected_cells = width // 8
    for row_index, row in enumerate(rows):
        if not isinstance(row, str) or not INDEX_ROW.fullmatch(row):
            raise FocusSourceError(
                f"{asset_id}: row {row_index} must be uppercase "
                "8-pixel hexadecimal cells"
            )
        cells = row.split(" ")
        if len(cells) != expected_cells:
            raise FocusSourceError(
                f"{asset_id}: row {row_index} must contain "
                f"{expected_cells} cells"
            )
        pixels.extend(int(character, 16) for character in "".join(cells))
    if not any(pixels):
        raise FocusSourceError(f"{asset_id}: asset is fully transparent")
    return width, height, tuple(pixels)


def iter_tiles(
    pixels: Sequence[int], width: int, height: int
) -> Iterable[tuple[int, ...]]:
    if len(pixels) != width * height or width % 8 or height % 8:
        raise FocusSourceError("tile iteration requires a complete 8x8 grid")
    for tile_y in range(0, height, 8):
        for tile_x in range(0, width, 8):
            yield tuple(
                pixels[(tile_y + y) * width + tile_x + x]
                for y in range(8)
                for x in range(8)
            )


def occupied_tile_count(
    pixels: Sequence[int], width: int, height: int
) -> int:
    return sum(any(tile) for tile in iter_tiles(pixels, width, height))


def encode_snes_4bpp(
    pixels: Sequence[int], width: int, height: int
) -> bytes:
    packed = bytearray()
    for tile in iter_tiles(pixels, width, height):
        low_planes = bytearray()
        high_planes = bytearray()
        for y in range(8):
            planes = [0, 0, 0, 0]
            for x in range(8):
                value = tile[y * 8 + x]
                if not 0 <= value <= 15:
                    raise FocusSourceError("pixel index does not fit 4bpp")
                mask = 1 << (7 - x)
                for plane in range(4):
                    if value & (1 << plane):
                        planes[plane] |= mask
            low_planes.extend(planes[:2])
            high_planes.extend(planes[2:])
        packed.extend(low_planes)
        packed.extend(high_planes)
    return bytes(packed)


def decode_snes_4bpp(
    packed: bytes, width: int, height: int
) -> tuple[int, ...]:
    tile_count = (width // 8) * (height // 8)
    if len(packed) != tile_count * 32:
        raise FocusSourceError("packed 4bpp size does not match dimensions")
    pixels = [0] * (width * height)
    for tile_index in range(tile_count):
        tile_x = (tile_index % (width // 8)) * 8
        tile_y = (tile_index // (width // 8)) * 8
        tile = packed[tile_index * 32 : (tile_index + 1) * 32]
        for y in range(8):
            planes = (
                tile[y * 2],
                tile[y * 2 + 1],
                tile[16 + y * 2],
                tile[16 + y * 2 + 1],
            )
            for x in range(8):
                mask = 1 << (7 - x)
                value = sum(
                    ((plane_byte & mask) != 0) << plane
                    for plane, plane_byte in enumerate(planes)
                )
                pixels[(tile_y + y) * width + tile_x + x] = value
    return tuple(pixels)


def _encode_palette(palette: dict[str, Any]) -> bytes:
    if palette.get("id") != PALETTE_ID:
        raise FocusSourceError("gameplay palette ID drifted")
    if palette.get("transparent_index") != 0:
        raise FocusSourceError("gameplay transparency index drifted")
    entries = palette.get("entries")
    if not isinstance(entries, list) or len(entries) != 16:
        raise FocusSourceError("gameplay palette must have 16 entries")
    encoded = bytearray()
    for expected_index, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("index") != expected_index:
            raise FocusSourceError("gameplay palette entries are unordered")
        color = entry.get("hex")
        if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
            raise FocusSourceError("gameplay palette contains invalid RGB")
        red, green, blue = (
            int(color[index : index + 2], 16) for index in (1, 3, 5)
        )
        bgr555 = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
        encoded.extend(bgr555.to_bytes(2, "little"))
    return bytes(encoded)


def _validate_dependencies(
    source: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    references = source.get("references")
    if not isinstance(references, list):
        raise FocusSourceError("references must be an array")
    by_path: dict[str, dict[str, Any]] = {}
    for reference in references:
        if not isinstance(reference, dict):
            raise FocusSourceError("reference must be an object")
        _require_exact_keys(
            reference,
            {"path", "sha256", "source_classification", "use"},
            "reference",
        )
        path = reference.get("path")
        if not isinstance(path, str) or path in by_path:
            raise FocusSourceError("reference paths must be unique strings")
        by_path[path] = reference
    if set(by_path) != set(EXPECTED_DEPENDENCY_HASHES):
        raise FocusSourceError("reference dependency set drifted")
    for relative, expected_hash in EXPECTED_DEPENDENCY_HASHES.items():
        dependency_path = ROOT / pathlib.PurePosixPath(relative)
        actual_hash = sha256(dependency_path.read_bytes())
        if actual_hash != expected_hash:
            raise FocusSourceError(f"dependency hash drifted: {relative}")
        if by_path[relative].get("sha256") != expected_hash:
            raise FocusSourceError(f"reference hash drifted: {relative}")
        expected_metadata = EXPECTED_REFERENCE_METADATA[relative]
        for field, expected in expected_metadata.items():
            if by_path[relative].get(field) != expected:
                raise FocusSourceError(
                    f"reference {field} drifted: {relative}"
                )

    gameplay_raw, gameplay = load_json(ROOT / GAMEPLAY_REL)
    item_raw, item_source = load_json(ROOT / ITEM_REL)
    tech_raw, tech_source = load_json(ROOT / TECH_REL)
    if sha256(gameplay_raw) != EXPECTED_DEPENDENCY_HASHES[
        GAMEPLAY_REL.as_posix()
    ]:
        raise FocusSourceError("gameplay source hash drifted")
    if sha256(item_raw) != EXPECTED_DEPENDENCY_HASHES[ITEM_REL.as_posix()]:
        raise FocusSourceError("item source hash drifted")
    if sha256(tech_raw) != EXPECTED_DEPENDENCY_HASHES[TECH_REL.as_posix()]:
        raise FocusSourceError("tech source hash drifted")
    palette = gameplay.get("palette")
    if not isinstance(palette, dict):
        raise FocusSourceError("gameplay source lacks its palette")
    return item_source, tech_source, _encode_palette(palette)


def _validate_binding_identity(
    source: dict[str, Any],
    item_source: dict[str, Any],
    tech_source: dict[str, Any],
) -> None:
    identity = source.get("binding_identity")
    if not isinstance(identity, dict):
        raise FocusSourceError("binding_identity is required")
    _require_exact_keys(
        identity,
        {
            "logical_pc_id",
            "action_id",
            "item_id",
            "focus_visual_id",
            "binding_state",
        },
        "binding_identity",
    )
    if identity != {
        "logical_pc_id": 7,
        "action_id": 0x90,
        "item_id": 0xE8,
        "focus_visual_id": 0,
        "binding_state": "unbound",
    }:
        raise FocusSourceError("Glass Focus identity drifted")
    for field in (
        "logical_pc_id",
        "action_id",
        "item_id",
        "focus_visual_id",
    ):
        if type(identity[field]) is not int:
            raise FocusSourceError(
                f"binding_identity.{field} must be an integer"
            )

    bindings = source.get("native_runtime_bindings")
    if not isinstance(bindings, dict):
        raise FocusSourceError("native_runtime_bindings is required")
    expected_binding_keys = {
        "native_action_record_id",
        "native_weapon_visual_id",
        "native_palette_id",
        "native_swing_sfx_id",
        "native_hit_sfx_id",
        "graphics_pointer",
        "animation_pointer",
        "effect_pointer",
        "palette_pointer",
        "swing_sfx_pointer",
        "hit_sfx_pointer",
        "runtime_descriptor_pointer",
    }
    _require_exact_keys(bindings, expected_binding_keys, "runtime bindings")
    if any(value is not None for value in bindings.values()):
        raise FocusSourceError("every native/runtime binding must remain null")

    item_ids = [
        value
        for key, value in _walk(source)
        if key == "item_id"
    ]
    visual_ids = [
        value
        for key, value in _walk(source)
        if key == "focus_visual_id"
    ]
    action_ids = [
        value
        for key, value in _walk(source)
        if key == "action_id"
    ]
    if item_ids != [0xE8] or visual_ids != [0] or action_ids != [0x90]:
        raise FocusSourceError(
            "source may bind only item $E8, visual 0, and action $90"
        )

    items = item_source.get("items")
    if not isinstance(items, list):
        raise FocusSourceError("item dependency lacks items")
    glass = [
        value
        for value in items
        if isinstance(value, dict) and value.get("item_id") == 0xE8
    ]
    if len(glass) != 1:
        raise FocusSourceError("item source must contain one Glass Focus")
    if (
        glass[0].get("design_name") != "Glass Focus"
        or glass[0].get("focus_visual_id") != 0
        or glass[0].get("native_binding") is not None
    ):
        raise FocusSourceError("Glass Focus dependency identity drifted")

    commands = tech_source.get("commands")
    if not isinstance(commands, list):
        raise FocusSourceError("tech dependency lacks commands")
    focus_pulse = [
        value
        for value in commands
        if isinstance(value, dict)
        and value.get("design_name") == "Focus Pulse"
    ]
    if len(focus_pulse) != 1:
        raise FocusSourceError("tech source must contain one Focus Pulse")
    if (
        focus_pulse[0].get("action_id") != 0x90
        or focus_pulse[0].get("kind") != "basic"
        or focus_pulse[0].get("primitive_binding") is not None
    ):
        raise FocusSourceError("Focus Pulse dependency identity drifted")


def _validate_provenance(source: dict[str, Any]) -> None:
    if (
        source.get("source_classification")
        != "project-epoch-original-same-project-derived-multimedia-source"
    ):
        raise FocusSourceError("source classification drifted")
    provenance = source.get("provenance")
    if not isinstance(provenance, dict):
        raise FocusSourceError("provenance is required")
    _require_exact_keys(
        provenance,
        {
            "visual_authorship",
            "audio_authorship",
            "playable_pc_metadata_correction",
        },
        "provenance",
    )
    visual = provenance["visual_authorship"]
    audio = provenance["audio_authorship"]
    if not isinstance(visual, dict) or not isinstance(audio, dict):
        raise FocusSourceError("authorship records must be objects")
    _require_exact_keys(
        visual,
        {
            "method",
            "same_project_original_body_pixels_reused",
            "same_project_source_path",
            "same_project_source_sha256",
            "external_imported_layers",
            "external_imported_pixels",
            "rom_or_extracted_tile_input",
            "npc_sprite_input",
            "vanilla_playable_character_sprite_input",
            "official_art_pixel_input",
            "concept_bitmap_input",
            "concept_pixels_sampled",
            "concept_palette_sampled",
            "automatic_resizing",
            "statement",
        },
        "visual_authorship",
    )
    _require_exact_keys(
        audio,
        {
            "method",
            "sampled_audio_input",
            "rom_or_extracted_sfx_input",
            "copied_vanilla_sfx_parameters",
            "rendered_audio_committed",
            "statement",
        },
        "audio_authorship",
    )
    if (
        visual.get("method") != VISUAL_AUTHORSHIP_METHOD
        or visual.get("statement") != VISUAL_AUTHORSHIP_STATEMENT
    ):
        raise FocusSourceError("visual authorship narrative drifted")
    if (
        audio.get("method") != AUDIO_AUTHORSHIP_METHOD
        or audio.get("statement") != AUDIO_AUTHORSHIP_STATEMENT
    ):
        raise FocusSourceError("audio authorship narrative drifted")
    for flag in (
        "external_imported_layers",
        "external_imported_pixels",
        "rom_or_extracted_tile_input",
        "npc_sprite_input",
        "vanilla_playable_character_sprite_input",
        "official_art_pixel_input",
        "concept_bitmap_input",
        "concept_pixels_sampled",
        "concept_palette_sampled",
        "automatic_resizing",
    ):
        if visual.get(flag) is not False:
            raise FocusSourceError(
                f"visual provenance flag must remain false: {flag}"
            )
    if visual.get("same_project_original_body_pixels_reused") is not True:
        raise FocusSourceError(
            "same-project original body reuse must be declared truthfully"
        )
    if (
        visual.get("same_project_source_path") != GAMEPLAY_REL.as_posix()
        or visual.get("same_project_source_sha256")
        != EXPECTED_DEPENDENCY_HASHES[GAMEPLAY_REL.as_posix()]
    ):
        raise FocusSourceError("same-project body source provenance drifted")
    for flag in (
        "sampled_audio_input",
        "rom_or_extracted_sfx_input",
        "copied_vanilla_sfx_parameters",
        "rendered_audio_committed",
    ):
        if audio.get(flag) is not False:
            raise FocusSourceError(
                f"audio provenance flag must remain false: {flag}"
            )
    correction = provenance["playable_pc_metadata_correction"]
    if not isinstance(correction, dict):
        raise FocusSourceError(
            "playable-PC metadata correction must be an object"
        )
    _require_exact_keys(
        correction,
        {
            "audit_scope",
            "method",
            "audit_tool_path",
            "audit_tool_sha256",
            "audit_command",
            "canonical_rom_sha256",
            "asset_count",
            "candidate_tile_count",
            "excluded_candidate_tile_count",
            "compared_candidate_tile_count",
            "reference_tile_count",
            "excluded_reference_tile_count",
            "compared_reference_tile_count",
            "pre_correction_exact_index_match_count",
            "pre_correction_visible_pattern_match_count",
            "affected_asset_id",
            "affected_candidate_tile_indices",
            "reference_pixels_displayed_or_exported",
            "correction",
            "post_correction_exact_index_match_count",
            "post_correction_visible_pattern_match_count",
            "npc_originality_claimed",
        },
        "playable-PC metadata correction",
    )
    expected_correction_values = {
        "audit_scope": AUDIT_SCOPE,
        "method": AUDIT_METHOD,
        "audit_tool_path": "tools/audit_schala_glass_focus_originality.py",
        "audit_tool_sha256": (
            "addbb63ce0d5c92972fc467bc7d0e92f6cab3015f792a9c8da90101c492d8ce7"
        ),
        "audit_command": AUDIT_COMMAND,
        "canonical_rom_sha256": (
            "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
        ),
        "asset_count": 12,
        "candidate_tile_count": 174,
        "excluded_candidate_tile_count": 80,
        "compared_candidate_tile_count": 94,
        "reference_tile_count": 7264,
        "excluded_reference_tile_count": 59,
        "compared_reference_tile_count": 7205,
        "pre_correction_exact_index_match_count": 0,
        "pre_correction_visible_pattern_match_count": 6,
        "affected_asset_id": "glass_focus_impact_arc_v0",
        "affected_candidate_tile_indices": [0, 2],
        "reference_pixels_displayed_or_exported": False,
        "correction": AUDIT_CORRECTION,
        "post_correction_exact_index_match_count": 0,
        "post_correction_visible_pattern_match_count": 0,
        "npc_originality_claimed": False,
    }
    for field, expected in expected_correction_values.items():
        if correction.get(field) != expected:
            raise FocusSourceError(
                f"playable-PC correction field drifted: {field}"
            )
    for field in (
        "asset_count",
        "candidate_tile_count",
        "excluded_candidate_tile_count",
        "compared_candidate_tile_count",
        "reference_tile_count",
        "excluded_reference_tile_count",
        "compared_reference_tile_count",
        "pre_correction_exact_index_match_count",
        "pre_correction_visible_pattern_match_count",
        "post_correction_exact_index_match_count",
        "post_correction_visible_pattern_match_count",
    ):
        if type(correction[field]) is not int:
            raise FocusSourceError(
                f"playable-PC correction count must be an integer: {field}"
            )
    if (
        not isinstance(correction["affected_candidate_tile_indices"], list)
        or any(
            type(value) is not int
            for value in correction["affected_candidate_tile_indices"]
        )
    ):
        raise FocusSourceError(
            "affected candidate tile indices must be integer metadata"
        )
    for field in (
        "reference_pixels_displayed_or_exported",
        "npc_originality_claimed",
    ):
        if correction[field] is not False:
            raise FocusSourceError(
                f"playable-PC correction flag must remain false: {field}"
            )


def _validate_palette_dependency(
    source: dict[str, Any], palette_bytes: bytes
) -> None:
    if "palette" in source:
        raise FocusSourceError("the existing gameplay palette may not be copied")
    dependency = source.get("palette_dependency")
    if not isinstance(dependency, dict):
        raise FocusSourceError("palette_dependency is required")
    _require_exact_keys(
        dependency,
        {
            "path",
            "sha256",
            "palette_id",
            "transparent_index",
            "allowed_indices",
            "focus_insert_indices",
            "embedded_palette_copy",
        },
        "palette_dependency",
    )
    expected = {
        "path": GAMEPLAY_REL.as_posix(),
        "sha256": EXPECTED_DEPENDENCY_HASHES[GAMEPLAY_REL.as_posix()],
        "palette_id": PALETTE_ID,
        "transparent_index": 0,
        "allowed_indices": list(range(16)),
        "focus_insert_indices": list(FOCUS_INSERT_INDICES),
        "embedded_palette_copy": False,
    }
    if dependency != expected:
        raise FocusSourceError("palette dependency contract drifted")
    if len(palette_bytes) != 0x20:
        raise FocusSourceError("gameplay palette did not encode to 0x20 bytes")


def _validate_frames(
    source: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], bytes, dict[str, int]]:
    raw_frames = source.get("frames")
    if not isinstance(raw_frames, list) or len(raw_frames) != 6:
        raise FocusSourceError("exactly six basic-attack frames are required")
    frames: dict[str, dict[str, Any]] = {}
    packed = bytearray()
    occupied: dict[str, int] = {}
    serialized: list[tuple[int, ...]] = []
    for index, frame in enumerate(raw_frames):
        if not isinstance(frame, dict):
            raise FocusSourceError("frame must be an object")
        _require_exact_keys(
            frame,
            {
                "id",
                "sequence_index",
                "context",
                "category",
                "phase",
                "direction",
                "width",
                "height",
                "indexed_color_mode",
                "palette_id",
                "focus_insert_id",
                "focus_center",
                "focus_insert_usage",
                "derivation",
                "composition",
                "rows",
            },
            "basic-attack frame",
        )
        frame_id, expected_phase = FRAME_PHASES[index]
        if frame.get("id") != frame_id:
            raise FocusSourceError("basic-attack frame order drifted")
        if (
            type(frame.get("sequence_index")) is not int
            or frame.get("sequence_index") != index
        ):
            raise FocusSourceError(f"{frame_id}: sequence index drifted")
        if (
            frame.get("context") != "battle_action"
            or frame.get("category") != "basic_attack"
            or frame.get("phase") != expected_phase
            or frame.get("direction") != "right"
        ):
            raise FocusSourceError(f"{frame_id}: action semantics drifted")
        if (
            frame.get("derivation")
            != "original-project-epoch-body-vocabulary-new-action-pose"
        ):
            raise FocusSourceError(f"{frame_id}: derivation drifted")
        if frame.get("composition") != FRAME_COMPOSITIONS[index]:
            raise FocusSourceError(f"{frame_id}: composition narrative drifted")
        if frame.get("focus_insert_id") != FRAME_INSERT_IDS[index]:
            raise FocusSourceError(f"{frame_id}: Focus insert mapping drifted")
        if (
            frame.get("focus_insert_usage")
            != "semantic-vocabulary-reference-not-composited"
        ):
            raise FocusSourceError(
                f"{frame_id}: Focus insert usage semantics drifted"
            )
        center = frame.get("focus_center")
        if (
            not isinstance(center, list)
            or len(center) != 2
            or any(type(value) is not int for value in center)
            or not all(0 <= value < 40 for value in center)
        ):
            raise FocusSourceError(
                f"{frame_id}: invalid logical Focus center"
            )
        width, height, pixels = _parse_pixels(frame, FRAME_DIMENSIONS)
        if not set(pixels).issubset(range(16)):
            raise FocusSourceError(f"{frame_id}: pixel outside gameplay palette")
        count = occupied_tile_count(pixels, width, height)
        if count > 16:
            raise FocusSourceError(
                f"{frame_id}: sixteen-cell source ceiling exceeded"
            )
        frame_bytes = encode_snes_4bpp(pixels, width, height)
        if decode_snes_4bpp(frame_bytes, width, height) != pixels:
            raise FocusSourceError(f"{frame_id}: 4bpp round trip failed")
        frames[frame_id] = frame
        occupied[frame_id] = count
        serialized.append(pixels)
        packed.extend(frame_bytes)
    if len(set(serialized)) != 6:
        raise FocusSourceError("basic-attack frames must be logically distinct")

    _, gameplay = load_json(ROOT / GAMEPLAY_REL)
    foundation_frames = gameplay.get("frames")
    if not isinstance(foundation_frames, list):
        raise FocusSourceError("gameplay dependency lacks frames")
    existing_battle = {
        _parse_pixels(frame, FRAME_DIMENSIONS)[2]
        for frame in foundation_frames
        if isinstance(frame, dict)
        and frame.get("context") == "battle_action"
    }
    if any(value in existing_battle for value in serialized):
        raise FocusSourceError(
            "dedicated basic-attack frame duplicates a foundation battle frame"
        )
    return frames, bytes(packed), occupied


def _validate_inserts(
    source: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], bytes, dict[str, int]]:
    raw_inserts = source.get("focus_inserts")
    if not isinstance(raw_inserts, list) or len(raw_inserts) != 6:
        raise FocusSourceError("exactly six Focus inserts are required")
    inserts: dict[str, dict[str, Any]] = {}
    packed = bytearray()
    occupied: dict[str, int] = {}
    serialized: list[tuple[int, ...]] = []
    for index, insert in enumerate(raw_inserts):
        if not isinstance(insert, dict):
            raise FocusSourceError("Focus insert must be an object")
        _require_exact_keys(
            insert,
            {
                "id",
                "vocabulary",
                "width",
                "height",
                "indexed_color_mode",
                "palette_id",
                "derivation",
                "rows",
            },
            "Focus insert",
        )
        insert_id, vocabulary = INSERT_VOCABULARY[index]
        if (
            insert.get("id") != insert_id
            or insert.get("vocabulary") != vocabulary
        ):
            raise FocusSourceError("Focus insert vocabulary order drifted")
        if insert.get("derivation") != "original-independent-target-grid":
            raise FocusSourceError(f"{insert_id}: derivation drifted")
        width, height, pixels = _parse_pixels(insert, INSERT_DIMENSIONS)
        if not set(pixels).issubset(FOCUS_INSERT_INDICES):
            raise FocusSourceError(
                f"{insert_id}: insert uses a non-Focus palette index"
            )
        if 13 not in pixels or 14 not in pixels:
            raise FocusSourceError(
                f"{insert_id}: Glass Focus needs both old-gold values"
            )
        count = occupied_tile_count(pixels, width, height)
        if count > 4:
            raise FocusSourceError(
                f"{insert_id}: four-cell Focus ceiling exceeded"
            )
        insert_bytes = encode_snes_4bpp(pixels, width, height)
        if decode_snes_4bpp(insert_bytes, width, height) != pixels:
            raise FocusSourceError(f"{insert_id}: 4bpp round trip failed")
        inserts[insert_id] = insert
        occupied[insert_id] = count
        serialized.append(pixels)
        packed.extend(insert_bytes)
        if insert_id == "glass_focus_impact_arc_v0":
            impact_tiles = tuple(iter_tiles(pixels, width, height))
            actual_counts = {
                tile_index: sum(pixel != 0 for pixel in impact_tiles[tile_index])
                for tile_index in IMPACT_ARC_CORRECTED_TILE_VISIBLE_COUNTS
            }
            if actual_counts != IMPACT_ARC_CORRECTED_TILE_VISIBLE_COUNTS:
                raise FocusSourceError(
                    "impact-arc metadata-corrected cell geometry drifted"
                )
    if len(set(serialized)) != 6:
        raise FocusSourceError("Focus inserts must be logically distinct")
    return inserts, bytes(packed), occupied


def _validate_audio_recipe(
    recipe: dict[str, Any],
    expected_id: str,
    expected_role: str,
    expected_trigger: str,
) -> None:
    _require_exact_keys(
        recipe,
        {
            "id",
            "role",
            "source_classification",
            "sample_rate_hz",
            "duration_samples",
            "trigger",
            "oscillators",
            "noise",
            "amplitude_envelope",
            "mix_normalization_q15",
            "native_sfx_id",
            "runtime_pointer",
            "rendered_audio_path",
        },
        expected_id,
    )
    if (
        recipe.get("id") != expected_id
        or recipe.get("role") != expected_role
        or recipe.get("source_classification")
        != "project-epoch-original-parametric-audio"
    ):
        raise FocusSourceError(f"{expected_id}: audio identity drifted")
    sample_rate = _require_int(
        recipe.get("sample_rate_hz"),
        f"{expected_id}.sample_rate_hz",
        8000,
        96000,
    )
    if sample_rate != 32000:
        raise FocusSourceError(f"{expected_id}: sample rate drifted")
    duration = _require_int(
        recipe.get("duration_samples"),
        f"{expected_id}.duration_samples",
        1,
        sample_rate,
    )
    trigger = recipe.get("trigger")
    if not isinstance(trigger, dict):
        raise FocusSourceError(f"{expected_id}: trigger must be an object")
    _require_exact_keys(trigger, {"frame_id", "sample_offset"}, "trigger")
    if (
        trigger.get("frame_id") != expected_trigger
        or trigger.get("sample_offset") != 0
    ):
        raise FocusSourceError(f"{expected_id}: trigger drifted")

    oscillators = recipe.get("oscillators")
    if not isinstance(oscillators, list) or len(oscillators) != 2:
        raise FocusSourceError(
            f"{expected_id}: exactly two oscillators are required"
        )
    for oscillator_index, oscillator in enumerate(oscillators):
        if not isinstance(oscillator, dict):
            raise FocusSourceError(f"{expected_id}: invalid oscillator")
        _require_exact_keys(
            oscillator,
            {
                "waveform",
                "start_frequency_millihz",
                "end_frequency_millihz",
                "amplitude_q15",
                "phase_q16",
            },
            f"{expected_id}.oscillator[{oscillator_index}]",
        )
        if oscillator.get("waveform") not in {"sine", "triangle"}:
            raise FocusSourceError(f"{expected_id}: unsupported waveform")
        _require_int(
            oscillator.get("start_frequency_millihz"),
            "start_frequency_millihz",
            1000,
            sample_rate * 500,
        )
        _require_int(
            oscillator.get("end_frequency_millihz"),
            "end_frequency_millihz",
            1000,
            sample_rate * 500,
        )
        _require_int(
            oscillator.get("amplitude_q15"),
            "amplitude_q15",
            0,
            32767,
        )
        _require_int(
            oscillator.get("phase_q16"), "phase_q16", 0, 65535
        )

    noise = recipe.get("noise")
    if not isinstance(noise, dict):
        raise FocusSourceError(f"{expected_id}: noise must be an object")
    _require_exact_keys(
        noise,
        {"generator", "seed", "amplitude_q15", "lowpass_hz"},
        f"{expected_id}.noise",
    )
    if noise.get("generator") != "xorshift32":
        raise FocusSourceError(f"{expected_id}: noise generator drifted")
    _require_int(noise.get("seed"), "noise.seed", 1, 0xFFFFFFFF)
    _require_int(
        noise.get("amplitude_q15"), "noise.amplitude_q15", 0, 32767
    )
    _require_int(
        noise.get("lowpass_hz"), "noise.lowpass_hz", 1, sample_rate // 2
    )

    envelope = recipe.get("amplitude_envelope")
    if not isinstance(envelope, list) or len(envelope) < 4:
        raise FocusSourceError(f"{expected_id}: envelope is incomplete")
    samples: list[int] = []
    values: list[int] = []
    for point_index, point in enumerate(envelope):
        if not isinstance(point, dict):
            raise FocusSourceError(f"{expected_id}: invalid envelope point")
        _require_exact_keys(
            point, {"sample", "value_q15"}, "amplitude envelope point"
        )
        samples.append(
            _require_int(
                point.get("sample"),
                f"envelope[{point_index}].sample",
                0,
                duration - 1,
            )
        )
        values.append(
            _require_int(
                point.get("value_q15"),
                f"envelope[{point_index}].value_q15",
                0,
                32767,
            )
        )
    if samples[0] != 0 or samples[-1] != duration - 1:
        raise FocusSourceError(f"{expected_id}: envelope endpoints drifted")
    if values[0] != 0 or values[-1] != 0 or max(values[1:-1]) == 0:
        raise FocusSourceError(f"{expected_id}: envelope shape is invalid")
    if any(right <= left for left, right in zip(samples, samples[1:])):
        raise FocusSourceError(
            f"{expected_id}: envelope samples must increase"
        )
    _require_int(
        recipe.get("mix_normalization_q15"),
        f"{expected_id}.mix_normalization_q15",
        1,
        32767,
    )
    for field in (
        "native_sfx_id",
        "runtime_pointer",
        "rendered_audio_path",
    ):
        if recipe.get(field) is not None:
            raise FocusSourceError(
                f"{expected_id}: {field} must remain null"
            )


def _validate_audio(
    source: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], bytes]:
    recipes = source.get("audio_recipes")
    if not isinstance(recipes, list) or len(recipes) != 2:
        raise FocusSourceError("exactly two audio recipes are required")
    expected = (
        (
            "focus_swing_v0",
            "swing",
            "schala_battle_basic_attack_open_f01_v0",
        ),
        (
            "focus_hit_v0",
            "hit",
            "schala_battle_basic_attack_followthrough_f03_v0",
        ),
    )
    for recipe, (recipe_id, role, trigger) in zip(recipes, expected):
        if not isinstance(recipe, dict):
            raise FocusSourceError("audio recipe must be an object")
        _validate_audio_recipe(recipe, recipe_id, role, trigger)
    for _, value in _walk(recipes):
        if isinstance(value, (bytes, bytearray)):
            raise FocusSourceError("binary audio data is forbidden")
        if isinstance(value, str) and value.lower().endswith(
            AUDIO_FILE_SUFFIXES
        ):
            raise FocusSourceError("rendered or encoded audio path is forbidden")
    return tuple(recipes), canonical_json_bytes(recipes)


def validate_source(
    source: dict[str, Any],
) -> dict[str, Any]:
    _require_exact_keys(
        source,
        {
            "schema_version",
            "asset_set",
            "status",
            "created",
            "author",
            "source_classification",
            "rom_integration",
            "rom_installable",
            "scope_statement",
            "binding_identity",
            "native_runtime_bindings",
            "provenance",
            "palette_dependency",
            "references",
            "frames",
            "focus_inserts",
            "audio_recipes",
        },
        "Glass Focus source",
    )
    if type(source.get("schema_version")) is not int:
        raise FocusSourceError("source schema version must be an integer")
    if source.get("schema_version") != 1:
        raise FocusSourceError("unsupported source schema")
    if source.get("asset_set") != (
        "project_epoch_schala_glass_focus_pulse_v0"
    ):
        raise FocusSourceError("asset-set identity drifted")
    if source.get("status") != "source-only-vertical-slice-unbound":
        raise FocusSourceError("source status drifted")
    if source.get("created") != SOURCE_CREATED:
        raise FocusSourceError("source creation date drifted")
    if source.get("author") != SOURCE_AUTHOR:
        raise FocusSourceError("source author drifted")
    if source.get("scope_statement") != SOURCE_SCOPE_STATEMENT:
        raise FocusSourceError("source scope narrative drifted")
    if source.get("rom_integration") is not False:
        raise FocusSourceError("source may not claim ROM integration")
    if source.get("rom_installable") is not False:
        raise FocusSourceError("source may not claim ROM installability")

    item_source, tech_source, palette_bytes = _validate_dependencies(source)
    _validate_binding_identity(source, item_source, tech_source)
    _validate_provenance(source)
    _validate_palette_dependency(source, palette_bytes)
    frames, frame_bytes, frame_occupied = _validate_frames(source)
    inserts, insert_bytes, insert_occupied = _validate_inserts(source)
    recipes, audio_recipe_bytes = _validate_audio(source)

    if set(frame.get("focus_insert_id") for frame in frames.values()) != set(
        inserts
    ):
        raise FocusSourceError("every Focus insert must appear once in sequence")
    return {
        "palette_bytes": palette_bytes,
        "frames": frames,
        "frame_bytes": frame_bytes,
        "frame_occupied": frame_occupied,
        "inserts": inserts,
        "insert_bytes": insert_bytes,
        "insert_occupied": insert_occupied,
        "audio_recipes": recipes,
        "audio_recipe_bytes": audio_recipe_bytes,
    }


def validation_report(
    source_raw: bytes, source: dict[str, Any]
) -> dict[str, Any]:
    validated = validate_source(source)
    palette_bytes = validated["palette_bytes"]
    frame_bytes = validated["frame_bytes"]
    insert_bytes = validated["insert_bytes"]
    audio_recipe_bytes = validated["audio_recipe_bytes"]
    return {
        "schema": "project-epoch-schala-glass-focus-validation-v1",
        "validator_version": VALIDATOR_VERSION,
        "canonical_source": {
            "path": SOURCE_REL.as_posix(),
            "sha256": sha256(source_raw),
            "size": len(source_raw),
        },
        "identity": {
            "logical_pc_id": 7,
            "action_id": 0x90,
            "item_id": 0xE8,
            "focus_visual_id": 0,
            "binding_state": "unbound",
        },
        "palette": {
            "id": PALETTE_ID,
            "dependency_path": GAMEPLAY_REL.as_posix(),
            "packed_bgr555_sha256": sha256(palette_bytes),
            "packed_bgr555_size": len(palette_bytes),
            "embedded_copy": False,
        },
        "frames": {
            "ids": list(FRAME_IDS),
            "count": len(FRAME_IDS),
            "dimensions": list(FRAME_DIMENSIONS),
            "validation_4bpp_sha256": sha256(frame_bytes),
            "validation_4bpp_size": len(frame_bytes),
            "occupied_tiles": validated["frame_occupied"],
            "assembly_packability_claimed": False,
        },
        "focus_inserts": {
            "ids": list(INSERT_IDS),
            "count": len(INSERT_IDS),
            "dimensions": list(INSERT_DIMENSIONS),
            "validation_4bpp_sha256": sha256(insert_bytes),
            "validation_4bpp_size": len(insert_bytes),
            "occupied_tiles": validated["insert_occupied"],
        },
        "audio_recipes": {
            "ids": list(AUDIO_IDS),
            "count": len(AUDIO_IDS),
            "canonical_sha256": sha256(audio_recipe_bytes),
            "canonical_size": len(audio_recipe_bytes),
            "rendered_audio_emitted": False,
            "native_sfx_ids_bound": False,
        },
        "provenance": {
            "validator_rom_accessed": False,
            "rom_or_npc_pixels_imported": False,
            "sampled_or_extracted_audio_imported": False,
            "recorded_playable_pc_metadata_correction": {
                "originality_auditor_rom_accessed": True,
                "originality_auditor_path": (
                    "tools/audit_schala_glass_focus_originality.py"
                ),
                "asset_count": 12,
                "candidate_tile_count": 174,
                "excluded_candidate_tile_count": 80,
                "compared_candidate_tile_count": 94,
                "reference_tile_count": 7264,
                "excluded_reference_tile_count": 59,
                "compared_reference_tile_count": 7205,
                "pre_correction_visible_pattern_match_count": 6,
                "post_correction_exact_index_match_count": 0,
                "post_correction_visible_pattern_match_count": 0,
                "reference_pixels_displayed_or_exported": False,
                "npc_originality_claimed": False,
            },
        },
        "allocation_status": "unbound",
        "rom_installable": False,
        "binary_files_emitted": False,
        "runtime_use_policy": "reject-before-any-native-or-wram-write",
        "evidence_scope": (
            "source structure, provenance declarations, palette dependency, "
            "identity cross-checks, indexed-pixel packing, and deterministic "
            "audio recipe serialization only"
        ),
    }


def manifest_expectation(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "identity": report["identity"],
        "palette": report["palette"],
        "frames": report["frames"],
        "focus_inserts": report["focus_inserts"],
        "audio_recipes": report["audio_recipes"],
        "allocation_status": report["allocation_status"],
        "rom_installable": report["rom_installable"],
        "binary_files_emitted": report["binary_files_emitted"],
        "runtime_use_policy": report["runtime_use_policy"],
    }


def verify_manifest_core(
    manifest: dict[str, Any],
    source_raw: bytes,
    report: dict[str, Any],
) -> None:
    _require_exact_keys(
        manifest,
        {
            "schema_version",
            "asset_set",
            "status",
            "created",
            "modified",
            "author",
            "review_status",
            "provenance_statement",
            "canonical_source",
            "validator",
            "dependencies",
            "originality_audit",
            "expected_validation",
            "generated_artifact_policy",
            "evidence",
        },
        "Glass Focus manifest",
    )
    if type(manifest.get("schema_version")) is not int:
        raise FocusSourceError("manifest schema version must be an integer")
    if manifest.get("schema_version") != 1:
        raise FocusSourceError("unsupported manifest schema")
    if manifest.get("asset_set") != (
        "project_epoch_schala_glass_focus_pulse_v0"
    ):
        raise FocusSourceError("manifest asset-set identity drifted")
    if manifest.get("status") != "source-only-vertical-slice-unbound":
        raise FocusSourceError("manifest status drifted")
    expected_narrative = {
        "created": MANIFEST_CREATED,
        "modified": MANIFEST_MODIFIED,
        "author": MANIFEST_AUTHOR,
        "review_status": MANIFEST_REVIEW_STATUS,
        "provenance_statement": MANIFEST_PROVENANCE_STATEMENT,
    }
    for field, expected in expected_narrative.items():
        if manifest.get(field) != expected:
            raise FocusSourceError(f"manifest {field} drifted")
    canonical = manifest.get("canonical_source")
    if not isinstance(canonical, dict):
        raise FocusSourceError("manifest canonical_source is required")
    _require_exact_keys(
        canonical,
        {"path", "sha256", "size", "source_classification"},
        "manifest canonical_source",
    )
    expected_canonical = {
        "path": SOURCE_REL.as_posix(),
        "sha256": sha256(source_raw),
        "size": len(source_raw),
        "source_classification": (
            "project-epoch-original-same-project-derived-multimedia-source"
        ),
    }
    if canonical != expected_canonical:
        raise FocusSourceError("manifest canonical source drifted")
    validator = manifest.get("validator")
    if not isinstance(validator, dict):
        raise FocusSourceError("manifest validator is required")
    _require_exact_keys(
        validator,
        {"path", "sha256", "size", "version", "command"},
        "manifest validator",
    )
    validator_path = pathlib.Path(__file__)
    expected_validator = {
        "path": "tools/validate_schala_glass_focus_pulse_v0.py",
        "sha256": sha256(validator_path.read_bytes()),
        "size": validator_path.stat().st_size,
        "version": VALIDATOR_VERSION,
        "command": (
            "python tools/validate_schala_glass_focus_pulse_v0.py"
        ),
    }
    if validator != expected_validator:
        raise FocusSourceError("manifest validator identity drifted")
    dependencies = manifest.get("dependencies")
    expected_dependencies = [
        {"path": path, "sha256": digest}
        for path, digest in EXPECTED_DEPENDENCY_HASHES.items()
    ]
    if dependencies != expected_dependencies:
        raise FocusSourceError("manifest dependency set drifted")
    if not isinstance(dependencies, list) or any(
        not isinstance(value, dict)
        or set(value) != {"path", "sha256"}
        for value in dependencies
    ):
        raise FocusSourceError("manifest dependency record shape drifted")
    originality = manifest.get("originality_audit")
    expected_originality = {
        "path": ORIGINALITY_REPORT_REL.as_posix(),
        "sha256": ORIGINALITY_REPORT_SHA256,
        "size": ORIGINALITY_REPORT_SIZE,
        "dependency_scope": "validation-only",
        "reproduction": AUDIT_COMMAND,
        "npc_originality_claimed": False,
    }
    if originality != expected_originality:
        raise FocusSourceError("manifest originality audit pin drifted")
    if manifest.get("expected_validation") != manifest_expectation(report):
        raise FocusSourceError("manifest validation evidence drifted")
    artifact_policy = manifest.get("generated_artifact_policy")
    if artifact_policy != {
        "output_directory": None,
        "binary_files_emitted": False,
        "rendered_visuals_emitted": False,
        "rendered_audio_emitted": False,
        "rom_or_patch_emitted": False,
    }:
        raise FocusSourceError("manifest artifact policy drifted")
    evidence = manifest.get("evidence")
    if evidence != {
        "source_validation": "verified-static",
        "visual_design": "proposal",
        "audio_design": "proposal",
        "rom_integration": "not performed",
        "runtime_rendering": "not performed",
        "runtime_audio": "not performed",
    }:
        raise FocusSourceError("manifest evidence labels drifted")


def verify_originality_report_file() -> None:
    originality_path = ROOT / ORIGINALITY_REPORT_REL
    originality_raw = originality_path.read_bytes()
    if (
        len(originality_raw) != ORIGINALITY_REPORT_SIZE
        or sha256(originality_raw) != ORIGINALITY_REPORT_SHA256
    ):
        raise FocusSourceError("originality report file drifted")


def verify_manifest(
    manifest: dict[str, Any],
    source_raw: bytes,
    report: dict[str, Any],
) -> None:
    verify_manifest_core(manifest, source_raw, report)
    verify_originality_report_file()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST
    )
    parser.add_argument(
        "--skip-manifest-verification",
        action="store_true",
        help="Validate an intentionally edited source before repinning.",
    )
    args = parser.parse_args()

    source_raw, source = load_json(args.source)
    report = validation_report(source_raw, source)
    if not args.skip_manifest_verification:
        _, manifest = load_json(args.manifest)
        verify_manifest(manifest, source_raw, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
