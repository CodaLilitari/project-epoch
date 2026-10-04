# DMA IRQ domains and callback inventory v1

Date: 2026-10-03 (America/New_York). Evidence level:
**reused observation plus source-conditional address model**. This is an
additive continuation of the accepted resolver-phase v3 and IRQ-transition
v1 packets. No native matrix was repeated and no game image was changed.

The accepted resolver-entry channels all use forward, indirect HDMA with
both source banks `$7E`. Under explicit mapping and configuration-lifetime
hypotheses, every modeled A-bus table/payload read stays in that bank despite
16-bit pointer wrap or unknown indirect table values. B-bus writes stay in
`$21xx`. This excludes **direct** TIMEUP acknowledgment and IRQ-enable/timer
writes for those conditional domains. It does not close memory handlers,
debugger hooks, PPU rendering, external mutations, or a helper deadline.

## Original artifacts and reproduction

- [Pure domain model](../tools/schala_dma_irq_domains_v1.py) and
  [model tests](../tests/test_schala_dma_irq_domains_v1.py).
- [Composition auditor](../tools/audit_schala_dma_irq_closure_v1.py) and
  [auditor tests](../tests/test_audit_schala_dma_irq_closure_v1.py).
- [Exact upstream identities](../references/mesen_dma_irq_closure_sources_v1.json):
  42 files at Mesen revision `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`.
- [Callback fact inventory](../references/schala_dma_callback_facts_v1.json):
  24 qualified facts, with 70 exact raw-byte source spans.
- [Composed metadata](../references/schala_dma_irq_closure_v1.json):
  77,504 bytes, SHA-256
  `0b99435c6b6209188284ebfc6f5db77f2726db0ec501e81872346286e146b50e`.

Run from the repository root with the existing private accepted evidence:

```powershell
python -B tools/audit_schala_dma_irq_closure_v1.py --output private/test_runs/dma_irq_closure_v1_reproduced.json
python -B -m unittest discover -s tests -p test_schala_dma_irq_domains_v1.py
python -B -m unittest discover -s tests -p test_audit_schala_dma_irq_closure_v1.py
```

The pure model tests need no ROM, emulator, save or trace. The composition
auditor requires the ignored accepted v3 evidence, including the frozen
auditor's transitive inputs; a public checkout alone cannot reproduce that
observation. Fetch upstream sources only from their exact manifest URLs,
then check size, SHA-256 and Git blob SHA-1. Hash agreement pins source bytes;
it does not mechanically establish the semantic interpretation in the facts.

## Observation reused, without extending its scope

The frozen v3 auditor was rerun offline and reproduced its accepted reference
byte for byte. Both 17,946,524-byte traces retain SHA-256
`cbcfee04c0eab0381d77392e43baf8cc5ed3c62b8a22ac533bf2d263424bd619`.
The new projection emits hardware configuration, counts and identities only.
No table payload, game array, ROM, SRAM or raw trace is published.

| Observed interval | Selected records | Master clocks | Watched hardware events |
| --- | ---: | ---: | ---: |
| Resolver entry to tail | 81 | 4,244 | 0 |
| Resolver entry through following IRQ entry | 682 | 124,904 | 0 |

Entry is at full serialized master clock 2,155,080,050, PPU line 119/H754.
All eight channels are enabled, unfinished, indirect and forward; manual DMA
is inactive. Selected register-controlled configuration fields stay equal
through the short resolver interval. Internal counters and payload pointers
do change. Equal selected snapshots alone are not a lifetime certificate.

The first later watched write is `$4200=$81` at offset +125,226. Channel 7 is
then reprogrammed. The complete window contains 280 watched hardware writes,
so the entry configuration must not be extended over the whole window.

The collector covers mapped-bank `$4200`, `$4207-$420D` and `$4300-$437F`
read/write callbacks, including DMA operation families. It omits `$4211`
and PPU B-bus traffic. No payload values, controller dynamic types or autojoy
scheduler fields were captured. Hidden timing caches remain source-conditional
inferences from the older crossing evidence, not directly observed fields.
The original-game interval is not a counterfactual run of the proposed helper.

## Domain model

`ChannelConfig` uses exact uint8/uint16/bool fields. Unknown mapping,
configuration, external pointer/lifecycle, nested-service or reset/load
hypotheses fail closed. Passing `True` does not certify any hypothesis.

The model retains the source's promoted B-bus addition, all eight offset
patterns, manual zero-size meaning 65,536 bytes, fixed/increment/decrement
addressing, and wrap within the same bank. HDMA table and indirect-pointer
reads always remain A-bus reads, even for reverse payload transfer. The
counter read still occurs when its value will be discarded without a reload.
Direct table movement is at most payload width plus one byte per service;
indirect table movement is at most three. Terminal initialization/reload
one-byte cases remain inside the conservative union.

For a single existing indirect service, the current payload pointer is known.
Initialization or a possible later reload allows any uint16 payload pointer.
The union intentionally includes infeasible paths and some calls suppressed
by the WRAM/`$2180` exception. A separate exact logical-copy function covers
that exception under a known WRAM-mapping result.

The composed example uses a supplied cap of 65,536 services. This is an
address-set bound, **not** a number of services admitted within a time window.
All eight conditional domains exclude direct IRQ-register candidates. Two
synthetic counterexamples preserve the importance of the hypotheses: moving
the table read to `$00:4211` creates an acknowledgment candidate even when no
payload transfers; reverse manual DMA in bank zero with size zero can reach
all five modeled IRQ-control/timer write registers. Neither is observed game
behavior or proof that the handler actually completes its side effect.

## Rendering and callback findings

Channel 5's possible B ports include `$2133` (SETINI). The source writes raw
rendering flags and may convert image buffers, but does not refresh the
VBlank/NMI/frame-end caches in that write. Power-on and line-zero completion
refresh those caches. The live interlace-dependent short-line exception is
line 240, outside lines 119-211. Thus, with valid fixed caches and no external
refresh/reset/load, SETINI does not directly change the cache inputs or the
1,364-clock line predicate within this interval. Full IRQ/NMI schedule
preservation still needs the other callback and mutation hypotheses.
See [the pinned PPU source](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L395-L561)
and facts CC17-CC20. Rendering equivalence remains unproved.

`Exec -> ProcessPpuCycle` invokes debugger dispatch. Rendering occurs inside
end-of-scanline processing before H resets to zero; autojoy and SPC update
follow that reset. With cached VBlank start 225, `UpdateSpcState` makes no SPC
call on lines 119-211. The exact ordinary controller bodies and the exact
SNES debugger's reviewed inert branches have conditional source closures;
runtime object binding and defined object/library/synchronization behavior
remain required. Other controller subclasses are not covered by that result.

HDMA event functions set pending flags; service occurs in CPU-cycle processing
before signal sampling and at the identified DMA-owned service sites. Service
recursion is distinct from recursion into an unfinished `Exec` phase.
Sequential service can end at H6/H10 without duplicating a waiting outer
counter phase. The debugger PPU call follows phase selection; coprocessor
synchronization follows both phase branches. Reentry there alone does not
repeat the outer counter branch, although an unfinished ancestor event can
still matter. The older synthetic counterexamples remain valid in their
declared callback positions; they are not newly observed callbacks.

Under concretely closed/absent callback branches and excluded bus/host
mutation, DRAM is the remaining reviewed direct nested-`Exec` route. It
returns at H572-578 under ordinary even phase. This conditional implication
does not establish that the game satisfies those antecedents.

## Validation and review

The root run passes **293 tests**: 34 new tests, all 81 preserved IRQ-transition
tests and all 178 preserved phase tests. The new model's independently written
mutable scalar projection checks 1,792 HDMA scenarios, six services each,
across modes, direction, initialization, direct/indirect addressing, counter
boundaries and changing table bytes. All 1,024 B-port addition cases are
checked. Auditor mutation tests cover missing/duplicated phases, types,
configuration changes, watched writes, source omissions/duplication, and a
file changing during computation.

Three native collaborators separately handled model construction, trace reuse
and callback source analysis. Cross-review found and corrected early auditor
identity-capture ordering, and incomplete controller, memory-write and
debugger-call evidence spans. Source identities are captured before use and
rechecked at the end; each trace is hashed and parsed from one byte buffer.
Exact pinned manifests reject omitted or substituted source/fact inventories.
Root independently verified all 42 files against the earlier exact Git tree
and freshly fetched eight primary-source files. No new external-provider
dispatch or native emulator run was used for this checkpoint.

Private review receipts remain under `private/reviews/20261003d/`, including
the original findings and superseded root output. Reproduction of the final
reference by the independent peer is recorded there separately. These are
review and file-consistency receipts, not authenticated execution certificates.

## Next bounded gate

Continue at **DMA-CALLBACK-BINDING-DESIGN**, within the still-open
`BA-NATIVE-INTEGRATION-DESIGN` gate. Inventory which accepted launch/state
artifacts can bind actual memory mappings, coprocessor presence, debugger
guards/script targets and controller types. Existing snapshots do not contain
all of those fields. Specify only the remaining read-only observations after
that inventory; do not rerun accepted matrices merely to reconstruct context.

Active debugger notifications/scripts/pause mutations, virtual coprocessor
targets, nonordinary controller targets, SPC/DSP hooks, outer DMA callbacks,
reset/load and external cache-refresh calls remain explicit frontiers. DMA
input lifetime and configuration stability during a future helper need their
own certificate. Wrapper cost, physical game stack, interrupt policy and
pre-effect refusal versus later completion remain separate obligations.
No game deadline, helper admission, production selector, allocation or hook
is approved by this packet.
