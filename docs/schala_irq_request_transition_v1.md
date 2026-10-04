# IRQ request transitions and CPU acceptance gates v1

Evidence level: `source-conditional-host-model`. This is a separately versioned
composition of the accepted resolver-phase v3 observation with pinned Mesen
source semantics. It does not execute a helper or establish a game deadline.
The [metadata](../references/schala_irq_request_transition_v1.json) retains
`game_deadline_certified=false`, `cpu_acceptance_deadline_certified=false`,
`handler_entry_proved=false` and `production_approval=false`.

## What is now reproducible

The pure register core models one invocation in source order: consume the
pending count; set the flag or set/clear the CPU's PPU-source bit; update H/V
counters; then compare timers and arm a new request. It preserves uint8 pending
counts, uint16 counter wrap, the horizontal H6 three-tick exception, same-value
assignments, timer writes and TIMEUP acknowledgment. Register enables and the
cached combined enable remain separate fields. A changed auto-joypad-enable
write refuses because its callback effects are outside the core.

The bounded Exec projection advances two clocks, processes a scheduled event,
then selects the PPU or counter phase using the **current H after the event
returns**. The real DRAM-refresh event recursively executes twenty such steps.
HDMA begin sets pending flags; it does not execute the transfer at that event.
The projection stops before line 225/VBlank and excludes DMA bus effects and
unclosed callbacks. A separate CPU model represents sampling and post-op
selection, without pretending to execute interrupt frames or vectors.

The auditor pins the complete accepted v3 reference, checks both equal typed
resolver-entry projections, verifies fourteen exact-revision Mesen files and
their Git blob identities, and records the eight original model/test files.
It reads no ROM, SRAM, state or raw game trace. All Mesen files were freshly
downloaded at revision `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1` and checked
against existing local bytes where available and the pinned upstream tree.
The [source manifest](../references/mesen_irq_transition_sources_v1.json)
contains URLs, sizes and hashes, not redistributed source bodies or game data.
Hashes pin the reviewed bytes; they do not derive their semantics automatically.

## Conditional timing result

The reused entry is master clock 2,155,080,050, PPU line 119/H754, internal
H186/V119, vertical-only timer 211, pending count 0, flag/level false, CPU current
and previous IRQ source 0. Eight HDMA channels are enabled and unfinished.
The cached combined enable is derived under the explicit valid-source-state
premise. It is not a newly observed hidden field. The unused auto-joy core field
is likewise not asserted observed; this scheduler performs no NMITIMEN write.

| Conditional scenario | Timer match/arm | Flag set | PPU CPU-source asserted |
|---|---:|---:|---:|
| Minimum 1360-clock line comparison | +124372 | +124376 | +124380 |
| Ordinary 1364-clock lines 119..211 | +124740 | +124744 | +124748 |

These are offsets from the observed entry **inside the stated host model**.
The all-1360 run is an abstract shortened comparison, not a legal raster for
this interval. The pinned PPU uses 1364 here; its short line 240 is not reached.

The lower-offset implication requires all of the following: the exact initial
state, unchanged timer/enables, no earlier pending source, a valid raster and
cache with zero extra lines, no reset/load/clock replacement, no acknowledgment,
no additional IRQ source, and no counter-changing callback reentry or mutation
beyond the reviewed DRAM refresh. Omitted renderer, control, SPC, debugger,
memory-handler and coprocessor calls must satisfy those premises too.

Under those hypotheses, V advances once per line at H6. DRAM recursion stays
between H532..538 and H572..578 and cannot duplicate H6/H10/H14. Thus the
minimum match offset is `(211-119)*1360-754+6`; flag and source follow four and
eight clocks later. This is a conditional implication, not closure of the
whole upstream program or proof that a future inserted helper satisfies it.
The theorem entry requires the exact modeled v3 seed, creates the fixed event
cursor itself and accepts no callback script. `game_deadline()` always refuses.

## Counterexamples that prevent stronger claims

- Refresh at H538 omits that counter invocation and duplicates H578. Both
  the naive endpoint and the recursive result have H-counter 186 at H754;
  endpoint equality conceals the intervening order. All four even refresh
  phases are exercised. A horizontal match near refresh can set the flag
  and assert the source on the same clock, despite distinct method calls.
- Pending 1 with a false flag clears the source at the next tick. Pending 1
  with a true flag asserts at +4; pending 2/false gives flag+4/source+8.
  The hostile uint8 maximum 255 is retained and gives source+1020 in the
  selected fixture. No reachability claim is made for every serialized state.
- A synthetic six-clock callback after every selected line boundary duplicates
  H6 and reaches V211 at PPU line 165, source+62004. A synthetic ten-clock
  callback at line 211 duplicates H10: flag and source both occur at +124744.
  These are explicit adversarial scripts, **not captured native callbacks**.
  Their outputs state that the ordinary callback hypothesis does not apply.
- DMA/HDMA bus effects cannot be dismissed as extra elapsed time. The pinned
  memory manager permits source reads with TIMEUP side effects and reverse
  writes to `$4200/$4207-$420A`. Fixed-register assumptions must cover CPU,
  DMA/HDMA, debugger, external and state-load routes. A no-CPU-store observation
  alone is insufficient. The current model excludes those bus effects rather
  than manufacturing their absence.

The underlying source anchors are the
[counter body](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/InternalRegisters.h#L81-L162),
[Exec/event order](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp#L206-L275),
[DMA read/write routes](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp#L293-L388),
and [line-boundary body](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L395-L511).
The metadata also hashes the exact cited line spans.

## CPU acceptance is a separate boundary

Pending DMA service precedes signal sampling. The CPU then samples the current
source and I bit unless the DMA result locks that sample. Memory/bus clocks
follow. After the opcode, the interrupt check prioritizes pending NMI, otherwise
uses the previous IRQ sample without rereading current I or source. A sampled
IRQ can survive a later SEI or source-clearing read. Clearing the PPU bit leaves
other source bits intact. These decisions follow the pinned
[CPU cycle/check](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L29-L130)
and [sampler](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L315-L367).

WAI's pre-idle wake snapshot, masked wake without IRQ selection, the STP
transition instruction and subsequent stopped calls are distinguished. Unknown
DMA results or callback effects refuse. WAI also requires an explicit stable
signal premise during its omitted idle clocks. No selection clock, frame,
vector completion, handler entry or helper-preemption claim is produced.

## Validation, review and reproduction

The final focused suite passes 81 tests. It includes 16,384 pending/flag/source/
enable/cache/level combinations, 65,536 CPU status/source pairs, every timer-write
byte, every NMI counter byte, source-mask preservation and malformed-input
refusal. Those are declared finite domains, not an exhaustive emulator proof.
An independent native peer also checked 12,000 deterministic hostile core cases
against a separately written imperative interpretation, without a mismatch.

Independent review found four missing Exec guards, all corrected with regression
tests: inconsistent initial event phases, budget overruns inside recursive
refresh, reuse after a refused boundary and uint64 clock wrap. Unknown premises
refuse; a failed instance cannot resume or emit a success summary. The revised
model and exact metadata receive separate root and peer reproductions. Earlier
peer output is preserved as belonging to its earlier source generation.

Grok reviewed the source packet in the existing saved project session and
contributed the H10 counterexample. Its whole-program closure objection is
retained as a limit; agreement or a premise boolean does not close that gap.
See the separate [review disposition](external_review_irq_transition_2026_10_03.md).
The accepted v3 native pair, rejected pilots, older models and original review
drafts remain unchanged. No native matrix was rerun for this checkpoint.

```powershell
python -B -m unittest discover -s tests -p 'test*schala_irq*v1.py'
python -B tools/audit_schala_irq_request_transition_v1.py --output private/test_runs/NEW_irq_request_v1.json
```

Reproduction requires the named Mesen files at the manifest's private local
paths, recoverable from its exact upstream URLs; verify all supplied hashes.
The output parent directory must exist. The auditor refuses to overwrite an
existing output. Compare the resulting complete bytes with the public reference.
No private game input is needed. Final metadata SHA-256:
`846a54df9c490cee263bb86cf1b351683262562915eaecb148e3c182bd1686a7`.

The next gate is a bounded source and observation design for DMA/HDMA bus-side
effects and omitted callback closure, using the accepted phase snapshot to
identify what is known and what would require a new observation. Do not compare
this conditional IRQ offset with the older helper envelope as if their premises
were already jointly proved. Wrapper cost, physical game-stack ownership,
interrupt policy, the pre-effect refusal lifecycle and later completion remain
separate obligations. `BA-NATIVE-INTEGRATION-DESIGN` stays open; all production
hooks, allocations and high selectors remain unapproved.
