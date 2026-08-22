#!/usr/bin/env python3
"""Compile Schala's original partial art into native-shaped sprite packets.

This compiler consumes only the Project Epoch clean-room indexed source.  It
emits a deduplicated raw 4bpp graphics packet and ten size-class-0 assembly
records, then reconstructs every source frame from those serialized packets.

The result proves packet-form compatibility for the current ten frames only.
It does not emit an animation blob, allocate ROM, patch a ROM, or install a
logical PC $07 resolver.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import itertools
import json
import pathlib
import struct
from collections.abc import Iterable, Sequence
from typing import Any

from PIL import Image

import build_schala_gameplay_foundation_v0 as foundation


BUILDER_VERSION = "1.0.0"
ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = foundation.DEFAULT_SOURCE
EXPECTED_SOURCE_SHA256 = (
    "9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2"
)

GRAPHICS_FILENAME = "schala_partial_graphics_v0.4bpp"
ASSEMBLY_FILENAME = "schala_partial_assembly_v0.bin"
PALETTE_FILENAME = "schala_partial_gameplay_palette_v0.bin"
FRAME_MAP_FILENAME = "schala_partial_frame_map_v0.json"
QA_SHEET_FILENAME = "schala_partial_packet_reconstruction_4x_v0.png"
MANIFEST_FILENAME = "schala_sprite_packet_foundation_manifest_v0.json"

FRAME_RECORD_SIZE = 0x28
TILE_WORD_COUNT = 16
OBJECT_COUNT = 4
OBJECT_TILE_WIDTH = 2
OBJECT_TILE_HEIGHT = 2
TILE_INDEX_MASK = 0x07FF
HORIZONTAL_FLIP_MASK = 0x4000
VANILLA_FIELD_CUSTOM_PALETTE_BYTES = 0x18
VANILLA_FIELD_CUSTOM_COLOR_COUNT = 12
BLANK_TILE = (0,) * 64


class SpritePacketError(ValueError):
    """Raised when source art cannot fit the audited native packet shape."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object_cells(origin: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    x, y = origin
    return tuple(
        (x + delta_x, y + delta_y)
        for delta_y in range(OBJECT_TILE_HEIGHT)
        for delta_x in range(OBJECT_TILE_WIDTH)
    )


def occupied_cells(
    pixels: Sequence[int], width: int, height: int
) -> frozenset[tuple[int, int]]:
    """Return the authoring-grid cells containing at least one visible pixel."""

    columns = width // 8
    return frozenset(
        (index % columns, index // columns)
        for index, tile in enumerate(
            foundation.iter_tiles(pixels, width, height)
        )
        if any(tile)
    )


def select_object_origins(
    occupied: Iterable[tuple[int, int]],
    grid_width: int,
    grid_height: int,
) -> tuple[tuple[int, int], ...]:
    """Choose at most four disjoint-on-art 2x2-tile object origins.

    Origins may extend by one transparent cell beyond the authoring canvas.
    That is necessary for odd-width 24x32 and sparse 40x40 sources while
    retaining the engine's fixed 16x16 object shape.
    """

    occupied_set = frozenset(occupied)
    if not occupied_set:
        raise SpritePacketError("a frame must contain visible cells")
    if any(
        x < 0 or y < 0 or x >= grid_width or y >= grid_height
        for x, y in occupied_set
    ):
        raise SpritePacketError("occupied cell lies outside the source grid")

    candidates = sorted(
        {
            (cell_x - delta_x, cell_y - delta_y)
            for cell_x, cell_y in occupied_set
            for delta_y in range(OBJECT_TILE_HEIGHT)
            for delta_x in range(OBJECT_TILE_WIDTH)
        }
    )
    for object_count in range(1, OBJECT_COUNT + 1):
        valid: list[
            tuple[
                tuple[int, int, tuple[tuple[int, int], ...]],
                tuple[tuple[int, int], ...],
            ]
        ] = []
        for origins in itertools.combinations(candidates, object_count):
            coverage = {cell: 0 for cell in occupied_set}
            for origin in origins:
                for cell in _object_cells(origin):
                    if cell in coverage:
                        coverage[cell] += 1
            if any(count != 1 for count in coverage.values()):
                continue

            object_cell_list = [
                cell for origin in origins for cell in _object_cells(origin)
            ]
            outside_count = sum(
                x < 0 or y < 0 or x >= grid_width or y >= grid_height
                for x, y in object_cell_list
            )
            transparent_inside_count = sum(
                0 <= x < grid_width
                and 0 <= y < grid_height
                and (x, y) not in occupied_set
                for x, y in object_cell_list
            )
            ordered = tuple(sorted(origins, key=lambda item: (item[1], item[0])))
            score = (outside_count, transparent_inside_count, ordered)
            valid.append((score, ordered))
        if valid:
            return min(valid, key=lambda item: item[0])[1]

    raise SpritePacketError(
        "visible cells do not fit four disjoint 16x16 sprite objects"
    )


def _tile_at(
    pixels: Sequence[int],
    width: int,
    height: int,
    tile_x: int,
    tile_y: int,
) -> tuple[int, ...]:
    if (
        tile_x < 0
        or tile_y < 0
        or tile_x >= width // 8
        or tile_y >= height // 8
    ):
        return BLANK_TILE
    return tuple(
        pixels[(tile_y * 8 + y) * width + tile_x * 8 + x]
        for y in range(8)
        for x in range(8)
    )


def _signed_byte(value: int) -> int:
    if not -128 <= value <= 127:
        raise SpritePacketError("assembly coordinate is outside signed byte")
    return value & 0xFF


def decode_signed_byte(value: int) -> int:
    if not 0 <= value <= 0xFF:
        raise SpritePacketError("coordinate byte is outside 0 through 255")
    return value - 0x100 if value & 0x80 else value


def _ordered_object_tiles(
    pixels: Sequence[int],
    width: int,
    height: int,
    origins: Sequence[tuple[int, int] | None],
) -> tuple[tuple[int, ...], ...]:
    """Return the engine stream order: 8 top tiles, then 8 bottom tiles."""

    if len(origins) != OBJECT_COUNT:
        raise SpritePacketError("exactly four object slots are required")
    ordered: list[tuple[int, ...]] = []
    for object_row in range(OBJECT_TILE_HEIGHT):
        for origin in origins:
            for object_column in range(OBJECT_TILE_WIDTH):
                if origin is None:
                    ordered.append(BLANK_TILE)
                else:
                    ordered.append(
                        _tile_at(
                            pixels,
                            width,
                            height,
                            origin[0] + object_column,
                            origin[1] + object_row,
                        )
                    )
    if len(ordered) != TILE_WORD_COUNT:
        raise AssertionError("internal tile-order length mismatch")
    return tuple(ordered)


def compile_packets(
    source_raw: bytes,
    source: dict[str, Any],
    *,
    enforce_source_hash: bool = True,
) -> dict[str, Any]:
    if enforce_source_hash and sha256(source_raw) != EXPECTED_SOURCE_SHA256:
        raise SpritePacketError("canonical gameplay source SHA-256 mismatch")
    frames = foundation.validate_source(source)

    tile_bank: list[tuple[int, ...]] = [BLANK_TILE]
    tile_indices: dict[tuple[int, ...], int] = {BLANK_TILE: 0}
    assembly = bytearray()
    frame_records: list[dict[str, Any]] = []

    for frame_index, frame_id in enumerate(foundation.REQUIRED_FRAME_IDS):
        frame = frames[frame_id]
        width, height, pixels = foundation.frame_pixels(frame)
        occupied = occupied_cells(pixels, width, height)
        active_origins = select_object_origins(
            occupied, width // 8, height // 8
        )
        padded_origins: tuple[tuple[int, int] | None, ...] = (
            *active_origins,
            *(None for _ in range(OBJECT_COUNT - len(active_origins))),
        )
        ordered_tiles = _ordered_object_tiles(
            pixels, width, height, padded_origins
        )
        words: list[int] = []
        for tile in ordered_tiles:
            if tile not in tile_indices:
                next_index = len(tile_bank)
                if next_index > TILE_INDEX_MASK:
                    raise SpritePacketError("$07FF tile-index ceiling exceeded")
                tile_indices[tile] = next_index
                tile_bank.append(tile)
            words.append(tile_indices[tile])

        anchor_x = width // 2
        anchor_y = height
        coordinates: list[tuple[int, int]] = []
        coordinate_bytes = bytearray()
        for origin in padded_origins:
            if origin is None:
                x_offset = 0
                y_offset = 0
            else:
                x_offset = origin[0] * 8 - anchor_x
                y_offset = origin[1] * 8 - anchor_y
            coordinates.append((x_offset, y_offset))
            coordinate_bytes.extend(
                (_signed_byte(x_offset), _signed_byte(y_offset))
            )

        record = struct.pack("<16H", *words) + bytes(coordinate_bytes)
        if len(record) != FRAME_RECORD_SIZE:
            raise AssertionError("internal assembly-record size mismatch")
        assembly.extend(record)
        frame_records.append(
            {
                "frame_id": frame_id,
                "frame_index": frame_index,
                "context": frame["context"],
                "canvas": {"width": width, "height": height},
                "anchor": {"x": anchor_x, "y": anchor_y},
                "active_object_count": len(active_origins),
                "object_origins_tiles": [
                    None if origin is None else list(origin)
                    for origin in padded_origins
                ],
                "object_coordinates_pixels": [
                    list(coordinate) for coordinate in coordinates
                ],
                "occupied_source_cells": [
                    list(cell) for cell in sorted(occupied, key=lambda p: (p[1], p[0]))
                ],
                "tile_indices_engine_order": words,
            }
        )

    graphics = b"".join(
        foundation.encode_snes_4bpp(tile, 8, 8) for tile in tile_bank
    )
    return {
        "graphics": graphics,
        "assembly": bytes(assembly),
        "frames": frame_records,
        "tile_count": len(tile_bank),
        "source_sha256": sha256(source_raw),
    }


def _decoded_tiles(graphics: bytes) -> tuple[tuple[int, ...], ...]:
    if len(graphics) % 32:
        raise SpritePacketError("graphics packet is not tile aligned")
    return tuple(
        foundation.decode_snes_4bpp(graphics[offset : offset + 32], 8, 8)
        for offset in range(0, len(graphics), 32)
    )


def reconstruct_frame(
    graphics: bytes,
    assembly: bytes,
    frame_record: dict[str, Any],
) -> tuple[int, int, tuple[int, ...]]:
    frame_index = frame_record["frame_index"]
    start = frame_index * FRAME_RECORD_SIZE
    record = assembly[start : start + FRAME_RECORD_SIZE]
    if len(record) != FRAME_RECORD_SIZE:
        raise SpritePacketError("assembly record lies outside packet")
    words = struct.unpack_from("<16H", record, 0)
    if any(word & ~TILE_INDEX_MASK for word in words):
        raise SpritePacketError("foundation packet contains unsupported flags")
    coordinates = tuple(
        (
            decode_signed_byte(record[0x20 + index * 2]),
            decode_signed_byte(record[0x21 + index * 2]),
        )
        for index in range(OBJECT_COUNT)
    )
    tiles = _decoded_tiles(graphics)
    if any(word >= len(tiles) for word in words):
        raise SpritePacketError("assembly tile index lies outside graphics")

    width = frame_record["canvas"]["width"]
    height = frame_record["canvas"]["height"]
    anchor_x = frame_record["anchor"]["x"]
    anchor_y = frame_record["anchor"]["y"]
    pixels = [0] * (width * height)
    for object_index, (x_offset, y_offset) in enumerate(coordinates):
        object_x = anchor_x + x_offset
        object_y = anchor_y + y_offset
        tile_slots = (
            (words[object_index * 2], 0, 0),
            (words[object_index * 2 + 1], 8, 0),
            (words[8 + object_index * 2], 0, 8),
            (words[8 + object_index * 2 + 1], 8, 8),
        )
        for tile_index, delta_x, delta_y in tile_slots:
            tile = tiles[tile_index]
            for y in range(8):
                target_y = object_y + delta_y + y
                if not 0 <= target_y < height:
                    continue
                for x in range(8):
                    target_x = object_x + delta_x + x
                    if not 0 <= target_x < width:
                        continue
                    value = tile[y * 8 + x]
                    if value:
                        pixels[target_y * width + target_x] = value
    return width, height, tuple(pixels)


def render_reconstruction_sheet(
    graphics: bytes,
    assembly: bytes,
    frame_records: Sequence[dict[str, Any]],
    palette_bytes: bytes,
) -> bytes:
    colors = foundation.decode_snes_palette(palette_bytes)
    flattened = [
        channel for color in colors for channel in color
    ] + [0, 0, 0] * (256 - len(colors))
    sheet = Image.new("P", (5 * 40, 2 * 40), 0)
    sheet.putpalette(flattened)
    sheet.info["transparency"] = 0
    for frame_record in frame_records:
        width, height, pixels = reconstruct_frame(
            graphics, assembly, frame_record
        )
        image = Image.new("P", (width, height))
        image.putdata(pixels)
        image.putpalette(flattened)
        image.info["transparency"] = 0
        index = frame_record["frame_index"]
        cell_x = (index % 5) * 40
        cell_y = (index // 5) * 40
        sheet.paste(
            image,
            (
                cell_x + (40 - width) // 2,
                cell_y + (40 - height) // 2,
            ),
        )
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
    source_raw: bytes,
    source: dict[str, Any],
    *,
    enforce_source_hash: bool = True,
) -> dict[str, bytes]:
    packet = compile_packets(
        source_raw, source, enforce_source_hash=enforce_source_hash
    )
    palette = foundation.encode_snes_palette(foundation.palette_rgb(source))
    visible_palette_indices = sorted(
        {
            pixel
            for frame in foundation.validate_source(source).values()
            for pixel in foundation.frame_pixels(frame)[2]
            if pixel
        }
    )
    frame_map = {
        "schema_version": 1,
        "status": "partial-native-shaped-packet-foundation",
        "logical_pc_id": 7,
        "source_sha256": packet["source_sha256"],
        "frame_record_size": FRAME_RECORD_SIZE,
        "tile_word_count": TILE_WORD_COUNT,
        "object_count": OBJECT_COUNT,
        "object_shape_tiles": [OBJECT_TILE_WIDTH, OBJECT_TILE_HEIGHT],
        "tile_index_mask": TILE_INDEX_MASK,
        "horizontal_flip_mask": HORIZONTAL_FLIP_MASK,
        "horizontal_flip_words_emitted": 0,
        "anchor_policy": "source-bottom-center",
        "frames": packet["frames"],
    }
    frame_map_bytes = (
        json.dumps(frame_map, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    outputs = {
        GRAPHICS_FILENAME: packet["graphics"],
        ASSEMBLY_FILENAME: packet["assembly"],
        PALETTE_FILENAME: palette,
        FRAME_MAP_FILENAME: frame_map_bytes,
        QA_SHEET_FILENAME: render_reconstruction_sheet(
            packet["graphics"],
            packet["assembly"],
            packet["frames"],
            palette,
        ),
    }
    manifest = {
        "schema_version": 1,
        "status": "partial-native-shaped-packet-foundation",
        "evidence": "verified-static",
        "builder": {
            "path": (
                "tools/build_schala_sprite_packet_foundation_v0.py"
            ),
            "version": BUILDER_VERSION,
            "sha256": sha256(pathlib.Path(__file__).read_bytes()),
            "command": (
                "python tools/build_schala_sprite_packet_foundation_v0.py "
                "--output-dir private/build/"
                "schala_sprite_packet_foundation_v0"
            ),
        },
        "canonical_source": {
            "path": DEFAULT_SOURCE.relative_to(ROOT).as_posix(),
            "sha256": packet["source_sha256"],
            "classification": "original-hand-pixelled-target-grid",
        },
        "logical_frame_count": len(packet["frames"]),
        "graphics_tile_count_including_blank": packet["tile_count"],
        "assembly_record_size": FRAME_RECORD_SIZE,
        "assembly_size": len(packet["assembly"]),
        "palette_contract": {
            "output_size": len(palette),
            "visible_indices_used": visible_palette_indices,
            "vanilla_field_custom_palette_bytes": (
                VANILLA_FIELD_CUSTOM_PALETTE_BYTES
            ),
            "vanilla_field_custom_color_count": (
                VANILLA_FIELD_CUSTOM_COLOR_COUNT
            ),
            "requires_full_palette_adapter": any(
                index > VANILLA_FIELD_CUSTOM_COLOR_COUNT
                for index in visible_palette_indices
            ),
        },
        "native_shape_compatible": True,
        "source_reconstruction_exact": True,
        "animation_blob": False,
        "complete_animation_sheet": False,
        "rom_allocation": False,
        "rom_integration": False,
        "rom_installable": False,
        "runtime_verified": False,
        "remaining_gates": [
            "complete_semantic_frame_inventory",
            "complete_four-facing_animation_blob",
            "auxiliary_animation_family",
            "expanded_graphics_bank_nonflip_decoder",
            "graphics_assembly_animation_pointer_adapters",
            "expanded_gameplay_palette_loader",
            "battle_staging_and_dma",
            "rom_allocation",
            "field_and_battle_runtime_replay",
        ],
        "outputs": {
            filename: {"sha256": sha256(data), "size": len(data)}
            for filename, data in sorted(outputs.items())
        },
    }
    outputs[MANIFEST_FILENAME] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return outputs


def verify_exact_reconstruction(
    source: dict[str, Any], outputs: dict[str, bytes]
) -> None:
    frame_map = json.loads(outputs[FRAME_MAP_FILENAME].decode("utf-8"))
    frames = foundation.validate_source(source)
    for frame_record in frame_map["frames"]:
        frame_id = frame_record["frame_id"]
        width, height, expected = foundation.frame_pixels(frames[frame_id])
        actual_width, actual_height, actual = reconstruct_frame(
            outputs[GRAPHICS_FILENAME],
            outputs[ASSEMBLY_FILENAME],
            frame_record,
        )
        if (actual_width, actual_height) != (width, height):
            raise SpritePacketError(f"{frame_id}: canvas changed")
        if actual != expected:
            raise SpritePacketError(
                f"{frame_id}: serialized packet reconstruction differs"
            )


def write_outputs(
    outputs: dict[str, bytes], output_dir: pathlib.Path
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in outputs.items():
        (output_dir / filename).write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=pathlib.Path, default=DEFAULT_SOURCE
    )
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument(
        "--allow-unpinned-source",
        action="store_true",
        help="compile an intentionally edited source before review/repinning",
    )
    args = parser.parse_args()

    source_raw, source = foundation.load_json(args.source)
    outputs = build_outputs(
        source_raw,
        source,
        enforce_source_hash=not args.allow_unpinned_source,
    )
    verify_exact_reconstruction(source, outputs)
    write_outputs(outputs, args.output_dir)
    manifest = json.loads(outputs[MANIFEST_FILENAME].decode("utf-8"))
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "logical_frame_count": manifest["logical_frame_count"],
                "graphics_tile_count_including_blank": manifest[
                    "graphics_tile_count_including_blank"
                ],
                "assembly_size": manifest["assembly_size"],
                "source_reconstruction_exact": manifest[
                    "source_reconstruction_exact"
                ],
                "rom_integration": manifest["rom_integration"],
                "outputs": manifest["outputs"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
