"""Private, status-only full portrait derivative of one current image.

Canonical game data is immutable. Only two exact instruction spans redirect;
new graphics, palette and helpers occupy separately named expanded allocations.
Immediate-parent receipt reuse avoids replaying historical construction chains.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import re
import subprocess
from pc07_run_pose_write_contract_v1 import ROOT, SIZE, NPC_SPANS, need, sha, encoded, resolve, read_pin
import native_pc07_status_portrait_codec_v1 as codec
import native_pc07_status_portrait_helpers_v1 as helpers

SCHEMA = 'project-epoch-private-pc07-status-portrait-intents-v1'
SOURCE = {'path': 'private/test_runs/pc07_caster_pose_refinement_v1/diagnostic.sfc', 'bytes': SIZE,
          'sha256': '17b156701321ec11b5ed115dff0964665160bc99a857641d42078a7d73e3cb3e'}
PARENT = {'path': 'private/test_runs/pc07_caster_pose_refinement_v1/receipt.json', 'bytes': 44773,
          'sha256': '63be8e0ea1881f231a1d26402382a6a39fba2dc3982e59c296fe84111f2a2e97'}
ART = {'path':'private/research/pc07_portrait_20261020/native_conversion_v2/reserved_purple_green13_indexed.json',
       'bytes':5134,'sha256':'3bb3c9f171efb6183616c0f758ca1a26314ed1c359e53d710be2beae8284f6ef'}
NATIVE_CONTEXT = {'path':'private/research/pc07_portrait_20261020/engineering/parent_status_context_qualified_v1.json',
                  'bytes':3540,'sha256':'a265732610847cda8dac6c82a0ea18b81f3f553165aa3319090ea08afa9ef8c7'}
NAME_CONTEXT = {'path':'private/research/pc07_portrait_20261020/engineering/parent_status_name_cells_v1.json',
                'bytes':8150,'sha256':'7e978cc5b4e7c3a66e34f03e59357278d078c37ea4ddda618c0ae31fd471ca32'}
ASM = {'path':'asm/pc07_status_portrait_v1.asm','bytes':4444,
       'sha256':'ccb6a83dd48cb7f9951bd1865478d9dfd6180602b8dcdb4c605e0ab6270d0a2b'}
ART_TILES_SHA = '6fc2c5a877c815278a4226570c9959cdc34c3d30238eb8ea8abca56f626bf0a0'
ART_PALETTE_SHA = 'e14f1bedeec81585ea189a8b453ccf1a8f9d143d969b2c731bc5c46749b597eb'
FIXED_NAME = bytes.fromhex('B2BCC1BAC5BA')
ASAR = {'path': 'private/tools/asar-1.91/asar.exe', 'bytes': 501248,
        'sha256': 'ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8'}
ALLOCATIONS = (('pc07-status-portrait-helpers', 0x4A0000, 0x4A0300),
               ('pc07-status-portrait-36tiles', 0x4A1000, 0x4A1480),
               ('pc07-status-portrait-16color-palette', 0x4A1480, 0x4A14A0),
               ('pc07-status-schala-fixed-name', 0x4A14A0, 0x4A14A6))
HOOKS = (('status-portrait-tile-hook', 0x02EC3E, bytes.fromhex('BF70CEFF'), 0x4A0000),
         ('status-portrait-palette-hook', 0x02EC8B, bytes.fromhex('547EFFEE150D'), 0x4A0200))
_ACTIVE = None


def identity(relative, raw):
    return {'path': relative, 'bytes': len(raw), 'sha256': sha(raw)}


def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_status_portrait_[A-Za-z0-9_-]+/diagnostic\.sfc', relative),
         'fresh private status-portrait output required')
    return resolve(relative)


def qualify_allocations(parent):
    prior = parent['manifest']['named_allocation_provenance']
    need(prior['all_disjoint'] is True and prior['FF_alone_is_authority'] is False and
         prior['occupied_spans_checked'] == 166 and len(prior['occupied_spans']) == 166,
         'accepted immediate allocation census')
    fill = prior['inherited_expanded_fill']
    need(fill == {'start': 0x410000, 'end': 0x7E0000, 'fill': 255}, 'accepted scaffold fill provenance')
    occupied = list(prior['occupied_spans'])
    for prefix, rows in (('pose-refinement', parent['manifest']['sections']),
                         ('pose-reservation', prior['new_allocations'])):
        for index, row in enumerate(rows):
            start, size = row['file_start'], row['bytes']
            need(type(start) is int and type(size) is int and 0 <= start < start+size <= SIZE, 'occupied bounds')
            occupied.append({'id': f'{prefix}:{index}:{row["id"]}', 'file_start': start, 'bytes': size,
                             'file_end_exclusive': start+size})
    need(len(occupied) == 180, '166 inherited plus11 current sections plus3 complete reservations')
    for name, start, end in ALLOCATIONS:
        need(fill['start'] <= start < end <= fill['end'], 'new allocation outside inherited expansion')
        for old in occupied:
            need(old['file_end_exclusive'] == old['file_start']+old['bytes'], 'complete occupied extent')
            need(max(start,old['file_start']) >= min(end,old['file_end_exclusive']), 'new allocation overlaps occupied data')
    return {'immediate_receipt': PARENT, 'inherited_expanded_fill': fill,
            'occupied_spans': sorted(occupied,key=lambda row:(row['file_start'],row['id'])),
            'occupied_spans_checked': 180, 'all_disjoint': True, 'FF_alone_is_authority': False,
            'new_allocations': [{'id':n,'file_start':s,'bytes':e-s,'file_end_exclusive':e} for n,s,e in ALLOCATIONS],
            'production_approval': False}


def assemble_helpers(directory, source_bytes):
    directory = resolve(directory.relative_to(ROOT).as_posix())
    need(not directory.exists(), 'fresh assembly directory')
    read_pin(ASAR)
    components = helpers.encode(source_bytes.decode('utf-8'))
    directory.mkdir(parents=True, exist_ok=False)
    results = {}
    for name, row in components.items():
        wrapper = f'arch 65816\nnorom\norg $000000\nbase ${row["cpu_start"]:06X}\n' + row['source']
        asm, binary = directory/(name+'.asm'), directory/(name+'.bin')
        asm.write_text(wrapper,encoding='utf-8',newline='\n')
        binary.write_bytes(b'')
        command = [str(resolve(ASAR['path'])),'--no-title-check','--fix-checksum=off',str(asm),str(binary)]
        run = subprocess.run(command,cwd=directory,capture_output=True,timeout=30,
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (directory/(name+'.stdout.txt')).write_bytes(run.stdout)
        (directory/(name+'.stderr.txt')).write_bytes(run.stderr)
        need(run.returncode == 0, 'Asar portrait helper failed')
        actual = binary.read_bytes()
        need(actual == row['data'], 'Asar and independent opcode encoder disagree')
        results[name] = {'cpu_start':row['cpu_start'],'bytes':len(actual),'sha256':sha(actual),
                         'wrapper_sha256':sha(wrapper.encode()),'returncode':run.returncode,
                         'stdout_sha256':sha(run.stdout),'stderr_sha256':sha(run.stderr)}
    return components, {'assembler':ASAR,'source':identity('asm/pc07_status_portrait_v1.asm',source_bytes),
                        'independent_opcode_equality':True,'components':results}


def derive(source, graphics, palette, components):
    need(type(source) is bytes and len(source) == SIZE, 'eight-MiB current source')
    need(len(graphics) == 0x480 and len(palette) == 0x20, 'full portrait payload size')
    need(source[:0x10000] == source[0x400000:0x410000], 'inherited boot mirror')
    target, sections = bytearray(source), []
    for name, start, end in ALLOCATIONS:
        need(source[start:end] == b'\xFF'*(end-start), 'named expansion exact fill preimage: '+name)
    def put(name,start,data):
        need(type(data) is bytes and data, 'nonempty fixed section')
        target[start:start+len(data)] = data
        sections.append((name,start,len(data)))
    for name,start,before,address in HOOKS:
        need(source[start:start+len(before)] == before, 'exact canonical instruction preimage: '+name)
        put(name,start,b'\x22'+address.to_bytes(3,'little')+b'\xEA'*(len(before)-4))
    for name,row in components.items():
        put(name,row['cpu_start'],row['data'])
    put('pc07-status-portrait-36tiles',0x4A1000,graphics)
    put('pc07-status-portrait-16color-palette',0x4A1480,palette)
    put('pc07-status-schala-fixed-name',0x4A14A0,FIXED_NAME)
    checksum = sum(target)&0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    for name,start in (('checksum-primary',0xFFDC),('checksum-mirror',0x40FFDC)):
        put(name,start,pair)
    need(sum(target)&0xFFFF == checksum and target[:0x10000] == target[0x400000:0x410000], 'checksum and boot mirror')
    return bytes(target), sorted(sections,key=lambda row:row[1])


@contextmanager
def source_snapshot(assembly_directory):
    global _ACTIVE
    need(_ACTIVE is None, 'nested snapshot refused')
    need(all(type(row) is dict for row in (ART,NATIVE_CONTEXT,NAME_CONTEXT,ASM)) and
         type(ART_TILES_SHA) is str and type(ART_PALETTE_SHA) is str,
         'portrait contract remains unsealed pending reviewed art and native context')
    source, parent = read_pin(SOURCE), json.loads(read_pin(PARENT))
    need(parent['emitted'] is True and parent['target'] == {k:SOURCE[k] for k in ('bytes','sha256')} and
         parent['manifest']['output'] == SOURCE['path'], 'exact immediate current parent')
    need(parent['current_shared_intent']['status'] == 'metadata-valid' and
         parent['current_shared_diff']['status'] == 'images-valid' and
         parent['current_shared_diff']['complete_diff_coverage'] is True, 'accepted parent guarded construction')
    allocation = qualify_allocations(parent)
    art, observed, names = json.loads(read_pin(ART)), json.loads(read_pin(NATIVE_CONTEXT)), json.loads(read_pin(NAME_CONTEXT))
    need(observed['schema'] == 'epoch-private-parent-status-context-qualified-v1' and
         observed['source'] == SOURCE and observed['all_eight_portraits_observed'] is True,
         'current native full-status contexts required')
    need(names['schema'] == 'epoch-private-parent-status-name-cells-v1' and names['source'] == SOURCE and
         names['all_three_positions_observed'] is True and names['both_highlight_states_observed'] is True,
         'current native visible-name layout required')
    graphics,palette = codec.encode(art)
    need(sha(graphics) == ART_TILES_SHA and sha(palette) == ART_PALETTE_SHA, 'reviewed native art bytes')
    components, assembly = assemble_helpers(assembly_directory,read_pin(ASM))
    target,sections = derive(source,graphics,palette,components)
    _ACTIVE = {'source':source,'target':target,'sections':sections,'allocation':allocation,'assembly':assembly,
               'art': {'source':ART,'tiles_sha256':sha(graphics),'palette_sha256':sha(palette),
                       'dimensions':[48,48],'tile_count':36,'palette_entries':16,
                       'native_encode_decode_roundtrip':True,'native_render_proved':False},
               'observed_context':NATIVE_CONTEXT,'name_context':NAME_CONTEXT}
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
    sections = [{'id':name,'file_start':start,'bytes':size,
                 'preimage_sha256':sha(snap['source'][start:start+size]),
                 'target_sha256':sha(snap['target'][start:start+size])} for name,start,size in snap['sections']]
    return {'schema':SCHEMA,'source':SOURCE,'accepted_parent_receipt':PARENT,'output':output,
            'target':{'bytes':SIZE,'sha256':sha(snap['target'])},'sections':sections,
            'named_allocation_provenance':snap['allocation'],'art_input':ART,'native_context_input':NATIVE_CONTEXT,
            'native_name_context_input':NAME_CONTEXT,'full_status_portrait_and_displayed_names':True,
            'name_cell_bases':[0x2FAC,0x2EC6,0x3046,0x31C6],'name_width':6,'dynamic_first_slot_ids':[0,7],
            'save_preview_unchanged':True,'name_work_buffer_and_vehicle_name_unchanged':True,
            'original_seven_portrait_assets_and_tables_unchanged':True,'epoch_naming_route_unchanged':True,
            'native_execution':False,'production_approval':False,
            'evidence_level':'guarded-private-static-status-portrait-candidate'}


def validate_manifest(manifest):
    need(type(manifest) is dict and encoded(manifest) == encoded(template(manifest.get('output'))), 'fixed status portrait manifest')
    return {'status':'metadata-valid','schema':SCHEMA,'manifest_sha256':sha(encoded(manifest)),'production_approval':False}


def audit_images(manifest,source,target):
    validate_manifest(manifest)
    snap = inputs()
    need(type(source) is bytes and source == snap['source'], 'exact pinned current image')
    need(type(target) is bytes and target == snap['target'], 'exact fixed derivative')
    cursor = changed = 0
    inverse = bytearray(target)
    for row in manifest['sections']:
        start,end = row['file_start'],row['file_start']+row['bytes']
        need(start >= cursor and source[cursor:start] == target[cursor:start], 'overlap or undeclared change')
        changed += sum(a != b for a,b in zip(source[start:end],target[start:end]))
        inverse[start:end] = source[start:end]
        cursor = end
    need(source[cursor:] == target[cursor:] and bytes(inverse) == source, 'complete diff and inverse')
    canonical = bytearray(target[:0x400000])
    for start,size in ((0xFFDC,4),(0x02EC3E,4),(0x02EC8B,6)):
        canonical[start:start+size] = source[start:start+size]
    need(bytes(canonical) == source[:0x400000], 'canonical bytes outside exact hooks and header changed')
    for name,start,end in NPC_SPANS:
        need(source[start:end] == target[start:end], 'original NPC changed: '+name)
    for name,start,end in (('seven full faces and palettes',0x3F0000,0x3F2060),
                           ('original portrait tables and Epoch palette',0x3FCE50,0x3FCE88),
                           ('Epoch name selector',0x02E44D,0x02E44F),
                           ('inherited save preview',0x02D1C1,0x02D1C5),
                           ('worldmap and battle helpers',0x410000,0x4A0000)):
        need(source[start:end] == target[start:end], name+' changed')
    codec.decode(target[0x4A1000:0x4A1480])
    return {'status':'images-valid','schema':SCHEMA,'declared_sections':len(manifest['sections']),
            'changed_bytes':changed,'complete_diff_coverage':True,'inverse_restores_parent':True,
            'canonical_instruction_hook_bytes':10,'canonical_game_data_including_unused_unchanged':True,
            'original_seven_portraits_palettes_and_tables_unchanged':True,'npc_protected_spans_unchanged':13,
            'all_previous_expanded_helpers_and_assets_unchanged':True,'worldmap_unchanged':True,
            'epoch_naming_unchanged':True,'save_preview_unchanged':True,
            'native_execution':False,'production_approval':False}
