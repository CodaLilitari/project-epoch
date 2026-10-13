"""Retail-derived animation bounds and preservation, without emitting assets."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_pc07_schala_presentation_v1 as p


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = p.npc.DEFAULT_ROM.read_bytes()
        cls.compiled = p.compile_provider(cls.rom)
        cls.retail = p.npc.build_bundle(cls.rom).artifacts

    def test_raw_graphics_and_assembly_are_retail_exact(self):
        self.assertEqual(self.compiled.assets["retail-schala-raw-graphics"], self.retail[p.npc.GRAPHICS_FILENAME])
        self.assertEqual(self.compiled.assets["retail-schala-assembly"], self.retail[p.npc.ASSEMBLY_FILENAME])

    def test_every_fallback_is_exact_retail_copy(self):
        primary = self.compiled.assets["retail-schala-primary"]
        aux = self.compiled.assets["retail-schala-timing"]
        for facing in range(4):
            source = self.retail[p.npc.PRIMARY_FILENAME][facing * 36:(facing + 1) * 36]
            block = primary[facing * p.FACING_SIZE:(facing + 1) * p.FACING_SIZE]
            self.assertEqual(block[:36], source)
            for selector in range(9, 256):
                self.assertEqual(block[selector * 4:selector * 4 + 4], source[:4])
                self.assertEqual(aux[selector * 4:selector * 4 + 4], self.retail[p.npc.AUX_FILENAME][:4])
            self.assertEqual(block[1024:1028], source[:4])
            self.assertEqual(len(block[255 * 4:255 * 4 + 8]), 8)
        self.assertEqual(aux[1024:1028], self.retail[p.npc.AUX_FILENAME][:4])

    def test_new_named_spans_are_disjoint_and_bank_contained(self):
        spans = sorted((p.ALLOCATIONS[k], p.ALLOCATIONS[k] + len(v)) for k, v in self.compiled.assets.items())
        for i, (start, end) in enumerate(spans):
            self.assertEqual(start >> 16, (end - 1) >> 16)
            if i:
                self.assertLessEqual(spans[i - 1][1], start)

    def test_changed_source_fails_closed(self):
        edited = bytearray(self.rom)
        edited[0x24F050] ^= 1
        with self.assertRaises(p.npc.CompatibilityBuildError):
            p.compile_provider(bytes(edited))


if __name__ == "__main__":
    unittest.main()
