# Package-helper interrupt strategy review

Authored 2026-10-03 from canonical source and retained September 8 evidence.
Status: **design review; no new runtime result or integration approval**.

A first, explicitly restricted integration experiment need not establish a
universal scene/NMI contract. It does need a proved reason that the omitted
paths cannot affect that experiment. The strongest next candidates are an
entry-specific interrupt contract and a bounded execution window with
interrupts left enabled. **Borrowing the normal-NMI busy flag is unsuitable.**
The source gives a direct counterexample to treating it as a main-thread lock,
and taking the busy return deliberately changes frame service behavior.

This review reads the [integration design](schala_package_resolver_integration_design_v0.md),
[normal-NMI proof](schala_package_normal_nmi_v1.md),
[IRQ memory contract](schala_package_irq_memory_contract_v2.md),
[IRQ DMA7 contract](schala_package_irq_dma7_contract_v3.md),
[retained context observation](schala_package_resolver_context_v1.md), and
canonical instructions. It changes none of those evidence packets.

The busy byte is physical `$00007F`, not storage owned by the package helper.
The exact relevant sequence is:

| Site | Effect | Consequence for a borrowed guard |
| --- | --- | --- |
| `$D1E78A` | Long store `$00420C=0` | NMI disables HDMA before testing busy. |
| `$D1E78E` | Read `$004210` | NMI status is acknowledged before the test. |
| `$D1E794` | Long store `$004200=$A1` | NMI rewrites interrupt/auto-joypad configuration before the test. |
| `$D1E798-$D1E79C` | Read DP `$7F`; nonzero jumps to `$D1E891` | The 13-byte busy route preserves CPU context, but skips the body. |
| `$D1E79F` / `$D1E88B` | Increment busy / store zero | Full normal NMI owns its busy interval. |
| `$D1FEA4` / `$D1FEEA` | IRQ increments busy / unconditionally clears it | An IRQ entering with a helper-borrowed value 1 changes it to 2 and then 0. |

After that IRQ, a later NMI may enter the full body while the helper still
believes it is guarded. Saving and restoring the old busy value only in the
helper does not repair this intervening exposure. Making the IRQ preserve a
borrowed count would require a separately reviewed interrupt-handler change.
It is not the existing protocol. The IRQ itself disables vertical IRQ via
`$4200=$81` at `$D1FEAE`, disables HDMA, performs raster/display work, and
restores its CPU frame; its busy clear is intentional in that protocol.

`SEI` does not dismiss an already sampled pending IRQ. The pinned Mesen
pipeline checks the previous IRQ sample after the instruction, so the
[accepted context report's pending-IRQ correction](schala_package_resolver_context_v1.md#review-correction-a-pending-irq-can-outlive-sei)
still applies. It also leaves NMI enabled. A hardware-register masking scheme
would need exact pending-edge, acknowledgement, re-enable, and lost-service
semantics; no such scheme is justified here. Leading zero-busy windows before
`$D1E79F`/`$D1FEA4` and trailing windows after `$D1E88B`/`$D1FEEA` remain real
obligations. Neither balanced CPU frames nor arbitrary injected nesting
establishes their hardware timing bound.

The busy route also cannot be called transparent deferral. It omits the
normal mode services, scene progress, controller service and frame
handshakes. Mode one ordinarily restores configured HDMA at
`$CD08FB-$CD08FE`; the busy route skips that restoration. The full NMI clears
`$7ECA20` at `$D1E88D`, while the pause/frame service at `$CD3E58` waits for
that clear. Deliberately skipping service can therefore alter graphics and
progress even when every saved CPU register is restored. A short measured
helper duration does not prove that this lost work is harmless.

Other existing flags offer narrower predicates, not interchangeable locks:

| Candidate | What the canonical code actually permits |
| --- | --- |
| `$7ECD02` pause | Mode one uploads/handles graphics before its pause checks. The flag also participates in input, audio and frame-wait behavior. Forcing it is a game-state change. |
| `$7EA013` animation activity | The caller increments it at `$C140A6`; frame code uses it to enable animation work. It does not freeze the reader. |
| `$7ECCEA` / `$7E5D9B` scene state | `$CD1609/$CD160C` returns if CCEA is nonzero; otherwise `$CD160E/$CD1611` returns if 5D9B is zero. These are useful natural exclusion conditions. Forcing either value would interfere with scene ownership/completion. |

The accepted primary resolver entry already observes mode `$007E=1`, busy
zero, `$CD02=0`, and `$5D9B=0`. Thus there is a concrete, potentially much
smaller **conditional** proof: establish that the helper and every earlier
service on this mode-one interrupt route preserve the inactive scene
predicate until `$CD160E`. Then all scene command handlers are unreachable
during that interval. This would avoid needing their complete legal domains
for that specific integration context. The entry snapshot alone does not
establish this: graphics, transition and frame services run before the scene
gate, and their writes/aliases must be checked. Mode selection, reset/alternate
handlers, stack ownership, non-scene services and DMA/HDMA effects remain
separate obligations. The existing 35-byte IRQ CPU closure and its 298-byte
ordinary-WRAM write footprint can be reused within their stated premises;
neither proves full-NMI safety or arbitrary effective memory aliases.

There is also enough measured timing margin to test whether this first
diagnostic can avoid interrupt entry altogether. The unchanged accepted
primary trace gives the following zero-based rows. Times use the full
`memoryManager.masterClock`, not the generic low-32-bit field.

| Row | Event | Clock | Delta from resolver entry |
| ---: | --- | ---: | ---: |
| 4227 | `$C14612`, scanline 119, hClock 754 | 2155080050 | 0 |
| 4315 | Pre-tail `$C1467F` | 2155084294 | 4,244 |
| 4316 | Common loader `$C14833` | 2155084312 | 4,262 |
| 4317 | Next battle IRQ entry, scanline 211 | 2155204954 | 124,904 |
| 4319 | Next normal NMI entry, scanline 225 | 2155224038 | 143,988 |

The separate immutable-ROM helper calibration sampled 54,108 master clocks
for its longest group at entry SP `$06D8`. Subtracting that from the next
observed IRQ entry leaves 70,796 clocks. This is a prioritization clue,
**not a worst-case execution bound or a certified deadline**. The calibration
uses its own fixture, inputs and placement. Incoming status, trampoline
overhead, memory wait states, DMA/HDMA stalls and the exact installed binding
must be accounted for. Handler-entry snapshots occur after interrupt
recognition/hardware-frame work. Adding helper time can change later game
execution and cannot be evaluated by blindly shifting the old trace.

The smallest falsifiable next experiment is a **single-entry timing and
scene-gate audit**, before a high-selector hook:

1. Fix the existing primary checkpoint, config donor `$08`, branch `$0000`,
   exact candidate helper and one immutable diagnostic binding. Keep the
   alternate branch a separately numbered extension. Source-check whether
   mode-one services preceding `$CD160E` can change the observed inactive
   scene predicate; stop at the first unresolved producer instead of opening
   another universal command census.
2. Prepare a separately versioned, read-only observer for the candidate
   pre-effect boundary `$C1BBD4`, resolver entry `$C14612`, common-loader
   entry `$C14833`, and surrounding interrupt boundaries. Record exact
   installed vectors, CPU/stack context, full clocks/raster, interrupt-control
   and timer state, pending interrupt state where source-backed observation
   supports it, DMA/HDMA configuration, and actual scene-gate reads/writes.
   Use non-mutating emulator inspection; do not introduce CPU reads of
   acknowledgement/latch registers. Missing required state is an incomplete
   experiment. The already prepared
   [normal-NMI stack observer](normal_nmi_stack_observation_v1.md) can supply
   its declared post-publication intervals, but is not a resolver-window or
   pending-interrupt probe and should retain its original scope.
3. Derive a conservative execution budget for that exact helper path,
   including entry/exit and asynchronous bus stalls, and compare it against
   the earliest possible IRQ/NMI recognition, including any pending source.
   A sampled duration is insufficient. Reject the proposed window if its
   lower-bound margin is not positive, if the gate predicate can change,
   or if a required producer/state cannot be bounded. The observer reports
   failure; it does not alter the running action to manufacture a pass.
4. Only after that review, design a guarded private insertion experiment
   with full WRAM/stack/publication reconciliation and normal action
   completion. Interrupts remain enabled. Any interrupt entering the claimed
   protected interval falsifies that experiment's exclusion premise. A
   successful result remains specific to its entry/phase contract; it does
   not license arbitrary battle entry times or production selectors.

A practical admission policy cannot simply reject late at `$C14612` when
the phase is wrong. Effects and participant MP preparation occur earlier
through `$C1BBD4`. The natural `$C1BB8B` failure context is different, and
`$C1BDB3` is a shared finalizer, not a refund API. A usable later design must
either prove the window for every admitted pre-effect transaction or define
a safe wait/admission point before effects. Pumping frames to wait changes
game state and requires its own contract. Terminal-only `$00` still does
not supply `$9876` completion or the distinct `$5D9B` lifetime. See the
[cancellation contract](schala_package_cancellation_contract_v1.md).

This narrows the engineering target: test a concrete timing/context
restriction first, and close only interrupt paths that remain reachable
under it. If that restriction fails, a mode-one, naturally inactive-scene
contract is the next bounded alternative. Moving work into the NMI or
changing interrupt handlers would introduce a new scheduling/ownership
design and should not be disguised as reuse of the busy fast path.

Provenance and reproduction: canonical US Rev0 is 4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The navigation source is the preserved
[upstream disassembly at eeae27acdb6565e96d1d796a3d60792c250c0aa1](https://github.com/dscotton/ct_disassembly/tree/eeae27acdb6565e96d1d796a3d60792c250c0aa1).
Canonical bytes decide the semantics. This review identifies an unsupported
prospective lock interpretation; it does not claim a newly discovered error
in that upstream annotation or change an accepted map.

| Canonical half-open CPU span | Bytes | SHA-256 |
| --- | ---: | --- |
| `$D1E77C-$D1E7A1`, NMI prefix | 37 | `de08d9b004ef402364abff51fb7b86c615d28f10be2fc12b52623211dcb4eb21` |
| `$D1E87A-$D1E899`, NMI release | 31 | `3506d00fa4aa18ee5c9c49efc33ee2aa5253a0571cf0bbf77270eb176e5237dd` |
| `$D1FE97-$D1FEF4`, battle IRQ | 93 | `cc06d1d9a49444be184db23bce01e1552c68497b288589d9f3d6475308942633` |
| `$CD1609-$CD1653`, scene gate/body before RTS | 74 | `56d8b5445e65bb11bb091dd4e85dd696f980dad58699e56c1d681a91e468c335` |

Reproduce these hashes without emission by slicing the pinned ROM at
`CPU_address - 0xC00000` with the stated half-open endpoints. Both
`private/test_runs/resolver_context_20260908_final1/trace.json` and `final2`
copies were rehashed in this review: 10,811,008 bytes each, SHA-256
`6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679`.
Read their JSON `records` at the row indices above and subtract the full
clock fields. The retained calibration reference is
`references/schala_package_helper_v4_timing_calibration.json`, 98,917 bytes,
SHA-256 `8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb`.
These identities were checked read-only; no historical collector was
regenerated. No emulator, hook, ROM write, catalog change, or new native
test was performed for this memo.

## Additive finite timing model, 2026-10-03

The separate original [calculation source](../tools/research_helper_timing_envelope_v1.py)
now provides a reviewed conditional upper envelope, rather than relying only
on the old calibration's sampled duration. Its
[metadata](../references/schala_package_helper_timing_envelope_v1.json)
is reproducible with:

```powershell
python -B tools/research_helper_timing_envelope_v1.py
```

This read-only model requires the original package test cartridge already
reproduced by [its guarded builder](original_snes_package_cartridge_v1.md),
plus the named pinned emulator sources. It emits no image or patch. It checks
the unchanged helper source, complete original cartridge, assembled 577-byte
helper and immutable registry counts. Eight source identities are pinned.
The cost interpretation is an explicitly reviewed model; hashes do not
automatically derive instruction semantics.

The immutable v3 fixture has target-list counts 2/2/1/1 and twelve unbound
rows. The model charges every nonloop block once, even mutually exclusive
exits; 32 complete preflight bodies; at most 64 target-search iterations;
16 full publication bodies; and two complete 16-iteration CountBits calls.
Its 280 expanded instruction rows encode 577 bytes. Independent review
matched every instruction and operand to those assembled bytes and checked
the four backward control edges. The bound includes the original entry JML
and final helper JML, stopping before the tail's first opcode.

ROM banks `$41/$42/$43` and all admitted WRAM/stack accesses cost eight
master clocks per byte in the pinned emulator. Definite internal idles cost
six; optional idle/dummy-read slots are charged eight. Data word widths and
taken conditional branches are deliberately overcharged where execution can
be shorter. The base envelope is **65,046 clocks**. DRAM refresh is included
separately: 40 clocks per event, with a deliberately weakened minimum event
spacing of 1,352 clocks, gives
`ceil((65046 + 80) * 1352 / 1312) = 67112` clocks.

That is 57,792 clocks below the historical 124,904-clock IRQ-entry gap,
whose source trace rows and full clocks were independently rechecked.
**This comparison is not an admission deadline.** It excludes DMA/HDMA
service, interrupt execution, memory corruption, and additional admission or
integration instructions. Incoming native M0/X0/D0/DBR7E and the fixed v3
entry SPs `$1FEF/$06D8` are premises. The helper does not disable DMA or
interrupts. The earliest interrupt recognition can precede its handler-entry
snapshot. Those exclusions require proof or a separate bound.

The general helper registry allows 32 targets, which increases the same loose
envelope to **243,202 clocks**. That bound cannot certify the historical gap;
it does not prove every future binding actually takes that long. The smaller
number depends on the exact immutable fixture and must not be generalized.

Two independent public CLI processes emitted identical metadata and retained
the private reviewed proposal's complete numerical results. The original
private prototype's text stdout used Windows CRLF, while its retained JSON
used LF; only parsed equality was claimed for that earlier comparison. The
published source writes explicit UTF-8/LF bytes. The original proposal and
independent review receipt remain unchanged under
`private/test_runs/helper_timing_bound_review_20261003/`.


## Additive resolver-phase result — 2026-10-03

The separate [v2 phase packet](schala_package_resolver_phase_v2.md) now repeats
in two unchanged-game runs. The earlier pre-effect point precedes resolver
entry by four frames and eight complete interrupts. These are individually
reconciled to the accepted historical context trace; they are not ignored.
At resolver entry, no IRQ/NMI or DMA request is pending in the declared
serialized fields, but all eight HDMA channels are enabled and unfinished.
The old no-DMA/HDMA timing premise therefore needs a separate service bound.

The selected PPU position is line119/h754 and the vertical IRQ timer is211.
These values are not sufficient to prove the next IRQ request time. The pinned
`InternalRegisters.h` uses independent `_hCounter` and `_vCounter` in
`ProcessIrqCounters` and `UpdateIrqLevel`; both are serialized by
`InternalRegisters.cpp` but omitted from this observer's 161-field contract.
Relevant overclock settings were also not captured. Preserve the actual
historical gap as an observation and obtain the missing state/source closure
before claiming an admission boundary. DMA source-read aliases and render
effects remain separate from any finite service-cost calculation.
