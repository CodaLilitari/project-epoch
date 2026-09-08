"""Revalidate frozen transaction observations and print metadata-only evidence.

No emulator launch or file write. Private game bytes never enter the output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import run_package_transaction_observation_v1 as observer

ROOT=Path(__file__).resolve().parents[1]
RUNS=('package_transaction_20260908_final1','package_transaction_20260908_final2')
TRACE_SHA='fc9e89c139d00a23ab67a84ee77f497e6dfe63133c14509b23f50ce72d0523e7'
MANIFEST_SHA='44b746ad5924ee085a7d203b84cf3f22480838d8bbea751ccef98149a508378d'
PRELAUNCH_SHA='bad38935adf7604e296b0ce03b77ef3cc529a79670c4d2ce7013b8d2bc6017e8'
SOURCES={
    'launcher':('tools/run_package_transaction_observation_v1.py','eb709e0188f588b17b7abe28b877654eee337f1f1728b7901ffbfc5281bb90f2'),
    'collector':('tools/mesen_package_transaction_observation_v1.lua','c6923bd608804795cfc6b3dfd143dc65c2b99bc3a858f422bfae7dd889492cdd'),
    'validation_library':('tools/package_transaction_validation_v1.py','cb03514d844d5a50671ec3bf98ce6566a05ad3e1b423d9156ff8d50101d3928b'),
    'tests':('tests/test_package_transaction_observation_v1.py','846749a9c84271d7b99c5553631b5d698b737321a5540b7e76cc9d0ccd90966c'),
    'isolation_library':('tools/run_mesen_field_animation_probe_v0.py','d5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96')}
PROVENANCE={
    'checkpoint_acceptance':('references/mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json','67cc7c9f7460a3de30a23c90aca53a079b8334c5e80c1975651fcdc60ba08564'),
    'checkpoint_collector':('tools/mesen_lavos_battle_checkpoint.lua','3bcc3146d9b5ef7fe7287f9031b7ad6f2d0c0423bfcf7c5f910efac4431cce11'),
    'checkpoint_launcher':('tools/run_mesen_lavos_battle_checkpoint.py','377024c212a72c4e2f3b000e44a7573cedd94093f86463c665be8925ae8c6321'),
    'canonical_bank_c1_annotation':('private/research/ct_disassembly_eeae27a/bank_C1.asm','298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa'),
    'canonical_bank_fd_annotation':('private/research/ct_disassembly_eeae27a/bank_FD.asm','0f8a0d59e97de7d60945fdfef1b614217e3d673cca1e14f543234d789a87779e')}


def identity(path:Path,expected:str|None=None)->dict:
    data=path.read_bytes(); sha=hashlib.sha256(data).hexdigest()
    if expected is not None and sha!=expected: raise observer.ObservationError('frozen identity mismatch: '+str(path))
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(data),'sha256':sha}


def collect()->dict:
    private=observer.safe.canonical_private_root()
    sources={k:identity(ROOT/p,h) for k,(p,h) in SOURCES.items()}
    provenance={k:identity(ROOT/p,h) for k,(p,h) in PROVENANCE.items()}
    sources['metadata_collector']=identity(Path(__file__).resolve())
    inputs={}
    for key,(path,size,sha) in observer.PINNED.items():
        p=observer.safe.resolve_private_file(ROOT/path,key,private_root=private)
        inputs[key]=identity(p,sha)
        if inputs[key]['size']!=size: raise observer.ObservationError('input size mismatch')
    runtime={}
    for key,name in observer.safe.RUNTIME_NAMES.items():
        p=observer.safe.resolve_private_file(observer.safe.DEFAULT_MESEN.parent/name,key,private_root=private)
        observer.safe.require_identity(p,key); runtime[key]=identity(p)
    runs=[]; manifests=[]
    for name in RUNS:
        directory=ROOT/'private/test_runs'/name
        def read(name:str,maximum:int)->dict:
            p=observer.safe.resolve_private_file(directory/name,name,private_root=private)
            return observer.safe.decode_json_object(observer.safe.read_direct_regular_file(p,name,parent=directory,maximum=maximum),name)
        trace_id=identity(directory/'trace.json',TRACE_SHA)
        manifest_id=identity(directory/'manifest.json',MANIFEST_SHA)
        prelaunch_id=identity(directory/'launch_inputs.json',PRELAUNCH_SHA)
        trace=read('trace.json',16*1024*1024); manifest=read('manifest.json',1024*1024); prepared=read('launch_inputs.json',1024*1024)
        summary=observer.summarize(trace)
        if observer.canonical(summary)!=observer.canonical(manifest['observations']): raise observer.ObservationError('summary differs from revalidated trace')
        expected_hashes={k:v['sha256'] for k,v in {**sources,**inputs,**runtime}.items() if k!='metadata_collector'}
        if manifest['source_hashes']!=expected_hashes or prepared['source_hashes']!=expected_hashes: raise observer.ObservationError('source identity set drift')
        expected_staged={k:v['sha256'] for k,v in {**inputs,**runtime,'collector':sources['collector']}.items()}
        if manifest['staged_hashes']!=expected_staged or prepared['staged_hashes']!=expected_staged: raise observer.ObservationError('staged identity set drift')
        if manifest['schema']!=observer.SCHEMA or manifest['trace_sha256']!=TRACE_SHA or manifest['sources_and_staged_inputs_unchanged'] is not True or any(manifest[k] is not False for k in ('rom_mutated','memory_or_cpu_injection','helper_installed','production_approval')):
            raise observer.ObservationError('read-only scope mismatch')
        archives={k:identity(directory/'source_archive'/Path(p).name,h) for k,(p,h) in SOURCES.items()}
        stage=directory/'staged'; app=stage/'app'; saves=app/'Saves'
        roms=list(stage.glob('pe_resolver_*.sfc')); states=list(stage.glob('pe_resolver_*.mss'))
        if len(roms)!=1 or len(states)!=1 or roms[0].stem!=states[0].stem: raise observer.ObservationError('isolated staged game filenames drift')
        staged={'rom':roms[0],'state':states[0],'sram':saves/(roms[0].stem+'.srm'),'collector':stage/'collector.lua',
                **{k:app/n for k,n in observer.safe.RUNTIME_NAMES.items()}}
        for key,p in staged.items():
            observer.safe.resolve_private_file(p,key,private_root=private)
            identity(p,expected_staged[key])
        observer.safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged['sram'].name)
        runs.append({'directory':directory.relative_to(ROOT).as_posix(),'trace':trace_id,'manifest':manifest_id,'prelaunch':prelaunch_id,
                     'process_log':identity(directory/'process.log'),'source_archive':archives,'all_staged_input_bytes_revalidated':True})
        manifests.append(manifest)
    if observer.canonical(manifests[0])!=observer.canonical(manifests[1]): raise observer.ObservationError('frozen repeat differs')
    rom=(ROOT/observer.PINNED['rom'][0]).read_bytes()
    spans=[]
    for name,start,end in (
        ('queued-tech-transaction',0xC1BB49,0xC1BC60),('queue-release',0xC1BCF8,0xC1BD6F),
        ('shared-finalizer',0xC1BDB3,0xC1BF46),('participant-mp-deduction',0xC1CC71,0xC1CCCB),
        ('result-wrapper',0xC1AC57,0xC1AC89),('result-application-and-first-hp-store',0xC1EC7F,0xC1ECA3),
        ('target-result-clear',0xFDACEE,0xFDACFD)):
        data=rom[start&0x3FFFFF:end&0x3FFFFF]
        spans.append({'name':name,'cpu_start':f'{start:06X}','cpu_end_exclusive':f'{end:06X}','size':len(data),
                      'sha256':hashlib.sha256(data).hexdigest(),'evidence_level':'verified-static'})
    history=[]
    for name,status in (
        ('package_transaction_20260908_explore1','root exploratory trace; old schema; launcher rejected its former 4 MiB read limit'),
        ('package_transaction_20260908_hardened1','rejected: exploratory target-result clear range was incomplete; no accepted manifest'),
        ('package_transaction_20260908_hardened2','source-frozen exploratory acceptance before independent review and final pair')):
        d=ROOT/'private/test_runs'/name
        history.append({'directory':d.relative_to(ROOT).as_posix(),'status':status,'trace':identity(d/'trace.json'),
                        'staged_collector':identity(d/'staged/collector.lua'),
                        'prelaunch_source_archive_available':(d/'source_archive').is_dir()})
    return {'schema':'project-epoch-package-transaction-evidence-v1','date':'2026-09-08','evidence_level':'verified-runtime',
        'evidence_scope':'two source-matched identical successful supported-PC queued-Tech observations; no helper installed',
        'sources':sources,'provenance':provenance,'inputs':inputs,'runtime':runtime,'runs':runs,'history':history,
        'identical_trace_sha256':TRACE_SHA,'identical_manifest_sha256':MANIFEST_SHA,'identical_prelaunch_sha256':PRELAUNCH_SHA,
        'observations':manifests[0]['observations'],'canonical_spans':spans,
        'annotation_revision':'eeae27acdb6565e96d1d796a3d60792c250c0aa1',
        'checkpoint_scope':'captured diagnostic checkpoint from recovered pre-Lavos SRAM; exact SRAM loaded into emulated SRAM during acquisition; current observer only reloads pinned state and supplies fixed joypad',
        'tests':{'command':'python -B -m unittest discover -s tests -p test_package_transaction_observation_v1.py','passed_at_freeze':41,'fixture_scope':'original synthetic metadata; not native refusal evidence'},
        'reproduce_observation':'python -B tools/run_package_transaction_observation_v1.py --output-dir private/test_runs/package_transaction_NEW_UNIQUE',
        'reproduce_metadata':'python -B tools/collect_package_transaction_evidence_v1.py',
        'serialization':'json.dumps(value, indent=2), UTF-8, LF, one trailing newline','production_approval':False}


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(collect(),indent=2))
