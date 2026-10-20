"""Read accepted placement metadata once; never import builders or read a ROM.

The conservative union retains superseded spans as occupied. FF preimages and
the current image binding are separate checks in the new private write guard.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = (
    ('private/research/pc07_save_preview_installation_design_20261014/installation_design_v1.json', 43842, 'bef42505563df50e68810f3396119face4a3ea9f5ba7ea554bbf95789f991b5e'),
    ('private/test_runs/pc07_schala_persistent_presentation_v1/receipt.json', 52897, '34374f84e9782f8098ea6c73fafb8c7616beeb60cf483c700b498a33be3d5e4c'),
    ('private/test_runs/pc07_party_exchange_v2/receipt.json', 46255, '4ce6b3fe99e82b29e07b1542c0048664597254c895d65678c86194fe18883bb4'),
    ('private/test_runs/pc07_worldmap_coda_v5_v1/receipt.json', 16669, '331f30de9e1e3ef6b3dffbc547e3e7e4e52525685b804c5e2eca941a5fa6a576'),
    ('private/test_runs/pc07_run_pose_v1/receipt.json', 4996, '3bbd059c6c213d33739b421c9d8c572ae4b279414868a6fc3a4005e458fcb8b1'),
)
PARENT_SHA = '00e3440c2927834554c7e3f872a5b995b76e53e1e6775ddd76abe9bac0b8f18f'
NEW = (('pc07-body-graphics-append', 0x4209E0, 0x420E00),
       ('pc07-body-assembly-append', 0x421398, 0x4214B0),
       ('pc07-battle-ko-helpers', 0x490000, 0x490100))


def need(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(row):
    raw = (ROOT / row['path']).read_bytes()
    need(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'metadata source drift: ' + row['path'])
    return raw


def derive():
    sources = [dict(path=p, bytes=n, sha256=h) for p, n, h in PINS]
    census, presentation, party, world, run = [json.loads(read_pin(p)) for p in sources]
    fill = dict(start=0x410000, end=0x7E0000, fill=255)
    for document in (presentation, party, world):
        provenance = document['manifest']['provenance']
        need(provenance['inherited_expanded_fill'] == fill and provenance['FF_alone_is_authority'] is False,
             'accepted expanded-fill provenance')
        need(document['emitted'] is True and document['current_shared_diff']['complete_diff_coverage'] is True,
             'accepted complete-diff receipt')
    need(run['emitted'] is True and run['target']['sha256'] == PARENT_SHA, 'current parent metadata binding')
    need(census['allocation']['inert_scaffold_sha256'] == '26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93',
         'accepted scaffold identity')
    old_rows = census['allocation']['inherited_occupied_spans']
    need(len(old_rows) == 46, 'original placement census extent')
    # Recover the six accepted additions as literal source data, never execute it.
    source_pin = next(p for p in party['sources'] if p['path'] == 'tools/pc07_party_exchange_write_contract_v2.py')
    tree = ast.parse(read_pin(source_pin))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'INHERITED_ADDITIONS' for t in n.targets)]
    need(len(values) == 1 and len(values[0]) == 6, 'six accepted additional placements')
    sources.append(source_pin)
    occupied = []

    def add(prefix, rows):
        for ordinal, row in enumerate(rows):
            start, size = row['file_start'], row['bytes']
            need(type(start) is int and type(size) is int and 0 <= start < start + size <= 0x800000,
                 'occupied span bounds')
            occupied.append(dict(id=prefix + ':' + str(ordinal) + ':' + row['id'], file_start=start,
                                 bytes=size, file_end_exclusive=start + size))

    add('original-census', old_rows)
    add('accepted-additions', [dict(id=n, file_start=s, bytes=b) for n, s, b in values[0]])
    for prefix, doc in (('presentation', presentation), ('party-v2', party), ('world-v5', world), ('run-v1', run)):
        add(prefix, doc['manifest']['sections'])
    proposed = []
    for name, start, end in NEW:
        need(fill['start'] <= start < end <= fill['end'], 'new span outside inherited expansion fill')
        overlaps = [r['id'] for r in occupied if start < r['file_end_exclusive'] and r['file_start'] < end]
        need(not overlaps, 'new allocation overlaps existing ownership: ' + str(overlaps))
        proposed.append(dict(id=name, file_start=start, bytes=end - start, file_end_exclusive=end,
                             overlapping_occupied_ids=overlaps))
    return dict(schema='epoch-private-battle-pose-allocation-census-v1', sources=sources,
                current_parent=dict(path='private/test_runs/pc07_run_pose_v1/diagnostic.sfc', bytes=0x800000, sha256=PARENT_SHA),
                inherited_expanded_fill=fill, inert_scaffold_sha256=census['allocation']['inert_scaffold_sha256'],
                occupied_spans=sorted(occupied, key=lambda r: (r['file_start'], r['id'])),
                new_allocations=proposed, new_allocations_disjoint=True, FF_alone_is_authority=False,
                evidence_level='accepted-placement-metadata-reuse-with-explicit-interval-comparison',
                ROM_read=False, ROM_written=False, historical_builders_or_validators_executed=False,
                production_approval=False,
                reproduction='python -B tools/build_pc07_battle_pose_allocation_census_v1.py <fresh-output.json>')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = derive()
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with args.output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps(dict(path=str(args.output), bytes=len(raw), sha256=sha(raw), occupied_records=len(result['occupied_spans']))))
