"""Independent boundary and evidence rejection checks for original ROM-source v1."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import run_schala_package_helper_v1_rom_source as tool


def original_fixture_rom():
    # Original test bytes have two sparse masks, repeated/shared entries, and
    # distinct pointer lists. This host fixture is not a cartridge output.
    rom=bytearray(0x800000)
    for bank,(root,end,_) in tool.FIXTURES.items():
        n=(end-root-4)//2
        first=n//2
        m0=((1<<first)-1)<<(16-first)
        m1=((1<<(n-first))-1)<<(16-(n-first))
        data=m0.to_bytes(2,"big")+m1.to_bytes(2,"big")
        data+=b"".join((0x6000+i*17).to_bytes(2,"little") for i in range(n))
        rom[bank*65536+root:bank*65536+end]=data
    return bytes(rom)


def accepted_record(case):
    baseline=dict(case["patches"])
    changes=[[a,v] for a,v in dict(case["expected_writes"]).items() if v!=baseline.get(a,0xA5)]
    fixture=bytearray(0x500)
    fixture[0x100:]=bytes([0xA5])*0x400
    for a,v in case["patches"]:
        if 0x7E3000<=a<0x7E3500: fixture[a-0x7E3000]=v
    return {"name":case["name"],"route":case["route"],"cpu":dict(case["expected_cpu"]),
        "writes":copy.deepcopy(case["expected_writes"]),"changes":changes,
        "rom_reads":copy.deepcopy(case["expected_rom_reads"]),"reads_total":len(case["expected_rom_reads"])+1,
        "input_fixture_before_hex":fixture.hex(),"input_fixture_after_hex":fixture.hex(),
        "exec_addresses":[tool.CODE,tool.TAILS[case["route"]]],"instructions":2}


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom=original_fixture_rom()
        cls.cases=tool.build_cases(cls.rom)

    def test_matrix_is_deterministic_and_names_unique(self):
        self.assertEqual(tool.canonical_json(self.cases),tool.canonical_json(tool.build_cases(self.rom)))
        self.assertEqual(len(self.cases),len({c["name"] for c in self.cases}))

    def test_canonical_path_ignores_hostile_flag_and_reads_no_rom(self):
        cases=[c for c in self.cases if c["category"]=="canonical-selector"]
        self.assertEqual([c["selector"] for c in cases],list(range(128)))
        self.assertTrue(all(c["route"]=="canonical" and not c["expected_rom_reads"] for c in cases))

    def test_every_low_byte_bank_identity_is_exercised(self):
        cases=[c for c in self.cases if c["category"]=="every-bank-word-low-byte"]
        self.assertEqual([c["source_bank"] for c in cases],list(range(256)))
        for c in cases:
            if c["source_bank"] not in (0x41,0x42):
                self.assertEqual((c["route"],c["expected_rom_reads"],c["expected_writes"]),("refusal",[],[]))

    def test_high_bank_word_bytes_never_alias_allowed_rom(self):
        cases=[c for c in self.cases if c["category"]=="bank-high-byte-refusal"]
        self.assertEqual(len(cases),6)
        self.assertTrue(all(c["route"]=="refusal" and not c["expected_rom_reads"] for c in cases))

    def test_all_branch_bytes_preserve_rom_bank(self):
        cases=[c for c in self.cases if c["category"]=="both-rom-banks-all-flag-bytes"]
        self.assertEqual(len(cases),512)
        for c in cases:
            self.assertEqual(c["route"],"success")
            self.assertEqual({a>>16 for a,_ in c["expected_rom_reads"]},{c["source_bank"]})

    def test_invalid_unselected_target_refuses_before_any_publication(self):
        for c in self.cases:
            if c["category"]=="every-allowlisted-target-required-before-publication":
                self.assertEqual((c["route"],c["expected_writes"]),("refusal",[]))
                self.assertGreater(len(c["expected_rom_reads"]),4)

    def test_bad_declared_extent_reads_only_header(self):
        cases=[c for c in self.cases if c["category"]=="exact-descriptor-extent"]
        self.assertTrue(all(c["route"]=="refusal" for c in cases))
        self.assertTrue(all(len(c["expected_rom_reads"]) in (0,4) for c in cases))

    def test_bank_crossing_root_is_refused_before_rom_read(self):
        for root in (0xFFFD,0xFFFE,0xFFFF):
            c=tool.make_case(self.rom,"bad",root=root)
            self.assertEqual((c["route"],c["expected_rom_reads"]),("refusal",[]))

    def test_root_at_fffc_can_read_header_without_crossing(self):
        c=tool.make_case(self.rom,"boundary",root=0xFFFC,end_word=0,end_carry=1,targets=[])
        self.assertEqual(c["route"],"success")
        self.assertEqual(c["expected_cpu"]["x"],0)
        self.assertEqual([a&0xFFFF for a,_ in c["expected_rom_reads"]],[0xFFFC,0xFFFD,0xFFFE,0xFFFF])

    def test_registry_reserved_and_large_count_refuse_without_rom_read(self):
        for kw in ({"reserved0":1},{"reserved1":1},{"target_count":33},{"valid":2}):
            c=tool.make_case(self.rom,"bad",**kw)
            self.assertEqual((c["route"],c["expected_rom_reads"]),("refusal",[]))

    def test_all_fixture_writes_remain_explicit_wram_inputs(self):
        tool.validate_fixture_spans(self.cases,676)
        c=copy.deepcopy(self.cases[0]);c["patches"].append([0x410000,0])
        with self.assertRaises(tool.ConformanceError):tool.validate_fixture_spans([c],676)

    def test_literal_ffff_pointer_is_refused_even_allowlisted(self):
        rom=bytearray(self.rom);root=tool.FIXTURES[0x42][0]
        rom[0x420000+root+4:0x420000+root+6]=b"\xff\xff"
        c=tool.make_case(bytes(rom),"ffff")
        self.assertEqual((c["route"],c["expected_writes"]),("refusal",[]))

    def test_descriptor_overlap_pointer_is_refused_even_allowlisted(self):
        rom=bytearray(self.rom);root=tool.FIXTURES[0x42][0]
        rom[0x420000+root+4:0x420000+root+6]=root.to_bytes(2,"little")
        c=tool.make_case(bytes(rom),"overlap")
        self.assertEqual((c["route"],c["expected_writes"]),("refusal",[]))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.case=tool.make_case(original_fixture_rom(),"evidence")
        self.record=accepted_record(self.case)

    def rejects(self):
        with self.assertRaises(tool.ConformanceError):tool.validate_record(self.record,self.case)

    def test_independently_encoded_record_accepted(self):
        tool.validate_record(self.record,self.case)

    def test_cpu_read_bound_missing_or_invalid_refused(self):
        for value in (None,-1,10001,True):
            self.record["reads_total"]=value;self.rejects()

    def test_execution_outside_helper_extent_refused(self):
        for pc in (tool.CODE-1,tool.CODE+676,0x410002,0x420000,0x7E4000,True):
            self.record["exec_addresses"]=[tool.CODE,pc,tool.TAILS["success"]]
            self.record["instructions"]=3;self.rejects()

    def test_nonterminal_byte_near_tail_refused(self):
        self.record["exec_addresses"]=[tool.CODE,tool.TAILS["success"]+1,tool.TAILS["success"]]
        self.record["instructions"]=3;self.rejects()

    def test_early_terminal_tail_refused(self):
        self.record["exec_addresses"]=[tool.CODE,tool.TAILS["canonical"],tool.TAILS["success"]]
        self.record["instructions"]=3;self.rejects()

    def test_wrong_final_tail_refused(self):
        self.record["exec_addresses"][-1]=tool.TAILS["refusal"];self.rejects()

    def test_missing_complete_execution_sequence_refused(self):
        self.record.pop("exec_addresses");self.rejects()

    def test_execution_count_mismatch_refused(self):
        self.record["instructions"]+=1;self.rejects()

    def test_execution_entry_must_match_assembled_base(self):
        self.record["exec_addresses"][0]+=1;self.rejects()

    def test_rom_read_wrong_bank_refused(self):
        self.record["rom_reads"][0][0]^=0x10000;self.rejects()

    def test_rom_read_wrong_value_refused(self):
        self.record["rom_reads"][0][1]^=1;self.rejects()

    def test_rom_read_order_refused(self):
        r=self.record["rom_reads"];r[0],r[1]=r[1],r[0];self.rejects()

    def test_missing_last_rom_read_refused(self):
        self.record["rom_reads"].pop();self.rejects()

    def test_extra_unapproved_read_refused(self):
        self.record["rom_reads"].append([0x430000,0]);self.rejects()

    def test_actual_wram_input_before_and_after_are_both_bound(self):
        for key in ("input_fixture_before_hex","input_fixture_after_hex"):
            r=copy.deepcopy(self.record)
            self.record[key]="ff"+self.record[key][2:]
            self.rejects();self.record=r

    def test_wram_input_write_then_restore_still_refused(self):
        self.record["writes"] += [[0x7E3000,0],[0x7E3000,1]];self.rejects()

    def test_complete_wram_diff_detects_undeclared_change(self):
        self.record["changes"].append([0x7E2CA0,0]);self.rejects()

    def test_cpu_return_width_and_status_bound(self):
        self.record["cpu"]["ps"]^=0x20;self.rejects()

    def test_refusal_cannot_claim_unobserved_rom_reads(self):
        self.case=tool.make_case(original_fixture_rom(),"refusal",bank_word=0x7E)
        self.record=accepted_record(self.case)
        self.record["rom_reads"]=[[0x7E0000,0]];self.rejects()


if __name__=="__main__":unittest.main()
