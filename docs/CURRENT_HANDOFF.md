# Project Epoch current handoff

## October 20 development download and correspondence checkpoint

Andrei accepted the corrected in-game portrait/status view and requested a
public development update, selected screenshots, a patch and matching states.
The final package is **IN DEVELOPMENT — NOT YET TRULY PLAYABLE**. It contains
one deterministic BPS, two independently restored Mesen states, six labeled
screenshots, installation instructions and machine-readable manifests. No ROM
is distributed; states remain download assets outside source Git. Older and
injected study screenshots retain their actual build and evidence labels.

The BPS applies directly to the exact clean unheadered US Rev 0 image and
reproduces the accepted `d4b6915d...` eight-MiB candidate below. Ten focused
format/export tests and an independent application using pinned Mesen patcher
source passed; all three CRCs and all target bytes match. The original research
chain was not replayed. See `epoch_development_release_2026_10_20.md`,
`project_epoch_development_update_2026_10_20.md` and their JSON counterparts.

The public download is available through the GitLab generic package
`project-epoch-development/2026.10.20`; the portfolio update contains the
portrait/status screenshot and the same downloadable package. Exact publication
receipts and the reviewed Justin email draft remain private under
`private/research/epoch_update_20261020/`. Lily reviewed the supplied source,
notes and portrait in the saved Epoch conversation; she did not run the game.
The email remains a draft for Andrei, not a sent message.

Resume engineering at the explicit unfinished consumers below, rather than
replaying the completed publication or historical proof chain. The Tech-tab
name, small save-card portrait, wider party/save lifecycle support, caster
balance, equipment, Techs and story progression remain open.

## October 20 current: numeric stats, portrait and HP-color correction pass

Final screenshot inspection of retained v1 exposed another display issue:
HP 608/969 was red despite all ten saved status bytes being zero. The older
threshold adapter admitted party-exchange mode only, so the ordinary status
route fell back to the seven-entry cache and read occupied `$0D46/$0D47`.
The separately guarded v2 adapter now uses PC07's own derived maximum:
floor(969/10)=96. Actual CPU reads/comparison and the ordinary white HP color
pass first selection and reopen, with Crono/Marle controls. Six captures and
760 observed status frames pass. Critical-HP boundaries are statically tested;
no critical-HP native fixture or repeat of the older battle/vehicle matrix
was added. Preserve v1 and its red-HP capture as historical evidence.

The latest tested private candidate is
`private/test_runs/pc07_menu_stats_portrait_v2/diagnostic.sfc`, SHA256
`d4b6915dc85ef2bc782583de4478f9ed61e07f68fb2dde58b9cced4350ba3117`.
It preserves the prior numeric/art correction unchanged. That initialization
gate lets the existing stat routine process PC07
only when her initialized live identity is present. The first menu opening
now recomputes the stale derived maximum HP/Attack from 1029/48 to 969/236
before any Schala selection. Actual record reads and thirteen native commit
writes are observed. The seven original records remain unchanged across that
additional pass. Both openings, sixteen gate returns and ten selected
Crono/Marle/Schala captures pass; source/staged ROM and battery are unchanged.

V6 palette-B portrait art replaces only Schala's separately owned tiles and
palette. It follows the original concept's calmer expression, pale face and
blue hair more closely; an independent visual review supports this improvement,
with remaining likeness differences documented. This is a new concept-derived
candidate subsequently accepted by Andrei in the screenshot follow-up. All seven original face
regions remain exact; original NPC assets and actual vehicle name Wings remain
preserved. No portrait code or upload scheduling changed in this derivative.

Andrei explicitly chose calculation/display fixes first and balance separately,
then confirmed equipment can wait. Base stats, equipment, growth and save inputs
remain unchanged. The requested real emulator screenshot is
`private/research/pc07_portrait_20261020/runtime/schala_fixed_portrait_stats_white_hp_native_4x.png`;
it is a plain nearest-neighbor enlargement of the first-selection capture.
The compact final receipt is `private/research/pc07_portrait_20261020/runtime/hp_color_delivery_receipt_v1.json`.
See `schala_menu_stats_portrait_2026_10_20.md` and its machine-readable counterpart.

The Tech tab still calls PC07 Wings; this separate name consumer remains open.
Schala renaming and native Epoch-renaming tests also remain separate work.

## October 20 preceding portrait-integration checkpoint

The separately guarded full-status portrait v2 candidate is
`private/test_runs/pc07_status_portrait_v2/diagnostic.sfc`, SHA256
`773e32de495acad1ac6d12fbe15101f45bc0240e65af47e4de19a318d54de128`.
Its controller-only route passes all eight faces, Schala-to-Crono restoration,
close/reopen and the separate Item/Tech/Settings-to-status returns. Graphics
upload once per menu initialization during forced blank. All seven original
portrait regions, Schala's separate region, the six-letter status name and
the vehicle's custom Wings name remain intact. This is bounded integration
evidence, not approval of every menu consumer or the final artwork.

Andrei subsequently requested closer original-concept likeness and corrected stats.
The first status display shows HP 608/29 and Attack 48, while later redraws
show 608/969 and Attack 236. These tiles match the parent: portrait v2 did
not introduce the defect. The source sidecar has valid base max HP 969;
the initial menu recalculation stopped after PC06. The narrow PC07
refresh fix is now in the separately tested derivative above.
The current test loadout/base stats remain donor-derived; caster progression
and equipment are separate unfinished work. Portrait V4/V5 studies remain
preserved alternatives; the derivative above uses the closer V6 palette B.

The Tech tab separately still calls PC07 Wings. The status name patch does
not fix that consumer, and no native Epoch-renaming test is claimed.
See `schala_status_portrait_2026_10_20.md` and its machine-readable checkpoint.

The refined front/rear casting and affected field/vehicle regressions below
are complete within their stated bounds. Lily and Claude Code both completed
image/source reviews; they differ on the preferred prismatic palette. The
unchanged native Dark Mist baseline is now captured through completion,
including its later palette brightening and raster limits. No prismatic
Tech is installed. Preserve the completed evidence instead of replaying it.

## October 20 historical first portrait integration: v1 rejected and superseded

The selected portrait is the earlier softer V2 likeness, converted to 48x48
and its own sixteen-color palette. Andrei rejected the later angular V3.
The first guarded status-portrait candidate
`private/test_runs/pc07_status_portrait_v1/diagnostic.sfc` has SHA256
`c3a2ff596b3d77040b0fde4e52dd4816faa76a69f8b8df491b4f12a247a2cc28`.
**Do not promote this image:** its controller-only native route exposes
display corruption on Crono/Schala and a stale sixth name glyph after leaving
Schala. The other six portraits, graphics/palette contents and hook return
contexts pass their scoped checks. The vehicle's custom name Wings remains
unchanged. The failed run and audit are retained under
`private/research/pc07_portrait_20261020/runtime/`.

The later v2 above fixes the recurrent transfer and stale sixth detail-name
cell. Preserve the rejected v1 and its timing pilot. The 17b156 casting
candidate below remains the unchanged parent of the accepted integration.

Lily completed the casting/prism review in Personal GPT-6 Pro, retaining the
compact casts and preferring pearl/cyan/lilac study A. The prismatic treatments
remain offline; the unchanged native Dark Mist baseline is now complete.
Her separate portrait critique supports retaining the softer face. That answer
was saved locally, but a subsequent conversation reload failed; acknowledgment
is pending. Claude Code's separate image/source review is complete. See
`schala_prismatic_study_2026_10_20.md` and private review receipts.

## October 20: refined front/rear casting tested; portrait added to active scope

The separate tested casting candidate is
`private/test_runs/pc07_caster_pose_refinement_v1/diagnostic.sfc`, SHA256
`17b156701321ec11b5ed115dff0964665160bc99a857641d42078a7d73e3cb3e`.
Four native battle contexts pass behavior and high-tile reads; the new rear
poses match every opaque pixel. Front's three outline mismatches are inherited;
all seventy changed release pixels match. Front impact is below the test HUD,
so exact palm-to-bolt alignment is still open. All prior frames remain intact.
The affected field route has 587 equal rows/35 identical captures; the flying
Epoch house/world roundtrip separately preserves its new landing position.
See `schala_caster_pose_refinement_2026_10_20.md` and its machine counterpart.

Lily is reviewing the actual media, ROM and source in Personal GPT-6 Pro.
Prismatic palettes remain offline studies. Andrei now explicitly requests
Schala's portrait from her concept art, matching the original seven portraits'
style and tight 48x48 crop. Keep original portraits, palettes and all existing
content intact; use separate graphics storage and qualified consumer routing.
The portrait is not yet installed in the casting candidate above. Preserve
the July portrait studies as historical, not selected retail-faithful art.

## October 20 current direction: poses, prismatic studies, complete legacy preservation

The next active pass finishes and tests front/up casting gestures, then asks
collaborators to compare prismatic dream-Tech color treatments. The accepted
stationary-caster image below remains the baseline until a separate guarded
derivative passes its focused tests. No prismatic Tech is installed yet.

Andrei's latest explicit constraint preserves all existing content, including
unused/cut/debug and cheat-accessible weapons, equipment and Techs. Unused is
not free. New Schala content belongs in separately named expanded storage with
explicit mappings; retain legacy IDs, records, assets and behavior. See the
absolute invariant in `AGENTS.md` and `schala_caster_direction_2026_10_20.md`.

## October 20: stationary casting Attack and forward pose pass native checks

The current tested private candidate is
`private/test_runs/pc07_caster_attack_v1/diagnostic.sfc`, SHA256
`9f678764d05f2f16e49c5a7cafe03ee6f192330322988918ff8bca2d1b2740f0`.
Schala casts from her existing position for normal and critical Attacks.
The approach flag is cleared after the original facing calculation; qualified
PC07 selects ranged packages `$04`/`$10` and sound `$4D`. No run-up or physical whack is
selected. This remains the existing third-active-position implementation.
Damage, equipment, action/result/queue processing and MP cost are unchanged.

Front preparation 30/release 31 append to the existing art. All 30 prior frames,
112 tiles, thirteen NPC spans, palette, world-map V5 and earlier KO helpers
remain unchanged. Both current guards pass: 953 changed bytes/20 declared spans.
Eight focused tests and 20,189 independent synthetic helper cases pass, without
replaying historical proofs. Source and Asar bytes agree.

Twelve candidate native processes finish normally: an unforced Schala critical
Attack, an ordinary Crono control, and ten declared animation-context injections.
All eleven Schala cases remain stationary, complete damage/cleanup and return
to readiness. The natural action retains the parent's 996 damage. Crono's
movement, 179-frame action and sounds match the parent observation. Actual
near 24px and inclusive 40px cases produce distance `$00`; natural/far produces `$FF`.
The initial near/equal fixtures changed target display coordinates without
the distance cache; retain them as facing/render studies, not boundary proof.

Actual rendered frames show Lily's horizontal cast and the new forward pair.
The small projectile and bright target impact are present; the travel fleck
is low contrast. Back/up retains frame 0 rather than a newly authored gesture.
Earlier injected near-front captures show lower-body occlusion outside casting;
the cause remains unresolved and the corrected front critical capture is full.
Keep pixel/capture lag and diagnostic context distinct from natural play.

The same candidate passes board/fly/land/disembark/hut/world/reboard in 4,164
frames. Epoch retains its new (544,480) position through the house transition,
from starting (544,512). Record, roster, Epoch name and SRAM remain unchanged.
This is the requested scene roundtrip, not a cold-load or normal save test.

Lily's completed Personal 5.6 Pro review recommends retaining front v3, with
minor palm-cluster/timing cautions. GPT-6 was visibly usage-locked. Actual art,
ROM and source were supplied; her static review makes no native claim. Claude
Code was not dispatched at its exhausted included allowance. No paid usage,
Git push or portfolio publication occurred. All emulator runs are closed.

Human checkpoint: `docs/schala_caster_attack_2026_10_20.md`.
Machine checkpoint: `references/schala_caster_attack_2026_10_20.json`.
Native packet: `private/test_runs/pc07_caster_attack_observation_v1/`.
Research/source review: `private/research/pc07_caster_attack_20261020/`.
This milestone is complete. Broader party-position support, distinct back-cast
art, Magus-derived dream Techs and full-game qualification remain future work;
Project Epoch is not complete. Preserve the prior battle candidate unchanged.

## October 20: battle casting and KO observed; flying Epoch regression passed

The current private battle-pose candidate is
`private/test_runs/pc07_battle_pose_v1/diagnostic.sfc`, SHA256
`7549c49c3fec255ea559e8b1e0420a7b6285d921948f9550308291270db470e5`.
It appends Lily's two horizontal casting poses and three explicit mirrors
(casting/recoil), plus Red's recoil and prone KO. Original body frames 0–22,
79 graphics tiles, all thirteen protected NPC spans, the palette and world-map
V5 remain unchanged. Both current shared guards pass: 1,525 changed bytes in
23 declared spans. Ten codec/mirror and five guard tests pass; the independent
two-helper opcode model passes 24,308 cases. No historical proof chain ran.

Actual critical Attack requests 26 → 31 → 32 → 0E → 03. Keep movement26,
run06 and recovery unchanged. New left-facing preparation27/release28 execute
and appear in the rendered output; observed phase intervals remain 7/21 frames.
The baseline's direct KO lookup returned invalid frameE0, briefly hiding Schala,
then status08 displayed an upright cast. Two narrowly qualified helpers now
return prone26 and redirect matched PC07 status08 to isolatedF0. Original07/08
streams and the canonical D1 table remain intact. Native entry/continuation
checks and final HP0/F0/cache26 pass. Horizontal recoil25/29 is installed but
not naturally exercised by this encounter, whose hit05 uses existing facing0
frame18. Do not claim full recoil, normal/path Attack or all-facing coverage.

The first comparison board used captures that still displayed the old frame;
screen output lagged cache updates. Use `battle_before_after_v2_3x.png` in the
new observation folder. Later existing captures independently match every
opaque pixel of preparation27 and release28; no extra emulator run was needed.

The same image passes the requested Epoch scene test: board, fly, land and
disembark, enter Ioka hut0115, return to world01F3, and reboard. Epoch retains
the new position (544,480), distinct from its starting (544,512). The roster,
live PC07 record, Epoch name and SRAM remain unchanged. This is an actual
house/world scene roundtrip, not a cold-load or battery-save substitute.

Andrei's latest direction is a weapon-free caster at every range, including
critical hits, with a front-facing cast and Magus-derived dream-themed Techs
connected to the Dream Devourer. The old "Astral Regent" design is historical;
its incompatible costume, palette and Shadow kit are superseded. See
`docs/schala_caster_direction_2026_10_20.md` and its machine-readable counterpart.

The current ROM still inherits Crono Attack movement, effects and mechanics.
The bounded Lucca/Marle investigation proves policy00 alone still permits
close whacks. A dedicated PC07 no-approach/9930 route, ranged packages04/10,
and deliberate visual/audio adapters remain to implement. Front-cast studies
v1/v2 are private, reviewed and uninstalled; the forward release still needs
clearer hand placement. Preserve this tested image while developing that next
candidate. Magus's own data and all original NPC assets must remain intact.

Human evidence: `docs/schala_battle_pose_pass_2026_10_20.md`.
Machine checkpoint: `references/schala_battle_pose_pass_2026_10_20.json`.
Current native packet: `private/test_runs/pc07_battle_pose_observation_v1/`.
Current engineering/art: `private/research/pc07_battle_pose_20261020/`.

## October 20: minimal normal-run correction, native comparison passed

Andrei clarified that suitable PC07 sprites must be preserved: fix assignments
and fill genuine gaps, rather than replace the whole body sheet. Lily's
corrected v2 casting preparation/release is now the preferred casting basis;
that selection supersedes the October18 art-direction note, but those study
frames are not installed. Keep the robe/covered feet, pure-caster direction
and original NPC assets intact.

The new private `private/test_runs/pc07_run_pose_v1/diagnostic.sfc` has SHA256
`00e3440c2927834554c7e3f872a5b995b76e53e1e6775ddd76abe9bac0b8f18f`.
It changes eight normal-run `$06` frame references to existing directional
movement pairs, plus eight header checksum bytes. All23 body frames, shared
timing, world-map V5 and thirteen original NPC spans remain byte-identical.
Current intent/complete-diff guards and five focused tests pass. The accepted
V5 parent remains unchanged; no historical builder/proof chain was replayed.

Two headless Snes9x runs used the same16-step controller plan and recorded
587 end-frame snapshots each through frame3286. In map01DA with00/01/07 in
the supported party positions, baseline `$06` uses `$13/$14` in all directions;
the candidate uses up04/06, down08/0A, left0C/0D, right0E/0F. Walk and final
idle return are observed; positions/context match across all paired snapshots,
and both batteries remain unchanged. Root inspected the same-frame rendered
comparison. This is bounded native functional/rendering evidence, not a bus
proof or a complete game-path qualification. See
`private/test_runs/pc07_run_pose_observation_v1/` and
`docs/schala_run_pose_correction_2026_10_20.md`.

Next: observe the actual Attack animation requests before binding Lily's cast
poses. KO/status `$08` currently shares its casting token with the end of
`$07`; correct those roles deliberately rather than blindly overwrite one
entry. Alternate leader run `$17` remains outside this third-position pass.
Explicit scripted `$06` requests inherit the corrected motion; their PC07
attribution remains unresolved. No publication occurred in this pass.

## October 18: main-body art continuation, no new ROM build

Andrei resumed the regular/battle/run/KO art with Lily and the other
contributors, keeping retail Schala's full robe and covered feet. Coda now has
a twelve-frame directional study: eight running frames across four facings,
casting preparation/release, recoil and KO. Actual PNG/index-grid equality,
palette/transparency and four-piece geometric coverage pass; native encoding,
consumer bindings and in-game motion remain unfinished. Front/back retain the
installed head/hair/collar pixels; left is a disclosed mirror of right. A more
energetic right-running alternative is preserved separately.

Lily's Personal GPT-6 Pro v2 bundle corrects two tan hem pixels and the run-B
robe gap but retains a weak KO. Red's new Opus 5.5 Max six-pose bundle improves
recoil and horizontal KO mass, with heavy swept hair and stiff folds still
provisional. A Red-body/Coda-head KO experiment is preserved but rejected for
selection: the triangular hair and neck join look worse. Gemini/Nua/Meta
returns were inspected and rejected for retail-design drift. Wren's actual
six-pose bundle was retrieved and visually inspected: useful covered-robe
motion, but heavy hair, a rigid casting arm, weak recoil and a muddled KO face
leave the set provisional. The checkpoint records each actual return and limit.

No ROM, save, NPC graphics/assembly/animation or shared palette was changed.
The accepted world-map V5 and flying-Epoch evidence remain prior receipts;
the historical proof chain was not rerun. No new art is user-selected or
installed, and no publication occurred in this pass. Keep the actual pixels,
reference packets and conversations private. Source-safe progress is in
`docs/schala_main_sprite_art_progress_2026_10_18.md` and
`references/schala_main_sprite_art_checkpoint_2026_10_18.json`; the inspected
boards and reproducible art sources are under
`private/research/pc07_main_sprite_art_20261018/`.

Continue from visual refinement and a coherent chosen set, then a new
PC07-only compiler version. Preserve installed frames 0-22. Normal run `$06`
uses 19/20 and a timing stream shared across facings; alternate run `$17` and
battle-role bindings are separate obligations. Pixel-equal native encoding,
the current write-intent/complete-diff audit and all thirteen recovered NPC
span equalities precede any emitted image. The shared original palette remains
protected. Test changed consumers only; do not replay world-map/Epoch/save
proofs for a new robe or arm pixel.

## October 17: selected Schala world-map art milestone

Coda V5 is explicitly selected by Andrei and now passes the selected native
world-map observation as logical07 in the third active position, with 00/01
retained. The guarded private image is
`private/test_runs/pc07_worldmap_coda_v5_v1/diagnostic.sfc`, SHA256
`ec7e5c089116c37510aea2bacc7a82c4131432eef414bdb8f6ef89723d6c6724`.
The accepted new recording is
`private/test_runs/pc07_worldmap_observer_v4_coda_v5_run1/validation_v4.json`.
All1,168 graphics/palette bytes, nine native copies, three actual caller returns,
949 third-member draw nodes and4,745 shadow-OAM writes/readbacks pass. All four
walking directions, actual selected displacement and both prolonged-idle
frames are observed. Original00/01 destination graphics/palettes, staged
inputs and battery remain unchanged. Root inspected native screenshots and
the70-frame documentary contact sheet. Lossless3x APNGs are available under
the private art packet's `visual_review/coda_v5_observer_v4_motion_v1/`.

The new provider is136 bytes with three exact hooks and five immutable data/code
allocations. Current intent and complete-diff guards passed before emission:
ten spans,1,320 changed bytes and exact inverse restoration to the accepted7098
parent. No historical builder/validator chain was replayed. Reuse these current
receipts; do not repeat the October15 menu/battle/save proofs without a newly
failing boundary or source drift. Production catalogs remain unchanged.

MAP-014 corrects our old auxiliary-graphics/palette annotations. The native
world-map set has nine16x16 images and eight copied palette colors. The strict
exporter reconstructed all seven retail sets in28 exact comparisons. Six
external collaborators supplied independent candidates; V5 retains the user's
preferred proportions, while V6 remains optional and uninstalled. Private
reference pixels, ROMs, saves, art bundles and conversations stay outside Git.

See `docs/schala_worldmap_milestone_2026_10_17.md` and
`references/schala_worldmap_milestone_2026_10_17.json` for current evidence and
reproduction. The recruited-start world-map fixture is explicitly synthetic;
it does not prove native recruitment. The separately requested flying-Epoch
functional check now passes: board all three, fly from544,512 to544,480, land,
enter Ioka hut0115, return to world01F3 and reboard at the unchanged544,480.
The4,164-frame Snes9x recording is under
`private/test_runs/pc07_epoch_scene_roundtrip_v2_run1/`; current validator and
nine read-only full-WRAM snapshots agree. Root inspected interior, returned
world and reboarded captures. Roster,PC07,Epoch name and SRAM remain unchanged.
This is scene-transition position persistence, not SRAM-save/cold-load proof.
The source fixture preserves genuine late-game vehicle/location/event data and
adds Schala deliberately. General vehicles, era changes, arbitrary active
positions and a complete playable release remain unproved.

The next user-directed art stage is the main field/battle/run/KO sprite set,
using the actual current playablePC07 sheet and original seven PC references.
Each collaborator and Coda should hand-author original missing poses, with no
weapon sprites: Schala is a pure caster, using an ordinary-Attack casting
gesture and a separately proposed magic bolt. See
`docs/schala_main_sprite_art_brief_2026_10_17.md`. The reference packet and all six
external attempts are collected in their available forms; Coda's own study is
also preserved. None is approved for integration. Andrei rejected retail-design
drift and bare feet: keep the existing robe, covered feet, hair, trim, proportions
and shading. Start the next pass with a small faithful pose comparison rather
than expanding a flawed sheet. This does not change the accepted ROM. Original NPC
Schala graphics, assembly and animation must never be overwritten. See
`references/schala_main_sprite_art_checkpoint_2026_10_17.json` for per-author
delivery and correction status. Project Epoch is unfinished.

The original NPC dependency map recovers 13 known protected spans. PC07 has
separate graphics/assembly/animation copies but still shares original palette
file `$240C00..$240C18`; preserve it. Any future PC07-only palette edit requires
a separate guarded copy/binding. The map is source recovery, not a newly
installed preservation guard or complete consumer-ownership proof. This bounded
two-hour continuation is closed with the tested world-map and flying-Epoch
milestones intact, main-body art unfinished, and no publication performed.

## October 15: selected native party-selection landmark complete

Andrei selected a short-term party-selection milestone after the bounded
persistent Schala prototype: choose, remove and reselect PC07 in the native
exchange UI, leave the menu, and preserve the chosen formation through field,
battle and normal save/fresh load. That bounded goal is now complete: the
corrected menu/field/Attack recording and the changed-formation native
save/fresh-load recording pass. Project Epoch remains unfinished. The admitted
route keeps active leaders00/01 and swaps Schala in/out of the third position;
it is not arbitrary-position support or a generally playable release. See
`docs/schala_party_selection_milestone_2026_10_15.md` and its machine-readable
companion under `references/`. Native first recruitment remains separate.

The corrected private v2 image now passes the selected native menu, field and
ordinary Attack route in one fresh process:
`private/test_runs/pc07_party_exchange_battle_v1_run1/`. Image SHA256 is
`7098f38c0b28b7806a1f69d092f7f3fd765544935e8667f5f6dfb495d386f95f`.
The menu prefix completes all 23 actions with 13,510 matched watched writes;
the field/battle suffix has 67,714 matched pairs. Actual movement, separate
00/01/07 battle records, Attack damage996, MP93 preservation, caller/cleanup
returns and renewed readiness pass the narrow new-run inspector. The battery
stays unchanged; no savestate or debugger state preparation is used.

Root visually inspected initial/page1/returned-page0 and attack-ready captures.
Schala's purple sprite and full six-letter name render correctly, Ayla is
restored, and Gaspar remains in place. A separate snapshot comparison confirms
Schala's exact512-byte frame across the physical05/02 page mapping, no old
Magus/Robo frame collision, restored six-byte D1 colors, identical full CGRAM
after returning to page0, and unchanged Gaspar record. Sources and reports are
under `private/research/pc07_party_exchange_v2_20261015/` and
`private/research/pc07_party_exchange_battle_followup_v1_20261015/`.

V2 removes out-of-task frame uploads and leaves dirty frame fields for the
ordinary animator after its own staging reset. It also restores old-owner D1
colors and fills the existing sixth-name blank through the local row hook.
The mapping core, eleven hook spans, field helper and semantic persistence
components are unchanged. Both current write audits passed before emission:
21 spans,3,334 changed bytes, exact inverse restoration. This is settled
rendering evidence, not an instant first-frame or whole-engine ownership proof.

Changed-formation normal save and fresh load now pass in
`private/test_runs/pc07_party_exchange_save_roundtrip_v2_run1_save/` and the
matching `_load/` directory. Actual separate child PIDs217260/94348 both exit64
without timeout. The first emulator's exact8192-byte battery is staged into
the second before fresh boot; no MSS or debugger game-state injection is used.
Its SHA256 is27968c673ee76f868a0b656a6dca4f85b7c13162c9530198be4538cf024d20a3.
Active00/01/02 and reserve07/80/04/03/06/05 persist through the native load
return and two actual field ticks. All2270 SRAM write/readback pairs reconcile,
with native checksum9744, sidecar CRC34127 and full-slot SHA256 binding passing.
Original-seven/name/compat snapshots match at the save/load returns; unrelated
SRAM regions remain unchanged. Root ran the current `validate_followup_v4.py`
once; `_load/save_roundtrip_validation_v4.json` records acceptance.

The v3 inspector incorrectly required scratch to stay zero after field startup
and draw00 for the inactive reserve object. V4 preserves zero atC2E694 only,
records later scratch booleans without inferring their writer, and accepts
observed object8 role80/id07/draw01. Canonical negative-role gates reject drawing
before the draw flag is read. This is source interpretation of recorded state,
not a captured rendering trace. No ROM change or native replay was needed.
See the additive `RESERVED_OBJECT_VISIBILITY_V1.md` in the save followup packet.

The earlier save observer stopped before any save because a suffix-only
callback atC28000 reached the prefix's smaller site table. Preserve
`private/test_runs/pc07_party_exchange_save_roundtrip_v1_run1_save/` and the
earlier sources. The corrected prepared_v5 collector limits prefix forwarding
to prefix-owned callbacks. That stopped attempt was an observer defect, not
evidence of a game save failure; it launched no fresh-load child.

The earlier first private candidate was emitted at
`private/test_runs/pc07_party_exchange_v1/diagnostic.sfc`, SHA256
`b2c6a3a6b8d90309731aa8ec734c8a0f3b219e84b9839aba4f0022f69f511a32`.
It composes the exchange-only display mapping, bounded object8 field refresh,
and matching semantic writer/loader roster predicates. Both current shared
audits passed before emission: 21 declared sections, 3,385 changed bytes, exact
inverse restoration, one captured source operation.
The controller-only pilot source is
`private/research/pc07_party_exchange_native_v1_20261015/`.

The separate v2 observer completed all 23 controller-only actions in
`private/test_runs/pc07_party_exchange_native_v2_run1/`: two actual roster
swaps/returns, removal and reselection, both reserve pages, two menu exits and
two actual object8 startup calls. All 13,544 watched writes have matching
readbacks; the battery stayed unchanged. Object8 changes from role/id0207 and
draw01 to8007/draw00 on removal and back on reselection. Gaspar's presenter
and the adjacent record are unchanged at the six settled menu captures.
This is bounded menu/field progress, not the completed landmark.

Root visual review of that earlier first candidate found a page-transition defect: page1 shows
incorrect sprite tiles for Schala and Ayla, and page0 remains corrupted after
returning. The captured logical mappings, sprite pointers and corresponding
CGRAM palette rows are correct, narrowing investigation to the graphics upload
path. Preserve this first image/recording; a separately versioned correction is
now accepted above. At that historical checkpoint battle and changed-formation
save/fresh-load follow-ups were source-only; preserve those earlier limits
without treating them as the current status.

The earlier v1 pilot stopped before any menu input because its readiness check
sampled field brightness at endFrame. V2 records brightness15 at the actual
C000A7 field callback but temporary brightness0/forcedBlank at endFrame. The
corrected observer changes sampling phase and preserves that stopped run; it
does not repair or alter game state.

Andrei reports that his earlier experiments corrupted and moved Gaspar's menu
sprite. Existing C2 source supplies a concrete alias mechanism: seven $40-byte
character display records occupy $1800-$19BF; the exchange presenter uses
$19C0. Raw logical07 placement reaches $19CE and animation reaches $19D1.
This corroborates a mechanism, not the cause of an unrecorded historical run.
Keep Gaspar's display/position/animation and the neighboring $1A00 context
protected. Do not extend a seven-entry table into occupied presenter storage.

The separate fresh-boot baseline is now recorded at
`private/test_runs/pc07_party_exchange_observer_v2_run1`. It reaches the actual
mode5 idle handler `$C2C7E0`, captures32 neutral visible frames and exits64.
Root inspected its screenshot: the third row still reads Epoch, uses presenter
graphics and has a malformed maximum-HP display. Trace rows1984/1988/1990 and
2082/2084/2086 show presenter48 at19C0/position20CA becoming logical07 at
position7498, with matching readbacks. The captured2600..2CFF region, including
all character records and Epoch's name, is unchanged. PC07 has current HP608,
base maximum969 at record+05, and stale derived maximum1029 at+3F; the native
three-digit field renders that derived value as029. MP is93/93. This is an
existing diagnostic-record inconsistency, not menu-entry corruption.
All1440 watched display writes have readbacks. Battery and staged
inputs remain unchanged. This is the baseline defect, not a fixed menu.

The earlier v1 observation is retained: it stopped at240 menu frames because
we watched the other menu's idle handlerC2C65D. Mode5's actual tableC2C7A6 is
C7AC/C7E0/C6B9. Correcting the observer produced the successful separate v2
recording without changing the ROM. Do not describe the stopped attempt as an
engine hang or repeat the successful baseline without a changed boundary.
Human result and machine inspection receipt are in
`private/research/pc07_party_exchange_observer_v1_20261015/`.

**Historical planning checkpoint, now resolved:** the mapping, reload scheduling,
field-return handling and matching writer/loader roster adaptation described
below were subsequently implemented and accepted in the bounded v2 route above.

At that planning checkpoint, the candidate was the exchange-only mode5 route ($C019CE), retaining
three active members, four visible reserve rows and the existing fifth-reserve
scrolling. The real swap at $C2C70C already operates on the nine-cell roster.
Separate logical character IDs from the seven physical display records and
their graphics/palette/VRAM resources. An exchange-scoped visible-page mapping
was proposed to avoid any new WRAM allocation; reload scheduling and field-return
handling remained implementation work. The exact bounded active-slot support must
be explicit: current presentation/Attack adapters admit PC07 in slot2 only.

Read the actual-artifact review disposition in
`private/reviews/20261015_next_milestone/REVIEW_DISPOSITION.md` before changing
the menu or persistence adapters. Lily, Red and main Grok Bot received the same
private code-and-ROM ZIP. Their static inspection is distinct from the accepted
native recordings. At that checkpoint, the writer/loader exact-formation gates
still required joint adaptation for real menu swaps. In particular, the writer's existing refusal
path bypasses native save; separate valid caller/stack/slot admission from
roster policy rather than forwarding every failed premise into native code.
Preserve loader preclear, invalid-vanilla abort, CRC/full-slot binding and
SafeEmpty sanitation. The existing fixture metadata stays explicitly diagnostic;
this menu milestone does not claim story recruitment or completed grants.

Reuse accepted evidence and the existing usage/workflow audit below. No whole-
chain validation or emulator replay was performed for this review/planning
checkpoint. Future checks must name their changed boundary or new claim.

## October 15: bounded persistent Schala prototype demonstrated

**Current milestone: Schala's presentation, genuine cold load, field movement
and an ordinary logical-PC07 Attack work together in one fresh process.**
The accepted new run is
`private/test_runs/pc07_native_sidecar_cold_load_v1_schala_battle_run1/`.
Its unchanged collectors and validators accept the selected actual writer
battery, slot0 and fixed recruited fixture, without a savestate or debugger
game-state preparation. The load takes 74 frames / 26,626,656 master clocks.
Controller input moves PC07 through the native field transition into battle,
with separate 00/01/07 battle records. The selected Attack deals 996 damage,
leaves MP at 93, and reaches actual Attack/cleanup returns and later readiness.
All 67,842 watched writes have readbacks; eleven snapshots and 147,305 suffix
rows reconcile. Original seven live records, PC07, names including Epoch,
non-rock compatibility and the entire battery remain protected in this scope.

Root separately opened `attack_ready.png`: it shows Schala's retail purple
sprite and full six-letter battle HUD name beside Crono and Marle. Its SHA256
is `0c592c8c94a6f45ac88f244232cce8f66c7e88c31d705381996ceca23257a060`.
The automated suffix report retains `screenshot_visually_reviewed=false` for
its own scope; this paragraph records the separate root visual inspection.

The prefix report SHA256 is
`fb2087cfbf55e70b02a2a465a76e5b63ac50d63b556a8f5fceab1737ad406b3d`;
the suffix report SHA256 is
`907490881a304f08326fa83d063425070d419b91e4e4d4512996d019abe14d74`.
Both validators passed on first execution for this new recording. The native
process returned collector64/host0 without timeout. Accepted earlier runtime
proofs and their validation chains were not replayed.

The combined image is
`3539b4069eabf34023a1a2457d8a99b9db2f05d7dc15bb7dba940e2bf61d4183`.
Both current shared write audits passed before its single emission: the 26
existing Schala-v2 presentation sections plus two checksum headers, with 8,651
changed bytes. The inverse restores the accepted persistence parent exactly.
The writer, loader, SHA, event and save-layout work remains inherited. The
only intentional occupied-span supersession is the old four-byte donor-name
hook inside the existing 37-byte name-source section.

This fulfills the exact bounded prototype goal: independent eighth state,
roster/field behavior, an ordinary action and a native normal-save/cold-load
round trip, now with Schala's presentation. The save was the earlier accepted
normal-save writer run from its admitted checkpoint; this new process consumed
its emulator-written battery and did not execute another save. Human result
and additive completion receipt are under
`private/research/pc07_schala_persistent_presentation_builder_v1_20261015/`.

The result is not a generally playable release or production approval. Native
recruitment, complete Techs/equipment/progression, all slots, erase/NG+,
corrupt-file runtime matrices, whole-engine timing/ownership and unobserved
Epoch boarding/travel remain open. The fixed battle HUD name is not a general
menu/dialogue naming system. World-map sprites remain future deliberate,
code-assisted retail-style work to discuss with Lily and relevant collaborators.
Do not replay accepted history merely because the bounded goal is complete.
The older observations below retain their original scope and identities.

## Earlier October 15: lean continuation and Red's existing preview evidence

**Earlier donor boundary: genuine cold load, field movement and PC07 Attack pass.**
`private/test_runs/pc07_native_sidecar_cold_load_v1_battle_run1/continuation_validation_result_v1.json`
accepts one fresh process from the actual writer battery, with no savestate or
debugger game-state preparation. The unchanged image loads PC07, moves the
independent actor, follows the installed field transition, builds separate
00/01/07 battle records and completes an ordinary PC07 Attack. Actual participants
are `07 FF FF`; four word stores/eight observed bytes reduce target HP by 996.
MP remains 93, including two same-value MP writes. The actual Attack and cleanup
returns lead to all three later readiness publications and a ready input poll.
All 67,842 retained writes have readbacks; eleven suffix snapshots reconcile.
The seven original live records, PC07 live record, names including Epoch, and
compatibility except the five legitimate rock bytes remain protected. Whole
battery SRAM remains unchanged. This is selected native evidence, not full
WRAM coverage, CPU-exclusive bus attribution or a global interrupt proof.

The result SHA256 is
`727231e149e1b42c4aef8b63bd83b930eef262c97eb2e70f2709b8023f792286`.
Its same-run cold-prefix report is
`f4057bf9312141b1823be68dd2235f86562d6125b19f46f2f2c224757262725a`.
The generated collector is `9029e60c825d03e1cdb6b039bc240ce60248131cd1ac3433845197536c62136d`;
the suffix validator is `c63fc2f01936adad03b43b3552309f29020f18aedddca6e9a30c0ed4844c0705`.
Both new-recording validations passed on their first execution. Accepted older
recordings/builders were not replayed. Root inspected the final screenshot:
this persistence-test image still presents PC07 with the Crono donor sprite/name.
Do not describe its screenshot as the combined Schala presentation.

**Completed subsequent work: compose the existing Schala-v2 presentation with this persistence image.**
All 26 existing presentation preimages match the current parent, with no collision
with loader/writer/SHA/events. The exact existing 37-byte name-source span
supersedes its inherited four-byte donor hook; this is intentional and explicit.
A fixed additive private contract/builder was prepared under
`private/research/pc07_schala_persistent_presentation_builder_v1_20261015/`.
Reuse the completed retail NPC conversion and helpers. Do not call the old
full-image recipe, which reconstructs an earlier parent and discards save/load
work. Root must run current shared intent/complete-diff audits before any new
image emission. Those audits and the new cold-load/Attack route with Schala's
presentation are now accepted above. Her fixed battle-HUD name is not a
menu/dialogue naming system; world-map art remains future work.

**Accepted prerequisite: the actual writer battery passes genuine cold load.**
`private/test_runs/pc07_native_sidecar_cold_load_v1_run1/validation_result_v1.json`
accepts one fresh Mesen process, with no savestate restore or debugger game-state
injection. The guarded loader copies the native ten-region layout, validates the
fixed sidecar's CRC and full-slot SHA binding, restores the PC07 record, and
returns through the normal menu/reset/field sequence to two neutral field ticks.
All 30 ordered observation boundaries pass. The loader takes 74 frames,
26,626,656 master clocks, with 74 observed completed menu NMIs. Battery SRAM
remains unchanged. Original seven records, names including Epoch, and relocated
compatibility bytes match from native-copy return through the second field tick;
PC07 and roster/joined checks hold after publication. Full detailed loader write
reconciliation and selected field-continuation observations retain their stated
limits; this is not whole-engine interrupt, stack or DMA ownership.

The result SHA256 is
`adcef988f05367b17d6c0a8598ac9e85ebbc1382eb50594aea89fadbda48a6ee`.
Image SHA256:
`2ce5e5a1719cf944079089691450e58a28d57f9ec94f2b7d6b5428b841d7989b`.
Current shared intent and complete-diff audits passed before one image emission:
eight exact spans, 743 changed bytes. No accepted historical runtime proof was
replayed. The first validator omitted the collector's `sanitized` mark, which is
the successful common restore alias at `$44352B`; the successful path skips the
SafeEmpty sanitation body. Its exact source/failure are preserved. A focused
correction required this actual boundary and retained published-record checks;
the same native recording then passed. There was no emulator rerun.

**Route basis for the completed post-load Attack above.** The accepted second
field tick has location `$01DA`, tile `$0B,$3C`, arrival `$03`, with logical
actors00/01/07 already instantiated by the installed event125. These match the
existing route origin. The separately versioned continuation collector observed
control readiness, used the sourced controller route to `$01DB`, and required
an ordinary Attack through actual damage, cleanup and later readiness. It used
the same guarded image and actual battery, without the historical 171 prepared
bytes or a checkpoint restore. The earlier cold-only report stays limited to
its own cut. Native recruitment, other save slots, the corrupt-file runtime
matrix and production readiness remain outside these selected results.

**Accepted prerequisite: Schala's sidecar is written and persisted.**
`private/test_runs/pc07_native_sidecar_writer_v1_run1/validation_result_v1.json`
accepts one actual Mesen run and its emulator-written battery file. The 160-byte
sidecar equals the existing v2 codec byte-for-byte. All 165 ordered stores pass:
invalidation before vanilla save, complete payload/checksum/digest/CRC before
one final M8 magic commit. The 158 CRC/magic reads match their exact sequence.
The observed CRC is `$751A`; the native profile-1 digest is unchanged from the
accepted shadow result. Full SRAM outside the selected sidecar equals the
accepted finalized save; protected original seven records, PC07, names including
Epoch, compatibility, roster/joined state and caller frames pass. All 194
borrowed scratch bytes are restored, and the original native result returns at
pre-`$C2CF55`. There are 73 elapsed frames, 26,416,294 master clocks and 73
completed NMIs. These are selected observations, not universal stack/interrupt
or scratch ownership.

The actual battery output is
`private/test_runs/pc07_native_sidecar_writer_v1_run1/app/Saves/diagnostic.srm`,
8192 bytes, SHA256
`d5c2dad13324cde1e0b4233248976e6adf3f52dee7570f463f7d0c4511bfed46`.
It is byte-equal to the returned SRAM snapshot and differs from the initial
file. Use this emulator-written file for the fresh-process cold-load test.
The validation result SHA256 is
`a98a7c2a3aa6adca3751c8f0ce698449ac7ef66d2c906e4a59427d0382f40c6f`.
The guarded image SHA256 is
`0d32e8509a62bdd12737409beba2a53fa79820e28ff9375ee92c4118d1fc2ba7`;
four exact spans change 572 bytes, retaining the old wrapper, SHA and tables.
Both current shared write audits ran before the single emission. No historical
builder or validator chain ran. The first reporting adapter incorrectly chose
the initial identity for the overwritten battery-file path; its source/failure
are preserved under the launch packet's `diagnostics/`. After an explicit
produced-file lookup fix, validation passed on the same recording. The emulator
was not rerun. New-run DMA attribution remains outside this validator's claim;
do not broaden the prior shadow interval's separate count proof to this run.

**Accepted loader source, now installed and observed above.** The source-only
loader is frozen in `private/research/pc07_native_sidecar_loader_v1_20261015/`.
Its source receipt reports 485 assembled-byte host cases, including 176 exact
record publications and refusal of three damaged copies. The new component is
671 bytes; the unchanged preflight is separately 108 bytes. It preclears PC07,
validates vanilla before copy/sidecar reads, restores the ten-region layout and
occupied staging tail, checks the complete fixed v2 binding, publishes only the
accepted record, and sanitizes exact07/joined01 on SafeEmpty. Native validator,
copy and SHA interiors are explicit opaque contracts in these host checks;
native installation and cold-load behavior are separate evidence above. The source receipt
SHA256 is `0f549d67fb9729db02d2930bebbfa7e426fc6b66d76e9fa4fc773d8f5cb3b8ff`.
The load-menu preview adapter and both LOAD table consumers were installed by
the separate guarded builder. The new cold-load observer reused only the old
collector's controller schedule; its SRAM injection and MSS shortcuts were not
used. Preserve this completed source/installation/runtime separation and reuse
the accepted result for the next continuation.

**Accepted prerequisite: the post-save shadow digest passes.** Root emitted
the private image through the current shared intent and complete-diff audits,
then ran one isolated Windows Mesen test from the accepted save checkpoint.
`private/test_runs/pc07_shadow_digest_v1_run1/validation_result_v1.json` accepts
the actual trace: 73 elapsed frames, 26,211,004 master clocks and 73 completed
menu NMIs during the digest call. The actual digest is
`fce4c8c9a7572926e8aaa3d8c862c10ce4454f067cfc4494a72f139794b70173`.
All 194 borrowed bytes return to zero; finalized full SRAM equals the accepted
save; protected original records, PC07, names including Epoch, compatibility,
roster/joined state and caller frames pass. The real return is pre-`$C2CF55`
with the native save-result CPU restored. The validation result SHA256 is
`1720aed3558865ada91c9c1bc6962cab3876f0a4827c8a354eefe5cb317742af`.

This is a selected native digest observation with aggregated scratch accesses,
not sidecar persistence or cold load. All non-scratch writes are individually
reconciled; intermediate scratch reads and readbacks are not independently
replayed from individual events. Lua callbacks omit CPU/DMA operation kind.
The initial Map has HDMA channels enabled, so do not claim no DMA/HDMA merely
because no new activation write was seen. The separate additive packet
`private/research/pc07_shadow_dma_context_20261015/` now closes scratch access
for this exact digest interval: all 484,408 scratch reads at 3,669 read PCs equal
the mandatory CPU byte-read counts; pinned local index/width/address contracts
cover the 23 indexed PCs and 224 immediate sigma-call producers. The recorded
unchanged A-to-B channel destinations also exclude DMA/HDMA WRAM writes.
Surplus and missing read mutations refuse. This reuses the accepted trace and
interrupt preservation; it does not recover operation-kind fields, replay
intermediate SHA values, or establish general scratch/stack ownership. Root
inspected the count-composition source. No emulator or historical validation
chain was rerun for this result.

**Accepted writer source proof, now used by the native result above.**
`private/research/pc07_native_sidecar_writer_v1_20261015/` contains the original
570-byte writer/header/metadata component at synthetic, unbound addresses.
It invalidates slot0's sidecar before native save, writes the live PC07 record,
explicit authored metadata, finalized checksum and profile-1 digest, computes
CRC16 over the final-format bytes, and commits one M8 magic byte last. It then
restores the 194 borrowed scratch bytes and full native result/return frame.
Its 318 assembled-byte host cases pass: 96 exact host-codec commits, 194
nonzero-scratch refusals, 21 entry refusals and seven later refusals. Three
damaged CRC/magic copies refuse; successful paths make exactly 165 ordered
sidecar byte writes. Root inspected the assembly and checker; a separate narrow
CRC/order source review found no concrete defect. Native save and SHA remain
explicit accepted-contract stubs in this host check. The fixed recruited
fixture and declared Tech/quest fields are not a generic gameplay implementation.
The source receipt is `source_check_v1.json`, SHA256
`207b3c23e612a2d311b50a2d084b4646977a2b3194c1e7b69c30d30a6b6dccac`.

The subsequent guarded installation and one native write observation are now
complete, as recorded above. Reuse the accepted native save, digest and writer
results while implementing the load path; repeat only the boundary changed by
that integration. The older source receipt remains source-only and unchanged.

Andrei explicitly requested fewer repeated whole-chain validations. Reuse accepted
evidence; a handoff, context compaction, documentation edit, or new reviewer does
not by itself require reproducing it. Run focused checks for changed source and
its affected boundary. Before repeating an accepted check, identify the changed
dependency, concrete failure, or new claim that requires it. Keep command output
and collaborator packets to the relevant delta. Optional review improvements are
not automatically prerequisites for the playable-character experiment.

A one-pass audit of this thread's October 14 00:00Z-02:20Z session metadata
(last event in that interval: 02:00:04Z) found 369 tool calls, six compactions,
27 named validation/audit/reproduction/checkpoint command lines and seven
invocations of three checkpoint builders. Five exact extracted command strings
occurred twice. Invocation counts do not establish success, unchanged inputs,
or a percentage of subscription quota spent hashing. Repeated model requests,
large results and carried context are the usage concern; local hashing itself
does not consume model tokens. Reuse this audit instead of repeating it.

The intent and complete-diff audits required by `AGENTS.md` still apply immediately
before actual ROM/patch emission. They do not require recursively replaying every
historical runtime proof at every development step. Prefer one qualified input
snapshot per operation and reuse its results within that operation; do not treat
cached results as current after relevant input drift. Any implementation of that
simplification must retain fail-closed write admission.

A bounded read-only review of the current writer contract, builder, launcher
and reporting adapter found no remaining historical builder/validator replay.
For the next loader packet, print a compact status and receipt path by default;
retain the full manifest/labels on disk, with verbose output only when needed.
Record validator identity from the exact source buffer executed. Optional
per-operation reuse of derived image bytes/digests can save local computation,
but is not a substantial subscription saving and does not justify reopening
the accepted writer packet. Preserve current-operation input/output checks.
No scripts, tests, hashes or emulator runs were executed for this read-only
workflow review.

**Read Red's existing work before scheduling another preview run.**
`private/red_lean_20261014/RED_LOG.md` records a completed Linux Mesen preview
continuation and points to `preview_linux_run2/coda_validator_result.json`.
Root read the log, builder, validator adapter and result metadata on October 15.
The existing run now also passes our current strengthened suffix validator:
3 frames, 809,836 master clocks, 29,586 instruction-flow checks, 8,525 WRAM
writes/readbacks, unchanged finalized SRAM, and the pre-`$C2CF7E` cut. The
accepted historical prefix was reused by exact rows, pinned receipt, CPU and
full snapshot/input identities; its historical validator was not executed.
The additive result is
`private/research/pc07_save_preview_red_reuse_20261015/reuse_result_v1.json`,
SHA256 `c03148a9395fc7ea8890404fac7b8e6185feefb1ccb7461a0c2168a384614990`.
Root inspected the current reuse/interrupt source and adapter. This closes the
bounded preview continuation without another emulator run. Persistence, MSS
restoration and production approval remain false. The original Red adapter
imports Red's modified validator, despite its stale "unchanged" docstring;
the additive result explicitly identifies the current source used instead.
The Red packet is not an exported Cowork/Grokbot conversation.

Root independently checked the specific vector correction using 12 bytes of the
accepted preserved-save image: `$FFEA -> $FF10`, `$FFEE -> $FF14`, and the two
ROM `JML` stubs reach `$000500/$000504`. The collector and validator now include
the correction, binding the exact stub, immediate hop and preserved CPU state.
Three focused tests and Lua syntax parsing pass. The revised collector has not
been executed; the accepted trace was collected by Red's version. The existing
MSS captures pass the stronger public-Map/diff checks, but have not been restored.
A new emulator run needs a concrete remaining question. The next persistence
boundary is the existing profile-01 shadow-digest design under a longer menu
transition, followed by native sidecar writing and genuine cold load.

Red's builder deliberately uses its own span/inverse audit instead of the shared
write-guard APIs required here. Preserve its artifacts and distinguish that build
provenance from runtime observations; do not adopt that bypass for future writes.
At the earlier October 15 workflow-review checkpoint, the prospective shared
preview-guard extension was still uninstalled and root had emitted no preview
image or run that continuation. The later loader installation and cold-load
result at the top of this handoff supersede that implementation status.
The completed local observer/refusal-test source work is under
`private/research/pc07_save_preview_observer_v1_20261014/`; the narrow Claude F1
test-evidence correction is under `private/reviews/20261014_save_preview_builder/`.
Their focused checks need not be repeated merely to resume this handoff.

The next original component is now assembled under
`private/research/pc07_shadow_digest_v1_20261015/`. Its 173-byte wrapper calls
the existing preservation wrapper, checks the qualified slot0 save context,
requires all 194 candidate scratch bytes to be zero, invokes the unchanged
round8 profile-01 SHA entry, exposes digest/status at a named observation label,
then restores scratch and the full native save-return CPU state. The focused
assembled-byte host check passes 405 cases and rejects three damaged copies;
the native save interior and SHA are explicit ABI stubs, not rerun correctness
proofs. Root read the wrapper and checker. That component check is source
evidence only; the later separate guarded native run is recorded above. The
nested save call adds three stack bytes. Its general physical stack/scratch
ownership is not established by the selected observation.
See its README and `source_check_v1.json` for reproduction and identities.

**Historical access check, now resolved:** Andrei subsequently identified Claude's
"Site Editing Request" and the main Grokbot thread, and the external consultation
completed. See `private/reviews/20261015_next_milestone/REVIEW_DISPOSITION.md`.
The earlier title/link request below is no longer pending.

Claude Chrome and Desktop access were restored and observed signed in again
after Andrei's confirmation. The native Windows skill reads Desktop's
actual UI; Chrome also exposes the signed-in history. Focused Epoch/Chrono,
Grokbot and Schala searches had not identified the requested Cowork discussion.
At that time, its exact title/link or opening it in Desktop was requested.
The local Red artifact review above is complete and must not be represented as
reading that conversation. No new provider request or model/billing change was
made in this access check. No native run was launched during that access/workflow
review itself; the later, separately recorded cold-load experiment is accepted
above. At that checkpoint, identifying the conversation was the remaining blocker.

## October 13 current: native save now restores its occupied staging tail

The original 85-byte preservation wrapper is now installed and has **one accepted
native Mesen run**, from the pinned pre-save MSS to the actual pre-`$C2CF55`
caller return. All ten occupied bytes `$7E98B8..$7E98C1` are restored before
the outer RTL. The native full A/X/Y, P/D/DBR and caller SP survive the wrapper.
The complete SRAM output equals the accepted ten-region save byte-for-byte,
including the relocated compatibility payload and slot0 checksum `$0B0E`.
The original seven live records, PC07, names including Epoch, roster and joined
state remain unchanged with zero observed writes. **PC07 sidecar persistence
and a genuine cold-load round trip are still incomplete.**

The run is `private/test_runs/pc07_preserved_save_table_v1_run1/`: collector64,
host0, 20,482 rows, 7,564 instruction callbacks, 2,299 writes/readbacks and
2,153 same-value writes. It observes all 39 wrapper instructions, 40 occupied-tail
bus operations and a 26-byte stack peak, with no interrupt in this selected
254,458-master-clock interval. This is one checkpoint/slot0 observation, not
general stack ownership, interrupt safety or a game-speed result. Evidence
ends before `$C2CF55` executes; the deferred stop is not a physical prevention
claim. Returned snapshots, rather than shutdown battery output, are authoritative.

Key identities:

- Image: `9c8993158843e3f4f2e7d8bc28ba7a2b4b6c6c60834c7414755a110865dff364`.
- Trace: `f7024bbcf48a7e4db593d7e768e5a0bf0687e4bb06b18f098a1e5288c35811cf`.
- Actual receipt: `23536cf4bad74f657571d510cc6d9062ca504a5f8e6f7a16619948e143553c33`.
- Root audit: `private/research/pc07_preserved_save_table_root_review_20261014/audit_v1.json`,
  SHA256 `b002a2cdec61f158f5054769848a0d8b61bae635333efd84cf14a93e56aa458c`.
- Independent audit: `private/research/pc07_preserved_save_table_independent_20261014/review_v1.json`,
  SHA256 `2c28aa4d984b116d1783c90a89ecb73ab47de6a3ac0b534536ed87d35a8f28dc`.

Root read and byte-reproduced the independent auditor. It separately reconstructs
all 187 observed stack-envelope operations, all 7,563 executed-instruction SP
transitions, the full physical memory ledger and carry-propagating checksum.
Ten corrupted actual-trace copies refuse. The two audits are offline reviews
of one native run, not repeated emulator runs. The process stdout adds ten
uninitialized-read warning addresses for the preserved tail; it has no clocks,
so individual warning timing or CPU/DMA ownership is not inferred.

The current shared guard is exactly the prior 43,102-byte source plus two
forwarders totaling 549 bytes. Both actual intent and complete-diff APIs ran before
the image was emitted: 95 changed bytes in four exact spans. Production catalogs
remain empty. The archived guard and historical adapter preserve the previous
evidence; historical checkpoint a now refuses its original live-guard pin drift.
Do not rewrite that checkpoint or call its old builder current-compatible.
The observer v1 remains frozen and unconditionally unlaunchable; separately
versioned v2 admits the exact current image, receipt, source closure and original
checkpoint. See `private/research/pc07_preserved_save_table_observer_v2_20261014/`.

The separate Claude Code builder review completed from three source snapshots.
Root checked its seven findings; no current fail-open counterexample was
reproduced. Eight additive refusal probes and the instrumented read-only default
build now pass without changing the accepted source. The actual frozen design
has four sections, a whole four-byte hook and no inherited/new bundle-path
overlap. Reporting/count and duplicate-path hardening suggestions remain useful
for future versions. See `private/reviews/20261014_preserved_save_builder/`.

The next source-only proposal installs the existing 17-byte saved-roster preview
helper at `$44:2200`. Exact `$07` becomes `$87` only in the accumulator so the
existing preview skips the unsupported row; SRAM, the roster and Epoch's name
remain untouched. This does not render Schala's save-card portrait. The proposal
has 29 changed bytes/four spans and is not emitted or admitted by a new guard.
Use `private/research/pc07_save_preview_installation_design_20261014/`; its
frozen wrapper-proof-pending wording describes its original design boundary,
while the accepted wrapper evidence above is a separate prerequisite.
The separate preview source review passed and root byte-reproduced it:
`private/research/pc07_save_preview_installation_review_20261014/review_v1.json`,
SHA256 `12532d253b0fdffb2abe046916fa0595f8c2404a3068144a2b93e4cf83c27d89`.
It independently reconstructs the exact proposed delta and verifies the helper's
two paths across byte/status/address combinations; it grants no runtime admission.
The new observer design must account for the scheduler's `$09FF` stack switch
after Sleep; the old `$0A00..$0ABF` watch range alone is insufficient. Minimal
preview continuation and a later 96-menu-NMI experiment are distinct gates.
Do not adopt the short zero-access scratch observation as long-SHA ownership.

The finalized source-only continuation plan is
`private/research/pc07_save_preview_observer_design_20261014/observer_design_v1.json`,
SHA256 `3f2f415ee3c38b80dd1841bd77d4c61c33d4b6a38cba769395a709697602e1fe`.
Root read and byte-reproduced it. It starts from the existing full pre-save MSS,
matches the accepted save boundary, and follows both Sleep calls and the three
preview ordinals to pre-`$C2CF7E`. No post-save MSS yet exists; CPU/WRAM/SRAM
snapshots cannot reconstruct one. First resume has source-conditioned P=`$23`
after PLX of zero, with volatile A, rather than unchanged pre-sleep A/P.
The packet implements no collector, launcher or native continuation.
An additive source review corrects its abbreviated label-return description:
`$C2D28C RTS` returns to `$C2D264 PLP`, then `$C2D265 RTS` reaches `$C2CF5B`.
Root verified canonical `$C2D261..$C2D265 = 20 66 D2 28 60` and `$C2D28C = 60`.
The future collector must include both intermediate boundaries and their actual
frame/status restoration. Preserve the frozen plan and checkpoint; do not copy
their shorter description as a direct `$C2D28C -> $C2CF5B` return.
The completed additive review is
`private/research/pc07_save_preview_observer_review_20261014/REVIEW_AND_ERRATA_v1.md`
(SHA256 `f82bb0ecc61a56f9e00e2729594d5e6f16e35331c183434336dd59de0c3eaccd`),
with machine-readable root disposition beside it. This closes the review marked
pending at checkpoint b's freeze without changing that historical index.

Current machine-readable index:
`private/research/pc07_progress_checkpoint_20261014b/checkpoint_v1.json`,
99,437 bytes, SHA256
`24cbc5ed2cd3a1ebd7a8bf553f41bf1db2e1b9ad372e5a942e930594f17c5b22`.
Root read and byte-reproduced its 48-pin metadata builder. It imports no project
builder/auditor and performs no ROM or emulator action. Reuse the accepted
evidence and review only new implementation or unresolved boundaries.

The goal stays active and incomplete. Later world-map art remains retail-style,
preferably deliberate/code-assisted pixel work, with Lily, Claude Desktop Code
and other appropriate collaborators consulted at that stage. No art or public
publication was performed in this save-restoration step.

## Previous October 13 checkpoint: installed ten-region save preserves serialized compatibility

The corrected table now has one actual native run from the accepted pre-save
MSS through the real pre-`$C2CF55` return. The guarded private image installs
the fifty-byte table at `$44:2000`, selects all ten regions, and copies the
relocated compatibility block `$7E2CA0..$2CEF` into slot-relative `$0430..$047F`.
PC07 is excluded from that native payload. This fixes the demonstrated original
serializer collision; it does not yet persist PC07 in its separate sidecar.

`private/test_runs/pc07_installed_save_table_v2_run1/` returned collector64/host0:
20,346 rows, 7,525 instruction callbacks, 2,100 payload bytes, 2,270 actual
writes and matching next-callback readbacks, including 2,150 same-value writes.
The full `$A00` checksum is `$0B0E` for slot0. All five metadata publications
precede native PLP/RTL. SP/P/D/DBR return correctly; native A/X/Y are
`$E402/$0000/$FFFE`. No interrupt was observed in the 253,072-master-clock
interval. All protected live records, names including Epoch, roster and joined
state remain unchanged with zero observed writes.

The 6,113,339-byte trace SHA256 is
`4ad13d1a885c7f14e944aea412175d1dfe29640e95712df1d6a77c7497618291`.
The actual receipt SHA256 is
`94cf6b70079b5545f61a4128b33a634af9c65c7088d1e71168dd931c22cb7631`.
Root reproduced the validator, input/file inventories and shared image audits
offline in `private/research/pc07_installed_save_table_root_review_20261014/`.
Its 6,224-byte report SHA256 is
`1889c12ad9f15600f1957202b1563bf209edf71115f40fbe03b0fa4b92858bd2`.
Compared with the original run, exactly 64 compatibility bytes and two checksum
bytes differ in SRAM. The 1,640-clock difference is a checkpoint comparison,
not a general performance or slowdown result. The separate independent actual
trace audit passed; root read and executed its reproducer byte-exactly. Its
28,210-byte report is
`private/research/pc07_installed_save_table_independent_20261014/review_v1.json`,
SHA256 `71f973bc9f2dd611faff8603634146cab6d34d210262ea7d9687c73d1c944144`.
Eight damaging in-memory trace corruptions refuse. This is one native run with
offline audits, not a repeated emulator pair. The ledger also accounts for
444 non-payload WRAM reads interleaved while MVN is the latest CPU instruction;
that context does not establish CPU/DMA/HDMA ownership.

The v2 builder at `private/research/pc07_installed_save_table_v2_20261014/`
reproduces the accepted original baseline and invokes both actual shared intent
and complete-diff APIs before emission. Twelve focused tests and sixteen existing
shared-guard tests passed; the observer's eight focused checks passed. The emitted
image is SHA256 `e795c34f8680b45a99f86b657e23066957e4816a481a38099b20be10bfef8908`,
with exactly 63 changed bytes in five declared spans. Production catalogs remain
empty. The old guard is preserved under that packet's `archive/` directory.
Historical checkpoint h still pins that old guard at its original path, so its
old builder now refuses live source drift; do not rewrite historical pins or
claim that historical builder runs unchanged against the new live guard.

The direct observer launch first refused on a missing Python import before any
output directory or subprocess. The additive hash-pinned `run_observer_v3.py`
supplies exact import roots; its inert qualification and actual launch passed.
It changes no collector or validation predicate. The launch manifest SHA256 is
`debf9be12b1b8df383632815e3ba1c0204d3b739dfa8dc3cdb2fe197d914644d`.

The extra occupied staging bytes `$98B8..$98C1` change from
`00abcebcbcba00363f00` to `90020011007c2c7e1e00` and remain overwritten at the
cut. They must be restored before a supported continuation. The separate original
85-byte wrapper in `private/research/pc07_save_staging_preservation_20261014/`
uses five stack words and preserves the native returned full A/X/Y, original
P/SP and outer RTL. D/DBR pass through from the native routine; equality with the
original values depends on its qualified contract. The supplementary Claude Code
review completed under `private/reviews/20261014_save_staging_wrapper/`, finding
no wrapper blocker under the declared premises and identifying checker gaps.
Root independently reproduced those gaps and the additive v2 checks: 4,201
positive cases, 224 mutation/status cases and four synthetic boundary faults.
In particular, deleting pre-call flag restoration passes the captured `$A1`
case but fails the sixteen qualified statuses with Z set. The original 85-byte
assembly and v1 packet remain unchanged. This is source evidence with an
explicitly stubbed serializer interior, not native wrapper execution. Its
conditional 26-byte full-source stack peak is not physical ownership or
interrupt admission. The wrapper is not installed. The prior unrelated
save-body review timeout remains preserved without an attributed approval.

The next observer's frozen source packet is
`private/research/pc07_preserved_save_table_observer_v1_20261014/`. Its seven
focused checks and Lua parse passed; the separate source review closed two
identified gaps before freezing. Its launcher qualification unconditionally
refuses: no wrapper guard or runtime admission exists yet. The historical
baseline adapter at `private/research/pc07_preserved_save_table_builder_v1_20261014/`
also passes seven focused checks and root's byte-exact reproduction. It resolves
only the exact archived guard role, retaining all other source pins. Historical
guard results are preserved evidence, not freshly executed by that adapter.
Next, implement the narrow current shared guard, audit the complete 95-byte
wrapper delta, then version and admit the observer against the actual build.

The current compact machine index is
`private/research/pc07_progress_checkpoint_20261014a/checkpoint_v1.json`:
18,770 bytes, SHA256
`5bff635f4ba9687e5db9eb144588e38e95678531d05d717cefea48debf8267fe`.
Its source reproducer verifies 24 pinned inputs without launching an emulator or
emitting an image. This remains one installed-table native run with offline
audits; the wrapper, observer and future persistence preparations are separate.

The warning log has the same length as the original run but different bytes.
Both have 2,421 unique warning addresses; the new one removes exactly
`$7E2830..$287F` and adds exactly `$7E2CA0..$2CEF`. Of the current addresses,
2,363 also occur in interval reads and 58 do not. No individual warning-to-trace
timing attribution or warning-free claim is made. All SRAM,
ROMs, states and traces remain private and disposable. Preview, staging
restoration, SHA/sidecar commit, cold-load, NG+ and erase remain separate gates.
The goal is active and incomplete. No new GitHub/GitLab/portfolio publication
occurred. World-map art remains a later retail-style, code-assisted task with
Lily, Claude Desktop Code and the other collaborators consulted at that stage.

### Prior accepted original eight-region save observation

The unchanged original eight-region save now has a bounded native observation
from the accepted pre-`$C2CF51` MSS through actual pre-`$C2CF55`. The hidden,
isolated run returned collector64/host0. Its 20,202 rows cover 7,475 actual
instruction callbacks, all 2,100 serialized bytes, full `$A00` checksum reads,
five final SRAM metadata bytes, and the actual PHP/PLP/RTL return. All 2,242
observed writes have next-callback readbacks; 2,073 are same-value writes.
The selected slot0 checksum is `$FBED`. SP/P/D/DBR are restored; A/X/Y need
not be preserved. No interrupt occurred in the 251,432-master-clock interval.
Do not promote the source-tested interrupt branches to native evidence here.

The run is `private/test_runs/pc07_native_save_body_v1_run1/`; its 6,071,777-byte
trace hashes to
`1d317fc00b0602f2639e089e2accb0934929c5d875029f878526f6374d7c0612`.
The launch manifest is 7,836 bytes, SHA256
`16bdd900021c35abdf01c8dbc93131237de7cbb27bf039f25ef35e89b212fe02`.
Root reran the reviewed validator offline, checked the full recorded file
inventory and unchanged inputs, and added exact candidate-range observations.
That 14,104-byte audit is
`private/research/pc07_native_save_body_v1_run1_review_20261013/audit_v1.json`,
SHA256 `276d33e0c6afd787cf644305cfbfc020a508b09eb2df7200b70e8ee55c865d4e`.
It is one actual run with offline result verification, not a repeated native pair.

All seven original live records, the 80-byte PC07 record, relocated compatibility
data, roster/joined state and all 48 name bytes including Epoch remain unchanged
with zero observed writes. The original serializer still puts PC07 into the
vanilla compatibility position and omits the relocated block. Its resulting SRAM
is incompatible and disposable; supported PC07 persistence and cold-load remain
open. The cutoff excludes later sleep/preview, but deferred stop does not
physically prevent later execution. Shutdown battery/CDL are not that evidence.

The ten extra staging bytes `$7E98B8..$98C1` are **nonzero**, identical at all seven
snapshots, and have no observed reads or writes in this interval. Their preimage
SHA256 is `5e054e374f2eec8b38c93f91dd14aecedcefc1082f4c4921ca7a1ad35f4fca34`.
The 194-byte `$AE00..$AEC1` candidate and its eight-byte guards remain zero with
no observed access. None of this proves post-return ownership or the longer
SHA transition's lifetime. Preserve the occupied staging preimage rather than
assuming blank/free storage.

The next save-only source candidate is
`private/research/pc07_installed_save_table_v1_20261013/`: the existing ten-entry
table at the named private candidate `$44:2000`, two exact save instruction
spans, and checksum pairs. Its in-memory target has 63 changed bytes; eleven
focused construction/refusal tests passed. No new image was emitted. The frozen
v1 emitter is deliberately unavailable: a separately numbered adapter must bind
and reproduce the accepted baseline and expose both narrowly scoped shared
write-guard APIs. Preview, load, SHA and sidecar integration remain absent.
Do not repeat the completed full field/battle acquisition or this baseline.

The independent actual-trace review is
`private/research/pc07_native_save_body_independent_run1_review_20261013/review_v1.json`,
25,236 bytes, SHA256
`8765fb60a8d957dbb3b3bca8c72fd92b4770ebc5c96fbdc7721c480177e9ef2d`.
Root read and reproduced its source. Its separate byte ledger/checksum agree;
all six deliberately corrupted in-memory trace copies refuse. The 80 actual
PC07 copy/readback triples change 64 bytes of the old serialized compatibility
span. These are offline checks of the same single native run.

The process log contains uninitialized-read warnings and is byte-identical to
the earlier checkpoint replay's log. It has no trace clock or row attribution;
address matches cannot place a warning inside or outside the accepted interval.
Do not describe the run as warning-free or assign every warning to post-cut code.

Local source review and component tests preceded the run. The supplementary
Claude Code source review was pending at launch, then timed out after 900 seconds
with delivery/completion uncertain and no answer or partial answer. No external
approval is claimed, and no retry or paid fallback was used. The final result
and disposition are under `private/reviews/20261013_native_save_body/`; preserve
the earlier source-review receipt's truthful pending-at-launch state.
The compact current machine index is
`private/research/pc07_progress_checkpoint_20261013h/checkpoint_v1.json`.
The active goal remains incomplete. The current local result is not a new
GitHub/GitLab/portfolio publication.

### Completed checkpoint acquisition and one-instruction replay

The post-battle route now reaches a real pre-save checkpoint, and a fresh Mesen
process restores that MSS with exact CPU, WRAM and SRAM equality. The native
JSL at `$C2CF51` then reaches pre-PHP `$FFF9FB` with all three actual stack
writes and the correct live return frame. Root reproduced both independent
audits. This closes checkpoint acquisition and its one-instruction replay;
normal PC07 save/cold-load remains open. Reuse this MSS rather than repeating
the full battle, escape and field route.

The compact machine index is
`private/research/pc07_progress_checkpoint_20261013g/checkpoint_v1.json`,
7,793 bytes, SHA256
`b489fb98118eab63128ab0159c694f53b04d67c40fbf6c274a4818f9565f7758`.
Its builder rechecks the pinned receipts without rerunning an emulator or the
full acquisition audit. The old failed collectors and host receipts remain
unchanged. The next observation's evidence must end at pre-`$C2CF55` unless a
separately qualified continuation is supplied: the older 96-menu-NMI proposal
would eventually reach the still-unadapted serialized-PC07 preview at `$C2CF58`.
An evidence cutoff does not make Mesen's deferred stop an immediate CPU halt.

The narrowed source-only next-step packet is
`private/research/pc07_native_save_body_design_20261013/design_v1.json`,
10,480 bytes, SHA256
`7f215ca9cf2ca862ddd879a2a566bbbf98e20f44bf51ead22d97502f206e7dd5`.
Root read its note and reproduced all 15 source pins, three private-input pins,
four canonical/current-image spans and eight original descriptors. The restored
caller's `$AE00..$AEC1` candidate is exactly 194 zero bytes, but post-save contents
and access lifetime remain unobserved. The current original eight-region save
would copy live PC07 into vanilla's serialized compatibility position; its
output must remain disposable. This next packet installs no observer, SHA,
ten-region table, preview adapter or persistent sidecar. It reuses existing
physical-WRAM callback primitives instead of repeating their prior proofs.

### Guarded image and acquisition history

The next private diagnostic is now built, after independent compiler/recipe
review and shared intent plus complete-diff audits. It adds a native confirm
exit after the accepted battle/movement route, returning to the installed
event125 save point at location `$01DA`, tile `$0B,$3C`, arrival `$03`.
This is authored diagnostic behavior, not a discovered retail exit. The first
new emulator attempt is now preserved as a rejected pilot: its collector
misclassified an initializer write to the shared event-flag byte. That first
attempt supplied no save-entry checkpoint, normal save or cold-load result. The separate v2
observer correction is source-reviewed. Its first native attempt passed the
old refusal location but timed out in `savepoint-wait`; its 44 snapshots end
at `savepoint_ready`, with no menu or output MSS. The image and all frozen
sources stay unchanged. The input-phase diagnosis is reproduced; the separate
v3 point-hold attempt reached the native save overlay, then refused the first
serialized-preview read. It has 45 snapshots and no output checkpoint. The
observer's CPU SRAM-window versus physical-offset calculation has a separately
reviewed v4 correction. Its first hidden native attempt passed the host checks
and captured a real pre-C2CF51 MSS. Independent acceptance now passes and root
reproduced it exactly. The original auditor found three tuple/list
representation differences, with identical values; a separate strict-JSON
comparison correction preserves every gameplay predicate. The fresh MSS replay
is now separately accepted below; the save body and genuine cold loading remain
separate obligations.

The exact event126 compiler replaces its idle B2 at script `$0556` with
`31 06 DF DA 07 0B 3C 11 08`. The packet grows 1,917 to 1,925 bytes; 95 of
240 pointer words relocate by eight, all aliases and 97 existing relative
branches remain exact, and the complete inverse restores the accepted packet.
The ordinary five-command object-slice quota bounds this SEC-returning wait
loop. Both initial126 and return126 must use the same new packet; event125
remains unchanged. Decoded126 SHA256 is
`75990bc5522be5b153461f67b35dcbdbf77da98284f00c52a2cc24962af8be40`;
its 2,172-byte encoding hashes to
`71960d5b5a1694315d130c05224fb5cdbeb70492b276e81fc1c3c73cbb61119a`.

The new image is
`private/test_runs/pc07_native_save_transition_diagnostic_v1/diagnostic.sfc`,
8 MiB, SHA256
`144a374d0074734bab2f5f5d122ade9d5d825f77529094dbeb7c24ac67a9c264`.
Its emitted receipt SHA256 is
`a9cbbae85eef90d3229b230d141d7662d45d07f6fccda0637e5c67ab89816aea`.
The 45-source build bundle is
`a922bdec1a64f33bbb98caa93afd50d306c42bd03ed7fa85ca572ffdd47fc346`.
There are 37 declared disjoint sections, 5,516 changed bytes from the inert
scaffold, checksum `$11C1`, and two fresh matching helper assemblies. Relative
to the accepted old native-event image, only event126's encoded interval and
the two checksum pairs differ. This still uses the earlier donor appearance;
the separate successful Schala presentation has not been combined with it.

The source and independently reviewed construction are in
`private/research/pc07_native_save_transition_transform_20261013/` and
`private/research/pc07_native_save_transition_design_20261013/`. Root inspected
and reproduced the independent compiler/recipe receipts. Six compiler tests,
nine source-resolution tests and 21 new contract/builder tests passed. Both
compiler and independent inverse checks reject a mutation at every output byte.
These are construction and refusal checks, not new native playability evidence.

The shared guard has a separate 557-byte pair of deferred APIs for this exact
recipe. Exact byte/AST excision restores the archived guard; old APIs, source
kinds and empty production catalogs are unchanged. Current guard SHA256 is
`78856072fc9f698853cb0c16e5294750d0390ca1b0181eb9428571427280fe01`.
The old default runtime audit correctly refuses this changed live hash. Use
`private/research/pc07_native_save_transition_guard_review_20261013/historical_runtime_wrapper_v1.py`
for an explicitly requested historical replay. Root executed it once after
this source change: the entire original 30,201-byte independent runtime report
was byte-identical, retaining SHA256
`fb9217c9cc01904a7681f29c0e227aa9742fd3f343b481007b461113e21c9a4b`.
There was no native rerun. The original quarantined v1 receipt stays unchanged.

The separately reviewed `image_source_support_v1.py` in that guard-review
folder composes the old 255-row/39-row source sets with the new 45-row image
bundle. It binds the current builder to a separately loaded current guard;
the historical builder retains its archived guard. Only one exact import
changes, with all builder functions preserved. Its read-only image
qualification and 13 independent refusal checks pass. Do not import the new
builder against the historical canonical module name without that separation.

The source-only save-entry design is
`private/research/pc07_pre_save_capture_design_20261013/`. Direct native C840
opens mode6/screen0B; selected initial previews read unchanged vanilla SRAM
identities rather than live07. The two encountered live07 mask lookups are
locally neutral under their explicit FE-mask premises. This is conditional
source admission, not general PC07 menu support. The mandatory shell also
recalculates records00..06: exactly 13 source-paired live publications per
record, 91 total, must be observed and reconciled. Whole-record equality must
not be weakened without that ledger. Full menu1, the later07 serialized preview,
and save/cold-load adapters remain outside this admission.

The frozen source-only collector is in
`private/research/pc07_native_save_entry_observer_20261013/`. Its declared
protocol retains the old38 snapshots and adds nine, with four native loads
125/126/126/125, fresh scene3, nine field helpers, the same171 preparation pairs
and zero new debugger edits. It retires completed phase callbacks explicitly,
observes the real save-point permission and direct overlay, and captures an
actual MSS before `$C2CF51`. Root reproduced its 5,717-byte source preflight,
SHA256 `47fc9174a61e59461a11e9ea38b38202bdbe47894eb81379a33cfada361ec3da`,
including both exact derivations, three construction/refusal tests and pinned
Lua parse-only compilation of both chunks. The source bundle is
`546583e9f9a13327b45922cb59530d4f4b6d1a230a60297f4480e3d4c23257de`.
The collector requires a separate release-qualified overwrite confirmation
and actual affirmative branch; every stat-copy source read owns its native
instruction. These are source checks, not native observations.

The frozen host validator and isolated launcher are under
`private/research/pc07_native_save_entry_host_20261013/`. Root's prefix adapter
uses 16 count-checked source edits with a complete inverse, original row
objects and honest control-subproof boundaries. Its 15 focused tests pass.
The separate four-load native component has 17 passing tests; it retains the
accepted inherited-I relation and InitBlock only on loads1/2/4. Five launcher
tests pass, including immediate pre-launch readback of copied inputs, runtime
and initial disposable battery. The separate suffix's ten tests and bounded
independent review now pass. Root's combined preflight passed all47 tests,
both Lua checks and current guarded-image/input qualification. Its 64,657-byte
receipt has SHA256
`e844ef27a3369c356e64c39f0d66d388e94f5bfc888a6113b39bab01c918d2a4`;
the frozen host bundle is
`2728f2ba373f98a1ab17dbfabc7f777b6d5b9b866f206bb4b422c0bfc6d584a6`.
The inert 56,258-byte launch plan hashes to
`bd23f04fb0748e116df51eb864e17255cebace187913d3cdc2688759420cf289`.
The first new native attempt stopped with collector code91 under
`private/test_runs/pc07_native_save_entry_v1_run1`. Its 89,205-byte receipt hashes
to `273fb7ec08d018adc3050503cc3ced953e8a9b753ed0a822e87539574bcf3845`.
Its 171,672,030-byte trace contains 504,052 rows and hashes to
`4163f7128c49c3f6764fa54eeef9eba3da2a2cb20af6da90ae4d41dbe9a3ca39`.
There are 42 snapshot pairs through the fourth native pointer install, but no
field-ready endpoint, save overlay or `pre_save_caller.mss`. The terminal
`$C06B9C` prewrite sets bit `$40` through object0's `65 86 CF` initializer
(script `$01F3`, store Y=`$01F5`), not object14's `65 87 CF` permission operation
(script `$09E4`, store Y=`$09E6`). The generic bit-writer's mask table supports
both. Row504051 has no next-execution readback because the observer refused
before queuing one. Never retrospectively accept that write or the failed run.
The bounded reuse assessment is now independently reproduced by root with
exact 53,602-byte equality, SHA256
`08bf6c1b69c42b1ea95d423b3956e1cc0230754eb659afe5e7f5e6222e367345`, under
`private/research/pc07_native_save_entry_run1_assessment_20261013/`.
The unchanged original 487,740-row/38-snapshot prefix passes; unchanged finite
native primitives pass all four loads and installations1/2/4. All42 SRAM and
stored-name snapshots are preserved. The four added snapshots retain records,
roster, compatibility and guards. This does not supply the missing native
completion row, scene3 helper acceptance, save permission or output checkpoint.
The separate two-class source correction is frozen under
`private/research/pc07_native_save_entry_observer_v2_20261013/`. Its source
receipt is 6,126 bytes, SHA256
`8c42453b0c020e0440feedacb493817bcae1028e813ad8f9c283d483b7ded33f`.
Both initializer and permission writes now require their own source context
and next-exec readback; only object14/mask80 can arm permission. The host
also binds native opcode/selector/target reads, OR/store and caller frame to
one observed command invocation. Interrupt gaps remain allowed. The independent
10,603-byte source review hashes to
`08af7e468afc7be27ce85c2220d18d4d0a13de01a2cf3e1d15cecfb0e0f5033b`;
root read its source and reproduced it exactly. Ten focused correction tests
pass, including the explicitly synthetic continuation of the failed prewrite.

The separate host v2 is at
`private/research/pc07_native_save_entry_host_v2_20261013/`. It reuses the frozen
host sources with exact counted inverses: the validator changes only its suffix
path/name; the launcher changes two imports and three file selections. Root
reproduced the independent structural review and exact two-constant seal
addendum. Eight host tests pass. Combined source/input qualification and both
Lua chunks pass; unchanged component suites were not repeated. The 71,246-byte
preflight hashes to
`7164a926a98f064915bd11fe54b05008ec7f4fda5fbf5d741af0c77f59abba25`.
Its frozen source bundle is
`bf3602c1cfd5ade1bfb2de880b5c338817c1002d9a93d487f1c496ef581033aa`;
the 62,842-byte inert plan hashes to
`4207a205d1075ec32e6ba8f57635a419a5c129777ca0e84770c9f946afab1a33`.
The first v2 native attempt at
`private/test_runs/pc07_native_save_entry_v2_run1` is quarantined, collector91.
It reached the declared clock bound at poll7243, clock3464000988, in
`savepoint-wait` (collector line1735). Its 96,653-byte receipt hashes to
`c8249182446111aacb669819c30679c90c758a8f4cb624ffbe1d1ef58f032a50`;
its 459,330,559-byte/1,361,974-row trace hashes to
`2a2b771e8429779d35b4f56fa8085019e2e44df00c3508047af0bdcaca35b5be`.
There are 44 snapshot pairs, ending at `savepoint_ready`, and only the input
`entry.mss`. No output checkpoint exists. The unchanged independent auditor
took only its refusal-inventory branch, verifying all271 source identities,
150 artifacts,12 original inputs,13 staged inputs and six runtime files.
Its 8,896-byte report hashes to
`6a4c09870fa9e3044cd032ed1531b1673161fc22ad3dbcba2f8bb29d38f75457` under
`private/research/pc07_native_save_entry_v2_run1_review_20261013/`.
Root read the complete auditor and reproduced its report byte-for-byte.
No complete composite acceptance was rerun or weakened.

The bounded input-phase diagnosis is now independently reproduced by root:
`private/research/pc07_savepoint_input_phase_v1_20261013/correlation_v1.json`,
42,294 bytes, SHA256
`b776acc7977a78772888d78af8b1517006b1fc38caeffe05959a1dc8b02d6b63`.
Root read its complete correlator, streaming scanner, source reviewer and note.
The selected producer proves `$00F8` is remapped held input; `$00F6` is the
remapped fresh-press input. Our earlier pressed-edge interpretation was wrong;
the original `EventCmd_IfPressed80` label stays unchanged (see MAP-012).
Ready occurs at poll4887. Actual A inputs on4889/4890 produce `$F8=$80`,
with native final-remap writes and next-exec readbacks. Poll4891 clears it
at row511373 before the first actual object14/Y09D2 confirm read, row511523.
All589 selected confirm reads are zero, with their own observed skip03 and
next-opcode10. The coordinate path succeeds; permission is not confirm-test
readiness. Eight commands intervene, under the five-command slice quota.
Functions1..15 point to `$09F7`/return; the selected C840 route is the
autonomous coordinate/input loop. The smallest next candidate extends only
the point A hold from two to three polls. It would cover the recorded first
test but still needs a new native observation. Delay2, the menu-release guard,
slot and overwrite inputs, image, events and fixture remain unchanged. The
menu guard stops further point assertions at the next controller callback;
it does not retroactively clear input already sampled during a poll.
This diagnosis accepts no additional lifecycle endpoint.

The separate v3 observer extends only the point hold2 to3, with the matching
suffix input replay. Its 8,360-byte source receipt has SHA256
`6214cd0f459dc0b1a23ce3be185fde31972c9cf29e0eee8dfa609a98c2c79f75`.
Root read the complete derivation, tests, source checker and note. The combined
host preflight executes eight focused input tests, eight host tests, both Lua
parse checks and unchanged image/input qualification; it reproduces that
observer receipt exactly. The 75,468-byte combined receipt has SHA256
`b91a81553d807e0994f3893ccbd2e697752f10da6d68f16237ec69e88a297a1f`.
The 290-source bundle is
`4d1f590b993d977b8229601d2e4a81e17272f7db90f94e6fccb63066a80d6ddc`;
its inert 67,035-byte launch plan hashes to
`62e44e0e2d626ff2c8087e3c87233e55db42bbdbc8798697708b28fa5773d1c2`.
The independent routing/source review passes and root reproduced its complete
6,240-byte receipt, SHA256
`7eaf9036af35a595873798a53b7929704d026e8d2c3a77e2dabbab3ff5a837cf`,
under `private/research/pc07_native_save_entry_host_v3_review_20261013/`.
Root's reviewed-bundle launch and final review-receipt sealing were separate
actions; do not imply that sealing preceded or authorized the launch. The
completed hidden process is at `private/test_runs/pc07_native_save_entry_v3_run1`.
Collector91 stops at line1861, `native serialized preview domain`, row531453,
poll4901, clock2627237766. The 101,286-byte receipt has SHA256
`911ba858b3b83513ef6acea376a3d3ff0e4cd037f34d970c8cc157383277d0b6`;
the 180,797,119-byte trace has SHA256
`6c17a2ecca3e10e76d40be52266d8ea1e14a507dd1807e6f99148b01bb323bf9`.
Its 45 snapshot pairs end at `save_overlay_entry`; there is no shell snapshot
or output MSS. The unchanged prepared independent auditor executed only its
refusal-inventory branch. Root reproduced that 8,940-byte report exactly,
SHA256 `8d2bdd324f684b21a4055e63f11825acea5273e00a5f481758154356614c3d95`,
under `private/research/pc07_native_save_entry_v3_run1_review_20261013/`.
All290 source identities,153 artifacts,12 original inputs,13 staged inputs
and six runtime files match. No complete or partial lifecycle acceptance was
rerun by this inventory. The failed preview site has X=$6000, which includes
the CPU SRAM-window base; the observer currently treats it as a physical
offset. Bind the source-derived slot/party domain before correcting that
predicate. The refused callback emitted no `save-preview-read` row; never
invent its unrecorded physical address or value from the expected mapping.
The bounded preview diagnosis is now independently reproduced by root:
20,602 bytes, SHA256
`f0dafa60663c867d48a147181a38f379b7d6a76da8745c3fa74b8a1e3d5b099b`,
under `private/research/pc07_save_preview_domain_diagnosis_20261013/`.
The finite X domain is6000/6A00/7400 plus ordinal0..2. Preserve CPU address
300580+X; physical offset is0580+X-6000. The existing07/08..7F refusal and
source-byte equality remain mandatory. Mesen's ExHiROM bank30 mapping has a
non-strict-board premise; this is no hardware-board compatibility proof.
See MAP-013. The separately numbered v4 correction is frozen; none of the
v1/v2/v3 sources or failed runs is rewritten. Its 14,684-byte source preflight
hashes to `51dc6544a0140476f5c43a64a630b8b1fb656fb64ff146ef8a7d9b9e9845632f`.
Eight focused observer tests include 36 actual Lua assertion cases. Root's
combined preflight also passes eight host tests, both Lua parse checks and
unchanged image/input qualification. That 82,194-byte receipt hashes to
`37b833a573d470311ce63db18d8f66bc885803456d88406387ef314a06e133ff`;
its 321-source bundle is
`3b089e896532081912f8b4cd5a1e45344d57b55a7579da4e79df684643e721d3`.
The six host derivatives have position-specific complete inverses that retain
preexisting original `observer_v4` references. The new collector/suffix and
original native observer/validator have separate module paths and scopes.
Root inspected and reproduced the independent 6,983-byte routing/source review,
SHA256 `a04e265cbd0a686299f0cbfe21985da082d72ce612269971f465b49037a341fb`,
under `private/research/pc07_native_save_entry_host_v4_review_20261013/` before
launching `private/test_runs/pc07_native_save_entry_v4_run1`. The input schedule,
47-snapshot acceptance, four loads, nine helpers, 91 stat publications and
pre-C2CF51 cut remain unchanged. The terminal auditor is an exact reversible
derivative of the frozen v3 auditor; its preparation alone accepts no run.

V4 completed with collector63/host0: 545,168 rows, 47 snapshot pairs and a
136,508-byte MSS. The 134,608-byte run receipt hashes to
`c9ea0c53258839b05844c01bf63dc209edfd223598ebae2062818f72ef8d5bf6`;
the 185,424,548-byte trace hashes to
`1b42e25e3c2d65e92fe5045e761a20cf0133154fe11cbf9e6ac2258ad4622079`.
The checkpoint hashes to
`50921dea6ea04811def9f62fe272e981501d7d293778a067ac551a764c1db586`.
Its actual cut is row545167, poll4921, clock2634115130, pre-C2CF51 with
SP0A7B, ACFFF, PS A1, X0/Y1, D0/DBR7E/native mode. The nine serialized preview
reads and two neutral live07 mask reads are now observed. The separate final
independent review is
`private/research/pc07_native_save_entry_v4_run1_review_20261013/review_v4.json`,
89,525 bytes, SHA256
`5e66af744a5021099aa7341dfeb8b3ee8880a5d43efab9dd9301e2c7f8c1853d`.
Root read the exact reversible comparison correction and reproduced the full
accepted review byte-for-byte. All321 sources,159 artifacts,12 original
inputs,13 staged inputs and six runtime files match. Both source-owned flag
writers and all91 stat source/store/readback triples pass. Records00/01 change
only offsets3D/3F/40 under that recalculation, without HP changes;02..06 remain
unchanged. PC07, all48 stored name bytes including Epoch and all47 SRAM
snapshots remain preserved. The failed original reviewer and its tuple/list
diagnosis remain unchanged; neither the trace nor a game predicate was altered.

The fresh replay at `private/test_runs/pc07_pre_save_replay_v1_run1` completed
with native collector64. Its eight-row trace is 2,876 bytes, SHA256
`3c49ec757bfaf36eef0598e80fe92712d689bd4ac3e3261d56e010ae0b125492`.
Immediately after the one MSS load, CPU/full WRAM/SRAM matched. The natural
JSL wrote C2/CF/54 at physical 0A7B/0A7A/0A79 and reached the actual FFF9FB
pre-PHP callback 54 master clocks later, SP0A78. Two writes were same-value;
the complete WRAM difference contains exactly one changed byte. SRAM stayed
unchanged. The frame54CFC2 is live at this boundary. This is restored-caller
equality plus the source-derived one-instruction transformation, not comparison
with an originally measured FFF9FB entry. No second C2CF51 callback is claimed;
instruction bytes/mappings are debugger readbacks, not Lua opcode-fetch rows.

The original host receipt remains `quarantined-failure` because its final file
inventory omitted six emulator-generated outputs. Its 11,681-byte identity is
`5b1ba09c2ddd8ea0767ea52cd05dd361a00b40f4b3b3749fd34d7aa7abcd67ea`.
The separate additive audit is
`private/research/pc07_pre_save_replay_v1_run1_review_20261013/audit_v1.json`,
12,025 bytes, SHA256
`61baea172358efcd860e7c4f196234c29b6e024fc86d392b4188e74b196d273f`.
Root inspected the auditor and all eight rows and reproduced the result exactly.
The unchanged native validator passes, with an exact 29-file inventory, original
and staged inputs, 15 source identities and six runtime files rechecked before
and after analysis. The five BSX startup files match pinned upstream resources;
the CDL has its source-aligned header, image CRC and 8 MiB coverage extent. Only
those six exact paths and hashes are admitted. The provenance receipt is
`private/research/pc07_pre_save_replay_generated_files_20261013/provenance_v1.json`,
11,387 bytes, SHA256
`00c461d903c219c0fd512b3aae9d0a4ca12c0e1e906c25698954cb3c9484ea76`;
root read its source and reproduced it. Generated coverage and the changed
shutdown battery are not authoritative pre-cut evidence or a native save result.
No acquisition or replay rerun was needed to correct the host inventory.

Full source composition
had no fabricated positive game fixture before launch. Compatibility rock-cache writes
have their three source-qualified writers and snapshot reconciliation; unlike
the91 stat publications, they have no dedicated next-exec readback rows.
Do not reuse old terminal snapshots as a resumable MSS.

The normal save/cold-load objective remains active and incomplete. The selected
longer private profile01 transition remains the persistence direction. No
production allocation, new publication or world-map art is approved by these
diagnostics. Schala's later world-map sprites must match the retail cast's
style. Favor deliberate/code-assisted pixel work; consult Lily, Claude Desktop
Code and other relevant collaborators on the best route at that art stage.

## October 13 current: native events, PC07 Attack, escape and field movement

The selected native `$0125/$0126/$0126` route now passes independent runtime
review through ordinary Attack, escape, both live-record commits, native field
restoration and individual movement. Root reproduced the separate runtime audit
byte for byte. The completed single run is
`private/test_runs/pc07_native_event_full_route_v1_run1`: collector exit 63,
487,407 trace rows and 38 WRAM/SRAM snapshot pairs. Its final evidence cut is
before the actual `$C000A7` instruction at poll 4,843, master clock 2,606,239,604,
after 64 Right polls and 32 neutral polls. Deferred stop execution is excluded.

All three event loads come from the unchanged guarded expanded-ROM image.
Both `$0126` loads use the same 1,917-byte event; `$0125` has 2,553 bytes. The
21,151 selected native event-bus observations include 6,933 physical WRAM writes
with next-instruction readbacks. The initial two loads install native function 0
pointers and priorities; the third preserves the restored live pointers and
returns through its actual `$032F` near frame to `$C00330`, without InitBlock.
All six selected role/graphics helper calls complete. This image still uses the
earlier Crono donor appearance; the separate Schala presentation is unchanged
and has not yet been combined with this full route.

The observed Attack belongs to active slot 2/logical PC07, participants
`07 FF FF`: selected enemy HP changes 8,000 to 7,038, PC07 MP remains 93, native
cleanup returns to `$C18603`, and the actor becomes ready again. The authored
escape condition is diagnostic, not a claim about retail Lavos escape rules.
Both 240-byte work-to-live commits and both 5,344-byte field backup/restore
ledgers reconcile with their actual callers. The original battle CPU context
returns through `$C018AB`, the field transition reaches `$C018CD`, and the
actual near return reaches `$C000A7`.

Each actor's own asynchronous op02 call publishes priority 6/function 15 before
its own first B0 dispatch and return. Each call has 17 bus bytes and seven write
readbacks; no artificial all-calls-before-first-B0 order is imposed. All 4,103
watched control writes have readbacks. Logical 00/01/07 move 64/49/34 pixels in
physical world coordinates, with unchanged Y and a native follower 2
history/velocity/world-write chain. Correct trailing formation and general
terrain/collision behavior remain unproved.

Exactly 171 explicit fixture-preparation pairs remain: compatibility 80,
independent PC07 record 80, roster 9, joined 1 and cursor-policy 1. There are zero
debugger event/length or CPU-register edits. All seven original identities
remain; active 00/01 and 07 receive the observed native commits rather than
remaining bitwise unchanged. Reserve 02..06 records, all 48 stored name bytes
including Epoch, all 38 SRAM snapshots, compatibility endpoints and declared
guards are preserved. Epoch-name preservation does not establish vehicle
playability. Recruitment without fixture preparation and normal save/cold-load
remain open.

### Preserved host rejection and separately accepted correction

The original run receipt remains `quarantined-failure`, SHA256
`b91c3ac07a58148728b8935f867f92bcb0089f90ddeed31eaa8f7878b3aa0629`.
Its frozen host incorrectly required final loader P=`$27` for all three loads.
The selected canonical source instead preserves incoming I, giving exactly
`$23 | (entryP & $04)` under the explicit native/decimal-clear premises.
Actual transitions are `$26->$27`, `$24->$27`, `$21->$23`. The source proof
checks 167 canonical instruction starts and 64 status/event cases. A separate
offline v2 adapter keeps every other final status bit exact and all original
native obligations; five focused correction tests pass. No native rerun or
original source/trace modification was needed.

The additive offline assessment is
`private/research/pc07_native_event_full_route_validation_v2_20261013/assessment_02.json`,
SHA256 `e1d44720ef6ebce58dc35a7733c279819ce3ce6d5a2bf5fe686771daaa73354e`.
The independent runtime review is
`private/research/pc07_native_event_full_route_runtime_review_20261013/review_v1.json`,
SHA256 `fb9217c9cc01904a7681f29c0e227aa9742fd3f343b481007b461113e21c9a4b`.
It requalifies all 255 source rows, 131 receipt-listed artifacts, 12 original
inputs, 13 staged inputs and six isolated runtime files; reproduces the original
refusal; and checks the native loads, action, copies, returns, control and
preservation independently. Root reproduction is recorded beside each packet.
The trace SHA256 is
`283748db647f45b5d8ff80fc7294049c6ce9b22ee0f9e39f0bcfbc37c44ec21c`.
Use the read-only auditors to reproduce this evidence, not another game run.

The human/machine checkpoint is
`private/research/pc07_progress_checkpoint_20261013f/`. Its metadata JSON is
28,638 bytes, SHA256
`a0b91ffdf3c2ef60f9faa06a45b48e950f5cdc8ac43da3eae718ecbc9fda2379`.
Root inspected and reproduced its metadata builder byte for byte. That small
reproducer checks the accepted receipts and selected snapshots without rerunning
the emulator, full audit or earlier proof suites.

### Next: a native route to an eligible save interaction

The current field endpoint is not yet a save-capable checkpoint. Both terminal
control snapshots have location `$01DB`, `$0110=01`, `$011F=01`, `$0162=00`,
and `$7F01CE=$4001`. The installed event's inherited object 0 command 4A at
script `$01F3` sets the menu lock `$0110`; E301 at `$0554` enables exploration
through `$011F` only. Canonical `$C01939..C0193D` therefore rejects main-menu
entry. Independently, the location/permission inputs derive `$0D34=FFFF` and
the normal-menu Save bit `$40` refusal. These are selected source/snapshot facts,
not a complete exit-map survey or a new capture of the lock's write history.

The source-reviewed preparation is
`private/research/pc07_natural_save_route_20261013/route_preparation_v1.json`,
SHA256 `eb80e17558dfd173abb5971640a78cc4ca3a24aa6a733fa6a3183b9b8a165b55`.
Root reproduced it byte for byte. Resume with a separately authored native
field/save-capable transition, preferably reconnecting to the installed
event125/save-point environment after proving destination, coordinates,
object lifecycle and save interaction. The historical savepoint A-pulse
schedule is not an established route from this endpoint. Require zero extra
debugger state preparation and explicit replacements for the collector's
location/menu stop gates. Capture a real pre-JSL `$C2CF51` MSS; this completed
run contains only its input MSS, not a resumable terminal state.

The existing menu-shadow v3 remains a design with no qualified input. Its
later actual `$C2CF55` return and 96-NMI interval need a new observer. After that
return, `$C2CF58` redraw reaches an unsupported PC07 save-preview consumer; either
qualify the separate preview adapter or declare an earlier cut. The unchanged
image has no installed persistence adapter, so a disposable vanilla save is
not PC07 persistence. Retain the already selected longer private profile01
transition; do not repeat the completed serializer/SHA proofs or reopen the
integrity-profile choice. Both fresh field-control snapshots retain 81 nonzero
bytes in borrowed candidate `$7EAE00..$7EAEC1`; zero restoration would be wrong.
Menu lifetime, CPU/DMA/HDMA access, stack/interrupt behavior and restoration
remain separate gates before any digest or sidecar writer.

The playable-PC07 goal remains active/incomplete. World-map sprites remain
deliberate/code-assisted pixel art matching the retail cast, with Lily and
Claude Desktop Code consulted at that stage. No new Git push or portfolio
deployment occurred in this checkpoint.

## Earlier October 13 checkpoint: two native events and PC07 battle admission

The unchanged guarded native-event image now has a completed two-load route:
events `$0125` and `$0126` load directly from expanded ROM, all three selected
actors are constructed in both scenes, and the actual D8 request reaches
`$C018A7` **before its battle JSL executes**. The run is
`private/test_runs/pc07_native_event_admission_v1_run1`, exit63, with 261,133
trace rows. Its 14,868 selected native event-bus observations include 4,874
physical WRAM writes with next-instruction readbacks. Both loads return to
`$C00112` and install fifteen function-0 pointers and priority-7 records.
All six field-helper calls and outer graphics returns complete naturally.
Actual logical IDs remain `$00/$01/$07`, with role pointers `$02/$04/$10`.

The shifted second-event D8 at script `$0548` reads settings `$13/$E0`.
The trace records its `$21` pending publication, actual consumption to `$01`,
five PC07 field-to-battle exports and readback, native arena reuse, and the
pre-JSL cut at poll2,811. The terminal `$0306=11296` is after arena reuse;
do not infer final decoded-length or event-payload persistence. Exactly 170
explicit fixture-preparation pairs remain. There are no debugger event-byte,
length or CPU-register edits. All seven original records, all48 stored name
bytes including Epoch, fifteen SRAM snapshots and declared guards survive.
The image still uses the older donor appearance; the separate Schala sprite
presentation has not yet been combined with this native battle route.

The independent runtime review accepts this bounded single run, and root
reproduced it byte for byte:
`private/research/pc07_native_event_admission_runtime_review_20261013/review_v1.json`
(SHA256 `26294be5c7cd7b53699cac1d542fe67b9cd3184558756d75b71a868d7da3e663`).
Its read-only `review_v1.py` rechecks all241 source rows, 61 run artifacts,
12 staged inputs, 11 original inputs and six isolated runtime files, then
independently checks load-byte causality, role/graphics returns, D8 consumption,
exports and the cut. Nine selected scene2 function15/B0 cells have zero
observed reads; they still receive decode and later arena writes. This is
watched-cell dormancy, not a whole-engine legal-domain or B0 execution proof.
The original run receipt retains its historical awaiting-review status.

Prelaunch checks passed nineteen focused tests, actual compilation of both
Lua chunks and exact collector derivation. The collector/validator and launcher
had separate reviews at bundle
`81a5280ab96f02dbe9db0fc4822c029a57514a623a3736848a884854aa48c420`.
The machine/human checkpoint is
`private/research/pc07_progress_checkpoint_20261013e/`, with checkpoint JSON
SHA256 `3eb9d3bf8f855f7ba1fe5a170f4476215e341bf5ae88bbad8da52f9754669240`.
Do not rerun the completed native experiment to reproduce its evidence; use
the read-only audit. Its fresh-output preflight now intentionally refuses the
existing run directory.

Claude Code completed a separate four-file source review through the existing
subscription route (`opus`/`max`, observed CLI label `claude-opus-5-5`, not
independent backend attestation). Exact reply and local disposition are under
`private/reviews/20261013_native_event_admission/`. No concrete blocker was
reported in that supplied packet. Coda checked56 canonical B0/dispatcher
instructions and four actual second-load tail continuations. The selected
B0 body does not directly pop priority7, but callee/touch-call effects remain
separate. Next require each actor's own priority6/function15 publication,
first B0 dispatch, actual return and pointer/priority state through movement;
do not assume all asynchronous calls precede the first B0. General replaced-
tail reachability and effective memory domains remain open.

The separate full native `$0125/$0126/$0126` collector candidate is now frozen
under `private/research/pc07_native_event_full_route_20261013/`. Its
`collector-notes.md` records the 38-snapshot contract and owner obligations;
`derivation_metadata_v1.json` has SHA256
`84f40bd239b9d4372de098c04648013f6d9f3da68e4f8ab55c85cacd2773e88d`.
Root reproduced the exact collector/observer derivation and verified all five
packet hashes. The implementer additionally passed actual Lua compilation and
six focused synthetic observer cases. Those are source checks, not native
execution. Resume with the host validator, launcher/preflight and independent
source review before any run. The candidate uses the identical 1917-byte
event126 on initial and return loads, with 171 state/cursor preparation pairs
and zero event/length edits. Preserve the completed assisted
Attack/escape/return/movement evidence and this admission proof independently.
No full native battle/return, normal save/cold-load, combined Schala Attack or
Epoch vehicle behavior is proved by this checkpoint. World-map art remains
deliberate/code-assisted retail-style pixel work, with Lily and relevant
collaborators consulted at that stage. No new Git push or portfolio deployment
occurred; the playable-PC07 goal remains active/incomplete.

## Earlier October 13 checkpoint: first native expanded-ROM event load

The first event `$0125` now loads from the guarded diagnostic image through
the game's native loader, with no debugger event-byte or decompressed-length
edits. The single run at
`private/test_runs/pc07_native_event_first_load_v1_run1` passes its frozen
validator: 11,573 trace rows, 8,428 selected native bus observations and 2,755
physical WRAM writes with next-instruction readbacks. It observes the actual
pointer-row reads, encoded bank `$44` reads, 2,553 decoded bytes, 134 builtin
bytes, return to `$C00112`, and all fifteen function-0 pointers and priority-7
words. Its evidence cut is before the instruction at `$C05770`.

The image is `private/test_runs/pc07_native_event_diagnostic_v1/diagnostic.sfc`,
SHA256 `badb29e699b38934c39f995ccfb484d8d0847f213524fdb958e9bc50fe5bbc90`.
The separate original-source builder emitted it only after shared intent and
complete-diff audits passed. Its 37 fixed sections contain 5,507 changed bytes
relative to the pinned inert scaffold. Reversing the new event allocations,
six pointer bytes and checksum pairs restores the exact accepted first-Attack
image. Both host decoders agree; fresh assembly reproduces both original
helpers. Production hook/allocation catalogs remain empty. The read-only
on-disk image auditor reproduces byte for byte at
`private/research/pc07_native_event_install_20261013/verify_emitted_v1.py`.

The pilot source bundle is
`1bb2a0c32d393558d6da7e9aff9e5a67c71b6c02435101e9bb79a853287c6e8d`
(227 rows). Root and the independent source reviewer passed actual Lua
compilation and eight protocol tests before launch. Preserve those historical
prelaunch receipts: their fixed fresh-output admission intentionally refuses
after this run directory exists. The independent runtime audit now accepts
the bounded first-load result, and root reproduced it byte for byte:
`private/research/pc07_native_event_first_load_review_20261013/review_v1.json`,
SHA256 `1b6fcb5ddfec549bf1379984be33472aba27147a778903c7101f04349df92b6e`.
Its `review_v1.py` checks all 227 source rows, run artifacts and original
inputs, then independently binds every decoded byte to actual source/port/
physical writes and CPU bank/width state. The original runtime receipt keeps
its historical `collected-awaiting-independent-first-load-review` status;
the additive review supplies acceptance. The human/machine checkpoint is
`private/research/pc07_progress_checkpoint_20261013d/`.

This is still a checkpoint-assisted diagnostic: exactly 170 explicit state
write/readback pairs prepare compatibility, a separate PC07 record, the roster
and joined byte. All seven original records, all 48 stored name bytes including
Epoch, seven SRAM snapshots and the selected compatibility endpoints remain
unchanged. The current image retains the earlier donor appearance. The cut is
inside InitBlock, before remaining actor startup. Event `$0126` initial/reload,
PC07 role/graphics, battle, return, movement, normal save/cold-load and vehicle
behavior are not proved by this run. Do not combine it with the separate
Schala presentation result into an unexecuted claim.

Next: qualify the second native event and actor/battle admission, then the
full native `$0125/$0126/$0126` route using the identical 1,917-byte event126
version at initial load and return reload. Observe actual priority-6/function15
calls and B0/input gates. Reuse the completed assisted Attack/return/movement
evidence below; do not replay it without a new source boundary or failure.
The frozen source-only continuation plan is
`private/research/pc07_native_event_route_plan_20261013/plan_v1.json`
(SHA256 `7aa1c76f2b00a697712b46ed66b5bc4412133f154acfbc8ca7ac00691275a9aa`).
Root rehashed its 17 source rows. The next proposed cut is actual `$C018A7`
before its battle JSL, after both native loads and actor/helper groups;
At that earlier checkpoint the two-load collector was not yet implemented;
the current section above records its subsequent bounded acceptance.

World-map artwork remains a later deliberate/code-assisted pixel task,
matching retail style, with Lily and relevant collaborators including Claude
Desktop Code consulted at that stage. No world-map sprites were produced.
This continuation is local; GitHub/GitLab commit `2f6606b30391cb8ba600096d015a949fb1842c59`
and portfolio version74 remain the preceding publication. The playable-PC07
goal remains active/incomplete.

## October 13 earlier: native post-return follower movement qualified

The bounded post-return control run now passes both its frozen validator and
an independent full audit, reproduced byte for byte by root. Preserve
`private/test_runs/pc07_post_return_control_v2_run1`: 472,824 trace rows,
39 WRAM/SRAM snapshot pairs and 4,178 watched native control writes with
next-instruction readbacks. It reuses the unchanged accepted first-Attack
image and observes the actual `C018CD` RTS to `C000A7`, followed by native
actor-control, D8 acknowledgement, E3 enable and pad-driven field movement.

After a zero-displacement neutral phase, 64 Right polls and 32 neutral polls
move logical PCs 00/01/07 by 64/49/34 pixels respectively, with no Y change.
PC07's concrete chain binds the leader's actual history publication to the
role-2 history read, velocity write/read and world-coordinate arithmetic.
All three B0 entries precede D8 acknowledgement; input waits for every gate.
All 39 SRAM snapshots, all 48 stored name bytes including Epoch, five inactive
original records and the declared compatibility/guard domains are preserved.
All eight final records equal the second native record commit.

This remains an assisted event experiment: 6,558 preparation write/readback
pairs include 1,916 at the second `C05D36`. Initial and return event packets
deliberately differ; the same-size post-return control transform has eight
audited byte changes. There are no debugger actor/record/coordinate/CPU edits
after `C018CD`. This run uses the earlier Crono-donor appearance, not the
separate Schala presentation image. Correct trailing formation, combined
Schala-appearance Attack, native event installation, menu access, normal
save/genuine cold-load and vehicle behavior remain unproved.

The accepted additive review is
`private/research/pc07_post_return_control_runtime_review_20261013/review_receipt_v1.json`,
SHA256 `16235724b964b61c1605ec7cad23a1fb59b3be15e7de97b874773f4a0de91b82`.
Its `review_control_v2.py` reproduces the full audit read-only. Preserve the
original run receipt's historical awaiting-review status; the additive review
supplies acceptance. The local human/machine checkpoint is
`private/research/pc07_progress_checkpoint_20261013c/`.

Preserve the prelaunch compiler correction: collector v1 exceeded Lua's
200-local limit and was never launched. Collector v2 scopes the new callbacks
in a separate function, passes actual compile-only checks and the independent
correction review, and supplies the successful native run. The earlier v1
launch-readiness opinion is superseded explicitly; do not rewrite it.

Next: remove event restaging through a separately guarded persistent native
event source. The verified-static compiler at
`private/research/pc07_native_control_transform_20261013/` produces an in-memory
1,917-byte candidate, preserving initial B2 waits and D8 while adding three
actor B0 functions and post-D8 calls. Its 240 pointer occurrences, 99 branch
dispositions and complete inverse pass; root reproduced its independent review.
Initial loading and native return reloading must use the same relocated
version. No native event ROM or integration run exists yet. Shared intent and
complete-diff audits, named private allocations and actual decompression/call
observations are required; production catalogs remain empty. Reuse the accepted
literal codec and save design, then qualify ordinary menu/save and cold-load.

World-map artwork remains a later deliberate/code-assisted pixel task, matching
retail style and consulting Lily and relevant collaborators including Claude
Desktop Code at that stage. No world-map sprites have been produced.

This checkpoint is local. The preceding publication remains GitHub/GitLab
`2f6606b30391cb8ba600096d015a949fb1842c59` and portfolio version74 with the
supplied photo as main hero. The goal remains active/incomplete.

## October 13 earlier local continuation after portfolio version74 (historical)

The following preserves the earlier full-return checkpoint. Its then-open
movement and next-address observations are superseded by the accepted result
above; its separate save, codec and publication boundaries remain applicable.

The selected full battle-to-field transition now has one successful native run:
`private/test_runs/pc07_escape_field_return_v1_run1`. It uses the unchanged
accepted first-Attack image and reaches actual `C018AB`, then `C018CD` before
RTS. The frozen validator and independent review pass; root reproduced the
review byte for byte. The 442,150-row trace includes the second 240-byte record
commit and both 5,344-byte native field-block copies. Final 00/01/07 HP is
739/603/608; PC07 MP remains 93. All 37 SRAM snapshots, all 48 stored name bytes
including Epoch, and five inactive original records remain unchanged.

Preserve the exact event-fixture boundary: native reload replaces the authored
event, so the collector records another 1,916 exact preparation pairs (6,558
total). This is not native event installation. The image still has the earlier
donor appearance. Movement after `C018CD`, combined Schala-appearance Attack,
save/cold-load and vehicle behavior remain unproved.

The additive accepted review is
`private/research/pc07_escape_field_return_reviews_20261013/review_receipt_v1.json`,
SHA256 `ddf34121fdd6fa3faff917a2d4ff3cdd284709f272c668087fa95e8d8a2dcd66`.
Reproduce with that directory's `review_run_v1.py`; do not rerun the emulator
without a new boundary or failure. The complete local human/machine checkpoint
is `private/research/pc07_progress_checkpoint_20261013b/`.

The separate source-only save preflight v2 now assembles 108 original bytes and
passes root's independent host checks. It qualifies the captured $826B scheduler
frame and accepts only native result $0000 (checksum failure is $4040; absent magic
is $8080). The v3 menu proposal retains an unapproved borrowed 194-byte scratch
candidate: historical save entry is all zero, but the new field cut has 81
nonzero bytes. Actual menu access/preservation must be observed. No SHA/game
scratch, serializer staging extension or native sidecar wrapper is installed.

The actual field cut still has explore flag $011F=0, $0162=0 and camera flag $0120=1;
the canonical pad-move gate skips movement. Qualify the authored event/actor
continuation before proposing directional-input trials. Preserve this fixture;
a new diagnostic tail is a separate change. Next: post-return movement and
actual access to the normal-save menu with its read-only phase observation; then guarded native
event sources and persistence integration. The literal event codec already
passes two host decoders and source review, but native decompression remains
untested. World-map art stays with the user's later deliberate/code-assisted
pixel workflow and Lily/collaborator consultation preference.

The concrete movement proposal is now frozen at
`private/research/pc07_post_return_movement_20261013/proposal_v1.md`; root ran
its five-input reproducer successfully. Evidence SHA256 is
`94fd09935c7ff211cc70aa353f3534a3f7a742420be61dbf69dc4cb61e96cb45`.
The current three actor scripts yield B2 with zero movement fields; the selected
function tables provide no B0 continuation. The proposed whole-command tail
changes script $0548's five-byte status copy to `E3 01 B2 B2 B2`, but that alone
does not supply the native actor-control transition. Implement a separately
versioned event/control fixture before directional-input trials. No such event
change, collector or native run has been made. The post-cut next address
`C000A7` is source-derived from the actual return frame, not yet observed.

This later checkpoint is local. The preceding publication is verified at
GitHub/GitLab `2f6606b30391cb8ba600096d015a949fb1842c59` and portfolio version74,
with the supplied photo as its main hero. The goal remains active/incomplete.

## October 13 publication and first escape commit

Andrei explicitly requested an updated GitHub/GitLab/portfolio publication and
supplied the Schala battle screenshot as the portfolio's main hero. This is
current publication authorization. Preserve the existing portfolio and all
historical evidence; publish source and curated findings, not ROMs, saves,
states, extracted game payloads or raw traces. The supplied screenshot is the
specific authorized portfolio illustration. The playable-eighth-character
goal remains active and incomplete.

The [first native escape commit](pc07_first_escape_commit_2026_10_13.md) now
passes its frozen validator and an additive independent review, reproduced
by root. The unchanged accepted Attack image executes the authored escape
fixture, then copies 240 bytes for logical PCs 00/01/07 and returns at
`$C18218`. Their live HP become 739/603/608; PC07 MP remains 93. Five reserve
original records, all 48 stored name bytes including Epoch, and all 26 SRAM
snapshots remain unchanged. This is the first commit only, on the earlier
donor-appearance image. Do not claim complete field return or a combined
Schala-appearance Attack from it.

Resume implementation from the source-only continuation packet
`private/research/pc07_escape_field_return_20261013/review_v1.md`: second
commit at `$C18440`, actual battle return `$C018AB`, then the proposed full
transition cut `$C018CD`. The exact 24-byte exit branch is conditionally
decoded for its selected premises; no new collector or native full-return
run has been executed. Preserve the completed first-commit proof.

The separate save design at
`private/research/pc07_save_integration_20261013/save_integration_v1.md`
reuses the ten-region serializer and selects a separately numbered private
profile-01 diagnostic with an explicitly longer transition. It installs
nothing. Scratch/interrupt ownership, the actual load success/failure ABI,
preview handling, declared recruited-state fixture and final post-field record
admission remain prerequisites. Claude Code review was requested through the
verified subscription route. The helper reported `sent: true` and a timeout,
with `model_review_completed: false`; the hub records delivery as unknown.
No returned Claude review has been accepted, and no duplicate was submitted.

Andrei also requested a later world-map sprite set for Schala. Match the
existing playable characters' map-sprite scale, palette, silhouettes, poses
and animation timing. Prefer deliberate pixel work or a code-assisted sprite
workflow over generative image creation. At that stage, confer with Lily and
other relevant collaborators, including the available Claude Desktop Code
routes, before choosing the method. This is a future art task, not an asset
already produced or verified by the current field/battle preview.

## October 13 active Schala presentation branch

Andrei now requests retail Schala sprites and the full name Schala for PC07,
with copied retail poses as fallbacks. The additive implementation is tracked
in [the presentation work note](pc07_schala_presentation_2026_10_13.md).
The old accepted Crono-appearance image and Attack run remain frozen. The new
provider compiler reuses the accepted NPC provider and fills all 256 numeric
animation selectors, with explicit guard cells for eight-byte initialization
reads. The fixed six-letter battle-name helper is separately assembled.
The v1 presentation image was emitted with both shared guard audits passing,
but later source review caught bank `$42` falling through to hardcoded `$D5`
in the non-flipped field decoder. No v1 native launch occurred. Preserve it as
a static pilot. The additive v2 decoder repair now has an actual continuous
field-to-battle run with visible Schala and the full six-letter battle HUD name.
All 96 sampled presentation windows and eight tile-copy/control windows pass;
original records, stored names including Epoch, body palettes and SRAM checks
pass. Preserve the initial validator failure: it wrongly required a temporary
HUD buffer to retain its name cells after command-menu reuse. The additive
temporal validator qualifies the same trace with correctly limited name claims.
The screenshot, not an unrecorded VRAM ledger, establishes the full visible name.
Do not repeat this preview without source drift or a new failing boundary.

The request's field/battle appearance milestone is achieved in the private
fixture. Battle action after the appearance change, the fourth rendered facing,
menu/dialogue names, recruitment and save/cold-load remain separate work. Keep
the prior Attack and parked escape packets unchanged; do not describe this
preview as a standalone playable release or an Epoch vehicle test.

The separate authored escape-event transform is complete-static:
`tools/transform_pc07_escape_event_v1.py` changes only accepted event0126 packet
offset0547 from93 to13. Its two focused tests pass. The new escape collector
has since run through the first native commit using the additive v2 launcher
and explicit historical source resolution described above. Complete
battle-to-field return remains unproved. Preserve the original source packet.

## October 13 resumed work, tool tests and first native Attack

Andrei explicitly said “You may resume,” confirmed E: is unlocked if needed,
and authorized downloading/testing useful Ghidra and recompilation tools.
The playable-eighth-character goal is active and incomplete. This resumption
supersedes the pause instruction in the historical October 7 section below;
it does not erase or reinterpret that frozen evidence. No new publication is
implied by the local work recorded here.

The [practical tool assessment](recomp_tool_practical_assessment_2026_10_13.md)
records new executed evidence: a local headless ct-recomp build passes 23
engine tests and nine selected game tests through a Gato victory replay.
These compare native dispatch with its own interpreter, not Mesen or the full
campaign. Ghidra and its SNES extension have actual small-probe results and
specific limitations. A Windows generic SNES CLI generates an original test
project; that generated output has not been built or run. This strengthens the
PC alternative without establishing that it simplifies PC07. Retain the SNES
prototype as the current implementation baseline and compare one actual Epoch
change before making a route decision.

The new [continuous field-to-battle checkpoint](pc07_field_battle_handoff_2026_10_13.md)
reuses the existing accepted image unchanged. Collector v2 now passes one
complete run through destination event0126, its three native graphics-helper
invocations, the real D8 request and native candidate exports, ending before
C018A7's battle-initialization call. Independent offline review and root's
reproduction agree on all 250,006 rows, fifteen SRAM/preservation snapshots,
4,641 preparation pairs and six helper calls. The machine record is
`references/pc07_field_battle_handoff_2026_10_13.json`.

Preserve the first pilot at `private/test_runs/pc07_field_battle_route_v1_run1`:
its collector incorrectly expected pending=$21 at C01890 after native C0177B
had consumed bit$20. V2 verifies both actual writes and reads in the $21→$01
lifecycle, without relaxing other gates. The accepted run is
`private/test_runs/pc07_field_battle_route_v2_run1`, bundle
`26114966b15ab41b807de0d8ab467db1e8e1a2ad6651855f439e74cd8b5dc9fd`.
Preserve the old v3 field run and both new route runs. Reuse this route; its
completion does not establish battle initialization, first Attack or saves.

The separate original battle-adapter packet under
`private/research/pc07_battle_adapters_20261013` now assembles eight new helpers
into 215 bytes, with sixteen exact hook spans and five compatibility operands.
Its original source-only and assembled receipts remain frozen. A separate
private first-Attack contract now places the unchanged 215-byte component at
`$410100`, retaining the old 157-byte component at `$410000`. The emitted
diagnostic is `private/test_runs/pc07_first_attack_diagnostic_v1/diagnostic.sfc`,
SHA256 `6d420e3daa6761a6ca2b0dd6bfc9119aa15967124f92c5d731a431f76726eefa`.
Both shared intent and complete-diff audits pass for its 34 fixed sections
and 481 changed bytes relative to the pinned inert scaffold. Fresh assembly
matches both reviewed components. This is private static construction
evidence, not a production allocation or native Attack result. The source
builder and emission receipt are preserved under
`private/research/pc07_first_attack_builder_20261013` and beside the image.
Its conditional 28,544-case whole-span model and Claude source review remain
separate static evidence. The source review resolves slot-based weapon-mask
production and canonical Tech-partner exclusion. The new selected native run
now qualifies thirty actual hook invocations, including their DBR/width/hidden-B
premises and complete instruction/bus sequences; broader entry coverage and
global interrupt safety remain unproved.

The [first native Attack checkpoint](pc07_first_attack_checkpoint_2026_10_13.md)
is now independently accepted and reproduced by root. The machine record is
`references/pc07_first_attack_checkpoint_2026_10_13.json`; read-only reproduction
is `python -B tools/audit_pc07_first_attack_checkpoint_2026_10_13.py`.
One complete run at `private/test_runs/pc07_first_attack_v2_run1`, bundle
`397ef413aac4e58f2dcb09fd855e862c4726de7c2b98c018b781ff036691df70`,
passes all 343,387 rows, thirty battle-hook windows across fourteen identities,
240 native work-copy bytes and 22 preservation/SRAM snapshots. PC07 in slot 2
executes an actual Attack, naturally takes the critical family, reduces target
HP 8000→7038, returns through C1BA80/C18603 cleanup and becomes ready again.
This uses 4,642 explicit WRAM preparation pairs and no debugger CPU edits.
It retains donor presentation assets. All seven original live records, Epoch
name bytes and captured SRAM are preserved; native work HP changes normally.

Preserve the incomplete 900-second v1 pilot unchanged. Its 24 closed startup
windows pass independently, but no Attack entry occurred. Recorder v2 removes
unused per-instruction CPU snapshots; all 270,687 shared trace rows match after
removing only the header source-bundle identifier. The full v2 trace is
`e2d58e302e937e70577a5d855954c9bbe08eb12bfafd50e53874a78d1a5aed00`.
Do not rerun the accepted action or prior mapping matrices without a relevant
changed source or missing condition.

The next source-only gate is native battle work-to-live commit and return.
The bounded memo is
`private/research/pc07_battle_return_gate_20261013/next_gate_v1.md`; root
reproduced its receipt `b55a858022c6ec4459f21b2b1f6d36df502488bbcaafd16465ad969a95326366`
from `reproduce_gate_v1.py`. It checks 253 selected canonical instruction rows
and all three direct commit callers without claiming full exit closure.
C1B442's roster-based destination already reaches 2830..287F for ID07; its
actual writes need a separate observation. The current D8=$93 fixture forbids
escape. A proposed authored escape-enabled derivative would change only that
operand to $13, or use an already escapable ordinary fixture. Neither has run;
do not claim vanilla Lavos escape. Selected commit needs a deliberately changed
preservation contract allowing actual writes to active records 00/01/07 while
preserving reserve identities and Epoch. Victory/progression and full teardown
remain separate gates. Save/cold-load, unique presentation, vehicle interaction
and a playable release remain open. No Tech or production binding is approved.
The goal stays active and incomplete; these local results do not imply new
GitHub/GitLab/portfolio publication.

## October 7 paused checkpoint

**Paused at Andrei's explicit request after preparing the publication checkpoint.
Do not continue research or launch another native experiment until asked.**
The [human report](pc07_native_field_checkpoint_2026_10_07.md) and
[machine JSON](../references/pc07_native_field_checkpoint_2026_10_07.json)
are the current evidence boundary. One instrumented event0125 run now executes
the qualified field graphics helper at ROM410000 for PCs00/01/07 and observes
candidate movement. Root reproduced the final independent offline receipt,
including the additive exact-bank00 stack audit. All 46 focused host tests pass.
No battle, PC07 save/cold-load, vehicle interaction, interrupt-safety or playable
release claim is made. Explicit debugger WRAM preparation remains necessary.

Resume, only when asked, with destination event0126 and the ordinary-Attack
experiment using the accepted field state and existing setup proposal. Preserve
the frozen v3 sources/run and reuse the completed mappings; no repeated field
matrix or general high-Tech helper closure is a prerequisite.

## October 7 playable-character goal and preserved planning context

Andrei explicitly resumed work and requested a new goal: demonstrate a genuine
eighth identity while preserving all seven original characters, with independent
state, roster/field behavior, an ordinary battle action, and a save/cold-load
round trip. The goal remains incomplete and is now paused. The SNES route is primary;
recompilation remains a comparative fallback. This direction supersedes the old
next-step recommendation below, without changing any accepted helper evidence.

Andrei explicitly reaffirmed that the Epoch vehicle must be preserved or
deliberately relocated. Candidate playable PC ID07 is not a globally free
identifier: naming selector07 and the eighth six-byte name field at
`$7E2C4D-$7E2C52` belong to Epoch, while PC dialogue-name table entry07 is
null. Preserve those contexts; give the new PC independent name storage and
qualified name/portrait resolvers. Do not globally rewrite07 or rename/reuse
Epoch. Final completion must include Epoch naming, appearance, travel/boarding
and save/load behavior. The selected field diagnostic has not proved those
vehicle interactions. Its ten WRAM snapshots do retain identical Epoch-name
bytes, and its entire captured SRAM remains unchanged; reuse this bounded
preservation evidence without promoting it to vehicle-function proof.

The bounded ordinary-Attack path does not require the unfinished high-Tech
package helper. Its identity, participant mapping, graphics, equipment and
progression consumers still need explicit adaptations; no PC07 is playable.

### Reuse before investigation (Andrei's October 7 direction)

Before a new subsystem task, consult its accepted packet, the
[developer guide](schala_eighth_character_developer_guide.md), and the
[correction register](DATA_MAPPING_CORRECTIONS.md). Reuse unchanged results;
do not rerun an accepted native matrix or repeat a completed mapping survey
without naming the changed source, contradictory evidence, or missing
condition that matters to the playable prototype. A new document or reviewer
is not itself a reason to repeat execution. Prefer inspecting existing traces
when they already capture the required observation.

Use community mappings and implementations as starting points and credit
them explicitly. Distinguish community-documented, locally confirmed,
corrected, newly measured for this prototype, and still unknown. Neither a
local confirmation nor a community annotation proves first-ever discovery.
Verification should address the particular dependency or uncertainty; it
should not restart a whole subsystem audit.

| Current need | Work to reuse | Genuinely remaining work |
| --- | --- | --- |
| Event decoding | The accepted [location-event audit](location_event_item_reference_audit.md) and `tools/audit_location_event_items.py`; historical cross-check against Temporal Redux `365086c1` covers 489 valid event IDs and 155,780 command-instance lengths. Completed exact in-memory transforms now cover selected events `$0125` and `$0126`. | Reuse both transforms for the continuous destination/battle experiment; no new decompressor, all-event census, or repeated transform implementation. |
| Insert an eighth field object | [Historical eighth-character audit](historical_eighth_character_forum_mapping_audit_2026-08-23.md), including Mauron's PC-before-NPC ordering and doubled object-index rule; Temporal Redux / Jets of Time [`insert_copy_object` and object-call adjustment](https://github.com/OnemusCT/temporal-redux/blob/365086c1c0a33144b24bff4933998bdff82c9940/sourcefiles/jetsoftime/ctevent.py#L532-L704). The accepted field v2 diagnostic demonstrates selected `$0125` construction and movement. | Observe destination `$0126` construction and the actual field-to-battle handoff. Preserve the completed selected-field observation; it does not prove every scene or Epoch vehicle behavior. |
| Record, graphics and save maps | The corrected character map, graphics/menu audit, and historical Vehek/Mauron/JLukas findings already distinguish occupied entries, seven-record storage, growth boundaries and the save descriptors. | Implement the specific `$07` consumers; do not present those old addresses as new discoveries. |
| Compatibility relocation | Accepted native save/load chain, menu pair and narrow residue observation below. | Installed lifecycle and genuine independent record remain open; preserve the completed bounded evidence. |
| First battle action | The source-only ordinary-Attack proposal at `private/research/pc07_basic_attack_prototype_20261007/basic_attack_candidate_v1.json`. | Implement and observe its participant/record/graphics adapters; high-Tech helper closure is not a prerequisite. |

### Earlier October 7 destination and native adapter source checkpoint

The source-only state below preceded the final native field run. Its six-byte
field hook and first adapter routine are now installed in the separate private
diagnostic and observed as described above. The six battle routines remain
unhooked. A distinct fixed private expanded-image contract and historical source
capsule now resolve the packaging obligation described in this earlier record;
no production catalog or general free-space authorization was opened.

The separate `tools/transform_pc07_lavos_event_v1.py` now constructs event0126
in memory. Root read the complete source and passed all eleven focused tests
with the canonical ROM, including exact reference reproduction. The 1,914-byte
result has SHA256
`6999eb3bb0cc4f9b3db8d6d405a8aa4ebe94a0b590b5c8f01c531a31c3bd3bc5`.
It inserts object8 before the original NPC/battle object, changes the copied
loader and six identity literals, shifts four doubled object references, and
preserves all original bytes through inverse projection. The donor's function4
shared audio effect is retained explicitly. Metadata and reproduction are in
`references/pc07_lavos_event_transform_v1.json`; no raw packet or ROM is emitted.
Destination execution and complete cutscene/victory behavior remain unproved.

The ordered source-only battle setup note is
`private/research/pc07_battle_setup_20261007/setup_note.json`, SHA256
`a2a8d505720c943a56ab28f4b4a86e304c018e85e2be7c0bff695bcaf5ec7c57`.
It identifies additional learned-mask readers, name and graphics lookups,
equipment ownership and initial turn-order requirements. Its correction to
the older Attack proposal is additive: normal C1CF15 calls read equipped item
IDs and use CC0000 as an item-table bank base; they do not require a new initial
character row for canonical equipment. Preserve the older note unchanged.

`asm/pc07_donor_read_adapters_v2.asm` is the current assembled source candidate
for one qualified field lookup and six battle table readers. It preserves
Epoch's independent naming path and name storage. The 157-byte raw component
has SHA256 `315f409ece80e84c656930c47bc5a0d6e0f97d83aecc95b7c474abc2056750e7`;
the source, assembler command and rejected-v1 delta are recorded in
`private/test_runs/pc07_donor_native_source_v2/receipt.json`. V1 is rejected:
its proposed field span split an immediate operand and its helper omitted INY.
V2 restores INY and specifies the exact six-byte C0448D..C04492 span.
At this earlier checkpoint neither version was installed or runtime-proved.
Do not use v1 for integration.
Independent v2 delta review found no remaining material source defect; root
read its receipt and checked all eight input identities. The review receipt at
`private/test_runs/pc07_donor_native_source_v2/source_review.json` has SHA256
`5b1ea5cff78b79f2f1a12a008e6731873eb20adb9535012bf482f540e484c7ca`.
That receipt is source/component review only; the later field evidence is
separate and still does not test vehicle interactions.

Before any native game-image emission, resolve a distinct private expanded
diagnostic write contract. Existing canonical private diagnostics cannot
authorize expanded payloads, and empty production catalogs must not be bypassed
with fabricated approvals. Extending the guard also changes dependency hashes:
preserve reproducible historical source bundles rather than silently changing
their pins or repeating accepted emulator matrices. This packaging obligation
does not change the active playable-character objective.

The July community survey is historical, not the last word. In particular,
MAP-003 corrects our own overbroad criticism of its base-stat ordering:
Magic-before-Hit is correct for base/live records, while growth rows use a
different order. Check corrections before repeating an old objection.

The already completed function-pointer/alias census in
`tools/audit_location_event_animation_operands_v0.py` is another reuse input;
selected insertion must preserve those relationships rather than inventing
a second generic topology model. The community `ctevent.py` raw pin has SHA256
`2d27b185f7009a976cf2439cc5a3c7fee6c00aa144920b6f1117f5dec7b558da`.
The local snapshot's SHA256
`608b2e6788724377b31b792bc17a1cc61de2e4e96f79f24940801db258ea7897`
differs only by CRLF serialization; normalized bytes were compared exactly.
Do not silently replace this previously cross-checked revision with a newer
upstream head. Source comparison does not require copying its general ROM
mutation or free-space allocation path.

The separate native save-layout v1 diagnostic now has two identical save traces
and two identical load traces. The real native loops transfer 2,100 bytes in
ten regions while a distinct marker protects `$7E2830-$287F`. The save makes
80 actual reads from relocated compatibility at `$7E2CA0-$2CEF`; the load
overwrites 80 distinct poison bytes there. All seven original records retain
their serialization positions. The native save checksum is `$0EEA`. A clean-ROM
cold boot accepts the produced SRAM, and a fresh-process replay reproduces the
pre-JSL load checkpoint's entry CPU, complete WRAM and SRAM. The subsequent
instrumented load is explicitly a resumed checkpoint, not direct cold boot.

The private diagnostic changes exactly two guarded CMP operand bytes and uses
debugger preparation/table injection. It restores the vanilla compatibility,
candidate and descriptor staging layout synchronously at copy completion, then
observes the save checksum/metadata epilogue. Its terminal boundary is before
RTL; deferred-stop battery data is not evidence. This is native instrumented
copy evidence, not an installed wrapper, persistent relocation lifecycle,
sidecar, global WRAM allocation, or new playable record. Production catalogs
remain empty. Preserve the frozen `a280927788eee65f2bac11d2acb0f3740e9fa0f80172f02254e7dc1c288247cb`
source bundle and all accepted/rejected acquisition pilots.

The metadata-only [accepted chain reference](../references/schala_save_layout_native_chain_v1.json)
pins 150 artifacts and 53 byte-equality groups. Run
`python tools/revalidate_save_layout_native_chain_v1.py` to reproduce its
validation without launching an emulator or emitting an image. Root reran this
CLI and the six integrity/lineage tests successfully.

The separate guarded seven-operand menu experiment now has two control runs
and two relocated runs. Root inspected the Tech-screen and field-return
images; the [paired metadata](../references/schala_compat_menu_pair_v1.json)
and `tools/revalidate_compat_menu_pair_v1.py` reproduce 239 equivalent watched
bus events and nine matching sampled CPU tuples, with the seven records,
roster, names, derived mirrors and SRAM preserved. There are 104 same-value
record writes and one same-value adjacent roster-byte write; unchanged does
not mean unwritten. The old-block marker remains exact. One early field PNG
in the relocated repeat captures a different save-point-orb animation frame;
native traces and memory snapshots remain byte-identical within each mode.
The equipped-rock store at `$C2830E` does not execute and remains static-only.

The separately versioned v2 observer closes the two-byte residual question
for this selected route. Both modes contain 14,196 aligned accesses to the
four watched physical bytes. Exactly 16 values differ, all from saving and
restoring Y `$285C -> $2CCC` or copying those bytes between `$7E0A78-$0A79`
and `$7F2158-$2159`. No observed field screen-X consumer reads the differing
values. The decompressor overwrites its two bytes identically before reading
them. Every original observation projects exactly to both accepted v1 runs
of its mode. This does not prove a universal field-index domain or global
WRAM ownership; it removes this selected differential as a current blocker.
No further repeat of this boundary is needed absent a new failing condition.

The independent receipt is
`private/research/compat_menu_v2_residue_review_20261007/receipt.json`, SHA256
`f4e90a5091736762ab82159c8eeb4a62cc6e5d4f3289c01071adfd462f989fe8`.
Root reproduced it read-only with
`python -B private/research/compat_menu_v2_residue_review_20261007/reproduce.py --check private/research/compat_menu_v2_residue_review_20261007/receipt.json`.
The frozen v1 bundle remains
`3862d30a8cd095f3678e83d7e710237a296565610ba4b828f70b2a8ae8ffc3a7`;
the separate v2 bundle is
`e9689f31639caf7d165a043b56091fc1dbc0d56ec278d9607c4df596c8de9a44`.

Claude Code completed both the architectural and native-loop source reviews
through the existing subscription. The second response ended normally and is
preserved at `private/reviews/20261007_pc07/claude_native_answer.txt`, SHA256
`85ef62a4780de6061388110d14f3a7f803ab632fb84de6abf2bad079a7700edd`.
It received six files, not all ten bundle dependencies; it did not execute
code or recompute hashes. Root and an independent native agent checked the
consequential findings. The separate
`tools/audit_save_layout_native_review_v1.py` proves physical stream uniqueness,
exact ordered vanilla equivalence and canonical compatibility position, then
checks observed global metadata values, contexts and final bytes. All seven
tests pass, including wrong-slot metadata and same-value wrong-context
adversaries. Historical accepted references still correctly say the review was
pending when they were created; this additive note supplies later completion.
No blanket external approval of the entire bundle is claimed. Raw inputs,
checkpoints, traces, screenshots and review packets remain under `private/`.

The selected event `$0125` insertion inventory is now accepted-static after
root source review, all 15 focused tests with the canonical input, and exact
metadata reproduction. It reuses the existing event parser and credits the
community insertion implementation. The reference
`references/pc07_selected_event_remap_v1.json` has SHA256
`aa9c83da8af9a6d249924bcdcdf4e39c346b397d4b5c3372768f3473fb832599`.
For insertion at object `$08`, exactly four existing direct-object operands
change; all 224 original function pointers retain their alias relationships,
all 186 original relative branches keep their displacement bytes, and the
party-role selectors remain unchanged. This instantiates a known format for
one packet; it is not new discovery of the format or a native insertion.

The preferred new-object source is a separate private copy of existing
object `$01` (159 bytes). Its complete functions cover the scene's required
functions 3-7 and contain no inter-object calls or character dialogue. The
proposed copy changes its fixed Crono loader to generic `LoadPC $07`, adding
one byte, and changes exactly thirteen comparisons against the donor ID to
`$07`. Its unrelated slot-6 control comparison stays unchanged. All seven
original objects remain intact. This replaces the earlier minimal-object
idea with a concrete 160-byte complete-body implementation. The separate
`tools/transform_pc07_selected_event_v1.py` now constructs it in memory and
verifies all 240 function pointers, all 205 original/copied branch targets,
the complete new body and inverse equality of every original packet byte.
Root passed all 12 focused tests and reproduced the metadata reference
`references/pc07_selected_event_transform_v1.json`, SHA256
`0bb253c1f296e5719b204052588f25254a045a3cc716d32127347b6e304cdd66`.
The transformed packet is 2,553 bytes, SHA256
`d81b7bfc4db23d95adc8a576ba2472e1cd005ab8e43cf997fda3e5e3da29a51d`.
The CLI emits metadata only. Its native use is separately described below.

One new clean-ROM observation at
`private/test_runs/mesen2/pc07_field_entry_v1_run1` confirms actual `$C00085`
entry with D=`$0100`, DBR=0, M8/X16 and SP=`$06FF`; exact canonical packet and
builtins at `$C05D36`, SP=`$06FB`, stored return `$0111`, decompressed size
2,361; and actual return to `$C00112`. Its trace SHA256 is
`95a1528b0c2cad29984fa86c27f2337b7e77710c9b371b75418d4492925428e0`.
All seven records and SRAM remain unchanged. The short Left/Right pulses move
the leader and first follower, not the third; no monitored scene-call site
executes. Root inspected the idle/left screenshots. This closes the selected
entry question without a new menu or serializer matrix. The four focused
observer checks pass. Do not repeat it merely to obtain a second trace.
The independent offline review is
`private/research/pc07_field_entry_review_20261007/receipt.json`, SHA256
`8e60151b54bceb079676c1aea3e4a3f18a44e4ce2d7158a9f2c6fdca9dea75ad`;
root reproduced it with the adjacent `reproduce.py --check`. One concrete
lifetime correction for the next probe: `$C043EC` publishes the third-object
word at `$0B8B`, but later native cache initialization overwrites that storage.
Observe its constructor write without asserting persistent ownership; use
the distinct `$0197/$0199/$019B` role pointers for the captured movement.

The first emulator-assisted PC07 field pilot is preserved as a rejected run
at `private/test_runs/mesen2/pc07_field_probe_v1_run1`. Its source bundle is
`67ff816f41fa0a5f34d4c8a3c55224577398e3f58419373052e8727baaee810c`;
the trace SHA256 is
`2208b2883d8354ee17e51ce5f635538faece9c644c6d0f35530fb27b74b08535`.
The native generic `$80 $07` loader publishes logical 7, role 2, and object
offset `$10`; both donor-0 and candidate-7 graphics windows complete through
actual returns. The one debugger substitution changes A `$0107 -> $0100`,
preserving hidden B and the other captured CPU fields/clock. Both staging
diffs and all 2,725 paired byte preparations were independently checked from
the existing trace. This is completed-prefix evidence, not a passing field run.

At poll 30 the protected-record guard refuses the native `$C282E4` write
event to `$2857`: value 0 conflicts with staged record byte `+$27=$8F`.
There is no subsequent readback or movement snapshot. This is an already
mapped compatibility consumer, not a new mapping discovery. The initial
probe omitted the accepted seven-operand relocation. A separately numbered
v2 reuses that unchanged guarded builder and prepares compatibility at the
already-tested `$C2E65B` point, before the post-load consumers execute. The
PC07 record and roster remain delayed until `$C00085`. Do not repeat the
menu matrix or relax the record guard to accommodate this failure.

The corrected v2 field run now completes through poll400 with 45,184 records:
`private/test_runs/mesen2/pc07_field_probe_v2_run1`. Its frozen source bundle is
`e5ff0b284a76a712c206933d492d83e295f6df86bd2b5250b28e27429e65afaa`;
trace SHA256 is
`1ce216f8a903cfdedc0fc24643515fb3c11c2ed50be9cd6fdd1586c18724039a`.
The unchanged guard accepts exactly fourteen known compatibility operand
bytes; no new ROM hook is added. Ten snapshots preserve all seven original
records and exact input SRAM. Candidate07 has its own 80-byte record with
HP968 versus donor00 HP969. Active roles 0/1/2 hold distinct logical PC IDs
00/01/07. At polls 90/180/280/400 the candidate's screen X is184/170/150/154, demonstrating
actual third-follower movement under the longer Left/Right sequence. Root
inspected poll180 and poll400: Crono, Marle and the donor-looking candidate
are visible together. Both graphics windows still use their actual native
returns, with exactly one explicit debugger A-low substitution for07.

The independent offline review passes and root reproduced its receipt
byte-for-byte with `python -B private/research/pc07_field_probe_v2_review_20261007/reproduce.py`.
Its metadata receipt SHA256 is
`328745a195b3d4c0bd9790545bda856c4db3d6b4b0b78e155894f7a9fb4a1e47`;
the reproducer SHA256 is
`54b030fb5378f41462aa75f514926dc5bb74a1ae2709459569335da03b6ecf31`.
It reconciles actual indexed native coordinate stores with later snapshots,
including PC07's first changed world/screen-X stores at poll166. No coordinate
CPU-read callbacks were collected. There are zero observed native record or
SRAM writes. The two early pre-render PNGs are empty and are not visual proof.

This closes the selected emulator-assisted field experiment; it is not an
installed native graphics adapter or independent action/save proof. Preserve the run instead of asking
for an otherwise identical pair. Next use the existing ordinary-Attack
proposal and this field state to specify the smallest battle diagnostic;
do not reopen the high-Tech helper or repeat the community mapping census.
The active playable-character goal remains incomplete.

## Earlier October 3 checkpoint (preserved)

Updated 2026-10-03. This page is the short resume point; the append-only
[developer log](DEVELOPER_LOG.md) and individual evidence packets retain the
full history. The project is research in progress, not a playable eighth-PC
release. The open integration gate is `BA-NATIVE-INTEGRATION-DESIGN`.

## Authoritative locations and resumption

- Local workspace: `C:\CHRONO TRIGGER`.
- GitHub: [CodaLilitari/project-epoch](https://github.com/CodaLilitari/project-epoch).
- GitLab: [codalilitari/project-epoch](https://gitlab.com/codalilitari/project-epoch).
- Portfolio: [Project Epoch case](https://richard-pemberton-research.darkahn.chatgpt.site/#project-epoch).

On resumption, both hosted main branches and the local checkout were exactly
`a0b17f6227ed6a54cdfb7c63e726feb94d26b89d`. The old GitHub account path
returned 404 through the authenticated API. The local `origin` URL was
corrected to the verified CodaLilitari repository; the private archive remote
was left unchanged. GitLab's later project activity was not a newer source
commit. The portfolio already linked to GitLab and accurately described
unfinished research, private game inputs, and no finished playable patch.

The September 8 session was interrupted with unfinished sources. October 3
is a new resumption date, not twenty-five days of elapsed engineering work.
The exact interrupted files were preserved in an ignored recovery archive
before editing. Historical September reports and accepted references remain
unchanged.

## Completed foundations to preserve

The original 577-byte stack-local helper already has repeated synthetic
cartridge-ROM execution and minimal-handler NMI proofs. The canonical game
has repeated primary/alternate resolver observations, one successful queued
action, and a natural failed Cure lifecycle. These prove their declared
contexts. They do not approve game code placement, game stack ownership,
partial-publication safety, a new late-rejection cleanup path, or PC `$07`.

The saved mapping distinctions, empty production allocation/hook catalogs,
safe-empty save policy, and all earlier conditional scene/IRQ packets remain
mandatory. Start with [the developer guide](schala_eighth_character_developer_guide.md)
and [the correction register](DATA_MAPPING_CORRECTIONS.md) before reusing an
older annotation. Do not repeat accepted native matrices without source drift
or a newly identified boundary.

## Work in progress at this checkpoint

1. The additive [scene `$80` remaining-return packet](schala_scene80_remaining_returns_v2.md)
   is accepted after independent root review, 38 tests and exact repeated CLI
   reproduction. Its two old frontiers now have conditional return proofs;
   this does not establish legal inputs or physical stack/memory ownership.
2. The [scene `$8B` copy-producer packet](schala_scene8b_copy_producers_v1.md)
   is accepted after independent peer/root review, 52 tests and exact CLI
   reproduction. Four stubs reduce to three pointer producers with explicit
   input/alias premises. The separate [half-fill packet](schala_scene8b_half_fill_v1.md)
   is now accepted with 38 tests and independently repeated metadata. Zero s
   causes 16,384 word stores under fixed-target premises; positive s fits the
   $380 comparison interval exactly for 1..224. This proves no legal script
   domain or ownership of that interval.
3. The [actual-game NMI observer](normal_nmi_stack_observation_v1.md) now has
   two identical full traces across five selected intervals, independently
   revalidated with complete observed WRAM reconciliation. Each reaches 34
   bytes below handler entry, 38 including its existing hardware frame.
   The accepted metadata preserves all limits and the failed earlier run.
   Its 80 observer and 46 acceptance tests pass. Preserve this pair; it is
   neither a whole-NMI bound nor helper-preemption/stack-ownership proof.
4. Follow the [interrupt strategy review](schala_package_interrupt_strategy_review_2026_10_03.md).
   Do not borrow the game's busy byte as a helper lock. The exact small
   original-cartridge fixture has a reviewed 67,112-clock conditional timing
   envelope, excluding DMA/HDMA and interrupt work. The general 32-target
   registry has a much larger envelope.
5. The [resolver-phase v2 observation](schala_package_resolver_phase_v2.md)
   now repeats identically in two isolated runs: 2,261 records, eight earlier
   interrupt contexts and the following IRQ/NMI pair, with 161 engine fields
   per record. Preserve the intentionally rejected v1 pilot and its unchanged
   protocol. The 43 v1, 34 v2 and 39 acceptance tests pass. HDMA is enabled
   for all eight unfinished channels at resolver entry; no-pending snapshots
   do not prove no future service. IRQ circuit counters and relevant overclock
   settings were not captured, so no interrupt deadline is certified.
6. The [HDMA timing model](schala_package_hdma_timing_v1.md) is now accepted
   as conditional static evidence: 13 tests and two root CLI reproductions
   match the independent peer and author exactly. Generic service is 472
   clocks; the fixed-fixture phase refinement is 106,342. Explicit line/frame
   minima and unproved configuration/cache binding prevent treating this as
   an admission certificate. The frozen report records preparation status;
   this handoff and the latest developer-log entry record root acceptance.
7. The separate [v3 observer](schala_package_resolver_phase_v3.md) now passes
   twice: 2,263 identical records, 163 engine fields and exact complete v2
   projection. It captures internalRegisters.hCounter/vCounter and a post-load
   line-0-to-line-1 crossing under guarded zero extras. The crossing occurs in
   historical NMI context 1; preserve the rejected main-context-only pilot.
   Hidden cache values remain unobserved and a valid-source-state premise is
   explicit. All 178 phase tests pass. Read the external review disposition
   before treating file consistency as authenticated execution evidence.
8. The separate [IRQ request-transition v1 packet](schala_irq_request_transition_v1.md)
   is accepted at source-conditional-host-model: 81 tests and identical independent
   root/peer metadata, SHA-256
   `846a54df9c490cee263bb86cf1b351683262562915eaecb148e3c182bd1686a7`.
   It pins fourteen Mesen files and the accepted v3 reference, models recursive
   DRAM Exec order, all uint8 pending counts, explicit register operations and
   separate CPU sampling/selection gates. The existing 178 phase tests pass;
   no native matrix was rerun. Exact observed-seed hypotheses give host-model
   offsets 124740/124744/124748; the abstract 1360-clock floor gives
   124372/124376/124380. Neither is a certified game deadline. Unknown
   callback/register/reset premises refuse. Preserve the older private drafts
   and earlier peer generation rather than relabeling them accepted.
9. The separate [DMA/IRQ and callback packet v1](schala_dma_irq_closure_v1.md)
   is accepted at reused-observation plus source-conditional-domain-model.
   All eight entry channels are forward/indirect with both source banks `$7E`;
   exact conditional bus unions exclude direct IRQ-register effects despite
   unknown table contents. This is not handler/callback closure. SETINI can
   change rendering but does not directly change the fixed timing-cache inputs
   or line-length predicate on lines 119..211. The source inventory pins 42
   files, 24 qualified facts and 70 spans. Root passes 293 tests (34 new,
   81 transition, 178 phase); the peer independently passes all 34 and produces
   identical metadata, SHA-256
   `0b99435c6b6209188284ebfc6f5db77f2726db0ec501e81872346286e146b50e`.
   The frozen v3 audit is reproduced unchanged; no native run was repeated.
10. Next: **DMA-CALLBACK-BINDING-DESIGN**. Inventory the accepted launch/state
    artifacts for actual memory mappings, coprocessor presence, debugger
    guards/script targets and controller types, then specify only missing
    read-only observations. The existing 163 fields omit controller profile,
    autojoy scheduler internals, TIMEUP/PPU payload traffic and direct hidden
    cache values. Exact ordinary controller/debugger source branches are
    conditional; host/virtual targets, reset/load and external cache refresh
    remain open. Service recursion is not automatically unfinished-Exec
    recursion. Preserve the older synthetic H6/H10 counterexamples in their
    declared positions. Do not compare the IRQ offsets with the helper envelope
    as though all premises were jointly proved. Wrapper cost, physical stack,
    interrupt policy and pre-effect/later-resolver lifecycle remain separate.
    No phase rule, high-selector binding or game insertion is approved.

The [October research refresh](online_research_2026_10_03.md) found 22 new
randomizer commits, including a useful Beast Toss counter-handshake fix, and
434 reported SNESRecomp commits since the prior pin. Its comparison response
is capped, ExHiROM remains unsupported there, and no new additive eighth-PC
release was verified. The two tracked disassemblies and main mapping/editor
tools are unchanged. Chrono Compendium refresh failed; no old forum timestamp
is claimed as freshly verified.

Earlier review state: Antigravity returned two bounded reviews, independently
dispositioned in [the review note](external_review_2026_10_03.md). Claude Code
job `8cf82ea83be948d89d7af51a80e106fe` timed out after 1,800 seconds with
delivery unknown; do not blindly retry. Grok startup isolation is solved with
a per-child empty USERPROFILE while preserving HOME and the dedicated profile.
Its model catalog and SuperGrok 17%, then 18%, weekly usage were observed.
Andrei confirmed paid extra usage is disabled. Grok returned the IRQ-timing
review and a same-session follow-up; the official export was checked against
all four saved messages. Session: 01a10469-782e-79c1-bd85-71071fc07e34.
Receipts are in private/reviews/20261003b/grok_irq_review_live/ and
grok_irq_followup/. Two initial claims were corrected, not adopted by
consensus. See the full disposition before reusing its advice. Refresh usage
before future dispatch. The old chat reached its native subagent limit.

The earlier continuation completed the IRQ transition checkpoint. Three
native collaborators and root independently checked the implementation; the
final peer output equals the root reference byte for byte. Two further Grok
messages in the same project session reviewed the model and received our
verified H10 correction/thanks. Fresh usage was 18% before each send, model
options and helper source were unchanged, and the final official export now
matches all eight saved messages. See private/reviews/20261003c/ and the new
review disposition. The current continuation completed the additive DMA and
callback checkpoint with three native collaborators and independent root
checks. Prior findings and final peer receipts remain in
private/reviews/20261003d/. No new external-provider dispatch or native run was
used; no reviewer remains running. Resume at step 10, preserving both packets.

All ROMs, SRAMs, emulator states, raw traces and extracted data stay under
ignored `private/`. Source-controlled outputs contain original tools, tests,
hashes and bounded analysis. No production selector or game hook is installed.

The v3/research checkpoint is GitHub commit
`7ac6499ae484a6598c1727659f18979aaf838a74`. Authenticated commit and branch
reads agree with the remote, and all 16 changed files were downloaded at that
exact commit and matched to committed local bytes. The private publication
receipt is private/test_runs/counters_checkpoint_20261003_publication.json.
At the October 3 final host check, GitLab main remains `a0b17f6`. The
synchronization question remains unanswered. The portfolio was refreshed,
still accurately described the unfinished project, and was left unchanged.
The newer IRQ transition publication receipt is retained separately at
private/test_runs/irq_request_transition_v1_publication_20261003.json; use its
exact commit and downloaded-byte comparisons for this checkpoint's host state.
The newer DMA/callback publication receipt is retained separately at
private/test_runs/dma_irq_closure_v1_publication_20261003.json. Use that receipt
for this checkpoint's exact GitHub commit and downloaded-file comparisons.
