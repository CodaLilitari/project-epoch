# Canonical battle IRQ: CPU-write and saved-register contract v2

Date: 2026-09-08. Status: complete within the declared scope after root and
independent peer review. Evidence: `verified-static` within the conditional model below.

The normal battle IRQ's ordinary CPU stores and complete block-move
destinations are now derived alongside symbolic register saves and restores.
This closes the earlier typed-stack audit's ordinary CPU-write alias premise
for one explicit helper/caller geometry. It does not establish DMA behavior,
NMI nesting, the lowest safe game stack address, or a production hook.

The new [auditor](../tools/audit_schala_package_irq_memory_contract_v2.py)
preserves the accepted
[IRQ control-flow audit](schala_package_interrupt_closure_v1.md) and its
reference unchanged. It reads the canonical ROM, reproduces that reference,
then runs a separate byte-value/stack interpreter. No ROM, save, state, trace,
patch, catalog, or emulator session is created or changed.

## Results and precise scope

| Check | Result |
| --- | --- |
| Original abstract states visited | 2,244 |
| Canonical instruction starts / width contexts | 401 / 404, matching the prior graph |
| Call edges | The same four near/long edges as the prior graph |
| Ordinary CPU write sites / contexts | 109 / 109 |
| Distinct physical WRAM bytes in those writes | 298 |
| Largest stack depth including native hardware entry | 35 bytes, matching the prior audit |
| Native entry M/X combinations | All four restore symbolic A/B, X, Y, D, DBR and the intact hardware return frame |
| Ordinary CPU-write overlap with the checked stack envelope | Empty |
| Ordinary CPU-write overlap with the checked package fields | Empty |
| New native execution | None |

“Ordinary CPU writes” includes `STA`, `STX`, `STY`, `STZ`, direct-page `INC`,
and every destination byte of each complete `MVN`. Implicit stack writes are
accounted for separately by their actual push widths, live byte extent, and
typed frames. DMA/HDMA bus transactions are not ordinary CPU writes in this
result. A CPU store to a DMA control register remains a control-register
store here; this model does not substitute that store's address for the
transfer's eventual destination.

The result is an overapproximation across data conditions. Every conditional
branch takes both edges; none is pruned from a presumed game variable or
computed flag. Some combinations can therefore be infeasible in a real battle.
Reaching a finite repeated state does not prove that an HBlank polling loop
terminates. No timing result follows.

## Exact caller context and remaining production obligations

The accepted [ordinary resolver observation](schala_package_resolver_observation_v0.md)
and [natural alternate observation](schala_package_resolver_alternate_v1.md)
both enter `$C1:4612` with native M=0/X=0, D=`$0000`, DBR=`$7E`, and
SP=`$06D8`. The two stored near-return words are `$432A` and `$40AF`; the
next byte is the caller's saved direct-page `$A4`. These occupy bank-zero
physical WRAM `$06D9-$06DD`, inclusive.

The candidate four-byte hook span `$C1:4612-$C1:4616` contains the canonical
`LDA $9877` / `ASL A`. A future canonical bypass must replay those operations
and tail-transfer to `$C1:4616`. A successful high package would have to
publish its complete ordered state, retain the two near frames, and
tail-transfer to `$C1:4833`. The common loader's `RTS` at `$C1:48EB` then
returns through `$C1:432B` to `$C1:40B0`. The original return chain has been
observed; no expanded helper currently enters those real continuations.
See the [integration design](schala_package_resolver_integration_design_v0.md#exact-hook-geometry-and-ordinary-caller-path)
for its pinned instruction spans and full entry/exit ABI.

The preserved [v2 helper](schala_package_helper_v2_stack.md) uses 42 local
bytes, eight saved-register/status bytes, and a deepest two-byte local `JSR`:
52 bytes in total. Its proof is synthetic. Applying its arithmetic to the
observed numeric SP yields a deepest helper SP of `$06A4`. This new IRQ
audit uses precisely that hypothetical interrupted SP; the IRQ's 35-byte
contribution then yields `$0681`. The written stack bytes start at `$0682`,
not `$0681`: the CPU writes at SP and then decrements it.

For every arithmetic helper depth from zero through 52 and IRQ depth up to
35, the combined possible stack bytes plus the five known caller bytes fit
the half-open interval `$0682-$06DE`. The derived ordinary CPU-write set
does not intersect any byte in that interval. This is an alias comparison
against an explicit interval, not proof that the interval is available,
that all actual callers use `$06D8`, or that NMI cannot require more depth.

The remaining caller obligations include:

- Prove the installed interrupt-handler lifetime at the proposed hook,
  including the alternate NMI whose early callee depends on incoming DBR.
- Close actual NMI and nesting behavior, DMA/HDMA interference, and physical
  writable stack ownership. The new calculation does not provide a global
  reserve recommendation.
- Establish the real helper's intermediate-publication observers. This
  packet proves no CPU-write overlap from this IRQ; it does not prove that
  interrupt readers cannot observe partial package publication.
- Preserve already consumed fixed-bank auxiliary config fields and establish
  an action's full completion behavior. The terminal-only synthetic package
  still supplies no action-lifecycle implementation.
- Implement and prove the selected earlier preflight boundary or a complete
  refusal lifecycle. The resolver runs after effect preparation and MP
  deduction; restoring its registers cannot cancel that transaction. The
  [source-only preflight planner](schala_package_preflight_planner_v1.md)
  does not yet execute inside the game.
- Promote exact hook spans, preimages, expanded allocations and bindings only
  after the remaining gates pass. Production catalogs remain untouched.

## Value and stack semantics

The abstract accumulator holds separate low A and hidden B bytes. X, Y and D
also hold two separate bytes; DBR holds one. Each byte is an explicit constant,
an initial-register symbol, or unknown. Unknown is never treated as zero.
Memory reads conservatively lose the visible destination bytes; 8-bit loads
preserve hidden B. `TDC` and `TCD` transfer the complete 16-bit value. `TAX`
uses the destination index width. Selecting 8-bit indices clears the high
bytes of X and Y. Arithmetic is retained only when the operands needed by
that operation are explicit constants; otherwise the visible result becomes
unknown. All data-condition branches remain unpruned either way.

The native hardware frame retains distinct symbolic PBR/PCH/PCL/P cells.
Software data pushes retain actual byte identities in high-then-low word
order. A pull reads low then high. A data pull cannot consume a typed PHP,
near-call, long-call, or hardware frame. PHP/PLP preserve the modeled width
and interrupt-mask tuple. A return must consume its exact near/long frame;
a near return must retain the correct program bank. RTI requires the original
hardware cells and restored symbolic A/B/X/Y/D/DBR. It then restores the
saved P, PC/PBR and SP according to the native hardware-frame contract.

The ordinary CPU-write alias check runs before accepting any store. It
normalizes low WRAM mirrors in banks `$00-$3F` and `$80-$BF`, and full WRAM
banks `$7E/$7F`, to physical byte indices. Banks `$40-$7D` are not silently
treated as low WRAM mirrors. The check covers every already-live IRQ byte and
the declared protected helper/caller bytes.

Direct-page stores require a known D and compute the bank-zero address
modulo `$10000`. Absolute stores require a known DBR. Their word high byte
uses the 24-bit next bus address; direct-page word addressing wraps in bank
zero. A 16-bit read/modify/write records the high-byte write before the
low-byte write. STX/STY widths follow X, independently of M.

Each `MVN` requires explicit A and Y with 16-bit indices and a bounded extent
of at most 4,096 bytes. The count is A+1; A=0 still copies one byte. The
destination bank comes from the actual first operand byte, updates DBR, and
remains fixed when Y wraps. The model expands every destination byte, then
updates X/Y and leaves A=`$FFFF`. The canonical transfers each copy 30 bytes.
Treating the whole transfer as one abstract step is conditional on the stated
absence of interfering asynchronous writes; this is not a timing or
preemption model.

## Derived ordinary CPU destination inventory

All ranges here are physical WRAM offsets and half-open.

| Destination family | Exact derived extent |
| --- | --- |
| IRQ busy marker | `$007F-$0080` |
| Animated-tile parity | `$051D-$051E` |
| Twelve animated-tile progress words | Two bytes starting at `$05B0,$05B5,$05BA,$05BF,$05C4,$05C9,$05CE,$05D3,$05D8,$05DD,$05E2,$05E7` |
| Nine display-table blocks | 30 bytes starting at `$C867,$C894,$C8C1,$C8EE,$C91B,$C948,$C975,$C9A2,$C9CF` |
| Display parity / pending change | `$CA22-$CA23` and `$CA24-$CA25` |

These account for exactly 298 distinct WRAM destination bytes. The complete
metadata additionally identifies all 109 instruction sites, write order,
width, stack depth, and each individual bus address.

The 19 derived hardware-register byte addresses are `$002100`,
`$002115-$002117`, `$004200`, `$004202-$004206`, `$00420B-$00420C`, and
`$004370-$004376`, with the listed ranges inclusive. Their existence keeps
DMA/HDMA semantics an explicit open gate. This audit does not infer their
transfer direction, source addresses, pending state, timing or memory effects.

The separately checked package/control intervals are DP `$0080-$0084`,
`$9876-$987C`, `$A0B3-$A0B5`, active-owner words `$5DAC-$5DBD`, pointer/bank
words `$5DBD-$5DFD`, and effect latch `$5D9B-$5D9C`. The config/control range
deliberately includes the selector/root neighborhood. No byte in any of
these ranges belongs to the derived IRQ CPU-write set.

## Provenance and reproduction

The input is the exact headerless US Rev0 4-MiB ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The four canonical code extents and hashes come from the unchanged accepted
IRQ reference; they are rehashed from the full-hash-checked ROM and the entire
previous reference is regenerated before the new analysis. Annotations are
navigation only; the interpreter reads actual instruction bytes.

The native CPU rules are checked against the already pinned Mesen source at
commit `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`:

- [SnesCpu.Shared.h, lines 450-511](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L450): word-write masks/order, push/pull order, native direct-page arithmetic.
- [SnesCpu.Instructions.h, lines 717-741](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L717): MVN byte iteration, destination-bank assignment and count.
- [SnesCpu.Instructions.h, lines 1173-1258](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1173): absolute and direct addressing-mode setup.

Both complete local source files are pinned by SHA-256 in the auditor. The
helper source and accepted helper/resolver references are retained as
identity-only context; their native traces are not rerun or revalidated by
this new static packet. All source identities are checked again after
collection.

Run from the repository root:

```powershell
python -B -m unittest discover -s tests -p test_schala_package_irq_memory_contract_v2.py
python -B tools/audit_schala_package_irq_memory_contract_v2.py
```

The 49 original-host tests cover wrong save order, hidden B, D/DBR selection,
native widths, caller and hardware-frame aliases, WRAM mirrors, byte and word
store boundaries, MVN count/bank/wrap/unknown-input refusal, typed returns,
unmasking, source truncation, bounded-state refusal and stack-underflow edges.
The first test pass found one fixture-expectation error: an STX/STY test used
bank-zero `$3000` as if it were WRAM. The test now explicitly selects bank
`$7E`; the physical mirror model was correct and unchanged. Self-review also
tightened the stack floor so a maximum depth equal to incoming SP ends at
SP=0, while one extra push refuses. No accepted or native artifact existed
under either earlier development revision.

Root preacceptance review identified three evidence-boundary improvements.
The CLI now writes explicit UTF-8 bytes with LF and one trailing newline,
independent of Windows text-output translation. The value walk assigns every
decoded byte to one instruction start and refuses both entry into operands
and incompatible width-dependent instruction lengths at a shared PC. It also
rejects instructions crossing a program-bank boundary. Finally, the original
four native hardware-frame bytes are checked against protected ranges before
any instruction, including an immediate RTI. These guards do not change the
canonical 2,244-state / 401-start / 404-context / 109-write result.

The preacceptance source, tests, report and candidate metadata remain intact
under ignored `private/test_runs/irq_memory_v2_20260908_review1`. Its
`receipt.json` SHA-256 is
`aa57073b4c3af5d7de21b145b28fa35cad900743e9d616c2d803cf944e3e4230`.
That draft is historical evidence, not an accepted reference. After the
hardening, all 49 tests pass and two actual fresh CLI processes emit identical
UTF-8/LF bytes with empty stderr. The independent peer review subsequently
passed the complete symbolic, address and stack model, all 49 tests, and a
fresh exact CLI reproduction. It also checked additional original boundary
specimens for a long-word high-byte WRAM alias at `$800000`, an MVN bank-zero
alias, and initial hardware-frame overlap; all refused as expected.

The final [reference](../references/schala_package_irq_memory_contract_v2.json)
is 84,558 bytes, SHA-256
`6a6cc3ac65cc2e9ae5d5fe92a313a7a716f31cdbc1256fc18d38a4731eaadc31`.
Both reviewers independently reproduced those bytes. The executable source
is 24,156 bytes, SHA-256
`cd7ce6b278bcbce5b9293a813640b0cc3a90dc95fb0a655957e295363e00c1a6`;
the tests are 9,606 bytes, SHA-256
`d3e2a1252caf44b3622d78992addf363b03261f0d95f1bfd7fc8435e751f0e80`.
The packet reports a new conditional proof, not a correction of the earlier
audit, which explicitly left ordinary CPU destination aliases unresolved.
