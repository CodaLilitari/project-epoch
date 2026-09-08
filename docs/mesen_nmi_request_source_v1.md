# Mesen 2.1.1 NMI request mechanism for a bounded helper experiment

Status: `verified-static` source/fixture audit; runtime behavior below is an
unexecuted prediction. No interrupt, register write, ROM edit or new native
run was performed for this design. Preserve the frozen normal-only v2 proof.

Use a rising NMI-enable edge through the emulated `$4200` register while the
PPU's real NMI latch is already set. Request it at the pre-execution callback
for the selected preceding instruction. The CPU should finish that instruction,
then enter the native NMI vector using its own hardware stack machinery.
This is a debugger-requested register event; it is not a fabricated PC/SP/frame
and it is not a CPU-executed store instruction.

## Pinned mechanism

All source analysis uses Mesen commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`, the source revision already pinned
for the 2.1.1 runtime. The
[metadata reference](../references/mesen_nmi_request_source_v1.json) records
24 exact source identities and verifies their Git blob hashes against the
pinned upstream tree. New downloaded files remain private at
`private/research/mesen_nmi_request_2_1_1`; existing CPU/PPU/Lua sources remain
unchanged in `private/research/mesen_timing_api_2_1_1`.

The natural NMI latch rises at hClock 2 of the NMI scanline and clears at
scanline 0/hClock 2. Normal enabled frame-edge delivery is scheduled at
hClock 6. These are master-clock positions, not CPU instruction counts.
Do not equate Mesen's `endFrame` callback with the latch already being set:
that callback occurs at the scanline transition before the hClock-2 event.
[InternalRegisters.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/InternalRegisters.h#L104),
[SnesPpu.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L457).

When `_nmiFlag` is true and `$4200` bit 7 changes from disabled to enabled,
`InternalRegisters::Write` sets the CPU NMI countdown to 2. Rewriting an
already enabled value is insufficient. CPU reads of `$4210` normally clear
the latch; debugger peeks preserve it.
[InternalRegisters.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/InternalRegisters.cpp#L299).

The proposed API call is
`emu.write(0x004200, 0x80, emu.memType.snesMemory)`. Its path is Lua
`WriteMemory` → `MemoryDumper::InternalSetMemoryValues` →
`MemoryMappings::DebugWrite` → `RegisterHandlerA::Write` → the real internal
register handler. It changes the emulated register without consuming CPU
cycles or advancing the master clock. The side-effect-disabled memory type
would instead try an absolute-memory conversion; register addresses have no
such backing offset and are skipped. Use the ordinary `snesMemory` type.
[LuaApi.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/LuaApi.cpp#L261),
[MemoryDumper.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/MemoryDumper.cpp#L248),
[MemoryMappings.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/MemoryMappings.cpp#L113),
[RegisterHandlerA.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/RegisterHandlerA.h#L53).

Execution callbacks precede `RunOp`. CPU cycles decrement the countdown;
service is checked after the instruction completes. DMA can defer detection,
so the first experiment must exclude pending DMA/HDMA and IRQ requests.
NMI service does not depend on the current I flag.
[SnesCpu.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L29),
[SnesCpu.Shared.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L310).

## First concrete boundary

The unchanged 577-byte v2 helper at `$7F8000` has its first `JSR` at
`$7F80EE`; its target is `$7F8232`, the CountBits entry. The normal accepted
case `rom-41-flag-00-sp-1FEF` observes these at ordinals 87 and 88.
Issue the register edge at ordinal 87, before the JSR. Its CPU cycles should
satisfy the countdown, so the JSR's two return bytes are pushed before NMI
service. The hardware-saved continuation should be `$7F8232`, before the
first CountBits instruction executes. Requesting NMI at the CountBits callback
would instead let that first instruction execute before service. A relocated
helper must derive these addresses from its own exact assembled bytes.

Reuse only the original carrier's native vector `$00FFEA`, which selects
`$008020`, and its existing 16-byte counter handler. That handler contributes
PHP plus a 16-bit PHA, then restores A/P and executes RTI. Native hardware
entry contributes four additional bytes. These are test expectations, not
measured interrupt results:

| Initial helper SP | After JSR, 52 bytes used | NMI entry, 56 used | Handler minimum, 59 used |
| --- | --- | --- | --- |
| `$1FEF` | `$1FBB` | `$1FB7` | `$1FB4` |
| `$06D8` | `$06A4` | `$06A0` | `$069D` |

The low-SP fixtures `$0034/$0033/$0008` have no interrupt reserve and are
excluded. This minimal handler supplies no game-stack ownership, full normal
NMI, IRQ nesting or publication-visibility proof. Its exact original bytes,
counter at `$7E5EF0`, and broader boundary matrix are documented in the
[separate preparation note](schala_package_helper_v2_stack_interrupt_preparation.md).

## Preparation and observability contract

Use a separately numbered collector. During declared setup, disable NMI,
H/V IRQ, auto-joypad and DMA/HDMA through their normal registers. Let an explicit
original idle fixture run until prior requests are drained and the PPU reaches
an interior VBlank boundary. An initial bounded choice is one scanline after
`ppu.nmiScanline`, not the latch's leading edge. Never assign PPU scanline,
clock, `cpu.needNmi`, `cpu.nmiFlagCounter` or `internalRegisters.nmiFlag`.
Do not spin inside a Lua callback waiting for emulated time: return control to
the CPU. Bound the preparation by full master-clock/frame progress and refuse
if the required phase does not occur.

At fixture baseline and immediately before requesting the NMI, require and
retain typed `getState` fields:

- `internalRegisters.nmiFlag=true`, `internalRegisters.enableNmi=false`;
  H/V IRQ and auto-joypad enables false.
- `cpu.nmiFlagCounter=0`, `cpu.needNmi=false`, `cpu.irqLock=false`,
  `cpu.irqSource=0`, `cpu.prevIrqSource=0`.
- `dmaController.needToProcess=false`, `dmaController.hdmaChannels=0`;
  retain the individual pending/delay flags too.
- Exact CPU registers/SP, `ppu.scanline`, `ppu.nmiScanline`,
  `memoryManager.hClock`, full `memoryManager.masterClock`, CPU cycle count,
  PPU frame count, and the original timing-key consistency checks.

These names follow the pinned serializers and name-normalization code; the
future collector must assert their presence and types rather than silently
substitute absent fields. `emu.read($4210,snesMemory)` also reaches a debugger
peek in this version, so it can cross-check latch bit 7 without clearing it.
[InternalRegisters serializer](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/InternalRegisters.cpp#L394),
[DMA serializer](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp#L638),
[name normalization](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Utilities/Serializer.cpp#L237).

Record the trigger as its own debugger event with before/after register state
and unchanged CPU/master clocks. The predicted immediate after-state has NMI
enabled and countdown 2. This write bypasses ordinary CPU write callbacks and
must not be reported as an executed STA. At handler entry, record a one-shot
`$4200=0` debugger event to prevent a later frame-edge NMI; refuse unexpected
additional requests instead of erasing them through state edits.

Acceptance must observe the JSR's two stack writes followed by four distinct
hardware writes, actual vector reads at `$00FFEA/$00FFEB`, handler entry,
every handler opcode/stack access, the single counter increment, pre-RTI and
the actual `$7F8232` post-RTI continuation. At native entry, stack bytes above
SP must be saved P, PC-low, PC-high, K; live P is `(savedP & ~$08) | $04`.
Keep hardware frame writes distinct from JSR-owned writes even though the last
helper execution ordinal still names the JSR. Restore the exact post-JSR CPU
state and complete the ordinary helper result/write/diff contract.
[native interrupt/RTI implementation](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L463).

One further provenance detail: an exec callback's value argument is the
debugger's pre-instruction opcode peek, not an independently observed opcode
bus fetch. The CPU's later opcode-read event does not emit a second exec
callback. Record it as a peek and compare it with exact mapped code bytes.
[SnesDebugger.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/Debugger/SnesDebugger.cpp#L145),
[Debugger.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/Debugger.cpp#L212),
[ScriptManager.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/ScriptManager.h#L61).

Reproduce all pinned source/fixture checks and metadata without a native run:

```powershell
python -B tools/audit_mesen_nmi_request_source_v1.py
```

The audit emits metadata only. Its source facts are statically verified;
chosen phase, delivered instruction boundary and measured 59-byte combined
depth remain runtime obligations. This mechanism tests a deliberately requested
interrupt in one emulator revision, not physical-SNES timing or a production
Chrono Trigger interrupt policy.
