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

## 2026-09-08 — expanded-ROM reads and interrupt context reproduced

**Status:** `verified-runtime` in two separate bounded experiments during the
six-hour continuation. No production helper or eighth-character patch is
installed. The preceding static cancellation/IRQ increment is published as
[`8cdc06a830eaf2124b7aa7dbc1a47081bc21fda0`](https://github.com/andreipemberton/project-epoch/commit/8cdc06a830eaf2124b7aa7dbc1a47081bc21fda0),
with all eleven changed files verified byte for byte through authenticated
GitHub access. The [session publication receipt](../references/work_session_publications_2026_09_08.json)
records that completed synchronization.

The separately versioned [676-byte ROM-source helper](schala_package_helper_v1_rom_source.md)
passes two identical 1,454-case Mesen runs. It reads actual emulated ROM banks
`$41/$42` from the unchanged original SHA benchmark, preflights both masks and
every direct target, and publishes the expected bank-qualified entries.
Each run retains 1,049,158 observed PCs and 543,631 CPU data reads, including
26,690 exact ROM-source reads. Final CPU state, ordered publications, complete
WRAM differences, input snapshots, and source/staged hashes pass. These are
original descriptor-shaped byte fixtures; their pointed bytes are neither
executed nor certified as battle commands. Code and scratch remain synthetic
WRAM placements, so real ROM code placement and game ownership remain open.
The [current reference](../references/schala_package_helper_v1_rom_source.json)
preserves all earlier attempts and the exact pre-execution-guard reference.

Review found an observation gap in the first execution-guard attempt:
Mesen executes a `setState` redirect's first opcode without another callback.
A separate original JML setup bridge makes the helper's first instruction
observable. The accepted pair covers the complete helper interval. The
helper assembly stayed unchanged, and all four old/new CPU/read/write/state
projections match. The report also preserves the earlier endpoint-carry bug,
its correction, and the prepared-only metadata serialization failure.

The [clean-ROM context observation](schala_package_resolver_context_v1.md)
also repeats exactly. Each run has 11,905 records and 2,402 paired handler
entries/pre-RTI snapshots with preserved registers and hardware return frames.
A PC-scoped NMI scene clear has a pre-instruction snapshot, actual zero write,
post-write readback, and later caller read. The earlier enemy clear is excluded.
No interrupt enters the short canonical resolver interval: 4,244 emulated
master clocks and 548 CPU-cycle-counter increments. Recorded SP minima are
samples, not a proved stack floor. The [reference](../references/package_resolver_context_v1.json)
and read-only metadata collector reproduce these identities without another
emulator run.

**Review and validation:** the two new host suites pass all 62 tests. The
root independently regenerated the context reference byte for byte and
reviewed both reports. The [independent review receipt](schala_package_integration_review_receipt_2026_09_08.md)
records source checks, exact artifact identities, the complete-execution
fix, and the IRQ latency correction. Mesen's generic clock is 32 bits;
intervals now use its full serialized counter. A proposed universal saved-I=0
IRQ rule was withdrawn after source review because a previously sampled IRQ
can survive SEI. These are diagnostic-tool refinements, not new canonical
character-data contradictions.

**Resume:** the [separate stack-frame design](schala_package_stack_frame_design_v2.md)
defines 42 bytes of locals and a 52-byte maximum helper contribution. Its
implementation and deliberate-interruption proof are separate next results.
The full normal-NMI tree, actual game stack headroom, immutable production
registry, guarded placement, and transaction-level cancellation remain open.
A natural Black Hole/Spekkio alternate-branch exploration has succeeded and
is being converted to a fixed, reviewed replay. This increment's own push
will receive a subsequent verified publication entry.

## 2026-09-08 — alternate resolver and bounded normal-NMI contracts

**Status:** the alternate resolver is `verified-runtime` within the exact
imported-save checkpoint and fixed controller replay; the NMI result is
`verified-static` within its explicitly bounded paths. The preceding runtime
increment is published as
[`afdf85610b078bbc2452ddf360e81b051dc78fb7`](https://github.com/andreipemberton/project-epoch/commit/afdf85610b078bbc2452ddf360e81b051dc78fb7).
Authenticated GitHub branch, commit and all twenty changed-file bytes were
verified. Its receipt is retained in the
[session publication history](../references/work_session_publications_2026_09_08.json).

The [alternate observation](schala_package_resolver_alternate_v1.md) now repeats
with 3,783 byte-identical CPU/data-flow records. Magus's Black Hole targets
Spekkio, takes the canonical boss-immunity branch, and writes `$AE94=$40`.
The observed resolver then reads selector `$37` and branch `$0040`, publishes
42 bytes in the expected order, preserves its return chain, and reaches both
completion conditions within the same action. Later action cleanup is outside
that lifetime. The [reference](../references/package_resolver_alternate_v1.json)
revalidates both traces, current frozen sources and private inputs without
rerunning the emulator. Its documentary screenshots differ; CPU/data-flow
reproducibility is accepted without a pixel-reproducibility or renderer-cause
claim.

Checkpoint provenance matters here. The SRAM is byte-identical to the archived
Outrunner save; the historical collector imported that SRAM before navigating
to the talkable Spekkio checkpoint. The accepted new replay loads that unchanged
checkpoint and uses controller input afterward. It does not inherit the later
event-grant/canary profiles or claim fresh-New-Game progression. This is an
ordinary completed immune-target action, not a cancellation proof.

**Mapping correction:** [MAP-009](DATA_MAPPING_CORRECTIONS.md#map-009--black-holes-nonboss-comparison-accepts-equality)
cites the older disassembly's incorrect strict-threshold comments. The canonical
nonboss comparison accepts equality before its survivor branch. Eight selected
instruction assertions and all 65,536 original byte-pair cases reproduce the
inclusive predicate. The Spekkio runtime path bypasses that comparison, so
its evidence is deliberately kept separate from the static equality proof.

The [normal-NMI audit](schala_package_normal_nmi_v1.md) proves the busy-flag
fast path for all four native M/X combinations, with restored CPU context and
13 bytes of stack use including the hardware frame. Its ten-region census
also identifies 44 opaque call frontiers. Those frontiers are explicit
assumptions, not secretly assigned zero stack depth. The full normal-NMI and
global nested-interrupt bounds remain null. The conditional 40-byte route and
52-byte helper arithmetic establish no game stack ownership. The
[metadata reference](../references/schala_package_normal_nmi_v1.json) reproduces
byte for byte from the canonical image and audited sources.

**Validation and resume:** all 31 alternate-observation and 23 normal-NMI host
tests pass. The root independently regenerated both references and the
threshold reference exactly. The separate stack helper's final acceptance is
being strengthened to reconcile each final WRAM change with its recorded
write history. The transaction probe is under independent review. A new
original-cartridge guard and raw-component builder are in preparation; no
cartridge from that builder has been written or executed at this entry.
The remaining overall gate is still `BA-NATIVE-INTEGRATION-DESIGN`.

## 2026-09-08 — successful action transaction reproduced

**Status:** `verified-runtime` for one supported-PC queued Tech, repeated from
the pinned pre-Lavos diagnostic checkpoint. The
[transaction report](schala_package_transaction_observation_v1.md) and
[metadata reference](../references/package_transaction_observation_v1.json)
retain two identical 1,277-record traces, identical manifests and identical
prelaunch receipts. The original sources were archived before each run and
are rechecked by the read-only evidence collector.

The action enters `$C1:BB49` with SP `$06EA` and saved near return `$85D0`.
After target validation it reaches the candidate preflight boundary before
`$C1:BBD4` with valid participant 0 and two `$FF` entries. The three separately
paired MP calls charge participant 0 by 20, changing party MP from
`[93,97,99]` to `[73,97,99]`, before the resolver runs. After animation, eleven
first HP-subtraction witnesses connect their pending terms, arithmetic,
ordered stores and immediate readbacks. The shared finalizer and queue
release then return to the actual caller `$C1:85D1` at SP `$06EC`.

The watched-memory ledger reconciles its declared HP/MP, queue, pending,
ATB, flag and latch ranges through the final active caller. It does not cover
full WRAM. Later HP clamping is outside the first-subtraction proof, and
the result-table clear is a snapshot witness without directly watched stores.
No refusal path was executed. These limits keep the evidence useful for
designing an earlier preflight without presenting success as cancellation.

An early exploratory run exceeded its old four-MiB trace-reader limit.
A later validator attempt used the wrong result-clear extent; the canonical
reader establishes index `$AD9B` plus `$AD9C-$AE4B`, preserving the first
18 bytes of the `$AD89` snapshot and clearing the following 177. Both failed
attempts remain identified in the report. This was an unpublished observer
assumption, not a newly contradicted community data map.

**Validation and resume:** independent review and the root each ran all 41
tests, and the root regenerated the reference byte for byte. Additional
review mutations at the final caller reject unexplained memory changes,
reversed clocks, changed invocation identity and incorrect program bank.
The next refusal work must establish an unsuccessful route's complete
participant, queue, ATB and result lifecycle before selecting a cancellation
destination. The helper's stack/interrupt and original-ROM placement work
continues separately; production selectors remain unbound.

## 2026-09-08 — stack-owned helper state passes normal conformance

**Status:** `verified-runtime`, original synthetic normal-call scope. The
[v2 stack-helper report](schala_package_helper_v2_stack.md) records two fresh
2,980-case runs under the final frozen validator, 5,960 accepted cases total.
Each has 1,426 transports, 1,158 refusals and 396 canonical paths. Their
70,196,608-byte traces are identical. The 577-byte helper uses 42 S-relative
local bytes and reaches 52 bytes below its entry SP, retaining the caller's
direct-page register and staging success outputs before frame release.

The accepted evidence now ties all 1,096,204 stack accesses per run to their
owning observed instructions. It derives all 43,656 required post-SP-change
observations from the exact assembly and PC sequence. Every final WRAM change
must match the last recorded CPU write and exact setup baseline, including
stack bytes. The retired global scratch remains unchanged. Both full matrix
blocks retain the v1 transport behavior exactly after the declared SP change.

The [reference](../references/schala_package_helper_v2_stack.json) preserves
the timeout, omitted-SP and instruction-ownership gaps, and the later final
stack-diff reconciliation gap. The initial final-named pair remains historical;
acceptance names `finalledger1` and `finalledger2`. These were observation and
validator gaps, not newly observed native helper defects. Independent reviews
accepted each hardening step, and the root revalidated all 48 tests and
regenerated the complete metadata byte for byte. V0/v1 remain unchanged.

**Resume:** normal conformance includes two ordinary synthetic stack placements
and three explicit floor/refusal boundaries. The latter have no interrupt
reserve. This proves no real-game stack ownership or interrupt behavior.
Separate ROM execution and original-NMI experiments are underway; no game
allocation, hook, action binding or PC `$07` is installed.

## 2026-09-08 — original ROM execution carrier built through the write guard

**Status:** `verified-static`. The
[original cartridge report](original_snes_package_cartridge_v1.md) and
[reference](../references/original_snes_package_cartridge_v1.json) preserve two
independent, byte-identical guarded builds. The image hash is
`1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b`.
The 290-byte original boot, 577-byte relocated helper, four original certified
terminal-only packages and immutable registry are assembled into memory from
literal blank bytes. There is no game-ROM argument or extracted-game input.

The original diagnostic has a distinct private schema and fixed section
catalog. The existing canonical/inert guard behavior and empty production
catalogs are unchanged. Both intent and complete-diff audits pass before
exclusive image creation. Asar sees only raw `.bin` components. Source,
assembler and certification identities are rechecked at the write boundary,
then actual written ROM/SRAM bytes are reread and hashed. All generated images
and source snapshots remain private. Only authored source and metadata enter Git.

Independent review caught Windows path aliases and receipt-provenance gaps
before any image write. All 43 guard/builder/regression tests pass. The review
reconstructed the final preparation in memory, then the root performed two
actual guarded builds. A further independent review regenerated the completed
build reference exactly and confirmed that the read-only replay paths were
never created. Failed/preparation revisions retain their own scope and hashes.

The [NMI mechanism source audit](mesen_nmi_request_source_v1.md) separately
pins 24 Mesen source files and the unchanged original handler. It defines a
real register-triggered edge during natural VBlank and predicts an authentic
native hardware frame after the selected instruction. The root regenerated
its reference exactly. No interrupt result is inferred from that design.

**Publication and resume:** the preceding alternate/NMI/transaction increment
is published as
[`0ad7df239bb3f2392ccdf8ea764ed4a3a1c59743`](https://github.com/andreipemberton/project-epoch/commit/0ad7df239bb3f2392ccdf8ea764ed4a3a1c59743),
with authenticated branch/commit and all 24 changed-file bytes verified.
The current native work must prove execution at the new ROM location,
immutable-registry CPU reads and separately scoped preemption. Natural
unsuccessful-action observation remains open; selecting Life2 on an entirely
living party did not queue an action, so that exploratory route supplies no
cancellation evidence.

## 2026-09-08 — corrected our NMI observability claim and bounded natural refusal

**Status:** `verified-static` source correction, with exploratory native
witnesses kept separate. MAP-010 identifies our own incorrect published
requirement for `ppu.nmiScanline`. Mesen's pinned `SnesPpu.cpp` explicitly
hides that field from Lua Map serialization. The original source audit had
verified file hashes, but those checks did not derive the document's runtime
key inventory. The first NMI pilot therefore stopped during preparation,
before requesting an interrupt. Its trace and source archive remain intact.

The [numbered v2 phase contract](mesen_nmi_phase_contract_v2.md) observes the
natural VBlank latch transition, checks the non-destructive register peek,
and enters on the next observed public scanline. The root independently
reproduced its metadata exactly and ran all ten rejection tests. The v1
auditor/reference remain unchanged; the old document now carries a correction
banner linked to the source-cited register. Exploratory hardware NMI success
is not promoted by this source correction.

The separate [natural-refusal boundary audit](../tools/audit_package_natural_refusal_boundaries_v1.py)
now pins seven new canonical spans and 35 selected instruction assertions,
reusing five prior cancellation spans. It connects actual menu queue fields,
the selected target's first HP subtraction, death status and zero clamp,
the dead-target failure branch, and a later ready-list insertion. Queue byte
`+2` is conservatively described as the copied menu field `$9615`; this
audit does not independently name its full semantics. The reproduction
command is an argument list so the canonical ROM path's spaces are preserved.

A controller-only exploration queues Marle's Cure for living Lucca, whose
187 HP is overtaken by a later 192-point enemy result before Cure executes.
The observed rejection changes neither party MP nor HP, performs the shared
queue/timing finalization, returns to the actual caller, and later re-enters
Marle into the ready list. The root has independently reviewed its 150-record
exploration and all 39 current host tests. Acceptance still awaits archived
source hardening and a fresh frozen pair; no helper rejection or game hook is
inferred from this vanilla event.

**Publication and resume:** the preceding stack/original-cartridge milestone
is published as
[`9e42e747fc523d7a99dad90ce21940dfbd18c51c`](https://github.com/andreipemberton/project-epoch/commit/9e42e747fc523d7a99dad90ce21940dfbd18c51c),
with the authenticated branch, commit and all 26 changed-file bytes verified.
The complete original-ROM helper pair is running after independent review
and 52 passing tests. The NMI boundary matrix is being hardened separately.
The overall gate remains `BA-NATIVE-INTEGRATION-DESIGN`.

## 2026-09-08 — immutable ROM execution and natural refusal accepted

**Status:** two separate `verified-runtime` results, with independent scopes.
The [v3 ROM execution report](schala_package_helper_v3_rom.md) now accepts two
identical 3,184-case runs, 6,368 cases total. Each executes the unchanged
577-byte v2 implementation at `$410000` and reads immutable package data from
`$42` and registry/allowlists from `$43`. Every case preserves the expected
CPU/stack result, ordered publications and complete final WRAM write ledger.
The pointed terminal streams are certified at source level but never executed.

Each v3 run records 2,537,920 executed helper instructions, 221,600 ROM data
byte reads, 1,561,056 instruction-owned stack accesses and 52,720 required
post-SP-change observations. Their 113,917,080-byte traces have SHA-256
`f9d042c5d76a15a717c7330204d0764a2783191875ac3c91b727a799e6450710`.
The root reviewed the complete evidence collector, independently revalidated
both traces and all source/stage/archive identities, and regenerated the
78,936-byte metadata reference exactly. All 52 host tests pass. Synthetic
normal-call results do not prove a game hook or interrupted game stack.

The [natural refusal report](schala_package_natural_refusal_observation_v1.md)
separately accepts two identical 150-record clean-game observations. Cure is
queued while Lucca has 187 HP; a pending enemy result of 192 then causes the
observed negative word, death-status update and zero clamp. Cure subsequently
takes the selected-dead-target failure, preserves party MP `[93,97,99]`, makes
exactly 22 watched cleanup writes and returns to `$C185EA`. Marle later
reenters the ready list at input poll 2773. No second player command is proved.

The 746,878-byte refusal traces and prelaunch receipts are identical. The
completed manifests differ only in documentary screenshot hashes. Both
screenshot sets are retained; no pixel determinism or cause of that variation
is inferred. All 41 host tests pass. The root revalidated both final traces,
all archives and input copies, the static packet and six historical attempts,
then reproduced the 32,864-byte reference exactly.

The [discovery history](battle_exploration_history_20260908.md) additionally
indexes 17 root-owned alternate/menu/Life2 explorations. Every manifest,
trace and staged Lua identity is checked. Fifteen older launcher revisions
are not supplied as matching source files in that packet, and the broad
alternate observer lacked prelaunch receipts. Those gaps are explicit;
neither later source nor stronger validation is substituted for history.
The current original discovery sources are preserved unchanged in Git.

**Corrections and resume:** the living guide and README now point to these
completed proofs. The command-namespace document uses shared participant
timing finalization instead of its earlier refund label, propagating MAP-007
without changing the identified high-ID reader addresses. MAP-010's correction
increment is published as
[`10d572740c2839cb771137550a9f7051518b0f06`](https://github.com/andreipemberton/project-epoch/commit/10d572740c2839cb771137550a9f7051518b0f06),
with all 12 changed remote files byte-verified. The source-only donor preflight
is being implemented after design review. The original-NMI validator needs
two identified evidence-schema/read-scope fixes and stronger archive checks
before its final matrix. All production catalogs and high bindings stay empty.

## 2026-09-08 — original NMI and source-only preflight accepted

**Status:** the [original-NMI matrix](schala_package_helper_v2_original_nmi.md)
now has two accepted, independently staged 224-case runs. Their complete
420,429,445-byte traces are identical, SHA-256
`3a84fca5e618a9aaaeac9c3056b7a15858f396b5cbfe5e2ae4fd2ae4fe147d50`.
This is `verified-runtime` for the unchanged v2 WRAM helper and original
minimal NMI handler. Each run records 422,544 events, 896 actual hardware
frame-byte writes, 448 vector-byte reads and 224 complete final-WRAM
reconciliations. The observed minimum SPs are `$1FB4/$069D` for the two
declared entry placements; they are not game stack bounds.

The final validator closes the two independently found host gaps: numeric
aliases in change records and an unexplained retired-scratch read. Exact
source-archive inventory is checked before and after execution. The 24 TCS
idle-read observations are distinct from the hardware dummy reads: the first
occurs before TCS changes SP; the second occurs after that instruction and
before the CPU's actual interrupt frame. Pinned Mesen source explains the
sequence. The genuine full trace and full-WRAM write ledger are validated
before the deliberately derived interrupt-free helper projection.

All 55 tests pass. A separate reviewer and the root each revalidated both
entire native traces, source/staged/archive identities, all seven retained
pilot histories and prior phase/normal-helper dependencies. Both independently
reproduced the 605,688-byte reference, SHA-256
`4a517b6c58ef5516b192bdd0558c242afba693b13fae8da71cf1985edb67957a`.
No game handler, ROM-code preemption or nested interrupt is inferred.

The [preflight planner](schala_package_preflight_planner_v1.md) separately
passes source-only review. Its exact successful Luminaire context and
earlier naturally refused Cure context cannot be substituted for each other.
The pure planner returns a qualified package request. The read-only auditor
then revalidates both previously accepted trace pairs, checks source-derived
config row `$08`, preserves all six auxiliary bytes and recomputes both
descriptor masks through the existing complete command policy. The default
high registry remains empty. No supplied certificate or coincident numeric
action/package ID establishes an association.

All 33 tests pass, including mutable/type aliases, every donor/auxiliary
byte, inconsistent contexts, malformed alternate streams and decoded `$1E`
refusal with raw operand `$1E` still accepted. The root independently
regenerated the metadata. A final output-only correction makes actual Windows
CLI output UTF-8/LF, matching the stated format and reference exactly;
the earlier CRLF output identity remains in the human receipt. The final
14,779-byte reference has SHA-256
`cd14a36b8d4e725349b1c3256fd2fb36e65a5be9597029998a4bf8273d58f0a9`.
This is `verified-static` transport eligibility, not native MP feasibility,
action completion, cancellation or integration.

**Publication and resume:** the preceding ROM/refusal increment is published
as [`50bc50860c700b381dce399633625b518af83411`](https://github.com/andreipemberton/project-epoch/commit/50bc50860c700b381dce399633625b518af83411),
with the authenticated branch/commit and all 30 changed-file bytes verified.
The next synthetic experiment combines immutable ROM execution with NMI
preemption under a separate reviewed contract. Normal-game indexed dispatch,
physical stack aliases and a deliberate completion protocol remain open.
The overall gate remains `BA-NATIVE-INTEGRATION-DESIGN`.

## 2026-09-08 — direct NMI callees and command-completion correction

**Status:** `verified-static` with explicit model premises. The separate
[normal-NMI v2 audit](schala_package_normal_nmi_closure_v2.md) closes 25
distinct direct callees, covering 34 of the original 44 call sites. Their
typed return frames and M/X/I states satisfy the prior census's return-width
premise. Ten original sites remain open. Both outcomes of branches are
traversed, near returns cannot restore a changed program bank, and unknown
or unbounded paths retain a null bound. Non-stack aliasing and termination
are not proved. The reset prefix explicitly assigns SP `$06FF`; it cannot
be modeled as a balanced ordinary return.

Two independent reviews found no blocking issue in the completed bounded
packet. The root and reviewer each passed all 42 original tests and
regenerated the 321,839-byte reference exactly, SHA-256
`413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242`.
The original v1 census and its 44-site inventory remain unchanged. The four
reviewed scroll table cells and unresolved scene dispatcher retain their
separate input-range/hidden-accumulator provenance requirements.

MAP-011 corrects the upstream annotation at `bank_C1.asm:9969`: its
`$A3D1`-set default handler does not consume the command under D=0. `TDC`
supplies zero to the pointer-add helper; the low and high words are stored
back unchanged, including the real same-value writes at `$E6-$E9`.
The mode-zero branch instead increments `$9876` modulo 256. Command `$00`
clears the owner-active byte without supplying the package-counter signal.
The [completion contract](schala_package_completion_contract_v1.md) preserves
the exact wrong source, pinned canonical spans, ABI premises and limitations.

Independent review checked the canonical instructions and all twelve original
boundary tests. The audit reproduces seven span hashes, 31 selected
instruction assertions, all 65,536 mode/counter model pairs and the existing
policy intersection. All 70 direct default-handler opcodes are excluded by
v0's 123-opcode allowed set; the audit does not claim that every other allowed
command lacks indirect or aliased completion effects. The 9,212-byte metadata
reference has SHA-256
`76c5d5a157748717c42301a7cbfd9d00f9f656cdeba048415e77c123d7095766`.
No new CPU replay or completion-policy extension is implied.

**Resume:** reuse the already recorded successful transaction's actual
default-handler increment, owner-stop entry sites, scene clear and caller
readbacks to document a bounded native completion witness. Its encoded
command ID and pointer movement were not captured and must not be invented.
The separate ROM/NMI design is ready for implementation. All production
hooks, allocations and high selector bindings remain absent.

## 2026-09-08 — native completion witness and scene-input boundaries

**Status:** completed bounded evidence reuse and static input analysis; no
new emulator launch in these two packets. The
[completion-witness audit](schala_package_completion_witness_v1.md)
revalidates the full accepted successful transaction pair before selecting
its chronology. It connects 516 observed zero-counter waits to the actual
`$7E9876: 0 -> 1` store at the default-family increment, the caller's next
snapshot, the separate zero scene-latch check, both cleanup resets, result
application and the same action's actual queue-caller return. All eight
recorded latch writes reconcile with their subsequent snapshots.

Two stop-handler entry observations calculate owner targets `$7E5DB0` and
`$7E5DAF`, but the observer did not capture those owner writes or readbacks.
It also did not capture an encoded `$01` command or a script-pointer delta.
The report preserves these distinctions and cites MAP-011 as separate static
evidence. No synthetic package is assigned this vanilla action's completion.

The author, root and second reviewer each passed all 54 tests. Both reviewers
regenerated the 16,543-byte reference exactly, SHA-256
`3ac28c6f572ad5023c99ff8f373d0346598611300bba26597207a71d4585e015`.
Two actual post-review CLI processes also matched it with UTF-8/LF output
and empty stderr. Existing native source and trace identities are unchanged.

The [scene-dispatch input audit](schala_scene_dispatch_inputs_v1.md) proves
the hidden accumulator byte B=0 before the first indexed call reached from
the tick prefix under native M1/X0/D0. It stops before that handler. The
continuation after an unmodeled handler return and a standalone slot entry
both retain unknown B. Eight-bit ASL followed by sixteen-bit TAX therefore
cannot be described as a universally zero-extended index.

The 122 reviewed cells for `$80-$F9` remain a physical prefix; the local
classifier admits 127 indexed byte values. The five `$FA-$FE` cells overlap
the decoded `$F9` handler's occupied body. Separately, the initializer skips
`$FF`, producing 255 hypothetical byte-ID reads and 207 distinct roots under
B=0, without certifying a legal script corpus. The exact PBR-wrapped indexed
JSR and long-indexed script-pointer recipes remain distinct.

All 27 tests pass for author/root/peer, including exhaustive mode-independent
command/B algebra and fail-closed prefix effects. Both reviewers reproduced
the 156,163-byte metadata, SHA-256
`d5604c65934dff1dfa4796ea3d990e227065e9b28a5499695f590fff912a8c13`.
This refines an open obligation in closure v2; it is not a new correction to
an annotation that claimed a complete legal table.

**Publication and resume:** the preceding NMI/preflight/completion-source
increment is published as
[`e14826a9e52dd4044565bc78c0ca6363cd68c14c`](https://github.com/andreipemberton/project-epoch/commit/e14826a9e52dd4044565bc78c0ca6363cd68c14c).
The authenticated branch/commit and every one of its 27 changed-file byte
strings were independently checked against the local commit. The current
guide now carries a stable completed/open gate ledger to prevent repeated
work after handoff. Active work is the separate immutable-ROM/NMI calibration,
outer-mode input contract, producer-domain closure and native rejection design.
The first combined pilot remains rejected history because its continuation
outlasted the initially required VBlank window; no production gate is promoted.

## 2026-09-08 — outer NMI mode caller and hidden-byte input contract

**Status:** independently reviewed `verified-static` prefix proof. The
[outer-mode audit](schala_nmi_mode_inputs_v1.md) tracks arbitrary symbolic
register bytes through all four initial native M/X combinations. The 40
decoded instructions on the busy-zero path establish A=`$0080`, X=`$002B`,
Y=`$CC90`, D=0, DBR=0 and M1/X0 at `$CD0C95`. Its 43-byte MVN summary and
the later full-accumulator TDC are explicit. Native entry, no intervening
asynchronous corruption and ordinary writable stack RAM remain premises.
The conditional 16 bytes below the interrupted SP do not establish a global
NMI maximum or a safe live-game reserve.

The local eight-bit shift aliases high-bit mode values onto the lower 128
cells. The three reviewed cells select `$CD09F1/$CD088D`; the next cell
overlaps the occupied field-service wrapper. All 65,536 mode/B combinations
are checked, while legal mode-producer domains and selected-body effects
remain open. The old annotation's named 0/1/2 targets are correct, so this
is a refinement rather than a new mapping-error entry.

Independent review found and corrected two generalized toy-model gaps before
release: stale Z flags after selected supported instructions, and reuse of
the one-time busy-byte mutation premise. Four new regression tests retain
the counterexamples. The canonical register result did not change. All 23
tests pass, and independent import/actual-CLI reproduction gives the exact
138,037-byte reference, SHA-256
`dc715f6726e482a00e649d15252b5ca42f933f82198d8520c78d7867f3932530`.
No accepted native run or earlier closure source needed to be repeated.

## 2026-09-08 — reused native dispatch frames and selected-mode composition

**Status:** separate reviewed runtime reuse and conditional static closure.
The [native dispatch witness](schala_nmi_dispatch_witness_v1.md) revalidates
the complete accepted context pair, then both current static input references.
All 1,201 mode snapshots have A=X=`$0002`, Y=`$CC90`, D=0, DBR=0, M1/X0/I1
and physical mode byte one. Each twelve-byte stack snapshot exactly matches
the pinned JSL return and nine saved register bytes from its own NMI entry.
The SP delta is twelve bytes from entry, which is already after the hardware
frame. All 3,097 scene snapshots in 657 NMI contexts have B0 and the expected
local ABI; their entry-relative SP delta is 24 bytes. Forty-four command
values are reconstructed from the static recipe, not recorded stream reads.

The 22 original tests and independent full reference reproduction pass.
Two actual CLI processes reproduce the 9,693-byte metadata, SHA-256
`e84739ef37b32812491b9166bf1f706a8d3490a3bf1810b3a4296c5305f47e20`.
Sampled minima `$06B5/$06A9` are not full stack low-water measurements.
This adds no new emulator run or proof of arbitrary handler-return B.

The [mode-body composition](schala_nmi_mode_bodies_v1.md) uses the unchanged
v2 walker and its eight previously closed callees. At `$CD09F1`, the full
walk agrees with the independent maximum of those sequential contributions:
12 additional bytes below entry, 14 including the near frame, and sole RTS
`$CD0ADD` in M1/X0/I1. `$CD088D` remains open at indexed JMP `$CD06B9` with
two typed near frames; its full bound remains null. All 40 tests passed for
author/root/peer, and two actual CLI outputs match the 160,900-byte reference,
SHA-256 `f3057c1cf9d0b354a318e3e67b2c760fdf9d8bfc49784d4efed344ba997a8d85`.
Register values, DMA, aliases and a whole-NMI bound remain separate work.

## 2026-09-08 — original-ROM timing calibration and combined pilot

**Status:** the [timing calibration](schala_package_helper_v4_timing_calibration.md)
passes two source-frozen 22-case runs. Each preserves the complete v3 normal
ROM/stack/WRAM contract and adds 15,090 instruction/timing observations.
Both 13,852,910-byte traces have SHA-256
`7b21a5bb512514923eb39e5bbed22f4f34d121b7f26ca73c8a16ce63aaf6d6af`.
Their elapsed projections and 92 rows are identical; the source-derived start
scanlines span 188 through 227. These are scheduling inferences, not a claim
that the corresponding interrupt was already executed.

Source review added preparation-edge raster/full-clock checks and duplicate
CPU/SP consistency checks before the native pair. All 46 host tests pass.
A new offline metadata collector initially expected LF in the launcher's
Windows-generated `inputs.lua`; it was corrected to reconstruct the actual
pinned CRLF bytes. That failed metadata attempt and source are preserved,
without relabeling either successful native run or altering its source.

The root independently revalidated both complete traces, archives, staged
inputs, elapsed projections and source identities, reproducing the 98,917-byte
reference exactly, SHA-256
`8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb`.
Its report retains its historical review wording because the separate v4
experiment now guards that report's exact bytes. This entry records the root
acceptance externally so the native provenance does not drift.

The calibrated combined ROM/NMI pilot then passed both selected deepest-JSR
cases. Its 7,146,635-byte trace has SHA-256
`f61cad80bb75e209568415828df683e5cff2e97c2f373390aeac6ce4b853ffa9`.
Root revalidation checks all 3,635 events per case, 48 current/prepared source
identities, all 41 archived sources, immutable staged inputs and the complete
actual WRAM ledger before the unchanged v3 helper projection. The interrupt
enters on scanline 227, returns on 228 and the longer continuation ends on
scanline 3 after wrap. The full 152-case pair is approved for evaluation; this
pilot is not its acceptance. The original rejected pilot remains unchanged.

**Publication and resume:** the preceding three-packet input increment is
published as
[`25080cc6b84ed8ee4124f0d2626527b5d25a6523`](https://github.com/andreipemberton/project-epoch/commit/25080cc6b84ed8ee4124f0d2626527b5d25a6523),
with authenticated branch/commit/remote-ref agreement and all 18 changed-file
byte strings verified. Continue the full combined matrix and exact scroll
input/target frontier, while keeping production catalogs and high bindings empty.

## 2026-09-08 — session extension and sampled-clear correction review

Andrei extended the original six-hour session by another three hours at
20:06 UTC. The planned finish is now 23:58:41 UTC, nine elapsed hours from
the original start. A coordinating context-recovery connection failure
interrupted root review; independent workers preserved their handoffs and
paused changed-source native execution until root recovered.

The first full combined ROM/NMI experiment completed all 152 native records.
Its frozen host validator accepted 148 and rejected four: selector `$80`,
branch `$40`, synthetic SP `$1FEF`, first-JSR boundary, statuses
`$00/$C3/$4C/$8F`. The rejected trace is 217,544,660 bytes, SHA-256
`69f2173421da9d5d0dada58e096b8937fbb6819f3ac6b95f656997f10895b061`.
Its exact source archive and explicit host rejection remain preserved.

The failed condition bounded the time between sampled pending and clear
states to 32 master clocks. Pinned emulator CPU, DMA and callback-filter
source explains an exact 38-clock observation gap across the original
`$4101DF` publication-word store and `$4101E3` stack-relative load:
initialization clears before an opcode fetch that is not a retained data
callback. The next retained stack read samples the already-cleared state.
This is not evidence of 38 clocks of pending DMA. The separately numbered
correction keeps the generic 32-clock limit and requires the entire original
instruction/event sequence, CPU states, physical addresses, publication
bytes, ordinals and exact clock/cycle intervals for the single exception.

Independent review reproduced the historical four failures with the archived
validator and passed all 152 records through the correction offline. Root
reviewed the source derivation and passed 81 native-envelope plus eleven
metadata tests. That offline check does not accept the historical run.
Two fresh frozen-source 152-case runs are now authorized; their actual
acceptance and full paired reproduction remain pending. The developer guide
continues to mark real game-stack ownership and production hooks unresolved.

## 2026-09-08 — scroll caller values and scene-handler control-flow census

**Status:** two independently reviewed additive static packets. The
[scroll caller audit](schala_nmi_scroll_inputs_v1.md) starts at `$CD088D`
with unknown B, D0, DBR0 and native M1/X0/I1. Its 947 states and 587 instruction
contexts inline the relevant direct callees, including actual temporary-bank
save/restore sequences. Every path reaching `$CD0929` before the explicit
`$CD0907` cut has B0/D0/DBR7E and the exact two-byte root frame. The separate
pad route is not silently assumed to return or preserve that ABI.

The four reviewed scroll cells then compose under a stated selected-input
premise. The table jump adds no return frame; local totals including the
existing scroll near frame are 2/2/2/4 bytes. The even base/index prevents a
pointer word from straddling the bank boundary, although base-plus-index can
wrap within PBR. The first successor cell is occupied executable code, and
the `$CA92` producer domain remains open. Root and a second reviewer each
passed all 49 tests and reproduced the 87,273-byte reference exactly, SHA-256
`003bf6be7e686445a8aa0a7bddf36bd8ca35b2fb49aa4d184ec5f3bc15db8013`.
Two actual CLI processes also agreed byte for byte before reference emission.

The [scene-handler census](schala_scene_handler_closure_v1.md) reuses the
122 previously reviewed B0 cells and their 121 distinct targets. Its separate
decoder adds ten source-cited instructions without changing prior source.
All 67 targets closed by the old walker retain exactly the same contracts
apart from declared ASL/ROL write metadata. The new total is 114 closed
targets and seven explicit indirect frontiers. The 123 closed return contexts
all have M1/X0/I1; their largest additional depth is 16 bytes at `$CD1805`.
That closed-subset maximum is not a dispatcher or whole-NMI bound.

The only pointer alias, `$B5/$B6`, selects an open target. A pre-review check
corrected the draft's guessed 115 closed cells to the derived 114. Independent
review then caught acceptance of floating-point `2.0` as a metadata stack
count; an exact-integer guard and negative fixture close that gap. Both
pre-fix source packets remain private preserved history. The canonical
control-flow and stack results did not change. Author and reviewer passed
all 40 tests, and two post-review CLI outputs reproduce the 1,029,264-byte
reference exactly, SHA-256
`ac44bd733e1b6f4dffd91887e5ac42738a57ace78a8583c5ff9c5bf2e602a43a`.

**Publication and resume:** the preceding calibration/dispatch checkpoint is
[`60bda0f9260633102db14c6dd43044edf979e616`](https://github.com/andreipemberton/project-epoch/commit/60bda0f9260633102db14c6dd43044edf979e616).
Authenticated commit/branch/remote-ref agreement and all 20 changed-file byte
strings were verified. Active work is the fresh combined ROM/NMI pair,
scene-handler return values and a separately reviewed IRQ memory/register
contract. No production catalog, high binding or PC `$07` claim is promoted.

## 2026-09-08 - combined ROM/NMI acceptance and conditional memory/value proofs

**Status:** four additive packets independently accepted. The
[combined original-ROM/NMI proof](schala_package_helper_v4_rom_nmi.md)
passes two fresh 152-case Mesen runs. Each exact trace is 217,544,660 bytes,
SHA-256 `9752443839e73d8cdb29e6096f41838ffb4091372b5fd910209cb0a74ab19c6e`.
The immutable ROM helper, registry and descriptor inputs remain unchanged.
Across each run, the validator checks 218,732 retained events, 119,960 helper/
terminal execution observations, 608 hardware stack writes, 304 actual vector
reads, 152 minimal-handler counter increments and complete WRAM reconciliation.
The named allocation, first-JSR, release, PLP and JML boundaries include
canonical, refused and successful routes. The observed combined peak is 59
bytes, including the original minimal handler, under the two declared entry
SPs. This is not the game's full interrupt handler or a global stack bound.

The correction permits exactly four 38-clock sampled-clear observations only
when the entire pinned original instruction/memory/CPU sequence agrees. The
generic 32-clock condition remains intact. The exact first rejected trace is
preserved, along with its source archive and mandatory rejection receipt.
An explicit initial-header-only protocol substitution reproduces the new
trace hash while retaining every other byte. That comparison documents the
correction transparently; it does not retroactively accept the old protocol.
The two earlier pilots, metadata draft and original paused handoff remain
separately pinned history. No raw trace or cartridge enters source control.

Root independently read the final collector and tests, passed all 99 tests,
and reconstructed both complete native records, archives, staged inputs and
source identities through a separate actual CLI. The exact 523,168-byte
public reference reproduces with empty stderr, SHA-256
`62eb9deae8cd960c05f8732d308cfc862b59e4daf3a233e64043ec4ce9ad6e01`.
All 52 guarded source/staged identities and 45 archived sources are checked.
The accepted calibration report remains frozen; this entry records its
later successful use without changing native prerequisites.

The [IRQ memory/register contract](schala_package_irq_memory_contract_v2.md)
reuses the accepted control-flow census and traces all four symbolic native
M/X entry combinations. It proves exact saved A/B/X/Y/D/DBR and typed-frame
restoration, and resolves 109 ordinary CPU-write contexts to 298 physical
WRAM bytes, including nine complete 30-byte MVN footprints. These writes are
disjoint from the explicitly proposed helper stack, direct-page and
publication ranges. Under the planning entry SP $06D8 and 52-byte helper
contribution, its 35-byte IRQ depth reaches SP $0681; this arithmetic does
not reserve that space or establish a game-wide ownership floor.

Both independent reviewers passed 49 tests and reproduced the 84,558-byte
reference exactly, SHA-256
`6a6cc3ac65cc2e9ae5d5fe92a313a7a716f31cdbc1256fc18d38a4731eaadc31`.
Original negative specimens also reject bank-mirror word aliases, MVN writes
into live frames and protected initial hardware-frame overlap. A pre-review
metadata/decoder hardening and Windows LF-stdout correction remain preserved
as draft history. DMA register writes are inventoried but their effects are
not claimed by this packet.

The [scene return-value audit](schala_scene_handler_values_v1.md) applies a
separate, source-pinned extension of the conservative value model to all
114 already control-flow-closed targets. Its 65 earlier supported projections
remain identical. All 114 return D0/DBR7E; 111 also return B0. The three roots
$CD1805, $CD19B1 and $CD2460 retain unresolved B values. No guessed branch
condition is used to close them. Author, root and a second reviewer passed
43 tests, and two actual CLI processes reproduce the 376,981-byte reference
with empty stderr, SHA-256
`cb99bfff13c319a7ec67742eeed1ab0fee0827799ec80b89cce2f3dd668af543`.
This is conditional per-handler evidence, not a whole command-loop invariant.

The [scene command $82 subdispatch](schala_scene82_subdispatch_v1.md) is
separate from Schala action IDs and package selectors. Its two parameter
reads remain independent: the first supplies count (p&31)+1; with B0 the
second supplies index 2*(q>>5). Exhaustive original byte-input checks retain
the hidden high accumulator byte when nonzero. All eight canonical target
words select individually closed near-return bodies, each returning
A0/B0/D0/DBR7E and M1/X0/I1 with no extra stack beyond the inherited two-byte
frame. This conditionally resolves one historical indirect frontier without
rewriting the original seven-frontier census. Memory-source/alias premises
remain explicit. Both reviewers passed 31 tests, and two actual CLI outputs
reproduce the 49,712-byte reference exactly, SHA-256
`b7e3144a800512e8e6391b72c9bc733b33240e0cc0a88e57092e2e13af0c0dfc`.

**Publication and resume:** the preceding scroll/census checkpoint is
[`6d13aac03f6228854de08af14da5b238c5d53dcb`](https://github.com/andreipemberton/project-epoch/commit/6d13aac03f6228854de08af14da5b238c5d53dcb).
Authenticated commit/branch/remote-ref agreement and all 14 changed-file
byte strings were verified. Continue the separate manual-DMA destination
contract, narrow return-value branch refinement and remaining indirect
scene paths. Full normal-game NMI closure, physical stack ownership,
publication-reader isolation and native preflight-rejection cleanup remain
required. The overall gate stays BA-NATIVE-INTEGRATION-DESIGN, with empty
production hook/allocation catalogs and unbound high production selectors.

## 2026-09-08 - scene return refinement, conditional subdispatches and DMA destinations

**Status:** four additional static packets accepted through independent
source review, focused tests and exact CLI reproduction. These are narrower
contracts for the remaining integration design; none changes a game image.

The [scene return-values v2 packet](schala_scene_handler_values_v2.md)
resolves the three previously uncertain B returns in the preserved 114-target
set. At exactly three named sites, the immediate executed predecessor is an
M16 LDA and the taken BEQ edge therefore has full A=0. Both successors remain
in the abstract graph; no general flag inference or branch pruning is added.
All 114 typed source/call/return contexts agree with the accepted census,
and the v1 111-proved/three-unresolved reference is reproduced unchanged.
Root and a separate reviewer passed 18 tests and reproduced the 357,484-byte
reference, SHA-256
`52543e1820669eac00b90baa39e307dcb9b35c9be14e7a0eff42e5aa762d8b87`.
This improves conservative analysis precision; it is not a mapping correction.

The [manual DMA7 destination contract](schala_package_irq_dma7_contract_v3.md)
follows the actual field-DMA leaf service from symbolic entry registers.
Its 338 states exactly cover the 254 instruction contexts and 136 ordinary
CPU byte-write contexts in the accepted IRQ packet. All twelve request sites
have dominating DMAP7=$41, BBAD7=$18, size=$0080 and exact byte STY MDMAEN=$80
writers. Pinned CPU/DMA/register/PPU source derives requested writes only to
$2118/$2119. The model invalidates size knowledge after each request; every
later request must establish its own count. This proves requested VRAM-port
destinations, not source validity, actual completion, timing or interference.

Independent review found a false acceptance in the initial generic model:
a reverse-direction overwrite through mirrored register $80:4370 could leave
an old bank-zero control value in its ledger. That exact draft and candidate
remain preserved. The corrected per-byte guard refuses unmodeled nonzero
hardware-register mirrors, including word-high range crossings. Root then
required byte-exact reproduction of the pinned accepted IRQ reference before
any new projection. That second draft is preserved too. All 41 tests pass,
including original mirror and prerequisite-drift specimens. Root's two actual
CLI outputs exactly reproduce the 58,451-byte reference, SHA-256
`10b35697c6eac860f79a3d062856f944540b96a200114b5da5fab0fb6b94d2d3`.
The canonical game configuration was unchanged by either model correction.

The [$8C/$8D proof](schala_scene8c8d_subdispatch_v1.md) resolves eight leaf
bodies under B0/D0/DBR7E, M1/X0/I1 and (parameter&$7F)<4. Their eight-bit
ASL discards parameter bit7, while the X16 TAX preserves hidden B. Each
selected leaf returns A/B0 with no frame beyond the existing near call.
B0 alone permits 128 physical word starts per command; arbitrary B covers
the bank. The odd-base pointer wrap and parameter-$04 occupied-code overlap
are explicit. DP43/Y and parameter-source lifetime remain unresolved.
Author, root and independent reviewer passed 34 tests. Two actual root CLI
outputs reproduce the 48,468-byte reference, SHA-256
`8b25fb718642c968e18fffebbccae6fe8c33ee0d229e337400485320b0dd3e5d`.

The [$88 proof](schala_scene88_subdispatch_v1.md) has the same conditional
four-cell predicate, but a materially different return ABI. Ordinals 0/1/2
return A=$00FF/B0; ordinal3 returns A=$FF00/B=$FF. The enclosing $D1FBD1 RTL
and $CD29E2 RTS preserve that hidden byte. Their exact frames contribute
JSL3+indexed-JSR2, five bytes below the scene-handler entry or seven including
its existing near frame. This conditional nonzero-B result is a concrete
reason not to generalize the 114 direct-target contract to the whole loop.
No legal parameter3 producer or live vanilla bug is established.

The root's first original metadata fixture omitted inherited scope fields;
its test failure and candidate output remain private preserved history.
After the fixture was completed, independent review found that the standalone
frame composer checked B but not its reported full A. The canonical audit
already supplied exact consistent rows. A strict A-word check and original
negative specimen now reject inconsistent or floating-point values; the
pre-hardening packet is preserved. All 33 tests pass. The final correction
changes only source-identity entries in metadata, and two root CLI outputs
reproduce the 57,422-byte reference, SHA-256
`321483c1f061847c9c24fadf1a2d43ca58d46edc7734c11c59cc990edbe03d84`.
No raw game bytes or native trace is a host-test fixture.

**Publication and resume:** the preceding combined ROM/NMI checkpoint is
[`17218fac2334cd376bc346ff7ad35dd104a08a2c`](https://github.com/andreipemberton/project-epoch/commit/17218fac2334cd376bc346ff7ad35dd104a08a2c).
Authenticated commit/branch/remote-ref agreement and every one of its 28
changed-file byte strings were verified. Continue the remaining scene-$80,
$8B and $B5/$B6 pointer/control boundaries and the actual NMI publication
readers. Keep parameter legality, memory aliases, nested interrupts, physical
stack ownership and native rejection cleanup as explicit unfinished gates.
The session continues through 23:58:41 UTC; production catalogs remain empty.

## 2026-09-08 - conditional scene topology and exact copy-pointer arithmetic

**Status:** three more static packets passed root and independent peer
review, their focused tests, and byte-exact CLI reference reproduction.
No native execution or image mutation belongs to these three packets.

The [scene $80 packet](schala_scene80_subdispatch_v1.md) proves 29 physical
pointer words before the first selected code body. The first 29 target walks
cover all 156 bytes of the remaining annotated incbin interval as code.
This does not make the preceding words a proved legal parameter domain, and
the annotation did not itself claim 107 legal entries. No false correction
is attributed to the upstream author. Twenty-seven targets close with
B0/D0/DBR7E; two retain exact MVP and ADC-dp-X frontiers. The already completed
128-cell B0 census remains explicitly hypothetical, including its accidental
closed paths and a near-frame-incompatible RTI destination. The 40 tests pass;
two root CLI outputs exactly match the 424,188-byte reference, SHA-256
`98ef60b958f997bc125d2550ff90c9cd6948a9f7b269be7fc0194790cfbece2f`.
A separately numbered proof is now reviewing the two remaining instruction
effects while preserving this v1 source and reference.

The [scene $8B packet](schala_scene8b_dispatch_inputs_v1.md) derives B0 from
the helper's successful return, with unknown incoming B. A complete local
CFG owns every return predecessor: failure executes CLC/RTS and the caller
exits; success executes SEC/RTS and reaches dispatch. The earlier temporary
index can still contain incoming B. After success, q selects a byte at
CAD1+q, while z's bit7 is discarded by byte ASL. Those are distinct input
namespaces. Two of six reviewed targets have exact conditional returns with
two additional stack bytes; the four other targets retain distinct producers
at the shared CEE7CC jump. No B5/B6 contract is substituted by address alone.
The 35 tests pass; two root CLI outputs match the 124,619-byte reference,
SHA-256 `f3cb6cef7e04c2dd101eb69ee4ccb212443ea3ea91e248f07ed2a586155609bf`.

The [B5/B6 copy-pointer packet](schala_scene_copy_pointer_v1.md) executes a
finite source projection over all 65,536 stable r/s byte pairs. Its independent
integer expression and actual binary carry/borrow/width calculation agree.
Exactly 64,414 select a verified copy suffix, equivalent to abs(r-s)<=222;
1,122 do not. The physical 256 copy pairs yield 257 suffix entries, whereas
safe inputs from this producer select only 223. The unknown CAAB high byte
remains unknown until an exact immediately following M16 AND removes it.
The DP pointer writer and bank-zero absolute-indirect reader coincide only
under D0. Both parity continuations preserve the typed 11-byte return chain.
These are conditional source facts, not legal-input, effective-address or
whole-handler proofs. The 37 tests pass; root and peer CLI reproduction
matches the 70,722-byte reference, SHA-256
`13913c7b244b454a8afd4afd89977408466e2dda06699578f344b9c691789c53`.
The initial unknown-high and overlap-test development refusals are described
in its report; no rejected native artifact is being relabeled.

The package-owner reconfirmation is the existing MAP-005 thirteen-owner
correction, not a new discovery or a new numbered correction. The verified
upstream citation and exact 224-byte source-span hash remain in the register.
The next native measurement has a reviewed design: five fixed actual-game
normal-NMI intervals, all instruction boundaries inside each interval, exact
SP and implicit stack-write transitions, complete WRAM baseline/final
reconciliation against bus writes, and declared publication-range accesses.
It uses the unchanged clean ROM, checkpoint and input sequence. Its source
is being authored; no pilot or runtime result is yet accepted. Bus callbacks
combine CPU/DMA/dummy writes, so broad observations will not be mislabeled
as CPU-only writes. The existing dispatch snapshots remain preserved and
are not upgraded into complete stack-depth measurements.

**Publication and resume:** the prior checkpoint is
[`a6f88fb10be6bc4b454c9db560c84bb248f88db7`](https://github.com/andreipemberton/project-epoch/commit/a6f88fb10be6bc4b454c9db560c84bb248f88db7).
Its authenticated commit, main branch and remote ref agree, and all 22 changed
files match the exact committed bytes. Continue the bounded native observer,
the separately numbered two-target $80 extension and actual $8B pointer
producers. Legal domains, physical memory/stack ownership, full game-NMI
composition, publication isolation and native rejection cleanup remain open.
The nine-hour session remains active through 23:58:41 UTC.

## 2026-10-03 — interrupted-session recovery and current host audit

Work resumed at 20:40 UTC from the interrupted September 8 checkpoint.
The historical September deadline above is preserved as history; the gap
between sessions is not engineering time. Before edits, nine unfinished or
locally changed files were copied byte-for-byte into an ignored recovery
archive, with source paths, sizes and SHA-256 identities in its manifest.
Accepted September sources, references and native traces remain unchanged.

At Andrei's request, Coda checked CodaLilitari's GitHub, GitLab and portfolio.
The authenticated [GitHub main](https://github.com/CodaLilitari/project-epoch)
and public [GitLab main](https://gitlab.com/codalilitari/project-epoch) both
matched the local `a0b17f6227ed6a54cdfb7c63e726feb94d26b89d` checkpoint.
GitLab's September 28 project activity did not represent newer engineering
commits. The old `andreipemberton/project-epoch` GitHub API path returned 404;
the local `origin` now uses the verified CodaLilitari path. This changes a
local remote URL, not repository ownership or account restriction status.

The [portfolio case](https://richard-pemberton-research.darkahn.chatgpt.site/#project-epoch)
already points to GitLab and accurately describes ongoing eighth-character
research, locally retained game inputs and no finished playable release.
No portfolio edit was needed or performed. A focused public research refresh
also confirmed that `dscotton/ct_disassembly` main is still the pinned
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`, dated July 11. That verifies
this dependency's current head; it is not a claim that every online project
or unreleased patch was exhaustively searched.

The separate [scene80 remaining-return v2 packet](schala_scene80_remaining_returns_v2.md)
now closes its two former conditional frontiers. Index 9's completed MVPs
leave B=$FF until the later TDC restores B0. Index 13's long callee explicitly
uses temporary D=$0A00 and restores saved D0 at both returns. All 29 reviewed
physical targets have conditional B0/D0/DBR7E/M1X0I1 returns, with a largest
seven additional stack bytes, nine including the existing near frame.
The complete old reference and all 114 prior direct-control contracts
reproduce unchanged. Root reviewed the full new source/report/tests, passed
38 tests, and ran two independent CLI processes yielding identical 59,258-byte
metadata, SHA-256 `9f24a7fb84c1534363c4d0384d835e41cdf03d62e4ca303f3502519a1d781338`.
This is an additive conditional proof, not a new legal-input, physical-memory
or whole-NMI claim. The current short resume page is [CURRENT_HANDOFF](CURRENT_HANDOFF.md).

The separate [scene8B copy-producer v1 packet](schala_scene8b_copy_producers_v1.md)
also passed root and independent peer review. Three distinct producers serve
the four previously open stubs. Their 393,216 actual evaluations cover two
q-parity representatives and all r/s byte pairs; full-q source use has an
explicit dependency proof, and four alias cases refuse. Each producer has
64,414 safe-or-skipped r/s pairs and 1,122 outside the copy suffix domain.
The typed return chain is nine counted bytes including the scene frame.
All 52 tests pass; author, peer and root CLI outputs match the 171,599-byte
reference, SHA-256 `f3fc3cf0999d0782f80c76a39ace13332dc31ef895482391e3e3282512d14ee6`.
The peer additionally checked 9,072 canonical high-q/boundary cases. The
interrupted draft's word-versus-bank-qualified pointer mismatch was our
unpublished implementation error, documented with its preserved source
identity; it was not an upstream mapping contradiction. The half-fill
continuation remains a distinct memory/termination obligation, even when
the preceding copy is skipped.

Before any native use of the new NMI observer, independent review exposed
an unpublished validator defect: high-ROM indirect-pointer bus values were
not reconciled with immutable source bytes. An original forged-jump example
could skip instructions and pass a falsely shallow interval. The correction
checks all captured high-ROM reads; positive and negative whole-interval
fixtures now pass their intended outcomes. All 79 focused tests pass, and
the primary implementation behind nonmutating debugger reads is now pinned.
The defective source remains preserved; it supported no accepted native run.

A single read-only pilot then observed the unchanged game's NMI at poll 379.
Independent revalidation found 5,507 executed instructions, 13,028 bus events,
exact full-WRAM reconciliation and minimum SP=$06A8: 34 bytes below handler
entry, 38 including its already-existing hardware frame. The process log
contains 28,319 Mesen uninitialized-read diagnostics; it is not a warning-free
run or a general initialization-safety proof. The pilot is not yet a repeated
runtime result. Full-pair execution and further source/evidence review remain
in progress; no game hook, production allocation or selector is approved.

## 2026-10-03 — repeated actual NMI observation and narrowed integration strategy

The first resumed static checkpoint was published to CodaLilitari GitHub at
`af3852f9b08285a5011a744d37e3a0b5cd279d49`. Authenticated commit lookup,
branch lookup and the Git remote agreed, and all fourteen changed files were
downloaded at that exact commit and compared byte-for-byte and by SHA-256.
The metadata receipt is
[`work_session_publications_2026_10_03.json`](../references/work_session_publications_2026_10_03.json).
GitLab remained at the earlier checked checkpoint. The question of keeping
that additional mirror synchronized remains pending; read-only inspection
and GitHub publication continued independently. No portfolio edit was needed.

The first five-interval NMI run did not succeed. Its whole-run JSON export
left a partial file and the emulator reached the declared 900-second timeout.
The frozen collector set its done flag before serialization; its exception
handler then called the same finalizer, which immediately returned and skipped
the stop request. This error-swallowing defect is directly established by our
source. The pinned Mesen callback watchdog defaults to one second, making
watchdog expiry during the large export a supported causal inference; the
actual exception was not captured. The failed source archive and partial
trace remain unchanged. A separate review also found that unverified
bank-zero indirect pointer reads could bypass the immutable-ROM guard.
Both are defects in our unpublished observer, not newly discovered game
mapping errors. The [report](normal_nmi_stack_observation_v1.md) retains exact
source/trace identities and the adversarial specimens.

The repaired collector writes each bounded event in its existing callback,
flushes completed intervals and uses a separate direct fail-stop path.
The validator refuses control pointers outside reconciled WRAM or pinned
high ROM. Eighty focused tests passed, followed by independent source review.
A fresh pilot completed with its entire decoded JSON equal to the old pilot;
only JSON serialization order differs. No watchdog setting was raised.

Two fresh isolated full runs then completed. Their 37,645,178-byte traces
are identical, SHA-256
`b1daedf1b9fafebbc148263ef498f46a2af57fa5730aad96d038e0e5b91c552a`.
Each captures five selected normal-NMI intervals, 28,581 executed instructions
and 59,408 bus events. Independent pointwise review checked 10,071 direct
WRAM writes, 30,353 WRAM reads and 2,746 high-ROM reads per run. All complete
final WRAM snapshots reconcile. Every selected interval reaches 34 bytes
below handler entry, or 38 including the native frame already present.
No observed access reaches the declared helper publication ranges, so this
does not test partial-publication safety. Logs repeat 28,824 uninitialized-read
diagnostics; success is not a warning-free or general initialization claim.

The separate metadata-only acceptance auditor checks actual files and reruns
the complete trace validator; it does not trust manifest acceptance flags.
All 46 original/adversarial acceptance tests pass. Root read both complete
source/test packets and reproduced the author's exact output in two fresh
CLI processes. The accepted 148,513-byte
[reference](../references/normal_nmi_stack_observation_v1.json) hashes to
`5431d238814391247771973e7c12e10bb1567da169c76aefd019c2b43b2ce97d`.
This promotes the declared repeated observation to `verified-runtime`, not
whole-game stack ownership or helper integration. The runner checked native
exit 52, but did not preserve a separate exit-code receipt; the auditor
states that provenance limit explicitly.

The [strategy review](schala_package_interrupt_strategy_review_2026_10_03.md)
now rules out borrowing the game busy byte as a helper lock: IRQ's later
unconditional clear can erase it, and the NMI fast return changes normal
frame service. A separate reviewed original timing model gives 67,112
master clocks for the unchanged small-registry diagnostic helper, including
conservative DRAM refresh. The general 32-target registry gives a loose
243,202-clock envelope. Both depend on explicit no-DMA/HDMA, no-interrupt
and uncorrupted-memory premises. Root rechecked the historical 124,904-clock
entry-to-IRQ gap directly in its pinned trace; that observed subtraction is
not a deadline or permission to reject an already charged action late.
The [calculation source](../tools/research_helper_timing_envelope_v1.py) emits
deterministic metadata and keeps all production flags false. A separate
read-only phase observer is the next concrete experiment.

An optional subscription-backed Claude source review timed out without a
response or provider completion receipt. It contributes no accepted review
evidence and was not retried after ambiguous delivery. Completed independent
local reviews and root-executed tests/reproductions support this checkpoint.
All game inputs and raw traces remain ignored and private. No production
hook, allocation, selector, completion protocol or eighth-PC claim is added.

## 2026-10-03 — half-fill boundary independently accepted

The preceding actual-NMI/timing checkpoint was pushed to CodaLilitari GitHub
as `0bd483ab268e3e65cfa843dc6a9ecc9348c59a7e`. Authenticated API and remote
branch identities agree; all sixteen changed files were fetched at that commit
and independently compared with the local committed bytes. Its receipt is in
the October3 publication reference. A fresh read-only GitLab check at 21:50 UTC
still returned `a0b17f6227ed6a54cdfb7c63e726feb94d26b89d`; no mirror write or
portfolio change has occurred.

The [half-fill v1 packet](schala_scene8b_half_fill_v1.md) closes the declared
local continuation at CD34F1 under explicit fixed-input/machine premises.
Positive byte s causes s word stores; s0 causes 16,384 stores, 32,768 distinct
indexed WRAM byte writes and one X wrap. Both DP45 setup word stores are
included. Address addition and a word's high byte carry into bank7F.
The comparison interval between canonical bases fits s1..224 exactly but is
not an approved allocation. Copy-safe witnesses s225/226 reach another base
or the separately established IRQ destination C867/68. No concurrent runtime
collision or legal vanilla producer has been proved.

Root reviewed the complete new source/tests/report, passed 38 tests and ran
two fresh CLI forms. Both match the author and independent peer's 44,048-byte
metadata, SHA-256 `97c7c22478aa688e6ceacb4508c3fc6b947dfdcc43930c0a8569402c6c7f10af`.
The collector performs 1,024 full local interpretations, 144 endpoint
interpretations, 64,512 mask projections and six actual canonical predecessor
replays. It checks 41 inherited identities before/after without pretending
to regenerate all older exhaustive collectors. The peer separately used a
mutable-memory model for 112 cases and checked all frame words and admitted
q/high combinations at s1. Exact review receipts are linked in the report.

The older copy packet already declared this continuation open and remains
unchanged. This result therefore adds evidence without contradicting a
published source. The proposed 8A/AB/8B writer chain still lacks a rooted
script, same-slot lifetime and intervening-writer proof. No MAP correction
is invented for an obligation that was explicitly unresolved. No production
hook, allocation, selector or actual eighth-PC behavior is added.


## 2026-10-03 — repeated resolver phase and explicit early-interrupt scope

The accepted half-fill checkpoint was pushed to CodaLilitari GitHub at
`36f5093614fb00ab182791f865de84fd8fd37de9`. Authenticated API and Git main
agree, and all ten changed files were independently downloaded and checked
against their committed bytes. Its exact receipt is retained in the October3
publication reference. GitLab synchronization has not been authorized by an
answer to the pending question; its check and the portfolio check remain read-only.

The first phase observer completed natively but correctly refused its declared
unsupported sequence: pre-effect at poll374 precedes the poll378 resolver by
eight balanced interrupt contexts. There was no actual nesting or export
failure. The unchanged v1 source, tests, archived inputs, trace, process52
receipt and host rejection are preserved. A separate v2 wrapper validates all
original records, individually matches those early contexts to the accepted
historical trace, then reuses the frozen v1 validator on an explicit projection.
The original trace remains intact and the projection is not claimed as an
interrupt-free native execution. Both scene gate markers now require their
own immediately following watched data read with exact CPU/context continuity.

After source review and 43 preserved v1 plus 34 v2 tests, a fresh v2 pilot
completed. Its entire decoded observation equals the rejected v1 trace except
for the schema name. Two subsequent isolated full v2 runs then produced
identical 17,782,665-byte traces, SHA-256
`7e2d2925f8523a134721427c1001128a073b6b64518abe3810ee637cb5e71bb0`.
Each has 2,261 records, 161 engine fields per record, eight early contexts
and the following IRQ/NMI pair. The resolver interval remains 4,244 master
clocks / 548 CPU-counter increments. Each log contains 28,319 uninitialized-
read diagnostics; this is not a warning-free or general initialization proof.

The separate acceptance auditor checks the actual 38 guarded identities,
28 archived sources and ten staged inputs per run, exact inventories and
process52 receipts, then reconstructs the launch receipts and full manifests
from complete trace revalidation. It passes 39 original/adversarial tests.
Root's two fresh CLI outputs and the independent peer's output match the
53,831-byte accepted reference, SHA-256
`8e3898c7886a88e166bf5fd13f69ac37b44b59bd202d5780c0a8ae98ae30c120`.
The peer additionally verified eighteen original rejection challenges.
The [report](schala_package_resolver_phase_v2.md) links exact review provenance.

The accepted observation exposes all eight HDMA channels enabled and unfinished
at resolver entry, despite no pending service at that instant. It also exposes
the next evidence gap: the observer did not capture the IRQ circuit's distinct
h/v counters or all relevant overclock settings. PPU position and timer values
alone cannot certify a deadline. No new upstream mapping contradiction was
found here; the v1 result is a documented protocol scope limit. The helper
still has no game placement, stack-ownership certificate or production binding.

## 2026-10-03 — final conditional HDMA checkpoint and explicit next experiment

The resolver-phase checkpoint was published to authenticated CodaLilitari
GitHub as `6b4a58826aca0f6c58a284a6018a3213cc1c53ea`. The commit API,
branch API and Git remote agree; all eighteen changed files were independently
downloaded at that exact commit and matched to local committed bytes. The
October3 publication reference retains that receipt. A fresh read-only GitLab
check at approximately 22:44 UTC still returned
`a0b17f6227ed6a54cdfb7c63e726feb94d26b89d`. No GitLab write or portfolio edit
was made; the synchronization question remains unanswered.

Root accepted the separate [HDMA v1 packet](schala_package_hdma_timing_v1.md)
after complete source/test/report review, all 13 focused tests, and two actual
CLI reproductions matching the author and independent peer. The accepted
reference is 18,674 bytes, SHA-256
`0d672ccd12b658e7ffff59b4acf45465749dd84f130ee5cf4e4a400cce8e0e8d`.
Root outputs and acceptance receipt are under
`private/test_runs/hdma_root_review_20261003/`; peer receipt is
`private/test_runs/resolver_hdma_peer_review_20261003/public_review_receipt.json`,
SHA-256 `5bfe61cb3684c564a79ac9289a37368e64499ba6627fa17ca292f3c3cd194e51`.
The frozen report's preparation-status paragraph is historical; this entry
records acceptance without changing its reviewed bytes.

Generic HDMA service is at most 472 clocks and initialization 216 under the
pinned source model. The fixed-fixture helper composes to 144,088 clocks
coarsely, 106,689 with at most one initialization, and 106,342 when the
observed phase and declared frame minimum exclude initialization. The argument
bounds every finite prefix, including partially started service; it does not
assume completion to establish progress. The collector checks 131,072 channel
cases and 456 alignments. The peer's independent private model additionally
checks 4,194,304 counter/payload cases. No native helper execution or game
admission is established by these calculations.

Review corrected an insufficient premise in our earlier unpublished private
proposal: nonnegative extra-scanline settings alone are not enough. At pinned
Mesen revision `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`,
[SettingTypes.h lines 572-573](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Shared/SettingTypes.h#L572)
uses uint32 settings, while
[SnesPpu.h lines 56-60](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.h#L56)
uses uint16 cached thresholds: `(225+65535) mod 65536 = 224` is the original
counterexample. The public packet requires line/frame minima directly and
leaves actual settings/cache provenance unproved. Both private predecessors
are preserved. This corrects our proposal, not an upstream mapping claim;
no new MAP entry is invented.

The minimal next-observation design is retained at
`private/test_runs/resolver_irq_admission_design_20261003/design_note.md`,
13,965 bytes, SHA-256
`a65a7c1aeaefa202b03681a41623154b8898cbce0b9d3640911e55a5bbb95751`.
Its source receipt pins six individually retrieved exact-revision primary
files, checked against upstream Git blobs. Add the real serialized uint16
`internalRegisters.hCounter` and `internalRegisters.vCounter`; retain all
existing pending-state fields and observe post-load line 0 to 1 under guarded
zero extra-scanline settings. This establishes a prospective cache-refresh
witness without inventing hidden Lua fields. The design is not implemented
and no successor native run is claimed.

HDMA source-read/rendering isolation, exact request timing, wrapper costs,
physical game-stack ownership and the earlier pre-effect versus later-resolver
lifecycle remain open. The session ends at a reproducible research checkpoint;
the eighth playable character remains unfinished. Production hooks, expanded
allocations and high-selector bindings stay unapproved. All game inputs and
raw traces remain private and ignored.

## 2026-10-03 - public refresh, IRQ counters and timing-cache crossing

A new bounded goal refreshed outside reverse-engineering work, then advanced
BA-NATIVE-INTEGRATION-DESIGN through a separately versioned read-only observer.
The date is October 3 in America/New_York; the actual review/run receipts are
October 4 UTC. This is a new checkpoint, not completion of the eighth PC.

The [public-source report](online_research_2026_10_03.md) compares exact heads
against September 8. Pseudoarc/ctrando advanced 22 commits and includes a
September 10 Beast Toss counter-handshake fix worth a later canonical audit.
The RetroPortingToolKit framework advanced 434 reported commits; the retained
comparison is capped at 250 commit entries and 300 files. It still requires
game-specific integration and excludes ExHiROM. The two tracked disassemblies
and main editor/mapping heads are unchanged. No new reproducible additive
eighth-PC patch was verified. Direct forum refresh failed, and restricted
authenticated repository search was retained as failed rather than disguised
as comprehensive coverage. Source receipt SHA-256:
`a46a12970fd9c5bcd024b9f491bea0b3c08fb547a14686210ea7dbe97afd0fa9`
for references/online_research_2026_10_03.json (8,019 bytes).

The separate [phase-v3 observer](schala_package_resolver_phase_v3.md) captures
internalRegisters.hCounter/vCounter and two post-load cache-crossing events,
with explicit zero extra-scanline arguments. Two actual full process launches
completed with exit 52 and identical 17,946,524-byte traces, SHA-256
`cbcfee04c0eab0381d77392e43baf8cc5ed3c62b8a22ac533bf2d263424bd619`.
Each has 2,263 records and 163 engine fields. Removing only the additions
reproduces the entire accepted v2 trace; the original 4,244-clock / 548-cycle
resolver interval and all watched bus/context records remain unchanged. The
new observed internal IRQ counters at resolver entry are H=186/V=119. Each log
still contains 28,319 uninitialized-read diagnostics, preserved as a limitation.

The first v3 pilot rejected my new main-thread-only cache premise. Both new
records actually lie inside historical normal-NMI context 1, strictly between
entry 2,019,782,308 and RTI 2,019,989,232. The crossing is clock 2,019,832,632, line 0/H=0
to clock 2,019,834,076, line 1/H=80: exactly 1,364+80. The rejected pilot, original
collector/launcher/test source archive and host rejection remain unchanged in
private/test_runs/resolver_phase_v3_pilot_20261003_1/. The corrected second
pilot passed, then two separate full runs were performed. This corrects our
unpublished expectation; no upstream mapping error or new MAP entry is claimed.
Hidden PPU cache values remain outside the Map API; the valid-source-state
bootstrap premise is explicit and is not discharged by these snapshots.

All 178 focused phase tests passed: preserved v1/v2 coverage plus 23 new
observer and 39 new acceptance cases. The 39 acceptance cases were rerun after
the evidence-authentication clarification. The separate auditor checks exact
source/staged/archive bytes, canonical process/manifest receipts, all trace
semantics and equal pair bytes. Accepted reference SHA-256:
`ef647b161531bc1d207f3aa1feacb4b8d669863e04b7390348d0d16381a3d1c1`
for references/schala_package_resolver_phase_v3.json (63,846 bytes).

Antigravity returned two subscription-backed, tool-denied source reviews.
The [full disposition](external_review_2026_10_03.md) preserves disagreement:
its unsigned-receipt critique is accepted as an authentication limit; the
auditor now explicitly reports that file consistency cannot authenticate
execution against fabricated receipts. Actual process invocations are separate
coordinator/tool evidence. Its instruction-overshoot claim is contradicted by
Mesen's two-clock Exec/event scheduling; the cached-state objection restates
an already-declared premise and does not override the pinned input hash.
Neither critique nor agreement is promoted to model authority. Review metadata
is references/external_review_2026_10_03.json (1,751 bytes), SHA-256
`81174f5f12ce40b76c398fcb12e457a8bfa7b3084d61848822e0eeb2b4482ba7`.

Claude Code attempted its packet but timed out at 1,800 seconds without an
answer; job 8cf82ea83be948d89d7af51a80e106fe remains delivery_unknown. No
automatic resend occurred. Grok's initial user-skill startup refusal was solved
by a per-child empty USERPROFILE, preserving HOME and its dedicated auth
profile. Catalog and SuperGrok weekly 17% usage were checked non-generatively.
The initial paid-extra question was resolved by Andrei confirming it is
disabled. One bounded Grok IRQ-timing review is now running; the exact packet
and helper receipts are retained. Its result is not yet claimed. No billing or normal setup was
changed. Native subagents hit this old chat's thread limit.

Next work is an additive IRQ request-transition proof, distinct from observed
handler latency. Preserve v3 rather than rerunning it without source drift.
HDMA source-read/rendering isolation, wrapper timing, physical game-stack
ownership and the pre-effect versus later-resolver lifecycle remain open.
All production hooks, allocations and high selectors remain unapproved.
ROMs, SRAM, states and raw traces stay private. GitLab synchronization remains
unanswered; no GitLab write or portfolio edit was made. After exact GitHub
publication verification, the user-authorized fresh project chat will receive
these handoff paths and the precise next gate.

Publication preparation normalized the new launcher to the repository LF
contract. Because its source hash changed, two final-source native replays
were executed as resolver_phase_v3_full_20261003_3 and _4; their complete
traces remain identical to the earlier pair. The acceptance reference now
pins that final source. Runs 1/2 and all pilots remain unchanged. All 178
phase tests passed again. The committed developer-log prefix is byte-identical
to its previous revision; only this new entry and follow-up are appended.

## 2026-10-03 - completed Grok review and fresh-chat handoff

The preceding research/v3 checkpoint was published as GitHub commit
`7ac6499ae484a6598c1727659f18979aaf838a74`. Authenticated commit and branch
reads and the remote main ref agreed. All 16 changed files were downloaded at
that exact commit and matched against the local committed bytes. The receipt
is private/test_runs/counters_checkpoint_20261003_publication.json. GitLab
main still resolved to `a0b17f6227ed6a54cdfb7c63e726feb94d26b89d`; no GitLab
write occurred. The portfolio's Project Epoch case still accurately states
that this is unfinished research and no finished eighth-character release is
available. It was not edited.

Grok completed its initial bounded source review and a same-session follow-up
in `01a10469-782e-79c1-bd85-71071fc07e34`. Before the second request the
official usage panel showed 18% weekly use; Andrei's explicit confirmation
that paid extra usage is disabled remained in force. The follow-up thanked
the reviewer, supplied omitted source bodies and challenged two errors.
Grok acknowledged both: count one needs an already-set flag to assert the
CPU source, and adding four clocks can invalidate a not-before bound. The
initial answer's opposite statements are preserved in the private transcript
and explicitly rejected in the [review disposition](external_review_2026_10_03.md).
These are review corrections, not newly discovered ROM mapping contradictions.

The useful nested-Exec observation was checked independently against pinned
Mesen source and a private draft: refresh at H=538 can omit that counter
update and duplicate H=578, leaving the final H=754 counter at 186. The same
end value does not prove a uniform four-clock schedule. The follow-up gives
the same compensating-update explanation. H=538 is a conditional example;
neither the draft nor the review observed that refresh position in the native
trace. Callback closure, fixed timer/enable premises, reset behavior and CPU
acceptance remain separate proof obligations. The candidate 124380-clock
source-assertion lower bound remains unaccepted and must not admit a helper.

The official export succeeded and contains exactly User/Assistant/User/Assistant;
all four messages match the saved packets and results after newline
normalization. Export: 37,717 bytes, SHA-256
`a0031233837190895e68daab6231d0e93bf938293f49273c7154ffcd8222d9e5`.
The follow-up result's provider UTF-8/LF digest and its CRLF file digest are
recorded separately; they are not conflicting execution identities. See
private/reviews/20261003b/grok_irq_followup/persistence_verification.json.
Updated public review metadata is 2,764 bytes, SHA-256
`c9bdcbf9e34b97d96c4c5866b9bdf955181f4c1b69a11efc4154988f89686f27`.
The earlier log entry and its 1,751-byte metadata hash describe the previous
published state and remain unchanged. Claude Code still has no returned
answer; its 1,800-second timeout is delivery unknown, not approval or failure
of the technical proposal. No automatic retry was performed.

The next bounded goal is a separately versioned source-pinned IRQ transition
model, including nested event execution and adversarial pending-count/flag
states. Draft paths, hashes and reproduction commands are recorded in
private/reviews/20261003b/next_model_handoff.json. They are exploration, not
accepted prerequisites. The accepted v3 tools/reference and all earlier
proofs remain byte-identical; this follow-up changes documentation and review
metadata only, so it does not repeat the 178 tests or native runs without
source drift. The fresh project chat is authorized by Andrei and needed for
new subagent capacity. Production hooks, allocations and high selectors remain
unapproved, and no game input or raw trace enters the publication allowlist.

## 2026-10-03 - IRQ request transitions, recursive events and CPU gates

The fresh project chat resumed from verified local/GitHub checkpoint 3360a486
and set a new bounded goal. The [separate IRQ request-transition v1 packet](schala_irq_request_transition_v1.md)
now completes that source-model checkpoint. The eighth playable character
remains unfinished; BA-NATIVE-INTEGRATION-DESIGN stays open.

The original register core preserves consume-pending -> flag/source -> H/V
update -> comparison/rearm order, all uint8 pending values, uint16 counters,
the H6 horizontal exception, timer writes and TIMEUP acknowledgment. The
separate Exec projection reproduces the real 40-clock DRAM recursion and
current-H outer continuation. HDMA begin requests work; transfer bus effects
remain excluded. CPU sampling, post-op acceptance selection and handler entry
are kept separate, including stale samples across SEI/source clear, DMA lock,
NMI priority, WAI and the STP transition versus later stopped calls.

Fourteen exact-revision Mesen files were freshly fetched and checked against
SHA-256, Git blobs and earlier local identities where available. The collector
pins the full accepted phase-v3 reference and exact matching resolver seeds.
The source manifest is references/mesen_irq_transition_sources_v1.json;
the final 35,737-byte result is references/schala_irq_request_transition_v1.json,
SHA-256 846a54df9c490cee263bb86cf1b351683262562915eaecb148e3c182bd1686a7.
Independent root and native-peer CLI executions produce identical complete
bytes. The earlier peer generation is preserved separately, not relabeled.

All 81 new focused tests pass, including 16,384 pending-state equivalence
combinations and 65,536 CPU status/source pairs. Independent peer review also
executed 12,000 hostile core comparisons against a separate imperative source
interpretation without mismatch. Its four Exec findings were corrected with
regressions: invalid starting event phases, recursive duration overruns,
continuation after refusal and uint64 wrap. The 178 existing phase tests pass.
No emulator matrix was rerun; accepted native traces, source archives, rejected
pilots and all older evidence packets remain unchanged.

The exact-seed DRAM-only host projection produces match/flag/source offsets
124740/124744/124748 under explicit callback, register, reset and raster
hypotheses. An abstract all-1360 comparison produces 124372/124376/124380.
Those figures are conditional host results, not observed or certified game
request times. All game, CPU deadline, handler-entry and production flags
remain false/null. The unused auto-joy field and derived enable cache are
labeled as model inputs/premises, not invented observations.

Two deeper counterexamples matter. Repeated synthetic six-clock line-boundary
reentry duplicates H6 and reaches source62004 at PPUline165. Grok's sharper
H10 case was independently executed and added: a ten-clock callback on the
arming line makes flag and source share offset124744. Both scripts explicitly
invalidate the ordinary callback hypothesis; neither is claimed actual native
behavior. Reverse DMA/HDMA can also write IRQ control registers, and DMA reads
can acknowledge TIMEUP. CPU-store absence alone cannot close those gates.

Grok reviewed the source packet and received a verification/thank-you follow-up
in the existing project session 01a10469-782e-79c1-bd85-71071fc07e34. The
unchanged current catalog retained grok-4.7/xhigh, and official SuperGrok usage
was freshly observed at 18% before each request. Paid extra usage remains off
per Andrei's explicit confirmation. The final official export matches all
eight saved messages; it is 83,232 bytes, SHA-256
c6c79c8b6d90c7bc2e26f54c3a5cc267ce0d486a2daa63187877dea932cd68c9.
The [review disposition](external_review_irq_transition_2026_10_03.md) preserves
its whole-program closure objection as an unresolved antecedent. Its final
reply had no blocking objection to the conditional publication, while stating
it had not run tests or inspected the new exact-seed entry point. Final-source
inspection and reproduction came from the coordinator and native peer. No
reviewer remains running; the earlier Claude timeout was not retried.

Next: a bounded DMA/HDMA bus-effect and callback closure design that separates
already observed fields from genuinely missing evidence before any new native
run. Do not compare the IRQ offsets with the old helper envelope as though
their premises were jointly established. Wrapper cost, physical game stack,
interrupt policy and pre-effect refusal versus later completion remain open.
All production hooks, allocations and high selectors remain unapproved.

Publication is limited to the exact allowlisted original source, tests, hash
metadata and documentation. Game inputs and raw traces stay ignored/private;
GitLab and portfolio writes remain outside this checkpoint. The exact GitHub
commit/branch and downloaded-file comparison receipt will be retained at
private/test_runs/irq_request_transition_v1_publication_20261003.json.

## 2026-10-03 - DMA IRQ domains and callback inventory v1

This new Project Epoch continuation completes an additive source/reuse packet
at [DMA IRQ closure v1](schala_dma_irq_closure_v1.md). It preserves every older
accepted proof. The frozen resolver-v3 auditor was rerun offline and reproduced
its reference byte for byte; no emulator matrix or game mutation was performed.

The new domain model handles exact-width channel fields, all transfer modes,
manual zero-size wrap, both payload directions, discarded HDMA counter reads,
indirect reloads and the WRAM/$2180 exception. Under explicit mapping,
configuration, service and external-mutation hypotheses, all eight observed
entry channels keep table/payload A reads in bank $7E and B writes in $21xx.
Direct TIMEUP/IRQ-register effects are therefore excluded in that conditional
address model without recovering table payloads. The supplied 65,536-service
cap is not a timing bound. Synthetic bank-zero/reverse examples retain the
missing hypotheses' significance. No handler effects or runtime premises are
certified by passing boolean arguments.

The independent hardware reuse agrees with root: entry/tail 81 records and 4,244
clocks; through following IRQ 682 records and 124,904 clocks; zero watched hardware
events in both intervals. The first later write is $4200=$81 at +125,226; the full
window has 280 hardware writes and later channel 7 reconfiguration. The collector
omits $4211 and PPU payload traffic, autojoy internals and controller types.
These original-game intervals do not execute the proposed helper.

The callback packet pins 42 upstream files, 24 qualified facts and 70 exact
source spans at Mesen 137ae7ce. SETINI changes raw rendering flags and buffers
but does not directly change cached timing inputs or the 1,364-clock predicate
within 119..211; the live short-line exception is 240. Valid fixed caches and
no external refresh/reset/load remain premises. Exec's PPU callback is debugger
dispatch; rendering precedes H=0 while autojoy/SPC update follow it. With cached
VBlank 225 the local SPC-update branch makes no SPC call in this interval.
Concrete ordinary controller and inert debugger branches close conditionally;
runtime target binding, other devices, enabled coprocs, debugger/host hooks,
outer bus callbacks and reset/load remain explicit frontiers. Sequential DMA
service is not automatically recursion into an unfinished Exec dispatch.

Root passes 293 selected tests: 34 new, 81 existing transition and 178 existing
phase tests. The model's independent mutable scalar replay contains 1,792
scenarios of six services each and all 1,024 B-port addition combinations.
Native cross-review corrected late input-identity capture and completed the
controller, memory-write and debugger getter evidence spans. The auditor now
captures identities before use, parses hashed buffers, checks exact pinned
inventories and 70 spans, and rechecks the initial identities after computation.
Mutation tests cover omitted/duplicated inventory and concurrent source drift.

Root verified all 42 source files against the earlier Git tree and freshly
fetched eight exact primary URLs. The independent peer passes all 34 new tests
and reproduces the final 77,504-byte metadata exactly, SHA256
0b99435c6b6209188284ebfc6f5db77f2726db0ec501e81872346286e146b50e.
Original and final review receipts, the superseded root result and test receipt
remain in private/reviews/20261003d/. Three native collaborators contributed;
no external provider was newly dispatched and no reviewer remains running.

Next is DMA-CALLBACK-BINDING-DESIGN: inventory accepted launch/state evidence
for actual mapping, controller, coprocessor and debugger targets before defining
only genuinely missing read-only observations. Do not promote this conditional
packet to a game deadline, helper admission, production hook/allocation,
interrupt policy or eighth-PC support. Wrapper cost, physical stack ownership
and pre-effect/later-resolver lifecycle remain separate obligations.

Publication is the explicit source/test/metadata/documentation allowlist only.
Private game inputs and upstream source downloads stay ignored. GitLab and
portfolio remain outside this checkpoint. The exact GitHub commit/branch and
downloaded-byte comparisons are recorded separately at
private/test_runs/dma_irq_closure_v1_publication_20261003.json.

## 2026-10-07 - Resume toward a bounded playable eighth identity

Andrei requested a new goal and explicitly authorized focused AI delegation,
including Claude Code through existing subscriptions. The active goal is a
genuine eighth identity with independent state, field behavior, an ordinary
battle action and a save/cold-load round trip, preserving all seven original
characters. SNES remains the primary route; recompilation is a fallback.
The ordinary-Attack proposal reuses canonical low-action mechanics, so the
unfinished high-Tech package helper is not on this prototype's critical path.
No playable eighth character is claimed at this checkpoint.

The native save-layout v1 diagnostic passes two identical saves and two
identical loads. It changes only two guarded loop-bound operand bytes and
uses explicitly recorded debugger preparation. Native transfers cover 2,100
bytes across ten regions while protecting an opaque candidate-record marker;
the save reads all 80 relocated compatibility bytes and the load replaces all
80 distinct poison bytes. Seven original record positions remain unchanged.
The save's authoritative pre-RTL SRAM snapshot passes clean-ROM cold-boot
validation; subsequent resumed load execution is a separate observation.
An installed wrapper, real PC07 persistence, sidecar and global WRAM ownership
remain open. The accepted metadata-only chain and offline reproducer are
`references/schala_save_layout_native_chain_v1.json` and
`tools/revalidate_save_layout_native_chain_v1.py`. The reference SHA256 is
`7ee90c74c042b8b5fdcd60dd4b8475a4d7c548f70992b3641fda2dbdce38b0a4`.

The bounded menu relocation uses seven guarded operand substitutions, then
follows native load return, menu entry, the Tech screen and field return.
Two controls and two relocated runs agree in their declared observations;
all seven original records, roster and SRAM remain preserved. Root inspected
the principal screenshots. One early repeated PNG differs in the save-point
orb's animation frame despite identical native trace and memory snapshots.
The pair reference is `references/schala_compat_menu_pair_v1.json`, SHA256
`b3e57bb4c906a6fa56aac6f5be2617bb003cc7bb1d6433f56b3d4cdfdba6a182`.
Reproduce offline with `python tools/revalidate_compat_menu_pair_v1.py`.

A narrow additive v2 observation resolved the two residual Y bytes without
reopening the prior matrix. Each mode records 14,196 aligned accesses to four
physical bytes; exactly 16 values differ, attributable to coroutine PHY/PLY
and the existing field backup/restore. The decompressor writes identical
values before reading its overlapping buffer. No captured screen-X consumer
reads the differing values. Both complete original observation projections
match both accepted v1 runs of their mode. The selected question is closed;
this is not universal field-index safety. Root reproduced the independent
receipt with `python -B private/research/compat_menu_v2_residue_review_20261007/reproduce.py --check private/research/compat_menu_v2_residue_review_20261007/receipt.json`.
Its SHA256 is `f4e90a5091736762ab82159c8eeb4a62cc6e5d4f3289c01071adfd462f989fe8`.

Claude Code completed two subscription-backed source reviews. Root and an
independent local collaborator reconciled the consequential findings against
source and trace data. The second reviewer received six files rather than
all ten bundle dependencies and did not execute or hash them; no blanket
approval is inferred. Its answer is retained privately, SHA256
`85ef62a4780de6061388110d14f3a7f803ab632fb84de6abf2bad079a7700edd`.
The additive `tools/audit_save_layout_native_review_v1.py` checks exact ordered
physical stream equivalence and the observed native global metadata stores.
Its seven tests include wrong-slot and same-value wrong-context refusals.
Together with the native-layout, checkpoint, chain, menu and residue tests,
82 focused tests have passed. Existing frozen packets remain unchanged.

Andrei then explicitly emphasized avoiding repeated completed work and using
community maps while allowing that they can be wrong. The current handoff now
records reuse rules and concrete dependencies. In particular, do not redo
the accepted all-event parser cross-check, the historical eighth-character
mapping survey, or completed native helper/serializer/menu matrices without
an identified new condition. The selected event0125 insertion inventory uses
the existing parser; it does not invent event formats or object insertion.
Community provenance includes Mauron's PC-before-NPC ordering and doubled
object-index rule, plus Temporal Redux / Jets of Time's object insertion and
call-renumbering implementation. Existing corrections apply to our claims
as well as community claims; MAP-003 supersedes our overbroad criticism of
base-stat order. Local confirmation is not a first-ever discovery claim.

All game inputs, generated diagnostic images, SRAM, checkpoints, traces and
review packets remain private. No commit, push or external publication was
performed for this checkpoint. See CURRENT_HANDOFF.md for the exact next
prototype step and any later additive results.

The selected event0125 inventory then passed root's 15 focused checks and
exact metadata reproduction. Its separately versioned in-memory transform
passed 12 checks: a complete existing PC object's copied body now targets07,
with the loader and thirteen identity comparisons adapted, while all original
objects remain intact. Actual pointer/branch validation and inverse projection
recover every original packet byte. The 2,553-byte result's SHA256 is
`d81b7bfc4db23d95adc8a576ba2472e1cd005ab8e43cf997fda3e5e3da29a51d`;
the metadata-only reference is `references/pc07_selected_event_transform_v1.json`,
SHA256 `0bb253c1f296e5719b204052588f25254a045a3cc716d32127347b6e304cdd66`.
Reproduce with `python -B tools/transform_pc07_selected_event_v1.py --rom <canonical-private-US-Rev0-ROM>`.
These are construction results, not native PC07 behavior. Credit the existing
community insertion algorithm and the already accepted decoder/topology work.

One new clean-ROM field observation confirms the exact later staging boundary:
scene entry atC00085, canonical packet/builtins and actual stored0111 atC05D36,
then actualC00112. It reuses the accepted checkpoint and isolated launcher;
four focused new-boundary checks pass. Trace SHA256 is
`95a1528b0c2cad29984fa86c27f2337b7e77710c9b371b75418d4492925428e0`
under `private/test_runs/mesen2/pc07_field_entry_v1_run1`. Seven records and
SRAM remain unchanged. The short walk moves the leader and first follower;
the watched third-follower coordinates do not change. No monitored scene-call
site executes. Root inspected the idle/left images. Preserve this useful
negative movement result and lengthen the upcoming PC07 diagnostic inputs;
do not repeat the clean observation merely for a matching pair.

The separate PC07 field v1 pilot stops at poll30 on a known compatibility
consumer, rather than reaching movement. Preserve
`private/test_runs/mesen2/pc07_field_probe_v1_run1`, source bundle
`67ff816f41fa0a5f34d4c8a3c55224577398e3f58419373052e8727baaee810c`,
trace SHA256
`2208b2883d8354ee17e51ce5f635538faece9c644c6d0f35530fb27b74b08535`.
Reproduction: `python -B tools/run_mesen_pc07_field_probe_v1.py --output <fresh-private-directory> --run-reviewed-bundle 67ff816f41fa0a5f34d4c8a3c55224577398e3f58419373052e8727baaee810c`.
Evidence level remains rejected-pilot. Independent read-only review of the
recorded prefix verifies the full staging diffs and 2,725 injection/readback
pairs, native generic80 logical07/role2/object10 publication, and both actual
graphics returns with identical nineteen donor ROM reads. The candidate uses
one explicit debugger A-low substitution; no native graphics adapter exists.
Native write event row10146 atC282E4 targets2857 with00 versus candidate+27=8F;
the guard fails immediately, with no postfailure readback or movement snapshot.
Root omitted the previously accepted compatibility operand relocations from
this first probe. Correct by reusing that builder, not by relearning its map
or weakening the record guard. Consumers execute beforeC00085, so compatibility
must be prepared at the acceptedC2E65B point; identity publication stays later.
V1 sources and failed output remain unchanged; the correction is separatev2.

The corrected v2 run completes through poll400, exit63, 45,184 trace records.
It reuses the unchanged guarded seven-operand compatibility builder, changes
exactly14ROM operand bytes, and prepares the compatibility copy atC2E65B.
Record/roster/joined preparation remains atC00085; event and graphics staging
remain the previously reviewed v1 operations. Source bundle:
`e5ff0b284a76a712c206933d492d83e295f6df86bd2b5250b28e27429e65afaa`.
Reproduce with `python -B tools/run_mesen_pc07_field_probe_v2.py --output <fresh-private-directory> --run-reviewed-bundle e5ff0b284a76a712c206933d492d83e295f6df86bd2b5250b28e27429e65afaa`.
The accepted-emission target hash is
`34937f84d1b6905171226a800a065b07912b1a790bad846bc82d6520784eef79`;
no production hook/allocation catalog changes. Recorded output lives at
`private/test_runs/mesen2/pc07_field_probe_v2_run1`; trace SHA256
`1ce216f8a903cfdedc0fc24643515fb3c11c2ed50be9cd6fdd1586c18724039a`.
Host validation passes all three complete preparation diffs and2,725 explicit
byte-write/readback pairs. All seven original records and exact input SRAM
remain unchanged across ten snapshots. Candidate logical07 owns a distinct
record withHP968 while donor00 retainsHP969. Third-follower screenX changes
184/170/150/154 atpolls90/180/280/400. Root viewedpoll180/400 screenshots,
which show Crono, Marle and a second Crono-looking candidate. This is new
selected-prototype movement evidence, not discovery of the community format.
Evidence level: emulator-assisted-runtime-observation, awaiting separate
offline review. No native graphics adapter, ordinary Attack, menu support or
PC07 persistence has been demonstrated. No identical repeat is needed merely
to obtain a pair; preserve this progress and advance the existing Attack plan.

The separate offline v2 review now passes. Root read its source and reproduced
the metadata receipt byte-for-byte without an emulator launch or image emission:
`python -B private/research/pc07_field_probe_v2_review_20261007/reproduce.py`.
Receipt SHA256 is
`328745a195b3d4c0bd9790545bda856c4db3d6b4b0b78e155894f7a9fb4a1e47`;
reproducer SHA256 is
`54b030fb5378f41462aa75f514926dc5bb74a1ae2709459569335da03b6ecf31`.
Each of the three actors has 2,480 watched coordinate-byte stores after poll90;
changed-store counts are 198/167/136 for IDs00/01/07. PC07 first changes at
poll166, rows22831 (world X) and22837 (screen X). The native stores reconcile
with all later coordinate snapshots; CPU coordinate-read callbacks were not
collected. The known C282E4 writes now target2CC7/2CC8 atpolls0/30. No native
record or SRAM writes are observed. The two early pre-render PNGs are empty;
only the separately inspected later screenshots are visual evidence. Accepted
scope is one verified emulator-assisted selected-field diagnostic, with all
native-adapter, battle, menu and PC07 persistence limitations retained.

### October 7: Epoch preservation and destination/battle source preparation

Andrei explicitly required the Epoch vehicle to be preserved or deliberately
relocated. The existing corrected character map already distinguishes naming
selector07 and Epoch's six-byte name at7E2C4D..52 from a new playable identity.
The plan preserves the vehicle in its existing contexts, adds independent PC
name storage/resolvers, and forbids a global07 rewrite. The selected field run's
ten WRAM snapshots retain identical Epoch-name bytes (SHA256
`90612fe14f612921ea04f64ea7b4a17834ddad86b415f0b7e2728d75b4e522b1`)
and unchanged SRAM; these snapshots do not prove boarding, travel or renaming.
Those vehicle interactions are now explicit completion requirements in the
current handoff. This is reuse and clarification of the existing map, not a
newly discovered universal character-ID allocation.

The separate event0126 in-memory transform is now independently reviewed and
root-verified with all eleven focused tests passing against the canonical ROM.
It preserves the original fourteen objects and introduces a separately copied
playable object8 before the original NPC/battle object. Six copied identity
literals and its loader are adapted; four original doubled object operands
are relocated. Exact inverse projection preserves all original bytes, including
all original function-pointer aliases and branches. The copied function4 audio
mailbox effect remains explicit. No complete cutscene/victory proof is claimed.
Result:1914bytes, SHA256
`6999eb3bb0cc4f9b3db8d6d405a8aa4ebe94a0b590b5c8f01c531a31c3bd3bc5`.
Source:`tools/transform_pc07_lavos_event_v1.py`; metadata-only reference:
`references/pc07_lavos_event_transform_v1.json`. Reproduce with its recorded CLI
or `CT_US_REV0_ROM` plus the eleven-test unittest command. No raw packet, patch
or ROM was emitted. The accepted0125 transform and native field run are reused.

The source-only ordered battle setup note is saved in
`private/research/pc07_battle_setup_20261007/setup_note.json`, SHA256
`a2a8d505720c943a56ab28f4b4a86e304c018e85e2be7c0bff695bcaf5ec7c57`.
Root checked its ten source identities. It adds the precise battle learned-mask,
name, graphics, equipment-owner and initial turn-order consumers. It also
corrects the earlier C1CF15 assumption: the reached normal initialization
calls read equipped item IDs and use CC0000 as a bank base, not as an indexed
new-character initialization row. The older proposal remains unchanged.

Root authored raw native donor lookup components without assigning ROM space
or emitting a game image. Independent review rejected v1's field hook because
the proposed five-byte span split an LDA operand and omitted INY. Preserve that
source and assembled component as rejected. The separate corrected v2 uses
the exact six-byte STA4202/INY/LDA05 span and restores the missing INY. Its157
assembled bytes differ from v1 only by C8 at offset45. Six table-reader routines
remain unchanged and restore incoming status before their final LDA; the field
routine remains restricted to the actual role2/logical07/roster07 object.

Current source:`asm/pc07_donor_read_adapters_v2.asm`, SHA256
`df0584a820d3b6b4994298cc1f0d6b3ffc4089797b42c5d6c6217d02a4e5a914`.
Raw component SHA256:
`315f409ece80e84c656930c47bc5a0d6e0f97d83aecc95b7c474abc2056750e7`.
Pinned Asar command, hashes, limits and reproduction are recorded in
`private/test_runs/pc07_donor_native_source_v2/receipt.json`; independent review
is `source_review.json`, SHA256
`5b1ea5cff78b79f2f1a12a008e6731873eb20adb9535012bf482f540e484c7ca`.
Root inspected that review and verified all eight input identities. Evidence
is assembled-source and component review only; no hook, placement, game-stack
ownership, native execution, ordinary Attack or vehicle function is proved.

The existing write guard and empty production catalogs are unchanged. Native
expanded-image packaging needs a distinct honest private diagnostic contract;
it must not label an experiment production-approved. Guard-file dependencies
must remain reproducible when that separate extension is implemented. Preserve
accepted source bundles rather than silently changing their pins or rerunning
completed emulator matrices. The playable-character goal remains active.

## 2026-10-07 — Native field helper observed; publication checkpoint and pause

One isolated Mesen run now executes the qualified field helper from ROM410000
through the real six-byte C0448D hook. PCs00/01 pass through and PC07 uses donor00
graphics; the independent record and candidate movement remain observed. The
run contains 45,276 trace rows and 2,725 explicit debugger preparation byte pairs.
There are no debugger CPU edits. Three helper windows reconcile fifteen actual
stack writes and fifteen reads, preserve sixteen live caller bytes per call, and
return with the required context. Their measured lengths are320/360/664 master
clocks. All original seven records, Epoch's six name bytes and ten SRAM snapshots
remain unchanged. Root inspected poll180/poll400 screenshots. This is one
prepared field run, not battle, PC07 persistence, vehicle behavior or a release.

The new private expanded diagnostic contract is separate from production. Its
fixed source, twelve sections and complete-diff guard accept191 changed bytes
relative to the validated inert8MiB scaffold. Only two forwarding APIs were added
to the shared guard; the remaining guard AST and empty production catalogs are
unchanged. A read-only historical source capsule at
private/research/pc07_guard_history_20261007 preserves29 source files. Its bounded
reproducer succeeds before and after the live guard addition without swapping
working files or changing old pins. This is local reproduction for two selected
workflows and a native-save bundle identity, not the entire older corpus.

Independent review found a host validator weakness: a forged ROM stack address
with matching low bits could pass the frozen mask-only check. The separate
validate_pc07_native_field_v3_stack_bus_v1.py wrapper pins that runner and requires
exact bank00 bus/physical equality. All30 actual events satisfy it; frozen runtime
sources and the trace remain unchanged. Root passed13 helper-validator tests,
17 diagnostic-contract tests and16 existing guard tests, then reproduced the
10,853-byte independent receipt with SHA256
fdfb4f48b23ec7aa694ba7f0d68831e994f39259f33ba80266db07c65cfb8032.

See [the public human report](pc07_native_field_checkpoint_2026_10_07.md) and
[the deterministic machine checkpoint](../references/pc07_native_field_checkpoint_2026_10_07.json)
for exact source/run identities, community attribution, reproduction and limits.
The public metadata builder checks pinned reports and sources; full native
reproduction still requires private inputs. No ROM, save, state, screenshot,
extracted packet or raw trace is published.

Andrei requested publication to GitHub, GitLab and the existing portfolio, then
a pause. The stopping point is this reviewed native field observation. Work
remains incomplete. After explicit resume, reuse the accepted event0126 transform
and ordinary-Attack setup note for the bounded field-to-battle experiment. Do
not rerun completed surveys or matrices without a concrete missing condition.
