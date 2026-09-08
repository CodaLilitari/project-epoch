# Canonical-donor package preflight planner design v1

Date: 2026-09-08. Status: design for independent review; no planner implementation
or native installation is claimed. The intended implementation has a
`verified-static` ceiling and produces metadata only.

This design advances step 3 of the
[cancellation contract](schala_package_cancellation_contract_v1.md): check an
immutable authored primary package before queued-Tech effect preparation. It
uses the accepted successful Luminaire transaction and the accepted naturally
refused Cure transaction as two different context contracts. It does not turn
the latter into evidence that a new rejection at a later boundary can safely
reuse vanilla cleanup.

A passing package decision means that its declared descriptor and direct
streams satisfy the existing transport policy. It does not mean that the
package can finish an action. In particular, the existing terminal-only `$00`
symbolic stream does not establish the `$9876/$5D9B` completion protocol. The
separate completion design must resolve that before any game experiment.

## Existing evidence and boundaries

| Evidence | What is reused | What it does not establish |
| --- | --- | --- |
| [Successful transaction v1](schala_package_transaction_observation_v1.md) | A supported canonical action `$08`, target-validation return, exact pre-effect `$C1BBD4` state, later MP/effect/resolver/result/finalizer ordering | A high package, injected refusal, general MP eligibility, or cleanup from a new boundary |
| [Natural Cure refusal v1](schala_package_natural_refusal_observation_v1.md) | Same queued action `$0C` selected while its target was alive, subsequent target death, `$AF23=1`, no preparation or charge in that invocation, shared finalizer, queue release and later readiness | A Cure invocation at `$C1BBD4`, a package failure, late refusal or rollback |
| [Cancellation static packet](../references/package_cancellation_boundaries_v1.json) | Canonical instruction spans for the proposed pre-effect boundary and shared finalizer | A complete write/read dependency closure for a newly introduced rejection |
| [Natural-refusal static packet](../references/package_natural_refusal_boundaries_v1.json) | Canonical queue, death/status, selected-target failure and ready-list instructions | General target semantics or complete battle-state ownership |
| [Symbolic package v0](schala_symbolic_high_package_v0.md) | Immutable original descriptor/terminal stream and explicit synthetic selector `$80` mapping | A production allocation, action completion or Schala binding |
| [Flat-direct policy v0](schala_expanded_package_command_policy_v0.md) | Both masks, bank-qualified pointers, token ownership, shared suffixes and decoded-command exclusions | Gameplay semantics of every allowed opcode or completion behavior |

The initial symbolic donor `$01` remains unchanged. This design creates a new,
explicit diagnostic association with observed canonical donor `$08`; it does
not revise or silently reinterpret the completed donor-`$01` artifact.

The successful trace SHA-256 is
`fc9e89c139d00a23ab67a84ee77f497e6dfe63133c14509b23f50ce72d0523e7`.
The natural-refusal trace SHA-256 is
`63f94fff2b81292b593073e1197b7a8b8778cf6f4b217e2caa02adb0d61efd15`.
Their acceptance references are respectively
[`package_transaction_observation_v1.json`](../references/package_transaction_observation_v1.json),
SHA-256 `1cc3030e1bbfe5f167ae69262ec7d78487ec4184e3500915b9dfbda94bea2787`,
and
[`package_natural_refusal_observation_v1.json`](../references/package_natural_refusal_observation_v1.json),
SHA-256 `a1318f53d2db33e73288da2c7a1faf8765da58b8696f47441afdcbcf0352114c`.
Those are checkpoint-bounded observations with prepared SRAM provenance and
controller-only behavior after the exact accepted state load.

## The two context contracts

The evidence importer must first revalidate each full accepted trace through
its pinned existing metadata collector and strict validator. It then extracts
the declared record indices and binds their canonical JSON hashes to the full
trace identity. A caller-provided `verified` flag, record kind, address or hash
cannot substitute for that process. The public report emits selected metadata
and hashes; raw snapshots and reconstructed game bytes stay private/in memory.

### Successful canonical donor context

Profile: `observed-lavos-luminaire-pre-effect-v1`.

The accepted trace's record 9 is the pre-execution snapshot at `$C1BBD4`, poll
374. Its canonical JSON SHA-256, using sorted keys and compact separators, is
`b9ddf0bea98b713a8b13cbc89540c4f3f71fc23e2547909054b4c8112b2b6fa5`.
It must be paired with queued entry record 5 and target-validation return
record 8 from the same accepted invocation. No field is supplied from a later
resolver or an earlier enemy action.

Required facts include the exact first queue record at `$7E93EE`, its `$08`
action byte, command flags `$20`, copied menu field `$01`, selected target
field `$03`, and observed participant descriptor. DP `$06/$07` selects that
same queue record. `$B18B=0`, `$B18C=$08`, resolved logical participants are
`[00, FF, FF]`, and the logical-PC-to-battle-slot map is the observed
`[00, 01, 02, FF, FF, FF, FF]`. At this boundary `$AE91/$AE92/$AE93/$AE94`
are `[00, 02, 08, 00]`; the first value is a battle slot, not a second logical
PC identity. The actor, participant map, action-config row and queue fields
must agree before a package is considered.

The CPU boundary is native mode, PBR `$C1`, PC `$BBD4`, D `$0000`, DBR `$7E`,
SP `$06EA`, M=1, X=0, A=0, X=0, Y=3, P=`$22`. The processor decimal flag is
therefore clear independently of direct-page D. All 16 sampled stack bytes,
including the outer near return `$85D0`, remain bound to the accepted record.
This is a host context constraint, not a proposal to allocate those stack bytes.

`$AF23=0` here is the target-validation result. `$B3C8=0` is an observed field;
it does not prove that the upcoming MP/status validation has already run.
The canonical call at `$C1BBD4` enters `$C1BF79`, then `$C1D523`; the later
`$C1D573` call performs participant/MP validation. Package preflight must not
replace that native check or move MP/effect work earlier.

### Already refused canonical context

Profile: `observed-lavos-cure-target-refusal-v1`.

The natural-refusal trace's record 117 is the pre-execution target-validation
return at `$C1BB8B`, poll 2560. Its canonical JSON SHA-256 is
`b798a62edf5e1eee2d469e47866ec69b149351daa66706e345cd7a37e10fb0bb`.
It is paired with queued entry record 110 and the accepted trace's selection,
death, `$AF23` write/readback and exact cleanup witnesses.

This context selects the second queue row at `$7E93F5`, action `$0C`, target
slot 2, `$B18B=1`, `$B18C=$0C`, resolved participants `[01, FF, FF]`, and the
same observed logical-PC-to-slot map. Its native return frame has outer saved
word `$85E9`. `$AF23=1` records the selected-dead-target rejection.

The animation fields still belong to earlier work: `$AE91=3` and `$AE93=0`
at this target-validation return. They are not a Cure actor/config pair.
Even the successful action's `$C1BB8B` snapshot precedes its new animation
identity setup. The importer must not normalize those fields to the desired
action or confuse initial target-validation participants with the later
resolved set.

The result for this profile is `native-target-refusal-observed`, with package
and donor eligibility marked `not-evaluated`. It preserves the observed early
short circuit. It supplies no adapted config, no publication plan and no cleanup
instructions. A package request attached to this profile is an invalid request;
the caller may not use an already-refused invocation to certify that package.

There is no `$C1BBD4` record for this Cure invocation. Manufacturing one by
changing `$AF23`, copying the successful registers or combining snapshots is
forbidden. Mutated host fixtures are explicitly synthetic and cannot acquire a
runtime evidence label merely by matching some fields.

## Immutable donor and explicit diagnostic association

The importer reads the exact headerless US Rev0 ROM in memory: 4,194,304 bytes,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
It reuses the canonical package-adapter table and reader pins before selecting
physical action-config row `$08` at file `$0D45DE-$0D45E5`, half-open, from
the seven-byte-row table starting at file `$0D45A6`.

| Content | SHA-256 |
| --- | --- |
| Canonical row `$08`, seven bytes | `044dfdb673f9506789daf42470a7d5173f70354169f6ecc5006235783a46b334` |
| Preserved row bytes `+1..+6` | `642eb9302b2906890aceb5baf58a28e11dfdaff1ed15d1233db7c401bb5f1a96` |
| Candidate row with only `+0` replaced by `$80` | `9c747786b110ff2b63c293e3cacefa0fb84e436f48257cd139742e0a339dbf3e` |

The canonical first byte is itself selector `$08`. Numeric equality of action
and selector does not create the new association. A diagnostic request must
explicitly bind all of these separate fields:

- canonical queued action ID `$08` and physical config donor row `$08`;
- the exact donor hash and preserved-suffix hash;
- authored primary package selector `$80`;
- the exact immutable synthetic source, bank-qualified root and named layout;
- the pinned command policy/interpreter dependencies and content certificate;
- the exact supported context profile and `synthetic-test` source kind.

Use immutable bytes, frozen records and immutable tuple mappings. Reject mutable
buffer views, duplicate keys/selectors, boolean-as-integer substitutions,
unknown fields and unrecognized namespace/source-kind values. The default
high-selector registry stays empty. Neither action `$80-$90` nor logical PC
`$07` is accepted; participant `$FF` remains an absent-position sentinel and
does not become a logical character. All other donor/action/profile pairs
remain unsupported in this version, even when they are valid vanilla content.

The first positive candidate reuses the exact original symbolic source at
synthetic `$42:2000/$42:3000` under a newly explicit local association. The
original symbolic auditor and donor-`$01` proof are unchanged. These addresses
remain test identities; they are not a production allocation or a game image
input. The planner offers no ROM image, patch, assembly, emulator or install
option.

## Both masks and auxiliary eligibility

The planner reparses the exact immutable source with the existing pinned
flat-direct command policy. It does not trust a supplied certificate in place
of recomputation. Both masks and every selected direct or suffix entrypoint
must pass before it can return a transport decision, regardless of the current
`$AE94/$A0B3` branch. Effect preparation can produce the alternate branch
later; predicting the currently observed branch is insufficient.

Keep the policy's exact descriptor extent, bank-end handling, pointer
endianness, sparse owner positions, shared-token agreement, full named-stream
ownership and terminal `$00` requirements. Decoded `$1E/$1F/$21` remain
forbidden, as does sticky/default `$01` under the unchanged v0 profile. An
operand equal to `$1E` is not itself an excluded command. A broken alternate
branch must reject even if the primary branch is valid.

Auxiliary eligibility is narrowly `canonical-donor-equality`, not a new bank
adapter. The candidate must equal donor `$08` at every byte `+1..+6`, including
the independent auxiliary selectors `+3/+4/+5`; any difference rejects before
package evaluation can pass. Reconstruct these bytes from the pinned ROM,
never from an extracted source-controlled literal or a live stale config block.

The canonical reader at `$C145BB-$C145EC` distributes the seven row bytes to
`$9877`, `$987A`, `$987B`, `$987E`, `$9881`, `$9884`, `$987C`. It does not
write a contiguous seven-byte block. At `$C145F3/$C145FF/$C1460B`, the later
auxiliary lookups still use fixed `$D1/$CD/$CE` families before the primary
resolver. The completed transaction trace did not snapshot every destination
or independently record all seven CPU row reads. Accordingly the new donor
equality proof is source-derived; it must not be described as a new complete
runtime auxiliary-read observation.

Retaining donor values establishes eligibility for this bounded source model.
It does not prove compatibility of that donor's auxiliary animation with the
terminal-only authored primary stream, new graphics, a different actor, an
expanded auxiliary bank or action completion.

## Proposed host API and decision order

Separate evidence import and policy evaluation from the pure context function.
The read-only auditor owns private-file access and evidence pins. The pure
function receives immutable typed context, donor and association objects and
performs no file access, writes, callback registration or CPU execution. A
successful candidate context returns `requires-package-policy-validation`
bound to exact source/layout hashes; that intermediate result is not a
transport certificate.

The existing policy validator reads its pinned dependency files. Keep that
unchanged implementation in the read-only auditor, outside the file-free
context function. The auditor must recompute policy checks on the exact
immutable source named by the qualified request before it can emit a final
transport decision. It cannot accept a caller-supplied policy certificate or
enable a skip-validation option. Evidence origin is kept outside the generic
context function: passing an independently constructed host object is at most
a synthetic host result, not authentication of a captured runtime state.

The deterministic order is:

1. Validate exact schema, types, lengths, profile and native boundary identity.
   Reject malformed queue rows, actor/action namespaces, unmapped or duplicate
   participants, invalid absent positions, mismatched queue pointers and
   conflicting source or invocation identity. Version 1 then requires the
   complete declared snapshot profile; it does not generalize to all rows,
   parties, dual/triple Techs, valid alternate targets or stack contexts.
2. For the already-refused profile, require the accepted refusal contract and
   absence of a package request; return `native-target-refusal-observed`.
3. For the successful profile, require the accepted pre-effect contract and
   exact donor row reconstructed from the pinned canonical input. A
   `canonical-baseline` request returns `canonical-path-preserved` with no
   replacement and no authored-package grammar assertion about vanilla data.
4. For `diagnostic-primary-substitution`, require the complete explicit local
   association. No mapping returns `unbound-diagnostic-package`; no implicit
   fallback to a canonical pointer is permitted. Validate all donor bytes and
   auxiliary equalities, then return the qualified policy request. The
   read-only auditor independently validates both descriptor branches and all
   owned streams under the pinned policy, requiring exact source/layout
   equality with that request.
5. The auditor emits `transport-valid-source-only` only after every check passes. Include
   content/contract hashes and the explicit fields `production_approved=false`,
   `native_cleanup_approved=false`, `action_completion_approved=false` and
   `runtime_integration_proved=false`.

Input errors and unsupported contexts return explicit, deterministic refusal
reasons or a typed validation exception with no partial certificate. Distinguish
`malformed-context`, `unsupported-context`, `source-drift`, `donor-mismatch`,
`auxiliary-mismatch`, `unbound-diagnostic-package` and `package-policy-refusal`.
Do not return WRAM writes, a jump/return address, a refund plan, a queue clear
or a claim that a rejected game action has been completed.

## Planned source and verification deliverables

After independent design review, use new files only:

- `tools/schala_package_preflight_planner_v1.py`: immutable schemas and pure
  context/donor decisions, including qualified policy requests; no native
  execution, file access or output mutation.
- `tools/audit_schala_package_preflight_planner_v1.py`: read-only pinned evidence
  and ROM importer, mandatory existing-policy recomputation, source-only
  matrix and payload-free stdout report.
- `tests/test_schala_package_preflight_planner_v1.py`: host adversarial controls.
- `references/schala_package_preflight_planner_v1.json`: deterministic metadata
  identity and exact implementation/evidence dependencies, created only after
  implementation review and successful reproduction.

At minimum, tests must reject every preserved donor-byte mutation; changed
action/row/selector association; absent binding; logical PC `$07` or high action
IDs; participant/map/queue mismatch; unknown or duplicate schema fields;
boolean integers; forged boundary or cross-invocation frames; late resolver
snapshots; a refused context relabeled as pre-effect; a valid primary mask
paired with a broken alternate mask; decoded `$1E`; mid-token suffixes,
overlap, unowned bytes or out-of-bank extents; and policy/source/reference
drift. Independently valid raw operand `$1E` must retain the existing policy's
accepted result. Existing symbolic and policy suites supply their completed
general transport coverage and remain unchanged.

The two accepted contexts must reproduce distinct deterministic decisions.
Canonical baseline and explicit diagnostic substitution must be distinguished;
all default high bindings remain absent. A test must show that changing a
completion claim to true is rejected even for a transport-valid source. No
test may infer MP sufficiency from the current `$B3C8` snapshot or manufacture
a new runtime label from synthetic fixtures.

Read-only imports must use bounded regular-file reads, strict duplicate-key
JSON decoding and exact current/archived source identities; arbitrary output,
runtime, profile and checkpoint selection are unnecessary. Reproduce the final
metadata byte-for-byte and verify immutable inputs before/after. Keep raw game
data, traces and adapted donor bytes out of stdout, references and Git.

## Remaining native obligations

This design approves no hook at `$C1BBD4`, `$C14612` or any other site. A later
native preflight needs independently proved ABI, timing, interrupt/stack policy,
named placement and an exact complete-diff write contract. The immutable
package association must remain identical between preflight and later helper
use. Equality of ROM bytes reduces that particular drift risk; it does not
prove context immutability, eliminate hardware errors or make late failures
semantically recoverable.

The natural refusal starts before the successful route's `$AE90/$AE94`
initialization, participant-to-actor mapping, `$AECB/$AECC` work and target-mask
calls. A newly rejected package at `$C1BBD4` has already passed those steps.
The accepted observers have declared watched-memory ledgers, not full WRAM
ownership or a proof that these different earlier writes are interchangeable.
The shared `$C1BC5A` tail is therefore still a conditional future cleanup
candidate, not an output or approved action of this planner.

Keep late helper refusal as an explicit failed experiment pending a separate
recovery design. Neither returning from the animation loader, clearing a
latch, restoring MP nor redirecting to the shared finalizer is implemented
here. The separate action-completion policy must also reconcile authored
stream termination with the caller's actual latch requirements. A passing
transport certificate cannot close either obligation.
