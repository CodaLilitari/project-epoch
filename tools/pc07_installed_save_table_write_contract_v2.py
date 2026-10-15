"""Fixed private ten-region save-table delta, bounded through pre-C2CF55.

This is a separate recipe, not production allocation approval. The unchanged v1
recipe supplies exact bytes and full-diff semantics. Its source-only manifest is
not silently promoted: v2 has its own schema and an explicit baseline requirement.
The image-writing builder must reproduce that baseline before emission.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ('private/research/pc07_installed_save_table_v1_20261013/contract_v1.py',
         10761, 'de152d66010b624ba14d498101466916a2508d60e4d885a845747b6aa3bce9e3')
GUARD = ('tools/validate_rom_write_intents.py', 43102,
         '9240a0ca431a9d567ebc0969027f552a5358674a5216e2c2114008518b2222c1')
ARCHIVE = ('private/research/pc07_installed_save_table_v2_20261014/archive/validate_rom_write_intents_pre_v2.py',
           42559, '78856072fc9f698853cb0c16e5294750d0390ca1b0181eb9428571427280fe01')
SCHEMA = 'project-epoch-private-installed-save-table-intents-v2'
OWNER = 'pc07-private-installed-save-table-v2'
SIZE = 0x800000
SOURCE_SHA = '144a374d0074734bab2f5f5d122ade9d5d825f77529094dbeb7c24ac67a9c264'
TARGET_SHA = 'e795c34f8680b45a99f86b657e23066957e4816a481a38099b20be10bfef8908'
GUARD_INTENT = 'validate_pc07_installed_save_table_manifest'
GUARD_DIFF = 'audit_pc07_installed_save_table_images'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_pin(path, size, digest):
    # Bootstrap without trusting an unverified private module or path alias.
    if (type(path) is not str or Path(path).is_absolute() or ':' in path
            or '\\' in path or any(p in ('', '.', '..') for p in path.split('/'))):
        raise ValueError('canonical project-relative source path required')
    import pc07_private_expanded_write_contract_v1 as field
    root = field._root(ROOT)
    p, info = field._inspect_path(root, Path(path).parts)
    import stat
    if info is None or not stat.S_ISREG(info.st_mode):
        raise ValueError('pinned regular source missing: ' + path)
    with p.open('rb') as stream:
        raw = stream.read(size + 1)
    if len(raw) != size or sha(raw) != digest:
        raise ValueError('pinned source drift: ' + path)
    return raw


def prior():
    raw = read_pin(*PRIOR)
    name = 'epoch_installed_save_table_immutable_v1'
    if name not in sys.modules:
        module = importlib.util.module_from_spec(importlib.util.spec_from_file_location(name, ROOT / PRIOR[0]))
        sys.modules[name] = module
        exec(compile(raw, str(ROOT / PRIOR[0]), 'exec'), module.__dict__)
    return sys.modules[name]


def source_rows():
    rows = {r['path']: r for r in prior().source_rows()}
    for p, n, h in (PRIOR, GUARD, ARCHIVE):
        read_pin(p, n, h)
        rows[p] = {'path': p, 'bytes': n, 'sha256': h}
    return sorted(rows.values(), key=lambda r: r['path'])


def verify_guard_extension():
    old, new = read_pin(*ARCHIVE), read_pin(*GUARD)
    start = new.index(b'def validate_pc07_installed_save_table_manifest(')
    end = new.index(b'def main() -> int:', start)
    if new[:start] + new[end:] != old:
        raise ValueError('shared guard must be a byte-preserving two-forwarder extension')
    return {'archived_sha256': sha(old), 'current_sha256': sha(new),
            'old_bytes_preserved': True, 'added_apis': [GUARD_INTENT, GUARD_DIFF]}


def recipe(canonical):
    return prior().recipe(canonical)


def expected():
    return prior()._expected()


def template(source, target, output):
    result = copy.deepcopy(prior()._template(source, target, output))
    result['schema'] = SCHEMA
    result['allocation']['id'] = OWNER
    for row in result['sections']:
        row['owner'] = OWNER
        if row['kind'] == 'named-private-expanded-table':
            row['id'] = OWNER
    result['baseline_admission'] = 'builder-must-reproduce-accepted-save-body-v1'
    result['evidence_level'] = 'guarded-private-save-table-diagnostic-only'
    result['observation_boundary'] = {
        'entry': 'C2CF51', 'exclusive_continuation': 'C2CF55',
        'ordinary_save_body_only': True, 'post_return_continuation_approved': False,
        'preview_adapted': False, 'extra_staging_is_free': False,
        'occupied_extra_staging_preimage_hex': '00abcebcbcba00363f00',
        'extra_staging_write_admitted_only_within_observation': True,
        'extra_staging_restoration_proved': False}
    return result


def validate_manifest(manifest):
    if type(manifest) is not dict:
        raise ValueError('fixed v2 manifest required')
    source_rows()
    verify_guard_extension()
    source, target = expected()
    prior().parent().prior.field._exact(manifest, template(source, target, manifest.get('output')), 'manifest-v2')
    return {'status': 'metadata-valid', 'schema': SCHEMA, 'production_approval': False,
            'manifest_sha256': sha(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())}


def audit_images(manifest, source, target):
    report = validate_manifest(manifest)
    # Never manufacture the legacy expectation from caller-supplied images.
    # Metadata remains fixed while the complete-image auditor rejects damage.
    expected_source, expected_target = expected()
    legacy = prior()._template(expected_source, expected_target, manifest['output'])
    fixed = prior().audit_images(legacy, source, target)
    if fixed['changed_bytes'] != 63 or fixed['declared_sections'] != 5:
        raise ValueError('exact inherited complete-diff invariant')
    return {**fixed, **report, 'status': 'images-valid',
            'native_execution': False, 'emission_admission': False,
            'baseline_reproduction_required_before_emission': True,
            'post_return_continuation_approved': False}


def build_manifest(source, target, output):
    result = template(source, target, output)
    audit_images(result, source, target)
    return result
