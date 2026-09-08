#!/usr/bin/env python3
"""Read-only normal-NMI fast-path proof and conditional local frontier census.

The full-body census uses explicit opaque-call return-width premises. It never
promotes its local stack arithmetic to a whole-NMI bound. Unknown opcodes,
unbalanced local frames, span escape and unreviewed call sites fail closed.
Only metadata is emitted; canonical game bytes stay private.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable

import audit_schala_package_interrupt_closure_v1 as irq

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-package-normal-nmi-frontiers-v1"
Read = Callable[[int, int], bytes]


class NmiError(ValueError):
    """Refuse an unsupported or inconsistent static claim."""


FIXED = dict(irq.FIXED)
FIXED.update({
    0x04:("TSB dp",2),0x0C:("TSB abs",3),0x1C:("TRB abs",3),
    0x2D:("AND abs",3),0x38:("SEC",1),0x3A:("DEC A",1),0x46:("LSR dp",2),
    0x65:("ADC dp",2),0x7D:("ADC abs,X",3),0x82:("BRL",3),
    0x84:("STY dp",2),0x86:("STX dp",2),0x88:("DEY",1),
    0x8A:("TXA",1),0x98:("TYA",1),0x9D:("STA abs,X",3),
    0x9E:("STZ abs,X",3),0xA4:("LDY dp",2),0xA7:("LDA [dp]",2),
    0xA8:("TAY",1),0xAC:("LDY abs",3),0xAE:("LDX abs",3),
    0xB9:("LDA abs,Y",3),0xBC:("LDY abs,X",3),0xBD:("LDA abs,X",3),
    0xC6:("DEC dp",2),0xC8:("INY",1),0xCA:("DEX",1),
    0xCE:("DEC abs",3),0xDE:("DEC abs,X",3),0xE8:("INX",1),
    0xEC:("CPX abs",3),0xEE:("INC abs",3),0xFC:("JSR (abs,X)",3),
    0xFD:("SBC abs,X",3),0xFE:("INC abs,X",3),
})


def decode(read: Read, pc: int, m8: bool, x8: bool) -> tuple[int,str,bytes]:
    raw=read(pc,1)
    if len(raw)!=1: raise NmiError("short opcode read")
    op=raw[0]
    if op in irq.M_IMMEDIATES: name,n=irq.M_IMMEDIATES[op],2 if m8 else 3
    elif op in irq.X_IMMEDIATES: name,n=irq.X_IMMEDIATES[op],2 if x8 else 3
    elif op in irq.BRANCHES or op==0x80: name,n="branch",2
    elif op in FIXED: name,n=FIXED[op]
    else: raise NmiError(f"unsupported opcode {op:02X} at {pc:06X}")
    raw=read(pc,n)
    if len(raw)!=n: raise NmiError("short instruction read")
    return op,name,raw


def busy_fast_path(read: Read, *, entry_m8: bool=False,
                   entry_x8: bool=False, entry: int=0xD1E77C,
                   end: int=0xD1E899, busy_branch: int=0xD1E79A,
                   rti: int=0xD1E898) -> dict:
    """Symbolically execute the exact path with physical $007F nonzero.

    Register bytes begin as independent symbols. This proves byte preservation
    without restricting incoming D/DBR or the accumulator's hidden B byte.
    Memory stores are restricted to the two long hardware register writes.
    """
    initial={k:(k+".lo",k+".hi") for k in ("a","x","y","d")}
    if entry_x8:
        initial["x"]=("x.lo",0); initial["y"]=("y.lo",0)
    initial["dbr"]=("dbr",)
    regs=dict(initial); stack=[]; peak=4; pc=entry
    m8,x8=entry_m8,entry_x8; zero=None; seen=[]; reads=[]; writes=[]
    push={0x48:"a",0xDA:"x",0x5A:"y",0x8B:"dbr",0x0B:"d"}
    pull={0x68:"a",0xFA:"x",0x7A:"y",0xAB:"dbr",0x2B:"d"}
    while len(seen)<80:
        if not entry<=pc<end: raise NmiError("fast path left pinned handler")
        op,name,raw=decode(read,pc,m8,x8); seen.append(pc); nxt=pc+len(raw)
        if op in (0xC2,0xE2):
            if raw[1]&0x04: raise NmiError("fast path changes interrupt-mask flag")
            if raw[1]&0x20: m8=op==0xE2
            if raw[1]&0x10:
                x8=op==0xE2
                if x8:
                    for k in ("x","y"): regs[k]=(regs[k][0],0)
        elif op in push:
            k=push[op]; n=(1 if m8 else 2) if k=="a" else ((1 if x8 else 2) if k in ("x","y") else len(regs[k]))
            stack.extend(reversed(regs[k][:n]))
        elif op in pull:
            k=pull[op]; n=(1 if m8 else 2) if k=="a" else ((1 if x8 else 2) if k in ("x","y") else len(regs[k]))
            if len(stack)<n: raise NmiError("fast-path pop consumes hardware frame")
            value=tuple(stack.pop() for _ in range(n))
            regs[k]=value+regs[k][n:]
        elif op==0xA9:
            value=tuple(raw[1:]); regs["a"]=value+regs["a"][len(value):]
            zero=all(x==0 for x in value)
        elif op==0x5B: regs["d"]=regs["a"]
        elif op==0x7B: regs["a"]=regs["d"]
        elif op==0xAF:
            address=int.from_bytes(raw[1:],"little")
            if address!=0x004210 or not m8: raise NmiError("unexpected fast-path long read")
            reads.append(address); regs["a"]=("RDNMI",regs["a"][1]); zero=None
        elif op==0xA5:
            if raw[1]!=0x7F or regs["d"]!=(0,0) or not m8:
                raise NmiError("busy flag is not the exact bank-zero byte")
            reads.append(0x00007F); regs["a"]=("busy-nonzero",regs["a"][1]); zero=False
        elif op==0x8F:
            address=int.from_bytes(raw[1:],"little")
            if address not in (0x00420C,0x004200) or not m8:
                raise NmiError("unexpected fast-path memory store")
            expected=0 if address==0x00420C else 0xA1
            if regs["a"][0]!=expected: raise NmiError("unexpected fast-path hardware value")
            writes.append({"address":f"${address:06X}","value":expected})
        elif op==0xF0:
            if pc!=busy_branch or zero is not False:
                raise NmiError("fast-path branch lacks nonzero-busy premise")
        elif op==0x4C: nxt=(pc&0xFF0000)|int.from_bytes(raw[1:],"little")
        elif op==0x40:
            if pc!=rti or stack or regs!=initial:
                raise NmiError("fast path does not restore exact register bytes")
            return {"entry_m8":entry_m8,"entry_x8":entry_x8,
                "instruction_count":len(seen),"instruction_addresses":[f"${p:06X}" for p in seen],
                "maximum_depth_including_hardware":peak,"software_depth":peak-4,
                "register_bytes_preserved":["A including B","X","Y","D","DBR"],
                "incoming_d_and_dbr":"unrestricted symbolic register values",
                "stack_and_hardware_return_frame":"software saves balanced; original four hardware bytes untouched",
                "nonstack_reads":[f"${p:06X}" for p in reads],"nonstack_writes":writes,
                "premise":"native interrupt entry; physical $00007F nonzero when read; no additional asynchronous interrupt"}
        else: raise NmiError(f"unexpected fast-path instruction {name} at {pc:06X}")
        peak=max(peak,4+len(stack)); pc=nxt
    raise NmiError("fast path did not reach RTI within its budget")


@dataclass(frozen=True)
class Region:
    role: str
    start: int
    end: int
    entry_depth: int
    exit_opcode: int


REGIONS=(
    Region("normal_handler_shell",0xD1E77C,0xD1E899,4,0x40),
    Region("mode_dispatch",0xCD0C95,0xCD0C9D,16,0x6B),
    Region("regular_mode_body",0xCD088D,0xCD09CE,18,0x60),
    Region("mode_zero_body",0xCD09F1,0xCD0ADE,18,0x60),
    Region("cgram_leaf",0xCD09CE,0xCD09F1,21,0x6B),
    Region("field_service_wrapper",0xCD0C89,0xCD0C95,16,0x6B),
    Region("screen_transition",0xCD05B2,0xCD05FF,20,0x60),
    Region("scene_tick",0xCD1609,0xCD1654,20,0x60),
    Region("scene_slot",0xCD1654,0xCD16A6,24,0x60),
    Region("scene_dispatch",0xCD16A6,0xCD16B5,28,0x60),
)

# Site -> (opcode, direct target or indexed-pointer table operand).
# Every call is a frontier, even when another region inventories its callee.
# Continuing local decoding after a call explicitly assumes a balanced return
# with M=1, X=0, I=1; it does not prove the callee obeys that interface.
CALLS={
    0xD1E7DA:(0x22,0xCD0C95),0xD1E7E3:(0x22,0xCD0C89),0xD1E841:(0x22,0xD1FE71),
    0xCD0C99:(0xFC,0xCD0C83),0xCD0C8C:(0x22,0xC00002),
    0xCD0893:(0x22,0xCD09CE),0xCD089B:(0x20,0xCD3EB4),0xCD08A9:(0x20,0xCD0607),
    0xCD08AC:(0x20,0xCD3EB4),0xCD08B4:(0x22,0xC10009),
    0xCD08F1:(0x20,0xCD0AEE),0xCD08F5:(0x20,0xCD05B2),0xCD08F8:(0x20,0xCD05B2),
    0xCD091A:(0x22,0xC28002),0xCD091E:(0x20,0xCD0340),0xCD0929:(0x20,0xCD06B4),
    0xCD092C:(0x20,0xCD0B51),0xCD097A:(0x22,0xCEE18E),0xCD0985:(0x22,0xD1EA4B),
    0xCD0993:(0x22,0xCEF066),
    0xCD0997:(0x22,0xC1000C),
    0xCD09AC:(0x20,0xCD3B82),0xCD09AF:(0x20,0xCD1609),0xCD09B8:(0x20,0xCD0B1E),
    0xCD09BB:(0x22,0xD1F426),0xCD09BF:(0x22,0xFDFFF7),0xCD09C3:(0x20,0xCD0ADE),
    0xCD09C6:(0x22,0xC28002),0xCD09CA:(0x20,0xCD0340),
    0xCD09F1:(0x22,0xCD09CE),0xCD0AB4:(0x22,0xC1000F),0xCD0ABC:(0x20,0xCD0AEE),
    0xCD0ACC:(0x20,0xCD06C4),0xCD0ACF:(0x20,0xCD0B1E),0xCD0AD2:(0x22,0xD1F426),
    0xCD0AD6:(0x22,0xFDFFF7),0xCD0ADA:(0x20,0xCD0ADE),
    0xCD05BE:(0x20,0xCD053C),0xCD05DA:(0x22,0xCEEE6E),0xCD05E5:(0x20,0xCD0577),
    0xCD1613:(0x20,0xCD0E9D),0xCD1631:(0x20,0xCD1654),0xCD1695:(0x20,0xCD16A6),
    0xCD16AF:(0xFC,0xCD16B5),
}


def local_frontiers(read: Read, region: Region, calls: dict=CALLS) -> dict:
    """Conditional local CFG; calls are recorded, never silently summarized."""
    queue=deque([(region.start,True,False,())]); seen=set(); decoded={}; edges=set()
    calls_seen={}; writes=set(); reads=set(); exits=0; peak=0; peak_with_call=0
    while queue:
        pc,m8,x8,stack=queue.popleft(); state=(pc,m8,x8,stack)
        if state in seen: continue
        seen.add(state)
        if len(seen)>12000: raise NmiError("local frontier state budget exceeded")
        if not region.start<=pc<region.end: raise NmiError(f"local CFG span escape at {pc:06X}")
        op,name,raw=decode(read,pc,m8,x8); nxt=pc+len(raw)
        if nxt>region.end: raise NmiError("instruction crosses local span")
        decoded[(pc,m8,x8)]=(name,len(raw)); dest=[nxt]; work=list(stack)
        if op in (0xC2,0xE2):
            if raw[1]&4 and op==0xC2: raise NmiError("local shell unmasks IRQ")
            if raw[1]&0x20: m8=op==0xE2
            if raw[1]&0x10: x8=op==0xE2
        elif op==0x08: work.append((m8,x8))
        elif op==0x28:
            if not work or not isinstance(work[-1],tuple): raise NmiError("unknown local PHP value")
            m8,x8=work.pop()
        elif op in (0x48,0xDA,0x5A,0x8B,0x0B):
            n=(1 if m8 else 2) if op==0x48 else ((1 if x8 else 2) if op in (0xDA,0x5A) else (1 if op==0x8B else 2))
            work.extend([None]*n)
        elif op in (0x68,0xFA,0x7A,0xAB,0x2B):
            n=(1 if m8 else 2) if op==0x68 else ((1 if x8 else 2) if op in (0xFA,0x7A) else (1 if op==0xAB else 2))
            if len(work)<n: raise NmiError(f"local pop consumes caller frame at {pc:06X}")
            del work[-n:]
        elif op in (0x20,0x22,0xFC):
            target=int.from_bytes(raw[1:],"little")|(0 if op==0x22 else pc&0xFF0000)
            if calls.get(pc)!=(op,target): raise NmiError(f"unreviewed call frontier at {pc:06X} target {target:06X}")
            n=3 if op==0x22 else 2
            calls_seen[(pc,m8,x8,len(work))]={"site":f"${pc:06X}","target_or_table":f"${target:06X}",
                "kind":"indexed-near" if op==0xFC else ("long" if op==0x22 else "near"),
                "instruction_sha256":hashlib.sha256(raw).hexdigest(),
                "entry_m8":m8,"entry_x8":x8,"local_saved_bytes":len(work),"call_frame_bytes":n,
                "conditional_depth_at_callee_entry":region.entry_depth+len(work)+n,
                "continuation_premise":"callee returns with exact call frame consumed, M=1/X=0/I=1; preservation and memory effects unproved here"}
            peak_with_call=max(peak_with_call,len(work)+n)
            m8,x8=True,False
        elif op in (0x60,0x6B,0x40):
            if op!=region.exit_opcode or work: raise NmiError(f"unbalanced local return at {pc:06X}")
            exits+=1; continue
        elif op==0x4C: dest=[(pc&0xFF0000)|int.from_bytes(raw[1:],"little")]
        elif op in irq.BRANCHES or op in (0x80,0x82):
            target=nxt+int.from_bytes(raw[1:],"little",signed=True)
            dest=[target] if op in (0x80,0x82) else [nxt,target]
        # This is a syntactic memory-operand inventory, not an effective-address
        # proof. Indexed/indirect references intentionally retain that label.
        if name.split()[0] in {"STA","STX","STY","STZ","INC","DEC","TSB","TRB","MVN"} and len(raw)>1:
            width=(1 if x8 else 2) if name.startswith(("STX","STY")) else (1 if m8 else 2)
            if op==0x54: width=0  # MVN length is A+1, not accumulator width.
            writes.add((pc,name,int.from_bytes(raw[1:],"little"),width))
        if name.startswith(("LDA ","LDX ","LDY ")) and "#" not in name:
            reads.add((pc,name,int.from_bytes(raw[1:],"little")))
        peak=max(peak,len(work)); edges.update((pc,p) for p in dest)
        queue.extend((p,m8,x8,tuple(work)) for p in dest)
    if not exits: raise NmiError("no balanced conditional local exit")
    starts={k[0] for k in decoded}
    for pc,_,_ in decoded:
        if any(other<pc<other+n for (other,_,_),(_,n) in decoded.items()):
            raise NmiError(f"overlapping width decode at {pc:06X}")
    return {"role":region.role,"span":[f"${region.start:06X}",f"${region.end:06X}"],
        "span_sha256":hashlib.sha256(read(region.start,region.end-region.start)).hexdigest(),
        "entry_depth_premise":region.entry_depth,"entry_width_premise":"M=1/X=0; shell immediately REP #$30",
        "instruction_starts":len(starts),"decoded_width_contexts":len(decoded),"balanced_conditional_exits":exits,
        "maximum_local_saved_bytes":peak,"maximum_local_saved_plus_one_call_frame":peak_with_call,
        "whole_callee_depth_bound":None,"opaque_call_frontier_count":len(calls_seen),
        "calls":[v for _,v in sorted(calls_seen.items())],
        "syntactic_write_operands":[{"site":f"${p:06X}","mnemonic":n,"encoded_operand":f"${a:X}","width_bytes":w or None,
            "effective_address_and_aliasing_proved":False} for p,n,a,w in sorted(writes)],
        "syntactic_load_operands":[{"site":f"${p:06X}","mnemonic":n,"encoded_operand":f"${a:X}"} for p,n,a in sorted(reads)],
        "interpretation":"conditional local CFG inventory; no unknown callee stack/memory behavior is certified"}


def audit(rom: bytes) -> dict:
    if len(rom)!=0x400000 or hashlib.sha256(rom).hexdigest()!=irq.ROM_SHA256:
        raise NmiError("requires exact canonical headerless US Rev0 ROM")
    def read(pc:int,n:int)->bytes:
        if not 0xC00000<=pc<pc+n<=0x1000000: raise NmiError("read outside canonical ROM")
        return rom[pc-0xC00000:pc-0xC00000+n]
    fast=[busy_fast_path(read,entry_m8=m,entry_x8=x) for m in (False,True) for x in (False,True)]
    if any(x["maximum_depth_including_hardware"]!=13 for x in fast): raise NmiError("fast-path stack identity changed")
    regions=[local_frontiers(read,r) for r in REGIONS]
    observed={int(c["site"][1:],16) for r in regions for c in r["calls"]}
    if observed!=set(CALLS): raise NmiError("call census differs from exact reviewed catalog")
    return {"schema":SCHEMA,"evidence_level":"verified-static",
        "status":"pass-busy-fast-path-and-conditional-frontier-census-full-nmi-open",
        "canonical_rom_sha256":irq.ROM_SHA256,
        "source_identities":[{"path":p,"sha256":hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in
            ("tools/audit_schala_package_normal_nmi_v1.py","tests/test_schala_package_normal_nmi_v1.py",
             "tools/audit_schala_package_interrupt_closure_v1.py")],
        "busy_fast_path":fast,"conditional_regions":regions,
        "mode_table_three_reviewed_cells":[{"mode":i,"target":f"$CD{int.from_bytes(read(0xCD0C83+2*i,2),'little'):04X}"} for i in range(3)],
        "full_nmi_stack_bound":None,"global_nested_interrupt_stack_bound":None,
        "global_stack_headroom_proved":False,"nonstack_memory_alias_closure":False,
        "whole_normal_nmi_call_closure":False,"production_approval":False,"rom_mutated":False,
        "remaining_frontiers":["opaque callees and their return-width/register/memory contracts",
            "mode predecessor constraints; initial mode-dispatch B=0 follows the pre-call TDC, but later scene-command B depends on callee contracts",
            "scene command legal table extent, stream provenance, termination and callees",
            "DMA/HDMA effective sources and destinations, nonstack writes aliasing stack",
            "leading/trailing zero-busy windows and hardware reentry timing",
            "alternate installed NMI and its early incoming-DBR dependency"]}


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom",type=Path,default=ROOT/"private/input/rom_archive/Chrono Trigger (USA).sfc")
    args=parser.parse_args()
    try: result=audit(args.rom.read_bytes())
    except (OSError,NmiError) as exc: parser.exit(1,f"normal NMI audit refused: {exc}\n")
    print(json.dumps(result,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
