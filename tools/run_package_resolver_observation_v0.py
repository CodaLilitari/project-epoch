#!/usr/bin/env python3
"""Observe a fixed ordinary player-Tech action on an isolated clean-ROM state.

No arbitrary state, collector, input, code injection, or memory-write option.
Raw game observations stay private; stdout is a metadata-only summary.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
from typing import Any

import run_mesen_field_animation_probe_v0 as safe

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="project-epoch-package-resolver-observation-v0"
COLLECTOR=ROOT/"tools/mesen_package_resolver_observation_v0.lua"
PINNED={
    "rom":("private/input/rom_archive/Chrono Trigger (USA).sfc",4194304,"06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"),
    "sram":("private/input/lavos_save/chrono_trigger.srm",8192,"cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203"),
    "state":("private/test_runs/mesen2/lavos_battle_checkpoint_accepted_v17/battle_ready.mss",261614,"d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b"),
}

class ObservationError(RuntimeError):
    pass

def canonical(value:Any)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()

def summarize(trace:dict[str,Any])->dict[str,Any]:
    if trace.get("schema")!=SCHEMA or trace.get("error") is not None:
        raise ObservationError("collector schema or execution failure")
    records=trace.get("records")
    if not isinstance(records,list) or not 2<=len(records)<=4096:
        raise ObservationError("invalid observation record count")
    if records[0].get("kind")!="baseline" or records[-1].get("kind")!="terminal":
        raise ObservationError("missing baseline/terminal")
    entries=[r for r in records if r["kind"]=="resolver-entry"]
    checks=[]
    for entry in entries:
        c=entry["cpu"]; stack=entry["stack"]
        checks.append(c["d"]==0 and c["dbr"]==0x7E and not c["emulationMode"]
            and c["ps"]&0x30==0 and entry["selector_word"]<0x80
            and entry["branch_word"] in (0,0x40) and entry["wram"]["AE91"]<3 and entry["wram"]["AE92"]==2
            and stack[:4]==[0x2A,0x43,0xAF,0x40])
    chains=[]; completions=[]
    for index,entry in enumerate(records):
        if entry['kind']!='resolver-entry':
            continue
        remaining=records[index+1:]
        following=[]
        for r in remaining:
            if r['kind'] in ('resolver-entry','branch-producer-complete'):
                break
            following.append(r)
        cursor=0; valid=True
        for kind,delta in [('resolver-tail',0),('common-loader-entry',0),('common-loader-rts',0),('dispatcher-rts',2),('caller-resume',4)]:
            while cursor<len(following) and following[cursor]['kind']!=kind:
                cursor+=1
            if cursor==len(following):
                valid=False; break
            r=following[cursor]; cursor+=1
            valid=valid and r['cpu']['sp']==((entry['cpu']['sp']+delta)&0xFFFF) and r['cpu']['ps']&0x30==0x20
        chains.append(valid)
        package_complete=False; effect_complete=False
        for r in following:
            if r['kind']=='caller-package-latch' and r['wram']['9876']!=0:
                package_complete=True
            if package_complete and r['kind']=='caller-effect-latch' and r['wram']['5D9B']==0:
                effect_complete=True
        completions.append(package_complete and effect_complete)
    return {"record_count":len(records),"event_counts":dict(sorted(Counter(r["kind"] for r in records).items())),
        "resolver_observed":bool(entries),"resolver_invocations":len(entries),
        "entry_abi_matches_static_contract":bool(entries) and all(checks),
        "observed_branch_words":sorted({r["branch_word"] for r in entries}),
        "entry_stack_pointers":sorted({r["cpu"]["sp"] for r in entries}),
        "paired_return_chain_matches_static_contract":bool(chains) and all(chains),
        "paired_pc_action_completion_observed":bool(completions) and all(completions),
        "all_entry_return_frames_match":bool(entries) and all(r["stack"][:4]==[0x2A,0x43,0xAF,0x40] for r in entries)}

def run(output_dir:Path)->dict[str,Any]:
    private=safe.canonical_private_root()
    inputs={}
    for key,(rel,size,sha) in PINNED.items():
        p=safe.resolve_private_file(ROOT/rel,key,private_root=private)
        if p.stat().st_size!=size or safe.sha256_file(p)!=sha:
            raise ObservationError(f"pinned {key} identity mismatch")
        inputs[key]=p
    runtime={key:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/name,key,private_root=private) for key,name in safe.RUNTIME_NAMES.items()}
    for key,p in runtime.items():
        safe.require_identity(p,key)
    output=safe.prepare_private_output_dir(output_dir,private_root=private,
        forbidden_roots=tuple(p.parent for p in inputs.values())+(safe.DEFAULT_MESEN.parent,))
    guarded={**inputs,**runtime,"collector":COLLECTOR,"launcher":Path(__file__),"isolation_library":Path(safe.__file__)}
    before={k:safe.sha256_file(p) for k,p in guarded.items()}
    stage=output/"staged"; app=stage/"app"; saves=app/"Saves"; saves.mkdir(parents=True)
    staged={}
    for key,name in safe.RUNTIME_NAMES.items():
        staged[key]=app/name; safe.copy_new_regular_file(runtime[key],staged[key],key)
    stem="pe_resolver_"+secrets.token_hex(12)
    for key,p in inputs.items():
        dest=(saves/(stem+".srm")) if key=="sram" else (stage/(stem+(".sfc" if key=="rom" else ".mss")))
        safe.copy_new_regular_file(p,dest,key); staged[key]=dest
    staged["collector"]=stage/"collector.lua"; safe.copy_new_regular_file(COLLECTOR,staged["collector"],"collector")
    staged_before={k:safe.sha256_file(p) for k,p in staged.items()}
    if any(staged_before[k]!=before[k] for k in staged):
        raise ObservationError("staged copy differs from pinned source")
    env=safe.minimal_subprocess_environment()
    for key,parts in {"USERPROFILE":("profile",),"APPDATA":("profile","AppData","Roaming"),"LOCALAPPDATA":("profile","AppData","Local"),"TEMP":("temp",),"TMP":("temp",)}.items():
        p=stage.joinpath(*parts); p.mkdir(parents=True,exist_ok=True); env[key]=str(p)
    env.update(PE_RESOLVER_PROTOCOL=SCHEMA,PE_RESOLVER_STATE=str(staged["state"]),PE_RESOLVER_TRACE=str(output/"trace.json"))
    command=[str(staged["mesen"]),"--testRunner","--timeout=60","--doNotSaveSettings","--debug.scriptWindow.allowIoOsAccess=true",
        "--snes.ramPowerOnState=AllZeros","--snes.port1.type=SnesController",str(staged["collector"]),str(staged["rom"])]
    error=None; proc=None
    try:
        proc=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=75,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0,check=False)
        (output/"process.log").write_bytes(proc.stdout+proc.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:
        error=str(exc)
    safe.require_file_hashes_unchanged(guarded,before,"source")
    safe.require_file_hashes_unchanged(staged,staged_before,"staged input")
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged["sram"].name)
    if error or proc is None or proc.returncode!=51:
        raise ObservationError(f"isolated observation failed: {error or proc.returncode}; retained {output}")
    trace_path=output/"trace.json"
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=4*1024*1024),"trace")
    result={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"checkpoint-bounded observation; no helper installed",
        "source_hashes":before,"staged_hashes":staged_before,"trace_sha256":safe.sha256_file(trace_path),
        "input_schedule_basis":"inputPolled callbacks; trace frame field is a relative poll count, not cycle timing",
        "observations":summarize(trace),"sources_and_staged_inputs_unchanged":True,
        "rom_mutated":False,"memory_or_cpu_injection":False,"helper_installed":False,"production_approval":False,
        "reproduce":["python","-B","tools/run_package_resolver_observation_v0.py","--output-dir","private/test_runs/resolver_observation_NEW"]}
    (output/"manifest.json").write_bytes(canonical(result))
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(run(args.output_dir),indent=2))
