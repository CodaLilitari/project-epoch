# Conditional scene-handler B/D/DBR returns, v1

Date: 2026-09-08. Evidence: **verified-static**, conditional on the exact entry
and memory/interrupt premises below. This separately numbered value audit
extends the accepted scroll projection without editing its source, tests, or
reference. No emulator is launched and no game artifact is written.

Of the **114 scene targets whose control flow and typed near returns already
closed**, 111 now prove B zero, D zero, and DBR `$7E` on every projected return
from native `M1/X0/I1`, B zero, D zero, and DBR `$7E` entry. All 114 prove the D
and DBR parts of that contract; three leave B unresolved in this conservative
model. The seven targets with unresolved indirect control flow remain excluded.

This is not a proof that every scene command preserves B, nor a new general
invariant for the scene interpreter. The earlier first-tick B-zero proof and
later unknown-B boundary remain separate. Even the 111 positive results apply
only to the identified targets under the declared entry values and alias/
asynchronous-execution premises.

## Results and explicit unresolved values

| Measure | Result |
| --- | ---: |
| Selected control-flow-closed targets and physical cells | 114 / 114 |
| Traversed by the unchanged scroll value model | 65 |
| Unsupported by that unchanged model | 49 |
| Traversed by the new minimal model | 114 |
| All returns prove B0/D0/DBR7E | 111 |
| B return remains unresolved | 3 |
| D0/DBR7E proved throughout the selected return set | 114 |
| Excluded control-flow-open targets / cells | 7 / 8 |

The unresolved B projections are:

| Physical command cell under B zero | Target | Projected root return | B results |
| --- | --- | --- | --- |
| `$F4` | `$CD1805` | `$CD1809` | zero or unknown |
| `$D9` | `$CD19B1` | `$CD24F2` | zero or unknown |
| `$AC` | `$CD2460` | `$CD24F2` | zero or unknown |

An unknown byte denotes an overapproximation of all possible byte values.
These results do **not** demonstrate that native execution returns nonzero B.
They also do not prove that a stronger value analysis could not establish
zero. For example, the inherited projection intentionally forgets an active
accumulator value after arithmetic and bitwise operations, even when a
particular mask might allow a more precise result. A later `XBA` can move that
unknown low byte into B; a later `TDC` under D zero resolves both bytes again.
This packet preserves that distinction instead of treating an unknown value
as a native failure or silently upgrading it to zero.

The remaining seven control-flow-open targets still account for eight cells,
because `$B5/$B6` share the open `$CD1F53` target. Their indirect frontiers are
retained verbatim from the accepted scene-handler census. They receive no
return-value contract from this packet.

## Minimal extension and inherited model

[The auditor](../tools/audit_schala_scene_handler_values_v1.py) copies the
accepted [scroll value projection](schala_nmi_scroll_inputs_v1.md) into a
separately named source and checks its parsed Python structure against that
frozen predecessor. The decoder uses the accepted scene-handler extension
inventory. There are exactly three new value-effect classifications:

1. `XBA` swaps A's complete low and high bytes regardless of the M flag.
2. Memory `ASL` and `ROL` change memory and flags, with no direct architectural
   A, D, or DBR effect. Their possible memory aliases remain outside this proof.
3. `TYX` changes X and flags. X values remain unmodeled, so a subsequent `TXA`
   still conservatively forgets the active accumulator width.

The other newly decoded instructions are covered by the inherited
conservative load/arithmetic/compare behavior. No `PHP/PLP`, `PHD/PLD`, `TCD`,
`PHK`, or `PEA` support is added: none appears in the complete decoded mnemonic
inventory of the 114 selected targets. Unsupported effects continue to refuse.
The original scroll source is unchanged and still refuses the added XBA
effect when exercised by its own API.

Memory loads become unknown in the active width. Immediate loads, `TDC`, and
typed A/bank stack transfers retain known bytes. Arithmetic forgets its active
A width. Byte operations preserve B except for explicitly full-register
instructions such as `XBA` and `TDC`. D remains the fixed entry value zero;
D-changing instructions are not implemented and therefore cannot silently
acquire an invariant. `PHB/PLB` transfer actual modeled byte values rather than
assuming that a balanced bank save restored a specific bank.

All conditional branches take both edges. Flags other than M/X/I are not
modeled, and no branch is pruned using a stale or partial flag calculation.
Loops reach a finite abstract fixed point or refuse on a bounded budget;
neither outcome is a native timing or termination proof. Every direct near
and long callee, and every supported direct tail jump, is followed with exact
typed return frames.

## What is checked against prior evidence

The historical 65/49 split is recomputed with the **unchanged** scroll value
walker on the same 114 canonical targets. Its first unsupported effects are
23 `$B7` cases, ten XBA `$EB` cases, five `$67` cases, five `$ED` cases, and six
`$77` cases. A first failure does not enumerate every unsupported instruction
later in that target; the new model uses the complete accepted opcode census.
The reference retains each target's first failure site and source identity.

For all 65 historical successes, the entire new value-projection object must
equal the old object. This checks that the decoder expansion did not change
already-supported paths or their results. For every one of the 114 new
projections, the auditor also requires exact agreement with its accepted
typed control-flow contract on:

- Decoded byte intervals and hashes.
- The complete width-qualified instruction-context identity.
- Direct-call inventory and mnemonic-context counts.
- The exact root-return sites and M/X/I return states.

Every reported endpoint must be a balanced root return with no remaining
software stack cell or return frame. These checks prevent a successful value
prefix from being presented as a full handler return. The result for each
target binds both the typed contract and the value projection by hash.

The source-driven audit operates only on the accepted 114 closed targets. Its
111/3 split, the three exact unresolved entries, and the historical first-fail
counts must match the reviewed result. The complete seven-target indirect
frontier set remains explicitly excluded rather than disappearing from the
report.

## Provenance

The canonical headerless US Rev0 ROM is read only: 4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Only addresses, derived relationships, and hashes enter the tracked output.
No copied ROM payload, SRAM, state, screenshot, or raw trace is produced.

The collector first reproduces these two accepted prerequisite references:

- [Scroll inputs](../references/schala_nmi_scroll_inputs_v1.json), 87,273 bytes,
  SHA-256 `003bf6be7e686445a8aa0a7bddf36bd8ca35b2fb49aa4d184ec5f3bc15db8013`.
- [Scene-handler closure](../references/schala_scene_handler_closure_v1.json),
  1,029,264 bytes, SHA-256
  `ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a`.

Their own collectors reproduce the earlier mode-input, mode-body, scene-input,
and closure-v2 evidence. The new collector retains and rechecks 21 underlying
source identities, all immediate prerequisites, and its own source/test
identities before and after the audit. It checks the exact imported dependency
paths and uses the existing bounded direct-path regular-file reader. It does
not accept a caller-supplied claim of canonical provenance as a substitute for
reproducing the pinned files.

Instruction semantics are reviewer-encoded from the pinned official Mesen
[SnesCpu.Instructions.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h):
memory ASL lines 635–646, memory ROL 679–690, TYX 1113–1116, and XBA 1118–1123.
These line numbers refer to the pinned local file. Its 27,673-byte identity is
SHA-256 `9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`.
The exact opcode/addressing inventory remains the reviewed scene decoder's
responsibility, bound to the same primary source commit. Hashes bind the
source used; they do not automatically infer instruction semantics.

This new result resolves part of a previously explicit value boundary. It
does not contradict the earlier stack-only or scroll-only results, and it
does not introduce a new mapping-correction entry.

## Reproduction and review status

```powershell
python -B -m unittest discover -s tests -p test_schala_scene_handler_values_v1.py -v
python -B tools/audit_schala_scene_handler_values_v1.py
```

The CLI prints UTF-8 indented JSON with LF and one trailing newline. It writes
no output file or game artifact itself. The 43 original host tests currently
pass. They cover known and unknown XBA bytes in both M widths, conservative
arithmetic followed by XBA, late TDC, nonzero high-byte preservation, new
memory shifts and TYX, all ten decoder extensions across M/X combinations,
unchanged old-model refusal, exact AST derivation, and return/context/alias
promotion rejection. These small original specimens are host tests, not
native game traces.

The finalized [reference](../references/schala_scene_handler_values_v1.json)
is 376,981 bytes, SHA-256
`cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543`.
The auditor is 21,359 bytes, SHA-256
`b92e5ff6534cb6383754753fa484ac6c4e8d38fab68e6645d207db9e47796610`;
tests are 8,109 bytes, SHA-256
`6c3d7e6f1b1da9c2b9166452842a4dcb0bf93b2b942905b154b615a5017f7601`.
Root and a second independent reviewer accepted the full source, effect
semantics, tests, and report within this scope. Each reran all 43 tests and
reproduced the exact metadata. The author and root each ran two actual fresh
CLI processes, with identical UTF-8 LF bytes, zero exit status, empty stderr,
and unchanged source/test identities. A further actual CLI output was emitted
as the final reference and checked byte-exact. No native execution was repeated.

The next bounded questions are the precise B dataflow in the three unresolved
targets and the seven previously identified indirect frontiers. The packet
does not establish arbitrary entry-register preservation, all-command closure,
complete legal command/script domains, memory aliases, asynchronous interrupt
ownership, a whole-NMI bound, or permission to install a hook or high selector.
