# Project Epoch: PC07 destination and battle-handoff checkpoint

Date: 2026-10-13. Coda, collaborating with Andrei. Local, emulator-assisted
runtime evidence from one successful continuous run, preceded by one rejected
collector pilot. Independent offline review reproduced the full result; root
read its source and reproduced its 38,993-byte receipt exactly. The
playable-character goal remains active and incomplete.
The companion machine record is
`references/pc07_field_battle_handoff_2026_10_13.json`; its read-only auditor
reproduces the private independent receipt before emitting the curated result.

**Logical PC07 now survives the selected field-to-destination transition and
the native preparation leading to the battle-initialization call.** The ledger
ends immediately before `$C018A7: JSL $C10000`. It does not establish battle
initialization, an ordinary Attack, victory, Techs or save/cold-load support.

This extends the [October 7 field checkpoint](pc07_native_field_checkpoint_2026_10_07.md).
It reuses its unchanged private diagnostic image, native graphics helper,
accepted event0125 transform and the previously completed event0126 transform.
No new ROM image or patch was emitted. The route uses controller input and
explicitly recorded debugger WRAM preparation; it is not native recruitment.

## New executed evidence

The successful collector v2 run is
`private/test_runs/pc07_field_battle_route_v2_run1`. Its 250,006 ordered records
cover two scene-initialization groups, six actual native graphics-helper
invocations, the destination's D8 battle request, native request consumption,
five actual candidate handoff stores with readback, and the final evidence cut
at controller poll 2,811. No debugger CPU edits were made.

The candidate remains logical07 in role2/object-offset10 (hex). Both original
active PCs00/01 remain present, and all seven original 80-byte records retain
their captured values. The candidate has its own 80-byte record and HP968,
distinct from the donor's HP969. Graphics are still temporary Crono donor
graphics; a picture of three actors does not independently establish identity.
The identity evidence comes from the observed record, roster, object and
helper paths. Root visually inspected the saved final field screenshot.

The five native exports at `$7E29BA-$7E29BE` read back as `0B 09 08 0F 03`.
Their instruction origins, source coordinate/palette values and ordered writes
are recorded. Native preparation returns carry clear before the later battle
call. These are field-side exports, not proof of battle actor initialization.

There are 4,641 explicit preparation byte-write/readback pairs: the inherited
2,725 plus 1,916 for the destination event packet and decompressed length.
The destination preparation uses an actual 1,914-byte preimage, including its
113-byte tail. It does not recreate the character record, roster, joined bits
or compatibility copy. Complete snapshots verify each preparation diff;
ordinary runtime writes are watched only in the declared ranges.

All fifteen captured SRAM snapshots equal the input. All fifteen preserve the
original seven records and Epoch's six name bytes. The staged compatibility
block and its guards, candidate record and roster retain their required
post-preparation values. This is selected-checkpoint preservation, not proof
of Epoch vehicle appearance, boarding/travel or save/load behavior. Those
vehicle requirements remain mandatory.

The source bundle is
`26114966b15ab41b807de0d8ab467db1e8e1a2ad6651855f439e74cd8b5dc9fd`.
It pins 54 source identities and reuses diagnostic image SHA-256
`cb33610be9adceaf12298a820e63c9a2aedaf32fb5b231ef54a8b14caa3cd51c`.
Original inputs and staged inputs are checked before/after the isolated
headless Mesen run. The final WRAM snapshot SHA-256 is
`9f4b6dcb0ee25303a7aca7c892952c004bc2c4c0ee73ea1a20b092631f93827f`.

## Preserved failed pilot and narrow correction

Collector v1 reached the destination and issued the request, but incorrectly
required `$0117=$21` at `$C01890`. The game actually writes `$21` at `$C03AA6`,
then its `$C0177B` TRB consumes bit `$20`, leaving `$01` for the battle branch.
The first run is preserved as a quarantined failure; it was not relabeled.

Separately derived v2 requires both real writes, two real `$C01770` reads
(`$21`, then `$01`), exact chronology and native address/CPU provenance. It
requires pending01/explore00 at the handoff. Nine focused synthetic tests
reject missing/extra writes, false bus aliases, substituted debugger writes,
wrong consumed values and out-of-order reads. Root checked the derivation,
canonical source sequence and tests before the new run. No other route,
preparation, helper or terminal guard was relaxed.

## Limits and next implementation boundary

`emu.stop` is deferred. Later disposable execution may physically occur, but
the collector closes its authoritative ledger at the pre-instruction cut;
post-cut activity and shutdown SRAM are excluded. The cut does not prove the
emulator physically halted before the call.

This is one qualified route with prepared party00/01/07. It is not a whole-game
scene matrix, full-WRAM reconciliation, interrupt proof, slowdown measurement
or a playable release. Two empty early screenshot files are documentary
limitations, not missing WRAM/SRAM snapshots; the terminal screenshot is valid.

The separate battle-adapter candidate assembles eight new helpers into 215
bytes and preserves six earlier donor-read helpers. Sixteen hook spans and
five additional compatibility operands are described, but none is installed.
A conditional host machine-byte model checks 28,544 complete-span cases;
Claude's independent source review agrees with the declared register/flag
semantics while identifying further admission/consumer questions. Neither
result proves actual game ABI, interior-entry exclusion or stack ownership.

The additive source review establishes that the vanilla weapon-mask producer
maps logical owner to active slot before calculating `$80 >> slot`; slot2
therefore produces `$20`. A selected-Attack read of that stored mask byte is
not yet observed. The reviewed canonical Tech-partner tables contain no `$07`
partner, and the three builders' party-entry reads are the proposed gated
reads. The local paths to the two long-address replacement sites preserve
incoming DBR; this does not prove all intervening calls/interrupts retain `$7E`.
Keep DBR=`$7E` as an actual hook-entry requirement. The bounded reverse-reference
check finds no decoded direct interior entry into the eight multi-instruction
spans; incomplete encodings and computed dispatch prevent a global absence
claim. Actual entry qualification, separately guarded placement and first
Attack execution remain the next specific obligations.

Reproduce the current source plan without launching:

```powershell
python -B private/research/pc07_field_battle_collector_v2_20261013/run_route_v2.py --output private/test_runs/<fresh-name>
```

The recorded runner requires an explicit exact source-bundle argument for a
new experiment. Do not rerun the completed route merely to rediscover its
mapping; use the saved trace and independent offline review. Raw traces,
screenshots, saves, event bytes and game inputs remain ignored/private.
