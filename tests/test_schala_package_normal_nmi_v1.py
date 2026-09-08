"""Independent tiny CPU fixtures; no ROM or extracted game data required."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import audit_schala_package_normal_nmi_v1 as nmi


BASE=0xC10000


def reader(raw):
    def read(pc,count):
        if pc<BASE: return b""
        return bytes(raw[pc-BASE:pc-BASE+count])
    return read


def busy_fixture():
    # An independently arranged native register-save example. There are no
    # game addresses, data pointers, mode services, hardware stores or vectors.
    code=bytearray.fromhex("C230 48 DA 5A 8B 0B A90000 5B E220 A57F")
    branch=BASE+len(code); code+=bytes.fromhex("F000 C230 2B AB 7A FA 68 40")
    return code,{"entry":BASE,"end":BASE+len(code),"busy_branch":branch,"rti":BASE+len(code)-1}


class BusyFastPathTests(unittest.TestCase):
    def test_all_native_widths_restore_symbolic_register_bytes(self):
        raw,kwargs=busy_fixture()
        for m in (False,True):
            for x in (False,True):
                with self.subTest(m=m,x=x):
                    r=nmi.busy_fast_path(reader(raw),entry_m8=m,entry_x8=x,**kwargs)
                    self.assertEqual(r["maximum_depth_including_hardware"],13)
                    self.assertIn("A including B",r["register_bytes_preserved"])

    def test_wrong_saved_register_refuses(self):
        raw,k=busy_fixture(); raw[2]=0xDA
        with self.assertRaisesRegex(nmi.NmiError,"restore exact register"):
            nmi.busy_fast_path(reader(raw),**k)

    def test_nonzero_direct_page_cannot_read_the_busy_byte(self):
        raw,k=busy_fixture(); raw[8]=1
        with self.assertRaisesRegex(nmi.NmiError,"exact bank-zero byte"):
            nmi.busy_fast_path(reader(raw),**k)

    def test_busy_branch_requires_nonzero_read(self):
        raw,k=busy_fixture(); raw[13]=0xA9; raw[14]=0
        with self.assertRaisesRegex(nmi.NmiError,"nonzero-busy premise"):
            nmi.busy_fast_path(reader(raw),**k)

    def test_irq_unmasking_refuses(self):
        raw,k=busy_fixture(); raw[1]|=4
        with self.assertRaisesRegex(nmi.NmiError,"interrupt-mask"):
            nmi.busy_fast_path(reader(raw),**k)

    def test_unknown_fast_path_instruction_refuses(self):
        raw,k=busy_fixture(); raw[2]=0xEA
        with self.assertRaisesRegex(nmi.NmiError,"unsupported opcode"):
            nmi.busy_fast_path(reader(raw),**k)

    def test_extra_pop_cannot_consume_hardware_frame(self):
        raw,k=busy_fixture(); raw[-1]=0x68
        with self.assertRaisesRegex(nmi.NmiError,"hardware frame"):
            nmi.busy_fast_path(reader(raw),**k)

    def test_wrong_final_stack_width_refuses(self):
        raw,k=busy_fixture(); raw[-8:-6]=bytes.fromhex("E220")
        with self.assertRaisesRegex(nmi.NmiError,"restore exact register"):
            nmi.busy_fast_path(reader(raw),**k)


class ConditionalFrontierTests(unittest.TestCase):
    def walk(self,hexcode,calls=None,ret=0x60):
        raw=bytes.fromhex(hexcode)
        region=nmi.Region("original-test",BASE,BASE+len(raw),18,ret)
        return nmi.local_frontiers(reader(raw),region,{} if calls is None else calls)

    def test_balanced_local_word_save(self):
        r=self.walk("C230 48 68 60")
        self.assertEqual(r["maximum_local_saved_bytes"],2)
        self.assertEqual(r["opaque_call_frontier_count"],0)
        self.assertIsNone(r["whole_callee_depth_bound"])

    def test_unknown_callee_is_not_silently_certified(self):
        r=self.walk("220000C2 60",{BASE:(0x22,0xC20000)})
        self.assertEqual(r["calls"][0]["conditional_depth_at_callee_entry"],21)
        self.assertIn("unproved",r["calls"][0]["continuation_premise"])
        self.assertIsNone(r["whole_callee_depth_bound"])

    def test_unreviewed_call_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"unreviewed call"):
            self.walk("220000C2 60")

    def test_call_target_drift_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"unreviewed call"):
            self.walk("220100C2 60",{BASE:(0x22,0xC20000)})

    def test_indexed_call_has_two_byte_frame_and_frontier(self):
        r=self.walk("FC0010 60",{BASE:(0xFC,0xC11000)})
        self.assertEqual(r["calls"][0]["kind"],"indexed-near")
        self.assertEqual(r["calls"][0]["call_frame_bytes"],2)

    def test_php_restores_local_width_after_opaque_call(self):
        r=self.walk("C230 08 220000C2 28 A93412 60",{BASE+3:(0x22,0xC20000)})
        self.assertEqual(r["instruction_starts"],6)

    def test_unknown_plp_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"PHP"):
            self.walk("48 28 60")

    def test_unbalanced_local_return_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"unbalanced local return"):
            self.walk("48 60")

    def test_span_escape_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"span escape"):
            self.walk("4C0010")

    def test_cross_span_instruction_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"short instruction"):
            self.walk("A9")

    def test_unmasking_refuses(self):
        with self.assertRaisesRegex(nmi.NmiError,"unmasks IRQ"):
            self.walk("C204 60")

    def test_store_x_width_uses_x_flag(self):
        r=self.walk("8643 60")
        self.assertEqual(r["syntactic_write_operands"][0]["width_bytes"],2)

    def test_mvn_has_register_selected_length(self):
        r=self.walk("547E7E 60")
        self.assertIsNone(r["syntactic_write_operands"][0]["width_bytes"])

    def test_branch_into_operand_is_not_a_valid_boundary(self):
        with self.assertRaises(nmi.NmiError): self.walk("F001 A960 60")

    def test_wrong_rom_identity_refuses_before_census(self):
        with self.assertRaisesRegex(nmi.NmiError,"exact canonical"):
            nmi.audit(bytes(0x400000))


if __name__=="__main__": unittest.main()
