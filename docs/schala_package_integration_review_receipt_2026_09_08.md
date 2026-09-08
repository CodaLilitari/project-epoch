# Package integration evidence: independent review receipt

Date: 2026-09-08. Reviewer scope: read-only source, metadata, and existing private
trace review by the interrupt-ownership worker. This receipt records checks
against exact source versions. It approves no production hook, allocation,
scratch region, ROM registry, game interrupt policy, or playable PC `$07`.

## ROM-source helper v1

The reviewed helper source is
`asm/schala_package_helper_v1_rom_source.asm`, SHA-256
`0a71029770a494707cc03eae6d80461de6de3a30544dc01cc632bf82d1079e9b`.
Its 676-byte assembled image has SHA-256
`9a8554aa0045163abcc15f021fb80dc6606f3d6ce444dea682ff04ec6cc46b63`.
The final reviewed metadata reference is
`references/schala_package_helper_v1_rom_source.json`, SHA-256
`d8b9c9ea589e33517331e377c084c0fadf91a42f1e665f5adbfb9c7895931c92`.

Source review found no blocking defect in exact bank-word validation, physical
bank bounds, two-mask extent calculation, or the native target-membership
preflight. Both masks' pointers are checked before any publication, including
pointers on the unselected branch. The last selector's 64-byte target array
ends exactly at the declared fixture boundary. Bank words with nonzero high
bytes cannot alias accepted `$0041/$0042`. These findings concern descriptor
transport; an allowlisted pointer is not proof of a valid command stream.

The initial collector retained only a short PC sample. The author and reviewer
agreed that a complete execution-span guard was useful before accepting the
stronger claim. The final collector guards the exact assembled helper interval
and the three exact route tails, retains every observed helper PC, and checks
the exact first entry and final route tail offline. It does not independently
decode every intermediate instruction boundary. A separate original JML at
`$7F:F100` is unobserved setup, required because Mesen executes the instruction
selected by `setState` without a second callback. The following first helper
instruction is observed. The report now states this boundary explicitly.

Both final `..._execguard2` and `..._execguard3` artifact manifests were checked
against the current reference. Each has 1,454 cases and the same 20,145,935-byte
trace, SHA-256
`bb5a9f54a57fb59072f6b9011bc80c4ba761b13d820e9df5acaee44b1e5595c9`.
The reviewer independently revalidated every `execguard2` case offline and
confirmed 1,049,158 retained PC observations, including 1,454 terminal
observations. Every case starts at the exact helper entry. All 32 host tests
passed, including malformed execution-sequence refusals.

The historical `final2/final3` traces and stronger `execguard2/execguard3`
traces were also projected independently onto the nine common fields named
in the reference. All four projections match SHA-256
`10e544d62bced1411aba860be6c106dfb443b4c69dfd2d6d198848767bc194a1`.
This verifies unchanged recorded CPU results, publication writes, WRAM
changes, ROM reads, read counts, and input snapshots across the instrumentation
change. It does not make the historical PC sample complete retrospectively.

## Clean-ROM resolver context validator

The final reviewed source identities are:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/run_package_resolver_context_v1.py` | 24,784 | `88ccf83e83a68f7bbdc3c65e626b1480041c9e95db4fe36541a6c267b8030214` |
| `tools/mesen_package_resolver_context_v1.lua` | 7,746 | `f7b74d551b74e1b81f0b1be68f07a96ab1a6915a42d6d1d0d832b6d7be5b6519` |
| `tests/test_package_resolver_context_v1.py` | 10,546 | `8927c5ee0d2b29a89e59f5a9534a1a42c0e42511a6efaa8f07b8d590de53d86a` |

All 30 host tests passed. The final validator also accepted the existing
private `resolver_context_20260908_hardened1/trace.json` offline: 11,905 records,
2,402 paired interrupts, one PC-scoped NMI scene-clear witness, and no
interrupt entry during the short resolver. All observed IRQ saved-I values
are zero in that replay. The minimum interrupt-entry SP is `$06C1`; the
minimum SP among recorded handler snapshots is `$06A2`. The latter is a
sampled minimum, not a complete stack low-water measurement.

Review covered strict record shapes, native hardware-frame preservation,
LIFO handler identities, full-clock/cycle/frame monotonicity, the low-32-bit
generic clock relationship, the actual scene-clear write and post-write
readback, and the later caller read within the same PC observation window.
Entry live P must equal `(saved_hardware_P & ~$08) | $04`. Live P immediately
before RTI need not equal entry live P because RTI restores the saved status.

A proposed universal rejection of IRQ frames with saved I set was withdrawn
during review. Mesen's CPU implementation samples `PrevIrqSource` during an
earlier cycle and dispatches from that saved sample after the current opcode;
SEI can update P in between. The validator consequently reports observed I
values and includes a passing latched-I1 fixture. This is a source-derived
pipeline possibility, not a claim that the captured game replay reaches it.
The pinned source files are retained privately under
`private/research/mesen_timing_api_2_1_1/`:

- `SnesCpu.cpp`, 3,666 bytes, SHA-256
  `ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8`;
  `CheckForInterrupts` starts at line 46 and tests `PrevIrqSource` at line 56.
- `SnesCpu.Instructions.h`, 27,673 bytes, SHA-256
  `9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd`;
  SEI is at lines 261-264, and native interrupt stacking/status transformation
  is within lines 505-533.
- `SnesCpu.Shared.h` samples `PrevIrqSource` at line 337; its identity is
  recorded with the context collector's source provenance.

The first two files were obtained from the official Mesen 2.1.1 source:
[CPU implementation](https://github.com/SourMesen/Mesen2/blob/2.1.1/Core/SNES/SnesCpu.cpp)
and [CPU instructions](https://github.com/SourMesen/Mesen2/blob/2.1.1/Core/SNES/SnesCpu.Instructions.h).
The context report owns the final matched-run evidence; the reviewer did not
launch another emulator for this receipt.

## Reproduction and remaining scope

Run the two independent host suites from the repository root:

```powershell
python -m unittest discover -s tests -p test_schala_package_helper_v1_rom_source.py -v
python -m unittest discover -s tests -p test_package_resolver_context_v1.py -v
```

Private trace validation uses `validate_record` in the v1 ROM-source launcher
with each recorded case contract, and `summarize` in the context launcher.
The cited source hashes must match before treating a new review as equivalent.
Exact replay instructions and complete artifact manifests remain in the
corresponding author reports and references.

The separate [stack-frame design](schala_package_stack_frame_design_v2.md)
recommends 42 stack-relative local bytes, unchanged D, separate framed and
unframed exits, and returning the cursor through saved X before releasing
locals. Its calculated 52-byte deepest helper frame remains a design result.
The [interrupt closure report](schala_package_interrupt_closure_v1.md) retains
the bounded IRQ result and unresolved normal-NMI paths. Neither the v1
synthetic proof nor the clean-ROM context replay closes those integration
obligations.
