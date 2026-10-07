"""Read-only, metadata-only audit of four pinned compatibility-menu probes.

Watched bus replay and selected snapshots are separate from complete WRAM
ownership. Enumerated pointer residues and one PNG difference are retained.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'references/schala_compat_menu_pair_v1.json'
REFERENCE_SHA='b3e57bb4c906a6fa56aac6f5be2617bb003cc7bb1d6433f56b3d4cdfdba6a182'
BUNDLE_SHA='3862d30a8cd095f3678e83d7e710237a296565610ba4b828f70b2a8ae8ffc3a7'
BASE='private/test_runs/mesen2/'
RUNS={'control':['compat_menu_v1_control_pilot1','compat_menu_v1_control_run2'],
      'relocated':['compat_menu_v1_relocated_pilot1','compat_menu_v1_relocated_run2']}
LABELS=['post_load','prepared','poll_150','poll_390','poll_630','poll_900','poll_1200','poll_1500','cleanup']
MARKER=bytes((19+73*i)&255 for i in range(80))
TRACKED=set(range(0x2830,0x2880))|set(range(0x2C9C,0x2D00))|set(range(0x2600,0x2830))|set(range(0x2980,0x298A))
EXPECTED_CONSUMERS={0xFFF86D:37,0xFFF9A2:60,0xC282E4:4,0xC282E7:4,0xC282EA:4,0xC2830E:0,0xC2B9AF:1}
RESIDUES={'post_load':[],'prepared':[],'poll_150':[0xA78,0xA79],
          **{name:[0x12158,0x12159] for name in ('poll_390','poll_630','poll_900','poll_1200')},
          'poll_1500':[0xA78,0xA79],'cleanup':[0xA78,0xA79]}

class PairError(ValueError): pass
def require(ok,message):
    if not ok: raise PairError(message)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def decode(raw):
    def pairs(items):
        value={}
        for k,v in items:
            require(k not in value,'duplicate JSON key');value[k]=v
        return value
    return json.loads(raw,object_pairs_hook=pairs)
def path(name):
    p=Path(name)
    require(not p.is_absolute() and '..' not in p.parts and p.as_posix()==name,'noncanonical artifact path')
    result=(ROOT/p).resolve()
    require(result.is_relative_to(ROOT) and not (ROOT/p).is_symlink(),'artifact escape/symlink')
    return result
def load(name,captured):
    filename='tools/'+name+'.py';mod=types.ModuleType(name);mod.__file__=str(ROOT/filename)
    sys.modules[name]=mod;exec(compile(captured[filename],mod.__file__,'exec',dont_inherit=True),mod.__dict__)
    return mod
def physical(address):
    require(type(address) is int and 0<=address<=0xFFFFFF,'bus address')
    bank,word=address>>16,address&0xFFFF
    if bank in (0x7E,0x7F): return 'wram',address-0x7E0000
    if (bank<=0x3F or 0x80<=bank<=0xBF) and word<0x2000: return 'wram',word
    if bank==0x30 and 0x6000<=word<0x8000: return 'sram',word-0x6000
    raise PairError('unmodeled bus alias')

def validate_observation(rows,snapshots,sram,mode):
    require(mode in RUNS and rows and rows[0]['kind']=='header' and rows[-1]['kind']=='success','trace envelope')
    require(rows[0]['schema']=='project-epoch-compat-menu-v1' and rows[0]['mode']==mode and
            rows[0]['source_bundle']==BUNDLE_SHA and rows[0]['full_wram_reconciliation'] is False,'trace source/scope')
    require(len(rows)==(360 if mode=='control' else 361),'exact record count')
    require(set(snapshots)==set(LABELS),'snapshot inventory')
    before=snapshots['post_load'][0]
    require(len(before)==0x20000 and len(sram)==8192,'snapshot shape')
    require(before[0x2C9C:0x2D00]==bytes(100),'candidate/guard initial preimage')
    require(before[0x2980:0x2989]==bytes((0,1,2,0x82,0x80,4,3,6,5)),'original roster premise')
    prepared=bytearray(before)
    if mode=='relocated':
        prepared[0x2CA0:0x2CF0]=before[0x2830:0x2880];prepared[0x2830:0x2880]=MARKER
    require(snapshots['prepared'][0]==prepared,'complete preparation footprint')
    terminal=snapshots['poll_1500'][0];cleanup=bytearray(terminal)
    if mode=='relocated':
        cleanup[0x2830:0x2880]=terminal[0x2CA0:0x2CF0];cleanup[0x2CA0:0x2CF0]=bytes(80)
    require(snapshots['cleanup'][0]==cleanup,'complete cleanup footprint')
    for label,(w,s) in snapshots.items():
        require(len(w)==0x20000 and s==sram,'snapshot SRAM identity')
        require(w[0x2C9C:0x2CA0]==bytes(4) and w[0x2CF0:0x2D00]==bytes(16),'guard snapshot changed')
        require(w[0x2600:0x2830]==before[0x2600:0x2830],'original seven snapshot changed')
        require(w[0x2980:0x298A]==before[0x2980:0x298A] and w[0x29AF]==before[0x29AF],'roster/joined snapshot changed')
        require(w[0x2C23:0x2C56]==before[0x2C23:0x2C56],'name snapshot changed')
        if mode=='relocated' and label not in ('post_load','cleanup'):
            require(w[0x2830:0x2880]==MARKER,'marker snapshot changed')
    seen=[];counts={k:0 for k in EXPECTED_CONSUMERS};bus=[];snapshot_rows=[]
    preserved_writes={'records':0,'roster_adjacent':0}
    memory={a:prepared[a] for a in TRACKED};last_poll=0;last_clock=0;prep_count=0
    for index,row in enumerate(rows,1):
        require(row['n']==index and type(row['poll']) is int and last_poll<=row['poll']<=1500,'record/poll order')
        last_poll=row['poll'];kind=row['kind']
        cpu=row.get('cpu',row.get('cpu_observed'))
        if cpu:
            require(type(cpu['clock']) is int and cpu['clock']>=last_clock,'clock ordering')
            last_clock=cpu['clock']
        if kind=='snapshot':
            label=row['label'];require(len(seen)<9 and label==LABELS[len(seen)],'snapshot order')
            require(row['poll']==(0 if label in ('post_load','prepared') else 1500 if label=='cleanup' else int(label[5:])), 'snapshot poll')
            if label in ('post_load','prepared'):
                require((cpu['k'],cpu['pc'],cpu['d'],cpu['emulationMode'])==(0xC2,0xE65B,0,False),'post-load native return')
            if label not in ('post_load','cleanup'):
                require(all(snapshots[label][0][a]==memory[a] for a in TRACKED),'watched snapshot lacks bus explanation')
            seen.append(label);snapshot_rows.append(row)
        elif kind=='diagnostic-preparation':
            prep_count+=1
            require(mode=='relocated' and seen==['post_load'] and row['natural_start']==0x2830 and
                    row['candidate_start']==0x2CA0 and row['size']==80,'preparation event')
        elif kind=='consumer':
            require(row['site'] in counts and seen and seen[-1]!='cleanup','consumer outside interval')
            require(cpu['k']<<16|cpu['pc']==row['site'],'consumer CPU boundary')
            counts[row['site']]+=1
        elif kind=='bus':
            require(seen and seen[-1] not in ('post_load','cleanup'),'bus outside prepared interval')
            space,a=physical(row['address'])
            require(space=='wram','observed SRAM activity; reads are not registered by this collector')
            require(a==row['physical'] and a in TRACKED,'physical mapping/watch domain')
            require(not 0x2C9C<=a<0x2CA0 and not 0x2CF0<=a<0x2D00,'guard bus access')
            if 0x2600<=a<0x2830 or 0x2980<=a<0x298A:
                require(row['operation']=='write' and row['value']==before[a],
                        'original record/roster write changes the preserved value')
                preserved_writes['records' if a<0x2830 else 'roster_adjacent']+=1
            require(not (mode=='relocated' and 0x2830<=a<0x2880),'opaque marker bus access')
            require(not (mode=='control' and 0x2CA0<=a<0x2CF0),'control candidate access')
            value=row['value'];require(type(value) is int and 0<=value<=255,'bus byte')
            if row['operation']=='read': require(memory[a]==value,'read disagrees with watched-byte replay')
            else:
                require(row['operation']=='write','unknown bus operation');memory[a]=value
            normalized=a-0x470 if mode=='relocated' and 0x2CA0<=a<0x2CF0 else a
            bus.append((row['operation'],normalized,value,row['poll'],cpu['clock']))
        elif kind=='header': require(index==1,'duplicate header')
        elif kind=='success': require(index==len(rows) and seen==LABELS and row['poll']==1500,'early success')
        else: raise PairError('unexpected/failure trace row')
    require(prep_count==(mode=='relocated') and len(bus)==239 and counts==EXPECTED_CONSUMERS,'bounded event census')
    require(preserved_writes=={'records':104,'roster_adjacent':1},'preserved-write census')
    return {'bus':bus,'snapshots':snapshot_rows,'counts':counts,'preserved_writes':preserved_writes}

def compare_modes(control,relocated,observed_control,observed_relocated):
    require(observed_control['bus']==observed_relocated['bus'],'inverse-relocated bus equivalence')
    for left,right in zip(observed_control['snapshots'],observed_relocated['snapshots']):
        require(left['label']==right['label'] and left['cpu']==right['cpu'] and
                all(left[k]==right[k] for k in ('poll','menu','cursor','location')),'snapshot CPU/context equivalence')
    residue={}
    for label in LABELS:
        a=control[label][0];b=bytearray(relocated[label][0])
        for start,end in ((0x2600,0x2830),(0x2980,0x298A),(0x2C23,0x2C56),(0x7F00,0x7F25),(0x04A4,0x04A9)):
            require(a[start:end]==b[start:end],'original records/roster/names/derived mirrors differ')
        if label not in ('post_load','cleanup'):
            b[0x2830:0x2880]=b[0x2CA0:0x2CF0];b[0x2CA0:0x2CF0]=bytes(80)
        offsets=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        require(offsets==RESIDUES[label],'unenumerated full-WRAM difference after inverse relocation')
        if offsets:
            start=offsets[0]
            require(int.from_bytes(a[start:start+2],'little')==0x285C and
                    int.from_bytes(b[start:start+2],'little')==0x2CCC,'enumerated pointer residue value changed')
        residue[label]=offsets
    return residue

def audit():
    ref_raw=REFERENCE.read_bytes();own=Path(__file__).read_bytes()
    require(sha(ref_raw)==REFERENCE_SHA,'reference identity drift')
    ref=decode(ref_raw);require(ref['runs']==RUNS and ref['source_bundle']['sha256']==BUNDLE_SHA,'accepted set drift')
    inventory=ref['artifact_inventory'];names=[r[0] for r in inventory]
    require(len(names)==155 and names==sorted(set(names)),'artifact inventory omission/duplication')
    captured={}
    for name,size,digest in inventory:
        raw=path(name).read_bytes();require(len(raw)==size and sha(raw)==digest,'artifact identity: '+name);captured[name]=raw
    for ps in ref['byte_equality_groups']:
        require(all(captured[p]==captured[ps[0]] for p in ps[1:]),'declared byte repeat failed')
    exception=ref['presentation_exception']['files']
    require(captured[exception[0].replace('\\','/')]!=captured[exception[1].replace('\\','/')],'presentation exception changed')
    load('schala_rom_scaffold',captured);load('validate_rom_write_intents',captured)
    contract=load('schala_compat_menu_v1',captured);builder=load('build_schala_compat_menu_v1',captured)
    require(contract.bundle_identity()==ref['source_bundle']['builder_bundle'],'builder source bundle drift')
    payload=json.dumps({'builder_bundle':contract.bundle_identity(),'probe_sources':ref['source_bundle']['probe_sources']},sort_keys=True,separators=(',',':')).encode()
    require(sha(payload)==BUNDLE_SHA,'probe bundle encoding')
    all_snaps={};all_obs={}
    for mode,dirs in RUNS.items():
        for name in dirs:
            d=BASE+name;receipt=decode(captured[d+'/receipt.json']);plan=decode(captured[d+'/plan.json'])
            require(receipt['mode']==mode and receipt['source_bundle']==ref['source_bundle'] and
                    receipt['status']=='collected-awaiting-pair-review' and receipt['returncode']==63 and
                    receipt['failure'] is None and receipt['launch_executed'] is True,'probe receipt status')
            require(plan['source_bundle']==receipt['source_bundle'] and plan['build']==receipt['build'],'prelaunch plan binding')
            for value in receipt['inputs'].values():
                input_name=Path(value['path']).resolve().relative_to(ROOT).as_posix();raw=captured[input_name]
                require(len(raw)==value['size'] and sha(raw)==value['sha256'],'original input identity')
            for filename,value in receipt['artifacts'].items():
                raw=captured[d+'/'+filename];require(len(raw)==value['size'] and sha(raw)==value['sha256'],'receipt output identity')
            canonical=captured['private/input/rom_archive/Chrono Trigger (USA).sfc']
            if mode=='relocated':
                image,build=builder.build_image(canonical,ROOT/d/'diagnostic.sfc')
                require(build==receipt['build'],'guarded build receipt mismatch')
            else: image=canonical
            require(image==captured[d+'/diagnostic.sfc'] and sha(image)==receipt['rom_sha256'],'diagnostic image identity')
            require(captured[d+'/collector.lua']==captured['tools/mesen_compat_menu_v1.lua'],'staged observer identity')
            rows=[decode(line) for line in captured[d+'/events.jsonl'].splitlines()]
            snapshots={label:(captured[d+'/'+label+'.wram.bin'],captured[d+'/'+label+'.sram.bin']) for label in LABELS}
            all_obs[name]=validate_observation(rows,snapshots,captured[d+'/input.sram'],mode);all_snaps[name]=snapshots
            require({f'{k:06X}':v for k,v in all_obs[name]['counts'].items()}==receipt['observed_consumers'],'consumer receipt drift')
    residues=compare_modes(all_snaps[RUNS['control'][0]],all_snaps[RUNS['relocated'][0]],
                           all_obs[RUNS['control'][0]],all_obs[RUNS['relocated'][0]])
    require(residues==ref['observed_pointer_residue']['snapshot_offsets'],'residue reference mismatch')
    for name,size,digest in inventory:
        require(path(name).read_bytes()==captured[name],'artifact changed during audit: '+name)
    require(REFERENCE.read_bytes()==ref_raw and Path(__file__).read_bytes()==own,'auditor/reference drift')
    return {'schema':'project-epoch-compat-menu-pair-revalidation-v1','evidence_level':ref['evidence_level'],
        'reference_sha256':REFERENCE_SHA,'auditor_sha256':sha(own),'source_bundle_sha256':BUNDLE_SHA,
        'artifacts':155,'declared_byte_equality_groups':len(ref['byte_equality_groups']),
        'matched_bus_events':239,'matched_snapshot_cpu_tuples':9,'original_pc_records':7,
        'same_value_original_record_writes_per_run':all_obs[RUNS['control'][0]]['preserved_writes']['records'],
        'same_value_roster_adjacent_writes_per_run':all_obs[RUNS['control'][0]]['preserved_writes']['roster_adjacent'],
        'observed_consumers':{f'{k:06X}':v for k,v in EXPECTED_CONSUMERS.items()},
        'pointer_residue':ref['observed_pointer_residue'],'presentation_exception':ref['presentation_exception'],
        'scope':ref['scope'],'limitations':ref['limitations'],'native_execution_performed':False,'rom_emitted':False}

if __name__=='__main__': print(json.dumps(audit(),indent=2,sort_keys=True))
