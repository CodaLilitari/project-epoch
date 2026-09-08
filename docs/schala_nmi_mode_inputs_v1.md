# Normal-NMI mode dispatcher: caller inputs and physical cells

Date: 2026-09-08. Status: `verified-static` within the explicit prefix
premises below; independent source review and reproduction passed. This is a separately numbered
input audit. It preserves the accepted normal-NMI v1 and direct-callee v2
artifacts, and does not close either of their indexed-dispatch frontiers.

The normal busy-zero NMI prefix establishes the following registers at its
first `$CD:0C95` call: A=`$0080`, X=`$002B`, Y=`$CC90`, D=`$0000`, DBR=`$00`,
M=1 and X-width=0. In particular, the hidden accumulator byte B is zero.
The local dispatcher then reads the mode byte at CPU `$00:007E`, shifts A
in eight-bit mode, copies the full accumulator to 16-bit X, and reads a
pointer in program bank `$CD`. There is no intervening bounds check.

This discharges the incoming-B question for that exact first call from the
normal prefix. It does not prove a global domain for the mode byte, a safe
table extension, selected mode-body returns, or game stack ownership.

## How the prefix establishes the inputs

The [read-only auditor](../tools/audit_schala_nmi_mode_inputs_v1.py) starts
from arbitrary symbolic bytes for A, X, Y, D and DBR. It checks all four
initial native M/X-width combinations. These are width cases over symbolic
register inputs, rather than four chosen concrete register seeds.

Its 40 decoded instructions cover the busy-zero path in the pinned
half-open span `$D1:E77C-$D1:E7DE`. At `$D1:E77C`, `REP #$30` establishes
16-bit A/X/Y before nine software-save bytes are pushed. `LDA #$0000`,
`TCD` and `TDC` establish D=0 and A=0; the following `SEP #$20` leaves B=0.
The normal branch requires the actual local `$007F` read to be zero.
Other busy values belong to the separately accepted busy-fast-path audit.

The block move at `$D1:E7AC` has A=`$002A`, X=`$0000`, Y=`$CC65` and
source/destination bank `$7E`. It copies 43 bytes from `$7E:0000-$7E:002A`
to `$7E:CC65-$7E:CC8F`. Its exact X16 register effects are A=`$FFFF`,
X=`$002B`, Y=`$CC90`, DBR=`$7E`. The auditor summarizes those instruction
semantics; it does not invent 43 recorded bus events or simulate their timing.

Four following word reads and stores copy color-state values and may leave
A's high byte unknown. The later `TDC` at `$D1:E7C7` clears the entire
accumulator again. After `SEP #$20`, the `PHA`/`PLB` pair publishes a zero
DBR. An eight-bit hardware-register read cannot change B. The final
`LDA #$80` therefore establishes A=`$0080` for the JSL at `$D1:E7DA`.

The model records all nonstack reads/stores and the one block-move range.
It does not solve memory aliases. Its push/pop semantics require ordinary
writable native stack RAM, no intervening corruption and no asynchronous
entry before this frontier. Native interrupt entry's I=1 is a premise;
none of this prefix's modeled status changes clears it. Enabling hardware
NMI in the prefix does not make nested NMI impossible, so the no-intervening-
entry premise remains explicit.

Conditional stack arithmetic gives four hardware-entry bytes, nine saved
software bytes and the three-byte JSL: 16 bytes below the interrupted SP
at the frontier. The temporary one-byte `PHA` is consumed before the JSL.
This is not a reserve recommendation, a physical SP measurement, a proof
that stores cannot alias saved frames, or a whole-NMI maximum. The selected
indexed JSR and everything below its target remain outside this prefix.

## The dispatcher and its aliases

Under the established M=1/X-width=0 contract, mode byte `m` and incoming
hidden byte `b` produce:

```text
X = (b << 8) | ((m << 1) & $FF)
pointer-low  = $CD0000 | (($0C83 + X) & $FFFF)
pointer-high = $CD0000 | (($0C84 + X) & $FFFF)
```

For B=0, the 256 hypothetical mode bytes select 128 distinct word cells.
Modes `$80-$FF` alias `$00-$7F` because the shift is eight-bit. In particular,
the three reviewed physical cells have six byte inputs:

| Mode bytes, under B=0 | Cell | Read target |
| --- | --- | --- |
| `$00`, `$80` | `$CD:0C83-$CD:0C84` | `$CD:09F1` |
| `$01`, `$81` | `$CD:0C85-$CD:0C86` | `$CD:088D` |
| `$02`, `$82` | `$CD:0C87-$CD:0C88` | `$CD:088D` |

These aliases follow the local instruction recipe. No high-bit mode is
asserted reachable in the game. The report enumerates all 256 hypothetical
B-zero inputs and checks all 65,536 mode/B pairs without promoting a global
producer-domain claim.

The first hypothetical successor, mode `$03` or `$83`, reads its cell from
`$CD:0C89-$CD:0C8A`. Those are the first two instructions of the occupied
field-service wrapper, `PHB` and `PHD`; as a little-endian pointer they read
as `$CD:0B8B`. The full wrapper spans `$CD:0C89-$CD:0C94` and ends in RTL.
This proves occupied successor code. It does not prove that these mode
values are legal, illegal, unreachable, unused, or available to an adapter.

The full-register recipe also matters outside the reviewed caller. A
standalone invocation with arbitrary B can address a bank-wide set of cells.
For example B=`$F3`, mode=`$BE` reads the pointer word at `$CD:FFFF` and
`$CD:0000`; the two indexed-JSR reads wrap in PBR. Caller provenance must
therefore accompany any use of the simpler `mode*2` description.

## Sources, reproduction and review history

Canonical input is the private 4 MiB US Rev0 ROM with SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Four exact named span hashes, every decoded prefix instruction, source
identities and dependency identities are recorded in the
[metadata reference](../references/schala_nmi_mode_inputs_v1.json).
No ROM, extracted payload, raw trace or emulator artifact belongs to this
source packet.

The preserved disassembly supplies useful annotations, checked against the
canonical bytes: [normal NMI prefix in bank D1](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_D1.asm#L400)
and [mode table and dispatcher in bank CD](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_CD.asm#L1495).
The existing annotation names modes 0/1/2 and their targets accurately.
This audit adds the full caller and alias premises; it does not label that
annotation a newly discovered error.

Primary CPU semantics use the same pinned Mesen revision as closure v2:
[`MVN`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L717),
[`TAX`, `TCD`, and `TDC`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1058),
and [`JSR_AbsIdxXInd`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L446).
These support the reviewer-encoded model; their hashes do not automatically
derive its semantics or substitute for independent review.

Twenty-three original host tests exercise all mode/B pairs, high-bit aliases,
word wrap, all initial M/X combinations, symbolic input convergence,
MVN's count-plus-one and distinct source/destination banks, hidden-B
retention, and fail-closed width/status/source/branch/budget boundaries.
The first toy-test run had two fixture errors: removing TDC also left DBR
unknown before an absolute read, and a branch-uncertainty specimen used an
absolute read before DBR was initialized. Both were corrected to explicit
long-address toy reads, preserving the intended unknown-B/unknown-branch
tests. No canonical model change or accepted observation was needed.
Independent review then found two generalized-model boundaries outside the
canonical path: index loads, TCD and PLB needed their Z-flag effects for a
later hypothetical branch, and a second `$007F` increment could reuse the
one-time busy premise. The model now updates those flags and refuses a
repeated busy read/increment or intervening alias store. Four additional
tests preserve these failures. The canonical 40-instruction path's register
result is unchanged; these repairs strengthen the audit tool before release.
The independent reviewer passed all 23 tests and reproduced the final
138,037-byte reference through both an imported audit and an actual CLI
process, SHA-256
`dc715f6726e482a00e649d15252b5ca42f933f82198d8520c78d7867f3932530`.

```powershell
python -B tools/audit_schala_nmi_mode_inputs_v1.py
python -B -m unittest discover -s tests -p test_schala_nmi_mode_inputs_v1.py -v
```

The next gate is a bounded mode-producer census and selected-target
control/return/alias analysis, joined to the separately tracked scene-input
and remaining direct-callee obligations. The production hook and allocation
catalogs, high package bindings and logical PC `$07` integration remain empty.
