#!/usr/bin/env python3
"""Audit two Project Epoch Schala asset sets against one pinned NPC packet.

The command accepts only an explicit clean Chrono Trigger US Rev0 ROM.  It
hash-gates the ROM, verifies the complete static chain from location $14E to
NPC descriptor $09 and compressed graphics selector $26, decodes that packet
in memory through the shared strict C3 decoder, and compares its 4bpp tiles
with the Project Epoch gameplay foundation and Glass Focus source.

Only metadata is emitted as deterministic JSON on standard output.  The tool
has no output-file option and never writes decoded bytes, pixels, images, ROMs,
patches, saves, states, or other artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import defaultdict
from collections.abc import Sequence
from typing import Any


TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import audit_ct_compressed_sprite_corpus as corpus
import audit_location_event_items as event_audit
import audit_schala_gameplay_originality as pc_audit
import build_schala_gameplay_foundation_v0 as gameplay
import validate_schala_glass_focus_pulse_v0 as focus


TOOL_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = 1
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_REL = pathlib.Path("tools/audit_schala_npc_originality.py")
REFERENCE_REL = pathlib.Path(
    "references/schala_npc_originality_audit_v0.json"
)
GAMEPLAY_SOURCE_REL = pathlib.Path(
    "assets/source/schala/v0/gameplay/"
    "schala_gameplay_foundation_v0.json"
)
GLASS_SOURCE_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_v0.json"
)
GLASS_MANIFEST_REL = pathlib.Path(
    "assets/source/schala/v0/focus/"
    "glass_focus_pulse_manifest_v0.json"
)
GAMEPLAY_SOURCE_PATH = ROOT / GAMEPLAY_SOURCE_REL
GLASS_SOURCE_PATH = ROOT / GLASS_SOURCE_REL
GLASS_MANIFEST_PATH = ROOT / GLASS_MANIFEST_REL
REPRODUCTION_COMMAND = (
    "python tools/audit_schala_npc_originality.py "
    '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
)

BEHAVIOR_DEPENDENCIES = (
    {
        "path": "tools/audit_ct_compressed_sprite_corpus.py",
        "size": 34_780,
        "sha256": (
            "5dcba015098dcf5a9ec754a5537f35ab6"
            "7144f0ac09d166e7644741a74ae990d"
        ),
        "role": "strict C3 sprite-packet decoder and canonical ROM gate",
    },
    {
        "path": "tools/audit_location_event_items.py",
        "size": 39_560,
        "sha256": (
            "cb39dd4485e6330c4f9d5b8817fe8e6a"
            "161cb2e965020cb1cd10a3fd30f7812a"
        ),
        "role": "location-event packet decoder and event parser",
    },
    {
        "path": "tools/audit_schala_gameplay_originality.py",
        "size": 14_624,
        "sha256": (
            "77f6724c5a0bfc73e26239337325f0a0"
            "94920954023978aae97c641a0804f0be"
        ),
        "role": "candidate packing and palette-pattern canonicalization",
    },
    {
        "path": "tools/build_schala_gameplay_foundation_v0.py",
        "size": 25_402,
        "sha256": (
            "e43f5d5b6fe30c5746ef04822f98f120"
            "165ecbea8393143e5b93941fdeb6cf8f"
        ),
        "role": "4bpp codec, tile iteration, and H/V/HV transforms",
    },
    {
        "path": "tools/validate_schala_glass_focus_pulse_v0.py",
        "size": 59_563,
        "sha256": (
            "0a51bd8b6ccb30893e5adc8da78f00b6"
            "1f98242a5ba0daf3403f33e2f4e3f93f"
        ),
        "role": "Glass Focus source and manifest validation",
    },
)

GAMEPLAY_SOURCE_SIZE = 25_193
GAMEPLAY_SOURCE_SHA256 = (
    "9c0d4dd9a83b6c77822286fb89deb04a"
    "7f1ae49261dedb1013e108f598af6db2"
)
GLASS_SOURCE_SIZE = 32_967
GLASS_SOURCE_SHA256 = (
    "cb705f5faa5b01fd365c57d69428a64"
    "c3df5cb40170b68130043d4c4d3dd0869"
)
GLASS_MANIFEST_SIZE = 6_284
GLASS_MANIFEST_SHA256 = (
    "dabbaa5b6a85d295f7726aa44683d96d"
    "6a8e0fbbf2d052e47c9b5d1b711c73f0"
)

LOCATION_ID = 0x14E
LOCATION_TABLE_FILE = 0x360000
LOCATION_RECORD_SIZE = 14
LOCATION_RECORD_FILE = 0x361244
LOCATION_RECORD_SHA256 = (
    "24cd1462f7836fd003542aa24d3e54d3"
    "1a22b2f13ac097b60fca735619270aa2"
)
LOCATION_EVENT_FIELD_OFFSET = 8
LOCATION_EVENT_FIELD_FILE = 0x36124C
LOCATION_EVENT_FIELD_SHA256 = (
    "5be57e88da9e860c2cd355ae7cbb4d18"
    "f972a0f751d61b79c08e03ea08f7a952"
)
EVENT_ID = 0x0CE
EVENT_POINTER_TABLE_FILE = 0x3CF9F0
EVENT_POINTER_ENTRY_FILE = 0x3CFC5A
EVENT_POINTER_ENTRY_SHA256 = (
    "8b6087b2ccd3f258baf933877765dcc2"
    "1310f921b0b8019124de11aa102c1eff"
)
EVENT_PACKET_SNES = 0xF969CE
EVENT_PACKET_FILE = 0x3969CE
EVENT_PACKET_COMPRESSED_SIZE = 942
EVENT_PACKET_COMPRESSED_SHA256 = (
    "083fe7d4acda8e841ebd115bf32e205c"
    "aec728e1c1a62c7550a412fcf33d9439"
)
EVENT_PACKET_DECOMPRESSED_SIZE = 1_435
EVENT_PACKET_DECOMPRESSED_SHA256 = (
    "0fdd87278dbeb3e95b385e1493ffb507"
    "e1e755e54c36a0055cdac9fa60e03179"
)
EVENT_OBJECT_COUNT = 17
EVENT_OBJECT_ID = 0x0F
EVENT_DATA_COMMAND_OFFSET = 0x0569
EVENT_OBJECT_END_OFFSET = 0x057D
EVENT_NPC_LOAD_OPCODE = 0x82
PRIMARY_NPC_ID = 0x09

NPC_DESCRIPTOR_TABLE_FILE = corpus.NPC_DESCRIPTOR_TABLE_FILE
NPC_DESCRIPTOR_TABLE_SIZE = corpus.NPC_DESCRIPTOR_TABLE_SIZE
NPC_DESCRIPTOR_TABLE_SHA256 = corpus.NPC_DESCRIPTOR_TABLE_SHA256
NPC_DESCRIPTOR_WIDTH = corpus.NPC_DESCRIPTOR_WIDTH
PRIMARY_NPC_DESCRIPTOR_FILE = 0x24F050
PRIMARY_NPC_DESCRIPTOR = bytes((0x26, 0x1B, 0x80, 0x3B, 0x00))
PRIMARY_NPC_DESCRIPTOR_SHA256 = (
    "dcfb1fcb9573e7cbf2cba1290b2bd187"
    "889a84efdbb67a4ca7d654288158eae8"
)
PALETTE_VARIANT_NPC_ID = 0xCD
PALETTE_VARIANT_DESCRIPTOR_FILE = 0x24F424
PALETTE_VARIANT_DESCRIPTOR = bytes((0x26, 0x1B, 0x9F, 0x3B, 0x00))
PALETTE_VARIANT_DESCRIPTOR_SHA256 = (
    "41e0318fa8379ff61f108f09ea783569"
    "03f09f780d2d52af2a70610dc8243186"
)
EXPECTED_GEOMETRY_FAMILY_IDS = (PRIMARY_NPC_ID, PALETTE_VARIANT_NPC_ID)

GFX_SELECTOR = 0x26
GFX_POINTER_TABLE_FILE = corpus.GFX_POINTER_TABLE_FILE
GFX_POINTER_TABLE_SIZE = corpus.GFX_POINTER_TABLE_SIZE
GFX_POINTER_TABLE_SHA256 = corpus.GFX_POINTER_TABLE_SHA256
GFX_POINTER_ENTRY_FILE = 0x242072
GFX_POINTER_ENTRY_SHA256 = (
    "7822e4cd703e8fb82ba2766461562c54"
    "3e736992295644f3fa683f3a0da1005f"
)
SPRITE_PACKET_SNES = 0xD9E2CE
SPRITE_PACKET_FILE = 0x19E2CE
SPRITE_PACKET_COMPRESSED_SIZE = 2_447
SPRITE_PACKET_COMPRESSED_SHA256 = (
    "db9b1e5967ad25ba7af2692e077fa7d"
    "a73e3d9659280d81fbe8f00c64109e1a3"
)
SPRITE_PACKET_DECOMPRESSED_SIZE = 2_528
SPRITE_PACKET_DECOMPRESSED_SHA256 = (
    "69322758b77fff5701cb0d5edb4ca34a"
    "b4109c2313ececd37bc018106fe84b73"
)
SPRITE_PACKET_TILE_COUNT = 79
SPRITE_PACKET_BACKREF_WIDTH_BITS = 12
SPRITE_PACKET_ADDENDUM_COUNT = 0

TRIVIAL_VISIBLE_PIXEL_LIMIT = 2
TRANSFORMS = ("identity", "horizontal", "vertical", "combined")
REFERENCE_EXPECTED_COUNTS = {
    "tile_count": 79,
    "excluded_trivial_tile_count": 1,
    "compared_tile_count": 78,
}
CANDIDATE_EXPECTED_COUNTS = {
    "gameplay_foundation": {
        "asset_count": 10,
        "tile_occurrence_count": 159,
        "excluded_trivial_tile_occurrence_count": 59,
        "compared_tile_occurrence_count": 100,
        "exact_index_match_count": 0,
        "visible_pattern_match_count": 0,
        "framed_candidate_pixels_sha256": (
            "d367e7dd2c163aa47bdaf93df466b9767"
            "d64d51a99be5f42a0d39bec978c580b"
        ),
    },
    "glass_focus": {
        "asset_count": 12,
        "tile_occurrence_count": 174,
        "excluded_trivial_tile_occurrence_count": 80,
        "compared_tile_occurrence_count": 94,
        "exact_index_match_count": 0,
        "visible_pattern_match_count": 0,
        "framed_candidate_pixels_sha256": (
            "3b7504fb82ceecb1afa39b5e0019e5b5"
            "52a6f6575d3a7792f3200402acf2dd9d"
        ),
    },
}

SEMANTIC_ANCHOR_COMMIT = "3af9a5a8fa5db7cd47740c791fa6580f7a4efa44"
SEMANTIC_ANCHOR_URL = (
    "https://github.com/Pseudoarc/jetsoftime/blob/"
    f"{SEMANTIC_ANCHOR_COMMIT}/sourcefiles/bossrandoevent.py#L188-L201"
)


class SchalaNpcOriginalityError(RuntimeError):
    """Raised when any pinned chain or bounded originality fact drifts."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_report_bytes(report: dict[str, Any]) -> bytes:
    return (
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _exact_slice(data: bytes, start: int, size: int, label: str) -> bytes:
    if start < 0 or size < 0 or start + size > len(data):
        raise SchalaNpcOriginalityError(f"{label}: range exceeds input")
    result = data[start : start + size]
    if len(result) != size:
        raise SchalaNpcOriginalityError(f"{label}: short range")
    return result


def _require_digest(
    data: bytes, expected_size: int, expected_sha256: str, label: str
) -> None:
    if len(data) != expected_size:
        raise SchalaNpcOriginalityError(
            f"{label} size drifted: {len(data)} != {expected_size}"
        )
    actual = sha256(data)
    if actual != expected_sha256:
        raise SchalaNpcOriginalityError(
            f"{label} SHA-256 drifted: {actual}"
        )


def _read_pinned_json(
    path: pathlib.Path, expected_size: int, expected_sha256: str, label: str
) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    _require_digest(raw, expected_size, expected_sha256, label)
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchalaNpcOriginalityError(
            f"{label} is not canonical JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise SchalaNpcOriginalityError(f"{label} root must be an object")
    return raw, parsed


def verify_behavior_dependencies() -> list[dict[str, Any]]:
    """Gate every imported behavior-bearing helper before its first use."""

    verified: list[dict[str, Any]] = []
    for expected in BEHAVIOR_DEPENDENCIES:
        path = ROOT / expected["path"]
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise SchalaNpcOriginalityError(
                f"behavior dependency unavailable: {expected['path']}"
            ) from exc
        _require_digest(
            raw,
            expected["size"],
            expected["sha256"],
            f"behavior dependency {expected['path']}",
        )
        verified.append(dict(expected))
    return verified


def validate_canonical_rom(rom: bytes) -> dict[str, Any]:
    try:
        return corpus.validate_canonical_rom(rom)
    except corpus.AuditError as exc:
        raise SchalaNpcOriginalityError(str(exc)) from exc


def inspect_location_event_chain(rom: bytes) -> dict[str, Any]:
    """Verify location $14E through object $0F's NPC-load command."""

    expected_record_file = (
        LOCATION_TABLE_FILE + LOCATION_ID * LOCATION_RECORD_SIZE
    )
    if expected_record_file != LOCATION_RECORD_FILE:
        raise AssertionError("location-record constant arithmetic drifted")
    if (
        LOCATION_RECORD_FILE + LOCATION_EVENT_FIELD_OFFSET
        != LOCATION_EVENT_FIELD_FILE
    ):
        raise AssertionError("location-event field constant drifted")
    record = _exact_slice(
        rom, LOCATION_RECORD_FILE, LOCATION_RECORD_SIZE, "location record"
    )
    _require_digest(
        record,
        LOCATION_RECORD_SIZE,
        LOCATION_RECORD_SHA256,
        "location $14E record",
    )
    event_field = record[
        LOCATION_EVENT_FIELD_OFFSET : LOCATION_EVENT_FIELD_OFFSET + 2
    ]
    _require_digest(
        event_field,
        2,
        LOCATION_EVENT_FIELD_SHA256,
        "location $14E event field",
    )
    event_id = int.from_bytes(event_field, "little")
    if event_id != EVENT_ID:
        raise SchalaNpcOriginalityError("location $14E event ID drifted")

    expected_pointer_file = EVENT_POINTER_TABLE_FILE + EVENT_ID * 3
    if expected_pointer_file != EVENT_POINTER_ENTRY_FILE:
        raise AssertionError("event-pointer constant arithmetic drifted")
    pointer_entry = _exact_slice(
        rom, EVENT_POINTER_ENTRY_FILE, 3, "event pointer entry"
    )
    _require_digest(
        pointer_entry,
        3,
        EVENT_POINTER_ENTRY_SHA256,
        "event $0CE pointer entry",
    )
    event_pointer = int.from_bytes(pointer_entry, "little")
    if event_pointer != EVENT_PACKET_SNES:
        raise SchalaNpcOriginalityError("event $0CE pointer drifted")
    try:
        event_file = event_audit.snes_hirom_to_file(event_pointer)
    except event_audit.AuditError as exc:
        raise SchalaNpcOriginalityError(str(exc)) from exc
    if event_file != EVENT_PACKET_FILE:
        raise SchalaNpcOriginalityError("event $0CE file mapping drifted")

    compressed = _exact_slice(
        rom,
        EVENT_PACKET_FILE,
        EVENT_PACKET_COMPRESSED_SIZE,
        "event $0CE compressed packet",
    )
    _require_digest(
        compressed,
        EVENT_PACKET_COMPRESSED_SIZE,
        EVENT_PACKET_COMPRESSED_SHA256,
        "event $0CE compressed packet",
    )
    try:
        packet = event_audit.decompress_packet(rom, EVENT_PACKET_FILE)
    except event_audit.AuditError as exc:
        raise SchalaNpcOriginalityError(str(exc)) from exc
    if packet.compressed_size != EVENT_PACKET_COMPRESSED_SIZE:
        raise SchalaNpcOriginalityError(
            "event $0CE decoded compressed extent drifted"
        )
    _require_digest(
        packet.data,
        EVENT_PACKET_DECOMPRESSED_SIZE,
        EVENT_PACKET_DECOMPRESSED_SHA256,
        "event $0CE decompressed packet",
    )
    if not packet.small_width or packet.addendum_count != 1:
        raise SchalaNpcOriginalityError(
            "event $0CE compression metadata drifted"
        )
    if not packet.data or packet.data[0] != EVENT_OBJECT_COUNT:
        raise SchalaNpcOriginalityError("event $0CE object count drifted")
    try:
        commands = event_audit.parse_event(EVENT_ID, packet.data)
    except event_audit.AuditError as exc:
        raise SchalaNpcOriginalityError(str(exc)) from exc
    command_matches = [
        command
        for command in commands
        if command.object_id == EVENT_OBJECT_ID
        and command.offset == EVENT_DATA_COMMAND_OFFSET
    ]
    if len(command_matches) != 1:
        raise SchalaNpcOriginalityError(
            "event $0CE object $0F command boundary drifted"
        )
    command = command_matches[0]
    if (
        command.opcode != EVENT_NPC_LOAD_OPCODE
        or command.payload != bytes((PRIMARY_NPC_ID,))
    ):
        raise SchalaNpcOriginalityError(
            "event $0CE object $0F NPC-load command drifted"
        )
    event_data = packet.data[1:]
    object_table_offset = EVENT_OBJECT_ID * 32
    object_start = int.from_bytes(
        event_data[object_table_offset : object_table_offset + 2], "little"
    )
    next_object_table_offset = (EVENT_OBJECT_ID + 1) * 32
    object_end = int.from_bytes(
        event_data[
            next_object_table_offset : next_object_table_offset + 2
        ],
        "little",
    )
    if (
        object_start != EVENT_DATA_COMMAND_OFFSET
        or object_end != EVENT_OBJECT_END_OFFSET
    ):
        raise SchalaNpcOriginalityError(
            "event $0CE object $0F bytecode range drifted"
        )

    return {
        "location_id": LOCATION_ID,
        "location_record": {
            "file_offset": f"0x{LOCATION_RECORD_FILE:06X}",
            "snes_range": "$F6:1244-$F6:1251",
            "size": LOCATION_RECORD_SIZE,
            "sha256": sha256(record),
        },
        "event_field": {
            "file_offset": f"0x{LOCATION_EVENT_FIELD_FILE:06X}",
            "snes_address": "$F6:124C",
            "event_id": EVENT_ID,
            "size": len(event_field),
            "sha256": sha256(event_field),
        },
        "event_pointer": {
            "table_file_offset": f"0x{EVENT_POINTER_TABLE_FILE:06X}",
            "entry_file_offset": f"0x{EVENT_POINTER_ENTRY_FILE:06X}",
            "entry_snes_address": "$FC:FC5A",
            "entry_sha256": sha256(pointer_entry),
            "packet_snes_pointer": f"${event_pointer:06X}",
            "packet_file_offset": f"0x{event_file:06X}",
        },
        "event_packet": {
            "compressed_size": packet.compressed_size,
            "compressed_sha256": sha256(compressed),
            "decompressed_size": len(packet.data),
            "decompressed_sha256": sha256(packet.data),
            "backref_width_bits": 11,
            "addendum_count": packet.addendum_count,
            "object_count": packet.data[0],
        },
        "npc_load_command": {
            "object_id": EVENT_OBJECT_ID,
            "event_data_offset": f"0x{command.offset:04X}",
            "object_end_offset_exclusive": f"0x{object_end:04X}",
            "opcode": command.opcode,
            "npc_id": command.payload[0],
        },
    }


def _descriptor_geometry(record: bytes) -> tuple[int, int, int, int]:
    if len(record) != NPC_DESCRIPTOR_WIDTH:
        raise SchalaNpcOriginalityError("NPC descriptor width drifted")
    return record[0], record[1], record[3], record[4]


def inspect_sprite_chain(rom: bytes) -> tuple[dict[str, Any], bytes]:
    """Verify NPC $09/$CD, selector $26, and the strict sprite decode."""

    pointer_table = _exact_slice(
        rom,
        GFX_POINTER_TABLE_FILE,
        GFX_POINTER_TABLE_SIZE,
        "graphics pointer table",
    )
    _require_digest(
        pointer_table,
        GFX_POINTER_TABLE_SIZE,
        GFX_POINTER_TABLE_SHA256,
        "graphics pointer table",
    )
    descriptor_table = _exact_slice(
        rom,
        NPC_DESCRIPTOR_TABLE_FILE,
        NPC_DESCRIPTOR_TABLE_SIZE,
        "NPC descriptor table",
    )
    _require_digest(
        descriptor_table,
        NPC_DESCRIPTOR_TABLE_SIZE,
        NPC_DESCRIPTOR_TABLE_SHA256,
        "NPC descriptor table",
    )

    def descriptor(npc_id: int) -> bytes:
        start = npc_id * NPC_DESCRIPTOR_WIDTH
        return descriptor_table[start : start + NPC_DESCRIPTOR_WIDTH]

    primary = descriptor(PRIMARY_NPC_ID)
    variant = descriptor(PALETTE_VARIANT_NPC_ID)
    _require_digest(
        primary,
        NPC_DESCRIPTOR_WIDTH,
        PRIMARY_NPC_DESCRIPTOR_SHA256,
        "NPC $09 descriptor",
    )
    _require_digest(
        variant,
        NPC_DESCRIPTOR_WIDTH,
        PALETTE_VARIANT_DESCRIPTOR_SHA256,
        "NPC $CD descriptor",
    )
    if primary != PRIMARY_NPC_DESCRIPTOR:
        raise SchalaNpcOriginalityError("NPC $09 descriptor fields drifted")
    if variant != PALETTE_VARIANT_DESCRIPTOR:
        raise SchalaNpcOriginalityError("NPC $CD descriptor fields drifted")

    geometry = _descriptor_geometry(primary)
    geometry_family_ids = tuple(
        npc_id
        for npc_id in range(corpus.NPC_DESCRIPTOR_COUNT)
        if _descriptor_geometry(descriptor(npc_id)) == geometry
    )
    if geometry_family_ids != EXPECTED_GEOMETRY_FAMILY_IDS:
        raise SchalaNpcOriginalityError(
            "NPC $09 same-geometry descriptor family drifted"
        )
    differing_fields = tuple(
        index
        for index, (left, right) in enumerate(zip(primary, variant))
        if left != right
    )
    if differing_fields != (2,):
        raise SchalaNpcOriginalityError(
            "NPC $CD is no longer a palette-only descriptor variant"
        )
    if primary[0] != GFX_SELECTOR:
        raise SchalaNpcOriginalityError("NPC $09 selector drifted")

    pointer_entry_start = GFX_SELECTOR * corpus.GFX_POINTER_WIDTH
    pointer_entry = pointer_table[
        pointer_entry_start : pointer_entry_start + corpus.GFX_POINTER_WIDTH
    ]
    _require_digest(
        pointer_entry,
        corpus.GFX_POINTER_WIDTH,
        GFX_POINTER_ENTRY_SHA256,
        "graphics selector $26 pointer entry",
    )
    sprite_pointer = int.from_bytes(pointer_entry, "little")
    if sprite_pointer != SPRITE_PACKET_SNES:
        raise SchalaNpcOriginalityError(
            "graphics selector $26 pointer drifted"
        )
    pointer_alias_indexes = tuple(
        index
        for index in range(corpus.GFX_POINTER_COUNT)
        if pointer_table[
            index * corpus.GFX_POINTER_WIDTH :
            (index + 1) * corpus.GFX_POINTER_WIDTH
        ]
        == pointer_entry
    )
    if pointer_alias_indexes != (GFX_SELECTOR,):
        raise SchalaNpcOriginalityError(
            "graphics selector $26 pointer aliases drifted"
        )
    try:
        sprite_file = corpus.snes_hirom_to_file(sprite_pointer)
    except corpus.AuditError as exc:
        raise SchalaNpcOriginalityError(str(exc)) from exc
    if sprite_file != SPRITE_PACKET_FILE:
        raise SchalaNpcOriginalityError(
            "graphics selector $26 file mapping drifted"
        )
    compressed = _exact_slice(
        rom,
        SPRITE_PACKET_FILE,
        SPRITE_PACKET_COMPRESSED_SIZE,
        "graphics selector $26 compressed packet",
    )
    _require_digest(
        compressed,
        SPRITE_PACKET_COMPRESSED_SIZE,
        SPRITE_PACKET_COMPRESSED_SHA256,
        "graphics selector $26 compressed packet",
    )
    try:
        packet = corpus.decode_c3_sprite_packet(rom, sprite_file)
    except corpus.AuditError as exc:
        raise SchalaNpcOriginalityError(str(exc)) from exc
    if packet.compressed_size != SPRITE_PACKET_COMPRESSED_SIZE:
        raise SchalaNpcOriginalityError(
            "graphics selector $26 decoded extent drifted"
        )
    _require_digest(
        packet.data,
        SPRITE_PACKET_DECOMPRESSED_SIZE,
        SPRITE_PACKET_DECOMPRESSED_SHA256,
        "graphics selector $26 decompressed packet",
    )
    if (
        packet.backref_width_bits != SPRITE_PACKET_BACKREF_WIDTH_BITS
        or packet.addendum_count != SPRITE_PACKET_ADDENDUM_COUNT
        or packet.segment_count != 1
    ):
        raise SchalaNpcOriginalityError(
            "graphics selector $26 compression metadata drifted"
        )
    if len(packet.data) // corpus.BYTES_PER_4BPP_TILE != (
        SPRITE_PACKET_TILE_COUNT
    ):
        raise SchalaNpcOriginalityError(
            "graphics selector $26 tile count drifted"
        )

    metadata = {
        "tables": {
            "graphics_pointer_table": {
                "file_offset": f"0x{GFX_POINTER_TABLE_FILE:06X}",
                "snes_range": "$E4:2000-$E4:22FF",
                "size": len(pointer_table),
                "sha256": sha256(pointer_table),
            },
            "npc_descriptor_table": {
                "file_offset": f"0x{NPC_DESCRIPTOR_TABLE_FILE:06X}",
                "snes_range": "$E4:F023-$E4:F522",
                "entry_count": corpus.NPC_DESCRIPTOR_COUNT,
                "entry_width": NPC_DESCRIPTOR_WIDTH,
                "size": len(descriptor_table),
                "sha256": sha256(descriptor_table),
            },
        },
        "descriptor_family": {
            "primary": {
                "npc_id": PRIMARY_NPC_ID,
                "file_offset": f"0x{PRIMARY_NPC_DESCRIPTOR_FILE:06X}",
                "snes_address": "$E4:F050",
                "fields": {
                    "gfx_selector": primary[0],
                    "assembly": primary[1],
                    "palette": primary[2],
                    "animation": primary[3],
                    "size": primary[4],
                },
                "sha256": sha256(primary),
            },
            "sole_same_geometry_palette_variant": {
                "npc_id": PALETTE_VARIANT_NPC_ID,
                "file_offset": f"0x{PALETTE_VARIANT_DESCRIPTOR_FILE:06X}",
                "snes_address": "$E4:F424",
                "fields": {
                    "gfx_selector": variant[0],
                    "assembly": variant[1],
                    "palette": variant[2],
                    "animation": variant[3],
                    "size": variant[4],
                },
                "sha256": sha256(variant),
                "only_differing_field": "palette",
            },
            "same_geometry_npc_ids": list(geometry_family_ids),
        },
        "sprite_packet": {
            "gfx_selector": GFX_SELECTOR,
            "pointer_entry_file_offset": (
                f"0x{GFX_POINTER_ENTRY_FILE:06X}"
            ),
            "pointer_entry_snes_address": "$E4:2072",
            "pointer_entry_sha256": sha256(pointer_entry),
            "pointer_alias_gfx_indexes": list(pointer_alias_indexes),
            "snes_pointer": f"${sprite_pointer:06X}",
            "file_offset": f"0x{sprite_file:06X}",
            "compressed_size": packet.compressed_size,
            "compressed_sha256": sha256(compressed),
            "decompressed_size": len(packet.data),
            "decompressed_sha256": sha256(packet.data),
            "tile_4bpp_count": len(packet.data)
            // corpus.BYTES_PER_4BPP_TILE,
            "backref_width_bits": packet.backref_width_bits,
            "addendum_count": packet.addendum_count,
        },
    }
    return metadata, packet.data


def decode_reference_tiles(
    packet_data: bytes,
) -> tuple[tuple[int, ...], ...]:
    _require_digest(
        packet_data,
        SPRITE_PACKET_DECOMPRESSED_SIZE,
        SPRITE_PACKET_DECOMPRESSED_SHA256,
        "graphics selector $26 decompressed packet",
    )
    tiles = tuple(
        gameplay.decode_snes_4bpp(
            packet_data[offset : offset + corpus.BYTES_PER_4BPP_TILE],
            8,
            8,
        )
        for offset in range(
            0, len(packet_data), corpus.BYTES_PER_4BPP_TILE
        )
    )
    excluded = sum(
        _visible_count(tile) <= TRIVIAL_VISIBLE_PIXEL_LIMIT for tile in tiles
    )
    counts = {
        "tile_count": len(tiles),
        "excluded_trivial_tile_count": excluded,
        "compared_tile_count": len(tiles) - excluded,
    }
    if counts != REFERENCE_EXPECTED_COUNTS:
        raise SchalaNpcOriginalityError(
            f"reference tile counts drifted: {counts}"
        )
    return tiles


def _gameplay_candidates(
) -> tuple[dict[str, tuple[int, int, Sequence[int]]], dict[str, Any]]:
    source_raw, source = _read_pinned_json(
        GAMEPLAY_SOURCE_PATH,
        GAMEPLAY_SOURCE_SIZE,
        GAMEPLAY_SOURCE_SHA256,
        "gameplay foundation source",
    )
    try:
        candidates, _ = pc_audit.packed_candidate_frames(source_raw, source)
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        raise SchalaNpcOriginalityError(
            f"gameplay foundation validation failed: {exc}"
        ) from exc
    return candidates, {
        "path": GAMEPLAY_SOURCE_REL.as_posix(),
        "size": len(source_raw),
        "sha256": sha256(source_raw),
        "source_classification": "original-hand-pixelled-target-grid",
    }


def _glass_candidates(
) -> tuple[dict[str, tuple[int, int, Sequence[int]]], dict[str, Any]]:
    source_raw, source = _read_pinned_json(
        GLASS_SOURCE_PATH,
        GLASS_SOURCE_SIZE,
        GLASS_SOURCE_SHA256,
        "Glass Focus source",
    )
    manifest_raw, manifest = _read_pinned_json(
        GLASS_MANIFEST_PATH,
        GLASS_MANIFEST_SIZE,
        GLASS_MANIFEST_SHA256,
        "Glass Focus manifest",
    )
    try:
        validated = focus.validate_source(source)
        source_report = focus.validation_report(source_raw, source)
        focus.verify_manifest_core(manifest, source_raw, source_report)
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        raise SchalaNpcOriginalityError(
            f"Glass Focus validation failed: {exc}"
        ) from exc
    candidates: dict[str, tuple[int, int, Sequence[int]]] = {}
    for asset_id in focus.FRAME_IDS:
        candidates[asset_id] = focus._parse_pixels(
            validated["frames"][asset_id], focus.FRAME_DIMENSIONS
        )
    for asset_id in focus.INSERT_IDS:
        candidates[asset_id] = focus._parse_pixels(
            validated["inserts"][asset_id], focus.INSERT_DIMENSIONS
        )
    if len(candidates) != len(focus.FRAME_IDS) + len(focus.INSERT_IDS):
        raise SchalaNpcOriginalityError(
            "Glass Focus candidate asset IDs are not unique"
        )
    return candidates, {
        "path": GLASS_SOURCE_REL.as_posix(),
        "size": len(source_raw),
        "sha256": sha256(source_raw),
        "source_classification": (
            "project-epoch-original-same-project-derived-multimedia-source"
        ),
        "manifest": {
            "path": GLASS_MANIFEST_REL.as_posix(),
            "size": len(manifest_raw),
            "sha256": sha256(manifest_raw),
        },
    }


def _visible_count(tile: Sequence[int]) -> int:
    return sum(pixel != 0 for pixel in tile)


def _framed_candidate_pixels_sha256(
    candidate_set: str,
    candidates: dict[str, tuple[int, int, Sequence[int]]],
) -> str:
    digest = hashlib.sha256()
    digest.update(
        b"ProjectEpoch/schala-npc-originality/candidate-v0\0"
        + candidate_set.encode("ascii")
        + b"\0"
    )
    for asset_id in sorted(candidates):
        width, height, pixels = candidates[asset_id]
        encoded_id = asset_id.encode("utf-8")
        digest.update(len(encoded_id).to_bytes(2, "little"))
        digest.update(encoded_id)
        digest.update(width.to_bytes(2, "little"))
        digest.update(height.to_bytes(2, "little"))
        try:
            digest.update(bytes(pixels))
        except ValueError as exc:
            raise SchalaNpcOriginalityError(
                f"{asset_id}: pixel index is outside byte range"
            ) from exc
    return digest.hexdigest()


def compare_candidate_set(
    candidate_set: str,
    candidates: dict[str, tuple[int, int, Sequence[int]]],
    reference_tiles: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Apply exact and palette-invariant H/V/HV comparisons in memory."""

    exact_index: dict[tuple[int, ...], set[int]] = defaultdict(set)
    pattern_index: dict[tuple[int, ...], set[int]] = defaultdict(set)
    excluded_reference = 0
    for reference_index, reference in enumerate(reference_tiles):
        reference_tuple = tuple(reference)
        if len(reference_tuple) != 64:
            raise SchalaNpcOriginalityError(
                "reference tile does not contain 64 pixels"
            )
        if _visible_count(reference_tuple) <= TRIVIAL_VISIBLE_PIXEL_LIMIT:
            excluded_reference += 1
            continue
        for variant in gameplay.tile_variants(reference_tuple):
            exact_index[variant].add(reference_index)
            pattern_index[pc_audit.visible_pattern(variant)].add(
                reference_index
            )

    tile_occurrences = 0
    excluded_candidates = 0
    exact_matches = 0
    pattern_matches = 0
    for asset_id in sorted(candidates):
        width, height, pixels = candidates[asset_id]
        try:
            tiles = gameplay.iter_tiles(pixels, width, height)
            for candidate in tiles:
                tile_occurrences += 1
                if _visible_count(candidate) <= TRIVIAL_VISIBLE_PIXEL_LIMIT:
                    excluded_candidates += 1
                    continue
                exact_matches += len(exact_index.get(candidate, ()))
                pattern_matches += len(
                    pattern_index.get(
                        pc_audit.visible_pattern(candidate), ()
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise SchalaNpcOriginalityError(
                f"{candidate_set}/{asset_id}: invalid candidate pixels"
            ) from exc

    counts = {
        "asset_count": len(candidates),
        "tile_occurrence_count": tile_occurrences,
        "excluded_trivial_tile_occurrence_count": excluded_candidates,
        "compared_tile_occurrence_count": (
            tile_occurrences - excluded_candidates
        ),
        "exact_index_match_count": exact_matches,
        "visible_pattern_match_count": pattern_matches,
        "framed_candidate_pixels_sha256": (
            _framed_candidate_pixels_sha256(candidate_set, candidates)
        ),
    }
    if excluded_reference != REFERENCE_EXPECTED_COUNTS[
        "excluded_trivial_tile_count"
    ]:
        raise SchalaNpcOriginalityError(
            "comparison reference exclusion count drifted"
        )
    require_expected_candidate_counts(candidate_set, counts)
    return counts


def require_expected_candidate_counts(
    candidate_set: str, counts: dict[str, Any]
) -> None:
    expected = CANDIDATE_EXPECTED_COUNTS.get(candidate_set)
    if expected is None:
        raise SchalaNpcOriginalityError(
            f"unapproved candidate set: {candidate_set}"
        )
    if counts != expected:
        raise SchalaNpcOriginalityError(
            f"{candidate_set} bounded originality counts drifted: {counts}"
        )


def build_report(rom_path: pathlib.Path) -> dict[str, Any]:
    behavior_dependencies = verify_behavior_dependencies()
    rom = rom_path.read_bytes()
    rom_identity = validate_canonical_rom(rom)
    location_chain = inspect_location_event_chain(rom)
    sprite_chain, packet_data = inspect_sprite_chain(rom)
    reference_tiles = decode_reference_tiles(packet_data)
    gameplay_candidates, gameplay_source = _gameplay_candidates()
    glass_candidates, glass_source = _glass_candidates()
    gameplay_counts = compare_candidate_set(
        "gameplay_foundation", gameplay_candidates, reference_tiles
    )
    glass_counts = compare_candidate_set(
        "glass_focus", glass_candidates, reference_tiles
    )

    tool_path = ROOT / TOOL_REL
    tool_raw = tool_path.read_bytes()
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": {
            "path": TOOL_REL.as_posix(),
            "version": TOOL_VERSION,
            "size": len(tool_raw),
            "sha256": sha256(tool_raw),
        },
        "reproduction": REPRODUCTION_COMMAND,
        "behavior_dependencies": behavior_dependencies,
        "canonical_rom": rom_identity,
        "semantic_identity": {
            "label": "Schala",
            "evidence": "documented",
            "anchor": {
                "repository": "Pseudoarc/jetsoftime",
                "commit": SEMANTIC_ANCHOR_COMMIT,
                "path": "sourcefiles/bossrandoevent.py",
                "lines": "188-201",
                "url": SEMANTIC_ANCHOR_URL,
                "scope": (
                    "The cited source identifies location $14E object $0F "
                    "as Schala."
                ),
            },
            "canonical_byte_chain_evidence": "verified-static",
            "runtime_semantic_identity_claimed": False,
        },
        "canonical_chain": {
            "evidence": "verified-static",
            "location_event": location_chain,
            "npc_graphics": sprite_chain,
        },
        "reference_scope": {
            "description": (
                "The 79 decoded 4bpp tile occurrences in only graphics "
                "selector $26, reached through the pinned location $14E, "
                "event $0CE, object $0F, NPC $09 chain."
            ),
            **REFERENCE_EXPECTED_COUNTS,
            "decompressed_packet_sha256": (
                SPRITE_PACKET_DECOMPRESSED_SHA256
            ),
            "coverage_limit": (
                "This is not a global NPC/enemy-corpus audit and makes no "
                "claim about near matches, silhouettes, animation, assembly "
                "layout, palettes, or runtime semantic identity."
            ),
        },
        "candidate_sets": {
            "gameplay_foundation": {
                "canonical_source": gameplay_source,
                "asset_ids": sorted(gameplay_candidates),
                "counts": gameplay_counts,
            },
            "glass_focus": {
                "canonical_source": glass_source,
                "asset_ids": sorted(glass_candidates),
                "counts": glass_counts,
            },
        },
        "comparison_policy": {
            "transforms": list(TRANSFORMS),
            "exact_index_comparison": True,
            "visible_pattern_comparison": (
                "Non-zero palette labels are canonicalized by first use; "
                "transparent index zero remains fixed."
            ),
            "trivial_exclusion": (
                "Candidate and reference tile occurrences with at most two "
                "non-zero pixels are counted and excluded from comparison."
            ),
            "interpretation": (
                "Zero matches is bounded evidence only for the pinned "
                "selector-$26 packet and these exact Project Epoch sources."
            ),
        },
        "claims": {
            "selector_26_exact_or_palette_pattern_matches_found": False,
            "global_npc_originality_claimed": False,
            "near_match_analysis_claimed": False,
            "silhouette_analysis_claimed": False,
            "animation_analysis_claimed": False,
            "assembly_layout_analysis_claimed": False,
            "runtime_semantic_identity_claimed": False,
        },
        "files_emitted": False,
        "copyright_boundary": (
            "Only bounded addresses, field values, sizes, counts, and hashes "
            "are serialized. No packet bytes, decoded reference pixels, "
            "palettes, images, or candidate pixel data are serialized or "
            "written."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="Explicit path to the pinned clean headerless US Rev0 ROM.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_report(args.rom)
    except (OSError, SchalaNpcOriginalityError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(canonical_report_bytes(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
