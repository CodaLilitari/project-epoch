#!/usr/bin/env python3
"""Prove original helper ROM reads using one unchanged synthetic ExHiROM carrier.

The existing SHA benchmark's original bytes are descriptor-shaped transport
fixtures only. This tool assembles original WRAM code, never mutates a ROM,
and never reads or executes a pointed stream. All raw artifacts stay private.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
from typing import Any

import audit_schala_player_tech_package_bank_adapter_v0 as adapter
import run_mesen_field_animation_probe_v0 as safe
import run_schala_package_helper_conformance_v0 as prior
import run_schala_package_helper_v1_rom_source as v1

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "tools/mesen_schala_package_helper_v2_stack.lua"
HELPER = ROOT / "asm/schala_package_helper_v2_stack.asm"
DEFAULT_ROM = ROOT / "private/test_runs/sha256_65c816/schala_sha256_profile1_benchmark.sfc"
ROM_SHA256 = "e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd"
ASAR_SHA256 = "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8"
ASAR = ROOT / "private/tools/asar-1.91/asar.exe"
CODE = 0x7F8000
ENTRY_BRIDGE = 0x7FF100  # Original JML setup; first helper opcode gets a callback.
TAILS = {"canonical": 0x7FF000, "success": 0x7FF010, "refusal": 0x7FF020}
RETIRED_SCRATCH = (0x7E4000, 0x7E4080)
ENTRY_STACKS = (0x1FEF,0x06D8,0x0034,0x0033,0x0008)
STACK_DEPTH_FRAMED = 52
STACK_DEPTH_UNFRAMED = 8
# The complete set of SP-changing and stack-memory opcodes in this helper.
SP_CHANGING_OPCODES = frozenset((0x08,0x48,0xDA,0x5A,0x8B,0xAB,0x7A,0xFA,0x68,0x28,0x20,0x60,0x1B))
STACK_RELATIVE_OPCODES = {0xA3:0,0x83:1,0x63:0,0xC3:0}
STACK_IMPLICIT_OPCODES = {0x08:1,0x48:1,0xDA:1,0x5A:1,0x8B:1,0xAB:0,0x7A:0,0xFA:0,0x68:0,0x28:0,0x20:1,0x60:0}
SCHEMA = "project-epoch-package-helper-v2-stack"


class ConformanceError(RuntimeError):
    """Fail-closed harness or independent execution mismatch."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def word_bytes(address: int, value: int) -> list[list[int]]:
    return [[address, value & 255], [address + 1, value >> 8]]


def input_cpu(index: int) -> dict[str, Any]:
    flags = (0x00, 0xC3, 0x4C, 0x8F)
    return {"a": 0xA55A, "x": 0xD3C7, "y": 0x8F69, "d": 0,
            "dbr": 0x7E, "sp": 0x1FEF, "ps": flags[index % len(flags)],
            "emulationMode": False}


FIXTURES = v1.FIXTURES
verified_rom_bytes = v1.verified_rom_bytes


def with_stack(case: dict[str, Any], sp: int, *, category: str | None = None) -> dict[str, Any]:
    c=copy.deepcopy(case)
    c["name"]+=f"-sp-{sp:04X}"
    if category is not None: c["category"]=category
    c["cpu"]["sp"]=sp
    c["expected_cpu"]["sp"]=sp
    high_ready=0x80<=c["selector"]<=0x8F and c["flag"]<=255
    framed=high_ready and sp>=STACK_DEPTH_FRAMED
    if high_ready and not framed:
        c["route"]="refusal"
        c["expected_cpu"]=dict(c["cpu"])
        c["expected_writes"],c["expected_rom_reads"]=[],[]
    c["frame_allocated"]=framed
    depth=STACK_DEPTH_FRAMED if framed else STACK_DEPTH_UNFRAMED
    c["stack_depth_limit"]=depth
    c["stack_span"]=[0x7E0000+sp-depth+1,0x7E0000+sp+1]
    return c


def build_cases(rom: bytes) -> list[dict[str, Any]]:
    base=v1.build_cases(rom)
    cases=[with_stack(c,sp) for sp in ENTRY_STACKS[:2] for c in base]
    boundary=(("canonical",0x7F,0,1),("primary",0x80,0,1),("alternate",0x80,0x40,1),
        ("unbound",0x80,0,0),("wide-flag",0x80,0x100,1),("wide-selector",0x100,0,1))
    for sp in ENTRY_STACKS[2:]:
        for name,selector,flag,valid in boundary:
            for status_index in range(4):
                c=v1.make_case(rom,f"boundary-{name}-status-{status_index}",selector,flag,
                    valid=valid,index=status_index)
                cases.append(with_stack(c,sp,category="stack-floor-and-underflow"))
    return cases


def validate_fixture_spans(cases: list[dict[str, Any]], code_size: int, code_base: int = CODE) -> None:
    v1.validate_fixture_spans(cases,code_size,code_base)
    protected=[(0x7E0080,0x7E0084),(0x7E3000,0x7E3500),RETIRED_SCRATCH,
        (0x7E9877,0x7E987A),(0x7EA0B3,0x7EA0B5),(0x7E5DAC,0x7E5DFD)]
    for c in cases:
        sp=c["cpu"]["sp"]
        if type(sp) is not int or sp not in ENTRY_STACKS:
            raise ConformanceError("entry SP outside explicit synthetic placements")
        depth=STACK_DEPTH_FRAMED if c["frame_allocated"] else STACK_DEPTH_UNFRAMED
        expected=[0x7E0000+sp-depth+1,0x7E0000+sp+1]
        if c["stack_span"]!=expected or c["stack_depth_limit"]!=depth or sp-depth<0:
            raise ConformanceError("declared stack extent or floor mismatch")
        start,end=expected
        if any(start<b and a<end for a,b in protected):
            raise ConformanceError("stack frame overlaps protected synthetic input/output span")


def lua_value(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ",".join("[" + json.dumps(k) + "]=" + lua_value(v) for k,v in value.items()) + "}"
    if isinstance(value, list):
        return "{" + ",".join(lua_value(v) for v in value) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


def assemble(output: Path, *, code_base: int = CODE) -> bytes:
    asar = safe.resolve_private_file(ASAR, "Asar")
    if asar.stat().st_size != 501248 or safe.sha256_file(asar) != ASAR_SHA256:
        raise ConformanceError("Asar1.91 identity mismatch")
    body = HELPER.read_text()
    wrapper = (f"norom\norg $000000\nbase ${code_base:06X}\n"
        "!PE_PH2_BINDINGS = $7E3000\n"
        "!PE_PH2_TARGETS = $7E3100\n!PE_PH2_CANONICAL_TAIL = $7FF000\n!PE_PH2_SUCCESS_TAIL = $7FF010\n"
        "!PE_PH2_REFUSAL_TAIL = $7FF020\n" + body)
    source = output / "helper.asm"
    target = output / "helper.bin"
    source.write_text(wrapper, encoding="utf-8")
    target.write_bytes(b"")
    proc = subprocess.run([str(asar), "--no-title-check", "--fix-checksum=off", str(source), str(target)],
        capture_output=True, timeout=20, check=False)
    (output / "asar.log").write_bytes(proc.stdout + proc.stderr)
    if proc.returncode:
        raise ConformanceError("raw helper assembly failed; inspect private asar.log")
    code = target.read_bytes()
    if not 1 <= len(code) <= 0x6000:
        raise ConformanceError("raw helper extent outside synthetic code window")
    return code


def validate_record(record: dict[str, Any], case: dict[str, Any], *,
                    code: bytes, code_base: int = CODE) -> None:
    if not isinstance(code,bytes) or not 1<=len(code)<=0x6000:
        raise ConformanceError("exact assembled opcode bytes required")
    code_size=len(code)
    try:
        v1.validate_execution_addresses(record,code_size=code_size,code_base=code_base)
    except v1.ConformanceError as exc:
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
    expected=bytearray(0x500)
    expected[0x100:]=bytes([0xA5])*0x400
    for address,value in case["patches"]:
        if 0x7E3000<=address<0x7E3500: expected[address-0x7E3000]=value
    if record.get("input_fixture_before_hex")!=expected.hex() or record.get("input_fixture_after_hex")!=expected.hex():
        raise ConformanceError("immutable registry/target input fixture changed")
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
    expected_depth=(52 if case["expected_rom_reads"] else 50) if case["frame_allocated"] else 8
    if minimum!=case["cpu"]["sp"]-expected_depth:
        raise ConformanceError("observed minimum SP differs from the executed route frame depth")
    if observed_writes!=[[a,v] for a,v in writes if start<=a<end]:
        raise ConformanceError("stack-write liveness evidence differs from complete write trace")


def run(output_dir: Path, *, limit: int | None = None,
        repetition: int = 1, timeout: int = 240, code_base: int = CODE) -> dict[str, Any]:
    private = safe.canonical_private_root()
    rom = safe.resolve_private_file(DEFAULT_ROM, "original synthetic benchmark", private_root=private)
    if rom.stat().st_size != 0x800000 or safe.sha256_file(rom) != ROM_SHA256:
        raise ConformanceError("original synthetic boot image identity mismatch")
    if not 1 <= timeout <= 900 or repetition not in (1,2):
        raise ConformanceError("invalid bounded launch parameters")
    validate_fixture_spans([],1,code_base)
    runtime = {label:safe.resolve_private_file(safe.DEFAULT_MESEN.parent / name, label, private_root=private)
               for label,name in safe.RUNTIME_NAMES.items()}
    identities = {label:safe.require_identity(path,label) for label,path in runtime.items()}
    output = safe.prepare_private_output_dir(output_dir, private_root=private,
        forbidden_roots=(rom.parent, safe.DEFAULT_MESEN.parent))
    guarded = {**runtime,"rom":rom,"collector":COLLECTOR,"launcher":Path(__file__),"asar":ASAR,
               "host_adapter":Path(adapter.__file__),"isolation_library":Path(safe.__file__),"v0_validation_library":Path(prior.__file__),"v1_contract_library":Path(v1.__file__)}
    guarded["helper"] = HELPER
    source_before = {k:safe.sha256_file(v) for k,v in guarded.items()}
    code = assemble(output,code_base=code_base)
    cases = build_cases(verified_rom_bytes())
    if limit is not None:
        if not 1 <= limit <= len(cases):
            raise ConformanceError("invalid case limit")
        cases = cases[:limit]
    validate_fixture_spans(cases,len(code),code_base)
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
             "entry_bridge":ENTRY_BRIDGE,"cases":[{k:v for k,v in c.items() if not k.startswith("expected_")} for c in cases]}
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
    safe.require_file_hashes_unchanged(staged,staged_before,"staged input")
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged["sram"].name)
    if error or proc is None or proc.returncode != 41:
        raise ConformanceError(f"isolated Mesen execution failed: {error or proc.returncode}; {output}")
    trace_path=output/"trace.json"
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=128*1024*1024),"trace")
    if trace.get("schema") != SCHEMA or trace.get("error") is not None or len(trace.get("records",[])) != len(cases):
        raise ConformanceError("trace schema, termination, or case count mismatch")
    for record,case in zip(trace["records"],cases,strict=True):
        validate_record(record,case,code=code,code_base=code_base)
    fixture_hashes=[{"name":r["name"],
        "before_sha256":digest(bytes.fromhex(r["input_fixture_before_hex"])),
        "after_sha256":digest(bytes.fromhex(r["input_fixture_after_hex"]))} for r in trace["records"]]
    (output/"wram_input_fixture_hashes.json").write_bytes(canonical_json(fixture_hashes))
    reproduction=["python","tools/run_schala_package_helper_v2_stack.py","--output-dir",
                  "private/test_runs/package_helper_v2_stack_NEW","--repetition",str(repetition),
                  "--timeout",str(timeout),"--code-base",f"0x{code_base:06X}"]
    if limit is not None:
        reproduction.extend(["--limit",str(limit)])
    manifest={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"immutable-original-rom-source-stack-frame-only",
        "repetition":repetition,"case_count":len(cases),"subset_only":limit is not None,
        "case_categories":{k:sum(c["category"]==k for c in cases) for k in sorted({c["category"] for c in cases})},
        "passed":True,"source_hashes":source_before,"staged_hashes":staged_before,
        "helper_size":len(code),"helper_code_base":code_base,"entry_bridge":ENTRY_BRIDGE,"helper_sha256":digest(code),"trace_sha256":safe.sha256_file(trace_path),
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "wram_input_fixture_hashes_sha256":safe.sha256_file(output/"wram_input_fixture_hashes.json"),
        "progress_sha256":safe.sha256_file(output/"progress.json"),
        "cpu_instruction_counts":{"min":min(r["instructions"] for r in trace["records"]),
                                  "max":max(r["instructions"] for r in trace["records"])},
        "sources_and_staged_inputs_unchanged":True,"no_rom_write_or_patch":True,
        "rom_source_banks":[0x41,0x42],"pointed_stream_execution":False,"complete_execution_span_guard":True,"complete_execution_pc_sequences":True,"no_global_scratch_access":True,"stack_entry_values":list(ENTRY_STACKS),"no_game_input":True,"production_hook_allocation_or_integration":False,
        "interrupt_policy":"synthetic IRQ/NMI sources disabled; no game interrupt claim",
        "reproduce":reproduction}
    (output/"manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--repetition",type=int,default=1)
    parser.add_argument("--limit",type=int)
    parser.add_argument("--timeout",type=int,default=240)
    parser.add_argument("--code-base",type=lambda value:int(value,0),default=CODE)
    args=parser.parse_args()
    print(json.dumps(run(args.output_dir,limit=args.limit,repetition=args.repetition,timeout=args.timeout,code_base=args.code_base),indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
