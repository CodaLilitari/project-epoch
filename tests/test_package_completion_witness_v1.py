"""Original synthetic completion envelopes; no game artifacts or native launch.

These tests certify only the selected-metadata validator. The real collector
rehashes and revalidates the untouched full native pair independently.
Synthetic timestamps provide ordered envelopes, not hardware reachability.
"""
from __future__ import annotations
import copy
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_package_completion_witness_v1 as a


def fixture():
    anchors=((49,376),(50,376),(51,377),(73,388),(74,413),(77,414),
        (181,466),(982,927),(993,932),(1108,989),(1113,991),(1114,991),
        (1115,991),(1116,992),(1117,993),(1118,993),(1119,993),(1120,993),
        (1253,994),(1275,994))
    def poll(index):
        for (left,lp),(right,rp) in zip(anchors,anchors[1:]):
            if left<=index<=right:return lp+(rp-lp)*(index-left)//(right-left)
        raise AssertionError(index)
    roles={51:'branch-producer-complete',74:'common-loader-rts',
        993:'terminal-command-clear',1108:'terminal-command-clear',1113:'sync-command-increment',
        1116:'caller-effect-latch',1119:'result-wrapper-entry',1120:'result-application-entry',
        1253:'animation-result-return',1275:'transaction-caller-resume'}
    roles.update({index:'caller-package-latch' if n%2==0 else 'caller-resume'
                  for n,index in enumerate(a.LOOP_INDICES)})
    writes={x[0]:x for x in a.LATCHES};live={'package':0,'scene':0};rows=[]
    for index in a.INDICES:
        kind=roles.get(index,'latch-write');clock=100000+index*100;cycle=10000+index*10
        address=0xC185D1 if index==1275 else a.v.validation.SITES.get(kind,0)
        pc=address;value=-1;sp=0x6DC;stack=list(a.CALLER_FRAME)
        if index in writes:
            _,address,value,pc,_,sp=writes[index]
        if index==74:sp=0x6D8
        if index in (993,1108,1113,1114):
            sp=0x6D6;inner={993:0x4C06,1108:0x4BF1,1113:0x4BCA,1114:0x4BCA}[index]
            stack=[0xD6,0x4C,inner&255,inner>>8,0xCD,0x40]+list(a.CALLER_FRAME[:10])
        if index==1119:sp=0x6E8;stack=[0x20,0xBC]+list(a.OUTER_FRAME[:14])
        if index==1120:sp=0x6E4;stack=[0x87,0xAC,0x5C,0xAC,0x20,0xBC]+list(a.OUTER_FRAME[:10])
        if index==1253:sp=0x6EA;stack=list(a.OUTER_FRAME)
        if index==1275:sp=0x6EC;stack=list(a.OUTER_FRAME[2:])+[0,0]
        if index==1114:clock=100000+1113*100+40;cycle=10000+1113*10+6
        cpu={'a':0,'x':{993:4,1108:3,1113:2,1114:2}.get(index,0),'y':0,
             'd':0,'dbr':0x7E,'sp':sp,'ps':0x22 if index==1113 else 0x20,
             'k':pc>>16,'pc':pc&65535,'emulationMode':False}
        timing={'masterClock':clock,'memoryManager.masterClock':clock,'cpu.cycleCount':cycle,
            'frameCount':poll(index)+10,'ppu.frameCount':poll(index)+10,
            'ppu.scanline':0,'memoryManager.hClock':0,'clockRate':21477270}
        rows.append({'index':index,'kind':kind,'address':address,'value':value,'frame':poll(index),
            'cpu':cpu,'stack':stack,'timing':timing,'latches':dict(live),
            'context':{'transaction_id':1,'transaction_active':True,'resolver_active':False,
                       'animation_identity':[0,2,8,0]}})
        if kind=='latch-write':live['package' if address==0x7E9876 else 'scene']=value
    return rows


class CompletionWitnessTests(unittest.TestCase):
    def setUp(self):self.rows=fixture();self.by={r['index']:r for r in self.rows}

    def rejects(self):
        with self.assertRaises(a.WitnessError):a.validate_projection(self.rows)

    def test_original_envelope_and_explicit_limits(self):
        result=a.validate_projection(self.rows)
        self.assertEqual(result['projected_record_count'],1051)
        self.assertEqual(result['zero_package_wait_iterations'],516)
        self.assertEqual(result['nonzero_package_wait_snapshots'],1)
        self.assertEqual(len(result['latch_write_readback_pairs']),8)
        self.assertEqual([x['calculated_stz_byte_target'] for x in result['stop_handler_observations']],['7E5DB0','7E5DAF'])
        for key in a.NONCLAIMS:self.assertIs(result[key],False)
        self.assertFalse(result['default_family_increment']['encoded_command_byte_observed'])

    def test_missing_record(self):self.rows.pop();self.rejects()
    def test_reordered_records(self):self.rows[0],self.rows[1]=self.rows[1],self.rows[0];self.rejects()
    def test_nonobject_record(self):self.rows[0]=None;self.rejects()
    def test_extra_field(self):self.rows[0]['invented']=0;self.rejects()
    def test_boolean_ordinal(self):self.rows[0]['index']=True;self.rejects()
    def test_missing_cpu_key(self):del self.by[1115]['cpu']['d'];self.rejects()
    def test_float_equal_cpu(self):self.by[1115]['cpu']['dbr']=126.0;self.rejects()
    def test_boolean_latch(self):self.by[1115]['latches']['package']=True;self.rejects()
    def test_boolean_timing(self):self.by[1115]['timing']['ppu.scanline']=False;self.rejects()
    def test_nonboolean_context(self):self.by[1115]['context']['transaction_active']=1;self.rejects()
    def test_native_mode_not_integer(self):self.by[1115]['cpu']['emulationMode']=0;self.rejects()
    def test_unknown_kind(self):self.by[1115]['kind']='package-read';self.rejects()
    def test_wrong_execution_pc(self):self.by[1115]['cpu']['pc']+=1;self.rejects()
    def test_wrong_execution_bank(self):self.by[1115]['cpu']['k']=0x41;self.rejects()
    def test_wrong_write_callback_pc(self):self.by[1114]['cpu']['pc']-=3;self.rejects()
    def test_wrong_latch_bus_bank(self):self.by[1114]['address']=0x009876;self.rejects()
    def test_wrong_write_width(self):self.by[1114]['cpu']['ps']=0;self.rejects()
    def test_wrong_reader_bank(self):self.by[1115]['cpu']['dbr']=0x41;self.rejects()
    def test_wrong_reader_direct_page(self):self.by[1115]['cpu']['d']=0x1234;self.rejects()
    def test_wrong_reader_decimal(self):self.by[1115]['cpu']['ps']|=8;self.rejects()
    def test_wrong_index_width(self):self.by[993]['cpu']['ps']|=0x10;self.rejects()
    def test_wrong_stop_owner_index(self):self.by[993]['cpu']['x']=3;self.rejects()
    def test_wrong_stop_frame(self):self.by[993]['stack'][2]^=1;self.rejects()
    def test_wrong_caller_frame(self):self.by[1115]['stack'][0]^=1;self.rejects()
    def test_wrong_default_frame(self):self.by[1113]['stack'][0]^=1;self.rejects()
    def test_wrong_result_near_frame(self):self.by[1120]['stack'][0]^=1;self.rejects()
    def test_wrong_actual_caller(self):self.by[1275]['cpu']['pc']+=1;self.rejects()
    def test_wrong_actual_return_stack(self):self.by[1275]['stack'][0]^=1;self.rejects()
    def test_full_clock_reversal(self):self.by[1115]['timing']['memoryManager.masterClock']=1;self.by[1115]['timing']['masterClock']=1;self.rejects()
    def test_full_cycle_reversal(self):self.by[1115]['timing']['cpu.cycleCount']=1;self.rejects()
    def test_full_frame_reversal(self):self.by[1115]['timing']['ppu.frameCount']=1;self.by[1115]['timing']['frameCount']=1;self.rejects()
    def test_input_poll_reversal(self):self.by[1115]['frame']=1;self.rejects()
    def test_wrong_inc_clock_delta(self):self.by[1114]['timing']['memoryManager.masterClock']+=2;self.by[1114]['timing']['masterClock']+=2;self.rejects()
    def test_wrong_inc_cycle_delta(self):self.by[1114]['timing']['cpu.cycleCount']+=1;self.rejects()
    def test_wrong_inc_nz(self):self.by[1114]['cpu']['ps']|=2;self.rejects()
    def test_wrong_inc_preserved_carry(self):self.by[1114]['cpu']['ps']|=1;self.rejects()
    def test_low32_rollover_is_valid(self):
        for r in self.rows:
            t=r['timing'];t['memoryManager.masterClock']+=0xFFFFFFFF-150000
            t['masterClock']=t['memoryManager.masterClock']&0xFFFFFFFF
        a.validate_projection(self.rows)
    def test_low32_mismatch(self):self.by[1115]['timing']['masterClock']+=1;self.rejects()
    def test_early_unexplained_package_signal(self):self.by[1109]['latches']['package']=1;self.rejects()
    def test_signal_write_without_readback(self):self.by[1115]['latches']['package']=0;self.rejects()
    def test_scene_clear_without_readback(self):self.by[983]['latches']['scene']=1;self.rejects()
    def test_scene_caller_still_busy(self):self.by[1116]['latches']['scene']=1;self.rejects()
    def test_later_cleanup_pre_memory_not_earlier_scene_clear(self):self.by[1117]['latches']['scene']=1;self.rejects()
    def test_later_cleanup_without_package_reset(self):self.by[1119]['latches']['package']=1;self.rejects()
    def test_extra_donated_write(self):self.by[994]['kind']='latch-write';self.by[994]['address']=0x7E9876;self.by[994]['value']=0;self.rejects()
    def test_other_transaction(self):self.by[1114]['context']['transaction_id']=2;self.rejects()
    def test_resolver_scope_still_open(self):self.by[1114]['context']['resolver_active']=True;self.rejects()
    def test_enemy_identity(self):self.by[1114]['context']['animation_identity'][0]=3;self.rejects()
    def test_boolean_identity(self):self.by[1114]['context']['animation_identity'][0]=False;self.rejects()
    def test_decode_duplicate_keys(self):
        with self.assertRaises(a.WitnessError):a.decode(b'{"a":1,"a":2}')
    def test_decode_nonfinite(self):
        with self.assertRaises(a.WitnessError):a.decode(b'{"a":NaN}')
    def test_read_bounds_and_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder).resolve()/'original.txt';path.write_bytes(b'original fixture')
            self.assertEqual(a.read(path,expected=a.sha(b'original fixture')),b'original fixture')
            with self.assertRaises(a.WitnessError):a.read(path,maximum=2)
            with self.assertRaises(a.WitnessError):a.read(path,expected='0'*64)
    def test_full_trace_validator_called_before_projection(self):
        class IndependentFailure(RuntimeError):pass
        with mock.patch.object(a.v,'summarize',side_effect=IndependentFailure),self.assertRaises(IndependentFailure):
            a.validate_trace({'records':[]})


if __name__=='__main__':unittest.main()
