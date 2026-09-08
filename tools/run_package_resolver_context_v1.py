#!/usr/bin/env python3
"""Observe ordinary resolver and interrupt context on an isolated clean-ROM state.

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
SCHEMA="project-epoch-package-resolver-context-v1"
COLLECTOR=ROOT/"tools/mesen_package_resolver_context_v1.lua"
PINNED={
    "rom":("private/input/rom_archive/Chrono Trigger (USA).sfc",4194304,"06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"),
    "sram":("private/input/lavos_save/chrono_trigger.srm",8192,"cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203"),
    "state":("private/test_runs/mesen2/lavos_battle_checkpoint_accepted_v17/battle_ready.mss",261614,"d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b"),
}

class ObservationError(RuntimeError):
    pass

def canonical(value:Any)->bytes:
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()

EXEC_SITES={
    'branch-producer-complete':{0xC1409C},'resolver-entry':{0xC14612},
    'canonical-continuation':{0xC14616},'resolver-tail':{0xC1467F},
    'common-loader-entry':{0xC14833},'common-loader-rts':{0xC148EB},
    'dispatcher-rts':{0xC1432B},'caller-resume':{0xC140B0},
    'caller-package-latch':{0xC140CE},'caller-effect-latch':{0xC140E7},
    'terminal-command-clear':{0xC14CF3},'sync-command-increment':{0xC14D00},
    'nmi-effect-latch-read':{0xCD160E},'nmi-effect-latch-clear':{0xCD164D},
    'nmi-mode-dispatch':{0xCD0C99},'nmi-scene-dispatch':{0xCD16AF},
    'irq-display-stack-lowpoint':{0xCEEEAE},
    'special-result-alternate-store':{0xC1E922,0xC1E951},
    'exhausted-mask-alternate-store':{0xC1F1C0},
}
INTERRUPT_ENTRIES={0xD1E77C:'normal-nmi',0xD1FE97:'battle-irq',0xD1F4C0:'alternate-nmi'}
INTERRUPT_EXITS={0xD1E898:'normal-nmi',0xD1FEF3:'battle-irq',0xD1F558:'alternate-nmi'}
TIMING_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount',
             'ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
WRAM_KEYS={'007C','007D','007E','007F','0080','0082','5D9B','9876','9877','A0B3',
           'AE91','AE92','AE93','AE94','95D5','95DC','06E2','06E6','06E7','A43F',
           '2980','2981','2982','CD01','CD02'}
RECORD_KEYS={'kind','address','value','poll','cpu','stack','wram','timing','trampolines',
             'context_id','context_kind','context_depth','resolver_active','action_active',
             'selector_word','branch_word','mask0_word','mask1_word','root_word'}
EVENT_KINDS={'baseline','terminal','menu-observation'}
MEMORY_KINDS={'temporary-read','temporary-write','publication-write','latch-or-flag-write'}


def _integer(value:Any,low:int,high:int,label:str)->int:
    if type(value) is not int or not low<=value<=high:
        raise ObservationError(f'invalid {label}')
    return value


def _exact_object(value:Any,keys:set[str],label:str)->dict:
    if not isinstance(value,dict) or set(value)!=keys:
        raise ObservationError(f'invalid {label} keys')
    return value


def _validate_record(r:Any,index:int)->None:
    _exact_object(r,RECORD_KEYS,f'record {index}')
    kind=r['kind']
    if not isinstance(kind,str) or kind not in set(EXEC_SITES)|EVENT_KINDS|MEMORY_KINDS|{'interrupt-entry','interrupt-rti'}:
        raise ObservationError('unknown event kind')
    _integer(r['address'],0,0xFFFFFF,'event address')
    _integer(r['poll'],0,1200,'poll')
    _integer(r['context_id'],0,32768,'context id')
    _integer(r['context_depth'],0,32768,'context depth')
    if not isinstance(r['context_kind'],str) or r['context_kind'] not in {'main',*INTERRUPT_ENTRIES.values()}:
        raise ObservationError('unknown context kind')
    for name in ('resolver_active','action_active'):
        if type(r[name]) is not bool:
            raise ObservationError(f'invalid {name}')
    cpu=_exact_object(r['cpu'],CPU_KEYS,'CPU')
    for name in CPU_KEYS-{'emulationMode'}:
        _integer(cpu[name],0,0xFF if name in {'dbr','ps','k'} else 0xFFFF,f'CPU {name}')
    if type(cpu['emulationMode']) is not bool or cpu['emulationMode']:
        raise ObservationError('native CPU mode required for four-byte hardware frame')
    for name,size in (('stack',12),('trampolines',8)):
        if not isinstance(r[name],list) or len(r[name])!=size:
            raise ObservationError(f'invalid {name} length')
        for v in r[name]: _integer(v,0,255,name+' byte')
    tramp=r['trampolines']
    if tramp[0]!=0x5C or tramp[4]!=0x5C or int.from_bytes(bytes(tramp[1:4]),'little') not in {0xD1E77C,0xD1F4C0} or int.from_bytes(bytes(tramp[5:8]),'little')!=0xD1FE97:
        raise ObservationError('unexpected interrupt trampoline targets')
    wram=_exact_object(r['wram'],WRAM_KEYS,'WRAM snapshot')
    for name,v in wram.items(): _integer(v,0,255,'WRAM '+name)
    for name in ('selector_word','branch_word','mask0_word','mask1_word','root_word'):
        _integer(r[name],0,65535,name)
    for name,byte in (('selector_word','9877'),('branch_word','A0B3'),('mask0_word','0080'),('mask1_word','0082')):
        if r[name]&255!=wram[byte]:
            raise ObservationError('inconsistent word and byte snapshot')
    timing=_exact_object(r['timing'],TIMING_KEYS,'timing')
    for name,v in timing.items(): _integer(v,0,2**64-1,'timing '+name)
    if timing['masterClock']!=(timing['memoryManager.masterClock']&0xFFFFFFFF):
        raise ObservationError('generic masterClock is not low 32 bits of full clock')
    if timing['clockRate']!=21477270 or timing['memoryManager.hClock']>1364 or timing['ppu.scanline']>312:
        raise ObservationError('invalid pinned SNES clock or raster value')
    if timing['frameCount']!=timing['ppu.frameCount']:
        raise ObservationError('inconsistent frame counters')
    address=r['address']; pc=(cpu['k']<<16)|cpu['pc']
    if kind in EXEC_SITES:
        if address not in EXEC_SITES[kind] or pc!=address:
            raise ObservationError('exec address or CPU PBR/PC mismatch')
    elif kind in {'interrupt-entry','interrupt-rti'}:
        table=INTERRUPT_ENTRIES if kind=='interrupt-entry' else INTERRUPT_EXITS
        if address not in table or r['context_kind']!=table[address] or pc!=address:
            raise ObservationError('interrupt address, kind, or CPU PBR/PC mismatch')
        if kind=='interrupt-entry':
            offset=4 if r['context_kind']=='battle-irq' else 0
            if int.from_bytes(bytes(tramp[offset+1:offset+4]),'little')!=address:
                raise ObservationError('interrupt entry disagrees with trampoline')
            saved_p=r['stack'][0]
            if cpu['ps']!=((saved_p&~0x08)|0x04):
                raise ObservationError('entry P disagrees with native interrupt hardware frame')
            # Do not require saved I=0 for IRQ. Mesen samples PrevIrqSource on
            # an earlier cycle; a pending IRQ can be serviced after SEI changes
            # the stacked status. Report observed saved-I values instead.
    elif kind in EVENT_KINDS:
        if address!=0:
            raise ObservationError('event callback must have zero address')
        if kind=='menu-observation' and r['poll'] not in {40,80,120,160}:
            raise ObservationError('unexpected menu observation poll')
    elif kind.startswith('temporary-'):
        if not (0x80<=address<=0x83 or 0x4000<=address<=0x407F):
            raise ObservationError('temporary callback outside physical WRAM range')
    elif kind=='publication-write':
        if not 0x7E5DAC<=address<=0x7E5DFC:
            raise ObservationError('publication outside observed range')
    elif address not in {0x7E9876,0x7E5D9B,0x7EAE94}:
        raise ObservationError('unexpected latch or flag write address')
    if kind in MEMORY_KINDS:
        _integer(r['value'],0,255,'memory callback value')
    elif type(r['value']) is not int or r['value']!=-1:
        raise ObservationError('exec/event callback must use sentinel value')


def summarize(trace:dict[str,Any])->dict[str,Any]:
    _exact_object(trace,{'schema','error','records'},'trace')
    if trace['schema']!=SCHEMA or trace['error'] is not None:
        raise ObservationError("collector schema or execution failure")
    records=trace['records']
    if not isinstance(records,list) or not 2<=len(records)<=32768:
        raise ObservationError("invalid observation record count")
    for i,r in enumerate(records): _validate_record(r,i)
    if records[0]['kind']!='baseline' or records[-1]['kind']!='terminal' or records[0]['poll']!=0 or records[-1]['poll']!=1200:
        raise ObservationError("missing baseline/terminal")
    if sum(r['kind']=='baseline' for r in records)!=1 or sum(r['kind']=='terminal' for r in records)!=1:
        raise ObservationError('duplicate baseline/terminal')
    pairs=[]; live=[]; invocations=[]; context_ids=set(); invocation_ids=[]
    resolver=None; current_invocation=None; action_active=False; pending_clears={}; clear_witnesses=[]
    last_clock=-1; last_poll=-1; last_cycles=-1; last_frame=-1
    for index,r in enumerate(records):
        kind=r['kind']; full_clock=r['timing']['memoryManager.masterClock']
        cycles=r['timing']['cpu.cycleCount']; frame=r['timing']['ppu.frameCount']
        if full_clock<last_clock or r['poll']<last_poll or cycles<last_cycles or frame<last_frame:
            raise ObservationError('clock, CPU cycles, frame count, or poll moved backward')
        last_clock=full_clock; last_poll=r['poll']; last_cycles=cycles; last_frame=frame
        if kind=='branch-producer-complete':
            if resolver is not None:
                raise ObservationError('next action begins before resolver tail')
            if current_invocation is not None:
                invocations[current_invocation-1]['window_end_index']=index
                invocations[current_invocation-1]['window_end_kind']=kind
            current_invocation=None; action_active=False
        if kind=='resolver-entry':
            if resolver is not None or current_invocation is not None or r['context_kind']!='main':
                raise ObservationError('nested or unscoped PC resolver entry')
            if not (r['wram']['AE91']<3 and r['wram']['AE92']==2 and r['selector_word']<=0x7F and r['branch_word'] in {0,0x40}):
                raise ObservationError('unexpected ordinary PC resolver inputs')
            if r['cpu']['ps']&0x30 or r['cpu']['d']!=0 or r['cpu']['dbr']!=0x7E:
                raise ObservationError('unexpected ordinary resolver entry ABI')
            current_invocation=len(invocations)+1; action_active=True; resolver=r
            invocations.append({'id':current_invocation,'entry_index':index,'entry_poll':r['poll'],
                'selector_word':r['selector_word'],'branch_word':r['branch_word'],
                'entry_clock':full_clock,'entry_cpu_cycles':r['timing']['cpu.cycleCount'],
                'tail_index':None,'window_end_index':len(records)-1,'window_end_kind':'terminal',
                'direct_page_positive_control_count':0})
        if r['resolver_active']!=(resolver is not None) or r['action_active']!=action_active:
            raise ObservationError('collector resolver/action state mismatch')
        invocation_ids.append(current_invocation)
        if kind=='interrupt-entry':
            if r['context_id'] in context_ids or r['context_id']<=0 or r['context_id']!=len(context_ids)+1:
                raise ObservationError("duplicate/invalid interrupt identity")
            context_ids.add(r['context_id']); live.append((index,r))
        if live:
            if r['context_id']!=live[-1][1]['context_id'] or r['context_depth']!=len(live) or r['context_kind']!=live[-1][1]['context_kind']:
                raise ObservationError("interrupt context mismatch")
        elif r['context_id']!=0 or r['context_depth']!=0 or r['context_kind']!='main':
            raise ObservationError("unowned interrupt context")
        if kind=='nmi-effect-latch-clear':
            if r['context_kind'] not in {'normal-nmi','alternate-nmi'} or r['context_id'] in pending_clears or not r['wram']['5D9B'] or not r['cpu']['ps']&0x20:
                raise ObservationError('invalid pre-STZ scene-clear context')
            pending_clears[r['context_id']]={'exec_index':index,'write_index':None,
                'context_id':r['context_id'],'context_kind':r['context_kind'],
                'poll':r['poll'],'pc_invocation_id':current_invocation}
        if kind=='latch-or-flag-write' and r['address']==0x7E5D9B and r['context_id'] in pending_clears:
            witness=pending_clears[r['context_id']]
            if witness['write_index'] is not None or r['value']!=0 or ((r['cpu']['k']<<16)|r['cpu']['pc'])!=0xCD1650:
                raise ObservationError('scene clear did not produce expected byte write')
            witness['write_index']=index
        if kind=='interrupt-rti':
            if not live:
                raise ObservationError("unpaired interrupt RTI")
            entry_index,entry=live.pop()
            regs=('a','x','y','d','dbr','sp','emulationMode')
            if not all(entry['cpu'][k]==r['cpu'][k] for k in regs):
                raise ObservationError('interrupt changed preserved register or stack state')
            if entry['stack'][:4]!=r['stack'][:4]:
                raise ObservationError('interrupt changed native hardware return frame')
            pairs.append({'kind':entry['context_kind'],'context_id':entry['context_id'],
                'entry_index':entry_index,'return_index':index,
                'entry_poll':entry['poll'],'return_poll':r['poll'],
                'entry_sp':entry['cpu']['sp'],'return_sp':r['cpu']['sp'],
                'saved_interrupt_disable':bool(entry['stack'][0]&0x04),
                'resolver_active_at_entry':entry['resolver_active'],
                'action_active_at_entry':entry['action_active']})
            if r['context_id'] in pending_clears:
                witness=pending_clears.pop(r['context_id'])
                if witness['write_index'] is None or r['wram']['5D9B']!=0 or full_clock<=records[witness['write_index']]['timing']['memoryManager.masterClock']:
                    raise ObservationError('missing scene clear write/post-write readback')
                witness['rti_readback_index']=index; clear_witnesses.append(witness)
        if kind.startswith('temporary-'):
            if not (r['resolver_active'] or (r['action_active'] and r['context_depth']>0)):
                raise ObservationError('temporary callback outside declared observation window')
            # Canonical STA dp $81 at C1:4627 reports its physical WRAM write
            # with PC C1:4629. This proves the low-bank mirror callback fires.
            if kind=='temporary-write' and r['address']==0x81 and ((r['cpu']['k']<<16)|r['cpu']['pc'])==0xC14629 and r['context_kind']=='main' and r['resolver_active'] and r['cpu']['d']==0 and r['cpu']['ps']&0x20 and r['value']==(r['cpu']['a']&255):
                invocations[current_invocation-1]['direct_page_positive_control_count']+=1
        if kind=='publication-write' and not r['resolver_active']:
            raise ObservationError('publication outside resolver window')
        if kind=='resolver-tail':
            if resolver is None or r['context_kind']!='main':
                raise ObservationError('unpaired resolver tail')
            invocation=invocations[current_invocation-1]
            invocation.update(tail_index=index,tail_poll=r['poll'],
                entry_to_pre_jump_tail_master_clocks=full_clock-invocation['entry_clock'],
                entry_to_pre_jump_tail_cpu_cycles=r['timing']['cpu.cycleCount']-invocation['entry_cpu_cycles'])
            if invocation['entry_to_pre_jump_tail_master_clocks']<=0 or invocation['entry_to_pre_jump_tail_cpu_cycles']<=0:
                raise ObservationError('invalid resolver entry-to-tail duration')
            resolver=None
    if live or pending_clears or resolver is not None:
        raise ObservationError('incomplete interrupt, scene-clear, or resolver pair at terminal')
    if not pairs or not invocations or not clear_witnesses:
        raise ObservationError('missing required interrupt/resolver/scene-clear observation')
    for invocation in invocations:
        if invocation['tail_index'] is None or not invocation['direct_page_positive_control_count']:
            raise ObservationError('missing resolver tail or direct-page positive control')
    for witness in clear_witnesses:
        witness['caller_zero_read_index']=None
        invocation_id=witness['pc_invocation_id']
        if invocation_id is not None:
            end=invocations[invocation_id-1]['window_end_index']
            for i in range(witness['rti_readback_index']+1,end):
                candidate=records[i]
                if candidate['kind']=='caller-effect-latch' and candidate['context_kind']=='main' and candidate['wram']['5D9B']==0 and invocation_ids[i]==invocation_id:
                    witness['caller_zero_read_index']=i; break
            if witness['caller_zero_read_index'] is None:
                raise ObservationError('missing same-PC caller zero-latch read')
    pc_clears=[w for w in clear_witnesses if w['pc_invocation_id'] is not None]
    if not pc_clears:
        raise ObservationError('no scene-clear witness belongs to a captured PC invocation')
    temporary=[r for r in records if r['kind'].startswith('temporary-')]
    return {'record_count':len(records),'event_counts':dict(sorted(Counter(r['kind'] for r in records).items())),
        'resolver_invocations':len(invocations),'observed_branch_words':sorted({r['branch_word'] for r in invocations}),
        'resolver_entry_contexts':['main'],'pc_invocation_windows':invocations,
        'paired_interrupt_count':len(pairs),
        'paired_interrupt_kind_counts':dict(sorted(Counter(p['kind'] for p in pairs).items())),
        'irq_saved_interrupt_disable_counts':dict(sorted(Counter(str(int(p['saved_interrupt_disable'])) for p in pairs if p['kind']=='battle-irq').items())),
        'paired_interrupts_entered_during_resolver':sum(p['resolver_active_at_entry'] for p in pairs),
        'paired_interrupts_entered_during_action_epoch':sum(p['action_active_at_entry'] for p in pairs),
        'minimum_observed_entry_sp':min((p['entry_sp'] for p in pairs),default=None),
        'minimum_sampled_handler_sp':min(r['cpu']['sp'] for r in records if r['context_depth']>0),
        'stack_sampling_scope':'minimum across recorded handler snapshots only; not a complete stack low-water measurement',
        'maximum_observed_context_depth':max(r['context_depth'] for r in records),
        'open_interrupt_ids_at_terminal':[],
        'paired_interrupt_registers_preserved':True,
        'paired_interrupt_hardware_frames_unchanged':True,
        'interrupt_preservation_scope':'A/X/Y/D/DBR/SP and native four-byte hardware return frame; live P at pre-RTI is not expected to equal entry P',
        'temporary_access_counts':dict(sorted(Counter(r['context_kind']+':'+r['kind'] for r in temporary).items())),
        'timing_keys':sorted(TIMING_KEYS),'master_clock_basis':'memoryManager.masterClock full counter; masterClock equals low 32 bits',
        'effect_latch_clear_contexts':dict(sorted(Counter(w['context_kind'] for w in clear_witnesses).items())),
        'scene_clear_witnesses':clear_witnesses,'pc_scoped_scene_clear_count':len(pc_clears),
        'outside_pc_window_scene_clear_count':len(clear_witnesses)-len(pc_clears),
        'limitations':['no installed helper or expanded-ROM read','no interrupt occurred inside the resolver unless counted explicitly',
            'absence of observed temporary access is checkpoint-bounded, not scratch ownership',
            'PC windows run from resolver entry until the next branch producer or terminal, not a proved complete action lifetime',
            'exec snapshots precede the named instruction; memory callback CPU PC may have advanced beyond its operands'],
        'trampoline_values':sorted({tuple(r['trampolines']) for r in records})}


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
    stem="pe_context_"+secrets.token_hex(12)
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
    if error or proc is None or proc.returncode!=52:
        raise ObservationError(f"isolated observation failed: {error or proc.returncode}; retained {output}")
    trace_path=output/"trace.json"
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=64*1024*1024),"trace")
    result={"schema":SCHEMA,"evidence_level":"exploratory-runtime-not-accepted","evidence_scope":"checkpoint-bounded observation; no helper installed",
        "source_hashes":before,"staged_hashes":staged_before,"trace_sha256":safe.sha256_file(trace_path),
        "input_schedule_basis":"inputPolled callbacks; poll field is a relative poll count; timing fields retain emulator key names",
        "observations":summarize(trace),"sources_and_staged_inputs_unchanged":True,
        "rom_mutated":False,"memory_or_cpu_injection":False,"helper_installed":False,"production_approval":False,
        "reproduce":["python","-B","tools/run_package_resolver_context_v1.py","--output-dir","private/test_runs/resolver_context_NEW"]}
    (output/"manifest.json").write_bytes(canonical(result))
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(run(args.output_dir),indent=2))
