"""Emission-boundary tests. No ROM files or event payloads are emitted."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import build_pc07_native_save_transition_diagnostic_v1 as builder


class BuilderBoundaryTests(unittest.TestCase):
    OUTPUT = 'private/test_runs/pc07_native_save_transition_builder_tests_no_emission/diagnostic.sfc'

    @classmethod
    def setUpClass(cls):
        if not (ROOT / builder.contract.CANONICAL_PATH).is_file():
            raise unittest.SkipTest("exact private canonical input is unavailable")
        cls.target, cls.receipt = builder.build(cls.OUTPUT)

    def test_shared_audits_and_production_default_deny(self):
        self.assertEqual(self.receipt['intent_audit']['status'], 'metadata-valid')
        self.assertEqual(self.receipt['complete_diff_audit']['status'], 'images-valid')
        self.assertTrue(self.receipt['complete_diff_audit']['complete_diff_coverage'])
        self.assertFalse(self.receipt['emitted'])
        self.assertFalse(self.receipt['native_execution'])
        self.assertFalse(builder.guard.APPROVED_PRODUCTION_ALLOCATIONS)
        self.assertFalse(builder.guard.APPROVED_PRODUCTION_HOOKS)
        self.assertFalse((ROOT/self.OUTPUT).parent.exists())

    def test_stale_bundle_refuses_before_assembly_or_output(self):
        with patch.object(builder, 'build', return_value=(self.target, self.receipt)), \
             patch.object(builder.assembler, 'verify_asar') as verify, \
             patch.object(builder.assembler, 'exclusive') as emit:
            with self.assertRaisesRegex(ValueError, 'reviewed source bundle'):
                builder.emit(self.OUTPUT, '0'*64)
            verify.assert_not_called()
            emit.assert_not_called()
        self.assertFalse((ROOT/self.OUTPUT).parent.exists())

    def test_shared_intent_refusal_precedes_emission(self):
        with patch.object(builder.guard, 'validate_pc07_native_save_transition_manifest',
                          side_effect=ValueError('shared intent refusal')), \
             patch.object(builder.guard, 'audit_pc07_native_save_transition_images') as diff, \
             patch.object(builder.assembler, 'exclusive') as emit:
            with self.assertRaisesRegex(ValueError, 'shared intent refusal'):
                builder.emit(self.OUTPUT, self.receipt['source_bundle']['sha256'])
            diff.assert_not_called()
            emit.assert_not_called()
        self.assertFalse((ROOT/self.OUTPUT).parent.exists())

    def test_shared_complete_diff_refusal_precedes_emission(self):
        with patch.object(builder.guard, 'audit_pc07_native_save_transition_images',
                          side_effect=ValueError('shared diff refusal')), \
             patch.object(builder.assembler, 'exclusive') as emit:
            with self.assertRaisesRegex(ValueError, 'shared diff refusal'):
                builder.emit(self.OUTPUT, self.receipt['source_bundle']['sha256'])
            emit.assert_not_called()
        self.assertFalse((ROOT/self.OUTPUT).parent.exists())

    def test_existing_destination_is_not_overwritten(self):
        with patch.object(builder.contract.prior.field, 'output_path',
                          return_value=ROOT/'private/test_runs/pc07_first_attack_diagnostic_v1/diagnostic.sfc'), \
             patch.object(builder, 'build') as build, \
             patch.object(builder.assembler, 'exclusive') as emit:
            with self.assertRaisesRegex(ValueError, 'fresh private build directory'):
                builder.emit(self.OUTPUT, self.receipt['source_bundle']['sha256'])
            build.assert_not_called()
            emit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
