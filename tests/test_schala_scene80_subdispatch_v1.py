"""Original dispatch algebra, executable miniatures and adversarial metadata.

No canonical game instruction stream or native trace is a test fixture.
"""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene80_subdispatch_v1 as a


def miniature(program=(0x7B,0x8B,0xAB,0x60)):
    # Original TDC/PHB/PLB/RTS at a diagnostic identity, not copied ROM bytes.
    entry=0xCD4000
    def read(p,n):
        i=p-entry
        return bytes(program[i:i+n]) if 0<=i<len(program) else bytes(n)
    return (a.handlers.walk_direct(read,entry,'near'),
            a.values.value_walk(read,entry,'near',entry_b=0,entry_dbr=126))


class Geometry(unittest.TestCase):
    def test_first29_words_two_parameter_aliases_each(self):
        accepted=[p for p in range(256) if a.prefix_contract(p)['among_first29_physical_words']]
        self.assertEqual(accepted,list(range(29))+list(range(128,157)))
        for i in range(29):
            r=a.prefix_contract(i);alias=a.prefix_contract(i+128)
            self.assertEqual(r['final_x'],2*i);self.assertEqual(alias['final_x'],2*i)
            self.assertEqual(r['pointer_byte_addresses'],[a.TABLE+2*i,a.TABLE+2*i+1])
            self.assertEqual(r['pointer_byte_addresses'],alias['pointer_byte_addresses'])

    def test_boundary_is_29_not_incbin_word_count(self):
        self.assertEqual(a.TABLE+29*2,a.CODE_START)
        self.assertEqual((a.INCBIN_END-a.TABLE)//2,107)
        self.assertEqual(a.INCBIN_END-a.CODE_START,156)
        self.assertEqual(min(a.FIRST_TARGETS),a.CODE_START)
        self.assertEqual(a.prefix_contract(29)['pointer_byte_addresses'],[a.CODE_START,a.CODE_START+1])
        self.assertFalse(a.prefix_contract(29)['among_first29_physical_words'])

    def test_b0_spans128_words_including_beyond_incbin(self):
        starts={a.prefix_contract(p)['pointer_byte_addresses'][0] for p in range(256)}
        self.assertEqual(starts,set(range(a.TABLE,a.TABLE+256,2)))
        self.assertEqual(a.prefix_contract(107)['pointer_byte_addresses'][0],a.INCBIN_END)
        self.assertEqual(a.prefix_contract(127)['pointer_byte_addresses'][1],0xCD2B50)

    def test_hidden_b_survives_byte_shift_and_word_tax(self):
        row=a.prefix_contract(0xFF,0x11)
        self.assertEqual(row['final_x'],0x11FE)
        self.assertFalse(row['among_first29_physical_words'])
        self.assertIs(row['hidden_b_zero_extension_assumed'],False)

    def test_all_b_parameter_pairs_independent_algebra(self):
        starts=set();physical=set()
        for b in range(256):
            for p in range(256):
                r=a.prefix_contract(p,b)
                self.assertEqual(r['final_x'],256*b+2*(p%128))
                start=(0x2A51+256*b+2*(p%128))%65536
                self.assertEqual(r['pointer_byte_addresses'],[0xCD0000+start,0xCD0000+(start+1)%65536])
                starts.add(r['pointer_byte_addresses'][0]);physical.update(r['pointer_byte_addresses'])
        self.assertEqual(len(starts),32768)
        self.assertEqual(physical,set(range(0xCD0000,0xCE0000)))

    def test_odd_base_pointer_read_wraps_within_pbr(self):
        self.assertEqual(a.prefix_contract(0x57,0xD5)['pointer_byte_addresses'],[0xCDFFFF,0xCD0000])

    def test_no_new_dispatch_call_frame(self):
        r=a.prefix_contract(0)
        self.assertEqual(r['prefix_stack_bytes'],0)
        self.assertIs(r['dispatch_jump_adds_frame'],False)

    def test_exact_byte_types_and_bounds(self):
        for p,b in ((False,0),(1.,0),(-1,0),(256,0),(0,True),(0,0.),(0,-1),(0,256)):
            with self.subTest(p=p,b=b),self.assertRaises(ValueError):a.prefix_contract(p,b)


class Composition(unittest.TestCase):
    def setUp(self):self.control,self.value=miniature()
    def result(self):return a.validate_closed(self.control,self.value)
    def reject(self):
        with self.assertRaises(ValueError):self.result()
    def test_original_save_restore_miniature_composes(self):
        row=self.result()
        self.assertEqual(row['additional_bytes'],1)
        self.assertEqual(row['total_including_existing_near_frame'],3)
        self.assertEqual(row['added_dispatch_jump_frame'],0)
        self.assertIs(row['legal_parameter_reachability_proved'],False)
        self.assertEqual(row['status'],'proved-B0-D0-DBR7E')
    def test_no_software_stack_miniature(self):
        row=a.validate_closed(*miniature((0x7B,0x60)))
        self.assertEqual(row['additional_bytes'],0)
        self.assertEqual(row['total_including_existing_near_frame'],2)
    def test_actual_byte_mode_load_keeps_hidden_b(self):
        row=a.validate_closed(*miniature((0xA9,0xCD,0x60)))
        self.assertTrue(row['b_zero_on_every_projected_return'])
    def test_actual_word_load_may_return_nonzero_b(self):
        c,v=miniature((0xC2,0x20,0xA9,0x34,0x12,0xE2,0x20,0x60))
        with self.assertRaisesRegex(ValueError,'return unproved'):a.validate_closed(c,v)
    def test_wrong_target_bank(self):self.control['entry']='$CE4000';self.reject()
    def test_wrong_call_kind(self):self.control['kind']='long';self.reject()
    def test_unclosed_control(self):self.control['frontier']={};self.reject()
    def test_extra_near_frame_count(self):self.control['maximum_counted_bytes_including_root_call_frame']=5;self.reject()
    def test_float_total(self):self.control['maximum_counted_bytes_including_root_call_frame']=3.;self.reject()
    def test_bool_extra(self):self.control['maximum_additional_bytes_below_callee_entry']=True;self.reject()
    def test_wrong_control_width(self):self.control['return_width_states'][0]['m8']=1;self.reject()
    def test_wrong_value_entry(self):self.value['entry_b']=None;self.reject()
    def test_bad_dbr_entry(self):self.value['entry_dbr']=0;self.reject()
    def test_decoded_context_disagreement(self):self.value['decoded_context_identity_sha256']='f'*64;self.reject()
    def test_decoded_interval_disagreement(self):self.value['decoded_byte_intervals']=[];self.reject()
    def test_direct_call_disagreement(self):self.value['direct_calls']=[{'site':'$CD4000'}];self.reject()
    def test_mnemonic_disagreement(self):self.value['mnemonic_context_counts']={};self.reject()
    def test_return_unknown_b(self):self.value['ends'][0]['b']=None;self.reject()
    def test_return_nonzero_b(self):self.value['ends'][0]['b']=1;self.reject()
    def test_return_float_zero(self):self.value['ends'][0]['d']=0.;self.reject()
    def test_return_wrong_dbr(self):self.value['ends'][0]['dbr']=0;self.reject()
    def test_return_wrong_width(self):self.value['ends'][0]['irq_masked']=1;self.reject()
    def test_live_return_frame(self):self.value['ends'][0]['frames']=[('caller','near')];self.reject()
    def test_forged_alias_authority(self):self.value['nonstack_memory_and_dma_effects_proved']=True;self.reject()
    def test_forged_termination(self):self.value['termination_proved']=True;self.reject()
    def test_canonical_identity_fails_before_walking(self):
        with mock.patch.object(a.handlers,'walk_direct',side_effect=AssertionError('no walk')):
            for data in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(data,{})


class Union(unittest.TestCase):
    def rows(self):
        # Original metadata partitions for interval reconciliation, not ROM walks.
        rows=[{'entry':a.cpu(x),'decoded_byte_intervals':[]} for x in a.FIRST_TARGETS]
        rows[0]['decoded_byte_intervals']=[{'start':a.cpu(a.CODE_START),'end_exclusive':a.cpu(a.CODE_START+73)}]
        rows[1]['decoded_byte_intervals']=[{'start':a.cpu(a.CODE_START+70),'end_exclusive':a.cpu(a.INCBIN_END)}]
        return rows
    def test_overlapping_partitions_cover_exact156(self):
        r=a.code_union(self.rows())
        self.assertEqual(r['bytes'],156)
        self.assertTrue(r['coverage_is_conditional_source_decoding_not_runtime_execution'])
    def test_single_byte_hole_refuses(self):
        rows=self.rows();rows[1]['decoded_byte_intervals'][0]['start']=a.cpu(a.CODE_START+74)
        with self.assertRaisesRegex(ValueError,'hole'):a.code_union(rows)
    def test_extra_nonlocal_coverage_is_clipped(self):
        rows=self.rows();rows[0]['decoded_byte_intervals'].append({'start':'$C00000','end_exclusive':'$C00010'})
        self.assertEqual(a.code_union(rows)['bytes'],156)
    def test_empty_interval_refuses(self):
        rows=self.rows();rows[0]['decoded_byte_intervals'][0]['end_exclusive']=a.cpu(a.CODE_START)
        with self.assertRaisesRegex(ValueError,'nonempty'):a.code_union(rows)
    def test_reordered_entries_refuse(self):
        rows=self.rows();rows[2],rows[3]=rows[3],rows[2]
        with self.assertRaisesRegex(ValueError,'ordered'):a.code_union(rows)
    def test_missing_contract_refuses(self):
        with self.assertRaisesRegex(ValueError,'first29'):a.code_union(self.rows()[:-1])


if __name__=='__main__':unittest.main()
