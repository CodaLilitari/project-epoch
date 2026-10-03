"""Original phase specimens; no ROM, checkpoint, emulator, or captured game bytes."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_package_resolver_phase_v1 as phase

def specimen(pre_effect=True):
    rows=[]
    def row(kind,address=0,ctx=None,value=-1):
        i=len(rows);cpu={'a':0,'x':0,'y':0,'d':0,'dbr':0x7E,'sp':0x700,
            'ps':0x24,'k':address>>16,'pc':address&65535,'emulationMode':False}
        gates={key:0 for key in phase.GATES};gates['9877']=8
        result={'kind':kind,'address':address,'value':value,'poll':0 if kind=='baseline' else 381 if kind=='terminal' else 378,
            'cpu':cpu,'timing':{'masterClock':1000+i*10,'memoryManager.masterClock':1000+i*10,
                'cpu.cycleCount':100+i,'frameCount':1,'ppu.frameCount':1,'ppu.scanline':100,
                'memoryManager.hClock':100,'clockRate':21477270},
            'engine':{**{key:False for key in phase.BOOL_FIELDS},**{key:0 for key in phase.INT_FIELDS}},
            'stack':[0x20]+[0]*11,'trampolines':phase.TRAMPOLINES.copy(),'gates':gates,
            'context_id':ctx[0] if ctx else 0,'context_kind':ctx[1] if ctx else 'main','context_depth':1 if ctx else 0}
        rows.append(result);return result
    row('baseline')
    if pre_effect:row('pre-effect',phase.EXEC_SITES['pre-effect'])
    row('resolver-entry',phase.EXEC_SITES['resolver-entry'])
    row('resolver-tail',phase.EXEC_SITES['resolver-tail'])
    row('common-loader-entry',phase.EXEC_SITES['common-loader-entry'])
    row('interrupt-entry',0xD1FE97,(1,'battle-irq'))
    row('interrupt-rti',0xD1FEF3,(1,'battle-irq'))
    row('interrupt-entry',0xD1E77C,(2,'normal-nmi'))
    row('scene-gate',phase.EXEC_SITES['scene-gate'],(2,'normal-nmi'))
    row('scene-effect-gate',phase.EXEC_SITES['scene-effect-gate'],(2,'normal-nmi'))
    row('bus-read',0x7E5D9B,(2,'normal-nmi'),0)
    row('interrupt-rti',0xD1E898,(2,'normal-nmi'))
    row('terminal')
    reference={}
    for item in rows:
        key=item['context_kind']+'-'+item['kind'] if item['kind'] in {'interrupt-entry','interrupt-rti'} else item['kind']
        if key in {'resolver-entry','resolver-tail','common-loader-entry','scene-effect-gate',
            'normal-nmi-interrupt-entry','normal-nmi-interrupt-rti','battle-irq-interrupt-entry','battle-irq-interrupt-rti'}:
            reference[key]={**copy.deepcopy(item),'wram':copy.deepcopy(item['gates'])}
    return {'schema':phase.SCHEMA,'records':rows,'error':None,'terminal_poll':381},reference

class PhaseTests(unittest.TestCase):
    def setUp(self):self.trace,self.reference=specimen()
    def row(self,kind):return next(row for row in self.trace['records'] if row['kind']==kind)
    def rejected(self):
        with self.assertRaises(phase.PhaseError):phase.summarize(self.trace,self.reference)
    def test_genuine_original_specimen(self):
        result=phase.summarize(self.trace,self.reference)
        self.assertEqual(result['resolver_to_tail_master_clocks'],10)
        self.assertEqual(result['engine_field_count'],161)
        self.assertEqual(len(result['interrupt_pairs']),2)
        self.assertFalse(result['interrupt_exclusion_proved'])
        self.assertFalse(result['deadline_certified'])
    def test_optional_pre_effect_absent(self):
        trace,reference=specimen(False);phase.summarize(trace,reference)
    def test_each_required_engine_field_missing(self):
        original=copy.deepcopy(self.trace)
        for key in phase.ENGINE_KEYS:
            with self.subTest(key=key):
                self.trace=copy.deepcopy(original);del self.row('resolver-entry')['engine'][key];self.rejected()
    def test_each_engine_boolean_rejects_integer(self):
        original=copy.deepcopy(self.trace)
        for key in phase.BOOL_FIELDS:
            with self.subTest(key=key):
                self.trace=copy.deepcopy(original);self.row('resolver-entry')['engine'][key]=0;self.rejected()
    def test_each_engine_integer_rejects_boolean_float_negative_overflow(self):
        original=copy.deepcopy(self.trace)
        for key,maximum in phase.INT_FIELDS.items():
            for invalid in (False,0.0,-1,maximum+1):
                with self.subTest(key=key,value=invalid):
                    self.trace=copy.deepcopy(original);self.row('resolver-entry')['engine'][key]=invalid;self.rejected()
    def test_all_source_width_maxima_accept(self):
        for row in self.trace['records']:
            row['engine']={**{key:True for key in phase.BOOL_FIELDS},**phase.INT_FIELDS}
        phase.summarize(self.trace,self.reference)
    def test_omitted_enum_and_nonserialized_fields_refuse(self):
        for key in ('cpu.stopState','memoryManager.nextEvent','ppu.nmiScanline','dmaController.activeChannel','internalRegisters.irqEnabled'):
            with self.subTest(key=key):
                self.trace,self.reference=specimen();self.row('resolver-entry')['engine'][key]=0;self.rejected()
    def test_historical_entire_cpu_drift(self):
        self.row('resolver-entry')['cpu']['a']=1;self.rejected()
    def test_historical_stack_drift(self):
        self.row('resolver-entry')['stack'][11]=1;self.rejected()
    def test_historical_full_clock_drift(self):
        row=self.row('resolver-entry');row['timing']['masterClock']+=1;row['timing']['memoryManager.masterClock']+=1;self.rejected()
    def test_historical_gate_drift(self):
        self.row('resolver-entry')['gates']['CD02']=1;self.rejected()
    def test_historical_first_pair_drift(self):
        self.row('interrupt-entry')['cpu']['a']=1;self.rejected()
    def test_duplicate_pre_effect(self):
        self.trace['records'].insert(2,copy.deepcopy(self.row('pre-effect')));self.rejected()
    def test_pre_effect_after_resolver(self):
        r=self.trace['records'].pop(1);self.trace['records'].insert(3,r);self.rejected()
    def test_interrupt_between_pre_effect_and_resolver_is_scoped_refusal(self):
        row=copy.deepcopy(self.row('interrupt-entry'))
        row['timing']=copy.deepcopy(self.row('pre-effect')['timing'])
        self.trace['records'].insert(2,row);self.rejected()
    def test_missing_common_loader(self):
        self.trace['records'].remove(self.row('common-loader-entry'));self.rejected()
    def test_terminal_partial_and_error(self):
        for key,value in [('error','serialization failed'),('terminal_poll',380),('terminal_poll',True),('schema','other')]:
            with self.subTest(key=key,value=value):
                self.trace,self.reference=specimen();self.trace[key]=value;self.rejected()
    def test_truncated_json_refused_before_summary(self):
        with self.assertRaises(json.JSONDecodeError):phase.parse_trace(json.dumps(self.trace)[:-1].encode())
    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(phase.PhaseError):phase.parse_trace(b'{"error":true,"error":null}')
    def test_nonfinite_json_refused(self):
        for value in (b'NaN',b'Infinity',b'-Infinity'):
            with self.assertRaises(phase.PhaseError):phase.parse_trace(b'{"value":'+value+b'}')
    def test_json_bytes_limit(self):
        with mock.patch.object(phase,'MAX_TRACE',1):
            with self.assertRaises(phase.PhaseError):phase.parse_trace(b'{}')
    def test_record_bound(self):
        self.trace['records']*=phase.MAX_RECORDS;self.rejected()
    def test_backward_poll_clock_cycle_frame(self):
        for key in ('poll','memoryManager.masterClock','cpu.cycleCount','ppu.frameCount'):
            self.trace,self.reference=specimen();r=self.row('terminal')
            if key=='poll':r[key]=0
            else:r['timing'][key]=0
            self.rejected()
    def test_unknown_top_level_field(self):self.trace['forged']=True;self.rejected()
    def test_bool_as_cpu_integer(self):self.row('resolver-entry')['cpu']['a']=False;self.rejected()
    def test_emulation_mode(self):self.row('resolver-entry')['cpu']['emulationMode']=True;self.rejected()
    def test_stack_outside_mirror(self):self.row('baseline')['cpu']['sp']=0x1FF4;self.rejected()
    def test_invalid_trampoline(self):self.row('baseline')['trampolines'][1]=0;self.rejected()
    def test_inconsistent_clock_halves(self):self.row('baseline')['timing']['masterClock']+=1;self.rejected()
    def test_unsafe_lua_integer_precision(self):self.row('baseline')['timing']['cpu.cycleCount']=2**53;self.rejected()
    def test_bus_byte_vs_snapshot(self):self.row('bus-read')['value']=1;self.rejected()
    def test_bus_without_positive_control(self):self.trace['records'].remove(self.row('bus-read'));self.rejected()
    def test_wrong_bus_domain(self):self.row('bus-read')['address']=0x7F5D9B;self.rejected()
    def test_bus_outside_window(self):
        self.row('baseline')['kind']='bus-read';self.row('bus-read')['address']=0x4200;self.rejected()
    def test_interrupt_context_id(self):self.row('interrupt-rti')['context_id']=4;self.rejected()
    def test_interrupt_stack_changed(self):self.row('interrupt-rti')['stack'][5]=1;self.rejected()
    def test_interrupt_register_changed(self):self.row('interrupt-rti')['cpu']['d']=1;self.rejected()
    def test_irq_stacked_i_need_not_be_zero(self):
        for row in self.trace['records']:
            if row['context_kind']=='battle-irq':row['stack'][0]=0x24
        for row in self.reference.values():
            if row['context_kind']=='battle-irq':row['stack'][0]=0x24
        phase.summarize(self.trace,self.reference)
    def test_nested_interrupt_refused(self):self.row('interrupt-entry')['context_depth']=2;self.rejected()
    def test_scene_gate_main_context_refused(self):
        row=self.row('scene-gate');row['context_id']=0;row['context_depth']=0;row['context_kind']='main';self.rejected()
    def test_bus_mirrors_are_qualified_per_byte(self):
        for bank in (0,0x3F,0x80,0xBF):
            self.assertIsNotNone(phase.bus_domain(bank<<16|0x4200))
            self.assertIsNotNone(phase.bus_domain(bank<<16|0x437F))
            self.assertEqual(phase.bus_domain(bank<<16|0x80),'gate')
        for address in (0x404200,0x7E4200,0xC04200,0x4380,0x4201,0x7F0080):self.assertIsNone(phase.bus_domain(address))
    def test_fresh_engine_values_not_replaced_by_historical(self):
        self.row('resolver-entry')['engine']['cpu.needNmi']=True
        self.row('resolver-entry')['engine']['dmaController.hdmaChannels']=0xA5
        result=phase.summarize(self.trace,self.reference)
        self.assertTrue(result['phases']['resolver-entry']['engine']['cpu.needNmi'])
        self.assertEqual(result['phases']['resolver-entry']['engine']['dmaController.hdmaChannels'],0xA5)
    def test_no_native_launch_during_summary(self):
        with mock.patch.object(phase.subprocess,'run',side_effect=AssertionError('native forbidden')):
            phase.summarize(self.trace,self.reference)

if __name__=='__main__':unittest.main()
