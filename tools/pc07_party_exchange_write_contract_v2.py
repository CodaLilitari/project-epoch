"""Unsealed private party-exchange composition; accepted receipts are data only.

One captured parent and the new exact source/component closure per operation.
No old builder, provider conversion, native validator or recursive hash chain.
Root must pin a complete reviewed recipe before either public API can admit it.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-epoch-private-party-exchange-intents-v2'
RECIPE_SCHEMA = 'project-epoch-private-party-exchange-recipe-v2'
RECIPE = dict(path='references/pc07_party_exchange_private_recipe_v2.json', bytes=12518,
              sha256='57796131ed61d5e0002ff2393f1e6d101aabaae63f715fb728b7786001cf72fa')
SIZE = 0x800000
SOURCE = dict(path='private/test_runs/pc07_schala_persistent_presentation_v1/diagnostic.sfc', bytes=SIZE,
              sha256='3539b4069eabf34023a1a2457d8a99b9db2f05d7dc15bb7dba940e2bf61d4183')
PARENT_BUILD = dict(path='private/test_runs/pc07_schala_persistent_presentation_v1/receipt.json', bytes=52897,
                    sha256='34374f84e9782f8098ea6c73fafb8c7616beeb60cf483c700b498a33be3d5e4c')
ALLOCATION = dict(path='private/research/pc07_save_preview_installation_design_20261014/installation_design_v1.json', bytes=43842,
                  sha256='bef42505563df50e68810f3396119face4a3ea9f5ba7ea554bbf95789f991b5e')
SCAFFOLD_SHA = '26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93'
FILL = dict(start=0x410000, end=0x7E0000, fill=255)
BOOT_SIZE, MIRROR = 0x10000, 0x400000
HEADERS = (('checksum-primary', 0xFFDC), ('checksum-boot-mirror', 0x40FFDC))
COMPONENTS = {
    'party-menu': (0x470000, 0x474000, None),
    'party-field': (0x474000, 0x475000, None),
    'party-writer': (0x475000, 0x476000, 612),
    'party-loader': (0x476000, 0x477000, 687),
}
KNOWN_HOOKS = {
    'normal-save-writer-call': (0x2CF51, '22003144', '22005047', 'party-writer'),
    'load-whole-success-branch': (0x2E657, '5c003444eaea', '5c006047eaea', 'party-loader'),
}
INHERITED_ADDITIONS = (
    ('shadow-wrapper', 0x443000, 173), ('round8-core', 0x450000, 0x4A26), ('sigma-tables', 0x460000, 0x4000),
    ('native-sidecar-writer', 0x443100, 570), ('load-preflight-suffix', 0x442032, 58), ('native-sidecar-loader', 0x443400, 671))
CENSUS_COUNT, PRESENTATION_ALLOCATIONS = 46, 7
GUARD_INTENT = 'validate_pc07_party_exchange_v2_manifest'
GUARD_DIFF = 'audit_pc07_party_exchange_v2_images'
_ACTIVE = None


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
def exact(a, b, why): need(encoded(a) == encoded(b), why)


def keys(value, expected, why):
    need(type(value) is dict and set(value) == set(expected), why)


def path(relative):
    need(type(relative) is str and '\\' not in relative and ':' not in relative, 'canonical relative path required')
    parts = relative.split('/')
    need(parts and all(p and p not in ('.', '..') for p in parts), 'path traversal refused')
    target = ROOT.joinpath(*parts)
    for p in (target, *target.parents):
        if p.exists() or p.is_symlink():
            info = p.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400, 'aliased path refused')
    need(target.resolve().is_relative_to(ROOT.resolve()), 'path outside project')
    return target


def pin(row):
    keys(row, ('path', 'bytes', 'sha256'), 'exact file pin schema')
    need(type(row['bytes']) is int and row['bytes'] > 0 and type(row['sha256']) is str
         and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'invalid file pin')
    path(row['path'])
    return row


def read_pin(row):
    pin(row)
    p = path(row['path'])
    need(p.is_file() and p.stat().st_size == row['bytes'], 'source extent drift: ' + row['path'])
    raw = p.read_bytes()
    need(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'source identity drift: ' + row['path'])
    return raw


def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_party_exchange_[A-Za-z0-9_-]+/diagnostic\.sfc', relative),
         'fresh named private party-exchange destination required')
    return path(relative)


def span(start, size, why):
    need(type(start) is int and type(size) is int and 0 <= start < SIZE and 0 < size <= SIZE - start, why)
    return start, start + size


def overlaps(a, b):
    return max(a[0], b[0]) < min(a[1], b[1])


def hex_bytes(value, why):
    need(type(value) is str and len(value) > 0 and len(value) % 2 == 0 and re.fullmatch('[0-9a-f]+', value), why)
    return bytes.fromhex(value)


def occupied_from_receipts(parent, allocation):
    need(parent.get('emitted') is True and parent.get('target_sha256') == SOURCE['sha256'], 'accepted parent target binding')
    exact(parent['artifacts']['diagnostic.sfc'], SOURCE, 'accepted parent artifact binding')
    need(parent['current_shared_intent']['status'] == 'metadata-valid'
         and parent['current_shared_diff']['status'] == 'images-valid'
         and parent['current_shared_diff']['complete_diff_coverage'] is True
         and parent['current_shared_diff']['inverse_restores_parent'] is True, 'accepted parent guarded construction')
    provenance = parent['manifest']['provenance']
    exact(provenance['allocation_census'], ALLOCATION, 'accepted census pin')
    exact(provenance['inherited_expanded_fill'], FILL, 'accepted expanded-fill provenance')
    need(provenance['FF_alone_is_authority'] is False and provenance['new_allocations_disjoint'] is True
         and provenance['inherited_occupied_span_records'] == CENSUS_COUNT + len(INHERITED_ADDITIONS)
         and provenance['new_expanded_allocations'] == PRESENTATION_ALLOCATIONS, 'accepted occupied-census provenance')
    census = allocation['allocation']
    need(census['inert_scaffold_sha256'] == SCAFFOLD_SHA and len(census['inherited_occupied_spans']) == CENSUS_COUNT,
         'accepted inert scaffold/census provenance')
    rows, by_id = [], {}
    def add(prefix, row):
        start, end = span(row['file_start'], row['bytes'], 'occupied span bounds')
        need(type(row['id']) is str and row['id'], 'occupied ID')
        normalized = dict(id=prefix + row['id'], file_start=start, bytes=end - start)
        if normalized['id'] in by_id:
            # The accepted historical census repeats the two identical checksum
            # footprints. Preserve their occupied bytes once; conflicting reuse
            # of an identity remains a refusal.
            exact(normalized, by_id[normalized['id']], 'conflicting occupied identity')
            return
        by_id[normalized['id']] = normalized
        rows.append(normalized)
    for row in census['inherited_occupied_spans']: add('census:', row)
    for name, start, size in INHERITED_ADDITIONS: add('inherited:', dict(id=name, file_start=start, bytes=size))
    for row in parent['manifest']['sections']: add('parent:', row)
    need(len({r['id'] for r in rows}) == len(rows), 'duplicate occupied identity')
    expanded = [r for r in parent['manifest']['sections'] if r['kind'] in ('original-helper', 'retail-provider')]
    need(len(expanded) == PRESENTATION_ALLOCATIONS, 'all current presentation allocations included')
    return sorted(rows, key=lambda r: (r['file_start'], r['id']))


def validate_recipe(spec):
    keys(spec, ('schema', 'parent', 'accepted_parent_build', 'allocation_census', 'sources', 'evidence', 'components', 'hooks', 'labels'),
         'exact sealed recipe schema')
    need(spec['schema'] == RECIPE_SCHEMA, 'recipe schema')
    exact(spec['parent'], SOURCE, 'recipe parent identity')
    exact(spec['accepted_parent_build'], PARENT_BUILD, 'recipe parent receipt identity')
    exact(spec['allocation_census'], ALLOCATION, 'recipe census identity')
    for key in ('sources', 'evidence', 'components', 'hooks'):
        need(type(spec[key]) is list and spec[key], 'nonempty recipe list: ' + key)
    source_paths = []
    for row in spec['sources'] + spec['evidence']:
        pin(row)
        need(row['path'].startswith(('private/research/pc07_party_', 'tools/pc07_party_')), 'new operation source/evidence scope')
        source_paths.append(row['path'])
    need(len(set(source_paths)) == len(source_paths), 'duplicate recipe source/evidence path')
    pin(spec['labels'])
    need(spec['labels']['path'].startswith('private/research/pc07_party_'), 'new labels scope')
    need({r.get('id') for r in spec['components'] if type(r) is dict} == set(COMPONENTS)
         and len(spec['components']) == len(COMPONENTS), 'exact four named source-controlled components')
    for r in spec['components']:
        keys(r, ('id', 'file_start', 'bytes', 'payload', 'source_paths', 'evidence_paths', 'preimage_sha256'), 'component schema')
        start, limit, fixed_size = COMPONENTS[r['id']]
        span(r['file_start'], r['bytes'], 'component extent')
        need(r['file_start'] == start and start + r['bytes'] <= limit and (fixed_size is None or r['bytes'] == fixed_size), 'named component slot/extent')
        need(type(r['preimage_sha256']) is str and re.fullmatch('[0-9a-f]{64}', r['preimage_sha256']), 'component preimage pin')
        pin(r['payload'])
        need(r['payload']['bytes'] == r['bytes'] and r['payload']['path'].startswith('private/research/pc07_party_'), 'component payload pin/scope')
        for key, allowed in (('source_paths', {p['path'] for p in spec['sources']}), ('evidence_paths', {p['path'] for p in spec['evidence']})):
            need(type(r[key]) is list and r[key] and all(type(p) is str and p in allowed for p in r[key])
                 and len(set(r[key])) == len(r[key]), 'component source/evidence closure')
    hook_ids = set()
    for r in spec['hooks']:
        keys(r, ('id', 'owner', 'file_start', 'preimage_hex', 'replacement_hex', 'occupied_intersections'), 'hook schema')
        need(type(r['id']) is str and re.fullmatch('[a-z][a-z0-9-]+', r['id']) and r['id'] not in hook_ids, 'unique hook identity')
        hook_ids.add(r['id'])
        need(r['owner'] in COMPONENTS, 'hook owner')
        before, after = hex_bytes(r['preimage_hex'], 'hook preimage'), hex_bytes(r['replacement_hex'], 'hook replacement')
        start, end = span(r['file_start'], len(before), 'hook extent')
        need(len(before) == len(after) and before != after, 'whole changed hook extent')
        need(end <= MIRROR or MIRROR <= start < end <= MIRROR + BOOT_SIZE, 'hooks confined to canonical/mirrored code')
        need(type(r['occupied_intersections']) is list and all(type(x) is str for x in r['occupied_intersections'])
             and r['occupied_intersections'] == sorted(set(r['occupied_intersections'])), 'exact ordered hook intersections')
    need(set(KNOWN_HOOKS) <= hook_ids, 'mandatory normal-save/load hooks')
    for name, (start, before, after, owner) in KNOWN_HOOKS.items():
        r = next(r for r in spec['hooks'] if r['id'] == name)
        need((r['file_start'], r['preimage_hex'], r['replacement_hex'], r['owner']) == (start, before, after, owner), 'fixed persistence hook')
    need({'party-menu', 'party-field'} <= {r['owner'] for r in spec['hooks']}, 'completed menu and field hook recipe required')
    # Source-linked recipe is sealed by its full byte identity, not caller claims.
    return spec


def qualify_sections(source, spec, occupied, raw_by_path):
    need(type(source) is bytes and len(source) == SIZE, 'exact parent extent/type')
    need(source[:BOOT_SIZE] == source[MIRROR:MIRROR + BOOT_SIZE], 'accepted exact boot mirror')
    rows, payloads = [], {}
    for r in spec['components']:
        start, end = span(r['file_start'], r['bytes'], 'component extent')
        need(FILL['start'] <= start < end <= FILL['end'] and start >> 16 == (end - 1) >> 16, 'accepted expanded-fill bounds')
        need(not any(overlaps((start, end), (o['file_start'], o['file_start'] + o['bytes'])) for o in occupied), 'new allocation overlaps occupied census')
        need(source[start:end] == bytes([FILL['fill']]) * r['bytes'] and sha(source[start:end]) == r['preimage_sha256'], 'exact proven expanded preimage')
        payload = raw_by_path[r['payload']['path']]
        need(len(payload) == r['bytes'] and sha(payload) == r['payload']['sha256'], 'captured component payload drift')
        rows.append(dict(id=r['id'], file_start=start, bytes=r['bytes'], kind='original-expanded-component'))
        payloads[r['id']] = payload
    for r in spec['hooks']:
        before, payload = bytes.fromhex(r['preimage_hex']), bytes.fromhex(r['replacement_hex'])
        start, end = r['file_start'], r['file_start'] + len(before)
        need(source[start:end] == before, 'exact whole hook preimage')
        intersections = sorted(o['id'] for o in occupied if overlaps((start, end), (o['file_start'], o['file_start'] + o['bytes'])))
        exact(intersections, r['occupied_intersections'], 'explicit named hook supersession required')
        rows.append(dict(id=r['id'], file_start=start, bytes=len(before), kind='whole-instruction-hook'))
        payloads[r['id']] = payload
    for r in spec['hooks']:
        start = r['file_start']
        if start < BOOT_SIZE or MIRROR <= start < MIRROR + BOOT_SIZE:
            other_start = start + MIRROR if start < BOOT_SIZE else start - MIRROR
            matches = [h for h in spec['hooks'] if h['file_start'] == other_start]
            need(len(matches) == 1 and matches[0]['preimage_hex'] == r['preimage_hex']
                 and matches[0]['replacement_hex'] == r['replacement_hex'] and matches[0]['owner'] == r['owner'], 'exact boot hook mirror pair required')
    rows += [dict(id=name, file_start=start, bytes=4, kind='header') for name, start in HEADERS]
    rows.sort(key=lambda r: (r['file_start'], r['id']))
    need(len({r['id'] for r in rows}) == len(rows), 'unique complete section identities')
    cursor = 0
    for r in rows:
        start, end = span(r['file_start'], r['bytes'], 'section extent')
        need(start >= cursor, 'overlapping declared sections')
        cursor = end
    return rows, payloads


def qualify():
    need(RECIPE is not None, 'party-exchange recipe is unsealed; root must pin the completed exact recipe')
    rows, raws = {}, {}
    def add(row):
        pin(row)
        if row['path'] in rows:
            exact(rows[row['path']], row, 'conflicting direct pin')
        else:
            rows[row['path']], raws[row['path']] = dict(row), read_pin(row)
        return raws[row['path']]
    spec = validate_recipe(json.loads(add(RECIPE)))
    source = add(SOURCE)
    parent, allocation = json.loads(add(PARENT_BUILD)), json.loads(add(ALLOCATION))
    occupied = occupied_from_receipts(parent, allocation)
    for row in spec['sources'] + spec['evidence']:
        raw = add(row)
        if row in spec['evidence']:
            need(type(json.loads(raw)) is dict, 'new assembly/review evidence must be JSON objects; never executable')
    labels = json.loads(add(spec['labels']))
    need(type(labels) is dict, 'combined label data object')
    for r in spec['components']: add(r['payload'])
    sections, payloads = qualify_sections(source, spec, occupied, raws)
    return dict(source=source, sections=sections, payloads=payloads, occupied=occupied, labels=labels,
                source_rows=sorted(rows.values(), key=lambda r: r['path']), recipe=spec,
                provenance=dict(accepted_parent_build=PARENT_BUILD, exact_recipe=RECIPE, allocation_census=ALLOCATION,
                    inherited_expanded_fill=FILL, FF_alone_is_authority=False, occupied_span_records=len(occupied),
                    new_allocations_disjoint=True, accepted_receipts_read_as_data=True,
                    historical_builders_or_validators_executed=False, provider_conversion_calls=0))


@contextmanager
def source_snapshot():
    global _ACTIVE
    need(_ACTIVE is None, 'nested captured operation refused')
    captured = qualify()
    _ACTIVE = captured
    try:
        yield captured
    finally:
        _ACTIVE = None


def inputs(): return _ACTIVE if _ACTIVE is not None else qualify()


def derive(snapshot):
    if '_target' in snapshot:
        return snapshot['_target']
    source = snapshot['source']
    target = bytearray(source)
    for r in snapshot['sections']:
        if r['kind'] != 'header':
            target[r['file_start']:r['file_start'] + r['bytes']] = snapshot['payloads'][r['id']]
    checksum = sum(target) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, 'little') + checksum.to_bytes(2, 'little')
    for _, start in HEADERS: target[start:start + 4] = pair
    need(sum(target) & 0xFFFF == checksum and target[:BOOT_SIZE] == target[MIRROR:MIRROR + BOOT_SIZE], 'checksum/full boot mirror')
    # Complete-diff coverage below protects every byte, including inherited
    # spans not listed in old censuses. Allocations already exclude that census.
    snapshot['_target'], snapshot['_target_sha'] = bytes(target), sha(target)
    return snapshot['_target']


def template(snapshot, target, output):
    output_path(output)
    rows = []
    for r in snapshot['sections']:
        start, end = r['file_start'], r['file_start'] + r['bytes']
        before, after = snapshot['source'][start:end], target[start:end]
        rows.append(dict(r, preimage_hex=before.hex(), preimage_sha256=sha(before), sha256=sha(after),
                         changed_bytes=sum(a != b for a, b in zip(before, after)), owner='pc07-private-party-exchange-v2'))
    return dict(schema=SCHEMA, mode='private-bounded-party-exchange', source=SOURCE,
                target=dict(bytes=SIZE, sha256=snapshot['_target_sha']), output=output, sections=rows,
                provenance=snapshot['provenance'], production_approval=False, native_execution=False,
                metadata_policy='unchanged-full-grant-diagnostic-fixture', implemented_grants=False,
                mutable_metadata=False, arbitrary_active_position_support=False,
                evidence_level='fixed-private-source-composition-only')


def validate_manifest(manifest):
    need(type(manifest) is dict, 'exact private party-exchange manifest')
    snapshot = inputs()
    target = derive(snapshot)
    exact(manifest, template(snapshot, target, manifest.get('output')), 'fixed party-exchange manifest mismatch')
    return dict(status='metadata-valid', schema=SCHEMA, manifest_sha256=sha(encoded(manifest)), production_approval=False)


def audit_images(manifest, source, target):
    need(type(manifest) is dict, 'exact private party-exchange manifest')
    snapshot = inputs()
    expected = derive(snapshot)
    need(type(source) is bytes and source == snapshot['source'], 'exact accepted combined parent required')
    need(type(target) is bytes and target == expected, 'exact party-exchange target required')
    exact(manifest, template(snapshot, expected, manifest.get('output')), 'fixed party-exchange manifest mismatch')
    inverse, cursor, changed = bytearray(target), 0, 0
    for r in manifest['sections']:
        start, end = r['file_start'], r['file_start'] + r['bytes']
        need(start >= cursor and source[cursor:start] == target[cursor:start], 'unauthorized or overlapping complete diff')
        need(sha(source[start:end]) == r['preimage_sha256'] and sha(target[start:end]) == r['sha256'], 'exact span bytes')
        n = sum(a != b for a, b in zip(source[start:end], target[start:end]))
        need(n == r['changed_bytes'], 'span changed-byte count')
        inverse[start:end], cursor, changed = source[start:end], end, changed + n
    need(source[cursor:] == target[cursor:] and bytes(inverse) == source, 'complete difference/inverse coverage')
    return dict(status='images-valid', schema=SCHEMA, manifest_sha256=sha(encoded(manifest)), target_sha256=snapshot['_target_sha'],
                changed_bytes=changed, declared_sections=len(manifest['sections']), complete_diff_coverage=True,
                inverse_restores_parent=True, production_approval=False, native_execution=False)
