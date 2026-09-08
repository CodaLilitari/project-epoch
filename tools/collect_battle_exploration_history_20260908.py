"""Read-only provenance census of seventeen preserved exploratory battle routes.

This artifact indexes historical evidence. It does not accept those runs,
reconstruct missing historical launcher revisions, or launch an emulator.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
MANIFESTS={'alternate_branch_20260908_baseline_hit_evade': 'c5cf3d4e97a4801996bddcf82d826cc1fe2b1bed97ce69ba6214d7ad14def216',
 'alternate_branch_20260908_baseline_menu': '8fd819317b7ce55e17d75075d0094613ca783693851b171009f9bbe6d45b205d',
 'alternate_branch_20260908_crono-spincut': 'e2adb698ed625d1ee0d3902c35397896217703e00b5ccbbdb68c741777ec7c7f',
 'alternate_branch_20260908_crono-spincut-left': '2acc581212b723d1f889b09ec67242c92041fd4f72557fd6aaa6b5c255a02bee',
 'alternate_branch_20260908_crono-spincut-right': '74e0fbe7206bf04e8652b1d2547c6b025b92cef34d95762a4f66d58882cefd6b',
 'alternate_branch_20260908_lucca_hypnowave1': '4d600c68c8ee155e0cdec489a992e4dc4aa2971ae99cd9519fe3b32f2e026ba6',
 'alternate_branch_20260908_marle_delayed_menu': '835696394a9ab3ed3e96e1af042961ec0fb2de2a0672fe1aa32fde277a0401d8',
 'alternate_branch_20260908_marle_menu': 'e77295ce381601521e788a49fb3941effd4e18db953f077aa55369e69435224f',
 'alternate_branch_20260908_marle_provoke1': 'c82af835cb8179fc532c47b8784f694cc4d98890da2430e83a2c02fbd04a9ba4',
 'alternate_branch_20260908_marle_provoke2': '2ed5a563f725146c3faf53cde6a5962483b1e9b131bdc64fa9caf17c964a54f6',
 'alternate_branch_20260908_marle_ready_menu': '8bcc4293d124266fa60f6e371d32a9809bd5790e0b8f31d6359d8fbc1fb86f11',
 'alternate_branch_20260908_spekkio_magus_black_hole1': 'd10fe7cfd3b21e0c2f0013f48007a0e2a8a1a6b8ba1d86463839247f9fb04379',
 'alternate_branch_20260908_spekkio_robo_rocket1': '0cf59e48d5a2dfb429d7e6448a15708faa114fddf454786fc71571e3eefc7645',
 'alternate_branch_20260908_spekkio_robo_rocket2': '398712b36e6dcdd71fa9132926111488a01f7c7531032a10ab7b6066b58c790f',
 'alternate_branch_20260908_spekkio_talk1': '53210f589b5e5e361b8b31c974c3eb01215de92b0b4acb1577f5ad565acbd253',
 'alternate_branch_20260908_spincut_accuracy': '32e06b93c4bdf9e4e6abf591c0d35ecd55a5fd97747431ea1139083f06d8dc39',
 'package_refusal_20260908_life2_living1': '91b648d2bdaaa467a0cd033ba56855d1849671ac1b634e5ab468c540f4d4bbed'}
CURRENT_SOURCES=(
    'tools/run_package_alternate_branch_probe_v1.py',
    'tools/mesen_package_alternate_branch_probe_v1.lua',
    'tools/run_package_refusal_probe_v1.py',
    'tools/mesen_package_refusal_probe_v1.lua',
)


def identity(path,expected=None):
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if expected is not None and sha!=expected:raise ValueError('historical identity mismatch: '+path.name)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':sha}


def collect():
    current=[identity(ROOT/p) for p in CURRENT_SOURCES]
    rows=[]
    for name,pin in MANIFESTS.items():
        directory=ROOT/'private/test_runs'/name
        manifest_id=identity(directory/'manifest.json',pin)
        manifest=json.loads((directory/'manifest.json').read_bytes())
        trace_id=identity(directory/'trace.json',manifest['trace_sha256'])
        trace=json.loads((directory/'trace.json').read_bytes())
        if trace['error'] is not None:raise ValueError('expected completed exploration')
        records=trace['records'];counts=dict(sorted(Counter(r['kind'] for r in records).items()))
        if len(records)!=manifest['observations']['record_count']:raise ValueError('historical record count mismatch')
        collector=identity(directory/'staged/collector.lua',manifest['source_hashes']['collector'])
        if collector['sha256']!=manifest['staged_hashes']['collector']:raise ValueError('staged collector receipt mismatch')
        source_available={}
        for key in ('launcher','collector'):
            source_available[key]=[s['path'] for s in current if s['sha256']==manifest['source_hashes'][key]]
        historical_archives=[]
        archive=directory/'source_archive'
        if archive.exists():
            for p in sorted(archive.iterdir()):
                if p.is_file():historical_archives.append(identity(p))
            expected={manifest['source_hashes'][key] for key in
                ('launcher','collector','isolation_library','validation_library','tests')}
            if {item['sha256'] for item in historical_archives}!=expected:
                raise ValueError('historical source archive differs from recorded five-source set')
        prelaunch=identity(directory/'launch_inputs.json') if (directory/'launch_inputs.json').exists() else None
        row={'run':name,'manifest':manifest_id,'trace':trace_id,'staged_collector':collector,
            'prelaunch_receipt':prelaunch,'historical_source_archives':historical_archives,
            'recorded_source_hashes':manifest['source_hashes'],'matching_current_sources':source_available,
            'route':manifest.get('route','fixed Life2 selection against a living party'),
            'records':len(records),'event_counts':counts,
            'observed_branch_words':sorted({r['branch_word'] for r in records if r['kind']=='resolver-entry'}),
            'historical_reproduce_argv':manifest['reproduce'],
            'accepted_runtime_evidence':False,
            'reproduction_limit':'historical manifest command alone cannot reproduce an unavailable historical launcher; use the source identities and retained staged Lua, not a substituted current version'}
        if name.endswith('spekkio_magus_black_hole1'):
            row['outcome']='alternate branch discovery only; superseded by the separately accepted focused alternate observer'
        elif name.startswith('package_refusal_'):
            row['outcome']='Life2 selection on a living party did not queue an action in this bounded route; no natural refusal witness'
        elif not counts.get('resolver-entry',0):row['outcome']='menu/setup exploration with no player resolver entry'
        else:row['outcome']='ordinary primary-branch discovery; no accepted alternate-branch proof'
        rows.append(row)
    return {'schema':'project-epoch-battle-exploration-history-20260908-v1','date':'2026-09-08',
        'evidence_level':'hypothesis','scope':'hash-verified history and discovery metadata; no new native acceptance',
        'collector_source':identity(Path(__file__).resolve()),'current_source_identities':current,
        'run_count':len(rows),'runs':rows,
        'current_source_note':'the alternate launcher/collector match the final Black Hole exploration; earlier launcher revisions may be unavailable. Life2 matches its retained archive.',
        'accepted_successor':'docs/schala_package_resolver_alternate_v1.md',
        'private_artifacts_unchanged':True,'production_approval':False,
        'reproduce':['python','-B','tools/collect_battle_exploration_history_20260908.py']}


if __name__=='__main__':sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode())
