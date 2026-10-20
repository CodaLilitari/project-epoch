"""Immediate-parent private HP-color correction; existing numeric/art build retained."""
from contextlib import contextmanager
import re,json,subprocess
from pc07_run_pose_write_contract_v1 import ROOT,SIZE,NPC_SPANS,need,sha,encoded,resolve,read_pin
from pc07_menu_stats_portrait_write_contract_v1 import identity,ASAR
import native_pc07_menu_hp_color_helper_v1 as helper
SCHEMA='project-epoch-private-pc07-menu-hp-color-intents-v1'
SOURCE={'path':'private/test_runs/pc07_menu_stats_portrait_v1/diagnostic.sfc','bytes':SIZE,'sha256':'c020bca3e766191a8db00bd0d4f75f9d2f16b3cd884c58184af8792f84f55244'}
PARENT={'path':'private/test_runs/pc07_menu_stats_portrait_v1/receipt.json','bytes':42645,'sha256':'7ba2adfec600df29ddf50932df31480777c6f75412d07bb4879794d536c55f2b'}
ASM={'path':'asm/pc07_menu_hp_color_v1.asm','bytes':1305,'sha256':'5b5980ad002a8a53af5f50cde943de4cb659f2988a0b2c28a53a27c7e715fd24'}
ALLOCATION=('pc07-normal-menu-HP-color-v1',0x4A0440,0x4A0540)
HOOK=0x02A200
PREIMAGE=bytes.fromhex('22050247EAEA')
FALLBACK_SPAN={'file_start': 4653573, 'file_end_exclusive': 4653654, 'bytes': 81, 'sha256': '2dc641affc3743ad088cc6696a6a67e633285709007add97386d72e93e0a0f0c'}
SYMPTOM_CONTEXT={'path': 'private/research/pc07_portrait_20261020/runtime/runs/candidate_stats_portrait_v1/schala_first.json', 'bytes': 4654, 'sha256': '26cb2b65d0cf63d438155679c87ad15381045d2e39374dbd53cfea29db4a1faf'}
_ACTIVE=None

def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_menu_stats_portrait_[A-Za-z0-9_-]+/diagnostic\.sfc',relative),'fresh private menu output')
    return resolve(relative)

def allocations(parent):
    old=parent['manifest']['named_allocation_provenance']
    need(old['occupied_spans_checked']==195 and len(old['occupied_spans'])==195 and old['all_disjoint'] is True and old['FF_alone_is_authority'] is False,'accepted immediate occupied census')
    occupied=list(old['occupied_spans'])
    for prefix,rows in (('stats-v1',parent['manifest']['sections']),('stats-v1-reservation',old['new_allocations'])):
        for i,row in enumerate(rows):
            a,n=row['file_start'],row['bytes'];need(type(a)is int and type(n)is int and 0<=a<a+n<=SIZE,'occupied bounds')
            occupied.append({'id':f'{prefix}:{i}:{row["id"]}','file_start':a,'bytes':n,'file_end_exclusive':a+n})
    need(len(occupied)==202,'195 plus6 sections plus1 complete reservation')
    fill=old['inherited_expanded_fill'];need(fill=={'start':0x410000,'end':0x7E0000,'fill':255},'scaffold provenance')
    name,a,b=ALLOCATION
    need(fill['start']<=a<b<=fill['end'],'expansion bounds')
    for row in occupied:
        need(row['file_end_exclusive']==row['file_start']+row['bytes'],'full occupied span')
        need(max(a,row['file_start'])>=min(b,row['file_end_exclusive']),'new allocation overlaps occupied')
    return {'immediate_receipt':PARENT,'inherited_expanded_fill':fill,'occupied_spans':sorted(occupied,key=lambda r:(r['file_start'],r['id'])),
            'occupied_spans_checked':202,'all_disjoint':True,'FF_alone_is_authority':False,
            'new_allocations':[{'id':name,'file_start':a,'bytes':b-a,'file_end_exclusive':b}],'production_approval':False}

def assemble(directory):
    directory=resolve(directory.relative_to(ROOT).as_posix());need(not directory.exists(),'fresh assembly output')
    read_pin(ASAR);src=read_pin(ASM);item=helper.encode(src.decode('utf-8'))['Pc07MenuHpColorV1']
    directory.mkdir(parents=True,exist_ok=False)
    ap,bp=directory/'color.asm',directory/'color.bin'
    ap.write_text('arch 65816\nnorom\norg $000000\nbase $4A0440\n'+item['source'],encoding='utf-8',newline='\n');bp.write_bytes(b'')
    run=subprocess.run([str(resolve(ASAR['path'])),'--no-title-check','--fix-checksum=off',str(ap),str(bp)],cwd=directory,capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (directory/'stdout.txt').write_bytes(run.stdout);(directory/'stderr.txt').write_bytes(run.stderr)
    need(run.returncode==0 and bp.read_bytes()==item['data'],'Asar independent byte equality')
    return item,{'assembler':ASAR,'source':ASM,'bytes':len(item['data']),'sha256':sha(item['data']),'independent_opcode_equality':True,'returncode':run.returncode}

def derive(source,blob):
    need(len(source)==SIZE and source[:0x10000]==source[0x400000:0x410000],'source extent/mirror')
    need(source[HOOK:HOOK+6]==PREIMAGE,'exact installed threshold hook')
    _,a,b=ALLOCATION;need(source[a:b]==b'\xFF'*(b-a),'named expansion preimage')
    target,sections=bytearray(source),[]
    def put(name,at,data):target[at:at+len(data)]=data;sections.append((name,at,len(data)))
    put('normal-menu-HP-color-hook',HOOK,bytes.fromhex('2240044AEAEA'))
    put(ALLOCATION[0],a,blob)
    checksum=sum(target)&65535;pair=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    put('checksum-primary',0xFFDC,pair);put('checksum-mirror',0x40FFDC,pair)
    need(sum(target)&65535==checksum and target[:0x10000]==target[0x400000:0x410000],'target checksum/mirror')
    return bytes(target),sorted(sections,key=lambda x:x[1])

@contextmanager
def source_snapshot(directory):
    global _ACTIVE
    need(_ACTIVE is None,'nested snapshot')
    source,parent=read_pin(SOURCE),json.loads(read_pin(PARENT))
    need(parent['emitted'] is True and parent['target']=={k:SOURCE[k] for k in ('bytes','sha256')} and parent['manifest']['output']==SOURCE['path'],'exact immediate parent')
    need(parent['current_shared_intent']['status']=='metadata-valid' and parent['current_shared_diff']['status']=='images-valid' and parent['current_shared_diff']['complete_diff_coverage'] is True,'parent guard receipt')
    context=json.loads(read_pin(SYMPTOM_CONTEXT));need(context['state']['mode']==255 and context['state']['record_9A90']==7,'retained normal-layout identity context')
    need(sha(source[FALLBACK_SPAN['file_start']:FALLBACK_SPAN['file_end_exclusive']])==FALLBACK_SPAN['sha256'],'complete original threshold helper preimage')
    allocation=allocations(parent);item,assembly=assemble(directory);target,sections=derive(source,item['data'])
    _ACTIVE={'source':source,'target':target,'sections':sections,'allocation':allocation,'assembly':assembly,'helper':item}
    try:yield _ACTIVE
    finally:_ACTIVE=None

def inputs():need(_ACTIVE is not None,'current snapshot required');return _ACTIVE

def template(output):
    output_path(output);s=inputs()
    return {'schema':SCHEMA,'source':SOURCE,'accepted_parent_receipt':PARENT,'output':output,'target':{'bytes':SIZE,'sha256':sha(s['target'])},
      'sections':[{'id':n,'file_start':a,'bytes':z,'preimage_sha256':sha(s['source'][a:a+z]),'target_sha256':sha(s['target'][a:a+z])} for n,a,z in s['sections']],
      'named_allocation_provenance':s['allocation'],'assembly_input':ASM,
      'source_owned_entry':'C2A200,M16/X16,D0,DBR7E','qualified_predicates':{'X':14,'layout0D36':255,'record9A90':7,'live2830':7,'pointer6F':0x2830},
      'threshold_source':'menu record9ACF derived maximumHP','threshold':'floor(maxHP/10)','critical':'currentHP<=threshold','comparison_target':'9A93 currentHP',
      'fallback_tail':'470205 original party-exchange helper','complete_fallback_preimage':FALLBACK_SPAN,'retained_native_symptom_context':SYMPTOM_CONTEXT,'new_hook_native_context_status':'pending focused run; entry widths source-owned','new_WRAM_scratch':False,'local_stack_bytes_including_JSL':9,
      'art_numeric_fix_base_stats_equipment_growth_save_unchanged':True,'native_execution':False,'production_approval':False,
      'evidence_level':'guarded-private-static-normal-menu-HP-color'}

def validate_manifest(m):
    need(type(m)is dict and encoded(m)==encoded(template(m.get('output'))),'fixed color manifest')
    return {'status':'metadata-valid','schema':SCHEMA,'manifest_sha256':sha(encoded(m)),'production_approval':False}

def audit_images(m,source,target):
    validate_manifest(m);s=inputs();need(type(source)is bytes and source==s['source'] and type(target)is bytes and target==s['target'],'exact parent and derivative')
    cursor=changed=0;inverse=bytearray(target)
    for row in m['sections']:
        a,b=row['file_start'],row['file_start']+row['bytes'];need(a>=cursor and source[cursor:a]==target[cursor:a],'undeclared diff/overlap')
        changed+=sum(x!=y for x,y in zip(source[a:b],target[a:b]));inverse[a:b]=source[a:b];cursor=b
    need(source[cursor:]==target[cursor:] and bytes(inverse)==source,'complete-diff inverse')
    for n,a,b in NPC_SPANS:need(source[a:b]==target[a:b],'NPC changed:'+n)
    canonical=bytearray(target[:0x400000])
    for a,z in ((0xFFDC,4),(HOOK,6)):canonical[a:a+z]=source[a:a+z]
    need(bytes(canonical)==source[:0x400000],'canonical outside exact hook/header')
    need(source[0x410000:0x4A0440]==target[0x410000:0x4A0440] and source[0x4A0540:]==target[0x4A0540:],'all prior expanded code/art exact')
    return {'status':'images-valid','schema':SCHEMA,'declared_sections':len(m['sections']),'changed_bytes':changed,'complete_diff_coverage':True,'inverse_restores_parent':True,
      'canonical_instruction_hook_bytes':6,'canonical_game_data_including_unused_unchanged':True,'npc_protected_spans_unchanged':13,
      'original_threshold_helper_unchanged':True,'all_previous_expanded_code_and_art_unchanged':True,'numeric_fix_balance_equipment_growth_save_unchanged':True,
      'native_execution':False,'production_approval':False}
