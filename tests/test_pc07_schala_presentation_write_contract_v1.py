"""Fail-closed fixed presentation recipe checks; all images stay in memory."""
import copy
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pc07_schala_presentation_write_contract_v1 as c
import validate_rom_write_intents as guard


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.target, cls.spec = c.recipe(c.provider.npc.DEFAULT_ROM.read_bytes())
        cls.output = "private/test_runs/pc07_schala_contract_test_unemitted/diagnostic.sfc"
        cls.manifest = c.build_manifest(cls.source, cls.target, cls.output)

    def test_shared_guard_accepts_complete_recipe(self):
        self.assertEqual(guard.validate_pc07_schala_presentation_manifest(self.manifest)["status"], "metadata-valid")
        r = guard.audit_pc07_schala_presentation_images(self.manifest, self.source, self.target)
        self.assertTrue(r["complete_diff_coverage"])
        self.assertTrue(r["accepted_image_inverse"])
        self.assertEqual(r["changed_bytes"], 8892)
        self.assertEqual(guard.APPROVED_PRODUCTION_ALLOCATIONS, ())
        self.assertEqual(guard.APPROVED_PRODUCTION_HOOKS, ())

    def test_arbitrary_payload_and_gap_changes_refused(self):
        for offset in (0x412093, 0x420000, 0x242000, 0x410000):
            target = bytearray(self.target)
            target[offset] ^= 1
            with self.subTest(offset=hex(offset)), self.assertRaises(ValueError):
                guard.audit_pc07_schala_presentation_images(self.manifest, self.source, bytes(target))

    def test_source_mutation_refused(self):
        source = bytearray(self.source)
        source[0x240C00] ^= 1
        with self.assertRaises(ValueError):
            guard.audit_pc07_schala_presentation_images(self.manifest, bytes(source), self.target)

    def test_manifest_fields_and_types_are_exact(self):
        for key, value in (("production_approval", 0), ("runtime_qualification", True),
                           ("target_bytes", float(0x800000)), ("recipe_sha256", "0" * 64)):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                guard.validate_pc07_schala_presentation_manifest(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["caller_approved_hook"] = True
        with self.assertRaises(ValueError):
            guard.validate_pc07_schala_presentation_manifest(manifest)

    def test_foreign_existing_or_public_output_refused(self):
        for output in ("public/diagnostic.sfc", "private/test_runs/../diagnostic.sfc",
                       "private/test_runs/pc07_first_attack_diagnostic_v1/diagnostic.sfc"):
            manifest = copy.deepcopy(self.manifest)
            manifest["output"] = output
            with self.subTest(output=output), self.assertRaises(ValueError):
                guard.validate_pc07_schala_presentation_manifest(manifest)

    def test_all_canonical_sprite_tables_and_npc_sources_preserved(self):
        for start, end in ((0x242000, 0x242A00), (0x24F000, 0x24F600),
                           (0x19E2CE, 0x19E2CE + 2447), (0x1E2B48, 0x1E2EE0),
                           (0x240000, 0x241000), (0x2467A0, 0x246830),
                           (0x24BC38, 0x24BC5C)):
            self.assertEqual(self.target[start:end], self.source[start:end])


if __name__ == "__main__":
    unittest.main()
