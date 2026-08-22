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
TOOL_PATH = TOOLS_DIR / "audit_schala_portrait_originality.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_schala_portrait_originality", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def make_tile(points: dict[tuple[int, int], int]) -> tuple[int, ...]:
    return tuple(
        points.get((x, y), 0) for y in range(8) for x in range(8)
    )


class PortraitOriginalityAuditTests(unittest.TestCase):
    def test_visible_pattern_renames_nonzero_indices_but_pins_zero(self) -> None:
        first = make_tile({(0, 0): 3, (1, 0): 8, (2, 0): 3})
        renamed = make_tile({(0, 0): 12, (1, 0): 1, (2, 0): 12})
        zero_changed = make_tile(
            {
                (x, y): (
                    0
                    if (x, y) == (0, 0)
                    else 12
                    if (x, y) == (1, 0)
                    else 1
                )
                for y in range(8)
                for x in range(8)
            }
        )
        self.assertEqual(
            TOOL.visible_pattern(first), TOOL.visible_pattern(renamed)
        )
        self.assertNotEqual(
            TOOL.visible_pattern(first), TOOL.visible_pattern(zero_changed)
        )

    def test_audit_finds_flipped_exact_and_palette_pattern_matches(self) -> None:
        reference = make_tile(
            {(0, 0): 2, (1, 1): 3, (1, 2): 3, (4, 5): 2}
        )
        exact_flipped = tuple(
            reference[y * 8 + (7 - x)]
            for y in range(8)
            for x in range(8)
        )
        renamed_flipped = tuple(
            {0: 0, 2: 11, 3: 7}[pixel] for pixel in exact_flipped
        )
        audit = TOOL.audit_tiles(
            {
                "exact": (8, 8, exact_flipped),
                "renamed": (8, 8, renamed_flipped),
            },
            [reference],
        )
        self.assertEqual(len(audit["exact_index_matches"]), 1)
        self.assertEqual(
            audit["exact_index_matches"][0]["reference_file_offset"],
            "0x3F0000",
        )
        self.assertEqual(len(audit["visible_pattern_matches"]), 2)
        self.assertEqual(audit["visible_pattern_only_match_count"], 1)

    def test_blank_and_two_pixel_tiles_are_excluded(self) -> None:
        blank = (0,) * 64
        two_pixels = make_tile({(0, 0): 1, (7, 7): 2})
        audit = TOOL.audit_tiles(
            {
                "blank": (8, 8, blank),
                "two": (8, 8, two_pixels),
            },
            [blank, two_pixels],
        )
        self.assertEqual(audit["exact_index_matches"], [])
        self.assertEqual(audit["visible_pattern_matches"], [])
        self.assertEqual(audit["excluded_reference_tile_count"], 2)
        self.assertEqual(len(audit["excluded_candidate_tiles"]), 2)

    def test_4bpp_block_decoder_requires_tile_alignment(self) -> None:
        with self.assertRaisesRegex(ValueError, "aligned"):
            TOOL.decode_4bpp_tile_block(b"\x00" * 31)
        decoded = TOOL.decode_4bpp_tile_block(b"\x00" * 32)
        self.assertEqual(decoded, ((0,) * 64,))

    def test_rom_gate_rejects_unpinned_input_before_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "wrong.sfc"
            path.write_bytes(b"\x00" * TOOL.CANONICAL_ROM_SIZE)
            with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                TOOL.verify_canonical_rom(path)


if __name__ == "__main__":
    unittest.main()
