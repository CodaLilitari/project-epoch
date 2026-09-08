"""Independent negative checks for the native execution evidence validator."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import run_schala_package_helper_conformance_v0 as tool


def accepted_record(case):
    baseline=dict(case["patches"])
    changes=[[a,v] for a,v in dict(case["expected_writes"]).items()
             if v != baseline.get(a,0xA5)]
    return {"name":case["name"],"route":case["route"],
            "cpu":dict(case["expected_cpu"]),"writes":copy.deepcopy(case["expected_writes"]),
            "changes":changes,"instructions":1}


class CaseContractTests(unittest.TestCase):
    def test_deterministic_unique_case_matrix(self):
        first=tool.build_cases()
        self.assertEqual(tool.canonical_json(first),tool.canonical_json(tool.build_cases()))
        self.assertEqual(len(first),len({c["name"] for c in first}))

    def test_all_canonical_selectors_bypass_hostile_flag(self):
        cases=tool.build_cases()[:128]
        self.assertEqual([c["selector"] for c in cases],list(range(128)))
        self.assertTrue(all(c["flag"]>255 and c["route"]=="canonical" for c in cases))

    def test_all_flag_bytes_both_native_masks(self):
        cases=tool.build_cases()[128:384]
        self.assertEqual([c["flag"] for c in cases],list(range(256)))
        self.assertTrue(all(c["route"]=="success" for c in cases))

    def test_bank_endpoint_wraps_register_only(self):
        c=tool.make_case("exact",root=0xFFF8,flag=1)
        self.assertEqual(c["route"],"success")
        self.assertEqual(c["expected_cpu"]["x"],0)
        self.assertEqual(tool.make_case("cross",root=0xFFF9)["route"],"refusal")

    def test_unselected_invalid_pointer_refuses_every_publication(self):
        for pointers in ([0x7000,0xFFFF],[0x7000,0x2007]):
            c=tool.make_case("bad",flag=0,pointers=pointers)
            self.assertEqual(c["route"],"refusal")
            self.assertEqual(c["expected_writes"],[])

    def test_reserved_registry_and_flag_bits_fail_closed(self):
        for changes in ({"valid":2},{"bank_word":0x017F},{"flag":0x0100}):
            self.assertEqual(tool.make_case("bad",**changes)["route"],"refusal")

    def test_all_default_high_selectors_unbound(self):
        for s in range(0x80,0x90):
            self.assertEqual(tool.make_case("unbound",selector=s,valid=0)["route"],"refusal")

    def test_unsupported_high_selectors_refuse(self):
        for s in range(0x90,0x100):
            self.assertEqual(tool.make_case("unsupported",selector=s)["route"],"refusal")

    def test_each_high_selector_has_both_success_branches(self):
        cases=[c for c in tool.build_cases() if c["category"]=="each-bound-high-selector"]
        self.assertEqual({(c["selector"],c["flag"]) for c in cases},
                         {(s,f) for s in range(0x80,0x90) for f in (0,1)})
        self.assertTrue(all(c["route"]=="success" for c in cases))

    def test_wide_selector_words_refuse(self):
        for value in (0x100,0x180,0xFF80,0xFFFF):
            self.assertEqual(tool.make_case("wide",selector=value)["route"],"refusal")

    def test_distinct_pointer_fixture_is_not_alias_only(self):
        cases=[c for c in tool.build_cases() if c["category"]=="distinct-pointer-transport"]
        self.assertEqual(len(cases),2)
        outputs=[]
        for case in cases:
            low={a:v for a,v in case["expected_writes"] if 0x7E5DBD<=a<0x7E5DFD and (a-0x7E5DBD)%4==0}
            outputs.append(set(low.values()))
        self.assertEqual([len(v) for v in outputs],[5,2])
        self.assertFalse(outputs[0]&outputs[1])

    def test_empty_and_single_pointer_exact_endpoints(self):
        for root,m0,m1,flag,x in ((0xFFFC,0,0,0,0),(0xFFFA,0x8000,0,0,0),
                                (0xFFFA,0,0x8000,1,0),(0xFFF9,0x8000,0,0,0xFFFF)):
            c=tool.make_case("endpoint",root=root,mask0=m0,mask1=m1,flag=flag)
            self.assertEqual((c["route"],c["expected_cpu"]["x"]),("success",x))

    def test_every_native_status_value_has_four_routes(self):
        cases=[c for c in tool.build_cases() if c["category"]=="all-native-status-bits"]
        self.assertEqual(len(cases),256)
        for flags in range(256):
            if not flags&0x30:
                self.assertEqual(sum(c["cpu"]["ps"]==flags for c in cases),4)


class FixtureBoundaryTests(unittest.TestCase):
    def test_matrix_spans_pass_at_both_explicit_origins(self):
        for origin in (0x7F8000,0x7F9000):
            tool.validate_fixture_spans(tool.build_cases(),537,origin)

    def test_every_protected_source_target_is_rejected(self):
        for address in (0x7F8000,0x7FF010,0x7E3000,0x7E4000,0x7E1FE6,
                        0x7E1FF0,0x7E0080,0x7E9878,0x7EA0B3,0x7E5DBD):
            c=tool.make_case("collision")
            c["source_spans"]=[[address,address+1]]
            with self.assertRaises(tool.ConformanceError):
                tool.validate_fixture_spans([c],537)

    def test_unapproved_origin_and_extent_rejected(self):
        for origin,size in ((0x7F7000,537),(0x7F9000,0x6000)):
            with self.assertRaises(tool.ConformanceError):
                tool.validate_fixture_spans([],size,origin)

    def test_source_bank_crossing_rejected(self):
        c=tool.make_case("crossing")
        c["source_spans"]=[[0x7EFFFF,0x7F0001]]
        with self.assertRaises(tool.ConformanceError):
            tool.validate_fixture_spans([c],537)

    def test_distinct_source_span_overlap_rejected(self):
        c=tool.make_case("overlap")
        c["source_spans"]=[[0x7F2000,0x7F2008],[0x7F2007,0x7F2009]]
        with self.assertRaises(tool.ConformanceError):
            tool.validate_fixture_spans([c],537)


class EvidenceRejectionTests(unittest.TestCase):
    def setUp(self):
        self.case=tool.make_case("proof",mask0=0xC000,mask1=0)
        self.record=accepted_record(self.case)

    def rejects(self,record,case=None):
        with self.assertRaises(tool.ConformanceError):
            tool.validate_record(record,self.case if case is None else case)

    def test_expected_record_passes(self):
        tool.validate_record(self.record,self.case)

    def test_every_cpu_field_is_bound(self):
        for key in self.record["cpu"]:
            r=copy.deepcopy(self.record)
            r["cpu"][key]=not r["cpu"][key] if isinstance(r["cpu"][key],bool) else r["cpu"][key]^1
            self.rejects(r)

    def test_unexpected_route_rejected(self):
        self.record["route"]="canonical"
        self.rejects(self.record)

    def test_write_even_if_restored_to_same_value_rejected(self):
        self.record["writes"].extend([[0x7E2CA0,0],[0x7E2CA0,0xA5]])
        self.rejects(self.record)

    def test_complete_diff_detects_unobserved_change(self):
        self.record["changes"].append([0x7F2020,0])
        self.rejects(self.record)

    def test_missing_unchanged_output_write_rejected(self):
        self.record["writes"]=[p for p in self.record["writes"] if p[0]!=0x7EA0B3]
        self.rejects(self.record)

    def test_adjacent_owner_word_order_is_bound(self):
        indexes=[i for i,p in enumerate(self.record["writes"]) if 0x7E5DAC <= p[0] < 0x7E5DFD]
        a,b=indexes[0],indexes[6]
        self.record["writes"][a],self.record["writes"][b]=self.record["writes"][b],self.record["writes"][a]
        self.rejects(self.record)

    def test_return_frame_cannot_change(self):
        self.record["writes"].append([0x7E1FF0,0])
        self.rejects(self.record)

    def test_stack_depth_is_bounded(self):
        self.record["writes"].append([0x7E1FE5,0])
        self.rejects(self.record)

    def test_canonical_cannot_use_scratch(self):
        c=tool.make_case("canonical",selector=1)
        r=accepted_record(c)
        r["writes"].append([0x7E4000,1])
        self.rejects(r,c)

    def test_refusal_cannot_write_publication(self):
        c=tool.make_case("refusal",valid=0)
        r=accepted_record(c)
        r["writes"].append([0x7E9878,1])
        self.rejects(r,c)

    def test_high_scratch_and_bounded_stack_are_explicitly_allowed(self):
        self.record["writes"] += [[0x7E4000,1],[0x7E1FE6,2]]
        self.record["changes"] += [[0x7E4000,1],[0x7E1FE6,2]]
        tool.validate_record(self.record,self.case)


if __name__=="__main__":
    unittest.main()
