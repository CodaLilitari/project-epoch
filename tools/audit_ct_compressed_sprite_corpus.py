#!/usr/bin/env python3
"""Audit Chrono Trigger's descriptor-reachable compressed sprite corpus.

The command accepts only a user-supplied, headerless US Rev0 ROM.  It hash
gates that ROM before parsing, reads the sprite pointer and descriptor tables,
independently decodes the bounded compressed catalog, and emits metadata-only
JSON to stdout.  It never writes a ROM, decoded bytes, tiles, or images.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import struct
import sys
from collections.abc import Sequence
from typing import Any


TOOL_VERSION = "0.1.0"
REPORT_SCHEMA_VERSION = 1

CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

GFX_POINTER_TABLE_FILE = 0x242000
GFX_POINTER_COUNT = 0x100
GFX_POINTER_WIDTH = 3
GFX_POINTER_TABLE_SIZE = GFX_POINTER_COUNT * GFX_POINTER_WIDTH
GFX_POINTER_TABLE_SHA256 = (
    "a4929e157e37543fee84c0ad87a8dd3c"
    "d7e23e864648401fdbd58652b16afaa4"
)

NPC_DESCRIPTOR_TABLE_FILE = 0x24F023
NPC_DESCRIPTOR_COUNT = 0x100
NPC_DESCRIPTOR_WIDTH = 5
NPC_DESCRIPTOR_TABLE_SIZE = NPC_DESCRIPTOR_COUNT * NPC_DESCRIPTOR_WIDTH
NPC_DESCRIPTOR_TABLE_SHA256 = (
    "17ae540728c200cf02d60943b8ccdae87"
    "edc8cb425e603a24343c078732e3b8a"
)

ENEMY_DESCRIPTOR_TABLE_FILE = 0x24F600
ENEMY_DESCRIPTOR_COUNT = 0x100
ENEMY_DESCRIPTOR_WIDTH = 10
ENEMY_DESCRIPTOR_TABLE_SIZE = (
    ENEMY_DESCRIPTOR_COUNT * ENEMY_DESCRIPTOR_WIDTH
)
ENEMY_DESCRIPTOR_TABLE_SHA256 = (
    "347a3f7202e02581deca02d1fbabdb34"
    "e1fa5ed4548ab0731fa4af9a852fb287"
)
NORMAL_ENEMY_DESCRIPTOR_TABLE_SHA256 = (
    "6f029d2969267d7a94367f68144a6ccc"
    "02af03e4005bfc0f9a4030fbd989a35a"
)
DIRECT_ENEMY_DESCRIPTOR_TABLE_SHA256 = (
    "273b7449cca59c3bce3e42af2c9a112b"
    "a3dcf5cc921870eb156c1af20b38e503"
)

DESCRIPTOR_SELECTOR_OFFSET = 0
NORMAL_ENEMY_ID_END_EXCLUSIVE = 0xF8
DIRECT_ENEMY_IDS = tuple(range(0xF8, 0x100))
EXPECTED_DIRECT_ENEMY_SELECTORS = (0x03, 0x06, 0x06, 0x06, 0, 0, 0, 0)
DIRECT_ENEMY_SELECTOR_SHA256 = (
    "174cc6b1e3e2761d4a89171aec4272f8"
    "bcd69e7cd5bf5720902373954c0c7aac"
)
DESCRIPTOR_SELECTED_SELECTOR_VECTOR_SHA256 = (
    "97dc46cf43944d991b421162d2d7937a"
    "1c6fbb2a48061ff4d487b989586a6c53"
)

# These are explicit architecture sets, not classifications inferred from
# pointer-table position.  The first set is the seven pinned playable-PC raw
# graphics sources.  The catalog set is accepted only after every member
# independently passes the HiROM pointer and C3 packet checks below.
RAW_PC_GFX_INDEXES = tuple(range(0x07))
COMPRESSED_CATALOG_INDEXES = tuple(range(0x07, 0xF8))
NULL_POINTER_INDEXES = tuple(range(0xF8, 0x100))
EXPECTED_CATALOG_ONLY_INDEXES = (0x47, 0x4A, 0xCC, 0xE5)
EXPECTED_UNSELECTED_INDEXES = (
    *RAW_PC_GFX_INDEXES,
    *EXPECTED_CATALOG_ONLY_INDEXES,
    *NULL_POINTER_INDEXES,
)

EXPECTED_CATALOG_PACKET_COUNT = 241
EXPECTED_CATALOG_DECOMPRESSED_BYTES = 699_872
EXPECTED_CATALOG_TILE_COUNT = 21_871
EXPECTED_CATALOG_COMPRESSED_BYTES = 540_847
EXPECTED_CATALOG_MIN_DECOMPRESSED = 128
EXPECTED_CATALOG_MAX_DECOMPRESSED = 23_776
EXPECTED_CATALOG_MIN_COMPRESSED = 39
EXPECTED_CATALOG_MAX_COMPRESSED = 18_466
EXPECTED_CATALOG_ONE_ADDENDUM = 211
EXPECTED_CATALOG_ZERO_ADDENDUM = 30
EXPECTED_CATALOG_SHA256 = (
    "01fe041352872a2efd8ba554722c71e71"
    "b9b20f70a32ee2ef33921286df2e418"
)

EXPECTED_SELECTED_PACKET_COUNT = 237
EXPECTED_SELECTED_DECOMPRESSED_BYTES = 699_200
EXPECTED_SELECTED_TILE_COUNT = 21_850
EXPECTED_SELECTED_COMPRESSED_BYTES = 540_276
EXPECTED_SELECTED_ONE_ADDENDUM = 207
EXPECTED_SELECTED_ZERO_ADDENDUM = 30
EXPECTED_SELECTED_SHA256 = (
    "87732136b365151b9d71d955c9bf196c"
    "f655df69ba05c1bb12b5c94378a0ac65"
)

BYTES_PER_4BPP_TILE = 0x20
MAX_DECOMPRESSED_SIZE = 0x10000
CORPUS_HASH_DOMAIN = b"ProjectEpoch/ct-compressed-sprite-corpus/v0\0"

DISASSEMBLY_COMMIT = "eeae27acdb6565e96d1d796a3d60792c250c0aa1"
DISASSEMBLY_REFERENCES = (
    {
        "path": "references/ct_disassembly/bank_C0.asm",
        "sha256": (
            "b5b209cd03ae430f095482a429798ee3"
            "600d97af3774841c069d8f9a071140b8"
        ),
        "scope": [
            "$C0:4590-$C0:46DE NPC descriptor load and compressed path",
            "$C0:46DF-$C0:485F enemy descriptor load, normal compressed "
            "path, and $F8-$FF direct/raw branch",
        ],
    },
    {
        "path": "references/ct_disassembly/bank_C3.asm",
        "sha256": (
            "11aa3492823ef8096961e1c129e4a5ee"
            "83418f6d1e19584455ff894d919ba134"
        ),
        "scope": [
            "$C3:0557-$C3:08B2 graphics decompressor entry, variants, "
            "and return"
        ],
    },
    {
        "path": "references/ct_disassembly/bank_E4.asm",
        "sha256": (
            "160bdd0ef4791f81a468ca0088f65a79"
            "fa6fbd638584fece50d6735950b29fda"
        ),
        "scope": [
            "$E4:F023 NPCSpriteData5Bytes label",
            "$E4:F600 EnemySpriteData10Bytes label",
            "$E4:FFE0 PC/NPC/enemy graphics-table base indirection",
        ],
    },
)


class AuditError(RuntimeError):
    """Raised when the canonical corpus fails a structural invariant."""


@dataclasses.dataclass(frozen=True)
class DecodedPacket:
    """One in-memory C3 decode; decoded bytes are never serialized."""

    data: bytes
    compressed_size: int
    backref_width_bits: int
    addendum_count: int
    segment_count: int


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_u16_le(data: bytes, offset: int, label: str) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise AuditError(f"{label}: truncated 16-bit read at {offset:#x}")
    return int.from_bytes(data[offset : offset + 2], "little")


def _read_u24_le(data: bytes, offset: int, label: str) -> int:
    if offset < 0 or offset + 3 > len(data):
        raise AuditError(f"{label}: truncated 24-bit read at {offset:#x}")
    return int.from_bytes(data[offset : offset + 3], "little")


def _exact_slice(data: bytes, start: int, size: int, label: str) -> bytes:
    if start < 0 or size < 0 or start + size > len(data):
        raise AuditError(f"{label}: range exceeds input")
    result = data[start : start + size]
    if len(result) != size:
        raise AuditError(f"{label}: short range")
    return result


def snes_hirom_to_file(pointer: int) -> int:
    """Map a canonical $C0-$FF HiROM pointer into a headerless ROM."""

    if not 0xC00000 <= pointer <= 0xFFFFFF:
        raise AuditError(f"pointer outside canonical HiROM: ${pointer:06X}")
    return pointer & 0x3FFFFF


def _require_source_bank_span(
    source: bytes,
    packet_start: int,
    offset: int,
    size: int,
    label: str,
) -> None:
    """Reject source reads that leave the packet's fixed 64 KiB CPU bank."""

    if offset < 0 or size < 0 or offset + size > len(source):
        raise AuditError(f"{label}: truncated source at {offset:#x}")
    bank_start = packet_start & ~0xFFFF
    bank_end = bank_start + 0x10000
    if not bank_start <= offset or offset + size > bank_end:
        raise AuditError(f"{label}: compressed source crosses a CPU bank")


def decode_c3_sprite_packet(source: bytes, start: int) -> DecodedPacket:
    """Decode one tile-aligned C3 graphics packet without extent inference.

    The initial segment boundary marker selects the 12- or 11-bit backref
    layout.  Control bits are consumed least-significant bit first.  A
    nonzero low-six-bit marker count introduces an addendum and gives the
    number of controls in its first (possibly partial) group.
    """

    _require_source_bank_span(source, start, start, 2, "packet header")
    main_length = _read_u16_le(source, start, "packet header")
    cursor = start + 2
    segment_end = cursor + main_length
    _require_source_bank_span(
        source,
        start,
        segment_end,
        1,
        "initial segment boundary",
    )

    initial_marker = source[segment_end]
    backref_width_bits = 11 if initial_marker & 0xC0 else 12
    distance_mask = 0x07FF if backref_width_bits == 11 else 0x0FFF
    length_shift = 11 if backref_width_bits == 11 else 12

    output = bytearray()
    addendum_count = 0
    segment_count = 1
    group_control_count = 8
    previous_boundary = segment_end

    while True:
        if cursor > segment_end:
            raise AuditError("compressed token crossed a segment boundary")

        if cursor == segment_end:
            _require_source_bank_span(
                source,
                start,
                cursor,
                1,
                "segment boundary marker",
            )
            marker = source[cursor]
            partial_count = marker & 0x3F
            if partial_count == 0:
                if len(output) % BYTES_PER_4BPP_TILE:
                    raise AuditError(
                        "decompressed sprite packet is not 0x20-byte aligned"
                    )
                return DecodedPacket(
                    data=bytes(output),
                    compressed_size=cursor - start + 1,
                    backref_width_bits=backref_width_bits,
                    addendum_count=addendum_count,
                    segment_count=segment_count,
                )

            _require_source_bank_span(
                source,
                start,
                cursor,
                3,
                "addendum boundary header",
            )
            new_end = start + _read_u16_le(
                source,
                cursor + 1,
                "addendum boundary",
            )
            addendum_start = cursor + 3
            if new_end <= previous_boundary or new_end <= addendum_start:
                raise AuditError("nonmonotonic addendum boundary")
            _require_source_bank_span(
                source,
                start,
                new_end,
                1,
                "addendum segment boundary",
            )
            cursor = addendum_start
            segment_end = new_end
            previous_boundary = new_end
            group_control_count = partial_count
            addendum_count += 1
            segment_count += 1

        _require_source_bank_span(
            source,
            start,
            cursor,
            1,
            "control byte",
        )
        if cursor >= segment_end:
            raise AuditError("truncated control group at segment boundary")
        control = source[cursor]
        cursor += 1
        controls_in_group = group_control_count
        group_control_count = 8
        if control == 0 and controls_in_group != 8:
            raise AuditError(
                "zero control byte cannot encode a partial addendum group"
            )

        for control_index in range(controls_in_group):
            is_backref = (
                control_index < 8
                and bool(control & (1 << control_index))
            )
            if is_backref:
                if cursor + 2 > segment_end:
                    raise AuditError("truncated back-reference token")
                _require_source_bank_span(
                    source,
                    start,
                    cursor,
                    2,
                    "back-reference token",
                )
                token = _read_u16_le(
                    source,
                    cursor,
                    "back-reference token",
                )
                cursor += 2
                distance = token & distance_mask
                length = (token >> length_shift) + 3
                if distance == 0:
                    raise AuditError("zero back-reference distance")
                if distance > len(output):
                    raise AuditError("forward back-reference distance")
                if len(output) + length > MAX_DECOMPRESSED_SIZE:
                    raise AuditError("decompressed packet exceeds 0x10000")
                for _ in range(length):
                    output.append(output[-distance])
            else:
                if cursor >= segment_end:
                    raise AuditError("truncated literal token")
                _require_source_bank_span(
                    source,
                    start,
                    cursor,
                    1,
                    "literal token",
                )
                if len(output) >= MAX_DECOMPRESSED_SIZE:
                    raise AuditError("decompressed packet exceeds 0x10000")
                output.append(source[cursor])
                cursor += 1


def validate_canonical_rom(rom: bytes) -> dict[str, Any]:
    """Hash gate the complete ROM before any table parsing occurs."""

    identity = {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha1": sha1(rom),
        "sha256": sha256(rom),
    }
    if len(rom) != CANONICAL_ROM_SIZE:
        raise AuditError(
            "canonical ROM size mismatch: "
            f"expected 0x{CANONICAL_ROM_SIZE:X}, got 0x{len(rom):X}"
        )
    if identity["sha1"] != CANONICAL_ROM_SHA1:
        raise AuditError("canonical ROM SHA-1 mismatch")
    if identity["sha256"] != CANONICAL_ROM_SHA256:
        raise AuditError("canonical ROM SHA-256 mismatch")
    return identity


def _read_tables(
    rom: bytes,
) -> tuple[list[int], list[int], list[int], dict[str, Any]]:
    pointer_bytes = _exact_slice(
        rom,
        GFX_POINTER_TABLE_FILE,
        GFX_POINTER_TABLE_SIZE,
        "graphics pointer table",
    )
    npc_bytes = _exact_slice(
        rom,
        NPC_DESCRIPTOR_TABLE_FILE,
        NPC_DESCRIPTOR_TABLE_SIZE,
        "NPC descriptor table",
    )
    enemy_bytes = _exact_slice(
        rom,
        ENEMY_DESCRIPTOR_TABLE_FILE,
        ENEMY_DESCRIPTOR_TABLE_SIZE,
        "enemy descriptor table",
    )

    actual_hashes = (
        sha256(pointer_bytes),
        sha256(npc_bytes),
        sha256(enemy_bytes),
    )
    expected_hashes = (
        GFX_POINTER_TABLE_SHA256,
        NPC_DESCRIPTOR_TABLE_SHA256,
        ENEMY_DESCRIPTOR_TABLE_SHA256,
    )
    if actual_hashes != expected_hashes:
        raise AuditError("canonical sprite table hash drift")

    pointers = [
        _read_u24_le(
            pointer_bytes,
            index * GFX_POINTER_WIDTH,
            f"graphics pointer {index:#04x}",
        )
        for index in range(GFX_POINTER_COUNT)
    ]
    npc_selectors = [
        npc_bytes[index * NPC_DESCRIPTOR_WIDTH + DESCRIPTOR_SELECTOR_OFFSET]
        for index in range(NPC_DESCRIPTOR_COUNT)
    ]
    enemy_selectors = [
        enemy_bytes[
            index * ENEMY_DESCRIPTOR_WIDTH + DESCRIPTOR_SELECTOR_OFFSET
        ]
        for index in range(ENEMY_DESCRIPTOR_COUNT)
    ]
    normal_enemy_bytes = enemy_bytes[
        : NORMAL_ENEMY_ID_END_EXCLUSIVE * ENEMY_DESCRIPTOR_WIDTH
    ]
    direct_enemy_bytes = enemy_bytes[
        NORMAL_ENEMY_ID_END_EXCLUSIVE * ENEMY_DESCRIPTOR_WIDTH :
    ]
    if sha256(normal_enemy_bytes) != NORMAL_ENEMY_DESCRIPTOR_TABLE_SHA256:
        raise AuditError("normal-enemy descriptor partition hash drift")
    if sha256(direct_enemy_bytes) != DIRECT_ENEMY_DESCRIPTOR_TABLE_SHA256:
        raise AuditError("direct-enemy descriptor partition hash drift")

    null_indexes = tuple(
        index for index, pointer in enumerate(pointers) if pointer == 0
    )
    if null_indexes != NULL_POINTER_INDEXES:
        raise AuditError("graphics pointer null-index set drift")

    hirom_indexes = []
    for index, pointer in enumerate(pointers):
        if pointer == 0:
            continue
        snes_hirom_to_file(pointer)
        hirom_indexes.append(index)
    if tuple(hirom_indexes) != tuple(range(0xF8)):
        raise AuditError("graphics pointer HiROM-index set drift")

    table_report = {
        "graphics_pointers": {
            "file_offset": GFX_POINTER_TABLE_FILE,
            "snes_range": "$E4:2000-$E4:22FF",
            "entry_count": GFX_POINTER_COUNT,
            "entry_width": GFX_POINTER_WIDTH,
            "byte_count": GFX_POINTER_TABLE_SIZE,
            "sha256": actual_hashes[0],
            "non_pc_tail_first_index": 7,
            "non_pc_tail_entry_count": 249,
            "valid_hirom_pointer_count": len(hirom_indexes),
            "null_pointer_indexes": list(null_indexes),
        },
        "npc_descriptors": {
            "file_offset": NPC_DESCRIPTOR_TABLE_FILE,
            "snes_range": "$E4:F023-$E4:F522",
            "entry_count": NPC_DESCRIPTOR_COUNT,
            "entry_width": NPC_DESCRIPTOR_WIDTH,
            "selector_offset": DESCRIPTOR_SELECTOR_OFFSET,
            "byte_count": NPC_DESCRIPTOR_TABLE_SIZE,
            "sha256": actual_hashes[1],
        },
        "enemy_descriptors": {
            "file_offset": ENEMY_DESCRIPTOR_TABLE_FILE,
            "snes_range": "$E4:F600-$E4:FFFF",
            "entry_count": ENEMY_DESCRIPTOR_COUNT,
            "entry_width": ENEMY_DESCRIPTOR_WIDTH,
            "selector_offset": DESCRIPTOR_SELECTOR_OFFSET,
            "byte_count": ENEMY_DESCRIPTOR_TABLE_SIZE,
            "sha256": actual_hashes[2],
            "normal_compressed_id_range": "$00-$F7",
            "normal_compressed_record_count": 248,
            "normal_compressed_snes_range": "$E4:F600-$E4:FFAF",
            "normal_compressed_sha256": sha256(normal_enemy_bytes),
            "direct_raw_id_range": "$F8-$FF",
            "direct_raw_record_count": 8,
            "direct_raw_snes_range": "$E4:FFB0-$E4:FFFF",
            "direct_raw_sha256": sha256(direct_enemy_bytes),
        },
    }
    return pointers, npc_selectors, enemy_selectors, table_report


def _selector_aliases(
    npc_selectors: Sequence[int],
    enemy_selectors: Sequence[int],
) -> dict[int, dict[str, list[int]]]:
    aliases = {
        index: {"npc_ids": [], "normal_enemy_ids": []}
        for index in COMPRESSED_CATALOG_INDEXES
    }
    for npc_id, selector in enumerate(npc_selectors):
        if selector in aliases:
            aliases[selector]["npc_ids"].append(npc_id)
    for enemy_id, selector in enumerate(
        enemy_selectors[:NORMAL_ENEMY_ID_END_EXCLUSIVE]
    ):
        if selector in aliases:
            aliases[selector]["normal_enemy_ids"].append(enemy_id)
    return aliases


def _framed_corpus_sha256(
    decoded_rows: Sequence[tuple[int, DecodedPacket]],
) -> str:
    digest = hashlib.sha256()
    digest.update(CORPUS_HASH_DOMAIN)
    for gfx_index, packet in decoded_rows:
        digest.update(struct.pack("<BI", gfx_index, len(packet.data)))
        digest.update(packet.data)
    return digest.hexdigest()


def _partition_summary(
    rows: Sequence[tuple[int, DecodedPacket]],
) -> dict[str, Any]:
    if not rows:
        raise AuditError("empty decoded corpus partition")
    decoded_sizes = [len(packet.data) for _, packet in rows]
    compressed_sizes = [packet.compressed_size for _, packet in rows]
    addenda = [packet.addendum_count for _, packet in rows]
    widths = [packet.backref_width_bits for _, packet in rows]
    return {
        "packet_count": len(rows),
        "compressed_byte_count": sum(compressed_sizes),
        "minimum_compressed_size": min(compressed_sizes),
        "maximum_compressed_size": max(compressed_sizes),
        "decompressed_byte_count": sum(decoded_sizes),
        "tile_4bpp_count": sum(decoded_sizes) // BYTES_PER_4BPP_TILE,
        "minimum_decompressed_size": min(decoded_sizes),
        "maximum_decompressed_size": max(decoded_sizes),
        "zero_addendum_packet_count": addenda.count(0),
        "one_addendum_packet_count": addenda.count(1),
        "other_addendum_packet_count": sum(
            count not in (0, 1) for count in addenda
        ),
        "backref_12_bit_packet_count": widths.count(12),
        "backref_11_bit_packet_count": widths.count(11),
        "source_bank_crossing_count": 0,
        "framed_decoded_corpus_sha256": _framed_corpus_sha256(rows),
    }


def _validate_expected_summaries(
    catalog: dict[str, Any],
    selected: dict[str, Any],
) -> None:
    expected_catalog = {
        "packet_count": EXPECTED_CATALOG_PACKET_COUNT,
        "compressed_byte_count": EXPECTED_CATALOG_COMPRESSED_BYTES,
        "minimum_compressed_size": EXPECTED_CATALOG_MIN_COMPRESSED,
        "maximum_compressed_size": EXPECTED_CATALOG_MAX_COMPRESSED,
        "decompressed_byte_count": EXPECTED_CATALOG_DECOMPRESSED_BYTES,
        "tile_4bpp_count": EXPECTED_CATALOG_TILE_COUNT,
        "minimum_decompressed_size": EXPECTED_CATALOG_MIN_DECOMPRESSED,
        "maximum_decompressed_size": EXPECTED_CATALOG_MAX_DECOMPRESSED,
        "zero_addendum_packet_count": EXPECTED_CATALOG_ZERO_ADDENDUM,
        "one_addendum_packet_count": EXPECTED_CATALOG_ONE_ADDENDUM,
        "other_addendum_packet_count": 0,
        "backref_12_bit_packet_count": EXPECTED_CATALOG_PACKET_COUNT,
        "backref_11_bit_packet_count": 0,
        "source_bank_crossing_count": 0,
        "framed_decoded_corpus_sha256": EXPECTED_CATALOG_SHA256,
    }
    expected_selected = {
        "packet_count": EXPECTED_SELECTED_PACKET_COUNT,
        "compressed_byte_count": EXPECTED_SELECTED_COMPRESSED_BYTES,
        "minimum_compressed_size": EXPECTED_CATALOG_MIN_COMPRESSED,
        "maximum_compressed_size": EXPECTED_CATALOG_MAX_COMPRESSED,
        "decompressed_byte_count": EXPECTED_SELECTED_DECOMPRESSED_BYTES,
        "tile_4bpp_count": EXPECTED_SELECTED_TILE_COUNT,
        "minimum_decompressed_size": EXPECTED_CATALOG_MIN_DECOMPRESSED,
        "maximum_decompressed_size": EXPECTED_CATALOG_MAX_DECOMPRESSED,
        "zero_addendum_packet_count": EXPECTED_SELECTED_ZERO_ADDENDUM,
        "one_addendum_packet_count": EXPECTED_SELECTED_ONE_ADDENDUM,
        "other_addendum_packet_count": 0,
        "backref_12_bit_packet_count": EXPECTED_SELECTED_PACKET_COUNT,
        "backref_11_bit_packet_count": 0,
        "source_bank_crossing_count": 0,
        "framed_decoded_corpus_sha256": EXPECTED_SELECTED_SHA256,
    }
    if catalog != expected_catalog:
        raise AuditError("compressed catalog summary drift")
    if selected != expected_selected:
        raise AuditError("descriptor-selected corpus summary drift")


def audit_rom_bytes(rom: bytes) -> dict[str, Any]:
    """Return a deterministic metadata report from an already-read ROM."""

    rom_identity = validate_canonical_rom(rom)
    pointers, npc_selectors, enemy_selectors, tables = _read_tables(rom)

    direct_selectors = tuple(
        enemy_selectors[enemy_id] for enemy_id in DIRECT_ENEMY_IDS
    )
    if direct_selectors != EXPECTED_DIRECT_ENEMY_SELECTORS:
        raise AuditError("direct/raw enemy selector sequence drift")
    if sha256(bytes(direct_selectors)) != DIRECT_ENEMY_SELECTOR_SHA256:
        raise AuditError("direct/raw enemy selector hash drift")

    selected_selector_vector = bytes(
        [*npc_selectors, *enemy_selectors[:NORMAL_ENEMY_ID_END_EXCLUSIVE]]
    )
    if (
        sha256(selected_selector_vector)
        != DESCRIPTOR_SELECTED_SELECTOR_VECTOR_SHA256
    ):
        raise AuditError("descriptor-selected selector-vector hash drift")

    selected_indexes = tuple(
        sorted(
            set(npc_selectors)
            | set(enemy_selectors[:NORMAL_ENEMY_ID_END_EXCLUSIVE])
        )
    )
    catalog_set = set(COMPRESSED_CATALOG_INDEXES)
    if not set(selected_indexes) <= catalog_set:
        conflicts = sorted(set(selected_indexes) - catalog_set)
        raise AuditError(
            "compressed selector conflicts with direct/raw index: "
            + ",".join(f"{index:02X}" for index in conflicts)
        )
    if set(selected_indexes) & set(RAW_PC_GFX_INDEXES):
        raise AuditError("compressed selector conflicts with raw PC index")
    if set(selected_indexes) & set(direct_selectors):
        raise AuditError("compressed selector conflicts with direct enemy source")

    catalog_only_indexes = tuple(
        sorted(catalog_set - set(selected_indexes))
    )
    if catalog_only_indexes != EXPECTED_CATALOG_ONLY_INDEXES:
        raise AuditError("catalog-only compressed index set drift")
    unselected_indexes = tuple(
        index for index in range(0x100) if index not in selected_indexes
    )
    if unselected_indexes != EXPECTED_UNSELECTED_INDEXES:
        raise AuditError("descriptor-unselected graphics index set drift")
    if len(selected_indexes) != EXPECTED_SELECTED_PACKET_COUNT:
        raise AuditError("descriptor-selected graphics index count drift")

    aliases = _selector_aliases(npc_selectors, enemy_selectors)
    if (
        sum(len(row["npc_ids"]) for row in aliases.values())
        != NPC_DESCRIPTOR_COUNT
    ):
        raise AuditError("NPC selector alias accounting is incomplete")
    if (
        sum(len(row["normal_enemy_ids"]) for row in aliases.values())
        != NORMAL_ENEMY_ID_END_EXCLUSIVE
    ):
        raise AuditError("normal-enemy selector alias accounting is incomplete")

    decoded_rows: list[tuple[int, DecodedPacket]] = []
    packet_report_rows: list[dict[str, Any]] = []
    selected_pointer_values: list[int] = []
    catalog_pointer_values: list[int] = []
    for gfx_index in COMPRESSED_CATALOG_INDEXES:
        pointer = pointers[gfx_index]
        file_offset = snes_hirom_to_file(pointer)
        packet = decode_c3_sprite_packet(rom, file_offset)
        decoded_rows.append((gfx_index, packet))
        catalog_pointer_values.append(pointer)
        descriptor_selected = gfx_index in selected_indexes
        if descriptor_selected:
            selected_pointer_values.append(pointer)
        packet_report_rows.append(
            {
                "gfx_index": gfx_index,
                "snes_pointer": f"${pointer:06X}",
                "file_offset": file_offset,
                "compressed_size": packet.compressed_size,
                "decompressed_size": len(packet.data),
                "tile_4bpp_count": (
                    len(packet.data) // BYTES_PER_4BPP_TILE
                ),
                "backref_width_bits": packet.backref_width_bits,
                "addendum_count": packet.addendum_count,
                "segment_count": packet.segment_count,
                "decoded_sha256": sha256(packet.data),
                "descriptor_selected": descriptor_selected,
                "selector_aliases": aliases[gfx_index],
            }
        )

    if len(set(catalog_pointer_values)) != len(catalog_pointer_values):
        raise AuditError("compressed catalog pointer alias detected")
    if len(set(selected_pointer_values)) != len(selected_pointer_values):
        raise AuditError("descriptor-selected pointer alias detected")
    raw_pointer_values = {pointers[index] for index in RAW_PC_GFX_INDEXES}
    if set(catalog_pointer_values) & raw_pointer_values:
        raise AuditError("compressed pointer aliases a raw PC graphics source")

    selected_rows = [
        row for row in decoded_rows if row[0] in selected_indexes
    ]
    catalog_summary = _partition_summary(decoded_rows)
    selected_summary = _partition_summary(selected_rows)
    _validate_expected_summaries(catalog_summary, selected_summary)

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": {
            "path": "tools/audit_ct_compressed_sprite_corpus.py",
            "version": TOOL_VERSION,
            "cli_contract": "required --rom only; metadata JSON to stdout",
            "writes_files": False,
        },
        "reproduction": {
            "command": (
                "python tools/audit_ct_compressed_sprite_corpus.py "
                "--rom <canonical-headerless-us-rev0.sfc>"
            ),
            "expected_stdout_reference": (
                "references/ct_compressed_sprite_corpus_v0.json"
            ),
            "comparison": "byte-for-byte UTF-8/LF stdout comparison",
        },
        "evidence": {
            "level": "verified-static",
            "claim": (
                "Canonical table and decoder evidence for the structurally "
                "valid compressed graphics catalog $07-$F7, plus its "
                "descriptor-selected field-NPC and normal-enemy subset."
            ),
            "selection_basis": (
                "NPC descriptor byte +0 for all $100 NPC records and enemy "
                "descriptor byte +0 for IDs $00-$F7. Enemy IDs $F8-$FF are "
                "the separately proved direct/raw branch."
            ),
            "catalog_basis": (
                "Every index $07-$F7 independently passed the pinned HiROM "
                "pointer and fail-closed C3 packet decoder; membership is "
                "not inferred solely from table position."
            ),
        },
        "canonical_rom": rom_identity,
        "tables": tables,
        "disassembly": {
            "repository": "https://github.com/dscotton/ct_disassembly",
            "commit": DISASSEMBLY_COMMIT,
            "references": list(DISASSEMBLY_REFERENCES),
        },
        "decoder_contract": {
            "initial_boundary_selects_backref_width": True,
            "control_bit_order": "least-significant bit first",
            "backref_distance_widths": [12, 11],
            "backref_length_rule": "encoded high bits + 3",
            "addendum_end_rule": (
                "little-endian boundary offset relative to packet start"
            ),
            "maximum_decompressed_size": MAX_DECOMPRESSED_SIZE,
            "required_output_alignment": BYTES_PER_4BPP_TILE,
            "source_bank_crossing_allowed": False,
            "extent_inferred_from_next_pointer": False,
            "aggregate_hash_framing": (
                "SHA-256(domain || repeated(index_u8 || "
                "decoded_length_u32le || decoded_bytes)), ascending index"
            ),
            "aggregate_hash_domain_ascii_with_nul": (
                "ProjectEpoch/ct-compressed-sprite-corpus/v0\\0"
            ),
        },
        "selection": {
            "raw_pc_gfx_indexes": list(RAW_PC_GFX_INDEXES),
            "compressed_catalog_index_range": "$07-$F7",
            "catalog_only_unselected_gfx_indexes": list(
                catalog_only_indexes
            ),
            "catalog_only_status": (
                "not selected by the audited NPC and enemy-$00-$F7 "
                "descriptors; not proof of global non-use"
            ),
            "all_descriptor_unselected_gfx_indexes": list(
                unselected_indexes
            ),
            "direct_raw_enemy_descriptors": [
                {
                    "enemy_id": enemy_id,
                    "gfx_selector": selector,
                    "path": "direct/raw; excluded from compressed corpus",
                }
                for enemy_id, selector in zip(
                    DIRECT_ENEMY_IDS,
                    direct_selectors,
                    strict=True,
                )
            ],
            "descriptor_selected_selector_vector_byte_count": len(
                selected_selector_vector
            ),
            "descriptor_selected_selector_vector_sha256": sha256(
                selected_selector_vector
            ),
            "direct_raw_enemy_selector_byte_count": len(direct_selectors),
            "direct_raw_enemy_selector_sha256": sha256(
                bytes(direct_selectors)
            ),
            "direct_raw_branch_operand": (
                "enemy/script ID at $C0:477A, not graphics-table index"
            ),
            "pointer_slots_f8_ff_status": (
                "separately null and unreferenced by this descriptor audit"
            ),
            "npc_alias_count": NPC_DESCRIPTOR_COUNT,
            "normal_enemy_alias_count": NORMAL_ENEMY_ID_END_EXCLUSIVE,
            "selected_gfx_index_count": len(selected_indexes),
            "selected_unique_pointer_count": len(
                set(selected_pointer_values)
            ),
            "selected_pointer_alias_count": 0,
            "catalog_unique_pointer_count": len(
                set(catalog_pointer_values)
            ),
            "catalog_pointer_alias_count": 0,
        },
        "corpus": {
            "conservative_compressed_catalog": catalog_summary,
            "descriptor_selected_subset": selected_summary,
            "packets": packet_report_rows,
        },
        "limitations": [
            (
                "This report does not identify Schala, a playable PC $07 "
                "sprite, or any other new character identity."
            ),
            (
                "This report makes no sprite-originality or similarity "
                "finding. The 241-packet catalog is the conservative future "
                "comparison corpus."
            ),
            (
                "The descriptor-selected subset is bounded to field NPC "
                "records and normal enemy IDs $00-$F7; it is not a special, "
                "menu, battle-global, or engine-global sprite inventory."
            ),
            (
                "Static decoding is not runtime proof and approves no hook, "
                "allocation, ROM write, patch, or production binding."
            ),
            (
                "Catalog-only indexes $47, $4A, $CC, and $E5 are not selected "
                "by the audited descriptors, but that does not prove they "
                "are unused elsewhere."
            ),
        ],
    }


def render_report(report: dict[str, Any]) -> bytes:
    """Render stable UTF-8 JSON with LF newlines and one terminal LF."""

    text = json.dumps(
        report,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    )
    if "\r" in text:
        raise AuditError("report renderer produced a carriage return")
    return (text + "\n").encode("utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit canonical compressed NPC/enemy sprite sources and emit "
            "metadata-only JSON to stdout."
        )
    )
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="canonical headerless Chrono Trigger US Rev0 ROM; read-only",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rom = args.rom.read_bytes()
        report = audit_rom_bytes(rom)
        payload = render_report(report)
    except (AuditError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
