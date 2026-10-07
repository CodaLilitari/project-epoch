# Project Epoch: native field checkpoint, October 7, 2026

**Status: paused at Andrei's request. The playable eighth-character goal is incomplete.**

Project Epoch has one successful, instrumented field run in which a separate
logical PC07 joins PC00 and PC01, loads donor00 graphics through an actual ROM
helper, and moves as the third party member. The seven original character records
remain intact. This is practical progress from the preceding field experiment:
the graphics substitution now executes as 65C816 code through a real JSL/RTL
call, with no debugger CPU edit. It is still a prepared diagnostic, not a
playable release, a completed eighth character, or authored Schala graphics.

The run covers location `$01DA`, event `$0125`, through controller poll400.
Its candidate has an independent 80-byte record with current HP968; donor00
retains HP969. Native publications identify the added object as logical07 in
active role2. PC02 remains in reserve, all seven original identities remain
joined, and PC00 continues to exist independently. Watched native coordinate
stores reconcile with subsequent snapshots: candidate screen X progresses
184, 170, 150, 154 at polls90, 180, 280, 400. The input schedule holds Left at
polls120–167, then Right at220–267. Coordinate-read callbacks were not collected.
Root also visually inspected the poll180 and poll400 images. The independent
offline reviewers checked source, trace and snapshots; they did not perform
that visual inspection.

The explicit preparation matters. The collector replays an existing load
checkpoint and records **2,725 debugger byte-write/readback pairs**: the
80-byte compatibility relocation, separate 80-byte candidate record, roster and
joined-state changes, transformed 2,553-byte event, and its two-byte length.
These are not native recruitment, event installation, or persistence routines.
The compatibility copy occurs at actual load return `$C2E65B`; candidate and
roster preparation occurs at `$C00085`; event insertion occurs at the qualified
decompression return `$C05D36`, followed by the actual caller `$C00112`.

The private 8 MiB ExHiROM diagnostic passed the scaffold and complete-diff
guards. Its 191 changed bytes relative to the inert scaffold comprise the
existing fourteen compatibility-operand bytes, the field hook and boot mirror,
checksums, and the original 157-byte adapter component. The six-byte hook at
`$C0448D` calls `$410000`; only the component's first 49 bytes execute as the
field helper. Its six other routines are unused component bytes: no battle-name
or Attack hook is installed. Actual post-checkpoint bus mappings and ROM bytes
were checked before native work and at the three helper calls.

| Observed invocation | Selector written by native helper | Instruction starts, including two return NOPs | Stack writes / reads | Observed helper-window clocks |
| --- | ---: | ---: | ---: | ---: |
| Original PC00 | 0 | 12 | 5 / 5 | 320 |
| Original PC01 | 1 | 12 | 5 / 5 | 360 |
| Candidate PC07 | 0 | 25 | 5 / 5 | 664 |

All three windows enter with SP`$06F7`, reach `$06F2`, and return to `$C04493`
with the expected context: low A05, preserved hidden B/X/D/DBR, Y incremented
once, restored SP, and the intended final flags. The five JSL/PHP/PHA stack
cells reconcile with their actual writes and reads; sixteen live caller bytes
remain unchanged. Popping does not erase the five residual cells. For PC00
and PC07, five descriptor reads and fourteen pointer-table reads each select
the same canonical donor00 data, followed by the actual loader returns. The
selector store executes at `$410029`; it is not a scripted hardware write.
No interrupt was observed inside these three short windows. This establishes
neither interrupt safety nor general game-stack ownership.

The frozen trace contains 45,276 rows. Independent offline inspection checks
the staged differences, native helper paths, graphics reads, logical/role
publications, and coordinate stores against the saved snapshots. The ten
snapshots preserve every original character record and captured SRAM; there
are zero observed native record or SRAM writes in the declared coverage.
Post-stop deferred execution and disposable shutdown battery output are
excluded. This is **one native run**, not a repeat pair or a whole-game matrix.

A subsequent host-validation review found a concrete acceptance gap: masking
a claimed stack bus address could accept a forged ROM address with the same
low bits. The additive
[`validate_pc07_native_field_v3_stack_bus_v1.py`](../tools/validate_pc07_native_field_v3_stack_bus_v1.py)
wrapper pins the frozen runner and requires integer bank00 addresses below
`$2000`, exactly equal to their recorded physical WRAM addresses. It rejects
the forged-address case and does not infer other mirrors. **All thirty actual
stack events meet this stricter condition.** The original collector, runner,
trace and run receipt remain unchanged; the correction is an additive offline
validation, not a new emulator run or a rewritten historical result.

Epoch the vehicle remains a separate protected context. Naming selector07 and
the six-byte name buffer `$7E2C4D–$7E2C52` belong to Epoch; the playable-PC
dialogue-name table's entry07 is null. No global07 rewrite, vehicle-name reuse,
or vehicle renaming is introduced. The field run preserves the six name bytes
in all ten snapshots and records no native writes to them. Vehicle appearance,
name-entry UI, travel, boarding and vehicle save/load behavior were not tested.

This work reuses the community's mappings and implementations. Mauron's
PC-before-NPC ordering and doubled object-index guidance inform the selected
insertion; the [historical mapping audit](historical_eighth_character_forum_mapping_audit_2026-08-23.md)
retains the forum sources and their limits. Temporal Redux / Jets of Time's
[`insert_copy_object` and object-call adjustment](https://github.com/OnemusCT/temporal-redux/blob/365086c1c0a33144b24bff4933998bdff82c9940/sourcefiles/jetsoftime/ctevent.py#L532-L704)
are credited implementation references. The existing
[event parser audit](location_event_item_reference_audit.md), corrected
Vehek/Mauron/JLukas record and graphics mappings, and prior native compatibility
experiments are reused. The contribution here is the narrowly checked selected
event transform and this native field observation; no first-discovery claim is
made for those mappings or the insertion technique.

The principal source files are the
[assembly component](../asm/pc07_donor_read_adapters_v2.asm),
[private diagnostic builder](../tools/build_pc07_native_field_v1.py),
[collector](../tools/mesen_pc07_field_probe_v3.lua),
[launcher and frozen validator](../tools/run_mesen_pc07_field_probe_v3.py),
[selected event transform](../tools/transform_pc07_selected_event_v1.py), and
[focused host tests](../tests/test_mesen_pc07_field_probe_v3.py).
SHA-256 identities at this checkpoint are:

| Artifact or source | SHA-256 |
| --- | --- |
| Frozen run source bundle | `b40b55833d905141ac8acc8a3b1752016f3981edbda8d641cdc6bb4174b8a063` |
| Assembly source | `df0584a820d3b6b4994298cc1f0d6b3ffc4089797b42c5d6c6217d02a4e5a914` |
| 157-byte original component | `315f409ece80e84c656930c47bc5a0d6e0f97d83aecc95b7c474abc2056750e7` |
| Diagnostic builder | `3bdc4a53057fa032b8f8af534caeac74a21b5a93b68ffc1df3a2c9e24411f71f` |
| Collector | `f1b29205209c216db135863b57734771ec0dd525716e5b11299b091adcc4eee8` |
| Frozen launcher/validator | `d06c2dcf0790e79117d17fd31552e0a4c5b449154b2c36173681641a96fa9204` |
| Additive stack-bus wrapper | `9c45e72f1b7f6f3d989744bcc04d60b9c42fa95cb731f8389c807bd9988c5afa` |
| Private diagnostic image | `cb33610be9adceaf12298a820e63c9a2aedaf32fb5b231ef54a8b14caa3cd51c` |
| Private trace | `3c34e1f22b5cf74c95ea2e3444b2c6459f9e5a39738236fc0b68636949ef1516` |
| Frozen run receipt | `042e6805cad04baaef5c395ca9357cd66f53c06e3bfe19e470d841d9afee2449` |
| Final independent review receipt | `fdfb4f48b23ec7aa694ba7f0d68831e994f39259f33ba80266db07c65cfb8032` |
| Independent review reproducer | `41b551cecf0969eeb8aa2d46aebb348dac26c50bf12299030133a0d76a360bd4` |

The run receipt is
`private/test_runs/pc07_field_probe_v3_run1/receipt.json`; its source manifest
pins all 25 run dependencies and its artifact manifest pins the private inputs
and outputs. The final 10,853-byte independent receipt is
`private/research/pc07_native_field_v3_review_20261007/receipt.json`; its
17,335-byte `reproduce.py` was independently rerun to reproduce that receipt.
These private paths
are provenance references, not distributed assets. ROMs, event payloads,
states, saves, screenshots and raw traces remain private.
The public machine-readable companion is
`references/pc07_native_field_checkpoint_2026_10_07.json`.

For an owner of the exact private fixtures, the offline receipt check is:

```text
python -B private/research/pc07_native_field_v3_review_20261007/reproduce.py
```

The frozen run's reproduction command is recorded below for a future explicit
resume; it is not an instruction to launch work during the pause:

```text
python -B tools/run_mesen_pc07_field_probe_v3.py --output <fresh-private-directory> --run-reviewed-bundle b40b55833d905141ac8acc8a3b1752016f3981edbda8d641cdc6bb4174b8a063
```

Public sources and hashes support inspection; the native result cannot be
reproduced from the public repository alone without those privately held
inputs. The raw receipt's historical status remains
`collected-awaiting-field-review`; later review is recorded additively.

After an explicit resume, the next task is the bounded ordinary-Attack
experiment: connect the accepted field state to destination event `$0126`,
observe PC07 battle initialization, and execute a real ordinary Attack using
the existing consumer-specific proposal. The separate destination transform
already has static preservation checks; it has not executed in this run.
Battle participation, Tech/menu support for PC07, native admission, persistent
PC07 save/cold-load, authored graphics and broader vehicle/game behavior remain
open. The unfinished high-Tech package helper and completed community census
are not prerequisites to repeat before that next step. Work is paused here;
the playable-character goal is not marked complete.
