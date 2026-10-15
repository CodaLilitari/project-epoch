"""Fixed private loader delta over the accepted native writer image; no history execution.

Two named expanded allocations, four whole instruction hooks and mirrored checksums.
The old wrapper, SHA and tables remain byte-identical. Production stays empty.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import re
import stat

ROOT=Path(__file__).resolve().parents[1]
PACKET='private/research/pc07_native_sidecar_loader_builder_v1_20261015/'
SCHEMA='project-epoch-private-native-sidecar-loader-intents-v1'
SOURCE_SHA='0d32e8509a62bdd12737409beba2a53fa79820e28ff9375ee92c4118d1fc2ba7'
SIZE=0x800000
SOURCE=dict(path='private/test_runs/pc07_native_sidecar_writer_v1/diagnostic.sfc',bytes=SIZE,sha256=SOURCE_SHA)
PARENT_BUILD=dict(path='private/test_runs/pc07_native_sidecar_writer_v1/receipt.json',bytes=19882,sha256='264dcf505852110126eeb57cf5024c1969d7c1a5a44666ac8202f2a6b31f477b')
PARENT_NATIVE=dict(path='private/test_runs/pc07_native_sidecar_writer_v1_run1/validation_result_v1.json',bytes=11122,sha256='a98a7c2a3aa6adca3751c8f0ce698449ac7ef66d2c906e4a59427d0382f40c6f')
ALLOCATION=dict(path='private/research/pc07_save_preview_installation_design_20261014/installation_design_v1.json',bytes=43842,sha256='bef42505563df50e68810f3396119face4a3ea9f5ba7ea554bbf95789f991b5e')
SCAFFOLD=dict(path='tools/schala_rom_scaffold.py',bytes=13386,sha256='a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a')
ASSEMBLY=dict(path=PACKET+'assembly/receipt.json',bytes=4511,sha256='96766cc67ac466cac269bcff11dce8e7404ff7ac3f4d2aed6698ac865bbb6aa0')
COMPONENT=dict(path=PACKET+'assembly/component.bin',bytes=147456,sha256='ad403d6ec7627585187fbc997b7f2ec37d866d658acfa6a89e656f1892c67df4')
LABELS=dict(path=PACKET+'assembly/labels.json',bytes=9044,sha256='a49b120b899464f84594a42a064011791c1a49c37fa5b41a6eae7bd171681fe7')
SPANS=(('native-sidecar-loader',0x443400,0,671),('load-preflight',0x442000,0x1000,108),
       ('round8-core',0x450000,0x10000,0x4A26),('sigma-tables',0x460000,0x20000,0x4000))
NEW_ALLOCATIONS=(('load-preflight-suffix',0x442032,0x1032,58),('native-sidecar-loader',0x443400,0,671))
HOOKS=(('load-preview-call',0x2D1C1,'bf800530','22322044'),
       ('load-whole-success-branch',0x2E657,'22a3faff8037','5c003444eaea'),
       ('load-table-copy',0x3FFAB2,'a27bfaa09098a92700547eff','a20020a09098a93100547e44'),
       ('load-table-loop-count',0x3FFAE6,'c92800','c93200'))
INHERITED_SHADOW=(('shadow-wrapper',0x443000,173,'e1dc837e962d1d7493690c62a635b90815464d6d2d1f5267c03f4df58cb95e9a'),
 ('round8-core',0x450000,0x4A26,'8ad573f3b5727402122929d5fca1982a224c43f8fc2448e44c1b6bba01e856e5'),
 ('sigma-tables',0x460000,0x4000,'f3a9bb9b3735fbc5e50403ccb86342f05e0b1762f5e835ce33fe7003bd892201'))
GUARD_INTENT='validate_pc07_native_sidecar_loader_manifest'
GUARD_DIFF='audit_pc07_native_sidecar_loader_images'
_ACTIVE=None

def need(value,message):
    if not value:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
def exact(a,b,message):need(encoded(a)==encoded(b),message)

def path(relative):
    need(type(relative) is str and '\\' not in relative and ':' not in relative,'canonical project-relative path')
    parts=relative.split('/')
    need(parts and all(p and p not in ('.','..') for p in parts),'path traversal refused')
    result=ROOT.joinpath(*parts)
    for item in (result,*result.parents):
        if item.exists() or item.is_symlink():
            info=item.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'aliased project path')
    need(result.resolve().is_relative_to(ROOT.resolve()),'path escapes project')
    return result

def read_pin(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256'} and type(row['bytes']) is int and row['bytes']>=0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']),'exact input identity')
    source=path(row['path']);need(source.is_file(),'regular source required')
    need(source.stat().st_size==row['bytes'],'source extent drift: '+row['path'])
    raw=source.read_bytes();need(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'source identity drift: '+row['path'])
    return raw

def output_path(relative):
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_native_sidecar_loader_[A-Za-z0-9_-]+/diagnostic\.sfc',relative),
         'fresh named private loader diagnostic destination required')
    return path(relative)

def qualify():
    """One direct source snapshot; accepted receipts are data, never code."""
    rows={};raws={}
    def add(row):
        if row['path'] in rows:
            exact(rows[row['path']],row,'conflicting source identity');return raws[row['path']]
        raw=read_pin(row);rows[row['path']]=dict(row);raws[row['path']]=raw;return raw
    source=add(SOURCE);parent=json.loads(add(PARENT_BUILD));native=json.loads(add(PARENT_NATIVE))
    allocation=json.loads(add(ALLOCATION));add(SCAFFOLD)
    assembly=json.loads(add(ASSEMBLY));component=add(COMPONENT);positioned=json.loads(add(LABELS))
    need(parent['emitted'] is True and parent['target_sha256']==SOURCE_SHA and parent['artifacts']['diagnostic.sfc']==SOURCE,
        'accepted parent build/image binding')
    need(parent['current_shared_intent']['status']=='metadata-valid' and parent['current_shared_diff']['status']=='images-valid'
         and parent['current_shared_diff']['complete_diff_coverage'] is True,'accepted parent guarded construction')
    exact(native['inputs']['diagnostic.sfc'],dict(bytes=SIZE,sha256=SOURCE_SHA),'accepted native image binding')
    need(native['result']['status']=='accepted-bounded-native-sidecar-writer' and native['sidecar_persistence_proved'] is True
         and native['result']['returned_cpu']['pc']==0xCF55 and native['result']['returned_cpu']['k']==0xC2,
         'accepted parent native writer boundary')
    for row in assembly['sources']+[assembly['preparer']]+assembly['artifacts']:add(row)
    need(assembly['ROM_read_or_emitted'] is False and assembly['native_execution'] is False and assembly['returncode']==0,
         'original component assembly scope')
    inherited=allocation['allocation']['inherited_occupied_spans']
    need(len(inherited)==46 and allocation['allocation']['inert_scaffold_sha256']=='26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93',
         'accepted scaffold and occupied-span provenance')
    writer_rows=[row for row in parent['manifest']['sections'] if row['kind']=='original-expanded-component']
    need(len(writer_rows)==1 and writer_rows[0]['id']=='native-sidecar-writer' and
         (writer_rows[0]['file_start'],writer_rows[0]['bytes'])==(0x443100,570),'accepted writer allocation')
    need(sha(source[0x443100:0x44333A])==writer_rows[0]['sha256'],'unchanged accepted writer bytes')
    shadow_rows=[]
    for name,start,size,digest in INHERITED_SHADOW:
        need(sha(source[start:start+size])==digest,'unchanged accepted shadow allocation bytes')
        shadow_rows.append(dict(id=name,file_start=start,bytes=size,sha256=digest))
    need(parent['manifest']['provenance']['inherited_shadow_span_records']==3 and
         parent['manifest']['provenance']['old_shadow_SHA_and_tables_unchanged'] is True,
         'accepted parent preserves the three shadow allocations')
    occupied=inherited+shadow_rows+writer_rows
    for name,start,offset,size in NEW_ALLOCATIONS:
        need(0x410000<=start<start+size<=0x7E0000 and start>>16==(start+size-1)>>16,'bounded inert-scaffold expanded placement')
        need(not any(max(start,r['file_start'])<min(start+size,r['file_start']+r['bytes']) for r in occupied),
             'loader allocation overlaps accepted occupied span')
        need(source[start:start+size]==b'\xFF'*size,'exact loader allocation preimage')
    for name,start,offset,size in SPANS:
        matching=[row for row in positioned['spans'] if row['id']==name]
        need(len(matching)==1,'unique original positioned component')
        exact(matching[0],dict(id=name,cpu_start=start,file_start=start,component_offset=offset,bytes=size,
            sha256=sha(component[offset:offset+size])),'exact positioned component bounds/identity')
        if name in ('round8-core','sigma-tables'):
            need(source[start:start+size]==component[offset:offset+size],'unchanged SHA/core table slice differs')
    need(source[0x442000:0x442032]==component[0x1000:0x1032],'existing first50 table bytes unchanged')
    need(sha(source[0x442100:0x442155])=='99e7372160bedd49f504fb2b678ce677c55ab823e459433d929a78b1dce36f2b',
         'accepted save-tail wrapper preserved')
    observer=dict(schema='project-epoch-cold-load-observer-labels-v1',labels=positioned['labels'],
        spans={key:dict(start=start,end=start+size) for key,(_,start,_,size) in zip(('loader','preflight','sha','tables'),SPANS)})
    for name,start,before,after in HOOKS:
        need(source[start:start+len(bytes.fromhex(before))]==bytes.fromhex(before),'whole exact '+name+' hook preimage')
        need(len(before)==len(after),'same-size whole instruction hook')
    return dict(source=source,component=component,labels=observer,source_rows=sorted(rows.values(),key=lambda r:r['path']),
        provenance=dict(accepted_parent_build_receipt=PARENT_BUILD,accepted_parent_native_result=PARENT_NATIVE,
            accepted_allocation_census=ALLOCATION,inert_scaffold_source=SCAFFOLD,
            inert_scaffold_sha256=allocation['allocation']['inert_scaffold_sha256'],
            inert_scaffold_expanded_fill_span=dict(start=0x410000,end=0x7E0000,fill=255),
            inherited_census_span_records=46,inherited_shadow_span_records=3,inherited_writer_span_records=1,
            new_allocations_disjoint=True,exact_preimages_checked=True,FF_alone_is_authority=False,
            existing_table_first50_save_wrapper_writer_shadow_SHA_tables_unchanged=True,
            historical_builders_or_validators_executed=False))

@contextmanager
def source_snapshot():
    global _ACTIVE
    need(_ACTIVE is None,'nested source snapshot refused')
    _ACTIVE=qualify()
    try:yield _ACTIVE
    finally:_ACTIVE=None

def inputs():return _ACTIVE if _ACTIVE is not None else qualify()

def derive(snapshot):
    # Same qualified immutable bytes are reused by both required audit APIs.
    if '_derived_target' in snapshot:return snapshot['_derived_target']
    source=snapshot['source'];target=bytearray(source)
    for name,start,before,after in HOOKS:target[start:start+len(bytes.fromhex(after))]=bytes.fromhex(after)
    for name,start,offset,size in NEW_ALLOCATIONS:target[start:start+size]=snapshot['component'][offset:offset+size]
    checksum=sum(target)&0xFFFF;pair=(checksum^0xFFFF).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    for offset in (0xFFDC,0x40FFDC):target[offset:offset+4]=pair
    need(sum(target)&0xFFFF==checksum and target[:0x10000]==target[0x400000:0x410000],'mirrored header/checksum invariant')
    for start,size in ((0x442000,50),(0x442100,85),(0x443100,570),*((start,size) for _,start,size,_ in INHERITED_SHADOW)):
        need(target[start:start+size]==source[start:start+size],'inherited accepted component changed')
    snapshot['_derived_target']=bytes(target);snapshot['_target_sha']=sha(snapshot['_derived_target'])
    return snapshot['_derived_target']

def template(snapshot,target,output):
    output_path(output);source=snapshot['source'];rows=[]
    spans=[('checksum-primary',0xFFDC,4,'header'),('checksum-boot-mirror',0x40FFDC,4,'header')]
    spans += [(name,start,len(bytes.fromhex(before)),'whole-instruction-hook') for name,start,before,after in HOOKS]
    spans += [(name,start,size,'original-expanded-component') for name,start,offset,size in NEW_ALLOCATIONS]
    for name,start,size,kind in sorted(spans,key=lambda row:row[1]):
        before,after=source[start:start+size],target[start:start+size]
        rows.append(dict(id=name,file_start=start,bytes=size,kind=kind,preimage_sha256=sha(before),sha256=sha(after),
            changed_bytes=sum(a!=b for a,b in zip(before,after)),preimage_hex=before.hex(),
            owner='pc07-private-native-sidecar-loader-v1'))
    return dict(schema=SCHEMA,mode='private-native-sidecar-loader-only',source=SOURCE,target=dict(bytes=SIZE,sha256=snapshot['_target_sha']),
        output=output,sections=rows,provenance=snapshot['provenance'],original_component_receipt=ASSEMBLY,
        positioned_labels=LABELS,scratch=dict(start=0x7EAE00,bytes=0xC2,ownership_proved=False),
        intended_runtime_sidecar=dict(start=0x307E00,bytes=0xA0,physical_slot=1,profile=1,metadata_live_address=None),
        success_cpu=0xC2E694,failure_cpu=0xC2E646,production_approval=False,native_execution=False,
        sidecar_load_observed=False,cold_load_proved=False,preview_patch_installed=True,
        evidence_level='fixed-private-source-construction-only')

def validate_manifest(manifest):
    need(type(manifest) is dict,'exact loader manifest')
    snapshot=inputs();target=derive(snapshot)
    exact(manifest,template(snapshot,target,manifest.get('output')),'fixed loader manifest mismatch')
    return dict(status='metadata-valid',schema=SCHEMA,manifest_sha256=sha(encoded(manifest)),production_approval=False)

def audit_images(manifest,source,target):
    snapshot=inputs();expected=derive(snapshot)
    need(type(source) is bytes and source==snapshot['source'],'exact accepted parent image')
    need(type(target) is bytes and target==expected,'exact positioned loader image')
    exact(manifest,template(snapshot,expected,manifest.get('output')),'fixed loader manifest mismatch')
    cursor=changed=0;inverse=bytearray(target)
    for row in manifest['sections']:
        start,end=row['file_start'],row['file_start']+row['bytes']
        need(start>=cursor and source[cursor:start]==target[cursor:start],'undeclared or overlapping loader write')
        need(sha(source[start:end])==row['preimage_sha256'] and sha(target[start:end])==row['sha256'],'exact loader section bytes')
        count=sum(a!=b for a,b in zip(source[start:end],target[start:end]));need(count==row['changed_bytes'],'per-span changed bytes')
        changed+=count;inverse[start:end]=source[start:end];cursor=end
    need(source[cursor:]==target[cursor:] and bytes(inverse)==source,'complete loader diff/inverse coverage')
    return dict(status='images-valid',schema=SCHEMA,manifest_sha256=sha(encoded(manifest)),target_sha256=snapshot['_target_sha'],
        changed_bytes=changed,declared_sections=len(manifest['sections']),complete_diff_coverage=True,
        inverse_restores_parent=True,production_approval=False,native_execution=False)
