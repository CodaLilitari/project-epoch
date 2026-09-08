"""Strict, checkpoint-bounded successful queued-Tech observation validator.

Original host logic. No ROM, CPU execution, file mutation or native payload.
The memory ledger explains every sampled change in the watched regions with
an actual recorded write before accepting semantic MP/HP/queue witnesses.
"""
from __future__ import annotations
from collections import Counter
import re
from typing import Any

SCHEMA='project-epoch-package-transaction-observation-v1'
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIMING_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
WRAM_KEYS={f'{a:04X}' for a in (0x0080,0x0082,0x5D9B,0x9876,0x9877,0xA0B3,0xAE91,0xAE92,0xAE93,0xAE94,
    0x95D5,0x95DC,0x06E2,0x06E6,0x06E7,0xA43F,0x2980,0x2981,0x2982,0x0006,0x0007,0xAF22,0xAF23,
    0xB18B,0xB18C,0xB2EA,0xB2EB,0xB2EC,0xB3C8,0xB3F4,0xB3BA,0xB3BB,0xB3BC)}
REGIONS={'battle_records':(0x5E2D,0x580),'queue':(0x93EE,21),'participant_map':(0xB1BE,7),
    'pending_results':(0xB18E,0x30),'target_result_work':(0xAD89,0xC3),'hp_pending_terms':(0xB328,0x84),
    'atb_rates':(0xAFAB,11),'atb_status':(0xB03A,11),'saved_rates':(0xB158,11)}
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
EVENTS={'baseline','menu-observation','terminal'}
MEMORY={'transaction-memory-write','publication-write','latch-write'}
RECORD_KEYS={'kind','address','value','frame','cpu','stack','wram','timing','regions','transaction_id','transaction_active',
    'resolver_active','selector_word','branch_word','mask0_word','mask1_word','root_word'}
WATCHED_WRITES=[(0x7E93EE,0x7E9403),(0x7EB18E,0x7EB1BE),(0x7EAFAB,0x7EAFB6),
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
    integer(r['address'],0,0xFFFFFF,'address'); integer(r['frame'],0,1200,'input poll')
    integer(r['transaction_id'],0,100,'transaction id')
    require(type(r['transaction_active']) is bool and type(r['resolver_active']) is bool,'invalid active flag')
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
    elif kind=='latch-write': require(r['address'] in (0x7E9876,0x7E5D9B),'unwatched latch write')
    elif kind=='publication-write': require(0x7E5DAC<=r['address']<0x7E5DFD,'unwatched publication')
    if kind in MEMORY: integer(r['value'],0,255,'write value')
    else: require(type(r['value']) is int and r['value']==-1,'non-write sentinel required')


def watched_snapshot(r:dict)->dict[int,int]:
    values={}
    for name in ('queue','pending_results','atb_rates','atb_status'):
        start,_=REGIONS[name]
        values.update({0x7E0000+start+i:v for i,v in enumerate(region(r,name))})
    b=region(r,'battle_records')
    for slot in range(11):
        for offset in range(3,11): values[0x7E5E2D+slot*128+offset]=b[slot*128+offset]
    for k in ('AF22','AF23','9876','5D9B'): values[0x7E0000+int(k,16)]=r['wram'][k]
    return values


def summarize(trace:dict[str,Any])->dict[str,Any]:
    exact(trace,{'schema','error','records'},'trace')
    require(trace['schema']==SCHEMA and trace['error'] is None,'collector schema or execution failure')
    records=trace['records']; require(type(records) is list and 2<=len(records)<=16384,'invalid record count')
    for r in records: validate_shape(r)
    require(records[0]['kind']=='baseline' and records[0]['frame']==0 and records[-1]['kind']=='terminal' and records[-1]['frame']==1200,'missing baseline/terminal')
    bykind={k:[i for i,r in enumerate(records) if r['kind']==k] for k in set(r['kind'] for r in records)}
    def one(kind:str)->tuple[int,dict]:
        indices=bykind.get(kind,[]); require(len(indices)==1,'exactly one '+kind+' required')
        return indices[0],records[indices[0]]
    one('baseline'); one('terminal')
    require([records[i]['frame'] for i in bykind.get('menu-observation',[])]==[40,80,120,160],'wrong menu/input evidence')
    begin,entry=one('queued-tech-entry'); end,caller=one('transaction-caller-resume')
    require(begin<end,'reversed transaction')
    require(not bykind.get('target-failure-jump'),'successful observation cannot contain target failure')
    previous=(-1,-1,-1,-1)
    resolver=False; ledger=None
    for i,r in enumerate(records):
        timing=r['timing']; counters=(timing['memoryManager.masterClock'],timing['cpu.cycleCount'],timing['ppu.frameCount'],r['frame'])
        require(all(a>=b for a,b in zip(counters,previous)),'clock/cycle/frame/poll reversal'); previous=counters
        active=begin<=i<=end
        require(r['transaction_id']==(0 if i<begin else 1) and r['transaction_active']==active,'transaction identity/window mismatch')
        if r['kind']=='resolver-entry': require(not resolver,'nested resolver'); resolver=True
        require(r['resolver_active']==resolver,'resolver window mismatch')
        if r['kind']=='resolver-tail': require(resolver,'unpaired resolver tail'); resolver=False
        if r['kind']=='publication-write': require(resolver,'publication outside resolver')
        if not active:
            require(r['kind'] in EVENTS,'transaction event outside owned invocation'); continue
        current=watched_snapshot(r)
        if ledger is not None: require(current==ledger,'watched snapshot change lacks matching actual write')
        ledger=current
        if r['kind'] in ('transaction-memory-write','latch-write'): ledger[r['address']]=r['value']
    require(not resolver,'open resolver at terminal')
    sequence=['queued-tech-entry','target-validation-return','pre-effect-boundary','effect-preparation-return',
        'preparation-af23-branch','preparation-b3c8-branch','mp-participant0-call','mp-participant0-return',
        'mp-participant1-call','mp-participant1-return','mp-participant2-call','animation-result-call',
        'animation-wrapper-entry','branch-producer-complete','resolver-entry','resolver-tail','common-loader-entry',
        'common-loader-rts','dispatcher-rts','caller-effect-latch','result-wrapper-entry','result-application-entry',
        'animation-result-return','successful-table-clear','shared-finalizer-call','shared-finalizer-entry',
        'shared-finalizer-return','queue-release-entry','queue-release-rts','transaction-caller-resume']
    ordered=[one(k)[0] for k in sequence]
    require(ordered==sorted(ordered) and len(set(ordered))==len(ordered),'transaction boundary order mismatch')
    base_sp=entry['cpu']['sp']; base_stack=entry['stack']
    require(base_sp==0x06EA and base_stack[:4]==[0xD0,0x85,0x35,0x83],'unexpected queued entry frame')
    require(entry['cpu']['d']==0 and entry['cpu']['dbr']==0x7E and entry['cpu']['ps']&0x30==0x20,'queued entry ABI')
    require(entry['wram']['0006']|(entry['wram']['0007']<<8)==0x93EE,'queued pointer is not supported first record')
    require(entry['cpu']['x']==0x93EE,'queued pointer X mismatch')
    q0=region(entry,'queue'); require(q0[:7]==bytes([1,0x20,1,3,0,0xFF,8]),'unexpected queued supported Tech record')
    for kind in ('target-validation-return','pre-effect-boundary','effect-preparation-return','preparation-af23-branch',
        'preparation-b3c8-branch','mp-participant0-call','mp-participant0-return','mp-participant1-call','mp-participant1-return',
        'mp-participant2-call','animation-result-call','animation-result-return','successful-table-clear',
        'shared-finalizer-call','shared-finalizer-return','queue-release-entry','queue-release-rts'):
        _,r=one(kind)
        require(r['cpu']['sp']==base_sp and r['stack']==base_stack,'outer transaction frame changed at '+kind)
        require(r['cpu']['d']==0 and r['cpu']['dbr']==0x7E and r['cpu']['ps']&0x30==0x20,'outer boundary ABI at '+kind)
        require((r['wram']['0006']|(r['wram']['0007']<<8))==0x93EE,'queue pointer drift at '+kind)
    target_i,target=one('target-validation-return'); pre_i,pre=one('pre-effect-boundary'); prepared_i,prepared=one('effect-preparation-return')
    require(pre['cpu']['a']==0 and pre['cpu']['x']==0 and pre['cpu']['y']==3 and pre['cpu']['ps']==0x22,'exact pre-effect ABI mismatch')
    require(participants(target)==[0,255,255] and participants(pre)==[0,255,255],'target participant contract')
    require(pre['wram']['B18C']==8 and pre['wram']['B18B']==0 and [pre['wram'][k] for k in ('AE91','AE92','AE93','AE94')]==[0,2,8,0],'pre-effect identity/config contract')
    require(region(pre,'participant_map')==bytes([0,1,2,255,255,255,255]),'supported participant mapping contract')
    for kind in ('target-validation-return','preparation-af23-branch','preparation-b3c8-branch'):
        _,r=one(kind); require(r['wram']['AF23']==0 and r['wram']['B3C8']==0,'preparation failure flag on successful route')
    # Exact deduction scopes: a call, its own near frame, byte writes, pre-RTS
    # state, then its specific caller continuation. Other calls cannot donate it.
    deductions=[]
    require(len(bykind.get('mp-deduction-entry',[]))==3 and len(bykind.get('mp-deduction-rts',[]))==3,'three MP deductions required')
    all_mp_addresses={0x7E5E34+i*128+j for i in range(11) for j in (0,1)}
    for pos,(callname,returnname) in enumerate((('mp-participant0-call','mp-participant0-return'),('mp-participant1-call','mp-participant1-return'),('mp-participant2-call','animation-result-call'))):
        ci,c=one(callname); ri,ret=one(returnname)
        ins=[j for j in bykind['mp-deduction-entry'] if ci<j<ri]; outs=[j for j in bykind['mp-deduction-rts'] if ci<j<ri]
        require(len(ins)==len(outs)==1 and ins[0]<outs[0],'unpaired MP participant call')
        enter,leave=records[ins[0]],records[outs[0]]
        expected_frame=list((SITES[returnname]-1).to_bytes(3,'little')[:2])+base_stack[:14]
        for r in (enter,leave): require(r['cpu']['sp']==base_sp-2 and r['stack']==expected_frame and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E and r['cpu']['ps']&0x30==0x20,'MP near-call frame/ABI mismatch')
        require(all(c['cpu'][k]==enter['cpu'][k] and leave['cpu'][k]==ret['cpu'][k] for k in ('a','x','y','d','dbr','ps')),'MP call/RTS register continuity mismatch')
        require(enter['cpu']['a']==c['cpu']['a']==[0,255,255][pos],'wrong MP participant argument')
        require(enter['cpu']['y']==c['cpu']['y']==[20,0,0][pos],'wrong MP cost argument')
        writes=[(j,r) for j,r in enumerate(records) if ins[0]<j<outs[0] and r['kind']=='transaction-memory-write' and r['address'] in all_mp_addresses]
        if pos==0:
            expected_mp=mp(enter,0)-20; require(expected_mp>=0,'invalid MP preflight')
            require([(r['address'],r['value']) for _,r in writes]==[(0x7E5E34,expected_mp&255),(0x7E5E35,expected_mp>>8)],'ordered participant MP byte writes missing')
            for _,r in writes: require(bankpc(r)==0xC1CC8F and r['cpu']['ps']&0x30==0 and r['cpu']['a']==expected_mp and r['cpu']['x']==0 and r['cpu']['sp']==base_sp-2 and r['stack']==expected_frame and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E,'MP write instruction/width/value mismatch')
            require(mp(leave,0)==mp(ret,0)==expected_mp,'MP post-write readback mismatch')
        else: require(not writes and [mp(enter,s) for s in range(11)]==[mp(leave,s) for s in range(11)],'absent participant changed MP')
        deductions.append({'participant_position':pos,'participant_id':c['cpu']['a'],'call_index':ci,'entry_index':ins[0],
            'rts_index':outs[0],'return_index':ri,'mp_before':mp(enter,0) if pos==0 else None,'mp_after':mp(leave,0) if pos==0 else None,
            'actual_write_indices':[j for j,_ in writes],'cost_argument':c['cpu']['y']})
    animation_i,animation=one('animation-result-call'); apply_i,apply=one('result-application-entry'); result_end_i,result_end=one('animation-result-return')
    wrapper_frame=[0x20,0xBC]+base_stack[:14]
    for kind,depth,frame in (('animation-wrapper-entry',2,wrapper_frame),('result-wrapper-entry',2,wrapper_frame),
            ('result-application-entry',6,[0x87,0xAC,0x5C,0xAC]+wrapper_frame[:12])):
        _,r=one(kind)
        require(r['cpu']['sp']==base_sp-depth and r['stack']==frame and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E and r['cpu']['ps']&0x30==0x20,'result wrapper frame/ABI mismatch')
    for i,r in enumerate(records[begin:end+1],begin):
        expected_first=mp(entry,0) if i<=deductions[0]['actual_write_indices'][0] else mp(entry,0)-20
        # A byte write's snapshot precedes that write. The high byte is zero in
        # this bounded primary fixture, so the following snapshots read the word.
        require(mp(r,0)==expected_first and mp(r,1)==mp(entry,1) and mp(r,2)==mp(entry,2),'PC MP changed outside the declared charge')
        if r['kind']=='transaction-memory-write' and r['address'] in all_mp_addresses:
            require(deductions[0]['entry_index']<i<deductions[0]['rts_index'] or apply_i<i<result_end_i,'MP write outside deduction/results scope')
    # Validate the first HP pass against its actual source terms, write callbacks,
    # and an immediate post-store execution snapshot for each of eleven battlers.
    stores=bykind.get('hp-result-store',[]); readbacks=bykind.get('hp-result-store-readback',[])
    require(len(stores)==len(readbacks)==11,'eleven HP first-pass stores/readbacks required')
    hp_witnesses=[]
    for slot,(si,bi) in enumerate(zip(stores,readbacks)):
        require(apply_i<si<bi<result_end_i and (slot==10 or bi<stores[slot+1]),'HP store/readback order mismatch')
        s,b=records[si],records[bi]; pending=region(s,'hp_pending_terms'); offset=slot*4
        require(s['cpu']['x']==b['cpu']['x']==slot*128 and s['cpu']['y']==b['cpu']['y']==offset,'HP battler index mismatch')
        for r in (s,b): require(r['cpu']['sp']==base_sp-6 and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E and r['cpu']['ps']&0x30==0,'HP store ABI mismatch')
        require(not word(pending,offset+2)&0x4000,'first HP pass is flagged to skip')
        amount=word(pending,offset); expected_hp=(hp(s,slot)-amount)&65535
        require(s['cpu']['a']==b['cpu']['a']==expected_hp,'pending HP subtraction does not match A')
        address=0x7E5E30+slot*128
        writes=[(j,r) for j,r in enumerate(records) if si<j<bi and r['kind']=='transaction-memory-write' and address<=r['address']<address+2]
        require([(r['address'],r['value']) for _,r in writes]==[(address,expected_hp&255),(address+1,expected_hp>>8)],'HP actual byte write witness missing')
        for r in (s,b): require(r['stack']==apply['stack'],'HP result frame changed')
        for _,r in writes: require(bankpc(r)==0xC1ECA3 and all(r['cpu'][k]==s['cpu'][k] for k in ('a','x','y','sp','d','dbr','ps')) and r['stack']==s['stack'],'HP write attributed to wrong instruction')
        require(hp(b,slot)==expected_hp and region(b,'hp_pending_terms')==pending,'HP post-store readback/source drift')
        hp_witnesses.append({'slot':slot,'store_index':si,'byte_write_indices':[j for j,_ in writes],'readback_index':bi,
            'hp_before':hp(s,slot),'pending_first_term':amount,'hp_after_first_store':expected_hp})
    # Resolver's two retained near frames are a nested subtransaction, not the
    # queue caller's return frame. All expected continuations are scoped here.
    resolver_i,resolver_entry=one('resolver-entry'); root_frame=resolver_entry['stack']
    require(resolver_entry['cpu']['sp']==base_sp-18 and root_frame[:4]==[0x2A,0x43,0xAF,0x40] and resolver_entry['cpu']['ps']&0x30==0,'resolver entry frame/width')
    require(resolver_entry['selector_word']==8 and resolver_entry['branch_word']==0,'unexpected primary resolver input')
    require(resolver_entry['cpu']['d']==0 and resolver_entry['cpu']['dbr']==0x7E,'resolver entry addressing context')
    for kind,delta in (('resolver-tail',0),('common-loader-entry',0),('common-loader-rts',0),('dispatcher-rts',2)):
        _,r=one(kind); require(r['cpu']['sp']==resolver_entry['cpu']['sp']+delta and r['cpu']['ps']&0x30==0x20 and r['stack'][:16-delta]==root_frame[delta:] and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E,'resolver return chain mismatch')
    resume=[i for i in bykind.get('caller-resume',[]) if one('dispatcher-rts')[0]<i<apply_i]
    require(resume,'resolver caller resume missing')
    r=records[resume[0]]; caller_frame=r['stack']
    require(r['cpu']['sp']==base_sp-14 and caller_frame[:12]==root_frame[4:] and caller_frame[-4:]==[0x20,0xBC]+base_stack[:2],'resolver caller frame mismatch')
    for kind in ('branch-producer-complete','caller-resume','caller-package-latch','caller-effect-latch'):
        for j in bykind.get(kind,[]):
            r=records[j]
            require(r['cpu']['sp']==base_sp-14 and r['stack']==caller_frame and r['cpu']['d']==0 and r['cpu']['dbr']==0x7E and r['cpu']['ps']&0x30==0x20,'animation caller context mismatch')
    effect_i,effect=one('caller-effect-latch')
    require(effect['wram']['5D9B']==0 and any(records[i]['wram']['9876'] for i in bykind.get('caller-package-latch',[]) if resolver_i<i<effect_i),'same-transaction completion latches missing')
    # Shared finalizer call and actual queue RTS return cannot be donated by the
    # later command which starts after this captured transaction has ended.
    fi,finalizer=one('shared-finalizer-entry'); fr_i,finalizer_ret=one('shared-finalizer-return')
    require(finalizer['cpu']['sp']==base_sp-2 and finalizer['stack']==[0x5C,0xBC]+base_stack[:14] and finalizer['cpu']['d']==0 and finalizer['cpu']['dbr']==0x7E and finalizer['cpu']['ps']&0x30==0x20,'finalizer near frame mismatch')
    for r in records[target_i:end+1]:
        require(participants(r)==[0,255,255] and region(r,'participant_map')==region(pre,'participant_map'),'participant identity changed within transaction')
        require(region(r,'queue')[7:]==q0[7:],'unrelated queue record changed in transaction')
    final_queue=bytes([0,0,0,0,0,255,0])+q0[7:]
    require(region(finalizer_ret,'queue')==final_queue and region(caller,'queue')==final_queue and caller['wram']['AF22']==0,'selected queue not released')
    queue_writes=[r for r in records[fi:end+1] if r['kind']=='transaction-memory-write' and 0x7E93EE<=r['address']<0x7E9403]
    require(queue_writes and all(r['address']<0x7E93F5 for r in queue_writes),'queue release wrote another record')
    clear_i,clear=one('successful-table-clear'); final_call_i,final_call=one('shared-finalizer-call')
    before_work=region(clear,'target_result_work'); after_work=region(final_call,'target_result_work')
    require(before_work[:0x12]==after_work[:0x12] and after_work[0x12:]==bytes(0xB1),'target-result table clear snapshot mismatch')
    rts_i,rts=one('queue-release-rts'); expected_caller=0xC10000|((word(bytes(rts['stack']),0)+1)&65535)
    require(caller['address']==expected_caller and caller['cpu']['sp']==base_sp+2 and caller['stack'][:14]==rts['stack'][2:],'actual transaction RTS caller/frame mismatch')
    require(all(caller['cpu'][k]==rts['cpu'][k] for k in ('a','x','y','d','dbr','ps')),'RTS caller register mismatch')
    require(rts['cpu']['x']==0x93EE,'queue return pointer mismatch')
    return {'record_count':len(records),'event_counts':dict(sorted(Counter(r['kind'] for r in records).items())),
        'transaction_count':1,'transaction_id':1,'queued_entry_index':begin,'caller_return_index':end,
        'entry_poll':entry['frame'],'caller_return_poll':caller['frame'],'entry_sp':base_sp,'caller_sp':caller['cpu']['sp'],
        'caller_cpu_address':f'{expected_caller:06X}','pre_effect_boundary':{'record_index':pre_i,'cpu':pre['cpu'],'queue_pointer':'7E93EE',
            'participant_ids':participants(pre),'action_id':8,'actor_slot':0,'selector_binding':'canonical action/config 08; no high package binding'},
        'mp_deductions':deductions,'pc_mp_before':[mp(entry,i) for i in range(3)],'pc_mp_after':[mp(caller,i) for i in range(3)],
        'hp_first_pass_witnesses':hp_witnesses,'hp_before_results':[hp(apply,i) for i in range(11)],'hp_after_results':[hp(result_end,i) for i in range(11)],
        'watched_snapshot_changes_explained_by_actual_writes':True,'resolver_entry_index':resolver_i,'resolver_branch_word':0,
        'selected_queue_released':True,'other_two_queue_records_unchanged_to_caller':True,'participants_unchanged_after_target_validation':True,
        'shared_finalizer_success_path_observed':True,'pending_result_application_observed':True,
        'boundary_cpu_contexts':{kind:records[one(kind)[0]]['cpu'] for kind in sequence},
        'target_result_clear_snapshot':{'preserved_start':'7EAD89','preserved_length':0x12,'zero_start':'7EAD9B','zero_length':0xB1,'actual_stores_not_watched':True},
        'limits':['fixed successful supported-PC action from a diagnostic checkpoint; no failure/refusal path executed',
            'first HP subtraction has direct operand/write/readback proof; later clamping and other result semantics remain outside that arithmetic claim',
            'memory ledger covers declared watched ranges, not every effect-preparation side effect',
            'three live party MP words observed; not all seven serialized playable-character records',
            'no installed helper, hook, production allocation, high binding, or PC07'],
        'timing_basis':'full memoryManager.masterClock; generic masterClock is low32; frame is input-poll ordinal'}
