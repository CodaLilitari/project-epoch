# Schala Recruitment Transaction Contract

Status: host-tested, runtime-unverified source contract  
Target: Schala logical playable PC ID `$07`  
ROM/install status: no writes, addresses, hooks, or allocations  
Last updated: 2026-07-26

## Why this contract exists

The original Silent Palace JSON is a player-facing narrative state machine.
Its symbolic `commit_recruitment` node appears before the party-capacity
branch, so it must not be compiled literally as engine write ordering.

The current-core North Cape trace supplies a safer behavioral reference. With
a full active party, Magus becomes provisionally visible in reserve and the
joined mask changes before name acceptance. Party exchange follows name
acceptance, while the isolated SRAM remains byte-identical throughout.
Live/provisional work and persistent save work are therefore separate phases.

`tools/schala_recruitment_transaction.py` freezes that separation as a pure
host model. It does not make a PC `$07` record, independent name buffer,
sidecar gap, or party adapter production-ready.

## Four deliberately separate states

```text
checksum-bound persisted sidecar preimage
        |
        v
reversible live reserve stage
        |
        v
caller-witnessed complete-grant live commit
        |
        v
later sidecar save bound to the exact newly serialized vanilla slot
```

1. `begin_recruitment` accepts only a valid sidecar bound to the selected
   vanilla checksum, a separately supplied PC `$07` readiness token, and a
   stable party/sidecar state.
2. The stage materializes Schala's persisted six opaque name bytes in an
   abstract live field and registers exact PC `$07` in reserve. It changes no
   persisted sidecar byte.
3. `prepare_recruitment_commit` derives the capacity-safe target party and
   lists required effects without claiming they happened.
4. `finalize_recruitment_commit` accepts only a complete
   `JoinGrantCompletionWitness`: the caller must assert that starting techs,
   Glass Focus, and Regent Mantle all completed. Only then does the live
   quest state gain recruited and grant-applied flags. The host model cannot
   observe inventory, learned-tech state, or adapter success; those remain
   runtime gates.
5. `prepare_sidecar_for_save` is a later boundary. After the vanilla slot has
   been serialized, it accepts the exact immutable `$A00` slot bytes,
   computes their vanilla checksum internally, increments the sequence with
   saturation, copies the committed live fields, binds that computed
   checksum, and performs a canonical encode/decode check. The returned host
   object records both the slot SHA-256 and computed checksum. It also parses
   roster bytes `+$0580..+$0588` and joined mask `+$05AF`, requiring exact PC
   `$07` once and bit `$01` set. The serialized formation may otherwise
   differ from the commit plan because post-commit party exchange may already
   have run.

The output of step 5 is still the frozen v1 host object. It is retained as
recruitment/roster ordering evidence, but the production-facing versioned load
planner deliberately classifies it `legacy-v1-migration-required` and will not
publish it. A separate v2 normal-save adapter must carry the same committed
live fields, registered identity gate, and serialized-party checks into the
full-slot SHA binding and magic-last lifecycle. No SRAM write hook is
installed.

## Record-readiness boundary

A valid sidecar envelope does not prove that its `$50`-byte character record
is safe to expose as PC `$07`. The transaction therefore requires
`PreparedPc07Identity`, bound by SHA-256 to a record whose identity byte is
`$07`. Its factory also requires an exact entry in an immutable
source-controlled gate/record catalog and emits a deterministic identity seal.
Direct self-consistent construction or resealing with an arbitrary gate does
not pass consumer revalidation.

The current focused tests use only two named non-installable test gates, the
explicit `host-fixture` evidence level, and one pinned synthetic record hash.
No `verified-runtime` PC `$07` readiness token exists, and both the exported
level and host-fixture catalogs are immutable. Record bytes `+$01`, `+$02`,
current/base stat
initialization, equipment translation, and tail recomputation remain open
gates.

## Party invariants

The model enforces:

- exactly nine party bytes;
- only logical IDs `$00-$07` or inactive values `$80-$87`;
- no duplicate exact/nonnegative logical ID;
- stable unrecruited state means no exact `$07` and joined bit `$01` clear;
- stable recruited state means exact `$07` appears once, joined bit `$01` is
  set, the grant guard is set, and at least three single techs are learned;
- reserve staging changes only joined bit `$01` and one inactive reserve byte;
- an existing inactive `$87` is preferred when staging so a stale `$87` is
  not left beside a new exact `$07`;
- all three active bytes remain unchanged during reserve staging;
- active insertion is derived only when the original active trio contained a
  high-bit-set slot;
- a full trio is left byte-identical, with party exchange emitted only as a
  post-commit action.

This deliberately excludes vanilla party operation 1's full-party fallback,
which replaces active slot 3.

## Name boundary

All names remain opaque exact-six-byte values. The transaction makes no
unproved claim about glyph encoding, `$EF`, padding, empty names, or duplicate
displayed values. Schala may have byte-identical displayed-name data to a
vanilla PC or Epoch; storage isolation, not value inequality, is the safety
property.

The model carries the seven vanilla name buffers and Epoch's six-byte buffer
unchanged through staging, commit, and save preparation. It chooses no
Schala live-name address. Name-entry, portrait, duplicate-name, dialogue
substitution, and save/load adapters remain required.

## Interruption and integrity behavior

- `abort_recruitment` revalidates the sealed stage and returns the exact
  original party.
- The persisted sidecar preimage remains unchanged through stage and live
  commit.
- Already-recruited entry produces no effects, grants, naming, or exchange
  action.
- Every incomplete grant-witness combination is rejected. A complete witness
  remains a caller assertion, not runtime observation.
- Prepared identities plus stage, commit-plan, and live-state derivations
  carry deterministic integrity seals, require their exact non-subclassed
  host types, and are semantically revalidated before the next transition.
  Save preparation re-derives the exact live state from its originating plan
  and grant witness, so a resealed forged gate, outcome, party, record, name,
  quest, tech, or post-action field is rejected.
- Uninitialized, invalid, and stale sidecars cause staging to be refused.
  This function does not clear a pre-existing live PC `$07`. The separate
  source-only load planner now requires a source/slot-bound caller assertion
  that preclear completed before it emits either a safe-empty or populated
  plan; the actual runtime clear remains unimplemented and unverified.

## Reproduction

Run:

```powershell
& "python" `
  tests\test_schala_recruitment_transaction.py -v
```

Current focused result: 18 tests pass.

Source hashes:

- `tools/schala_recruitment_transaction.py`:
  `1ac60f023b45a1874102f21e322f1229c4ccc2df569a680538a0338f4945c6ba`
- `tests/test_schala_recruitment_transaction.py`:
  `bffd12d0998722e4ec14f69434c495d67b994cf8ff3331f47562cd864b90e540`

The suite covers open/full capacity branches, `$87` reuse, exact abort and
restart, invalid/stale sidecars, opaque/equal name values, record identity and
host-fixture-only readiness binding, namespace rejection, stable joined-state
synchronization, all partial grant witnesses, forged stages/plans/live
fields and polymorphic subclasses, idempotent entry, exact `$A00` slot
checksum/roster binding, registered-gate identity forgery, and sequence
saturation.

## Remaining runtime gates

This contract does not prove or install:

- a complete natural PC `$07` record or compatibility-block relocation;
- an independent live-name allocation or any naming/dialogue hook;
- PC `$07` roster and eight-character party-exchange adapters;
- runtime sidecar preclear/load publication, normal save, New Game+, erase,
  preview, or power-cycle persistence;
- a production v2 adapter from the committed recruitment state (the current
  step-5 save object is v1/source-only);
- runtime starting-tech and starting-item grants;
- any menu, field, battle, sprite, portrait, equipment, item, tech, or growth
  consumer.

Every recruitment binding in the authored JSON remains null until those
independent gates pass.
