# Location-event animation operand census v0

Date: 2026-08-22

Evidence: `verified-static` for the hash-gated encoded census and direct-entry
topology; no runtime attribution

## Outcome

The read-only auditor inventories every structurally valid encoded
location-event use of `$AA`, `$AB`, `$AC`, `$AE`, `$B3`, `$B4`, and `$B7` in
the canonical headerless Chrono Trigger US Rev 0 ROM. It keeps animation
entrypoint selectors, implicit entrypoints, static assembly-frame selectors,
and `$B7` repetition/progress values in separate namespaces. The census is
complete for the pinned encoded corpus: 10,637 unique physical sites in 391
animation-bearing packets.

The result is deliberately not a runtime playable-character attribution. An
encoded command belongs to one physical source range, but any logical
object's 16 function entries can point into another object's source. Of
116,064 function-pointer occurrences, 2,269 leave their nominal physical
owner: 1,864 point backward, 321 point forward, and 84 point exactly to the
packet-end sentinel. Treating the physically adjacent loader as the command's
runtime identity would therefore be unsound.

The auditor instead computes a conservative, syntax-only direct-entry marker
closure. That closure is complete over the 16 direct function entries per
logical object and intentionally admits false positives. Calls, jumps,
fallthrough, startup replay, loader lifetime, lifecycle order, party state,
and actual runtime reachability remain unresolved. The report status is
therefore:

```text
pass-metadata-only-encoded-census-with-unresolved-contexts
```

This closes the encoded location-event operand-inventory gate. It does not
approve a Schala frame binding, a logical PC `$07`, a graphics source, an
expanded-bank reader, a hook, an allocation, or a ROM installation.

## Pinned input and public artifacts

The only game input is the ignored, local-only canonical ROM:

- size: 4,194,304 bytes;
- SHA-1: `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`;
- SHA-256:
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.

The source-controlled outputs contain metadata only:

- auditor: `tools/audit_location_event_animation_operands_v0.py`, 92,781
  bytes, SHA-256
  `e3276f6b7822254d6c1d17f37b84132d85ccbe61cd842facc3556faa30d94141`;
- tests: `tests/test_location_event_animation_operands_v0.py`, 18,438 bytes,
  SHA-256
  `53c99b2bc0c24ccb4f515c46266993acf14b4023887885b068af7c8c6c7135cb`;
- canonical report:
  `references/location_event_animation_operands_v0.json`, 31,731 bytes,
  SHA-256
  `d170c0d5771b84e0fbcb394dcd4151ccef3e8c96f4bd6a80a6cc9c498f78f2c4`;
- closed nested-schema SHA-256:
  `93efc3dceb56a0a920d0c23938d5fb0e6986198457bd543504ca5bd6e9c2e6ce`;
- semantic report SHA-256, with the tool self-receipt normalized to avoid a
  source/report hash cycle:
  `4bc4130f808d966a1260080a57c96edca7df01e9b0fe7f9ec6d71ef1006ce7cd`.

The auditor writes nothing. It has no output-path option and emits canonical
JSON only to standard output. The checked-in report contains no ROM bytes,
decoded packet bytes, ordered script/site ledger, dialogue, image, save,
state, trace, emulator binary, patch, or private path.

## Corpus and alias topology

The fail-closed corpus gates are:

| Measure | Canonical result |
|---|---:|
| Location records | 512 |
| Event-pointer entries | 513 |
| Location-referenced event IDs | 497 |
| Structurally decoded event-ID entries | 489 |
| Expected placeholder event IDs | 24 |
| Unique encoded packet pointers | 466 |
| Valid decoded packet pointers | 462 |
| Unique decoded-content digests | 455 |
| Unique physical commands | 145,615 |
| Event-ID command instances | 155,780 |
| Physical objects | 7,254 |
| Animation/static sites | 10,637 |
| Animation-bearing packets | 391 |

The 24 expected placeholders form exactly four pinned pointer groups. Their
event IDs, pointers, failure stages, and stable categorical reasons are an
allowlist. Any added, removed, moved, differently failing, or otherwise
unexpected decompression/parse failure aborts the audit rather than silently
becoming a non-script.

Packet-pointer aliases and equal decoded-content packets remain separate
relations:

- 16 packet-pointer alias groups account for 27 additional event IDs;
- four decoded-content equivalence groups account for seven additional packet
  pointers; and
- equal decoded content never erases the fact that those are distinct source
  packets.

Every canonical function entry lands on a decoded command boundary or the
exact packet-end sentinel. Function-0 starts are strictly increasing, but the
complete 16-entry lists are not generally monotone:

| Function-topology measure | Canonical result |
|---|---:|
| Function-pointer occurrences | 116,064 |
| In-owner open-range occurrences | 113,795 |
| Backward cross-owner occurrences | 1,864 |
| Forward cross-owner occurrences | 321 |
| Exact packet-end sentinels | 84 |
| Repeated same-start aliases | 91,869 |
| Objects with nonmonotone lists | 668 |
| Objects with cross-owner entries | 669 |
| Packets with cross-owner entries | 111 |
| Animation-bearing packets with cross-owner entries | 109 |
| Nonboundary targets or non-sentinel unowned targets | 0 |

A repeated start is an alias, not proof of an empty function. Only an exact
one-past-packet pointer is recorded as the packet-end sentinel, and its runtime
meaning remains unresolved.

## Conservative direct-entry context

For each physical animation source owner `S`, the tool computes:

```text
targets[L] = distinct physical owners reached by logical owner L's
             sixteen direct function entries, excluding packet end

incoming[S] = every logical owner L for which S is in targets[L]

closure[S] = union of targets[L] for every L in incoming[S]
```

Loader and alternate-identity markers from each distinct owner in
`closure[S]` are then unioned once. The animation sites physically owned by
`S` are counted once. This incoming closure is necessary: an object can point
backward or forward into code stored under another object, so examining only
the source owner's outgoing entries can miss a logical PC context.

The canonical direct-entry geometry is:

| Measure | Result |
|---|---:|
| Physical animation source owners | 2,744 |
| Incoming logical-owner associations | 3,299 |
| External incoming associations | 555 |
| Distinct logical-to-source-owner relations, all objects | 7,967 |
| Function-pointer occurrences targeting animation owners | 44,701 |
| Animation owners with external/multiple incoming context | 122 |
| Animation owners with self-only incoming context | 2,622 |
| Maximum incoming logical owners for one animation owner | 14 |
| Closure/source-owner associations | 3,564 |
| Animation owners whose closure extends beyond self | 351 |
| Packets with a closure extending beyond self | 93 |
| Animation owners whose marker union changes | 350 |
| Packets whose marker union changes | 92 |

The 93-versus-92 distinction is intentional. One packet has a genuine
cross-owner closure whose additional source owner contains no relevant
identity or graphics marker, so topology changes while the marker union does
not.

The physical-owner-only classification would have produced 939 PC-only, nine
mixed PC/non-PC, and 1,796 no-PC-marker owners. The incoming closure instead
produces:

| Marker bucket | Animation source owners |
|---|---:|
| PC marker without NPC/enemy marker | 927 |
| PC and NPC/enemy markers | 23 |
| No PC marker | 1,794 |

Fourteen source owners change coarse bucket. Across the 950 source owners
whose direct-entry closure contains some PC marker, 5,624 encoded
animation/static sites are possible PC-marker sites. They are not proved
runtime PC sites.

The direct-entry PC-marker site counts by opcode are:

| Opcode | Possible PC-marker sites |
|---:|---:|
| `$AA` | 3,051 |
| `$AB` | 347 |
| `$AC` | 1,264 |
| `$AE` | 684 |
| `$B3` | 66 |
| `$B4` | 30 |
| `$B7` | 182 |

Dedicated loader markers map only to the seven vanilla IDs `$00-$06`.
Canonical generic `$80/$81` operands also span exactly `$00-$06`; synthetic
tests prove that the auditor leaves `$07` and larger values in
`unknown-pc-like-not-project-epoch` and never promotes them to Epoch, Schala,
or a vanilla playable PC.

## Animation command namespaces

The command-size vector covers all 256 opcodes and has SHA-256
`95e029ecb6f39753e5a9870035c30cf28e540b75e5f107c24753e57780b43f65`.
The relevant closed contract is:

| Opcode | Total bytes | Selector source | Namespace | Unique sites |
|---:|---:|---|---|---:|
| `$AA` | 2 | payload byte 0 | animation entrypoint | 5,593 |
| `$AB` | 2 | payload byte 0 | secondary animation entrypoint | 638 |
| `$AC` | 2 | payload byte 0 | static assembly frame | 2,581 |
| `$AE` | 1 | implicit `$00` | animation entrypoint | 1,011 |
| `$B3` | 1 | implicit `$00` | animation entrypoint | 278 |
| `$B4` | 1 | implicit `$01` | animation entrypoint | 275 |
| `$B7` | 3 | payload byte 0 | secondary animation entrypoint | 261 |

`$B7` payload byte 1 is repetition/progress control, never an entrypoint.
`$AC` is never merged into an animation-entrypoint domain. `$AE`, `$B3`, and
`$B4` carry implicit selectors rather than operands. Entrypoint `N` begins at
`N * 4`; four bytes is a table stride, not a fixed record length.

The public report retains only unordered domains, counts, ranges, and
frequency/ledger digests. It does not expose a source-ordered site list or an
ordered event script.

## Identity, graphics, and lifecycle boundaries

The loader-marker model distinguishes:

- dedicated vanilla-PC loaders `$57/$5C/$62/$68/$6A/$6C/$6D`;
- party-aware generic PC loader `$80` and direct PC-like loader `$81`;
- NPC loader `$82`;
- three-byte enemy loader `$83`, where operand 1 is graphics/cache-slot flags
  and never another identity;
- graphics-assignment override `$87`; and
- lifecycle/role markers `$0A/$0B/$0C/$D4/$D6`.

Opcode `$87` is orthogonal to identity classification. The canonical corpus
contains 1,170 unique `$87` commands and 16 distinct operand values, with
minimum `$00`, maximum `$7F`, and 25 uses of `$7F`. There are 461 physical
animation owners with a local `$87` marker and 485 direct-entry contexts whose
closure contains one. Presence of `$87` does not prove which graphics source
or identity is live at an animation site; the bitfield and path-order model
remains incomplete.

An independent absolute-address command audit found 1,511 relevant absolute
references. Fifty-one overlap the `$7E1000-$107F` and `$7E1100-$117F`
identity/state arrays; all 51 are reads and none is a direct write. That is a
pinned negative result, not proof against computed or indirect writes.

## Fail-closed behavior

The audit aborts on any drift in:

1. ROM size, SHA-1, or SHA-256;
2. the exact parser dependency receipt;
3. the complete 256-opcode size-vector hash;
4. any pinned dispatcher, loader, animation, lifecycle, or reader preimage;
5. the exact placeholder allowlist;
6. packet/object/function topology, boundary validity, or canonical counts;
7. loader, alternate-marker, graphics, or lifecycle domains;
8. command widths or animation namespace rules;
9. the closed nested report schema, semantic identity, or checked-in report
   bytes; or
10. a forbidden raw/private field or production-facing claim.

The synthetic suite additionally rejects a function pointer into an operand,
non-strict function-0 starts, the outgoing-only backward and forward
counterexamples, malformed report mutations, and generic PC ID `$07`.

## Reproduction

Set the private canonical ROM explicitly, disable incidental bytecode-cache
writes, and run the focused suite:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CT_US_REV0_ROM = (Resolve-Path -LiteralPath `
  'private\input\rom_archive\Chrono Trigger (USA).sfc').Path
python -m unittest tests.test_location_event_animation_operands_v0 -v
```

The focused result is 19 tests passed. To reproduce the report to standard
output without creating an artifact:

```powershell
python tools/audit_location_event_animation_operands_v0.py `
  $env:CT_US_REV0_ROM
```

The report validator checks exact canonical bytes against the checked-in
31,731-byte artifact. The test fixture hashes the ROM before and after all
ROM-backed cases and requires byte preservation.

## Evidence ceiling and next gate

The positive claim is limited to a complete, hash-gated encoded
location-event animation/static-site census and a conservative marker
overapproximation over direct function-entry topology. It is
`verified-static`, metadata-only evidence.

It does not prove:

- that any encoded site executes in a reachable story branch;
- that a loader is live when a site executes;
- function-call, fallthrough, startup-replay, or asynchronous order;
- execution frequency or a complete animation loop;
- an effective `$87` graphics assignment;
- a complete playable-character field packet;
- any battle, menu, overworld, save/load, recruitment, New Game+, or modified
  ROM behavior; or
- logical PC `$07`, Schala, Epoch safety, a graphics index, free space, a
  hook, an allocation, or installation.

Before this census may be used as runtime PC attribution, implement or
explicitly defer a closed inter-object control-flow and loader-lifetime model.
The separate metadata-only battle action-package topology census and
source-only package-bank adapter have since been completed. Their next gate is
a lossless battle command grammar and canonical stream census with an explicit
decoded-command `$1E` decision; the current fixed-`$CE` subscript reader must
not be generalized from a raw byte search. No native Schala frame should be
assigned from a fixed numeric operand until its consumer path and runtime
context are independently proved.
