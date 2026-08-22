#!/usr/bin/env python3
"""Audit the vanilla field sprite-palette loader without exporting ROM data.

The audit hash-gates the canonical US Rev0 ROM, verifies the three producers
of the per-object palette source key, pins all five logical palette-copy paths
and both shadow-buffer copies, and emits metadata/hashes only.
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

PC_NAMES = ("Crono", "Marle", "Lucca", "Robo", "Frog", "Ayla", "Magus")
PC_COUNT = len(PC_NAMES)
PC_DESCRIPTOR_TABLE_FILE = 0x24F000
PC_DESCRIPTOR_STRIDE = 5
DESCRIPTOR_PALETTE_BYTE = 2
COLLIDING_ID7_PALETTE_ID = 0x85

PALETTE_POINTER_TABLE_FILE = 0x242A00
PALETTE_SOURCE_FILE = 0x240000
VANILLA_PALETTE_SOURCE_BANK = 0xE4
VANILLA_PALETTE_BYTES = 0x18
VANILLA_VISIBLE_COLOR_COUNT = VANILLA_PALETTE_BYTES // 2
FULL_PALETTE_BYTES = 0x20
FULL_VISIBLE_PALETTE_BYTES = FULL_PALETTE_BYTES - 2
FULL_VISIBLE_COLOR_COUNT = FULL_VISIBLE_PALETTE_BYTES // 2

OBJECT_PALETTE_SOURCE_KEY = 0x1400
MAX_GENERATED_PALETTE_SOURCE_KEY = 0xFF * VANILLA_PALETTE_BYTES
SCHALA_EXPANDED_PALETTE_SENTINEL = 0xFFFF

PRIMARY_CGRAM_SHADOW = 0x7E2000
PRIMARY_SPRITE_PALETTE_BASE = 0x7E2100
MIRROR_CGRAM_SHADOW = 0x7E2200
MIRROR_SPRITE_PALETTE_BASE = 0x7E2300
CGRAM_SHADOW_SIZE = 0x200
SPRITE_PALETTE_ROW_BYTES = 0x20
PALETTE_DESTINATION_COLOR = 1
PALETTE_DESTINATION_OFFSET = PALETTE_DESTINATION_COLOR * 2


@dataclasses.dataclass(frozen=True)
class SourceKeyWriter:
    name: str
    signature_start_snes: int
    descriptor_read: bytes

    @property
    def store_snes(self) -> int:
        return self.signature_start_snes + len(self.descriptor_read) + 22


@dataclasses.dataclass(frozen=True)
class CopyPath:
    name: str
    purpose: str
    row_preamble_snes: int
    row_preamble: bytes
    copy_setup_snes: int

    @property
    def first_copy_snes(self) -> int:
        return self.copy_setup_snes + 11

    @property
    def second_copy_snes(self) -> int:
        return self.copy_setup_snes + 24


SOURCE_WRITER_COMMON = bytes.fromhex(
    "8D 02 42 "  # palette id -> WRMPYA
    "A9 18 "  # 24-byte stride -> WRMPYB
    "8D 03 42 "
    "EA EA EA "
    "C2 20 "
    "AD 16 42 "  # 16-bit product
    "18 "
    "69 00 00 "
    "A6 6D "
    "9D 00 14"  # per-object source key
)

SOURCE_KEY_WRITERS = (
    SourceKeyWriter(
        "playable-character descriptor",
        0xC044C3,
        bytes.fromhex("BF 02 F0 E4"),
    ),
    SourceKeyWriter(
        "NPC descriptor",
        0xC045CB,
        bytes.fromhex("BF 25 F0 E4"),
    ),
    SourceKeyWriter(
        "enemy descriptor",
        0xC0471A,
        bytes.fromhex("BF 02 F6 E4"),
    ),
)

EVENT_SET_ROW_PREAMBLE = bytes.fromhex(
    "0A 29 0E A6 6D 9D 81 0F C2 30 29 FF 00 "
    "0A 0A 0A 0A 1A 1A 18"
)
EVENT_RESTORE_ROW_PREAMBLE = bytes.fromhex(
    "BD 81 0F C2 30 29 FF 00 0A 0A 0A 0A 1A 1A 18"
)
ALLOCATOR_ROW_PREAMBLE = bytes.fromhex(
    "8A 0A 29 0E A6 6D 9D 81 0F C2 30 29 FF 00 "
    "0A 0A 0A 0A 1A 1A 18"
)

COPY_SETUP_SIGNATURE = bytes.fromhex(
    "69 00 21 "  # add $2100 primary sprite-row base
    "A8 8B 5A "
    "BD 00 14 AA DA "  # source key from per-object $1400
    "A9 17 00 54 7E E4 "  # 24 bytes E4:X -> 7E:Y
    "FA 68 18 69 00 02 A8 "  # restore source; destination += $0200
    "A9 17 00 54 7E E4"  # 24 bytes into mirror shadow
)

COPY_PATHS = (
    CopyPath(
        "event_set_palette",
        "event opcode $33 selects a row and reloads the object's source palette",
        0xC0371E,
        EVENT_SET_ROW_PREAMBLE,
        0xC03732,
    ),
    CopyPath(
        "event_palette_restore",
        "event opcode $88 palette-effect restore reloads the source palette",
        0xC048DB,
        EVENT_RESTORE_ROW_PREAMBLE,
        0xC048EA,
    ),
    CopyPath(
        "fixed_slot_allocator",
        "object types assigned fixed sprite-palette slots 5, 6, or 7",
        0xC071B3,
        ALLOCATOR_ROW_PREAMBLE,
        0xC071C8,
    ),
    CopyPath(
        "general_slot_allocator",
        "PC and NPC object types search sprite-palette slots 0 through 4",
        0xC07242,
        ALLOCATOR_ROW_PREAMBLE,
        0xC07257,
    ),
    CopyPath(
        "restricted_slot_allocator",
        "object types 5 and 6 search sprite-palette slots 1 through 3",
        0xC072DA,
        ALLOCATOR_ROW_PREAMBLE,
        0xC072EF,
    ),
)

SHADOW_MIRROR_SNES = 0xC0711D
SHADOW_MIRROR_SIGNATURE = bytes.fromhex(
    "A2 00 20 "  # X = $2000
    "A0 00 22 "  # Y = $2200
    "A9 FF 01 "  # $0200 bytes
    "8B 54 7E 7E AB E2 20 60"
)

CGRAM_UPLOAD_SNES = 0xC0712E
CGRAM_UPLOAD_SIGNATURE = bytes.fromhex(
    "A9 00 8D 21 21 "  # CGADD = 0
    "A9 00 8D 70 43 "  # DMA mode 0
    "A9 22 8D 71 43 "  # destination $2122
    "A2 00 22 8E 72 43 "  # source $2200
    "A9 7E 8D 74 43 "  # source bank $7E
    "A2 00 02 8E 75 43 "  # length $0200
    "A9 80 8D 0B 42 60"  # start channel 7
)

STA_OBJECT_PALETTE_KEY = bytes.fromhex("9D 00 14")


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snes_to_file(address: int) -> int:
    if not 0xC00000 <= address <= 0xFFFFFF:
        raise ValueError(f"address outside audited high-bank range: {address:#x}")
    return address & 0x3FFFFF


def format_snes(address: int) -> str:
    return f"${address >> 16:02X}:{address & 0xFFFF:04X}"


def read_u16_le(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError("16-bit read exceeds input")
    return int.from_bytes(data[offset : offset + 2], "little")


def require_bytes(data: bytes, address: int, expected: bytes, label: str) -> None:
    offset = snes_to_file(address)
    actual = data[offset : offset + len(expected)]
    if actual != expected:
        raise ValueError(
            f"{label} signature mismatch at {format_snes(address)}"
        )


def find_all(data: bytes, needle: bytes, start: int, end: int) -> list[int]:
    matches: list[int] = []
    cursor = start
    while True:
        match = data.find(needle, cursor, end)
        if match < 0:
            return matches
        matches.append(match)
        cursor = match + 1


def validate_layout_constants() -> None:
    if VANILLA_PALETTE_BYTES != 0x18:
        raise ValueError("vanilla field palette size drifted")
    if VANILLA_VISIBLE_COLOR_COUNT != 12:
        raise ValueError("vanilla visible-color count drifted")
    if FULL_VISIBLE_PALETTE_BYTES != 0x1E:
        raise ValueError("full visible-palette size drifted")
    if FULL_VISIBLE_COLOR_COUNT != 15:
        raise ValueError("full visible-color count drifted")
    if PALETTE_DESTINATION_OFFSET + FULL_VISIBLE_PALETTE_BYTES != (
        SPRITE_PALETTE_ROW_BYTES
    ):
        raise ValueError("full visible palette does not end at the row boundary")
    if MAX_GENERATED_PALETTE_SOURCE_KEY != 0x17E8:
        raise ValueError("generated palette-key domain drifted")
    if SCHALA_EXPANDED_PALETTE_SENTINEL <= MAX_GENERATED_PALETTE_SOURCE_KEY:
        raise ValueError("expanded-palette sentinel collides with vanilla keys")
    if len(COPY_PATHS) != 5:
        raise ValueError("expected five logical field palette-copy paths")


def validate_descriptor_contract(data: bytes) -> None:
    for pc_id in range(PC_COUNT):
        descriptor = PC_DESCRIPTOR_TABLE_FILE + pc_id * PC_DESCRIPTOR_STRIDE
        palette_id = data[descriptor + DESCRIPTOR_PALETTE_BYTE]
        if palette_id != pc_id:
            raise ValueError(
                f"PC descriptor {pc_id} palette id is {palette_id:#x}, "
                f"expected {pc_id:#x}"
            )
        pointer = read_u16_le(
            data, PALETTE_POINTER_TABLE_FILE + pc_id * 2
        )
        if pointer != pc_id * VANILLA_PALETTE_BYTES:
            raise ValueError(
                f"PC palette pointer {pc_id} is {pointer:#x}, expected "
                f"{pc_id * VANILLA_PALETTE_BYTES:#x}"
            )

    id7_descriptor = (
        PC_DESCRIPTOR_TABLE_FILE + PC_COUNT * PC_DESCRIPTOR_STRIDE
    )
    id7_palette_id = data[id7_descriptor + DESCRIPTOR_PALETTE_BYTE]
    if id7_palette_id != COLLIDING_ID7_PALETTE_ID:
        raise ValueError(
            f"occupied descriptor at logical id 7 changed: palette id "
            f"{id7_palette_id:#x}"
        )

    first_npc_pointer = read_u16_le(
        data, PALETTE_POINTER_TABLE_FILE + PC_COUNT * 2
    )
    if first_npc_pointer != PC_COUNT * VANILLA_PALETTE_BYTES:
        raise ValueError("first NPC palette pointer is not the eighth row")


def validate_source_key_writers(data: bytes) -> None:
    expected_stores: list[int] = []
    for writer in SOURCE_KEY_WRITERS:
        require_bytes(
            data,
            writer.signature_start_snes,
            writer.descriptor_read + SOURCE_WRITER_COMMON,
            writer.name,
        )
        expected_stores.append(snes_to_file(writer.store_snes))

    actual_stores = find_all(data, STA_OBJECT_PALETTE_KEY, 0, 0x10000)
    if actual_stores != expected_stores:
        formatted = ", ".join(f"$C0:{value:04X}" for value in actual_stores)
        raise ValueError(
            "unexpected writers of per-object palette source key $1400,X: "
            f"{formatted or 'none'}"
        )


def validate_copy_paths(data: bytes) -> None:
    for path in COPY_PATHS:
        require_bytes(
            data,
            path.row_preamble_snes,
            path.row_preamble,
            f"{path.name} row calculation",
        )
        require_bytes(
            data,
            path.copy_setup_snes,
            COPY_SETUP_SIGNATURE,
            f"{path.name} shadow copies",
        )


def validate_shadow_upload(data: bytes) -> None:
    require_bytes(
        data,
        SHADOW_MIRROR_SNES,
        SHADOW_MIRROR_SIGNATURE,
        "CGRAM shadow mirror",
    )
    require_bytes(
        data,
        CGRAM_UPLOAD_SNES,
        CGRAM_UPLOAD_SIGNATURE,
        "field CGRAM upload",
    )


def validate_static_contract(data: bytes) -> None:
    if len(data) != CANONICAL_ROM_SIZE:
        raise ValueError(
            f"ROM must be exactly {CANONICAL_ROM_SIZE:#x} bytes"
        )
    validate_layout_constants()
    validate_descriptor_contract(data)
    validate_source_key_writers(data)
    validate_copy_paths(data)
    validate_shadow_upload(data)


def verify_canonical_rom(path: pathlib.Path) -> bytes:
    data = path.read_bytes()
    if len(data) != CANONICAL_ROM_SIZE:
        raise ValueError(
            f"ROM size mismatch: got {len(data):#x}, "
            f"expected {CANONICAL_ROM_SIZE:#x}"
        )
    actual_sha1 = sha1(data)
    if actual_sha1 != CANONICAL_ROM_SHA1:
        raise ValueError(
            f"ROM SHA-1 mismatch: got {actual_sha1}, "
            f"expected {CANONICAL_ROM_SHA1}"
        )
    actual_sha256 = sha256(data)
    if actual_sha256 != CANONICAL_ROM_SHA256:
        raise ValueError(
            f"ROM SHA-256 mismatch: got {actual_sha256}, "
            f"expected {CANONICAL_ROM_SHA256}"
        )
    return data


def audit_rom(data: bytes) -> dict[str, Any]:
    validate_static_contract(data)

    pc_palette_rows = []
    for pc_id, name in enumerate(PC_NAMES):
        source_offset = (
            PALETTE_SOURCE_FILE + pc_id * VANILLA_PALETTE_BYTES
        )
        row = data[source_offset : source_offset + VANILLA_PALETTE_BYTES]
        pc_palette_rows.append(
            {
                "logical_id": pc_id,
                "name": name,
                "source_snes": format_snes(
                    0xE40000 + pc_id * VANILLA_PALETTE_BYTES
                ),
                "byte_count": len(row),
                "visible_color_count": len(row) // 2,
                "sha256": sha256(row),
            }
        )

    copy_paths = []
    for path in COPY_PATHS:
        copy_paths.append(
            {
                "name": path.name,
                "purpose": path.purpose,
                "row_calculation": format_snes(path.row_preamble_snes),
                "first_shadow_copy": format_snes(path.first_copy_snes),
                "mirror_shadow_copy": format_snes(path.second_copy_snes),
                "copy_count_each": VANILLA_PALETTE_BYTES,
            }
        )

    id7_descriptor = (
        PC_DESCRIPTOR_TABLE_FILE + PC_COUNT * PC_DESCRIPTOR_STRIDE
    )
    id7_palette_id = data[id7_descriptor + DESCRIPTOR_PALETTE_BYTE]
    id7_source_key = id7_palette_id * VANILLA_PALETTE_BYTES

    return {
        "tool_version": TOOL_VERSION,
        "status": "verified-static",
        "canonical_rom": {
            "size": len(data),
            "sha1": sha1(data),
            "sha256": sha256(data),
        },
        "reconstruction_commit": RECONSTRUCTION_COMMIT,
        "source_contract": {
            "bank": VANILLA_PALETTE_SOURCE_BANK,
            "base_snes": "$E4:0000",
            "descriptor_palette_id_width": 1,
            "stride": VANILLA_PALETTE_BYTES,
            "source_key_writers": [
                {
                    "name": writer.name,
                    "signature_start": format_snes(
                        writer.signature_start_snes
                    ),
                    "source_key_store": format_snes(writer.store_snes),
                }
                for writer in SOURCE_KEY_WRITERS
            ],
            "maximum_generated_source_key": (
                MAX_GENERATED_PALETTE_SOURCE_KEY
            ),
            "pc_palette_rows": pc_palette_rows,
            "logical_id7_collision": {
                "occupied_descriptor_snes": "$E4:F023",
                "palette_id": id7_palette_id,
                "generated_source_key": id7_source_key,
                "generated_source_snes": format_snes(
                    0xE40000 + id7_source_key
                ),
            },
        },
        "destination_contract": {
            "formula": (
                "$7E:2100 + ((palette_attribute & $0E) << 4) + $0002"
            ),
            "primary_sprite_palette_base": "$7E:2100",
            "mirror_sprite_palette_base": "$7E:2300",
            "mirror_delta": 0x200,
            "destination_first_color": PALETTE_DESTINATION_COLOR,
            "vanilla_destination_last_color": (
                PALETTE_DESTINATION_COLOR
                + VANILLA_VISIBLE_COLOR_COUNT
                - 1
            ),
            "vanilla_copy_bytes": VANILLA_PALETTE_BYTES,
            "untouched_tail_colors": [13, 14, 15],
            "untouched_tail_bytes": (
                FULL_VISIBLE_PALETTE_BYTES - VANILLA_PALETTE_BYTES
            ),
            "copy_paths": copy_paths,
        },
        "upload_contract": {
            "primary_to_mirror_copy": format_snes(SHADOW_MIRROR_SNES),
            "primary_shadow": "$7E:2000-$7E:21FF",
            "mirror_shadow": "$7E:2200-$7E:23FF",
            "field_cgram_upload": format_snes(CGRAM_UPLOAD_SNES),
            "upload_source": "$7E:2200",
            "upload_destination": "$2122 with CGADD=$00",
            "upload_bytes": CGRAM_SHADOW_SIZE,
        },
        "adapter_contract": {
            "source_key_sentinel": SCHALA_EXPANDED_PALETTE_SENTINEL,
            "sentinel_is_outside_generated_domain": True,
            "expanded_source_shape": (
                "one 16-color BGR555 row; adapter reads bytes $02-$1F"
            ),
            "expanded_copy_bytes_each_shadow": FULL_VISIBLE_PALETTE_BYTES,
            "expanded_visible_color_count": FULL_VISIBLE_COLOR_COUNT,
            "destination_still_begins_at_color": PALETTE_DESTINATION_COLOR,
            "logical_copy_paths_to_adapt": len(COPY_PATHS),
            "individual_mvn_sites_to_adapt": len(COPY_PATHS) * 2,
            "vanilla_source_keys_remain_unchanged": True,
        },
        "copyright_boundary": (
            "Metadata and hashes only; no ROM bytes, decoded colors, or "
            "palette images are emitted."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="canonical headerless Chrono Trigger US Rev0 ROM",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = audit_rom(verify_canonical_rom(args.rom))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
