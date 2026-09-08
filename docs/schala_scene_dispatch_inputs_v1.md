# Scene dispatcher inputs and the hidden accumulator byte

Status: `verified-static` under the explicit native M=1, X=0 and D=0
prefix contract. Two independent reviews passed all 27 tests and reproduced
the 156,163-byte reference exactly at SHA-256
`d5604c65934dff1dfa4796ea3d990e227065e9b28a5499695f590fff912a8c13`.
One review additionally reproduced it through the fresh CLI. This separately
numbered audit preserves the accepted NMI closure v2 source and reference.
It proves a register-byte fact before the first indexed call and records
the remaining source-data obligations. It does not close a command handler
or establish a whole-NMI stack reserve.

The first indexed scene-command call reached from the tick setup has B=0.
At `$CD:161D`, `TDC` clears both accumulator bytes when D=0. The slot path
loads the bank byte and command byte in M=1, preserving B. Its eight-bit
`ASL A` also preserves B; `TAX` in X=0 then copies the full accumulator.
The alternative tick path through `$CD:1640` also executes `TDC` before
the next slot. The finite prefix analysis explores both outcomes of every
conditional branch and stops at the first `$CD:16AF` indexed call. Every
path reaching that frontier has B=0; no command handler is assigned an
assumed return value to obtain that result.

That result is local to the first indexed call reached after the tick
setup. The command continuation at `$CD:1698-$CD:169E` reads and increments
the current script cursor, then returns to the byte fetch at `$CD:165F`.
There is no `TDC` in this loop. A command handler's returned B therefore
reaches the next indexed dispatch unchanged unless the handler itself
establishes a suitable value. The second analysis enters this continuation
with unknown B and retains that uncertainty at the next indexed call.
A standalone entry at `$CD:1654` also does not clear an incoming unknown B.
The yield and tilemap exit paths separately clear the full accumulator at
`$CD:166F` and `$CD:1689`; that does not certify arbitrary command returns.

These distinctions refine the previously open hidden-B frontier in
[normal-NMI closure v2](schala_package_normal_nmi_closure_v2.md). They do
not contradict its statement that the complete dispatch contract remained
unproved. The source annotation's `(A-$80)*2` description is a useful
low-byte shorthand only when the full-register preconditions are supplied.

## The exact local byte and pointer recipes

The slot classifier has four cases:

| Stream byte | Local behavior |
| --- | --- |
| `$00-$7E` | Tilemap request path, followed by a slot return |
| `$7F` | Yield path, followed by a slot return |
| `$80-$FE` | Direct call of the indexed-command wrapper |
| `$FF` | Clear the slot-active byte and return |

For an indexed command byte `c` and incoming hidden byte `b`, the actual
M=1 `ASL A`, X=0 `TAX` recipe is:

```text
X = (b << 8) | ((c << 1) & $FF)
table-low-byte address  = $CD0000 | (($16B5 + X) & $FFFF)
table-high-byte address = $CD0000 | (($16B6 + X) & $FFFF)
```

With B=0, X is `2*(c-$80)`. With B unknown, it is a bank-wide indexing
problem. The host algebra checks all 32,512 indexed-command/B pairs.
One pair, command `$A5` with B=`$E9`, reads the pointer bytes at `$CD:FFFF`
and `$CD:0000`; the indexed JSR's pointer-word read wraps inside PBR.
This is a possible input to the local instruction recipe, not a runtime
claim that this command/B pair occurs in a game scene.

The CPU semantics are supported by the pinned Mesen 2.1.1 source:
[`ASL_Acc`, lines 625-632](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L625)
retains A's high byte in M=1;
[`TAX`, lines 1058-1060](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1058)
selects the destination width from X;
[`TDC`, lines 1078-1080](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L1078)
copies the full D register; and
[`JSR_AbsIdxXInd`, lines 446-459](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L446)
reads the two pointer bytes through program-bank addresses. The metadata
pins both instruction and opcode-dispatch source files to the same source
identities already retained in closure v2. These are static source contracts,
not new emulator observations or an independent CPU implementation.

## Reviewed cells and code occupancy

The 122 reviewed cells for B=0 and commands `$80-$F9` occupy the exact
half-open span `$CD:16B5-$CD:17A9`. They point to 121 distinct targets;
`$B5` and `$B6` share a target. The `$F9` cell itself points to `$CD:17A9`,
where a decoded command body begins. Its 21-byte span through `$CD:17BD`
contains ordinary instructions and ends in RTS. The new metadata records
each instruction's address, length and hash, without publishing game bytes.

The five remaining syntax-admitted cells overlap the beginning of that
same command body:

| B=0 command | Pointer cell | Word interpreted as target |
| --- | --- | --- |
| `$FA` | `$CD:17A9` | `$CD:40A7` |
| `$FB` | `$CD:17AB` | `$CD:A048` |
| `$FC` | `$CD:17AD` | `$CD:0001` |
| `$FD` | `$CD:17AF` | `$CD:20C2` |
| `$FE` | `$CD:17B1` | `$CD:40B7` |

This is an exact occupied-code/table-read overlap, not evidence that these
five values are reachable, legal, illegal, unused or free. Canonical code
and data can share bytes; mere adjacency cannot prove the complete legal
table extent. The 122-cell prefix is therefore explicitly a reviewed prefix.
The auditable requirement remains a command-domain proof from actual script
tokens and their producers, followed by each selected command's control,
width, return-B, stack and effective-address contracts.

The preserved disassembly labels `$CD:16B5` and places the region through
`$CD:1833` in an opaque data inclusion. It does not independently supply a
122-entry legal domain. See the exact
[`bank_CD.asm` source around lines 2732-2744](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_CD.asm#L2732).
The local source file has 474,851 bytes and SHA-256
`0d230620c6accf311c0588e2fefaf3bcc48b0d42575f3745fec3a402a6ca19fb`.

## Script-source chain and what it still requires

The background loader at `$CD:0F42-$CD:0F61` computes a 16-bit index from
four times the incoming X value, reads two consecutive words through long
address `$D1:6240`, and stores four bytes beginning at `$7E:CA93` under
DBR=$7E. Its background-ID domain is not established by this local consumer.
Long indexed addresses can cross a bank; they must not be modeled as the
same PBR-wrapped recipe used by the indexed JSR.

The initializer at `$CD:0D33-$CD:0D61` clears the local scene arrays, then
reads the two IDs at `$CA93/$CA94`, skipping `$FF`. It starts slots with
X=`$0000/$0010`. Its `TDC` supplies B=0 under D=0 before the ID read, and
the start routine clears A again before returning. These are exact source
recipes, not a global census of writers or proof that every input to the
initializer belongs to a known descriptor.

At `$CD:15D5`, StartScript widens A before doubling it. With B=0, a visible
ID `i` selects the word at `$D1:646C + 2*i`; a caller with another B can
select a different long address. The selected word supplies the offset in
bank `$D1`. The routine reads the header with Y=0, keeps its low nibble as
the delay reload, writes the initial cursor as the selected word plus one
with 16-bit wrap, and marks the slot active. The cursor bank remains `$D1`.

The report enumerates all 255 hypothetical non-`$FF` byte IDs under B=0
because that is the initializer's local syntactic gate. They produce 207
distinct word roots in the pinned image. This does not identify 255 valid
scripts: some hypothetical IDs select data that has not been certified as
an entrypoint at all. The report marks every such row's reachability false
and emits no complete script-token grammar. A producer-domain census must
precede following those roots as a legal scene corpus.

The slot copies `$CA35/$CA36/$CA37` into direct-page `$40/$41/$42` and reads
through that 24-bit cursor. The initializer's bank-$D1 publication alone is
not a lifetime proof. Other command effects, pointer changes, other callers
and aliased writers must remain part of the later source and runtime audit.

## Reproduction and limits

The [read-only auditor](../tools/audit_schala_scene_dispatch_inputs_v1.py)
requires the exact 4 MiB US Rev0 source, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
It verifies ten named spans, the preserved closure reference and its source
dependencies, and the pinned upstream annotations and primary CPU sources.
The [metadata reference](../references/schala_scene_dispatch_inputs_v1.json)
contains only addresses, hashes, counts, semantic fields and explicit limits.

The prefix traversal uses 78 abstract states for the tick entry, 46 for the
standalone slot, and 45 for the post-command continuation. It tracks M/X and
known or unknown accumulator bytes, following both branch outcomes. It does
not model register-valued branch feasibility, full flags, effective memory
addresses, physical software frames, asynchronous preemption or termination.
Unknown accumulator effects, unexpected calls, unsupported status changes,
source escape, incompatible instruction widths and exhausted state budgets
refuse the requested prefix proof.

Twenty-seven original tests exercise all byte-route boundaries, all indexed
command/B pairs, pointer bank wrap, script-ID widening, unknown-B retention,
TDC recovery, both branch outcomes and fail-closed prefix boundaries. They
contain no extracted game bytes and launch no emulator. The separate v4
NMI experiment's host tests were authored during this investigation; they
belong to that experiment and supply no scene-command execution evidence.

```powershell
python -B tools/audit_schala_scene_dispatch_inputs_v1.py
python -B -m unittest discover -s tests -p test_schala_scene_dispatch_inputs_v1.py -v
```

The next finite work is to derive the allowed scene IDs from their actual
background/configuration producers, decode that rooted stream grammar, and
prove B plus M/X/D/DBR across each reachable command return. Effective-address
and saved-frame alias analysis then has a bounded target set to work with.
Every production hook, allocation, high-selector binding and PC `$07`
integration gate remains unchanged.
