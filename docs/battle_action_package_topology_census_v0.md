# Project Epoch battle action-package topology census v0

Status: `verified-static`; metadata-only structural census complete, command
stream decoding and runtime proof unresolved

Last verified: 2026-08-22

Canonical input: Chrono Trigger US Rev0, headerless

## Result

This tranche maps the canonical primary battle-action routes from their typed
inputs through configuration selectors and package resolvers to
**bank-qualified direct script entrypoints**. It gives Project Epoch a bounded,
reproducible picture of the package topology that a future Schala animation
adapter must preserve.

It does not install an adapter. The auditor is read-only, emits metadata-only
JSON to standard output, and stops before decoding any battle-animation
command stream. The result is therefore a structural foundation for an
expanded-bank design, not evidence that logical PC `$07`, a Schala command, or
an eighth playable character works in battle.

The implementation comprises:

- `tools/audit_battle_action_package_topology_v0.py`, the fail-closed auditor;
- `references/battle_action_package_topology_v0.json`, the closed expected
  contract;
- `tests/test_battle_action_package_topology_v0.py`, synthetic negative
  controls plus canonical-input checks.

No ROM bytes, table payloads, pointer lists, script streams, saves, states,
traces, patches, or emulator artifacts are stored in these files or emitted in
the report.

## The namespace boundary that must not be collapsed

The principal finding is not merely a set of addresses. It is that several
byte-valued namespaces participate in battle animation and remain independent:

1. logical PC ID;
2. player-command/action ID;
3. top-level action type in `$AE92`;
4. route-specific parameter in `$AE93`;
5. PC type-2 animation-config row index;
6. config row byte-0 package selector;
7. resolver-selected package descriptor, identified by bank and root offset;
8. descriptor owner-bit index;
9. direct script entrypoint, identified by package bank and 16-bit offset;
10. command-stream opcode, graphics selector, and battle marker values.

Equal numeric values do not make two of these identities interchangeable. In
particular, player-command IDs `$7C-$7F` remain reserved command gaps, while
the separate PC type-2 animation-config table has fixed engine producers for
rows `$7C`, `$7D`, and `$7F`. Rows `$79-$7B` also have fixed producers. This
does not consume those values as player commands, and it does not make any of
them globally free or globally occupied under a single unified namespace.

The proposed Schala player-command range `$80-$90` is likewise not an index
extension of the canonical PC animation-config table. Canonical type-2 player
loading rejects action ID `$80` before it could fall through into the adjacent
enemy configuration data. A future high-ID adapter must branch to named
expanded data rather than extending a vanilla table in place.

## Typed route chain

The top-level dispatcher uses `$AE92`, not `$AE93`:

| `$AE92` | Structural route |
| --- | --- |
| `$00` | no package load; return |
| `$01` | Attack, then player/enemy actor split |
| `$02` | Tech/internal animation, then player/enemy actor split |
| `$03` | battle item |
| `$04-$FF` | coerced to type `$00` before dispatch |

After dispatch, the complete selection key is route-specific. The general
shape is:

```text
AE92 action type
  -> actor partition and route-specific typed input
  -> config row or route-specific selector source
  -> package selector
  -> bank-local resolver
  -> (package bank, descriptor root)
  -> one of two structural mask lists
  -> (package bank, direct script offset)
```

The audited routes are:

| Route | Typed source domain | Package selector source | Resolver | Package bank |
| --- | --- | --- | --- | --- |
| PC normal Attack | logical PCs `$00-$06` plus three outcome families | three independent seven-entry selector families | 21-word normal-Attack resolver | `$CE` |
| PC named Tech | player action IDs `$01-$74` | byte 0 of the indexed seven-byte PC config row | 128-word PC resolver | `$CE` |
| PC internal type 2 | seven pinned fixed contexts selecting config rows `$79/$7A/$7B/$7C/$7D/$7F` | byte 0 of the selected PC config row | 128-word PC resolver | `$CE` |
| PC physical supplement | all 128 encoded PC config rows `$00-$7F`; no runtime domain asserted | byte 0 of each physical row | 128-word PC resolver | `$CE` |
| enemy Attack | all 256 encoded enemy records in each of the `$AE93==0` and `$AE93!=0` branches | byte 0 of the selected branch row | 256-word enemy-Attack resolver | `$CD` |
| enemy Tech | all 256 encoded rows indexed by `$AE93` | byte 0 of the selected row | 256-word enemy-Tech resolver | `$CD` |
| battle item | canonical raw IDs `$BC-$DB`, row indices `$00-$1F` | byte 0 of the physical item-config row | 96-word item resolver | `$CE` |

Important route-specific consequences:

- PC normal Attack package selection ignores `$AE93`; it uses logical PC ID
  plus the Attack outcome family. Project Epoch's proposed Focus Pulse action
  `$90` is a player-command identity in another namespace.
- PC named-Tech action IDs do not index the resolver directly. Across the 128
  physical PC rows, the selector vector is a permutation with 27 row/selector
  mismatches.
- The PC internal type-2 chain is specifically `$AE93` config-row index, then
  row-byte-0 package selector, then resolver-selected `$CE` descriptor root.
  Numeric identity in the currently fixed tail rows is observed data, not a
  license to merge those stages.
- For enemy Attack, `$AE93` chooses the zero/nonzero config branch; the enemy
  record index comes from separate actor state. `$AE93` is not the enemy
  record index on that route.
- The physical PC supplement inventories encoded topology only. It is not a
  claim that every row is reachable.
- Item IDs beyond the audited canonical `$BC-$DB` domain are not accepted by
  this census as battle-item packages. In particular, the proposed Schala item
  range `$E8-$EE` receives no package-binding approval here.

## Descriptor geometry and bank-qualified identity

Each selected primary package descriptor is parsed as:

```text
4-byte header: mask0, mask1
then 2 * (popcount(mask0) + popcount(mask1)) bytes of script offsets
```

The two masks use big-endian byte placement. Their following script offsets
are little-endian 16-bit offsets local to the package bank. Mask bits are
visited most-significant-bit first and recorded as neutral owner-bit indices
`$00-$0F`.

The two masks are structural alternatives, not simultaneous execution lists.
The pinned machine path uses one list when `$A0B3` is zero and consumes/skips
the first before using the second when `$A0B3` is nonzero.

Neither descriptor roots nor script entrypoints can be identified by their
low 16-bit offsets alone:

```text
descriptor identity = (package bank, descriptor root offset)
script identity     = (package bank, script offset)
```

The negative controls demonstrate why the bank is mandatory. Descriptor low
offset `$8171` occurs in both `$CD` and `$CE`, as do script low offsets
`$6E56`, `$76F9`, `$7750`, and `$81CE`. Omitting the bank would incorrectly
merge distinct physical nodes. Conversely, the enemy Attack and enemy Tech
routes share exactly seven same-bank `$CD` direct script entrypoints; those are
real aliases and are retained as such.

Across both reported structural unions, selected descriptor spans are
disjoint and their direct script entrypoints lie outside those descriptor
spans. Owner-bit indices `$05-$07` happen to be unset in the selected
descriptors, while `$08-$0F` are present. These are neutral descriptor slots,
not logical PC IDs. The pattern proves neither a latent eighth-character slot
nor free capacity.

Selected resolver targets are non-`$FFFF` because the auditor rejects a
selected `$FFFF` before attempting descriptor access. This is an auditor
validity rule. It is not proof that the engine locally rejects `$FFFF`, and no
unselected resolver word, `$FFFF` entry, table gap, or neighboring byte is
classified as free.

## Route and aggregate counts

For each route, “pointer relations” means physical script-pointer occurrences
across its distinct selected descriptors. “Direct scripts” deduplicates by the
bank-qualified identity `(package bank, script offset)`.

| Route | Source contexts | Selectors | Distinct descriptors | Pointer relations | Distinct direct scripts |
| --- | ---: | ---: | ---: | ---: | ---: |
| PC normal Attack | 21 | 19 | 19 | 116 | 63 |
| PC named Tech | 116 | 116 | 116 | 1,095 | 806 |
| PC internal type 2 | 7 | 6 | 6 | 20 | 8 |
| PC physical supplement | 128 | 128 | 125 | 1,145 | 841 |
| enemy Attack | 512 | 122 | 122 | 678 | 372 |
| enemy Tech | 256 | 191 | 174 | 1,221 | 846 |
| battle item | 32 | 32 | 15 | 89 | 58 |

The primary **declared-context structural union** includes PC normal Attack,
PC named Tech, the seven fixed PC internal type-2 contexts, enemy Attack,
enemy Tech, and battle item:

| Measure | Total | By bank |
| --- | ---: | --- |
| distinct descriptors | 452 | `$CD`: 296; `$CE`: 156 |
| physical pointer relations | 3,219 | not additive by route because descriptors can overlap |
| distinct direct scripts | 2,146 | `$CD`: 1,211; `$CE`: 935 |

The separate **config-selected structural supplement union** replaces the
named/fixed PC route slices with all 128 encoded PC physical rows. It includes
PC normal Attack, PC physical supplement, enemy Attack, enemy Tech, and battle
item:

| Measure | Total | By bank |
| --- | ---: | --- |
| distinct descriptors | 455 | `$CD`: 296; `$CE`: 159 |
| physical pointer relations | 3,249 | not additive by route because descriptors can overlap |
| distinct direct scripts | 2,173 | `$CD`: 1,211; `$CE`: 962 |

Both are structural unions. Neither is a runtime-reachability, frequency,
story-state, or execution-order result.

## Fixed PC type-2 configuration contexts

The pinned fixed-value contexts establish seven producers for six internal
config rows. The table below preserves all three typed stages; matching values
in the first two columns do not collapse their namespaces.

| Config row selected through `$AE93` | Fixed-value load context(s) | Row-byte-0 package selector | `$CE` descriptor root | Relations | Distinct direct scripts |
| --- | --- | --- | --- | ---: | ---: |
| `$79` | `$C1:820D` | `$79` | `$81D0` | 2 | 1 |
| `$7A` | `$C1:B365` | `$7A` | `$81E0` | 4 | 2 |
| `$7B` | `$C1:C69E` | `$7B` | `$821F` | 2 | 1 |
| `$7C` | `$C1:C697` | `$7C` | `$8234` | 4 | 2 |
| `$7D` | `$C1:C689` | `$7D` | `$8250` | 6 | 2 |
| `$7F` | `$C1:8943`, `$C1:8BAF` | `$7F` | `$8288` | 2 | 1 |

Rows `$79` and `$7F` reach a shared helper whose encoded direct store is at
`$C1:895B`; the raw whole-ROM helper-reference scan finds three `JSR absolute`
candidates at `$C1:820F`, `$C1:8945`, and `$C1:8BB1`. Row `$7A` has a direct
producer. Rows `$7B-$7D` are selected by a separate fallback path.

For that fallback, the verified-static condition is `$3A != $04`, 16-bit
`$99C0 == $FFFF`, and `$B18B < $03`. It chooses `$7D` when `$B2EC` is
nonnegative, otherwise `$7C` when `$B2EB != $FF`, otherwise `$7B`. Describing
this as a participant-arity-shaped no-target fallback is an inference only;
the topology census does not promote that interpretation to runtime evidence.

No listed fixed producer selects row `$7E`. Row `$7E` exists in the physical
config-table supplement, but remains unclaimed rather than free. Indirect,
pointer-derived, adjacent-width, and other effective writes have not been
proved absent.

## `$AE93` encoded-operand census and the `$AE92` width caveat

To prevent the fixed-context list from being mistaken for a complete writer
graph, the report includes a separate raw whole-ROM byte-pattern census. It
enumerates write-capable direct absolute, absolute-indexed, and long-address
opcode families whose **encoded operand** is `$AE93`.

On the pinned image it finds:

- 14 `STA absolute` candidates with encoded operand `$AE93`;
- 2 `STZ absolute` candidates with encoded operand `$AE93`;
- no hits in the other enumerated store/read-modify-write families;
- 7 candidates classified as PC type-2 encoded-operand writers;
- 9 candidates categorized as enemy/AI, explicit non-type-2, item/scratch, or
  scratch-clear contexts;
- a complete partition of those 16 exact-operand candidates;
- a canonical candidate-ledger size of 464 bytes and SHA-256
  `53ab189afdcd922a766c3df72ae3706af5067270a9e1761d07764b54d8094a7b`.

That partition is complete only for the exact raw candidate set. It is not an
instruction-start proof, control-flow graph, DBR proof, call graph, or runtime
trace.

The 65C816 accumulator-width issue requires an additional negative control: a
16-bit accumulator store encoded to `$AE92` could also write adjacent byte
`$AE93`. The report therefore records 11 raw `STA absolute` candidates whose
encoded operand is `$AE92`. It does not establish their M width and sets both
`adjacent_ae92_effective_write_to_ae93_proved` and
`all_effective_writes_to_ae93_claimed` to false.

The census also does not rule out indexed effective addresses, direct-page or
indirect addressing, pointer-derived stores, block moves, DMA, or other
battle-state writers. The helper-reference patterns are raw candidates, not a
complete helper-entry CFG. Consequently, absence of a fixed `$7E` producer in
this census cannot be used as a free-space or unused-row conclusion.

## Reproduction and pinned identities

Supply a legally obtained, headerless canonical input that matches the hashes
below. The tool accepts the ROM as a positional input, opens it read-only,
prints one compact metadata-only JSON report to standard output, and has no
output-file option:

```powershell
python tools/audit_battle_action_package_topology_v0.py `
  "PATH_TO_CANONICAL_HEADERLESS_ROM" `
  --compact
```

Expected result: exit code `0`, empty standard error, one JSON object on
standard output, and no side effects. The report hash below covers the
auditor's canonical JSON bytes—ASCII, `ensure_ascii=true`, sorted keys, compact
separators—without the command-line newline.

| Artifact | Exact size | SHA-256 |
| --- | ---: | --- |
| canonical headerless ROM input | 4,194,304 bytes | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| auditor source | 73,179 bytes | `2760e8bc3b2bf56cdeeb985a69a69abebb7f8120ee7b76e344593f0c59246952` |
| reference contract | 23,353 bytes | `e6e3c23fd86927e1fa443cb46e67aed100693bb7c0dc14f5c1dce01b7a6419b7` |
| focused test source | 35,330 bytes | `bed108c86bd3b9da85a2109a8c956984966e7eee0e5f4c8828930eb0b96db9db` |
| semantic payload, excluding `artifact_identity` | 35,970 bytes | `dd9fdca3df71093873e723276778d066d162447e138a65ba3491fc214a6585c6` |
| complete canonical report, including identity envelope | 36,390 bytes | `7b201b7af2e6ec48459b802631b62495b2859ac09f5258ec61dd969f7a88871f` |

The canonical ROM SHA-1 is
`de5822f4f2f7a55acb8926d4c0eaa63d5d989312`. The report's schema-shape
SHA-256 is
`e4937373bb7961684ef085a9513a3c63298297bc608cd285fd67fc6d8e311e4b`.
The full report deliberately does not contain a self-hash; its identity
envelope hashes the semantic payload that excludes that envelope.

The canonical audit pins 20 bounded machine-code spans and 11 table spans.
Every bounded preimage and the complete ROM identity must match or the audit
fails closed. The interpretive source is `dscotton/ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`; it is
`documented-interpretive-only`, while the matching canonical machine preimages
are authoritative for this result.

The focused suite was run with:

```powershell
python -m unittest tests.test_battle_action_package_topology_v0
```

It passed all 17 tests against the pinned canonical input. The tests also
cover synthetic descriptor endianness, mask alternatives, zero-mask and
boundary cases, bank-identity negative controls, duplicate-key/reference
drift rejection, deterministic stdout-only CLI behavior, complete report
closure, and confirmation that the ROM size, hash, and modification timestamp
are unchanged.

## Evidence ceiling and nonclaims

Evidence level: `verified-static` for the pinned canonical image and exact
auditor/reference identities above.

The following remain explicitly unproved:

- battle-animation opcode or operand decoding;
- a transitive CFG across calls, subscripts, conditions, fallthrough, or
  command `$1E` cross-bank behavior;
- runtime reachability, execution order, frequency, story-state conditions, or
  loader lifetime;
- descriptor owner-bit runtime roles or any mapping from those bits to logical
  PCs;
- visual pose, graphics, effect, palette, sound, or source-role semantics for
  any script entrypoint;
- any free resolver entry, free config row, free ROM span, or safe adjacent
  table extension;
- a complete effective-writer graph for `$AE93`;
- logical PC `$07`, Schala action IDs, Focus Pulse, Schala items, an original
  battle frame, or an eighth-character battle binding;
- an expanded-bank reader, production allocation, instruction hook, ROM
  mutation, patch, save/state/trace artifact, or emulator runtime result.

The next safe use of this census is to design and separately prove an explicit
expanded-bank package reader and then decode only the required command paths.
It is not authority to install a hook or to infer that an unreferenced value is
available.
