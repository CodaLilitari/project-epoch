# Project Epoch: Schala eighth-character developer guide

Status: active engineering guide  
Selected eighth character: Schala  
Target logical playable ID: `$07`  
Last updated: 2026-08-22

This is the living implementation and verification guide for adding Schala as
a genuine eighth playable character. Update it whenever a ROM fact is proved,
an architectural decision changes, a builder emits a new artifact, or an
emulator checkpoint is completed.

The project is not yet at the point where logical PC `$07` may be activated.
The supported-slot clone, Schala packet smoke, and static audits have now
exposed the principal seven-character assumptions. The translated event
`$11C` consumer has a four-case `verified-runtime` proof for an
already-decompressed packet patched only in volatile WRAM. The current 10
gameplay frames plus six Glass Focus body poses now also have independent
`verified-static` proof that they fit one 16-record native-shaped partial
packet and reconstruct exactly. The next art/engine gate is the semantic
animation-slot and auxiliary-animation contract, not a speculative full sheet.
The remaining production gate is still to install and prove the complete
relocated compatibility lifecycle and sidecar behavior, complete Schala's
field palette/frame adapters, and implement the selected record, command,
item, and recruitment boundaries. A booting ROM or a visually plausible
sprite is not sufficient evidence.

## 1. Evidence vocabulary

Every technical claim in this guide uses one of these labels.

- `verified-static`: proved from the canonical ROM, a deterministic builder,
  or byte-for-byte artifact inspection.
- `verified-runtime`: reproduced in an emulator with recorded input and
  hashed evidence.
- `documented`: supported by an identified technical source but not yet
  independently traced here.
- `hypothesis`: a proposal or plausible interpretation awaiting proof.

Creative character design is labeled `proposal`. It is never evidence that an
engine representation exists.

## 2. Non-negotiable safety rules

- Do not distribute ROMs, saves, emulator states, raw traces, or extracted
  copyrighted graphics.
- Builders may read the pinned clean ROM, but release artifacts must be
  deterministic source plus IPS/BPS patches, manifests, hashes, and reports.
- Preserve save-slot region `$0430-$047F`. It is not an eighth PC record.
- Do not overwrite graphics-source entries `$07` or `$08`.
- Do not use file `$0D400E` as an eighth-PC normal-attack byte. It is also
  Crono's critical-attack entry.
- Do not make `$07` work by rewriting it to Magus `$06` in WRAM.
- Do not assume zero-filled ROM or save bytes are unused.
- Treat the complete canonical ROM as default-deny for production data.
  Production payloads require named expanded allocations; instruction hooks
  require exact proved sites and pinned preimages.
- Keep the trusted production hook and allocation catalogs empty until their
  individual runtime/evidence gates pass. Metadata may not self-approve a
  write.
- Preserve the Epoch name at `$7E2C4D-$7E2C52`. The compatibility relocation
  `$7E2CA0-$7E2CEF` and SRAM sidecar `$30:7E00-$30:7FDF` remain candidates,
  not free space.
- Do not save in-game after an unsafe runtime experiment unless the test uses
  a disposable SRM and the serialization effect is the object of the test.

The complete repository rules remain authoritative in `AGENTS.md`. The
machine-enforced ROM policy and current protected-range catalog are documented
in `docs/rom_write_intent_guard.md`.

## 3. Pinned inputs and reproducibility

### Canonical clean ROM

- Title: Chrono Trigger (USA), unheadered US Rev 0
- Size: `0x400000`
- SHA-1: `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- SHA-256:
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`
- Local-only path:
  `private/input/rom_archive/Chrono Trigger (USA).sfc`

### Recovered Lavos save

- Size: `0x2000`
- SHA-256:
  `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`
- Local-only path: `private/input/lavos_save/chrono_trigger.srm`
- `tools/inspect_ct_srm.py` validates all three vanilla magic/checksum pairs.
  Slot 1 is location `$01DA`, storyline `$D6`, active party `00 01 02`, roster
  `00 01 02 82 80 04 03 06 05`: the Lavos Tunnel save point immediately
  preceding the Lavos Core encounter. A current-core canary replay now walks
  from that save point into location `$01DB`, advances the bounded party
  dialogue, and reaches the visible native Lavos battle. The source file
  remains read-only; current-core runs use same-stem disposable copies.

### Active emulator baseline

RetroArch 1.22.2 remains the newest stable frontend observed on 2026-08-22.
Its executable and official portable archive remain pinned at:

- executable SHA-256:
  `81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a`;
- portable archive SHA-256:
  `b2139b1d0f9d4526dc6b5ce23cbb3efdc766096fa6f2c3df016818b486ac6372`.

Two portable installations now exist on `C:` without overwriting either the
old runtime or a user profile:

- restored July harness:
  `private\tools\RetroArch-1.22.2-ProjectEpoch-20260724`;
- current rolling-core harness:
  `private\tools\RetroArch-1.22.2-ProjectEpoch-current-20260822`.

The 2026-08-22 official rolling bsnes archive is 1,056,730 bytes, SHA-256
`60441409e6877b52bb135588cba1b278d7713db0ec512b188aae66599ced3081`.
Its extracted DLL is 5,661,090 bytes, SHA-256
`bb00b395dcac6db960ecacaaf40ea9906fea9b7e23cedf55f8d117c44fcdde78`.
The core-info display version remains 115, but that display string is not a
binary identity. The moving buildbot URL and observed repository head are
recorded separately because the binary has no per-artifact source-commit
attestation.

The new DLL is a separate evidence line. It passed two independent runs of the
standalone round8 diagnostic with exact `68, 69, 69` frame results, serializer
115.1, identical defined result/scratch/SRAM evidence, the known eight-byte
serializer span, and zero unaccounted differences. Two additional isolated
120-frame canonical-clean-ROM copies loaded, exited cleanly, serialized state,
and preserved exact ROM and all-zero SRAM bytes. The early thumbnails are
black, so those runs make no visual-title claim. Exact install provenance,
manifests, hashes, reproduction commands, and limitations are in
`docs/current_emulator_update_2026-08-22.md`.

The extensive July BSV2 replay matrix remains accepted only against its exact
older core DLL SHA-256
`003c7de04adef5f64fa106ef5175a0f66b08032001bde0383af97c5e5b81d470`
and archive SHA-256
`6372add6a383a9373c27f97a2378f6a1ed9fb5e4e419d74cb4ba3601f59f2965`.
Its logs retain their original `private\tools\RetroArch-1.22.2` provenance.
The restored `C:` bytes do not rewrite or reclassify those manifests. That
matrix covers Continue, save loads, field/menu/equipment/party exchange,
North Cape fight and Magus recruitment, Lavos battle entry, soft reset, and
matched inert-ExHiROM controls; see
`docs/current_emulator_replay_harness_2026-07-26.md`.

Both core lines can open same-stem SRAM directly even when the frontend says
SRAM is skipped. Every run therefore requires a unique disposable ROM/SRAM
pair and before/after hashes. Save states remain binary-pinned and are never
assumed interchangeable across core DLLs.

### Legacy evidence baseline

- RetroArch 1.7.1 SHA-256:
  `bb8d1bb0a781c3fab2c4d08dd9d1dd1abe365cd5c339af6353870e73bdd79a76`
- bsnes2014 Performance core SHA-256:
  `4d1708574ae059cb4f43ad995c0276ca03e2693bc6a7612e4e8f4343d48a317d`

Existing hashed bsnes2014 results remain historical evidence for their stated
checkpoints, but its savestates and flat BSV1 streams are not inputs to the
active current-core matrix. New runtime approvals require regenerated
current-core checkpoints.

All ROMs, saves, states, screenshots, videos, and recorded-input movies stay
under ignored `private/` paths.

### Byte-matched static reconstruction

`verified-static`

- Upstream: `https://github.com/dscotton/ct_disassembly`
- Local reference: `references/ct_disassembly`
- Pinned commit: `eeae27acdb6565e96d1d796a3d60792c250c0aa1`
- License: CC0
- Target ROM: the same unheadered US v1.0 image, CRC32 `2D206BF7`

The upstream project separates code/structure from copyrighted game data and
documents a byte-identical rebuild after extracting data from a user-supplied
ROM. This workspace uses the committed assembly as a navigation aid and
checks instructions and table bytes against the pinned private ROM. It does
not run extraction inside the reference clone. Some semantic labels were
community/AI-assisted, so a label alone is not runtime proof.

## 4. What has been accomplished

### 4.1 Recovered and reproduced diagnostic v0

`verified-static`

- Recovered the prior Lucca-to-Magus clone bundle unchanged under
  `recovered/`.
- Reproduced its 510-byte IPS exactly from the canonical ROM.
- Supplied and reproduced IPS SHA-256:
  `39b9a3ea6c7354f5ecfcfe312a79a97fd29ece635deb3beb8e4468e5581a2626`.

### 4.2 Completed deterministic diagnostic v1

`verified-static`

The source builder `tools/build_lucca_to_magus_clone_v1.py` now accounts for:

- four field/battle graphics-source table families;
- all eight single-tech entries across five known table families;
- full `0x200`-byte portrait tiles and the portrait palette;
- three per-PC attack-selector families;
- eight TP-learning thresholds;
- the known menu-element selector;
- SNES checksum/complement repair;
- deterministic IPS reapplication and invariant checks.

Normal static IPS:

- Path: `output/patches/ct_lucca_to_magus_clone_static_v1.ips`
- SHA-256:
  `20fcbd08b954311cb948bbcfc0a90eb3bbb6cc46ad00524c0add8ac0e9ecc0d7`
- Patched-ROM verification SHA-256:
  `4c4ea60434e22c19df0278aeb89ab03f566cdf7323c6fd0a31d2f6739d80666e`

Quarantined runtime experiment:

- Path:
  `output/experimental/ct_lucca_to_magus_clone_runtime_v1_UNSAFE.ips`
- SHA-256:
  `484bad4051f39d92015f57a927471d8287ca4e3652a1eef5a9475fabbf4b3cae`
- Patched-ROM verification SHA-256:
  `b0538af193fbac24773a78b593de12fed47eb63e7e4dd70cfb11994f9f5e8f43`

The runtime output is not a release patch. Static reconstruction now proves
that its `$CC:63F6-$CC:642F` payload overwrites part of
`EnemyRewardTable` (`$CC:5E00-$CC:64FF`, 256 seven-byte records). It is known
unsafe and retained only to reproduce the earlier negative experiment.

### 4.3 Emulator proof and negative result

`verified-runtime`

The static clone passes:

- boot;
- Continue and save-select;
- slot load;
- coherent Magus portrait in Lucca's row;
- coherent field sprite in Lucca's supported slot;
- recorded field movement.

This proves selected graphics and portrait paths for supported PC `$02`. It
does not prove an eighth roster slot.

The provisional runtime hook reaches the same field checkpoint but does not
leave Magus's `$50`-byte live record cloned over Lucca. Paired emulator states
show:

- live Lucca state offset: `28995`;
- live Magus state offset: `29315`;
- delta: `0x140`, matching `$7E26A0 -> $7E27E0`;
- runtime-patched Lucca record: byte-for-byte original Lucca data.

Static reconstruction resolves the ambiguity: `$CC:E980` belongs to
`Field_SpriteAnimComputeBase`. It reads the three active-party IDs and derives
graphics and animation indexes. It is not a character-record initialization
hook. The shim is retired and must not be extended or used as architecture.
Full results are in `docs/emulator_test_results_2026-07-25.md`.

The replacement current-core harness is documented in
`docs/current_emulator_replay_harness_2026-07-26.md`. It source-confirms and
tests tagged BSV2 input editing, loads isolated save slots, constructs raw
current-core checkpoints, and anchors live WRAM at state offset `$2284`. The
exact `$7E2CA0-$2CEF` canary survives field and menu idle, Equipment
character selection, a real seven-PC party swap, both North Cape decision
branches, full-party Magus reserve registration, a second party swap that
places the new recruit in the active formation, and normal narrative battle
entry. A Player-1-only soft reset returns to the vanilla intro and clears the
candidate block to zero. Matched current-core inert ExHiROM controls are
byte-exact across the raw core state for field, menu, Equipment selection, and
the full 3,599-frame idle. That reset result requires a future Project Epoch
post-reset initializer; none of these results approves the allocation.

### 4.4 Schala content direction

`proposal`

Schala is the selected eighth character. The content target is described in
`docs/schala_character_design_v0.md`:

- defensive Shadow-magic controller, working title "Astral Regent";
- eight original single techs;
- bounded dual/triple-tech launch set;
- unique Focus weapon family and Schala-specific equipment;
- optional late-game recruitment quest, "The Silent Palace";
- explicit balance ceilings against all seven vanilla PCs.

The command content now also exists in a machine-readable authoring pack:

- source:
  `assets/source/schala/v0/content/schala_tech_content_v0.json`;
- canonical normalized SHA-256:
  `90f43fb7602682911829a1077fb91b824a61e9071931eec1e0832c8a96590c2b`;
- validator: `tools/validate_schala_content.py`;
- coverage: eight original single techs, six duals, two triples, and the
  original Focus Pulse basic attack at pinned IDs `$80-$90`.

The pack records names, descriptions, targets, MP budgets, effects, learning
rules, and animation families. Every native primitive binding is deliberately
null and the pack is marked `authoring-only-unmapped`; no proposed mechanic is
approved for ROM encoding until its data path is traced.

A bounded static primitive audit is now recorded in
`docs/schala_tech_primitive_binding_audit.md`. It identifies safe reuse of the
existing damage, heal, cleanse, status, revive, line, and radius machinery;
proposes an original high-ID per-component descriptor for independent
properties, MP costs, elements, and visual-only passes; and keeps Sanctuary,
Astral Gate's timed penalty, Phase Engine, and New Dawn behind explicit
new-control-flow gates.

The original item set is also machine-readable:

- source:
  `assets/source/schala/v0/content/schala_item_content_v0.json`;
- canonical normalized SHA-256:
  `dfa3f66d079a8921ff088b99f2ba507cf205525ab47fb11da609704e90c2fd85`;
- validator: `tools/validate_schala_items.py`;
- candidate IDs `$E8-$EE`: four original Focus weapons, Regent Mantle,
  Crescent Clasp, and Pendant Shard.

Structured scans find those high-band IDs blank/inert and absent from shops,
enemy rewards, reachable treasures, starting equipment, and pinned enums.
All 513 canonical location-event pointer entries and 489 valid referenced
scripts have now been audited. There are zero fixed `$E8-$EE` operands and
zero unresolved computed item references, so the IDs are
`verified-static: unclaimed by canonical location events`. They are still not
globally free or active: every high-band classification/equipment adapter and
the runtime matrix remain unresolved. Native item bindings are null. The
complete record and hook architecture is in
`docs/schala_item_namespace_architecture.md`.

The original item overlay now also has a fixed, allocation-neutral `$20`-byte
descriptor and a deterministic seven-record `$E0` table. It carries direct
Magic and Magic Defense amounts, class/equip/behavior flags, distinct Focus
visual identities, and 24-bit description/visual pointer fields. Eight tests
pin the layout and item semantics. Both pointer sets remain zero and the
manifest explicitly says `rom_installable: false`; this closes a data-format
gate without pretending that classification hooks or expanded allocations
exist.

Schala's original progression data is now machine-readable:

- source:
  `assets/source/schala/v0/content/schala_progression_v0.json`;
- canonical normalized SHA-256:
  `17e25577bfb80998e33c5ac0890147231a5e1d3674de8af97e6fdf242f51aab5`;
- recruitment level: median active-party level, clamped to 30-45 with a
  level-35 fallback;
- authored level-one HP/MP and seven-stat basis, four-bracket HP/MP growth,
  seven-stat growth, and eight-step TP cadence;
- starting learned count three with the engine-correct high-bit mask `$E0`;
- original starting loadout: Glass Focus `$E8` and Regent Mantle `$EC`.

`tools/schala_progression.py` validates those decisions, projects levels, and
packs a deterministic `$48`-byte Project Epoch overlay with SHA-256
`b95a0a3d8397706f2c83472539ee208ebaef1af3e9e6057691b0b1c00dedaaff`.
Nine tests pin the format, provenance, projections, caps, TP delta conversion,
and loadout. The overlay is deliberately not a vanilla `$50`-byte character
record and is marked `rom_installable: false`; record bytes `$01/$02`,
experience, current-stat recomputation, reader hooks, and runtime balance
remain gates. The full basis is in
`docs/schala_progression_foundation_v0.md`.

The compiler also pins the runtime-confirmed seven-stat order as Power,
Stamina, Speed, Hit, Evade, Magic, Magic Defense. This corrects a misleading
order in an older disassembly data label before any ROM binding; Schala's
authored meanings and level projections are unchanged.

The original recruitment flow is also machine-readable:

- source:
  `assets/source/schala/v0/content/schala_recruitment_content_v0.json`;
- canonical normalized SHA-256:
  `fbffbc7bd9bed555ed7966ed62f6b9b247b4403986fef358711e9e00e13520eb`;
- 28 graph nodes, including 11 original dialogue nodes;
- seven executable acceptance scenarios;
- 29 explicit engine dependencies, all unmapped with null bindings.

The graph covers Magus present/absent, accept/decline, an open or full active
party, already-recruited idempotence, and both retained/reset New Game+
states. It grants the original starting tech/item references exactly once
behind a separate guard. It contains no copied dialogue, event bytes, guessed
opcodes, addresses, or free-space claims. This is an authoring-only
`hypothesis`, not an encoded event. The validator and remaining runtime gates
are documented in `docs/schala_recruitment_content_foundation_v0.md`.

A bounded engine-routing audit now maps all 29 dependencies to reusable
vanilla primitives or explicit Project Epoch adapters while leaving every
authored binding null. It proves three especially important constraints:

- active-party insertion must be preceded by a real capacity check, because
  vanilla party operation 1 displaces active slot 3 when the formation is
  full;
- name-entry ID `$07` writes the Epoch name at `$7E:2C4D`, and the dialogue
  PC-name table entry for `$07` is null, so Schala needs separate live-name,
  name-entry, and dialogue-substitution adapters;
- retained/reset New Game+ policy must be normalized in the partial-loader
  path before the recruitment graph evaluates state.

The complete routing table, exact addresses, stop conditions, and reproduction
steps are in `docs/schala_recruitment_engine_binding_audit.md`. Recruitment
remains uninstalled.

The full-party user-facing sequence now also has a current-core vanilla
reference trace in
`docs/vanilla_magus_recruitment_runtime_trace_2026-07-26.md`. A checksum-valid
pre-Magus slot was loaded from an isolated disposable SRAM. On the recruit
branch, Magus is present in reserve before name acceptance; accepting the name
opens party exchange, and the new recruit can replace an active PC. The other
choice reaches the native Frog-versus-Magus battle. Every checkpoint preserved
the relocation canary and guards, and every disposable/source SRAM retained
its original hash. This validates the authored sequence—capacity check,
reserve registration on the full branch, independent naming, then optional
party exchange—without making PC `$07` or its vanilla name path safe.

That runtime reference is now frozen into
`tools/schala_recruitment_transaction.py`, a host-tested but
runtime-unverified source contract. It keeps the checksum-bound sidecar
preimage, reversible live reserve stage, caller-witnessed complete-grant
commit, and later exact-slot save/checksum binding as four separate states.
It also:

- accepts only two registered non-installable `host-fixture` gates bound to
  one exact synthetic record hash and identity byte `$07`; arbitrary
  self-consistent gate tokens fail, and no runtime token level exists yet;
- reuses inactive `$87` when available and never replaces a full active slot;
- keeps all name values opaque while carrying the seven PC buffers and Epoch
  buffer unchanged;
- sets the join-grant guard only after a caller-supplied witness asserts all
  three components; the model does not observe live grants;
- emits party exchange as a post-commit action on the full branch;
- re-derives sealed live state from its exact plan and witness, rejects
  resealed forged fields and polymorphic subclasses, and makes an
  already-recruited entry effect-free;
- computes the binding checksum from exact serialized `$A00` slot bytes
  rather than accepting a caller-supplied checksum integer, then verifies
  that the serialized roster and joined bit agree PC `$07` is recruited.

The 18 focused tests use only a synthetic, non-installable `host-fixture`
record. No production record token, name allocation, party hook, grant
adapter, or save hook is approved. The exact ordering, hashes, reproduction,
and remaining gates are in
`docs/schala_recruitment_transaction_contract.md`.

`tools/schala_sidecar_load_plan.py` now supplies the separate source-only load
decision. It accepts one immutable complete SRAM image and exact slot, requires
a full-image/slot-bound caller assertion that live PC `$07` was precleared,
and emits either a no-publication safe-empty result or an identity-gated
prepared v2 load. Its 20 focused tests reject forged, resealed, subclassed,
stale, wrong-source, malformed-roster, and colliding-slot values; valid v1 is
migration-required safe-empty. The witness is not runtime observation, and
the planner chooses no address or hook. See
`docs/schala_sidecar_load_plan_contract.md`.

### 4.5 Staged visual-source policy

#### Phase A: private vanilla-NPC compatibility provider

`verified-static` for local source reconstruction; no runtime claim

The first visual integration pass now uses the unmodified canonical Schala NPC
family reached through NPC `$09`, graphics selector `$26`, assembly selector
`$1B`, animation selector `$3B`, and palette selector `$80`. The fail-closed
builder derives it transiently from the user's pinned clean ROM and permits raw
outputs only beneath the ignored `private/` tree. The checked reference contains
metadata and hashes only.

The provider contains 79 graphics tiles, 23 exact `$28`-byte assembly records,
four aligned 36-byte primary animation blocks with nine entrypoint starts per
facing, one 36-byte auxiliary block, and twelve character-specific palette
colors. Its assembly uses every tile index 0-78, and the primary animation
references every record 0-22 without exceeding that range. This is enough to
justify a private supported-slot field diagnostic before the original sheet is
redrawn.

PC `$07` must reach this provider through independent bounded adapters. The
diagnostic may not relabel or overwrite NPC `$09`, its descriptor, selector
`$26`, graphics entries `$07/$08`, any existing actor or vehicle data, or any
Epoch name/vehicle path. Unsupported animation roles remain explicitly
unbound or use a documented safe fallback. No extracted packet, tile, palette,
animation stream, screenshot, ROM, or patch enters source control. Full details
are in `docs/schala_vanilla_npc_source_compatibility_v0.md`.

Crimson Echoes and Flames of Eternity additions are disabled unless an exact
source asset, author, revision, and explicit reuse license or permission are
pinned. ROM-, patch-, screenshot-, or reconstruction-only pixels are not an
acceptable source.

#### Phase B: original Chrono Trigger-style replacement art

`proposal`

- Path: `assets/concepts/schala_playable_concept_v0.png`
- SHA-256:
  `4799352c9e4a273bc88be56e1f9d472b1a1723411956857160ab89919d7bfd45`

The image is a concept reference generated for this project. It deliberately
retains only high-level identity cues—blue hair, Zeal royalty, celestial
magic—while creating a new travel costume, silhouette, focus, poses, and
portrait direction.

An additional concept-only sprite-production reference tightens the new
travel silhouette:

- Path: `assets/concepts/schala_playable_sprite_reference_v1.png`
- SHA-256:
  `8b9d38332eb4b1b7f66ad5ce4bff995772fa890cb3561bcb62ba6f42f9fcc456`
- Prompt:
  `assets/concepts/schala_playable_sprite_reference_v1.prompt.txt`
  (`fe153468cd3363f92482546e4cda930ec13b989064751216adb8a583c237b611`)
- Generator: OpenAI built-in image generation workflow.
- Generation role: original visual reference; never a ROM input.
- Design changes: high knot and short braid, shorter mantle, clearly visible
  legs, no permanent weapon, and a focus shown only while casting.

The image-generation workflow influenced the silhouette reference only. It did
not sample ROM data, and no generated pixels are eligible for packing. Neither
concept is ROM-ready artwork. Do not rescale, quantize, or paste either into
the ROM. Final field sprites, battle sprites, and portraits must be redrawn on
the actual SNES tile grid and checked for copied tile clusters against every
vanilla PC and Schala NPC source.

The existing concepts and original target-grid assets remain preserved
unchanged as a provenance-backed experimental foundation. They are no longer
the default Phase A graphics because their current style is not yet a close
enough match for Chrono Trigger. Their source manifests, hashes, and
originality findings remain valid for this deferred branch.

#### Original target-size portraits

`verified-static` for source format and deterministic packing

Two independent, hand-authored indexed portraits now exist:

- canonical source:
  `assets/source/schala/v0/portrait/schala_portraits_v0.json`;
- source SHA-256:
  `55f5ba865ef60e0e663268f9dc7e3cbccc556b5fc42b0a72f8e4732c769ea3d9`;
- full portrait: 48x48, 36 tiles, exactly `0x480` packed bytes;
- save preview: independently composed 32x32, 16 tiles, exactly `0x200`
  packed bytes;
- shared palette: sixteen entries, exactly `0x20` packed bytes.

`tools/build_schala_portraits_v0.py` validates provenance, rejects crop and
common nearest-neighbor derivations, round-trips SNES 4bpp bytes, and renders
QA PNGs from the packed output. The two portraits share no non-trivial exact
8x8 tile. A bounded in-memory comparison of 48 non-trivial candidate tiles
against all 252 canonical uncompressed menu-portrait tiles found zero exact
or palette-renaming-invariant pattern matches, including H/V/HV flips.
Compressed NPC/field/battle art and actual ROM loading remain gates.
Reproduction and hashes are in
`docs/schala_portrait_asset_foundation_v0.md`; the bounded canonical-ROM
comparison is in `docs/schala_portrait_originality_audit_v0.md`.

#### Original gameplay sprite foundation

`verified-static` for source validation and deterministic packing;
`proposal` for the partial visual design

The first ten native-grid gameplay frames now exist as project-owned indexed
source:

- canonical source:
  `assets/source/schala/v0/gameplay/schala_gameplay_foundation_v0.json`;
- source SHA-256:
  `9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2`;
- four independently authored 24x32 cardinal field idles;
- a three-key 24x32 downward walk cycle;
- 40x40 battle-ready, cast-gather, and cast-release keys;
- one sixteen-entry palette with index 0 transparent.

The pixels were authored directly as palette-index rows without importing,
tracing, transforming, resizing, or sampling any NPC, PC, portrait, concept,
ROM, save, or emulator-state bitmap. The written silhouette vocabulary keeps
Schala recognizable—indigo hair, light split garment, asymmetric mantle,
crescent detail, casting-only focus—without copying the NPC gown or tiles.
`tools/build_schala_gameplay_foundation_v0.py` reproducibly packs exact SNES
4bpp and renders QA images only from the packed bytes. A metadata-only
canonical-ROM audit then identified and removed five incidental sparse
edge-fragment coincidences without displaying or exporting reference pixels.
Eighteen focused checks now cover dimensions, provenance, palette, round
trips, budgets, focus use, cross-context sharing, and all 7,264 tiles in the
seven playable-character graphics windows. The final packed source has zero
exact or palette-renaming-invariant matches, including H/V/HV flips.

This remains a partial animation foundation, not a complete sheet or
production ROM integration. A separate deterministic compiler proves that all
ten current frames fit ten native-shaped `$28`-byte assembly records and one
81-tile raw graphics packet, with exact reconstruction from serialized bytes.
A private Lucca-slot diagnostic now also verifies the first four cardinal
records after a recorded Continue/load and field movement. It emits no
complete animation blob, expanded allocation, production hook, or PC `$07`
claim. The vanilla field path also loads only twelve character-specific
colors, so Schala's fifteen-visible-color art requires a dedicated palette
adapter. The packet format, object-cover algorithm, hashes, and remaining
gates are in `docs/schala_sprite_packet_foundation_v0.md`; the accepted
runtime replay and rejected inherited-state checkpoint are in
`docs/schala_supported_slot_sprite_smoke_v0.md`.
The full frame inventory remains mandatory. The conservative compressed
NPC/enemy corpus is now decoded and the current frames pass a bounded
comparison against the one documented Schala-family packet, but the complete
future sheets still require the broader corpus and near-match gates.
Reproduction details and hashes are in
`docs/schala_gameplay_sprite_foundation_v0.md`; the bounded canonical-PC
comparison is in `docs/schala_gameplay_originality_audit_v0.md`.

#### Glass Focus / Focus Pulse source slice

`verified-static` for source validation and deterministic serialization;
`proposal` for the visual/audio design; no runtime binding

The first dedicated basic-Attack slice is deliberately limited to Glass
Focus (`$E8`, visual 0) and action `$90`:

- source:
  `assets/source/schala/v0/focus/glass_focus_pulse_v0.json`
  (`32967` bytes, SHA-256
  `fe7ccfc67c523e2a7edfeba9b14b855b3d14c92d1ef2d46076a6c57ce1765aa0`);
- source manifest:
  `assets/source/schala/v0/focus/glass_focus_pulse_manifest_v0.json`
  (`6284` bytes, SHA-256
  `e14efe2dac41758fca34aeb64019caa7d104be8ac5f6f939c23374b65d597a87`);
- read-only validator:
  `tools/validate_schala_glass_focus_pulse_v0.py`
  (`59563` bytes, SHA-256
  `061a7169f1bbd6c57409fba52b36a4cbf76ff3d9fcd32665b946558feafa9b4e`);
- focused test:
  `tests/test_schala_glass_focus_pulse_v0.py`
  (`21540` bytes, SHA-256
  `7bf6de33de772be318c94098d839751c8d9f266d821ea1ab94cda00cbbd2b208`);
- canonical-ROM metadata auditor:
  `tools/audit_schala_glass_focus_originality.py`
  (`8258` bytes, SHA-256
  `addbb63ce0d5c92972fc467bc7d0e92f6cab3015f792a9c8da90101c492d8ce7`);
- pinned metadata report:
  `references/schala_glass_focus_originality_v0.json`
  (`2649` bytes, SHA-256
  `a8727872ecc8831818b71e0fab149580e035fd695e23baa3b4721f5db556d282`);
- originality-auditor test:
  `tests/test_schala_glass_focus_originality.py`
  (`6815` bytes, SHA-256
  `2316430ffc9cdf903f66df96e2ad1c92710e0cd87abd95548b9718d7c92dc93e`).

The source contains six ordered 40x40 poses—draw, open, pulse,
follow-through, recoil, and recover—and six separate 16x16 shapes—closed
crescent, open ring, quarter-turn ring, edge-on ring, collapse point, and
impact arc. It references the existing original gameplay palette instead of
embedding another copy. It also defines two integer-only parametric source
recipes, `focus_swing_v0` and `focus_hit_v0`; no waveform, BRR, SPC data,
native SFX ID, or rendered audio is committed.

The provenance distinguishes external copying from deliberate reuse of
Project Epoch's own original Schala body pixels. External/ROM/NPC/vanilla-PC
pixels and sampled or extracted game audio remain forbidden. Every native
action/visual/palette/SFX ID and graphics/animation/effect/palette/audio
pointer is null. Tide Lens, Night Prism, and Star of Zeal remain
identity-only.

The validator cross-checks PC `$07`, action `$90`, item `$E8`, visual 0, the
item/Tech authoring sources, the palette dependency, and the still-unbound
architecture document. It exact-key validates all records and provenance
narratives, rejects booleans as integers, rejects runtime or NPC-originality
overclaims, round-trips the six poses and six inserts through SNES 4bpp, and
canonicalizes both audio recipes without rendering them. Twenty-eight source
and manifest tests plus ten Focus-originality wrapper tests pass:

```powershell
$epochPython = 'python'

& $epochPython tools\validate_schala_glass_focus_pulse_v0.py
& $epochPython tests\test_schala_glass_focus_pulse_v0.py -v
& $epochPython tools\audit_schala_glass_focus_originality.py `
    --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
& $epochPython tests\test_schala_glass_focus_originality.py -v
```

A separate read-only metadata comparison packed the 12 visual sources in
memory and inventoried 174 candidate tile occurrences and 7,264 canonical
playable-PC tiles. The declared policy excludes tiles with at most two visible
pixels: 80 candidate and 59 reference occurrences are reported but not
automatically compared. The remaining 94 candidate and 7,205 reference tiles
are checked as exact and palette-renaming-invariant H/V/HV forms. After
changing only two sparse impact-arc cells without displaying or exporting
reference pixels, both match counts are zero. The dedicated wrapper pins the
source and underlying comparison implementation, accepts only the private
canonical ROM argument, emits canonical UTF-8/LF report bytes only to stdout,
and reproduces the source-controlled metadata report byte for byte without
reading that report. The full validator separately verifies the pinned report
and fails closed if it is stale. This bounded check does not cover compressed
NPC/enemy art and makes no NPC-originality claim. It emits no
source-controlled binary.

#### Current 16-frame body-packet fit

`verified-static` for dependency identity, native-shaped packet fit, bounds,
serialization, and exact reconstruction; `proposal` for source order and
visual design; no new runtime evidence

The unchanged ten gameplay-foundation frames and unchanged six Glass Focus
basic-Attack body poses now pass one additive, metadata-only packet audit:

- 16 provisional body records, each exactly `$28` bytes;
- 91 deduplicated tiles including reserved transparent tile 0;
- 90 nontransparent unique tiles and maximum tile index `$005A`;
- `$0B60` bytes of in-memory raw graphics, SHA-256
  `361ea69917d97a8c68e4450df0b944e43c9dad73b3aca2ecf52304ed70484a66`;
- `$0280` bytes of in-memory assembly, SHA-256
  `b14735361a2546337d32ad3f8318a4138980c16515a7cbcc48a1b92de89d69d1`;
- the existing `$20`-byte palette, SHA-256
  `782a063ffc99087cca1b64876cd024a5c5c7e6c6193c8f9ff224e9ed88ead5ea`;
- 15 four-object frames and the known three-object middle down-walk frame;
- exact source-canvas reconstruction for all 16 frames.

The complete ten-frame graphics and assembly streams remain exact prefixes,
so the six attack poses add only ten unique tiles and six records. The six
standalone Focus inserts and two integer-only audio recipes remain validated
source vocabulary but are not body-packet data. The Glass manifest itself
still truthfully says `assembly_packability_claimed: false`; this independent
audit adds an external bounded claim without rewriting that earlier contract.

The artifacts are:

- `tools/audit_schala_current_body_packet.py`: 29,448 bytes, SHA-256
  `00db7f71e9c85b5a3efc4b3bccdbc7d7d7407b731f9780ab02a13cfd9fa90789`;
- `tests/test_schala_current_body_packet.py`: 15,462 bytes, SHA-256
  `608bff2ee7d7dfb9f5cc2009662afe3f04673ca8377496691ca18e118ddd0fb1`;
- `references/schala_current_body_packet_v0.json`: 11,953 bytes, SHA-256
  `c5a04304739e5fac3125cb840e9745bafae0f45b0b2869b4743b5d25c1c1313b`;
- `docs/schala_current_body_packet_v0.md`: reproduction, stop gates, and the
  complete evidence boundary.

The tool hash-gates all four existing source/manifest inputs and the three
behavior-bearing helpers before use. It accepts no ROM or output path, writes
no files, and serializes no rows, pixels, tiles, assembly bytes, palette bytes,
images, or decoded game data. Eighteen focused tests cover drift, bindings,
frame identity/order, palette identity, four-object packing, overflows,
unchanged prefixes, exact reconstruction, metadata-only output, no-write
behavior, and byte-identical report reproduction.

The ordinals are provisional authoring order, not native animation IDs. This
does not define the four-facing animation blob, `$E4:2800` auxiliary family,
battle staging, DMA, expanded-bank reads, action `$90`, item `$E8`, sound,
allocation, hook, PC `$07`, save/load, New Game+, or Epoch behavior. It also
does not close the full 241-packet, near-match, silhouette, or finished-sheet
originality gates. The next safe source-only engine step is to map semantic
animation entrypoints and the auxiliary-animation contract before authoring
the remaining field and battle inventory. The following subsection records
the completed result of that follow-on gate and its still-open consumer
censuses.

#### Animation semantic contract and field timing probe

`verified-static` for canonical stream geometry, roots, consumers, and
selector control flow; `exploratory-runtime` for one exact native-Mesen field
checkpoint; no Schala or PC `$07` binding

The read-only semantic-contract audit closes the first engine gate left by the
16-frame packet without promoting its source ordinals. It proves:

- engine primary-facing numeric order is `$00-$03`; the direction names are
  documented as up, down, left, right, while the existing cardinal source
  roles remain down, up, left, right;
- animation entrypoint `N` begins at byte offset `N * 4`, but sequences are
  variable-length and may overlap or share suffixes beyond that stride;
- `$E4:FFE4` resolves the primary boundary table at `$E4:2600`, while
  `$E4:FFE6` resolves the distinct auxiliary timing/control table at
  `$E4:2800`;
- each playable PC has one auxiliary contract equal to one primary-facing
  span;
- Magus's bounded auxiliary contract is `$E4:AEC0-$E4:AFB4`;
  `$E4:AFB4-$E4:B5FF` remains unclassified and is not free space, and occupied
  successor entries begin at `$E4:B600` and `$E4:B614`;
- fixed-bank `$E4` setup/reader sites are present in the field, menu, and
  battle paths and therefore require an explicit relocated-bank adapter;
- menu roles are `$00` reset, `$01` hovered, and `$0B` picked;
- the minimum automatic battle anchors are
  `$00/$03/$08/$0A/$0C/$12/$1A/$23`; and
- `$CC:F77F-$CC:F7BF` is sixteen four-byte state-selection records followed by
  its `$FF` table terminator. Record 0's `$A119` forced match, the
  `$A09B`-dependent `$00/$03` default, the later critical `$12` override, and
  the nonliteral selector-`$FF` branches are all pinned. `$A0A7` itself remains
  unresolved.

The canonical metadata report is
`references/schala_animation_semantic_contract_v0.json`, 68,305 bytes,
SHA-256
`50374adab6ad07522184b8b0ffc26300f3dd15abe7e817bd48263b20c3a2b015`.
It is reproduced only to stdout by
`tools/audit_schala_animation_semantic_contract_v0.py`; 21 focused tests pin
all source hashes, instruction-aligned code/table preimages, decoded records,
overlap rules, closed metadata shape, explicit missing-ROM failure, CLI
behavior, absence of explicit artifact-write calls, and byte equality with the
checked-in report.
No primary stream, timing stream, pixel, save/state/trace content, ROM path,
patch, payload, allocation, or hook is serialized.

A hardened tracked native-Mesen launcher and collector then tested the field
reader relationship at the exact `event11c-checkpoint-v5-spekkio-talkable`
checkpoint. Two final idle runs and two final Right-input runs used unique
disposable same-stem ROM/SRAM/state/config staging trees and preserved every
pinned source. The
Right route was collision-blocked, but it still switched the Magus leader from
selector `$00` to selector `$01`, fixing right-facing as engine facing 3 at
that checkpoint. One complete reset-to-reset loop read primary frame bytes
`$10-$15` from `$E4:4DE0-$E4:4DE5`, each paired with delay `$07` from
`$E4:AEC4-$E4:AEC9`, then observed timing zero at `$E4:AECA` and reloaded the
entrypoint. Canonical `$E4:4DE6=$FF` was statically cross-checked but was not
fetched by the primary reader because the timing zero reset the cursor first.

The frozen tracked collector is 19,345 bytes, SHA-256 `9abca7ba...`; the
launcher is 55,200 bytes, SHA-256 `d5cde9c3...`; and its synthetic test module
is 30,429 bytes, SHA-256 `3ed78c6d...`. The focused suite discovers 35 tests:
33 pass, while two real-symlink cases skip only because the Windows token
lacks symlink privilege. Deterministic mocked dangling-link/reparse tests
pass. The final idle
normalized trace and semantic-manifest identities are `ff984961...` and
`4cde0ddd...`; the final Right identities are `d671b787...` and `c24cc516...`.
Both repetitions agree under the documented normalization. The earlier private
aggregate remains unchanged at 11,615 bytes, SHA-256 `829a0fe4...`, as
historical exploratory provenance. Endpoint PNGs remain supporting
presentation only. Raw traces, manifests, screenshots, ROMs, SRAM, savestates,
emulator binaries, and extracted streams must never be published. Exact
receipts and reproduction boundaries are in
`docs/schala_field_animation_runtime_probe_v0.md`.

This runtime result proves only the paired field-reader behavior at one
vanilla seven-PC checkpoint. It does not prove free movement, another facing,
another PC, a location-event operand, battle action packages, a relocated
bank, Schala rendering, logical PC `$07`, save/load, or production timing.

#### Location-event animation operand census

`verified-static` for the encoded corpus and direct-function-entry topology;
runtime identity and loader lifetime unresolved

The fail-closed, read-only location-event census now inventories every
structurally valid encoded `$AA/$AB/$AC/$AE/$B3/$B4/$B7` site in the
hash-gated canonical ROM. It finds 10,637 unique physical animation/static
sites in 391 packets and keeps `$AC` static assembly frames separate from
animation entrypoints. `$AE/$B3/$B4` are implicit selectors; `$AB/$B7` use
the secondary selector path; and `$B7`'s second operand is repetition/progress
control rather than an entrypoint.

The corpus contains 116,064 function-pointer occurrences. Of those, 1,864
point backward into another physical source owner, 321 point forward, and 84
point to the exact packet-end sentinel. Physical object adjacency is therefore
not a safe identity classifier. The auditor computes an incoming
direct-function-entry closure for each animation source owner and unions each
distinct directly targeted source owner's PC, NPC/enemy, graphics, and lifecycle
markers. This syntax-only overapproximation is complete for the sixteen direct
entries per logical owner, not for calls, jumps, fallthrough, startup replay,
loader lifetime, party state, or runtime reachability.

The conservative closure classifies 927 of 2,744 animation source owners with
PC markers and no NPC/enemy marker, 23 with both PC and NPC/enemy markers, and
1,794 with no PC marker. The 950 possible-PC-marker owners contain 5,624
encoded sites; none is promoted to a definite runtime PC site. Generic
`$80/$81` operands are canonically limited to `$00-$06`, while synthetic
`$07+` values are kept outside the vanilla-PC result and never named Epoch or
Schala. Opcode `$87` remains an orthogonal graphics-assignment marker.

The checked-in metadata report is 31,731 bytes, SHA-256
`d170c0d5771b84e0fbcb394dcd4151ccef3e8c96f4bd6a80a6cc9c498f78f2c4`.
Its closed schema and semantic identities, exact machine-code preimages,
complete pointer topology, placeholder allowlist, parser dependency, stdout-
only behavior, absence of write APIs, and ROM preservation are pinned by 19
focused tests. No raw ROM or decoded event data is serialized. Exact counts,
reproduction, proof boundaries, and the incoming-versus-outgoing
counterexample are in
`docs/location_event_animation_operand_census_v0.md`.

This closes the encoded location-event operand-inventory gate only. Before
using the result as runtime PC attribution, implement or explicitly defer a
closed inter-object control-flow and loader-lifetime model. The separate next
planning audit is the data-driven battle action-package census.

#### Compressed sprite corpus and bounded Schala NPC comparison

`verified-static` for the canonical byte chain and tile comparison;
`documented` for the human-readable Schala identity; no runtime binding

The fail-closed read-only corpus audit now parses the complete 256-entry
graphics-pointer table, all 256 NPC descriptors, and all 256 enemy
descriptors. It independently decodes every structurally valid compressed
packet in graphics-source range `$07-$F7`:

- conservative catalog: 241 packets, 540,847 compressed bytes, 699,872
  decompressed bytes, and 21,871 aligned 4bpp tiles;
- descriptor-selected subset: 237 packets, 540,276 compressed bytes, 699,200
  decompressed bytes, and 21,850 aligned tiles;
- catalog-only selectors: `$47`, `$4A`, `$CC`, and `$E5`, which are not
  selected by the audited NPC and normal-enemy descriptor tables but are not
  declared unused;
- enemy IDs `$F8-$FF`: a separately proved direct/raw branch, not the null
  pointer slots `$F8-$FF`.

The decoder follows the canonical C3 control-bit, 11/12-bit back-reference,
addendum, source-bank, and tile-alignment rules. An independent
assembly-faithful implementation reproduced the exact catalog and selected
aggregate hashes. Review also exposed and closed a malformed partial-addendum
edge: a zero control byte is now accepted only for an eight-control group,
matching the engine's eight-literal fast path. Twenty-one focused tests cover
both width forms, addenda, malformed sources, the table partitions,
byte-identical report reproduction, and no output-file path.

The corpus artifacts are:

- `tools/audit_ct_compressed_sprite_corpus.py`: 34,780 bytes, SHA-256
  `5dcba015098dcf5a9ec754a5537f35ab67144f0ac09d166e7644741a74ae990d`;
- `tests/test_ct_compressed_sprite_corpus.py`: 15,431 bytes, SHA-256
  `3c861355f5e35552244b258c5a2ba42c0881871615f8c8a1b814f70468f013a8`;
- `references/ct_compressed_sprite_corpus_v0.json`: 147,507 bytes, SHA-256
  `ae7fb21d2f13cc1d58fa64fbe76a7086a08c0a10c28c7bd88aae857bd3e35f0e`;
- `docs/ct_compressed_sprite_corpus_audit.md`: 8,193 bytes, SHA-256
  `fd75e9c87c4856b7dee08ce28de75ccec10f313a99b312d64031059d8a492854`.

A second audit pins the exact static route
`location $14E -> event $0CE -> object $0F -> NPC $09 -> gfx selector $26`.
The canonical event packet is 942 compressed bytes and 1,435 decompressed
bytes; object `$0F` begins at event-data offset `$0569` with command
`$82 $09`. NPC `$09` has descriptor
`[$26,$1B,$80,$3B,$00]`; NPC `$CD` is its sole same-geometry descriptor
variant and differs only in palette (`$9F`). Selector `$26` uniquely points to
a 2,447-byte packet that decodes to 2,528 bytes, or 79 tiles. The
human-readable identity comes from the pinned
[Pseudoarc/jetsoftime source at commit `3af9a5a`](https://github.com/Pseudoarc/jetsoftime/blob/3af9a5a8fa5db7cd47740c791fa6580f7a4efa44/sourcefiles/bossrandoevent.py#L188-L201);
that label remains `documented`, while the ROM chain is `verified-static`.

With the same at-most-two-visible-pixels exclusion used by the existing
playable-PC audits, the selector-`$26` packet contributes 79 tile occurrences,
one excluded as trivial and 78 compared. The current gameplay foundation
contributes 159 occurrences, 59 excluded and 100 compared; Glass Focus
contributes 174, 80 excluded and 94 compared. Both candidate sets have zero
exact-index and zero palette-renaming-invariant H/V/HV matches against those
78 reference tiles.

The Schala-specific artifacts are:

- `tools/audit_schala_npc_originality.py`: 38,224 bytes, SHA-256
  `b8fc56d4e5b782576718290a26caddd86741a3da79390a2717089f9716adb9fa`;
- `tests/test_schala_npc_originality_audit.py`: 19,794 bytes, SHA-256
  `af6b7b5e7880c70588aceb7f5b816d3ae4f47e3e5832732721c200f4986115c7`;
- `references/schala_npc_originality_audit_v0.json`: 10,708 bytes, SHA-256
  `752f29a5f058c5323d689c64a08073ac6ba97f13b8370211d87a6699f955c647`;
- `docs/schala_npc_originality_audit_v0.md`: 8,948 bytes, SHA-256
  `5b674583f377a9dbdbb3a97ccd40082ed453e14a1c553bbb9dfa82a4edbb495d`.

The Schala audit pre-use hash-gates all five behavior-bearing helper modules,
pins both candidate sources and the Glass manifest, rejects any count or
match drift, and reproduces its metadata-only report byte for byte without
reading it. Twenty-four focused tests cover the dependency gates, canonical
chain mutations, descriptor family, candidate policy, no-write behavior, and
report boundaries:

```powershell
$epochPython = 'python'

& $epochPython tools\audit_ct_compressed_sprite_corpus.py `
    --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
& $epochPython tests\test_ct_compressed_sprite_corpus.py -v
& $epochPython tools\audit_schala_npc_originality.py `
    --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
& $epochPython tests\test_schala_npc_originality_audit.py -v
```

Neither report serializes decoded tiles, pixels, palettes, images, or packet
bytes. The zero-match result applies only to this pinned Schala-family packet
and the exact current Project Epoch sources. It is not a global NPC/enemy,
near-match, silhouette, animation, assembly-layout, palette-art, or runtime
semantic-identity result, and it approves no hook, allocation, ROM write, or
PC `$07` binding.

The missing vanilla PC packet envelope is now measured in
`docs/pc_sprite_packet_envelope_audit.md`. All seven PCs use `$28`-byte
size-class-0 records with sixteen tile words and four coordinate pairs; the
field path builds four objects, decodes `$200` bytes, and queues two
`$100`-byte transfers. `$FF` is the animation frame sentinel, so `$FE` is the
highest unchanged-format frame ID and `$27D8` is the 255-record assembly
ceiling. Ayla reaches that ceiling. Six derived packet ends match the next
canonical pointer; Robo's derived `$DC:DF70` end remains a minimum rather than
a proved physical boundary. No tail bytes are declared free.

### 4.6 Static PC `$07` surface audits

`verified-static`

The pinned reconstruction and canonical ROM have now been used to map the
principal eighth-ID collisions before installing any production hook:

- `docs/pc7_graphics_menu_hook_audit.md` covers field, battle, overworld,
  menu-sprite, portrait, save-preview, icon, and fixed-buffer paths.
- `docs/pc7_character_tech_equipment_audit.md` covers live records, growth,
  equipment, normal attacks, tech learning, multi-tech groups, and the
  action-command namespace.
- `docs/sram_gap_sidecar_audit.md` covers the vanilla serializer and the
  candidate three-slot Project Epoch sidecar.
- `docs/wram_compatibility_block_audit.md` covers the preferred `$2CA0`
  relocation destination, descriptor translation, and runtime canaries.
- `docs/schala_command_namespace_architecture.md` covers the selected raw
  `$80-$90` command overlay and every known high-ID edge.
- `docs/schala_item_namespace_architecture.md` covers candidate item IDs
  `$E8-$EE`, their expanded descriptor, and menu/shop/battle adapters.
- `docs/location_event_item_reference_audit.md` proves those candidate IDs
  are unclaimed by every canonical location-event script path.
- `docs/schala_recruitment_content_foundation_v0.md` records the original
  branch/dialogue graph, null engine bindings, and executable authoring
  scenarios for recruitment.
- `docs/schala_recruitment_engine_binding_audit.md` maps all 29 dependencies
  to proved primitives or named adapters while retaining null bindings.
- `docs/schala_portrait_originality_audit_v0.md` records the zero-match
  bounded comparison against all uncompressed vanilla menu portraits.
- `docs/schala_gameplay_sprite_foundation_v0.md` records the first original
  target-grid field/battle frames, deterministic packing, and explicit
  partial-status boundary.
- `docs/ct_compressed_sprite_corpus_audit.md` records the conservative
  241-packet compressed catalog and its 237-packet descriptor-selected subset
  without declaring catalog-only selectors free.
- `docs/schala_npc_originality_audit_v0.md` records the bounded zero-match
  comparison against the one statically reached, documented Schala-family
  packet.
- `docs/pc_sprite_packet_envelope_audit.md` records all seven exact raw PC
  graphics windows, animation boundary sizes, size-class-0 assembly format,
  per-character packet hashes, tile-index envelope, and field transfer limit.
- `docs/schala_sprite_packet_foundation_v0.md` records the deterministic
  ten-frame native-shaped graphics/assembly packet and exact reconstruction.
- `docs/schala_animation_semantic_contract_v0.md` records the entrypoint
  stride, auxiliary timing family, fixed-bank setup/reader sites,
  field/menu/battle minimum, and decoded battle-state selector table without
  binding Schala.
- `docs/schala_supported_slot_sprite_smoke_v0.md` records the accepted
  pre-Continue full-load field replay, clean control, and supported-slot
  Schala render without promoting it to PC `$07`.
- `docs/field_sprite_palette_loader_audit.md` maps all five field palette
  reload paths and ten shadow-copy sites, and defines the non-colliding
  `$FFFF` source-key adapter for Schala's fifteen visible colors.
- `docs/pc_init_record_schema_audit.md` assigns every byte in the canonical
  `$50`-byte record, maps new-game and attract/demo initialization, and pins
  the seven-row HP/MP/TP bounds plus the eight-row stat-table hazard.
- `docs/schala_rom_expansion_architecture.md` covers the inert 8 MiB ExHiROM
  scaffold, reserved mirrors, allocation contract, and BPS build plan.

The audits prove that PC `$07` cannot be enabled by extending loop bounds.
Depending on context it currently aliases tech state, NPC graphics, the Epoch
portrait, overworld palette storage, or live menu scratch records.

## 5. Namespace architecture

These identifiers must remain separate.

### Logical playable identity

- `$00-$06`: vanilla playable PCs.
- `$07`: Project Epoch Schala.
- `$80`: empty party-slot sentinel in tooling.

### Save/editor records

- `$00-$06`: vanilla `$50`-byte PC records at slot-relative
  `$0200-$042F`.
- Apparent record `$07` at `$0430`: not a PC record; preserve.
- `$0480` is not an approved backing record. Zero-filled bytes in one save are
  not provenance, and the vanilla slot checksum covers the whole `$A00`.
- Preferred candidate: three versioned `$A0` sidecars in the bounded SRAM
  gap `$30:7E00-$30:7FDF`, pending save/load/NG+/erase proof. Deliberately
  expanded SRAM remains the fallback if that gap fails any ownership gate.

### Runtime records

- Supported live records structurally begin at `$7E2600` with stride `$50`.
- Lucca: `$7E26A0`.
- Magus: `$7E27E0`.
- Natural logical ID `$07`: `$7E2830-$7E287F`, currently occupied by vanilla
  tech-learning/group state and other compatibility bytes.
- Preferred candidate: relocate that complete `$50`-byte compatibility block
  to candidate `$7E2CA0-$7E2CEF`, then use the natural ID-derived range as
  Schala's live record. The destination has bounded guards and survives
  loaded field, full-menu entry/idle, equipment-page entry/render/idle, one
  ordinary seven-PC party swap, the complete North Cape Magus
  fight/recruitment decision path, reserve registration, newly recruited
  Magus party insertion, and native battle entry canaries, but still needs the
  remaining transition matrix.
  Save/load must serialize the relocated vanilla state back to its original
  slot offsets `$0430-$047F`.
- Fallback: allocate a separate Schala record and adapt every record consumer.
  This has a larger and more fragile hook surface.

### Graphics-source indices

- `$00-$06`: known playable sources.
- Low indices above `$06`: occupied engine actors/vehicles unless traced.
- Schala needs a logical-ID adapter that resolves to relocated graphics data;
  she must not claim an existing low graphics index.

### Required adapter boundary

The intended architecture has independent resolvers:

```text
GetPlayableRecordPtr(logical_id)
GetGraphicsSource(logical_id, context)
GetPortraitSource(logical_id, context)
GetSingleTechBlock(logical_id)
GetEquipmentPermission(logical_id)
GetTechProgressPtr(logical_id)
GetActionData(action_id, data_kind)
```

For IDs `$00-$06`, each resolver should preserve vanilla behavior. For `$07`,
it should return Project Epoch storage. Do not build one global `$07->$06`
identity substitution.

## 6. Known seven-PC data surface

This table records the evidence currently established from the pinned ROM,
the deterministic emulator runs, and the byte-matched static reconstruction.
It is not proof that every engine consumer has been found.

| Subsystem | Known source or collision | Current evidence | Gate for PC `$07` |
| --- | --- | --- | --- |
| Active party | SRAM `$0580-$0582`; WRAM `$7E2980-$7E2982`; field setup at `$CC:E97E` reads three IDs | selected bytes `verified-runtime`; instructions `verified-static` | Trace save-select, roster, battle, event, and bounds-sensitive consumers. |
| Joined state | `$7E29AF`; `CharPartyFlagTable` is `80 40 20 10 08 04 02 01 00` | `verified-static` | Preserve bits 7-1 and prove bit 0 through recruitment, roster, save/load, and NG+. |
| Save records | `$0200-$042F`, seven × `$50`; `$0430` is not a record | `verified-static` | Use versioned sidecar storage; do not append into the vanilla payload by inference. |
| Save serialization | Three slots at `$30:6000/$30:6A00/$30:7400`, stride `$A00`; eight source-region descriptors; checksum covers the whole slot; bounded gap `$30:7E00-$30:7FDF` precedes metadata | boundaries `verified-static`; gap survives boot/load `verified-runtime`; no distinct copy path found | Hook save/full-load/NG+/erase; use expanded SRAM only if the bounded sidecar candidate fails. |
| Runtime records | `$7E2600 + id*$50` for supported records; `$07` lands on the vanilla compatibility block at `$7E2830-$287F` | formula, complete `$50` schema, and collision `verified-static`; Lucca/Magus locations `verified-runtime` | Prefer relocating the complete compatibility block and using the natural record; resolve `+$01` low flags, `+$02` seed flags, and all initialization routes before emitting Schala bytes. |
| New-game seed | `$C2:956E` copies `$280` bytes from `$CC:0000` to `$7E2600`; seven `$50` records occupy the first `$230` | `verified-static` | Replace the monolithic assumption with explicit vanilla plus Schala initialization. |
| Attract/demo seed | `$FD:B2DE` loops over eight `$50` destinations, but each of the three HP/MP source blocks has only seven `$08`-byte rows | `verified-static` | Add a bounded PC `$07` branch; the eighth vanilla iteration reads beyond the selected block. |
| Battle record commit | `$C1:B442` writes each slot's first `$50` bytes back to `$2600 + id*$50`; battle work records are slot-based at `$7E5E2D + slot*$80` | `verified-static` | Use the natural formula only after the compatibility block has moved; otherwise add an ID-aware commit adapter. |
| Tech progress | Save `$0430-$0436`; WRAM `$7E2830-$7E2836` | `verified-static` | Relocate/expand seven-byte array and trace save/load/learning. |
| Learned masks | Save `$0437-$043D`; WRAM `$7E2837-$7E283D`; combo state follows at `$7E283E` | `verified-static` | Relocate/expand; an in-place eighth byte would collide with combo state. |
| Post-battle combo learning | `$C1:F29C` builds `$283E +` a five-byte requirement-record index; `$C1:F5C1/$F5C7` update the selected byte | canonical table/code hashes and exact `$283E-$2856` maximum `verified-static`; no vanilla participant mask uses bit `$01` | Relocate this 25-byte learned-group span and create an expanded Schala namespace; a naive 26th row would collide with rock flag `$2857`, and other hidden/computed consumers still require review. |
| Location-event tech grant | Event `$11C`, object `$09`, location `$1D1` has 12 absolute commands touching counts `$2830/$31/$32/$34` and masks `$2837/$38/$39/$3B` | all 513 pointers and 1,511 absolute commands scanned; exact 12-site/24-byte volatile translation and both prepared party profiles `verified-runtime` | Recompress and install the pinned `$2CA0-$2CAB` operands in a named allocation, then repeat the natural-PC07 and lifecycle guards; the current proof patches only the already-decompressed `$7F2000` buffer. |
| Names | `$7E2C23` holds eight six-byte fields, but `PcNameAddrTable` entry 7 is `$0000`; `$7E2C4D` is the separately handled Epoch name | `verified-static` | Add Schala-owned name storage and a resolver; do not repurpose Epoch. |
| Sprite sources | Core `$E4:2000/$2300/$2600/$2800/$2A00` tables and five-byte descriptors at `$E4:F000`; ID7 reaches occupied NPC data or an end sentinel. All vanilla PCs use `$28`-byte, four-object, sixteen-tile-word size-class-0 records; the private vanilla Schala provider has 23 such records and 79 fully referenced tiles. | packet metadata and vanilla provider `verified-static`; supported original partial packet `verified-runtime` | First replay the vanilla provider in a supported slot with explicit entrypoint fallback. Then add context-specific PC `$07` resolvers while leaving entries 7/8, NPC `$09`, and `$E4:F023` unchanged; final distributable art remains a separate original-art gate. |
| Field sprite palettes | Five logical reload paths contain ten `$18`-byte bank-`$E4` moves into colors 1-12 of both CGRAM shadows; the private vanilla provider uses exactly twelve character-specific colors, while the deferred original source uses fifteen | loader matrix and provider shape `verified-static`; twelve-color supported-slot render `verified-runtime` | Use the native twelve-color path for the Phase A diagnostic. Retain the `$FFFF` full-palette resolver as a Phase B gate, preserving color 0 and vanilla `$18` behavior at all ten sites. |
| Overworld graphics | `$C2:2BBC/$2BCF/$28ED` derive tile and palette addresses from ID; ID7 lands in palette/staging data | `verified-static` | Stage a dedicated Schala overworld page and palette rows. |
| Menu walking sprite | Seven `$40`-byte records at `$7E1800-$19BF`; ID7 reaches active scratch at `$19C0` | `verified-static` | Virtualize Schala into a deliberate display slot; do not increase the record bound. |
| Portraits | Full menu path has seven `$480` 36-tile faces plus seven palettes; ID7 aliases Crono/Epoch depending on context. The supported clone's `$200` preview path is separate. | static layout `verified-static`; supported small preview `verified-runtime` | Preserve Epoch naming context and dynamically resolve both an original full portrait and a distinct save preview. |
| Tech bases/ranges | `CharTechBaseTable` at `$CC:276A` has seven two-byte entries; `$C2:BD40` supplies 37 boundaries for 36 learned groups | `verified-static` | Relocate/expand owner and group metadata before adding Schala techs. |
| Action namespace | Named player commands use `$01-$74`, basic attacks `$75-$7B`; `$7C-$7F` stay reserved as player-command IDs, although the separate PC type-2 animation-config namespace has fixed internal producers for rows `$7C/$7D/$7F`; raw `$80-$90` survives the battle descriptor/queue unchanged, while `$F0-$FF` is a marker family | transport and internal-config distinction `verified-static`; layout `proposal` | Use the pinned `$80-$90` overlay, patch every signed/direct-index edge, leave `$7C-$7F` untouched as player commands, and preserve the same-valued vanilla animation-config rows independently. |
| Player Tech animation packages | half-open `$C1:4612-$C1:4682` resolves config byte 0 through `$CD:5EF0` and fixed bank `$CE`; command `$1E` independently reads and installs a fixed-`$CE` subscript; config bytes `+3/+4/+5` retain separate fixed `$D1/$CD/$CE` auxiliary readers | primary reader, seven exact preimages, 128 canonical `(bank,root)` identities, nested-script and auxiliary boundaries `verified-static`; high adapter and complete vanilla-shaped host state model `proposal` | Preserve the canonical `$00-$7F` path. Candidate Epoch package selectors `$80-$8F` remain explicitly unbound and do not inherit same-numbered command IDs. Complete a lossless command-stream/`$1E` decision and one symbolic high-package source contract before authoring an original helper. See `docs/schala_player_tech_package_bank_adapter_v0.md`. |
| Tech names | `$CC:15CF`, 116 records of 11 bytes, IDs `$01-$74` | `verified-static` | Resolve Project Epoch command data separately and trace all callers. |
| Tech targets | `$CC:1ACB`, two bytes for IDs `$00-$74`; following data begins at `$1BB5` | `verified-static` | Resolve Project Epoch command data separately and trace all callers. |
| Tech properties | `$CC:214B`, 72 records of 12 bytes, IDs `$00-$47`; participant lists follow at `$249F` | `verified-static` | Resolve Project Epoch command data separately and trace all callers. |
| Tech MP costs | `$CC:253B`, one byte for IDs `$01-$47`; basic-action map follows at `$2583` | `verified-static` | Resolve Project Epoch command data separately and trace all callers. |
| Tech effects | Base `0x0D45AD`, stride 7, seven × eight | `documented` | Relocate/expand table and trace callers. |
| Basic Attack action IDs | `$CC:2583-$CC:2589`; direct logical PC `$07` falls into HP-growth data at `$CC:258A` | `verified-static` | Preserve `$00-$06` and resolve `$07` from named expanded data at the `$C1:BFFF` consumer. |
| Attack approach policy | `$CC:F63C-$CC:F643`; direct logical PC `$07` reaches the occupied `$FF` byte and takes the nonzero pathfind branch | `verified-static`; Crono consumer route partly `verified-runtime` | Preserve all eight occupied bytes and add an independent `$07` policy adapter near `$C1:4A44`; do not call `$CC:F643` free. |
| Attack animation selectors | Seven-entry families at `$CD:4000-$4006`, `$CD:4007-$400D`, and `$CD:400E-$4014`; direct `$07` indexes alias the next family/record. `$CD:400E[0]` is Crono's runtime-confirmed critical selector. | boundary chain `verified-static`; Crono critical path `verified-runtime` | Expand/adapt all three consumers near `$C1:438B/$C1:43C4/$C1:43F8`; never append in place or repurpose file byte `$0D400E`. See `docs/pc7_attack_adapter_audit.md`. |
| Focus Pulse action/weapon presentation | Raw action `$90` indexes `$CC:221B` inside Tech properties; Focus weapons `$E8-$EB` index four 15-byte spans inside enemy Attack-animation records; a three-selector append reaches `TechAnimPtrTable[0]`. The same IDs reach existing hit-SFX rows through the palette map and reachable enemy Attack-animation packages through both SFX maps; those owners are separate from the PC normal-Attack resolver. The 64 six-byte palette rows and all menu/battle copies are fixed to bank `$D1`. One `$10`-byte PC Attack schema and four `$18`-byte Focus visual schemas are frozen with every runtime value and pointer explicitly unbound. Glass Focus now has a six-pose/six-insert/two-audio-recipe source slice, still with null native bindings; the other three Focus weapons remain identity-only. | boundary geometry `verified-static`; source schemas and Glass presentation `proposal` | Author Tide Lens, Night Prism, and Star of Zeal slices, then define a separately versioned composite target with distinct palette pointer, swing cue, hit cue, and graphics fanout. Select named expanded allocations and approved hook preimages only afterward. See `docs/schala_focus_pulse_adapter_architecture.md`. |
| TP thresholds | `$CC:26FA`, seven rows × `$10` bytes, eight u16 thresholds per PC; direct row 7 enters the following table | `verified-static` | Relocate/expand and trace TP award/next-tech logic. |
| Menu element | Seven-byte map at `$C2:A2C6`; ID7 reads following code | `verified-static` | Hook `$C2:A279/$A27C` and return Schala's deliberate element/type icon. |
| Equipment | `$C2:93A8` ANDs an item mask with `CharPartyFlagTable[id]`; ID `$07` maps to bit 0, while general mask `$FE` excludes it | `verified-static` | Use `$01` for Schala-only items, deliberately extend selected general masks, and runtime-test equip/stat/weapon paths. |
| Multi-techs | Dual builder `$C1:CA1A` assumes IDs `$39-$65` and three actions per group; triple builder `$C1:CCCB` assumes `$66-$74` and one per group | `verified-static` | Replace fixed command ranges/group widths with explicit Project Epoch metadata; Schala's six duals require six participant groups. |
| Recruitment | Party add/remove uses the flag table, giving `$07` a structural joined bit; vanilla full-party Magus recruitment now proves reserve registration before naming and subsequent active insertion | vanilla Magus flow `verified-runtime`; PC `$07` adapters uninstalled | Implement and trace Schala naming, locks, eight-PC roster visibility, save/load, and all original event branches. |
| Save-select/roster | Recovered raw `$07` shows Epoch/garbage/duplicate behavior | `documented`; not yet reproduced in this workspace | Trace record, name, portrait, loop count, availability, and sprite mapping separately. |
| Battle | Initialization and record commit partly mapped; the native North Cape encounter covers entry/idle, one normal-attack target/damage cycle, one Heal self-target/effect cycle, and one Item/list/target/consumption cycle. A natural Guardia Forest encounter additionally covers a three-enemy victory, reward, teardown, field return, and a matched-control Cyclone cycle that resolves two targets. A native-Mesen Lavos command-ready checkpoint adds exact zero/canary ownership traces for calibration, 60-frame idle, Down/Up command navigation, and Down-to-Tech: all 196 watched bytes receive zero callbacks. The accepted battle-action v4 extension adds exact zero/canary traces for one already-in-flight enemy action, Attack target selection, and one Crono critical Attack through command recovery. The action route pins the `$AE9B` bit-`$80` critical marker, preserves the control's party HP, lowers only enemy slot 3 from `8000` to `7038`, and exposes two exact `$7E2980` roster reads at advanced PCs `$C1:4A43/$C1:438A`; the candidate and guards receive zero measured access and no watched write occurs after observer arm. Noncritical Attack under this observer, attacks by other PCs, Tech/Item execution under this observer, remaining Tech classes, status/death, multi-PC victory presentation, battle teardown, persistence, and PC `$07` remain untested. | listed vanilla paths plus bounded Lavos command/action tranches `verified-runtime`; remaining paths partially `verified-static` | Record deterministic checkpoints for every unresolved path, extend the ownership census through noncritical/other-PC Attack, Tech, Item, status, death, victory/teardown, and persistence, then repeat through PC `$07` adapters. |

For every trace, record:

```text
subsystem:
emulator/core and hashes:
recorded-input hash:
SNES routine address:
input logical ID source:
computed index or pointer:
ROM/WRAM/SRAM data source:
observed output:
first safe hook point:
evidence artifact and hash:
```

## 7. ROM and save expansion strategy

This section records the conservative target architecture. Expanded-bank
ownership remains unassigned until the first production allocation manifest.

### 7.1 ROM data

`verified-static` for the inert scaffold; production allocations are
`proposal`

`tools/schala_rom_scaffold.py` validates the canonical 4 MiB fast-HiROM input
and creates an inert 8 MiB fast-ExHiROM image entirely in memory:

- map mode `$35`, size code `$0D`;
- vanilla file `$000000-$3FFFFF` preserved except deliberate header fields;
- file `$400000-$40FFFF` reserved as the required low-bank `$00` boot/data
  mirror;
- file `$410000-$7DFFFF` as the only approved explicit allocation pool;
- file `$7E0000-$7FFFFF` conservatively reserved because CPU banks `$7E/$7F`
  are WRAM;
- both header copies receive one validated checksum/complement pair.

The pinned inert target SHA-256 is
`26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93`.
Every future block must be named in an overlap-checked manifest; zero/fill
bytes never confer ownership.

The ignored inert image passes a controlled 3,600-frame bsnes2014 boot
checkpoint. `tools/compare_bsnes2014_states.py` compares it with two clean-ROM
runs, uses the clean pair to identify five run-variant payload offsets, and
finds zero additional differences. The entire 128 KiB WRAM image is
byte-identical.

The same inert transformation also passes 3,600-frame full-menu,
post-native-swap party-exchange, and native-battle state replays.
`tools/rebind_retroarch_bsv_rom_identity.py` changes only the replay metadata
and BST1 ROM identity while preserving the serialized core payload and input
stream. At all three checkpoints the relocation canary and guards survive,
and the complete output payload—including all WRAM—matches a repeated 4 MiB
control byte-for-byte after excluding ROM identity. These checkpoints start
inside the destination engine states; ordinary input transitions,
attack/tech/victory/exit, soft reset, translated save/write/load, New Game+,
long-run attract behavior, and an independent emulator remain gates.

Three additional recorded-input replays select Continue and load vanilla save
slots 1, 2, and 3 on the inert 8 MiB image. Every complete output payload and
all WRAM match a repeated 4 MiB control after excluding ROM identity. The
candidate relocation block is all zero in both mappings, as expected from
cold initialization. This proves the inert mapping through vanilla full load,
not the future translated ten-descriptor save or Schala sidecar restore.

The production build will use explicit `org` addresses in a pinned assembler,
Python-owned preimage/diff/checksum verification, and a deterministic BPS
patch. The current supported-slot diagnostic remains IPS. Boot, interrupts,
soft reset, save/load, and New Game+ must pass in two accurate emulators before
any non-inert expanded allocation is approved. Full details are in
`docs/schala_rom_expansion_architecture.md`.

### 7.2 Save and WRAM data

`hypothesis`

Schala needs:

- one independent `$50`-byte character record;
- one TP-progress byte;
- one learned-single-tech mask byte;
- combination-tech learned/eligibility state as actually required by traced
  code;
- recruited/available/locked state;
- active-party support for logical ID `$07`;
- a six-byte name field in Project Epoch storage; vanilla field 7 belongs to
  the Epoch and its PC-name pointer-table entry is null.

The vanilla save routine uses eight descriptors:

| Source | Length |
| --- | ---: |
| `$7E2400` | `$05B0` |
| `$7E2C23` | `$0033` |
| `$7E0400` | `$0010` |
| `$000100` | `$0010` |
| `$7F0000` | `$0200` |
| `$00027E` | `$0002` |
| `$000290` | `$0011` |
| `$7E2C7C` | `$001E` |

`verified-static`: each save slot is `$A00` bytes and its checksum spans the
whole slot. There is therefore no approved append point inside a vanilla
slot. The three slots end at `$30:7DFF`; global metadata begins at
`$30:7FE0`, leaving a bounded `$1E0`-byte candidate interval. A deterministic
canary has survived both boot and Continue/slot-1 load without changing
vanilla slots or metadata (`verified-runtime`). A second current-core control
now boots and idles 3,599 frames with one structurally valid v1 sidecar, then
loads Save #63 in a fresh process. The complete SRAM and sidecar remain exact,
Epoch and `$0430-$047F` remain protected, and `$7E2CA0-$2CEF` remains zero.
This proves vanilla compatibility/cold-load preservation for slot 1, not a
Project Epoch hook or production ownership.

The preferred proposal divides that interval into three `$A0` versioned
sidecars, one per slot. Normal save, full load, New Game+ partial load, and
erase paths must be adapted before this becomes production storage; no
distinct vanilla slot-to-slot copy routine was found. Vanilla erase currently
invalidates only its own magic word and would leave a stale sidecar behind.
If any ownership or compatibility gate fails, use deliberately expanded SRAM
instead. In either design, preserve vanilla slots byte-for-byte when Schala is
absent, include a format marker and checksum, and initialize safely when
loading an unmodified save. The full layout and canary hashes are in
`docs/sram_gap_sidecar_audit.md`.

The version-1 host policy remains frozen in `tools/schala_sidecar.py`:
initialized and New Game+ retention are the only valid header flags; quest
unlock, three-anchor progress, ward resolution, recruitment, and the one-time
join grant have a canonical eight-byte representation; unknown bits,
impossible state order, nonzero reserved bytes, CRC failures, and mismatched
vanilla checksums are rejected. The learned count/mask pair is canonical and
high-bit-first (`$E0` for three techs). However, v1's 16-bit checksum cannot
prove physical slot origin: two distinct `$A00` slots can collide. The
production-facing load planner therefore treats even a valid v1 record as
`legacy-v1-migration-required` safe-empty. Keep every v1 reserved byte zero;
migration is explicit, offline, full-source-bound, and never automatic.

`tools/schala_sidecar_v2.py` supplies the collision-resistant source format
without changing the `$A0` record size or gameplay offsets. Byte `$0E` is the
physical slot, `$0F` is binding profile 1, and `$80-$9F` is a full SHA-256 of
the exact selected `$A00` vanilla slot plus a 16-byte
`PE07BIND`/version/profile/slot/length trailer. The old 16-bit checksum remains
a cheap preflight. The digest covers the untouched slot tail
`+$0834-$09FF`, not only the `$834` bytes copied by vanilla save. CRC-16 covers
the complete sidecar with its CRC field zero. This binding is integrity, not
authentication or rollback protection. The first standalone current-bsnes
implementation is byte-correct but takes 366-367 NMI frames, about 6.1
seconds, per digest. A separate fixed-rotate candidate preserves the exact
profile and ABI and cuts that to 123-124 frames, about 2.05 seconds, while
passing two clean runs. The bounded round8/table candidate reaches 68-69
frames, about 1.14 seconds, and also passes twice. That roughly 5.3-fold
improvement still exceeds the predeclared 30-frame stop gate and is not a
production save/load implementation.

The source load planner now publishes only party-consistent v2. A pre-load
clear remains mandatory, but it is not sufficient: the vanilla full loader
blindly restores roster bytes `+$0580-$0588` and joined mask `+$05AF`.
Consequently every result after a valid copy contains a post-load party target
for the boundary before party consumers. Safe-empty replaces exact logical
`$07` with inactive `$87` and clears joined bit `$01`; valid v2 must already
agree with recruitment, join-grant, starting-tech, namespace, and duplicate-ID
invariants. Invalid vanilla metadata aborts before copy and exposes no party
write target, while the preclear still prevents stale PC `$07` state.

The preferred natural-record architecture avoids swapping live blocks around
the vanilla writer. Relocate the descriptor table and replace its first
`$05B0` region with three sequential regions:

```text
$7E2400 len $0430 -> slot +$0000..$042F
$7E2CA0 len $0050 -> slot +$0430..$047F
$7E2880 len $0130 -> slot +$0480..$05AF
```

Keep the other seven descriptors unchanged. The ten descriptors still
serialize the same `$834` bytes into the same vanilla slot layout, and the
checksum still covers the same `$A00`. The executable layout model and
byte-preservation tests are in `tools/schala_save_layout.py`. The same model
now proves the inverse direction: an exact immutable `$A00` slot restores
`+$0430-$047F` only to `$7E2CA0-$2CEF`, consumes exactly the native `$834`
prefix, preserves a precleared `$7E2830-$287F`, and round-trips the serialized
prefix without touching the checksum-bound `$834-$9FF` tail. Invalid table
fields, overlaps, missing/short banks, and partial tables fail closed. This is
host proof only, not an approved hook or WRAM allocation.

The same source model now separates initialization by namespace instead of
extending vanilla arrays in place. Normal new game consumes the exact native
`$280` seed, leaves its first `$230` bytes as the seven vanilla records,
relocates the final `$50` compatibility template to `$7E2CA0-$2CEF`, and
requires an independent exact `$50` PC `$07` record for `$7E2830-$287F`.
Attract/demo finalization likewise requires explicit caller-supplied `$50`
compatibility and PC `$07` inputs after the native seven-record copy; it does
not invent an eighth HP/MP/stat row. These functions prove destination shape
and preservation only. They do not author Schala's unresolved record bytes or
install either initializer.

Normal save must invalidate the selected sidecar first, call vanilla
`SaveSlot_Write`, wait for the complete `$A00` checksum/magic/global metadata
to finish, then derive/write v2 and commit sidecar magic byte `$00` last. On
completion the caller-finalized `$A00`, including `$0430-$047F` and Epoch's
name, must remain exact; this does not forbid a legitimate vanilla change from
the pre-save value. Only untouched tail `$0834-$09FF` must equal its pre-save
source. On
full load, clear PC `$07` even if validation later fails, revalidate vanilla,
run the translated descriptor
copy, validate v2, apply the sealed post-load party target, and only then
publish Schala. Candidate call boundaries are `$C2:CF51` for normal save and
`$C2:E657` for full load; neither is an approved hook.

The New Game+ partial loader's correctly ordered internal boundary remains
`$FF:FB3B`, before its party processing. The preferred translated source
contract replaces the native `$580` transfer with three exact copies:
`+$0000-$042F -> $7E2400-$282F`, `+$0430-$047F ->
$7E2CA0-$2CEF`, and `+$0480-$057F -> $7E2880-$297F`; it keeps the native
`+$05B0-$05E2 -> $7E2C23-$2C55` name copy. This preserves natural PC `$07`
and `$7E2980-$29AF` roster/joined state for explicit processing at the
boundary.

A current-bsnes negative control now observes the unmodified loader changing
`$7E2830-$287F` between replay frames 61 and 62 to the selected slot's
byte-exact `+$0430-$047F` data. The `$7E2CA0-$2CEF` canary and both guards
survive, matched zero/canary states differ only in that 80-byte canary span,
and the route reaches the native Battle Mode prompt. This is
`verified-runtime` evidence that translation is required, not evidence that
the source contract is installed or that `$2CA0` is globally free.

New Game+ is load-only: no newly serialized vanilla slot or checksum exists
there. Apply retain/reset policy as staged live state, reconstruct retained
recruitment/roster state explicitly because the partial loader stops before
`+$0580`, and bind/persist v2 only on the first later normal save. A wrapper
after New Game+ returns is too late, while the internal route still depends on
adapting every direct compatibility reader such as `$FF:F9A2`. Full details
are in
`docs/wram_compatibility_block_audit.md` and
`docs/schala_sidecar_v2_contract.md`.

`tools/schala_sidecar_v2_lifecycle.py` now makes those source boundaries
executable without touching a ROM. It gates every publishable `$50` record
through the registered PC `$07` identity, requires the exact source/slot-bound
preclear witness, refuses to read a sidecar when vanilla metadata is invalid,
and applies SafeEmpty `$07->$87`/joined-bit normalization after valid copies
even if other restored roster bytes are malformed. Its save path permits
legitimate caller-finalized compatibility and Epoch changes while preserving
the final `$A00` exactly; its New Game+ result remains unbound until a later
normal save. Preview tokens bind the independent Schala name and complete
source state. Erase breaks sidecar byte `$00` before any partial body clear and
runs the native selected-slot invalidation last. Twelve focused tests cover
all three slots and failure injection. This is still host proof, not an
installed lifecycle.

The binding-profile implementation now also has a relocatable,
correctness-first 65C816 source unit at
`asm/schala_sidecar_sha256_profile1.asm`. It streams the exact `$A00` selected
slot from bank `$30`, constructs the one fixed trailer/padding block, uses a
16-word circular SHA-256 schedule, and writes a 32-byte digest plus status
inside a caller-supplied `$C2`-byte WRAM scratch span. It installs no mapping,
allocation, or hook. The routine preserves `A/X/Y/P/DBR/D`, forces binary
arithmetic internally, restores the caller's decimal flag, and has statically
bounded stack growth of 16 bytes after entry (19 including the caller's
`JSL`). Nine host/oracle tests match standard, all-zero-slot, and patterned
vectors and assemble a deterministic 1,469-byte syntax probe.

The independent fixed-rotate source
`asm/schala_sidecar_sha256_profile1_fast.asm` preserves the same input,
profile, `$C2` scratch contract, digest bytes, invalid-output refusal, and
caller state. Ten focused tests and high-coverage host oracles pass; Asar
emits a deterministic 2,000-byte core. It remains a candidate rather than a
replacement for the correctness baseline.

The separate standalone builder
`tools/build_sha256_65816_standalone_benchmark.py` never accepts a game ROM.
It uses pinned Asar 1.91 only against a temporary all-`$FF` synthetic 8 MiB
image below `private/`, imports only source-labelled diagnostic spans,
independently finalizes the two ExHiROM header copies, performs complete-diff
accounting, and emits a disposable zero-filled 8 KiB SRAM. This is a separate
diagnostic audit rather than an exception to the production write-intent
guard. Full source ABI, tool provenance, reproduction commands, runtime
acceptance criteria, and remaining gates are in
`docs/schala_sidecar_sha256_65c816_benchmark.md`.

The standalone runtime record now passes all three physical-slot digests,
valid/invalid status handling, exact `A/X/Y/P/DBR/D/SP` restoration with a
hostile decimal-enabled caller, front/rear scratch guards, and interruption by
the benchmark's minimal NMI counter. Two runs have identical result,
scratch/guard, and exact-zero SRAM spans. This upgrades only standalone
correctness to `verified-runtime`: each call consumes 366-367 frames, and the
minimal handler does not stand in for the game's real interrupt workload.

The fixed-rotate candidate also passes two independent current-bsnes runs with
identical result, scratch/guard, and exact-zero SRAM evidence. It consumes
123, 123, and 124 frames for slots 1-3, approximately 2.047, 2.047, and
2.063 seconds at 60.10 Hz. The accepted private runtime manifest is
`c464ab1006847797e6b85fc85c80a03d978f5537e11fa6baed4d4093fff4840e`;
an earlier source-drifted manifest is rejected. This remains too slow for a
synchronous game hook.

The completed bounded source-only experiment uses eight-round symbolic
unrolling and exactly `$4000` bytes of generated byte-decomposition sigma
tables. The generator exhaustively verifies all 4,096 basis entries and
reconstructs deterministic adversarial inputs; the generated source SHA-256 is
`7455ce0e13d243cee1c8bd0a36c8ef3582f1df4176a155f837300b907b98e61a`.
The `$4A26`-byte core passes two runs at 68, 69, and 69 frames but lands in
the explicit stop category frozen in
`docs/schala_sidecar_binding_performance_architecture.md`. No game allocation,
hook, cooperative wrapper, or binding-profile change follows from this
experiment. Its fail-closed private runtime manifest hashes to
`ad20b04e0be5345184db3246bb6be02bd669ad0cb50d5b4799e3b9e874be7a45`.

## 8. Staged graphics pipeline

Phase A is a private vanilla-Schala donor diagnostic. It references the pinned
canonical NPC `$09/$26` family through independent adapters or consumes it
transiently from the clean ROM; it does not copy game data into source control,
relabel the NPC family, overwrite its tables, or claim a complete playable
packet. Map every supported animation role and leave missing roles explicitly
unbound before attempting logical PC `$07`.

Phase B is the final distributable replacement-art track. Those graphics must
be based on Schala's narrative identity, not copied NPC tile data:

1. Lock the new silhouette and palette hierarchy from the concept sheet.
2. Build an inventory of required vanilla field and battle animation
   categories without extracting them into release artifacts. The physical
   PC packet envelope is now measured; semantic slot coverage remains.
3. Draw new frames on the native tile grid.
4. Quantize deliberately to the traced per-sprite palette limit.
5. Assemble tiles, frame maps, timing, and palette data using a source
   representation owned by this project.
6. Compare every emitted tile against all relevant vanilla PC and Schala NPC
   tiles. Any exact or suspicious near-match must be redrawn unless it is a
   trivial blank tile.
7. Test visibility on dark, snow, indoor, and battle backgrounds at native
   scale.
8. Hash the source art, compiled tile data, and allocation manifest.

The concept PNGs are reference material only and must never be fed directly
to the ROM builder. Exact palette, tile, frame, provenance, and originality
requirements are maintained in `docs/schala_sprite_asset_spec_v0.md`.
The current partial target-grid implementation and its deterministic outputs
are recorded in `docs/schala_gameplay_sprite_foundation_v0.md`. Phase A's
private source contract is recorded in
`docs/schala_vanilla_npc_source_compatibility_v0.md`.

## 9. Content implementation order

Schala content is encoded only after the corresponding adapter exists.

1. Independent record, name, recruited state, and save/load round trip.
2. Roster and party exchange with eight distinct identities.
3. Field graphics and animation.
4. Portraits in save-select, status, roster, and party exchange.
5. Base stats, growth, equipment permission, and Focus weapons.
6. Normal attack, critical path, battle sprite, damage, hurt/death, victory,
   and battle exit.
7. Raw `$80-$90` command overlay, sparse action table, high-ID edge branches,
   queue round trip, and unchanged vanilla action IDs.
8. Eight single techs: names, descriptions, targeting, MP, effects,
   animation, TP progression, learned masks, and save round trip.
9. Six dual techs and two triple techs after combination logic is expanded.
10. Recruitment event and all dialogue/party-state branches.
11. New Game+, all save slots, and compatibility/migration checks.

## 10. Test ladder

Each rung must have deterministic input, emulator/core hashes, screenshots or
states where useful, and a written result.

### Gate A: supported-slot surface

- [x] Boot.
- [x] Continue/save-select.
- [x] Portrait render in Lucca's supported row.
- [x] Save-slot load.
- [x] Field sprite render.
- [x] Recorded field movement.
- [x] Main-menu entry and 600-frame idle.
- [x] Every top-level main-menu page and one native Tech owner switch.
- [x] Roster and one native party exchange with an actual swap.
- [x] Equipment-menu entry, rendering, and 600-frame idle.
- [x] One native equipment change with derived-stat recomputation.
- [ ] Shop menu.
- [x] Native battle entry and 600-frame idle.
- [x] Native battle-menu raw input and Confirm-state calibration.
- [x] One native basic-attack target/damage cycle.
- [x] One Crono critical Attack, including the runtime `$AE9B` bit-`$80`
      marker and damage/recovery endpoint.
- [x] One native Item/list/target/consumption cycle.
- [x] One native offensive two-target Tech with matched no-cast control.
- [x] Controlled vanilla event `$11C` magic grant in two prepared active-party
      profiles with matched zero/canary terminal states.
- [x] Native Mesen trace observes all 12 unmodified event `$11C` compatibility
      accesses with exact instruction PC, target, value, and order.
- [x] Native Mesen Lavos checkpoint and matched zero/canary ownership traces
      cover frame-zero calibration plus 60-frame idle, Down/Up command round
      trip, and Down-to-Tech. The complete old compatibility block, candidate,
      guards, roster, joined flag, and Epoch receive zero callbacks in this
      bounded command window.
- [x] Native Mesen battle-action v4 traces cover one already-in-flight enemy
      action, Attack target selection, and one Crono critical Attack through
      command recovery as exact zero/canary pairs. Candidate and guards
      receive zero measured access; the critical marker is exact, and the only
      callbacks are the two expected `$7E2980` roster reads in each recovery
      variant.
- [x] Native Mesen volatile relocated event `$11C` grant updates only the
      `$2CA0-$2CAB` targets in both prepared profiles while the complete
      prepared old block, candidate non-target bytes, guards, and Epoch remain
      exact. This does not represent a recompressed or installed packet.
- [ ] Every single-tech menu and battle path.
- [x] One natural victory, reward, battle exit, and field return.
- [ ] Status/death and multi-PC victory presentation.
- [ ] Save serialization behavior.

### Gate B: logical-ID adapters with placeholder assets

- [ ] `$00-$06` regression output matches vanilla.
- [ ] `$07` resolves an independent runtime record.
- [ ] `$07` survives save, power cycle, load, and all three slots.
- [ ] `$07` has independent roster and lock state.
- [ ] Placeholder graphics use a bounded provider in a named expanded
      diagnostic allocation, not indices 7/8 or a relabeled NPC descriptor.
- [ ] Vanilla compatibility state relocated from `$7E2830-$287F` survives
      menus, field transitions, battles, save/load, and New Game+ unchanged.
- [ ] Slot offsets `$0430-$047F` retain their vanilla meanings; Schala record
      bytes never replace them on disk.
- [ ] Raw `$80-$90` commands round-trip through menu selection, battle queue,
      execution, learning, and MP deduction; all signed/direct-index edges use
      Project Epoch data without changing vanilla action IDs.

### Gate C: Schala content

- [x] Vanilla PC graphics, assembly, animation, and field-transfer envelope
      measured without exporting source bytes.
- [x] Partial clean-room field/battle foundation compiles deterministically.
- [x] All ten current frames compile into the measured four-object packet
      shape and reconstruct exactly from serialized graphics/assembly bytes.
- [x] Native entrypoint/timing stream geometry, facing order, fixed-bank
      readers, menu roles, and the minimum battle/state selectors are pinned
      without assigning Schala-native IDs.
- [x] Two fresh native-Mesen repetitions per route reproduce one complete
      Magus/right-facing walk-selector timing loop at the prepared field
      checkpoint; the result remains exploratory and checkpoint-bounded.
- [x] The four current cardinal records load and render after a recorded
      Continue/slot-load and field movement in Lucca's supported slot.
- [x] The canonical vanilla Schala NPC family reconstructs locally into 23
      records, 79 fully referenced tiles, four primary facing blocks, one
      auxiliary block, and twelve colors without source-controlled raw bytes.
- [ ] Replay the vanilla-derived provider in a supported slot; map every
      exercised role and keep missing or ambiguous entrypoints safely unbound.
- [ ] Complete the original Chrono Trigger-style field/battle replacement
      inventory and compilation for the final distributable art track.
- [x] Original full and preview portrait compilation.
- [x] Original stats/growth/TP authoring data and overlay compile.
- [ ] Stats and growth runtime integration and equal-level balance.
- [ ] Focus weapons and equipment legality.
- [ ] Eight single techs and learning.
- [ ] Launch dual/triple set.
- [x] Original recruitment branch/dialogue foundation validates.
- [x] All 29 recruitment engine dependencies have bounded static routing;
      no binding is installed.
- [x] Reversible-stage/complete-grant/save-rebind recruitment ordering is
      host-tested with a synthetic PC `$07` fixture; runtime adapters remain
      uninstalled.
- [ ] Recruitment and optional dialogue.
- [ ] Balance comparisons under controlled RNG and equipment.

### Gate D: release regression

- [ ] Boot and checksum in two emulators.
- [ ] New Game and New Game+.
- [ ] Every recruitment ordering and Magus present/absent branch.
- [ ] Save slots 1-3, copy/erase if applicable, power-cycle reload.
- [ ] Every roster size from recruitment through eight characters.
- [ ] Field transitions, vehicles, End of Time, Black Omen, final battle.
- [ ] Status effects, death, revival, charm/steal interaction, victory.
- [ ] No vanilla PC regression.
- [ ] Deterministic patch reproduction from the pinned ROM.
- [ ] Release package contains no copyrighted source data.

## 11. Current blockers and next actions

1. Close the remaining record semantics (`+$01` low nibble and unmapped
   `+$02` flags) and finish the callers that assume seven tech owners,
   portraits, graphics sources, HP/MP rows, or TP rows.
2. Extend the regenerated current-bsnes checkpoints into shop paths, the
   remaining Tech target/effect classes, status, death, criticals, and
   multi-PC victory presentation.
   Every top-level main-menu page, one Tech owner switch, one equipment
   mutation/recalculation, and one Item/list/target/consumption cycle now pass
   in addition to the existing Heal and normal-attack cycles. Heal changes
   Frog from `837/999` HP and `99/99` MP to `999/999` and `97/99` against a
   matched no-cast control; the normal attack lowers Magus from `6666` to
   `6137`; the MegaElixir control/use pair changes only its battle-inventory
   quantity from 33 to 32. A separate natural three-Roly encounter now reaches
   `Found 480G` and returns to free Guardia Forest movement. Cyclone now has a
   matched no-cast control: `[14,14,14]` resolves to `[0,14,0]` with MP
   `99->97`, while the control remains unchanged. These paths still do not
   exercise an eighth identity or Schala-specific adapters.
3. Finish candidate sidecar runtime integration. The source-only v2 codec now
   supplies explicit physical slot identity and a full exact-`$A00` SHA-256
   binding; the production-facing planner refuses v1 publication, rejects
   malformed/colliding v2, and distinguishes post-copy party normalization
   from invalid-vanilla no-copy abort. The host lifecycle executor now proves
   all-three-slot save/load/NG+/preview/erase ordering and interrupted
   save/erase refusal without overwriting finalized `$0430-$047F`, Epoch, other
   slots, or other sidecars. Native slot-1 overwrite and fresh-process reload
   pass with exact `$0430-$047F` restoration, and a valid v1 sidecar survives
   the vanilla compatibility control. The correctness-first and fixed-rotate
   65C816 SHA implementations both pass standalone correctness/ABI/NMI
   benchmarks for all three slots. The fixed-rotate version reduces 366-367
   frames to 123-124; the round8/table version reaches 68-69 but still exceeds
   its predeclared 30-frame stop gate. Do not integrate any of them. Make the
   profile `$01` cooperative-transition versus new integrity-only-profile
   decision explicitly before Project Epoch hooks, all-three-slot game-context
   execution, and power-cycle persistence. Use expanded SRAM if the bounded
   gap, timing, or atomicity gates fail.
4. Finish the `$7E2CA0-$2CEF` installed save/load, erase, reset, and Project
   Epoch initialization matrix, then implement natural-record initialization
   and the ten-descriptor translations; use record resolvers only if the
   candidate fails. The unmodified attract and New Game+ cycles now have
   matched canary controls and both confirm natural-PC07 overwrite hazards.
   The source model pins their safe destination shapes, but neither replacement
   initializer nor loader is installed. The source audit now builds a
   fail-closed in-memory event `$11C` translation: it requires all 12 pinned
   operands, changes exactly their 24 low/high address bytes, reparses the
   `$0C6B`-byte packet, and proves no old-block reference remains. The
   controlled unmodified location-`$1D1` baseline now completes both prepared
   party profiles with exact predicted end state and matched zero/canary
   preservation. A native Mesen trace independently observes the exact 12
   `$C0:6797/$C0:6822` old-address operations, including target, value, and
   order, in matched zero/canary runs. A second accepted Mesen matrix requires
   the complete source packet at `$7F2000`, changes only the same 24 bytes in
   volatile WRAM, copies the full old compatibility block to `$2CA0`, and
   proves the 12 relocated operations with CPU-Y/DP/M/accumulator binding while
   old and candidate non-target state remains exact. None of these routes
   recompresses or installs the packet. Allocate, recompress, and install it
   only with the other relocation adapters, then rerun the matrix with an
   actual natural-PC07 record and the remaining lifecycle guards before
   declaring the relocation complete.
   The accepted battle-v3 Lavos command-ready ownership tranche separately
   proves zero access to all 196 watched bytes during calibration and three
   60-frame idle/navigation routes. That command-only tranche does not execute
   an action or observe an enemy turn. The accepted battle-action v4 extension
   now follows one already-in-flight enemy action and one Crono critical Attack
   through an exact critical marker, HP changes, and command recovery. Its
   only watched accesses are the same two `$7E2980` roster reads in each
   recovery variant; candidate and guards still receive zero access, and no
   watched write occurs. Noncritical Attack, attacks by other PCs, Tech, Item,
   status, death, victory/teardown, persistence, and natural PC `$07` paths
   remain required before relocation approval.
5. Implement the selected raw `$80-$90` command overlay, beginning with the
   sparse action table and the mandatory signed/direct-index branches; trace
   the `$C1:D70D` runtime flag before action execution.
6. Keep the completed encoded location-event animation-operand census within
   its static evidence ceiling, then implement or explicitly defer its closed
   inter-object control-flow and loader-lifetime model. Complete the separate
   data-driven battle action-package census before assigning any native Schala
   frame. The location-event audit now inventories all 10,637 encoded sites
   and proves the complete 116,064-entry direct-function topology; its
   incoming marker closure intentionally remains a possible-context
   overapproximation rather than runtime identity. The entrypoint stride,
   auxiliary timing family, fixed-bank setup/reader sites, menu roles, battle
   fixed minimum, and battle-state selector table are also proved, and a
   private checkpoint reproduces the field walk timing relation.
   The ten gameplay frames plus six Glass Focus body poses already fit one
   91-tile, 16-record native-shaped partial packet and reconstruct exactly,
   but their ordinals are not engine frame IDs. Next author complete
   facing/source/timing token sequences with conflict-free overlap, rerun the
   exact sources against the conservative 241-packet compressed corpus plus
   the bounded near-match/silhouette review, allocate the packet and `$20`-byte
   palette explicitly, then implement and runtime-test the `$FFFF`
   full-palette resolver and expanded-bank readers. The current partial
   sources have zero exact and palette-pattern matches against the 78
   nontrivial tiles in the documented Schala-family packet; that one packet
   does not close the broader corpus or completed-sheet gates.
7. Implement the named recruitment adapters in dependency order, beginning
   with independent naming, capacity-safe party insertion, and loader-level
   New Game+ normalization. Reproduce the source contract's reversible
   reserve stage, runtime-observed complete grants, and later exact-slot save
   binding at runtime; do not compile the authoring graph's symbolic
   pre-capacity commit order literally. Keep all graph bindings null until
   their runtime gates pass.

## 12. Change log

### 2026-08-23

- Completed an address-by-address audit of the historical `8thy` and Project
  Schala forum mapping. The forum did preserve valuable roots and collision
  leads for the natural `$7E2830` record formula, graphics/assembly/descriptor
  tables, portraits, element icons, attacks, Techs, names, party transport, and
  ExHiROM detection. Canonical re-verification also rejects the old
  `$CC:0230` eighth-record label, `$CD:400E` standalone attack-byte label,
  occupied low graphics rows, Epoch-name reuse, Gaspar/menu-scratch reuse, and
  historical 6 MiB relocation addresses. Project Schala's own posts explicitly
  bound its demonstrated line to Magus-slot replacement pending a complete
  redo for coexistence. The reusable 2018 lesson is the separation of generic
  PC `$07`, Tech, Schala-specific, and naming components, not the unpublished
  payload. Confirmed historical leads include the eight-by-five save-region
  descriptor table, the all-zero eighth stat-growth row (but no eighth HP/MP
  rows), seven-character healing/menu bounds, corrected Magus assembly extent,
  and animation-entrypoint-times-four rule. A modified-prototype ID7 name read
  at `$7E2CA3` is retained only as an adversarial watchpoint inside the still
  unapproved `$2CA0-$2CEF` relocation candidate. Four current metadata-only
  canonical-ROM audits were rerun without mutation. See
  `docs/historical_eighth_character_forum_mapping_audit_2026-08-23.md`.
- Proved that at least one private Project-Schala-era development patch was
  transferred to Vehek and that the unreleased Project Schala line was later
  demonstrated in a substantially developed gameplay state. The original
  thread records Justin privately sending Vehek a development patch on
  2008-12-30; Vehek posted debugger
  observations 47 minutes later and diagnosed its lost expanded-ROM marker.
  That discussion interleaves the generic `8thy`, variable-width-font, and
  Schala graphics work, so it is not promoted to proof that Vehek received the
  later rescue/Dream Devourer build. Nor does the evidence establish that
  Justin's retained incomplete copy and IPS, reported in March 2016, was
  byte-identical to that later demonstrated state. The project line did include
  a Schala rescue route and Dream Devourer/event work, while still replacing
  Magus rather than implementing a natural PC `$07`.
  No public copy was found in the attachment archive, forum/Wayback surfaces,
  creator repositories, inspected patch mirrors, or video comments. Recovery
  outreach remains a separate user-authorized action. See
  `docs/recovered_2008_eighth_character_prototype_audit_2026-08-23.md`.
- Located a separate 2009 Schala-as-PC8 proof in the `8thy` thread. Justin
  reported Schala's graphics working without palette or sprite-assembly
  conflicts and selected her as the test identity, while explicitly leaving
  animation repair open. The same-day follow-up says PC8 occupied Gaspar's
  party-exchange area. Classified this as a graphics/assembly diagnostic and a
  Gaspar party-exchange display-slot collision negative control, not
  natural-PC `$07` completion; Project Epoch will not consume that occupied
  display route as its architecture.
- Recovered the public 40,344,158-byte Kajar attachment archive under ignored
  local storage (SHA-256
  `DC06EBD5CF5527B444F10B5E52C33D4499BDED6AEA1911402236E809A706A5B9`).
  Its Schala Project folder contains only a screenshot, but its historical
  eighth-character folders preserve Mauron's 533-byte component IPS, Vehek's
  173-byte NPC-sprite adapter and 1,384-byte Temporal Flux event export, four
  Justin3009 6-MiB composite IPS variants, and two nested 2008 emulator states.
  None of those binary/media artifacts entered Git.
- Added a payload-free, read-only historical IPS metadata auditor and nine
  focused tests. It proves Mauron's complete 548-effective-byte patch and
  Vehek's complete 80-effective-byte adapter are byte-identical subsets of
  Justin's `almost Playable` composite. The later variants retain every
  component address with small value revisions. It also turns the recovered
  family into a negative-control ledger: two variants mutate the now-proved
  shared `$0D400E` PC `$07` normal-Attack/Crono-critical byte, all four touch
  protected low graphics/assembly/descriptor neighborhoods and bank `$40`, and
  the six-letter/fresh variants touch the null PC-name entry `$07`. No ROM,
  patched image, patch payload, hook, or allocation was emitted or approved.
  Verification passed all nine focused tests and the complete 906-test
  repository suite, with 22 environment-dependent tests skipped.
- Completed a direct forensic review of Justin3009's 92-second Project Schala
  video and surviving author comments. The prototype successfully presents
  Schala through Magus's supported PC `$06` path in save select/Continue, party
  exchange, menus, portrait and several four-direction field roles. Schala's
  label renders, but the party-exchange screen also visibly mislabels Frog as
  Schala, so independent name transport was not solved cleanly.
  It is not a complete replacement: Shadow, Magus's equipment, all eight Magus
  single Techs, existing Magus dialogue and at least one unconverted Magus
  sprite role remain, while battle, attacks, Tech execution/learning,
  recruitment, New Game+ and Magus coexistence are unproved. Classified it as
  a partial presentation prototype and a useful adapter-family comparison, not
  PC `$07` evidence. No completed public IPS, builder or gameplay source was
  found in the bounded search; no video, derived frame, comment corpus or game
  data was committed. See the direct prototype audit in
  `docs/eighth_playable_character_external_research_2026-08-22.md`.
- Reconciled the Crimson Echoes / Project Schala art-provenance boundary.
  Public sources conflict over whether the abandoned playable-Schala idea was
  once scheduled inside Crimson Echoes, while a contemporaneous project post
  treats Schala Project as a separate effort. Justin3009's surviving video
  and a direct review of its 92-second stream show only field/menu material,
  not a battle, executed attack, executed Tech, or other additional playable-
  role animation. Its
  preserved screenshot is byte-exact with the live video thumbnail and shows a
  vanilla field pose; its portrait is derivative from official art. The
  current Project-Fonts repository contains fonts rather than a licensed
  gameplay sheet, and Flames of Eternity's documented Schala/Magus hug proves
  event presentation rather than a new graphics record. No exact additional
  frame, pixel author, reuse license, or authorizing email was proved; no
  creator was contacted and no community pixels were imported. See the dated
  supplement in
  `docs/eighth_playable_character_external_research_2026-08-22.md`.
- Kept the permission gate asset-specific. Canonical vanilla Schala bytes remain
  a private clean-ROM-derived compatibility input, while any genuinely new
  community frame would require exact source/revision/transformation
  provenance and permission from its actual author. Refusal or silence means
  no permission, and community approval cannot confer rights over vanilla
  Chrono Trigger art.
- Restored recruitment audit rows 22 and 23 to the frozen authoring-schema IDs
  `schala_original_field_sprite` and `schala_original_battle_sprite`. The
  private vanilla provider changes the current evidence and diagnostic input,
  not those binding identities. This repairs the documentation-only drift from
  the provider commit without changing the pinned authoring JSON.

### 2026-08-22

- Selected a staged Schala visual policy. Phase A derives the canonical
  vanilla NPC `$09/$26` family transiently from the user's pinned clean ROM for
  private adapter diagnostics; Phase B preserves the existing original v0
  assets for a later Chrono Trigger-style replacement pass. Crimson Echoes and
  Flames of Eternity additions remain disabled pending exact attributable
  source and explicit reuse permission.
- Added the fail-closed vanilla-NPC compatibility builder and metadata-only
  reference. The source reconstructs 79 tiles, 23 exact `$28`-byte records,
  four aligned 36-byte primary facing blocks, a 36-byte auxiliary block, and
  a twelve-color palette. Fourteen focused tests pass, including canonical
  rebuild, full descriptor-family census, corrupted-ROM refusal, private-path
  and reparse enforcement, exact artifact-name allowlisting, transactional-
  stage failure cleanup, idempotence, conflict refusal, and byte-exact no-write
  metadata mode. No ROM or patch is emitted, and extracted packet bytes remain
  ignored under `private/`. See
  `docs/schala_vanilla_npc_source_compatibility_v0.md`.
- Added the fail-closed, metadata-only battle action-package topology census.
  It preserves the distinction between player-command IDs, internal PC
  type-2 animation-config rows, package selectors, bank-qualified descriptor
  roots, owner bits, and direct script entrypoints. Six fixed internal config
  rows resolve through seven bounded producers, while row `$7E` remains
  unclaimed rather than free. The direct encoded-operand census separately
  records adjacent `$AE92` candidates because an unresolved 16-bit write could
  affect `$AE93`. No command stream, runtime reachability, hook, allocation,
  PC `$07`, or Schala binding is claimed. See
  `docs/battle_action_package_topology_census_v0.md`.
- Refreshed the public eighth-character survey against first-person Mauron
  status posts and current source repositories. No complete, source-licensed
  natural SNES PC `$07` implementation was found in the bounded search. The
  useful adoption lead is the bank-qualified player-Tech package design
  exposed by `Pseudoarc/ctrando`. Its Python host plumbing is MIT-licensed,
  but the opaque embedded routine is attributed to Mauron without separate
  license/source provenance; no machine bytes, copied canonical roots,
  allocator choice, or hook were imported. Project Epoch will reconstruct and
  prove the behavior independently before any hook or named expanded
  allocation is proposed. See
  `docs/eighth_playable_character_external_research_2026-08-22.md`.
- Added the source-only Schala player-Tech package-bank adapter v0. It pins
  seven canonical spans, proves all 128 canonical `(CE,root)` identities by
  hashes without emitting their payload, preserves the original `$00-$7F`
  resolver as the selected architecture, and host-tests exact masks,
  bank-qualified direct entries, bank-boundary refusal, unbound candidate
  `$80-$8F` package selectors, same-low/different-bank identity, both `$A0B3`
  branches, all 16 owner bits, exact word-write footprints, cursor/mask/flag
  exit state, and repeated-pointer aliases. Equal
  command/package numbers create no mapping. Command `$1E` remains a hard
  fixed-`$CE` nested-script blocker, while config bytes `+3/+4/+5` expose
  independent fixed-bank auxiliary readers. No hook, allocation, package,
  Schala action binding, ROM write, or runtime proof is claimed. See
  `docs/schala_player_tech_package_bank_adapter_v0.md`.
- Added the fail-closed, read-only location-event animation operand census.
  It inventories all 10,637 encoded `$AA/$AB/$AC/$AE/$B3/$B4/$B7` sites in
  391 packets and preserves the entrypoint/static-frame/repetition namespace
  split. The complete 116,064-entry function topology includes 1,864 backward
  cross-owner targets, 321 forward targets, and 84 exact packet-end sentinels,
  so the tool uses an incoming direct-entry marker closure rather than
  physical adjacency. That conservative closure yields 927 PC-only-marker,
  23 mixed, and 1,794 no-PC-marker animation source owners, covering 5,624
  possible-PC-marker sites without claiming runtime reachability. The
  31,731-byte metadata report has SHA-256 `d170c0d5...`; all 19 focused tests
  pass. No ROM, decoded packet, ordered script, patch, runtime PC `$07`,
  Schala binding, allocation, or hook is emitted or approved.
- The complete ROM-backed regression now discovers 883 tests: 879 pass and
  four skip explicitly under their existing privilege/toolchain gates. All 90
  source-controlled Python tools parse under the bundled Python 3.12.13
  runtime, and the canonical ROM remains byte-identical before and after.

- Confirmed RetroArch 1.22.2 remains the newest official stable frontend,
  restored the exact July Project Epoch frontend/core bytes on `C:`, and
  installed the official 2026-08-22 rolling bsnes core in a separate portable
  tree. The new DLL is 5,661,090 bytes, SHA-256
  `bb00b395dcac6db960ecacaaf40ea9906fea9b7e23cedf55f8d117c44fcdde78`;
  it is a separate runtime evidence line, not a replacement for the older
  `003c7de0...` core pin.
- Preserved the exact mutable-download response headers and archive SHA-256
  `60441409e6877b52bb135588cba1b278d7713db0ec512b188aae66599ced3081`.
  The observed source head is recorded as an inference because the buildbot
  artifact has no cryptographic per-binary source-commit attestation.
- Ran the new core twice against the original standalone round8 diagnostic.
  Both serializer-115.1 captures reproduce `68,69,69` frames, the exact result,
  scratch/guard, and zero-SRAM hashes, the known eight-byte serializer span,
  and zero unaccounted differences. The greater-than-30-frame production stop
  gate remains in force.
- Ran two additional isolated 120-frame copies of the canonical clean ROM.
  Both exit successfully, serialize state, and preserve exact ROM/all-zero
  SRAM bytes. Their black early-boot thumbnails support no visual-title claim.
  The complete current-core provenance and evidence boundaries are in
  `docs/current_emulator_update_2026-08-22.md`.
- Kept all three accepted historical runtime manifests byte-identical. The
  fast and round8 live-artifact tests now check for the original pinned
  toolchain in their skip predicates, so an unavailable `D:` reports two
  explicit environment skips instead of false evidence errors.
- The complete regression discovers 765 tests: 763 pass and exactly those two
  historical live-artifact checks skip. All 85 source-controlled Python tools
  parse under the bundled Python 3.12.13 runtime.
- Added the read-only current-body packet audit. The unchanged ten gameplay
  frames plus six Glass Focus body poses compile in memory into sixteen
  `$28`-byte records and 91 tiles, preserve the complete ten-frame packet as an
  exact prefix, and reconstruct every source canvas. The graphics, assembly,
  and palette hashes are `361ea699...`, `b1473536...`, and `782a063f...`.
- Kept that new claim bounded: the 16 ordinals are provisional source order,
  the six Focus inserts and audio recipes are excluded from the body packet,
  and no animation slot, auxiliary family, ROM address, action/item/sound
  binding, PC `$07`, save/load path, hook, allocation, or Epoch data is
  assigned.
- Added the fail-closed animation semantic-contract v0. It pins the
  `$00-$03` engine-facing order documented as up/down/left/right, the
  variable-length `N*4` entrypoint
  rule, nine auxiliary pointers through `$E4:B614`, the bounded Magus
  `$AEC0-$AFB4` timing contract, fixed-bank setup/reader sites,
  field/menu/battle minimum, and the complete 16-record battle-state selector
  table. The 68,305-byte
  metadata report has SHA-256 `50374ada...`; all 21 focused canonical-ROM
  tests pass. No Schala-native ID, stream, pointer, allocation, hook, or
  expanded-bank adapter is assigned.
- Promoted a hardened tracked native-Mesen launcher/collector with strict
  workspace-private path, reparse, schema, mapping, object-binding, count,
  source-hash, timeout, and teardown gates. The focused suite discovers 35
  tests: 33 pass, and two privilege-dependent real-symlink cases skip with
  deterministic mocked reparse coverage passing.
- Ran two final idle and two final Right-input native-Mesen field probes from
  one pinned checkpoint. The Right route reproduces one complete selector
  `$01`, facing-3 Magus loop: frames `$10-$15`, six `$07` delays, timing-zero
  reset, then `$10` again. Both repetitions share exact normalized trace and
  semantic-manifest identities for their route; all named source
  ROM/SRAM/state/emulator inputs were preserved and staging was removed. The
  result remains exploratory and checkpoint-bounded, and every raw trace,
  screenshot, ROM, SRAM, state, and emulator artifact stays ignored.

### 2026-07-28

- Accepted a native-Mesen Lavos Core command-ready checkpoint from the
  recovered pre-Lavos SRAM. Its canonical `261614`-byte state and three
  semantic TSV traces repeat exactly, fresh processes prove Attack
  Down/Up restoration and Down-to-Tech without an action, and all protected
  WRAM plus the complete SRAM image remain exact.
- Separated deterministic checkpoint evidence from renderer presentation.
  `checkpoint.json` and the four accepted state/trace artifacts are hash-gated;
  each run records PNG hashes in a presentation manifest, but changing Lavos
  frames cannot promote or reject the checkpoint.
- Derived a private battle-v3 ownership collector from the exact accepted v1
  source. The builder pins every replacement preimage, uses the fixed
  `project_epoch_mesen_lavos_clean.sfc` stem and all-zero Mesen power-on RAM,
  and deletes the generated Lua plus disposable emulator tree after each run.
- Ran frame-zero calibration, 60-frame battle idle, Down/Up command round trip,
  and Down-to-Tech as exact zero/canary pairs. All 196 watched bytes record
  zero callbacks; the old `$2830-$287F` block, `$2CA0-$2CEF` candidate, guards,
  roster, joined flag, and Epoch remain unchanged. The loaded checkpoint pins
  direct page `$0000`, battle UI `$0059AC`, the complete combatant vector, and
  full HP.
- Froze the exact eight trace hashes in
  `references/mesen_wram_ownership_battle_scenarios_v3.json` and the complete
  source/private-evidence contract in
  `references/mesen_wram_ownership_battle_accepted_artifacts_v3.json`.
  Accepted and independent replay roots validate and have byte-identical JSON
  traces. Screenshots remain supporting-only because prior otherwise-identical
  runs exposed adjacent Lavos presentation frames.
- Kept the battle-v3 command-tranche claim bounded: it executes no attack,
  Tech, Item, enemy action, damage, status, death, victory, teardown,
  save/load, reset, attract, shop, equipment, or naming path. Neither WRAM
  range nor the compatibility relocation is approved.
- Accepted the battle-action v4 extension as three exact zero/canary pairs:
  no-input action control through frame 606, Attack target hold through frame
  60, and one Crono critical Attack through frame-606 command recovery. The exact
  endpoint HP/UI/command signatures and all six trace hashes are pinned by
  `references/mesen_wram_ownership_battle_action_scenarios_v4.json`; the
  complete source/private-evidence manifest is
  `references/mesen_wram_ownership_battle_action_accepted_artifacts_v4.json`
  (`11045` bytes, SHA-256
  `0d0936cccb1640109eeab09b870281ff638e736bcd75b1b77fc2ce93a319c2d6`).
- The control and recovery party HP match at `739,821,712`; only the recovery
  route lowers enemy slot 3 from `8000` to `7038`. The action timeline pins
  enqueue at frame 32, the already-in-flight enemy damage at frame 337,
  dequeue at frame 373, the `$AE9B` bit-`$80` critical marker at frame 375,
  player damage to enemy slot 3 at frame 557, and command recovery at frame
  606.
- All 196 watched counters reconcile. Candidate and guards receive zero
  measured access, and no watched write occurs after observer arm. In each
  recovery variant, the only callbacks are reads of `$7E2980` at frame 377
  with advanced PCs `$C1:4A43` then `$C1:438A`. The accepted and independent
  replay JSON traces are byte-identical; screenshots are presentation-only.
- Kept the v4 claim bounded to one already-in-flight enemy action and one
  Crono critical Attack. It does not approve the WRAM candidate or relocation,
  prove PC `$07`, or cover noncritical Attack, attacks by other PCs, Tech,
  Item, status, death, victory, teardown, persistence, or the wider lifecycle
  matrix.
- Added the fail-closed, read-only logical-PC-`$07` Attack boundary audit in
  `docs/pc7_attack_adapter_audit.md`. It proves that `$CC:258A`, `$CC:F643`,
  `$CD:4007`, `$CD:400E`, and `$CD:4015` are occupied boundary results rather
  than free eighth entries. The audit emits table hashes and five lookup-byte
  observations only; it performs no ROM, patch, save, state, or trace write.
- Continued the chain through `docs/schala_focus_pulse_adapter_architecture.md`.
  Raw action `$90` reaches `$CC:221B` inside Tech properties, Focus weapon IDs
  `$E8-$EB` reach four spans inside enemy Attack-animation records, and a
  three-selector append reaches `TechAnimPtrTable[0]`. Ten hashed canonical
  regions and 11 focused tests now pin the action, three-branch weapon config,
  selector resolver, and downstream fanout without emitting table bytes.
- Froze separate, allocation-neutral unbound v1 schemas for the PC `$07`
  Attack decision and the four Focus weapon visuals. Only Project Epoch-owned
  identities are nonzero; approach and selector values, all three-by-five
  WRAM-output blocks, expanded pointers, and reserved bytes remain zero.
  Sixteen focused tests enforce exact `$10`/`$18` layouts, boundary-contract
  and original-source identity cross-checks, table ordering, round trips, no
  ROM/NPC data import, no project binary emission, and fail-closed refusal
  before any WRAM write.
- Closed the Focus weapon palette/sound boundary without modifying the ROM.
  The three 96-byte map tables, the 64 six-byte bank-`$D1` palette rows, and
  the 256-word Attack-package offset table are hash-pinned. Direct `$E8-$EB`
  palette lookups collide with existing hit-SFX rows; the swing and hit
  lookups collide with reachable selector-`$00/$02/$03` enemy
  Attack-animation packages. The PC normal-Attack path uses a separate
  resolver. The required future composite binding consequently has distinct
  palette-source, swing-cue, and hit-cue semantics, while the current v1
  descriptor and every runtime pointer remain zero.
- Authored the first bounded Glass Focus / Focus Pulse source slice: six
  distinct 40-by-40 basic-Attack poses, six standalone 16-by-16 Focus
  inserts, and separate integer-only swing/hit recipes. The palette is
  referenced from the existing original Schala source rather than copied,
  Project Epoch's own body pixels are truthfully declared as reused/adapted,
  and every native ID, pointer, rendered-audio path, and runtime binding is
  null. Twenty-eight source/manifest tests and ten originality-wrapper tests
  pin exact identities, schemas, narratives, 4bpp round-trips, deterministic
  audio serialization, provenance, the source-only manifest, and the
  reproducible metadata report.
- Applied a metadata-only playable-PC originality correction to the new
  impact arc without displaying or exporting canonical reference pixels.
  Of 174 candidate and 7,264 playable-PC reference tile occurrences, the
  stated sparsity policy excludes 80 and 59 respectively. The remaining 94
  candidate and 7,205 reference tiles have zero exact-index and zero
  palette-renaming-invariant matches. That wrapper itself makes no NPC
  originality claim.
- Added the conservative compressed sprite corpus. A strict read-only C3
  decoder accepts 241 packets in `$07-$F7`; the audited NPC and normal-enemy
  descriptors select 237 of them. The four catalog-only selectors remain
  explicitly not-free, and enemy IDs `$F8-$FF` remain separate from the null
  pointer slots with the same numeric range. Twenty-one focused tests and an
  independent assembly-faithful decoder reproduce both aggregate hashes.
- Added the bounded Schala NPC originality audit. The static
  `$14E -> $0CE -> object $0F -> NPC $09 -> selector $26` chain reaches a
  79-tile packet with one trivial tile. The current gameplay foundation
  compares 100 nontrivial tile occurrences and Glass Focus compares 94;
  neither has an exact or palette-renaming-invariant H/V/HV match against the
  78 reference tiles. All five behavior-bearing helper modules are pre-use
  hash-gated, and 24 focused tests reproduce the metadata-only report. This
  closes only the documented Schala-family packet; the global corpus,
  near-match, completed-sheet, and runtime-identity gates remain open.

### 2026-07-27

- Audited public Crimson Echoes, Temporal Flux/Redux, Jets of Time, Data
  Crystal, Chrono Compendium, and ExHiROM guidance. The bounded
  `docs/community_modding_reconnaissance_2026-07-27.md` survey records useful
  workflow and breakpoint leads alongside the public false-eighth-record,
  false-eighth-attack-byte, and generic-free-space counterexamples. Community
  material remains guidance, never PC `$07` or allocation proof.
- Completed a 51-artifact current-bsnes compatibility-canary tranche. All six
  top-level menu pages render, the Tech page switches to Marle, Crono equips
  the Kali Blade with an exact weapon/Attack recomputation, and Frog completes
  a native MegaElixir list/target/consumption cycle against a matched no-use
  control. Thirteen terminal states preserve the exact `$7E2CA0-$2CEF`
  canary, both zero guards, and byte-exact disposable SRAM.
- Calibrated a natural Guardia Forest encounter boundary, defeated three
  Rolys with ordinary attack/target cycles, rendered `Found 480G`, and
  returned to free field movement. A separate 37-artifact fail-closed set
  preserves the relocation canary, both guards, `$0430-$047F`, and disposable
  SRAM across the complete route; it is structural evidence, not a balance
  fixture.
- Completed a 25-artifact native Cyclone tranche from that battle checkpoint.
  A matched no-cast control keeps all three Rolys at 14 HP and Crono at 99 MP;
  the cast resolves enemy slots 3 and 5 to zero, leaves slot 4 at 14, spends
  2 MP, and restores the command menu while preserving the canary, guards,
  compatibility bytes, and SRAM.
- Completed a 37-artifact current-bsnes attract tranche from an exact title
  checkpoint through entry, Flea and Zombor battle clips, a Zeal field scene,
  and return to title. Matched zero/canary endpoints differ only in the exact
  80-byte `$2CA0-$2CEF` span and have identical screenshots. Vanilla
  overwrites natural PC `$07` between replay frames 2,130 and 2,131 while the
  candidate and guards remain exact, confirming the required attract adapter
  without claiming Project Epoch initialization.
- Extended the BSV2 canary injector with a fail-closed pinned current-bsnes
  title-state mode. It accepts only the exact 290,423-byte `BST1`/115.1 layout,
  preserves every replay frame, and deterministically reproduces the accepted
  attract canary carrier.
- Completed a current-bsnes New Game+ negative control from a checksum-valid
  unlocked SRAM. Selecting slot 1 changes natural PC `$07` in one frame to
  byte-exact slot `+$0430-$047F`, while the relocation canary and guards
  survive and matched zero/canary runs reach the native Battle Mode prompt
  with identical screenshots and unchanged disposable SRAM.
- Extended `tools/inspect_current_wram_candidate.py` to expose all seven live
  field equipment rows, nonzero field inventory slots, and nonzero five-byte
  battle-inventory rows, plus all twelve `$80`-stride battle combatant
  records; focused synthetic tests pin those new diagnostics.
- Added the relocatable correctness-first 65C816 implementation of sidecar v2
  binding profile `$01`, with exact all-three-slot host vectors, caller-ABI
  preservation, invalid-pair refusal, `$C2` scratch bounds, and pinned Asar
  1.91 syntax output.
- Added the original all-`$FF` standalone ExHiROM builder, complete-diff
  auditing, disposable zero SRAM, current-bsnes state inspector, and
  fail-closed two-run runtime manifest. The reference passes every functional
  check at 366-367 frames per digest, about 6.1 seconds.
- Added and separately pinned the fixed-rotate candidate. It passes two clean
  runs at 123-124 frames, about 2.05 seconds and roughly three times faster,
  while preserving the reference evidence. A source-drifted intermediate
  manifest is rejected.
- Generated the exact `$4000`-byte sigma-table source from mathematical
  definitions and exhaustively verified all 4,096 basis entries. The separate
  round8 core embeds K/schedule indices and removes runtime state shuffles
  without changing profile `$01`, stack, scratch, output, or invalid behavior.
- Measured the round8 candidate twice at 68, 69, and 69 frames with identical
  accepted result, scratch/guard, and zero-SRAM spans. Its fail-closed runtime
  manifest triggers the predeclared greater-than-30-frame stop gate, so no
  synchronous or cooperative game integration is approved. The next step is
  an explicit profile `$01` transition versus new integrity-profile decision.
- Added the inverse ten-descriptor load model. It restores slot
  `+$0430-$047F` to the relocated compatibility block while preserving a
  precleared natural PC `$07` record, proves an exact serialized-prefix
  round trip with untouched slot tail, and rejects malformed or overlapping
  descriptors.
- Added source-only initialization contracts for the normal `$280` new-game
  seed, explicit attract finalization, and the exact four-region translated
  New Game+ partial load. They preserve natural PC `$07` and NG+ roster state
  without authoring unresolved Schala bytes or installing a hook.
- Closed the `$C1:F29C` post-battle combo-learning bound. The canonical
  five-byte table has 25 live records followed by one final sentinel, so
  `$283E + index` can reach only `$283E-$2856`; the path cannot touch the
  rock flags at `$2857-$285B`. The source audit pins the table, code, and
  disassembly hashes without emitting raw payload bytes.
- Extended the complete location-event audit to inventory all 1,511 absolute
  memory commands. Event `$11C`, object `$09`, location `$1D1` contains the
  only 12 compatibility-span hits and must be translated to
  `$2CA0-$2CAB`; no event absolute command reaches `$285C-$287F`.
- Added the fail-closed source-only event `$11C` transform. It pins the
  compressed/decompressed packet identity and exact 12-site preimage, changes
  only 24 address bytes in memory, preserves packet size, reparses every
  translated site, and emits hashes/metadata rather than packet data. Static
  route analysis pins Spekkio's object/function call, the three-lap gate, and
  the two-party runtime requirement; no local natural pre-grant fixture was
  found.
- Added a bounded current-bsnes vanilla baseline for that route. Prepared
  Magus/Robo/Frog and Crono/Marle/Lucca profiles both reach storyline `$4D`
  with the predicted tech counts, masks, magic flags, and TP. Each matched
  zero/canary terminal pair differs only in `$7E2CA0-$2CEF`; guards, Epoch,
  paired screenshots, and disposable SRAM remain exact. This does not test an
  installed translated packet or a natural first-grant save.
- Added a native Mesen 2.1.1 instruction-level cross-check for the same
  unmodified event. Each zero/canary pair repeats an exact sequence; after
  collapsing the pairs, the profiles contain the predicted nine-plus-three
  unique accesses at `$C0:6797/$C0:6822`, including live pointer targets and
  `$03/$1F/$FF` values. Candidate, guards, Epoch, and pair-identical
  screenshots remain exact. A canonical-path host launcher now runs a fully
  isolated temporary Mesen app and uniquely named disposable ROM/SRAM, pins
  the validator and complete relevant runtime, refuses output collisions,
  and accepts only the exact traced JSON/PNG hashes. The collector, launcher,
  strict host validator, private manifest, and public hash contract add no
  ROM, SRAM, or state data. This closes the old-address transient baseline
  only; translated packet installation remains blocked.
- Added the accepted volatile relocated event `$11C` matrix. The collector
  requires the full source packet at `$7F2000-$7F2C6A`, proves the exact
  12-site/24-byte relation, changes those volatile operands, copies the
  complete `$2830-$287F` block to `$2CA0-$2CEF`, and requires the full
  transformed packet after preparation and at termination. Every explicit
  collector `write8`/`write16` call targets `snesWorkRam`. CPU Y, direct page
  `$0100`, M, live operand pointers, and pre/post-STA values bind every routed
  access to its command. An initial full-old-block canary correctly exposed
  legitimate rock-flag recalculation at `$2857-$285B`; the accepted control is
  limited to `$2830-$283B` and does not overwrite the existing tail. Across
  four accepted cases, zero/canary pairs have identical callbacks, candidate
  endpoints, and screenshots; the complete prepared old block, candidate
  non-target bytes, guards, Epoch, ROM, SRAM, and shared saves remain exact.
  The exact PNG gate now pins field frame modulo 16 to zero and Spekkio sprite
  frame 22 for Magus/Robo/Frog or 4 for Crono/Marle/Lucca, removing adjacent
  idle-frame nondeterminism.
- Hardened that matrix under current acceptance v3. The accepted root is
  `private/test_runs/mesen2/event11c_relocated_accepted_hardened_v4`, the
  independent guarded replay is
  `private/test_runs/mesen2/event11c_relocated_launcher_replay_hardened_v4`,
  and the 8,934-byte
  `references/mesen_event11c_relocated_trace_accepted_artifacts_v3.json`
  contract hashes to
  `839b86310dbe33273cf14ffec01386aa4ee6b88426b100be2cdc65d17a0790cc`.
  Acceptance v1 and v2 and their roots remain retained as historical
  evidence. V2 mislabeled the incompatible hardened shape as
  trace-v1/collector version 1. The current validator requires trace schema
  v2 and collector version 2 because the shape removed synthesized
  `absolute_frame`, added phase fields, and narrowed the explicit-write scope.
  Both four-trace sets pass and all eight accepted/replay artifacts are
  byte-identical. The launcher exact-byte compiles and executes pinned Python
  modules, reads and hashes the legacy launcher only for provenance without
  executing it, stages the verified collector and checkpoint, and publishes a
  staged trace/PNG pair using exclusive `xb` creation plus identity-limited
  rollback. The pinned collector, validator, and launcher are respectively
  `35700` / `4413876f258c091a728a8d6d53e2aea824206c5e7f9852ca476b5ee5c974070c`,
  `24820` / `2025a749fc3081ff7a6dfeb49b7b1c9aa6ae31241c4744be14c23d63e06de186`,
  and
  `43512` / `78371ecb3974046d170d6613239d08c3b7a56252681af0bb352dac12e4676b4c`.
  This remains verified only for an already-decompressed volatile packet.
  `loadSavestate` and game execution may alter other transient emulator state;
  the host proves source files and shared saves unchanged. No ROM allocation,
  pointer, hook, global candidate ownership, PC `$07`, or persistence adapter
  is approved.
- Added a generic native-Mesen WRAM ownership collector rather than extending
  the event-specific tracer. It watches all 196 bytes in the vanilla
  compatibility block, roster, joined flag, Epoch name, four-byte front
  guard, 80-byte relocation candidate, and sixteen-byte rear guard. The zero
  variant asserts the candidate is already zero and performs no candidate
  write; the canary variant installs the original deterministic 80-byte
  Project Epoch canary. All preparation finishes before callbacks/counters
  arm, and the collector refuses to proceed unless every watched counter then
  reads zero.
- Ran calibration, 600-frame field idle, 600-frame main-menu, and the
  Frog/Spekkio event route as exact zero/canary pairs. Calibration records no
  callbacks. Field idle records 450 roster reads. The menu records 52
  old-block and 72 roster reads. The event records 1,224 callbacks: 1,106
  roster reads and 118 old-block operations, including the exact
  `$2834/$283B` grant sequence plus 25 same-value rock-tail writes. The
  validator simulates every watched byte so non-target event writes are
  accepted only when they are same-value/no-net-change; complete pair
  callback and counter streams must remain identical.
- Hardened the Mesen 2.1.1 observer against three runtime-specific behaviors.
  Raw `snesWorkRam` callbacks are normalized to raw WRAM through
  `convertAddress`; the working access-counter call order is
  `(memoryType, counterType)`; and callback PCs are the advanced
  `$C0:6799/$C0:6824` values rather than the instruction entry addresses.
  Access counters cover every watched byte and must reconcile exactly with
  the independent callback log.
- Removed renderer-boundary nondeterminism without extending the measurement.
  The event trace freezes and disarms at the first valid `endFrame` route
  endpoint. If Mesen still exposes the adjacent Spekkio presentation buffer,
  only screenshot acquisition waits; the already-frozen callback stream does
  not. The launcher publishes only the exact canonical 9,503-byte PNG.
- Accepted all eight exact cases under
  `references/mesen_wram_ownership_accepted_artifacts_v1.json`
  (`10813` bytes,
  `b8f863ab2db7ed5f17222c59044a026305a05db86a7a0303fc3db84bfa197142`).
  `private/test_runs/mesen2/wram_ownership_accepted_v2` and the independent
  `private/test_runs/mesen2/wram_ownership_replay_v2` both pass the strict
  eight-trace validator and are byte-identical across all 16 JSON/PNG files.
  Candidate and guards receive zero callbacks; Epoch, roster, and joined state
  receive no writes. This is the first ownership tranche only. Battle,
  save/load, New Game+, erase, reset, attract, shops, equipment, naming, and
  wider field/menu coverage remain required before `$7E2CA0-$2CEF` can be
  promoted.
- Added a separate menu-only ownership extension without modifying the
  accepted v1 collector. A deterministic builder requires the exact v1
  preimage and privately stages a derived 41,089-byte collector for Equipment
  owner switching, Tech owner switching, Item Use/Move, and Party Exchange.
  The generated source is deleted after every isolated launch.
- Accepted all four menu routes as exact zero/canary pairs. Equipment and Item
  each record 124 reads; Tech records 132 reads plus five writes; Party
  records 2,117 reads, including 2,065 roster reads. Candidate and both guards
  receive zero callbacks. Epoch, roster, and joined state receive no writes.
- Scoped the Tech writes to one exact frame-221 same-value sequence at
  `$7E2857-$285B`, from `$C2:82E7/$C2:82F3`. The validator pins sequence,
  frame, address, value, and PC and reconciles the old-block pre/post bytes, so
  any changing or additional write fails.
- Froze the 11,785-byte acceptance reference
  `references/mesen_wram_ownership_menu_accepted_artifacts_v2.json`
  (`c6978ec88c573dd4181e42d4645cbbd76b85612574cacfe4f8e0ef3d59bd2e04`).
  `private/test_runs/mesen2/wram_ownership_menu_v2_accepted_v2` and
  `private/test_runs/mesen2/wram_ownership_menu_v2_replay_v2` are
  byte-identical across all 16 JSON/PNG artifacts.
- Kept the evidence claim narrow. The schedules contain no final item-use,
  equipment-change, party-swap, or save confirmation, and roster/joined writes
  are directly absent. Inventory and equipment arrays are not watched, so the
  endpoints are route witnesses rather than byte-level mutation proof. Full
  leave-page flows, battle, persistence, reset, attract, shops, naming, and
  wider coverage remain open.
- Consolidated verification at 556 passing tests; all 65 source-controlled
  Python tools parse.

### 2026-07-26

- Added a source-confirmed RetroArch BSV2 parser/editor that mutates only an
  existing exact Player-1 event value and fails closed on missing, duplicate,
  nonzero, truncated, or structurally inconsistent data.
- Reproduced Continue, slot-1 load, and field initialization on current bsnes;
  converted the exit RASTATE into a raw field checkpoint and replayed it for
  600 frames.
- Anchored current-core WRAM at state offset `$2284`, injected the exact
  `$7E2CA0-$2CEF` canary, and preserved it once through field idle and native
  menu entry with four-byte front and sixteen-byte rear zero guards.
- Fired an isolated Player-1 soft reset on the current core. The pendulum intro
  rendered and the candidate block cleared to all zero, proving the future
  Project Epoch reset initializer is mandatory.
- Documented current bsnes's core-managed same-stem SRAM behavior and made
  isolated disposable ROM/SRAM fixtures mandatory; frontend `nosave` is not a
  write barrier for this core.
- Preserved the original 82-artifact recursive manifest as historical only,
  then added a fail-closed, source-controlled acceptance spec and a curated
  40-artifact manifest so exploratory replays cannot be promoted implicitly.
- Entered the Equipment page on current bsnes, rendered Crono, switched to
  Marle with a tagged Player-1 Down event, and preserved the exact canary and
  guards throughout.
- Added a BSV2 content-CRC-only rebind and ran matched current-core 4 MiB and
  inert 8 MiB ExHiROM controls. Field, menu, Equipment/Marle selection, and
  the complete 3,599-frame field replay produced byte-identical raw core
  states and pixel-identical screenshots.
- Installed RetroArch 1.22.2 and the current bsnes core side-by-side, pinned
  their download and executable hashes, and passed 120-frame clean-ROM and
  diagnostic-ROM smoke tests. Future runtime approvals use this baseline.
- Corrected the legacy BSV model to one byte per callback and 24 callbacks
  per dual-port auto-joypad latch. The former 12-position tests covered six
  even-numbered controls on each port, not twelve player-1 controls.
- Calibrated the vanilla soft-reset effect: candidate WRAM clears while the
  complete SRAM image and sidecar-gap canary remain exact. The replay pressed
  the chord on both ports, so it is retained as calibration evidence and the
  Project Epoch reset/initialization gate remains open.
- Corrected the compatibility-block structural front guard to four bytes
  (`$2C9C-$2C9F`); `$2C98-$2C9B` can be touched by the PC7-aware battle-exit
  formula.
- Added a deterministic state inspector that verifies the SRAM gap canary,
  the complete SRAM image, the vanilla save region, and global metadata
  against a BSV's embedded baseline.
- Verified the canonical playable-record schema with 13 focused checks,
  corrected the attract/demo source to three pointers plus three seven-row
  HP/MP blocks, and kept record `+$01/+$02` unknown bits gated.
- Built the private supported-Lucca-slot Schala diagnostic and rejected the
  first inherited-state checkpoint when its clean rebound was pixel-identical.
- Replayed Continue, slot-1 load, field initialization, and calibrated movement
  from a ROM-identity-matched movie. The accepted 3,000-frame run renders
  Schala's original cardinal packet beside Crono and Marle; the clean control
  renders Lucca. This is supported-slot evidence, not PC `$07`.
- Extended the BSV input editor to preserve existing inputs while adding only
  non-overlapping calibrated pulses.
- Audited all five field palette reload paths and ten `$18`-byte shadow-copy
  sites. Defined the uninstalled `$FFFF` source-key resolver that preserves
  vanilla colors 1-12 and supplies Schala colors 1-15 from named expanded
  storage.
- Entered the native Equipment page with calibrated Confirm, rendered its
  equipment/stat data for 600 frames, and preserved the exact
  `$7E2CA0-$2CEF` canary plus both zero guards.
- Validated and isolated a checksum-correct pre-Magus SRAM, traced both North
  Cape choices, and captured a normal Frog-versus-Magus battle through
  600 zero-input frames.
- Proved the vanilla full-party reference registers Magus in reserve and sets
  joined mask `$FC->$FE` before name acceptance, then opens native party
  exchange and can move Magus into the active formation. The exact canary,
  guards, Epoch name, and source/disposable SRAM hashes remain unchanged.
- Validated the recovered Lavos save as a true pre-encounter checkpoint:
  a normal current-core walk changes location `$01DA->$01DB`, bounded dialogue
  reaches the native Lavos battle menu, and the canary, guards, Epoch name,
  clean ROM, and source/disposable SRAM bytes remain exact.
- Calibrated all twelve Player-1 buttons independently at the native
  Frog-versus-Magus command menu. Y moves the window, Start pauses, Up/Down
  navigate to Item/Tech, and A begins attack flow; seven bounded inert
  endpoints match the zero-input control. All twelve preserve the canary,
  guards, Epoch name, clean ROM, and isolated SRAM.
- Promoted only the five meaningful battle runs, increasing the fail-closed
  accepted artifact set from 40 to 60 entries.
- Opened Frog's native Tech submenu without selecting a tech. The 1,200-frame
  A-only probe correctly stops at target choice with Magus at `6666/6666`;
  a released second A completes the normal attack and lowers Magus to
  `6137/6666` while a matched 1,500-frame control remains `6666/6666`.
- Selected Heal, confirmed Frog after four released frames, spent 2 MP,
  restored `837/999` HP to `999/999`, and returned to the stable command menu
  against a matched Tech-open no-cast control. This proves one vanilla
  self-target tech cycle, not Schala or other target/effect classes.
- Performed a real disposable slot-1 overwrite and fresh-process reload.
  Save #63 validates at `$FAF7`; `$0430-$047F` reloads byte-exactly to
  `$7E2830-$287F`; Epoch and the guards remain exact; vanilla reload leaves
  `$7E2CA0-$2CEF` all zero. With the bounded normal-attack and Heal proofs, the
  accepted set reached 88 artifacts.
- Recorded a fresh current-bsnes initial state containing one valid slot-1 v1
  sidecar, proved exact preservation after 3,599 idle frames, then loaded Save
  #63 in a fresh process while the complete SRAM, sidecar, Epoch name,
  `$0430-$047F`, all three vanilla slots, and metadata remained exact. Seven
  supporting artifacts raise the accepted set to 95. This is a vanilla
  compatibility/cold-load control, not a Project Epoch hook or storage
  approval.
- Added a host-tested, runtime-unverified recruitment transaction contract.
  It separates the persisted sidecar, reversible reserve staging,
  caller-witnessed complete-grant commit, and later exact-slot checksum
  binding; preserves all protected name buffers; refuses full-party
  displacement; and rejects forged fields, subclasses, and serialized-slot
  roster disagreement. Eighteen focused tests use only a synthetic,
  non-installable PC `$07` record fixture.
- Restricted those record tokens to an immutable registered gate/hash catalog
  and included their deterministic identity seal in every later derivation.
- Added a source-only sidecar load planner with mandatory source/slot-bound
  preclear assertions, fail-closed safe-empty classifications, protected
  compatibility/Epoch hashes, and exact re-derivation. Twenty focused tests
  include the deliberate counterexample proving v1's 16-bit checksum does not
  establish cross-slot provenance.
- Froze the exact `$A0` v2 format with physical slot/profile bytes and a full
  exact-`$A00` SHA-256 binding. Seventeen codec tests cover collision,
  migration, corruption, and New Game+ value boundaries.
- Added the source-only lifecycle executor with registered identity and
  preclear gates, invalid-vanilla no-read/no-copy behavior, raw-roster
  SafeEmpty normalization, all-three-slot save/erase isolation, staged New
  Game+, exact preview tokens, and save/erase failure injection. Twelve
  focused tests pass in either dependency-import order.
- Consolidated verification at 357 passing tests; all 45 Python tools parse.

### 2026-07-25

- Recovered the prior eighth-character conversation and local artifacts.
- Reproduced diagnostic v0.
- Completed deterministic static and quarantined-runtime v1 builders.
- Added automated builder, BSV-editing, BSV-inspection, SRAM/WRAM canaries,
  checksummed-sidecar, command/save/ROM-layout, state comparison, original
  content, event-audit, portrait, and gameplay-art checks; 148 tests pass and
  all 22 Python tools syntax-compile.
- Verified the supported-slot portrait, field render, and field movement.
- Proved the provisional runtime record-copy shim ineffective at the recorded
  checkpoint.
- Selected Schala as the production eighth-character target.
- Wrote the initial Schala character/content specification.
- Authored Schala's independent level policy, base stats, HP/MP and stat
  growth, TP cadence, and original starting loadout; froze a deterministic
  `$48`-byte progression overlay without claiming a vanilla record or runtime
  binding.
- Generated and pinned an original playable visual concept reference.
- Wrote the native-grid sprite/portrait asset specification.
- Authored and deterministically packed the first original target-grid
  gameplay foundation: four field idles, a three-key walk cycle, battle
  ready, cast gather, and cast release. It remains a partial source set with
  no ROM integration claim.
- Compiled all ten current frames into a deterministic 81-tile raw graphics
  packet and ten `$28`-byte four-object assembly records; serialized packet
  reconstruction is exact, while the complete sheet, animation blobs,
  allocation, hooks, and runtime evidence remain gated.
- Audited all seven vanilla PC graphics, assembly, descriptor, and animation
  envelopes without exporting source bytes: exact raw windows total 7,264
  tiles; size-class-0 frames use four objects and sixteen tile words; the
  unchanged animation/frame format tops out at 255 records (`$27D8` bytes).
  Six derived assembly ends match the next packet pointer, while Robo's tail
  remains explicitly unclassified.
- Corrected the asset specification to require two original portrait assets:
  a 48×48 (`$480`-byte) full menu face and a separate 32×32 (`$200`-byte)
  save preview.
- Implemented an inert, in-memory 8 MiB fast-ExHiROM scaffold with a required
  bank `$40` mirror, explicit `$41-$7D` allocation pool, dual-header checksum,
  and deterministic allocation validation; no PC `$07` hook is installed.
- Replayed full-menu, post-swap party-exchange, and native-battle canary
  checkpoints for 3,600 frames on the inert ExHiROM mapping; each complete
  state payload and all WRAM match a repeated 4 MiB control apart from ROM
  identity.
- Replayed recorded Continue inputs and vanilla full loads for all three save
  slots on the inert mapping with payload-exact 4 MiB controls; the candidate
  WRAM block follows the expected cold-clear negative control.
- Calibrated the six even-numbered player-1 battle controls plus the
  corresponding player-2 controls in the legacy stream; six changed native
  battle state and Confirm advanced the menu state. At that 2026-07-25
  checkpoint, the remaining player-1 controls, attack/queue/damage, and exit
  were still unproved. Every run preserved the relocation canary.
- Pinned the matching CC0 static reconstruction at commit
  `eeae27acdb6565e96d1d796a3d60792c250c0aa1`.
- Proved the runtime shim overwrites enemy-reward records and its hook site is
  field graphics setup; retired it as known unsafe.
- Reconstructed the eight-region save serializer, `$A00` checksum boundary,
  new-game record seed, PC-name/Epoch collision, joined bit table, ID `$07`
  equipment bit, and battle-record commit collision.
- Completed static PC `$07` graphics/menu and character/tech/equipment
  surface audits, including the occupied `$E4` entries, overworld and menu
  scratch collisions, full 36-tile portrait path, growth tables, equipment
  bit `$01`, and fixed multi-tech group shapes.
- Proved the vanilla low command namespace has only four unused IDs while
  Schala's launch set requires 17; selected raw `$80-$90` identities after
  proving the existing descriptor and battle queue preserve them unchanged.
- Audited every canonical location-event pointer and valid script for item
  references, upgrading `$E8-$EE` to statically unclaimed by location events
  while retaining null bindings and the remaining adapter gates.
- Added an original 28-node recruitment graph with 11 dialogue nodes, 29 null
  engine dependencies, and seven executed acceptance scenarios covering
  Magus, party-capacity, decline, repeat, and New Game+ branches.
- Audited all 29 recruitment dependencies against the canonical engine while
  installing none; proved the full-party displacement hazard, the PC `$07`
  collision with Epoch naming, and the loader-level New Game+ adapter point.
- Selected relocation of the full `$7E2830-$287F` compatibility block to
  candidate `$7E2CA0-$2CEF` plus a natural `$7E2830` Schala record; pinned
  the ten-descriptor save translation that preserves slot `$0430-$047F`.
- Proved the `$2CA0` canary is correctly cleared during cold initialization,
  then survives loaded-field idle, calibrated menu entry, cursor movement,
  page entry, cancel, overlay exit, full-menu idle, a native party swap, and
  native-battle idle; interactive battle commands, translated save, and New
  Game+ coverage are still required.
- Proved with a deterministic canary that the SRAM
  `$30:7E00-$30:7FDF` sidecar candidate survives boot and Continue/slot-1
  load without changing the vanilla slots or global metadata; no separate
  vanilla copy path exists, while erase and in-game-save gates remain.
- Added a fail-closed ROM write-intent and complete-diff guard. Canonical
  production bytes are default-deny; trusted production allocations and hooks
  remain empty; known Epoch, NPC, shared-selector, reward-table, mirror, and
  noncanonical ranges are hard protected.
- Integrated the guard into both current diagnostic builders. The private
  Schala-over-Lucca smoke and static Lucca-to-Magus clone account for every
  changed byte and pass only as nonproduction diagnostics. The retired runtime
  clone receives the required explicit rejection for its occupied
  `EnemyRewardTable` overlap.
- Made the retired unsafe emulator variant explicit opt-in, prevented the
  Schala smoke from aliasing its clean input path, and made it refuse to
  replace a different existing ROM.
- Created this living developer guide.
