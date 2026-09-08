# Conditional scene-command handler closure

Date: 2026-09-08. Status: independently reviewed `verified-static` result.
This adds a conditional control-flow and typed-stack census for the
122 previously reviewed scene-command pointer cells. It does not establish
a legal command domain, handler-return register values, physical stack
ownership or a complete NMI bound.

The [scene input audit](schala_scene_dispatch_inputs_v1.md) already separates
the first tick's proved hidden accumulator byte B=0 from an unknown B after
an arbitrary command returns. Its physical prefix covers commands `$80-$F9`
under B=0 and contains 121 distinct targets. This packet asks what each of
those targets does to the typed call stack and M/X/I state, assuming it is
entered through a native near call in M1/X0/I1. It never assumes that those
premises hold for every later command.

## Results

| Measure | Result |
| --- | --- |
| Reviewed physical pointer cells | 122 |
| Distinct near-call targets | 121 |
| Targets closed by the unchanged prior decoder | 67 |
| Targets closed by this separately versioned decoder | 114 |
| Cells whose targets close | 114 |
| Remaining distinct open targets | 7, selected by 8 cells |
| Balanced return contexts in the closed subset | 123, all M1/X0/I1 |
| Largest additional depth within one closed handler | 16 bytes at `$CD1805` |
| Same closed-handler maximum including its root near frame | 18 bytes |

The 16/18-byte numbers describe the closed subset only. Seven targets remain
open, and no whole-dispatcher or whole-NMI stack bound is assigned. An open
walk's encountered local peak remains explicitly exploratory, even if the
walk found a balanced return on another branch before reaching its frontier.

The largest closed target calls `$D1EBFF` and then includes the nested paths
through `$D1F9AF`, `$D1F91D`, `$D1F972` and `$CD38B2`. The metadata retains
each exact direct call, source span, instruction-context digest and peak site.
These are bounded abstract control-flow paths; no timing or termination proof
is inferred from the finite traversal.

The remaining frontiers are:

| Command cells under B=0 | Handler entry | First frontier | Unresolved operation |
| --- | --- | --- | --- |
| `$B5/$B6` | `$CD1F53` | `$CEE7CC` | `JMP (abs)`: pointer value and target |
| `$8C` | `$CD2958` | `$CD295E` | `JMP (abs,X)`: index and target domain |
| `$8D` | `$CD2999` | `$CD299F` | `JMP (abs,X)`: index and target domain |
| `$88` | `$CD29DA` | `$D1FBCE` | `JSR (abs,X)`: index, targets and nested returns |
| `$80` | `$CD2A4A` | `$CD2A4E` | `JMP (abs,X)`: index and target domain |
| `$82` | `$CD2DD6` | `$CD2DE7` | `JMP (abs,X)`: index and target domain |
| `$8B` | `$CD2FB7` | `$CD319A` | `JMP (abs,X)`: index and target domain |

These command values identify physical cells under the earlier B=0 recipe.
They do not prove a stream used the values, that all values are legal, or
that arbitrary handler returns preserve B=0. The `$FA-$FE` cells still overlap
the occupied `$F9` handler body and are excluded from this reviewed prefix.

## What changed in the auditor

The previous [normal-NMI closure v2](schala_package_normal_nmi_closure_v2.md)
and every source/reference it accepted remain byte-for-byte unchanged.
Its walker initially closed 67 of these 121 targets. Of the remaining 54,
48 first stopped on an instruction that its deliberately small decoder did
not support; six stopped at indexed dispatches.

This separately named auditor copies the pinned prior walker and adds ten
documented instructions that do not directly change SP or M/X/I:

- `$B7` `LDA [dp],Y`; `$67` `ADC [dp]`; `$77` `ADC [dp],Y`.
- `$ED` `SBC abs`; `$6F` `ADC long`; `$C4` `CPY dp`.
- `$06` `ASL dp`; `$26` `ROL dp`; `$2E` `ROL abs`; `$BB` `TYX`.

The memory shifts are included in the syntactic write-operand inventory with
their M-dependent width. They are not silently treated as memory reads.
`JMP (abs)` at opcode `$6C` has its own explicit unresolved frontier. Its
pointer is never read as if a constant target had already been established.
All other unsupported opcodes retain the prior fail-closed behavior.

The collector checks the copied walker's parsed Python structure against the
pinned original after exactly two declared edits: that `$6C` frontier and
the ASL/ROL write inventory. Decoder additions live in a separate immutable
table and cannot overwrite prior supported opcodes. It also reruns both old
and new walkers on all 121 targets. Every previously closed result must agree
exactly, apart from the declared additional syntactic write metadata.

The opcode/addressing pairs are checked against the pinned official Mesen
[CPU dispatcher](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h).
The source's [ADC/SBC implementations](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L73),
[memory shifts](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L635),
[loads](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L934)
and [long indirect addressing](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1297)
support the reviewer-encoded effect classification. Hashing those sources
does not automatically infer instruction semantics. Exact full-file hashes,
dispatch line numbers and operation names are retained in the metadata.

## Provenance and reproduction

The input is the canonical 4,194,304-byte US Rev0 image, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The collector first reproduces the complete accepted closure-v2 and scene
input references. It then rereads the 122 exact cell pointers from that image,
walks the derived unique targets, joins every cell to one contract, and checks
the source identities again. No game bytes or private traces are emitted.

The [accepted metadata](../references/schala_scene_handler_closure_v1.json)
is 1,029,264 bytes, SHA-256
`ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a`.
Its source is `tools/audit_schala_scene_handler_closure_v1.py`, SHA-256
`2c8de06dea25a35971143bf6a8c868aea1996a6ab6a8de26fa4b5a12c9ade71d`;
its 40 original tests are SHA-256
`89b50ffd56f3fdc9aa528fd14c563281226421d10140c92a7d4483aa727357da`.
The independent reviewer passed all 40 tests, reproduced that complete output
exactly and confirmed the type-substitution counterexample is rejected. Two
actual post-review CLI processes also returned identical UTF-8/LF bytes with
empty stderr before the reference was written and reread.

```powershell
python -B tools/audit_schala_scene_handler_closure_v1.py
python -B -m unittest discover -s tests -p test_schala_scene_handler_closure_v1.py
```

The tests use original short opcode sequences and metadata fixtures. They
check every new instruction across all four M/X combinations, memory-shift
write widths, exact typed returns and PHP/PLP restoration, unchanged prior
decoder behavior, indirect frontiers, instruction overlap, missing/duplicate
cells and targets, address/type substitution, scope promotion and canonical
identity rejection before walking. They require no ROM or emulator trace.

A pre-review expected-total check initially guessed 115 closed cells from
114 closed targets. The exact join rejected that expectation: the only alias,
`$B5/$B6`, shares the open `$CD1F53` target. The correct closed-cell count is
114, while the 114 closed-target result never changed. The failed draft and
exact source files are preserved under ignored
`private/test_runs/scene_handler_closure_20260908_pre_review_count/`, with
receipt SHA-256 `88f2b3ab9e3e8e9745b469d5e17deca5638fe66880722fb73acf8102372df108`.
This is a correction to an unpublished expectation, not a contradiction of
an upstream mapping or a relabeling of accepted evidence.

Independent review also found that the metadata join accepted `2.0` as the
frame-inclusive byte count through Python numeric equality. The collector
now requires an exact integer, and an added negative fixture rejects that
substitution. The canonical walker already emitted integers; no native or
static control-flow result changed. The pre-fix source, tests and report are
preserved under ignored
`private/test_runs/scene_handler_closure_20260908_peer_type_review/`, receipt
SHA-256 `4b20ebb490af018a661a0cf46fa3e2a9a033386ecb819473d9cfce5e0326a518`.

## Remaining obligations

All contracts assume ordinary writable stack RAM and that nonstack writes,
DMA and asynchronous activity do not overwrite the abstract saved stack or
status. They do not establish effective addresses for ordinary reads/writes,
live-game stack ownership, return values of A/B/X/Y/D/DBR, legal command or
script domains, or interrupt nesting. The seven indirect frontiers and the
handler-return B contract remain concrete next boundaries. No production
hook, expanded allocation, high-selector binding or PC `$07` behavior is
approved by this packet.
