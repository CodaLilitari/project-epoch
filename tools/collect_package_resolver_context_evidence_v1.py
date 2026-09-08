"""Reproduce metadata-only acceptance of the two frozen context observations.

Reads existing private artifacts, validates current source and evidence, and
prints deterministic JSON. It launches no emulator and writes no files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import run_package_resolver_context_v1 as observer


ROOT=Path(__file__).resolve().parents[1]
RUNS=('resolver_context_20260908_final1','resolver_context_20260908_final2')
MESEN_COMMIT='137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1'
TRACE_SHA256='6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679'
MANIFEST_SHA256='abc8abbbf135fb1bc4e79ad4b893977015936fb55b4f76746dabd19b573a5c13'
MESEN_SOURCES=(
    ('Core/Debugger/LuaApi.cpp','fd1292483bd2e7fa1f5a13c392afadcae2d9ff418cab216c964d623f97e10e24','4deebdedaf976b584574a4c2371f614cc929f4ff'),
    ('Core/SNES/SnesConsole.cpp','cdfa45011f3dfd39fa5a8686e7f827cb8ea660d5a1b79ecb20da9d0c2606c706','94ed65811b6c5db95b2abbc4786d0faf303c22b8'),
    ('Core/SNES/SnesCpu.Shared.h','dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f','bbabf420bd1bd8899b62e392fcadcf3a500468c5'),
    ('Core/SNES/SnesMemoryManager.cpp','2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58','8c7b9433f1aa33aa42624b9c7686b91136fdcd2e'),
    ('Core/SNES/SnesPpu.cpp','5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180','3c7245217083e3e7d9ce72bcf2e037f43b463b0b'),
    ('Core/SNES/SnesCpu.cpp','ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8','e8441981c7f2527e16303ddd35d5010deec850f7'),
    ('Core/SNES/SnesCpu.Instructions.h','9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd','46b8553e24ab5151c0da049b4fcc49289c3648a9'),
)
SOURCE_FILES={
    'launcher':('tools/run_package_resolver_context_v1.py','88ccf83e83a68f7bbdc3c65e626b1480041c9e95db4fe36541a6c267b8030214'),
    'collector':('tools/mesen_package_resolver_context_v1.lua','f7b74d551b74e1b81f0b1be68f07a96ab1a6915a42d6d1d0d832b6d7be5b6519'),
    'tests':('tests/test_package_resolver_context_v1.py','8927c5ee0d2b29a89e59f5a9534a1a42c0e42511a6efaa8f07b8d590de53d86a'),
    'isolation_library':('tools/run_mesen_field_animation_probe_v0.py','d5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96'),
}


def identity(path:Path)->dict:
    data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def collect()->dict:
    private=observer.safe.canonical_private_root()
    source_files={}
    for name,(relative,expected) in SOURCE_FILES.items():
        value=identity(ROOT/relative)
        if value['sha256']!=expected:
            raise observer.ObservationError('accepted source drift: '+name)
        source_files[name]=value
    source_files['evidence_collector']=identity(Path(__file__).resolve())
    sources=[]
    for upstream_path,expected,blob_expected in MESEN_SOURCES:
        path=observer.safe.resolve_private_file(ROOT/'private/research/mesen_timing_api_2_1_1'/Path(upstream_path).name,'Mesen source',private_root=private)
        data=path.read_bytes(); value=identity(path)
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if value['sha256']!=expected or blob!=blob_expected:
            raise observer.ObservationError('pinned Mesen source mismatch')
        sources.append({**value,'upstream_path':upstream_path,'git_blob_sha1':blob,
            'url':f'https://github.com/SourMesen/Mesen2/blob/{MESEN_COMMIT}/{upstream_path}'})
    runs=[]; manifests=[]; traces=[]
    for name in RUNS:
        directory=ROOT/'private/test_runs'/name
        manifest_path=observer.safe.resolve_private_file(directory/'manifest.json','run manifest',private_root=private)
        trace_path=observer.safe.resolve_private_file(directory/'trace.json','run trace',private_root=private)
        manifest=observer.safe.decode_json_object(observer.safe.read_direct_regular_file(manifest_path,'manifest',parent=directory,maximum=2*1024*1024),'manifest')
        trace=observer.safe.decode_json_object(observer.safe.read_direct_regular_file(trace_path,'trace',parent=directory,maximum=64*1024*1024),'trace')
        summary=observer.summarize(trace)
        if manifest.get('schema')!=observer.SCHEMA or observer.canonical(summary)!=observer.canonical(manifest.get('observations')):
            raise observer.ObservationError('manifest does not match revalidated trace')
        if manifest.get('sources_and_staged_inputs_unchanged') is not True or any(manifest.get(k) is not False for k in ('rom_mutated','memory_or_cpu_injection','helper_installed','production_approval')):
            raise observer.ObservationError('run does not satisfy read-only scope')
        for source in ('launcher','collector','isolation_library'):
            if manifest['source_hashes'].get(source)!=source_files[source]['sha256']:
                raise observer.ObservationError('run source identity differs from accepted source')
        for key,(_,_,expected) in observer.PINNED.items():
            if manifest['source_hashes'].get(key)!=expected or manifest['staged_hashes'].get(key)!=expected:
                raise observer.ObservationError('run input identity mismatch')
        for key in observer.safe.RUNTIME_NAMES:
            if manifest['source_hashes'].get(key)!=manifest['staged_hashes'].get(key):
                raise observer.ObservationError('run runtime copy mismatch')
        trace_identity=identity(trace_path)
        if trace_identity['sha256']!=manifest['trace_sha256']:
            raise observer.ObservationError('trace hash differs from run manifest')
        if trace_identity['sha256']!=TRACE_SHA256 or identity(manifest_path)['sha256']!=MANIFEST_SHA256:
            raise observer.ObservationError('frozen accepted artifact identity mismatch')
        runs.append({'run_directory':directory.relative_to(ROOT).as_posix(),
                     'manifest':identity(manifest_path),'trace':trace_identity,
                     'process_log':identity(directory/'process.log')})
        manifests.append(manifest); traces.append(trace)
    if observer.canonical(manifests[0])!=observer.canonical(manifests[1]) or observer.canonical(traces[0])!=observer.canonical(traces[1]):
        raise observer.ObservationError('frozen repeated observations differ')
    rom_path=observer.safe.resolve_private_file(ROOT/observer.PINNED['rom'][0],'canonical ROM',private_root=private)
    rom=rom_path.read_bytes()
    if len(rom)!=observer.PINNED['rom'][1] or hashlib.sha256(rom).hexdigest()!=observer.PINNED['rom'][2]:
        raise observer.ObservationError('canonical ROM drift')
    spans=[]
    for name,start,end in (
        ('canonical-resolver',0xC14612,0xC14682),
        ('direct-page-positive-control-instruction',0xC14627,0xC14629),
        ('normal-nmi-handler',0xD1E77C,0xD1E899),
        ('battle-irq-handler',0xD1FE97,0xD1FEF4),
        ('alternate-nmi-handler-not-observed',0xD1F4C0,0xD1F559),
        ('scene-latch-tick-and-clear',0xCD1609,0xCD1654)):
        data=rom[start&0x3FFFFF:end&0x3FFFFF]
        spans.append({'name':name,'evidence_level':'verified-static','cpu_start':f'{start:06X}','cpu_end_exclusive':f'{end:06X}',
                      'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    return {
        'schema':'project-epoch-package-resolver-context-evidence-v1','date':'2026-09-08',
        'evidence_level':'verified-runtime','evidence_scope':'two identical bounded clean-ROM context observations; no helper installed',
        'private_manifest_status_preserved':'exploratory-runtime-not-accepted; this separate reference records reviewed repeated acceptance',
        'source_files':source_files,'mesen_source_revision':MESEN_COMMIT,'mesen_source_files':sources,
        'source_input_hashes':manifests[0]['source_hashes'],'runs':runs,
        'identical_trace_sha256':runs[0]['trace']['sha256'],'identical_manifest_sha256':runs[0]['manifest']['sha256'],
        'observations':manifests[0]['observations'],'canonical_spans':spans,
        'validator_tests':{'command':'python -B -m unittest discover -s tests -p test_package_resolver_context_v1.py','tests_passed_at_freeze':30,'fixture_scope':'original synthetic metadata, including a feasible latched IRQ-I1 boundary; not new native interrupt schedules'},
        'history':[
            {'run_directory':'private/test_runs/resolver_context_20260908_explore1',
             'manifest':identity(ROOT/'private/test_runs/resolver_context_20260908_explore1/manifest.json'),
             'trace':identity(ROOT/'private/test_runs/resolver_context_20260908_explore1/trace.json'),
             'status':'historical exploratory trace has superseded timing-key shape; unmodified and not accepted by current strict schema'},
            {'run_directory':'private/test_runs/resolver_context_20260908_hardened1',
             'manifest':identity(ROOT/'private/test_runs/resolver_context_20260908_hardened1/manifest.json'),
             'trace':identity(ROOT/'private/test_runs/resolver_context_20260908_hardened1/trace.json'),
             'status':'preserved pre-final-validator exploratory replay; current final runs independently repeated after source freeze'}],
        'reproduce_observation':'python -B tools/run_package_resolver_context_v1.py --output-dir private/test_runs/resolver_context_NEW_UNIQUE',
        'reproduce_reference':'python -B tools/collect_package_resolver_context_evidence_v1.py',
        'serialization':'json.dumps(value, indent=2), UTF-8, LF, exactly one trailing newline',
        'production_approval':False,
    }


def main()->None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(collect(),indent=2))


if __name__=='__main__': main()
