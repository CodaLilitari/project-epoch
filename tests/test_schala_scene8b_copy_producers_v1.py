"""Authored finite instruction specimens and independent boundary expectations."""
from pathlib import Path
import copy
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene8b_copy_producers_v1 as a


def memory_reader():
    memory={}
    def put(p,raw):
        for i,v in enumerate(raw):
            assert p+i not in memory
            memory[p+i]=v
    def read(p,n):
        try:return bytes(memory[p+i] for i in range(n))
        except KeyError:raise ValueError('outside original specimen') from None
    return memory,put,read


def producer(start=0xCD352D,arithmetic=None,y=2):
    """Tiny authored producer: input reads, chosen arithmetic, parity and count."""
    memory,put,read=memory_reader();spec=a.PRODUCERS[start]
    prefix=bytes.fromhex('AD AA CA AA BD A4 CA A8 84 45 BD A8 CA A8 84 47 C2 20')
    arithmetic=bytes.fromhex('A9 08 00') if arithmetic is None else arithmetic
    raw=prefix+b'\xA9'+y.to_bytes(2,'little')+b'\xA8'+arithmetic+bytes.fromhex('85 4B 64 4F')
    put(start,raw);p=start+len(raw)
    put(p,b'\x18\x90'+bytes([spec['mask']-3-(p+3)]))
    tail=bytes.fromhex('AD AA CA 29 01 00 0A 85 45 A5 4F 0A 0A 18 65 45 AA')
    tail+=bytes.fromhex('C4 4B F0 03') if spec['conditional'] else b''
    put(spec['mask']-3,tail+bytes.fromhex('20 16 36'))
    put(0xCD3616,bytes.fromhex('84 45 A5 4B 38 E5 45 85 4B 0A 18 65 4B 85 4B A9 C7 E7 38 E5 4B 85 4B'))
    return memory,read


def return_specimen():
    memory,put,read=memory_reader()
    for p,raw in ((a.copy.RTS,b'\x60'),(0xCEE7CB,b'\x6B'),(0xCD3644,b'\x80\x10'),(0xCD3656,b'\x60')):
        put(p,raw)
    return memory,read


def historical_specimen():
    targets=[]
    for target,continuation in (('$CD33B5','$CD3612'),('$CD33BB','$CD35A1'),('$CD33C1','$CD34F1'),('$CD33CD','$CD3612')):
        targets.append({'target':target,'control':{'frontier':{
            'site':'$CEE7CC','counted_stack_bytes_at_frontier':9,
            'incoming_width_state':{'m8':False,'x8':False,'irq_masked':True},
            'active_call_return_sites':[{'return':p,'kind':k} for p,k in (
                ('abstract-caller','near'),(continuation,'near'),('$CD3644','long'),('$CEE7CB','near'))]}}})
    return {'open_targets':[v['target'] for v in targets],'selected_targets':targets}


class Inputs(unittest.TestCase):
    def test_all_q_geometry_and_exact_four_aliases(self):
        rows=[a.geometry(q) for q in range(256)]
        self.assertEqual([v['q'] for v in rows if v['aliases']],[2,3,6,7])
        self.assertEqual(rows[255]['r_address'],0x7ECBA3)
        self.assertEqual(rows[255]['s_address'],0x7ECBA7)
    def test_q_aliases_keep_input_and_word_part(self):
        self.assertEqual([(q,a.geometry(q)['aliases'][0]['input'],a.geometry(q)['aliases'][0]['word_part'])
            for q in (2,3,6,7)],[(2,'s','low'),(3,'s','high'),(6,'r','low'),(7,'r','high')])
    def test_each_alias_refuses_independent_input_contract(self):
        for start in a.PRODUCERS:
            for q in (2,3,6,7):
                with self.subTest(start=start,q=q),self.assertRaisesRegex(ValueError,'aliases'):
                    a.input_contract(start,q,0,0)
    def test_q_high_bit_is_preserved_in_source_addresses(self):
        self.assertEqual(a.geometry(128)['r_address']-a.geometry(0)['r_address'],128)
        self.assertEqual(a.geometry(128)['parity'],a.geometry(0)['parity'])
    def test_all_other_q_values_admitted_as_conditional_parameters(self):
        for q in range(256):
            if q not in a.EXCLUDED_Q:a.input_contract(0xCD352D,q,255,255)
    def test_bad_q_types_and_range_refuse(self):
        for q in (True,-1,256,0.0,None):
            with self.subTest(q=q),self.assertRaises(ValueError):a.geometry(q)
    def test_bad_start_types_and_namespace_refuse(self):
        for start in (True,0xCD352D+1,float(0xCD352D),0xCD1F53):
            with self.subTest(start=start),self.assertRaises(ValueError):a.input_contract(start,0,0,0)
    def test_wrong_register_or_decimal_premises_refuse(self):
        for kw in ({'b':1},{'d':1},{'dbr':0},{'decimal':True},{'decimal':0}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):a.input_contract(0xCD352D,0,0,0,**kw)
    def test_nonbyte_selected_inputs_refuse(self):
        for r,s in ((True,0),(0,True),(-1,0),(0,256),(0.0,0)):
            with self.subTest(r=r,s=s),self.assertRaises(ValueError):a.input_contract(0xCD352D,0,r,s)
    def test_distinct_formula_and_floor_boundaries(self):
        self.assertEqual(a.count_formula(0xCD35A5,111,111),222)
        self.assertEqual(a.count_formula(0xCD352D,111,111),166)
        self.assertEqual(a.count_formula(0xCD347D,111,111),166)
        for start in a.PRODUCERS:
            self.assertEqual(a.count_formula(start,255,32),-1)
            self.assertEqual(a.count_formula(start,255,33),0)
            self.assertEqual(a.count_formula(start,255,0),-33)


class Instructions(unittest.TestCase):
    def test_original_arithmetic_and_pointer(self):
        _,read=producer();v=a.evaluate(read,0xCD352D,0,17,23)
        self.assertEqual(v['doubled_count'],6);self.assertEqual(v['pointer'],0xE7B5)
        self.assertEqual(v['frame_returns'],[0xCD35A1])
    def test_lsr_word_does_not_truncate_high_byte(self):
        _,read=producer(arithmetic=bytes.fromhex('A9 01 80 4A'),y=0)
        self.assertEqual(a.evaluate(read,0xCD352D,0,0,0)['doubled_count'],0x4000)
    def test_lsr_low_bit_sets_carry_consumed_by_adc(self):
        for word,expected in ((0,0),(1,1),(2,1),(3,2),(65535,32768)):
            _,read=producer(arithmetic=b'\xA9'+word.to_bytes(2,'little')+bytes.fromhex('4A 69 00 00'),y=0)
            v=a.evaluate(read,0xCD352D,0,0,0)
            self.assertEqual(v['doubled_count'],expected)
            self.assertEqual(v['skipped'],expected==0)
    def test_cpy_beq_true_skips_only_conditional_producers(self):
        for start in a.PRODUCERS:
            _,read=producer(start,y=8);v=a.evaluate(read,start,0,0,0)
            self.assertEqual(v['skipped'],a.PRODUCERS[start]['conditional'])
            self.assertEqual(v['doubled_count'],0)
            self.assertEqual(v['pointer'],None if v['skipped'] else 0xE7C7)
    def test_cpy_uses_full_y_word(self):
        _,read=producer(y=0x108);v=a.evaluate(read,0xCD352D,0,0,0)
        self.assertFalse(v['skipped']);self.assertEqual(v['doubled_count'],0xFF00)
    def test_all_q_high_values_select_sources_and_only_parity_x(self):
        _,read=producer()
        for q in range(256):
            if q in a.EXCLUDED_Q:continue
            v=a.evaluate(read,0xCD352D,q,17,23)
            self.assertEqual(v['x'],2*(q&1));self.assertEqual(v['y'],2)
            self.assertEqual(v['pointer'],0xE7B5)
            self.assertIn((0xCD3531,0x7ECAA4+q,1),v['source_reads'])
            self.assertIn((0xCD3537,0x7ECAA8+q,1),v['source_reads'])
    def test_changed_word_mask_refuses_unknown_high(self):
        memory,read=producer();memory[0xCD358E]=1
        with self.assertRaisesRegex(ValueError,'unknown word high'):a.evaluate(read,0xCD352D,0,0,0)
    def test_q_cannot_control_branch_before_mask(self):
        memory,read=producer();memory[0xCD3530]=0xF0;memory[0xCD3531]=0
        with self.assertRaisesRegex(ValueError,'q must not influence'):a.evaluate(read,0xCD352D,0,0,0)
    def test_nonzero_hidden_b_refuses_before_source_access(self):
        _,read=producer()
        with self.assertRaises(ValueError):a.evaluate(read,0xCD352D,0,0,0,b=1)
    def test_unknown_dp_read_refuses(self):
        _,read=producer(arithmetic=bytes.fromhex('A5 53'))
        with self.assertRaisesRegex(ValueError,'uninitialized producer DP'):a.evaluate(read,0xCD352D,0,0,0)
    def test_wrong_external_source_read_refuses(self):
        memory,read=producer();memory[0xCD3532]=0xA5
        with self.assertRaisesRegex(ValueError,'selected r/s'):a.evaluate(read,0xCD352D,0,0,0)
    def test_wrong_near_call_target_refuses(self):
        memory,read=producer();memory[0xCD359F]=0x17
        with self.assertRaisesRegex(ValueError,'near producer call'):a.evaluate(read,0xCD352D,0,0,0)
    def test_missing_final_pointer_writer_refuses(self):
        memory,read=producer();memory[0xCD362C]=0x49
        with self.assertRaisesRegex(ValueError,'final pointer byte'):a.evaluate(read,0xCD352D,0,0,0)
    def test_unsupported_instruction_refuses(self):
        memory,read=producer();memory[0xCD352D]=0xFB
        with self.assertRaises(ValueError):a.evaluate(read,0xCD352D,0,0,0)
    def test_uninitialized_branch_flag_refuses(self):
        memory,read=producer();memory[0xCD352D]=0xF0;memory[0xCD352E]=0
        with self.assertRaisesRegex(ValueError,'branch flag'):a.evaluate(read,0xCD352D,0,0,0)
    def test_unknown_high_cannot_reach_beq(self):
        memory,read=producer();memory[0xCD358C]=0xF0
        with self.assertRaisesRegex(ValueError,'unknown word high'):a.evaluate(read,0xCD352D,0,0,0)
    def test_q_taint_cannot_survive_into_count(self):
        memory,read=producer();memory[0xCD3617]=0x47
        with self.assertRaisesRegex(ValueError,'q must not reach doubled count'):a.evaluate(read,0xCD352D,1,0,0)
    def test_parity_must_not_be_transferred_to_source_y(self):
        memory,read=producer();memory[0xCD3599]=0xA8
        with self.assertRaisesRegex(ValueError,'q must not influence producer control'):a.evaluate(read,0xCD352D,1,0,0)
    def test_finite_budget_refuses_a_cycle(self):
        memory,read=producer();memory[0xCD352D]=0x18;memory[0xCD352E]=0x90;memory[0xCD352F]=0xFD
        with self.assertRaisesRegex(ValueError,'budget'):a.evaluate(read,0xCD352D,0,0,0)


class SourceAndPostcopy(unittest.TestCase):
    def factorization_specimen(self):
        memory={}
        for start in a.PRODUCERS:
            part,_=producer(start)
            for p,v in part.items():
                self.assertTrue(p not in memory or memory[p]==v);memory[p]=v
        return memory,lambda p,n:bytes(memory[p+i] for i in range(n))
    def test_exact_q_source_templates_and_all_address_geometry(self):
        _,read=self.factorization_specimen();v=a.factorization(read)
        self.assertEqual(v['admitted_q_count'],252)
        self.assertEqual(v['excluded_q'],[2,3,6,7])
        self.assertEqual(len(v['source_use_contracts']),3)
        self.assertFalse(v['sixteen_million_case_execution_claim'])
    def test_source_mask_drift_refuses(self):
        memory,read=self.factorization_specimen();memory[0xCD358D]=3
        with self.assertRaisesRegex(ValueError,'parity to X'):a.factorization(read)
    def test_source_q_scratch_overwrite_drift_refuses(self):
        memory,read=self.factorization_specimen();memory[0xCD3617]=0x47
        with self.assertRaisesRegex(ValueError,'overwrites q-derived'):a.factorization(read)
    def test_source_cpy_beq_chain_drift_refuses(self):
        memory,read=self.factorization_specimen();memory[0xCD359C]=0x90
        with self.assertRaisesRegex(ValueError,'conditional skip'):a.factorization(read)
    def postcopy_specimen(self,target=None):
        memory,put,read=memory_reader();start=0xCD347D;entry=0xCD34F1;final=0xCD3529
        put(entry,b'\x80'+bytes([(final if target is None else target)-(entry+2)]))
        put(final,bytes.fromhex('7B E2 20 60'))
        return memory,read,start
    def test_half_postcopy_return_has_required_zero_and_width_restore(self):
        _,read,start=self.postcopy_specimen();v=a.postcopy_contract(read,start)
        self.assertTrue(v['return_b0_d0_dbr7e_conditionally'])
        self.assertFalse(v['termination_proved']);self.assertFalse(v['memory_effects_proved'])
    def test_half_postcopy_cannot_bypass_tdc(self):
        _,read,start=self.postcopy_specimen(0xCD352A)
        with self.assertRaisesRegex(ValueError,'owns TDC/SEP'):a.postcopy_contract(read,start)
    def test_half_postcopy_cannot_bypass_sep(self):
        _,read,start=self.postcopy_specimen(0xCD352C)
        with self.assertRaises(ValueError):a.postcopy_contract(read,start)
    def test_half_postcopy_wrong_final_tdc_refuses(self):
        memory,read,start=self.postcopy_specimen();memory[0xCD3529]=0xEA
        with self.assertRaisesRegex(ValueError,'cleanup TDC'):a.postcopy_contract(read,start)
    def test_emitter_unchanged_control_and_value_models_agree(self):
        memory,put,read=memory_reader();put(0xCD31FE,bytes.fromhex('7B E2 20 60'))
        v=a.emitter_contract(read,0xCD31FE,0xCD3201)
        self.assertEqual(v['classification']['status'],'proved-B0-D0-DBR7E')
        self.assertFalse(v['termination_proved'])
    def test_emitter_nonzero_b_return_refuses(self):
        memory,put,read=memory_reader();put(0xCD31FE,bytes.fromhex('C2 20 A9 00 FF E2 20 60'))
        with self.assertRaisesRegex(ValueError,'emitter return register'):a.emitter_contract(read,0xCD31FE,0xCD3205)


class ReturnAndHistory(unittest.TestCase):
    def test_three_producers_both_distinct_typed_return_routes(self):
        _,read=return_specimen()
        for start in a.PRODUCERS:
            for arm in (0,1):
                v=a.typed_copy_return(read,start,arm)
                self.assertEqual([x['counted_before'] for x in v['events']],[9,7,4])
                self.assertEqual([x['counted_after'] for x in v['events']],[7,4,2])
                self.assertEqual(v['postcopy_entry'],f"${a.PRODUCERS[start]['call']+3:06X}")
    def test_near_frame_cannot_be_consumed_by_far_return(self):
        memory,read=return_specimen();memory[a.copy.RTS]=0x6B
        with self.assertRaisesRegex(ValueError,'typed continuation'):a.typed_copy_return(read,0xCD352D,0)
    def test_long_frame_cannot_be_consumed_by_near_return(self):
        memory,read=return_specimen();memory[0xCEE7CB]=0x60
        with self.assertRaisesRegex(ValueError,'typed continuation'):a.typed_copy_return(read,0xCD352D,0)
    def test_wrong_parity_branch_refuses(self):
        memory,read=return_specimen();memory[0xCD3645]=0x11
        with self.assertRaisesRegex(ValueError,'parity continuation'):a.typed_copy_return(read,0xCD352D,1)
    def test_return_arm_must_be_exact_integer(self):
        _,read=return_specimen()
        for arm in (True,2,None):
            with self.subTest(arm=arm),self.assertRaises(ValueError):a.typed_copy_return(read,0xCD352D,arm)
    def test_all_four_historical_frontiers_preserved(self):
        v=a.preserved_frontiers(historical_specimen());self.assertEqual(len(v),4)
        self.assertEqual(v[2]['frontier']['active_call_return_sites'][1]['return'],'$CD34F1')
    def test_distinct_historical_continuation_cannot_be_swapped(self):
        v=historical_specimen();v['selected_targets'][2]['control']['frontier']['active_call_return_sites'][1]['return']='$CD35A1'
        with self.assertRaisesRegex(ValueError,'typed frame chain'):a.preserved_frontiers(v)
    def test_historical_wrong_stack_count_refuses(self):
        v=historical_specimen();v['selected_targets'][0]['control']['frontier']['counted_stack_bytes_at_frontier']=11
        with self.assertRaisesRegex(ValueError,'frontier/width/depth'):a.preserved_frontiers(v)
    def test_historical_width_change_refuses(self):
        v=historical_specimen();v['selected_targets'][0]['control']['frontier']['incoming_width_state']['m8']=True
        with self.assertRaises(ValueError):a.preserved_frontiers(v)
    def test_duplicate_historical_target_refuses(self):
        v=historical_specimen();v['selected_targets'].append(copy.deepcopy(v['selected_targets'][0]))
        with self.assertRaisesRegex(ValueError,'unique prior'):a.preserved_frontiers(v)
    def test_missing_historical_target_refuses(self):
        v=historical_specimen();v['selected_targets'].pop()
        with self.assertRaisesRegex(ValueError,'unique prior'):a.preserved_frontiers(v)
    def test_wrong_open_target_inventory_refuses(self):
        v=historical_specimen();v['open_targets'].reverse()
        with self.assertRaisesRegex(ValueError,'four open target'):a.preserved_frontiers(v)
    def test_noncanonical_rom_refuses_before_projection(self):
        for raw in (b'',bytes(0x400000),bytearray(0x400000)):
            with self.assertRaisesRegex(ValueError,'ROM identity'):a.audit(raw)


if __name__=='__main__':unittest.main()
