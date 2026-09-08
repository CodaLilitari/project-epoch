"""Original immutable-ROM helper with separately scoped real NMI observation.

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
import run_schala_package_helper_v3_rom as v3
import run_schala_package_helper_v2_stack as v2
import audit_mesen_nmi_phase_contract_v2 as phase_audit

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-package-helper-v4-rom-nmi-calibrated-v3'
COLLECTOR=ROOT/'tools/mesen_schala_package_helper_v4_rom_nmi.lua'
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIME_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
FLAG_KEYS={'internalRegisters.nmiFlag','internalRegisters.enableNmi','internalRegisters.enableHorizontalIrq',
    'internalRegisters.enableVerticalIrq','internalRegisters.enableAutoJoypadRead','cpu.nmiFlagCounter','cpu.needNmi',
    'cpu.irqLock','cpu.irqSource','cpu.prevIrqSource','dmaController.needToProcess','dmaController.hdmaChannels',
    'dmaController.hdmaPending','dmaController.hdmaInitPending','dmaController.dmaStartDelay','dmaController.dmaPending'}
HANDLER_PCS=(0x8080,0x8081,0x8083,0x8084,0x8088,0x8089,0x808D,0x808E,0x808F)
INTEGER_FLAGS={'cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'}
PHASE_LIMIT=262
ACTIVE_CLOCK_LIMIT=120000
POST_RTI_CLOCK_LIMIT=80000
CALIBRATION_REFERENCE_SHA256='8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb'
PHASE_SOURCE_FILES=(
    ('phase_ppu_source','private/research/mesen_timing_api_2_1_1/SnesPpu.cpp','5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180'),
    ('phase_memory_source','private/research/mesen_timing_api_2_1_1/SnesMemoryManager.cpp','2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58'),
    ('phase_dma_source','private/research/mesen_nmi_request_2_1_1/SnesDmaController.cpp','f0bd85d5a3001cb3c847980922d6cf2aa19ef294a562a9c827f189328a1cfae6'),
    ('phase_cpu_source','private/research/mesen_timing_api_2_1_1/SnesCpu.cpp','ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8'),
    ('phase_cpu_shared_source','private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h','dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f'),
    ('phase_cpu_instructions_source','private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h','9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd'),
    ('phase_script_manager_source','private/research/mesen_nmi_request_2_1_1/ScriptManager.h','c6ec04a297abaf8b6f2927d8d6433278a69fb24df908786ca7a0f74bdea6c8a5'),
    ('phase_debugger_source','private/research/mesen_nmi_request_2_1_1/Debugger.cpp','71fa7d663b8cb61c7290bdf404244270a8c9d3f907224c990b43ae82a6c95db3'),
)
ARCHIVE_KEYS=('collector','launcher','nmi_tests','v3_library','v3_collector','v3_model','v3_tests','v3_reference',
    'v2_library','helper','host_adapter','isolation_library','v0_library','v1_library',
    'phase_audit','prior_phase_audit','phase_reference','previous_nmi_launcher','previous_nmi_collector',
    'previous_nmi_tests','previous_nmi_reference','original_fixture_source','package_policy_source',
    'policy_reference','grammar_source','grammar_reference','adapter_reference',
    'cartridge_completion','cartridge_build_audit','design','phase_extension',
    'phase_ppu_source','phase_memory_source','phase_dma_source','phase_cpu_source','phase_cpu_shared_source','phase_cpu_instructions_source',
    'phase_script_manager_source','phase_debugger_source','calibration_reference',
    'calibration_launcher','calibration_collector','calibration_tests','calibration_metadata','calibration_report')
SUCCESS_BOUNDARIES={
    'allocate-tcs':(0x410043,0x410044,8,50),
    'first-countbits-jsr':(0x4100EE,0x410232,50,52),
    'release-tcs':(0x410215,0x410216,50,8),
    'pull-p':(0x41021A,0x41021B,1,0),
    'success-jml-tail':(0x41021B,0x008110,0,0),
}

SAFE=v2.safe


class ConformanceError(RuntimeError):pass


def require(test:bool,message:str)->None:
    if not test:raise ConformanceError(message)


def canonical(value)->bytes:return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()


def with_boundary(case:dict,name:str,spec:tuple[int,int,int,int])->dict:
    c=copy.deepcopy(case);before,after,depth_before,depth_after=spec
    normal_depth=(52 if c['countbits_reached'] else 50) if c['frame_allocated'] else 8
    c.update(name=c['name']+'-nmi-'+name,nmi_trigger=before,nmi_resume=after,
             nmi_boundary=name,nmi_depth_before=depth_before,nmi_depth_after=depth_after,
             nmi_max_depth=max(normal_depth,depth_after+7),nmi_phase_limit=PHASE_LIMIT)
    return c


def build_cases(payload:bytes,registry:bytes,scope:str='matrix')->list[dict]:
    require(scope in ('pilot','matrix'),'unknown fixed matrix scope')
    result=[]
    for sp in v3.ENTRY_STACKS:
        for selector in range(0x80,0x84):
            for flag in (0,0x40):
                for status in (0,0xC3,0x4C,0x8F):
                    c=v3.model.make_case(payload,registry,f'bound-{selector:02X}-flag-{flag:02X}-status-{status:02X}',
                        selector,flag,sp=sp,status=status)
                    names=SUCCESS_BOUNDARIES if status==0 else ('first-countbits-jsr',)
                    for name in names:
                        if scope=='pilot' and (selector!=0x80 or flag!=0 or status!=0 or name!='first-countbits-jsr'):continue
                        result.append(with_boundary(c,name,SUCCESS_BOUNDARIES[name]))
        if scope!='pilot':
            for status in (0,0x8F):
                for route,selector,specs in (
                    ('canonical',0x7F,{'canonical-pull-p':(0x410019,0x41001A,1,0),'canonical-jml-tail':(0x41001E,0x008100,0,0)}),
                    ('early-refusal',0x90,{'refusal-pull-p':(0x41022D,0x41022E,1,0),'refusal-jml-tail':(0x41022E,0x008120,0,0)}),
                    ('framed-refusal',0x84,{'refusal-release-tcs':(0x410226,0x410227,50,8),'refusal-jml-tail':(0x41022E,0x008120,0,0)})):
                    c=v3.model.make_case(payload,registry,route+f'-status-{status:02X}',selector,0,sp=sp,status=status)
                    for name,spec in specs.items():result.append(with_boundary(c,name,spec))
    require(len(result)==(2 if scope=='pilot' else 152) and len(result)==len({c['name'] for c in result}),'exact unique NMI case count')
    return result


def physical(address:int)->int:
    bank,offset=address>>16,address&65535
    if (bank<=0x3F or 0x80<=bank<=0xBF) and offset<0x2000:return 0x7E0000+offset
    return address


def validate_sites(cases:list[dict],code:bytes)->None:
    require(sha(code)==v3.HELPER_SHA256,'unchanged exact helper required')
    for c in cases:
        require(c['cpu']['sp'] in (0x1FEF,0x06D8) and c['nmi_phase_limit']==PHASE_LIMIT,'case stack/phase allowlist')
        before,after=c['nmi_trigger'],c['nmi_resume'];offset=before-v3.CODE
        require(0<=offset<len(code),'trigger outside helper')
        opcode=code[offset]
        if opcode==0x20:predicted=0x410000+int.from_bytes(code[offset+1:offset+3],'little')
        elif opcode==0x5C:predicted=int.from_bytes(code[offset+1:offset+4],'little')
        else:
            require(opcode in (0x08,0x1B,0x8F,0xE2,0xAB,0x7A,0xFA,0x68,0x28),'unreviewed boundary opcode')
            predicted=before+(4 if opcode==0x8F else 2 if opcode==0xE2 else 1)
        require(after==predicted,'boundary continuation does not match exact instruction bytes')
        normal=(52 if c['countbits_reached'] else 50) if c['frame_allocated'] else 8
        require(c['nmi_max_depth']==max(normal,c['nmi_depth_after']+7) and 7<=c['nmi_max_depth']<=59,'combined depth contract')


def nz16(ps:int,value:int)->int:return (ps&~0x82)|(0x80 if value&0x8000 else 0)|(2 if value==0 else 0)


def require_archive_hashes(actual:dict,guarded:dict)->None:
    require(set(actual)==set(ARCHIVE_KEYS),'source archive key set mismatch')
    require(all(type(actual[k]) is str and len(actual[k])==64 and actual[k]==guarded[k] for k in ARCHIVE_KEYS),
            'source archive differs from guarded prelaunch sources')


def require_prior_v3_sources()->None:
    data=(ROOT/'references/schala_package_helper_v3_rom.json').read_bytes()
    require(sha(data)=='4c6c469ffde9c75517b1b7087f6c8956e2b2b2637355b87a99a1ae7981d15677',
        'preserved accepted ROM-helper reference drift')
    for row in json.loads(data)['source_identities'].values():
        content=(ROOT/row['path']).read_bytes()
        require(len(content)==row['size_bytes'] and sha(content)==row['sha256'],
            'preserved accepted ROM-helper source drift')


def read_calibration_reference()->dict:
    require(len(CALIBRATION_REFERENCE_SHA256)==64,'calibration acceptance not yet populated')
    data=(ROOT/'references/schala_package_helper_v4_timing_calibration.json').read_bytes()
    require(sha(data)==CALIBRATION_REFERENCE_SHA256,'accepted calibration reference drift')
    reference=json.loads(data)
    require(reference.get('schema')=='project-epoch-package-helper-v4-timing-calibration-accepted-pair' and
        reference.get('elapsed_projections_identical') is True and reference.get('schedules_identical') is True and
        reference.get('schedule_is_inference') is True and reference.get('schedule_executed') is False and
        reference.get('schedule_elapsed_basis')=='fixture-baseline-before-original-entry-JML','accepted calibration scope')
    require(type(reference.get('schedule')) is list and len(reference['schedule'])==92,'calibration schedule extent')
    import collect_schala_package_helper_v4_timing_calibration as calibrated
    require((json.dumps(calibrated.collect(),indent=2)+'\n').encode()==data,'calibration full evidence no longer reproduces its accepted reference')
    for _,path,expected in PHASE_SOURCE_FILES:require(sha((ROOT/path).read_bytes())==expected,'pinned phase/housekeeping source drift')
    return reference


def apply_calibration(cases:list[dict],schedule:list[dict])->list[dict]:
    """Use an explicit source-bound table; actual request phase remains decisive."""
    require(type(schedule) is list and schedule,'calibration schedule missing')
    by_key={}
    for row in schedule:
        require(type(row) is dict and set(row)=={'selector','flag','sp','trigger','elapsed_master_clocks',
            'start_scanline','observed_rise_scanline','boundary','group_name'},'calibration schedule row')
        for key in ('selector','flag','sp','trigger','elapsed_master_clocks','start_scanline','observed_rise_scanline'):
            require(type(row.get(key)) is int,'calibration exact integer '+key)
        require(type(row.get('boundary')) is str and type(row.get('group_name')) is str,'calibration named group/boundary')
        require(0<=row['observed_rise_scanline']<PHASE_LIMIT and 0<=row['start_scanline']<PHASE_LIMIT and
            0<=row['elapsed_master_clocks']<ACTIVE_CLOCK_LIMIT,'calibration clock/raster bounds')
        inferred=(row['observed_rise_scanline']+3-(row['elapsed_master_clocks']+1363)//1364)%PHASE_LIMIT
        require(row['start_scanline']==inferred,'calibration schedule formula differs')
        key=(row['selector'],row['flag'],row['sp'],row['boundary'])
        require(key not in by_key,'duplicate calibration key');by_key[key]=row
    result=[]
    for original in cases:
        c=copy.deepcopy(original);key=(c['selector'],c['flag'],c['cpu']['sp'],c['nmi_boundary'])
        require(key in by_key,'calibration coverage missing')
        row=by_key[key];require(row['trigger']==c['nmi_trigger'],'calibration trigger differs from fixed helper site')
        c.update(nmi_start_scanline=row['start_scanline'],nmi_rise_scanline=row['observed_rise_scanline'],
            nmi_calibration_group=row['group_name'],nmi_calibration_elapsed_clocks=row['elapsed_master_clocks'])
        result.append(c)
    return result


def require_raster_clock_interval(before:dict,after:dict,rise:int)->None:
    """Pinned noninterlaced raster: each crossed line is 1360..1364 clocks."""
    def position(t):return t['ppu.frameCount']*PHASE_LIMIT+(t['ppu.scanline']-rise)%PHASE_LIMIT
    lines=position(after)-position(before)
    horizontal=after['memoryManager.hClock']-before['memoryManager.hClock']
    elapsed=after['memoryManager.masterClock']-before['memoryManager.masterClock']
    require(lines>=0 and lines*1360+horizontal<=elapsed<=lines*1364+horizontal,
        'raster advancement inconsistent with full master clocks')


def validate_publication_init_clear_witness(events:list[dict],start:int,end:int)->None:
    """Exact 38-clock sampled clear across original STA long,X -> LDA $05,S.

    This owns a sparse-observation interval, not 38 clocks of pending DMA.
    ProcessCpuCycle services the zero-channel init before the unretained opcode
    fetch; the next retained data callback follows opcode/operand/idle cycles.
    """
    require(start>0 and end==start+3,'extended sampled clear has wrong event count')
    before,low,high,execute,read=events[start-1:end+1]
    require(before['kind']=='exec' and before['address']==0x4101DF and before['value']==0x9F and
        execute['kind']=='exec' and execute['address']==0x4101E3 and execute['value']==0xA3,
        'extended sampled clear has wrong original instruction pair')
    require(low['kind']==high['kind']=='write' and read['kind']=='read','extended sampled clear memory ordering')
    cpu=before['cpu'];after_store={**cpu,'pc':0x01E3};after_operand={**cpu,'pc':0x01E5}
    require(cpu['k']==0x41 and cpu['pc']==0x01DF and not cpu['emulationMode'] and not cpu['ps']&0x20 and
        low['cpu']==high['cpu']==execute['cpu']==after_store and read['cpu']==after_operand,
        'extended sampled clear instruction CPU ownership')
    address=(0x7E5DBD+cpu['x'])&0xFFFFFF
    require(low['address']==low['bus_address']==address and high['address']==high['bus_address']==address+1 and
        low['value']==cpu['a']&255 and high['value']==cpu['a']>>8 and
        read['address']==0x7E0000+((cpu['sp']+5)&65535) and read['bus_address']==((cpu['sp']+5)&65535),
        'extended sampled clear physical publication/stack address or value')
    require(low['exec_index']==high['exec_index']==before['exec_index'] and
        execute['exec_index']==read['exec_index']==before['exec_index']+1,'extended sampled clear opcode ordinal ownership')
    for a,b,clocks,cycles in ((before,low,40,5),(low,high,8,1),(high,execute,0,0),(execute,read,30,4)):
        require(b['timing']['memoryManager.masterClock']-a['timing']['memoryManager.masterClock']==clocks and
            b['timing']['cpu.cycleCount']-a['timing']['cpu.cycleCount']==cycles,'extended sampled clear exact clock/cycle intervals')
    require(low['flags']['dmaController.dmaStartDelay'] is True and
        high['flags']['dmaController.dmaStartDelay'] is False and execute['flags']['dmaController.dmaStartDelay'] is False and
        read['timing']['ppu.scanline']==0 and read['timing']['memoryManager.hClock']<=64,'extended sampled clear delay/raster witness')


def validate_zero_channel_init(events:list[dict],request_i:int,resume_i:int)->list[int]:
    """Raster-start bookkeeping can be pending even with every HDMA channel off."""
    observed=[];start_clock=None;start_index=None;episodes=0;delay_cleared=False
    for i,e in enumerate(events):
        f=e['flags'];pending=f['dmaController.hdmaInitPending'];delay=f['dmaController.dmaStartDelay']
        require(all(f[k]==0 for k in ('dmaController.hdmaChannels','dmaController.hdmaPending','dmaController.dmaPending','cpu.irqLock')),
            'zero-channel bookkeeping has transfer or CPU-lock state')
        require(f['dmaController.needToProcess']==(pending or delay),'disabled-channel init pending-flag relation')
        if pending or delay:
            require(pending and not request_i<=i<=resume_i and e['timing']['ppu.scanline']==0 and
                12<=e['timing']['memoryManager.hClock']<=64,'zero-channel init outside declared raster boundary')
            if start_clock is None:
                episodes+=1;require(episodes==1,'repeated zero-channel init episode')
                start_clock=e['timing']['memoryManager.masterClock']
                start_index=i
            require(not delay or not delay_cleared,'zero-channel init delay restarted')
            if not delay:delay_cleared=True
            observed.append(i)
        elif start_clock is not None:
            elapsed=e['timing']['memoryManager.masterClock']-start_clock
            if elapsed>32:
                require(elapsed==38,'zero-channel init did not clear promptly')
                validate_publication_init_clear_witness(events,start_index,i)
            start_clock=None
    require(start_clock is None,'zero-channel init has no observed clear')
    return observed


def validate_phase(events:list[dict],case:dict,prep:dict,request_i:int,resume_i:int)->None:
    """Natural scheduled setup, decisive request/RTI window, bounded continuation."""
    base=events[0];request=events[request_i];resume=events[resume_i]
    require(type(prep) is dict and set(prep)=={'wait_start_clock','latch_rise'} and set(prep['latch_rise'])=={'before','after'},'natural latch transition shape')
    false,risen=prep['latch_rise']['before'],prep['latch_rise']['after']
    for sample in (false,risen):
        require(set(sample)=={'clock','cycles','frame','scanline','hclock','latch','peek'} and type(sample['latch']) is bool,'phase sample shape')
        require(all(type(x) is int and 0<=x<2**64 for k,x in sample.items() if k!='latch'),'phase sample integer')
        require(sample['peek']<=255 and sample['scanline']<PHASE_LIMIT and sample['hclock']<1364,'phase sample bounds')
    require(type(prep['wait_start_clock']) is int and 0<=prep['wait_start_clock']<=false['clock'] and
        base['timing']['memoryManager.masterClock']-prep['wait_start_clock']<800000,'phase wait bounds')
    require(0<risen['clock']-false['clock']<=32 and false['cycles']<risen['cycles'] and risen['frame'] in (false['frame'],false['frame']+1),'consecutive idle transition bracket')
    require(false['latch'] is False and risen['latch'] is True and not false['peek']&128 and risen['peek']&128 and
        false['clock']<risen['clock']<=base['timing']['memoryManager.masterClock'],'natural latch transition evidence')
    start=case.get('nmi_start_scanline');rise=case.get('nmi_rise_scanline')
    require(type(start) is int and type(rise) is int and 0<=start<PHASE_LIMIT and rise==risen['scanline'],'calibrated phase plan missing or changed')
    require(base['timing']['ppu.scanline']==start and base['timing']['ppu.frameCount']==risen['frame'] and
        base['timing']['cpu.cycleCount']>=risen['cycles'],'scheduled natural baseline raster/frame/cycles')
    require(base['flags']['internalRegisters.nmiFlag'] is (start>=rise),'scheduled baseline latch phase')
    anchor={'ppu.frameCount':risen['frame'],'ppu.scanline':risen['scanline'],
        'memoryManager.hClock':risen['hclock'],'memoryManager.masterClock':risen['clock']}
    preceding={'ppu.frameCount':false['frame'],'ppu.scanline':false['scanline'],
        'memoryManager.hClock':false['hclock'],'memoryManager.masterClock':false['clock']}
    require_raster_clock_interval(preceding,anchor,rise)
    require_raster_clock_interval(anchor,base['timing'],rise)
    last_position=None
    base_clock=base['timing']['memoryManager.masterClock'];base_frame=base['timing']['ppu.frameCount']
    for e in events:
        t=e['timing'];scan=t['ppu.scanline'];frame=t['ppu.frameCount']
        require(0<=scan<PHASE_LIMIT and 0<=t['memoryManager.masterClock']-base_clock<ACTIVE_CLOCK_LIMIT and
            frame-base_frame in (0,1),'bounded active raster/frame/full clock')
        position=(frame*PHASE_LIMIT+(scan-rise)%PHASE_LIMIT,t['memoryManager.hClock'])
        require(last_position is None or position>=last_position,'raster/frame order reversal');last_position=position
        require(bool(e['latch_peek']&128)==e['flags']['internalRegisters.nmiFlag'],'latch/peek disagreement')
    for a,b in zip(events,events[1:]):require_raster_clock_interval(a['timing'],b['timing'],rise)
    for e in events[request_i:resume_i+1]:
        require(e['flags']['internalRegisters.nmiFlag'] is True and e['latch_peek']&128 and
            rise<=e['timing']['ppu.scanline']<case['nmi_phase_limit'] and
            e['timing']['ppu.frameCount']==request['timing']['ppu.frameCount'],'request-through-RTI left natural VBlank')
    require(events[-1]['timing']['memoryManager.masterClock']-resume['timing']['memoryManager.masterClock']<=POST_RTI_CLOCK_LIMIT,
        'post-RTI continuation full-clock budget')
    # Before a preblank start reaches the request, the active helper itself
    # witnesses the next natural latch edge. No frame/latch is manufactured.
    if start<rise:
        edges=[(a,b) for a,b in zip(events[:request_i],events[1:request_i+1])
            if not a['flags']['internalRegisters.nmiFlag'] and b['flags']['internalRegisters.nmiFlag']]
        require(len(edges)==1 and edges[0][1]['timing']['ppu.scanline']==rise and
            request['timing']['ppu.frameCount']==base_frame+1,'active preblank natural latch transition')
    else:require(request['timing']['ppu.frameCount']==base_frame,'late-phase request moved to another frame')


def validate_handler(events:list[dict],exec_events:list[tuple[int,dict]],interrupted:dict,counter:int)->set[int]:
    observed=[e for _,e in exec_events if e['address'] in HANDLER_PCS]
    require([e['address'] for e in observed]==list(HANDLER_PCS),'complete exact handler instruction sequence')
    expected=dict(interrupted);expected.update(k=0,pc=0x8080,sp=interrupted['sp']-4,ps=(interrupted['ps']&~8)|4)
    entry_ps=expected['ps'];saved_a=expected['a'];counter_after=(counter+1)&65535
    states=[]
    for pc in HANDLER_PCS:
        expected['pc']=pc;states.append(dict(expected))
        if pc==0x8080:expected['sp']-=1
        elif pc==0x8081:expected['ps']&=~0x20
        elif pc==0x8083:expected['sp']-=2
        elif pc==0x8084:expected.update(a=counter,ps=nz16(expected['ps'],counter))
        elif pc==0x8088:expected.update(a=counter_after,ps=nz16(expected['ps'],counter_after))
        elif pc==0x808D:expected.update(a=saved_a,ps=nz16(expected['ps'],saved_a),sp=expected['sp']+2)
        elif pc==0x808E:expected.update(ps=entry_ps,sp=expected['sp']+1)
    require([e['cpu'] for e in observed]==states,'exact handler CPU instruction states')
    epochs={e['exec_index']:e['address'] for e in observed};s=interrupted['sp'];k=interrupted['k'];pc=interrupted['pc']
    # Actual stack callbacks are pre-write and post-increment-for-pull in this
    # pinned emulator. Every handler memory operation has an exact owner/SP.
    expected_memory=[
        (0x8080,'write',0x7E0000+s-4,entry_ps,s-4),
        (0x8083,'write',0x7E0000+s-5,saved_a>>8,s-5),(0x8083,'write',0x7E0000+s-6,saved_a&255,s-6),
        (0x8084,'read',0x7E5EF0,counter&255,s-7),(0x8084,'read',0x7E5EF1,counter>>8,s-7),
        (0x8089,'write',0x7E5EF0,counter_after&255,s-7),(0x8089,'write',0x7E5EF1,counter_after>>8,s-7),
        (0x808D,'read',0x7E0000+s-6,saved_a&255,s-6),(0x808D,'read',0x7E0000+s-5,saved_a>>8,s-5),
        (0x808E,'read',0x7E0000+s-4,entry_ps,s-4),
        (0x808F,'read',0x7E0000+s-3,interrupted['ps'],s-3),
        (0x808F,'read',0x7E0000+s-2,pc&255,s-2),(0x808F,'read',0x7E0000+s-1,pc>>8,s-1),
        (0x808F,'read',0x7E0000+s,k,s)]
    memory=[e for e in events if e['kind'] in ('read','write') and e['exec_index'] in epochs]
    require([(epochs[e['exec_index']],e['kind'],e['address'],e['value'],e['cpu']['sp']) for e in memory]==expected_memory,
            'complete exact handler memory sequence/ownership/SP')
    return set(epochs)


def validate_record(row:dict,case:dict,code:bytes,handler:bytes,*,payload:bytes,registry:bytes)->dict:
    require(type(row) is dict and type(case) is dict and type(code) is bytes and type(handler) is bytes and len(handler)==16,'validator input shape')
    require(set(row)=={'name','route','events','changes','preparation','input_fixture_before_hex','input_fixture_after_hex',
        'retired_scratch_before_hex','retired_scratch_after_hex','descriptor_fixture_before_hex','descriptor_fixture_after_hex'},'record shape')
    require(row['name']==case['name'] and row['route']==case['route'],'case/route mismatch')
    events=row['events'];require(type(events) is list and 20<len(events)<20000,'event bound')
    kinds={'fixture-baseline','exec','read','write','request-before','request-after','handler-entry','disable-before','disable-after','pre-rti','post-rti'}
    counts={};exec_events=[];previous=(-1,-1,-1);epoch=0
    v3.model.require_components(payload,registry)
    require(all(row[k]==registry.hex() for k in ('input_fixture_before_hex','input_fixture_after_hex')) and
        all(row[k]==payload.hex() for k in ('descriptor_fixture_before_hex','descriptor_fixture_after_hex')),
        'exact immutable ROM input snapshots')
    ledger=dict(case['patches'])
    # Unlike the WRAM-code experiment, interrupt dummy reads now address ROM.
    # Bind their actual bytes as well as all ordinary registry/package reads.
    rom_data={v3.CODE+i:b for i,b in enumerate(code)}
    rom_data.update({0x420000+i:b for i,b in enumerate(payload)})
    rom_data.update({0x430000+i:b for i,b in enumerate(registry)})
    rom_data.update({0x8080+i:b for i,b in enumerate(handler)})
    rom_data.update({0xFFEA:0x80,0xFFEB:0x80})
    for tail in v3.TAILS.values():rom_data.update({tail:0x80,tail+1:0xFE})
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
            if k not in {'internalRegisters.nmiFlag','internalRegisters.enableNmi','cpu.nmiFlagCounter','cpu.needNmi',
                'dmaController.needToProcess','dmaController.hdmaInitPending','dmaController.dmaStartDelay'}:
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
            elif e['kind']=='read':
                require(e['address'] in rom_data and e['value']==rom_data[e['address']],
                    'ROM read differs from exact immutable mapped byte')
            if e['kind']=='write':ledger[e['address']]=e['value']
        if e['kind']=='exec':
            epoch+=1;exec_events.append((i,e));pc=e['address']
            require(pc==(e['cpu']['k']<<16)|e['cpu']['pc'],'execution PC mismatch')
            if v3.CODE<=pc<v3.CODE+len(code):expected=code[pc-v3.CODE]
            elif pc in HANDLER_PCS:expected=handler[pc-0x8080]
            else:require(pc in v3.TAILS.values(),'execution whitelist');expected=0x80
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
    require(exec_events[-1][1]['address']==v3.TAILS[case['route']] and
            (exec_events[-1][0]==len(events)-1 or (resume_i==len(events)-1 and resume_i==exec_events[-1][0]+1)), 'exact final terminal')
    require(exec_events[0][1]['address']==v3.CODE,'first helper opcode absent')
    require(base['address']==v3.ENTRY_BRIDGE and base['value']==-1 and base['cpu']['k']==0 and base['cpu']['pc']==v3.ENTRY_BRIDGE&65535,'declared setup bridge boundary')
    require(exec_events[0][1]['cpu']==dict(base['cpu'],k=v3.CODE>>16,pc=v3.CODE&65535),'original bridge changed helper entry registers')
    for tag_i,address in ((entry_i,0x8080),(rti_i,0x808F),(resume_i,case['nmi_resume'])):
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
    validate_phase(events,case,row['preparation'],request_i,resume_i)
    init_indices=validate_zero_channel_init(events,request_i,resume_i)
    for r in (base,request):
        f=r['flags'];require(f['internalRegisters.enableNmi'] is False,'NMI disabled before request')
        for k in ('cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'):require(type(f[k]) is int and f[k]==0,'pending interrupt/DMA integer')
        for k in FLAG_KEYS-{'internalRegisters.nmiFlag','cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'}:
            require(f[k] is False,'pending interrupt/DMA flag')
    require(all(base['cpu'][k]==case['cpu'][k] for k in case['cpu']),'fixture CPU differs from declared input')
    for a,b,value in ((request,after,0x80),(disable,disabled,0)):
        require(a['address']==b['address']==0x4200 and a['value']==b['value']==value and a['cpu']==b['cpu'] and a['timing']==b['timing'] and a['stack']==b['stack']
                and a['nmi_counter']==b['nmi_counter'] and a['latch_peek']==b['latch_peek'],'debugger event changed CPU/clock/frame')
        expected=dict(a['flags']);expected['internalRegisters.enableNmi']=bool(value)
        if value:expected['cpu.nmiFlagCounter']=2
        require(b['flags']==expected,'4200 event did not match actual register transition')
    trigger_cpu=request['cpu'];sp=case['cpu']['sp'];resume_pc=case['nmi_resume']
    require(trigger_cpu['sp']==sp-case['nmi_depth_before'] and trigger_cpu['k']==0x41 and trigger_cpu['pc']==(case['nmi_trigger']&65535),'trigger CPU/frame')
    dummy=[(i,e) for i,e in enumerate(events) if after_i<i<entry_i and e['kind']=='read' and e['bus_address']==resume_pc]
    conditional_idle=[]
    if code[case['nmi_trigger']-v3.CODE]==0x1B:
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
    require(entry['cpu']['k']==0 and entry['cpu']['pc']==0x8080 and entry['flags']['cpu.needNmi'] is False and entry['flags']['cpu.nmiFlagCounter']==0,'handler vector/ack mismatch')
    require(all(entry['cpu'][k]==interrupted[k] for k in ('a','x','y','d','dbr')),'hardware entry changed general registers')
    vectors=[(i,e) for i,e in enumerate(events) if e['kind']=='read' and e['bus_address'] in (0xFFEA,0xFFEB)]
    require([(e['bus_address'],e['value']) for _,e in vectors]==[(0xFFEA,0x80),(0xFFEB,0x80)],'actual native vector reads missing')
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
    require([e['address'] for i,e in exec_events if request_i<i<entry_i]==[0x8080],'NMI did not follow selected instruction directly')
    if code[case['nmi_trigger']-v3.CODE]==0x20:
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
        normal=(0x420000<=address<0x420000+len(payload) or 0x430000<=address<0x430000+len(registry) or
                0x7E9877<=address<0x7E9879 or 0x7EA0B3<=address<0x7EA0B5)
        stack=read_low<=address<read_high
        require(normal or stack,'undeclared helper data read')
        if stack:require((address&65535)>=e['cpu']['sp'],'stack read below pointwise live SP')
    require(events[entry_i-1]['kind']=='exec' and events[entry_i-1]['address']==0x8080,'entry is not pre-handler')
    require(events[rti_i-1]['kind']=='exec' and events[rti_i-1]['address']==0x808F and rti['stack'][:4]==hardware_frame and rti['cpu']['sp']==interrupted_sp-4,'pre-RTI frame')
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
    # Reuse v3's independent immutable-ROM helper contract on a declared helper-only projection.
    # Its derived diff is not the native full diff above; interrupted free stack
    # bytes can legitimately retain handler writes after the helper finishes.
    helpers=[e for _,e in exec_events if e['address'] not in HANDLER_PCS]
    epoch_map={e['exec_index']:i+1 for i,e in enumerate(helpers)}
    helper_memory=[e for i,e in enumerate(events) if e['kind'] in ('read','write') and e['exec_index'] in epoch_map and i not in hardware_indices]
    hwrites=[[e['address'],e['value']] for e in helper_memory if e['kind']=='write'];hfinal=dict(hwrites)
    pcs=[e['address'] for e in helpers];spos=[[i+1,e['address'],e['cpu']['sp']] for i,e in enumerate(helpers) if i>0 and code[pcs[i-1]-v3.CODE] in v2.SP_CHANGING_OPCODES]
    accesses=[[epoch_map[e['exec_index']],e['address'],e['value'],e['cpu']['sp'],int(e['kind']=='write')] for e in helper_memory if case['stack_span'][0]<=e['address']<case['stack_span'][1]]
    projection={k:row[k] for k in ('name','route','input_fixture_before_hex','input_fixture_after_hex','retired_scratch_before_hex','retired_scratch_after_hex','descriptor_fixture_before_hex','descriptor_fixture_after_hex')}
    projection.update(cpu={k:events[-1]['cpu'][k] for k in case['expected_cpu']},instructions=len(pcs),exec_addresses=pcs,exec_opcode_peeks=[e['value'] for e in helpers],
        writes=hwrites,changes=[[a,b] for a,b in sorted(hfinal.items()) if b!=patches.get(a,0xA5)],
        rom_reads=[[e['address'],e['value']] for e in helper_memory if e['kind']=='read' and (0x420000<=e['address']<0x420000+len(payload) or 0x430000<=e['address']<0x430000+len(registry))],
        reads_total=sum(e['kind']=='read' for e in helper_memory),stack_accesses=accesses,
        minimum_sp=min([sp]+[e['cpu']['sp'] for e in helpers]+[x[3] for x in accesses]),sp_observations=spos)
    v3.validate_record(projection,case,code=code,payload=payload,registry=registry)
    return {'name':case['name'],'events':len(events),'helper_execution_observations':len(helpers),'nmi_count':1,
        'vector_read_indices':[i for i,_ in vectors],'native_hardware_write_indices':[i for i,_ in hardware_writes],
        'conditional_instruction_idle_read_indices':[i for i,_ in conditional_idle],'hardware_dummy_read_index':dummy_i,
        'handler_entry_index':entry_i,'pre_rti_index':rti_i,'post_rti_index':resume_i,'minimum_sp':sp-case['nmi_max_depth'],
        'boundary':case['nmi_boundary'],'interrupted_cpu':interrupted,'helper_depth_at_interrupt':case['nmi_depth_after'],
        'zero_channel_hdma_init_observation_indices':init_indices,
        'counter_before':base['nmi_counter'],'counter_after':counter,'whole_wram_diff_reconciled':True,'helper_projection_passed_v3':True}


def run(output_dir:Path,repetition:int=1,scope:str='pilot')->dict:
    require(repetition in (1,2),'repetition must be1or2')
    calibration=read_calibration_reference()
    require_prior_v3_sources()
    phase_reference=ROOT/'references/mesen_nmi_phase_contract_v2.json'
    phase_bytes=(json.dumps(phase_audit.collect(),indent=2)+'\n').encode()
    require(phase_bytes==phase_reference.read_bytes() and sha(phase_bytes)=='a948e62fa24c8be7520902ec3e0763bbaf3ae097409961c0f7474b77a0a54c5a','corrected phase prerequisite drift')
    private=SAFE.canonical_private_root();rom=SAFE.resolve_private_file(v3.DEFAULT_ROM,'immutable original cartridge',private_root=private)
    rom_bytes,code,payload_bytes,registry,certificate,receipts=v3.verified_cartridge()
    handler=rom_bytes[0x408080:0x408090]
    require(sha(handler)=='7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448' and
        rom_bytes[0x40FFEA:0x40FFEC]==bytes((0x80,0x80)) and rom_bytes[0x408040:0x408042]==bytes((0x80,0xFE)),
        'original handler/vector/idle identity')
    runtime={k:SAFE.resolve_private_file(SAFE.DEFAULT_MESEN.parent/n,k,private_root=private) for k,n in SAFE.RUNTIME_NAMES.items()}
    for k,p in runtime.items():SAFE.require_identity(p,k)
    output=SAFE.prepare_private_output_dir(output_dir,private_root=private,forbidden_roots=(rom.parent,SAFE.DEFAULT_MESEN.parent))
    guarded={**runtime,**receipts,**{k:ROOT/p for k,p,_ in PHASE_SOURCE_FILES},'rom':rom,'collector':COLLECTOR,'launcher':Path(__file__),
        'v3_library':Path(v3.__file__),'v3_collector':v3.COLLECTOR,'v3_model':Path(v3.model.__file__),
        'v3_tests':ROOT/'tests/test_schala_package_helper_v3_rom.py','v3_reference':ROOT/'references/schala_package_helper_v3_rom.json',
        'v2_library':Path(v2.__file__),'helper':v2.HELPER,'host_adapter':Path(v2.adapter.__file__),'isolation_library':Path(SAFE.__file__),
        'v0_library':Path(v2.prior.__file__),'v1_library':Path(v2.v1.__file__),
        'nmi_tests':ROOT/'tests/test_schala_package_helper_v4_rom_nmi.py','phase_audit':Path(phase_audit.__file__),
        'prior_phase_audit':Path(phase_audit.prior.__file__),'phase_reference':phase_reference,
        'previous_nmi_launcher':ROOT/'tools/run_schala_package_helper_v2_nmi.py',
        'previous_nmi_collector':ROOT/'tools/mesen_schala_package_helper_v2_nmi.lua',
        'previous_nmi_tests':ROOT/'tests/test_schala_package_helper_v2_nmi.py',
        'previous_nmi_reference':ROOT/'references/schala_package_helper_v2_original_nmi.json',
        'original_fixture_source':Path(v3.model.fixtures.__file__),'package_policy_source':Path(v3.model.fixtures.policy.__file__),
        'policy_reference':v3.model.fixtures.policy.REFERENCE_PATH,'grammar_source':Path(v3.model.fixtures.policy.grammar.__file__),
        'grammar_reference':v3.model.fixtures.policy.grammar.REFERENCE_PATH,'adapter_reference':v3.model.adapter.REFERENCE_PATH,
        'design':ROOT/'docs/schala_package_helper_v4_rom_nmi_design.md',
        'phase_extension':ROOT/'docs/schala_package_helper_v4_rom_nmi_phase_extension.md',
        'calibration_reference':ROOT/'references/schala_package_helper_v4_timing_calibration.json',
        'calibration_launcher':ROOT/'tools/run_schala_package_helper_v4_timing_calibration.py',
        'calibration_collector':ROOT/'tools/mesen_schala_package_helper_v4_timing_calibration.lua',
        'calibration_tests':ROOT/'tests/test_schala_package_helper_v4_timing_calibration.py',
        'calibration_metadata':ROOT/'tools/collect_schala_package_helper_v4_timing_calibration.py',
        'calibration_report':ROOT/'docs/schala_package_helper_v4_timing_calibration.md'}
    require(sha(guarded['previous_nmi_reference'].read_bytes())=='4a517b6c58ef5516b192bdd0558c242afba693b13fae8da71cf1985edb67957a','preserved original-NMI reference drift')
    before={k:SAFE.sha256_file(p) for k,p in guarded.items()};cases=apply_calibration(build_cases(payload_bytes,registry,scope),calibration['schedule'])
    validate_sites(cases,code);v3.validate_fixture_spans(cases,code)
    (output/'helper.bin').write_bytes(code)
    (output/'original_package_certificate.json').write_bytes(canonical(certificate))
    stage=output/'staged';app=stage/'app';saves=app/'Saves';saves.mkdir(parents=True)
    staged={}
    for k,n in SAFE.RUNTIME_NAMES.items():staged[k]=app/n;SAFE.copy_new_regular_file(runtime[k],staged[k],k)
    stem='pe_nmi_'+secrets.token_hex(12);staged['rom']=stage/(stem+'.sfc');SAFE.copy_new_regular_file(rom,staged['rom'],'rom')
    staged['sram']=saves/(stem+'.srm');staged['sram'].write_bytes(bytes(8192))
    staged['collector']=stage/'collector.lua';SAFE.copy_new_regular_file(COLLECTOR,staged['collector'],'collector')
    payload={'schema':SCHEMA,'code_hex':code.hex(),'code':v3.CODE,'tails':v3.TAILS,'entry_bridge':v3.ENTRY_BRIDGE,'descriptor_hex':payload_bytes.hex(),'registry_hex':registry.hex(),
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
    require_prior_v3_sources()
    require({p.name for p in archive.iterdir()}=={p.name for p in archive_paths.values()},'source archive inventory changed')
    SAFE.require_file_hashes_unchanged(archive_paths,archive_before,'source archive')
    require_archive_hashes({k:SAFE.sha256_file(SAFE.resolve_private_file(p,'source archive',private_root=private)) for k,p in archive_paths.items()},before)
    SAFE.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged['sram'].name)
    require(not error and proc is not None and proc.returncode==61,f'isolated native pilot failed: {error or (proc.returncode if proc else None)}; retained {output}')
    trace=SAFE.decode_json_object(SAFE.read_direct_regular_file(output/'trace.json','trace',parent=output,maximum=1024*1024*1024),'trace')
    require(trace['schema']==SCHEMA and trace['error'] is None and trace['partial_events']==[] and len(trace['records'])==len(cases),'trace completion')
    result=[validate_record(r,c,code,handler,payload=payload_bytes,registry=registry) for r,c in zip(trace['records'],cases,strict=True)]
    manifest={'schema':SCHEMA,'status':'exploratory pilot; not final matched acceptance','evidence_level':'verified-runtime','repetition':repetition,
        'source_hashes':before,'staged_hashes':staged_before,'source_archive_hashes':archive_before,
        'trace_sha256':SAFE.sha256_file(output/'trace.json'),'observations':result,'matrix_scope':scope,
        'helper_sha256':sha(code),'case_contract_sha256':SAFE.sha256_file(output/'case_contract.json'),
        'sources_and_staged_inputs_unchanged':True,'source_archives_unchanged':True,'cartridge_mutation':False,'manufactured_interrupt_frame':False,'internal_nmi_or_ppu_state_edit':False,
        'interrupt_scope':'single debugger-requested register-edge NMI per original fixture, natural VBlank latch','production_approval':False}
    (output/'manifest.json').write_bytes(canonical(manifest));return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--repetition',type=int,default=1)
    p.add_argument('--scope',choices=('pilot','matrix'),default='pilot')
    args=p.parse_args();print(json.dumps(run(args.output_dir,args.repetition,args.scope),indent=2))
