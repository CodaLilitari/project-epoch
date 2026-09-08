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
import run_schala_package_helper_v2_nmi as v

ROOT=Path(__file__).resolve().parents[1]
PREFIX='package_helper_v2_nmi_20260908_'
RUNS=(('final1','544de092e18ec9c77f284c1582a0961222fef4c2c91ff9f76898a886782710af'),
      ('final2','9fc6c9372f0858188a790f424fec9441a8bac2beb6f7efaead57127864e25593'))
TRACE_SHA256='3a84fca5e618a9aaaeac9c3056b7a15858f396b5cbfe5e2ae4fd2ae4fe147d50'
TESTS_SHA256='1d15ddedeb5eda60401b5df6036772deb1369fc8e62b8e4df1918e39531df57b'
ARCHIVE_KEYS=v.ARCHIVE_KEYS
HISTORY=(
    ('pilot1','Published source-note hidden ppu.nmiScanline mapping error; failed preparation before any active event or NMI request'),
    ('pilot2','Native NMI entry/resume occurred, but the new Lua allowlist omitted existing root-pointer output9878; rejected and not accepted'),
    ('pilot3','Lua allowlist next exposed omitted existing A0B3 byte clear; rejected and not accepted'),
    ('pilot4','Two deepest-JSR native exploratory cases passed the initial narrower validator; no final pair'),
    ('hardened_pilot1','Two native cases completed; host validator list-comprehension index bug rejected, subsequently fixed; preserved original sources'),
    ('boundary_pilot1','Nineteen native cases completed; host one-dummy assumption rejected three TCS sites; pinned CPU source explains two distinct reads'),
    ('boundary_hardened1','Nineteen fresh source-matched boundary cases passed after full handler, snapshot ledger, phase and TCS read hardening'),
)
SPANS=(('SnesCpu.Shared.h',68,68,'TCS implied-addressing dispatch'),
       ('SnesCpu.Instructions.h',1331,1334,'implied addressing calls IdleOrRead'),
       ('SnesCpu.Shared.h',386,394,'pending interrupt converts idle cycle to code read'),
       ('SnesCpu.Instructions.h',1073,1076,'TCS applies SetSP(A)'),
       ('SnesCpu.cpp',46,60,'native NMI check acknowledges pending flag before hardware entry'),
       ('SnesCpu.Instructions.h',505,533,'hardware dummy read, native pushes and vector fetch'))


def identity(path:Path)->dict:
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':v.SAFE.sha256_file(path)}


def pinned(path:Path,expected:str)->dict:
    item=identity(path);v.require(item['sha256']==expected,'pinned artifact drift: '+str(path));return item


def checked(path:Path)->Path:return v.SAFE.resolve_private_file(path,'NMI evidence',private_root=v.SAFE.canonical_private_root())


def read_json(path:Path,maximum:int=1024*1024*1024):
    path=checked(path)
    return json.loads(v.SAFE.read_direct_regular_file(path,'NMI evidence JSON',parent=path.parent,maximum=maximum))


def source_paths()->dict:
    return {**{k:v.SAFE.DEFAULT_MESEN.parent/n for k,n in v.SAFE.RUNTIME_NAMES.items()},
        'rom':v.v2.DEFAULT_ROM,'collector':v.COLLECTOR,'launcher':Path(v.__file__),'v2_library':Path(v.v2.__file__),
        'helper':v.v2.HELPER,'asar':v.v2.ASAR,'host_adapter':Path(v.v2.adapter.__file__),'isolation_library':Path(v.SAFE.__file__),
        'v0_library':Path(v.v2.prior.__file__),'v1_library':Path(v.v2.v1.__file__),
        'nmi_tests':ROOT/'tests/test_schala_package_helper_v2_nmi.py','phase_audit':Path(v.phase_audit.__file__),
        'prior_phase_audit':Path(v.phase_audit.prior.__file__),'phase_reference':ROOT/'references/mesen_nmi_phase_contract_v2.json'}


def span_metadata()->list[dict]:
    result=[]
    for name,start,end,claim in SPANS:
        path=ROOT/'private/research/mesen_timing_api_2_1_1'/name
        raw=b''.join(path.read_bytes().splitlines(keepends=True)[start-1:end])
        result.append({'file':identity(path),'first_line':start,'last_line':end,'span_bytes':len(raw),'span_sha256':v.sha(raw),
                       'interpretation':claim,'url':f'https://github.com/SourMesen/Mesen2/blob/{v.phase_audit.prior.COMMIT}/Core/SNES/{name}#L{start}'})
    return result


def history_metadata()->list[dict]:
    result=[];key_by_name={p.name:k for k,p in source_paths().items()}
    for suffix,description in HISTORY:
        directory=ROOT/'private/test_runs'/(PREFIX+suffix)
        receipt=read_json(directory/'launch_inputs.json');archive=directory/'source_archive'
        archived=[]
        for path in sorted(archive.iterdir()):
            v.require(path.is_file(),'unexpected history source entry');item=identity(checked(path))
            key=key_by_name.get(path.name)
            v.require(key in receipt['source_hashes'] and item['sha256']==receipt['source_hashes'][key],'historical archive not bound to its named prepared source')
            archived.append(item)
        paths=[directory/'launch_inputs.json',directory/'trace.json',directory/'case_contract.json',directory/'staged/collector.lua']
        if (directory/'manifest.json').exists():paths.append(directory/'manifest.json')
        result.append({'run_id':PREFIX+suffix,'meaning':description,'artifacts':[identity(checked(p)) for p in paths],
                       'source_archive':archived,'source_hashes':receipt['source_hashes']})
    return result


def collect()->dict:
    v.require(len(RUNS)==2 and len(TRACE_SHA256)==64,'matched native acceptance pins have not been populated')
    normal_path=ROOT/'references/schala_package_helper_v2_stack.json'
    normal_id=pinned(normal_path,'a095a1e18e97bd7f9746f3bc21affc90e30d76de10a34a2ffdff164e4b3c423f')
    normal=json.loads(normal_path.read_bytes())
    for item in [*normal['source_identities'].values(),normal['tests_identity'],normal['preserved_v1_reference']]:
        pinned(ROOT/item['path'],item['sha256'])
    phase=v.phase_audit.collect();phase_bytes=(json.dumps(phase,indent=2)+'\n').encode()
    paths=source_paths();sources={k:identity(p) for k,p in paths.items()}
    pinned(paths['phase_reference'],v.sha(phase_bytes));pinned(paths['nmi_tests'],TESTS_SHA256)
    rom=v.v2.verified_rom_bytes();cases=v.build_cases(rom,'matrix');case_bytes=v.canonical(cases)
    v.require(len(cases)==224,'fixed matrix extent drift')
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
        v.require(manifest['helper_sha256']==v.sha(code) and manifest['case_contract_sha256']==v.sha(case_bytes),'helper/case native digest mismatch')
        archive=directory/'source_archive';expected_names={paths[k].name for k in ARCHIVE_KEYS}
        v.require({p.name for p in archive.iterdir()}==expected_names,'exact source archive inventory mismatch')
        archive_ids=[pinned(checked(archive/paths[k].name),current_hashes[k]) for k in ARCHIVE_KEYS]
        stage=directory/'staged';app=stage/'app';roms=list(stage.glob('*.sfc'));saves=list((app/'Saves').iterdir())
        v.require(len(roms)==len(saves)==1 and saves[0].suffix=='.srm','isolated image/save inventory')
        staged={k:app/n for k,n in v.SAFE.RUNTIME_NAMES.items()}
        staged.update(rom=roms[0],sram=saves[0],collector=stage/'collector.lua',inputs=stage/'inputs.lua')
        staged_ids={k:pinned(checked(p),manifest['staged_hashes'][k]) for k,p in staged.items()}
        trace_path=checked(directory/'trace.json');trace_id=pinned(trace_path,TRACE_SHA256)
        v.require(manifest['trace_sha256']==TRACE_SHA256,'manifest/trace identity differs')
        trace=read_json(trace_path)
        v.require(set(trace)=={'schema','records','error','partial_events'} and trace['schema']==v.SCHEMA and
                  trace['error'] is None and trace['partial_events']==[] and len(trace['records'])==224,'trace completeness')
        rows=trace['records'];results=[v.validate_record(r,c,code,rom[0x408020:0x408030]) for r,c in zip(rows,cases,strict=True)]
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
            'maximum_observed_ppu_scanline':max(e['timing']['ppu.scanline'] for r in rows for e in r['events'])}
        accepted.append({'run_id':PREFIX+suffix,'manifest':manifest_id,'trace':trace_id,
                         'prepared_receipt':identity(checked(directory/'launch_inputs.json')),'source_archive':archive_ids,
                         'staged':staged_ids,'summary':summary,'per_case_observations':results,
                         'artifact_identities':[identity(checked(p)) for p in sorted(directory.rglob('*')) if p.is_file()]})
        del rows,trace
    return {'schema':'project-epoch-package-helper-v2-original-nmi-evidence-v1','date':'2026-09-08',
        'status':'accepted matched synthetic runtime pair','evidence_level':'verified-runtime',
        'scope':'unchanged original carrier and v2 WRAM helper, real emulated4200-edge NMI request after observed natural VBlank latch',
        'collector_source':identity(Path(__file__).resolve()),'human_report':identity(ROOT/'docs/schala_package_helper_v2_original_nmi.md'),
        'source_identities':sources,
        'corrected_phase_prerequisite':identity(paths['phase_reference']),'preserved_normal_v2_reference':normal_id,'source_spans':span_metadata(),
        'case_contract_sha256':v.sha(case_bytes),'runs':accepted,'trace_byte_identity':True,'cases_per_run':224,
        'host_tests':{'count':55,'scope':'original host NMI envelope and matrix specimens; helper projection mocked only in envelope unit tests',
                      'command':'python -m unittest discover -s tests -p test_schala_package_helper_v2_nmi.py'},
        'history':history_metadata(),
        'preserved_before_read_scope_delta':[identity(checked(p)) for p in sorted((ROOT/'private/test_runs'/(PREFIX+'before_read_scope_sources')).iterdir())],
        'projection_contract':'Actual complete event/write/final-WRAM evidence is validated first. The interrupt-free helper projection then excludes the four hardware pushes, vector and hardware dummy reads, all original handler epochs, and the separately witnessed conditional TCS idle read. Its final diff is derived from helper CPU writes, never presented as the actual native final diff.',
        'limitations':['Mesen hardware path, not a physical-SNES timing validation','debugger register request is not a CPU store instruction',
            'original minimal NMI handler only; no normal game NMI/IRQ nesting or physical stack ownership',
            'no full instruction-boundary matrix; exactly the named224cases',
            'no helper stream execution, production allocation, game hook, package binding or eighth-character runtime proof'],
        'cartridge_mutation':False,'manufactured_interrupt_frames':False,'production_approval':False,
        'reproduce':'python -B tools/collect_schala_package_helper_v2_nmi_evidence.py','serialization':'UTF-8 indented JSON, LF, one trailing newline'}


if __name__=='__main__':sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode())
