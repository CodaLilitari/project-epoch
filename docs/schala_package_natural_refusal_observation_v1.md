# Natural queued-Cure refusal observation v1

Date: 2026-09-08. Status: `verified-runtime`, two byte-identical source-matched
observations after independent review. Earlier discovery and hardening runs
remain explicitly historical. This is not a production installation approval.

A normal queued Tech can fail before effect preparation. In the observed
route, Marle confirms Cure for living Lucca, an already pending Lavos attack
kills Lucca, and the queued Cure subsequently fails the selected-target check.
The game takes its shared finalizer and releases Marle's command. It spends no
MP and invokes neither the effect-preparation routine nor the package resolver
inside that rejected transaction. Marle later returns to the menu's ready list.

This supplies a concrete vanilla failure lifecycle for integration design.
It does not install or prove a high-selector cancellation adapter. The existing
[successful transaction observation](schala_package_transaction_observation_v1.md)
still establishes that cancellation delayed until the resolver occurs after
effect preparation and MP deduction. A future helper preflight must be placed
at an independently approved boundary and preserve the whole surrounding
transaction contract.

## Setup, input and provenance

The observer uses the same fixed canonical US Rev0 ROM, recovered pre-Lavos
SRAM and accepted Lavos battle-ready state as the successful observation:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Canonical clean ROM | 4,194,304 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| Recovered SRAM | 8,192 | `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203` |
| Accepted battle-ready state | 261,614 | `d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b` |

The [checkpoint acceptance reference](../references/mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json)
records its acquisition. Its historical collector copied recovered SRAM into
emulated SRAM, then used controller input to reach the battle. The checkpoint
launcher normalized the non-authoritative preview framebuffer and checked fresh
reloads. This is a prepared diagnostic checkpoint; its provenance does not
establish an unassisted playthrough. The present observer loads that exact state
and supplies only the fixed joypad sequence below.

The trace field `frame` counts input-polled callbacks relative to readiness;
it is not the PPU frame counter. Every record also contains the full
`memoryManager.masterClock`, CPU cycle count, hardware frame/raster fields and
the generic low-32-bit clock. The validator checks their monotonicity and the
low-32-bit relation, including a synthetic rollover case.

| Button | Inclusive input-poll intervals |
| --- | --- |
| Right | 2180-2183 |
| Down | 2200-2203, 2340-2343, 2360-2363, 2380-2383, 2420-2423, 2430-2433 |
| Up | 2240-2319 |
| A | 2220-2223, 2400-2403, 2440-2443 |

All other buttons remain false; the observer stops at poll 4000. There is no
arbitrary input, checkpoint, collector, CPU edit, memory edit or helper option.
The isolated Mesen 2.1.1 launcher pins and preserves original inputs, copies
runtime files into a private profile, uses disposable matching ROM/state/SRAM
filenames, and checks source and staged hashes again after execution. Exact
source archives and a prelaunch receipt are written before the native process
starts, so even rejected runs retain their actual revision.

## The action, failure and return

The source checks are separately reproducible through the
[natural-refusal static packet](../references/package_natural_refusal_boundaries_v1.json).
It pins seven new canonical spans and 35 selected instruction assertions,
while reusing the completed cancellation audit's preparation/finalizer spans.
Instruction meanings are reviewed assertions checked against canonical bytes;
a span hash alone does not derive semantics.

| Boundary | CPU address | Observed poll | Meaning |
| --- | --- | ---: | --- |
| Selected living target snapshot | Input callback | 2435 | Marle, Cure `$0C`, target slot 2; Lucca has 187 HP and no death bit |
| Menu commit | `$C1161A` | 2443 | Confirmation while Lucca remains alive |
| Queued fields readback | `$C11713` | 2443 | Six actual byte stores construct the selected row |
| First HP subtraction | `$C1EC99-$C1ECA3` | 2524 | Lucca's 187 HP minus pending damage 192 yields `$FFFB` |
| Death status and zero clamp | `$C1ED04-$C1ED12` | 2524 | Actual death-bit store and two actual zero-HP bytes, with readbacks |
| Queued Tech entry | `$C1BB49` | 2560 | Same Cure row and target 2, now dead |
| Selected-target death branch | `$C1C367/$C1C36E` | 2560 | X `$0100` selects Lucca's battle record; death bit takes the failure JMP |
| Failure setter and return | `$C1C72B/$C1BB8B` | 2560 | `$AF23` changes from 0 to 1 through its actual store |
| Shared finalizer | `$C1BDB3` | 2560 | One resolved participant, Marle, followed by two absent positions |
| Queue release and actual caller | `$C1BCF8/$C185EA` | 2561 | Selected row released and actual near return observed |
| Ready-list insertion/readback | `$C11B80/$C11B83` | 2773 | Marle reenters slot 1 of the menu's ready list |

The menu stores target 2 and action `$0C` into the second seven-byte queue
record, `$7E93F5-$7E93FB`. Its complete fields read back as
`41 20 01 02 00 FF 0C` after menu construction and
`01 20 01 02 00 FF 0C` at queued execution. Queue byte `+2` is the observed
copy of `$9615`; this report does not assign an additional semantic name to
that field. The prelude ledger accounts for the actual ready-flag transition
between these two states.

The selected HP arithmetic is supported by the canonical SEC/SBC/STA sequence,
pre-execution operand snapshots, the accumulator at the store, both actual byte
writes, and the following readback. This is not a separate CPU operand-read
callback proof. The processor's decimal flag must be clear in addition to
direct-page D being zero; those are different CPU properties. The status and
clamp witnesses preserve the same enemy-result near frame, SP `$06E3`, with
return prefix `$AC87/$AC5C`. These checks establish this one negative result
and its zero clamp, not all healing, overflow, death or reward behavior.

The rejected Cure enters with SP `$06EA`, D `$0000`, DBR `$7E`, M=1 and X=0.
Its outer saved return word is `$85E9`. Target validation has the expected
additional `$BB8A` near frame, and the shared finalizer has `$BC5C`. The
observed actual return reaches `$C185EA`, removes exactly two bytes, restores
SP `$06EC`, and preserves A/X/Y/D/DBR/P across that RTS. All 16 sampled stack
bytes agree at the corresponding outer boundaries. This is stack-frame
continuity, not a global stack low-water claim.

Participant IDs at the initial target-validation entry still contain earlier
work. `Tech_GetTargetData` resolves the Cure participant before the selected
target check. The validator therefore requires `[1, FF, FF]` from that resolved
boundary onward; it does not mislabel earlier temporary data as the Cure's
participant set.

## Memory and cleanup contract

The prelude ledger starts at the declared living-target snapshot and ends at
the queued entry. It covers all 21 queue bytes and each of the three party
slots' HP/max-HP/MP/max-MP bytes plus current-status byte 0. Every sampled
change must be preceded by its recorded actual byte write.

The separate transaction ledger covers the selected invocation from `$C1BB49`
through the actual `$C185EA` caller snapshot. Its ranges are all 21 queue bytes,
48 pending-result bytes, the HP/max-HP/MP/max-MP fields of all 11 battle records,
11 ATB rates, 11 ATB status bytes, the three command latches, the three `$9F22`
rate mirrors, `$AF22/$AF23`, and the `$9876/$5D9B` completion latches.
It reconciles each snapshot against the preceding actual write, including the
final caller snapshot. These are declared watched ranges, not full WRAM.

The transaction contains exactly 22 recorded writes in these ranges. Each has
its required address, value, post-store callback PC, width/bank/direct-page
context and matching call frame. The sequence includes the initial `$AF23`
clear, its failure store, the shared finalizer's queue/latch/rate work, and
queue release. Marle's saved ATB rate is restored to 84, both observed mirrors
agree, her command latch ends zero, her ATB status ends 1 and `$AF22` ends zero.
The other two queue records remain unchanged. Pending-result bytes, all 11
sampled HP/MP words, and party MP `[93, 97, 99]` remain unchanged during this
rejected invocation.

The absence claim is bounded to that exact invocation: there is no effect
preparation, MP deduction, animation/result wrapper, package resolver or result
application dispatch in it. Earlier Lavos result work belongs to the explicitly
separate prelude. Later menu readiness is likewise a separate witness: an actual
`STA $A6D9,X`, X=1/A=1, is followed immediately by its `$C11B83` readback.
This proves ready-list insertion after refusal; the replay executes no second
player command.

## Preserved exploration and limitations

The initial root-owned Life 2 attempt selected Life 2 against a living party;
the menu did not queue a Tech. It remains useful evidence about menu validation,
and is not a transaction refusal. A separate idle replay located Lucca's natural
death window. The first Cure attempt selected Crono with one Down press and
successfully healed him after Lucca died. The second added one more Down, kept
the same confirmation timing, and reached the dead-target failure. No blind
search or artificial game-state mutation was used to obtain the route.

Those discovery runs retain their original source archives. The first idle
revision ran to poll 6000; the later exploratory source has different fixed
routes and a poll-4000 stop. Historical source identities must be restored
before reproducing an older run; a current command alone is not claimed to
reproduce a historical source revision.

The first enriched observation was rejected by an over-early participant
assertion; its raw trace and prelaunch source archive remain preserved. Later
hardening added the readiness readback, binary-arithmetic requirement and
explicit menu/enemy-result frame continuity. Independent review passed the
observer, validator, 41 original synthetic/adversarial tests and the retained
hardening trace. A final launcher improvement added explicit archive hashes
to both launch and completion receipts and rechecked those archives after
native execution; it received separate review before the final pair.

The old `$A0D1` annotation's word "busy" is refined here to its status-derived
Lock mirror. This clarification does not assert a new data-mapping correction
without a contradictory source claim. The existing correction to the shared
`$C1BDB3` finalizer remains applicable: successful and unsuccessful paths share
it, so its name alone cannot prove cancellation or an MP refund.

The observed refusal neither implements Schala effects nor binds a high package
selector. Hook placement, helper preflight inputs, interrupted game execution,
production allocations, auxiliary readers and logical playable PC `$07` remain
separate work.

## Final pair and reproduction

Both final runs contain 150 records and reproduce the same 746,878-byte trace:

`63f94fff2b81292b593073e1197b7a8b8778cf6f4b217e2caa02adb0d61efd15`

The identical 2,880-byte prelaunch receipt has SHA-256:

`8b4f33c4c5d77a78904867ca9c84f0b78f608681706c62125f73cc6f36762d50`

Each completed manifest is 5,888 bytes. Final1 has SHA-256
`de617a852ac43de156c6895a987ef72494afdb886bc9b243dca27aee4070da2f`;
final2 has SHA-256
`229dbaa3543f4d4b97706514a75ca84d85f36b4798aff3318add420cd5f896c1`.
Their only differing field is the per-run screenshot identity map. The exact
CPU/data-flow trace, summarized findings, and all input/source/archive hashes
agree. Both screenshot sets remain preserved and hash-checked; no claim of
identical rendered pixels or an established cause of image variance is made.

The [read-only metadata collector](../tools/collect_package_natural_refusal_evidence_v1.py)
revalidates both traces, summaries, current sources, archived sources, runtime
files, fixed original and staged inputs, exact save filenames and screenshot
inventories. It also reproduces the separate static boundary packet and checks
all six historical exploratory source archives. It creates no image, emulator
process, directory or output file. The
[metadata reference](../references/package_natural_refusal_observation_v1.json)
records the complete source, checkpoint, runtime, run and historical identities.

The selected transaction takes 166,954 emulated master clocks from queued entry
to actual caller return, approximately 7.77 milliseconds at the recorded clock
rate. That is an emulated duration, not an emulator wall-time benchmark or an
interrupt-free claim. The return precedes the separately observed ready-list
insertion at poll 2773.

```powershell
python -B -m unittest discover -s tests -p test_package_natural_refusal_observation_v1.py
python -B tools/run_package_natural_refusal_observation_v1.py --output-dir private/test_runs/package_natural_refusal_NEW_UNIQUE
python -B tools/collect_package_natural_refusal_evidence_v1.py
```

The metadata serialization is `json.dumps(value, indent=2)` encoded as UTF-8
with LF newlines and exactly one trailing newline. Running the collector and
serializing that result reproduces the checked-in reference byte for byte.
