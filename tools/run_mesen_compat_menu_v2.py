"""Observe four residue bytes on the unchanged v1 menu route (separate v2).

Default: read-only plan. A successful process is a collected probe, not a
playability or global memory ownership certificate. Compare the paired traces,
selected memory and screenshots independently before promoting the result.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess

import schala_compat_menu_v1 as c
import build_schala_compat_menu_v1 as builder
import run_mesen_save_layout_native_v1 as runtime

ROOT=Path(__file__).resolve().parents[1]
COLLECTOR=ROOT/'tools/mesen_compat_menu_v2.lua'
STATE=ROOT/'private/test_runs/mesen2/load_entry_checkpoint_v1_native_save_run2/load_entry.mss'
STATE_SHA='cdbfc74c21a6a345f5c9b7d74fce9159b95a3ff735ecd92afde70332bce0a5e1'
SRAM=ROOT/'private/test_runs/mesen2/save_layout_native_v1_save_run1/trace.terminal.sram.bin'
SRAM_SHA='0032c1cdb1600ec0eba51243200e1361d54014eb2755d6ace0cf4661d2f341e8'
RUNTIME_SOURCE_SHA='847bf77d28757ddad07b75b30d9071534b4792f7ad09a6cb3762153c8c29cd75'
V1_BUILDER_BUNDLE_SHA='455c16343c6fffb672805652de4f527a0018dae8be3bd36298b45e8c34aedef6'
V1_PREREQUISITES={
    'tools/run_mesen_compat_menu_v1.py':'0232c5e84a4dc950124b7689cc1b980bb4132b2bf33e8b2f9706f247ff59569d',
    'tools/mesen_compat_menu_v1.lua':'3ecac7ed4081ffe4f6f1559d851c69a93ecc7d81c163e6a472e38de66d59324e',
    'references/ct_disassembly/bank_C0.asm':'b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8',
}
RESIDUE_ADDRESSES=(0x0A78,0x0A79,0x12158,0x12159)
RESIDUE_SITES={
    0xC2821F:(0x5A,'phy','before'),
    0xC28220:(0x08,'phy','successor'),
    0xC28213:(0x7A,'ply','before'),
    0xC28214:(0xFA,'ply','successor'),
    0xC28403:(0x4C,'terminal-sleep-jump','before'),
    0xC00911:(0x54,'restore-field-work','before'),
    0xC00914:(0xAB,'restore-field-work','successor'),
    0xC00924:(0x54,'save-field-work','before'),
    0xC00927:(0xAB,'save-field-work','successor'),
}
# Bus addresses, lengths and exact canonical-ROM span hashes. bank_C2 is also
# pinned by the frozen v1 builder; bank_C0 is an explicit additional dependency.
NATIVE_SPANS=(
    (0xC00905,38,'ad6bef875bc751c4d434552c476540019830a1851e6a735b9d6e60caf42aa8d6'),
    (0xC01958,33,'26b0180994c4e9d60badb45d6bbb8afdbfe65ee1133abc1e9451b82bf09ac1b1'),
    (0xC00129,3,'d386f459fbaf234b9678f7b3e6ef5e785e18d5c9b5b5e6b32b5efa0ed5612d89'),
    (0xC001A5,3,'77071168668cdcbf0f35002f6c2d452efb431dddccb2760f65e2e56e68aa655b'),
    (0xC001D8,3,'4a0b48d8bdda5ca6d00586cc8a8d51133a2e281b127ebb2c0b80421b9913c12a'),
    (0xC28206,16,'13051e65b83d68f523fce50bc0cadc7c53758657eaa92e21a3deeeb436941c55'),
    (0xC2821E,42,'2c557536e7d27c82ccfcf57a927e002bd30457b6e1fd06dc53d2d30e6bb4d778'),
    (0xC28320,45,'cddecef59a34d62c7a0e427666408816601fe6082ff2099760542b71d4d367ff'),
    (0xC283CA,60,'bc0a149260d1a594a3ff619f278757187082bb6610bba50d6929e0fa326c5863'),
    (0xC2837B,10,'c1466eec349698c6296a02e7323b45fcab73a3c2be5e223289db553d1c507d68'),
    (0xC2B9AB,26,'e94a94d025de2cd585f8107ad935e49d163f71261a13bca41de6447b6399867a'),
)

def sha(data): return hashlib.sha256(data).hexdigest()

def bundle():
    b=c.bundle_identity()
    if b['sha256']!=V1_BUILDER_BUNDLE_SHA: raise ValueError('frozen v1 builder bundle drift')
    for path,digest in V1_PREREQUISITES.items():
        runtime.read_regular(ROOT/path,digest=digest)
    rows=[{'path':p,'sha256':sha((ROOT/p).read_bytes())} for p in
          ('tools/run_mesen_compat_menu_v2.py','tools/mesen_compat_menu_v2.lua',
           'tests/test_mesen_compat_menu_v2.py','tools/run_mesen_save_layout_native_v1.py')]
    components={'builder_bundle':b,'probe_sources':rows,'frozen_prerequisites':V1_PREREQUISITES}
    payload=json.dumps(components,sort_keys=True,separators=(',',':')).encode()
    return {'sha256':sha(payload),**components}

def native_source_contract(rom):
    if type(rom) is not bytes or len(rom)!=c.ROM_SIZE or sha(rom)!=c.ROM_SHA256:
        raise ValueError('native source requires canonical ROM')
    for pc,size,digest in NATIVE_SPANS:
        if sha(rom[pc-0xC00000:pc-0xC00000+size])!=digest:
            raise ValueError('residue native span drift')
    for pc,(opcode,_,_) in RESIDUE_SITES.items():
        if rom[pc-0xC00000]!=opcode: raise ValueError('residue native opcode drift')
    return {'spans':[{'pc':pc,'size':size,'sha256':digest} for pc,size,digest in NATIVE_SPANS],
            'exec_sites':[{'pc':pc,'opcode':opcode,'role':role,'phase':phase}
                          for pc,(opcode,role,phase) in RESIDUE_SITES.items()],
            'watched_physical_bytes':list(RESIDUE_ADDRESSES),
            'source_evidence':'canonical source aligned; native lifetime pending observation'}

def _integer(value,lo,hi,label):
    if type(value) is not int or not lo<=value<=hi: raise ValueError(label)
    return value

def physical_wram(address):
    """SNES CPU WRAM banks and low 8-KiB mirrors; all other routes refuse."""
    _integer(address,0,0xFFFFFF,'residue bus address')
    bank=address>>16;offset=address&0xFFFF
    if bank in (0x7E,0x7F): return address-0x7E0000
    if (bank<=0x3F or 0x80<=bank<=0xBF) and offset<0x2000: return offset
    raise ValueError('residue bus address is not a WRAM alias')

def _cpu_tuple(row):
    for k in ('a','x','y','d','sp','pc'): _integer(row[k],0,0xFFFF,'CPU '+k)
    for k in ('dbr','ps','k'): _integer(row[k],0,0xFF,'CPU '+k)
    if type(row['emulationMode']) is not bool: raise ValueError('CPU emulationMode')
    _integer(row['clock'],0,2**64-1,'CPU full master clock')

def audit_residue(rows,snapshots):
    """Reconcile only four bytes, using ordered native writes/reads and snapshots.

    The preceding-exec context is not automatically an instruction-owner proof.
    Unexpected contexts are retained as review boundaries, never called corrupt.
    This does not replace the independent v1-projection and screenshot review.
    """
    if [r.get('n') for r in rows]!=list(range(1,len(rows)+1)):
        raise ValueError('trace record sequence')
    current=None;contexts=Counter();witnesses=Counter();bus_count=0;last_exec=0
    labels=[]
    for row in rows:
        kind=row['kind']
        if kind=='snapshot':
            label=row['label'];data=snapshots[label]
            if type(data) is not bytes or len(data)!=0x20000: raise ValueError('residue snapshot size')
            actual={a:data[a] for a in RESIDUE_ADDRESSES}
            if current is None:
                if label!='post_load': raise ValueError('residue initial snapshot')
                current=actual
            elif current!=actual: raise ValueError('residue snapshot/write reconciliation: '+label)
            labels.append(label)
        elif kind in ('residue-bus','residue-exec'):
            if current is None or labels[-1]=='cleanup': raise ValueError('residue event outside observation')
            index=_integer(row['exec_index'],1,2**53-1,'residue exec index')
            if index<last_exec: raise ValueError('residue exec index order')
            last_exec=index
            _integer(row['poll'],0,1500,'residue input poll')
            if kind=='residue-bus':
                bus_count+=1
                _cpu_tuple(row['cpu_observed'])
                a=_integer(row['physical'],0,0x1FFFF,'residue address')
                if a not in current: raise ValueError('undeclared residue address')
                if physical_wram(row['address'])!=a: raise ValueError('residue bus/physical address mismatch')
                value=_integer(row['value'],0,255,'residue byte')
                pc=_integer(row['preceding_exec_pc'],0,0xFFFFFF,'preceding exec PC')
                op=row['operation']
                if op=='read':
                    if value!=current[a]: raise ValueError('residue read/write reconciliation')
                elif op=='write': current[a]=value
                else: raise ValueError('residue operation')
                contexts[pc,op,a]+=1
            else:
                _cpu_tuple(row['cpu'])
                pc=_integer(row['site'],0,0xFFFFFF,'residue witness PC')
                expected=RESIDUE_SITES.get(pc)
                if expected is None or (row['opcode'],row['role'],row['phase'])!=expected:
                    raise ValueError('residue witness identity')
                if (row['cpu']['k']<<16)|row['cpu']['pc']!=pc: raise ValueError('residue witness CPU PC')
                for base,key in ((0x0A78,'stack_word'),(0x12158,'backup_word')):
                    value=_integer(row[key],0,0xFFFF,'residue witness word')
                    if value!=current[base]|(current[base+1]<<8): raise ValueError('residue witness readback')
                witnesses[pc]+=1
    if labels!=['post_load','prepared',*[f'poll_{n}' for n in (150,390,630,900,1200,1500)],'cleanup']:
        raise ValueError('residue snapshot sequence')
    if not bus_count or set(witnesses)!=set(RESIDUE_SITES): raise ValueError('residue witness coverage')
    expected_contexts={0xC2821F,0xC2822C,0xC28213,0xC00911,0xC00924}
    return {'watched_physical_bytes':list(RESIDUE_ADDRESSES),'bus_records':bus_count,
            'observed_exec_witnesses':{f'{pc:06X}':n for pc,n in sorted(witnesses.items())},
            'access_contexts':[{'preceding_exec_pc':f'{pc:06X}','operation':op,'physical':a,
                                'count':n,'outside_initial_context_hypothesis':pc not in expected_contexts}
                               for (pc,op,a),n in sorted(contexts.items())],
            'four_byte_values_reconciled':True,'instruction_ownership_proved':False,
            'semantic_read_safety_proved':False,'unexpected_contexts_are_review_boundaries':True}

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
    native_contract=native_source_contract(original['rom'][1])
    output=c.private_path(args.output)
    if any(path.resolve().is_relative_to(output) for path,_ in original.values()):
        raise ValueError('output contains input')
    target,build=builder.build_image(original['rom'][1],output/'diagnostic.sfc')
    if args.mode=='control': target=original['rom'][1]
    report={'schema':'project-epoch-compat-menu-v2-run','mode':args.mode,'source_bundle':identity,
      'build':build if args.mode=='relocated' else {'rom_unchanged':True},
      'inputs':{k:{'path':str(p),'size':len(b),'sha256':sha(b)} for k,(p,b) in original.items()},
      'rom_sha256':sha(target),'launch_executed':False,'playable_pc07':False,
      'evidence_level':'verified-static-plan','global_ownership_proved':False,
      'source_checkpoint':'coldboot selected-slot validation followed by separately verified pre-JSL replay',
      'deferred_stop_excluded':True,'shutdown_sram_authoritative':False,
      'full_wram_reconciliation':False,'caller_return_observed':False,
      'planned_preparation':'C2E65B after native load return',
      'residue_source_contract':native_contract,
      'residue_lifetime_observed':False,'residue_semantic_safety_proved':False,
      'v1_bus_collector_source_preserved':True,
      'v1_runtime_projection_verified':False,
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
        if rows[0].get('schema')!='project-epoch-compat-menu-v2' or rows[0].get('mode')!=args.mode:
            raise ValueError('v2 trace identity')
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
        report['residue_observation']=audit_residue(rows,{label:(output/(label+'.wram.bin')).read_bytes() for label in labels})
        report['residue_lifetime_observed']=True
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
