"""Read-only conditional scroll-input value proof and four-cell target closure.

The value projection follows every direct callee. Memory reads are unknown,
branches take both edges, and nonstack aliases/asynchronous effects are premises.
This is not an emulator, a complete producer census, or whole-NMI approval.
"""
from __future__ import annotations
from collections import Counter, deque
import argparse
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_nmi_mode_bodies_v1 as bodies
import audit_schala_package_normal_nmi_closure_v2 as closure

ROOT=Path(__file__).resolve().parents[1]
ROM=bodies.ROM
ROM_SHA=bodies.ROM_SHA
PINS={
 **bodies.PINS,
 'mode_bodies':('tools/audit_schala_nmi_mode_bodies_v1.py',13937,'9b685d63e68153d1c7d56213af5b1211237c3f36d067046a9e854ae5beb34187'),
 'mode_body_tests':('tests/test_schala_nmi_mode_bodies_v1.py',8308,'3bccabc53eda3357079a2db236c37cbd81e1cf139c6e5c5ec913ee0facb38833'),
 'mode_body_reference':('references/schala_nmi_mode_bodies_v1.json',160900,'f3057c1cf9d0b354a318e3e67b2c760fdf9d8bfc49784d4efed344ba997a8d85'),
 'ce_annotation':('private/research/ct_disassembly_eeae27a/bank_CE.asm',67102,'23b885667ad4f454ed95f4d441253378cb40964c3e2d543120f5f9c1288a35ad'),
 'cf_annotation':('private/research/ct_disassembly_eeae27a/bank_CF.asm',300449,'f2783556f4963cbeb75b320c996a3fd8e5da6d435009aa8c1516086c65ed02a6'),
}
CALLEES=((0xCD09CE,'long'),(0xCD3EB4,'near'),(0xCD0607,'near'),
         (0xC10009,'long'),(0xCD0AEE,'near'),(0xCD05B2,'near'))
TARGETS=((0xCD06C4,0,0xCD076B),(0xCD076C,0,0xCD076B),
         (0xCD07E2,0,0xCD088C),(0xCD07B9,2,0xCD07E1))
LIMITS={
 'global_ca92_producer_domain_proved':False,'complete_table_extent_proved':False,
 'callee_memory_read_values_proved':False,'nonstack_alias_closure':False,
 'dma_effects_proved':False,'termination_proved':False,'timing_proved':False,
 'asynchronous_entry_proved':False,'whole_nmi_stack_bound':None,
 'production_approval':False,'new_native_execution':False,
}
sha=bodies.sha
serial=bodies.serial
require=bodies.require
cpu=bodies.cpu


def exact_byte(value,name,unknown=False):
    require((unknown and value is None) or type(value) is int and 0<=value<=255,'exact byte '+name)


def decode(read,pc,m8,x8):
    """Reuse the unchanged closure opcode/width inventory, not its value semantics."""
    raw=read(pc,1);require(type(raw) is bytes and len(raw)==1,'one opcode byte')
    op=raw[0]
    if op in closure.prior.irq.M_IMMEDIATES:name,n=closure.prior.irq.M_IMMEDIATES[op],2 if m8 else 3
    elif op in closure.prior.irq.X_IMMEDIATES:name,n=closure.prior.irq.X_IMMEDIATES[op],2 if x8 else 3
    elif op in closure.prior.irq.BRANCHES or op==0x80:name,n='branch',2
    else:
        require(op in closure.FIXED,'unsupported decode opcode')
        name,n=closure.FIXED[op]
    require((pc&65535)+n<=65536,'instruction bank crossing')
    raw=read(pc,n);require(type(raw) is bytes and len(raw)==n,'exact instruction extent')
    return op,name,raw


def value_walk(read,entry,kind,*,entry_b=None,entry_dbr=None,stops=(),budget=30000):
    """Project A bytes/DBR with invariant D=0 and exact typed native call frames.

    Arithmetic, memory loads and index-to-A transfers conservatively forget the
    visible A width. Immediate loads, TDC and stack transfers retain byte values.
    Unknown means any byte; no branch is pruned from a computed flag. X/Y values,
    flags besides M/X/I, effective addresses and memory contents are not modeled.
    """
    exact_byte(entry_b,'entry B',True);exact_byte(entry_dbr,'entry DBR',True)
    require(kind in ('near','long') and type(entry) is int and 0xC00000<=entry<0x1000000,'entry namespace')
    require(type(budget) is int and 1<=budget<=100000,'state budget')
    require(type(stops) is tuple and all(type(x) is int and 0xC00000<=x<0x1000000 for x in stops)
            and len(set(stops))==len(stops),'exact stop sites')
    # Data cells are ('data', byte). Frame cells cannot be consumed by pulls.
    root=('frame','root',kind);root_size=2 if kind=='near' else 3
    # pc, M, X, I, A.low, A.high, DBR, stack bottom->top, active frames
    queue=deque([(entry,True,False,True,None,entry_b,entry_dbr,(root,)*root_size,(('root',kind),))])
    seen=set();decoded={};owners={};calls=set();edges=set();ends=set();peak=root_size
    while queue:
        state=queue.popleft()
        if state in seen:continue
        seen.add(state);require(len(seen)<=budget,'value state budget exhausted')
        pc,m8,x8,masked,lo,hi,dbr,old_stack,old_frames=state
        require(0xC00000<=pc<0x1000000,'control flow outside canonical high ROM')
        if pc in stops:
            ends.add((pc,'stop',m8,x8,masked,lo,hi,dbr,old_stack,old_frames));continue
        op,name,raw=decode(read,pc,m8,x8)
        for address in range(pc,pc+len(raw)):
            require(address not in owners or owners[address]==pc,'overlapping instruction decode')
            owners[address]=pc
        key=(pc,m8,x8)
        require(not any(k[0]==pc and v[1]!=len(raw) for k,v in decoded.items()),'width-dependent overlapping decode')
        decoded[key]=(name,len(raw),sha(raw))
        stack=list(old_stack);frames=list(old_frames)
        nxt=(pc&0xFF0000)|((pc+len(raw))&65535);dest=[nxt]
        def push(values):stack.extend(('data',x) for x in reversed(values))
        def pull(count):
            require(len(stack)>=count and all(x[0]=='data' for x in stack[-count:]),'software pull consumes call frame')
            return tuple(stack.pop()[1] for _ in range(count))
        def forget_a():
            nonlocal lo,hi
            lo=None
            if not m8:hi=None
        if op in (0xC2,0xE2):
            on=op==0xE2
            if raw[1]&0x20:m8=on
            if raw[1]&0x10:x8=on
            if raw[1]&4:masked=on
        elif op==0x48:push((lo,) if m8 else (lo,hi))
        elif op==0x68:
            values=pull(1 if m8 else 2);lo=values[0]
            if not m8:hi=values[1]
        elif op==0x8B:push((dbr,))
        elif op==0xAB:dbr=pull(1)[0]
        elif op in (0xDA,0x5A):push((None,)*(1 if x8 else 2))
        elif op in (0xFA,0x7A):pull(1 if x8 else 2)
        elif op==0xA9:
            lo=raw[1]
            if not m8:hi=raw[2]
        elif op==0x7B:lo=hi=0  # TDC copies all 16 D bits, even in M8.
        elif op==0x54:
            require(not m8 and not x8,'MVN projection requires native M16/X16')
            # Mesen pinned encoding: first operand destination, second source.
            lo=hi=255;dbr=raw[1]
        elif op in (0x20,0x22):
            call_kind='near' if op==0x20 else 'long'
            target=int.from_bytes(raw[1:],'little')|(pc&0xFF0000 if op==0x20 else 0)
            marker=('frame',nxt,call_kind);stack.extend([marker]*(2 if op==0x20 else 3))
            frames.append((nxt,call_kind));calls.add((pc,target,call_kind));dest=[target]
        elif op in (0x60,0x6B):
            call_kind='near' if op==0x60 else 'long'
            require(frames and frames[-1][1]==call_kind,'return call kind mismatch')
            target,_=frames.pop();n=2 if op==0x60 else 3
            require(stack[-n:]==[('frame',target,call_kind)]*n,'return frame value mismatch')
            del stack[-n:]
            if target=='root':
                require(not stack and not frames,'unbalanced root return')
                require(op!=0x60 or pc>>16==entry>>16,'root near return bank differs')
                ends.add((pc,'return',m8,x8,masked,lo,hi,dbr,(),()));continue
            require(op!=0x60 or pc>>16==target>>16,'nested near return bank differs')
            dest=[target]
        elif op==0x4C:dest=[(pc&0xFF0000)|int.from_bytes(raw[1:],'little')]
        elif op==0x5C:dest=[int.from_bytes(raw[1:],'little')]
        elif op in closure.prior.irq.BRANCHES or op in (0x80,0x82):
            target=(pc&0xFF0000)|((nxt+int.from_bytes(raw[1:],'little',signed=True))&65535)
            dest=[target] if op in (0x80,0x82) else [nxt,target]
        elif op==0x78:masked=True
        elif name.startswith('LDA ') or name in ('TXA','TYA','ASL A','LSR A','INC A','DEC A') or name.split()[0] in ('ADC','SBC','AND','ORA','EOR'):
            forget_a()
        elif (name.split()[0] in ('STA','STX','STY','STZ','CMP','CPX','CPY','BIT','TSB','TRB')
              or name.startswith(('LDX ','LDY '))
              or name in ('CLC','SEC','TAX','TAY','INX','INY','DEX','DEY','NOP')
              or name.split()[0] in ('INC','DEC','LSR') and name.endswith(('dp','abs','abs,X'))):
            pass  # No architectural A/D/DBR/SP/M/X/I effect.
        else:
            raise ValueError(f'unsupported value effect {op:02X} at {pc:06X}')
        require(masked,'IRQ unmasking outside projection')
        require(len(stack)<=512 and len(frames)<=64,'stack budget exhausted')
        peak=max(peak,len(stack));edges.update((pc,p) for p in dest)
        queue.extend((p,m8,x8,masked,lo,hi,dbr,tuple(stack),tuple(frames)) for p in dest)
    require(ends,'no bounded stop or balanced return')
    intervals=[]
    for address in sorted(owners):
        if intervals and intervals[-1][1]==address:intervals[-1][1]+=1
        else:intervals.append([address,address+1])
    end_rows=[]
    for pc,why,m8,x8,masked,lo,hi,dbr,stack,frames in sorted(ends,key=repr):
        end_rows.append({'site':cpu(pc),'kind':why,'m8':m8,'x8':x8,'irq_masked':masked,
          'a_low':lo,'b':hi,'d':0,'dbr':dbr,'counted_stack_bytes':len(stack),
          'frames':[{'return':'abstract-caller' if r=='root' else cpu(r),'kind':k} for r,k in frames]})
    return {'entry':cpu(entry),'kind':kind,'entry_b':entry_b,'entry_d':0,'entry_dbr':entry_dbr,
      'entry_m8':True,'entry_x8':False,'entry_irq_masked':True,'abstract_states':len(seen),
      'instruction_contexts':len(decoded),'direct_calls':[{'site':cpu(s),'target':cpu(t),'kind':k} for s,t,k in sorted(calls)],
      'decoded_context_identity_sha256':sha(bodies.canonical(sorted((k,v) for k,v in decoded.items()))),
      'edge_identity_sha256':sha(bodies.canonical(sorted(edges))),
      'decoded_byte_intervals':[{'start':cpu(a),'end_exclusive':cpu(b),'sha256':sha(read(a,b-a))} for a,b in intervals],
      'mnemonic_context_counts':dict(sorted(Counter(v[0] for v in decoded.values()).items())),
      'ends':end_rows,'exploratory_peak_counted_bytes_not_a_whole_path_bound':peak,
      'd_invariant_proved_under_no_alias_no_asynchronous_premises':True,
      'all_direct_callees_inlined':True,'branch_conditions_overapproximated':True,
      'nonstack_memory_and_dma_effects_proved':False,'termination_proved':False}


def pointer_recipe(value,b):
    exact_byte(value,'CA92');exact_byte(b,'B')
    index=(b<<8)|((value<<1)&255)
    return {'ca92':value,'b':b,'x':index,'pointer_low':0xCD0000|((0x06BC+index)&65535),
            'pointer_high':0xCD0000|((0x06BD+index)&65535)}


def verify_caller(row):
    require(row['entry']=='$CD088D' and row['kind']=='near' and row['entry_b'] is None
        and row['entry_d']==0 and row['entry_dbr']==0,'caller exact entry contract')
    selected=[x for x in row['ends'] if x['site']=='$CD0929']
    other=[x for x in row['ends'] if x['site']!='$CD0929']
    require(selected and other and all(x['site']=='$CD0907' and x['kind']=='stop' for x in other),'bounded caller path partition')
    require(all(x['kind']=='stop' and x['m8'] is True and x['x8'] is False and x['irq_masked'] is True
        and type(x['b']) is int and x['b']==0 and type(x['d']) is int and x['d']==0
        and type(x['dbr']) is int and x['dbr']==0x7E
        and type(x['counted_stack_bytes']) is int and x['counted_stack_bytes']==2
        and x['frames']==[{'return':'abstract-caller','kind':'near'}] for x in selected),'scroll caller values/frame unproved')
    return {'site':'$CD0929','b':0,'d':0,'dbr':126,'m8':True,'x8':False,'irq_masked':True,
        'conditional_on_reaching_scroll_call_before_the_other_branch_cut':True,'outgoing_near_return':'$CD092C',
        'other_branch_cut_before_external_pad_route':'$CD0907','other_branch_returns_or_rejoins_proved':False,
        'incoming_b_not_required_zero':True,'callee_register_preservation_assumed':False,
        'ca92_effective_read_address':'$7ECA92','ca92_value_domain_proved':False}


def audit(rom,prior):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(address,n):
        require(type(address) is int and type(n) is int and n>0 and 0xC00000<=address<address+n<=0x1000000,'read bounds')
        return rom[address-0xC00000:address-0xC00000+n]
    require(sha(read(0xCD06B4,8))=='0016098af9a67c4facae3dd092e328de1da7bb6e0c74f4ec5075db44779827d7','dispatch span')
    caller=value_walk(read,0xCD088D,'near',entry_dbr=0,stops=(0xCD0907,0xCD0929))
    contract=verify_caller(caller)
    callees=[]
    for entry,kind in CALLEES:
        previous=next(x for x in prior['direct_callee_contracts'] if x['entry']==cpu(entry) and x['kind']==kind)
        bodies.closed(previous,entry,kind)
        row=value_walk(read,entry,kind,entry_b=0,entry_dbr=0x7E)
        require(row['decoded_byte_intervals']==previous['decoded_byte_intervals'],'callee value/width source coverage differs')
        require(row['direct_calls']==previous['direct_calls'],'callee inlined call inventory differs')
        require(all(e['kind']=='return' and e['b']==0 and e['d']==0 and e['dbr']==0x7E
            and e['m8'] is True and e['x8'] is False and e['irq_masked'] is True for e in row['ends']),'callee conditional value return differs')
        row['prior_typed_closure_metadata_sha256']=sha(bodies.canonical(previous));callees.append(row)
    table=read(0xCD06BC,8);target_rows=[]
    for i,(target,additional,ret) in enumerate(TARGETS):
        require(0xCD0000|int.from_bytes(table[2*i:2*i+2],'little')==target,'four-cell target differs')
        row=closure.walk_direct(read,target,'near',entry_m8=True,entry_x8=False)
        bodies.closed(row,target,'near')
        require(row['maximum_additional_bytes_below_callee_entry']==additional
            and row['return_width_states']==[{'site':cpu(ret),'m8':True,'x8':False,'irq_masked':True}],'reviewed target return/stack differs')
        target_rows.append({'cell_index':i,'pointer':cpu(0xCD06BC+2*i),'target':cpu(target),
            'b0_aliasing_ca92_bytes':[i,i+128],'conditional_target_closure':row,
            'new_frame_added_by_dispatch_jmp':0,'existing_scroll_jsr_frame_bytes':2,
            'conditional_scroll_call_bytes_including_existing_near_frame':2+additional,
            'target_register_value_return_proved':False})
    selected=[];wraps=0;aliases=0
    for b in range(256):
        for value in range(128):
            p=pointer_recipe(value,b);q=pointer_recipe(value+128,b)
            require(p['x']==q['x'] and p['pointer_low']==q['pointer_low'] and p['pointer_high']==q['pointer_high'],'high-bit alias recipe')
            aliases+=1;wraps+=p['pointer_low']&65535==65535
            if b==0:
                selected.append({'ca92_low7':value,'pointer':cpu(p['pointer_low']),
                    'target':cpu(0xCD0000|int.from_bytes(read(p['pointer_low'],2),'little')),
                    'among_four_reviewed_cells':value<4})
    require(wraps==0 and aliases==32768 and selected[4]['target']=='$CD10E2','dispatch enumeration differs')
    return {'schema':'project-epoch-nmi-scroll-inputs-v1','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},'caller_value_projection':caller,
        'caller_contract':contract,'six_callee_value_projections':callees,
        'dispatch':{'span':['$CD06B4','$CD06BC'],'sha256':sha(read(0xCD06B4,8)),
            'absolute_read_requires_dbr_7e':True,'direct_page_not_used_by_ca92_absolute_read':True,
            'recipe':'X = (B << 8) | ((CA92 << 1) & 255); pointer word read in PBR CD with 16-bit address arithmetic',
            'hypothetical_byte_b_pairs':65536,'high_bit_alias_pairs':aliases,
            'pointer_word_boundary_wrap_pairs':wraps,'base_plus_index_can_wrap_in_pbr':True,
            'b0_possible_physical_cells':selected,'four_reviewed_span':['$CD06BC','$CD06C4'],
            'four_reviewed_span_sha256':sha(table),
            'first_successor_overlaps_executable_instruction':{'site':'$CD06C4','mnemonic':'SEP #$10',
                'instruction_sha256':sha(read(0xCD06C4,2)),'interpreted_pointer_target':'$CD10E2',
                'legal_input_or_free_space_proved':False}},
        'four_conditional_targets':target_rows,
        'premises':['Native M1/X0/I1 mode-body near entry; D=0 and DBR=0 come from the separately reproduced mode-input prefix.',
          'Unknown memory loads range over every byte; conditional branches take both edges, without flag feasibility pruning.',
          'Ordinary writable typed stack; no nonstack CPU write or DMA alias modifies stack frames or the pinned instruction bytes.',
          'No intervening asynchronous handler or externally changing architectural registers; the decoder refuses SP reassignment and every D-changing instruction.',
          'Caller proof stops at CD0907 before the external-pad route; only paths reaching CD0929 before that cut are claimed.',
          'A selected CA92 byte among the eight listed aliases is an additional explicit premise for four-target composition.'],
        **LIMITS}


def collect():
    sources={key:bodies.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    owned=[Path(__file__).resolve(),ROOT/'tests/test_schala_nmi_scroll_inputs_v1.py']
    before=[bodies.identity(p) for p in owned]
    require(Path(bodies.__file__).resolve()==ROOT/PINS['mode_bodies'][0]
        and Path(closure.__file__).resolve()==ROOT/PINS['closure'][0],'exact imported dependency paths')
    accepted=bodies.collect()
    require(serial(accepted)==bodies.read_file(ROOT/PINS['mode_body_reference'][0],PINS['mode_body_reference'][2],PINS['mode_body_reference'][1]),'accepted mode bodies no longer reproduce')
    prior=json.loads(bodies.read_file(ROOT/bodies.PINS['closure_reference'][0],bodies.PINS['closure_reference'][2],bodies.PINS['closure_reference'][1]))
    inherited=accepted['reused_closure_source_identities']+accepted['reused_primary_cpu_sources']+list(accepted['reused_mode_input_sources'].values())
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited identity')
        expected[item['path']]=item['sha256']
    transitive=[bodies.identity(ROOT/path,digest) for path,digest in sorted(expected.items())]
    rom=bodies.read_file(ROM,ROM_SHA,0x400000)
    result=audit(rom,prior)
    result['prerequisites']=sources
    result['reproduced_mode_body_reference_sha256']=sha(serial(accepted))
    result['source_identities']=before
    result['reused_underlying_source_identities']=transitive
    result['primary_instruction_sources']=prior['primary_instruction_sources']
    result['reproduce']=['python','-B','tools/audit_schala_nmi_scroll_inputs_v1.py']
    result['serialization']='UTF-8 indented JSON, LF, one trailing newline'
    require(before==[bodies.identity(p) for p in owned],'owned source changed while collecting')
    require(sources=={key:bodies.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()},'prerequisite source changed')
    require(transitive==[bodies.identity(ROOT/path,digest) for path,digest in sorted(expected.items())],'underlying source changed')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    sys.stdout.buffer.write(serial(collect()));return 0


if __name__=='__main__':raise SystemExit(main())
