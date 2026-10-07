"""Original synthetic refusal cases plus optional pinned-corpus inventory."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pc07_selected_remap_test_tool", ROOT / "tools/audit_pc07_selected_event_remap_v1.py")
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

ROM_ENV = os.environ.get("CT_US_REV0_ROM")
if ROM_ENV and not Path(ROM_ENV).is_file():
    raise RuntimeError("CT_US_REV0_ROM does not name a regular file")


def packet(*bodies: bytes) -> bytes:
    """Create original test bytecode with every function aliased to its start."""
    start = 32 * len(bodies)
    table = bytearray()
    for body in bodies:
        table.extend(start.to_bytes(2, "little") * 16)
        start += len(body)
    return bytes([len(bodies)]) + bytes(table) + b"".join(bodies)


class SyntheticInventoryTests(unittest.TestCase):
    def inspect(self, value, **kwargs):
        return TOOL.inspect_packet(value, insertion=1, **kwargs)

    def test_doubled_object_remap_preserves_function_and_priority(self):
        result = self.inspect(packet(bytes([3, 2, 0x53, 0]), b"\x00"))
        self.assertEqual(result["direct_references"], [[0, 64, 3, 1, 2, 2, 4, 3, 5]])
        self.assertEqual(result["changed_direct_reference_count"], 1)

    def test_odd_and_out_of_domain_direct_targets_refuse(self):
        for operand in (1, 4, 0x80):
            with self.subTest(operand=operand), self.assertRaisesRegex(TOOL.AuditError, "doubled index"):
                self.inspect(packet(bytes([0x7C, operand, 0]), b"\x00"))

    def test_active_role_is_unchanged_and_requires_real_function(self):
        result = self.inspect(packet(bytes([7, 4, 0x47, 0]), b"\x00"))
        self.assertEqual(result["active_role_references"], [[0, 64, 7, 4, 2, 7, 4]])
        self.assertEqual(result["candidate_role2_referenced_functions"], [7])
        self.assertEqual(result["direct_references"], [])

    def test_unreviewed_active_role_refuses(self):
        for operand in (1, 6, 0x80):
            with self.subTest(operand=operand), self.assertRaisesRegex(TOOL.AuditError, "role operand"):
                self.inspect(packet(bytes([5, operand, 0x43, 0]), b"\x00"))

    def test_equal_numeric_self_operand_is_not_remapped(self):
        result = self.inspect(packet(bytes([0x89, 2, 0]), b"\x00"))
        self.assertEqual(result["direct_references"], [])
        self.assertEqual(result["opcode_schema_rows"][1][2], "self_property_or_animation")

    def test_pointer_aliases_and_piecewise_deltas_are_explicit(self):
        result = self.inspect(packet(b"\x00", b"\x00"), new_body_size=11)
        groups = result["function_pointer_groups"]
        self.assertEqual(groups[0], [0, 0, list(range(16)), 64, 96])
        self.assertEqual(groups[1], [1, 2, list(range(16)), 65, 108])

    def test_function_pointer_into_operand_or_other_object_refuses(self):
        original = packet(bytes([0x89, 1, 0]), b"\x00")
        for bad in (65, 67):
            altered = bytearray(original)
            altered[3:5] = bad.to_bytes(2, "little")
            with self.subTest(target=bad), self.assertRaisesRegex(TOOL.AuditError, "function pointer"):
                self.inspect(bytes(altered))

    def test_branch_arithmetic_uses_last_operand_anchor(self):
        result = self.inspect(packet(bytes([0x10, 2, 0, 0x11, 1]), b"\x00"))
        self.assertEqual(result["branches"], [[0, 64, 0x10, 65, 67, 2],
                                              [0, 67, 0x11, 68, 67, 1]])
        conditional = self.inspect(packet(bytes([0x12, 0, 0, 0, 1, 0]), b"\x00"))
        self.assertEqual(conditional["branches"], [[0, 64, 0x12, 68, 69, 1]])

    def test_branch_into_operand_or_another_object_refuses(self):
        for body in (bytes([0x10, 0, 0]), bytes([0x10, 1])):
            with self.subTest(body=body), self.assertRaisesRegex(TOOL.AuditError, "relative branch"):
                self.inspect(packet(body, b"\x00"))

    def test_unreviewed_opcode_and_submode_refuse(self):
        for body in (bytes([1, 0]), bytes([0xFF, 0x92, 0]), bytes([0x88, 0x01, 0])):
            with self.subTest(body=body), self.assertRaisesRegex(TOOL.AuditError, "unreviewed"):
                self.inspect(packet(body, b"\x00"))

    def test_palette_native_word_extent_is_checked(self):
        # Original synthetic color literals. The parser uses the low length
        # byte; this selected profile additionally pins its native high byte.
        body = bytes([0x88, 0x8D, 8, 0, 0, 0, 0, 0, 0, 0, 0])
        self.inspect(packet(body, b"\x00"))
        altered = bytearray(body)
        altered[3] = 1
        with self.assertRaisesRegex(TOOL.AuditError, "literal extent"):
            self.inspect(packet(bytes(altered), b"\x00"))

    def test_unknown_absolute_memory_domain_refuses(self):
        body = bytes([0x48, 0x97, 1, 0x7E, 0, 0])
        with self.assertRaisesRegex(TOOL.AuditError, "absolute-memory"):
            self.inspect(packet(body, b"\x00"))

    def test_unknown_comparison_and_logical_pc_domain_refuse(self):
        for body in (bytes([0x12, 0, 0, 7, 1, 0]), bytes([0xD2, 7, 1, 0])):
            with self.subTest(body=body), self.assertRaisesRegex(TOOL.AuditError, "unreviewed"):
                self.inspect(packet(body, b"\x00"))

    def test_capacity_and_invalid_layout_size_refuse(self):
        value = packet(b"\x00", b"\x00")
        for size in (-1, 0, True, 0x1700):
            with self.subTest(size=size), self.assertRaises(TOOL.AuditError):
                self.inspect(value, new_body_size=size)


@unittest.skipUnless(ROM_ENV, "set CT_US_REV0_ROM for the private canonical corpus")
class CanonicalInventoryTests(unittest.TestCase):
    def test_selected_inventory_and_existing_packet_are_pinned(self):
        rom = Path(ROM_ENV).read_bytes()
        before = TOOL.sha256(rom)
        report = TOOL.audit_rom(rom)
        inv = report["inventory"]
        self.assertEqual(before, TOOL.sha256(rom))
        self.assertEqual(report["packet_sha256"], TOOL.PACKET_SHA256)
        self.assertEqual(report["scope"]["event_pointer_aliases"], [0x125])
        self.assertEqual(report["scope"]["location_aliases"], [0x1DA])
        self.assertEqual((inv["command_count"], inv["function_pointer_count"], inv["branch_count"]),
                         (697, 224, 186))
        changed = [row for row in inv["direct_references"] if row[5] != row[6]]
        self.assertEqual([(r[1], r[2], r[5], r[6]) for r in changed],
                         [(0x86D, 0x7C, 20, 22), (0x86F, 0x7C, 22, 24),
                          (0x873, 0x03, 20, 22), (0x876, 0x04, 22, 24)])
        self.assertEqual(len(inv["active_role_references"]), 17)
        self.assertEqual(inv["candidate_role2_referenced_functions"], [3, 4, 5, 6, 7])
        donors = report["complete_body_reuse_assessment"]
        self.assertEqual([(d["source_object"], d["source_body_size"], d["proposed_body_size"],
                           len(d["identity_comparisons"]), d["unchanged_relative_branch_count"],
                           d["dialogue_opcode_C1_count"]) for d in donors],
                         [(1, 159, 160, 13, 19, 0), (3, 163, 164, 13, 19, 1)])
        self.assertEqual([row[1] for row in donors[0]["identity_comparisons"]],
                         [0x2CC, 0x2D4, 0x2DC, 0x2FD, 0x303, 0x309, 0x314,
                          0x31E, 0x326, 0x32E, 0x33D, 0x345, 0x34D])
        self.assertEqual(donors[0]["retained_control_comparisons"], [[0x2EF, 6, 0, 1]])
        self.assertEqual(donors[0]["function_relative_targets_proposed"][0], 0)
        self.assertEqual(donors[0]["function_relative_targets_proposed"][3:8],
                         [value + 1 for value in donors[0]["function_relative_targets_before"][3:8]])
        # The larger hypothetical body moves targets without changing any
        # old intra-object branch byte or alias relationship.
        bigger = TOOL.audit_rom(rom, 96)["inventory"]
        self.assertEqual(bigger["branches"], inv["branches"])
        self.assertEqual(bigger["active_role_references"], inv["active_role_references"])
        self.assertEqual(bigger["direct_references"], inv["direct_references"])
        report_path = ROOT / "references/pc07_selected_event_remap_v1.json"
        if report_path.exists():
            self.assertEqual(report, json.loads(report_path.read_text()))


if __name__ == "__main__":
    unittest.main()
