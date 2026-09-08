"""Original semantic boundary cases; no extracted game payload or CPU proof."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import audit_schala_package_completion_contract_v1 as c


class CompletionContractTests(unittest.TestCase):
    def setUp(self):
        self.state = c.HandlerState(0x42FFFF, True, 0, 0, 0)

    def test_stop_clears_owner_without_satisfying_package_wait(self):
        after = c.step(0, self.state)
        self.assertEqual(after, c.HandlerState(0x42FFFF, False, 0, 0, 0))
        self.assertEqual(c.caller_wait(after.package_counter, after.scene_busy), 'continue-package-loop')

    def test_default_signals_but_does_not_advance_or_clear_owner(self):
        after = c.step(1, self.state)
        self.assertEqual(after, c.HandlerState(0x42FFFF, True, 1, 0, 0))
        self.assertEqual(c.caller_wait(after.package_counter, after.scene_busy), 'both-observed-waits-satisfied')

    def test_every_nonzero_mode_leaves_selected_default_state_unchanged(self):
        for mode in range(1, 256):
            before = replace(self.state, mode_a3d1=mode, package_counter=37, scene_busy=2)
            with self.subTest(mode=mode):
                self.assertEqual(c.step(1, before), before)

    def test_counter_byte_wrap_can_restore_the_package_wait(self):
        before = replace(self.state, package_counter=255)
        after = c.step(1, before)
        self.assertEqual(after.package_counter, 0)
        self.assertEqual(c.caller_wait(after.package_counter, after.scene_busy), 'continue-package-loop')

    def test_stop_never_clears_an_existing_counter_or_scene_latch(self):
        before = replace(self.state, package_counter=9, scene_busy=128)
        after = c.step(0, before)
        self.assertEqual(after, replace(before, owner_active=False))
        self.assertEqual(c.caller_wait(after.package_counter, after.scene_busy), 'wait-for-scene')

    def test_package_wait_precedes_scene_wait(self):
        self.assertEqual(c.caller_wait(0, 255), 'continue-package-loop')
        self.assertEqual(c.caller_wait(255, 1), 'wait-for-scene')
        self.assertEqual(c.caller_wait(255, 0), 'both-observed-waits-satisfied')

    def test_zero_advance_never_wraps_any_pointer_boundary(self):
        for pointer in (0, 0xFFFF, 0x420000, 0x42FFFF, 0xFFFFFF):
            for opcode in (0, 1):
                for mode in (0, 1):
                    before = replace(self.state, pointer=pointer, mode_a3d1=mode)
                    self.assertEqual(c.step(opcode, before).pointer, pointer)

    def test_nonzero_direct_page_and_decimal_arithmetic_are_out_of_contract(self):
        for direct_page in (1, 0x100, 65535):
            with self.assertRaises(ValueError):
                c.step(1, self.state, direct_page=direct_page)
        with self.assertRaises(ValueError):
            c.step(1, self.state, processor_decimal=True)

    def test_exact_scalar_types_reject_python_numeric_aliases(self):
        for name in ('pointer', 'package_counter', 'scene_busy', 'mode_a3d1'):
            for value in (False, 0.0):
                with self.subTest(field=name, value=value), self.assertRaises(ValueError):
                    c.step(1, replace(self.state, **{name: value}))
        for value in (0, 1, 0.0):
            with self.assertRaises(ValueError):
                c.step(1, replace(self.state, owner_active=value))
        for value in (False, 0.0):
            with self.assertRaises(ValueError):
                c.step(value, self.state)
            with self.assertRaises(ValueError):
                c.step(1, self.state, direct_page=value)
            with self.assertRaises(ValueError):
                c.caller_wait(value, 0)
            with self.assertRaises(ValueError):
                c.caller_wait(1, value)
        for value in (0, 0.0):
            with self.assertRaises(ValueError):
                c.step(1, self.state, processor_decimal=value)

    def test_out_of_range_states_and_unmodeled_handlers_refuse(self):
        for name, maximum in (('pointer', 0xFFFFFF), ('package_counter', 255), ('scene_busy', 255), ('mode_a3d1', 255)):
            for value in (-1, maximum + 1):
                with self.assertRaises(ValueError):
                    c.step(1, replace(self.state, **{name: value}))
        for opcode in (2, 0x1E, 0xDA, 256, -1):
            with self.assertRaises(ValueError):
                c.step(opcode, self.state)

    def test_state_is_immutable_and_exact(self):
        with self.assertRaises(FrozenInstanceError):
            self.state.pointer = 0
        with self.assertRaises(ValueError):
            c.step(1, self.state.__dict__)
        self.assertEqual(c.step(1, replace(self.state, owner_active=False)).owner_active, False)

    def test_arbitrary_source_images_are_rejected_before_decoding(self):
        for source in (b'', bytes(0x400000), bytearray(0x400000)):
            with self.assertRaisesRegex(ValueError, 'canonical ROM identity'):
                c.audit(source)


if __name__ == '__main__':
    unittest.main()
