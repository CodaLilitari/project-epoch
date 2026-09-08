# Original immutable-ROM timing calibration v4

Status: two fresh source-frozen calibration runs pass all 22 groups each at
`verified-runtime`, within the original diagnostic scope. Their complete traces,
per-instruction elapsed projections and 92 inferred schedule rows are identical.
The runtime sources passed independent review before launch; final metadata and
report review are pending. This separate experiment preserves the completed v3
proof and the separate NMI observer. It requests no interrupt, edits no cartridge
byte, and executes no pointed package stream.

The purpose is to measure the normal helper's arrival time at each selected
instruction boundary. The original v4 NMI pilot has already shown why the
whole helper cannot be required to finish inside a single VBlank interval.
Scheduling must instead arrange the selected interruption inside that interval
and prove the actual trigger/handler/RTI phase in the separate NMI experiment.
This calibration supplies measured delays and a scheduling inference only.

The 22 groups use the unchanged original ROM helper at `$41:0000`, descriptor
bank `$42`, registry bank `$43`, entry bridge `$00:8060`, and fixed ROM tails.
They cover all four original bound selectors `$80-$83`, both flag branches
`$00/$40`, and SP `$1FEF/$06D8` (16 groups), plus canonical `$7F`, early refusal
`$90`, and framed unbound refusal `$84` at both SPs (six groups). All groups
use initial P=`$00`; timings for other status inputs are not asserted here.

Each group waits at the original `$00:8040` idle loop. Two consecutive idle
instruction samples bracket an actual false-to-true `internalRegisters.nmiFlag`
transition, with the non-consuming `$4210` peek agreeing. The fixture starts
one observed scanline later. No PPU, NMI latch, master clock or frame field is
edited. Setup changes only the declared CPU register fixture, WRAM, and zero
peripheral enable values. It never writes `$80` to `$4200`.

The full baseline snapshot occurs before the original entry JML at `$00:8060`.
As with v3, Mesen executes that redirected setup instruction without a second
exec callback. The first helper opcode and every later helper instruction have
their own observation; each fixed tail is intercepted before its BRA executes.

The normal record is passed to the unchanged, source-pinned v3 validator.
Complete helper PC/peek order, exact ROM data-read order, final CPU, ordered
publications, live stack access ownership/SP observations, untouched old scratch,
immutable input snapshots and the full final WRAM write ledger remain mandatory.
Every execution observation additionally has exactly one ordinal, bank-qualified
PC, full CPU, full-master-clock/cycle/frame/raster tuple, interrupt/DMA flag set,
and latch peek. Missing, shifted or detached timing records are refused.

The timing validator requires disabled interrupt sources and zero pending flags
at the recorded instruction boundaries. It does not claim that internal
zero-channel HDMA initialization bookkeeping is continuously zero between
those samples. If that bookkeeping reaches an observed instruction boundary,
the present calibration refuses and retains the run for a separately reviewed
policy decision. No DMA transfer or memory-ledger exception is approved.

Full master clocks and CPU cycles increase at every instruction observation.
The generic master clock is checked as the low 32 bits of the full clock.
The raster consistency bound uses the observed NMI-rise scanline as the PPU
frame-count origin. The pinned non-interlaced NTSC source increments frameCount
at that scanline, wraps raster at 262 lines, and gives each crossed line between
1,360 and 1,364 master clocks. This checks a source-supported interval, rather
than pretending that every line has exactly 1,364 clocks. Source: pinned Mesen
[`SnesPpu.cpp`, lines 397-398 and 459-486](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L397),
SHA-256 `5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180`.
The corrected phase prerequisite is regenerated and pinned before a launch.

There are 92 schedule rows: five boundaries for each success group and two
for each canonical/refusal group. Each row retains `selector`, `flag`, `sp`,
`boundary`, `trigger`, `elapsed_master_clocks`, `start_scanline`,
`observed_rise_scanline`, and `group_name`.

The schedule's elapsed time starts at the explicit **fixture baseline before
the entry JML** and therefore includes that JML's delay. A separately named
per-execution projection measures clocks/cycles from the **first helper opcode**.
The two bases must never be substituted for each other. The inferred start is:

```text
start_scanline = (observed_rise_scanline + 3
                 - ceil(baseline_to_trigger_master_clocks / 1364)) modulo 262
```

The ceiling uses integer arithmetic. This start is an inference intended for
the later NMI fixture, not a measured scheduling result or guaranteed VBlank
arrival. That experiment must still observe its natural phase, actual trigger,
hardware frame, original handler, RTI continuation, and complete helper result.

The launcher stages byte-identical original ROM/runtime inputs in an isolated
private directory, archives original guarded sources before launch, and writes
a prepared receipt before starting Mesen. It rehashes source, snapshots and
staged inputs after every launch attempt. Failed runs retain their trace,
partial instruction timing observations, preparation, source snapshots, and
process output. No shared SRAM or settings are used.

Forty-six original host tests cover the exact matrix, all schedule boundaries,
clock bases, ceiling/wrap arithmetic, complete per-instruction timing pairing,
natural latch evidence, scalar schema, source policy, raster consistency and
normal-validator refusal propagation. They use explicitly abbreviated metadata
with the independent v3 normal projection mocked; they are not native traces.
During development, an absolute-timing comparison exposed that the returned
summary aliased its input dictionaries. The summary now copies those dictionaries;
the test verifies that translating absolute clocks preserves only the elapsed
projection and schedule. No native calibration run was involved in that repair.

The first source-review snapshot is preserved under the ignored
`package_helper_v4_timing_20260908_prephase_review` directory. Review found that
the natural-latch bracket and bracket-to-baseline interval also needed the
full-clock/raster check. The original host specimen incorrectly kept one PPU
frame number while crossing the documented NMI frame-count origin; its metadata
was corrected. The first helper CPU is now bound to the baseline plus the JML's
K/PC change, and every normal SP observation is paired with its full timed CPU
snapshot. These are source/host-evidence repairs before any calibration launch.

The accepted local runs are `package_helper_v4_timing_20260908_final1` and
`package_helper_v4_timing_20260908_final2`. Each retains 15,090 instruction
observations across 22 groups, with 19 to 1,959 observed instructions per group.
Measured fixture-baseline-to-final-tail durations range from 550 to 54,108
master clocks. The observed NMI rise is scanline 225; the 92 inferred start
scanlines range from 188 to 227. The source/staged/archive hashes, immutable
ROM snapshots, unchanged v3 validation, and all additional phase/timing checks
pass in both repetitions. No bookkeeping exception was observed at a sampled
instruction boundary, and neither native run was rejected.

| Artifact or projection | Size / scope | SHA-256 |
| --- | --- | --- |
| Each raw private trace | 13,852,910 bytes | `7b21a5bb512514923eb39e5bbed22f4f34d121b7f26ca73c8a16ce63aaf6d6af` |
| Each schedule | 92 rows | `961021271ea9e8f508e418cc758f2f9c5b97aaadc60380a623ae797d106a0baf` |
| Each complete elapsed projection | 15,090 observations plus schedule | `b959dc620fab68d2ebd927b7467a2b11326f9c5ebd976a01561bfa3fa5030c75` |
| First manifest | repetition 1 | `5592818b5113845452a7e08fedb14de99e60d80fbd11b6cfa7baae5f8d03da63` |
| Second manifest | repetition 2 | `80d14da9f44b1782ebaad49bd87f4d61e0b10b2976621fe52065258c8432226c` |
| Public metadata reference | 98,917 bytes | `8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb` |

The new metadata collector first rejected the staged input-script reconstruction
because its draft expected LF while the frozen Windows launcher's
`Path.write_text` emitted CRLF. Exact script content plus that CRLF equals the
retained staged bytes. The draft collector and its failure receipt are preserved
under `package_helper_v4_timing_20260908_metadata_review1`; only the new metadata
collector was corrected. Neither the native launcher, Lua, tests, traces nor
manifests changed. This was an offline metadata-check repair, not a failed native
calibration or a substituted run.

The public [reference](../references/schala_package_helper_v4_timing_calibration.json)
pins 33 current source identities, both complete artifact receipts, every
archived original source, the 92-row schedule and separate absolute timing
observations. The [collector](../tools/collect_schala_package_helper_v4_timing_calibration.py)
revalidates every normal and timing record, rederives the complete elapsed
projection and schedule, and compares the pair. Absolute clocks are retained
separately; equality of the normalized projections is the acceptance condition.
The complete trace bytes also happen to agree in this pair.

```powershell
python -B -m unittest discover -s tests -p test_schala_package_helper_v4_timing_calibration.py
python -B tools/collect_schala_package_helper_v4_timing_calibration.py
python -B tools/run_schala_package_helper_v4_timing_calibration.py --output-dir private/test_runs/package_helper_v4_timing_NEW --repetition 1 --timeout 300
```

The two source-frozen runs reproduce the exact per-execution elapsed projection
and inferred schedule. This does not execute the inferred schedule or measure
an interruption. Production selectors, placements, hooks, game interrupt
ownership and PC `$07` integration remain unapproved.
