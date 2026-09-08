"""Reproduce metadata-only acceptance of the frozen natural alternate replay pair.

Reads and validates existing private artifacts; launches no emulator and
writes no files. Source images, save states, screenshots and traces stay private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import audit_package_black_hole_threshold_v1 as threshold
import run_package_resolver_alternate_v1 as observer

ROOT=Path(__file__).resolve().parents[1]
RUNS=(
    ('resolver_alternate_20260908_final1','d5ac67a6fdfde4fa1e6a0a117d27dd93cb452c8245cddf9f93549677d89a2b78'),
    ('resolver_alternate_20260908_final2','4e15244238340be92b6d8bf09656bf186e57a46e6a35b3d1f4c115004e9ef960'),
)
TRACE_SHA256='f4400adb7488b9f65d290bb7dafedfd29228037bdcf2470e340ef06e9bb9b26b'
PREPARED_SHA256='9db2937e37fa69b91658977ad30a20a8c881b4926e2cb3f2bb99f0b85f400274'
SOURCE_FILES={
    'launcher':('tools/run_package_resolver_alternate_v1.py','46497341c658cea57bf09ddf0382246ad271e6fc43892612c4090aa3023bd758'),
    'collector':('tools/mesen_package_resolver_alternate_v1.lua','2bcbdc504b353940917f021bb99274aa682821bd186b40c397b2b105ca3b18ef'),
    'tests':('tests/test_package_resolver_alternate_v1.py','d96bd5a7e626427350fb1f1a2b6caed20c0129177ca157f3065e07b4ec017371'),
    'isolation_library':('tools/run_mesen_field_animation_probe_v0.py','d5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96'),
    'descriptor_model':('tools/audit_schala_player_tech_package_bank_adapter_v0.py','3ea222fdcc45028a174989769fa726a04a09506b5b65d071bceed855d60774f3'),
    'threshold_auditor':('tools/audit_package_black_hole_threshold_v1.py','707796948c846f9c80ee35a711452d79c73deea3eb80c1931e3e38e2715c505b'),
}


def identity(path:Path)->dict:
    data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def collect()->dict:
    private=observer.safe.canonical_private_root()
    def private_path(relative,label):
        return observer.safe.resolve_private_file(ROOT/relative,label,private_root=private)
    def read_json(path:Path,maximum:int)->dict:
        return observer.safe.decode_json_object(observer.safe.read_direct_regular_file(path,'JSON artifact',parent=path.parent,maximum=maximum),'JSON artifact')
    source_files={}
    for name,(relative,expected) in SOURCE_FILES.items():
        value=identity(ROOT/relative)
        observer.require(value['sha256']==expected,'accepted source drift: '+name)
        source_files[name]=value
    source_files['evidence_collector']=identity(Path(__file__).resolve())
    rom_path=private_path(observer.PINNED['rom'][0],'canonical ROM')
    rom=rom_path.read_bytes(); model=observer.canonical_model(rom)
    inputs={}
    for name,(relative,size,expected) in observer.PINNED.items():
        value=identity(private_path(relative,name))
        observer.require(value['size']==size and value['sha256']==expected,'pinned input drift: '+name)
        inputs[name]=value
    runs=[]; manifests=[]; traces=[]
    for name,expected_manifest in RUNS:
        directory=ROOT/'private/test_runs'/name
        mp=private_path(directory.relative_to(ROOT)/'manifest.json','manifest')
        tp=private_path(directory.relative_to(ROOT)/'trace.json','trace')
        lp=private_path(directory.relative_to(ROOT)/'launch_inputs.json','prepared launch receipt')
        observer.require(identity(mp)['sha256']==expected_manifest,'accepted manifest identity drift')
        observer.require(identity(tp)['sha256']==TRACE_SHA256,'accepted trace identity drift')
        observer.require(identity(lp)['sha256']==PREPARED_SHA256,'accepted prepared receipt drift')
        manifest=read_json(mp,2*1024*1024); trace=read_json(tp,32*1024*1024); prepared=read_json(lp,1024*1024)
        summary=observer.summarize(trace,model)
        observer.require(manifest['schema']==observer.SCHEMA and observer.canonical(summary)==observer.canonical(manifest['observations']),'manifest observations differ from revalidated trace')
        observer.require(manifest['evidence_level']=='exploratory-runtime-not-accepted','historical per-run acceptance status changed')
        observer.require(manifest['sources_and_staged_inputs_unchanged'] is True and all(manifest[k] is False for k in ('rom_mutated','memory_or_cpu_injection_after_load','helper_installed','production_approval')),'run scope or input preservation mismatch')
        observer.require(prepared['status']=='prepared-only-not-executed' and prepared['schema']==observer.SCHEMA,'prepared receipt status changed')
        observer.require(prepared['source_hashes']==manifest['source_hashes'] and prepared['staged_hashes']==manifest['staged_hashes'],'prepared and completed source identities differ')
        for key in ('launcher','collector','isolation_library','descriptor_model'):
            observer.require(manifest['source_hashes'][key]==source_files[key]['sha256'],'run source differs from accepted source')
        for key in observer.PINNED:
            observer.require(manifest['source_hashes'][key]==manifest['staged_hashes'][key]==inputs[key]['sha256'],'run input differs from accepted input')
        for key in observer.safe.RUNTIME_NAMES:
            observer.require(manifest['source_hashes'][key]==manifest['staged_hashes'][key],'staged runtime differs from source')
        observer.require(manifest['trace_sha256']==TRACE_SHA256,'manifest trace identity differs')
        expected_names={f'menu_{poll}.png' for poll in (2100,2680,3000)}
        observer.require(set(manifest['screenshots'])==expected_names,'screenshot inventory differs')
        screens=[]
        for filename in sorted(expected_names):
            path=private_path(directory.relative_to(ROOT)/filename,'screenshot'); value=identity(path)
            observer.require({k:value[k] for k in ('size','sha256')}==manifest['screenshots'][filename],'screenshot differs from its run manifest')
            screens.append(value)
        runs.append({'run_directory':directory.relative_to(ROOT).as_posix(),'prepared_receipt':identity(lp),
                     'manifest':identity(mp),'trace':identity(tp),'process_log':identity(private_path(directory.relative_to(ROOT)/'process.log','process log')),
                     'screenshots':screens})
        manifests.append(manifest); traces.append(trace)
    observer.require(observer.canonical(traces[0])==observer.canonical(traces[1]),'repeated CPU/data-flow observations differ')
    differing=[key for key in manifests[0] if manifests[0][key]!=manifests[1].get(key)]
    observer.require(set(manifests[0])==set(manifests[1]) and differing==['screenshots'],'manifest pair differs outside declared documentary screenshot identities')
    archive=private_path('private/downloads/chrono_trigger_saves/zophar_7175_after_crono_return.zip','original save archive')
    observer.require(identity(archive)['sha256']=='0a49d5634b6739202b9be7f1992b59d285f8589087056c75fd84d92111c80ca2','save archive provenance drift')
    with zipfile.ZipFile(archive) as z:
        candidates=[item for item in z.infolist() if item.filename=='ChronoTrigger.srm']
        observer.require(len(candidates)==1 and candidates[0].file_size==8192,'archive SRAM member mismatch')
        data=z.read(candidates[0])
        observer.require(hashlib.sha256(data).hexdigest()==inputs['sram']['sha256'],'observation SRAM differs from archived external save')
    provenance={'archive':identity(archive),'embedded_sram_member':'ChronoTrigger.srm','embedded_sram_matches_input':True,
                'attribution':'Outrunner, as named by the archived readme; external save, not new-game acquisition evidence',
                'source_listing':'https://www.zophar.net/savestates/snes/chrono-trigger.html'}
    for name,relative,expected in (
        ('readme','private/downloads/chrono_trigger_saves/zophar_7175_after_crono_return/ChronoTrigger.txt','9e32a2de4672afc239122d1735e861f94829ec65674f1640cefdd197394a2160'),
        ('checkpoint_route_log','private/test_runs/mesen2/event11c_checkpoint_v5/checkpoint.tsv','fa3b549802d54510bb1362b79feb6fb16e4e6c1d8eacfc446f76fd5b321515d2'),
    ):
        value=identity(private_path(relative,name)); observer.require(value['sha256']==expected,'checkpoint provenance drift: '+name); provenance[name]=value
    value=identity(ROOT/'tools/mesen_spekkio_checkpoint.lua')
    observer.require(value['sha256']=='6edd5fc924fb272714ccbb56c72f038003c3118f9c02d14dc5a5252c6cb01948','historical checkpoint collector drift')
    provenance['checkpoint_collector']=value
    provenance['setup_scope']='historical collector imports the entire byte-exact external SRAM through snesSaveRam writes before boot, then navigates with controller input to capture the talkable state'
    provenance['post_load_scope']='unchanged talkable state; fixed joypad only; no subsequent event-grant or canary preparation profiles'
    threshold_result=threshold.audit(rom)
    threshold_reference=ROOT/'references/package_black_hole_threshold_v1.json'
    observer.require(threshold_reference.read_bytes()==(json.dumps(threshold_result,indent=2)+'\n').encode(),'threshold correction reference differs from audit')
    navigation=private_path('private/research/ct_disassembly_eeae27a/bank_C1.asm','pinned disassembly')
    observer.require(identity(navigation)['sha256']==threshold.SOURCE_SHA256,'pinned navigation source drift')
    context_reference=ROOT/'references/package_resolver_context_v1.json'
    observer.require(identity(context_reference)['sha256']=='d7eb845a97f1398996ff28936b0117a423b6534aa1d518fbf49023e28317fd99','pinned context timing reference drift')
    context=json.loads(context_reference.read_text())
    return {
        'schema':'project-epoch-package-resolver-alternate-evidence-v1','date':'2026-09-08',
        'evidence_level':'verified-runtime','evidence_scope':'two byte-identical canonical alternate-resolver CPU/data-flow observations from the declared external-save checkpoint',
        'private_manifest_status_preserved':'exploratory-runtime-not-accepted; this separate reviewed reference accepts the repeated bounded observations',
        'source_files':source_files,'private_inputs':inputs,'checkpoint_provenance':provenance,
        'source_input_runtime_hashes':manifests[0]['source_hashes'],'runs':runs,
        'identical_trace_sha256':TRACE_SHA256,'identical_prepared_receipt_sha256':PREPARED_SHA256,
        'manifest_pair_differing_keys':differing,'screenshot_pixel_reproducibility_claimed':False,
        'observations':manifests[0]['observations'],'threshold_correction_reference':identity(threshold_reference),
        'threshold_correction':threshold_result,'pinned_navigation_source':identity(navigation),
        'timing_api_reference':identity(context_reference),'mesen_source_revision':context['mesen_source_revision'],
        'mesen_source_files':context['mesen_source_files'],
        'validator_tests':{'command':'python -B -m unittest tests.test_package_resolver_alternate_v1 -q','tests_passed_at_freeze':31,
                           'scope':'original synthetic metadata and descriptor; adversarial schema, timing, publication, ABI, flag, return and completion boundaries'},
        'history':[
            {'run_directory':'private/test_runs/alternate_branch_20260908_spekkio_magus_black_hole1',
             'manifest':identity(private_path('private/test_runs/alternate_branch_20260908_spekkio_magus_black_hole1/manifest.json','historical exploration manifest')),
             'status':'historical broad-route exploration; separate schema, unchanged, not the accepted focused collector'},
            {'run_directory':'private/test_runs/resolver_alternate_20260908_explore1',
             'trace':identity(private_path('private/test_runs/resolver_alternate_20260908_explore1/trace.json','focused exploratory trace')),
             'status':'focused collector executed; former overstrict action-window validator rejected later cleanup; no final manifest or prelaunch receipt existed; preserved without rewriting or claiming final source alignment'}],
        'reproduce_observation':'python -B tools/run_package_resolver_alternate_v1.py --output-dir private/test_runs/resolver_alternate_NEW_UNIQUE',
        'reproduce_reference':'python -B tools/collect_package_resolver_alternate_evidence_v1.py',
        'serialization':'json.dumps(value, indent=2), UTF-8, LF, exactly one trailing newline',
        'production_approval':False,
    }


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(collect(),indent=2))
