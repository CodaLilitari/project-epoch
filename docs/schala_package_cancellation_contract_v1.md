# Package refusal and queued-Tech cancellation contract v1

Date: 2026-09-08. Gate: `BA-NATIVE-INTEGRATION-DESIGN`.

Status: `verified-static` for the named canonical instructions and control-flow
relationships below; `hypothesis` for the proposed earlier preflight boundary.
No cancellation adapter, ROM hook, expanded allocation, or production selector
is approved. This document adds a bounded contract to the
[resolver integration design](schala_package_resolver_integration_design_v0.md).
The completed [primary resolver observation](schala_package_resolver_observation_v0.md)
and original synthetic helper proof remain unchanged.

## The decisive distinction

A bank-correct return from the package resolver is an animation-loader refusal.
It is not a complete cancellation of the player's queued Tech. On the canonical
queued-Tech path, participant MP is deducted before the animation phase, and
the ordinary return from that phase proceeds to pending-result application.
Making the animation waits terminate could therefore spend MP and apply the
prepared effect without running the intended animation.

The integration design must distinguish these outcomes:

| Outcome | Required meaning | Current evidence |
| --- | --- | --- |
| Descriptor refusal | Publish no package data and restore the helper's declared context | Completed synthetic helper evidence |
| Animation phase completion | Return with the real caller's stack and width contract, finish its latches and cleanup | One ordinary canonical action observed; refusal path unproved |
| Queued-Tech cancellation | Release the exact queued command and participants without running the rejected effect or charging its MP | Earlier vanilla failure branches identified statically; new adapter unproved |

The recommended next design is an earlier package preflight before effect
preparation, with the existing resolver check retained as defense against an
unexpected invalid input. A late failure still requires an explicit policy;
it must not silently masquerade as cancellation.

## Provenance and reproducible checks

Primary evidence is the user's local headerless US Rev0 ROM: 4,194,304 bytes,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The [read-only verifier](../tools/audit_package_cancellation_boundaries_v1.py)
rejects a different full-ROM identity, then checks 19 named span hashes and
32 selected instruction operands/control-flow relationships. Its deterministic
[metadata](../references/package_cancellation_boundaries_v1.json) contains no
canonical byte payload, ROM, save, or trace. Hashes identify the inspected
corpus; reviewer interpretation supplies the semantic labels. This is not a
general disassembler or a complete reachable-code proof.

Navigation and annotation source:
[dscotton/ct_disassembly at eeae27acdb6565e96d1d796a3d60792c250c0aa1](https://github.com/dscotton/ct_disassembly/tree/eeae27acdb6565e96d1d796a3d60792c250c0aa1),
preserved unchanged at `private/research/ct_disassembly_eeae27a`.
The inspected files have these SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `bank_C1.asm` | `298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa` |
| `bank_CC.asm` | `d60669a2de45ce888298b5d1e4a88739173bb707a8293ddadbeffb2eeab2eb7d` |
| `bank_CD.asm` | `0d230620c6accf311c0588e2fefaf3bcc48b0d42575f3745fec3a402a6ca19fb` |

Run from the repository root:

```powershell
python -B tools/audit_package_cancellation_boundaries_v1.py
```

The verifier writes nothing. To reproduce the checked-in JSON, serialize the
returned audit object with `json.dumps(..., indent=2)`, append one newline, and
use UTF-8 with LF line endings. Compare the resulting bytes with the checked-in
metadata. The initial verification also refused a truncated image and a
same-size, one-byte alteration constructed only in memory. No altered image
was written, no emulator was launched, and no catalog was changed in this pass.

All ranges in this document are half-open CPU bus ranges. File offsets for
this canonical image are `CPU address & $3FFFFF`.

## The queued-Tech transaction is wider than the resolver

The bounded ordinary path is:

1. `$C1:BB49` enters queued-Tech execution. `$C1:BB88` calls target-list
   validation. Its `$AF23` failure branch at `$C1:BB8B-$BB93` bypasses action
   construction and transfers to `$C1:BC5A`.
2. The valid path establishes action type `$02`, actor, Tech/config ID,
   target list, and masks. `$C1:BBD4` calls effect preparation at `$C1:BF79`,
   which calls `$C1:D523`. That routine clears result work, resolves participant
   data, checks MP, and proceeds to the per-participant effect dispatcher.
   Preparation is not merely a graphics lookup. Its complete side-effect
   closure is outside this bounded audit.
3. After preparation, nonzero `$AF23` or `$B3C8` branches to `$C1:BC5A` at
   `$C1:BBDA/$BBDF`. The successful path calls the MP deduction routine at
   `$C1:BC01`, `$C1:BC0E`, and `$C1:BC1B` for the three participant positions.
   The deduction routine accepts absent participant `$FF`; present positions
   resolve to the supported party slots. It directly subtracts the discounted
   cost from the MP words at `$7E5E34`, `$7E5EB4`, or `$7E5F34`.
4. `$C1:BC1E` calls `$C1:AC57`. That wrapper first invokes animation service 4
   through `$C1:BFA4`, then unconditionally calls the result-application wrapper
   at `$C1:AC5A`. The latter reaches `$C1:EC7F`. For example, the canonical HP
   pass subtracts a pending result from a battler's HP and stores the result
   at `$C1:ECA0`; additional entries, clamping, MP, and death handling follow.
5. The successful Tech path clears its target-result display table at
   `$C1:BC56` and returns directly into `$C1:BC5A`, the same finalization tail
   reached by the early failures. This calls `$C1:BDB3`, then tail-transfers
   to the command/partner-release routine at `$C1:BCF8`.

The verifier checks the named calls, failure branches, direct MP stores,
success fallthrough, and service-4 table target. The following central pins
make the effect/animation ordering independently reviewable; the JSON records
the remaining spans.

| CPU range | Bytes | SHA-256 | Evidence |
| --- | ---: | --- | --- |
| `$C1:BB49-$C1:BBD4` | 139 | `4449dcbfa74ed8d603426f98e639b727a9be43608f1f9b3a88f2947c19ba5b8b` | Target failure and action setup |
| `$C1:BBD4-$C1:BC21` | 77 | `8b3c37b61d5c6455f6bb01bd1befcd18337bd557ff54c363aa3de55f1c2b5570` | Effect preparation, MP calls, animation/result commit |
| `$C1:CC71-$C1:CCCB` | 90 | `a244c0b228a6f66df81db5c4fb32bf3c98d9c0d2c9f7e98193264648ac0d93bc` | Direct participant MP writes |
| `$C1:AC57-$C1:AC5E` | 7 | `d46f35d4a2da30eb6ba1b9e286d34b944fb853ee0ec9b5eedc8fcc7742122499` | Animation return proceeds to result application |
| `$C1:EC7F-$C1:ECA3` | 36 | `4fd8fb28635325d22bd8c0dae9a942bfa420ee78b9e0b2f8bf464555fe35004c` | One concrete pending HP result store |
| `$C1:BC4A-$C1:BC60` | 22 | `2258622ba95551f41347b852f03148795064fb55c5932ae7b92b40f3fa6e4f70` | Success and failure share the finalizer |

This order is `verified-static`. The current primary runtime observation
begins too late to prove the MP/result history of that particular invocation;
this document does not retroactively claim that it captured these earlier
sites.

## Why a near return or latch write is insufficient

The ordinary animation phase resets its work at `$C1:405B` through
`$CC:F06B-$CC:F102`. The reset clears the span `$7E5D80-$7E5E0D`, including
the package active bytes and `$5D9B`, and separately clears `$9876`.
Later setup and frame service can start new work; the reset is not proof that
all those bytes remain zero at the resolver.

The action-type-zero target `$C1:475A` is an `RTS`, but it is not a proved
error handler for type-2 package installation. A tail transfer to it can fix
the program-bank problem only after the helper restores the ordinary M=1
return width and preserves the existing near-call frames. It supplies no
package completion signal and does not unwind the broader action transaction.

After the dispatcher returns, `$C1:40B0-$40D3` executes its frame/script loop
at least once and waits for nonzero `$9876`. Terminal command `$00` only
clears its owner at `$C1:4CF3`. The separate synchronization handler increments
`$9876` at `$C1:4D00`. Under a quiescent diagnostic with no publication and no
other writer making that latch nonzero, a bank-correct no-op return cannot
leave this loop. This is a conditional static failure argument, not a claim
that all possible battle states hang.

Writing `$9876=1` would address only one predicate. It would still allow the
script runner to execute before the latch test, so stale owners must be
excluded by evidence. The next loop waits for `$5D9B=0`. The scene-script
routine `$CD:1609-$CD:1654` owns one important completion route: it checks two
scene slots and clears `$5D9B` at `$CD:164D` only after both finish. Clearing
this byte from a refusal adapter would bypass a separate producer's lifetime;
its generic name in the existing probe does not make it disposable scratch.

Even if both waits terminate, the caller restores its saved DP `$A4` byte,
clears animation work, resets sprite state, performs enemy/visual follow-up,
and returns to the wrapper that applies prepared results. Skipping directly
to `$C1:40EC` or `$C1:BC5A` from the resolver would additionally need an exact
stack transformation. The existing two near-return words and saved byte
cannot be consumed as though execution entered either continuation normally.

Consequently there is no selected late-refusal write set in v1. In particular,
this document approves neither clearing all owners nor forcibly clearing the
scene latch, restoring old MP, clearing arbitrary result tables, or bypassing
the ordinary action finalizer. Those actions have different ownership and
would need separate evidence.

## Earlier preflight proposal and exact limits

For a supported queued Tech with validated participant and command context,
evaluate the package registry and the complete descriptor contract before
the call at `$C1:BBD4`. This is a semantic boundary proposal, not an approved
overwrite span. Both descriptor masks must validate because effect preparation
can change the later branch flag. Do not preflight only the currently selected
mask and assume `$AE94` cannot change.

The preflight needs an immutable, explicitly bound action-config/package
association, legal source bank, bounds and complete token ownership, and the
same decoded flat-stream exclusions as the existing package validator. It
must also validate the fixed-bank auxiliary selectors or use an independently
approved auxiliary adapter. A package-only check cannot protect unsafe
action/config readers that precede or follow it.

For a diagnostic using a canonical action ID with only its package mapping
adapted, a rejection could preserve the expected CPU/stack state and transfer
to the existing `$C1:BC5A` finalization path before effect preparation. That
path already receives a vanilla target-validation failure. However, this
proposal is conditional on proving these inputs at the new boundary:

- `$B18C` is a valid action ID for every finalizer table reader.
- `$B2EA/$B2EB/$B2EC`, `$B1BE`, `$B3F4`, and the queue record/partner fields
  are valid for the existing seven-PC command and participant schemas.
- The earlier target-list and mask work has no gameplay effect requiring
  rollback, and pending result work cannot leak into a later action.
- The helper restores the exact caller ABI and current stack, and it touches
  no unrelated queue record, MP word, effect result, or script owner.
- Both the rejected command and any participating partners become available
  according to an explicitly stated timing policy.

These inputs are not established for Schala's new logical PC `$07` or proposed
action IDs `$80-$90`. The native finalizer itself indexes canonical action
tables with `$B18C` and maps participants through existing PC data. It must not
be reused for a high action ID simply because a canonical donor Tech can use
it. Package selectors `$80-$8F` remain a separate namespace.

The original resolver helper should still refuse an invalid descriptor without
publishing. With immutable ROM-bound package data, an earlier identical
preflight can reduce the expected late-refusal cases, but that is not a proof
that a late refusal cannot occur. A future production design must name how a
disagreement, corrupted state, or invalid caller exits the action transaction.
For now such a disagreement is an experiment failure with private evidence,
not a condition that a diagnostic silently papers over.

## Mapping correction: the named refund helper is a shared finalizer

Proposed correction ID: `BA-MAP-SHARED-TECH-FINALIZER-20260908`.

The pinned upstream
[bank_C1.asm:23863](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L23863)
describes `$C1:BDB3` as `action failed/cancelled` and calls its timing work a
`partial gauge refund`. The symbol `Battle_CancelPcActionRefundAtb` repeats
that interpretation. The failure-only reading is contradicted by the canonical
success fallthrough at `$C1:BC56-$C1:BC60`: the successful result-table clear
returns directly to the same call at `$C1:BC5A`.

The corrected, narrower description is **shared queued-Tech participant and
timing finalization**, reached on both success and failure. Its first
participant path clears command fields, reloads timing fields from `$B158`,
applies status adjustments, then scales those fields using a Tech-table
nibble. The arithmetic does not establish restoration of a previously
captured gauge value or MP refund. This audit does not assert a new complete
meaning for every timing field.

Independent canonical provenance:

| CPU range | Bytes | SHA-256 |
| --- | ---: | --- |
| `$C1:BC4A-$C1:BC60` | 22 | `2258622ba95551f41347b852f03148795064fb55c5932ae7b92b40f3fa6e4f70` |
| `$C1:BDB3-$C1:BF46` | 403 | `b3281d8212fb9d53d70068adff23d3281d86defa936fc07174fb07c79f4c15bc` |
| `$C1:BCF8-$C1:BD6F` | 119 | `6ce9e5574a0c6892a773ed1da81b03069c5ba47c68cb9b53e257eac9830c1aab` |

Evidence level: `verified-static`. The annotation source is preserved
unchanged. A corrected name here does not make the routine a ready-made
Project Epoch cancellation API.

## Next experiments and pass conditions

1. Extend a read-only ordinary-action observer upstream. Capture target
   validation return `$C1:BB8B`, pre-effect boundary `$C1:BBD4`, each MP
   deduction entry/return, `$C1:AC57/$AC5A`, result application, and the shared
   `$C1:BC5A/$BCF8` finalizer. Record full CPU/stack context, the exact queue
   record and participants, current HP/MP/status, result-buffer identities,
   and existing animation-latch observations. The pass must establish which
   invocation each effect/charge belongs to; preceding enemy work is separate.
2. Capture a natural early queued-Tech failure if an ordinary reproducible
   checkpoint supports it, such as a target or participant becoming invalid
   after selection. Record the exact reason and branch; do not relabel an
   injected flag as normal play. Verify no new MP-deduction or result-commit
   call occurred and observe the actual queue/partner and timing finalization.
3. Only after those captures, build a source-only preflight planner for a
   canonical diagnostic donor. Require whole-context validity, both package
   masks, auxiliary-reader eligibility, and an explicit rejection result.
   Test malformed descriptor and inconsistent participant/queue inputs as
   refusal cases without creating a live production mapping.
4. A later isolated native diagnostic may compare ordinary success against
   deliberate preflight rejection. It must declare all injected state as
   diagnostic, retain clean input hashes, prove exact permitted writes and
   unchanged unrelated HP/MP/status/queue records, observe normal next-command
   progression, and preserve failure artifacts. Any ROM mutation remains
   subject to the existing intent/full-diff guard and its exact scope rules.

The late loader refusal remains open until an explicit transaction-level
failure policy is selected and proved. Completing the earlier preflight
experiment does not by itself approve expanded code placement, game scratch,
interrupt ownership, high package binding, or logical PC `$07` integration.
