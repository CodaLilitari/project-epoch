"""Collect a bounded clean-control or privately relocated menu path.

Default: read-only plan. A successful process is a collected probe, not a
playability or global memory ownership certificate. Compare the paired traces,
selected memory and screenshots independently before promoting the result.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import schala_compat_menu_v1 as c
import build_schala_compat_menu_v1 as builder
import run_mesen_save_layout_native_v1 as runtime

ROOT=Path(__file__).resolve().parents[1]
COLLECTOR=ROOT/'tools/mesen_compat_menu_v1.lua'
STATE=ROOT/'private/test_runs/mesen2/load_entry_checkpoint_v1_native_save_run2/load_entry.mss'
STATE_SHA='cdbfc74c21a6a345f5c9b7d74fce9159b95a3ff735ecd92afde70332bce0a5e1'
SRAM=ROOT/'private/test_runs/mesen2/save_layout_native_v1_save_run1/trace.terminal.sram.bin'
SRAM_SHA='0032c1cdb1600ec0eba51243200e1361d54014eb2755d6ace0cf4661d2f341e8'
RUNTIME_SOURCE_SHA='847bf77d28757ddad07b75b30d9071534b4792f7ad09a6cb3762153c8c29cd75'

def sha(data): return hashlib.sha256(data).hexdigest()

def bundle():
    b=c.bundle_identity()
    rows=[{'path':p,'sha256':sha((ROOT/p).read_bytes())} for p in
          ('tools/run_mesen_compat_menu_v1.py','tools/mesen_compat_menu_v1.lua',
           'tools/run_mesen_save_layout_native_v1.py')]
    payload=json.dumps({'builder_bundle':b,'probe_sources':rows},sort_keys=True,separators=(',',':')).encode()
    return {'sha256':sha(payload),'builder_bundle':b,'probe_sources':rows}

def collect(args):
    runtime.read_regular(ROOT/'tools/run_mesen_save_layout_native_v1.py',digest=RUNTIME_SOURCE_SHA)
    original={
      'rom':(c.DEFAULT_ROM,runtime.read_regular(c.DEFAULT_ROM,digest=c.ROM_SHA256)),
      'state':(STATE,runtime.read_regular(STATE,size=93029,digest=STATE_SHA)),
      'sram':(SRAM,runtime.read_regular(SRAM,size=8192,digest=SRAM_SHA)),
    }
    for name,(size,digest) in runtime.RUNTIME.items():
        path=ROOT/'private/tools/mesen2/app'/name
        original[name]=(path,runtime.read_regular(path,size=size,digest=digest))
    identity=bundle()
    output=c.private_path(args.output)
    if any(path.resolve().is_relative_to(output) for path,_ in original.values()):
        raise ValueError('output contains input')
    target,build=builder.build_image(original['rom'][1],output/'diagnostic.sfc')
    if args.mode=='control': target=original['rom'][1]
    report={'schema':'project-epoch-compat-menu-v1-run','mode':args.mode,'source_bundle':identity,
      'build':build if args.mode=='relocated' else {'rom_unchanged':True},
      'inputs':{k:{'path':str(p),'size':len(b),'sha256':sha(b)} for k,(p,b) in original.items()},
      'rom_sha256':sha(target),'launch_executed':False,'playable_pc07':False,
      'evidence_level':'verified-static-plan','global_ownership_proved':False,
      'source_checkpoint':'coldboot selected-slot validation followed by separately verified pre-JSL replay',
      'deferred_stop_excluded':True,'shutdown_sram_authoritative':False,
      'full_wram_reconciliation':False,'caller_return_observed':False,
      'planned_preparation':'C2E65B after native load return',
      'cleanup_is_not_continued_vanilla_compatibility':True}
    if not args.run_reviewed_bundle:
        runtime.check_inputs(original)
        if bundle()!=identity: raise ValueError('plan source drift')
        return report
    if args.run_reviewed_bundle!=identity['sha256']: raise ValueError('reviewed probe bundle mismatch')
    if output.exists(): raise ValueError('fresh private directory required')
    output.mkdir(parents=True)
    app=output/'app';(app/'Saves').mkdir(parents=True)
    for name in runtime.RUNTIME: (app/name).write_bytes(original[name][1])
    staged={'rom':output/'diagnostic.sfc','state':output/'entry.mss','sram':output/'input.sram',
            'collector':output/'collector.lua'}
    expected={'rom':target,'state':original['state'][1],'sram':original['sram'][1],'collector':COLLECTOR.read_bytes()}
    for name,path in staged.items(): path.write_bytes(expected[name])
    (app/'Saves/diagnostic.srm').write_bytes(original['sram'][1])
    env=os.environ.copy()
    for key in list(env):
        if key.startswith('PE_COMPAT_MENU_'): env.pop(key)
    env.update(PE_COMPAT_MENU_MODE=args.mode,PE_COMPAT_MENU_OUTPUT=str(output),
               PE_COMPAT_MENU_STATE=str(staged['state']),PE_COMPAT_MENU_SRAM=str(staged['sram']),
               PE_COMPAT_MENU_BUNDLE=identity['sha256'])
    command=[str(app/'Mesen.exe'),'--testRunner','--timeout=120','--doNotSaveSettings',
             '--debug.scriptWindow.allowIoOsAccess=true','--snes.port1.type=SnesController',
             str(staged['collector']),str(staged['rom'])]
    failure=None;process=None;launched=False;launch_attempted=False
    (output/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    try:
        if bundle()!=identity: raise ValueError('source drift before launch')
        runtime.check_inputs(original)
        launch_attempted=True
        process=subprocess.run(command,cwd=app,env=env,capture_output=True,text=True,timeout=140,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        launched=True
        if process.returncode!=63: raise ValueError(f'collector exit {process.returncode}')
        if (output/'failure.txt').exists(): raise ValueError('collector failure file')
        rows=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
        if rows[0].get('source_bundle')!=identity['sha256'] or rows[-1]['kind']!='success':
            raise ValueError('trace envelope')
        labels=['post_load','prepared',*[f'poll_{n}' for n in (150,390,630,900,1200,1500)],'cleanup']
        if [r['label'] for r in rows if r['kind']=='snapshot']!=labels: raise ValueError('snapshot sequence')
        for label in labels:
            if (output/(label+'.sram.bin')).read_bytes()!=original['sram'][1]: raise ValueError('SRAM drift')
            if (output/(label+'.wram.bin')).stat().st_size!=0x20000: raise ValueError('WRAM snapshot size')
        terminal=(output/'poll_1500.wram.bin').read_bytes()
        cleanup=(output/'cleanup.wram.bin').read_bytes()
        expected_cleanup=bytearray(terminal)
        if args.mode=='relocated':
            expected_cleanup[0x2830:0x2880]=terminal[0x2CA0:0x2CF0]
            expected_cleanup[0x2CA0:0x2CF0]=bytes(80)
        if cleanup!=expected_cleanup: raise ValueError('exact cleanup footprint/readback')
        report['caller_return_observed']=True
        report['records']=len(rows)
        report['observed_consumers']={f'{offset | 0xC00000:06X}':sum(r.get('kind')=='consumer' and r['site']==(offset | 0xC00000) for r in rows)
                                      for offset,_,_ in c.PATCHES}
    except subprocess.TimeoutExpired as exc:
        launched=True;failure=repr(exc)
    except Exception as exc: failure=repr(exc)
    finally:
        try:
            runtime.check_inputs(original)
            if bundle()!=identity: raise ValueError('source changed during launch')
            if any(path.read_bytes()!=expected[k] for k,path in staged.items()): raise ValueError('staged immutable input drift')
        except Exception as exc: failure=repr(exc)
        report.update(launch_executed=launched,launch_attempted=launch_attempted,
                      status='quarantined-failure' if failure else 'collected-awaiting-pair-review',
                      evidence_level='rejected-pilot' if failure else 'observed-runtime',failure=failure,
                      returncode=process.returncode if process else None)
        report['artifacts']={p.name:{'size':p.stat().st_size,'sha256':sha(p.read_bytes())}
            for p in output.iterdir() if p.is_file() and (p.suffix in {'.jsonl','.bin','.png','.txt'})}
        (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if failure: raise RuntimeError(failure)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('control','relocated'),required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-reviewed-bundle')
    print(json.dumps(collect(p.parse_args()),indent=2))

if __name__=='__main__': main()
