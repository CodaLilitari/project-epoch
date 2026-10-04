import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_irq_request_transition_v1 as audit


class CompositionAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference=json.loads((audit.ROOT/audit.PHASE_PIN[0]).read_bytes())

    def test_exact_seed_reused(self):
        row,state=audit.observed_seed(self.reference)
        self.assertEqual((row['master_clock'],state.v_counter,state.need_irq),(2155080050,119,0))
        self.assertTrue(state.nmi_enabled)
        self.assertTrue(state.irq_enabled_cache)

    def test_inconsistent_pair_refuses(self):
        r=copy.deepcopy(self.reference)
        row=next(x for x in r['runs'][1]['projection']['phases'] if x['kind']=='resolver-entry')
        row['hardware']['internalRegisters.needIrq']=1
        with self.assertRaisesRegex(ValueError,'pair seed'):audit.observed_seed(r)

    def test_hostile_or_mistyped_matching_pair_refuses(self):
        for key,value in (('internalRegisters.needIrq',2),('internalRegisters.needIrq',False),
            ('internalRegisters.irqFlag',0),('internalRegisters.verticalTimer',119),
            ('cpu.prevIrqSource',1),('cpu.irqSource',1),('dmaController.hdmaChannels',0)):
            r=copy.deepcopy(self.reference)
            for run in r['runs']:
                next(x for x in run['projection']['phases'] if x['kind']=='resolver-entry')['hardware'][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):audit.observed_seed(r)

    def test_missing_or_duplicate_phase_refuses(self):
        for duplicate in (True,False):
            r=copy.deepcopy(self.reference)
            for run in r['runs']:
                phases=run['projection']['phases']
                entry=next(x for x in phases if x['kind']=='resolver-entry')
                if duplicate:phases.append(entry)
                else:phases.remove(entry)
            with self.assertRaisesRegex(ValueError,'one resolver'):audit.observed_seed(r)

    def test_no_deadline_promotion_from_reference(self):
        r=copy.deepcopy(self.reference);r['deadline_certified']=True
        with self.assertRaisesRegex(ValueError,'non-admission'):audit.observed_seed(r)

    def test_each_pin_is_fail_closed(self):
        for name,size,digest in (audit.PHASE_PIN,audit.UPSTREAM_PIN):
            self.assertEqual(audit.identity(name,size,digest)['sha256'],digest)
            with self.assertRaisesRegex(ValueError,'size drift'):audit.identity(name,size+1,digest)
            with self.assertRaisesRegex(ValueError,'hash drift'):audit.identity(name,size,'0'*64)
        with self.assertRaisesRegex(ValueError,'bounded'):audit.identity('../AGENTS.md')

    def test_source_manifest_drift_refuses_before_simulation(self):
        raw=(audit.ROOT/audit.UPSTREAM_PIN[0]).read_bytes()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'references').mkdir()
            (root/audit.PHASE_PIN[0]).write_bytes((audit.ROOT/audit.PHASE_PIN[0]).read_bytes())
            (root/audit.UPSTREAM_PIN[0]).write_bytes(raw+b' ')
            with patch.object(audit,'ROOT',root),self.assertRaisesRegex(ValueError,'drift'):
                audit.collect()

    def test_conditional_bounds_keep_game_gate_closed(self):
        _,state=audit.observed_seed(self.reference)
        r=audit.conditional_request(state)
        self.assertEqual(r['scenarios'][0]['request_offsets'],{'match':124372,'flag':124376,'source':124380})
        self.assertEqual(r['scenarios'][1]['request_offsets'],{'match':124740,'flag':124744,'source':124748})
        self.assertIsNone(r['game_deadline'])
        self.assertFalse(r['game_helper_admitted'])

    def test_conditional_entry_rejects_even_unused_state_drift(self):
        _,state=audit.observed_seed(self.reference)
        for change in ({'h_counter':187},{'need_irq':1},{'irq_flag':True},{'irq_enabled_cache':False}):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'exact modeled'):
                audit.conditional_request(replace(state,**change))

    def test_callback_and_refresh_counterexamples(self):
        _,state=audit.observed_seed(self.reference)
        r=audit.adversaries(state)
        self.assertFalse(r['line_callback_is_observed_native_behavior'])
        self.assertEqual(r['unclosed_line_callback_counterexample']['line'],165)
        self.assertTrue(r['unclosed_line_callback_counterexample']['scripted_adversarial_callbacks'])
        self.assertEqual([x['final_h'] for x in r['refresh_endpoint_scenarios']],[186]*4)
        self.assertEqual([x['first_source_offset'] for x in r['pending']],[124748,4,8,12,1020])
        h10=r['unclosed_h10_callback_counterexample']
        self.assertEqual(audit.request_offsets(h10),{'match':124740,'flag':124744,'source':124744})
        self.assertFalse(h10['ordinary_callback_hypothesis_applies'])

    def test_pending_domain_metadata(self):
        r=audit.finite_pending()
        self.assertEqual(r['cases'],16384)
        self.assertEqual(len(r['ordered_projection_sha256']),64)

    def test_cpu_example_state_distinctions(self):
        r=audit.cpu_examples()
        self.assertEqual(r['sample_then_sei'],'irq')
        self.assertEqual(r['sample_then_source_clear'],'irq')
        self.assertEqual(r['source_before_sample'],'none')
        self.assertFalse(r['handler_entry_proved'])

    def test_complete_output_is_deterministic_and_has_no_game_arrays(self):
        first=audit.serial(audit.collect())
        second=audit.serial(audit.collect())
        self.assertEqual(first,second)
        r=json.loads(first)
        self.assertEqual(len(r['source_identities']),14)
        self.assertEqual(len(r['original_source_identities']),8)
        self.assertEqual(r['evidence_level'],'source-conditional-host-model')
        for key in ('raw_game_data_emitted','native_pair_reexecuted','game_deadline_certified',
                    'cpu_acceptance_deadline_certified','handler_entry_proved','production_approval'):
            self.assertIs(r[key],False)
        self.assertNotIn('wram',r)
        self.assertNotIn('rom',r)


if __name__=='__main__':unittest.main()
