"""Original host metadata specimens for NMI-envelope rejection tests.

The specimen deliberately abbreviates normal helper execution and mocks only
the separately tested v2 helper projection. It is not a native trace, full
helper proof, or manufactured emulator interrupt. No emulator is launched.
"""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_schala_package_helper_v2_nmi as tool


def specimen(interrupted_p=0x80,*,tcs=False):
    sp=0x1FEF
    baseline={'a':0xA55A,'x':0xD3C7,'y':0x8F69,'d':0,'dbr':0x7E,'sp':sp,'ps':0,'emulationMode':False}
    case={'name':'original envelope specimen','route':'success','cpu':baseline,'patches':[],
          'expected_cpu':baseline,'expected_writes':[],'expected_rom_reads':[],'stack_span':[0x7E0000+sp-51,0x7E0000+sp+1],
          'nmi_trigger':0x7F80EE,'nmi_resume':0x7F8232,'nmi_depth_before':50,'nmi_depth_after':52,
          'nmi_max_depth':59,'nmi_boundary':'first-countbits-jsr','nmi_phase_limit':262}
    code=bytearray([0xEA]*577);code[0]=0x08;code[0xEE:0xF1]=bytes.fromhex('203282');code[0x200]=0x1B;code[0x232]=0xA2
    if tcs:
        case.update(nmi_resume=0x7F80EF,nmi_depth_before=8,nmi_depth_after=50,nmi_max_depth=57,nmi_boundary='allocate-tcs')
        code[0xEE]=0x1B;code[0xEF]=0xEA
    resume=case['nmi_resume']
    handler=bytes.fromhex('08c22048aff05e7e1a8ff05e7e682840')
    cpu=dict(baseline,k=0x7F,pc=0xF100);flags=dict.fromkeys(tool.FLAG_KEYS,False)
    for k in tool.INTEGER_FLAGS:flags[k]=0
    flags['internalRegisters.nmiFlag']=True
    ledger={tool.v2.CODE+i:v for i,v in enumerate(code)};ledger.update({v:0xDB for v in tool.v2.TAILS.values()})
    events=[];epoch=0;clock=40;cycles=10
    def emit(kind,address,value=-1,*,tick=True,bus=None):
        nonlocal epoch,clock,cycles
        if tick:clock+=8;cycles+=1
        if kind=='exec':epoch+=1;cpu.update(k=address>>16,pc=address&65535)
        timing={k:0 for k in tool.TIME_KEYS};timing.update({'masterClock':clock,'memoryManager.masterClock':clock,
            'cpu.cycleCount':cycles,'frameCount':1,'ppu.frameCount':1,'ppu.scanline':226,
            'memoryManager.hClock':clock%1364,'clockRate':21477270})
        e={'kind':kind,'address':address,'value':value,'exec_index':epoch,'cpu':dict(cpu),'flags':dict(flags),
           'timing':timing,'stack':[ledger.get(0x7E0000+cpu['sp']+i,0xA5) for i in range(1,17)],
           'nmi_counter':ledger.get(0x7E5EF0,0xA5)+(ledger.get(0x7E5EF1,0xA5)<<8),'latch_peek':128}
        if kind in ('read','write'):e['bus_address']=address if bus is None else bus
        events.append(e)
        if kind=='write':ledger[address]=value
    def instruction(pc):emit('exec',pc,handler[pc-0x8020] if pc in tool.HANDLER_PCS else code[pc-tool.v2.CODE] if pc<tool.v2.CODE+len(code) else 0xDB)
    def push(value):
        emit('write',0x7E0000+cpu['sp'],value,bus=cpu['sp']);cpu['sp']-=1
    def pull():
        cpu['sp']+=1;value=ledger.get(0x7E0000+cpu['sp'],0xA5)
        emit('read',0x7E0000+cpu['sp'],value,bus=cpu['sp']);return value
    emit('fixture-baseline',tool.v2.ENTRY_BRIDGE)
    instruction(tool.v2.CODE);push(cpu['ps'])
    cpu.update(sp=sp-case['nmi_depth_before'],a=sp-50 if tcs else 0xD8A9,x=6,ps=interrupted_p,dbr=0x41)
    instruction(0x7F80EE);emit('request-before',0x4200,128,tick=False)
    flags.update({'internalRegisters.enableNmi':True,'cpu.nmiFlagCounter':2})
    emit('request-after',0x4200,128,tick=False)
    flags.update({'cpu.nmiFlagCounter':0,'cpu.needNmi':True})
    if tcs:
        cpu['pc']=resume&65535;emit('read',resume,code[resume-tool.v2.CODE]);cpu['sp']=cpu['a']
    else:
        cpu['pc']=0x80F1;push(0x80);push(0xF0);cpu['pc']=resume&65535
    flags['cpu.needNmi']=False
    emit('read',resume,code[resume-tool.v2.CODE]);push(0x7F);push((resume>>8)&255);push(resume&255);push(cpu['ps'])
    cpu.update(k=0,ps=(interrupted_p&~8)|4)
    emit('read',0xFFEA,0x20);emit('read',0xFFEB,0x80)
    instruction(0x8020);emit('handler-entry',0x8020,tick=False)
    emit('disable-before',0x4200,0,tick=False);flags['internalRegisters.enableNmi']=False
    emit('disable-after',0x4200,0,tick=False);push(cpu['ps'])
    instruction(0x8021);cpu['ps']&=~32
    instruction(0x8023);push(cpu['a']>>8);push(cpu['a']&255)
    instruction(0x8024);emit('read',0x7E5EF0,0xA5);emit('read',0x7E5EF1,0xA5)
    cpu.update(a=0xA5A5,ps=(cpu['ps']&~0x82)|0x80)
    instruction(0x8028);cpu['a']+=1
    instruction(0x8029);emit('write',0x7E5EF0,0xA6);emit('write',0x7E5EF1,0xA5)
    instruction(0x802D);lo=pull();hi=pull();restored=lo+(hi<<8)
    cpu.update(a=restored,ps=(cpu['ps']&~0x82)|(0x80 if restored&0x8000 else 0)|(2 if restored==0 else 0))
    instruction(0x802E);cpu['ps']=pull()
    instruction(0x802F);emit('pre-rti',0x802F,tick=False)
    cpu['ps']=pull();lo=pull();hi=pull();cpu['pc']=lo+(hi<<8);cpu['k']=pull()
    instruction(resume);emit('post-rti',resume,tick=False)
    # Abbreviated normal execution is delegated to the mocked, separately
    # proved helper projection. These are intentionally host-only CPU states.
    instruction(0x7F8200);cpu.update(baseline);instruction(tool.v2.TAILS['success'])
    last={e['address']:e['value'] for e in events if e['kind']=='write'}
    row={'name':case['name'],'route':case['route'],'events':events,
         'changes':[[a,v] for a,v in sorted(last.items()) if v!=0xA5],
         'preparation':{'wait_start_clock':0,'latch_rise':{
             'before':{'clock':10,'cycles':1,'frame':0,'scanline':224,'hclock':1354,'latch':False,'peek':0},
             'after':{'clock':20,'cycles':2,'frame':1,'scanline':225,'hclock':12,'latch':True,'peek':128}}},
         'input_fixture_before_hex':'','input_fixture_after_hex':'',
         'retired_scratch_before_hex':'a5'*128,'retired_scratch_after_hex':'a5'*128}
    return row,case,bytes(code),handler


class NmiEnvelopeTests(unittest.TestCase):
    def check(self,row,case,code,handler):
        with patch.object(tool.v2,'validate_record') as helper:
            result=tool.validate_record(row,case,code,handler)
            helper.assert_called_once();return result
    def rejected(self,mutator):
        args=specimen();mutator(*args)
        with self.assertRaises((tool.ConformanceError,tool.v2.ConformanceError,ValueError,KeyError,IndexError)):
            self.check(*args)
    def event(self,row,kind):return next(e for e in row['events'] if e['kind']==kind)
    def test_original_host_envelope_accepts(self):
        self.assertEqual(self.check(*specimen())['minimum_sp'],0x1FB4)
    def test_decimal_saved_status_restores(self):
        self.assertEqual(self.check(*specimen(0x88))['interrupted_cpu']['ps'],0x88)
    def test_memory_width_saved_status_restores(self):
        self.assertEqual(self.check(*specimen(0xA0))['interrupted_cpu']['ps'],0xA0)
    def test_tcs_has_two_distinct_source_explained_reads(self):
        result=self.check(*specimen(tcs=True))
        self.assertEqual(len(result['conditional_instruction_idle_read_indices']),1)
        self.assertNotEqual(result['conditional_instruction_idle_read_indices'][0],result['hardware_dummy_read_index'])
    def test_tcs_omitted_conditional_read_refuses(self):
        args=specimen(tcs=True);r=args[0]
        r['events'].remove(next(e for e in r['events'] if e['kind']=='read' and e['address']==args[1]['nmi_resume']))
        with self.assertRaises(tool.ConformanceError):self.check(*args)
    def test_tcs_wrong_effect_sp_refuses(self):
        args=specimen(tcs=True);args[1]['nmi_depth_after']=49
        with self.assertRaises(tool.ConformanceError):self.check(*args)
    def test_no_private_trace_dependency(self):self.assertEqual(len(specimen()[0]['events']),46)
    def test_missing_vector_read_refuses(self):
        self.rejected(lambda r,*_:r['events'].remove(next(e for e in r['events'] if e['address']==0xFFEA)))
    def test_wrong_vector_byte_refuses(self):
        self.rejected(lambda r,*_:next(e for e in r['events'] if e['address']==0xFFEA).__setitem__('value',0x30))
    def test_wrong_physical_alias_refuses(self):
        self.rejected(lambda r,*_:next(e for e in r['events'] if e['kind']=='write').__setitem__('bus_address',0x410000))
    def test_forged_stack_snapshot_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'handler-entry')['stack'].__setitem__(0,0xFF))
    def test_unexplained_final_stack_change_refuses(self):
        self.rejected(lambda r,c,*_:r['changes'].append([0x7E0000+c['cpu']['sp']-20,0]))
    def test_missing_final_stack_change_refuses(self):self.rejected(lambda r,*_:r['changes'].pop())
    def test_float_equal_final_byte_refuses(self):
        self.rejected(lambda r,*_:r['changes'][0].__setitem__(1,float(r['changes'][0][1])))
    def test_float_equal_final_address_refuses(self):
        self.rejected(lambda r,*_:r['changes'][0].__setitem__(0,float(r['changes'][0][0])))
    def test_boolean_final_byte_refuses(self):
        self.rejected(lambda r,*_:r['changes'][0].__setitem__(1,False))
    def test_tuple_final_change_refuses(self):
        self.rejected(lambda r,*_:r['changes'].__setitem__(0,tuple(r['changes'][0])))
    def test_duplicate_final_address_refuses(self):
        self.rejected(lambda r,*_:r['changes'].insert(0,list(r['changes'][0])))
    def test_undeclared_retired_scratch_read_refuses(self):
        def mutate(r,*_):
            e=copy.deepcopy(r['events'][1]);e.update(kind='read',address=0x7E4000,bus_address=0x7E4000,value=0xA5)
            r['events'].insert(2,e)
        self.rejected(mutate)
    def test_unrelated_wram_read_refuses(self):
        def mutate(r,*_):
            e=copy.deepcopy(r['events'][1]);e.update(kind='read',address=0x7E6000,bus_address=0x7E6000,value=0xA5)
            r['events'].insert(2,e)
        self.rejected(mutate)
    def test_counter_snapshot_drift_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'post-rti').__setitem__('nmi_counter',0))
    def test_request_advances_cpu_clock_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'request-after')['timing'].__setitem__('cpu.cycleCount',999))
    def test_request_does_not_set_countdown_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'request-after')['flags'].__setitem__('cpu.nmiFlagCounter',0))
    def test_countdown_over_two_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'request-after')['flags'].__setitem__('cpu.nmiFlagCounter',3))
    def test_horizontal_raster_out_of_range_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['timing'].__setitem__('memoryManager.hClock',1365))
    def test_later_irq_source_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['flags'].__setitem__('cpu.irqSource',1))
    def test_untyped_flag_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['flags'].__setitem__('cpu.needNmi',0))
    def test_later_dma_pending_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['flags'].__setitem__('dmaController.dmaPending',True))
    def test_hidden_phase_key_substitution_refuses(self):
        def mutate(r,*_):r['events'][0]['timing']['ppu.nmiScanline']=r['events'][0]['timing'].pop('ppu.scanline')
        self.rejected(mutate)
    def test_no_natural_latch_edge_refuses(self):
        self.rejected(lambda r,*_:r['preparation']['latch_rise']['before'].__setitem__('latch',True))
    def test_wide_edge_bracket_refuses(self):
        self.rejected(lambda r,*_:r['preparation']['latch_rise']['after'].__setitem__('clock',1000))
    def test_completion_outside_phase_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['timing'].__setitem__('ppu.scanline',0))
    def test_full_clock_reversal_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['timing'].__setitem__('memoryManager.masterClock',1))
    def test_extra_event_key_refuses(self):self.rejected(lambda r,*_:r['events'][0].__setitem__('invented',True))
    def test_wrong_handler_register_refuses(self):
        self.rejected(lambda r,*_:next(e for e in r['events'] if e['kind']=='exec' and e['address']==0x8028)['cpu'].__setitem__('x',0))
    def test_wrong_handler_width_refuses(self):
        self.rejected(lambda r,*_:next(e for e in r['events'] if e['kind']=='exec' and e['address']==0x8023)['cpu'].__setitem__('ps',0xA4))
    def test_handler_memory_wrong_owner_refuses(self):
        self.rejected(lambda r,*_:next(e for e in r['events'] if e['kind']=='write' and e['address']==0x7E5EF0).__setitem__('exec_index',1))
    def test_restored_pbr_drift_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'post-rti')['cpu'].__setitem__('k',0))
    def test_no_countbits_reserve_refuses(self):self.rejected(lambda r,c,*_:c.__setitem__('nmi_max_depth',57))
    def test_unknown_scope_refuses(self):
        with self.assertRaises(tool.ConformanceError):tool.build_cases(b'',scope='unbounded')
    def test_helper_projection_failure_propagates(self):
        with patch.object(tool.v2,'validate_record',side_effect=tool.v2.ConformanceError('independent helper rejection')):
            with self.assertRaises(tool.v2.ConformanceError):tool.validate_record(*specimen())
    def test_tag_cpu_detached_from_exec_refuses(self):
        self.rejected(lambda r,*_:self.event(r,'handler-entry')['cpu'].__setitem__('a',0))
    def test_hidden_nmi_enable_change_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['flags'].__setitem__('internalRegisters.enableNmi',True))
    def test_late_pending_request_refuses(self):
        self.rejected(lambda r,*_:r['events'][-1]['flags'].__setitem__('cpu.needNmi',True))
    def test_hardware_push_general_register_change_refuses(self):
        self.rejected(lambda r,c,*_:next(e for e in r['events'] if e['kind']=='write' and e['address']==0x7E0000+c['cpu']['sp']-53)['cpu'].__setitem__('x',1))


class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from test_schala_package_helper_v1_rom_source import original_fixture_rom
        cls.rom=original_fixture_rom();cls.cases=tool.build_cases(cls.rom)
    def test_declared_224_case_matrix_is_deterministic(self):
        self.assertEqual(len(self.cases),224)
        self.assertEqual(tool.canonical(self.cases),tool.canonical(tool.build_cases(self.rom)))
    def test_only_two_stack_placements_with_reserve(self):
        self.assertEqual({c['cpu']['sp'] for c in self.cases},{0x1FEF,0x06D8})
        self.assertTrue(all(c['cpu']['sp']>=c['nmi_max_depth'] for c in self.cases))
    def test_both_banks_branches_four_statuses(self):
        rows=[c for c in self.cases if c['route']=='success']
        self.assertEqual({c['source_bank'] for c in rows},{0x41,0x42})
        self.assertEqual({c['flag'] for c in rows},{0,0x40})
        self.assertEqual({c['cpu']['ps'] for c in rows},{0,0xC3,0x4C,0x8F})
    def test_all_three_routes_are_declared(self):
        self.assertEqual({c['route'] for c in self.cases},{'canonical','refusal','success'})
        self.assertEqual({c['nmi_depth_after'] for c in self.cases if c['nmi_boundary']=='refusal-release-tcs'},{8})
    def test_pilot_is_two_deepest_cases(self):
        cases=tool.build_cases(self.rom,'pilot');self.assertEqual(len(cases),2)
        self.assertTrue(all(c['nmi_depth_after']==52 and c['nmi_max_depth']==59 for c in cases))
    def test_boundary_pilot_contains_all_success_sites(self):
        cases=tool.build_cases(self.rom,'boundary-pilot');self.assertEqual(len(cases),19)
        self.assertEqual({c['nmi_boundary'] for c in cases if c['route']=='success'},set(tool.SUCCESS_BOUNDARIES))
    def test_source_archive_exact_guarded_set(self):
        hashes=dict.fromkeys(tool.ARCHIVE_KEYS,'a'*64);tool.require_archive_hashes(hashes,dict(hashes))
    def test_source_archive_missing_key_refuses(self):
        hashes=dict.fromkeys(tool.ARCHIVE_KEYS,'a'*64);actual=dict(hashes);actual.pop('launcher')
        with self.assertRaises(tool.ConformanceError):tool.require_archive_hashes(actual,hashes)
    def test_source_archive_altered_value_refuses(self):
        hashes=dict.fromkeys(tool.ARCHIVE_KEYS,'a'*64);actual=dict(hashes);actual['launcher']='b'*64
        with self.assertRaises(tool.ConformanceError):tool.require_archive_hashes(actual,hashes)
    def test_source_archive_extra_key_refuses(self):
        hashes=dict.fromkeys(tool.ARCHIVE_KEYS,'a'*64);actual=dict(hashes,extra='a'*64)
        with self.assertRaises(tool.ConformanceError):tool.require_archive_hashes(actual,hashes)


if __name__=='__main__':unittest.main()
