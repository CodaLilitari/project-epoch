#!/usr/bin/env python3
"""Bounded direct-callee stack/width closure of the preserved NMI v1 frontiers.

This is a fail-closed abstract control-flow walker, not register-value, alias,
termination, timing, or whole-NMI proof. Canonical game bytes never leave memory.
"""
from __future__ import annotations
from collections import Counter,deque
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_package_normal_nmi_v1 as prior

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="project-epoch-package-normal-nmi-direct-closure-v2"
PRIOR_REFERENCE_SHA256="27dd6f602781b83107bd7ab9072f1704e26bb39433713a3188679114db3b4f2c"
FIXED=dict(prior.FIXED)
# Generic documented instructions with no direct SP/width/I effect, or explicit
# stack/control semantics below. Any other opcode remains a hard frontier.
FIXED.update({0x4B:("PHK",1),0x5C:("JML",4),0xF4:("PEA",3),0x78:("SEI",1),0x58:("CLI",1),
    0xE5:("SBC dp",2),0x99:("STA abs,Y",3),0x2C:("BIT abs",3),0x0D:("ORA abs",3),
    0xEA:("NOP",1),0xC5:("CMP dp",2),0x7C:("JMP (abs,X)",3),
    0x0F:("ORA long",4),0x45:("EOR dp",2),0x05:("ORA dp",2),0xD9:("CMP abs,Y",3),
    0x25:("AND dp",2),0x79:("ADC abs,Y",3),0xF9:("SBC abs,Y",3),0x9F:("STA long,X",4),
    0xFB:("XCE",1),0x1B:("TCS",1),0x9A:("TXS",1),0x87:("STA [dp]",2),0xE4:("CPX dp",2)})
ROOT_RETURN=0x1000000  # abstract identity, never fetched as an emulated address
PRIMARY_SOURCES=(
    ("private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h","dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f","Core/SNES/SnesCpu.Shared.h"),
    ("private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h","9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd","Core/SNES/SnesCpu.Instructions.h"),
)


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
        if length>1 and name.split()[0] in {"STA","STX","STY","STZ","INC","DEC","TSB","TRB","LSR","MVN"}:
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


def reset_transition(read,*,reset_entry=0xC0FF00,boot_entry=0xFDC000):
    """Decode the explicit reset-to-fixed-SP prefix, separately from call closure."""
    reset=read(reset_entry,7);boot=read(boot_entry,8)
    if len(reset)!=7 or list(reset[:4])!=[0x78,0x18,0xFB,0x5C] or int.from_bytes(reset[4:],"little")!=boot_entry:
        raise ValueError("reset mode/long-jump prefix differs")
    if len(boot)!=8 or list(boot[:5])!=[0xC2,0x10,0xE2,0x20,0xA2] or boot[7]!=0x9A:
        raise ValueError("boot width/LDX/TXS prefix differs")
    value=int.from_bytes(boot[5:7],"little")
    if value!=0x06FF:raise ValueError("reviewed reset SP constant differs")
    return {"reset_entry":f"${reset_entry:06X}","reset_prefix_sha256":hashlib.sha256(reset).hexdigest(),
        "boot_entry":f"${boot_entry:06X}","boot_prefix_sha256":hashlib.sha256(boot).hexdigest(),
        "reset_clears_carry_before_xce":True,"boot_sets_x16_and_a8":True,
        "fixed_sp_assignment_site":f"${boot_entry+7:06X}","assigned_sp":value,
        "interpretation":"explicit reset transition replaces S with $06FF; not a balanced subroutine-return contract",
        "reset_gate_predicates_discharged":False,"reset_executed":False}


def audit(rom):
    if type(rom) is not bytes or len(rom)!=0x400000 or hashlib.sha256(rom).hexdigest()!=prior.irq.ROM_SHA256:raise ValueError("exact pinned canonical headerless US Rev0 required")
    reference_data=(ROOT/"references/schala_package_normal_nmi_v1.json").read_bytes()
    if hashlib.sha256(reference_data).hexdigest()!=PRIOR_REFERENCE_SHA256:raise ValueError("preserved v1 reference identity differs")
    previous_reference=json.loads(reference_data)
    for source in previous_reference["source_identities"]:
        if hashlib.sha256((ROOT/source["path"]).read_bytes()).hexdigest()!=source["sha256"]:
            raise ValueError("preserved v1 source identity differs")
    def read(pc,n):
        if not 0xC00000<=pc<pc+n<=0x1000000:raise ValueError("canonical high ROM read bounds")
        return rom[pc-0xC00000:pc-0xC00000+n]
    previous=prior.audit(rom)
    if previous!=previous_reference:raise ValueError("preserved v1 audit no longer reproduces its accepted reference")
    calls=[c for region in previous["conditional_regions"] for c in region["calls"]]
    keys=sorted({(int(c["target_or_table"][1:],16),c["kind"],c["entry_m8"],c["entry_x8"]) for c in calls if c["kind"]!="indexed-near"})
    results=[walk_direct(read,target,kind,entry_m8=m8,entry_x8=x8) for target,kind,m8,x8 in keys]
    by_key={(row["entry"],row["kind"],row["entry_m8"],row["entry_x8"]):row for row in results}
    sites=[]
    for call in calls:
        row={"site":call["site"],"target_or_table":call["target_or_table"],"kind":call["kind"],
            "prior_instruction_sha256":call["instruction_sha256"],
            "prior_conditional_depth_at_callee_entry":call["conditional_depth_at_callee_entry"],
            "whole_region_or_nmi_bound":None}
        if call["kind"]=="indexed-near":
            row.update(status="open-indexed-dispatch",callee_additional_stack_bound=None,conditional_peak_from_prior_entry_premise=None)
        else:
            contract=by_key[(call["target_or_table"],call["kind"],call["entry_m8"],call["entry_x8"])]
            depth=contract["maximum_additional_bytes_below_callee_entry"]
            row.update(status=contract["status"],callee_additional_stack_bound=depth,
                conditional_peak_from_prior_entry_premise=None if depth is None else call["conditional_depth_at_callee_entry"]+depth,
                matches_prior_return_width_premise=contract["matches_prior_return_width_premise"])
        sites.append(row)
    if len(calls)!=44 or len(results)!=32 or {int(c["site"][1:],16) for c in calls}!=set(prior.CALLS):
        raise ValueError("preserved exact v1 frontier inventory differs")
    primary=[]
    for path,expected,upstream in PRIMARY_SOURCES:
        content=(ROOT/path).read_bytes()
        if hashlib.sha256(content).hexdigest()!=expected:raise ValueError("pinned primary instruction source differs")
        primary.append({"path":path,"sha256":expected,"size_bytes":len(content),
            "url":"https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/"+upstream})
    table=read(0xCD06BC,8)
    history_root=ROOT/"private/test_runs/normal_nmi_closure_v2_20260908_explore1"
    history_data=(history_root/"receipt.json").read_bytes()
    if hashlib.sha256(history_data).hexdigest()!="1fc09d63c07462b7ef0af3d7f95b2ea601704de6528fc3456814d2535c82c3b0":
        raise ValueError("preserved exploratory receipt differs")
    history=json.loads(history_data);history_ids=[]
    for filename,key in (("auditor.py","source_sha256"),("metadata.json","metadata_sha256"),("receipt.json",None)):
        path=history_root/filename;content=path.read_bytes();sha=hashlib.sha256(content).hexdigest()
        if key is not None and sha!=history[key]:raise ValueError("preserved exploratory artifact differs")
        history_ids.append({"path":path.relative_to(ROOT).as_posix(),"size_bytes":len(content),"sha256":sha})
    return {"schema":SCHEMA,"evidence_level":"verified-static","canonical_rom_sha256":prior.irq.ROM_SHA256,
        "original_frontier_count":len(calls),"direct_callee_contracts":results,
        "original_site_reconciliation":sites,
        "summary":{"closed_distinct_direct_callees":sum(r["frontier"] is None for r in results),
            "open_distinct_direct_callees":sum(r["frontier"] is not None for r in results),
            "closed_original_direct_call_sites":sum(s["status"]=="closed-direct-stack-width-control-flow" for s in sites),
            "open_original_call_sites":sum(s["status"]!="closed-direct-stack-width-control-flow" for s in sites)},
        "indexed_frontiers":[c for c in calls if c["kind"]=="indexed-near"],
        "scroll_hdma_four_reviewed_table_cells":{"span":["$CD06BC","$CD06C4"],"sha256":hashlib.sha256(table).hexdigest(),
            "cells":[{"index":i,"target":f"$CD{int.from_bytes(table[i*2:i*2+2],'little'):04X}"} for i in range(4)],
            "all_possible_indices_or_table_extent_proved":False,"required_data_contracts":["encoded $CA92 producer range","incoming hidden accumulator B at 8-bit ASL/TAX","actual table extent and selected-callee contract"]},
        "explicit_reset_transition":reset_transition(read),"primary_instruction_sources":primary,
        "preserved_exploratory_history":{"status":"not accepted; first decoder-coverage inventory before near-return bank and width-overlap hardening",
            "artifact_identities":history_ids},
        "source_identities":[{"path":p.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in
            (Path(__file__),ROOT/"tests/test_schala_package_normal_nmi_closure_v2.py",Path(prior.__file__),Path(prior.irq.__file__),ROOT/"references/schala_package_normal_nmi_v1.json")],
        "full_normal_nmi_stack_bound":None,"global_nested_interrupt_bound":None,"production_approval":False,"rom_mutated":False}


def main():
    result=audit((ROOT/"private/input/rom_archive/Chrono Trigger (USA).sfc").read_bytes())
    sys.stdout.buffer.write((json.dumps(result,indent=2)+"\n").encode("utf-8"))
    return 0


if __name__=="__main__":raise SystemExit(main())
