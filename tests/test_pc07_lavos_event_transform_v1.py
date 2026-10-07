"""Finite byte/alias preservation and adversaries for destination event0126."""

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
    "pc07_lavos_transform_tests", ROOT / "tools/transform_pc07_lavos_event_v1.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)
ROM_ENV = os.environ.get("CT_US_REV0_ROM")
if ROM_ENV and not Path(ROM_ENV).is_file():
    raise RuntimeError("CT_US_REV0_ROM does not name a regular file")


class RefusalTests(unittest.TestCase):
    def test_arbitrary_packet_refuses(self):
        for packet in (b"", bytes(1801), b"\x0E" + bytes(1800)):
            with self.subTest(size=len(packet)), self.assertRaisesRegex(TOOL.TransformError, "exact canonical"):
                TOOL.transform_packet(packet)

    def test_accepted0125_dependencies_are_still_pinned(self):
        module = TOOL.load_reuse()
        self.assertEqual(module.INVENTORY.PACKET_SHA256, module.REFERENCE["packet_sha256"])
        self.assertEqual(TOOL.digest(TOOL.REUSE_PATH.read_bytes()), TOOL.REUSE_SHA256)


@unittest.skipUnless(ROM_ENV, "set CT_US_REV0_ROM for the private canonical corpus")
class LavosTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = Path(ROM_ENV).read_bytes()
        cls.result = TOOL.transform_from_rom(cls.rom)
        _, ptr = TOOL.PARSER.event_pointer(cls.rom, 0x126)
        cls.original = TOOL.PARSER.decompress_packet(cls.rom, ptr).data

    def reject_byte(self, offset, value, reason):
        altered = bytearray(self.result.packet)
        altered[offset + 1] = value
        with self.assertRaisesRegex(TOOL.TransformError, reason):
            TOOL.validate_transformation(self.original, bytes(altered))

    def test_exact_original_projection_and_independent_body(self):
        result = self.result
        self.assertEqual((len(result.packet), result.packet[0]), (1914, 15))
        self.assertEqual(TOOL.inverse_original_projection(result.packet), self.original)
        commands = TOOL.PARSER.parse_event(0x126, result.packet)
        self.assertEqual(len(commands), 555)
        copied = [c for c in commands if c.object_id == 8]
        self.assertEqual(len(copied), 33)
        self.assertEqual((copied[0].opcode, copied[0].payload), (0x80, b"\x07"))
        self.assertEqual([c.payload[1] for c in copied if c.opcode == 0x12], [7] * 6)
        original0 = [c for c in commands if c.object_id == 1]
        original2 = [c for c in commands if c.object_id == 3]
        self.assertEqual(original0[0].opcode, 0x57)
        self.assertEqual(original2[0].opcode, 0x62)
        self.assertEqual([c.payload[1] for c in original0 if c.opcode == 0x12], [0] * 6)
        self.assertEqual(result.metadata["source_inventory"]["required_role2_functions"], [4, 5])
        self.assertEqual(result.metadata["original_branch_count"], 93)
        self.assertEqual(result.metadata["copied_branch_count"], 6)
        # Exactly one battle command remains in the relocated original object8.
        battle = [c for c in commands if c.opcode == 0xD8]
        self.assertEqual([(c.object_id, c.offset) for c in battle], [(9, TOOL.old_to_new(0x4D4))])

    def test_source_drift_and_wrong_selected_event_refuse(self):
        changed = bytearray(self.original)
        changed[-1] ^= 1
        _, ptr = TOOL.PARSER.event_pointer(self.rom, 0x125)
        for packet in (bytes(changed), TOOL.PARSER.decompress_packet(self.rom, ptr).data):
            with self.assertRaisesRegex(TOOL.TransformError, "exact canonical"):
                TOOL.transform_packet(packet)

    def test_every_copied_identity_literal_and_loader_are_required(self):
        for offset in TOOL.IDENTITY_OPERANDS:
            with self.subTest(offset=offset):
                self.reject_byte(TOOL.donor_to_new(offset), 0, "copied-body")
        self.reject_byte(TOOL.NEW_BODY_START + 1, 0, "LoadPC07")

    def test_all_four_existing_targets_are_doubled_indices(self):
        for offset, old, new in TOOL.DIRECT_OPERANDS:
            self.assertEqual(new, old + 2)
            for wrong in (old, old + 1):
                with self.subTest(offset=offset, wrong=wrong):
                    self.reject_byte(TOOL.old_to_new(offset), wrong, "remapped direct operand")

    def test_original_and_copied_function_alias_substitution_refuses(self):
        for obj in (1, 8):
            altered = bytearray(self.result.packet)
            # Alias function1 to function3 instead of the retained function2 target.
            at, source = 1 + obj * 32 + 2, 1 + obj * 32 + 6
            altered[at:at + 2] = altered[source:source + 2]
            with self.subTest(obj=obj), self.assertRaisesRegex(TOOL.TransformError, "function-pointer"):
                TOOL.validate_transformation(self.original, bytes(altered))

    def test_original_and_copied_relative_branch_changes_refuse(self):
        displacement = 0x1E2
        for mapped, reason in ((TOOL.old_to_new(displacement), "original relative branch"),
                               (TOOL.donor_to_new(displacement), "copied-body")):
            with self.subTest(offset=mapped):
                self.reject_byte(mapped, self.result.packet[mapped + 1] ^ 1, reason)

    def test_original_donor_role_operands_and_battle_flags_stay_exact(self):
        # Original donor movement property, unchanged role operand2, D8 flags.
        for old in (0x1DD, 0x663, 0x4D5):
            mapped = TOOL.old_to_new(old)
            with self.subTest(old=old):
                self.reject_byte(mapped, self.result.packet[mapped + 1] ^ 1, "inverse projection")

    def test_copied_nonidentity_coordinate_and_animation_bytes_stay_exact(self):
        for old in (0x1E4, 0x210, 0x226):
            mapped = TOOL.donor_to_new(old)
            with self.subTest(old=old):
                self.reject_byte(mapped, self.result.packet[mapped + 1] ^ 1, "copied-body")

    def test_metadata_cli_is_repeatable_and_payload_free(self):
        report = TOOL.make_report(self.rom)
        self.assertEqual(TOOL.transform_packet(self.original), self.result)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(TOOL.main(["--rom", ROM_ENV]), 0)
        self.assertEqual(json.loads(output.getvalue()), report)
        self.assertNotIn("packet", report)
        self.assertNotIn("body", report)
        self.assertEqual(TOOL.digest(Path(ROM_ENV).read_bytes()), TOOL.PARSER.CANONICAL_SHA256)
        reference = ROOT / "references/pc07_lavos_event_transform_v1.json"
        if reference.exists():
            self.assertEqual(json.loads(reference.read_text()), report)


if __name__ == "__main__":
    unittest.main()
