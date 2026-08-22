#!/usr/bin/env python3
"""Deterministic ExHiROM layout primitives for Project Epoch.

This module does not activate logical PC $07, assemble code, emit a ROM, or
write any file.  It provides the production builder with a conservative
8 MiB ExHiROM scaffold and an explicit-allocation validator.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json


EXPECTED_SOURCE_SIZE = 0x400000
EXPECTED_SOURCE_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
EXPECTED_INERT_SCAFFOLD_SHA256 = (
    "26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93"
)
TARGET_SIZE = 0x800000
FILL_BYTE = 0xFF

HIROM_HEADER = 0x00FFC0
EXHIROM_HEADER = 0x40FFC0
HEADER_MAP_MODE = 0x15
HEADER_ROM_SIZE = 0x17
HEADER_COMPLEMENT = 0x1C
HEADER_CHECKSUM = 0x1E
HIROM_FAST = 0x31
EXHIROM_FAST = 0x35
ROM_SIZE_4_MIB = 0x0C
ROM_SIZE_8_MIB = 0x0D

# ExHiROM maps bank $00's high half to file $40:8000-$40:FFFF. Chrono
# Trigger uses that mirror for reset/interrupt entry points and $00:Fxxx data,
# so the whole first bank is conservatively mirrored and reserved.
BOOT_MIRROR_START = 0x400000
BOOT_MIRROR_END = 0x410000

# Use only simple full-bank ExHiROM allocations. File $7E0000-$7FFFFF has no
# full-bank canonical ROM mapping because CPU banks $7E/$7F are WRAM.
ALLOCATION_START = BOOT_MIRROR_END
ALLOCATION_END = 0x7E0000
NONCANONICAL_TAIL_START = ALLOCATION_END
NONCANONICAL_TAIL_END = TARGET_SIZE

ALLOCATION_KINDS = frozenset(
    {"code", "table", "graphics", "palette", "text", "event", "reserved"}
)
EVIDENCE_LEVELS = frozenset(
    {"verified-static", "verified-runtime", "documented", "hypothesis"}
)


def digest(data: bytes, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def _read_u16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def _write_u16(data: bytearray, offset: int, value: int) -> None:
    data[offset : offset + 2] = value.to_bytes(2, "little")


def validate_source(
    source: bytes, expected_sha1: str = EXPECTED_SOURCE_SHA1
) -> None:
    if len(source) != EXPECTED_SOURCE_SIZE:
        raise ValueError(
            f"expected unheadered 4 MiB input, got {len(source):#x} bytes"
        )
    actual_sha1 = digest(source, "sha1")
    if actual_sha1 != expected_sha1:
        raise ValueError(
            f"input SHA-1 mismatch: expected {expected_sha1}, "
            f"got {actual_sha1}"
        )
    if source[HIROM_HEADER + HEADER_MAP_MODE] != HIROM_FAST:
        raise ValueError("input is not fast HiROM ($31)")
    if source[HIROM_HEADER + HEADER_ROM_SIZE] != ROM_SIZE_4_MIB:
        raise ValueError("input header does not declare a 4 MiB ROM")
    stored_complement = _read_u16(
        source, HIROM_HEADER + HEADER_COMPLEMENT
    )
    stored_checksum = _read_u16(source, HIROM_HEADER + HEADER_CHECKSUM)
    if stored_complement ^ stored_checksum != 0xFFFF:
        raise ValueError("input checksum/complement pair is invalid")
    if sum(source) & 0xFFFF != stored_checksum:
        raise ValueError("input checksum does not match its bytes")


def exhirom_snes_to_file(address: int) -> int | None:
    """Translate a mapped 24-bit ExHiROM address to an unheadered file offset."""
    if not 0 <= address <= 0xFFFFFF:
        raise ValueError("SNES address must fit in 24 bits")
    bank = address >> 16
    offset = address & 0xFFFF

    if 0xC0 <= bank <= 0xFF:
        return address - 0xC00000
    if 0x40 <= bank <= 0x7D:
        return address
    if 0x80 <= bank <= 0xBF and offset >= 0x8000:
        return ((bank & 0x3F) << 16) | offset
    if 0x00 <= bank <= 0x3F and offset >= 0x8000:
        return 0x400000 | (bank << 16) | offset
    return None


def exhirom_file_to_canonical_snes(offset: int) -> int:
    """Return the simple full-bank address used by the allocation manifest."""
    if 0 <= offset < EXPECTED_SOURCE_SIZE:
        return 0xC00000 + offset
    if BOOT_MIRROR_START <= offset < ALLOCATION_END:
        return offset
    raise ValueError(f"file offset {offset:#x} has no approved canonical map")


def _set_header_checksums(image: bytearray) -> None:
    # A checksum/complement pair always contributes $1FE to the byte sum.
    # Both header copies already contain valid pairs, so changing both pairs
    # to the final value does not change the sum used to derive that value.
    checksum = sum(image) & 0xFFFF
    complement = checksum ^ 0xFFFF
    for header in (HIROM_HEADER, EXHIROM_HEADER):
        _write_u16(image, header + HEADER_COMPLEMENT, complement)
        _write_u16(image, header + HEADER_CHECKSUM, checksum)


def expand_exhirom_scaffold(
    source: bytes, expected_sha1: str = EXPECTED_SOURCE_SHA1
) -> bytes:
    """Create the inert 8 MiB ExHiROM base entirely in memory."""
    validate_source(source, expected_sha1)
    image = bytearray([FILL_BYTE]) * TARGET_SIZE
    image[:EXPECTED_SOURCE_SIZE] = source
    image[BOOT_MIRROR_START:BOOT_MIRROR_END] = source[:0x10000]

    for header in (HIROM_HEADER, EXHIROM_HEADER):
        image[header + HEADER_MAP_MODE] = EXHIROM_FAST
        image[header + HEADER_ROM_SIZE] = ROM_SIZE_8_MIB

    _set_header_checksums(image)
    result = bytes(image)
    validate_exhirom_scaffold(result, source=source)
    return result


def validate_exhirom_scaffold(
    image: bytes, source: bytes | None = None
) -> None:
    if len(image) != TARGET_SIZE:
        raise ValueError(f"expected 8 MiB scaffold, got {len(image):#x}")
    checksum = sum(image) & 0xFFFF
    for label, header in (
        ("original-bank header", HIROM_HEADER),
        ("ExHiROM header", EXHIROM_HEADER),
    ):
        if image[header + HEADER_MAP_MODE] != EXHIROM_FAST:
            raise ValueError(f"{label} does not declare fast ExHiROM")
        if image[header + HEADER_ROM_SIZE] != ROM_SIZE_8_MIB:
            raise ValueError(f"{label} does not declare 8 MiB")
        complement = _read_u16(image, header + HEADER_COMPLEMENT)
        stored = _read_u16(image, header + HEADER_CHECKSUM)
        if complement ^ stored != 0xFFFF or stored != checksum:
            raise ValueError(f"{label} checksum is invalid")

    mutable = {
        HEADER_MAP_MODE,
        HEADER_ROM_SIZE,
        HEADER_COMPLEMENT,
        HEADER_COMPLEMENT + 1,
        HEADER_CHECKSUM,
        HEADER_CHECKSUM + 1,
    }
    if source is not None:
        if len(source) != EXPECTED_SOURCE_SIZE:
            raise ValueError("source comparison requires an unheadered 4 MiB ROM")
        allowed_source_changes = {
            HIROM_HEADER + relative for relative in mutable
        }
        actual_source_changes = {
            offset
            for offset, (old, new) in enumerate(
                zip(
                    source,
                    image[:EXPECTED_SOURCE_SIZE],
                    strict=True,
                )
            )
            if old != new
        }
        if actual_source_changes != allowed_source_changes:
            raise ValueError(
                "original 4 MiB changed outside the six header bytes"
            )

        actual_mirror_changes = {
            offset
            for offset, (old, new) in enumerate(
                zip(
                    source[:0x10000],
                    image[BOOT_MIRROR_START:BOOT_MIRROR_END],
                    strict=True,
                )
            )
            if old != new
        }
        if actual_mirror_changes != allowed_source_changes:
            raise ValueError("boot mirror differs outside the six header bytes")

    for index, (original, mirror) in enumerate(
        zip(
            image[:0x10000],
            image[BOOT_MIRROR_START:BOOT_MIRROR_END],
            strict=True,
        )
    ):
        if 0xFFC0 <= index < 0x10000 and index - 0xFFC0 in mutable:
            continue
        if original != mirror:
            raise ValueError(f"boot mirror mismatch at bank offset {index:#x}")

    if any(
        value != FILL_BYTE
        for value in image[ALLOCATION_START:NONCANONICAL_TAIL_END]
    ):
        raise ValueError("inert scaffold contains non-fill expanded data")


@dataclasses.dataclass(frozen=True)
class Allocation:
    allocation_id: str
    file_start: int
    size: int
    snes_start: int
    kind: str
    owner: str
    evidence: str
    alignment: int = 1
    no_bank_cross: bool = True

    @property
    def file_end(self) -> int:
        return self.file_start + self.size

    @property
    def snes_end(self) -> int:
        return self.snes_start + self.size


def validate_allocations(allocations: tuple[Allocation, ...]) -> None:
    seen_ids: set[str] = set()
    ordered = sorted(allocations, key=lambda item: item.file_start)
    previous: Allocation | None = None

    for allocation in ordered:
        if not allocation.allocation_id:
            raise ValueError("allocation ID must not be empty")
        if allocation.allocation_id in seen_ids:
            raise ValueError(f"duplicate allocation ID: {allocation.allocation_id}")
        seen_ids.add(allocation.allocation_id)
        if allocation.kind not in ALLOCATION_KINDS:
            raise ValueError(f"{allocation.allocation_id}: unknown kind")
        if allocation.evidence not in EVIDENCE_LEVELS:
            raise ValueError(f"{allocation.allocation_id}: unknown evidence")
        if allocation.size <= 0:
            raise ValueError(f"{allocation.allocation_id}: size must be positive")
        if (
            allocation.alignment <= 0
            or allocation.alignment & (allocation.alignment - 1)
        ):
            raise ValueError(
                f"{allocation.allocation_id}: alignment must be a power of two"
            )
        if allocation.file_start % allocation.alignment:
            raise ValueError(f"{allocation.allocation_id}: start is misaligned")
        if not (
            ALLOCATION_START <= allocation.file_start < allocation.file_end
            <= ALLOCATION_END
        ):
            raise ValueError(
                f"{allocation.allocation_id}: outside approved expanded banks"
            )
        canonical = exhirom_file_to_canonical_snes(allocation.file_start)
        if allocation.snes_start != canonical:
            raise ValueError(
                f"{allocation.allocation_id}: SNES/file mapping mismatch"
            )
        if allocation.no_bank_cross and (
            allocation.file_start >> 16 != (allocation.file_end - 1) >> 16
        ):
            raise ValueError(f"{allocation.allocation_id}: crosses a bank")
        if previous is not None and previous.file_end > allocation.file_start:
            raise ValueError(
                f"{previous.allocation_id} overlaps {allocation.allocation_id}"
            )
        previous = allocation


def allocation_manifest(
    allocations: tuple[Allocation, ...],
) -> dict[str, object]:
    validate_allocations(allocations)
    return {
        "schema_version": 1,
        "source_requirements": {
            "size": EXPECTED_SOURCE_SIZE,
            "sha1": EXPECTED_SOURCE_SHA1,
            "headered": False,
            "map_mode": HIROM_FAST,
            "rom_size_code": ROM_SIZE_4_MIB,
        },
        "inert_scaffold_verification": {
            "sha256": EXPECTED_INERT_SCAFFOLD_SHA256,
            "written_to_disk": False,
        },
        "mapping": {
            "type": "ExHiROM",
            "source_size": EXPECTED_SOURCE_SIZE,
            "target_size": TARGET_SIZE,
            "fill_byte": FILL_BYTE,
            "map_mode": EXHIROM_FAST,
            "rom_size_code": ROM_SIZE_8_MIB,
            "canonical_header_file_offset": EXHIROM_HEADER,
        },
        "allocation_pool": {
            "file_start": ALLOCATION_START,
            "file_end_exclusive": ALLOCATION_END,
            "snes_start": exhirom_file_to_canonical_snes(ALLOCATION_START),
            "snes_end_exclusive": ALLOCATION_END,
            "capacity": ALLOCATION_END - ALLOCATION_START,
        },
        "reserved_ranges": [
            {
                "id": "bank40_boot_and_lowbank_data_mirror",
                "file_start": BOOT_MIRROR_START,
                "file_end_exclusive": BOOT_MIRROR_END,
                "reason": (
                    "preserves reset, interrupt, soft-reset, and "
                    "$00:Fxxx vanilla mirrors"
                ),
            },
            {
                "id": "noncanonical_7e_7f_tail",
                "file_start": NONCANONICAL_TAIL_START,
                "file_end_exclusive": NONCANONICAL_TAIL_END,
                "reason": (
                    "CPU banks $7E/$7F are WRAM; fragmented low-bank mirrors "
                    "are intentionally excluded"
                ),
            },
        ],
        "allocations": [
            {
                **dataclasses.asdict(allocation),
                "file_end_exclusive": allocation.file_end,
                "snes_end_exclusive": allocation.snes_end,
                "file_start_hex": f"0x{allocation.file_start:06X}",
                "snes_start_hex": f"${allocation.snes_start:06X}",
            }
            for allocation in sorted(
                allocations, key=lambda item: item.file_start
            )
        ],
    }


def main() -> None:
    print(json.dumps(allocation_manifest(()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
