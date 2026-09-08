"""Compose two reviewed mode-cell targets using the unchanged closure-v2 walker.

Only near-call M1/X0/I1 typed stack/control flow is certified conditionally.
Register values, effective addresses, DMA, aliases and whole NMI remain open.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import audit_schala_package_normal_nmi_closure_v2 as closure
import audit_schala_nmi_mode_inputs_v1 as inputs

ROOT=Path(__file__).resolve().parents[1]
ROM=ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
PINS={
 'closure':('tools/audit_schala_package_normal_nmi_closure_v2.py',19110,'c346e0db11dc35a4ecd4e756dcc951ca7a760d3bd52849da55b1f7fe7e7b7e13'),
 'mode_inputs':('tools/audit_schala_nmi_mode_inputs_v1.py',13792,'2372dd5c829f889ca0069227d1d4322726ce2c893c4e55cdf1471a3f0f28614f'),
 'closure_reference':('references/schala_package_normal_nmi_closure_v2.json',321839,'413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242'),
 'mode_input_reference':('references/schala_nmi_mode_inputs_v1.json',138037,'dc715f6726e482a00e649d15252b5ca42f933f82198d8520c78d7867f3932530'),
}
SPANS=(
 ('mode0-wrapper',0xCD09F1,0xCD0ADE,'224aaf43ca64993c9e7b861ee95ebc4b98ccbd1e579abf60f32384712dab37c7'),
 ('mode0-bank-publish',0xCD0AAB,0xCD0AAF,'80cf1d79c04196eb604cf1d960215ebe07fc0b310f71d23871b10076753e144d'),
 ('mode0-temporary-bank',0xCD0AB8,0xCD0ACC,'5af9df71e8507d8d7f9f32e5a4f5c992696a43c3b9281ea7fbb103a654570384'),
 ('mode1-entry-bank',0xCD088D,0xCD08A4,'099e96805e4ac785d4c5b6fef4a1ac9518209607ceaa9f81beac314b312d5e17'),
 ('scroll-dispatch',0xCD06B4,0xCD06BC,'0016098af9a67c4facae3dd092e328de1da7bb6e0c74f4ec5075db44779827d7'),
 ('palette-worker-bank-d-setup',0xFDE39C,0xFDE3AC,'89e9d73273897666c3bb296add7881983b4ca6d1f6b30b2aa5c2c1fb6faf3783'),
 ('palette-worker-restore',0xFDE434,0xFDE437,'55f64236c7b149ae783fca7fff3b03c5d69c1bb4eac32c8c2b5ac670650a6e35'),
)
# Reviewed wrapper-local saved bytes at each direct call, excluding root and
# callee return frames. The sole persistent byte is PHB at CD0AB8; the nested
# PHA/PLB pair is consumed before CD0ABC and PLB CD0ACB later consumes PHB.
CALLS=(
 (0xCD09F1,0xCD09CE,'long',0),(0xCD0AB4,0xC1000F,'long',0),
 (0xCD0ABC,0xCD0AEE,'near',1),(0xCD0ACC,0xCD06C4,'near',0),
 (0xCD0ACF,0xCD0B1E,'near',0),(0xCD0AD2,0xD1F426,'long',0),
 (0xCD0AD6,0xFDFFF7,'long',0),(0xCD0ADA,0xCD0ADE,'near',0),
)
LIMITS={
 'callee_register_value_preservation':False,'d_dbr_return_values_proved':False,
 'nonstack_alias_closure':False,'dma_effects_proved':False,
 'complete_legal_mode_domain_proved':False,'termination_proved':False,
 'asynchronous_entry_proved':False,'whole_nmi_stack_bound':None,
 'production_approval':False,'new_native_execution':False,
}


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')
def serial(value):return (json.dumps(value,indent=2)+'\n').encode('utf-8')
def integer(value,lo,hi,name):require(type(value) is int and lo<=value<=hi,'exact integer '+name)
def cpu(value):return f'${value:06X}'


def read_file(path,expected=None,size=None,maximum=16*1024*1024):
    require(path.is_absolute() and path.resolve(strict=True)==path,'direct absolute path required')
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'regular unaliased source required')
    require(info.st_size<=maximum and (size is None or info.st_size==size),'bounded exact source size')
    with path.open('rb') as stream:raw=stream.read(maximum+1)
    require(len(raw)==info.st_size and len(raw)<=maximum,'source read extent')
    require(expected is None or sha(raw)==expected,'source SHA differs')
    return raw


def identity(path,expected=None,size=None):
    raw=read_file(path,expected,size)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':sha(raw)}


def exact_width(row,entry,kind):
    require(row['entry']==cpu(entry) and row['kind']==kind,'callee namespace/kind differs')
    require(row['entry_m8'] is True and row['entry_x8'] is False and row['entry_irq_masked'] is True,'callee entry widths/I differ')
    require(row['callee_register_value_preservation'] is False and row['nonstack_alias_closure'] is False
            and row['premise_nonstack_writes_do_not_modify_stack_or_saved_status'] is True
            and row['termination_proved'] is False and row['whole_nmi_bound'] is None,'prior scope differs')


def closed(row,entry,kind):
    exact_width(row,entry,kind)
    require(row['status']=='closed-direct-stack-width-control-flow' and row['frontier'] is None,'callee is not closed')
    require(row['return_width_states'] and all(type(x) is dict and set(x)=={'site','m8','x8','irq_masked'}
        and x['m8'] is True and x['x8'] is False and x['irq_masked'] is True for x in row['return_width_states']),
        'callee return widths/I differ')
    integer(row['maximum_additional_bytes_below_callee_entry'],0,512,'callee added stack')
    integer(row['maximum_counted_bytes_including_root_call_frame'],0,515,'callee total stack')
    require(row['maximum_counted_bytes_including_root_call_frame']==row['maximum_additional_bytes_below_callee_entry']+(2 if kind=='near' else 3),
            'callee call frame counted incorrectly')


def compose(mode0,mode12,prior):
    """Independent arithmetic over certified metadata; no native provenance."""
    closed(mode0,0xCD09F1,'near');exact_width(mode12,0xCD088D,'near')
    require(mode0['return_width_states']==[{'site':'$CD0ADD','m8':True,'x8':False,'irq_masked':True}],'mode0 sole return differs')
    expected_calls=[{'site':cpu(s),'target':cpu(t),'kind':k} for s,t,k,_ in CALLS]
    require([x for x in mode0['direct_calls'] if 0xCD09F1<=int(x['site'][1:],16)<0xCD0ADE]==expected_calls,'exact wrapper direct-call inventory')
    rows=[]
    for site,target,kind,persistent in CALLS:
        candidates=[r for r in prior if r['entry']==cpu(target) and r['kind']==kind
                    and r['entry_m8'] is True and r['entry_x8'] is False]
        require(len(candidates)==1,'missing/duplicate exact prior callee')
        r=candidates[0];closed(r,target,kind)
        depth=r['maximum_additional_bytes_below_callee_entry'];frame=3 if kind=='long' else 2
        rows.append({'site':cpu(site),'target':cpu(target),'kind':kind,
            'persistent_wrapper_bytes':persistent,'callee_call_frame_bytes':frame,
            'reused_callee_additional_bytes':depth,'composed_additional_below_mode_entry':persistent+frame+depth,
            'prior_callee_metadata_sha256':sha(canonical(r))})
    composed=max([2]+[x['composed_additional_below_mode_entry'] for x in rows])
    require(mode0['maximum_additional_bytes_below_callee_entry']==composed,'full walk/composition disagree')
    frontier=mode12['frontier']
    require(mode12['status']=='open-frontier' and type(frontier) is dict
        and frontier['category']=='indexed-jump-dispatch' and frontier['site']=='$CD06B9','mode12 exact open frontier')
    state=frontier['incoming_width_state']
    require(type(state) is dict and set(state)=={'m8','x8','irq_masked'}
        and state['m8'] is True and state['x8'] is False and state['irq_masked'] is True,'frontier width/I differs')
    integer(frontier['counted_stack_bytes_at_frontier'],0,512,'frontier stack')
    require(frontier['counted_stack_bytes_at_frontier']==4 and frontier['active_call_return_sites']==[
        {'return':'abstract-caller','kind':'near'},{'return':'$CD092C','kind':'near'}],'frontier typed frames differ')
    require(mode12['maximum_additional_bytes_below_callee_entry'] is None
        and mode12['maximum_counted_bytes_including_root_call_frame'] is None
        and mode12['return_width_states']==[],'open frontier must not acquire a bound/return')
    integer(mode12['exploratory_observed_local_peak_not_a_bound'],0,512,'open traversal local peak')
    return {'mode0_wrapper_components':rows,'mode0_local_noncall_peak_bytes':2,
        'mode0_composed_additional_below_entry':composed,
        'mode0_conditional_total_including_indexed_near_frame':composed+2,
        'mode0_full_walk_matches_composition':True,
        'mode0_sole_return':'$CD0ADD','mode12_first_frontier':'$CD06B9',
        'mode12_frontier_counted_stack_bytes':4,
        'mode12_traversal_local_peak_explicitly_not_a_bound':mode12['exploratory_observed_local_peak_not_a_bound'],
        'mode12_additional_stack_bound':None,**LIMITS}


def audit(rom,prior):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(address,n):
        require(type(address) is int and type(n) is int and n>0 and 0xC00000<=address and address+n<=0x1000000,'canonical read bounds')
        return rom[address-0xC00000:address-0xC00000+n]
    spans=[]
    for name,start,end,digest in SPANS:
        raw=read(start,end-start);require(sha(raw)==digest,'named span drift')
        spans.append({'name':name,'start':cpu(start),'end_exclusive':cpu(end),'size':len(raw),'sha256':digest})
    for site,target,kind,_ in CALLS:
        raw=read(site,4 if kind=='long' else 3)
        require(raw[0]==(0x22 if kind=='long' else 0x20)
            and int.from_bytes(raw[1:],'little')==(target if kind=='long' else target&65535),'wrapper call encoding')
    # Explicit original metadata recipes, checked against canonical opcodes.
    # No copied ROM payload is distributed.
    stack_sites=((0xCD0AAD,0x48),(0xCD0AAE,0xAB),(0xCD0AB8,0x8B),
        (0xCD0ABA,0x48),(0xCD0ABB,0xAB),(0xCD0ACB,0xAB),(0xCD0ADD,0x60))
    require(all(read(site,1)[0]==opcode for site,opcode in stack_sites),'wrapper stack recipe drift')
    results=[closure.walk_direct(read,entry,'near',entry_m8=True,entry_x8=False) for entry in (0xCD09F1,0xCD088D)]
    composition=compose(*results,prior['direct_callee_contracts'])
    require(composition['mode0_composed_additional_below_entry']==12
        and composition['mode12_traversal_local_peak_explicitly_not_a_bound']==10,'reviewed traversal identities differ')
    return {'schema':'project-epoch-nmi-mode-body-composition-v1','date':'2026-09-08',
        'evidence_level':'verified-static','canonical_rom':{'size':len(rom),'sha256':ROM_SHA},
        'scope':'exact two near-call targets of three reviewed physical NMI mode cells; unchanged closure-v2 walker',
        'selected_cells':[{'mode':m,'target':cpu(t),'legal_or_reachable_input_proved':False}
                          for m,t in ((0,0xCD09F1),(1,0xCD088D),(2,0xCD088D))],
        'named_spans':spans,'conditional_target_walks':results,'composition':composition,
        'register_value_obligations':[
            'Mode0 publishes DBR7E with PHA/PLB, then uses TDC in temporary-bank setup; values require a separate D/DBR proof.',
            'The palette worker saves D/DBR, installs D0500, and later pulls D/DBR; typed stack balance does not itself prove physical saved-value integrity.',
            'Mode12 also publishes DBR7E before its open scroll frontier; incoming hidden B and CA92 domain there remain unproved.',
            'A/X/Y values and flags beyond M/X/I are not preserved by the closure contract; no source caller ABI is silently inferred.'],
        'premises':[
            'Native M1/X0/I1 near entry with an exact two-byte typed return frame.',
            'Ordinary writable stack and no nonstack write, DMA effect or alias changes a saved frame/status/control-flow input outside the abstract branch overapproximation.',
            'No intervening asynchronous handler or stack-pointer reassignment; no physical SP ownership is established.',
            'All conditional branches are overapproximated; finite traversal is not a termination or timing proof.',
            'The local wrapper-save counts are reviewer-encoded composition over exact pinned source and prior callee contracts.'],
        **LIMITS}


def collect():
    before={key:identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    own={'auditor':identity(Path(__file__).resolve()),'tests':identity(ROOT/'tests/test_schala_nmi_mode_bodies_v1.py')}
    require(Path(closure.__file__).resolve()==ROOT/PINS['closure'][0]
        and Path(inputs.__file__).resolve()==ROOT/PINS['mode_inputs'][0],'imported dependency paths')
    rom=read_file(ROM,ROM_SHA,0x400000)
    prior=closure.audit(rom)
    require(serial(prior)==read_file(ROOT/PINS['closure_reference'][0],PINS['closure_reference'][2]),'preserved closure does not reproduce')
    mode_input=inputs.collect()
    require(serial(mode_input)==read_file(ROOT/PINS['mode_input_reference'][0],PINS['mode_input_reference'][2]),'preserved mode inputs do not reproduce')
    require(mode_input['reviewed_three_cell_targets']==['CD09F1','CD088D','CD088D']
        and mode_input['complete_legal_mode_domain_proved'] is False,'reviewed mode-cell relation differs')
    report=audit(rom,prior)
    after={key:identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    require(before==after and own=={'auditor':identity(Path(__file__).resolve()),
        'tests':identity(ROOT/'tests/test_schala_nmi_mode_bodies_v1.py')},'composition source drift')
    report.update(source_identities=before,**own,
        reused_closure_source_identities=prior['source_identities'],
        reused_primary_cpu_sources=prior['primary_instruction_sources'],
        reused_mode_input_sources=mode_input['sources'],
        reproduce=['python','-B','tools/audit_schala_nmi_mode_bodies_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    return report


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
