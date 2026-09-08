# Project Epoch Agent Rules

## Absolute invariants

- Do not include or commit ROM files, patched ROM files, save files, or extracted copyrighted game data.
- Keep clean ROMs, generated SRMs, emulator states, and raw traces under ignored local-only directories.
- Generated IPS/BPS patches are allowed only when a source builder reproduces them deterministically.
- Every generated artifact must include hashes, reproduction steps, and an evidence level.
- Preserve recovered artifacts unchanged under `recovered/`.
- Every same-size ROM mutation or patch builder must run the fail-closed intent
  and complete-diff audit in `tools/validate_rom_write_intents.py` before
  writing an image or emitting a patch. Safe modes must pass. A preserved
  retired-unsafe reproduction may continue only when the guard returns its
  expected explicit rejection; it must remain opt-in, quarantined, and
  forbidden as a production input. The size-changing inert ExHiROM scaffold is
  the sole structural exception and must pass
  `schala_rom_scaffold.validate_exhirom_scaffold` with exact source/mirror/
  header/fill invariants.
- Canonical ROM bytes are production-default-deny. Production payloads belong
  only in source-controlled named expanded allocations; vanilla instruction
  hooks require exact approved spans and pinned preimages. The trusted
  production hook and allocation catalogs remain empty until evidence is
  explicitly promoted.
- A separate original-cartridge diagnostic contract accepts only the pinned
  eight-MiB literal all-`$FF` source, a private-only schema, and seven fixed
  original diagnostic sections. Its two explicit APIs in the write guard
  perform intent and complete-diff audits before image emission. It changes
  no legacy source kind, production catalog or game ownership. The original
  package test cartridge has two identical guarded builds; this is static
  construction evidence, separate from all native execution claims.

## Namespace doctrine

These are separate namespaces. Never conflate them.

### Logical playable PC ID

- `$00-$06`: vanilla playable PCs.
- `$07`: Project Epoch candidate eighth playable identity; undefined as a complete PC in vanilla.
- `$80`: empty party slot in save-editor tooling.

### Save/editor record index

- Records `$00-$06`: vanilla playable PCs.
- Record `$07`, slot-relative `$0430`: not a valid PC record. Save editors may
  display it as Epoch, but `$0430-$0436` are the seven PC tech-progress bytes
  and `$0437-$043D` are learned-tech masks. The remainder is not fully mapped;
  preserve the whole region.
- Slot-relative `$0480`: not an approved Project Epoch record. It lies inside
  the vanilla save serializer's first `$05B0`-byte region, and the checksum
  covers the whole `$A00` slot. The bounded global SRAM gap
  `$30:7E00-$30:7FDF` is the preferred versioned-sidecar candidate, pending
  save/load/NG+/erase proof; expanded SRAM is the fallback.
- Candidate v1 sidecars never populate live state through the production-facing
  load planner. Even a structurally valid v1 record is
  `legacy-v1-migration-required` safe-empty because its 16-bit checksum cannot
  prove slot provenance. Keep all v1 reserved bytes zero. Offline migration
  requires an explicit full-SRAM/source-slot-bound caller provenance assertion;
  it is never automatic and cannot make a false assertion trustworthy.
- Candidate v2 keeps the exact `$A0` size and gameplay offsets, assigns physical
  slot ID/profile to `$0E/$0F`, and stores a full SHA-256 binding at `$80-$9F`.
  Profile 1 hashes the exact full `$A00` vanilla slot plus the 16-byte
  `PE07BIND` version/profile/slot/length trailer. The legacy checksum remains a
  preflight only. Unknown versions/profiles, invalid CRC or fields, checksum,
  physical-slot, or digest mismatch are safe-empty.
- A relocatable correctness-first 65C816 profile-1 SHA implementation now
  matches all three physical-slot vectors in a standalone current-bsnes
  benchmark while preserving `A/X/Y/P/DBR/D/SP`, scratch guards, invalid-output
  refusal, and the benchmark's minimal NMI counter. It takes 366-367 frames
  (about 6.1 seconds) per digest. A separate fixed-rotate candidate passes the
  same two-run evidence at 123-124 frames (about 2.05 seconds), an
  approximately threefold improvement that still fails synchronous production
  timing. Its baseline and current-source manifests are independent; the
  source-drifted intermediate manifest is rejected. The bounded
  eight-round-unrolled core with exactly `$4000` bytes of generated,
  exhaustively verified sigma tables also passes twice, at 68-69 frames
  (about 1.14 seconds). That exceeds its predeclared 30-frame stop gate, so no
  synchronous or cooperative game integration is allowed. The next step is an
  explicit choice between a deliberately longer profile-`$01` transition and
  a separately numbered/proved integrity-only profile. The benchmark's
  `$7E4000` scratch and `$41/$42` code/data are synthetic diagnostic
  addresses, not approved Project Epoch allocations. The standalone all-`$FF`
  complete-diff builder is not an exception to or approval from the
  canonical-ROM write guard. No game hook, SRAM ownership, real interrupt
  policy, or production SHA placement is approved.
- The source load planner's preclear witness is only a caller assertion bound
  to one full SRAM image and slot; it is not runtime proof that live PC `$07`
  was cleared. Full load restores roster/joined bytes after preclear, so every
  safe-empty result after a valid vanilla copy must also replace exact roster
  ID `$07` with `$87` and clear joined bit `$01` before party consumers. If
  vanilla validation fails, abort before copy and expose no party-write target.
  A valid v2 result may publish only when its quest state agrees with an
  in-namespace, duplicate-free serialized PC `$07` roster/joined state.
- Normal save must invalidate the selected sidecar first, let vanilla finish
  the complete `$A00` slot plus metadata, then bind/write v2 and commit its
  magic last. New Game+ at `$FF:FB3B` may stage retain/reset live state only;
  no new vanilla slot exists there, so v2 rebinding waits for the first later
  normal save. Erase must invalidate exactly one selected `$A0` record.
- The host lifecycle executor proves source ordering only. Invalid vanilla
  aborts before any sidecar read or party target; SafeEmpty after a valid copy
  sanitizes exact `$07` even beside otherwise malformed roster bytes. Erase
  must break sidecar byte `$00` before clearing `$01-$9F`, and native magic
  invalidation comes last. Do not promote these host results to runtime
  evidence.

### Graphics source index

- `$00-$06`: vanilla playable-character sources.
- Low indices beyond `$06` are occupied by existing engine actors or vehicles unless tracing proves otherwise.
- Never treat a zero-filled ROM region or table entry as free space without provenance or runtime evidence.

### Runtime record and command candidates

- Preferred live record architecture is natural PC `$07` at
  `$7E2830-$7E287F`, after relocating the complete vanilla compatibility block
  to candidate `$7E2CA0-$7E2CEF`.
- `$7E2CA0-$7E2CEF` is not yet declared free. It has static bounds and
  loaded-field/menu-entry canary evidence, but the remaining menu, battle,
  save, New Game+, attract, and reset matrix is mandatory.
- Proposed Schala action IDs are `$80-$90`; `$7C-$7F` remain untouched and
  `$F0-$FF` remain the battle marker family.
- High action IDs are safe only through the proved descriptor/queue transport.
  Every signed check and direct table index listed in
  `docs/schala_command_namespace_architecture.md` must be adapted.
- Candidate Project Epoch player-Tech package selectors `$80-$8F` are a
  separate, explicitly unbound policy namespace. Numeric equality with
  Schala action IDs creates no mapping; an extended action-config record must
  bind config byte 0 deliberately.
- The source-only package-bank adapter v0 preserves the canonical `$00-$7F`
  resolver path and host-models both `$A0B3` branches, all 16 owner bits,
  exact word-write footprints, and bank-qualified direct entries. It approves
  no hook or allocation. Command `$1E` still forces nested scripts into bank
  `$CE`, and config bytes `+3/+4/+5` retain independent fixed-bank auxiliary
  readers. The native `$1E/$1F` handler semantics are already decoded; do not
  repeat that work. The general lossless command grammar/canonical stream
  census is now complete-static across 2,173 direct and 59 fixed-`$CE` nested
  entrypoints. Its reviewer-encoded width interpretation is pinned to the
  canonical handler corpus; its hashes do not auto-derive semantics. All
  nested forced-fallthrough traces reach `$1F`, but 24 contain conditional
  return `$21`, and one exact four-byte descriptor/stream dual use is occupied,
  not free space. The final v0 expanded-package decision is strict decoded
  `$1E` exclusion for flat direct streams. Raw byte scans are never authority:
  an operand may equal `$1E`. Every future authored package must pass both
  descriptor masks, all suffix/shared entrypoints, exact disjoint named spans,
  complete token ownership, and terminal `$00` under the interpreter-pinned
  validator. The adapter's cross-bank `$1E` refusal remains intact, and
  auxiliary fixed-bank readers remain separate gates. The canonical four-byte
  descriptor/stream dual use remains occupied canonical data; newly authored
  Epoch descriptor/stream overlap is forbidden. No production selector is bound.
- `BA-SYMBOLIC-HIGH-PACKAGE` now has one source-only, terminal-only test
  package under an explicit local selector-`$80` mapping. Its synthetic bank
  `$42` descriptor/stream spans are test identities, not allocations. It
  reconstructs canonical action-config row `$01`, replaces only byte `+0`,
  and proves `+1..+6` equality; that donor does not assign Schala effect
  semantics. Both masks preserve the repeated direct pointer across all 256
  `$A0B3` values in the host model. All 128 canonical selectors remain
  equivalent and all 16 default high selectors remain unbound. This proves
  no native helper, animation, action binding, hook, or logical PC `$07`.
- The original 537-byte package helper now passes `BA-NATIVE-HELPER-CONFORMANCE`
  at `verified-runtime`, strictly synthetic scope. Three full Mesen runs pass
  879 cases each: two at `$7F8000` have identical traces; one at `$7F9000`
  proves that second placement. The v0 helper accepts only diagnostic WRAM
  source banks `$7E/$7F`, and its registry, scratch, stack, and tails are
  synthetic fixtures, not game ownership. Final CPU state, exact ordered
  publications, complete WRAM diffs, and unchanged input hashes pass. This
  does not prove expanded-ROM access, an actual resolver hook, game interrupts,
  command execution, or PC `$07`. Keep production selectors unbound. Resume
  at `BA-NATIVE-INTEGRATION-DESIGN`; do not repeat the completed synthetic
  proof without source drift or a new failing boundary.
- The clean-ROM primary resolver observation now repeats identically in two
  isolated Mesen runs: one ordinary PC type-2 invocation, config/selector
  `$08`, branch `$0000`, entry SP `$06D8`, return words `$432A/$40AF`, eighteen
  exact ordered publication bytes, and paired action-completion latch reads.
  This is checkpoint-bounded vanilla runtime evidence, not high-selector
  integration or alternate-branch proof. Preserve the completed observation.
  The separate canonical alternate observation also repeats identically from
  the pinned imported-save Spekkio checkpoint: Magus Black Hole selector `$37`,
  actual `$AE94=$40` write/readback, branch `$0040`, 42 ordered publications,
  and completion within that action. This is a normally completed immune-target
  action, not transaction cancellation. Documentary screenshots differ while
  the 3,783-record CPU/data-flow traces match; preserve that distinction.
  Integration design must separately establish cancellation, expanded-ROM
  reads, and scratch/interrupt ownership. Synthetic `$7E4000` has a proved
  vanilla menu/overworld collision and must not be adopted as game scratch.
  The terminal-only symbolic stream does not by itself complete an action;
  the caller also waits on `$9876` and `$5D9B`. See the developer log and
  `docs/DATA_MAPPING_CORRECTIONS.md` before adopting an old annotation.
- The separately versioned 676-byte ROM-source helper now passes two identical
  1,454-case synthetic Mesen runs using actual CPU reads from banks `$41/$42`
  of the unchanged original SHA benchmark. Both masks and every direct target
  are preflighted before publication. Complete observed helper PC sequences,
  ordered reads/writes, final CPU state, full WRAM diffs, and unchanged input
  snapshots pass. Those descriptor-shaped original bytes are not certified
  battle streams. The helper still executes in synthetic WRAM and uses the
  known-unsuitable `$7E4000` scratch fixture; no ROM code placement, immutable
  production registry, game hook, interrupt ownership, or selector is approved.
  Preserve v0 and v1; the separate v2 stack-frame design is the next temporary
  storage architecture, not an approved game-stack allocation.
- The separately versioned 577-byte stack helper now passes two identical
  2,980-case normal synthetic Mesen runs. Its 42 locals are S-relative, with
  eight saved context bytes and 52-byte deepest helper contribution. Final
  values are staged before releasing locals. Every stack access owns an
  observed instruction, required post-SP-change observations are complete,
  and every final WRAM difference matches its last observed CPU write and
  exact setup baseline. Retired `$7E4000-$7E4080` remains unchanged. The five
  tested entry SPs include exact helper-only floor/refusal boundaries, which
  have no interrupt reserve. Preserve this normal-only v2 proof; it approves
  neither game stack ownership nor interrupt safety. See the v2 report.
- The original package cartridge separately assembles that unchanged include
  in ROM at `$410000` with immutable registry `$430000` and target lists
  `$430100`. Four certified terminal-only test bindings `$80-$83` and twelve
  unbound rows remain diagnostic identities. The separate v3 now passes two
  identical 3,184-case normal Mesen runs: actual helper execution at `$410000`,
  ordered descriptor/registry CPU reads from `$42/$43`, unchanged immutable
  inputs, complete WRAM write/diff reconciliation and stack liveness. Preserve
  v0/v1/v2 and this v3 proof; none approves a game allocation or interrupt
  policy. Pointed terminal streams are certified but not executed. The source-
  pinned Mesen NMI request design uses a real `$4200` enable edge at natural
  VBlank; it is a debugger register event, not a CPU store or fabricated frame.
  Its original Lua inventory incorrectly required `ppu.nmiScanline`, which
  Mesen explicitly excludes from Map serialization. Follow the numbered v2
  phase contract: observe the natural latch transition and the next public
  scanline. MAP-010 pins our incorrect published claim, contrary source, and
  failed preparation pilot. Preserve the historical v1 auditor/reference.
  Preserve these distinctions and the existing production-default unbound set.
- A separate repeated clean-ROM context observation records 2,402 paired
  interrupt entries/pre-RTI snapshots per run and one PC-scoped NMI scene
  clear with an actual write and later readback. No interrupt enters its short
  canonical resolver interval of 4,244 master clocks / 548 CPU-cycle-counter
  increments. The recorded minimum handler SP `$06A2` is sampled, not the
  whole stack floor. Use the full serialized `memoryManager.masterClock`;
  Mesen's generic `masterClock` is only its low 32 bits. Saved IRQ I=0 is an
  observation, not a universal precondition: a previously sampled IRQ can
  remain pending across SEI. This proves no helper preemption behavior.
- A late resolver refusal is not queued-Tech cancellation: the vanilla path
  prepares effects and charges participant MP before animation, then applies
  pending results after normal animation return. The candidate preflight is
  before `$C1:BBD4`; reusing `$C1:BC5A` still requires valid participant,
  queue, finalizer-table, CPU, and stack context. `$C1:BDB3` is shared by
  successful and failed Tech paths, not a cancellation/refund API.
  A repeated successful canonical transaction now observes the candidate
  pre-effect boundary, three MP calls with only participant 0 charged 20,
  eleven first HP stores/readbacks, shared finalizer, queue release and actual
  caller. Its ledger covers declared watched ranges only, not full WRAM;
  later HP clamps and snapshot-only target clearing retain their limits.
  A separate repeated natural Cure refusal now verifies that a living queued
  target can die before resolution: actual death/clamp, `$AF23=1`, unchanged
  HP/MP during refusal, exact 22 watched cleanup writes, actual caller return
  and later actor readiness. This is a vanilla failure lifecycle, not a new
  cancellation adapter. It exits before the successful route's AE/mask setup;
  cleanup from a new rejection at `$C1:BBD4` remains unproved. At the earlier
  `$C1:BB8B` failure boundary, AE fields still belong to previous work.
- The normal-NMI busy-flag fast path is statically proved for all four native
  M/X combinations with 13 bytes including its hardware frame. The separate
  ten-region census retains 44 opaque callee frontiers and explicit conditional
  return contracts. Full normal-NMI and global nested-interrupt bounds remain
  null. The conditional 40-byte route is not a universal bound; leading/trailing
  zero-busy windows, callee closure, DMA aliases, alternate NMI and game stack
  headroom remain unresolved. See `docs/schala_package_normal_nmi_v1.md`.
- The bounded direct battle-IRQ CPU closure now covers 401 instruction starts
  in 404 width contexts, with balanced near/long calls and 35 bytes maximum
  stack use including the native four-byte hardware frame. NMI nesting,
  data-dependent DMA sources, the complete NMI tree, and global stack
  headroom remain unproved. The two apparent `$AAEB` writes in the old
  `$FD:E21B/$FD:E247` annotations are 16-bit immediate operands, not writes.
- Proposed Schala item IDs are `$E8-$EE`, with `$EF-$F1` reserved. They are
  `verified-static` as unclaimed by canonical US Rev0 location events after
  all 513 pointer entries and every valid referenced script were audited.
  This is not proof that the IDs are globally free; do not install their
  records until the remaining item adapters and runtime matrix pass.
  `$F2+` is rejected by the vanilla sanitizer, and `$F0-$FF` also overlaps the
  battle marker family.
- The allocation-neutral Schala item overlay uses seven `$20`-byte v1
  descriptors (`$E0` bytes total). Its description and visual pointers remain
  zero/unbound; the table is not ROM-installable until named expanded
  allocations and every classification adapter exist.
- The Schala progression overlay is an original `$48`-byte Project Epoch
  descriptor, not a vanilla `$50`-byte character record. Its learned-single
  mask is high-bit-first (`$E0` for the three recruitment techs). Do not emit
  a full record or install the overlay until record bytes `$01/$02`,
  experience/current-stat initialization, growth/TP readers, equipment null
  translation, save/load, and balance replays are resolved.
- Vanilla has exactly seven `$50` initialization records. The normal `$280`
  seed is seven records plus the `$50` compatibility span, while the
  attract/demo path loops over eight destinations using only seven HP/MP
  source rows. Record `+$01` low flags and `+$02` bits other than `$01/$10`
  remain unmapped; do not copy Magus's `$42/$80` seeds into Schala.
- Schala's growth/progression arrays use the runtime-confirmed order Power,
  Stamina, Speed, Hit, Evade, Magic, Magic Defense. Vanilla base/live record
  stats instead use Power, Stamina, Speed, Magic, Hit, Evade, Magic Defense.
  Keep these schemas separate; the older disassembly's Magic-before-Hit
  growth-table label is misleading, but that order is correct for base/live
  record fields. See the corrected character data map.
- The ten current original gameplay frames compile into ten native-shaped
  `$28`-byte records and an 81-tile packet with exact host reconstruction.
  This is a partial packet foundation only: do not claim a complete animation
  blob, production ROM allocation, expanded-bank read, battle sprite, or PC
  `$07` runtime sprite from it. A private supported-Lucca-slot replay verifies
  only the first four cardinal records after Continue/load and field movement.
  Vanilla field loading copies only twelve character-specific colors;
  Schala's indices 13-15 require the audited but still uninstalled `$FFFF`
  full-palette adapter.
- The first-pass private visual provider now derives the canonical Schala NPC
  family from the user's pinned clean ROM at build time. It has 23 exact
  `$28`-byte records, 79 fully referenced tiles, four aligned 36-byte primary
  animation blocks, and the native twelve-color palette. Extracted bytes stay
  ignored under `private/`; only metadata and hashes may be source-controlled.
  Two fresh current-bsnes diagnostic runs and two matched clean controls now
  verify this provider through Lucca's supported field path across bounded
  four-direction and run movement, with deterministic endpoint frames/states
  and intact compatibility canary, guards, roster, joined mask, and Epoch
  name. This is still supported-slot compatibility evidence, not reusable art,
  a complete PC packet, a production allocation, or logical PC `$07`
  evidence. It must leave NPC `$09`, entries `$07/$08`, `$E4:F023`, and all
  Epoch data unchanged. The original Project Epoch art remains preserved as
  deferred replacement-art research pending a deliberate Chrono Trigger-style
  redraw.
- An independent additive audit now proves that those ten frames plus the six
  existing Glass Focus body poses fit one 16-record, 91-tile native-shaped
  partial packet with exact reconstruction, while preserving the complete
  ten-frame graphics and assembly streams as prefixes. The ordinals are
  provisional source order, not engine animation IDs. It adds no Focus
  inserts, audio, animation pointers, allocation, action/item binding,
  runtime sprite, or PC `$07` claim.
- The canonical animation semantic contract is now mapped far enough for
  source-role authoring, not installation. Engine facing values `$00-$03`
  have verified-static dispatch order; their documented names are
  up/down/left/right. The existing source-art order down/up/left/right is a
  separate namespace and must not be silently reordered. Entrypoint `N`
  begins at `N*4`, but four bytes is an entrypoint stride, not a fixed record
  length; overlapping/suffix sequences are valid only when shared primary and
  auxiliary tokens agree.
- `$E4:2800` is the auxiliary timing/control pointer table, not graphics. Each
  vanilla PC auxiliary contract is one primary-facing span. Magus is bounded
  only through `$E4:AFB4`; `$E4:AFB4-$E4:B5FF` remains unclassified and is not
  free space, while table entries at `$E4:B600` and `$E4:B614` prove occupied
  successor timing data. Do not infer visual semantics from a fixed numeric
  field/menu/battle anchor.
- A hardened tracked native-Mesen launcher/collector reproduces only the field
  relation between main-frame and timing streams: Magus/right-facing selector `$01`
  reads `$10-$15` with six `$07` delays and resets on timing zero before the
  following primary `$FF` is fetched. This is exploratory, checkpoint-bounded
  evidence, not a Schala, PC `$07`, expanded-bank, allocation, or save-safety
  proof. The tracked code contains no raw trace or game artifact. Raw traces,
  ROM/SRAM/state files, screenshots, and emulator binaries remain ignored and
  must never enter source control.
- The canonical location-event animation census now inventories all 10,637
  encoded `$AA/$AB/$AC/$AE/$B3/$B4/$B7` sites and the complete 116,064-entry
  direct-function topology. Because 2,269 function entries leave their nominal
  physical owner, identity context uses an incoming direct-entry marker
  closure. Its 927 PC-only-marker, 23 mixed, and 1,794 no-PC-marker source
  owners are a syntax-only possible-context overapproximation. Calls, jumps,
  fallthrough, startup replay, loader lifetime, party state, and runtime
  reachability remain unresolved. `$87` is orthogonal, and generic `$80/$81`
  operands outside `$00-$06` are never promoted to a vanilla PC, Epoch, or
  Schala by the auditor.
- Recruitment party operation 1 is not a capacity-safe append: with three
  active PCs it replaces slot 3 and moves the displaced PC to reserve. Require
  an explicit open-slot helper; use reserve registration on the full branch.
- Vanilla naming ID `$07` is the Epoch at `$7E2C4D`, and dialogue PC-name
  entry 7 is null. Schala requires independent live naming, entry, dialogue,
  save, and load adapters; never route her through the vanilla ID-7 name path.
- Apply Schala's retained/reset New Game+ sidecar policy at the partial loader
  before any recruitment-graph state test. It is not a location-event query.

## Retired mistakes

- Do not use active-party byte `$08` for Magus2/Gaspar.
- Do not overwrite graphics table entry `$07` or `$08` as architecture.
- Do not use file `$0D400E` as a free eighth-character attack byte; it is
  shared by PC `$07` normal-attack indexing and Crono critical-attack indexing.
- Do not rewrite `$07` to `$06` in WRAM as architecture.
- Do not treat duplicate Magus as Phase 1 success.
- Do not treat a booting ROM as proof that a hook site or zero run is safe.
- Do not claim save record `$0480` is safe because it is zero-filled in one save.
- Do not use `$CC:63F6-$CC:642F` as code space. Static reconstruction proves
  it is inside `EnemyRewardTable` (`$CC:5E00-$CC:64FF`).
- Do not treat a runtime-only WRAM edit as save-safe. The clone hook's
  `$7E2832/$7E2839` writes structurally map to slot `$0432/$0439`; use a
  disposable SRM and do not save.
- Do not extend a ROM action table in place across its documented end.
  `$80` aliases occupied target/animation data in several vanilla tables even
  though the queue transports the byte unchanged.
- Do not publish a valid v1 sidecar or infer its physical origin from the
  16-bit vanilla checksum.
- Do not treat a PC `$07` preclear before full load as sufficient. Vanilla load
  can restore exact `$07` roster bytes and joined bit `$01`; normalize or
  validate them after the copy and before party consumers.
- Do not rebind or write a New Game+ v2 sidecar at `$FF:FB3B`. That boundary is
  load-only; stage live retain/reset state and bind it after a later finalized
  normal save.
- Do not describe the unkeyed v2 SHA-256 as authentication or rollback
  protection. It is a collision-resistant exact-slot integrity binding.

## Current milestone

The supported seven-PC Magus-over-Lucca diagnostic has exposed the principal
character-data assumptions and its unsafe runtime shim is retired. A separate
private Schala-over-Lucca smoke verifies the partial original cardinal packet
without claiming PC `$07`. A second private supported-Lucca diagnostic now
verifies the canonical-ROM-derived Schala NPC-family provider with explicit
animation-entrypoint fallback and no source-controlled extracted bytes.
Current work remains the evidence-gated Schala PC `$07` foundation: finish the
remaining adapter/runtime matrix while keeping final replacement art original
and provenance-backed. The current 16 original body frames are packable but
remain natively unbound. The stream shape,
fixed-bank setup/reader sites, and minimum automatic/menu/battle anchors are
now mapped. The complete encoded location-event operand census and its direct-
entry topology are also mapped, but its inter-object control-flow and loader-
lifetime model remains unresolved. The battle action-package census and
source-only bank-qualified direct-entry adapter are now complete at the host
model level while every production high package binding remains absent.
`BA-SYMBOLIC-HIGH-PACKAGE` is complete as a source-only host proof, and
`BA-NATIVE-HELPER-CONFORMANCE` is complete in the isolated synthetic Mesen
matrix. The next gate is `BA-NATIVE-INTEGRATION-DESIGN`: exact live resolver
hook/continuation evidence, named expanded placement and source-bank access,
and scratch/interrupt ownership before installation.
The ordinary primary resolver and its completion latches now have a repeated
clean-ROM observation. A separate repeated Black Hole/Spekkio observation proves
the canonical alternate branch from its pinned imported-save checkpoint;
the high-selector integration and refusal lifecycle remain separate obligations.
The lossless battle-command
grammar/canonical stream census and strict flat-direct decoded-`$1E` exclusion
policy are complete at `verified-static`, reusing rather than repeating the
decoded native `$1E/$1F` handler semantics. Every default `$80-$8F` selector
remains unbound; high associations exist only inside the symbolic and native
synthetic proof fixtures. The stronger
location-event contextual model and complete source-role/facing inventory
remain explicit later gates. The original helper is authored and executed
only in synthetic WRAM; no production placement, hook, scratch ownership, or
game integration is approved.

The clone diagnostic must separately account for:

- field and battle sprite source tables;
- runtime character record;
- portrait tiles and palette;
- single-tech names, targeting, properties, MP costs, and animation/effect selectors;
- normal-attack selector;
- menu element icon;
- tech-learning state;
- save-select, menu, roster, field, and battle timing.

No production eighth-character patch is allowed until trace evidence identifies each subsystem's input ID, computed index or pointer, data source, and safe hook point.

## Evidence labels

- `verified-static`: proven directly from the canonical clean ROM or deterministic builder output.
- `verified-runtime`: reproduced in an emulator with recorded inputs and hashes.
- `documented`: supported by a cited technical source but not independently traced here.
- `hypothesis`: plausible and explicitly awaiting verification.
