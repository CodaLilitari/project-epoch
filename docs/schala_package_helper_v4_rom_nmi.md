# Original cartridge ROM helper with a real emulated NMI

Date: 2026-09-08. Evidence level: **verified-runtime**, within the original
diagnostic cartridge and 152 named cases in Mesen 2.1.1. Two fresh runs under
the independently reviewed corrected source passed every native and host
gate and produced byte-identical traces. The earlier rejected source revision
remains preserved as rejected evidence.

This experiment combines the immutable ROM execution and registry proof in
[normal v3](schala_package_helper_v3_rom.md) with the actual native interrupt
observations developed in the separately preserved
[WRAM v2 NMI experiment](schala_package_helper_v2_original_nmi.md). Its source,
addresses, case contract and native observations are separately versioned.
It does not install a Chrono Trigger hook, claim ownership of a game stack or
run the game's NMI handler. Logical playable PC `$07` remains unimplemented.

## Matched native result

The accepted runs are
`package_helper_v4_rom_nmi_20260908_sampledwitness1` and
`package_helper_v4_rom_nmi_20260908_sampledwitness2`, under ignored
`private/test_runs/`. Each has 152 passing cases and a 217,544,660-byte trace
with SHA-256
`9752443839e73d8cdb29e6096f41838ffb4091372b5fd910209cb0a74ab19c6e`.
Their manifest hashes are respectively
`8ad37dba7d14e42c14756321796d97928fce8b1541df29a8a480422e7c988475`
and `b39fa24f8a10d1fd595465efe81c2e877f3810f6618fc5e7e08d963aeba6fd6d`.
The [acceptance reference](../references/schala_package_helper_v4_rom_nmi.json)
contains exact current, prepared, staged, archived and per-case identities.

Each run retained 218,732 events: 119,960 helper/terminal execution
observations, 1,368 handler execution observations, 608 native hardware
stack writes, 304 vector-byte reads, and 36 separately owned conditional
TCS idle reads. All 152 counter increments and full WRAM reconciliations
passed before the unchanged normal-v3 validator accepted each derived
helper projection. All 52 guarded current/prepared identities and all 45
archived source/reference files stayed unchanged through each run.

The greatest observed combined live depth was 59 bytes, with minimum SP
`$1FB4` from entry `$1FEF` and `$069D` from entry `$06D8`. The longest complete
active fixture was 54,504 master clocks; the longest post-RTI continuation
was 53,544. Eleven cases sampled zero-channel HDMA initialization, with 25
pending observations in total. Four cases used the exact source-owned
38-clock sparse-observation witness described below; every other such
clear interval stayed within the generic 32-clock gate.

The corrected pair's raw native observations match the rejected `final1`
trace byte for byte after one explicit substitution of its initial protocol
header from `calibrated-v2` to `calibrated-v3`. The evidence collector checks
the original input hash, exact initial header and resulting whole-file hash.
This is evidence that the validator correction did not change the observed
native execution; it does not convert the historical rejected run into an
accepted run. Its old collector, launcher, tests and rejection remain intact.

## Immutable cartridge and selected boundaries

The original diagnostic cartridge is SHA-256
`1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b`.
Its 577-byte helper at `$41:0000` is SHA-256
`7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b`.
The original package is in bank `$42`, the immutable registry in bank `$43`,
and the setup bridge is the original `$00:8060` JML to `$41:0000`.
The normal v3 cartridge certificate, allocation audit and exact source
identities must still validate before and after each launch. This harness
does not emit an image or write to cartridge memory.
The [original cartridge build report](original_snes_package_cartridge_v1.md)
describes the separate guarded, source-reproducible image and its receipts;
the image has no source-game-ROM or extracted-game input.

The actual native vector reads are `$00:FFEA/$00:FFEB`, whose bytes select
the original handler at `$00:8080`. The handler preserves status and A,
increments the synthetic word at `$7E:5EF0`, and executes RTI at `$00:808F`.
Its 16 bytes have SHA-256
`7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448`.
No `$00:8020` handler address from the older carrier is reused implicitly.

The 152 named cases use synthetic entry SP `$1FEF` and `$06D8` only:

- 80 successful cases: four immutable selector bindings `$80-$83`, both
  `$A0B3` branches, both stacks, and five boundaries at incoming status `$00`.
- 48 further successes: those same sixteen binding/branch/stack groups at
  incoming statuses `$C3`, `$4C` and `$8F`, at the first CountBits JSR.
- 24 canonical/refusal cases: selector `$7F`, unsupported `$90` and
  immutable-unbound `$84`, both stacks, statuses `$00/$8F`, and two route
  appropriate return or frame-release boundaries.

The success boundaries are allocation TCS `$41:0043`, first CountBits JSR
`$41:00EE`, release TCS `$41:0215`, PLP `$41:021A` and final JML `$41:021B`.
Their independently decoded continuations are respectively `$41:0044`,
`$41:0232`, `$41:0216`, `$41:021B` and `$00:8110`. Canonical and refusal
cases retain their own decoded instruction sites and tails. Empty selected
descriptor branches remain part of the immutable fixture matrix.

The 42 bytes of stack-relative local storage, eight caller-save bytes and two-byte CountBits
return word give a helper maximum of 52 bytes. Native NMI adds four hardware
bytes; this particular handler adds three more. A 59-byte combined maximum
is therefore the declared synthetic bound at the deepest JSR. The small-SP
normal-conformance cases are excluded because they have no interrupt reserve.
This is neither an all-instruction preemption proof nor a game stack bound.

The source case contract distinguishes the live depth when the interrupt
arrives from the maximum reached anywhere in the fixture. Depths below are
bytes beneath the case's original entry SP. Hardware entry adds four bytes
to the post-instruction depth; this handler's maximum adds another three.
The full-run validator must reconcile those actual writes and observed SPs,
then require the maximum over the entire case to match its declared value.
The actual pre-instruction, post-instruction, hardware-entry and handler-peak
depths in both accepted runs agree with every row of this contract.

| Route and selected boundary | Cases | Helper depth before → after instruction | Peak during this NMI | Whole-fixture maximum |
| --- | ---: | ---: | ---: | ---: |
| Success, allocation TCS | 16 | 8 → 50 | 57 | 57 |
| Success, first CountBits JSR | 64 | 50 → 52 | 59 | 59 |
| Success, release TCS | 16 | 50 → 8 | 15 | 52 |
| Success, PLP | 16 | 1 → 0 | 7 | 52 |
| Success, JML | 16 | 0 → 0 | 7 | 52 |
| Canonical `$7F`, PLP / JML | 8 | 1 → 0 / 0 → 0 | 7 | 8 |
| Early refusal `$90`, PLP / JML | 8 | 1 → 0 / 0 → 0 | 7 | 8 |
| Framed refusal `$84`, release TCS | 4 | 50 → 8 | 15 | 50 |
| Framed refusal `$84`, JML | 4 | 0 → 0 | 7 | 50 |

The JSR's own two-byte near return word is written before the four hardware
NMI bytes; its required value is `$00F0`, independently derived from the
original `$4100EE` instruction. TCS is checked on both sides of its SP
change, including its distinct conditional idle read. At PLP, the hardware
frame contains the restored caller status. At JML, it contains the bank and
PC of the destination tail after the branch has completed. The final tail
execution callback is an observation before its loop opcode executes.

These cases request one NMI before the selected instruction and require
hardware entry after that instruction completes. They do not inject an
interrupt halfway through an instruction. They do not individually preempt
the other register pulls, the second CountBits JSR, every publication write
or every loop iteration. Only the stated incoming statuses, branches,
bindings, stacks and original minimal handler are covered; IRQ, nested NMI,
the real game handler, other caller contexts and ownership of physical game
stack bytes remain separate obligations.

## Natural timing and the preserved failed pilot

The first original-ROM pilot completed its two native records, but its host
validator rejected the inherited requirement that the entire helper fixture
remain in VBlank. Both NMIs entered on scanline 227 and resumed on 228. The
longer selector-$80 continuation reached its tail on scanline 3 after raster
wrap. The exact 7,146,622-byte trace is SHA-256
`5344fbd723568a078b8e2233f77bfb11a31930fd2079a17a071cb455fe5b5a2a`.
The failed run, its thirty archived source files and its explicit rejection
receipt remain under the ignored private test-run directory. This was a
phase-contract failure, not a demonstrated helper or interrupt defect. It
was not relabeled as accepted evidence after the validator changed.

The calibrated two-case pilot subsequently passed with source-matched trace
SHA-256 `f61cad80bb75e209568415828df683e5cff2e97c2f373390aeac6ce4b853ffa9`.
The first full matrix then completed all 152 native records, but four failed
the proposed 32-clock observed-clear limit for zero-channel initialization.
Its 217,544,660-byte trace, SHA-256
`69f2173421da9d5d0dada58e096b8937fbb6819f3ac6b95f656997f10895b061`,
remains rejected with its exact 41-file source archive. The four affected
cases share the original publication-word store followed by a stack-relative
load; the next retained callback samples clear after 38 clocks. The other
148 records passed the earlier contract unchanged. This failure produced the
separately numbered calibrated-v3 sampled-clear witness described below.

The reviewed [phase extension](schala_package_helper_v4_rom_nmi_phase_extension.md)
requires a separate [timing calibration](schala_package_helper_v4_timing_calibration.md).
Two frozen calibration runs each validate 22 status-zero fixture groups and
15,090 instruction observations through the unchanged normal-v3 proof.
Their exact traces match, SHA-256
`7b21a5bb512514923eb39e5bbed22f4f34d121b7f26ca73c8a16ce63aaf6d6af`.
Their 92 schedule rows match, SHA-256
`961021271ea9e8f508e418cc758f2f9c5b97aaadc60380a623ae797d106a0baf`.
The accepted calibration reference is pinned as SHA-256
`8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb`.

Schedule elapsed clocks start at the fixture baseline before the original
entry JML. Per-instruction reproducibility projections use a separately
named first-helper-instruction clock origin. The inferred start scanline is
`(observed_latch_rise + 3 - ceil(elapsed_clocks / 1364)) mod 262`. The resulting
eight start lines are 188, 212, 213, 214, 217, 218, 226 and 227, against an
observed rise on 225. The formula selects a proposed start phase; it does not
establish constant scanline duration or incoming-status timing equivalence.

The CPU waits in the original `$00:8040` idle loop for the fixed natural
start. The preceding false-to-true latch bracket, baseline, scanline,
horizontal clock, full master clock and frame counters remain recorded.
After setup the helper executes continuously. At the selected pre-instruction
callback the debugger writes the real `$4200` register with its NMI-enable
bit while the actual latch is set. Mesen completes that selected instruction
and services the native NMI. The harness neither edits an internal pending
flag nor manufactures or restores an interrupt frame.

Every request through the actual post-RTI continuation must remain inside
one observed natural VBlank interval. The complete fixture is bounded to
120,000 full master clocks and its disabled post-RTI continuation to 80,000.
That continuation may cross raster wrap. Raster progression is checked
against 1360-to-1364 clocks per crossed line, using the observed VBlank rise
as the frame-counter phase origin. The source-backed short-line and frame
rules are cited and byte-pinned in the phase extension and reference.

A narrow line-zero exception permits observed HDMA initialization bookkeeping
with zero enabled channels, zero transfer-pending flags and no IRQ lock.
Its pending-state OR must be exact; it must occur outside request-through-RTI,
at line zero/horizontal clocks 12 through 64. The generic observed-clear
limit is 32 full clocks.
At most one observed episode is allowed; a cleared delay flag cannot restart.
This follows pinned Mesen source and makes no exception to the memory ledger.
It does not permit an actual DMA transfer.

One precisely owned sparse-observation interval may sample clear after
exactly 38 clocks. Original `$41:01DF` executes `STA $7E5DBD,X`; its low-byte
write samples initialization and delay true, its high-byte write eight clocks
later samples delay false, and the next `LDA $05,S` pre-execution callback
at `$41:01E3` shares that clock. Initialization is serviced before the next
opcode fetch. The next retained general-data callback follows opcode/operand
fetches and an idle cycle, 30 clocks after that execution callback. The
validator requires the complete consecutive sequence, original PCs/opcodes,
exact CPU states, physical addresses, accumulator byte values, execution
ordinals and exact master-clock and CPU-cycle differences. The source and
failed observation are cited in the phase extension. This is neither a
general timeout increase nor 38 clocks of actual pending DMA.

The [corrected v2 phase contract](mesen_nmi_phase_contract_v2.md) is a mandatory
prerequisite. In particular, the previously published claim that Lua exposes
`ppu.nmiScanline` was our own observability error, documented as MAP010 in
[the correction register](DATA_MAPPING_CORRECTIONS.md). The current experiment
uses only the natural latch and serialized public scanline fields.

## Actual event evidence before the helper projection

Every retained event has an exact CPU, timing, interrupt/DMA-state and
stack/counter schema. The first helper state must equal the fixture baseline
with only the program bank and PC changed by the original JML. Full 64-bit
`memoryManager.masterClock` is authoritative; generic Lua `masterClock` must
equal its low 32 bits. CPU cycles are a separate monotonic quantity.

The selected instruction must have completed before hardware entry. The
native four-byte stack writes are checked in order with exact physical
addresses, live SP and interrupted status/PC/PBR values. The actual vector
reads, handler entry bank `$00`, status transform, exact nine handler
instruction observations, fourteen handler memory operations, counter
increment, pre-RTI frame and complete post-RTI CPU restoration are required.
The original ROM contains the vector and handler throughout.

TCS requires two distinct code reads when preempted: the conditional implied
addressing idle read happens before TCS changes SP, with `needNmi` still set;
the hardware-entry dummy read happens after SP changes, with that flag
acknowledged. They can share a ROM address while having different ownership
and CPU states. Both reads must have the exact original ROM byte. Their
source spans are retained independently; collapsing them rejects the case.

The host independently enforces the collector's data-read policy. General
reads may use only declared package/registry spans, selector/branch inputs
and the pointwise live stack. Exact hardware and handler operations have
separate owners. Retired `$7E:4000` scratch reads reject. ROM writes reject.
All execution callback PCs and opcode values must agree with the immutable
helper, handler or exact terminal tail. Callback values are pre-execution
debugger peeks, not independently observed opcode bus fetches.

The complete final 128-KiB WRAM diff must equal the last observed CPU write
to every address against the declared A5/setup-patch baseline, including
stack bytes and the counter. Every address/value must be an exact bounded
integer, in strict order. No unexplained stack change or omitted final
change is accepted.

Only after that actual evidence passes does the validator construct a
declared helper-only projection for the unchanged normal-v3 validator. It
removes the four hardware pushes, vector/dummy reads, original handler epochs
and separately owned conditional TCS idle read. Its final diff is derived
from helper writes. It is not substituted for the actual native diff, which
may retain interrupt writes in released stack bytes. Normal v3 then checks
exact ROM data reads, stack-relative accesses, execution/opcode observations,
final CPU/publications and unchanged ROM fixture snapshots.

## Reproduction and handoff

Native source: `tools/run_schala_package_helper_v4_rom_nmi.py` and
`tools/mesen_schala_package_helper_v4_rom_nmi.lua`. Host tests:
`tests/test_schala_package_helper_v4_rom_nmi.py`. The source-only tests use
original abbreviated envelope specimens and mock the v3 projection only
where that boundary is stated explicitly; native acceptance always invokes
the real frozen v3 validator.

Before launch, the harness reconstructs the accepted calibration reference,
checks the corrected phase contract and all frozen v3 sources, then copies
45 exact named source/reference files into a new private archive. Runtime,
original cartridge, staged Lua/input, isolated zero SRAM and source identities
are recorded and rechecked after execution. The public evidence collector
rechecks the exact archive inventory and all current, prepared, staged and
final hashes; it launches no emulator and writes no cartridge.

Run the host checks with:

```powershell
python -m unittest discover -s tests -p test_schala_package_helper_v4_rom_nmi.py
```

All 81 native-envelope/source tests and 18 separate metadata tests pass.
The metadata tests cover missing/extra historical archives, pinned prepared
and rejection receipts, exact initial-header projection and bounded reads;
they use original host specimens without private trace dependencies.
The read-only accepted-evidence reproduction command is:

```powershell
python -B tools/collect_schala_package_helper_v4_rom_nmi_evidence.py
```

A fresh native reproduction uses the pinned local Mesen runtime, audited
original cartridge/receipts and preserved prerequisite evidence. Choose new
private output directories; the launcher refuses existing output instead of
overwriting history. With those dependencies present, the two bounded runs
use the same source and declared matrix:

```powershell
python -B tools/run_schala_package_helper_v4_rom_nmi.py --output-dir private/test_runs/package_helper_v4_NEW1 --scope matrix --repetition 1
python -B tools/run_schala_package_helper_v4_rom_nmi.py --output-dir private/test_runs/package_helper_v4_NEW2 --scope matrix --repetition 2
```

The second run follows only after the first passes. Metadata-only replay
requires the preserved private native traces; those are not bundled in Git.
The public sources describe how to generate new evidence and identify every
private prerequisite by path and digest.

The final acceptance pins identify the fresh corrected pair above. The
metadata collector also pins the earlier paused handoff unchanged in private
history; its public continuation note identifies the later completion.
Raw traces, cartridge copies, SRAM and executable staging remain ignored and
private. This experiment establishes bounded preemption in an original
synthetic ROM fixture; it cannot establish real-game interrupt closure, physical stack
ownership, production placement, action-package execution, game hook safety,
save safety or an eighth playable character.
