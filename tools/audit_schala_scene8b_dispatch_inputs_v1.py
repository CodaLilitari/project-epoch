"""Scene 8B conditional successful-return index and selected target contracts.

The exact CLC/SEC return predecessors supply a local source-derived carry fact;
no general flag model, legal script domain, alias closure or native run.
"""
from __future__ import annotations
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_scene_handler_values_v2 as values

ROOT=Path(__file__).resolve().parents[1]
handlers=values.scene
io=values.bodies
require=io.require
sha=io.sha
serial=io.serial
SOURCE='tools/audit_schala_scene8b_dispatch_inputs_v1.py'
TESTS='tests/test_schala_scene8b_dispatch_inputs_v1.py'
PINS={
 'value_source':('tools/audit_schala_scene_handler_values_v2.py',19076,'cfacea4c27289daa12f8a2965ee4e16b46b53b4f7b72b23ec91b648eedf9c872'),
 'value_tests':('tests/test_schala_scene_handler_values_v2.py',6150,'76bd30b55b96d1c2580a76af7827256119899b8bfbc4f4e56974e743603b9528'),
 'value_reference':('references/schala_scene_handler_values_v2.json',357484,'52543e1820669eac00b90baa39e307dcb9b35c9be14e7a0eff42e5aa762d8b87'),
}
SPANS=((0xCD2FB7,0xCD2FBC,'7bd3501e6f7ad1f8c26effa5f94603092483237bec54b464d671f0fe504a5d50'),
 (0xCD3189,0xCD319E,'88dcee046a11b7b690c68784e2caa94672ec091f72ed30718b1f968568c1365b'),
 (0xCD319E,0xCD31AA,'497ed7d635dc2511272fbb36ba59d24f1551cfda3852afa5dd30f35488581a75'),
 (0xCD31AA,0xCD31FE,'853ddf3d360a7c44b76b0cd4ad36a9ace97a01d94595c14e2336dfb2ca0eb63f'),
 (0xCD33B5,0xCD33D9,'933417b94b90f7ad574b3b374ce4fd53f46d10be665a532f5240d8288927eb6c'))
TARGETS=(0xCD33B5,0xCD33BB,0xCD33C1,0xCD33C7,0xCD33CD,0xCD33D3)
CLOSED=(0xCD33C7,0xCD33D3)


def geometry(q,z):
    for name,v in [('q',q),('z',z)]:require(type(v) is int and 0<=v<=255,'exact byte '+name)
    index=(z<<1)&255;pointer=0xCD319E+index
    return {'q':q,'z':z,'selector_read_address':0x7ECAD1+q,'dispatch_x':index,
        'pointer_byte_addresses':[pointer,pointer+1],'among_six_reviewed_cells':(z&127)<6,
        'q_high_bit_preserved_in_selector_source_index':True,'z_high_bit_discarded_in_dispatch_index':True,
        'successful_callee_return_b_zero_required':True,'legal_q_z_domain_proved':False}


def exit_predecessors(read):
    """Decode the complete no-call helper CFG and own every RTS predecessor."""
    queue=deque([(0xCD31AA,True,False)]);seen=set();owners={};lengths={};edges=set();returns=set();decoded={}
    while queue:
        pc,m8,x8=queue.popleft()
        if (pc,m8,x8) in seen:continue
        seen.add((pc,m8,x8));require(len(seen)<=200,'helper CFG budget')
        require(0xCD31AA<=pc<0xCD31FE,'helper CFG extent')
        require(pc not in owners or owners[pc]==pc,'helper CFG operand entry')
        op,name,raw=values.decode(read,pc,m8,x8)
        require(pc+len(raw)<=0xCD31FE,'helper instruction extent')
        require(pc not in lengths or lengths[pc]==len(raw),'helper changing decode width');lengths[pc]=len(raw)
        decoded[(pc,m8,x8)]=(name,len(raw),sha(raw))
        for p in range(pc,pc+len(raw)):
            require(p not in owners or owners[p]==pc,'helper CFG overlap');owners[p]=pc
        nxt=pc+len(raw)
        if op==0x60:
            require(m8 and not x8,'helper return widths');returns.add(pc);continue
        if op in (0xC2,0xE2):
            require(raw[1] in (0x10,),'only helper index-width changes')
            x8=op==0xE2
        require(name not in ('JSR','JSL','RTL','RTI','JMP abs','JML')
            and not name.startswith('JMP'),'unexpected helper control transfer')
        if op in values.closure.prior.irq.BRANCHES or op==0x80:
            target=nxt+int.from_bytes(raw[1:],'little',signed=True)
            successors=[target] if op==0x80 else [nxt,target]
        else:successors=[nxt]
        for p in successors:edges.add((pc,p));queue.append((p,m8,x8))
    require(returns=={0xCD31B6,0xCD31FD},'complete exact helper return set')
    for ret,pred,opcode in ((0xCD31B6,0xCD31B5,0x18),(0xCD31FD,0xCD31FC,0x38)):
        require({a for a,b in edges if b==ret}=={pred},'return has an unowned flag predecessor')
        require(read(pred,2)==bytes((opcode,0x60)),'exact CLC or SEC immediately before RTS')
    return {'contexts':[{'pc':f'${p:06X}','m8':m,'x8':x} for p,m,x in sorted(seen)],
        'complete_return_set':['$CD31B6','$CD31FD'],
        'source_owned_exit_flags':[{'site':'$CD31B6','predecessor':'$CD31B5','carry':False},
                                 {'site':'$CD31FD','predecessor':'$CD31FC','carry':True}],
        'both_edges_retained':True,'global_carry_model_added':False,
        'decoded_context_identity_sha256':sha(io.canonical(sorted(decoded.items()))),
        'edge_identity_sha256':sha(io.canonical(sorted(edges)))}


def compare_models(control,value,entry):
    io.closed(control,entry,'near')
    require(value['entry']==f'${entry:06X}' and value['kind']=='near','exact value entry')
    require(value['entry_m8'] is True and value['entry_x8'] is False and value['entry_irq_masked'] is True,
        'exact entry widths')
    require(type(value['entry_d']) is int and value['entry_d']==0 and
        type(value['entry_dbr']) is int and value['entry_dbr']==126,'exact D/DBR entry')
    for key in ('decoded_byte_intervals','decoded_context_identity_sha256','mnemonic_context_counts','direct_calls'):
        require(value[key]==control[key],'exact source context agreement '+key)
    require(value['all_direct_callees_inlined'] is True and value['branch_conditions_overapproximated'] is True
        and value['d_invariant_proved_under_no_alias_no_asynchronous_premises'] is True
        and value['nonstack_memory_and_dma_effects_proved'] is False and value['termination_proved'] is False,
        'unchanged conditional value scope')


def exact_end(row,site,low,b):
    expected={'site':f'${site:06X}','kind':'return','m8':True,'x8':False,'irq_masked':True,
        'a_low':low,'b':b,'d':0,'dbr':126,'counted_stack_bytes':0,'frames':[]}
    require(row==expected,'exact returned value state')
    for k in ('m8','x8','irq_masked'):require(type(row[k]) is bool,'exact return boolean')
    for k in ('a_low','b','d','dbr','counted_stack_bytes'):
        require(row[k] is None if expected[k] is None else type(row[k]) is int,'exact return integer or unknown')


def prehelper_contract(read,control,value):
    compare_models(control,value,0xCD31AA)
    require(value['entry_b'] is None,'arbitrary helper-entry B remains unknown')
    require(control['maximum_additional_bytes_below_callee_entry']==0
        and type(control['maximum_additional_bytes_below_callee_entry']) is int
        and control['maximum_counted_bytes_including_root_call_frame']==2
        and type(control['maximum_counted_bytes_including_root_call_frame']) is int,'helper exact frame extent')
    require(control['direct_calls']==[],'helper has no callees')
    require(control['return_width_states']==[{'site':f'${p:06X}','m8':True,'x8':False,'irq_masked':True}
        for p in (0xCD31B6,0xCD31FD)],'complete typed helper returns')
    require(len(value['ends'])==2,'complete value helper returns')
    exact_end(value['ends'][0],0xCD31B6,None,None);exact_end(value['ends'][1],0xCD31FD,126,0)
    cfg=exit_predecessors(read)
    require(len(cfg['contexts'])==control['instruction_contexts'],'helper CFG context count differs')
    require(cfg['decoded_context_identity_sha256']==control['decoded_context_identity_sha256'],
        'helper CFG exact decoded contexts differ')
    require(read(0xCD3189,8)==bytes.fromhex('8D AA CA 20 AA 31 90 0C')
        and read(0xCD319D,1)==b'\x60','exact caller store/call/BCC/early return')
    return {'entry_b':'unknown','failure':{'return':'$CD31B6','carry':False,'b':'unknown','caller_branch':'$CD318F -> $CD319D RTS'},
        'success':{'return':'$CD31FD','carry':True,'a_low':126,'b':0,'caller_branch':'$CD318F -> $CD3191'},
        'successful_dispatch_b_zero_proved_conditionally':True,'arbitrary_failure_b_zero_claim':False,
        'additional_bytes_below_helper_entry':0,'caller_jsr_frame_bytes':2,'cfg':cfg,
        'control_contract_sha256':sha(io.canonical(control)),'value_contract_sha256':sha(io.canonical(value))}


def closed_target(control,value,target):
    require(type(target) is int and target in CLOSED,'only two independently closed targets')
    compare_models(control,value,target)
    require(type(value['entry_b']) is int and value['entry_b']==0,'successful dispatch B0 entry')
    require(type(control['maximum_additional_bytes_below_callee_entry']) is int
        and control['maximum_additional_bytes_below_callee_entry']==2
        and type(control['maximum_counted_bytes_including_root_call_frame']) is int
        and control['maximum_counted_bytes_including_root_call_frame']==4,'selected target frame extent')
    require(control['return_width_states']==[{'site':'$CD347C','m8':True,'x8':False,'irq_masked':True}]
        and len(value['ends'])==1,'selected target complete return set')
    exact_end(value['ends'][0],0xCD347C,0,0)
    return {'target':f'${target:06X}','additional_bytes_below_target_entry':2,
        'handler_and_target_share_existing_near_frame':True,'dispatch_jump_new_frame_bytes':0,
        'sequential_helper_and_target_max_additional_bytes':2,'total_including_handler_near_frame':4,
        'return':'$CD347C','return_a_b':0,'return_d':0,'return_dbr':126,
        'control_contract_sha256':sha(io.canonical(control)),'value_contract_sha256':sha(io.canonical(value))}


def audit(rom,census):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==values.ROM_SHA,'canonical ROM identity')
    def read(p,n):
        require(type(p) is int and type(n) is int and n>0 and 0xC00000<=p<p+n<=0x1000000,'canonical read extent')
        return rom[p-0xC00000:p-0xC00000+n]
    spans=[]
    for p,end,h in SPANS:
        require(sha(read(p,end-p))==h,'exact selected source span')
        spans.append({'start':f'${p:06X}','end_exclusive':f'${end:06X}','sha256':h})
    parent=next(x for x in census['conditional_handler_contracts'] if x['entry']=='$CD2FB7')
    require(parent['frontier']['site']=='$CD319A' and parent['frontier']['counted_stack_bytes_at_frontier']==2,
        'original parent frontier differs')
    for p,raw in ((0xCD2FB7,bytes.fromhex('A7 40 4C 89 31')),
                  (0xCD3191,bytes.fromhex('AD AA CA AA BD D1 CA 0A AA 7C 9E 31'))):
        require(read(p,len(raw))==raw,'exact input/index prefix')
    helper_control=handlers.walk_direct(read,0xCD31AA,'near')
    helper_value=values.value_walk(read,0xCD31AA,'near',entry_b=None,entry_dbr=126)
    helper=prehelper_contract(read,helper_control,helper_value)
    targets=[];closed=[];opened=[]
    for i,target in enumerate(TARGETS):
        require(0xCD0000|int.from_bytes(read(0xCD319E+2*i,2),'little')==target,'selected pointer cell differs')
        control=handlers.walk_direct(read,target,'near');row={'cell':i,'target':f'${target:06X}','control':control}
        if target in CLOSED:
            value=values.value_walk(read,target,'near',entry_b=0,entry_dbr=126)
            row['value']=value;row['conditional_contract']=closed_target(control,value,target);closed.append(target)
        else:
            require(control['frontier'] is not None and control['frontier']['site']=='$CEE7CC'
                and control['frontier']['counted_stack_bytes_at_frontier']==9
                and control['maximum_additional_bytes_below_callee_entry'] is None,'exact downstream open pointer frontier')
            opened.append(target);row['b5_b6_pointer_contract_applied']=False
        targets.append(row)
    digest=hashlib.sha256();source_addresses=set();pointer_starts=set();admitted=[]
    for q in range(256):
        for z in range(256):
            row=geometry(q,z);addresses=row['pointer_byte_addresses']
            require(row['dispatch_x']==2*(z%128) and row['selector_read_address']==0x7ECAD1+q,'independent geometry')
            digest.update(bytes((q,z))+row['selector_read_address'].to_bytes(3,'little')+
                row['dispatch_x'].to_bytes(2,'little')+b''.join(p.to_bytes(3,'little') for p in addresses))
            source_addresses.add(row['selector_read_address']);pointer_starts.add(addresses[0])
            if q==0 and row['among_six_reviewed_cells']:admitted.append(z)
    require(len(source_addresses)==256 and len(pointer_starts)==128 and admitted==list(range(6))+list(range(128,134)),
        'exact q/z domains')
    require(read(0xCD31AA,2)==b'\xAD\xAA','first extra cell no longer overlaps LDA CAAA')
    return {'schema':'project-epoch-scene8b-dispatch-inputs-v1','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':values.ROM_SHA},'source_spans':spans,
        'namespace':'scene command 8B only; no action/package-selector association',
        'preserved_original_frontier':parent['frontier'],'prehelper_contract':helper,
        'prehelper_control':helper_control,'prehelper_value':helper_value,
        'geometry':{'q_z_combinations':65536,'selector_byte_sources':256,'source_start':'$7ECAD1','source_end_inclusive':'$7ECBD0',
            'physical_word_starts':128,'first_word':'$CD319E','last_word':'$CD329C','reviewed_cells':6,
            'conditional_z_aliases':admitted,'matrix_sha256':digest.hexdigest(),
            'serialization':'q,z bytes; selector source24 little; X16 little; pointer low/high addresses24 little',
            'q_high_bit_preserved':True,'z_high_bit_discarded':True,'legal_q_z_domain_proved':False},
        'earlier_helper_radius_source':'Before successful B0 establishment, CAA4 absolute,X uses X=(incoming B<<8)|q; its contents/alias/lifetime are unproved.',
        'first_code_overlap':{'z':6,'pointer_low':'$CD31AA','pointer_high':'$CD31AB','would_target':'$CDAAAD',
            'source_role':'first helper LDA CAAA instruction','escaped_target_followed':False},
        'selected_targets':targets,'closed_targets':[f'${p:06X}' for p in closed],'open_targets':[f'${p:06X}' for p in opened],
        'premises':['Native M1/X0/I1 with D0/DBR7E; B may be unknown before the prehelper.',
            'No asynchronous flag/register change between each exact CLC/SEC exit and caller BCC.',
            'Stable q reload, selector byte z, script pointer and q-indexed helper input; no intervening alias changes their meaning.',
            'Ordinary writable stack; no nonstack CPU/DMA/WRAM-port alias overwrites saved frames or code.',
            'Conditional target selection requires (z & 7F) < 6; that domain is not proved for legal scripts.'],
        'legal_script_domain_proved':False,'q_indexed_input_validity_and_lifetime_proved':False,
        'effective_memory_alias_closure':False,'dma_or_wram_port_ownership_proved':False,
        'whole_scene8b_closed':False,'whole_nmi_bound':None,'termination_or_timing_proved':False,
        'production_approval':False,'native_execution':False}


def collect():
    pins={k:io.identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()}
    own=[io.identity(ROOT/p) for p in (SOURCE,TESTS)]
    require(Path(values.__file__).resolve()==ROOT/PINS['value_source'][0],'exact imported value source')
    previous=values.collect();p,n,h=PINS['value_reference']
    require(serial(previous)==io.read_file(ROOT/p,h,n),'accepted value reference no longer reproduces')
    p,n,h=values.base.PINS['scene_reference'];census=json.loads(io.read_file(ROOT/p,h,n))
    expected={}
    for item in previous['reused_underlying_source_identities']+list(previous['prerequisites'].values())+previous['source_identities']:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'consistent inherited sources')
        expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/p,h) for p,h in sorted(expected.items())]
    result=audit(io.read_file(values.ROM,values.ROM_SHA,0x400000),census)
    cpu_path=ROOT/'private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h'
    cpu_raw=io.read_file(cpu_path,'9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd',27673)
    lines=cpu_raw.splitlines(keepends=True)
    result['reviewed_cpu_semantic_spans']=[{'path':cpu_path.relative_to(ROOT).as_posix(),
        'first_line':first,'last_line_inclusive':last,'sha256':sha(b''.join(lines[first-1:last])),
        'role':role,'interpretation':'reviewer-derived semantics over pinned source'}
        for first,last,role in ((163,167,'BCC reads carry clear'),(231,255,'CLC and SEC change carry'),
            (479,501,'near/far returns do not restore status'),(626,633,'M8 ASL preserves hidden B'),
            (1058,1063,'TAX uses destination X width'),(434,445,'indexed indirect JMP reads within PBR'))]
    result.update(prerequisites=pins,source_identities=own,reused_underlying_source_identities=transitive,
        primary_cpu_sources=previous['primary_cpu_sources'],reproduce=['python','-B',SOURCE],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    require(own==[io.identity(ROOT/p) for p in (SOURCE,TESTS)],'own source drift')
    require(pins=={k:io.identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()},'prerequisite drift')
    require(transitive==[io.identity(ROOT/p,h) for p,h in sorted(expected.items())],'inherited source drift')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
