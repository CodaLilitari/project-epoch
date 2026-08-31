# Project Epoch battle-command grammar and canonical stream census v0

Status: `verified-static`; `BA-CMD-GRAMMAR-CANONICAL-CENSUS` complete

Last verified: 2026-08-31

Canonical input: Chrono Trigger US Rev0, headerless

Runtime evidence: none in this tranche

## BLUF

Project Epoch now has a lossless, bank-qualified command grammar for the full
byte domain `$00-$FF` and a closed static tokenization of every direct battle
animation stream selected by the previously audited canonical package
topology. The auditor follows every canonical command `$1E` target through the
fixed `$CE` subscript table and verifies shared-token agreement, nonoverlapping
token ownership, bounded termination, and exact metadata ledgers.

The closed result covers 2,173 direct entrypoints, 59 nested entrypoints,
31,655 distinct token starts, and 58,960 owned bytes. It found no nested
`$1E`, no canonical `$80` zero-nibble case, and no `$DB-$FF` marker inside the
audited closure. All 59 nested **forced-fallthrough** traces reach `$1F`; 24 of
those traces contain conditional-return command `$21`, so this is deliberately
not described as proof that every runtime path executes through to `$1F`.

One canonical stream has a genuine four-byte dual-use relation with one
selected package descriptor. Two command tokens start in those descriptor
bytes. That is not a token-overlap error, and it is emphatically not free
space: the exact relation is hash-pinned so that any additional or altered
descriptor/stream intersection fails closed.

This gate does **not** approve an expanded package, high package selector,
command `$1E` rewrite, production hook, allocation, logical PC `$07`, Schala
Tech, or battle runtime. The next gate is
`BA-CMD-1E-FINAL-EXPANDED-POLICY`.

## Artifacts

The implementation consists of:

- `tools/audit_battle_command_grammar_census_v0.py`, the read-only auditor;
- `references/battle_command_grammar_census_v0.json`, the exact closed
  expected-result contract;
- `tests/test_battle_command_grammar_census_v0.py`, synthetic negative
  controls, canonical checks, privacy checks, and deterministic CLI coverage.

The reference contract is 12,433 bytes with SHA-256
`1582aca15e209d8015d5c34fdf4016ee45e75d9872ff76f4933e29f80ce46e0c`.
It stores counts, classifications, and cryptographic ledgers only. It contains
no ROM bytes, command streams, direct-root rows, pointer rows, saves, states,
traces, patches, or extracted game assets.

## Evidence and derivation hierarchy

The command-width vector is not inferred merely because canonical streams
happen to terminate. Its authority and cross-checks are kept separate:

1. The pinned canonical dispatcher, complete command-handler corpus, pointer
   advance routine, 219-word dispatch table, fixed `$CE` subscript table, and
   focused irregular-width witnesses are the byte-level authority.
2. The 219 dispatched widths are a reviewer-encoded static interpretation of
   that pinned canonical handler corpus. Handler sharing and eventual pointer
   deltas are retained in the metadata grammar. The 37 dispatcher-exit values
   `$DB-$FF` are classified from the dispatch boundary, not invented as
   handlers.
3. The canonical stream closure cross-checks the interpretation wherever an
   opcode appears. It does not independently prove the 92 dispatched opcodes
   absent from this possible-context corpus; their authority remains the
   static handler analysis.
4. The community parser in
   [Pseudoarc/ctrando at commit `20609d5`](https://github.com/Pseudoarc/ctrando/blob/20609d50932a84be58f6281d23b3f4e4d4c4e167/src/ctrando/attacks/animationcommands.py)
   was used as a comparison lead only. It was not executed, imported, or
   accepted as canonical authority. Disagreements were resolved against the
   pinned ROM handlers.

The full handler-corpus and dispatch-table hashes make later byte drift
detectable. They do not automatically derive semantics; that distinction is
recorded in both the reference limitations and each emitted grammar row's
`width_authority` field.

## Dispatcher and control-flow contract

The dispatcher accepts command values `$00-$DA`. Values `$DB-$FF` leave the
dispatch loop without indexing the table or advancing the pointer. Within the
dispatched domain there are 115 distinct handler families; 13 are shared by
multiple opcodes, no shared family has conflicting owned widths, and 70
opcodes resolve to the default sticky handler.

The grammar uses these flow classes:

| Opcode/family | Owned width | Static flow model |
| --- | ---: | --- |
| `$00` | 1 | stop current script |
| default-handler opcodes | encoded width, normally 1 | sticky terminal; no pointer advance |
| `$1E` | 2 | call fixed-`$CE` subscript and preserve parent continuation |
| `$1F` | 1 | restore saved 24-bit parent pointer |
| `$21` | 1 | conditional fallthrough or restore saved parent |
| `$25` | 2 | conditional fallthrough or stop current script |
| ordinary dispatched opcode | encoded width | eventual sequential fallthrough |
| `$DB-$FF` | 1-byte marker classification | dispatcher-exit sticky terminal |

“Eventual” matters. Wait and conditional handlers do not necessarily advance
on every invocation. The grammar records the consuming extent used when their
fallthrough path advances; it is not a per-frame timing model.

### Command `$80`

Command `$80` is the sole variable-owned-width opcode. Let `N` be the low
nibble of the first following byte:

- when `N > 0`, the command owns `N + 1` bytes total;
- when `N == 0`, the decrement loop wraps and reads 256 following bytes while
  the computed pointer advance remains one byte. The token therefore owns one
  byte and carries a 256-byte read-lookahead dependency.

The canonical closure contains 289 `$80` sites: 34 own two bytes, 200 own
three, and 55 own six. It contains no zero-nibble instance. The zero case is
still modeled and tested because a future authored stream must not silently
turn it into an ordinary one-byte no-op.

### Command `$DA`

Command `$DA` owns one byte but reads relative byte `+1`. The following byte
can simultaneously be the next token's owned byte. Ownership and read
dependency are therefore separate concepts. All 88 canonical `$DA` sites
retain that lookahead without falsely absorbing the next token.

## Complete owned-width grid

Each numeric cell is the total owned width in bytes. `N+1*` is command `$80`
with the zero-nibble exception described above. `M` means a one-byte
dispatcher-exit marker classification, not a dispatched handler.

| High | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0x | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 1x | 3 | 1 | 2 | 4 | 2 | 3 | 3 | 1 | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 1 |
| 2x | 2 | 1 | 3 | 2 | 2 | 2 | 3 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 3x | 3 | 2 | 2 | 2 | 2 | 1 | 1 | 2 | 1 | 1 | 3 | 2 | 2 | 2 | 2 | 2 |
| 4x | 2 | 3 | 2 | 4 | 1 | 2 | 2 | 2 | 2 | 3 | 1 | 1 | 1 | 1 | 1 | 1 |
| 5x | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 |
| 6x | 2 | 4 | 4 | 4 | 4 | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 3 | 1 | 1 | 1 |
| 7x | 1 | 1 | 2 | 2 | 2 | 2 | 3 | 2 | 2 | 2 | 3 | 3 | 1 | 1 | 1 | 1 |
| 8x | N+1* | 2 | 2 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 9x | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 3 | 2 | 3 | 2 | 3 | 2 | 1 | 1 |
| Ax | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| Bx | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Cx | 5 | 4 | 5 | 4 | 3 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Dx | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 3 | 4 | 2 | 1 | M | M | M | M | M |
| Ex | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |
| Fx | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M | M |

The fixed-width distribution across the full byte domain is 168 one-byte, 56
two-byte, 20 three-byte, nine four-byte, and two five-byte entries, plus the
single variable `$80` entry.

## Canonical corrections to the comparison parser

The canonical static review changed six owned widths and preserved one
lookahead distinction that a flattened parser representation can hide:

| Opcode | Canonical owned width | Canonical reason |
| --- | ---: | --- |
| `$15` | 3 | handler stores consuming delta 3 after two operands |
| `$18` | 2 | handler consumes one coordinate-table selector |
| `$3B` | 2 | handler reads one immediate and advances 2 |
| `$3C` | 2 | handler reads one variable selector and advances 2 |
| `$9B` | 2 | shared target-mode path stores consuming delta 2 |
| `$C5` | 2 | handler reads one parameter and stores consuming delta 2 |
| `$DA` | 1 | handler reads `+1` but advances only 1 |

These are corrections to Project Epoch's comparison input, not a claim that a
community project is generally unreliable. The pinned canonical handler
behavior governs this project.

## Root domain and closure

The direct roots come from the closed package-topology dependency. Two related
domains remain visible:

| Direct-root domain | Total | `$CD` | `$CE` |
| --- | ---: | ---: | ---: |
| declared route contexts | 2,146 | 1,211 | 935 |
| config-selected structural supplement | 2,173 | 1,211 | 962 |

The declared set is a strict subset of the config-selected set; the 27-root
supplement comes entirely from `$CE`. The census tokenizes the larger set so
that every physically encoded PC config-selected source is covered without
claiming that every source is reachable at runtime.

Command `$1E` produces a separate fixed-`$CE` closure:

| Measure | Result |
| --- | ---: |
| direct entrypoints | 2,173 |
| distinct nested entrypoints | 59 |
| total closure entrypoints | 2,232 |
| distinct `$1E` sites | 742 |
| distinct `$1E` operands | 59 |
| distinct targets | 59 |
| operand-to-target aliases | 0 |
| nested entrypoints containing `$1E` | 0 |
| maximum transitive `$1E` depth | 1 |
| distinct `$1F` sites | 59 |

Every nested forced-fallthrough trace ends at `$1F`. Across those nested
traces, command `$21` appears 24 times and command `$25` appears zero times.
Because `$21` can restore the parent conditionally, the exact claim is about
physical fallthrough tokenization—not guaranteed runtime execution of all
later tokens.

## Stream census

| Measure | Result |
| --- | ---: |
| distinct token starts | 31,655 |
| distinct owned bytes | 58,960 |
| entrypoint-traversal token count | 31,659 |
| minimum tokens per entrypoint | 1 |
| maximum tokens per entrypoint | 147 |
| distinct observed opcodes | 127 |
| dispatched opcodes not observed | 92 |
| default-handler sticky sites | 448 |
| `$21` sites in the complete closure | 24 |
| `$25` sites in the complete closure | 70 |
| `$DB-$FF` marker sites | 0 |
| conflicting token extents | 0 |

The four-token difference between distinct starts and traversal count is
intentional shared-entry topology. Every shared start decodes to the same
opcode, owned width, handler family, flow class, and lookahead contract.

Direct entrypoints terminate at 1,724 distinct stop outcomes and 449
default-handler sticky outcomes. Nested entrypoints contribute 59
forced-fallthrough `$1F` endpoints. Terminal counts are per entrypoint;
default-handler site counts are deduplicated physical token starts, so those
two totals need not be identical.

## The four-byte descriptor/stream dual use

The census originally tested the sensible hypothesis that selected package
descriptor spans and command streams would be physically disjoint. The
canonical evidence falsified that stronger hypothesis in one bounded case:

- two token starts are inside one selected descriptor span;
- four token-owned bytes are inside that span;
- one direct entrypoint reaches the intersection;
- all command-token extents remain mutually disjoint;
- no other selected descriptor/stream intersection appears.

The auditor records two exact metadata ledgers: one for the intersecting token
and descriptor extents, and one for the entrypoint that reaches them. It emits
neither raw bytes nor physical script/root rows. Any new cross-boundary token,
additional descriptor, changed extent, or different entrypoint changes the
closed contract and fails the audit.

This finding changes an architectural assumption: a package descriptor span
cannot be treated as automatically separate from command data, and neither
side of this canonical dual-use region may be considered padding or free
space.

## Reproduction

The cache-free read-only command is:

```text
python -B tools/audit_battle_command_grammar_census_v0.py \
  <canonical-us-rev0-headerless-rom> --compact
```

The command writes metadata-only JSON to standard output. There is no output
file option. `-B` suppresses interpreter bytecode-cache writes, so the stated
reproduction has no expected filesystem side effects. The auditor rejects a
wrong ROM identity, machine-witness drift, package-topology drift, reference
hash drift, inconsistent shared token, overlapping owned extent, out-of-range
token/lookahead, cycle, malformed caller contract, or changed result.

The focused test command is:

```text
python -B -m unittest tests.test_battle_command_grammar_census_v0 -v
```

## What this gate now permits

The completed grammar is sufficient to begin the next design proof. It permits
Project Epoch to ask, with exact boundaries, how an expanded package would
handle nested scripts. It does not permit installing one.

`BA-CMD-1E-FINAL-EXPANDED-POLICY` must choose and prove one of two policies:

1. **Exclusion:** every authored expanded-package stream is statically proved
   to contain no `$1E`, including every reachable suffix/shared entrypoint.
2. **Adaptation:** a bank-qualified nested-script registry and handler preserve
   canonical `$00-$7F` behavior, parent continuation, `$1F` restoration,
   `$21` conditional return, `$25` conditional stop, operand identity, DBR,
   direct page, stack, timing, and vanilla output equivalence.

Only after that gate passes may `BA-SYMBOLIC-HIGH-PACKAGE` bind one candidate
selector in `$80-$8F` to named expanded data and prove its auxiliary readers.

## Evidence ceiling and nonclaims

This result is `verified-static`. It establishes a deterministic structural
grammar and a canonical possible-context census. It is not:

- runtime reachability or frequency evidence;
- an animation timing model;
- a visual-semantics assignment for any stream;
- proof that an unobserved or default-handler opcode is free;
- approval to reuse `$DB-$FF` battle markers as commands;
- proof that command `$1E` is safe in an expanded bank;
- an auxiliary animation, graphics, palette, effect, or sound adapter;
- a logical PC `$07`, Schala Tech, item, sprite, or battle-runtime proof;
- a production hook, allocation, helper, ROM mutation, patch, save, state,
  trace, or emulator result.

Unkeyed hashes here are reproducibility and drift checks. They are not
authentication, provenance by themselves, or ownership claims.
