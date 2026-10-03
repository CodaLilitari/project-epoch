"""Original instruction miniatures and adversarial conditional compositions.

No ROM, extracted game stream or native trace is a fixture. The small anchored
D miniature deliberately differs from the game's body and branch topology.
"""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene80_remaining_returns_v2 as a


def miniature(program,entry=0xCD4000):
    def read(p,n):
        off=p-entry
        return bytes(program[off:off+n]) if 0<=off<len(program) else bytes(n)
    return read


def d_miniature(changes=None):
    # Original long body: prescribed save/setup/restore anchors, an INY runway,
    # arbitrary ADC operand and a late two-way branch. It contains no game data.
    base=0xD1F108
    data=bytearray([0xC8]*(0xD1F1B0-base))
    def put(pc,raw):data[pc-base:pc-base+len(raw)]=bytes(raw)
    put(base,[0x0B,0xA2,0x00,0x0A,0xDA,0x2B,0xE2,0x10,0xA0,0x00])
    put(0xD1F112,[0x75,0x80,0x29,0x3F,0xBB,0xE8,0xAD,0x20,0x31])
    put(0xD1F11B,[0x99,0x40,0x52])
    put(0xD1F15F,[0xD0,0x45])  # either restore at 161 or six INYs at 1A6.
    put(0xD1F161,[0x2B,0xC2,0x10,0x6B])
    put(0xD1F1AC,[0x2B,0xC2,0x10,0x6B])
    for pc,raw in (changes or {}).items():put(pc,raw)
    return miniature(data,base)


class Derivation(unittest.TestCase):
    def test_exact_two_extensions_without_mutation(self):
        old=copy.deepcopy(a.handlers.FIXED)
        walker,decode,value,receipt=a.derive_models()
        self.assertEqual(a.handlers.FIXED,old)
        self.assertEqual(set(receipt['new_fixed_entries']),{'$44','$75'})
        self.assertFalse(receipt['typed_control_algorithm_changed'])
        self.assertEqual(decode(miniature([0x44,0x32,0x43]),0xCD4000,False,False)[:2],(0x44,'MVP'))
        self.assertEqual(decode(miniature([0x75,0x80]),0xCD4000,True,True)[:2],(0x75,'ADC dp,X'))

    def test_derivation_rejects_no_match_or_multiple_matches(self):
        for source in ('nothing','xx xx'):
            with self.subTest(source=source),self.assertRaises(ValueError):a.replace_once(source,'xx','yy')

    def test_no_implicit_generic_phd_pld_value_support(self):
        _,_,value,_=a.derive_models()
        with self.assertRaisesRegex(ValueError,'unsupported value effect 0B'):
            value(miniature([0x0B,0x2B,0x60]),0xCD4000,'near',entry_b=0,entry_dbr=126)

    def test_adc_byte_preserves_b_and_word_adc_forgets_it(self):
        _,_,value,_=a.derive_models()
        for program,b in (([0x75,0x21,0x60],0x71),([0xC2,0x20,0x75,0x21,0xE2,0x20,0x60],None)):
            row=value(miniature(program),0xCD4000,'near',entry_b=0x71,entry_dbr=126)
            self.assertEqual(row['ends'][0]['b'],b)
            self.assertIsNone(row['ends'][0]['a_low'])

    def test_mvp_write_inventory_has_unknown_transfer_width(self):
        walker,_,_,_=a.derive_models()
        row=walker(miniature([0xC2,0x20,0x44,0x32,0x43,0xE2,0x20,0x60]),0xCD4000,'near')
        self.assertIsNone(row['frontier'])
        self.assertEqual(len(row['syntactic_write_operands']),1)
        write=row['syntactic_write_operands'][0]
        self.assertEqual(write['mnemonic'],'MVP')
        self.assertIsNone(write['width_bytes'])
        self.assertIs(write['effective_address_and_aliasing_proved'],False)

    def test_value_mvp_completes_full_a_and_first_operand_bank(self):
        _,_,value,_=a.derive_models()
        row=value(miniature([0xC2,0x20,0x44,0x32,0x43,0xE2,0x20,0x60]),0xCD4000,'near',entry_b=0,entry_dbr=126)
        end=row['ends'][0]
        self.assertEqual((end['a_low'],end['b'],end['dbr']),(255,255,0x32))

    def test_later_tdc_resets_b_after_mvp(self):
        walker,_,value,_=a.derive_models()
        read=miniature([0xC2,0x20,0x44,0x7E,0x32,0x7B,0xE2,0x20,0x60])
        row=a.prior.validate_closed(walker(read,0xCD4000,'near'),value(read,0xCD4000,'near',entry_b=0,entry_dbr=126))
        self.assertEqual(row['status'],'proved-B0-D0-DBR7E')

    def test_unrestored_b_after_mvp_is_not_b0(self):
        walker,_,value,_=a.derive_models()
        read=miniature([0xC2,0x20,0x44,0x7E,0x32,0xE2,0x20,0x60])
        with self.assertRaisesRegex(ValueError,'return unproved'):
            a.prior.validate_closed(walker(read,0xCD4000,'near'),value(read,0xCD4000,'near',entry_b=0,entry_dbr=126))

    def test_mvp_value_refuses_either_byte_width(self):
        _,_,value,_=a.derive_models()
        for program in ([0x44,0x7E,0x7E,0x60],[0xC2,0x20,0xE2,0x10,0x44,0x7E,0x7E,0x60]):
            with self.subTest(program=program),self.assertRaisesRegex(ValueError,'native M16/X16'):
                value(miniature(program),0xCD4000,'near',entry_b=0,entry_dbr=126)


class BlockMove(unittest.TestCase):
    def test_counter_and_index_wrap_for_all_word_counts(self):
        for counter in range(65536):
            row=a.mvp_completion(counter,0x0193,0xFF07,0x42)
            count=counter+1
            self.assertEqual((row['count'],row['a'],row['x'],row['y'],row['dbr']),
                (count,65535,(0x0193-count)%65536,(0xFF07-count)%65536,0x42))

    def test_one_byte_and_full_65536_byte_endpoints(self):
        self.assertEqual(a.mvp_completion(0,0,0,0)['x'],65535)
        row=a.mvp_completion(65535,37,59,255)
        self.assertEqual((row['count'],row['x'],row['y']),(65536,37,59))
        self.assertEqual(row['stack_bytes'],0)
        self.assertFalse(row['d_changed'])
        self.assertFalse(row['memory_alias_or_effective_address_ownership_proved'])

    def test_word_type_and_bounds_refuse(self):
        for index in range(3):
            for bad in (True,1.,None,-1,65536):
                args=[1,2,3,126];args[index]=bad
                with self.subTest(index=index,bad=bad),self.assertRaises(ValueError):a.mvp_completion(*args)

    def test_destination_type_and_bounds_refuse(self):
        for bad in (True,1.,None,-1,256):
            with self.subTest(bad=bad),self.assertRaises(ValueError):a.mvp_completion(1,2,3,bad)

    def test_widths_are_exact_false(self):
        for key in ('m8','x8'):
            for bad in (True,0,None):
                with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):a.mvp_completion(1,2,3,126,**{key:bad})


class TemporaryD(unittest.TestCase):
    def setUp(self):self.walk,self.decode,_,_=a.derive_models()
    def project(self,changes=None,**kwargs):return a.d_routine_projection(d_miniature(changes),self.decode,**kwargs)
    def test_original_body_has_both_balanced_restores(self):
        row=self.project();control=self.walk(d_miniature(),0xD1F108,'long')
        a.compare_d_projection(control,row)
        self.assertEqual(row['return_d'],0)
        self.assertFalse(row['d_is_zero_throughout_body'])
        self.assertEqual(row['maximum_counted_bytes_including_long_frame'],7)
        self.assertEqual(row['d_transitions'],[
            {'site':'$D1F10D','before':0,'after':0xA00,'stack_bytes_after':5},
            {'site':'$D1F161','before':0xA00,'after':0,'stack_bytes_after':3},
            {'site':'$D1F1AC','before':0xA00,'after':0,'stack_bytes_after':3}])

    def test_entry_types_values_and_widths_refuse(self):
        for key,values in {'entry_b':[None,1,False,0.], 'entry_d':[1,False,0.],
                          'entry_dbr':[0,126.], 'm8':[False,1], 'x8':[True,0]}.items():
            for bad in values:
                with self.subTest(key=key,bad=bad),self.assertRaises(ValueError):self.project(**{key:bad})

    def test_wrong_temporary_d_immediate_refuses(self):
        with self.assertRaisesRegex(ValueError,'temporary-D immediate'):self.project({0xD1F10A:[0x01]})

    def test_unsaved_original_d_cannot_restore_from_frame(self):
        with self.assertRaises(ValueError):self.project({0xD1F108:[0xC8]})

    def test_unsaved_temporary_x_cannot_be_substituted_by_original_d(self):
        with self.assertRaises(ValueError):self.project({0xD1F10C:[0xC8]})

    def test_m16_change_is_not_silently_projected(self):
        with self.assertRaisesRegex(ValueError,'only X-width'):self.project({0xD1F10F:[0x30]})

    def test_extra_software_save_at_unreviewed_site_refuses(self):
        with self.assertRaisesRegex(ValueError,'exact original D save'):self.project({0xD1F11E:[0x0B]})

    def test_unmodeled_tdc_with_temporary_d_is_refused(self):
        with self.assertRaisesRegex(ValueError,'unreviewed D-routine effect 7B'):self.project({0xD1F11E:[0x7B]})

    def test_missing_either_d_restore_refuses(self):
        for pc in (0xD1F161,0xD1F1AC):
            with self.subTest(pc=pc),self.assertRaises(ValueError):self.project({pc:[0xC8]})

    def test_wrong_return_kind_refuses(self):
        for pc in (0xD1F164,0xD1F1AF):
            with self.subTest(pc=pc),self.assertRaises(ValueError):self.project({pc:[0x60]})

    def test_x8_return_refuses(self):
        with self.assertRaises(ValueError):self.project({0xD1F162:[0xE2]})

    def test_branch_outside_owned_extent_refuses(self):
        with self.assertRaisesRegex(ValueError,'exact D-routine source extent'):self.project({0xD1F112:[0xD0,0x80]})

    def test_branch_into_an_operand_refuses(self):
        with self.assertRaises(ValueError):self.project({0xD1F112:[0xD0,0xF5]})

    def test_opcode_and_extent_must_be_owned(self):
        with self.assertRaises(ValueError):self.project({0xD1F11E:[0xFB]})


class Composition(unittest.TestCase):
    def setUp(self):
        walk,decode,_,_=a.derive_models();read=d_miniature()
        self.control=walk(read,0xD1F108,'long');self.value=a.d_routine_projection(read,decode)
    def reject(self):
        with self.assertRaises(ValueError):a.compare_d_projection(self.control,self.value)
    def test_original_control_and_value_agree(self):a.compare_d_projection(self.control,self.value)
    def test_wrong_entry_or_kind(self):
        for key,bad in [('entry','$D1F109'),('kind','near')]:
            with self.subTest(key=key):
                old=self.value[key];self.value[key]=bad;self.reject();self.value[key]=old
    def test_all_scalar_contract_values_have_exact_types(self):
        for key in ('entry_b','entry_d','entry_dbr','return_b','return_d','return_dbr'):
            with self.subTest(key=key):
                old=self.value[key];self.value[key]=float(old);self.reject();self.value[key]=old
    def test_full_context_inventory_disagreement_refuses(self):
        for key,bad in [('instruction_contexts',0),('decoded_context_identity_sha256','0'*64),
                        ('decoded_byte_intervals',[]),('mnemonic_context_counts',{}),
                        ('direct_calls',[{}]),('return_width_states',[])]:
            with self.subTest(key=key):
                old=self.value[key];self.value[key]=bad;self.reject();self.value[key]=old
    def test_stack_bound_numeric_type_and_value_refuse(self):
        for bad in (True,7.,6,8):
            with self.subTest(bad=bad):self.value['maximum_counted_bytes_including_long_frame']=bad;self.reject()
    def test_claimed_global_or_termination_authority_refuses(self):
        for key in ('d_is_zero_throughout_body','body_data_values_proved',
                    'nonstack_aliases_and_asynchronous_preservation_proved','termination_proved'):
            with self.subTest(key=key):self.value[key]=True;self.reject();self.value[key]=False
    def test_no_return_or_branch_coverage_claim_refuses(self):
        for key in ('branch_conditions_overapproximated','all_return_paths_checked'):
            with self.subTest(key=key):self.value[key]=False;self.reject();self.value[key]=True
    def test_changed_or_missing_d_transition_refuses(self):
        original=copy.deepcopy(self.value['d_transitions'])
        for bad in (original[:-1],list(reversed(original)),[] ):
            with self.subTest(bad=bad):self.value['d_transitions']=bad;self.reject()
        self.value['d_transitions']=original
        self.value['d_transitions'][0]['after']=0
        self.reject()
    def test_float_or_boolean_saved_d_is_not_an_exact_word(self):
        for bad in (False,0.):
            with self.subTest(bad=bad):self.value['d_transitions'][0]['before']=bad;self.reject()
    def test_canonical_identity_rejected_before_any_derivation(self):
        with mock.patch.object(a,'derive_models',side_effect=AssertionError('must refuse first')):
            for bad in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.subTest(kind=type(bad)),self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(bad,{}, {})


if __name__=='__main__':unittest.main()
