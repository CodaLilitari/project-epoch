#!/usr/bin/env python3
"""Execute original package helper in isolated Mesen WRAM; never mutate a ROM.

The only boot image accepted is the pinned, already-existing original synthetic
SHA benchmark. All fixtures, execution records, and raw binaries stay private.
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

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "tools/mesen_schala_package_helper_conformance_v0.lua"
HELPER = ROOT / "asm/schala_package_helper_v0.asm"
DEFAULT_ROM = ROOT / "private/test_runs/sha256_65c816/schala_sha256_profile1_benchmark.sfc"
ROM_SHA256 = "e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd"
ASAR_SHA256 = "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8"
ASAR = ROOT / "private/tools/asar-1.91/asar.exe"
CODE = 0x7F8000
TAILS = {"canonical": 0x7FF000, "success": 0x7FF010, "refusal": 0x7FF020}
SCRATCH = (0x7E4000, 0x7E4080)
STACK = (0x7E1FE6, 0x7E1FF0)  # eight saved bytes plus one two-byte JSR
SCHEMA = "project-epoch-original-package-helper-conformance-v0"


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


def make_case(name: str, selector: int = 0x80, flag: int = 0, *,
              bank: int = 0x7F, root: int = 0x2000, mask0: int = 0x8000,
              mask1: int = 0x8000, pointers: list[int] | None = None,
              valid: int = 1, bank_word: int | None = None,
              index: int = 0, category: str = "descriptor") -> dict[str, Any]:
    pointers = ([0x7000] * (mask0.bit_count() + mask1.bit_count())
                if pointers is None else pointers)
    descriptor = mask0.to_bytes(2, "big") + mask1.to_bytes(2, "big")
    descriptor += b"".join(p.to_bytes(2, "little") for p in pointers)
    patches = word_bytes(0x7E9877, selector) + word_bytes(0x7EA0B3, flag)
    if 0x80 <= selector <= 0x8F:
        entry = 0x7E3000 + (selector - 0x80) * 6
        patches += word_bytes(entry, valid) + word_bytes(entry + 2, root)
        patches += word_bytes(entry + 4, bank if bank_word is None else bank_word)
    # Malformed fixtures deliberately clip at their physical bank boundary.
    patches += [[bank * 65536 + root + i, b]
                for i, b in enumerate(descriptor) if root + i < 65536]
    for pointer in set(pointers):
        if pointer != 0xFFFF and not root <= pointer < root + len(descriptor):
            patches.append([bank * 65536 + pointer, 0])
    cpu = input_cpu(index)
    expected = dict(cpu)
    expected_writes: list[list[int]] = []
    if selector < 0x80:
        route = "canonical"
        expected.update(a=selector * 2, ps=(cpu["ps"] & 0x7C) | (2 if selector == 0 else 0))
    else:
        route = "refusal"
        if selector <= 0x8F and flag <= 255 and valid == 1 and (bank_word is None or bank_word == bank) and bank in (0x7E, 0x7F):
            image = bytearray(65536)
            for address, value in patches:
                if address >> 16 == bank:
                    image[address & 65535] = value
            try:
                source = adapter.make_package_source(selector=selector, bank=bank,
                    root_offset=root, allocation_name="SYNTHETIC_NATIVE_DESCRIPTOR", source_kind="synthetic-test")
                model = adapter.simulate_descriptor_install(bytes(image), source, a0b3=flag)
            except adapter.PackageBankAdapterError:
                pass
            else:
                route = "success"
                expected.update(a=0, x=model.x_final, y=16,
                    ps=(cpu["ps"] & 0x4C) | 0x23)
                expected_writes += word_bytes(0x7E9878, root)
                expected_writes += word_bytes(0x7E0080, 0)
                expected_writes += word_bytes(0x7E0082, mask1)
                for p in model.publications:
                    expected_writes += word_bytes(0x7E0000 + p.activation_address, p.activation_word)
                    expected_writes += word_bytes(0x7E0000 + p.script_address, p.script_offset)
                    expected_writes += word_bytes(0x7E0000 + p.bank_address, p.bank_word)
                expected_writes += [[0x7EA0B3, 0]]
    spans = [[bank*65536+root,bank*65536+min(65536,root+len(descriptor))]]
    spans += [[bank*65536+p,bank*65536+p+1] for p in sorted(set(pointers))
              if p != 0xFFFF and not root <= p < root+len(descriptor)]
    return {"name": name, "category": category, "selector": selector, "flag": flag, "cpu": cpu,
            "source_spans": spans,
            "patches": patches, "route": route, "expected_cpu": expected,
            "expected_writes": expected_writes}


def build_cases() -> list[dict[str, Any]]:
    cases = [make_case(f"canonical-{s:02X}", s, 0xA55A, index=s,category="canonical-selector") for s in range(128)]
    cases += [make_case(f"symbolic-flag-{f:02X}", flag=f, index=f,category="all-flag-bytes") for f in range(256)]
    for owner in range(16):
        for branch in (0, 1):
            cases.append(make_case(f"owner-{owner:02}-{branch}", flag=branch,
                mask0=1 << (15-owner), mask1=1 << (15-owner), index=owner,category="each-owner-both-masks"))
    for name, m0, m1 in (("sparse", 0xA509, 0x5282), ("all", 65535, 65535), ("empty", 0, 0)):
        for branch in (0, 1):
            cases.append(make_case(f"{name}-{branch}", flag=branch, mask0=m0, mask1=m1, index=branch,category="mask-shape"))
    for bank in (0x7E, 0x7F):
        for root in (0xFFF8, 0xFFF9, 0xFFFC, 0xFFFD):
            for branch in (0, 1):
                cases.append(make_case(f"bank-{bank:02X}-root-{root:04X}-{branch}", flag=branch,
                    bank=bank, root=root, index=branch,category="bank-boundary"))
    for selector in range(0x80, 0x100):
        cases.append(make_case(f"unbound-{selector:02X}", selector, valid=0, index=selector,category="unbound-or-outside-selector"))
    for name, kwargs in (
        ("bad-valid", {"valid":2}), ("bad-bank-high", {"bank_word":0x017F}),
        ("bad-bank-low", {"bank_word":0x0042}), ("bad-flag-high", {"flag":0x0100}),
        ("ffff-selected", {"pointers":[0xFFFF,0x7000]}),
        ("ffff-unselected", {"pointers":[0x7000,0xFFFF]}),
        ("overlap-selected", {"pointers":[0x2000,0x7000]}),
        ("overlap-unselected", {"pointers":[0x7000,0x2007]}),
        ("wram-bank7e", {"bank":0x7E,"root":0x5000,"pointers":[0x6000,0x6000]}),
    ):
        cases.append(make_case(name, category="malformed-or-second-bank",**kwargs))
    for selector in range(0x80,0x90):
        for branch in (0,1):
            cases.append(make_case(f"bound-selector-{selector:02X}-{branch}",selector,branch,
                category="each-bound-high-selector",index=selector))
    for selector in (0x0100,0x0180,0xFF80,0xFFFF):
        cases.append(make_case(f"wide-selector-{selector:04X}",selector,category="wide-selector-refusal"))
    for branch in (0,1):
        cases.append(make_case(f"distinct-pointers-{branch}",flag=branch,mask0=0xA501,
            mask1=0x4100,pointers=[0x6800+i*17 for i in range(7)],category="distinct-pointer-transport"))
        for root,m0,m1 in ((0xFFFC,0,0),(0xFFFA,0x8000,0),(0xFFFA,0,0x8000),
                           (0xFFF9,0x8000,0),(0xFFBC,65535,65535)):
            cases.append(make_case(f"exact-boundary-{root:04X}-{m0:04X}-{branch}",flag=branch,
                root=root,mask0=m0,mask1=m1,category="exact-bank-boundary"))
    for flags in range(256):
        if flags & 0x30:
            continue
        for route,selector,valid,branch in (("canonical",0x7F,1,0),("success0",0x80,1,0),
                                           ("success1",0x80,1,1),("refusal",0x80,0,0)):
            c=make_case(f"status-{flags:02X}-{route}",selector,branch,valid=valid,
                category="all-native-status-bits")
            c["cpu"]["ps"]=flags
            c["expected_cpu"]["ps"]=(flags & 0x7C) if route=="canonical" else (
                ((flags & 0x4C)|0x23) if route.startswith("success") else flags)
            cases.append(c)
    return cases


def validate_fixture_spans(cases: list[dict[str, Any]], code_size: int, code_base: int = CODE) -> None:
    if code_base not in (0x7F8000,0x7F9000) or code_base+code_size > 0x7FE000:
        raise ConformanceError("code origin or extent outside bounded synthetic windows")
    protected = [SCRATCH,STACK,(0x7E3000,0x7E3060),(code_base,code_base+code_size),
        (0x7E0080,0x7E0084),(0x7E9877,0x7E987A),(0x7EA0B3,0x7EA0B5),
        (0x7E5DAC,0x7E5DFD),(0x7E1FF0,0x7E2000)]
    protected += [(tail,tail+1) for tail in TAILS.values()]
    for c in cases:
        spans=c["source_spans"]
        for start,end in spans:
            if not 0x7E0000 <= start < end <= 0x800000 or (start>>16)!=((end-1)>>16):
                raise ConformanceError(f"{c['name']}: source span outside one WRAM bank")
            if any(start < b and a < end for a,b in protected):
                raise ConformanceError(f"{c['name']}: source fixture overlaps protected span")
        for index,(start,end) in enumerate(spans):
            if any(start < b and a < end for a,b in spans[index+1:]):
                raise ConformanceError(f"{c['name']}: distinct source spans overlap")


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


def assemble(output: Path, *, smoke: bool = False, code_base: int = CODE) -> bytes:
    asar = safe.resolve_private_file(ASAR, "Asar")
    if asar.stat().st_size != 501248 or safe.sha256_file(asar) != ASAR_SHA256:
        raise ConformanceError("Asar1.91 identity mismatch")
    body = "lda.w #$1234\nsta.l $7E4100\njml $7FF010\n" if smoke else HELPER.read_text()
    wrapper = (f"norom\norg $000000\nbase ${code_base:06X}\n"
        "!PE_PH_SCRATCH = $7E4000\n!PE_PH_BINDINGS = $7E3000\n"
        "!PE_PH_CANONICAL_TAIL = $7FF000\n!PE_PH_SUCCESS_TAIL = $7FF010\n"
        "!PE_PH_REFUSAL_TAIL = $7FF020\n" + body)
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


def validate_record(record: dict[str, Any], case: dict[str, Any]) -> None:
    if record["name"] != case["name"] or record["route"] != case["route"]:
        raise ConformanceError(f"{case['name']}: unexpected terminal route")
    if record["cpu"] != case["expected_cpu"]:
        raise ConformanceError(f"{case['name']}: CPU mismatch: {record['cpu']} expected {case['expected_cpu']}")
    output_values = dict(case["expected_writes"])
    # Replay the ordered publication words to retain overlapping byte writes.
    baseline = {a:v for a,v in case["patches"]}
    expected_changes = {a:v for a,v in output_values.items() if v != baseline.get(a, 0xA5)}
    actual_changes = {}
    output_write_set = set(output_values)
    def temporary(address: int) -> bool:
        return ((case["route"] != "canonical" and SCRATCH[0] <= address < SCRATCH[1])
                or STACK[0] <= address < STACK[1])
    for address, value in record["writes"]:
        if temporary(address):
            continue
        if address not in output_write_set:
            raise ConformanceError(f"{case['name']}: undeclared CPU write {address:06X}")
    actual_outputs = {a for a,v in record["writes"] if a in output_write_set}
    if actual_outputs != output_write_set:
        raise ConformanceError(f"{case['name']}: incomplete output write footprint")
    publication_actual = [[a,v] for a,v in record["writes"] if 0x7E5DAC <= a < 0x7E5DFD]
    publication_expected = [[a,v] for a,v in case["expected_writes"] if 0x7E5DAC <= a < 0x7E5DFD]
    if publication_actual != publication_expected:
        raise ConformanceError(f"{case['name']}: ordered publication byte-write mismatch")
    for address, value in record["changes"]:
        if temporary(address):
            continue
        actual_changes[address] = value
    if actual_changes != expected_changes:
        raise ConformanceError(f"{case['name']}: full WRAM diff mismatch {actual_changes} expected {expected_changes}")


def run(output_dir: Path, *, smoke: bool = False, limit: int | None = None,
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
               "host_adapter":Path(adapter.__file__),"isolation_library":Path(safe.__file__)}
    if not smoke:
        guarded["helper"] = HELPER
    source_before = {k:safe.sha256_file(v) for k,v in guarded.items()}
    code = assemble(output, smoke=smoke,code_base=code_base)
    cases = build_cases()
    if smoke:
        c = make_case("mechanism-smoke")
        c["expected_cpu"] = dict(c["cpu"])
        c["expected_cpu"].update(a=0x1234, ps=c["cpu"]["ps"] & 0x7D)
        c["expected_writes"] = word_bytes(0x7E4100, 0x1234)
        cases = [c]
    elif limit is not None:
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
             "cases":[{k:v for k,v in c.items() if not k.startswith("expected_")} for c in cases]}
    staged["inputs"]=stage/"inputs.lua"
    staged["inputs"].write_text("return " + lua_value(payload) + "\n", encoding="utf-8")
    (output/"case_contract.json").write_bytes(canonical_json(cases))
    staged_before={k:safe.sha256_file(v) for k,v in staged.items()}
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
        validate_record(record,case)
    reproduction=["python","tools/run_schala_package_helper_conformance_v0.py","--output-dir",
                  "private/test_runs/package_helper_NEW","--repetition",str(repetition),
                  "--timeout",str(timeout),"--code-base",f"0x{code_base:06X}"]
    if smoke:
        reproduction.append("--smoke")
    if limit is not None:
        reproduction.extend(["--limit",str(limit)])
    manifest={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"synthetic-only",
        "repetition":repetition,"case_count":len(cases),"smoke_only":smoke,"subset_only":limit is not None,
        "case_categories":{k:sum(c["category"]==k for c in cases) for k in sorted({c["category"] for c in cases})},
        "passed":True,"source_hashes":source_before,"staged_hashes":staged_before,
        "helper_size":len(code),"helper_code_base":code_base,"helper_sha256":digest(code),"trace_sha256":safe.sha256_file(trace_path),
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "cpu_instruction_counts":{"min":min(r["instructions"] for r in trace["records"]),
                                  "max":max(r["instructions"] for r in trace["records"])},
        "sources_and_staged_inputs_unchanged":True,"no_rom_write_or_patch":True,
        "no_game_input":True,"production_hook_allocation_or_integration":False,
        "interrupt_policy":"synthetic IRQ/NMI sources disabled; no game interrupt claim",
        "reproduce":reproduction}
    (output/"manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--repetition",type=int,default=1)
    parser.add_argument("--smoke",action="store_true")
    parser.add_argument("--limit",type=int)
    parser.add_argument("--timeout",type=int,default=240)
    parser.add_argument("--code-base",type=lambda value:int(value,0),default=CODE)
    args=parser.parse_args()
    print(json.dumps(run(args.output_dir,smoke=args.smoke,limit=args.limit,repetition=args.repetition,timeout=args.timeout,code_base=args.code_base),indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
