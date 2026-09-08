"""Read-only, source-frozen natural-refusal evidence; no launch or file writes."""
from __future__ import annotations
import hashlib,json,stat
from pathlib import Path
import run_package_natural_refusal_observation_v1 as observer
import audit_package_natural_refusal_boundaries_v1 as boundaries
ROOT=Path(__file__).resolve().parents[1]
RUNS=('package_natural_refusal_20260908_final1','package_natural_refusal_20260908_final2')
TRACE_SHA='63f94fff2b81292b593073e1197b7a8b8778cf6f4b217e2caa02adb0d61efd15'
MANIFEST_SHAS=('de617a852ac43de156c6895a987ef72494afdb886bc9b243dca27aee4070da2f','229dbaa3543f4d4b97706514a75ca84d85f36b4798aff3318add420cd5f896c1')
PRELAUNCH_SHA='8b4f33c4c5d77a78904867ca9c84f0b78f608681706c62125f73cc6f36762d50'
SOURCES={'launcher': ('tools/run_package_natural_refusal_observation_v1.py', '1a9e7a0e1b6d1bb51c94fe965bdf671562be0cd0695ea6e894b90796382ede76'), 'collector': ('tools/mesen_package_natural_refusal_observation_v1.lua', '0e5ceaf568f3744f87cbe495018d476f4957626756d65c872eab4259f38984de'), 'validation_library': ('tools/package_natural_refusal_validation_v1.py', '4422ee7448f37cfba6cfa73e78a8671a0a5dad50ebfd35a4c81a5643afc173e2'), 'tests': ('tests/test_package_natural_refusal_observation_v1.py', '7ee154740ac20ffcdf733d914230dc13213d7b2e8668790e61562776121a9b4a'), 'isolation_library': ('tools/run_mesen_field_animation_probe_v0.py', 'd5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96')}
PROVENANCE={
    'checkpoint_acceptance':('references/mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json','67cc7c9f7460a3de30a23c90aca53a079b8334c5e80c1975651fcdc60ba08564'),
    'checkpoint_collector':('tools/mesen_lavos_battle_checkpoint.lua','3bcc3146d9b5ef7fe7287f9031b7ad6f2d0c0423bfcf7c5f910efac4431cce11'),
    'checkpoint_launcher':('tools/run_mesen_lavos_battle_checkpoint.py','377024c212a72c4e2f3b000e44a7573cedd94093f86463c665be8925ae8c6321'),
    'canonical_bank_c1_annotation':('private/research/ct_disassembly_eeae27a/bank_C1.asm','298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa'),
    'canonical_bank_fd_annotation':('private/research/ct_disassembly_eeae27a/bank_FD.asm','0f8a0d59e97de7d60945fdfef1b614217e3d673cca1e14f543234d789a87779e')}
HISTORY=[('package_refusal_20260908_life2_living1', 'Life2 selected for living party; UI never queued a Tech', {'trace.json': 'ed65b25bf45e1782955102ae19df8a4a7fdb2078ba605e927c853df7dfb6fc25', 'manifest.json': '91b648d2bdaaa467a0cd033ba56855d1849671ac1b634e5ab468c540f4d4bbed', 'launch_inputs.json': 'f426f2712583cba9e4127e6f37e384e9d9f03be1c76f81046b36a4d881792404'}), ('package_natural_refusal_20260908_lavos_idle1', 'historical idle timeline ended at poll6000; no action input', {'trace.json': '24a929b49c3aef8f4395cd3949d807f11eded185d3c8a8fd5e4f3608c77e9ef1', 'manifest.json': '7b20b830d0c2f8d478dfeb0daa509bd1e52a487b101577800ec3df559bb7cd7c', 'launch_inputs.json': 'f11f86a4a348643fc26cb06e19c2552c40074dffe34a0b0864c44164c2d1b6f9'}), ('package_natural_refusal_20260908_lavos_cure1', 'first Cure experiment targeted Crono; successful ordinary Cure', {'trace.json': 'c163bb6d5a9c49e44190017781fe74b0335e951f52b1ebbdb5a01d62b864b40f', 'manifest.json': '1e3feb20802d29dc07e20c9fd1437ce4b4330f988c72f59e1ba55afbe9e557ad', 'launch_inputs.json': '32870c35e1bbc53204405559988bbd1006fb1d0a5b0ca21c25fec5fbcd02e3d4'}), ('package_natural_refusal_20260908_lavos_cure_lucca1', 'first natural dead-Lucca Cure refusal; exploratory schema only', {'trace.json': '0827235a26cc3e69ae4916e5c9b4b17681b37a954f41830e0bea31ee96046036', 'manifest.json': '0167883e4341e2bf7b9f8ced3e854cf5de8ed3fda72de35d07d69f64164a827f', 'launch_inputs.json': 'f06de421414ea733fe3321898fa064f8dfd2cafacb30c2072f02f41d00bd37d2'}), ('package_natural_refusal_20260908_observation_explore1', 'enriched trace rejected by overly early participant assertion; no accepted manifest', {'trace.json': 'a71a896c72795a7a03d72f026d8996e733421d870496b1a238df0356257e681f', 'launch_inputs.json': 'a712b21f16321171ef4a9c720816a17217bb735b72fce28eedd473b93e2b0c1d'}), ('package_natural_refusal_20260908_hardened1', 'source-matched hardening before final validator/test/archive changes; historical acceptance only', {'trace.json': '63f94fff2b81292b593073e1197b7a8b8778cf6f4b217e2caa02adb0d61efd15', 'manifest.json': '6d9c248b40a4cc29a47edd9e0be6a758364c9d44f83a0f312a3ef9f682093244', 'launch_inputs.json': '5eabd6d1536251e19e3b21737926a7e50ad68bc0f37b96ea24066a60493caaca'})]
BOUNDARIES={'auditor': ('tools/audit_package_natural_refusal_boundaries_v1.py', '216673a8e557e0c86e05d248d9f1ccd3c44ece4f1c1096afa109fbbd6c0ccc54'), 'reference': ('references/package_natural_refusal_boundaries_v1.json', '91aa1a0a01e56859c974a43690bf93e9ed27dff71f892c1939bb9e2b8aa512f0')}
def read(path,maximum=16*1024*1024):
    info=path.lstat()
    if path.resolve(strict=True)!=path or not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
        raise observer.ObservationError('unaliasable regular evidence file required')
    with path.open('rb') as stream:data=stream.read(maximum+1)
    if len(data)>maximum:raise observer.ObservationError('bounded evidence read exceeded')
    return data


def identity(path,expected=None):
    info=path.lstat()
    if path.resolve(strict=True)!=path or not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400 or info.st_size>256*1024*1024:
        raise observer.ObservationError('bounded regular identity source required')
    digest_state=hashlib.sha256();count=0
    with path.open('rb') as stream:
        while chunk:=stream.read(min(1024*1024,info.st_size-count+1)):
            count+=len(chunk)
            if count>info.st_size:raise observer.ObservationError('identity source grew while reading')
            digest_state.update(chunk)
    if count!=info.st_size:raise observer.ObservationError('identity source changed size')
    digest=digest_state.hexdigest()
    if expected is not None and digest!=expected:raise observer.ObservationError('frozen identity mismatch: '+path.name)
    return {'path':path.relative_to(ROOT).as_posix(),'size':count,'sha256':digest}


def collect():
    private=observer.safe.canonical_private_root()
    sources={k:identity(ROOT/p,h) for k,(p,h) in SOURCES.items()}
    provenance={k:identity(ROOT/p,h) for k,(p,h) in PROVENANCE.items()}
    inputs={}
    for k,(p,n,h) in observer.PINNED.items():
        path=observer.safe.resolve_private_file(ROOT/p,k,private_root=private);inputs[k]=identity(path,h)
        if inputs[k]['size']!=n:raise observer.ObservationError('pinned input size drift')
    runtime={}
    for k,name in observer.safe.RUNTIME_NAMES.items():
        path=observer.safe.resolve_private_file(observer.safe.DEFAULT_MESEN.parent/name,k,private_root=private)
        observer.safe.require_identity(path,k);runtime[k]=identity(path)
    expected_sources={k:d['sha256'] for k,d in {**sources,**inputs,**runtime}.items()}
    expected_staged={k:d['sha256'] for k,d in {**inputs,**runtime,'collector':sources['collector']}.items()}
    expected_archive={k:sources[k]['sha256'] for k in observer.ARCHIVE_KEYS}
    runs=[];manifests=[]
    for name,manifest_sha in zip(RUNS,MANIFEST_SHAS):
        directory=ROOT/'private/test_runs'/name
        def js(filename):return json.loads(read(directory/filename))
        trace_id=identity(directory/'trace.json',TRACE_SHA);manifest_id=identity(directory/'manifest.json',manifest_sha)
        launch_id=identity(directory/'launch_inputs.json',PRELAUNCH_SHA)
        trace,manifest,launch=js('trace.json'),js('manifest.json'),js('launch_inputs.json')
        summary=observer.summarize(trace)
        if observer.canonical(summary)!=observer.canonical(manifest['observations']):raise observer.ObservationError('revalidated summary differs')
        for receipt in (manifest,launch):
            if receipt['source_hashes']!=expected_sources or receipt['staged_hashes']!=expected_staged or receipt['archived_source_hashes']!=expected_archive:
                raise observer.ObservationError('prepared/completed input or archive identity set differs')
        if launch['schema']!=observer.SCHEMA or launch['status']!='prepared; native run not yet accepted' or observer.canonical(launch['fixed_inputs'])!=observer.canonical(observer.PINNED):
            raise observer.ObservationError('prelaunch source contract differs')
        if manifest['schema']!=observer.SCHEMA or manifest['trace_sha256']!=TRACE_SHA or manifest['sources_and_staged_inputs_unchanged'] is not True or any(manifest[k] is not False for k in ('rom_mutated','memory_or_cpu_injection','helper_installed','production_approval')):
            raise observer.ObservationError('read-only run scope differs')
        archived={k:identity(directory/'source_archive'/Path(p).name,h) for k,(p,h) in SOURCES.items()}
        stage=directory/'staged';app=stage/'app';saves=app/'Saves'
        roms=list(stage.glob('pe_resolver_*.sfc'));states=list(stage.glob('pe_resolver_*.mss'))
        if len(roms)!=1 or len(states)!=1 or roms[0].stem!=states[0].stem:raise observer.ObservationError('staged exact game filenames differ')
        staged={'rom':roms[0],'state':states[0],'sram':saves/(roms[0].stem+'.srm'),'collector':stage/'collector.lua',**{k:app/n for k,n in observer.safe.RUNTIME_NAMES.items()}}
        for k,path in staged.items():
            observer.safe.resolve_private_file(path,k,private_root=private);identity(path,expected_staged[k])
        observer.safe.require_exact_staged_save_entries(sorted(p.name for p in saves.iterdir()),staged['sram'].name)
        expected_names={f'menu_{i}.png' for i in (2180,2320,2390,2410,2435,2600,3600)}
        if set(manifest['screenshots'])!=expected_names or {p.name for p in directory.glob('menu_*.png')}!=expected_names:
            raise observer.ObservationError('documentary screenshot inventory differs')
        screenshots=[]
        for filename in sorted(expected_names):
            value=identity(directory/filename)
            if {k:value[k] for k in ('size','sha256')}!=manifest['screenshots'][filename]:raise observer.ObservationError('documentary screenshot changed')
            screenshots.append(value)
        runs.append({'directory':directory.relative_to(ROOT).as_posix(),'trace':trace_id,'manifest':manifest_id,'prelaunch':launch_id,
            'source_archive':archived,'screenshots':screenshots,'process_log':identity(directory/'process.log'),'all_staged_input_bytes_revalidated':True})
        manifests.append(manifest)
    differences=[k for k in manifests[0] if manifests[0][k]!=manifests[1].get(k)]
    if set(manifests[0])!=set(manifests[1]) or set(differences)-{'screenshots'}:raise observer.ObservationError('pair differs outside documentary screenshots')
    static_ids={k:identity(ROOT/p,h) for k,(p,h) in BOUNDARIES.items()}
    static=boundaries.audit(read(ROOT/observer.PINNED['rom'][0]))
    if (json.dumps(static,indent=2)+'\n').encode()!=read(ROOT/BOUNDARIES['reference'][0]):raise observer.ObservationError('static boundary reference differs')
    history=[]
    for name,status,pins in HISTORY:
        directory=ROOT/'private/test_runs'/name
        ids={file:identity(directory/file,h) for file,h in pins.items()}
        prepared=json.loads(read(directory/'launch_inputs.json'))
        archive=directory/'source_archive';files=list(archive.iterdir())
        historical_hashes={prepared['source_hashes'][k] for k in observer.ARCHIVE_KEYS}
        if len(files)!=5 or {identity(p)['sha256'] for p in files}!=historical_hashes:raise observer.ObservationError('historical exact source archive differs')
        history.append({'directory':directory.relative_to(ROOT).as_posix(),'status':status,'artifacts':ids,'exact_five_source_archive_verified':True,
            'accepted_as_final_pair':False,'historical_launcher_command_requires_its_archived_source_revision':True})
    return {'schema':'project-epoch-package-natural-refusal-evidence-v1','date':'2026-09-08','evidence_level':'verified-runtime',
        'scope':'two source-matched identical controller-only naturally refused Cure transactions from the pinned diagnostic checkpoint',
        'sources':sources,'metadata_collector':identity(Path(__file__).resolve()),'inputs':inputs,'runtime':runtime,'provenance':provenance,
        'checkpoint_scope':'recovered SRAM was copied into emulated SRAM during historical checkpoint acquisition; current observer only loads the pinned state and supplies joypad',
        'runs':runs,'identical_trace_sha256':TRACE_SHA,'identical_prelaunch_sha256':PRELAUNCH_SHA,'manifest_differing_fields':differences,
        'observations':manifests[0]['observations'],'static_boundary_artifacts':static_ids,'static_boundaries':static,'history':history,
        'independent_review':'root reviewed observer/validator/runner, all41 tests and hardened trace, then archive hardening before final pair',
        'tests':{'passed_at_freeze':41,'command':'python -B -m unittest discover -s tests -p test_package_natural_refusal_observation_v1.py','fixtures':'original synthetic metadata and original source-archive files, not game traces'},
        'reproduce_observation':'python -B tools/run_package_natural_refusal_observation_v1.py --output-dir private/test_runs/package_natural_refusal_NEW_UNIQUE',
        'reproduce_metadata':'python -B tools/collect_package_natural_refusal_evidence_v1.py',
        'serialization':'json.dumps(value, indent=2), UTF-8, LF, one trailing newline','production_approval':False}


if __name__=='__main__':print(json.dumps(collect(),indent=2))
