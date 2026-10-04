#!/usr/bin/env python3
"""Add IRQ counters and a source-owned cache crossing to frozen phase v2.

This is a read-only checkpoint replay. Hidden PPU cache fields are not exposed
by Mesen's Map serializer. The crossing is conditional on valid source state,
not an independent decoding of those hidden cached values.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import run_package_resolver_phase_v2 as v2

v1=v2.v1;context=v2.context;safe=v2.safe;ROOT=v2.ROOT
PhaseError=v2.PhaseError;require=v2.require;serial=v2.serial;sha=v2.sha
read_bounded=v2.read_bounded;parse_trace=v2.parse_trace;MAX_TRACE=v2.MAX_TRACE
SCHEMA='project-epoch-package-resolver-phase-v3'
COLLECTOR=ROOT/'tools/mesen_package_resolver_phase_v3.lua'
TESTS=ROOT/'tests/test_package_resolver_phase_v3.py'
COUNTERS={'internalRegisters.hCounter','internalRegisters.vCounter'}
CACHE_KINDS={'cache-frame-start','cache-line-one'}
GUARDED_SETTINGS=['--snes.ppuExtraScanlinesBeforeNmi=0','--snes.ppuExtraScanlinesAfterNmi=0']
V2_PINS={
 'launcher':('tools/run_package_resolver_phase_v2.py','f06f95c4e3169780220444db774024ab7b1c55227a7b3c9dbdfc0b0bd8e29acd'),
 'collector':('tools/mesen_package_resolver_phase_v2.lua','63e9f8203ff5a31af43c616a502a66fda6e0505146f5b747dbe2d9867bc403fe'),
 'tests':('tests/test_package_resolver_phase_v2.py','748a2c43bc7713b07e2195c3e06d6886598a25bda9ac39bdfd99511f6217c4a6')}
CONFIG_PINS={
 'SnesConfig.cs':'17f100d1219270861a6f524ac078e279bd2bed190ac9c62dc8a74b20c35a7a59',
 'ConfigManager.cs':'e2ec6d0a15bb5e9908baf4c4c8cc8cbb3cbdaf2b13fb0980390bd99beda6641d',
 'SettingTypes.h':'0396504d406ce23e30761a3875c35392a941f94cb3164910747951bca179f14c',
 'SnesPpu.h':'15859642a2f720b4fbc8298583705e4fecd16397d6da32f57cf8f2bd12cc8f89'}
V2_TRACE=('private/test_runs/resolver_phase_v2_full_20261003_1/trace.json',17782665,
 '7e2d2925f8523a134721427c1001128a073b6b64518abe3810ee637cb5e71bb0')

def reference_records():
    path=safe.resolve_private_file(ROOT/V2_TRACE[0],'accepted v2 trace')
    raw=read_bounded(path,V2_TRACE[1],'accepted v2 trace')
    require(len(raw)==V2_TRACE[1] and sha(raw)==V2_TRACE[2],'accepted v2 trace identity')
    reference=v2.reference_records()
    context_raw=read_bounded(ROOT/v1.REFERENCE[0],v1.REFERENCE[1],'accepted context trace')
    require(sha(context_raw)==v1.REFERENCE[2],'cache context reference identity')
    pair=[r for r in json.loads(context_raw)['records'] if r['kind'] in {'interrupt-entry','interrupt-rti'} and r['context_id']==1]
    require([r['kind'] for r in pair]==['interrupt-entry','interrupt-rti'],'first historical context pair')
    return {'v2_reference':reference,'v2_trace':parse_trace(raw),'cache_context':pair}

def projected_record(row):
    v1.exact(row,v1.RECORD_KEYS,'v3 record')
    v1.exact(row['engine'],v1.ENGINE_KEYS|COUNTERS,'v3 engine')
    for key in COUNTERS:v1.integer(row['engine'][key],0,65535,key)
    projected={**row,'engine':{k:v for k,v in row['engine'].items() if k not in COUNTERS}}
    if row['kind'] in CACHE_KINDS:
        # Reuse only the common field validation; own the added event semantics here.
        v1.validate_record({**projected,'kind':'baseline','address':0})
        if row['kind']=='cache-frame-start':require(type(row['address']) is int and row['address']==0,'frame event address')
        else:
            v1.integer(row['address'],0,0xFFFFFF,'line-one execution address')
            require(row['address']==(row['cpu']['k']<<16)|row['cpu']['pc'],'line-one PC ownership')
    else:v1.validate_record(projected)
    return projected

def summarize(trace,reference):
    v1.exact(trace,{'schema','records','error','terminal_poll'},'v3 trace')
    require(trace['schema']==SCHEMA,'v3 schema')
    records=trace['records'];require(type(records) is list and 11<=len(records)<=v1.MAX_RECORDS,'bounded v3 records')
    projected=[];kept=[];cache=[];last=(-1,-1,-1,-1)
    for index,row in enumerate(records):
        old=projected_record(row);t=row['timing']
        now=(row['poll'],t['memoryManager.masterClock'],t['cpu.cycleCount'],t['ppu.frameCount'])
        require(all(a>=b for a,b in zip(now,last)),'all v3 rows monotonic');last=now
        if row['kind'] in CACHE_KINDS:cache.append((index,row))
        else:projected.append(old);kept.append(index)
    require([r['kind'] for _,r in cache]==['cache-frame-start','cache-line-one'],'exact cache pair order')
    (start_index,start),(end_index,end)=cache
    require(start_index==1 and end_index==2,'cache witness immediately after baseline')
    a=start['timing'];b=end['timing']
    require(a['ppu.scanline']==0 and a['memoryManager.hClock']==0,'source-owned frame-start raster')
    require(b['ppu.scanline']==1 and b['memoryManager.hClock']<=128,'first line-one execution raster')
    require(start['poll']==end['poll']==0 and a['ppu.frameCount']==b['ppu.frameCount'],'same first replay frame/poll')
    delta=b['memoryManager.masterClock']-a['memoryManager.masterClock']
    require(delta==1364+b['memoryManager.hClock'],'one exact line-zero crossing')
    entry,rti=reference['cache_context']
    for row in (start,end):
        require((row['context_id'],row['context_depth'],row['context_kind'])==
            (entry['context_id'],entry['context_depth'],entry['context_kind'])==
            (rti['context_id'],rti['context_depth'],rti['context_kind']), 'cache historical context identity')
        require(entry['timing']['memoryManager.masterClock']<row['timing']['memoryManager.masterClock']<
            rti['timing']['memoryManager.masterClock'],'cache within historical context clocks')
    legacy={**trace,'schema':v2.SCHEMA,'records':projected}
    require(legacy==reference['v2_trace'],'complete frozen v2 trace equality')
    legacy_summary=v2.summarize(legacy,reference['v2_reference'])
    return {'record_count':len(records),'engine_field_count':len(v1.ENGINE_KEYS|COUNTERS),
      'legacy_summary':legacy_summary,'projection_to_native_indices':kept,
      'complete_v2_trace_equal':True,'cache_witness':{
        'start_index':start_index,'end_index':end_index,'elapsed_master_clocks':delta,
        'start_timing':a,'end_timing':b,'guarded_cli_settings':GUARDED_SETTINGS,
        'valid_source_state_required':True,'hidden_cache_values_directly_observed':False,
        'source_conditional_refresh_crossing':True,'context_kind':start['context_kind'],
        'context_id':start['context_id'],'interrupt_free_crossing':False},
      'native_helper_executed':False,'deadline_certified':False,'production_approval':False}

def source_paths():
    paths=v2.source_paths()
    for key,(relative,pin) in V2_PINS.items():
        path=ROOT/relative;require(sha(path.read_bytes())==pin,'frozen v2 '+key);paths['v2_'+key]=path
    for name,pin in CONFIG_PINS.items():
        path=ROOT/'private/test_runs/resolver_irq_admission_design_20261003/source'/name
        require(sha(path.read_bytes())==pin,'configuration source '+name);paths['config_'+name.replace('.','_')]=path
    paths.update(launcher=Path(__file__).resolve(),collector=COLLECTOR,tests=TESTS,
        v2_reference_trace=ROOT/V2_TRACE[0])
    return paths
def run(output_dir:Path):
    private=safe.canonical_private_root();inputs={}
    for key,(relative,size,pin) in context.PINNED.items():
        path=safe.resolve_private_file(ROOT/relative,key,private_root=private)
        require(path.stat().st_size==size and safe.sha256_file(path)==pin,'pinned '+key);inputs[key]=path
    runtime={key:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/name,key,private_root=private) for key,name in safe.RUNTIME_NAMES.items()}
    for key,path in runtime.items():safe.require_identity(path,key)
    sources=source_paths();guarded={**inputs,**runtime,**sources}
    before={key:safe.sha256_file(path) for key,path in guarded.items()};reference=reference_records()
    output=safe.prepare_private_output_dir(output_dir,private_root=private,
        forbidden_roots=tuple(path.parent for path in inputs.values())+(safe.DEFAULT_MESEN.parent,))
    archive=output/'source_archive';archive.mkdir();archives={}
    for key,path in sources.items():
        if key=='reference_trace':continue
        target=archive/(key+path.suffix);safe.copy_new_regular_file(path,target,key);archives[key]=target
    archive_before={key:safe.sha256_file(path) for key,path in archives.items()}
    require(all(archive_before[key]==before[key] for key in archives),'exact archived bytes')
    stage=output/'staged';app=stage/'app';saves=app/'Saves';saves.mkdir(parents=True);staged={}
    for key,name in safe.RUNTIME_NAMES.items():
        staged[key]=app/name;safe.copy_new_regular_file(runtime[key],staged[key],key)
    stem='pe_resolver_phase_v3_'+secrets.token_hex(12)
    for key,path in inputs.items():
        target=saves/(stem+'.srm') if key=='sram' else stage/(stem+('.sfc' if key=='rom' else '.mss'))
        safe.copy_new_regular_file(path,target,key);staged[key]=target
    staged['collector']=stage/'collector.lua';safe.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    stage_before={key:safe.sha256_file(path) for key,path in staged.items()}
    require(all(stage_before[key]==before[key] for key in staged),'exact staged bytes')
    receipt={'schema':SCHEMA,'source_hashes':before,'staged_hashes':stage_before,
        'source_archive_hashes':archive_before,'source_archive_files':{key:path.name for key,path in archives.items()},
        'guarded_settings':GUARDED_SETTINGS}
    (output/'launch_inputs.json').write_bytes(serial(receipt))
    env=safe.minimal_subprocess_environment()
    for key,parts in {'USERPROFILE':('profile',),'APPDATA':('profile','AppData','Roaming'),
        'LOCALAPPDATA':('profile','AppData','Local'),'TEMP':('temp',),'TMP':('temp',)}.items():
        path=stage.joinpath(*parts);path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    env.update(PE_RESOLVER_PHASE_V3_PROTOCOL=SCHEMA,PE_RESOLVER_PHASE_V3_STATE=str(staged['state']),
        PE_RESOLVER_PHASE_V3_TRACE=str(output/'trace.json'))
    command=[str(staged['mesen']),'--testRunner','--timeout=900','--doNotSaveSettings',
        '--debug.scriptWindow.allowIoOsAccess=true','--snes.ramPowerOnState=AllZeros',
        '--snes.port1.type=SnesController',*GUARDED_SETTINGS,str(staged['collector']),str(staged['rom'])]
    process=None;error=None
    try:
        process=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=915,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=False)
        (output/'process.log').write_bytes(process.stdout+process.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:error=str(exc)
    process_receipt={'schema':SCHEMA,'returncode':process.returncode if process else None,'exception':error}
    (output/'process_receipt.json').write_bytes(serial(process_receipt))
    safe.require_file_hashes_unchanged(guarded,before,'source')
    safe.require_file_hashes_unchanged(staged,stage_before,'staged')
    safe.require_file_hashes_unchanged(archives,archive_before,'source archive')
    require((output/'launch_inputs.json').read_bytes()==serial(receipt),'unchanged launch receipt')
    require(sorted(path.name for path in archive.iterdir())==sorted(path.name for path in archives.values()),'exact archive inventory')
    safe.require_exact_staged_save_entries(sorted(path.name for path in saves.iterdir()),staged['sram'].name)
    require(process is not None and error is None and process.returncode==52,'native observation failed; private artifacts retained')
    require(not (output/'trace.json.error.txt').exists(),'collector error sidecar absent')
    trace_path=output/'trace.json'
    raw=read_bounded(trace_path,MAX_TRACE,'phase trace')
    try:observations=summarize(parse_trace(raw),reference)
    except (ValueError,KeyError,TypeError) as exc:
        (output/'host_rejection.json').write_bytes(serial({'schema':SCHEMA,'error':str(exc),'trace_sha256':sha(raw)}));raise
    result={**receipt,'evidence_level':'exploratory-runtime-not-accepted','observations':observations,
        'trace_sha256':sha(raw),'process_receipt_sha256':sha(serial(process_receipt)),
        'sources_staged_archives_unchanged':True,'checkpoint_load_only':True,
        'controller_schedule_reused':True,'rom_cpu_memory_edits':False,'production_approval':False}
    (output/'manifest.json').write_bytes(serial(result));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    sys.stdout.buffer.write((json.dumps(run(parser.parse_args().output_dir),indent=2)+'\n').encode())
