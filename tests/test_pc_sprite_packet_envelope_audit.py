from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "audit_pc_sprite_packet_envelopes.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_pc_sprite_packet_envelopes", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def make_table_only_rom() -> bytearray:
    rom = bytearray(TOOL.CANONICAL_ROM_SIZE)
    for packet in TOOL.PC_PACKETS:
        index = packet.logical_id
        gfx_offset = TOOL.PC_GFX_POINTER_TABLE_FILE + index * 3
        rom[gfx_offset : gfx_offset + 3] = packet.graphics_start_snes.to_bytes(
            3, "little"
        )
        assembly_offset = TOOL.PC_ASSEMBLY_POINTER_TABLE_FILE + index * 3
        rom[assembly_offset : assembly_offset + 3] = (
            packet.assembly_start_snes.to_bytes(3, "little")
        )
        descriptor_offset = (
            TOOL.PC_DESCRIPTOR_TABLE_FILE + index * TOOL.PC_DESCRIPTOR_STRIDE
        )
        rom[
            descriptor_offset : descriptor_offset + TOOL.PC_DESCRIPTOR_STRIDE
        ] = bytes((index, index, index, index, 0))
    for index, boundary in enumerate(TOOL.EXPECTED_ANIMATION_BOUNDARIES):
        offset = TOOL.PC_ANIMATION_BOUNDARY_TABLE_FILE + index * 2
        rom[offset : offset + 2] = boundary.to_bytes(2, "little")
    return rom


def make_record(tile_words: list[int], offsets: list[int]) -> bytes:
    assert len(tile_words) == TOOL.ASSEMBLY_TILE_WORD_COUNT
    assert len(offsets) == TOOL.ASSEMBLY_OFFSET_BYTE_COUNT
    return b"".join(word.to_bytes(2, "little") for word in tile_words) + bytes(
        value & 0xFF for value in offsets
    )


class PcSpritePacketEnvelopeAuditTests(unittest.TestCase):
    def test_layout_constants_cover_7264_aligned_graphics_tiles(self) -> None:
        TOOL.validate_layout_constants()
        self.assertEqual(len(TOOL.PC_PACKETS), 7)
        self.assertEqual(
            sum(
                packet.graphics_byte_count // TOOL.BYTES_PER_4BPP_TILE
                for packet in TOOL.PC_PACKETS
            ),
            7264,
        )

    def test_core_table_validation_pins_all_four_pc_table_families(self) -> None:
        rom = make_table_only_rom()
        TOOL.verify_core_tables(bytes(rom))
        rom[TOOL.PC_ASSEMBLY_POINTER_TABLE_FILE] ^= 1
        with self.assertRaisesRegex(ValueError, "assembly pointer"):
            TOOL.verify_core_tables(bytes(rom))

    def test_descriptor_validation_rejects_nonzero_pc_size_class(self) -> None:
        rom = make_table_only_rom()
        rom[
            TOOL.PC_DESCRIPTOR_TABLE_FILE + TOOL.PC_DESCRIPTOR_STRIDE - 1
        ] = 1
        with self.assertRaisesRegex(ValueError, "descriptor 0"):
            TOOL.verify_core_tables(bytes(rom))

    def test_animation_blob_requires_four_equal_facing_blocks(self) -> None:
        with self.assertRaisesRegex(ValueError, "aligned"):
            TOOL.analyze_animation_blob(b"\x00" * 15)
        blob = bytes(
            (
                0,
                1,
                0xFF,
                0xFF,
                2,
                0xFF,
                0xFF,
                0xFF,
            )
            * 4
        )
        result = TOOL.analyze_animation_blob(blob)
        self.assertEqual(result["facing_block_byte_count"], 8)
        self.assertEqual(result["entrypoint_stride"], 4)
        self.assertEqual(result["entrypoint_count_per_facing"], 2)
        self.assertEqual(result["unique_frame_ids"], [0, 1, 2])

    def test_animation_entrypoints_can_overlap_variable_length_sequences(
        self,
    ) -> None:
        facing_block = bytes((0, 1, 2, 3, 4, 5, 0xFF, 0xFF))
        result = TOOL.analyze_animation_blob(facing_block * 4)

        first = TOOL.animation_sequence_at_entrypoint(facing_block, 0)
        second = TOOL.animation_sequence_at_entrypoint(facing_block, 1)

        self.assertEqual(result["entrypoint_count_per_facing"], 2)
        self.assertGreater(len(first), result["entrypoint_stride"])
        self.assertEqual(first, bytes((0, 1, 2, 3, 4, 5)))
        self.assertEqual(second, bytes((4, 5)))
        self.assertEqual(first[result["entrypoint_stride"] :], second)

    def test_assembly_analysis_decodes_index_flip_and_offsets(self) -> None:
        record0 = make_record(
            [0, TOOL.HORIZONTAL_FLIP_MASK | 3] + [1] * 14,
            [-8, -16, 8, -16, -8, 0, 8, 0],
        )
        record1 = make_record(
            [5] * 16,
            [-7, -15, 9, -15, -7, 1, 9, 1],
        )
        result = TOOL.analyze_assembly_envelope(
            record0 + record1, [0, 1], graphics_tile_count=6
        )
        self.assertEqual(result["record_count_through_maximum_frame_id"], 2)
        self.assertEqual(result["object_count_per_record"], 4)
        self.assertEqual(result["maximum_referenced_tile_index"], 5)
        self.assertEqual(result["horizontal_flip_word_count"], 1)
        self.assertEqual(result["out_of_graphics_window_reference_count"], 0)
        self.assertEqual(result["minimum_referenced_object_x_offset"], -8)
        self.assertEqual(result["maximum_referenced_object_y_offset"], 1)

    def test_assembly_analysis_reports_out_of_window_index(self) -> None:
        record = make_record([7] + [0] * 15, [0] * 8)
        result = TOOL.analyze_assembly_envelope(
            record, [0], graphics_tile_count=7
        )
        self.assertEqual(result["out_of_graphics_window_reference_count"], 1)

    def test_assembly_analysis_rejects_ff_as_frame_id(self) -> None:
        record = make_record([0] * 16, [0] * 8)
        with self.assertRaisesRegex(ValueError, "sentinel"):
            TOOL.analyze_assembly_envelope(
                record * 0x100, [0xFF], graphics_tile_count=1
            )

    def test_rom_gate_rejects_unpinned_input_before_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "wrong.sfc"
            path.write_bytes(b"\x00" * TOOL.CANONICAL_ROM_SIZE)
            with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                TOOL.verify_canonical_rom(path)


if __name__ == "__main__":
    unittest.main()
