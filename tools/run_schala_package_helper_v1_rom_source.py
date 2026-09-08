#!/usr/bin/env python3
"""Prove original helper ROM reads using one unchanged synthetic ExHiROM carrier.

The existing SHA benchmark's original bytes are descriptor-shaped transport
fixtures only. This tool assembles original WRAM code, never mutates a ROM,
and never reads or executes a pointed stream. All raw artifacts stay private.
"""
from __future__ import annotations

import argparse
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

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "tools/mesen_schala_package_helper_v1_rom_source.lua"
HELPER = ROOT / "asm/schala_package_helper_v1_rom_source.asm"
DEFAULT_ROM = ROOT / "private/test_runs/sha256_65c816/schala_sha256_profile1_benchmark.sfc"
ROM_SHA256 = "e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd"
ASAR_SHA256 = "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8"
ASAR = ROOT / "private/tools/asar-1.91/asar.exe"
CODE = 0x7F8000
ENTRY_BRIDGE = 0x7FF100  # Original JML setup; first helper opcode gets a callback.
TAILS = {"canonical": 0x7FF000, "success": 0x7FF010, "refusal": 0x7FF020}
SCRATCH = (0x7E4000, 0x7E4080)
STACK = (0x7E1FE6, 0x7E1FF0)  # eight saved bytes plus one two-byte JSR
SCHEMA = "project-epoch-package-helper-v1-rom-source"


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


# Existing original SHA code and constants viewed only as descriptor-shaped bytes.
# These are explicitly not certified battle-command packages.
FIXTURES = {
    0x41: (0x0002, 0x0016, "d6b8165c0913a74324c7d46b24330ddd7fbcd99cf05b12d2fabf9b82fe2b91e7"),
    0x42: (0x0000, 0x0020, "04f93fd18db0bc237c01a03fe85c033f2c090085f0cd3d6301669ae4cc2bb8ab"),
}


def verified_rom_bytes() -> bytes:
    rom = safe.resolve_private_file(DEFAULT_ROM, "original synthetic benchmark")
    data = rom.read_bytes()
    if len(data) != 0x800000 or digest(data) != ROM_SHA256:
        raise ConformanceError("original synthetic ROM identity mismatch")
    for bank,(root,end,expected) in FIXTURES.items():
        if digest(data[bank*65536+root:bank*65536+end]) != expected:
            raise ConformanceError("immutable descriptor fixture drift")
    return data


def make_case(rom: bytes, name: str, selector: int = 0x80, flag: int = 0, *,
              bank: int = 0x42, root: int | None = None, valid: int = 1,
              bank_word: int | None = None, end_word: int | None = None,
              end_carry: int = 0, targets: list[int] | None = None,
              target_count: int | None = None, reserved0: int = 0,
              reserved1: int = 0, index: int = 0,
              category: str = "rom-source") -> dict[str, Any]:
    native_bank = bank if bank_word is None else bank_word
    fixture_root,fixture_end,_ = FIXTURES[bank]
    root = fixture_root if root is None else root
    end_word = fixture_end if end_word is None else end_word
    fixture = rom[bank*65536:(bank+1)*65536]
    default_targets = sorted({int.from_bytes(fixture[a:a+2], "little")
        for a in range(fixture_root+4,fixture_end,2)})
    targets = default_targets if targets is None else targets
    target_count = len(targets) if target_count is None else target_count
    patches = word_bytes(0x7E9877,selector)+word_bytes(0x7EA0B3,flag)
    if 0x80 <= selector <= 0x8F:
        entry=0x7E3000+(selector-0x80)*16
        fields=(valid,root,native_bank,end_word,end_carry,target_count,reserved0,reserved1)
        for i,value in enumerate(fields): patches += word_bytes(entry+i*2,value)
        target_base=0x7E3100+(selector-0x80)*64
        for i,value in enumerate(targets[:32]): patches += word_bytes(target_base+i*2,value)
    cpu=input_cpu(index)
    expected=dict(cpu)
    route="refusal"
    writes,reads=[],[]
    def read_word(offset: int) -> int:
        for a in (offset,offset+1): reads.append([native_bank*65536+a,rom[native_bank*65536+a]])
        return int.from_bytes(rom[native_bank*65536+offset:native_bank*65536+offset+2],"little")
    if selector < 0x80:
        route="canonical"
        expected.update(a=selector*2,ps=(cpu["ps"]&0x7C)|(2 if selector==0 else 0))
    elif (selector <= 0x8F and flag <= 255 and valid == 1 and native_bank in FIXTURES
          and reserved0 == reserved1 == 0 and target_count <= 32
          and end_carry in (0,1) and (end_carry == 0 or end_word == 0) and root <= 0xFFFC):
        m0=int.from_bytes(read_word(root).to_bytes(2,"little"),"big")
        m1=int.from_bytes(read_word(root+2).to_bytes(2,"little"),"big")
        actual_end=root+4+2*(m0.bit_count()+m1.bit_count())
        if actual_end <= 65536 and actual_end == end_word+65536*end_carry:
            allowed=(targets[:32]+[0xA5A5]*32)[:target_count]
            for a in range(root+4,actual_end,2):
                pointer=read_word(a)
                if pointer == 65535 or root <= pointer < actual_end or pointer not in allowed: break
            else:
                source=adapter.make_package_source(selector=selector,bank=native_bank,root_offset=root,
                    allocation_name="IMMUTABLE_ORIGINAL_ROM_BYTE_FIXTURE",source_kind="synthetic-test")
                model=adapter.simulate_descriptor_install(rom[native_bank*65536:(native_bank+1)*65536],source,a0b3=flag)
                route="success"
                expected.update(a=0,x=model.x_final,y=16,ps=(cpu["ps"]&0x4C)|0x23)
                writes+=word_bytes(0x7E9878,root)+word_bytes(0x7E0080,0)+word_bytes(0x7E0082,m1)
                first=root+4+(2*m0.bit_count() if flag else 0)
                for i,p in enumerate(model.publications):
                    read_word(first+i*2)
                    writes+=word_bytes(0x7E0000+p.activation_address,p.activation_word)
                    writes+=word_bytes(0x7E0000+p.script_address,p.script_offset)
                    writes+=word_bytes(0x7E0000+p.bank_address,p.bank_word)
                writes+=[[0x7EA0B3,0]]
    return {"name":name,"category":category,"selector":selector,"flag":flag,
        "cpu":cpu,"patches":patches,"route":route,"expected_cpu":expected,
        "expected_writes":writes,"expected_rom_reads":reads,
        "source_bank":native_bank,"source_root":root,"descriptor_end":end_word+65536*end_carry,
        "allowed_targets":targets[:32],"target_count":target_count}


def build_cases(rom: bytes) -> list[dict[str, Any]]:
    cases=[make_case(rom,f"canonical-{s:02X}",s,0xA55A,index=s,category="canonical-selector") for s in range(128)]
    for bank in FIXTURES:
        cases += [make_case(rom,f"rom-{bank:02X}-flag-{f:02X}",flag=f,bank=bank,index=f,
            category="both-rom-banks-all-flag-bytes") for f in range(256)]
    for bank in range(256):
        cases.append(make_case(rom,f"bank-word-{bank:02X}",bank_word=bank,
            category="every-bank-word-low-byte"))
    for selector in range(0x80,0x100):
        cases.append(make_case(rom,f"unbound-{selector:02X}",selector,valid=0,category="unbound-selector"))
    for selector in range(0x80,0x90):
        for bank in FIXTURES:
            for flag in (0,0x40):
                cases.append(make_case(rom,f"bound-{selector:02X}-{bank:02X}-{flag}",selector,flag,bank=bank,
                    index=selector,category="each-high-selector-both-rom-banks"))
    for bank in FIXTURES:
        root,end,_=FIXTURES[bank]
        original=make_case(rom,"original",bank=bank)["allowed_targets"]
        for i in range(len(original)):
            targets=original[:i]+original[i+1:]
            for branch in (0,0x40):
                cases.append(make_case(rom,f"missing-target-{bank:02X}-{i}-{branch}",flag=branch,bank=bank,
                    targets=targets,category="every-allowlisted-target-required-before-publication"))
        for count in (0,1,31,32,33,65535):
            cases.append(make_case(rom,f"target-count-{bank:02X}-{count}",bank=bank,target_count=count,
                category="allowlist-count-boundary"))
        for low,carry in ((end-1,0),(end+1,0),(end,1),(0,1),(0,2),(0,65535)):
            cases.append(make_case(rom,f"end-{bank:02X}-{low}-{carry}",bank=bank,end_word=low,end_carry=carry,
                category="exact-descriptor-extent"))
        for bad_root in (0xFFFB,0xFFFC,0xFFFD,0xFFFE,0xFFFF):
            cases.append(make_case(rom,f"root-{bank:02X}-{bad_root:04X}",bank=bank,root=bad_root,
                category="source-bank-boundary"))
        for key in ("valid","reserved0","reserved1"):
            for value in (2,0x100,0xFFFF):
                cases.append(make_case(rom,f"field-{bank:02X}-{key}-{value}",bank=bank,
                    category="registry-reserved-fields",**{key:value}))
        for upper in (1,0x7E,0xFF):
            cases.append(make_case(rom,f"wide-bank-{bank:02X}-{upper:02X}",bank=bank,
                bank_word=(upper<<8)|bank,category="bank-high-byte-refusal"))
    for value in (0x100,0x180,0xFF80,0xFFFF):
        cases.append(make_case(rom,f"wide-selector-{value:04X}",value,category="wide-selector"))
        cases.append(make_case(rom,f"wide-flag-{value:04X}",flag=value,category="wide-branch-refusal"))
    for flags in range(256):
        if flags&0x30: continue
        for route,selector,valid,flag in (("canonical",0x7F,1,0),("success0",0x80,1,0),
                                         ("success1",0x80,1,0x40),("refusal",0x80,0,0)):
            c=make_case(rom,f"status-{flags:02X}-{route}",selector,flag,valid=valid,category="all-native-status-bits")
            c["cpu"]["ps"]=flags
            c["expected_cpu"]["ps"]=(flags&0x7C) if route=="canonical" else (((flags&0x4C)|0x23) if route.startswith("success") else flags)
            cases.append(c)
    return cases


def validate_fixture_spans(cases: list[dict[str, Any]], code_size: int, code_base: int = CODE) -> None:
    prior.validate_fixture_spans([],code_size,code_base)
    protected=[SCRATCH,STACK,(code_base,code_base+code_size),(0x7E1FF0,0x7E2000)]
    allowed=[(0x7E3000,0x7E3500),(0x7E9877,0x7E9879),(0x7EA0B3,0x7EA0B5)]
    for c in cases:
        for address,value in c["patches"]:
            if not any(a<=address<b for a,b in allowed) or not 0<=value<=255:
                raise ConformanceError("setup write outside exact WRAM input fixtures")
            if any(a<=address<b for a,b in protected):
                raise ConformanceError("setup write overlaps protected fixture")
        for address,value in c["expected_rom_reads"]:
            if address>>16 not in FIXTURES or not 0<=value<=255:
                raise ConformanceError("expected read is outside exact ROM fixture banks")


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
        "!PE_PH1_SCRATCH = $7E4000\n!PE_PH1_BINDINGS = $7E3000\n"
        "!PE_PH1_TARGETS = $7E3100\n!PE_PH1_CANONICAL_TAIL = $7FF000\n!PE_PH1_SUCCESS_TAIL = $7FF010\n"
        "!PE_PH1_REFUSAL_TAIL = $7FF020\n" + body)
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


def validate_execution_addresses(record: dict[str, Any], *, code_size: int, code_base: int = CODE) -> None:
    if type(code_size) is not int or not 1<=code_size<=0x6000:
        raise ConformanceError("invalid assembled execution extent")
    pcs=record.get("exec_addresses")
    if not isinstance(pcs,list) or not 2<=len(pcs)<=10000 or record.get("instructions")!=len(pcs):
        raise ConformanceError("complete execution sequence missing or instruction-count mismatch")
    if pcs[0]!=code_base or pcs[-1]!=TAILS.get(record.get("route")):
        raise ConformanceError("execution entry or exact terminal tail mismatch")
    if any(type(pc) is not int or not code_base<=pc<code_base+code_size for pc in pcs[:-1]):
        raise ConformanceError("execution address outside exact assembled helper span")


def validate_record(record: dict[str, Any], case: dict[str, Any], *,
                    code_size: int = 676, code_base: int = CODE) -> None:
    validate_execution_addresses(record,code_size=code_size,code_base=code_base)
    try:
        prior.validate_record(record,case)
    except prior.ConformanceError as exc:
        raise ConformanceError(str(exc)) from exc
    expected=bytearray(0x500)
    expected[0x100:]=bytes([0xA5])*0x400
    for address,value in case["patches"]:
        if 0x7E3000<=address<0x7E3500: expected[address-0x7E3000]=value
    if record.get("input_fixture_before_hex") != expected.hex() or record.get("input_fixture_after_hex") != expected.hex():
        raise ConformanceError(f"{case['name']}: complete WRAM input fixture mismatch")
    count=record.get("reads_total")
    if type(count) is not int or not len(case["expected_rom_reads"]) <= count <= 10000:
        raise ConformanceError(f"{case['name']}: CPU data-read bound missing or invalid")
    if record.get("rom_reads") != case["expected_rom_reads"]:
        raise ConformanceError(f"{case['name']}: exact ordered CPU ROM-read mismatch")


def run(output_dir: Path, *, limit: int | None = None,
        repetition: int = 1, timeout: int = 240, code_base: int = CODE) -> dict[str, Any]:
    private = safe.canonical_private_root()
    rom = safe.resolve_private_file(DEFAULT_ROM, "original synthetic benchmark", private_root=private)
    if rom.stat().st_size != 0x800000 or safe.sha256_file(rom) != ROM_SHA256:
        raise ConformanceError("original synthetic boot image identity mismatch")
    if not 1 <= timeout <= 300 or repetition not in (1,2):
        raise ConformanceError("invalid bounded launch parameters")
    validate_fixture_spans([],1,code_base)
    runtime = {label:safe.resolve_private_file(safe.DEFAULT_MESEN.parent / name, label, private_root=private)
               for label,name in safe.RUNTIME_NAMES.items()}
    identities = {label:safe.require_identity(path,label) for label,path in runtime.items()}
    output = safe.prepare_private_output_dir(output_dir, private_root=private,
        forbidden_roots=(rom.parent, safe.DEFAULT_MESEN.parent))
    guarded = {**runtime,"rom":rom,"collector":COLLECTOR,"launcher":Path(__file__),"asar":ASAR,
               "host_adapter":Path(adapter.__file__),"isolation_library":Path(safe.__file__),"v0_validation_library":Path(prior.__file__)}
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
               PE_PACKAGE_TRACE=str(output/"trace.json"))
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
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=32*1024*1024),"trace")
    if trace.get("schema") != SCHEMA or trace.get("error") is not None or len(trace.get("records",[])) != len(cases):
        raise ConformanceError("trace schema, termination, or case count mismatch")
    for record,case in zip(trace["records"],cases,strict=True):
        validate_record(record,case,code_size=len(code),code_base=code_base)
    fixture_hashes=[{"name":r["name"],
        "before_sha256":digest(bytes.fromhex(r["input_fixture_before_hex"])),
        "after_sha256":digest(bytes.fromhex(r["input_fixture_after_hex"]))} for r in trace["records"]]
    (output/"wram_input_fixture_hashes.json").write_bytes(canonical_json(fixture_hashes))
    reproduction=["python","tools/run_schala_package_helper_v1_rom_source.py","--output-dir",
                  "private/test_runs/package_helper_v1_rom_source_NEW","--repetition",str(repetition),
                  "--timeout",str(timeout),"--code-base",f"0x{code_base:06X}"]
    if limit is not None:
        reproduction.extend(["--limit",str(limit)])
    manifest={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"immutable-original-rom-source-transport-only",
        "repetition":repetition,"case_count":len(cases),"subset_only":limit is not None,
        "case_categories":{k:sum(c["category"]==k for c in cases) for k in sorted({c["category"] for c in cases})},
        "passed":True,"source_hashes":source_before,"staged_hashes":staged_before,
        "helper_size":len(code),"helper_code_base":code_base,"entry_bridge":ENTRY_BRIDGE,"helper_sha256":digest(code),"trace_sha256":safe.sha256_file(trace_path),
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "wram_input_fixture_hashes_sha256":safe.sha256_file(output/"wram_input_fixture_hashes.json"),
        "cpu_instruction_counts":{"min":min(r["instructions"] for r in trace["records"]),
                                  "max":max(r["instructions"] for r in trace["records"])},
        "sources_and_staged_inputs_unchanged":True,"no_rom_write_or_patch":True,
        "rom_source_banks":[0x41,0x42],"pointed_stream_execution":False,"complete_execution_span_guard":True,"complete_execution_pc_sequences":True,"no_game_input":True,"production_hook_allocation_or_integration":False,
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
