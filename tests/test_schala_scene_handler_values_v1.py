"""Original source specimens for the minimal scene return-value extension."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene_handler_values_v1 as a


def specimen(text,entry_b=0,entry_dbr=126):
    raw=bytes.fromhex(text);base=0xCD4000
    def read(pc,n):
        if not base<=pc<pc+n<=base+len(raw):raise ValueError('outside original specimen')
        return raw[pc-base:pc-base+n]
    values=a.value_walk(read,base,'near',entry_b=entry_b,entry_dbr=entry_dbr)
    typed=a.scene.walk_direct(read,base,'near')
    return values,typed


class MinimalEffects(unittest.TestCase):
    def one(self,text,**kwargs):
        row,_=specimen(text,**kwargs);self.assertEqual(len(row['ends']),1);return row['ends'][0]

    def test_xba_swaps_known_bytes_in_m8(self):
        row=self.one('a9 34 eb 60',entry_b=18)
        self.assertEqual((row['a_low'],row['b']),(18,52))

    def test_xba_swaps_known_bytes_in_m16(self):
        row=self.one('c2 20 a9 34 12 eb e2 20 60')
        self.assertEqual((row['a_low'],row['b']),(18,52))

    def test_xba_unknown_low_moves_to_b(self):
        row=self.one('ad 00 80 eb 60');self.assertEqual(row['a_low'],0);self.assertIsNone(row['b'])

    def test_xba_unknown_high_moves_to_low(self):
        row=self.one('a9 34 eb 60',entry_b=None);self.assertIsNone(row['a_low']);self.assertEqual(row['b'],52)

    def test_xba_twice_restores_both_bytes(self):
        row=self.one('a9 34 eb eb 60',entry_b=18)
        self.assertEqual((row['a_low'],row['b']),(52,18))

    def test_byte_arithmetic_then_xba_remains_unknown(self):
        self.assertIsNone(self.one('a9 00 69 00 eb 60')['b'])

    def test_late_tdc_resolves_previously_unknown_b(self):
        row=self.one('ad 00 80 eb 7b 60');self.assertEqual((row['a_low'],row['b']),(0,0))

    def test_byte_load_after_tdc_keeps_b_zero(self):
        self.assertEqual(self.one('7b ad 00 80 60')['b'],0)

    def test_word_load_after_tdc_can_make_b_nonzero(self):
        values,typed=specimen('7b c2 20 a9 00 01 e2 20 60')
        result=a.classify(values,typed);self.assertEqual(result['projected_b_values'],[1])
        self.assertEqual(result['status'],'B-return-not-proved')

    def test_and_zero_is_deliberately_conservative(self):
        self.assertIsNone(self.one('ad 00 80 29 00 eb 60')['b'])

    def test_memory_shift_and_tyx_preserve_architectural_a_bytes(self):
        for text in ('06 00','26 00','2e 00 80','bb'):
            for prefix,suffix in (('',''),('c2 20','e2 20')):
                row=self.one('a9 34 '+prefix+' '+text+' '+suffix+' 60',entry_b=18)
                self.assertEqual((row['a_low'],row['b']),(52,18))

    def test_tyx_then_txa_does_not_invent_index_value(self):
        row=self.one('bb c2 20 8a e2 20 60');self.assertIsNone(row['a_low']);self.assertIsNone(row['b'])

    def test_new_memory_loads_forget_active_width(self):
        for text in ('b7 00','67 00','ed 00 80','77 00','6f 00 80 c0'):
            row=self.one(text+' 60',entry_b=18);self.assertEqual(row['b'],18);self.assertIsNone(row['a_low'])
            row=self.one('c2 20 '+text+' e2 20 60',entry_b=18);self.assertIsNone(row['b'])

    def test_all_ten_decodes_across_widths_match_typed_contexts(self):
        for op,(_,size) in a.scene.EXTENSIONS.items():
            for m8 in (True,False):
                for x8 in (True,False):
                    prefix=('' if m8 else 'c2 20 ')+('e2 10 ' if x8 else '')
                    text=prefix+bytes([op]+[0x12]*(size-1)).hex()+' e2 20 c2 10 60'
                    values,typed=specimen(text)
                    self.assertEqual(values['decoded_context_identity_sha256'],typed['decoded_context_identity_sha256'])

    def test_preserved_model_still_refuses_xba(self):
        raw=bytes.fromhex('eb 60')
        with self.assertRaisesRegex(ValueError,'unsupported value effect EB'):
            a.old.value_walk(lambda p,n:raw[p-0xCD4000:p-0xCD4000+n],0xCD4000,'near',entry_b=0,entry_dbr=126)

    def test_no_unused_register_or_status_extension(self):
        for text in ('08 28 60','0b 2b 60','5b 60','4b ab 60','f4 00 00 60'):
            with self.subTest(text=text),self.assertRaises(ValueError):specimen(text)

    def test_exact_declared_ast_derivation(self):
        r=a.verify_derivation();self.assertTrue(r['only_declared_ast_changes']);self.assertFalse(r['inherited_sources_mutated'])

    def test_undeclared_derivation_is_rejected(self):
        getsource=a.inspect.getsource
        def changed(fn):
            source=getsource(fn)
            return source.replace('lo,hi=hi,lo','lo,hi=lo,hi') if fn is a.value_walk else source
        with mock.patch.object(a.inspect,'getsource',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'undeclared value effect'):a.verify_derivation()


class ReturnClassification(unittest.TestCase):
    def setUp(self):self.values,self.typed=specimen('7b 60')
    def reject(self):
        with self.assertRaises(ValueError):a.classify(self.values,self.typed)

    def test_proved_return(self):
        row=a.classify(self.values,self.typed);self.assertEqual(row['status'],'proved-B0-D0-DBR7E')
        self.assertTrue(row['typed_source_and_return_contexts_match'])

    def test_unknown_b_stays_unproved(self):
        values,typed=specimen('ad 00 80 eb 60');r=a.classify(values,typed)
        self.assertEqual(r['status'],'B-return-not-proved');self.assertEqual(r['projected_b_values'],[None])
        self.assertTrue(r['unknown_b_is_not_a_demonstrated_nonzero_runtime_value'])

    def test_mixed_zero_and_unknown_return_is_not_promoted(self):
        values,typed=specimen('ad 00 80 eb f0 01 7b 60');r=a.classify(values,typed)
        self.assertEqual(r['projected_b_values'],[0,None]);self.assertFalse(r['b_zero_on_every_projected_return'])

    def test_wrong_entry_bank_rejects(self):self.values['entry_dbr']=0;self.reject()
    def test_unknown_entry_b_rejects(self):self.values['entry_b']=None;self.reject()
    def test_boolean_entry_b_rejects(self):self.values['entry_b']=False;self.reject()
    def test_wrong_entry_d_rejects(self):self.values['entry_d']=1;self.reject()
    def test_wrong_entry_width_rejects(self):self.values['entry_x8']=True;self.reject()
    def test_open_typed_target_rejects(self):self.typed['frontier']={'site':'$CD4000'};self.reject()
    def test_wrong_call_kind_rejects(self):self.values['kind']='long';self.reject()
    def test_source_interval_change_rejects(self):self.values['decoded_byte_intervals'][0]['sha256']='0'*64;self.reject()
    def test_source_context_change_rejects(self):self.values['decoded_context_identity_sha256']='0'*64;self.reject()
    def test_missing_direct_call_rejects(self):self.values['direct_calls'].append({'site':'$CD4000'});self.reject()
    def test_mnemonic_coverage_change_rejects(self):self.values['mnemonic_context_counts']['TDC']=99;self.reject()
    def test_missing_return_rejects(self):self.values['ends']=[];self.reject()
    def test_wrong_return_site_rejects(self):self.values['ends'][0]['site']='$CD4000';self.reject()
    def test_wrong_return_width_rejects(self):self.values['ends'][0]['m8']=False;self.reject()
    def test_boolean_return_b_rejects(self):self.values['ends'][0]['b']=False;self.reject()
    def test_float_return_d_rejects(self):self.values['ends'][0]['d']=0.0;self.reject()
    def test_unknown_return_dbr_rejects(self):self.values['ends'][0]['dbr']=None;self.reject()
    def test_unconsumed_return_frame_rejects(self):self.values['ends'][0]['frames']=[{'kind':'near'}];self.reject()
    def test_float_stack_count_rejects(self):self.values['ends'][0]['counted_stack_bytes']=0.0;self.reject()
    def test_alias_promotion_rejects(self):self.values['nonstack_memory_and_dma_effects_proved']=True;self.reject()
    def test_termination_promotion_rejects(self):self.values['termination_proved']=True;self.reject()
    def test_opaque_callee_claim_rejects(self):self.values['all_direct_callees_inlined']=False;self.reject()


if __name__=='__main__':unittest.main()
