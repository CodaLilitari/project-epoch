"""Adversarial tests for the read-only ISR/resolver evidence collector.

Fixtures are original synthetic metadata, not copied emulator or game data.
They exercise evidence attribution and rejection rather than game behavior.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_package_resolver_context_v1 as probe


def record(kind,address=0,*,poll=100,context_id=0,context_kind='main',depth=0,
           action=False,resolver=False,value=-1,pc=None,latch=0,ps=0x22):
    bus_pc=address if kind in probe.EXEC_SITES or kind.startswith('interrupt-') else (pc or 0xC10084)
    wram={key:0 for key in probe.WRAM_KEYS}
    wram.update({'9877':8,'AE91':0,'AE92':2,'AE93':8,'2980':0,'2981':1,'2982':2,'5D9B':latch})
    if kind=='interrupt-entry': ps=0x26
    return {'kind':kind,'address':address,'value':value,'poll':poll,
            'cpu':{'a':0,'x':16,'y':2,'d':0,'dbr':0x7E,'sp':0x06D8,'ps':ps,
                   'k':bus_pc>>16,'pc':bus_pc&65535,'emulationMode':False},
            'stack':[0x22,0x84,0,0xC1,0,0,0,0,0,0,0,0],
            'trampolines':[0x5C,0x7C,0xE7,0xD1,0x5C,0x97,0xFE,0xD1],
            'wram':wram,'timing':{'masterClock':0,'memoryManager.masterClock':0,
                 'cpu.cycleCount':0,'frameCount':6000,'ppu.frameCount':6000,
                 'ppu.scanline':119,'memoryManager.hClock':100,'clockRate':21477270},
            'context_id':context_id,'context_kind':context_kind,'context_depth':depth,
            'resolver_active':resolver,'action_active':action,
            'selector_word':8,'branch_word':0,'mask0_word':0,'mask1_word':0,'root_word':0}


def stamp(trace,base=100000):
    for i,r in enumerate(trace['records']):
        clock=base+i*10
        r['timing']['memoryManager.masterClock']=clock
        r['timing']['masterClock']=clock&0xFFFFFFFF
        r['timing']['cpu.cycleCount']=1000+i*2
    return trace


def fixture():
    irq=dict(context_id=1,context_kind='battle-irq',depth=1,poll=10)
    nmi=dict(context_id=2,context_kind='normal-nmi',depth=1,poll=150,action=True)
    r=[record('baseline',poll=0),
       record('interrupt-entry',0xD1FE97,**irq),
       record('interrupt-rti',0xD1FEF3,ps=0x05,**irq),
       record('branch-producer-complete',0xC1409C),
       record('resolver-entry',0xC14612,action=True,resolver=True,ps=0x80),
       record('temporary-write',0x81,action=True,resolver=True,value=0,pc=0xC14629),
       record('resolver-tail',0xC1467F,action=True,resolver=True,ps=0x23),
       record('interrupt-entry',0xD1E77C,latch=1,**nmi),
       record('nmi-effect-latch-read',0xCD160E,latch=1,**nmi),
       record('nmi-effect-latch-clear',0xCD164D,latch=1,**nmi),
       record('latch-or-flag-write',0x7E5D9B,value=0,pc=0xCD1650,latch=1,**nmi),
       record('interrupt-rti',0xD1E898,ps=0x05,**nmi),
       record('caller-effect-latch',0xC140E7,poll=200,action=True),
       record('branch-producer-complete',0xC1409C,poll=300),
       record('terminal',poll=1200)]
    return stamp({'schema':probe.SCHEMA,'error':None,'records':r})


class ContextEvidenceTests(unittest.TestCase):
    def reject(self,trace,pattern=None):
        if pattern:
            with self.assertRaisesRegex(probe.ObservationError,pattern): probe.summarize(trace)
        else:
            with self.assertRaises(probe.ObservationError): probe.summarize(trace)

    def test_complete_scoped_witness_and_pre_rti_flags(self):
        result=probe.summarize(fixture())
        self.assertEqual(result['paired_interrupt_count'],2)
        self.assertEqual(result['pc_scoped_scene_clear_count'],1)
        self.assertEqual(result['pc_invocation_windows'][0]['entry_to_pre_jump_tail_master_clocks'],20)
        self.assertEqual(result['pc_invocation_windows'][0]['direct_page_positive_control_count'],1)
        self.assertEqual(result['scene_clear_witnesses'][0]['caller_zero_read_index'],12)

    def test_32_bit_generic_clock_rollover_uses_full_clock(self):
        trace=stamp(fixture(),2**32-100)
        self.assertGreater(trace['records'][0]['timing']['masterClock'],trace['records'][-1]['timing']['masterClock'])
        self.assertEqual(probe.summarize(trace)['pc_scoped_scene_clear_count'],1)

    def test_generic_clock_cannot_lie_about_full_clock(self):
        t=fixture(); t['records'][7]['timing']['masterClock']+=1
        self.reject(t,'low 32 bits')

    def test_full_clock_reversal_refuses_even_if_low_word_matches(self):
        t=fixture(); t['records'][7]['timing']['memoryManager.masterClock']=10
        t['records'][7]['timing']['masterClock']=10
        self.reject(t,'backward')

    def test_poll_reversal_refuses(self):
        t=fixture(); t['records'][8]['poll']=149
        self.reject(t,'backward')

    def test_cpu_cycle_and_frame_reversal_refuse(self):
        for key in ('cpu.cycleCount','ppu.frameCount'):
            with self.subTest(key=key):
                t=fixture(); t['records'][8]['timing'][key]=1
                if key=='ppu.frameCount': t['records'][8]['timing']['frameCount']=1
                self.reject(t,'backward')

    def test_unknown_kind_refuses(self):
        t=fixture(); t['records'][5]['kind']='unregistered-reader'
        self.reject(t,'unknown event')

    def test_exec_cpu_pc_must_match_site(self):
        t=fixture(); t['records'][9]['cpu']['pc']+=1
        self.reject(t,'PBR/PC')

    def test_memory_cpu_pc_may_be_advanced(self):
        t=fixture()
        self.assertNotEqual(t['records'][10]['address'],(t['records'][10]['cpu']['k']<<16)|t['records'][10]['cpu']['pc'])
        probe.summarize(t)

    def test_wrong_interrupt_kind_or_return_address_refuses(self):
        t=fixture(); t['records'][11]['context_kind']='battle-irq'
        self.reject(t,'interrupt address')

    def test_return_to_wrong_context_id_refuses(self):
        t=fixture(); t['records'][11]['context_id']=1
        self.reject(t,'context mismatch')

    def test_context_kind_of_internal_event_must_match_owner(self):
        t=fixture(); t['records'][8]['context_kind']='battle-irq'
        self.reject(t,'context mismatch')

    def test_native_hardware_frame_changes_refuse(self):
        t=fixture(); t['records'][11]['stack'][0]^=1
        self.reject(t,'hardware return frame')

    def test_native_entry_p_transform_refuses_inconsistent_frame(self):
        t=fixture(); t['records'][7]['cpu']['ps']^=1
        self.reject(t,'entry P disagrees')

    def test_latched_irq_may_stack_i_set_after_sei(self):
        # A prior-cycle IRQ sample may outlive SEI's status update. This is a
        # feasible pipeline boundary, not a claim this checkpoint reaches it.
        t=fixture(); t['records'][1]['stack'][0]|=4
        t['records'][2]['stack'][0]|=4
        result=probe.summarize(t)
        self.assertEqual(result['irq_saved_interrupt_disable_counts'],{'1':1})

    def test_register_or_stack_pointer_damage_refuses(self):
        for key in ('a','x','y','d','dbr','sp'):
            with self.subTest(key=key):
                t=fixture(); t['records'][11]['cpu'][key]^=1
                self.reject(t,'preserved register')

    def test_missing_rti_is_not_discarded(self):
        t=fixture(); del t['records'][11]
        self.reject(t)

    def test_missing_scene_store_does_not_turn_exec_into_write_proof(self):
        t=fixture(); del t['records'][10]
        self.reject(t,'missing scene clear write')

    def test_nonzero_scene_store_refuses(self):
        t=fixture(); t['records'][10]['value']=1
        self.reject(t,'expected byte write')

    def test_scene_store_without_post_write_readback_refuses(self):
        t=fixture(); t['records'][11]['wram']['5D9B']=1
        self.reject(t,'post-write readback')

    def test_scene_clear_without_same_pc_caller_read_refuses(self):
        t=fixture(); del t['records'][12]
        self.reject(t,'same-PC caller')

    def test_next_action_read_cannot_complete_previous_pc_witness(self):
        t=fixture(); t['records'][12],t['records'][13]=t['records'][13],t['records'][12]
        t['records'][13]['poll']=300; t['records'][13]['action_active']=False
        stamp(t)
        self.reject(t,'same-PC caller')

    def test_missing_direct_page_callback_positive_control_refuses(self):
        t=fixture(); del t['records'][5]
        self.reject(t,'positive control')

    def test_unrelated_temporary_write_is_not_positive_control(self):
        t=fixture(); t['records'][5]['cpu']['pc']=0x462F
        self.reject(t,'positive control')

    def test_missing_tail_refuses(self):
        t=fixture(); del t['records'][6]
        self.reject(t)

    def test_boolean_numeric_fields_are_not_integers(self):
        for key in ('address','poll','value','selector_word'):
            with self.subTest(key=key):
                t=fixture(); t['records'][5][key]=False
                self.reject(t)

    def test_malformed_cpu_bytes_and_booleans_refuse(self):
        mutations=[('a',-1),('dbr',256),('emulationMode',0),('emulationMode',True)]
        for key,value in mutations:
            with self.subTest(key=key,value=value):
                t=fixture(); t['records'][5]['cpu'][key]=value
                self.reject(t)

    def test_exact_frame_stack_and_timing_shapes(self):
        for key in ('stack','trampolines'):
            with self.subTest(key=key):
                t=fixture(); t['records'][5][key].pop()
                self.reject(t,'length')
        t=fixture(); t['records'][5]['timing']['oldExtraClock']=0
        self.reject(t,'timing keys')

    def test_unhashable_context_kind_is_controlled_refusal(self):
        t=fixture(); t['records'][5]['context_kind']=[]
        self.reject(t,'unknown context')

    def test_nested_nmi_pair_preserves_outer_irq_identity(self):
        t=fixture()
        outer=copy.deepcopy(t['records'][1:3])
        for r in outer:
            r.update(context_id=2,poll=150,action_active=True)
        for r in t['records'][7:12]:
            r.update(context_id=3,context_depth=2)
            r['cpu']['sp']=0x06C0
            r['stack'][0]|=4
        t['records'].insert(12,outer[1])
        t['records'].insert(7,outer[0])
        stamp(t)
        result=probe.summarize(t)
        self.assertEqual(result['maximum_observed_context_depth'],2)
        self.assertEqual(result['paired_interrupt_count'],3)
        self.assertEqual(result['scene_clear_witnesses'][0]['context_id'],3)
        self.assertEqual(result['minimum_sampled_handler_sp'],0x06C0)


if __name__=='__main__': unittest.main()
