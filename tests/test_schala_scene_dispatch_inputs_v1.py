"""Original bounded byte/index specimens; no game payload or runtime input."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene_dispatch_inputs_v1 as a


class IndexContracts(unittest.TestCase):
    def test_all_byte_routes_have_exact_counts(self):
        from collections import Counter
        self.assertEqual(Counter(a.classify(i) for i in range(256)),{'tilemap':127,'yield':1,'indexed-command':127,'stop':1})

    def test_route_boundaries(self):
        self.assertEqual([a.classify(i) for i in (0,0x7E,0x7F,0x80,0xF9,0xFA,0xFE,0xFF)],
            ['tilemap','tilemap','yield','indexed-command','indexed-command','indexed-command','indexed-command','stop'])

    def test_every_b_zero_command_uses_modulo_low_byte(self):
        for command in range(0x80,0xFF):
            c=a.index_contract(command,0)
            self.assertEqual(c['x'],2*(command-0x80))
            self.assertEqual(c['pointer_byte_addresses'],[0xCD16B5+2*(command-0x80),0xCD16B6+2*(command-0x80)])

    def test_hidden_b_is_not_silently_zero_extended(self):
        self.assertEqual(a.index_contract(0x80,0x41)['x'],0x4100)
        self.assertEqual(a.index_contract(0xFE,0xFF)['x'],0xFFFC)

    def test_every_hidden_b_and_command_pair_stays_in_program_bank(self):
        for b in range(256):
            for command in range(0x80,0xFF):
                c=a.index_contract(command,b)
                self.assertEqual(c['x'],b*256+2*(command&0x7F))
                self.assertTrue(all(p>>16==0xCD for p in c['pointer_byte_addresses']))

    def test_pointer_word_wraps_within_pbr(self):
        self.assertEqual(a.index_contract(0xA5,0xE9)['pointer_byte_addresses'],[0xCDFFFF,0xCD0000])

    def test_noncommands_refuse_indexing(self):
        for value in list(range(0x80))+[255]:
            with self.assertRaises(ValueError):a.index_contract(value,0)

    def test_exact_byte_types_and_ranges(self):
        for value in (False,True,0.0,-1,256,None):
            with self.assertRaises(ValueError):a.classify(value)
            with self.assertRaises(ValueError):a.index_contract(0x80,value)
            with self.assertRaises(ValueError):a.script_start_contract(value)

    def test_script_id_ff_is_initializer_sentinel(self):
        with self.assertRaises(ValueError):a.script_start_contract(255)

    def test_non_ff_script_ids_are_only_hypothetical_reads(self):
        for script_id in range(255):
            c=a.script_start_contract(script_id)
            self.assertEqual(c['x'],2*script_id)
            self.assertEqual(c['pointer_byte_addresses'],[0xD1646C+2*script_id,0xD1646D+2*script_id])
            self.assertFalse(c['complete_legal_id_domain_proved'])

    def test_script_start_widens_before_shift(self):
        self.assertEqual(a.script_start_contract(1,0x40)['x'],0x8002)
        self.assertEqual(a.script_start_contract(1,0x80)['x'],2)
        self.assertEqual(a.script_start_contract(0xFE,0x7F)['pointer_byte_addresses'],[0xD26468,0xD26469])


class PrefixAccumulatorProof(unittest.TestCase):
    BASE=0xC00000

    def run_prefix(self,code,*,frontier=None,entry_offset=0,hidden_b=None,budget=100):
        raw=bytes.fromhex(code)
        def read(pc,n):return raw[pc-self.BASE:pc-self.BASE+n]
        return a.first_indexed_b(read,entry=self.BASE+entry_offset,hidden_b=hidden_b,
            spans=((self.BASE,self.BASE+len(raw)),),frontier=self.BASE+(len(raw)-3 if frontier is None else frontier),calls=(),budget=budget)

    def test_tdc_then_byte_load_and_shift_proves_b_zero(self):
        r=self.run_prefix('7b a740 0a aa fcb516')
        self.assertTrue(r['all_frontier_hidden_b_zero'])
        self.assertFalse(r['command_handler_executed_or_summarized'])
        self.assertFalse(r['physical_stack_model'])

    def test_standalone_unknown_b_remains_open(self):
        r=self.run_prefix('a740 0a aa fcb516')
        self.assertTrue(r['frontier_hidden_b_can_be_unknown'])
        self.assertFalse(r['all_frontier_hidden_b_zero'])

    def test_nonzero_b_survives_byte_asl_and_tax(self):
        r=self.run_prefix('a740 0a aa fcb516',hidden_b=0xA5)
        self.assertEqual(r['frontier_hidden_b_values'],[0xA5])

    def test_word_load_then_byte_load_does_not_invent_zero_b(self):
        r=self.run_prefix('7b c220 a540 e220 a740 fcb516')
        self.assertTrue(r['frontier_hidden_b_can_be_unknown'])

    def test_later_tdc_recovers_zero_b(self):
        r=self.run_prefix('c220 a540 7b e220 a740 fcb516')
        self.assertTrue(r['all_frontier_hidden_b_zero'])

    def test_xba_can_move_unknown_low_byte_into_b(self):
        r=self.run_prefix('7b a740 eb fcb516')
        self.assertTrue(r['frontier_hidden_b_can_be_unknown'])

    def test_both_branch_paths_keep_unknown_path(self):
        r=self.run_prefix('d002 7b 18 fcb516')
        self.assertEqual(r['frontier_hidden_b_values'],[0])
        self.assertTrue(r['frontier_hidden_b_can_be_unknown'])

    def test_nonzero_direct_page_is_not_adopted(self):
        with self.assertRaises(ValueError):a.first_indexed_b(lambda *_:b'\x7b',direct_page=1)

    def test_status_change_outside_m_bit_refuses(self):
        with self.assertRaises(ValueError):self.run_prefix('c210 fcb516')

    def test_word_width_at_dispatch_refuses(self):
        with self.assertRaises(ValueError):self.run_prefix('c220 fcb516')

    def test_unknown_call_is_not_zero_cost_summary(self):
        with self.assertRaises(ValueError):self.run_prefix('200010 fcb516')

    def test_unmodeled_accumulator_pull_refuses(self):
        with self.assertRaises(ValueError):self.run_prefix('68 fcb516')

    def test_short_opcode_and_instruction_refuse(self):
        with self.assertRaises(ValueError):a.first_indexed_b(lambda *_:b'')
        with self.assertRaises(ValueError):self.run_prefix('a9')

    def test_source_escape_and_budget_refuse(self):
        with self.assertRaises(ValueError):self.run_prefix('8010 fcb516')
        with self.assertRaises(ValueError):self.run_prefix('7b 18 fcb516',budget=1)

    def test_finite_graph_is_not_a_termination_proof(self):
        r=self.run_prefix('80fe')
        self.assertFalse(r['frontier_reached'])
        self.assertFalse(r['termination_proved'])

    def test_noncanonical_images_reject_before_any_data_claim(self):
        for raw in (b'',bytes(0x400000),bytearray(0x400000)):
            with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(raw)


if __name__=='__main__':unittest.main()
