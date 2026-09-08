# Schala symbolic high package v0

Status: `complete-static`

Gate: `BA-SYMBOLIC-HIGH-PACKAGE`

Evidence ceiling: `verified-static`, source-only synthetic package and host
descriptor transport. No runtime evidence is claimed.

The first symbolic player-Tech package now passes the closed flat-direct
command policy under one explicit local selector `$80` mapping. It combines
an original eight-byte descriptor and one terminal command with a privately
reconstructed canonical action-config donor. The default production high
selector registry remains empty, and no Schala action selects this package.

Implementation:
[`tools/audit_schala_symbolic_high_package_v0.py`](../tools/audit_schala_symbolic_high_package_v0.py)

Closed reference:
[`references/schala_symbolic_high_package_v0.json`](../references/schala_symbolic_high_package_v0.json)

Focused verification:
[`tests/test_schala_symbolic_high_package_v0.py`](../tests/test_schala_symbolic_high_package_v0.py)

## Exact synthetic source

The only explicit local binding is a `synthetic-test` `PackageSource` for
selector `$80`, bank `$42`, descriptor root `$2000`. These are synthetic
identities. They do not reserve or approve production addresses, ROM banks,
or allocations.

| Named span | Synthetic bank | Half-open offsets | Size | Meaning |
| --- | --- | --- | --- | --- |
| `EPOCH_PKG80_SYMBOLIC_DESCRIPTOR_V0` | `$42` | `$2000-$2008` | 8 | Two masks and two direct pointers |
| `EPOCH_PKG80_SYMBOLIC_STREAM_V0` | `$42` | `$3000-$3001` | 1 | One original terminal command `$00` |

Both big-endian descriptor masks are `$8000`, selecting owner slot zero on
their respective branches. Both little-endian direct pointers select the
same bank-qualified entrypoint `$42:3000`. There are two descriptor pointer
occurrences, one distinct direct entrypoint, and one repeated-pointer alias.

The existing policy independently validates both descriptor branches and
decodes each distinct direct entrypoint. Its trace count is consequently one,
with one token, one owned stream byte, and one terminal `$00`. Its
`shared_token_start_count` is zero because that field counts sharing among
distinct independently decoded entrypoints. It does not count repeated
descriptor relations to the same entrypoint.

Every declared stream byte is token-owned. There are no decoded `$1E`, `$1F`,
or `$21` commands, no descriptor/stream overlap, no unowned stream bytes,
and no graphics, effects, sound, or gameplay commands. This deliberately
minimal source proves bank-qualified selection, transport, and closure.

The full immutable 64 KiB synthetic bank envelope is checked for exact
equality, including zero filler outside the two named spans. That filler is
test scaffolding only; zero bytes establish no free-space claim. The image
is constructed in memory and is never emitted or installed.

## Canonical config donor and preservation

The auditor requires the exact headerless US Rev0 ROM: 4,194,304 bytes,
SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The default input is the ignored local file
`private/input/rom_archive/Chrono Trigger (USA).sfc`.

The deliberately selected donor is physical player action-config row `$01`
from the seven-byte-row table at file `$0D45A6`. Its exact source span is
`$0D45AD-$0D45B4`, half-open. The full canonical ROM identity and the existing
adapter's seven canonical reader/table spans are verified before the report
can pass.

Only donor byte `+0` is replaced with package selector `$80`. Bytes `+1`
through `+6` must remain exactly equal, including the independently fixed-bank
auxiliary selectors at `+3`, `+4`, and `+5`. The report gives byte-offset
equalities and hashes without disclosing any canonical donor values or
adapted row bytes.

| Content | SHA-256 |
| --- | --- |
| Canonical seven-byte donor row | `d64477971e5fa2a0d679810b37ad90412615d49786671b71ec6aea209bd61313` |
| Preserved bytes `+1` through `+6` | `cf2dfb5466e64043a0995b97e825a9633d3f68890e1df2a5ac229ed8506e21c7` |
| Seven-byte config after only `+0` substitution | `88430e3592fe6cd2781c39854771c87bfb458b0557951a6317c974faea316733` |

Preserving these canonical values is a source-level equality result. It does
not prove their compatibility with Schala at runtime or implement new
auxiliary readers. Config `+3` still refers to the fixed `$D1` family;
`+4` retains its fixed `$CD/$D1` consumers; and `+5` retains its fixed `$CE`
consumers. Their existing contract is copied as metadata from the pinned
package-bank adapter, with its unresolved/runtime-false boundary intact.

The donor row is not written back to the ROM, and no action table is extended
or changed. The donor's row index, the candidate package selector, Schala
action IDs, and logical PC `$07` remain distinct namespaces.

## Host transport and default refusal

The proof checks all 256 possible `$A0B3` flag-byte inputs against explicit
complete expected host states. Zero selects mask 0; every nonzero input
selects mask 1. Both branches publish exactly one identical bank-qualified
direct pointer. The native-shaped host model records the exact activation,
script-offset, and bank-word footprints, final mask/cursor/register fields,
cleared `$A0B3`, and balanced stack. No WRAM write actually occurs.

The namespace check also proves:

- all 128 canonical selectors resolve identically with and without the
  explicit local synthetic mapping;
- all 16 candidate high selectors `$80-$8F` refuse when no mapping is passed;
- passing the explicit local mapping binds only `$80`, while the other 15
  candidate selectors continue to refuse;
- the default extended registry is empty;
- expanded command `$1E` continues to raise its explicit refusal.

This advances the source-only package gate. It leaves the production registry
empty and does not bind any action, Tech, item, animation, sprite, or PC.

## Closed dependencies and report identity

The source pins the policy implementation and reference. The policy in turn
pins the grammar and package-adapter implementations and contracts, plus the
complete 511-row grammar token-shape profile. An unexecuted grammar opcode
changing shape therefore fails before this one-command package can pass.

The new reference is byte-pinned and checked against its complete expected
metadata, with type-sensitive canonical JSON equality. Unknown fields,
changed evidence/scope claims, and boolean/integer substitutions fail closed.
The report includes its current auditor source identity, reference identity,
ROM identity, exact source-content hashes, decoder proof, and complete host
state ledger. Its artifact hash covers all these fields and excludes only the
self-referential `artifact_identity` field.

| Artifact or proof | Size if applicable | SHA-256 |
| --- | --- | --- |
| New auditor source | 20,486 bytes | `e6911a979a60cb06ee78b4b58a410875a2b7acbeb2fce4733bf2795828ad2b5d` |
| New closed reference | 8,164 bytes | `37c13271c3632bca6b27a2daa0e5e2820d502a6673b1863b64b29a647df470e2` |
| Synthetic bank envelope | 65,536 bytes, memory only | `d1d085d52aade99d212e033f498f2626ca83994de7512fa6206bf3e478e1afd3` |
| Original descriptor | 8 bytes, memory only | `618d615e6ee39b40aedce9a7764be19aebaa37e996211e68b58c09333a854313` |
| Original terminal stream | 1 byte, memory only | `6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d` |
| Policy exclusion proof | metadata | `13cfc9f9175d61e173f133e171dd5199d1c65cfe73cbf5fdc7af826de4bbf209` |
| All-256-input host state ledger | metadata | `6c66e852d31b4ce9e59472a94c2d3256ec8370b15d77d3cb0024eac2eb3b206d` |
| Report canonical artifact identity | metadata | `dcae013742fea5d0b70acffe80a7d8a174e23d72504d7dba28899382e17a8965` |
| Compact stdout on verified Windows runtime | 9,188 bytes, includes final CRLF | `28693283ecc44bce8a60731fe9fc79a01ad1d8e2dcfbf67828995f7ce9382b6e` |

The policy dependency reflects the separately audited descriptor-bank-end
correction: its adapter now preserves the physical one-past cursor while
wrapping native 16-bit `X`. The symbolic `$2000/$3000` geometry is unaffected.
Its final policy source hash is
`5f9417cb5c44d6dd71577bcd48de0a3c90c9d7f2b790c57a26d1e8c4bd5b5c3f`,
and its policy reference hash is
`35246c00e274f35a80cfe589cfe3557b7585ff515c7e43747453d161de99f0d9`.

## Reproduction and actual verification

From the workspace root, using the ignored canonical input at its default
path:

```powershell
py -B tools/audit_schala_symbolic_high_package_v0.py --compact
py -B -m unittest tests.test_schala_symbolic_high_package_v0 -v
```

An exact alternative local ROM path may be supplied with `--rom`. The ROM
must still pass the same full identity check. There is no output-file,
installation, patch, or assembly option.

The focused run on 2026-09-08 passed all **24 tests**, with zero failures,
errors, or skips. Coverage includes actual canonical donor reconstruction,
every preserved-byte mutation, wrong donor and primary-selector refusal,
ROM/reference/source/interpreter drift, exact layout and full-bank envelope,
both descriptor masks and all 256 flag inputs, default high-selector refusal,
canonical equivalence, nested-command refusal, complete report identities,
payload-free output checks, and error paths with empty stdout.

Two compact CLI runs produced identical stdout and empty stderr. The actual
ROM's SHA-256, size, and modification timestamp remained unchanged. Test runs
use `-B`, and the auditor creates no output files.

## Remaining boundary

This gate supplies one proved original symbolic primary package and an exact
canonical donor-preservation contract. It does not authorize an original
65C816 helper, choose a production allocation or hook, or prove runtime
interrupt, scratch, graphics, auxiliary, save, or logical PC `$07` behavior.
Any later helper or integration requires its own reviewed source contract
and evidence before production placement or emulator integration.
