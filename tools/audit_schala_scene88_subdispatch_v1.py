"""Conditional scene-byte88 dispatch, return values and exact call-frame sum.

No legal parameter domain is inferred from four physical table cells. The
fourth target deliberately returns hidden B=FF, so this is not a B0 loop ABI.
All source is original analysis; the canonical ROM is read only and private.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_scene_handler_closure_v1 as control
import audit_schala_scene_handler_values_v1 as values
import audit_schala_nmi_mode_bodies_v1 as io

ROOT=Path(__file__).resolve().parents[1]
ROM=control.ROM
PINS={
 'control_source':('tools/audit_schala_scene_handler_closure_v1.py',24705,'2c8de06dea25a35971143bf6a8c868aea1996a6ab6a8de26fa4b5a12c9ade71d'),
 'control_reference':('references/schala_scene_handler_closure_v1.json',1029264,'ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a'),
 'value_source':('tools/audit_schala_scene_handler_values_v1.py',21359,'b92e5ff6534cb6383754753fa484ac6c4e8d38fab68e6645d207db9e47796610'),
 'value_reference':('references/schala_scene_handler_values_v1.json',376981,'cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543'),
 'cpu_source':('private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h',27673,'9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd'),
}
TARGETS=(0xD1FCF4,0xD1FC38,0xD1FC96,0xD1FBDA)
RETURNS=((0xD1FD3B,0xD1FD7D),(0xD1FC69,0xD1FC95),(0xD1FCC7,0xD1FCF3),(0xD1FC0B,0xD1FC37))
SPANS=(
 ('scene-prefix-and-return',0xCD29DA,0xCD29E3,'46f485f960f266f3ab0674af0d6a9075a6cef7491e187fbef5b4ff7f4796b2a6'),
 ('indexed-near-wrapper',0xD1FBCE,0xD1FBD2,'f9f7c9ab15393fc9c209122951c96635e9f59cc989a9d8a6030f450b23c1ce79'),
 ('four-reviewed-physical-cells',0xD1FBD2,0xD1FBDA,'7a2ce6fdeb7921190edfaaa80997f47c2cef8716c9e075fcb398848c9e2eff76'),
 ('four-target-body-union',0xD1FBDA,0xD1FD7E,'104ee301bec1645213137d5163c2ed68581adf59a90cc3cf4bc989d62e9c30c6'),
)
RECIPE=((0xCD29DA,0xA7,2,0x40),(0xCD29DC,0x0A,1,0),(0xCD29DD,0xAA,1,0),
 (0xCD29DE,0x22,4,0xD1FBCE),(0xCD29E2,0x60,1,0),
 (0xD1FBCE,0xFC,3,0xFBD2),(0xD1FBD1,0x6B,1,0))
SEMANTICS=((409,425,'JSL pushes caller PBR and final-operand return word'),
 (446,461,'indexed JSR pushes its own word and reads the table in PBR'),
 (479,500,'RTL and RTS consume their exact frame and increment return PC'),
 (626,633,'M8 accumulator ASL preserves hidden B'),
 (1058,1061,'TAX width follows X flag, not accumulator width'))
LIMITS={'legal_parameter_or_scene_stream_domain_proved':False,
 'input_pointer_or_parameter_memory_proved':False,'selected_body_memory_alias_closure':False,
 'dma_or_asynchronous_interference_proved':False,'global_scene_return_b0_proved':False,
 'runtime_reachability_of_parameter3_proved':False,'vanilla_runtime_bug_proved':False,
 'termination_or_timing_proved':False,'whole_nmi_stack_bound':None,
 'new_native_execution':False,'production_approval':False}
require=io.require
sha=io.sha
serial=io.serial


def parameter_contract(parameter,hidden_b=0):
    for value,name in ((parameter,'parameter'),(hidden_b,'hidden B')):
        require(type(value) is int and 0<=value<=255,'exact byte '+name)
    index=(hidden_b<<8)|((parameter<<1)&255)
    pointer=(0xFBD2+index)&65535
    selected=hidden_b==0 and (parameter&127)<4
    return {'parameter':parameter,'hidden_b':hidden_b,'computed_x':index,
        'pointer_byte_addresses':[0xD10000|pointer,0xD10000|((pointer+1)&65535)],
        'among_four_reviewed_cells':selected,'selected_ordinal':parameter&127 if selected else None,
        'parameter_bit7_discarded':True,'hidden_b_preserved':True}


def validate_target(ordinal,c,v):
    require(type(ordinal) is int and 0<=ordinal<4,'exact target ordinal')
    target=TARGETS[ordinal];expected_sites=[f'${a:06X}' for a in RETURNS[ordinal]]
    io.closed(c,target,'near')
    for name,want in (('maximum_additional_bytes_below_callee_entry',0),
                      ('maximum_counted_bytes_including_root_call_frame',2)):
        require(type(c[name]) is int and c[name]==want,'exact selected target stack count')
    expected_width=[{'site':p,'m8':True,'x8':False,'irq_masked':True} for p in expected_sites]
    require(c['return_width_states']==expected_width and c['direct_calls']==[],
            'selected target return widths or calls differ')
    require(v['entry']==f'${target:06X}' and v['kind']=='near','selected value target differs')
    for name,want in (('entry_b',0),('entry_d',0),('entry_dbr',126)):
        require(type(v[name]) is int and v[name]==want,'exact selected value entry')
    require(v['entry_m8'] is True and v['entry_x8'] is False and v['entry_irq_masked'] is True,
            'selected value entry widths differ')
    require(v['decoded_byte_intervals']==c['decoded_byte_intervals'] and
            v['instruction_contexts']==c['instruction_contexts'] and
            v['direct_calls']==c['direct_calls'],'selected value/control coverage differs')
    require(v['all_direct_callees_inlined'] is True and v['nonstack_memory_and_dma_effects_proved'] is False
            and v['termination_proved'] is False,'selected target value scope differs')
    low,b=(0,255) if ordinal==3 else (255,0)
    expected=[{'site':site,'kind':'return','m8':True,'x8':False,'irq_masked':True,
        'a_low':low,'b':b,'d':0,'dbr':126,'counted_stack_bytes':0,'frames':[]} for site in expected_sites]
    require(v['ends']==expected,'selected target A/B return differs')
    for row in v['ends']:
        for key in ('a_low','b','d','dbr','counted_stack_bytes'):
            require(type(row[key]) is int,'exact return value integer')
        for key in ('m8','x8','irq_masked'):
            require(type(row[key]) is bool,'exact return width boolean')
    return {'ordinal':ordinal,'physical_cell':f'${0xD1FBD2+ordinal*2:06X}',
        'target':f'${target:06X}','parameter_aliases':[ordinal,ordinal+128],
        'body_returns':expected_sites,'body_additional_stack_bytes':0,
        'return_a':(b<<8)|low,'return_b':b,'return_d':0,'return_dbr':126,
        'return_m8':True,'return_x8':False,'return_irq_masked':True,
        'control_contract_sha256':sha(io.canonical(c)),
        'value_contract_sha256':sha(io.canonical(v))}


def compose_frames(rows):
    require(type(rows) is list and len(rows)==4,'four reviewed target contracts required')
    for ordinal,row in enumerate(rows):
        require(type(row['ordinal']) is int and row['ordinal']==ordinal and
            row['target']==f'${TARGETS[ordinal]:06X}','target order differs')
        require(type(row['body_additional_stack_bytes']) is int and row['body_additional_stack_bytes']==0,
                'exact body depth required')
        for key,want in (('return_a',0xFF00 if ordinal==3 else 0x00FF),
                         ('return_b',255 if ordinal==3 else 0),('return_d',0),('return_dbr',126)):
            require(type(row[key]) is int and row[key]==want,'target return register contract differs')
        require(row['return_m8'] is True and row['return_x8'] is False and row['return_irq_masked'] is True,
                'target return width contract differs')
    return {'existing_scene_near_frame_bytes':2,
        'scene_jsl':{'site':'$CD29DE','target':'$D1FBCE','frame_bytes':3,
            'saved_pbr':0xCD,'saved_return_word':0x29E1,'resumed_pc':'$CD29E2'},
        'wrapper_indexed_jsr':{'site':'$D1FBCE','frame_bytes':2,
            'saved_return_word':0xFBD0,'resumed_pc':'$D1FBD1','target_pbr':0xD1},
        'maximum_additional_bytes_below_scene_handler_entry':5,
        'maximum_bytes_including_existing_scene_near_frame':7,
        'continuation_instructions':['$D1FBD1 RTL','$CD29E2 RTS'],
        'continuation_changes_a_b_d_dbr_or_widths':False,
        'parameter3_retains_bff_through_scene_return':True,
        'global_scene_return_b0_proved':False}


def audit(rom,census):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==control.ROM_SHA,'canonical ROM identity')
    def read(a,n):
        require(type(a) is int and type(n) is int and n>0 and 0xC00000<=a<a+n<=0x1000000,'canonical read bounds')
        return rom[a-0xC00000:a-0xC00000+n]
    parent=[r for r in census['open_frontiers'] if r['entry']=='$CD29DA']
    require(len(parent)==1 and parent[0]['commands']==[0x88] and parent[0]['full_bound'] is None,
            'preserved scene88 parent differs')
    frontier=parent[0]['frontier']
    require(frontier['category']=='indexed-call-dispatch' and frontier['site']=='$D1FBCE'
        and type(frontier['counted_stack_bytes_at_frontier']) is int
        and frontier['counted_stack_bytes_at_frontier']==5,'preserved indexed call frontier differs')
    require(frontier['active_call_return_sites']==[{'return':'abstract-caller','kind':'near'},
        {'return':'$CD29E2','kind':'long'}],'preserved active call frames differ')
    spans=[]
    for name,start,end,digest in SPANS:
        raw=read(start,end-start);require(sha(raw)==digest,'named canonical span differs')
        spans.append({'name':name,'start':f'${start:06X}','end_exclusive':f'${end:06X}',
                      'size':len(raw),'sha256':digest})
    instructions=[]
    for pc,opcode,size,operand in RECIPE:
        raw=read(pc,size)
        require(raw[0]==opcode and int.from_bytes(raw[1:],'little')==operand,'exact prefix/wrapper recipe differs')
        instructions.append({'site':f'${pc:06X}','size':size,'sha256':sha(raw)})
    rows=[];controls=[];projections=[]
    for i,target in enumerate(TARGETS):
        require(0xD10000|int.from_bytes(read(0xD1FBD2+2*i,2),'little')==target,'physical target cell differs')
        c=control.walk_direct(read,target,'near')
        v=values.value_walk(read,target,'near',entry_b=0,entry_dbr=126)
        rows.append(validate_target(i,c,v));controls.append(c);projections.append(v)
    algebra=[];selected=0
    for b in range(256):
        for p in range(256):
            row=parameter_contract(p,b)
            require(row['computed_x']==256*b+2*(p%128),'independent index arithmetic')
            pointer=(0xFBD2+256*b+2*(p%128))%65536
            require(row['pointer_byte_addresses']==[0xD10000+pointer,0xD10000+pointer+1],
                    'even physical pointer words cannot straddle bank boundary')
            selected+=row['among_four_reviewed_cells']
            algebra.append((b,p,row['computed_x'],pointer))
    require(selected==8,'exact reviewed parameter aliases')
    escaped=parameter_contract(4)
    escaped['pointed_target']=f"${0xD10000|int.from_bytes(read(0xD1FBDA,2),'little'):06X}"
    escaped['physical_cell_is_occupied_body_start']=True
    escaped['runtime_reachable']=None
    return {'schema':'project-epoch-scene88-conditional-subdispatch-v1','date':'2026-09-08',
        'evidence_level':'verified-static','canonical_rom':{'size':len(rom),'sha256':control.ROM_SHA},
        'scope':'scene byte88, conditional native B0/D0/DBR7E/M1/X0/I1 and (parameter&7F)<4',
        'namespace':'scene stream command only; no Schala action or package-selector association',
        'preserved_parent_frontier':parent[0],'named_spans':spans,'exact_instruction_recipes':instructions,
        'arithmetic_checks':len(algebra),'arithmetic_projection_sha256':sha(io.canonical(algebra)),
        'b0_physical_word_starts':128,'arbitrary_b_physical_word_starts':32768,
        'reviewed_parameter_aliases':[0,1,2,3,128,129,130,131],
        'first_escaped_b0_example':escaped,'selected_targets':rows,
        'control_contracts':controls,'value_contracts':projections,'conditional_frame_composition':compose_frames(rows),
        'return_b_by_reviewed_ordinal':[0,0,0,255],
        'premises':['Native near entry with B0/D0/DBR7E and M1/X0/I1; parameter&7F is below4.',
            'Ordinary writable stack and no CPU/DMA/asynchronous alias changes saved frames or canonical code.',
            'Parameter pointer, target write addresses, data lifetime and global legal producer domain remain unresolved.',
            'The counterexample is a conditional return ABI, not evidence that parameter3 occurs in a live script.'],**LIMITS}


def collect():
    before={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()}
    own_paths=[Path(__file__).resolve(),ROOT/'tests/test_schala_scene88_subdispatch_v1.py']
    own=[io.identity(p) for p in own_paths]
    require(Path(control.__file__).resolve()==ROOT/PINS['control_source'][0] and
        Path(values.__file__).resolve()==ROOT/PINS['value_source'][0],'exact imported dependency paths')
    c=control.collect();v=values.collect()
    for key,value in (('control_reference',c),('value_reference',v)):
        path,size,digest=PINS[key]
        require(serial(value)==io.read_file(ROOT/path,digest,size),'accepted prerequisite does not reproduce: '+key)
    inherited=list(c['source_identities'].values())+c['reused_closure_sources']+list(c['reused_scene_sources'].values())
    inherited+=c['primary_semantics']['sources']+list(v['prerequisites'].values())+v['source_identities']+v['reused_underlying_source_identities']
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited source identity')
        expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/path,digest) for path,digest in sorted(expected.items())]
    result=audit(io.read_file(ROM,control.ROM_SHA,0x400000),c)
    source=ROOT/PINS['cpu_source'][0];lines=source.read_bytes().splitlines(keepends=True)
    primary=[]
    for first,last,meaning in SEMANTICS:
        raw=b''.join(lines[first-1:last]);require(raw,'primary source span is empty')
        primary.append({'source':before['cpu_source'],'first_line':first,'last_line_inclusive':last,
            'size':len(raw),'sha256':sha(raw),'interpretation':meaning,
            'url':f'https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L{first}'})
    require(before=={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()}
        and own==[io.identity(p) for p in own_paths],'direct source changed during audit')
    require(transitive==[io.identity(ROOT/path,digest) for path,digest in sorted(expected.items())],
            'inherited source changed during audit')
    result.update(prerequisites=before,source_identities=own,transitive_source_identities=transitive,
        primary_semantics=primary,reproduce=['python','-B','tools/audit_schala_scene88_subdispatch_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
