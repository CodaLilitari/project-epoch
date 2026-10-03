"""Two remaining first29 scene80 return contracts; source-only v2.

Exactly MVP44/ADCdpX75 extend the typed decoder. The D1F108 local projection
models saved and temporary D explicitly. Old scene80 and all114 accepted
direct-control contracts remain unchanged. No memory or production approval.
Resumed 2026-10-03 from an unaccepted 2026-09-08 draft.
"""
from __future__ import annotations
from collections import Counter,deque
import argparse
import ast
import inspect
import json
from pathlib import Path
import sys
import types
import audit_schala_scene80_subdispatch_v1 as prior

ROOT=Path(__file__).resolve().parents[1]
handlers=prior.handlers
values=prior.values
io=prior.io
require=io.require
sha=io.sha
serial=io.serial
cpu=prior.cpu
SOURCE='tools/audit_schala_scene80_remaining_returns_v2.py'
TESTS='tests/test_schala_scene80_remaining_returns_v2.py'
D_TRANSITIONS=[
 {'site':'$D1F10D','before':0,'after':0x0A00,'stack_bytes_after':5},
 {'site':'$D1F161','before':0x0A00,'after':0,'stack_bytes_after':3},
 {'site':'$D1F1AC','before':0x0A00,'after':0,'stack_bytes_after':3}]
PINS={
 'scene80_source':('tools/audit_schala_scene80_subdispatch_v1.py',17082,'5bf0ff11fa69ad09f74e204524444ec336b036a6c1ccc6ee90c649275a68492f'),
 'scene80_tests':('tests/test_schala_scene80_subdispatch_v1.py',8999,'909da68de2896c0dcda47df71fb37e35b6ae15387e8bad2278b82803461a8c89'),
 'scene80_reference':('references/schala_scene80_subdispatch_v1.json',424188,'98ef60b958f997bc125d2550ff90c9cd6948a9f7b269be7fc0194790cfbece2f'),
}
EXTENSIONS={0x44:('MVP',3),0x75:('ADC dp,X',2)}
SPANS=((0xCD2BFC,0xCD2C16,'1f86ec05598668a3e9bb00313e10e2c63cd9906a4cd328f8073e24e6766008d7'),
 (0xCD2C16,0xCD2C7F,'b898a8fce09c948189e0971e572f29ac1f0d355f7d209125b38817a9367506e8'),
 (0xCD2B64,0xCD2B69,'02c4c57239810fdd17c475edc07052b7af321e4f077eebe9d32b6e38d8a788d1'),
 (0xD1F108,0xD1F1B0,'20e54f4babade6dc371b269b54e61ad26b3af01b26d89b8a964a2b6e34368166'),
 (0xD1F108,0xD1F110,'a1fcf770fc4d1ab4df1aa3eb8def9b2fc6fbe948277241f5ef6397958270be1f'),
 (0xD1F161,0xD1F165,'866b67378d0188a9fa81246e40c481153fcdfa62e556a73525e91e031604c435'),
 (0xD1F1AC,0xD1F1B0,'866b67378d0188a9fa81246e40c481153fcdfa62e556a73525e91e031604c435'))


def replace_once(source,old,new):
    require(source.count(old)==1,'exact one declared derivation edit')
    return source.replace(old,new)


def derive_models():
    """Fresh in-memory functions; never alter imported modules or source files.

    The typed algorithm is unchanged; two write-inventory literals learn MVP.
    The existing value algorithm adds MVP's same A/DBR completion as MVN.
    No generic D effect is added to that inherited value implementation.
    """
    fixed={**handlers.FIXED,**EXTENSIONS}
    require(not(set(EXTENSIONS)&set(handlers.FIXED)),'extension was already inherited')
    control_source=inspect.getsource(handlers.walk_direct)
    control_source=replace_once(control_source,'"ROL","MVN"','"ROL","MVN","MVP"')
    control_source=replace_once(control_source,'name=="MVN"','name in ("MVN","MVP")')
    control_globals=dict(handlers.__dict__);control_globals['FIXED']=fixed
    exec(compile(control_source,'<scene80-v2-declared-control-derivation>','exec'),control_globals)
    value_globals=dict(values.__dict__);value_globals['scene']=types.SimpleNamespace(FIXED=fixed)
    decode_source=inspect.getsource(values.decode)
    exec(compile(decode_source,'<scene80-v2-exact-inherited-decoder>','exec'),value_globals)
    value_source=replace_once(inspect.getsource(values.value_walk),'elif op==0x54:','elif op in (0x54,0x44):')
    value_source=replace_once(value_source,"'MVN projection requires native M16/X16'","'block-move projection requires native M16/X16'")
    exec(compile(value_source,'<scene80-v2-MVP-value-derivation>','exec'),value_globals)
    receipt={'new_fixed_entries':{f'${op:02X}':{'name':n,'bytes':z} for op,(n,z) in EXTENSIONS.items()},
        'typed_control_algorithm_changed':False,'new_write_inventory_mnemonic':'MVP',
        'value_changes':['MVP uses existing M16/X16 block-move completed A=FFFF and DBR=first operand rule',
                         'diagnostic error names block move; no generic D support added'],
        'derived_control_ast_sha256':sha(ast.dump(ast.parse(control_source)).encode()),
        'inherited_decoder_ast_sha256':sha(ast.dump(ast.parse(decode_source)).encode()),
        'derived_value_ast_sha256':sha(ast.dump(ast.parse(value_source)).encode())}
    return control_globals['walk_direct'],value_globals['decode'],value_globals['value_walk'],receipt


def mvp_completion(a,x,y,destination,*,m8=False,x8=False):
    for name,v in (('A',a),('X',x),('Y',y)):
        require(type(v) is int and 0<=v<=65535,'exact word '+name)
    require(type(destination) is int and 0<=destination<=255,'exact destination bank')
    require(m8 is False and x8 is False,'native M16/X16 block move premise')
    count=a+1
    return {'count':count,'a':65535,'x':(x-count)&65535,'y':(y-count)&65535,
        'dbr':destination,'d_changed':False,'m_x_i_changed':False,'stack_bytes':0,
        'memory_alias_or_effective_address_ownership_proved':False}


def d_routine_projection(read,decode,*,entry_b=0,entry_d=0,entry_dbr=126,m8=True,x8=False):
    """Exact D1F108 long routine with a real D state and typed software bytes.

    All conditional branches remain. No data value, flag-dependent loop exit,
    effective address or asynchronous preservation is inferred.
    """
    require(type(entry_b) is int and entry_b==0 and type(entry_d) is int and entry_d==0
        and type(entry_dbr) is int and entry_dbr==126 and m8 is True and x8 is False,
        'exact native M1/X0 B0/D0/DBR7E entry')
    root=('frame','root');queue=deque([(0xD1F108,True,False,0,0,126,None,(root,)*3)])
    seen=set();decoded={};owners={};edges=set();returns=set();peak=3;d_events=set()
    while queue:
        state=queue.popleft()
        if state in seen:continue
        seen.add(state);require(len(seen)<=1000,'bounded D-routine state budget')
        pc,m,x,b,d,dbr,xv,old_stack=state
        require(0xD1F108<=pc<0xD1F1B0,'exact D-routine source extent')
        op,name,raw=decode(read,pc,m,x)
        require(pc+len(raw)<=0xD1F1B0,'D-routine instruction extent')
        require(m is True and b==0 and dbr==126,'body must remain M8/B0/DBR7E')
        key=(pc,m,x)
        require(not any(k[0]==pc and v[1]!=len(raw) for k,v in decoded.items()),'D-routine width overlap')
        decoded[key]=(name,len(raw),sha(raw))
        for p in range(pc,pc+len(raw)):
            require(p not in owners or owners[p]==pc,'D-routine operand overlap');owners[p]=pc
        stack=list(old_stack);nxt=pc+len(raw);dest=[nxt]
        operand=int.from_bytes(raw[1:],'little')
        def push_word(value):
            require(type(value) is int and 0<=value<=65535,'known word required for software save')
            stack.extend([('data',value>>8),('data',value&255)])
        if op==0x0B:
            require(pc==0xD1F108 and d==0 and len(stack)==3,'exact original D save')
            push_word(d)
        elif op==0xA2:
            require(pc==0xD1F109 and not x and operand==0x0A00,'exact temporary-D immediate')
            xv=operand
        elif op==0xDA:
            require(pc==0xD1F10C and not x and xv==0x0A00,'exact full X save for temporary D')
            push_word(xv)
        elif op==0x2B:
            require(pc in (0xD1F10D,0xD1F161,0xD1F1AC) and len(stack)>=5
                and all(t[0]=='data' for t in stack[-2:]),'typed PLD must consume two saved software bytes')
            lo=stack.pop()[1];hi=stack.pop()[1];before=d;d=lo|(hi<<8)
            require(d==(0x0A00 if pc==0xD1F10D else 0),'exact temporary/restored D value')
            d_events.add((pc,before,d,len(stack)))
        elif op in (0xC2,0xE2):
            require(operand==0x10,'only X-width changes allowed in D-routine')
            x=op==0xE2
            if x and xv is not None:xv&=255
        elif op==0xA0:
            require(pc==0xD1F110 and x and operand==0,'exact initial Y byte')
        elif op==0xBB:xv=None  # Y is deliberately not modeled; no later software X save.
        elif op==0xE8:
            if xv is not None:xv=(xv+1)&(255 if x else 65535)
        elif op==0xC8:pass
        elif op in (0xAD,0xB9,0x75,0x29):
            require(x and d==0x0A00,'all modeled loads/arithmetic occur with temporary D and X8')
            # M8 LDA/ADC/AND overwrite only A.low. No B/D/DBR/stack effect.
        elif op==0x99:
            require(x and d==0x0A00,'temporary-D body store context')
            # Its memory/alias effects remain outside this projection.
        elif op in handlers.prior.irq.BRANCHES:
            target=nxt+int.from_bytes(raw[1:],'little',signed=True)
            dest=[nxt,target]
        elif op==0x6B:
            require(pc in (0xD1F164,0xD1F1AF) and not x and d==0 and stack==[root]*3,
                'exact balanced D-restored long return')
            returns.add((pc,m,x,b,d,dbr));continue
        else:raise ValueError(f'unreviewed D-routine effect {op:02X} at {pc:06X}')
        peak=max(peak,len(stack));edges.update((pc,p) for p in dest)
        queue.extend((p,m,x,b,d,dbr,xv,tuple(stack)) for p in dest)
    require(returns=={(0xD1F164,True,False,0,0,126),(0xD1F1AF,True,False,0,0,126)},'complete exact D-routine return set')
    require(d_events=={(0xD1F10D,0,0x0A00,5),(0xD1F161,0x0A00,0,3),(0xD1F1AC,0x0A00,0,3)},
        'complete D transition set')
    intervals=[]
    for p in sorted(owners):
        if intervals and intervals[-1][1]==p:intervals[-1][1]+=1
        else:intervals.append([p,p+1])
    return {'entry':'$D1F108','kind':'long','entry_b':0,'entry_d':0,'entry_dbr':126,
        'entry_m8':True,'entry_x8':False,'entry_irq_masked':True,'abstract_states':len(seen),
        'instruction_contexts':len(decoded),'direct_calls':[],
        'decoded_context_identity_sha256':sha(io.canonical(sorted(decoded.items()))),
        'edge_identity_sha256':sha(io.canonical(sorted(edges))),
        'decoded_byte_intervals':[{'start':cpu(a),'end_exclusive':cpu(z),'sha256':sha(read(a,z-a))} for a,z in intervals],
        'mnemonic_context_counts':dict(sorted(Counter(v[0] for v in decoded.values()).items())),
        'd_transitions':[{'site':cpu(p),'before':a,'after':z,'stack_bytes_after':n} for p,a,z,n in sorted(d_events)],
        'd_is_zero_throughout_body':False,'maximum_counted_bytes_including_long_frame':peak,
        'return_width_states':[{'site':cpu(p),'m8':m,'x8':x,'irq_masked':True} for p,m,x,b,d,dbr in sorted(returns)],
        'return_b':0,'return_d':0,'return_dbr':126,'body_data_values_proved':False,
        'branch_conditions_overapproximated':True,'all_return_paths_checked':True,
        'nonstack_aliases_and_asynchronous_preservation_proved':False,'termination_proved':False}


def compare_d_projection(control,value):
    io.closed(control,0xD1F108,'long')
    require(value['entry']=='$D1F108' and value['kind']=='long' and
        value['entry_m8'] is True and value['entry_x8'] is False and value['entry_irq_masked'] is True,'D projection entry')
    for k,v in (('entry_b',0),('entry_d',0),('entry_dbr',126),('return_b',0),('return_d',0),('return_dbr',126)):
        require(type(value[k]) is int and value[k]==v,'exact D projection scalar')
    for k in ('instruction_contexts','decoded_context_identity_sha256','decoded_byte_intervals','mnemonic_context_counts','direct_calls','return_width_states'):
        require(value[k]==control[k],'full D projection/typed context agreement: '+k)
    require(type(value['maximum_counted_bytes_including_long_frame']) is int and
        value['maximum_counted_bytes_including_long_frame']==7 and
        control['maximum_additional_bytes_below_callee_entry']==4 and
        type(control['maximum_additional_bytes_below_callee_entry']) is int and
        control['maximum_counted_bytes_including_root_call_frame']==7 and
        type(control['maximum_counted_bytes_including_root_call_frame']) is int,'D projection exact stack composition')
    require(value['d_is_zero_throughout_body'] is False and value['body_data_values_proved'] is False and
        value['branch_conditions_overapproximated'] is True and value['all_return_paths_checked'] is True and
        value['nonstack_aliases_and_asynchronous_preservation_proved'] is False and value['termination_proved'] is False,
        'D projection scope')
    require(type(value['d_transitions']) is list and
        serial(value['d_transitions'])==serial(D_TRANSITIONS),'exact typed temporary/restored D transitions')


def audit(rom,previous,census):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==prior.ROM_SHA,'canonical ROM identity')
    def read(p,n):
        require(type(p) is int and type(n) is int and n>0 and 0xC00000<=p<p+n<=0x1000000,'canonical read extent')
        return rom[p-0xC00000:p-0xC00000+n]
    control_walk,decode,value_walk,derivation=derive_models()
    spans=[]
    for p,z,h in SPANS:
        require(sha(read(p,z-p))==h,'exact v2 selected source span')
        spans.append({'start':cpu(p),'end_exclusive':cpu(z),'sha256':h})
    accepted=[r for r in census['conditional_handler_contracts'] if r['frontier'] is None]
    require(len(accepted)==114,'exact accepted closed direct corpus')
    retained=[]
    for old in accepted:
        new=control_walk(read,int(old['entry'][1:],16),'near')
        require(new==old,'accepted direct-control projection changed')
        retained.append({'entry':old['entry'],'unchanged_contract_sha256':sha(io.canonical(new))})
    require(previous['primary_conditional_returns']['closed_targets']==27 and
        previous['primary_conditional_returns']['all_29_composed'] is False and
        [r['physical_index'] for r in previous['primary_conditional_returns']['unclosed_targets']]==[9,13],
        'preserved scene80 v1 frontier set')
    require(previous['primary_conditional_returns']['closed_physical_indices']==[i for i in range(29) if i not in (9,13)] and
        previous['primary_conditional_returns']['maximum_additional_for_27_closed_only']==3 and
        previous['primary_conditional_returns']['total_including_existing_near_frame_for_27_closed_only']==5 and
        previous['primary_conditional_returns']['all_27_closed_return_b']==0 and
        previous['primary_conditional_returns']['all_27_closed_return_d']==0 and
        previous['primary_conditional_returns']['all_27_closed_return_dbr']==126,'preserved first27 return contract')
    mvp_control=control_walk(read,0xCD2BFC,'near')
    mvp_value=value_walk(read,0xCD2BFC,'near',entry_b=0,entry_dbr=126)
    mvp_contract=prior.validate_closed(mvp_control,mvp_value)
    require(mvp_contract['additional_bytes']==0 and
        mvp_control['return_width_states']==[{'site':'$CD2C7E','m8':True,'x8':False,'irq_masked':True}],
        'MVP target exact return')
    moves=[]
    for site,a,x,y in ((0xCD2C07,0x01AF,0x08BF,0x08FF),(0xCD2C13,0x001A,0x091B,0x091F)):
        require(read(site,3)==bytes((0x44,0x7E,0x7E)),'exact native MVP bank operands')
        moves.append({'site':cpu(site),'entry_a':a,'entry_x':x,'entry_y':y,'source_bank':126,
            'completion':mvp_completion(a,x,y,126)})
    d_control=control_walk(read,0xD1F108,'long');d_value=d_routine_projection(read,decode)
    compare_d_projection(d_control,d_value)
    caller=control_walk(read,0xCD2B64,'near');io.closed(caller,0xCD2B64,'near')
    require(read(0xCD2B64,5)==bytes((0x22,0x08,0xF1,0xD1,0x60)) and
        caller['direct_calls']==[{'site':'$CD2B64','target':'$D1F108','kind':'long'}] and
        caller['maximum_additional_bytes_below_callee_entry']==7 and
        caller['maximum_counted_bytes_including_root_call_frame']==9 and
        caller['return_width_states']==[{'site':'$CD2B68','m8':True,'x8':False,'irq_masked':True}],
        'exact single long call and near return composition')
    return {'schema':'project-epoch-scene80-remaining-returns-v2','date':'2026-10-03','evidence_level':'verified-static',
        'history':{'unaccepted_draft_date':'2026-09-08','resumed_authoring_date':'2026-10-03',
            'unaccepted_draft_source_sha256':'0fc2ec5cc26d3c376871659f92fa11bada61ca0fc9c00ae172156f515a8c285d',
            'prerequisite_evidence_date':'2026-09-08','native_run_performed':False},
        'canonical_rom':{'size':len(rom),'sha256':prior.ROM_SHA},'derivation':derivation,'source_spans':spans,
        'preserved_114_direct_control_contracts':retained,
        'preserved_scene80_v1_primary':previous['primary_conditional_returns'],
        'preserved_scene80_v1_secondary_census_sha256':sha(io.canonical(previous['secondary_hypothetical_census'])),
        'mvp_target':{'physical_index':9,'control':mvp_control,'value':mvp_value,'composition':mvp_contract,'exact_moves':moves},
        'temporary_d_target':{'physical_index':13,'callee_control':d_control,'callee_value':d_value,'caller_control':caller,
            'conditional_composition':{'root_near_bytes':2,'long_call_bytes':3,'callee_local_peak_bytes':4,
                'maximum_additional_below_root_entry':7,'total_counted_bytes':9,'dispatch_jump_frame_bytes':0,
                'return':'$CD2B68','return_b':0,'return_d':0,'return_dbr':126,'m8':True,'x8':False,'irq_masked':True}},
        'combined_first29_conditional_result':{'prior_closed_targets':27,'new_closed_targets':2,'total_conditional_targets':29,
            'conditional_additional_peak':7,'conditional_total_including_existing_near_frame':9,
            'all_return_b':0,'all_return_d':0,'all_return_dbr':126,'legal_parameter_domain_proved':False},
        'premises':['Native near scene entry M1/X0/I1 B0/D0/DBR7E and an ordinary two-byte root frame.',
            'MVP completion projection is only native M16/X16; it decrements X/Y and full A until A=FFFF.',
            'No nonstack CPU/DMA or asynchronous alias modifies code, saved D/X bytes, return frames or architectural registers.',
            'The D1F108 body explicitly runs with D=0A00; only both proved return paths restore the original D0.',
            'Memory loads/arithmetic values are unknown and all branches are followed; no timing or loop termination claim.',
            'Selection among the first29 physical words is conditional topology, not a legal game-data or script invariant.'],
        'secondary_128_census_recomputed_or_promoted':False,'game_input_domain_proved':False,
        'effective_memory_or_dma_alias_closure':False,'asynchronous_preservation_proved':False,
        'whole_scene80_arbitrary_input_closed':False,'whole_nmi_stack_bound':None,
        'termination_or_timing_proved':False,'new_native_execution':False,'production_approval':False}


def collect():
    before={k:io.identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()}
    own=[io.identity(ROOT/p) for p in (SOURCE,TESTS)]
    require(Path(prior.__file__).resolve()==ROOT/PINS['scene80_source'][0],'exact prior import')
    previous=prior.collect();p,n,h=PINS['scene80_reference']
    require(serial(previous)==io.read_file(ROOT/p,h,n),'scene80 v1 exact reference reproduction')
    p,n,h=prior.PINS['handler_reference'];census=json.loads(io.read_file(ROOT/p,h,n))
    inherited=list(previous['prerequisites'].values())+list(previous['source_identities'].values())+previous['transitive_source_identities']
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'consistent inherited identity')
        expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/p,h) for p,h in sorted(expected.items())]
    result=audit(io.read_file(prior.ROM,prior.ROM_SHA,0x400000),previous,census)
    primary=ROOT/'private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h'
    raw=io.read_file(primary,'9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd',27673)
    lines=raw.splitlines(keepends=True)
    result['reviewed_cpu_semantic_spans']=[{'path':primary.relative_to(ROOT).as_posix(),'first_line':a,'last_line_inclusive':z,
        'sha256':sha(b''.join(lines[a-1:z])),'role':role,'interpretation':'reviewer-derived semantics under pinned primary source'}
        for a,z,role in ((744,769,'MVP destination/source operand order; X/Y and A decrement; completion FFFF'),
            (4,33,'Add8 preserves high A in binary and decimal arithmetic'),
            (73,80,'ADC applies active accumulator width'),(1261,1266,'direct-page indexed X addressing'),
            (801,806,'PHD always saves full D word'),(831,838,'PLD always consumes a full saved word'),
            (859,863,'PHX follows active X width'),(1078,1081,'TDC copies full D to A'))]
    shared=ROOT/'private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h'
    shared_raw=io.read_file(shared,'dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f',20483)
    shared_lines=shared_raw.splitlines(keepends=True)
    for line,recipe in ((109,b'case 0x44: AddrMode_BlkMov(); MVP(); break;'),
                        (158,b'case 0x75: AddrMode_DirIdxX(); ADC(); break;')):
        require(shared_lines[line-1].strip()==recipe,'exact reviewed opcode/addressing/operation binding')
        result['reviewed_cpu_semantic_spans'].append({'path':shared.relative_to(ROOT).as_posix(),
            'first_line':line,'last_line_inclusive':line,'sha256':sha(shared_lines[line-1]),
            'role':'exact added opcode/addressing/operation binding',
            'interpretation':'reviewer-derived semantics under pinned primary source'})
    result.update(prerequisites=before,source_identities=own,transitive_source_identities=transitive,
        primary_cpu_sources=previous['primary_cpu_sources'],reproduce=['python','-B',SOURCE],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    require(before=={k:io.identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()} and own==[io.identity(ROOT/p) for p in (SOURCE,TESTS)],
        'own or prerequisite source drift')
    require(transitive==[io.identity(ROOT/p,h) for p,h in sorted(expected.items())],'underlying source drift')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
