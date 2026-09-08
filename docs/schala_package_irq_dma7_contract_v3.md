# Requested channel-7 DMA destinations in the battle IRQ, v3

Date: 2026-09-08. Evidence: `verified-static` under the explicit entry and
interference premises below. Source, original-host tests and reproducible CLI
output are complete; independent review and final reference emission are pending.

The field-DMA service used by the normal battle IRQ establishes the same
configuration before each of its twelve manual DMA request sites: channel 7,
forward A-to-B transfer, mode 1, B-bus destination register `$18`, and 128
bytes. Under the pinned emulator's register and transfer semantics, the data
writes requested by those configurations target only `$2118` and `$2119`.
Those addresses route to VRAM ports, independently of the source bank and
offset values. They do not target the WRAM port `$2180` or the helper's stack.

This is a destination contract for those specific requests. It does not
establish valid source bytes or source-read side effects, graphics correctness,
actual transfer completion, timing, competing DMA/HDMA activity, NMI nesting,
or a global stack-ownership policy. No native execution, game hook, patched
ROM, source-controlled game data, or production allocation is added.

The separately numbered
[auditor](../tools/audit_schala_package_irq_dma7_contract_v3.py) preserves the
entire frozen [IRQ memory/register packet](schala_package_irq_memory_contract_v2.md).
It reproduces that packet before applying a smaller value projection to its
field-DMA leaf service, `$FD:E022-$FD:E275` half-open. The source extent is
595 bytes, SHA-256
`710683e30da8a2b55b5c7865cbc61161b200618537bb5ccdacffe33d4a07cf61`.

## Configuration and ordering proof

The reproduced IRQ graph reaches the service with native M=1, X-width=0,
and I=1. The new projection uses exactly those width/status premises and
symbolic incoming A/B, X, Y, D and DBR values. It does not require an
unjustified incoming zero bank or accumulator.

The actual prologue saves P, D and DBR, sets DBR zero through the one-byte
`LDA/PHA/PLB` sequence, selects D=`$0500` through the actual X push/D pull,
selects 8-bit indices, and loads Y=`$80`. The service has no direct or
indirect callee: its odd-record branch is a direct bank-local jump. Every
conditional record branch takes both edges in the model.

| Role | Exact CPU writer | Established value |
| --- | --- | --- |
| Channel 7 control, `$004370` | `$FDE030` | `$41` |
| Channel 7 B-bus base, `$004371` | `$FDE035` | `$18` |
| Each request's size high byte, `$004376` | The word STZ six bytes before its enable site | `$00` |
| Each request's size low byte, `$004375` | The byte STY three bytes before its enable site | `$80` |
| Each manual enable, `$00420B` | The request site itself, exact byte STY | `$80`, channel 7 only |

The twelve enable sites are:

| Even-record branch | Odd-record branch |
| --- | --- |
| `$FDE076` | `$FDE18B` |
| `$FDE0A2` | `$FDE1B7` |
| `$FDE0CE` | `$FDE1E3` |
| `$FDE0FA` | `$FDE20F` |
| `$FDE126` | `$FDE23B` |
| `$FDE152` | `$FDE267` |

The canonical projection visits 338 abstract states and all 254 instruction
contexts belonging to this service in the reproduced IRQ packet. Its 136
ordinary CPU byte-write contexts match the previous packet exactly by PC,
bus address, width and M/X state. It reaches the two original long-return
sites `$FDE15F` and `$FDE274` with the original long frame, saved D/DBR and
entry width/status tuple restored. The larger IRQ's saved-register proof
remains separate; this service deliberately changes its caller's A/X/Y.

Each DMA request retains the last actual modeled CPU writer of all four
configuration bytes. The collector checks the two shared control-writer
addresses and both per-request size-writer addresses. A stale initial size,
unknown high byte, wrong write width, intervening overwrite, wrong control,
wrong B-bus port or additional channel bit cannot satisfy the contract.

The projection admits hardware-register writes only through bank zero.
Every byte of a modeled store is checked against the pinned hardware mirrors
in banks `$00-$3F/$80-$BF`, ranges `$2000-$2FFF/$4000-$4FFF`.
An equivalent register write through a nonzero bank refuses, including a
word whose first byte is outside the mapped range and whose second enters it.
This narrow policy avoids silently ignoring an alias or treating a WRAM
address in banks `$7E/$7F` as a hardware register.

After a request, the projected size-counter bytes become unknown. The audit
does not assume that hardware completed the requested transfer or left its
counter at zero. The next request must establish both size bytes again.
Source-bank and source-offset writes remain unknown-valued and are explicitly
outside the destination certificate; their unknownness cannot silently
become a source-data validity claim.

## From register values to data destinations

Mesen's pinned DMA decoder assigns bit 7 of DMAP to direction and the low
three bits to transfer mode. `$41` therefore selects forward mode 1. Its bit
6 controls HDMA indirect addressing; it does not invert a manual transfer.
The mode-1 transfer-offset sequence repeats `0,1,0,1`. With BBAD `$18`, the
manual DMA loop's B-bus address expression selects `$2118/$2119`.
[Pinned DMA source](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp#L46)

The forward copy path reads the selected A-bus source and writes the B-bus
address. The memory manager routes low-bank `$2000-$2FFF` to the B-register
handler. That handler handles the WRAM data/address ports `$2180-$2183`
separately and forwards `$2118/$2119` to the PPU. The PPU writes the low or
high VRAM byte when VRAM is accessible; otherwise it suppresses that data
write while retaining its own address-increment semantics.
[Bus-B routing](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/RegisterHandlerB.cpp#L60),
[PPU port semantics](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L2046)

The metadata records the 128-byte requested address order by SHA-256:
`081917f4bab918301ab537954c10a3101a62239ccd8a8ffe9d5d012e9e3e07a7`.
The hash covers the sequence of 128 two-byte little-endian B-bus addresses.
It is a deterministic consequence of the requested configuration, not a
native bus trace or a claim that 128 transfers actually completed.

This proof does not inspect A-bus source contents. A source address can have
effects on reads, and source validity can matter even when the data-write
destination is VRAM. Likewise, an intervening HDMA operation or other writer
can invalidate a channel's configuration. The contract explicitly requires
that no other actor changes the DMA channel configuration while the request
executes. Prior pending DMA, HDMA enable/lifetime, interleaving and elapsed
time remain separate gates.

## Model, provenance and reproduction

The new value projection reuses only the frozen IRQ decoder, byte-value
helpers and saved-cell type. It implements its own finite state transition
and DMA-register ledger. No instrumentation or source rewriting of the old
interpreter occurs. Decoded-byte ownership and instruction lengths must
remain unambiguous; unsupported calls, instructions, status effects,
bank-crossing instructions, IRQ unmasking, bad frames and state-budget
exhaustion refuse.

The canonical ROM remains the exact 4,194,304-byte headerless US Rev0 image,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Complete source identities and nine semantic source spans are retained in
the metadata. Source spans are explicitly identified as reviewer-derived
semantics; a source hash pins the interpretation's input and does not itself
derive meaning from C++.

All CPU/DMA/routing sources use Mesen commit
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. Previously pinned DMA, memory-manager
and PPU sources are reused unchanged. The additional public
`RegisterHandlerB.h/.cpp` files were fetched from that exact commit, checked
against GitHub's reported Git blob SHA-1 using the canonical blob prefix,
and retained in ignored `private/research/mesen_irq_dma7_2_1_1` with URL,
commit, size, SHA-256 and Git-blob receipts. The implementation is 2,969 bytes,
SHA-256 `a3ebaecac6e6fe2d2bdfc04f072e77a9ba47251cdc5ae9d4b6fcdd4618af7ea7`.
The header is 874 bytes, SHA-256
`709fb56c99d894650c4a0c55fbcf1c6714cac59fa85fe8518e486302d2519e20`.
The already-local `RegisterHandlerA.h` is also pinned: 1,635 bytes, SHA-256
`782f34e6b68d6b247d37a5142f8071fad85b2dd13bd33a96d3f5bb085f176f3c`.
Its actual CPU-write dispatch masks to sixteen address bits before routing
manual-DMA/HDMA enable and channel-register writes to the DMA controller.
The selected DMA source spans include both transfer-count byte assignments.
[CPU register dispatch](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/RegisterHandlerA.h#L55),
[transfer-count assignments](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesDmaController.cpp#L474)

The collector pins and reads the accepted IRQ v2 reference (SHA-256
`6a6cc3ac65cc2e9ae5d5fe92a313a7a716f31cdbc1256fc18d38a4731eaadc31`),
requires byte-exact equality with the full regenerated prerequisite, and
verifies the exact
subset of instruction contexts and ordinary CPU writes before reporting
the new requests. All direct, owned and inherited source identities are
checked again at the end. The human report is outside these executable
input hashes; a review-status update cannot change the static result.

```powershell
python -B -m unittest discover -s tests -p test_schala_package_irq_dma7_contract_v3.py
python -B tools/audit_schala_package_irq_dma7_contract_v3.py
```

All 41 original-host tests pass. They cover reverse direction, WRAM-port
selection, wrong/additional channels, strict numeric types, wrong count,
missing or overwritten count bytes, exact STY width, unknown Y/configuration,
prior-request counter reuse, per-request size reinitialization, other-channel
or HDMA writes, bank/direct-page setup, typed status/return, unsupported
calls, both branch edges and instruction overlap. The first test pass
correctly rejected an unknown Y earlier than its test expected: Y also
supplied the size low byte, so the unknown-size check fired first. The test
expectation was corrected, and a second specimen independently supplies
the size to reach the unknown request-value check. No native or accepted
artifact existed under that development revision.

Independent review reproduced a generic model gap in the initial draft:
setting DBR to `$80`, storing reverse-direction `$C1` through `$80:4370`,
then restoring DBR to zero left the ledger's older `$41` control intact.
The canonical routine uses bank zero, so the canonical twelve requests were
not contradicted. The draft source, tests, report and candidate metadata
remain preserved under ignored
`private/test_runs/irq_dma7_v3_20260908_review1`; its receipt SHA-256 is
`d671ef0873617104a50ac6bfb3affa7160f8cad9635c38dc39cfee1e2d1d910d`.
The corrected guard refuses every nonzero hardware-mirror bank. Four added
tests cover all 127 such banks, mirrored control/count/enable/other-channel
writes, high-byte range crossings, and the distinct full-WRAM banks.
No native run or accepted reference existed under the superseded draft.

The corrected semantics passed root and independent review. Root then
requested that the reproduced IRQ prerequisite be compared directly with
the accepted reference file, in addition to computing its digest. The
semantically accepted intermediate source, tests, report and candidate are
preserved under `private/test_runs/irq_dma7_v3_20260908_review2`, receipt
SHA-256 `31fcc235da85065942ccdadc155f9ab9fdba51cea6adff2f350692b51eef3693`.
The explicit pin/read/byte-equality gate now runs before DMA projection;
four additional original-fixture tests cover exact reproduction, missing
reference, byte drift, and changed regeneration against an intact reference.

Two fresh actual CLI processes emit identical UTF-8/LF output with empty
stderr and unchanged source hashes. The current candidate metadata is
58,451 bytes, SHA-256
`10b35697c6eac860f79a3d062856f944540b96a200114b5da5fab0fb6b94d2d3`.
Root and independent review accepted the corrected destination semantics,
hardware-mirror guard and source provenance. Root additionally reviewed the
final accepted-reference binding, independently passed all 41 tests, and
reproduced the exact output in two actual CLI processes. The final
[reference](../references/schala_package_irq_dma7_contract_v3.json) is now
emitted at that exact identity. The executable source and tests remain frozen.

This is additive evidence. It does not contradict the v2 IRQ packet's
explicitly open DMA-transfer gate and does not promote any production hook,
stack allocation, high-selector binding or eighth playable character.
