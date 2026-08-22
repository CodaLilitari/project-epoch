#!/usr/bin/env python3
"""Encode and validate collision-resistant Project Epoch sidecars.

Version 2 preserves the complete 0xA0-byte v1 layout through offset 0x7F.
It assigns the two v1-reserved header bytes to an explicit physical slot and
binding profile, then assigns the v1 expansion reserve at 0x80-0x9F to a full
SHA-256 binding of the exact selected 0xA00-byte vanilla slot.

This is a source-only host model.  It writes no ROM, chooses no hook or WRAM
scratch address, and does not approve the bounded SRAM gap for production.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import struct
from typing import Final

import inspect_ct_srm
import schala_sidecar as sidecar_v1


VERSION: Final = 2
BINDING_PROFILE_SHA256_SLOT_TRAILER: Final = 1
BINDING_TRAILER_TAG: Final = b"PE07BIND"
BINDING_DIGEST_SIZE: Final = 0x20
BINDING_DIGEST_OFFSET: Final = 0x80
SLOT_IDENTITY_OFFSET: Final = 0x0E
BINDING_PROFILE_OFFSET: Final = 0x0F

MIGRATION_EVIDENCE_CALLER_ASSERTED: Final = "caller-asserted-unverified"
_MIGRATION_SEAL_DOMAIN: Final = (
    b"project-epoch-v1-to-v2-migration-authorization-v1"
)

SIDECAR_SIZE: Final = sidecar_v1.SIDECAR_SIZE
PAYLOAD_LENGTH: Final = sidecar_v1.PAYLOAD_LENGTH
CHECKSUM_OFFSET: Final = sidecar_v1.CHECKSUM_OFFSET
CHARACTER_RECORD_SIZE: Final = sidecar_v1.CHARACTER_RECORD_SIZE
NAME_SIZE: Final = sidecar_v1.NAME_SIZE
COMBO_STATE_SIZE: Final = sidecar_v1.COMBO_STATE_SIZE
QUEST_STATE_SIZE: Final = sidecar_v1.QUEST_STATE_SIZE


class SidecarV2Error(ValueError):
    """Raised before malformed or ambiguously bound v2 data is accepted."""


@dataclasses.dataclass(frozen=True, slots=True)
class SchalaSidecarV2:
    character_record: bytes
    name: bytes
    tech_progress: int
    learned_mask: int
    combo_state: bytes
    quest_state: bytes
    flags: int
    sequence: int
    vanilla_slot_checksum: int
    slot_number: int
    binding_profile: int
    binding_digest: bytes


@dataclasses.dataclass(frozen=True, slots=True)
class SidecarLoadResultV2:
    status: str
    value: SchalaSidecarV2 | None
    detail: str


@dataclasses.dataclass(frozen=True, slots=True)
class VersionedSidecarLoadResult:
    status: str
    version: int | None
    value: SchalaSidecarV2 | None
    detail: str


@dataclasses.dataclass(frozen=True, slots=True)
class V1MigrationAuthorization:
    """Caller assertion that one selected v1 record has reviewed provenance."""

    source_sram_sha256: str
    source_v1_sha256: str
    serialized_slot_sha256: str
    slot_number: int
    selected_slot_provenance_reviewed: bool
    evidence_level: str
    seal: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_exact_bytes(value: object, size: int, field: str) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise SidecarV2Error(
            f"{field} must be immutable bytes of exact length 0x{size:X}"
        )
    return value


def _require_exact_int(
    value: object, minimum: int, maximum: int, field: str
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SidecarV2Error(
            f"{field} must be an exact integer from {minimum} through {maximum}"
        )
    return value


def _require_slot_number(value: object) -> int:
    return _require_exact_int(
        value, 1, sidecar_v1.SIDECAR_SLOT_COUNT, "slot_number"
    )


def _validate_header_flags(value: object) -> int:
    flags = _require_exact_int(value, 0, 0xFF, "flags")
    if not flags & sidecar_v1.FLAG_INITIALIZED:
        raise SidecarV2Error("sidecar initialized flag is not set")
    unknown = flags & ~sidecar_v1.KNOWN_HEADER_FLAGS
    if unknown:
        raise SidecarV2Error(
            f"sidecar contains unknown header flags 0x{unknown:02X}"
        )
    return flags


def binding_trailer(slot_number: int) -> bytes:
    """Return the fixed 16-byte, stream-aligned v2 SHA-256 trailer."""

    slot_number = _require_slot_number(slot_number)
    trailer = (
        BINDING_TRAILER_TAG
        + bytes(
            (
                VERSION,
                BINDING_PROFILE_SHA256_SLOT_TRAILER,
                slot_number,
                0,
            )
        )
        + inspect_ct_srm.SLOT_SIZE.to_bytes(2, "little")
        + b"\x00\x00"
    )
    if len(trailer) != 0x10:
        raise AssertionError("v2 binding trailer must be exactly 16 bytes")
    return trailer


def slot_binding_digest(
    serialized_vanilla_slot: bytes, slot_number: int
) -> bytes:
    """Bind exact slot bytes and physical slot identity with SHA-256."""

    serialized_vanilla_slot = _require_exact_bytes(
        serialized_vanilla_slot,
        inspect_ct_srm.SLOT_SIZE,
        "serialized vanilla slot",
    )
    return hashlib.sha256(
        serialized_vanilla_slot + binding_trailer(slot_number)
    ).digest()


def _validate_value(value: SchalaSidecarV2) -> None:
    if type(value) is not SchalaSidecarV2:
        raise SidecarV2Error(
            "v2 sidecar must use the exact immutable host type"
        )
    _require_exact_bytes(
        value.character_record, CHARACTER_RECORD_SIZE, "character_record"
    )
    _require_exact_bytes(value.name, NAME_SIZE, "name")
    _require_exact_bytes(value.combo_state, COMBO_STATE_SIZE, "combo_state")
    _require_exact_bytes(value.quest_state, QUEST_STATE_SIZE, "quest_state")
    _require_exact_bytes(
        value.binding_digest, BINDING_DIGEST_SIZE, "binding_digest"
    )
    _validate_header_flags(value.flags)
    _require_exact_int(value.sequence, 0, 0xFFFF, "sequence")
    _require_exact_int(
        value.vanilla_slot_checksum,
        0,
        0xFFFF,
        "vanilla_slot_checksum",
    )
    _require_slot_number(value.slot_number)
    if (
        type(value.binding_profile) is not int
        or value.binding_profile != BINDING_PROFILE_SHA256_SLOT_TRAILER
    ):
        raise SidecarV2Error("unsupported v2 binding profile")
    _require_exact_int(value.tech_progress, 0, 8, "tech_progress")
    _require_exact_int(value.learned_mask, 0, 0xFF, "learned_mask")
    expected_mask = sidecar_v1.learned_mask_for_count(value.tech_progress)
    if value.learned_mask != expected_mask:
        raise SidecarV2Error(
            "learned_mask does not match the high-bit-first learned count"
        )
    try:
        sidecar_v1.decode_quest_state(value.quest_state)
    except sidecar_v1.SidecarError as exc:
        raise SidecarV2Error(f"quest_state is invalid: {exc}") from exc


def prepare_sidecar_v2(
    *,
    character_record: bytes,
    name: bytes,
    tech_progress: int,
    learned_mask: int,
    combo_state: bytes,
    quest_state: bytes,
    flags: int,
    sequence: int,
    serialized_vanilla_slot: bytes,
    slot_number: int,
) -> SchalaSidecarV2:
    """Create one v2 record bound to exact already-serialized slot bytes."""

    serialized_vanilla_slot = _require_exact_bytes(
        serialized_vanilla_slot,
        inspect_ct_srm.SLOT_SIZE,
        "serialized vanilla slot",
    )
    slot_number = _require_slot_number(slot_number)
    value = SchalaSidecarV2(
        character_record=character_record,
        name=name,
        tech_progress=tech_progress,
        learned_mask=learned_mask,
        combo_state=combo_state,
        quest_state=quest_state,
        flags=flags,
        sequence=sequence,
        vanilla_slot_checksum=inspect_ct_srm.slot_checksum(
            serialized_vanilla_slot
        ),
        slot_number=slot_number,
        binding_profile=BINDING_PROFILE_SHA256_SLOT_TRAILER,
        binding_digest=slot_binding_digest(
            serialized_vanilla_slot, slot_number
        ),
    )
    _validate_value(value)
    return value


def encode_sidecar_v2(
    value: SchalaSidecarV2, serialized_vanilla_slot: bytes
) -> bytes:
    """Encode v2 only when its checksum and strong binding both rederive."""

    _validate_value(value)
    serialized_vanilla_slot = _require_exact_bytes(
        serialized_vanilla_slot,
        inspect_ct_srm.SLOT_SIZE,
        "serialized vanilla slot",
    )
    expected_checksum = inspect_ct_srm.slot_checksum(
        serialized_vanilla_slot
    )
    if value.vanilla_slot_checksum != expected_checksum:
        raise SidecarV2Error(
            "v2 sidecar checksum binding does not match serialized slot"
        )
    expected_digest = slot_binding_digest(
        serialized_vanilla_slot, value.slot_number
    )
    if value.binding_digest != expected_digest:
        raise SidecarV2Error(
            "v2 sidecar SHA-256 binding does not match serialized slot"
        )

    encoded = bytearray(SIDECAR_SIZE)
    struct.pack_into(
        "<4sBBHHHHBB",
        encoded,
        0,
        sidecar_v1.MAGIC,
        VERSION,
        value.flags,
        PAYLOAD_LENGTH,
        value.sequence,
        0,
        value.vanilla_slot_checksum,
        value.slot_number,
        value.binding_profile,
    )
    encoded[0x10:0x60] = value.character_record
    encoded[0x60:0x66] = value.name
    encoded[0x66] = value.tech_progress
    encoded[0x67] = value.learned_mask
    encoded[0x68:0x78] = value.combo_state
    encoded[0x78:0x80] = value.quest_state
    encoded[BINDING_DIGEST_OFFSET:SIDECAR_SIZE] = value.binding_digest
    checksum = sidecar_v1.crc16_ccitt_false(encoded)
    struct.pack_into("<H", encoded, CHECKSUM_OFFSET, checksum)
    return bytes(encoded)


def decode_sidecar_v2(
    encoded: bytes,
    *,
    serialized_vanilla_slot: bytes | None = None,
    expected_slot_number: int | None = None,
) -> SchalaSidecarV2:
    """Decode v2 and optionally require its complete slot binding."""

    encoded = _require_exact_bytes(encoded, SIDECAR_SIZE, "sidecar")
    if encoded == b"\xFF" * SIDECAR_SIZE:
        raise SidecarV2Error("sidecar is uninitialized")
    if (serialized_vanilla_slot is None) != (
        expected_slot_number is None
    ):
        raise SidecarV2Error(
            "binding validation requires both serialized slot and slot number"
        )

    (
        magic,
        version,
        flags,
        payload_length,
        sequence,
        stored_crc,
        vanilla_slot_checksum,
        slot_number,
        binding_profile,
    ) = struct.unpack_from("<4sBBHHHHBB", encoded, 0)
    if magic != sidecar_v1.MAGIC:
        raise SidecarV2Error("sidecar magic does not match")
    if version != VERSION:
        raise SidecarV2Error(f"unsupported sidecar version {version}")
    if payload_length != PAYLOAD_LENGTH:
        raise SidecarV2Error("sidecar payload length does not match version 2")
    _validate_header_flags(flags)
    _require_slot_number(slot_number)
    if binding_profile != BINDING_PROFILE_SHA256_SLOT_TRAILER:
        raise SidecarV2Error("unsupported v2 binding profile")

    checksum_input = bytearray(encoded)
    checksum_input[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 2] = b"\x00\x00"
    computed_crc = sidecar_v1.crc16_ccitt_false(checksum_input)
    if stored_crc != computed_crc:
        raise SidecarV2Error(
            f"sidecar CRC mismatch: stored 0x{stored_crc:04X}, "
            f"computed 0x{computed_crc:04X}"
        )

    value = SchalaSidecarV2(
        character_record=encoded[0x10:0x60],
        name=encoded[0x60:0x66],
        tech_progress=encoded[0x66],
        learned_mask=encoded[0x67],
        combo_state=encoded[0x68:0x78],
        quest_state=encoded[0x78:0x80],
        flags=flags,
        sequence=sequence,
        vanilla_slot_checksum=vanilla_slot_checksum,
        slot_number=slot_number,
        binding_profile=binding_profile,
        binding_digest=encoded[BINDING_DIGEST_OFFSET:SIDECAR_SIZE],
    )
    _validate_value(value)

    if serialized_vanilla_slot is not None:
        serialized_vanilla_slot = _require_exact_bytes(
            serialized_vanilla_slot,
            inspect_ct_srm.SLOT_SIZE,
            "serialized vanilla slot",
        )
        selected_slot = _require_slot_number(expected_slot_number)
        if value.slot_number != selected_slot:
            raise SidecarV2Error(
                "v2 sidecar physical slot identity does not match selection"
            )
        expected_checksum = inspect_ct_srm.slot_checksum(
            serialized_vanilla_slot
        )
        if value.vanilla_slot_checksum != expected_checksum:
            raise SidecarV2Error(
                "v2 sidecar checksum binding does not match serialized slot"
            )
        expected_digest = slot_binding_digest(
            serialized_vanilla_slot, selected_slot
        )
        if value.binding_digest != expected_digest:
            raise SidecarV2Error(
                "v2 sidecar SHA-256 binding does not match serialized slot"
            )
    return value


def classify_sidecar_v2(
    encoded: bytes,
    serialized_vanilla_slot: bytes,
    selected_slot_number: int,
) -> SidecarLoadResultV2:
    """Classify v2 without publishing any mismatched binding."""

    encoded = _require_exact_bytes(encoded, SIDECAR_SIZE, "sidecar")
    serialized_vanilla_slot = _require_exact_bytes(
        serialized_vanilla_slot,
        inspect_ct_srm.SLOT_SIZE,
        "serialized vanilla slot",
    )
    selected_slot_number = _require_slot_number(selected_slot_number)
    if encoded == b"\xFF" * SIDECAR_SIZE:
        return SidecarLoadResultV2(
            status="uninitialized",
            value=None,
            detail="no Project Epoch record is present",
        )
    try:
        value = decode_sidecar_v2(encoded)
    except SidecarV2Error as exc:
        return SidecarLoadResultV2(
            status="invalid", value=None, detail=str(exc)
        )

    if value.slot_number != selected_slot_number:
        return SidecarLoadResultV2(
            status="stale",
            value=None,
            detail=(
                "v2 sidecar physical slot identity does not match selection"
            ),
        )
    expected_checksum = inspect_ct_srm.slot_checksum(
        serialized_vanilla_slot
    )
    if value.vanilla_slot_checksum != expected_checksum:
        return SidecarLoadResultV2(
            status="stale",
            value=None,
            detail="v2 checksum binding does not match selected vanilla slot",
        )
    expected_digest = slot_binding_digest(
        serialized_vanilla_slot, selected_slot_number
    )
    if value.binding_digest != expected_digest:
        return SidecarLoadResultV2(
            status="stale",
            value=None,
            detail="v2 SHA-256 binding does not match selected vanilla slot",
        )
    return SidecarLoadResultV2(
        status="valid",
        value=value,
        detail="v2 sidecar is valid and strongly slot-bound",
    )


def classify_versioned_sidecar(
    encoded: bytes,
    serialized_vanilla_slot: bytes,
    selected_slot_number: int,
) -> VersionedSidecarLoadResult:
    """Dispatch exactly by version; valid v1 remains non-publishable legacy."""

    encoded = _require_exact_bytes(encoded, SIDECAR_SIZE, "sidecar")
    serialized_vanilla_slot = _require_exact_bytes(
        serialized_vanilla_slot,
        inspect_ct_srm.SLOT_SIZE,
        "serialized vanilla slot",
    )
    selected_slot_number = _require_slot_number(selected_slot_number)
    if encoded == b"\xFF" * SIDECAR_SIZE:
        return VersionedSidecarLoadResult(
            status="uninitialized",
            version=None,
            value=None,
            detail="no Project Epoch record is present",
        )
    if encoded[:4] != sidecar_v1.MAGIC:
        return VersionedSidecarLoadResult(
            status="invalid",
            version=None,
            value=None,
            detail="sidecar magic does not match",
        )

    version = encoded[4]
    if version == sidecar_v1.VERSION:
        legacy = sidecar_v1.classify_sidecar(
            encoded, inspect_ct_srm.slot_checksum(serialized_vanilla_slot)
        )
        if legacy.status == "valid":
            return VersionedSidecarLoadResult(
                status="legacy-v1-migration-required",
                version=sidecar_v1.VERSION,
                value=None,
                detail=(
                    "valid v1 sidecar lacks collision-resistant slot "
                    "provenance and cannot publish live state"
                ),
            )
        return VersionedSidecarLoadResult(
            status=legacy.status,
            version=sidecar_v1.VERSION,
            value=None,
            detail=legacy.detail,
        )
    if version != VERSION:
        return VersionedSidecarLoadResult(
            status="invalid",
            version=version,
            value=None,
            detail=f"unsupported sidecar version {version}",
        )

    result = classify_sidecar_v2(
        encoded, serialized_vanilla_slot, selected_slot_number
    )
    return VersionedSidecarLoadResult(
        status=result.status,
        version=VERSION,
        value=result.value,
        detail=result.detail,
    )


def load_sidecar_v2_from_sram(
    sram: bytes, selected_slot_number: int
) -> VersionedSidecarLoadResult:
    """Classify one record only after the selected vanilla slot validates."""

    sram = _require_exact_bytes(sram, inspect_ct_srm.SRAM_SIZE, "SRAM")
    selected_slot_number = _require_slot_number(selected_slot_number)
    slot_info = inspect_ct_srm.inspect_slot(sram, selected_slot_number)
    if type(slot_info) is not dict or slot_info.get("valid") is not True:
        return VersionedSidecarLoadResult(
            status="invalid-vanilla",
            version=None,
            value=None,
            detail=(
                "selected vanilla slot failed checksum or magic validation"
            ),
        )
    slot_base = (selected_slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    serialized_slot = sram[
        slot_base : slot_base + inspect_ct_srm.SLOT_SIZE
    ]
    sidecar_start = sidecar_v1.slot_file_offset(selected_slot_number)
    encoded = sram[sidecar_start : sidecar_start + SIDECAR_SIZE]
    return classify_versioned_sidecar(
        encoded, serialized_slot, selected_slot_number
    )


def install_sidecar_v2(
    sram: bytes, selected_slot_number: int, encoded: bytes
) -> bytes:
    """Install one already-bound v2 record and preserve every other byte."""

    sram = _require_exact_bytes(sram, inspect_ct_srm.SRAM_SIZE, "SRAM")
    selected_slot_number = _require_slot_number(selected_slot_number)
    encoded = _require_exact_bytes(encoded, SIDECAR_SIZE, "sidecar")
    slot_info = inspect_ct_srm.inspect_slot(sram, selected_slot_number)
    if type(slot_info) is not dict or slot_info.get("valid") is not True:
        raise SidecarV2Error(
            "selected vanilla slot must pass checksum and magic validation"
        )
    slot_base = (selected_slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    serialized_slot = sram[
        slot_base : slot_base + inspect_ct_srm.SLOT_SIZE
    ]
    result = classify_sidecar_v2(
        encoded, serialized_slot, selected_slot_number
    )
    if result.status != "valid":
        raise SidecarV2Error(
            f"v2 sidecar installation refused: {result.detail}"
        )
    sidecar_start = sidecar_v1.slot_file_offset(selected_slot_number)
    output = bytearray(sram)
    output[sidecar_start : sidecar_start + SIDECAR_SIZE] = encoded
    return bytes(output)


def _migration_authorization_seal(
    value: V1MigrationAuthorization,
) -> str:
    if type(value) is not V1MigrationAuthorization:
        raise SidecarV2Error(
            "migration authorization must use the exact immutable host type"
        )
    digest = hashlib.sha256(_MIGRATION_SEAL_DOMAIN)
    for text in (
        value.source_sram_sha256,
        value.source_v1_sha256,
        value.serialized_slot_sha256,
        value.evidence_level,
    ):
        if type(text) is not str:
            raise SidecarV2Error(
                "migration authorization text fields must use exact strings"
            )
        encoded = text.encode("utf-8")
        digest.update(len(encoded).to_bytes(2, "little"))
        digest.update(encoded)
    _require_slot_number(value.slot_number)
    if type(value.selected_slot_provenance_reviewed) is not bool:
        raise SidecarV2Error(
            "migration provenance assertion must use an exact boolean"
        )
    digest.update(bytes((value.slot_number,)))
    digest.update(bytes((int(value.selected_slot_provenance_reviewed),)))
    return digest.hexdigest()


def _validated_v1_migration_source(
    source_sram: bytes, selected_slot_number: int
) -> tuple[bytes, bytes, sidecar_v1.SchalaSidecarV1]:
    source_sram = _require_exact_bytes(
        source_sram, inspect_ct_srm.SRAM_SIZE, "source SRAM"
    )
    selected_slot_number = _require_slot_number(selected_slot_number)
    slot_info = inspect_ct_srm.inspect_slot(
        source_sram, selected_slot_number
    )
    if type(slot_info) is not dict or slot_info.get("valid") is not True:
        raise SidecarV2Error(
            "v1 migration requires a checksum-valid selected vanilla slot"
        )
    slot_base = (selected_slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    serialized_slot = source_sram[
        slot_base : slot_base + inspect_ct_srm.SLOT_SIZE
    ]
    sidecar_start = sidecar_v1.slot_file_offset(selected_slot_number)
    encoded_v1 = source_sram[
        sidecar_start : sidecar_start + SIDECAR_SIZE
    ]
    legacy = sidecar_v1.classify_sidecar(
        encoded_v1, slot_info["computed_checksum"]
    )
    if (
        legacy.status != "valid"
        or type(legacy.value) is not sidecar_v1.SchalaSidecarV1
    ):
        raise SidecarV2Error(
            f"v1 migration requires a valid legacy record: {legacy.detail}"
        )
    return serialized_slot, encoded_v1, legacy.value


def prepare_v1_migration_authorization(
    source_sram: bytes,
    selected_slot_number: int,
    *,
    selected_slot_provenance_reviewed: bool,
) -> V1MigrationAuthorization:
    """Bind an explicit human provenance assertion to one v1 source image."""

    serialized_slot, encoded_v1, _ = _validated_v1_migration_source(
        source_sram, selected_slot_number
    )
    if (
        type(selected_slot_provenance_reviewed) is not bool
        or selected_slot_provenance_reviewed is not True
    ):
        raise SidecarV2Error(
            "v1 migration requires explicit selected-slot provenance review"
        )
    provisional = V1MigrationAuthorization(
        source_sram_sha256=sha256(source_sram),
        source_v1_sha256=sha256(encoded_v1),
        serialized_slot_sha256=sha256(serialized_slot),
        slot_number=_require_slot_number(selected_slot_number),
        selected_slot_provenance_reviewed=True,
        evidence_level=MIGRATION_EVIDENCE_CALLER_ASSERTED,
        seal="",
    )
    return dataclasses.replace(
        provisional, seal=_migration_authorization_seal(provisional)
    )


def _validate_migration_authorization(
    source_sram: bytes,
    selected_slot_number: int,
    value: V1MigrationAuthorization,
) -> None:
    if type(value) is not V1MigrationAuthorization:
        raise SidecarV2Error(
            "v1 migration requires the exact authorization host type"
        )
    if type(value.seal) is not str or value.seal != (
        _migration_authorization_seal(value)
    ):
        raise SidecarV2Error("v1 migration authorization integrity failed")
    expected = prepare_v1_migration_authorization(
        source_sram,
        selected_slot_number,
        selected_slot_provenance_reviewed=(
            value.selected_slot_provenance_reviewed
        ),
    )
    if expected != value:
        raise SidecarV2Error(
            "v1 migration authorization is not bound to this source and slot"
        )


def migrate_v1_sidecar_in_sram(
    source_sram: bytes,
    selected_slot_number: int,
    authorization: V1MigrationAuthorization,
) -> bytes:
    """Explicitly migrate one reviewed v1 record; never called automatically."""

    serialized_slot, _, legacy = _validated_v1_migration_source(
        source_sram, selected_slot_number
    )
    _validate_migration_authorization(
        source_sram, selected_slot_number, authorization
    )
    value = prepare_sidecar_v2(
        character_record=legacy.character_record,
        name=legacy.name,
        tech_progress=legacy.tech_progress,
        learned_mask=legacy.learned_mask,
        combo_state=legacy.combo_state,
        quest_state=legacy.quest_state,
        flags=legacy.flags,
        sequence=min(legacy.sequence + 1, 0xFFFF),
        serialized_vanilla_slot=serialized_slot,
        slot_number=selected_slot_number,
    )
    encoded_v2 = encode_sidecar_v2(value, serialized_slot)
    migrated = install_sidecar_v2(
        source_sram, selected_slot_number, encoded_v2
    )
    loaded = load_sidecar_v2_from_sram(migrated, selected_slot_number)
    if loaded.status != "valid" or loaded.value != value:
        raise AssertionError("migrated v2 sidecar failed exact round trip")
    return migrated


def prepare_new_game_plus_v2_for_serialized_save(
    source: SchalaSidecarV2,
    *,
    source_serialized_slot: bytes,
    destination_serialized_slot: bytes,
    destination_slot_number: int,
    reset_character_record: bytes,
    reset_name: bytes,
) -> SchalaSidecarV2:
    """Apply v2 NG+ policy only after destination slot serialization."""

    source_serialized_slot = _require_exact_bytes(
        source_serialized_slot,
        inspect_ct_srm.SLOT_SIZE,
        "source serialized vanilla slot",
    )
    destination_serialized_slot = _require_exact_bytes(
        destination_serialized_slot,
        inspect_ct_srm.SLOT_SIZE,
        "destination serialized vanilla slot",
    )
    decode_sidecar_v2(
        encode_sidecar_v2(source, source_serialized_slot),
        serialized_vanilla_slot=source_serialized_slot,
        expected_slot_number=source.slot_number,
    )
    reset_character_record = _require_exact_bytes(
        reset_character_record,
        CHARACTER_RECORD_SIZE,
        "reset_character_record",
    )
    reset_name = _require_exact_bytes(reset_name, NAME_SIZE, "reset_name")
    next_sequence = min(source.sequence + 1, 0xFFFF)

    if source.flags & sidecar_v1.FLAG_NG_PLUS_RETAIN:
        fields = {
            "character_record": source.character_record,
            "name": source.name,
            "tech_progress": source.tech_progress,
            "learned_mask": source.learned_mask,
            "combo_state": source.combo_state,
            "quest_state": source.quest_state,
            "flags": source.flags,
        }
    else:
        fields = {
            "character_record": reset_character_record,
            "name": reset_name,
            "tech_progress": 0,
            "learned_mask": 0,
            "combo_state": bytes(COMBO_STATE_SIZE),
            "quest_state": sidecar_v1.encode_quest_state(
                sidecar_v1.QuestStateV1()
            ),
            "flags": sidecar_v1.FLAG_INITIALIZED,
        }
    return prepare_sidecar_v2(
        **fields,
        sequence=next_sequence,
        serialized_vanilla_slot=destination_serialized_slot,
        slot_number=destination_slot_number,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sidecar", type=pathlib.Path)
    parser.add_argument("--vanilla-slot", required=True, type=pathlib.Path)
    parser.add_argument("--slot", required=True, type=int, choices=(1, 2, 3))
    args = parser.parse_args()

    encoded = args.sidecar.read_bytes()
    serialized_slot = args.vanilla_slot.read_bytes()
    value = decode_sidecar_v2(
        encoded,
        serialized_vanilla_slot=serialized_slot,
        expected_slot_number=args.slot,
    )
    print(f"path={args.sidecar}")
    print(f"sha256={sha256(encoded)}")
    print(f"version={VERSION}")
    print(f"flags=0x{value.flags:02X}")
    print(f"sequence={value.sequence}")
    print(f"slot_number={value.slot_number}")
    print(f"binding_profile={value.binding_profile}")
    print(
        "vanilla_slot_checksum="
        f"0x{value.vanilla_slot_checksum:04X}"
    )
    print(f"binding_digest={value.binding_digest.hex()}")


if __name__ == "__main__":
    main()
