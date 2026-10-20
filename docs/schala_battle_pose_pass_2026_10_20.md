# Schala Attack, recoil and KO pass — October 20

The first private battle-pose build installs Lily's retail-faithful horizontal
casting poses, adds directional recoil bindings, and fixes both observed KO
paths. The original 23 body frames, original 79 graphics tiles, all thirteen
protected NPC spans and shared palette remain unchanged. The requested flying
Epoch scene roundtrip passes on this same image.

This is a bounded presentation milestone for the currently supported third
active position. It does not finish Project Epoch or implement a ranged magic
bolt. The inherited Crono Attack movement and mechanics remain in this build.
Andrei's current caster/dream-Tech direction is recorded separately in
`schala_caster_direction_2026_10_20.md`.

## Trace-led changes

The actual critical Attack requests animation selectors
`26 → 31 → 32 → 0E → 03` (hex). Existing normal/path package decoding also uses
31, while path approach explicitly uses the already corrected run06. Preserve
preparation/movement26, run06, recovery0E/03 and unrelated existing sequences.

| Consumer | New mapping | Preserved behavior |
|---|---|---|
| Attack31, left/right | Lily preparation → release, frames27/28 or23/24 | Original total raw delay5, now2+3; existing up/down art |
| Attack32, left/right | Lily release28 or24 | Original delay5; existing up/down art |
| Recoil05, left/right | Red recoil29 or25 | Original delay5; up/down retain frame18 |
| Qualified PC07 status08 | Private selectorF0, prone frame26 | Original07/08 streams remain unchanged |
| Qualified direct predicted KO | Return prone frame26 | Canonical D1 table and every nonqualifying read remain intact |

The left-facing records are explicit reflections of the selected right-facing
art, without adding graphics tiles. Native target-facing selection is unchanged.
Forward/down-facing casting is a separate art study, not installed here.

KO needed two corrections. The baseline predicted-death read at C141A5 used
logical07's canonical D1 row and returned frameE0, outside the23-frame provider;
the delayed screenshot shows Schala disappearing. Later status08 selected a
standing casting frame. Rewriting08 directly would also alter the shared tail
of07. The new qualified producer instead selects isolatedF0, preserving both
old streams.

Both KO helpers require roster07 plus the complete published slot2 graphics
420000 and assembly421000 pointers. Direct KO additionally checks X001C..001F;
status checks the full slot word0002 and incoming selector08. The status helper
changes only the value of the original dp84 store, restores incoming A/X/P,
then performs the original LDY. The direct helper otherwise executes the
original lookup. No vehicle state or shared canonical table is repurposed.

## Construction and focused checks

Current parent:
`private/test_runs/pc07_run_pose_v1/diagnostic.sfc`, SHA256
`00e3440c2927834554c7e3f872a5b995b76e53e1e6775ddd76abe9bac0b8f18f`.

New private image:
`private/test_runs/pc07_battle_pose_v1/diagnostic.sfc`, SHA256
`7549c49c3fec255ea559e8b1e0420a7b6285d921948f9550308291270db470e5`.

The source builder derives four new poses from the actual pinned Lily/Red
indexed files and appends three mirrors. There are112 graphics tiles and30
assembly records in total. The existing field tile adapter changes only its
qualified upper-bound operand, from09C1 to0DE1. Original frames are never
repacked or overwritten.

Both shared intent and complete-diff guards pass before image emission:
1,525 changed bytes in23 declared sections, with exact inverse restoration of
the parent. A focused allocation census reuses accepted placement metadata and
checks three named new regions against117 conservative occupied records. FF
alone is not ownership evidence. Production catalogs remain empty.

Asar reproduces the independently encoded74-byte direct and82-byte status
helpers. The independent opcode model passes24,308 focused cases covering all
seven qualification bytes, branch outcomes, relevant flags/hidden-B values,
slot/index boundaries, register preservation and exact writes. This is a host
model, not interrupt or physical stack ownership proof. Ten pure codec/mirror
tests and five current guard tests also pass. No historical builder or proof
chain was rerun.

Reproduce the new build into a fresh private directory:

```powershell
python -B tools/build_pc07_battle_pose_v1.py --output private/test_runs/pc07_battle_pose_<fresh-name>
python -B -m unittest tests.test_native_pc07_pose_codec_v1 tests.test_native_pc07_pose_mirror_v1 tests.test_pc07_battle_pose_write_contract_v1
```

## Native battle evidence

The Mesen baseline records1,719 targeted events through frame8254. The new
candidate records1,739 through8253, using ordinary controller input to Attack
and then waiting for natural incoming damage/KO. The selected first Attack is
critical package01; a separate normal/path action is not claimed.

Actual frame reads/cache writes select left preparation27 then release28.
The request31-to32 interval remains7 frames and32-to-first0E remains21, matching
the baseline. Both helpers execute in the game with native E0/M8/X16/D0 and
DBR7E. Their recorded continuations preserve the declared CPU context and
restore the stack. Direct KO returns26; settled HP0 selectsF0/cache26. Root
visually inspected the prone sprite and the corrected casting comparison.

Screenshot timing matters: request31+1/+3 still visibly show the previous
idle frame, despite newer cache observations. The later request32+1 displays
preparation27, and32+3 displays release28. An opaque-pixel comparison confirms
391/391 and423/423 expected pixels respectively, with a per-channel tolerance8
and documented origin; transparent pixels are not compared. The first comparison
board's premature pose labels are corrected in `battle_before_after_v2_3x.png`.
The original board is retained with the correction, not used as visual proof.

Incoming-hit selector05 is observed, but this encounter uses facing0 and keeps
existing frame18. The newly bound horizontal recoil25/29 is therefore
**not yet demonstrated by a natural hit in this run**. No claim of complete
recoil coverage or all-party-position support follows from the static binding.

Evidence lives under
`private/test_runs/pc07_battle_pose_observation_v1/`, including the baseline and
candidate reports, exact events, snapshots and corrected comparison. The
runtime README contains reproduction commands. Batteries and images remain
unchanged by observation; no full bus/WRAM, global interrupt or all-game-path
proof is claimed.

## Flying Epoch regression on the new image

One headless Snes9x process uses the previously accepted flying-Epoch fixture
and ordinary controller sequence. It reaches all seven required milestones:
parked start, board, fly, land/disembark, enter Ioka hut, return to world, reboard.
The scene test completes at4164 frames, without a cold-load substitution.

Epoch moves from(544,512) to(544,480). That new parked position and era persist
through actual interior0115 and return to world01F3, then reboarding succeeds.
The00/01/07 roster, live PC07 record and Epoch name remain intact throughout
the sampled route. SRAM remains unchanged. This checks scene persistence as
requested; it is not a new battery-save, cold-load or all-era test.

Root inspected the inside-hut, returned-world and reboarded captures. The
recording and validator are `epoch_roundtrip_v1/` and
`epoch_roundtrip_validation_v1.json` in the new observation directory.

## Next implementation boundary

Keep this accepted battle-pose image intact. Refine and review the front cast,
exercise the new horizontal recoil in a suitable native encounter, and build
the separately investigated caster-only Attack route. Lucca/Marle's near-range
physical branches, weapon visual configuration and sound consumers must be
handled deliberately; changing body poses or one donor selector is insufficient.
Magus-derived dream Techs remain a content/engine integration task, with Magus's
own data preserved. Do not rerun unrelated historical proof chains.
