"""Original parameter algebra and typed-contract specimens; no game input."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene82_subdispatch_v1 as a


def specimen(index=0):
    target,ret=a.TARGETS[index],a.RETURNS[index]
    program={target:0x4C,target+1:ret&255,target+2:ret>>8&255,ret:0x60}
    def read(pc,n):return bytes(program.get(pc+i,0) for i in range(n))
    control=a.handlers.walk_direct(read,target,'near')
    value=a.values.value_walk(read,target,'near',entry_b=0,entry_dbr=126)
    # This synthetic jump preserves unknown low A; the actual target's TDC
    # result is represented as original metadata for the composition guard.
    value['ends'][0]['a_low']=0
    return control,value


class Prefix(unittest.TestCase):
    def test_two_parameter_reads_are_independent(self):
        r=a.prefix_contract(0,255)
        self.assertEqual(r['stored_dp45_word'],1);self.assertEqual(r['final_x'],14)
        self.assertEqual(r['pointer_byte_addresses'],[0xCD2DF8,0xCD2DF9])

    def test_all_b0_parameter_pairs_select_exact_eight_cells(self):
        selections=set();counts=set()
        for first in range(256):
            for second in range(256):
                r=a.prefix_contract(first,second);counts.add(r['stored_dp45_word'])
                selections.add(tuple(r['pointer_byte_addresses']))
                self.assertEqual(r['final_x'],2*(second>>5))
                self.assertEqual(r['stored_dp45_bytes'],[(first%32)+1,0])
        self.assertEqual(counts,set(range(1,33)))
        self.assertEqual(selections,{(0xCD2DEA+2*i,0xCD2DEB+2*i) for i in range(8)})

    def test_nonzero_b_is_preserved_in_both_x_transfers(self):
        r=a.prefix_contract(31,224,5)
        self.assertEqual(r['stored_dp45_word'],0x520);self.assertEqual(r['final_x'],0x50E)
        self.assertFalse(r['among_eight_reviewed_cells'])

    def test_byte_and_boolean_types_refuse(self):
        for args in ((True,0,0),(0,False,0),(0,0,False),(-1,0,0),(0,256,0),(0,0,256),(0.,0,0)):
            with self.subTest(args=args),self.assertRaises(ValueError):a.prefix_contract(*args)

    def test_upper_low_bits_do_not_change_selected_cell(self):
        for second in range(0,256,32):
            self.assertEqual({a.prefix_contract(0,v)['final_x'] for v in range(second,second+32)},
                {second>>4})

    def test_prefix_adds_no_stack_or_return_frame(self):
        r=a.prefix_contract(255,255)
        self.assertEqual(r['new_stack_bytes_in_prefix'],0);self.assertIs(r['jump_adds_return_frame'],False)
        self.assertIs(r['m8'],True);self.assertIs(r['x8'],False);self.assertIs(r['irq_masked'],True)


class Composition(unittest.TestCase):
    def setUp(self):self.control,self.value=specimen()
    def result(self):return a.validate_target(0,self.control,self.value)
    def rejects(self):
        with self.assertRaises(ValueError):self.result()

    def test_all_eight_conditional_contracts(self):
        for i in range(8):
            r=a.validate_target(i,*specimen(i));self.assertEqual(r['additional_bytes_below_scene_handler_entry'],0)
            self.assertEqual(r['existing_scene_near_frame_bytes'],2);self.assertEqual(r['new_frame_from_dispatch_jump'],0)
            self.assertEqual((r['return_a'],r['return_b'],r['return_d'],r['return_dbr']),(0,0,0,126))

    def test_invalid_index_types_and_values(self):
        for i in (False,-1,8,1.0):
            with self.subTest(i=i),self.assertRaises(ValueError):a.validate_target(i,self.control,self.value)

    def test_wrong_target_or_bank_refuses(self):self.control['entry']='$CE2E89';self.rejects()
    def test_wrong_call_kind_refuses(self):self.control['kind']='long';self.rejects()
    def test_open_control_cannot_be_composed(self):self.control['frontier']={};self.rejects()
    def test_added_local_stack_refuses(self):self.control['maximum_additional_bytes_below_callee_entry']=1;self.rejects()
    def test_float_stack_total_refuses(self):self.control['maximum_counted_bytes_including_root_call_frame']=2.0;self.rejects()
    def test_wrong_sole_return_refuses(self):self.control['return_width_states'][0]['site']='$CD2E88';self.rejects()
    def test_wrong_return_width_refuses(self):self.control['return_width_states'][0]['x8']=True;self.rejects()
    def test_different_value_coverage_refuses(self):self.value['decoded_byte_intervals']=[];self.rejects()
    def test_opaque_callee_cannot_replace_inlining(self):self.value['all_direct_callees_inlined']=False;self.rejects()
    def test_extra_target_call_refuses(self):self.value['direct_calls']=[{'site':'$CD2E89'}];self.rejects()
    def test_unknown_return_b_refuses(self):self.value['ends'][0]['b']=None;self.rejects()
    def test_wrong_return_bank_refuses(self):self.value['ends'][0]['dbr']=0;self.rejects()
    def test_wrong_return_d_refuses(self):self.value['ends'][0]['d']=0x500;self.rejects()
    def test_float_zero_return_refuses(self):self.value['ends'][0]['a_low']=0.;self.rejects()
    def test_integer_alias_of_boolean_refuses(self):self.value['ends'][0]['m8']=1;self.rejects()
    def test_value_entry_contract_cannot_change(self):self.value['entry_b']=None;self.rejects()
    def test_value_entry_boolean_alias_refuses(self):self.value['entry_d']=False;self.rejects()
    def test_value_entry_width_cannot_change(self):self.value['entry_x8']=True;self.rejects()
    def test_alias_promotion_refuses(self):self.value['nonstack_memory_and_dma_effects_proved']=True;self.rejects()
    def test_termination_promotion_refuses(self):self.value['termination_proved']=True;self.rejects()
    def test_unconsumed_frame_refuses(self):self.value['ends'][0]['frames']=[{'return':'abstract-caller','kind':'near'}];self.rejects()
    def test_extra_return_refuses(self):self.value['ends'].append(copy.deepcopy(self.value['ends'][0]));self.rejects()
    def test_canonical_identity_refuses_before_walking(self):
        with mock.patch.object(a.handlers,'walk_direct',side_effect=AssertionError('must not walk')):
            for blob in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(blob,{})


if __name__=='__main__':unittest.main()
