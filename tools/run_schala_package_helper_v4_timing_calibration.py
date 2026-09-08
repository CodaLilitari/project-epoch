"""Original immutable-ROM no-interrupt timing calibration for a later NMI run.

Normal helper semantics remain the unchanged v3 validator's responsibility.
Only observed elapsed times support the separately labeled scheduling inference.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
from typing import Any
import run_schala_package_helper_v3_rom as v3
import audit_mesen_nmi_phase_contract_v2 as phase_audit

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-package-helper-v4-timing-calibration'
COLLECTOR=ROOT/'tools/mesen_schala_package_helper_v4_timing_calibration.lua'
TESTS=ROOT/'tests/test_schala_package_helper_v4_timing_calibration.py'
safe=v3.safe
model=v3.model
v2=v3.v2
CODE=v3.CODE
ENTRY_BRIDGE=v3.ENTRY_BRIDGE
TAILS=v3.TAILS
ENTRY_STACKS=v3.ENTRY_STACKS
DEFAULT_ROM=v3.DEFAULT_ROM
ConformanceError=v3.ConformanceError
canonical_json=v3.canonical_json
digest=v3.digest
lua_value=v3.lua_value
verified_cartridge=v3.verified_cartridge
validate_fixture_spans=v3.validate_fixture_spans
archive_guarded_sources=v3.archive_guarded_sources
CPU_KEYS={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'}
TIME_KEYS={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount','ppu.scanline','memoryManager.hClock','clockRate'}
FLAG_KEYS={'internalRegisters.nmiFlag','internalRegisters.enableNmi','internalRegisters.enableHorizontalIrq',
 'internalRegisters.enableVerticalIrq','internalRegisters.enableAutoJoypadRead','cpu.nmiFlagCounter','cpu.needNmi',
 'cpu.irqLock','cpu.irqSource','cpu.prevIrqSource','dmaController.needToProcess','dmaController.hdmaChannels',
 'dmaController.hdmaPending','dmaController.hdmaInitPending','dmaController.dmaStartDelay','dmaController.dmaPending'}
INTEGER_FLAGS={'cpu.nmiFlagCounter','cpu.irqSource','cpu.prevIrqSource','dmaController.hdmaChannels'}
BOUNDARIES={
 'success':{'allocate-tcs':0x410043,'first-countbits-jsr':0x4100EE,'release-tcs':0x410215,
            'pull-p':0x41021A,'success-jml-tail':0x41021B},
 'canonical':{'canonical-pull-p':0x410019,'canonical-jml-tail':0x41001E},
 'early-refusal':{'refusal-pull-p':0x41022D,'refusal-jml-tail':0x41022E},
 'framed-refusal':{'refusal-release-tcs':0x410226,'refusal-jml-tail':0x41022E},
}
EXTRA_KEYS={'preparation','fixture_baseline','execution_samples'}


def require(value,message):
    if not value:raise ConformanceError(message)


def integer(value,low,high,name):require(type(value) is int and low<=value<=high,'exact bounded integer '+name)


def build_cases(payload,registry):
    result=[]
    for sp in ENTRY_STACKS:
        for selector in range(0x80,0x84):
            for flag in (0,0x40):
                result.append(model.make_case(payload,registry,f'calibration-{selector:02X}-{flag:02X}',selector,flag,sp=sp,status=0))
        for selector in (0x7F,0x90,0x84):
            result.append(model.make_case(payload,registry,f'calibration-{selector:02X}-00',selector,0,sp=sp,status=0))
    require(len(result)==22 and len({c['name'] for c in result})==22,'exact calibration group count')
    return result


def verify_v3_prerequisites():
    reference=ROOT/'references/schala_package_helper_v3_rom.json'
    raw=reference.read_bytes()
    require(digest(raw)=='4c6c469ffde9c75517b1b7087f6c8956e2b2b2637355b87a99a1ae7981d15677','accepted v3 reference drift')
    for identity in json.loads(raw)['source_identities'].values():
        source=ROOT/identity['path'];data=source.read_bytes()
        require(len(data)==identity['size_bytes'] and digest(data)==identity['sha256'],'preserved v3 prerequisite drift: '+source.name)
    phase_raw=(json.dumps(phase_audit.collect(),indent=2)+'\n').encode('utf-8')
    require(digest(phase_raw)=='a948e62fa24c8be7520902ec3e0763bbaf3ae097409961c0f7474b77a0a54c5a'
        and phase_raw==(ROOT/'references/mesen_nmi_phase_contract_v2.json').read_bytes(),'corrected phase prerequisite drift')


def boundaries(case):
    key=case['route'] if case['route']!='refusal' else 'framed-refusal' if case['frame_allocated'] else 'early-refusal'
    return BOUNDARIES[key]


def validate_snapshot(sample):
    require(type(sample) is dict and set(sample)=={'exec_index','pc','cpu','timing','flags','latch_peek'},'timing snapshot shape')
    integer(sample['exec_index'],0,10000,'execution ordinal');integer(sample['pc'],0,0xFFFFFF,'PC')
    cpu=sample['cpu'];require(type(cpu) is dict and set(cpu)==CPU_KEYS and cpu['emulationMode'] is False,'native CPU shape')
    for key,value in cpu.items():
        if key!='emulationMode':integer(value,0,255 if key in ('ps','k','dbr') else 65535,'CPU '+key)
    require(sample['pc']==(cpu['k']<<16)|cpu['pc'],'sample CPU/PC mismatch')
    timing=sample['timing'];flags=sample['flags']
    require(type(timing) is dict and set(timing)==TIME_KEYS,'complete timing fields')
    for value in timing.values():integer(value,0,2**64-1,'timing')
    require(timing['masterClock']==timing['memoryManager.masterClock']&0xFFFFFFFF and timing['frameCount']==timing['ppu.frameCount'] and timing['clockRate']==21477270,'clock basis')
    require(timing['ppu.scanline']<262 and timing['memoryManager.hClock']<=1364,'fixed NTSC raster bounds')
    require(type(flags) is dict and set(flags)==FLAG_KEYS,'complete interrupt/DMA fields')
    for key,value in flags.items():
        if key in INTEGER_FLAGS:require(type(value) is int and value==0,'pending interrupt/DMA integer')
        else:
            require(type(value) is bool,'interrupt/DMA boolean')
            if key!='internalRegisters.nmiFlag':require(value is False,'interrupt/DMA source enabled or pending')
    integer(sample['latch_peek'],0,255,'latch peek')
    require(bool(sample['latch_peek']&128)==flags['internalRegisters.nmiFlag'],'latch/peek mismatch')


def schedule_start(rise_scanline,elapsed_master_clocks):
    integer(rise_scanline,0,261,'observed rise scanline');integer(elapsed_master_clocks,0,1000000,'elapsed clocks')
    return (rise_scanline+3-(elapsed_master_clocks+1363)//1364)%262


def require_raster_clock_interval(before,after,rise):
    # Pinned non-interlaced NTSC source: frameCount increments at the NMI
    # scanline, while scanline itself wraps at 262; one line is 1360 or 1364.
    def position(t):return t['ppu.frameCount']*262+(t['ppu.scanline']-rise)%262
    lines=position(after)-position(before)
    delta_h=after['memoryManager.hClock']-before['memoryManager.hClock']
    delta=after['memoryManager.masterClock']-before['memoryManager.masterClock']
    require(lines>=0 and lines*1360+delta_h<=delta<=lines*1364+delta_h,'full clock/raster interval mismatch')


def validate_record(record,case,*,code,registry,payload,code_base=CODE):
    require(type(record) is dict and EXTRA_KEYS<=set(record),'complete calibration record')
    normal={k:v for k,v in record.items() if k not in EXTRA_KEYS}
    v3.validate_record(normal,case,code=code,registry=registry,payload=payload,code_base=code_base)
    baseline=record['fixture_baseline'];validate_snapshot(baseline)
    require(baseline['exec_index']==0 and baseline['pc']==ENTRY_BRIDGE,'setup bridge timing boundary')
    require(all(baseline['cpu'][k]==value for k,value in case['cpu'].items()),'baseline CPU differs from fixture')
    prep=record['preparation']
    require(type(prep) is dict and set(prep)=={'wait_start_clock','latch_rise'} and type(prep['latch_rise']) is dict and set(prep['latch_rise'])=={'before','after'},'natural phase preparation shape')
    before,after=prep['latch_rise']['before'],prep['latch_rise']['after']
    for row in (before,after):
        require(type(row) is dict and set(row)=={'clock','cycles','frame','scanline','hclock','latch','peek'},'natural phase sample shape')
        require(type(row['latch']) is bool,'phase latch boolean')
        for key,value in row.items():
            if key!='latch':integer(value,0,2**64-1,'phase '+key)
        require(row['scanline']<262 and row['hclock']<1364 and row['peek']<=255,'phase field bounds')
    integer(prep['wait_start_clock'],0,before['clock'],'wait start')
    require(0<after['clock']-before['clock']<=32 and after['clock']-prep['wait_start_clock']<800000,'consecutive original idle latch bracket')
    require(before['cycles']<after['cycles'] and after['frame'] in (before['frame'],before['frame']+1),'phase counter progression')
    require(before['latch'] is False and after['latch'] is True and not before['peek']&128 and after['peek']&128,'actual natural latch transition')
    def phase_timing(sample):
        return {'memoryManager.masterClock':sample['clock'],'ppu.frameCount':sample['frame'],
            'ppu.scanline':sample['scanline'],'memoryManager.hClock':sample['hclock']}
    require_raster_clock_interval(phase_timing(before),phase_timing(after),after['scanline'])
    bt=baseline['timing']
    require(bt['memoryManager.masterClock']>after['clock'] and bt['cpu.cycleCount']>after['cycles'] and bt['ppu.frameCount']==after['frame'] and bt['ppu.scanline']==after['scanline']+1,'baseline one scanline after natural rise')
    require(baseline['flags']['internalRegisters.nmiFlag'] is True,'latched baseline')
    require_raster_clock_interval(phase_timing(after),bt,after['scanline'])
    samples=record['execution_samples']
    require(type(samples) is list and len(samples)==normal['instructions'],'one timing record per complete execution PC')
    previous=baseline
    for ordinal,(sample,pc) in enumerate(zip(samples,normal['exec_addresses'],strict=True),1):
        validate_snapshot(sample)
        require(sample['exec_index']==ordinal and sample['pc']==pc,'complete execution/time ordinal pairing')
        t=sample['timing'];old=previous['timing']
        require(t['memoryManager.masterClock']>old['memoryManager.masterClock'] and t['cpu.cycleCount']>old['cpu.cycleCount'] and t['ppu.frameCount']>=old['ppu.frameCount'],'strict instruction clock/cycle progression')
        require_raster_clock_interval(old,t,after['scanline'])
        previous=sample
    require(samples[0]['pc']==CODE and samples[-1]['pc']==TAILS[case['route']],'calibration execution endpoints')
    require(samples[0]['cpu']==dict(baseline['cpu'],k=CODE>>16,pc=CODE&65535),'original entry JML CPU continuity')
    for ordinal,pc,sp in normal['sp_observations']:
        require(1<=ordinal<=len(samples) and samples[ordinal-1]['pc']==pc and samples[ordinal-1]['cpu']['sp']==sp,
            'normal SP observation detached from timed execution CPU')
    require(all(samples[-1]['cpu'][k]==value for k,value in normal['cpu'].items()),'final CPU timing/normal-record mismatch')
    first=samples[0]['timing'];elapsed=[]
    for sample in samples:
        t=sample['timing']
        elapsed.append({'exec_index':sample['exec_index'],'pc':sample['pc'],
            'master_clocks':t['memoryManager.masterClock']-first['memoryManager.masterClock'],
            'cpu_cycles':t['cpu.cycleCount']-first['cpu.cycleCount']})
    require(elapsed[-1]['master_clocks']<=1000000,'bounded calibration duration')
    schedule=[]
    for name,trigger in boundaries(case).items():
        entry=next((s for s in elapsed if s['pc']==trigger),None)
        require(entry is not None,'required boundary absent from exact execution sequence')
        baseline_elapsed=entry['master_clocks']+first['memoryManager.masterClock']-bt['memoryManager.masterClock']
        schedule.append({'selector':case['selector'],'flag':case['flag'],'sp':case['cpu']['sp'],'boundary':name,'trigger':trigger,
            'elapsed_master_clocks':baseline_elapsed,'start_scanline':schedule_start(after['scanline'],baseline_elapsed),
            'observed_rise_scanline':after['scanline'],'group_name':case['name']})
    return {'name':case['name'],'elapsed_execution':elapsed,'elapsed_execution_sha256':digest(canonical_json(elapsed)),
        'duration_master_clocks':elapsed[-1]['master_clocks'],'duration_cpu_cycles':elapsed[-1]['cpu_cycles'],
        'schedule':schedule,'normal_v3_passed':True,'interrupt_requested':False,
        'absolute_baseline_timing':dict(bt),'absolute_first_helper_timing':dict(first),'absolute_final_timing':dict(samples[-1]['timing']),
        'schedule_elapsed_basis':'fixture-baseline-before-original-entry-JML','execution_elapsed_basis':'first-observed-helper-opcode',
        'schedule_is_inference':True,'schedule_executed':False}


def run(output_dir: Path, *, repetition: int = 1, timeout: int = 900, code_base: int = CODE) -> dict[str, Any]:
    verify_v3_prerequisites()
    private = safe.canonical_private_root()
    data,code,payload_bytes,registry,certificate,receipts=verified_cartridge()
    rom=safe.resolve_private_file(DEFAULT_ROM,"reviewed original diagnostic cartridge",private_root=private)
    if code_base!=CODE or not 1<=timeout<=1200 or repetition not in (1,2):
        raise ConformanceError("fixed ROM placement or bounded launch parameters differ")
    runtime={label:safe.resolve_private_file(safe.DEFAULT_MESEN.parent/name,label,private_root=private)
        for label,name in safe.RUNTIME_NAMES.items()}
    for label,path in runtime.items():safe.require_identity(path,label)
    output=safe.prepare_private_output_dir(output_dir,private_root=private,forbidden_roots=(rom.parent,safe.DEFAULT_MESEN.parent))
    guarded={**runtime,**receipts,"rom":rom,"collector":COLLECTOR,"launcher":Path(__file__),"tests":TESTS,
        'phase_audit':Path(phase_audit.__file__),'prior_phase_audit':Path(phase_audit.prior.__file__),
        'phase_reference':ROOT/'references/mesen_nmi_phase_contract_v2.json',
        'ppu_source':ROOT/'private/research/mesen_timing_api_2_1_1/SnesPpu.cpp',
        "v3_launcher":Path(v3.__file__),"v3_collector":v3.COLLECTOR,"v3_tests":v3.TESTS,
        "v3_reference":ROOT/"references/schala_package_helper_v3_rom.json","helper_source":v2.HELPER,"v2_validation_source":Path(v2.__file__),"host_model":Path(model.__file__),
        "original_fixture_source":Path(model.fixtures.__file__),"package_policy_source":Path(model.fixtures.policy.__file__),
        "host_adapter":Path(model.adapter.__file__),"isolation_library":Path(safe.__file__),
        "v1_contract_library":Path(v2.v1.__file__),"v0_validation_library":Path(v2.prior.__file__),
        "policy_reference":model.fixtures.policy.REFERENCE_PATH,"grammar_source":Path(model.fixtures.policy.grammar.__file__),
        "grammar_reference":model.fixtures.policy.grammar.REFERENCE_PATH,"adapter_reference":model.adapter.REFERENCE_PATH}
    source_before={key:safe.sha256_file(path) for key,path in guarded.items()}
    snapshots,snapshot_before=archive_guarded_sources(output,guarded,source_before)
    cases=build_cases(payload_bytes,registry)
    validate_fixture_spans(cases,code)
    (output/"original_package_certificate.json").write_bytes(canonical_json(certificate))
    (output/"helper.bin").write_bytes(code)
    stage = output / "staged"
    app = stage / "app"
    saves = app / "Saves"
    saves.mkdir(parents=True)
    staged: dict[str,Path] = {}
    for label,name in safe.RUNTIME_NAMES.items():
        path=app/name
        safe.copy_new_regular_file(runtime[label],path,label)
        staged[label]=path
    stem="pe_package_" + secrets.token_hex(12)
    staged["rom"]=stage/(stem+".sfc")
    safe.copy_new_regular_file(rom,staged["rom"],"rom")
    staged["sram"]=saves/(stem+".srm")
    staged["sram"].write_bytes(bytes(8192))
    staged["collector"]=stage/"collector.lua"
    safe.copy_new_regular_file(COLLECTOR,staged["collector"],"collector")
    payload={"schema":SCHEMA,"code_hex":code.hex(),"code":code_base,"tails":TAILS,
             "entry_bridge":ENTRY_BRIDGE,"registry_hex":registry.hex(),"descriptor_hex":payload_bytes.hex(),"cases":[{k:v for k,v in c.items() if not k.startswith("expected_")} for c in cases]}
    staged["inputs"]=stage/"inputs.lua"
    staged["inputs"].write_text("return " + lua_value(payload) + "\n", encoding="utf-8")
    (output/"case_contract.json").write_bytes(canonical_json(cases))
    staged_before={k:safe.sha256_file(v) for k,v in staged.items()}
    for key in (*runtime,"rom","collector"):
        if staged_before[key] != source_before[key]:
            raise ConformanceError(f"staged {key} differs from pinned source before execution")
    (output/"launch_inputs.json").write_bytes(canonical_json({"schema":SCHEMA,
        "evidence_level":"hypothesis","execution_status":"prepared-not-yet-executed",
        "source_hashes":source_before,"staged_hashes":staged_before,
        "source_snapshot_hashes":snapshot_before,
        "helper_sha256":digest(code),"helper_size":len(code),"helper_code_base":code_base,
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "runtime_sizes":{label:path.stat().st_size for label,path in runtime.items()},"rom_mutation":False,"pointed_stream_execution":False}))
    env=safe.minimal_subprocess_environment()
    for key,parts in {"USERPROFILE":("profile",), "APPDATA":("profile","AppData","Roaming"),
                      "LOCALAPPDATA":("profile","AppData","Local"),"TEMP":("temp",),"TMP":("temp",)}.items():
        p=stage.joinpath(*parts)
        p.mkdir(parents=True,exist_ok=True)
        env[key]=str(p)
    env.update(PE_PACKAGE_PROTOCOL=SCHEMA, PE_PACKAGE_INPUT=str(staged["inputs"]),
               PE_PACKAGE_TRACE=str(output/"trace.json"),PE_PACKAGE_PROGRESS=str(output/"progress.json"))
    command=[str(staged["mesen"]),"--testRunner",f"--timeout={timeout}",
        "--doNotSaveSettings","--debug.scriptWindow.allowIoOsAccess=true",
        str(staged["collector"]),str(staged["rom"])]
    proc=None
    error=None
    try:
        proc=subprocess.run(command,cwd=app,env=env,capture_output=True,timeout=timeout+15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0,check=False)
        (output/"process.log").write_bytes(proc.stdout+proc.stderr)
    except (OSError,subprocess.TimeoutExpired) as exc:
        error=str(exc)
    # Preserve the complete isolated stage even on failure; never copy a shared save.
    safe.require_file_hashes_unchanged(guarded,source_before,"source")
    safe.require_file_hashes_unchanged(snapshots,snapshot_before,"archived source")
    safe.require_file_hashes_unchanged(staged,staged_before,"staged input")
    safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged["sram"].name)
    if error or proc is None or proc.returncode != 41:
        raise ConformanceError(f"isolated Mesen execution failed: {error or proc.returncode}; {output}")
    trace_path=output/"trace.json"
    trace=safe.decode_json_object(safe.read_direct_regular_file(trace_path,"trace",parent=output,maximum=192*1024*1024),"trace")
    if trace.get("schema") != SCHEMA or trace.get("error") is not None or trace.get('partial_execution_samples')!=[] or len(trace.get("records",[])) != len(cases):
        raise ConformanceError("trace schema, termination, or case count mismatch")
    observations=[validate_record(record,case,code=code,registry=registry,payload=payload_bytes,code_base=code_base)
        for record,case in zip(trace["records"],cases,strict=True)]
    schedule=[row for observation in observations for row in observation["schedule"]]
    require(len(schedule)==92,"exact scheduling inference row count")
    (output/"elapsed_observations.json").write_bytes(canonical_json(observations))
    (output/"schedule.json").write_bytes(canonical_json(schedule))
    fixture_hashes=[{"name":r["name"],
        "registry_before_sha256":digest(bytes.fromhex(r["input_fixture_before_hex"])),
        "registry_after_sha256":digest(bytes.fromhex(r["input_fixture_after_hex"])),
        "descriptor_before_sha256":digest(bytes.fromhex(r["descriptor_fixture_before_hex"])),
        "descriptor_after_sha256":digest(bytes.fromhex(r["descriptor_fixture_after_hex"]))} for r in trace["records"]]
    (output/"rom_input_fixture_hashes.json").write_bytes(canonical_json(fixture_hashes))
    reproduction=["python","tools/run_schala_package_helper_v4_timing_calibration.py","--output-dir",
                  "private/test_runs/package_helper_v4_timing_NEW","--repetition",str(repetition),
                  "--timeout",str(timeout),"--code-base",f"0x{code_base:06X}"]
    manifest={"schema":SCHEMA,"evidence_level":"verified-runtime","evidence_scope":"original-no-interrupt-timing-calibration",
        "repetition":repetition,"case_count":len(cases),"subset_only":True,
        "case_categories":{k:sum(c["category"]==k for c in cases) for k in sorted({c["category"] for c in cases})},
        "passed":True,"source_hashes":source_before,"staged_hashes":staged_before,
        "source_snapshot_hashes":snapshot_before,
        "helper_size":len(code),"helper_code_base":code_base,"entry_bridge":ENTRY_BRIDGE,"helper_sha256":digest(code),"trace_sha256":safe.sha256_file(trace_path),
        "case_contract_sha256":safe.sha256_file(output/"case_contract.json"),
        "rom_input_fixture_hashes_sha256":safe.sha256_file(output/"rom_input_fixture_hashes.json"),
        "progress_sha256":safe.sha256_file(output/"progress.json"),
        "cpu_instruction_counts":{"min":min(r["instructions"] for r in trace["records"]),
                                  "max":max(r["instructions"] for r in trace["records"])},
        "sources_and_staged_inputs_unchanged":True,"no_rom_write_or_patch":True,
        "rom_descriptor_bank":0x42,"rom_registry_bank":0x43,"helper_execution_bank":0x41,"pointed_stream_execution":False,"pre_execution_opcode_peeks":True,"independent_opcode_bus_fetch_observation":False,"complete_execution_span_guard":True,"complete_execution_pc_sequences":True,"no_global_scratch_access":True,"stack_entry_values":list(ENTRY_STACKS),"no_game_input":True,"production_hook_allocation_or_integration":False,
        "interrupt_policy":"synthetic IRQ/NMI sources disabled; no game interrupt claim",
        "reproduce":reproduction,"elapsed_observations_sha256":safe.sha256_file(output/"elapsed_observations.json"),
        "schedule_sha256":safe.sha256_file(output/"schedule.json"),"schedule_rows":92,"schedule_is_inference":True,
        "schedule_executed":False,"natural_latch_preparation":True,"interrupt_requested":False}
    (output/"manifest.json").write_bytes(canonical_json(manifest))
    return manifest



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--repetition',type=int,default=1)
    parser.add_argument('--timeout',type=int,default=300)
    parser.add_argument('--code-base',type=lambda value:int(value,0),default=CODE)
    args=parser.parse_args()
    print(json.dumps(run(args.output_dir,repetition=args.repetition,timeout=args.timeout,code_base=args.code_base),indent=2))
