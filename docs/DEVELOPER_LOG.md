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
