"""Original synthetic prefix recipes and fail-closed mode-index boundaries."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_nmi_mode_inputs_v1 as a


class ModeIndex(unittest.TestCase):
    def test_all_pairs_preserve_b_and_wrap_low_shift(self):
        for b in range(256):
            for mode in range(256):
                c=a.index_contract(mode,b)
                self.assertEqual(c['x'],b*256+(mode*2)%256)
                self.assertEqual(c['pointer_byte_addresses'],
                    [0xCD0000|((0x0C83+c['x'])&65535),0xCD0000|((0x0C84+c['x'])&65535)])
                self.assertFalse(c['mode_reachability_proved'])

    def test_high_modes_alias_low_modes_under_same_b(self):
        for b in (0,1,0xFF):
            for mode in range(128):
                self.assertEqual(a.index_contract(mode,b)['pointer_byte_addresses'],a.index_contract(mode+128,b)['pointer_byte_addresses'])

    def test_reviewed_three_cells_have_six_byte_aliases(self):
        self.assertEqual([m for m in range(256) if a.index_contract(m)['x'] in (0,2,4)], [0,1,2,128,129,130])

    def test_pointer_word_bank_wrap(self):
        self.assertEqual(a.index_contract(0xBE,0xF3)['pointer_byte_addresses'],[0xCDFFFF,0xCD0000])

    def test_mode_three_selects_occupied_wrapper_start(self):
        self.assertEqual(a.index_contract(3)['pointer_byte_addresses'],[0xCD0C89,0xCD0C8A])

    def test_exact_types(self):
        for bad in (True,False,0.0,-1,256,None,'0'):
            with self.assertRaises(ValueError):a.index_contract(bad)
            with self.assertRaises(ValueError):a.index_contract(0,bad)


class Prefix(unittest.TestCase):
    BASE=0xC00000
    TARGET=0xC10000

    def fixture(self,changes=None):
        # Authored toy sequence: two arbitrary RAM copies and one near-end
        # symbolic read differ from the canonical source under audit.
        parts=[('widths','c230'),('save_a','48'),('save_x','da'),('save_y','5a'),('save_bank','8b'),('save_d','0b'),
            ('zero','a90000'),('d','5b'),('byte','e220'),('busy','a57f'),('branch','f000'),('busy_inc','e67f'),
            ('word','c230'),('x','a20500'),('y','a07777'),('count','a90200'),('move','547e7f'),
            ('unknown','ad3412'),('tdc','7b'),('byte2','e220'),('bankpush','48'),('bankpull','ab'),
            ('unknown8','ad3f21'),('value','a980'),('call','220000c1')]
        changes=changes or {};raw=bytearray();sites={}
        for key,code in parts:
            sites[key]=self.BASE+len(raw);raw.extend(bytes.fromhex(changes.get(key,code)))
        def read(pc,n):return bytes(raw[pc-self.BASE:pc-self.BASE+n])
        return read,dict(entry=self.BASE,end=self.BASE+len(raw),call=sites['call'],target=self.TARGET,busy_site=sites['busy'])

    def run_fixture(self,changes=None,**kwargs):
        read,args=self.fixture(changes);return a.prefix(read,**args,**kwargs)

    def test_symbolic_entry_registers_and_all_widths_converge(self):
        for m8 in (False,True):
            for x8 in (False,True):
                r=self.run_fixture(entry_m8=m8,entry_x8=x8)
                self.assertEqual(r['frontier_register_bytes'],{'a':[128,0],'x':[8,0],'y':[122,119],'d':[0,0],'dbr':[0]})
                self.assertEqual(r['conditional_bytes_below_interrupted_sp'],16)
                self.assertEqual(r['software_saved_bytes'],9)
                self.assertEqual(r['prefix_peak_stack_bytes'],16)
                self.assertFalse(r['memory_aliases_solved'])
                self.assertFalse(r['whole_nmi_bound_proved'])
                self.assertFalse(r['asynchronous_entry_or_physical_stack_ownership_proved'])

    def test_mvn_uses_count_plus_one_and_distinct_source_destination(self):
        r=self.run_fixture();m=r['block_moves'][0]
        self.assertEqual((m['count'],m['source_start'],m['source_end_exclusive'],m['destination_start'],m['destination_end_exclusive']),
            (3,'7F0005','7F0008','7E7777','7E777A'))

    def test_missing_final_tdc_preserves_unknown_high_byte(self):
        r=self.run_fixture({'tdc':'','unknown8':'af3f2100'})
        self.assertIsInstance(r['frontier_register_bytes']['a'][1],str)
        self.assertNotEqual(r['frontier_register_bytes']['a'],[128,0])

    def test_tdc_reads_full_nonzero_d(self):
        # A nonzero D changes the busy effective address and must refuse
        # instead of applying the physical $007F premise elsewhere.
        with self.assertRaisesRegex(ValueError,'busy premise'):
            self.run_fixture({'zero':'a90100'})

    def test_busy_nonzero_is_not_forced_through_normal_path(self):
        for b in (1,255,False,0.0):
            with self.assertRaises(ValueError):self.run_fixture(busy_value=b)

    def test_unreviewed_branch_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'branch lacks'):
            self.run_fixture({'branch':'af3f2100f000'})

    def test_status_irq_mutation_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'status'):
            self.run_fixture({'widths':'c234'})

    def test_index_load_flags_cannot_reuse_stale_busy_zero(self):
        for instruction in ('a00100','a20100'):
            with self.assertRaisesRegex(ValueError,'branch lacks'):
                self.run_fixture({'branch':instruction+'f002'})

    def test_tcd_and_plb_flags_replace_prior_zero(self):
        for instruction in ('a901a200005b','a90148a900ab'):
            with self.assertRaisesRegex(ValueError,'branch lacks'):
                self.run_fixture({'branch':instruction+'f002'})

    def test_repeated_busy_increment_refuses(self):
        with self.assertRaisesRegex(ValueError,'repeated direct-page'):
            self.run_fixture({'busy_inc':'e67fe67f'})

    def test_busy_alias_store_refuses(self):
        with self.assertRaisesRegex(ValueError,'busy premise'):
            self.run_fixture({'busy_inc':'8f7f0000e67f'})

    def test_unknown_effect_is_rejected(self):
        with self.assertRaises(ValueError):self.run_fixture({'value':'eb'})

    def test_unsupported_early_call_rejected(self):
        with self.assertRaisesRegex(ValueError,'unreviewed call'):
            self.run_fixture({'unknown':'220000c1'})

    def test_block_move_width_and_wrap_boundaries_refuse(self):
        for changes in ({'move':'e210547e7f'},{'count':'a90001'},{'x':'a2ffff'},{'y':'a0ffff'}):
            with self.assertRaises(ValueError):self.run_fixture(changes)

    def test_truncated_and_escaped_prefix_refuse(self):
        read,args=self.fixture()
        with self.assertRaises(ValueError):a.prefix(lambda pc,n:b'',**args)
        with self.assertRaises(ValueError):self.run_fixture({'branch':'f07f'})

    def test_budget_and_exact_width_types_refuse(self):
        for kwargs in ({'budget':1},{'budget':True},{'budget':0},{'entry_m8':0},{'entry_x8':1}):
            with self.assertRaises(ValueError):self.run_fixture(**kwargs)

    def test_canonical_guard_precedes_claims(self):
        for raw in (b'',bytes(0x400000),bytearray(0x400000)):
            with self.assertRaisesRegex(ValueError,'canonical ROM identity'):a.audit(raw)


if __name__=='__main__':unittest.main()
