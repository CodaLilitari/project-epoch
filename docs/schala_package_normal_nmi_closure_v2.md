# Normal NMI direct callees: bounded stack and width closure

Date: 2026-09-08. Evidence level: `verified-static` in the explicitly bounded
abstract model below. Two independent reviews passed the source and all 42
tests, and each reproduced the 321,839-byte reference exactly at SHA-256
`413a6e70a222aee957d9d9f37a7655634e034bda91b777ebdcebad7c29911242`.
Those reviews retain every conditional premise and open ownership frontier
described here; they add no native execution evidence.

The preserved normal-NMI v1 census contains 44 call sites. This separate v2
investigation now closes the typed stack/call-frame and M/X/I control-flow
model for **25 of 32 distinct direct callees**, covering **34 of the 42 direct
call sites**. All of those completed callees return with the M=1/X=0/I=1 state
assumed by v1's conditional local census. The other eight direct call sites,
plus its two indexed call sites, remain open. No opaque callee receives an
invented zero-depth summary.

This is progress on the call-frame part of stack ownership. It is not a
whole-NMI bound, a proof that non-stack memory writes avoid the live stack,
or an execution of the handler. The completed v1 NMI, IRQ and v2/v3 helper
sources and references remain unchanged. No emulator was launched and no ROM
was mutated for this investigation.

## Reproduction and source identity

The [new read-only auditor](../tools/audit_schala_package_normal_nmi_closure_v2.py)
requires the exact canonical headerless US Rev0 ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
It verifies the [preserved v1 reference](../references/schala_package_normal_nmi_v1.json)
and all of that reference's source identities, then reproduces the entire v1
audit before resolving its call inventory. The previous reference SHA-256 is
`27dd6f602781b83107bd7ab9072f1704e26bb39433713a3188679114db3b4f2c`.

The [v2 reference](../references/schala_package_normal_nmi_closure_v2.json)
records every original site, the exact callee context, decoded byte-interval
hashes, return-width states, direct calls/jumps, unresolved first frontiers,
and syntactic memory-write operands. Raw ROM bytes are never emitted. Two
independent in-process audits produced identical metadata before it was written.

```powershell
python -B tools/audit_schala_package_normal_nmi_closure_v2.py
python -B -m unittest discover -s tests -p test_schala_package_normal_nmi_closure_v2.py
```

The CLI emits deterministic UTF-8/LF JSON to standard output. Forty-two
original host tests pass without reading a game ROM. They cover typed status
saves, native save widths, nested near/long frames, far-tail return-bank
failures, stack corruption/underflow, unknown status restoration, IRQ
unmasking, dynamic dispatch, mode/SP changes, recursion and bounded-state
refusal, overlapping width decode, physical-bank boundaries, and reset-prefix
mutations. A finite loop may close mechanically without proving termination;
the tests require that distinction to remain explicit.

Instruction/address-mode and native push/pop/return semantics are checked
against pinned primary Mesen source at revision
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`:
[SnesCpu.Shared.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h)
and [SnesCpu.Instructions.h](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L479).
Their exact hashes are in the new metadata and are checked by the auditor.
Upstream Chrono Trigger labels are documentary context from the preserved
`eeae27acdb6565e96d1d796a3d60792c250c0aa1` disassembly checkout; they do not
supply instruction widths or turn table-adjacent bytes into valid targets.

## What a completed callee contract means

The walker starts at the exact direct target and native M/X/I state recorded
by v1. Its root near or long return frame is a typed abstract identity. Each
nested JSR/JSL adds its actual two/three-byte frame; an RTS/RTL must consume
the correct frame kind and continuation. Near returns cannot restore a
program bank changed by a far tail jump. Direct far tails are supported only
when the eventual return preserves the correct frame semantics.

PHP records known M/X/I bits in a typed byte; PLP must recover that exact kind
of value. Other pushes/pulls have their native widths. PEA, PHK and direct
JML/BRL handling are explicit. CLI or REP that unmasks IRQ, XCE, direct SP
assignment, indexed dispatch and unknown operations produce unresolved
frontiers. A changed opcode does not become a guessed one-byte no-op.

Both outcomes of each conditional branch are traversed. Direct calls are
actually entered, and only proved returns resume their caller. The model
follows finite revisited states and refuses unbounded stack growth, excessive
call nesting, or state-budget exhaustion. It rejects incompatible
width-dependent instruction lengths and branch targets inside another
instruction. Ordinary PC fallthrough and relative branches wrap within the
physical program bank; instruction operands that cross that bank boundary
are deliberately outside this model.

**The model assumes that non-stack memory operations do not alter the saved
stack bytes or return frames.** Register values, effective memory addresses,
DMA/HDMA destinations and timing are not modeled. This premise is recorded
in every callee result, with non-stack alias closure false. The result is
therefore a conditional stack-instruction/call-frame bound, not physical
memory ownership. Generic arithmetic flags are not value-tracked; both branch
outcomes form a possible-path overapproximation. Termination and runtime
reachability are also unproved.

The additional depth below a callee's entry SP excludes its root call frame,
because v1's conditional callee-entry depth already includes that frame.
Adding the result to a v1 entry depth retains the original caller-depth
premise. No number in the table is a maximum for the complete NMI.

| Direct target | Return frame | Additional bytes below callee entry | Instruction starts traversed | Original call sites |
| --- | --- | ---: | ---: | ---: |
| `$C00002` | long | 4 | 190 | 1 |
| `$C10009` | long | 0 | 222 | 1 |
| `$C1000F` | long | 2 | 230 | 1 |
| `$CD0340` | near | 0 | 35 | 2 |
| `$CD053C` | near | 0 | 29 | 1 |
| `$CD0577` | near | 0 | 29 | 1 |
| `$CD05B2` | near | 20 | 156 | 2 |
| `$CD0607` | near | 6 | 121 | 1 |
| `$CD06C4` | near | 0 | 71 | 1 |
| `$CD09CE` | long | 0 | 13 | 2 |
| `$CD0ADE` | near | 0 | 7 | 2 |
| `$CD0AEE` | near | 0 | 17 | 2 |
| `$CD0B1E` | near | 0 | 25 | 2 |
| `$CD0B51` | near | 2 | 130 | 1 |
| `$CD0C89` | long | 11 | 199 | 1 |
| `$CD0E9D` | near | 0 | 18 | 1 |
| `$CD3B82` | near | 0 | 15 | 1 |
| `$CD3EB4` | near | 5 | 29 | 2 |
| `$CEE18E` | long | 1 | 32 | 1 |
| `$CEEE6E` | long | 17 | 68 | 1 |
| `$CEF066` | long | 0 | 51 | 1 |
| `$D1EA4B` | long | 4 | 202 | 1 |
| `$D1F426` | long | 2 | 52 | 2 |
| `$D1FE71` | long | 0 | 14 | 1 |
| `$FDFFF7` | long | 9 | 890 | 2 |

The zeroes above follow complete instruction traversal and balanced returns;
they are not placeholders for unknown implementations. All 25 completed
contracts match the prior M1/X0/I1 return-width premise. D, DBR and the actual
A/B/X/Y values have not been symbolically proved for those callees.

Three useful examples illustrate the newly closed arithmetic:

- `$CD05B2` traverses the complete direct screen-transition subgraph, including
  the display-table loader, and adds 20 bytes below entry. With v1's entry
  premise of 20, its conditional peak is 40 bytes below interrupted SP.
- `$CD0C89` enters the real `$C00002` field service and adds 11 bytes below
  wrapper entry. With v1's 16-byte entry premise, the conditional peak is 27.
  The nested field callee itself adds four bytes below its own entry.
- `$FDFFF7` traverses 890 distinct instruction starts through the animated-tile
  service and its direct callees, adding nine bytes below entry. V1's 21-byte
  callee-entry premise therefore yields a conditional 30-byte peak.

The old busy fast path remains separately proved at 13 total bytes. The
complete direct display-loader result also agrees with its existing IRQ
closure. These relationships reuse the completed evidence; they do not
replace a global interrupt or alias proof.

## The remaining ten original call sites

Two direct target families reach an explicit reset path:

- `$C1000C` follows the fixed battle entry through `$C1007A -> $CFE58A` and
  can reach the far jump at `$CFE702 -> $C0FF00`. Its branch ancestry includes
  encoded `$2989` bit `$20`, input/latch state, and a countdown at encoded
  `$BB00`. The new model follows both branch outcomes and does not prove
  those predicates false in a package-helper context.
- `$C28002`, called at two original NMI sites, can reach
  `$C28523 -> $C0FF00`. The local joypad service sets D/DBR to zero and has
  the word comparison of `$004218` against `$3030` before this reset jump.
  The input predicate and its reachability are not discharged here.

The shared prefix at `$C0FF00` executes SEI, CLC, XCE and a direct jump to
`$FDC000`. A separate finite source check confirms that startup selects X16,
loads X=`$06FF`, and executes TXS at `$FDC007`. It replaces the stack pointer;
it is not an ordinary balanced return to the interrupted call. The metadata
retains exact hashes for the seven-byte reset prefix and eight-byte startup
prefix. It does not claim that reset ran in an emulator. A later normal-return
contract must either prove the reset predicates excluded in its declared
context or explicitly separate intentional reset as a different lifecycle
outcome. Continuing past XCE as an ordinary no-op would hide this distinction.

Three indexed-dispatch instructions account for the other seven open sites:

| Frontier | Original sites affected | Remaining data/control contract |
| --- | --- | --- |
| `$CD06B9`, indexed JMP through `$CD06BC` | One direct caller of `$CD06B4` | Encoded `$CA92` producer range, incoming hidden B at eight-bit ASL/TAX, actual table extent and selected callee |
| `$CD0C99`, indexed JSR through `$CD0C83` | The direct mode-wrapper caller plus the indexed site itself | Mode predecessor constraints, complete legal targets, and each selected body contract |
| `$CD16AF`, indexed JSR through `$CD16B5` | Three direct scene-wrapper callers plus the indexed site itself | Scene command/table extent, script provenance, B/index state, command callees and loops |

The new metadata reads exactly four physical scroll-HDMA table cells at
`$CD06BC-$CD06C3`: `$CD06C4`, `$CD076C`, `$CD07E2`, `$CD07B9`. They are reviewed
cells, not proof that every possible index is legal or that the table's full
valid extent is established. The existing v1 mode table similarly has three
reviewed cells. The scene table receives no invented 127-entry extent merely
because the byte syntax admits commands `$80-$FE`.

An open direct result records its first encountered frontier and partial
traversal provenance. It does not claim to enumerate every later frontier in
that callee; no depth maximum is emitted for it. The caller's continuation is
never resumed behind an unresolved call by assigning it an opaque zero cost.

## Remaining ownership work and preserved history

The next high-value source work is effective-address analysis of completed
callees and producer/dispatch analysis of the three indexed sites. The
metadata inventories syntactic memory writes, but neither a direct-page
operand nor an absolute operand proves an effective physical target without
D/DBR and index provenance. Indirect stores and block moves require explicit
alias contracts. A completed call-frame model alone cannot show that the
helper's live local frame, caller frame, publication words or direct-page
outputs survive the interrupt.

The full handler also retains its busy-flag leading/trailing windows,
installed-handler choice, hardware reentry timing and nested IRQ/NMI
obligations. The earlier 35-byte non-nested IRQ maximum and the newly closed
local subgraphs must not be added into an invented universal reserve.

The first exploratory decoder snapshot is preserved privately under
`normal_nmi_closure_v2_20260908_explore1`. Its metadata was an incomplete
coverage inventory, before near-return bank, incompatible-width and bank-wrap
hardening and before all ordinary opcodes in the final direct subgraphs were
covered. The reference pins that source, output and receipt and labels them
unaccepted exploratory history. There is no native failed run to replace.

No prior data-map claim is contradicted by discharging some of v1's explicit
premises or identifying reset/dispatch reasons why others remain open. V1
already declared its opaque return and stack assumptions as unproved. Every
production hook, allocation, selector binding and PC `$07` integration gate
remains unchanged.
