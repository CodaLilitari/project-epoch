"""Original instruction/value specimens for the requested DMA destination proof."""
from pathlib import Path
import sys
import unittest
import hashlib
import json
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import audit_schala_package_irq_dma7_contract_v3 as v

BASE = 0xC00000
SAVE = bytes.fromhex('08 0B 8B A9 00 48 AB A2 00 05 DA 2B E2 10 A0 80')
CONFIG = bytes.fromhex('A9 41 8D 70 43 A9 18 8D 71 43')
SIZE = bytes.fromhex('C2 20 9C 75 43 8C 75 43')
REQUEST = bytes.fromhex('8C 0B 42')
RESTORE = bytes.fromhex('E2 20 C2 10 AB 2B 28 6B')


def run(program):
    def read(address, count):
        return program[address-BASE:address-BASE+count]
    return v.project(read, entry=BASE, end=BASE+len(program))


def standard(config=CONFIG, size=SIZE, request=REQUEST, extra=b''):
    return SAVE + config + size + extra + request + RESTORE


class Destination(unittest.TestCase):
    def test_exact_request_is_two_ppu_ports(self):
        r=v.requested_destination(0x41,0x18,0x80,128)
        self.assertEqual(r['unique_bus_write_addresses'],[0x2118,0x2119])
        self.assertFalse(r['contains_wram_port_2180'])
        self.assertFalse(r['actual_transfer_completed'])
    def test_reverse_direction_refuses(self):
        with self.assertRaises(ValueError):v.requested_destination(0xC1,0x18,0x80,128)
    def test_wram_port_refuses(self):
        with self.assertRaises(ValueError):v.requested_destination(0x41,0x80,0x80,128)
    def test_multiple_or_wrong_channel_refuses(self):
        for mask in (0,1,0x81,0xFF):
            with self.subTest(mask=mask),self.assertRaises(ValueError):v.requested_destination(0x41,0x18,mask,128)
    def test_other_mode_or_configuration_refuses(self):
        for control in (0x40,0x42,0x49,0x51,1):
            with self.subTest(control=control),self.assertRaises(ValueError):v.requested_destination(control,0x18,0x80,128)
    def test_exact_numeric_types_required(self):
        for args in ((65.0,24,128,128),(65,True,128,128),(65,24,128,128.0),(65,24,128,True)):
            with self.subTest(args=args),self.assertRaises(ValueError):v.requested_destination(*args)
    def test_size_boundary_refuses(self):
        for size in (0,127,129,65536):
            with self.subTest(size=size),self.assertRaises(ValueError):v.requested_destination(65,24,128,size)


class AcceptedReference(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.value={'original_fixture':'IRQ evidence identity specimen'}
        self.raw=(json.dumps(self.value,indent=2)+'\n').encode('utf-8')
        self.path=self.root/v.IRQ_REFERENCE
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(self.raw)
        self.digest=hashlib.sha256(self.raw).hexdigest()
        self.patches=[patch.object(v,'ROOT',self.root),patch.object(v,'IRQ_REFERENCE_SHA256',self.digest)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
    def test_exact_original_reference_reproduces(self):
        self.assertEqual(v.verify_irq_reference(self.value),self.digest)
    def test_missing_reference_refuses(self):
        self.path.unlink()
        with self.assertRaisesRegex(ValueError,'unavailable'):v.verify_irq_reference(self.value)
    def test_reference_byte_drift_refuses(self):
        self.path.write_bytes(self.raw+b' ')
        with self.assertRaisesRegex(ValueError,'byte identity'):v.verify_irq_reference(self.value)
    def test_correct_reference_but_changed_reproduction_refuses(self):
        with self.assertRaisesRegex(ValueError,'no longer reproduces'):
            v.verify_irq_reference({'original_fixture':'changed interpretation'})


class ValueProjection(unittest.TestCase):
    def fails(self,program,pattern='.'):
        with self.assertRaisesRegex(ValueError,pattern):run(program)
    def test_original_complete_request_and_long_return(self):
        r=run(standard());self.assertEqual(len(r['request_contracts']),1)
        self.assertEqual(r['request_contracts'][0]['byte_count'],128)
        self.assertFalse(r['post_request_size_and_completion_assumed'])
    def test_all_four_last_writers_are_retained(self):
        r=run(standard())['request_contracts'][0]
        writers=r['last_cpu_configuration_writers']
        self.assertEqual(set(writers),{'$004370','$004371','$004375','$004376'})
        self.assertNotEqual(writers['$004375'],writers['$004376'])
    def test_unknown_control_rejects(self):
        self.fails(standard(config=bytes.fromhex('AD 00 30 8D 70 43 A9 18 8D 71 43')))
    def test_wrong_destination_rejects(self):
        self.fails(standard(config=bytes.fromhex('A9 41 8D 70 43 A9 80 8D 71 43')))
    def test_missing_high_size_initialization_rejects(self):
        self.fails(standard(size=bytes.fromhex('8C 75 43')),'size bytes')
    def test_nonzero_size_high_rejects(self):
        self.fails(standard(size=bytes.fromhex('C2 20 A9 00 01 8D 75 43 8C 75 43')),'128-byte')
    def test_high_size_overwrite_after_setup_rejects(self):
        self.fails(standard(extra=bytes.fromhex('E2 20 A9 01 8D 76 43')),'128-byte')
    def test_request_width_cannot_write_hdmaen_high_byte(self):
        self.fails(standard(extra=bytes.fromhex('C2 10')),'exact 8-bit STY')
    def test_only_exact_request_opcode_allowed(self):
        self.fails(standard(request=bytes.fromhex('E2 20 A9 80 8D 0B 42')),'exact 8-bit STY')
    def test_request_y_value_is_proved(self):
        self.fails(standard(extra=bytes.fromhex('A0 01')),'configuration')
    def test_unknown_y_is_not_replaced_with_default_request(self):
        # Removing LDY from original setup retains an arbitrary caller value.
        self.fails(SAVE[:-2]+CONFIG+SIZE+REQUEST+RESTORE,'size bytes')
    def test_unknown_request_value_refuses_even_with_explicit_size(self):
        explicit_size=bytes.fromhex('A9 80 8D 75 43 A9 00 8D 76 43')
        self.fails(SAVE[:-2]+CONFIG+explicit_size+REQUEST+RESTORE,'exact byte')
    def test_second_request_cannot_borrow_unproved_post_dma_size(self):
        self.fails(SAVE+CONFIG+SIZE+REQUEST+REQUEST+RESTORE,'size bytes')
    def test_second_request_reinitializes_its_own_size(self):
        r=run(SAVE+CONFIG+SIZE+REQUEST+SIZE+REQUEST+RESTORE)
        self.assertEqual(len(r['request_contracts']),2)
        self.assertNotEqual(r['request_contracts'][0]['last_cpu_configuration_writers']['$004375'],
                            r['request_contracts'][1]['last_cpu_configuration_writers']['$004375'])
    def test_other_channel_configuration_write_refuses(self):
        self.fails(standard(extra=bytes.fromhex('8D 60 43')),'unreviewed DMA')
    def test_hdma_enable_write_refuses(self):
        self.fails(standard(extra=bytes.fromhex('8C 0C 42')),'HDMA enable')
    def test_all_nonzero_hardware_mirror_banks_refuse_overwrite(self):
        for bank in list(range(1,0x40))+list(range(0x80,0xC0)):
            # Change DMAP7 through its mirror and restore DBR before request.
            extra=bytes.fromhex('E2 20 A9')+bytes([bank])+bytes.fromhex(
                '48 AB A9 C1 8D 70 43 A9 00 48 AB')
            with self.subTest(bank=bank):
                self.fails(standard(extra=extra),'hardware register mirror')
    def test_mirrored_request_hdma_count_and_other_channel_refuse(self):
        for address in (0x420B,0x420C,0x4371,0x4375,0x4376,0x4360,0x2118):
            extra=bytes.fromhex('E2 20 A9 80 48 AB A9 00 8D')+address.to_bytes(2,'little')
            extra+=bytes.fromhex('A9 00 48 AB')
            with self.subTest(address=address):
                self.fails(standard(extra=extra),'hardware register mirror')
    def test_high_byte_entering_hardware_mirror_refuses(self):
        # Word store begins outside the mapped range; its high byte enters it.
        for address in (0x1FFF,0x3FFF):
            extra=bytes.fromhex('E2 20 A9 80 48 AB C2 20 A9 00 00 8D')
            extra+=address.to_bytes(2,'little')+bytes.fromhex('E2 20 A9 00 48 AB')
            with self.subTest(address=address):
                self.fails(standard(extra=extra),'hardware register mirror')
    def test_full_wram_bank_is_not_hardware_mirror(self):
        for bank in (0x7E,0x7F):
            extra=bytes.fromhex('E2 20 A9')+bytes([bank])+bytes.fromhex(
                '48 AB A9 C1 8D 70 43 A9 00 48 AB')
            with self.subTest(bank=bank):
                self.assertEqual(len(run(standard(extra=extra))['request_contracts']),1)
    def test_zero_page_bank_select_must_be_known(self):
        p=SAVE.replace(bytes.fromhex('A9 00'),bytes.fromhex('A5 20'),1)
        self.fails(p+CONFIG+SIZE+REQUEST+RESTORE,'known DBR')
    def test_dp_selection_must_be_known(self):
        p=SAVE.replace(bytes.fromhex('A2 00 05'),bytes.fromhex('A6 20'),1)
        self.fails(p+CONFIG+bytes.fromhex('85 70')+SIZE+REQUEST+RESTORE,'known D')
    def test_wrong_saved_bank_cannot_fake_restoration(self):
        self.fails(standard()[:-5]+bytes.fromhex('A9 00 48 AB 2B 28 6B'))
    def test_unmodeled_status_pull_refuses(self):
        self.fails(bytes.fromhex('28 6B'),'typed PHP')
    def test_direct_call_is_not_assumed_preserving(self):
        self.fails(standard(extra=bytes.fromhex('20 00 00')),'unsupported service')
    def test_irq_unmasking_refuses(self):
        self.fails(standard(extra=bytes.fromhex('C2 04')),'unmasking')
    def test_both_branch_edges_keep_bad_setup_visible(self):
        # BNE skips a harmful one-byte mode change, while the other edge takes it.
        self.fails(standard(extra=bytes.fromhex('D0 07 E2 20 A9 C1 8D 70 43')),'configuration')
    def test_operand_entry_refuses(self):
        self.fails(standard(extra=bytes.fromhex('D0 01 A9 00 00')),'operand|overlapping')
    def test_incompatible_width_refuses(self):
        self.fails(standard(extra=bytes.fromhex('D0 02 E2 20 A9 00 00')),'incompatible')
    def test_memory_source_bytes_can_remain_unknown(self):
        r=run(standard(extra=bytes.fromhex('A5 B0 8D 72 43 A6 B4 8E 74 43')))
        self.assertFalse(r['dma_source_bank_offset_data_validity_proved'])


if __name__=='__main__':unittest.main()
