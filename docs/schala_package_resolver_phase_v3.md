# Primary resolver counters and cache crossing v3

Evidence level: `verified-runtime`, restricted to the repeated canonical
checkpoint replay and its captured fields. The cached-threshold interpretation
is a source-conditional inference. No helper, hook, high selector or new PC
has been inserted into the game.

V3 adds the real serialized uint16 fields `internalRegisters.hCounter` and
`internalRegisters.vCounter`, making 163 engine fields per record. It retains
the complete v2 replay contract and adds exactly two records: the first
post-load `startFrame` callback, and the first CPU execution callback on the
following PPU line 1. The command line explicitly supplies
`--snes.ppuExtraScanlinesBeforeNmi=0` and
`--snes.ppuExtraScanlinesAfterNmi=0` in an isolated portable configuration.
Source, settings parser, collector, test, runtime and staged identities are
guarded and archived.

## Repeated observation

Both independent full runs contain 2,263 records and have identical complete
trace bytes: 17,946,524 bytes, SHA-256
`cbcfee04c0eab0381d77392e43baf8cc5ed3c62b8a22ac533bf2d263424bd619`.
They each exit with the collector's success code 52. The retained process logs
each contain 28,319 uninitialized-read diagnostics, as did the earlier replay;
this is not a warning-free execution claim.

The validation projection removes only the two new records and the two new
engine fields. It equals the entire accepted v2 trace, including all 2,261
records, CPU state, stack windows, watched data, timing and interrupt identities.
Frozen v2 then revalidates its own evidence. The native trace is never rewritten.
`legacy_summary` indices describe that explicit projection; the accompanying
`projection_to_native_indices` maps them back to v3 rows.

| Selected point | Full master clock | PPU line / H clock | Internal IRQ H / V |
|---|---:|---:|---:|
| Pre-effect | 2,153,595,368 | 79 / 96 | 21 / 79 |
| Resolver entry | 2,155,080,050 | 119 / 754 | 186 / 119 |
| Resolver tail | 2,155,084,294 | 122 / 906 | 224 / 122 |
| Common loader | 2,155,084,312 | 122 / 924 | 228 / 122 |

The original resolver interval remains 4,244 master clocks / 548 CPU counter
increments. The internal counter and PPU raster are separate sampled quantities;
neither a counter snapshot nor subtraction from a later handler entry is an
IRQ-request deadline certificate.

## Cache crossing and the rejected pilot

The frame-start record is at clock 2,019,832,632, PPU line 0, H=0. The first
line-one CPU record is at clock 2,019,834,076, H=80. Their difference is exactly
1,364+80 clocks, with the same frame and poll zero. That rules out a hidden
full raster wrap between the selected endpoints under the pinned source model.

My initial validator incorrectly required these records to belong to the main
thread. The first pilot completed natively but was correctly rejected by that
predeclared validator. Both records actually belong to normal-NMI context 1.
The accepted earlier context trace brackets them with entry clock
2,019,782,308 and pre-RTI clock 2,019,989,232. The corrected validator requires
the exact historical context identity and strict clock bracketing. It does not
relabel the crossing as interrupt-free. The rejected pilot, its original
source archive and `host_rejection.json` remain unchanged under
`private/test_runs/resolver_phase_v3_pilot_20261003_1/`; a second preparation
pilot passed under the corrected source before the two full runs.

The rejected pilot's launcher archive is 11,773 bytes, SHA-256
`536799178aa01c9ef15c8a43d5c64d81929192f8fc9eab84eea6fe1990cbc604`;
its 164-byte rejection receipt hashes to
`4ad90317689d11406a554e26f0dac8b5049e83b114ef94cc70dad798b422a499`.
Its complete trace happens to equal the later accepted native trace; the
validator/source status and actual invocation remain distinct.

This corrects our unpublished pilot assumption, not an upstream ROM annotation.
It is recorded here and in the developer log without inventing a new mapping
correction against an unrelated source.

At pinned Mesen revision `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`,
[SnesPpu.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L395)
recomputes thresholds at the end of line zero when the existing cached
`_vblankStartScanline` admits that line. It emits `StartFrame` after resetting
line/H to zero. The observed crossing, fixed zero-extra arguments and pinned
source therefore support refresh **under the valid-source-state premise**.
They do not independently decode the checkpoint's hidden cache fields.
Those fields remain excluded from the
[Map serializer](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L2287).
No fictitious Lua field or direct cache-value observation is claimed.

## Reproduction and acceptance

Original sources are `tools/run_package_resolver_phase_v3.py`,
`tools/mesen_package_resolver_phase_v3.lua`, and
`tools/audit_package_resolver_phase_v3.py`. The independent read-only auditor
pins the observer, revalidates every trace, checks all source/staged/archive
identities and process receipts, requires distinct run directories and stems,
and rejects aliased evidence or unequal trace bytes. Its public output contains
hardware observations, counts and hashes; no game arrays.

These checks establish consistency of the supplied artifacts. They do not
cryptographically authenticate emulator execution against someone fabricating
or copying unsigned receipts. The two actual, separate process launches are
recorded coordinator/tool evidence. A copied directory with renamed staged
files is not a new execution merely because this offline audit passes.

```powershell
python -B -m unittest discover -s tests -p 'test*package_resolver_phase_v*.py'
python -B tools/run_package_resolver_phase_v3.py --output-dir private/test_runs/NEW_UNIQUE_RUN_A
python -B tools/run_package_resolver_phase_v3.py --output-dir private/test_runs/NEW_UNIQUE_RUN_B
python -B tools/audit_package_resolver_phase_v3.py --run-a private/test_runs/NEW_UNIQUE_RUN_A --run-b private/test_runs/NEW_UNIQUE_RUN_B
```

The 178 focused phase tests pass, including 23 v3 observation and 39 v3
acceptance tests. The historical v1/v2 suites remain unchanged. Native
reproduction requires the pinned private ROM, SRAM, checkpoint, reference
traces and exact Mesen runtime; none is redistributed. Accepted run directories
are `private/test_runs/resolver_phase_v3_full_20261003_3/` and `_4/`.
The complete hash-only acceptance metadata is
[the v3 reference](../references/schala_package_resolver_phase_v3.json).

## Next boundary

Preserve this pair. The next additive work must prove actual IRQ request timing
from the internal-counter/pending-state transition semantics, separately from
handler-entry latency. Keep the cached-state bootstrap premise visible. Any
helper-admission claim also needs HDMA source-read/rendering isolation, wrapper
cost, physical stack ownership and the pre-effect versus later-resolver
lifecycle. The enabled eight-channel HDMA snapshot remains unchanged. No late
refusal after effect preparation or MP charging is approved by this packet.

The final source was normalized to the repository LF line-ending contract
before publication. That changed the launcher hash, so the two full replays
were repeated as runs 3/4 under the final pinned source; both retain exactly
the same trace hash. Runs 1/2 and their source archives remain unchanged as
historical pre-normalization evidence. All 178 tests passed again.
