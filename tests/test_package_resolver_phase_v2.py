"""Original projection fixtures; preserved v1 tests stay independent and unchanged."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_package_resolver_phase_v2 as phase
import test_package_resolver_phase_v1 as original

def specimen(early=True,pre_effect=True):
    trace,_=original.specimen(pre_effect);trace['schema']=phase.SCHEMA
    rows=trace['records']
    gate=next(r for r in rows if r['kind']=='scene-gate')
    read=copy.deepcopy(gate);read.update(kind='bus-read',address=0x7ECCEA,value=0);read['cpu']['pc']+=3
    rows.insert(rows.index(gate)+1,read)
    gate=next(r for r in rows if r['kind']=='scene-effect-gate')
    read=rows[rows.index(gate)+1];read['cpu']=copy.deepcopy(gate['cpu']);read['cpu']['pc']+=3
    early_rows=[]
    if early:
        assert pre_effect
        for r in rows:
            if r['context_id']:r['context_id']+=2
        for i,(entry_pc,exit_pc,kind) in enumerate(((0xD1FE97,0xD1FEF3,'battle-irq'),(0xD1E77C,0xD1E898,'normal-nmi')),1):
            template=next(r for r in rows if r['kind']=='interrupt-entry' and r['context_kind']==kind)
            entry=copy.deepcopy(template);entry.update(address=entry_pc,context_id=i);entry['cpu']['pc']=entry_pc&65535
            read=copy.deepcopy(entry);read.update(kind='bus-read',address=0x7E007F,value=0)
            rti=copy.deepcopy(entry);rti.update(kind='interrupt-rti',address=exit_pc);rti['cpu']['pc']=exit_pc&65535
            early_rows.extend((entry,read,rti))
        rows[2:2]=early_rows
    for i,row in enumerate(rows):
        row['timing']['masterClock']=1000+i*10;row['timing']['memoryManager.masterClock']=1000+i*10
        row['timing']['cpu.cycleCount']=100+i
    references={};early_reference=[]
    resolver=next(i for i,r in enumerate(rows) if r['kind']=='resolver-entry')
    for i,row in enumerate(rows):
        old={**copy.deepcopy(row),'wram':copy.deepcopy(row['gates'])}
        if i<resolver and row['kind'] in {'interrupt-entry','interrupt-rti'}:early_reference.append(old)
        if i>=resolver:
            key=row['context_kind']+'-'+row['kind'] if row['kind'] in {'interrupt-entry','interrupt-rti'} else row['kind']
            if key in {'resolver-entry','resolver-tail','common-loader-entry','scene-effect-gate',
                'battle-irq-interrupt-entry','battle-irq-interrupt-rti','normal-nmi-interrupt-entry','normal-nmi-interrupt-rti'}:
                references[key]=old
    return trace,{'phases':references,'earlier_context_records':early_reference}

class PhaseV2Tests(unittest.TestCase):
    def setUp(self):self.trace,self.reference=specimen()
    def reject(self):
        with self.assertRaises(phase.PhaseError):phase.summarize(self.trace,self.reference)
    def rows(self,kind):return [r for r in self.trace['records'] if r['kind']==kind]
    def test_balanced_early_projection_preserves_all_original_rows(self):
        before=copy.deepcopy(self.trace);result=phase.summarize(self.trace,self.reference)
        self.assertEqual(self.trace,before)
        self.assertEqual(len(result['early_interrupt_pairs']),2)
        self.assertEqual(len(result['post_resolver_interrupt_pairs']),2)
        self.assertEqual(result['early_historical_records_matched'],4)
        self.assertEqual(result['projection']['removed_record_count'],6)
        self.assertEqual(result['record_count'],len(before['records']))
        self.assertFalse(result['projection']['native_interrupt_free_execution'])
        for kind,record in result['phases'].items():self.assertEqual(before['records'][record['index']]['kind'],kind)
    def test_no_pre_effect_or_early_context(self):
        trace,reference=specimen(False,False);self.assertEqual(phase.summarize(trace,reference)['early_interrupt_pairs'],[])
    def test_optional_pre_effect_without_early_context(self):
        trace,reference=specimen(False,True);phase.summarize(trace,reference)
    def test_v1_schema_does_not_become_v2_acceptance(self):self.trace['schema']=phase.v1.SCHEMA;self.reject()
    def test_omit_complete_balanced_early_pair(self):
        self.trace['records']=[r for r in self.trace['records'] if r['context_id']!=1];self.reject()
    def test_omit_all_early_contexts(self):
        self.trace['records']=[r for r in self.trace['records'] if r['context_id'] not in {1,2}];self.reject()
    def test_extra_pair_without_historical_membership(self):
        self.reference['earlier_context_records']=self.reference['earlier_context_records'][2:];self.reject()
    def test_misordered_historical_pairs(self):
        self.reference['earlier_context_records'].reverse();self.reject()
    def test_early_pair_crosses_resolver(self):
        row=self.rows('interrupt-rti')[1];self.trace['records'].remove(row);self.reject()
    def test_nested_early_pair(self):
        self.trace['records'].insert(3,copy.deepcopy(self.rows('interrupt-entry')[1]));self.reject()
    def test_early_stack_change(self):self.rows('interrupt-rti')[0]['stack'][10]=1;self.reject()
    def test_early_cpu_change(self):self.rows('interrupt-rti')[0]['cpu']['x']=1;self.reject()
    def test_early_historical_gate_change(self):self.rows('interrupt-entry')[0]['gates']['CD02']=1;self.reject()
    def test_early_historical_identity_change(self):
        for r in self.trace['records']:
            if r['context_id']==1:r['context_id']=10
        self.reject()
    def test_post_context_reuses_removed_id(self):
        for r in self.trace['records']:
            if r['context_id']==3:r['context_id']=2
        self.reject()
    def test_post_context_uses_new_but_nonhistorical_id(self):
        for r in self.trace['records']:
            if r['context_id']==4:r['context_id']=5
        self.reject()
    def test_early_bus_context_mismatch(self):self.rows('bus-read')[0]['context_id']=2;self.reject()
    def test_early_bus_gate_byte_forgery(self):self.rows('bus-read')[0]['value']=1;self.reject()
    def test_early_bus_backward_clock_not_hidden_by_projection(self):
        row=self.rows('bus-read')[0];row['timing']['masterClock']=1;row['timing']['memoryManager.masterClock']=1;self.reject()
    def test_early_missing_engine_key_not_hidden_by_projection(self):
        del self.rows('bus-read')[0]['engine']['cpu.needNmi'];self.reject()
    def test_early_fresh_engine_values_independent_of_old_reference(self):
        self.rows('interrupt-entry')[0]['engine']['cpu.needNmi']=True
        result=phase.summarize(self.trace,self.reference)
        self.assertTrue(result['early_interrupt_pairs'][0]['entry_engine']['cpu.needNmi'])
    def test_early_context_count_bound(self):
        self.reference['earlier_context_records']*=5;self.reject()
    def test_source_owned_gate_witness_indices(self):
        result=phase.summarize(self.trace,self.reference)
        self.assertEqual(len(result['gate_read_witnesses']),2)
        for w in result['gate_read_witnesses']:
            self.assertEqual(w['read_index'],w['entry_index']+1)
            self.assertEqual(self.trace['records'][w['read_index']]['address'],w['read_bus_address'])
    def test_gate_read_wrong_cpu_pc(self):
        row=next(r for r in self.rows('bus-read') if r['address']==0x7E5D9B);row['cpu']['pc']+=1;self.reject()
    def test_gate_read_wrong_register(self):
        row=next(r for r in self.rows('bus-read') if r['address']==0x7E5D9B);row['cpu']['a']=1;self.reject()
    def test_gate_read_delayed_by_another_record(self):
        row=next(r for r in self.rows('bus-read') if r['address']==0x7E5D9B)
        extra=copy.deepcopy(row);extra.update(address=0x4200)
        self.trace['records'].insert(self.trace['records'].index(row),extra);self.reject()
    def test_gate_read_wrong_stack(self):
        row=next(r for r in self.rows('bus-read') if r['address']==0x7E5D9B);row['stack'][6]=1;self.reject()
    def test_gate_read_wrong_context(self):
        row=next(r for r in self.rows('bus-read') if r['address']==0x7E5D9B);row['context_id']=1;self.reject()
    def test_scene_first_gate_read_missing(self):
        row=next(r for r in self.rows('bus-read') if r['address']==0x7ECCEA);self.trace['records'].remove(row);self.reject()
    def test_early_scene_gate_is_not_removed_as_unchecked_data(self):
        row=self.rows('bus-read')[0];row.update(kind='scene-gate',address=0xCD1609,value=-1)
        row['cpu']['k']=0xCD;row['cpu']['pc']=0x1609;self.reject()
    def test_all_original_metadata_keys_checked(self):self.trace['extra']=True;self.reject()
    def test_partial_original_trace_refused(self):self.trace['error']='failure';self.reject()
    def test_tail_summary_keeps_v1_nonpromotion(self):
        r=phase.summarize(self.trace,self.reference)
        for key in ('native_helper_executed','interrupt_exclusion_proved','complete_dma_bus_trace','deadline_certified','production_approval'):
            self.assertFalse(r[key])
    def test_collector_changes_only_protocol_and_environment_names(self):
        old=phase.v1.COLLECTOR.read_text(encoding='utf-8')
        expected=old.replace(phase.v1.SCHEMA,phase.SCHEMA).replace('PE_RESOLVER_PHASE_','PE_RESOLVER_PHASE_V2_')
        self.assertEqual(phase.COLLECTOR.read_text(encoding='utf-8'),expected)

if __name__=='__main__':unittest.main()
