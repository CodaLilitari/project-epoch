# Project Epoch SRAM sidecar audit

Status: candidate storage, not yet approved for production  
Last updated: 2026-07-26  
Target: Schala logical playable ID `$07`

## Outcome so far

The original 8 KB SRAM image contains a structurally bounded `$1E0`-byte
interval between the three vanilla save slots and the global save metadata:

```text
$30:6000-$30:69FF  vanilla slot 1 ($A00)
$30:6A00-$30:73FF  vanilla slot 2 ($A00)
$30:7400-$30:7DFF  vanilla slot 3 ($A00)
$30:7E00-$30:7FDF  sidecar candidate ($1E0)
$30:7FE0-$30:7FFF  vanilla global metadata ($20)
```

This is a substantially better candidate than slot-relative `$0480`, which is
inside each vanilla slot's serialized main region. The gap is still not
approved merely because a recovered SRAM fills it with `$FF`.

## Static evidence

`verified-static`

- `SaveSlotBases` at `$FF:FBE1` contains `$6000`, `$6A00`, and `$7400`.
- `SaveSlot_Checksum` covers exactly `$A00` bytes beginning at the selected
  slot base, so the three checksum ranges end at `$30:7DFF`.
- `SaveSlot_Write` at `$FF:F9FB` copies exactly eight five-byte region
  descriptors from `$FF:FA7B`, totaling `$834` bytes, then writes the vanilla
  slot checksum and magic. `SaveSlot_LoadRegions` at `$FF:FAA3` mirrors those
  eight descriptors. The descriptor table cannot simply grow in place
  because the loader begins immediately after it.
- `$FF:FAED` is a separate partial SRAM-to-WRAM loader, not another writer.
  It restores slot offset `$0000` to `$7E2400` for `$580` bytes and offset
  `$05B0` to `$7E2C23` for `$33` bytes, then reads additional carry-over
  state. Its caller at `$C2:E6D8` is the New Game+ slot path. It does not
  access the sidecar candidate.
- Direct SRAM references in the byte-matched reconstruction address the three
  slot bases or global metadata beginning at `$30:7FE0`; none directly name
  `$30:7E00-$30:7FDF`.
- Vanilla erase invalidates a slot by writing byte `slot*2` (`00/02/04`) to
  the selected magic low byte at `$30:7FF8 + slot*2`; it does not clear a full
  word or touch the candidate gap. A Project Epoch erase adapter is therefore
  mandatory.
- The complete pinned-source caller audit finds no separate slot-to-slot copy
  routine: one normal writer, one full loader, one New Game+ partial loader,
  and one erase path are the whole vanilla lifecycle surface found.
- The pinned recovered SRAM has all `$1E0` candidate bytes set to `$FF`, but
  that observation is supporting evidence only.

Indirect and computed access plus save/load/NG+/erase integration still
require proof before the range is promoted to production storage.

The minimum integration surface is therefore a fail-closed normal-save wrapper
that invalidates first and commits v2 only after vanilla serialization, a
translated full-load wrapper with post-copy roster handling, staged New Game+
handling at `$FF:FB3B` plus later normal-save binding, an explicit save-preview
resolver before PC `$07` indexes `$0430`/Epoch, and exact-slot invalidation in
erase. Expanding the vanilla descriptor table in place is not safe.

## Runtime canary

`verified-runtime` for boot and Continue/slot-1 load

`tools/inject_bsv_sram_gap_canary.py` replaces only SRAM file offsets
`$1E00-$1FDF` inside a disposable BSV's embedded state. Its deterministic
`$1E0`-byte canary has SHA-256:

`219051da0bd17ea7e24c9d260ed4d84ee8215ebdb71545fb25bb49b859eb7348`

### Boot-only run

- Source BSV SHA-256:
  `298500747628918c7ee69053a547e31c6a3d4103fbd9f4731f1ab8b29fc3806a`
- Canary BSV SHA-256:
  `777b397023ac6a77522911159caefcf7e3a01c3df71290da874304ae68ddb196`
- Exit state SHA-256:
  `15d3575621a973594401eb421a243e99c924fc71b697f79a1df2fca444d84891`

### Continue and slot-1 load

- Source BSV SHA-256:
  `bd478b28e28ca2a772614ac437fb15cbbe92adcf6f987ab065ed9f3ed515b596`
- Canary BSV SHA-256:
  `eb2ebf5ba908589210e45d7ba69cca0bbe95efa608423611fa1c6b83075cafc5`
- Exit state SHA-256:
  `5b8d35b883f794158113a7ffb5369b1a69f2f6ccd0cfeba0cbea121bce06bd9d`

In both exit states:

- the canary occurs exactly once at state offset `8280`;
- the containing SRAM begins at state offset `600`;
- SRAM `$0000-$1DFF` matches the recovered three vanilla slots byte-for-byte;
- SRAM `$1FE0-$1FFF` matches vanilla global metadata byte-for-byte.

The load-run state also contains the live Lucca/Magus record pair at offsets
`28995/29315`, the same `$140` delta observed at the loaded-field checkpoint.
This confirms that the canary survived the actual Continue/load path rather
than only an idle boot.

### Current-core normal save and fresh reload

`verified-runtime` for the native slot-1 boundary; no sidecar hook installed

An isolated current-bsnes replay overwrote slot 1 from Save #62 to Save #63.
Only nine SRAM bytes changed: six gameplay/time bytes, the save counter, and
the two-byte slot-1 checksum. Slot 1 validates at `$FAF7`; slots 2 and 3,
Epoch's name, and `$0430-$047F` remain exact. The bounded sidecar gap remains
all `$FF` before and after, with SHA-256
`bf9b62d4418d862aa0826a28a846948151da66b8042967382ca6bfd6d7d1cdb2`.

A fresh emulator process then loaded Save #63 into Lavos Tunnel `$01DA`.
Live `$7E2830-$287F` exactly equals saved slot-1 `$0430-$047F`; both hash to
`b70a2e5d291811c9f58689d7d0dbbfe89b913a3c0b1ef846de4607f0af6d9c73`.
The proposed relocation block `$7E2CA0-$7E2CEF` is all zero after the vanilla
reload. This closes the native normal-save/full-load negative control and
confirms that neither the candidate gap nor relocation block is implicitly
handled. It does not install or validate the future sidecar write/load hook.

### Current-core valid-sidecar compatibility and cold load

`verified-runtime` for vanilla boot, 3,599-frame idle, and Continue/slot-1 load

A deterministic Save #63 SRAM bearing one structurally valid v1 sidecar hashes
to
`668aed39e84b63bc5cd1a1d3d146623681e0a0b1e412bf99bf8427826aad3685`.
The slot-1 sidecar hashes to
`1e7e9fc1179bee9f04614e0eb1ccf60a65b6101dee4b9775d8db59fc5a193ce9`
and classifies `valid`, bound to vanilla checksum `$FAF7`; slots 2 and 3
sidecars remain all `$FF`.

The corrected zero-input current-bsnes recording
`cc437bc567da39e0719241f68dfbb698517074f44402e56577aa9bb9fa204557`
embeds that exact SRAM once. Its 3,599-frame exit RASTATE
`670b1f4ba2299e1e8a94c59afdd518ba04c07847c4e323b7d5d0d65189637d76`
still contains the exact full SRAM once and the exact sidecar once. The
same-stem disk SRAM is byte-identical before and after.

A second movie, differing only by the intended Continue/slot-1 input values,
hashes to
`433a534cf76ffe3e7a8eee7617f89227754a5daeb9d7fd25550a2f2bba175ed6`.
It reaches Lavos Tunnel `$01DA`, storyline `$D6`, Save #63, and party
`00 01 02`. Exit RASTATE
`356949e724481d7fd86d90e1da48c633a3b881d269d3a0177ed1fc311dd676fc`
retains the exact complete SRAM and valid sidecar. Live
`$7E2830-$287F` remains the vanilla saved `$0430-$047F` block, Epoch remains
exact, and `$7E2CA0-$2CEF` remains zero.

An earlier movie beginning `fa26a04a` captured baseline SRAM after a
concurrent exploratory run replaced its fixture. It is rejected and not in
the accepted manifest.

This proves that current bsnes plus the unmodified vanilla ROM tolerate and
preserve the sidecar-bearing image across boot and one cold load. It does not
prove ownership against every game path, install a load adapter, cover a
sidecar write, New Game+, erase, or the other two slots. Because this control
uses v1, it also provides no runtime evidence for v2's collision-resistant
binding.

## Candidate per-slot format

`proposal`

The `$1E0` interval divides exactly into three `$A0` records:

```text
slot 1 sidecar: $30:7E00-$30:7E9F
slot 2 sidecar: $30:7EA0-$30:7F3F
slot 3 sidecar: $30:7F40-$30:7FDF
```

Proposed version-1 record:

| Offset | Size | Field |
| ---: | ---: | --- |
| `$00` | 4 | Project Epoch magic |
| `$04` | 1 | format version |
| `$05` | 1 | v1 flags: bit 0 initialized; bit 1 retain Project Epoch state in New Game+; bits 2-7 invalid |
| `$06` | 2 | payload length |
| `$08` | 2 | monotonically increasing save sequence |
| `$0A` | 2 | sidecar checksum |
| `$0C` | 2 | checksum of the bound vanilla `$A00` slot |
| `$0E` | 2 | reserved header |
| `$10` | `$50` | independent Schala character record |
| `$60` | 6 | Schala name |
| `$66` | 1 | single-tech learned count, valid range 0-8 |
| `$67` | 1 | high-bit-first learned-single-tech mask |
| `$68` | `$10` | Project Epoch combo-tech state |
| `$78` | 1 | quest flags: unlock, ward resolved, recruited, one-time join grant applied |
| `$79` | 1 | stabilized-anchor count, valid range 0-3 |
| `$7A` | 6 | v1 quest-state reserved bytes, required zero |
| `$80` | `$20` | versioned expansion reserve, required zero in v1 |

The frozen legacy codec uses CRC-16/CCITT-FALSE for the sidecar and binds each
record only to the current vanilla slot checksum. A sidecar is invalid if
either checksum fails, but that does not establish physical provenance.

The host-side v1 policy is now frozen and tested:

- an all-`$FF` record is `uninitialized` and loads no Schala state;
- malformed magic/version/length/CRC, unknown flag bits, nonzero v1 reserved
  bytes, or impossible quest-state ordering is `invalid`;
- a structurally valid record bound to another vanilla checksum is `stale`;
- its legacy classifier can return `valid`, but the production-facing
  versioned planner converts that result to
  `legacy-v1-migration-required` and publishes nothing;
- the single-tech learned count must be 0-8 and its mask must use the
  engine's high-bit-first ordering (`$E0` for three learned techs);
- ward resolution requires an unlocked quest and three anchors; recruitment
  requires ward resolution; the one-time join grant requires recruitment;
- erase invalidates exactly the selected `$A0`-byte sidecar with `$FF` and
  preserves both vanilla slot bytes and global metadata;
- New Game+ with header bit 1 set retains the record and quest/grant guards,
  increments the sequence, and rebinds it to the new vanilla checksum;
- New Game+ without header bit 1 creates a reset record from a caller-supplied
  clean PC7 seed/name and clears tech, combo, quest, recruitment, and grant
  progress.

Version 2 preserves every field through `$7F` and changes only v1-reserved
bytes:

| Offset | Size | Version-2 extension |
| ---: | ---: | --- |
| `$0E` | 1 | explicit physical slot `$01-$03` |
| `$0F` | 1 | binding profile, exactly `$01` |
| `$80` | `$20` | full SHA-256 exact-slot binding |

The byte-exact trailer, reference vectors, CRC order, migration policy, and
lifecycle contract are frozen in `docs/schala_sidecar_v2_contract.md`.

The source-only recruitment transaction adds a separate normal-save
preparation boundary: only after a complete live grant/party commit and after
the exact immutable vanilla `$A00` slot bytes have been serialized may its
legacy `prepare_sidecar_for_save` compute their checksum, copy the live PC7
fields, increment the sequence with saturation, and round-trip the encoded
record. It parses roster bytes `+$0580..+$0588` and joined mask `+$05AF`,
requiring exact PC `$07` once and joined bit `$01` without requiring the
pre-exchange formation. Its complete-grant witness is caller-supplied, not
runtime-observed. That output remains an explicit v1/source-only contract; it
is not accepted by the production-facing v2 load planner and still requires a
separate v2 save adapter.

`tools/schala_sidecar.py` preserves the frozen v1 codec and tests.
`tools/schala_sidecar_v2.py` keeps the same exact `$A0` size and gameplay
offsets while assigning `$0E/$0F` to physical slot/profile and `$80-$9F` to a
full SHA-256. Profile 1 hashes the exact full `$A00` vanilla slot plus a
16-byte `PE07BIND` version/profile/slot/length trailer; the untouched
`+$0834-$09FF` tail is included. CRC-16 still covers the complete sidecar.
Seventeen focused v2 tests cover structural corruption, exact types, stale and
cross-slot copies, a concrete 16-bit checksum collision, all-zero digest
vectors, install isolation, explicit v1 migration, New Game+ value transforms,
invalid vanilla metadata, and magic-last torn states.

The source-only full-load decision boundary is modeled separately in
`tools/schala_sidecar_load_plan.py`. It accepts one exact immutable `$2000`
SRAM image and exact slot number, verifies selected vanilla checksum and magic,
derives only that slot's sidecar, and emits either no-publication `SafeEmpty`
or identity-gated `PreparedLoad`. Both require an exact caller-asserted
preclear witness bound to the full image and slot.

Preclear alone is insufficient when a validated vanilla full load then
restores party bytes. Every post-copy plan includes a mandatory target:
safe-empty changes only exact roster `$07->$87` and clears joined bit `$01`;
valid v2 is published only when its recruitment/grant/tech state agrees with
an in-namespace, duplicate-free serialized roster and joined state, including
both recruited and unrecruited branches. `invalid-vanilla` instead aborts
before copy and exposes no actionable party target.
Valid v1 is always
`legacy-v1-migration-required` safe-empty, while the v2 digest rejects the
preserved 16-bit checksum-collision copy. Twenty focused load-plan tests
cover these boundaries. See `docs/schala_sidecar_load_plan_contract.md` and
`docs/schala_sidecar_v2_contract.md`.

`tools/schala_sidecar_v2_lifecycle.py` now composes those source contracts into
one immutable host executor. Twelve focused tests cover all three slots,
normal-save preinvalidate/body/commit failures, legitimate finalized
`$0430-$047F` and Epoch changes, invalid-vanilla abort before sidecar read,
SafeEmpty `$07->$87` normalization even beside malformed non-`$07` roster
bytes, registered identity publication, retained/reset New Game+ staging and
later binding, exact preview staleness, byte-zero-first partial erase, and
nonselected-byte preservation. This closes the host-model gaps only; none of
the corresponding SNES hooks or allocations is installed.

## Remaining approval gates

- [x] Static slot and metadata boundaries.
- [x] Deterministic boot canary.
- [x] Deterministic Continue/load canary.
- [x] Isolated native slot-1 save and fresh-process full reload with exact
      protected-region comparison.
- [ ] Hook the Project Epoch preinvalidate/vanilla-save/v2-magic-last write
      sequence and readback validation.
- [x] Execute that ordering on host bytes for all three slots with phase and
      partial-body failure injection, exact finalized-slot preservation, and
      readback classification.
- [x] Define and host-test fail-closed full-load classification, registered
      PC `$07` identity gating, a source/slot-bound preclear assertion, and
      post-copy party normalization.
- [ ] Apply the safe-empty party target or publish matching v2 after translated
      vanilla full-load success.
- [x] Define retained/reset v2 value semantics and the load-only New Game+
      staging versus later-normal-save boundary.
- [ ] Hook and runtime-test staged semantics at `$FF:FB3B`, then v2 rebinding
      on the first later normal save.
- [ ] Resolve Schala's save-preview data without treating slot `$0430` as a
      character record.
- [x] Define and host-test an exact-source preview token that uses the
      independent sidecar name and rejects cross-slot, sequence, full-slot,
      and sidecar-content changes.
- [x] Trace save-slot copy: no distinct vanilla copy path exists.
- [x] Trace erase: `$C2:E729->$C2:E8B7`, with selected magic-low-byte
      invalidation only.
- [ ] Hook exact-slot sidecar invalidation before native erase.
- [x] Host-test byte-zero-first sidecar invalidation, partial body clears,
      native magic invalidation last, and exact isolation across all three
      slots.
- [ ] Runtime-test all three slots with distinct canaries.
- [ ] Power-cycle reload after a Project Epoch sidecar write.
- [x] Verify current-bsnes vanilla boot and slot-1 cold-load behavior when
      presented with a valid sidecar-bearing SRAM; save, New Game+, erase, and
      the other two slots remain separate gates.
- [x] Freeze v2 profile 1: CRC-16/CCITT-FALSE plus explicit slot identity,
      weak vanilla-checksum preflight, and full SHA-256 of exact `$A00` plus
      the domain trailer; collision and cross-slot rejection are host-tested.
- [ ] Implement and benchmark profile-1 SHA-256 on 65C816 with proved scratch,
      interrupt, timing, and UI/audio behavior.
- [x] Freeze v1 flag meanings and corruption/staleness behavior in the host
      model.

Until those gates pass, this range is a strong candidate, not a declared free
region.
