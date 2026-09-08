"""Source-only masked scene-opcode-82 dispatch and local return composition.

Scene byte82 is not a Schala action ID or an extended package selector.
The two parameter reads remain independent arbitrary bytes. Only the explicit
B0/D0/DBR7E/M1/X0/I1 entry contract selects this complete eight-target branch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_scene_handler_closure_v1 as handlers
import audit_schala_nmi_scroll_inputs_v1 as values
import audit_schala_nmi_mode_bodies_v1 as io

ROOT=Path(__file__).resolve().parents[1]
ROM=handlers.ROM
ROM_SHA=handlers.ROM_SHA
PINS={
 'handler_auditor':('tools/audit_schala_scene_handler_closure_v1.py',24705,'2c8de06dea25a35971143bf6a8c868aea1996a6ab6a8de26fa4b5a12c9ade71d'),
 'handler_reference':('references/schala_scene_handler_closure_v1.json',1029264,'ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a'),
 'value_auditor':('tools/audit_schala_nmi_scroll_inputs_v1.py',19678,'4153a240d3a1fa750dd0ac67626776e061ceb049f03b9fce54fc08da8e31c686'),
 'value_reference':('references/schala_nmi_scroll_inputs_v1.json',87273,'003bf6be7e686445a8aa0a7bddf36bd8ca35b2fb49aa4d184ec5f3bc15db8013'),
}
TARGETS=(0xCD2E89,0xCD2E78,0xCD2E5E,0xCD2E4D,0xCD2E3C,0xCD2E23,0xCD2E13,0xCD2DFA)
RETURNS=(0xCD2EA1,0xCD2E88,0xCD2E77,0xCD2E5D,0xCD2E4C,0xCD2E3B,0xCD2E22,0xCD2E12)
SPANS=(
 ('parameter-prefix',0xCD2DD6,0xCD2DEA,'0b28214837c2c5943f00c409c5d886efb3865fac8aba8b7898aee3fa71521857'),
 ('complete-b0-selected-cells',0xCD2DEA,0xCD2DFA,'c310cab5e3bb6d1dd76b14ae710da05d5c46a8749003eab48cbe40019db77ad3'),
 ('eight-target-body-union',0xCD2DFA,0xCD2EA2,'5a9e0d716c39304a54ba595f0800be76ba27f359ad2769acc431cc9658aa510c'),
)
PREFIX=((0xCD2DD6,0xA7,2,0x40),(0xCD2DD8,0x29,2,0x1F),(0xCD2DDA,0x1A,1,0),
 (0xCD2DDB,0xAA,1,0),(0xCD2DDC,0x86,2,0x45),(0xCD2DDE,0xA7,2,0x40),
 (0xCD2DE0,0x29,2,0xE0),(0xCD2DE2,0x4A,1,0),(0xCD2DE3,0x4A,1,0),
 (0xCD2DE4,0x4A,1,0),(0xCD2DE5,0x4A,1,0),(0xCD2DE6,0xAA,1,0),
 (0xCD2DE7,0x7C,3,0x2DEA))
LIMITS={'legal_scene_command_or_script_domain_proved':False,'input_pointer_or_parameter_memory_proved':False,
 'two_parameter_reads_required_equal':False,'nonstack_memory_alias_closure':False,
 'target_effective_write_addresses_proved':False,'dma_effects_proved':False,
 'global_handler_return_b_proved':False,'whole_nmi_stack_bound':None,
 'termination_or_timing_proved':False,'production_approval':False,'new_native_execution':False}
require=io.require
sha=io.sha
serial=io.serial


def byte(value,name):require(type(value) is int and 0<=value<=255,'exact byte '+name)


def prefix_contract(first_parameter,second_parameter,hidden_b=0):
    """Exact fixed-prefix algebra; parameter observations need not be equal."""
    for value,name in ((first_parameter,'first parameter'),(second_parameter,'second parameter'),(hidden_b,'B')):byte(value,name)
    count=(first_parameter&0x1F)+1
    stored_x=(hidden_b<<8)|count
    final_x=(hidden_b<<8)|((second_parameter&0xE0)>>4)
    low=(0x2DEA+final_x)&65535
    return {'first_parameter':first_parameter,'second_parameter':second_parameter,'b':hidden_b,
        'stored_dp45_word':stored_x,'stored_dp45_bytes':[stored_x&255,stored_x>>8],
        'final_x':final_x,'pointer_byte_addresses':[0xCD0000|low,0xCD0000|((low+1)&65535)],
        'among_eight_reviewed_cells':hidden_b==0,'new_stack_bytes_in_prefix':0,
        'jump_adds_return_frame':False,'m8':True,'x8':False,'irq_masked':True,'d':0,'dbr':126}


def validate_target(index,control,value):
    require(type(index) is int and 0<=index<8,'exact selected cell index')
    target,ret=TARGETS[index],RETURNS[index]
    io.closed(control,target,'near')
    require(control['maximum_additional_bytes_below_callee_entry']==0 and
        type(control['maximum_additional_bytes_below_callee_entry']) is int and
        control['maximum_counted_bytes_including_root_call_frame']==2 and
        type(control['maximum_counted_bytes_including_root_call_frame']) is int,'target stack bound differs')
    require(control['return_width_states']==[{'site':f'${ret:06X}','m8':True,'x8':False,'irq_masked':True}],
        'target return site/width differs')
    require(value['entry']==f'${target:06X}' and value['kind']=='near' and value['entry_b']==0
        and type(value['entry_b']) is int and value['entry_d']==0 and type(value['entry_d']) is int
        and value['entry_dbr']==126 and type(value['entry_dbr']) is int,'target value entry differs')
    require(value['entry_m8'] is True and value['entry_x8'] is False and value['entry_irq_masked'] is True,
        'target value entry widths differ')
    require(value['decoded_byte_intervals']==control['decoded_byte_intervals'] and
        value['direct_calls']==control['direct_calls']==[],'target value/control source coverage differs')
    require(value['all_direct_callees_inlined'] is True and value['nonstack_memory_and_dma_effects_proved'] is False
        and value['termination_proved'] is False,'target value scope differs')
    expected={'site':f'${ret:06X}','kind':'return','m8':True,'x8':False,'irq_masked':True,
        'a_low':0,'b':0,'d':0,'dbr':126,'counted_stack_bytes':0,'frames':[]}
    require(value['ends']==[expected],'target value return differs')
    for key in ('a_low','b','d','dbr','counted_stack_bytes'):
        require(type(value['ends'][0][key]) is int,'target exact return integer')
    for key in ('m8','x8','irq_masked'):
        require(type(value['ends'][0][key]) is bool,'target exact return boolean')
    return {'cell_index':index,'pointer':f'${0xCD2DEA+2*index:06X}','target':f'${target:06X}',
        'return_site':f'${ret:06X}','additional_bytes_below_scene_handler_entry':0,
        'existing_scene_near_frame_bytes':2,'new_frame_from_dispatch_jump':0,
        'return_a':0,'return_b':0,'return_d':0,'return_dbr':126,'return_m8':True,'return_x8':False,
        'return_irq_masked':True,'control_contract_sha256':sha(io.canonical(control)),
        'value_contract_sha256':sha(io.canonical(value))}


def audit(rom,handler_reference):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(a,n):
        require(type(a) is int and type(n) is int and n>0 and 0xC00000<=a<a+n<=0x1000000,'canonical read bounds')
        return rom[a-0xC00000:a-0xC00000+n]
    parent=[r for r in handler_reference['open_frontiers'] if r['entry']=='$CD2DD6']
    require(len(parent)==1 and parent[0]['commands']==[0x82] and
        parent[0]['frontier']['site']=='$CD2DE7' and parent[0]['frontier']['category']=='indexed-jump-dispatch'
        and parent[0]['full_bound'] is None,'preserved parent frontier differs')
    spans=[]
    for name,a,b,pin in SPANS:
        raw=read(a,b-a);require(sha(raw)==pin,'named span differs')
        spans.append({'name':name,'start':f'${a:06X}','end_exclusive':f'${b:06X}','size':len(raw),'sha256':pin})
    decoded=[]
    for pc,opcode,length,operand in PREFIX:
        raw=read(pc,length)
        require(raw[0]==opcode and int.from_bytes(raw[1:],'little')==operand,'prefix instruction recipe differs')
        decoded.append({'site':f'${pc:06X}','instruction_bytes':length,'instruction_sha256':sha(raw)})
    require(sum(x[2] for x in PREFIX)==20,'prefix exact coverage')
    target_rows=[];controls=[];projected=[]
    for index,target in enumerate(TARGETS):
        raw=read(0xCD2DEA+2*index,2)
        require(0xCD0000|int.from_bytes(raw,'little')==target,'selected target pointer differs')
        control=handlers.walk_direct(read,target,'near')
        value=values.value_walk(read,target,'near',entry_b=0,entry_dbr=126)
        target_rows.append(validate_target(index,control,value));controls.append(control);projected.append(value)
    all_pairs=[]
    for first in range(256):
        for second in range(256):
            row=prefix_contract(first,second)
            require(1<=row['stored_dp45_word']<=32 and row['stored_dp45_bytes'][1]==0
                and row['final_x'] in range(0,16,2) and
                row['pointer_byte_addresses']==[0xCD2DEA+row['final_x'],0xCD2DEB+row['final_x']],
                'B0 parameter composition differs')
            all_pairs.append((first,second,row['stored_dp45_word'],row['final_x']))
    for b in range(256):
        for value in range(256):
            row=prefix_contract(value,value,b)
            require(row['stored_dp45_word']==(b<<8)|((value&31)+1) and
                row['final_x']==(b<<8)|((value&224)>>4),'hidden B algebra differs')
    return {'schema':'project-epoch-scene82-masked-subdispatch-v1','date':'2026-09-08',
        'evidence_level':'verified-static','canonical_rom':{'size':len(rom),'sha256':ROM_SHA},
        'scope':'scene command byte82 only, conditional B0/D0/DBR7E/M1/X0/I1 near entry',
        'namespace':'scene-command stream byte; no Schala action or package-selector association',
        'preserved_parent_frontier':parent[0],'named_spans':spans,'prefix_instructions':decoded,
        'first_read_count_values':list(range(1,33)),'second_read_indices':list(range(0,16,2)),
        'independent_b0_parameter_pairs':len(all_pairs),'parameter_pair_projection_sha256':sha(io.canonical(all_pairs)),
        'hidden_b_byte_checks':65536,'nonzero_b_not_silently_zero_extended':True,
        'all_eight_selected_targets_composed':True,'conditional_handler_additional_stack_bytes':0,
        'conditional_total_including_existing_scene_near_frame':2,
        'all_conditional_returns':{'a':0,'b':0,'d':0,'dbr':126,'m8':True,'x8':False,'irq_masked':True},
        'selected_targets':target_rows,'target_control_contracts':controls,'target_value_contracts':projected,
        'premises':['Native scene-handler near entry in M1/X0/I1, B0/D0/DBR7E.',
            'The two parameter reads may return any two independent byte values; neither equality nor source validity is assumed.',
            'Ordinary writable stack and no nonstack CPU/DMA/asynchronous alias modifies live frames or canonical code.',
            'Input pointer, memory effects, source lifetime and the other scene handlers remain separate obligations.'],**LIMITS}


def collect():
    before={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()}
    own={'auditor':io.identity(Path(__file__).resolve()),'tests':io.identity(ROOT/'tests/test_schala_scene82_subdispatch_v1.py')}
    require(Path(handlers.__file__).resolve()==ROOT/PINS['handler_auditor'][0] and
        Path(values.__file__).resolve()==ROOT/PINS['value_auditor'][0],'imported source paths')
    handler_reference=handlers.collect();value_reference=values.collect()
    require(serial(handler_reference)==io.read_file(ROOT/PINS['handler_reference'][0],PINS['handler_reference'][2]),
        'preserved handler reference does not reproduce')
    require(serial(value_reference)==io.read_file(ROOT/PINS['value_reference'][0],PINS['value_reference'][2]),
        'preserved value reference does not reproduce')
    inherited=(list(handler_reference['source_identities'].values())+
        handler_reference['reused_closure_sources']+list(handler_reference['reused_scene_sources'].values())+
        handler_reference['primary_semantics']['sources']+list(value_reference['prerequisites'].values())+
        value_reference['source_identities']+value_reference['reused_underlying_source_identities'])
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited source identity')
        expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/path,pin) for path,pin in sorted(expected.items())]
    rom=io.read_file(ROM,ROM_SHA,0x400000);result=audit(rom,handler_reference)
    require(before=={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()} and
        own=={'auditor':io.identity(Path(__file__).resolve()),'tests':io.identity(ROOT/'tests/test_schala_scene82_subdispatch_v1.py')},
        'source changed during collection')
    require(transitive==[io.identity(ROOT/path,pin) for path,pin in sorted(expected.items())],
        'inherited source changed during new composition')
    result.update(source_identities=before,**own,
        primary_instruction_sources=handler_reference['primary_semantics']['sources'],
        reused_handler_sources=handler_reference['source_identities'],
        reused_value_sources=value_reference['reused_underlying_source_identities'],
        transitive_source_identities=transitive,
        reproduce=['python','-B','tools/audit_schala_scene82_subdispatch_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
