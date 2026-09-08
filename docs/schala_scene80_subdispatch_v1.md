# Scene `$80`: pointer/code topology and conditional subdispatch v1

Date: 2026-09-08. Evidence level: `verified-static`. Review status: accepted
after independent root and peer review; the exact reference has been emitted
and reread. No native replay, ROM output, hook, allocation or production
binding is part of this packet.

The scene `$80` dispatcher has **29 physical pointer words before its first
selected code body**. This is a source-topology boundary, not a proved legal
parameter range. Of those 29 selected targets, the unchanged models prove 27
conditional balanced returns with B0/D0/DBR `$7E`. Two remain explicit source
frontiers. All 156 bytes after those 29 words and before the annotated
`incbin` endpoint are covered by the first 29 targets' instruction decodes.

The broader B0 arithmetic admits 128 physical pointer cells. Its already
completed census is retained as secondary, hypothetical metadata: 33 cells
select 32 targets with conditional return contracts; 95 cells select 84
targets with unresolved frontiers. Successful decoding outside the 29-word
prefix does not turn those cells into legal entries. No full dispatcher or
whole-NMI stack bound follows.

## What is new, and what stays preserved

The accepted [scene-handler control census](schala_scene_handler_closure_v1.md)
leaves scene `$80` at `$CD2A4E`, an indexed `JMP`. This packet adds its exact
local input arithmetic, physical byte topology, conditional target contracts
and explicit remaining frontiers. It reruns the unchanged typed control
walker and [value-v1 model](schala_scene_handler_values_v1.md); no decoder or
value effect is added. Value-v2's three word-load refinements are unnecessary
here and are not a dependency.

The new artifacts are:

- `tools/audit_schala_scene80_subdispatch_v1.py`: read-only auditor and LF JSON CLI.
- `tests/test_schala_scene80_subdispatch_v1.py`: 40 original host tests.
- This human-readable report.
- Reviewed reference: `references/schala_scene80_subdispatch_v1.json`.

Scene command `$80`, Schala action `$80`, and package selector `$80` remain
separate namespaces. This packet creates no association among them.

## Exact dispatcher input contract

The canonical seven-byte prefix is `$CD2A4A..$CD2A51`:

| Site | Operation under native M1/X0 | Relevant result |
|---|---|---|
| `$CD2A4A` | `LDA [$40]` | Reads one arbitrary byte through the direct-page long pointer; B is retained. |
| `$CD2A4C` | `ASL A` | Doubles the low byte modulo 256; the original parameter bit 7 is discarded. |
| `$CD2A4D` | `TAX` | Copies full A into sixteen-bit X, including hidden B. |
| `$CD2A4E` | `JMP ($2A51,X)` | Reads its near pointer in program bank `$CD`; adds no return frame. |

For parameter `p` and hidden byte `B`, both exact bytes:

```text
X = (B << 8) | ((p << 1) & $FF)
pointer-low address  = CD : (($2A51 + X) & $FFFF)
pointer-high address = CD : (($2A51 + X + 1) & $FFFF)
```

With B0, parameters `i` and `i+$80` select the same cell for each index
`i=$00..$7F`. The 128 starts are `$CD2A51..$CD2B4F`, and their complete
256-byte footprint is the half-open span `$CD2A51..$CD2B51`. There is no
local range check or mask restricting this to 29 targets. The conditional
first-29 restriction is `B=0` and `(p & $7F)<29`; it is not a discovered
producer-domain invariant.

The auditor independently checks all 65,536 B/parameter combinations against
the equivalent arithmetic `256*B + 2*(p mod 128)`. All B values together
produce 32,768 word starts whose low/high bytes cover bank `$CD`. The odd
base permits a word read straddling its end: `B=$D5,p=$57` gives `X=$D5AE`
and reads `$CDFFFF/$CD0000`. Only the B0 destinations are followed; the all-B
calculation is address arithmetic, not a target or legal-domain proof.

The conditional target models assume native near entry M1/X0/I1,
B0/D0/DBR `$7E`, and an existing two-byte scene return frame. A.low, X/Y
values and memory-load results are conservatively unknown where the model
does not establish them. All conditional branches are followed. The
dispatcher's known initial X does not justify pruning target branches.

## Why the `incbin` length is not a table length

The pinned annotation labels `Dispatch_BattleSceneB` at `$CD2A51`, followed
by `incbin` covering `$2A51..$2B27`. That packaging interval is 214 bytes,
which is arithmetically 107 words. It does **not** assert or establish 107
legal entries. [Pinned `bank_CD.asm`, lines 3595–3602](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_CD.asm#L3595)
supplies the annotation provenance; canonical source bytes determine the
new topology result.

The first 29 words occupy `$CD2A51..$CD2A8B`. Their 29 selected targets are
distinct, and their minimum target is exactly `$CD2A8B`, selected by index
27. At `$CD2A8B`, the unchanged walkers decode a twelve-byte routine that
begins `TDC; TAX` and reaches its sole `RTS` at `$CD2A96` with no extra
stack. Consequently, cell 29 reads that executable `TDC/TAX` pair as the
pointer `$CDAA7B`. The next physical word is already code under a reviewed
conditional entry context.

This is stronger than a single overlapping instruction. The union of
decoded intervals from the first 29 target walks covers **every one of
the 156 bytes** in `$CD2A8B..$CD2B27`, with no hole. The union includes the
partial source reached before the two explicit frontiers; it does not
claim their complete return paths. It is conditional source decoding, not
observed execution or proof that every covered instruction is reachable.

The source annotation itself is not treated as a mapping error: `incbin`
can legitimately contain mixed data and code. The corrected inference is
that neither its byte count nor its label establishes a legal table
extent. No unsupported prior claim of 107 legal entries is attributed to
the disassembler.

## First 29 targets: 27 returns and two exact frontiers

Every first-29 target except indices 9 and 13 closes under the unchanged
typed walker. Every one of those 27 closed targets also passes independent
value-v1 projection with exact decoded-context identity, byte intervals,
call sites, mnemonic counts and return-site/width agreement. All projected
returns have B0/D0/DBR `$7E`, M1/X0/I1 and no remaining local frame.
A.low may be known or unknown and is not asserted to be zero globally.

The largest additional stack use among these **27 closed targets only**
is three bytes, yielding five including the existing two-byte near frame.
The indexed `JMP` adds zero. This is neither a bound for all first 29
targets nor a bound for the dispatcher or its enclosing NMI.

| Physical index and aliases | Selected target | First unresolved instruction | State at frontier | Full return/stack contract |
|---|---|---|---|---|
| 9: `$09/$89` | `$CD2BFC` | `$CD2C07`, opcode `$44` (`MVP`) | M0/X0/I1; two counted bytes, existing near frame | Unresolved/null |
| 13: `$0D/$8D` | `$CD2B64` | `$D1F11D`, opcode `$75` (`ADC dp,X`) | M1/X1/I1; seven counted bytes, existing near plus nested long frame resuming at `$CD2B68` | Unresolved/null |

Those counts are local observed abstract depths at the frontiers, not full
bounds. The source-only model refuses the unsupported effects rather than
assuming their stack or register behavior. A separately numbered proof
could review these two effects and any further source they expose. V1 does
not silently extend the decoder to close them.

## Secondary hypothetical census of all 128 B0 cells

The exact 256-byte physical footprint yields 116 distinct selected targets.
The complete retained control metadata reports:

| Conditional result | Physical cells | Unique targets |
|---|---:|---:|
| Typed closure plus B0/D0/DBR `$7E` return | 33 | 32 |
| Explicit remaining frontier | 95 | 84 |

Outside indices 0–28, indices 47, 57, 58, 59, 61 and 62 happen to select
closed source paths; 59 and 62 select the same target. These are hypothetical
arithmetic destinations and are not approved extensions of the table.

The 95 frontier cells divide into 83 unsupported-opcode cases, one unexpected
`RTI`, two overlapping decodes, five stack-pointer assignments, one return-frame
mismatch, two further indexed jumps and one return-kind mismatch. Each exact
selected target and first frontier remains in the metadata. V1 does not add
semantics or explore further branches to make these cells close.

One direct counterexample prevents treating arbitrary B0 parameters as a
uniform near-return family: index 35 (`$23/$A3`) selects `$CDC122`, whose
first instruction is `RTI`. A native interrupt return does not match the
dispatcher's existing two-byte near frame. This is an instruction/frame
counterexample under a hypothetical input; it is not evidence that ordinary
gameplay supplies that parameter or that a vanilla runtime defect occurs.

## Provenance and reproduction

The canonical input is the unchanged US Rev0 ROM, 4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
It stays private. The auditor checks the whole image and six named spans,
including the exact prefix, first 29 words, first code body, complete
annotated `incbin`, full hypothetical footprint and `RTI` counterexample.
Only hashes, addresses and original analysis are emitted.

The existing handler and value-v1 references are regenerated byte-for-byte
before reuse. Their exact source and reference pins, the pinned annotation,
the new auditor/tests and **29 inherited source identities** are checked
before and after collection. The immutable Mesen 2.1.1 source identities
underpin byte-mode ASL, full-width TAX, program-bank indexed pointer reads,
and the reused architectural value/stack rules. The metadata preserves
those primary-source identities and the older auditors' semantic scopes.

Run from the project root:

```powershell
python -B -m unittest discover -s tests -p test_schala_scene80_subdispatch_v1.py
python -B tools/audit_schala_scene80_subdispatch_v1.py
```

The second command emits UTF-8 indented JSON with LF and one trailing
newline to binary stdout. It writes no image, trace, directory or reference
file. A reference is emitted separately only after independent review.

The 40 tests use original executable miniatures, exhaustive input algebra,
and explicitly synthetic metadata partitions. They test byte-width B
retention against word-width nonzero-B refusal, typed near-frame accounting,
source/context disagreement, exact scalar types, bank/width/register
refusals, alias/termination overclaims, all-byte topology coverage and
canonical input refusal before any source walk. They are host checks, not
native evidence. The first author test run passed all 40; the first
collection produced the identities below. No abandoned runtime or image
artifact exists for this packet.

Frozen auditor: 17,082 bytes, SHA-256
`5bf0ff11fa69ad09f74e204524444ec336b036a6c1ccc6ee90c649275a68492f`.
Frozen tests: 8,999 bytes, SHA-256
`909da68de2896c0dcda47df71fb37e35b6ae15387e8bad2278b82803461a8c89`.
Emitted reference: 424,188 bytes, SHA-256
`98ef60b958f997bc125d2550ff90c9cd6948a9f7b269be7fc0194790cfbece2f`.

Root and the second reviewer independently read the source, tests, report
and relevant canonical/primary-source evidence; each ran all 40 tests and
reproduced the exact CLI bytes. Root checked two actual CLI invocations.
After both acceptances, the author ran two additional actual CLI processes,
verified identical UTF-8 LF output with empty stderr and unchanged auditor/test
identities, emitted their exact bytes with exclusive file creation, and
reread the reference byte-for-byte. No source/test change was needed after
review; only this report's review and emission status was updated.

The remaining legal script/parameter domain, pointer/source lifetimes,
effective writes, stack/nonstack aliases, DMA/asynchronous behavior,
termination, timing and whole-NMI composition remain open. Production
approval and new native execution are explicitly false.
