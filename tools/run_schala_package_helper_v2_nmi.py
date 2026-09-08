"""Isolated original NMI pilot; unchanged original carrier and v2 helper.

NMI is requested through the actual 4200 register after a natural VBlank latch.
No manufactured interrupt frame, direct NMI state edit, or cartridge mutation.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import run_schala_package_helper_v2_stack as v2
import audit_mesen_nmi_phase_contract_v2 as phase_audit

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-package-helper-v2-nmi-v1'
COLLECTOR=ROOT/'tools/mesen_schala_package_helper_v2_nmi.lua'
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIME_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
FLAG_KEYS={'internalRegisters.nmiFlag','internalRegisters.enableNmi','internalRegisters.enableHorizontalIrq',
    'internalRegisters.enableVerticalIrq','internalRegisters.enableAutoJoypadRead','cpu.nmiFlagCounter','cpu.needNmi',
    'cpu.irqLock','cpu.irqSource','cpu.prevIrqSource','dmaController.needToProcess','dmaController.hdmaChannels',
    'dmaController.hdmaPending','dmaController.hdmaInitPending','dmaController.dmaStartDelay','dmaController.dmaPending'}
HANDLER_PCS=(0x8020,0x8021,0x8023,0x8024,0x8028,0x8029,0x802D,0x802E,0x802F)
INTEGER_FLAGS={'cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'}
PHASE_LIMIT=262
ARCHIVE_KEYS=('collector','launcher','v2_library','helper','host_adapter','isolation_library','v0_library','v1_library',
              'nmi_tests','phase_audit','prior_phase_audit','phase_reference')
# Exact pre-instruction sites in the unchanged 577-byte helper. Depths count
# helper-owned bytes before/after that instruction, excluding the NMI.
SUCCESS_BOUNDARIES={
    'first-save-php':(0x8000,0x8001,0,1),
    'allocate-tcs':(0x8043,0x8044,8,50),
    'first-countbits-jsr':(0x80EE,0x8232,50,52),
    'second-countbits-jsr':(0x80F5,0x8232,50,52),
    'root-publication':(0x8182,0x8186,50,50),
    'stage-byte-width':(0x81F6,0x81F8,50,50),
    'release-tcs':(0x8215,0x8216,50,8),
    'pull-dbr':(0x8216,0x8217,8,7),
    'pull-y':(0x8217,0x8218,7,5),
    'pull-x':(0x8218,0x8219,5,3),
    'pull-a':(0x8219,0x821A,3,1),
    'pull-p':(0x821A,0x821B,1,0),
    'success-jml-tail':(0x821B,0xF010,0,0),
}
SAFE=v2.safe


class ConformanceError(RuntimeError):pass


def require(test:bool,message:str)->None:
    if not test:raise ConformanceError(message)


def canonical(value)->bytes:return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()


def with_boundary(case:dict,name:str,spec:tuple[int,int,int,int])->dict:
    c=copy.deepcopy(case);before,after,depth_before,depth_after=spec
    normal_depth=(52 if c['expected_rom_reads'] else 50) if c['frame_allocated'] else 8
    c.update(name=c['name']+'-nmi-'+name,nmi_trigger=0x7F0000+before,nmi_resume=0x7F0000+after,
             nmi_boundary=name,nmi_depth_before=depth_before,nmi_depth_after=depth_after,
             nmi_max_depth=max(normal_depth,depth_after+7),nmi_phase_limit=PHASE_LIMIT)
    return c


def build_cases(rom:bytes,scope:str='matrix')->list[dict]:
    require(scope in ('pilot','boundary-pilot','matrix'),'unknown fixed matrix scope')
    result=[]
    for sp in (0x1FEF,0x06D8):
        for bank in (0x41,0x42):
            for flag in (0,0x40):
                for status in range(4):
                    c=v2.with_stack(v2.v1.make_case(rom,f'rom-{bank:02X}-flag-{flag:02X}-status-{status}',
                        flag=flag,bank=bank,index=status),sp)
                    names=SUCCESS_BOUNDARIES if status==0 else ('first-countbits-jsr','pull-p','success-jml-tail')
                    for name in names:
                        if scope=='pilot' and (bank!=0x41 or flag!=0 or status!=0 or name!='first-countbits-jsr'):continue
                        result.append(with_boundary(c,name,SUCCESS_BOUNDARIES[name]))
        if scope!='pilot':
            for status in range(4):
                for route,kwargs,specs in (
                    ('canonical',{'selector':0x7F},{'canonical-pull-p':(0x8019,0x801A,1,0),'canonical-jml-tail':(0x801E,0xF000,0,0)}),
                    ('early-refusal',{'selector':0x90},{'refusal-pull-p':(0x822D,0x822E,1,0),'refusal-jml-tail':(0x822E,0xF020,0,0)}),
                    ('framed-refusal',{'valid':0},{'refusal-release-tcs':(0x8226,0x8227,50,8),'refusal-jml-tail':(0x822E,0xF020,0,0)})):
                    c=v2.with_stack(v2.v1.make_case(rom,route+f'-status-{status}',index=status,**kwargs),sp)
                    for name,spec in specs.items():result.append(with_boundary(c,name,spec))
    require(len(result)==len({c['name'] for c in result}),'duplicate NMI case')
    if scope=='boundary-pilot':
        result=[c for c in result if c['cpu']['sp']==0x1FEF and '-status-0-' in c['name'] and
                ((c['source_bank']==0x42 and c['flag']==0x40) or c['route']!='success')]
    return result


def physical(address:int)->int:
    bank,offset=address>>16,address&65535
    if (bank<=0x3F or 0x80<=bank<=0xBF) and offset<0x2000:return 0x7E0000+offset
    return address


def validate_sites(cases:list[dict],code:bytes)->None:
    require(sha(code)=='77dc3224baaa93077218d43d64cbef10bb55494a37057c1a5bfcf0d8fd6758f8','unchanged exact helper required')
    for c in cases:
        require(c['cpu']['sp'] in (0x1FEF,0x06D8) and c['nmi_phase_limit']==PHASE_LIMIT,'case stack/phase allowlist')
        before,after=c['nmi_trigger'],c['nmi_resume'];offset=before-v2.CODE
        require(0<=offset<len(code),'trigger outside helper')
        opcode=code[offset]
        if opcode==0x20:predicted=0x7F0000+int.from_bytes(code[offset+1:offset+3],'little')
        elif opcode==0x5C:predicted=int.from_bytes(code[offset+1:offset+4],'little')
        else:
            require(opcode in (0x08,0x1B,0x8F,0xE2,0xAB,0x7A,0xFA,0x68,0x28),'unreviewed boundary opcode')
            predicted=before+(4 if opcode==0x8F else 2 if opcode==0xE2 else 1)
        require(after==predicted,'boundary continuation does not match exact instruction bytes')
        normal=(52 if c['expected_rom_reads'] else 50) if c['frame_allocated'] else 8
        require(c['nmi_max_depth']==max(normal,c['nmi_depth_after']+7) and 7<=c['nmi_max_depth']<=59,'combined depth contract')


def nz16(ps:int,value:int)->int:return (ps&~0x82)|(0x80 if value&0x8000 else 0)|(2 if value==0 else 0)


def require_archive_hashes(actual:dict,guarded:dict)->None:
    require(set(actual)==set(ARCHIVE_KEYS),'source archive key set mismatch')
    require(all(type(actual[k]) is str and len(actual[k])==64 and actual[k]==guarded[k] for k in ARCHIVE_KEYS),
            'source archive differs from guarded prelaunch sources')


def validate_handler(events:list[dict],exec_events:list[tuple[int,dict]],interrupted:dict,counter:int)->set[int]:
    observed=[e for _,e in exec_events if e['address'] in HANDLER_PCS]
    require([e['address'] for e in observed]==list(HANDLER_PCS),'complete exact handler instruction sequence')
    expected=dict(interrupted);expected.update(k=0,pc=0x8020,sp=interrupted['sp']-4,ps=(interrupted['ps']&~8)|4)
    entry_ps=expected['ps'];saved_a=expected['a'];counter_after=(counter+1)&65535
    states=[]
    for pc in HANDLER_PCS:
        expected['pc']=pc;states.append(dict(expected))
        if pc==0x8020:expected['sp']-=1
        elif pc==0x8021:expected['ps']&=~0x20
        elif pc==0x8023:expected['sp']-=2
        elif pc==0x8024:expected.update(a=counter,ps=nz16(expected['ps'],counter))
        elif pc==0x8028:expected.update(a=counter_after,ps=nz16(expected['ps'],counter_after))
        elif pc==0x802D:expected.update(a=saved_a,ps=nz16(expected['ps'],saved_a),sp=expected['sp']+2)
        elif pc==0x802E:expected.update(ps=entry_ps,sp=expected['sp']+1)
    require([e['cpu'] for e in observed]==states,'exact handler CPU instruction states')
    epochs={e['exec_index']:e['address'] for e in observed};s=interrupted['sp'];k=interrupted['k'];pc=interrupted['pc']
    # Actual stack callbacks are pre-write and post-increment-for-pull in this
    # pinned emulator. Every handler memory operation has an exact owner/SP.
    expected_memory=[
        (0x8020,'write',0x7E0000+s-4,entry_ps,s-4),
        (0x8023,'write',0x7E0000+s-5,saved_a>>8,s-5),(0x8023,'write',0x7E0000+s-6,saved_a&255,s-6),
        (0x8024,'read',0x7E5EF0,counter&255,s-7),(0x8024,'read',0x7E5EF1,counter>>8,s-7),
        (0x8029,'write',0x7E5EF0,counter_after&255,s-7),(0x8029,'write',0x7E5EF1,counter_after>>8,s-7),
        (0x802D,'read',0x7E0000+s-6,saved_a&255,s-6),(0x802D,'read',0x7E0000+s-5,saved_a>>8,s-5),
        (0x802E,'read',0x7E0000+s-4,entry_ps,s-4),
        (0x802F,'read',0x7E0000+s-3,interrupted['ps'],s-3),
        (0x802F,'read',0x7E0000+s-2,pc&255,s-2),(0x802F,'read',0x7E0000+s-1,pc>>8,s-1),
        (0x802F,'read',0x7E0000+s,k,s)]
    memory=[e for e in events if e['kind'] in ('read','write') and e['exec_index'] in epochs]
    require([(epochs[e['exec_index']],e['kind'],e['address'],e['value'],e['cpu']['sp']) for e in memory]==expected_memory,
            'complete exact handler memory sequence/ownership/SP')
    return set(epochs)


def validate_record(row:dict,case:dict,code:bytes,handler:bytes)->dict:
    require(type(row) is dict and type(case) is dict and type(code) is bytes and type(handler) is bytes and len(handler)==16,'validator input shape')
    require(set(row)=={'name','route','events','changes','preparation','input_fixture_before_hex','input_fixture_after_hex',
        'retired_scratch_before_hex','retired_scratch_after_hex'},'record shape')
    require(row['name']==case['name'] and row['route']==case['route'],'case/route mismatch')
    events=row['events'];require(type(events) is list and 20<len(events)<20000,'event bound')
    kinds={'fixture-baseline','exec','read','write','request-before','request-after','handler-entry','disable-before','disable-after','pre-rti','post-rti'}
    counts={};exec_events=[];previous=(-1,-1,-1);epoch=0
    ledger={a:0 for a in range(0x7E3000,0x7E3100)}
    ledger.update({v2.CODE+i:b for i,b in enumerate(code)})
    ledger.update({a:0xDB for a in v2.TAILS.values()})
    ledger.update(dict(case['patches']))
    for i,e in enumerate(events):
        require(type(e) is dict,'event object')
        extra={'bus_address'} if e.get('kind') in ('read','write') else set()
        require(set(e)=={'kind','address','value','exec_index','cpu','timing','flags','stack','nmi_counter','latch_peek'}|extra,'event shape')
        require(e['kind'] in kinds and type(e['address']) is int and 0<=e['address']<=0xFFFFFF,'event address/kind')
        require(type(e['cpu']) is dict and set(e['cpu'])==CPU_KEYS and e['cpu']['emulationMode'] is False,'native CPU shape')
        for k,value in e['cpu'].items():
            if k!='emulationMode':require(type(value) is int and 0<=value<=(255 if k in ('ps','k','dbr') else 65535),'CPU integer')
        require(set(e['timing'])==TIME_KEYS and set(e['flags'])==FLAG_KEYS,'timing/flags shape')
        for k,value in e['flags'].items():
            require((type(value) is int and 0<=value<=255) if k in INTEGER_FLAGS else type(value) is bool,'flag types')
            if k not in {'internalRegisters.nmiFlag','internalRegisters.enableNmi','cpu.nmiFlagCounter','cpu.needNmi'}:
                require(value==0,'unexpected IRQ/DMA/autojoy state')
        require(e['flags']['cpu.nmiFlagCounter']<=2,'NMI countdown outside declared range')
        for value in e['timing'].values():require(type(value) is int and 0<=value<2**64,'timing integer')
        t=e['timing'];current=(t['memoryManager.masterClock'],t['cpu.cycleCount'],t['ppu.frameCount'])
        require(all(a>=b for a,b in zip(current,previous)),'clock/cycle/frame reversal');previous=current
        require(t['masterClock']==(t['memoryManager.masterClock']&0xFFFFFFFF) and t['frameCount']==t['ppu.frameCount'] and t['clockRate']==21477270,'clock basis')
        require(0<=t['memoryManager.hClock']<=1364,'horizontal raster clock outside declared range')
        require(type(e['stack']) is list and len(e['stack'])==16 and all(type(x) is int and 0<=x<=255 for x in e['stack']),'stack snapshot')
        require(type(e['nmi_counter']) is int and 0<=e['nmi_counter']<=65535 and type(e['latch_peek']) is int and 0<=e['latch_peek']<=255,'counter/latch shape')
        require(type(e['value']) is int and -1<=e['value']<=255,'byte/sentinel shape')
        # Debugger snapshots/read callbacks see all earlier completed CPU stores;
        # the current write callback itself runs before its addressed store.
        require(e['stack']==[ledger.get(0x7E0000+((e['cpu']['sp']+j)&65535),0xA5) for j in range(1,17)],'stack snapshot lacks prior-write provenance')
        require(e['nmi_counter']==ledger.get(0x7E5EF0,0xA5)+(ledger.get(0x7E5EF1,0xA5)<<8),'counter snapshot lacks prior-write provenance')
        if e['kind'] in ('read','write'):
            require(type(e['bus_address']) is int and 0<=e['bus_address']<=0xFFFFFF and e['address']==physical(e['bus_address']),'physical bus alias mismatch')
            require(0<=e['value']<=255,'memory byte value')
            if 0x7E0000+case['cpu']['sp']-59<e['address']<=0x7E0000+case['cpu']['sp']:
                require(e['bus_address']==e['address']&65535,'stack bus must use native bank zero')
            if e['kind']=='read' and 0x7E0000<=e['address']<0x800000:
                require(e['value']==ledger.get(e['address'],0xA5),'WRAM read lacks prior-write provenance')
            if e['kind']=='write':ledger[e['address']]=e['value']
        if e['kind']=='exec':
            epoch+=1;exec_events.append((i,e));pc=e['address']
            require(pc==(e['cpu']['k']<<16)|e['cpu']['pc'],'execution PC mismatch')
            if v2.CODE<=pc<v2.CODE+len(code):expected=code[pc-v2.CODE]
            elif pc in HANDLER_PCS:expected=handler[pc-0x8020]
            else:require(pc in v2.TAILS.values(),'execution whitelist');expected=0xDB
            require(e['value']==expected,'pre-execution opcode peek mismatch')
        require(type(e['exec_index']) is int and e['exec_index']==epoch,'execution ownership ordinal')
        counts.setdefault(e['kind'],[]).append(i)
    def one(kind):
        require(len(counts.get(kind,[]))==1,'exactly one '+kind)
        j=counts[kind][0];return j,events[j]
    base_i,base=one('fixture-baseline');request_i,request=one('request-before');after_i,after=one('request-after')
    entry_i,entry=one('handler-entry');disable_i,disable=one('disable-before');disabled_i,disabled=one('disable-after')
    rti_i,rti=one('pre-rti');resume_i,resume=one('post-rti')
    require(base_i==0 and request_i<after_i<entry_i<disable_i<disabled_i<rti_i<resume_i<=len(events)-1,'NMI lifecycle order')
    require(exec_events[-1][1]['address']==v2.TAILS[case['route']] and
            (exec_events[-1][0]==len(events)-1 or (resume_i==len(events)-1 and resume_i==exec_events[-1][0]+1)), 'exact final terminal')
    require(exec_events[0][1]['address']==v2.CODE,'first helper opcode absent')
    require(base['address']==v2.ENTRY_BRIDGE and base['value']==-1 and base['cpu']['k']==0x7F and base['cpu']['pc']==v2.ENTRY_BRIDGE&65535,'declared setup bridge boundary')
    for tag_i,address in ((entry_i,0x8020),(rti_i,0x802F),(resume_i,case['nmi_resume'])):
        tagged=events[tag_i];anchor=events[tag_i-1]
        require(anchor['kind']=='exec' and anchor['address']==address and tagged['address']==address and tagged['value']==-1,'exact tagged execution boundary')
        require(all(tagged[k]==anchor[k] for k in ('cpu','timing','flags','stack','nmi_counter','latch_peek')),'tag snapshot detached from execution observation')
    require(all(request[k]==events[request_i-1][k] for k in ('cpu','timing','flags','stack','nmi_counter','latch_peek')),'request detached from execution observation')
    require(all(disable[k]==entry[k] for k in ('cpu','timing','flags','stack','nmi_counter','latch_peek')),'disable detached from handler entry')
    for i,e in enumerate(events):
        require(e['flags']['internalRegisters.enableNmi'] is (after_i<=i<disabled_i),'NMI enable state not explained by declared register events')
        if i<after_i or i>=entry_i:
            require(e['flags']['cpu.nmiFlagCounter']==0 and e['flags']['cpu.needNmi'] is False,'pending NMI outside declared trigger window')
    require(events[request_i-1]['kind']=='exec' and events[request_i-1]['address']==case['nmi_trigger'],'request not at selected instruction')
    prep=row['preparation'];require(set(prep)=={'wait_start_clock','latch_rise'} and set(prep['latch_rise'])=={'before','after'},'natural latch transition shape')
    false,risen=prep['latch_rise']['before'],prep['latch_rise']['after']
    for sample in (false,risen):
        require(set(sample)=={'clock','cycles','frame','scanline','hclock','latch','peek'} and type(sample['latch']) is bool,'phase sample shape')
        require(all(type(v) is int and 0<=v<2**64 for k,v in sample.items() if k!='latch'),'phase sample integer')
        require(sample['peek']<=255 and sample['scanline']<PHASE_LIMIT and sample['hclock']<1364,'phase sample bounds')
    require(type(prep['wait_start_clock']) is int and 0<=prep['wait_start_clock']<=false['clock'] and risen['clock']-prep['wait_start_clock']<800000,'phase wait bounds')
    require(0<risen['clock']-false['clock']<=32 and false['cycles']<risen['cycles'] and risen['frame'] in (false['frame'],false['frame']+1),'consecutive idle transition bracket')
    require(false['latch'] is False and risen['latch'] is True and false['peek']&128==0 and risen['peek']&128 and prep['wait_start_clock']<=false['clock']<risen['clock']<base['timing']['memoryManager.masterClock'],'natural latch transition evidence')
    require(base['timing']['ppu.scanline']==risen['scanline']+1,'fixture did not start one line after observed latch rise')
    require(base['timing']['ppu.frameCount']==risen['frame'] and base['timing']['cpu.cycleCount']>risen['cycles'],'phase baseline counters')
    for e in events:
        require(risen['scanline']<e['timing']['ppu.scanline']<case['nmi_phase_limit'] and e['timing']['ppu.frameCount']==risen['frame'],
                'active fixture left declared VBlank phase')
        require(e['flags']['internalRegisters.nmiFlag'] is True and e['latch_peek']&128,'active VBlank latch mismatch')
    for r in (base,request):
        f=r['flags'];require(f['internalRegisters.nmiFlag'] is True and f['internalRegisters.enableNmi'] is False and r['latch_peek']&0x80,'natural latched NMI precondition')
        for k in ('cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'):require(type(f[k]) is int and f[k]==0,'pending interrupt/DMA integer')
        for k in FLAG_KEYS-{'internalRegisters.nmiFlag','cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'}:
            require(f[k] is False,'pending interrupt/DMA flag')
        require(r['timing']['ppu.scanline']>risen['scanline'] and r['timing']['ppu.scanline']<case['nmi_phase_limit'],'interior VBlank precondition')
    require(all(base['cpu'][k]==case['cpu'][k] for k in case['cpu']),'fixture CPU differs from declared input')
    for a,b,value in ((request,after,0x80),(disable,disabled,0)):
        require(a['address']==b['address']==0x4200 and a['value']==b['value']==value and a['cpu']==b['cpu'] and a['timing']==b['timing'] and a['stack']==b['stack']
                and a['nmi_counter']==b['nmi_counter'] and a['latch_peek']==b['latch_peek'],'debugger event changed CPU/clock/frame')
        expected=dict(a['flags']);expected['internalRegisters.enableNmi']=bool(value)
        if value:expected['cpu.nmiFlagCounter']=2
        require(b['flags']==expected,'4200 event did not match actual register transition')
    trigger_cpu=request['cpu'];sp=case['cpu']['sp'];resume_pc=case['nmi_resume']
    require(trigger_cpu['sp']==sp-case['nmi_depth_before'] and trigger_cpu['k']==0x7F and trigger_cpu['pc']==(case['nmi_trigger']&65535),'trigger CPU/frame')
    dummy=[(i,e) for i,e in enumerate(events) if after_i<i<entry_i and e['kind']=='read' and e['bus_address']==resume_pc]
    conditional_idle=[]
    if code[case['nmi_trigger']-v2.CODE]==0x1B:
        # TCS uses AddrMode_Imp -> IdleOrRead before changing SP. A pending
        # NMI turns that instruction idle cycle into a distinct code read.
        # ProcessInterrupt then reads the same PC after TCS has changed SP.
        require(len(dummy)==2,'TCS conditional idle read plus hardware dummy read required')
        conditional_idle=dummy[:1];dummy=dummy[1:]
        idle=conditional_idle[0][1]
        expected_idle=dict(trigger_cpu,pc=resume_pc&65535)
        require(idle['cpu']==expected_idle and idle['flags']['cpu.needNmi'] is True and idle['flags']['cpu.nmiFlagCounter']==0,
                'TCS conditional idle read pre-effect CPU/pending state')
    else:require(len(dummy)==1,'hardware dummy read missing')
    dummy_i,interruption=dummy[0];interrupted=interruption['cpu'];interrupted_sp=sp-case['nmi_depth_after']
    require(interrupted['sp']==interrupted_sp and interrupted['k']==resume_pc>>16 and interrupted['pc']==resume_pc&65535,'completed instruction interruption boundary')
    if conditional_idle:
        require(interrupted==dict(trigger_cpu,sp=trigger_cpu['a'],pc=resume_pc&65535),'TCS completed instruction semantics')
    require(interruption['flags']['cpu.needNmi'] is False and interruption['flags']['cpu.nmiFlagCounter']==0,'hardware NMI acknowledgement absent')
    saved_p=interrupted['ps'];hardware_frame=[saved_p,resume_pc&255,(resume_pc>>8)&255,resume_pc>>16]
    require(entry['cpu']['sp']==interrupted_sp-4 and entry['stack'][:4]==hardware_frame and entry['cpu']['ps']==((saved_p&~8)|4),'native hardware NMI frame/P mismatch')
    require(entry['cpu']['k']==0 and entry['cpu']['pc']==0x8020 and entry['flags']['cpu.needNmi'] is False and entry['flags']['cpu.nmiFlagCounter']==0,'handler vector/ack mismatch')
    require(all(entry['cpu'][k]==interrupted[k] for k in ('a','x','y','d','dbr')),'hardware entry changed general registers')
    vectors=[(i,e) for i,e in enumerate(events) if e['kind']=='read' and e['bus_address'] in (0xFFEA,0xFFEB)]
    require([(e['bus_address'],e['value']) for _,e in vectors]==[(0xFFEA,0x20),(0xFFEB,0x80)],'actual native vector reads missing')
    require(after_i<vectors[0][0]<vectors[1][0]<entry_i,'vector scope')
    hardware_writes=[(i,e) for i,e in enumerate(events) if dummy_i<i<vectors[0][0] and e['kind']=='write']
    expected_four=[(0x7E0000+interrupted_sp,resume_pc>>16),(0x7E0000+interrupted_sp-1,(resume_pc>>8)&255),
                   (0x7E0000+interrupted_sp-2,resume_pc&255),(0x7E0000+interrupted_sp-3,saved_p)]
    require([(e['address'],e['value']) for _,e in hardware_writes]==expected_four,'four distinct exact hardware pushes')
    require([e['cpu']['sp'] for _,e in hardware_writes]==[interrupted_sp-i for i in range(4)],'hardware push live SP sequence')
    require([e['cpu'] for _,e in hardware_writes]==[dict(interrupted,sp=interrupted_sp-i) for i in range(4)],'hardware push CPU state changed')
    vector_cpu=dict(interrupted,k=0,sp=interrupted_sp-4,ps=(saved_p&~8)|4)
    require(all(e['cpu']==vector_cpu for _,e in vectors),'native vector read CPU state')
    require(all(e['exec_index']==request['exec_index'] for _,e in hardware_writes+vectors+dummy),'hardware operations not owned by selected completed instruction')
    require([e['address'] for i,e in exec_events if request_i<i<entry_i]==[0x8020],'NMI did not follow selected instruction directly')
    if code[case['nmi_trigger']-v2.CODE]==0x20:
        near=[e for i,e in enumerate(events) if after_i<i<dummy_i and e['kind']=='write'];ret=(case['nmi_trigger']+2)&65535
        require([(e['address'],e['value']) for e in near]==[(0x7E0000+trigger_cpu['sp'],ret>>8),(0x7E0000+trigger_cpu['sp']-1,ret&255)],'JSR near pushes not distinct from hardware')
    hardware_indices={i for i,_ in hardware_writes}
    hardware_indices.update(i for i,_ in vectors+dummy+conditional_idle)
    handler_epochs=validate_handler(events,exec_events,interrupted,base['nmi_counter'])
    # The native Lua callback already refuses undeclared reads. Reapply that
    # scope in the host so an edited trace cannot add a retired-scratch or
    # other unrelated read while retaining a plausible final state.
    read_low=0x7E0000+sp-case['nmi_max_depth']+1;read_high=0x7E0000+sp+1
    for i,e in enumerate(events):
        if e['kind']!='read':continue
        address=e['address']
        if i in hardware_indices:continue
        if e['exec_index'] in handler_epochs:
            # validate_handler already requires its exact memory sequence.
            continue
        normal=(0x410000<=address<0x430000 or 0x7E3000<=address<0x7E3500 or
                0x7E9877<=address<0x7E9879 or 0x7EA0B3<=address<0x7EA0B5)
        stack=read_low<=address<read_high
        require(normal or stack,'undeclared helper data read')
        if stack:require((address&65535)>=e['cpu']['sp'],'stack read below pointwise live SP')
    require(events[entry_i-1]['kind']=='exec' and events[entry_i-1]['address']==0x8020,'entry is not pre-handler')
    require(events[rti_i-1]['kind']=='exec' and events[rti_i-1]['address']==0x802F and rti['stack'][:4]==hardware_frame and rti['cpu']['sp']==interrupted_sp-4,'pre-RTI frame')
    require(events[resume_i-1]['kind']=='exec' and events[resume_i-1]['address']==resume_pc,'actual RTI continuation absent')
    require(resume['cpu']==interrupted,'post-RTI CPU preservation')
    require(min(e['cpu']['sp'] for e in events)==sp-case['nmi_max_depth'],'complete observed combined stack depth')
    counter_writes=[e for e in events if e['kind']=='write' and 0x7E5EF0<=e['address']<0x7E5EF2]
    counter=(base['nmi_counter']+1)&65535
    require([(e['address'],e['value']) for e in counter_writes]==[(0x7E5EF0,counter&255),(0x7E5EF1,counter>>8)] and all(e['exec_index'] in handler_epochs for e in counter_writes),'single handler counter write')
    require(resume['nmi_counter']==events[-1]['nmi_counter']==counter,'counter readback')
    writes=[e for e in events if e['kind']=='write'];patches=dict(case['patches']);last={}
    outputs=dict(case['expected_writes']);low=0x7E0000+sp-case['nmi_max_depth']+1;high=0x7E0000+sp+1
    for e in writes:
        address,value=e['address'],e['value']
        require(type(value) is int and 0<=value<=255 and (low<=address<high or address in outputs or 0x7E5EF0<=address<0x7E5EF2),'undeclared CPU write')
        if low<=address<high:require((address&65535)>=e['cpu']['sp'] and sp-case['nmi_max_depth']<=e['cpu']['sp']<=sp,'pointwise stack floor/liveness')
        last[address]=value
    require(type(row['changes']) is list and len(row['changes'])<=0x20000,'full WRAM diff list/extent')
    previous_address=-1
    for change in row['changes']:
        require(type(change) is list and len(change)==2 and type(change[0]) is int and 0x7E0000<=change[0]<0x800000
                and type(change[1]) is int and 0<=change[1]<=255 and change[0]>previous_address,'full WRAM diff exact address-byte schema/order')
        previous_address=change[0]
    require(row['changes']==[[a,b] for a,b in sorted(last.items()) if b!=patches.get(a,0xA5)],'entire final WRAM diff lacks complete write ledger')
    # Reuse v2's independent helper contract on a declared helper-only projection.
    # Its derived diff is not the native full diff above; interrupted free stack
    # bytes can legitimately retain handler writes after the helper finishes.
    helpers=[e for _,e in exec_events if e['address'] not in HANDLER_PCS]
    epoch_map={e['exec_index']:i+1 for i,e in enumerate(helpers)}
    helper_memory=[e for i,e in enumerate(events) if e['kind'] in ('read','write') and e['exec_index'] in epoch_map and i not in hardware_indices]
    hwrites=[[e['address'],e['value']] for e in helper_memory if e['kind']=='write'];hfinal=dict(hwrites)
    pcs=[e['address'] for e in helpers];spos=[[i+1,e['address'],e['cpu']['sp']] for i,e in enumerate(helpers) if i>0 and code[pcs[i-1]-v2.CODE] in v2.SP_CHANGING_OPCODES]
    accesses=[[epoch_map[e['exec_index']],e['address'],e['value'],e['cpu']['sp'],int(e['kind']=='write')] for e in helper_memory if case['stack_span'][0]<=e['address']<case['stack_span'][1]]
    projection={k:row[k] for k in ('name','route','input_fixture_before_hex','input_fixture_after_hex','retired_scratch_before_hex','retired_scratch_after_hex')}
    projection.update(cpu={k:events[-1]['cpu'][k] for k in case['expected_cpu']},instructions=len(pcs),exec_addresses=pcs,
        writes=hwrites,changes=[[a,b] for a,b in sorted(hfinal.items()) if b!=patches.get(a,0xA5)],
        rom_reads=[[e['address'],e['value']] for e in helper_memory if e['kind']=='read' and 0x410000<=e['address']<0x430000],
        reads_total=sum(e['kind']=='read' for e in helper_memory),stack_accesses=accesses,
        minimum_sp=min([sp]+[e['cpu']['sp'] for e in helpers]+[x[3] for x in accesses]),sp_observations=spos)
    v2.validate_record(projection,case,code=code)
    return {'name':case['name'],'events':len(events),'helper_execution_observations':len(helpers),'nmi_count':1,
        'vector_read_indices':[i for i,_ in vectors],'native_hardware_write_indices':[i for i,_ in hardware_writes],
        'conditional_instruction_idle_read_indices':[i for i,_ in conditional_idle],'hardware_dummy_read_index':dummy_i,
        'handler_entry_index':entry_i,'pre_rti_index':rti_i,'post_rti_index':resume_i,'minimum_sp':sp-case['nmi_max_depth'],
        'boundary':case['nmi_boundary'],'interrupted_cpu':interrupted,'helper_depth_at_interrupt':case['nmi_depth_after'],
        'counter_before':base['nmi_counter'],'counter_after':counter,'whole_wram_diff_reconciled':True,'helper_projection_passed_v2':True}


def run(output_dir:Path,repetition:int=1,scope:str='pilot')->dict:
    require(repetition in (1,2),'repetition must be1or2')
    phase_reference=ROOT/'references/mesen_nmi_phase_contract_v2.json'
    phase_bytes=(json.dumps(phase_audit.collect(),indent=2)+'\n').encode()
    require(phase_bytes==phase_reference.read_bytes() and sha(phase_bytes)=='a948e62fa24c8be7520902ec3e0763bbaf3ae097409961c0f7474b77a0a54c5a','corrected phase prerequisite drift')
    private=SAFE.canonical_private_root();rom=SAFE.resolve_private_file(v2.DEFAULT_ROM,'original carrier',private_root=private)
    rom_bytes=v2.verified_rom_bytes();require(len(rom_bytes)==0x800000,'carrier extent')
    handler=rom_bytes[0x408020:0x408030]
    require(sha(handler)=='7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448','original handler identity')
    runtime={k:SAFE.resolve_private_file(SAFE.DEFAULT_MESEN.parent/n,k,private_root=private) for k,n in SAFE.RUNTIME_NAMES.items()}
    for k,p in runtime.items():SAFE.require_identity(p,k)
    output=SAFE.prepare_private_output_dir(output_dir,private_root=private,forbidden_roots=(rom.parent,SAFE.DEFAULT_MESEN.parent))
    guarded={**runtime,'rom':rom,'collector':COLLECTOR,'launcher':Path(__file__),'v2_library':Path(v2.__file__),
        'helper':v2.HELPER,'asar':v2.ASAR,'host_adapter':Path(v2.adapter.__file__),'isolation_library':Path(SAFE.__file__),
        'v0_library':Path(v2.prior.__file__),'v1_library':Path(v2.v1.__file__),
        'nmi_tests':ROOT/'tests/test_schala_package_helper_v2_nmi.py','phase_audit':Path(phase_audit.__file__),
        'prior_phase_audit':Path(phase_audit.prior.__file__),'phase_reference':phase_reference}
    before={k:SAFE.sha256_file(p) for k,p in guarded.items()};code=v2.assemble(output);cases=build_cases(rom_bytes,scope)
    require(sha(code)=='77dc3224baaa93077218d43d64cbef10bb55494a37057c1a5bfcf0d8fd6758f8','unchanged v2 helper binary required')
    validate_sites(cases,code)
    v2.validate_fixture_spans(cases,len(code));stage=output/'staged';app=stage/'app';saves=app/'Saves';saves.mkdir(parents=True)
    staged={}
    for k,n in SAFE.RUNTIME_NAMES.items():staged[k]=app/n;SAFE.copy_new_regular_file(runtime[k],staged[k],k)
    stem='pe_nmi_'+secrets.token_hex(12);staged['rom']=stage/(stem+'.sfc');SAFE.copy_new_regular_file(rom,staged['rom'],'rom')
    staged['sram']=saves/(stem+'.srm');staged['sram'].write_bytes(bytes(8192))
    staged['collector']=stage/'collector.lua';SAFE.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    payload={'schema':SCHEMA,'code_hex':code.hex(),'code':v2.CODE,'tails':v2.TAILS,'entry_bridge':v2.ENTRY_BRIDGE,
        'cases':[{k:value for k,value in c.items() if not k.startswith('expected_')} for c in cases]}
    staged['inputs']=stage/'inputs.lua';staged['inputs'].write_text('return '+v2.lua_value(payload)+'\n',encoding='utf-8',newline='\n')
    (output/'case_contract.json').write_bytes(canonical(cases));staged_before={k:SAFE.sha256_file(p) for k,p in staged.items()}
    for k in (*runtime,'rom','collector'):require(staged_before[k]==before[k],'staged source mismatch')
    archive=output/'source_archive';archive.mkdir()
    archive_paths={k:archive/guarded[k].name for k in ARCHIVE_KEYS}
    for k,path in archive_paths.items():SAFE.copy_new_regular_file(guarded[k],path,k)
    archive_before={k:SAFE.sha256_file(path) for k,path in archive_paths.items()};require_archive_hashes(archive_before,before)
    (output/'launch_inputs.json').write_bytes(canonical({'schema':SCHEMA,'status':'prepared; pilot not accepted','source_hashes':before,
        'staged_hashes':staged_before,'source_archive_hashes':archive_before,'helper_sha256':sha(code),'case_contract_sha256':SAFE.sha256_file(output/'case_contract.json')}))
    env=SAFE.minimal_subprocess_environment()
    for k,parts in {'USERPROFILE':('profile',),'APPDATA':('profile','AppData','Roaming'),'LOCALAPPDATA':('profile','AppData','Local'),'TEMP':('temp',),'TMP':('temp',)}.items():
        p=stage.joinpath(*parts);p.mkdir(parents=True,exist_ok=True);env[k]=str(p)
    env.update(PE_PACKAGE_PROTOCOL=SCHEMA,PE_PACKAGE_INPUT=str(staged['inputs']),PE_PACKAGE_TRACE=str(output/'trace.json'))
    native_timeout=120 if scope=='pilot' else 2400
    command=[str(staged['mesen']),'--testRunner',f'--timeout={native_timeout}','--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true',str(staged['collector']),str(staged['rom'])]
    proc=None;error=None
    try:
        proc=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=native_timeout+30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=False)
        (output/'process.log').write_bytes(proc.stdout+proc.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:error=str(exc)
    SAFE.require_file_hashes_unchanged(guarded,before,'source');SAFE.require_file_hashes_unchanged(staged,staged_before,'staged')
    require({p.name for p in archive.iterdir()}=={p.name for p in archive_paths.values()},'source archive inventory changed')
    SAFE.require_file_hashes_unchanged(archive_paths,archive_before,'source archive')
    require_archive_hashes({k:SAFE.sha256_file(SAFE.resolve_private_file(p,'source archive',private_root=private)) for k,p in archive_paths.items()},before)
    SAFE.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged['sram'].name)
    require(not error and proc is not None and proc.returncode==61,f'isolated native pilot failed: {error or (proc.returncode if proc else None)}; retained {output}')
    trace=SAFE.decode_json_object(SAFE.read_direct_regular_file(output/'trace.json','trace',parent=output,maximum=1024*1024*1024),'trace')
    require(trace['schema']==SCHEMA and trace['error'] is None and trace['partial_events']==[] and len(trace['records'])==len(cases),'trace completion')
    result=[validate_record(r,c,code,handler) for r,c in zip(trace['records'],cases,strict=True)]
    manifest={'schema':SCHEMA,'status':'exploratory pilot; not final matched acceptance','evidence_level':'verified-runtime','repetition':repetition,
        'source_hashes':before,'staged_hashes':staged_before,'source_archive_hashes':archive_before,
        'trace_sha256':SAFE.sha256_file(output/'trace.json'),'observations':result,'matrix_scope':scope,
        'helper_sha256':sha(code),'case_contract_sha256':SAFE.sha256_file(output/'case_contract.json'),
        'sources_and_staged_inputs_unchanged':True,'source_archives_unchanged':True,'cartridge_mutation':False,'manufactured_interrupt_frame':False,'internal_nmi_or_ppu_state_edit':False,
        'interrupt_scope':'single debugger-requested register-edge NMI per original fixture, natural VBlank latch','production_approval':False}
    (output/'manifest.json').write_bytes(canonical(manifest));return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--repetition',type=int,default=1)
    p.add_argument('--scope',choices=('pilot','boundary-pilot','matrix'),default='pilot')
    args=p.parse_args();print(json.dumps(run(args.output_dir,args.repetition,args.scope),indent=2))
