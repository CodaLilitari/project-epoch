"""Original tiny instruction fixtures exercise refusal and stack semantics."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_schala_package_interrupt_closure_v1 as subject


def walk(program: bytes):
    start = 0xC08000
    def read(pc, size):
        return program[pc - start:pc - start + size]
    return subject.walk_irq(read, start, ((start, start + len(program)),))


class InterruptClosureTests(unittest.TestCase):
    def test_status_selects_immediate_width(self):
        # REP #M/X; AND #$0E00; XBA; TAX; RTI. Operand $0E is not ASL.
        result = walk(bytes.fromhex("c23029000eebaa40"))
        self.assertEqual(result["unique_instruction_start_count"], 5)
        self.assertEqual(result["maximum_depth_including_native_hardware_frame"], 4)

    def test_register_saves_use_forced_widths(self):
        result = walk(bytes.fromhex("c23048da5a8b0b2bab7afa6840"))
        self.assertEqual(result["maximum_depth_including_native_hardware_frame"], 13)
        self.assertEqual(result["balanced_rti_context_count"], 1)

    def test_php_plp_recovers_width_after_change(self):
        result = walk(bytes.fromhex("c23008e23028a9808040"))
        self.assertEqual(result["unique_instruction_start_count"], 6)

    def test_temporary_word_cannot_be_mistaken_for_return(self):
        with self.assertRaisesRegex(subject.ClosureError, "lacks its exact frame"):
            walk(bytes.fromhex("c230200680404860"))

    def test_balanced_near_call_and_temporary_word(self):
        result = walk(bytes.fromhex("c23020068040486860"))
        self.assertEqual(result["maximum_depth_including_native_hardware_frame"], 8)

    def test_long_call_has_three_byte_frame(self):
        result = walk(bytes.fromhex("c230220780c04048686b"))
        self.assertEqual(result["maximum_depth_including_native_hardware_frame"], 9)

    def test_software_pop_cannot_consume_call_return(self):
        with self.assertRaisesRegex(subject.ClosureError, "pop consumes a return frame"):
            walk(bytes.fromhex("c23020068040684860"))

    def test_unpaired_return_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "unpaired RTS"):
            walk(bytes.fromhex("60"))

    def test_unbalanced_interrupt_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "unbalanced RTI"):
            walk(bytes.fromhex("c2304840"))

    def test_unknown_status_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "known saved status"):
            walk(bytes.fromhex("c230482840"))

    def test_irq_unmasking_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "IRQ unmasking"):
            walk(bytes.fromhex("c20440"))

    def test_unsupported_instruction_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "unsupported opcode"):
            walk(bytes.fromhex("db"))

    def test_out_of_bounds_branch_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "leaves declared bounds"):
            walk(bytes.fromhex("807f"))

    def test_truncated_instruction_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "crosses declared span"):
            walk(bytes.fromhex("c230a901"))

    def test_wrong_canonical_input_refuses(self):
        with self.assertRaisesRegex(subject.ClosureError, "exact canonical"):
            subject.audit(b"original fixture")


if __name__ == "__main__":
    unittest.main()
