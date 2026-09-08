"""Conditional scene-command handler stack/width closure, with explicit frontiers.

This separately versioned walker copies the pinned closure-v2 implementation.
Only ten documented width/stack-neutral opcodes, an explicit indirect-JMP
frontier and two syntactic memory-write mnemonics are added. Old proofs remain
unchanged. Register values, aliases, legal domains and whole-NMI bounds are open.
"""
from __future__ import annotations
from collections import Counter, deque
import argparse
import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
import audit_schala_package_normal_nmi_closure_v2 as base
import audit_schala_scene_dispatch_inputs_v1 as inputs
import audit_schala_nmi_mode_bodies_v1 as io

ROOT=Path(__file__).resolve().parents[1]
ROM=ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
prior=base.prior
ROOT_RETURN=base.ROOT_RETURN
EXTENSIONS={0xB7:('LDA [dp],Y',2),0x67:('ADC [dp]',2),
    0xED:('SBC abs',3),0x77:('ADC [dp],Y',2),0xC4:('CPY dp',2),
    0x06:('ASL dp',2),0x6F:('ADC long',4),0x26:('ROL dp',2),
    0x2E:('ROL abs',3),0xBB:('TYX',1)}
FIXED={**base.FIXED,**EXTENSIONS,0x6C:('JMP (abs)',3)}
PINS={
 'closure':('tools/audit_schala_package_normal_nmi_closure_v2.py',19110,'c346e0db11dc35a4ecd4e756dcc951ca7a760d3bd52849da55b1f7fe7e7b7e13'),
 'closure_reference':('references/schala_package_normal_nmi_closure_v2.json',321839,'413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242'),
 'scene_inputs':('tools/audit_schala_scene_dispatch_inputs_v1.py',14561,'3aef357ad9c557d21015711e834d37a370737228665cca4c2ece4745a71f4d30'),
 'scene_reference':('references/schala_scene_dispatch_inputs_v1.json',156163,'d5604c65934dff1dfa4796ea3d990e227065e9b28a5499695f590fff912a8c13'),
 'io_library':('tools/audit_schala_nmi_mode_bodies_v1.py',13937,'9b685d63e68153d1c7d56213af5b1211237c3f36d067046a9e854ae5beb34187'),
}
LIMITS={'callee_register_value_preservation':False,'hidden_b_return_values_proved':False,
 'd_dbr_return_values_proved':False,'nonstack_alias_closure':False,
 'dma_effects_proved':False,'legal_command_domain_proved':False,
 'legal_script_domain_proved':False,'termination_proved':False,
 'timing_bound':None,'whole_nmi_stack_bound':None,'production_approval':False,
 'new_native_execution':False,'all_scene_handlers_closed':False}

def require(value,message):
    if not value:raise ValueError(message)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def serial(value):return (json.dumps(value,indent=2)+'\n').encode('utf-8')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')

class FrontierError(ValueError):
    def __init__(self,category,pc,message):
        super().__init__(message);self.category=category;self.pc=pc


def walk_direct(read,entry,kind,*,entry_m8=True,entry_x8=False,budget=30000):
    if kind not in ("near","long"):raise ValueError("only exact direct call kinds supported")
    n=2 if kind=="near" else 3
    State=prior.irq.State
    queue=deque([State(entry,entry_m8,entry_x8,True,(ROOT_RETURN,)*n,((ROOT_RETURN,kind),))])
    seen=set();decoded={};byte_owner={};calls=set();edges=set();exits=set();peak=n;peaks=set();failure=None
    def fail(category,pc,message):raise FrontierError(category,pc,message)
    try:
        while queue:
            state=queue.popleft()
            if state in seen:continue
            seen.add(state)
            if len(seen)>budget:fail("state-budget",state.pc,"bounded abstract state budget exceeded")
            pc=state.pc
            if not 0xC00000<=pc<0x1000000:fail("noncanonical-control-flow",pc,"control flow left pinned canonical high ROM")
            opcode=read(pc,1)[0]
            if opcode in prior.irq.M_IMMEDIATES:name,length=prior.irq.M_IMMEDIATES[opcode],2 if state.m8 else 3
            elif opcode in prior.irq.X_IMMEDIATES:name,length=prior.irq.X_IMMEDIATES[opcode],2 if state.x8 else 3
            elif opcode in prior.irq.BRANCHES or opcode==0x80:name,length="branch",2
            elif opcode in FIXED:name,length=FIXED[opcode]
            else:fail("unsupported-opcode",pc,f"unsupported opcode {opcode:02X}")
            if (pc&0xFFFF)+length>0x10000:fail("instruction-bank-boundary",pc,"instruction crosses its physical program bank")
            raw=read(pc,length)
            if len(raw)!=length:fail("short-read",pc,"short canonical instruction read")
            if any(other_pc==pc and value[1]!=length for (other_pc,_,_),value in decoded.items()):
                fail("overlapping-decode",pc,"same instruction start has incompatible width-dependent lengths")
            for address in range(pc,pc+length):
                if address in byte_owner and byte_owner[address]!=pc:fail("overlapping-decode",pc,"control flow or width state overlaps another instruction")
                byte_owner[address]=pc
            decoded[(pc,state.m8,state.x8)]=(name,length,hashlib.sha256(raw).hexdigest())
            m8,x8,masked=state.m8,state.x8,state.irq_masked
            stack=list(state.stack);frames=list(state.calls)
            next_pc=(pc&0xFF0000)|((pc+length)&0xFFFF);destinations=[next_pc]
            def pop(count,expected=None):
                if len(stack)<count:fail("stack-underflow",pc,"pop exceeds declared frame")
                if expected is None and any(type(item) is int for item in stack[-count:]):fail("return-frame-consumed",pc,"software pop consumes a call return frame")
                if expected is not None and stack[-count:]!=[expected]*count:fail("return-frame-mismatch",pc,"return lacks its exact typed call frame")
                del stack[-count:]
            if opcode in (0xC2,0xE2):
                value=opcode==0xE2
                if raw[1]&0x20:m8=value
                if raw[1]&0x10:x8=value
                if raw[1]&4:masked=value
            elif opcode==0x08:stack.append((m8,x8,masked))
            elif opcode==0x28:
                if not stack or not isinstance(stack[-1],tuple):fail("unknown-status-value",pc,"PLP lacks a typed PHP value")
                m8,x8,masked=stack[-1];pop(1)
            elif opcode in (0x48,0xDA,0x5A,0x8B,0x0B,0x4B,0xF4):
                width=(1 if m8 else 2) if opcode==0x48 else ((1 if x8 else 2) if opcode in (0xDA,0x5A) else (2 if opcode in (0x0B,0xF4) else 1))
                stack.extend([None]*width)
            elif opcode in (0x68,0xFA,0x7A,0xAB,0x2B):
                width=(1 if m8 else 2) if opcode==0x68 else ((1 if x8 else 2) if opcode in (0xFA,0x7A) else (2 if opcode==0x2B else 1))
                pop(width)
            elif opcode in (0x20,0x22):
                target=int.from_bytes(raw[1:],"little")|(0 if opcode==0x22 else pc&0xFF0000)
                call_kind="long" if opcode==0x22 else "near";frame=3 if opcode==0x22 else 2
                stack.extend([next_pc]*frame);frames.append((next_pc,call_kind));calls.add((pc,target,call_kind));destinations=[target]
            elif opcode==0xFC:fail("indexed-call-dispatch",pc,"indexed JSR requires bounded target and index provenance")
            elif opcode==0x6C:fail("indirect-jump-dispatch",pc,"indirect JMP requires pointer-value and target provenance")
            elif opcode==0x7C:fail("indexed-jump-dispatch",pc,"indexed JMP requires bounded target and index provenance")
            elif opcode in (0x60,0x6B):
                expected_kind="near" if opcode==0x60 else "long"
                if not frames or frames[-1][1]!=expected_kind:fail("return-kind-mismatch",pc,"RTS/RTL does not match its call frame")
                target,_=frames.pop();pop(2 if opcode==0x60 else 3,target)
                if target==ROOT_RETURN:
                    if stack or frames:fail("unbalanced-root-return",pc,"root return leaves local state")
                    if opcode==0x60 and pc&0xFF0000!=entry&0xFF0000:
                        fail("near-return-bank-mismatch",pc,"root RTS cannot restore a bank changed by a far tail jump")
                    exits.add((pc,m8,x8,masked));continue
                if opcode==0x60 and pc&0xFF0000!=target&0xFF0000:fail("near-return-bank-mismatch",pc,"RTS cannot restore a bank changed by a far tail jump")
                destinations=[target]
            elif opcode==0x40:fail("unexpected-rti",pc,"callee attempts an interrupt return")
            elif opcode==0x4C:destinations=[pc&0xFF0000|int.from_bytes(raw[1:],"little")]
            elif opcode==0x5C:destinations=[int.from_bytes(raw[1:],"little")]
            elif opcode in prior.irq.BRANCHES or opcode in (0x80,0x82):
                target=(pc&0xFF0000)|((next_pc+int.from_bytes(raw[1:],"little",signed=True))&0xFFFF)
                destinations=[target] if opcode in (0x80,0x82) else [next_pc,target]
            elif opcode==0x78:masked=True
            elif opcode==0x58:masked=False
            elif opcode==0xFB:fail("processor-mode-transition",pc,"XCE requires carry/emulation-state and changed stack semantics")
            elif opcode in (0x1B,0x9A):fail("stack-pointer-assignment",pc,"SP assignment requires register-value and ownership analysis")
            if not masked:fail("irq-unmasking",pc,"callee permits asynchronous IRQ before return")
            if len(stack)>512 or len(frames)>64:fail("stack-budget",pc,"bounded stack/call budget exceeded")
            if len(stack)>peak:peak=len(stack);peaks={pc}
            elif len(stack)==peak and len(stack)>len(state.stack):peaks.add(pc)
            edges.update((pc,target) for target in destinations)
            queue.extend(State(target,m8,x8,masked,tuple(stack),tuple(frames)) for target in destinations)
        if not exits:fail("no-balanced-return",entry,"no reachable balanced root return")
    except FrontierError as exc:
        failure={"category":exc.category,"site":f"${exc.pc:06X}","reason":str(exc),
            "incoming_width_state":{"m8":state.m8,"x8":state.x8,"irq_masked":state.irq_masked},
            "counted_stack_bytes_at_frontier":len(state.stack),
            "active_call_return_sites":[{"return":f"${ret:06X}" if ret!=ROOT_RETURN else "abstract-caller","kind":k} for ret,k in state.calls]}
    covered=sorted(byte_owner);intervals=[]
    for address in covered:
        if intervals and intervals[-1][1]==address:intervals[-1][1]+=1
        else:intervals.append([address,address+1])
    identity=[{"start":f"${a:06X}","end_exclusive":f"${b:06X}","sha256":hashlib.sha256(read(a,b-a)).hexdigest()} for a,b in intervals]
    writes=[];far_jumps=[]
    for (pc,m8,x8),(name,length,sha) in sorted(decoded.items()):
        raw=read(pc,length)
        if name=="JML":far_jumps.append({"site":f"${pc:06X}","target":f"${int.from_bytes(raw[1:],'little'):06X}","instruction_sha256":sha})
        if length>1 and name.split()[0] in {"STA","STX","STY","STZ","INC","DEC","TSB","TRB","LSR","ASL","ROL","MVN"}:
            width=(1 if x8 else 2) if name.startswith(("STX","STY")) else (1 if m8 else 2)
            writes.append({"site":f"${pc:06X}","mnemonic":name,"encoded_operand":f"${int.from_bytes(raw[1:],'little'):X}",
                "width_bytes":None if name=="MVN" else width,"instruction_sha256":sha,"effective_address_and_aliasing_proved":False})
    return {"entry":f"${entry:06X}","kind":kind,"entry_m8":entry_m8,"entry_x8":entry_x8,"entry_irq_masked":True,
        "status":"closed-direct-stack-width-control-flow" if failure is None else "open-frontier",
        "frontier":failure,"abstract_states":len(seen),"instruction_contexts":len(decoded),"instruction_starts":len({k[0] for k in decoded}),
        "decoded_byte_intervals":identity,"decoded_context_identity_sha256":hashlib.sha256(json.dumps(sorted((k,value) for k,value in decoded.items()),separators=(",",":")).encode()).hexdigest(),
        "maximum_additional_bytes_below_callee_entry":peak-n if failure is None else None,
        "exploratory_observed_local_peak_not_a_bound":peak-n if failure else None,
        "maximum_counted_bytes_including_root_call_frame":peak if failure is None else None,
        "peak_instruction_sites":[f"${p:06X}" for p in sorted(peaks)] if failure is None else [],
        "return_width_states":[{"site":f"${pc:06X}","m8":m,"x8":x,"irq_masked":i} for pc,m,x,i in sorted(exits)],
        "matches_prior_return_width_premise":bool(exits) and failure is None and all(m and not x and i for _,m,x,i in exits),
        "direct_calls":[{"site":f"${pc:06X}","target":f"${target:06X}","kind":k} for pc,target,k in sorted(calls)],
        "direct_far_jumps":far_jumps,"syntactic_write_operands":writes,
        "mnemonic_context_counts":dict(sorted(Counter(value[0] for value in decoded.values()).items())),
        "callee_register_value_preservation":False,"nonstack_alias_closure":False,
        "premise_nonstack_writes_do_not_modify_stack_or_saved_status":True,
        "termination_proved":False,"whole_nmi_bound":None}


def verify_walker_derivation():
    """Reject an undocumented change to the pinned prior control-flow engine."""
    expected=inspect.getsource(base.walk_direct)
    expected=expected.replace('elif opcode==0x7C:fail(',
        'elif opcode==0x6C:fail("indirect-jump-dispatch",pc,"indirect JMP requires pointer-value and target provenance")\n            elif opcode==0x7C:fail(')
    expected=expected.replace('"TSB","TRB","LSR","MVN"}',
        '"TSB","TRB","LSR","ASL","ROL","MVN"}')
    require(ast.dump(ast.parse(expected))==ast.dump(ast.parse(inspect.getsource(walk_direct))),
        'walker differs beyond declared indirect frontier and write inventory')
    require(not set(EXTENSIONS)&set(base.FIXED) and 0x6C not in base.FIXED,
        'extension overwrites a prior decoded opcode')
    return {'prior_walker_source_sha256':sha(inspect.getsource(base.walk_direct).encode()),
        'new_walker_source_sha256':sha(inspect.getsource(walk_direct).encode()),
        'only_declared_ast_changes':True,'prior_module_mutated':False}


def project(cells,contracts,old_contracts):
    """Join exact source cells to conditional contracts without domain promotion."""
    require(type(cells) is list and len(cells)==122,'exact reviewed physical cell prefix')
    require([x['command'] for x in cells]==list(range(0x80,0xFA)),'cell command order')
    for cell in cells:
        require(type(cell['command']) is int and cell['hidden_b']==0 and type(cell['hidden_b']) is int,
            'exact cell byte and B')
        expected=inputs.index_contract(cell['command'],0)
        require(type(cell['x']) is int and type(cell['pointer_byte_addresses']) is list and
            len(cell['pointer_byte_addresses'])==2 and all(type(x) is int for x in cell['pointer_byte_addresses']),
            'exact pointer address and index integers')
        require(all(cell[k]==v for k,v in expected.items()),'cell recipe differs')
        require(cell['in_reviewed_122_cell_prefix'] is True and cell['command_reachability_proved'] is False,
            'cell scope differs')
        require(type(cell['target']) is str and len(cell['target'])==6 and cell['target'].startswith('CD'),
            'same-bank scene target')
    targets=sorted({int(x['target'],16) for x in cells})
    require(len(targets)==121,'reviewed target deduplication')
    expected_entries=[f'${x:06X}' for x in targets]
    require([x['entry'] for x in contracts]==expected_entries and
        [x['entry'] for x in old_contracts]==expected_entries,'complete unique contract order')
    linked=[];closed=[];open_rows=[];old_closed=0
    for row,old in zip(contracts,old_contracts):
        require(row['kind']=='near' and row['entry_m8'] is True and row['entry_x8'] is False
            and row['entry_irq_masked'] is True,'exact near M1/X0/I1 entry')
        require(row['callee_register_value_preservation'] is False and row['nonstack_alias_closure'] is False
            and row['premise_nonstack_writes_do_not_modify_stack_or_saved_status'] is True
            and row['termination_proved'] is False and row['whole_nmi_bound'] is None,'contract scope differs')
        commands=[x['command'] for x in cells if '$'+x['target']==row['entry']]
        if row['frontier'] is None:
            require(row['status']=='closed-direct-stack-width-control-flow' and row['return_width_states']
                and row['matches_prior_return_width_premise'] is True,'closed state differs')
            require(all(x['m8'] is True and x['x8'] is False and x['irq_masked'] is True
                for x in row['return_width_states']),'return widths differ')
            depth=row['maximum_additional_bytes_below_callee_entry']
            require(type(depth) is int and 0<=depth<=512 and
                type(row['maximum_counted_bytes_including_root_call_frame']) is int and
                row['maximum_counted_bytes_including_root_call_frame']==depth+2,
                'closed stack arithmetic differs')
            require(row['exploratory_observed_local_peak_not_a_bound'] is None,'closed exploratory peak')
            closed.append(row)
        else:
            require(row['status']=='open-frontier' and row['maximum_additional_bytes_below_callee_entry'] is None
                and row['maximum_counted_bytes_including_root_call_frame'] is None,'open frontier acquired a bound')
            open_rows.append({'entry':row['entry'],'commands':commands,'frontier':row['frontier'],
                'exploratory_observed_local_peak_not_a_bound':row['exploratory_observed_local_peak_not_a_bound'],
                'full_bound':None})
        if old['frontier'] is None:
            old_closed+=1
            # ASL/ROL operands are the declared metadata-only difference.
            stripped={**row,'syntactic_write_operands':[x for x in row['syntactic_write_operands']
                if x['mnemonic'].split()[0] not in {'ASL','ROL'}]}
            require(stripped==old,'previously closed handler changed')
        linked.append({'entry':row['entry'],'commands':commands,'status':row['status'],
            'prior_status':old['status'],'contract_sha256':sha(canonical(row))})
    return {'cell_to_contract_relation':linked,'summary':{
        'reviewed_physical_cells':len(cells),'distinct_targets':len(targets),
        'prior_closed_targets':old_closed,'closed_targets':len(closed),'open_targets':len(open_rows),
        'closed_cells':sum(len(x['commands']) for x in linked if x['status']=='closed-direct-stack-width-control-flow'),
        'closed_return_widths_all_m1_x0_i1':True,
        'largest_closed_handler_additional_bytes':max(x['maximum_additional_bytes_below_callee_entry'] for x in closed),
        'largest_closed_handler_including_near_frame':max(x['maximum_counted_bytes_including_root_call_frame'] for x in closed),
        'closed_subset_maximum_is_not_a_dispatcher_or_nmi_bound':True},'open_frontiers':open_rows,**LIMITS}


def source_semantics():
    """Pin primary source recipes; semantic interpretation is reviewer encoded."""
    sources=[];contents=[]
    for relative,pin,upstream in base.PRIMARY_SOURCES:
        path=ROOT/relative;raw=io.read_file(path,pin)
        contents.append(raw)
        sources.append({'path':relative,'size':len(raw),'sha256':pin,
            'url':'https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/'+upstream})
    shared=contents[0].decode('utf-8')
    recipes={0xB7:('AddrMode_DirIndLngIdxY','LDA'),0x67:('AddrMode_DirIndLng','ADC'),
        0xED:('AddrMode_Abs','SBC'),0x77:('AddrMode_DirIndLngIdxY','ADC'),
        0xC4:('AddrMode_Dir','CPY'),0x06:('AddrMode_Dir','ASL'),
        0x6F:('AddrMode_AbsLng','ADC'),0x26:('AddrMode_Dir','ROL'),
        0x2E:('AddrMode_Abs','ROL'),0xBB:('AddrMode_Imp','TYX')}
    rows=[]
    for opcode,(addressing,operation) in sorted(recipes.items()):
        marker=f'case 0x{opcode:02X}: {addressing}(); {operation}(); break;'
        require(shared.count(marker)==1,'primary opcode recipe differs')
        line=shared[:shared.index(marker)].count('\n')+1
        name,length=EXTENSIONS[opcode]
        rows.append({'opcode':f'${opcode:02X}','mnemonic':name,'instruction_bytes':length,
            'primary_dispatch_line':line,'addressing_method':addressing,'operation_method':operation,
            'changes_m_x_i_or_sp':False,'semantic_interpretation':'reviewer-encoded from pinned primary source',
            'memory_write_width':'M-dependent' if operation in {'ASL','ROL'} else None,
            'operand_memory_effects_and_aliases_proved':False})
    return {'sources':sources,'extension_recipes':rows,
        'indirect_jmp_6c_remains_frontier':True,'all_other_unsupported_opcodes_remain_frontiers':True}


def audit(rom,scene_reference):
    require(type(rom) is bytes and len(rom)==0x400000 and sha(rom)==ROM_SHA,'canonical ROM identity')
    def read(address,length):
        require(type(address) is int and type(length) is int and length>0 and
            0xC00000<=address<address+length<=0x1000000,'canonical read bounds')
        return rom[address-0xC00000:address-0xC00000+length]
    cells=scene_reference['b_zero_syntax_cells'][:122]
    for cell in cells:
        actual=b''.join(read(a,1) for a in cell['pointer_byte_addresses'])
        require(sha(actual)==cell['pointer_bytes_sha256'] and
            f'{0xCD0000|int.from_bytes(actual,"little"):06X}'==cell['target'],'canonical pointer identity')
    targets=sorted({int(x['target'],16) for x in cells})
    old=[base.walk_direct(read,t,'near') for t in targets]
    rows=[walk_direct(read,t,'near') for t in targets]
    report=project(cells,rows,old)
    require(report['summary']=={'reviewed_physical_cells':122,'distinct_targets':121,
        'prior_closed_targets':67,'closed_targets':114,'open_targets':7,'closed_cells':114,
        'closed_return_widths_all_m1_x0_i1':True,'largest_closed_handler_additional_bytes':16,
        'largest_closed_handler_including_near_frame':18,
        'closed_subset_maximum_is_not_a_dispatcher_or_nmi_bound':True},'reviewed census totals differ')
    return {'schema':'project-epoch-scene-handler-conditional-closure-v1','date':'2026-09-08',
        'evidence_level':'verified-static','canonical_rom':{'size':len(rom),'sha256':ROM_SHA},
        'scope':'122 reviewed B0 scene pointer cells, 121 distinct near M1/X0/I1 handler targets',
        'premises':['Native near entry with an exact two-byte typed return frame and M1/X0/I1.',
            'Ordinary writable stack; no memory alias or asynchronous/DMA effect alters saved stack/status/control-flow inputs.',
            'Conditional branches are overapproximated; finite traversal is not termination or timing proof.',
            'Input command and hidden B select the reviewed cells only conditionally; handler-return B/D/DBR and legal domains remain open.'],
        'walker_derivation':verify_walker_derivation(),'primary_semantics':source_semantics(),
        'conditional_handler_contracts':rows,'preserved_v2_handler_contracts_sha256':sha(canonical(old)),**report}


def collect():
    before={key:io.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
    own={'auditor':io.identity(Path(__file__).resolve()),
        'tests':io.identity(ROOT/'tests/test_schala_scene_handler_closure_v1.py')}
    require(Path(base.__file__).resolve()==ROOT/PINS['closure'][0] and
        Path(inputs.__file__).resolve()==ROOT/PINS['scene_inputs'][0] and
        Path(io.__file__).resolve()==ROOT/PINS['io_library'][0],'import source paths differ')
    rom=io.read_file(ROM,ROM_SHA,0x400000)
    prior_report=base.audit(rom)
    require(serial(prior_report)==io.read_file(ROOT/PINS['closure_reference'][0],PINS['closure_reference'][2]),
        'preserved closure reference does not reproduce')
    scene=inputs.collect()
    require(serial(scene)==io.read_file(ROOT/PINS['scene_reference'][0],PINS['scene_reference'][2]),
        'preserved scene inputs do not reproduce')
    report=audit(rom,scene)
    for item in report['primary_semantics']['sources']:
        io.read_file(ROOT/item['path'],item['sha256'],item['size'])
    require(before=={key:io.identity(ROOT/path,digest,size) for key,(path,size,digest) in PINS.items()}
        and own=={'auditor':io.identity(Path(__file__).resolve()),
            'tests':io.identity(ROOT/'tests/test_schala_scene_handler_closure_v1.py')},'source drift')
    report.update(source_identities=before,**own,reused_scene_sources=scene['sources'],
        reused_closure_sources=prior_report['source_identities'],
        reproduce=['python','-B','tools/audit_schala_scene_handler_closure_v1.py'],
        serialization='UTF-8 indented JSON, LF, one trailing newline')
    return report


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
