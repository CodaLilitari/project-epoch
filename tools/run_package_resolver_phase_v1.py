#!/usr/bin/env python3
"""Observe the pinned primary resolver's actual interrupt/timer/DMA phase.

Preparation is not native evidence. This launcher has no arbitrary input, script,
state-edit or memory-write option; raw observations remain under private/.
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
import sys
from typing import Any
import run_package_resolver_context_v1 as context

safe=context.safe
ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-package-resolver-phase-v1'
COLLECTOR=ROOT/'tools/mesen_package_resolver_phase_v1.lua'
TESTS=ROOT/'tests/test_package_resolver_phase_v1.py'
MAX_TRACE=64*1024*1024
MAX_RECORDS=8192
REVISION='137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1'
REFERENCE=('private/test_runs/resolver_context_20260908_final1/trace.json',10811008,
    '6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679')
ENGINE_PINS={
 'mesen_resolver_phase_2_1_1/SnesCpuTypes.h':'5394d51e2dd6e765eb8805e318d8f1b3407d2bd2a7076047250936e5838d1b9d',
 'mesen_resolver_phase_2_1_1/InternalRegisterTypes.h':'4813491e579eda91d6954153cfa4dceabe36f7feaf22e0c5616cad4936b4fbe3',
 'mesen_resolver_phase_2_1_1/DmaControllerTypes.h':'b03114d7ff465eee145356c204ab95ca110a856f95dc80edfbe1833e7a0537c7',
 'mesen_resolver_phase_2_1_1/SnesPpuTypes.h':'938489933483084a6928f35ab0f634466499c2c4b1c7b1e95a8bd42ef715428b',
 'mesen_nmi_request_2_1_1/Serializer.h':'fa82a8e441b5ce002daf343bf3813443d0b3796cbe1258924b1879fe771f21df',
 'mesen_nmi_request_2_1_1/Serializer.cpp':'b7af6a8b8b628ed6fd44f450a50d1a06af1bb8ce86cb65e44bf1ad978b0fc4a9',
 'mesen_nmi_request_2_1_1/InternalRegisters.cpp':'2b964a17f6cd16bb98f7953d7f8f8036cdf0c1178e87bb204eb846782cf96cbc',
 'mesen_nmi_request_2_1_1/InternalRegisters.h':'d4433c01d99f587d3686a5df72d50fc5942e51ad56ef868987d7ec0bce2a4698',
 'mesen_nmi_request_2_1_1/SnesDmaController.cpp':'f0bd85d5a3001cb3c847980922d6cf2aa19ef294a562a9c827f189328a1cfae6',
 'mesen_nmi_request_2_1_1/SnesDmaController.h':'05a4c63d0f18efd11b12bd476f4bf99bb0d7cd8ba2b51f95bdb463653f82cdfd',
 'mesen_nmi_request_2_1_1/MemoryDumper.cpp':'db1422d7ff1794334f55f5e30a66e3bc859347de42f7dc5425d9ac93e45ca197',
 'mesen_nmi_request_2_1_1/SnesDebugger.cpp':'cdc731b03b249a32305be0e020cbcdb3f13e9f8ca897aeadae142d06ef55bd51',
 'mesen_nmi_request_2_1_1/ScriptManager.h':'c6ec04a297abaf8b6f2927d8d6433278a69fb24df908786ca7a0f74bdea6c8a5',
 'mesen_timing_api_2_1_1/SnesConsole.cpp':'cdfa45011f3dfd39fa5a8686e7f827cb8ea660d5a1b79ecb20da9d0c2606c706',
 'mesen_timing_api_2_1_1/LuaApi.cpp':'fd1292483bd2e7fa1f5a13c392afadcae2d9ff418cab216c964d623f97e10e24',
 'mesen_timing_api_2_1_1/SnesCpu.Shared.h':'dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f',
 'mesen_timing_api_2_1_1/SnesCpu.cpp':'ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8',
 'mesen_timing_api_2_1_1/SnesPpu.cpp':'5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180',
 'mesen_nmi_stack_watchdog_2_1_1/ScriptingContext.cpp':'1e4645ab7783c179a2998e906b72a42bce98c340badb269c0506996229ba0157',
 'mesen_nmi_stack_watchdog_2_1_1/ScriptWindowConfig.cs':'d58e9419defca6c3fd2e182ed23ebb08c39e61b7f5ea677275cf86d9ccb5a51a',
}
BOOL_FIELDS={
 'ppu.overscanMode','ppu.screenInterlace','ppu.objInterlace',
 'cpu.irqLock','cpu.needNmi','internalRegisters.enableNmi',
 'internalRegisters.enableHorizontalIrq','internalRegisters.enableVerticalIrq',
 'internalRegisters.irqFlag','internalRegisters.irqLevel','internalRegisters.nmiFlag',
 'internalRegisters.enableFastRom','dmaController.dmaPending','dmaController.dmaStartDelay',
 'dmaController.needToProcess','dmaController.hdmaPending','dmaController.hdmaInitPending'}
INT_FIELDS={
 'cpu.irqSource':255,'cpu.prevIrqSource':255,'cpu.nmiFlagCounter':255,
 'internalRegisters.horizontalTimer':65535,'internalRegisters.verticalTimer':65535,
 'internalRegisters.needIrq':255,'dmaController.hdmaChannels':255,
 'dmaController.dmaClockCounter':2**32-1}
CHANNEL_BOOL={'decrement','dmaActive','doTransfer','fixedTransfer','hdmaFinished',
 'hdmaIndirectAddressing','invertDirection','unusedControlFlag'}
CHANNEL_INT={'destAddress':255,'hdmaBank':255,'hdmaLineCounterAndRepeat':255,
 'hdmaTableAddress':65535,'srcAddress':65535,'srcBank':255,'transferMode':7,
 'transferSize':65535,'unusedRegister':255}
for channel in range(8):
    prefix=f'dmaController.channel[{channel}].'
    BOOL_FIELDS.update(prefix+k for k in CHANNEL_BOOL)
    INT_FIELDS.update({prefix+k:v for k,v in CHANNEL_INT.items()})
ENGINE_KEYS=BOOL_FIELDS|set(INT_FIELDS)
GATES={f'{x:04X}' for x in (0x7C,0x7D,0x7E,0x7F,0x80,0x81,0x82,0x83,0xA0,
 0x5D9B,0x9876,0x9877,0x9878,0x9879,0x987A,0x987B,0xA0B3,0xA0B4,
 0xA012,0xA013,0xA028,0xAE91,0xAE92,0xAE93,0xAE94,0xCCEA,0xCD01,0xCD02,0xCD2E)}
EXEC_SITES={'pre-effect':0xC1BBD4,'resolver-entry':0xC14612,'resolver-tail':0xC1467F,
 'common-loader-entry':0xC14833,'scene-gate':0xCD1609,'scene-effect-gate':0xCD160E}
RECORD_KEYS={'kind','address','value','poll','cpu','timing','engine','stack','trampolines',
 'gates','context_id','context_kind','context_depth'}
TRAMPOLINES=[0x5C,0x7C,0xE7,0xD1,0x5C,0x97,0xFE,0xD1]
BUS_KINDS={'bus-read','bus-write'}
EVENT_KINDS={'baseline','terminal'}

class PhaseError(ValueError):
    pass

def require(condition:bool,label:str)->None:
    if not condition:raise PhaseError(label)

def sha(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def serial(value:Any)->bytes:return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()

def integer(value:Any,low:int,high:int,label:str)->None:
    require(type(value) is int and low<=value<=high,'integer '+label)

def exact(value:Any,keys:set[str],label:str)->None:
    require(type(value) is dict and set(value)==keys,'exact keys '+label)

def physical_wram(address:int)->int|None:
    bank,offset=address>>16,address&65535
    if bank==0x7E:return offset
    if (bank<0x40 or 0x80<=bank<0xC0) and offset<0x2000:return offset
    return None

def bus_domain(address:int)->str|None:
    physical=physical_wram(address)
    if physical is not None and f'{physical:04X}' in GATES:return 'gate'
    bank,offset=address>>16,address&65535
    if bank<0x40 or 0x80<=bank<0xC0:
        if offset==0x4200 or 0x4207<=offset<=0x420D:return 'interrupt-timer-dma-register'
        if 0x4300<=offset<=0x437F:return 'dma-channel-register'
    return None

def validate_record(row:Any)->None:
    exact(row,RECORD_KEYS,'record')
    kind=row['kind'];require(type(kind) is str and kind in set(EXEC_SITES)|BUS_KINDS|EVENT_KINDS|{'interrupt-entry','interrupt-rti'},'record kind')
    integer(row['address'],0,0xFFFFFF,'address');integer(row['poll'],0,381,'poll')
    integer(row['context_id'],0,4096,'context id');integer(row['context_depth'],0,1,'context depth')
    require(row['context_kind'] in {'main','normal-nmi','battle-irq'},'context kind')
    exact(row['cpu'],context.CPU_KEYS,'CPU')
    cpu=row['cpu']
    for key in context.CPU_KEYS-{'emulationMode'}:
        integer(cpu[key],0,255 if key in {'k','ps','dbr'} else 65535,'CPU '+key)
    require(cpu['emulationMode'] is False and cpu['sp']+12<0x2000,'native low WRAM stack')
    if cpu['ps']&0x10:require(cpu['x']<256 and cpu['y']<256,'X8 index widths')
    for name,size in (('stack',12),('trampolines',8)):
        require(type(row[name]) is list and len(row[name])==size,name+' length')
        for value in row[name]:integer(value,0,255,name+' byte')
    require(row['trampolines']==TRAMPOLINES,'pinned normal interrupt trampolines')
    exact(row['gates'],GATES,'gate bytes')
    for value in row['gates'].values():integer(value,0,255,'gate byte')
    exact(row['engine'],ENGINE_KEYS,'engine fields')
    for key in BOOL_FIELDS:require(type(row['engine'][key]) is bool,'boolean '+key)
    for key,maximum in INT_FIELDS.items():integer(row['engine'][key],0,maximum,key)
    exact(row['timing'],context.TIMING_KEYS,'timing')
    timing=row['timing']
    for key,value in timing.items():integer(value,0,2**53-1,'timing '+key)
    require(timing['masterClock']==timing['memoryManager.masterClock']&0xFFFFFFFF,'full/low clock agreement')
    require(timing['clockRate']==21477270 and timing['ppu.scanline']<=261 and timing['memoryManager.hClock']<=1364,'NTSC clock/raster')
    require(timing['frameCount']==timing['ppu.frameCount'],'frame counters')
    pc=(cpu['k']<<16)|cpu['pc']
    if kind in EXEC_SITES:require(row['address']==pc==EXEC_SITES[kind],'execution address')
    elif kind in {'interrupt-entry','interrupt-rti'}:
        table=context.INTERRUPT_ENTRIES if kind=='interrupt-entry' else context.INTERRUPT_EXITS
        require(row['address']==pc and table.get(pc)==row['context_kind'],'interrupt address/kind')
        if kind=='interrupt-entry':require(cpu['ps']==((row['stack'][0]&~8)|4),'native stacked P')
    elif kind in EVENT_KINDS:require(row['address']==0,'event address')
    else:require(bus_domain(row['address']) is not None,'watched bus domain')
    if kind in BUS_KINDS:integer(row['value'],0,255,'bus byte')
    else:require(type(row['value']) is int and row['value']==-1,'non-bus value sentinel')

def reference_records()->dict[str,dict]:
    path=safe.resolve_private_file(ROOT/REFERENCE[0],'accepted context trace')
    data=safe.read_direct_regular_file(path,'accepted context trace',parent=path.parent,maximum=REFERENCE[1])
    require(len(data)==REFERENCE[1] and sha(data)==REFERENCE[2],'accepted context trace identity')
    trace=json.loads(data);require(trace['schema']==context.SCHEMA and trace['error'] is None,'accepted context schema')
    records=trace['records'];start=next(i for i,r in enumerate(records) if r['kind']=='resolver-entry')
    result={}
    for row in records[start:]:
        kind=row['kind']
        if kind in {'resolver-entry','resolver-tail','common-loader-entry'}:result.setdefault(kind,row)
        if kind in {'interrupt-entry','interrupt-rti'} and row['context_kind'] in {'battle-irq','normal-nmi'}:
            result.setdefault(row['context_kind']+'-'+kind,row)
        if kind=='nmi-effect-latch-read':result.setdefault('scene-effect-gate',row)
        if 'normal-nmi-interrupt-rti' in result:break
    require(set(result)>={'resolver-entry','resolver-tail','common-loader-entry','normal-nmi-interrupt-entry',
        'normal-nmi-interrupt-rti','battle-irq-interrupt-entry','battle-irq-interrupt-rti','scene-effect-gate'},'complete historical reference')
    return result

def summarize(trace:Any,reference:dict[str,dict])->dict[str,Any]:
    exact(trace,{'schema','records','error','terminal_poll'},'trace')
    require(trace['schema']==SCHEMA and trace['error'] is None and type(trace['terminal_poll']) is int and trace['terminal_poll']==381,'collector completion')
    records=trace['records'];require(type(records) is list and 9<=len(records)<=MAX_RECORDS,'bounded record list')
    for row in records:validate_record(row)
    require(records[0]['kind']=='baseline' and records[0]['poll']==0 and records[-1]['kind']=='terminal' and records[-1]['poll']==381,'baseline/terminal')
    counts=Counter(r['kind'] for r in records)
    for kind in ('baseline','terminal','resolver-entry','resolver-tail','common-loader-entry','scene-gate','scene-effect-gate'):
        require(counts[kind]==1,'exact one '+kind)
    require(counts['pre-effect']<=1,'optional single pre-effect')
    live=None;window=False;resolved=False;closed=False;last=(-1,-1,-1,-1)
    phases={};pairs=[];selected_order=[];bus_counts=Counter();reference_matches=[]
    last_context_id=0;scene_read_witness=False
    for index,row in enumerate(records):
        kind=row['kind'];t=row['timing'];now=(row['poll'],t['memoryManager.masterClock'],t['cpu.cycleCount'],t['ppu.frameCount'])
        require(all(a>=b for a,b in zip(now,last)),'monotonic counters');last=now
        if kind=='pre-effect':
            require(not window and not resolved and not closed,'pre-effect ordering');window=True
        if kind=='resolver-entry':
            require(not resolved and not closed and live is None,'resolver ordering');window=True;resolved=True
            g=row['gates'];require(row['poll']==378 and (g['9877']|(g['9878']<<8))==8 and (g['A0B3']|(g['A0B4']<<8))==0,'primary selector/branch/poll')
        if kind in {'resolver-tail','common-loader-entry'}:
            require(resolved and window and live is None,'main resolver continuation')
        if kind=='common-loader-entry':require('resolver-tail' in phases,'tail before common loader')
        if kind=='interrupt-entry':
            require(window and resolved and 'common-loader-entry' in phases and live is None,'selected interrupt ordering/non-nesting')
            require(row['context_id']>last_context_id,'increasing context identity');last_context_id=row['context_id']
            live=row;selected_order.append(row['context_kind'])
        if live is None:require((row['context_id'],row['context_depth'],row['context_kind'])==(0,0,'main'),'unowned context')
        else:require((row['context_id'],row['context_depth'],row['context_kind'])==(live['context_id'],1,live['context_kind']),'paired context identity')
        if kind in {'scene-gate','scene-effect-gate'}:
            require(live is not None and live['context_kind']=='normal-nmi' and resolved and window,'scene gate within selected NMI')
            if kind=='scene-effect-gate':require('scene-gate' in phases,'scene gate ordering')
        if kind in BUS_KINDS:
            require(window and not closed,'bus observation window');bus_counts[kind+'/'+bus_domain(row['address'])]+=1
            # A read's callback value must agree with its side-effect-free WRAM
            # snapshot at this callback; write callbacks precede the actual write.
            physical=physical_wram(row['address'])
            if kind=='bus-read' and physical is not None:
                require(row['value']==row['gates'][f'{physical:04X}'],'gate read/snapshot agreement')
                if physical==0x5D9B and live is not None and live['context_kind']=='normal-nmi' and 'scene-effect-gate' in phases:
                    scene_read_witness=True
        if kind=='interrupt-rti':
            require(live is not None and row['stack']==live['stack'],'intact selected interrupt stack window')
            for key in ('a','x','y','d','dbr','sp','emulationMode'):
                require(row['cpu'][key]==live['cpu'][key],'interrupt preserved '+key)
            pairs.append({'kind':live['context_kind'],'entry_clock':live['timing']['memoryManager.masterClock'],
                'rti_clock':t['memoryManager.masterClock'],'entry_sp':live['cpu']['sp'],
                'entry_engine':live['engine'],'rti_engine':row['engine']})
            live=None
            if row['context_kind']=='normal-nmi':window=False;closed=True
        refkind=row['context_kind']+'-'+kind if kind in {'interrupt-entry','interrupt-rti'} else kind
        if refkind in reference:
            old=reference[refkind]
            for key in ('cpu','stack','trampolines','timing'):
                require(row[key]==old[key],'historical phase '+refkind+' '+key)
            for key in GATES&set(old['wram']):require(row['gates'][key]==old['wram'][key],'historical gate '+refkind+' '+key)
            reference_matches.append(refkind)
        if kind in EXEC_SITES:phases[kind]={'index':index,'poll':row['poll'],'clock':t['memoryManager.masterClock'],
            'cpu_cycles':t['cpu.cycleCount'],'engine':row['engine']}
    require(live is None and closed and not window,'closed observation window')
    require(selected_order==['battle-irq','normal-nmi'] and len(pairs)==2,'retained first IRQ/NMI sequence')
    require(scene_read_witness,'selected scene effect-gate read positive control')
    require(set(reference_matches)==set(reference),'all historical phases matched')
    require(phases['resolver-tail']['index']>phases['resolver-entry']['index'],'resolver tail ordering')
    return {'record_count':len(records),'event_counts':dict(sorted(counts.items())),
        'bus_counts':dict(sorted(bus_counts.items())),'phases':phases,'interrupt_pairs':pairs,
        'historical_phase_matches':reference_matches,'engine_field_count':len(ENGINE_KEYS),
        'resolver_to_tail_master_clocks':phases['resolver-tail']['clock']-phases['resolver-entry']['clock'],
        'resolver_to_tail_cpu_counter':phases['resolver-tail']['cpu_cycles']-phases['resolver-entry']['cpu_cycles'],
        'native_helper_executed':False,'interrupt_exclusion_proved':False,'complete_dma_bus_trace':False,
        'deadline_certified':False,'production_approval':False}

def read_bounded(path:Path,maximum:int,label:str)->bytes:
    return safe.read_direct_regular_file(path,label,parent=path.parent,maximum=maximum)

def parse_trace(raw:bytes)->Any:
    require(len(raw)<=MAX_TRACE,'trace byte bound')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate JSON key '+key);result[key]=value
        return result
    def constant(value):raise PhaseError('non-finite JSON constant '+value)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)

def source_paths()->dict[str,Path]:
    paths={'launcher':Path(__file__).resolve(),'collector':COLLECTOR,'tests':TESTS,
        'context_launcher':Path(context.__file__).resolve(),'isolation_library':Path(safe.__file__).resolve(),
        'reference_trace':ROOT/REFERENCE[0]}
    for relative,pin in ENGINE_PINS.items():
        path=ROOT/'private/research'/relative
        require(sha(path.read_bytes())==pin,'engine source pin '+relative)
        paths['engine_'+path.name.replace('.','_')]=path
    for key,pin in {'context_launcher':'88ccf83e83a68f7bbdc3c65e626b1480041c9e95db4fe36541a6c267b8030214',
        'isolation_library':'d5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96'}.items():
        require(sha(paths[key].read_bytes())==pin,'accepted dependency '+key)
    return paths

def run(output_dir:Path)->dict[str,Any]:
    private=safe.canonical_private_root();inputs={}
    for key,(relative,size,pin) in context.PINNED.items():
        path=safe.resolve_private_file(ROOT/relative,key,private_root=private)
        require(path.stat().st_size==size and safe.sha256_file(path)==pin,'pinned '+key);inputs[key]=path
    runtime={key:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/name,key,private_root=private) for key,name in safe.RUNTIME_NAMES.items()}
    for key,path in runtime.items():safe.require_identity(path,key)
    sources=source_paths();guarded={**inputs,**runtime,**sources}
    before={key:safe.sha256_file(path) for key,path in guarded.items()};reference=reference_records()
    output=safe.prepare_private_output_dir(output_dir,private_root=private,
        forbidden_roots=tuple(path.parent for path in inputs.values())+(safe.DEFAULT_MESEN.parent,))
    archive=output/'source_archive';archive.mkdir();archives={}
    for key,path in sources.items():
        if key=='reference_trace':continue
        target=archive/(key+path.suffix);safe.copy_new_regular_file(path,target,key);archives[key]=target
    archive_before={key:safe.sha256_file(path) for key,path in archives.items()}
    require(all(archive_before[key]==before[key] for key in archives),'exact archived bytes')
    stage=output/'staged';app=stage/'app';saves=app/'Saves';saves.mkdir(parents=True);staged={}
    for key,name in safe.RUNTIME_NAMES.items():
        staged[key]=app/name;safe.copy_new_regular_file(runtime[key],staged[key],key)
    stem='pe_resolver_phase_'+secrets.token_hex(12)
    for key,path in inputs.items():
        target=saves/(stem+'.srm') if key=='sram' else stage/(stem+('.sfc' if key=='rom' else '.mss'))
        safe.copy_new_regular_file(path,target,key);staged[key]=target
    staged['collector']=stage/'collector.lua';safe.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    stage_before={key:safe.sha256_file(path) for key,path in staged.items()}
    require(all(stage_before[key]==before[key] for key in staged),'exact staged bytes')
    receipt={'schema':SCHEMA,'source_hashes':before,'staged_hashes':stage_before,
        'source_archive_hashes':archive_before,'source_archive_files':{key:path.name for key,path in archives.items()}}
    (output/'launch_inputs.json').write_bytes(serial(receipt))
    env=safe.minimal_subprocess_environment()
    for key,parts in {'USERPROFILE':('profile',),'APPDATA':('profile','AppData','Roaming'),
        'LOCALAPPDATA':('profile','AppData','Local'),'TEMP':('temp',),'TMP':('temp',)}.items():
        path=stage.joinpath(*parts);path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    env.update(PE_RESOLVER_PHASE_PROTOCOL=SCHEMA,PE_RESOLVER_PHASE_STATE=str(staged['state']),
        PE_RESOLVER_PHASE_TRACE=str(output/'trace.json'))
    command=[str(staged['mesen']),'--testRunner','--timeout=900','--doNotSaveSettings',
        '--debug.scriptWindow.allowIoOsAccess=true','--snes.ramPowerOnState=AllZeros',
        '--snes.port1.type=SnesController',str(staged['collector']),str(staged['rom'])]
    process=None;error=None
    try:
        process=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=915,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,check=False)
        (output/'process.log').write_bytes(process.stdout+process.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:error=str(exc)
    process_receipt={'schema':SCHEMA,'returncode':process.returncode if process else None,'exception':error}
    (output/'process_receipt.json').write_bytes(serial(process_receipt))
    safe.require_file_hashes_unchanged(guarded,before,'source')
    safe.require_file_hashes_unchanged(staged,stage_before,'staged')
    safe.require_file_hashes_unchanged(archives,archive_before,'source archive')
    require((output/'launch_inputs.json').read_bytes()==serial(receipt),'unchanged launch receipt')
    require(sorted(path.name for path in archive.iterdir())==sorted(path.name for path in archives.values()),'exact archive inventory')
    safe.require_exact_staged_save_entries(sorted(path.name for path in saves.iterdir()),staged['sram'].name)
    require(process is not None and error is None and process.returncode==52,'native observation failed; private artifacts retained')
    require(not (output/'trace.json.error.txt').exists(),'collector error sidecar absent')
    trace_path=output/'trace.json'
    raw=read_bounded(trace_path,MAX_TRACE,'phase trace')
    try:observations=summarize(parse_trace(raw),reference)
    except (ValueError,KeyError,TypeError) as exc:
        (output/'host_rejection.json').write_bytes(serial({'schema':SCHEMA,'error':str(exc),'trace_sha256':sha(raw)}));raise
    result={**receipt,'evidence_level':'exploratory-runtime-not-accepted','observations':observations,
        'trace_sha256':sha(raw),'process_receipt_sha256':sha(serial(process_receipt)),
        'sources_staged_archives_unchanged':True,'checkpoint_load_only':True,
        'controller_schedule_reused':True,'rom_cpu_memory_edits':False,'production_approval':False}
    (output/'manifest.json').write_bytes(serial(result));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    sys.stdout.buffer.write((json.dumps(run(parser.parse_args().output_dir),indent=2)+'\n').encode())
