"""Finite preservation and adversarial tests for the selected in-memory copy."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pc07_selected_transform_tests", ROOT / "tools/transform_pc07_selected_event_v1.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)
ROM_ENV = os.environ.get("CT_US_REV0_ROM")
if ROM_ENV and not Path(ROM_ENV).is_file():
    raise RuntimeError("CT_US_REV0_ROM does not name a regular file")


class RefusalWithoutGameDataTests(unittest.TestCase):
    def test_arbitrary_packet_refuses(self):
        for value in (b"", b"\x01" + bytes(32), bytes(2361)):
            with self.subTest(size=len(value)), self.assertRaisesRegex(TOOL.TransformError, "exact canonical"):
                TOOL.transform_packet(value)

    def test_accepted_dependency_pins_revalidate(self):
        module, reference = TOOL.load_dependencies()
        self.assertEqual(reference["source_manifest"][0]["sha256"], TOOL.INVENTORY_SHA256)
        self.assertEqual(module.PACKET_SHA256, TOOL.REFERENCE["packet_sha256"])


@unittest.skipUnless(ROM_ENV, "set CT_US_REV0_ROM for the private canonical corpus")
class SelectedTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = Path(ROM_ENV).read_bytes()
        _, pointer = TOOL.PARSER.event_pointer(cls.rom, 0x125)
        cls.original = TOOL.PARSER.decompress_packet(cls.rom, pointer).data
        cls.result = TOOL.transform_packet(cls.original)

    def assert_refuses_byte_change(self, offset, value, message):
        candidate = bytearray(self.result.packet)
        candidate[1 + offset] = value
        with self.assertRaisesRegex(TOOL.TransformError, message):
            TOOL.validate_transformation(self.original, bytes(candidate))

    def test_exact_preservation_and_new_object_census(self):
        result = self.result
        self.assertEqual((len(result.packet), result.packet[0]), (2553, 15))
        self.assertEqual(TOOL.inverse_original_projection(result.packet), self.original)
        self.assertEqual(TOOL.digest(self.original), TOOL.INVENTORY.PACKET_SHA256)
        commands = TOOL.PARSER.parse_event(0x125, result.packet)
        self.assertEqual(len(commands), 757)
        copied = [c for c in commands if c.object_id == 8]
        self.assertEqual(len(copied), 60)
        self.assertEqual((copied[0].opcode, copied[0].payload), (0x80, b"\x07"))
        identity_tests = [c for c in copied if c.opcode == 0x12 and c.payload[0] in (7, 8, 9)]
        self.assertEqual(len(identity_tests), 13)
        self.assertTrue(all(c.payload[1] == 7 for c in identity_tests))
        original0 = [c for c in commands if c.object_id == 1]
        original2 = [c for c in commands if c.object_id == 3]
        self.assertEqual(original0[0].opcode, 0x57)
        self.assertEqual(original2[0].opcode, 0x62)
        self.assertEqual(result.metadata["original_branch_count"], 186)
        self.assertEqual(result.metadata["copied_branch_count"], 19)

    def test_missed_copied_identity_literal_refuses(self):
        self.assert_refuses_byte_change(TOOL.donor_to_new(0x2CC), 0, "undeclared copied-body")

    def test_unrelated_control_comparison_must_remain_zero(self):
        self.assert_refuses_byte_change(TOOL.donor_to_new(0x2F1), 7, "undeclared copied-body")

    def test_original_donor_body_cannot_be_changed(self):
        # MoveProps2 operand01 belongs to the retained original object1.
        self.assert_refuses_byte_change(TOOL.old_to_new(0x2C4), 0, "inverse projection")

    def test_existing_doubled_target_must_change_by_two(self):
        self.assert_refuses_byte_change(TOOL.old_to_new(0x86E), 20, "remapped direct operand")

    def test_copied_and_original_function_aliases_cannot_be_substituted(self):
        for obj, function, replacement in ((8, 3, 4), (1, 1, 3)):
            candidate = bytearray(self.result.packet)
            source = 1 + obj * 32 + replacement * 2
            target = 1 + obj * 32 + function * 2
            candidate[target:target + 2] = candidate[source:source + 2]
            with self.subTest(obj=obj), self.assertRaisesRegex(TOOL.TransformError, "function-pointer"):
                TOOL.validate_transformation(self.original, bytes(candidate))

    def test_copied_branch_and_generic_loader_operand_are_pinned(self):
        for offset in (TOOL.donor_to_new(0x2C9), TOOL.NEW_BODY_START + 1):
            value = self.result.packet[offset + 1] ^ 1
            with self.subTest(offset=offset):
                self.assert_refuses_byte_change(offset, value, "copied.body|LoadPC07")

    def test_original_branch_target_cannot_change(self):
        # The original object1 first conditional's displacement, now +32.
        offset = TOOL.old_to_new(0x2C9)
        self.assert_refuses_byte_change(offset, self.result.packet[offset + 1] ^ 1,
                                       "original branch")

    def test_source_drift_refuses_before_construction(self):
        original = bytearray(self.original)
        original[-1] ^= 1
        with self.assertRaisesRegex(TOOL.TransformError, "exact canonical"):
            TOOL.transform_packet(bytes(original))

    def test_repeat_metadata_and_cli_are_payload_free(self):
        report = TOOL.make_report(self.rom)
        self.assertEqual(TOOL.transform_packet(self.original), self.result)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(TOOL.main(["--rom", ROM_ENV]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), report)
        self.assertNotIn("packet", report)
        self.assertNotIn("body", report)
        self.assertEqual(TOOL.digest(Path(ROM_ENV).read_bytes()), TOOL.PARSER.CANONICAL_SHA256)
        reference = ROOT / "references/pc07_selected_event_transform_v1.json"
        if reference.exists():
            self.assertEqual(json.loads(reference.read_text()), report)


if __name__ == "__main__":
    unittest.main()
