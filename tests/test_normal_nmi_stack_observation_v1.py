"""Original host specimens for exact NMI instruction/stack observation.

All tiny programs, CPU values and envelopes below are authored test data.
They are not canonical game instructions, emulator traces, or runtime proof.
"""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_normal_nmi_stack_observation_v1 as a


def cpu(pc=0xC18000,**updates):
    row={'a':0,'x':0,'y':0,'d':0,'dbr':126,'sp':0x600,'ps':0x24,
         'k':pc>>16,'pc':pc&65535,'emulationMode':False}
    row.update(updates);return row


def timing(clock=100):
    return {'masterClock':clock&0xFFFFFFFF,'memoryManager.masterClock':clock,
            'cpu.cycleCount':clock//6,'frameCount':1,'ppu.frameCount':1,
            'ppu.scanline':240,'memoryManager.hClock':100,'clockRate':21477270}


def read_program(memory):
    return lambda pc,n:bytes(memory.get(pc+i,0xEA) for i in range(n))


def bus(kind,address,value,sp=0x600,ordinal=1,clock=105):
    return {'kind':kind,'ordinal':ordinal,'address':address,'value':value,
            'cpu':cpu(sp=sp),'timing':timing(clock)}


def flow(raw,previous=None,following=None,events=None):
    p=copy.deepcopy(previous or cpu());at=a.pc_of(p)
    memory={at+i:v for i,v in enumerate(raw)};read=read_program(memory)
    q=copy.deepcopy(following or cpu(at+len(raw)))
    return ({'cpu':p,'code':list(read(at,4)),'timing':timing(100)},
            {'cpu':q,'timing':timing(112)},events or [],read)


def envelope(*,clock=100,write=None):
    # Original JMP/RTI program uses the required observer identities only.
    memory={a.ENTRY:0x4C,a.ENTRY+1:a.EXIT&255,a.ENTRY+2:(a.EXIT>>8)&255,a.EXIT:0x40}
    read=read_program(memory);hardware=[0x20,0,0x80,0xC1]
    before=[0]*0x20000;before[0x601:0x605]=hardware;after=before.copy()
    marker={'hardware':hardware,'trampolines':[92,124,231,209,92,151,254,209],'gate_bytes':[0]*12}
    first={'kind':'exec','ordinal':1,'cpu':cpu(a.ENTRY),'timing':timing(clock),
           'code':list(read(a.ENTRY,4)),'stack':before[0x601:0x60D]}
    last={'kind':'exec','ordinal':2,'cpu':cpu(a.EXIT),'timing':timing(clock+12),
          'code':list(read(a.EXIT,4)),'stack':before[0x601:0x60D]}
    events=[first,last]
    if write:
        addr,value=write;event=bus('write',addr,value,clock=clock+6)
        events.insert(1,event);physical=a.physical_wram(addr)
        if physical is not None:after[physical]=value
    return {'poll':379,'events':events,'wram_before':before,'wram_after':after,
            'entry_marker':copy.deepcopy(marker),'exit_marker':copy.deepcopy(marker)},read


def forged_stack_read_envelope():
    # Original PHA; PLA; LDA #0; JMP EXIT; RTI. The actual saved byte is zero.
    row,_=envelope();memory={a.ENTRY+i:v for i,v in enumerate((0x48,0x68,0xA9,0,0x4C,a.EXIT&255,(a.EXIT>>8)&255))}
    memory[a.EXIT]=0x40;read=read_program(memory);events=[]
    points=[(a.ENTRY,0x600,0),(a.ENTRY+1,0x5FF,0),(a.ENTRY+2,0x600,9),
            (a.ENTRY+4,0x600,0),(a.EXIT,0x600,0)]
    for ordinal,(pc,sp,acc) in enumerate(points,1):
        events.append({'kind':'exec','ordinal':ordinal,'cpu':cpu(pc,sp=sp,a=acc),
                       'timing':timing(100+ordinal*12),'code':list(read(pc,4)),
                       'stack':row['wram_before'][sp+1:sp+13]})
        if ordinal==1:events.append(bus('write',0x600,0,sp=0x600,ordinal=1,clock=118))
        if ordinal==2:events.append(bus('read',0x600,9,sp=0x600,ordinal=2,clock=130))
    row['events']=events;return row,read


def indirect_rom_envelope(*,forged=False):
    # Original JMP ($3000,X); JMP EXIT; RTI, with an immutable pointer.
    row,_=envelope();target=0xD19000
    memory={a.ENTRY:0x7C,a.ENTRY+1:0,a.ENTRY+2:0x30,
            0xD13000:0,0xD13001:0x90,target:0x4C,
            target+1:a.EXIT&255,target+2:(a.EXIT>>8)&255,a.EXIT:0x40}
    read=read_program(memory)
    row['events'][0]['code']=list(read(a.ENTRY,4))
    pointer=a.EXIT if forged else target
    reads=[bus('read',0xD13000+i,(pointer>>(8*i))&255,clock=103+i)
           for i in range(2)]
    row['events'][1:1]=reads
    if not forged:
        middle=copy.deepcopy(row['events'][-1]);middle['cpu']=cpu(target)
        middle['code']=list(read(target,4));row['events'].insert(-1,middle)
        row['events'][-1]['ordinal']=3;row['events'][-1]['timing']=timing(124)
    return row,read


def unverified_pointer_envelope(address=0x8000,*,forged=False):
    row,old_read=indirect_rom_envelope(forged=forged)
    code={a.ENTRY:0x6C,a.ENTRY+1:address&255,a.ENTRY+2:address>>8,
          0xC08000:0,0xC08001:0x90}
    def read(pc,n):return bytes(code.get(pc+i,old_read(pc+i,1)[0]) for i in range(n))
    row['events'][0]['code']=list(read(a.ENTRY,4))
    for e in row['events']:
        if e['kind']=='read':e['address']=address+(e['address']-0xD13000)
    return row,read


class Flow(unittest.TestCase):
    def test_sequential_nop(self):self.assertEqual(a.instruction_flow(*flow([0xEA]))['kind'],'sequential')
    def test_source_opcode_mismatch_refuses(self):
        p,q,e,read=flow([0xEA]);p['code'][0]=0x18
        with self.assertRaises(a.ObservationError):a.instruction_flow(p,q,e,read)
    def test_wrong_next_pc_refuses(self):
        args=flow([0xEA],following=cpu(0xC18002))
        with self.assertRaisesRegex(a.ObservationError,'PC transition'):a.instruction_flow(*args)
    def test_unowned_sp_change_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'SP transition'):a.instruction_flow(*flow([0xEA],following=cpu(0xC18001,sp=0x5FF)))
    def test_unowned_d_change_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'D change'):a.instruction_flow(*flow([0xEA],following=cpu(0xC18001,d=1)))
    def test_unowned_dbr_change_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'DBR change'):a.instruction_flow(*flow([0xEA],following=cpu(0xC18001,dbr=0)))
    def test_wrong_width_change_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'width'):a.instruction_flow(*flow([0xEA],following=cpu(0xC18001,ps=0x04)))
    def test_pha_byte_and_word_push_order(self):
        for ps,vals in ((0x24,[0x34]),(0x04,[0x12,0x34])):
            p=cpu(a=0x1234,ps=ps);q=cpu(0xC18001,a=0x1234,ps=ps,sp=0x600-len(vals))
            events=[bus('write',0x600-i,v,sp=0x600-i) for i,v in enumerate(vals)]
            self.assertEqual(a.instruction_flow(*flow([0x48],p,q,events))['push_bytes'],len(vals))
    def test_missing_stack_push_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'stack writes'):
            a.instruction_flow(*flow([0x48],cpu(a=4),cpu(0xC18001,a=4,sp=0x5FF)))
    def test_wrong_push_value_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'stack writes'):
            a.instruction_flow(*flow([0x48],cpu(a=4),cpu(0xC18001,a=4,sp=0x5FF),[bus('write',0x600,5)]))
    def test_push_cpu_sp_callback_timing_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'stack writes'):
            a.instruction_flow(*flow([0x48],cpu(a=4),cpu(0xC18001,a=4,sp=0x5FF),[bus('write',0x600,4,sp=0x5FF)]))
    def test_pla_byte_preserves_hidden_b(self):
        events=[bus('read',0x601,0x56,sp=0x601)]
        r=a.instruction_flow(*flow([0x68],cpu(a=0x1200),cpu(0xC18001,a=0x1256,sp=0x601),events))
        self.assertEqual(r['pull_bytes'],1)
    def test_pla_wrong_hidden_b_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'pull value'):
            a.instruction_flow(*flow([0x68],cpu(a=0x1200),cpu(0xC18001,a=0x56,sp=0x601),[bus('read',0x601,0x56,sp=0x601)]))
    def test_jsr_pushes_last_operand_address(self):
        e=[bus('write',0x600,0x80),bus('write',0x5FF,2,sp=0x5FF)]
        r=a.instruction_flow(*flow([0x20,0,0x90],following=cpu(0xC19000,sp=0x5FE),events=e))
        self.assertEqual((r['push_bytes'],r['next']),(2,0xC19000))
    def test_jsl_pushes_program_bank_then_word(self):
        e=[bus('write',0x600,0xC1),bus('write',0x5FF,0x80,sp=0x5FF),bus('write',0x5FE,3,sp=0x5FE)]
        self.assertEqual(a.instruction_flow(*flow([0x22,0,0x90,0xD1],following=cpu(0xD19000,sp=0x5FD),events=e))['push_bytes'],3)
    def test_indexed_jsr_uses_actual_program_bank_pointer_reads(self):
        e=[bus('read',0xC13002,0),bus('read',0xC13003,0x90),bus('write',0x600,0x80),bus('write',0x5FF,2,sp=0x5FF)]
        p,q,e,_=flow([0xFC,0,0x30],cpu(x=2),cpu(0xC19000,x=2,sp=0x5FE),e)
        read=read_program({0xC18000:0xFC,0xC18001:0,0xC18002:0x30,0xC13002:0,0xC13003:0x90})
        r=a.instruction_flow(p,q,e,read)
        self.assertEqual(r['kind'],'indexed-call')
    def test_duplicate_indirect_read_refuses(self):
        e=[bus('read',0xC13000,0),bus('read',0xC13000,0),bus('read',0xC13001,0x90)]
        with self.assertRaisesRegex(a.ObservationError,'ownership'):a.instruction_flow(*flow([0x7C,0,0x30],following=cpu(0xC19000),events=e))
    def test_absolute_indirect_reads_bank_zero(self):
        e=[bus('read',0x30,0),bus('read',0x31,0x90)]
        self.assertEqual(a.instruction_flow(*flow([0x6C,0x30,0],following=cpu(0xC19000),events=e))['kind'],'indirect-jump')
    def test_rts_uses_actual_stack_word_plus_one(self):
        e=[bus('read',0x5FF,2,sp=0x5FF),bus('read',0x600,0x80,sp=0x600)]
        self.assertEqual(a.instruction_flow(*flow([0x60],cpu(0xC19000,sp=0x5FE),cpu(0xC18003),e))['pull_bytes'],2)
    def test_rtl_uses_actual_stack_bank(self):
        e=[bus('read',0x5FE,3,sp=0x5FE),bus('read',0x5FF,0x80,sp=0x5FF),bus('read',0x600,0xC1)]
        self.assertEqual(a.instruction_flow(*flow([0x6B],cpu(0xD19000,sp=0x5FD),cpu(0xC18004),e))['next'],0xC18004)
    def test_branch_flag_is_from_preinstruction_cpu(self):
        self.assertEqual(a.instruction_flow(*flow([0xF0,2],cpu(ps=0x26),cpu(0xC18004,ps=0x26)))['next'],0xC18004)
        with self.assertRaisesRegex(a.ObservationError,'PC transition'):
            a.instruction_flow(*flow([0xF0,2],cpu(ps=0x24),cpu(0xC18004,ps=0x24)))
    def test_tcs_rebases_from_full_a(self):
        self.assertEqual(a.instruction_flow(*flow([0x1B],cpu(a=0x550),cpu(0xC18001,a=0x550,sp=0x550)))['kind'],'stack-rebase')
    def test_tcd_changes_only_owned_d(self):
        self.assertEqual(a.instruction_flow(*flow([0x5B],cpu(a=0x1234),cpu(0xC18001,a=0x1234,d=0x1234)))['sp_after'],0x600)
    def test_pld_reads_two_bytes_even_in_m8(self):
        e=[bus('read',0x601,0x34,sp=0x601),bus('read',0x602,0x12,sp=0x602)]
        self.assertEqual(a.instruction_flow(*flow([0x2B],following=cpu(0xC18001,d=0x1234,sp=0x602),events=e))['pull_bytes'],2)
    def test_plp_requires_exact_pulled_status(self):
        e=[bus('read',0x601,0x14,sp=0x601)]
        self.assertEqual(a.instruction_flow(*flow([0x28],following=cpu(0xC18001,ps=0x14,sp=0x601),events=e))['pull_bytes'],1)
    def test_block_move_repeats_until_initial_a_zero(self):
        for op,delta in ((0x54,1),(0x44,-1)):
            for acc in (0,1):
                p=cpu(a=acc,x=0x100,y=0x200,ps=4)
                q=cpu(0xC18003 if acc==0 else 0xC18000,a=(acc-1)&65535,x=0x100+delta,y=0x200+delta,ps=4,dbr=127)
                self.assertEqual(a.instruction_flow(*flow([op,127,126],p,q))['kind'],'block-move')
    def test_block_move_index8_wrap(self):
        p=cpu(a=0,x=255,y=255,ps=0x34);q=cpu(0xC18003,a=65535,x=0,y=0,ps=0x34)
        self.assertEqual(a.instruction_flow(*flow([0x54,126,126],p,q))['next'],0xC18003)
    def test_block_move_wrong_bank_refuses(self):
        p=cpu(a=0,x=1,y=1);q=cpu(0xC18003,a=65535,x=2,y=2)
        with self.assertRaisesRegex(a.ObservationError,'destination bank'):a.instruction_flow(*flow([0x54,127,126],p,q))
    def test_internal_rti_refuses(self):
        with self.assertRaisesRegex(a.ObservationError,'RTI'):a.instruction_flow(*flow([0x40]))
    def test_emulation_and_halt_refuse(self):
        with self.assertRaisesRegex(a.ObservationError,'native'):a.instruction_flow(*flow([0xEA],cpu(emulationMode=True)))
        for op in a.FORBIDDEN:
            with self.subTest(op=op),self.assertRaises(a.ObservationError):a.instruction_flow(*flow([op]))
    def test_cpu_scalar_aliases_refuse(self):
        for value in (False,0.,-1,65536):
            with self.subTest(value=value),self.assertRaises(a.ObservationError):a.instruction_flow(*flow([0xEA],cpu(a=value)))


class Envelope(unittest.TestCase):
    def setUp(self):self.row,self.read=envelope()
    def result(self):return a.validate_interval(self.row,self.read)
    def reject(self):
        with self.assertRaises(a.ObservationError):self.result()
    def test_original_positive_jmp_rti_envelope(self):
        r=self.result();self.assertEqual(r['executed_instructions'],1)
        self.assertEqual(r['minimum_recorded_sp'],0x600)
        self.assertEqual(r['bytes_below_interrupted_sp_including_existing_hardware_frame'],4)
        self.assertIs(r['native_hardware_pushes_captured'],False)
        self.assertIs(r['production_stack_headroom_proved'],False)
    def test_low32_rollover_keeps_full_time_monotonic(self):
        row,read=envelope(clock=2**32-6)
        self.assertEqual(a.validate_interval(row,read)['master_clocks'],12)
    def test_complete_wram_ledger_includes_high_bank_and_mirrors(self):
        for address in (0x7F1234,0x7E3000,0x800010):
            row,read=envelope(write=(address,9))
            self.assertEqual(a.validate_interval(row,read)['wram_changed_bytes'],1)
    def test_unrecorded_wram_change_refuses(self):self.row['wram_after'][0x1FFFF]=9;self.reject()
    def test_missing_write_readback_refuses(self):
        self.row,self.read=envelope(write=(0x7F1234,9));self.row['wram_after'][0x11234]=0;self.reject()
    def test_unchanged_hardware_write_still_requires_stack_ownership(self):
        self.row,self.read=envelope(write=(0x7E0601,0x20));self.reject()
    def test_stack_read_must_match_prior_wram_ledger(self):
        row,read=forged_stack_read_envelope()
        with self.assertRaises(a.ObservationError):a.validate_interval(row,read)
    def test_real_stack_read_has_a_positive_complete_envelope(self):
        row,read=forged_stack_read_envelope()
        next(e for e in row['events'] if e['kind']=='read')['value']=0
        next(e for e in row['events'] if e['kind']=='exec' and e['ordinal']==3)['cpu']['a']=0
        self.assertEqual(a.validate_interval(row,read)['executed_instructions'],4)
    def test_genuine_rom_pointer_complete_envelope(self):
        row,read=indirect_rom_envelope()
        self.assertEqual(a.validate_interval(row,read)['executed_instructions'],2)
    def test_forged_rom_pointer_cannot_shorten_complete_interval(self):
        row,read=indirect_rom_envelope(forged=True)
        with self.assertRaisesRegex(a.ObservationError,'immutable ROM read'):
            a.validate_interval(row,read)
    def test_unmapped_rom_mirror_and_hardware_pointer_domains_refuse(self):
        for address in (0x2000,0x4200,0x6000,0x8000,0xFFFE):
            for forged in (False,True):
                with self.subTest(address=address,forged=forged):
                    row,read=unverified_pointer_envelope(address,forged=forged)
                    with self.assertRaisesRegex(a.ObservationError,'unreconciled indirect/stack pointer source domain'):
                        a.validate_interval(row,read)
    def test_all_captured_high_rom_reads_require_pinned_values(self):
        for address in (0xC00000,0xD13000,0xFFFFFF):
            with self.subTest(address=address):
                row,read=envelope();row['events'].insert(1,bus('read',address,0xEA))
                self.assertEqual(a.validate_interval(row,read)['executed_instructions'],1)
                row['events'][1]['value']=0
                with self.assertRaisesRegex(a.ObservationError,'immutable ROM read'):
                    a.validate_interval(row,read)
    def test_missing_execution_ordinal_refuses(self):self.row['events'][-1]['ordinal']=3;self.reject()
    def test_bus_wrong_owner_refuses(self):
        self.row,self.read=envelope(write=(0x7E3000,9));self.row['events'][1]['ordinal']=2;self.reject()
    def test_terminal_bus_event_refuses(self):self.row['events'].append(bus('read',0,0,ordinal=2,clock=113));self.reject()
    def test_bad_opcode_peek_refuses(self):self.row['events'][0]['code'][3]=0;self.reject()
    def test_bad_stack_peek_refuses(self):self.row['events'][0]['stack'][5]=1;self.reject()
    def test_bad_hardware_marker_refuses(self):self.row['exit_marker']['hardware'][0]^=1;self.reject()
    def test_bad_native_status_transform_refuses(self):self.row['events'][0]['cpu']['ps']=0x2C;self.reject()
    def test_wrong_trampoline_refuses(self):self.row['entry_marker']['trampolines'][1]^=1;self.reject()
    def test_wrong_marker_extent_refuses(self):self.row['entry_marker']['gate_bytes'].append(0);self.reject()
    def test_unknown_event_field_refuses(self):self.row['events'][0]['extra']=1;self.reject()
    def test_boolean_wram_byte_refuses(self):self.row['wram_before'][0]=False;self.reject()
    def test_float_opcode_byte_refuses(self):self.row['events'][0]['code'][0]=76.;self.reject()
    def test_full_clock_backwards_refuses(self):
        t=self.row['events'][-1]['timing'];t['memoryManager.masterClock']=99;t['masterClock']=99;self.reject()
    def test_cycle_count_backwards_refuses(self):self.row['events'][-1]['timing']['cpu.cycleCount']=1;self.reject()
    def test_frame_count_backwards_refuses(self):self.row['events'][-1]['timing']['frameCount']=0;self.reject()
    def test_generic_clock_disagreement_refuses(self):self.row['events'][-1]['timing']['masterClock']+=1;self.reject()
    def test_timing_unknown_key_refuses(self):self.row['events'][-1]['timing']['privateCounter']=1;self.reject()
    def test_duration_over_budget_refuses(self):self.row['events'][-1]['timing']=timing(100+a.MAX_CLOCK+1);self.reject()
    def test_unrestored_register_refuses(self):self.row['events'][-1]['cpu']['a']=1;self.reject()
    def test_wrong_endpoint_refuses(self):self.row['events'][-1]['cpu']['pc']+=1;self.reject()


class Summary(unittest.TestCase):
    def setUp(self):
        row,self.read=envelope()
        self.trace={'schema':a.SCHEMA,'error':None,'pilot':True,'intervals':[row],
            'baseline':{'location':0x1DB,'party':[0,1,2]},
            'resolver':{'poll':378,'cpu':cpu(0xC14612),'selector':8,'branch':0},'terminal_poll':381}
        self.old={379:{'cpu':copy.deepcopy(row['events'][0]['cpu']),'stack':row['entry_marker']['hardware']+[0]*8}}
    def result(self):
        with mock.patch.object(a,'reference_entries',return_value=self.old),mock.patch.object(
                a,'reference_resolver',return_value={'cpu':cpu(0xC14612)}):
            return a.summarize(self.trace,self.read,pilot=True)
    def reject(self):
        with self.assertRaises(a.ObservationError):self.result()
    def test_original_summary_with_mocked_prior_identity(self):
        # Only original historical context identity is mocked, not the validator.
        self.assertEqual(self.result()['complete_observed_intervals'],1)
    def test_prior_cpu_mismatch_refuses(self):self.old[379]['cpu']['a']=1;self.reject()
    def test_prior_hardware_mismatch_refuses(self):self.old[379]['stack'][1]=1;self.reject()
    def test_wrong_pilot_refuses(self):self.trace['pilot']=False;self.reject()
    def test_extra_interval_refuses(self):self.trace['intervals'].append(copy.deepcopy(self.trace['intervals'][0]));self.reject()
    def test_wrong_poll_refuses(self):self.trace['intervals'][0]['poll']=380;self.reject()
    def test_reported_collector_error_refuses(self):self.trace['error']='failed';self.reject()
    def test_wrong_resolver_site_refuses(self):self.trace['resolver']['cpu']['pc']+=1;self.reject()
    def test_changed_checkpoint_party_refuses(self):self.trace['baseline']['party']=[6,4,3];self.reject()
    def test_float_terminal_poll_refuses(self):self.trace['terminal_poll']=381.;self.reject()
    def test_float_resolver_poll_refuses(self):self.trace['resolver']['poll']=378.;self.reject()
    def test_float_selector_refuses(self):self.trace['resolver']['selector']=8.;self.reject()
    def test_boolean_branch_refuses(self):self.trace['resolver']['branch']=False;self.reject()
    def test_float_location_refuses(self):self.trace['baseline']['location']=475.;self.reject()
    def test_boolean_party_id_refuses(self):self.trace['baseline']['party'][0]=False;self.reject()
    def test_full_resolver_cpu_mismatch_refuses(self):self.trace['resolver']['cpu']['a']=1;self.reject()
    def test_boolean_pilot_argument_required(self):
        with self.assertRaises(a.ObservationError):a.summarize(self.trace,self.read,pilot=1)


if __name__=='__main__':unittest.main()
