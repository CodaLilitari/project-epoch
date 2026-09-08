"""Original synthetic adversarial v3 metadata; no private image or trace input."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import run_schala_package_helper_v3_rom as v
m=v.model
PAYLOAD,REGISTRY,CERTIFICATE=m.original_components()
SPECIMEN=bytes((0x08,0x1B,0xA3,1,0x1B,0x5C,0x10,0x81,0))


def original_case(selector=0x80,flag=0,sp=0x1FEF,status=0):
    return m.make_case(PAYLOAD,REGISTRY,"original-metadata",selector,flag,sp=sp,status=status)


def original_record(c):
    # Validator-only opcode specimen, not an asserted execution of the helper.
    writes=copy.deepcopy(c["expected_writes"]);address=0x7E0000+c["cpu"]["sp"]
    writes.append([address,c["cpu"]["ps"]]);baseline=dict(c["patches"])
    changes=[[a,value] for a,value in sorted(dict(writes).items()) if value!=baseline.get(a,0xA5)]
    depth=(52 if c["countbits_reached"] else 50) if c["frame_allocated"] else 8
    minimum=c["cpu"]["sp"]-depth
    pcs=[v.CODE,v.CODE+1,v.CODE+2,v.CODE+4,v.CODE+5,v.TAILS[c["route"]]]
    return {"name":c["name"],"route":c["route"],"cpu":dict(c["expected_cpu"]),
        "writes":writes,"changes":changes,"rom_reads":copy.deepcopy(c["expected_rom_reads"]),
        "reads_total":len(c["expected_rom_reads"])+1,"instructions":len(pcs),"exec_addresses":pcs,
        "exec_opcode_peeks":[SPECIMEN[a-v.CODE] for a in pcs[:-1]]+[0x80],
        "input_fixture_before_hex":REGISTRY.hex(),"input_fixture_after_hex":REGISTRY.hex(),
        "descriptor_fixture_before_hex":PAYLOAD.hex(),"descriptor_fixture_after_hex":PAYLOAD.hex(),
        "retired_scratch_before_hex":bytes([0xA5]*128).hex(),"retired_scratch_after_hex":bytes([0xA5]*128).hex(),
        "minimum_sp":minimum,"sp_observations":[[2,v.CODE+1,c["cpu"]["sp"]-1],[3,v.CODE+2,minimum],[5,v.CODE+5,c["cpu"]["sp"]]],
        "stack_accesses":[[1,address,c["cpu"]["ps"],c["cpu"]["sp"],1],[3,0x7E0000+minimum+1,0,minimum,0]]}


class OriginalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases=m.build_cases(PAYLOAD,REGISTRY)

    def test_matrix_is_exact_unique_and_deterministic(self):
        self.assertEqual(len(self.cases),3184)
        self.assertEqual(len({c["name"] for c in self.cases}),3184)
        self.assertEqual(self.cases,m.build_cases(PAYLOAD,REGISTRY))

    def test_all_flags_of_all_four_bindings_at_both_sps(self):
        for sp in m.ENTRY_STACKS:
            for selector in range(0x80,0x84):
                rows=[c for c in self.cases if c["cpu"]["sp"]==sp and c["selector"]==selector and c["category"]=="all-four-bindings-all-flag-bytes"]
                self.assertEqual([c["flag"] for c in rows],list(range(256)))
                self.assertTrue(all(c["route"]=="success" for c in rows))

    def test_all_canonical_inputs_ignore_hostile_flag_and_rom(self):
        for sp in m.ENTRY_STACKS:
            rows=[c for c in self.cases if c["cpu"]["sp"]==sp and c["category"]=="all-canonical-selectors"]
            self.assertEqual([c["selector"] for c in rows],list(range(128)))
            self.assertTrue(all(c["route"]=="canonical" and not c["expected_rom_reads"] for c in rows))

    def test_unbound_registry_requires_only_actual_valid_word(self):
        for selector in range(0x84,0x90):
            c=original_case(selector);a=m.REGISTRY+(selector-0x80)*16
            self.assertEqual(c["expected_rom_reads"],[[a,0],[a+1,0]])
            self.assertTrue(c["frame_allocated"]);self.assertFalse(c["countbits_reached"])
            self.assertEqual(c["expected_writes"],[])

    def test_unsupported_and_wide_inputs_read_no_rom(self):
        for selector,flag in ((0x90,0),(0xFFFF,0),(0x80,0x100)):
            c=original_case(selector,flag)
            self.assertEqual(c["route"],"refusal");self.assertEqual(c["expected_rom_reads"],[])
            self.assertFalse(c["frame_allocated"])

    def test_empty_selected_masks_still_preflight_both_masks(self):
        for selector,flag in ((0x83,0),(0x82,0x40)):
            c=original_case(selector,flag)
            self.assertEqual(c["route"],"success");self.assertTrue(c["countbits_reached"])
            self.assertFalse(any(0x7E5DAC<=a<0x7E5DFD for a,_ in c["expected_writes"]))
            self.assertTrue(any(a>>16==0x42 for a,_ in c["expected_rom_reads"]))

    def test_registry_then_interleaved_pointer_allowlist_reads(self):
        c=original_case();reads=c["expected_rom_reads"]
        self.assertEqual([a-m.REGISTRY for a,_ in reads[:16]],[0,1,12,13,14,15,10,11,6,7,8,9,4,5,2,3])
        self.assertEqual(reads[20:24],[[0x420004,0x80],[0x420005,0],[0x430100,0x80],[0x430101,0]])
        self.assertEqual(len(reads),212)

    def test_no_pointed_terminal_byte_is_a_data_read(self):
        targets={0x420000+t for p in CERTIFICATE["packages"] for t in p["targets"]}
        self.assertTrue(all(a not in targets for c in self.cases for a,_ in c["expected_rom_reads"]))

    def test_all_source_setup_is_four_exact_wram_bytes(self):
        v.validate_case_setup(self.cases)
        self.assertTrue(all(len(c["patches"])==4 for c in self.cases))

    def test_registry_rom_mutation_cannot_be_added_to_setup(self):
        c=original_case();c["patches"].append([0x430000,0])
        with self.assertRaises(v.ConformanceError):v.validate_case_setup([c])

    def test_wram_registry_replacement_cannot_be_added_to_setup(self):
        c=original_case();c["patches"].append([0x7E3000,1])
        with self.assertRaises(v.ConformanceError):v.validate_case_setup([c])

    def test_every_immutable_registry_byte_is_bound(self):
        for i in range(len(REGISTRY)):
            b=bytearray(REGISTRY);b[i]^=1
            with self.assertRaises(ValueError):m.require_components(PAYLOAD,bytes(b))

    def test_every_original_payload_byte_is_bound(self):
        for i in range(len(PAYLOAD)):
            b=bytearray(PAYLOAD);b[i]^=1
            with self.assertRaises(ValueError):m.require_components(bytes(b),REGISTRY)

    def test_component_extent_or_mutable_type_cannot_pass(self):
        for p,r in ((PAYLOAD[:-1],REGISTRY),(PAYLOAD,REGISTRY+b"x"),(bytearray(PAYLOAD),REGISTRY)):
            with self.assertRaises(ValueError):m.require_components(p,r)

    def test_original_policy_certificate_survives_json_serialization(self):
        self.assertEqual(v.canonical_json(CERTIFICATE),v.canonical_json(json.loads(v.canonical_json(CERTIFICATE))))


class EvidenceRejectionTests(unittest.TestCase):
    def setUp(self):self.c=original_case();self.r=original_record(self.c)
    def check(self):v.validate_record(self.r,self.c,code=SPECIMEN,registry=REGISTRY,payload=PAYLOAD)
    def rejects(self):
        with self.assertRaises(v.ConformanceError):self.check()

    def test_original_validator_specimen_passes(self):self.check()
    def test_unbound_frame_has_50_byte_minimum_despite_registry_reads(self):
        self.c=original_case(0x84);self.r=original_record(self.c);self.check()
        self.assertEqual(self.r["minimum_sp"],self.c["cpu"]["sp"]-50)
    def test_changed_opcode_peek_rejects(self):self.r["exec_opcode_peeks"][0]^=1;self.rejects()
    def test_missing_opcode_peek_rejects(self):self.r["exec_opcode_peeks"].pop();self.rejects()
    def test_wrong_terminal_peek_rejects(self):self.r["exec_opcode_peeks"][-1]=0xDB;self.rejects()
    def test_code_cannot_execute_from_old_wram_placement(self):self.r["exec_addresses"][0]=0x7F8000;self.rejects()
    def test_registry_cannot_be_executed(self):self.r["exec_addresses"][1]=0x430000;self.rejects()
    def test_pointed_terminal_cannot_be_executed(self):self.r["exec_addresses"][1]=0x420080;self.rejects()
    def test_missing_registry_read_rejects(self):self.r["rom_reads"].pop(0);self.rejects()
    def test_registry_read_value_rejects(self):self.r["rom_reads"][0][1]^=1;self.rejects()
    def test_registry_read_bank_cannot_be_wram(self):self.r["rom_reads"][0][0]=0x7E3000;self.rejects()
    def test_registry_descriptor_read_order_is_bound(self):self.r["rom_reads"][15:17]=reversed(self.r["rom_reads"][15:17]);self.rejects()
    def test_rom_registry_before_and_after_bound(self):
        for key in ("input_fixture_before_hex","input_fixture_after_hex"):
            saved=self.r[key];self.r[key]="ff"+saved[2:];self.rejects();self.r[key]=saved
    def test_rom_descriptor_before_and_after_bound(self):
        for key in ("descriptor_fixture_before_hex","descriptor_fixture_after_hex"):
            saved=self.r[key];self.r[key]="00"+saved[2:];self.rejects();self.r[key]=saved
    def test_missing_nonminimum_sp_observation_rejects(self):self.r["sp_observations"].pop(0);self.rejects()
    def test_stack_relative_local_at_sp_rejects(self):self.r["stack_accesses"][1][1]-=1;self.rejects()
    def test_unexplained_final_stack_change_rejects(self):
        self.r["changes"].append([self.c["stack_span"][0]+3,0]);self.r["changes"].sort();self.rejects()
    def test_ordered_publication_is_bound(self):
        i=next(i for i,r in enumerate(self.r["writes"]) if 0x7E5DAC<=r[0]<0x7E5DFD)
        self.r["writes"][i],self.r["writes"][i+1]=self.r["writes"][i+1],self.r["writes"][i];self.rejects()
    def test_original_rom_write_even_if_ignored_is_rejected(self):self.r["writes"].append([0x430000,0]);self.rejects()
    def test_retired_scratch_cpu_write_rejects(self):self.r["writes"].append([0x7E4000,0]);self.rejects()
    def test_final_cpu_bank_is_bound(self):self.r["cpu"]["dbr"]=0x43;self.rejects()
    def test_cpu_integer_registers_reject_float_and_boolean_aliases(self):
        for key in self.r["cpu"]:
            if key=="emulationMode":continue
            for convert in (float,bool):
                with self.subTest(key=key,convert=convert):
                    self.r=original_record(self.c);self.r["cpu"][key]=convert(self.r["cpu"][key]);self.rejects()
    def test_cpu_register_widths_are_strict(self):
        for key in ("a","x","y","d","dbr","sp","ps"):
            for value in (-1,256 if key in ("ps","dbr") else 65536):
                with self.subTest(key=key,value=value):
                    self.r=original_record(self.c);self.r["cpu"][key]=value;self.rejects()
    def test_emulation_mode_rejects_integer_alias(self):self.r["cpu"]["emulationMode"]=0;self.rejects()
    def test_cpu_missing_or_extra_key_rejects(self):
        self.r["cpu"].pop("a");self.rejects()
        self.r=original_record(self.c);self.r["cpu"]["extra"]=0;self.rejects()
    def test_byte_evidence_rejects_numeric_aliases(self):
        for key in ("writes","changes","rom_reads"):
            for index in (0,1):
                for convert in (float,bool):
                    with self.subTest(key=key,index=index,convert=convert):
                        self.r=original_record(self.c);self.r[key][0][index]=convert(self.r[key][0][index]);self.rejects()
    def test_byte_evidence_requires_lists_and_exact_pairs(self):
        for key in ("writes","changes","rom_reads"):
            for mutation in (lambda rows:tuple(rows),lambda rows:[tuple(rows[0])]+rows[1:],
                    lambda rows:[[rows[0][0]]]+rows[1:],lambda rows:[rows[0]+[0]]+rows[1:]):
                with self.subTest(key=key,mutation=mutation):
                    self.r=original_record(self.c);self.r[key]=mutation(self.r[key]);self.rejects()
    def test_byte_evidence_widths_reject(self):
        for key in ("writes","changes","rom_reads"):
            for index,value in ((0,-1),(0,0x1000000),(1,-1),(1,256)):
                with self.subTest(key=key,index=index,value=value):
                    self.r=original_record(self.c);self.r[key][0][index]=value;self.rejects()
    def test_byte_evidence_extent_limits_reject(self):
        for key,maximum in (("writes",8192),("changes",131072),("rom_reads",256)):
            self.r=original_record(self.c);self.r[key]=[[0,0]]*(maximum+1);self.rejects()
    def test_missing_byte_evidence_rejects(self):
        for key in ("writes","changes","rom_reads"):
            self.r=original_record(self.c);self.r.pop(key);self.rejects()
    def test_float_instruction_count_rejects(self):self.r["instructions"]=float(self.r["instructions"]);self.rejects()
    def test_float_terminal_pc_rejects(self):self.r["exec_addresses"][-1]=float(self.r["exec_addresses"][-1]);self.rejects()


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.output=self.root/"run";self.output.mkdir()
        self.paths={}
        for label in ("one","two"):
            directory=self.root/label;directory.mkdir();path=directory/"same.py"
            path.write_bytes(b"# Original source specimen\n");self.paths[label]=path
        self.before={key:v.safe.sha256_file(path) for key,path in self.paths.items()}
    def archive(self):return v.archive_guarded_sources(self.output,self.paths,self.before,source_root=self.root)
    def test_identical_basenames_have_distinct_archives_and_metadata(self):
        paths,hashes=self.archive();self.assertNotEqual(paths["one"],paths["two"])
        rows=json.loads(paths["snapshot_metadata"].read_bytes())["sources"]
        self.assertEqual([r["source"] for r in rows],["one/same.py","two/same.py"])
        self.assertEqual({r["label"]:r["sha256"] for r in rows},self.before)
        for label,path in paths.items():self.assertEqual(v.safe.sha256_file(path),hashes[label])
    def test_existing_archive_is_never_replaced(self):
        paths,hashes=self.archive()
        with self.assertRaises(FileExistsError):self.archive()
        self.assertEqual({k:v.safe.sha256_file(p) for k,p in paths.items()},hashes)
    def test_source_drift_before_archive_refuses(self):
        self.paths["one"].write_bytes(b"# Changed original specimen\n")
        with self.assertRaises(v.ConformanceError):self.archive()
    def test_unsafe_label_refuses(self):
        self.paths["../escape"]=self.paths.pop("one");self.before["../escape"]=self.before.pop("one")
        with self.assertRaises(v.ConformanceError):self.archive()
    def test_binary_inputs_are_not_source_snapshots(self):
        path=self.root/"original.bin";path.write_bytes(b"original specimen")
        self.paths["binary"]=path;self.before["binary"]=v.safe.sha256_file(path)
        paths,_=self.archive();self.assertNotIn("binary",paths)


if __name__=="__main__":unittest.main()
