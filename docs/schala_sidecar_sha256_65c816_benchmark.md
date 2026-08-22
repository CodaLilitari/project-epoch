# Schala sidecar SHA-256 65C816 benchmark

## Scope and status

Project Epoch sidecar v2 binding profile `$01` hashes the complete finalized
vanilla save slot plus a 16-byte physical-slot trailer. The host lifecycle
model already defines and tests that construction. This work adds a
correctness-first 65C816 implementation and a standalone emulator benchmark
without installing any Chrono Trigger hook, allocation, or data.

The benchmark cartridge is an original synthetic 8 MiB ExHiROM containing
only Project Epoch test code, headers, vectors, and `$FF` fill. It is generated
only below ignored `private/`. Its disposable SRAM and savestates are also
private. No clean ROM, patched ROM, save, state, or extracted game data is a
source-controlled artifact.

Evidence must remain split:

- host vectors and source audits are `source-only-host-model`;
- deterministic assembly and complete-diff checks are `verified-static`;
- the recorded standalone digest, ABI, bounds, minimal-NMI, and timing
  observations are `verified-runtime`;
- production placement, scratch allocation, interrupt policy, and hooks remain
  unapproved.

## Why Asar is present

[Asar](https://github.com/RPGHacker/asar) is the assembler used to translate
the new human-readable 65C816 source into SNES machine code. The staged
[v1.91 release](https://github.com/RPGHacker/asar/releases/tag/v1.91) is used
only for:

1. a temporary raw syntax probe of the relocatable SHA include; and
2. the private standalone benchmark cartridge.

It is not currently used to patch Chrono Trigger. The production ROM write
catalog remains empty. The benchmark builder treats Asar output as untrusted,
audits all changed spans against an all-`$FF` synthetic baseline, finalizes
both standalone headers, and writes only a private diagnostic artifact.

Pinned local tool provenance:

| Artifact | SHA-256 |
| --- | --- |
| official Asar 1.91 archive | `5d40f9cfa574360d8a3f382583556ba8757435274b35207977bf1cf20397b1e7` |
| `asar.exe` | `ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8` |
| bundled 32-bit `asar.dll` | `bd25cd481dcb052d4e743380417a2a19c9e46c2be558a7ad754e1d7cc1f039de` |
| bundled Python binding | `8f6a3c9c7431adfad545208c87aa68dfcdbc2f63a527b51975ddda3f5a5c95e0` |

The bundled DLL cannot be loaded by the current 64-bit Python runtime
(`WinError 193`), so the builder does not claim an in-memory DLL assembly
path. It invokes the pinned CLI on a temporary target below `private/`, then
imports and audits only declared output spans.

## Binding profile

The exact message is:

```text
exact finalized physical vanilla slot bytes $0000-$09FF
|| "PE07BIND"
|| version $02
|| profile $01
|| physical slot $01/$02/$03
|| $00
|| slot length bytes $00 $0A
|| $00 $00
```

This is `$A10` bytes and pads to 41 SHA-256 blocks. The first 40 blocks stream
from bank `$30`; the routine constructs the final trailer/padding block in
scratch.

Pinned all-zero slot vectors:

| Physical slot | SHA-256 |
| ---: | --- |
| 1 | `878829ba5210cd4d1defacbedb6c485407a25dc8be2cf46ae2bd90636b9ebdbd` |
| 2 | `45351b0ff714359ed22d687605b843658bf8ce3e2d997199ce0077323cde00b5` |
| 3 | `716b7eb41aa41f3febfb7843cb18174a01ba869cf2a634b0fe53f0d58cdd59b2` |

## Source interface

The relocatable source is
`asm/schala_sidecar_sha256_profile1.asm`. It deliberately contains no mapping,
`org`, hook, ROM allocation, or selected WRAM allocation. Its includer defines
`!PE_SHA256_SCRATCH`.

Entry point:

```text
JSL EpochSha256_Profile1Digest
```

Preconditions:

- native mode;
- 16-bit accumulator and index registers;
- `A` is physical slot `1`, `2`, or `3`;
- `X` is the matching low SRAM base `$6000`, `$6A00`, or `$7400`;
- bank `$30` contains the finalized slot.

Results and bounds:

- reads exactly `$A00` selected SRAM bytes;
- writes only the caller-provided `$C2`-byte scratch span;
- digest is scratch `+$A0..+$BF` in standard byte order;
- status at scratch `+$C0` is `$0000` or fail-closed `$FFFF`;
- invalid slot/base pairs do not alter the digest span;
- restores `A`, `X`, `Y`, `P`, `DBR`, and `D`;
- forces binary arithmetic internally with `CLD`, then restores the caller's
  original decimal flag through `PLP`;
- maximum stack growth after entry is 16 bytes, or 19 bytes including the
  caller's `JSL` return.

The implementation uses eight 32-bit chaining values, a 16-word circular
message schedule, and 16-bit high/low lanes. The final-block source oracle
converts those numeric halves back to conceptual SHA bytes before comparing
the trailer, padding, and 64-bit length.

### Separate fixed-rotate candidate

`asm/schala_sidecar_sha256_profile1_fast.asm` preserves the same profile,
entry arguments, `$C2` scratch layout, digest/status locations, invalid-output
refusal, and caller ABI. It is deliberately separate from the correctness
baseline. It replaces variable bit-at-a-time rotates with fixed byte/word
permutations and at most three unrolled single-bit steps per primitive.

Its entry point is:

```text
JSL EpochSha256Fast_Profile1Digest
```

The candidate's maximum stack growth is 14 bytes after entry, or 17 bytes
including the caller's `JSL`. It installs no mapping, allocation, or hook.
Passing its standalone benchmark does not supersede the baseline or approve
production use.

## Source-only verification

Run:

```powershell
& 'python' `
  -m unittest tests.test_schala_sha256_65816 -v

& 'python' `
  tools\validate_schala_sha256_65816.py `
  --asar private\tools\asar-1.91\asar.exe
```

Current source-only result:

- 9 focused tests pass;
- standard SHA-256 vectors match Python `hashlib`;
- zero and patterned `$A00` vectors match for all physical slots;
- the source oracle reconstructs the exact final block;
- Asar 1.91 emits 1,469 bytes;
- assembled SHA-256:
  `1f6ffadda67090156118038af719f395d4794f58024126d287951765477df91b`;
- core source SHA-256:
  `0c9636a6fbfdd79f14db83d90488552894d694da30632edd336dfebc78d169f0`.

The separate fixed-rotate validator and tests additionally establish:

- 10 focused tests pass;
- 524,288 authored macro-body comparisons pass;
- 3,145,728 primitive/sigma comparisons pass over 196,608 host vectors;
- standard, profile, patterned-slot, and all-three-slot vectors remain exact;
- the proved baseline files remain hash-identical;
- Asar 1.91 emits exactly 2,000 bytes;
- assembled SHA-256:
  `ad43218b8804d23fe9733be31352e2636c24a0b9eb8bef5be78e385b3ae117de`;
- fixed-rotate source SHA-256:
  `f4244a5f4c5586a0f096f5f12baf3400bf0402af1136cb73b115147e9e4e0f86`;
- authored wrapper SHA-256:
  `9a19c389d71e9f2f0cd6a80815b5f501923892e4efb4941660ac50fd12c9965a`;
  and
- modeled one-bit work falls from 352,928 to 57,728 steps per digest, an
  83.643% reduction. Runtime timing is measured separately below.

## Runtime benchmark acceptance

The standalone wrapper and inspector must establish all of the following
before the routine receives any `verified-runtime` label:

1. the synthetic cartridge boots through its own reset/vector code;
2. all three zero-filled physical slots produce their pinned digests;
3. a mismatched slot/base pair returns `$FFFF` without altering the digest;
4. caller registers, processor flags (including decimal), direct page, data
   bank, and stack pointer are restored;
5. front and rear scratch guards remain exact;
6. the NMI frame counter advances during each call without corrupting state;
7. the result record is complete, internally consistent, and unique in the
   current bsnes state;
8. a repeated clean run has the same functional result and artifact hashes
   for every defined evidence span; unrelated uninitialized emulator state is
   not promoted as evidence;
9. the builder manifest pins inputs, outputs, exact write spans, reproduction
   commands, and evidence levels.

## Recorded current-bsnes result

The original standalone image passed the complete-diff builder:

| Artifact | SHA-256 |
| --- | --- |
| benchmark assembly wrapper | `1f8a9a1bce6320d8571389aa6b81e054151d24d3dc561e0ea6968d2a95d7e7f2` |
| private 8 MiB benchmark ROM | `e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd` |
| private zero 8 KiB SRAM | `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47` |
| private static build manifest | `8cffbacdacb28424aa64ceae9eee1e0038a76395f2cfac869e88f4bdffbd004b` |
| standalone builder | `b07fc0f3f62714aeaa52c37c32a1ab3f41111e94d8de2ac96ddbf9dae1982ab1` |
| private two-run runtime manifest | `4eb566a7a7b657cad7c8c0a0f58d481156ec5f834482e3584d074673311a0cac` |
| runtime-manifest builder | `778c87a935930cb705dfbf1ca29742bbc0c357877a97d909e8662e7659d43356` |

The audit contains five declared spans and exactly 3,500 bytes that differ
from the synthetic all-`$FF` source. Every changed byte is inside a header,
reset/NMI, core, or vector span. Both 64-byte header/vector copies are
byte-identical and have independently finalized checksum pairs.

Two fresh 1,800-frame runs used:

- RetroArch 1.22.2, executable SHA-256
  `81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a`;
- current bsnes core SHA-256
  `003c7de04adef5f64fa106ef5175a0f66b08032001bde0383af97c5e5b81d470`;
- serialized core-state version `115.1`;
- the null video/audio/input configuration;
- freshly initialized all-zero 8 KiB SRAM; and
- no game ROM, game save, replay, or prior savestate.

The frontend log says it skipped loading the external SRAM file in
`load-nosave` mode. The raw bsnes state nevertheless exposes its exact
8,192-byte SRAM at `$022E-$222D`, and both runs hash that region to the pinned
all-zero SHA-256 above. More importantly, the three successful digests prove
that every byte actually read from `$30:6000-$30:7DFF` was zero.

Both runs produce the same `$140`-byte committed result record and the same
scratch/guard evidence:

| Evidence span | SHA-256 |
| --- | --- |
| result record `$7E:5F00-$7E:603F` | `7a232c44478d9a8879d66458c8e77697d6a3325447cb8c3f75fe7111b91c8f8b` |
| scratch plus guards `$7E:3FF0-$7E:40D1` | `c6586caf1a3ba9032a06b084611f156d75129c42c71f66de32b7fc54a734c038` |
| exact 8 KiB core SRAM | `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47` |

Decoded result:

- commit magic `PESHA816`, version 1, length `$0140`;
- overall status `$A55A`, failure count 0, four exercised calls;
- valid statuses 0 and exact pinned digests for slots 1, 2, and 3;
- ABI masks `$007F` for all valid and invalid calls;
- caller `P=$8D` restored with decimal set;
- exact `A`, `X`, `Y=$A55A`, `D=$1234`, `DBR=$12`, and
  `SP=$1FFC` restoration;
- invalid slot 1/base `$6A00` status `$FFFF`;
- invalid output sentinel unchanged;
- exact front and rear canaries; and
- NMI frame deltas 366, 367, and 366.

The two complete RASTATE hashes differ because current bsnes serializes eight
nondeterministic core bytes and this synthetic reset intentionally does not
initialize unrelated WRAM. Those bytes are outside every accepted evidence
span. The result record, scratch/guards, and SRAM are byte-identical. The two
private RASTATE SHA-256 values are:

- run 1:
  `1a0b3bd3bf94deab33bdb1fa139965ea9694da159b05a9206580b302904b6634`;
- run 2:
  `5b5d01ec518d224b224cca5bb3af3b7ce0d504bb975dde02b5fbd41d8eb36a85`.

### Correctness-baseline timing verdict

At the core-reported 60.10 frames per second, the three digest calls take:

| Slot | NMI frames | Approximate time |
| ---: | ---: | ---: |
| 1 | 366 | 6.090 s |
| 2 | 367 | 6.106 s |
| 3 | 366 | 6.090 s |

The synchronized three-call benchmark reaches completion at frame 1,100,
about 18.303 seconds. This proves correctness and resumability across the
benchmark's minimal NMI handler, but it is a measured performance failure for
a production save/load path. It also does not model Chrono Trigger's real
NMI/IRQ workload. The bit-at-a-time rotate prototype remains a reference
implementation; an optimized, separately benchmarked candidate is required.

## Recorded fixed-rotate candidate result

The fixed-rotate wrapper differs from the baseline wrapper only in its
diagnostic title, two entry calls, and included core. The current-source build
again starts from an all-`$FF` 8 MiB image, imports only the five declared
spans, and never accepts a game ROM.

| Artifact | SHA-256 |
| --- | --- |
| private fast benchmark ROM | `c0aab3909bf6068090d778c1cd3eae92c4093177b73fdb2bf19590480c6c22da` |
| private zero 8 KiB SRAM | `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47` |
| current-source static manifest | `0beb9e3e23cf060de7b6c69170cefd235b7ebf36caf45b30f87eef63bba58231` |
| private fast runtime manifest | `c464ab1006847797e6b85fc85c80a03d978f5537e11fa6baed4d4093fff4840e` |
| fast runtime-manifest builder | `08d52c856adcb6980ead0cd3b7409218b62f572e62985a9e43703c234ba4294e` |

An earlier manifest built before the wrapper's final source freeze is
rejected even though its assembled ROM bytes happen to match. The accepted
manifest binds the current 14,365-byte wrapper and complete include closure.

Two new 1,800-frame runs on the same RetroArch/current-bsnes pair pass every
baseline functional check. Their complete RASTATE hashes are:

- run 1:
  `38f323db1e717778780f61d4c8c31f198b8b95f23f85fce58b5dc2dc706cae4a`;
- run 2:
  `a87fc78b0f9d2e2e1ed2d8fbdd94d9971c54170193e4216ace11497ae3a71be4`.

Both runs have zero failures, exact slot digests, ABI masks `$007F`, restored
decimal-enabled caller state, fail-closed invalid arguments, unchanged output
sentinel, exact guards, and exact zero SRAM. Their defined evidence spans are
byte-identical:

| Evidence span | SHA-256 |
| --- | --- |
| result record `$7E:5F00-$7E:603F` | `92a12e353b112ffa03f86566cf59e15354b758a2981e80d5a1b7f259f8ab5bfe` |
| scratch plus guards `$7E:3FF0-$7E:40D1` | `c6586caf1a3ba9032a06b084611f156d75129c42c71f66de32b7fc54a734c038` |
| exact 8 KiB core SRAM | `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47` |

The complete core states differ in exactly 130,481 bytes: eight bounded
serializer bytes and 130,473 unrelated uncleared-WRAM bytes. No defined
evidence byte differs.

### Fixed-rotate timing verdict

At the core-reported 60.10 frames per second:

| Slot | NMI frames | Approximate time | Baseline speedup |
| ---: | ---: | ---: | ---: |
| 1 | 123 | 2.047 s | 2.976x |
| 2 | 123 | 2.047 s | 2.984x |
| 3 | 124 | 2.063 s | 2.952x |

The benchmark completes all three valid calls at frame 371. This is a real
approximately threefold improvement and a second standalone correctness pass,
but roughly two seconds of synchronous CPU time per digest still fails the
production save/load timing gate.

## Recorded round8/table candidate result

The bounded third candidate keeps profile `$01` unchanged and combines:

- eight compile-time groups whose symbolic `a` through `h` mapping realigns
  after every eight rounds;
- compile-time circular-schedule and round-constant indices;
- no runtime K table or round-counter traffic; and
- four generated byte-decomposition sigma transforms totaling exactly
  `$4000` bytes.

The tables are derived from the SHA-256 rotate/shift definitions, not copied
from any ROM. Their generator tests every one of 4,096 basis entries,
reconstructs adversarial and deterministic random inputs, and rejects drift.
The generated source hashes to
`7455ce0e13d243cee1c8bd0a36c8ef3582f1df4176a155f837300b907b98e61a`.

The round8 validator and 11 focused tests pin the complete K sequence, all
eight symbolic mappings, standard and profile digests, table geometry,
wrapper equivalence, stack/scratch bounds, and Asar symbols. The core is
`$4A26` bytes, below its `$6000` bound; stack remains 17 bytes including the
caller `JSL`, and scratch remains `$C2`.

| Artifact | SHA-256 |
| --- | --- |
| round8 source | `90c2c7d887089e01c717c7356c0bd4d65b595c4793b05ea18c18bd309cb3cdf3` |
| round8 benchmark wrapper | `67aad7bcdb59d200d5c6747ebf338d7993a94072879b0e88e7d7d348709f004f` |
| round8 validator | `8255e7457f02a0068e9a405fd29b9de8bf77624b8706c82b3d037f3c056f2797` |
| private round8 benchmark ROM | `47aca086d0c714a549312d75317b4fc6c4e7aca4d0af9e3a072ef8625f59028e` |
| private zero 8 KiB SRAM | `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47` |
| private round8 static manifest | `46636c5c33683622f9f742ebf0fae610d7186d28d88330a5af801d52063f2620` |
| private round8 runtime manifest | `ad20b04e0be5345184db3246bb6be02bd669ad0cb50d5b4799e3b9e874be7a45` |
| round8 runtime-manifest builder | `5fe97140e3dd2b11b3563113dfa1d64b0351507653a26130841f4955856c82ae` |

The unchanged standalone builder accounts for exactly 37,363 changed bytes
inside the same five declared spans. The expected vectors and generated
tables share the bounded `$4060`-byte bank-`$42` data span; the core remains
in bank `$41`. No Chrono Trigger ROM, save, state, or extracted data is an
input.

Two independent current-bsnes runs again pass every functional and ABI check.
Their complete RASTATE hashes are:

- run 1:
  `591218c3f4ce8bb19aba51163850d84416a5d1058791a2fde5bf55bd76a0623f`;
- run 2:
  `6974a1f1a50d365b5778963807bd35b7060ff1366f44a98aafe21eb2b398a808`.

The accepted defined spans are byte-identical:

| Evidence span | SHA-256 |
| --- | --- |
| result record `$7E:5F00-$7E:603F` | `58af32127cdf9b0f8a11fee2d2a4bb90f8e847bda1492ad5aae9092e1f700c75` |
| scratch plus guards `$7E:3FF0-$7E:40D1` | `14cc30162870a2fbac89a49a07568a31c194c9ed7d8cc7d0b2250486e103303f` |
| exact 8 KiB core SRAM | `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47` |

The two full core states differ in exactly 130,502 bytes: eight bounded
serializer bytes and 130,494 unrelated uncleared-WRAM bytes. No defined
evidence or unaccounted byte differs.

### Round8 timing verdict

| Slot | NMI frames | Approximate time | Baseline speedup |
| ---: | ---: | ---: | ---: |
| 1 | 68 | 1.131 s | 5.382x |
| 2 | 69 | 1.148 s | 5.319x |
| 3 | 69 | 1.148 s | 5.304x |

The benchmark completes at frame 207. This is exact and about 5.3 times
faster than the reference, but it exceeds the architecture's predeclared
30-frame stop gate. It is therefore not eligible for synchronous or
cooperative game integration. The measured decision boundary is documented
in `docs/schala_sidecar_binding_performance_architecture.md`: either retain
profile `$01` with a deliberately accepted longer cooperative transition, or
define and independently prove a new integrity-only binding profile. No
profile, hook, or allocation changes have been made.

## Production gates that remain

Even a passing standalone benchmark does not approve a game patch. Production
still requires:

- a proved exclusive `$C2`-byte live WRAM scratch allocation;
- a complete current-game NMI/IRQ interruption and latency policy;
- an optimized digest implementation that clears the explicit standalone
  routing budget, followed by measurement at the actual save/load call sites;
- named expanded-ROM allocation through the production catalog;
- exact save, load, erase, New Game+, preview, and failure-order hooks;
- emulator replay of all three slots with disposable game saves;
- complete-diff proof that Epoch, `$0430-$047F`, vanilla slots, global SRAM,
  and unrelated ROM data remain unchanged.
