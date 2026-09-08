"""Original source and evidence specimens for scene8B conditional dispatch."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene8b_dispatch_inputs_v1 as a


def helper_fixture():
    memory={}
    def put(p,raw):
        for i,v in enumerate(raw):
            assert p+i not in memory
            memory[p+i]=v
    put(0xCD31AA,bytes.fromhex('A5 40 D0 46 80 05'))
    put(0xCD31B5,bytes.fromhex('18 60'))
    put(0xCD31F4,bytes.fromhex('7B A9 7E EA EA EA EA EA 38 60'))
    put(0xCD3189,bytes.fromhex('8D AA CA 20 AA 31 90 0C'))
    put(0xCD319D,b'\x60')
    def read(p,n):
        try:return bytes(memory[x] for x in range(p,p+n))
        except KeyError:raise ValueError('outside original helper specimen') from None
    return memory,read


def helper_models(read):
    return (a.handlers.walk_direct(read,0xCD31AA,'near'),
            a.values.value_walk(read,0xCD31AA,'near',entry_b=None,entry_dbr=126))


def target_fixture(target):
    memory={}
    for p,raw in ((target,bytes.fromhex('20 00 40 4C 7C 34')),(0xCD4000,b'\x7B\x60'),(0xCD347C,b'\x60')):
        memory.update({p+i:v for i,v in enumerate(raw)})
    def read(p,n):return bytes(memory[x] for x in range(p,p+n))
    return (a.handlers.walk_direct(read,target,'near'),
            a.values.value_walk(read,target,'near',entry_b=0,entry_dbr=126))


class Geometry(unittest.TestCase):
    def test_exact_q_byte_source_extent(self):
        self.assertEqual(a.geometry(0,0)['selector_read_address'],0x7ECAD1)
        self.assertEqual(a.geometry(255,0)['selector_read_address'],0x7ECBD0)
    def test_q_high_bit_does_not_alias(self):
        self.assertEqual(a.geometry(128,0)['selector_read_address']-a.geometry(0,0)['selector_read_address'],128)
    def test_z_high_bit_aliases_all_pointer_cells(self):
        for z in range(128):
            self.assertEqual(a.geometry(0,z)['pointer_byte_addresses'],a.geometry(0,z+128)['pointer_byte_addresses'])
    def test_exact_six_conditional_cell_domain(self):
        self.assertEqual([z for z in range(256) if a.geometry(0,z)['among_six_reviewed_cells']],list(range(6))+list(range(128,134)))
    def test_first_escape_and_last_physical_word(self):
        self.assertEqual(a.geometry(0,6)['pointer_byte_addresses'],[0xCD31AA,0xCD31AB])
        self.assertEqual(a.geometry(0,255)['pointer_byte_addresses'],[0xCD329C,0xCD329D])
    def test_exact_types_and_range_refuse(self):
        for q,z in ((True,0),(0,0.0),(-1,0),(0,256),(None,0)):
            with self.subTest(q=q,z=z),self.assertRaises(ValueError):a.geometry(q,z)


class ExitProvenance(unittest.TestCase):
    def setUp(self):self.memory,self.read=helper_fixture()
    def test_both_exact_predecessors_owned(self):
        r=a.exit_predecessors(self.read)
        self.assertEqual([x['carry'] for x in r['source_owned_exit_flags']],[False,True])
        self.assertFalse(r['global_carry_model_added'])
    def test_direct_branch_to_failure_rts_refuses(self):
        self.memory[0xCD31AF]=6
        with self.assertRaisesRegex(ValueError,'unowned flag'):a.exit_predecessors(self.read)
    def test_direct_branch_to_success_rts_refuses(self):
        self.memory[0xCD31AD]=0x4F
        with self.assertRaisesRegex(ValueError,'unowned flag'):a.exit_predecessors(self.read)
    def test_wrong_exit_flag_opcode_refuses(self):
        self.memory[0xCD31FC]=0x18
        with self.assertRaisesRegex(ValueError,'CLC or SEC'):a.exit_predecessors(self.read)
    def test_wrong_return_width_refuses(self):
        self.memory[0xCD31F9]=0xE2;self.memory[0xCD31FA]=0x10
        with self.assertRaisesRegex(ValueError,'return widths'):a.exit_predecessors(self.read)
    def test_unreviewed_callee_refuses(self):
        self.memory[0xCD31F7]=0x20;self.memory[0xCD31F8]=0;self.memory[0xCD31F9]=0x40
        with self.assertRaisesRegex(ValueError,'control transfer'):a.exit_predecessors(self.read)
    def test_operand_entry_refuses(self):
        self.memory[0xCD31AD]=(-3)&255
        with self.assertRaises(ValueError):a.exit_predecessors(self.read)


class HelperContract(unittest.TestCase):
    def setUp(self):
        self.memory,self.read=helper_fixture();self.control,self.value=helper_models(self.read)
    def result(self):return a.prehelper_contract(self.read,self.control,self.value)
    def reject(self):
        with self.assertRaises(ValueError):self.result()
    def test_success_b_zero_and_failure_unknown(self):
        r=self.result();self.assertEqual(r['success']['b'],0)
        self.assertEqual(r['failure']['b'],'unknown');self.assertFalse(r['arbitrary_failure_b_zero_claim'])
    def test_failure_unknown_not_promoted_to_zero(self):self.value['ends'][0]['b']=0;self.reject()
    def test_success_unknown_not_accepted(self):self.value['ends'][1]['b']=None;self.reject()
    def test_entry_b_not_assumed_zero(self):self.value['entry_b']=0;self.reject()
    def test_missing_return_refuses(self):self.value['ends'].pop();self.reject()
    def test_extra_return_refuses(self):self.value['ends'].append(copy.deepcopy(self.value['ends'][0]));self.reject()
    def test_different_decoded_context_refuses(self):self.value['decoded_context_identity_sha256']='0'*64;self.reject()
    def test_false_frame_size_refuses(self):self.control['maximum_additional_bytes_below_callee_entry']=False;self.reject()
    def test_float_return_refuses(self):self.value['ends'][1]['a_low']=126.0;self.reject()
    def test_nonboolean_return_width_refuses(self):self.value['ends'][1]['m8']=1;self.reject()
    def test_wrong_caller_branch_refuses(self):self.memory[0xCD3190]=0x0B;self.reject()
    def test_nonstack_claim_refuses(self):self.value['nonstack_memory_and_dma_effects_proved']=True;self.reject()
    def test_missing_d_invariant_refuses(self):self.value['d_invariant_proved_under_no_alias_no_asynchronous_premises']=False;self.reject()


class TargetContract(unittest.TestCase):
    def setUp(self):self.control,self.value=target_fixture(a.CLOSED[0])
    def result(self):return a.closed_target(self.control,self.value,a.CLOSED[0])
    def reject(self):
        with self.assertRaises(ValueError):self.result()
    def test_two_original_conditional_targets(self):
        for target in a.CLOSED:
            r=a.closed_target(*target_fixture(target),target)
            self.assertEqual(r['sequential_helper_and_target_max_additional_bytes'],2)
            self.assertEqual(r['total_including_handler_near_frame'],4)
    def test_open_target_not_substituted(self):
        with self.assertRaises(ValueError):a.closed_target(self.control,self.value,a.TARGETS[0])
    def test_zero_depth_not_invented(self):self.control['maximum_additional_bytes_below_callee_entry']=0;self.reject()
    def test_wrong_source_interval_refuses(self):self.value['decoded_byte_intervals']=[];self.reject()
    def test_unknown_return_b_refuses(self):self.value['ends'][0]['b']=None;self.reject()
    def test_leftover_frame_refuses(self):self.value['ends'][0]['frames']=[{}];self.reject()
    def test_arbitrary_b_entry_refuses(self):self.value['entry_b']=None;self.reject()
    def test_wrong_return_site_refuses(self):self.value['ends'][0]['site']='$CD347D';self.reject()
    def test_no_canonical_rom_substitute(self):
        for raw in (b'',bytes(0x400000),bytearray(0x400000)):
            with self.assertRaisesRegex(ValueError,'ROM identity'):a.audit(raw,{})


if __name__=='__main__':unittest.main()
