#!/usr/bin/env python3
"""Acquire a private clean-ROM checkpoint at actual normal-save entry.

Reuses pinned runtime/path checks from the accepted Lavos acquisition. No ROM
mutation. Each run retains its isolated runtime and a complete hash receipt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/'tools/run_mesen_lavos_battle_checkpoint.py'
BASE_SHA='377024c212a72c4e2f3b000e44a7573cedd94093f86463c665be8925ae8c6321'
COLLECTOR=ROOT/'tools/mesen_save_entry_checkpoint_v1.lua'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--verify-from',type=Path,help='Accepted acquisition directory; resume it in a fresh process at the same entry')
    args=p.parse_args()
    raw=BASE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA: raise ValueError('base launcher drift')
    mod=types.ModuleType('_save_entry_lavos_base');mod.__file__=str(BASE_PATH)
    sys.modules[mod.__name__]=mod;exec(compile(raw,str(BASE_PATH),'exec'),mod.__dict__)
    base=mod.BASE
    mesen=base.resolve_private_file(mod.DEFAULT_MESEN,'Mesen')
    shared=(mesen.parent/'Saves').resolve(strict=True)
    shared_before=base.snapshot_private_files(shared)
    names={'mesen':'Mesen.exe','mesen_core':'MesenCore.dll','harfbuzz':'libHarfBuzzSharp.dll','skia':'libSkiaSharp.dll','nesdb':'MesenNesDB.txt','settings':'settings.json'}
    inputs={k:base.resolve_private_file(mesen.parent/v,k) for k,v in names.items()}
    inputs.update(rom=base.resolve_private_file(mod.DEFAULT_ROM,'ROM'),sram=base.resolve_private_file(mod.DEFAULT_SRAM,'SRAM'),archive=base.resolve_private_file(mesen.parent.parent/'Mesen_2.1.1_Windows.zip','archive'))
    before={k:base.require_hash(v,mod.RUNTIME_HASHES[k],k) for k,v in inputs.items()}
    for k,v in inputs.items():
        if v.stat().st_size!=mod.PINNED_SIZES[k]: raise ValueError('input size: '+k)
    sources={'runner':Path(__file__).resolve(),'collector':COLLECTOR,'base':BASE_PATH}
    source_hashes={k:sha(v) for k,v in sources.items()}
    verify_paths={}
    if args.verify_from:
        prior=base.resolve_private_file(args.verify_from/'receipt.json','acquisition receipt')
        prior_doc=json.loads(prior.read_text(encoding='utf-8'))
        if prior_doc.get('schema')!='project-epoch-save-entry-checkpoint-v1' or prior_doc.get('accepted') is not True: raise ValueError('unaccepted acquisition')
        verify_paths={'state':base.resolve_private_file(prior.parent/'save_entry.mss','checkpoint'),'wram':base.resolve_private_file(prior.parent/'entry_wram.bin','entry WRAM'),'cpu':base.resolve_private_file(prior.parent/'entry_cpu.txt','entry CPU'),'receipt':prior}
        for k,name in (('state','save_entry.mss'),('wram','entry_wram.bin'),('cpu','entry_cpu.txt')):
            if sha(verify_paths[k])!=prior_doc['artifacts'][name]['sha256']: raise ValueError('acquisition artifact drift')
    verify_hashes={k:sha(v) for k,v in verify_paths.items()}
    out=base.prepare_private_output_dir(args.output_dir,forbidden_roots=(shared,))
    app=out/'isolated_runtime';(app/'Saves').mkdir(parents=True)
    for k,v in names.items(): shutil.copyfile(inputs[k],app/v)
    rom=out/'save_entry_clean.sfc';sram=app/'Saves/save_entry_clean.srm';lua=out/COLLECTOR.name
    shutil.copyfile(inputs['rom'],rom);shutil.copyfile(inputs['sram'],sram);shutil.copyfile(COLLECTOR,lua)
    staged={**{k:app/v for k,v in names.items()},'rom':rom,'sram':sram,'collector':lua}
    staged_before={k:sha(v) for k,v in staged.items()}
    if any(staged_before[k]!=before[k] for k in before if k!='archive') or staged_before['collector']!=source_hashes['collector']:
        raise ValueError('staging mismatch')
    env=os.environ.copy()
    for key in ('PE_SAVE_ENTRY_STATE','PE_SAVE_ENTRY_EXPECT_WRAM','PE_SAVE_ENTRY_EXPECT_CPU'): env.pop(key,None)
    env.update(PE_SRAM_PATH=str(sram),PE_SAVE_ENTRY_OUTPUT=str(out))
    if verify_paths:
        for k in ('state','wram','cpu'): shutil.copyfile(verify_paths[k],out/('verify_input.'+k))
        env.update(PE_SAVE_ENTRY_STATE=str(out/'verify_input.state'),PE_SAVE_ENTRY_EXPECT_WRAM=str(out/'verify_input.wram'),PE_SAVE_ENTRY_EXPECT_CPU=str(out/'verify_input.cpu'))
    cmd=[str(app/'Mesen.exe'),'--testRunner','--timeout=120','--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true','--snes.ramPowerOnState=AllZeros','--snes.port1.type=SnesController',str(lua),str(rom)]
    failure=None;completed=None
    try:
        completed=subprocess.run(cmd,cwd=app,env=env,capture_output=True,text=True,timeout=145,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except Exception as exc: failure=repr(exc)
    after={k:sha(v) for k,v in inputs.items()}
    staged_after={k:sha(v) for k,v in staged.items()}
    source_after={k:sha(v) for k,v in sources.items()}
    # stop() is deferred by Mesen; the isolated game may finish the save after
    # the entry snapshot was captured. Only that disposable SRAM may change.
    staged_changes=[k for k in staged_before if staged_before[k]!=staged_after[k]]
    unchanged=before==after and set(staged_changes)<= {'sram'} and source_hashes==source_after and shared_before==base.snapshot_private_files(shared)
    unchanged=unchanged and verify_hashes=={k:sha(v) for k,v in verify_paths.items()}
    artifacts={}
    for name in ('checkpoint.tsv','endpoint.png','save_entry.mss','entry_wram.bin','entry_sram.bin','entry_cpu.txt'):
        f=out/name
        if f.is_file(): artifacts[name]={'bytes':f.stat().st_size,'sha256':sha(f)}
    accepted=bool(completed and completed.returncode==49 and unchanged and set(artifacts)=={'checkpoint.tsv','endpoint.png','save_entry.mss','entry_wram.bin','entry_sram.bin','entry_cpu.txt'})
    if accepted:
        trace=(out/'checkpoint.tsv').read_text()
        accepted=sum(line.startswith('save-entry\t') for line in trace.splitlines())==1 and trace.splitlines()[-1].startswith('success\t') and (out/'entry_sram.bin').read_bytes()==inputs['sram'].read_bytes()
        if verify_paths:
            accepted=accepted and (out/'entry_wram.bin').read_bytes()==verify_paths['wram'].read_bytes()
            accepted=accepted and (out/'entry_cpu.txt').read_bytes()==verify_paths['cpu'].read_bytes()
    receipt={'schema':'project-epoch-save-entry-checkpoint-v1','evidence_level':'observed-runtime-checkpoint' if accepted else 'rejected-pilot','accepted':accepted,'rom_mutated':False,'execution_boundary':'capture before FFF9FB SaveSlot_Write, reached through controller input; execution can continue after deferred stop','input_paths':{k:str(v) for k,v in inputs.items()},'input_hashes':before,'input_hashes_after':after,'source_hashes':source_hashes,'source_hashes_after':source_after,'staged_hashes_before':staged_before,'staged_hashes_after':staged_after,'staged_changes':staged_changes,'immutable_inputs_and_shared_saves_preserved':unchanged,'artifacts':artifacts,'command':cmd,'reproduction':['python','tools/run_mesen_save_entry_checkpoint_v1.py','--output-dir','private/test_runs/mesen2/NEW_EMPTY_SAVE_ENTRY_RUN'],'returncode':completed.returncode if completed else None,'process_error':failure,'stdout':completed.stdout if completed else None,'stderr':completed.stderr if completed else None,'limitations':['single checkpoint acquisition; repeated equality and fresh-process checkpoint resume are separate checks','does not install PC07, relocation, or sidecar','isolated runtime and binary artifacts remain private','post-stop disposable SRAM can differ; entry_sram.bin is the exact captured input']}
    receipt['verification_input_paths']={k:str(v) for k,v in verify_paths.items()}
    receipt['verification_input_hashes']=verify_hashes
    receipt['fresh_process_resume']=bool(verify_paths)
    receipt['checkpoint_pc']='C2CF51'
    receipt['observed_entry_pc']='FFF9FB'
    receipt['execution_boundary']='MSS at caller C2CF51; CPU/WRAM/SRAM observed at FFF9FB before PHP; deferred stop permits later execution'
    receipt['presentation_available']=artifacts.get('endpoint.png',{}).get('bytes',0)>0
    receipt['limitations'].append('fresh resume may have no screenshot before its first rendered frame; presentation is not an acceptance witness')
    if verify_paths: receipt['reproduction']+=['--verify-from',str(args.verify_from)]
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':accepted,'output_dir':str(out),'receipt_sha256':sha(out/'receipt.json'),'returncode':receipt['returncode'],'artifacts':artifacts},indent=2))
    return 0 if accepted else 1
if __name__=='__main__': raise SystemExit(main())
