"""Original tiny instruction fixtures for the bounded scroll value projection.

No game bytes are fixtures. These prove host refusal/abstraction behavior; the
canonical claim separately requires the complete pinned source reproduction.
"""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_nmi_scroll_inputs_v1 as a


def fixture(raw,other=(),entry=0xC00000,kind='near',**kwargs):
    memory={entry+i:value for i,value in enumerate(bytes.fromhex(raw))}
    for base,text in other:
        for i,value in enumerate(bytes.fromhex(text)):
            if base+i in memory:raise ValueError('original fixture overlap')
            memory[base+i]=value
    def read(pc,n):
        try:return bytes(memory[x] for x in range(pc,pc+n))
        except KeyError:raise ValueError('fixture control flow/read outside declared source') from None
    return a.value_walk(read,entry,kind,**kwargs)


class Projection(unittest.TestCase):
    def only(self,raw,**kwargs):
        r=fixture(raw,**kwargs);self.assertEqual(len(r['ends']),1);return r['ends'][0]

    def test_byte_lda_preserves_unknown_hidden_b(self):
        r=self.only('a9 7e 60');self.assertIsNone(r['b']);self.assertEqual(r['a_low'],126)

    def test_byte_lda_preserves_known_hidden_b(self):
        self.assertEqual(self.only('a9 7e 60',entry_b=73)['b'],73)

    def test_word_lda_sets_b(self):
        r=self.only('c2 20 a9 34 12 e2 20 60');self.assertEqual((r['a_low'],r['b']),(52,18))

    def test_tdc_clears_b_even_under_m8(self):
        r=self.only('7b 60',entry_b=99);self.assertEqual((r['a_low'],r['b'],r['d']),(0,0,0))

    def test_bank_publish_requires_actual_low_a(self):
        r=self.only('a9 7e 48 ab 60');self.assertEqual(r['dbr'],126);self.assertIsNone(r['b'])

    def test_byte_stack_order_and_saved_bank(self):
        r=self.only('8b a9 41 48 ab ab 60',entry_dbr=126);self.assertEqual(r['dbr'],126)

    def test_word_stack_order(self):
        r=self.only('c2 20 a9 34 12 48 a9 ff ff 68 e2 20 60')
        self.assertEqual((r['a_low'],r['b']),(52,18))

    def test_byte_pla_retains_hidden_b(self):
        r=self.only('a9 44 48 a9 55 68 60',entry_b=7);self.assertEqual((r['a_low'],r['b']),(68,7))

    def test_memory_load_cannot_supply_known_bank(self):
        r=self.only('ad 00 80 48 ab 60',entry_dbr=126);self.assertIsNone(r['dbr'])

    def test_word_memory_load_forgets_b(self):
        r=self.only('c2 20 ad 00 80 e2 20 60',entry_b=0);self.assertIsNone(r['b'])

    def test_byte_arithmetic_preserves_b_but_forgets_low(self):
        r=self.only('a9 01 18 69 01 60',entry_b=3);self.assertEqual(r['b'],3);self.assertIsNone(r['a_low'])

    def test_word_arithmetic_forgets_b(self):
        self.assertIsNone(self.only('c2 20 a9 01 00 18 69 01 00 e2 20 60')['b'])

    def test_txa_conservatively_forgets_visible_width(self):
        self.assertEqual(self.only('a2 00 00 8a 60',entry_b=5)['b'],5)
        self.assertIsNone(self.only('c2 20 a2 00 00 8a e2 20 60',entry_b=5)['b'])

    def test_flags_never_prune_branch(self):
        r=fixture('a9 00 f0 04 a9 41 80 02 a9 7e 48 ab 60')
        self.assertEqual({e['dbr'] for e in r['ends']},{65,126})

    def test_near_call_is_inlined(self):
        r=self.only('20 10 00 60',other=((0xC00010,'7b 60'),),entry_b=9)
        self.assertEqual(r['b'],0)

    def test_long_call_is_inlined(self):
        r=self.only('22 00 00 c1 60',other=((0xC10000,'7b 6b'),),entry_b=9)
        self.assertEqual(r['b'],0)

    def test_far_tail_jump_with_long_root(self):
        r=self.only('5c 00 00 c1',other=((0xC10000,'7b 6b'),),kind='long');self.assertEqual(r['b'],0)

    def test_mvn_destination_bank_and_post_a(self):
        r=self.only('c2 20 a9 00 00 54 7e ce e2 20 60')
        self.assertEqual((r['a_low'],r['b'],r['dbr']),(255,255,126))

    def test_mvn_followed_by_tdc_and_bank_restore(self):
        r=self.only('8b c2 20 a9 1d 00 54 7e ce 7b e2 20 ab 60',entry_dbr=0)
        self.assertEqual((r['b'],r['dbr']),(0,0))

    def test_mvn_m8_rejected(self):
        with self.assertRaises(ValueError):fixture('54 7e ce 60')

    def test_mvn_x8_rejected(self):
        with self.assertRaises(ValueError):fixture('c2 20 e2 10 54 7e ce e2 20 60')

    def test_d_changing_instructions_reject(self):
        for raw in ('5b 60','2b 60'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):fixture(raw)

    def test_unsupported_saved_status_rejects(self):
        with self.assertRaises(ValueError):fixture('08 28 60')

    def test_indexed_dispatch_rejects(self):
        for raw in ('7c 00 80','fc 00 80'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):fixture(raw)

    def test_stack_pointer_or_emulation_change_rejects(self):
        for raw in ('1b 60','9a 60','fb 60'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):fixture(raw)

    def test_irq_unmask_rejects(self):
        for raw in ('58 60','c2 04 60'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):fixture(raw)

    def test_software_pop_cannot_consume_near_frame(self):
        with self.assertRaises(ValueError):fixture('68 60')

    def test_wrong_return_kind_rejects(self):
        with self.assertRaises(ValueError):fixture('6b')

    def test_unbalanced_data_on_return_rejects(self):
        with self.assertRaises(ValueError):fixture('48 60')

    def test_near_return_cannot_change_pbr(self):
        with self.assertRaises(ValueError):fixture('5c 00 00 c1',other=((0xC10000,'60'),))

    def test_nonreturning_loop_rejects(self):
        with self.assertRaises(ValueError):fixture('80 fe')

    def test_budget_refuses_growth(self):
        with self.assertRaises(ValueError):fixture('48 80 fd',budget=5)

    def test_bank_boundary_instruction_rejects(self):
        with self.assertRaises(ValueError):fixture('a9 00 60',entry=0xC0FFFF)

    def test_branch_into_operand_rejects(self):
        with self.assertRaises(ValueError):fixture('f0 01 a9 a9 00 60')

    def test_boolean_byte_rejects(self):
        with self.assertRaises(ValueError):fixture('60',entry_b=False)

    def test_conditional_stop_keeps_frame(self):
        r=self.only('7b',stops=(0xC00001,));self.assertEqual(r['counted_stack_bytes'],2)
        self.assertEqual(r['frames'],[{'return':'abstract-caller','kind':'near'}])


class Recipe(unittest.TestCase):
    def test_four_cell_addresses(self):
        self.assertEqual([a.pointer_recipe(v,0)['pointer_low'] for v in range(4)],
                         [0xCD06BC,0xCD06BE,0xCD06C0,0xCD06C2])

    def test_high_ca92_bit_aliases_all_b_values(self):
        for b in range(256):
            for v in range(128):
                low=a.pointer_recipe(v,b);high=a.pointer_recipe(v+128,b)
                self.assertEqual((low['x'],low['pointer_low'],low['pointer_high']),
                                 (high['x'],high['pointer_low'],high['pointer_high']))

    def test_b_is_not_discarded(self):
        self.assertNotEqual(a.pointer_recipe(2,1)['pointer_low'],a.pointer_recipe(2,0)['pointer_low'])

    def test_even_index_prevents_word_boundary_wrap(self):
        for b in range(256):
            for v in range(128):
                r=a.pointer_recipe(v,b);self.assertEqual(r['pointer_high'],r['pointer_low']+1)

    def test_base_addition_wrap_keeps_pbr(self):
        r=a.pointer_recipe(34,249);self.assertEqual(r['pointer_low'],0xCD0000)

    def test_nonbyte_values_reject(self):
        for v,b in ((True,0),(0,False),(-1,0),(256,0),(0,256),(0,None),(1.0,0)):
            with self.subTest(v=v,b=b),self.assertRaises(ValueError):a.pointer_recipe(v,b)


class CallerAcceptance(unittest.TestCase):
    def setUp(self):
        end={'site':'$CD0929','kind':'stop','m8':True,'x8':False,'irq_masked':True,
             'b':0,'d':0,'dbr':126,'counted_stack_bytes':2,
             'frames':[{'return':'abstract-caller','kind':'near'}]}
        other=copy.deepcopy(end);other['site']='$CD0907'
        self.row={'entry':'$CD088D','kind':'near','entry_b':None,'entry_d':0,'entry_dbr':0,
                  'ends':[end,other]}

    def test_exact_bounded_contract(self):
        result=a.verify_caller(self.row)
        self.assertFalse(result['other_branch_returns_or_rejoins_proved'])
        self.assertFalse(result['callee_register_preservation_assumed'])
        self.assertFalse(result['ca92_value_domain_proved'])

    def test_nonzero_or_unknown_b_rejects(self):
        for value in (1,None,False,0.0):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.row['ends'][0]['b']=value;a.verify_caller(self.row)

    def test_d_or_dbr_not_established_rejects(self):
        for key,value in (('d',1),('d',False),('dbr',0),('dbr',None)):
            row=copy.deepcopy(self.row);row['ends'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):a.verify_caller(row)

    def test_width_or_i_changed_rejects(self):
        for key,value in (('m8',False),('x8',True),('irq_masked',False),('m8',1)):
            row=copy.deepcopy(self.row);row['ends'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):a.verify_caller(row)

    def test_stale_frame_or_extra_software_save_rejects(self):
        for change in ({'counted_stack_bytes':3},{'frames':[{'return':'$CD1234','kind':'near'}]}):
            row=copy.deepcopy(self.row);row['ends'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):a.verify_caller(row)

    def test_missing_selected_branch_rejects(self):
        self.row['ends']=self.row['ends'][1:]
        with self.assertRaises(ValueError):a.verify_caller(self.row)

    def test_unreviewed_other_exit_rejects(self):
        self.row['ends'][1]['site']='$CD092C'
        with self.assertRaises(ValueError):a.verify_caller(self.row)


if __name__=='__main__':unittest.main()
