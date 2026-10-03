# Primary resolver phase observation v2

Status: **accepted repeated native observation, strictly checkpoint-bounded**.
The preparation and rejected-v1 analysis below are preserved; the accepted
October3 result and reproduction details follow at the end.
The v1 collector completed its one authorized pilot with exit 52, but its host
correctly refused a predeclared unsupported sequence. This separate v2 expands
only that scope while preserving the complete original observations.

The shared input, field, callback, type, isolation and evidence contracts remain
those described in [v1](schala_package_resolver_phase_v1.md). V1 runner, collector,
tests and its rejected native pilot remain unchanged. The v2 launcher pins and
archives all three frozen v1 executable/test files because it reuses the unchanged
v1 record and selected-phase validator.

## What the rejected pilot actually showed

The unique `$C1:BBD4` pre-effect entry occurred at poll 374 / master clock
2,153,595,368. The primary resolver remained at poll 378 / clock 2,155,080,050,
with the accepted historical CPU, stack and timing identity. Eight complete
interrupt contexts occurred between those points:

| Context | Kind | Entry poll | Entry clock | Pre-RTI clock |
|---:|---|---:|---:|---:|
| 750 | Battle IRQ | 374 | 2,153,775,470 | 2,153,782,654 |
| 751 | Normal NMI | 375 | 2,153,794,592 | 2,153,944,068 |
| 752 | Battle IRQ | 375 | 2,154,132,844 | 2,154,134,756 |
| 753 | Normal NMI | 376 | 2,154,151,936 | 2,154,297,794 |
| 754 | Battle IRQ | 376 | 2,154,490,228 | 2,154,492,954 |
| 755 | Normal NMI | 377 | 2,154,509,286 | 2,154,657,404 |
| 756 | Battle IRQ | 377 | 2,154,847,582 | 2,154,849,494 |
| 757 | Normal NMI | 378 | 2,154,866,668 | 2,154,999,142 |

The first refusal was original record 4, IRQ context 750. This was not actual
nesting or a serialization failure. V1 explicitly required the resolver/common
loader before any selected interrupt, so the observed early sequence lay outside
its contract. The later first IRQ/NMI pair, contexts 758/759, and both scene-gate
sites were also present.

The retained rejected trace is
`private/test_runs/resolver_phase_v1_pilot_20261003_1/trace.json`, 17,782,665 bytes,
SHA-256 `910481d4d72949dd1a6c1f7b83d76beb1bc16263d0b2460dd590e1656b58fde4`.
It has 2,261 records, `error: null`, and terminal poll 381. Its process receipt
records exit 52; `host_rejection.json` records the scope refusal. Neither those
receipts nor the trace is rewritten or treated as accepted v1/v2 native evidence.

## Small, explicit projection and independent reconciliation

V2 validates every original record with frozen `v1.validate_record`, and checks
monotonic poll/clock/cycle/frame counters and globally increasing interrupt-entry
IDs across the complete original sequence. It selects the historical entry/RTI
records strictly between the current pre-effect clock and resolver clock from the
already accepted, independently pinned context trace. The rejected pilot is not
used as a historical authority.

For each early context, the wrapper requires:

- Non-nested, balanced entry/RTI ownership, with no frame crossing the resolver.
- Exact historical kind, address, full CPU, all twelve stack bytes, trampolines,
  timing, poll, context identity/depth, and every overlapping natural gate byte.
- Complete membership and order: an omitted complete balanced pair is refused.
- CPU A/X/Y/D/DBR/SP/native-mode restoration and an unchanged twelve-byte stack
  window at pre-RTI.
- Exact ownership and normal field validation of every intervening watched bus
  row, including WRAM read-value agreement with its snapshot.

The explicit maximum is eight early contexts / sixteen historical entry/RTI
records. Alternate/nested contexts remain refused. Zero or one pre-effect marker
remains the declared observation contract; when absent, no early projection is
allowed. Current engine values are not compared with invented old values.

Only the fully validated early context spans are removed from an in-memory
validation projection. Main-thread pre-effect records and their bus rows remain.
The unchanged v1 summary validator then checks the primary resolver, common loader,
and following IRQ/NMI pair against its eight historical phase points. V2 also
requires exact historical IDs for that post-resolver pair, preventing identity
reuse or a backward jump across the projection boundary.

The original trace remains complete. Summary indices are translated back to its
original record indices. `record_count`, `event_counts` and `bus_counts` describe
all original rows; `early_interrupt_pairs` and `post_resolver_interrupt_pairs`
are separate. The projection receipt states its removed/retained counts and
`native_interrupt_free_execution: false`.

Read-only reinterpretation of the rejected pilot under this proposed contract
passes: eight early contexts match sixteen accepted historical records; 427 owned
rows are projected out, leaving 1,834 rows for unchanged v1 validation. The retained
resolver interval is still 4,244 master clocks / 548 CPU-counter increments. This
is host revalidation of existing v1 observations, **not a native run of v2**.

## Narrow scene-read witness refinement

V2 additionally requires each gate instruction marker to be immediately followed
in the recorded event stream by its own watched data read:

- `$CD:1609` → `$7E:CCEA`, with callback CPU PC `$160C`.
- `$CD:160E` → `$7E:5D9B`, with callback CPU PC `$1611`.

The pinned clean ROM must contain the exact three-byte absolute LDA preimages at
both sites. The instruction-entry state requires M8/DBR7E. The read snapshot must
match its entire CPU state except PC+3, with identical poll, context, stack and
trampolines, and equal entry/snapshot/read gate bytes. The recorded pilot has these
adjacent pairs at indices 2247/2248 and 2249/2250.

This prevents an unrelated later `$5D9B` callback from substituting for the scene
gate's positive control. It is limited to these two source-owned instruction/data
observations; it does not turn the selected callback stream into complete CPU
instruction-flow or DMA/HDMA bus evidence.

## Launch, receipts, and verification

The v2 Lua is byte-equivalent to v1 after replacing only its protocol name and
environment-variable prefix. A host test enforces that equivalence. Streaming,
direct fail-stop, bounds, input schedule and stop poll remain unchanged.

The new schema is `project-epoch-package-resolver-phase-v2`; environment variables
are `PE_RESOLVER_PHASE_V2_PROTOCOL`, `_STATE`, and `_TRACE`. Staged stems begin
`pe_resolver_phase_v2_` with 24 random hexadecimal characters. The process receipt
retains the same `{schema, returncode, exception}` structure. The source inventory
has 29 entries, including the three frozen v1 dependencies; normal launch totals
are 38 guarded source/input/runtime identities, 28 archived files and ten staged
inputs. Documentation remains outside the executable source-identity guard.

```powershell
python -B -m unittest discover -s tests -p test_package_resolver_phase_v1.py
python -B -m unittest discover -s tests -p test_package_resolver_phase_v2.py
```

The additional original specimens challenge whole-pair omission, extra or
misordered historical pairs, frames crossing resolver, nested/mismatched ownership,
early rows with invalid fields or backward clocks, fresh independent engine
values, global ID reuse across projection, exact original indices, and false
gate-read placements. No specimen includes copyrighted ROM data.

Only after independent frozen-source review and explicit root launch approval:

```powershell
python -B tools/run_package_resolver_phase_v2.py --output-dir private/test_runs/resolver_phase_v2_REVIEWED_UNIQUE_RUN
```

No new helper is executed, and no deadline, interrupt exclusion, complete DMA bus
trace, cancellation adapter, stack ownership or production integration is proved.


## Accepted repeated result — 2026-10-03

The repeated unchanged checkpoint now has accepted resolver-phase observations: two isolated full traces match byte-for-byte, with 2,261 records each and all 161 required serialized fields present. Current source/input/runtime, archive and staged guards cover 38, 28 and ten identities respectively. Ten complete interrupt contexts are retained: eight early contexts individually reconciled to the accepted historical trace, then the selected following IRQ/NMI pair. No helper was injected.

At the exact resolver entry, no sampled IRQ/NMI or DMA/HDMA work is pending. NMI and vertical IRQ are enabled; the vertical timer is 211, horizontal IRQ is disabled, and FastROM is enabled. The three captured PPU overscan/interlace flags are false. HDMA is enabled for all eight channels and every channel remains unfinished. The enabled/unfinished state is separate from the false pending flags:

| Channel | Transfer mode | Direction | BBAD destination | doTransfer | HDMA finished |
|---:|---:|---|---|---|---|
| 0 | 4 | A to B | $07 | false | false |
| 1 | 3 | A to B | $0D | true | false |
| 2 | 3 | A to B | $0F | true | false |
| 3 | 3 | A to B | $11 | true | false |
| 4 | 4 | A to B | $2C | false | false |
| 5 | 4 | A to B | $30 | false | false |
| 6 | 1 | A to B | $05 | false | false |
| 7 | 4 | A to B | $26 | true | false |

For indirect HDMA, the serialized `transferSize` field is an indirect pointer, not the remaining manual-DMA transfer length. Channel-counter/pointer changes across the short resolver interval are consistent with continued HDMA progress, so false pending flags must not be described as a transfer-free window.

The old resolver interval repeats at 4,244 master clocks / 548 CPU-counter increments. The natural `$CCEA` and `$5D9B` scene-gate reads both return zero, each 26 master clocks after its exact instruction marker. The next observed IRQ and NMI handler entries lie +124,904 and +143,988 master clocks after resolver entry in this vanilla replay. Those are observed separations, not deadlines or a replacement-helper timing allowance.

Each retained process log contains 28,319 uninitialized-read diagnostics and no other line category. The result remains limited to this checkpoint, source and controller schedule. The next timing obligation includes the still-uncaptured serialized `internalRegisters.hCounter/vCounter`, upcoming HDMA work and exact interrupt-sampling semantics. PPU line 119 and timer 211 alone do not establish an exclusion deadline. No production helper, hook, stack ownership, publication isolation, action-completion or cancellation policy is approved.

## Correction receipt — static envelope versus measured calibration

The earlier private “next timing candidate” item 3 incorrectly calls 67,112 clocks an “isolated helper measurement.” That wording is withdrawn. The earlier text is retained above as the exact draft history; it must not be copied into the shared report.

**67,112 clocks is the separately reviewed static conditional upper envelope** for the fixed small original-cartridge fixture, including the source-model DRAM-refresh allowance. `docs/schala_package_interrupt_strategy_review_2026_10_03.md:217–221` gives the base 65,046-clock model and `ceil((65046 + 80) * 1352 / 1312) = 67112`. The separate immutable-ROM timing calibration's **observed sampled maximum is 54,108 clocks**, as stated in `docs/schala_package_helper_v4_timing_calibration.md:108–114`. These are different evidence categories and scopes. Neither establishes a game admission deadline; the envelope's DMA/HDMA/interrupt/integration exclusions remain explicit.

Corrected item 3 wording: “Bind any next timing candidate to the exact resolver CPU, code placement/access speeds, actual internal timer phase, DMA/HDMA state and interrupt-sampling semantics. The 67,112-clock static conditional fixture envelope excludes DMA/HDMA, interrupts and added integration instructions; it is separate from the calibration's 54,108-clock sampled maximum. Neither the static envelope nor the measured maximum, combined with a vanilla IRQ-entry gap, is an admission certificate.”

Correction provenance: root identified the categorization error; this reviewer independently read both cited source reports and checked their corresponding reference files. The compact suggested shared-report extract does not contain the mistaken measurement wording and needs no correction.

Pre-correction draft SHA-256: `56d0bb86ccaa9c474236e8d404931bd904a7c45dfb17099c930ffaad809c702e`.
Static-envelope reference SHA-256: `058d9f1ac1a2bb1c9a2f7ea375e9f507d3e1536e475eaf1316f1afd5dad0d8db`.
Calibration reference SHA-256: `8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb`.

The full traces are each 17,782,665 bytes, SHA-256
`7e2d2925f8523a134721427c1001128a073b6b64518abe3810ee637cb5e71bb0`.
Their exact private roots are
`private/test_runs/resolver_phase_v2_full_20261003_1` and
`private/test_runs/resolver_phase_v2_full_20261003_2`.
A prior fresh v2 pilot has the same trace bytes; its decoded observation also
matches the rejected v1 pilot except for the schema. V1 remains rejected under
its preserved protocol, and none of its files was rewritten.

The [acceptance auditor](../tools/audit_package_resolver_phase_v2.py) reconstructs
both complete manifests from actual source/staged/archive identities and full
trace revalidation. It checks the separate native process52 receipts and rejects
error markers, missing files, altered source, aliased paired files and manifest
claims unsupported by the reconstructed result. The compact output includes
selected emulator hardware metadata, without raw game CPU/stack/gate arrays.

All 43 preserved v1, 34 v2 and 39 acceptance tests pass. Root read the complete
new source/test/report packets and ran two fresh acceptance CLI processes.
Their outputs equal the independent peer's output: 53,831 bytes, SHA-256
`8e3898c7886a88e166bf5fd13f69ac37b44b59bd202d5780c0a8ae98ae30c120`.
The accepted [reference](../references/schala_package_resolver_phase_v2.json)
contains exact identities, compact observations, scope flags and reproduction.

```powershell
python -B -m unittest discover -s tests -p test_package_resolver_phase_v*.py
python -B -m unittest discover -s tests -p test_audit_package_resolver_phase_v2.py
python -B tools/audit_package_resolver_phase_v2.py --run-a private/test_runs/resolver_phase_v2_full_20261003_1 --run-b private/test_runs/resolver_phase_v2_full_20261003_2
```

Additional independent source review exercised 24 temporal/context mutations;
acceptance review exercised eighteen original filesystem/receipt mutations.
The preserved private review receipts are:

- `private/test_runs/resolver_phase_v2_peer_review_20261003/review_receipt.json`,
  SHA-256 `f5186fb2ff7bcbc8dceee95b3ee2501697ec12302523f3e356e66551854ad9d8`.
- `private/test_runs/resolver_phase_v2_acceptance_peer_review_20261003/review_receipt.json`,
  SHA-256 `5e9debc4c2e4850ad055dc39453a54b53f9b646111fd9b100bc3cf1cd5180e5f`.
- `private/test_runs/resolver_phase_v2_full_review_20261003.json`,
  SHA-256 `80c16fa3e78c3d37938775d5bfeb4a388dbe1319c466f417976ef7034b103e53`.

Relevant overclock settings are also outside the captured field contract.
Unknown HDMA payload can write PPU registers, including channel5's SETINI
`$2133` destination; initial PPU mode flags must not be assumed constant
through a hypothetical helper. Timing cost, source-read aliases, render effects
and production ownership are separate obligations.
