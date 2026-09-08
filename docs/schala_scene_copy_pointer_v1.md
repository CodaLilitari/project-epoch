# Scene B5/B6 copy-pointer contract v1

Date: 2026-09-08. Evidence: **verified-static**, conditional source analysis.
No emulator launch, ROM mutation, game hook, allocation, or production binding
is performed by this packet.

The indirect jump at `$CEE7CC`, reached from the shared scene-command
`$B5/$B6` target `$CD1F53`, has an identifiable pointer producer and a finite
physical copy routine. It is now possible to state exactly when that producer
selects a valid suffix. **The legal game-data domain remains open.** The old
scene-handler census and its unresolved B5/B6 classification are preserved.

For the selected producer inputs described below, the independent instruction
evaluation and integer expression agree on all **65,536** byte pairs. Exactly
**64,414** select a physical suffix; **1,122** point outside the copy routine.
The successful relation is `abs(r-s) <= 222`. This relation is derived and
compared exhaustively, rather than supplied as a presumed game invariant.

The [auditor](../tools/audit_schala_scene_copy_pointer_v1.py) and
[original host tests](../tests/test_schala_scene_copy_pointer_v1.py) are
separately named. They do not extend or modify the accepted scene walkers.

## Exact caller and pointer namespaces

The accepted open-frontier census identifies this path:

`$CD1F53 -> $CD35A5 -> $CD3616 -> $CEE7C8 -> $CEE7CC`.

The first three edges are near calls, except the transition to `$CEE7C8`,
which is a long call. The original wrapper makes a further near call to
`$CEE7CC`. The earlier census preserves the exact typed frame chain at that
frontier; the new collector verifies that evidence before composing returns.

At `$CD1F96`, the branch that reaches the call executes `TDC`, switches A to
8-bit, and clears the byte `$7ECAAA` before calling `$CD35A5`. Under D zero,
the complete accumulator is zero there, including hidden B. The producer
therefore reads the byte `$7ECAAA` as zero, transfers full A to X16, and reads
the two byte inputs at **`$7ECAA4` (r)** and **`$7ECAA8` (s)**. These are the
producer's exact inputs; descriptive radius/position labels do not establish
their allowed values.

The earlier command reads a script-selected source row and has its own zero
exit and fill loop. This packet does not prove that its selected row, or the
eventual global CAA4/CAA8 bytes, enforce the safe relation. Its observation
that CAAA is cleared applies only if the call is reached. The complete
preceding command's data/alias and runtime-reachability obligations remain
separate.

The final pointer store is the M16 direct-page store at `$CD362B`, writing
both `$4B/$4C`. The consumer at `$CEE7CC` is **absolute-indirect** `JMP ($004B)`:
it reads **bank-zero `$00004B/$00004C`**, independent of D and DBR, then keeps
program bank `$CE`. A direct-page producer and this absolute-indirect consumer
refer to the same physical pointer only under the explicit **D=0** premise.
The target is `$CE:word`, not a long pointer stored in three DP bytes.
[Pinned indirect-addressing implementation](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1216)

## Exhaustive producer domain

The new finite instruction projection starts at `$CD35A5` with native
M8/X16/I1, B=0, D=0, DBR=`$7E`, and **decimal flag clear**. A is zero from
the immediate caller prefix. X, Y, carry and branch flags begin unknown;
using an uninitialized value refuses. The actual producer overwrites these
before use. Each direct-page byte must have an earlier modeled writer.
The model follows the real branch conditions with exact binary carry,
borrow, sign and width behavior. It rejects unsupported opcodes, instruction
overlap, changing instruction lengths, unexpected calls, unknown reads, or
an exhausted finite instruction budget.

The code contains no CLD that could justify arbitrary decimal-mode entry.
Binary mode is a stated input condition. ADC/SBC results are truncated to
the active width and their carry/borrow conditions are retained. This
interpretation uses pinned Mesen's actual binary arithmetic implementation.
[Word arithmetic](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L35)

The word read of `$CAAA` at `$CD35FE` needs a separate qualification:
the caller cleared only its low byte, so `$CAAB` is still unknown. The very
next instruction is the M16 `AND #$0001` at `$CD3601`. The projection carries
an explicit unknown-high marker and requires that exact immediate mask
before any other use or branch. All high bits are then removed. It does not
pretend that the word load itself returned zero or let a branch consume a
placeholder flag. The subsequent parity read of DP `$7C` is outside the
arithmetic projection and both parity continuations are checked separately.

For each pair r,s in `$00-$FF`, the executed arithmetic is compared against
the separately written integer expression:

```text
n = r + min(r,s) - max(r + max(r,s) - 222, 0)
count_word = (2*n) mod 65536
pointer_word = ($E7C7 - 6*n) mod 65536
```

The comparison uses the actual DP word recorded at `$CD361D`, and the final
pointer bytes written at `$CD362B`. No annotation supplies the multiplication
factor or the unit of n. The code multiplies a byte count by three; a complete
word-copy pair occupies six instruction bytes.

The enumeration yields n from -33 through 222. The relation
`abs(r-s) <= 222` is checked against actual target membership in the verified
physical suffix set for every pair. It is not merely checked against n's
sign. Every successful n from 0 through 222 occurs. Examples near the boundary:

| r | s | n | Pointer result | Interpretation |
| ---: | ---: | ---: | --- | --- |
| 0 | 222 | 0 | `$CEE7C7` | Empty suffix, immediate RTS |
| 0 | 223 | -1 | `$CEE7CD` | Outside the copy routine; inside the JMP's operand bytes |
| 255 | 32 | -1 | `$CEE7CD` | Same out-of-routine result |
| 255 | 33 | 0 | `$CEE7C7` | Empty suffix |
| 111 | 111 | 222 | `$CEE293` | Longest suffix selected by this producer |
| 255 | 0 | -33 | `$CEE88D` | Outside the copy routine |

These invalid-input examples are mathematical and static source witnesses.
They are not observed game failures or proof that any such pair is reachable.
The full r-major/s-minor matrix is represented by SHA-256
`63949e99a17ae90a05152202df30f07a1a16225bf387254c1aff290e85ce3b2e`.
Each record consists of r, s and the safe bit as three bytes, followed by the
actual count and pointer as two little-endian words. The reference also
retains the complete count distribution and the exact modeled read/context
inventory. It contains no extracted ROM payload.

## Physical suffixes and return-frame composition

The exact physical routine contains **256** complete pairs, starting at
`$CEE1C7`, followed by RTS at `$CEE7C7`. Pair k loads a word at source offset
`2*k` relative to Y and stores it at destination offset `4*k` relative to X.
The pairs run from the highest selected offset down to zero. Each pair is
one three-byte LDA absolute,Y plus one three-byte STA absolute,X.

The auditor reconstructs all pair bytes and verifies the preceding six bytes
do not extend the same pattern. This proves **257 physical suffix entries**:
256 LDA starts plus the empty suffix at RTS. The producer's safe outputs use
only **223** of those entries, representing 0 through 222 pairs. The first
34 physical pairs are inside an `incbin` region of the old disassembly;
the source audit must not mistake the first visibly annotated pair at
`$CEE293` for the beginning of the physical routine. No copy-data contents,
effective-address ownership, graphics result or HDMA-table correctness is
inferred from the repeated instruction pattern.

The validated suffixes add no stack bytes. Their RTS consumes the existing
near wrapper frame. A small typed return walker then verifies both original
arms, including the actual opcode and branch bytes:

| Return instruction | Consumed frame | Next PC | Counted bytes remaining |
| --- | --- | --- | ---: |
| RTS `$CEE7C7` | Near | `$CEE7CB` | 9 |
| RTL `$CEE7CB` | Long | `$CD3644` or `$CD3656` | 6 |
| RTS `$CD3656` | Near | `$CD3612` | 4 |
| RTS `$CD3615` | Near | `$CD1F9F` | 2 |
| RTS `$CD1F9F` | Original near caller | Caller | 0 |

The first arm executes the exact BRA from `$CD3644` to `$CD3656`. The common
suffix at `$CD3612` performs TDC and SEP M8 before its near return. Under the
D-zero and no-alias premises this restores B0/D0/DBR7E at the selected root
return. The frontier has 11 counted bytes including the original two-byte
near frame, or nine below the root's entry. This is conditional composition
for the validated producer inputs and unchanged frames. The global B5/B6
contract remains open, as do physical interrupt-stack ownership and a whole
normal-NMI stack bound.
[Near and far returns](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L479)

## Reproduction, history and remaining work

The collector first regenerates the exact accepted scene-values v1 reference
and retains its 111/3 classification. That prerequisite already regenerates
the accepted scene-handler census. The new collector reads that pinned
census and requires its original `$CEE7CC` M16/X16/I1 frontier and complete
11-byte typed frame chain. It does not overwrite those historical results.
Twenty-nine inherited source identities, the three immediate prerequisites,
the new source/tests, canonical-ROM hash and all selected source-span hashes
are checked. Full source identities are checked again after collection.

The canonical ROM identity remains the headerless 4,194,304-byte US Rev0 image,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The arithmetic, control-transfer and indirect-addressing interpretation uses
Mesen commit `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`; its instruction source
is 27,673 bytes, SHA-256
`9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`.
The new metadata pins four reviewed semantic line spans as well as the
complete source. Those hashes identify the source of the reviewed semantics;
they do not mechanically prove the interpretation by themselves.

```powershell
python -B -m unittest discover -s tests -p test_schala_scene_copy_pointer_v1.py -v
python -B tools/audit_schala_scene_copy_pointer_v1.py
```

All 37 original host tests pass. They cover input namespaces and decimal
refusal; exact arithmetic, carry and borrow; uninitialized DP/index/flags;
wrong calls and final pointer writers; unknown-high masking; instruction
overlap and changing widths; complete suffix geometry, wrong strides and
return kinds; both typed continuations and wrong branch/width/zero restoration.

The first exploratory full collection refused because it initially allowed
only byte reads of CAAA. Reading the actual later M16 access exposed the
unknown CAAB byte and led to the explicit mask dependency above. An initial
operand-overlap test also reached an unsupported decode before its intended
ownership error; moving the existing-owner check ahead of decoding makes
that boundary fail directly. Both were development refusals before any
accepted reference or native run. Complete exploratory enumeration then
matched the stated domain. Root and second-peer review both read the complete
frozen source/tests/report, passed all 37 tests, and independently reproduced
the exact CLI output. The final
[reference](../references/schala_scene_copy_pointer_v1.json) is emitted;
the executable source and tests remain unchanged.

Two fresh actual CLI processes produce identical 70,722-byte UTF-8/LF
metadata, SHA-256
`13913c7b244b454a8afd4afd89977408466e2dda06699578f344b9c691789c53`,
with empty stderr and unchanged source/test identities. The source is
18,696 bytes, SHA-256
`e3fb94da358b0bd122d9e6f502cacd4fb424af0ec19831ccb89b0bb5ceb4e973`;
the tests are 9,614 bytes, SHA-256
`9dd6fb63ca9877da69226648a7de4fa3198b2bf67bdd6612ca0767bf655862ca`.

The next concrete obligation is to establish what writes CAA4/CAA8, under
which actual scene-command/script domain and lifetime, and whether those
paths enforce the derived relation before this call. No production hook,
allocation, selector binding, DMA safety, or playable PC `$07` follows from
this packet.
