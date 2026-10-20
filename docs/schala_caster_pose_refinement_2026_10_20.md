# Schala aimed-casting refinement — October 20

The separate private candidate `private/test_runs/pc07_caster_pose_refinement_v1/diagnostic.sfc`
has SHA256 `17b156701321ec11b5ed115dff0964665160bc99a857641d42078a7d73e3cb3e`.
It preserves the accepted stationary-caster parent and adds a more distinct
front release and a rear-facing preparation/release pair. This remains the
qualified third-active-position implementation, not complete character support.

## Changed art and guarded construction

All previous 32 assembly records and 122 graphics tiles remain byte-identical.
New front release 32, rear preparation 33 and rear release 34 use fourteen
additional tiles in a separate declared span. Front preparation 30 and Lily's
horizontal casts are retained. Movement, recoil, KO, NPC Schala, the shared
body palette and world-map V5 assets remain unchanged.

The field adapter now permits the original aligned graphics offsets and the
new isolated tile span while refusing the occupied gap. Its 236-byte encoding
agrees with Asar and an independent splice of the parent. The focused tests
cover all 65,536 possible X values: 136 aligned offsets are admitted. Nine
focused tests pass. Intent and complete-diff guards accept 728 changed bytes
in eleven declared spans, with exact inverse-parent reconstruction. Canonical
gameplay data, including unused content, is unchanged from the parent; the
canonical checksum header is updated. No historical validation chain ran.

## Native observations

Four fresh Mesen runs cover up/front normal and critical animation contexts.
Each explicitly injects target position and animation flags after damage
calculation; these are not claims of naturally occurring critical damage.
All four remain at (184,159), select the expected facing and ranged package
04/10, preserve the qualified helper context, complete cleanup and return to
readiness. Actual high-ROM read callbacks reach the new graphics bytes. The
callback itself does not distinguish CPU and DMA read origin.

Rear preparation and release match all 398 and 411 opaque pixels respectively
in both up cases, with RGB error at most one. The front preparation matches
385/388 and release 386/389 opaque pixels. The same three lower-right outline
coordinates have exactly the same actual RGB in the retained parent capture.
All seventy changed opaque front-release pixels match the new native art.
The strict exact-match result remains false; its tolerance was not relaxed.
The apparent inherited overlap's precise rendering cause remains unproved.

The up-fixture ring appears near Schala's torso, so its visibility alone does
not establish impact on a separated target. Claude Code flagged this and Coda
confirmed the visual limitation in the supplied contact board. A narrow reuse
of the existing trace finds both target display and distance-cache coordinates
at (184,135), only 24 pixels above the caster foot anchor (184,159). The captured
ring effects are near (194,143), inside her body's vertical span. This does not
show a cache disagreement or establish a hit on a clearly separated enemy.
The artificial front target lies below the battle HUD. The captures establish
the body pose, facing and completed action, but not ideal front impact placement
or exact palm-to-bolt alignment. The body returns to inherited idle before the
later visible effect interval. No new animation timing was authored.

Root and the runtime reviewer inspected the actual native boards at 1x/3x.
The covered robe, retail colors and changed hand gestures remain visible.
The packet is `private/test_runs/pc07_caster_pose_refinement_observation_v1/`;
use the v2 contact boards, which show the up impact ring and label the front
HUD limitation. Earlier boards and strict failed equality results are retained.

## Affected field and Epoch regressions

A fresh controller-only field run reaches frame 3286. All 587 observed rows
and 35 screenshot files match the retained movement candidate exactly, with
PC07 present at object offset 10 throughout. Commands, animation bases, roster,
and source/staged/live battery data remain equal. This supplies selected-route
coverage of the changed field adapter, separately from the vehicle test.

The same candidate passes the flying Epoch scene roundtrip in 4,164 frames:
board, fly from (544,512) to (544,480), land, disembark, enter Ioka hut 0115,
return to world 01F3 and reboard at (544,480). All nine captures and recorded
rows match the parent vehicle run. Roster, PC07 live record, Epoch name and
SRAM remain unchanged. This is scene-position persistence, not a normal-save
or cold-load test. That fixture has an empty third field-object pointer, so it
does not supply the positive PC07 field-adapter coverage described above.

## Reproduction and remaining work

Build once to a fresh private destination with
`python -B tools/build_pc07_caster_pose_refinement_v1.py --output <fresh-output>`.
The builder pins its immediate parent and runs both write guards before image
emission. Runtime commands and evidence distinctions are documented in
`private/research/pc07_caster_pose_refinement_20261020/runtime/README.md`.

The native packet's delivery manifest records source and output identities.
The field result is under
`private/test_runs/pc07_run_pose_observation_v1/caster_pose_refinement_v1/`;
the vehicle result is under
`private/test_runs/pc07_caster_attack_observation_v1/epoch_pose_refinement_v1/`.
ROMs, saves, traces and extracted/derived game art remain private and ignored.

Lily received the actual media, candidate ROM and relevant source for a bounded
visual review in Personal GPT-6 Pro. Its disposition is recorded separately
when returned. Prismatic dream-Tech work currently consists of offline source
and palette studies; no new Tech or prismatic resource has been installed.
The separately requested Schala portrait is being developed against the actual
48x48 retail portraits and concept reference. Neither work item changes the
scope of this casting evidence. No Git push or portfolio publication occurred.
