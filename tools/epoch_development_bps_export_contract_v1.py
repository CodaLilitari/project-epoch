"""Export one immutable accepted development snapshot; authorize no new ROM writes.

The immediate guarded receipt and final binary are pinned, rather than replaying
historical builders. This explicitly separate export contract does not promote
diagnostic allocations or hooks into the production catalogs.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import re
import epoch_bps_v1 as bps

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-epoch-development-bps-export-intents-v1'
NAME = 'project-epoch-development-2026-10-20-v1.bps'
SOURCE = {'bytes': 4194304, 'sha256': '06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'}
TARGET = {'bytes': 8388608, 'sha256': 'd4b6915dc85ef2bc782583de4478f9ed61e07f68fb2dde58b9cced4350ba3117'}
RECEIPT = {'bytes': 42999, 'sha256': '6cd8051e1bc9c7be691fb5a3f770132dfe82fd562cd7abc51fad282f1fa473fd'}
METADATA = ('<patch><description>Project Epoch 2026-10-20 v1. DEVELOPMENT SNAPSHOT; '
            'NOT TRULY PLAYABLE. Use a separate copy and the supplied Mesen demo state.'
            '</description><source_sha256>' + SOURCE['sha256'] + '</source_sha256>'
            '<target_sha256>' + TARGET['sha256'] + '</target_sha256></patch>').encode()
_ACTIVE = None


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def pin(raw, expected, label):
    need(type(raw) is bytes and len(raw) == expected['bytes'] and sha(raw) == expected['sha256'],
         label + ' identity mismatch')


def output_path(relative):
    need(type(relative) is str and re.fullmatch(
        r'private/research/epoch_update_20261020/release/[A-Za-z0-9_-]+/' + re.escape(NAME), relative),
        'fresh private development release destination required')
    path = ROOT / relative
    need(path.resolve().is_relative_to((ROOT / 'private/research/epoch_update_20261020/release').resolve()),
         'output escapes release directory')
    for part in (path, *path.parents):
        need(not part.is_symlink() and not (part.exists() and getattr(part.stat(), 'st_file_attributes', 0) & 0x400),
             'aliased output refused')
    return path


def delta_census(source, target):
    """Cover every clean-source byte and the complete appended extent once."""
    runs = []
    position = changed = 0
    while position < len(source):
        if source[position] == target[position]:
            position += 1
            continue
        start = position
        while position < len(source) and source[position] != target[position]:
            position += 1
        changed += position - start
        runs.append({'start': start, 'bytes': position - start,
                     'before_sha256': sha(source[start:position]),
                     'after_sha256': sha(target[start:position])})
    return {'canonical_changed_bytes': changed, 'canonical_difference_runs': runs,
            'canonical_unchanged_bytes': len(source) - changed,
            'appended_bytes': len(target) - len(source),
            'appended_sha256': sha(target[len(source):]),
            'scope': 'Exact accepted binary export, not new per-span production approval.'}


@contextmanager
def source_snapshot(source, target, receipt_raw):
    global _ACTIVE
    need(_ACTIVE is None, 'nested export snapshot')
    pin(source, SOURCE, 'clean unheadered US Rev0 source')
    pin(target, TARGET, 'accepted development target')
    pin(receipt_raw, RECEIPT, 'immediate guarded build receipt')
    receipt = json.loads(receipt_raw)
    need(receipt['schema'] == 'project-epoch-private-pc07-menu-hp-color-build-v1' and
         receipt['emitted'] is True and receipt['target'] == TARGET, 'wrong target receipt')
    need(receipt['current_shared_intent']['status'] == 'metadata-valid' and
         receipt['current_shared_diff']['status'] == 'images-valid' and
         receipt['current_shared_diff']['complete_diff_coverage'] is True and
         receipt['current_shared_diff']['changed_bytes'] == 113, 'immediate guard receipt absent')
    need(receipt['production_approval'] is False and receipt['historical_builders_or_validators_executed'] is False,
         'diagnostic provenance differs')
    need(source[0xFFD5] == 0x31 and source[0xFFD7] == 0x0C, 'clean header')
    need(target[:0x10000] == target[0x400000:0x410000], 'accepted boot mirror')
    for header in (0xFFC0, 0x40FFC0):
        checksum = int.from_bytes(target[header + 30:header + 32], 'little')
        complement = int.from_bytes(target[header + 28:header + 30], 'little')
        need(target[header + 21] == 0x35 and target[header + 23] == 0x0D and
             checksum ^ complement == 65535 and checksum == sum(target) & 65535,
             'accepted ExHiROM header/checksum')
    _ACTIVE = {'source': source, 'target': target, 'receipt': receipt,
               'delta': delta_census(source, target)}
    try:
        yield _ACTIVE
    finally:
        _ACTIVE = None


def inputs():
    need(_ACTIVE is not None, 'pinned export snapshot required')
    return _ACTIVE


def template(output):
    output_path(output)
    return {'schema': SCHEMA, 'source': SOURCE, 'target': TARGET,
            'accepted_immediate_build_receipt': RECEIPT, 'output': output,
            'format': 'BPS1', 'metadata_sha256': sha(METADATA),
            'complete_image_delta': inputs()['delta'], 'new_ROM_mutations': False,
            'ROM_output': False, 'production_approval': False,
            'evidence_level': 'accepted-development-binary-export; native evidence separately bounded',
            'warning': 'DEVELOPMENT SNAPSHOT - NOT TRULY PLAYABLE'}


def validate_manifest(manifest):
    need(type(manifest) is dict and encoded(manifest) == encoded(template(manifest.get('output'))),
         'fixed development export manifest')
    return {'status': 'metadata-valid', 'schema': SCHEMA, 'manifest_sha256': sha(encoded(manifest)),
            'production_approval': False, 'new_ROM_mutations': False}


def audit_patch(manifest, source, target, patch):
    validate_manifest(manifest)
    snapshot = inputs()
    need(source == snapshot['source'] and target == snapshot['target'], 'snapshot bytes differ')
    restored, information = bps.apply(source, patch)
    need(restored == target and information['metadata'] == METADATA, 'complete patch application mismatch')
    # Independently undo all canonical difference runs, and discard only the
    # declared appended extent. This accounts for every changed image byte.
    inverse = bytearray(target[:len(source)])
    cursor = 0
    for run in manifest['complete_image_delta']['canonical_difference_runs']:
        a, b = run['start'], run['start'] + run['bytes']
        need(a >= cursor and source[cursor:a] == target[cursor:a], 'undeclared canonical diff')
        inverse[a:b] = source[a:b]
        cursor = b
    need(source[cursor:] == target[cursor:len(source)] and bytes(inverse) == source,
         'complete-diff inverse failed')
    return {'status': 'patch-valid', 'complete_diff_coverage': True,
            'whole_patch_applies_to_exact_target': True, 'source_inverse_exact': True,
            'source_crc_target_crc_patch_crc': 'passed', 'target': TARGET,
            'new_ROM_mutations': False, 'ROM_file_written': False,
            'historical_builders_or_validators_executed': False, 'production_approval': False}
