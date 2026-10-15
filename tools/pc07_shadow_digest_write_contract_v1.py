"""Fixed private shadow-digest image delta; no historical builder execution.

Accepted parent evidence is reused by identity. The three new named expanded
allocations derive from the documented inert scaffold and accepted occupied
span census, with exact source preimages. Production catalogs stay untouched.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import re
import stat

ROOT=Path(__file__).resolve().parents[1]
PACKET='private/research/pc07_shadow_digest_builder_v1_20261015/'
SCHEMA='project-epoch-private-shadow-digest-intents-v1'
SOURCE_SHA='9c8993158843e3f4f2e7d8bc28ba7a2b4b6c6c60834c7414755a110865dff364'
SIZE=0x800000
SOURCE=dict(path='private/test_runs/pc07_preserved_save_table_v1/diagnostic.sfc',bytes=SIZE,sha256=SOURCE_SHA)
RECEIPT=dict(path='private/test_runs/pc07_preserved_save_table_v1_run1/receipt.json',bytes=41439,sha256='23536cf4bad74f657571d510cc6d9062ca504a5f8e6f7a16619948e143553c33')
ALLOCATION=dict(path='private/research/pc07_save_preview_installation_design_20261014/installation_design_v1.json',bytes=43842,sha256='bef42505563df50e68810f3396119face4a3ea9f5ba7ea554bbf95789f991b5e')
SCAFFOLD=dict(path='tools/schala_rom_scaffold.py',bytes=13386,sha256='a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a')
ASSEMBLY=dict(path=PACKET+'assembly/receipt.json',bytes=3961,sha256='706363377e6089f245627763eb1bfc2d6cec841628503a93e124f497db440bb8')
COMPONENT=dict(path=PACKET+'assembly/component.bin',bytes=147456,sha256='ee4a8827fc1ce783323c0854d54bfed3e5f8dc833e65b14ba18016185c3372f4')
LABELS=dict(path=PACKET+'assembly/labels.json',bytes=6512,sha256='6c85e86398f4315a9c68b94dc03f643009c7cbd4696b33198818693314993fd4')
SPANS=(('shadow-wrapper',0x443000,0,173),('round8-core',0x450000,0x10000,0x4A26),('sigma-tables',0x460000,0x20000,0x4000))
GUARD_INTENT='validate_pc07_shadow_digest_manifest'
GUARD_DIFF='audit_pc07_shadow_digest_images'
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
    need(type(relative) is str and re.fullmatch(r'private/test_runs/pc07_shadow_digest_[A-Za-z0-9_-]+/diagnostic\.sfc',relative),
         'fresh named private shadow diagnostic destination required')
    return path(relative)


def qualify():
    """One bounded source snapshot; no recursive imports or old validation."""
    rows={};raws={}
    def add(row):
        if row['path'] in rows:
            exact(rows[row['path']],row,'conflicting source identity');return raws[row['path']]
        raw=read_pin(row);rows[row['path']]=dict(row);raws[row['path']]=raw;return raw
    source=add(SOURCE);receipt=json.loads(add(RECEIPT));allocation=json.loads(add(ALLOCATION));add(SCAFFOLD)
    assembly=json.loads(add(ASSEMBLY));component=add(COMPONENT);positioned=json.loads(add(LABELS))
    need(receipt['returncode']==64 and receipt['artifacts']['diagnostic.sfc']=={'bytes':SIZE,'sha256':SOURCE_SHA},'accepted parent receipt/image binding')
    need(receipt['observations']['returned_cpu']['pc']==0xCF55 and receipt['observations']['returned_cpu']['k']==0xC2,'accepted parent save boundary')
    for row in assembly['sources']+[assembly['preparer']]+assembly['artifacts']:add(row)
    need(assembly['ROM_read_or_emitted'] is False and assembly['native_execution'] is False and assembly['returncode']==0,'original component assembly scope')
    need(all(source[start:start+size]==b'\xFF'*size for _,start,_,size in SPANS),'exact expanded allocation preimages')
    inherited=allocation['allocation']['inherited_occupied_spans']
    need(len(inherited)==46 and allocation['allocation']['inert_scaffold_sha256']=='26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93','accepted scaffold and occupied-span provenance')
    for name,start,offset,size in SPANS:
        need(0x410000<=start<start+size<=0x7E0000 and start>>16==(start+size-1)>>16,'bounded canonical expanded bank placement')
        need(not any(max(start,r['file_start'])<min(start+size,r['file_start']+r['bytes']) for r in inherited),'new allocation overlaps accepted occupied span')
        matching=[r for r in positioned['spans'] if r['id']==name]
        need(len(matching)==1,'unique original positioned component')
        exact(matching[0],dict(id=name,cpu_start=start,file_start=start,component_offset=offset,bytes=size,sha256=sha(component[offset:offset+size])),'exact positioned component bounds/identity')
    labels=positioned['labels']
    observer=dict(schema='project-epoch-shadow-observer-labels-v1',labels=labels,
        spans={key:dict(start=start,end=start+size) for key,(_,start,_,size) in zip(('wrapper','sha','tables'),SPANS)})
    need(source[0x2CF51:0x2CF55]==bytes.fromhex('22002144'),'whole accepted save-call hook preimage')
    need(sha(source[0x442100:0x442155])=='99e7372160bedd49f504fb2b678ce677c55ab823e459433d929a78b1dce36f2b','accepted preserved wrapper identity')
    return dict(source=source,component=component,labels=observer,source_rows=sorted(rows.values(),key=lambda r:r['path']),
        provenance=dict(accepted_parent_receipt=RECEIPT,accepted_allocation_census=ALLOCATION,
            inert_scaffold_sha256=allocation['allocation']['inert_scaffold_sha256'],inherited_span_records=46,
            new_allocations_disjoint=True,exact_preimages_checked=True,FF_alone_is_authority=False,
            historical_builders_or_validators_executed=False))


@contextmanager
def source_snapshot():
    """Reuse one qualified immutable-byte snapshot across both current audits."""
    global _ACTIVE
    need(_ACTIVE is None,'nested source snapshot refused')
    _ACTIVE=qualify()
    try:yield _ACTIVE
    finally:_ACTIVE=None


def inputs():return _ACTIVE if _ACTIVE is not None else qualify()


def derive(snapshot):
    source=snapshot['source'];target=bytearray(source)
    target[0x2CF51:0x2CF55]=bytes.fromhex('22003044')
    for _,start,offset,size in SPANS:target[start:start+size]=snapshot['component'][offset:offset+size]
    checksum=sum(target)&0xFFFF;pair=(checksum^0xFFFF).to_bytes(2,'little')+checksum.to_bytes(2,'little')
    for offset in (0xFFDC,0x40FFDC):target[offset:offset+4]=pair
    need(sum(target)&0xFFFF==checksum and target[:0x10000]==target[0x400000:0x410000],'mirrored header/checksum invariant')
    return bytes(target)


def template(snapshot,target,output):
    output_path(output);source=snapshot['source']
    rows=[]
    spans=[('checksum-primary',0xFFDC,4,'header'),('normal-save-shadow-call',0x2CF51,4,'whole-instruction-hook'),
           ('checksum-boot-mirror',0x40FFDC,4,'header')]+[(name,start,size,'original-expanded-component') for name,start,_,size in SPANS]
    for name,start,size,kind in sorted(spans,key=lambda item:item[1]):
        before,after=source[start:start+size],target[start:start+size]
        rows.append(dict(id=name,file_start=start,bytes=size,kind=kind,preimage_sha256=sha(before),sha256=sha(after),
            changed_bytes=sum(a!=b for a,b in zip(before,after)),preimage_hex=before.hex() if size==4 else None,
            owner='pc07-private-shadow-digest-v1'))
    return dict(schema=SCHEMA,mode='private-shadow-digest-only',source=SOURCE,target=dict(bytes=SIZE,sha256=sha(target)),
        output=output,sections=rows,provenance=snapshot['provenance'],original_component_receipt=ASSEMBLY,
        positioned_labels=LABELS,scratch=dict(start=0x7EAE00,bytes=0xC2,ownership_proved=False),
        final_cut_cpu=0xC2CF55,production_approval=False,native_execution=False,sidecar_publication=False,
        preview_patch_installed=False,evidence_level='fixed-private-source-construction-only')


def validate_manifest(manifest):
    need(type(manifest) is dict,'exact shadow manifest')
    snapshot=inputs();target=derive(snapshot)
    exact(manifest,template(snapshot,target,manifest.get('output')),'fixed shadow manifest mismatch')
    return dict(status='metadata-valid',schema=SCHEMA,manifest_sha256=sha(encoded(manifest)),production_approval=False)


def audit_images(manifest,source,target):
    snapshot=inputs();expected=derive(snapshot)
    need(type(source) is bytes and source==snapshot['source'],'exact accepted parent image')
    need(type(target) is bytes and target==expected,'exact positioned shadow image')
    exact(manifest,template(snapshot,expected,manifest.get('output')),'fixed shadow manifest mismatch')
    cursor=changed=0;inverse=bytearray(target)
    for row in manifest['sections']:
        start,end=row['file_start'],row['file_start']+row['bytes']
        need(start>=cursor and source[cursor:start]==target[cursor:start],'undeclared or overlapping shadow write')
        need(sha(source[start:end])==row['preimage_sha256'] and sha(target[start:end])==row['sha256'],'exact shadow section bytes')
        count=sum(a!=b for a,b in zip(source[start:end],target[start:end]));need(count==row['changed_bytes'],'per-span changed bytes')
        changed+=count;inverse[start:end]=source[start:end];cursor=end
    need(source[cursor:]==target[cursor:] and bytes(inverse)==source,'complete shadow diff/inverse coverage')
    return dict(status='images-valid',schema=SCHEMA,manifest_sha256=sha(encoded(manifest)),target_sha256=sha(target),
        changed_bytes=changed,declared_sections=len(manifest['sections']),complete_diff_coverage=True,
        inverse_restores_parent=True,production_approval=False,native_execution=False)
