# Scene opcode $82: bounded nested dispatch

Date: 2026-09-08. Status: authored static composition pending independent review.
This packet concerns the scene-script opcode `$82`. It does not associate that
byte with Schala's proposed action IDs, logical PC ID or extended package
selectors.

The [scene-handler census](schala_scene_handler_closure_v1.md) leaves the
`$CD2DD6` handler open at indexed jump `$CD2DE7`. The original prefix masks the
parameter, so its target domain can be bounded without claiming a global
legal script corpus. Under native M1/X0/I1 with B0/D0/DBR7E and an intact near
frame, the prefix selects exactly eight targets. Each has a balanced return
with A=0, B=0, D=0, DBR=`$7E` and M1/X0/I1. The complete conditional handler
uses zero additional stack bytes, or two bytes including its existing scene
near-call frame.

## The two reads are independent

The 20-byte prefix at `$CD2DD6..$CD2DEA` contains thirteen instructions. Its
first long-indirect parameter read supplies a count: mask the low five bits,
increment once and transfer to 16-bit X, then store that word through direct
page operand `$45`. The second long-indirect parameter read independently
supplies the dispatch index: mask the high three bits, shift right four times,
transfer to X and jump through the word table at `$CD2DEA`.

For first observed byte `p`, second observed byte `q` and incoming hidden
accumulator byte `B`, the exact recipes are:

```text
stored X word = (B << 8) | ((p & $1F) + 1)
dispatch X   = (B << 8) | ((q & $E0) >> 4)
```

Under B=0, the stored count is 1 through 32 and the dispatch index is one of
`$0000,$0002,$0004,$0006,$0008,$000A,$000C,$000E`. The source reads twice, so
the audit does not assume `p=q`. All 65,536 independent B-zero parameter pairs
are checked. Their projection digest is
`6f08ea720e2102cd30b59d7cad8f0afbfa91674f7136e131f35babf4cbf9fe1c`.
An additional 65,536 byte/B checks retain the hidden byte's effect; nonzero B
is never silently zero-extended into the eight-cell domain.

The prefix's word store addresses `$000045/$000046` under D0. Its parameter
pointer and source bytes remain unproved. The contract excludes a physical
alias that changes the live call frame or the pinned code. It does not certify
that the parameter source is ROM, remains unchanged, or has a valid lifetime.
The fixed source sequence changes neither SP nor M/X/I, D or DBR. Its final
indexed jump adds no return frame.

## Eight selected targets

| Second byte's high three bits | Pointer cell | Target | Sole return |
| --- | --- | --- | --- |
| 0 | `$CD2DEA` | `$CD2E89` | `$CD2EA1` |
| 1 | `$CD2DEC` | `$CD2E78` | `$CD2E88` |
| 2 | `$CD2DEE` | `$CD2E5E` | `$CD2E77` |
| 3 | `$CD2DF0` | `$CD2E4D` | `$CD2E5D` |
| 4 | `$CD2DF2` | `$CD2E3C` | `$CD2E4C` |
| 5 | `$CD2DF4` | `$CD2E23` | `$CD2E3B` |
| 6 | `$CD2DF6` | `$CD2E13` | `$CD2E22` |
| 7 | `$CD2DF8` | `$CD2DFA` | `$CD2E12` |

The table occupies exactly `$CD2DEA..$CD2DFA` for this masked B-zero domain.
The next address is already the selected target-7 body. All eight target
bodies lie within `$CD2DFA..$CD2EA2`; no extra cell is inferred from nearby
space. The mask bounds this particular selection independently of any claim
about globally legal scene-script parameter values.

The unchanged accepted scene walker proves each target's typed near return
and zero additional stack depth. The unchanged accepted scroll value walker
independently follows every target and establishes the returned A/B/D/DBR
values. Their decoded byte intervals and direct-call inventories must agree;
there are no direct or nested calls in these eight bodies. The value results
come from the actual full-accumulator `TDC` and return sequence under the
stated D-zero premise, not from assuming a preserving ABI.

This is an additive closure of one prior frontier under its explicit input
contract. The historical census remains 114 closed and seven open because
its source and scope are preserved. A future composed caller may consume
this result only after establishing B0/D0/DBR7E/M1/X0/I1 at this handler's
actual entry. The remaining six distinct indirect frontiers and arbitrary
scene-handler return values are separate work.

## Provenance and reproduction

The canonical 4,194,304-byte US Rev0 input is SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The exact prefix, eight selected pointers and body union have independently
checked named-span hashes in the output. Thirteen opcode/operand recipes
are verified against those canonical bytes before any composition. The
instructions' byte widths and register effects use the same pinned official
Mesen [CPU dispatcher](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h)
and [instruction implementation](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h)
as the two reused auditors.

The collector fully regenerates the accepted scene-handler and scroll-value
references, preserves the exact historical `$CD2DE7` frontier, rereads the
canonical target words and runs both unchanged target models. It checks its
own source/tests and 23 inherited source identities before and after the new
composition. No ROM mutation, emulator launch or game artifact is emitted.

The current review output is 49,712 bytes, SHA-256
`b7e3144a800512e8e6391b72c9bc733b33240e0cc0a88e57092e2e13af0c0dfc`.
The source is 12,823 bytes, SHA-256
`6339afbfe35be747e8da268c3dc8c415d761b74c05ad8de6167347572c4c2e5a`;
the 6,297-byte test source is SHA-256
`de74157d3c8db13deb7813021a3c9cf5162815fd1bef9549c62c2d5f93af2e99`.
All 31 original host tests pass. They cover independent parameter values,
every B-zero byte pair, hidden-B preservation, exact integer/boolean types,
changed target/call/return/stack contracts, mismatched value coverage,
unresolved returns and scope promotion. The fixtures contain original
metadata and short synthetic control flow; no game code is a test fixture.

```powershell
python -B tools/audit_schala_scene82_subdispatch_v1.py
python -B -m unittest discover -s tests -p test_schala_scene82_subdispatch_v1.py
```

Independent author/reviewer checks pass all 31 tests. Two separate actual
CLI processes reproduce the exact review bytes above with empty stderr;
`references/schala_scene82_subdispatch_v1.json` now contains those bytes.
The reviewer independently checked the complete prefix, separate p/q
parameter inputs, hidden-B preservation and eight unchanged target closures.
The result does not prove target memory destinations, DMA behavior, source validity,
termination, timing, a whole-NMI stack bound, a production hook/allocation,
an extended package binding or logical PC `$07` behavior.
