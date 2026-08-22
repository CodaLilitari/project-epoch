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
TOOL_PATH = TOOLS_DIR / "audit_schala_gameplay_originality.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_schala_gameplay_originality", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def make_tile(points: dict[tuple[int, int], int]) -> tuple[int, ...]:
    return tuple(
        points.get((x, y), 0) for y in range(8) for x in range(8)
    )


class GameplayOriginalityAuditTests(unittest.TestCase):
    def test_reference_windows_are_aligned_nonoverlapping_and_complete(self):
        TOOL.validate_reference_windows()
        self.assertEqual(len(TOOL.PC_REFERENCE_WINDOWS), 7)
        self.assertEqual(
            sum(
                window.byte_count // TOOL.BYTES_PER_4BPP_TILE
                for window in TOOL.PC_REFERENCE_WINDOWS
            ),
            7264,
        )

    def test_pointer_table_validation_pins_all_seven_entries(self) -> None:
        rom = bytearray(TOOL.CANONICAL_ROM_SIZE)
        for window in TOOL.PC_REFERENCE_WINDOWS:
            offset = (
                TOOL.PC_GFX_POINTER_TABLE_FILE + window.logical_id * 3
            )
            rom[offset : offset + 3] = window.snes_start.to_bytes(3, "little")
        TOOL.verify_pc_pointer_table(bytes(rom))
        rom[TOOL.PC_GFX_POINTER_TABLE_FILE] ^= 1
        with self.assertRaisesRegex(ValueError, "pointer table"):
            TOOL.verify_pc_pointer_table(bytes(rom))

    def test_4bpp_decoder_requires_tile_alignment(self) -> None:
        with self.assertRaisesRegex(ValueError, "aligned"):
            TOOL.decode_4bpp_tile_block(b"\x00" * 31)
        self.assertEqual(
            TOOL.decode_4bpp_tile_block(b"\x00" * 32), ((0,) * 64,)
        )

    def test_visible_pattern_renames_nonzero_indices_but_pins_zero(self):
        first = make_tile({(0, 0): 3, (1, 0): 8, (2, 0): 3})
        renamed = make_tile({(0, 0): 12, (1, 0): 1, (2, 0): 12})
        zero_changed = make_tile({(1, 0): 12, (2, 0): 1})
        self.assertEqual(
            TOOL.visible_pattern(first), TOOL.visible_pattern(renamed)
        )
        self.assertNotEqual(
            TOOL.visible_pattern(first), TOOL.visible_pattern(zero_changed)
        )

    def test_audit_finds_flipped_exact_and_palette_pattern_matches(self):
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
        reference_tile = TOOL.ReferenceTile(
            character="Test",
            logical_id=0,
            tile_index=4,
            file_offset=0x1234,
            pixels=reference,
        )
        audit = TOOL.audit_tiles(
            {
                "exact": (8, 8, exact_flipped),
                "renamed": (8, 8, renamed_flipped),
            },
            [reference_tile],
        )
        self.assertEqual(len(audit["exact_index_matches"]), 1)
        self.assertEqual(len(audit["visible_pattern_matches"]), 2)
        self.assertEqual(audit["visible_pattern_only_match_count"], 1)
        self.assertEqual(
            audit["exact_index_matches"][0]["reference_file_offset"],
            "0x001234",
        )

    def test_blank_and_two_pixel_tiles_are_excluded(self) -> None:
        blank = (0,) * 64
        two = make_tile({(0, 0): 1, (7, 7): 2})
        references = [
            TOOL.ReferenceTile("Test", 0, 0, 0, blank),
            TOOL.ReferenceTile("Test", 0, 1, 0x20, two),
        ]
        audit = TOOL.audit_tiles(
            {"blank": (8, 8, blank), "two": (8, 8, two)}, references
        )
        self.assertEqual(audit["exact_index_matches"], [])
        self.assertEqual(audit["visible_pattern_matches"], [])
        self.assertEqual(audit["excluded_reference_tile_count"], 2)
        self.assertEqual(len(audit["excluded_candidate_tiles"]), 2)

    def test_rom_gate_rejects_unpinned_input_before_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "wrong.sfc"
            path.write_bytes(b"\x00" * TOOL.CANONICAL_ROM_SIZE)
            with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                TOOL.verify_canonical_rom(path)


if __name__ == "__main__":
    unittest.main()
