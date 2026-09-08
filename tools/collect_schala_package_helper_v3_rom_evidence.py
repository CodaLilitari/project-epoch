"""Read-only reproduction of original ROM-code/registry v3 evidence metadata.

No emulator launch, ROM mutation, file output or raw-trace publication.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import sys
import run_schala_package_helper_v3_rom as v

ROOT=v.ROOT
PREFIX="package_helper_v3_rom_20260908_"
RUNS=(("final1","d9abf64340f8a68bde6e95fec21fc89431f2a58c10317ac1d58125b6dad52865"),("final2","1d15f8794fdc1c54d7cc2a57193475b82ef86028537e3ba814c3b97d5e7193be"))
TRACE_SHA256="f9d042c5d76a15a717c7330204d0764a2783191875ac3c91b727a799e6450710"
CASE_SHA256="cfb9f96fb99bb93e4fb1348170d2ec509c9c3d5acfacafd2a7e936e9a5be3258"
V2_REFERENCE_SHA256="a095a1e18e97bd7f9746f3bc21affc90e30d76de10a34a2ffdff164e4b3c423f"
HISTORY_ARCHIVE_SHA256="c58c474cb338b816e0397fc33018536916291ef090f5db41c02d21a5985d2d99"
EXPLORE_TRACE_SHA256="28024b8d62bda5fcb3e0d42987438cc555e992c500e5e9ac5811b12069e3066f"


def require(condition,message):
    if not condition:raise v.ConformanceError(message)


def checked(path):return v.safe.resolve_private_file(path,"private evidence artifact",private_root=v.safe.canonical_private_root())


def identity(path):
    return {"path":path.relative_to(ROOT).as_posix(),"size_bytes":path.stat().st_size,"sha256":v.safe.sha256_file(path)}


def pinned(path,sha):
    row=identity(path);require(row["sha256"]==sha,"frozen artifact drift: "+str(path));return row


def private_json(path,maximum=192*1024*1024):
    path=checked(path)
    return json.loads(v.safe.read_direct_regular_file(path,"evidence JSON",parent=path.parent,maximum=maximum))


def artifacts(directory):
    return [identity(checked(p)) for p in sorted(directory.rglob("*")) if p.is_file()]


def source_snapshots(directory,manifest,prepared):
    hashes=manifest["source_snapshot_hashes"]
    require(prepared["source_snapshot_hashes"]==hashes,"prepared/completed snapshot identities differ")
    metadata_path=checked(directory/"source_snapshots.json")
    pinned(metadata_path,hashes["snapshot_metadata"])
    metadata=private_json(metadata_path)
    require(metadata["schema"]==v.SCHEMA+"-source-snapshots" and metadata["execution_status"]=="prepared-not-yet-executed","source snapshot schema differs")
    labels=[row["label"] for row in metadata["sources"]]
    require(len(labels)==len(set(labels)) and set(labels)==set(hashes)-{"snapshot_metadata"},"source snapshot inventory differs")
    sources={key:v.safe.DEFAULT_MESEN.parent/name for key,name in v.safe.RUNTIME_NAMES.items()}
    sources["rom"]=v.DEFAULT_ROM
    for row in metadata["sources"]:
        label=row["label"];source=ROOT/row["source"];archive=checked(directory/row["archive"])
        require(row["sha256"]==hashes[label]==manifest["source_hashes"][label],"source/archive manifest relation differs")
        require(archive.stat().st_size==row["size_bytes"],"source snapshot size differs")
        pinned(archive,row["sha256"]);pinned(source,row["sha256"])
        sources[label]=source
    require(set(sources)==set(manifest["source_hashes"]),"full guarded source inventory differs")
    for label,path in sources.items():pinned(path,manifest["source_hashes"][label])
    eligible={k for k,p in sources.items() if p.suffix.lower() in (".py",".asm",".lua",".json")}
    require(eligible==set(labels) and "tests" in labels,"not every original source and test was archived")
    return {k:identity(p) for k,p in sources.items()},metadata


def validate_staged(directory,manifest,prepared):
    require(prepared["staged_hashes"]==manifest["staged_hashes"],"prepared/completed staged input mismatch")
    stage=directory/"staged";app=stage/"app"
    staged={k:app/name for k,name in v.safe.RUNTIME_NAMES.items()}
    roms=list(stage.glob("*.sfc"));saves=list((app/"Saves").iterdir())
    require(len(roms)==len(saves)==1 and saves[0].name==roms[0].stem+".srm","isolated ROM/save inventory differs")
    staged.update(rom=roms[0],sram=saves[0],collector=stage/"collector.lua",inputs=stage/"inputs.lua")
    require(set(staged)==set(manifest["staged_hashes"]),"staged inventory differs")
    for label,path in staged.items():pinned(checked(path),manifest["staged_hashes"][label])
    for label in (*v.safe.RUNTIME_NAMES,"rom","collector"):
        require(manifest["staged_hashes"][label]==manifest["source_hashes"][label],"staged artifact differs from source")
    require(staged["sram"].read_bytes()==bytes(8192),"isolated zero SRAM changed")


def observations(records,cases):
    return {"route_counts":dict(sorted(Counter(r["route"] for r in records).items())),
        "execution_pc_observations":sum(len(r["exec_addresses"]) for r in records),
        "executed_helper_instructions":sum(len(r["exec_addresses"])-1 for r in records),
        "terminal_observations_not_executed":len(records),
        "pre_execution_opcode_peeks":sum(len(r["exec_opcode_peeks"]) for r in records),
        "cpu_data_reads":sum(r["reads_total"] for r in records),
        "rom_byte_reads":sum(len(r["rom_reads"]) for r in records),
        "rom_byte_reads_per_bank":{f"{bank:02X}":sum(a>>16==bank for r in records for a,_ in r["rom_reads"]) for bank in (0x42,0x43)},
        "stack_accesses":sum(len(r["stack_accesses"]) for r in records),
        "post_sp_change_observations":sum(len(r["sp_observations"]) for r in records),
        "cpu_byte_writes":sum(len(r["writes"]) for r in records),
        "final_changed_wram_bytes":sum(len(r["changes"]) for r in records),
        "per_entry_sp":{f"{sp:04X}":{"case_count":sum(c["cpu"]["sp"]==sp for c in cases),"minimum_observed_sp":min(r["minimum_sp"] for r,c in zip(records,cases,strict=True) if c["cpu"]["sp"]==sp)} for sp in v.ENTRY_STACKS}}


def collect():
    _,code,payload,registry,certificate,_=v.verified_cartridge()
    cases=v.model.build_cases(payload,registry)
    require(len(cases)==3184 and v.digest(v.canonical_json(cases))==CASE_SHA256,"full model contract drift")
    prior=pinned(ROOT/"references/schala_package_helper_v2_stack.json",V2_REFERENCE_SHA256)
    accepted=[];paired_rows=[];sources=None
    for repetition,(suffix,manifest_sha) in enumerate(RUNS,1):
        directory=ROOT/"private/test_runs"/(PREFIX+suffix)
        pinned(checked(directory/"manifest.json"),manifest_sha)
        manifest=private_json(directory/"manifest.json");prepared=private_json(directory/"launch_inputs.json")
        require(manifest["schema"]==v.SCHEMA and manifest["passed"] is True and manifest["subset_only"] is False and manifest["case_count"]==3184 and manifest["repetition"]==repetition,"accepted full-run boundary differs")
        require(prepared["schema"]==v.SCHEMA and prepared["execution_status"]=="prepared-not-yet-executed" and prepared["source_hashes"]==manifest["source_hashes"],"prepared/completed source identity differs")
        require(manifest["trace_sha256"]==TRACE_SHA256 and manifest["case_contract_sha256"]==prepared["case_contract_sha256"]==CASE_SHA256 and manifest["helper_sha256"]==prepared["helper_sha256"]==v.HELPER_SHA256 and manifest["helper_size"]==prepared["helper_size"]==577 and manifest["helper_code_base"]==prepared["helper_code_base"]==v.CODE,"pinned native input/result identities differ")
        require(manifest["sources_and_staged_inputs_unchanged"] is True and manifest["no_rom_write_or_patch"] is True and manifest["production_hook_allocation_or_integration"] is False and manifest["pointed_stream_execution"] is False,"accepted scope/preservation differs")
        current,snapshots=source_snapshots(directory,manifest,prepared)
        if sources is not None:require(current==sources,"matched source identities differ")
        sources=current
        validate_staged(directory,manifest,prepared)
        pinned(checked(directory/"trace.json"),TRACE_SHA256)
        pinned(checked(directory/"case_contract.json"),CASE_SHA256)
        require(private_json(directory/"case_contract.json")==cases,"retained case contract differs from current model")
        require(checked(directory/"helper.bin").read_bytes()==code,"retained ROM helper differs")
        trace=private_json(directory/"trace.json")
        require(trace["schema"]==v.SCHEMA and trace["error"] is None and len(trace["records"])==3184,"trace schema/count/termination differs")
        records=trace["records"]
        for row,case in zip(records,cases,strict=True):v.validate_record(row,case,code=code,registry=registry,payload=payload)
        hashes=[{"name":r["name"],"registry_before_sha256":v.digest(bytes.fromhex(r["input_fixture_before_hex"])),"registry_after_sha256":v.digest(bytes.fromhex(r["input_fixture_after_hex"])),"descriptor_before_sha256":v.digest(bytes.fromhex(r["descriptor_fixture_before_hex"])),"descriptor_after_sha256":v.digest(bytes.fromhex(r["descriptor_fixture_after_hex"]))} for r in records]
        pinned(checked(directory/"rom_input_fixture_hashes.json"),manifest["rom_input_fixture_hashes_sha256"])
        require(private_json(directory/"rom_input_fixture_hashes.json")==hashes,"per-case immutable input hash evidence differs")
        pinned(checked(directory/"progress.json"),manifest["progress_sha256"])
        paired_rows.append(records)
        accepted.append({"run_id":PREFIX+suffix,"manifest":manifest,"observations":observations(records,cases),"source_snapshot_manifest":snapshots,"artifact_identities":artifacts(directory)})
    require(paired_rows[0]==paired_rows[1],"paired complete native traces differ")
    archive=ROOT/"private/test_runs"/(PREFIX+"before_strict_schema_sources")
    pinned(checked(archive/"manifest.json"),HISTORY_ARCHIVE_SHA256)
    history_sources=private_json(archive/"manifest.json")
    for row in history_sources["sources"]:
        pinned(checked(ROOT/row["archive"]),row["sha256"])
        require((ROOT/row["archive"]).stat().st_size==row["size"],"historical source size differs")
    directory=ROOT/"private/test_runs"/(PREFIX+"explore1")
    pinned(checked(directory/"manifest.json"),history_sources["explore1_manifest_sha256"])
    historical=private_json(directory/"manifest.json")
    historical_sources={row["label"]:row["sha256"] for row in history_sources["sources"]}
    for label,sha in historical["source_hashes"].items():
        require(sha==historical_sources.get(label,sources[label]["sha256"]),"historical source is not preserved")
    pinned(checked(directory/"trace.json"),EXPLORE_TRACE_SHA256)
    pinned(checked(directory/"case_contract.json"),historical["case_contract_sha256"])
    require(private_json(directory/"case_contract.json")==cases[:130],"historical subset model differs")
    require(checked(directory/"helper.bin").read_bytes()==code,"historical helper differs")
    records=private_json(directory/"trace.json")["records"]
    require(len(records)==130 and historical["subset_only"] is True,"exploratory boundary differs")
    for row,case in zip(records,cases[:130],strict=True):v.validate_record(row,case,code=code,registry=registry,payload=payload)
    return {"schema":v.SCHEMA+"-evidence","version":3,"date":"2026-09-08","evidence_level":"verified-runtime",
        "gate":"BA-NATIVE-INTEGRATION-DESIGN","subgate":"BA-NATIVE-ROM-CODE-REGISTRY-CONFORMANCE",
        "evidence_scope":"original ROM helper, immutable original ROM registry and certified descriptor transport; synthetic normal calls with interrupts disabled",
        "source_identities":sources,"evidence_collector_identity":identity(Path(__file__).resolve()),"report_identity":identity(ROOT/"docs/schala_package_helper_v3_rom.md"),"preserved_v2_reference":prior,
        "fixture_contract":{"rom_sha256":v.ROM_SHA256,"code_origin":v.CODE,"code_size":577,"code_sha256":v.HELPER_SHA256,"registry_span":[0x430000,0x430500],"payload_span":[0x420000,0x420381],"registry_sha256":v.model.REGISTRY_SHA256,"payload_sha256":v.model.PAYLOAD_SHA256,"entry_bridge_span":[v.ENTRY_BRIDGE,v.ENTRY_BRIDGE+4],"tails":v.TAILS,"entry_stacks":list(v.ENTRY_STACKS),"maximum_helper_stack_depth":52,"package_certificate":certificate},
        "accepted_runs":accepted,"matched_trace_sha256":TRACE_SHA256,"case_contract_sha256":CASE_SHA256,
        "history":[{"run_id":PREFIX+"explore1","status":"130 native cases preserved as exploratory, superseded by strict scalar schema and prelaunch complete source archival","manifest":historical,"current_strict_validator_revalidated_offline":True,"artifact_identities":artifacts(directory)}],"history_source_archive_identities":artifacts(archive),
        "limits":["Diagnostic bindings are not production allocations or selector bindings.","All helper instructions are observed inside an exact span; allowable instruction starts are not independently disassembled.","Opcode values are pre-execution debugger peeks, not independent actual opcode bus fetches.","Pointed terminal streams are certified but never executed or read as stream bytes.","Complete final WRAM diff and CPU writes apply to the declared synthetic disabled-interrupt/DMA policy.","Stack-relative operand guard covers a one-or-two-byte span rather than independently emulating M-state access width.","No game hook, action completion, real game interrupt/stack ownership, or logical PC 07 integration is established."],
        "reproduce":["python -B -m unittest discover -s tests -p test_schala_package_helper_v3_rom.py","python -B tools/collect_schala_package_helper_v3_rom_evidence.py"]}


def main():
    data=v.canonical_json(collect())
    sys.stdout.buffer.write(data)
    return 0


if __name__=="__main__":raise SystemExit(main())
