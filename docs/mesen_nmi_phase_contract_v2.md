# Corrected Mesen NMI phase and Lua field contract v2

The published v1 preparation note incorrectly required `ppu.nmiScanline`
from `emu.getState()`. Mesen 2.1.1 explicitly hides this field from its Lua
Map serialization. The corrected preparation observes the actual natural
VBlank latch transition, cross-checks it with a non-destructive register peek,
then starts on the following observed scanline. It never assigns a PPU phase,
clock, NMI latch, pending request, or hardware stack frame.

This is our source-mapping correction. The incorrect source is
[`docs/mesen_nmi_request_source_v1.md` at published commit
`9e42e747fc523d7a99dad90ce21940dfbd18c51c`](https://github.com/andreipemberton/project-epoch/blob/9e42e747fc523d7a99dad90ce21940dfbd18c51c/docs/mesen_nmi_request_source_v1.md#L93):
lines 93–94 base the interior phase on the unavailable field, line 109 lists
it among required runtime keys, and lines 113–115 attribute that inventory
to serialization. The original file has SHA-256
`c8262bf4ea157e58f17e55bbd0d9581055424798c463807c804f019ec62725cd`.
The original source audit and reference are preserved unchanged; their source
hash checks did not derive or validate the human-written observable-key
inventory. Their existing register-edge and CPU pipeline findings remain
separate claims.

The contrary evidence is direct pinned source, not an inference from a failed
emulator run. In Mesen commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`,
[`SnesPpu.cpp` lines 2287–2292](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L2287)
place `_nmiScanline` inside `if(s.GetFormat() != SerializeFormat::Map)`.
The comment states that these entries are hidden from the Lua API. The file
is 83,153 bytes with SHA-256
`5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180`;
the exact LF bytes of lines 2287–2292 hash to
`7b96d992d9395abd46a8060e7c09a65aa31fb2508a4127242c5f60c8fd3fc724`.
The ordinary `_scanline` is serialized outside this exclusion at line 2255.

The first private pilot independently exposed the mismatch. Its collector
stopped at line 129 with an arithmetic-on-nil error naming
`ppu.nmiScanline`. It produced zero completed records and zero active fixture
events, before any baseline or interrupt request. This was a preparation
failure, not a hardware NMI failure. The exact private trace is 233 bytes,
SHA-256 `afb1fac64efd1cf2fba526478a4d39667d831a8aaa9d927813fcf03333f8338d`;
the reference pins its prelaunch receipt and archived collector as well.

The replacement gate uses only observed, typed keys. Ordinary instructions in
an original idle fixture advance emulation while NMI, H/V IRQ, auto-joypad,
DMA and HDMA are disabled through their emulated registers. Consecutive idle
instruction samples retain the last false `internalRegisters.nmiFlag` and
the first true sample, full master clocks, CPU cycles, PPU frame/scanline,
horizontal clock, and the corresponding `$4210` peek. The two observations
bracket the transition; they do not identify its exact cycle. Setup proceeds
at an observed instruction on the next scanline while the latch remains true
and all declared pending interrupt/DMA state is clear. A finite full-clock
bound refuses preparation that never reaches this state. The active fixture
also requires the request and completion to remain inside its declared
VBlank interval.

The corrected exploratory pilot retained this phase at both synthetic SPs
`$1FEF/$06D8`. The first transition bracket is scanline 224, hClock 1354,
master clock 306890, latch false, followed by scanline 225, hClock 12,
master clock 306912, latch true. Its baseline is scanline 226, hClock 8,
master clock 308272. These are observed Mesen values for this fixture, not
universal SNES constants. All 16 required interrupt/DMA fields and all eight
timing keys were present. The complete key list and both witnesses are in
[`references/mesen_nmi_phase_contract_v2.json`](../references/mesen_nmi_phase_contract_v2.json).

The separately numbered native pilot records a debugger write of `$80` to
`$004200` through the actual emulated register path and observes the resulting
hardware NMI. That debugger event does not execute a CPU store or advance
emulated clocks. Its hardware-frame proof, continuation, stack/write ledger,
and adversarial review belong to the native harness; this source correction
does not independently accept those claims or a final matched pair.

Reproduce the metadata without launching an emulator:

```powershell
python -B tools/audit_mesen_nmi_phase_contract_v2.py
```

The auditor verifies all 24 upstream source blobs through the preserved v1
audit, the exact published historical document via its Git object, the Map
exclusion byte span, unchanged v1 audit/reference, the failed pilot, and the
corrected exploratory key/phase receipt. Its UTF-8/LF output reproduces the
reference byte for byte. Raw traces and original cartridge data remain private.
No normal-game NMI closure, asynchronous nesting bound, production stack
ownership, resolver hook, high-selector binding, or eighth-character runtime
integration is approved by this correction.
