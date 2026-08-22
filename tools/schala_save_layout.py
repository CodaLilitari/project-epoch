#!/usr/bin/env python3
"""Model Project Epoch's vanilla-compatible ten-region save/load layout.

The production patch will relocate the complete vanilla $7E2830-$287F
compatibility block to $7E2CA0-$2CEF and use $7E2830 as Schala's live record.
This module pins both directions of the descriptor-table transformation
without containing ROM or save data.  Its immutable host helpers are source
proof only; they install no runtime hook and authorize no WRAM allocation.
"""

from __future__ import annotations

import dataclasses
import json
import struct


DESCRIPTOR_SIZE = 5
VANILLA_REGION_COUNT = 8
PROJECT_EPOCH_REGION_COUNT = 10
SERIALIZED_BYTES = 0x0834
SLOT_SIZE = 0x0A00
TABLE_STAGING_CAPACITY = 0x40
TABLE_COPY_MVN_A = PROJECT_EPOCH_REGION_COUNT * DESCRIPTOR_SIZE - 1
TABLE_LOOP_STOP = PROJECT_EPOCH_REGION_COUNT * DESCRIPTOR_SIZE
VANILLA_PC_RECORDS_WRAM_START = 0x2600
VANILLA_PC_RECORDS_BYTES = 0x0230
VANILLA_NEW_GAME_SEED_BYTES = 0x0280
NATURAL_PC07_WRAM_START = 0x2830
NATURAL_PC07_WRAM_END_EXCLUSIVE = 0x2880
RELOCATED_COMPATIBILITY_WRAM_START = 0x2CA0
RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE = 0x2CF0
SERIALIZED_COMPATIBILITY_START = 0x0430
SERIALIZED_COMPATIBILITY_END_EXCLUSIVE = 0x0480


@dataclasses.dataclass(frozen=True)
class SaveRegion:
    address: int
    bank: int
    length: int
    label: str


@dataclasses.dataclass(frozen=True)
class PartialLoadRegion:
    source_offset: int
    address: int
    bank: int
    length: int
    label: str


VANILLA_REGIONS = (
    SaveRegion(0x2400, 0x7E, 0x05B0, "main"),
    SaveRegion(0x2C23, 0x7E, 0x0033, "names"),
    SaveRegion(0x0400, 0x7E, 0x0010, "config"),
    SaveRegion(0x0100, 0x00, 0x0010, "lowram_0100"),
    SaveRegion(0x0000, 0x7F, 0x0200, "event_flags"),
    SaveRegion(0x027E, 0x00, 0x0002, "lowram_027e"),
    SaveRegion(0x0290, 0x00, 0x0011, "lowram_0290"),
    SaveRegion(0x2C7C, 0x7E, 0x001E, "cursor_state"),
)


PROJECT_EPOCH_REGIONS = (
    SaveRegion(0x2400, 0x7E, 0x0430, "main_through_pc6"),
    SaveRegion(0x2CA0, 0x7E, 0x0050, "relocated_compatibility"),
    SaveRegion(0x2880, 0x7E, 0x0130, "main_after_compatibility"),
    *VANILLA_REGIONS[1:],
)

PROJECT_EPOCH_NEW_GAME_PLUS_REGIONS = (
    PartialLoadRegion(0x0000, 0x2400, 0x7E, 0x0430, "main_through_pc6"),
    PartialLoadRegion(
        0x0430,
        0x2CA0,
        0x7E,
        0x0050,
        "relocated_compatibility",
    ),
    PartialLoadRegion(
        0x0480,
        0x2880,
        0x7E,
        0x0100,
        "partial_main_after_compatibility",
    ),
    PartialLoadRegion(0x05B0, 0x2C23, 0x7E, 0x0033, "names"),
)


def encode_region_table(regions: tuple[SaveRegion, ...]) -> bytes:
    encoded = bytearray()
    for region in regions:
        if not 0 <= region.address <= 0xFFFF:
            raise RuntimeError(f"{region.label}: address must fit in 16 bits")
        if not 0 <= region.bank <= 0xFF:
            raise RuntimeError(f"{region.label}: bank must fit in 8 bits")
        if not 1 <= region.length <= 0xFFFF:
            raise RuntimeError(f"{region.label}: invalid length")
        encoded += struct.pack("<HBH", region.address, region.bank, region.length)
    return bytes(encoded)


def destination_ranges(
    regions: tuple[SaveRegion, ...],
) -> tuple[tuple[int, int, SaveRegion], ...]:
    result: list[tuple[int, int, SaveRegion]] = []
    cursor = 0
    for region in regions:
        result.append((cursor, cursor + region.length, region))
        cursor += region.length
    return tuple(result)


def validate_layout() -> None:
    if len(VANILLA_REGIONS) != VANILLA_REGION_COUNT:
        raise RuntimeError("vanilla descriptor count changed")
    if len(PROJECT_EPOCH_REGIONS) != PROJECT_EPOCH_REGION_COUNT:
        raise RuntimeError("Project Epoch descriptor count changed")
    if sum(region.length for region in VANILLA_REGIONS) != SERIALIZED_BYTES:
        raise RuntimeError("vanilla serialized byte count changed")
    if (
        sum(region.length for region in PROJECT_EPOCH_REGIONS)
        != SERIALIZED_BYTES
    ):
        raise RuntimeError("Project Epoch serialized byte count is not vanilla")
    if sum(region.length for region in PROJECT_EPOCH_REGIONS[:3]) != 0x05B0:
        raise RuntimeError("split main region does not preserve $5B0 bytes")

    expected_split = (
        (0x2400, 0x7E, 0x0430),
        (0x2CA0, 0x7E, 0x0050),
        (0x2880, 0x7E, 0x0130),
    )
    actual_split = tuple(
        (region.address, region.bank, region.length)
        for region in PROJECT_EPOCH_REGIONS[:3]
    )
    if actual_split != expected_split:
        raise RuntimeError("Project Epoch main-region split changed")
    compatibility_matches = tuple(
        region
        for region in PROJECT_EPOCH_REGIONS
        if (
            region.bank == 0x7E
            and region.address == RELOCATED_COMPATIBILITY_WRAM_START
            and region.address + region.length
            == RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
        )
    )
    if len(compatibility_matches) != 1:
        raise RuntimeError(
            "relocated compatibility range is not represented exactly once"
        )
    for region in PROJECT_EPOCH_REGIONS:
        if region.bank != 0x7E:
            continue
        region_end = region.address + region.length
        if (
            region.address < NATURAL_PC07_WRAM_END_EXCLUSIVE
            and NATURAL_PC07_WRAM_START < region_end
        ):
            raise RuntimeError(
                "Project Epoch restore table writes the natural PC $07 range"
            )

    table = encode_region_table(PROJECT_EPOCH_REGIONS)
    if len(table) != TABLE_LOOP_STOP:
        raise RuntimeError("descriptor table byte count changed")
    if len(table) > TABLE_STAGING_CAPACITY:
        raise RuntimeError("descriptor table exceeds $7E9890 staging capacity")
    if TABLE_COPY_MVN_A + 1 != len(table):
        raise RuntimeError("MVN count is inconsistent with descriptor table")
    if SERIALIZED_BYTES > SLOT_SIZE:
        raise RuntimeError("serialized regions exceed vanilla slot size")

    expected_new_game_plus = (
        (0x0000, 0x2400, 0x7E, 0x0430),
        (0x0430, 0x2CA0, 0x7E, 0x0050),
        (0x0480, 0x2880, 0x7E, 0x0100),
        (0x05B0, 0x2C23, 0x7E, 0x0033),
    )
    actual_new_game_plus = tuple(
        (
            region.source_offset,
            region.address,
            region.bank,
            region.length,
        )
        for region in PROJECT_EPOCH_NEW_GAME_PLUS_REGIONS
    )
    if actual_new_game_plus != expected_new_game_plus:
        raise RuntimeError("Project Epoch New Game+ split changed")
    for region in PROJECT_EPOCH_NEW_GAME_PLUS_REGIONS:
        region_end = region.address + region.length
        if (
            region.bank == 0x7E
            and region.address < NATURAL_PC07_WRAM_END_EXCLUSIVE
            and NATURAL_PC07_WRAM_START < region_end
        ):
            raise RuntimeError("New Game+ split writes natural PC $07")
        if (
            region.bank == 0x7E
            and region.address < 0x29B0
            and 0x2980 < region_end
        ):
            raise RuntimeError("New Game+ split writes roster/joined state")


def serialize_regions(
    banks: dict[int, bytes],
    regions: tuple[SaveRegion, ...],
) -> bytes:
    result = bytearray()
    for region in regions:
        source = banks.get(region.bank)
        if source is None:
            raise RuntimeError(f"missing source bank ${region.bank:02X}")
        end = region.address + region.length
        if end > len(source):
            raise RuntimeError(f"{region.label}: source bank is too short")
        result += source[region.address:end]
    return bytes(result)


def _require_exact_bytes(
    value: object,
    length: int,
    label: str,
) -> bytes:
    if type(value) is not bytes or len(value) != length:
        raise RuntimeError(
            f"{label} must be immutable bytes of length ${length:04X}"
        )
    return value


def _clone_destination_banks(
    banks: dict[int, bytes],
) -> dict[int, bytearray]:
    if type(banks) is not dict:
        raise RuntimeError("destination banks must use one exact dict")
    destination_banks: dict[int, bytearray] = {}
    for bank, data in banks.items():
        if type(bank) is not int or not 0 <= bank <= 0xFF:
            raise RuntimeError("destination bank keys must be exact bytes")
        if type(data) is not bytes:
            raise RuntimeError(
                f"destination bank ${bank:02X} must be immutable bytes"
            )
        destination_banks[bank] = bytearray(data)
    return destination_banks


def _freeze_banks(
    banks: dict[int, bytearray],
) -> dict[int, bytes]:
    return {bank: bytes(data) for bank, data in banks.items()}


def restore_regions_from_slot(
    serialized_slot: bytes,
    banks: dict[int, bytes],
    regions: tuple[SaveRegion, ...],
) -> dict[int, bytes]:
    """Restore one exact vanilla slot through an explicit region table.

    Only the first ``SERIALIZED_BYTES`` bytes are copied, matching the native
    descriptor engine.  The caller must still supply the complete ``SLOT_SIZE``
    image because the untouched tail participates in vanilla checksum and
    sidecar-binding validation outside this layout helper.
    """

    _require_exact_bytes(serialized_slot, SLOT_SIZE, "serialized slot")
    if type(regions) is not tuple or not regions:
        raise RuntimeError("restore regions must use one nonempty exact tuple")

    destination_banks = _clone_destination_banks(banks)

    cursor = 0
    occupied: dict[int, list[tuple[int, int, str]]] = {}
    for region in regions:
        if type(region) is not SaveRegion:
            raise RuntimeError("restore table contains a non-SaveRegion entry")
        if type(region.address) is not int or not 0 <= region.address <= 0xFFFF:
            raise RuntimeError(f"{region.label}: invalid restore address")
        if type(region.bank) is not int or not 0 <= region.bank <= 0xFF:
            raise RuntimeError(f"{region.label}: invalid restore bank")
        if type(region.length) is not int or not 1 <= region.length <= 0xFFFF:
            raise RuntimeError(f"{region.label}: invalid restore length")
        if type(region.label) is not str or not region.label:
            raise RuntimeError("restore region label must be a nonempty string")
        destination = destination_banks.get(region.bank)
        if destination is None:
            raise RuntimeError(
                f"{region.label}: missing destination bank ${region.bank:02X}"
            )
        destination_end = region.address + region.length
        if destination_end > len(destination):
            raise RuntimeError(
                f"{region.label}: destination bank is too short"
            )
        if (
            region.bank == 0x7E
            and region.address < NATURAL_PC07_WRAM_END_EXCLUSIVE
            and NATURAL_PC07_WRAM_START < destination_end
        ):
            raise RuntimeError(
                f"{region.label}: restore table writes natural PC $07"
            )
        source_end = cursor + region.length
        if source_end > SERIALIZED_BYTES:
            raise RuntimeError(
                f"{region.label}: restore table exceeds serialized prefix"
            )
        for prior_start, prior_end, prior_label in occupied.setdefault(
            region.bank, []
        ):
            if region.address < prior_end and prior_start < destination_end:
                raise RuntimeError(
                    f"{region.label}: restore destination overlaps "
                    f"{prior_label}"
                )
        occupied[region.bank].append(
            (region.address, destination_end, region.label)
        )
        destination[region.address:destination_end] = serialized_slot[
            cursor:source_end
        ]
        cursor = source_end

    if cursor != SERIALIZED_BYTES:
        raise RuntimeError(
            "restore table does not consume the exact serialized prefix"
        )
    return _freeze_banks(destination_banks)


def split_new_game_seed(
    vanilla_seed: bytes,
    banks: dict[int, bytes],
    pc07_record: bytes,
) -> dict[int, bytes]:
    """Split vanilla's monolithic $280 new-game seed by namespace."""

    seed = _require_exact_bytes(
        vanilla_seed,
        VANILLA_NEW_GAME_SEED_BYTES,
        "vanilla new-game seed",
    )
    record = _require_exact_bytes(
        pc07_record,
        NATURAL_PC07_WRAM_END_EXCLUSIVE - NATURAL_PC07_WRAM_START,
        "PC $07 record",
    )
    destination_banks = _clone_destination_banks(banks)
    destination = destination_banks.get(0x7E)
    if (
        destination is None
        or len(destination) < RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
    ):
        raise RuntimeError("destination bank $7E is missing or too short")

    vanilla_records_end = (
        VANILLA_PC_RECORDS_WRAM_START + VANILLA_PC_RECORDS_BYTES
    )
    destination[
        VANILLA_PC_RECORDS_WRAM_START:vanilla_records_end
    ] = seed[:VANILLA_PC_RECORDS_BYTES]
    destination[
        RELOCATED_COMPATIBILITY_WRAM_START:
        RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
    ] = seed[VANILLA_PC_RECORDS_BYTES:]
    destination[
        NATURAL_PC07_WRAM_START:NATURAL_PC07_WRAM_END_EXCLUSIVE
    ] = record
    return _freeze_banks(destination_banks)


def finalize_attract_pc07_layout(
    banks: dict[int, bytes],
    compatibility_template: bytes,
    pc07_record: bytes,
) -> dict[int, bytes]:
    """Replace attract's PC07 overrun with explicit namespaced inputs."""

    compatibility = _require_exact_bytes(
        compatibility_template,
        RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
        - RELOCATED_COMPATIBILITY_WRAM_START,
        "attract compatibility template",
    )
    record = _require_exact_bytes(
        pc07_record,
        NATURAL_PC07_WRAM_END_EXCLUSIVE - NATURAL_PC07_WRAM_START,
        "PC $07 record",
    )
    destination_banks = _clone_destination_banks(banks)
    destination = destination_banks.get(0x7E)
    if (
        destination is None
        or len(destination) < RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
    ):
        raise RuntimeError("destination bank $7E is missing or too short")

    destination[
        RELOCATED_COMPATIBILITY_WRAM_START:
        RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
    ] = compatibility
    destination[
        NATURAL_PC07_WRAM_START:NATURAL_PC07_WRAM_END_EXCLUSIVE
    ] = record
    return _freeze_banks(destination_banks)


def restore_new_game_plus_regions_from_slot(
    serialized_slot: bytes,
    banks: dict[int, bytes],
) -> dict[int, bytes]:
    """Restore the exact translated New Game+ partial-load regions."""

    validate_layout()
    slot = _require_exact_bytes(serialized_slot, SLOT_SIZE, "serialized slot")
    destination_banks = _clone_destination_banks(banks)
    source_ranges: list[tuple[int, int, str]] = []
    destination_ranges_by_bank: dict[
        int, list[tuple[int, int, str]]
    ] = {}
    for region in PROJECT_EPOCH_NEW_GAME_PLUS_REGIONS:
        if (
            type(region.source_offset) is not int
            or not 0 <= region.source_offset < SLOT_SIZE
        ):
            raise RuntimeError(f"{region.label}: invalid source offset")
        if type(region.address) is not int or not 0 <= region.address <= 0xFFFF:
            raise RuntimeError(f"{region.label}: invalid restore address")
        if type(region.bank) is not int or not 0 <= region.bank <= 0xFF:
            raise RuntimeError(f"{region.label}: invalid restore bank")
        if type(region.length) is not int or not 1 <= region.length <= 0xFFFF:
            raise RuntimeError(f"{region.label}: invalid restore length")
        if type(region.label) is not str or not region.label:
            raise RuntimeError(
                "New Game+ region label must be a nonempty string"
            )

        source_end = region.source_offset + region.length
        if source_end > SLOT_SIZE:
            raise RuntimeError(f"{region.label}: source exceeds slot")
        for prior_start, prior_end, prior_label in source_ranges:
            if (
                region.source_offset < prior_end
                and prior_start < source_end
            ):
                raise RuntimeError(
                    f"{region.label}: source overlaps {prior_label}"
                )
        source_ranges.append(
            (region.source_offset, source_end, region.label)
        )

        destination = destination_banks.get(region.bank)
        if destination is None:
            raise RuntimeError(
                f"{region.label}: missing destination bank ${region.bank:02X}"
            )
        destination_end = region.address + region.length
        if destination_end > len(destination):
            raise RuntimeError(
                f"{region.label}: destination bank is too short"
            )
        occupied = destination_ranges_by_bank.setdefault(region.bank, [])
        for prior_start, prior_end, prior_label in occupied:
            if region.address < prior_end and prior_start < destination_end:
                raise RuntimeError(
                    f"{region.label}: destination overlaps {prior_label}"
                )
        occupied.append((region.address, destination_end, region.label))
        destination[region.address:destination_end] = slot[
            region.source_offset:source_end
        ]
    return _freeze_banks(destination_banks)


def manifest() -> dict[str, object]:
    validate_layout()
    return {
        "descriptor_count": PROJECT_EPOCH_REGION_COUNT,
        "descriptor_table_bytes": TABLE_LOOP_STOP,
        "table_copy_mvn_a": TABLE_COPY_MVN_A,
        "table_loop_stop": TABLE_LOOP_STOP,
        "serialized_bytes": SERIALIZED_BYTES,
        "slot_size": SLOT_SIZE,
        "restore_contract": {
            "input_slot_bytes": SLOT_SIZE,
            "copied_prefix_bytes": SERIALIZED_BYTES,
            "serialized_compatibility_start": SERIALIZED_COMPATIBILITY_START,
            "serialized_compatibility_end_exclusive": (
                SERIALIZED_COMPATIBILITY_END_EXCLUSIVE
            ),
            "relocated_compatibility_wram_start": (
                RELOCATED_COMPATIBILITY_WRAM_START
            ),
            "relocated_compatibility_wram_end_exclusive": (
                RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE
            ),
            "natural_pc07_wram_start": NATURAL_PC07_WRAM_START,
            "natural_pc07_wram_end_exclusive": (
                NATURAL_PC07_WRAM_END_EXCLUSIVE
            ),
            "natural_pc07_restore_action": "preserve-precleared",
        },
        "initialization_contract": {
            "evidence_scope": "source-shape-only",
            "normal_new_game": {
                "vanilla_seed_bytes": VANILLA_NEW_GAME_SEED_BYTES,
                "vanilla_pc_record_bytes": VANILLA_PC_RECORDS_BYTES,
                "compatibility_destination": (
                    RELOCATED_COMPATIBILITY_WRAM_START
                ),
                "pc07_destination": NATURAL_PC07_WRAM_START,
            },
            "attract": {
                "compatibility_input": "caller-supplied-exact-$50",
                "pc07_input": "caller-supplied-exact-$50",
            },
            "new_game_plus": {
                "evidence_scope": "translated-partial-copy-only",
                "natural_pc07_action": "preserve-caller-state",
                "roster_joined_action": "preserve-caller-state",
                "regions": [
                    {
                        "label": region.label,
                        "source_offset": region.source_offset,
                        "bank": region.bank,
                        "address": region.address,
                        "length": region.length,
                    }
                    for region in PROJECT_EPOCH_NEW_GAME_PLUS_REGIONS
                ],
            },
        },
        "regions": [
            {
                "label": region.label,
                "bank": region.bank,
                "address": region.address,
                "length": region.length,
                "destination_start": start,
                "destination_end_exclusive": end,
            }
            for start, end, region in destination_ranges(PROJECT_EPOCH_REGIONS)
        ],
    }


def main() -> None:
    print(json.dumps(manifest(), indent=2))


if __name__ == "__main__":
    main()
