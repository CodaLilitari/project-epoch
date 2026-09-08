"""Adversarial synthetic metadata fixtures; no ROM, SRAM, state, or trace data."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_package_resolver_alternate_v1 as v


def fixture():
    bank=bytearray(65536)
    bank[0x1200:0x120A]=bytes((0,1,0xA0,0,0,0x40,0x20,0x40,0x40,0x40))
    source=v.adapter.make_package_source(selector=0x80,bank=0x42,root_offset=0x1200,
        allocation_name='ORIGINAL_ALTERNATE_TEST',source_kind='synthetic-test')
    model=v.adapter.simulate_descriptor_install(bytes(bank),source,a0b3=0x40)
    records=[]
    saved=[0x2A,0x43,0xAF,0x40,0x12,0x34,0x56,0x78,0x9A,0xBC,0xDE,0xF0]
    def add(kind,*,delta=0,**changes):
        address=v.EXEC_SITES.get(kind,0)
        w={key:0 for key in v.WRAM_KEYS}
        w.update({'0100':0xD1,'0101':1,'2980':6,'2981':4,'2982':3,'AEFF':6,'AF00':4,'AF01':3,
                  'AE91':0,'AE92':2,'AE93':0x37,'AE94':0x40,'9877':0x37,'A0B3':0x40,
                  'B1F6':0x80,'B1F7':1,'B1FD':3})
        c={'a':0,'x':0,'y':0,'d':0,'dbr':0x7E,'sp':0x900+delta,'ps':0x20,'k':address>>16,'pc':address&65535,'emulationMode':False}
        r={'kind':kind,'address':address,'value':-1,'frame':100,'cpu':c,'stack':saved[delta:]+[0]*delta,
           'wram':w,'timing':{},'target_type':0x80,'selector_word':0x37,'branch_word':0x40,
           'mask0_word':0,'mask1_word':0,'root_word':0}
        r.update(changes); records.append(r); return r
    add('baseline',frame=0)
    enemy=add('branch-producer-complete'); enemy['wram']['AE91']=3
    # Earlier enemy completion cannot satisfy the following player's checks.
    for kind in ('caller-package-latch','caller-effect-latch'):
        r=add(kind,delta=4); r['wram']['AE91']=3; r['wram']['9876']=1
    for kind in ('black-hole-entry','black-hole-type-test','black-hole-survivor','black-hole-mask-advance','exhausted-mask-alternate-store'):
        r=add(kind); r['wram']['AE93']=0; r['wram']['AE94']=0
        if kind in {'black-hole-type-test','black-hole-survivor'}:
            r['cpu']['a']=0x80; r['cpu']['x']=0x180; r['wram']['AE96']=0x10
        if kind=='exhausted-mask-alternate-store': r['cpu']['a']=0x40
    flag=add('latch-write',address=0x7EAE94,value=0x40)
    flag['cpu']['k']=0xC1; flag['cpu']['pc']=0xF1C3; flag['wram']['AE93']=0; flag['wram']['AE94']=0
    add('branch-producer-complete')
    entry=add('resolver-entry'); entry['cpu']['ps']=0x80
    continuation=add('canonical-continuation'); continuation['cpu']['ps']=0; continuation['cpu']['a']=0x6E
    for address,value,next_pc in v.publication_sequence(model):
        r=add('publication-write',address=address,value=value)
        r['cpu']['ps']=0; r['cpu']['k']=next_pc>>16; r['cpu']['pc']=next_pc&65535
    tail=add('resolver-tail',branch_word=0,mask1_word=model.dp82_word_final,root_word=model.descriptor_root_word)
    tail['wram']['A0B3']=0; tail['wram']['0082']=model.dp82_word_final&255
    tail['cpu'].update(a=model.accumulator_word_final,x=model.x_final,y=model.y_final,ps=0x23)
    add('common-loader-entry'); add('common-loader-rts'); add('dispatcher-rts',delta=2); add('caller-resume',delta=4)
    add('sync-command-increment',delta=4)
    sync=add('latch-write',address=0x7E9876,value=1,delta=4)
    sync['cpu']['k']=0xC1; sync['cpu']['pc']=0x4D03
    package=add('caller-package-latch',delta=4); package['wram']['9876']=1
    effect=add('caller-effect-latch',delta=4); effect['wram']['9876']=1
    cleanup=add('latch-write',address=0x7EAE94,value=0); cleanup['wram']['AE93']=0
    add('terminal',frame=4400)
    # Cross the generic 32-bit master clock boundary with a monotonic full clock.
    for i,r in enumerate(records):
        full=2**32-1000+i*100
        r['timing']={'masterClock':full&0xFFFFFFFF,'memoryManager.masterClock':full,'cpu.cycleCount':1000+i*10,
                     'frameCount':100,'ppu.frameCount':100,'ppu.scanline':0,'memoryManager.hClock':0,'clockRate':21477270}
    return {'schema':v.SCHEMA,'error':None,'records':records},model


class AlternateValidatorTests(unittest.TestCase):
    def setUp(self): self.trace,self.model=fixture()

    def record(self,kind):
        return next(r for r in self.trace['records'] if r['kind']==kind)

    def rejected(self):
        with self.assertRaises(v.ObservationError): v.summarize(self.trace,self.model)

    def test_original_fixture_and_clock_rollover(self):
        result=v.summarize(self.trace,self.model)
        self.assertEqual(result['publication_byte_count'],12)
        self.assertEqual(result['published_owner_slots'],[0,2])
        self.assertEqual(result['branch_word_at_entry'],0x40)
        self.assertTrue(result['boss_immunity_bypasses_rng'])
        self.assertFalse(result['preflight_cancellation_tested'])

    def test_unknown_record_key(self):
        self.record('baseline')['unexpected']=0; self.rejected()

    def test_boolean_is_not_cpu_byte(self):
        self.record('resolver-entry')['cpu']['a']=True; self.rejected()

    def test_native_mode_is_boolean(self):
        self.record('baseline')['cpu']['emulationMode']=0; self.rejected()

    def test_twelve_stack_bytes_required(self):
        self.record('resolver-entry')['stack'].pop(); self.rejected()

    def test_known_kind_wrong_address(self):
        r=self.record('resolver-entry'); r['address']=0xC14616; r['cpu']['pc']=0x4616; self.rejected()

    def test_exec_pbr_pc_mismatch(self):
        self.record('black-hole-type-test')['cpu']['k']=0xC0; self.rejected()

    def test_wrong_generic_clock_low_word(self):
        self.record('resolver-entry')['timing']['masterClock']+=1; self.rejected()

    def test_backwards_monotonic_counters(self):
        for key in ('memoryManager.masterClock','cpu.cycleCount','ppu.frameCount'):
            with self.subTest(key=key):
                self.trace,self.model=fixture(); r=self.record('resolver-entry'); r['timing'][key]=0
                if key=='memoryManager.masterClock': r['timing']['masterClock']=0
                if key=='ppu.frameCount': r['timing']['frameCount']=0
                self.rejected()

    def test_unexpected_timing_key(self):
        self.record('baseline')['timing']['cpu.masterClock']=1; self.rejected()

    def test_primary_branch_is_not_alternate(self):
        r=self.record('resolver-entry'); r['branch_word']=0; r['wram']['A0B3']=0; self.rejected()

    def test_different_logical_character(self):
        self.record('resolver-entry')['wram']['AEFF']=0; self.rejected()

    def test_boss_bit_required(self):
        r=self.record('black-hole-type-test'); r['target_type']=4; r['cpu']['a']=4; self.rejected()

    def test_boss_path_cannot_enter_rng(self):
        r=self.record('black-hole-survivor'); r['kind']='black-hole-rng-path'; r['address']=v.EXEC_SITES[r['kind']]; r['cpu']['pc']=r['address']&65535; self.rejected()

    def test_target_slot_base_must_agree(self):
        self.record('black-hole-type-test')['wram']['B1FD']=4; self.rejected()

    def test_exhaustion_requires_both_masks_zero(self):
        self.record('black-hole-mask-advance')['wram']['AE99']=1; self.rejected()

    def test_pre_store_does_not_count_as_actual_write(self):
        self.trace['records']=[r for r in self.trace['records'] if not(r['kind']=='latch-write' and r['address']==0x7EAE94 and r['value']==0x40)]
        self.rejected()

    def test_actual_flag_write_requires_canonical_next_pc(self):
        r=next(r for r in self.trace['records'] if r['kind']=='latch-write' and r['value']==0x40)
        r['cpu']['pc']=0xF1C0; self.rejected()

    def test_prewrite_snapshot_is_not_readback(self):
        r=next(r for r in self.trace['records'] if r['kind']=='latch-write' and r['value']==0x40)
        r['wram']['AE94']=0x40; self.rejected()

    def test_postwrite_readback_required(self):
        r=[r for r in self.trace['records'] if r['kind']=='branch-producer-complete'][-1]
        r['wram']['AE94']=0; self.rejected()

    def test_publication_values_and_order(self):
        r=self.record('publication-write'); r['value']^=1; self.rejected()
        self.trace,self.model=fixture()
        indices=[i for i,r in enumerate(self.trace['records']) if r['kind']=='publication-write']
        a,b=indices[0:2]
        self.trace['records'][a],self.trace['records'][b]=self.trace['records'][b],self.trace['records'][a]
        # Keep timestamps ordered so this specifically tests ordered publications.
        self.trace['records'][a]['timing'],self.trace['records'][b]['timing']=self.trace['records'][b]['timing'],self.trace['records'][a]['timing']
        self.rejected()

    def test_publication_width_required(self):
        self.record('publication-write')['cpu']['ps']=0x20; self.rejected()

    def test_tail_stack_and_flags(self):
        self.record('resolver-tail')['stack'][8]^=1; self.rejected()
        self.trace,self.model=fixture(); self.record('resolver-tail')['cpu']['ps']^=1; self.rejected()

    def test_return_chain_stack_consumption(self):
        self.record('dispatcher-rts')['stack'][0]^=1; self.rejected()

    def test_earlier_enemy_completion_cannot_satisfy_pc(self):
        self.trace['records']=[r for r in self.trace['records'] if not(r['kind']=='caller-effect-latch' and r['wram']['AE91']==0)]
        self.rejected()

    def test_identity_change_ends_completion_scope(self):
        self.record('sync-command-increment')['wram']['AE93']=0; self.rejected()

    def test_identity_change_before_tail_fails_closed(self):
        self.record('canonical-continuation')['wram']['AE93']=0; self.rejected()

    def test_sync_exec_without_actual_write_rejected(self):
        self.trace['records']=[r for r in self.trace['records'] if not(r['kind']=='latch-write' and r['address']==0x7E9876)]
        self.rejected()

    def test_later_enemy_completion_cannot_satisfy_pc(self):
        effect=next(r for r in self.trace['records'] if r['kind']=='caller-effect-latch' and r['wram']['AE91']==0)
        effect['wram']['AE91']=3; self.rejected()

    def test_completion_and_sync_require_canonical_data_access_abi(self):
        for kind in ('sync-command-increment','sync-write','caller-package-latch','caller-effect-latch'):
            for key,value in (('d',0x1234),('dbr',0x41),('ps',0x00),('ps',0x30)):
                with self.subTest(kind=kind,key=key,value=value):
                    self.trace,self.model=fixture()
                    if kind=='sync-write':
                        r=next(r for r in self.trace['records'] if r['kind']=='latch-write' and r['address']==0x7E9876)
                    else:
                        r=next(r for r in self.trace['records'] if r['kind']==kind and r['wram']['AE91']==0)
                    r['cpu'][key]=value; self.rejected()

    def test_refuses_truncated_or_modified_canonical_rom(self):
        with self.assertRaises(v.adapter.PackageBankAdapterError): v.canonical_model(bytes(100))
        with self.assertRaises(v.adapter.PackageBankAdapterError): v.canonical_model(bytes(0x400000))


if __name__=='__main__': unittest.main()
