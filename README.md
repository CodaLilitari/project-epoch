# Project Epoch

This workspace resumes the Chrono Trigger playable eighth-character investigation recovered from the ChatGPT conversation **Chrono Trigger 8th Character**.

## Current direction

The supported-slot Magus-over-Lucca diagnostic is complete enough to expose
the major seven-character assumptions and its unsafe runtime experiment has
been retired. Production work now targets Schala as logical PC `$07`, using a
natural eighth live record after relocating the vanilla compatibility block,
versioned per-slot sidecars, context-specific graphics/menu adapters, and raw
high-ID `$80-$90` commands that preserve every vanilla action.

The recovered v0 diagnostic is preserved under:

`recovered/ct_lucca_to_magus_clone_v0_bundle/`

It reproduces exactly from the canonical clean US Rev 0 ROM, but it is incomplete and remains a diagnostic:

- portrait palette copied, portrait tiles omitted;
- normal-attack selector omitted;
- menu element icon omitted;
- menu/battle tech description paths not mapped;
- the retired runtime experiment overwrites enemy-reward records and is known
  unsafe.

The resumed v1 diagnostic builder and its tests are under `tools/` and
`tests/`. Generated static-only and provisional-runtime IPS patches, reports,
and manifests are under `output/`.
Normal emulator-run preparation excludes the known-unsafe runtime variant;
historical reproduction requires the explicit
`--include-retired-unsafe` option.

All current diagnostic builders now run
`tools/validate_rom_write_intents.py`. The Schala smoke and static
Lucca-to-Magus clone must account for every changed byte and pass as private
diagnostics; the retired runtime clone must be explicitly rejected for its
`EnemyRewardTable` overlap. The production hook and allocation catalogs are
currently empty.

Use `docs/runtime_test_protocol.md` for the disposable-save emulator test and
the interpretation matrix. The first reproducible emulator run is recorded in
`docs/emulator_test_results_2026-07-25.md`. The accepted July RetroArch
1.22.2/bsnes replay matrix remains in
`docs/current_emulator_replay_harness_2026-07-26.md`; the separately pinned
2026-08-22 rolling-core install and bounded compatibility results are in
`docs/current_emulator_update_2026-08-22.md`. The complete vanilla Magus
fight/recruitment reference trace is in
`docs/vanilla_magus_recruitment_runtime_trace_2026-07-26.md`. The active
harness also verifies that the recovered final save walks directly from Lavos
Tunnel into Lavos Core and reaches the native battle menu. Its independent
twelve-button Player-1 battle calibration now proves top-level navigation,
pause, command-window movement, and normal-attack confirmation while keeping
seven context-inert controls out of the accepted artifact set. A separate
route opens Frog's native Tech submenu. The first A-only probe correctly
failed to damage Magus because it stopped at target choice; a released second
A confirms the target and reproducibly lowers Magus from `6666` to `6137`
while returning to a stable command menu. A separate four-confirm route now
opens the Tech menu, selects Heal, confirms Frog, spends 2 MP, restores him to
`999/999`, and returns to the command menu against a matched no-cast control.
The latest compatibility tranche renders every top-level main-menu page,
switches the Tech owner to Marle, equips Crono with a Kali Blade while
recomputing Attack, and completes a matched MegaElixir
list/target/consumption cycle. All thirteen terminal states preserve the
relocation canary and both guards. A separate natural Guardia Forest route
enters a three-Roly battle, reaches the `Found 480G` reward, tears battle
state down, and returns to the field with the same preservation checks. From
that checkpoint, Cyclone now has a matched no-cast control and demonstrably
resolves two separate enemy slots while spending exactly 2 MP.
The same harness also performs a real slot-1 overwrite and reloads Save #63 in
a fresh emulator process while preserving Epoch and `$0430-$047F`. A separate
vanilla compatibility control boots with one valid v1 sidecar, preserves the
complete SRAM through 3,599 idle frames, then cold-loads Save #63 while the
sidecar, vanilla slots, metadata, Epoch, and protected compatibility bytes
remain exact.

## Current v1 outputs

- Static-only IPS SHA-256:
  `20fcbd08b954311cb948bbcfc0a90eb3bbb6cc46ad00524c0add8ac0e9ecc0d7`
- Quarantined provisional-runtime IPS SHA-256:
  `484bad4051f39d92015f57a927471d8287ca4e3652a1eef5a9475fabbf4b3cae`
- 883 automated checks are discovered: 879 pass and four skip explicitly.
  Two skips are privilege-dependent real-symlink cases with deterministic
  mocked reparse coverage passing; two are historical live-artifact rebuild
  checks whose original pinned `D:` toolchain is unavailable. Coverage
  includes the recovered clone,
  deterministic BSV inputs, SRAM/WRAM canaries, save layouts, ExHiROM
  controls, canonical event and record audits, original content, portraits,
  sprite packing, field palette routing, source-only recruitment, the v2
  sidecar/load/lifecycle contracts, three standalone 65C816 binding
  candidates, native-Mesen event `$11C`, WRAM-ownership trace contracts,
  Focus adapter boundaries, the Glass Focus and current 16-frame body-packet
  audits, the animation semantic contract, the hardened field-animation
  probe, the complete encoded location-event animation operand census, the
  compressed NPC/enemy sprite corpus, the bounded Schala NPC comparison, the
  metadata-only battle action-package topology census, and the source-only
  player-Tech package-bank adapter contract.
- All 90 source-controlled Python tools parse successfully.
- Independent repeated builds produce identical IPS, report, and manifest
  bytes.

The static diagnostic now reaches save-select and the loaded field with a
coherent Magus portrait and field sprite in Lucca's supported slot. The
quarantined runtime shim also reaches the field but does **not** leave the
Magus record cloned over Lucca at the recorded checkpoint. It remains unsafe
and ineffective.

The static-only IPS under `output/patches/` is the normal deliverable. The
runtime-hook build is named `UNSAFE` and kept under `output/experimental/`.
Static reconstruction proves its `$CC:63F6-$CC:642F` shim overwrites
`EnemyRewardTable`, while `$CC:E980` is field sprite/animation setup rather
than character-record initialization. The artifact is retained only to
reproduce the negative experiment; do not build on it.

Schala is now the selected production eighth-character target. The living
implementation guide is `docs/schala_eighth_character_developer_guide.md`;
the creative/technical content proposal is
`docs/schala_character_design_v0.md`, and the original native-grid art
requirements are in `docs/schala_sprite_asset_spec_v0.md`.
The selected first-pass graphics route is a private, non-destructive vanilla-
Schala compatibility diagnostic built from the user's pinned clean ROM; the
current original native-grid assets remain the later replacement-art track.
Crimson Echoes, Temporal Flux/Redux, Jets of Time, Data Crystal, and related
community guidance are graded in
`docs/community_modding_reconnaissance_2026-07-27.md`; those sources guide
breakpoints and regression cases but do not prove PC `$07`, free space, or
production ownership. The 2026-08-22 primary-source refresh is in
`docs/eighth_playable_character_external_research_2026-08-22.md`; it records
the current public implementation ceiling and the pinned arbitrary-bank
player-Tech lead selected for independent study. Its Python host plumbing is
MIT-licensed, but the embedded Mauron-attributed routine has unresolved reuse
provenance and is not imported. Project Epoch's independently reconstructed,
source-only bank-qualified package contract is in
`docs/schala_player_tech_package_bank_adapter_v0.md`; its candidate high
package selectors remain unbound, command `$1E` remains blocked, and it
installs no hook or allocation.
The candidate per-slot SRAM sidecar and its deterministic canary evidence are
tracked in `docs/sram_gap_sidecar_audit.md`; its host-side corruption,
single-slot erase, and retained/reset New Game+ semantics are now explicit,
while the SNES hooks remain unimplemented. The source-only load contract is in
`docs/schala_sidecar_load_plan_contract.md`; it requires a bound preclear
assertion plus post-vanilla-load PC `$07` roster handling. Version 2 now gives
each exact `$A0` record an explicit physical slot and a full SHA-256 binding of
the complete `$A00` vanilla slot. Valid v1 remains migration-required
safe-empty, and its reserved bytes remain zero. The exact v2 format, migration,
atomic-write ordering, New Game+ staging rule, and implementation gates are in
`docs/schala_sidecar_v2_contract.md`. These are source-only contracts: the
vanilla sidecar-bearing boot/load control is compatibility evidence only and
does not approve the gap or implement Project Epoch save/load behavior.
The executable host lifecycle in `tools/schala_sidecar_v2_lifecycle.py`
additionally proves all-three-slot ordering, partial save/erase refusal,
invalid-vanilla no-read/no-copy behavior, raw-roster SafeEmpty normalization,
staged New Game+, and exact preview invalidation without writing a ROM.
The bidirectional descriptor model in `tools/schala_save_layout.py` separately
proves that translated full load restores the protected slot
`+$0430-$047F` bytes to the candidate relocated compatibility block while a
precleared natural PC `$07` record remains untouched. It is source proof only;
no save/load hook or WRAM allocation is installed.
The same source-only model now pins normal-new-game, attract, and New Game+
initialization shapes. Normal new game splits the native `$280` seed into
seven vanilla records plus the relocated compatibility template and accepts an
independent exact `$50` PC `$07` record. The New Game+ model translates the
native partial load into four exact regions, preserving natural PC `$07` and
the roster for later retained/reset staging.
An independently curated current-bsnes attract run now carries the candidate
canary through title timeout, battle/field demo scenes, and return to title
with matched zero-control states. Vanilla overwrites natural PC `$07` during
that route while leaving `$2CA0-$2CEF` untouched, so the attract adapter is a
confirmed requirement; Project Epoch initialization is still unimplemented.
A separate current-bsnes New Game+ negative control catches the native partial
loader changing `$7E2830-$287F` in one frame to the selected slot's exact
`+$0430-$047F` bytes. Matched zero/canary runs preserve `$2CA0-$2CEF`, both
guards, screenshots, and disposable SRAM through the Battle Mode prompt. This
confirms the loader adapter requirement; it does not install that adapter or
approve the candidate allocation.
The canonical post-battle combo-learning scan is now bounded as well: its 25
live five-byte records can address only `$7E283E-$7E2856`, followed by a
sentinel, so that computed path cannot reach rock flags `$2857-$285B`.
The exhaustive event-script pass also found the one non-assembly consumer that
must move: event `$11C` at location `$1D1` has 12 absolute tech-state
reads/writes in `$2830-$283B`. Those operands must target the corresponding
`$2CA0-$2CAB` fields before natural PC `$07` is safe. The audit now constructs
that exact translation in memory, rejects any whole-packet preimage drift,
changes only 24 address bytes, and reparses the result with no old-range or
unplanned destination hit. It emits only hashes and edit metadata.
A controlled current-bsnes baseline now completes the canonical vanilla
Spekkio grant in prepared Magus/Robo/Frog and Crono/Marle/Lucca profiles.
Each matched zero/canary endpoint differs only in `$7E2CA0-$2CEF`, with
identical paired screenshots and unchanged disposable SRAM. This closes the
unmodified-event endpoint baseline. A separate native Mesen trace now
observes all 12 old-address operations with exact PC, pointer target, value,
and order in the same two matched profiles. Its guarded launcher stages an
isolated emulator and uniquely named disposable ROM/SRAM, then accepts only
the exact trace and PNG hashes while preserving all shared saves.
A second native Mesen collector now closes the translated
**already-decompressed volatile-WRAM** matrix. It requires the complete
`$0C6B`-byte source packet at `$7F2000`, changes exactly the pinned 24 operand
bytes, requires the complete transformed packet both immediately and at the
endpoint, copies all `$50` compatibility bytes from `$2830-$287F` to
`$2CA0-$2CEF`, and runs both profiles with zero/canary controls limited to the
old event-target span `$2830-$283B`. All explicit collector
`write8`/`write16` calls target `snesWorkRam`. The first full-old-block canary
calibration correctly exposed legitimate rock-flag recalculation at
`$2857-$285B`; the accepted target-only control therefore preserves the
existing learned-mask/rock-flag tail instead of overwriting it. All four
accepted runs bind CPU Y to the exact event command, require direct page
`$0100` and M set, and match each write accumulator to the deferred stored
byte. Candidate non-target bytes, the complete old block after preparation,
both guards, Epoch, ROM, SRAM, and shared Mesen saves remain exact.
The current hardened acceptance contract is the 8,934-byte
`references/mesen_event11c_relocated_trace_accepted_artifacts_v3.json`,
SHA-256
`839b86310dbe33273cf14ffec01386aa4ee6b88426b100be2cdc65d17a0790cc`.
It requires trace schema v2 and collector version 2. Acceptance v1 and v2
remain retained as historical evidence; v2 mislabeled the incompatible
hardened trace shape as trace-v1/version 1. The schema bump records the removal
of synthesized `absolute_frame`, the addition of phase fields, and the
narrowed explicit-write scope. The launcher exact-byte compiles and executes
its pinned Python modules, reads and hashes the legacy launcher only for
provenance, stages the verified collector and state, and publishes each
trace/PNG pair with exclusive creation plus identity-limited rollback. Exact
endpoint-image acceptance pins field frame modulo 16 to zero and Spekkio
sprite frame 4 for Crono/Marle/Lucca or 22 for Magus/Robo/Frog, eliminating
adjacent idle-frame nondeterminism. Both current four-trace sets pass the
schema-v2/version-2 validator, and the accepted/replay roots are byte-identical
across all eight artifacts.
This is narrow `verified-runtime` evidence for a volatile decompressed packet
only. Loading the checkpoint and executing the game may change other transient
emulator state; the host proves the source files and shared Mesen `Saves` tree
unchanged. Recompression, named ROM allocation, event-pointer installation,
hooks, global `$2CA0` ownership, natural PC `$07`, and save/load/New Game+
integration remain open.
A separate generic Mesen WRAM-ownership census now watches every byte in the
old compatibility block, active roster, joined flag, Epoch name, structural
guards, and candidate relocated block. Calibration, 600-frame field idle,
600-frame main-menu, and the Frog/Spekkio event route run as matched
zero/canary pairs. The candidate and both guards receive zero callbacks in all
eight accepted traces; Epoch, roster, and joined state receive no writes.
Field idle records 450 roster reads, the main menu records 52 old-block plus
72 roster reads, and the event route records 1,224 callbacks including the
exact `$2834/$283B` positive control and 25 same-value writes at
`$2857-$285B`. Access counters reconcile exactly with callbacks, and paired
observations are identical after candidate normalization. The accepted and
independent replay roots are byte-identical across all 16 trace/PNG artifacts.
The 10,813-byte acceptance contract is
`references/mesen_wram_ownership_accepted_artifacts_v1.json`, SHA-256
`b8f863ab2db7ed5f17222c59044a026305a05db86a7a0303fc3db84bfa197142`.
This closes only the first ownership tranche; it does not approve
`$7E2CA0-$2CEF`, relocate the block, install PC `$07`, or change Epoch.
A separate menu-only extension now runs Equipment owner switching, Tech owner
switching, Item Use/Move entry, and Party Exchange entry/cancel as eight
matched zero/canary traces. The candidate and both guards again receive zero
callbacks, while Epoch, roster, and joined state receive no writes. Equipment
and Item each record 124 reads; Tech records 132 reads plus one exact
five-byte same-value sequence at `$7E2857-$285B`; Party records 2,117 reads,
including 2,065 roster reads. Both final private roots are byte-identical
across all 16 trace/PNG artifacts. The 11,785-byte acceptance reference is
`references/mesen_wram_ownership_menu_accepted_artifacts_v2.json`, SHA-256
`c6978ec88c573dd4181e42d4645cbbd76b85612574cacfe4f8e0ef3d59bd2e04`.
The input schedule contains no final item-use, equipment-change, party-swap,
or save confirmation; inventory and equipment arrays are not watched, so this
is not byte-level proof that those systems are unchanged. It still does not
approve the candidate allocation or install Schala.
A native-Mesen 2.1.1 Lavos Core checkpoint now supplies an exact
command-ready battle boundary independent of the current-bsnes state format.
Fresh-process control and Down-to-Tech reloads preserve the complete battle
identity/HP anchor, protected WRAM, source SRAM, and immutable inputs. A
derived ownership collector then runs frame-zero calibration plus 60-frame
idle, Down/Up, and Down-to-Tech routes as zero/canary pairs. All 196 watched
bytes receive zero callbacks in both accepted and independent replay roots.
Screenshots are presentation-only; the exact JSON traces are the acceptance
gate. That battle-v3 command-only tranche proves only those bounded
command-menu routes: it executes no action, observes no enemy turn, and does
not approve `$7E2CA0-$2CEF` or the compatibility-block relocation.

A separate accepted battle-action v4 extension runs a no-input control to
frame 606, holds Attack target selection after A at frames `20-23`, and
completes one Crono Attack with a critical outcome after A at `20-23` and
`32-35`, each as an exact zero/canary pair. The control and recovery endpoints
have identical party HP `739,821,712`; only recovery lowers enemy slot 3 from
`8000` to `7038`. Every one of the 196 watched counters reconciles. The
candidate and both guards receive zero measured access, and no watched write
occurs after observers arm. The recovery timeline pins the `$AE9B` bit-`$80`
critical marker at frame 375. In each recovery variant, the only callbacks are
two reads of `$7E2980` at frame 377, with advanced PCs `$C1:4A43` and
`$C1:438A`. All six accepted JSON traces are byte-identical to an independent
replay; screenshots remain presentation-only and outside the acceptance gate.
This covers only one already-in-flight enemy action and one Crono critical
Attack. It does not approve the candidate or relocation, prove PC `$07`, or
cover noncritical Attack, attacks by other PCs, Tech, Item, status, death,
victory, teardown, or persistence paths.
The complete v4 source and private-evidence contract is
`references/mesen_wram_ownership_battle_action_accepted_artifacts_v4.json`
(`11045` bytes, SHA-256
`0d0936cccb1640109eeab09b870281ff638e736bcd75b1b77fc2ce93a319c2d6`).
The resulting direct-index and fallthrough-collision map for logical PC `$07`
is in `docs/pc7_attack_adapter_audit.md`; its read-only audit emits hashes and
five bounded lookup observations, not a ROM or table dump.
`docs/schala_focus_pulse_adapter_architecture.md` continues that chain through
action `$90`, Focus weapons `$E8-$EB`, the three-branch equipped-weapon
configuration, and its four fixed downstream consumers. Its source-only
descriptor builder now freezes one unbound `$10`-byte PC Attack record and
four unbound `$18`-byte Focus visual records. It binds only Project
Epoch-owned identities, imports no ROM or NPC data, writes no binary files,
and marks the result non-installable. A second read-only boundary contract
pins the palette map, 64 six-byte palette rows, separate swing/hit sound
tables, and the reachable enemy Attack-animation packages hit by direct
`$E8-$EB` lookups. Those package offsets are explicitly kept separate from
the PC normal-Attack selector namespace. The existing visual descriptor
remains unchanged: its zero pointer may eventually locate a separately
versioned composite packet, but no palette, sound, graphics, allocation, or
hook binding is approved.
The first source-only vertical slice now gives Glass Focus (`$E8`, visual 0)
six original basic-Attack poses, six standalone Focus shapes, and independent
integer-only swing/hit audio recipes. The source truthfully records reuse of
Project Epoch's own Schala body pixels, imports no ROM/NPC/vanilla-PC pixels
or sampled game audio, and leaves every native ID and pointer null. A
reproducible metadata-only audit inventories 174 candidate tile occurrences
and 7,264 canonical playable-PC tiles. It excludes 80 candidate and 59
reference tiles having at most two visible pixels, then reports zero exact or
palette-pattern matches across the remaining 94 by 7,205 comparison. It makes
no NPC-originality claim by itself and installs nothing.
An independent additive packet audit now proves that the unchanged ten
gameplay frames and six Glass Focus body poses fit one native-shaped partial
body packet: sixteen `$28`-byte records, 91 tiles including blank tile 0,
`$0B60` graphics bytes, `$0280` assembly bytes, and exact reconstruction of
all 16 source canvases. The existing ten-frame graphics and assembly streams
remain exact prefixes; the six poses add only ten unique tiles. These are
provisional source ordinals, not animation IDs. No Focus insert, sound,
pointer, allocation, action/item binding, PC `$07`, save path, or Epoch data
is assigned. The metadata-only report and stop gates are in
`docs/schala_current_body_packet_v0.md`.
The follow-on fail-closed semantic audit now proves that native animation
`N` starts at byte offset `N * 4` but is not a fixed four-byte record, that
facing values `$00-$03` use the statically verified order documented as
up/down/left/right, and that `$E4:2800` is the
separate one-facing timing/control family rather than graphics data. It pins
the fixed-bank field, menu, and battle readers; menu roles `$00/$01/$0B`;
the minimum battle anchors `$00/$03/$08/$0A/$0C/$12/$1A/$23`; and all
sixteen records in the `$CC:F77F` battle-state selector table. Magus's timing
contract ends at `$E4:AFB4`; the following tail remains unclassified and is
not free space, while `$E4:B600` and `$E4:B614` are occupied successor
entries. This is metadata-only static evidence, not a Schala frame binding,
animation blob, allocation, hook, or PC `$07` runtime claim; see
`docs/schala_animation_semantic_contract_v0.md`.
A companion fail-closed, read-only census now inventories all 10,637 encoded
location-event `$AA/$AB/$AC/$AE/$B3/$B4/$B7` animation/static sites. Its
complete 116,064-entry function topology includes 2,269 entries outside their
nominal physical owner, so the auditor uses an incoming direct-entry marker
closure instead of physical adjacency. The 927 PC-only-marker, 23 mixed, and
1,794 no-PC-marker source-owner buckets are a syntax-only possible-context
overapproximation, not runtime identity. Calls, jumps, fallthrough, loader
lifetime, and reachability remain open; see
`docs/location_event_animation_operand_census_v0.md`.
A separate hardened, isolated native-Mesen probe has now reproduced the field
timing relationship twice per route at the prepared Spekkio checkpoint. Idle
selector `$00` repeatedly terminates and reloads through the timing stream;
holding Right switches the Magus leader to selector `$01` and executes the
six right-facing frame bytes `$10-$15`, each paired with delay `$07`, before
timing zero resets the cursor. The following primary `$FF` is statically
present but is not fetched on that path. These are checkpoint-bounded,
exploratory runtime findings; no PC `$07`, Schala render, movement success,
save behavior, allocation, or installed adapter is inferred.
Only the bounded launcher, collector, synthetic tests, and public-safe receipt
are tracked; all raw runs and game/emulator artifacts remain ignored. Exact
source identities, fresh-run receipts, containment gates, and nonclaims are in
`docs/schala_field_animation_runtime_probe_v0.md`.
A separate fail-closed corpus audit now decodes all 241 structurally valid
compressed graphics packets in `$07-$F7`; the 237 selectors reached by the
audited NPC and normal-enemy descriptor tables remain a distinct subset, and
the four catalog-only selectors are not declared unused. From that corpus, a
pinned static chain identifies the one 79-tile packet used by the documented
Schala NPC descriptor family. The current gameplay foundation and Glass Focus
sources have zero exact or palette-renaming-invariant H/V/HV matches against
its 78 nontrivial tiles. This is bounded one-packet evidence, not a global
NPC/enemy, near-match, silhouette, animation, palette-art, or runtime-identity
claim; see `docs/ct_compressed_sprite_corpus_audit.md` and
`docs/schala_npc_originality_audit_v0.md`.
The exact profile-1 SHA-256 binding now has two standalone current-bsnes
implementations: the correctness baseline passes at 366-367 frames per slot,
and a separate fixed-rotate candidate passes at 123-124 frames. The latter is
about three times faster. A third round8/table candidate passes at 68-69
frames, about 5.3 times faster than the reference, but still exceeds its
predeclared 30-frame stop gate.
The separately downloaded 2026-08-22 rolling bsnes DLL reruns that standalone
candidate twice with the exact same `68,69,69` result vector, serializer 115.1,
defined evidence hashes, and bounded nondeterminism. It also completes two
isolated 120-frame clean-ROM load/serialization smokes while preserving exact
ROM and all-zero disposable SRAM bytes. This is a new pinned runtime line, not
a replacement for the July replay core or proof of full gameplay
compatibility; see `docs/current_emulator_update_2026-08-22.md`.
All three use original synthetic all-`$FF` benchmark cartridges under
`private/`; none reads or patches Chrono Trigger. Reproduction hashes,
two-run evidence,
and remaining gates are in
`docs/schala_sidecar_sha256_65c816_benchmark.md`. The completed bounded
acceleration experiment, its stop result, and the explicit profile decision
are in
`docs/schala_sidecar_binding_performance_architecture.md`.
The preferred live compatibility-block relocation and canary matrix are in
`docs/wram_compatibility_block_audit.md`; the selected Schala action identity
overlay is in `docs/schala_command_namespace_architecture.md`.
The inert 8 MiB ExHiROM scaffold and explicit-allocation/BPS plan are in
`docs/schala_rom_expansion_architecture.md`.
The complete canonical location-event item-reference audit is in
`docs/location_event_item_reference_audit.md`; it finds no `$E8-$EE` claims
but does not yet declare those proposed Schala item IDs globally free.
Their fixed, allocation-neutral overlay descriptor is documented in
`docs/schala_item_namespace_architecture.md`; all ROM pointers remain unbound.
Schala's original level policy, base stats, HP/MP and stat growth, TP cadence,
and starting loadout are documented in
`docs/schala_progression_foundation_v0.md`; its deterministic `$48`-byte
Project Epoch descriptor is deliberately not a vanilla character record and
is not yet ROM-installable.
The original recruitment branch/dialogue state machine is documented in
`docs/schala_recruitment_content_foundation_v0.md`; all event-engine bindings
remain deliberately null. Their bounded static routing is now documented in
`docs/schala_recruitment_engine_binding_audit.md`, including the full-party
displacement, Epoch-name collision, and New Game+ loader constraints. A
current-core North Cape trace now verifies the full-party vanilla reference:
Magus is registered in reserve before name acceptance, then the native party
exchange can place him in the active formation without any source-SRAM write.
The resulting reversible-stage, caller-witnessed-grant, and later
caller-supplied-slot binding is frozen in a host-tested, runtime-unverified
source contract at
`docs/schala_recruitment_transaction_contract.md`; its tests use only a
registered synthetic non-installable PC `$07` fixture.
The first clean-room native-grid gameplay pixels and deterministic SNES packer
are documented in `docs/schala_gameplay_sprite_foundation_v0.md`; the bounded
comparison against all seven canonical PC graphics windows is in
`docs/schala_gameplay_originality_audit_v0.md`. This is a partial field/battle
animation foundation, not yet a ROM-integrated sheet. Its ten current frames
also compile into the measured native four-object packet shape and reconstruct
exactly; see `docs/schala_sprite_packet_foundation_v0.md`.
The first four cardinal records now have a private, save-isolated supported-
slot runtime proof after Continue/load and field movement; the accepted replay
and clean control are in `docs/schala_supported_slot_sprite_smoke_v0.md`.
For the next private compatibility pass, the canonical vanilla Schala NPC
family can now be reconstructed at local build time from the user's exact
clean ROM. Its 23 records, 79 tiles, four aligned facing blocks, twelve-color
palette, strict hashes, private-only output boundary, and explicit nonclaims
are documented in `docs/schala_vanilla_npc_source_compatibility_v0.md`.
No extracted bytes are checked in, no ROM or patch is emitted, Crimson Echoes
content is absent, and the original Project Epoch art remains preserved as
deferred replacement-art research.
The five field palette reload paths and all ten shadow-copy sites are mapped in
`docs/field_sprite_palette_loader_audit.md`; its `$FFFF` source-key resolver is
an uninstalled adapter proposal for Schala's fifteen visible colors.
The complete bounded `$50`-byte playable-record schema, including the separate
new-game and attract/demo hazards, is in
`docs/pc_init_record_schema_audit.md`.

## Recovered inputs

- `references/PHASE1_FINDINGS_FOR_LILY.pdf`
- `references/PHASE1_FINDINGS_v2_FOR_LILY.pdf`
- `references/project_epoch_character_data_atlas_v0.md`
- `recovered/ct_lucca_to_magus_clone_v0_bundle.zip`

The clean ROM is local-only under `private/` and is ignored. Its expected SHA-1 is:

`de5822f4f2f7a55acb8926d4c0eaa63d5d989312`

## Safety

Read `AGENTS.md` before changing patch code. In particular:

- preserve the non-PC save region beginning at `$0430`;
- do not write graphics entries `$07` or `$08`;
- do not infer free space from zero bytes;
- do not commit ROMs, saves, emulator states, or raw traces.

The provisional runtime patch overwrites Lucca's live WRAM record. Although
the builder never edits an SRM, saving in-game afterward may persist the cloned
record. Its tech-state writes also map structurally to save-slot `$0432/$0439`
inside the conventionally labeled `$0430` region. Use only a disposable save
copy and do not save during the diagnostic. It also overwrites vanilla
enemy-reward records in ROM and is therefore known unsafe.
