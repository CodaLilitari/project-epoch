# Project Epoch developer log

This is the human-readable history and handoff index for the Schala eighth-PC
work. It records completed work, its evidence ceiling, corrections, and the
next bounded step. Exact machine-readable identities live in the linked
references and checkpoints. The [developer guide](schala_eighth_character_developer_guide.md)
explains the architecture; the [correction register](DATA_MAPPING_CORRECTIONS.md)
explains which earlier claims no longer apply and why.

## How to resume and maintain this log

1. Read the newest dated entry, the current milestone in `AGENTS.md`, and its
   linked checkpoint. Verify input and source hashes before relying on a
   frozen experiment. A checkpoint is a historical snapshot: later changes
   to a living document do not invalidate the old experiment, but they do
   mean that document no longer matches the old snapshot.
2. Append a dated entry for each completed milestone or material change in
   direction. Include the concrete result, evidence level and scope, exact
   verification, unresolved issues, and next step. Do not turn a plan into
   a result when copying it forward.
3. Distinguish `planned`, `in-progress`, `implemented`, `verified-static`,
   `verified-runtime`, `committed`, and `pushed`. A local commit is not a
   GitHub update; an accepted push is not proof of anonymous visibility.
   Record the commit and remote verification when publication occurs.
4. Add a stable correction ID when evidence contradicts a prior map, source
   annotation, test oracle, or project statement. Link the exact old revision
   and the counterexample or supporting reader. Keep dated reports and
   recovered artifacts unchanged; supersede them explicitly.
5. Keep raw ROMs, SRAM, states, extracted assets, emulator binaries, and raw
   traces in ignored local storage. Publish original source, reproducible
   tests, addresses, hashes, metadata, and conclusions. Every new generated
   artifact needs its source identity, reproduction steps, and evidence level.
6. Re-run completed experiments only when source drift, a new failure, or a
   newly identified boundary warrants it. A smaller smoke or subset never
   substitutes for a previously declared full matrix.
7. Write tracked text and metadata explicitly as UTF-8 with LF newlines, as
   required by `.gitattributes`. Compute publication hashes from the bytes
   Git will store. If a historical local file used another newline encoding,
   retain the old checkpoint and document the conversion in a new receipt.

## Repository history through 2026-08-31

This summary was reconstructed from actual Git history on 2026-09-08. Dates
below are commit dates in the repository's recorded local offset, not an
inferred date of original research. Documents imported into the initial
baseline can describe work from before the repository existed. Their dates
must not be converted into invented commits or fresh verification.

| Commit date | Recorded work and durable boundary | Exact Git history |
| --- | --- | --- |
| 2026-08-22 | Established the research baseline and then added the animation contract, location-event operand census, battle-package topology, and fail-closed bank-qualified package contract. These are separate evidence scopes; their existence does not establish an eighth playable PC. | [Baseline `a01ab3a`](https://github.com/andreipemberton/project-epoch/commit/a01ab3a), [animation `cf62432`](https://github.com/andreipemberton/project-epoch/commit/cf62432), [events `0388114`](https://github.com/andreipemberton/project-epoch/commit/0388114), [packages `d998a6f`](https://github.com/andreipemberton/project-epoch/commit/d998a6f), [adapter `62e86af`](https://github.com/andreipemberton/project-epoch/commit/62e86af) |
| 2026-08-22 | Added the private canonical-ROM-derived Schala provider and hardened its promotion rules. Extracted bytes remain private and the supported-slot diagnostic cannot establish logical PC `$07`. | [`c9f65f7`](https://github.com/andreipemberton/project-epoch/commit/c9f65f7), [`d72e61b`](https://github.com/andreipemberton/project-epoch/commit/d72e61b) |
| 2026-08-23 | Recorded art/prototype provenance, Project Schala build recovery, historical eighth-character mapping, and recompilation research. Corrected the earlier ct-recomp ROM-presence statement and pinned the PC7 reserve-XP boundary. These are historical research and bounded audit results, not imported implementation. | [History from `86002ea` through `d35aafb`](https://github.com/andreipemberton/project-epoch/compare/d72e61b...d35aafb), [ROM-presence correction `b251f88`](https://github.com/andreipemberton/project-epoch/commit/b251f88) |
| 2026-08-24 | Published the corrected character-data map, verified the private Schala-over-Lucca provider replay, and recorded the remaining battle-command gates. The supported Lucca path remains distinct from an additive eighth slot. | [Map `b63cb1f`](https://github.com/andreipemberton/project-epoch/commit/b63cb1f), [replay `04481c7`](https://github.com/andreipemberton/project-epoch/commit/04481c7), [gates `85ba03e`](https://github.com/andreipemberton/project-epoch/commit/85ba03e) |
| 2026-08-31 | Added the bounded Mesen MCP adapter; completed the canonical battle-command grammar census and the decoded-`$1E` exclusion policy for new flat direct packages. The census covers 2,173 direct and 59 fixed-`$CE` nested entrypoints. No production high selector was bound. | [MCP `50ca603`](https://github.com/andreipemberton/project-epoch/commit/50ca603), [grammar `9bf8a47`](https://github.com/andreipemberton/project-epoch/commit/9bf8a47), [policy `cd0c9bc`](https://github.com/andreipemberton/project-epoch/commit/cd0c9bc) |

The last committed baseline at the start of the September 8 resumption was
`cd0c9bc1204705e63685a22aecd168fd10021979`. Git history itself is the source for
the chronology above; the corresponding audit documents supply the scope
and evidence behind each result.

## 2026-09-08 — mapping review and symbolic high package completed

**Status:** completed source-only proof, `verified-static` and deterministic
host verification. No emulator was used in this stage.

Recovered the prior handoff and audited the corrected map and current battle
contracts before extending them. All 21 canonical graphics, assembly, and
primary-animation windows matched their recorded bounds, sizes, and hashes.
The audit found an actual host-model defect: a descriptor ending at physical
bank offset `$10000` also returned that impossible value as native 16-bit X.
The physical extent now remains `$10000`, while X wraps to `$0000`.
Boundary tests cover both branches, exact ends, and overflow. The endpoint
notation and growth-versus-record wording were also clarified. See
[MAP-001 through MAP-003](DATA_MAPPING_CORRECTIONS.md).

Completed `BA-SYMBOLIC-HIGH-PACKAGE` with one original terminal-only package
under a local test binding for selector `$80`. Its named synthetic descriptor
and stream spans establish test identity, not production allocation. The
test reconstructs canonical action-config row `$01` from the hash-pinned ROM,
changes only byte `+0`, and proves exact preservation of `+1..+6`. It exercises
both masks over all 256 branch-byte values. All 128 canonical selectors remain
equivalent; all 16 default high selectors remain unbound. The donor does not
assign Schala effect semantics and the terminal stream does not prove an
animation.

**Verification recorded at this checkpoint:** 24 focused symbolic tests
passed; the project suite ran 1,012 tests with 990 passes, zero failures, and
22 explicit skips; 191 Python sources compiled in memory. The independent
review reproduced the symbolic report and found no additional blocker.

**Evidence and reproduction:**

- [Independent mapping audit](mapping_independent_audit_2026_09_08.md).
- [Symbolic package contract and commands](schala_symbolic_high_package_v0.md).
- [Frozen resumption checkpoint](../references/resumption_checkpoint_2026_09_08.json),
  exact-file SHA-256 `e3e5d70aa7e8d2c1167be348d321c7f4ff24bcff287f6d666fd6ff05d541c0a2`.

The next step at that checkpoint was native execution of an original helper.
That step was subsequently completed below. Preserve this checkpoint as the
earlier source-only snapshot.

## 2026-09-08 — public tooling and strategy refresh completed

**Status:** `documented`, dated source inspection. This entry records the
bounded search already performed; it does not assert that all private or
unindexed work was found.

The refresh found activity in Temporal Redux, ctrando, and general SNES
recompilation tooling, but no newly verified complete Chrono Trigger
decompilation or reproducible additive eighth-PC release in the inspected
sources. ctrando's August 26 change now preserves sparse object positions,
so our older role-count criticism must not describe that newer implementation
([MAP-004](DATA_MAPPING_CORRECTIONS.md)).

Official Super Famicom development tools are documented, but no public,
buildable retail Chrono Trigger source or Square character-authoring kit was
verified. The research did not acquire leak archives or game data. The
strategy remains targeted SNES extensions with executable component gates.
The original Mesen repository's move to Community Edition is recorded as a
future tooling consideration; the evidence emulator stays pinned.

**Evidence:** [online refresh](online_research_2026_09_08.md) and
[development-tools assessment](development_tools_strategy_2026_09_08.md).
Their pinned source URLs and inspection boundaries are the authority for
these time-sensitive observations.

## 2026-09-08 — native helper conformance completed

**Status:** `BA-NATIVE-HELPER-CONFORMANCE` complete at `verified-runtime`,
strictly synthetic scope.

Authored an original 537-byte 65C816 helper and an isolated Mesen collector.
The helper's registry accepts diagnostic WRAM source banks `$7E/$7F` only.
The runner assembles a raw `norom` binary and loads original code and test
fixtures into disposable WRAM while using an existing original benchmark
cartridge. This stage does not run Chrono Trigger or mutate a cartridge.

Three full runs passed 879 cases each: 471 high-path successes, 216 refusals,
and 192 canonical cases per run. Two at `$7F8000` yielded identical raw traces;
a third at `$7F9000` passed the same contract. Final CPU state, exact ordered
publications, complete WRAM differences, preserved return state, and input
hashes passed. The matrix includes the MAP-001 exact-bank-end regression.
The recorded instruction fields count collector callbacks, including the
terminal observation; they are not cycle or game-timing measurements.

**Verification recorded at this checkpoint:** 30 focused harness tests
passed. The complete suite ran 1,042 tests: 1,020 passes, zero failures, and
22 explicit optional skips in 42.501 seconds. All 193 Python sources compiled
in memory. The 2,637 recorded native cases and evidence identities were
independently revalidated. These are the recorded results of this milestone,
not a claim that the suite was rerun whenever this log is read or edited.

**Evidence and reproduction:**

- [Native contract, matrix, hashes, and commands](schala_package_helper_conformance_v0.md).
- [Metadata reference](../references/schala_package_helper_conformance_v0.json).
- [Frozen native checkpoint](../references/native_helper_checkpoint_2026_09_08.json).
  Its declared canonical-JSON self-identity, excluding `artifact_identity`, is
  `c75a5ee41cf45f64941084e3ea483ddd601bf9d893b5a8bc165ceadb5ff16edc`.

The bounded Mesen MCP bridge remains available in the project, but these
specific runs used Mesen's Lua test runner, not MCP calls. No expanded-ROM
access, live resolver hook, game scratch ownership, game interrupt policy,
command execution, Schala action, or PC `$07` playability follows from this
result. No production high selector is bound.

## 2026-09-08 — live integration design and published handoff in progress

**Status at entry creation:** `in-progress`. The user authorized continuing
implementation, maintaining a human-readable history and correction record,
and updating GitHub so another developer can resume from exact state.

The current gate is `BA-NATIVE-INTEGRATION-DESIGN`. Work is addressing the
exact live resolver hook and continuation ABI, named expanded placement and
source-bank access, and scratch/interrupt ownership. The completed synthetic
conformance matrix will be reused unless a changed source or newly failing
boundary requires a new run.

This log and the correction register have been added as maintained handoff
documents. Integration results, newly executed checks, a new checkpoint, and
the actual commit/push outcome must be appended when verified. This entry
alone records neither a completed integration nor a completed GitHub push.

Publication preparation identified one metadata-format mismatch:
`references/schala_package_helper_conformance_v0.json` used CRLF locally,
while `.gitattributes` requires LF. The previous local file was 27,679 bytes,
SHA-256 `cc89531d1794edd8482988938ab6c4ae250f7cc743d5c76d9ac5ed0e30b2d2c8`.
The LF publication representation is 27,081 bytes, SHA-256
`492dfbb054ac2bc55253864a28fdbe9217bcb82553983133583da4b84698810e`.
This changes exact-file identity but no JSON value, internal source/tool/trace
hash, or runtime result. The earlier checkpoints retain their historical
local-byte identities; the new publication receipt must record the conversion.
This formatting correction does not call for another emulator run.

**Resume boundary:** production hook/allocation catalogs remain empty and high
selectors remain unbound until evidence is explicitly promoted. The original
helper's synthetic placements are not approved game addresses.

## 2026-09-08 — canonical primary resolver and action completion observed

**Status:** `BA-LIVE-RESOLVER-PRIMARY-OBSERVATION` completed at
`verified-runtime`, bounded to one ordinary canonical PC invocation repeated
in two fresh Mesen processes. `BA-NATIVE-INTEGRATION-DESIGN` remains open.

The unmodified game reaches actor `$00`, type `$02`, physical config and
package selector `$08`, branch `$0000`. The observed entry, tail, eighteen
ordered publication bytes, and return stack match the source model. SP moves
from `$06D8` to `$06DA` and `$06DC` as the two original near-call frames are
consumed. The same PC action later satisfies its completion reads at input
polls 991 and 992, before the next action starts. Two final traces each have
1,774 records and the identical SHA-256
`699776cf0d3c69fe13f7fbd7eb9240e47b56cc651395ac53cf15253c73b25190`.
Input-poll counts are not cycle or verified video-frame timing.

The first exploration missed the resolver because the new launcher omitted
the explicit controller setting; it remains a recorded non-proof. The second
reached the PC resolver but stopped before the action completed. Independent
review prevented an earlier enemy's completion from being credited to the
PC. A longer bounded capture and invocation-scoped checks resolved that
measurement issue; the final pair uses the corrected frozen sources.

**New findings:** the caller's completion latches make rejection/cancellation
a separate contract; a terminal-only stream is not sufficient lifecycle
evidence. Synthetic scratch `$7E4000` has a proved vanilla menu/overworld
collision. Five named expanded spans pass geometric validation but remain
unapproved candidates. The ordinary primary stack is observed; interrupt
headroom and temporary-memory ownership remain open.

**Corrections:** MAP-005 identifies the wrong upstream "8 slots" annotation
and the canonical thirteen possible owner checks. MAP-006 narrows our old
universal `JSL/RTL` instruction to distinguish a new long call from a `JML`
tail transfer retaining an existing near-call frame. The correction register
cites exact old revisions and the supporting canonical/native evidence.

**Verification:** 18 new synthetic-metadata tests pass, including exclusion
of earlier enemy completion and later action completion. The full project
suite runs 1,060 tests in 43.743 seconds: 1,038 pass, zero fail, and the same
22 optional cases skip. All 195 Python sources compile in memory. Twenty-one
canonical spans in the two design reports were independently rehashed; forty
private output files are bound by the runtime reference. No game hook, ROM
patch, or direct CPU/memory edit was used; the source ROM, SRAM, and saved
state files retain their exact input hashes.

**Evidence and reproduction:**

- [Read-only observation contract](schala_package_resolver_observation_v0.md)
  and [metadata reference](../references/package_resolver_observation_v0.json).
- [Resolver integration design](schala_package_resolver_integration_design_v0.md).
- [Placement and interrupt review](schala_package_placement_interrupt_review_v0.md).
- [Integration handoff checkpoint](../references/integration_checkpoint_2026_09_08.json).

**Publication already verified:** the prior audit, symbolic proof, and native
helper milestone were committed and pushed to `origin/main` as
[`9f14ae7f407ce783ada02b996db4e0955a5a5918`](https://github.com/andreipemberton/project-epoch/commit/9f14ae7f407ce783ada02b996db4e0955a5a5918).
Both the remote branch and GitHub commit API returned that exact identity.
The new observation and this log entry are a subsequent work increment;
their publication receipt will be appended after the push is verified.

**Resume here:** preserve the completed primary observation. Define the exact
refusal/action-cancellation cleanup and return contract; then prove the
ROM-source helper version, the ordinary alternate branch, and scratch/interrupt
ownership. Production catalogs and high selectors remain unbound. Do not
repeat the completed grammar, symbolic package, or native synthetic matrix
without source drift or a newly failing boundary.

**Sharing limitation observed during publication:** authenticated GitHub
reports `andreipemberton/project-epoch` as `PUBLIC` with admin access and
accepts the push. Anonymous requests to the repository page, repository API,
and commit-pinned raw README all return HTTP 404; an anonymous request to the
public Mesen repository API returns 200. This establishes an access
discrepancy, not its cause. Do not claim that unauthenticated readers can
retrieve the handoff until a later anonymous check succeeds. No repository
visibility toggle, account change, or alternate publication was attempted.

## 2026-09-08 — GitHub source publication verified

**Status:** committed and pushed to `origin/main`. The integration source,
runtime evidence metadata, developer history, correction register, and
updated guidance are published in
[`ac2b9a96ec816bbd33a4f69f40dedb8e865fdf0e`](https://github.com/andreipemberton/project-epoch/commit/ac2b9a96ec816bbd33a4f69f40dedb8e865fdf0e),
following the helper milestone
[`9f14ae7f407ce783ada02b996db4e0955a5a5918`](https://github.com/andreipemberton/project-epoch/commit/9f14ae7f407ce783ada02b996db4e0955a5a5918).

The remote branch and authenticated GitHub commit API returned the exact
integration commit. All fourteen files changed in that commit were fetched
through the authenticated contents API and matched the committed bytes,
sizes, and SHA-256 values. The
[publication receipt](../references/github_publication_receipt_2026_09_08.json)
records those identities and reproduction steps. This entry and the receipt
are a documentation follow-up; they do not change or rerun the pinned native
sources or test results.

Anonymous access still has the separately observed 404 limitation recorded
above. Therefore the verified claim is synchronization to the authenticated
repository, not confirmed availability to unauthenticated readers. The next
engineering work remains the explicit cancellation contract and the other
integration obligations in the preceding entry.

## 2026-09-08 — six-hour continuation started

**Status:** in progress, beginning at 14:58:41 UTC with a six-hour target of
20:58:41 UTC. Andrei acknowledged the account restriction and requested
continued engineering. The starting source is `f387a077052195df833b2984076a0962cf4aff72`.
The [session ledger](work_session_2026_09_08.md) records the time boundary and
active work streams. The completed primary observation and native v0 proof
are preserved; new work addresses cancellation, expanded-ROM access, the
ordinary alternate branch, and interrupt/temporary-state ownership.

## 2026-09-08 — cancellation boundary and bounded IRQ closure established

**Status:** two integration constraints completed at `verified-static` during
the six-hour continuation; no game adapter is installed.

The queued-Tech path deducts participant MP before the animation resolver
runs and applies prepared results after animation returns. A resolver refusal
cannot therefore be called complete action cancellation. The new
[cancellation contract](schala_package_cancellation_contract_v1.md) identifies
an earlier pre-effect preflight candidate and the exact existing failure
continuations. Reusing them still requires proof of the participant map,
queued command, finalizer eligibility, and caller state. The verifier passes
19 canonical span hashes and 32 selected instruction assertions, rejects
altered input, and reproduces the checked-in metadata exactly.

The [interrupt closure audit](schala_package_interrupt_closure_v1.md) follows
all conditional outcomes in the bounded direct battle-IRQ CPU graph. Its
401 instruction starts and 404 width contexts retain balanced near/long
return frames and keep IRQ masked. The maximum modeled stack use is 35 bytes
including the four-byte native hardware frame. This excludes NMI nesting,
data-dependent DMA sources, and global stack ownership. Fifteen focused
tests pass, including incorrect-width and invalid-return rejection.

**Corrections:** [MAP-007 and MAP-008](DATA_MAPPING_CORRECTIONS.md) identify
two wrong upstream annotations with pinned source links and canonical hashes.
The first mislabels shared success/failure finalization as cancellation/refund.
The second decodes two 16-bit immediate operands as apparent `$AAEB` writes.
The reports preserve the original sources and state exactly what the evidence
changes. No unrelated SRAM, graphics, or playable-PC mapping is promoted.

**Resume:** finish the interrupt-attributed runtime observation, confirm a
naturally selected alternate package branch, and complete the separately
versioned ROM-source helper proof. The original global scratch remains
unsuitable for game use; stack-owned temporary storage needs its own ABI and
interrupt proof. This increment's publication will be recorded after push.
