#!/usr/bin/env python3
"""Build Project Epoch's original Schala portrait foundation.

The canonical art is target-size textual palette-index data. This builder does
not read a ROM, save, emulator state, extracted tile, or concept bitmap. It
validates the source, packs SNES 4bpp tiles and BGR555 palette bytes, decodes
the packed bytes again, and renders deterministic indexed PNG QA previews.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import re
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
    / "portrait"
    / "schala_portraits_v0.json"
)
DEFAULT_MANIFEST = (
    ROOT / "assets" / "source" / "schala" / "v0" / "manifest.json"
)
ASSET_DIMENSIONS = {
    "schala_portrait_full_48x48_v0": (48, 48),
    "schala_portrait_preview_32x32_v0": (32, 32),
}
PACKED_FILENAMES = {
    "schala_portrait_full_48x48_v0": (
        "schala_portrait_full_48x48_v0.4bpp"
    ),
    "schala_portrait_preview_32x32_v0": (
        "schala_portrait_preview_32x32_v0.4bpp"
    ),
}
PALETTE_FILENAME = "schala_portrait_palette_v0.bin"
BUILD_MANIFEST_FILENAME = "schala_portrait_build_manifest_v0.json"
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
INDEX_ROW = re.compile(r"^[0-9A-F]+$")


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
    if palette.get("transparent_index") != 0:
        raise ValueError("palette index 0 must be transparent")
    entries = palette.get("entries")
    if not isinstance(entries, list) or len(entries) != 16:
        raise ValueError("portrait palette must contain exactly 16 entries")
    colors: list[tuple[int, int, int]] = []
    for expected_index, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("index") != expected_index:
            raise ValueError("palette indices must be ordered 0 through 15")
        colors.append(_hex_to_rgb(entry.get("hex", "")))
    return colors


def asset_pixels(asset: dict[str, Any]) -> tuple[int, int, tuple[int, ...]]:
    asset_id = asset.get("id")
    if asset_id not in ASSET_DIMENSIONS:
        raise ValueError(f"unexpected portrait asset ID: {asset_id!r}")
    expected_width, expected_height = ASSET_DIMENSIONS[asset_id]
    width = asset.get("width")
    height = asset.get("height")
    if (width, height) != (expected_width, expected_height):
        raise ValueError(
            f"{asset_id}: expected {expected_width}x{expected_height}, "
            f"got {width}x{height}"
        )
    if width % 8 or height % 8:
        raise ValueError(f"{asset_id}: dimensions must be multiples of 8")
    if asset.get("indexed_color_mode") != "4bpp-index-rows":
        raise ValueError(f"{asset_id}: source is not declared indexed 4bpp")
    if asset.get("derivation") != "original-independent-target-size":
        raise ValueError(f"{asset_id}: independent derivation is not declared")
    if not asset.get("canvas_id"):
        raise ValueError(f"{asset_id}: canvas_id is required")
    rows = asset.get("rows")
    if not isinstance(rows, list) or len(rows) != height:
        raise ValueError(f"{asset_id}: row count does not match height")
    pixels: list[int] = []
    for row_number, row in enumerate(rows):
        if (
            not isinstance(row, str)
            or len(row) != width
            or not INDEX_ROW.fullmatch(row)
        ):
            raise ValueError(
                f"{asset_id}: invalid row {row_number}; expected "
                f"{width} uppercase hexadecimal indices"
            )
        pixels.extend(int(character, 16) for character in row)
    return width, height, tuple(pixels)


def validate_source(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if source.get("schema_version") != 1:
        raise ValueError("unsupported portrait source schema")
    if source.get("source_classification") != "original-hand-pixelled":
        raise ValueError("source must be classified original-hand-pixelled")
    authorship = source.get("pixel_authorship")
    if not isinstance(authorship, dict):
        raise ValueError("pixel_authorship object is required")
    prohibited_flags = (
        "imported_layers",
        "imported_pixels",
        "rom_or_extracted_tile_input",
    )
    if any(authorship.get(flag) is not False for flag in prohibited_flags):
        raise ValueError("source declares imported or ROM-derived input")

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
        ):
            raise ValueError("concept references must be non-ROM-eligible")

    assets = source.get("assets")
    if not isinstance(assets, list) or len(assets) != 2:
        raise ValueError("exactly two portrait assets are required")
    by_id: dict[str, dict[str, Any]] = {}
    canvas_ids: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("portrait asset must be an object")
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or asset_id in by_id:
            raise ValueError("portrait asset IDs must be unique strings")
        asset_pixels(asset)
        canvas_id = asset.get("canvas_id")
        if canvas_id in canvas_ids:
            raise ValueError("full and preview portraits need distinct canvases")
        canvas_ids.add(canvas_id)
        by_id[asset_id] = asset
    if set(by_id) != set(ASSET_DIMENSIONS):
        raise ValueError("full and preview portrait IDs are both required")
    validate_independent_canvases(by_id)
    return by_id


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
        raise ValueError("SNES portrait palette must contain 16 colors")
    packed = bytearray()
    for red, green, blue in colors:
        if any(not 0 <= channel <= 255 for channel in (red, green, blue)):
            raise ValueError("RGB channel outside 0 through 255")
        bgr555 = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
        packed.extend(bgr555.to_bytes(2, "little"))
    return bytes(packed)


def decode_snes_palette(packed: bytes) -> list[tuple[int, int, int]]:
    if len(packed) != 0x20:
        raise ValueError("SNES portrait palette must be 0x20 bytes")
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


def _nearest_downsample(
    pixels: Sequence[int],
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
    *,
    centered: bool,
) -> tuple[int, ...]:
    result = []
    for y in range(target_height):
        if centered:
            source_y = min(
                source_height - 1,
                int((y + 0.5) * source_height / target_height),
            )
        else:
            source_y = y * source_height // target_height
        for x in range(target_width):
            if centered:
                source_x = min(
                    source_width - 1,
                    int((x + 0.5) * source_width / target_width),
                )
            else:
                source_x = x * source_width // target_width
            result.append(pixels[source_y * source_width + source_x])
    return tuple(result)


def validate_independent_canvases(
    assets: dict[str, dict[str, Any]]
) -> None:
    full_width, full_height, full = asset_pixels(
        assets["schala_portrait_full_48x48_v0"]
    )
    preview_width, preview_height, preview = asset_pixels(
        assets["schala_portrait_preview_32x32_v0"]
    )
    for offset_y in range(full_height - preview_height + 1):
        for offset_x in range(full_width - preview_width + 1):
            crop = tuple(
                full[(offset_y + y) * full_width + offset_x + x]
                for y in range(preview_height)
                for x in range(preview_width)
            )
            if crop == preview:
                raise ValueError("preview is an exact crop of the full portrait")
    for centered in (False, True):
        if (
            _nearest_downsample(
                full,
                full_width,
                full_height,
                preview_width,
                preview_height,
                centered=centered,
            )
            == preview
        ):
            raise ValueError(
                "preview is a nearest-neighbor resize of the full portrait"
            )


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


def audit_reference_tiles_in_memory(
    candidate_assets: dict[str, tuple[int, int, Sequence[int]]],
    reference_tiles: Iterable[Sequence[int]],
) -> dict[str, Any]:
    """Compare candidates with caller-provided reference tiles in memory.

    This deliberately has no ROM or file-reading path. A future gated audit can
    decode canonical comparison tiles in memory and pass them here without
    saving extracted copyrighted graphics.
    """

    indexed_references: dict[tuple[int, ...], int] = {}
    reference_count = 0
    for reference_index, reference in enumerate(reference_tiles):
        reference_tuple = tuple(reference)
        reference_count += 1
        if sum(pixel != 0 for pixel in reference_tuple) <= 2:
            continue
        for variant in tile_variants(reference_tuple):
            indexed_references.setdefault(variant, reference_index)

    matches = []
    trivial_candidates = []
    for asset_id, (width, height, pixels) in candidate_assets.items():
        for tile_index, tile in enumerate(iter_tiles(pixels, width, height)):
            nontransparent = sum(pixel != 0 for pixel in tile)
            if nontransparent <= 2:
                trivial_candidates.append(
                    {
                        "asset_id": asset_id,
                        "tile_index": tile_index,
                        "nontransparent_pixels": nontransparent,
                    }
                )
                continue
            if tile in indexed_references:
                matches.append(
                    {
                        "asset_id": asset_id,
                        "tile_index": tile_index,
                        "reference_tile_index": indexed_references[tile],
                    }
                )
    return {
        "reference_tile_count": reference_count,
        "matches": matches,
        "trivial_candidates": trivial_candidates,
    }


def audit_portrait_pair(
    assets: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    full_width, full_height, full = asset_pixels(
        assets["schala_portrait_full_48x48_v0"]
    )
    preview_width, preview_height, preview = asset_pixels(
        assets["schala_portrait_preview_32x32_v0"]
    )
    return audit_reference_tiles_in_memory(
        {
            "schala_portrait_preview_32x32_v0": (
                preview_width,
                preview_height,
                preview,
            )
        },
        iter_tiles(full, full_width, full_height),
    )


def build_outputs(
    source_raw: bytes, source: dict[str, Any]
) -> dict[str, bytes]:
    assets = validate_source(source)
    palette_bytes = encode_snes_palette(palette_rgb(source))
    outputs: dict[str, bytes] = {PALETTE_FILENAME: palette_bytes}
    for asset_id in sorted(assets):
        width, height, pixels = asset_pixels(assets[asset_id])
        packed = encode_snes_4bpp(pixels, width, height)
        if decode_snes_4bpp(packed, width, height) != pixels:
            raise AssertionError(f"{asset_id}: 4bpp round-trip failed")
        outputs[PACKED_FILENAMES[asset_id]] = packed
        outputs[assets[asset_id]["canonical_filename"]] = render_packed_png(
            packed, palette_bytes, width, height
        )

    pair_audit = audit_portrait_pair(assets)
    if pair_audit["matches"]:
        raise ValueError(
            "full and preview portraits share a non-trivial exact 8x8 tile"
        )
    manifest = {
        "schema_version": 1,
        "builder": {
            "path": "tools/build_schala_portraits_v0.py",
            "version": BUILDER_VERSION,
            "command": (
                "python tools/build_schala_portraits_v0.py "
                "--output-dir private/build/schala_portraits_v0"
            ),
        },
        "canonical_source": {
            "path": (
                "assets/source/schala/v0/portrait/"
                "schala_portraits_v0.json"
            ),
            "sha256": sha256(source_raw),
            "source_classification": "original-hand-pixelled",
        },
        "evidence": "verified-static",
        "rom_integration": False,
        "packed_from_source_then_decoded_for_png": True,
        "independent_portrait_audit": pair_audit,
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
    manifest: dict[str, Any], source_raw: bytes, outputs: dict[str, bytes]
) -> None:
    builder = manifest.get("builder")
    if not isinstance(builder, dict):
        raise ValueError("source manifest lacks builder")
    if builder.get("version") != BUILDER_VERSION:
        raise ValueError("builder version differs from source manifest")
    actual_builder = pathlib.Path(__file__).read_bytes()
    if builder.get("sha256") != sha256(actual_builder):
        raise ValueError("builder SHA-256 differs from source manifest")
    canonical = manifest.get("canonical_source")
    if not isinstance(canonical, dict):
        raise ValueError("source manifest lacks canonical_source")
    expected_source = canonical.get("sha256")
    if expected_source != sha256(source_raw):
        raise ValueError(
            "portrait source SHA-256 differs from source manifest"
        )
    expected_outputs = manifest.get("expected_outputs")
    if not isinstance(expected_outputs, dict):
        raise ValueError("source manifest lacks expected_outputs")
    for filename, expectation in expected_outputs.items():
        if filename not in outputs or not isinstance(expectation, dict):
            raise ValueError(f"missing expected output: {filename}")
        if expectation.get("sha256") != sha256(outputs[filename]):
            raise ValueError(f"output SHA-256 mismatch: {filename}")
        if expectation.get("size") != len(outputs[filename]):
            raise ValueError(f"output size mismatch: {filename}")
    if set(expected_outputs) != set(outputs):
        raise ValueError("source manifest output set is incomplete")


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
