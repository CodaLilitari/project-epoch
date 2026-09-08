"""Conditional source-only CEE7CC pointer producer and copy-suffix contract.

All byte inputs to the selected CD35A5 producer are evaluated in binary mode.
No legal game-data domain, memory-alias closure or native behavior is inferred.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_scene_handler_values_v1 as prior

ROOT=Path(__file__).resolve().parents[1]
SOURCE='tools/audit_schala_scene_copy_pointer_v1.py'
TESTS='tests/test_schala_scene_copy_pointer_v1.py'
PINS={
 'value_source':('tools/audit_schala_scene_handler_values_v1.py',21359,'b92e5ff6534cb6383754753fa484ac6c4e8d38fab68e6645d207db9e47796610'),
 'value_tests':('tests/test_schala_scene_handler_values_v1.py',8109,'6c3d7e6f1b1da9c2b9166452842a4dcb0bf93b2b942905b154b615a5017f7601'),
 'value_reference':('references/schala_scene_handler_values_v1.json',376981,'cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543'),
}
SPANS=((0xCD1F53,0xCD1FA0,'a911d9a7ad75d7f7cd3398c393b6f315988542f1e4fe3ba343337193806f179c'),
 (0xCD35A5,0xCD362D,'412b23a839d23381ea61eae0404170796fa45a5f0f73734bf2f377be2ae69a6b'),
 (0xCD362D,0xCD3657,'ca5056f3c6ef530ef4732dcf7614e754f7fc6b996e2ab2b894a3c2de475bb6bf'),
 (0xCEE1C7,0xCEE7CF,'c949db8bcd330b1682a19cd5a24b312bf31822f5350bac4e030a79e5798459de'),
 (0xCEE1C1,0xCEE1C7,'00d4bff3acfb6686bfb44bd130c72099249cd5772ffe617ae144eae86f73ee2b'))
START,STOP,RTS=0xCD35A5,0xCD362D,0xCEE7C7
sha=prior.sha
serial=prior.serial
require=prior.require


def input_contract(r,s,*,b=0,d=0,dbr=0x7E,decimal=False):
    for name,v in [('r',r),('s',s)]:
        require(type(v) is int and 0<=v<=255,'exact byte input '+name)
    require(type(b) is int and b==0 and type(d) is int and d==0
            and type(dbr) is int and dbr==0x7E,'B0/D0/DBR7E required')
    require(decimal is False,'binary arithmetic required')


def evaluate(read,r,s,*,b=0,d=0,dbr=0x7E,decimal=False):
    """Concrete finite projection of actual producer instructions to CD362D.

    Memory input CAAA.low=0 is explicit; CAAA.high remains unknown until the
    exact immediate AND #0001 removes it. CAA4/CAA8 are external byte values.
    Every DP read must have an earlier byte writer; arithmetic is concrete.
"""
    input_contract(r,s,b=b,d=d,dbr=dbr,decimal=decimal)
    pc=START;a=0;x=y=None;m8=True;carry=negative=zero=None
    dp={};contexts=[];owners={};lengths={};frames=[];counts=[];source_reads=[];pointer_writers={};unknown_high=False
    def get_dp(address,width):
        require(all(((address+i)&65535) in dp for i in range(width)),'uninitialized producer DP read')
        return sum(dp[(address+i)&65535]<<(8*i) for i in range(width))
    def put_dp(address,v,width):
        for i in range(width):
            dest=(address+i)&65535;dp[dest]=(v>>(8*i))&255
            if dest in (0x4B,0x4C):pointer_writers[dest]=pc
    def flags(v,eight_bit=None):
        nonlocal negative,zero
        small=m8 if eight_bit is None else eight_bit
        negative=bool(v & (0x80 if small else 0x8000));zero=v==0
    def set_a(v):
        nonlocal a
        v &= 255 if m8 else 65535
        a=(a&0xFF00)|v if m8 else v;flags(v)
    for step in range(200):
        if pc==STOP:
            require(frames==[0xCD3612] and len(counts)==1 and not m8 and not unknown_high,'exact producer call context')
            require(pointer_writers=={0x4B:0xCD362B,0x4C:0xCD362B},'exact final pointer byte writers')
            return {'pointer':get_dp(0x4B,2),'doubled_count':counts[0],
                'a':a,'x':x,'y':y,'m8':m8,'contexts':contexts,'source_reads':source_reads,
                'last_pointer_writer':0xCD362B,'frame_returns':frames}
        require(START<=pc<STOP and not 0xCD3612<=pc<0xCD3616,'producer control extent')
        require(pc not in owners or owners[pc]==pc,'producer control overlaps an operand')
        op,name,raw=prior.decode(read,pc,m8,False)
        require(pc+len(raw)<=STOP,'producer instruction crosses stop')
        require(pc not in lengths or lengths[pc]==len(raw),'producer width-dependent instruction length')
        lengths[pc]=len(raw)
        for address in range(pc,pc+len(raw)):
            require(address not in owners or owners[address]==pc,'producer instruction overlap')
            owners[address]=pc
        contexts.append((pc,m8,False));nxt=pc+len(raw);width=1 if m8 else 2;mask=255 if m8 else 65535
        operand=int.from_bytes(raw[1:],'little')
        require(not unknown_high or (pc==0xCD3601 and op==0x29 and operand==1 and not m8),
                'unknown word high byte must be removed by exact next AND')
        if op in (0xAD,0xBD):
            require(op!=0xBD or type(x) is int,'uninitialized producer X read')
            address=operand+(x if op==0xBD else 0)
            require((m8 and address in (0xCAAA,0xCAA4,0xCAA8))
                    or (pc==0xCD35FE and op==0xAD and not m8 and address==0xCAAA),
                    'exact external producer byte or masked word read')
            source_reads.append((pc,0x7E0000+address,width))
            set_a({0xCAAA:0,0xCAA4:r,0xCAA8:s}[address])
            if not m8:unknown_high=True
        elif op==0xAA:x=a;flags(x,False)  # X16 includes B.
        elif op==0xA8:y=a;flags(y,False)
        elif op==0x84:
            require(type(y) is int,'uninitialized producer Y read');put_dp(operand,y,2)
        elif op==0x85:
            put_dp(operand,a,width)
            if pc==0xCD361D:counts.append(a)
        elif op==0xA5:set_a(get_dp(operand,width))
        elif op==0xA9:set_a(operand)
        elif op==0xC2:
            require(raw[1]==0x20,'only REP M16 belongs to producer');m8=False
        elif op==0x38:carry=True
        elif op==0x18:carry=False
        elif op in (0x65,0x69,0xE5,0xE9):
            require(type(carry) is bool,'uninitialized producer carry read')
            value=get_dp(operand,width) if op in (0x65,0xE5) else operand
            total=(a&mask)+value+int(carry) if op in (0x65,0x69) else (a&mask)-value-int(not carry)
            carry=total>mask if op in (0x65,0x69) else total>=0
            set_a(total)
        elif op==0x49:set_a((a&mask)^operand)
        elif op==0x29:
            set_a((a&mask)&operand);unknown_high=False
        elif op==0x1A:set_a(a+1)
        elif op in (0x0A,0x06):
            value=(a&mask) if op==0x0A else get_dp(operand,width)
            carry=bool(value & (0x80 if m8 else 0x8000));value=(value<<1)&mask
            if op==0x0A:set_a(value)
            else:put_dp(operand,value,width);flags(value)
        elif op==0x64:put_dp(operand,0,width)
        elif op==0xC9:
            value=(a&mask)-operand;carry=value>=0;flags(value&mask)
        elif op in (0x10,0x90):
            require(type(negative if op==0x10 else carry) is bool,'uninitialized producer branch flag')
            take=not negative if op==0x10 else not carry
            if take:nxt+=int.from_bytes(raw[1:],'little',signed=True)
        elif op==0x20:
            require(pc==0xCD360F and operand==0x3616 and not m8,'exact near producer call')
            frames.append(nxt);nxt=(pc&0xFF0000)|operand
        else:raise ValueError(f'unsupported producer opcode {op:02X}')
        pc=nxt
    raise ValueError('producer instruction budget exhausted')


def closed_form(r,s):
    """Independent integer expression, compared against every CPU evaluation."""
    input_contract(r,s)
    return r+min(r,s)-max(r+max(r,s)-222,0)


def ladder(read):
    require(read(RTS,1)==b'\x60','exact ladder RTS')
    rows=[]
    for n in range(1,257):
        pc=RTS-6*n
        expected=b'\xB9'+(2*(n-1)).to_bytes(2,'little')+b'\x9D'+(4*(n-1)).to_bytes(2,'little')
        require(read(pc,6)==expected,'exact LDA/STA pair geometry')
        rows.append({'pairs':n,'entry':f'${pc:06X}','source_offset':2*(n-1),'destination_offset':4*(n-1)})
    before=b'\xB9'+(512).to_bytes(2,'little')+b'\x9D'+(1024).to_bytes(2,'little')
    require(read(RTS-6*257,6)!=before,'ladder extends beyond reviewed 256-pair boundary')
    return {'start':'$CEE1C7','rts':'$CEE7C7','physical_pairs':256,
        'physical_suffix_entries':257,'source_stride':2,'destination_stride':4,
        'native_width_contract':'M16/X16','pair_instruction_bytes':6,
        'suffix_additional_stack_bytes':0,'suffixes':[{'pairs':0,'entry':'$CEE7C7'}]+rows,
        'memory_addresses_values_and_aliasing_proved':False}


def return_path(read,arm):
    """Consume the exact typed frames after a separately validated suffix."""
    require(type(arm) is int and arm in (0,1),'exact continuation arm')
    frames=[('near',None,2),('near',0xCD1F9F,2),('near',0xCD3612,2),
            ('long',0xCD3644 if arm else 0xCD3656,3),('near',0xCEE7CB,2)]
    pc=RTS;m8=False;acc=None;events=[]
    for _ in range(16):
        op=read(pc,1)[0]
        if op in (0x60,0x6B):
            kind='near' if op==0x60 else 'long'
            require(frames and frames[-1][0]==kind,'typed continuation frame mismatch')
            before=sum(x[2] for x in frames);_,target,_=frames.pop()
            require(kind!='near' or target is None or target>>16==pc>>16,'near continuation PBR mismatch')
            events.append({'site':f'${pc:06X}','kind':kind,'before_bytes':before,
                'after_bytes':sum(x[2] for x in frames),'return':'abstract-caller' if target is None else f'${target:06X}'})
            if target is None:
                require(not frames and m8 and acc==0 and pc==0xCD1F9F,'complete root continuation')
                return events
            pc=target
        elif op==0x80:
            require(pc==0xCD3644,'only original continuation branch')
            pc=(pc&0xFF0000)|((pc+2+int.from_bytes(read(pc+1,1),'little',signed=True))&65535)
            require(pc==0xCD3656,'exact branch continuation')
        elif op==0x7B:
            require(pc==0xCD3612,'exact return TDC');acc=0;pc+=1
        elif op==0xE2:
            require(pc==0xCD3613 and read(pc+1,1)==b'\x20','exact return SEP M8')
            m8=True;pc+=2
        else:raise ValueError('unsupported continuation instruction')
    raise ValueError('continuation budget exhausted')


def continuation_contract(read):
    # Exact source bytes, separate from pointer arithmetic and game-data domain.
    for pc,raw in ((0xCD1F96,b'\x7B\xE2\x20\x9C\xAA\xCA\x20\xA5\x35\x60'),
                   (0xCD3612,b'\x7B\xE2\x20\x60'),
                   (0xCD3640,b'\x22\xC8\xE7\xCE\x80\x10'),
                   (0xCD3652,b'\x22\xC8\xE7\xCE\x60'),
                   (0xCEE7C8,b'\x20\xCC\xE7\x6B\x6C\x4B\x00')):
        require(read(pc,len(raw))==raw,'exact caller/wrapper/continuation bytes')
    return {'producer_final_store':'$CD362B -> DP $4B/$4C',
        'consumer':'$CEE7CC JMP ($004B) reads $00004B/$00004C; PBR stays CE',
        'producer_consumer_same_physical_pointer_requires_d_zero':True,
        'pointer_written_before_both_long_calls':True,
        'caller_prefix_if_call_reached':'$CD1F96 TDC; SEP #$20; STZ $CAAA; JSR $35A5',
        'call_stack_at_indirect_jump':[{'return':p,'kind':k,'bytes':n} for p,k,n in (
            ('abstract-caller','near',2),('$CD1F9F','near',2),('$CD3612','near',2),
            ('$CD3644 or $CD3656','long',3),('$CEE7CB','near',2))],
        'counted_bytes_including_root_near_frame':11,'additional_bytes_below_root_entry':9,
        'return_sequence':['RTS $CEE7C7 -> $CEE7CB','RTL $CEE7CB -> $CD3644 or $CD3656',
            '$CD3644 BRA $CD3656 if first arm','RTS $CD3656 -> $CD3612',
            'TDC; SEP #$20; RTS $CD3615 -> $CD1F9F','RTS $CD1F9F -> abstract caller'],
        'conditional_return_b0_d0_dbr7e':True,
        'typed_return_paths':[{'arm':arm,'returns':return_path(read,arm)} for arm in (0,1)],
        'whole_b5_b6_contract_closed':False}


def audit(rom):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==prior.ROM_SHA,'canonical ROM identity')
    def read(p,n):
        require(type(p) is int and type(n) is int and n>0 and 0xC00000<=p<p+n<=0x1000000,'canonical source extent')
        return rom[p-0xC00000:p-0xC00000+n]
    spans=[]
    for a,b,digest in SPANS:
        require(sha(read(a,b-a))==digest,'exact pointer source span')
        spans.append({'start':f'${a:06X}','end_exclusive':f'${b:06X}','sha256':digest})
    physical=ladder(read);continuations=continuation_contract(read)
    valid={RTS-6*n for n in range(257)};counts=Counter();invalid=[];contexts=set();reads=set();digest=hashlib.sha256()
    good=0
    for r in range(256):
        for s in range(256):
            result=evaluate(read,r,s);n=closed_form(r,s)
            require(result['doubled_count']==(2*n)&65535,'closed form disagrees with exact count')
            require(result['pointer']==(0xE7C7-6*n)&65535,'closed form disagrees with pointer')
            target=0xCE0000|result['pointer'];safe=target in valid
            require(safe==(abs(r-s)<=222),'exhaustively checked safe relation differs')
            counts[n]+=1;good+=int(safe)
            if not safe and (r,s) in ((0,223),(0,255),(223,0),(255,0),(255,32)):
                invalid.append({'r':r,'s':s,'signed_pair_count':n,'pointer':f'${target:06X}'})
            contexts.update(tuple(x) for x in result['contexts']);reads.update(result['source_reads'])
            digest.update(bytes((r,s,int(safe)))+result['doubled_count'].to_bytes(2,'little')+result['pointer'].to_bytes(2,'little'))
    require(min(counts)==-33 and max(counts)==222 and good==64414,'exact enumerated domain changed')
    return {'schema':'project-epoch-scene-copy-pointer-v1','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':prior.ROM_SHA},'source_spans':spans,
        'selected_entry':'$CD35A5 with CAAA=0, byte CAA4=r and CAA8=s',
        'input_combinations':65536,'binary_projection_contexts':[{'pc':f'${p:06X}','m8':m,'x8':x} for p,m,x in sorted(contexts)],
        'external_read_sites':[{'site':f'${p:06X}','bus_address':f'${a:06X}','width_bytes':w} for p,a,w in sorted(reads)],
        'unknown_caab_word_read':'CD35FE M16 LDA includes unknown CAAB; immediate CD3601 AND #0001 removes all high bits before any use or branch.',
        'matrix_sha256':digest.hexdigest(),'matrix_serialization':'r,s,safe as bytes; doubled-count and pointer as little-endian words; r-major then s',
        'independently_compared_formula':'n = r + min(r,s) - max(r + max(r,s) - 222, 0); pointer = (E7C7 - 6*n) mod 65536',
        'safe_relation_exhaustively_compared':'abs(r-s) <= 222','safe_input_pairs':good,'unsafe_input_pairs':65536-good,
        'pair_count_distribution':[{'n':n,'input_pairs':c} for n,c in sorted(counts.items())],
        'unsafe_input_examples':invalid,'producer_selected_safe_suffix_counts':list(range(223)),
        'physical_ladder':physical,'conditional_continuations':continuations,
        'premises':['Native M8/X16/I1 producer entry with B=0, D=0, DBR=7E and decimal flag clear.',
            'CAAA=0 and stable byte values at CAA4/CAA8; DP bytes read after their actual modeled writes.',
            'Ordinary writable stack; nonstack writes do not alias saved frames, pointer or input values.',
            'No asynchronous register/status/memory change while these conditional paths execute.',
            'Only when the derived safe relation holds does the selected suffix/return composition apply.'],
        'game_input_domain_proved':False,'whole_b5_b6_contract_closed':False,'whole_nmi_bound':None,
        'effective_memory_alias_closure':False,'dma_effects_proved':False,'native_execution':False,'production_approval':False}


def collect():
    identity=prior.bodies.identity
    pins={k:identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()}
    own=[identity(ROOT/p) for p in (SOURCE,TESTS)]
    previous=prior.collect();p,n,h=PINS['value_reference']
    require(serial(previous)==prior.bodies.read_file(ROOT/p,h,n),'accepted value prerequisite no longer reproduces')
    inherited=previous['reused_underlying_source_identities']+list(previous['prerequisites'].values())+previous['source_identities']
    unique={}
    for item in inherited:
        require(item['path'] not in unique or unique[item['path']]==item['sha256'],'inconsistent inherited identity')
        unique[item['path']]=item['sha256']
    transitive=[identity(ROOT/p,h) for p,h in sorted(unique.items())]
    p,n,h=prior.PINS['scene_reference']
    census=json.loads(prior.bodies.read_file(ROOT/p,h,n))
    historical=next(x for x in census['conditional_handler_contracts'] if x['entry']=='$CD1F53')
    frontier=historical['frontier']
    require(frontier['site']=='$CEE7CC' and frontier['counted_stack_bytes_at_frontier']==11
        and frontier['incoming_width_state']=={'m8':False,'x8':False,'irq_masked':True},'accepted original indirect frontier differs')
    require(frontier['active_call_return_sites']==[{'return':p,'kind':k} for p,k in (
        ('abstract-caller','near'),('$CD1F9F','near'),('$CD3612','near'),('$CD3644','long'),('$CEE7CB','near'))],
        'accepted original typed frame chain differs')
    result=audit(prior.bodies.read_file(prior.ROM,prior.ROM_SHA,0x400000))
    result['preserved_original_open_frontier']=frontier
    cpu_path=ROOT/'private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h'
    raw=prior.bodies.read_file(cpu_path,'9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd',27673)
    lines=raw.splitlines(keepends=True)
    result['reviewed_cpu_semantic_spans']=[{'path':cpu_path.relative_to(ROOT).as_posix(),
        'first_line':first,'last_line_inclusive':last,'sha256':sha(b''.join(lines[first-1:last])),
        'role':role,'interpretation':'reviewer-derived semantics over pinned source'}
        for first,last,role in ((35,160,'binary word ADC/SBC carry and result truncation'),
            (403,432,'JMP keeps PBR; JSL and JSR push far/near frames'),
            (479,501,'RTL and RTS restore distinct frame types'),
            (1216,1222,'absolute-indirect pointer reads bank zero, independent of D and DBR'))]
    result.update(prerequisites=pins,source_identities=own,reused_underlying_source_identities=transitive,
        primary_cpu_sources=previous['primary_cpu_sources'],
        reproduce=['python','-B',SOURCE],serialization='UTF-8 indented JSON, LF, one trailing newline')
    require(own==[identity(ROOT/p) for p in (SOURCE,TESTS)],'own source drift')
    require(pins=={k:identity(ROOT/p,h,n) for k,(p,n,h) in PINS.items()},'prerequisite drift')
    require(transitive==[identity(ROOT/p,h) for p,h in sorted(unique.items())],'inherited source drift')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
