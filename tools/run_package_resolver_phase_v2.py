#!/usr/bin/env python3
"""Read-only phase v2: reconcile early contexts, then reuse the frozen v1 validator.

The early-context projection is explicit, complete and independently matched to
the accepted context trace. It is not an interrupt-free native execution claim.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import run_package_resolver_phase_v1 as v1

context=v1.context;safe=v1.safe;ROOT=v1.ROOT
PhaseError=v1.PhaseError;require=v1.require;serial=v1.serial;sha=v1.sha
read_bounded=v1.read_bounded;parse_trace=v1.parse_trace;MAX_TRACE=v1.MAX_TRACE
SCHEMA='project-epoch-package-resolver-phase-v2'
COLLECTOR=ROOT/'tools/mesen_package_resolver_phase_v2.lua'
TESTS=ROOT/'tests/test_package_resolver_phase_v2.py'
V1_PINS={
 'launcher':('tools/run_package_resolver_phase_v1.py','cf931ff23f11bd5045b437001f3365f69d3c1530a43e6569f2b41474356cb321'),
 'collector':('tools/mesen_package_resolver_phase_v1.lua','2dbab520abbd8bc95bd078a81153d0d2f6d49147e01a66591ce0c5e726c6850c'),
 'tests':('tests/test_package_resolver_phase_v1.py','06ecf78a69dc4f0167c4a83ad36ac46d31b3a601357821b747e1d634818784fe')}

def reference_records():
    phases=v1.reference_records()
    path=safe.resolve_private_file(ROOT/v1.REFERENCE[0],'accepted context trace')
    data=read_bounded(path,v1.REFERENCE[1],'accepted context trace')
    require(len(data)==v1.REFERENCE[1] and sha(data)==v1.REFERENCE[2],'accepted context identity')
    rows=json.loads(data)['records'];clock=phases['resolver-entry']['timing']['memoryManager.masterClock']
    early=[row for row in rows if row['kind'] in {'interrupt-entry','interrupt-rti'} and
        row['timing']['memoryManager.masterClock']<clock]
    return {'phases':phases,'earlier_context_records':early}

def historical_match(row,old):
    for key in ('kind','address','cpu','stack','trampolines','timing','poll','context_id','context_kind','context_depth'):
        require(row[key]==old[key],'early historical '+key)
    for key in v1.GATES&set(old['wram']):
        require(row['gates'][key]==old['wram'][key],'early historical gate '+key)

def gate_read_witness(records,kind,address):
    sites=[i for i,row in enumerate(records) if row['kind']==kind]
    require(len(sites)==1 and sites[0]+1<len(records),'unique paired '+kind)
    index=sites[0];entry=records[index];read=records[index+1]
    require(read['kind']=='bus-read' and read['address']==address,'immediate watched read '+kind)
    expected=entry['cpu'].copy();expected['pc']+=3
    require(entry['cpu']['ps']&0x20 and entry['cpu']['dbr']==0x7E,'M8 DBR7E '+kind)
    require(read['cpu']==expected,'pre-data-read CPU '+kind)
    for key in ('poll','context_id','context_kind','context_depth','stack','trampolines'):
        require(read[key]==entry[key],'owned gate read '+key)
    require(read['context_kind']=='normal-nmi','normal NMI gate read')
    require(read['value']==entry['gates'][f'{address&65535:04X}']==read['gates'][f'{address&65535:04X}'],
        'gate entry/read/snapshot agreement')
    return {'entry_index':index,'read_index':index+1,'entry_pc':entry['address'],'read_bus_address':address}

def summarize(trace,reference):
    v1.exact(trace,{'schema','records','error','terminal_poll'},'v2 trace')
    require(trace['schema']==SCHEMA,'v2 schema')
    records=trace['records'];require(type(records) is list and 9<=len(records)<=v1.MAX_RECORDS,'bounded v2 records')
    last=(-1,-1,-1,-1);last_interrupt_id=0
    for row in records:
        v1.validate_record(row)
        t=row['timing'];now=(row['poll'],t['memoryManager.masterClock'],t['cpu.cycleCount'],t['ppu.frameCount'])
        require(all(a>=b for a,b in zip(now,last)),'all-row monotonic counters');last=now
        if row['kind']=='interrupt-entry':
            require(row['context_id']>last_interrupt_id,'globally increasing interrupt identities')
            last_interrupt_id=row['context_id']
    resolver_indices=[i for i,row in enumerate(records) if row['kind']=='resolver-entry']
    pre_indices=[i for i,row in enumerate(records) if row['kind']=='pre-effect']
    require(len(resolver_indices)==1 and len(pre_indices)<=1,'single resolver/optional pre-effect')
    resolver_index=resolver_indices[0]
    if pre_indices:require(pre_indices[0]<resolver_index,'pre-effect precedes resolver')
    pre_index=pre_indices[0] if pre_indices else resolver_index
    start_clock=records[pre_index]['timing']['memoryManager.masterClock']
    resolver_clock=records[resolver_index]['timing']['memoryManager.masterClock']
    expected=[row for row in reference['earlier_context_records'] if
        start_clock<row['timing']['memoryManager.masterClock']<resolver_clock]
    # This version expands only the observed bounded early window. It still
    # refuses nested/alternate contexts and any incomplete boundary frame.
    require(len(expected)<=16,'at most eight historical early contexts')
    observed=[];removed=set();live=None;early_pairs=[];early_bus_counts=Counter()
    for index in range(pre_index+1,resolver_index):
        row=records[index];kind=row['kind']
        if kind=='interrupt-entry':
            require(live is None,'non-nested early interrupt')
            live=(index,row);observed.append(row)
        if live is None:
            require((row['context_id'],row['context_depth'],row['context_kind'])==(0,0,'main'),'unowned early context')
            require(kind not in {'interrupt-rti','scene-gate','scene-effect-gate'},'early main record kind')
        else:
            entry=live[1]
            require((row['context_id'],row['context_depth'],row['context_kind'])==(entry['context_id'],1,entry['context_kind']),
                'early context ownership')
            require(kind in {'interrupt-entry','interrupt-rti',*v1.BUS_KINDS},'early context record kind')
            removed.add(index)
            if kind in v1.BUS_KINDS:
                early_bus_counts[kind+'/'+v1.bus_domain(row['address'])]+=1
                physical=v1.physical_wram(row['address'])
                if kind=='bus-read' and physical is not None:
                    require(row['value']==row['gates'][f'{physical:04X}'],'early gate read/snapshot')
        if kind=='interrupt-rti':
            require(live is not None,'paired early RTI')
            entry_index,entry=live
            require(row['stack']==entry['stack'],'intact early stack window')
            for key in ('a','x','y','d','dbr','sp','emulationMode'):
                require(row['cpu'][key]==entry['cpu'][key],'early preserved '+key)
            observed.append(row)
            early_pairs.append({'kind':entry['context_kind'],'context_id':entry['context_id'],
                'entry_index':entry_index,'rti_index':index,'entry_clock':entry['timing']['memoryManager.masterClock'],
                'rti_clock':row['timing']['memoryManager.masterClock'],'entry_sp':entry['cpu']['sp'],
                'entry_engine':entry['engine'],'rti_engine':row['engine']})
            live=None
    require(live is None,'no early context crosses resolver')
    require(len(observed)==len(expected),'complete historical early context sequence')
    for row,old in zip(observed,expected):historical_match(row,old)
    kept=[i for i in range(len(records)) if i not in removed]
    projected={**trace,'schema':v1.SCHEMA,'records':[records[i] for i in kept]}
    result=v1.summarize(projected,reference['phases'])
    for row in records[resolver_index:]:
        if row['kind'] in {'interrupt-entry','interrupt-rti'}:
            old=reference['phases'][row['context_kind']+'-'+row['kind']]
            require(row['context_id']==old['context_id'],'historical post-resolver context identity')
    for phase in result['phases'].values():phase['index']=kept[phase['index']]
    # Each witness is bounded to one pinned canonical AD absolute instruction;
    # this does not establish all instructions or bus operations between phases.
    witnesses=[gate_read_witness(records,'scene-gate',0x7ECCEA),
        gate_read_witness(records,'scene-effect-gate',0x7E5D9B)]
    result['post_resolver_interrupt_pairs']=result.pop('interrupt_pairs')
    result.update(record_count=len(records),event_counts=dict(sorted(Counter(row['kind'] for row in records).items())),
        bus_counts=dict(sorted(Counter(row['kind']+'/'+v1.bus_domain(row['address']) for row in records if row['kind'] in v1.BUS_KINDS).items())),
        early_interrupt_pairs=early_pairs,early_interrupt_bus_counts=dict(sorted(early_bus_counts.items())),
        early_historical_records_matched=len(observed),gate_read_witnesses=witnesses,
        projection={'kind':'remove-only-individually-validated-owned-early-context-records',
            'removed_record_count':len(removed),'retained_record_count':len(kept),
            'native_interrupt_free_execution':False})
    return result

def source_paths():
    paths=v1.source_paths()
    for key,(relative,pin) in V1_PINS.items():
        path=ROOT/relative;require(sha(path.read_bytes())==pin,'frozen v1 '+key)
        paths['v1_'+key]=path
    paths.update(launcher=Path(__file__).resolve(),collector=COLLECTOR,tests=TESTS)
    # The data-read witness relies on the canonical instruction lengths/opcodes.
    rom_path=safe.resolve_private_file(ROOT/context.PINNED['rom'][0],'pinned ROM')
    raw=read_bounded(rom_path,context.PINNED['rom'][1],'pinned ROM')
    require(sha(raw)==context.PINNED['rom'][2],'pinned ROM for gate instruction witnesses')
    require(raw[0xD1609:0xD160C]==bytes((0xAD,0xEA,0xCC)) and
        raw[0xD160E:0xD1611]==bytes((0xAD,0x9B,0x5D)),'canonical gate AD preimages')
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
    stem='pe_resolver_phase_v2_'+secrets.token_hex(12)
    for key,path in inputs.items():
        target=saves/(stem+'.srm') if key=='sram' else stage/(stem+('.sfc' if key=='rom' else '.mss'))
        safe.copy_new_regular_file(path,target,key);staged[key]=target
    staged['collector']=stage/'collector.lua';safe.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    stage_before={key:safe.sha256_file(path) for key,path in staged.items()}
    require(all(stage_before[key]==before[key] for key in staged),'exact staged bytes')
    receipt={'schema':SCHEMA,'source_hashes':before,'staged_hashes':stage_before,
        'source_archive_hashes':archive_before,'source_archive_files':{key:path.name for key,path in archives.items()}}
    (output/'launch_inputs.json').write_bytes(serial(receipt))
    env=safe.minimal_subprocess_environment()
    for key,parts in {'USERPROFILE':('profile',),'APPDATA':('profile','AppData','Roaming'),
        'LOCALAPPDATA':('profile','AppData','Local'),'TEMP':('temp',),'TMP':('temp',)}.items():
        path=stage.joinpath(*parts);path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    env.update(PE_RESOLVER_PHASE_V2_PROTOCOL=SCHEMA,PE_RESOLVER_PHASE_V2_STATE=str(staged['state']),
        PE_RESOLVER_PHASE_V2_TRACE=str(output/'trace.json'))
    command=[str(staged['mesen']),'--testRunner','--timeout=900','--doNotSaveSettings',
        '--debug.scriptWindow.allowIoOsAccess=true','--snes.ramPowerOnState=AllZeros',
        '--snes.port1.type=SnesController',str(staged['collector']),str(staged['rom'])]
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
