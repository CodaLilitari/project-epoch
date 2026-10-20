"""Private qualified startup-stat repair and portrait payload revision.

One immediate accepted image, one new named expansion, one exact instruction
hook. Existing full-menu portrait integration remains byte-identical. This is
not a balance, growth, save-format, item, vehicle or production authorization.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import re
import subprocess
from pc07_run_pose_write_contract_v1 import ROOT,SIZE,NPC_SPANS,need,sha,encoded,resolve,read_pin
import native_pc07_menu_stats_helper_v1 as helper
import native_pc07_status_portrait_codec_v1 as codec

SCHEMA='project-epoch-private-pc07-menu-stats-portrait-intents-v1'
SOURCE={'path':'private/test_runs/pc07_status_portrait_v2/diagnostic.sfc','bytes':SIZE,
        'sha256':'773e32de495acad1ac6d12fbe15101f45bc0240e65af47e4de19a318d54de128'}
PARENT={'path':'private/test_runs/pc07_status_portrait_v2/receipt.json','bytes':44194,
        'sha256':'884e7735b8244e5633acc55544e0b942e80a608cc90400ec8ff60ed1bb07dc7f'}
ASM={'path':'asm/pc07_menu_stats_v1.asm','bytes':923,
     'sha256':'52e644ca825f06dd3c6abd203e0af45b2e0930dda745e38d35549fdc5d53c84e'}
ASAR={'path':'private/tools/asar-1.91/asar.exe','bytes':501248,
      'sha256':'ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8'}
ART={'path': 'private/research/pc07_portrait_20261020/native_conversion_v6b/schala_v6b_indexed.json', 'bytes': 5468, 'sha256': '9d3bccbfb44271393975f3228b0329064e0125f9b3ac547a71713bae1036ea8e'}
ART_TILES_SHA='3c30e7d91423131c5d7789907dc725dab621250b6131f07f9f282373e841d825'
ART_PALETTE_SHA='b8ecadddcf15f8ed3612584a009c37c992ef7ddb59eac1560b870e169b4fc155'
SOURCE_QUALIFICATION={'path': 'private/research/pc07_menu_stats_20261020/engineering/source_qualification_v1.json', 'bytes': 6424, 'sha256': '12a54468542808be8130d558792f7658e6d0f498fad1146f208eec6411972c71'}
ALLOCATION=('pc07-menu-recompute-gate-v1',0x4A0400,0x4A0440)
HOOK_START=0x0299C1
HOOK_PREIMAGE=bytes.fromhex('A502C90700')
_ACTIVE=None

def identity(path,raw):
    return {'path':path,'bytes':len(raw),'sha256':sha(raw)}

def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_menu_stats_portrait_[A-Za-z0-9_-]+/diagnostic\.sfc',relative),
         'fresh private stats/portrait output required')
    return resolve(relative)

def allocations(parent):
    prior=parent['manifest']['named_allocation_provenance']
    need(prior['all_disjoint'] is True and prior['FF_alone_is_authority'] is False and
         prior['occupied_spans_checked']==180 and len(prior['occupied_spans'])==180,'accepted immediate allocation census')
    fill=prior['inherited_expanded_fill']
    need(fill=={'start':0x410000,'end':0x7E0000,'fill':255},'accepted scaffold fill provenance')
    occupied=list(prior['occupied_spans'])
    for prefix,rows in (('portrait-v2',parent['manifest']['sections']),('portrait-v2-reservation',prior['new_allocations'])):
        for i,row in enumerate(rows):
            start,size=row['file_start'],row['bytes']
            need(type(start) is int and type(size) is int and 0<=start<start+size<=SIZE,'occupied bounds')
            occupied.append({'id':f'{prefix}:{i}:{row["id"]}','file_start':start,'bytes':size,'file_end_exclusive':start+size})
    need(len(occupied)==195,'180 inherited plus11 sections plus4 complete reservations')
    name,start,end=ALLOCATION
    need(fill['start']<=start<end<=fill['end'],'new allocation inside inherited scaffold')
    for old in occupied:
        need(old['file_end_exclusive']==old['file_start']+old['bytes'],'occupied full extent')
        need(max(start,old['file_start'])>=min(end,old['file_end_exclusive']),'new allocation overlaps occupied source')
    return {'immediate_receipt':PARENT,'inherited_expanded_fill':fill,'occupied_spans':sorted(occupied,key=lambda x:(x['file_start'],x['id'])),
            'occupied_spans_checked':195,'all_disjoint':True,'FF_alone_is_authority':False,
            'new_allocations':[{'id':name,'file_start':start,'bytes':end-start,'file_end_exclusive':end}],
            'replaced_owned_payloads':[{'id':'pc07-status-portrait-36tiles','file_start':0x4A1000,'bytes':0x480},
                                       {'id':'pc07-status-portrait-16color-palette','file_start':0x4A1480,'bytes':0x20}],
            'production_approval':False}

def assemble(directory,source):
    directory=resolve(directory.relative_to(ROOT).as_posix())
    need(not directory.exists(),'fresh assembly output')
    read_pin(ASAR)
    item=helper.encode(source.decode('utf-8'))
    wrapper='arch 65816\nnorom\norg $000000\nbase $4A0400\n'+item['source']
    directory.mkdir(parents=True,exist_ok=False)
    asm,binary=directory/'gate.asm',directory/'gate.bin'
    asm.write_text(wrapper,encoding='utf-8',newline='\n'); binary.write_bytes(b'')
    command=[str(resolve(ASAR['path'])),'--no-title-check','--fix-checksum=off',str(asm),str(binary)]
    run=subprocess.run(command,cwd=directory,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (directory/'stdout.txt').write_bytes(run.stdout); (directory/'stderr.txt').write_bytes(run.stderr)
    need(run.returncode==0,'Asar gate assembly failed')
    need(binary.read_bytes()==item['data'],'independent gate encoding mismatch')
    return item,{'assembler':ASAR,'source':ASM,'bytes':len(item['data']),'sha256':sha(item['data']),
                 'independent_opcode_equality':True,'returncode':run.returncode}

def derive(source,gate,graphics,palette):
    need(type(source) is bytes and len(source)==SIZE,'eight-MiB source')
    need(source[:0x10000]==source[0x400000:0x410000],'accepted boot mirror')
    _,start,end=ALLOCATION
    need(source[start:end]==b'\xFF'*(end-start),'exact named expanded fill preimage')
    need(source[HOOK_START:HOOK_START+5]==HOOK_PREIMAGE,'exact loop comparison preimage')
    need(len(graphics)==0x480 and len(palette)==0x20,'unchanged native portrait geometry')
    target,spans=bytearray(source),[]
    def put(name,start,data):
        need(type(data) is bytes and data,'nonempty bytes')
        target[start:start+len(data)]=data; spans.append((name,start,len(data)))
    put('menu-recompute-gate-hook',HOOK_START,bytes.fromhex('2200044AEA'))
    put(ALLOCATION[0],start,gate)
    put('pc07-status-portrait-36tiles-revision',0x4A1000,graphics)
    put('pc07-status-portrait-palette-revision',0x4A1480,palette)
    checksum=sum(target)&0xFFFF
    pair=(checksum^0xFFFF).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    put('checksum-primary',0xFFDC,pair); put('checksum-mirror',0x40FFDC,pair)
    need(sum(target)&0xFFFF==checksum and target[:0x10000]==target[0x400000:0x410000],'checksum and mirror')
    return bytes(target),sorted(spans,key=lambda x:x[1])

@contextmanager
def source_snapshot(assembly_directory):
    global _ACTIVE
    need(_ACTIVE is None,'nested snapshot refused')
    need(type(ART) is dict and type(SOURCE_QUALIFICATION) is dict and isinstance(ART_TILES_SHA,str) and isinstance(ART_PALETTE_SHA,str),
         'unsealed reviewed art or source qualification')
    source,parent=read_pin(SOURCE),json.loads(read_pin(PARENT))
    need(parent['emitted'] is True and parent['target']=={k:SOURCE[k] for k in ('bytes','sha256')} and
         parent['manifest']['output']==SOURCE['path'],'exact immediate emitted parent')
    need(parent['current_shared_intent']['status']=='metadata-valid' and parent['current_shared_diff']['status']=='images-valid' and
         parent['current_shared_diff']['complete_diff_coverage'] is True,'accepted parent complete guard')
    proof=json.loads(read_pin(SOURCE_QUALIFICATION))
    need(proof['source']==SOURCE and proof['schema']=='epoch-private-menu-stats-source-qualification-v1' and
         proof['all_qualification_checks_passed'] is True,'source-owned qualification')
    for row in proof['current_rom_spans']:
        need(sha(source[row['file_start']:row['file_end_exclusive']])==row['sha256'],'qualified current span drift')
    allocation=allocations(parent)
    graphics,palette=codec.encode(json.loads(read_pin(ART)))
    need(sha(graphics)==ART_TILES_SHA and sha(palette)==ART_PALETTE_SHA,'reviewed present art bytes')
    gate,assembly=assemble(assembly_directory,read_pin(ASM))
    target,sections=derive(source,gate['data'],graphics,palette)
    _ACTIVE={'source':source,'target':target,'sections':sections,'allocation':allocation,'assembly':assembly,'gate':gate}
    try: yield _ACTIVE
    finally: _ACTIVE=None

def inputs():
    need(_ACTIVE is not None,'single current-operation snapshot required')
    return _ACTIVE

def template(output):
    output_path(output); snap=inputs()
    sections=[{'id':name,'file_start':start,'bytes':size,'preimage_sha256':sha(snap['source'][start:start+size]),
               'target_sha256':sha(snap['target'][start:start+size])} for name,start,size in snap['sections']]
    return {'schema':SCHEMA,'source':SOURCE,'accepted_parent_receipt':PARENT,'output':output,
            'target':{'bytes':SIZE,'sha256':sha(snap['target'])},'sections':sections,'named_allocation_provenance':snap['allocation'],
            'source_qualification':SOURCE_QUALIFICATION,'assembly_input':ASM,'art_input':ART,
            'loop_gate':{'counter_dp':2,'counter':7,'live_identity_address':0x7E2830,'live_identity':7,
                         'qualified_result':'original A/P except C=0; one additional canonical iteration',
                         'other_results':'exact original LDA dp02 / CMP #0007 semantics'},
            'original_recompute_body_unchanged':True,'balance_growth_equipment_and_save_data_unchanged':True,
            'portrait_code_destinations_geometry_and_timing_unchanged':True,'per_redraw_portrait_dma_bytes':0,
            'native_execution':False,'production_approval':False,'evidence_level':'guarded-private-static-menu-stats-and-portrait-candidate'}

def validate_manifest(manifest):
    need(type(manifest) is dict and encoded(manifest)==encoded(template(manifest.get('output'))),'fixed stats/portrait manifest')
    return {'status':'metadata-valid','schema':SCHEMA,'manifest_sha256':sha(encoded(manifest)),'production_approval':False}

def audit_images(manifest,source,target):
    validate_manifest(manifest); snap=inputs()
    need(type(source) is bytes and source==snap['source'],'exact immediate source')
    need(type(target) is bytes and target==snap['target'],'exact fixed derivative')
    cursor=changed=0; inverse=bytearray(target)
    for row in manifest['sections']:
        start,end=row['file_start'],row['file_start']+row['bytes']
        need(start>=cursor and source[cursor:start]==target[cursor:start],'undeclared change or overlap')
        changed+=sum(a!=b for a,b in zip(source[start:end],target[start:end]))
        inverse[start:end]=source[start:end]; cursor=end
    need(source[cursor:]==target[cursor:] and bytes(inverse)==source,'complete-diff inverse')
    canonical=bytearray(target[:0x400000])
    for start,size in ((0xFFDC,4),(HOOK_START,5)): canonical[start:start+size]=source[start:start+size]
    need(bytes(canonical)==source[:0x400000],'canonical outside exact hook/header changed')
    for name,start,end in NPC_SPANS: need(source[start:end]==target[start:end],'NPC changed: '+name)
    for name,start,end in (('previous helpers',0x410000,0x4A0400),('post-helper gap',0x4A0440,0x4A1000),
                           ('name and other expanded content',0x4A14A0,SIZE)):
        need(source[start:end]==target[start:end],name+' changed')
    need(source[0x0299B2:HOOK_START]==target[0x0299B2:HOOK_START] and source[0x0299C6:0x0299CA]==target[0x0299C6:0x0299CA],
         'canonical loop body/branch/exit unchanged')
    return {'status':'images-valid','schema':SCHEMA,'declared_sections':len(manifest['sections']),'changed_bytes':changed,
            'complete_diff_coverage':True,'inverse_restores_parent':True,'canonical_instruction_hook_bytes':5,
            'canonical_game_data_including_unused_unchanged':True,'npc_protected_spans_unchanged':13,
            'original_seven_portraits_and_palettes_unchanged':True,'all_previous_expanded_code_unchanged':True,
            'portrait_integration_and_preload_timing_unchanged':True,'worldmap_and_epoch_consumers_unchanged':True,
            'balance_growth_equipment_save_inputs_unchanged':True,'native_execution':False,'production_approval':False}
