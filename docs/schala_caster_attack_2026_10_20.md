# Schala stationary casting Attack checkpoint — October 20

The new private candidate implements a stationary casting route for Schala's
normal and critical Attacks and adds the refined forward casting poses. Its
source, guarded construction, twelve native battle cases and flying-Epoch
scene regression now pass. Coda inspected the rendered side/front poses and
the Epoch milestone captures; this is a tested private candidate.

This remains a bounded implementation for logical PC07 in the third active
party position, slot 2. It does not finish Project Epoch or establish support
in every party position.

## Source changes

Five qualified helpers implement the route. The approach helper preserves
the original target-facing calculation, then clears the approach flag so
both near and far Attacks bypass pathfinding. The
normal and defensive path consumers select ranged package `$04`; critical
selects `$10`. All require Attack type `$01`, actor slot 2, roster PC07 and the
exact installed graphics/assembly provider. Calls that fail those predicates
retain the current parent's original fallback behavior.

The selectors publish an explicitly inspected effect configuration with
projectile, ring and flash artwork. The launch-sound consumer uses sound
`$4D` in the existing audio namespace and retains actor-position panning.
The equipped weapon, action `$75`, damage formula, pending-result processing
and queue machinery are unchanged. Matching damage outcomes and complete
native action cleanup are recorded separately below.

There is **no impact-sound hook**. The selected ranged roots and their target
subscript do not invoke command `$7D`, so the proposed override was removed.
Static artwork inspection also does not establish native colors, timing or
auditory acceptance.

Forward preparation and release append as frames 30 and 31. Existing frames
0–29 and all 112 prior graphics tiles remain byte-identical; the new totals
are 32 frames and 122 tiles. Selector `$31` uses the new forward pair, `$32`
uses the forward release, and `$09` holds the appropriate release for forward,
left and right. Back-facing art, existing movement/recoil/KO sequences, shared
timing and the game's facing choice remain unchanged.

## Guarded build and focused checks

The candidate is `private/test_runs/pc07_caster_attack_v1/diagnostic.sfc`,
SHA-256 `9f678764d05f2f16e49c5a7cafe03ee6f192330322988918ff8bca2d1b2740f0`.
Its immediate parent and detailed source identities are recorded in the
private build receipt; unchanged historical-chain hashes are not repeated.

Both shared intent and complete-diff guards pass before image emission:
**953 changed bytes in 20 declared spans**, with exact inverse restoration of
the parent. A placement census retains 143 accepted occupied records and the
entire earlier KO-helper reservation. The new five-helper allocation is
`$490100..490380`; fill bytes alone are not treated as ownership evidence.

All thirteen protected NPC spans, the shared palette, world-map bytes, old
art prefixes and previous KO helpers are preserved. Canonical effect, weapon
and sound tables are unchanged. The stream audit checks all 1,024 directional
entrypoints, including the boundaries around selector `$09`.

Eight focused codec/guard tests pass. Asar matches the independently encoded
five helpers, and a separate opcode executor passes 20,189 synthetic cases
covering qualifiers, both branch outcomes, CPU-state preservation, exact
writes, balanced stack use and the inclusive near-distance boundary. These
checks do not prove game execution, interrupt safety or physical stack
ownership. No historical builder or validation chain was replayed.

Reproduce into a fresh private directory with the pinned local inputs:

```powershell
python -B tools/build_pc07_caster_attack_v1.py --output private/test_runs/pc07_caster_attack_<fresh-name>
python -B tests/test_pc07_caster_attack_write_contract_v1.py
```

Source: [caster helpers](../asm/pc07_caster_attack_v1.asm),
[builder](../tools/build_pc07_caster_attack_v1.py),
[write contract](../tools/pc07_caster_attack_write_contract_v1.py) and
[focused tests](../tests/test_pc07_caster_attack_write_contract_v1.py).
The guarded receipt is under `private/test_runs/pc07_caster_attack_v1/`;
helper execution, source reviews and static art/effect inspection are under
`private/research/pc07_caster_attack_20261020/`. Those private inputs and game
artifacts are not distributed with this source checkpoint.

## Native battle results

All twelve candidate processes finish normally. One is an ordinary-input
Schala critical Attack; one is an ordinary-input Crono control. The other ten
are explicitly injected animation-context tests: target coordinates and
normal/critical or alternate-branch flags are changed at declared boundaries
after native damage calculation. They establish the selected animation routes,
not natural RNG or newly proved damage mechanics.

Schala remains at (184,159), with zero pathfinding calls, in all eleven of her
cases. Normal selects package `$04` and critical `$10`; the tested alternate producer
branches are `$00` and `$40`. All four target facings are observed. The native Attack
completes the result, owner release, completion latch, cleanup and subsequent
readiness. The ordinary Schala action preserves 379 HP / 93 MP and deals 996 damage,
matching its immediate parent. The Crono control preserves its original `$01`
package, movement, 179-frame action duration and `$4F`/`$40` sound sequence.

The first fixture moved displayed target coordinates but left cached distance
coordinates stale. Its near/equal names are retained as historical labels,
not accepted distance claims. Two additional cases synchronize the actual
distance inputs: 24px up/normal and exactly 40px front/critical both produce the
native near flag `$00`. Natural and far cases produce `$FF`. Both sides of the threshold
still return approach `$00`. No unrelated cases or historical proofs were rerun.

Rendered output visibly contains Lily's left preparation 27 and release 28,
and the new front preparation 30 and release 31. The capture/cache lag is
documented; acceptance uses actual screen pixels. The clearest synchronized
front critical sequence preserves the full covered robe. An earlier injected
near-front case has lower-body occlusion outside its cast poses; its cause is
unresolved and the captures are retained. Back-facing Attack preserves the
original frame 0; this pass adds no new back-facing gesture.

The projectile is a small travelling light fleck with a clear ring/flash at
the target, without a held weapon. Its travel is low contrast in the Lavos
scene; a larger or more distinctive dream effect remains possible polish.
The actual audio publication is `$4D`, replacing the matched launch sound. This
is a sound-ID observation, not listening-based audio acceptance.

Evidence: `private/test_runs/pc07_caster_attack_observation_v1/aggregate_v1.json`,
the per-case traces and summaries, `visible_art_pixel_matches_v1.json`, and
the independent `engineering/visual_review_v1.json` under the current research
folder. The two preserved parent processes timed out after complete action,
cleanup and readiness windows; their derived cut observations do not change
those raw process statuses. All twelve new candidate processes succeeded.

## Epoch and NPC preservation

The same `9f678764` candidate passes the requested ordinary-controller sequence
over 4,164 frames: board, fly, land, disembark, enter Ioka hut `$0115`, return to
world `$01F3` and reboard. Epoch's position changes from (544,512) to (544,480)
and remains at the new position through the house/world roundtrip. The roster,
live PC07 record, Epoch name and SRAM remain unchanged. This is scene-position
preservation; no cold-load or normal SRAM-save test is substituted for it.
The detailed result is `epoch_candidate_v1/result.json` in the native packet.
All thirteen original NPC spans and the shared palette remain byte-identical
under the complete-diff guard.

## Review and remaining scope

Lily received the two actual art PNGs plus a private ZIP containing the ROM,
authored implementation source and editable art in the saved Project Epoch
conversation. Personal GPT-6 was visibly locked by its usage limit, so the
authorized GPT-5.6 Pro fallback was used. Her completed static review recommends
keeping v3, with minor cautions about the compact palm cluster and preparation
timing. Coda retained the art after independent rendered inspection. Her review
does not claim native execution. Claude Code was not dispatched because its
included session allowance was exhausted; no paid usage was enabled.

This milestone changes Attack presentation, not its damage formula, equipment
or MP cost. Coda chose stationary basic casting at every range; any later
close-up spell choreography belongs to deliberately authored Techs. Magus-derived
dream Techs, a distinct back-cast pose, broader party-position support and full
game-path qualification remain separate work. Production catalogs remain
unapproved. No Git push or portfolio publication occurred in this pass.

Machine-readable counterpart:
[schala_caster_attack_2026_10_20.json](../references/schala_caster_attack_2026_10_20.json).
