#!/usr/bin/env python3
"""Audit Chrono Trigger location-event item and absolute-memory references.

The tool is deliberately self-contained: it reads a user-supplied, headerless
US Rev0 ROM, validates its hashes, examines all 513 location-event pointer
entries, decompresses every structurally valid packet, walks the event
bytecode, and emits only aggregate/reference metadata. In addition to item
operations, it inventories opcodes $48-$4E and reports their overlap with the
vanilla $7E2830-$287F compatibility span. It never writes decompressed scripts
or ROM bytes.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
from collections.abc import ByteString, Iterable


CANONICAL_SIZE = 0x400000
CANONICAL_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

LOCATION_TABLE = 0x360000
LOCATION_RECORD_SIZE = 14
LOCATION_COUNT = 0x200
LOCATION_EVENT_ID_FIELD = 8
EVENT_POINTER_TABLE = 0x3CF9F0
EVENT_ID_COUNT = 0x201

CANDIDATE_IDS = frozenset(range(0xE8, 0xEF))
COMPATIBILITY_WRAM_START = 0x7E2830
COMPATIBILITY_WRAM_END_EXCLUSIVE = 0x7E2880
COMPATIBILITY_TAIL_WRAM_START = 0x7E285C
RELOCATED_COMPATIBILITY_WRAM_START = 0x7E2CA0
RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE = 0x7E2CF0
COMPATIBILITY_EVENT_ID = 0x11C
COMPATIBILITY_EVENT_OBJECT_ID = 0x09
COMPATIBILITY_EVENT_DECOMPRESSED_SIZE = 0x0C6B
COMPATIBILITY_EVENT_SOURCE_SHA256 = (
    "31d5b222828eca6c1c91a309f1543a8f"
    "dccf2e2f5deea7a4074b7376eaa70d8a"
)
COMPATIBILITY_EVENT_TRANSFORMED_SHA256 = (
    "8e2952bd5e8c25eaf0ad4244dece929b"
    "6f4fc1eea8317ea707fcd782c898e50b"
)
EXPECTED_COMPATIBILITY_RELOCATION_SITES = (
    (0x05C0, 0x4C, 0x7E2830, 1),
    (0x05C5, 0x48, 0x7E2837, 1),
    (0x05CD, 0x4C, 0x7E2837, 1),
    (0x0609, 0x4C, 0x7E2831, 1),
    (0x060E, 0x48, 0x7E2838, 1),
    (0x0616, 0x4C, 0x7E2838, 1),
    (0x0652, 0x4C, 0x7E2832, 1),
    (0x0657, 0x48, 0x7E2839, 1),
    (0x065F, 0x4C, 0x7E2839, 1),
    (0x06B4, 0x4C, 0x7E2834, 1),
    (0x06B9, 0x48, 0x7E283B, 1),
    (0x06C1, 0x4C, 0x7E283B, 1),
)

# Total command sizes (opcode plus operands) for the fixed-width SNES event
# commands.  The five context-dependent opcodes are resolved by
# command_size().  These values are pinned to the operand reads and returned
# script-PC increments behind EventScript_CommandTable at $C0:5D6E.
FIXED_COMMAND_SIZES = (
    1, 1, 3, 3, 3, 3, 3, 3, 1, 1, 2, 2, 2, 2, 2, 1,
    2, 2, 5, 6, 5, 5, 5, 1, 3, 2, 3, 1, 3, 1, 2, 2,
    2, 4, 4, 3, 3, 2, 2, 3, 3, 2, 1, 1, 3, 2, 2, 3,
    2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 1, 1, 2,
    2, 2, 2, 2, 2, 1, 1, 2, 5, 5, 5, 6, 5, 5, 7, 3,
    4, 3, 3, 4, 4, 2, 4, 1, 4, 4, 2, 3, 1, 3, 3, 3,
    4, 3, 1, 3, 3, 3, 3, 3, 1, 3, 1, 3, 1, 1, 1, 3,
    1, 2, 2, 2, 1, 2, 2, 2, 1, 1, 4, 5, 2, 2, 1, 2,
    2, 2, 2, 3, 2, 1, 1, 2, 2, 2, 2, 3, 3, 5, 2, 2,
    1, 1, 3, 1, 2, 2, 3, 3, 3, 3, 4, 1, 3, 3, 2, 2,
    3, 3, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1,
    1, 1, 1, 1, 1, 2, 2, 3, 4, 1, 1, 2, 1, 1, 1, 1,
    3, 2, 2, 3, 3, 1, 1, 2, 2, 3, 2, 2, 4, 3, 3, 3,
    2, 2, 3, 2, 2, 3, 2, 3, 3, 7, 1, 1, 5, 5, 5, 5,
    5, 5, 5, 2, 8, 8, 5, 3, 2, 1, 2, 3, 4, 1, 1, 1,
    2, 3, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 18, 2,
)

ITEM_OPCODE_INFO = {
    0xC7: ("add_from_script_memory", None),
    0xC9: ("if_has_item", 1),
    0xCA: ("add_item", 1),
    0xCB: ("remove_item", 1),
    0xD5: ("equip_item", 2),
    0xD7: ("get_item_quantity", 1),
}

ABSOLUTE_MEMORY_OPCODE_INFO = {
    0x48: ("read_absolute_8", "read", 1),
    0x49: ("read_absolute_16", "read", 2),
    0x4A: ("write_absolute_immediate_8", "write", 1),
    0x4B: ("write_absolute_immediate_16", "write", 2),
    0x4C: ("write_absolute_from_script_memory_8", "write", 1),
    0x4D: ("write_absolute_from_script_memory_16", "write", 2),
    0x4E: ("copy_literal_to_absolute", "write", None),
}


class AuditError(RuntimeError):
    """Raised when the canonical corpus cannot be decoded structurally."""


@dataclasses.dataclass(frozen=True)
class PacketInfo:
    data: bytes
    compressed_size: int
    small_width: bool
    addendum_count: int


@dataclasses.dataclass(frozen=True)
class Command:
    event_id: int
    object_id: int
    offset: int
    opcode: int
    payload: bytes


@dataclasses.dataclass(frozen=True)
class ItemReference:
    event_id: int
    object_id: int
    offset: int
    opcode: int
    operation: str
    item_id: int | None
    source_slot: int | None = None
    source_addresses: tuple[int, ...] = ()
    resolution: str = "fixed_operand"


@dataclasses.dataclass(frozen=True)
class AbsoluteMemoryReference:
    event_id: int
    object_id: int
    offset: int
    opcode: int
    operation: str
    access: str
    address: int
    width: int


@dataclasses.dataclass(frozen=True)
class CompatibilityRelocationEdit:
    event_id: int
    object_id: int
    event_data_command_offset: int
    packet_opcode_offset: int
    opcode: int
    packet_address_operand_offset: int
    old_address: int
    new_address: int
    width: int


def _u16(data: ByteString, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise AuditError(f"u16 read outside input at {offset:#x}")
    return data[offset] | (data[offset + 1] << 8)


def _u24(data: ByteString, offset: int) -> int:
    if offset < 0 or offset + 3 > len(data):
        raise AuditError(f"u24 read outside input at {offset:#x}")
    return (
        data[offset]
        | (data[offset + 1] << 8)
        | (data[offset + 2] << 16)
    )


def snes_hirom_to_file(pointer: int) -> int:
    """Convert a canonical $C0-$FF HiROM address to a file offset."""
    bank = pointer >> 16
    if not 0xC0 <= bank <= 0xFF:
        raise AuditError(f"pointer is outside canonical HiROM: ${pointer:06X}")
    return pointer & 0x3FFFFF


def validate_canonical_rom(rom: bytes) -> dict[str, str | int]:
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if len(rom) != CANONICAL_SIZE:
        raise AuditError(
            f"expected {CANONICAL_SIZE:#x} bytes, got {len(rom):#x}"
        )
    if sha1 != CANONICAL_SHA1 or sha256 != CANONICAL_SHA256:
        raise AuditError("ROM hash does not match headerless US Rev0")
    return {"size": len(rom), "sha1": sha1, "sha256": sha256}


def decompress_packet(rom: ByteString, start: int) -> PacketInfo:
    """Decode the LZ packet format used by $C3:0557."""
    if start < 0 or start + 3 > len(rom):
        raise AuditError(f"compressed packet starts outside ROM: {start:#x}")

    main_length = _u16(rom, start)
    source = start + 2
    end = source + main_length
    if end >= len(rom):
        raise AuditError(f"compressed packet end outside ROM: {end:#x}")

    small_width = bool(rom[end] & 0xC0)
    output = bytearray()
    addendum_count = 0
    last_end = end

    while True:
        if source == end:
            marker = rom[source]
            if marker & 0x3F == 0:
                return PacketInfo(
                    bytes(output),
                    source - start + 1,
                    small_width,
                    addendum_count,
                )
            new_end = start + _u16(rom, source + 1)
            if new_end <= source + 2 or new_end >= len(rom):
                raise AuditError(
                    f"invalid packet addendum {source:#x}->{new_end:#x}"
                )
            if new_end <= last_end:
                raise AuditError("packet addendum does not advance")
            source += 3
            end = new_end
            last_end = new_end
            addendum_count += 1
            continue
        if source > end:
            raise AuditError("compressed stream crossed packet boundary")

        header = rom[source]
        source += 1
        for bit in range(8):
            if source == end:
                break
            if not header & (1 << bit):
                output.append(rom[source])
                source += 1
                continue

            if source + 2 > end:
                raise AuditError("truncated LZ copy token")
            token = _u16(rom, source)
            source += 2
            if small_width:
                distance = token & 0x07FF
                length = (token >> 11) + 3
            else:
                distance = token & 0x0FFF
                length = (token >> 12) + 3
            if distance == 0 or distance > len(output):
                raise AuditError(
                    f"invalid LZ distance {distance:#x} at {source - 2:#x}"
                )
            for _ in range(length):
                output.append(output[-distance])
                if len(output) > 0x10000:
                    raise AuditError("decompressed packet exceeds 64 KiB")


def command_size(script: ByteString, offset: int) -> int:
    if offset < 0 or offset >= len(script):
        raise AuditError(f"command starts outside script at {offset:#x}")
    opcode = script[offset]
    size = FIXED_COMMAND_SIZES[opcode]

    def byte(relative: int) -> int:
        absolute = offset + relative
        if absolute >= len(script):
            raise AuditError(
                f"opcode ${opcode:02X} truncated at {offset:#x}"
            )
        return script[absolute]

    if opcode == 0x2E:
        mode = byte(1) >> 4
        if mode in (4, 5):
            size = 6
        elif mode == 8:
            copy_length = _u16(script, offset + 3) - 2
            if copy_length < 0:
                raise AuditError("opcode $2E has invalid copy length")
            size = 5 + copy_length
        else:
            raise AuditError(f"opcode $2E has unsupported mode {mode:#x}")
    elif opcode == 0x4E:
        copy_length = _u16(script, offset + 4) - 2
        if copy_length < 0:
            raise AuditError("opcode $4E has invalid copy length")
        size = 6 + copy_length
    elif opcode == 0x88:
        mode = byte(1) >> 4
        if mode == 0:
            size = 2
        elif mode in (2, 3):
            size = 4
        elif mode in (4, 5):
            size = 5
        elif mode == 8:
            copy_length = byte(2) - 2
            if copy_length < 0:
                raise AuditError("opcode $88 has invalid copy length")
            size = 4 + copy_length
        else:
            raise AuditError(f"opcode $88 has unsupported mode {mode:#x}")
    elif opcode == 0xF1:
        size = 2 if byte(1) == 0 else 3
    elif opcode == 0xFF:
        size = 5 if byte(1) in (0x90, 0x97) else 2

    if offset + size > len(script):
        raise AuditError(
            f"opcode ${opcode:02X} at {offset:#x} overruns script"
        )
    return size


def parse_event(event_id: int, event: bytes) -> list[Command]:
    """Walk each object's contiguous bytecode range exactly once."""
    if not event:
        raise AuditError(f"event ${event_id:02X} is empty")
    object_count = event[0]
    if object_count == 0 or object_count > 0x40:
        raise AuditError(
            f"event ${event_id:02X} invalid object count {object_count:#x}"
        )
    data = event[1:]
    table_size = object_count * 32
    if table_size > len(data):
        raise AuditError(f"event ${event_id:02X} pointer table is truncated")

    pointers = [
        _u16(data, index)
        for index in range(0, table_size, 2)
    ]
    if min(pointers) < table_size or max(pointers) > len(data):
        raise AuditError(f"event ${event_id:02X} pointer is out of bounds")

    object_starts = [pointers[obj * 16] for obj in range(object_count)]
    if object_starts != sorted(object_starts):
        raise AuditError(f"event ${event_id:02X} objects overlap")

    commands: list[Command] = []
    for object_id, start in enumerate(object_starts):
        end = (
            object_starts[object_id + 1]
            if object_id + 1 < object_count
            else len(data)
        )
        if start > end:
            raise AuditError(f"event ${event_id:02X} invalid object range")
        position = start
        while position < end:
            size = command_size(data, position)
            if position + size > end:
                raise AuditError(
                    f"event ${event_id:02X} object ${object_id:02X} "
                    f"command at {position:#x} crosses object boundary"
                )
            commands.append(
                Command(
                    event_id,
                    object_id,
                    position,
                    data[position],
                    bytes(data[position + 1:position + size]),
                )
            )
            position += size
        if position != end:
            raise AuditError(f"event ${event_id:02X} parse did not converge")
    return commands


def _script_memory_write_slot(command: Command) -> int | None:
    """Return the destination word-slot for commands that overwrite it."""
    payload = command.payload
    if command.opcode in (0x48, 0x49):
        return payload[3]
    if command.opcode in (0x4F, 0x51, 0x52, 0x5B, 0x5D, 0x5E, 0x5F,
                          0x61, 0x63, 0x64, 0x67, 0x69, 0x6B, 0x6F):
        return payload[1]
    if command.opcode in (0x50, 0x53, 0x54, 0x60):
        return payload[2]
    if command.opcode in (0x55, 0x71, 0x72, 0x73, 0x75, 0x76, 0x77):
        return payload[0]
    if command.opcode == 0xD7:
        return payload[1]
    return None


def _is_vanilla_equipment_field(address: int) -> bool:
    for pc_id in range(7):
        record = 0x7E2600 + pc_id * 0x50
        if record + 0x27 <= address <= record + 0x2A:
            return True
    return False


def scan_item_references(commands: Iterable[Command]) -> list[ItemReference]:
    references: list[ItemReference] = []
    prior_writers: dict[tuple[int, int, int], list[Command]] = {}
    for command in commands:
        info = ITEM_OPCODE_INFO.get(command.opcode)
        if info is not None:
            operation, item_operand = info
            if item_operand is None:
                source_slot = command.payload[0]
                writers = prior_writers.get(
                    (command.event_id, command.object_id, source_slot),
                    [],
                )
                if writers and all(writer.opcode == 0x48 for writer in writers):
                    source_addresses = tuple(sorted({
                        writer.payload[0]
                        | (writer.payload[1] << 8)
                        | (writer.payload[2] << 16)
                        for writer in writers
                    }))
                    if all(
                        _is_vanilla_equipment_field(address)
                        for address in source_addresses
                    ):
                        references.append(
                            ItemReference(
                                command.event_id,
                                command.object_id,
                                command.offset,
                                command.opcode,
                                operation,
                                None,
                                source_slot,
                                source_addresses,
                                "runtime_equipment_passthrough",
                            )
                        )
                    else:
                        references.append(
                            ItemReference(
                                command.event_id,
                                command.object_id,
                                command.offset,
                                command.opcode,
                                operation,
                                None,
                                source_slot,
                                source_addresses,
                                "computed_unresolved",
                            )
                        )
                elif len(writers) == 1 and writers[0].opcode == 0x4F:
                    references.append(
                        ItemReference(
                            command.event_id,
                            command.object_id,
                            command.offset,
                            command.opcode,
                            operation,
                            writers[0].payload[0],
                            source_slot,
                            (),
                            "computed_constant",
                        )
                    )
                elif len(writers) == 1 and writers[0].opcode == 0x50:
                    references.append(
                        ItemReference(
                            command.event_id,
                            command.object_id,
                            command.offset,
                            command.opcode,
                            operation,
                            writers[0].payload[0],
                            source_slot,
                            (),
                            "computed_constant",
                        )
                    )
                else:
                    references.append(
                        ItemReference(
                            command.event_id,
                            command.object_id,
                            command.offset,
                            command.opcode,
                            operation,
                            None,
                            source_slot,
                            (),
                            "computed_unresolved",
                        )
                    )
            else:
                payload_index = item_operand - 1
                references.append(
                    ItemReference(
                        command.event_id,
                        command.object_id,
                        command.offset,
                        command.opcode,
                        operation,
                        command.payload[payload_index],
                    )
                )

        destination = _script_memory_write_slot(command)
        if destination is not None:
            prior_writers.setdefault(
                (command.event_id, command.object_id, destination),
                [],
            ).append(command)
    return references


def scan_absolute_memory_references(
    commands: Iterable[Command],
) -> list[AbsoluteMemoryReference]:
    references: list[AbsoluteMemoryReference] = []
    for command in commands:
        info = ABSOLUTE_MEMORY_OPCODE_INFO.get(command.opcode)
        if info is None:
            continue
        operation, access, fixed_width = info
        if len(command.payload) < 3:
            raise AuditError(
                f"opcode ${command.opcode:02X} lacks an absolute address"
            )
        address = (
            command.payload[0]
            | (command.payload[1] << 8)
            | (command.payload[2] << 16)
        )
        if fixed_width is None:
            if len(command.payload) < 5:
                raise AuditError("opcode $4E lacks its copy length")
            width = _u16(command.payload, 3) - 2
        else:
            width = fixed_width
        if width <= 0 or address + width > 0x1000000:
            raise AuditError(
                f"opcode ${command.opcode:02X} has invalid absolute extent"
            )
        references.append(
            AbsoluteMemoryReference(
                command.event_id,
                command.object_id,
                command.offset,
                command.opcode,
                operation,
                access,
                address,
                width,
            )
        )
    return references


def _translate_pinned_compatibility_sites(
    event_id: int,
    event: bytes,
) -> tuple[bytes, tuple[CompatibilityRelocationEdit, ...]]:
    """Translate the exact 12 sites; caller owns whole-packet identity."""
    if event_id != COMPATIBILITY_EVENT_ID:
        raise AuditError(
            f"compatibility relocation requires event "
            f"${COMPATIBILITY_EVENT_ID:03X}"
        )

    commands = parse_event(event_id, event)
    references = [
        reference
        for reference in scan_absolute_memory_references(commands)
        if _overlaps(
            reference,
            COMPATIBILITY_WRAM_START,
            COMPATIBILITY_WRAM_END_EXCLUSIVE,
        )
    ]
    actual_sites = tuple(
        (
            reference.offset,
            reference.opcode,
            reference.address,
            reference.width,
        )
        for reference in references
        if reference.object_id == COMPATIBILITY_EVENT_OBJECT_ID
    )
    if (
        len(references) != len(EXPECTED_COMPATIBILITY_RELOCATION_SITES)
        or actual_sites != EXPECTED_COMPATIBILITY_RELOCATION_SITES
    ):
        raise AuditError(
            "event $11C compatibility sites do not match the pinned preimage"
        )

    relocated = bytearray(event)
    edits: list[CompatibilityRelocationEdit] = []
    delta = (
        RELOCATED_COMPATIBILITY_WRAM_START - COMPATIBILITY_WRAM_START
    )
    for reference in references:
        if reference.object_id != COMPATIBILITY_EVENT_OBJECT_ID:
            raise AuditError("compatibility reference escaped object $09")
        packet_opcode_offset = reference.offset + 1
        packet_address_operand_offset = reference.offset + 2
        if packet_address_operand_offset + 3 > len(relocated):
            raise AuditError("absolute-address operand is outside event packet")
        preimage = (
            relocated[packet_address_operand_offset]
            | (relocated[packet_address_operand_offset + 1] << 8)
            | (relocated[packet_address_operand_offset + 2] << 16)
        )
        if preimage != reference.address:
            raise AuditError(
                "absolute-address operand does not match parsed preimage"
            )
        new_address = reference.address + delta
        relocated[
            packet_address_operand_offset:packet_address_operand_offset + 3
        ] = bytes(
            (
                new_address & 0xFF,
                (new_address >> 8) & 0xFF,
                (new_address >> 16) & 0xFF,
            )
        )
        edits.append(
            CompatibilityRelocationEdit(
                event_id=reference.event_id,
                object_id=reference.object_id,
                event_data_command_offset=reference.offset,
                packet_opcode_offset=packet_opcode_offset,
                opcode=reference.opcode,
                packet_address_operand_offset=packet_address_operand_offset,
                old_address=reference.address,
                new_address=new_address,
                width=reference.width,
            )
        )

    transformed = bytes(relocated)
    transformed_references = scan_absolute_memory_references(
        parse_event(event_id, transformed)
    )
    transformed_sites = tuple(
        (
            reference.offset,
            reference.opcode,
            reference.address,
            reference.width,
        )
        for reference in transformed_references
        if reference.object_id == COMPATIBILITY_EVENT_OBJECT_ID
        and any(
            reference.offset == edit.event_data_command_offset
            for edit in edits
        )
    )
    expected_transformed_sites = tuple(
        (
            edit.event_data_command_offset,
            edit.opcode,
            edit.new_address,
            edit.width,
        )
        for edit in edits
    )
    if transformed_sites != expected_transformed_sites:
        raise AuditError("relocated event does not reparse to translated sites")
    if any(
        _overlaps(
            reference,
            COMPATIBILITY_WRAM_START,
            COMPATIBILITY_WRAM_END_EXCLUSIVE,
        )
        for reference in transformed_references
    ):
        raise AuditError("relocated event still touches the original block")
    destination_references = [
        reference
        for reference in transformed_references
        if _overlaps(
            reference,
            RELOCATED_COMPATIBILITY_WRAM_START,
            RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE,
        )
    ]
    destination_sites = tuple(
        (
            reference.object_id,
            reference.offset,
            reference.opcode,
            reference.address,
            reference.width,
        )
        for reference in destination_references
    )
    expected_destination_sites = tuple(
        (
            edit.object_id,
            edit.event_data_command_offset,
            edit.opcode,
            edit.new_address,
            edit.width,
        )
        for edit in edits
    )
    if destination_sites != expected_destination_sites:
        raise AuditError(
            "relocated destination has an unplanned absolute-memory reference"
        )

    allowed_offsets = {
        edit.packet_address_operand_offset + byte_index
        for edit in edits
        for byte_index in range(3)
    }
    changed_offsets = {
        index
        for index, (old, new) in enumerate(zip(event, transformed))
        if old != new
    }
    if not changed_offsets or not changed_offsets <= allowed_offsets:
        raise AuditError("relocated event changed a non-address byte")
    return transformed, tuple(edits)


def build_relocated_compatibility_event(
    event_id: int,
    event: bytes,
) -> tuple[bytes, tuple[CompatibilityRelocationEdit, ...]]:
    """Translate only the complete pinned event $11C packet in memory.

    The public builder rejects any whole-packet drift. It does not recompress
    data, allocate ROM space, mutate an image, or approve an install site.
    """
    if (
        len(event) != COMPATIBILITY_EVENT_DECOMPRESSED_SIZE
        or hashlib.sha256(event).hexdigest()
        != COMPATIBILITY_EVENT_SOURCE_SHA256
    ):
        raise AuditError(
            "event $11C whole-packet preimage does not match the pinned "
            "size and SHA-256"
        )
    transformed, edits = _translate_pinned_compatibility_sites(
        event_id,
        event,
    )
    if (
        hashlib.sha256(transformed).hexdigest()
        != COMPATIBILITY_EVENT_TRANSFORMED_SHA256
    ):
        raise AuditError("event $11C transformed SHA-256 does not match")
    return transformed, edits


def _overlaps(
    reference: AbsoluteMemoryReference,
    start: int,
    end_exclusive: int,
) -> bool:
    return (
        reference.address < end_exclusive
        and start < reference.address + reference.width
    )


def location_event_ids(rom: ByteString) -> list[int]:
    ids = []
    for location_id in range(LOCATION_COUNT):
        offset = (
            LOCATION_TABLE
            + location_id * LOCATION_RECORD_SIZE
            + LOCATION_EVENT_ID_FIELD
        )
        event_id = _u16(rom, offset)
        if event_id >= EVENT_ID_COUNT:
            raise AuditError(
                f"location ${location_id:03X} event ID ${event_id:04X} "
                "is outside the canonical table"
            )
        ids.append(event_id)
    return ids


def event_pointer(rom: ByteString, event_id: int) -> tuple[int, int]:
    if not 0 <= event_id < EVENT_ID_COUNT:
        raise AuditError(f"invalid event ID: {event_id:#x}")
    table_offset = EVENT_POINTER_TABLE + event_id * 3
    snes_pointer = _u24(rom, table_offset)
    return snes_pointer, snes_hirom_to_file(snes_pointer)


def audit_rom(rom: bytes) -> dict[str, object]:
    rom_identity = validate_canonical_rom(rom)
    location_ids = location_event_ids(rom)
    unique_location_ids = sorted(set(location_ids))
    all_event_ids = list(range(EVENT_ID_COUNT))

    all_commands: list[Command] = []
    packet_rows: list[dict[str, int | bool]] = []
    pointers: set[int] = set()
    decoded_pointers: set[int] = set()
    command_instances = 0
    unique_packet_addenda = 0
    referenced_set = set(unique_location_ids)
    non_script_entries: list[dict[str, int | str]] = []
    compatibility_relocation: dict[str, object] | None = None
    for event_id in all_event_ids:
        snes_pointer, file_pointer = event_pointer(rom, event_id)
        try:
            packet = decompress_packet(rom, file_pointer)
        except AuditError as exc:
            non_script_entries.append(
                {
                    "event_id": event_id,
                    "snes_pointer": snes_pointer,
                    "stage": "decompress",
                    "reason": str(exc),
                }
            )
            pointers.add(snes_pointer)
            continue
        if not packet.data:
            non_script_entries.append(
                {
                    "event_id": event_id,
                    "snes_pointer": snes_pointer,
                    "stage": "decompress",
                    "reason": "empty packet",
                }
            )
            pointers.add(snes_pointer)
            continue
        try:
            commands = parse_event(event_id, packet.data)
        except AuditError as exc:
            non_script_entries.append(
                {
                    "event_id": event_id,
                    "snes_pointer": snes_pointer,
                    "stage": "parse",
                    "reason": str(exc),
                }
            )
            pointers.add(snes_pointer)
            continue
        if event_id == COMPATIBILITY_EVENT_ID:
            transformed, edits = build_relocated_compatibility_event(
                event_id,
                packet.data,
            )
            changed_offsets = [
                index
                for index, (old, new) in enumerate(
                    zip(packet.data, transformed)
                )
                if old != new
            ]
            compatibility_relocation = {
                "event_id": event_id,
                "object_id": COMPATIBILITY_EVENT_OBJECT_ID,
                "snes_pointer": snes_pointer,
                "file_pointer": file_pointer,
                "compressed_size": packet.compressed_size,
                "decompressed_size": len(packet.data),
                "source_sha256": hashlib.sha256(packet.data).hexdigest(),
                "transformed_sha256": hashlib.sha256(transformed).hexdigest(),
                "packet_size_preserved": len(transformed) == len(packet.data),
                "edit_count": len(edits),
                "changed_byte_count": len(changed_offsets),
                "changed_offsets": changed_offsets,
                "offset_basis": {
                    "event_data_command_offset": (
                        "decompressed event excluding its object-count byte"
                    ),
                    "packet_opcode_offset": (
                        "full decompressed packet including object-count byte"
                    ),
                    "packet_address_operand_offset": (
                        "full decompressed packet including object-count byte"
                    ),
                    "changed_offsets": (
                        "full decompressed packet including object-count byte"
                    ),
                },
                "edits": [
                    dataclasses.asdict(edit)
                    for edit in edits
                ],
                "scope": (
                    "decompressed-packet-only; no recompression, ROM "
                    "allocation, image write, or patch emission"
                ),
            }
        command_instances += len(commands)
        if snes_pointer not in decoded_pointers:
            all_commands.extend(commands)
            decoded_pointers.add(snes_pointer)
            unique_packet_addenda += packet.addendum_count
        pointers.add(snes_pointer)
        packet_rows.append(
            {
                "event_id": event_id,
                "snes_pointer": snes_pointer,
                "compressed_size": packet.compressed_size,
                "decompressed_size": len(packet.data),
                "small_width": packet.small_width,
                "addendum_count": packet.addendum_count,
                "command_count": len(commands),
            }
        )

    references = scan_item_references(all_commands)
    absolute_references = scan_absolute_memory_references(all_commands)
    compatibility_references = [
        reference
        for reference in absolute_references
        if _overlaps(
            reference,
            COMPATIBILITY_WRAM_START,
            COMPATIBILITY_WRAM_END_EXCLUSIVE,
        )
    ]
    compatibility_tail_references = [
        reference
        for reference in absolute_references
        if _overlaps(
            reference,
            COMPATIBILITY_TAIL_WRAM_START,
            COMPATIBILITY_WRAM_END_EXCLUSIVE,
        )
    ]
    relocated_candidate_references = [
        reference
        for reference in absolute_references
        if _overlaps(
            reference,
            RELOCATED_COMPATIBILITY_WRAM_START,
            RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE,
        )
    ]
    locations_by_event: dict[int, list[int]] = {}
    for location_id, event_id in enumerate(location_ids):
        locations_by_event.setdefault(event_id, []).append(location_id)
    candidate_hits = [
        reference
        for reference in references
        if reference.item_id in CANDIDATE_IDS
    ]
    unresolved = [
        reference
        for reference in references
        if reference.resolution == "computed_unresolved"
    ]
    passthrough = [
        reference
        for reference in references
        if reference.resolution == "runtime_equipment_passthrough"
    ]

    opcode_counts: dict[str, int] = {}
    for reference in references:
        key = f"{reference.opcode:02X}"
        opcode_counts[key] = opcode_counts.get(key, 0) + 1
    fixed_domains: dict[str, dict[str, int | None]] = {}
    for opcode in (0xC9, 0xCA, 0xCB, 0xD5, 0xD7):
        values = sorted({
            reference.item_id
            for reference in references
            if reference.opcode == opcode and reference.item_id is not None
        })
        fixed_domains[f"{opcode:02X}"] = {
            "distinct_count": len(values),
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
        }

    return {
        "schema_version": 1,
        "evidence": "verified-static",
        "rom": rom_identity,
        "coverage": {
            "location_records": len(location_ids),
            "pointer_entries_examined": len(all_event_ids),
            "location_referenced_event_ids": len(unique_location_ids),
            "unreferenced_event_ids": [
                event_id
                for event_id in all_event_ids
                if event_id not in referenced_set
            ],
            "event_id_range": [0, EVENT_ID_COUNT - 1],
            "unique_packet_pointers": len(pointers),
            "unique_decoded_packet_pointers": len(decoded_pointers),
            "packets_decompressed": len(packet_rows),
            "non_script_entries": non_script_entries,
            "location_referenced_non_script_event_ids": [
                row["event_id"]
                for row in non_script_entries
                if row["event_id"] in referenced_set
            ],
            "unreferenced_non_script_event_ids": [
                row["event_id"]
                for row in non_script_entries
                if row["event_id"] not in referenced_set
            ],
            "commands_parsed": len(all_commands),
            "event_id_command_instances": command_instances,
            "packet_addenda": sum(
                int(row["addendum_count"]) for row in packet_rows
            ),
            "unique_packet_addenda": unique_packet_addenda,
        },
        "item_references": {
            "total": len(references),
            "by_opcode": dict(sorted(opcode_counts.items())),
            "fixed_operand_domains": fixed_domains,
            "candidate_range": [min(CANDIDATE_IDS), max(CANDIDATE_IDS)],
            "candidate_fixed_hits": [
                dataclasses.asdict(reference)
                for reference in candidate_hits
            ],
            "computed_unresolved": [
                dataclasses.asdict(reference)
                for reference in unresolved
            ],
            "runtime_equipment_passthrough": [
                dataclasses.asdict(reference)
                for reference in passthrough
            ],
            "runtime_equipment_source_addresses": sorted({
                address
                for reference in passthrough
                for address in reference.source_addresses
            }),
            "candidate_range_unclaimed": (
                not candidate_hits and not unresolved
            ),
        },
        "absolute_memory_references": {
            "opcode_range": [0x48, 0x4E],
            "total": len(absolute_references),
            "compatibility_range": [
                COMPATIBILITY_WRAM_START,
                COMPATIBILITY_WRAM_END_EXCLUSIVE - 1,
            ],
            "compatibility_hits": [
                {
                    **dataclasses.asdict(reference),
                    "location_ids": locations_by_event.get(
                        reference.event_id, []
                    ),
                }
                for reference in compatibility_references
            ],
            "compatibility_event_ids": sorted({
                reference.event_id
                for reference in compatibility_references
            }),
            "compatibility_location_ids": sorted({
                location_id
                for reference in compatibility_references
                for location_id in locations_by_event.get(
                    reference.event_id, []
                )
            }),
            "tail_range": [
                COMPATIBILITY_TAIL_WRAM_START,
                COMPATIBILITY_WRAM_END_EXCLUSIVE - 1,
            ],
            "tail_hits": [
                {
                    **dataclasses.asdict(reference),
                    "location_ids": locations_by_event.get(
                        reference.event_id, []
                    ),
                }
                for reference in compatibility_tail_references
            ],
            "tail_has_no_absolute_command_overlap": (
                not compatibility_tail_references
            ),
            "relocated_candidate_range": [
                RELOCATED_COMPATIBILITY_WRAM_START,
                RELOCATED_COMPATIBILITY_WRAM_END_EXCLUSIVE - 1,
            ],
            "relocated_candidate_preexisting_hits": [
                dataclasses.asdict(reference)
                for reference in relocated_candidate_references
            ],
            "relocated_candidate_has_no_preexisting_hits": (
                not relocated_candidate_references
            ),
            "relocation_plan": compatibility_relocation,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=pathlib.Path)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON instead of indented JSON",
    )
    args = parser.parse_args()
    result = audit_rom(args.rom.read_bytes())
    print(
        json.dumps(
            result,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
