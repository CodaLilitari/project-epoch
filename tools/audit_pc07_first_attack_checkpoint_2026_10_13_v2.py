"""Reproduce the frozen Attack review using one exact archived guard source.

Read-only. The v1 review, its result, source rows, trace and public checkpoint
remain byte-identical. Only source lookup and builder-source enumeration gain
the existing exact historical resolution; no native validator is replaced.
"""
from pathlib import Path
import hashlib
import importlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'private/research/pc07_first_attack_independent_review_20261013'
RESOLVER = ROOT / 'private/research/pc07_schala_presentation_20261013/accepted_attack_source_resolution_v1.py'
PINS = {
    'resolver': (RESOLVER, 'ef3be0bc8679445b0c1e8ecfc52e911f0665990700d0215ef26ce89783dffe2a'),
    'review': (PACKET / 'review_v2.py', '31463f43f479625208f82565da6cd6061b7c804fbb442c87b7d8345e1344c969'),
    'review_receipt': (PACKET / 'review_v2.json', '36cdac6bcac3d33baa906935c8a5348a9306841f203f8e1cafb08a2004e3bbb6'),
    'old_auditor': (ROOT / 'tools/audit_pc07_first_attack_checkpoint_2026_10_13.py', 'c014b074200ef7d63b0b647cafa5fbb4b186f91e53cac454164b1434618b7979'),
    'old_reference': (ROOT / 'references/pc07_first_attack_checkpoint_2026_10_13.json', 'ff1c4e88b60e4de35c63dcbfc126ad6c3f8dac27be9d93ac0ee253b6973989df'),
    'old_report': (ROOT / 'docs/pc07_first_attack_checkpoint_2026_10_13.md', 'e69dfc16b5bd068ff7cd7f41107a237240ba19200fa8bf602dbeda04e2711d77'),
    'builder_receipt': (ROOT / 'private/test_runs/pc07_first_attack_diagnostic_v1/build_receipt.json', '68c7847116774dd832247e79884d0effefab8da74d07d57b1c2e74c4dc4dad65'),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(path, digest=None):
    for p in (path, *path.parents):
        if p.is_symlink() or (p.exists() and getattr(p.stat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('aliased input: ' + str(path))
    raw = path.read_bytes()
    if digest is not None and sha(raw) != digest:
        raise ValueError('source drift: ' + str(path))
    return raw


def identity(path):
    raw = checked(path)
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_preflight():
    for path, digest in PINS.values():
        checked(path, digest)
    resolver = load('epoch_attack_public_v2_resolution', RESOLVER)
    resolution = resolver.audit()
    rows = resolver.frozen_rows()
    if len(rows) != 98 or resolution['new_resolution_count'] != 1:
        raise ValueError('fixed 98-row source resolution')
    guard = [r for r in rows if r['path'] == resolver.GUARD_PATH and r['sha256'] == resolver.GUARD_SHA]
    if len(guard) != 1:
        raise ValueError('one exact historical guard row')
    # This adversary tests the resolver, not an emulated CPU or a new trace.
    bad = dict(guard[0], sha256='0' * 64)
    try:
        resolver.resolve_source(bad)
    except ValueError:
        pass
    else:
        raise ValueError('foreign source hash was accepted')
    build = json.loads(checked(*PINS['builder_receipt']))['source_bundle']
    if len(build['sources']) != 22 or build['sha256'] != 'fa75ac54ca70d005a10949a41784709a6366d00be1af5e5a6c4045681a42b574':
        raise ValueError('fixed historical builder bundle')
    for item in build['sources']:
        matches = [r for r in rows if r['path'] == item['path'] and r['bytes'] == item['size'] and r['sha256'] == item['sha256']]
        paths = {resolver.resolve_source(r) for r in matches}
        if len(paths) != 1:
            raise ValueError('one exact builder source resolution: ' + item['path'])
    return resolver, resolution, rows, guard[0], build


def audit():
    resolver, resolution, rows, guard_row, historical_build = source_preflight()
    review = load('epoch_attack_public_v2_frozen_review', PINS['review'][0])
    original_checked = review.checked
    live_guard = ROOT / resolver.GUARD_PATH

    def resolved_checked(path, pin):
        if path == live_guard:
            if pin != guard_row:
                raise ValueError('undeclared live-guard resolution request')
            path = resolver.resolve_source(pin)
        return original_checked(path, pin)

    # Preload the exact archived guard before any frozen builder import. No
    # builder emitter or launcher is called; the full frozen review is reused.
    previous_guard = sys.modules.get('validate_rom_write_intents')
    load('validate_rom_write_intents', resolver.resolve_source(guard_row))
    sys.path.insert(0, str(ROOT / 'private/research/pc07_first_attack_collector_v2_20261013'))
    runner = importlib.import_module('run_attack_v2')
    builder = runner.image_builder
    original_bundle = builder.bundle

    def resolved_builder_bundle():
        if list(builder.SOURCES) != [r['path'] for r in historical_build['sources']]:
            raise ValueError('frozen builder source order changed')
        current = []
        for item in historical_build['sources']:
            match = next(r for r in rows if r['path'] == item['path'] and r['bytes'] == item['size'] and r['sha256'] == item['sha256'])
            raw = checked(resolver.resolve_source(match), item['sha256'])
            current.append({'path': item['path'], 'size': len(raw), 'sha256': sha(raw)})
        result = {'sha256': sha(json.dumps(current, sort_keys=True, separators=(',', ':')).encode()), 'sources': current}
        if result != historical_build:
            raise ValueError('reconstructed historical builder bundle differs')
        return result

    review.checked = resolved_checked
    builder.bundle = resolved_builder_bundle
    try:
        result = review.review()
    finally:
        review.checked = original_checked
        builder.bundle = original_bundle
        if previous_guard is None:
            sys.modules.pop('validate_rom_write_intents', None)
        else:
            sys.modules['validate_rom_write_intents'] = previous_guard
    saved = checked(*PINS['review_receipt'])
    if (json.dumps(result, indent=2, sort_keys=True) + '\n').encode() != saved:
        raise ValueError('full frozen review result changed')
    # Source resolution remains explicit in this additive receipt; no frozen
    # source rows, source-bundle hashes or earlier evidence files are rewritten.
    if resolver.audit() != resolution:
        raise ValueError('source resolution changed during review')
    return {
        'schema': 'project-epoch-pc07-first-attack-checkpoint-2026-10-13-v2',
        'status': 'full-frozen-review-reproduced-with-one-archived-source-resolution',
        'auditor': identity(Path(__file__).resolve()),
        'human_report': identity(ROOT / 'docs/pc07_first_attack_checkpoint_2026_10_13_v2.md'),
        'preserved_public_checkpoint': identity(PINS['old_reference'][0]),
        'preserved_public_report': identity(PINS['old_report'][0]),
        'preserved_v1_auditor': identity(PINS['old_auditor'][0]),
        'resolver': identity(RESOLVER),
        'frozen_review': identity(PINS['review'][0]),
        'frozen_review_receipt': identity(PINS['review_receipt'][0]),
        'source_resolution': resolution,
        'historical_builder_rows_checked': 22,
        'foreign_source_hash_refused': True,
        'full_frozen_validator_passed': result['full_frozen_validator_passed'],
        'full_review_receipt_byte_identical': True,
        'source_bundle_sha256': result['source_bundle_sha256'],
        'run': result['run'],
        'ordinary_attack_selector_family': result['independent_action_facts']['selector_family_observed'],
        'damage': result['independent_action_facts']['damage']['delta'],
        'hook_windows': result['hook_window_count'],
        'observed_pilot_prefix_rows': result['v1_v2_observed_prefix_comparison']['compared_rows'],
        'emulator_launched': False, 'image_emitted': False, 'frozen_files_modified': False,
        'scope': 'One already recorded Attack; preserve all limitations in the frozen review and v1 checkpoint. Historical v1 live-path command refuses after the separate guard extension.',
        'reproduction': 'python -B tools/audit_pc07_first_attack_checkpoint_2026_10_13_v2.py',
    }


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
