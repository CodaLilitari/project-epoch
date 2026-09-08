# Normal NMI: closed busy path and remaining integration frontiers

The normal NMI's busy-flag fast path now has an independent symbolic proof:
**13 bytes below the interrupted SP**, including the four hardware bytes,
with exact restoration of A including its hidden B byte, X, Y, D, and DBR.
The proof accepts all four native entry M/X combinations and unrestricted
symbolic incoming D/DBR. It applies when physical `$00007F` is nonzero at
the handler's test and no further interrupt preempts this handler.

The full NMI remains open. A separate conditional local control-flow census
now inventories **44 call sites across ten bounded code regions**, including
four calls hidden inside the older disassembly's `incbin` blocks. The census
makes those calls explicit obligations. It does not assign a whole-NMI stack
bound by assuming that their implementations are harmless.

This is `verified-static` evidence within the pinned source and stated
premises. There is no new emulator run, helper installation, production
allocation, ROM mutation, or PC `$07` claim. The previously published IRQ v1
audit and stack-frame v2 design remain unchanged.

## Reproduction and evidence identity

The original read-only utility is
[`audit_schala_package_normal_nmi_v1.py`](../tools/audit_schala_package_normal_nmi_v1.py).
The exact source identities, region hashes, instruction counts, call-site
instruction hashes, and symbolic results are in
[`schala_package_normal_nmi_v1.json`](../references/schala_package_normal_nmi_v1.json).
Only metadata is emitted. The tool requires the canonical headerless US Rev0
ROM SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.

```powershell
python tools/audit_schala_package_normal_nmi_v1.py
python -m unittest discover -s tests -p test_schala_package_normal_nmi_v1.py -v
```

All **23 original host tests pass**. They exercise symbolic register damage,
busy-flag addressing, width changes, frame damage, unsupported operations,
unknown call targets, indirect-call frame sizes, PHP/PLP, span escape,
instruction overlap, and the distinction between local arithmetic and a
whole-callee bound. They need no ROM. Two independent in-process canonical
audits generated identical metadata before the reference was written.

The upstream source used for human labels is the unchanged private checkout
`private/research/ct_disassembly_eeae27a`, commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`. Canonical bytes and native width
state govern the audit; the labels do not supply instruction lengths.

## What is closed on the busy path

Entry `$D1E77C` first selects 16-bit A/X/Y, then saves A, X, Y, DBR, and D
in nine bytes. It sets D to zero. The two early writes address hardware by
long addressing, before DBR is changed: `$00420C = $00` and `$004200 = $A1`.
The handler reads `$004210`, then reads the actual bank-zero busy byte at
`$00007F`. If nonzero, `$D1E79C` jumps to the restore block at `$D1E891`.
The software frame is restored before RTI at `$D1E898`.

The symbolic executor follows all 24 instructions on that path. It begins
with independent symbols for the saved register bytes and requires the
final bytes to equal the originals. It refuses an unexpected memory write,
changed mask flag, wrong busy address, unsupported instruction, wrong saved
register, stack underflow, or non-restoring return. It does not rely on D=0
or DBR=`$7E` at the interrupted instruction. Consequently, incoming source
DBR `$41/$42` is included in this bounded preservation result.

The path never increments or clears the busy flag, never copies direct page,
and never enters a service routine. Its non-stack writes are the two long
hardware writes above. This is stronger than observing preserved registers
at one checkpoint, but it still excludes asynchronous nesting and physical
stack-region ownership.

## What the full-body census means

Each region has an explicit entry width and an explicit conditional depth
derived from its caller frames. The utility follows both outcomes of local
conditional branches and tracks M/X, local pushes/pops, and PHP/PLP. At a
call it records the exact direct target or indexed table operand and its
two-byte near or three-byte long frame.

To inventory the caller instructions *after* an opaque call, the utility
declares a premise: that callee returns with the exact call frame consumed
and M=1/X=0/I=1. That premise is stored at every call. The utility does not
prove it from an unknown callee. A later local exit therefore proves only
conditional local balance. Every reported whole-callee and full-NMI depth
bound stays null. DBR, D, hidden B, memory effects, and termination of an
opaque callee remain separate obligations.

This deliberate separation permits a complete local call inventory without
pretending it is an interprocedural closure proof. An unknown opcode, span
escape, local frame error, ambiguous instruction overlap, IRQ unmasking, or
call site/target absent from the reviewed catalog is a hard refusal.

| Region | Entry depth premise, including hardware | Instruction starts | Call sites |
| --- | ---: | ---: | ---: |
| Normal handler shell `$D1E77C` | 4 | 121 | 3 |
| Mode dispatch `$CD0C95` | 16 | 5 | 1 |
| Regular mode body `$CD088D` | 18 | 122 | 24 |
| Mode-zero body `$CD09F1` | 18 | 93 | 8 |
| CGRAM leaf `$CD09CE` | 21 | 13 | 0 |
| Field-service wrapper `$CD0C89` | 16 | 9 | 1 |
| Screen transition `$CD05B2` | 20 | 30 | 3 |
| Scene tick `$CD1609` | 20 | 36 | 2 |
| Scene slot `$CD1654` | 24 | 43 | 1 |
| Scene dispatch `$CD16A6` | 28 | 9 | 1 |

The four newly explicit call sites are `$CD0893 -> $CD09CE`,
`$CD089B -> $CD3EB4`, `$CD097A -> $CEE18E`, and `$CD0985 -> $D1EA4B`.
They lie inside the upstream `bank_CD.asm` blocks `$0893-$08A0` and
`$097A-$0989`. This fills an annotation gap; it does not contradict a prior
claim that these spans are data or free space. The canonical region hashes
and per-call instruction hashes in the reference provide provenance without
committing game bytes.

## Stack frontiers that matter for v2

The following are exact frame arithmetic along stated routes, not maxima
for all full-NMI paths:

- Normal entry hardware plus register saves contributes 13 bytes. The full
  path also has a transient one-byte PHA used to set DBR, reaching 14 before
  any service. That temporary push is absent from the busy fast path.
- Mode dispatch adds a JSL frame of three and an indexed-JSR frame of two,
  placing its selected body at a conditional depth of 18.
- The field-service wrapper enters at 16, saves DBR/D/P in four bytes, and
  calls `$C00002` with another three: the unexplored callee begins at 23.
- The scene route reaches `$CD16AF` after the outer 18, scene-tick JSR two,
  PHY two, slot JSR two, slot PHX two, and command-dispatch JSR two. The
  indexed call adds two more: **30 bytes before a scene command body**.
- The screen-transition reinitialization path reaches the display loader at
  23. Its PHB plus eight saved word pointers adds 17, producing the previously
  identified **40-byte conditional path**. The IRQ v1 audit independently
  closes that loader's instruction/push-pop behavior. Earlier opaque calls
  still need their contracts before this becomes a whole-path proof.

These frontiers already show why the non-nested IRQ's 35-byte maximum cannot
serve as the full interrupt reserve. They also do not prove that the 40-byte
transition path occurs while the package helper executes.

## Dispatch and memory ownership remain open

The initial full-NMI prefix proves D=0, sets DBR=0 before mode dispatch, and
uses TDC to zero the full accumulator before its eight-bit loads. Thus B=0
at the first `$CD0C99` indexed dispatch. The three reviewed encoded cells are
mode 0 to `$CD09F1`, modes 1 and 2 to `$CD088D`. The mode reader does not
clamp the byte. Eight-bit ASL also discards its high bit; those three cells
do not certify every mode predecessor or every mechanically possible index.

Scene commands present a larger independent frontier. `$CD165F` distinguishes
tilemap operations, `$7F` yield, `$FF` end, and `$80-$FE` command dispatch.
`$CD16AF` calls through the table operand `$CD16B5` after ASL/TAX. The existence
of 127 syntactic byte values does not prove a 127-entry legal command table.
The valid extent, command-specific return states, command loops, script
source provenance, and B-byte state after prior opaque commands remain open.
Mechanically treating every following word as a legal entry would promote
unclassified table-adjacent content to code authority.

The main prefix copies exactly 43 bytes, `$7E0000-$7E002A`, to
`$7ECC65-$7ECC8F`; the epilogue copies them back. This does not preserve DP
`$80-$83`. The scene machinery independently uses DP `$40-$44`, mutable
scene slots `$CA32/$CA42`, and the shared `$7E5D9B` completion latch. The
known field wrapper saves D/DBR/P around its service but does not close the
callee's non-stack reads or writes. The metadata's memory operands are
syntactic inventories, with effective-address/alias proof explicitly false.

Stack-local state avoids the retired global scratch collision only if all
interrupt activity respects the stack's lifetime. An indirect store, a
block move, or a DMA/HDMA transfer can still reach a stack range without
using PHA/PLA. CPU call-frame balance does not constrain those aliases.
The v2 frame, caller frame, interrupt reserve, direct-page mirrors, DMA
sources, and all effective destinations need separate coverage.

Full normal-NMI preservation remains conditional on balanced callees and no
alias damage. The busy-path proof does not resolve alternate NMI:
`$D1F4C0` still calls its early CGRAM service before selecting DBR, as recorded
in the [IRQ/placement review](schala_package_interrupt_closure_v1.md).

## Nesting and deliberate preemption design

The busy flag becomes nonzero at `$D1E79F` and is cleared at `$D1E88B`.
An NMI that sees it nonzero takes the 13-byte fast path. For example, the
closed 35-byte IRQ peak plus one such NMI is 48 bytes. A leading NMI window
before the increment, or a trailing window after the clear, can see zero
and enter the full body. The fast path itself leaves the flag unchanged.

The code does not by itself bound the number or placement of asynchronous
entries. Arbitrarily repeated injection into a zero-flag window would not
have a finite global depth bound in a timing-free model. This is not a claim
that hardware generates those entries. A usable nesting bound must combine
the installed handlers, busy-flag state, interrupt-edge timing, and I behavior.

The next v2 synthetic preemption diagnostic should therefore use an original,
explicitly scoped interrupt fixture and record the actual hardware frame:

1. Interrupt around frame allocation/release, local JSR entry/return,
   source-bank PHA/PLB, pointer preflight, and the publication boundaries.
2. Exercise both source DBRs, incoming status bits, and the retained hidden B
   value; confirm handler entry/RTI context and byte-exact helper continuation.
3. Measure actual nested hardware/save depth and guard the caller frame,
   live local extent, lower interrupt reserve, and every memory write.
4. Keep a short busy-path fixture separate from a deeper original fixture.
   Passing either proves its declared synthetic contract, not execution of
   the complete game NMI. Executing the real game handlers is a later,
   separately prepared and pinned diagnostic.

For v2's 52-byte deepest helper frame, one proved busy-path NMI adds 13,
giving 65 bytes of arithmetic depth from helper entry. A 35-byte IRQ plus
one guarded NMI gives 100. The 40-byte conditional full-NMI route would
give 92 before any additional nesting. None of these numbers establishes
game stack ownership or a universal reserve. Production remains blocked
on the explicitly open full-NMI, alias, timing, and installation contracts.
