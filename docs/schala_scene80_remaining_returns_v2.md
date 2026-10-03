# Scene `$80`: the two remaining conditional return contracts, v2

Authored from an unfinished 2026-09-08 draft; resumed and validated
2026-10-03. Evidence level: `verified-static`. Root independently reviewed
the source and original tests, passed all 38 tests, and reproduced identical
metadata in two actual CLI processes. The reference is accepted in this
explicitly conditional scope.

The two explicit first-29 frontiers in
[scene `$80` v1](schala_scene80_subdispatch_v1.md) now have separate,
conditional return proofs. Physical index 9 reaches two decreasing block
copies and returns with B0/D0/DBR `$7E`; index 13 calls a routine that
temporarily sets direct page D to `$0A00`, restores its saved D0 on both
exits, and returns with the same B0/D0/DBR `$7E` contract. Together with
v1's 27 preserved targets, all 29 selected targets have conditional
M1/X0/I1, B0/D0/DBR `$7E` returns. Their largest additional stack use is
seven bytes below scene entry, nine including its existing near frame.

These 29 physical pointer words still describe a topology boundary. The
game's legal parameter domain, effective memory addresses, stack ownership,
asynchronous interference, and full scene/NMI bounds remain unresolved.
The 128-cell hypothetical v1 census is preserved without extension.
Scene opcode `$80` is unrelated to a Schala action or package selector.

## Narrow model changes and preserved evidence

The separately derived typed decoder adds exactly opcode `$44`, `MVP`
(three bytes), and opcode `$75`, `ADC dp,X` (two bytes). Its control/stack
algorithm is unchanged. The syntactic write inventory learns that an `MVP`
is a block transfer with unknown write-count width, just as for the already
supported `MVN`. There is no claim that this inventory resolves addresses.

The inherited value walker adds `MVP` to the same native M16/X16 completion
rule used for `MVN`: completed A is `$FFFF` and DBR is the first encoded
operand. Arithmetic still conservatively forgets the active A width. Thus
M8 `ADC dp,X` can change A.low and flags while retaining B; a word ADC
does not retain a known B. Decimal arithmetic is not evaluated and does
not create a hidden-B exception to the active-width rule.

The generic value walker deliberately retains its explicit refusal of
`PHD`/`PLD`. The `$D1F108` routine needs a separate bounded value projection
because its D is **not** invariantly zero. Reusing the old invariant without
modeling that change would be a false proof.

The auditor regenerates the complete accepted scene80-v1 reference exactly.
It also reruns the derived typed decoder against every one of the 114
previously closed direct scene targets, requiring each complete control
contract to remain equal. The accepted v1 source, tests, reference, its
secondary census, and inherited source identities are unchanged. The new
collector does not overwrite any historical packet or run an emulator.

## Index 9: two completed MVP operations and the later B reset

Under native M1/X0/I1 near entry with B0/D0/DBR `$7E`, the target
`$CD2BFC` changes A to sixteen-bit width. Its immediate setup supplies:

| MVP site | Initial A | Initial X | Initial Y | Source/destination bank | Transfer count | Completed X/Y |
|---|---:|---:|---:|---|---:|---|
| `$CD2C07` | `$01AF` | `$08BF` | `$08FF` | `$7E` / `$7E` | 432 bytes | `$070F` / `$074F` |
| `$CD2C13` | `$001A` | `$091B` | `$091F` | `$7E` / `$7E` | 27 bytes | `$0900` / `$0904` |

For a completed native M16/X16 MVP with initial word `a`, the local
arithmetic is `count=a+1`, `A=$FFFF`, `X=(X-count)&$FFFF`, and
`Y=(Y-count)&$FFFF`. The first encoded bank operand becomes DBR. This
models the completed instruction's register effect, including the
65536-transfer endpoint when initial A is `$FFFF`. It does not certify
the copy's memory ownership, copied values, interrupt behavior or duration.

The two block copies leave B at `$FF`. The subsequent `TDC` at `$CD2C2A`
copies full D0 into A, and a second `TDC` at `$CD2C2D` also occurs after
`SEP #$20`. From there, byte arithmetic and loads retain B0. The typed
walk closes all 58 instruction contexts at the sole `RTS`, `$CD2C7E`.
The independent value projection owns the identical decoded contexts,
intervals, direct calls, mnemonic inventory and returned width/site.
No software stack bytes are added; the inherited two-byte near frame
remains the whole conditional counted stack for this target.

The existing upstream annotation supplies the instruction addresses and
immediate setup, which are independently checked against the canonical
ROM spans. [Pinned `bank_CD.asm`, lines 3677–3738](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_CD.asm#L3677)
is cited as provenance, not as independent runtime evidence.

## Index 13: save D0, run with D `$0A00`, restore D0

The selected target at `$CD2B64` consists of a direct long call to
`$D1F108` followed by `RTS` at `$CD2B68`. The long callee has a separate
76-context value projection with a typed software stack and explicit D:

| Site | Reviewed operation | D and live software bytes |
|---|---|---|
| `$D1F108` | `PHD` | Saves the original word D0 above the existing three-byte long frame. |
| `$D1F109` | Word `LDX #$0A00` | Establishes the complete temporary word independently of entry X. |
| `$D1F10C` | Word `PHX` | Adds two temporary bytes; local peak is four above the long frame. |
| `$D1F10D` | `PLD` | Consumes those temporary X bytes and sets D to `$0A00`; original D remains saved. |
| `$D1F10E` | `SEP #$10` | Uses byte indices during the body; M remains byte width and B remains zero. |
| `$D1F161` or `$D1F1AC` | `PLD` | Consumes the original saved word and restores D0. |
| `$D1F162` or `$D1F1AD` | `REP #$10` | Restores sixteen-bit index width, without claiming the original X/Y values. |
| `$D1F164` or `$D1F1AF` | `RTL` | Requires exactly the original long frame, D0, B0, DBR `$7E`, M1/X0/I1. |

All decoded instructions are assigned an explicit effect in this bounded
routine. Loads, stores and arithmetic run with temporary D and byte A;
their memory values and flags remain unknown. Both successors of every
conditional branch are retained. The model owns all decoded bytes and
rejects overlaps, unreviewed effects, control outside the exact source
extent, consumption of a return frame, an unknown saved word, a width
change other than the declared index changes, or a return with D unrestored.
The two return paths have identical D/DBR/B and width contracts.

This projection agrees with the independent typed walker on all 76 decoded
contexts, complete byte intervals, mnemonic counts, direct-call list and
return-site/width set. The typed full caller walk owns 78 contexts. Stack
composition is explicit: existing scene near frame 2 + nested long call 3
+ the callee's peak software words 4 = **9 counted bytes**, or **7 added
below scene entry**. The dispatcher is a jump and adds no frame.

This proves conditional preservation of D, B and DBR at return. It does not
prove preservation of the original X/Y values, A.low, memory values, flags
other than M/X/I, termination of data-dependent loops, or absence of an
alias that overwrites those saved bytes.

## Evidence provenance and reproducibility

The only canonical game input is the private, unchanged US Rev0 image,
4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The collector pins seven selected source spans, including the complete
MVP setup/suffix, the long-call wrapper, the complete temporary-D routine,
its setup, and both identical-width return suffixes. It emits addresses,
hashes and original analysis; no extracted game bytes are an artifact.

The exact accepted scene80-v1 reference is 424,188 bytes, SHA-256
`98ef60b958f997bc125d2550ff90c9cd6948a9f7b269be7fc0194790cfbece2f`.
It must reproduce before the new proof is collected. The 32 transitive
source/reference identities, all direct pins and both new source/test
files are checked before and after collection. No accepted v1 claim was
wrong: its explicit unsupported-opcode frontiers correctly represented the
scope of its unchanged models. This is an additive proof, not a correction
that rewrites earlier evidence.

The CPU semantics are reviewer-encoded and supported by immutable Mesen
source, commit `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. The opcode
dispatch binds `$44` to block-move addressing/MVP and `$75` to direct-page
indexed-X addressing/ADC. [Pinned `SnesCpu.Shared.h`, opcode dispatch](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L109)
provides those bindings. [MVP](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L744)
establishes decrement direction, full-A completion and operand bank order.
[ADC and Add8](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L4)
establish active-width arithmetic and preserved high A for byte arithmetic.
[PHD/PLD/PHX](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L801)
and [TDC](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1078)
support the explicit word saves, pulls and full-D transfer. A source hash
identifies reviewed code; it does not derive these semantics automatically.

Run from the project root:

```powershell
python -B -m unittest discover -s tests -p test_schala_scene80_remaining_returns_v2.py
python -B tools/audit_schala_scene80_remaining_returns_v2.py
```

The CLI produces UTF-8 indented JSON with LF and one trailing newline on
binary stdout. It writes no file. The independently accepted reference is
`references/schala_scene80_remaining_returns_v2.json`. Tests use original executable
miniatures and fabricated metadata, including a deliberately different
temporary-D body and branch topology. They cover every word MVP count,
wraparound, operand bank order, B effects, stack/width/return mutations,
unmodeled effects, and attempts to turn the conditional evidence into a
global or physical-memory approval.

Author verification on 2026-10-03 passed all **38 tests**. Two independent
CLI processes emitted identical **59,258-byte** proposed metadata, SHA-256
`9f24a7fb84c1534363c4d0384d835e41cdf03d62e4ca303f3502519a1d781338`.
The author initially retained those bytes without emitting a reference.
Root then independently read the source, report and original tests, passed
the same 38 tests, and reproduced those exact bytes in two additional CLI
processes. That reviewed output is now the separately named reference;
the accepted v1 packet remains unchanged.

The next integration obligation is still a caller and input-domain proof,
followed by physical memory/interrupt ownership. None of these results
installs a game hook, allocation, high selector, Schala command, sprite,
record or playable PC `$07`.
