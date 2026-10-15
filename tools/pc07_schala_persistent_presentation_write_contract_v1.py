"""Fixed additive Schala presentation over the accepted cold-loader image.

Accepted receipts are data. Only the unchanged retail provider conversion runs;
no historical image recipe, validation chain, native run or art generation.
"""
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
import builtins
import hashlib
import json
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-epoch-private-schala-persistent-presentation-intents-v1'
SIZE = 0x800000
SOURCE_SHA = '2ce5e5a1719cf944079089691450e58a28d57f9ec94f2b7d6b5428b841d7989b'
SOURCE = dict(path='private/test_runs/pc07_native_sidecar_loader_v1/diagnostic.sfc', bytes=SIZE, sha256=SOURCE_SHA)
PARENT_BUILD = dict(path='private/test_runs/pc07_native_sidecar_loader_v1/receipt.json', bytes=23518, sha256='7730c663a2d7df84b7622369ce4ef5a83b8b1af2d3f29f1340ce30e6e379e459')
PARENT_NATIVE = dict(path='private/test_runs/pc07_native_sidecar_cold_load_v1_battle_run1/continuation_validation_result_v1.json', bytes=8388, sha256='727231e149e1b42c4aef8b63bd83b930eef262c97eb2e70f2709b8023f792286')
RECIPE = dict(path='references/pc07_schala_presentation_private_contract_v2.json', bytes=21004, sha256='6795e2064dc8754a0c09567427fd089bc333b07b20e94b52a8a2f9cb4ec8d3ad')
OBSERVATION = dict(path='references/pc07_schala_presentation_observation_2026_10_13.json', bytes=5031, sha256='2b9e0e461b268b3484d635e02c37569e7dc81598d136ea75c6b91c09e2e9df78')
TEMPORAL = dict(path='private/research/pc07_schala_presentation_temporal_review_20261013/receipt.json', bytes=6979, sha256='650b9c9682e6d94ead85d12c86acfe6a9ec0d1a7766d6cd95d120a501e25e9aa')
ALLOCATION = dict(path='private/research/pc07_save_preview_installation_design_20261014/installation_design_v1.json', bytes=43842, sha256='bef42505563df50e68810f3396119face4a3ea9f5ba7ea554bbf95789f991b5e')
SCAFFOLD = dict(path='tools/schala_rom_scaffold.py', bytes=13386, sha256='a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a')
CANONICAL = dict(path='private/input/rom_archive/Chrono Trigger (USA).sfc', bytes=0x400000, sha256='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9')
CORPUS = dict(path='tools/audit_ct_compressed_sprite_corpus.py', bytes=34780, sha256='5dcba015098dcf5a9ec754a5537f35ab67144f0ac09d166e7644741a74ae990d')
PROVIDER_PATH = 'tools/build_pc07_schala_presentation_v1.py'
NPC_PATH = 'tools/build_schala_vanilla_npc_compat_v0.py'
FALLBACK_PATH = 'tools/build_schala_vanilla_npc_supported_slot_smoke_v0.py'
INHERITED_ADDITIONS = (
 ('shadow-wrapper', 0x443000, 173), ('round8-core', 0x450000, 0x4A26), ('sigma-tables', 0x460000, 0x4000),
 ('native-sidecar-writer', 0x443100, 570), ('load-preflight-suffix', 0x442032, 58), ('native-sidecar-loader', 0x443400, 671))
SUPERSEDED = dict(id='battle-name', file_start=0x0CE616, bytes=4, provenance='inherited-native-transition')
GUARD_INTENT = 'validate_pc07_schala_persistent_presentation_manifest'
GUARD_DIFF = 'audit_pc07_schala_persistent_presentation_images'
_ACTIVE = None


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
def exact(a, b, message): need(encoded(a) == encoded(b), message)


def path(relative):
    need(type(relative) is str and '\\' not in relative and ':' not in relative, 'canonical relative path')
    parts = relative.split('/')
    need(parts and all(p and p not in ('.', '..') for p in parts), 'path traversal refused')
    result = ROOT.joinpath(*parts)
    for item in (result, *result.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400, 'aliased project path')
    need(result.resolve().is_relative_to(ROOT.resolve()), 'path escapes project')
    return result


def read_pin(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'exact input identity')
    p = path(row['path'])
    need(p.is_file() and p.stat().st_size == row['bytes'], 'input extent drift: ' + row['path'])
    raw = p.read_bytes()
    need(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'input identity drift: ' + row['path'])
    return raw


def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_schala_persistent_presentation_[A-Za-z0-9_-]+/diagnostic\.sfc', relative),
         'fresh named private persistent-presentation destination required')
    return path(relative)


def compile_captured_provider(raws, canonical):
    """Execute the existing conversion from captured source, with cached imports.

    Only dependency acquisition changes: NPC's one CORPUS assignment binds the
    already captured decoder; provider source-pin reads use captured buffers.
    The existing decoder, build_bundle and fallback/compile functions are intact.
    The old supported-slot writer's unused guard import is deliberately inert.
    """
    modules = {}; installed = []
    original_import = builtins.__import__
    def load(relative, short, extra=None, corpus_binding=False):
        raw = raws[relative]
        if corpus_binding:
            before = b'CORPUS = _load_corpus_tool()'
            need(raw.count(before) == 1, 'exact captured decoder binding seam')
            raw = raw.replace(before, b'CORPUS = _CAPTURED_CORPUS', 1)
        name = '_epoch_persistent_schala_' + short
        need(name not in sys.modules, 'isolated provider module name in use')
        module = ModuleType(name); module.__file__ = str(path(relative))
        def captured_import(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and name in modules:
                return modules[name]
            return original_import(name, globals, locals, fromlist, level)
        module.__dict__.update(extra or {})
        module.__dict__['__builtins__'] = dict(vars(builtins), __import__=captured_import)
        sys.modules[name] = module; installed.append(name)
        exec(compile(raw, module.__file__, 'exec'), module.__dict__)
        return module
    class CapturedFile:
        def __init__(self, raw): self.raw = raw
        def read_bytes(self): return self.raw
    class CapturedRoot:
        def __truediv__(self, name):
            need(name in (NPC_PATH, FALLBACK_PATH), 'provider source read outside exact captured dependencies')
            return CapturedFile(raws[name])
    try:
        corpus = load(CORPUS['path'], 'corpus')
        npc = load(NPC_PATH, 'npc', {'_CAPTURED_CORPUS': corpus}, corpus_binding=True)
        modules['build_schala_vanilla_npc_compat_v0'] = npc
        modules['validate_rom_write_intents'] = ModuleType('_unused_historical_writer_guard')
        fallback = load(FALLBACK_PATH, 'fallback')
        modules['build_schala_vanilla_npc_supported_slot_smoke_v0'] = fallback
        provider = load(PROVIDER_PATH, 'provider'); provider.ROOT = CapturedRoot()
        compiled = provider.compile_provider(canonical)
        return compiled.assets, compiled.metadata
    finally:
        for name in installed:
            sys.modules.pop(name, None)


def qualify_sections(source, spec, occupied, payloads):
    """Fixed whole spans; only the named 4-byte donor-name hook is superseded."""
    need(len(spec['new_sections']) == 26 and len({r['id'] for r in spec['new_sections']}) == 26, 'exact26 section recipe')
    rows = sorted(spec['new_sections'], key=lambda r: r['file_start']); previous = 0; overlaps = []
    for r in rows:
        start, size = r['file_start'], r['bytes']; end = start + size
        need(type(start) is int and type(size) is int and size > 0 and start >= previous and end <= SIZE, 'section extent or overlap')
        previous = end
        need(sha(source[start:end]) == r['accepted_preimage_sha256'], 'whole accepted preimage drift: ' + r['id'])
        need(len(payloads[r['id']]) == size and sha(payloads[r['id']]) == r['sha256'], 'exact payload drift: ' + r['id'])
        for old in occupied:
            if max(start, old['file_start']) < min(end, old['file_start'] + old['bytes']):
                need(r['id'] == 'name-active-name-source' and start == 0x0CE616 and size == 37 and old == SUPERSEDED,
                     'unauthorized inherited overlap: ' + r['id'])
                overlaps.append(old)
        if r['kind'] in ('original-helper', 'retail-provider'):
            need(0x410000 <= start < end <= 0x7E0000 and start >> 16 == (end - 1) >> 16, 'bounded expanded allocation')
            need(source[start:end] == b'\xFF' * size, 'exact expanded preimage')
        else:
            need(r['kind'] == 'instruction-hook', 'unknown section kind')
    exact(overlaps, [SUPERSEDED], 'exact single donor-name supersession required')
    return rows


def qualify():
    """One operation snapshot; no old recipe()/validator/reproducer execution."""
    rows = {}; raws = {}
    def add(row):
        if row['path'] in rows:
            exact(rows[row['path']], row, 'conflicting input pin'); return raws[row['path']]
        raw = read_pin(row); rows[row['path']] = dict(row); raws[row['path']] = raw; return raw
    source = add(SOURCE); parent = json.loads(add(PARENT_BUILD)); native = json.loads(add(PARENT_NATIVE))
    spec = json.loads(add(RECIPE)); observation = json.loads(add(OBSERVATION)); temporal = json.loads(add(TEMPORAL))
    allocation = json.loads(add(ALLOCATION)); add(SCAFFOLD); canonical = add(CANONICAL); add(CORPUS)
    need(parent['emitted'] is True and parent['target_sha256'] == SOURCE_SHA and parent['artifacts']['diagnostic.sfc'] == SOURCE, 'accepted parent image binding')
    need(parent['current_shared_intent']['status'] == 'metadata-valid' and parent['current_shared_diff']['status'] == 'images-valid'
         and parent['current_shared_diff']['complete_diff_coverage'] is True, 'accepted parent guarded construction')
    exact(native['inputs']['diagnostic.sfc'], dict(bytes=SIZE, sha256=SOURCE_SHA), 'accepted native image binding')
    need(native['result']['status'] == 'accepted-bounded-native-cold-load-Attack' and native['result']['passed'] is True
         and native['fresh_process'] is True and native['debugger_game_state_injection'] is False, 'accepted parent cold-load Attack')
    exact(observation['recipe'], RECIPE, 'accepted presentation recipe binding')
    exact(observation['temporal_requalification'], TEMPORAL, 'accepted temporal receipt binding')
    exact(observation['trace'], temporal['trace'], 'same accepted presentation trace')
    need(observation['status'] == 'verified-runtime-selected-private-presentation'
         and temporal['status'] == 'accepted-existing-run-under-corrected-temporal-contract'
         and temporal['original_seven_records_all48names_Epoch_preserved'] is True, 'accepted presentation evidence')
    need(spec['schema'] == 'project-epoch-pc07-schala-private-recipe-v2' and spec['target_sha256'] == observation['image']['sha256'], 'exact v2 recipe')
    inherited = allocation['allocation']['inherited_occupied_spans']
    need(len(inherited) == 46 and allocation['allocation']['inert_scaffold_sha256'] == '26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93', 'scaffold allocation provenance')
    need(parent['manifest']['provenance']['inherited_census_span_records'] == 46
         and parent['manifest']['provenance']['inherited_shadow_span_records'] == 3
         and parent['manifest']['provenance']['inherited_writer_span_records'] == 1, 'current parent allocation provenance')
    for name, start, size in INHERITED_ADDITIONS[-2:]:
        matching = [r for r in parent['manifest']['sections'] if r['id'] == name]
        need(len(matching) == 1 and (matching[0]['file_start'], matching[0]['bytes']) == (start, size), 'accepted loader placement')
    occupied = inherited + [dict(id=name, file_start=start, bytes=size, provenance='accepted-cold-loader-parent') for name, start, size in INHERITED_ADDITIONS]
    def source_pin(name):
        matches = [r for r in spec['sources'] if r['path'] == name]
        need(len(matches) == 1, 'unique recipe source pin: ' + name); return matches[0]
    for name in (PROVIDER_PATH, NPC_PATH, FALLBACK_PATH): add(source_pin(name))
    for component in spec['assembly_components']: add(source_pin(component['source']))
    assets, provider_metadata = compile_captured_provider(raws, canonical)
    payloads = {}
    for r in spec['new_sections']:
        if r['kind'] == 'retail-provider': payloads[r['id']] = assets[r['id']]
        elif r['kind'] == 'original-helper': payloads[r['id']] = add({k: r[k] for k in ('path', 'bytes', 'sha256')})
        elif r['kind'] == 'instruction-hook': payloads[r['id']] = bytes.fromhex(r['replacement_hex'])
        else: raise ValueError('unknown presentation payload kind')
    sections = qualify_sections(source, spec, occupied, payloads)
    return dict(source=source, sections=sections, payloads=payloads, occupied=occupied, source_rows=sorted(rows.values(), key=lambda r: r['path']),
                provider=provider_metadata, labels=parent['labels'], provenance=dict(
                    accepted_parent_build=PARENT_BUILD, accepted_parent_native=PARENT_NATIVE, accepted_presentation=OBSERVATION,
                    accepted_temporal_name_result=TEMPORAL, exact_v2_recipe=RECIPE, allocation_census=ALLOCATION, scaffold_source=SCAFFOLD,
                    inherited_occupied_span_records=len(occupied), superseded_exact_hook=SUPERSEDED,
                    new_expanded_allocations=7, new_allocations_disjoint=True, FF_alone_is_authority=False,
                    inherited_expanded_fill=dict(start=0x410000, end=0x7E0000, fill=255),
                    provider_conversion_calls=1, captured_dependency_imports=True, canonical_asset_conversion_unchanged=True,
                    historical_recipe_or_validator_chain_executed=False))


@contextmanager
def source_snapshot():
    global _ACTIVE
    need(_ACTIVE is None, 'nested operation snapshot refused')
    _ACTIVE = qualify()
    try: yield _ACTIVE
    finally: _ACTIVE = None


def inputs(): return _ACTIVE if _ACTIVE is not None else qualify()


def derive(snapshot):
    if '_derived_target' in snapshot: return snapshot['_derived_target']
    source = snapshot['source']; target = bytearray(source)
    for r in snapshot['sections']:
        target[r['file_start']:r['file_start'] + r['bytes']] = snapshot['payloads'][r['id']]
    checksum = sum(target) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, 'little') + checksum.to_bytes(2, 'little')
    for start in (0xFFDC, 0x40FFDC): target[start:start + 4] = pair
    need(sum(target) & 0xFFFF == checksum and target[:0x10000] == target[0x400000:0x410000], 'checksum/full boot mirror')
    for old in snapshot['occupied']:
        if old == SUPERSEDED: continue
        start, size = old['file_start'], old['bytes']
        # Historical header rows are intentionally updated as the two named checksums.
        if start in (0xFFDC, 0x40FFDC) and size == 4: continue
        need(target[start:start + size] == source[start:start + size], 'inherited occupied bytes changed: ' + old['id'])
    snapshot['_derived_target'] = bytes(target); snapshot['_target_sha'] = sha(snapshot['_derived_target'])
    return snapshot['_derived_target']


def template(snapshot, target, output):
    output_path(output); source = snapshot['source']; rows = []
    spans = [('checksum-primary', 0xFFDC, 4, 'header'), ('checksum-boot-mirror', 0x40FFDC, 4, 'header')]
    spans += [(r['id'], r['file_start'], r['bytes'], r['kind']) for r in snapshot['sections']]
    for name, start, size, kind in sorted(spans, key=lambda r: r[1]):
        before, after = source[start:start + size], target[start:start + size]
        rows.append(dict(id=name, file_start=start, bytes=size, kind=kind, preimage_sha256=sha(before), sha256=sha(after),
                         changed_bytes=sum(a != b for a, b in zip(before, after)), preimage_hex=before.hex(), owner='pc07-private-persistent-schala-presentation-v1'))
    return dict(schema=SCHEMA, mode='private-additive-Schala-presentation', source=SOURCE,
                target=dict(bytes=SIZE, sha256=snapshot['_target_sha']), output=output, sections=rows,
                provenance=snapshot['provenance'], save_load_layout_unchanged=True, existing_event_packets_unchanged=True,
                fixed_battle_name='Schala', required_battle_gauge_display_type=2, editable_global_name=False,
                production_approval=False, native_execution=False, combined_runtime_result_proved=False,
                evidence_level='fixed-private-source-composition-only')


def validate_manifest(manifest):
    need(type(manifest) is dict, 'exact additive presentation manifest')
    snapshot = inputs(); target = derive(snapshot)
    exact(manifest, template(snapshot, target, manifest.get('output')), 'fixed presentation manifest mismatch')
    return dict(status='metadata-valid', schema=SCHEMA, manifest_sha256=sha(encoded(manifest)), production_approval=False)


def audit_images(manifest, source, target):
    snapshot = inputs(); expected = derive(snapshot)
    need(type(source) is bytes and source == snapshot['source'], 'exact current cold-loader parent required')
    need(type(target) is bytes and target == expected, 'exact additive presentation target required')
    exact(manifest, template(snapshot, expected, manifest.get('output')), 'fixed presentation manifest mismatch')
    cursor = changed = 0; inverse = bytearray(target)
    for r in manifest['sections']:
        start, end = r['file_start'], r['file_start'] + r['bytes']
        need(start >= cursor and source[cursor:start] == target[cursor:start], 'undeclared or overlapping presentation write')
        need(sha(source[start:end]) == r['preimage_sha256'] and sha(target[start:end]) == r['sha256'], 'exact presentation span bytes')
        n = sum(a != b for a, b in zip(source[start:end], target[start:end])); need(n == r['changed_bytes'], 'per-span changed bytes')
        changed += n; inverse[start:end] = source[start:end]; cursor = end
    need(source[cursor:] == target[cursor:] and bytes(inverse) == source, 'complete difference/inverse coverage')
    return dict(status='images-valid', schema=SCHEMA, manifest_sha256=sha(encoded(manifest)), target_sha256=snapshot['_target_sha'],
                changed_bytes=changed, declared_sections=len(manifest['sections']), complete_diff_coverage=True,
                inverse_restores_parent=True, production_approval=False, native_execution=False)
