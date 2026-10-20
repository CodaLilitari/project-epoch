"""Exact private 17-byte preview helper and complete four-span image audit.

Historical native evidence is admitted separately through a fixed guard archive.
Only these two APIs can admit this exact private source/target pair; production
catalogs remain empty. No historical source validator is repinned or bypassed.
"""
from pathlib import Path
from types import ModuleType
import hashlib
import json
import stat
import sys

ROOT=Path(__file__).resolve().parents[1]
PACKET='private/research/pc07_save_preview_builder_v1_20261014/'
DESIGN_DIR='private/research/pc07_save_preview_installation_design_20261014/'
SCHEMA='project-epoch-private-save-preview-intents-v1'
OWNER='pc07-private-save-preview-roster-v1'
SIZE=0x800000
SOURCE_SHA='9c8993158843e3f4f2e7d8bc28ba7a2b4b6c6c60834c7414755a110865dff364'
TARGET_SHA='448763f91d8aee201546d2d365c0753029996358084dd8a789916f58bb349f40'
HELPER_START=0x442200
HELPER=bytes.fromhex('08bf800530c907d00428a9876b2848686b')
HOOK_START=0x02D1C1
HOOK_OLD=bytes.fromhex('bf800530')
HOOK_NEW=bytes.fromhex('22002244')
GUARD_INTENT='validate_pc07_save_preview_manifest'
GUARD_DIFF='audit_pc07_save_preview_images'
BASELINE={'path':PACKET+'historical_wrapper_baseline_v1.py','bytes':19096,'sha256':'57dab6fb133b637dda4be07b83768a717cc9210a5c1c0054bde6a06472974874'}
BASELINE_REPORT={'path':PACKET+'historical_baseline_v1.json','bytes':41881,'sha256':'71785cf44cf53a004116fc4cd4cffc6a1f559da2ff6da46f325ade5a95274a6a'}
GUARD={'path':'tools/validate_rom_write_intents.py','bytes':44162,'sha256':'f028480587d8b5342d946b609c1328707c830f1d75d7015e10e1ebfbdf3d88a3'}
PROSPECTIVE_GUARD={**GUARD,'path':PACKET+'prospective/validate_rom_write_intents_with_preview.py'}
DESIGN={'path':DESIGN_DIR+'installation_design_v1.json','bytes':43842,'sha256':'bef42505563df50e68810f3396119face4a3ea9f5ba7ea554bbf95789f991b5e'}
REVIEW={'path':'private/research/pc07_save_preview_installation_review_20261014/review_v1.json','bytes':5423,'sha256':'12532d253b0fdffb2abe046916fa0595f8c2404a3068144a2b93e4cf83c27d89'}
COMPONENT={'path':'private/research/pc07_save_integration_20261013/v2/assembly/component.bin','bytes':108,'sha256':'4edb7d920d7fbbe45a52d3ad5f67ec5701df4510c4e9ef493c325b31f75c12e4'}
FIELD={'path':'tools/pc07_private_expanded_write_contract_v1.py','bytes':15819,'sha256':'b8bb7cec02a5041658922a842cc29a086e45edeef82d12059f436d794e39f376'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def bootstrap_read(row):
    """Two fixed source roles, checked with stdlib only before project execution."""
    if row not in (FIELD,BASELINE):raise ValueError('fixed preview bootstrap source role')
    path=ROOT/row['path']
    for part in (path,*path.parents):
        try:info=part.lstat()
        except OSError as error:raise ValueError('missing preview bootstrap source') from error
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('preview bootstrap source alias refused')
    if not stat.S_ISREG(path.lstat().st_mode):raise ValueError('preview bootstrap source must be regular')
    with path.open('rb') as stream:raw=stream.read(row['bytes']+1)
    if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('preview bootstrap source identity drift: '+row['path'])
    return raw


def baseline():
    # Neither the field reader nor the adapter executes before both pins pass.
    bootstrap_read(FIELD)
    raw=bootstrap_read(BASELINE);path=ROOT/BASELINE['path']
    name='_epoch_preview_historical_wrapper_v1'
    if name not in sys.modules:
        module=ModuleType(name);module.__file__=str(path);sys.modules[name]=module
        exec(compile(raw,str(path),'exec'),module.__dict__)
    return sys.modules[name]


def read_pin(row):return baseline().read_exact(row)


def load_exact(name,row):
    raw=read_pin(row)
    if name not in sys.modules:
        module=ModuleType(name);module.__file__=str(ROOT/row['path']);sys.modules[name]=module
        exec(compile(raw,module.__file__,'exec'),module.__dict__)
    return sys.modules[name]


def field():return load_exact('_epoch_preview_confined_destination_v1',FIELD)


def add_source(rows,row):
    """Reject duplicate path drift before assigning either inherited or new pin."""
    if row['path'] in rows:baseline().exact(rows[row['path']],row,'duplicate source pin conflict')
    rows[row['path']]=row


def historical_mapping():
    h=baseline();h.validate_mapping(h.ARCHIVE_MAPPING);h.read_historical_row(h.GUARD_ROLE)
    return json.loads(json.dumps(h.ARCHIVE_MAPPING))


def verify_guard_extension():
    h=baseline();old=h.read_exact(h.ARCHIVE_ROW);new=read_pin(GUARD)
    start=new.index(b'def validate_pc07_save_preview_manifest(');end=new.index(b'def main() -> int:',start)
    if new[:start]+new[end:]!=old or new!=read_pin(PROSPECTIVE_GUARD):raise ValueError('current guard must be the exact reviewed additive preview extension')
    return {'archived_guard':h.ARCHIVE_ROW,'current_guard':GUARD,'old_bytes_preserved':True,
            'added_bytes':len(new)-len(old),'added_apis':[GUARD_INTENT,GUARD_DIFF]}


def design():
    h=baseline();plan=json.loads(read_pin(DESIGN));review=json.loads(read_pin(REVIEW))
    for row in plan['sources']:h.read_historical_row(row)
    for row in review['principal_pins']:h.read_historical_row(row)
    read_pin(review['review_source'])
    if (review['status']!='accepted-static-source-proposal-no-image-emission-or-runtime-admission'
            or review['findings'] or review['independent_delta']['target_sha256']!=TARGET_SHA
            or review['native_execution'] is not False or plan['proposed_complete_diff']['changed_bytes']!=29):
        raise ValueError('fixed reviewed source-only preview proposal')
    return plan


def source_rows():
    h=baseline();rows={}
    for row in h.source_rows():add_source(rows,row)
    plan=design();review=json.loads(read_pin(REVIEW))
    for row in plan['sources']+review['principal_pins']+[review['review_source'],BASELINE,BASELINE_REPORT,DESIGN,REVIEW,COMPONENT,FIELD,PROSPECTIVE_GUARD,GUARD]:
        # Only the original proposal's exact old guard role resolves to archive.
        if row['path']==h.GUARD_ROLE['path'] and row!=GUARD:
            h.read_historical_row(row);row=h.ARCHIVE_ROW
        read_pin(row);add_source(rows,row)
    return sorted(rows.values(),key=lambda r:r['path'])


def allocation_check(plan):
    if HELPER_START!=0x442200:raise ValueError('exact named preview allocation')
    end=HELPER_START+len(HELPER)
    if not 0x410000<=HELPER_START<end<=0x7E0000 or HELPER_START>>16!=(end-1)>>16:
        raise ValueError('one-bank canonical expanded allocation')
    for row in plan['allocation']['inherited_occupied_spans']:
        if max(HELPER_START,row['file_start'])<min(end,row['file_start']+row['bytes']):raise ValueError('preview allocation overlaps inherited occupied span')
    if plan['allocation']['cpu_start']!=HELPER_START or plan['allocation']['file_start']!=HELPER_START or plan['allocation']['bytes']!=17:
        raise ValueError('exact reviewed named allocation')


def derive_target(source):
    if type(source)is not bytes or len(source)!=SIZE or sha(source)!=SOURCE_SHA:raise ValueError('exact accepted wrapper source required')
    plan=design();allocation_check(plan)
    helper=read_pin(COMPONENT)[50:67]
    if helper!=HELPER or source[HELPER_START:HELPER_START+17]!=b'\xff'*17:raise ValueError('original helper or named scaffold preimage')
    if HOOK_START!=0x02D1C1 or len(HOOK_OLD)!=4 or len(HOOK_NEW)!=4 or source[HOOK_START:HOOK_START+4]!=HOOK_OLD:
        raise ValueError('whole exact C2D1C1 four-byte load hook')
    target=bytearray(source);target[HELPER_START:HELPER_START+17]=helper;target[HOOK_START:HOOK_START+4]=HOOK_NEW
    checksum=sum(target)&65535;pair=(checksum^65535).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    for start in (0xFFDC,0x40FFDC):target[start:start+4]=pair
    if checksum!=0xABB0 or pair.hex()!='4f54b0ab' or sha(target)!=TARGET_SHA or sum(target)&65535!=checksum or target[:65536]!=target[0x400000:0x410000]:
        raise ValueError('exact preview image/checksum/mirror')
    return bytes(target)


def expected():
    source=read_pin(baseline().IMAGE_ROW)
    return source,derive_target(source)


def sections(source,target):
    rows=[]
    for name,start,size,kind in (('checksum-00FFDC',0xFFDC,4,'structural-checksum-pair'),
        ('preview-whole-load',HOOK_START,4,'canonical-whole-instruction-hook'),
        ('checksum-40FFDC',0x40FFDC,4,'structural-checksum-pair'),
        (OWNER,HELPER_START,17,'named-private-expanded-original-helper')):
        before,after=source[start:start+size],target[start:start+size]
        rows.append({'id':name,'file_start':start,'bytes':size,'kind':kind,'preimage_hex':before.hex(),
                     'payload_hex':after.hex(),'preimage_sha256':sha(before),'sha256':sha(after),
                     'changed_bytes':sum(x!=y for x,y in zip(before,after))})
    if len(rows)!=4 or [(r['file_start'],r['bytes']) for r in rows if r['id']=='preview-whole-load']!=[(0x02D1C1,4)]:
        raise ValueError('derived four-span whole-hook invariant')
    baseline().exact(rows,design()['proposed_complete_diff']['sections'],'independently derived reviewed sections')
    return rows


def template(source,target,output):
    field()._validate_destination(output,{'size':SIZE,'sha256':TARGET_SHA},ROOT)
    plan=design()
    return {'schema':SCHEMA,'mode':'private-save-preview-only','source':{'kind':'exact-native-qualified-preserved-wrapper','bytes':SIZE,'sha256':SOURCE_SHA},
        'target':{'bytes':SIZE,'sha256':TARGET_SHA},'output':output,'sections':sections(source,target),
        'allocation':plan['allocation'],'entry_contract':plan['entry_contract'],'domain':plan['domain'],
        'hook':plan['hook'],'component':plan['component'],'design':DESIGN,'independent_source_review':REVIEW,
        'historical_baseline':BASELINE_REPORT,'historical_guard_mapping':historical_mapping(),
        'baseline_reproduction_required_before_emission':True,'evidence_level':'fixed-private-source-construction-only',
        'native_execution':False,'production_approval':False,'post_C2CF55_continuation_proved':False,
        'physical_stack_ownership_proved':False,'interrupt_admission':False,'compatible_PC07_persistence':False,
        'cold_load_proved':False,'sidecar_or_SHA_installed':False,'preview_portrait_implemented':False}


def validate_manifest(manifest):
    if type(manifest)is not dict:raise ValueError('exact preview manifest required')
    source_rows();verify_guard_extension();source,target=expected()
    baseline().exact(manifest,template(source,target,manifest.get('output')),'exact preview manifest')
    return {'status':'metadata-valid','schema':SCHEMA,'production_approval':False,
            'manifest_sha256':sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())}


def audit_images(manifest,source,target):
    report=validate_manifest(manifest);wanted_source,wanted_target=expected()
    if type(source)is not bytes or type(target)is not bytes or source!=wanted_source or target!=wanted_target:
        raise ValueError('complete preview image differs from exact fixed recipe')
    count=len(manifest['sections'])
    if count!=4:raise ValueError('exact four declared sections')
    hook=[r for r in manifest['sections'] if r['id']=='preview-whole-load']
    if len(hook)!=1 or (hook[0]['file_start'],hook[0]['bytes'],hook[0]['preimage_hex'],hook[0]['payload_hex'])!=(0x02D1C1,4,HOOK_OLD.hex(),HOOK_NEW.hex()):
        raise ValueError('whole C2D1C1 load instruction invariant')
    cursor=changed=0;inverse=bytearray(target)
    for row in manifest['sections']:
        start,end=row['file_start'],row['file_start']+row['bytes']
        if start<cursor or source[cursor:start]!=target[cursor:start]:raise ValueError('undeclared/overlapping preview delta')
        if sha(source[start:end])!=row['preimage_sha256'] or sha(target[start:end])!=row['sha256']:raise ValueError('fixed preview section identity')
        actual=sum(x!=y for x,y in zip(source[start:end],target[start:end]))
        if actual!=row['changed_bytes']:raise ValueError('derived changed byte count')
        changed+=actual;inverse[start:end]=source[start:end];cursor=end
    if changed!=29 or source[cursor:]!=target[cursor:] or bytes(inverse)!=source:raise ValueError('complete preview diff/inverse invariant')
    return {**report,'status':'images-valid','changed_bytes':changed,'declared_sections':count,'complete_diff_coverage':True,
            'accepted_image_inverse':True,'whole_hook_extent_checked':True,'target_sha256':TARGET_SHA,
            'native_execution':False,'emission_admission':False,'post_C2CF55_continuation_proved':False}


def build_manifest(source,target,output):
    manifest=template(source,target,output);audit_images(manifest,source,target)
    return manifest
