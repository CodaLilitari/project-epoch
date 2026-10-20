"""Private sparse casting-art derivative on the accepted stationary parent.

One current snapshot and immediate receipt; no historical builder execution.
Original 122 tiles/32 records and every caster/KO helper remain unchanged.
"""
from contextlib import contextmanager
from pathlib import Path
import json, re, struct, subprocess
from pc07_run_pose_write_contract_v1 import ROOT, SIZE, NPC_SPANS, need, sha, encoded, resolve, read_pin, tokens
import native_pc07_caster_pose_codec_v2 as codec

SCHEMA = 'project-epoch-private-pc07-caster-pose-refinement-intents-v1'
SOURCE = {'path': 'private/test_runs/pc07_caster_attack_v1/diagnostic.sfc', 'bytes': SIZE,
          'sha256': '9f678764d05f2f16e49c5a7cafe03ee6f192330322988918ff8bca2d1b2740f0'}
PARENT = {'path': 'private/test_runs/pc07_caster_attack_v1/receipt.json', 'bytes': 51852,
          'sha256': '5ec10796378555b32546d8ac89e264c10e2ba22a8338ab3ad27bf21c1d750712'}
ART = {'path': 'private/research/pc07_caster_pose_refinement_20261020/art_v1/pose_study_v1_indexed.json',
       'bytes': 24805, 'sha256': '4cd38a4ffacaee5afbccba08cc324ff91067813cb6ecd78d514e7d267905635b'}
CENSUS = {'path': 'private/research/pc07_caster_attack_20261020/engineering/allocation_census_v2.json',
          'bytes': 23090, 'sha256': 'cfbf38d1c2e3ba34a224c8246983dff535654d10a5b0b71ca8c1b962896ae6e4'}
OLD_ASM = {'path': 'asm/pc07_schala_tile_bank_v4.asm', 'bytes': 3380,
           'sha256': 'bdf23dcf547e31c6104ac68e605c3575a984ee06f4bac47d31037e927a9a15d3'}
NEW_ASM = {'path': 'asm/pc07_schala_tile_bank_v5.asm', 'bytes': 3539,
           'sha256': 'd9ddb0e618a6349c6fff7ce9990e79b85f8d9ecb6e14a53ddcd2a7d66017a73c'}
ASAR = {'path': 'private/tools/asar-1.91/asar.exe', 'bytes': 501248,
        'sha256': 'ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8'}
OLD_TILE_SHA = '4bb0a144a049812b505db058a01a42cb0d739ff261f84b698d4564c3b8d8d036'
GFX, ASSEMBLY, PRIMARY, TIMING, STRIDE = 0x420000, 0x421000, 0x424000, 0x425100, 0x404
ALLOCATIONS = (('pc07-caster-sparse-graphics', 0x423000, 0x4231C0),
               ('pc07-caster-pose-records-append', 0x421500, 0x421578),
               ('pc07-caster-sparse-tile-adapter-tail', 0x4130E2, 0x4130EC))
_ACTIVE = None


def identity(relative, raw):
    return {'path': relative, 'bytes': len(raw), 'sha256': sha(raw)}


def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_caster_pose_refinement_[A-Za-z0-9_-]+/diagnostic\.sfc', relative),
         'fresh private caster-pose output required')
    return resolve(relative)


def qualify_allocations(parent):
    census = json.loads(read_pin(CENSUS))
    need(census['schema'] == 'epoch-private-caster-attack-allocation-census-v1' and
         census['FF_alone_is_authority'] is False and census['new_allocations_disjoint'] is True,
         'accepted immediate allocation census')
    need(parent['manifest']['named_allocation_provenance']['accepted_census'] == CENSUS,
         'current receipt must bind accepted census')
    fill = census['inherited_expanded_fill']
    need(fill == {'start': 0x410000, 'end': 0x7E0000, 'fill': 255}, 'inherited scaffold fill provenance')
    occupied = list(census['occupied_spans'])
    for prefix, rows in (('caster-v1', parent['manifest']['sections']),
                         ('caster-reservation', parent['manifest']['named_allocation_provenance']['new_allocations'])):
        for index, row in enumerate(rows):
            start, size = row['file_start'], row['bytes']
            need(type(start) is int and type(size) is int and 0 <= start < start + size <= SIZE, 'occupied span bounds')
            occupied.append({'id': f'{prefix}:{index}:{row["id"]}', 'file_start': start,
                             'bytes': size, 'file_end_exclusive': start + size})
    need(len(occupied) == 166, '143 inherited plus20 current sections plus3 complete reservations')
    for name, start, end in ALLOCATIONS:
        need(fill['start'] <= start < end <= fill['end'], 'new expanded bounds')
        for old in occupied:
            need(old['file_end_exclusive'] == old['file_start'] + old['bytes'], 'occupied extent')
            need(max(start, old['file_start']) >= min(end, old['file_end_exclusive']), 'new allocation overlaps occupied data')
    return {'accepted_census': CENSUS, 'immediate_receipt': PARENT, 'inherited_expanded_fill': fill,
            'occupied_spans': sorted(occupied, key=lambda row: (row['file_start'], row['id'])),
            'occupied_spans_checked': 166,
            'new_allocations': [{'id': n, 'file_start': s, 'bytes': e-s, 'file_end_exclusive': e} for n, s, e in ALLOCATIONS],
            'all_disjoint': True, 'FF_alone_is_authority': False, 'production_approval': False}


def encode_art(source, doc):
    need(doc['schema'] == 'epoch-private-caster-pose-refinement-study-v1' and doc['canvas'] == [48, 48]
         and doc['native_origin'] == [16, 40] and doc['transparent_index'] == 0, 'pinned art geometry')
    need(len(doc['palette_rgb']) == 13 and all(type(row) is list and len(row) == 3 and
         all(type(v) is int and 0 <= v <= 255 for v in row) for row in doc['palette_rgb']), 'palette13')
    need([f['role'] for f in doc['frames']] == ['cast_release_front', 'cast_windup_up', 'cast_release_up'], 'fixed roles')
    candidates = [{'role': f['role'], 'rows': [[int(v, 16) for v in row] for row in f['pixel_rows_hex']],
                   'preferred_cover': f['cover_16x16_top_left']} for f in doc['frames']]
    oldgfx, oldasm = source[GFX:GFX+122*32], source[ASSEMBLY:ASSEMBLY+32*40]
    graphics, assembly, report = codec.append_frames(oldgfx, oldasm, candidates)
    need(len(graphics) == 448 and sha(graphics) == '7e7c0eb3b2b7b9f8059ec538fd713c947505bc31e4199f9a69653911a6210892',
         'deterministic14tile sparse component')
    need(len(assembly) == 1400 and sha(assembly) == 'cdeb1353e699a09ed61f16f90b767a89105376371af3f566b7b3db85c55aeb5a',
         'deterministic35frame assembly')
    need([r['frame_id'] for r in report] == [32, 33, 34], 'exact appended frame IDs')
    return graphics, assembly, {'frames': report, 'new_tiles': 14, 'new_tile_ids': list(range(384, 398)),
                               'total_owned_tiles': 136, 'assembly_frames': 35,
                               'old_tile_prefix_preserved': 122, 'old_frame_prefix_preserved': 32,
                               'native_binding_proved': False}


def expected_adapter(old):
    """Independent opcode splice of the frozen whole226byte adapter.

    Only the sparse range fence is inserted. Earlier qualification branches
    retain their exact logical targets by advancing ten bytes. The copy and
    original tails are byte-identical. No original opcode body is embedded.
    """
    need(type(old) is bytes and len(old) == 226 and sha(old) == OLD_TILE_SHA, 'whole frozen tile-adapter preimage')
    need(old[81:86] == bytes.fromhex('E0210FB00B'), 'old five-byte bound')
    prefix = bytearray(old[:81])
    widths = {0xA5: 2, 0xC9: 2, 0x08: 1, 0x48: 1, 0xDA: 1, 0x05: 2,
              0xD0: 2, 0xCF: 4, 0xAF: 4, 0xAE: 3, 0xBF: 4, 0xFA: 1}
    offset, branches = 0, []
    while offset < len(prefix):
        opcode = old[offset]
        need(opcode in widths, 'independent qualifier instruction grammar')
        if opcode == 0xD0:
            target = offset + 2 + int.from_bytes(old[offset+1:offset+2], 'little', signed=True)
            need(target == 96, 'all original qualification refusals retain original_pop')
            displacement = target + 10 - (offset + 2)
            need(-128 <= displacement <= 127, 'qualification branch range')
            prefix[offset+1] = displacement & 255
            branches.append(offset)
        offset += widths[opcode]
    need(offset == 81 and len(branches) == 10, 'complete qualifier prefix decoding')
    fence = bytes.fromhex('E0210F900AE000309010E0A131B00B')
    return bytes(prefix) + fence + old[86:]


def assemble_adapter(directory, source):
    directory = resolve(directory.relative_to(ROOT).as_posix())
    need(not directory.exists(), 'fresh component assembly directory')
    read_pin(ASAR)
    old_source, new_source = read_pin(OLD_ASM), read_pin(NEW_ASM)
    expected = expected_adapter(source[0x413000:0x4130E2])
    directory.mkdir(parents=True, exist_ok=False)
    wrapper = 'arch 65816\nnorom\norg $000000\nbase $413000\n' + new_source.decode('utf-8')
    asm, binary = directory/'Pc07SchalaTileBankV5.asm', directory/'Pc07SchalaTileBankV5.bin'
    asm.write_text(wrapper, encoding='utf-8', newline='\n')
    binary.write_bytes(b'')
    command = [str(resolve(ASAR['path'])), '--no-title-check', '--fix-checksum=off', str(asm), str(binary)]
    run = subprocess.run(command, cwd=directory, capture_output=True, timeout=30,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    (directory/'stdout.txt').write_bytes(run.stdout)
    (directory/'stderr.txt').write_bytes(run.stderr)
    need(run.returncode == 0, 'Asar adapter failed')
    data = binary.read_bytes()
    need(data == expected and len(data) == 236, 'independent opcode splice and Asar disagree')
    return data, {'assembler': ASAR, 'bytes': len(data), 'sha256': sha(data),
                  'wrapper_sha256': sha(wrapper.encode()), 'returncode': run.returncode,
                  'stdout_sha256': sha(run.stdout), 'stderr_sha256': sha(run.stderr),
                  'independent_opcode_equality': True, 'old_qualifier_targets_preserved': 10,
                  'old_copy_and_fallback_tails_unchanged': True,
                  'accepted_aligned_offsets_hex': [['0000', '0F20'], ['3000', '31A0']],
                  'source_inputs': [identity(OLD_ASM['path'], old_source), identity(NEW_ASM['path'], new_source)]}


def expected_frames(facing, selector, before):
    if facing == 0 and selector in (9, 0x31, 0x32):
        return bytes([33, 34] if selector == 0x31 else [34])
    if facing == 1 and selector in (9, 0x31, 0x32):
        return bytes([30, 32] if selector == 0x31 else [32])
    return before


def stream_audit(source, target):
    timing = source[TIMING:TIMING+STRIDE]
    need(timing == target[TIMING:TIMING+STRIDE], 'inherited animation timing changed')
    bindings = []
    for facing in range(4):
        start = PRIMARY + facing * STRIDE
        for selector in range(256):
            before = tokens(source[start:start+STRIDE], selector, 255)
            after = tokens(target[start:start+STRIDE], selector, 255)
            delays = tokens(timing, selector, 0)
            need(after == expected_frames(facing, selector, before), 'selector reachability ownership')
            need(len(after) == len(delays) and all(v < 35 for v in after), 'frame/timing shape')
            if before != after:
                bindings.append({'facing': facing, 'selector': selector, 'before': list(before), 'after': list(after), 'delays': list(delays)})
    need(len(bindings) == 6, 'exact six up/front selector bindings')
    return {'entrypoints_checked': 1024, 'changed_selectors': [9, 0x31, 0x32], 'changed_directional_entries': 6,
            'bindings': bindings, 'timing_unchanged': True, 'facing_selection_unchanged': True,
            'horizontal_cast_recoil_KO_and_movement_unchanged': True, 'native_execution': False}


def derive(source, graphics, assembly, adapter):
    need(type(source) is bytes and len(source) == SIZE, 'eight-MiB current source')
    need(source[:0x10000] == source[0x400000:0x410000], 'inherited boot mirror')
    target, sections = bytearray(source), []
    for name, start, end in ALLOCATIONS:
        need(source[start:end] == b'\xFF' * (end-start), 'exact allocated-fill preimage: ' + name)
    def put(name, start, data):
        need(type(data) is bytes and data and 0 <= start < start + len(data) <= SIZE, 'bounded payload')
        target[start:start+len(data)] = data
        sections.append((name, start, len(data)))
    need(assembly[:32*40] == source[ASSEMBLY:ASSEMBLY+32*40], 'accepted32frames changed')
    put('pc07-caster-sparse-graphics', 0x423000, graphics)
    put('pc07-caster-pose-records-append', 0x421500, assembly[32*40:])
    need(adapter == expected_adapter(source[0x413000:0x4130E2]), 'frozen adapter derivation')
    put('pc07-caster-sparse-tile-adapter', 0x413000, adapter)
    preimages = {(0, 9): bytes([0]), (0, 0x31): bytes([0, 0]), (0, 0x32): bytes([0]),
                 (1, 9): bytes([31]), (1, 0x31): bytes([30, 31]), (1, 0x32): bytes([31])}
    for (facing, selector), expected in preimages.items():
        start = PRIMARY + facing * STRIDE
        before = tokens(source[start:start+STRIDE], selector, 255)
        need(before == expected, 'fixed accepted selector preimage')
        put(f'pc07-primary-{selector:02x}-facing{facing}', start+selector*4, expected_frames(facing, selector, before)+b'\xFF')
    checksum = sum(target) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, 'little') + checksum.to_bytes(2, 'little')
    for name, start in (('checksum-primary', 0xFFDC), ('checksum-mirror', 0x40FFDC)):
        put(name, start, pair)
    need(sum(target) & 0xFFFF == checksum and target[:0x10000] == target[0x400000:0x410000], 'checksum/mirror')
    return bytes(target), sorted(sections, key=lambda row: row[1])


@contextmanager
def source_snapshot(assembly_directory):
    global _ACTIVE
    need(_ACTIVE is None, 'nested snapshot refused')
    source, parent = read_pin(SOURCE), json.loads(read_pin(PARENT))
    need(parent['emitted'] is True and parent['target'] == {k: SOURCE[k] for k in ('bytes', 'sha256')}
         and parent['manifest']['output'] == SOURCE['path'], 'exact immediate parent binding')
    need(parent['current_shared_intent']['status'] == 'metadata-valid' and parent['current_shared_diff']['status'] == 'images-valid'
         and parent['current_shared_diff']['complete_diff_coverage'] is True, 'accepted immediate construction')
    allocation = qualify_allocations(parent)
    graphics, assembly, art = encode_art(source, json.loads(read_pin(ART)))
    adapter, asm = assemble_adapter(assembly_directory, source)
    target, sections = derive(source, graphics, assembly, adapter)
    _ACTIVE = {'source': source, 'target': target, 'target_sha256': sha(target), 'sections': sections,
               'streams': stream_audit(source, target), 'allocation': allocation, 'art': art, 'assembly': asm}
    try:
        yield _ACTIVE
    finally:
        _ACTIVE = None


def inputs():
    need(_ACTIVE is not None, 'one current-operation snapshot required')
    return _ACTIVE


def template(output):
    output_path(output)
    snap = inputs()
    sections = [{'id': name, 'file_start': start, 'bytes': size,
                 'preimage_sha256': sha(snap['source'][start:start+size]), 'target_sha256': sha(snap['target'][start:start+size])}
                for name, start, size in snap['sections']]
    return {'schema': SCHEMA, 'source': SOURCE, 'accepted_parent_receipt': PARENT, 'art_input': ART, 'output': output,
            'target': {'bytes': SIZE, 'sha256': snap['target_sha256']}, 'sections': sections,
            'named_allocation_provenance': snap['allocation'], 'stream_audit': snap['streams'],
            'new_frames': [32, 33, 34], 'new_tile_ids': list(range(384, 398)),
            'original_frame_prefix_preserved': 32, 'original_tile_prefix_preserved': 122,
            'all_caster_and_KO_helpers_unchanged': True, 'field_adapter_sparse_fence': True,
            'native_execution': False, 'production_approval': False,
            'evidence_level': 'guarded-private-static-sparse-casting-pose-candidate'}


def validate_manifest(manifest):
    need(type(manifest) is dict and encoded(manifest) == encoded(template(manifest.get('output'))), 'fixed refinement manifest')
    return {'status': 'metadata-valid', 'schema': SCHEMA, 'manifest_sha256': sha(encoded(manifest)), 'production_approval': False}


def audit_images(manifest, source, target):
    validate_manifest(manifest)
    snap = inputs()
    need(type(source) is bytes and source == snap['source'], 'exact pinned current source')
    need(type(target) is bytes and target == snap['target'], 'exact fixed target')
    cursor = changed = 0
    inverse = bytearray(target)
    for row in manifest['sections']:
        start, end = row['file_start'], row['file_start'] + row['bytes']
        need(start >= cursor and source[cursor:start] == target[cursor:start], 'undeclared change or overlapping sections')
        changed += sum(a != b for a, b in zip(source[start:end], target[start:end]))
        inverse[start:end] = source[start:end]
        cursor = end
    need(source[cursor:] == target[cursor:] and bytes(inverse) == source, 'complete diff and inverse')
    for name, start, end in NPC_SPANS:
        need(source[start:end] == target[start:end], 'original NPC changed: ' + name)
    need(source[:0xFFDC] == target[:0xFFDC] and source[0xFFE0:0x400000] == target[0xFFE0:0x400000],
         'canonical gameplay bytes including unused assets must stay exact; only checksum header differs')
    need(source[GFX:GFX+122*32] == target[GFX:GFX+122*32] and
         source[ASSEMBLY:ASSEMBLY+32*40] == target[ASSEMBLY:ASSEMBLY+32*40], 'old art changed')
    need(source[0x490000:0x490380] == target[0x490000:0x490380], 'existing caster/KO helpers changed')
    for record in range(35):
        codec.decode_sparse(target[GFX:GFX+122*32], target[0x423000:0x4231C0],
                            target[ASSEMBLY+record*40:ASSEMBLY+(record+1)*40])
    return {'status': 'images-valid', 'schema': SCHEMA, 'declared_sections': len(manifest['sections']), 'changed_bytes': changed,
            'complete_diff_coverage': True, 'inverse_restores_parent': True, 'npc_protected_spans_unchanged': 13,
            'shared_palette_unchanged': True, 'original_frame_prefix_preserved': 32, 'original_tile_prefix_preserved': 122,
            'all_caster_and_KO_helpers_unchanged': True, 'canonical_effect_weapon_sound_tables_unchanged': True,
            'canonical_gameplay_bytes_including_unused_content_unchanged': True,
            'worldmap_unchanged': True, 'all35records_use_owned_tiles': True, 'native_execution': False, 'production_approval': False}
