# Scene command $88: conditional dispatch and a nonzero hidden-B return

Date: 2026-09-08. Evidence: `verified-static` under the entry, parameter and
memory-alias premises below. Independent review and exact reference
reproduction are complete. This is a scene-stream command, unrelated to Schala action or
extended package selector namespaces.

The four reviewed subdispatch cells for scene command `$88` have balanced
control flow and exact register-width returns. They do **not** all preserve
B=$00. Ordinals 0/1/2 return A=$00FF, while ordinal 3 returns A=$FF00, hence
hidden B=$FF. The enclosing RTL and RTS leave those accumulator bytes intact.
This is a concrete conditional limit on a proposed all-handler B0 invariant;
it is not evidence that a live script uses ordinal 3 or that vanilla gameplay
is broken.

The new [auditor](../tools/audit_schala_scene88_subdispatch_v1.py) preserves
the accepted [handler census](schala_scene_handler_closure_v1.md) and
[return-value v1 packet](schala_scene_handler_values_v1.md). That earlier
packet explicitly excluded this indirect target, so its 111 proved and three
unresolved results are not contradicted. The new result must remain separate
from the later precision refinement of those 114 direct targets.

## Exact dispatch inputs and physical cells

Scene `$88` enters `$CD29DA` with the conditional native near-call ABI
M1/X0/I1, B0/D0/DBR=$7E. Its prefix loads one byte through `[$40]`, doubles
the visible accumulator in M8, transfers the full accumulator to X16, and
calls `$D1FBCE` with JSL. That wrapper executes indexed near JSR through
table `$D1FBD2`, then RTL.

For parameter byte p and incoming hidden accumulator byte B:

`X = (B << 8) | ((p << 1) & $FF)`

The parameter's high bit disappears during the eight-bit shift. The hidden
B byte survives and enters X. Table addressing then adds X to `$FBD2`, wraps
the low word, and reads the two pointer bytes in program bank `$D1`. DBR does
not select the pointer bank. The even base and index prevent a pointer word
from straddling the bank boundary, although the base-plus-index sum can wrap.
The [pinned Mesen ASL](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L626),
[TAX](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1058),
and [indexed JSR](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L446)
implement those width and pointer rules.

| Ordinal | Conditional parameter aliases | Physical cell | Target | A at both body returns |
| --- | --- | --- | --- | --- |
| 0 | `$00/$80` | `$D1FBD2` | `$D1FCF4` | `$00FF` |
| 1 | `$01/$81` | `$D1FBD4` | `$D1FC38` | `$00FF` |
| 2 | `$02/$82` | `$D1FBD6` | `$D1FC96` | `$00FF` |
| 3 | `$03/$83` | `$D1FBD8` | `$D1FBDA` | `$FF00` |

Selecting those four cells requires B0 **and** `(p & $7F) < 4`. B0 alone
allows 128 physical cells. Arbitrary B and p cover all 32,768 even pointer-word
starts in bank `$D1`. The auditor exhaustively checks all 65,536 B/p pairs;
neither complete byte input space is promoted to a legal scene domain.

The first B0 input outside the reviewed subset is p=$04. It reads the word
at `$D1FBDA`, which is the first instruction of ordinal 3's occupied body,
and would derive target `$D17CA5`. This is an arithmetic escape example,
not a runtime execution claim or free-space declaration. Exact stream
producers and parameter lifetime remain necessary for a whole-handler proof.

## Target returns and call frames

The four targets independently pass the unchanged typed-stack control-flow
walker and the unchanged v1 value walker. Each target branches on a direct
page byte, sets M16 and X8, and writes one fixed word through a bounded
source-control loop. The value proof keeps both branch edges and does not
claim iteration counts, physical writes, loop termination or timing.
Both branches load the same constant for their target, and neither changes
the accumulator after that load. They restore X16/M8 before RTS.

| Target | Two near-return sites | A low / B | Additional stack below target entry |
| --- | --- | --- | --- |
| `$D1FCF4` | `$D1FD3B`, `$D1FD7D` | `$FF / $00` | 0 |
| `$D1FC38` | `$D1FC69`, `$D1FC95` | `$FF / $00` | 0 |
| `$D1FC96` | `$D1FCC7`, `$D1FCF3` | `$FF / $00` | 0 |
| `$D1FBDA` | `$D1FC0B`, `$D1FC37` | `$00 / $FF` | 0 |

All eight returns preserve D0, DBR=$7E and M1/X0/I1 under the input and
alias premises. These are exact A/B return values, not general preservation
of the incoming accumulator or flags. The caller does not clear hidden B:
the continuation is exactly `$D1FBD1 RTL`, followed by `$CD29E2 RTS`.

The existing scene near frame contributes two bytes. JSL at `$CD29DE` adds
three bytes: caller PBR `$CD` and saved return word `$29E1`, resuming at
`$CD29E2`. Indexed JSR at `$D1FBCE` adds two bytes with saved return word
`$FBD0`, resuming at `$D1FBD1`. The selected body adds zero. Thus the conditional
maximum is **five additional bytes below scene-handler entry**, or **seven
including its existing near frame**. The stack sum uses the actual near and
long call kinds, not a uniform guessed frame size.
[JSL frame source](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L409),
[return source](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L479).

This sum assumes an ordinary writable stack whose live frames and saved
values cannot be changed by other CPU stores, DMA or asynchronous code.
It proves no physical stack ownership, complete NMI bound, interrupt timing,
or native scene execution. A subsequent scene dispatch would still need
its own B/parameter contract; the ordinal-3 result cannot be silently set to
zero by an integration planner.

## Provenance and reproduction

The audit requires the pinned canonical 4,194,304-byte US Rev0 ROM,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
It reconstructs both accepted prerequisite references byte for byte before
the new composition, and checks 29 inherited source identities plus direct
dependencies and its own source/tests before and after collection. Native
observations, ROM data and source extracts remain private; the emitted JSON
contains metadata, source spans and hashes rather than game payloads.

The named canonical source spans are:

| Span, half-open | Bytes | SHA-256 |
| --- | ---: | --- |
| `$CD29DA-$CD29E3`, prefix and scene return | 9 | `46f485f960f266f3ab0674af0d6a9075a6cef7491e187fbef5b4ff7f4796b2a6` |
| `$D1FBCE-$D1FBD2`, indexed wrapper | 4 | `f9f7c9ab15393fc9c209122951c96635e9f59cc989a9d8a6030f450b23c1ce79` |
| `$D1FBD2-$D1FBDA`, reviewed cells | 8 | `7a2ce6fdeb7921190edfaaa80997f47c2cef8716c9e075fcb398848c9e2eff76` |
| `$D1FBDA-$D1FD7E`, four-body union | 420 | `104ee301bec1645213137d5163c2ed68581adf59a90cc3cf4bc989d62e9c30c6` |

The human interpretation of Mesen semantics is pinned to commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`; five exact line spans retain their
own hashes. A hash fixes the source bytes used in review; it does not
automatically prove the interpretation.

All 33 original host tests pass. They cover the full arithmetic input space,
parameter aliases, pointer wrapping, exact numeric types, changed or missing
returns, hidden-B normalization, extra calls/stack, mismatched value coverage,
scope promotion and near/long frame composition. Test fixtures contain
original metadata, with no game instruction sequence. The first draft's
fixture omitted required inherited scope fields and raised KeyError in 22
tests; its exact source, fixture and candidate output remain preserved under
`private/test_runs/scene88_subdispatch_20260908_initial_metadata_fixture`.
The fixture was completed before review; canonical results did not change.

Independent review accepted the canonical contracts and found one reusable
metadata-boundary gap: the standalone frame composer checked B but not the
reported full A word. The canonical audit already supplied exact consistent
rows. Before reference emission, the composer gained an exact typed A-word
check and an original negative specimen for inconsistent or floating-point
values. The reviewed predecessor packet remains preserved in
`private/test_runs/scene88_subdispatch_20260908_compose_a_review`.

```powershell
python -B tools/audit_schala_scene88_subdispatch_v1.py
python -B -m unittest discover -s tests -p test_schala_scene88_subdispatch_v1.py
```

The current review output is 57,422 bytes, SHA-256
`321483c1f061847c9c24fadf1a2d43ca58d46edc7734c11c59cc990edbe03d84`.
Source: 14,759 bytes, SHA-256
`867f299b95e7362b4af6137ca19223c836780718d3715769a8623976cd598478`.
Tests: 8,209 bytes, SHA-256
`a4f536b2d48e04c7b7445108f3ca1b0340ce00f1a70147afc4505c38052ab78d`.
The independent reviewer read the complete source/tests/report and pinned
CPU semantics, passed all 33 tests, and reproduced the exact final CLI output.
The final correction changes only the source-identity entries in metadata;
all canonical contracts, arithmetic and 29 inherited identities remain exact.
Two additional root CLI processes reproduce those bytes with empty stderr,
and `references/schala_scene88_subdispatch_v1.json` now contains that exact
57,422-byte output.

No production hook, expanded allocation, high package binding, Schala action,
save change or logical PC `$07` behavior is authorized by this result.
