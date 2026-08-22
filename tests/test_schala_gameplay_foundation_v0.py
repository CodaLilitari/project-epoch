from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "build_schala_gameplay_foundation_v0.py"
SOURCE_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "gameplay"
    / "schala_gameplay_foundation_v0.json"
)
MANIFEST_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "gameplay"
    / "manifest_v0.json"
)

SPEC = importlib.util.spec_from_file_location(
    "build_schala_gameplay_foundation_v0", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class GameplayFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_raw, cls.source = TOOL.load_json(SOURCE_PATH)
        _, cls.manifest = TOOL.load_json(MANIFEST_PATH)
        cls.frames = TOOL.validate_source(cls.source)
        cls.outputs = TOOL.build_outputs(cls.source_raw, cls.source)

    def test_separate_manifest_pins_source_builder_and_outputs(self) -> None:
        TOOL.verify_source_manifest(
            self.manifest, self.source_raw, self.outputs
        )
        self.assertEqual(
            self.manifest["status"], "partial-animation-foundation"
        )
        self.assertIs(self.manifest["rom_integration"], False)

    def test_required_frame_set_dimensions_and_walk_cycle(self) -> None:
        self.assertEqual(set(self.frames), set(TOOL.REQUIRED_FRAME_IDS))
        for frame_id in TOOL.FIELD_FRAME_IDS:
            self.assertEqual(
                TOOL.frame_pixels(self.frames[frame_id])[:2], (24, 32)
            )
        for frame_id in TOOL.BATTLE_FRAME_IDS:
            self.assertEqual(
                TOOL.frame_pixels(self.frames[frame_id])[:2], (40, 40)
            )
        self.assertEqual(
            [
                self.frames[
                    f"schala_field_walk_down_f0{index}_v0"
                ]["cycle_index"]
                for index in range(3)
            ],
            [0, 1, 2],
        )

    def test_single_palette_is_indexed_and_transparency_is_zero(self) -> None:
        self.assertEqual(self.source["palette"]["transparent_index"], 0)
        self.assertEqual(len(TOOL.palette_rgb(self.source)), 16)
        used = set()
        for frame in self.frames.values():
            _, _, pixels = TOOL.frame_pixels(frame)
            self.assertTrue(all(0 <= pixel <= 15 for pixel in pixels))
            used.update(pixels)
        self.assertEqual(used, set(range(16)))
        self.assertEqual(len(self.outputs[TOOL.PALETTE_FILENAME]), 0x20)

    def test_packed_sizes_and_snes_4bpp_round_trip(self) -> None:
        for frame_id, frame in self.frames.items():
            width, height, pixels = TOOL.frame_pixels(frame)
            packed = self.outputs[f"{frame_id}.4bpp"]
            self.assertEqual(
                len(packed), (width // 8) * (height // 8) * 32
            )
            self.assertEqual(
                TOOL.decode_snes_4bpp(packed, width, height), pixels
            )

    def test_provenance_excludes_rom_npc_pc_and_concept_pixels(self) -> None:
        self.assertEqual(
            self.source["source_classification"],
            "original-hand-pixelled-target-grid",
        )
        authorship = self.source["pixel_authorship"]
        for flag in (
            "imported_layers",
            "imported_pixels",
            "rom_or_extracted_tile_input",
            "concept_bitmap_input",
            "concept_pixels_sampled",
            "concept_palette_sampled",
            "automatic_resizing",
        ):
            self.assertIs(authorship[flag], False)
        concepts = [
            item
            for item in self.source["references"]
            if item.get("source_classification")
            == "generated-concept-reference"
        ]
        self.assertEqual(len(concepts), 2)
        for concept in concepts:
            self.assertIs(concept["rom_eligible"], False)
            self.assertIs(concept["opened_by_pixel_author"], False)
            self.assertIs(concept["pixels_or_palette_sampled"], False)

    def test_frame_and_unique_tile_budgets(self) -> None:
        report = TOOL.tile_budget_report(self.frames)
        for frame_id in TOOL.FIELD_FRAME_IDS:
            self.assertLessEqual(
                report["occupied_tiles_by_frame"][frame_id], 12
            )
        self.assertLessEqual(
            report["occupied_tiles_by_frame"][TOOL.BATTLE_FRAME_IDS[0]], 16
        )
        for frame_id in TOOL.BATTLE_FRAME_IDS[1:]:
            self.assertLessEqual(
                report["occupied_tiles_by_frame"][frame_id], 20
            )
        self.assertLessEqual(
            report["unique_nontransparent_tiles_total"], 352
        )

    def test_no_inappropriate_nontrivial_exact_or_flipped_tile_sharing(
        self,
    ) -> None:
        audit = TOOL.tile_sharing_audit(self.frames)
        self.assertEqual(audit["prohibited_cross_context_groups"], [])
        self.assertEqual(
            audit["comparison"],
            "exact-index tiles including H/V/HV flips",
        )

    def test_field_and_neutral_ready_frames_contain_no_magic_focus(self) -> None:
        for frame_id in TOOL.FIELD_FRAME_IDS + (TOOL.BATTLE_FRAME_IDS[0],):
            self.assertNotIn(
                15, TOOL.frame_pixels(self.frames[frame_id])[2]
            )
        for frame_id in TOOL.BATTLE_FRAME_IDS[1:]:
            self.assertIn(15, TOOL.frame_pixels(self.frames[frame_id])[2])

    def test_pngs_are_decoded_from_packed_bytes(self) -> None:
        for frame_id, frame in self.frames.items():
            width, height, _ = TOOL.frame_pixels(frame)
            image = Image.open(io.BytesIO(self.outputs[f"{frame_id}.png"]))
            self.assertEqual(image.mode, "P")
            self.assertEqual(image.size, (width, height))
            self.assertEqual(image.info.get("transparency"), 0)
            self.assertEqual(
                tuple(image.tobytes()),
                TOOL.decode_snes_4bpp(
                    self.outputs[f"{frame_id}.4bpp"], width, height
                ),
            )

    def test_private_output_write_is_complete_and_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = pathlib.Path(directory)
            TOOL.write_outputs(self.outputs, output_dir)
            actual = {
                path.name: path.read_bytes()
                for path in output_dir.iterdir()
                if path.is_file()
            }
            self.assertEqual(actual, self.outputs)
            build_manifest = json.loads(
                actual[TOOL.BUILD_MANIFEST_FILENAME].decode("utf-8")
            )
            self.assertEqual(
                build_manifest["status"], "partial-animation-foundation"
            )
            self.assertIs(build_manifest["rom_integration"], False)
            self.assertIs(build_manifest["assembly_packet"], False)


class TileSharingPrimitiveTests(unittest.TestCase):
    def test_cross_context_horizontal_flip_is_prohibited(self) -> None:
        source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        frames = {frame["id"]: frame for frame in source["frames"]}
        field = frames["schala_field_idle_down_f00_v0"]
        battle = frames["schala_battle_ready_f00_v0"]
        field_width, field_height, field_pixels = TOOL.frame_pixels(field)
        reference = next(
            tile
            for tile in TOOL.iter_tiles(
                field_pixels, field_width, field_height
            )
            if sum(pixel != 0 for pixel in tile) > 2
        )
        flipped = tuple(
            reference[y * 8 + (7 - x)]
            for y in range(8)
            for x in range(8)
        )
        battle_width, battle_height, battle_pixels = TOOL.frame_pixels(battle)
        modified = list(battle_pixels)
        for y in range(8):
            for x in range(8):
                modified[y * battle_width + x] = flipped[y * 8 + x]
        synthetic = dict(battle)
        synthetic["rows"] = [
            " ".join(
                "".join(f"{pixel:X}" for pixel in modified[y * 40 + x : y * 40 + x + 8])
                for x in range(0, 40, 8)
            )
            for y in range(40)
        ]
        audit = TOOL.tile_sharing_audit(
            {
                field["id"]: field,
                synthetic["id"]: synthetic,
            }
        )
        self.assertTrue(audit["prohibited_cross_context_groups"])


if __name__ == "__main__":
    unittest.main()
