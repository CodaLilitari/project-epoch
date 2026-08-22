#!/usr/bin/env python3
"""Audit the seven vanilla playable-character sprite packet envelopes.

The tool hash-gates the canonical US Rev0 ROM, reads its graphics, assembly,
animation, and descriptor tables only in memory, and emits metadata only.
It never writes or prints canonical-ROM bytes, decoded pixels, or images.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
from collections.abc import Sequence
from typing import Any


TOOL_VERSION = "1.0.0"
CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)
RECONSTRUCTION_COMMIT = "eeae27acdb6565e96d1d796a3d60792c250c0aa1"

PC_GFX_POINTER_TABLE_FILE = 0x242000
PC_ASSEMBLY_POINTER_TABLE_FILE = 0x242300
PC_ANIMATION_BOUNDARY_TABLE_FILE = 0x242600
PC_ANIMATION_DATA_BASE_SNES = 0xE40000
PC_DESCRIPTOR_TABLE_FILE = 0x24F000
PC_DESCRIPTOR_STRIDE = 5

BYTES_PER_4BPP_TILE = 0x20
ASSEMBLY_RECORD_SIZE = 0x28
ASSEMBLY_TILE_WORD_COUNT = 0x10
ASSEMBLY_OFFSET_BYTE_COUNT = 0x08
ASSEMBLY_OBJECT_COUNT = 4
TILE_INDEX_MASK = 0x07FF
HORIZONTAL_FLIP_MASK = 0x4000
UNCLASSIFIED_TILE_WORD_MASK = 0xB800
ANIMATION_FACING_COUNT = 4
ANIMATION_ENTRYPOINT_STRIDE = 4
ANIMATION_END_VALUE = 0xFF


@dataclasses.dataclass(frozen=True)
class PcPacket:
    name: str
    logical_id: int
    graphics_start_snes: int
    graphics_end_snes: int
    assembly_start_snes: int
    assembly_upper_bound_snes: int
    assembly_upper_bound_basis: str
    assembly_upper_bound_exact: bool

    @property
    def graphics_byte_count(self) -> int:
        return self.graphics_end_snes - self.graphics_start_snes

    @property
    def assembly_bounded_byte_count(self) -> int:
        return self.assembly_upper_bound_snes - self.assembly_start_snes


# Graphics ends are the next physical PC start in the same contiguous region,
# a bank end, or (for Ayla) the earliest later canonical graphics pointer.
# Assembly upper bounds are the next packet pointer except for Robo, whose
# same-bank physical end is not identified by a later pointer.
PC_PACKETS = (
    PcPacket(
        "Crono",
        0,
        0xD272C0,
        0xD30000,
        0xDC27B0,
        0xDC4E70,
        "next playable-character assembly pointer",
        True,
    ),
    PcPacket(
        "Marle",
        1,
        0xD40000,
        0xD47C40,
        0xDC9AD8,
        0xDCC080,
        "next playable-character assembly pointer",
        True,
    ),
    PcPacket(
        "Lucca",
        2,
        0xD36B40,
        0xD40000,
        0xDC4E70,
        0xDC7490,
        "next playable-character assembly pointer",
        True,
    ),
    PcPacket(
        "Robo",
        3,
        0xD47C40,
        0xD50000,
        0xDCC080,
        0xDD0000,
        "source-bank boundary; no later same-bank pointer proves packet end",
        False,
    ),
    PcPacket(
        "Frog",
        4,
        0xD30000,
        0xD36B40,
        0xDC7490,
        0xDC9AD8,
        "next playable-character assembly pointer",
        True,
    ),
    PcPacket(
        "Ayla",
        5,
        0xD50000,
        0xD58C00,
        0xDE0000,
        0xDE27D8,
        "first later canonical non-PC assembly pointer",
        True,
    ),
    PcPacket(
        "Magus",
        6,
        0xD20000,
        0xD272C0,
        0xDC0000,
        0xDC27B0,
        "next playable-character assembly pointer",
        True,
    ),
)

EXPECTED_ANIMATION_BOUNDARIES = (
    0x3000,
    0x34A0,
    0x3880,
    0x3CF0,
    0x4160,
    0x45C0,
    0x4B00,
    0x4ED0,
)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snes_to_file(address: int) -> int:
    """Map the audited high-bank addresses into a headerless 4 MiB ROM."""

    if not 0xC00000 <= address <= 0xFFFFFF:
        raise ValueError(f"address outside audited high-bank range: {address:#x}")
    return address & 0x3FFFFF


def read_u16_le(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError("16-bit read exceeds input")
    return int.from_bytes(data[offset : offset + 2], "little")


def read_u24_le(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 3 > len(data):
        raise ValueError("24-bit read exceeds input")
    return int.from_bytes(data[offset : offset + 3], "little")


def validate_layout_constants() -> None:
    if tuple(packet.logical_id for packet in PC_PACKETS) != tuple(range(7)):
        raise ValueError("playable-character IDs must be contiguous 0..6")
    if len(EXPECTED_ANIMATION_BOUNDARIES) != len(PC_PACKETS) + 1:
        raise ValueError("animation boundary table must have eight entries")
    if sorted(EXPECTED_ANIMATION_BOUNDARIES) != list(
        EXPECTED_ANIMATION_BOUNDARIES
    ):
        raise ValueError("animation boundaries are not monotonically ordered")

    graphics_windows = sorted(
        PC_PACKETS, key=lambda packet: packet.graphics_start_snes
    )
    for packet in graphics_windows:
        if packet.graphics_byte_count <= 0:
            raise ValueError(f"{packet.name}: empty graphics window")
        if packet.graphics_byte_count % BYTES_PER_4BPP_TILE:
            raise ValueError(f"{packet.name}: graphics window is not tile-aligned")
    for previous, current in zip(graphics_windows, graphics_windows[1:]):
        if previous.graphics_end_snes > current.graphics_start_snes:
            raise ValueError(
                f"{previous.name}/{current.name} graphics windows overlap"
            )

    for packet in PC_PACKETS:
        if packet.assembly_bounded_byte_count <= 0:
            raise ValueError(f"{packet.name}: empty assembly bound")


def verify_core_tables(rom: bytes) -> None:
    validate_layout_constants()
    expected_gfx = tuple(packet.graphics_start_snes for packet in PC_PACKETS)
    actual_gfx = tuple(
        read_u24_le(rom, PC_GFX_POINTER_TABLE_FILE + index * 3)
        for index in range(7)
    )
    if actual_gfx != expected_gfx:
        raise ValueError("playable-character graphics pointer table mismatch")

    expected_assembly = tuple(
        packet.assembly_start_snes for packet in PC_PACKETS
    )
    actual_assembly = tuple(
        read_u24_le(rom, PC_ASSEMBLY_POINTER_TABLE_FILE + index * 3)
        for index in range(7)
    )
    if actual_assembly != expected_assembly:
        raise ValueError("playable-character assembly pointer table mismatch")

    actual_animation_boundaries = tuple(
        read_u16_le(rom, PC_ANIMATION_BOUNDARY_TABLE_FILE + index * 2)
        for index in range(8)
    )
    if actual_animation_boundaries != EXPECTED_ANIMATION_BOUNDARIES:
        raise ValueError("playable-character animation boundary table mismatch")

    for index in range(7):
        offset = PC_DESCRIPTOR_TABLE_FILE + index * PC_DESCRIPTOR_STRIDE
        expected = bytes((index, index, index, index, 0))
        actual = rom[offset : offset + PC_DESCRIPTOR_STRIDE]
        if actual != expected:
            raise ValueError(
                f"playable-character descriptor {index} mismatch"
            )


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
    verify_core_tables(rom)
    return rom, identity


def signed_byte(value: int) -> int:
    if not 0 <= value <= 0xFF:
        raise ValueError("signed-byte input is outside 0..255")
    return value - 0x100 if value & 0x80 else value


def analyze_animation_blob(blob: bytes) -> dict[str, Any]:
    if not blob:
        raise ValueError("animation blob is empty")
    block_divisor = ANIMATION_FACING_COUNT * ANIMATION_ENTRYPOINT_STRIDE
    if len(blob) % block_divisor:
        raise ValueError(
            "animation blob is not four-facing/four-byte-entrypoint aligned"
        )

    facing_size = len(blob) // ANIMATION_FACING_COUNT
    entrypoint_count = facing_size // ANIMATION_ENTRYPOINT_STRIDE
    frame_bytes = [value for value in blob if value != ANIMATION_END_VALUE]
    if not frame_bytes:
        raise ValueError("animation blob contains no frame IDs")

    per_facing = []
    for facing in range(ANIMATION_FACING_COUNT):
        start = facing * facing_size
        block = blob[start : start + facing_size]
        stored = [value for value in block if value != ANIMATION_END_VALUE]
        per_facing.append(
            {
                "facing_index": facing,
                "byte_count": len(block),
                "entrypoint_count": entrypoint_count,
                "stored_frame_byte_count": len(stored),
                "sentinel_byte_count": len(block) - len(stored),
                "unique_frame_id_count": len(set(stored)),
                "maximum_frame_id": max(stored) if stored else None,
            }
        )

    return {
        "byte_count": len(blob),
        "facing_count": ANIMATION_FACING_COUNT,
        "facing_block_byte_count": facing_size,
        "entrypoint_stride": ANIMATION_ENTRYPOINT_STRIDE,
        "entrypoint_count_per_facing": entrypoint_count,
        "stored_frame_byte_count": len(frame_bytes),
        "sentinel_byte_count": len(blob) - len(frame_bytes),
        "unique_frame_ids": sorted(set(frame_bytes)),
        "unique_frame_id_count": len(set(frame_bytes)),
        "minimum_frame_id": min(frame_bytes),
        "maximum_frame_id": max(frame_bytes),
        "per_facing": per_facing,
    }


def animation_sequence_at_entrypoint(
    facing_block: bytes, entrypoint: int
) -> bytes:
    """Return one sentinel-terminated sequence from a single facing block.

    Animation entrypoints are spaced four bytes apart, but their sequences
    are not fixed-size records. A sequence may continue through a later
    entrypoint, which then addresses a suffix of the earlier sequence.
    """

    if not facing_block:
        raise ValueError("animation facing block is empty")
    if len(facing_block) % ANIMATION_ENTRYPOINT_STRIDE:
        raise ValueError("animation facing block is not entrypoint aligned")
    entrypoint_count = len(facing_block) // ANIMATION_ENTRYPOINT_STRIDE
    if not 0 <= entrypoint < entrypoint_count:
        raise ValueError("animation entrypoint is outside the facing block")

    start = entrypoint * ANIMATION_ENTRYPOINT_STRIDE
    try:
        end = facing_block.index(ANIMATION_END_VALUE, start)
    except ValueError as error:
        raise ValueError(
            "animation sequence has no in-block end sentinel"
        ) from error
    return facing_block[start:end]


def _assembly_record_words(record: bytes) -> tuple[int, ...]:
    if len(record) != ASSEMBLY_RECORD_SIZE:
        raise ValueError("assembly record has the wrong size")
    return tuple(
        read_u16_le(record, index * 2)
        for index in range(ASSEMBLY_TILE_WORD_COUNT)
    )


def analyze_assembly_envelope(
    assembly: bytes,
    frame_ids: Sequence[int],
    graphics_tile_count: int,
) -> dict[str, Any]:
    if not frame_ids:
        raise ValueError("frame ID sequence is empty")
    if any(not 0 <= frame_id < ANIMATION_END_VALUE for frame_id in frame_ids):
        raise ValueError("frame ID collides with the $FF animation sentinel")
    maximum_frame_id = max(frame_ids)
    record_count = maximum_frame_id + 1
    required_size = record_count * ASSEMBLY_RECORD_SIZE
    if required_size > len(assembly):
        raise ValueError("assembly bound is smaller than the frame-ID envelope")

    envelope = assembly[:required_size]
    referenced = sorted(set(frame_ids))
    referenced_words: list[int] = []
    all_words: list[int] = []
    offset_x: list[int] = []
    offset_y: list[int] = []
    for frame_id in range(record_count):
        start = frame_id * ASSEMBLY_RECORD_SIZE
        record = envelope[start : start + ASSEMBLY_RECORD_SIZE]
        words = _assembly_record_words(record)
        all_words.extend(words)
        if frame_id not in referenced:
            continue
        referenced_words.extend(words)
        offsets = record[
            ASSEMBLY_TILE_WORD_COUNT * 2 : ASSEMBLY_RECORD_SIZE
        ]
        offset_x.extend(signed_byte(offsets[index]) for index in range(0, 8, 2))
        offset_y.extend(signed_byte(offsets[index]) for index in range(1, 8, 2))

    referenced_indices = [word & TILE_INDEX_MASK for word in referenced_words]
    all_indices = [word & TILE_INDEX_MASK for word in all_words]
    outside = [
        index for index in referenced_indices if index >= graphics_tile_count
    ]
    unclassified_mask = 0
    for word in referenced_words:
        unclassified_mask |= word & UNCLASSIFIED_TILE_WORD_MASK

    return {
        "record_size": ASSEMBLY_RECORD_SIZE,
        "record_count_through_maximum_frame_id": record_count,
        "referenced_record_count": len(referenced),
        "unreferenced_record_count_within_envelope": record_count
        - len(referenced),
        "used_byte_count": required_size,
        "used_sha256": sha256(envelope),
        "tile_words_per_record": ASSEMBLY_TILE_WORD_COUNT,
        "offset_bytes_per_record": ASSEMBLY_OFFSET_BYTE_COUNT,
        "object_count_per_record": ASSEMBLY_OBJECT_COUNT,
        "referenced_tile_word_count": len(referenced_words),
        "minimum_referenced_tile_index": min(referenced_indices),
        "maximum_referenced_tile_index": max(referenced_indices),
        "maximum_tile_index_in_full_envelope": max(all_indices),
        "unique_referenced_tile_index_count": len(set(referenced_indices)),
        "horizontal_flip_word_count": sum(
            bool(word & HORIZONTAL_FLIP_MASK) for word in referenced_words
        ),
        "unclassified_high_flag_mask": f"0x{unclassified_mask:04X}",
        "out_of_graphics_window_reference_count": len(outside),
        "minimum_referenced_object_x_offset": min(offset_x),
        "maximum_referenced_object_x_offset": max(offset_x),
        "minimum_referenced_object_y_offset": min(offset_y),
        "maximum_referenced_object_y_offset": max(offset_y),
    }


def analyze_character(
    rom: bytes,
    packet: PcPacket,
    animation_start: int,
    animation_end: int,
) -> dict[str, Any]:
    graphics_start_file = snes_to_file(packet.graphics_start_snes)
    graphics_end_file = snes_to_file(packet.graphics_end_snes)
    graphics = rom[graphics_start_file:graphics_end_file]
    graphics_tile_count = len(graphics) // BYTES_PER_4BPP_TILE

    animation_start_snes = PC_ANIMATION_DATA_BASE_SNES + animation_start
    animation_end_snes = PC_ANIMATION_DATA_BASE_SNES + animation_end
    animation_blob = rom[
        snes_to_file(animation_start_snes) : snes_to_file(animation_end_snes)
    ]
    animation = analyze_animation_blob(animation_blob)

    assembly_start_file = snes_to_file(packet.assembly_start_snes)
    assembly_bound_file = snes_to_file(packet.assembly_upper_bound_snes)
    bounded_assembly = rom[assembly_start_file:assembly_bound_file]
    assembly = analyze_assembly_envelope(
        bounded_assembly,
        animation["unique_frame_ids"],
        graphics_tile_count,
    )
    used_end_snes = packet.assembly_start_snes + assembly["used_byte_count"]
    exact_match = used_end_snes == packet.assembly_upper_bound_snes

    if packet.assembly_upper_bound_exact and not exact_match:
        raise ValueError(
            f"{packet.name}: animation-derived assembly end does not match "
            "the next canonical packet pointer"
        )

    return {
        "character": packet.name,
        "logical_id": packet.logical_id,
        "descriptor": {
            "graphics_index": packet.logical_id,
            "assembly_index": packet.logical_id,
            "palette_index": packet.logical_id,
            "animation_index": packet.logical_id,
            "size_class": 0,
        },
        "graphics": {
            "start_snes": f"0x{packet.graphics_start_snes:06X}",
            "end_snes_exclusive": f"0x{packet.graphics_end_snes:06X}",
            "start_file": f"0x{graphics_start_file:06X}",
            "end_file_exclusive": f"0x{graphics_end_file:06X}",
            "byte_count": len(graphics),
            "tile_count": graphics_tile_count,
            "sha256": sha256(graphics),
        },
        "animation": {
            "start_snes": f"0x{animation_start_snes:06X}",
            "end_snes_exclusive": f"0x{animation_end_snes:06X}",
            "sha256": sha256(animation_blob),
            **animation,
        },
        "assembly": {
            "start_snes": f"0x{packet.assembly_start_snes:06X}",
            "animation_derived_end_snes_exclusive": f"0x{used_end_snes:06X}",
            "physical_upper_bound_snes_exclusive": (
                f"0x{packet.assembly_upper_bound_snes:06X}"
            ),
            "physical_upper_bound_basis": packet.assembly_upper_bound_basis,
            "physical_upper_bound_is_exact_packet_end": (
                packet.assembly_upper_bound_exact
            ),
            "animation_derived_end_matches_physical_bound": exact_match,
            "bounded_byte_count": len(bounded_assembly),
            "bounded_sha256": sha256(bounded_assembly),
            "unclassified_tail_byte_count": len(bounded_assembly)
            - assembly["used_byte_count"],
            **assembly,
        },
    }


def build_report(rom_path: pathlib.Path) -> dict[str, Any]:
    rom, identity = verify_canonical_rom(rom_path)
    characters = [
        analyze_character(
            rom,
            packet,
            EXPECTED_ANIMATION_BOUNDARIES[index],
            EXPECTED_ANIMATION_BOUNDARIES[index + 1],
        )
        for index, packet in enumerate(PC_PACKETS)
    ]
    total_graphics_tiles = sum(
        character["graphics"]["tile_count"] for character in characters
    )
    maximum_assembly_records = max(
        character["assembly"]["record_count_through_maximum_frame_id"]
        for character in characters
    )
    maximum_animation_entrypoints = max(
        character["animation"]["entrypoint_count_per_facing"]
        for character in characters
    )

    return {
        "schema_version": 1,
        "tool": {
            "path": "tools/audit_pc_sprite_packet_envelopes.py",
            "version": TOOL_VERSION,
        },
        "evidence": "verified-static",
        "reproduction": (
            "python tools/audit_pc_sprite_packet_envelopes.py "
            '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
        ),
        "canonical_rom": identity,
        "reconstruction": {
            "path": "references/ct_disassembly",
            "commit": RECONSTRUCTION_COMMIT,
            "relevant_code": [
                "$C0:448D-$C0:4555 descriptor and pointer resolution",
                "$C0:CB3A-$C0:CBDB animation addressing and frame-byte read",
                "$C0:CC04-$C0:CDC7 class-0 frame decode and upload queue",
                "$C0:E534-$C0:E686 horizontal tile decode",
                "$C0:E687-$C0:E934 non-flipped tile decode",
                "$C0:E952-$C0:E979 one-cell allocator",
                "$CC:E97E-$CC:EA30 battle pointer/stride setup",
            ],
        },
        "table_contract": {
            "graphics_pointer_table_snes": "0xE42000",
            "assembly_pointer_table_snes": "0xE42300",
            "animation_boundary_table_snes": "0xE42600",
            "animation_blob_base_snes": "0xE40000",
            "descriptor_table_snes": "0xE4F000",
            "descriptor_stride": PC_DESCRIPTOR_STRIDE,
            "descriptor_fields": [
                "graphics index",
                "assembly index",
                "palette index",
                "animation index",
                "size class",
            ],
        },
        "engine_envelope": {
            "all_vanilla_pc_size_class": 0,
            "assembly_record_size": ASSEMBLY_RECORD_SIZE,
            "assembly_tile_words_per_record": ASSEMBLY_TILE_WORD_COUNT,
            "assembly_offset_pairs_per_record": ASSEMBLY_OBJECT_COUNT,
            "object_count_per_record": ASSEMBLY_OBJECT_COUNT,
            "tile_index_mask": f"0x{TILE_INDEX_MASK:04X}",
            "tile_index_encoding_count": TILE_INDEX_MASK + 1,
            "raw_graphics_bytes_addressable_by_tile_index": (
                (TILE_INDEX_MASK + 1) * BYTES_PER_4BPP_TILE
            ),
            "horizontal_flip_test_mask": (
                f"0x{HORIZONTAL_FLIP_MASK:04X}"
            ),
            "animation_facing_count": ANIMATION_FACING_COUNT,
            "animation_entrypoint_stride": ANIMATION_ENTRYPOINT_STRIDE,
            "animation_end_value": f"0x{ANIMATION_END_VALUE:02X}",
            "maximum_encodable_frame_id": ANIMATION_END_VALUE - 1,
            "maximum_encodable_assembly_record_count": ANIMATION_END_VALUE,
            "maximum_encodable_assembly_byte_count": (
                ANIMATION_END_VALUE * ASSEMBLY_RECORD_SIZE
            ),
            "class0_decoded_tile_bytes_per_frame": (
                ASSEMBLY_TILE_WORD_COUNT * BYTES_PER_4BPP_TILE
            ),
            "class0_field_dma_transfer_count": 2,
            "class0_field_dma_bytes_per_transfer": 0x100,
            "class0_field_dma_total_bytes_per_frame": 0x200,
            "observed_maximum_assembly_record_count": maximum_assembly_records,
            "observed_maximum_animation_entrypoints_per_facing": (
                maximum_animation_entrypoints
            ),
            "total_raw_pc_graphics_tiles_audited": total_graphics_tiles,
        },
        "characters": characters,
        "interpretation_limits": [
            (
                "The animation-derived assembly span is the minimum envelope "
                "needed to address every non-$FF frame byte stored in the "
                "four canonical facing blocks; it is not a runtime coverage "
                "trace of every animation entrypoint."
            ),
            (
                "Six derived assembly ends coincide with a next canonical "
                "packet pointer. Robo ends at $DC:DF70 by frame-ID envelope, "
                "but no later same-bank pointer proves that this is its "
                "physical packet end; $DC:DF70-$DC:FFFF is not declared free."
            ),
            (
                "The four coordinate pairs are reported as signed-byte "
                "metadata. No untraced meaning is assigned to tile-word bits "
                "outside the proved $07FF index and $4000 horizontal-flip "
                "tests."
            ),
            (
                "These limits describe the vanilla size-class-0 PC path. "
                "They do not prove expanded-ROM bank handling, allocation, "
                "menu/overworld packets, or a complete Schala frame set."
            ),
        ],
        "copyright_boundary": (
            "No canonical-ROM bytes, decoded pixels, palettes, frame images, "
            "or assembly records are included in this report or written by "
            "the tool."
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
    print(json.dumps(build_report(args.rom), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
