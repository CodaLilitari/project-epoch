#!/usr/bin/env python3
"""Revalidate an exact pair of private resolver-phase v3 observations.

The previously accepted NMI auditor supplies only unchanged file/JSON guards.
Its NMI trace semantics are not reused. The separately pinned phase observer
validates every new trace record and historical-context comparison.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import audit_normal_nmi_stack_observation_v1 as files

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-package-resolver-phase-v3-accepted-pair'
UTILITY_PIN=('tools/audit_normal_nmi_stack_observation_v1.py',17388,
 '7a6bd6c7300db1899d7cd5619f4120682be29f695fbe9f0c7ac4353dbffadc9b')
OBSERVER_PINS={'tools/run_package_resolver_phase_v3.py': (12674, 'c1ef98fca6660cc33381503c8e38e98b279eb3ef84413b637b6e6d33cd12790f'), 'tools/mesen_package_resolver_phase_v3.lua': (10424, '0ad2559374c23816dad376f2ee4f6bc51ce8288f2c9a7107d87d7eb44f576fa4'), 'tests/test_package_resolver_phase_v3.py': (5857, '0f2b5fdcfc7e11d7ab43b0e7bc05be24c7ad642db69d471eb05d6b2b8a544ecc')}
HARDWARE_KEYS=(
 'internalRegisters.hCounter','internalRegisters.vCounter',
 'cpu.irqSource','cpu.prevIrqSource','cpu.irqLock','cpu.needNmi','cpu.nmiFlagCounter',
 'internalRegisters.enableNmi','internalRegisters.enableHorizontalIrq',
 'internalRegisters.enableVerticalIrq','internalRegisters.horizontalTimer',
 'internalRegisters.verticalTimer','internalRegisters.irqFlag','internalRegisters.irqLevel',
 'internalRegisters.needIrq','internalRegisters.nmiFlag','dmaController.hdmaChannels',
 'dmaController.dmaPending','dmaController.dmaStartDelay','dmaController.needToProcess',
 'dmaController.hdmaPending','dmaController.hdmaInitPending',
 'ppu.overscanMode','ppu.screenInterlace','ppu.objInterlace')
RECEIPT_KEYS={'schema','source_hashes','staged_hashes','source_archive_hashes','source_archive_files','guarded_settings'}
require=files.require
serial=files.serial
sha=files.sha

def observer_module(ledger):
    relative,size,pin=UTILITY_PIN
    row=ledger.file(ROOT/relative)
    require((row['size_bytes'],row['sha256'])==(size,pin),'file-guard utility pin')
    require(len(OBSERVER_PINS)>=3,'phase observer pins not frozen')
    for name,(size,pin) in OBSERVER_PINS.items():
        row=ledger.file(ROOT/name)
        require((row['size_bytes'],row['sha256'])==(size,pin),'phase observer pin '+name)
    import run_package_resolver_phase_v3 as observer
    require(Path(observer.__file__).resolve()==ROOT/'tools/run_package_resolver_phase_v3.py','exact observer module')
    return observer

def current_sources(observer,ledger):
    paths=observer.source_paths()
    for key,(relative,size,pin) in observer.context.PINNED.items():
        path=ROOT/relative;row=ledger.file(path)
        require((row['size_bytes'],row['sha256'])==(size,pin),'canonical input pin '+key)
        paths[key]=path
    for key,name in observer.safe.RUNTIME_NAMES.items():
        path=observer.safe.DEFAULT_MESEN.parent/name;row=ledger.file(path)
        require((row['size_bytes'],row['sha256'])==observer.safe.PINNED_IDENTITIES[key],'runtime pin '+key)
        paths[key]=path
    sources={key:ledger.file(path) for key,path in paths.items()}
    _,size,pin=observer.v1.REFERENCE
    require((sources['reference_trace']['size_bytes'],sources['reference_trace']['sha256'])==(size,pin),'historical reference pin')
    return paths,sources

def process_contract(value,schema):
    require(type(value) is dict and set(value)=={'schema','returncode','exception'},'exact process receipt')
    require(value['schema']==schema and type(value['returncode']) is int and value['returncode']==52
            and value['exception'] is None,'successful native process receipt')

def compact(trace,summary):
    """Emit counts and selected emulator hardware observations, never game arrays."""
    phase=[]
    for row in trace['records']:
        if row['kind'] not in {'pre-effect','resolver-entry','resolver-tail','common-loader-entry','scene-gate','scene-effect-gate'}:
            continue
        e=row['engine'];t=row['timing']
        phase.append({'kind':row['kind'],'poll':row['poll'],
          'master_clock':t['memoryManager.masterClock'],'scanline':t['ppu.scanline'],
          'hclock':t['memoryManager.hClock'],'hardware':{key:e[key] for key in HARDWARE_KEYS},
          'dma_active_channels':[i for i in range(8) if e[f'dmaController.channel[{i}].dmaActive']],
          'hdma_unfinished_enabled_channels':[i for i in range(8)
             if e['dmaController.hdmaChannels']&(1<<i) and not e[f'dmaController.channel[{i}].hdmaFinished']]})
    context_counts=Counter(row['context_kind'] for row in trace['records'] if row['kind']=='interrupt-entry')
    return {'record_count':len(trace['records']),'event_counts':dict(sorted(Counter(row['kind'] for row in trace['records']).items())),
      'interrupt_entry_counts':dict(sorted(context_counts.items())),
      'engine_fields_per_record':summary['engine_field_count'],
      'cache_witness':summary['cache_witness'],'complete_v2_trace_equal':summary['complete_v2_trace_equal'],
      'resolver_to_tail_master_clocks':summary['legacy_summary']['resolver_to_tail_master_clocks'],
      'resolver_to_tail_cpu_counter':summary['legacy_summary']['resolver_to_tail_cpu_counter'],'phases':phase,
      'raw_cpu_stack_gate_arrays_emitted':False,'complete_dma_bus_trace':False,
      'future_dma_absence_proved':False,'interrupt_exclusion_proved':False,'deadline_certified':False,
      'native_helper_executed':False,'production_approval':False}

def verify_run(directory,observer,paths,sources,ledger,reference):
    require(not (directory/'host_rejection.json').exists() and not (directory/'trace.json.error.txt').exists(),'error marker refuses acceptance')
    ledger.inventory(directory)
    launch,launch_id,launch_raw=ledger.json(directory/'launch_inputs.json')
    manifest,manifest_id,manifest_raw=ledger.json(directory/'manifest.json')
    process,process_id,process_raw=ledger.json(directory/'process_receipt.json')
    process_contract(process,observer.SCHEMA)
    require(process_raw==serial(process),'canonical process receipt')
    require(set(launch)==RECEIPT_KEYS,'exact launch shape')
    hashes={key:row['sha256'] for key,row in sources.items()}
    archive_paths={key:directory/'source_archive'/(key+path.suffix) for key,path in paths.items()
        if key not in {*observer.context.PINNED,*observer.safe.RUNTIME_NAMES,'reference_trace'}}
    require(ledger.inventory(directory/'source_archive')==sorted(p.name for p in archive_paths.values()),'exact archive inventory')
    archives={key:ledger.file(path) for key,path in archive_paths.items()}
    require(all((r['size_bytes'],r['sha256'])==(sources[k]['size_bytes'],sources[k]['sha256']) for k,r in archives.items()),'archive byte identity')
    stage=directory/'staged';names=ledger.inventory(stage)
    rom_names=[n for n in names if re.fullmatch(r'pe_resolver_phase_v3_[0-9a-f]{24}\.sfc',n)]
    require(len(rom_names)==1,'one isolated ROM stem');stem=rom_names[0][:-4]
    require(names==sorted(['app','collector.lua',stem+'.sfc',stem+'.mss','profile','temp']),'exact stage inventory')
    staged_paths={key:stage/'app'/name for key,name in observer.safe.RUNTIME_NAMES.items()}
    staged_paths.update(rom=stage/(stem+'.sfc'),state=stage/(stem+'.mss'),sram=stage/'app/Saves'/(stem+'.srm'),collector=stage/'collector.lua')
    require(ledger.inventory(stage/'app/Saves')==[stem+'.srm'],'exact save inventory')
    staged={key:ledger.file(path) for key,path in staged_paths.items()}
    require(all((r['size_bytes'],r['sha256'])==(sources[k]['size_bytes'],sources[k]['sha256']) for k,r in staged.items()),'staged byte identity')
    receipt={'schema':observer.SCHEMA,'source_hashes':hashes,
      'staged_hashes':{key:r['sha256'] for key,r in staged.items()},
      'source_archive_hashes':{key:r['sha256'] for key,r in archives.items()},
      'source_archive_files':{key:p.name for key,p in archive_paths.items()},'guarded_settings':observer.GUARDED_SETTINGS}
    require(launch_raw==serial(receipt),'actual files must reproduce prelaunch receipt')
    trace,trace_id,_=ledger.json(directory/'trace.json',maximum=observer.MAX_TRACE)
    summary=observer.summarize(trace,reference)
    expected={**receipt,'evidence_level':'exploratory-runtime-not-accepted','observations':summary,
      'trace_sha256':trace_id['sha256'],'process_receipt_sha256':sha(process_raw),
      'sources_staged_archives_unchanged':True,'checkpoint_load_only':True,
      'controller_schedule_reused':True,'rom_cpu_memory_edits':False,'production_approval':False}
    require(manifest_raw==serial(expected),'manifest must reproduce fully revalidated evidence')
    log_id,log=ledger.file(directory/'process.log',maximum=32*1024*1024,allow_empty=True,retain=True)
    projection=compact(trace,summary)
    return {'directory':directory.relative_to(ROOT).as_posix(),'staged_stem':stem,
      'artifacts':{'launch_inputs':launch_id,'manifest':manifest_id,'process_receipt':process_id,'trace':trace_id,'process_log':log_id},
      'uninitialized_read_diagnostics':log.count(b'Uninitialized memory read'),
      'staged_identities':staged,'archived_identities':archives,
      'summary_sha256':sha(serial(summary)),'projection':projection}

def pair_contract(runs):
    # These are consistency/isolation checks, not an authenticated execution
    # log. Copying and rewriting unsigned receipts can fabricate a second run.
    # The two actual process invocations are separate operator/tool evidence.
    require(len(runs)==2 and runs[0]['staged_stem']!=runs[1]['staged_stem'],'two independent launch stems')
    require(runs[0]['artifacts']['trace']['sha256']==runs[1]['artifacts']['trace']['sha256'],'full trace pair mismatch')
    require(runs[0]['summary_sha256']==runs[1]['summary_sha256'] and runs[0]['projection']==runs[1]['projection'],'revalidated pair mismatch')

def audit_pair(first,second):
    run_root=files.direct_path(ROOT/'private/test_runs',directory=True)
    dirs=[files.direct_path(p,directory=True) for p in (first,second)]
    for d in dirs:require(d!=run_root and d.is_relative_to(run_root),'private run root required')
    require(dirs[0]!=dirs[1] and not os.path.samefile(*dirs),'distinct run roots')
    require(not dirs[0].is_relative_to(dirs[1]) and not dirs[1].is_relative_to(dirs[0]),'nested run roots')
    ledger=files.FileLedger();observer=observer_module(ledger)
    paths,sources=current_sources(observer,ledger);reference=observer.reference_records()
    runs=[verify_run(d,observer,paths,sources,ledger,reference) for d in dirs]
    for name in ('trace.json','manifest.json','launch_inputs.json','process_receipt.json'):
        require(not os.path.samefile(dirs[0]/name,dirs[1]/name),'aliased evidence file')
    pair_contract(runs)
    own=[ledger.file(ROOT/name) for name in ('tools/audit_package_resolver_phase_v3.py','tests/test_audit_package_resolver_phase_v3.py')]
    ledger.recheck()
    return {'schema':SCHEMA,'evidence_level':'verified-runtime',
      'evidence_scope':'exact repeated primary checkpoint; selected hardware snapshots, source-conditional cache crossing and watched bus domains only',
      'acceptance_source_identities':own,'file_guard_utility':ledger.file(ROOT/UTILITY_PIN[0]),
      'source_identities':sources,'runs':runs,'full_trace_bytes_identical':True,
      'native_process_exit_receipts_checked':True,'raw_game_data_emitted':False,
      'execution_authenticated_against_fabricated_receipts':False,
      'native_helper_executed':False,'deadline_certified':False,'production_approval':False,
      'reproduce':['python','-B','tools/audit_package_resolver_phase_v3.py','--run-a',runs[0]['directory'],'--run-b',runs[1]['directory']]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-a',type=Path,required=True);p.add_argument('--run-b',type=Path,required=True)
    args=p.parse_args()
    try:result=audit_pair(args.run_a,args.run_b)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('phase acceptance refused: '+str(exc),file=sys.stderr);return 1
    sys.stdout.buffer.write((json.dumps(result,indent=2,allow_nan=False)+'\n').encode());return 0

if __name__=='__main__':raise SystemExit(main())
