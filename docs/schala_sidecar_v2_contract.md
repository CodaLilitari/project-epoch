# Schala Sidecar Version 2 Contract

Status: host-tested, runtime-unverified source contract  
Target: Schala logical playable PC ID `$07`  
Record size: `$A0` bytes per vanilla save slot  
ROM/install status: no ROM writes, hooks, WRAM allocations, or production SRAM
ownership approval  
Last updated: 2026-07-26

## Purpose and scope

`tools/schala_sidecar_v2.py` defines a collision-resistant successor to the
candidate version-1 Schala sidecar, and
`tools/schala_sidecar_v2_lifecycle.py` executes its fail-closed lifecycle on
immutable host bytes. Version 2 keeps the same three `$A0`-byte record
boundaries and does not move any gameplay field through offset `$7F`. It gives
new meaning only to bytes that version 1 requires to be zero:

- header bytes `$0E-$0F` become an explicit physical-slot identity and fixed
  binding profile; and
- expansion bytes `$80-$9F` become a full SHA-256 binding.

The SHA-256 binds the exact selected vanilla `$A00` slot and the physical slot
number. It closes the demonstrated version-1 failure in which distinct
`$A00` slot bodies with the same 16-bit vanilla checksum accept a copied
sidecar.

This contract is a source model, not an installation. The candidate SRAM gap,
every lifecycle hook, the live PC `$07` destination, SHA-256 code and scratch,
and all ROM allocations remain unapproved.

## Evidence boundary

Use the project evidence labels narrowly:

- `verified-static`: the three vanilla `$A00` slot bounds, checksum coverage,
  candidate `$1E0` gap, global metadata boundary, and currently identified
  normal-load/save/New Game+/erase lifecycle surface reconstructed from the
  canonical ROM.
- `verified-runtime`: the unmodified game preserves the candidate gap during
  the recorded vanilla boot, slot-1 Continue/load, isolated normal save, and
  fresh-process reload controls. A structurally valid **v1** record also
  survived the recorded vanilla boot and cold-load control.
- host-tested source contract: the v2 Python codec, lifecycle executor, and
  their focused tests. This is not `verified-runtime`.
- `caller-asserted-unverified`: the exact evidence string carried by the
  explicit v1 migration authorization. It is not proof of original slot
  provenance.
- `hypothesis`: all future 65C816 code, timing, hook placement, allocation,
  runtime publication, preview, migration, erase, and power-loss behavior
  until separately traced and reproduced.

No current runtime evidence executes a v2 codec, computes SHA-256 on the SNES,
writes a v2 record, or publishes its contents as live PC `$07`.

## Candidate storage geometry

The original 8 KiB SRAM layout is:

```text
$30:6000-$30:69FF  vanilla slot 1 ($A00)
$30:6A00-$30:73FF  vanilla slot 2 ($A00)
$30:7400-$30:7DFF  vanilla slot 3 ($A00)
$30:7E00-$30:7FDF  candidate sidecar area ($1E0)
$30:7FE0-$30:7FFF  vanilla global metadata ($20)
```

The candidate sidecar area divides exactly:

| Selected slot | SRAM record | SRAM file offsets |
| ---: | --- | --- |
| 1 | `$30:7E00-$30:7E9F` | `$1E00-$1E9F` |
| 2 | `$30:7EA0-$30:7F3F` | `$1EA0-$1F3F` |
| 3 | `$30:7F40-$30:7FDF` | `$1F40-$1FDF` |

The caller-selected vanilla slot determines both the `$A00` bytes and the
matching physical sidecar record. An embedded slot byte must never be used to
choose which SRAM region to validate.

## Exact version-2 record

All multibyte header integers are little-endian. The SHA-256 digest is stored
in the standard 32-byte digest order.

| Record offset | Size | Version-2 field and rule |
| ---: | ---: | --- |
| `$00` | 4 | magic `PE07` |
| `$04` | 1 | format version, exactly `$02` |
| `$05` | 1 | flags: bit 0 initialized; bit 1 retain Project Epoch state in New Game+; bits 2-7 invalid |
| `$06` | 2 | payload length, exactly `$0090` |
| `$08` | 2 | save sequence, saturating at `$FFFF` |
| `$0A` | 2 | CRC-16/CCITT-FALSE, stored little-endian |
| `$0C` | 2 | vanilla checksum of the exact bound `$A00` slot |
| `$0E` | 1 | physical slot identity, exactly `$01`, `$02`, or `$03` |
| `$0F` | 1 | binding profile, exactly `$01` |
| `$10` | `$50` | independent Schala character record |
| `$60` | 6 | independent Schala name |
| `$66` | 1 | single-tech learned count, range 0-8 |
| `$67` | 1 | high-bit-first learned mask derived from `$66` |
| `$68` | `$10` | Project Epoch combo-tech state |
| `$78` | 1 | quest flags |
| `$79` | 1 | stabilized-anchor count, range 0-3 |
| `$7A` | 6 | quest-state reserve, required zero |
| `$80` | `$20` | full SHA-256 slot-binding digest |

The existing canonical quest ordering remains mandatory:

- ward resolved requires the quest unlocked and exactly three anchors;
- recruited requires ward resolved; and
- the one-time join-grant guard requires recruited.

The `$50` character record is still subject to the separate PC `$07` identity
and readiness gate. A valid v2 envelope does not prove that record safe for
live publication.

Version 2 consumes the complete v1 expansion reserve. Any additional persisted
fields require another explicit version or another storage design.

### Physical extension bytes

| Slot | Identity/profile | Digest |
| ---: | --- | --- |
| 1 | `$30:7E0E-$30:7E0F` | `$30:7E80-$30:7E9F` |
| 2 | `$30:7EAE-$30:7EAF` | `$30:7F20-$30:7F3F` |
| 3 | `$30:7F4E-$30:7F4F` | `$30:7FC0-$30:7FDF` |

## SHA-256 binding profile `$01`

The binding is:

```text
SHA-256(
    exact selected vanilla slot bytes $0000-$09FF
    || binding_trailer(selected_slot_number)
)
```

The exact 16-byte trailer is:

| Trailer offset | Size | Value |
| ---: | ---: | --- |
| `$00` | 8 | ASCII `PE07BIND` |
| `$08` | 1 | record version `$02` |
| `$09` | 1 | binding profile `$01` |
| `$0A` | 1 | physical slot `$01`, `$02`, or `$03` |
| `$0B` | 1 | zero |
| `$0C` | 2 | slot length `$0A00`, little-endian bytes `00 0A` |
| `$0E` | 2 | zero |

For slot 1 the trailer is:

```text
50 45 30 37 42 49 4E 44 02 01 01 00 00 0A 00 00
```

The message is exactly `$A10` bytes, or `$5080` bits. Because `$A00` is forty
complete 64-byte SHA-256 blocks, a future 65C816 implementation may stream
those forty blocks directly from the selected vanilla slot and construct one
final block containing the 16-byte trailer, SHA padding, and bit length.

### All-zero `$A00` reference vectors

| Physical slot | SHA-256 |
| ---: | --- |
| 1 | `878829ba5210cd4d1defacbedb6c485407a25dc8be2cf46ae2bd90636b9ebdbd` |
| 2 | `45351b0ff714359ed22d687605b843658bf8ce3e2d997199ce0077323cde00b5` |
| 3 | `716b7eb41aa41f3febfb7843cb18174a01ba869cf2a634b0fe53f0d58cdd59b2` |

Including the slot number in both the header and digest trailer means that
even byte-identical slot bodies produce different bindings for slots 1, 2,
and 3.

## CRC construction and validation order

Version 2 retains CRC-16/CCITT-FALSE:

- polynomial `$1021`;
- initial value `$FFFF`;
- no reflection; and
- no final XOR.

Encoding order is normative:

1. Require exact field types, lengths, ranges, flags, learned mask, and quest
   semantics.
2. Compute the vanilla checksum and SHA-256 from the exact `$A00` slot and
   selected slot number.
3. Build all `$A0` record bytes with `$0A-$0B` zero.
4. Place the 32-byte SHA-256 at `$80-$9F`.
5. Compute CRC-16 over all `$A0` bytes.
6. Store the CRC little-endian at `$0A-$0B`.

Validation zeroes `$0A-$0B`, recomputes the CRC across all `$A0` bytes, and
compares it to the stored value. The CRC therefore covers the magic, version,
flags, lengths, sequence, weak checksum, explicit slot, binding profile,
gameplay fields, and SHA-256 digest.

The current source validation order is:

1. exact input types and lengths;
2. for a complete SRAM load, selected vanilla-slot stored checksum and global
   magic;
3. all-`$FF`, magic, and exact-version dispatch;
4. v2 payload length, flags, embedded slot range, and profile;
5. v2 CRC;
6. learned-tech and quest canonicality;
7. embedded slot equality, vanilla checksum equality, and SHA-256 equality.

Unknown versions or profiles never fall back to another parser. Any
uninitialized, invalid, stale, legacy, or invalid-vanilla result carries no
publishable Schala value.

CRC detects accidental sidecar corruption and torn records. SHA-256 supplies
the collision-resistant binding to the selected vanilla data. They serve
different purposes and both are required.

Profile `$01` does not additionally hash the sidecar gameplay body; those
bytes are covered by the record CRC. This closes the demonstrated vanilla-slot
checksum collision without claiming adversarial payload authentication. A
future profile that changes the digest message must use a new explicit profile
ID and new vectors.

## Version-1 compatibility and migration

Version 1 remains byte-exact:

- version byte `$01`;
- header bytes `$0E-$0F` required zero;
- expansion bytes `$80-$9F` required zero; and
- the frozen v1 CRC, field, flag, quest, and 16-bit checksum rules unchanged.

The versioned v2 classifier may decode a valid v1 record only far enough to
classify it `legacy-v1-migration-required`. Its returned value is `None`.
A v1 record must never publish live PC `$07` state through the v2 path.

Automatic migration is forbidden. A v1 record cannot prove its original slot:
an exact checksum collision and copied-record counterexample is preserved in
the tests.

The host-only explicit migration path requires
`V1MigrationAuthorization`, which binds:

- SHA-256 of the complete source `$2000` SRAM;
- SHA-256 of the selected encoded v1 record;
- SHA-256 of the selected `$A00` slot;
- exact slot number 1, 2, or 3;
- `selected_slot_provenance_reviewed=True`; and
- evidence string `caller-asserted-unverified`.

The selected vanilla slot must independently pass its stored checksum and
global magic, and the selected v1 record must pass the complete v1 classifier.
Migration preserves the v1 gameplay and retention fields, increments the
sequence with saturation, creates a v2 digest for the asserted physical slot,
installs only that `$A0` record in the host image, and revalidates the result.

The authorization seal is deterministic and public. It detects mutation; it
does not prove the human review occurred. A mistaken assertion can canonize a
copied v1 record. That limitation is why migration is explicit and why no ROM
migration hook is approved.

## Lifecycle contract

### Normal save

A future normal-save wrapper must first invalidate the selected sidecar, then
call the vanilla writer and wait until it has finished the exact selected
`$A00` serialization and finalized that slot's global checksum, magic, and
global metadata.

Before preparing a recruited-state sidecar, the post-serialization boundary
must validate the serialized roster at slot offsets `$0580-$0588` and joined
mask at `$05AF`:

- every roster byte is logical `$00-$07` or inactive `$80-$87`, with no
  duplicate exact playable IDs;
- recruited state requires exact logical PC `$07` exactly once and joined bit
  `$01` set;
- unrecruited state requires no exact `$07` and joined bit `$01` clear;
- recruited quest state requires the one-time grant guard and at least the
  three recruitment techs; and
- unrecruited state must not carry the grant guard or learned single-tech
  progress.

The sidecar codec does not perform this roster check. The existing recruitment
transaction model freezes the source-only form of that boundary. A future v2
save adapter must combine the roster/quest identity checks with v2 preparation;
it must not encode an arbitrary `$50` record merely because its lengths fit.

The complete fail-closed runtime order is:

1. write an invalid value to selected sidecar byte `$00`, breaking `PE07`;
2. call vanilla `SaveSlot_Write` and allow it to finalize the selected full
   `$A00`, checksum, magic, last-selected slot, and save-count metadata;
3. derive a complete v2 buffer from those finalized `$A00` bytes;
4. write final sidecar bytes `$01-$9F`, including the final CRC and SHA-256;
5. write final byte `$00` (`P`, `$50`) last as the commit marker; and
6. read back and fully revalidate the selected vanilla metadata, record CRC,
   slot identity, weak checksum, SHA-256, and semantic fields.

The sidecar phase must leave the caller-finalized `$A00` byte-for-byte exact,
including protected `$0430-$047F` and Epoch's independent name. This compares
post-sidecar output with the finalized vanilla save, not with the old pre-save
slot: legitimate vanilla changes such as a renamed Epoch remain vanilla's
responsibility. Only untouched tail `$0834-$09FF` is required to equal its
pre-save source because the native writer does not serialize that range.

Power loss before step 3 must leave a magic mismatch and publish nothing.
The host `install_sidecar_v2` helper performs an immutable byte-array
replacement; it is not evidence that this runtime write protocol exists or is
power-loss safe.

### Full load and postload roster boundary

A future full-load adapter must not publish directly from the low-level
decoder. The required order is:

1. require an exact externally selected slot index;
2. clear every pre-existing live PC `$07` field even if later validation
   fails;
3. revalidate the selected vanilla slot's global stored checksum and magic;
4. run the translated vanilla full load for that slot only after validation;
5. select only the matching physical `$A0` sidecar;
6. run exact version dispatch and complete v2 validation;
7. require a registered PC `$07` identity token for the decoded `$50` record;
8. compare the now-loaded party roster and joined bit with
   recruited/unrecruited sidecar quest state using the normal-save invariants;
9. if vanilla metadata was valid and the copy ran, normalize any safe-empty
   result by replacing exact roster `$07` with inactive `$87` and clearing
   joined bit `$01` before a party consumer runs; invalid vanilla metadata
   instead aborts before the copy and carries no party-write target; and
10. only on complete success preserve the consistent party and publish record,
   independent name, tech, combo, and quest state atomically.

The preclear witness in the existing source load-plan model is only a
full-image/slot-bound caller assertion. It is not runtime evidence that step 2
happened. Likewise, `load_sidecar_v2_from_sram` proves metadata and persisted
binding only; it does not inspect a live roster, choose a live address, or
perform steps 2, 6, 7, or 8.

On any disagreement, publish no Schala fields. The only canonical safe-empty
party normalization is exact `$07->$87` plus clearing joined bit `$01`; do not
rewrite `$07` as another playable PC, treat `$0430` as an eighth record, or
route through Epoch's name. Applying that sealed target at runtime remains an
approval gate.

### New Game+

New Game+ has two distinct phases that must not be conflated:

1. **Source-load staging.** Validate the selected source vanilla metadata and
   v2 record, apply the retained/reset sidecar policy to live staged state, and
   apply that policy before any recruitment-graph state test.
2. **Later normal save.** Only after a destination `$A00` slot has actually
   been serialized may a destination v2 sidecar be computed from those exact
   bytes and the destination physical slot.

Do not copy source v2 bytes to a destination slot, and do not bind a persisted
record to a hypothetical destination during the New Game+ partial load.

The host function
`prepare_new_game_plus_v2_for_serialized_save` models phase 2:

- it first requires the supplied source value to rederive against the supplied
  source `$A00` bytes under its embedded source slot;
- retained mode preserves character, name, tech, combo, quest, and flags;
- reset mode uses caller-supplied reset record/name and clears tech, combo,
  quest, recruitment, grant, and retain state;
- both modes saturating-increment the sequence; and
- both bind a new value to exact already-serialized destination bytes and
  destination slot.

This is a pure value transform. It receives neither a complete source SRAM nor
an independently selected source-slot argument. Its caller must supply a
source value obtained from the validated physical-source load boundary. The
reset record also remains subject to the external registered PC `$07` identity
gate.

No New Game+ read, staging, or later-save hook is installed.

### Erase

Vanilla erase clears only its global slot magic. A Project Epoch erase adapter
must invalidate exactly the matching `$A0` sidecar, preferably by breaking its
magic before any longer clear, and must preserve:

- all three vanilla `$A00` slots;
- the other two sidecars; and
- unrelated global metadata.

The v2 host lifecycle model breaks selected sidecar magic byte `$00` first,
then clears bytes `$01-$9F`, then applies the native selected magic-low-byte
write. Failure injection covers interruption after byte `$00`, throughout the
longer body clear, after the complete body clear, and after native
invalidation. The selected record becomes non-publishable at the first byte;
the other two records and all nonselected bytes remain exact. No v2 runtime
erase integration exists.

### Save preview

Save preview is a read-only consumer with its own boundary. It must:

- use the externally selected vanilla slot and matching sidecar;
- require valid vanilla metadata and complete v2 classification before showing
  any Schala-specific field;
- require the registered PC `$07` identity gate before using record-dependent
  preview fields;
- treat v1, invalid, stale, unknown, and uninitialized records as
  no-publication states;
- never interpret slot-relative `$0430` as an eighth character record; and
- never use Epoch's independent name buffer or vanilla naming ID `$07` as
  Schala's name.

Preview-specific portrait, name, level/stat, and roster adapters remain
unimplemented and unapproved.

### Executable host lifecycle proof

`tools/schala_sidecar_v2_lifecycle.py` composes the codec, registered identity
gate, and load planner without modifying a ROM or claiming an SRAM hook. Its
immutable results and byte-level traces model:

- normal save preinvalidation, exact vanilla `$834`-byte prefix and metadata
  finalization, full-`$A00` binding, body write, magic-last commit, and
  readback;
- interruption after each save phase and after any selected count of sidecar
  body bytes;
- source/slot-bound preclear, invalid-vanilla abort before copy or sidecar
  read, valid-copy SafeEmpty normalization, and identity-gated v2
  publication;
- retained/reset New Game+ staging with no destination identity, followed by
  exactly one sequence increment and bind on a later normal save;
- preview tokens bound to the exact source image, physical slot, sidecar,
  sequence, binding digest, protected ranges, and independent Schala name;
  and
- byte-zero-first exact-slot erase, partial body clears, and native
  invalidation last.

The full-source hashes that seal caller assertions and immutable host results
are provenance metadata outside the modeled SNES read trace. They do not
permit a runtime adapter to classify or consume the selected sidecar before
vanilla validation succeeds.

SafeEmpty normalization deliberately accepts the exact raw nine roster bytes
restored by vanilla even when non-`$07` bytes are malformed. It changes only
exact `$07` entries to `$87` and clears joined bit `$01`; malformed values are
not silently recoded as other characters. Valid publication remains stricter
and requires the planner's canonical namespace and duplicate-ID checks.

This is host proof of ordering and refusal behavior, not evidence that any
candidate hook, WRAM target, scratch range, or SRAM ownership is safe.

## Threat model and explicit non-goals

Version 2 is designed to detect:

- accidental sidecar corruption;
- torn or precommit records;
- stale sidecars after vanilla-slot changes;
- copied records between physical slots, including byte-identical slot bodies;
- distinct `$A00` bodies with the same 16-bit vanilla checksum; and
- unsupported versions, profiles, flags, and noncanonical gameplay state.

It is not authentication:

- SHA-256 and CRC are unkeyed;
- a party able to rewrite SRAM can recompute both;
- deterministic host seals and caller witnesses are not secret capabilities;
  and
- no useful secret can be assumed merely because it is embedded in a ROM.

It is not rollback protection:

- sequence saturation is a save-order hint, not a monotonic security counter;
- no trusted external counter or authenticated metadata anchors it; and
- restoring an older internally consistent full SRAM image restores an older
  valid sidecar with it.

The SHA-256 binding authenticates neither the human origin nor authorship of a
save. It states only that this record is internally bound to these exact
`$A00` bytes and this physical slot under profile `$01`.

## 65C816 implementation and benchmark gate

SHA-256 is practical enough to model but expensive on a 65C816: its 32-bit
adds, rotates, and logical operations must be composed on a 16-bit CPU.
Profile `$01` requires 41 compression blocks per binding.

Before any runtime approval, an implementation must:

- reproduce the host trailer and digest vectors byte-for-byte;
- use standard SHA-256 big-endian message words and digest order while
  retaining the sidecar's little-endian integers;
- preserve processor flags, direct-page assumptions, data bank, stack, and
  every live caller register required by the selected path;
- use only a separately proved WRAM scratch allocation and a named expanded-ROM
  code/constants allocation;
- avoid NMI or another frame-critical context unless a separately proved
  resumable design exists;
- benchmark normal save, full load, New Game+ source staging, preview, and any
  readback validation on the supported current emulator;
- record cycle/frame latency, input/audio impact, scratch high-water mark, and
  exact output hashes; and
- pass all-three-slot, interrupted-write, erase, New Game+, reset, preview, and
  power-cycle persistence tests.

No cycle budget or acceptance threshold is yet approved. Do not assume
`$7E2CA0-$7E2CEF`, a canonical ROM zero run, or any other candidate address is
available for SHA state, schedule, code, constants, or buffers.

## Reproduction

Using the bundled Python runtime:

```powershell
$python = "python"

& $python -m unittest tests.test_schala_sidecar_v2 -v
& $python -m unittest tests.test_schala_sidecar_v2_lifecycle -v
& $python -m unittest tests.test_schala_sidecar -v
& $python -m py_compile tools\schala_sidecar_v2.py `
  tools\schala_sidecar_v2_lifecycle.py `
  tests\test_schala_sidecar_v2.py `
  tests\test_schala_sidecar_v2_lifecycle.py
```

Current focused results:

```text
Ran 17 tests in 0.044s
OK

Ran 12 tests in 0.115s
OK
```

Current source hashes:

- `tools/schala_sidecar_v2.py`:
  `d9d359261610137bc52c1ed99404fed8265f645f7b39860979881884fef58c24`
- `tests/test_schala_sidecar_v2.py`:
  `d26e60067e202b241abd174660d09305f4676d0f22f576ace13310e1c6cb62f0`
- `tools/schala_sidecar_v2_lifecycle.py`:
  `7025677a733e5e941216be71ecb9fe882cd93716097c37cec15e4edc618e5443`
- `tests/test_schala_sidecar_v2_lifecycle.py`:
  `ce74689f30f6f80685e29b93b978039d0cb54dd81e380105bda807f0ffa8b72b`

The focused suite covers exact layout and digest vectors, round trip, CRC and
header corruption, wrong slot/profile/version, digest corruption with a
recomputed CRC, exact-type and subclass rejection, checksum-collision and
identical-body cross-slot copies, install isolation, invalid vanilla metadata,
explicit v1 migration and refusal cases, migration sequence saturation,
retained/reset New Game+ rebinding, stale-source rejection, and magic-last
torn-record behavior. The lifecycle suite adds all-three-slot save/erase
isolation, phase and partial-body failure injection, finalized
compatibility/Epoch preservation, exact preclear and identity binding,
invalid-vanilla no-copy/no-sidecar-read behavior, raw-roster SafeEmpty
sanitization, retained/reset staging, publishable preview collisions, and
CRC-16 sidecar-collision cache rejection.

## Remaining approval gates

This source contract does not approve or implement:

- ownership of `$30:7E00-$30:7FDF` against every vanilla and emulator path;
- a complete production-ready natural PC `$07` record or identity token;
- live record, compatibility block, name, roster, party, or preclear
  allocations;
- normal-save, full-load, New Game+, erase, preview, or migration hooks;
- 65C816 SHA-256, CRC, commit-order, or readback code;
- an all-three-slot runtime and power-cycle matrix;
- interrupted-write behavior on actual SRAM;
- rollback protection or authenticated saves; or
- any menu, field, battle, equipment, item, tech, growth, sprite, portrait, or
  dialogue consumer.

Until those gates pass with named allocations and runtime evidence, version 2
remains non-installable source-only architecture.
