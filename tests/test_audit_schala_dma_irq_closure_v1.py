import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import audit_schala_dma_irq_closure_v1 as audit


class DmaCompositionAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trace = json.loads((audit.ROOT /
            'private/test_runs/resolver_phase_v3_full_20261003_3/trace.json').read_bytes())['records']

    def test_complete_frozen_pair_revalidation(self):
        projected, identities = audit.accepted_projection()
        self.assertEqual(projected, audit.project(self.trace))
        self.assertEqual(len(identities), 2)
        self.assertEqual(projected['resolver_interval']['master_clocks'], 4244)
        self.assertEqual(projected['through_following_interrupt']['master_clocks'], 124904)
        self.assertEqual(projected['full_window_watched_hardware_writes'], 280)
        self.assertFalse(projected['watcher_covers_timeup'])
        self.assertFalse(projected['future_configuration_certified'])

    def test_missing_and_duplicate_phase_fail_closed(self):
        for kind in ('resolver-entry', 'resolver-tail'):
            with self.subTest(kind=kind):
                rows = copy.deepcopy(self.trace)
                next(r for r in rows if r['kind'] == kind)['kind'] = 'scene-gate'
                with self.assertRaisesRegex(ValueError, 'one '):
                    audit.project(rows)
                rows = copy.deepcopy(self.trace)
                rows[0]['kind'] = kind
                with self.assertRaisesRegex(ValueError, 'one '):
                    audit.project(rows)

    def test_byte_boolean_drift_is_not_equal_configuration(self):
        for key, value in (('srcBank', 0), ('invertDirection', 0), ('transferMode', 8),
                           ('hdmaBank', False), ('hdmaLineCounterAndRepeat', True)):
            rows = copy.deepcopy(self.trace)
            entry = next(r for r in rows if r['kind'] == 'resolver-entry')
            entry['engine']['dmaController.channel[0].'+key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.project(rows)

    def test_intermediate_configuration_change_is_detected(self):
        rows = copy.deepcopy(self.trace)
        index = next(i for i,r in enumerate(rows) if r['kind']=='resolver-entry')
        rows[index+1]['engine']['dmaController.channel[5].invertDirection'] = True
        with self.assertRaisesRegex(ValueError, 'sampled configuration drift'):
            audit.project(rows)

    def test_watched_write_inside_resolver_is_detected(self):
        rows = copy.deepcopy(self.trace)
        index = next(i for i,r in enumerate(rows) if r['kind']=='resolver-entry')
        rows[index+1].update(kind='bus-write', address=0x804209, value=0)
        with self.assertRaisesRegex(ValueError, 'hardware traffic'):
            audit.project(rows)

    def test_full_clock_cannot_be_replaced_by_low_word(self):
        rows = copy.deepcopy(self.trace)
        entry = next(r for r in rows if r['kind']=='resolver-entry')
        entry['timing']['memoryManager.masterClock'] = True
        with self.assertRaisesRegex(ValueError, 'full serialized clock'):
            audit.project(rows)

    def test_watch_aliases_and_missing_timeup_are_explicit(self):
        for bank in range(256):
            mapped = bank < 0x40 or 0x80 <= bank < 0xC0
            for offset in (0x4200, 0x4207, 0x420D, 0x4300, 0x437F):
                self.assertEqual(audit.hardware_bus((bank<<16)|offset), mapped)
            self.assertFalse(audit.hardware_bus((bank<<16)|0x4211))
            self.assertFalse(audit.hardware_bus((bank<<16)|0x2133))
        for value in (True, -1, 2**24):
            with self.assertRaises(ValueError):
                audit.hardware_bus(value)

    def test_source_and_reference_pins_refuse_drift(self):
        for name, size, digest in (audit.PHASE_PIN, audit.SOURCE_PIN, audit.FACTS_PIN):
            audit.identity(name,size,digest)
            with self.assertRaisesRegex(ValueError, 'size drift'):
                audit.identity(name,size+1,digest)
            with self.assertRaisesRegex(ValueError, 'hash drift'):
                audit.identity(name,size,'0'*64)
        with self.assertRaisesRegex(ValueError, 'bounded repository'):
            audit.identity('../AGENTS.md')

    def test_result_does_not_promote_address_facts(self):
        result = audit.collect()
        self.assertEqual(result['direct_irq_register_candidates'], [])
        self.assertIn(0x2133, result['possible_b_payload_ports'])
        self.assertEqual(result['hdma_service_bound'], 65536)
        self.assertFalse(result['service_bound_is_a_time_bound'])
        self.assertFalse(result['premises_are_certificates'])
        self.assertFalse(result['callback_closure_proved'])
        self.assertFalse(result['all_memory_handler_effects_closed'])
        self.assertFalse(result['game_helper_admitted'])
        self.assertFalse(result['production_approval'])
        self.assertIsNone(result['game_deadline'])
        self.assertTrue(result['original_v3_auditor_reproduced_byte_identically'])
        for item in result['channel_domains']:
            self.assertFalse(item['runtime_observation'])
            self.assertFalse(any(item['irq_candidates'].values()))

    def test_manifest_omission_or_duplication_fails_before_evidence_use(self):
        for duplicate in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in audit.ORIGINAL_FILES + (audit.SOURCE_MANIFEST,):
                    (root/name).parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(audit.ROOT/name,root/name)
                value = json.loads((root/audit.SOURCE_MANIFEST).read_bytes())
                value['sources'] = value['sources'] * 2 if duplicate else []
                (root/audit.SOURCE_MANIFEST).write_bytes(audit.serial(value))
                with patch.object(audit,'ROOT',root), patch.object(audit,'accepted_projection') as accepted:
                    with self.assertRaisesRegex(ValueError, 'drift'):
                        audit.collect()
                    accepted.assert_not_called()

    def test_consumed_original_is_rechecked_against_initial_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = json.loads((audit.ROOT/audit.SOURCE_MANIFEST).read_bytes())
            names = list(audit.ORIGINAL_FILES) + [audit.SOURCE_MANIFEST, audit.CALLBACK_FACTS,
                audit.PHASE_PIN[0]] + [s['path'] for s in manifest['sources']]
            for name in names:
                (root/name).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(audit.ROOT/name,root/name)
            def during_audit():
                original = root/audit.ORIGINAL_FILES[1]
                original.write_bytes(original.read_bytes()+b'\n# concurrent drift\n')
                return audit.project(self.trace), []
            with patch.object(audit,'ROOT',root), patch.object(audit,'accepted_projection',side_effect=during_audit):
                with self.assertRaisesRegex(ValueError, 'size drift'):
                    audit.collect()


if __name__ == '__main__':
    unittest.main()
