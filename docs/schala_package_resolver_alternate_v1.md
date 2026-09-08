# Canonical alternate player-Tech package observation v1

Date: 2026-09-08. Gate: `BA-NATIVE-INTEGRATION-DESIGN`.

Status: `verified-runtime` for two byte-identical, bounded CPU/data-flow
observations under independently reviewed and frozen sources. Both runs
contain 3,783 records, one alternate resolver invocation, the complete
42-byte publication sequence, and same-action completion. This completes the
natural alternate-input observation; the larger integration gate remains open.

The [metadata reference](../references/package_resolver_alternate_v1.json)
binds the accepted pair, all input/source/runtime identities, the declared
checkpoint provenance, and the static mapping-correction packet. Its
[read-only collector](../tools/collect_package_resolver_alternate_evidence_v1.py)
revalidates both raw traces and regenerates the reference deterministically.

The ordinary Black Hole action by logical PC `$06` (Magus), targeting Spekkio,
provides a natural input to the canonical resolver's alternate branch. The
target's boss-type bit takes the immunity path, removes its result-mask bit,
and leaves both target-result masks empty. Canonical code then sets action
flag `$AE94` bit `$40`; the animation setup carries that value to `$A0B3`.
The existing player-Tech resolver enters with selector `$37` and branch word
`$0040`, publishes the second descriptor mask's scripts, returns through its
ordinary call frames, and reaches the same action's completion reads.

The ROM remains the unchanged canonical US Rev0 image. No high selector,
helper, patch, memory edit after state load, game hook, expanded allocation,
scratch assignment, or logical PC `$07` is installed or approved.

## What the checkpoint establishes

This experiment loads a previously captured diagnostic checkpoint. Its
provenance has three distinct stages:

1. The 8,192-byte SRAM is byte-identical to `ChronoTrigger.srm` inside the
   locally pinned Outrunner archive, `zophar_7175_after_crono_return.zip`.
   The [earlier source-save audit](vanilla_magus_recruitment_runtime_trace_2026-07-26.md#source-save-provenance)
   records its attribution to the [Zophar save listing](https://www.zophar.net/savestates/snes/chrono-trigger.html).
   Its third slot begins at the End of Time with active IDs `$06/$04/$03`,
   corresponding in order to Magus/Frog/Robo. This is an imported external
   save, not evidence that the current experiment played from New Game.
2. The original [checkpoint collector](../tools/mesen_spekkio_checkpoint.lua)
   explicitly writes that complete SRAM image into Mesen's `snesSaveRam`
   before boot, selects Continue and slot 3, and navigates with controller
   input. It captures the native state at Spekkio's talkable field position,
   location `$01D1`, coordinates `1568,2623`, after relative input poll 3236.
   The historical log calls that field `frame`; it counts input-poll callbacks.
   The checkpoint creation is a declared diagnostic setup operation.
3. This alternate-resolver collector loads that unchanged talkable checkpoint
   and supplies only the fixed controller schedule below. It does not run
   `mesen_event11c_trace.lua` or inherit that later collector's volatile
   Tech-grant/canary profiles. No SRAM or WRAM write API appears in this
   observation collector.

The route source and the accepted checkpoint reference agree on the state
identity. The archive's embedded SRAM was independently hashed again for this
audit and matches the observation input. Copying the original external save
into a disposable emulator directory does not mean its contents were authored
or changed by the project.

| Provenance artifact | SHA-256 |
| --- | --- |
| Outrunner archive, 2,421 bytes | `0a49d5634b6739202b9be7f1992b59d285f8589087056c75fd84d92111c80ca2` |
| SRAM, 8,192 bytes | `a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9` |
| Archive readme, 405 bytes | `9e32a2de4672afc239122d1735e861f94829ec65674f1640cefdd197394a2160` |
| Checkpoint collector, 6,494 bytes | `6edd5fc924fb272714ccbb56c72f038003c3118f9c02d14dc5a5252c6cb01948` |
| Checkpoint route log, 621 bytes | `fa3b549802d54510bb1362b79feb6fb16e4e6c1d8eacfc446f76fd5b321515d2` |
| Native talkable state, 133,993 bytes | `26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e` |

The [historical Mesen checkpoint acceptance reference](../references/mesen_event11c_trace_accepted_artifacts_v1.json)
retains the checkpoint, route-log, screenshot, state-key, and runtime hashes.
Raw SRAM, states, logs, screenshots, and traces remain ignored private files.

## The alternate branch has a complete causal witness

The focused collector observes pre-execution CPU sites and actual memory-write
callbacks. It keeps these distinct: a callback before `STA` is evidence that
the store is about to execute, and its memory snapshot still contains the
previous value. A subsequent execution snapshot supplies the readback.

| Stage | CPU site | Relative input poll | Observed relation |
| --- | --- | ---: | --- |
| Black Hole effect entry | `$C1:F132` | 2766 | Actor slot `$00`, action type `$02`, logical PC `$06` |
| Target-type test | `$C1:F139` | 2766 | Target slot `$03`, base `$0180`; type byte contains boss bit `$80` |
| Survivor path | `$C1:F156` | 2766 | The RNG-path watchpoint `$C1:F13F` is absent from this effect invocation |
| Result-mask advance | `$C1:F18B` | 2766 | Both `$AE95/$AE96` and `$AE99/$AE9A` are zero |
| Pre-STA flag site | `$C1:F1C0` | 2766 | A low byte `$40`, M=1/X=0, stored `$AE94` still zero |
| Actual flag write | `$7E:AE94` | 2766 | Value `$40`; memory-callback PC has advanced to `$C1:F1C3` |
| Branch producer readback | `$C1:409C` | 2768 | `$AE94=$40`, `$A0B3=$0040`, actor/type/config `$00/$02/$37` |
| Player-Tech resolver entry | `$C1:4612` | 2769 | Config `$37`, selector word `$0037`, branch word `$0040` |

The validator requires the five effect sites in order, the same target
base/slot/type, the single targeted mask bit at the survivor entry, both empty
masks at mask advance, the actual flag write at its canonical next PC, and
the following producer's readback. An unrelated earlier enemy flag write
cannot supply the witness. The effect code runs before the animation config
field is populated, so it is wrong to require `$AE93=$37` already at
`$C1:F132`; the recorded actor/type/logical-PC and ordered producer relation
provide the earlier identity context.

## Publications, return ABI, and action completion

The launcher privately derives selector `$37`'s canonical descriptor from the
full-hash-checked ROM using the existing package-bank adapter host model. It
then compares every ordered low/high publication byte and each corresponding
canonical store PC. There are 42 bytes for owners `$00/$01/$02/$08/$09/$0A/$0B`:
seven activation words, seven script-offset words, and seven script-bank
words. These are canonical owner slots, not new playable-character IDs.
The expected script payload and raw pointers are not distributed in the report.

The native entry is M=0/X=0, D=`$0000`, DBR=`$7E`, SP=`$06D8`; its first two
near-call return words are `$432A/$40AF`. The canonical continuation at
`$C1:4616` has A=`$006E`, the doubled selector. At the pre-JMP resolver tail,
A/X/Y/P/D/DBR, the root, fully consumed first mask, retained second mask,
cleared branch word, SP, and all twelve recorded stack bytes match the model.

| Return boundary | Relative input poll | SP |
| --- | ---: | --- |
| Resolver tail `$C1:467F` | 2769 | `$06D8` |
| Common loader `$C1:4833` | 2769 | `$06D8` |
| Common loader pre-RTS `$C1:48EB` | 2818 | `$06D8` |
| Dispatcher pre-RTS `$C1:432B` | 2818 | `$06DA` |
| First caller resume `$C1:40B0` | 2818 | `$06DC` |

The validator compares the recorded portion of the stack after each original
two-byte frame is consumed. Later loop visits to `$C1:40B0` do not count as
additional resolver calls.

The package synchronization command at `$C1:4D00`, its actual `$9876=1`
write with callback PC `$C1:4D03`, and the caller's nonzero latch read occur
at poll 3365. The subsequent `$C1:40E7` read sees `$5D9B=0` at poll 3366.
Both reads belong to actor/type/config `$00/$02/$37` and SP=`$06DC`.

The action window ends at the earliest next producer, next resolver, terminal,
or change to the actor/type/config tuple. Here config `$AE93` clears at poll
3370, before the later enemy producer at poll 3504. The validator therefore
ends its window at that first change and cannot attribute later enemy or
cleanup writes to Black Hole. It also rejects a trace where only the earlier
enemy completion reads are present.

This observer does not attribute scene-latch activity to an interrupt handler.
The separate [context observation](schala_package_resolver_context_v1.md)
contains the independently paired NMI-clear witness for its primary action.
Do not transfer that witness to this different replay.

The resolver entry-to-pre-JMP-tail interval is 9,248 master clocks and 1,195
CPU-cycle-counter increments, with no video-frame increment. At the pinned
21,477,270 Hz master clock it is approximately 0.431 ms. That interval ends
before the tail jump and excludes the common loader and the complete action.
No interrupt entry/exit events are collected here, so the elapsed duration
cannot establish that no interrupt ran inside it.

Timing uses `memoryManager.masterClock`, the full serialized counter. Mesen's
generic `masterClock` field retains only its low 32 bits. The validator checks
their relation and monotonic full clocks, CPU counters, video frames, and
input polls. The [pinned Mesen source audit](schala_package_resolver_context_v1.md#clock-interpretation-and-the-32-bit-api-limit)
documents this API distinction. The synthetic tests cross a 32-bit wrap; this
replay itself does not.

## Mapping correction: the nonboss cutoff is inclusive

The pinned disassembly at revision
`eeae27acdb6565e96d1d796a3d60792c250c0aa1` describes strict-below-threshold
success in its [Black Hole header](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L30747-L30754),
and its [comment at `$C1:F148`](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L30767)
assigns equality to the survivor path. The canonical instructions contradict
those comments:

- `$C1:F144` compares the roll with the byte at direct-page `$1C`.
- `$C1:F146` branches on equality to `$C1:F14A`, the instant-death path.
- Only then does `$C1:F148` branch on carry to the survivor path. With equality
  already removed, that branch means strictly greater than the threshold.

The precise predicate is **roll less than or equal to threshold succeeds**.
With roll and threshold both 40, CMP sets both Zero and Carry, and the earlier
BEQ takes the success path. The static audit verifies eight selected
instructions, four named span hashes, and all 65,536 original byte-pair
comparison cases. Its [metadata packet](../references/package_black_hole_threshold_v1.json)
is the provenance for proposed correction `MAP-009`.

The six-byte comparison span `$C1:F144-$C1:F149` hashes to
`c6f99397ead976a855cd7f8dc2c5fb643d6370fdb3be3efb16228355e1499859`.
The whole effect/mask-tail span `$C1:F132-$C1:F1C6` hashes to
`f94e11174a1a852b30352a765aedddd47195e9324fb71e00e19be4c9fd0c89aa`.
The pinned `bank_C1.asm` file hashes to
`298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa`.

This correction proves the inclusive comparison, not the RNG distribution.
No percentage follows without separately proving the generator's outcomes and
distribution. The narrow static packet treats threshold 40 as the upstream
annotation's counterexample parameter; it does not rederive the Tech parameter
table. The observed boss branch bypasses the RNG and comparison entirely, so
this replay is not a dynamic equality-boundary test.

## Reproduction and remaining limits

The independently reviewed source freeze is:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| [Launcher and validator](../tools/run_package_resolver_alternate_v1.py) | 23,869 | `46497341c658cea57bf09ddf0382246ad271e6fc43892612c4090aa3023bd758` |
| [Lua observer](../tools/mesen_package_resolver_alternate_v1.lua) | 7,030 | `2bcbdc504b353940917f021bb99274aa682821bd186b40c397b2b105ca3b18ef` |
| [31 synthetic tests](../tests/test_package_resolver_alternate_v1.py) | 11,076 | `d96bd5a7e626427350fb1f1a2b6caed20c0129177ca157f3065e07b4ec017371` |

The two private accepted directories are
`private/test_runs/resolver_alternate_20260908_final1` and
`private/test_runs/resolver_alternate_20260908_final2`. Each raw trace is
3,296,451 bytes, SHA-256
`f4400adb7488b9f65d290bb7dafedfd29228037bdcf2470e340ef06e9bb9b26b`.
Both prepared launch receipts hash to
`9db2937e37fa69b91658977ad30a20a8c881b4926e2cb3f2bb99f0b85f400274`.
The first manifest hashes to
`d5ac67a6fdfde4fa1e6a0a117d27dd93cb452c8245cddf9f93549677d89a2b78`;
the second hashes to
`4e15244238340be92b6d8bf09656bf186e57a46e6a35b3d1f4c115004e9ef960`.

Those manifests differ only in the three documentary screenshot identities.
Their observations, full traces, input/source/runtime hashes, and scope flags
are identical. The screenshot files are retained with their individual hashes;
pixel reproducibility is not claimed. The accepted result concerns the
recorded CPU/data-flow path and its exact publications. The screenshot
difference is not attributed to a particular renderer mechanism by this audit.

Private per-run manifests keep their historical
`exploratory-runtime-not-accepted` label. The separately reviewed paired
reference records the bounded acceptance without rewriting those manifests.
The earlier broad-route exploration and the first focused exploratory trace
also remain unchanged. That first focused run executed successfully, but its
then-overstrict validator rejected the config clear after completion; it has
no final manifest or prelaunch source receipt, so it is not promoted to a
source-aligned accepted run.

Independent review also found that watched completion PCs alone were
insufficient: the caller reads and synchronization events must retain
D=`$0000`, DBR=`$7E`, M=1/X=0. The final validator enforces those checks at
all four decisive sync/read records; sixteen adversarial subcases reject
wrong direct pages, banks, or widths. All 31 tests pass. The tests also reject
earlier or later enemy completion, a missing actual flag write, wrong target
masks, reordered publications, incorrect stack consumption, and false clock
or CPU metadata. They contain original synthetic metadata and descriptors,
not extracted game data.

The runner has only a required fresh output-directory argument. It verifies
the fixed ROM, external-source SRAM, native state, and emulator identities;
stages exact copies into isolated profile/temp/Saves directories; runs a hidden
bounded Mesen process; and rejects changes to any input, source, staged file,
or save-directory entry. The output directory must remain under ignored
`private/`. The collector has no custom route or arbitrary input option.
The prepared `launch_inputs.json` is written before process launch and remains
prepared-only even after success; its role is retaining the input identities
if the process or later validation fails. A successful final manifest is
written only after exit code 51 and all post-run input/save guards pass.

The fixed sequence uses relative input polls:

| Input | Inclusive poll intervals |
| --- | --- |
| A to progress dialogue | Four-poll pulses beginning at 60, 180, 300, 420, 540, 660, 780, 900, 1020, 1140 |
| Down to Tech | 2040-2043 |
| A to open Tech | 2080-2083 |
| Up to the first Tech | 2120-2399 |
| Six Down pulses | 2440-2443, 2480-2483, 2520-2523, 2560-2563, 2600-2603, 2640-2643 |
| A to select and confirm Black Hole | 2720-2723, 2760-2763 |
| Terminal observation | 4400 |

All other buttons are false. Screenshots at polls 2100, 2680, and 3000 are
private evidence; the 2680 image visibly selects Black Hole. Neither input
polls nor menu snapshots alone replace the CPU/data-flow validation.

```powershell
python -B -m unittest tests.test_package_resolver_alternate_v1 -q
python -B tools/run_package_resolver_alternate_v1.py --output-dir private/test_runs/resolver_alternate_NEW1
python -B tools/run_package_resolver_alternate_v1.py --output-dir private/test_runs/resolver_alternate_NEW2
python -B tools/audit_package_black_hole_threshold_v1.py --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
python -B tools/collect_package_resolver_alternate_evidence_v1.py
```

An alternate animation branch is not preflight cancellation. This action has
already run its effect-preparation path, and its existing package completes
the game's ordinary lifecycle. It does not establish how a new unbound
package should refuse before spending MP or preparing results. The
[cancellation contract](schala_package_cancellation_contract_v1.md) remains
a separate installation gate.

The earlier primary resolver proof remains complete and unchanged. This pass
adds the natural `$0040` branch, not a high-selector integration, ROM-source
helper installation, interrupt-safety proof, new playable actor, or production
eighth-character patch.
