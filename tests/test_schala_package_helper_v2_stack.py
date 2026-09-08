"""Independent frame ownership and liveness rejection tests for synthetic v2."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(ROOT/"tests"))
import run_schala_package_helper_v2_stack as tool
import run_schala_package_helper_v1_rom_source as v1
import test_schala_package_helper_v1_rom_source as original


def make_case(*,sp=0x1FEF,selector=0x80,flag=0,valid=1,index=0):
    return tool.with_stack(v1.make_case(original.original_fixture_rom(),"stack-proof",selector,flag,
        valid=valid,index=index),sp)


# Original validator-only opcode specimen; this is not an emulator trace.
# PHP; TCS; LDA 1,S; TCS; JML fixed tail. SP values are adversarial metadata.
SPECIMEN = bytes((0x08,0x1B,0xA3,0x01,0x1B,0x5C,0x10,0xF0,0x7F))

def accepted_record(c):
    r=original.accepted_record(c)
    depth=(52 if c["expected_rom_reads"] else 50) if c["frame_allocated"] else 8
    r["minimum_sp"]=c["cpu"]["sp"]-depth
    r["exec_addresses"]=[tool.CODE,tool.CODE+1,tool.CODE+2,tool.CODE+4,tool.CODE+5,tool.TAILS[c["route"]]]
    r["instructions"]=len(r["exec_addresses"])
    r["sp_observations"]=[[2,tool.CODE+1,c["cpu"]["sp"]-1],
        [3,tool.CODE+2,r["minimum_sp"]],[5,tool.CODE+5,c["cpu"]["sp"]]]
    r["retired_scratch_before_hex"]=bytes([0xA5]*128).hex()
    r["retired_scratch_after_hex"]=bytes([0xA5]*128).hex()
    address=c["stack_span"][1]-1
    r["writes"].append([address,c["cpu"]["ps"]])
    if c["cpu"]["ps"]!=0xA5:r["changes"].append([address,c["cpu"]["ps"]])
    r["stack_accesses"]=[[1,address,c["cpu"]["ps"],c["cpu"]["sp"],1],
        [3,0x7E0000+r["minimum_sp"]+1,0,r["minimum_sp"],0]]
    r["changes"].sort(key=lambda row:row[0])
    return r


class FrameContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=original.original_fixture_rom()
        cls.cases=tool.build_cases(cls.rom)

    def test_full_matrix_repeated_at_two_distinct_synthetic_sps(self):
        for sp in (0x1FEF,0x06D8):
            cases=[c for c in self.cases if c["cpu"]["sp"]==sp]
            self.assertEqual(len(cases),1454)
        self.assertEqual(len(self.cases),2980)

    def test_all_case_names_unique_and_matrix_deterministic(self):
        self.assertEqual(len(self.cases),len({c["name"] for c in self.cases}))
        self.assertEqual(tool.canonical_json(self.cases),tool.canonical_json(tool.build_cases(self.rom)))

    def test_every_matrix_stack_extent_is_valid_and_disjoint(self):
        tool.validate_fixture_spans(self.cases,577)

    def test_underflow_guard_cancels_high_path_before_rom_or_publications(self):
        for sp in (8,0x33):
            for flag in (0,0x40):
                c=make_case(sp=sp,flag=flag)
                self.assertEqual(c["route"],"refusal")
                self.assertFalse(c["frame_allocated"])
                self.assertEqual(c["stack_depth_limit"],8)
                self.assertEqual(c["expected_rom_reads"],[])
                self.assertEqual(c["expected_writes"],[])
                self.assertEqual(c["expected_cpu"],c["cpu"])

    def test_exact_stack_floor_accepts_without_wrap(self):
        c=make_case(sp=0x34)
        self.assertEqual(c["route"],"success")
        self.assertTrue(c["frame_allocated"])
        self.assertEqual(c["stack_span"],[0x7E0001,0x7E0035])
        self.assertEqual(c["cpu"]["sp"]-c["stack_depth_limit"],0)

    def test_canonical_keeps_eight_save_bytes_at_every_placement(self):
        for sp in tool.ENTRY_STACKS:
            c=make_case(sp=sp,selector=1,flag=0xFFFF)
            self.assertEqual(c["route"],"canonical")
            self.assertFalse(c["frame_allocated"])
            self.assertEqual(c["stack_depth_limit"],8)

    def test_early_refusal_keeps_only_eight_save_bytes(self):
        for selector,flag in ((0x90,0),(0x100,0),(0x80,0x100)):
            c=make_case(selector=selector,flag=flag)
            self.assertFalse(c["frame_allocated"])
            self.assertEqual(c["stack_depth_limit"],8)

    def test_registry_refusal_releases_allocated_frame(self):
        c=make_case(valid=0)
        self.assertTrue(c["frame_allocated"])
        self.assertEqual(c["route"],"refusal")
        self.assertEqual(c["expected_cpu"],c["cpu"])

    def test_unsafe_initial_stack_is_rejected_by_caller_before_native_push(self):
        for sp in (0,7,0x2000,0xFFFF,True):
            c=make_case();c["cpu"]["sp"]=sp
            with self.assertRaises(tool.ConformanceError):tool.validate_fixture_spans([c],577)

    def test_forged_stack_span_cannot_include_old_global_scratch(self):
        c=make_case();c["stack_span"]=[0x7E4000,0x7E4080]
        with self.assertRaises(tool.ConformanceError):tool.validate_fixture_spans([c],577)

    def test_boundary_matrix_contains_incoming_decimal_status(self):
        c=[c for c in self.cases if c["category"]=="stack-floor-and-underflow"]
        self.assertEqual(len(c),72)
        self.assertTrue(any(c["cpu"]["ps"]&8 and c["route"]=="success" for c in c))
        self.assertTrue(any(c["cpu"]["ps"]&8 and c["route"]=="refusal" for c in c))


class EvidenceRejectionTests(unittest.TestCase):
    def setUp(self):
        self.c=make_case();self.r=accepted_record(self.c)

    def rejects(self):
        with self.assertRaises(tool.ConformanceError):tool.validate_record(self.r,self.c,code=SPECIMEN)

    def test_independent_record_passes(self):tool.validate_record(self.r,self.c,code=SPECIMEN)

    def test_old_scratch_cpu_write_even_if_restored_is_rejected(self):
        self.r["writes"] += [[0x7E4000,0],[0x7E4000,0xA5]];self.rejects()

    def test_old_scratch_diff_without_write_callback_is_rejected(self):
        self.r["changes"].append([0x7E407F,0]);self.rejects()

    def test_retired_scratch_before_and_after_are_bound(self):
        for key in ("retired_scratch_before_hex","retired_scratch_after_hex"):
            original_value=self.r[key];self.r[key]="00"+original_value[2:]
            self.rejects();self.r[key]=original_value

    def test_write_one_byte_below_allocated_frame_is_rejected(self):
        self.r["writes"].append([self.c["stack_span"][0]-1,0]);self.rejects()

    def test_preexisting_caller_frame_write_is_rejected(self):
        self.r["writes"].append([self.c["stack_span"][1],0]);self.rejects()

    def test_framed_local_read_after_release_is_rejected(self):
        self.r["stack_accesses"].append([3,self.c["stack_span"][0]+4,0,self.c["cpu"]["sp"]-8,0]);self.rejects()

    def test_stack_write_liveness_trace_must_match_every_stack_write(self):
        self.r["stack_accesses"]=[];self.rejects()

    def test_changed_stack_write_value_is_rejected(self):
        self.r["stack_accesses"][0][2]^=1;self.rejects()

    def test_stack_read_below_declared_floor_is_rejected(self):
        self.r["stack_accesses"].append([3,self.c["stack_span"][0]-1,0,self.c["cpu"]["sp"]-52,0]);self.rejects()

    def test_stack_access_sp_underflow_is_rejected(self):
        self.r["stack_accesses"][0][3]=self.c["cpu"]["sp"]-53;self.rejects()

    def test_stack_access_wrong_mode_is_rejected(self):
        self.r["stack_accesses"][0][4]=2;self.rejects()

    def test_minimum_sp_must_match_observed_sp(self):
        self.r["minimum_sp"]+=1;self.rejects()

    def test_missing_executed_sp_observations_is_rejected(self):
        self.r.pop("sp_observations");self.rejects()

    def test_executed_sp_below_frame_is_rejected(self):
        self.r["sp_observations"][1][2]-=1;self.rejects()

    def test_omitting_nonminimum_sp_observation_is_rejected(self):
        self.r["sp_observations"].pop(0);self.rejects()

    def test_only_minimum_sp_observation_cannot_pass(self):
        self.r["sp_observations"]=[self.r["sp_observations"][1]];self.rejects()

    def test_shifted_sp_observation_ordinal_is_rejected(self):
        self.r["sp_observations"][0][0]+=1;self.rejects()

    def test_sp_observation_pc_must_match_owning_execution(self):
        self.r["sp_observations"][0][1]+=1;self.rejects()

    def test_extra_sp_observation_is_rejected(self):
        self.r["sp_observations"].append(self.r["sp_observations"][-1]);self.rejects()

    def test_opcode_bytes_define_required_observations(self):
        altered=bytes((0xEA,))+SPECIMEN[1:]
        with self.assertRaises(tool.ConformanceError):tool.validate_record(self.r,self.c,code=altered)

    def test_stack_relative_read_at_live_sp_is_unallocated(self):
        a=self.r["stack_accesses"][1];a[1]-=1;self.rejects()

    def test_stack_relative_operand_is_bound(self):
        self.r["stack_accesses"][1][1]+=3;self.rejects()

    def test_local_read_cannot_claim_non_stack_instruction(self):
        self.r["stack_accesses"][1][0]=2;self.rejects()

    def test_stack_access_cannot_claim_terminal_opcode(self):
        self.r["stack_accesses"][1][0]=len(self.r["exec_addresses"]);self.rejects()

    def test_stack_access_cannot_precede_first_exec_observation(self):
        self.r["stack_accesses"][0][0]=0;self.rejects()

    def test_stack_access_instruction_ownership_cannot_move_backwards(self):
        self.r["stack_accesses"].append(self.r["stack_accesses"][0]);self.rejects()

    def test_unexplained_stack_diff_without_cpu_write_is_rejected(self):
        self.r["changes"].append([self.c["stack_span"][0]+3,0])
        self.r["changes"].sort(key=lambda row:row[0]);self.rejects()

    def test_unvisited_countbits_depth_bytes_cannot_change(self):
        self.c=make_case(valid=0);self.r=accepted_record(self.c)
        self.assertEqual(self.r["minimum_sp"],self.c["cpu"]["sp"]-50)
        self.r["changes"].append([self.c["stack_span"][0],0])
        self.r["changes"].sort(key=lambda row:row[0]);self.rejects()

    def test_stack_diff_must_match_the_final_write_value(self):
        address=self.r["stack_accesses"][0][1]
        next(row for row in self.r["changes"] if row[0]==address)[1]^=1;self.rejects()

    def test_required_final_stack_change_cannot_be_omitted(self):
        address=self.r["stack_accesses"][0][1]
        self.r["changes"]=[row for row in self.r["changes"] if row[0]!=address];self.rejects()

    def test_unframed_route_cannot_claim_local_frame_depth(self):
        self.c=make_case(selector=1);self.r=accepted_record(self.c)
        self.r["minimum_sp"]-=42;self.rejects()

    def test_saved_x_must_receive_final_cursor(self):
        self.r["cpu"]["x"]^=1;self.rejects()

    def test_incoming_decimal_flag_restoration_is_checked(self):
        self.c=make_case(index=3);self.r=accepted_record(self.c)
        self.r["cpu"]["ps"]^=8;self.rejects()

    def test_rom_bank_and_read_order_still_bound(self):
        self.r["rom_reads"][0][0]^=0x10000;self.rejects()

    def test_execution_cannot_enter_old_scratch(self):
        self.r["exec_addresses"]=[tool.CODE,0x7E4000,tool.TAILS["success"]]
        self.r["instructions"]=3;self.rejects()

    def test_registry_changes_are_rejected(self):
        self.r["input_fixture_after_hex"]="ff"+self.r["input_fixture_after_hex"][2:];self.rejects()


if __name__=="__main__":unittest.main()
