"""Native-ROM graphics adapter in the bounded PC07 field fixture; default is a plan.

This reuses the canonical entry observer, event transform, isolated runtime,
and the previously accepted fourteen-byte compatibility relocation. The actual
CPU now executes the qualified graphics helper in ROM bank41. Record and event
preparation still use explicit debugger writes. Raw game data stays below private/.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import run_mesen_pc07_field_entry_v1 as baseline
import transform_pc07_selected_event_v1 as transform
import schala_compat_menu_v1 as compatibility
import build_pc07_native_field_v1 as native_builder

ROOT=baseline.ROOT
runtime=baseline.runtime
COLLECTOR=ROOT/'tools/mesen_pc07_field_probe_v3.lua'
BASE_RUN=ROOT/'private/test_runs/mesen2/pc07_field_entry_v1_run1'
BASE_REVIEW=ROOT/'private/research/pc07_field_entry_review_20261007/receipt.json'
BASE_REVIEW_SHA='8e60151b54bceb079676c1aea3e4a3f18a44e4ce2d7158a9f2c6fdca9dea75ad'
SCHEMA='project-epoch-pc07-field-probe-v3'
LABELS=('post_load','compatibility_staged','scene_entry','entry_staged','canonical_event_ready','event_staged',
        'poll_90','poll_180','poll_280','poll_400')
ROSTER=bytes((0,1,7,2,0x80,4,3,6,5))
PINS={
 'tools/schala_compat_menu_v1.py':'4b679c79791a8d2ec879f2f9e1e5ad5b46bb4655f59c7d00d217cc3613c35f59',
 'tools/build_schala_compat_menu_v1.py':'2b52518dc365e0bbfef0259dfbea990e69b8d5407fffa8b9b1df859ebf5fa47d',
 'references/schala_compat_menu_pair_v1.json':'b3e57bb4c906a6fa56aac6f5be2617bb003cc7bb1d6433f56b3d4cdfdba6a182',
 'tools/run_mesen_pc07_field_entry_v1.py':'7c6eae5771acfcbc5749c93eb29d6b540c757bcde46a741b0b1bc486b810b6b5',
 'tools/mesen_pc07_field_entry_v1.lua':'6c36380b93cb19ef7b031299a8f1d04d0def7338d27a594037e828ff60d00b47',
 'tools/transform_pc07_selected_event_v1.py':'1213ae3f274ba044608185d9b9e806cf9f6db2cfdb0ab89f70a09de0e2ff1d3a',
 'references/pc07_selected_event_transform_v1.json':'0bb253c1f296e5719b204052588f25254a045a3cc716d32127347b6e304cdd66',
 **baseline.PINNED,
}

def sha(data):return hashlib.sha256(data).hexdigest()

def bundle():
    for path,digest in PINS.items():runtime.read_regular(ROOT/path,digest=digest)
    transform.load_dependencies()
    built=native_builder.bundle()
    paths=tuple(dict.fromkeys((*PINS,*native_builder.SOURCES,
        'tools/run_mesen_pc07_field_probe_v3.py','tools/mesen_pc07_field_probe_v3.lua')))
    sources=[{'path':path,'sha256':sha((ROOT/path).read_bytes())} for path in paths]
    return {'sha256':sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()),
            'sources':sources,'builder_bundle_sha256':built['sha256']}


def make_record(entry):
    if len(entry)!=0x20000:raise ValueError('entry WRAM size')
    donor=entry[0x2600:0x2650]
    hp=int.from_bytes(donor[3:5],'little')
    maximum=int.from_bytes(donor[5:7],'little')
    if donor[0]!=0 or not 1<hp<=maximum:raise ValueError('donor identity/current HP')
    record=bytearray(donor);record[0]=7;record[3:5]=(hp-1).to_bytes(2,'little')
    return bytes(record)

def baseline_inputs():
    runtime.read_regular(BASE_REVIEW,digest=BASE_REVIEW_SHA)
    # Exact reviewed paths and hashes; a different snapshot from the same
    # receipt cannot silently substitute for either required preimage.
    entry=runtime.read_regular(BASE_RUN/'scene_entry.wram.bin',size=0x20000,
        digest='8756d486dba79b85f9ec41168922dd0b22acae0fb0473b411377479634346a83')
    ready=runtime.read_regular(BASE_RUN/'canonical_event_ready.wram.bin',size=0x20000,
        digest='785d5f2f7df22a9d784209b17dc7b1ea5eef21070f2e0247467018a7460d8c7a')
    return entry,ready

def validate_observation(rows,snapshots,sram,entry,ready,packet,builtins,new_packet,record):
    if [r.get('n') for r in rows]!=list(range(1,len(rows)+1)):raise ValueError('record sequence')
    if rows[0]['kind']!='header' or rows[0].get('schema')!=SCHEMA or rows[-1]['kind']!='success':raise ValueError('trace envelope')
    if tuple(r['label'] for r in rows if r['kind']=='snapshot')!=LABELS:raise ValueError('snapshot sequence')
    for label in LABELS:
        w=snapshots[label]
        if len(w)!=0x20000 or w[0x2600:0x2830]!=entry[0x2600:0x2830]:raise ValueError('original records changed')
        if w[0x2C4D:0x2C53]!=entry[0x2C4D:0x2C53]:raise ValueError('Epoch name changed')
        if label not in ('post_load','compatibility_staged','scene_entry'):
            for address,value in ((0x2830,record),(0x2CA0,entry[0x2830:0x2880]),(0x2980,ROSTER),
                                  (0x29AF,b'\xff'),(0x2C80,entry[0x2C80:0x2CA0]),(0x2CF0,entry[0x2CF0:0x2D10])):
                if w[address:address+len(value)]!=value:raise ValueError('staged range changed: '+label)
        if sram[label]!=sram['scene_entry']:raise ValueError('captured SRAM drift')
    expected=bytearray(snapshots['post_load'])
    if expected[0x2830:0x2880]!=entry[0x2830:0x2880]:raise ValueError('post-load compatibility preimage')
    expected[0x2CA0:0x2CF0]=expected[0x2830:0x2880]
    if bytes(expected)!=snapshots['compatibility_staged']:raise ValueError('early compatibility injection complete diff')
    if snapshots['scene_entry'][0x2CA0:0x2CF0]!=entry[0x2830:0x2880]:raise ValueError('compatibility not current at scene entry')
    expected=bytearray(snapshots['scene_entry'])
    for address,value in ((0x2830,record),(0x2980,ROSTER),(0x29AF,b'\xff')):
        expected[address:address+len(value)]=value
    if bytes(expected)!=snapshots['entry_staged']:raise ValueError('entry injection complete diff')
    ready_row=next(r for r in rows if r.get('label')=='canonical_event_ready' and r['kind']=='snapshot')
    baseline.check_ready_snapshot(snapshots['canonical_event_ready'],ready_row,packet,builtins)
    if snapshots['canonical_event_ready'][0x12000:0x13700]!=ready[0x12000:0x13700]:raise ValueError('arena preimage')
    expected=bytearray(snapshots['canonical_event_ready']);expected[0x12000:0x12000+len(new_packet)]=new_packet
    expected[0x306:0x308]=len(new_packet).to_bytes(2,'little')
    if bytes(expected)!=snapshots['event_staged']:raise ValueError('event injection complete diff')
    # The source-defined six preparations must have exact, paired per-byte
    # debugger write/readback witnesses, independent of memory callbacks.
    plans=[('compatibility-copy',0x2CA0,snapshots['post_load'][0x2CA0:0x2CF0],entry[0x2830:0x2880]),
           ('separate-PC07-record',0x2830,entry[0x2830:0x2880],record),
           ('roster',0x2980,bytes((0,1,2,0x82,0x80,4,3,6,5)),ROSTER),
           ('joined',0x29AF,b'\xfe',b'\xff'),
           ('transformed-event',0x12000,ready[0x12000:0x12000+len(new_packet)],new_packet),
           ('decompressed-length',0x306,b'\x39\x09',len(new_packet).to_bytes(2,'little'))]
    observed=[r for r in rows if r['kind'] in ('injection','injection-readback')]
    expected_rows=[]
    for label,address,old,new in plans:
        for i,(a,b) in enumerate(zip(old,new)):
            expected_rows.extend([('injection',label,address+i,a,b),('injection-readback',label,address+i,None,b)])
    actual=[(r['kind'],r['label'],r['physical'],r.get('before'),r.get('after',r.get('value'))) for r in observed]
    if actual!=expected_rows:raise ValueError('injection byte ledger')
    native = validate_native_helper(rows)
    descriptors=[0xE4F001,0xE4F002,0xE4F003,0xE4F004,0xE4F000]
    pointer_reads=list(zip(
        [0xE42300,0xE42301,0xE42302,0xE42602,0xE42603,0xE42600,0xE42601,
         0xE42600,0xE42601,0xE42800,0xE42801,0xE42000,0xE42001,0xE42002],
        [0xC044B1,0xC044B1,0xC044BC,0xC044F1,0xC044F1,0xC044F6,0xC044F6,
         0xC044FF,0xC044FF,0xC04504,0xC04504,0xC04529,0xC04529,0xC04534]))
    for which,role,logical,obj in [('original00',0,0,2),('candidate07',2,7,16)]:
        for kind in ('graphics-window-start','graphics-pre-rts','graphics-return'):
            selected=[r for r in rows if r['kind']==kind and r['which']==which]
            if len(selected)!=1:raise ValueError('missing graphics phase: '+which+'/'+kind)
            c=selected[0]['context']
            if (c['self_role'],c['self_logical_id'],c['self_object_offset'])!=(role,logical,obj):raise ValueError('graphics identity drift')
        reads=[r for r in rows if r['kind']=='graphics-rom-read' and r['which']==which and 0xE4F000<=r['address']<0xE4F028]
        if [r['address'] for r in reads]!=descriptors:raise ValueError('donor descriptor sequence')
        reads=[(r['address'],r['preceding_exec_pc']) for r in rows
               if r['kind']=='graphics-rom-read' and r['which']==which and not 0xE4F000<=r['address']<0xE4F028]
        if reads!=pointer_reads:raise ValueError('donor pointer-table sequence')
        stores=[r for r in rows if r['kind']=='graphics-hardware-write' and r['which']==which and r['preceding_exec_pc']==0x410029]
        if len(stores)!=1 or (stores[0]['address'],stores[0]['value'])!=(0x4202,0):raise ValueError('actual donor hardware write')
    positions=[]
    for label in LABELS[6:]:
        w=snapshots[label]
        if w[0x197:0x19D]!=bytes((2,0,4,0,16,0)):raise ValueError('active role pointers')
        for role,obj,logical in [(0,2,0),(1,4,1),(2,16,7)]:
            if (w[0x1100+obj],w[0x1101+obj])!=(role,logical):raise ValueError('field identity')
        positions.append({'snapshot':label,'screen_x':[int.from_bytes(w[0xA00+o:0xA02+o],'little') for o in (2,4,16)],
                          'screen_y':[int.from_bytes(w[0xA80+o:0xA82+o],'little') for o in (2,4,16)]})
    candidate_positions={(r['screen_x'][2],r['screen_y'][2]) for r in positions}
    if len(candidate_positions)<2:raise ValueError('candidate movement not observed')
    return {'early_compatibility_entry_and_event_complete_diff':True,'injection_bytes':len(expected_rows)//2,
            'graphics_donor_control_and_candidate_observed':True,'all_original_records_preserved':True,
            'independent_candidate_hp':int.from_bytes(record[3:5],'little'),
            'original_donor_hp':int.from_bytes(entry[0x2603:0x2605],'little'),
            'screen_positions':positions,'candidate_screen_movement_observed':len(candidate_positions)>1,
            'installed_private_native_adapter':True,'native_helper':native,'battle_menu_save_support':False,
            'epoch_name_snapshots_preserved':all(w[0x2C4D:0x2C53]==entry[0x2C4D:0x2C53] for w in snapshots.values()),
            'evidence':'native ROM graphics adapter in an instrumented selected field diagnostic; not a playable release'}

def validate_native_helper(rows):
    if any(r['kind'] in ('cpu-edit','helper-interrupt') for r in rows):
        raise ValueError('CPU edit or interrupt is outside this normal native observation')
    helper=native_builder.component()
    canonical=runtime.read_regular(baseline.ROM,size=0x400000,digest=baseline.ROM_SHA)
    expected_maps={'C0448D':(0x448D,native_builder.HOOK),
                   '410000':(0x410000,helper),
                   'C2E657':(0x2E657,bytes.fromhex('22a3faff')),
                   'E4F000':(0x24F000,canonical[0x24F000:0x24F005])}
    mappings=[r for r in rows if r['kind'] in ('postload-mapping','helper-mapping')]
    if [r['kind'] for r in mappings]!=['postload-mapping']+['helper-mapping']*3:
        raise ValueError('required post-load and invocation mappings')
    for row in mappings:
        if row['prg_size']!=0x800000 or set(row['entries'])!=set(expected_maps):
            raise ValueError('expanded ROM mapping shape')
        for key,(physical,payload) in expected_maps.items():
            entry=row['entries'][key]
            if (entry['address']!=int(key,16) or entry['physical']!=physical or
                    entry['memType']!=row['prg_memory_type'] or
                    bytes.fromhex(entry['bytes_hex'])!=payload):
                raise ValueError('expanded ROM mapping/content: '+key)
    starts=[r for r in rows if r['kind']=='helper-window-start']
    ends=[r for r in rows if r['kind']=='helper-window-end']
    names=['original00','original01','candidate07']
    if ([r['which'] for r in starts]!=names or [r['which'] for r in ends]!=names or
            [r['window'] for r in starts]!=[1,2,3] or [r['window'] for r in ends]!=[1,2,3]):
        raise ValueError('three actual helper windows required')
    control=[0,1,2,4,40,41,44,45,46,48]
    candidate=[0,1,2,4,6,10,12,14,18,20,22,26,28,30,33,35,36,38,41,44,45,46,48]
    results=[]
    for index,(start,end) in enumerate(zip(starts,ends),1):
        before=start['cpu'];after=end['after'];name=names[index-1]
        if end['before']!=before or not start['n']<end['n']:
            raise ValueError('helper before/after pairing')
        if index<3 and end['n']>=starts[index]['n']:
            raise ValueError('overlapping helper windows')
        if not mappings[index]['n']<start['n'] or (index==1 and not mappings[0]['n']<start['n']):
            raise ValueError('mapping must precede native helper')
        if (before['k']!=0xC0 or before['pc']!=0x448D or before['emulationMode'] or
                before['ps']&0x30!=0x20 or before['d']!=0x100 or before['dbr']!=0 or
                before['sp']!=0x6F7 or before['x']!=(2,4,16)[index-1] or
                before['y']!=(0x2E2,0x381,0x734)[index-1] or
                before['a']!=(0,1,0x107)[index-1]):
            raise ValueError('helper selected native entry context')
        expected=dict(before)
        expected.update(a=(before['a']&0xFF00)|5,y=(before['y']+1)&0xFFFF,
                        ps=before['ps']&0x7D,pc=0x4493,clock=after['clock'])
        if after!=expected or after['clock']<=before['clock']:
            raise ValueError('native replacement result/context differs')
        subset=[r for r in rows if start['n']<r['n']<end['n'] and r.get('window')==index
                and r['kind'].startswith('helper-')]
        if any(r.get('which')!=name for r in subset):raise ValueError('helper identity label drift')
        executed=[r for r in subset if r['kind']=='helper-exec']
        addresses=[0x410000+o for o in (candidate if index==3 else control)]+[0xC04491,0xC04492]
        if [r['address'] for r in executed]!=addresses:
            raise ValueError('actual helper instruction sequence')
        low=before['sp']-4
        initial=bytes.fromhex(start['stack_hex'])
        ledger=bytearray.fromhex(start['stack_coverage_hex']);coverage_low=before['sp']-64
        if len(initial)!=21 or start['stack_base']!=low or end['stack_base']!=low:
            raise ValueError('helper stack capture extent')
        if (len(ledger)!=81 or ledger[60:]!=initial or
                start['stack_coverage_low']!=coverage_low or start['stack_coverage_high']!=before['sp']+16):
            raise ValueError('helper full watched stack preimage')
        writes=[];reads=[];last_exec=start['exec_index'];last_pc=0xC0448D
        minimum=before['sp']
        for r in subset:
            kind=r['kind']
            if kind=='helper-exec':
                c=r['cpu']
                if (r['stack_base']!=low or bytes.fromhex(r['stack_hex'])!=ledger[60:] or
                        (c['k']<<16|c['pc'])!=r['address'] or
                        r['exec_index']<=last_exec or c['emulationMode'] or c['ps']&0x30!=0x20):
                    raise ValueError('helper instruction/stack readback')
                last_exec,last_pc=r['exec_index'],r['address'];minimum=min(minimum,c['sp'])
            elif kind in ('helper-stack-read','helper-stack-write'):
                if (r['preceding_exec_pc']!=last_pc or r['exec_index']!=last_exec or
                        r['stack_base']!=low or bytes.fromhex(r['stack_hex'])!=ledger[60:] or
                        r['physical']!=r['address']&0x1FFF):
                    raise ValueError('stack access ownership or ordered snapshot')
                at=r['physical']-coverage_low
                if not 0<=at<81:raise ValueError('stack access outside captured normal cells')
                if kind=='helper-stack-write':
                    if r['snapshot_phase']!='prewrite':raise ValueError('stack write snapshot phase')
                    writes.append((r['physical'],r['value'],last_pc));ledger[at]=r['value']
                else:
                    if r['snapshot_phase']!='read-callback' or r['value']!=ledger[at]:
                        raise ValueError('native stack read value')
                    reads.append((r['physical'],r['value'],last_pc))
            elif kind=='helper-hardware-write':
                if r['preceding_exec_pc']!=last_pc or r['exec_index']!=last_exec:
                    raise ValueError('helper hardware write ownership')
            else:
                raise ValueError('unknown helper evidence row')
        sp=before['sp']
        expected_writes=[(sp,0xC0,0xC0448D),(sp-1,0x44,0xC0448D),(sp-2,0x90,0xC0448D),
                         (sp-3,before['ps'],0x410000),(sp-4,before['a']&255,0x410001)]
        if writes!=expected_writes:raise ValueError('native JSL/PHP/PHA write ledger')
        # Dummy stack reads may coexist; the real pop operands must all be seen.
        required_reads=[(sp-4,before['a']&255,0x410023 if index==3 else 0x410028),
                        (sp-3,before['ps'],0x41002C),
                        (sp-2,0x90,0x410030),(sp-1,0x44,0x410030),(sp,0xC0,0x410030)]
        for item in required_reads:
            if item not in reads:raise ValueError('missing actual stack pop read')
        if (minimum!=sp-5 or end['min_sp']!=minimum or end['write_count']!=5 or
                end['selector_count']!=1 or end['interrupt_observed'] is not False or
                bytes.fromhex(end['stack_before_hex'])!=initial or
                bytes.fromhex(end['stack_hex'])!=ledger[60:] or ledger[65:]!=initial[5:]):
            raise ValueError('native helper final stack or interrupt result')
        hardware=[r for r in subset if r['kind']=='helper-hardware-write']
        if (len(hardware)!=1 or hardware[0]['address']!=0x4202 or
                hardware[0]['value']!=(1 if index==2 else 0) or
                hardware[0]['preceding_exec_pc']!=0x410029):
            raise ValueError('native multiply selector publication')
        results.append({'which':name,'instructions':len(executed),'stack_writes':len(writes),
                        'stack_reads':len(reads),'entry_sp':sp,'minimum_observed_sp':minimum,
                        'master_clocks':after['clock']-before['clock'],
                        'ordered_stack_reconciliation':True,'live_caller_bytes_preserved':16})
    return {'windows':results,'actual_rom_helper':True,'debugger_cpu_edits':0,
            'expanded_mapping_observed':True,'interrupts_observed_in_helper':0,
            'interrupt_safety_proved':False,'global_stack_ownership_proved':False}


def collect(args):
    identity=bundle()
    original={'rom':(baseline.ROM,runtime.read_regular(baseline.ROM,size=0x400000,digest=baseline.ROM_SHA)),
              'state':(baseline.STATE,runtime.read_regular(baseline.STATE,size=93029,digest=baseline.STATE_SHA)),
              'sram':(baseline.SRAM,runtime.read_regular(baseline.SRAM,size=8192,digest=baseline.SRAM_SHA))}
    for name,(size,digest) in runtime.RUNTIME.items():
        path=ROOT/'private/tools/mesen2/app'/name;original[name]=(path,runtime.read_regular(path,size=size,digest=digest))
    packet,builtins,contract=baseline.comparison_inputs(original['rom'][1])
    # Reuse the canonical packet contract, not the baseline's shorter controls.
    contract={k:v for k,v in contract.items() if k!='input_schedule'}
    entry,ready=baseline_inputs();record=make_record(entry);new=transform.transform_from_rom(original['rom'][1])
    output=baseline.private_path(args.output)
    native_builder.contract.output_path((output/'diagnostic.sfc').relative_to(ROOT).as_posix())
    if any(path.resolve().is_relative_to(output) for path,_ in original.values()):raise ValueError('output contains input')
    target,build=native_builder.build_image(original['rom'][1],native_builder.component(),output/'diagnostic.sfc')
    expected={'diagnostic.sfc':target,'entry.mss':original['state'][1],'input.sram':original['sram'][1],
              'collector.lua':COLLECTOR.read_bytes(),'canonical_packet.bin':packet,'canonical_builtins.bin':builtins,
              'transformed_packet.bin':new.packet,'entry_preimage.bin':entry,'ready_preimage.bin':ready,'record.bin':record,'helper.bin':native_builder.component()}
    report={'schema':SCHEMA+'-run','source_bundle':identity,'baseline_review_sha256':BASE_REVIEW_SHA,
      'inputs':{k:{'path':str(p),'sha256':sha(b),'bytes':len(b)} for k,(p,b) in original.items()},
      'staged_inputs':{k:{'sha256':sha(v),'bytes':len(v)} for k,v in expected.items()},
      'canonical_contract':contract,'transform':new.metadata,'rom_unmodified':False,'emulator_assisted':True,
      'native_field_build':build,'reused_compatibility_operand_bytes':14,
      'input_schedule':{'Left':[120,167],'Right':[220,267],'snapshots':[90,180,280,400],'stop_poll':400},
      'launch_executed':False,'native_adapter_in_image':True,'native_execution':False,'playable_release':False,
      'deferred_stop_excluded':True,'shutdown_sram_authoritative':False,
      'reproduction':'python -B tools/run_mesen_pc07_field_probe_v3.py --output <fresh-private-directory> --run-reviewed-bundle '+identity['sha256'],
      'status':'verified-static-plan'}
    if not args.run_reviewed_bundle:return report
    if args.run_reviewed_bundle!=identity['sha256']:raise ValueError('exact reviewed bundle required')
    if output.exists():raise ValueError('fresh private output required')
    output.mkdir(parents=True,exist_ok=False)
    native_builder.assembler.verify_asar()
    wrapper='arch 65816\nnorom\norg $000000\nincsrc "'+native_builder.ASM.as_posix()+'"\n'
    assembled,assembly=native_builder.assembler.assemble_raw(output,'adapters',wrapper,maximum=157)
    if assembled!=expected['helper.bin']:raise ValueError('fresh assembly differs from reviewed helper')
    target2,build2=native_builder.build_image(original['rom'][1],assembled,output/'diagnostic.sfc')
    if target2!=target or build2!=build:raise ValueError('fresh assembly/build differs from plan')
    report['fresh_assembly']=assembly
    app=output/'app';(app/'Saves').mkdir(parents=True)
    for name in runtime.RUNTIME:(app/name).write_bytes(original[name][1])
    for name,data in expected.items():native_builder.assembler.exclusive(output/name,data)
    (app/'Saves/diagnostic.srm').write_bytes(original['sram'][1])
    env={k:v for k,v in os.environ.items() if not k.startswith('PE_FIELD_PROBE_')}
    suffixes={'STATE':'entry.mss','SRAM':'input.sram','PACKET':'canonical_packet.bin','BUILTINS':'canonical_builtins.bin',
              'TRANSFORMED':'transformed_packet.bin','ENTRY_PREIMAGE':'entry_preimage.bin','READY_PREIMAGE':'ready_preimage.bin','RECORD':'record.bin','HELPER':'helper.bin'}
    env.update({'PE_FIELD_PROBE_'+k:str(output/v) for k,v in suffixes.items()})
    env.update(PE_FIELD_PROBE_OUTPUT=str(output),PE_FIELD_PROBE_BUNDLE=identity['sha256'])
    command=[str(app/'Mesen.exe'),'--testRunner','--timeout=120','--doNotSaveSettings',
             '--debug.scriptWindow.allowIoOsAccess=true','--snes.port1.type=SnesController',str(output/'collector.lua'),str(output/'diagnostic.sfc')]
    (output/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    process=None;failure=None;attempted=False;launched=False
    try:
        runtime.check_inputs(original)
        if bundle()!=identity or baseline_inputs()!=(entry,ready):raise ValueError('source/baseline drift before launch')
        attempted=True
        process=subprocess.run(command,cwd=app,env=env,capture_output=True,text=True,timeout=140,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        launched=True
        (output/'stdout.txt').write_text(process.stdout,encoding='utf-8');(output/'stderr.txt').write_text(process.stderr,encoding='utf-8')
        if process.returncode!=63 or (output/'failure.txt').exists():raise ValueError('collector failure')
        rows=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
        if rows[0].get('source_bundle')!=identity['sha256']:raise ValueError('trace source identity')
        snapshots={name:(output/(name+'.wram.bin')).read_bytes() for name in LABELS}
        srams={name:(output/(name+'.sram.bin')).read_bytes() for name in LABELS}
        if any(value!=original['sram'][1] for value in srams.values()):raise ValueError('input SRAM changed')
        report['observations']=validate_observation(rows,snapshots,srams,entry,ready,packet,builtins,new.packet,record)
        report['records']=len(rows)
        report['native_execution']=True
    except subprocess.TimeoutExpired as exc:launched=True;failure=repr(exc)
    except Exception as exc:failure=repr(exc)
    finally:
        try:
            runtime.check_inputs(original)
            if bundle()!=identity or baseline_inputs()!=(entry,ready):raise ValueError('source/baseline drift during launch')
            if any((output/name).read_bytes()!=data for name,data in expected.items()):raise ValueError('staged input drift')
        except Exception as exc:failure=repr(exc)
        report.update(launch_executed=launched,launch_attempted=attempted,
                      status='quarantined-failure' if failure else 'collected-awaiting-field-review',
                      evidence='rejected-pilot' if failure else 'emulator-assisted-runtime-observation',
                      failure=failure,returncode=process.returncode if process else None)
        report['artifacts']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in output.iterdir()
                             if p.is_file() and p.suffix in ('.jsonl','.bin','.png','.txt')}
        (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if failure:raise RuntimeError(failure)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--run-reviewed-bundle')
    print(json.dumps(collect(p.parse_args()),indent=2))
