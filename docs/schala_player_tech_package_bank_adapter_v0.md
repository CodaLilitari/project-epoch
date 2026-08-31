# Schala player-Tech package-bank adapter contract v0

Status: `verified-static` canonical geometry plus source-only proposal

Last updated: 2026-08-22

Production installable: no

## Result

Project Epoch now has a fail-closed host model for the narrow part of player
Tech animation loading that can safely be learned from current public work:

```text
typed PC action/config context
    -> action-config byte 0 package selector
    -> explicit (package bank, descriptor root)
    -> two exact descriptor masks
    -> bank-qualified direct script entrypoints
```

The model proves the 128 canonical package-source identities from the pinned
US Rev0 ROM without publishing their pointer payload. It reparses all 128
canonical descriptors and independently reproduces the existing payload-free
geometry totals: 125 distinct roots, three selector aliases, 900/251 mask-bit
occurrences, 1,151 direct-pointer occurrences, 841 distinct direct
entrypoints, and a 26-pointer maximum. It also proves with
synthetic data that the same 16-bit script offset in two banks remains two
different identities, that masks retain their exact bit placement and byte
order, and that a descriptor or pointer list cannot cross a 64 KiB bank. A
complete pure-host install-state model now covers both `$A0B3` alternatives,
all 16 owner bits, exact 16-bit write footprints, cursor/state/flag results,
and repeated-pointer alias preservation.

No high package selector, Schala action config, package, expanded allocation,
hook, assembler routine, ROM byte, or runtime path is bound. Animation command
`$1E` is explicitly refused for expanded packages because its separate native
subscript lookup is still fixed to bank `$CE`.

The machine-readable contract is
`references/schala_player_tech_package_bank_adapter_v0.json`. The read-only
auditor and host model are
`tools/audit_schala_player_tech_package_bank_adapter_v0.py`; focused tests are
in `tests/test_schala_player_tech_package_bank_adapter_v0.py`.

## Namespace boundary

The equal-looking numeric ranges below are not interchangeable:

| Namespace | Current range | Meaning |
| --- | --- | --- |
| Schala player-command IDs | `$80-$8F` | Sixteen named single/dual/triple Tech commands |
| Candidate Project Epoch package selectors | `$80-$8F` | An unbound policy range for possible package sources |
| PC type-2 action-config row | separately resolved | Seven-byte presentation/config record selected by the action path |
| Action-config byte 0 | package selector | Input consumed at `$C1:4612` |
| Package root | `(bank, u16 offset)` | Two-mask descriptor identity |
| Direct script entry | `(package bank, u16 offset)` | One selected owner-bit script identity |

The fact that the first two candidate ranges are numerically equal creates no
mapping. A Schala command must first resolve through a separately authored
extended action-config record; that record's byte 0 must then explicitly name
a declared Project Epoch package selector. The current v0 contract binds
neither side.

Focus Pulse command `$90` belongs to the separate PC normal-Attack
architecture. Package selector `$90` is merely undeclared; numeric equality
does not route the command into the player-Tech package reader. Likewise, the
known action/menu reservation of action ID `$FF` is not evidence that package
selector `$FF` has the same semantic role. The v0 package policy refuses it
because it is undeclared, not because the namespaces were merged.

## Canonical route and preimages

`verified-static`

The canonical PC type-2 path is:

1. `$C1:45AA-$C1:45EB` computes `AE93 * 7` and copies the seven-byte row at
   `$CD:45A6` into the `$9877` config block.
2. `$C1:4612` loads the 16-bit value at `$9877`; `$C1:4615` doubles it and
   `$C1:4617` reads one 16-bit root from `$CD:5EF0`.
3. `$C1:4623-$C1:4639` reads four descriptor-header bytes from fixed bank
   `$CE` into the two big-endian masks in DP `$80-$83`.
4. `$C1:4644-$C1:4667` consumes owner bits MSB-first and reads each selected
   little-endian script offset from fixed bank `$CE`.
5. `$C1:465F-$C1:4662` publishes the hard-coded 16-bit bank word `$00CE`
   beside each script offset in `$5DBD/$5DBF`.

The pinned spans are:

| Span | Length | SHA-256 | Role |
| --- | ---: | --- | --- |
| `$C1:45AA-$C1:45EC` | 66 | `d60ecb18fbb0e3f09194997b89e230d4876c5b3b3104e3192f97b44798686cf1` | Fixed-bank PC action-config reader |
| `$C1:4612-$C1:4682` | 112 | `a68be4a9dfa59349976827ca080eec58a5057e8144c5ba18a4609bceae291968` | Complete player package resolver/installer through its tail jump |
| `$C1:4612-$C1:4616` | 4 | `de49003154a89c179eab719b3741a288e7f53742ff31e29bc446923aa2cbd2ac` | Instruction-aligned tail-transfer candidate only |
| `$C1:4612-$C1:467F` | 109 | `32a8f05f0f64f8a3e84032cad0a6f3850e6d98730e4f26925695c9defe5e189a` | Resolver/parser core before the tail jump |
| `$C1:56CC-$C1:5714` | 72 | `a22f0cfecd41b57e14a4b2e796d581e683520734f92a8b55a66e36a6062f9575` | Commands `$1E/$1F` |
| `$CD:45A6-$CD:4926` | 896 | `2cbcd73e9b5ef64d99da2f7fe97208fb8cad245a9c8b148b52088ad5625e74d6` | 128 seven-byte physical player action configs |
| `$CD:5EF0-$CD:5FF0` | 256 | `074a9bca7aaa630085654200634002e8f3c0f251a5c3874a5b1c1237d713a4d1` | 128 canonical descriptor roots; the following byte is another table |

The auditor reads the canonical root vector only in memory. It emits these
closed identities instead of the table payload:

```text
canonical selectors:                    128
canonical package bank:                 CE
bank-vector SHA-256:                    8800a8e4e0109253ab8e82ea8119fd88
                                        ebcc17b40b1eaeb0e22c34593961ecde
root-vector SHA-256:                    074a9bca7aaa630085654200634002e8f
                                        3c0f251a5c3874a5b1c1237d713a4d1
selector/bank/root ledger SHA-256:       a88c3dd658b1d2a07b55417d9aa0eafb
                                        8c9b50efeee9d9b2f12971ced8f28343
```

## Selected architecture

`proposal`

Use a narrow high-selector adapter, not a duplicated 256-entry replacement of
the canonical resolver:

```text
package selector $00-$7F
    -> replay the exact overwritten LDA $9877 / ASL A instructions
    -> rejoin untouched canonical code at $C1:4616

explicitly declared Project Epoch package selector
    -> require a present PackageSource(bank, root, named allocation)
    -> parse the unchanged two-mask descriptor geometry
    -> publish direct script pointers with the PackageSource bank
    -> reproduce every documented vanilla side effect
    -> tail-transfer to common loader $C1:4833

every other selector or absent binding
    -> refuse before an indirect read or runtime pointer publication
```

This avoids copying the canonical `$CD:5EF0` root table into expanded ROM and
keeps the original resolver/parser instructions active for all vanilla
selectors. The four bytes at `$C1:4612-$C1:4615` could physically hold a `JML`
to a named expanded helper. That is a candidate geometry result only: no hook,
destination, return, or write is approved.

### Candidate helper ABI

At `$C1:4612`, static reconstruction establishes:

- native mode;
- `M=0`, so A is 16-bit;
- `X=0`, so X/Y are 16-bit;
- direct page `$0000`;
- DBR `$7E` for absolute WRAM operations;
- the original indirect-`JSR` return frame remains on the stack;
- `$9877` is the required package-selector word with high byte zero;
- `$A0B3` is a strict byte flag with its adjacent high byte zero; `$00`
  selects mask 0 and `$01-$FF` select mask 1; and
- the preceding action-config fields are already populated.

For an extended package, an eventual helper must reproduce at least:

- a 16-bit root write to `$9878/$9879`;
- exact big-endian header bytes in DP `$80-$83`;
- MSB-first mask consumption;
- pointer-cursor advancement for every set bit, including skipped mask-0
  entries on the alternate path;
- a 16-bit `$0001` owner activation at `$5DAC + owner`;
- a 16-bit script-offset write at `$5DBD + owner*4`;
- a 16-bit `bank,00` write at `$5DBF + owner*4`;
- initial nonzero `$A0B3` skipping mask 0, clearing `$A0B3`, and then
  publishing mask 1;
- exit with M 8-bit, X/Y 16-bit, D `$0000`, DBR `$7E`, balanced stack,
  X at the consumed-list cursor, Y `$0010`, DP `$80/$81` consumed to zero,
  DP `$82/$83` retaining mask 1, and A/B zero; and
- preservation or explicit proof for the remaining status flags. The helper
  may not borrow DP `$40-$42` or any WRAM scratch without a separate ownership
  proof.

The canonical branch obtains these effects by rejoining the original code;
it does not reimplement the 128 vanilla selectors.

## The command `$1E` blocker

`verified-static` native behavior; expanded policy `proposal`

The main battle-animation runner carries a 24-bit live script pointer and its
advance helper handles bank carry, so a direct entrypoint in an expanded bank
is structurally transportable. Command `$1E` is a separate control-flow edge:

```text
$C1:56CC    read one-byte subscript operand
$C1:56CF    multiply operand by two
$C1:56E7    read a 16-bit target from fixed $CE:0000,X
$C1:56ED    force the live script bank to $CE
```

Command `$1F` correctly restores the saved 24-bit parent pointer, but it does
not fix the entry into the nested script. An expanded direct script containing
`$1E` can therefore jump to an unrelated canonical `$CE` target while looking
superficially valid.

The v0 model does not pretend that searching raw bytes for `$1E` is enough;
an operand byte can equal `$1E`. It refuses nested resolution. Before an
expanded package can be installed, Project Epoch must choose and prove one of:

1. a lossless command decoder/census that proves every Project Epoch stream
   excludes `$1E`; or
2. a separate, bank-qualified subscript registry and `$1E` handler preserving
   all canonical operands, `$1F` return behavior, widths, DBR, DP, stack, and
   runtime timing.

## Other fixed-bank readers are separate gates

Changing the primary `(bank, root)` package reader does not make the rest of
the seven-byte action config arbitrary-bank safe:

| Config field | Native route | Remaining assumption |
| --- | --- | --- |
| byte `+3` | `$C1:45F3` reads `$D1:0060`; `$C1:4870` later selects decompression data | source bank fixed to `$D1` |
| byte `+4` | `$C1:45FF` reads `$CD:692C`; command `$60` and the tile-animation tick consume related fixed tables | fixed `$CD/$D1` auxiliary path |
| byte `+5` | `$C1:460B` reads `$CD:656E`; `$C1:48EC-$C1:4943` parses headers and later frame readers consume records | fixed `$CE` frame/header path |

Until each adapter is independently proved, an extended config may use only
already-valid canonical auxiliary selectors whose exact behavior is intended.
That can support a bounded primary-script experiment; it cannot support a
claim of original expanded graphics, auxiliary frames, or a complete Schala
Tech animation package.

## External design reference and provenance boundary

The current public lead is
[`Pseudoarc/ctrando` at commit `20609d5`](https://github.com/Pseudoarc/ctrando/commit/20609d50932a84be58f6281d23b3f4e4d4c4e167).
Its
[`apply_mauron_player_tech_patch`](https://github.com/Pseudoarc/ctrando/blob/20609d50932a84be58f6281d23b3f4e4d4c4e167/src/ctrando/base/basepatch.py#L266-L326)
allocates separate 256-entry local-root and bank tables, copies the first 128
roots from the user's ROM, and installs an opaque byte routine. The repository
has an [MIT license](https://github.com/Pseudoarc/ctrando/blob/20609d50932a84be58f6281d23b3f4e4d4c4e167/LICENSE),
but the routine is explicitly attributed as Mauron's patch and no separate
Mauron license or source provenance was found.

Project Epoch therefore adopts only independently verified behavior:

- package identity requires bank plus local root;
- direct script pointers inherit that bank; and
- the two-mask descriptor can be interpreted without flattening namespaces.

It imports none of the opaque machine bytes, copied canonical roots, dynamic
free-space choices, or hook. This is a conservative provenance classification,
not a legal conclusion.

The upstream high-level serializer is also not used as an exact preservation
oracle. It reconstructs contiguous role masks from counts and emits fresh
sequential pointers, which can discard sparse mask placement and shared-pointer
alias identity. Its companion config relocation names `$79`, `$7A`, and `$7F`
producers but does not expose source rewrites for the newly censused
`$7B-$7D` producers. Those are research leads only; Project Epoch retains its
own exact mask, alias, and producer ledgers.

## Host model and test gate

The current focused suite verifies:

- byte-pinned contract identity and duplicate-key refusal;
- every scope, namespace, command-`$1E`, auxiliary-reader, ABI, and upstream
  provenance gate;
- strict integer and symbolic allocation-name types;
- all 128 canonical selectors resolving through bank `$CE` in the model;
- all 128 canonical descriptors reparsing to the pinned payload-free topology
  counts;
- all candidate `$80-$8F` package selectors remaining unbound by default;
- explicit synthetic high-source resolution without implicit action mapping;
- refusal of `project-epoch-source` bindings until a later version names an
  approved allocation-catalog entry;
- package `$90`, `$91-$FE`, and `$FF` refusal;
- exact mask and pointer endianness;
- bank-qualified identity when two banks share the same low script offset;
- primary and alternate `$A0B3` passes, including mask-0 skip/consume before
  mask-1 publication;
- all 16 owner bits, a maximum 16-entry selected list, and repeated pointer
  aliases;
- exact 16-bit activation/script/bank publication addresses with a four-byte
  script-slot stride;
- the vanilla-shaped final cursor, mask words, accumulator/index widths, DBR,
  DP, stack delta, and `N/Z/C` state;
- an exact bank-end descriptor without wrap;
- header/pointer-list crossing, selected `$FFFF`, and descriptor-overlap
  refusal;
- unconditional command-`$1E` refusal;
- the seven canonical preimage hashes and all 128 real source identities when
  the private ROM is present; and
- deterministic stdout-only CLI output with the ROM hash unchanged.

This is host evidence, not 65C816 implementation or emulator evidence.

## Next safe step

Do not assemble or hook the adapter yet. The lossless command
grammar/canonical census is now complete in
`docs/battle_command_grammar_census_v0.md`, reusing rather than repeating the
already decoded native `$1E/$1F` handler semantics. Now freeze and prove the
expanded-package `$1E` exclusion-or-adaptation policy.
The host model now reproduces the complete vanilla-shaped
descriptor-installer state under both `$A0B3` branches and all 16 owner bits;
the next source-only extension is one symbolic synthetic high package that
uses only canonical, already-valid auxiliary selectors and proves its command
stream against that decoder.

Only after that command/package source contract passes should an original
65C816 helper be authored against the ABI above. Any later same-size ROM mutation or
patch builder must use a named expanded allocation, an approved exact hook
preimage, and the mandatory fail-closed write-intent/complete-diff audit before
writing an image or emitting a patch.

## Nonclaims

- No production hook or allocation exists.
- No canonical ROM table payload is source-controlled.
- No upstream machine-code patch is copied or licensed here.
- No high package selector is bound.
- No Schala command is mapped to a package selector.
- No animation command stream is decoded.
- No original Schala Tech package, battle sprite, menu path, save path, or
  logical PC `$07` runtime behavior is installed or proved.
