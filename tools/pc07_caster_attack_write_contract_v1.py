"""Private stationary-caster Attack composition on the accepted battle parent.

Fixed source/art pins, five qualified consumers, one current snapshot and a
complete diff. Existing art0..29 and all NPC/vehicle data remain unchanged.
No canonical visual/weapon/sound table edits, action replacement, or old chain.
"""
from contextlib import contextmanager
from pathlib import Path
import json,re,subprocess
from pc07_run_pose_write_contract_v1 import ROOT,SIZE,NPC_SPANS,need,sha,encoded,resolve,read_pin,tokens
import native_pc07_caster_pose_codec_v1 as codec
import pc07_caster_attack_helper_encoding_v1 as helper_encoder

SCHEMA="project-epoch-private-pc07-caster-attack-intents-v1"
SEALED=True  # Five-helper interface reviewed; exact bytes independently executed and Asar-matched.
SOURCE={'path':'private/test_runs/pc07_battle_pose_v1/diagnostic.sfc','bytes':SIZE,
        'sha256':'7549c49c3fec255ea559e8b1e0420a7b6285d921948f9550308291270db470e5'}
PARENT={'path':'private/test_runs/pc07_battle_pose_v1/receipt.json','bytes':37601,
        'sha256':'4cc9afaaacffd89c2177fe6bd632c885f74ae88381943b2d774e0a00c86e1f69'}
ART={'path':'private/research/pc07_caster_attack_20261020/front_cast_v3/front_cast_v3_indexed.json','bytes':18670,
     'sha256':'b54908f7d26da5f96b165d04a71be60bb1c20594d9bb39bcd23462fe65bbd5d1'}
CENSUS={'path':'private/research/pc07_caster_attack_20261020/engineering/allocation_census_v2.json','bytes':23090,
        'sha256':'cfbf38d1c2e3ba34a224c8246983dff535654d10a5b0b71ca8c1b962896ae6e4'}
EFFECT_REVIEW={'path':'private/research/pc07_caster_attack_20261020/effect_inspection_v1/manifest_v1.json','bytes':2170,
               'sha256':'0daaf866cb69e19ddf939f74b90c8471bf38bcb979761d6eaf988e7f4970e1ab'}
ASAR={'path':'private/tools/asar-1.91/asar.exe','bytes':501248,
      'sha256':'ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8'}
GFX,ASSEMBLY,PRIMARY,TIMING,STRIDE=0x420000,0x421000,0x424000,0x425100,0x404
ALLOCATIONS=(('pc07-caster-front-graphics-append',0x420E00,0x420F40),
             ('pc07-caster-front-assembly-append',0x4214B0,0x421500),
             ('pc07-caster-attack-helpers',0x490100,0x490380))
# Original project helper identities; not extracted game-code payloads.
HELPERS=(
    ('Pc07CasterApproachV1',0x490100,85,'3c0c315ac9ad6adc0c6e92ad5ff6ee556dc7a62f3f3e2c0ac94659119aa3caf3'),
    ('Pc07CasterNormalV1',0x490180,111,'68f7349d1f14383409c6c9135d8a61ac3bc904b78e58b9dd0f24dd7a7875f3c9'),
    ('Pc07CasterPathV1',0x490200,111,'7bef0fac9fb20d70247cf5928e9028ae16382c7e5a71edc1df37e3248cb2ab3e'),
    ('Pc07CasterCriticalV1',0x490280,111,'65a70a21d195221b83eaf0ec3defea138d84296005d179b112838b6f144a90b2'),
    ('Pc07CasterSwingSoundV1',0x490300,103,'044af7bff2697ef4cba0daab3d823b737921d1ad293255c9c4120502ab32f51a'),
)
HOOKS=(('stationary-approach',0x14A44,'22550041',0x490100),
       ('caster-normal-selector',0x143C4,'22670041',0x490180),
       ('caster-path-selector',0x143F8,'22790041',0x490200),
       ('caster-critical-selector',0x1438B,'228B0041',0x490280),
       ('caster-launch-sound',0x161EF,'BF4C6DCD',0x490300))
_ACTIVE=None

def identity(relative,raw):return {'path':relative,'bytes':len(raw),'sha256':sha(raw)}
def output_path(relative):
    need(type(relative)is str and re.fullmatch(r'private/test_runs/pc07_caster_attack_[A-Za-z0-9_-]+/diagnostic\.sfc',relative),
         'fresh private caster-attack output required')
    return resolve(relative)

def qualify_allocations():
    census=json.loads(read_pin(CENSUS))
    need(census['schema']=='epoch-private-caster-attack-allocation-census-v1' and census['current_parent']==SOURCE
         and census['new_allocations_disjoint'] is True and census['FF_alone_is_authority'] is False
         and census['whole_previous_KO_reservation_preserved'] is True,'accepted current allocation provenance')
    fill=census['inherited_expanded_fill']
    need(fill=={'start':0x410000,'end':0x7E0000,'fill':255} and len(census['occupied_spans'])==143,'complete current occupied census')
    need([(r['id'],r['file_start'],r['file_end_exclusive'])for r in census['new_allocations']]==list(ALLOCATIONS),
         'exact three current allocations')
    for _,start,end in ALLOCATIONS:
        need(fill['start']<=start<end<=fill['end'],'expanded allocation bounds')
        for old in census['occupied_spans']:
            need(old['file_end_exclusive']==old['file_start']+old['bytes'],'occupied extent')
            need(max(start,old['file_start'])>=min(end,old['file_end_exclusive']),'new occupied overlap')
    return {'accepted_census':CENSUS,'inherited_expanded_fill':fill,'occupied_spans_checked':143,
            'new_allocations':[{'id':n,'file_start':s,'bytes':e-s,'file_end_exclusive':e}for n,s,e in ALLOCATIONS],
            'all_disjoint':True,'whole_previous_KO_reservation_preserved':True,'production_approval':False}

def qualify_effect_review():
    review=json.loads(read_pin(EFFECT_REVIEW))
    need(review['schema']=='epoch-private-effect-inspection-v1' and review['ROM_written'] is False
         and review['native_color_and_timing_verified'] is False,'bounded effect inspection evidence')
    return {'accepted_static_inspection':EFFECT_REVIEW,'selected_config_hex':'07 0B 1A 09 04',
            'published_fields_hex':['7E987A','7E987B','7E987E','7E9881','7E9884'],
            'existing_graphics_chunks_hex':['07','08','09','0A','0B','0C'],
            'frame_packet_cpu_hex':'D10D7A','decoder_source_cpu_hex':['CD1368','CD1488','CD1509'],
            'launch_sound_source':'Rooted Black Hole package command7A sound4D; same sound-ID namespace as selected7C reader.',
            'rooted_packages_hex':['04','10'],'unused_7D_hook_omitted':True,
            'canonical_graphics_tables_unchanged':True,'native_color_timing_audio_verified':False}

def encode_art(source,doc):
    need(doc['schema']=='epoch-private-front-cast-study-v3' and doc['canvas']==[48,48]
         and doc['native_origin']==[16,40] and doc['transparent_index']==0,'pinned front-art format')
    palette=doc['palette_rgb']
    need(len(palette)==13 and all(type(r)is list and len(r)==3 and all(type(v)is int and 0<=v<=255 for v in r)for r in palette),
         'pinned palette13')
    need([f['role']for f in doc['frames']]==['cast_windup_front','cast_release_front'],'exact accepted front roles')
    candidates=[{'role':f['role'],'rows':[[int(v,16)for v in row]for row in f['pixel_rows_hex']],
                 'preferred_cover':f['cover_16x16_top_left']}for f in doc['frames']]
    oldgfx,oldasm=source[GFX:GFX+112*32],source[ASSEMBLY:ASSEMBLY+30*40]
    gfx,assembly,report=codec.append_frames(oldgfx,oldasm,candidates)
    need(len(gfx)==122*32 and sha(gfx)=='5fa2ed36bfad202b477ed906dde615805e85924bfe8349808f5f5151b6ab1f80',
         'reviewed deterministic122tile component')
    need(len(assembly)==32*40 and sha(assembly)=='c434a9c67b24f6d49255a7f5663243469851f1631c35be2a032a2dfd30a74769',
         'reviewed deterministic32frame component')
    need([r['frame_id']for r in report]==[30,31],'append-only front frame IDs')
    return gfx,assembly,{'frames':report,'graphics_tiles':122,'assembly_frames':32,'old_frame_prefix_preserved':30,
                         'old_tile_prefix_preserved':112,'native_binding_proved':False}

def assemble_components(directory):
    directory=resolve(directory.relative_to(ROOT).as_posix());need(not directory.exists(),'fresh original assembly directory')
    read_pin(ASAR)
    asm_name,tile_name='asm/pc07_caster_attack_v1.asm','asm/pc07_schala_tile_bank_v4.asm'
    asmraw,tileraw=resolve(asm_name).read_bytes(),resolve(tile_name).read_bytes()
    source=asmraw.decode('utf-8');helpers=helper_encoder.encode(source)
    need(set(helpers)=={r[0]for r in HELPERS},'exact five qualified helpers; unused impact hook forbidden')
    items=[]
    for name,cpu,size,expected_sha in HELPERS:
        row=helpers[name]
        need(row['cpu_start']==cpu and len(row['data'])==size and sha(row['data'])==expected_sha,'fixed reviewed helper bytes')
        body=name+':'+source.split(name+':',1)[1].split(name+'End:',1)[0]+name+'End:\n'
        items.append((name,cpu,body,row['data']))
    items.append(('Pc07SchalaTileBankV4',0x413000,tileraw.decode('utf-8'),None))
    directory.mkdir(parents=True,exist_ok=False);components={};evidence=[]
    for name,cpu,body,expected in items:
        wrapper=f'arch 65816\nnorom\norg $000000\nbase ${cpu:06X}\n'+body
        asm,binary=directory/(name+'.asm'),directory/(name+'.bin')
        asm.write_text(wrapper,encoding='utf-8',newline='\n');binary.write_bytes(b'')
        command=[str(resolve(ASAR['path'])),'--no-title-check','--fix-checksum=off',str(asm),str(binary)]
        run=subprocess.run(command,cwd=directory,capture_output=True,timeout=30,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (directory/(name+'.stdout.txt')).write_bytes(run.stdout);(directory/(name+'.stderr.txt')).write_bytes(run.stderr)
        need(run.returncode==0,'Asar component failed: '+name)
        data=binary.read_bytes();need(0<len(data)<=256,'bounded original component')
        if expected is not None:need(data==expected,'independent opcode encoder/Asar mismatch')
        components[name]=data
        evidence.append({'name':name,'cpu_start':cpu,'bytes':len(data),'sha256':sha(data),'returncode':run.returncode,
                         'wrapper_sha256':sha(wrapper.encode()),'stdout_sha256':sha(run.stdout),'stderr_sha256':sha(run.stderr)})
    label_report={name:{'cpu_start':r['cpu_start'],'bytes':len(r['data']),'hex':r['data'].hex(),
                        'labels':{k:r['cpu_start']+v for k,v in r['labels'].items()},'instructions':r['instructions']}
                  for name,r in helpers.items()}
    return components,{'assembler':ASAR,'components':evidence,'helpers':label_report,
                       'source_inputs':[identity(asm_name,asmraw),identity(tile_name,tileraw)]}

def expected_frames(facing,selector,before):
    if selector==9 and facing in (1,2,3):return bytes([{1:31,2:28,3:24}[facing]])
    if selector==0x31 and facing==1:return bytes([30,31])
    if selector==0x32 and facing==1:return bytes([31])
    return before

def stream_audit(source,target):
    timing=source[TIMING:TIMING+STRIDE]
    need(timing==target[TIMING:TIMING+STRIDE],'all inherited animation timing preserved')
    bindings=[]
    for facing in range(4):
        start=PRIMARY+facing*STRIDE;old=source[start:start+STRIDE];new=target[start:start+STRIDE]
        for selector in range(256):
            before,after=tokens(old,selector,255),tokens(new,selector,255);delays=tokens(timing,selector,0)
            need(after==expected_frames(facing,selector,before),'selector reachability ownership')
            need(len(after)==len(delays) and all(v<32 for v in after),'frame/timing shape')
            if before!=after:bindings.append({'facing':facing,'selector':selector,'before':list(before),'after':list(after),'delays':list(delays)})
    need(len(bindings)==5,'exact five directional selector bindings')
    return {'entrypoints_checked':1024,'changed_selectors':[9,0x31,0x32],'changed_directional_entries':5,'bindings':bindings,
            'timing_unchanged':True,'facing_selection_unchanged':True,'front_is_facing1':True,'back_facing0_unchanged':True,
            'recoil_KO_and_movement_streams_unchanged':True,'evidence_level':'static-stream-reachability-not-native-consumer-proof'}

def derive(source,gfx,assembly,components):
    need(type(source)is bytes and len(source)==SIZE,'eight-MiB pinned current image')
    need(source[:0x10000]==source[0x400000:0x410000],'inherited boot mirror')
    target=bytearray(source);sections=[]
    def put(name,start,data):
        need(type(data)is bytes and data and 0<=start<start+len(data)<=SIZE,'bounded immutable payload')
        target[start:start+len(data)]=data;sections.append((name,start,len(data)))
    for name,start,end in ALLOCATIONS:need(source[start:end]==b'\xFF'*(end-start),'named allocation exactFF preimage: '+name)
    need(gfx[:112*32]==source[GFX:GFX+112*32] and assembly[:30*40]==source[ASSEMBLY:ASSEMBLY+30*40],'original component prefixes preserved')
    put('pc07-caster-front-graphics-append',GFX+112*32,gfx[112*32:])
    put('pc07-caster-front-assembly-append',ASSEMBLY+30*40,assembly[30*40:])
    for name,start,preimage,cpu in HOOKS:
        need(source[start:start+4]==bytes.fromhex(preimage),'exact existing whole-instruction hook preimage')
        put(name,start,b'\x22'+cpu.to_bytes(3,'little'))
    for name,cpu,_,_ in HELPERS:put(name,cpu,components[name])
    tile=components['Pc07SchalaTileBankV4'];needle=bytes.fromhex('E0210F')
    need(tile.count(needle)==1,'single new tile-bound instruction')
    oldtile=tile.replace(needle,bytes.fromhex('E0E10D'),1)
    need(source[0x413000:0x413000+len(tile)]==oldtile,'complete unchanged v3 tile-adapter body')
    bound=tile.index(needle)+1;put('pc07-tile-bank122-bound',0x413000+bound,tile[bound:bound+2])
    for facing in range(4):
        start=PRIMARY+facing*STRIDE
        for selector in (9,0x31,0x32):
            before=tokens(source[start:start+STRIDE],selector,255);after=expected_frames(facing,selector,before)
            if before!=after:
                expected=bytes([facing]) if selector in (9,0x32) else bytes([1,1])
                need(before==expected,'fixed front/hold selector preimage')
                put(f'pc07-primary-{selector:02x}-facing{facing}',start+selector*4,after+b'\xFF')
    checksum=sum(target)&0xFFFF;pair=(checksum^0xFFFF).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    for name,start in (('checksum-primary',0xFFDC),('checksum-mirror',0x40FFDC)):put(name,start,pair)
    need(sum(target)&0xFFFF==checksum and target[:0x10000]==target[0x400000:0x410000],'checksum/mirror')
    return bytes(target),sorted(sections,key=lambda r:r[1])

@contextmanager
def source_snapshot(assembly_directory):
    global _ACTIVE
    need(SEALED,'caster helper interface is not yet sealed')
    need(_ACTIVE is None,'nested snapshot refused')
    source=read_pin(SOURCE);parent=json.loads(read_pin(PARENT))
    need(parent['emitted'] is True and parent['target']=={k:SOURCE[k]for k in ('bytes','sha256')}
         and parent['manifest']['output']==SOURCE['path'],'exact immediate parent binding')
    need(parent['current_shared_intent']['status']=='metadata-valid' and parent['current_shared_diff']['status']=='images-valid'
         and parent['current_shared_diff']['complete_diff_coverage'] is True,'accepted immediate construction')
    allocation=qualify_allocations();effect=qualify_effect_review();gfx,assembly,art=encode_art(source,json.loads(read_pin(ART)))
    components,asm=assemble_components(assembly_directory);target,sections=derive(source,gfx,assembly,components)
    _ACTIVE={'source':source,'target':target,'target_sha256':sha(target),'sections':sections,'streams':stream_audit(source,target),
             'allocation':allocation,'art':art,'assembly':asm,'effect_review':effect}
    try:yield _ACTIVE
    finally:_ACTIVE=None

def inputs():need(_ACTIVE is not None,'one current-operation snapshot required');return _ACTIVE
def template(output):
    output_path(output);snap=inputs()
    sections=[{'id':name,'file_start':start,'bytes':size,'preimage_sha256':sha(snap['source'][start:start+size]),
               'target_sha256':sha(snap['target'][start:start+size])}for name,start,size in snap['sections']]
    return {'schema':SCHEMA,'source':SOURCE,'accepted_parent_receipt':PARENT,'art_input':ART,'output':output,
            'target':{'bytes':SIZE,'sha256':snap['target_sha256']},'sections':sections,'named_allocation_provenance':snap['allocation'],
            'stream_audit':snap['streams'],'effect_review':snap['effect_review'],'new_frames':[30,31],
            'original_frame_prefix_preserved':30,'original_tile_prefix_preserved':112,
            'qualified_visual_field_values':[7,11,26,9,4],'qualified_normal_path_package':4,'qualified_critical_package':16,
            'qualified_launch_sound':77,'impact_sound_hook':False,'native_execution':False,'production_approval':False,
            'evidence_level':'guarded-private-static-stationary-caster-candidate'}

def validate_manifest(manifest):
    need(type(manifest)is dict and encoded(manifest)==encoded(template(manifest.get('output'))),'fixed caster manifest')
    return {'status':'metadata-valid','schema':SCHEMA,'manifest_sha256':sha(encoded(manifest)),'production_approval':False}

def audit_images(manifest,source,target):
    validate_manifest(manifest);snap=inputs()
    need(type(source)is bytes and source==snap['source'],'exact pinned current source')
    need(type(target)is bytes and target==snap['target'],'exact fixed caster target')
    cursor=changed=0;inverse=bytearray(target)
    for row in manifest['sections']:
        start,end=row['file_start'],row['file_start']+row['bytes']
        need(start>=cursor and source[cursor:start]==target[cursor:start],'undeclared change or overlapping sections')
        changed+=sum(a!=b for a,b in zip(source[start:end],target[start:end]));inverse[start:end]=source[start:end];cursor=end
    need(source[cursor:]==target[cursor:] and bytes(inverse)==source,'complete image diff and inverse')
    for name,start,end in NPC_SPANS:need(source[start:end]==target[start:end],'original NPC changed: '+name)
    need(source[GFX:GFX+112*32]==target[GFX:GFX+112*32] and source[ASSEMBLY:ASSEMBLY+30*40]==target[ASSEMBLY:ASSEMBLY+30*40],
         'original112tiles30frames changed')
    need(source[0x490000:0x490100]==target[0x490000:0x490100],'inherited KO helpers changed')
    return {'status':'images-valid','schema':SCHEMA,'declared_sections':len(manifest['sections']),'changed_bytes':changed,
            'complete_diff_coverage':True,'inverse_restores_parent':True,'npc_protected_spans_unchanged':13,'shared_palette_unchanged':True,
            'original_frame_prefix_preserved':30,'original_tile_prefix_preserved':112,'inherited_KO_helpers_unchanged':True,
            'canonical_effect_weapon_sound_tables_unchanged':True,'worldmap_unchanged':True,'native_execution':False,'production_approval':False}
