#!/usr/bin/env python3
"""Read-only, source-bound instruction/SP observation of five actual game NMIs.

The intervals begin after the native hardware frame already exists and end
before RTI. Bus callbacks combine CPU, DMA and dummy operations. No helper,
ROM/CPU edit, fabricated interrupt, or global stack-headroom claim is made.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import run_package_resolver_context_v1 as context

ROOT=Path(__file__).resolve().parents[1]
safe=context.safe
SCHEMA='project-epoch-normal-nmi-stack-observation-v1'
COLLECTOR=ROOT/'tools/mesen_normal_nmi_stack_observation_v1.lua'
TESTS=ROOT/'tests/test_normal_nmi_stack_observation_v1.py'
POLLS=(379,500,700,927,928)
ENTRY=0xD1E77C
EXIT=0xD1E898
MAX_EXEC=50000
MAX_BUS=250000
MAX_CLOCK=715000
MAX_TRACE=128*1024*1024
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIMING_KEYS=set(context.TIMING_KEYS)
REFERENCE_TRACE=('private/test_runs/resolver_context_20260908_final1/trace.json',10811008,
    '6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679')
ENGINE_PINS={
 'shared':('private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h','dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f'),
 'instructions':('private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h','9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd'),
}
ENGINE_PATHS={
 'private/research/mesen_timing_api_2_1_1/SnesCpu.cpp':'ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8',
 'private/research/mesen_timing_api_2_1_1/LuaApi.cpp':'fd1292483bd2e7fa1f5a13c392afadcae2d9ff418cab216c964d623f97e10e24',
 'private/research/mesen_timing_api_2_1_1/SnesMemoryManager.cpp':'2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58',
 'private/research/mesen_nmi_request_2_1_1/SnesDebugger.cpp':'cdc731b03b249a32305be0e020cbcdb3f13e9f8ca897aeadae142d06ef55bd51',
 'private/research/mesen_nmi_request_2_1_1/Debugger.cpp':'71fa7d663b8cb61c7290bdf404244270a8c9d3f907224c990b43ae82a6c95db3',
 'private/research/mesen_nmi_request_2_1_1/ScriptManager.h':'c6ec04a297abaf8b6f2927d8d6433278a69fb24df908786ca7a0f74bdea6c8a5',
 'private/research/mesen_nmi_request_2_1_1/MemoryDumper.cpp':'db1422d7ff1794334f55f5e30a66e3bc859347de42f7dc5425d9ac93e45ca197',
 'private/research/mesen_nmi_stack_watchdog_2_1_1/ScriptingContext.cpp':'1e4645ab7783c179a2998e906b72a42bce98c340badb269c0506996229ba0157',
 'private/research/mesen_nmi_stack_watchdog_2_1_1/ScriptWindowConfig.cs':'d58e9419defca6c3fd2e182ed23ebb08c39e61b7f5ea677275cf86d9ccb5a51a',
}
PUBLICATION=((0x5DAC,0x5DFD),(0x9876,0x987C),(0xA0B3,0xA0B5))

class ObservationError(ValueError):pass

def require(value,message):
    if not value:raise ObservationError(message)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def serial(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
def integer(value,lo,hi,label):
    require(type(value) is int and lo<=value<=hi,'exact bounded integer '+label)
    return value

def exact(value,keys,label):
    require(type(value) is dict and set(value)==set(keys),'exact object '+label)
    return value

def byte_array(value,n,label):
    require(type(value) is list and len(value)==n,'exact byte-array extent '+label)
    require(all(type(x) is int and 0<=x<=255 for x in value),'exact byte-array values '+label)

def cpu(value):
    exact(value,CPU_KEYS,'CPU')
    require(value['emulationMode'] is False,'native mode required')
    for k in CPU_KEYS-{'emulationMode'}:integer(value[k],0,255 if k in ('k','dbr','ps') else 65535,'CPU '+k)
    require(value['sp']<0x2000,'observed stack leaves low WRAM mirror')
    if value['ps']&0x10:require(value['x']<256 and value['y']<256,'8-bit index high bytes')

def timing(value):
    exact(value,TIMING_KEYS,'timing')
    for k in TIMING_KEYS:integer(value[k],0,2**53-1,'timing '+k)
    require(value['masterClock']==value['memoryManager.masterClock']&0xFFFFFFFF,'full/generic clock relation')
    require(value['clockRate']==21477270,'pinned NTSC clock rate')
    require(0<=value['ppu.scanline']<262 and 0<=value['memoryManager.hClock']<=1364,'raster bounds')

def physical_wram(address):
    bank=address>>16; offset=address&0xFFFF
    if bank in (0x7E,0x7F):return address-0x7E0000
    if (bank<=0x3F or 0x80<=bank<=0xBF) and offset<0x2000:return offset
    return None

def opcode_modes(source):
    """Recover the pinned emulator's complete opcode/address-mode inventory.

    The mapping from mode name to encoded length is explicitly reviewed below;
    source extraction inventories spelling, not an automatic semantic proof.
    """
    rows=re.findall(r'case 0x([0-9A-F]{2}): (.*?); break;',source)
    require(len(rows)==256 and len({a for a,_ in rows})==256,'complete opcode dispatch source inventory')
    modes={}
    for key,body in rows:
        match=re.search(r'AddrMode_(\w+)',body)
        modes[int(key,16)]=match.group(1) if match else 'special'
    return modes

def load_modes():
    rel,pin=ENGINE_PINS['shared']; raw=(ROOT/rel).read_bytes()
    require(sha(raw)==pin,'pinned opcode inventory source')
    return opcode_modes(raw.decode('utf-8'))

MODE_LENGTHS={
 'Abs':3,'AbsIdxX':3,'AbsIdxY':3,'AbsInd':3,'AbsIndLng':3,'AbsJmp':3,
 'AbsLng':4,'AbsLngIdxX':4,'AbsLngJmp':4,'Acc':1,'BlkMov':3,
 'Dir':2,'DirIdxIndX':2,'DirIdxX':2,'DirIdxY':2,'DirInd':2,'DirIndIdxY':2,
 'DirIndLng':2,'DirIndLngIdxY':2,'Imm16':3,'Imm8':2,'Imp':1,'Rel':2,
 'RelLng':3,'StkRel':2,'StkRelIndIdxY':2,
}
MODES=load_modes()
SPECIAL_LENGTHS={0x08:1,0x0B:1,0x22:4,0x28:1,0x2B:1,0x40:1,0x48:1,
 0x4B:1,0x5A:1,0x60:1,0x68:1,0x6B:1,0x7A:1,0x7C:3,0x8B:1,0xAB:1,
 0xCB:1,0xDA:1,0xFA:1,0xFC:3}
FORBIDDEN={0x00,0x02,0x42,0xCB,0xDB,0xFB} # BRK/COP/WDM/WAI/STP/XCE need a new contract.
BRANCHES={0x10:(0x80,False),0x30:(0x80,True),0x50:(0x40,False),0x70:(0x40,True),
          0x90:(1,False),0xB0:(1,True),0xD0:(2,False),0xF0:(2,True)}

def decode(raw,p):
    byte_array(raw,4,'opcode peeks')
    op=raw[0]; require(op not in FORBIDDEN,'unreviewed halted/interrupt/emulation opcode')
    mode=MODES[op]
    if mode=='ImmM':n=2 if p&0x20 else 3
    elif mode=='ImmX':n=2 if p&0x10 else 3
    elif mode=='special':n=SPECIAL_LENGTHS[op]
    else:
        require(mode in MODE_LENGTHS,'unreviewed addressing mode');n=MODE_LENGTHS[mode]
    return op,raw[:n]

def pc_of(c):return c['k']<<16|c['pc']
def signed(v,bits):return v-(1<<bits) if v&(1<<(bits-1)) else v

def instruction_flow(previous,following,bus_events,read_rom):
    """Validate observed PC/SP/width/D/DBR flow and implicit stack ownership.

    Arithmetic register semantics are retained observations, not re-emulated.
    Dynamic branch flags and indirect call bytes are checked against the actual
    pre-state / bus reads. All stack-changing opcodes have explicit semantics.
    """
    p=previous['cpu']; q=following['cpu']; at=pc_of(p)
    cpu(p);cpu(q)
    for key in ('memoryManager.masterClock','cpu.cycleCount'):
        require(following['timing'][key]>previous['timing'][key],'strict successive instruction '+key)
    require(type(bus_events) is list,'bus event sequence')
    for e in bus_events:
        require(type(e) is dict and e.get('kind') in ('read','write'),'bus ownership event kind')
        integer(e['address'],0,0xFFFFFF,'owned bus address');integer(e['value'],0,255,'owned bus byte');cpu(e['cpu'])
    op,raw=decode(previous['code'],p['ps']); n=len(raw)
    require((at&0xFFFF)+n<=0x10000,'instruction crosses program bank')
    require(bytes(raw)==read_rom(at,n),'instruction bytes differ from pinned ROM')
    nxt=p['k']<<16|((p['pc']+n)&0xFFFF); expected=nxt; sp=p['sp']; push=[]; pull=[]
    transition='sequential'; flags=p['ps']&0x34
    def read_bytes(addresses):
        values=[]
        for address in addresses:
            require(physical_wram(address) is not None or 0xC00000<=address<=0xFFFFFF,
                    'unreconciled indirect/stack pointer source domain')
            matches=[x for x in bus_events if x['kind']=='read' and x['address']==address]
            require(len(matches)==1,'exact indirect/stack bus read ownership')
            if 0xC00000<=address<=0xFFFFFF:
                require(bytes([matches[0]['value']])==read_rom(address,1),
                        'immutable control-pointer read versus pinned source')
            values.append(matches[0]['value'])
        return values
    def word_bytes(value):return [value>>8&255,value&255]
    width_a=1 if p['ps']&0x20 else 2; width_x=1 if p['ps']&0x10 else 2
    if op in BRANCHES:
        bit,wanted=BRANCHES[op]
        if bool(p['ps']&bit)==wanted:expected=p['k']<<16|((nxt+signed(raw[1],8))&65535)
        transition='conditional-branch'
    elif op in (0x80,0x82):
        expected=p['k']<<16|((nxt+signed(int.from_bytes(bytes(raw[1:]),'little'),8 if op==0x80 else 16))&65535)
        transition='relative-branch'
    elif op in (0x4C,0x5C,0x20,0x22):
        expected=int.from_bytes(bytes(raw[1:]),'little')|(p['k']<<16 if op in (0x4C,0x20) else 0)
        transition='call' if op in (0x20,0x22) else 'jump'
        if op in (0x20,0x22):push=([p['k']] if op==0x22 else [])+word_bytes((nxt-1)&65535)
    elif op in (0x7C,0xFC,0x6C,0xDC):
        base=int.from_bytes(bytes(raw[1:]),'little')
        if op in (0x7C,0xFC):base=(base+p['x'])&65535; bank=p['k']<<16
        else:bank=0
        values=read_bytes([bank|((base+i)&65535) for i in range(3 if op==0xDC else 2)])
        expected=int.from_bytes(bytes(values),'little')|(0 if op==0xDC else p['k']<<16)
        transition='indexed-call' if op==0xFC else 'indirect-jump'
        if op==0xFC:push=word_bytes((nxt-1)&65535)
    elif op in (0x60,0x6B):
        pull=read_bytes([sp+i for i in range(1,4 if op==0x6B else 3)])
        expected=((pull[2] if op==0x6B else p['k'])<<16)|((int.from_bytes(bytes(pull[:2]),'little')+1)&65535)
        transition='return'
    elif op==0x40:raise ObservationError('RTI inside the closed pre-RTI interval')
    elif op in (0x08,0x0B,0x48,0x4B,0x5A,0x8B,0xDA,0xF4,0x62,0xD4):
        if op==0x08:push=[p['ps']]
        elif op==0x0B:push=word_bytes(p['d'])
        elif op==0x4B:push=[p['k']]
        elif op==0x8B:push=[p['dbr']]
        elif op in (0x48,0x5A,0xDA):
            value=p[{0x48:'a',0x5A:'y',0xDA:'x'}[op]]
            push=[value&255] if (width_a if op==0x48 else width_x)==1 else word_bytes(value)
        elif op==0xF4:push=word_bytes(int.from_bytes(bytes(raw[1:]),'little'))
        elif op==0x62:push=word_bytes((nxt+signed(int.from_bytes(bytes(raw[1:]),'little'),16))&65535)
        else:
            address=(p['d']+raw[1])&65535
            values=read_bytes([address,(address+1)&65535]);push=list(reversed(values))
    elif op in (0x28,0x2B,0x68,0x7A,0xAB,0xFA):
        count={0x28:1,0x2B:2,0x68:width_a,0x7A:width_x,0xAB:1,0xFA:width_x}[op]
        pull=read_bytes([sp+i for i in range(1,count+1)])
        value=int.from_bytes(bytes(pull),'little')
        if op==0x28:require(q['ps']==value,'PLP exact pulled status');flags=value&0x34
        else:
            reg={0x2B:'d',0x68:'a',0x7A:'y',0xAB:'dbr',0xFA:'x'}[op]
            expected_value=(p['a']&0xFF00|value) if op==0x68 and width_a==1 else value
            require(q[reg]==expected_value,'pull value/register mismatch')
    elif op in (0x1B,0x9A):sp=p['a'] if op==0x1B else p['x'];transition='stack-rebase'
    elif op in (0x44,0x54):
        expected=at if p['a']!=0 else nxt
        require(q['a']==(p['a']-1)&65535,'block-move accumulator iteration')
        delta=1 if op==0x54 else -1; mask=255 if width_x==1 else 65535
        require(q['x']==(p['x']+delta)&mask and q['y']==(p['y']+delta)&mask,'block-move index iteration')
        require(q['dbr']==raw[1],'block-move destination bank');transition='block-move'
    if op in (0xC2,0xE2):flags=(p['ps']&~raw[1] if op==0xC2 else p['ps']|raw[1])&0x34
    elif op==0x58:flags&=~4
    elif op==0x78:flags|=4
    require(q['ps']&0x34==flags,'width/interrupt-mask transition')
    if op not in (0x2B,0x5B):require(q['d']==p['d'],'unowned D change')
    elif op==0x5B:require(q['d']==p['a'],'TCD value')
    if op not in (0xAB,0x44,0x54):require(q['dbr']==p['dbr'],'unowned DBR change')
    expected_sp=sp-len(push)+len(pull)
    require(0<=expected_sp<0x2000 and q['sp']==expected_sp,'exact instruction SP transition / no wrap')
    require(pc_of(q)==expected,'exact instruction PC transition')
    # PushByte writes at current S then decrements; PopByte increments before read.
    expected_push=[(p['sp']-i,value,p['sp']-i) for i,value in enumerate(push)]
    expected_pull=[(p['sp']+i+1,value,p['sp']+i+1) for i,value in enumerate(pull)]
    actual_push=[(e['address'],e['value'],e['cpu']['sp']) for e in bus_events
        if e['kind']=='write' and e['address'] in {a for a,_,_ in expected_push}]
    actual_pull=[(e['address'],e['value'],e['cpu']['sp']) for e in bus_events
        if e['kind']=='read' and e['address'] in {a for a,_,_ in expected_pull}]
    require(actual_push==expected_push,'exact implicit CPU stack writes')
    require(actual_pull==expected_pull,'exact implicit CPU stack reads')
    allowed_sp={p['sp'],q['sp']}|{a for a,_,_ in expected_push}|{a for a,_,_ in expected_pull}
    require(all(e['cpu']['sp'] in allowed_sp for e in bus_events),'unowned intra-instruction SP value')
    return {'kind':transition,'site':at,'next':expected,'sp_before':p['sp'],'sp_after':q['sp'],
            'push_bytes':len(push),'pull_bytes':len(pull),'owned_stack_writes':expected_push}

def validate_interval(row,read_rom):
    exact(row,{'poll','events','wram_before','wram_after','entry_marker','exit_marker'},'interval')
    integer(row['poll'],0,930,'interval poll')
    byte_array(row['wram_before'],0x20000,'WRAM baseline');byte_array(row['wram_after'],0x20000,'WRAM final')
    for marker in ('entry_marker','exit_marker'):
        exact(row[marker],{'hardware','trampolines','gate_bytes'},marker)
        byte_array(row[marker]['hardware'],4,'native hardware frame')
        byte_array(row[marker]['trampolines'],8,'trampolines')
        byte_array(row[marker]['gate_bytes'],12,'selected gates')
        require(row[marker]['trampolines']==[92,124,231,209,92,151,254,209],'unchanged original interrupt trampolines')
    require(row['entry_marker']['hardware']==row['exit_marker']['hardware'],'native hardware frame preservation')
    events=row['events'];require(type(events) is list and events,'nonempty interval events')
    executions=[];bus_count=0;last_timing=None;last_exec=0;ledger={};groups={};mins=[];publication=[]
    decoded_lengths={};byte_owner={}
    for index,event in enumerate(events):
        require(type(event) is dict and event.get('kind') in ('exec','read','write'),'event kind')
        base={'kind','ordinal','cpu','timing'}
        exact(event,base|({'code','stack'} if event['kind']=='exec' else {'address','value'}),'event')
        cpu(event['cpu']);timing(event['timing']);mins.append(event['cpu']['sp'])
        integer(event['ordinal'],1,MAX_EXEC,'execution ordinal')
        t=event['timing']
        if last_timing:
            for k in ('memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount'):
                require(t[k]>=last_timing[k],'monotonic '+k)
        last_timing=t
        if event['kind']=='exec':
            last_exec+=1;require(event['ordinal']==last_exec,'complete ordered execution ordinals')
            byte_array(event['code'],4,'opcode peeks');byte_array(event['stack'],12,'execution stack peek')
            at=pc_of(event['cpu']);require(0xC00000<=at<=0xFFFFFF,'observed execution left canonical high ROM')
            require(bytes(event['code'])==read_rom(at,4),'four-byte opcode peeks differ from ROM')
            _,instruction=decode(event['code'],event['cpu']['ps']);length=len(instruction)
            require((at&65535)+length<=65536,'instruction crosses program bank')
            require(at not in decoded_lengths or decoded_lengths[at]==length,'incompatible width-dependent decode')
            decoded_lengths[at]=length
            for occupied in range(at,at+length):
                require(occupied not in byte_owner or byte_owner[occupied]==at,'overlapping executed instruction bytes')
                byte_owner[occupied]=at
            require(at not in (0xD1FE97,0xD1F4C0) and (at!=ENTRY or last_exec==1),'nested/alternate interrupt boundary')
            executions.append(event);groups[last_exec]=[]
        else:
            bus_count+=1;require(bus_count<=MAX_BUS,'bus event bound')
            require(last_exec and event['ordinal']==last_exec,'bus event ownership ordinal')
            integer(event['address'],0,0xFFFFFF,'bus address');integer(event['value'],0,255,'bus byte')
            groups[last_exec].append(event)
            physical=physical_wram(event['address'])
            if event['kind']=='write' and physical is not None:ledger[physical]=event['value']
            if physical is not None and any(a<=physical<b for a,b in PUBLICATION):
                publication.append({'event_index':index,'ordinal':last_exec,'kind':event['kind'],
                    'address':event['address'],'value':event['value'],'cpu':event['cpu']})
    require(2<=len(executions)<=MAX_EXEC,'bounded complete executions')
    first,last=executions[0],executions[-1]
    require(events[0] is first and events[-1] is last,'closed pre-execution endpoints')
    require(pc_of(first['cpu'])==ENTRY and pc_of(last['cpu'])==EXIT,'exact normal-NMI interval boundaries')
    require(first['cpu']['ps']==(row['entry_marker']['hardware'][0]&~8)|4,'native hardware entry status transform')
    for key in ('a','x','y','d','dbr','sp'):
        require(first['cpu'][key]==last['cpu'][key],'restored handler register '+key)
    require(first['stack'][:4]==row['entry_marker']['hardware'] and last['stack'][:4]==row['exit_marker']['hardware'],
            'execution/marker hardware frame agreement')
    before=row['wram_before'];after=row['wram_after'];expected=before.copy()
    for address,value in ledger.items():expected[address]=value
    require(after==expected,'complete WRAM final state / bus-write ledger')
    current=before.copy()
    # Each debugger stack peek must agree with the prior actual bus-write ledger.
    for event in events:
        if event['kind']=='write':
            address=physical_wram(event['address'])
            if address is not None:current[address]=event['value']
        elif event['kind']=='read':
            address=physical_wram(event['address'])
            if address is not None:require(event['value']==current[address],'WRAM read versus prior write ledger')
            if 0xC00000<=event['address']<=0xFFFFFF:
                require(bytes([event['value']])==read_rom(event['address'],1),
                        'immutable ROM read versus pinned source')
        elif event['kind']=='exec':
            s=event['cpu']['sp'];require(s+12<0x2000,'stack-peek extent')
            require(event['stack']==current[s+1:s+13],'stack snapshot versus prior write ledger')
    changes=[];calls=[];widths=[];frames=[]
    minimum=min(mins);entry_sp=first['cpu']['sp']
    for prior,later in zip(executions,executions[1:]):
        result=instruction_flow(prior,later,groups[prior['ordinal']],read_rom)
        owned=result.pop('owned_stack_writes')
        op,raw=decode(prior['code'],prior['cpu']['ps'])
        if op in (0x20,0x22,0xFC):
            frames.append({'kind':'long' if op==0x22 else 'near','sp':later['cpu']['sp'],
                'restore_sp':prior['cpu']['sp'],'resume':prior['cpu']['k']<<16|((prior['cpu']['pc']+len(raw))&65535)})
        elif op in (0x60,0x6B):
            require(frames and frames[-1]['kind']==('near' if op==0x60 else 'long'),'typed call/return frame kind')
            frame=frames.pop()
            require(prior['cpu']['sp']==frame['sp'] and later['cpu']['sp']==frame['restore_sp']
                and pc_of(later['cpu'])==frame['resume'],'exact owned call return frame / PBR')
        elif result['pull_bytes']:
            addresses=set(range(prior['cpu']['sp']+1,prior['cpu']['sp']+result['pull_bytes']+1))
            require(not any(addresses.intersection(range(f['sp']+1,f['restore_sp']+1)) for f in frames),
                'software pull consumes a typed call frame')
        for event in groups[prior['ordinal']]:
            physical=physical_wram(event['address'])
            if event['kind']=='write' and physical is not None and minimum<physical<=entry_sp+4:
                require((event['address'],event['value'],event['cpu']['sp']) in owned,
                        'write into observed frame lacks implicit CPU stack ownership')
        if result['sp_before']!=result['sp_after']:changes.append({'ordinal':later['ordinal'],**result})
        if result['kind'] in ('call','indexed-call','return','indirect-jump'):
            calls.append({'ordinal':prior['ordinal'],**result})
        widths.append(prior['cpu']['ps']&0x30)
    require(last['code'][0]==0x40 and not groups[last['ordinal']],'RTI is an unexecuted terminal observation')
    require(not frames,'all observed native calls returned before RTI')
    clocks=last['timing']['memoryManager.masterClock']-first['timing']['memoryManager.masterClock']
    require(0<clocks<=MAX_CLOCK,'bounded interval master clocks')
    require(last['timing']['ppu.frameCount']-first['timing']['ppu.frameCount']<=2,'bounded interval frames')
    require(minimum<=entry_sp and minimum>0,'bounded observed minimum SP')
    return {'poll':row['poll'],'execution_observations':len(executions),'executed_instructions':len(executions)-1,
        'bus_events':bus_count,'entry_sp':entry_sp,'minimum_instruction_boundary_sp':min(e['cpu']['sp'] for e in executions),
        'minimum_recorded_sp':minimum,'additional_bytes_below_handler_entry':entry_sp-minimum,
        'bytes_below_interrupted_sp_including_existing_hardware_frame':entry_sp+4-minimum,
        'master_clocks':clocks,'execution_projection_sha256':sha(serial(executions)),
        'sp_changes':changes,'observed_call_return_transitions':calls,'width_states':sorted(set(widths)),
        'publication_accesses':publication,'wram_changed_bytes':sum(a!=b for a,b in zip(before,after)),
        'wram_before_sha256':sha(bytes(before)),'wram_after_sha256':sha(bytes(after)),
        'complete_observed_wram_write_ledger':True,'native_hardware_pushes_captured':False,
        'all_game_nmi_paths_proved':False,'production_stack_headroom_proved':False}

def reference_records():
    path,size,pin=REFERENCE_TRACE;raw=(ROOT/path).read_bytes()
    require(len(raw)==size and sha(raw)==pin,'accepted prior context trace identity')
    return json.loads(raw)['records']

def reference_entries():
    records=reference_records()
    selected={r['poll']:r for r in records if r['kind']=='interrupt-entry'
        and r['context_kind']=='normal-nmi' and r['poll'] in POLLS}
    require(set(selected)==set(POLLS),'five fixed prior entry contexts')
    return selected

def reference_resolver():
    rows=[r for r in reference_records() if r['kind']=='resolver-entry']
    require(len(rows)==1,'one accepted prior resolver entry')
    return rows[0]

def summarize(trace,read_rom,pilot=False):
    require(type(pilot) is bool,'exact pilot argument')
    exact(trace,{'schema','error','pilot','intervals','baseline','resolver','terminal_poll'},'trace')
    require(type(trace['pilot']) is bool,'exact trace pilot boolean')
    require(trace['schema']==SCHEMA and trace['error'] is None and trace['pilot'] is pilot,'trace protocol/error/mode')
    require(type(trace['intervals']) is list,'interval array')
    chosen=POLLS[:1] if pilot else POLLS
    for row in trace['intervals']:
        require(type(row) is dict,'interval object');integer(row['poll'],0,930,'selected interval poll')
    require([r['poll'] for r in trace['intervals']]==list(chosen),'exact fixed interval inventory')
    integer(trace['terminal_poll'],0,930,'terminal poll')
    require(trace['terminal_poll']==(381 if pilot else 930),'fixed observation terminal')
    exact(trace['baseline'],{'location','party'},'baseline')
    integer(trace['baseline']['location'],0,65535,'baseline location')
    byte_array(trace['baseline']['party'],3,'baseline party')
    require(trace['baseline']=={'location':0x01DB,'party':[0,1,2]},'unchanged checkpoint baseline')
    exact(trace['resolver'],{'poll','cpu','selector','branch'},'resolver witness')
    resolver=trace['resolver'];cpu(resolver['cpu'])
    integer(resolver['poll'],0,930,'resolver poll');integer(resolver['selector'],0,65535,'resolver selector')
    integer(resolver['branch'],0,65535,'resolver branch')
    require(resolver['poll']==378 and pc_of(resolver['cpu'])==0xC14612 and resolver['selector']==8
        and resolver['branch']==0 and resolver['cpu']['d']==0 and resolver['cpu']['dbr']==0x7E,
        'same ordinary resolver provenance')
    require(resolver['cpu']==reference_resolver()['cpu'],'same source-pinned entire resolver entry CPU')
    old=reference_entries();results=[]
    for row in trace['intervals']:
        require(row['events'][0]['cpu']==old[row['poll']]['cpu'],'same source-pinned actual NMI entry CPU')
        require(row['entry_marker']['hardware']==old[row['poll']]['stack'][:4],'same source-pinned hardware return frame')
        results.append(validate_interval(row,read_rom))
    return {'intervals':results,'complete_observed_intervals':len(results),
        'minimum_recorded_sp':min(r['minimum_recorded_sp'] for r in results),
        'maximum_additional_bytes_below_handler_entry':max(r['additional_bytes_below_handler_entry'] for r in results),
        'maximum_depth_including_hardware_frame':max(r['bytes_below_interrupted_sp_including_existing_hardware_frame'] for r in results),
        'all_game_nmi_paths_proved':False,'production_stack_headroom_proved':False}

def read_bounded(path,maximum,label):
    size=path.stat().st_size;require(size<=maximum,'bounded '+label)
    return safe.read_direct_regular_file(path,label,parent=path.parent,maximum=size)

def source_paths():
    paths={'launcher':Path(__file__).resolve(),'collector':COLLECTOR,'tests':TESTS,
      'context_launcher':Path(context.__file__).resolve(),'isolation_library':Path(safe.__file__).resolve(),
      'reference_trace':ROOT/REFERENCE_TRACE[0]}
    for name,(rel,pin) in ENGINE_PINS.items():
        p=ROOT/rel;require(sha(p.read_bytes())==pin,'engine pin '+name);paths['engine_'+name]=p
    for rel,pin in ENGINE_PATHS.items():
        p=ROOT/rel;require(sha(p.read_bytes())==pin,'pinned engine source '+rel);paths['engine_'+Path(rel).stem]=p
    require(sha(paths['context_launcher'].read_bytes())=='88ccf83e83a68f7bbdc3c65e626b1480041c9e95db4fe36541a6c267b8030214',
            'unchanged accepted context launcher')
    require(sha(paths['isolation_library'].read_bytes())=='d5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96',
            'unchanged isolation library')
    return paths

def run(output_dir,pilot=False):
    private=safe.canonical_private_root();inputs={}
    for key,(rel,size,pin) in context.PINNED.items():
        p=safe.resolve_private_file(ROOT/rel,key,private_root=private)
        require(p.stat().st_size==size and safe.sha256_file(p)==pin,'pinned '+key);inputs[key]=p
    runtime={k:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/n,k,private_root=private) for k,n in safe.RUNTIME_NAMES.items()}
    for k,p in runtime.items():safe.require_identity(p,k)
    guarded={**inputs,**runtime,**source_paths()};before={k:safe.sha256_file(p) for k,p in guarded.items()}
    reference_entries()
    output=safe.prepare_private_output_dir(output_dir,private_root=private,
        forbidden_roots=tuple(p.parent for p in inputs.values())+(safe.DEFAULT_MESEN.parent,))
    archive=output/'source_archive';archive.mkdir();archives={}
    for key,path in source_paths().items():
        if key=='reference_trace':continue
        target=archive/(key+path.suffix);safe.copy_new_regular_file(path,target,key);archives[key]=target
    archive_before={k:safe.sha256_file(p) for k,p in archives.items()}
    require(all(archive_before[k]==before[k] for k in archives),'source archive matches guarded prelaunch bytes')
    stage=output/'staged';app=stage/'app';saves=app/'Saves';saves.mkdir(parents=True);staged={}
    for key,name in safe.RUNTIME_NAMES.items():
        staged[key]=app/name;safe.copy_new_regular_file(runtime[key],staged[key],key)
    stem='pe_nmi_stack_'+secrets.token_hex(12)
    for key,path in inputs.items():
        target=saves/(stem+'.srm') if key=='sram' else stage/(stem+('.sfc' if key=='rom' else '.mss'))
        safe.copy_new_regular_file(path,target,key);staged[key]=target
    staged['collector']=stage/'collector.lua';safe.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    stage_before={k:safe.sha256_file(p) for k,p in staged.items()}
    require(all(stage_before[k]==before[k] for k in staged),'exact staged source bytes')
    receipt={'schema':SCHEMA,'pilot':pilot,'source_hashes':before,'staged_hashes':stage_before,
             'source_archive_hashes':archive_before,'source_archive_files':{k:p.name for k,p in archives.items()}}
    (output/'launch_inputs.json').write_bytes(serial(receipt))
    env=safe.minimal_subprocess_environment()
    for key,parts in {'USERPROFILE':('profile',),'APPDATA':('profile','AppData','Roaming'),
        'LOCALAPPDATA':('profile','AppData','Local'),'TEMP':('temp',),'TMP':('temp',)}.items():
        p=stage.joinpath(*parts);p.mkdir(parents=True,exist_ok=True);env[key]=str(p)
    env.update(PE_NMI_STACK_PROTOCOL=SCHEMA,PE_NMI_STACK_STATE=str(staged['state']),
        PE_NMI_STACK_TRACE=str(output/'trace.json'),PE_NMI_STACK_PILOT='1' if pilot else '0')
    command=[str(staged['mesen']),'--testRunner','--timeout=900','--doNotSaveSettings',
        '--debug.scriptWindow.allowIoOsAccess=true','--snes.ramPowerOnState=AllZeros',
        '--snes.port1.type=SnesController',str(staged['collector']),str(staged['rom'])]
    error=None;proc=None
    try:
        proc=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=915,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=False)
        (output/'process.log').write_bytes(proc.stdout+proc.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:error=str(exc)
    safe.require_file_hashes_unchanged(guarded,before,'source')
    safe.require_file_hashes_unchanged(staged,stage_before,'staged')
    safe.require_file_hashes_unchanged(archives,archive_before,'source archive')
    require((output/'launch_inputs.json').read_bytes()==serial(receipt),'prelaunch receipt unchanged')
    require(sorted(x.name for x in archive.iterdir())==sorted(p.name for p in archives.values()),'exact source archive inventory')
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged['sram'].name)
    require(not error and proc is not None and proc.returncode==52,'native observation failed; private artifacts retained: '+str(error or (proc.returncode if proc else None)))
    trace_path=output/'trace.json';trace=json.loads(read_bounded(trace_path,MAX_TRACE,'trace'))
    raw_rom=read_bounded(inputs['rom'],4194304,'ROM')
    def read_rom(address,count):
        require(0xC00000<=address and address+count<=0x1000000,'canonical ROM read extent')
        return raw_rom[address-0xC00000:address-0xC00000+count]
    try:observations=summarize(trace,read_rom,pilot)
    except (ValueError,KeyError,TypeError) as exc:
        (output/'host_rejection.json').write_bytes(serial({'schema':SCHEMA,'error':str(exc),'source_hashes':before,
            'trace_sha256':sha(trace_path.read_bytes())}));raise
    result={**receipt,'evidence_level':'exploratory-runtime-not-accepted','observations':observations,
        'trace_sha256':safe.sha256_file(trace_path),'sources_staged_archives_unchanged':True,
        'checkpoint_load_only':True,'controller_schedule_reused':True,'rom_cpu_memory_edits':False,
        'production_approval':False}
    (output/'manifest.json').write_bytes(serial(result));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--pilot',action='store_true');args=parser.parse_args()
    sys.stdout.buffer.write((json.dumps(run(args.output_dir,args.pilot),indent=2)+'\n').encode('utf-8'))
