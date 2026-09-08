# Package-helper interrupt closure v1

The normal battle IRQ now has a complete, bounded static CPU control-flow
and push/pop audit. It reaches **35 bytes below the interrupted stack
pointer**, including the four-byte native hardware frame. That result is
useful for sizing a future helper, but it is not the maximum for all game
interrupts. Normal NMI has a larger reachable service tree, a scene-command
interpreter, and a separately calculated 40-byte path. NMI nesting and the
lowest safe game stack address remain open.

The principal new ownership finding is that normal NMI reads and clears the
action's effect-completion latch `$7E5D9B`. An action cancellation design
therefore has to account for an interrupt consumer. The current helper's
successful synthetic tests cannot supply that guarantee.

This report is `verified-static` only within its stated canonical-ROM and
abstract-walk scope. It makes no production hook, allocation, scratch,
expanded-ROM, eighth-PC, or save-safety approval.

## Closed IRQ graph

The native handler is `$D1FE97`, with RTI at `$D1FEF3`. Both conditional
outcomes are included in the audit, without pretending that every
combination of data conditions can occur in one actual battle.

| Call site | Target and purpose | Return convention |
| --- | --- | --- |
| `$D1FECE` | `$D1FE4C`, changed display configuration | near `JSR/RTS` |
| `$D1FE69` | `$CEEE6E`, copy nine HDMA table records | long `JSL/RTL` |
| `$D1FEDA` | `$FDFFFD`, tail jump to `$FDE022` field VRAM DMA service | long `JSL/RTL` |
| `$D1FEE6` | `$D1FE71`, restore pending hardware multiply/divide inputs | long `JSL/RTL` |

The table loader has no further call or indirect branch. The DMA service has
an ordinary direct jump to its odd-slot branch and no further call or
indirect branch. The math service has two leaf RTL paths. The complete graph
contains 401 instruction starts and 404 decoded width contexts; the extra
three contexts are the four possible entry M/X combinations at the initial
`REP #$30`.

The original auditor
[`audit_schala_package_interrupt_closure_v1.py`](../tools/audit_schala_package_interrupt_closure_v1.py)
tracks M, X, and I; known PHP/PLP status values; software push widths; and
the exact pairing of near and long return frames. It rejects unknown
instructions, unsupported control flow, an unknown PLP value, an instruction
leaving the declared code spans, an unbalanced RTI, a pop into a call frame,
or IRQ unmasking. The walk finds one balanced RTI context and no path that
clears I. It is not a value-level CPU emulator: DMA pointers, memory values,
cycle timing, and asynchronous interrupt entry are outside its model.

The 35-byte maximum occurs after the eighth temporary word push in the
display-table loader. `$CEEEAE` is the first convenient observation point;
the same depth persists until the first pointer pop at `$CEEEC2`.

| Contribution on that path | Bytes |
| --- | ---: |
| Native interrupt frame | 4 |
| Handler saves A, X, Y, DBR, D | 9 |
| Near call to display-change service | 2 |
| Long call to table loader | 3 |
| Table loader saves DBR | 1 |
| Eight temporary word pointers | 16 |
| **Total** | **35** |

The other IRQ branch reaches 23 bytes including hardware entry: the handler
frame (13), an outer PHP and JSL (4), the DMA service's PHP/PHD/PHB (4), and
its temporary PHX used to set D (2). The original static walker determines
the common 35-byte bound across both branches; the 23-byte breakdown is a
reviewed path calculation, not a separately reported runtime measurement.

The reviewed direct CPU destinations in these services do not target helper
scratch `$7E4000-$7E4021`, DP `$0080-$0083`, or package publication
`$7E5DAC-$7E5DFC`. The display loader writes its explicit `$7EC867` through
`$7EC9EC` table destinations in nine separate 30-byte blocks. The field DMA
service changes D to `$0500`; its apparent DP operands belong to `$05xx`,
not `$00xx`. This is a scoped source interpretation, not an automated
all-memory proof. In particular, DMA source reads are selected from existing
field state and are not certified by the control-flow walker.

## Normal NMI frontier and a shared lifecycle field

The native NMI saves the same nine register bytes after the four-byte
hardware frame, selects D=0, and copies DP `$00-$2A` to `$7ECC65` before
running its full body. Its epilogue restores that same 43-byte range. No
blanket preservation of DP `$80-$83` follows from those block moves.

The first service is mode dispatch at `$CD0C95`. The exact three table
entries at `$CD0C83` are:

| DP `$7E` mode | Encoded target |
| --- | --- |
| `$00` | `$CD09F1`, CGRAM/HDMA setup path |
| `$01` | `$CD088D`, regular NMI body |
| `$02` | `$CD088D`, the same regular NMI body |

The caller does not clamp DP `$7E` at the indirect call `$CD0C99`. These are
three proved encoded entries, not proof that every possible mode byte is
safe or that their predecessors always constrain it correctly.

The regular body calls queued DMA, battler display work, frame updates,
scene scripts, raster services, palette animation, and input services. A
particularly relevant path is:

```text
D1E77C normal NMI
  -> D1E7DA JSL CD0C95
     -> CD0C99 indexed JSR, mode 1/2 -> CD088D
        -> CD09AF JSR CD1609 (scene scripts)
           CD160E reads $7E5D9B
           CD164D clears $7E5D9B when both scene slots are inactive
           CD16AF dispatches scene commands through an indexed JSR
```

The scene interpreter uses a separate long pointer at DP `$40-$42`, a
saved slot index at `$43-$44`, and mutable per-scene records at `$CA32` and
`$CA42`. Its command dispatch and source-lifetime closure are not included
in this IRQ audit. The action helper must not infer exclusive ownership of
the completion latch from the main caller's reads alone.

Another regular-NMI path calls `$CD05B2` twice for screen transitions. If
its negative transition state is exactly `$FF`, it calls the same
`$CEEE6E` table loader as IRQ. The path's stack contribution is 40 bytes:
13 for hardware/register entry, 3 for mode-dispatch JSL, 2 for its indexed
JSR, 2 for the transition JSR, 3 for the loader JSL, and 17 for loader saves
and temporary pointers. This establishes a concrete deeper conditional
path; it does not establish the deepest possible NMI path or that this path
occurs at the observed resolver checkpoint.

An NMI entering while IRQ's DP `$7F` busy flag is nonzero takes the short
register-save/restore path, adding 13 bytes. Thus IRQ's 35-byte peak plus
that particular guarded NMI is 48 bytes. Leading and trailing windows
around the busy-flag update can instead enter the full NMI. The result must
not be generalized to a 48-byte global nesting maximum.

## Alternate NMI and temporary DBR

The alternate NMI at `$D1F4C0` calls CGRAM upload `$CD09CE` at `$D1F4DE`
before assigning DBR at `$D1F4F4`. The upload service uses absolute hardware
register accesses. Saving and restoring DBR in the handler is therefore
insufficient to prove that its *callee* works with an arbitrary incoming
source bank. This is a dependency on the caller's bank context, not proof
that the vanilla handler is broken.

Normal NMI and normal IRQ establish the required bank before their relevant
absolute accesses, as recorded in the
[placement review](schala_package_placement_interrupt_review_v0.md). A
future source-bank helper must either prove that the alternate handler
cannot be installed during the helper's lifetime or establish a separately
reviewed bank-independent integration contract. The observed normal
trampolines at one checkpoint cannot settle all mode transitions.

## Stack-local helper alternative

The original helper uses 34 scratch bytes at offsets `$00-$21`, eight saved
context bytes, and a deepest local JSR of two bytes. A straightforward new
stack-relative implementation with the same 34-byte working frame would
therefore require **44 bytes below helper entry SP**, before interrupts.
This calculation assumes a deliberate source rewrite; the current v0 code
does not allocate or access such a frame.

For the already observed vanilla entry SP `$06D8`, that hypothetical helper
alone would reach `$06AC`. Combining it with the closed IRQ bound would
reach `$0689`; adding a guarded nested NMI would reach `$067C`. These are
arithmetic planning examples, not free-space or runtime safety evidence.
The larger normal-NMI tree, repeated resolver callers, existing stack
contents, and the lowest permitted stack address still need evidence.

Stack-relative loads/stores can avoid selecting a new direct page and avoid
a persistent WRAM scratch allocation. They also require careful handling
of the changing stack depth at local JSRs and temporary bank pushes. A
callee must not use caller-relative local offsets unless the additional
return frame is included. The source rewrite must preserve the original
canonical and success/refusal ABI, including the saved status position and
exact return-frame shape. It does not resolve publication ordering, the
effect-latch lifecycle, or temporary source-DBR obligations by itself.

## Mapping correction: two false `$AAEB` writes

The private unmodified `dscotton/ct_disassembly` checkout is pinned to
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`. In
[`bank_FD.asm`, lines 6032-6033](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_FD.asm#L6032)
and
[lines 6050-6051](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_FD.asm#L6050),
the unannotated odd-slot tails label `$FDE21B` and `$FDE247` as an
eight-bit `AND #$00`, followed by `ASL $AAEB`.

That interpretation is incorrect on the audited IRQ entry path. `REP #$21`
at `$FDE160` selects M=0. Neither path changes M before these instructions.
The canonical five-byte spans decode as a 16-bit `AND #$0E00`, then `XBA`,
then `TAX`. `$FDE21D` and `$FDE249` are operand bytes within their preceding
three-byte instructions, not instruction starts. Neither sequence writes
to `$AAEB`. Treating the older annotation as a write would create a false
interrupt/scratch collision.

Both corrected half-open spans, `$FDE21B-$FDE220` and
`$FDE247-$FDE24C`, independently hash to
`ea507cc8d6ab6f2681420c5099a90369d6f0ef195c8e1b6a82b3075464391a4a`.
The ROM-pinned width-aware walk reaches both with M=0 and X=1 and reports
all six actual instruction boundaries. This is an upstream width-decoding
correction, not a new gameplay meaning for `$AAEB`.

## Provenance, verification, and handoff

Canonical input is the private 4,194,304-byte headerless US Rev0 ROM with
SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The auditor verifies that full identity first and then verifies every named
half-open canonical span. The generated
[metadata reference](../references/schala_package_interrupt_closure_v1.json)
contains exact span hashes, original auditor identity, counts, call edges,
width witnesses, and explicit scope limitations. It contains no ROM or
script bytes.

The source checkout was clean when inspected. The relevant source-file
identities are:

| Private source | SHA-256 |
| --- | --- |
| `bank_D1.asm` | `020f6df9efd22cc12a35608da6523b5d2e5d76d965d94567e0b74d50ab9eacea` |
| `bank_CD.asm` | `0d230620c6accf311c0588e2fefaf3bcc48b0d42575f3745fec3a402a6ca19fb` |
| `bank_CF.asm` | `f2783556f4963cbeb75b320c996a3fd8e5da6d435009aa8c1516086c65ed02a6` |
| `bank_CE.asm` | `23b885667ad4f454ed95f4d441253378cb40964c3e2d543120f5f9c1288a35ad` |
| `bank_FD.asm` | `0f8a0d59e97de7d60945fdfef1b614217e3d673cca1e14f543234d789a87779e` |
| `bank_C0.asm` | `b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8` |

Reproduce the metadata-only audit with:

```powershell
python -B tools/audit_schala_package_interrupt_closure_v1.py
python -B -m unittest discover -s tests -p test_schala_package_interrupt_closure_v1.py -v
```

The focused suite has 15 passing tests using original tiny instruction
fixtures. It checks width-dependent boundaries, 16-bit register pushes,
PHP/PLP recovery, near/long frame sizes, exact return-frame integrity,
unbalanced returns, unsupported instructions, out-of-bounds control flow,
and fail-closed rejection of noncanonical ROM input.

The next useful evidence is a context-attributed normal battle trace with
paired hardware entry/RTI frames, full emulator master-clock timestamps,
minimum observed SP, actual mode/scene dispatch values, and every access to
the proposed temporary/publication fields. That trace narrows the remaining
NMI frontier; it does not promote a finite untouched memory window to global
ownership. Root owns that independent collector and its evidence record.
