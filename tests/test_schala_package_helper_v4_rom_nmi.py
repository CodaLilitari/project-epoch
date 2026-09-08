"""Original host metadata for the separately scoped immutable-ROM/NMI envelope.

The abbreviated execution specimen is authored metadata, not a native trace.
Only the separately frozen v3 helper projection is mocked in envelope tests.
The site specimen patches only its expected hash while testing relocation;
no original cartridge, private trace, emulator or ROM mutation is required.
"""
from __future__ import annotations
import copy
from collections import Counter
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_schala_package_helper_v4_rom_nmi as tool
PAYLOAD,REGISTRY,CERTIFICATE=tool.v3.model.original_components()


def specimen(interrupted_p=0x80,*,tcs=False):
    sp=0x1FEF
    baseline={'a':0xA55A,'x':0xD3C7,'y':0x8F69,'d':0,'dbr':0x7E,'sp':sp,'ps':0,'emulationMode':False}
    case={'name':'original envelope specimen','route':'success','cpu':baseline,'patches':[],
          'expected_cpu':baseline,'expected_writes':[],'expected_rom_reads':[],'stack_span':[0x7E0000+sp-51,0x7E0000+sp+1],
          'nmi_trigger':0x4100EE,'nmi_resume':0x410232,'nmi_depth_before':50,'nmi_depth_after':52,
          'nmi_max_depth':59,'nmi_boundary':'first-countbits-jsr','nmi_phase_limit':262,
          'nmi_start_scanline':226,'nmi_rise_scanline':225}
    code=bytearray([0xEA]*577);code[0]=0x08;code[0xEE:0xF1]=bytes.fromhex('203202');code[0x200]=0x1B;code[0x232]=0xA2
    if tcs:
        case.update(nmi_resume=0x4100EF,nmi_depth_before=8,nmi_depth_after=50,nmi_max_depth=57,nmi_boundary='allocate-tcs')
        code[0xEE]=0x1B;code[0xEF]=0xEA
    resume=case['nmi_resume']
    handler=bytes.fromhex('08c22048aff05e7e1a8ff05e7e682840')
    cpu=dict(baseline,k=0,pc=0x8060);flags=dict.fromkeys(tool.FLAG_KEYS,False)
    for k in tool.INTEGER_FLAGS:flags[k]=0
    flags['internalRegisters.nmiFlag']=True
    ledger={}
    events=[];epoch=0;clock=1372;cycles=10
    def emit(kind,address,value=-1,*,tick=True,bus=None):
        nonlocal epoch,clock,cycles
        if tick:clock+=8;cycles+=1
        if kind=='exec':epoch+=1;cpu.update(k=address>>16,pc=address&65535)
        timing={k:0 for k in tool.TIME_KEYS};timing.update({'masterClock':clock,'memoryManager.masterClock':clock,
            'cpu.cycleCount':cycles,'frameCount':1,'ppu.frameCount':1,'ppu.scanline':226,
            'memoryManager.hClock':(clock-8)%1364,'clockRate':21477270})
        e={'kind':kind,'address':address,'value':value,'exec_index':epoch,'cpu':dict(cpu),'flags':dict(flags),
           'timing':timing,'stack':[ledger.get(0x7E0000+cpu['sp']+i,0xA5) for i in range(1,17)],
           'nmi_counter':ledger.get(0x7E5EF0,0xA5)+(ledger.get(0x7E5EF1,0xA5)<<8),'latch_peek':128}
        if kind in ('read','write'):e['bus_address']=address if bus is None else bus
        events.append(e)
        if kind=='write':ledger[address]=value
    def instruction(pc):emit('exec',pc,handler[pc-0x8080] if pc in tool.HANDLER_PCS else code[pc-tool.v3.CODE] if tool.v3.CODE<=pc<tool.v3.CODE+len(code) else 0x80)
    def push(value):
        emit('write',0x7E0000+cpu['sp'],value,bus=cpu['sp']);cpu['sp']-=1
    def pull():
        cpu['sp']+=1;value=ledger.get(0x7E0000+cpu['sp'],0xA5)
        emit('read',0x7E0000+cpu['sp'],value,bus=cpu['sp']);return value
    emit('fixture-baseline',tool.v3.ENTRY_BRIDGE)
    instruction(tool.v3.CODE);push(cpu['ps'])
    cpu.update(sp=sp-case['nmi_depth_before'],a=sp-50 if tcs else 0xD8A9,x=6,ps=interrupted_p,dbr=0x41)
    instruction(0x4100EE);emit('request-before',0x4200,128,tick=False)
    flags.update({'internalRegisters.enableNmi':True,'cpu.nmiFlagCounter':2})
    emit('request-after',0x4200,128,tick=False)
    flags.update({'cpu.nmiFlagCounter':0,'cpu.needNmi':True})
    if tcs:
        cpu['pc']=resume&65535;emit('read',resume,code[resume-tool.v3.CODE]);cpu['sp']=cpu['a']
    else:
        cpu['pc']=0x00F1;push(0x00);push(0xF0);cpu['pc']=resume&65535
    flags['cpu.needNmi']=False
    emit('read',resume,code[resume-tool.v3.CODE]);push(0x41);push((resume>>8)&255);push(resume&255);push(cpu['ps'])
    cpu.update(k=0,ps=(interrupted_p&~8)|4)
    emit('read',0xFFEA,0x80);emit('read',0xFFEB,0x80)
    instruction(0x8080);emit('handler-entry',0x8080,tick=False)
    emit('disable-before',0x4200,0,tick=False);flags['internalRegisters.enableNmi']=False
    emit('disable-after',0x4200,0,tick=False);push(cpu['ps'])
    instruction(0x8081);cpu['ps']&=~32
    instruction(0x8083);push(cpu['a']>>8);push(cpu['a']&255)
    instruction(0x8084);emit('read',0x7E5EF0,0xA5);emit('read',0x7E5EF1,0xA5)
    cpu.update(a=0xA5A5,ps=(cpu['ps']&~0x82)|0x80)
    instruction(0x8088);cpu['a']+=1
    instruction(0x8089);emit('write',0x7E5EF0,0xA6);emit('write',0x7E5EF1,0xA5)
    instruction(0x808D);lo=pull();hi=pull();restored=lo+(hi<<8)
    cpu.update(a=restored,ps=(cpu['ps']&~0x82)|(0x80 if restored&0x8000 else 0)|(2 if restored==0 else 0))
    instruction(0x808E);cpu['ps']=pull()
    instruction(0x808F);emit('pre-rti',0x808F,tick=False)
    cpu['ps']=pull();lo=pull();hi=pull();cpu['pc']=lo+(hi<<8);cpu['k']=pull()
    instruction(resume);emit('post-rti',resume,tick=False)
    # Abbreviated normal execution is delegated to the mocked, separately
    # proved helper projection. These are intentionally host-only CPU states.
    instruction(0x410200);cpu.update(baseline);instruction(tool.v3.TAILS['success'])
    last={e['address']:e['value'] for e in events if e['kind']=='write'}
    row={'name':case['name'],'route':case['route'],'events':events,
         'changes':[[a,v] for a,v in sorted(last.items()) if v!=0xA5],
         'preparation':{'wait_start_clock':0,'latch_rise':{
             'before':{'clock':0,'cycles':1,'frame':0,'scanline':224,'hclock':1354,'latch':False,'peek':0},
             'after':{'clock':20,'cycles':2,'frame':1,'scanline':225,'hclock':12,'latch':True,'peek':128}}},
         'input_fixture_before_hex':REGISTRY.hex(),'input_fixture_after_hex':REGISTRY.hex(),
         'descriptor_fixture_before_hex':PAYLOAD.hex(),'descriptor_fixture_after_hex':PAYLOAD.hex(),
         'retired_scratch_before_hex':'a5'*128,'retired_scratch_after_hex':'a5'*128}
    return row,case,bytes(code),handler


class ImmutableRomEnvelopeTests(unittest.TestCase):
    def check(self, row, case, code, handler):
        with patch.object(tool.v3,'validate_record') as helper:
            result=tool.validate_record(row,case,code,handler,payload=PAYLOAD,registry=REGISTRY)
            helper.assert_called_once()
            self.assertEqual(helper.call_args.kwargs,{'code':code,'payload':PAYLOAD,'registry':REGISTRY})
            return result,helper.call_args.args[0]

    def event(self,row,kind):return next(e for e in row['events'] if e['kind']==kind)

    def reject(self,mutator,*,tcs=False):
        args=specimen(tcs=tcs);mutator(*args)
        with self.assertRaises(tool.ConformanceError):self.check(*args)

    def test_original_abbreviated_envelope_accepts(self):
        result,projection=self.check(*specimen())
        self.assertEqual(result['minimum_sp'],0x1FB4)
        self.assertEqual(result['interrupted_cpu']['k'],0x41)
        self.assertEqual(result['interrupted_cpu']['pc'],0x0232)
        self.assertEqual(projection['exec_addresses'][0],0x410000)
        self.assertEqual(projection['exec_addresses'][-1],0x008110)
        self.assertFalse(any(pc in tool.HANDLER_PCS for pc in projection['exec_addresses']))

    def test_original_specimen_has_no_private_trace_dependency(self):
        self.assertEqual(len(specimen()[0]['events']),46)

    def test_decimal_and_hidden_accumulator_status_restore(self):
        for status in (0x88,0xA0,0x80):
            with self.subTest(status=status):
                result,_=self.check(*specimen(status))
                self.assertEqual(result['interrupted_cpu']['ps'],status)

    def test_tcs_conditional_idle_and_hardware_dummy_are_distinct(self):
        result,_=self.check(*specimen(tcs=True))
        self.assertEqual(len(result['conditional_instruction_idle_read_indices']),1)
        self.assertNotEqual(result['conditional_instruction_idle_read_indices'][0],result['hardware_dummy_read_index'])

    def test_wrong_old_vector_low_byte_refuses(self):
        self.reject(lambda r,*_:next(e for e in r['events'] if e['address']==0xFFEA).__setitem__('value',0x20))

    def test_missing_vector_read_refuses(self):
        self.reject(lambda r,*_:r['events'].remove(next(e for e in r['events'] if e['address']==0xFFEB)))

    def test_wrong_old_helper_pbr_refuses(self):
        self.reject(lambda r,*_:self.event(r,'post-rti')['cpu'].__setitem__('k',0x7F))

    def test_original_bridge_cannot_change_first_helper_registers(self):
        self.reject(lambda r,*_:r['events'][1]['cpu'].__setitem__('a',0xFFFF))

    def test_wrong_old_handler_address_refuses(self):
        def mutate(r,*_):
            e=next(e for e in r['events'] if e['kind']=='exec' and e['address']==0x8080)
            e['address']=0x8020;e['cpu']['pc']=0x8020
        self.reject(mutate)

    def test_wrong_rom_dummy_opcode_byte_refuses(self):
        self.reject(lambda r,c,*_:next(e for e in r['events'] if e['kind']=='read' and e['address']==c['nmi_resume']).__setitem__('value',0))

    def test_wrong_tcs_idle_opcode_byte_refuses(self):
        self.reject(lambda r,c,*_:next(e for e in r['events'] if e['kind']=='read' and e['address']==c['nmi_resume']).__setitem__('value',0),tcs=True)

    def test_wrong_hardware_pbr_stack_byte_refuses(self):
        self.reject(lambda r,c,*_:next(e for e in r['events'] if e['kind']=='write' and e['address']==0x7E0000+c['cpu']['sp']-52).__setitem__('value',0x7F))

    def test_jsr_near_push_high_byte_uses_relocated_return(self):
        row,case,code,handler=specimen()
        writes=[e for e in row['events'] if e['kind']=='write' and e['address'] in (0x7E0000+case['cpu']['sp']-50,0x7E0000+case['cpu']['sp']-51)]
        self.assertEqual([e['value'] for e in writes[:2]],[0,0xF0])
        self.check(row,case,code,handler)

    def test_wrong_old_jsr_return_high_byte_refuses(self):
        self.reject(lambda r,c,*_:next(e for e in r['events'] if e['kind']=='write' and e['address']==0x7E0000+c['cpu']['sp']-50).__setitem__('value',0x80))

    def test_all_immutable_snapshot_roles_are_checked_without_projection(self):
        for key in ('input_fixture_before_hex','input_fixture_after_hex','descriptor_fixture_before_hex','descriptor_fixture_after_hex'):
            with self.subTest(key=key):self.reject(lambda r,*_,key=key:r.__setitem__(key,'00'))

    def test_retired_scratch_snapshots_reach_frozen_projection(self):
        _,projection=self.check(*specimen())
        self.assertEqual(projection['retired_scratch_before_hex'],'a5'*128)
        self.assertEqual(projection['retired_scratch_after_hex'],'a5'*128)

    def test_undeclared_rom_read_edges_refuse(self):
        for address in (0x41FFFF,0x420000+len(PAYLOAD),0x430000+len(REGISTRY),0x440000):
            def mutate(r,*_):
                e=copy.deepcopy(r['events'][1]);e.update(kind='read',address=address,bus_address=address,value=0xFF)
                r['events'].insert(2,e)
            with self.subTest(address=address):self.reject(mutate)

    def test_immutable_code_is_not_general_helper_data(self):
        def mutate(r,_,code,*__):
            e=copy.deepcopy(r['events'][1]);e.update(kind='read',address=tool.v3.CODE,bus_address=tool.v3.CODE,value=code[0])
            r['events'].insert(2,e)
        self.reject(mutate)

    def test_wrong_in_span_registry_data_byte_refuses(self):
        def mutate(r,*_):
            e=copy.deepcopy(r['events'][1]);e.update(kind='read',address=0x430000,bus_address=0x430000,value=REGISTRY[0]^1)
            r['events'].insert(2,e)
        self.reject(mutate)

    def test_rom_write_refuses(self):
        def mutate(r,*_):
            e=copy.deepcopy(r['events'][1]);e.update(kind='write',address=0x430000,bus_address=0x430000,value=REGISTRY[0])
            r['events'].insert(2,e)
        self.reject(mutate)

    def test_float_cpu_byte_alias_refuses(self):
        self.reject(lambda r,*_:r['events'][0]['cpu'].__setitem__('a',float(r['events'][0]['cpu']['a'])))

    def test_float_final_wram_byte_refuses(self):
        self.reject(lambda r,*_:r['changes'][0].__setitem__(1,float(r['changes'][0][1])))

    def test_extra_unexplained_frame_diff_refuses(self):
        self.reject(lambda r,c,*_:r['changes'].append([0x7E0000+c['cpu']['sp']-20,0]))

    def test_missing_frame_diff_refuses(self):self.reject(lambda r,*_:r['changes'].pop())

    def test_hidden_phase_key_substitution_refuses(self):
        def mutate(r,*_):r['events'][0]['timing']['ppu.nmiScanline']=r['events'][0]['timing'].pop('ppu.scanline')
        self.reject(mutate)

    def test_fabricated_latch_edge_refuses(self):
        self.reject(lambda r,*_:r['preparation']['latch_rise']['before'].__setitem__('latch',True))

    def test_pending_dma_refuses(self):
        self.reject(lambda r,*_:r['events'][-1]['flags'].__setitem__('dmaController.dmaPending',True))

    def test_request_clock_change_refuses(self):
        self.reject(lambda r,*_:self.event(r,'request-after')['timing'].__setitem__('cpu.cycleCount',999))

    def test_handler_register_change_refuses(self):
        self.reject(lambda r,*_:next(e for e in r['events'] if e['kind']=='exec' and e['address']==0x8088)['cpu'].__setitem__('x',0))

    def test_projection_rejection_is_not_swallowed(self):
        with patch.object(tool.v3,'validate_record',side_effect=tool.v3.ConformanceError('independent projection refusal')):
            with self.assertRaises(tool.v3.ConformanceError):
                tool.validate_record(*specimen(),payload=PAYLOAD,registry=REGISTRY)


def site_specimen():
    """Original opcode/site geometry, not the complete assembled helper."""
    code=bytearray([0xEA]*577)
    for offset in (0x43,0x215,0x226):code[offset]=0x1B
    for offset in (0x19,0x21A,0x22D):code[offset]=0x28
    code[0xEE:0xF1]=bytes.fromhex('203202')
    for offset,tail in ((0x1E,0x8100),(0x21B,0x8110),(0x22E,0x8120)):
        code[offset:offset+4]=bytes((0x5C,tail&255,tail>>8,0))
    return bytes(code)


class ImmutableMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases=tool.build_cases(PAYLOAD,REGISTRY)

    def test_exact_152_unique_cases_are_deterministic(self):
        self.assertEqual(len(self.cases),152)
        self.assertEqual(len({c['name'] for c in self.cases}),152)
        self.assertEqual(self.cases,tool.build_cases(PAYLOAD,REGISTRY))

    def test_two_safe_stacks_have_equal_counts(self):
        self.assertEqual(Counter(c['cpu']['sp'] for c in self.cases),{0x1FEF:76,0x06D8:76})
        self.assertTrue(all(c['cpu']['sp']>c['nmi_max_depth'] for c in self.cases))

    def test_exact_route_and_binding_counts(self):
        self.assertEqual(Counter(c['route'] for c in self.cases),{'success':128,'canonical':8,'refusal':16})
        self.assertEqual({c['selector'] for c in self.cases if c['route']=='success'},set(range(0x80,0x84)))

    def test_successes_cover_both_branches_and_four_statuses(self):
        rows=[c for c in self.cases if c['route']=='success']
        self.assertEqual({c['flag'] for c in rows},{0,0x40})
        self.assertEqual({c['cpu']['ps'] for c in rows},{0,0xC3,0x4C,0x8F})
        self.assertEqual({c['nmi_boundary'] for c in rows},set(tool.SUCCESS_BOUNDARIES))

    def test_refusals_distinguish_frame_allocation(self):
        rows=[c for c in self.cases if c['route']=='refusal']
        self.assertEqual({c['selector'] for c in rows},{0x84,0x90})
        self.assertTrue(all(c['frame_allocated']==(c['selector']==0x84) for c in rows))
        self.assertTrue(all(not c['expected_writes'] for c in rows))

    def test_canonical_route_reads_no_registry(self):
        rows=[c for c in self.cases if c['route']=='canonical']
        self.assertTrue(all(c['selector']==0x7F and not c['expected_rom_reads'] for c in rows))

    def test_no_old_wram_source_bank_or_production_selector_binding(self):
        self.assertEqual({a>>16 for c in self.cases for a,_ in c['expected_rom_reads']},{0x42,0x43})
        self.assertTrue(all(len(c['patches'])==4 and all(a>>16==0x7E for a,_ in c['patches']) for c in self.cases))

    def test_empty_selected_masks_still_reach_countbits(self):
        for selector,flag in ((0x82,0x40),(0x83,0)):
            rows=[c for c in self.cases if c['selector']==selector and c['flag']==flag]
            self.assertTrue(rows and all(c['countbits_reached'] for c in rows))

    def test_pilot_is_two_original_deepest_cases(self):
        rows=tool.build_cases(PAYLOAD,REGISTRY,'pilot')
        self.assertEqual(len(rows),2)
        self.assertTrue(all(c['selector']==0x80 and c['flag']==0 and c['cpu']['ps']==0 and c['nmi_max_depth']==59 for c in rows))

    def test_unknown_scope_refuses(self):
        with self.assertRaises(tool.ConformanceError):tool.build_cases(PAYLOAD,REGISTRY,'all-inputs')

    def test_mutated_original_component_refuses(self):
        for payload,registry in ((bytes([PAYLOAD[0]^1])+PAYLOAD[1:],REGISTRY),(PAYLOAD,REGISTRY[:-1]+bytes([REGISTRY[-1]^1]))):
            with self.assertRaises(ValueError):tool.build_cases(payload,registry)

    def sites(self,cases,code):
        with patch.object(tool.v3,'HELPER_SHA256',tool.sha(code)):tool.validate_sites(cases,code)

    def test_all_declared_site_continuations_match_original_geometry(self):self.sites(self.cases,site_specimen())

    def test_real_helper_hash_gate_refuses_opcode_specimen(self):
        with self.assertRaises(tool.ConformanceError):tool.validate_sites(self.cases,site_specimen())

    def test_old_wram_jsr_continuation_refuses(self):
        rows=copy.deepcopy(tool.build_cases(PAYLOAD,REGISTRY,'pilot'));rows[0]['nmi_resume']=0x7F8232
        with self.assertRaises(tool.ConformanceError):self.sites(rows,site_specimen())

    def test_old_wram_jsr_operand_refuses(self):
        code=bytearray(site_specimen());code[0xF0]=0x82
        with self.assertRaises(tool.ConformanceError):self.sites(self.cases,bytes(code))

    def test_wrong_tail_bank_refuses(self):
        rows=copy.deepcopy(self.cases)
        next(c for c in rows if c['nmi_boundary']=='success-jml-tail')['nmi_resume']=0x7F8110
        with self.assertRaises(tool.ConformanceError):self.sites(rows,site_specimen())

    def test_stack_boundary_without_interrupt_reserve_refuses(self):
        rows=copy.deepcopy(self.cases);rows[0]['cpu']['sp']=0x34
        with self.assertRaises(tool.ConformanceError):self.sites(rows,site_specimen())

    def test_wrong_combined_depth_refuses(self):
        rows=copy.deepcopy(self.cases);rows[0]['nmi_max_depth']=0
        with self.assertRaises(tool.ConformanceError):self.sites(rows,site_specimen())

    def test_archive_requires_complete_exact_frozen_inventory(self):
        guarded=dict.fromkeys(tool.ARCHIVE_KEYS,'a'*64)
        tool.require_archive_hashes(guarded,guarded)
        for changed in ({k:v for k,v in guarded.items() if k!='nmi_tests'},dict(guarded,extra='a'*64),dict(guarded,nmi_tests='b'*64)):
            with self.assertRaises(tool.ConformanceError):tool.require_archive_hashes(changed,guarded)


class CalibratedPhaseTests(unittest.TestCase):
    """Original scheduling/phase metadata; no native fixture is manufactured."""
    def phase(self,preblank=False):
        original,case,_,_=specimen();base=original['events'][0]
        points=[(200,1,8),(225,2,12),(228,2,0),(228,2,80),(229,2,0)] if preblank else [
            (226,1,8),(227,1,0),(228,1,0),(228,1,80),(0,1,40)]
        events=[]
        for scan,frame,hclock in points:
            e=copy.deepcopy(base)
            position=frame*262+(scan-225)%262
            clock=20+(position-262)*1364+hclock-12
            e['timing'].update({'ppu.scanline':scan,'ppu.frameCount':frame,'frameCount':frame,
                'memoryManager.masterClock':clock,'masterClock':clock&0xFFFFFFFF,
                'memoryManager.hClock':hclock,'cpu.cycleCount':clock//8})
            e['flags']['internalRegisters.nmiFlag']=scan>=225;e['latch_peek']=128 if scan>=225 else 0
            events.append(e)
        case.update(nmi_start_scanline=200 if preblank else 226,nmi_rise_scanline=225)
        return events,case,original['preparation']

    def check(self,events,case,prep):tool.validate_phase(events,case,prep,2,3)

    def test_disabled_post_rti_continuation_may_wrap_raster(self):self.check(*self.phase())
    def test_preblank_setup_observes_active_natural_latch_edge(self):self.check(*self.phase(True))
    def test_start_phase_must_equal_declared_calibration(self):
        e,c,p=self.phase();c['nmi_start_scanline']=227
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_missing_phase_plan_refuses(self):
        e,c,p=self.phase();del c['nmi_start_scanline']
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_actual_request_to_rti_cannot_leave_vblank(self):
        e,c,p=self.phase();e[3]=copy.deepcopy(e[4])
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_latch_and_peek_must_agree_after_wrap(self):
        e,c,p=self.phase();e[-1]['latch_peek']=128
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_raster_movement_cannot_outrun_full_clock(self):
        e,c,p=self.phase();e[-1]['timing']['memoryManager.masterClock']-=1000
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_preparation_latch_bracket_obeys_raster_clock_interval(self):
        e,c,p=self.phase();p['latch_rise']['before']['hclock']=10
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_short_line_interval_is_allowed_without_fixed1364_claim(self):
        e,c,p=self.phase();e[-1]['timing']['memoryManager.masterClock']-=4
        self.check(e,c,p)
    def test_frame_count_origin_cannot_move_to_raster_zero(self):
        e,c,p=self.phase();e[-1]['timing']['ppu.frameCount']+=1
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_active_preblank_edge_is_required(self):
        e,c,p=self.phase(True);e[0]['flags']['internalRegisters.nmiFlag']=True;e[0]['latch_peek']=128
        with self.assertRaises(tool.ConformanceError):self.check(e,c,p)
    def test_post_rti_budget_is_enforced(self):
        with patch.object(tool,'POST_RTI_CLOCK_LIMIT',10):
            with self.assertRaises(tool.ConformanceError):self.check(*self.phase())

    def schedule(self):
        cases=tool.build_cases(PAYLOAD,REGISTRY,'pilot')
        rows=[{'selector':c['selector'],'flag':c['flag'],'sp':c['cpu']['sp'],
            'boundary':c['nmi_boundary'],'trigger':c['nmi_trigger'],'elapsed_master_clocks':2496,
            'start_scanline':226,'observed_rise_scanline':225,'group_name':'original group '+str(c['cpu']['sp'])} for c in cases]
        return cases,rows
    def test_fixed_schedule_is_applied_without_editing_original_cases(self):
        c,r=self.schedule();out=tool.apply_calibration(c,r)
        self.assertTrue(all(x['nmi_start_scanline']==226 for x in out));self.assertNotIn('nmi_start_scanline',c[0])
    def test_schedule_formula_and_trigger_are_bound(self):
        for key,value in (('start_scanline',225),('trigger',0x7F80EE),('elapsed_master_clocks',5000)):
            c,r=self.schedule();r[0][key]=value
            with self.subTest(key=key):
                with self.assertRaises(tool.ConformanceError):tool.apply_calibration(c,r)
    def test_schedule_coverage_duplicates_types_and_unknown_fields_refuse(self):
        for mutation in ('missing','duplicate','float','unknown'):
            c,r=self.schedule()
            if mutation=='missing':r.pop()
            elif mutation=='duplicate':r.append(copy.deepcopy(r[0]))
            elif mutation=='float':r[0]['sp']=float(r[0]['sp'])
            else:r[0]['hidden_phase']=225
            with self.subTest(mutation=mutation):
                with self.assertRaises(tool.ConformanceError):tool.apply_calibration(c,r)

    def housekeeping(self):
        e,_,_=self.phase();rows=[copy.deepcopy(e[0]) for _ in range(3)]
        for row,h in zip(rows,(12,26,34)):
            row['timing'].update({'ppu.scanline':0,'memoryManager.hClock':h,'memoryManager.masterClock':50000+h})
        rows[1]['flags'].update({'dmaController.needToProcess':True,'dmaController.hdmaInitPending':True})
        return rows
    def test_zero_channel_init_may_set_then_clear_without_transfer(self):
        rows=self.housekeeping();self.assertEqual(tool.validate_zero_channel_init(rows,10,20),[1])
        rows[1]['flags']['dmaController.dmaStartDelay']=True
        self.assertEqual(tool.validate_zero_channel_init(rows,10,20),[1])
    def test_housekeeping_requires_no_channels_transfer_or_lock(self):
        for key in ('dmaController.hdmaChannels','dmaController.hdmaPending','dmaController.dmaPending','cpu.irqLock'):
            rows=self.housekeeping();rows[1]['flags'][key]=1 if key.endswith('hdmaChannels') else True
            with self.subTest(key=key):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)
    def test_housekeeping_is_forbidden_during_actual_nmi(self):
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(self.housekeeping(),0,2)
    def test_housekeeping_requires_line_zero_early_clock(self):
        for key,value in (('ppu.scanline',1),('memoryManager.hClock',65),('memoryManager.hClock',11)):
            rows=self.housekeeping();rows[1]['timing'][key]=value
            with self.subTest(key=key,value=value):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)
    def test_housekeeping_requires_correct_pending_or(self):
        rows=self.housekeeping();rows[1]['flags']['dmaController.needToProcess']=False
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)
    def test_housekeeping_cannot_restart_in_the_same_raster_window(self):
        rows=self.housekeeping();second=copy.deepcopy(rows[1]);clear=copy.deepcopy(rows[2])
        second['timing'].update({'memoryManager.hClock':42,'memoryManager.masterClock':50042})
        clear['timing'].update({'memoryManager.hClock':50,'memoryManager.masterClock':50050})
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows+[second,clear],10,20)
    def test_housekeeping_delay_cannot_restart_while_pending(self):
        rows=self.housekeeping();again=copy.deepcopy(rows[1])
        again['flags']['dmaController.dmaStartDelay']=True
        again['timing'].update({'memoryManager.hClock':30,'memoryManager.masterClock':50030})
        rows.insert(2,again)
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)
    def test_housekeeping_needs_bounded_observed_clear(self):
        rows=self.housekeeping();rows[-1]['timing']['memoryManager.masterClock']+=40
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(self.housekeeping()[:2],10,20)

    def publication_housekeeping(self):
        """Original short instruction/metadata specimen, no recorded trace bytes."""
        seed=self.housekeeping()[0]
        rows=[copy.deepcopy(seed) for _ in range(5)]
        cpu={'a':0x5A17,'x':0x28,'y':1,'d':0,'dbr':0x42,'sp':0x1FBD,'ps':0,'k':0x41,'pc':0x01DF,'emulationMode':False}
        for i,(row,kind,address,value,clock,cycles) in enumerate(zip(rows,
            ('exec','write','write','exec','read'),(0x4101DF,0x7E5DE5,0x7E5DE6,0x4101E3,0x7E1FC2),
            (0x9F,0x17,0x5A,0xA3,0x42),(49974,50014,50022,50022,50052),(100,105,106,106,110))):
            row.update(kind=kind,address=address,value=value,exec_index=10 if i<3 else 11,
                cpu={**cpu,'pc':0x01DF if i==0 else 0x01E5 if i==4 else 0x01E3})
            if kind in ('read','write'):row['bus_address']=address if kind=='write' else 0x1FC2
            row['timing'].update({'memoryManager.masterClock':clock,'cpu.cycleCount':cycles,
                'ppu.scanline':261 if i==0 else 0,'memoryManager.hClock':1338 if i==0 else clock-50000})
            row['flags'].update({'dmaController.hdmaInitPending':i in (1,2,3),
                'dmaController.needToProcess':i in (1,2,3),'dmaController.dmaStartDelay':i==1})
        return rows

    def test_exact_original_publication_clear_sampling_gap_accepts(self):
        self.assertEqual(tool.validate_zero_channel_init(self.publication_housekeeping(),10,20),[1,2,3])

    def test_longer_sample_gap_is_not_general_timeout_extension(self):
        rows=self.housekeeping();rows[-1]['timing']['memoryManager.masterClock']=rows[1]['timing']['memoryManager.masterClock']+38
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_wrong_original_pc_or_opcode_refuses(self):
        for index,key,value in ((0,'address',0x7F81DF),(3,'address',0x4101E4),(0,'value',0x8F),(3,'value',0xA5)):
            rows=self.publication_housekeeping();rows[index][key]=value
            with self.subTest(index=index,key=key):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_missing_or_extra_event_refuses(self):
        for change in ('missing','extra'):
            rows=self.publication_housekeeping()
            if change=='missing':del rows[2]
            else:rows.insert(3,copy.deepcopy(rows[2]))
            with self.subTest(change=change):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_wrong_clock_or_cycle_interval_refuses(self):
        for index,key in ((2,'memoryManager.masterClock'),(4,'cpu.cycleCount')):
            rows=self.publication_housekeeping();rows[index]['timing'][key]+=1
            with self.subTest(key=key):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_wrong_physical_address_or_value_refuses(self):
        for index,key,value in ((1,'address',0x7E4000),(2,'value',0x5B),(4,'bus_address',0x1FC3),(4,'address',0x7E1FC3)):
            rows=self.publication_housekeeping();rows[index][key]=value
            with self.subTest(index=index,key=key):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_wrong_cpu_or_ordinal_ownership_refuses(self):
        rows=self.publication_housekeeping();rows[3]['cpu']['sp']-=1
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)
        rows=self.publication_housekeeping();rows[4]['exec_index']-=1
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_requires_delay_true_then_false(self):
        rows=self.publication_housekeeping();rows[1]['flags']['dmaController.dmaStartDelay']=False
        with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)

    def test_publication_gap_clear_cannot_leave_line_zero_window(self):
        for key,value in (('ppu.scanline',1),('memoryManager.hClock',65)):
            rows=self.publication_housekeeping();rows[-1]['timing'][key]=value
            with self.subTest(key=key):
                with self.assertRaises(tool.ConformanceError):tool.validate_zero_channel_init(rows,10,20)


if __name__=='__main__':unittest.main()
