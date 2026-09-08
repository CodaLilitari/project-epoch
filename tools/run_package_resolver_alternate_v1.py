#!/usr/bin/env python3
"""Observe canonical Black Hole's alternate package path from a pinned checkpoint.

The checkpoint descends from a prepared diagnostic SRAM. After loading it,
only the fixed controller schedule changes emulation. No arbitrary input,
state, collector, memory injection, or ROM mutation option is exposed.
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

import audit_schala_player_tech_package_bank_adapter_v0 as adapter
import run_mesen_field_animation_probe_v0 as safe

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-package-resolver-alternate-v1'
COLLECTOR=ROOT/'tools/mesen_package_resolver_alternate_v1.lua'
PINNED={
    'rom':('private/input/rom_archive/Chrono Trigger (USA).sfc',4194304,'06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'),
    'sram':('private/tools/mesen2/app/Saves/project_epoch_mesen_event11c_clean.srm',8192,'a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9'),
    'state':('private/test_runs/mesen2/event11c_checkpoint_v5/spekkio_talkable.mss',133993,'26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e'),
}
EXEC_SITES={
    'black-hole-entry':0xC1F132,'black-hole-type-test':0xC1F139,
    'black-hole-rng-path':0xC1F13F,'black-hole-survivor':0xC1F156,
    'black-hole-mask-advance':0xC1F18B,'exhausted-mask-alternate-store':0xC1F1C0,
    'branch-producer-complete':0xC1409C,'resolver-entry':0xC14612,
    'canonical-continuation':0xC14616,'resolver-tail':0xC1467F,
    'common-loader-entry':0xC14833,'common-loader-rts':0xC148EB,
    'dispatcher-rts':0xC1432B,'caller-resume':0xC140B0,
    'caller-package-latch':0xC140CE,'caller-effect-latch':0xC140E7,
    'terminal-command-clear':0xC14CF3,'sync-command-increment':0xC14D00,
}
EVENT_KINDS={'baseline','menu-observation','terminal'}
MEMORY_KINDS={'publication-write','latch-write'}
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIMING_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount',
             'ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
WRAM_KEYS={f'{a:04X}' for a in (
    0x001A,0x001C,0x007E,0x007F,0x0080,0x0082,0x0100,0x0101,0x011F,0x0162,
    0x2980,0x2981,0x2982,0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,
    0xAE94,0xAE95,0xAE96,0xAE99,0xAE9A,0xAEFF,0xAF00,0xAF01,0xB1F6,0xB1F7,
    0xB1FD,0xA6D9,0xA6DA,0xA6DB,0x95D5,0x95DC)}
RECORD_KEYS={'kind','address','value','frame','cpu','stack','wram','timing','target_type',
             'selector_word','branch_word','mask0_word','mask1_word','root_word'}


class ObservationError(RuntimeError):
    pass


def canonical(value:Any)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def require(condition:bool,message:str)->None:
    if not condition:
        raise ObservationError(message)


def integer(value:Any,low:int,high:int,label:str)->int:
    require(type(value) is int and low<=value<=high,'invalid '+label)
    return value


def exact_object(value:Any,keys:set[str],label:str)->dict:
    require(isinstance(value,dict) and set(value)==keys,'invalid '+label+' keys')
    return value


def pc(r:dict)->int:
    return r['cpu']['k']<<16|r['cpu']['pc']


def word(r:dict,address:int)->int:
    return r['wram'][f'{address:04X}']|r['wram'][f'{address+1:04X}']<<8


def action(r:dict)->tuple[int,int,int]:
    return tuple(r['wram'][key] for key in ('AE91','AE92','AE93'))


def validate_record(r:Any)->None:
    exact_object(r,RECORD_KEYS,'record')
    kind=r['kind']
    require(isinstance(kind,str) and kind in set(EXEC_SITES)|EVENT_KINDS|MEMORY_KINDS,'unknown event kind')
    integer(r['address'],0,0xFFFFFF,'address')
    integer(r['frame'],0,4400,'relative input poll')
    c=exact_object(r['cpu'],CPU_KEYS,'CPU')
    for key in CPU_KEYS-{'emulationMode'}:
        integer(c[key],0,255 if key in {'ps','dbr','k'} else 65535,'CPU '+key)
    require(type(c['emulationMode']) is bool and not c['emulationMode'],'native CPU mode required')
    require(isinstance(r['stack'],list) and len(r['stack'])==12,'invalid twelve-byte stack snapshot')
    for value in r['stack']: integer(value,0,255,'stack byte')
    for key,value in exact_object(r['wram'],WRAM_KEYS,'WRAM').items(): integer(value,0,255,'WRAM '+key)
    for key in ('selector_word','branch_word','mask0_word','mask1_word','root_word'):
        integer(r[key],0,65535,key)
    for key,address in (('selector_word','9877'),('branch_word','A0B3'),('mask0_word','0080'),('mask1_word','0082')):
        require(r[key]&255==r['wram'][address],'word and byte snapshots disagree')
    integer(r['target_type'],-1,255,'target type')
    target=word(r,0xB1F6)
    require((r['target_type']!=-1)==(target<=0x500 and target%0x80==0),'target type validity disagrees with bounded target base')
    t=exact_object(r['timing'],TIMING_KEYS,'timing')
    for key,value in t.items(): integer(value,0,2**64-1,'timing '+key)
    require(t['masterClock']==t['memoryManager.masterClock']&0xFFFFFFFF,'generic masterClock differs from full clock low word')
    require(t['frameCount']==t['ppu.frameCount'],'frame counters disagree')
    require(t['clockRate']==21477270 and t['memoryManager.hClock']<=1364 and t['ppu.scanline']<=312,'invalid pinned NTSC timing')
    if kind in EXEC_SITES:
        require(r['address']==EXEC_SITES[kind]==pc(r),'exec address, kind, or PBR/PC mismatch')
    elif kind in EVENT_KINDS:
        require(r['address']==0,'event callback address must be zero')
        if kind=='menu-observation': require(r['frame'] in {2100,2680,3000},'unknown menu observation poll')
    elif kind=='publication-write':
        require(0x7E5DAC<=r['address']<=0x7E5DFC,'publication address outside callback range')
    else:
        require(r['address'] in {0x7E9876,0x7E5D9B,0x7EAE94},'unknown latch write address')
    if kind in MEMORY_KINDS: integer(r['value'],0,255,'memory write value')
    else: require(type(r['value']) is int and r['value']==-1,'event sentinel value required')


def canonical_model(rom:bytes)->adapter.DescriptorInstallState:
    """Privately derive the expected canonical selector-37 alternate publications."""
    sources=adapter.build_canonical_sources(rom)
    return adapter.simulate_descriptor_install(rom[0x0E0000:0x0F0000],sources[0x37],a0b3=0x40)


def publication_sequence(model:adapter.DescriptorInstallState)->list[tuple[int,int,int]]:
    result=[]
    for pub in model.publications:
        for address,value,next_pc in (
            (pub.activation_address,pub.activation_word,0xC14653),
            (pub.script_address,pub.script_offset,0xC1465F),
            (pub.bank_address,pub.bank_word,0xC14665),
        ):
            result.extend([(0x7E0000|address,value&255,next_pc),(0x7E0000|address+1,value>>8,next_pc)])
    return result


def summarize(trace:dict,model:adapter.DescriptorInstallState)->dict:
    """Validate one fixed replay against a separately derived descriptor model.

    Callers of this pure validator supply the model. The launcher constructs it
    only from the pinned canonical ROM. Unit tests use original synthetic data.
    """
    exact_object(trace,{'schema','error','records'},'trace')
    require(trace['schema']==SCHEMA and trace['error'] is None,'collector schema or execution failure')
    records=trace['records']
    require(isinstance(records,list) and 2<=len(records)<=16384,'invalid bounded record list')
    for r in records: validate_record(r)
    counts=Counter(r['kind'] for r in records)
    require(counts['baseline']==counts['terminal']==1,'missing or duplicate baseline/terminal')
    require(records[0]['kind']=='baseline' and records[0]['frame']==0 and records[-1]['kind']=='terminal' and records[-1]['frame']==4400,'incorrect baseline/terminal boundary')
    require(word(records[0],0x0100)==0x1D1 and [records[0]['wram'][k] for k in ('2980','2981','2982')]==[6,4,3],'wrong prepared Spekkio checkpoint')
    previous=(-1,-1,-1,-1)
    for r in records:
        current=(r['frame'],r['timing']['memoryManager.masterClock'],r['timing']['cpu.cycleCount'],r['timing']['ppu.frameCount'])
        require(all(a>=b for a,b in zip(current,previous)),'nonmonotonic poll, full clock, CPU cycles, or video frames')
        previous=current
    require(counts['resolver-entry']==counts['resolver-tail']==counts['canonical-continuation']==1,'exactly one canonical resolver invocation required')
    entry_index=next(i for i,r in enumerate(records) if r['kind']=='resolver-entry')
    entry=records[entry_index]; c=entry['cpu']; sp=c['sp']
    require(action(entry)==(0,2,0x37) and entry['selector_word']==0x37 and entry['branch_word']==0x40,'wrong fixed alternate action or package selector')
    require([entry['wram'][k] for k in ('AEFF','AF00','AF01')]==[6,4,3],'battle logical identity does not match prepared party')
    require(c['d']==0 and c['dbr']==0x7E and c['ps']&0x30==0,'resolver entry ABI mismatch')
    require(entry['stack'][:4]==[0x2A,0x43,0xAF,0x40],'resolver near-call frames differ')
    require(entry['wram']['AE94']==0x40 and entry['wram']['9876']==0,'resolver entered with wrong action flags')
    producer_index=max((i for i in range(entry_index) if records[i]['kind']=='branch-producer-complete'),default=-1)
    require(producer_index>=0,'missing preceding branch producer')
    producer=records[producer_index]
    require(action(producer)==action(entry) and producer['branch_word']==0x40 and producer['wram']['AE94']==0x40,'preceding producer belongs to another action or branch')
    earlier_producer=max((i for i in range(producer_index) if records[i]['kind']=='branch-producer-complete'),default=0)
    start=max((i for i in range(earlier_producer+1,producer_index) if records[i]['kind']=='black-hole-entry'),default=-1)
    require(start>=0,'missing same-action Black Hole effect entry')
    effect=records[start:producer_index]
    stages=['black-hole-entry','black-hole-type-test','black-hole-survivor','black-hole-mask-advance','exhausted-mask-alternate-store']
    observed=[r['kind'] for r in effect if r['kind'].startswith('black-hole-') or r['kind']=='exhausted-mask-alternate-store']
    require(observed==stages,'boss-immunity producer path missing, reordered, repeated, or entered RNG')
    type_test=next(r for r in effect if r['kind']=='black-hole-type-test')
    survivor=next(r for r in effect if r['kind']=='black-hole-survivor')
    advance=next(r for r in effect if r['kind']=='black-hole-mask-advance')
    store=next(r for r in effect if r['kind']=='exhausted-mask-alternate-store')
    target_slot=type_test['wram']['B1FD']; target_base=word(type_test,0xB1F6)
    require(3<=target_slot<=10 and target_base==target_slot*0x80,'target slot/base mismatch')
    require(type_test['target_type']&0x80!=0 and type_test['cpu']['a']&255==type_test['target_type'],'boss type test is not supported by the target-byte read')
    require(type_test['cpu']['x']==target_base and type_test['cpu']['ps']&0x30==0x20,'boss type test addressing or width mismatch')
    require(all(word(r,0xB1F6)==target_base and r['wram']['B1FD']==target_slot and r['target_type']==type_test['target_type']
                and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E for r in effect),'effect target, direct page, or bank changed')
    require(word(survivor,0xAE95)|word(survivor,0xAE99)==0x8000>>target_slot,'unexpected initial single-target result mask')
    require(word(advance,0xAE95)==word(advance,0xAE99)==0,'survivor did not exhaust both result masks')
    require(all(r['wram']['AE91']==0 and r['wram']['AE92']==2 and r['wram']['AEFF']==6 for r in effect),'Black Hole producer action identity drift')
    require(store['cpu']['a']&255==0x40 and store['cpu']['ps']&0x30==0x20 and store['wram']['AE94']==0,'pre-STA alternate flag state mismatch')
    store_index=records.index(store,start,producer_index)
    writes=[(i,r) for i,r in enumerate(records[store_index+1:producer_index],store_index+1) if r['kind']=='latch-write' and r['address']==0x7EAE94]
    require(len(writes)==1,'missing or ambiguous actual alternate flag write')
    flag_index,flag=writes[0]
    require(flag['value']==0x40 and pc(flag)==0xC1F1C3 and flag['cpu']['ps']&0x30==0x20 and flag['cpu']['dbr']==0x7E,'actual flag write does not execute canonical STA')
    require(flag['wram']['AE94']==0 and action(flag)[:2]==(0,2),'write callback was confused with post-write state or another actor')
    # The following producer snapshot is the readback witness, not the pre-write callback.
    require(producer['wram']['AE94']==flag['value'],'alternate flag lacks post-write readback')
    end=next((i for i in range(entry_index+1,len(records))
              if records[i]['kind'] in {'branch-producer-complete','resolver-entry','terminal'}
              or action(records[i])!=action(entry)),len(records))
    tail_index=next((i for i in range(entry_index+1,end) if records[i]['kind']=='resolver-tail'),-1)
    require(tail_index>=0,'resolver tail missing before action identity changed')
    tail=records[tail_index]
    continuation=next((r for r in records[entry_index+1:tail_index] if r['kind']=='canonical-continuation'),None)
    require(continuation is not None,'canonical continuation missing before tail')
    require(continuation['cpu']['a']==0x6E and continuation['cpu']['ps']&0x30==0 and continuation['cpu']['sp']==sp,'canonical selector shift continuation mismatch')
    pubs=[r for r in records[entry_index+1:tail_index] if r['kind']=='publication-write']
    expected=publication_sequence(model)
    require([(r['address'],r['value'],pc(r)) for r in pubs]==expected,'ordered publication bytes or canonical store sites differ from ROM-derived model')
    require(counts['publication-write']==len(pubs),'publication callback outside the single resolver interval')
    require(all(r['cpu']['ps']&0x30==0 and r['cpu']['dbr']==0x7E and r['cpu']['d']==0 for r in pubs),'publication width, bank, or direct page mismatch')
    t=tail['cpu']
    require((t['a'],t['x'],t['y'],t['d'],t['dbr'],t['sp'])==(model.accumulator_word_final,model.x_final,model.y_final,model.direct_page_final,model.data_bank_final,sp),'resolver tail CPU differs from host model')
    require(t['ps']==((c['ps']&0x4C)|0x23) and tail['stack']==entry['stack'],'resolver tail flags or preserved stack mismatch')
    require((tail['root_word'],tail['mask0_word'],tail['mask1_word'],tail['branch_word'])==(model.descriptor_root_word,model.dp80_word_final,model.dp82_word_final,model.a0b3_final),'resolver tail descriptor state mismatch')
    chain=[]; cursor=tail_index
    for kind,delta in [('resolver-tail',0),('common-loader-entry',0),('common-loader-rts',0),('dispatcher-rts',2),('caller-resume',4)]:
        index=next((i for i in range(cursor,end) if records[i]['kind']==kind),-1)
        require(index>=0,'missing ordered resolver return stage: '+kind)
        r=records[index]; cursor=index+1
        require(r['cpu']['sp']==sp+delta and r['cpu']['ps']&0x30==0x20 and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E,'return chain ABI mismatch: '+kind)
        require(r['stack'][:12-delta]==entry['stack'][delta:],'return chain stack consumption mismatch: '+kind)
        chain.append({'kind':kind,'record_index':index,'poll':r['frame'],'sp':r['cpu']['sp']})
    sync_index=next((i for i in range(cursor,end) if records[i]['kind']=='sync-command-increment'),-1)
    require(sync_index>=0,'missing PC-scoped package synchronization command')
    sync_write=next((i for i in range(sync_index+1,end) if records[i]['kind']=='latch-write' and records[i]['address']==0x7E9876 and records[i]['value']==1),-1)
    require(sync_write>=0 and pc(records[sync_write])==0xC14D03,'missing actual canonical synchronization write')
    package_read=next((i for i in range(sync_write+1,end) if records[i]['kind']=='caller-package-latch' and records[i]['wram']['9876']!=0),-1)
    require(package_read>=0,'missing PC-scoped package-completion readback')
    effect_read=next((i for i in range(package_read+1,end) if records[i]['kind']=='caller-effect-latch' and records[i]['wram']['5D9B']==0),-1)
    require(effect_read>=0,'missing same-action effect-completion read after package read')
    require(records[package_read]['cpu']['sp']==records[effect_read]['cpu']['sp']==sp+4,'completion reads use another call frame')
    for index in (sync_index,sync_write,package_read,effect_read):
        cpu=records[index]['cpu']
        require(cpu['d']==0 and cpu['dbr']==0x7E and cpu['ps']&0x30==0x20,
                'synchronization or completion read ABI mismatch')
    duration=tail['timing']['memoryManager.masterClock']-entry['timing']['memoryManager.masterClock']
    return {
        'record_count':len(records),'event_counts':dict(sorted(counts.items())),
        'canonical_selector':0x37,'action_config':0x37,'actor_slot':0,'logical_pc_id':6,'branch_word_at_entry':0x40,
        'entry_abi_verified':True,'entry_sp':sp,'entry_poll':entry['frame'],'entry_record_index':entry_index,
        'preflight_cancellation_tested':False,'boss_immunity_bypasses_rng':True,
        'target_slot':target_slot,'target_type_boss_bit_set':True,'both_result_masks_exhausted':True,
        'alternate_flag_witness':{'pre_store_index':store_index,'actual_write_index':flag_index,'readback_producer_index':producer_index,
                                  'pre_store_poll':store['frame'],'producer_poll':producer['frame']},
        'host_model_publication_comparison':True,'publication_byte_count':len(pubs),
        'published_owner_slots':[p.owner_slot for p in model.publications],
        'tail_cpu_stack_and_descriptor_match':True,'return_chain':chain,
        'pc_observation_window_end_index':end,'pc_observation_window_end_poll':records[end]['frame'] if end<len(records) else None,
        'completion':{'sync_command_index':sync_index,'sync_write_index':sync_write,'package_read_index':package_read,'effect_read_index':effect_read,
                      'package_read_poll':records[package_read]['frame'],'effect_read_poll':records[effect_read]['frame']},
        'resolver_entry_to_pre_jmp_tail':{'master_clocks':duration,'cpu_cycle_counter_increment':tail['timing']['cpu.cycleCount']-entry['timing']['cpu.cycleCount'],
                                        'video_frame_increment':tail['timing']['ppu.frameCount']-entry['timing']['ppu.frameCount'],
                                        'end_record_index':tail_index,'interrupt_attribution':'not collected'},
    }


def run(output_dir:Path)->dict[str,Any]:
    private=safe.canonical_private_root(); inputs={}
    for key,(relative,size,sha) in PINNED.items():
        path=safe.resolve_private_file(ROOT/relative,key,private_root=private)
        require(path.stat().st_size==size and safe.sha256_file(path)==sha,'pinned '+key+' identity mismatch')
        inputs[key]=path
    model=canonical_model(inputs['rom'].read_bytes())
    runtime={key:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/name,key,private_root=private) for key,name in safe.RUNTIME_NAMES.items()}
    for key,path in runtime.items(): safe.require_identity(path,key)
    output=safe.prepare_private_output_dir(output_dir,private_root=private,forbidden_roots=tuple(p.parent for p in inputs.values())+(safe.DEFAULT_MESEN.parent,))
    guarded={**inputs,**runtime,'collector':COLLECTOR,'launcher':Path(__file__),'isolation_library':Path(safe.__file__),'descriptor_model':Path(adapter.__file__)}
    before={key:safe.sha256_file(path) for key,path in guarded.items()}
    stage=output/'staged'; app=stage/'app'; saves=app/'Saves'; saves.mkdir(parents=True)
    staged={}
    for key,name in safe.RUNTIME_NAMES.items():
        staged[key]=app/name; safe.copy_new_regular_file(runtime[key],staged[key],key)
    stem='pe_alternate_'+secrets.token_hex(12)
    for key,path in inputs.items():
        dest=saves/(stem+'.srm') if key=='sram' else stage/(stem+('.sfc' if key=='rom' else '.mss'))
        safe.copy_new_regular_file(path,dest,key); staged[key]=dest
    staged['collector']=stage/'collector.lua'; safe.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    staged_before={key:safe.sha256_file(path) for key,path in staged.items()}
    require(all(staged_before[key]==before[key] for key in staged),'staged copy differs from source')
    env=safe.minimal_subprocess_environment()
    for key,parts in {'USERPROFILE':('profile',),'APPDATA':('profile','AppData','Roaming'),'LOCALAPPDATA':('profile','AppData','Local'),'TEMP':('temp',),'TMP':('temp',)}.items():
        path=stage.joinpath(*parts); path.mkdir(parents=True,exist_ok=True); env[key]=str(path)
    env.update(PE_RESOLVER_PROTOCOL=SCHEMA,PE_RESOLVER_STATE=str(staged['state']),PE_RESOLVER_TRACE=str(output/'trace.json'),PE_ALTERNATE_OUTPUT=str(output))
    command=[str(staged['mesen']),'--testRunner','--timeout=60','--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true',
             '--snes.ramPowerOnState=AllZeros','--snes.port1.type=SnesController',str(staged['collector']),str(staged['rom'])]
    prepared={'schema':SCHEMA,'status':'prepared-only-not-executed','source_hashes':before,'staged_hashes':staged_before,
              'checkpoint_basis':'byte-exact imported external SRAM; previously captured diagnostic state; controller-only after load',
              'rom_mutation_authorized':False,'memory_or_cpu_injection_after_load_authorized':False}
    (output/'launch_inputs.json').write_bytes(canonical(prepared))
    error=None; proc=None
    try:
        proc=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=75,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=False)
        (output/'process.log').write_bytes(proc.stdout+proc.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:
        error=str(exc)
    safe.require_file_hashes_unchanged(guarded,before,'source')
    safe.require_file_hashes_unchanged(staged,staged_before,'staged input')
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged['sram'].name)
    require(not error and proc is not None and proc.returncode==51,f'isolated observation failed: {error or (proc.returncode if proc else None)}; retained {output}')
    trace_path=output/'trace.json'
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,'trace',parent=output,maximum=32*1024*1024),'trace')
    screenshots={}
    for poll in (2100,2680,3000):
        path=output/f'menu_{poll}.png'
        data=safe.read_direct_regular_file(path,'screenshot',parent=output,maximum=4*1024*1024)
        screenshots[path.name]={'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    result={'schema':SCHEMA,'evidence_level':'exploratory-runtime-not-accepted',
            'evidence_scope':'checkpoint-bounded canonical alternate resolver; no helper installed',
            'checkpoint_basis':'byte-exact imported external SRAM; previously captured diagnostic state; controller-only after load',
            'source_hashes':before,'staged_hashes':staged_before,'trace_sha256':safe.sha256_file(trace_path),
            'observations':summarize(trace,model),'screenshots':screenshots,
            'sources_and_staged_inputs_unchanged':True,'rom_mutated':False,'memory_or_cpu_injection_after_load':False,
            'helper_installed':False,'production_approval':False,
            'reproduce':['python','-B','tools/run_package_resolver_alternate_v1.py','--output-dir','private/test_runs/resolver_alternate_NEW']}
    (output/'manifest.json').write_bytes(canonical(result))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(run(args.output_dir),indent=2))
