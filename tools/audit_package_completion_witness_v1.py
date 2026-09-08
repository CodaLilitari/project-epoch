"""Reuse accepted vanilla completion observations; no native launch or writes.

Stop-handler target calculations are not owner-byte write/readback evidence.
The default-family execution site does not identify an encoded command byte.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import collect_package_transaction_evidence_v1 as evidence
import audit_schala_package_completion_contract_v1 as static_contract
import audit_package_cancellation_boundaries_v1 as cancellation

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'references/package_completion_witness_v1.json'
STATIC_REFERENCE=ROOT/'references/schala_package_completion_contract_v1.json'
STATIC_REFERENCE_SHA='76c5d5a157748717c42301a7cbfd9d00f9f656cdeba048415e77c123d7095766'
TRACE_SHA='fc9e89c139d00a23ab67a84ee77f497e6dfe63133c14509b23f50ce72d0523e7'
EVIDENCE_REFERENCE_SHA='1cc3030e1bbfe5f167ae69262ec7d78487ec4184e3500915b9dfbda94bea2787'
PINS={
 'accepted_collector':('tools/collect_package_transaction_evidence_v1.py',9491,'610ced62a320c9a0ae53efd0174ed4e1a661a4db63b1d0a43d15ca2c48a377b4'),
 'static_auditor':('tools/audit_schala_package_completion_contract_v1.py',9676,'76840c5b0edfea07e117745ee0dd70da77dd489eeabb406684d48f2177121214'),
 'cancellation_auditor':('tools/audit_package_cancellation_boundaries_v1.py',8894,'c3693afadfb6b1d46252e40c5d2c9db645879c56c9227f48b3ed3d98acfd1114'),
}
v=evidence.observer
CALLER_FRAME=[1,76,0,0,0,0,0,4,168,191,89,172,32,188,208,133]
OUTER_FRAME=[208,133,53,131,12,0,144,0,0,5,0,1,0,1,0,35]
LOOP_INDICES=tuple(i for i in range(77,1116) if i not in {181,982,993,1108,1113,1114})
LATCHES=(
 (49,0x7E5D9B,0,0xCCF071,376,0x6DA),(50,0x7E9876,0,0xCCF0EC,376,0x6DA),
 (73,0x7E5D9B,0,0xCD0D2B,388,0x6D5),(181,0x7E5D9B,1,0xC15938,466,0x6D6),
 (982,0x7E5D9B,0,0xCD1650,927,0x6C3),(1114,0x7E9876,1,0xC14D03,991,0x6D6),
 (1117,0x7E5D9B,0,0xCCF071,993,0x6DA),(1118,0x7E9876,0,0xCCF0EC,993,0x6DA),
)
EXTRA={49,50,51,73,74,181,982,993,1108,1113,1114,1116,1117,1118,1119,1120,1253,1275}
INDICES=tuple(sorted(set(LOOP_INDICES)|EXTRA))
ROW_KEYS={'index','kind','address','value','frame','cpu','stack','timing','latches','context'}
NONCLAIMS={
 'encoded_default_opcode_identified':False,'script_pointer_movement_observed':False,
 'owner_clear_write_observed':False,'owner_clear_readback_observed':False,
 'scene_write_isr_ownership_proved':False,'high_package_completion_proved':False,
 'production_approval':False,'new_native_execution':False,
}


class WitnessError(ValueError):pass


def require(condition,message):
    if not condition:raise WitnessError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def integer(value,lo,hi,name):require(type(value) is int and lo<=value<=hi,'invalid integer '+name)
def bankpc(r):return (r['cpu']['k']<<16)|r['cpu']['pc']


def read(path,maximum=16*1024*1024,expected=None,size=None):
    path=Path(path);info=path.lstat()
    require(path.is_absolute() and path.resolve(strict=True)==path and stat.S_ISREG(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400,'unaliasable regular source required')
    require(info.st_size<=maximum and (size is None or info.st_size==size),'bounded source size')
    with path.open('rb') as stream:raw=stream.read(maximum+1)
    require(len(raw)==info.st_size and len(raw)<=maximum,'source changed size')
    require(expected is None or sha(raw)==expected,'pinned source SHA differs')
    return raw


def identity(path,expected=None,size=None):
    raw=read(path,expected=expected,size=size)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':sha(raw)}


def decode(raw):
    def pairs(items):
        result={}
        for k,value in items:
            require(k not in result,'duplicate JSON key');result[k]=value
        return result
    def bad(value):raise WitnessError('non-finite JSON constant')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    require(type(value) is dict,'JSON object required');return value


def project(r,index):
    return {'index':index,'kind':r['kind'],'address':r['address'],'value':r['value'],'frame':r['frame'],
        'cpu':r['cpu'],'stack':r['stack'],'timing':r['timing'],
        'latches':{'package':r['wram']['9876'],'scene':r['wram']['5D9B']},
        'context':{'transaction_id':r['transaction_id'],'transaction_active':r['transaction_active'],
                   'resolver_active':r['resolver_active'],
                   'animation_identity':[r['wram'][k] for k in ('AE91','AE92','AE93','AE94')]}}


def validate_projection(rows):
    """Validate selected original host metadata; this does not certify origin."""
    require(type(rows) is list and len(rows)==len(INDICES),'exact projected extent')
    require(all(type(r) is dict for r in rows),'projected records must be objects')
    require([r.get('index') for r in rows]==list(INDICES),'exact ordered source ordinals')
    previous=(-1,-1,-1,-1);byindex={}
    for r in rows:
        require(type(r) is dict and set(r)==ROW_KEYS,'exact projected record schema')
        integer(r['index'],0,1276,'source ordinal');integer(r['address'],0,0xFFFFFF,'address')
        integer(r['value'],-1,255,'value');integer(r['frame'],0,1200,'input poll')
        require(type(r['kind']) is str and r['kind'] in set(v.validation.SITES)|{'latch-write','transaction-caller-resume'},'projected kind')
        cpu=r['cpu'];require(type(cpu) is dict and set(cpu)==v.validation.CPU_KEYS,'CPU schema')
        require(cpu['emulationMode'] is False,'native mode')
        for k,value in cpu.items():
            if k!='emulationMode':integer(value,0,255 if k in ('ps','k','dbr') else 65535,'CPU '+k)
        require(cpu['d']==0 and cpu['dbr']==0x7E and cpu['ps']&0x30==0x20 and cpu['ps']&8==0,
                'native M1/X0/D0/DBR7E/binary addressing contract')
        require(type(r['stack']) is list and len(r['stack'])==16,'16 sampled stack bytes')
        for b in r['stack']:integer(b,0,255,'stack byte')
        require(type(r['timing']) is dict and set(r['timing'])==v.validation.TIMING_KEYS,'timing schema')
        t=r['timing']
        for value in t.values():integer(value,0,2**64-1,'timing')
        current=(t['memoryManager.masterClock'],t['cpu.cycleCount'],t['ppu.frameCount'],r['frame'])
        require(all(a>=b for a,b in zip(current,previous)),'clock/cycle/frame/poll reversal');previous=current
        require(t['masterClock']==(t['memoryManager.masterClock']&0xFFFFFFFF)
                and t['frameCount']==t['ppu.frameCount'] and t['clockRate']==21477270,'clock basis')
        require(t['ppu.scanline']<263 and t['memoryManager.hClock']<=1364,'raster bounds')
        require(type(r['latches']) is dict and set(r['latches'])=={'package','scene'},'latch schema')
        for value in r['latches'].values():integer(value,0,255,'latch byte')
        c=r['context'];require(type(c) is dict and set(c)=={'transaction_id','transaction_active','resolver_active','animation_identity'},'context schema')
        require(type(c['transaction_id']) is int and c['transaction_id']==1 and c['transaction_active'] is True
                and c['resolver_active'] is False,'exact owned transaction outside resolver')
        require(type(c['animation_identity']) is list and len(c['animation_identity'])==4,'animation identity shape')
        for x in c['animation_identity']:integer(x,0,255,'identity byte')
        require(c['animation_identity']==[0,2,8,0],'same supported action/config identity')
        if r['kind']=='latch-write':require(r['address'] in (0x7E9876,0x7E5D9B) and r['value']>=0,'latch write shape')
        else:
            require(r['value']==-1 and bankpc(r)==r['address'],'execution witness PC/sentinel')
            if r['kind']!='transaction-caller-resume':require(r['address']==v.validation.SITES[r['kind']],'exact execution site')
        byindex[r['index']]=r
    require([(r['index'],r['address'],r['value'],bankpc(r),r['frame'],r['cpu']['sp']) for r in rows if r['kind']=='latch-write']==list(LATCHES),
            'complete eight-write latch ledger/site/width/ordinal differs')
    # This ledger covers both latch bytes across every selected snapshot. The
    # full accepted transaction validator independently covers its entire trace.
    live={'package':0,'scene':0}
    for r in rows:
        require(r['latches']==live,'latch snapshot not explained by prior actual writes')
        if r['kind']=='latch-write':live['package' if r['address']==0x7E9876 else 'scene']=r['value']
    pairs=[]
    for index,address,value,pc,poll,sp in LATCHES:
        before,after=byindex[index],byindex[index+1]
        key='package' if address==0x7E9876 else 'scene'
        require(after['latches'][key]==value,'actual latch store lacks following snapshot readback')
        pairs.append({'write_index':index,'readback_index':index+1,'bus_address':f'{address:06X}',
                      'callback_cpu_pc':f'{pc:06X}','before':before['latches'][key],'after':value})
    for n,index in enumerate(LOOP_INDICES):
        r=byindex[index];kind='caller-package-latch' if n%2==0 else 'caller-resume'
        require(r['kind']==kind and r['cpu']['sp']==0x6DC and r['stack']==CALLER_FRAME,'exact package-loop boundary/frame')
        require(r['latches']['package']==(1 if index==1115 else 0),'zero wait/final package readback differs')
    stops=[]
    for index,x,poll,inner in ((993,4,932,0x4C06),(1108,3,989,0x4BF1)):
        r=byindex[index]
        frame=[0xD6,0x4C,inner&255,inner>>8,0xCD,0x40]+CALLER_FRAME[:10]
        require(r['kind']=='terminal-command-clear' and r['cpu']['x']==x and r['frame']==poll
                and r['cpu']['sp']==0x6D6 and r['stack']==frame,'stop-handler pre-instruction context')
        require(byindex[index+1]['kind']=='caller-package-latch' and byindex[index+2]['kind']=='caller-resume',
                'stop observation must be followed by still-zero package wait and loop')
        stops.append({'record_index':index,'poll':poll,'observed_x':x,
            'calculated_stz_byte_target':f'{0x7E5DAC+x:06X}','evidence':'pre-execution CPU plus canonical STZ addressing only',
            'actual_owner_write_observed':False,'owner_readback_observed':False})
    pre,write,readback=byindex[1113],byindex[1114],byindex[1115]
    require(pre['kind']=='sync-command-increment' and pre['frame']==991 and pre['cpu']['sp']==0x6D6
            and pre['cpu']['x']==2 and pre['cpu']['y']==0 and pre['cpu']['a']==0,'default-family increment boundary')
    require(pre['stack']==[0xD6,0x4C,0xCA,0x4B,0xCD,0x40]+CALLER_FRAME[:10]
            and pre['stack']==write['stack'],'default-family increment near frame')
    expected=dict(pre['cpu'],pc=0x4D03,ps=pre['cpu']['ps']&~0x82)
    require(write['cpu']==expected,'INC byte write callback CPU/NZ mismatch')
    require(write['timing']['memoryManager.masterClock']-pre['timing']['memoryManager.masterClock']==40
            and write['timing']['cpu.cycleCount']-pre['timing']['cpu.cycleCount']==6
            and write['timing']['ppu.frameCount']==pre['timing']['ppu.frameCount'],'observed INC callback timing')
    require(pre['latches']['package']==write['latches']['package']==0 and readback['latches']['package']==1,'zero-to-one actual increment/readback')
    effect=byindex[1116]
    require(effect['kind']=='caller-effect-latch' and effect['frame']==992 and effect['cpu']['sp']==0x6DC
            and effect['stack']==CALLER_FRAME and effect['latches']=={'package':1,'scene':0},'subsequent separate scene-wait boundary')
    require(byindex[982]['latches']['scene']==1 and byindex[983]['latches']['scene']==0
            and byindex[1117]['latches']['scene']==0,'last scene-clear-site write versus later cleanup reset')
    wrapper=byindex[1119];application=byindex[1120]
    require(wrapper['kind']=='result-wrapper-entry' and wrapper['cpu']['sp']==0x6E8 and wrapper['stack']==[0x20,0xBC]+OUTER_FRAME[:14],
            'result wrapper after reset near frame')
    require(application['kind']=='result-application-entry' and application['cpu']['sp']==0x6E4
            and application['stack']==[0x87,0xAC,0x5C,0xAC]+wrapper['stack'][:12],'result application after both resets')
    end,caller=byindex[1253],byindex[1275]
    require(end['kind']=='animation-result-return' and end['cpu']['sp']==0x6EA and end['stack']==OUTER_FRAME,'same-action animation/result return')
    require(caller['kind']=='transaction-caller-resume' and caller['address']==0xC185D1 and caller['cpu']['sp']==0x6EC
            and caller['stack'][:14]==OUTER_FRAME[2:],'same-action actual queue caller return')
    return {'projected_record_count':len(rows),'latch_write_readback_pairs':pairs,
        'zero_package_wait_iterations':516,'nonzero_package_wait_snapshots':1,'stop_handler_observations':stops,
        'default_family_increment':{'pre_index':1113,'write_index':1114,'readback_index':1115,
            'pre_memory':0,'written_byte':1,'callback_delta_master_clocks':40,'callback_delta_cpu_cycles':6,
            'encoded_command_byte_observed':False},
        'scene_clear_site_write_index':982,'scene_clear_first_later_snapshot_index':983,
        'separate_scene_wait_index':1116,'later_cleanup_reset_indices':[1117,1118],
        'result_wrapper_index':1119,'result_application_index':1120,'animation_result_return_index':1253,
        'actual_transaction_caller_index':1275,'projection_sha256':sha(canonical(rows)),**NONCLAIMS}


def validate_trace(trace):
    v.summarize(trace)  # Unchanged full transaction/queue/HP/MP/stack ledger.
    records=trace['records'];require(len(records)==1277,'exact accepted trace length')
    require([i for i,r in enumerate(records) if r['kind']=='latch-write']==[x[0] for x in LATCHES],'no omitted or donated latch write')
    require([i for i,r in enumerate(records) if r['kind']=='terminal-command-clear']==[993,1108]
            and [i for i,r in enumerate(records) if r['kind']=='sync-command-increment']==[1113],'exact stop/default execution occurrences')
    require([i for i,r in enumerate(records) if r['kind']=='caller-package-latch']==list(LOOP_INDICES[::2]),'exact caller package observations')
    rows=[project(records[i],i) for i in INDICES]
    result=validate_projection(rows)
    result['selected_full_record_hashes']={str(i):sha(canonical(records[i])) for i in sorted(EXTRA|{983,994,995,1109,1110,1111,1112,1115})}
    return result


def collect():
    require(type(STATIC_REFERENCE_SHA) is str and len(STATIC_REFERENCE_SHA)==64,'static acceptance reference not yet pinned')
    before={key:identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    own_before={'auditor':identity(Path(__file__).resolve()),
                'tests':identity(ROOT/'tests/test_package_completion_witness_v1.py')}
    require(Path(evidence.__file__).resolve()==ROOT/PINS['accepted_collector'][0]
            and Path(static_contract.__file__).resolve()==ROOT/PINS['static_auditor'][0]
            and Path(cancellation.__file__).resolve()==ROOT/PINS['cancellation_auditor'][0],'dependency import path')
    old_reference=ROOT/'references/package_transaction_observation_v1.json'
    accepted=decode(read(old_reference,expected=EVIDENCE_REFERENCE_SHA))
    require(canonical(evidence.collect())==canonical(accepted),'accepted full pair no longer reproduces')
    static=static_contract.collect()
    require((json.dumps(static,indent=2)+'\n').encode()==read(STATIC_REFERENCE,expected=STATIC_REFERENCE_SHA),'static source/reference does not reproduce')
    # Reuse the completed canonical scene/reset assertions as source support.
    rom=read(static_contract.ROM,0x400000,static_contract.ROM_SHA,0x400000)
    cancellation_proof=cancellation.audit(rom)
    runs=[];first=None
    for name in evidence.RUNS:
        path=ROOT/'private/test_runs'/name/'trace.json';raw=read(path,expected=TRACE_SHA)
        result=validate_trace(decode(raw))
        if first is None:first=result
        else:require(first==result,'source-matched reuse pair differs')
        runs.append({'trace':identity(path,TRACE_SHA),'witnesses':result})
    after={key:identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    require(before==after,'source drift during reuse audit')
    require(own_before=={'auditor':identity(Path(__file__).resolve()),
                'tests':identity(ROOT/'tests/test_package_completion_witness_v1.py')},'reuse source drift')
    return {'schema':'project-epoch-package-completion-witness-v1','date':'2026-09-08',
        'evidence_level':'verified-runtime','evidence_origin':'reuse and revalidation of two previously accepted native traces; no new CPU execution',
        'scope':'one canonical action08 invocation and exact stop/default-family/latch/caller observations',
        'source_identities':before,**own_before,
        'accepted_transaction_reference':identity(old_reference,EVIDENCE_REFERENCE_SHA),
        'static_completion_reference':identity(STATIC_REFERENCE,STATIC_REFERENCE_SHA),
        'reused_scene_reset_spans':[s for s in cancellation_proof['spans'] if s['role'] in ('scene-latch-owner','animation-work-reset')],
        'canonical_rom':{'size':len(rom),'sha256':sha(rom)},'runs':runs,'paired_reuse_results_identical':True,
        'interpretation_limits':[
            'C14CF3 pre-execution STZ targets are calculated; post-resolver owner writes and owner readbacks were not captured.',
            'C14D00 identifies the shared default-handler branch, not an independently observed encoded command01.',
            'The caller latch sites are pre-execution debugger snapshots plus canonical reader/control flow, not CPU data-read callbacks.',
            'Scene-clear callback PC does not independently establish NMI ownership in this observer.',
            'No script-pointer values or movement are observed; the independent static contract supplies its own bounded interpretation.',
            'The 516 zero-counter waits and later satisfied latch snapshots do not approve a new primary package completion protocol.',
            'Native checkpoint/SRAM provenance and original full watched-transaction limits remain unchanged.'],
        **NONCLAIMS,'reproduce':['python','-B','tools/audit_package_completion_witness_v1.py'],
        'serialization':'UTF-8 indented JSON, LF, one trailing newline'}


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    report=collect();require(canonical(report)==canonical(decode(read(REFERENCE))),'closed reuse reference differs')
    sys.stdout.buffer.write((json.dumps(report,indent=2)+'\n').encode('utf-8'))
