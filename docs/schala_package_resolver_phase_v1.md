# Primary resolver phase observation v1

Status: **preserved protocol; its one native pilot was refused by the host**.
The original preparation contract is retained below; the dated pilot outcome
at the end explains the unsupported early-interrupt sequence.
This is a separately versioned, read-only observation protocol. Existing accepted
resolver, context, NMI, and synthetic helper sources and evidence remain unchanged.
The purpose is to obtain the actual serialized pending-interrupt, timer, PPU-mode,
and DMA/HDMA state at the established primary resolver and its next observed
interrupts. Historical key inventories establish names and types, never new values.

The executable protocol is encoded by the new runner, Lua collector, and tests.
Their bytes, dependencies, primary emulator source, inputs, and runtime are guarded
and archived at launch. This narrative document is not an executable identity
prerequisite; later results and corrections may be appended without invalidating
the frozen run. No accepted native reference exists for this observer yet.

## Exact scope and stopping boundary

The only input contract is the unchanged clean US Rev0 ROM, imported SRAM, and
accepted `battle_ready.mss` checkpoint already pinned in
`tools/run_package_resolver_context_v1.py`. A fresh isolated runtime receives a
random unique ROM/state/SRAM stem and private profile/temp directories. Its only
script-requested game-state operations are one initial checkpoint load and the
retained controller schedule: Down at polls 20–23; A at 60–63, 100–103, and 140–143;
all other buttons false. It stops at end-frame poll **381**. It has no configurable
script, arbitrary input, CPU-state edit, memory write, helper injection, or ROM
mutation option.

The collector records:

- Initial and terminal markers.
- Zero or one candidate pre-effect instruction entry at `$C1:BBD4`, before the
  unique primary resolver. A second hit, a later transaction, or an interrupt
  context at that hit refuses; this optional point is not a cancellation adapter.
- Exactly one resolver entry `$C1:4612`, tail `$C1:467F`, and common-loader entry
  `$C1:4833`.
- The first following battle IRQ `$D1:FE97` / pre-RTI `$D1:FEF3`, then normal NMI
  `$D1:E77C` / pre-RTI `$D1:E898`, in the sequence retained by this exact checkpoint.
- Scene gate instruction entries `$CD:1609` and `$CD:160E` in that selected NMI.
- Declared gate and MMIO read/write callbacks from optional pre-effect, or resolver
  when pre-effect is absent, through the selected NMI's pre-RTI snapshot.

This first version **refuses an interrupt between pre-effect and resolver**, an
interrupt before the common loader, nested or alternate handlers, another selected
IRQ before the next NMI, a reversed first-pair order, missing scene gates, and
repeated resolver phase hits. Those are predeclared scope limits, not evidence that
these situations cannot occur elsewhere. A pilot exposing a limit must be retained
as rejected evidence; a changed protocol requires a newly frozen review and run.

Every record contains exact A/X/Y/D/DBR/SP/P/PBR/PC/native-mode state, twelve bytes
above SP, eight interrupt-trampoline bytes, 29 natural gate bytes, all eight timing
fields, and the **161 required engine fields** below. No missing field becomes a
default zero. Native mode and a twelve-byte low-WRAM stack window are required.

## Source-backed engine field contract

The public upstream revision is
[`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`](https://github.com/SourMesen/Mesen2/tree/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1).
Exact local source hashes are executable prerequisites in `ENGINE_PINS`.
The new missing type headers were fetched from that exact revision, with upstream
Git-blob and size agreement verified before private storage. Their private receipt
is `private/research/mesen_resolver_phase_2_1_1/field_type_source_receipt.json`,
SHA-256 `f6709674a2c775f2e58c6021b0bbc9a94c8bd9c8ef75038636482eee2d4bc86e`.
The PPU type receipt is `ppu_mode_type_source_receipt.json`, SHA-256
`86cb5b281837b4ba3d2b9a27e4739c544f272510e8638fcf06aedd479b519924`.

| Map prefix | Exact fields and serialized types |
|---|---|
| `cpu.` | `irqSource`, `prevIrqSource`, `nmiFlagCounter`: uint8 integers; `irqLock`, `needNmi`: booleans |
| `internalRegisters.` | `enableNmi`, `enableHorizontalIrq`, `enableVerticalIrq`, `irqFlag`, `irqLevel`, `nmiFlag`, `enableFastRom`: booleans; `horizontalTimer`, `verticalTimer`: uint16 integers; `needIrq`: uint8 integer |
| `dmaController.` | `dmaPending`, `dmaStartDelay`, `needToProcess`, `hdmaPending`, `hdmaInitPending`: booleans; `hdmaChannels`: uint8 integer; `dmaClockCounter`: uint32 integer |
| `dmaController.channel[i].`, each `i=0..7` | `decrement`, `dmaActive`, `doTransfer`, `fixedTransfer`, `hdmaFinished`, `hdmaIndirectAddressing`, `invertDirection`, `unusedControlFlag`: booleans; `srcAddress`, `transferSize`, `hdmaTableAddress`: uint16 integers; `destAddress`, `hdmaBank`, `hdmaLineCounterAndRepeat`, `srcBank`, `transferMode`, `unusedRegister`: uint8 integers |
| `ppu.` | `overscanMode`, `screenInterlace`, `objInterlace`: booleans |

The host applies the stored integer widths, plus the ordinary MMIO-producer bound
`transferMode <= 7`. Timer storage is uint16 even though the normal MMIO producer
limits H/V timer values to nine bits. `prevIrqSource` is an integer even though its
usual producer yields zero or one. `destAddress` is BBAD's byte, not a full bus
address. No PPU-mode value is assumed and no deadline is calculated from these flags.

Primary paths and relevant source locations, all pinned:

- `mesen_resolver_phase_2_1_1/{SnesCpuTypes,InternalRegisterTypes,DmaControllerTypes,SnesPpuTypes}.h`
  declare the types. The PPU booleans are at `SnesPpuTypes.h:178–180`.
- `mesen_timing_api_2_1_1/SnesCpu.Shared.h:626–630`,
  `mesen_nmi_request_2_1_1/InternalRegisters.cpp:394–410`, and
  `mesen_nmi_request_2_1_1/SnesDmaController.cpp:638–648` serialize the requested
  CPU, internal-register, and channel fields; `SnesPpu.cpp:2259–2260` serializes the
  three PPU modes.
- `Serializer.cpp:237` normalizes `_state`/private-member names and channel indices.
  `Serializer.h:127–136` maps booleans and integral types separately.
  `LuaApi.cpp:1071–1101` builds the map and pushes corresponding Lua values.
- **Do not require `cpu.stopState` or `memoryManager.nextEvent`: their enum types
  have no `WriteMapFormat` branch.** `ppu.nmiScanline` is explicitly excluded from
  Map serialization in `SnesPpu.cpp:2287`. `internalRegisters.irqEnabled` and
  `dmaController.activeChannel` are not serialized. These absent keys are never
  fabricated, and their presence in submitted trace engine objects is refused.

The earlier `snes_state_keys.txt` at
`private/test_runs/mesen2/event11c_checkpoint_v5/` is spelling corroboration only.
Its historical values are not used to populate or validate fresh engine snapshots.

## Observation semantics and evidence limits

Pinned `SnesCpu.cpp:29–43` invokes the instruction callback before executing the
instruction; interrupt checks follow instruction execution. `SnesCpu.Shared.h`
retains the distinction between current IRQ source, previously sampled IRQ, IRQ
lock, NMI-delay counter, and pending NMI. Saved IRQ I=0 is not imposed: a previously
sampled IRQ can survive a subsequent SEI.

The full serialized `memoryManager.masterClock` is authoritative. The generic
`masterClock` must equal its low 32 bits. CPU cycle counter, frame/PPU-frame
agreement, NTSC rate, and bounded raster values are checked independently.
All timing integers remain within Lua's exact integer range used by this protocol.

`MemoryDumper.cpp:362–394` and `LuaApi.cpp:244–258` establish that script memory
reads use side-effect-free peeks/direct WRAM snapshots. They are not CPU reads.
`ScriptManager.h:43–69` maps actual read, DMA-read and dummy-read operations into
the same Lua read callback family, and corresponding writes into write callbacks.
Consequently rows are named **bus-read/bus-write**, not CPU-only reads/writes.
The CPU snapshot attached to a DMA callback does not identify a CPU store.
Snapshot getters do not create watched bus events.

The bus window watches the exact 29 gate-byte addresses declared in the source,
with physical low-WRAM aliases resolved per byte, and only true hardware banks
`$00–$3F/$80–$BF` for `$4200`, `$4207–$420D`, and `$4300–$437F`. It includes
interrupt enables/timers, MDMAEN, HDMAEN, FastROM and eight channel-register ranges.
No callback outside these addresses is represented as covered. A selected NMI
`$5D9B` read after the scene-effect gate is a required positive control; its byte
must agree with that callback's WRAM peek. Write callback values are recorded
without incorrectly requiring the pre-write peek to equal the new value.

This is not a complete DMA/HDMA bus trace, write ledger, all-instruction flow trace,
or proof of no hidden/interleaved interrupt. It records selected serialized engine
state and watched bus observations. No helper is inserted or timed here. The
original helper's 67,112-clock envelope excluded DMA/HDMA/interrupts and cannot be
generalized into a game deadline. There is no interrupt-exclusion certificate,
late-cancellation adapter, stack-ownership approval, or production integration.

## Historical identity, guards, and failure behavior

The exact accepted context trace is pinned by size and SHA-256
`6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679`.
The host compares full CPU, twelve stack bytes, trampolines, all timing fields and
overlapping gate bytes at eight historical phase points: resolver, tail, common
loader, both first IRQ/NMI entry/RTI pairs, and the scene-effect gate. Only after
those matches does it report the newly derived resolver interval duration.
This reuses old context identity; it does not reuse nonexistent old engine values.

The launcher verifies source/input/runtime bytes before and after execution,
archives exact source bytes, rechecks isolated staged ROM/SRAM/state/runtime/Lua,
checks exact save/archive inventories, and retains a separate process-exit receipt.
Exit 52, an absent error sidecar, complete bounded JSON, and full host validation
are all required before an exploratory manifest is written. A successful single
run still requires independent review and an unchanged repeat before acceptance.

Each callback streams one bounded record. The collector caps records at 8,192 and
the trace at 64 MiB. Finish emits a constant-sized footer and closes the file.
Any protected callback or finalization failure directly enters `failed`, preserves
a private `.error.txt` when possible, and requests stop 93. It never calls finish
recursively. Partial JSON, duplicate JSON keys, non-finite JSON constants, schema
errors, missing/extra/type-invalid fields, altered identity, and unpaired contexts
refuse. Source pinning includes the Mesen scripting watchdog implementation and
default timeout configuration that motivated this streaming design.

Host-only verification:

```powershell
python -B -m unittest discover -s tests -p test_package_resolver_phase_v1.py
```

Native reproduction, **only after frozen-source review and launch authorization**,
uses a new empty ignored output path:

```powershell
python -B tools/run_package_resolver_phase_v1.py --output-dir private/test_runs/resolver_phase_v1_REVIEWED_UNIQUE_RUN
```

The original specimens exercise acceptance with/without pre-effect, every required
engine key/type/width, omitted enum refusal, historical CPU/stack/gate/clock drift,
interrupt pairing/restoration, the pre-effect interrupt scope limit, physical bus
mirrors, actual gate-read consistency, malformed/partial/bounded JSON, and refusal
of production or interrupt-exclusion promotion. They use no ROM-derived bytes or
native execution. Lua callback/finalization behavior remains source-reviewed until
the new collector is independently reviewed and run; no existing Lua interpreter
was available for a mocked runtime check and no software was installed.

## 2026-10-03 pilot outcome — preserved scope refusal

After the prepared-source checkpoint above, the authorized v1 pilot completed
with process exit 52, valid streamed JSON and terminal poll 381. The host refused
its declared unsupported early-interrupt sequence: the single pre-effect entry
was at poll 374 and eight balanced IRQ/NMI contexts preceded the unchanged
poll-378 resolver. The first refusal was IRQ context 750 at original record 4.
This is a predeclared scope refusal, not observed nesting or a serialization defect.

The 2,261-record, 17,782,665-byte trace remains unchanged under
`private/test_runs/resolver_phase_v1_pilot_20261003_1/`, SHA-256
`910481d4d72949dd1a6c1f7b83d76beb1bc16263d0b2460dd590e1656b58fde4`.
Its frozen source archive, process/launch receipts and host rejection remain
preserved. V1 source/tests are unchanged and the pilot is not accepted v1 evidence.
The separately prepared [v2 protocol](schala_package_resolver_phase_v2.md)
reconciles those early contexts against the accepted historical context trace
before reusing unchanged v1 validation for the selected resolver and following pair.
