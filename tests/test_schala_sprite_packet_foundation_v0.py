from __future__ import annotations

import importlib.util
import json
import pathlib
import struct
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "build_schala_sprite_packet_foundation_v0.py"
SPEC = importlib.util.spec_from_file_location(
    "build_schala_sprite_packet_foundation_v0", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaSpritePacketFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_raw, cls.source = TOOL.foundation.load_json(
            TOOL.DEFAULT_SOURCE
        )
        cls.frames = TOOL.foundation.validate_source(cls.source)
        cls.outputs = TOOL.build_outputs(cls.source_raw, cls.source)
        cls.frame_map = json.loads(
            cls.outputs[TOOL.FRAME_MAP_FILENAME].decode("utf-8")
        )
        cls.manifest = json.loads(
            cls.outputs[TOOL.MANIFEST_FILENAME].decode("utf-8")
        )

    def test_canonical_original_source_is_hash_pinned(self) -> None:
        self.assertEqual(
            TOOL.sha256(self.source_raw), TOOL.EXPECTED_SOURCE_SHA256
        )
        self.assertEqual(
            self.source["source_classification"],
            "original-hand-pixelled-target-grid",
        )
        self.assertEqual(
            self.manifest["canonical_source"]["sha256"],
            TOOL.EXPECTED_SOURCE_SHA256,
        )

    def test_packet_has_native_size_class_zero_shape(self) -> None:
        self.assertEqual(len(self.outputs[TOOL.ASSEMBLY_FILENAME]), 10 * 0x28)
        self.assertEqual(self.frame_map["frame_record_size"], 0x28)
        self.assertEqual(self.frame_map["tile_word_count"], 16)
        self.assertEqual(self.frame_map["object_count"], 4)
        self.assertEqual(self.frame_map["object_shape_tiles"], [2, 2])
        self.assertEqual(self.frame_map["tile_index_mask"], 0x07FF)

    def test_graphics_packet_contains_one_blank_and_eighty_art_tiles(
        self,
    ) -> None:
        graphics = self.outputs[TOOL.GRAPHICS_FILENAME]
        self.assertEqual(len(graphics), 81 * 32)
        self.assertEqual(graphics[:32], bytes(32))
        self.assertEqual(
            TOOL.sha256(graphics),
            "61bdecf43ad967ff5bd3c7604d7ce0708305a516e1e17d7cbbcabe949f3c791f",
        )
        self.assertEqual(
            self.manifest["graphics_tile_count_including_blank"], 81
        )

    def test_each_record_has_sixteen_bounded_unflipped_tile_words(
        self,
    ) -> None:
        assembly = self.outputs[TOOL.ASSEMBLY_FILENAME]
        self.assertEqual(
            TOOL.sha256(assembly),
            "11c7d77ec789853aca496b1bd38fdef35c437c31407000af74c7aa498bebb540",
        )
        for frame_index in range(10):
            words = struct.unpack_from(
                "<16H", assembly, frame_index * TOOL.FRAME_RECORD_SIZE
            )
            self.assertTrue(
                all(0 <= word <= TOOL.TILE_INDEX_MASK for word in words)
            )
            self.assertFalse(
                any(word & TOOL.HORIZONTAL_FLIP_MASK for word in words)
            )

    def test_object_cover_is_disjoint_on_every_visible_source_cell(
        self,
    ) -> None:
        active_counts = []
        for frame_record in self.frame_map["frames"]:
            active_counts.append(frame_record["active_object_count"])
            occupied = {
                tuple(cell)
                for cell in frame_record["occupied_source_cells"]
            }
            origins = [
                tuple(origin)
                for origin in frame_record["object_origins_tiles"]
                if origin is not None
            ]
            counts = {cell: 0 for cell in occupied}
            for origin in origins:
                for cell in TOOL._object_cells(origin):
                    if cell in counts:
                        counts[cell] += 1
            self.assertTrue(all(count == 1 for count in counts.values()))
        self.assertEqual(active_counts, [4, 4, 4, 4, 4, 3, 4, 4, 4, 4])

    def test_serialized_packets_reconstruct_all_source_pixels_exactly(
        self,
    ) -> None:
        TOOL.verify_exact_reconstruction(self.source, self.outputs)
        for frame_record in self.frame_map["frames"]:
            frame_id = frame_record["frame_id"]
            _, _, expected = TOOL.foundation.frame_pixels(
                self.frames[frame_id]
            )
            _, _, actual = TOOL.reconstruct_frame(
                self.outputs[TOOL.GRAPHICS_FILENAME],
                self.outputs[TOOL.ASSEMBLY_FILENAME],
                frame_record,
            )
            self.assertEqual(actual, expected)

    def test_packet_foundation_makes_no_runtime_or_rom_claim(self) -> None:
        self.assertTrue(self.manifest["native_shape_compatible"])
        self.assertTrue(self.manifest["source_reconstruction_exact"])
        palette_contract = self.manifest["palette_contract"]
        self.assertEqual(palette_contract["output_size"], 0x20)
        self.assertEqual(
            palette_contract["visible_indices_used"], list(range(1, 16))
        )
        self.assertEqual(
            palette_contract["vanilla_field_custom_palette_bytes"], 0x18
        )
        self.assertEqual(
            palette_contract["vanilla_field_custom_color_count"], 12
        )
        self.assertTrue(palette_contract["requires_full_palette_adapter"])
        for field in (
            "animation_blob",
            "complete_animation_sheet",
            "rom_allocation",
            "rom_integration",
            "rom_installable",
            "runtime_verified",
        ):
            self.assertIs(self.manifest[field], False)
        self.assertIn(
            "expanded_graphics_bank_nonflip_decoder",
            self.manifest["remaining_gates"],
        )
        self.assertIn(
            "expanded_gameplay_palette_loader",
            self.manifest["remaining_gates"],
        )

    def test_unpinned_source_and_impossible_cover_are_rejected(self) -> None:
        with self.assertRaisesRegex(TOOL.SpritePacketError, "SHA-256"):
            TOOL.compile_packets(
                self.source_raw + b"\n", self.source
            )
        with self.assertRaisesRegex(TOOL.SpritePacketError, "four"):
            TOOL.select_object_origins(
                {(0, 0), (2, 0), (4, 0), (6, 0), (8, 0)},
                10,
                2,
            )

    def test_signed_coordinate_codec_covers_native_offsets(self) -> None:
        for value in (-128, -40, -20, -4, 0, 4, 19, 127):
            self.assertEqual(
                TOOL.decode_signed_byte(TOOL._signed_byte(value)), value
            )
        with self.assertRaisesRegex(TOOL.SpritePacketError, "signed"):
            TOOL._signed_byte(128)

    def test_private_outputs_are_complete_and_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = pathlib.Path(directory)
            TOOL.write_outputs(self.outputs, destination)
            actual = {
                path.name: path.read_bytes()
                for path in destination.iterdir()
                if path.is_file()
            }
            self.assertEqual(actual, self.outputs)
        self.assertEqual(
            TOOL.sha256(self.outputs[TOOL.QA_SHEET_FILENAME]),
            "de89381fc1c3a81a6ee116d60700e8f0ab50ea259d15766f1de9965a046aacf2",
        )


if __name__ == "__main__":
    unittest.main()
