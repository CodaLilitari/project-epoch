# Schala sidecar binding performance architecture

Status: round8 experiment measured; stop gate reached; no game ROM writes, hooks, or allocations  
Scope: profile-1 binding performance only  
Evidence boundary: synthetic standalone current-bsnes measurements  
Last updated: 2026-07-27

## Decision

The bounded profile-1 experiment is complete. Its separate source-only
candidate combines:

1. compile-time eight-round unrolling;
2. byte-decomposed lookup tables for the four SHA-256 sigma transforms; and
3. canonical eight-round boundaries that could support a future cooperative
   interface.

It passes exact standalone correctness but takes 68-69 frames, about 1.14
seconds, per `$0A00` slot under a minimal NMI load. This exceeds the
predeclared 30-frame stop gate. Do not integrate any of the three monolithic
SHA cores into a Chrono Trigger path.

Do not weaken profile `$01` to a CRC merely to clear a timing gate. The v2
contract deliberately promises a collision-resistant full-slot binding.
Changing that promise requires a new binding profile, host lifecycle model,
migration policy, and an explicit threat-model decision.

## Measured baseline

The inputs below are original synthetic benchmark cartridges and zero-filled
disposable SRAM. No game ROM or game save is used.

| Candidate | Source SHA-256 | Slot frame deltas | Mean seconds per slot at 60.10 Hz | Relative speed |
| --- | --- | --- | ---: | ---: |
| correctness baseline | `0c9636a6fbfdd79f14db83d90488552894d694da30632edd336dfebc78d169f0` | 366, 367, 366 | 6.095 | 1.00x |
| fixed-rotate candidate | `f4244a5f4c5586a0f096f5f12baf3400bf0402af1136cb73b115147e9e4e0f86` | 123, 123, 124 | 2.052 | 2.97x |
| round8/table candidate | `90c2c7d887089e01c717c7356c0bd4d65b595c4793b05ea18c18bd309cb3cdf3` | 68, 69, 69 | 1.143 | 5.33x |

Both independent fast runs:

- produced the three pinned profile-1 digests;
- returned status zero for valid calls and `$FFFF` for the invalid pair;
- preserved `A`, `X`, `Y`, `P` including decimal, `D`, `DBR`, and `SP`;
- preserved both scratch guards;
- retained the invalid-call output sentinel; and
- committed the same decoded result record, whose SHA-256 is
  `92a12e353b112ffa03f86566cf59e15354b758a2981e80d5a1b7f259f8ab5bfe`.

The full fast RASTATE hashes differ, as expected, outside the defined evidence
spans:

- run 1:
  `38f323db1e717778780f61d4c8c31f198b8b95f23f85fce58b5dc2dc706cae4a`;
- run 2:
  `a87fc78b0f9d2e2e1ed2d8fbdd94d9971c54170193e4216ace11497ae3a71be4`.

Both independent round8 runs also pass every digest, ABI, invalid-output,
guard, and zero-SRAM check. Their complete RASTATE hashes are:

- run 1:
  `591218c3f4ce8bb19aba51163850d84416a5d1058791a2fde5bf55bd76a0623f`;
- run 2:
  `6974a1f1a50d365b5778963807bd35b7060ff1366f44a98aafe21eb2b398a808`.

The decoded result record is identical between runs and hashes to
`58af32127cdf9b0f8a11fee2d2a4bb90f8e847bda1492ad5aae9092e1f700c75`.
Scratch plus guards hash to
`14cc30162870a2fbac89a49a07568a31c194c9ed7d8cc7d0b2250486e103303f`;
the exact 8 KiB SRAM remains the pinned all-zero image. The fail-closed
private runtime manifest hashes to
`ad20b04e0be5345184db3246bb6be02bd669ad0cb50d5b4799e3b9e874be7a45`.

Profile `$01` always compresses 41 blocks and executes 2,624 rounds. The fast
measurement is therefore about 3.01 frames per compression block and 0.047
frame per round. These are aggregate NMI-frame measurements, not exact CPU
cycle counts, but they are sufficient to reject the current routine as a
synchronous production candidate.

## Why the measured candidate is eight-round unrolled

The fixed-rotate source still performs runtime work that is known entirely at
assembly time:

- tests and increments the round number 64 times per block;
- derives the round-constant index and circular-schedule index every round;
- derives three circular-schedule indices during every expanded round;
- copies `h=g`, `g=f`, `f=e`, `d=c`, `c=b`, and `b=a` through WRAM every
  round; and
- copies each sigma operand through shared input/result temporaries.

An eight-round macro can rotate the symbolic meanings of `a` through `h`
instead of copying six 32-bit values every round. After exactly eight rounds,
the physical `a` through `h` layout is aligned again. That boundary is useful
both for a monolithic compressor and for a resumable job.

Each expanded-round macro can also name its circular `W` offsets and embed its
two 16-bit halves of `K[t]` directly. This removes runtime masking, shifts,
index transfers, round-counter traffic, and the `K` indexed reads. Keep the
16-word circular schedule; expanding to 64 words would add `$00C0` bytes to an
already unproved WRAM allocation without being necessary for unrolling.

The candidate must continue to use bank-$7E/$7F absolute accesses through
`DBR`. Direct-page addressing is not a free optimization: 65C816 direct page
is in bank `$00`, so it cannot address a proposed high-WRAM scratch block such
as `$7E:4000`. No low-WRAM allocation may be assumed.

## Exact table strategy

All four SHA-256 sigma functions are linear over XOR. For a 32-bit input
`x = b0 || b1 || b2 || b3`, each transform can be represented as:

```text
sigma(x) =
    table_position_0[b0] XOR
    table_position_1[b1] XOR
    table_position_2[b2] XOR
    table_position_3[b3]
```

Each entry is one 32-bit result in the core's existing numeric-high-half,
numeric-low-half representation.

| Property | Bound |
| --- | ---: |
| entries per byte-position table | 256 |
| bytes per entry | 4 |
| byte-position tables per transform | 4 |
| transforms (`Sigma0`, `Sigma1`, `sigma0`, `sigma1`) | 4 |
| exact total table bytes | `$4000` |

The tables must be generated from the mathematical rotate/shift definitions,
not copied from another ROM or binary. Put the four `$1000`-byte transforms in
one standalone data bank for the experiment and assert every boundary. A
future production builder would need named expanded allocations; this design
does not create them.

The host generator must prove all 4 x 4 x 256 basis entries, reconstruct
adversarial and deterministic random 32-bit inputs from the four tables, and
compare every result with direct host arithmetic. Existing standard SHA-256,
profile trailer, zero-slot, patterned-slot, all-three-slot, and invalid-pair
vectors remain mandatory.

Tables should be measured, not assumed faster. Expanded ExHiROM allocations
map through the slow full-bank `$40-$7D` window, so the gain must come from
fewer instructions and fewer WRAM temporaries, not from claiming FastROM
timing.

## Bounded candidate and gates

Create new files rather than modifying either proved reference:

```text
tools/generate_schala_sha256_65816_sigma_tables.py
tests/test_generate_schala_sha256_65816_sigma_tables.py
asm/schala_sidecar_sha256_sigma_tables.asm
asm/schala_sidecar_sha256_profile1_round8.asm
asm/schala_sidecar_sha256_profile1_round8_syntax.asm
asm/schala_sidecar_sha256_profile1_round8_benchmark.asm
```

`asm/schala_sidecar_sha256_sigma_tables.asm` is a generated, unplaced Asar
source unit despite its `.asm` suffix. A consumer includes it only after
supplying the mapping and `org`; the generated unit itself must contain
neither.

The implemented candidate satisfies these static bounds:

- preserve the profile-1 input, digest bytes, argument validation, output
  preservation, and caller ABI exactly;
- retain the current `$00C2` scratch bound for the monolithic entry;
- unroll in eight-round groups, not 64 unrelated hand-written bodies;
- keep generated code at or below `$6000` bytes and generated tables exactly
  `$4000` bytes, each with no bank crossing;
- preserve or improve the current 17-byte total stack-growth bound including
  the caller's `JSL`;
- add assembler labels around every eight-round group and every generated
  table so a validator can account for exact sizes;
- use only the synthetic all-`$FF` 8 MiB benchmark target and disposable
  generated SRAM; and
- reuse the current result ABI so the existing state inspector can compare
  functional output directly.

Use these provisional timing dispositions:

| Measured slot time | Disposition |
| --- | --- |
| at most 12 NMI frames, about 200 ms | eligible for later synchronous hook experiments |
| 13-30 frames | cooperative-only candidate |
| more than 30 frames | do not integrate; revisit the binding profile or a different algorithm |

These are experiment routing gates, not production approval. Actual save,
load, preview, New Game+, and interrupt-path budgets still require measurement
inside the game.

The measured 68-69 frames lands in the final row. The candidate is therefore
preserved as correct standalone evidence but is not eligible for either
synchronous or cooperative game integration under this architecture.

## Cooperative interface if a future result is 13-30 frames

Do not wrap the existing two-second monolith in a frame scheduler. Make the
eight-round boundary the unit of resumability:

```text
Begin(slot, base) -> INVALID or RUNNING
Step(fixed_group_budget) -> RUNNING or DONE
ReadDigest() -> valid only after DONE
Cancel() -> IDLE with no publishable output
```

There are 8 groups per compression block and 41 blocks, hence 328 deterministic
groups per slot. At every group boundary the physical working-state layout is
canonical. The resumable context needs the chaining state, working state,
circular schedule, slot cursor, block number, group number, status, and an
owner/generation token. Any context growth beyond `$00C2` must be explicit and
separately allocated; it must not silently consume adjacent WRAM.

`Step` belongs in a proved main-line scheduler, never in NMI. It must preserve
the same caller ABI on every return, force binary arithmetic only internally,
and refuse a second owner while a job is active. The actual number of groups
per frame must be fixed only after an emulator benchmark shows the worst-case
group cost under real Chrono Trigger NMI/IRQ load.

### Input immutability

A digest spanning frames is correct only if the selected `$0A00` bytes cannot
change during the job. Rechecking the 16-bit vanilla checksum afterward is not
enough, because profile `$01` specifically closes same-checksum substitutions.
The lifecycle must therefore own a save-system lock that prevents every writer
from touching the selected slot until completion or cancellation. NMI, DMA,
save, erase, New Game+, and preview paths must be audited against that lock.

### Publication order

Normal save:

1. invalidate the selected sidecar magic;
2. let the native writer finalize the exact vanilla slot and checksum;
3. lock that slot and run the digest job;
4. write the sidecar body and its CRC;
5. commit magic last and read it back;
6. unlock and leave the saving state.

Power loss before step 5 produces SafeEmpty, never a stale accepted sidecar.
The UI may not report saving complete before step 5.

Full load:

1. validate the vanilla slot before reading or classifying the sidecar;
2. establish SafeEmpty live PC `$07` state;
3. lock the immutable selected SRAM source and run the digest job;
4. validate the complete sidecar, digest, roster, joined bit, and identity;
5. publish PC `$07` exactly once, or remain SafeEmpty on any failure.

Preview may cache completed jobs for all three slots during title/menu idle,
but a cache entry is usable only while its exact source ownership token remains
valid. It is an optimization, never an authority.

## Explicit decision now required

A table-driven CRC64 would probably clear the timing problem and would be
strong protection against accidental corruption. It would not preserve the
current stated collision-resistant binding property: CRC is linear and an
intentional same-CRC substitution is practical even though neither CRC nor
unkeyed SHA authenticates an author.

The bounded round8 experiment exceeds 30 frames, so implementation stops here
and the next choice must be explicit:

- retain profile `$01` and accept a measured cooperative transition; or
- define a new integrity-only profile and revise the threat model.

An integrity-only profile must use a new profile number, canonical output
encoding, new host codec and lifecycle tests, explicit migration/refusal
rules, same-checksum adversarial fixtures, and new runtime evidence. It must
not reinterpret profile `$01`, silently truncate its digest, hash less than the
exact `$0A00` bytes, or rely only on the existing 16-bit vanilla checksum.

## Required evidence before any game integration

- Exact host/65C816 equality for standard, profile, patterned, and all-three
  slot vectors.
- Exhaustive generated-table basis validation and deterministic source hash.
- Asar syntax, code/table size, bank-boundary, stack, and scratch audits.
- Invalid slot/base refusal with unchanged output.
- Decimal-mode and full caller-ABI preservation.
- Guard checks and a high-water audit for every resumable context byte.
- Pause/resume equivalence after each of the 328 group boundaries.
- Reset, cancellation, duplicate-owner, and source-lock failure injection.
- Two independent current-bsnes standalone runs with identical defined
  evidence spans.
- Only then, separately approved game allocations and save/load/preview/
  New Game+/erase timing replays.

Until those gates pass, all three current SHA sources remain diagnostic
evidence, not production inputs.
