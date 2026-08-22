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
TOOL_PATH = ROOT / "tools" / "build_schala_portraits_v0.py"
SOURCE_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "portrait"
    / "schala_portraits_v0.json"
)
MANIFEST_PATH = (
    ROOT / "assets" / "source" / "schala" / "v0" / "manifest.json"
)

SPEC = importlib.util.spec_from_file_location(
    "build_schala_portraits_v0", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class CanonicalSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_raw, cls.source = TOOL.load_json(SOURCE_PATH)
        _, cls.manifest = TOOL.load_json(MANIFEST_PATH)
        cls.assets = TOOL.validate_source(cls.source)
        cls.outputs = TOOL.build_outputs(cls.source_raw, cls.source)

    def test_canonical_source_hash_and_pinned_outputs(self) -> None:
        self.assertEqual(
            TOOL.sha256(self.source_raw),
            "55f5ba865ef60e0e663268f9dc7e3cbccc556b5fc42b0a72f8e4732c769ea3d9",
        )
        TOOL.verify_source_manifest(
            self.manifest, self.source_raw, self.outputs
        )

    def test_native_dimensions_and_independent_canvas_declarations(self) -> None:
        full = self.assets["schala_portrait_full_48x48_v0"]
        preview = self.assets["schala_portrait_preview_32x32_v0"]
        self.assertEqual(TOOL.asset_pixels(full)[:2], (48, 48))
        self.assertEqual(TOOL.asset_pixels(preview)[:2], (32, 32))
        self.assertNotEqual(full["canvas_id"], preview["canvas_id"])
        self.assertEqual(
            full["derivation"], "original-independent-target-size"
        )
        self.assertEqual(
            preview["derivation"], "original-independent-target-size"
        )
        TOOL.validate_independent_canvases(self.assets)

    def test_both_concepts_are_non_rom_eligible_and_unsampled(self) -> None:
        concepts = [
            item
            for item in self.source["references"]
            if item.get("source_classification")
            == "generated-concept-reference"
        ]
        self.assertEqual(len(concepts), 2)
        for concept in concepts:
            self.assertIs(concept["rom_eligible"], False)
            self.assertIs(concept["pixels_or_palette_sampled"], False)

    def test_palette_and_source_pixels_use_exactly_four_bits(self) -> None:
        colors = TOOL.palette_rgb(self.source)
        self.assertEqual(len(colors), 16)
        used = set()
        for asset in self.assets.values():
            _, _, pixels = TOOL.asset_pixels(asset)
            used.update(pixels)
            self.assertTrue(all(0 <= pixel <= 15 for pixel in pixels))
        self.assertEqual(used, set(range(16)))
        palette_bytes = self.outputs[TOOL.PALETTE_FILENAME]
        self.assertEqual(len(palette_bytes), 0x20)

    def test_packed_sizes_and_round_trip(self) -> None:
        expected_sizes = {
            "schala_portrait_full_48x48_v0": 0x480,
            "schala_portrait_preview_32x32_v0": 0x200,
        }
        for asset_id, expected_size in expected_sizes.items():
            width, height, pixels = TOOL.asset_pixels(self.assets[asset_id])
            packed = self.outputs[TOOL.PACKED_FILENAMES[asset_id]]
            self.assertEqual(len(packed), expected_size)
            self.assertEqual(
                TOOL.decode_snes_4bpp(packed, width, height), pixels
            )

    def test_pngs_are_indexed_and_decoded_from_packed_bytes(self) -> None:
        palette_bytes = self.outputs[TOOL.PALETTE_FILENAME]
        quantized_palette = TOOL.decode_snes_palette(palette_bytes)
        for asset_id, asset in self.assets.items():
            width, height, _ = TOOL.asset_pixels(asset)
            png = self.outputs[asset["canonical_filename"]]
            image = Image.open(io.BytesIO(png))
            self.assertEqual(image.mode, "P")
            self.assertEqual(image.size, (width, height))
            self.assertEqual(image.info.get("transparency"), 0)
            packed = self.outputs[TOOL.PACKED_FILENAMES[asset_id]]
            self.assertEqual(
                tuple(image.tobytes()),
                TOOL.decode_snes_4bpp(packed, width, height),
            )
            flat_palette = image.getpalette()
            self.assertIsNotNone(flat_palette)
            self.assertEqual(
                [
                    tuple(flat_palette[index : index + 3])
                    for index in range(0, 48, 3)
                ],
                quantized_palette,
            )

    def test_full_and_preview_share_no_nontrivial_exact_tile(self) -> None:
        audit = TOOL.audit_portrait_pair(self.assets)
        self.assertEqual(audit["matches"], [])
        self.assertGreater(audit["reference_tile_count"], 0)

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
            generated_manifest = json.loads(
                actual[TOOL.BUILD_MANIFEST_FILENAME].decode("utf-8")
            )
            self.assertEqual(generated_manifest["evidence"], "verified-static")
            self.assertIs(generated_manifest["rom_integration"], False)


class OriginalityAuditPrimitiveTests(unittest.TestCase):
    def test_detects_exact_hv_flipped_reference_in_memory(self) -> None:
        reference = tuple(
            1 if (x, y) in {(0, 0), (1, 2), (3, 4), (7, 6)} else 0
            for y in range(8)
            for x in range(8)
        )
        flipped = tuple(
            reference[y * 8 + (7 - x)]
            for y in range(8)
            for x in range(8)
        )
        audit = TOOL.audit_reference_tiles_in_memory(
            {"candidate": (8, 8, flipped)}, [reference]
        )
        self.assertEqual(
            audit["matches"],
            [
                {
                    "asset_id": "candidate",
                    "tile_index": 0,
                    "reference_tile_index": 0,
                }
            ],
        )

    def test_lists_but_does_not_fail_trivial_coincidences(self) -> None:
        trivial = tuple(
            1 if index in (0, 63) else 0 for index in range(64)
        )
        audit = TOOL.audit_reference_tiles_in_memory(
            {"candidate": (8, 8, trivial)}, [trivial]
        )
        self.assertEqual(audit["matches"], [])
        self.assertEqual(
            audit["trivial_candidates"][0]["nontransparent_pixels"], 2
        )


if __name__ == "__main__":
    unittest.main()
