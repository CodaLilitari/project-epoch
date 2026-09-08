# Three word-load zero-edge refinements, scene values v2

Date: 2026-09-08. Evidence: **verified-static**, conditional on the same native
entry, stack, memory-alias, and asynchronous-execution premises as v1. No
native execution, ROM mutation, production binding, or shared catalog change
is performed by this packet.

The [preserved v1 value audit](schala_scene_handler_values_v1.md) proves
B0/D0/DBR7E returns for 111 of 114 selected control-flow-closed targets and
leaves B unresolved for three. This separate v2 now proves that conditional
return contract for **all 114 selected targets**, using only three exact
word-load/taken-BEQ refinements. The seven targets whose indirect control
flow remained open in the accepted census are still excluded. This result
does not by itself establish a complete scene-command loop or whole NMI.

The v1 result was conservative, not incorrect. Its unchanged reference,
source, tests, and 111/3 classification remain part of this packet's required
provenance. The new result increases the precision of an explicit boundary;
it is not a mapping correction or evidence of a native B-register failure.

## The three zero-length exits

All three unresolved v1 targets reach the shared quad-window rasterizer.
That routine has three paths where a 16-bit `LDA` is immediately followed by
`BEQ`. The taken branch skips a later `TDC`, because the complete accumulator
is already zero when that branch is taken.

| Word load | Immediate BEQ | Taken destination | Fallthrough path's final TDC | Common suffix |
| --- | --- | --- | --- | --- |
| `$D1FA47` | `$D1FA49` | `$D1FA65` | `$D1FA64` | `SEP #$20`, `RTS` |
| `$D1FAC7` | `$D1FAC9` | `$D1FAE5` | `$D1FAE4` | `SEP #$20`, `RTS` |
| `$D1FB47` | `$D1FB49` | `$D1FB65` | `$D1FB64` | `SEP #$20`, `RTS` |

The first load uses direct-page operand `$45`; the other two use `$49`.
In each accepted instruction context the accumulator is 16-bit. A taken BEQ
directly after that word load implies the loaded word is zero, hence both
A.low and B are zero. The other branch remains conservatively modeled; its
eventual `TDC` supplies zero under the unchanged D-zero premise.

This changes only the three previously unresolved target classifications:

| Command cell under B zero | Target | Preserved v1 result | v2 result |
| --- | --- | --- | --- |
| `$F4` | `$CD1805` | B zero or unknown; D0/DBR7E proved | B0/D0/DBR7E proved |
| `$D9` | `$CD19B1` | B zero or unknown; D0/DBR7E proved | B0/D0/DBR7E proved |
| `$AC` | `$CD2460` | B zero or unknown; D0/DBR7E proved | B0/D0/DBR7E proved |

The remaining 111 targets retain their positive classification. All 114
decoded source-context identities, direct-call inventories, and exact
typed return contexts still agree with the preserved scene-handler closure.
The changed classification does not make arbitrary entry B/D/DBR values safe:
the target entry contract remains native near `M1/X0/I1`, B zero, D zero,
and DBR `$7E`.

## Why this does not use a stale zero flag

[The v2 model](../tools/audit_schala_scene_handler_values_v2.py) adds the actual
immediate predecessor PC to every abstract state. At each of the three
allowlisted sites it requires all of these conditions:

- The current instruction is BEQ at the exact named PC.
- The immediate executed predecessor is the named adjacent load.
- The accumulator is 16-bit at that boundary.
- The predecessor bytes decode as the exact direct-page LDA operand.
- The branch target is the exact named suffix address.

If any condition fails, the model refuses instead of borrowing the new rule.
In particular, entering the BEQ directly, jumping into it from another
instruction, using an LDX-produced zero flag, changing the DP operand, using
an 8-bit accumulator, changing BEQ to BNE/BRA, or changing the destination
cannot produce this refinement.

Both successors remain in the control-flow graph. Only the taken successor
gets A.low=0 and B=0; the fallthrough retains its inherited unknown values.
No other BEQ is refined, and no general Z/N/C flag model or branch pruning is
introduced. The no-asynchronous-register/status-change premise remains
necessary between the load and branch, just as it is elsewhere in this
conditional static model.

The source verifies the parsed Python function against v1 after exactly the
declared predecessor-state, named-edge guard, taken-edge transfer, and evidence
record additions. It reuses the unchanged v1 decoder and value effects.
Its finite-state count may increase because predecessor identity distinguishes
previously merged states. That metadata difference does not imply new CPU
execution or a different source instruction corpus.

## Source and evidence provenance

The canonical headerless US Rev0 ROM is read only: 4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The exact named half-open source spans are:

| Span | Bytes | SHA-256 |
| --- | ---: | --- |
| `$D1FA47..$D1FA4B` | 4 | `12b5b20d2cf244802019e00efd0380b88cf2d33264d7f8d909a4b0aeeb0131b8` |
| `$D1FAC7..$D1FACB` | 4 | `376265e47c5d1a903b5472ac440b8b574a95fdf3240cacaaef7b6cdd557ebecb` |
| `$D1FB47..$D1FB4B` | 4 | `376265e47c5d1a903b5472ac440b8b574a95fdf3240cacaaef7b6cdd557ebecb` |
| `$D1FA64..$D1FA68` | 4 | `052b462218d0e720daca46617ff0a556d75683287a65e4c870290344635bbf5c` |
| `$D1FAE4..$D1FAE8` | 4 | `052b462218d0e720daca46617ff0a556d75683287a65e4c870290344635bbf5c` |
| `$D1FB64..$D1FB68` | 4 | `052b462218d0e720daca46617ff0a556d75683287a65e4c870290344635bbf5c` |

The interpretation is pinned to official Mesen commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. In
[SnesCpu.Instructions.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h),
BEQ at lines 173–176 uses the Zero flag; LoadRegister at 916–923 and LDA at
934–938 select a word load when M is zero. In
[SnesCpu.Shared.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h),
SetRegister at 580–589 and SetZeroNegativeFlags at 591–600 set Z precisely
when that full word equals zero. These are pinned local-file line numbers.
Their full SHA-256 identities remain
`9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`
and `dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f`.

The collector reproduces the immutable
[v1 reference](../references/schala_scene_handler_values_v1.json):
376,981 bytes, SHA-256
`cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543`.
It also reproduces the accepted scene-handler census and independently
rebuilds every one of the 114 v1 target projections before using the new
model. All new value projections must agree with the accepted typed source
and return contexts. The exact three changed target classifications and the
exact three refined branch sites are mandatory; an unexpected change refuses.

Twenty-seven inherited source identities, immediate prerequisites, and the
new source/tests are bounded-read and checked before and after collection.
The reference retains both old and new contract hashes for the three changed
targets and preserves all seven unresolved control-flow frontiers. No raw
ROM payload or emulator trace is tracked.

## Reproduction and current status

```powershell
python -B -m unittest discover -s tests -p test_schala_scene_handler_values_v2.py -v
python -B tools/audit_schala_scene_handler_values_v2.py
```

The 18 original host tests currently pass. They exercise all three exact
zero edges, both-edge retention, conservative fallthrough, the unchanged v1
unknown result, M8 rejection, direct/jump entry into BEQ, wrong flag-producing
load, wrong operand/opcode/target, unchanged unlisted BEQ behavior, exact source
contexts, AST-delta refusal, and canonical-ROM refusal before walking. The
short instruction specimens are original host tests, not native trace data.

The finalized [reference](../references/schala_scene_handler_values_v2.json)
is 357,484 bytes, SHA-256
`52543e1820669eac00b90baa39e307dcb9b35c9be14e7a0eff42e5aa762d8b87`.
The collector writes only UTF-8 LF JSON to stdout and creates no game file.
An independent peer reviewed the full source, tests, report, and pinned CPU
semantics, reran all 18 tests, and reproduced the exact metadata through an
actual CLI process. The author also ran two actual fresh CLI processes with
identical bytes, zero exits, empty stderr, LF-only UTF-8, and unchanged source
and test identities. After that independent review passed, another actual CLI
output was emitted as the reference and checked byte-exact.

Frozen auditor: 19,076 bytes, SHA-256
`cfacea4c27289daa12f8a2965ee4e16b46b53b4f7b72b23ec91b648eedf9c872`.
Frozen tests: 6,150 bytes, SHA-256
`76bd30b55b96d1c2580a76af7827256119899b8bfbc4f4e56974e743603b9528`.
The review found no blocking issue within this conditional scope. No native
execution or inherited source change occurred.

The complete legal command/script domain, the seven excluded indirect
frontiers, effective memory addresses and aliases, DMA effects, physical
interrupt/stack ownership, termination/timing, and whole-NMI closure remain
separate obligations. The independently authored scene-opcode `$82` packet
can resolve one of those frontiers under its own entry contract; it is not
silently merged into this historical 114-target set. No production hook,
allocation, high-selector mapping, or PC `$07` behavior is approved here.
