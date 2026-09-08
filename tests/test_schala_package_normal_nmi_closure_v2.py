"""Original byte specimens for the bounded direct-callee walker; no game input."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import audit_schala_package_normal_nmi_closure_v2 as v
BASE=0xC00000


def specimen(parts):
    memory={}
    for address,data in parts.items():
        for i,value in enumerate(data):
            if address+i in memory:raise ValueError("overlapping original specimen")
            memory[address+i]=value
    def read(address,n):return bytes(memory.get(a,0) for a in range(address,address+n))
    return read


def walk(data,*,kind="near",entry=BASE,extra=None,**kwargs):
    return v.walk_direct(specimen({entry:bytes(data),**(extra or {})}),entry,kind,**kwargs)


class DirectClosureTests(unittest.TestCase):
    def closed(self,result,depth):
        self.assertEqual(result["status"],"closed-direct-stack-width-control-flow")
        self.assertIsNone(result["frontier"])
        self.assertEqual(result["maximum_additional_bytes_below_callee_entry"],depth)
        self.assertIsNone(result["whole_nmi_bound"])
        self.assertFalse(result["termination_proved"])
        self.assertFalse(result["nonstack_alias_closure"])
        self.assertTrue(result["premise_nonstack_writes_do_not_modify_stack_or_saved_status"])
    def frontier(self,result,category):
        self.assertEqual(result["status"],"open-frontier")
        self.assertEqual(result["frontier"]["category"],category)
        self.assertIsNone(result["maximum_additional_bytes_below_callee_entry"])
        self.assertIsNone(result["maximum_counted_bytes_including_root_call_frame"])
    def test_empty_near_leaf_has_proved_zero_local_depth(self):self.closed(walk([0x60]),0)
    def test_empty_long_leaf_has_proved_zero_local_depth(self):self.closed(walk([0x6B],kind="long"),0)
    def test_typed_status_and_all_native_saves_balance(self):
        r=walk([0x08,0xC2,0x30,0x48,0xDA,0x5A,0x0B,0x8B,0xAB,0x2B,0x7A,0xFA,0x68,0x28,0x6B],kind="long")
        self.closed(r,10);self.assertTrue(r["matches_prior_return_width_premise"])
    def test_accumulator_save_width_changes_depth(self):
        for m8,depth in ((True,1),(False,2)):self.closed(walk([0x48,0x68,0x60],entry_m8=m8),depth)
    def test_index_save_width_changes_depth(self):
        for x8,depth in ((True,1),(False,2)):self.closed(walk([0xDA,0xFA,0x60],entry_x8=x8),depth)
    def test_nested_near_and_long_frames_are_counted(self):
        r=walk([0x20,0x10,0,0x60],extra={BASE+0x10:bytes([0x22,0x20,0,0xC1,0x60]),0xC10020:bytes([0x48,0x68,0x6B])})
        self.closed(r,6);self.assertEqual(len(r["direct_calls"]),2)
    def test_long_far_tail_can_return_through_unchanged_long_frame(self):
        self.closed(walk([0x5C,0x10,0,0xC1],kind="long",extra={0xC10010:bytes([0x6B])}),0)
    def test_root_near_far_tail_cannot_restore_pbr(self):
        self.frontier(walk([0x5C,0x10,0,0xC1],extra={0xC10010:bytes([0x60])}),"near-return-bank-mismatch")
    def test_nested_near_far_tail_cannot_restore_pbr(self):
        self.frontier(walk([0x20,0x10,0,0x60],extra={BASE+0x10:bytes([0x5C,0x20,0,0xC1]),0xC10020:bytes([0x60])}),"near-return-bank-mismatch")
    def test_return_kind_is_exact(self):
        self.frontier(walk([0x6B]),"return-kind-mismatch")
        self.frontier(walk([0x60],kind="long"),"return-kind-mismatch")
    def test_software_pop_cannot_eat_return_bytes(self):self.frontier(walk([0x68,0x60]),"return-frame-consumed")
    def test_return_cannot_skip_local_save(self):self.frontier(walk([0x48,0x60]),"return-frame-mismatch")
    def test_untyped_plp_is_a_dataflow_frontier(self):self.frontier(walk([0x48,0x28,0x60]),"unknown-status-value")
    def test_pea_pair_and_phk_balance(self):self.closed(walk([0xF4,0,0,0x2B,0x4B,0xAB,0x60]),2)
    def test_pea_cannot_invent_typed_saved_status(self):self.frontier(walk([0xF4,0,0,0x28,0x60]),"unknown-status-value")
    def test_cli_refuses_even_with_later_sei(self):self.frontier(walk([0x58,0x78,0x60]),"irq-unmasking")
    def test_rep_irq_unmask_refuses(self):self.frontier(walk([0xC2,4,0x60]),"irq-unmasking")
    def test_xce_is_an_explicit_native_mode_frontier(self):self.frontier(walk([0xFB,0x60]),"processor-mode-transition")
    def test_sp_assignment_is_not_ordinary_register_transfer(self):
        for opcode in (0x1B,0x9A):self.frontier(walk([opcode,0x60]),"stack-pointer-assignment")
    def test_indexed_near_call_does_not_get_a_zero_depth_summary(self):self.frontier(walk([0xFC,0x20,0,0x60]),"indexed-call-dispatch")
    def test_indexed_jump_is_not_followed_as_a_direct_target(self):self.frontier(walk([0x7C,0x20,0]),"indexed-jump-dispatch")
    def test_indirect_long_control_flow_remains_unsupported(self):self.frontier(walk([0xDC,0x20,0]),"unsupported-opcode")
    def test_callee_rti_is_not_balanced_rtl(self):self.frontier(walk([0x40],kind="long"),"unexpected-rti")
    def test_unknown_opcode_never_becomes_a_one_byte_nop(self):self.frontier(walk([0,0x60]),"unsupported-opcode")
    def test_both_branch_outcomes_must_close(self):self.frontier(walk([0xD0,1,0x60,0]),"unsupported-opcode")
    def test_balanced_loop_does_not_claim_termination(self):self.closed(walk([0xD0,0xFE,0x60]),0)
    def test_unbounded_push_cycle_refuses(self):self.frontier(walk([0x48,0x80,0xFD]),"stack-budget")
    def test_recursive_call_refuses(self):self.frontier(walk([0x20,0,0,0x60]),"stack-budget")
    def test_state_budget_is_a_refusal(self):self.frontier(walk([0xEA,0xEA,0x60],budget=1),"state-budget")
    def test_jump_into_operand_refuses(self):self.frontier(walk([0xD0,1,0xA9,0x60,0x60]),"overlapping-decode")
    def test_incompatible_width_decode_refuses(self):
        self.frontier(walk([0xD0,2,0xC2,0x20,0xA9,0,0x60]),"overlapping-decode")
    def test_instruction_crossing_physical_bank_refuses(self):
        self.frontier(walk([0xA9,0],entry=0xC0FFFF),"instruction-bank-boundary")
    def test_exact_bank_end_fallthrough_wraps_within_pbr(self):
        self.closed(walk([0xEA],entry=0xC0FFFF,extra={BASE:bytes([0x60])}),0)
    def test_relative_branch_wraps_within_pbr(self):
        self.closed(walk([0x80,0],entry=0xC0FFFE,extra={BASE:bytes([0x60])}),0)
    def test_long_call_to_wram_is_an_unproved_code_frontier(self):
        self.frontier(walk([0x22,0,0x80,0x7F,0x60]),"noncanonical-control-flow")
    def test_balanced_return_width_is_reported_without_forcing_prior_premise(self):
        r=walk([0xC2,0x20,0x60]);self.closed(r,0);self.assertFalse(r["matches_prior_return_width_premise"])
    def test_indirect_memory_store_keeps_alias_premise_explicit(self):
        r=walk([0x87,0,0x60]);self.closed(r,0);self.assertFalse(r["nonstack_alias_closure"])
    def test_metadata_has_hashes_without_original_fixture_bytes(self):
        r=walk([0xEA,0x60]);self.closed(r,0)
        self.assertEqual(r["decoded_byte_intervals"][0]["start"],"$C00000")
        self.assertEqual(len(r["decoded_byte_intervals"][0]["sha256"]),64)
        self.assertNotIn("bytes",r)
    def test_canonical_audit_refuses_unpinned_original_test_buffer(self):
        with self.assertRaises(ValueError):v.audit(bytes(0x400000))


class ResetTransitionTests(unittest.TestCase):
    def setUp(self):
        self.boot=BASE+0x100
        self.parts={BASE:bytes([0x78,0x18,0xFB,0x5C])+self.boot.to_bytes(3,"little"),
            self.boot:bytes([0xC2,0x10,0xE2,0x20,0xA2,0xFF,0x06,0x9A])}
    def run_contract(self):return v.reset_transition(specimen(self.parts),reset_entry=BASE,boot_entry=self.boot)
    def test_original_reset_prefix_proves_fixed_sp_but_no_balanced_return(self):
        r=self.run_contract();self.assertEqual(r["assigned_sp"],0x06FF)
        self.assertFalse(r["reset_executed"]);self.assertFalse(r["reset_gate_predicates_discharged"])
    def test_every_reset_prefix_byte_is_semantically_bound(self):
        for i in range(7):
            with self.subTest(i=i):
                old=self.parts[BASE];b=bytearray(old);b[i]^=1;self.parts[BASE]=bytes(b)
                with self.assertRaises(ValueError):self.run_contract()
                self.parts[BASE]=old
    def test_every_boot_prefix_byte_is_semantically_bound(self):
        for i in range(8):
            with self.subTest(i=i):
                old=self.parts[self.boot];b=bytearray(old);b[i]^=1;self.parts[self.boot]=bytes(b)
                with self.assertRaises(ValueError):self.run_contract()
                self.parts[self.boot]=old


if __name__=="__main__":unittest.main()
