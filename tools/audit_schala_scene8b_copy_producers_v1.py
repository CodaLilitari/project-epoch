"""Conditional scene8B producer counts, q-data ownership and typed copy returns.

Read-only canonical-source evidence; no legal game domain or native claim.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_scene8b_dispatch_inputs_v1 as prior
import audit_schala_scene_copy_pointer_v1 as copy
ROOT=Path(__file__).resolve().parents[1]
SOURCE='tools/audit_schala_scene8b_copy_producers_v1.py'
TESTS='tests/test_schala_scene8b_copy_producers_v1.py'
sha=prior.sha;serial=prior.serial;require=prior.require;io=prior.io
PRODUCERS={0xCD35A5:{'call':0xCD360F,'mask':0xCD3601,'conditional':False,'shape':'full'},
 0xCD352D:{'call':0xCD359E,'mask':0xCD358C,'conditional':True,'shape':'short'},
 0xCD347D:{'call':0xCD34EE,'mask':0xCD34DC,'conditional':True,'shape':'half'}}
STOP=0xCD362D
EXCLUDED_Q=(2,3,6,7)
PINS={
 'dispatch_source':('tools/audit_schala_scene8b_dispatch_inputs_v1.py',17345,'d71ceb87f2840ce59f7056ccecb904797de326e28ef9261e12e16fcbf0a607c6'),
 'dispatch_tests':('tests/test_schala_scene8b_dispatch_inputs_v1.py',7461,'1424f403932f3d5a3f106deac480c628c7f10957944d2b3398d7c2ed1f44622e'),
 'dispatch_reference':('references/schala_scene8b_dispatch_inputs_v1.json',124619,'f3cb6cef7e04c2dd101eb69ee4ccb212443ea3ea91e248f07ed2a586155609bf'),
 'copy_source':('tools/audit_schala_scene_copy_pointer_v1.py',18696,'e3fb94da358b0bd122d9e6f502cacd4fb424af0ec19831ccb89b0bb5ceb4e973'),
 'copy_tests':('tests/test_schala_scene_copy_pointer_v1.py',9614,'9dd6fb63ca9877da69226648a7de4fa3198b2bf67bdd6612ca0767bf655862ca'),
 'copy_reference':('references/schala_scene_copy_pointer_v1.json',70722,'13913c7b244b454a8afd4afd89977408466e2dda06699578f344b9c691789c53')}


def geometry(q):
    require(type(q) is int and 0<=q<=255,'exact q byte')
    r,s=0x7ECAA4+q,0x7ECAA8+q
    aliases=[{'input':name,'address':f'${p:06X}','word_part':'low' if p==0x7ECAAA else 'high'}
             for name,p in (('r',r),('s',s)) if p in (0x7ECAAA,0x7ECAAB)]
    return {'q':q,'r_address':r,'s_address':s,'parity':q&1,'aliases':aliases,'independent_projection_admitted':not aliases}


def input_contract(start,q,r,s,*,b=0,d=0,dbr=126,decimal=False):
    require(type(start) is int and start in PRODUCERS,'exact selected producer')
    require(geometry(q)['independent_projection_admitted'],'q-selected input aliases CAAA/CAAB; unresolved')
    copy.input_contract(r,s,b=b,d=d,dbr=dbr,decimal=decimal)


def evaluate(read,start,q,r,s,*,b=0,d=0,dbr=0x7E,decimal=False):
    """Concrete finite projection of actual producer instructions to CD362D.

    Stable CAAA.low=q; CAAA.high is unknown until the exact AND.
    Independent selected bytes r/s require q-alias refusal. Every q use is tagged.
    Every DP read must have an earlier byte writer; arithmetic is concrete.
"""
    input_contract(start,q,r,s,b=b,d=d,dbr=dbr,decimal=decimal)
    spec=PRODUCERS[start];call=spec["call"];continuation=call+3;mask_site=spec["mask"]
    pc=start;a=0;x=y=None;m8=True;carry=negative=zero=None
    at=xt=yt=fct=fnt=fzt=frozenset();dt={};taint_uses=[]
    dp={};contexts=[];owners={};lengths={};frames=[];counts=[];source_reads=[];pointer_writers={};unknown_high=False
    def get_dp(address,width):
        require(all(((address+i)&65535) in dp for i in range(width)),'uninitialized producer DP read')
        return sum(dp[(address+i)&65535]<<(8*i) for i in range(width))
    def dp_tags(address,width):
        return frozenset().union(*(dt[(address+i)&65535] for i in range(width)))
    def put_dp(address,v,width,tags=frozenset()):
        for i in range(width):
            dest=(address+i)&65535;dp[dest]=(v>>(8*i))&255;dt[dest]=tags
            if dest in (0x4B,0x4C):pointer_writers[dest]=pc
    def flags(v,eight_bit=None,tags=frozenset()):
        nonlocal negative,zero,fnt,fzt
        small=m8 if eight_bit is None else eight_bit
        negative=bool(v & (0x80 if small else 0x8000));zero=v==0;fnt=fzt=tags
    def set_a(v,tags=frozenset()):
        nonlocal a,at
        v &= 255 if m8 else 65535
        a=(a&0xFF00)|v if m8 else v;at=tags;flags(v,tags=tags)
    for step in range(200):
        if pc==STOP:
            require(frames==[continuation] and len(counts)==1 and not m8 and not unknown_high,'exact producer call context')
            require(pointer_writers=={0x4B:0xCD362B,0x4C:0xCD362B},'exact final pointer byte writers')
            require(not at and not yt and not dp_tags(0x4B,2),'q must not reach count/pointer/source Y')
            require(xt==frozenset(('qbit',)),'final X carries only q parity')
            return {'skipped':False,'q':q,'start':start,'taint_uses':taint_uses,'pointer':get_dp(0x4B,2),'doubled_count':counts[0],
                'a':a,'x':x,'y':y,'m8':m8,'contexts':contexts,'source_reads':source_reads,
                'last_pointer_writer':0xCD362B,'frame_returns':frames}
        if pc==continuation and not frames:
            require(spec['conditional'] and not m8 and not unknown_high and not fzt,'exact untainted skip context')
            return {'skipped':True,'q':q,'start':start,'taint_uses':taint_uses,'pointer':None,'doubled_count':0,
                'a':a,'x':x,'y':y,'m8':m8,'contexts':contexts,'source_reads':source_reads,'frame_returns':[]}
        require(start<=pc<=call or 0xCD3616<=pc<STOP,'producer control extent')
        require(pc not in owners or owners[pc]==pc,'producer control overlaps an operand')
        op,name,raw=prior.values.decode(read,pc,m8,False)
        require(pc+len(raw)<=STOP,'producer instruction crosses stop')
        require(pc not in lengths or lengths[pc]==len(raw),'producer width-dependent instruction length')
        lengths[pc]=len(raw)
        for address in range(pc,pc+len(raw)):
            require(address not in owners or owners[address]==pc,'producer instruction overlap')
            owners[address]=pc
        contexts.append((pc,m8,False));nxt=pc+len(raw);width=1 if m8 else 2;mask=255 if m8 else 65535
        operand=int.from_bytes(raw[1:],'little')
        require(not unknown_high or (pc==mask_site and op==0x29 and operand==1 and not m8),
                'unknown word high byte must be removed by exact next AND')
        if op in (0xAD,0xBD):
            require(op!=0xBD or type(x) is int,'uninitialized producer X read')
            address=operand+(x if op==0xBD else 0)
            if op==0xBD:
                require(m8 and x==q and xt==frozenset(('q',)) and operand in (0xCAA4,0xCAA8),
                    'only selected r/s reads consume full q as X')
                value=r if operand==0xCAA4 else s;tags=frozenset()
                taint_uses.append((pc,'q-selected-input',address))
            else:
                require(address==0xCAAA and ((pc==start and m8) or (pc==mask_site-3 and not m8)),
                    'exact external q byte or masked q word read')
                value=q;tags=frozenset(('q',));unknown_high=not m8
                taint_uses.append((pc,'q-load',width))
            source_reads.append((pc,0x7E0000+address,width));set_a(value,tags)
        elif op==0xAA:x=a;xt=at;flags(x,False,xt)
        elif op==0xA8:y=a;yt=at;flags(y,False,yt)
        elif op==0x84:
            require(type(y) is int,'uninitialized producer Y read');put_dp(operand,y,2,yt)
        elif op==0x85:
            put_dp(operand,a,width,at)
            if pc==0xCD361D:
                require(not at,'q must not reach doubled count');counts.append(a)
        elif op==0xA5:set_a(get_dp(operand,width),dp_tags(operand,width))
        elif op==0xA9:set_a(operand)
        elif op==0xC2:
            require(raw[1]==0x20,'only REP M16 belongs to producer');m8=False
        elif op==0x38:carry=True;fct=frozenset()
        elif op==0x18:carry=False;fct=frozenset()
        elif op in (0x65,0x69,0xE5,0xE9):
            require(type(carry) is bool,'uninitialized producer carry read')
            value=get_dp(operand,width) if op in (0x65,0xE5) else operand
            total=(a&mask)+value+int(carry) if op in (0x65,0x69) else (a&mask)-value-int(not carry)
            tags=at|fct|(dp_tags(operand,width) if op in (0x65,0xE5) else frozenset())
            carry=total>mask if op in (0x65,0x69) else total>=0
            fct=tags;set_a(total,tags)
        elif op==0x49:set_a((a&mask)^operand,at)
        elif op==0x29:
            require(pc==mask_site and operand==1 and at==frozenset(('q',)),'exact q high-bit elimination')
            set_a((a&mask)&operand,frozenset(('qbit',)));unknown_high=False
            taint_uses.append((pc,'q-bit0-mask',1))
        elif op==0x1A:set_a(a+1,at)
        elif op in (0x0A,0x06,0x4A):
            value=(a&mask) if op in (0x0A,0x4A) else get_dp(operand,width)
            tags=at if op in (0x0A,0x4A) else dp_tags(operand,width);fct=tags
            require(op!=0x4A or not m8,'only M16 LSR is newly admitted')
            carry=bool(value & (1 if op==0x4A else (0x80 if m8 else 0x8000)))
            value=(value>>1) if op==0x4A else (value<<1)&mask
            if op in (0x0A,0x4A):set_a(value,tags)
            else:put_dp(operand,value,width,tags);flags(value,tags=tags)
        elif op==0x64:put_dp(operand,0,width)
        elif op==0xC9:
            value=(a&mask)-operand;carry=value>=0;fct=at;flags(value&mask,tags=at)
        elif op==0xC4:
            require(not m8 and type(y) is int,'CPY uses initialized X16 Y')
            value=y-get_dp(operand,2);tags=yt|dp_tags(operand,2)
            carry=value>=0;fct=tags;flags(value&65535,False,tags)
        elif op in (0x10,0x90,0xF0):
            flag,tags=(negative,fnt) if op==0x10 else ((carry,fct) if op==0x90 else (zero,fzt))
            require(type(flag) is bool,'uninitialized producer branch flag')
            require(not tags,'q must not influence producer control')
            take=not flag if op in (0x10,0x90) else flag
            if take:nxt+=int.from_bytes(raw[1:],'little',signed=True)
        elif op==0x20:
            require(pc==call and operand==0x3616 and not m8,'exact near producer call')
            frames.append(nxt);nxt=(pc&0xFF0000)|operand
        else:raise ValueError(f'unsupported producer opcode {op:02X}')
        if at or xt or yt or any(dt.values()):
            taint_uses.append((pc,'post-state',','.join(sorted(at))+':'+','.join(sorted(xt))+':'+','.join(sorted(yt)),
                tuple((k,','.join(sorted(v))) for k,v in sorted(dt.items()) if v)))
        pc=nxt
    raise ValueError('producer instruction budget exhausted')



def count_formula(start,r,s):
    input_contract(start,0,r,s)
    high=r if PRODUCERS[start]['shape']=='full' else r//2
    return high+min(r,s)-max(high+max(r,s)-222,0)


def factorization(read):
    """Exact source-use templates plus all-q address geometry, separate from r/s."""
    rows=[]
    for start,spec in PRODUCERS.items():
        # Full q is used only as X for these two loads. A is overwritten by r,
        # then s; X is not otherwise read before its later parity-dependent TAX.
        prefix=bytes.fromhex('AD AA CA AA BD A4 CA A8 84 45 BD A8 CA A8 84 47 C2 20')
        require(read(start,len(prefix))==prefix,'exact selected-input q prefix')
        mask=spec['mask'];call=spec['call']
        tail=bytes.fromhex('AD AA CA 29 01 00 0A 85 45 A5 4F 0A 0A 18 65 45 AA')
        require(read(mask-3,len(tail))==tail,'exact q parity to X use chain')
        gap=bytes.fromhex('C4 4B F0 03') if spec['conditional'] else b''
        require(read(mask-3+len(tail),len(gap)+3)==gap+bytes.fromhex('20 16 36'),
                'exact conditional skip/near call after q data uses')
        require(mask-3+len(tail)+len(gap)==call,'exact source chain covers complete q tail')
        require(read(0xCD3616,23)==bytes.fromhex('84 45 A5 4B 38 E5 45 85 4B 0A 18 65 4B 85 4B A9 C7 E7 38 E5 4B 85 4B'),
                'exact count kernel overwrites q-derived DP45 before count use')
        rows.append({'producer':f'${start:06X}','initial_q_consumer':'X16 source selection only',
            'source_prefix_sha256':sha(prefix),'q_word_mask':f'${mask:06X}',
            'complete_parity_chain_sha256':sha(tail+gap+bytes.fromhex('20 16 36')),
            'helper_q_scratch_kill':'$CD3616 STY $45 overwrites both bytes before count arithmetic',
            'branches_must_have_no_q_taint':True,'count_and_pointer_must_have_no_q_taint':True,
            'final_x_taint':'q bit0 only','all_semantic_instruction_uses_covered_by_evaluator':True})
    geometry_rows=[geometry(q) for q in range(256)]
    require([x['q'] for x in geometry_rows if not x['independent_projection_admitted']]==list(EXCLUDED_Q),
            'exact unresolved alias q domain')
    return {'all_q_geometry':geometry_rows,'source_use_contracts':rows,
        'admitted_q_count':252,'excluded_q':list(EXCLUDED_Q),
        'q_full_data_influence':'Selected r/s addresses; loaded r/s are explicit independent input parameters.',
        'q_numerical_influence_after_source_selection':'Only q bit0 contributes 0 or2 to X; pointer/count/skip/Y independent.',
        'actual_exhaustive_cpu_workload':'Three producers x two q parity representatives x 65,536 r/s pairs = 393,216 evaluations.',
        'sixteen_million_case_execution_claim':False,'legal_game_q_domain_proved':False}


def emitter_contract(read,entry,expected_return):
    control=prior.handlers.walk_direct(read,entry,'near')
    value=prior.values.value_walk(read,entry,'near',entry_b=0,entry_dbr=126)
    prior.compare_models(control,value,entry)
    classification=prior.values.base.classify(value,control)
    require(classification['status']=='proved-B0-D0-DBR7E','emitter return register contract')
    require(control['maximum_additional_bytes_below_callee_entry']==0
            and control['maximum_counted_bytes_including_root_call_frame']==2,'emitter near frame only')
    require(control['return_width_states']==[{'site':f'${expected_return:06X}',
        'm8':True,'x8':False,'irq_masked':True}],'complete emitter return set')
    return {'entry':f'${entry:06X}','control':control,'value':value,'classification':classification,
        'termination_proved':False,'ordinary_or_wram_port_write_aliasing_proved':False}


def postcopy_contract(read,start):
    spec=PRODUCERS[start];entry=spec['call']+3
    final={0xCD35A5:0xCD3612,0xCD352D:0xCD35A1,0xCD347D:0xCD3529}[start]
    require(read(final,4)==bytes.fromhex('7B E2 20 60'),'exact cleanup TDC/SEP/RTS')
    typed=prior.handlers.walk_direct(read,entry,'near',entry_m8=False)
    require(typed['frontier'] is None and typed['status']=='closed-direct-stack-width-control-flow',
            'postcopy control must close in original model')
    require(typed['entry_m8'] is False and typed['entry_x8'] is False
            and typed['maximum_additional_bytes_below_callee_entry']==0
            and typed['maximum_counted_bytes_including_root_call_frame']==2,'postcopy M16 near frame only')
    require(typed['return_width_states']==[{'site':f'${final+3:06X}',
        'm8':True,'x8':False,'irq_masked':True}],'postcopy complete return site/width')
    # A complete narrow CFG checks that no branch can bypass TDC and enter SEP/RTS.
    queue=[(entry,False)];seen=set();owners={};decoded={};edges=set()
    allowed={0xA5,0x0A,0x85,0xAD,0x29,0xAA,0x18,0x65,0xF0,0x9D,0xE8,0xE4,0xD0,0x80,0x7B,0xE2,0x60}
    while queue:
        pc,m8=queue.pop()
        if (pc,m8) in seen:continue
        seen.add((pc,m8));require(len(seen)<=64,'postcopy CFG budget')
        require(entry<=pc<=final+3 and (pc not in owners or owners[pc]==pc),'postcopy control extent/operand ownership')
        op,name,raw=prior.values.decode(read,pc,m8,False)
        require(op in allowed and pc+len(raw)<=final+4,'postcopy register-neutral opcode/extent')
        require(not any(k[0]==pc and v[1]!=len(raw) for k,v in decoded.items()),'postcopy width overlap')
        for address in range(pc,pc+len(raw)):
            require(address not in owners or owners[address]==pc,'postcopy instruction overlap');owners[address]=pc
        decoded[(pc,m8,False)]=(name,len(raw),sha(raw));nxt=pc+len(raw)
        if op==0x60:
            require(pc==final+3 and m8,'exact postcopy return');continue
        if op==0xE2:
            require(pc==final+1 and raw==b'\xE2\x20','only final SEP M8');m8=True
        if op==0x7B:require(pc==final,'only final TDC')
        destinations=[nxt]
        if op in (0x80,0xD0,0xF0):
            target=nxt+int.from_bytes(raw[1:],'little',signed=True)
            destinations=[target] if op==0x80 else [target,nxt]
        for destination in destinations:
            edges.add((pc,destination));queue.append((destination,m8))
    require({a for a,b in edges if b==final+1}=={final}
        and {a for a,b in edges if b==final+3}=={final+1},'every return path owns TDC/SEP predecessors')
    require(sha(io.canonical(sorted(decoded.items())))==typed['decoded_context_identity_sha256'],
            'postcopy CFG/accepted decoder exact context identity')
    return {'entry':f'${entry:06X}','control':typed,'edge_identity_sha256':sha(io.canonical(sorted(edges))),
        'return_b0_d0_dbr7e_conditionally':True,'memory_effects_proved':False,'termination_proved':False,
        'reason':'Every returning path executes final TDC D0 then SEP20 then RTS; decoded operations never change D or DBR.'}


def typed_copy_return(read,start,arm):
    require(type(start) is int and start in PRODUCERS and type(arm) is int and arm in (0,1),'exact return route')
    continuation=PRODUCERS[start]['call']+3
    frames=[('near',None,2),('near',continuation,2),('long',0xCD3644 if arm else 0xCD3656,3),('near',0xCEE7CB,2)]
    events=[];pc=copy.RTS
    while pc!=continuation:
        op=read(pc,1)[0]
        if op==0x80:
            require(pc==0xCD3644 and read(pc,2)==b'\x80\x10','exact parity continuation branch')
            pc=0xCD3656;continue
        require(op in (0x60,0x6B),'exact near/long continuation opcode')
        kind='near' if op==0x60 else 'long'
        require(frames and frames[-1][0]==kind,'typed continuation mismatch')
        before=sum(z[2] for z in frames);_,target,_=frames.pop()
        require(target is not None and (kind=='long' or target>>16==pc>>16),'typed continuation PBR')
        events.append({'site':f'${pc:06X}','kind':kind,'return':f'${target:06X}',
            'counted_before':before,'counted_after':sum(z[2] for z in frames)})
        pc=target
    require(frames==[('near',None,2)],'postcopy original root near frame remains')
    return {'arm':arm,'events':events,'postcopy_entry':f'${continuation:06X}',
        'peak_counted_bytes_including_handler_near_frame':9,'copy_suffix_additional_bytes':0,
        'additional_bytes_below_handler_entry':7,'postcopy_near_frame_bytes':2}


def audit(rom):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==prior.values.ROM_SHA,'canonical ROM identity')
    def read(pc,n):
        require(type(pc) is int and type(n) is int and n>0 and 0xC00000<=pc<pc+n<=0x1000000,'canonical read extent')
        return rom[pc-0xC00000:pc-0xC00000+n]
    spans=[]
    for first,last,h in SPANS:
        require(sha(read(first,last-first))==h,'exact producer/continuation source span')
        spans.append({'start':f'${first:06X}','end_exclusive':f'${last:06X}','sha256':h})
    factor=factorization(read);physical=copy.ladder(read)
    # evaluate returns a bank-relative word; ladder entries are CE bus addresses.
    valid={(copy.RTS&65535)-6*n for n in range(257)}
    emitters=[emitter_contract(read,p,r) for p,r in ((0xCD31FE,0xCD3272),(0xCD3273,0xCD3336),(0xCD3337,0xCD33B4))]
    rows=[]
    for start,spec in PRODUCERS.items():
        counts=Counter();contexts=set();taints=set();skipped=safe=unsafe=0;digest=hashlib.sha256();examples=[]
        for r in range(256):
            for s in range(256):
                n=count_formula(start,r,s)
                pair=[]
                for q in (0,1):
                    value=evaluate(read,start,q,r,s);pair.append(value)
                    expected_skip=spec['conditional'] and n==0
                    require(value['skipped']==expected_skip,'concrete CPY/BEQ skip differs from independent count equality')
                    require(value['source_reads']==[(start,0x7ECAAA,1),(start+4,0x7ECAA4+q,1),
                        (start+10,0x7ECAA8+q,1),(spec['mask']-3,0x7ECAAA,2)],'complete producer source-read ownership')
                    if not value['skipped']:
                        require(value['doubled_count']==(2*n)&65535 and value['pointer']==(0xE7C7-6*n)&65535,
                            'independent count/pointer formula differs from executed instructions')
                    contexts.update(value['contexts']);taints.update(repr(v) for v in value['taint_uses'])
                    digest.update(bytes((q,r,s,int(value['skipped'])))+value['doubled_count'].to_bytes(2,'little')+
                        (value['pointer'] or 0).to_bytes(2,'little')+value['x'].to_bytes(2,'little')+value['y'].to_bytes(2,'little'))
                require(pair[0]['skipped']==pair[1]['skipped'] and pair[0]['pointer']==pair[1]['pointer']
                    and pair[0]['doubled_count']==pair[1]['doubled_count'] and pair[0]['y']==pair[1]['y']
                    and pair[1]['x']==(pair[0]['x']+2)&65535,'q parity may change only X by2')
                v=pair[0];good=v['skipped'] or v['pointer'] in valid
                require(good==(abs(r-s)<=222),'derived suffix-safe input relation differs')
                skipped+=int(v['skipped']);safe+=int(good);unsafe+=int(not good);counts[n]+=1
                if (r,s) in ((0,0),(0,222),(0,223),(0,255),(255,0),(255,32),(255,33),(255,255),(111,111),(148,148)):
                    examples.append({'r':r,'s':s,'signed_count':n,'skipped':v['skipped'],'pointer':None if v['pointer'] is None else f'${0xCE0000|v["pointer"]:06X}','suffix_safe_or_skipped':good})
        require(safe==64414 and unsafe==1122 and min(counts)==-33 and max(counts)==222,'exact producer domain census')
        rows.append({'entry':f'${start:06X}','shape':spec['shape'],'evaluations':131072,'independent_r_s_pairs':65536,
            'safe_or_skipped_pairs':safe,'unsafe_pairs':unsafe,'skipped_pairs':skipped,
            'count_distribution':dict(sorted(counts.items())),'matrix_sha256':digest.hexdigest(),
            'matrix_serialization':'r then s then q loops: q,r,s,skip bytes; count16,pointer16 (zero for skip),X16,Y16 little endian',
            'formula':'h+min(r,s)-max(h+max(r,s)-222,0), h=r for full or floor(r/2) for short/half',
            'suffix_safe_or_skipped_relation':'abs(r-s)<=222, derived exhaustively for this producer',
            'complete_contexts_sha256':sha(io.canonical(sorted(contexts))),
            'complete_q_taint_observations_sha256':sha(io.canonical(sorted(taints))),
            'examples':examples,'postcopy':postcopy_contract(read,start),
            'typed_copy_returns':[typed_copy_return(read,start,arm) for arm in (0,1)]})
    stubs=[]
    for target,emitter,producer in ((0xCD33B5,0xCD31FE,0xCD35A5),(0xCD33BB,0xCD3273,0xCD352D),
        (0xCD33C1,0xCD3273,0xCD347D),(0xCD33CD,0xCD3337,0xCD35A5)):
        expected=b'\x20'+(emitter&65535).to_bytes(2,'little')+b'\x4C'+(producer&65535).to_bytes(2,'little')
        require(read(target,6)==expected,'exact emitter call/producer jump route')
        stubs.append({'target':f'${target:06X}','emitter':f'${emitter:06X}','producer':f'${producer:06X}',
            'sequential_peak_counted_bytes':9,'composition':'max(root2+emitter2, root2+producer7)=9 on a copied suffix',
            'requires_safe_input_domain':True,'whole_target_closed_unconditionally':False})
    return {'schema':'project-epoch-scene8b-copy-producers-v1','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':prior.values.ROM_SHA},'source_spans':spans,
        'namespace':'Scene8B selected targets only; no action/package/PC mapping',
        'q_factorization':factor,'physical_copy_ladder':physical,'emitters':emitters,'producers':rows,'target_compositions':stubs,
        'premises':['Native M1/X0/I1, B0,D0,DBR7E at each emitter/producer boundary; decimal arithmetic clear.',
            'Stable q, selected r/s, other emitter inputs and pointer bytes; four alias q values remain unresolved.',
            'No ordinary CPU, WRAM-port, DMA or asynchronous write aliases live frames, code, source inputs or the indirect pointer.',
            'The selected route returns from its emitter; this proof does not establish emitter or postcopy-loop termination.',
            'The source-derived suffix predicate must hold; no legal game input domain was inferred.'],
        'q_alias_cases_unresolved':list(EXCLUDED_Q),'b5_b6_producer_contract_reused_as_general_authority':False,
        'legal_game_input_domain_proved':False,'whole_scene8b_closed':False,'whole_nmi_bound':None,
        'effective_memory_alias_closure':False,'dma_or_wram_port_ownership_proved':False,
        'native_execution':False,'production_approval':False}

SPANS=((13447678, 13448153, '5256285fef21abf116740e9dd929103a8cd4c424a4ce8d0b758ae61df31bfef7'), (13448317, 13448791, 'f344306d9d28a7bfc23c386f415c4f476fc07cfd7afd02742f4734cf1a6247dd'), (13558209, 13559759, 'beeb6d6132932cf9317b00d6790fa41192b61b73617e07ec0b5fe1bb588e66ff'))


def preserved_frontiers(previous):
    require(previous['open_targets']==['$CD33B5','$CD33BB','$CD33C1','$CD33CD'],
        'accepted four open target identities')
    result=[]
    for target,continuation in (('$CD33B5','$CD3612'),('$CD33BB','$CD35A1'),
                               ('$CD33C1','$CD34F1'),('$CD33CD','$CD3612')):
        matches=[x for x in previous['selected_targets'] if x['target']==target]
        require(len(matches)==1,'exact unique prior target')
        frontier=matches[0]['control']['frontier']
        require(frontier['site']=='$CEE7CC' and frontier['counted_stack_bytes_at_frontier']==9
            and frontier['incoming_width_state']=={'m8':False,'x8':False,'irq_masked':True},
            'accepted original target frontier/width/depth differs')
        require(frontier['active_call_return_sites']==[{'return':p,'kind':k} for p,k in (
            ('abstract-caller','near'),(continuation,'near'),('$CD3644','long'),('$CEE7CB','near'))],
            'accepted original target typed frame chain differs')
        result.append({'target':target,'frontier':frontier})
    return result


def collect():
    pins={k:io.identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()}
    own=[io.identity(ROOT/p) for p in (SOURCE,TESTS)]
    require(Path(prior.__file__).resolve()==ROOT/PINS['dispatch_source'][0]
        and Path(copy.__file__).resolve()==ROOT/PINS['copy_source'][0],'exact imported prerequisites')
    previous=prior.collect();baseline=copy.collect()
    for key,value in (('dispatch_reference',previous),('copy_reference',baseline)):
        p,n,h=PINS[key]
        require(serial(value)==io.read_file(ROOT/p,h,n),'accepted prerequisite no longer reproduces')
    expected={}
    for packet in (previous,baseline):
        for item in packet['reused_underlying_source_identities']+list(packet['prerequisites'].values())+packet['source_identities']:
            require(item['path'] not in expected or expected[item['path']]==item['sha256'],'consistent inherited sources')
            expected[item['path']]=item['sha256']
    transitive=[io.identity(ROOT/p,h) for p,h in sorted(expected.items())]
    frontiers=preserved_frontiers(previous)
    result=audit(io.read_file(prior.values.ROM,prior.values.ROM_SHA,0x400000))
    result['preserved_original_open_frontiers']=frontiers
    result['preserved_b5_b6_reference_sha256']=PINS['copy_reference'][2]
    cpu_path=ROOT/'private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h'
    raw=io.read_file(cpu_path,'9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd',27673)
    lines=raw.splitlines(keepends=True)
    result['reviewed_cpu_semantic_spans']=[{'path':cpu_path.relative_to(ROOT).as_posix(),
        'first_line':first,'last_line_inclusive':last,'sha256':sha(b''.join(lines[first-1:last])),
        'role':role,'interpretation':'reviewer-derived semantics over pinned source'}
        for first,last,role in ((173,176,'BEQ consumes the actual zero flag'),
            (354,391,'CPY compares at X width and establishes carry/zero/negative'),
            (602,614,'ShiftRight consumes low carry bit and establishes zero/negative'),
            (648,655,'LSR accumulator uses M width'),
            (35,160,'binary word ADC/SBC carry and truncation'),
            (479,501,'RTL and RTS consume distinct frames'),
            (1216,1222,'absolute-indirect pointer reads bank zero'))]
    require(previous['primary_cpu_sources']==baseline['primary_cpu_sources'],'consistent CPU source identities')
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
