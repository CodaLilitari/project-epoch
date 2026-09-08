# Scene 8B successful-return dispatch inputs, v1

Date: 2026-09-08. Evidence: **verified-static**, conditional on the source,
memory and execution premises below. No native execution, game-file write,
ROM hook, allocation or production binding is performed.

Scene command `$8B`, whose target is `$CD2FB7`, has a useful conditional input
contract at the indirect jump `$CD319A`. **Its dispatch path receives B=0
from the preceding helper's successful return.** The other helper return can
leave B unknown, but the caller exits on that path. This proof does not
assume incoming B zero for the whole handler.

Six adjacent pointer cells are decoded. Two selected targets have complete
conditional stack/value contracts using unchanged accepted models; four
still reach the unresolved `$CEE7CC` copy-pointer frontier. The legal script
domain, input lifetime, memory aliases, full handler and whole NMI remain
open. The six cells are not an unconditional dispatch-domain bound.

The [new auditor](../tools/audit_schala_scene8b_dispatch_inputs_v1.py) and
[original tests](../tests/test_schala_scene8b_dispatch_inputs_v1.py) preserve
the accepted parent census and value models. Scene-command `$8B` is a
separate namespace from Schala actions and high package selectors.

## Exact helper-return and caller-branch relation

At `$CD2FB7`, the handler reads one script byte through `[$40]`, then
tail-jumps to `$CD3189`. Denote that byte q. The caller stores q in byte
`$7ECAAA`, calls `$CD31AA`, and executes BCC at `$CD318F` immediately after
the near return. Native entry is M8/X16/I1, D=0 and DBR=`$7E`; incoming B is
left unknown in the value proof.

The complete direct-call walker closes the helper body `$CD31AA-$CD31FE`
with 46 instruction contexts, no callees, no additional stack bytes, and
exactly two near-return sites. The unchanged value model, explicitly run
with unknown entry B, gives these return states:

| Return | Sole immediate predecessor | Return carry | A.low / B | Caller outcome |
| --- | --- | --- | --- | --- |
| `$CD31B6` RTS | `$CD31B5` CLC | Clear | Unknown / unknown | BCC to `$CD319D`, then RTS |
| `$CD31FD` RTS | `$CD31FC` SEC | Set | `$7E` / zero | BCC falls through to `$CD3191` |

Both returns preserve D=0, DBR=`$7E` and the M8/X16/I1 width/interrupt-mask
contract. The nonzero path passes a TDC under D zero and subsequently uses
8-bit accumulator operations, leaving hidden B zero. It restores X16 before
its final SEC/RTS. The zero path does not justify a B-zero claim; its unknown
value is retained.

The new local CFG audit follows both branch edges and checks every decoded
instruction context against the accepted control/value models. It proves
that each RTS has only its named CLC or SEC as an immediate predecessor.
A direct jump into the RTS, an alternative flag writer, a changing decode
width, an extra call, or an unexpected return refuses. This prevents using
an annotation or a merely adjacent flag instruction as path evidence.

This is a local source-derived flag fact, not a general carry model. Mesen's
pinned implementation shows CLC/SEC changing carry, RTS leaving processor
status unrestored, and BCC testing carry clear. The exact caller bytes bind
that fact to this branch. No asynchronous flag/register change between the
exit instruction and caller BCC is allowed by the contract.
[Flag instructions](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L231),
[RTS semantics](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L491),
[BCC semantics](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L163)

## The two distinct input indices

There are two stages, with different hidden-B evidence.

Before the successful return, the helper reads `$CAAA` in M8 and transfers
the whole accumulator into X16. Its initial CAA4-indexed input can therefore
use `X = (incoming B << 8) | q`. That possible input address, its validity,
aliasing and lifetime are unresolved. The later B-zero result must not be
projected backward to rewrite this earlier source index.

On the dispatch path, B is now proved zero. The caller reloads q from byte
`$7ECAAA`, so TAX gives X=q. It then reads a second byte, denoted z, at:

```text
selector source = $7ECAD1 + q
```

With q spanning all byte values, those possible byte addresses span
`$7ECAD1-$7ECBD0`. This is an address calculation; no claim is made that all
256 bytes are a legal selector table or belong to one script's lifetime.
The q reload, z read, script pointer and the earlier helper input must remain
stable under the explicit no-intervening-alias premise.

The M8 ASL at `$CD3198` changes only low A. TAX at `$CD3199` uses X16. Since
the successful helper established B zero, the exact final index is:

```text
dispatch X = 2 * (z & $7F)
pointer low byte  = $CD319E + dispatch X
pointer high byte = pointer low byte + 1
```

The high bit of **q is preserved** in the selector-source index. The high
bit of **z is discarded** from the final dispatch index. These are different
operations over different bytes, not interchangeable parameter aliases.
Mesen's pinned M8 accumulator shift, X-width transfer and program-bank
indirect-JMP implementation support the calculation.
[ASL A](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L626),
[TAX](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1058),
[indexed indirect JMP](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L434)

All 65,536 q/z pairs are checked. They produce 256 possible selector-source
bytes and 128 distinct physical pointer-word starts, from `$CD319E` through
`$CD329C`. The last high byte is `$CD329D`; this conditional B-zero geometry
does not approach the program-bank boundary. The ordered algebra matrix has
SHA-256 `19290df0f661ba5c69095e12f0adc84b3f6063a1115fabf57115d0640867fda0`.
Its serialization is recorded in the metadata.

## Six reviewed cells, two closed targets, four open frontiers

The six adjacent words at `$CD319E-$CD31AA` select the following targets:

| Cell | Arithmetic z aliases | Target | Conditional control/value result |
| ---: | --- | --- | --- |
| 0 | `$00/$80` | `$CD33B5` | Open at `$CEE7CC` |
| 1 | `$01/$81` | `$CD33BB` | Open at `$CEE7CC` |
| 2 | `$02/$82` | `$CD33C1` | Open at `$CEE7CC` |
| 3 | `$03/$83` | `$CD33C7` | Closed; returns at `$CD347C` |
| 4 | `$04/$84` | `$CD33CD` | Open at `$CEE7CC` |
| 5 | `$05/$85` | `$CD33D3` | Closed; returns at `$CD347C` |

The cell restriction is `(z & $7F) < 6`. It is a premise for these selected
contracts, not a proved restriction of a legal producer. At z=`$06` or
`$86`, the index already selects `$CD31AA/$CD31AB`, which are the first two
bytes of the helper's LDA CAAA instruction. Interpreted as a pointer, they
would select `$CDAAAD`. The auditor retains that occupied-code overlap and
does not follow the escaped target or claim the input is reachable.

For `$CD33C7` and `$CD33D3`, the unchanged models traverse 148 and 154
instruction contexts respectively. Every decoded context, source interval,
callee inventory and exact returned value must agree. Both have two
additional bytes below target entry, share the original handler near frame,
and return A/B=0, D=0, DBR=`$7E`, M8/X16/I1. The prefix's earlier helper call
also costs two bytes, but it has already returned before target dispatch.
The composed additional depth is therefore **max(2,2)=2**, with four bytes
counted including the original handler near frame. The indirect JMP adds
no new call frame.

The other four retain their complete open control contracts, including the
nine counted bytes at `$CEE7CC` and their different active return chains.
The separately proved B5/B6 copy-pointer relation is **not applied here**.
That relation was derived for a particular producer with CAAA zero and
particular stable byte inputs. These paths have q-selected data, preceding
emitters and multiple upstream producer routines. Reusing the final jump
address alone would not establish their pointer domain.

These are conditional returning-path and stack contracts. The value models
do not prove loop termination, effective memory addresses, WRAM-port
ownership, graphics results, DMA/HDMA effects, physical stack ownership or
asynchronous safety. Nonstack CPU, DMA or WRAM-port writes must not alias
the live frames or canonical code. None of those premises becomes evidence
of a safe production hook.

## Provenance and reproducibility

The canonical input remains the headerless 4,194,304-byte US Rev0 ROM,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Five named source spans pin the script-read entry, caller/index prefix,
six pointer cells, complete helper and six target entry stubs. The actual
ROM drives the decoding; private disassembly names serve only as navigation.

The collector regenerates the accepted scene-values v2 reference exactly,
which in turn reproduces the earlier value and scene-handler references.
It retains the original `$CD319A` parent frontier. The new source/tests,
three immediate prerequisites and 32 inherited source identities are checked
before and after collection. Six reviewed CPU semantic spans are recorded
under the full pinned Mesen instruction-source identity, commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`, SHA-256
`9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`.
The spans pin reviewed source semantics; the hashes do not infer semantics
automatically. No extracted game-data payload or native trace is tracked.

```powershell
python -B -m unittest discover -s tests -p test_schala_scene8b_dispatch_inputs_v1.py -v
python -B tools/audit_schala_scene8b_dispatch_inputs_v1.py
```

All 35 original host tests pass. They cover q/z alias distinctions and
boundaries, strict byte types, complete exit/predecessor ownership, direct
entry into an RTS, wrong flag opcode or return width, unknown failure B,
missing/extra returned states, exact source-context agreement, strict scalar
types, caller-branch changes, selected target frames and scope preservation.
The helper and target instruction specimens are authored for the tests and
do not contain extracted canonical bodies.

Two fresh actual CLI processes emit identical **124,619-byte** UTF-8/LF
metadata, SHA-256
`f3cb6cef7e04c2dd101eb69ee4ccb212443ea3ea91e248f07ed2a586155609bf`,
with empty stderr and unchanged source/test identities. Source: 17,345 bytes,
SHA-256 `d71ceb87f2840ce59f7056ccecb904797de326e28ef9261e12e16fcbf0a607c6`.
Tests: 7,461 bytes, SHA-256
`1424f403932f3d5a3f106deac480c628c7f10957944d2b3398d7c2ed1f44622e`.
Root and independent peer reviews both accepted this conditional scope.
Each reviewer read the full source, tests, report and canonical helper, ran
all 35 tests, and reproduced the exact CLI metadata above. The accepted
reference is `references/schala_scene8b_dispatch_inputs_v1.json`; its bytes
and hash match both reviewed reproductions. No native run was added.

The next useful proof must establish q/z producer bounds and lifetime or
derive the actual pointer domains of the four remaining target paths. This
packet does not close the whole scene `$8B` handler or permit a game hook,
expanded allocation, high-selector binding or eighth playable character.
