"""Observe the unchanged v2 helper executing from original ROM with ROM registry.

This separate v3 harness uses an independently guarded original test cartridge.
It writes only synthetic WRAM setup and peripheral control, never a ROM image.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from typing import Any
import run_schala_package_helper_v2_stack as v2
import schala_package_helper_v3_rom_model as model

ROOT=Path(__file__).resolve().parents[1]
safe=v2.safe
COLLECTOR=ROOT/"tools/mesen_schala_package_helper_v3_rom.lua"
TESTS=ROOT/"tests/test_schala_package_helper_v3_rom.py"
DEFAULT_ROM=ROOT/"private/test_runs/original_package_20260908_build1/original_package_test.sfc"
ROM_SHA256="1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b"
HELPER_SHA256="7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b"
CODE=model.CODE
ENTRY_BRIDGE=model.ENTRY_BRIDGE
TAILS=model.TAILS
ENTRY_STACKS=model.ENTRY_STACKS
SCHEMA="project-epoch-package-helper-v3-rom-code-registry"
SP_CHANGING_OPCODES=v2.SP_CHANGING_OPCODES
STACK_RELATIVE_OPCODES=v2.STACK_RELATIVE_OPCODES
STACK_IMPLICIT_OPCODES=v2.STACK_IMPLICIT_OPCODES
ConformanceError=v2.ConformanceError
canonical_json=v2.canonical_json
digest=v2.digest
lua_value=v2.lua_value


def verified_cartridge():
    rom=safe.resolve_private_file(DEFAULT_ROM,"reviewed original diagnostic cartridge")
    data=rom.read_bytes()
    if len(data)!=0x800000 or digest(data)!=ROM_SHA256:raise ConformanceError("immutable original cartridge identity mismatch")
    payload,registry,certificate=model.original_components()
    code=data[CODE:CODE+577]
    if digest(code)!=HELPER_SHA256 or data[0x420000:0x420000+len(payload)]!=payload or data[0x430000:0x430500]!=registry:
        raise ConformanceError("original ROM component identity mismatch")
    for address in TAILS.values():
        if data[0x400000+address:0x400000+address+2]!=bytes((0x80,0xFE)):
            raise ConformanceError("fixed ROM observation tail differs")
    if data[0x408060:0x408064]!=bytes((0x5C,0,0,0x41)):raise ConformanceError("fixed ROM entry bridge differs")
    directory=rom.parent
    completed=safe.resolve_private_file(directory/"completion.json","guarded cartridge completion")
    receipt=safe.resolve_private_file(directory/"audited-build.json","guarded cartridge audit")
    if digest(receipt.read_bytes())!="217267873a81fc537e124113de7c9517e3cdb88ee1ea46abb3225246892c69a0":raise ConformanceError("approved original build receipt identity mismatch")
    completion=json.loads(completed.read_bytes());audit=json.loads(receipt.read_bytes())
    if canonical_json(audit["package_certificate"])!=canonical_json(certificate):raise ConformanceError("original command-policy certificate differs")
    if completion.get("status")!="written-and-rehashed" or completion.get("rom")!={"size":len(data),"sha256":ROM_SHA256}:
        raise ConformanceError("reviewed original cartridge completion mismatch")
    if completion.get("audited_build_sha256")!=digest(receipt.read_bytes()) or audit["intent_manifest"]["target"]!=completion["rom"]:
        raise ConformanceError("cartridge completion/audit provenance mismatch")
    if audit["complete_diff_audit"].get("status")!="images-valid" or not audit["complete_diff_audit"].get("complete_diff_coverage") or audit["production_approval"] is not False:
        raise ConformanceError("original diagnostic complete-diff guard did not pass")
    return data,code,payload,registry,certificate,{"cartridge_completion":completed,"cartridge_build_audit":receipt}


def validate_fixture_spans(cases,code):
    if type(code) is not bytes or len(code)!=577 or digest(code)!=HELPER_SHA256:
        raise ConformanceError("fixed relocated original helper required")
    validate_case_setup(cases)


def validate_case_setup(cases):
    for c in cases:
        sp=c["cpu"]["sp"];depth=52 if c["frame_allocated"] else 8
        if type(sp) is not int or sp not in ENTRY_STACKS or c["stack_depth_limit"]!=depth or c["stack_span"]!=[0x7E0000+sp-depth+1,0x7E0000+sp+1]:
            raise ConformanceError("synthetic stack fixture differs")
        if c["patches"]!=v2.word_bytes(0x7E9877,c["selector"])+v2.word_bytes(0x7EA0B3,c["flag"]):
            raise ConformanceError("setup contains anything other than exact selector/flag WRAM words")
        for a,value in c["expected_rom_reads"]:
            if not ((0x420000<=a<0x420381) or (0x430000<=a<0x430500)) or type(value) is not int or not 0<=value<=255:
                raise ConformanceError("expected data read outside immutable ROM input spans")


def validate_execution_addresses(record,*,code:bytes,code_base:int=CODE):
    pcs=record.get("exec_addresses");peeks=record.get("exec_opcode_peeks")
    if type(pcs) is not list or not 2<=len(pcs)<=10000 or type(record.get("instructions")) is not int or record["instructions"]!=len(pcs):
        raise ConformanceError("complete execution sequence missing")
    if any(type(pc) is not int or not 0<=pc<=0xFFFFFF for pc in pcs):
        raise ConformanceError("execution PC must be an exact 24-bit integer")
    if pcs[0]!=code_base or pcs[-1]!=TAILS.get(record.get("route")):
        raise ConformanceError("exact ROM entry or terminal tail differs")
    if any(type(pc) is not int or not code_base<=pc<code_base+len(code) for pc in pcs[:-1]):
        raise ConformanceError("execution leaves exact ROM helper extent")
    expected=[code[pc-code_base] for pc in pcs[:-1]]+[0x80]
    if not isinstance(peeks,list) or any(type(value) is not int for value in peeks) or peeks!=expected:
        raise ConformanceError("pre-execution opcode peeks differ from exact mapped ROM bytes")


def validate_record_shapes(record):
    """Reject numeric equality aliases before comparing native JSON evidence."""
    if type(record) is not dict:
        raise ConformanceError("native record must be an object")
    cpu=record.get("cpu")
    limits={"a":0xFFFF,"x":0xFFFF,"y":0xFFFF,"d":0xFFFF,"dbr":0xFF,"sp":0xFFFF,"ps":0xFF}
    if type(cpu) is not dict or set(cpu)!=set(limits)|{"emulationMode"}:
        raise ConformanceError("native CPU keys differ from the exact register schema")
    if type(cpu["emulationMode"]) is not bool:
        raise ConformanceError("emulationMode must be a boolean")
    if any(type(cpu[key]) is not int or not 0<=cpu[key]<=limit for key,limit in limits.items()):
        raise ConformanceError("native CPU register is not an exact bounded integer")
    for key,maximum in (("writes",8192),("changes",131072),("rom_reads",256)):
        rows=record.get(key)
        if type(rows) is not list or len(rows)>maximum:
            raise ConformanceError(key+" must be a bounded list")
        for row in rows:
            if type(row) is not list or len(row)!=2 or any(type(value) is not int for value in row):
                raise ConformanceError(key+" requires exact integer address/byte pairs")
            if not 0<=row[0]<=0xFFFFFF or not 0<=row[1]<=0xFF:
                raise ConformanceError(key+" address or byte exceeds its native width")


def validate_record(record: dict[str, Any], case: dict[str, Any], *,
                    code: bytes, registry: bytes, payload: bytes, code_base: int = CODE) -> None:
    validate_record_shapes(record)
    if not isinstance(code,bytes) or not 1<=len(code)<=0x6000:
        raise ConformanceError("exact assembled opcode bytes required")
    code_size=len(code)
    try:
        validate_execution_addresses(record,code=code,code_base=code_base)
    except ConformanceError as exc:
        raise ConformanceError(str(exc)) from exc
    if record.get("name")!=case["name"] or record.get("route")!=case["route"]:
        raise ConformanceError("unexpected case identity or terminal route")
    if record.get("cpu")!=case["expected_cpu"]:
        raise ConformanceError(f"{case['name']}: CPU mismatch: {record.get('cpu')} expected {case['expected_cpu']}")
    start,end=case["stack_span"]
    baseline=dict(case["patches"])
    output=dict(case["expected_writes"])
    expected_changes={a:v for a,v in output.items() if v!=baseline.get(a,0xA5)}
    writes=record.get("writes",[])
    for address,value in writes:
        if not start<=address<end and address not in output:
            raise ConformanceError(f"{case['name']}: undeclared CPU write {address:06X}")
    if {a for a,_ in writes if a in output}!=set(output):
        raise ConformanceError("incomplete required output-write footprint")
    actual_pub=[[a,v] for a,v in writes if 0x7E5DAC<=a<0x7E5DFD]
    expected_pub=[[a,v] for a,v in case["expected_writes"] if 0x7E5DAC<=a<0x7E5DFD]
    if actual_pub!=expected_pub:
        raise ConformanceError("ordered publication byte mismatch")
    actual_changes={a:v for a,v in record.get("changes",[]) if not start<=a<end}
    if actual_changes!=expected_changes:
        raise ConformanceError("complete WRAM diff exceeds exact stack/output contract")
    # The complete final WRAM diff must follow from the exact final CPU write
    # to each byte, including stack memory. No unexplained stack delta can hide
    # inside an otherwise allowed maximum frame extent.
    final_writes=dict(writes)
    full_expected_changes=[[a,value] for a,value in sorted(final_writes.items())
        if value!=baseline.get(a,0xA5)]
    if record.get("changes")!=full_expected_changes:
        raise ConformanceError("complete WRAM diff does not equal the final CPU-write ledger")
    model.require_components(payload,registry)
    if record.get("input_fixture_before_hex")!=registry.hex() or record.get("input_fixture_after_hex")!=registry.hex():
        raise ConformanceError("immutable ROM registry/targets changed")
    if record.get("descriptor_fixture_before_hex")!=payload.hex() or record.get("descriptor_fixture_after_hex")!=payload.hex():
        raise ConformanceError("immutable original descriptor/terminal bytes changed")
    for key in ("retired_scratch_before_hex","retired_scratch_after_hex"):
        if record.get(key)!=bytes([0xA5]*128).hex():
            raise ConformanceError("retired global scratch fixture changed")
    if record.get("rom_reads")!=case["expected_rom_reads"]:
        raise ConformanceError("exact ordered CPU ROM-read mismatch")
    count=record.get("reads_total")
    if type(count) is not int or not len(case["expected_rom_reads"])<=count<=10000:
        raise ConformanceError("CPU data-read bound missing or invalid")
    minimum=record.get("minimum_sp")
    if type(minimum) is not int or not case["cpu"]["sp"]-case["stack_depth_limit"]<=minimum<=case["cpu"]["sp"]:
        raise ConformanceError("observed SP exceeds exact frame/call depth")
    pcs=record["exec_addresses"]
    required_observations=[(i+1,pcs[i]) for i in range(1,len(pcs))
        if code[pcs[i-1]-code_base] in SP_CHANGING_OPCODES]
    observations=record.get("sp_observations")
    if not isinstance(observations,list) or not observations:
        raise ConformanceError("executed stack-pointer observations missing")
    if any(not isinstance(row,list) or len(row)!=3 or any(type(v) is not int for v in row)
           for row in observations):
        raise ConformanceError("invalid execution SP observation tuple")
    if [(ordinal,pc) for ordinal,pc,_ in observations]!=required_observations:
        raise ConformanceError("SP observation sequence does not cover every executed SP-changing instruction")
    seen_minimum=case["cpu"]["sp"]
    for ordinal,pc,sp in observations:
        if not case["cpu"]["sp"]-case["stack_depth_limit"]<=sp<=case["cpu"]["sp"]:
            raise ConformanceError("execution SP observation exceeds exact frame depth")
        seen_minimum=min(seen_minimum,sp)
    accesses=record.get("stack_accesses")
    if not isinstance(accesses,list) or not accesses:
        raise ConformanceError("complete stack access evidence missing")
    observed_writes=[]
    previous_ordinal=0
    for access in accesses:
        if not isinstance(access,list) or len(access)!=5:
            raise ConformanceError("invalid stack-access tuple")
        ordinal,address,value,sp,mode=access
        if any(type(v) is not int for v in access) or mode not in (0,1) or not 0<=value<=255:
            raise ConformanceError("invalid stack-access values")
        if not 1<=ordinal<len(pcs) or ordinal<previous_ordinal:
            raise ConformanceError("stack access lacks ordered executed-instruction ownership")
        previous_ordinal=ordinal
        offset=pcs[ordinal-1]-code_base
        opcode=code[offset]
        if not start<=address<end or not case["cpu"]["sp"]-case["stack_depth_limit"]<=sp<=case["cpu"]["sp"]:
            raise ConformanceError("stack access exceeds exact fixture bounds")
        low=address&0xFFFF
        if opcode in STACK_RELATIVE_OPCODES:
            if mode!=STACK_RELATIVE_OPCODES[opcode] or low<=sp:
                raise ConformanceError("stack-relative local access is not strictly above live SP")
            if offset+1>=len(code) or not sp+code[offset+1]<=low<=sp+code[offset+1]+1:
                raise ConformanceError("stack-relative local address differs from owning instruction operand")
        elif opcode in STACK_IMPLICIT_OPCODES:
            if mode!=STACK_IMPLICIT_OPCODES[opcode] or low<sp:
                raise ConformanceError("implicit stack operation mode or callback SP mismatch")
        else:
            raise ConformanceError("stack access is owned by an instruction without stack memory semantics")
        seen_minimum=min(seen_minimum,sp)
        if mode==1:observed_writes.append([address,value])
    if minimum!=seen_minimum:
        raise ConformanceError("reported minimum SP differs from complete stack observations")
    expected_depth=(52 if case["countbits_reached"] else 50) if case["frame_allocated"] else 8
    if minimum!=case["cpu"]["sp"]-expected_depth:
        raise ConformanceError("observed minimum SP differs from the executed route frame depth")
    if observed_writes!=[[a,v] for a,v in writes if start<=a<end]:
        raise ConformanceError("stack-write liveness evidence differs from complete write trace")


def archive_guarded_sources(output,guarded,source_before,*,source_root=ROOT):
    """Exclusively preserve exact source bytes before any native process starts."""
    directory=output/"source_snapshots"
    directory.mkdir(exist_ok=False)
    rows=[];snapshots={}
    for label,path in sorted(guarded.items()):
        if path.suffix.lower() not in (".py",".asm",".lua",".json"):
            continue
        if re.fullmatch(r"[a-z0-9_]+",label) is None:
            raise ConformanceError("unsafe guarded source archive label")
        expected=source_before[label]
        if safe.sha256_file(path)!=expected:
            raise ConformanceError("guarded source drift before archival: "+label)
        target=directory/(label+"--"+expected+path.suffix.lower())
        safe.copy_new_regular_file(path,target,label)
        if safe.sha256_file(target)!=expected:
            raise ConformanceError("guarded source archive identity mismatch: "+label)
        rows.append({"label":label,"source":path.relative_to(source_root).as_posix(),
            "archive":target.relative_to(output).as_posix(),"size_bytes":target.stat().st_size,"sha256":expected})
        snapshots[label]=target
    metadata=output/"source_snapshots.json"
    with metadata.open("xb") as handle:
        handle.write(canonical_json({"schema":SCHEMA+"-source-snapshots","execution_status":"prepared-not-yet-executed","sources":rows}))
    snapshots["snapshot_metadata"]=metadata
    return snapshots,{label:safe.sha256_file(path) for label,path in snapshots.items()}


def run(output_dir: Path, *, limit: int | None = None,
        repetition: int = 1, timeout: int = 900, code_base: int = CODE) -> dict[str, Any]:
    private = safe.canonical_private_root()
    data,code,payload_bytes,registry,certificate,receipts=verified_cartridge()
    rom=safe.resolve_private_file(DEFAULT_ROM,"reviewed original diagnostic cartridge",private_root=private)
    if code_base!=CODE or not 1<=timeout<=1200 or repetition not in (1,2):
        raise ConformanceError("fixed ROM placement or bounded launch parameters differ")
    runtime={label:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/name,label,private_root=private)
        for label,name in safe.RUNTIME_NAMES.items()}
    for label,path in runtime.items():safe.require_identity(path,label)
    output=safe.prepare_private_output_dir(output_dir,private_root=private,forbidden_roots=(rom.parent,safe.DEFAULT_MESEN.parent))
    guarded={**runtime,**receipts,"rom":rom,"collector":COLLECTOR,"launcher":Path(__file__),"tests":TESTS,
        "helper_source":v2.HELPER,"v2_validation_source":Path(v2.__file__),"host_model":Path(model.__file__),
        "original_fixture_source":Path(model.fixtures.__file__),"package_policy_source":Path(model.fixtures.policy.__file__),
        "host_adapter":Path(model.adapter.__file__),"isolation_library":Path(safe.__file__),
        "v1_contract_library":Path(v2.v1.__file__),"v0_validation_library":Path(v2.prior.__file__),
        "policy_reference":model.fixtures.policy.REFERENCE_PATH,"grammar_source":Path(model.fixtures.policy.grammar.__file__),
        "grammar_reference":model.fixtures.policy.grammar.REFERENCE_PATH,"adapter_reference":model.adapter.REFERENCE_PATH}
    source_before={key:safe.sha256_file(path) for key,path in guarded.items()}
    snapshots,snapshot_before=archive_guarded_sources(output,guarded,source_before)
    cases=model.build_cases(payload_bytes,registry)
    if limit is not None:
        if not 1<=limit<=len(cases):raise ConformanceError("invalid bounded case subset")
        cases=cases[:limit]
    validate_fixture_spans(cases,code)
    (output/"original_package_certificate.json").write_bytes(canonical_json(certificate))
    (output/"helper.bin").write_bytes(code)
    stage = output / "staged"
    app = stage / "app"
    saves = app / "Saves"
    saves.mkdir(parents=True)
    staged: dict[str,Path] = {}
    for label,name in safe.RUNTIME_NAMES.items():
        path=app/name
        safe.copy_new_regular_file(runtime[label],path,label)
        staged[label]=path
    stem="pe_package_" + secrets.token_hex(12)
    staged["rom"]=stage/(stem+".sfc")
    safe.copy_new_regular_file(rom,staged["rom"],"rom")
    staged["sram"]=saves/(stem+".srm")
    staged["sram"].write_bytes(bytes(8192))
    staged["collector"]=stage/"collector.lua"
    safe.copy_new_regular_file(COLLECTOR,staged["collector"],"collector")
    payload={"schema":SCHEMA,"code_hex":code.hex(),"code":code_base,"tails":TAILS,
             "entry_bridge":ENTRY_BRIDGE,"registry_hex":registry.hex(),"descriptor_hex":payload_bytes.hex(),"cases":[{k:v for k,v in c.items() if not k.startswith("expected_")} for c in cases]}
    staged["inputs"]=stage/"inputs.lua"
    staged["inputs"].write_text("return " + lua_value(payload) + "\n", encoding="utf-8")
    (output/"case_contract.json").write_bytes(canonical_json(cases))
    staged_before={k:safe.sha256_file(v) for k,v in staged.items()}
    for key in (*runtime,"rom","collector"):
        if staged_before[key] != source_before[key]:
            raise ConformanceError(f"staged {key} differs from pinned source before execution")
    (output/"launch_inputs.json").write_bytes(canonical_json({"schema":SCHEMA,
        "evidence_level":"hypothesis","execution_status":"prepared-not-yet-executed",
        "source_hashes":source_before,"staged_hashes":staged_before,
        "source_snapshot_hashes":snapshot_before,
        "helper_sha256":digest(code),"helper_size":len(code),"helper_code_base":code_base,
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "runtime_sizes":{label:path.stat().st_size for label,path in runtime.items()},"rom_mutation":False,"pointed_stream_execution":False}))
    env=safe.minimal_subprocess_environment()
    for key,parts in {"USERPROFILE":("profile",), "APPDATA":("profile","AppData","Roaming"),
                      "LOCALAPPDATA":("profile","AppData","Local"),"TEMP":("temp",),"TMP":("temp",)}.items():
        p=stage.joinpath(*parts)
        p.mkdir(parents=True,exist_ok=True)
        env[key]=str(p)
    env.update(PE_PACKAGE_PROTOCOL=SCHEMA, PE_PACKAGE_INPUT=str(staged["inputs"]),
               PE_PACKAGE_TRACE=str(output/"trace.json"),PE_PACKAGE_PROGRESS=str(output/"progress.json"))
    command=[str(staged["mesen"]),"--testRunner",f"--timeout={timeout}",
        "--doNotSaveSettings","--debug.scriptWindow.allowIoOsAccess=true",
        str(staged["collector"]),str(staged["rom"])]
    proc=None
    error=None
    try:
        proc=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=timeout+15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0,check=False)
        (output/"process.log").write_bytes(proc.stdout+proc.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:
        error=str(exc)
    # Preserve the complete isolated stage even on failure; never copy a shared save.
    safe.require_file_hashes_unchanged(guarded,source_before,"source")
    safe.require_file_hashes_unchanged(snapshots,snapshot_before,"archived source")
    safe.require_file_hashes_unchanged(staged,staged_before,"staged input")
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged["sram"].name)
    if error or proc is None or proc.returncode != 41:
        raise ConformanceError(f"isolated Mesen execution failed: {error or proc.returncode}; {output}")
    trace_path=output/"trace.json"
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=192*1024*1024),"trace")
    if trace.get("schema") != SCHEMA or trace.get("error") is not None or len(trace.get("records",[])) != len(cases):
        raise ConformanceError("trace schema, termination, or case count mismatch")
    for record,case in zip(trace["records"],cases,strict=True):
        validate_record(record,case,code=code,registry=registry,payload=payload_bytes,code_base=code_base)
    fixture_hashes=[{"name":r["name"],
        "registry_before_sha256":digest(bytes.fromhex(r["input_fixture_before_hex"])),
        "registry_after_sha256":digest(bytes.fromhex(r["input_fixture_after_hex"])),
        "descriptor_before_sha256":digest(bytes.fromhex(r["descriptor_fixture_before_hex"])),
        "descriptor_after_sha256":digest(bytes.fromhex(r["descriptor_fixture_after_hex"]))} for r in trace["records"]]
    (output/"rom_input_fixture_hashes.json").write_bytes(canonical_json(fixture_hashes))
    reproduction=["python","tools/run_schala_package_helper_v3_rom.py","--output-dir",
                  "private/test_runs/package_helper_v3_rom_NEW","--repetition",str(repetition),
                  "--timeout",str(timeout),"--code-base",f"0x{code_base:06X}"]
    if limit is not None:
        reproduction.extend(["--limit",str(limit)])
    manifest={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"immutable-original-rom-code-registry-transport-only",
        "repetition":repetition,"case_count":len(cases),"subset_only":limit is not None,
        "case_categories":{k:sum(c["category"]==k for c in cases) for k in sorted({c["category"] for c in cases})},
        "passed":True,"source_hashes":source_before,"staged_hashes":staged_before,
        "source_snapshot_hashes":snapshot_before,
        "helper_size":len(code),"helper_code_base":code_base,"entry_bridge":ENTRY_BRIDGE,"helper_sha256":digest(code),"trace_sha256":safe.sha256_file(trace_path),
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "rom_input_fixture_hashes_sha256":safe.sha256_file(output/"rom_input_fixture_hashes.json"),
        "progress_sha256":safe.sha256_file(output/"progress.json"),
        "cpu_instruction_counts":{"min":min(r["instructions"] for r in trace["records"]),
                                  "max":max(r["instructions"] for r in trace["records"])},
        "sources_and_staged_inputs_unchanged":True,"no_rom_write_or_patch":True,
        "rom_descriptor_bank":0x42,"rom_registry_bank":0x43,"helper_execution_bank":0x41,"pointed_stream_execution":False,"pre_execution_opcode_peeks":True,"independent_opcode_bus_fetch_observation":False,"complete_execution_span_guard":True,"complete_execution_pc_sequences":True,"no_global_scratch_access":True,"stack_entry_values":list(ENTRY_STACKS),"no_game_input":True,"production_hook_allocation_or_integration":False,
        "interrupt_policy":"synthetic IRQ/NMI sources disabled; no game interrupt claim",
        "reproduce":reproduction}
    (output/"manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--repetition",type=int,default=1)
    parser.add_argument("--limit",type=int)
    parser.add_argument("--timeout",type=int,default=900)
    parser.add_argument("--code-base",type=lambda value:int(value,0),default=CODE)
    args=parser.parse_args()
    print(json.dumps(run(args.output_dir,limit=args.limit,repetition=args.repetition,timeout=args.timeout,code_base=args.code_base),indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
