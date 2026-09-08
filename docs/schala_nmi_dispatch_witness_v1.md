# Native NMI dispatcher snapshots reused against the input contracts

Date: 2026-09-08. Status: bounded `verified-runtime` evidence reuse;
independent packet review and exact reproduction passed. No emulator was launched for this audit.
It revalidates both accepted context traces and both new static input
references before deriving the following metadata.

The accepted Lavos-checkpoint observation contains 1,201 paired normal-NMI
entries and pre-RTI snapshots per run, with exactly one recorded outer-mode
dispatch in each pair. All 1,201 use mode `$01`. At `$CD:0C99`, every observed
CPU has A=X=`$0002`, Y=`$CC90`, D=0, DBR=0 and native M1/X0/I1. Those values
agree with the [static caller/input contract](schala_nmi_mode_inputs_v1.md).
The indexed instruction's canonical cell selects `$CD:088D`; the observer
did not record that pointer's CPU bus reads or the target's entry instruction.

Each mode snapshot also retains twelve bytes above SP. All 1,201 exact
snapshots match the three-byte return of the pinned `$D1:E7DA` JSL followed
by the nine saved A/X/Y/DBR/D bytes from that same NMI's entry registers.
The mode SP is twelve bytes below the recorded entry SP. Entry is already
after the native hardware frame, so this measurement is consistent with
the separately stated sixteen-byte contribution below the interrupted main
SP; it is not another four bytes on top of sixteen.

The same source contains 3,097 scene-dispatch snapshots at `$CD:16AF`,
inside 657 of those NMI contexts. All recorded A/X values agree, are even
and lie in `$0000-$00FC`; B is zero, D=0 and DBR=`$7E`, under native M1/X0/I1.
Their SP is 24 bytes below the corresponding recorded NMI-entry SP. The
other 544 observed NMIs have no scene-dispatch record. Among contexts with
scene dispatch, counts range from one through twenty observations.

Applying the separately reviewed scene classifier and eight-bit-shift
recipe reconstructs 44 distinct command-byte values in this particular
trace. The metadata retains their complete histogram and static cell/target
projection hashes. This is a reconstruction from pre-indexed-call CPU
registers and pinned code, not a record of stream-byte fetches. It does not
certify a legal corpus of 44 commands, every selected handler's return
contract, all scene lifetimes, or a complete global input domain.

The [scene-input contract](schala_scene_dispatch_inputs_v1.md) proves B=0
statically only for the first indexed call reached after tick setup. The
native snapshots add evidence that B also happened to be zero at all later
observed calls in this bounded replay. They do not turn that observation into
a theorem about arbitrary handler returns or other scenes.

The lowest sampled mode SP is `$06B5`; the lowest sampled scene SP is `$06A9`.
Neither is a complete low-water measurement: the observer samples selected
instructions rather than every stack access. No free stack reserve, memory
alias ownership, helper preemption, alternate mode, or production allocation
follows from these values. The accepted pair's full context validator still
checks matched entry/pre-RTI registers and hardware-frame snapshots first.

## Reproduction and provenance

The [read-only auditor](../tools/audit_nmi_dispatch_witness_v1.py) imports
the preserved accepted-context collector and regenerates its reference
exactly. It verifies current source identities and all original run-input
and manifest dependencies before reading the pinned traces again. Each
trace has SHA-256
`6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679`.
Both static input references are also regenerated exactly from the canonical
ROM and their pinned CPU/disassembly sources before any target recipe is used.

The [metadata reference](../references/nmi_dispatch_witness_v1.json)
binds selected complete records, their zero-based ordinals, every mode and
scene projection, and their containing entry/pre-RTI relationships by SHA-256.
It records the original two run manifests and source identities. No raw
trace, ROM, SRAM, state, extracted stream or cartridge payload is emitted.
Private historical artifacts remain unchanged.

Twenty-two original host tests use abbreviated selected-record specimens.
They test exact register/context/stack types, every one of the twelve saved
frame bytes, parent/child order, clock/cycle consistency, mode and scene
widths, hidden-byte and index limits, source-cell substitution, and explicit
absence of global claims. These specimens do not pass themselves off as
native traces; the public collection path always requires the full accepted
context proof before invoking the selected-field projection.
The independent reviewer passed all 22 tests, revalidated both complete
accepted context runs and both static input references, and reproduced the
9,693-byte output exactly, SHA-256
`e84739ef37b32812491b9166bf1f706a8d3490a3bf1810b3a4296c5305f47e20`.

```powershell
python -B tools/audit_nmi_dispatch_witness_v1.py
python -B -m unittest discover -s tests -p test_nmi_dispatch_witness_v1.py -v
```

The original [context-observation report](schala_package_resolver_context_v1.md)
remains the authority for what its collector actually watched. The new
packet supplies a bounded connection to the static mode/scene mappings.
The next work remains selected-callee and producer-domain closure, a
complete physical alias/stack policy and separately proved integration.
