"""Only the new canonical packet/builtin/native-return acceptance boundary."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_mesen_pc07_field_entry_v1 as field


class FieldEntryCaptureTests(unittest.TestCase):
    def fixture(self):
        packet=bytes((i*17+3)&255 for i in range(2361));builtins=bytes(range(134))
        wram=bytearray(0x20000);wram[0x12000:0x12000+len(packet)]=packet
        wram[0x13700:0x13700+len(builtins)]=builtins;wram[0x6FC:0x6FE]=b'\x11\x01'
        row={'cpu':{'k':0xC0,'pc':0x5D36,'d':0x100,'dbr':0,'emulationMode':False,'ps':0x20,'sp':0x6FB},
             'location':0x1DA,'stored_near_return':0x111}
        return wram,row,packet,builtins

    def test_exact_packet_builtin_and_real_stack_preimage(self):
        wram,row,packet,builtins=self.fixture()
        field.check_ready_snapshot(bytes(wram),row,packet,builtins)

    def test_packet_or_builtin_snapshot_mismatch_refuses(self):
        for address in (0x12000,0x12938,0x13700,0x13785):
            wram,row,packet,builtins=self.fixture();wram[address]^=1
            with self.subTest(address=address),self.assertRaisesRegex(ValueError,'packet mismatch|builtin mismatch'):
                field.check_ready_snapshot(bytes(wram),row,packet,builtins)

    def test_claimed_return_word_cannot_replace_actual_stack_bytes(self):
        wram,row,packet,builtins=self.fixture();wram[0x6FD]^=1
        with self.assertRaisesRegex(ValueError,'near return stack bytes'):
            field.check_ready_snapshot(bytes(wram),row,packet,builtins)

    def test_different_dp_or_next_instruction_context_refuses(self):
        for key,value in (('d',0),('pc',0x112),('ps',0x30)):
            wram,row,packet,builtins=self.fixture();row['cpu'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'native context'):
                field.check_ready_snapshot(bytes(wram),row,packet,builtins)


if __name__=='__main__':unittest.main()
