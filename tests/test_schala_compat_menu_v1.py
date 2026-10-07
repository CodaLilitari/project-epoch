"""Private canonical-input checks build in memory only; no image emission."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_schala_compat_menu_v1 as builder
import schala_compat_menu_v1 as c
import validate_rom_write_intents as guard


class MenuRelocationContractTests(unittest.TestCase):
    def test_indexed_rock_base_is_not_the_rock_start(self):
        # Y is the item ID AE..B2, not an ordinal 0..4.
        new_base = int.from_bytes(c.PATCHES[5][2][1:], "little")
        self.assertEqual([new_base + item for item in range(0xAE, 0xB3)], list(range(0x2CC7, 0x2CCC)))
        self.assertEqual(c.DELTA, 0x470)

    def test_forward_mvn_clears_all_five_rock_bytes_with_overlap(self):
        memory = bytearray([0xA5] * 0x50)
        memory[0x27:0x29] = b"\0\0"  # STZ under M16.
        for i in range(3):  # MVN count A=2 means three transfers.
            memory[0x29 + i] = memory[0x27 + i]
        self.assertEqual(memory[0x27:0x2C], bytes(5))
        self.assertEqual(memory[:0x27] + memory[0x2C:], bytes([0xA5]) * 0x4B)

    def test_nonprivate_output_refused(self):
        for output in (c.ROOT / "diagnostic.sfc", c.ROOT / "private/../diagnostic.sfc", c.ROOT / "private"):
            with self.subTest(output=output), self.assertRaises(c.ContractError):
                c.private_path(output)

    def test_explicit_emission_requires_review_before_build_or_write(self):
        with mock.patch.object(builder, "build_image") as build:
            with self.assertRaises(c.ContractError):
                builder.emit(b"", c.ROOT / "private/test_runs/compat_menu_v1_test/never.sfc", "0" * 64)
            build.assert_not_called()

    def test_noncanonical_input_is_rejected_before_path_or_mutation(self):
        with self.assertRaises(c.ContractError):
            builder.build_image(bytes(16), c.ROOT / "private/test_runs/compat_menu_v1_test/never.sfc")


@unittest.skipUnless(c.DEFAULT_ROM.exists(), "private canonical input unavailable")
class CanonicalMenuBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = c.DEFAULT_ROM.read_bytes()
        cls.destination = c.ROOT / "private/test_runs/compat_menu_v1_test/not_emitted.sfc"
        cls.target, cls.report = builder.build_image(cls.source, cls.destination)

    def test_exact_fourteen_operands_full_guard_and_no_output(self):
        expected = [0x0282E5, 0x0282E6, 0x0282E8, 0x0282E9, 0x0282EB, 0x0282EC,
                    0x02830F, 0x028310, 0x02B9B0, 0x02B9B1,
                    0x3FF86E, 0x3FF86F, 0x3FF9A3, 0x3FF9A4]
        self.assertEqual([i for i, (a, b) in enumerate(zip(self.source, self.target)) if a != b], expected)
        self.assertEqual(self.report["changed_file_offsets"], expected)
        audit = self.report["write_intent_audit"]
        self.assertEqual(audit["status"], "images-valid")
        self.assertEqual(audit["changed_byte_count"], 14)
        self.assertTrue(audit["complete_diff_coverage"] and audit["preimages_verified"])
        self.assertFalse(self.report["emitted"])
        self.assertFalse(self.destination.exists())

    def test_opcode_bound_header_and_size_are_unchanged(self):
        self.assertEqual(len(self.target), 0x400000)
        for start, old, new in c.PATCHES:
            self.assertEqual(self.target[start:start + 3], new)
            self.assertEqual(self.target[start], old[0])
        self.assertEqual(self.target[0x028319:0x02831C], bytes.fromhex("c93028"))
        self.assertEqual(self.target[0xFFC0:0x10000], self.source[0xFFC0:0x10000])

    def test_undeclared_mutation_rejected_even_with_updated_target_hash(self):
        bad = bytearray(self.target)
        bad[0] ^= 1
        manifest = copy.deepcopy(self.report["write_intent_manifest"])
        manifest["target_sha256"] = c.sha256(bad)
        with self.assertRaises(guard.WriteIntentError):
            guard.audit_images(manifest, self.source, bytes(bad))

    def test_changed_record_bound_rejected_by_complete_diff(self):
        bad = bytearray(self.target)
        bad[0x02831A] = 0x80
        manifest = copy.deepcopy(self.report["write_intent_manifest"])
        manifest["target_sha256"] = c.sha256(bad)
        with self.assertRaises(guard.WriteIntentError):
            guard.audit_images(manifest, self.source, bytes(bad))

    def test_missing_intent_and_production_relabel_are_rejected(self):
        missing = copy.deepcopy(self.report["write_intent_manifest"])
        missing["writes"].pop()
        with self.assertRaises(guard.WriteIntentError):
            guard.audit_images(missing, self.source, self.target)
        production = copy.deepcopy(self.report["write_intent_manifest"])
        production.update(build_mode="production", output_path=None)
        with self.assertRaises(guard.WriteIntentError):
            guard.validate_manifest(production)
        self.assertEqual(guard.APPROVED_PRODUCTION_ALLOCATIONS, ())
        self.assertEqual(guard.APPROVED_PRODUCTION_HOOKS, ())

    def test_full_disassembly_drift_is_rejected(self):
        path = "references/ct_disassembly/bank_C2.asm"
        with mock.patch.dict(c.PINNED_SOURCES, {path: "0" * 64}):
            with self.assertRaises(c.ContractError):
                c.source_contract(self.source)


if __name__ == "__main__":
    unittest.main()
