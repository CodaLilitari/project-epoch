"""Focused new-boundary checks; no ancestor builds or historical test suites."""
import copy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import pc07_battle_pose_write_contract_v1 as contract
import validate_rom_write_intents as guard


class BattlePoseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (contract.ROOT / contract.SOURCE['path']).is_file():
            raise unittest.SkipTest('private accepted ROM fixture is not distributed')
        parent = (contract.ROOT / 'private/test_runs').resolve()
        cls.temporary = Path(tempfile.mkdtemp(prefix='pc07_battle_pose_unit_', dir=parent)).resolve()
        if cls.temporary.parent != parent:
            raise ValueError('test directory outside private workspace')

        def cleanup():
            resolved = cls.temporary.resolve()
            if resolved.parent != parent or not resolved.name.startswith('pc07_battle_pose_unit_'):
                raise ValueError('unsafe test cleanup target')
            shutil.rmtree(resolved)

        cls.addClassCleanup(cleanup)
        cls.context = contract.source_snapshot(cls.temporary / 'assembly')
        cls.snap = cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__, None, None, None)
        cls.manifest = contract.template('private/test_runs/pc07_battle_pose_test/diagnostic.sfc')

    def test_exact_append_and_preserved_consumers(self):
        result = guard.audit_pc07_battle_pose_images(self.manifest, self.snap['source'], self.snap['target'])
        self.assertTrue(result['inverse_restores_parent'])
        self.assertEqual(result['npc_protected_spans_unchanged'], 13)
        self.assertTrue(result['canonical_direct_KO_table_unchanged'])
        self.assertEqual(self.snap['streams']['entrypoints_checked'], 1024)
        self.assertEqual(self.snap['streams']['changed_selectors'], [5, 0x31, 0x32, 0xF0])
        for facing in range(4):
            start = contract.PRIMARY + facing * contract.STRIDE
            old = self.snap['source'][start:start + contract.STRIDE]
            new = self.snap['target'][start:start + contract.STRIDE]
            for selector in (0, 1, 3, 6, 7, 8, 0x0B, 0x0E, 0x17, 0x26):
                self.assertEqual(contract.tokens(old, selector, 255), contract.tokens(new, selector, 255))

    def test_extra_changes_to_game_and_inherited_content_refuse(self):
        # Main code, NPC art/palette, canonical KO/Epoch namespace, old body,
        # unchanged movement timing, world-map art, and undeclared expansion.
        for offset in (0, 0x19E2CE, 0x240C00, 0x115F5E, 0x420000, 0x421000,
                       0x425118, 0x480400, 0x490070, 0x500000):
            with self.subTest(offset=hex(offset)):
                target = bytearray(self.snap['target'])
                target[offset] ^= 1
                with self.assertRaises(ValueError):
                    guard.audit_pc07_battle_pose_images(self.manifest, self.snap['source'], bytes(target))

    def test_forged_scope_or_declared_extra_span_refuses(self):
        for key, value in (('production_approval', True), ('native_execution', True),
                           ('original_frame_prefix_preserved', 0),
                           ('sections', self.manifest['sections'] + [{'id': 'extra'}])):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = value
            with self.assertRaises(ValueError):
                guard.validate_pc07_battle_pose_manifest(manifest)

    def test_source_drift_refuses(self):
        source = bytearray(self.snap['source'])
        source[0x480400] ^= 1
        with self.assertRaises(ValueError):
            guard.audit_pc07_battle_pose_images(self.manifest, bytes(source), self.snap['target'])

    def test_output_escape_refuses(self):
        for output in ('diagnostic.sfc', 'private/test_runs/pc07_battle_pose_test/../diagnostic.sfc',
                       'private/test_runs/pc07_battle_pose_test/link/diagnostic.sfc'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                contract.output_path(output)


if __name__ == '__main__':
    unittest.main()
