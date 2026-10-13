# Project Epoch: first native PC07 Attack checkpoint

Date: 2026-10-13. Local research checkpoint; no publication or release.

## Result and scope

One complete instrumented Mesen run now carries logical PC07 from the selected
field route into battle, executes a controller-selected Attack, applies actual
damage, returns through native cleanup, and observes the candidate become ready
again. The target's HP changes from **8,000 to 7,038**, a 962-point decrease.
The game naturally selects the critical-hit animation branch. This is an
ordinary Attack command; the normal and alternate-path animation branches have
not been observed in this run.

The frozen runner's offline validator passes all 343,387 rows. Independent
review and root reproduction are recorded in the accompanying machine record.
There is one complete run, not a repeated pair. Preserve the incomplete first
pilot separately.

This is a private diagnostic milestone, not a playable eighth-character release.
The experiment still uses 4,642 explicit debugger WRAM preparation byte writes
and readbacks, temporary Crono graphics/name/action assets, and a selected
endgame checkpoint. It makes no debugger CPU edits. Normal acquisition, a unique
name/presentation, battle-to-field state commit, rewards, progression, Techs,
ordinary saves, cold loads and Epoch vehicle interaction remain open.

## What actually executed

The earlier accepted field-to-battle route is reused as acquisition, rather
than repeated as a separate qualification matrix. Its endpoint at C018A7 is
now crossed into battle initialization.

- The native loader copies 240 bytes from the three independent live records
  for IDs $00/$01/$07 into work slots 0/1/2. The candidate work identity is $07.
- Thirty complete installed battle-hook windows, covering fourteen distinct
  hooks, pass replay of their actual instruction states and ordered data/stack
  accesses. These include initialization, donor lookup, logical participant,
  effect-slot and MP-slot adaptation. The two unobserved hooks select the
  normal and alternate-path Attack animation families.
- Native Left/Right actor selection and two distinct A presses select the
  candidate's Attack and enemy slot 3. The controller queues physical actor 2;
  the native action ID is $75. The participant stores and subsequent readback
  establish **07 FF FF** before their consumer.
- At poll 3545, Attack entry is observed at C1BFAA. The pending-result boundary
  is reached at poll 3731. Four actual 16-bit HP-store/readback pairs all publish
  7,038. The ordinary caller return at C1BA80 and cleanup return at C18603 occur
  at poll 3732 with their actual stack transitions.
- The command-clear, queue-release and later readiness publications occur in
  order. At poll 4263, the final snapshot and evidence cut precede another
  controller-selected player action. Deferred emulator shutdown is outside
  the evidence boundary.

The HP readbacks are observer snapshots immediately after the actual CPU
stores, not claims of a separate subsequent CPU data read. The inspected
`pre_results.png` and `attack_ready.png` illustrate the borrowed appearance;
identity, ordering and HP acceptance come from the trace and memory snapshots.

The C1BFAA entry snapshot still contains action ID $43 and participant bytes from
earlier work. The candidate's action $75 and `07 FF FF` claims begin at their actual
later publications and C1D573 readback, not at that entry snapshot.

Candidate MP is 93 before and after its zero-cost Attack. Its work HP is 737
during that action and 608 at the later readiness snapshot because enemy work
continues between those endpoints. The later participant bytes also belong to
subsequent enemy work; do not treat them as a failed preservation of the
candidate's earlier `07 FF FF` publication.

All 22 WRAM/SRAM snapshot pairs preserve the seven original **live** records
and Epoch's six name bytes, with captured SRAM byte-identical to the input.
After their respective explicit preparation steps, the PC07 live record,
active roster/joined state and relocated compatibility block also remain
unchanged through the selected battle scope.
The donor's live HP remains 969 while PC07's remains 968. Battle work records
are allowed to change through native combat. This is not a save/load test or
proof that all original characters'
battle behavior is unchanged.

The final write reconciliation covers the declared battle ranges, not all
WRAM. The compatibility rear guard during battle is `2CF0..2CFF`: canonical
bootstrap clears `2D01` onward, so the old field-only `2D00..2D0F` extension is not
claimed as preserved. No helper interruption occurred in the observed
windows; no global interrupt, stack-ownership or performance bound is proved.

## Construction and preserved pilot

The existing 157-byte component remains at `410000`. A separate fixed private
contract places the unchanged 215-byte battle component at `410100`. Shared intent
and complete-diff audits cover 34 fixed sections and 481 changed bytes relative
to the pinned inert ExHiROM scaffold. Fresh assembly, both checksum copies,
the full boot mirror and inverse recovery of the prior field image pass.
Production hook/allocation catalogs remain empty.

Image SHA256:
`6d420e3daa6761a6ca2b0dd6bfc9119aa15967124f92c5d731a431f76726eefa`.
The ROM and all raw traces, states, screenshots and SRAM remain ignored and
local. The source builder, contract and reproduction metadata are retained.

The first collector timed out at its 900-second wall watchdog, exit `FFFFFFFF`,
without an Attack-entry observation or a collector assertion file. Its 24
complete startup hook windows independently pass; its trace is not a successful
action result. Preserve `private/test_runs/pc07_first_attack_v1_run1` unchanged.

Recorder v2 removes an unused full-CPU snapshot from ordinary instructions,
taking it only inside an active helper window or at a selected hook entry.
The complete inverse recovers the frozen v1 collector. Nine focused checks and
independent source review pass. A read-only comparison also finds all 270,687
rows of the incomplete pilot identical to the completed run's prefix after
removing only the header's source-bundle identifier. This is measured prefix
equivalence, not a claim about the unobserved remainder of the earlier run.
Input rules, callback checks, records and the
5,000-poll bound are unchanged; wall watchdogs are 1800/1830 seconds. This
optimization concerns instrumentation overhead, not demonstrated game slowdown.

The preparation checks comprise eleven focused write-contract tests, fifteen
observation-validator tests and nine recorder-delta checks. No completed native
semantics matrix was repeated as a prerequisite for this new experiment.

## Reproduction and provenance

The successful run is `private/test_runs/pc07_first_attack_v2_run1`.
Its source bundle is
`397ef413aac4e58f2dcb09fd855e862c4726de7c2b98c018b781ff036691df70`.
Trace SHA256:
`e2d58e302e937e70577a5d855954c9bbe08eb12bfafd50e53874a78d1a5aed00`.
The [machine-readable companion](../references/pc07_first_attack_checkpoint_2026_10_13.json)
pins the run, review, source and artifact identities. Reproduce the full
independent review and curated metadata without an emulator launch:

```powershell
python -B tools/audit_pc07_first_attack_checkpoint_2026_10_13.py
```

The independent receipt is
`private/research/pc07_first_attack_independent_review_20261013/review_v2.json`,
SHA256 `36cdac6bcac3d33baa906935c8a5348a9306841f203f8e1cafb08a2004e3bbb6`.
Root reproduced it byte-for-byte. It rehashes 98 source entries and 83 listed
artifacts, reconstructs all 13 staged inputs, and independently checks the
action/publication/damage/return/readiness timeline. Reuse this evidence;
do not relaunch a completed native matrix without a relevant changed source or
missing condition.

Underlying addresses and engine behavior come from the community-derived
disassembly, prior Vehek/Mauron/JLukas mapping work, Temporal Redux/Jets of Time
event handling, and the project's existing accepted packets. The original
adapters, fixed write contract and selected native qualification are the new
work here. This is not a claim to first-ever discovery of the underlying maps.

The [tool assessment](recomp_tool_practical_assessment_2026_10_13.md) remains
separate. A working headless recompiler strengthens the PC alternative, but
this native SNES action result supports continuing the bounded SNES prototype.
Neither result establishes a fully playable eighth character. The next work
should connect native battle state back to the independent live record and
then complete the versioned save/cold-load path, retaining the explicit Epoch
vehicle/name preservation obligation. Do not restart completed high-Tech or
general NMI mapping as a prerequisite for this ordinary-Attack path.

The next source-only gate already identifies a useful simplification: C1B442's
roster-based `ID * $50` destination naturally reaches `2830..287F` for PC07.
That destination needs qualification, not an invented new copy routine.
The current Lavos fixture's D8 flags `$93` forbid controller escape. A separately
proposed authored fixture could clear only that escape restriction (`$93` to
`$13`) and observe the real first escape-path commit before admitting the
rest of teardown. This would be deliberately enabled diagnostic escape, not
proof that vanilla Lavos can be escaped. An already escapable ordinary battle
is the alternative. Neither next experiment has run. Victory/progression has
additional unresolved consumers and is not silently included in this plan.
