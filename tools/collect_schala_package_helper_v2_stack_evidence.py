"""Revalidate and reproduce the metadata-only accepted v2 stack evidence.

Reads frozen private native artifacts and public original source. Does not
launch an emulator, write a file, mutate a ROM, or publish raw trace bytes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import sys
from pathlib import Path
import run_schala_package_helper_v2_stack as v

ROOT=Path(__file__).resolve().parents[1]
PREFIX="package_helper_v2_stack_20260908_"
RUNS=(("finalledger1","739690a870193684797c19c2800d7639b473f2a9554c237b587c16f0bee902e6"),
      ("finalledger2","eb305f20e70069429213e85df0fc5f625a766aae24ba6a06bbaa97ec7d7e0ad0"))
TRACE_SHA256="41931d1424daf97d633aa446c4c964e3aa3fecedb6b62ea494400c0161071a9f"
HELPER_SHA256="77dc3224baaa93077218d43d64cbef10bb55494a37057c1a5bfcf0d8fd6758f8"
CASE_SHA256="5c46bd0e5885a2a463f02399f6cd9879b13b2ab25d2af19d5c705b43d05e7d76"
V1_REFERENCE_SHA256="d8b9c9ea589e33517331e377c084c0fadf91a42f1e665f5adbfb9c7895931c92"
TESTS_SHA256="3b71e286d694c3adee2b1ccce648b1f5475a8da85591a29d4a0c1dd63fbffedb"
HISTORY=(
    ("final1","manifest.json","2b73209fbc9922636a3b323dd09a01108f303c4330b967e41f0cd4b4bd795126",
     "First 2980-case matched run with instruction ownership; full stack diff not yet reconciled to last CPU writes"),
    ("final2","manifest.json","46730d7356753ad427a02974aebdcb85eca80201062fa2de1efca4055c2df2e8",
     "Second 2980-case matched run; byte-identical trace preserved before final full-WRAM ledger hardening"),
    ("explore1","manifest.json","76756e6ee2f8c93655984cd36d703a1288b56e916bda6dd9f854ae4516b7e116",
     "130-case exploratory subset before post-instruction SP observations; not final evidence"),
    ("explore2","launch_inputs.json","fe09aa26f315447c403648c28d2b7a9b7c8dcb39138f1ef064cc6a54fedc5f53",
     "Executed full attempt exceeded 240-second emulator bound; no completed trace or accepted manifest"),
    ("explore3","manifest.json","2020f1f02d246464ab97c9dfc372ba2a7498812d72cfdb882cae13319211ef9a",
     "2980 cases passed before independent review reproduced omitted SP metadata and missing instruction ownership gaps"),
    ("execownership1","manifest.json","b53e6fcf44239a26335353331dd54d7f9d7494184bf8424abc690ebfdd480b4a",
     "130-case fresh subset after complete instruction-owned SP/access evidence; precedes final matched pair"),
)


def require(condition:bool,message:str)->None:
    if not condition:raise v.ConformanceError(message)


def identity(path:Path)->dict:
    data=path.read_bytes()
    return {"path":path.relative_to(ROOT).as_posix(),"size_bytes":len(data),"sha256":v.digest(data)}


def checked_private(path:Path)->Path:
    return v.safe.resolve_private_file(path,"evidence artifact",private_root=v.safe.canonical_private_root())


def pinned(path:Path,expected:str)->dict:
    value=identity(path);require(value["sha256"]==expected,"frozen artifact drift: "+str(path));return value


def json_private(path:Path,maximum:int=128*1024*1024)->dict|list:
    path=checked_private(path)
    data=v.safe.read_direct_regular_file(path,"evidence JSON",parent=path.parent,maximum=maximum)
    return json.loads(data)


def artifacts(directory:Path)->list[dict]:
    return [identity(checked_private(p)) for p in sorted(directory.rglob("*")) if p.is_file()]


def projection(row:dict,case:dict)->dict:
    outputs={a for a,_ in case["expected_writes"]}
    return {"route":row["route"],"cpu_except_sp":{k:value for k,value in row["cpu"].items() if k!="sp"},
        "ordered_output_writes":[[a,value] for a,value in row["writes"] if a in outputs],
        "rom_reads":row["rom_reads"],"input_fixture_before_hex":row["input_fixture_before_hex"],
        "input_fixture_after_hex":row["input_fixture_after_hex"]}


def collect()->dict:
    v1path=ROOT/"references/schala_package_helper_v1_rom_source.json"
    prior_reference=pinned(v1path,V1_REFERENCE_SHA256)
    prior=json.loads(v1path.read_bytes())
    for row in [*prior["source_identities"],prior["preserved_v0_source"]]:pinned(ROOT/row["path"],row["sha256"])
    test_identity=pinned(ROOT/"tests/test_schala_package_helper_v2_stack.py",TESTS_SHA256)
    rom=v.verified_rom_bytes();cases=v.build_cases(rom)
    require(len(cases)==2980 and v.digest(v.canonical_json(cases))==CASE_SHA256,"source case contract drift")
    runtime={key:v.safe.DEFAULT_MESEN.parent/name for key,name in v.safe.RUNTIME_NAMES.items()}
    sources={**runtime,"rom":v.DEFAULT_ROM,"collector":v.COLLECTOR,"launcher":Path(v.__file__),
        "asar":v.ASAR,"host_adapter":Path(v.adapter.__file__),"isolation_library":Path(v.safe.__file__),
        "v0_validation_library":Path(v.prior.__file__),"v1_contract_library":Path(v.v1.__file__),"helper":v.HELPER}
    source_ids={key:identity(path) for key,path in sources.items()}
    accepted=[];all_records=[]
    for suffix,expected_manifest in RUNS:
        directory=ROOT/"private/test_runs"/(PREFIX+suffix)
        mp=checked_private(directory/"manifest.json");pinned(mp,expected_manifest)
        manifest=json_private(mp);prepared=json_private(directory/"launch_inputs.json")
        require(manifest["schema"]==v.SCHEMA and manifest["case_count"]==2980 and manifest["passed"] is True
            and manifest["subset_only"] is False,"full accepted run contract mismatch")
        require(manifest["source_hashes"]=={k:value["sha256"] for k,value in source_ids.items()},"current source differs from accepted run")
        require(prepared["schema"]==v.SCHEMA and prepared["execution_status"]=="prepared-not-yet-executed","prepared receipt scope differs")
        require(prepared["source_hashes"]==manifest["source_hashes"] and prepared["staged_hashes"]==manifest["staged_hashes"],"prepared/completed identity mismatch")
        require(manifest["sources_and_staged_inputs_unchanged"] is True and manifest["no_rom_write_or_patch"] is True
            and manifest["production_hook_allocation_or_integration"] is False,"scope or preservation mismatch")
        stage=directory/"staged";app=stage/"app"
        staged={key:app/name for key,name in v.safe.RUNTIME_NAMES.items()}
        roms=list(stage.glob("*.sfc"));saves=list((app/"Saves").iterdir())
        require(len(roms)==len(saves)==1 and saves[0].suffix==".srm","isolated staged ROM/save inventory differs")
        staged.update(rom=roms[0],sram=saves[0],collector=stage/"collector.lua",inputs=stage/"inputs.lua")
        for key,path in staged.items():pinned(checked_private(path),manifest["staged_hashes"][key])
        trace_path=checked_private(directory/"trace.json");pinned(trace_path,TRACE_SHA256)
        pinned(checked_private(directory/"case_contract.json"),CASE_SHA256)
        code=checked_private(directory/"helper.bin").read_bytes()
        require(len(code)==577 and v.digest(code)==HELPER_SHA256,"assembled helper identity differs")
        trace=json_private(trace_path)
        require(trace["schema"]==v.SCHEMA and trace["error"] is None and len(trace["records"])==2980,"trace boundary mismatch")
        for row,case in zip(trace["records"],cases,strict=True):v.validate_record(row,case,code=code)
        rows=trace["records"];all_records.append(rows)
        observations={"route_counts":dict(sorted(Counter(r["route"] for r in rows).items())),
            "rom_byte_reads":sum(len(r["rom_reads"]) for r in rows),
            "cpu_data_reads":sum(r["reads_total"] for r in rows),
            "execution_pc_observations":sum(len(r["exec_addresses"]) for r in rows),
            "executed_helper_instructions":sum(len(r["exec_addresses"])-1 for r in rows),
            "terminal_observations_not_executed":len(rows),
            "stack_accesses":sum(len(r["stack_accesses"]) for r in rows),
            "post_sp_change_observations":sum(len(r["sp_observations"]) for r in rows),
            "per_entry_sp":{f"{sp:04X}":{"case_count":sum(c["cpu"]["sp"]==sp for c in cases),
                "minimum_observed_sp":min(r["minimum_sp"] for r,c in zip(rows,cases,strict=True) if c["cpu"]["sp"]==sp)} for sp in v.ENTRY_STACKS}}
        accepted.append({"run_id":PREFIX+suffix,"manifest":manifest,"observations":observations,"artifact_identities":artifacts(directory)})
    require(all_records[0]==all_records[1],"matched raw observation records differ")
    oldrun=prior["accepted_runs"][0]
    oldpath=ROOT/"private/test_runs"/oldrun["run_id"]/"trace.json"
    pinned(checked_private(oldpath),oldrun["manifest"]["trace_sha256"])
    oldrows=json_private(oldpath)["records"]
    common=[projection(r,c) for r,c in zip(oldrows,cases[:1454],strict=True)]
    for offset in (0,1454):
        require(common==[projection(r,c) for r,c in zip(all_records[0][offset:offset+1454],cases[offset:offset+1454],strict=True)],"v1 externally visible transport behavior differs")
    history=[]
    for suffix,receipt,sha,meaning in HISTORY:
        directory=ROOT/"private/test_runs"/(PREFIX+suffix)
        pinned(checked_private(directory/receipt),sha)
        old_receipt=json_private(directory/receipt)
        if receipt=="manifest.json":
            for filename,key in (("trace.json","trace_sha256"),("case_contract.json","case_contract_sha256"),
                    ("helper.bin","helper_sha256")):
                pinned(checked_private(directory/filename),old_receipt[key])
        history.append({"run_id":PREFIX+suffix,"status":meaning,
            "historical_source_hashes":old_receipt["source_hashes"],
            "historical_completed_case_count":old_receipt.get("case_count"),
            "artifact_identities":artifacts(directory)})
    archive_identities=[]
    for suffix in ("before_exec_ownership_sources","before_complete_diff_ledger_sources"):
        archive=ROOT/"private/test_runs"/(PREFIX+suffix)
        archived=json_private(archive/"manifest.json")
        for row in archived["sources"].values():pinned(checked_private(ROOT/row["archive"]),row["sha256"])
        archive_identities.extend(artifacts(archive))
    return {"schema":"project-epoch-package-helper-v2-stack-evidence","version":2,"date":"2026-09-08",
        "evidence_level":"verified-runtime","gate":"BA-NATIVE-INTEGRATION-DESIGN","subgate":"BA-NATIVE-STACK-FRAME-CONFORMANCE",
        "evidence_scope":"original stack-relative helper in synthetic WRAM, immutable original ExHiROM descriptor-shaped source, interrupts disabled",
        "source_identities":source_ids,"tests_identity":test_identity,"evidence_collector_identity":identity(Path(__file__).resolve()),
        "preserved_v1_reference":prior_reference,"fixture_contract":{
            "source_rom_sha256":v.ROM_SHA256,"descriptor_fixtures":prior["fixture_contract"]["descriptors"],
            "accepted_complete_bank_words":[0x41,0x42],"registry_span":[0x7E3000,0x7E3100],"target_array_span":[0x7E3100,0x7E3500],
            "code_origin":v.CODE,"code_size":577,"code_sha256":HELPER_SHA256,"entry_bridge_span":[v.ENTRY_BRIDGE,v.ENTRY_BRIDGE+4],
            "entry_stack_values":list(v.ENTRY_STACKS),"local_bytes":42,"saved_context_bytes":8,"maximum_local_call_bytes":2,"maximum_helper_depth":52,
            "retired_global_scratch_unchanged":[0x7E4000,0x7E4080]},
        "accepted_runs":accepted,"identical_raw_trace_sha256":TRACE_SHA256,"total_accepted_cases":5960,
        "v1_behavior_equivalence":{"case_count_per_synthetic_sp":1454,"synthetic_entry_sps":[0x1FEF,0x06D8],
            "fields":"route, final CPU except SP, ordered existing outputs, exact ROM reads, before/after immutable input snapshots",
            "common_projection_sha256":v.digest(v.canonical_json(common)),"v1_trace_sha256":oldrun["manifest"]["trace_sha256"]},
        "execution_and_stack_guards":{"complete_helper_span_and_exact_terminal":True,"first_helper_opcode_observed":True,
            "independent_instruction_start_disassembly_guard":False,"required_post_sp_change_observations_derived_from_exact_code_and_pc_sequence":True,
            "stack_access_owning_instruction_ordinal_required":True,"stack_relative_access_strictly_above_sp":True,
            "stack_relative_operand_one_or_two_byte_span_required":True,"independent_m_state_width_emulation":False,
            "full_wram_diff_restricted_to_exact_allocated_stack_and_existing_outputs":True,
            "entire_final_wram_diff_reconciled_to_last_cpu_writes_and_exact_setup_baseline":True},
        "host_tests":{"count":48,"command":"python -B -m unittest discover -s tests -p test_schala_package_helper_v2_stack.py -v"},
        "exploratory_history":history,"pre_hardening_source_archives":archive_identities,
        "scope":{"rom_mutation":False,"pointed_stream_read_or_execution":False,"production_hook_allocation_or_registry":False,
            "game_stack_ownership":False,"interrupt_execution_or_safety":False,"cancellation_lifecycle":False,"logical_pc07_runtime":False},
        "reproduce_reference":"python -B tools/collect_schala_package_helper_v2_stack_evidence.py",
        "serialization":"json.dumps(value, indent=2), UTF-8, LF, exactly one trailing newline",
        "next_gates":["separately measured original interrupt fixture","real game stack and normal-NMI closure","immutable ROM registry and ROM helper execution","cancellation and production placement/hook contracts"]}


if __name__=="__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write((json.dumps(collect(),indent=2)+"\n").encode("utf-8"))
