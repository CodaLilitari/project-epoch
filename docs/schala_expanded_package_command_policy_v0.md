# Schala expanded-package command policy v0

Status: `complete-static`

Gate: `BA-CMD-1E-FINAL-EXPANDED-POLICY`

Policy ID: `decoded-command-1e-exclusion-flat-direct-v0`

Evidence ceiling: `verified-static` source-only policy and host validation

## BLUF

Project Epoch's first expanded player-Tech animation packages will use a
strict **decoded-command exclusion** policy for command `$1E`. Every distinct
descriptor-selected entrypoint is decoded with the closed canonical command
grammar. A package passes only when every decoded path is a flat direct stream,
contains no decoded `$1E`, `$1F`, or `$21`, and terminates at `$00` inside an
exact named stream span.

This closes the policy choice; it does not bind a package. Candidate package
selectors `$80-$8F` remain empty. The vanilla `$1E` handler still forces its
nested target into bank `$CE`, so cross-bank `$1E` adaptation remains
deliberately unimplemented and unapproved. Any future package that needs
nested scripts requires a new, separately numbered policy and proof.

The implementation is
[`tools/audit_schala_expanded_package_command_policy_v0.py`](../tools/audit_schala_expanded_package_command_policy_v0.py).
The byte-pinned contract is
[`references/schala_expanded_package_command_policy_v0.json`](../references/schala_expanded_package_command_policy_v0.json).

## Why exclusion is the v0 decision

The completed package-bank adapter can publish bank-qualified direct script
entries, but the native command-`$1E` handler independently resolves its
operand through a fixed-bank `$CE` pointer table and then changes the live
script bank to `$CE`. Preserving nested calls across an expanded bank would
therefore require a new bank-qualified subscript registry or handler, plus
proof for `$1F`, `$21`, `$25`, pointer state, DBR, DP, stack, operands, timing,
and exact vanilla equivalence.

The first original package does not need to take that risk. Flat streams are
expressive enough for the first symbolic proof, so v0 makes `$1E` structurally
illegal and leaves the existing handler untouched. The decision is final for
this profile, not a claim that a later nested profile is impossible.

## A decoded command is not a raw byte

A raw scan for byte value `$1E` is not authoritative. Command operands may
legitimately equal `$1E`; only bytes reached at token boundaries are opcodes.
The pinned conformance vector makes this distinction executable:

- one two-byte command owns an operand whose value is exactly `$1E`;
- a second descriptor-selected entrypoint begins at the shared terminal
  `$00` suffix;
- both entrypoints decode and close successfully;
- the report records one raw `$1E` byte and zero decoded command-`$1E` sites.

Conversely, tests place decoded `$1E` at the root, in the middle of a stream,
and behind an alternate-mask descriptor entry. Every case fails closed. This
prevents both false rejection of harmless operand data and false acceptance of
a hidden nested-script call.

## Strict flat-direct grammar profile

The allowed set is derived from the 127 opcodes observed by the closed
canonical package census, then removes four commands:

- `$01`: the canonical default-handler sticky terminal, excluded from authored
  streams;
- `$1E`: nested-script call, excluded by this policy;
- `$1F`: parent return, invalid without a saved parent from `$1E`;
- `$21`: conditional parent return, likewise invalid in a flat direct stream.

The resulting profile contains 123 opcodes and is pinned by SHA-256
`2e3ae36cc7cb7a562c2e8ec3f5d67038ce09225953264c2ed5e3cb87a7fb39aa`.
Unobserved opcodes, default-handler aliases, and the `$DB-$FF` dispatcher-exit
marker family are rejected. This is a conservative authoring set, not a claim
that every observed canonical command is appropriate for every future Tech.

Special cases retain the completed grammar's exact ownership rules:

- `$00` is the only accepted terminal and must be reached by forced
  fallthrough;
- `$25` is allowed only when its physical fallthrough remains fully decodable
  through `$00`; its conditional early-stop runtime branch is not replayed by
  this static policy;
- `$80` is variable-width, but low-nibble zero is deliberately forbidden for
  authored data because it implies the canonical 256-byte read-lookahead
  shape;
- `$DA` owns one byte while reading `+1`; that lookahead byte must remain
  inside the same named stream span.

## Layout and entrypoint proof

The validator accepts only an immutable synthetic 64 KiB bank image and an
explicit layout. It does not open a ROM. The layout must provide:

- one high candidate selector in `$80-$8F`;
- one exact uppercase symbolic descriptor span;
- one or more exact uppercase symbolic stream spans;
- a common source bank for every span;
- no overlap among any descriptor or stream spans;
- no unnamed bytes inside a declared stream allocation.

The descriptor span must equal the complete parsed descriptor. Both native
`$A0B3` branches are simulated through the completed package-bank adapter, and
their publications must exactly reproduce the descriptor's mask-0 and mask-1
relations. Every distinct selected pointer is then decoded independently.

Shared suffix entrypoints are valid only when they begin at an existing token
boundary and produce an identical token signature. An entrypoint inside
another command's owned extent is rejected. After all selected entries close,
every byte of every named stream span must be owned by a decoded token. This
rules out unreachable padding and keeps the source allocation auditable.

The canonical game's known four-byte descriptor/stream dual-use relation is
preserved as occupied canonical evidence. It is not a precedent for new
Project Epoch data: the v0 authoring policy forbids descriptor/stream overlap.

## Content-bound evidence

A proof must identify the data it actually checked, not merely the layout. The
metadata-only result binds:

- the grammar and package-bank-adapter contract hashes;
- the allowed-opcode-vector hash;
- selector, bank, root, symbolic allocation, and source kind;
- SHA-256 for the exact descriptor and each exact stream span;
- descriptor relations for both masks;
- decoded token, trace, terminal, and owned-byte ledgers.

The certificate also pins the exact grammar-auditor and package-adapter source
files and a complete 511-row token-shape profile covering all 256 opcodes and
every `$80` first-payload value. This binds the result to the interpreters that
gave the bytes meaning, not just to their reference JSON. A negative control
changes an allowed opcode that the conformance vector never executes and
proves that the dependency gate rejects the semantic drift.

Those fields feed `command_exclusion_proof_sha256`. A change to a meaningful
operand, source bank, descriptor relation, token, terminal, or owned byte
therefore changes or invalidates the proof even when the stream's opcode
sequence appears unchanged. No descriptor bytes or command-stream bytes are
printed in the report.

The pinned v0 contract is 6,717 bytes with SHA-256
`808f286c37fd9163a776a5b545513aa1a9fb89f4c78281a204af5540f272c1ea`.
Its synthetic conformance proof is
`b3bbd8b43304381fc7e9a141546286b26101e36bb0d2a75f29ed2877a39f9aa0`.
These hashes pin the policy and its deliberately minimal conformance vector;
they are not ROM allocation or runtime evidence.

## Reproduction and regression coverage

Run the metadata-only audit:

```powershell
py -B tools/audit_schala_expanded_package_command_policy_v0.py --compact
```

Run the focused suite:

```powershell
py -B -m unittest tests.test_schala_expanded_package_command_policy_v0 -v
```

The 23 focused tests cover dependency and reference pins, the strict opcode
profile, raw-operand acceptance, decoded `$1E` rejection across both masks,
control/default/marker/unobserved refusal, `$25`, `$80`, and `$DA` bounds,
shared suffixes, mid-token entry rejection, exact descriptor and stream
ownership, bank and name validation, immutable input, interpreter drift,
content and source-identity binding, valid structural mutations, duplicate
cross-mask pointer accounting, the explicit out-of-span boundary, adapter
fail-closed preservation, deterministic metadata-only output, and the absence
of any output-file option.

## Evidence ceiling and nonclaims

This gate proves one source-authoring rule and its validator. It does not
prove or approve any of the following:

- a bound selector in `$80-$8F`;
- a mapping between a Schala action ID and a package selector;
- a Schala Tech, effect, sprite, palette, sound, or animation;
- auxiliary graphics, palette, effect, or sound selectors;
- command-`$1E` adaptation or cross-bank nested scripts;
- an expanded ROM bank, address, free-space claim, allocation, hook, helper,
  patch, ROM image, save, state, trace, or emulator result;
- logical PC `$07` runtime behavior.

Synthetic banks and offsets used by the tests are identities for the test
vector only. They are not candidate production placements.

## Next gate

Resume at `BA-SYMBOLIC-HIGH-PACKAGE`. Define exactly one source-only symbolic
package under selector `$80`, still unbound to any action. The safest first
contract should reconstruct one selected canonical action-config row from the
user's pinned clean ROM at build time, preserve its proven fixed-bank
auxiliary selectors in bytes `+1` through `+6`, and deliberately replace only
config byte `+0` with the high package selector. The expanded primary
descriptor and original flat command stream must live in exact named synthetic
allocations and pass this policy.

That next gate may publish only metadata, hashes, schemas, and source code. It
must not source-control the reconstructed canonical row or any extracted
payload, choose a production address, bind a Schala action, authorize a hook,
or claim runtime behavior.
