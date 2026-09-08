"""Conditional B/D/DBR return projection of the 114 closed scene targets.

Separately numbered extension of the unchanged scroll value projection.
Only the pinned scene decoder, XBA, memory ASL/ROL and TYX are added.
No native execution, global domain proof, memory-alias closure or approval.
"""
from __future__ import annotations
from collections import Counter, deque
import argparse
import ast
import inspect
import json
from pathlib import Path
import sys
import audit_schala_nmi_scroll_inputs_v1 as old
import audit_schala_scene_handler_closure_v1 as scene

ROOT=Path(__file__).resolve().parents[1]
bodies=old.bodies
closure=old.closure
sha=old.sha
serial=old.serial
require=old.require
cpu=old.cpu
exact_byte=old.exact_byte
ROM=old.ROM
ROM_SHA=old.ROM_SHA
PINS={
 'scroll':('tools/audit_schala_nmi_scroll_inputs_v1.py',19678,'4153a240d3a1fa750dd0ac67626776e061ceb049f03b9fce54fc08da8e31c686'),
 'scroll_tests':('tests/test_schala_nmi_scroll_inputs_v1.py',9965,'f4083eb152d606a39511a011e7454384c237f3ece149d786202bd718c328a3c9'),
 'scroll_reference':('references/schala_nmi_scroll_inputs_v1.json',87273,'003bf6be7e686445a8aa0a7bddf36bd8ca35b2fb49aa4d184ec5f3bc15db8013'),
 'scene':('tools/audit_schala_scene_handler_closure_v1.py',24705,'2c8de06dea25a35971143bf6a8c868aea1996a6ab6a8de26fa4b5a12c9ade71d'),
 'scene_tests':('tests/test_schala_scene_handler_closure_v1.py',9821,'89b50ffd56f3fdc9aa528fd14c563281226421d10140c92a7d4483aa727357da'),
 'scene_reference':('references/schala_scene_handler_closure_v1.json',1029264,'ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a'),
}
LIMITS={
 'arbitrary_entry_b_d_dbr_contract':False,'a_low_x_y_or_other_flags_preserved':False,
 'nonstack_alias_closure':False,'dma_effects_proved':False,
 'all_122_cells_or_all_scene_handlers_value_closed':False,
 'complete_legal_command_or_script_domain_proved':False,
 'termination_proved':False,'timing_proved':False,'asynchronous_entry_proved':False,
 'whole_nmi_stack_bound':None,'production_approval':False,'new_native_execution':False,
}


def decode(read,pc,m8,x8):
    """Use the pinned scene opcode/width inventory, not its value semantics."""
    raw=read(pc,1);require(type(raw) is bytes and len(raw)==1,'one opcode byte')
    op=raw[0]
    if op in closure.prior.irq.M_IMMEDIATES:name,n=closure.prior.irq.M_IMMEDIATES[op],2 if m8 else 3
    elif op in closure.prior.irq.X_IMMEDIATES:name,n=closure.prior.irq.X_IMMEDIATES[op],2 if x8 else 3
    elif op in closure.prior.irq.BRANCHES or op==0x80:name,n='branch',2
    else:
        require(op in scene.FIXED,'unsupported decode opcode')
        name,n=scene.FIXED[op]
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


def verify_derivation():
    expected=inspect.getsource(old.decode).replace('closure.FIXED','scene.FIXED').replace(
        'Reuse the unchanged closure opcode/width inventory','Use the pinned scene opcode/width inventory')
    require(ast.dump(ast.parse(expected))==ast.dump(ast.parse(inspect.getsource(decode))),'undeclared decoder change')
    expected=inspect.getsource(old.value_walk)
    expected=expected.replace('elif op==0x54:',
        'elif op==0xEB:lo,hi=hi,lo\n        elif op==0x54:')
    expected=expected.replace("'DEX','DEY','NOP')","'DEX','DEY','NOP','TYX')")
    expected=expected.replace("('INC','DEC','LSR') and name.endswith",
        "('INC','DEC','LSR','ASL','ROL') and name.endswith")
    require(ast.dump(ast.parse(expected))==ast.dump(ast.parse(inspect.getsource(value_walk))),'undeclared value effect change')
    return {'old_value_walk_source_sha256':sha(inspect.getsource(old.value_walk).encode()),
        'new_value_walk_source_sha256':sha(inspect.getsource(value_walk).encode()),
        'decoder_uses_pinned_scene_inventory':True,'only_declared_ast_changes':True,
        'value_changes':['XBA swaps complete A low/high bytes in either M width.',
            'Memory ASL/ROL affect memory and flags, with no architectural A/D/DBR effect.',
            'TYX affects X and flags; X values remain unmodeled and later TXA remains conservative.'],
        'unused_php_plp_phd_pld_tcd_phk_pea_support_added':False,'inherited_sources_mutated':False}


def classify(values,typed):
    """Check source/return agreement, then retain unknown B as unresolved."""
    require(values['entry']==typed['entry'] and values['kind']==typed['kind']=='near','exact target and call kind')
    require(typed['frontier'] is None and typed['status']=='closed-direct-stack-width-control-flow','typed target must be closed')
    require(values['entry_m8'] is True and values['entry_x8'] is False and values['entry_irq_masked'] is True
        and type(values['entry_b']) is int and values['entry_b']==0
        and type(values['entry_d']) is int and values['entry_d']==0
        and type(values['entry_dbr']) is int and values['entry_dbr']==126,'exact value entry contract')
    require(typed['entry_m8'] is True and typed['entry_x8'] is False and typed['entry_irq_masked'] is True,'typed entry width contract')
    for key in ('decoded_byte_intervals','decoded_context_identity_sha256','direct_calls','mnemonic_context_counts'):
        require(values[key]==typed[key],'value/typed source coverage or calls differ: '+key)
    require(values['all_direct_callees_inlined'] is True and values['branch_conditions_overapproximated'] is True
        and values['d_invariant_proved_under_no_alias_no_asynchronous_premises'] is True
        and values['nonstack_memory_and_dma_effects_proved'] is False and values['termination_proved'] is False,'value scope differs')
    require(type(values['ends']) is list and values['ends'],'nonempty exact returned value states')
    states=set();b_values=set();dbr_values=set()
    for row in values['ends']:
        require(row['kind']=='return' and row['m8'] is True and row['x8'] is False and row['irq_masked'] is True,'exact balanced return width')
        require(type(row['counted_stack_bytes']) is int and row['counted_stack_bytes']==0 and row['frames']==[],'return retains a frame or software value')
        exact_byte(row['a_low'],'return A.low',True);exact_byte(row['b'],'return B',True);exact_byte(row['dbr'],'return DBR',True)
        require(type(row['d']) is int and row['d']==0,'return D differs')
        require(type(row['site']) is str and len(row['site'])==7 and row['site'].startswith('$CD'),'root near return bank/site')
        states.add((row['site'],row['m8'],row['x8'],row['irq_masked']));b_values.add(row['b']);dbr_values.add(row['dbr'])
    require([{'site':s,'m8':m,'x8':x,'irq_masked':i} for s,m,x,i in sorted(states)]==typed['return_width_states'],'exact typed return-site contexts differ')
    require(dbr_values=={126},'selected corpus DBR return not proved')
    return {'entry':values['entry'],'b_zero_on_every_projected_return':b_values=={0},
        'd_zero_on_every_projected_return':True,'dbr_7e_on_every_projected_return':True,
        'projected_b_values':sorted(b_values,key=repr),'status':'proved-B0-D0-DBR7E' if b_values=={0} else 'B-return-not-proved',
        'unknown_b_is_not_a_demonstrated_nonzero_runtime_value':True,
        'typed_source_and_return_contexts_match':True,
        'typed_contract_sha256':sha(bodies.canonical(typed)),
        'value_projection_sha256':sha(bodies.canonical(values))}


def audit(rom,scene_report):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(p,n):
        require(type(p) is int and type(n) is int and n>0 and 0xC00000<=p<p+n<=0x1000000,'canonical read bounds')
        return rom[p-0xC00000:p-0xC00000+n]
    typed=[r for r in scene_report['conditional_handler_contracts'] if r['frontier'] is None]
    excluded=[r for r in scene_report['conditional_handler_contracts'] if r['frontier'] is not None]
    require(len(typed)==114 and len(excluded)==7 and scene_report['summary']['closed_cells']==114,'exact closed scene subset')
    results=[];baseline=[];all_values=[]
    for row in typed:
        entry=int(row['entry'][1:],16);old_value=None;last=[]
        def record_read(p,n):
            raw=read(p,n);last[:]=[(p,raw[0])];return raw
        try:old_value=old.value_walk(record_read,entry,'near',entry_b=0,entry_dbr=126)
        except ValueError as exc:
            reason=str(exc)
            require(reason=='unsupported decode opcode' or reason.startswith('unsupported value effect EB at '),'unexpected historical baseline failure')
            site,opcode=last[0]
            baseline.append({'entry':row['entry'],'status':'unsupported-by-preserved-scroll-model',
                'first_frontier':cpu(site),'opcode':f'${opcode:02X}','reason':reason,
                'source_instruction_prefix_sha256':sha(read(site,1))})
        else:
            baseline.append({'entry':row['entry'],'status':'traversed-by-preserved-scroll-model',
                'projection_sha256':sha(bodies.canonical(old_value))})
        values=value_walk(read,entry,'near',entry_b=0,entry_dbr=126)
        result=classify(values,row)
        if old_value is not None:
            require(values==old_value and result['status']=='proved-B0-D0-DBR7E','preserved 65 successful projections changed')
        link=next(x for x in scene_report['cell_to_contract_relation'] if x['entry']==row['entry'])
        result['commands_at_b_zero']=link['commands'];results.append(result);all_values.append(values)
    unsupported=[x for x in baseline if x['status']=='unsupported-by-preserved-scroll-model']
    missing=[x for x in results if x['status']!='proved-B0-D0-DBR7E']
    require(len(unsupported)==49 and len(missing)==3 and [x['entry'] for x in missing]==['$CD1805','$CD19B1','$CD2460'],'reviewed value counts/boundaries differ')
    require(dict(Counter(x['opcode'] for x in unsupported))=={'$B7':23,'$EB':10,'$67':5,'$ED':5,'$77':6},'historical first-frontier census differs')
    return {'schema':'project-epoch-scene-handler-return-values-v1','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},
        'scope':'114 control-flow-closed scene targets only; native near M1/X0/I1 with B0/D0/DBR7E',
        'derivation':verify_derivation(),'preserved_scroll_baseline':baseline,
        'conditional_return_contracts':results,'value_projections':all_values,
        'excluded_control_flow_open_targets':[{'entry':r['entry'],'frontier':r['frontier'],'return_values_proved':False} for r in excluded],
        'summary':{'selected_closed_targets':114,'selected_closed_cells':114,
            'preserved_model_successes':65,'preserved_model_unsupported':49,
            'new_model_traversed_targets':114,'all_returns_b0_d0_dbr7e_targets':111,
            'b_return_unresolved_targets':3,'d0_dbr7e_targets':114,
            'excluded_open_targets':7,'excluded_open_cells':8,
            'unresolved_b_entries':[x['entry'] for x in missing]},
        'premises':['Native near entry with B=0, D=0, DBR=7E and M1/X0/I1, exact two-byte return frame.',
            'Ordinary writable stack; no nonstack CPU/DMA alias overwrites saved data, frames or pinned code.',
            'No asynchronous handler or other external change to architectural registers.',
            'Memory loads and active-width arithmetic are conservative unknown values; every conditional branch takes both edges.',
            'The proved result applies only to the 111 identified targets under these inputs; it is not a general command-loop invariant.'],
        **LIMITS}


def collect():
    pins={key:bodies.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    owned=[Path(__file__).resolve(),ROOT/'tests/test_schala_scene_handler_values_v1.py']
    own=[bodies.identity(p) for p in owned]
    require(Path(old.__file__).resolve()==ROOT/PINS['scroll'][0]
        and Path(scene.__file__).resolve()==ROOT/PINS['scene'][0],'exact dependency import paths')
    scroll=old.collect();census=scene.collect()
    for key,value in (('scroll_reference',scroll),('scene_reference',census)):
        path,size,digest=PINS[key]
        require(serial(value)==bodies.read_file(ROOT/path,digest,size),'accepted prerequisite no longer reproduces: '+key)
    inherited=scroll['reused_underlying_source_identities']+list(scroll['prerequisites'].values())
    inherited+=list(census['source_identities'].values())+list(census['reused_scene_sources'].values())+census['reused_closure_sources']
    expected={}
    for item in inherited:
        require(item['path'] not in expected or expected[item['path']]==item['sha256'],'inconsistent inherited source')
        expected[item['path']]=item['sha256']
    transitive=[bodies.identity(ROOT/path,digest) for path,digest in sorted(expected.items())]
    report=audit(bodies.read_file(ROM,ROM_SHA,0x400000),census)
    report.update(prerequisites=pins,source_identities=own,reused_underlying_source_identities=transitive,
        primary_cpu_sources=census['primary_semantics']['sources'],
        reproduce=['python','-B','tools/audit_schala_scene_handler_values_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    require(own==[bodies.identity(p) for p in owned],'own source changed')
    require(pins=={key:bodies.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()},'prerequisite source changed')
    require(transitive==[bodies.identity(ROOT/path,digest) for path,digest in sorted(expected.items())],'underlying source changed')
    return report


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
