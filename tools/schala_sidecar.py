#!/usr/bin/env python3
"""Encode and validate Project Epoch Schala per-save-slot sidecars.

This module defines the candidate version-1 0xA0-byte record only. It does not
patch game code or claim that SRAM $30:7E00-$30:7FDF is production-approved.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import struct


SRAM_SIZE = 0x2000
SIDECAR_AREA_OFFSET = 0x1E00
SIDECAR_AREA_LENGTH = 0x01E0
SIDECAR_SIZE = 0x00A0
SIDECAR_SLOT_COUNT = 3
GLOBAL_METADATA_OFFSET = 0x1FE0

MAGIC = b"PE07"
VERSION = 1
HEADER_SIZE = 0x10
PAYLOAD_LENGTH = SIDECAR_SIZE - HEADER_SIZE
CHECKSUM_OFFSET = 0x0A

CHARACTER_RECORD_SIZE = 0x50
NAME_SIZE = 6
COMBO_STATE_SIZE = 0x10
QUEST_STATE_SIZE = 8
RESERVED_SIZE = 0x20

FLAG_INITIALIZED = 0x01
FLAG_NG_PLUS_RETAIN = 0x02
KNOWN_HEADER_FLAGS = FLAG_INITIALIZED | FLAG_NG_PLUS_RETAIN

QUEST_UNLOCKED = 0x01
QUEST_WARD_RESOLVED = 0x02
QUEST_SCHALA_RECRUITED = 0x04
QUEST_JOIN_GRANT_APPLIED = 0x08
KNOWN_QUEST_FLAGS = (
    QUEST_UNLOCKED
    | QUEST_WARD_RESOLVED
    | QUEST_SCHALA_RECRUITED
    | QUEST_JOIN_GRANT_APPLIED
)


class SidecarError(ValueError):
    """Raised when a sidecar cannot be encoded or validated."""


@dataclasses.dataclass(frozen=True)
class SchalaSidecarV1:
    character_record: bytes
    name: bytes
    tech_progress: int
    learned_mask: int
    combo_state: bytes = bytes(COMBO_STATE_SIZE)
    quest_state: bytes = bytes(QUEST_STATE_SIZE)
    reserved: bytes = bytes(RESERVED_SIZE)
    flags: int = FLAG_INITIALIZED
    sequence: int = 0
    vanilla_slot_checksum: int = 0


@dataclasses.dataclass(frozen=True)
class QuestStateV1:
    quest_unlocked: bool = False
    anchor_count: int = 0
    ward_resolved: bool = False
    schala_recruited: bool = False
    join_grant_applied: bool = False


@dataclasses.dataclass(frozen=True)
class SidecarLoadResult:
    status: str
    value: SchalaSidecarV1 | None
    detail: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def crc16_ccitt_false(data: bytes) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no reflection."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (
                crc << 1
            ) & 0xFFFF
    return crc


def slot_file_offset(slot: int) -> int:
    if slot not in range(1, SIDECAR_SLOT_COUNT + 1):
        raise SidecarError("slot must be 1, 2, or 3")
    offset = SIDECAR_AREA_OFFSET + (slot - 1) * SIDECAR_SIZE
    if offset + SIDECAR_SIZE > GLOBAL_METADATA_OFFSET:
        raise AssertionError("sidecar layout overlaps global metadata")
    return offset


def _require_byte(value: int, field: str) -> None:
    if not 0 <= value <= 0xFF:
        raise SidecarError(f"{field} must fit in one byte")


def _require_length(value: bytes, expected: int, field: str) -> None:
    if len(value) != expected:
        raise SidecarError(
            f"{field} must be exactly 0x{expected:X} bytes, got 0x{len(value):X}"
        )


def learned_mask_for_count(count: int) -> int:
    """Return the vanilla high-bit-first single-tech mask for 0..8 techs."""

    if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 8:
        raise SidecarError("tech_progress learned count must be 0 through 8")
    if count == 0:
        return 0
    return (0xFF << (8 - count)) & 0xFF


def _validate_single_tech_state(tech_progress: int, learned_mask: int) -> None:
    _require_byte(tech_progress, "tech_progress")
    _require_byte(learned_mask, "learned_mask")
    expected = learned_mask_for_count(tech_progress)
    if learned_mask != expected:
        raise SidecarError(
            "learned_mask does not match the high-bit-first learned count"
        )


def _validate_header_flags(flags: int) -> None:
    _require_byte(flags, "flags")
    if not flags & FLAG_INITIALIZED:
        raise SidecarError("sidecar initialized flag is not set")
    unknown = flags & ~KNOWN_HEADER_FLAGS
    if unknown:
        raise SidecarError(
            f"sidecar contains unknown header flags 0x{unknown:02X}"
        )


def encode_quest_state(value: QuestStateV1) -> bytes:
    if not 0 <= value.anchor_count <= 3:
        raise SidecarError("anchor_count must be between 0 and 3")
    if value.ward_resolved and (
        not value.quest_unlocked or value.anchor_count != 3
    ):
        raise SidecarError(
            "ward_resolved requires quest_unlocked and anchor_count 3"
        )
    if value.schala_recruited and not value.ward_resolved:
        raise SidecarError("schala_recruited requires ward_resolved")
    if value.join_grant_applied and not value.schala_recruited:
        raise SidecarError(
            "join_grant_applied requires schala_recruited"
        )

    flags = 0
    flags |= QUEST_UNLOCKED if value.quest_unlocked else 0
    flags |= QUEST_WARD_RESOLVED if value.ward_resolved else 0
    flags |= QUEST_SCHALA_RECRUITED if value.schala_recruited else 0
    flags |= QUEST_JOIN_GRANT_APPLIED if value.join_grant_applied else 0
    return bytes((flags, value.anchor_count, 0, 0, 0, 0, 0, 0))


def decode_quest_state(encoded: bytes) -> QuestStateV1:
    _require_length(encoded, QUEST_STATE_SIZE, "quest_state")
    unknown = encoded[0] & ~KNOWN_QUEST_FLAGS
    if unknown:
        raise SidecarError(
            f"quest_state contains unknown flags 0x{unknown:02X}"
        )
    if any(encoded[2:]):
        raise SidecarError("quest_state reserved bytes must be zero")
    value = QuestStateV1(
        quest_unlocked=bool(encoded[0] & QUEST_UNLOCKED),
        anchor_count=encoded[1],
        ward_resolved=bool(encoded[0] & QUEST_WARD_RESOLVED),
        schala_recruited=bool(encoded[0] & QUEST_SCHALA_RECRUITED),
        join_grant_applied=bool(encoded[0] & QUEST_JOIN_GRANT_APPLIED),
    )
    # Reuse the encoder as the single semantic validator.
    if encode_quest_state(value) != encoded:
        raise SidecarError("quest_state is not canonical version-1 data")
    return value


def encode_sidecar(value: SchalaSidecarV1) -> bytes:
    _require_length(
        value.character_record, CHARACTER_RECORD_SIZE, "character_record"
    )
    _require_length(value.name, NAME_SIZE, "name")
    _require_length(value.combo_state, COMBO_STATE_SIZE, "combo_state")
    _require_length(value.quest_state, QUEST_STATE_SIZE, "quest_state")
    _require_length(value.reserved, RESERVED_SIZE, "reserved")
    _validate_single_tech_state(value.tech_progress, value.learned_mask)
    _validate_header_flags(value.flags)
    decode_quest_state(value.quest_state)
    if any(value.reserved):
        raise SidecarError("version-1 reserved bytes must be zero")
    if not 0 <= value.sequence <= 0xFFFF:
        raise SidecarError("sequence must fit in two bytes")
    if not 0 <= value.vanilla_slot_checksum <= 0xFFFF:
        raise SidecarError("vanilla_slot_checksum must fit in two bytes")

    encoded = bytearray(SIDECAR_SIZE)
    struct.pack_into(
        "<4sBBHHHHH",
        encoded,
        0,
        MAGIC,
        VERSION,
        value.flags,
        PAYLOAD_LENGTH,
        value.sequence,
        0,
        value.vanilla_slot_checksum,
        0,
    )
    encoded[0x10:0x60] = value.character_record
    encoded[0x60:0x66] = value.name
    encoded[0x66] = value.tech_progress
    encoded[0x67] = value.learned_mask
    encoded[0x68:0x78] = value.combo_state
    encoded[0x78:0x80] = value.quest_state
    encoded[0x80:0xA0] = value.reserved

    checksum = crc16_ccitt_false(encoded)
    struct.pack_into("<H", encoded, CHECKSUM_OFFSET, checksum)
    return bytes(encoded)


def decode_sidecar(
    encoded: bytes, expected_vanilla_checksum: int | None = None
) -> SchalaSidecarV1:
    _require_length(encoded, SIDECAR_SIZE, "sidecar")
    if encoded == b"\xFF" * SIDECAR_SIZE:
        raise SidecarError("sidecar is uninitialized")

    (
        magic,
        version,
        flags,
        payload_length,
        sequence,
        stored_crc,
        vanilla_slot_checksum,
        header_reserved,
    ) = struct.unpack_from("<4sBBHHHHH", encoded, 0)
    if magic != MAGIC:
        raise SidecarError("sidecar magic does not match")
    if version != VERSION:
        raise SidecarError(f"unsupported sidecar version {version}")
    if payload_length != PAYLOAD_LENGTH:
        raise SidecarError("sidecar payload length does not match version 1")
    if header_reserved != 0:
        raise SidecarError("reserved header word is nonzero")
    _validate_header_flags(flags)
    if (
        expected_vanilla_checksum is not None
        and vanilla_slot_checksum != expected_vanilla_checksum
    ):
        raise SidecarError(
            "sidecar is bound to vanilla checksum "
            f"0x{vanilla_slot_checksum:04X}, not "
            f"0x{expected_vanilla_checksum:04X}"
        )

    checksum_input = bytearray(encoded)
    checksum_input[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 2] = b"\x00\x00"
    computed_crc = crc16_ccitt_false(checksum_input)
    if stored_crc != computed_crc:
        raise SidecarError(
            f"sidecar CRC mismatch: stored 0x{stored_crc:04X}, "
            f"computed 0x{computed_crc:04X}"
        )

    decode_quest_state(encoded[0x78:0x80])
    if any(encoded[0x80:0xA0]):
        raise SidecarError("version-1 reserved bytes must be zero")
    _validate_single_tech_state(encoded[0x66], encoded[0x67])

    return SchalaSidecarV1(
        character_record=encoded[0x10:0x60],
        name=encoded[0x60:0x66],
        tech_progress=encoded[0x66],
        learned_mask=encoded[0x67],
        combo_state=encoded[0x68:0x78],
        quest_state=encoded[0x78:0x80],
        reserved=encoded[0x80:0xA0],
        flags=flags,
        sequence=sequence,
        vanilla_slot_checksum=vanilla_slot_checksum,
    )


def install_sidecar(sram: bytes, slot: int, sidecar: bytes) -> bytes:
    _require_length(sram, SRAM_SIZE, "SRAM")
    # Decode before touching the SRAM image so malformed records never install.
    decode_sidecar(sidecar)
    offset = slot_file_offset(slot)
    result = bytearray(sram)
    result[offset : offset + SIDECAR_SIZE] = sidecar
    return bytes(result)


def classify_sidecar(
    encoded: bytes, expected_vanilla_checksum: int
) -> SidecarLoadResult:
    """Classify a record without allowing invalid data into live state."""

    _require_length(encoded, SIDECAR_SIZE, "sidecar")
    if encoded == b"\xFF" * SIDECAR_SIZE:
        return SidecarLoadResult(
            status="uninitialized",
            value=None,
            detail="no Project Epoch record is present",
        )
    try:
        value = decode_sidecar(encoded)
    except SidecarError as exc:
        return SidecarLoadResult(
            status="invalid", value=None, detail=str(exc)
        )
    if value.vanilla_slot_checksum != expected_vanilla_checksum:
        return SidecarLoadResult(
            status="stale",
            value=None,
            detail=(
                "sidecar binding does not match the current vanilla slot "
                "checksum"
            ),
        )
    return SidecarLoadResult(
        status="valid", value=value, detail="sidecar is valid and bound"
    )


def load_sidecar_from_sram(
    sram: bytes, slot: int, expected_vanilla_checksum: int
) -> SidecarLoadResult:
    _require_length(sram, SRAM_SIZE, "SRAM")
    offset = slot_file_offset(slot)
    return classify_sidecar(
        sram[offset : offset + SIDECAR_SIZE],
        expected_vanilla_checksum,
    )


def invalidate_sidecar(sram: bytes, slot: int) -> bytes:
    """Erase exactly one Project Epoch record and preserve vanilla bytes."""

    _require_length(sram, SRAM_SIZE, "SRAM")
    offset = slot_file_offset(slot)
    result = bytearray(sram)
    result[offset : offset + SIDECAR_SIZE] = b"\xFF" * SIDECAR_SIZE
    return bytes(result)


def apply_new_game_plus_policy(
    source: SchalaSidecarV1,
    *,
    new_vanilla_checksum: int,
    reset_character_record: bytes,
    reset_name: bytes,
) -> SchalaSidecarV1:
    """Return the deterministic v1 carry-over or reset record.

    The ROM hook is not implemented here. This host model freezes the policy
    that the future hook must reproduce.
    """

    # Validate the source before deriving another record.
    decode_sidecar(encode_sidecar(source))
    _require_length(
        reset_character_record,
        CHARACTER_RECORD_SIZE,
        "reset_character_record",
    )
    _require_length(reset_name, NAME_SIZE, "reset_name")
    if not 0 <= new_vanilla_checksum <= 0xFFFF:
        raise SidecarError("new_vanilla_checksum must fit in two bytes")
    next_sequence = min(source.sequence + 1, 0xFFFF)

    if source.flags & FLAG_NG_PLUS_RETAIN:
        return dataclasses.replace(
            source,
            sequence=next_sequence,
            vanilla_slot_checksum=new_vanilla_checksum,
        )

    return SchalaSidecarV1(
        character_record=reset_character_record,
        name=reset_name,
        tech_progress=0,
        learned_mask=0,
        combo_state=bytes(COMBO_STATE_SIZE),
        quest_state=encode_quest_state(QuestStateV1()),
        reserved=bytes(RESERVED_SIZE),
        flags=FLAG_INITIALIZED,
        sequence=next_sequence,
        vanilla_slot_checksum=new_vanilla_checksum,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sidecar", type=pathlib.Path)
    args = parser.parse_args()

    encoded = args.sidecar.read_bytes()
    value = decode_sidecar(encoded)
    print(f"path={args.sidecar}")
    print(f"sha256={sha256(encoded)}")
    print(f"version={VERSION}")
    print(f"flags=0x{value.flags:02X}")
    print(f"sequence={value.sequence}")
    print(f"vanilla_slot_checksum=0x{value.vanilla_slot_checksum:04X}")
    print(f"tech_progress=0x{value.tech_progress:02X}")
    print(f"learned_mask=0x{value.learned_mask:02X}")
    quest = decode_quest_state(value.quest_state)
    print(f"quest_unlocked={int(quest.quest_unlocked)}")
    print(f"anchor_count={quest.anchor_count}")
    print(f"ward_resolved={int(quest.ward_resolved)}")
    print(f"schala_recruited={int(quest.schala_recruited)}")
    print(f"join_grant_applied={int(quest.join_grant_applied)}")


if __name__ == "__main__":
    main()
