"""Strict, checkpoint-bounded naturally refused Cure observation validator.

Original host logic. No ROM, CPU execution, file mutation or native payload.
The memory ledger explains every sampled change in the watched regions with
an actual recorded write before accepting semantic MP/HP/queue witnesses.
"""
from __future__ import annotations
from collections import Counter
import re
from typing import Any

SCHEMA='project-epoch-package-natural-refusal-observation-v1'
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIMING_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
WRAM_KEYS={f'{a:04X}' for a in (0x0080,0x0082,0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,
    0x95D5,0x95DC,0x06E2,0x06E6,0x06E7,0xA43F,0x2980,0x2981,0x2982,0x0006,0x0007,0xAF22,0xAF23,
    0xB18B,0xB18C,0xB2EA,0xB2EB,0xB2EC,0xB3C8,0xB3F4,0xB3BA,0xB3BB,0xB3BC,0x0084,0x95DB,0x9EE3,0xA62D,0x9615,0xB2AE,0xA0D1,0xA0D2,0xA0D3)}
REGIONS={'battle_records':(0x5E2D,0x580),'queue':(0x93EE,21),'participant_map':(0xB1BE,7),
    'pending_results':(0xB18E,0x30),'target_result_work':(0xAD89,0xC3),'hp_pending_terms':(0xB328,0x84),
    'command_latches':(0xB188,3),'atb_mirror':(0x9F22,3),'menu_ready':(0xA6D9,7),'atb_rates':(0xAFAB,11),'atb_status':(0xB03A,11),'saved_rates':(0xB158,11)}
SITES={
    'queued-tech-entry':0xC1BB49,'target-validation-return':0xC1BB8B,'target-failure-jump':0xC1BB90,
    'pre-effect-boundary':0xC1BBD4,'effect-preparation-return':0xC1BBD7,
    'preparation-af23-branch':0xC1BBDA,'preparation-b3c8-branch':0xC1BBDF,
    'mp-participant0-call':0xC1BC01,'mp-participant0-return':0xC1BC04,
    'mp-participant1-call':0xC1BC0E,'mp-participant1-return':0xC1BC11,
    'mp-participant2-call':0xC1BC1B,'animation-result-call':0xC1BC1E,
    'mp-deduction-entry':0xC1CC71,'mp-deduction-rts':0xC1CCCA,
    'animation-wrapper-entry':0xC1AC57,'result-wrapper-entry':0xC1AC5A,
    'result-application-entry':0xC1EC7F,'hp-result-store':0xC1ECA0,'hp-result-store-readback':0xC1ECA3,
    'animation-result-return':0xC1BC21,'successful-table-clear':0xC1BC56,
    'shared-finalizer-call':0xC1BC5A,'shared-finalizer-entry':0xC1BDB3,
    'shared-finalizer-return':0xC1BC5D,'queue-release-entry':0xC1BCF8,'queue-release-rts':0xC1BD6E,
    'branch-producer-complete':0xC1409C,'resolver-entry':0xC14612,'resolver-tail':0xC1467F,
    'common-loader-entry':0xC14833,'common-loader-rts':0xC148EB,'dispatcher-rts':0xC1432B,
    'caller-resume':0xC140B0,'caller-package-latch':0xC140CE,'caller-effect-latch':0xC140E7,
    'terminal-command-clear':0xC14CF3,'sync-command-increment':0xC14D00}
SITES.update({'post-refusal-ready-readback':0xC11B83,'target-validation-entry':0xC1C1DD,'selected-target-status-read':0xC1C367,'selected-target-dead-jump':0xC1C36E,'target-validation-failure':0xC1C72B,'participant-mp-failure':0xC1D7B8,'disabled-pending-command-clear':0xC1B421,
    'menu-commit-entry':0xC1161A,'menu-queue-fields-written':0xC11713,'menu-commit-complete':0xC1172A,
    'target-hp-before-subtraction':0xC1EC99,'target-hp-subtraction-store':0xC1ECA0,'target-hp-subtraction-readback':0xC1ECA3,
    'target-status-before-death':0xC1ED04,'target-status-death-readback':0xC1ED0C,'target-hp-clamp-store':0xC1ED0F,'target-hp-clamp-readback':0xC1ED12})
EVENTS={'preselection-living-target','baseline','menu-observation','terminal'}
MEMORY={'prelude-memory-write','post-refusal-ready-write','transaction-memory-write','publication-write','latch-write'}
RECORD_KEYS={'kind','address','value','frame','cpu','stack','wram','timing','regions','transaction_id','transaction_active',
    'resolver_active','prelude_active','selector_word','branch_word','mask0_word','mask1_word','root_word'}
PRELUDE_WRITES=[(0x7E93EE,0x7E9403)]+[(0x7E5E30+i*128,0x7E5E38+i*128) for i in range(3)]+[(0x7E5E4A+i*128,0x7E5E4B+i*128) for i in range(3)]
WATCHED_WRITES=[(0x7EB188,0x7EB18B),(0x7E9F22,0x7E9F25),(0x7E93EE,0x7E9403),(0x7EB18E,0x7EB1BE),(0x7EAFAB,0x7EAFB6),
    (0x7EB03A,0x7EB045),(0x7EAF22,0x7EAF24)]+[(0x7E5E30+i*0x80,0x7E5E38+i*0x80) for i in range(11)]


class ObservationError(RuntimeError): pass


def require(condition:bool,message:str)->None:
    if not condition: raise ObservationError(message)


def integer(value:Any,low:int,high:int,name:str)->None:
    require(type(value) is int and low<=value<=high,'invalid integer '+name)


def exact(value:Any,keys:set[str],name:str)->None:
    require(type(value) is dict and set(value)==keys,'invalid exact object '+name)


def word(data:bytes,offset:int)->int: return int.from_bytes(data[offset:offset+2],'little')
def bankpc(r:dict)->int: return (r['cpu']['k']<<16)|r['cpu']['pc']
def region(r:dict,name:str)->bytes: return bytes.fromhex(r['regions'][name])
def hp(r:dict,slot:int)->int: return word(region(r,'battle_records'),slot*128+3)
def mp(r:dict,slot:int)->int: return word(region(r,'battle_records'),slot*128+7)
def participants(r:dict)->list[int]: return [r['wram'][k] for k in ('B2EA','B2EB','B2EC')]


def validate_shape(r:dict)->None:
    exact(r,RECORD_KEYS,'record'); kind=r['kind']
    require(type(kind) is str and kind in set(SITES)|EVENTS|MEMORY|{'transaction-caller-resume'},'unknown event kind')
    integer(r['address'],0,0xFFFFFF,'address'); integer(r['frame'],0,4000,'input poll')
    integer(r['transaction_id'],0,100,'transaction id')
    require(type(r['transaction_active']) is bool and type(r['resolver_active']) is bool and type(r['prelude_active']) is bool,'invalid active flag')
    for key in ('selector_word','branch_word','mask0_word','mask1_word','root_word'): integer(r[key],0,65535,key)
    exact(r['cpu'],CPU_KEYS,'CPU'); cpu=r['cpu']
    require(cpu['emulationMode'] is False,'native mode required')
    for k in CPU_KEYS-{'emulationMode'}: integer(cpu[k],0,255 if k in {'dbr','ps','k'} else 65535,'CPU '+k)
    require(type(r['stack']) is list and len(r['stack'])==16,'exact stack snapshot required')
    for b in r['stack']: integer(b,0,255,'stack byte')
    exact(r['wram'],WRAM_KEYS,'WRAM')
    for b in r['wram'].values(): integer(b,0,255,'WRAM byte')
    exact(r['regions'],set(REGIONS),'regions')
    for name,(_,size) in REGIONS.items():
        value=r['regions'][name]
        require(type(value) is str and len(value)==size*2 and re.fullmatch('[0-9a-f]*',value) is not None,'invalid region '+name)
    exact(r['timing'],TIMING_KEYS,'timing'); t=r['timing']
    for k,v in t.items(): integer(v,0,2**64-1,'timing '+k)
    require(t['masterClock']==(t['memoryManager.masterClock']&0xFFFFFFFF),'generic clock is not low 32 bits')
    require(t['frameCount']==t['ppu.frameCount'] and t['clockRate']==21477270,'wrong frame/clock basis')
    require(t['ppu.scanline']<263 and t['memoryManager.hClock']<=1364,'invalid raster position')
    for key,bytekey in (('selector_word','9877'),('branch_word','A0B3'),('mask0_word','0080'),('mask1_word','0082')):
        require(r[key]&255==r['wram'][bytekey],'inconsistent word/byte snapshot')
    if kind in SITES: require(r['address']==SITES[kind] and bankpc(r)==r['address'],'wrong execution site or CPU PC')
    elif kind=='transaction-caller-resume': require(bankpc(r)==r['address'],'wrong dynamic caller PC')
    elif kind in EVENTS: require(r['address']==0,'event address must be zero')
    elif kind=='transaction-memory-write': require(any(a<=r['address']<b for a,b in WATCHED_WRITES),'unwatched transaction write')
    elif kind=='prelude-memory-write': require(any(a<=r['address']<b for a,b in PRELUDE_WRITES),'unwatched prelude write')
    elif kind=='post-refusal-ready-write': require(r['address']==0x7EA6DA,'wrong future actor ready address')
    elif kind=='latch-write': require(r['address'] in (0x7E9876,0x7E5D9B),'unwatched latch write')
    elif kind=='publication-write': require(0x7E5DAC<=r['address']<0x7E5DFD,'unwatched publication')
    if kind in MEMORY: integer(r['value'],0,255,'write value')
    else: require(type(r['value']) is int and r['value']==-1,'non-write sentinel required')


def watched_snapshot(r:dict)->dict[int,int]:
    values={}
    for name in ('queue','pending_results','atb_rates','atb_status','command_latches','atb_mirror'):
        start,_=REGIONS[name]
        values.update({0x7E0000+start+i:v for i,v in enumerate(region(r,name))})
    b=region(r,'battle_records')
    for slot in range(11):
        for offset in range(3,11): values[0x7E5E2D+slot*128+offset]=b[slot*128+offset]
    for k in ('AF22','AF23','9876','5D9B'): values[0x7E0000+int(k,16)]=r['wram'][k]
    return values


def prelude_snapshot(r):
    values={0x7E93EE+i:b for i,b in enumerate(region(r,'queue'))}
    data=region(r,'battle_records')
    for slot in range(3):
        for offset in (*range(3,11),29):
            values[0x7E5E2D+slot*128+offset]=data[slot*128+offset]
    return values


def abi(r, *, width=0x20, x=None, y=None):
    c=r['cpu']
    require(c['d']==0 and c['dbr']==0x7E and c['ps']&0x30==width and c['ps']&8==0,'wrong WRAM addressing/width/binary-arithmetic ABI')
    if x is not None: require(c['x']==x,'wrong indexed base')
    if y is not None: require(c['y']==y,'wrong secondary index')


def summarize(trace):
    exact(trace,{'schema','error','records'},'trace')
    require(trace['schema']==SCHEMA and trace['error'] is None,'collector rejected')
    rows=trace['records']; require(type(rows) is list and 2<=len(rows)<=16384,'record bound')
    for r in rows: validate_shape(r)
    bykind={k:[i for i,r in enumerate(rows) if r['kind']==k] for k in {r['kind'] for r in rows}}
    def one(kind):
        ix=bykind.get(kind,[]); require(len(ix)==1,'exactly one '+kind+' required'); return ix[0],rows[ix[0]]
    def ordered(kinds):
        indices=[one(k)[0] for k in kinds]
        require(indices==sorted(set(indices)),'wrong ordered boundary sequence'); return indices
    bi,base=one('baseline'); ti,terminal=one('terminal')
    require(bi==0 and base['frame']==0 and ti==len(rows)-1 and terminal['frame']==4000,'baseline/terminal mismatch')
    require([rows[i]['frame'] for i in bykind.get('menu-observation',[])]==[2320,2390,2410,2600,3000],'fixed menu schedule mismatch')
    pre,selection=one('preselection-living-target'); begin,entry=one('queued-tech-entry'); end,caller=one('transaction-caller-resume')
    require(pre<begin<end and selection['frame']==2435,'wrong observed prelude/transaction')
    seq=['queued-tech-entry','target-validation-entry','selected-target-status-read','selected-target-dead-jump',
         'target-validation-failure','target-validation-return','target-failure-jump','shared-finalizer-call',
         'shared-finalizer-entry','shared-finalizer-return','queue-release-entry','queue-release-rts','transaction-caller-resume']
    ordered(seq)
    preseq=['preselection-living-target','menu-commit-entry','menu-queue-fields-written','menu-commit-complete',
            'target-hp-before-subtraction','target-hp-subtraction-store','target-hp-subtraction-readback',
            'target-status-before-death','target-status-death-readback','target-hp-clamp-store','target-hp-clamp-readback','queued-tech-entry']
    ordered(preseq)
    allowed=set(seq)|set(preseq)|EVENTS|{'transaction-memory-write','prelude-memory-write','post-refusal-ready-write','post-refusal-ready-readback'}
    require(set(bykind)<=allowed,'forbidden effect/MP/resolver/result or unscoped site observed')
    previous=(-1,)*4; preledger=ledger=None
    for i,r in enumerate(rows):
        t=r['timing']; counters=(t['memoryManager.masterClock'],t['cpu.cycleCount'],t['ppu.frameCount'],r['frame'])
        require(all(a>=b for a,b in zip(counters,previous)),'clock/cycle/frame/poll reversal'); previous=counters
        require(r['transaction_id']==(0 if i<begin else 1) and r['transaction_active']==(begin<=i<=end),'transaction identity/window')
        require(r['prelude_active']==(pre<=i<begin) and r['resolver_active'] is False,'prelude/resolver window')
        if pre<=i<=begin:
            current=prelude_snapshot(r)
            if preledger is not None: require(current==preledger,'prelude change lacks actual write')
            preledger=current
            if r['kind']=='prelude-memory-write': preledger[r['address']]=r['value']
        elif r['kind']=='prelude-memory-write': require(False,'prelude write outside scope')
        if begin<=i<=end:
            current=watched_snapshot(r)
            if ledger is not None: require(current==ledger,'transaction change lacks actual write')
            ledger=current
            if r['kind']=='transaction-memory-write': ledger[r['address']]=r['value']
        elif r['kind']=='transaction-memory-write': require(False,'transaction write outside scope')
        if r['kind'] in set(seq): require(begin<=i<=end,'transaction site outside invocation')
        if r['kind'] in set(preseq)-{'queued-tech-entry'}: require(pre<=i<begin,'prelude site outside scope')
        if r['kind']=='post-refusal-ready-write': require(i>end and r['value']==1,'premature ready witness')
    require([base['wram'][k] for k in ('2980','2981','2982')]==[0,1,2],'wrong party')
    require(hp(selection,2)==187 and region(selection,'battle_records')[2*128+29]&0x80==0,'target must be living before confirmation')
    require(selection['wram']['A62D']==2 and selection['wram']['9EE3']==12 and selection['wram']['95D5']==1,'selected Cure/actor/target mismatch')
    ci,commit=one('menu-commit-entry'); fi,fields=one('menu-queue-fields-written'); co,complete=one('menu-commit-complete')
    for r in (commit,fields,complete): abi(r)
    require(hp(commit,2)>0 and region(commit,'battle_records')[2*128+29]&0x80==0,'menu confirmation target already dead')
    writes=[r for r in rows[ci:fi] if r['kind']=='prelude-memory-write']
    expected=[(0x7E93F5,0x41,0xC116F5),(0x7E93F6,0x20,0xC116FD),(0x7E93F7,1,0xC11703),
              (0x7E93F8,2,0xC11709),(0x7E93FA,255,0xC1170E),(0x7E93FB,12,0xC11713)]
    require([(r['address'],r['value'],bankpc(r)) for r in writes]==expected,'actual menu queue commit mismatch')
    for r in writes: abi(r,x=7)
    for r in writes+[fields,complete]:
        require(r['cpu']['sp']==commit['cpu']['sp'] and r['stack']==commit['stack'],'menu commit stack frame drift')
    require(region(fields,'queue')[7:14]==bytes([0x41,0x20,1,2,0,255,12]),'queue fields lack immediate readback')
    # The selected target's own canonical subtraction, dead-status update and
    # clamp are scoped between this menu commit and this queued Cure entry.
    si,sub=one('target-hp-before-subtraction'); sti,store=one('target-hp-subtraction-store'); sri,readback=one('target-hp-subtraction-readback')
    for r in (sub,store,readback): abi(r,width=0,x=256,y=8)
    amount=word(region(sub,'hp_pending_terms'),8); difference=(hp(sub,2)-amount)&65535
    require(hp(sub,2)==187 and amount==192 and difference==65531,'unexpected selected target subtraction')
    require(store['cpu']['a']==difference and hp(readback,2)==difference,'subtraction accumulator/readback')
    sw=[r for r in rows[sti:sri] if r['kind']=='prelude-memory-write']
    require([(r['address'],r['value'],bankpc(r)) for r in sw]==[(0x7E5F30,251,0xC1ECA3),(0x7E5F31,255,0xC1ECA3)],'subtraction actual byte writes')
    for r in sw: abi(r,width=0,x=256,y=8); require(r['cpu']['a']==difference,'subtraction write A')
    di,dead=one('target-status-before-death'); dri,dead_read=one('target-status-death-readback')
    abi(dead,x=256,y=8); abi(dead_read,x=256,y=8)
    status=region(dead,'battle_records')[285]; require(status&128==0,'target death already present')
    dw=[r for r in rows[di:dri] if r['kind']=='prelude-memory-write']
    require([(r['address'],r['value'],bankpc(r)) for r in dw]==[(0x7E5F4A,status|128,0xC1ED0C)],'actual target dead-status write')
    abi(dw[0],x=256,y=8)
    require(region(dead_read,'battle_records')[285]==status|128,'dead-status readback')
    cli,clamp=one('target-hp-clamp-store'); cri,clamp_read=one('target-hp-clamp-readback')
    for r in (clamp,clamp_read): abi(r,width=0,x=256,y=8)
    cw=[r for r in rows[cli:cri] if r['kind']=='prelude-memory-write']
    require([(r['address'],r['value'],bankpc(r)) for r in cw]==[(0x7E5F30,0,0xC1ED12),(0x7E5F31,0,0xC1ED12)],'actual zero clamp byte writes')
    for r in cw: abi(r,width=0,x=256,y=8); require(r['cpu']['a']==0,'clamp write A')
    require(sub['cpu']['sp']==0x6E3 and sub['stack'][:4]==[0x87,0xAC,0x5C,0xAC],'enemy result near frame')
    for r in [store,readback,dead,dead_read,clamp,clamp_read]+sw+dw+cw:
        require(r['cpu']['sp']==sub['cpu']['sp'] and r['stack']==sub['stack'],'target damage/death frame continuity')
    require(hp(clamp_read,2)==hp(entry,2)==0 and region(entry,'battle_records')[285]&128,'dead target not preserved to queued execution')
    # Exact near frames and live D/DBR/M/X at the rejection and cleanup sites.
    sp=entry['cpu']['sp']; stack=entry['stack']
    require(sp==0x6EA and stack[:4]==[0xE9,0x85,0x35,0x83],'queued near-call frame')
    abi(entry,x=0x93F5)
    require(entry['wram']['0006']|(entry['wram']['0007']<<8)==0x93F5,'queued record pointer')
    q=region(entry,'queue'); require(q[7:14]==bytes([1,0x20,1,2,0,255,12]),'same queued Cure row missing')
    for kind in seq[1:-1]:
        _,r=one(kind); abi(r)
        inner=kind in {'target-validation-entry','selected-target-status-read','selected-target-dead-jump','target-validation-failure','shared-finalizer-entry'}
        expected_stack=([0x5C,0xBC] if kind=='shared-finalizer-entry' else [0x8A,0xBB])+stack[:14] if inner else stack
        require(r['cpu']['sp']==sp-(2 if inner else 0) and r['stack']==expected_stack,'near frame changed at '+kind)
        if kind!='target-validation-entry':
            require(participants(r)==[1,255,255],'resolved participant binding changed')
        require(region(r,'participant_map')==bytes([0,1,2,255,255,255,255]),'participant map changed')
        require(r['wram']['B18C']==12 and r['wram']['B18B']==1,'queued action identity changed')
    _,statusread=one('selected-target-status-read'); _,dead_jump=one('selected-target-dead-jump')
    abi(statusread,x=256); abi(dead_jump,x=256)
    require(dead_jump['cpu']['a']==128 and dead_jump['cpu']['ps']&2==0,'selected target death branch not taken')
    _,fail=one('target-validation-failure'); ri,ret=one('target-validation-return')
    require(fail['wram']['AF23']==0 and ret['wram']['AF23']==1 and ret['cpu']['a']==1,'AF23 prewrite/readback')
    af=[(i,r) for i,r in enumerate(rows) if begin<=i<=end and r['kind']=='transaction-memory-write' and r['address']==0x7EAF23]
    require([(r['value'],bankpc(r)) for _,r in af]==[(0,0xC1C1E1),(1,0xC1C730)],'AF23 actual write sequence')
    require(one('target-validation-entry')[0]<af[0][0]<one('target-validation-failure')[0]<af[1][0]<ri,'AF23 stores escaped validation call')
    for _,r in af: abi(r); require(r['cpu']['sp']==sp-2 and r['stack']==[0x8A,0xBB]+stack[:14],'AF23 store context')
    rate=region(entry,'saved_rates')[1]
    cleanup=[(0x7E93F5,0,0xC1BDCA),(0x7E93F6,0,0xC1BDCD),(0x7E93F7,0,0xC1BDD0),
        (0x7E93F8,0,0xC1BDD3),(0x7E93FB,0,0xC1BDD6),(0x7EB189,1,0xC1BDE3),(0x7EB189,0,0xC1BDE6),
        (0x7EAFAC,rate,0xC1BDEC),(0x7E9F23,rate,0xC1BDB2),(0x7EAFAC,rate,0xC1BE2A),
        (0x7E9F23,rate,0xC1BE2D),(0x7EB03B,1,0xC1BE37),(0x7EB189,0,0xC1BE3B),(0x7E93F5,0,0xC1BE4B),
        (0x7E93F6,0,0xC1BD0E),(0x7E93F7,0,0xC1BD11),(0x7E93F8,0,0xC1BD14),(0x7E93FB,0,0xC1BD17),
        (0x7E93FA,255,0xC1BD6B),(0x7EAF22,0,0xC1BD6E)]
    wi=[(i,r) for i,r in enumerate(rows) if begin<=i<=end and r['kind']=='transaction-memory-write']
    require([(r['address'],r['value'],bankpc(r)) for _,r in wi[2:]]==cleanup,'complete scoped cleanup write sequence')
    finalizer_frame=[0x5C,0xBC]+stack[:14]
    for index,r in wi[2:]:
        abi(r)
        if bankpc(r)==0xC1BDB2: depth,frame=4,[0xEE,0xBD]+finalizer_frame[:14]
        elif index<one('shared-finalizer-return')[0]: depth,frame=2,finalizer_frame
        else: depth,frame=0,stack
        require(r['cpu']['sp']==sp-depth and r['stack']==frame,'cleanup write call frame')
    for r in rows[begin:end+1]:
        require([hp(r,s) for s in range(11)]==[hp(entry,s) for s in range(11)] and [mp(r,s) for s in range(11)]==[mp(entry,s) for s in range(11)],'refusal changed HP or MP')
    require(region(caller,'queue')[:7]==q[:7] and region(caller,'queue')[14:]==q[14:] and region(caller,'queue')[7:14]==bytes([0,0,0,0,0,255,0]),'queue cleanup changed wrong records')
    require(region(caller,'pending_results')==region(entry,'pending_results'),'refusal changed pending results')
    require(region(caller,'command_latches')[1]==0 and region(caller,'atb_status')[1]==1 and caller['wram']['AF22']==0,'participant/ATB release incomplete')
    require(region(caller,'atb_rates')[1]==region(entry,'saved_rates')[1] and region(caller,'atb_mirror')[1]==region(caller,'atb_rates')[1],'ATB rate/mirror restoration mismatch')
    _,rts=one('queue-release-rts'); abi(caller,x=0x93F5)
    expected_caller=0xC10000|((word(bytes(rts['stack']),0)+1)&65535)
    require(caller['address']==expected_caller==0xC185EA and caller['cpu']['sp']==sp+2 and caller['stack'][:14]==rts['stack'][2:],'actual dynamic RTS return/frame')
    require(all(caller['cpu'][k]==rts['cpu'][k] for k in ('a','x','y','d','dbr','ps')),'RTS register continuity')
    ready_i,ready=one('post-refusal-ready-write'); ready_read_i,ready_read=one('post-refusal-ready-readback')
    require(end<ready_i<ready_read_i and ready_read_i==ready_i+1,'ready write/readback order')
    require(bankpc(ready)==0xC11B83 and ready['cpu']['a']==1 and region(ready,'menu_ready')[1]==255,'ready list insertion source')
    for r in (ready,ready_read): abi(r,x=1)
    require(region(ready_read,'menu_ready')[1]==1 and region(ready_read,'atb_status')[1]==0x81,'ready list/readback status')
    require(ready_read['cpu']==ready['cpu'] and ready_read['stack']==ready['stack'],'ready store/readback CPU frame continuity')
    return {'status':'validated-checkpoint-bounded-natural-Cure-refusal' ,'record_count':len(rows),
        'transaction_id':1,'preselection_index':pre,'queued_entry_index':begin,'caller_return_index':end,
        'polls':{k:rows[one(k)[0]]['frame'] for k in dict.fromkeys(preseq+seq)},
        'target_slot':2,'actor_slot':1,'canonical_tech_id':12,'target_hp_before':hp(selection,2),'pending_damage':amount,
        'target_hp_wrapped_subtraction':difference,'target_hp_after_clamp':0,'af23_write_indices':[i for i,_ in af],
        'transaction_actual_write_count':len(bykind.get('transaction-memory-write',[])),
        'pc_mp_before':[mp(entry,s) for s in range(3)],'pc_mp_after':[mp(caller,s) for s in range(3)],
        'queue_selected_record_released':True,'other_queue_records_unchanged':True,
        'prelude_and_transaction_watched_ledgers_reconciled':True,'no_effect_preparation_mp_charge_resolver_or_result_dispatch_in_invocation':True,
        'entry_sp':sp,'caller_sp':caller['cpu']['sp'],'caller_cpu_address':f'{expected_caller:06X}',
        'transaction_master_clocks':caller['timing']['memoryManager.masterClock']-entry['timing']['memoryManager.masterClock'],
        'post_refusal_ready':{'write_index':ready_i,'readback_index':ready_read_i,'poll':ready['frame'],'actor_slot':1,'menu_ready_value':1,'subsequent_command_not_executed':True},
        'limits':['one fixed natural dead-target refusal; not a helper cancellation adapter',
            'ledger covers declared ranges only, not all WRAM','pre-execution snapshots plus actual byte stores, not independent operand bus reads',
            'future ready-list insertion is observed; a subsequent command is not executed','no game mutation, installed helper, allocation, high binding or PC07']}
