# Actual normal-NMI instruction and stack observation v1

Prepared: 2026-09-08; resumed and reviewed: 2026-10-03.
Status: **verified-runtime within the five selected observation intervals**.
Gate: `BA-NATIVE-INTEGRATION-DESIGN`.

This separately named observer measures five complete selected normal-NMI
instruction intervals in the unchanged clean-ROM replay. It records the
lowest stack pointer at every instruction boundary and bus callback within
each interval. It installs no helper and changes no CPU, ROM, or WRAM state.
The only initial state change is the same pinned checkpoint load used by the
accepted resolver-context observation; controller inputs retain that existing
schedule. The full five-interval experiment now repeats identically with
independent ledger review. It approves no helper integration.

The earlier [resolver context observation](schala_package_resolver_context_v1.md)
remains unchanged. It records selected handler watchpoints and explicitly
does not claim a complete stack low-water measurement. Its ordinary resolver
takes 4,244 master clocks and contains no interrupt entry. The new experiment
does not turn that replay into a publication-preemption test.

## Fixed intervals and their provenance

The input is the exact 4,194,304-byte US Rev0 ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The retained SRAM is 8,192 bytes, SHA-256
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.
The existing `battle_ready.mss` checkpoint is 261,614 bytes, SHA-256
`d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b`.
Its preparation history and diagnostic limits remain those of the accepted
context experiment. These are private artifacts, not source-controlled files.

The five input-poll positions were selected from the accepted prior context
trace at `private/test_runs/resolver_context_20260908_final1/trace.json`,
10,811,008 bytes, SHA-256
`6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679`.
Each new interval must match that trace's exact entry CPU state and observed
native hardware return frame. Poll positions are controller-poll counts,
not instruction counts or wall-clock measurements.

| Relative poll | Prior context ID | Prior handler-entry SP | Reason for selection |
| ---: | ---: | --- | --- |
| 379 | 759 | `$06CA` | First normal NMI after the observed resolver finishes; common-loader work |
| 500 | 1001 | `$06D6` | Active scene; one recorded scene-command dispatch in the old trace |
| 700 | 1401 | `$06D1` | Active scene; two recorded command dispatches in the old trace |
| 927 | 1855 | `$06D3` | Previously witnessed actual scene-latch clear |
| 928 | 1857 | `$06D3` | Subsequent inactive-scene interval |

The normal NMI at poll 378 occurs **before** the resolver entry at the same
poll. It is deliberately excluded from the post-publication selection.
The pilot selects only poll 379 and stops at poll 381. The full experiment
selects the five rows and stops at poll 930. Selection and stopping rules are
source-fixed; no arbitrary instruction, checkpoint, controller sequence, or
injected state can be supplied through command-line options.

## Closed observation boundary

Each interval begins at the pre-execution callback for `$D1:E77C` and ends
at the pre-execution callback for `$D1:E898`, immediately before its `RTI`.
The native four-byte hardware return frame already exists at entry. It is
observed there and checked again at the end; **its hardware pushes are not
separately captured by this experiment**. The original WRAM interrupt
trampolines must still be `JML $D1E77C` and `JML $D1FE97`.

The final callback observes the `RTI` instruction without executing it inside
the captured interval. Mesen's pinned native `RTI` implementation only pulls
the status, PC word and PBR, then performs its final idle. Consequently RTI
cannot introduce a lower stack pointer than the recorded interval. A later
IRQ or NMI is outside this closed interval. Nested normal/alternate NMI or
IRQ entry inside a selected interval is a hard refusal, not an assumed
extension of this proof.

The report will distinguish three quantities for each accepted interval:

- Lowest SP among all pre-instruction observations.
- Lowest SP among all retained instruction and bus observations.
- Additional bytes below the handler-entry SP, and the corresponding depth
  below the interrupted SP after including the already-existing four-byte
  native hardware frame.

None is a proof of available stack memory, worst-case game depth, arbitrary
interrupt nesting, or production helper headroom.

## Source-backed callback coverage

The emulator is the existing pinned Mesen 2.1.1 runtime, with source revision
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`.

[`SnesCpu::Exec`, lines 29–43](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L29)
calls the instruction observer before `RunOp`, and checks hardware interrupts
after the instruction. The
[`SnesDebugger` instruction callback, lines 145–151](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/Debugger/SnesDebugger.cpp#L145)
obtains the current PC and performs a debugger `Peek` for the opcode.
[`Debugger.cpp`, lines 242–248](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/Debugger.cpp#L242)
delivers that operation to the scripting callback with execution processing
enabled. Therefore the retained opcode is a pre-execution debugger peek,
not an independent opcode bus-fetch observation.

One global exec callback stays installed throughout the replay. It performs
only selection work outside the five intervals; within a selected interval
it records every observed instruction. The code does not add or remove a
callback halfway through a handler or redirect CPU execution to collect a
missing boundary. WAI/STP, software interrupt, emulation-mode changes and
unreviewed execution boundaries refuse. Halted-cycle coverage is not claimed.

[`ScriptManager.h`, lines 43–69](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/ScriptManager.h#L43)
maps ordinary, DMA and dummy read/write operations into the same Lua callback
families. The broad retained stream is accordingly called **bus events**.
Only writes that exactly match the pinned CPU's implicit push semantics are
attributed as CPU stack writes. The callback argument is never returned or
replaced by the observer.

The implementation of the debugger reads is also pinned and archived:
[`MemoryDumper::GetMemoryValue`, lines 362–394](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/MemoryDumper.cpp#L362)
uses `Peek` for the SNES address space and the backing buffer for direct
WRAM reads. These observations do not perform a CPU bus read or mutate the
emulated machine.

## Validation and limits

The host validator recovers all 256 opcode/address-mode entries from the
byte-pinned emulator switch and uses a reviewed mode-to-encoded-length map.
That extraction inventories the source; it does not automatically derive
instruction semantics. Branches use the retained exact pre-status flags;
calls and jumps use the exact canonical operand bytes, and indirect transfers
require the corresponding actual bus-read values. RTS/RTL use their observed
stack reads. Repeated MVN/MVP instruction PCs require the correct counter and
index transition. Incompatible width-dependent or overlapping instruction
decodes refuse.

Every adjacent instruction pair must have the expected next PC, SP, width/I
state, and owned D/DBR change. Push/pull byte widths follow the incoming M/X
flags; PHD/PLD and near/far call frames retain their independent fixed widths.
[`PushByte`/`PopByte`, lines 481–505](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L481)
establish the pointwise SP relation: pushes write at current S before
decrementing, while pulls increment before reading. Every write into the
actually observed frame span must have exact implicit CPU-stack ownership.
All retained stack peeks must agree with the preceding bus-write ledger.
Every captured WRAM read must also agree with that pointwise ledger, and
every captured high-ROM (`$C0-$FF`) read must match the pinned immutable ROM.
This includes indirect control-transfer pointer bytes; trusting recorded
pointer values alone would allow a forged trace to skip part of the handler.
Indirect control pointers outside reconciled WRAM and pinned high ROM refuse.
In particular, this validator does not infer bank-zero ROM mirrors or trust
hardware-register reads as pointer certificates.

Full CPU state is retained for every event. General arithmetic register
results are observations, not an independently re-executed ALU model.
The independent checks concern PC/SP/control and the named register effects,
plus exact restoration of A/X/Y/D/DBR/SP and the native hardware return frame
at the closed endpoints. This distinction prevents a control-flow checker
from being presented as a second complete CPU emulator.

Each interval has a complete 128-KiB WRAM baseline and final snapshot. The
final state must equal the baseline after applying every retained bus write
whose bus address maps directly to WRAM, in order. Unexplained WRAM changes
refuse, including a write through a side-effect port that the direct-address
ledger cannot attribute. This is an observed-state and recorded-write check;
it is not general DMA destination or memory-lifetime proof.

Reads/writes to owner words `$7E5DAC-$7E5DBC`, pointer storage
`$7E5DBD-$7E5DFC`, and controls `$9876-$987B` / `$A0B3-$A0B4` are reported
separately when observed. The selected handlers occur after publication;
their observations cannot establish behavior under partial publication.
The thirteen-owner consumer mapping remains the already accepted
[MAP-005](DATA_MAPPING_CORRECTIONS.md#map-005--active-script-checks-are-not-an-eight-slot-loop).

The predeclared limits are 50,000 exec observations and 250,000 bus events
per interval, 715,000 master clocks and at most two PPU-frame advances per
interval, a 128-MiB trace, and a 900-second emulator timeout. Full clocks,
CPU cycle counters, and both frame counters must be monotonic; raster values
are bounded. Unknown paths, missing/extra intervals, malformed scalar types,
source drift, or any failed ledger/control check refuse acceptance.

## Reproduction and preservation

The launcher creates an isolated private application/profile/save tree. It
pins the clean inputs, accepted context source and reference trace, and eleven
primary emulator files. Current and staged source identities, plus an exact
archive of original observer/test/dependency sources, are checked before
launch and after exit. Launch receipts, unsuccessful runs and host refusals
remain private historical evidence. Accepted sources are never overwritten
to repair a run retroactively.

Commands for new, uniquely named private runs:

```powershell
python -B tools/run_normal_nmi_stack_observation_v1.py --pilot --output-dir private/test_runs/normal_nmi_stack_PILOT_NEW
python -B tools/run_normal_nmi_stack_observation_v1.py --output-dir private/test_runs/normal_nmi_stack_FINAL1_NEW
python -B tools/run_normal_nmi_stack_observation_v1.py --output-dir private/test_runs/normal_nmi_stack_FINAL2_NEW
```

Original host fixtures and adversarial validation tests are separate from the
native evidence. After independent source/test review, a pilot may be run;
only a separately reviewed, source-frozen pair can support a runtime result.

## Pre-execution review correction, 2026-10-03

The interrupted, unpublished launcher (31,579 bytes, SHA-256
`918a9c9eb6635aa58cafde92b965d866e2caf6087b059cc0ee1f701b58780604`)
reconciled WRAM reads but did not reconcile immutable ROM bus reads. An
independent reviewer demonstrated an original synthetic `JMP ($3000,X)`
interval whose actual pointer selected `$D1:9000`; forged pointer reads
selected the required exit `$D1:E898` instead. The old validator accepted
that shortened one-instruction interval. The resumed implementation checks
every captured high-ROM read and refuses the same specimen. A genuine
pointer specimen still passes its two-instruction complete interval.

The old source is preserved unchanged in the private interrupted-source
recovery archive. This was our unfinished validator defect, not a discovered
game behavior or a correction to an upstream ROM map. No native experiment
had been accepted with the defective validator.

## Pilot, failed full run, and collector repair, 2026-10-03

The first pilot at `private/test_runs/normal_nmi_stack_pilot_20261003_1`
completed poll 379 only. Its 7,875,155-byte trace hashes to
`de2350a01e776b797c552c5b4d0b9708e5e9c59ec5757c561c55a339be8697c2`.
Independent revalidation checked 5,507 executed instructions, 13,028 bus
events and full WRAM reconciliation. The observed minimum SP is `$06A8`,
34 bytes below its post-hardware-entry `$06CA`, or 38 including that native
frame. This is one selected interval, not a whole-game stack bound. The
process log contains 28,319 uninitialized-memory-read diagnostics; a
successful trace validator is not a warning-free execution claim.

The first full run at `private/test_runs/normal_nmi_stack_full_20261003_1`
exhausted the declared 900-second emulator timeout. It left an invalid
7,875,154-byte partial JSON file, SHA-256
`f2feb92515158d0230e7cd774438c2f9634238f620114bcf3ca334adda3abfc2`.
The launcher refused process code 4294967295; no second full run began.
Its 42,005 process-log diagnostics are uninitialized-memory reads. Preserve
this failure and its frozen source archive; do not repair its JSON and
promote the repaired file to native evidence.

The old collector definitely swallowed errors raised during finalization:
it set `done=true` before encoding the complete run, then its error handler
called `finish(error)`, which immediately returned without stopping Mesen.
The pinned [Mesen watchdog](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/ScriptingContext.cpp#L116)
checks elapsed callback time; its [configuration default](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/UI/Config/Debugger/ScriptWindowConfig.cs#L34)
is one second. Watchdog expiry during whole-run serialization is a supported
causal inference, not a captured exception from this failed run.

The revised collector encodes each event during its existing callback and
flushes each complete interval. Finalization only closes the JSON object.
Explicit capturing/finalizing/stopped/failed states replace the early done
flag. Any callback or serialization error takes a separate fail-stop path,
preserves a private `.error.txt` when possible and requests exit 93. Partial
traces are not accepted. WRAM snapshot/serialization still has a per-interval
callback cost and must pass the fresh pilot; no watchdog limit is raised.

A second independent adversarial review found that bank-zero `JMP ($8000)`
pointer reads could evade both reconciliation domains. The frozen first-pilot
runner accepted a forged one-instruction shortcut as well as the genuine
two-instruction specimen. The corrected validator refuses both outside-domain
specimens instead of silently inventing a mirror mapping. Eighty host tests
pass after this correction. Both defects concern our unpublished observer;
neither revises an upstream game map or proves a game behavior.

## Repeated full observation, 2026-10-03

The repaired collector's fresh pilot at
`private/test_runs/normal_nmi_stack_pilot_20261003_2` completed successfully.
Its complete decoded JSON equals the preserved first pilot, including every
event and WRAM byte. Serialization order changes the file hash to
`58a8b5d7cade70f43fb5fe4784c3942932b77e7ac00ba70d4938e09ccedf7ef9`;
this is decoded equivalence, not byte equality between the two collector
versions. Their process logs are byte-identical.

The separate full runs at `private/test_runs/normal_nmi_stack_full_20261003_2`
and `normal_nmi_stack_full_20261003_3` then completed. Both 37,645,178-byte
traces are byte-identical, SHA-256
`b1daedf1b9fafebbc148263ef498f46a2af57fa5730aad96d038e0e5b91c552a`.
Both complete manifests hash to
`ca60682b3ef259886b900f1667cca25c8eee1f19960a9c034a4183e454af3854`.
Each run checks 26 guarded source/input/runtime identities, 16 exact source
archives and 10 isolated staged identities. The launcher checks exit 52
before emitting a completed manifest; it does not preserve a separate
process-exit receipt, so the later auditor cannot claim an independent
observation of that exit code.

| Poll | Entry SP | Minimum observed SP | Executed instructions | Bus events | Master clocks |
| ---: | --- | --- | ---: | ---: | ---: |
| 379 | `$06CA` | `$06A8` | 5,507 | 13,028 | 172,136 |
| 500 | `$06D6` | `$06B4` | 5,613 | 11,398 | 167,084 |
| 700 | `$06D1` | `$06AF` | 6,366 | 12,400 | 184,590 |
| 927 | `$06D3` | `$06B1` | 5,553 | 11,291 | 165,324 |
| 928 | `$06D3` | `$06B1` | 5,542 | 11,291 | 165,092 |

All five selected intervals reach 34 bytes below their recorded
post-hardware-entry SP, or 38 including the already-existing hardware frame.
The observed low points follow `PEA` at `$C284EC/$C284F0/$C28547/$C285B0`
and `JSR` at `$C2854F/$C28552`. There is no observed stack rebase. All
347 observed calls per run have matching returns.

Independent pointwise replay rechecks 10,071 direct WRAM writes, 30,353 WRAM
reads and 2,746 high-ROM reads per run. All five final complete WRAM
snapshots reconcile. The declared publication ranges have **zero observed
accesses** in these intervals; these runs therefore do not test reader
behavior during partially published helper state.

The logs are byte-identical at 1,210,608 bytes, SHA-256
`a4267dbe2c5b6c158da82dd767fb6a980b6c6cc5c35e27c8d5393e4026129514`.
Each contains 28,824 uninitialized-memory-read diagnostics. The isolated
checkpoint replay remains useful for its exact observation contract, without
claiming general initialization safety or a warning-free process.

Poll 700 supplies one useful local scene-mapping observation: actual scene
`$8B` reaches `$CD2FB7`, selects `$CD319A -> $CD33CD`, then jumps
`$CEE7CC -> $CEE773` through recorded WRAM pointer reads `$004B=$73` and
`$004C=$E7`. That is a 14-pair copy suffix under this handler's own producer.
It is separate from B5/B6 and from the half-fill continuation. It supplies
neither the legal domain of every scene script nor an intervening-writer
proof for arbitrary inputs.

The source/test-reviewed acceptance auditor is
[`audit_normal_nmi_stack_observation_v1.py`](../tools/audit_normal_nmi_stack_observation_v1.py).
It reopens and checks both complete traces and actual source/staged/archive
files, refuses partial/error/pilot/same-root inputs, and emits only compact
metadata. Raw game traces and snapshots remain private. Reproduction:

```powershell
python -B tools/audit_normal_nmi_stack_observation_v1.py --run-a private/test_runs/normal_nmi_stack_full_20261003_2 --run-b private/test_runs/normal_nmi_stack_full_20261003_3
```

All 80 observer tests and 46 separate acceptance-auditor tests pass. Root
reviewed both complete source/test packets. Two fresh root CLI processes
reproduced the author's exact 148,513-byte
[accepted metadata](../references/normal_nmi_stack_observation_v1.json),
SHA-256 `5431d238814391247771973e7c12e10bb1567da169c76aefd019c2b43b2ce97d`.
The independent ledger review is also preserved as the original private
`private/test_runs/nmi_observer_review_20261003/review_streaming_pair.py`,
SHA-256 `4555376e07e8e918ea0269a8de30a2315d848c32fdf4ad2a623c22e7338f3249`.

This result is an observed bound for the five selected clean-ROM intervals.
It does not prove whole-NMI path closure, global nesting depth, physical game
stack ownership, helper preemption behavior, partial-publication safety,
game integration, or a production allocation. The [next phase-specific
design](schala_package_interrupt_strategy_review_2026_10_03.md) preserves
those separate obligations.
