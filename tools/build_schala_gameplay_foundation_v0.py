#!/usr/bin/env python3
"""Build the original Project Epoch Schala gameplay-sprite foundation.

The canonical art is textual, target-grid palette-index data. This builder
does not read a ROM, save, emulator state, extracted tile, portrait, or concept
bitmap. It validates the clean-room source, packs SNES 4bpp tiles and a BGR555
palette, decodes those packed bytes, and writes deterministic private QA PNGs.

This is a partial animation foundation. It does not build an assembly packet,
allocate ROM space, or integrate logical PC $07.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from PIL import Image


BUILDER_VERSION = "1.0.0"
ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "gameplay"
    / "schala_gameplay_foundation_v0.json"
)
DEFAULT_MANIFEST = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "gameplay"
    / "manifest_v0.json"
)

FIELD_FRAME_IDS = (
    "schala_field_idle_down_f00_v0",
    "schala_field_idle_up_f00_v0",
    "schala_field_idle_left_f00_v0",
    "schala_field_idle_right_f00_v0",
    "schala_field_walk_down_f00_v0",
    "schala_field_walk_down_f01_v0",
    "schala_field_walk_down_f02_v0",
)
BATTLE_FRAME_IDS = (
    "schala_battle_ready_f00_v0",
    "schala_battle_cast_gather_f00_v0",
    "schala_battle_cast_release_f00_v0",
)
REQUIRED_FRAME_IDS = FIELD_FRAME_IDS + BATTLE_FRAME_IDS

FIELD_DIMENSIONS = (24, 32)
BATTLE_DIMENSIONS = (40, 40)
PALETTE_FILENAME = "schala_gameplay_palette_v0.bin"
SHEET_FILENAME = "schala_gameplay_foundation_sheet_4x_v0.png"
BUILD_MANIFEST_FILENAME = "schala_gameplay_build_manifest_v0.json"
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
INDEX_ROW = re.compile(r"^[0-9A-F]{8}( [0-9A-F]{8})+$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: pathlib.Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path}: top level must be an object")
    return raw, parsed


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    if not HEX_COLOR.fullmatch(value):
        raise ValueError(f"invalid RGB color: {value!r}")
    return tuple(
        int(value[index : index + 2], 16) for index in (1, 3, 5)
    )  # type: ignore[return-value]


def palette_rgb(source: dict[str, Any]) -> list[tuple[int, int, int]]:
    palette = source.get("palette")
    if not isinstance(palette, dict):
        raise ValueError("palette must be an object")
    if palette.get("id") != "schala_gameplay_palette_v0":
        raise ValueError("unexpected gameplay palette ID")
    if palette.get("transparent_index") != 0:
        raise ValueError("palette index 0 must be transparent")
    entries = palette.get("entries")
    if not isinstance(entries, list) or len(entries) != 16:
        raise ValueError("gameplay palette must contain exactly 16 entries")
    colors: list[tuple[int, int, int]] = []
    for expected_index, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("index") != expected_index:
            raise ValueError("palette indices must be ordered 0 through 15")
        colors.append(_hex_to_rgb(entry.get("hex", "")))
    return colors


def frame_pixels(frame: dict[str, Any]) -> tuple[int, int, tuple[int, ...]]:
    frame_id = frame.get("id")
    if frame_id not in REQUIRED_FRAME_IDS:
        raise ValueError(f"unexpected gameplay frame ID: {frame_id!r}")
    context = frame.get("context")
    expected_dimensions = (
        FIELD_DIMENSIONS
        if context == "field_locomotion"
        else BATTLE_DIMENSIONS
        if context == "battle_action"
        else None
    )
    if expected_dimensions is None:
        raise ValueError(f"{frame_id}: invalid context")
    width = frame.get("width")
    height = frame.get("height")
    if (width, height) != expected_dimensions:
        raise ValueError(
            f"{frame_id}: expected {expected_dimensions[0]}x"
            f"{expected_dimensions[1]}, got {width}x{height}"
        )
    if width % 8 or height % 8:
        raise ValueError(f"{frame_id}: dimensions must be multiples of 8")
    if frame.get("indexed_color_mode") != "4bpp-index-cell-rows":
        raise ValueError(f"{frame_id}: source is not declared indexed 4bpp")
    if frame.get("derivation") != "original-independent-target-grid":
        raise ValueError(f"{frame_id}: original derivation is not declared")
    if frame.get("palette_id") != "schala_gameplay_palette_v0":
        raise ValueError(f"{frame_id}: unexpected palette")
    rows = frame.get("rows")
    if not isinstance(rows, list) or len(rows) != height:
        raise ValueError(f"{frame_id}: row count does not match height")
    pixels: list[int] = []
    expected_cells = width // 8
    for row_number, row in enumerate(rows):
        if not isinstance(row, str) or not INDEX_ROW.fullmatch(row):
            raise ValueError(
                f"{frame_id}: row {row_number} must contain uppercase "
                "8-pixel hexadecimal cells"
            )
        cells = row.split(" ")
        if len(cells) != expected_cells:
            raise ValueError(
                f"{frame_id}: row {row_number} has {len(cells)} cells, "
                f"expected {expected_cells}"
            )
        pixels.extend(int(character, 16) for character in "".join(cells))
    return width, height, tuple(pixels)


def iter_tiles(
    pixels: Sequence[int], width: int, height: int
) -> Iterable[tuple[int, ...]]:
    if len(pixels) != width * height:
        raise ValueError("pixel count does not match dimensions")
    if width % 8 or height % 8:
        raise ValueError("tile iteration requires multiples of 8")
    for tile_y in range(0, height, 8):
        for tile_x in range(0, width, 8):
            yield tuple(
                pixels[(tile_y + y) * width + tile_x + x]
                for y in range(8)
                for x in range(8)
            )


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
                    raise ValueError("4bpp pixel index outside 0 through 15")
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
        raise ValueError("packed 4bpp size does not match dimensions")
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


def encode_snes_palette(colors: Sequence[tuple[int, int, int]]) -> bytes:
    if len(colors) != 16:
        raise ValueError("SNES gameplay palette must contain 16 colors")
    packed = bytearray()
    for red, green, blue in colors:
        if any(not 0 <= channel <= 255 for channel in (red, green, blue)):
            raise ValueError("RGB channel outside 0 through 255")
        bgr555 = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
        packed.extend(bgr555.to_bytes(2, "little"))
    return bytes(packed)


def decode_snes_palette(packed: bytes) -> list[tuple[int, int, int]]:
    if len(packed) != 0x20:
        raise ValueError("SNES gameplay palette must be 0x20 bytes")
    colors = []
    for offset in range(0, len(packed), 2):
        value = int.from_bytes(packed[offset : offset + 2], "little")
        channels_5bit = (
            value & 0x1F,
            (value >> 5) & 0x1F,
            (value >> 10) & 0x1F,
        )
        colors.append(
            tuple((channel << 3) | (channel >> 2) for channel in channels_5bit)
        )
    return colors  # type: ignore[return-value]


def render_packed_png(
    packed: bytes,
    palette_bytes: bytes,
    width: int,
    height: int,
) -> bytes:
    pixels = decode_snes_4bpp(packed, width, height)
    colors = decode_snes_palette(palette_bytes)
    image = Image.new("P", (width, height))
    image.putdata(pixels)
    flattened = [
        channel for color in colors for channel in color
    ] + [0, 0, 0] * (256 - len(colors))
    image.putpalette(flattened)
    output = io.BytesIO()
    image.save(
        output,
        format="PNG",
        transparency=0,
        optimize=False,
        compress_level=9,
    )
    return output.getvalue()


def tile_variants(tile: Sequence[int]) -> set[tuple[int, ...]]:
    if len(tile) != 64:
        raise ValueError("tile must contain 64 pixels")

    def at(x: int, y: int) -> int:
        return tile[y * 8 + x]

    return {
        tuple(at(x, y) for y in range(8) for x in range(8)),
        tuple(at(7 - x, y) for y in range(8) for x in range(8)),
        tuple(at(x, 7 - y) for y in range(8) for x in range(8)),
        tuple(at(7 - x, 7 - y) for y in range(8) for x in range(8)),
    }


def canonical_tile(tile: Sequence[int]) -> tuple[int, ...]:
    return min(tile_variants(tile))


def occupied_tile_count(
    pixels: Sequence[int], width: int, height: int
) -> int:
    return sum(any(tile) for tile in iter_tiles(pixels, width, height))


def tile_sharing_audit(
    frames: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Classify exact/flip tile sharing under the declared context policy.

    Sharing non-trivial body vocabulary inside field locomotion or inside
    battle action is intentional. Any non-trivial exact tile relationship
    across those two contexts is prohibited: a field body tile must not be
    dropped into the larger battle vocabulary.
    """

    occurrences: dict[
        tuple[int, ...], list[dict[str, Any]]
    ] = defaultdict(list)
    trivial_count = 0
    for frame_id, frame in frames.items():
        width, height, pixels = frame_pixels(frame)
        for tile_index, tile in enumerate(iter_tiles(pixels, width, height)):
            nontransparent = sum(pixel != 0 for pixel in tile)
            if nontransparent <= 2:
                trivial_count += 1
                continue
            occurrences[canonical_tile(tile)].append(
                {
                    "frame_id": frame_id,
                    "context": frame["context"],
                    "tile_index": tile_index,
                    "nontransparent_pixels": nontransparent,
                }
            )

    prohibited = []
    permitted = []
    for group in occurrences.values():
        frame_ids = {item["frame_id"] for item in group}
        if len(frame_ids) < 2:
            continue
        contexts = {item["context"] for item in group}
        record = {
            "contexts": sorted(contexts),
            "occurrences": sorted(
                group, key=lambda item: (item["frame_id"], item["tile_index"])
            ),
        }
        if len(contexts) > 1:
            prohibited.append(record)
        else:
            permitted.append(record)
    return {
        "comparison": "exact-index tiles including H/V/HV flips",
        "trivial_threshold": 2,
        "trivial_tile_occurrences": trivial_count,
        "permitted_same_context_groups": permitted,
        "prohibited_cross_context_groups": prohibited,
    }


def tile_budget_report(
    frames: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    by_context: dict[str, set[tuple[int, ...]]] = defaultdict(set)
    occupied_by_frame: dict[str, int] = {}
    all_unique: set[tuple[int, ...]] = set()
    for frame_id, frame in frames.items():
        width, height, pixels = frame_pixels(frame)
        occupied = occupied_tile_count(pixels, width, height)
        occupied_by_frame[frame_id] = occupied
        for tile in iter_tiles(pixels, width, height):
            if not any(tile):
                continue
            tile_key = tuple(tile)
            by_context[frame["context"]].add(tile_key)
            all_unique.add(tile_key)
    return {
        "occupied_tiles_by_frame": occupied_by_frame,
        "unique_nontransparent_tiles_by_context": {
            context: len(tiles) for context, tiles in sorted(by_context.items())
        },
        "unique_nontransparent_tiles_total": len(all_unique),
        "gameplay_total_ceiling": 352,
    }


def validate_source(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if source.get("schema_version") != 1:
        raise ValueError("unsupported gameplay source schema")
    if source.get("status") != "partial-animation-foundation":
        raise ValueError("source must declare partial-animation-foundation")
    if (
        source.get("source_classification")
        != "original-hand-pixelled-target-grid"
    ):
        raise ValueError("source must be clean-room target-grid pixel data")
    if source.get("rom_integration") is not False:
        raise ValueError("foundation must not claim ROM integration")

    authorship = source.get("pixel_authorship")
    if not isinstance(authorship, dict):
        raise ValueError("pixel_authorship object is required")
    prohibited_flags = (
        "imported_layers",
        "imported_pixels",
        "rom_or_extracted_tile_input",
        "concept_bitmap_input",
        "concept_pixels_sampled",
        "concept_palette_sampled",
        "automatic_resizing",
    )
    if any(authorship.get(flag) is not False for flag in prohibited_flags):
        raise ValueError("source declares prohibited imported/derived input")

    palette_rgb(source)
    references = source.get("references")
    if not isinstance(references, list):
        raise ValueError("references must be an array")
    concepts = [
        reference
        for reference in references
        if isinstance(reference, dict)
        and reference.get("source_classification")
        == "generated-concept-reference"
    ]
    if len(concepts) != 2:
        raise ValueError("both generated concept references must be recorded")
    for concept in concepts:
        if (
            concept.get("rom_eligible") is not False
            or concept.get("pixels_or_palette_sampled") is not False
            or concept.get("opened_by_pixel_author") is not False
        ):
            raise ValueError(
                "concept references must remain unopened and non-ROM-eligible"
            )

    raw_frames = source.get("frames")
    if not isinstance(raw_frames, list) or len(raw_frames) != 10:
        raise ValueError("exactly ten foundation frames are required")
    frames: dict[str, dict[str, Any]] = {}
    for frame in raw_frames:
        if not isinstance(frame, dict):
            raise ValueError("gameplay frame must be an object")
        frame_id = frame.get("id")
        if not isinstance(frame_id, str) or frame_id in frames:
            raise ValueError("frame IDs must be unique strings")
        _, _, pixels = frame_pixels(frame)
        if not any(pixels):
            raise ValueError(f"{frame_id}: frame is fully transparent")
        frames[frame_id] = frame
    if set(frames) != set(REQUIRED_FRAME_IDS):
        raise ValueError("required foundation frame set is incomplete")

    walk_frames = [
        frames[f"schala_field_walk_down_f0{index}_v0"]
        for index in range(3)
    ]
    if [frame.get("cycle_index") for frame in walk_frames] != [0, 1, 2]:
        raise ValueError("downward walk cycle indices must be 0, 1, 2")
    if any(
        15 in frame_pixels(frames[frame_id])[2]
        for frame_id in FIELD_FRAME_IDS
    ):
        raise ValueError("field locomotion frames must not contain magic focus")
    if 15 in frame_pixels(frames["schala_battle_ready_f00_v0"])[2]:
        raise ValueError("battle ready frame must not contain magic focus")
    for frame_id in BATTLE_FRAME_IDS[1:]:
        if 15 not in frame_pixels(frames[frame_id])[2]:
            raise ValueError(f"{frame_id}: cast key lacks rose-violet focus")

    serialized_frames = {
        frame_id: frame_pixels(frame)[2] for frame_id, frame in frames.items()
    }
    if len(set(serialized_frames.values())) != len(serialized_frames):
        raise ValueError("foundation contains an identical logical frame")

    budgets = tile_budget_report(frames)
    for frame_id in FIELD_FRAME_IDS:
        if budgets["occupied_tiles_by_frame"][frame_id] > 12:
            raise ValueError(f"{frame_id}: field cell budget exceeded")
    if budgets["occupied_tiles_by_frame"][BATTLE_FRAME_IDS[0]] > 16:
        raise ValueError("battle ready cell budget exceeded")
    for frame_id in BATTLE_FRAME_IDS[1:]:
        if budgets["occupied_tiles_by_frame"][frame_id] > 20:
            raise ValueError(f"{frame_id}: extended battle cell budget exceeded")
    if budgets["unique_nontransparent_tiles_total"] > 352:
        raise ValueError("gameplay unique-tile ceiling exceeded")

    sharing = tile_sharing_audit(frames)
    if sharing["prohibited_cross_context_groups"]:
        raise ValueError(
            "field and battle contexts share a non-trivial exact/flip tile"
        )
    return frames


def _indexed_image(
    pixels: Sequence[int],
    width: int,
    height: int,
    colors: Sequence[tuple[int, int, int]],
) -> Image.Image:
    image = Image.new("P", (width, height))
    image.putdata(pixels)
    flattened = [
        channel for color in colors for channel in color
    ] + [0, 0, 0] * (256 - len(colors))
    image.putpalette(flattened)
    image.info["transparency"] = 0
    return image


def render_contact_sheet(
    packed_frames: dict[str, tuple[bytes, int, int]],
    palette_bytes: bytes,
) -> bytes:
    colors = decode_snes_palette(palette_bytes)
    cell_width = 40
    cell_height = 40
    columns = 5
    rows = 2
    sheet = Image.new("P", (columns * cell_width, rows * cell_height), 0)
    flattened = [
        channel for color in colors for channel in color
    ] + [0, 0, 0] * (256 - len(colors))
    sheet.putpalette(flattened)
    sheet.info["transparency"] = 0
    for index, frame_id in enumerate(REQUIRED_FRAME_IDS):
        packed, width, height = packed_frames[frame_id]
        pixels = decode_snes_4bpp(packed, width, height)
        frame_image = _indexed_image(pixels, width, height, colors)
        x = (index % columns) * cell_width + (cell_width - width) // 2
        y = (index // columns) * cell_height + (cell_height - height) // 2
        sheet.paste(frame_image, (x, y))
    sheet = sheet.resize(
        (sheet.width * 4, sheet.height * 4),
        resample=Image.Resampling.NEAREST,
    )
    output = io.BytesIO()
    sheet.save(
        output,
        format="PNG",
        transparency=0,
        optimize=False,
        compress_level=9,
    )
    return output.getvalue()


def build_outputs(
    source_raw: bytes, source: dict[str, Any]
) -> dict[str, bytes]:
    frames = validate_source(source)
    palette_bytes = encode_snes_palette(palette_rgb(source))
    outputs: dict[str, bytes] = {PALETTE_FILENAME: palette_bytes}
    packed_frames: dict[str, tuple[bytes, int, int]] = {}
    for frame_id in REQUIRED_FRAME_IDS:
        width, height, pixels = frame_pixels(frames[frame_id])
        packed = encode_snes_4bpp(pixels, width, height)
        if decode_snes_4bpp(packed, width, height) != pixels:
            raise AssertionError(f"{frame_id}: 4bpp round-trip failed")
        packed_frames[frame_id] = (packed, width, height)
        outputs[f"{frame_id}.4bpp"] = packed
        outputs[f"{frame_id}.png"] = render_packed_png(
            packed, palette_bytes, width, height
        )
    outputs[SHEET_FILENAME] = render_contact_sheet(
        packed_frames, palette_bytes
    )

    manifest = {
        "schema_version": 1,
        "builder": {
            "path": "tools/build_schala_gameplay_foundation_v0.py",
            "version": BUILDER_VERSION,
            "command": (
                "python tools/build_schala_gameplay_foundation_v0.py "
                "--output-dir private/build/"
                "schala_gameplay_foundation_v0"
            ),
        },
        "canonical_source": {
            "path": (
                "assets/source/schala/v0/gameplay/"
                "schala_gameplay_foundation_v0.json"
            ),
            "sha256": sha256(source_raw),
            "source_classification": "original-hand-pixelled-target-grid",
        },
        "status": "partial-animation-foundation",
        "evidence": "verified-static",
        "rom_integration": False,
        "assembly_packet": False,
        "packed_from_source_then_decoded_for_png": True,
        "tile_budget": tile_budget_report(frames),
        "tile_sharing_audit": tile_sharing_audit(frames),
        "outputs": {
            filename: {"sha256": sha256(data), "size": len(data)}
            for filename, data in sorted(outputs.items())
        },
    }
    outputs[BUILD_MANIFEST_FILENAME] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return outputs


def verify_source_manifest(
    manifest: dict[str, Any],
    source_raw: bytes,
    outputs: dict[str, bytes],
) -> None:
    builder = manifest.get("builder")
    if not isinstance(builder, dict):
        raise ValueError("source manifest lacks builder")
    if builder.get("version") != BUILDER_VERSION:
        raise ValueError("builder version differs from source manifest")
    if builder.get("sha256") != sha256(pathlib.Path(__file__).read_bytes()):
        raise ValueError("builder SHA-256 differs from source manifest")
    canonical = manifest.get("canonical_source")
    if not isinstance(canonical, dict):
        raise ValueError("source manifest lacks canonical_source")
    if canonical.get("sha256") != sha256(source_raw):
        raise ValueError("gameplay source SHA-256 differs from source manifest")
    expected_outputs = manifest.get("expected_outputs")
    if not isinstance(expected_outputs, dict):
        raise ValueError("source manifest lacks expected_outputs")
    if set(expected_outputs) != set(outputs):
        raise ValueError("source manifest output set is incomplete")
    for filename, expectation in expected_outputs.items():
        if not isinstance(expectation, dict):
            raise ValueError(f"invalid expected output: {filename}")
        if expectation.get("sha256") != sha256(outputs[filename]):
            raise ValueError(f"output SHA-256 mismatch: {filename}")
        if expectation.get("size") != len(outputs[filename]):
            raise ValueError(f"output size mismatch: {filename}")


def write_outputs(outputs: dict[str, bytes], output_dir: pathlib.Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in outputs.items():
        (output_dir / filename).write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=pathlib.Path, default=DEFAULT_SOURCE
    )
    parser.add_argument(
        "--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST
    )
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument(
        "--skip-manifest-verification",
        action="store_true",
        help="Build an intentionally modified source without pinned hashes.",
    )
    args = parser.parse_args()

    source_raw, source = load_json(args.source)
    outputs = build_outputs(source_raw, source)
    if not args.skip_manifest_verification:
        _, manifest = load_json(args.manifest)
        verify_source_manifest(manifest, source_raw, outputs)
    write_outputs(outputs, args.output_dir)
    print(
        json.dumps(
            {
                "builder_version": BUILDER_VERSION,
                "output_dir": str(args.output_dir),
                "status": "partial-animation-foundation",
                "outputs": {
                    filename: {
                        "sha256": sha256(data),
                        "size": len(data),
                    }
                    for filename, data in sorted(outputs.items())
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
