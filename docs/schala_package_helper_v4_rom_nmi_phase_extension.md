# V4 ROM/NMI phase extension after the first pilot

Date: 2026-09-08. Status: approved experimental design; calibrated native
evidence remains required. The original
[v4 design](schala_package_helper_v4_rom_nmi_design.md) and every source
archived by its first pilot remain unchanged as history.

The first pilot's native collector completed two records. It recorded the
request and handler entry on scanline 227 and the RTI/resume on scanline 228
for both synthetic stack values. The longer immutable selector-$80 helper
then reached its final observation tail on scanline 3 after raster wrap.
The inherited host requirement that the entire helper fixture remain inside
VBlank rejected those records. The exact 7,146,622-byte trace is SHA-256
`5344fbd723568a078b8e2233f77bfb11a31930fd2079a17a071cb455fe5b5a2a`,
under `private/test_runs/package_helper_v4_rom_nmi_20260908_pilot1/`.
It is preserved as a rejected experiment, not accepted conformance evidence.
The failure exposed an overly narrow phase assumption for this larger
original fixture, not a demonstrated helper or hardware-interrupt defect.

This extension separates three periods: uninterrupted helper execution
before the request, actual NMI request through the first observed instruction
after RTI, and the remaining helper continuation with interrupts disabled.
Only the middle period must stay inside the observed natural VBlank latch
and one frame. The complete active fixture remains bounded to 120,000 full
master-clock ticks; the post-RTI continuation is bounded to 80,000 ticks.
CPU cycles and frame counters must remain monotonic. The 262-line raster
must advance consistently across wrap, with at most one frame-count
increment during the bounded fixture. NMI/IRQ/DMA pending and enabled state
must remain exactly explained by the one declared request and disable edge.
The latch's recorded bit must always agree with the debugger's $4210 peek.

Late release/PLP/JML boundaries require a different start time. A separately
numbered no-NMI calibration will observe 22 fixed source groups at status
$00: four immutable bindings times two branches times two entry SP values,
plus the canonical, unsupported and immutable-unbound route at both SPs.
It starts at the next observed scanline after the natural latch rise, retains
complete per-execution PC/timing/interrupt-state evidence, and must pass the
unchanged v3 ROM-read/output/CPU/live-stack/full-WRAM contract. Two frozen
calibration runs must agree in their exact per-PC elapsed-clock projections
and derived scheduling table. Absolute clocks remain separately recorded.

For each named boundary, the calibration supplies its elapsed full master
clocks from the declared fixture baseline. The fixed proposed start scanline
is `(observed_latch_rise_scanline + 3 - ceil(elapsed_clocks / 1364)) mod 262`.
This is a scheduling inference targeting roughly the third line after the
observed rise. It is not proof that every scanline lasts 1364 clocks; SNES
short-line variation is not hidden or normalized. The actual NMI request and
RTI phase checks decide acceptance. The three additional statuses at the
first JSR use the same explicit group schedule, with their actual native
phase independently checked; this is not a status-timing equivalence claim.

Before active observation, the CPU waits in the original `$008040` idle loop
until the fixed natural start scanline. For a start earlier than the observed
rise scanline, this means the next raster cycle, before that cycle's VBlank.
The preceding natural latch transition, baseline raster/frame/clock and
actual active-state latch transitions are retained. The helper then executes
continuously from the original `$008060` JML bridge through its selected
instruction and final tail. There is no mid-helper wait, CPU redirection,
restoration, clock edit, latch edit or manufactured interrupt frame.

The calibrated schedule and its exact source/run provenance become pinned
launch inputs. All original v4 hardware, CPU restoration, ROM-byte, complete
WRAM-ledger and unchanged-v3-projection requirements remain in force. A
calibration or actual phase failure must remain explicit history and requires
a new frozen attempt. This adds no game interrupt, stack-ownership,
production-hook or PC-$07 claim.

One raster-start bookkeeping detail is now explicitly distinguished from a
DMA transfer. The second first-pilot record samples `needToProcess=true` and
`hdmaInitPending=true` at scanline 0, horizontal clock 26. Both clear by the
next callback at horizontal clock 34, with zero HDMA channels, no pending
transfer and no CPU IRQ lock. Pinned Mesen
[memory scheduling, lines 224-258](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp#L224)
starts HDMA initialization at line 0 even with no channels enabled. The
[DMA initialization path, lines 104-118](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp#L104)
clears this request and returns without transferring when the channel mask
is zero. The [pending-state logic, lines 347-384](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp#L347)
and [per-cycle service, lines 121-130](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L121)
explain the transient flags.

Acceptance permits only that zero-channel initialization outside the actual
request-through-RTI interval: line 0, horizontal clock 12 through 64, correct
pending-flag OR relationship, and an observed clear within 32 full master
clocks. Only one observed initialization episode is allowed, and a cleared
start-delay flag cannot become set again while that episode is pending.
The first sampled pending state may already have its delay clear. Transfer
flags, nonzero channels or IRQ lock still reject. No memory
ledger exception is added. The source identities are explicitly guarded and
archived. This is a narrow correction to the proposed all-pending-flags-zero
continuation condition above; it does not permit a DMA transfer.

Raster consistency is also checked against full clocks, using intervals of
1360 through 1364 clocks for each crossed line. The pinned
[PPU line-length rule, lines 397-398](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L397)
and [frame/raster advancement, lines 459-486](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L459)
support the check. Frame-count advancement is anchored to the observed latch
rise scanline, not raster zero or the unavailable hidden `ppu.nmiScanline`.

The first full 152-case calibrated matrix completed natively, but four host
records failed the proposed 32-clock bound from the first sampled pending
flag to the first sampled clear. The remaining 148 records passed unchanged.
The rejected 217,544,660-byte trace is SHA-256
`69f2173421da9d5d0dada58e096b8937fbb6819f3ac6b95f656997f10895b061`,
under `private/test_runs/package_helper_v4_rom_nmi_20260908_final1/`.
Its exact source archives, trace and explicit host rejection remain preserved.
No second run began under that rejected acceptance contract.

All four refusals occur on selector `$80`, branch `$40`, synthetic SP `$1FEF`,
at the first-JSR NMI boundary, for the four incoming statuses. After RTI,
the original `STA $7E5DBD,X` at `$41:01DF` writes a publication word across
the line-zero initialization request. Its low-byte write samples pending
and delay true. Eight clocks later the high-byte write samples delay false
with initialization still pending. The immediately following pre-execution
callback for original `LDA $05,S` at `$41:01E3` has the same clock and flags.
The first retained data-read callback is 30 clocks later and samples clear.
The observed pending-to-clear interval is therefore exactly 38 clocks.

The source distinction is between the time initialization clears and the
time the next retained callback samples it. The
[CPU read path, lines 121-155](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L121)
services pending work before a bus read. After the start delay has cleared,
the [DMA branch, lines 367-384](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp#L367)
clears the zero-channel initialization before the next opcode fetch.
[Opcode and operand fetches, lines 379-420](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L379)
have distinct operation types. The
[script callback switch, lines 43-69](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/ScriptManager.h#L43)
and [debugger script path, lines 625-636](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/Debugger.cpp#L625)
show why their bus operations do not become separate retained general-data
callbacks. The
[stack-relative addressing mode, lines 1347-1351](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1347)
fetches its operand and inserts an idle cycle before the stack data read.
For this original instruction pair, the retained pre-execution-to-data-read
interval is opcode 8 + operand 8 + idle 6 + data 8 = 30 full clocks. The
[memory speed table, lines 89-108](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp#L89)
sets eight-clock accesses for these ROM/low-WRAM addresses; the
[idle implementation, lines 86-93](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L86)
supplies the six-clock idle.

The separately numbered calibrated-v3 contract retains the generic 32-clock
observed-clear limit. It permits exactly 38 only when the complete consecutive
original publication-low/publication-high/A3-execution/stack-read witness is
present, including the preceding `$41:01DF` execution. Original PCs and opcode
bytes, exact CPU states, physical write/read addresses, accumulator byte
values, opcode ordinals, and the exact +40/+8/+0/+30 master-clock and
+5/+1/+0/+4 CPU-cycle intervals are required. A missing/extra event, another
instruction, a changed interval or a later clear still rejects. This is not
38 clocks of pending DMA and does not widen the generic timeout. Both CPU
instruction source headers and the script/debugger callback sources join the
exact guarded/archive inventory.
