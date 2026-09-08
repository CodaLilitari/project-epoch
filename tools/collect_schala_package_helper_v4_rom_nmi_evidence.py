"""Read-only reproduction of the separately scoped original-NMI matched proof.

No emulator launch, file output, assembler invocation or cartridge mutation.
Raw observations remain private. Final acceptance pins must be populated only
after the independently reviewed frozen pair has completed.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
import run_schala_package_helper_v4_rom_nmi as v

ROOT=Path(__file__).resolve().parents[1]
PREFIX='package_helper_v4_rom_nmi_20260908_'
RUNS=(('sampledwitness1','8ad37dba7d14e42c14756321796d97928fce8b1541df29a8a480422e7c988475'),
      ('sampledwitness2','b39fa24f8a10d1fd595465efe81c2e877f3810f6618fc5e7e08d963aeba6fd6d'))
TRACE_SHA256='9752443839e73d8cdb29e6096f41838ffb4091372b5fd910209cb0a74ab19c6e'
TESTS_SHA256='48f4d95aae835c9e65fe580c4b16ee74d5ce9594cac4281698bbb1f91e85b8e1'
HOST_TEST_COUNT=81
ARCHIVE_KEYS=v.ARCHIVE_KEYS
HISTORY=(
    ('pilot1','Two original-ROM deepest-JSR cases completed natively; the inherited whole-fixture VBlank restriction rejected their post-RTI continuation after raster wrap. This is preserved rejected evidence, not an accepted source-matched run.',
     '5344fbd723568a078b8e2233f77bfb11a31930fd2079a17a071cb455fe5b5a2a',None,
     '49c323c4cdd4ae84a3dff8bfc6a5116734b7c06506de29ee1f4436862367d42e',
     '439fa432fc4dece74a7063de3af9c2cb5cc066477ff8176bbd3dcc3c6a5769cd'),
    ('pilot2','Two calibrated deepest-JSR cases passed before the separately accepted full pair. Natural original cold boot, actual VBlank entry/RTI and bounded post-RTI raster-wrap continuation were observed; this pilot alone is not the 152-case acceptance.',
     'f61cad80bb75e209568415828df683e5cff2e97c2f373390aeac6ce4b853ffa9',
     'bdfd55bc6c78f2c75fd0efd45300b923eebc11e899ffe5ba6a1380099b00c631',
     '7bddde8866b72e3815b244c79be039c580fb9d36155ea256fba136ee2b53559b',None),
    ('final1','All152 cases completed natively, but four failed the then-declared32-clock sampled-init-clear limit;148 passed unchanged. The exact original publication/A3 sequence samples clear after38clocks. This rejected source revision is preserved, not retrospectively accepted.',
     '69f2173421da9d5d0dada58e096b8937fbb6819f3ac6b95f656997f10895b061',None,
     'f3fc0500fe1b3191a1142c3aaa1201d17976969db92a88321f709bb0686ae45e',
     '71d6d469963f43aa1ab00a2cdfc03ae6a7d664aa7b7b340d1ca2ed758c2eb45c'))
SPANS=(('SnesCpu.Shared.h',68,68,'TCS implied-addressing dispatch'),
       ('SnesCpu.Instructions.h',1331,1334,'implied addressing calls IdleOrRead'),
       ('SnesCpu.Shared.h',386,394,'pending interrupt converts idle cycle to code read'),
       ('SnesCpu.Instructions.h',1073,1076,'TCS applies SetSP(A)'),
       ('SnesCpu.cpp',46,60,'native NMI check acknowledges pending flag before hardware entry'),
       ('SnesCpu.Instructions.h',505,533,'hardware dummy read, native pushes and vector fetch'),
       ('SnesPpu.cpp',397,398,'short scanline prevents treating 1364 clocks as a universal line duration'),
       ('SnesPpu.cpp',459,486,'PPU frame counter advances at VBlank; scanline reset has a different phase'),
       ('SnesMemoryManager.cpp',224,258,'line-zero HDMA initialization bookkeeping even when no channels are enabled'),
       ('SnesDmaController.cpp',104,118,'zero-channel HDMA initialization returns without a transfer'),
       ('SnesDmaController.cpp',347,384,'pending-state OR, initialization request, and pending transfer processing'),
       ('SnesCpu.cpp',121,155,'per-cycle pending DMA processing before bus reads and writes'),
       ('SnesCpu.cpp',86,94,'six-clock idle cycle'),
       ('SnesCpu.Shared.h',379,420,'opcode and operand fetches use the CPU read path'),
       ('SnesCpu.Instructions.h',1347,1351,'stack-relative operand fetch and idle before the data read'),
       ('SnesMemoryManager.cpp',89,108,'eight-clock original bank41 and low-WRAM accesses'),
       ('ScriptManager.h',43,69,'read/write callback types differ from instruction fetch types'),
       ('Debugger.cpp',625,636,'bus operations process scripts with processExec false'))


def identity(path:Path)->dict:
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':v.SAFE.sha256_file(path)}


def pinned(path:Path,expected:str)->dict:
    item=identity(path);v.require(item['sha256']==expected,'pinned artifact drift: '+str(path));return item


def checked(path:Path)->Path:return v.SAFE.resolve_private_file(path,'NMI evidence',private_root=v.SAFE.canonical_private_root())


def read_json(path:Path,maximum:int=1024*1024*1024):
    path=checked(path)
    size=path.stat().st_size
    v.require(size<=maximum,'NMI evidence JSON exceeds its explicit size bound')
    # Passing the 1GiB ceiling to buffered read() needlessly reserves that much
    # even for a tiny receipt. The checked current extent is the read bound;
    # the direct-file helper still refuses growth beyond it or unsafe paths.
    return json.loads(v.SAFE.read_direct_regular_file(path,'NMI evidence JSON',parent=path.parent,maximum=size))


def source_paths()->dict:
    v3=v.v3;v2=v.v2
    return {**{k:v.SAFE.DEFAULT_MESEN.parent/n for k,n in v.SAFE.RUNTIME_NAMES.items()},
        **{k:ROOT/p for k,p,_ in v.PHASE_SOURCE_FILES},
        'rom':v3.DEFAULT_ROM,'collector':v.COLLECTOR,'launcher':Path(v.__file__),
        'v3_library':Path(v3.__file__),'v3_collector':v3.COLLECTOR,'v3_model':Path(v3.model.__file__),
        'v3_tests':ROOT/'tests/test_schala_package_helper_v3_rom.py','v3_reference':ROOT/'references/schala_package_helper_v3_rom.json',
        'v2_library':Path(v2.__file__),'helper':v2.HELPER,'host_adapter':Path(v2.adapter.__file__),'isolation_library':Path(v.SAFE.__file__),
        'v0_library':Path(v2.prior.__file__),'v1_library':Path(v2.v1.__file__),
        'nmi_tests':ROOT/'tests/test_schala_package_helper_v4_rom_nmi.py','phase_audit':Path(v.phase_audit.__file__),
        'prior_phase_audit':Path(v.phase_audit.prior.__file__),'phase_reference':ROOT/'references/mesen_nmi_phase_contract_v2.json',
        'previous_nmi_launcher':ROOT/'tools/run_schala_package_helper_v2_nmi.py',
        'previous_nmi_collector':ROOT/'tools/mesen_schala_package_helper_v2_nmi.lua',
        'previous_nmi_tests':ROOT/'tests/test_schala_package_helper_v2_nmi.py',
        'previous_nmi_reference':ROOT/'references/schala_package_helper_v2_original_nmi.json',
        'original_fixture_source':Path(v3.model.fixtures.__file__),'package_policy_source':Path(v3.model.fixtures.policy.__file__),
        'policy_reference':v3.model.fixtures.policy.REFERENCE_PATH,'grammar_source':Path(v3.model.fixtures.policy.grammar.__file__),
        'grammar_reference':v3.model.fixtures.policy.grammar.REFERENCE_PATH,'adapter_reference':v3.model.adapter.REFERENCE_PATH,
        'cartridge_completion':v3.DEFAULT_ROM.parent/'completion.json','cartridge_build_audit':v3.DEFAULT_ROM.parent/'audited-build.json',
        'design':ROOT/'docs/schala_package_helper_v4_rom_nmi_design.md',
        'phase_extension':ROOT/'docs/schala_package_helper_v4_rom_nmi_phase_extension.md',
        'calibration_reference':ROOT/'references/schala_package_helper_v4_timing_calibration.json',
        'calibration_launcher':ROOT/'tools/run_schala_package_helper_v4_timing_calibration.py',
        'calibration_collector':ROOT/'tools/mesen_schala_package_helper_v4_timing_calibration.lua',
        'calibration_tests':ROOT/'tests/test_schala_package_helper_v4_timing_calibration.py',
        'calibration_metadata':ROOT/'tools/collect_schala_package_helper_v4_timing_calibration.py',
        'calibration_report':ROOT/'docs/schala_package_helper_v4_timing_calibration.md'}


def span_metadata()->list[dict]:
    result=[]
    for name,start,end,claim in SPANS:
        folder='mesen_nmi_request_2_1_1' if name in ('SnesDmaController.cpp','ScriptManager.h','Debugger.cpp') else 'mesen_timing_api_2_1_1'
        path=ROOT/'private/research'/folder/name
        raw=b''.join(path.read_bytes().splitlines(keepends=True)[start-1:end])
        source_folder='Debugger' if name in ('ScriptManager.h','Debugger.cpp') else 'SNES'
        result.append({'file':identity(path),'first_line':start,'last_line':end,'span_bytes':len(raw),'span_sha256':v.sha(raw),
                       'interpretation':claim,'url':f'https://github.com/SourMesen/Mesen2/blob/{v.phase_audit.prior.COMMIT}/Core/{source_folder}/{name}#L{start}'})
    return result


def history_metadata()->list[dict]:
    result=[];key_by_name={p.name:k for k,p in source_paths().items()}
    for suffix,description,trace_hash,manifest_hash,prepared_hash,rejection_hash in HISTORY:
        directory=ROOT/'private/test_runs'/(PREFIX+suffix)
        pinned(checked(directory/'launch_inputs.json'),prepared_hash)
        receipt=read_json(directory/'launch_inputs.json');archive=directory/'source_archive'
        history_hashes=receipt['source_archive_hashes']
        v.require(type(history_hashes) is dict and history_hashes,'historical archive receipt is empty')
        known_paths=source_paths()
        v.require(set(history_hashes)<=set(known_paths),'historical archive has unknown source keys')
        expected_names={known_paths[k].name for k in history_hashes}
        v.require(len(expected_names)==len(history_hashes),'historical archive source basename collision')
        v.require({p.name for p in archive.iterdir()}==expected_names,'exact historical source archive inventory mismatch')
        archived=[]
        for path in sorted(archive.iterdir()):
            v.require(path.is_file(),'unexpected history source entry');item=identity(checked(path))
            key=key_by_name.get(path.name)
            v.require(key in receipt['source_hashes'] and item['sha256']==receipt['source_hashes'][key]==history_hashes[key],
                'historical archive not bound to its named prepared source')
            archived.append(item)
        paths=[directory/'launch_inputs.json',directory/'trace.json',directory/'case_contract.json',directory/'staged/collector.lua']
        pinned(directory/'trace.json',trace_hash)
        if manifest_hash is not None:
            pinned(directory/'manifest.json',manifest_hash);paths.append(directory/'manifest.json')
        else:v.require(not (directory/'manifest.json').exists(),'rejected pilot unexpectedly gained a manifest')
        if rejection_hash is not None:
            pinned(checked(directory/'host_rejection.json'),rejection_hash);paths.append(directory/'host_rejection.json')
        else:v.require(not (directory/'host_rejection.json').exists(),'successful pilot unexpectedly gained a rejection receipt')
        result.append({'run_id':PREFIX+suffix,'meaning':description,'artifacts':[identity(checked(p)) for p in paths],
                       'source_archive':archived,'source_hashes':receipt['source_hashes']})
    return result


def protocol_label_projection(path:Path,expected_hash:str)->dict:
    """Explicit top-level label substitution; every native observation stays raw."""
    path=checked(path);size=path.stat().st_size
    v.require(size<=1024*1024*1024,'historical trace exceeds projection bound')
    data=v.SAFE.read_direct_regular_file(path,'historical protocol projection',parent=path.parent,maximum=size)
    v.require(v.sha(data)==expected_hash,'historical projection input identity differs')
    old_schema='project-epoch-package-helper-v4-rom-nmi-calibrated-v2'
    before=('{"schema":"'+old_schema+'","records":[').encode()
    after=('{"schema":"'+v.SCHEMA+'","records":[').encode()
    v.require(data.startswith(before),'historical projection has unexpected top-level protocol header')
    return {'input':identity(path),'original_schema':old_schema,'replacement_schema':v.SCHEMA,
        'replacement_scope':'exact initial schema header only; all native observation and completion bytes retained verbatim',
        'projected_bytes':len(after)+len(data)-len(before),'projected_sha256':v.sha(after+data[len(before):])}


def metadata_draft_history()->dict:
    directory=ROOT/'private/test_runs'/(PREFIX+'before_history_receipt_pins')
    manifest_path=checked(directory/'manifest.json')
    manifest_id=pinned(manifest_path,'9d7c111bec2c1c9789afd317a467683df028d7c0f39a0567213241a4a21c2c72')
    manifest=read_json(manifest_path)
    names={'collect_schala_package_helper_v4_rom_nmi_evidence.py',
        'test_schala_package_helper_v4_rom_nmi_evidence.py','schala_package_helper_v4_rom_nmi.md'}
    v.require({p.name for p in directory.iterdir()}==names|{'manifest.json'},'metadata draft history exact inventory')
    v.require(len(manifest['files'])==3 and {Path(r['copy']).name for r in manifest['files']}==names,'metadata draft manifest inventory')
    artifacts=[]
    for row in manifest['files']:
        path=checked(directory/Path(row['copy']).name)
        v.require(path.relative_to(ROOT).as_posix()==row['copy'],'metadata draft copy path differs')
        item=pinned(path,row['sha256']);v.require(item['bytes']==row['bytes'],'metadata draft extent differs');artifacts.append(item)
    return {'manifest':manifest_id,'meaning':manifest['status'],'files':artifacts}


def collect()->dict:
    v.require(len(RUNS)==2 and len(TRACE_SHA256)==64,'matched native acceptance pins have not been populated')
    v.require_prior_v3_sources()
    normal_id=pinned(ROOT/'references/schala_package_helper_v3_rom.json','4c6c469ffde9c75517b1b7087f6c8956e2b2b2637355b87a99a1ae7981d15677')
    previous_nmi=pinned(ROOT/'references/schala_package_helper_v2_original_nmi.json','4a517b6c58ef5516b192bdd0558c242afba693b13fae8da71cf1985edb67957a')
    phase=v.phase_audit.collect();phase_bytes=(json.dumps(phase,indent=2)+'\n').encode()
    paths=source_paths();sources={k:identity(p) for k,p in paths.items()}
    collector_path=Path(__file__).resolve();report_path=ROOT/'docs/schala_package_helper_v4_rom_nmi.md'
    collector_id=identity(collector_path);report_id=identity(report_path)
    metadata_tests_path=ROOT/'tests/test_schala_package_helper_v4_rom_nmi_evidence.py'
    metadata_tests_id=identity(metadata_tests_path)
    pinned(paths['phase_reference'],v.sha(phase_bytes));pinned(paths['nmi_tests'],TESTS_SHA256)
    rom,expected_code,payload,registry,certificate,_=v.v3.verified_cartridge()
    calibration=v.read_calibration_reference()
    cases=v.apply_calibration(v.build_cases(payload,registry,'matrix'),calibration['schedule']);case_bytes=v.canonical(cases)
    v.require(len(cases)==152,'fixed matrix extent drift')
    current_hashes={k:x['sha256'] for k,x in sources.items()};accepted=[];first_results=None
    for repetition,(suffix,manifest_hash) in enumerate(RUNS,1):
        directory=ROOT/'private/test_runs'/(PREFIX+suffix);manifest_path=checked(directory/'manifest.json')
        manifest_id=pinned(manifest_path,manifest_hash);manifest=read_json(manifest_path);prepared=read_json(directory/'launch_inputs.json')
        v.require(manifest['schema']==v.SCHEMA and manifest['matrix_scope']=='matrix' and manifest['repetition']==repetition,'run scope differs')
        v.require(manifest['source_hashes']==prepared['source_hashes']==current_hashes,'current/prepared/native source identity mismatch')
        v.require(manifest['staged_hashes']==prepared['staged_hashes'],'prepared/staged identity mismatch')
        v.require(manifest['source_archive_hashes']==prepared['source_archive_hashes'],'prepared/final archive identity mismatch')
        v.require_archive_hashes(manifest['source_archive_hashes'],current_hashes)
        v.require(manifest['sources_and_staged_inputs_unchanged'] is True and manifest['cartridge_mutation'] is False and
                  manifest['manufactured_interrupt_frame'] is False and manifest['internal_nmi_or_ppu_state_edit'] is False and
                  manifest['production_approval'] is False and manifest['source_archives_unchanged'] is True,'native preservation/scope drift')
        v.require(checked(directory/'case_contract.json').read_bytes()==case_bytes,'native case contract differs from source')
        code=checked(directory/'helper.bin').read_bytes();v.validate_sites(cases,code)
        v.require(code==expected_code,'observed helper differs from immutable cartridge')
        v.require(checked(directory/'original_package_certificate.json').read_bytes()==v.canonical(certificate),'original package certificate drift')
        v.require(manifest['helper_sha256']==v.sha(code) and manifest['case_contract_sha256']==v.sha(case_bytes),'helper/case native digest mismatch')
        archive=directory/'source_archive';expected_names={paths[k].name for k in ARCHIVE_KEYS}
        v.require({p.name for p in archive.iterdir()}==expected_names,'exact source archive inventory mismatch')
        archive_ids=[pinned(checked(archive/paths[k].name),current_hashes[k]) for k in ARCHIVE_KEYS]
        stage=directory/'staged';app=stage/'app';roms=list(stage.glob('*.sfc'));saves=list((app/'Saves').iterdir())
        v.require(len(roms)==len(saves)==1 and saves[0].name==roms[0].stem+'.srm','isolated image/save inventory')
        staged={k:app/n for k,n in v.SAFE.RUNTIME_NAMES.items()}
        staged.update(rom=roms[0],sram=saves[0],collector=stage/'collector.lua',inputs=stage/'inputs.lua')
        staged_ids={k:pinned(checked(p),manifest['staged_hashes'][k]) for k,p in staged.items()}
        for key in (*v.SAFE.RUNTIME_NAMES,'rom','collector'):
            v.require(staged_ids[key]['sha256']==current_hashes[key],'staged artifact differs from exact guarded source')
        v.require(checked(saves[0]).read_bytes()==bytes(8192),'isolated staged SRAM is not the exact zero8192 fixture')
        input_payload={'schema':v.SCHEMA,'code_hex':code.hex(),'code':v.v3.CODE,'tails':v.v3.TAILS,
            'entry_bridge':v.v3.ENTRY_BRIDGE,'descriptor_hex':payload.hex(),'registry_hex':registry.hex(),
            'cases':[{k:value for k,value in c.items() if not k.startswith('expected_')} for c in cases]}
        expected_inputs=('return '+v.v2.lua_value(input_payload)+'\n').encode('utf-8')
        v.require(checked(staged['inputs']).read_bytes()==expected_inputs,'staged LF Lua inputs do not reproduce from exact source cases')
        trace_path=checked(directory/'trace.json');trace_id=pinned(trace_path,TRACE_SHA256)
        v.require(manifest['trace_sha256']==TRACE_SHA256,'manifest/trace identity differs')
        trace=read_json(trace_path)
        v.require(set(trace)=={'schema','records','error','partial_events'} and trace['schema']==v.SCHEMA and
                  trace['error'] is None and trace['partial_events']==[] and len(trace['records'])==152,'trace completeness')
        rows=trace['records'];results=[v.validate_record(r,c,code,rom[0x408080:0x408090],payload=payload,registry=registry) for r,c in zip(rows,cases,strict=True)]
        v.require(results==manifest['observations'],'manifest observations not rederived from exact trace')
        if first_results is None:first_results=results
        else:v.require(results==first_results,'matched native evidence differs')
        boundary=defaultdict(list)
        for r,c in zip(results,cases,strict=True):boundary[c['nmi_boundary']].append(c['cpu']['sp']-r['minimum_sp'])
        summary={'case_count':len(rows),'routes':dict(sorted(Counter(c['route'] for c in cases).items())),
            'event_count':sum(len(r['events']) for r in rows),
            'helper_and_terminal_execution_observations':sum(r['helper_execution_observations'] for r in results),
            'handler_instruction_observations':9*len(rows),'native_hardware_stack_writes':4*len(rows),
            'actual_native_vector_byte_reads':2*len(rows),'conditional_tcs_idle_reads':sum(len(r['conditional_instruction_idle_read_indices']) for r in results),
            'counter_increments':len(rows),'whole_wram_diff_reconciliations':len(rows),
            'observed_saved_p_values':sorted({r['interrupted_cpu']['ps'] for r in results}),
            'observed_minimum_sp_by_entry':{f'{sp:04X}':min(r['minimum_sp'] for r,c in zip(results,cases,strict=True) if c['cpu']['sp']==sp) for sp in (0x1FEF,0x06D8)},
            'combined_depths_by_boundary':{k:sorted(set(vals)) for k,vals in sorted(boundary.items())},
            'zero_channel_hdma_init_observations':sum(len(r['zero_channel_hdma_init_observation_indices']) for r in results),
            'cases_with_zero_channel_hdma_init_observations':sum(bool(r['zero_channel_hdma_init_observation_indices']) for r in results),
            'source_owned_38_clock_sampled_clear_witnesses':sum(
                bool(r['zero_channel_hdma_init_observation_indices']) and
                row['events'][r['zero_channel_hdma_init_observation_indices'][-1]+1]['timing']['memoryManager.masterClock']-
                row['events'][r['zero_channel_hdma_init_observation_indices'][0]]['timing']['memoryManager.masterClock']==38
                for row,r in zip(rows,results,strict=True)),
            'scheduled_start_scanlines':sorted({c['nmi_start_scanline'] for c in cases}),
            'maximum_active_master_clocks':max(row['events'][-1]['timing']['memoryManager.masterClock']-
                row['events'][0]['timing']['memoryManager.masterClock'] for row in rows),
            'maximum_post_rti_master_clocks':max(row['events'][-1]['timing']['memoryManager.masterClock']-
                row['events'][r['post_rti_index']]['timing']['memoryManager.masterClock'] for row,r in zip(rows,results,strict=True)),
            'maximum_observed_ppu_scanline':max(e['timing']['ppu.scanline'] for r in rows for e in r['events'])}
        accepted.append({'run_id':PREFIX+suffix,'manifest':manifest_id,'trace':trace_id,
                         'prepared_receipt':identity(checked(directory/'launch_inputs.json')),'source_archive':archive_ids,
                         'staged':staged_ids,'summary':summary,'per_case_observations':results,
                         'artifact_identities':[identity(checked(p)) for p in sorted(directory.rglob('*')) if p.is_file()]})
        del rows,trace
    history_projection=protocol_label_projection(ROOT/'private/test_runs'/(PREFIX+'final1')/'trace.json',
        '69f2173421da9d5d0dada58e096b8937fbb6819f3ac6b95f656997f10895b061')
    v.require(history_projection['projected_sha256']==TRACE_SHA256,'new pair differs beyond the declared historical protocol-label change')
    result={'schema':'project-epoch-package-helper-v4-rom-nmi-evidence-v1','date':'2026-09-08',
        'status':'accepted matched synthetic runtime pair','evidence_level':'verified-runtime',
        'scope':'immutable original cartridge, ROM helper and registry; real emulated 4200-edge NMI request after observed natural VBlank latch',
        'collector_source':collector_id,'human_report':report_id,
        'source_identities':sources,
        'corrected_phase_prerequisite':identity(paths['phase_reference']),
        'calibration_prerequisite':identity(paths['calibration_reference']),
        'phase_extension_contract':identity(paths['phase_extension']),
        'preserved_normal_v3_reference':normal_id,'preserved_v2_nmi_reference':previous_nmi,'source_spans':span_metadata(),
        'case_contract_sha256':v.sha(case_bytes),'runs':accepted,'trace_byte_identity':True,'cases_per_run':152,
        'host_tests':{'count':HOST_TEST_COUNT,'scope':'original host NMI envelope and matrix specimens; helper projection mocked only in envelope unit tests',
                      'command':'python -m unittest discover -s tests -p test_schala_package_helper_v4_rom_nmi.py'},
        'metadata_host_tests':{'count':18,'source':metadata_tests_id,
            'scope':'original two-file history specimen, empty/missing/extra archive refusal, pinned prepared/rejection receipts and missing/drift refusal, rejected-history manifest refusal, size-bounded receipt reads and explicit top-level-only protocol projection; no native or private trace dependency',
            'command':'python -m unittest discover -s tests -p test_schala_package_helper_v4_rom_nmi_evidence.py'},
        'history':history_metadata(),
        'preserved_metadata_draft':metadata_draft_history(),
        'preserved_paused_handoff':pinned(checked(ROOT/'private/test_runs'/(PREFIX+'paused_receipt_history')/
            'schala_package_helper_v4_rom_nmi_resume.md'),'cbaab3cd8b762e7eabf330f97d37e892b91b6bd63325a38ca280805bad7b1711'),
        'historical_native_bytes_preserved_after_explicit_protocol_label_change':history_projection,
        'projection_contract':'Actual complete event/write/final-WRAM evidence is validated first. The interrupt-free helper projection then excludes the four hardware pushes, vector and hardware dummy reads, all original handler epochs, and the separately witnessed conditional TCS idle read. Its final diff is derived from helper CPU writes, never presented as the actual native final diff.',
        'phase_contract':'A separately repeated 22-group no-NMI calibration derives 92 fixed schedule rows from baseline-before-JML elapsed clocks. The schedule is an inference; the native request through actual RTI must independently remain in the observed natural VBlank. IRQ/NMI/DMA-disabled continuation may cross raster with an 80000-clock post-RTI and 120000-clock whole-fixture bound. At most one source-supported, zero-channel line-zero HDMA-init bookkeeping episode may be observed outside the interrupt interval; generic observed clear is bounded to32 clocks. Exactly38 is permitted only with the complete original9F/A3 publication/stack-read witness and exact opcode/CPU/address/value/clock/cycle ownership. This sparse-observation exception does not claim38 clocks of actual pending DMA. Delay cannot restart.',
        'limitations':['Mesen hardware path, not a physical-SNES timing validation','debugger register request is not a CPU store instruction',
            'original minimal NMI handler only; no normal game NMI/IRQ nesting or physical stack ownership',
            'schedule inference reuses status-zero calibration for the three additional incoming statuses; actual native phase checks remain decisive',
            'no full instruction-boundary matrix; exactly the named152cases',
            'no action-script execution, production allocation, game hook, package binding or eighth-character runtime proof'],
        'cartridge_mutation':False,'manufactured_interrupt_frames':False,'production_approval':False,
        'reproduce':'python -B tools/collect_schala_package_helper_v4_rom_nmi_evidence.py','serialization':'UTF-8 indented JSON, LF, one trailing newline'}
    v.SAFE.require_file_hashes_unchanged(paths,current_hashes,'source after full evidence collection')
    v.require(identity(collector_path)==collector_id and identity(report_path)==report_id and identity(metadata_tests_path)==metadata_tests_id,
        'evidence collector/report/tests changed during collection')
    return result


if __name__=='__main__':sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode())
