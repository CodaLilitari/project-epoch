# Original NMI preemption of the stack-local package helper

Two independently staged Mesen runs passed all 224 cases each and produced
byte-identical 420,429,445-byte traces, SHA-256
`3a84fca5e618a9aaaeac9c3056b7a15858f396b5cbfe5e2ae4fd2ae4fe147d50`.
The evidence level is **verified-runtime**, limited to the original minimal
NMI handler and the named synthetic fixture matrix. The helper, carrier,
original/staged inputs and exact source archives remained unchanged.

This experiment keeps the original 8 MiB SHA diagnostic carrier and the
577-byte v2 package helper unchanged. It requests an NMI through Mesen's
emulated `$004200` register path after observing a natural VBlank latch
transition. The CPU executes the selected helper instruction, constructs its
native hardware interrupt frame, reads the original vector, executes the
original minimal NMI handler, and returns with `RTI`. No interrupt frame or
internal NMI/PPU state is assigned by the collector.

The current prerequisite is the corrected
[Mesen phase/key contract v2](mesen_nmi_phase_contract_v2.md). Our earlier v1
note incorrectly exposed the hidden `ppu.nmiScanline` field. That published
source error and its first failed pilot are retained under MAP010. This
harness observes the last false and first true `internalRegisters.nmiFlag`
samples, their `$4210` debugger peeks, full clocks, and the next actual
scanline. It never substitutes an invented field or phase for an absent key.

## What is fixed and what is diagnostic

The carrier SHA-256 is
`e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd`.
Its existing native NMI vector is `$00:FFEA → $00:8020`; its existing handler
occupies `$00:8020-$00:802F`, 16 bytes with SHA-256
`7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448`.
The handler saves P and the 16-bit accumulator, increments the original word
counter at `$7E5EF0`, restores A/P, and returns with `RTI`. It leaves X, Y,
D and DBR untouched. This is an original diagnostic handler, not Chrono
Trigger's normal NMI routine.

The assembled v2 helper remains 577 bytes with SHA-256
`77dc3224baaa93077218d43d64cbef10bb55494a37057c1a5bfcf0d8fd6758f8`.
It executes from synthetic WRAM `$7F8000`, reads the original descriptor-shaped
ROM fixtures in banks `$41/$42`, and uses the same synthetic WRAM registry,
inputs and fixed tails as the completed
[normal v2 proof](schala_package_helper_v2_stack.md). These locations are
diagnostic identities. This experiment grants them no game allocation or
ownership.

Setup is explicit. The collector disables NMI, IRQ, auto-joypad and DMA/HDMA
through their emulated registers, executes an original idle fixture, waits
for the observed natural latch edge, writes declared original WRAM fixtures,
and installs the declared starting CPU registers outside the observation.
The original four-byte JML bridge at `$7FF100` executes after the debugger
redirect; every helper opcode from its initial PHP onward is then observed.
The bridge is setup provenance, not a claimed observed helper instruction.

At a selected pre-instruction callback, a debugger write sets `$4200=$80`.
The before/after records must show unchanged CPU registers, clocks, stack,
counter and latch, together with NMI enable becoming true and countdown
becoming 2. This is a register write through Mesen's actual device handler;
it is not an executed CPU `STA`. At the original NMI entry, a second recorded
debugger register event sets `$4200=0` to make the request single-shot.

## Declared boundary matrix

The full fixed matrix contains 224 cases at two synthetic entry SPs,
`$1FEF/$06D8`. It includes both ROM fixture banks, primary and alternate
branch flags `$00/$40`, and four initial P values `$00/$C3/$4C/$8F`.
M and X are initially clear; decimal, interrupt-disable, carry, overflow and
sign conditions vary. Success returns through its normal 8-bit accumulator
status, which is also interrupted at the PLP and JML boundaries.

At initial status `$00`, all four bank/branch combinations at both SPs use
every success boundary below. The remaining three initial statuses use the
first JSR, final PLP and final JML. Canonical, early-refusal and framed-refusal
exits add their declared sites at all four statuses and both SPs. This is a
named boundary matrix, not every instruction or every possible interrupt
arrival time.

| Boundary | Selected instruction | Continuation | Helper bytes after instruction |
| --- | --- | --- | ---: |
| First save | `$7F8000 PHP` | `$7F8001` | 1 |
| Allocate locals | `$7F8043 TCS` | `$7F8044` | 50 |
| First local call | `$7F80EE JSR` | `$7F8232` | 52 |
| Second local call | `$7F80F5 JSR` | `$7F8232` | 52 |
| Root publication | `$7F8182 STA long` | `$7F8186` | 50 |
| Staging width change | `$7F81F6 SEP` | `$7F81F8` | 50 |
| Release locals | `$7F8215 TCS` | `$7F8216` | 8 |
| Pull DBR | `$7F8216 PLB` | `$7F8217` | 7 |
| Pull Y | `$7F8217 PLY` | `$7F8218` | 5 |
| Pull X | `$7F8218 PLX` | `$7F8219` | 3 |
| Pull A | `$7F8219 PLA` | `$7F821A` | 1 |
| Pull P | `$7F821A PLP` | `$7F821B` | 0 |
| Success tail jump | `$7F821B JML` | `$7FF010` | 0 |
| Canonical pull P | `$7F8019 PLP` | `$7F801A` | 0 |
| Canonical tail jump | `$7F801E JML` | `$7FF000` | 0 |
| Refusal release | `$7F8226 TCS` | `$7F8227` | 8 |
| Refusal pull P | `$7F822D PLP` | `$7F822E` | 0 |
| Refusal tail jump | `$7F822E JML` | `$7FF020` | 0 |

The deepest preemption adds four hardware bytes and three handler save bytes
to the helper's 52-byte call depth: 59 bytes in all. The expected minima are
`$1FB4` and `$069D`. A late preemption has a smaller live depth; its overall
case minimum can still be the helper's earlier 52-byte peak. Each case checks
that distinction. The low-SP normal fixtures `$0034/$0033/$0008` have no
interrupt reserve and are excluded.

## Two distinct reads at TCS

The first expanded exploratory run completed all 19 native cases, but its host
validator rejected the three TCS sites because it expected one code read at
the resume address. Two reads are correct for this pinned emulator.

The opcode dispatch calls `AddrMode_Imp()` before `TCS()`. The implied
addressing handler calls `IdleOrRead()`, which turns the idle cycle into a
code read when an NMI is pending. This first read retains the old SP and
`cpu.needNmi=true`. TCS then sets SP from A. `CheckForInterrupts()` clears the
pending flag and calls `ProcessInterrupt()`, whose own code read is the
second read at the same PC. It carries the new SP and `cpu.needNmi=false`.
The validator requires both exact witnesses and their separate meanings.
[TCS dispatch](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L68),
[implied addressing](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1331),
[conditional idle read](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L386),
[TCS effect](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1073),
[NMI acknowledgement](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L46),
[hardware entry](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L505).

The final metadata pins each exact source span and whole-file identity. This
finding extends the boundary model; the original first-JSR prediction did not
claim TCS semantics. The rejected exploratory trace and its exact sources
remain preserved.

## Evidence checks and interpretation

Every retained execution callback records its CPU, live SP, stack bytes,
timing, interrupt/DMA fields, and original counter. Its opcode value is a
pre-execution debugger peek, not an independent opcode bus-fetch observation.
It must equal the exact mapped helper or original handler byte. Each data
access carries its execution ordinal and physical/bus address. The complete
sequence is restricted to the helper, the nine exact original handler
instruction starts, and the selected fixed tail. Tail STP instructions are
observed and stopped before execution.

The hardware witness is explicit: the selected instruction's completed CPU
state, any separate near-call frame, the hardware dummy read, four distinct
ordered hardware pushes with live SP, actual `$00FFEA/$00FFEB` vector reads,
and entry at `$008020`. Hardware P must set I and clear D while preserving
the other saved bits. Every original handler instruction has an exact
expected CPU state. Its complete ordered stack/counter memory sequence,
pre-RTI frame, and actual post-RTI CPU must match. The counter must increment
once, with actual byte stores and subsequent readback.

All stack snapshots and WRAM data reads are reconciled to the declared setup
baseline plus all earlier CPU writes. The current write callback precedes
that store in the pinned emulator; pull callbacks see the incremented SP.
The full final 128 KiB WRAM diff must equal the last observed CPU write at
every changed address, including interrupt and helper stack bytes. No final
stack changes are filtered away. IRQ, DMA/HDMA and auto-joypad remain absent,
and the active fixture stays inside its recorded VBlank phase.

Only after validating that actual complete evidence does the host construct
an explicitly derived interrupt-free helper projection. It removes hardware
entry accesses, all original handler epochs, and the separately identified
conditional TCS idle read. Its projected final diff is computed from the
helper's own CPU writes. It is not the actual native final WRAM diff. This
projection must pass the unchanged v2 validator's register, ordered
publication, source read, immutable input/scratch, instruction ownership and
stack-access checks. Interrupt writes can remain in stack bytes that the
helper has legitimately released, which is why these two diffs must remain
distinct.

The 55 host tests use original constructed metadata, not private traces or a
native emulator. Their abbreviated NMI-envelope specimens mock only the
already separate helper projection; they are not full helper proofs. Other
tests cover the deterministic matrix and refusal of missing or altered vector
reads, hidden-field substitutions, detached snapshots, counter/stack ledger
drift, unexplained final changes, phase violations, pending IRQ/DMA state,
wrong handler widths/registers, missing TCS reads and failed helper validation.
The native runs apply the real unchanged v2 validator to every full case.

Independent review of the first frozen 19-case version found two host
acceptance gaps: an equal-valued floating-point final-diff byte passed Python
numeric equality, and an inserted retired-scratch read could pass despite
the Lua collector already forbidding that access. The final host validator
requires an exact bounded list of strictly increasing integer address/byte
pairs and independently applies the native read scope. It also bounds the
horizontal raster clock and NMI countdown, and checks the exact source archive
against the prelaunch source set before and after execution. The pre-delta
sources and exploratory run remain preserved. These were validator gaps;
they were not observed helper or native interrupt defects.

## Reproduction and limits

Each complete run records the following evidence:

| Observed result | Count per run |
| --- | ---: |
| Successful extended fixture cases | 176 |
| Canonical fixture cases | 16 |
| Refusal fixture cases | 32 |
| Total retained events | 422,544 |
| Helper instructions plus terminal observations | 240,264 |
| Original handler instructions | 2,016 |
| Native hardware stack-byte writes | 896 |
| Actual native vector-byte reads | 448 |
| Separate conditional TCS idle reads | 24 |
| Counter increments and full-WRAM reconciliations | 224 each |

The minimum observed SPs are `$1FB4/$069D`, the predicted 59-byte deepest
preemption. Allocation, publication and byte-width staging preemptions peak
at 57 bytes. Later success exits retain their earlier 52-byte helper peak;
canonical/early-refusal exits peak at eight, and framed-refusal exits at 50.
All events remain at or below observed scanline 259, inside the declared
phase. Every fixture starts its counter at `$A5A5` and observes exactly one
increment to `$A5A6`; setup resets it between cases.

The read-only collector rederived all per-case observations from both full
traces and checked current, staged and archived source identities. The exact
metadata and complete preserved attempt history are in
[`references/schala_package_helper_v2_original_nmi.json`](../references/schala_package_helper_v2_original_nmi.json).
The final directories are `private/test_runs/package_helper_v2_nmi_20260908_final1`
and `private/test_runs/package_helper_v2_nmi_20260908_final2`. Their manifest
hashes are respectively
`544de092e18ec9c77f284c1582a0961222fef4c2c91ff9f76898a886782710af`
and `9fc6c9372f0858188a790f424fec9441a8bac2beb6f7efaead57127864e25593`.
Their identical case contract has SHA-256
`1fb5d10663dc81698d2df432cbb01393dd5e862bfefff11f2c2e28bdeb8d19e3`.

Reproduce the host checks and metadata without launching an emulator:

```powershell
python -m unittest discover -s tests -p test_schala_package_helper_v2_nmi.py
python -B tools/collect_schala_package_helper_v2_nmi_evidence.py
```

Fresh execution requires the pinned private original carrier, Mesen runtime
and assembler. A new, empty output directory is mandatory:

```powershell
python tools/run_schala_package_helper_v2_nmi.py --scope matrix --repetition 1 --output-dir private/test_runs/package_helper_v2_nmi_new1
python tools/run_schala_package_helper_v2_nmi.py --scope matrix --repetition 2 --output-dir private/test_runs/package_helper_v2_nmi_new2
```

Each run stages an isolated runtime, untouched carrier and fresh zero SRAM,
archives the exact source/test/prerequisite files, and verifies original and
staged inputs after execution. Its per-run receipt is separate from matched
pair acceptance. The read-only evidence collector revalidates both complete
traces, exact current and archived sources, staged identities, case contracts,
historical attempts, source spans and byte identity. Raw traces, states,
cartridges and staged runtime files remain private.

This establishes only the declared minimal-handler synthetic contract in
Mesen. It is not physical-SNES timing validation, Chrono Trigger's full normal
NMI closure, IRQ nesting, publication visibility, or real-game stack ownership.
It adds no game hook, production allocation, high-selector binding, command
stream execution, save behavior, or playable eighth character. The separate
normal-NMI frontier audit and production integration gates remain mandatory.
