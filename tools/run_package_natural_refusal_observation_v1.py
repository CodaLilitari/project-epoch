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
import package_natural_refusal_validation_v1 as validation

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="project-epoch-package-natural-refusal-observation-v1"
COLLECTOR=ROOT/"tools/mesen_package_natural_refusal_observation_v1.lua"
PINNED={
    "rom":("private/input/rom_archive/Chrono Trigger (USA).sfc",4194304,"06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"),
    "sram":("private/input/lavos_save/chrono_trigger.srm",8192,"cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203"),
    "state":("private/test_runs/mesen2/lavos_battle_checkpoint_accepted_v17/battle_ready.mss",261614,"d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b"),
}

ObservationError=validation.ObservationError
summarize=validation.summarize


def canonical(value:Any)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()


ARCHIVE_KEYS=('collector','launcher','isolation_library','validation_library','tests')


def archive_sources(archive, guarded, before):
    archive.mkdir()
    archived={}
    for key in ARCHIVE_KEYS:
        destination=archive/guarded[key].name
        safe.copy_new_regular_file(guarded[key],destination,key)
        archived[key]=destination
    hashes={k:safe.sha256_file(p) for k,p in archived.items()}
    if hashes!={k:before[k] for k in ARCHIVE_KEYS}:
        raise ObservationError('archived source copy differs from guarded original')
    return archived,hashes


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
    guarded={**inputs,**runtime,"collector":COLLECTOR,"launcher":Path(__file__),"isolation_library":Path(safe.__file__),"validation_library":Path(validation.__file__),"tests":ROOT/"tests/test_package_natural_refusal_observation_v1.py"}
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
    archived,archive_before=archive_sources(output/'source_archive',guarded,before)
    (output/"launch_inputs.json").write_bytes(canonical({"schema":SCHEMA,"status":"prepared; native run not yet accepted",
        "source_hashes":before,"staged_hashes":staged_before,"archived_source_hashes":archive_before,"fixed_inputs":PINNED}))
    env=safe.minimal_subprocess_environment()
    for key,parts in {"USERPROFILE":("profile",),"APPDATA":("profile","AppData","Roaming"),"LOCALAPPDATA":("profile","AppData","Local"),"TEMP":("temp",),"TMP":("temp",)}.items():
        p=stage.joinpath(*parts); p.mkdir(parents=True,exist_ok=True); env[key]=str(p)
    env.update(PE_RESOLVER_PROTOCOL=SCHEMA,PE_RESOLVER_STATE=str(staged["state"]),PE_RESOLVER_TRACE=str(output/"trace.json"),PE_REFUSAL_OUTPUT=str(output))
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
    safe.require_file_hashes_unchanged(archived,archive_before,"archived source")
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged["sram"].name)
    if error or proc is None or proc.returncode!=51:
        raise ObservationError(f"isolated observation failed: {error or proc.returncode}; retained {output}")
    trace_path=output/"trace.json"
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=16*1024*1024),"trace")
    result={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"single source-matched controller-only natural dead-target Cure refusal; independent pair required",
        "source_hashes":before,"staged_hashes":staged_before,"archived_source_hashes":archive_before,"trace_sha256":safe.sha256_file(trace_path),
        "input_schedule_basis":"inputPolled callbacks; trace frame field is a relative input-poll count; timing fields are independent emulated clocks",
        "observations":summarize(trace),
        "screenshots":{p.name:{"size":p.stat().st_size,"sha256":safe.sha256_file(p)} for p in sorted(output.glob("menu_*.png"))},"sources_and_staged_inputs_unchanged":True,
        "rom_mutated":False,"memory_or_cpu_injection":False,"helper_installed":False,"production_approval":False,
        "reproduce":["python","-B","tools/run_package_natural_refusal_observation_v1.py","--output-dir","private/test_runs/package_natural_refusal_NEW"]}
    (output/"manifest.json").write_bytes(canonical(result))
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(); result=run(args.output_dir)
    print(json.dumps({"status":result["observations"]["status"],"record_count":result["observations"]["record_count"],"trace_sha256":result["trace_sha256"]},indent=2))
