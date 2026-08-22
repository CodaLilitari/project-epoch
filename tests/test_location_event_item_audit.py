from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "audit_location_event_items.py"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("audit_location_event_items", TOOL_PATH)


def make_event(code: bytes) -> bytes:
    pointer_table = b"\x20\x00" * 16
    return bytes([1]) + pointer_table + code


def make_pinned_compatibility_event() -> bytes:
    object_count = TOOL.COMPATIBILITY_EVENT_OBJECT_ID + 1
    table_size = object_count * 32
    data = bytearray(0x06C6)
    for offset in range(0, table_size, 2):
        data[offset:offset + 2] = table_size.to_bytes(2, "little")
    for command_offset, opcode, address, _width in (
        TOOL.EXPECTED_COMPATIBILITY_RELOCATION_SITES
    ):
        data[command_offset:command_offset + 5] = bytes(
            (
                opcode,
                address & 0xFF,
                (address >> 8) & 0xFF,
                (address >> 16) & 0xFF,
                0,
            )
        )
    return bytes([object_count]) + bytes(data)


class LocationEventItemAuditTests(unittest.TestCase):
    def test_decompresses_literal_group(self) -> None:
        packet = b"\x09\x00\x00ABCDEFGH\xC0"
        result = TOOL.decompress_packet(packet, 0)
        self.assertEqual(result.data, b"ABCDEFGH")
        self.assertEqual(result.compressed_size, len(packet))
        self.assertTrue(result.small_width)
        self.assertEqual(result.addendum_count, 0)

    def test_decompresses_partial_group_addendum(self) -> None:
        packet = b"\x00\x00\xC3\x09\x00\xF8ABC\xC0"
        result = TOOL.decompress_packet(packet, 0)
        self.assertEqual(result.data, b"ABC")
        self.assertEqual(result.compressed_size, len(packet))
        self.assertEqual(result.addendum_count, 1)

    def test_parses_all_fixed_and_computed_item_operations(self) -> None:
        code = bytes.fromhex(
            "4F E8 08 "
            "C7 08 "
            "C9 E9 00 "
            "CA EA "
            "CB EB "
            "D5 00 EC "
            "D7 ED 09 "
            "00"
        )
        commands = TOOL.parse_event(0x123, make_event(code))
        references = TOOL.scan_item_references(commands)
        self.assertEqual(
            [reference.item_id for reference in references],
            [0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED],
        )
        self.assertEqual(references[0].resolution, "computed_constant")

    def test_classifies_equipment_field_as_generic_passthrough(self) -> None:
        code = bytes.fromhex("48 27 26 7E 08 C7 08 00")
        commands = TOOL.parse_event(0x123, make_event(code))
        references = TOOL.scan_item_references(commands)
        self.assertEqual(len(references), 1)
        self.assertIsNone(references[0].item_id)
        self.assertEqual(
            references[0].resolution,
            "runtime_equipment_passthrough",
        )
        self.assertEqual(references[0].source_addresses, (0x7E2627,))

    def test_non_equipment_indirect_source_remains_unresolved(self) -> None:
        code = bytes.fromhex("48 00 24 7E 08 C7 08 00")
        commands = TOOL.parse_event(0x123, make_event(code))
        references = TOOL.scan_item_references(commands)
        self.assertEqual(references[0].resolution, "computed_unresolved")

    def test_command_size_table_covers_every_opcode(self) -> None:
        self.assertEqual(len(TOOL.FIXED_COMMAND_SIZES), 0x100)
        self.assertTrue(all(size >= 1 for size in TOOL.FIXED_COMMAND_SIZES))

    def test_scans_absolute_reads_writes_and_copy_extents(self) -> None:
        code = bytes.fromhex(
            "48 30 28 7E 01 "
            "49 5B 28 7E 02 "
            "4C 37 28 7E 03 "
            "4E 5B 28 7E 04 00 AA BB "
            "00"
        )
        commands = TOOL.parse_event(0x123, make_event(code))
        references = TOOL.scan_absolute_memory_references(commands)
        self.assertEqual(
            [
                (
                    reference.opcode,
                    reference.address,
                    reference.width,
                    reference.access,
                )
                for reference in references
            ],
            [
                (0x48, 0x7E2830, 1, "read"),
                (0x49, 0x7E285B, 2, "read"),
                (0x4C, 0x7E2837, 1, "write"),
                (0x4E, 0x7E285B, 2, "write"),
            ],
        )
        self.assertFalse(
            TOOL._overlaps(
                references[0],
                TOOL.COMPATIBILITY_TAIL_WRAM_START,
                TOOL.COMPATIBILITY_WRAM_END_EXCLUSIVE,
            )
        )
        self.assertTrue(
            TOOL._overlaps(
                references[1],
                TOOL.COMPATIBILITY_TAIL_WRAM_START,
                TOOL.COMPATIBILITY_WRAM_END_EXCLUSIVE,
            )
        )

    def test_relocation_plan_changes_only_pinned_address_operands(self) -> None:
        source = make_pinned_compatibility_event()
        transformed, edits = TOOL._translate_pinned_compatibility_sites(
            TOOL.COMPATIBILITY_EVENT_ID,
            source,
        )
        self.assertEqual(len(transformed), len(source))
        self.assertEqual(len(edits), 12)
        self.assertEqual(
            [edit.new_address for edit in edits],
            [
                old_address
                + (
                    TOOL.RELOCATED_COMPATIBILITY_WRAM_START
                    - TOOL.COMPATIBILITY_WRAM_START
                )
                for _, _, old_address, _ in (
                    TOOL.EXPECTED_COMPATIBILITY_RELOCATION_SITES
                )
            ],
        )
        self.assertEqual(
            [
                index
                for index, (old, new) in enumerate(
                    zip(source, transformed)
                )
                if old != new
            ],
            [
                byte_offset
                for command_offset, _, _, _ in (
                    TOOL.EXPECTED_COMPATIBILITY_RELOCATION_SITES
                )
                for byte_offset in (command_offset + 2, command_offset + 3)
            ],
        )

    def test_relocation_plan_rejects_drifted_preimage(self) -> None:
        source = bytearray(make_pinned_compatibility_event())
        source[0x05C0 + 2] ^= 1
        with self.assertRaisesRegex(TOOL.AuditError, "pinned preimage"):
            TOOL._translate_pinned_compatibility_sites(
                TOOL.COMPATIBILITY_EVENT_ID,
                bytes(source),
            )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_absolute_memory_compatibility_hits_are_exact(self) -> None:
        report = TOOL.audit_rom(ROM_PATH.read_bytes())
        absolute = report["absolute_memory_references"]
        self.assertEqual(absolute["total"], 1511)
        self.assertEqual(absolute["compatibility_event_ids"], [0x11C])
        self.assertEqual(absolute["compatibility_location_ids"], [0x1D1])
        self.assertTrue(absolute["tail_has_no_absolute_command_overlap"])
        self.assertEqual(absolute["tail_hits"], [])
        self.assertTrue(
            absolute["relocated_candidate_has_no_preexisting_hits"]
        )
        self.assertEqual(
            absolute["relocated_candidate_range"],
            [0x7E2CA0, 0x7E2CEF],
        )
        self.assertEqual(
            absolute["relocated_candidate_preexisting_hits"],
            [],
        )
        self.assertEqual(
            [
                (
                    row["event_id"],
                    row["object_id"],
                    row["offset"],
                    row["opcode"],
                    row["address"],
                    row["width"],
                    row["location_ids"],
                )
                for row in absolute["compatibility_hits"]
            ],
            [
                (0x11C, 0x09, 0x05C0, 0x4C, 0x7E2830, 1, [0x1D1]),
                (0x11C, 0x09, 0x05C5, 0x48, 0x7E2837, 1, [0x1D1]),
                (0x11C, 0x09, 0x05CD, 0x4C, 0x7E2837, 1, [0x1D1]),
                (0x11C, 0x09, 0x0609, 0x4C, 0x7E2831, 1, [0x1D1]),
                (0x11C, 0x09, 0x060E, 0x48, 0x7E2838, 1, [0x1D1]),
                (0x11C, 0x09, 0x0616, 0x4C, 0x7E2838, 1, [0x1D1]),
                (0x11C, 0x09, 0x0652, 0x4C, 0x7E2832, 1, [0x1D1]),
                (0x11C, 0x09, 0x0657, 0x48, 0x7E2839, 1, [0x1D1]),
                (0x11C, 0x09, 0x065F, 0x4C, 0x7E2839, 1, [0x1D1]),
                (0x11C, 0x09, 0x06B4, 0x4C, 0x7E2834, 1, [0x1D1]),
                (0x11C, 0x09, 0x06B9, 0x48, 0x7E283B, 1, [0x1D1]),
                (0x11C, 0x09, 0x06C1, 0x4C, 0x7E283B, 1, [0x1D1]),
            ],
        )
        relocation = absolute["relocation_plan"]
        self.assertEqual(relocation["event_id"], 0x11C)
        self.assertEqual(relocation["object_id"], 0x09)
        self.assertEqual(relocation["snes_pointer"], 0xFAB19E)
        self.assertEqual(relocation["file_pointer"], 0x3AB19E)
        self.assertEqual(relocation["compressed_size"], 0x0776)
        self.assertEqual(relocation["decompressed_size"], 0x0C6B)
        self.assertEqual(
            relocation["source_sha256"],
            "31d5b222828eca6c1c91a309f1543a8f"
            "dccf2e2f5deea7a4074b7376eaa70d8a",
        )
        self.assertEqual(
            relocation["transformed_sha256"],
            "8e2952bd5e8c25eaf0ad4244dece929b"
            "6f4fc1eea8317ea707fcd782c898e50b",
        )
        self.assertTrue(relocation["packet_size_preserved"])
        self.assertEqual(relocation["edit_count"], 12)
        self.assertEqual(relocation["changed_byte_count"], 24)
        self.assertIn(
            "excluding its object-count byte",
            relocation["offset_basis"]["event_data_command_offset"],
        )
        self.assertIn(
            "including object-count byte",
            relocation["offset_basis"]["packet_address_operand_offset"],
        )
        self.assertEqual(
            [row["old_address"] for row in relocation["edits"]],
            [row["address"] for row in absolute["compatibility_hits"]],
        )
        self.assertEqual(
            [row["new_address"] for row in relocation["edits"]],
            [
                0x7E2CA0,
                0x7E2CA7,
                0x7E2CA7,
                0x7E2CA1,
                0x7E2CA8,
                0x7E2CA8,
                0x7E2CA2,
                0x7E2CA9,
                0x7E2CA9,
                0x7E2CA4,
                0x7E2CAB,
                0x7E2CAB,
            ],
        )
        _snes_pointer, file_pointer = TOOL.event_pointer(
            ROM_PATH.read_bytes(),
            TOOL.COMPATIBILITY_EVENT_ID,
        )
        packet = TOOL.decompress_packet(
            ROM_PATH.read_bytes(),
            file_pointer,
        )
        drifted = bytearray(packet.data)
        drifted[-1] ^= 1
        with self.assertRaisesRegex(TOOL.AuditError, "whole-packet preimage"):
            TOOL.build_relocated_compatibility_event(
                TOOL.COMPATIBILITY_EVENT_ID,
                bytes(drifted),
            )


if __name__ == "__main__":
    unittest.main()
