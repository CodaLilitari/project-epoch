"""Three exact M16-LDA/taken-BEQ refinements over preserved scene values v1.

The immediate predecessor is part of each abstract state. Both branch edges
remain; only a proved taken zero edge assigns full A=0. No global flag model.
"""
from __future__ import annotations
from collections import Counter, deque
import argparse
import ast
import inspect
from pathlib import Path
import sys
import audit_schala_scene_handler_values_v1 as base

ROOT=Path(__file__).resolve().parents[1]
bodies=base.bodies
closure=base.closure
scene=base.scene
sha=base.sha
serial=base.serial
require=base.require
cpu=base.cpu
exact_byte=base.exact_byte
decode=base.decode
ROM=base.ROM
ROM_SHA=base.ROM_SHA
PINS={
 'value_v1':('tools/audit_schala_scene_handler_values_v1.py',21359,'b92e5ff6534cb6383754753fa484ac6c4e8d38fab68e6645d207db9e47796610'),
 'value_v1_tests':('tests/test_schala_scene_handler_values_v1.py',8109,'6c3d7e6f1b1da9c2b9166452842a4dcb0bf93b2b942905b154b615a5017f7601'),
 'value_v1_reference':('references/schala_scene_handler_values_v1.json',376981,'cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543'),
}
# branch -> (immediate word-LDA predecessor, taken destination, DP operand)
REFINEMENTS={0xD1FA49:(0xD1FA47,0xD1FA65,0x45),
             0xD1FAC9:(0xD1FAC7,0xD1FAE5,0x49),
             0xD1FB49:(0xD1FB47,0xD1FB65,0x49)}
SPANS=(
 (0xD1FA47,0xD1FA4B,'12b5b20d2cf244802019e00efd0380b88cf2d33264d7f8d909a4b0aeeb0131b8'),
 (0xD1FA64,0xD1FA68,'052b462218d0e720daca46617ff0a556d75683287a65e4c870290344635bbf5c'),
 (0xD1FAC7,0xD1FACB,'376265e47c5d1a903b5472ac440b8b574a95fdf3240cacaaef7b6cdd557ebecb'),
 (0xD1FAE4,0xD1FAE8,'052b462218d0e720daca46617ff0a556d75683287a65e4c870290344635bbf5c'),
 (0xD1FB47,0xD1FB4B,'376265e47c5d1a903b5472ac440b8b574a95fdf3240cacaaef7b6cdd557ebecb'),
 (0xD1FB64,0xD1FB68,'052b462218d0e720daca46617ff0a556d75683287a65e4c870290344635bbf5c'),
)
LIMITS={**base.LIMITS,'complete_legal_command_or_script_domain_proved':False,
        'global_zero_flag_tracking_added':False,'new_native_execution':False}


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
    queue=deque([(entry,True,False,True,None,entry_b,entry_dbr,(root,)*root_size,(('root',kind),),None)])
    seen=set();decoded={};owners={};calls=set();edges=set();ends=set();peak=root_size;refined_edges=set()
    while queue:
        state=queue.popleft()
        if state in seen:continue
        seen.add(state);require(len(seen)<=budget,'value state budget exhausted')
        pc,m8,x8,masked,lo,hi,dbr,old_stack,old_frames,previous_pc=state
        require(0xC00000<=pc<0x1000000,'control flow outside canonical high ROM')
        if pc in stops:
            ends.add((pc,'stop',m8,x8,masked,lo,hi,dbr,old_stack,old_frames));continue
        op,name,raw=decode(read,pc,m8,x8)
        require(pc not in REFINEMENTS or op==0xF0,'refined site must decode BEQ')
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
        elif op==0xEB:lo,hi=hi,lo  # XBA swaps both bytes regardless of M.
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
            if pc in REFINEMENTS:
                load,taken,operand=REFINEMENTS[pc]
                require(op==0xF0 and previous_pc==load and not m8 and target==taken
                    and load+2==pc and read(load,2)==bytes((0xA5,operand)),
                    'refined edge requires exact immediate M16 LDA predecessor')
                refined_edges.add((pc,load,taken,m8,x8,masked))
        elif op==0x78:masked=True
        elif name.startswith('LDA ') or name in ('TXA','TYA','ASL A','LSR A','INC A','DEC A') or name.split()[0] in ('ADC','SBC','AND','ORA','EOR'):
            forget_a()
        elif (name.split()[0] in ('STA','STX','STY','STZ','CMP','CPX','CPY','BIT','TSB','TRB')
              or name.startswith(('LDX ','LDY '))
              or name in ('CLC','SEC','TAX','TAY','INX','INY','DEX','DEY','NOP','TYX')
              or name.split()[0] in ('INC','DEC','LSR','ASL','ROL') and name.endswith(('dp','abs','abs,X'))):
            pass  # No architectural A/D/DBR/SP/M/X/I effect.
        else:
            raise ValueError(f'unsupported value effect {op:02X} at {pc:06X}')
        require(masked,'IRQ unmasking outside projection')
        require(len(stack)<=512 and len(frames)<=64,'stack budget exhausted')
        peak=max(peak,len(stack));edges.update((pc,p) for p in dest)
        for p in dest:
            edge_lo,edge_hi=(0,0) if pc in REFINEMENTS and p==REFINEMENTS[pc][1] else (lo,hi)
            queue.append((p,m8,x8,masked,edge_lo,edge_hi,dbr,tuple(stack),tuple(frames),pc))
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
      'nonstack_memory_and_dma_effects_proved':False,'termination_proved':False,
      'refined_zero_edges':[{'branch':cpu(p),'immediate_predecessor':cpu(prev),'taken_target':cpu(t),
          'm8':m,'x8':x,'irq_masked':i,'taken_edge_full_a':0,'both_successors_retained':True}
          for p,prev,t,m,x,i in sorted(refined_edges)]}


def verify_derivation():
    expected=inspect.getsource(base.value_walk)
    changes=(
      ("(('root',kind),))])","(('root',kind),),None)])"),
      ('seen=set();decoded={};owners={};calls=set();edges=set();ends=set();peak=root_size',
       'seen=set();decoded={};owners={};calls=set();edges=set();ends=set();peak=root_size;refined_edges=set()'),
      ('pc,m8,x8,masked,lo,hi,dbr,old_stack,old_frames=state',
       'pc,m8,x8,masked,lo,hi,dbr,old_stack,old_frames,previous_pc=state'),
      ('op,name,raw=decode(read,pc,m8,x8)',
       "op,name,raw=decode(read,pc,m8,x8)\n        require(pc not in REFINEMENTS or op==0xF0,'refined site must decode BEQ')"),
      ('dest=[target] if op in (0x80,0x82) else [nxt,target]',
       """dest=[target] if op in (0x80,0x82) else [nxt,target]
            if pc in REFINEMENTS:
                load,taken,operand=REFINEMENTS[pc]
                require(op==0xF0 and previous_pc==load and not m8 and target==taken
                    and load+2==pc and read(load,2)==bytes((0xA5,operand)),
                    'refined edge requires exact immediate M16 LDA predecessor')
                refined_edges.add((pc,load,taken,m8,x8,masked))"""),
      ('queue.extend((p,m8,x8,masked,lo,hi,dbr,tuple(stack),tuple(frames)) for p in dest)',
       """for p in dest:
            edge_lo,edge_hi=(0,0) if pc in REFINEMENTS and p==REFINEMENTS[pc][1] else (lo,hi)
            queue.append((p,m8,x8,masked,edge_lo,edge_hi,dbr,tuple(stack),tuple(frames),pc))"""),
      ("'nonstack_memory_and_dma_effects_proved':False,'termination_proved':False}",
       """'nonstack_memory_and_dma_effects_proved':False,'termination_proved':False,
      'refined_zero_edges':[{'branch':cpu(p),'immediate_predecessor':cpu(prev),'taken_target':cpu(t),
          'm8':m,'x8':x,'irq_masked':i,'taken_edge_full_a':0,'both_successors_retained':True}
          for p,prev,t,m,x,i in sorted(refined_edges)]}"""),
    )
    for before,after in changes:
        require(expected.count(before)==1,'unique declared source replacement')
        expected=expected.replace(before,after)
    require(ast.dump(ast.parse(expected))==ast.dump(ast.parse(inspect.getsource(value_walk))),'undeclared v2 model change')
    return {'predecessor_tracked_in_abstract_state':True,'both_branch_successors_retained':True,
        'only_three_named_taken_edges_assign_full_a_zero':True,
        'only_declared_ast_changes':True,'global_zero_flag_tracking_added':False,
        'v1_walker_source_sha256':sha(inspect.getsource(base.value_walk).encode()),
        'v2_walker_source_sha256':sha(inspect.getsource(value_walk).encode())}


def audit(rom,prior,census):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    require(prior['summary']['all_returns_b0_d0_dbr7e_targets']==111
        and prior['summary']['unresolved_b_entries']==['$CD1805','$CD19B1','$CD2460'],'preserved v1 boundary differs')
    def read(p,n):
        require(type(p) is int and type(n) is int and n>0 and 0xC00000<=p<p+n<=0x1000000,'canonical read bounds')
        return rom[p-0xC00000:p-0xC00000+n]
    spans=[]
    for start,end,pin in SPANS:
        require(sha(read(start,end-start))==pin,'named refinement source span differs')
        spans.append({'start':cpu(start),'end_exclusive':cpu(end),'size':end-start,'sha256':pin})
    results=[];projections=[];changes=[];edges=set()
    typed=[x for x in census['conditional_handler_contracts'] if x['frontier'] is None]
    require(len(typed)==114,'exact 114 closed typed targets')
    for row in typed:
        entry=row['entry'];previous=next(x for x in prior['conditional_return_contracts'] if x['entry']==entry)
        old_projection=next(x for x in prior['value_projections'] if x['entry']==entry)
        require(base.value_walk(read,int(entry[1:],16),'near',entry_b=0,entry_dbr=126)==old_projection,'v1 target projection no longer reproduces')
        values=value_walk(read,int(entry[1:],16),'near',entry_b=0,entry_dbr=126)
        result=base.classify(values,row)
        require(result['status']=='proved-B0-D0-DBR7E','new target return remains unproved')
        result['commands_at_b_zero']=previous['commands_at_b_zero'];results.append(result);projections.append(values)
        if previous['status']!=result['status']:
            changes.append({'entry':entry,'commands_at_b_zero':result['commands_at_b_zero'],
                'preserved_v1_status':previous['status'],'new_status':result['status'],
                'previous_contract_sha256':sha(bodies.canonical(previous)),
                'new_contract_sha256':sha(bodies.canonical(result))})
        for edge in values['refined_zero_edges']:
            branch=int(edge['branch'][1:],16);load,target,_=REFINEMENTS[branch]
            require(edge=={'branch':cpu(branch),'immediate_predecessor':cpu(load),'taken_target':cpu(target),
                'm8':False,'x8':False,'irq_masked':True,'taken_edge_full_a':0,'both_successors_retained':True},'exact canonical refined edge state differs')
            edges.add(branch)
    require([x['entry'] for x in changes]==['$CD1805','$CD19B1','$CD2460'] and edges==set(REFINEMENTS),'exact changed target/edge set')
    return {'schema':'project-epoch-scene-handler-return-values-v2','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},'scope':'same 114 closed scene targets, exact three word-load zero edges',
        'derivation':verify_derivation(),'named_refinement_spans':spans,
        'changed_target_contracts':changes,'conditional_return_contracts':results,'value_projections':projections,
        'excluded_control_flow_open_targets':prior['excluded_control_flow_open_targets'],
        'summary':{'selected_targets':114,'selected_cells':114,'v1_proved_targets':111,'v1_unresolved_b_targets':3,
            'v2_b0_d0_dbr7e_targets':114,'v2_unresolved_b_targets':0,'refined_branch_sites':3,
            'excluded_open_targets':7,'excluded_open_cells':8},
        'premises':prior['premises'][:-1]+[
            'At each named BEQ, the immediate executed predecessor is its exact M16 LDA with no intervening instruction or asynchronous register/status change.',
            'Only the taken edge is refined to full A=0; the fallthrough remains conservative and both control-flow edges remain.',
            'These 114 conditional target returns do not close the other seven targets or establish a legal command-loop invariant.'],
        **LIMITS}


def collect():
    pins={key:bodies.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    owned=[Path(__file__).resolve(),ROOT/'tests/test_schala_scene_handler_values_v2.py'];own=[bodies.identity(p) for p in owned]
    require(Path(base.__file__).resolve()==ROOT/PINS['value_v1'][0],'exact imported v1 path')
    prior=base.collect()
    require(serial(prior)==bodies.read_file(ROOT/PINS['value_v1_reference'][0],PINS['value_v1_reference'][2],PINS['value_v1_reference'][1]),'accepted v1 reference no longer reproduces')
    census=scene.collect()
    path,size,digest=base.PINS['scene_reference']
    require(serial(census)==bodies.read_file(ROOT/path,digest,size),'accepted scene census no longer reproduces')
    inherited=prior['reused_underlying_source_identities']+list(prior['prerequisites'].values())
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited identity')
        expected[item['path']]=item['sha256']
    transitive=[bodies.identity(ROOT/path,digest) for path,digest in sorted(expected.items())]
    result=audit(bodies.read_file(ROM,ROM_SHA,0x400000),prior,census)
    result.update(prerequisites=pins,source_identities=own,reused_underlying_source_identities=transitive,
        primary_cpu_sources=prior['primary_cpu_sources'],
        reproduce=['python','-B','tools/audit_schala_scene_handler_values_v2.py'],serialization='UTF-8 indented JSON, LF, one trailing newline')
    require(own==[bodies.identity(p) for p in owned],'own source changed')
    require(pins=={key:bodies.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()},'v1 prerequisite changed')
    require(transitive==[bodies.identity(ROOT/path,digest) for path,digest in sorted(expected.items())],'underlying source changed')
    return result


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
