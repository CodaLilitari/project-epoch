"""Original algebra and executable leaf specimens; no ROM or native fixture."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene8c8d_subdispatch_v1 as a


def specimen(command=0x8C,index=0):
    target=a.TARGETS[command][index];ret=target+11
    # Original TDC/JMP/RTS miniature: no canonical instruction sequence copied.
    program={target:0x7B,target+1:0x4C,target+2:ret&255,target+3:(ret>>8)&255,ret:0x60}
    def read(pc,n):return bytes(program.get(pc+i,0) for i in range(n))
    return (a.handlers.walk_direct(read,target,'near'),
            a.values.value_walk(read,target,'near',entry_b=0,entry_dbr=126))


class Prefix(unittest.TestCase):
    def test_four_selected_cells_have_two_parameter_aliases(self):
        for command in a.ENTRIES:
            admitted=[p for p in range(256) if a.prefix_contract(command,p)['among_four_reviewed_cells']]
            self.assertEqual(admitted,[0,1,2,3,128,129,130,131])
            for index in range(4):
                rows=[a.prefix_contract(command,p) for p in (index,index+128)]
                self.assertEqual(rows[0]['final_x'],rows[1]['final_x'])
                self.assertEqual(rows[0]['pointer_byte_addresses'],[a.TABLES[command]+2*index,a.TABLES[command]+2*index+1])

    def test_b0_does_not_bound_to_four_cells(self):
        for command in a.ENTRIES:
            rows=[a.prefix_contract(command,p) for p in range(256)]
            self.assertEqual(len({tuple(r['pointer_byte_addresses']) for r in rows}),128)
            self.assertFalse(a.prefix_contract(command,4)['among_four_reviewed_cells'])
            self.assertEqual(a.prefix_contract(command,4)['pointer_byte_addresses'][0],a.TARGETS[command][0])

    def test_all_b_parameter_pairs_select_every_other_cell(self):
        for command in a.ENTRIES:
            starts=set();physical=set()
            for b in range(256):
                for p in range(256):
                    r=a.prefix_contract(command,p,b)
                    self.assertEqual(r['final_x'],b*256+(p%128)*2)
                    starts.add(r['pointer_byte_addresses'][0]);physical.update(r['pointer_byte_addresses'])
            self.assertEqual(len(starts),32768)
            self.assertEqual(physical,set(range(0xCD0000,0xCE0000)))

    def test_hidden_b_is_not_zero_extended(self):
        r=a.prefix_contract(0x8C,0,1)
        self.assertEqual(r['final_x'],256);self.assertFalse(r['among_four_reviewed_cells'])
        self.assertEqual(r['pointer_byte_addresses'],[0xCD2A61,0xCD2A62])

    def test_8c_pointer_high_byte_wraps_within_program_bank(self):
        self.assertEqual(a.prefix_contract(0x8C,0x4F,0xD6)['pointer_byte_addresses'],[0xCDFFFF,0xCD0000])

    def test_8d_last_even_cell_does_not_cross_bank(self):
        self.assertEqual(a.prefix_contract(0x8D,0x2E,0xD6)['pointer_byte_addresses'],[0xCDFFFE,0xCDFFFF])

    def test_namespace_and_exact_byte_types(self):
        for args in ((0x8B,0,0),(0x8E,0,0),(140.,0,0),(True,0,0),(0x8C,True,0),
                     (0x8C,0,False),(0x8C,-1,0),(0x8D,256,0),(0x8D,0,256)):
            with self.subTest(args=args),self.assertRaises(ValueError):a.prefix_contract(*args)

    def test_prefix_preserves_declared_frame_and_domain_limit(self):
        r=a.prefix_contract(0x8D,255,255)
        self.assertEqual(r['new_stack_bytes_in_prefix'],0);self.assertIs(r['jump_adds_return_frame'],False)
        self.assertIs(r['hidden_b_zero_extension_assumed'],False)
        self.assertEqual(r['entry_contract'],{'m8':True,'x8':False,'irq_masked':True,'d':0,'dbr':126})


class Composition(unittest.TestCase):
    def setUp(self):self.control,self.value=specimen()
    def result(self):return a.validate_target(0x8C,0,self.control,self.value)
    def rejects(self):
        with self.assertRaises(ValueError):self.result()

    def test_all_eight_original_executable_leaf_specimens(self):
        for command in a.ENTRIES:
            for index in range(4):
                r=a.validate_target(command,index,*specimen(command,index))
                self.assertEqual(r['additional_bytes_below_scene_handler_entry'],0)
                self.assertEqual(r['existing_scene_near_frame_bytes'],2)
                self.assertEqual(r['new_frame_from_dispatch_jump'],0)
                self.assertEqual((r['return_a'],r['return_b'],r['return_d'],r['return_dbr']),(0,0,0,126))
                self.assertEqual(r['parameter_arithmetic_aliases'],[index,index+128])
                self.assertIs(r['legal_parameter_values_proved'],False)

    def test_wrong_command_or_index_refuses(self):
        for command,index in ((0x8B,0),(0x8C,4),(0x8D,-1),(0x8C,False),(140.,0)):
            with self.subTest(command=command,index=index),self.assertRaises(ValueError):
                a.validate_target(command,index,self.control,self.value)
    def test_wrong_control_target(self):self.control['entry']='$CE2969';self.rejects()
    def test_wrong_call_kind(self):self.control['kind']='long';self.rejects()
    def test_open_frontier(self):self.control['frontier']={};self.rejects()
    def test_unexpected_local_stack(self):self.control['maximum_additional_bytes_below_callee_entry']=1;self.rejects()
    def test_false_zero_depth(self):self.control['maximum_additional_bytes_below_callee_entry']=False;self.rejects()
    def test_float_frame_extent(self):self.control['maximum_counted_bytes_including_root_call_frame']=2.;self.rejects()
    def test_wrong_return_site(self):self.control['return_width_states'][0]['site']='$CD2975';self.rejects()
    def test_control_integer_alias_of_width_boolean(self):self.control['return_width_states'][0]['m8']=1;self.rejects()
    def test_different_value_coverage(self):self.value['decoded_byte_intervals']=[];self.rejects()
    def test_additional_call(self):self.value['direct_calls']=[{'site':'$CD2969'}];self.rejects()
    def test_opaque_value_callee(self):self.value['all_direct_callees_inlined']=False;self.rejects()
    def test_wrong_value_entry_bank(self):self.value['entry_dbr']=0;self.rejects()
    def test_unknown_entry_b(self):self.value['entry_b']=None;self.rejects()
    def test_false_entry_d(self):self.value['entry_d']=False;self.rejects()
    def test_wrong_value_width(self):self.value['entry_x8']=True;self.rejects()
    def test_unknown_return_b(self):self.value['ends'][0]['b']=None;self.rejects()
    def test_wrong_return_dbr(self):self.value['ends'][0]['dbr']=0;self.rejects()
    def test_float_return_zero(self):self.value['ends'][0]['a_low']=0.;self.rejects()
    def test_integer_alias_return_boolean(self):self.value['ends'][0]['irq_masked']=1;self.rejects()
    def test_leftover_frame(self):self.value['ends'][0]['frames']=[{'return':'caller','kind':'near'}];self.rejects()
    def test_extra_return(self):self.value['ends'].append(copy.deepcopy(self.value['ends'][0]));self.rejects()
    def test_nonstack_promotion(self):self.value['nonstack_memory_and_dma_effects_proved']=True;self.rejects()
    def test_termination_promotion(self):self.value['termination_proved']=True;self.rejects()
    def test_canonical_identity_rejects_before_source_walk(self):
        with mock.patch.object(a.handlers,'walk_direct',side_effect=AssertionError('must not walk')):
            for data in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(data,{})


if __name__=='__main__':unittest.main()
