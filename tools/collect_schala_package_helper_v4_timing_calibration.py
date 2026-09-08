"""Revalidate a matched original no-interrupt timing calibration pair."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import run_schala_package_helper_v4_timing_calibration as c

ROOT=c.ROOT
RUNS=('package_helper_v4_timing_20260908_final1','package_helper_v4_timing_20260908_final2')
REFERENCE=ROOT/'references/schala_package_helper_v4_timing_calibration.json'
HISTORY=ROOT/'private/test_runs/package_helper_v4_timing_20260908_prephase_review'
HISTORY_SHA='3ea3da75bcf4df96584256ec000b150e0a3d5a4f3d48fc218deb85e0b611d8de'
METADATA_HISTORY=ROOT/'private/test_runs/package_helper_v4_timing_20260908_metadata_review1'
METADATA_HISTORY_SHA='36c2bf3326a5effef2f94c0cfc6ddaa958d01ac4bb32d82f30da3d934b613501'


def identity(path):
    raw=c.safe.read_direct_regular_file(path,path.name,parent=path.parent,maximum=192*1024*1024)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':c.digest(raw)}


def read_json(path):
    raw=c.safe.read_direct_regular_file(path,path.name,parent=path.parent,maximum=192*1024*1024)
    def pairs(items):
        value={}
        for k,v in items:c.require(k not in value,'duplicate JSON key');value[k]=v
        return value
    def nonfinite(_):raise c.ConformanceError('nonfinite JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)


def source_paths():
    prior=read_json(ROOT/'references/schala_package_helper_v3_rom.json')
    result={key:ROOT/item['path'] for key,item in prior['source_identities'].items()}
    result.update(launcher=Path(c.__file__),collector=c.COLLECTOR,tests=c.TESTS,
        v3_launcher=Path(c.v3.__file__),v3_collector=c.v3.COLLECTOR,v3_tests=c.v3.TESTS,
        v3_reference=ROOT/'references/schala_package_helper_v3_rom.json',
        phase_audit=Path(c.phase_audit.__file__),prior_phase_audit=Path(c.phase_audit.prior.__file__),
        phase_reference=ROOT/'references/mesen_nmi_phase_contract_v2.json',
        ppu_source=ROOT/'private/research/mesen_timing_api_2_1_1/SnesPpu.cpp')
    return result


def verify_run(directory,*,sources,code,payload,registry,certificate,cases):
    launch=read_json(directory/'launch_inputs.json');manifest=read_json(directory/'manifest.json')
    c.require(launch['schema']==manifest['schema']==c.SCHEMA and manifest['passed'] is True,'completed calibration schema/status')
    c.require(launch['execution_status']=='prepared-not-yet-executed' and manifest['sources_and_staged_inputs_unchanged'] is True,'prepared provenance and posthash witness')
    hashes={key:item['sha256'] for key,item in sources.items()}
    c.require(launch['source_hashes']==manifest['source_hashes']==hashes,'source-frozen calibration identities')
    c.require(manifest['case_count']==22 and manifest['schedule_rows']==92 and manifest['interrupt_requested'] is False
        and manifest['schedule_executed'] is False and manifest['schedule_is_inference'] is True,'fixed timing scope')
    c.require((directory/'case_contract.json').read_bytes()==c.canonical_json(cases),'original case contract differs')
    c.require(c.digest(code)==manifest['helper_sha256']==launch['helper_sha256'] and (directory/'helper.bin').read_bytes()==code,'helper identity differs')
    c.require((directory/'original_package_certificate.json').read_bytes()==c.canonical_json(certificate),'original fixture certificate differs')
    c.require(identity(directory/'case_contract.json')['sha256']==manifest['case_contract_sha256']==launch['case_contract_sha256'],'case receipt digest')
    archive=read_json(directory/'source_snapshots.json')
    c.require(archive['schema']==c.v3.SCHEMA+'-source-snapshots' and archive['execution_status']=='prepared-not-yet-executed','reused v3 archive helper provenance')
    expected={key:item for key,item in sources.items() if Path(item['path']).suffix in ('.py','.asm','.lua','.json')}
    c.require(len(archive['sources'])==len(expected) and {x['label'] for x in archive['sources']}==set(expected),'complete original source archive set')
    archive_hashes={'snapshot_metadata':identity(directory/'source_snapshots.json')['sha256']};archive_names=[]
    for row in archive['sources']:
        source=expected[row['label']];suffix=Path(source['path']).suffix
        filename=row['label']+'--'+source['sha256']+suffix
        c.require(row=={'label':row['label'],'source':source['path'],'archive':'source_snapshots/'+filename,
            'size_bytes':source['size'],'sha256':source['sha256']},'exact archived source metadata')
        archived=identity(directory/'source_snapshots'/filename)
        c.require(archived['size']==source['size'] and archived['sha256']==source['sha256'],'archived source bytes differ')
        archive_hashes[row['label']]=archived['sha256'];archive_names.append(filename)
    c.require(sorted(p.name for p in (directory/'source_snapshots').iterdir())==sorted(archive_names),'archive contains extra or missing entries')
    c.require(archive_hashes==manifest['source_snapshot_hashes']==launch['source_snapshot_hashes'],'archive manifest digest set differs')
    stage=directory/'staged';app=stage/'app';roms=list(stage.glob('pe_package_*.sfc'))
    c.require(len(roms)==1,'one isolated staged original ROM')
    staged={key:app/name for key,name in c.safe.RUNTIME_NAMES.items()}
    staged.update(rom=roms[0],sram=app/'Saves'/(roms[0].stem+'.srm'),collector=stage/'collector.lua',inputs=stage/'inputs.lua')
    c.safe.require_exact_staged_save_entries(sorted(p.name for p in (app/'Saves').iterdir()),staged['sram'].name)
    staged_ids={key:identity(path) for key,path in staged.items()};staged_hashes={key:item['sha256'] for key,item in staged_ids.items()}
    c.require(staged_hashes==manifest['staged_hashes']==launch['staged_hashes'],'staged input drift')
    for key in (*c.safe.RUNTIME_NAMES,'rom','collector'):c.require(staged_hashes[key]==hashes[key],'staged/source mismatch')
    c.require(staged['sram'].read_bytes()==bytes(8192),'isolated zero SRAM')
    inputs={'schema':c.SCHEMA,'code_hex':code.hex(),'code':c.CODE,'tails':c.TAILS,'entry_bridge':c.ENTRY_BRIDGE,
        'registry_hex':registry.hex(),'descriptor_hex':payload.hex(),'cases':[{k:v for k,v in row.items() if not k.startswith('expected_')} for row in cases]}
    # The pinned Windows launcher uses Path.write_text(newline=None), whose
    # native newline translation emits this exact CRLF, retained in both runs.
    c.require(staged['inputs'].read_bytes()==('return '+c.lua_value(inputs)+'\r\n').encode('utf-8'),'exact source-derived input script')
    trace=read_json(directory/'trace.json')
    c.require(trace['schema']==c.SCHEMA and trace['error'] is None and trace['partial_execution_samples']==[] and len(trace['records'])==22,'complete calibration trace')
    observations=[c.validate_record(row,case,code=code,payload=payload,registry=registry) for row,case in zip(trace['records'],cases,strict=True)]
    c.require((directory/'elapsed_observations.json').read_bytes()==c.canonical_json(observations),'native elapsed observations do not revalidate')
    schedule=[item for row in observations for item in row['schedule']]
    c.require(len(schedule)==92 and (directory/'schedule.json').read_bytes()==c.canonical_json(schedule),'native scheduling inference differs')
    fixtures=[{'name':row['name'],'registry_before_sha256':c.digest(bytes.fromhex(row['input_fixture_before_hex'])),
        'registry_after_sha256':c.digest(bytes.fromhex(row['input_fixture_after_hex'])),
        'descriptor_before_sha256':c.digest(bytes.fromhex(row['descriptor_fixture_before_hex'])),
        'descriptor_after_sha256':c.digest(bytes.fromhex(row['descriptor_fixture_after_hex']))} for row in trace['records']]
    c.require((directory/'rom_input_fixture_hashes.json').read_bytes()==c.canonical_json(fixtures),'input fixture hash receipts')
    artifacts={name:identity(directory/name) for name in ('manifest.json','launch_inputs.json','trace.json','case_contract.json',
        'elapsed_observations.json','schedule.json','rom_input_fixture_hashes.json','progress.json','source_snapshots.json','process.log')}
    for filename,field in (('trace.json','trace_sha256'),('elapsed_observations.json','elapsed_observations_sha256'),
        ('schedule.json','schedule_sha256'),('rom_input_fixture_hashes.json','rom_input_fixture_hashes_sha256'),('progress.json','progress_sha256')):
        c.require(artifacts[filename]['sha256']==manifest[field],'artifact/manifest hash mismatch')
    progress=read_json(directory/'progress.json')
    c.require(progress=={'schema':c.SCHEMA,'status':'completed','completed_cases':22,'total_cases':22},'exact final progress receipt')
    projection=[{'name':row['name'],'elapsed_execution':row['elapsed_execution'],'schedule':row['schedule']} for row in observations]
    return {'directory':directory.relative_to(ROOT).as_posix(),'repetition':manifest['repetition'],'artifacts':artifacts,
        'staged_identities':staged_ids,'source_archive_hashes':archive_hashes,
        'elapsed_projection_sha256':c.digest(c.canonical_json(projection)),
        'execution_observations':sum(len(row['elapsed_execution']) for row in observations),
        'duration_master_clocks':{'minimum':min(row['duration_master_clocks'] for row in observations),'maximum':max(row['duration_master_clocks'] for row in observations)},
        'absolute_timing_by_group':[{'name':row['name'],'baseline':row['absolute_baseline_timing'],
            'first_helper':row['absolute_first_helper_timing'],'last_tail':row['absolute_final_timing']} for row in observations]},projection,schedule


def collect():
    c.verify_v3_prerequisites()
    _,code,payload,registry,certificate,_=c.verified_cartridge();cases=c.build_cases(payload,registry)
    paths=source_paths();sources={key:identity(path) for key,path in paths.items()}
    runs=[];projections=[];schedules=[]
    for name in RUNS:
        run,projection,schedule=verify_run(ROOT/'private/test_runs'/name,sources=sources,code=code,payload=payload,registry=registry,certificate=certificate,cases=cases)
        runs.append(run);projections.append(projection);schedules.append(schedule)
    c.require([run['repetition'] for run in runs]==[1,2] and projections[0]==projections[1] and schedules[0]==schedules[1],'fresh source-frozen elapsed/schedule pair differs')
    c.require({key:identity(path) for key,path in paths.items()}==sources,'source drift during paired collection')
    history_id=identity(HISTORY/'receipt.json');c.require(history_id['sha256']==HISTORY_SHA,'source-review history receipt drift')
    history=read_json(HISTORY/'receipt.json');history_sources=[]
    for row in history['sources']:
        item=identity(HISTORY/row['archive']);c.require(item['sha256']==row['sha256'] and item['size']==row['size'],'preserved pre-review source drift');history_sources.append(item)
    metadata_history_id=identity(METADATA_HISTORY/'receipt.json')
    c.require(metadata_history_id['sha256']==METADATA_HISTORY_SHA,'metadata review receipt drift')
    metadata_history=read_json(METADATA_HISTORY/'receipt.json')
    metadata_history_source=identity(METADATA_HISTORY/Path(metadata_history['source']['path']).name)
    c.require(metadata_history_source['sha256']==metadata_history['source']['sha256']
        and metadata_history_source['size']==metadata_history['source']['size'],'preserved metadata source drift')
    return {'schema':c.SCHEMA+'-accepted-pair','date':'2026-09-08','evidence_level':'verified-runtime',
        'evidence_scope':'original immutable-ROM normal execution timing; no requested interrupt or stream execution',
        'source_identities':sources,'metadata_collector':identity(Path(__file__).resolve()),'runs':runs,
        'case_count_per_run':22,'schedule_row_count':92,'elapsed_projections_identical':True,'schedules_identical':True,
        'schedule_elapsed_basis':'fixture-baseline-before-original-entry-JML','execution_elapsed_basis':'first-observed-helper-opcode',
        'schedule':schedules[0],'schedule_is_inference':True,'schedule_executed':False,
        'absolute_clocks_compared_for_equality':False,'trace_bytes_equal':runs[0]['artifacts']['trace.json']['sha256']==runs[1]['artifacts']['trace.json']['sha256'],
        'source_review_history':{'receipt':history_id,'sources':history_sources,'native_execution':False},
        'metadata_review_history':{'receipt':metadata_history_id,'source':metadata_history_source,'native_rejection':False},
        'production_approval':False,'game_interrupt_ownership_proved':False,'other_entry_status_timings_calibrated':False,
        'reproduce':['python','-B','tools/collect_schala_package_helper_v4_timing_calibration.py']}


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    raw=(json.dumps(collect(),indent=2)+'\n').encode('utf-8')
    c.require(raw==REFERENCE.read_bytes(),'accepted calibration reference differs')
    sys.stdout.buffer.write(raw)
