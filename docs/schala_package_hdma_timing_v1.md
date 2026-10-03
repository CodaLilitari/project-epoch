# Conditional helper / HDMA timing envelope v1

Prepared 2026-10-03. Evidence level: **conditional static model**. This is an
additive timing proposal for the unchanged immutable-v3 helper fixture. It is
not an admission deadline, native helper execution, memory-isolation proof,
rendering-equivalence proof, or production approval. Preserve the earlier
helper timing source/reference and the rejected phase-v1 pilot unchanged.

Under the premises below, the generic eight-channel HDMA service costs at most
**472 master clocks** before separately charged refresh. Initialization costs
at most **216**. Composing those costs with the published helper's **65,046**
base clocks gives a **144,088-clock** coarse bound. It refines to **106,689**
when at most one initialization is possible, and **106,342** at the accepted
resolver phase when the declared line/frame minima exclude initialization.
These numbers do not establish that running the helper at that phase is safe.

## Exact prerequisites and validation scope

The collector reads source files and public metadata only. It does not import
the earlier timing collector, read any ROM or raw trace, or run an emulator.

| Prerequisite | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/research_helper_timing_envelope_v1.py` | 7,962 | `c8f160d8eb57bd4b22f10954bc6cbda231802272df1f55344345a2c30158733a` |
| `references/schala_package_helper_timing_envelope_v1.json` | 5,974 | `058d9f1ac1a2bb1c9a2f7ea375e9f507d3e1536e475eaf1316f1afd5dad0d8db` |
| `references/schala_package_resolver_phase_v2.json` | 53,831 | `8e3898c7886a88e166bf5fd13f69ac37b44b59bd202d5780c0a8ae98ae30c120` |

The baseline's eight declared source identities are rechecked, together with
all twelve directly pinned prerequisites, before and after collection. This
reuses the published baseline's instruction inventory; it does not regenerate
its collector, revalidate its original cartridge bytes, or rerun the accepted
phase auditor. The new source and test identities are included in the output.
Source spans are hashed as exact bytes including their existing line endings;
their semantic interpretations remain reviewer-derived.

The accepted compact phase pair supplies matching resolver-entry observations
at poll 378, scanline 119, horizontal clock 754. All eight HDMA channels are
enabled and unfinished. Manual-active channels are empty; DMA pending, start
delay, need-to-process, HDMA pending and initialization pending are false. The
compact reference omits transfer modes, destinations and table payloads. This
model does not infer them. Entry state is an observation, not a certificate that
no later writer, handler or HDMA effect can invalidate the premises.

## Source provenance and finite service accounting

The pinned Mesen commit is
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. Complete local file identities and
25 inclusive line spans are emitted by the collector. Corresponding source:

- [SnesDmaController.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp):
  lines 8-12 define mode byte counts; 46-66 charge one data byte; 104-172
  initialize channels; 174-204 transfer payloads; 206-218 synchronize; 230-335
  service HDMA counters/reloads; 347-405 dispatch pending work; 408-436 handle
  CPU DMA requests.
- [SnesMemoryManager.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp):
  lines 158-219 advance clocks and charge refresh; 224-264 request line events
  and frame-zero initialization; 293-328 and 360-388 charge DMA reads/writes.
- [SnesPpu.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp):
  lines 395-398 set line timing; 459-486 advance lines/frame zero; 538-560
  update frame thresholds; 2253-2257 serialize the internal scanline.
- [SnesCpu.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp):
  lines 88-96, 119-130 and 143-157 establish idle speed and pending-service
  placement relative to CPU speed selection.
- [RegisterHandlerB.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/RegisterHandlerB.cpp):
  lines 61-88 distinguish PPU destinations from the WRAM port.
- [InternalRegisters.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/InternalRegisters.h):
  lines 27-34, 79-102 and 104-162 show separate IRQ counters, comparison and
  update. [InternalRegisters.cpp](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/InternalRegisters.cpp)
  lines 409-410 serialize those counters.

A normal data byte costs eight base clocks: four for its read and four for
its write. The WRAM-port special case still costs eight. Each counter or
indirect-table byte similarly costs four read clocks plus four explicit clocks.
For each enabled, unfinished channel, payload length is at most four bytes,
the counter-table read costs one byte even when discarded, and an indirect
reload costs at most two bytes. Thus one channel costs at most 56 clocks.
Finished/disabled channels incur no channel cost. Counter decrement is modulo
256; low seven bits govern reload. A last-channel zero reload uses only one
pointer byte, which cannot increase the maximum.

The model enumerates 131,072 source-equivalence cases over every current
counter, mode and relevant Boolean alternative. Per-mode maxima are
`[32, 40, 40, 56, 56, 56, 40, 56]`. Unknown next-counter payloads are reduced
only by their actual zero/nonzero branch predicate. The eight-channel maximum
is `8 * 56 + 8 + 8 + 8 = 472`: eight channels, common service cost, start
alignment and end alignment. Initialization has at most three table bytes
per channel, giving `8 * 24 + 24 = 216`. The 456 alignment cases cover
six/eight-clock helper CPU cycles and attain the conservative 16-clock combined
alignment allowance. Refresh during either service is charged separately.

The private mode-specific refinement is deliberately outside this public
contract. The public cost is valid for any of the eight modes under the
remaining premises; it does not depend on observed table contents.

## Composition, initialization bootstrap and premises

Let `B = 65046`, `R = 40`, `H = 472`, and `I = 216`. Require the pinned normal
event mechanism and **minimum 1,360-clock lines and 262-line frames as explicit
independent premises**. Using a weakened event spacing `D = 1352` accounts for
the less-than-eight-clock phase variation. Each request family obeys
`N <= 1 + ceil(T / D) <= 2 + T / D`. Delayed or coalesced requests cannot
increase this count.

Apply the inequality to **every finite elapsed execution prefix**, with CPU
work at most `B`. Charge a partially started service its entire bound. Then
`T <= B + 2*C + (C/D)*T`. Since `C < D`, the ceiling of
`(B + 2*C)*D/(D-C)` bounds every prefix. This establishes progress under the
premises; it does not presume completion in order to prove completion.

1. Allow initialization as often as every line: `C = R + H + I = 728`.
   The coarse result is 144,088 clocks.
2. Initialization request spacing is at least `262*1360 - 8 = 356312`.
   The strict inequality `144088 < 356312`, with no initially pending
   initialization, permits at most one initialization. Add 216 to `B` and
   use `C = R + H = 512`: the result is 106,689 clocks.
3. At scanline 119 / horizontal clock 754, the declared frame minimum gives
   `(262-119)*1360 - 754 = 193726` clocks to frame zero. The strict inequality
   `144088 < 193726` excludes initialization within this bounded interval.
   With `B = 65046` and `C = 512`, the result is 106,342 clocks.

The arithmetic refuses each initialization refinement when its strict coarse
comparison fails. It also refuses an event duty greater than or equal to its
spacing. A late-frame phase cannot borrow the no-initialization result.

The line/frame premises are **not established merely by nonnegative extra
scanlines**. Cached PPU thresholds may wrap for unbounded settings. The actual
settings, bounds and valid cache recomputation are not bound by the phase
observation. An additive review identified this limit before public freeze;
the private earlier proposal is preserved unchanged. This packet directly
requires the timing minima instead of certifying those missing configuration
conditions.

Further premises are the unchanged baseline helper's native CPU/SP,
immutable code/registry and six/eight-clock access assumptions; no extra
wrapper/trampoline cost; no interrupt handler, new manual-DMA request,
coprocessor stall, reset, stop, external CPU mutation or memory corruption;
and no HDMA corruption of live helper counters, frames, registry or code.
Normal internal HDMA pointers/counters may evolve and payload values are
unconstrained. The observed empty pending state alone does not prove these
future interval conditions. A future writer/handler and memory contract must
establish them.

## Limits relevant to integration

The immutable-v3 fixture has its own target lists and loop inventory. The
general 32-target helper has base cost 235,926, a separate contract. Even its
no-initialization arithmetic would be 381,377; the bootstrap does not permit
that refinement at this phase. Do not apply the fixed-fixture result to
arbitrary future bindings. The scope begins with the original entry JML and
ends with the helper's final JML; it excludes the tail instruction and any
new admission machinery.

Internal IRQ `_hCounter` / `_vCounter` and overclock settings were not captured
by the phase observer. PPU scanline 119 and vertical timer 211 therefore do
not certify the next IRQ request boundary. A historical handler-entry gap
also occurs after interrupt recognition. This packet certifies no deadline,
interrupt exclusion or spare timing margin.

This is one resolver-phase model. A phase check at an earlier pre-effect
boundary does not certify the later resolver phase after intervening work and
interrupts. It cannot authorize late rejection after MP charging or effect
preparation; admission, fallback/defer behavior and cleanup remain separate
lifecycle obligations.

Forward HDMA reads can expose helper-written stack/publication bytes to PPU
registers even when destinations avoid WRAM. A finite cost bound does not
prove source-read isolation or rendering equivalence. Unknown payloads can
also change SETINI when that destination is configured; initial PPU mode flags
are not assumed constant. The compact reference does not certify destinations,
source lifetimes or the complete game interrupt tree. These remain integration
obligations, separate from the arithmetic result.

## Reproduction and review state

Run from the repository root with the pinned local source cache available:

```powershell
python -B -m unittest discover -s tests -p test_research_helper_hdma_envelope_v1.py -v
python -B tools/research_helper_hdma_envelope_v1.py
```

The CLI emits original metadata as binary UTF-8/LF JSON with one trailing
newline. Use a binary subprocess capture when saving it; shell newline
conversion must not be called byte-exact reproduction. No reference is emitted
automatically. The source hashes both its own source and tests before/after.

Thirteen original tests cover skipped-transfer reads, counter wrap/repeat,
the final zero reload, finished channels, exact integer rounding, saturated
duty refusal, late-phase and larger-contract bootstrap refusal, wrong types,
pending/mismatched observation refusal, same-size source mutation, pure import
and output line endings. The actual collector additionally performs the finite
cost/alignment enumeration and prerequisite checks.

At preparation this packet awaits root acceptance and the public freeze review.
The private predecessor has independent source/arithmetic review, including
4,194,304 independently encoded counter/payload cases and integer inequality
challenges. That review is not a native scheduling census. Public acceptance,
reference identity and publication should be recorded externally by root
without changing these frozen source bytes.
