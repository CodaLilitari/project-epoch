# Scroll-dispatch inputs and four conditional target contracts, v1

Date: 2026-09-08. Evidence: **verified-static**, within the stated native-mode,
stack, alias, and asynchronous-execution premises. This is a separate additive
packet. It preserves the mode-input, mode-body, and closure-v2 references and
does not run an emulator or install a resolver hook.

The new result is a conditional caller-value proof: starting at `$CD088D` with
native `M1/X0/I1`, `D=$0000`, `DBR=$00`, and **unknown incoming accumulator B**,
every modeled path that reaches `$CD0929` before entering the separately cut
pad-input route has **B=$00, D=$0000, DBR=$7E**. The call at `$CD0929` therefore
reaches the absolute `$CA92` load in `$CD06B4` with the data bank required to
read `$7ECA92`. Its byte value is still an independent, unbounded input here.

The four previously reviewed physical pointer cells can then be composed with
their exact target stack/width contracts under an additional selected-input
premise. The eight CA92 bytes `$00/$01/$02/$03/$80/$81/$82/$83` select those four
cells when B is zero. This is an arithmetic alias result, **not a proof that
all eight are legitimate or reachable scroll modes**.

## Why the caller needed a new proof

The earlier [mode-body composition](schala_nmi_mode_bodies_v1.md) deliberately
left register values open at `$CD06B9`. Its typed stack walker establishes
widths and return frames; it does not silently give every callee a preserving
ABI. The earlier reference is still correct in its stated scope. No mapping
correction or annotation-error claim is introduced by this additive result.

The local mode-body prefix publishes `DBR=$7E` at `$CD08A0..$CD08A4`. Much later,
`TDC` at `$CD08EE` clears the complete accumulator under the D-zero premise.
That instruction alone was insufficient: its value crosses a window-setup
call and two transition calls before the scroll dispatcher, and those calls
contain further direct callees. The new value projection follows the complete
relevant callee paths and checks their decoded byte coverage and direct-call
inventory against the accepted closure-v2 metadata.

The caller projection has **947 abstract states and 587 instruction contexts**.
Its only two endpoints are pre-execution stops at `$CD0907` and `$CD0929`.
Both retain the exact root near-call frame and have B zero, D zero, and DBR
`$7E`. Only the `$CD0929` endpoint supplies the scroll-call contract. The other
endpoint cuts before the external pad-input route; this packet does not prove
that route returns, cannot rejoin, or preserves these values afterward.

The six distinct direct callee roots needed by the caller prefix are checked
separately with B zero, D zero, and DBR `$7E`. Every one is fully inlined by the
new value projection, including its descendants and direct tail jumps.

| Callee root | Call kind | Value-projection states | Conditional result |
| --- | --- | ---: | --- |
| `$CD09CE` | Long | 13 | B zero, D zero, DBR `$7E`; `M1/X0/I1` return |
| `$CD3EB4` | Near | 30 | Same; includes `$CD3E8E` DMA setup |
| `$CD0607` | Near | 125 | Same; includes `$D1E8D9` and the near DMA tail |
| `$C10009` | Long | 229 | Same; follows the direct far tail into `$CFE300` |
| `$CD0AEE` | Near | 17 | Same; window setup uses the actual caller bank in the inlined prefix |
| `$CD05B2` | Near | 160 | Same; includes `$CD053C`, `$CD0577`, and `$CEEE6E` |

The standalone six-callee contracts are additional checks; their input bank
is not substituted for the temporary bank used by the actual caller. In the
full caller projection, `$CD0AEE` executes after the real `PHB/TDC/PHA/PLB`
sequence with DBR zero, and the following `PLB` restores `$7E`.

None of the decoded relevant callee instructions changes D. The model rejects
`TCD`, `PLD`, and any unsupported instruction effect, so D invariance is checked
over the complete declared instruction coverage. Paths through transition and
DMA helpers either preserve an already-zero B byte or clear the full
accumulator with `TDC` after using 16-bit A. The transition's `MVN` sequence
changes DBR to its encoded destination and ends with the actual saved-bank
pull. The source analysis follows those saves and pulls as values; it does not
infer them merely from balanced stack depth.

## Projection semantics and limits

[The new auditor](../tools/audit_schala_nmi_scroll_inputs_v1.py) reuses the
unchanged closure-v2 opcode and instruction-width inventory. Its register
semantics are separately implemented and independently tested. The state
contains A's low and high bytes, DBR, `M/X/I`, typed stack cells, and exact
near/long return identities. D is fixed at the explicit entry value zero, and
every instruction that could change it is unsupported and causes refusal.

Immediate A loads, `TDC`, byte/word A stack transfers, and `PHB/PLB` preserve
known byte values. Memory loads become unknown in the active accumulator
width. Arithmetic and index-to-A transfers conservatively forget their active
A width. An 8-bit operation keeps the hidden B byte. X/Y values and all flags
besides `M/X/I` are unmodeled; every conditional branch takes both edges even
when the preceding value would make one edge infeasible. This avoids using a
stale or incompletely modeled condition flag as a proof.

`MVN` has a deliberately narrow native `M16/X16` projection: after its complete
repeat sequence, A is `$FFFF` and DBR is the encoded destination bank. The
projection does not invent transferred contents or prove effective source or
destination addresses. Any nonstack CPU write or DMA write aliasing a saved
stack cell remains excluded by an explicit premise. Without that premise,
typed stack-value reconstruction alone cannot prove physical saved values.

The model refuses indirect dispatch, status pulls with unmodeled values,
stack-pointer assignment, emulation transitions, IRQ unmasking, mismatched
return kinds or banks, overlapping instruction decodes, consumed return
frames, and bounded-state exhaustion. Reaching a fixed point is a finite
analysis result; it is not a proof that a game loop terminates or meets an NMI
timing budget. The reported local peak is explicitly not a whole-path or
whole-NMI stack bound.

## Exact scroll index and occupied successor

The canonical dispatcher is `$CD06B4..$CD06BC` (half-open), SHA-256
`0016098af9a67c4facae3dd092e328de1da7bb6e0c74f4ec5075db44779827d7`.
Its source recipe is:

1. Read one byte at absolute `$CA92` using DBR.
2. Shift the 8-bit A value left once, retaining the hidden B byte.
3. Transfer the full accumulator to 16-bit X.
4. Use `JMP ($06BC,X)` in program bank `$CD`.

Thus `X = (B << 8) | ((CA92 << 1) & $FF)`. The pointer's low-byte address is
`$CD0000 | (($06BC + X) & $FFFF)`; its high-byte address uses `$06BD` with the
same 16-bit bank-local arithmetic. This jump adds **no new return frame**. It
uses the existing near frame from the caller at `$CD0929`, whose continuation
is `$CD092C`.

The auditor checks all 65,536 hypothetical B/CA92 pairs, represented by 32,768
high-bit alias pairs. Because both the table base and index are even, no
selected pointer word straddles `$CDFFFF/$CD0000`. Base-plus-index arithmetic
can still wrap within PBR; for example B `$F9`, CA92 `$22` reads at `$CD0000`.
This differs from the previously reviewed odd-based scene dispatcher, whose
pointer word can straddle the bank boundary.

The four reviewed cells occupy `$CD06BC..$CD06C4`, exactly eight bytes. The
first following cell, selected by B zero and CA92 `$04/$84`, overlaps the
executable `SEP #$10` at `$CD06C4`. Interpreting those two instruction bytes as a
pointer gives `$CD10E2`. This is evidence of an occupied successor, not a free
extension slot or a proof that such an input is valid. The reference lists the
128 possible physical cells for B zero as an arithmetic inspection inventory;
it does not relabel them as a 128-entry legal table.

## Four conditional target contracts

The unchanged closure-v2 walker is run only after the caller-value proof and
then only for the four reviewed cells. Its native entry remains `M1/X0/I1` with
the existing two-byte near frame. No per-target D, DBR, A/X/Y value-preservation
claim is added here. Source-role rendering behavior, memory footprints, and
DMA effects are also outside this target closure.

| Cell index | B-zero CA92 aliases | Target | Sole return | Additional bytes below target entry | Total including existing scroll near frame |
| --- | --- | --- | --- | ---: | ---: |
| 0 | `$00/$80` | `$CD06C4` | `RTS $CD076B` | 0 | 2 |
| 1 | `$01/$81` | `$CD076C` | `RTS $CD076B` | 0 | 2 |
| 2 | `$02/$82` | `$CD07E2` | `RTS $CD088C` | 0 | 2 |
| 3 | `$03/$83` | `$CD07B9` | `RTS $CD07E1` | 2 | 4 |

Target 1 jumps into target 0's shared fill at `$CD0706`. Target 3 first calls
target 2 at `$CD07B9`; that one additional near frame explains its two-byte
increment. All four returns have `M1/X0/I1`. The table jump itself contributes
zero bytes, and the mode-body's own near frame, upstream long frame, software
saves, and hardware interrupt frame are not folded into these local totals.

The native-runtime dispatch snapshots and parent-owned calibration work remain
separate evidence. This packet adds no new execution and makes no claim that
a particular table cell was selected during a new run.

## Provenance and reproduction

The canonical headerless US Rev0 ROM is read only: 4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Canonical instructions and table payloads never leave private input storage;
the tracked output contains metadata, address recipes, and hashes only.

The prerequisite references are:

- [Mode inputs](../references/schala_nmi_mode_inputs_v1.json), SHA-256
  `dc715f6726e482a00e649d15252b5ca42f933f82198d8520c78d7867f3932530`.
- [Mode bodies](../references/schala_nmi_mode_bodies_v1.json), SHA-256
  `f3057c1cf9d0b354a318e3e67b2c760fdf9d8bfc49784d4efed344ba997a8d85`.
- [Direct closure v2](../references/schala_package_normal_nmi_closure_v2.json),
  SHA-256 `413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242`.

The collector reproduces the complete accepted mode-body packet, which itself
reproduces the mode inputs and closure-v2 packet. It binds the current source
and test files, the immutable prerequisite sources, twelve underlying source
identities, and the two primary CPU sources before and after the new audit.
Reads use the existing bounded, direct-path, regular-file checks. The CLI
prints UTF-8 JSON with LF and one trailing newline; it writes no output file,
ROM, SRAM, state, or patch.

Primary instruction semantics are pinned to Mesen commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`:

- [SnesCpu.Instructions.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h),
  27,673 bytes, SHA-256
  `9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`:
  indexed jump lines 434–443; MVN 717–742; PLB 822–829; TAX 1058–1061;
  TDC 1078–1081. These are local pinned-file line numbers.
- [SnesCpu.Shared.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h),
  20,483 bytes, SHA-256
  `dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f`:
  lines 369–372 show the 16-bit address argument combined with PBR.

The pinned annotation checkout is commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`. Its bank-CD caller and dispatcher,
bank-D1 quadrant helper, bank-CE transition table loader, and bank-CF upload
worker provide human-readable source names; canonical bytes and the declared
instruction semantics control the result. All four file identities are
retained in the metadata. Annotation search also identifies explicit `$CA92`
store candidates at `$CD0466`, `$D1F250`, `$CD161A`, `$CD25BC`, and `$CD262D`.
That text search is not a complete direct/indirect/overlapping writer census,
and these candidates do not establish a global legal producer domain.

Reproduce the original host fixtures:

```powershell
python -B -m unittest discover -s tests -p test_schala_nmi_scroll_inputs_v1.py -v
```

Reproduce the complete source-only metadata:

```powershell
python -B tools/audit_schala_nmi_scroll_inputs_v1.py
```

The 49 host tests currently pass. They cover hidden B under byte/word
operations, actual bank saves/restores, conservative arithmetic and memory
loads, both branch edges, near/long frames, MVN bank order, unsupported D/SP
and status effects, overlap and budget refusal, caller context rejection,
and exhaustive pointer alias/wrap arithmetic. They contain only original tiny
instruction examples; host fixtures are not native game evidence.

The root's independent review passed the complete source/value/stack semantics
and all 49 host tests. It also independently checked the canonical `$CD0929`
near-call encoding and its three-byte continuation. Two actual fresh CLI
processes produced identical UTF-8 LF output with empty stderr and unchanged
sources. The finalized [reference](../references/schala_nmi_scroll_inputs_v1.json)
is **87,273 bytes**, SHA-256
`003bf6be7e686445a8aa0a7bddf36bd8ca35b2fb49aa4d184ec5f3bc15db8013`.
The author then regenerated and emitted those exact bytes without a native
launch. Frozen auditor: 19,678 bytes, SHA-256
`4153a240d3a1fa750dd0ac67626776e061ceb049f03b9fce54fc08da8e31c686`;
tests: 9,965 bytes, SHA-256
`f4083eb152d606a39511a011e7454384c237f3ece149d786202bd718c328a3c9`.

The next useful boundary is a separately scoped producer and lifetime proof
for `$CA92`, or a continuation proof after the selected scroll target returns.
This packet grants neither global NMI closure nor production hook, scratch,
stack, selector, or PC `$07` approval.
