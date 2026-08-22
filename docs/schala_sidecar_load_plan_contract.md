# Schala Sidecar Load-Plan Contract

Status: host-tested, runtime-unverified v2 source contract  
Target: Schala logical playable PC ID `$07`  
ROM/install status: no writes, addresses, hooks, or allocations  
Evidence level: source tests only  
Last updated: 2026-07-26

## Purpose

`tools/schala_sidecar_load_plan.py` models the decision boundary between one
complete immutable `$2000` SRAM image and a future live PC `$07` full-load
adapter. It selects exactly one numbered vanilla slot and its matching
candidate sidecar, validates them, and returns either:

- `SafeEmpty`, which publishes no Schala record, name, tech, combo, or quest
  state; or
- `PreparedLoad`, which carries the exact decoded sidecar fields for a later
  adapter.

The model never mutates its input and exposes no SRAM or WRAM address. Only a
strongly bound v2 sidecar can produce `PreparedLoad`; a structurally valid v1
record is deliberately safe-empty pending explicit offline migration.

## Required preclear witness

Every result, including `SafeEmpty`, requires a
`PreclearCompletionWitness`. The factory binds this exact immutable value to:

- the SHA-256 of the complete source SRAM image;
- the exact integer slot number 1, 2, or 3;
- an explicit `all_live_pc07_state_cleared=True` assertion; and
- the fixed evidence label `caller-asserted-unverified`.

The plan and its integrity seal include the complete witness. Reusing it with
another image or slot, changing and resealing a field, omitting it during plan
validation, or supplying a subclass is rejected.

This is deliberately an assertion boundary, not runtime evidence. The host
model cannot observe WRAM and does not prove that a future adapter actually
cleared the complete live PC `$07` footprint. Runtime code must perform that
clear before invoking the vanilla full loader.

Preclear is not sufficient by itself once a validated vanilla load proceeds.
The loader then restores roster bytes `+$0580-$0588` and joined mask `+$05AF`,
so it can reintroduce exact logical ID `$07` after the clear. Every result
following a valid vanilla copy therefore includes a mandatory post-load party
target at the fixed symbolic boundary
`after-vanilla-slot-copy-before-party-consumers`:

- `SafeEmpty` replaces every exact `$07` party byte with inactive `$87` and
  clears joined bit `$01`; and
- `PreparedLoad` preserves the serialized party only after proving that it
  agrees with the sidecar's recruitment and grant state.

`invalid-vanilla` is different: the wrapper must abort before copying the
rejected slot. Its plan carries `postload_party_required=False`, no target
bytes, and action `abort-without-party-write`; untrusted roster bytes from an
invalid slot must never become an actionable live-party target. The preclear
still applies so stale PC `$07` state cannot survive the failed load attempt.
The planner validates vanilla before slicing or classifying the selected
sidecar; a focused mock guard makes any premature classifier call fail.

The complete-source SHA-256 values used to seal the host witness and plan are
provenance bindings computed outside the modeled SNES read sequence. They do
not authorize a future hook to scan the sidecar before vanilla validation.

These are host-derived targets, not proof that a runtime hook applies them.

## Vanilla-slot and sidecar classification

The planner accepts only exact immutable `$2000` bytes and an exact integer
slot number. It derives the `$A00` vanilla slot and matching `$A0` sidecar
internally.

The selected vanilla slot must pass both its stored checksum and magic word.
Failure produces `SafeEmpty("invalid-vanilla")`. A valid vanilla slot then
dispatches exactly by sidecar version:

- all `$FF` is `uninitialized`;
- malformed magic, envelope, CRC, fields, flags, quest invariants, unknown
  version, slot identity, or binding profile is `invalid`;
- a v2 checksum, physical slot, or full `$A00` SHA-256 mismatch is `stale`;
- a valid v1 record is `legacy-v1-migration-required` and publishes nothing;
- a valid v2 payload that disagrees with serialized PC `$07` roster/joined
  state is `state-inconsistent`; and
- only a fully valid, strongly bound, party-consistent v2 record is eligible
  for `PreparedLoad`.

All non-valid classifications publish no Schala fields.

There is no unknown-version fallback and no v2-as-v1 retry.

## Persisted v2 binding

The eligible v2 record stores:

- physical slot identity at sidecar byte `$0E`;
- binding profile 1 at `$0F`;
- the legacy 16-bit slot checksum at `$0C-$0D` as a cheap preflight; and
- a full SHA-256 at `$80-$9F`.

Profile 1 hashes the exact selected `$A00` vanilla slot followed by the
16-byte domain trailer `PE07BIND`, version 2, profile 1, physical slot number,
one zero byte, little-endian `$0A00`, and two zero bytes. This covers the
untouched vanilla tail `$0834-$09FF`, not merely the `$834` bytes written by
the native serializer. The planner also carries the exact v2 version, profile,
and digest in `PreparedLoad` and includes them in its deterministic seal.

## PC `$07` identity gate

A valid sidecar envelope is not sufficient to publish its character record.
`PreparedLoad` also requires the exact `PreparedPc07Identity` type from the
recruitment transaction model.

The identity factory now checks an immutable source-controlled catalog. Its
only entries are the two named non-installable test gates, both pinned to the
same exact synthetic record hash and the `host-fixture` evidence level.
Arbitrary gate names, alternate PC `$07`-shaped records, unsupported evidence
levels, direct self-consistent out-of-catalog construction, and resealed
out-of-catalog substitutions fail revalidation. The identity also carries a
deterministic integrity seal that is included in recruitment and load-plan
seals. Direct reconstruction of an exact registered tuple is accepted by
design because the catalog is the trust boundary.

This makes the value registered-gate validated; it is not a secret capability.
There is no production or `verified-runtime` record gate.

## Protected vanilla data

Each plan binds, but does not publish, SHA-256 values for:

- the complete selected `$A00` vanilla slot;
- protected slot bytes `$0430-$047F`; and
- Epoch's independent six-byte name buffer.

The complete source-image SHA-256 is also bound. Equal displayed bytes for
Schala and Epoch remain legal because their storage identities are separate.

## Integrity and consumption

Both result types are exact frozen slotted dataclasses with deterministic
seals. `validate_load_plan` requires the original complete source image, slot
number, and preclear witness. It checks the presented seal, re-runs the entire
classification and identity gate, and accepts only byte-for-byte equality with
that derivation.

The seal detects accidental or out-of-contract mutation. It is not a
cryptographic authorization secret.

## Version-1 migration and collision policy

The v1 sidecar stores only the vanilla slot's 16-bit checksum. It stores no
slot number and no strong digest of the `$A00` slot. Distinct vanilla slots can
therefore share that checksum, and a copied sidecar can classify as valid for
the wrong slot when such a collision occurs.

The old load planner could publish that copied v1 record. The current
production-facing planner preserves the collision counterexample but returns
`SafeEmpty("legacy-v1-migration-required")`, even when the legacy checksum
matches. Version-1 reserved bytes remain required zero and are never
reinterpreted as v2.

Migration is a separate offline operation in `tools/schala_sidecar_v2.py`. It
requires an exact immutable authorization value bound to the full source SRAM,
selected legacy sidecar, selected `$A00` slot, physical slot number, and an
explicit caller assertion that provenance was reviewed. The assertion is not
independent proof: if the caller authorizes a copied colliding v1 record, the
migration will canonize the wrong origin. No load path migrates automatically.

## Reproduction

Run:

```powershell
& "python" `
  tests\test_schala_sidecar_load_plan.py -v
```

Current focused result: 20 tests pass.

Source hashes:

- `tools/schala_sidecar_load_plan.py`:
  `c4adc0376ab5de40373a787d61bcbe13ed4b8464be5cb495cf022e13b1587162`
- `tests/test_schala_sidecar_load_plan.py`:
  `d704a705a3855f28ce5750dc8e4fb1b9b6239e8496536f8342b631699f343ff4`

The suite covers all safe-empty classes, vanilla checksum/magic rejection,
exact slot selection, full-image/slot-bound preclear witnesses, source
immutability, protected Epoch/compatibility hashes, invalid-vanilla no-copy
semantics, post-load PC `$07` sanitization, recruited/unrecruited and malformed
party rejection, registered record identity, forged/resealed/subclassed
values, canonical v2 publication, exact re-derivation, the intentional v1
checksum-collision counterexample, and v2 rejection of the same collision.
`tools/schala_sidecar_v2_lifecycle.py` now consumes these exact plans in a
separate host executor, including malformed-roster SafeEmpty normalization and
the invalid-vanilla no-copy/no-sidecar-read branch. That composition remains
source-only and does not make the runtime gates below pass.

## Remaining runtime gates

This contract does not prove or install:

- the complete live PC `$07` preclear operation;
- the post-vanilla-load party target being applied before any party consumer;
- the natural PC `$07` record or compatibility-block relocation;
- a sidecar read or live-state publication hook;
- independent name, save preview, normal save, New Game+, or erase integration;
- all-three-slot or power-cycle persistence;
- a 65C816 implementation and timing proof of the v2 SHA-256 binding; or
- any menu, field, battle, equipment, item, tech, growth, or graphics consumer.
