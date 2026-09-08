# Stop, default command and the two completion waits

Status: `verified-static` in the declared native M=1, X=0, D=0, DBR=$7E,
binary-arithmetic contract. This is a bounded interpretation of the canonical
US Rev0 bytes and a source-policy intersection, not a new native experiment.
Independent review checked the canonical handler, advance and caller
instructions, reproduced the audit and passed all twelve tests. The existing
v0 authoring policy is unchanged.

The terminal-only symbolic package is useful for proving pointer transport,
but its `$00` stream cannot by itself release the observed caller's package
wait. At `$C1:4CF0`, command `$00` clears the selected owner's `$5DAC,X`
active byte. It neither increments `$9876` nor advances the command pointer.
The caller reads `$9876` at `$C1:40CE` and continues its package loop when
that byte is zero. It separately waits for `$5D9B` to become zero at
`$C1:40E7`. The already accepted primary observation supplies runtime evidence
for those caller reads; this audit adds no newly executed CPU evidence.

The default handler at `$C1:4CF7`, used by command `$01` and 69 other encoded
commands, has a different contract. When `$A3D1` is zero, it increments the
byte `$9876` and returns. It leaves the owner active and the stream pointer
on the same command. Because this is a byte increment, `$FF` wraps to `$00`;
the model does not turn the counter into a Boolean success flag. A nonzero
counter also does not clear the independent scene wait.

When `$A3D1` is nonzero, the handler executes `TDC` and jumps to the pointer
advance helper at `$C1:75BB`. Under the declared D=0 contract, the advance
amount is zero. `REP #$21` widens A and clears carry; adding zero to the low
pointer word cannot set carry. The following high-word add is therefore
also zero. The pointer does not move, and `$9876` is not incremented.
The helper nevertheless performs two same-value 16-bit stores at direct-page
`$E6` and `$E8`, covering `$E6-$E9`. Those real writes are not erased from
the interpretation just because the selected semantic state is unchanged.

This contradicts the default-handler annotation's claim that the `$A3D1`-set
branch consumes the command. The exact wrong source is
[`dscotton/ct_disassembly`, commit `eeae27acdb6565e96d1d796a3d60792c250c0aa1`,
`bank_C1.asm:9969`](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L9969).
Its 2,768,817-byte file has SHA-256
`298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa`.
The original annotation remains unchanged in the private source checkout.
MAP-011 records the correction with this scope and provenance.

The dispatcher resets `$A00F` before calling a command and uses it to decide
whether to dispatch again immediately. Neither of these two handlers sets
that flag. Their return is not an implicit command-pointer increment. The
separate canonical setup clears `$9876` at `$CC:F0E9`.

| Selected operation | Owner active | `$9876` | Pointer | `$5D9B` |
| --- | --- | --- | --- | --- |
| `$00` | Cleared | Preserved | Preserved | Preserved |
| `$01`, `$A3D1=0` | Preserved | Incremented modulo 256 | Preserved | Preserved |
| `$01`, `$A3D1!=0`, D=0 | Preserved | Preserved | Preserved through same-value DP stores | Preserved |

The current decoded-command v0 policy allows 123 opcodes. Reusing its pinned
grammar and canonical 219-word dispatch table shows that all 70 opcodes whose
direct handler is `$4CF7` are excluded. The policy also requires terminal
`$00`. This establishes that its direct default-handler completion route is
unavailable. It does **not** prove that none of the other 123 allowed commands
can affect completion through another direct, indirect or aliased writer.
That wider side-effect census has not been supplied by this audit.

A future completion design must therefore establish the intended signal and
scene lifecycle explicitly. Merely replacing `$00` with `$01` would violate
the current authoring policy and would retain a sticky command pointer.
This receipt approves no replacement stream, policy extension, native
diagnostic, cleanup destination, game hook or allocation. The preflight
planner's action-completion approval remains false.

## Reproduction and evidence boundaries

The [read-only auditor](../tools/audit_schala_package_completion_contract_v1.py)
requires the exact 4,194,304-byte clean ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
It checks seven named half-open spans and 31 selected instruction/operand or
branch assertions. It reuses the frozen command grammar and authoring policy
rather than introducing an independent opcode-width interpretation.
The [metadata reference](../references/schala_package_completion_contract_v1.json)
records every span hash, dependency identity and original semantic example.
No game bytes are emitted by the auditor or stored in this report.

| Half-open CPU span | Bytes | Purpose |
| --- | ---: | --- |
| `$C1:4CF0-$C1:4CF7` | 7 | Owner stop |
| `$C1:4CF7-$C1:4D04` | 13 | Default handler and counter increment |
| `$C1:75BB-$C1:75CC` | 17 | Pointer addition and same-value stores |
| `$C1:4CBF-$C1:4CEF` | 48 | Dispatcher and immediate-repeat control |
| `$C1:40CE-$C1:40D3` | 5 | Package-counter wait |
| `$C1:40E7-$C1:40EC` | 5 | Scene wait |
| `$CC:F0E9-$CC:F0EC` | 3 | Counter initialization |

The host model checks all 65,536 mode/counter pairs. Twelve original tests
exercise zero-advance pointer boundaries, byte wrap, independent latch waits,
preservation of existing state, immutable exact types, noncanonical source
refusal and the explicit D/decimal premises. These tests validate the bounded
model and its refusal behavior; they are not 65,536 native CPU observations
or an independent ISA emulator. An initial test incorrectly expected the
valid Boolean `processor_decimal=False` premise to be rejected alongside
integer/float aliases; the test was corrected, with no implementation change.

```powershell
python -B tools/audit_schala_package_completion_contract_v1.py
python -B -m unittest discover -s tests -p test_schala_package_completion_contract_v1.py -v
```

The CLI emits UTF-8 JSON with two-space indentation, LF and one trailing
newline. Generated metadata can be compared byte for byte with the reference.
All production catalogs, source bindings and existing native proofs remain
unchanged.
