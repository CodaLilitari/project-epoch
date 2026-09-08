"""Original abbreviated timing envelopes; no private trace or emulator launch.

Only the frozen v3 normal-helper projection is mocked. These tests certify
the timing/phase evidence boundary, not the specimen's hardware reachability.
"""
import copy
from collections import Counter
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_schala_package_helper_v4_timing_calibration as c
PAYLOAD,REGISTRY,_=c.model.original_components()


def specimen():
    case=c.build_cases(PAYLOAD,REGISTRY)[0]
    pcs=[c.CODE]+list(c.boundaries(case).values())+[c.TAILS['success']]
    def sample(ordinal,pc):
        fullclock=10000 if ordinal==0 else 10012+(ordinal-1)*32
        flags=dict.fromkeys(c.FLAG_KEYS,False)
        flags['internalRegisters.nmiFlag']=True
        for k in c.INTEGER_FLAGS:flags[k]=0
        cpu=dict(case['cpu'],k=pc>>16,pc=pc&65535)
        if ordinal==len(pcs):cpu.update(case['expected_cpu'])
        return {'exec_index':ordinal,'pc':pc,'cpu':cpu,'flags':flags,'latch_peek':128,
            'timing':{'masterClock':fullclock,'memoryManager.masterClock':fullclock,'cpu.cycleCount':1000+ordinal*5,
                'frameCount':1,'ppu.frameCount':1,'ppu.scanline':226,'memoryManager.hClock':20 if ordinal==0 else 32+(ordinal-1)*32,'clockRate':21477270}}
    row={'name':case['name'],'route':case['route'],'cpu':dict(case['expected_cpu']),
        'exec_addresses':pcs,'instructions':len(pcs),'sp_observations':[[2,pcs[1],case['cpu']['sp']]],
        'preparation':{'wait_start_clock':0,'latch_rise':{
            'before':{'clock':8612,'cycles':800,'frame':0,'scanline':224,'hclock':1360,'latch':False,'peek':0},
            'after':{'clock':8620,'cycles':802,'frame':1,'scanline':225,'hclock':4,'latch':True,'peek':128}}},
        'fixture_baseline':sample(0,c.ENTRY_BRIDGE),
        'execution_samples':[sample(i,pc) for i,pc in enumerate(pcs,1)]}
    return row,case,bytes([0xEA]*577)


class TimingEnvelopeTests(unittest.TestCase):
    def check(self,row,case,code):
        with patch.object(c.v3,'validate_record') as normal:
            result=c.validate_record(row,case,code=code,registry=REGISTRY,payload=PAYLOAD)
            normal.assert_called_once()
            self.assertEqual(normal.call_args.args[0],{k:v for k,v in row.items() if k not in c.EXTRA_KEYS})
            self.assertEqual(normal.call_args.kwargs,{'code':code,'registry':REGISTRY,'payload':PAYLOAD,'code_base':c.CODE})
            return result

    def reject(self,mutator):
        args=specimen();mutator(*args)
        with self.assertRaises(c.ConformanceError):self.check(*args)

    def test_original_timing_envelope_and_explicit_clock_bases(self):
        result=self.check(*specimen())
        self.assertTrue(result['normal_v3_passed'])
        self.assertFalse(result['interrupt_requested'])
        self.assertFalse(result['schedule_executed'])
        self.assertTrue(result['schedule_is_inference'])
        self.assertEqual(result['execution_elapsed_basis'],'first-observed-helper-opcode')
        self.assertEqual(result['schedule_elapsed_basis'],'fixture-baseline-before-original-entry-JML')
        self.assertEqual(result['elapsed_execution'][1]['master_clocks'],32)
        self.assertEqual(result['schedule'][0]['elapsed_master_clocks'],44)

    def test_every_boundary_uses_its_first_execution_occurrence(self):
        row,case,code=specimen();result=self.check(row,case,code)
        self.assertEqual([s['trigger'] for s in result['schedule']],list(c.boundaries(case).values()))
        self.assertEqual(len(result['schedule']),5)

    def test_absolute_clock_translation_preserves_elapsed_projection(self):
        row,case,code=specimen();before=self.check(row,case,code)
        for sample in [row['fixture_baseline']]+row['execution_samples']:
            t=sample['timing'];t['memoryManager.masterClock']+=0xFFFFFFFF;t['masterClock']=t['memoryManager.masterClock']&0xFFFFFFFF
        for sample in row['preparation']['latch_rise'].values():sample['clock']+=0xFFFFFFFF
        row['preparation']['wait_start_clock']+=0xFFFFFFFF
        after=self.check(row,case,code)
        self.assertEqual(before['elapsed_execution'],after['elapsed_execution'])
        self.assertEqual(before['schedule'],after['schedule'])
        self.assertNotEqual(before['absolute_baseline_timing'],after['absolute_baseline_timing'])

    def test_full_projection_rejection_propagates(self):
        with patch.object(c.v3,'validate_record',side_effect=c.ConformanceError('normal proof rejected')):
            with self.assertRaises(c.ConformanceError):c.validate_record(*specimen()[:2],code=specimen()[2],registry=REGISTRY,payload=PAYLOAD)

    def test_missing_execution_timing_rejects(self):self.reject(lambda r,*_:r['execution_samples'].pop(1))
    def test_reordered_execution_timing_rejects(self):
        def mutate(r,*_):r['execution_samples'][1],r['execution_samples'][2]=r['execution_samples'][2],r['execution_samples'][1]
        self.reject(mutate)
    def test_wrong_execution_ordinal_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1].__setitem__('exec_index',1))
    def test_timing_pc_cannot_borrow_handler_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1].__setitem__('pc',0x8080))
    def test_old_wram_pbr_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['cpu'].__setitem__('k',0x7F))
    def test_float_equal_cpu_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['cpu'].__setitem__('d',0.0))
    def test_integer_emulation_mode_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['cpu'].__setitem__('emulationMode',0))
    def test_extra_timing_field_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['timing'].__setitem__('ppu.nmiScanline',225))
    def test_missing_full_master_clock_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['timing'].pop('memoryManager.masterClock'))
    def test_low32_clock_alias_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['timing'].__setitem__('masterClock',0))
    def test_equal_instruction_clock_rejects(self):
        def mutate(r,*_):r['execution_samples'][1]['timing']=dict(r['execution_samples'][0]['timing'])
        self.reject(mutate)
    def test_float_clock_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['timing'].__setitem__('cpu.cycleCount',1000.0))
    def test_inconsistent_raster_with_valid_full_clock_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['timing'].__setitem__('memoryManager.hClock',1))
    def test_nmi_enable_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['flags'].__setitem__('internalRegisters.enableNmi',True))
    def test_pending_nmi_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['flags'].__setitem__('cpu.nmiFlagCounter',1))
    def test_irq_source_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['flags'].__setitem__('cpu.irqSource',1))
    def test_pending_dma_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['flags'].__setitem__('dmaController.dmaPending',True))
    def test_integer_boolean_flag_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1]['flags'].__setitem__('cpu.needNmi',0))
    def test_latch_peek_mismatch_rejects(self):self.reject(lambda r,*_:r['execution_samples'][1].__setitem__('latch_peek',0))
    def test_missing_natural_edge_rejects(self):self.reject(lambda r,*_:r['preparation']['latch_rise']['before'].__setitem__('latch',True))
    def test_nonconsecutive_edge_bracket_rejects(self):self.reject(lambda r,*_:r['preparation']['latch_rise']['after'].__setitem__('clock',9000))
    def test_wrong_scanline_after_edge_rejects(self):self.reject(lambda r,*_:r['fixture_baseline']['timing'].__setitem__('ppu.scanline',227))
    def test_prep_frame_origin_mismatch_rejects(self):self.reject(lambda r,*_:r['preparation']['latch_rise']['before'].__setitem__('frame',1))
    def test_prep_raster_disagrees_with_short_clock_bracket_rejects(self):self.reject(lambda r,*_:r['preparation']['latch_rise']['before'].__setitem__('hclock',1200))
    def test_adjacent_baseline_scanline_with_unrelated_clock_gap_rejects(self):
        def mutate(r,*_):
            t=r['fixture_baseline']['timing'];t['masterClock']+=20;t['memoryManager.masterClock']+=20
        self.reject(mutate)
    def test_baseline_wrong_bridge_rejects(self):self.reject(lambda r,*_:r['fixture_baseline'].__setitem__('pc',0x7FF100))
    def test_baseline_cpu_mutation_rejects(self):self.reject(lambda r,*_:r['fixture_baseline']['cpu'].__setitem__('sp',0x1FFF))
    def test_final_cpu_disagrees_with_normal_record_rejects(self):self.reject(lambda r,*_:r['execution_samples'][-1]['cpu'].__setitem__('sp',0x1FFF))
    def test_entry_jml_cannot_change_accumulator_rejects(self):self.reject(lambda r,*_:r['execution_samples'][0]['cpu'].__setitem__('a',0))
    def test_normal_sp_and_full_cpu_observation_disagree_rejects(self):self.reject(lambda r,*_:r['sp_observations'][0].__setitem__(2,0x1FFF))
    def test_missing_boundary_rejects(self):
        def mutate(r,*_):
            r['exec_addresses'][1]=c.CODE+1;r['execution_samples'][1]['pc']=c.CODE+1;r['execution_samples'][1]['cpu']['pc']=1
        self.reject(mutate)


class CalibrationMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases=c.build_cases(PAYLOAD,REGISTRY)

    def test_exact_22_groups_are_deterministic(self):
        self.assertEqual(len(self.cases),22);self.assertEqual(len({x['name'] for x in self.cases}),22)
        self.assertEqual(self.cases,c.build_cases(PAYLOAD,REGISTRY))
    def test_both_stack_placements_and_route_counts(self):
        self.assertEqual(Counter(x['cpu']['sp'] for x in self.cases),{0x1FEF:11,0x06D8:11})
        self.assertEqual(Counter(x['route'] for x in self.cases),{'success':16,'canonical':2,'refusal':4})
    def test_exact_four_bindings_both_branches(self):
        self.assertEqual({(x['selector'],x['flag'],x['cpu']['sp']) for x in self.cases if x['route']=='success'},
            {(s,f,sp) for s in range(0x80,0x84) for f in (0,0x40) for sp in c.ENTRY_STACKS})
    def test_status_zero_only_is_explicit(self):self.assertTrue(all(x['cpu']['ps']==0 for x in self.cases))
    def test_exact_92_scheduling_rows(self):self.assertEqual(sum(len(c.boundaries(x)) for x in self.cases),92)
    def test_framed_refusal_has_release_boundary(self):
        rows=[x for x in self.cases if x['selector']==0x84]
        self.assertTrue(all('refusal-release-tcs' in c.boundaries(x) for x in rows))
        self.assertTrue(all('refusal-release-tcs' not in c.boundaries(x) for x in self.cases if x['selector']==0x90))
    def test_mutated_immutable_inputs_refuse(self):
        with self.assertRaises(ValueError):c.build_cases(PAYLOAD[:-1],REGISTRY)
    def test_schedule_ceil_and_wrap_are_exact(self):
        for elapsed,expected in ((0,228),(1,227),(1364,227),(1365,226),(1364*229,261)):
            self.assertEqual(c.schedule_start(225,elapsed),expected)
    def test_schedule_numeric_aliases_refuse(self):
        for rise,delta in ((225.0,0),(225,False),(262,0),(225,-1),(225,1000001)):
            with self.assertRaises(c.ConformanceError):c.schedule_start(rise,delta)

    def test_raster_clock_bounds_include_short_line(self):
        before={'ppu.frameCount':1,'ppu.scanline':240,'memoryManager.hClock':100,'memoryManager.masterClock':1000}
        for clocks in (1360,1364):
            after=dict(before,**{'ppu.scanline':241,'memoryManager.masterClock':1000+clocks})
            c.require_raster_clock_interval(before,after,225)
        after=dict(before,**{'ppu.scanline':241,'memoryManager.masterClock':2359})
        with self.assertRaises(c.ConformanceError):c.require_raster_clock_interval(before,after,225)

    def test_raster_wrap_uses_observed_nmi_frame_origin(self):
        before={'ppu.frameCount':1,'ppu.scanline':261,'memoryManager.hClock':100,'memoryManager.masterClock':1000}
        after={'ppu.frameCount':1,'ppu.scanline':0,'memoryManager.hClock':100,'memoryManager.masterClock':2364}
        c.require_raster_clock_interval(before,after,225)
        before.update({'ppu.scanline':224});after.update({'ppu.scanline':225,'ppu.frameCount':2})
        c.require_raster_clock_interval(before,after,225)


if __name__=='__main__':unittest.main()
