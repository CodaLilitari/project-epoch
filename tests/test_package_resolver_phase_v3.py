"""Adversarial tests for the additive counter/cache evidence contract."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_package_resolver_phase_v3 as phase
import test_package_resolver_phase_v2 as old

def specimen():
    legacy,reference=old.specimen()
    for i,row in enumerate(legacy['records']):
        clock=10000+i*10000
        row['timing']['masterClock']=clock;row['timing']['memoryManager.masterClock']=clock
    # Historical fixtures share the modified phase clocks deliberately.
    resolver=next(i for i,r in enumerate(legacy['records']) if r['kind']=='resolver-entry')
    reference={'phases':{},'earlier_context_records':[]}
    for i,row in enumerate(legacy['records']):
        entry={**copy.deepcopy(row),'wram':copy.deepcopy(row['gates'])}
        if i<resolver and row['kind'] in {'interrupt-entry','interrupt-rti'}:reference['earlier_context_records'].append(entry)
        if i>=resolver:
            key=row['context_kind']+'-'+row['kind'] if row['kind'] in {'interrupt-entry','interrupt-rti'} else row['kind']
            if key in {'resolver-entry','resolver-tail','common-loader-entry','scene-effect-gate',
                'battle-irq-interrupt-entry','battle-irq-interrupt-rti','normal-nmi-interrupt-entry','normal-nmi-interrupt-rti'}:
                reference['phases'][key]=entry
    trace=copy.deepcopy(legacy);trace['schema']=phase.SCHEMA
    for r in trace['records']:
        r['engine'].update({'internalRegisters.hCounter':189,'internalRegisters.vCounter':118})
    start=copy.deepcopy(trace['records'][0]);start.update(kind='cache-frame-start',address=0)
    start['timing'].update({'masterClock':11000,'memoryManager.masterClock':11000,'ppu.scanline':0,'memoryManager.hClock':0})
    end=copy.deepcopy(start);end.update(kind='cache-line-one',address=(end['cpu']['k']<<16)|end['cpu']['pc'])
    end['timing'].update({'masterClock':12380,'memoryManager.masterClock':12380,'ppu.scanline':1,'memoryManager.hClock':16})
    trace['records'][1:1]=[start,end]
    entry=copy.deepcopy(start);entry['timing']['memoryManager.masterClock']=10500
    rti=copy.deepcopy(end);rti['timing']['memoryManager.masterClock']=15000
    return trace,{'v2_reference':reference,'v2_trace':legacy,'cache_context':[entry,rti]}

class PhaseV3Tests(unittest.TestCase):
    def setUp(self):self.trace,self.reference=specimen()
    def reject(self):
        with self.assertRaises(phase.PhaseError):phase.summarize(self.trace,self.reference)
    def test_full_projection_and_no_mutation(self):
        before=copy.deepcopy(self.trace);r=phase.summarize(self.trace,self.reference)
        self.assertEqual(before,self.trace);self.assertEqual(r['engine_field_count'],163)
        self.assertEqual(r['cache_witness']['elapsed_master_clocks'],1380)
        self.assertTrue(r['complete_v2_trace_equal']);self.assertFalse(r['deadline_certified'])
        self.assertFalse(r['cache_witness']['hidden_cache_values_directly_observed'])
    def test_missing_counter(self):del self.trace['records'][0]['engine']['internalRegisters.hCounter'];self.reject()
    def test_counter_domain(self):
        for value in (True,-1,65536,1.5,None):
            with self.subTest(value=value):
                self.trace,self.reference=specimen();self.trace['records'][1]['engine']['internalRegisters.vCounter']=value;self.reject()
    def test_counter_65535_is_legal_snapshot(self):
        self.trace['records'][1]['engine']['internalRegisters.vCounter']=65535;phase.summarize(self.trace,self.reference)
    def test_extra_field(self):self.trace['records'][1]['engine']['ppu.nmiScanline']=225;self.reject()
    def test_old_engine_drift_not_hidden(self):self.trace['records'][3]['engine']['cpu.needNmi']=True;self.reject()
    def test_missing_pair(self):del self.trace['records'][2];self.reject()
    def test_duplicate_pair(self):self.trace['records'].insert(3,copy.deepcopy(self.trace['records'][2]));self.reject()
    def test_wrong_schema(self):self.trace['schema']=phase.v2.SCHEMA;self.reject()
    def test_failed_completion(self):self.trace['error']='bad';self.reject()
    def test_event_address(self):self.trace['records'][1]['address']=1;self.reject()
    def test_line_one_pc_ownership(self):self.trace['records'][2]['address']^=1;self.reject()
    def test_start_hclock(self):self.trace['records'][1]['timing']['memoryManager.hClock']=4;self.reject()
    def test_start_line(self):self.trace['records'][1]['timing']['ppu.scanline']=261;self.reject()
    def test_end_line(self):self.trace['records'][2]['timing']['ppu.scanline']=2;self.reject()
    def test_whole_frame_hidden_between_endpoints(self):
        r=self.trace['records'][2]['timing'];r['masterClock']+=357368;r['memoryManager.masterClock']+=357368;self.reject()
    def test_shorter_line(self):
        r=self.trace['records'][2]['timing'];r['masterClock']-=4;r['memoryManager.masterClock']-=4;self.reject()
    def test_later_frame(self):
        r=self.trace['records'][2]['timing'];r['frameCount']+=1;r['ppu.frameCount']+=1;self.reject()
    def test_context_unowned(self):self.trace['records'][2]['context_id']=1;self.reject()
    def test_removed_row_common_validation(self):self.trace['records'][1]['stack']=[0]*11;self.reject()
    def test_removed_row_old_engine_validation(self):self.trace['records'][1]['engine']['cpu.needNmi']=1;self.reject()
    def test_changed_legacy_bus_byte_refused(self):
        r=next(r for r in self.trace['records'] if r['kind']=='bus-read');r['value']^=1;self.reject()
    def test_future_counter_values_not_deadline(self):
        for r in self.trace['records']:r['engine']['internalRegisters.vCounter']=60000
        result=phase.summarize(self.trace,self.reference);self.assertFalse(result['deadline_certified'])

if __name__=='__main__':unittest.main()
