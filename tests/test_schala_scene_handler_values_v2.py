"""Original branch specimens for three explicit word-load zero refinements."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene_handler_values_v2 as a


def specimen(branch=0xD1FA49,*,word=True,load_opcode=0xA5,operand=None,
             branch_opcode=0xF0,target_delta=0,fall_tdc=True,entry_b=0,entry_at_branch=False,
             alternate_predecessor=False):
    load,target,expected_operand=a.REFINEMENTS[branch]
    memory={}
    def put(pc,blob):
        for i,value in enumerate(blob):
            if pc+i in memory:raise AssertionError('overlapping original specimen')
            memory[pc+i]=value
    put(load,[load_opcode,expected_operand if operand is None else operand])
    put(branch,[branch_opcode,(target+target_delta-(branch+2))&255])
    put(branch+2,([0x7B] if fall_tdc else [])+[0xE2,0x20,0x60])
    put(target,[0xE2,0x20,0x60])
    entry=load
    if word:
        entry=load-2;put(entry,[0xC2,0x20])
    if entry_at_branch:entry=branch
    if alternate_predecessor:
        entry=0xD1F000;put(entry,[0xC2,0x20,0x4C,branch&255,branch>>8&255])
    def read(pc,n):
        try:return bytes(memory[x] for x in range(pc,pc+n))
        except KeyError:raise ValueError('outside original specimen') from None
    return read,entry,dict(entry_b=entry_b,entry_dbr=126)


class ZeroEdges(unittest.TestCase):
    def run_model(self,**kwargs):
        read,entry,args=specimen(**kwargs);return a.value_walk(read,entry,'near',**args)

    def test_all_three_word_zero_edges_prove_b_zero(self):
        for branch in a.REFINEMENTS:
            r=self.run_model(branch=branch)
            self.assertEqual({x['b'] for x in r['ends']},{0})
            self.assertEqual(len(r['refined_zero_edges']),1)
            self.assertFalse(r['refined_zero_edges'][0]['m8'])
            self.assertTrue(r['refined_zero_edges'][0]['both_successors_retained'])

    def test_taken_edge_assigns_both_a_bytes(self):
        r=self.run_model(fall_tdc=False,entry_b=99)
        taken=a.REFINEMENTS[0xD1FA49][1]+2
        target=next(x for x in r['ends'] if x['site']==a.cpu(taken))
        self.assertEqual((target['a_low'],target['b']),(0,0))

    def test_fallthrough_remains_conservatively_unknown(self):
        r=self.run_model(fall_tdc=False)
        self.assertEqual({x['b'] for x in r['ends']},{0,None})
        self.assertEqual(len(r['ends']),2)

    def test_preserved_v1_retains_unknown_branch(self):
        read,entry,args=specimen()
        r=a.base.value_walk(read,entry,'near',**args)
        self.assertEqual({x['b'] for x in r['ends']},{0,None})

    def test_m8_load_cannot_prove_full_a_zero(self):
        with self.assertRaisesRegex(ValueError,'exact immediate M16 LDA'):self.run_model(word=False)

    def test_direct_entry_at_beq_refuses_without_predecessor(self):
        with self.assertRaises(ValueError):self.run_model(entry_at_branch=True)

    def test_jump_into_beq_refuses_stale_zero_provenance(self):
        with self.assertRaisesRegex(ValueError,'exact immediate M16 LDA'):self.run_model(alternate_predecessor=True)

    def test_ldx_predecessor_cannot_supply_accumulator_zero(self):
        with self.assertRaisesRegex(ValueError,'exact immediate M16 LDA'):self.run_model(load_opcode=0xA6)

    def test_other_direct_page_operand_refuses(self):
        with self.assertRaisesRegex(ValueError,'exact immediate M16 LDA'):self.run_model(operand=0x46)

    def test_bne_is_not_a_zero_edge(self):
        with self.assertRaisesRegex(ValueError,'refined site must decode BEQ'):self.run_model(branch_opcode=0xD0)

    def test_unconditional_branch_cannot_borrow_refinement(self):
        with self.assertRaisesRegex(ValueError,'refined site must decode BEQ'):self.run_model(branch_opcode=0x80)

    def test_changed_taken_target_refuses(self):
        with self.assertRaisesRegex(ValueError,'exact immediate M16 LDA'):self.run_model(target_delta=1)

    def test_other_beq_is_unchanged(self):
        raw=bytes.fromhex('c2 20 a5 45 f0 01 7b e2 20 60');entry=0xCD4000
        read=lambda p,n:raw[p-entry:p-entry+n]
        r=a.value_walk(read,entry,'near',entry_b=0,entry_dbr=126)
        self.assertEqual({x['b'] for x in r['ends']},{0,None});self.assertEqual(r['refined_zero_edges'],[])

    def test_both_branches_keep_same_typed_source_contexts(self):
        for branch in a.REFINEMENTS:
            read,entry,args=specimen(branch)
            old=a.base.value_walk(read,entry,'near',**args);new=a.value_walk(read,entry,'near',**args)
            for key in ('decoded_context_identity_sha256','decoded_byte_intervals','direct_calls','edge_identity_sha256'):
                self.assertEqual(new[key],old[key])

    def test_exact_ast_delta(self):
        r=a.verify_derivation();self.assertTrue(r['only_declared_ast_changes'])
        self.assertFalse(r['global_zero_flag_tracking_added'])

    def test_undeclared_refinement_change_rejects(self):
        getsource=a.inspect.getsource
        def changed(fn):
            text=getsource(fn)
            return text.replace('edge_lo,edge_hi=(0,0)','edge_lo,edge_hi=(1,0)') if fn is a.value_walk else text
        with mock.patch.object(a.inspect,'getsource',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'undeclared v2 model change'):a.verify_derivation()

    def test_rom_identity_rejects_before_any_new_walk(self):
        with mock.patch.object(a,'value_walk',side_effect=AssertionError('must not walk')):
            for raw in (b'',bytes(0x400000),bytearray(0x400000)):
                with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(raw,{}, {})

    def test_scope_stays_bounded(self):
        for key in ('all_122_cells_or_all_scene_handlers_value_closed','complete_legal_command_or_script_domain_proved',
                    'nonstack_alias_closure','production_approval','new_native_execution','global_zero_flag_tracking_added'):
            self.assertIs(a.LIMITS[key],False)
        self.assertIsNone(a.LIMITS['whole_nmi_stack_bound'])


if __name__=='__main__':unittest.main()
