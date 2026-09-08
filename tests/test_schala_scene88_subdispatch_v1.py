"""Original arithmetic and certificate specimens; no extracted game bytes."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene88_subdispatch_v1 as v


def specimen(i):
    entry=f'${v.TARGETS[i]:06X}'
    sites=[f'${p:06X}' for p in v.RETURNS[i]]
    shared={'entry':entry,'kind':'near','entry_m8':True,'entry_x8':False,'entry_irq_masked':True,
            'instruction_contexts':1,'decoded_byte_intervals':[], 'direct_calls':[]}
    c={**copy.deepcopy(shared),'status':'closed-direct-stack-width-control-flow','frontier':None,
       'callee_register_value_preservation':False,'nonstack_alias_closure':False,
       'premise_nonstack_writes_do_not_modify_stack_or_saved_status':True,
       'termination_proved':False,'whole_nmi_bound':None,
       'maximum_additional_bytes_below_callee_entry':0,'maximum_counted_bytes_including_root_call_frame':2,
       'return_width_states':[{'site':p,'m8':True,'x8':False,'irq_masked':True} for p in sites]}
    low,high=(0,255) if i==3 else (255,0)
    value={**copy.deepcopy(shared),'entry_b':0,'entry_d':0,'entry_dbr':126,
           'all_direct_callees_inlined':True,'nonstack_memory_and_dma_effects_proved':False,'termination_proved':False,
           'ends':[{'site':p,'kind':'return','m8':True,'x8':False,'irq_masked':True,
                    'a_low':low,'b':high,'d':0,'dbr':126,'counted_stack_bytes':0,'frames':[]} for p in sites]}
    return c,value


class ArithmeticTests(unittest.TestCase):
    def test_exact_eight_selected_aliases(self):
        self.assertEqual([p for p in range(256) if v.parameter_contract(p)['among_four_reviewed_cells']],
                         [0,1,2,3,128,129,130,131])
    def test_high_parameter_bit_aliases_every_byte(self):
        for p in range(128):
            self.assertEqual(v.parameter_contract(p)['computed_x'],v.parameter_contract(p+128)['computed_x'])
    def test_hidden_b_is_not_silently_zero_extended(self):
        for b in range(1,256):
            row=v.parameter_contract(3,b)
            self.assertEqual(row['computed_x'],(b<<8)+6)
            self.assertFalse(row['among_four_reviewed_cells'])
    def test_b0_all_arithmetic_inputs_cover_128_cells(self):
        self.assertEqual(len({tuple(v.parameter_contract(p)['pointer_byte_addresses']) for p in range(256)}),128)
    def test_all_b_parameter_pairs_cover_even_words_in_pbr(self):
        pointers=set()
        for b in range(256):
            for p in range(256):
                row=v.parameter_contract(p,b);a,z=row['pointer_byte_addresses']
                self.assertEqual(a>>16,0xD1);self.assertEqual(z,a+1);self.assertEqual(a&1,0)
                pointers.add(a)
        self.assertEqual(len(pointers),32768)
    def test_first_successor_is_outside_reviewed_cells(self):
        row=v.parameter_contract(4)
        self.assertFalse(row['among_four_reviewed_cells']);self.assertIsNone(row['selected_ordinal'])
        self.assertEqual(row['pointer_byte_addresses'],[0xD1FBDA,0xD1FBDB])
    def test_base_plus_index_wraps_in_bank(self):
        self.assertEqual(v.parameter_contract(0,5)['pointer_byte_addresses'],[0xD100D2,0xD100D3])
    def test_strict_parameter_byte_types(self):
        for p in (True,0.0,-1,256,None,'3'):
            with self.subTest(p=p),self.assertRaises(ValueError):v.parameter_contract(p)
    def test_strict_hidden_byte_types(self):
        for b in (False,0.0,-1,256,None):
            with self.subTest(b=b),self.assertRaises(ValueError):v.parameter_contract(0,b)


class TargetCertificateTests(unittest.TestCase):
    def check_change(self,which,change,i=0):
        c,x=specimen(i);change(c if which=='control' else x)
        with self.assertRaises(ValueError):v.validate_target(i,c,x)
    def test_all_four_original_metadata_specimens_accept(self):
        self.assertEqual([v.validate_target(i,*specimen(i))['return_b'] for i in range(4)],[0,0,0,255])
    def test_nonzero_b_fourth_return_cannot_be_normalized(self):
        self.check_change('value',lambda x:x['ends'][0].update(b=0),3)
    def test_unknown_b_return_cannot_be_promoted(self):
        self.check_change('value',lambda x:x['ends'][0].update(b=None))
    def test_visible_accumulator_return_is_also_checked(self):
        self.check_change('value',lambda x:x['ends'][0].update(a_low=0))
    def test_both_selected_return_sites_required(self):
        self.check_change('value',lambda x:x['ends'].pop())
    def test_wrong_return_site_refuses(self):
        self.check_change('value',lambda x:x['ends'][0].update(site='$C00000'))
    def test_unclosed_control_refuses(self):
        self.check_change('control',lambda x:x.update(status='open'))
    def test_extra_direct_call_refuses(self):
        self.check_change('control',lambda x:x['direct_calls'].append({'kind':'near'}))
    def test_added_stack_depth_refuses(self):
        self.check_change('control',lambda x:x.update(maximum_additional_bytes_below_callee_entry=1,
            maximum_counted_bytes_including_root_call_frame=3))
    def test_float_stack_count_refuses(self):
        self.check_change('control',lambda x:x.update(maximum_counted_bytes_including_root_call_frame=2.0))
    def test_value_coverage_drift_refuses(self):
        self.check_change('value',lambda x:x.update(instruction_contexts=2))
    def test_unsupported_value_entry_b_refuses(self):
        self.check_change('value',lambda x:x.update(entry_b=None))
    def test_bool_or_float_value_entry_refuses(self):
        for bad in (False,0.0):
            self.check_change('value',lambda x:x.update(entry_b=bad))
    def test_float_return_value_refuses(self):
        self.check_change('value',lambda x:x['ends'][0].update(b=0.0))
    def test_numeric_width_return_refuses(self):
        self.check_change('value',lambda x:x['ends'][0].update(m8=1))
    def test_bank_and_direct_page_returns_checked(self):
        self.check_change('value',lambda x:x['ends'][0].update(dbr=0))
        self.check_change('value',lambda x:x['ends'][0].update(d=1))
    def test_scope_promotion_refuses(self):
        self.check_change('value',lambda x:x.update(nonstack_memory_and_dma_effects_proved=True))
    def test_target_ordinal_types_and_range_refuse(self):
        for i in (True,0.0,-1,4):
            with self.subTest(i=i),self.assertRaises(ValueError):v.validate_target(i,*specimen(0))


class FrameCompositionTests(unittest.TestCase):
    def rows(self):return [v.validate_target(i,*specimen(i)) for i in range(4)]
    def test_distinct_near_long_frames_are_counted(self):
        row=v.compose_frames(self.rows())
        self.assertEqual(row['maximum_additional_bytes_below_scene_handler_entry'],5)
        self.assertEqual(row['maximum_bytes_including_existing_scene_near_frame'],7)
        self.assertEqual(row['scene_jsl']['saved_return_word'],0x29E1)
        self.assertEqual(row['wrapper_indexed_jsr']['saved_return_word'],0xFBD0)
        self.assertFalse(row['global_scene_return_b0_proved'])
    def test_missing_or_duplicate_target_refuses(self):
        rows=self.rows()
        with self.assertRaises(ValueError):v.compose_frames(rows[:-1])
        rows[3]=copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):v.compose_frames(rows)
    def test_target_depth_cannot_be_float_or_nonzero(self):
        for value in (0.0,True,1):
            rows=self.rows();rows[1]['body_additional_stack_bytes']=value
            with self.subTest(value=value),self.assertRaises(ValueError):v.compose_frames(rows)
    def test_fourth_return_b_survives_composition(self):
        rows=self.rows();rows[3]['return_b']=0
        with self.assertRaises(ValueError):v.compose_frames(rows)
    def test_composition_width_premises_are_exact(self):
        rows=self.rows();rows[0]['return_m8']=1
        with self.assertRaises(ValueError):v.compose_frames(rows)
    def test_full_accumulator_must_match_b_and_exact_return(self):
        for ordinal,bad in ((0,0),(3,0),(3,65280.0),(0,255.0)):
            rows=self.rows();rows[ordinal]['return_a']=bad
            with self.subTest(ordinal=ordinal,bad=bad),self.assertRaises(ValueError):v.compose_frames(rows)


if __name__=='__main__':unittest.main()
