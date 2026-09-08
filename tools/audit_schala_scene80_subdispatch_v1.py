"""Scene80 pointer/code topology and conditional target census; read-only.

The first 29 physical words precede proved executable source, not a proved
legal parameter domain. The full 128-cell B0 inventory is hypothetical only.
No decoder additions, native execution, ROM output, hook or allocation.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_scene_handler_closure_v1 as handlers
import audit_schala_scene_handler_values_v1 as values
import audit_schala_nmi_mode_bodies_v1 as io

ROOT=Path(__file__).resolve().parents[1]
ROM=handlers.ROM
ROM_SHA=handlers.ROM_SHA
PINS={
 'handler_auditor':('tools/audit_schala_scene_handler_closure_v1.py',24705,'2c8de06dea25a35971143bf6a8c868aea1996a6ab6a8de26fa4b5a12c9ade71d'),
 'handler_reference':('references/schala_scene_handler_closure_v1.json',1029264,'ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a'),
 'value_auditor':('tools/audit_schala_scene_handler_values_v1.py',21359,'b92e5ff6534cb6383754753fa484ac6c4e8d38fab68e6645d207db9e47796610'),
 'value_reference':('references/schala_scene_handler_values_v1.json',376981,'cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543'),
 'annotation':('private/research/ct_disassembly_eeae27a/bank_CD.asm',474851,'0d230620c6accf311c0588e2fefaf3bcc48b0d42575f3745fec3a402a6ca19fb'),
}
PREFIX=0xCD2A4A
TABLE=0xCD2A51
CODE_START=0xCD2A8B
INCBIN_END=0xCD2B27
FIRST_TARGETS=(0xCD2D4A,0xCD2D1F,0xCD2CF5,0xCD2D0C,0xCD2CDC,0xCD2CB3,
 0xCD2C98,0xCD2C8B,0xCD2C7F,0xCD2BFC,0xCD2BD2,0xCD2BA8,0xCD2B69,
 0xCD2B64,0xCD2D44,0xCD2B5C,0xCD2B45,0xCD2B27,0xCD2B12,0xCD2D39,
 0xCD2B05,0xCD2AEF,0xCD2AC6,0xCD2AAA,0xCD2AA5,0xCD2AA1,0xCD2A9C,
 0xCD2A8B,0xCD2A97)
SPANS=(
 ('dispatcher-prefix',PREFIX,TABLE,'6d98dd01fe6b0dd3ece9818b700b0b28dfc32d67e96171a05003405dd73d48bb'),
 ('29-physical-words-before-code',TABLE,CODE_START,'b58d1ac3705ed4861994b16bedb9f7ff1d6e6988151db7f1ce9f80be5517278d'),
 ('first-selected-code-body',CODE_START,0xCD2A97,'45219cbaf86d9ec7d32ac5da7a5e71030779ed78604465b24c407556fd012378'),
 ('annotated-incbin-with-mixed-roles',TABLE,INCBIN_END,'d9e89d094dbe779d1d37572682157793ac327f26a88b861c16ff24ade92f0a5f'),
 ('all-128-b0-physical-pointer-words',TABLE,TABLE+256,'3da62682bf1adbe828ff0e716ec528a97bcf0afe4cd22cb3da26f642390e2494'),
 ('hypothetical-cell35-rti',0xCDC122,0xCDC123,'c3641f8544d7c02f3580b07c0f9887f0c6a27ff5ab1d4a3e29caf197cfc299ae'),
)
LIMITS={'legal_parameter_or_script_producer_domain_proved':False,
 '29_topological_words_are_a_proved_legal_table':False,'107_incbin_words_are_a_proved_legal_table':False,
 'hypothetical_closed_spillover_cells_are_approved_entries':False,
 'input_pointer_lifetime_proved':False,'nonstack_memory_alias_closure':False,
 'dma_effects_proved':False,'global_handler_return_b_proved':False,
 'full_dispatcher_stack_bound':None,'whole_nmi_stack_bound':None,
 'termination_or_timing_proved':False,'production_approval':False,'new_native_execution':False}
require=io.require
sha=io.sha
serial=io.serial
cpu=lambda a:f'${a:06X}'


def prefix_contract(parameter,hidden_b=0):
    for name,v in (('parameter',parameter),('hidden B',hidden_b)):
        require(type(v) is int and 0<=v<=255,'exact byte '+name)
    x=(hidden_b<<8)|((parameter<<1)&255)
    low=((TABLE&65535)+x)&65535
    return {'parameter':parameter,'hidden_b':hidden_b,'final_x':x,
        'pointer_byte_addresses':[0xCD0000|low,0xCD0000|((low+1)&65535)],
        'among_first29_physical_words':hidden_b==0 and parameter%128<29,
        'parameter_bit7_discarded':True,'hidden_b_zero_extension_assumed':False,
        'prefix_stack_bytes':0,'dispatch_jump_adds_frame':False}


def validate_closed(control,value):
    """Compose existing independently typed source and returned value contexts."""
    require(type(control['entry']) is str and len(control['entry'])==7 and
        control['entry'].startswith('$CD'),'exact same-bank near target')
    io.closed(control,int(control['entry'][1:],16),'near')
    extra=control['maximum_additional_bytes_below_callee_entry']
    total=control['maximum_counted_bytes_including_root_call_frame']
    require(type(extra) is int and extra>=0 and type(total) is int and total==extra+2,
        'exact additional/root near stack counts')
    for row in control['return_width_states']:
        require(row['m8'] is True and row['x8'] is False and row['irq_masked'] is True,
            'exact control return widths')
    result=values.classify(value,control)
    require(result['status']=='proved-B0-D0-DBR7E','conditional B0/D0/DBR7E return unproved')
    result.update(additional_bytes=extra,total_including_existing_near_frame=total,
        added_dispatch_jump_frame=0,legal_parameter_reachability_proved=False)
    return result


def code_union(contracts):
    """Require complete decoder coverage of the incbin's 156-byte code suffix."""
    require(type(contracts) is list and len(contracts)==29,'exact first29 target contracts')
    require([row['entry'] for row in contracts]==[cpu(a) for a in FIRST_TARGETS],
        'exact ordered first29 targets')
    covered=set()
    for contract in contracts:
        for row in contract['decoded_byte_intervals']:
            lo=int(row['start'][1:],16);hi=int(row['end_exclusive'][1:],16)
            require(lo<hi,'nonempty decoded interval')
            covered.update(range(max(lo,CODE_START),min(hi,INCBIN_END)))
    expected=set(range(CODE_START,INCBIN_END))
    require(covered==expected,'incbin code suffix coverage has a hole')
    return {'start':cpu(CODE_START),'end_exclusive':cpu(INCBIN_END),'bytes':len(covered),
        'all_bytes_covered_by_first29_selected_target_decodes':True,
        'coverage_is_conditional_source_decoding_not_runtime_execution':True,
        'source_contracts_include_two_explicit_partial_frontiers':True}


def audit(rom,handler_reference):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(p,n):
        require(type(p) is int and type(n) is int and n>0 and 0xC00000<=p<p+n<=0x1000000,'canonical read bounds')
        return rom[p-0xC00000:p-0xC00000+n]
    parent=[r for r in handler_reference['open_frontiers'] if r['entry']==cpu(PREFIX)]
    require(len(parent)==1 and parent[0]['commands']==[0x80] and parent[0]['full_bound'] is None
        and parent[0]['frontier']['site']=='$CD2A4E'
        and parent[0]['frontier']['category']=='indexed-jump-dispatch','preserved parent frontier differs')
    spans=[]
    for name,a,b,pin in SPANS:
        require(sha(read(a,b-a))==pin,'named span differs')
        spans.append({'name':name,'start':cpu(a),'end_exclusive':cpu(b),'size':b-a,'sha256':pin})
    recipe=((PREFIX,0xA7,2,0x40),(PREFIX+2,0x0A,1,0),(PREFIX+3,0xAA,1,0),(PREFIX+4,0x7C,3,0x2A51))
    instructions=[]
    for pc,op,n,operand in recipe:
        raw=read(pc,n);require(raw[0]==op and int.from_bytes(raw[1:],'little')==operand,'prefix recipe differs')
        instructions.append({'site':cpu(pc),'length':n,'sha256':sha(raw)})
    require(sum(x[2] for x in recipe)==7,'complete prefix coverage')
    digest=hashlib.sha256();starts=set();physical=set();b0=set();first=[]
    for b in range(256):
        for p in range(256):
            row=prefix_contract(p,b);x=row['final_x'];addresses=row['pointer_byte_addresses']
            require(x==b*256+(p%128)*2,'independent ASL/TAX algebra differs')
            digest.update(bytes((b,p))+x.to_bytes(2,'little')+b''.join(a.to_bytes(3,'little') for a in addresses))
            starts.add(addresses[0]);physical.update(addresses)
            if b==0:b0.add(addresses[0])
            if row['among_first29_physical_words']:first.append((b,p))
    require(len(starts)==32768 and physical==set(range(0xCD0000,0xCE0000)) and
        b0==set(range(TABLE,TABLE+256,2)),'physical address domain differs')
    require(first==[(0,p) for p in list(range(29))+list(range(128,157))],'first29 arithmetic aliases differ')
    require(prefix_contract(0x57,0xD5)['pointer_byte_addresses']==[0xCDFFFF,0xCD0000],'odd table wrap differs')
    cells=[];controls={};projections={};closed={}
    for i in range(128):
        ptr=TABLE+2*i;raw=read(ptr,2);target=0xCD0000|int.from_bytes(raw,'little')
        cells.append({'physical_index':i,'parameter_aliases':[i,i+128],'pointer':cpu(ptr),
            'pointer_word_sha256':sha(raw),'target':cpu(target),'before_first_code_target':i<29,
            'legal_parameter_reachability_proved':False})
        if target not in controls:
            controls[target]=handlers.walk_direct(read,target,'near')
            if controls[target]['frontier'] is None:
                projections[target]=values.value_walk(read,target,'near',entry_b=0,entry_dbr=126)
                closed[target]=validate_closed(controls[target],projections[target])
    require([int(r['target'][1:],16) for r in cells[:29]]==list(FIRST_TARGETS)
        and min(FIRST_TARGETS)==CODE_START and TABLE+29*2==CODE_START,'29-word topological boundary differs')
    union=code_union([controls[a] for a in FIRST_TARGETS])
    require(read(CODE_START,2)==bytes((0x7B,0xAA)) and cells[29]['target']=='$CDAA7B',
        'first code overlap no longer TDC/TAX')
    first_closed=[i for i in range(29) if FIRST_TARGETS[i] in closed]
    require(first_closed==[i for i in range(29) if i not in (9,13)],'first29 conditional closure set differs')
    first_open=[]
    for i,site,opcode in ((9,0xCD2C07,0x44),(13,0xD1F11D,0x75)):
        row=controls[FIRST_TARGETS[i]]
        require(row['frontier']['category']=='unsupported-opcode' and row['frontier']['site']==cpu(site)
            and read(site,1)[0]==opcode and row['maximum_additional_bytes_below_callee_entry'] is None,
            'preserved first29 frontier differs')
        first_open.append({'physical_index':i,'target':row['entry'],'frontier':row['frontier'],
            'frontier_opcode':opcode,'full_bound':None,'value_return_contract':None})
    closed_cells=[r['physical_index'] for r in cells if int(r['target'][1:],16) in closed]
    require(closed_cells==first_closed+[47,57,58,59,61,62] and len(controls)==116 and len(closed)==32,
        'hypothetical physical census differs')
    counts=Counter(controls[int(r['target'][1:],16)]['frontier']['category'] for r in cells
        if controls[int(r['target'][1:],16)]['frontier'] is not None)
    require(dict(counts)=={'unsupported-opcode':83,'unexpected-rti':1,'overlapping-decode':2,
        'stack-pointer-assignment':5,'return-frame-mismatch':1,'indexed-jump-dispatch':2,'return-kind-mismatch':1},
        'hypothetical frontier census differs')
    require(cells[35]['target']=='$CDC122' and read(0xCDC122,1)[0]==0x40
        and controls[0xCDC122]['frontier']['category']=='unexpected-rti','hypothetical near-frame RTI counterexample differs')
    require(max(closed[a]['additional_bytes'] for a in FIRST_TARGETS if a in closed)==3,'first27 conditional peak differs')
    return {'schema':'project-epoch-scene80-topology-and-conditional-subdispatch-v1','date':'2026-09-08',
        'evidence_level':'verified-static','canonical_rom':{'size':len(rom),'sha256':ROM_SHA},
        'namespace':'scene command80; not Schala action80 or package selector80',
        'scope':'29 physical words before code, 27 conditional returns, two frontiers; secondary hypothetical 128-cell census',
        'preserved_parent_frontier':parent[0],'named_spans':spans,'prefix_instructions':instructions,
        'primary_topology':{'pointer_words_before_first_selected_code':29,'word_span':[cpu(TABLE),cpu(CODE_START)],
            'minimum_first29_selected_target':cpu(CODE_START),'annotated_incbin_span':[cpu(TABLE),cpu(INCBIN_END)],
            'annotated_incbin_bytes':214,'arithmetic_word_count_only':107,'complete_code_suffix':union,
            'first_code_overlap_cell':cells[29],'first_code_instruction_roles':['TDC','TAX'],
            'topology_proves_legal_parameter_extent':False},
        'primary_conditional_returns':{'closed_physical_indices':first_closed,'closed_targets':27,
            'unclosed_targets':first_open,'maximum_additional_for_27_closed_only':3,
            'total_including_existing_near_frame_for_27_closed_only':5,'new_jump_frame':0,
            'all_27_closed_return_b':0,'all_27_closed_return_d':0,'all_27_closed_return_dbr':126,
            'all_29_composed':False,'full_29_target_bound':None},
        'physical_address_geometry':{'all_b_parameter_pairs':65536,'algebra_projection_sha256':digest.hexdigest(),
            'all_b_word_starts':len(starts),'all_b_pointer_bytes':len(physical),'b0_word_starts':128,
            'b0_span':[cpu(TABLE),cpu(TABLE+256)],'first29_b_parameter_aliases':first,
            'odd_base_wrap_example':prefix_contract(0x57,0xD5),'all_b_targets_traced':False},
        'secondary_hypothetical_census':{'scope':'all 128 B0 physical words; no legal-entry or production authority',
            'physical_cells':128,'unique_targets':116,'closed_cells':33,'closed_targets':32,
            'frontier_cells':95,'frontier_targets':84,'frontier_categories_by_cell':dict(counts),
            'closed_spillover_indices':[47,57,58,59,61,62],'full_bound':None,
            'near_frame_incompatible_rti_cell':cells[35],'rti_site':'$CDC122',
            'first_instruction_rti_is_not_a_near_return':True},
        'physical_cells':cells,'target_control_contracts':list(controls.values()),
        'closed_target_value_projections':list(projections.values()),'closed_target_compositions':list(closed.values()),
        'premises':['Native scene near entry M1/X0/I1 with B0/D0/DBR7E and an existing two-byte near frame.',
            'The prefix reads one arbitrary byte through DP40, retains B under M8 ASL, then TAX copies full A under X16.',
            'First29 selection is a conditional topology restriction, not a proved legal parameter or script producer domain.',
            'Ordinary writable stack; no nonstack CPU/DMA alias changes live frames, saved bytes, or canonical code.',
            'No asynchronous architectural register/status change; target source/address lifetimes and memory effects remain open.',
            'All branches are conservatively followed. A closed projection does not prove termination, timing or runtime reachability.',
            'Unsupported source effects remain frontiers; no decoder or value model has been expanded for this packet.'],**LIMITS}


def collect():
    before={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()}
    own={'auditor':io.identity(Path(__file__).resolve()),'tests':io.identity(ROOT/'tests/test_schala_scene80_subdispatch_v1.py')}
    require(Path(handlers.__file__).resolve()==ROOT/PINS['handler_auditor'][0] and
        Path(values.__file__).resolve()==ROOT/PINS['value_auditor'][0],'imported source paths')
    old_handler=handlers.collect();old_value=values.collect()
    for key,report in (('handler_reference',old_handler),('value_reference',old_value)):
        path,size,pin=PINS[key]
        require(serial(report)==io.read_file(ROOT/path,pin,size),'accepted reference no longer reproduces: '+key)
    inherited=(list(old_handler['source_identities'].values())+old_handler['reused_closure_sources']+
        list(old_handler['reused_scene_sources'].values())+old_handler['primary_semantics']['sources']+
        list(old_value['prerequisites'].values())+old_value['source_identities']+
        old_value['reused_underlying_source_identities'])
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited source identity')
        expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/path,pin) for path,pin in sorted(expected.items())]
    result=audit(io.read_file(ROM,ROM_SHA,0x400000),old_handler)
    require(before=={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()} and
        own=={'auditor':io.identity(Path(__file__).resolve()),'tests':io.identity(ROOT/'tests/test_schala_scene80_subdispatch_v1.py')},
        'source changed during collection')
    require(transitive==[io.identity(ROOT/path,pin) for path,pin in sorted(expected.items())],
        'inherited source changed during composition')
    result.update(prerequisites=before,source_identities=own,transitive_source_identities=transitive,
        primary_cpu_sources=old_handler['primary_semantics']['sources'],
        annotation={'commit':'eeae27acdb6565e96d1d796a3d60792c250c0aa1','path':PINS['annotation'][0],
            'lines':[3595,3602],'incbin_extent_is_not_table_extent':True,
            'url':'https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_CD.asm#L3595'},
        reproduce=['python','-B','tools/audit_schala_scene80_subdispatch_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
