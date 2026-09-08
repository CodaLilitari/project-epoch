"""Original instruction specimens; no native trace or extracted fixture bytes."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene_copy_pointer_v1 as a


def synthetic_producer(prefix=b'\xC2\x20\xA9\x03\x00\x85\x4B',subtract=0):
    memory={}
    def put(p,raw):
        for i,v in enumerate(raw):
            assert p+i not in memory
            memory[p+i]=v
    put(a.START,prefix)
    p=a.START+len(prefix)
    put(p,b'\x18\x90'+bytes([0xCD360F-(p+3)]))
    put(0xCD360F,bytes.fromhex('20 16 36'))
    # Compute count=2*the original input word-subtract, then pointer E7C7-3*count.
    put(0xCD3616,bytes.fromhex('A5 4B 0A 38 E9')+subtract.to_bytes(2,'little'))
    put(0xCD361D,bytes.fromhex('85 4B 0A 18 65 4B 85 4B A9 C7 E7 38 E5 4B 85 4B'))
    def read(p,n):
        try:return bytes(memory[p+i] for i in range(n))
        except KeyError:raise ValueError('outside original producer specimen') from None
    return memory,read


def synthetic_ladder():
    memory={a.RTS:0x60}
    for n in range(1,257):
        raw=b'\xB9'+(2*(n-1)).to_bytes(2,'little')+b'\x9D'+(4*(n-1)).to_bytes(2,'little')
        memory.update({a.RTS-6*n+i:v for i,v in enumerate(raw)})
    for p in range(a.RTS-6*257,a.RTS-6*256):memory[p]=0
    return memory,lambda p,n:bytes(memory[x] for x in range(p,p+n))


def synthetic_return():
    memory={}
    for p,raw in ((a.RTS,b'\x60'),(0xCEE7CB,b'\x6B'),(0xCD3644,b'\x80\x10'),
                  (0xCD3656,b'\x60'),(0xCD3612,b'\x7B\xE2\x20\x60'),(0xCD1F9F,b'\x60')):
        memory.update({p+i:v for i,v in enumerate(raw)})
    return memory,lambda p,n:bytes(memory[x] for x in range(p,p+n))


class Inputs(unittest.TestCase):
    def test_all_byte_endpoints_accepted(self):
        for r,s in ((0,0),(0,255),(255,0),(255,255)):a.input_contract(r,s)
    def test_bad_scalar_types_and_range_refuse(self):
        for v in (True,0.0,-1,256,None):
            with self.subTest(v=v),self.assertRaises(ValueError):a.input_contract(v,0)
    def test_nonzero_b_refuses_hidden_index(self):
        with self.assertRaises(ValueError):a.input_contract(0,0,b=1)
    def test_nonzero_d_refuses_pointer_mismatch(self):
        with self.assertRaises(ValueError):a.input_contract(0,0,d=1)
    def test_wrong_dbr_refuses_source_namespace(self):
        with self.assertRaises(ValueError):a.input_contract(0,0,dbr=0)
    def test_decimal_or_nonboolean_mode_refuses(self):
        for v in (True,0,None):
            with self.subTest(v=v),self.assertRaises(ValueError):a.input_contract(0,0,decimal=v)
    def test_integer_closed_form_crossing_boundaries(self):
        for r,s,n in ((0,222,0),(0,223,-1),(255,32,-1),(255,33,0),(111,111,222),(255,255,222)):
            self.assertEqual(a.closed_form(r,s),n)


class Instructions(unittest.TestCase):
    def test_original_producer_exact_count_and_pointer(self):
        _,read=synthetic_producer();r=a.evaluate(read,0,0)
        self.assertEqual(r['doubled_count'],6);self.assertEqual(r['pointer'],0xE7B5)
        self.assertEqual(r['frame_returns'],[0xCD3612]);self.assertFalse(r['m8'])
    def test_binary_borrow_wrap_is_retained(self):
        _,read=synthetic_producer(subtract=7);r=a.evaluate(read,0,0)
        self.assertEqual(r['doubled_count'],65535);self.assertEqual(r['pointer'],0xE7CA)
    def test_binary_adc_carry_and_inc_wrap(self):
        prefix=bytes.fromhex('C2 20 A9 FF FF 38 69 00 00 1A 85 4B')
        _,read=synthetic_producer(prefix);self.assertEqual(a.evaluate(read,0,0)['doubled_count'],2)
    def test_uninitialized_dp_read_refuses(self):
        _,read=synthetic_producer(bytes.fromhex('C2 20 A5 49 85 4B'))
        with self.assertRaisesRegex(ValueError,'uninitialized'):a.evaluate(read,0,0)
    def test_unknown_external_address_refuses(self):
        _,read=synthetic_producer(bytes.fromhex('AD A5 CA C2 20 85 4B'))
        with self.assertRaisesRegex(ValueError,'external producer'):a.evaluate(read,0,0)
    def test_other_call_target_refuses(self):
        memory,read=synthetic_producer();memory[0xCD3610]=0x17
        with self.assertRaisesRegex(ValueError,'near producer call'):a.evaluate(read,0,0)
    def test_unsupported_opcode_refuses(self):
        memory,read=synthetic_producer();memory[a.START]=0xFB
        with self.assertRaises(ValueError):a.evaluate(read,0,0)
    def test_entry_at_loop_exhausts_finite_budget(self):
        memory,read=synthetic_producer();memory[a.START]=0x18;memory[a.START+1]=0x90;memory[a.START+2]=0xFD
        with self.assertRaisesRegex(ValueError,'budget'):a.evaluate(read,0,0)
    def test_uninitialized_carry_refuses(self):
        _,read=synthetic_producer(bytes.fromhex('C2 20 A9 00 00 69 00 00 85 4B'))
        with self.assertRaisesRegex(ValueError,'carry read'):a.evaluate(read,0,0)
    def test_uninitialized_index_refuses(self):
        _,read=synthetic_producer(bytes.fromhex('BD A4 CA C2 20 85 4B'))
        with self.assertRaisesRegex(ValueError,'X read'):a.evaluate(read,0,0)
    def test_uninitialized_branch_flag_refuses(self):
        memory,read=synthetic_producer();memory[a.START]=0x90;memory[a.START+1]=0
        with self.assertRaisesRegex(ValueError,'branch flag'):a.evaluate(read,0,0)
    def test_changed_final_store_operand_refuses(self):
        memory,read=synthetic_producer();memory[0xCD362C]=0x49
        with self.assertRaisesRegex(ValueError,'final pointer'):a.evaluate(read,0,0)
    def masked_specimen(self):
        memory,read=synthetic_producer()
        p=a.START+7;memory[p+2]=0xCD35FE-(p+3)
        for i,v in enumerate(bytes.fromhex('AD AA CA 29 01 00 18 90 08')):memory[0xCD35FE+i]=v
        return memory,read
    def test_word_read_masks_unknown_caab_before_use(self):
        _,read=self.masked_specimen();r=a.evaluate(read,0,0)
        self.assertIn((0xCD35FE,0x7ECAAA,2),r['source_reads'])
        self.assertEqual(r['doubled_count'],6)
    def test_changed_unknown_high_mask_refuses(self):
        memory,read=self.masked_specimen();memory[0xCD3603]=1
        with self.assertRaisesRegex(ValueError,'unknown word high'):a.evaluate(read,0,0)
    def test_branch_cannot_observe_placeholder_word_flag(self):
        memory,read=self.masked_specimen();memory[0xCD3601]=0x90
        with self.assertRaisesRegex(ValueError,'unknown word high'):a.evaluate(read,0,0)
    def test_branch_into_existing_operand_refuses(self):
        memory,read=synthetic_producer();memory[a.START+9]=(-7)&255
        with self.assertRaisesRegex(ValueError,'overlap'):a.evaluate(read,0,0)
    def test_width_dependent_length_refuses(self):
        raw=bytes.fromhex('A9 01 C2 20 18 90 F9')
        read=lambda p,n:raw[p-a.START:p-a.START+n]
        with self.assertRaisesRegex(ValueError,'width-dependent'):a.evaluate(read,0,0)


class Geometry(unittest.TestCase):
    def test_complete_original_geometry(self):
        _,read=synthetic_ladder();r=a.ladder(read)
        self.assertEqual(r['physical_pairs'],256);self.assertEqual(len(r['suffixes']),257)
        self.assertEqual(r['suffixes'][-1]['entry'],'$CEE1C7')
    def test_changed_load_opcode_refuses(self):
        memory,read=synthetic_ladder();memory[a.RTS-6]=0xBD
        with self.assertRaisesRegex(ValueError,'pair geometry'):a.ladder(read)
    def test_changed_store_stride_refuses(self):
        memory,read=synthetic_ladder();memory[a.RTS-12+4]=5
        with self.assertRaisesRegex(ValueError,'pair geometry'):a.ladder(read)
    def test_wrong_return_kind_refuses(self):
        memory,read=synthetic_ladder();memory[a.RTS]=0x6B
        with self.assertRaisesRegex(ValueError,'RTS'):a.ladder(read)
    def test_extra_physical_pair_refuses_fixed_extent(self):
        memory,read=synthetic_ladder()
        raw=b'\xB9\x00\x02\x9D\x00\x04'
        for i,v in enumerate(raw):memory[a.RTS-6*257+i]=v
        with self.assertRaisesRegex(ValueError,'extends beyond'):a.ladder(read)
    def test_rom_identity_refuses_before_projection(self):
        for raw in (b'',bytes(0x400000),bytearray(0x400000)):
            with self.assertRaisesRegex(ValueError,'ROM identity'):a.audit(raw)


class ReturnFrames(unittest.TestCase):
    def test_both_original_typed_chains_balance(self):
        _,read=synthetic_return()
        for arm in (0,1):
            r=a.return_path(read,arm)
            self.assertEqual([x['before_bytes'] for x in r],[11,9,6,4,2])
            self.assertEqual(r[-1]['after_bytes'],0)
    def test_wrong_near_return_kind_refuses(self):
        memory,read=synthetic_return();memory[a.RTS]=0x6B
        with self.assertRaisesRegex(ValueError,'frame mismatch'):a.return_path(read,0)
    def test_wrong_long_return_kind_refuses(self):
        memory,read=synthetic_return();memory[0xCEE7CB]=0x60
        with self.assertRaisesRegex(ValueError,'frame mismatch'):a.return_path(read,0)
    def test_wrong_branch_destination_refuses(self):
        memory,read=synthetic_return();memory[0xCD3645]=0x11
        with self.assertRaisesRegex(ValueError,'branch continuation'):a.return_path(read,1)
    def test_return_width_change_refuses(self):
        memory,read=synthetic_return();memory[0xCD3614]=0x10
        with self.assertRaisesRegex(ValueError,'SEP M8'):a.return_path(read,0)
    def test_missing_zero_restore_refuses(self):
        memory,read=synthetic_return();memory[0xCD3612]=0xEA
        with self.assertRaisesRegex(ValueError,'unsupported'):a.return_path(read,0)
    def test_noninteger_arm_refuses(self):
        _,read=synthetic_return()
        with self.assertRaisesRegex(ValueError,'continuation arm'):a.return_path(read,True)


if __name__=='__main__':unittest.main()
