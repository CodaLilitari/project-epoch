"""Fixed private 85-byte staging-preservation wrapper and complete image audit.

The previous installed image is reconstructed from its frozen v1 recipe. Old
guard identities resolve only through the separate pinned historical adapter.
This contract admits four exact private spans, never production allocations.
"""
from pathlib import Path
from types import ModuleType
import copy
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
PACKET='private/research/pc07_preserved_save_table_builder_v1_20261014/'
DESIGN_DIR='private/research/pc07_preserved_save_table_design_20261014/'
WRAPPER_DIR='private/research/pc07_save_staging_preservation_20261014/'
SCHEMA='project-epoch-private-preserved-save-table-intents-v1'
OWNER='pc07-private-preserved-save-table-wrapper-v1'
SIZE=0x800000
SOURCE_SHA='e795c34f8680b45a99f86b657e23066957e4816a481a38099b20be10bfef8908'
TARGET_SHA='9c8993158843e3f4f2e7d8bc28ba7a2b4b6c6c60834c7414755a110865dff364'
HELPER_START=0x442100
GUARD_INTENT='validate_pc07_preserved_save_table_manifest'
GUARD_DIFF='audit_pc07_preserved_save_table_images'
BASELINE={'path':PACKET+'historical_table_baseline_v1.py','bytes':17548,'sha256':'4a64babd871f4c5258d8044c1f7af696609b497efdd137f5e5e40af1effc1f91'}
BASELINE_REPORT={'path':PACKET+'historical_baseline_v1.json','bytes':32935,'sha256':'0f620e5b883d87d8c0d6534d78546447fea6b56165d807633c1047b71d2d3f01'}
GUARD={'path':'tools/validate_rom_write_intents.py','bytes':43651,'sha256':'d51cb06e69757bdaec6304f5a44ef1709cb08425d2d9c6c926c0320c2b71f2c4'}
PRIOR={'path':'private/research/pc07_installed_save_table_v1_20261013/contract_v1.py','bytes':10761,'sha256':'de152d66010b624ba14d498101466916a2508d60e4d885a845747b6aa3bce9e3'}
DESIGN={'path':DESIGN_DIR+'installation_design_v1.json','bytes':12511,'sha256':'422ad0d3ed4f03637c36a7e31a2ce9596937eb0f183d77252427770eb78d9ce2'}
ROOT_REPORT={'path':DESIGN_DIR+'root_verification_v1.json','bytes':805,'sha256':'d8a68eacb73940cc7209e99aa9fd34eef9b6eef2826af7caef374960b588b0f1'}
ROOT_SOURCE={'path':DESIGN_DIR+'root_verify_v1.py','bytes':3783,'sha256':'e9fae2973c2c4ea92efec5bd7ae8ee26527f6f1fa39b4c9082929c43fd0b6da5'}
CHECK2={'path':WRAPPER_DIR+'source_check_v2.json','bytes':40548,'sha256':'032443411a59e8b9b06ac684c5267b1f797e0756721d067ed779ede84ff527db'}
COMPONENT={'path':WRAPPER_DIR+'assembly_v1/component.bin','bytes':85,'sha256':'99e7372160bedd49f504fb2b678ce677c55ab823e459433d929a78b1dce36f2b'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def historical():
    # Bootstrap validates the one immutable adapter before importing its reader.
    import pc07_private_expanded_write_contract_v1 as field
    path,info=field._inspect_path(field._root(ROOT),Path(BASELINE['path']).parts)
    import stat
    if info is None or not stat.S_ISREG(info.st_mode):raise ValueError('fixed historical adapter missing')
    raw=path.read_bytes()
    if len(raw)!=BASELINE['bytes'] or sha(raw)!=BASELINE['sha256']:raise ValueError('fixed historical adapter drift')
    name='_epoch_preserved_save_historical_v1'
    if name not in sys.modules:
        module=ModuleType(name);module.__file__=str(path);sys.modules[name]=module
        exec(compile(raw,str(path),'exec'),module.__dict__)
    return sys.modules[name]


def read_pin(row):return historical().read_exact(row)


def load_exact(name,row):
    raw=read_pin(row)
    if name not in sys.modules:
        module=ModuleType(name);module.__file__=str(ROOT/row['path']);sys.modules[name]=module
        exec(compile(raw,module.__file__,'exec'),module.__dict__)
    return sys.modules[name]


def prior():return load_exact('_epoch_preserved_save_frozen_table_v1',PRIOR)


def historical_mapping():
    h=historical();h.validate_mapping(h.ARCHIVE_MAPPING);h.read_historical_row(h.GUARD_ROLE)
    return copy.deepcopy(h.ARCHIVE_MAPPING)


def verify_guard_extension():
    h=historical();old=h.read_exact(h.ARCHIVE_ROW);new=read_pin(GUARD)
    start=new.index(b'def validate_pc07_preserved_save_table_manifest(')
    end=new.index(b'def main() -> int:',start)
    if new[:start]+new[end:]!=old:raise ValueError('current guard is not exact two-forwarder additive extension')
    return {'archived_guard':copy.deepcopy(h.ARCHIVE_ROW),'current_guard':GUARD,
            'old_bytes_preserved':True,'added_apis':[GUARD_INTENT,GUARD_DIFF]}


def design():
    h=historical();plan=json.loads(read_pin(DESIGN))
    for row in plan['sources']:h.read_historical_row(row)
    report=json.loads(read_pin(ROOT_REPORT));read_pin(ROOT_SOURCE)
    if (report['design_sha256']!=DESIGN['sha256'] or report['prospective_target_sha256']!=TARGET_SHA
            or report['changed_bytes']!=95 or report['source_reconstructed'] is not True):
        raise ValueError('root design receipt mismatch')
    return plan


def source_rows():
    h=historical();rows={r['path']:r for r in prior().source_rows()}
    fixed=[BASELINE,BASELINE_REPORT,PRIOR,DESIGN,ROOT_REPORT,ROOT_SOURCE,CHECK2,COMPONENT,h.ARCHIVE_ROW]
    planned=design()
    for row in planned['sources']:
        if row['path']==h.GUARD_ROLE['path']:
            h.exact(row,h.GUARD_ROLE,'historical design guard');row=h.ARCHIVE_ROW
        fixed.append(row)
    # Close the unchanged original component's source/assembly provenance.
    manifest=json.loads(h.read_exact(next(r for r in planned['sources'] if r['path']==WRAPPER_DIR+'manifest_v1.json')))
    for row in manifest['sources_and_outputs']:fixed.append({**row,'path':WRAPPER_DIR+row['path']})
    checked=json.loads(read_pin(CHECK2));fixed.append(checked['v2_source'])
    if checked['positive_cases']!=4201 or checked['mutation_status_cases']!=224 or checked['native_execution'] is not False:
        raise ValueError('preserved supplementary source-check scope')
    for row in fixed:
        h.read_exact(row)
        if row['path'] in rows:h.exact(rows[row['path']],row,'conflicting source pin')
        rows[row['path']]=row
    read_pin(GUARD);rows[GUARD['path']]=GUARD
    return sorted(rows.values(),key=lambda r:r['path'])


def allocation_check():
    p=prior();inherited=p.allocation_check()
    end=HELPER_START+85
    occupied=[(r['file_start'],r['file_start']+r['bytes']) for r in inherited]
    occupied += [(s,s+n) for s,n in ((0xFFDC,4),(0x3FFA1A,12),(0x3FFA4F,3),(0x40FFDC,4),(0x442000,50))]
    if any(max(HELPER_START,a)<min(end,b) for a,b in occupied):raise ValueError('wrapper overlaps inherited named span')
    scaffold=p.parent().scaffold
    if HELPER_START>>16!=(end-1)>>16 or any(scaffold.exhirom_snes_to_file(a)!=a for a in (HELPER_START,end-1)):
        raise ValueError('fixed one-bank expanded wrapper mapping')
    if HELPER_START!=0x442100:raise ValueError('fixed wrapper allocation address')


def derive_target(source):
    if type(source) is not bytes or len(source)!=SIZE or sha(source)!=SOURCE_SHA:raise ValueError('exact installed ten-region source required')
    plan=design();allocation_check();component=read_pin(COMPONENT)
    target=bytearray(source)
    for row in plan['proposed_complete_diff']['sections']:
        start,size=row['file_start'],row['bytes'];before=bytes.fromhex(row['preimage_hex']);after=bytes.fromhex(row['payload_hex'])
        if source[start:start+size]!=before or len(after)!=size:raise ValueError('exact wrapper delta preimage/extent')
        if row['id']==OWNER and after!=component:raise ValueError('original wrapper component mismatch')
        target[start:start+size]=after
    if (len(target)!=SIZE or sha(target)!=TARGET_SHA or sum(target)&65535!=0xB765
            or target[0xFFDC:0xFFE0]!=bytes.fromhex('9a4865b7') or target[:65536]!=target[0x400000:0x410000]):
        raise ValueError('exact wrapper target/checksum/mirror')
    return bytes(target)


def expected():
    # Frozen v1 recipe has no mutable live-guard pin. No old APIs are repinned.
    source=prior()._expected()[1]
    return source,derive_target(source)


def template(source,target,output):
    p=prior();p.parent().prior.field._validate_destination(output,{'size':SIZE,'sha256':TARGET_SHA},ROOT)
    plan=design()
    sections=[{**row,'owner':OWNER} for row in plan['proposed_complete_diff']['sections']]
    return {'schema':SCHEMA,'mode':'private-preserved-save-table-only',
        'source':{'kind':'exact-installed-ten-region-diagnostic','bytes':SIZE,'sha256':SOURCE_SHA},
        'target':{'bytes':SIZE,'sha256':TARGET_SHA},'output':output,'sections':sections,
        'allocation':plan['allocation'],'entry_contract':plan['entry_contract'],
        'stack_admission':plan['stack_admission'],'occupied_tail_admission':plan['occupied_tail_admission'],
        'runtime_requirements':plan['bounded_runtime_requirements'],'design':DESIGN,
        'historical_baseline':BASELINE_REPORT,'historical_guard_mapping':historical_mapping(),
        'baseline_reproduction_required_before_emission':True,
        'evidence_level':'fixed-private-source-construction-only','native_execution':False,
        'production_approval':False,'post_C2CF55_continuation_approved':False,
        'interrupt_admission':False,'physical_stack_ownership_proved':False,
        'compatible_PC07_persistence':False,'sidecar_SHA_load_preview_implemented':False}


def validate_manifest(manifest):
    if type(manifest) is not dict:raise ValueError('exact preserved-table manifest required')
    source_rows();verify_guard_extension();source,target=expected()
    historical().exact(manifest,template(source,target,manifest.get('output')),'preserved-table-manifest')
    return {'status':'metadata-valid','schema':SCHEMA,'production_approval':False,
            'manifest_sha256':sha(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())}


def audit_images(manifest,source,target):
    report=validate_manifest(manifest);expected_source,expected_target=expected()
    if type(source) is not bytes or type(target) is not bytes or source!=expected_source or target!=expected_target:
        raise ValueError('complete wrapper image differs from exact fixed recipe')
    cursor=changed=0;inverse=bytearray(target)
    for row in manifest['sections']:
        start,end=row['file_start'],row['file_start']+row['bytes']
        if start<cursor or source[cursor:start]!=target[cursor:start]:raise ValueError('overlap or undeclared wrapper image difference')
        if sha(source[start:end])!=row['preimage_sha256'] or sha(target[start:end])!=row['sha256']:raise ValueError('fixed wrapper section identity')
        count=sum(a!=b for a,b in zip(source[start:end],target[start:end]))
        if count!=row['changed_bytes']:raise ValueError('per-span changed-byte invariant')
        changed+=count;inverse[start:end]=source[start:end];cursor=end
    if source[cursor:]!=target[cursor:] or bytes(inverse)!=source or changed!=95:raise ValueError('complete wrapper diff/inverse invariant')
    return {**report,'status':'images-valid','changed_bytes':95,'declared_sections':4,
        'complete_diff_coverage':True,'accepted_image_inverse':True,'target_sha256':TARGET_SHA,
        'native_execution':False,'emission_admission':False,'post_C2CF55_continuation_approved':False}


def build_manifest(source,target,output):
    manifest=template(source,target,output);audit_images(manifest,source,target)
    return manifest
