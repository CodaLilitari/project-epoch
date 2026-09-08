"""Conditional scene-command 8C/8D four-cell dispatch and leaf return proof.

The unmasked parameter and hidden B are not a proved legal producer domain.
All physical index arithmetic remains separate from the eight selected leaves.
Read-only; no emulator, ROM output, patch, hook or allocation.
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
ENTRIES={0x8C:0xCD2958,0x8D:0xCD2999}
TABLES={0x8C:0xCD2961,0x8D:0xCD29A2}
TARGETS={0x8C:(0xCD2969,0xCD2975,0xCD2981,0xCD298D),
         0x8D:(0xCD29AA,0xCD29B6,0xCD29C2,0xCD29CE)}
SPANS=(
 ('8c-prefix',0xCD2958,0xCD2961,'ee3e3727ed042810ab7df57599cc09789e94e994fcb911736a5fbd0a0792962a'),
 ('8c-selected-cells',0xCD2961,0xCD2969,'df4b1b51e7110957e207f6ca5c53eaaacdf1eb3b80cfd80604da279c88d9ff9b'),
 ('8c-target-body-union',0xCD2969,0xCD2999,'f4b18b8a171958ed937c98a536570d15cf271caec72edf193633c9a088b48aa2'),
 ('8d-prefix',0xCD2999,0xCD29A2,'5e316bb6aa20db849d26c0691a784d36864f4f9acae645e80567b8d99e7e3ee5'),
 ('8d-selected-cells',0xCD29A2,0xCD29AA,'3ebfcc7021d59d27095c746a8075ee47a96aba90210cb26325afab66c757e221'),
 ('8d-target-body-union',0xCD29AA,0xCD29DA,'a30d06c3566c405184df55d88623540646f00e36715f86bc1276b23c8e0dc100'),
)
LIMITS={'legal_parameter_or_script_producer_domain_proved':False,
 'all_physical_dispatch_cells_are_legal_table_entries':False,'arbitrary_parameter_handler_closure':False,
 'input_pointer_and_y_source_lifetime_proved':False,'target_effective_memory_addresses_proved':False,
 'nonstack_memory_alias_closure':False,'dma_effects_proved':False,'global_handler_return_b_proved':False,
 'whole_nmi_stack_bound':None,'termination_or_timing_proved':False,
 'production_approval':False,'new_native_execution':False}
require=io.require
sha=io.sha
serial=io.serial


def byte(value,name):require(type(value) is int and 0<=value<=255,'exact byte '+name)


def prefix_contract(command,parameter,hidden_b=0):
    require(type(command) is int and command in ENTRIES,'exact scene command 8C or 8D')
    byte(parameter,'parameter');byte(hidden_b,'hidden B')
    index=(hidden_b<<8)|((parameter<<1)&255)
    low=(TABLES[command]+index)&65535
    return {'scene_command':command,'parameter':parameter,'hidden_b':hidden_b,'final_x':index,
        'pointer_byte_addresses':[0xCD0000|low,0xCD0000|((low+1)&65535)],
        'among_four_reviewed_cells':hidden_b==0 and (parameter&127)<4,
        'parameter_bit7_discarded':True,'hidden_b_zero_extension_assumed':False,
        'new_stack_bytes_in_prefix':0,'jump_adds_return_frame':False,
        'entry_contract':{'m8':True,'x8':False,'irq_masked':True,'d':0,'dbr':126},
        'y_source':'unknown 16-bit word loaded from DP43; no value or lifetime asserted'}


def validate_target(command,index,control,value):
    require(type(command) is int and command in ENTRIES,'exact scene command 8C or 8D')
    require(type(index) is int and 0<=index<4,'exact selected cell index')
    target=TARGETS[command][index];ret=target+11
    io.closed(control,target,'near')
    require(control['maximum_additional_bytes_below_callee_entry']==0 and
        type(control['maximum_additional_bytes_below_callee_entry']) is int and
        control['maximum_counted_bytes_including_root_call_frame']==2 and
        type(control['maximum_counted_bytes_including_root_call_frame']) is int,'target stack bound differs')
    require(control['return_width_states']==[{'site':f'${ret:06X}','m8':True,'x8':False,'irq_masked':True}],
        'target return site/width differs')
    require(all(type(control['return_width_states'][0][key]) is bool for key in ('m8','x8','irq_masked')),
        'target control exact width booleans')
    require(value['entry']==f'${target:06X}' and value['kind']=='near' and value['entry_b']==0 and
        type(value['entry_b']) is int and value['entry_d']==0 and type(value['entry_d']) is int and
        value['entry_dbr']==126 and type(value['entry_dbr']) is int,'target value entry differs')
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
    return {'scene_command':command,'cell_index':index,'pointer':f'${TABLES[command]+2*index:06X}',
        'target':f'${target:06X}','return_site':f'${ret:06X}',
        'parameter_arithmetic_aliases':[index,index+128],'legal_parameter_values_proved':False,
        'additional_bytes_below_scene_handler_entry':0,'existing_scene_near_frame_bytes':2,
        'new_frame_from_dispatch_jump':0,'return_a':0,'return_b':0,'return_d':0,'return_dbr':126,
        'return_m8':True,'return_x8':False,'return_irq_masked':True,
        'control_contract_sha256':sha(io.canonical(control)),'value_contract_sha256':sha(io.canonical(value))}


def audit(rom,handler_reference):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(a,n):
        require(type(a) is int and type(n) is int and n>0 and 0xC00000<=a<a+n<=0x1000000,'canonical read bounds')
        return rom[a-0xC00000:a-0xC00000+n]
    parents=[]
    for command,entry in ENTRIES.items():
        matches=[r for r in handler_reference['open_frontiers'] if r['entry']==f'${entry:06X}']
        require(len(matches)==1 and matches[0]['commands']==[command] and
            matches[0]['frontier']['site']==f'${entry+6:06X}' and
            matches[0]['frontier']['category']=='indexed-jump-dispatch' and matches[0]['full_bound'] is None,
            'preserved parent frontier differs')
        parents.append(matches[0])
    spans=[]
    for name,a,b,pin in SPANS:
        raw=read(a,b-a);require(sha(raw)==pin,'named span differs')
        spans.append({'name':name,'start':f'${a:06X}','end_exclusive':f'${b:06X}','size':len(raw),'sha256':pin})
    prefixes=[];targets=[];controls=[];projected=[];domains=[];escapes=[]
    for command,entry in ENTRIES.items():
        recipe=((entry,0xA4,2,0x43),(entry+2,0xA7,2,0x40),(entry+4,0x0A,1,0),
                (entry+5,0xAA,1,0),(entry+6,0x7C,3,TABLES[command]&65535))
        require(sum(n for _,_,n,_ in recipe)==9,'exact prefix coverage')
        for pc,opcode,length,operand in recipe:
            raw=read(pc,length)
            require(raw[0]==opcode and int.from_bytes(raw[1:],'little')==operand,'prefix recipe differs')
            prefixes.append({'command':command,'site':f'${pc:06X}','instruction_bytes':length,'instruction_sha256':sha(raw)})
        for index,target in enumerate(TARGETS[command]):
            require(0xCD0000|int.from_bytes(read(TABLES[command]+2*index,2),'little')==target,'selected pointer differs')
            control=handlers.walk_direct(read,target,'near')
            value=values.value_walk(read,target,'near',entry_b=0,entry_dbr=126)
            targets.append(validate_target(command,index,control,value));controls.append(control);projected.append(value)
        digest=hashlib.sha256();starts=set();bytes_seen=set();b0=set();admitted=[]
        for b in range(256):
            for parameter in range(256):
                row=prefix_contract(command,parameter,b);index=row['final_x'];addresses=row['pointer_byte_addresses']
                require(index==(b*256+(parameter%128)*2),'independent ASL/TAX algebra differs')
                digest.update(bytes((b,parameter))+index.to_bytes(2,'little')+
                    b''.join(a.to_bytes(3,'little') for a in addresses))
                starts.add(addresses[0]);bytes_seen.update(addresses)
                if b==0:b0.add(addresses[0])
                if row['among_four_reviewed_cells']:admitted.append((b,parameter))
        require(len(starts)==32768 and bytes_seen==set(range(0xCD0000,0xCE0000)) and len(b0)==128,
            'physical cell/address domain differs')
        require(admitted==[(0,p) for p in (0,1,2,3,128,129,130,131)],'conditional aliases differ')
        domains.append({'command':command,'exhaustive_b_parameter_pairs':65536,'algebra_projection_sha256':digest.hexdigest(),
            'physical_cell_starts_all_b':len(starts),'physical_pointer_bytes_all_b':len(bytes_seen),
            'physical_cell_starts_b0':len(b0),'reviewed_adjacent_cells':4,'conditional_b_parameter_pairs':admitted,
            'physical_census_is_not_legal_table_extent':True})
        escape=prefix_contract(command,4)
        require(escape['pointer_byte_addresses']==[TARGETS[command][0],TARGETS[command][0]+1]
            and not escape['among_four_reviewed_cells'],'first escape no longer overlaps leaf code')
        require(read(TARGETS[command][0],2)==bytes((0xC2,0x20)),'first escape instruction is not REP20')
        escapes.append({'command':command,'parameter':4,'hidden_b':0,
            'pointer_byte_addresses':escape['pointer_byte_addresses'],'pointer_would_target':'$CD20C2',
            'selected_bytes_role':'first leaf REP20 instruction; outside the four reviewed pointer cells',
            'escaped_target_control_flow_followed':False,'legal_producer_reachability_proved':False})
    return {'schema':'project-epoch-scene8c8d-conditional-subdispatch-v1','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},
        'namespace':'scene-command bytes8C/8D; no Schala action or package-selector association',
        'scope':'conditional native M1/X0/I1 D0/DBR7E/B0 with (parameter&7F)<4; no legal producer-domain proof',
        'preserved_parent_frontiers':parents,'named_spans':spans,'prefix_instructions':prefixes,
        'physical_vs_conditional_domains':domains,'first_code_overlap_counterexamples':escapes,
        'all_eight_conditional_targets_composed':True,'conditional_handler_additional_stack_bytes':0,
        'conditional_total_including_existing_scene_near_frame':2,
        'all_conditional_returns':{'a':0,'b':0,'d':0,'dbr':126,'m8':True,'x8':False,'irq_masked':True},
        'selected_targets':targets,'target_control_contracts':controls,'target_value_contracts':projected,
        'premises':['Native scene-handler near entry M1/X0/I1, D0/DBR7E; conditional B0 and (parameter&7F)<4.',
            'Parameter read may be an arbitrary byte; restricting it for leaf composition is a premise, not a proved producer domain.',
            'Ordinary writable stack; no nonstack CPU/DMA/asynchronous alias changes live frames or canonical code.',
            'DP40 pointer, DP43 word loaded into Y, and target effective memory addresses/lifetime remain unresolved.'],**LIMITS}


def collect():
    before={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()}
    own={'auditor':io.identity(Path(__file__).resolve()),'tests':io.identity(ROOT/'tests/test_schala_scene8c8d_subdispatch_v1.py')}
    require(Path(handlers.__file__).resolve()==ROOT/PINS['handler_auditor'][0] and
        Path(values.__file__).resolve()==ROOT/PINS['value_auditor'][0],'imported source paths')
    handler_reference=handlers.collect();value_reference=values.collect()
    require(serial(handler_reference)==io.read_file(ROOT/PINS['handler_reference'][0],PINS['handler_reference'][2]),
        'preserved handler reference does not reproduce')
    require(serial(value_reference)==io.read_file(ROOT/PINS['value_reference'][0],PINS['value_reference'][2]),
        'preserved value reference does not reproduce')
    inherited=(list(handler_reference['source_identities'].values())+handler_reference['reused_closure_sources']+
        list(handler_reference['reused_scene_sources'].values())+handler_reference['primary_semantics']['sources']+
        list(value_reference['prerequisites'].values())+value_reference['source_identities']+
        value_reference['reused_underlying_source_identities'])
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited source identity')
        expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/path,pin) for path,pin in sorted(expected.items())]
    rom=io.read_file(ROM,ROM_SHA,0x400000);result=audit(rom,handler_reference)
    require(before=={key:io.identity(ROOT/path,pin,size) for key,(path,size,pin) in PINS.items()} and
        own=={'auditor':io.identity(Path(__file__).resolve()),'tests':io.identity(ROOT/'tests/test_schala_scene8c8d_subdispatch_v1.py')},
        'source changed during collection')
    require(transitive==[io.identity(ROOT/path,pin) for path,pin in sorted(expected.items())],
        'inherited source changed during new composition')
    result.update(source_identities=before,**own,
        primary_instruction_sources=handler_reference['primary_semantics']['sources'],
        transitive_source_identities=transitive,
        reproduce=['python','-B','tools/audit_schala_scene8c8d_subdispatch_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
