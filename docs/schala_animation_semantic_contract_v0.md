# Schala animation semantic contract v0

Status: `pass-metadata-only-with-open-gates`
Evidence ceiling: `verified-static`
Production status: not ROM-installable

## Outcome

The current 16-frame Schala body packet now has a minimal semantic contract
against the canonical player-character animation engine. The contract is
strictly read-only and metadata-only. It proves enough of the native stream
shape and consumer namespaces to continue source-role animation authoring
without pretending that source ordinals are native animation IDs.

Static evidence is sufficient now for:

- retaining the current 16 source frames in their established source order;
- planning additional source poses by field, menu, and battle role;
- writing candidate primary-frame and auxiliary-timing token sequences;
- detecting overlap conflicts under the native `entrypoint * 4` rule; and
- keeping visual names separate from engine anchors whose appearance is not
  yet proved.

Static evidence is not sufficient now for:

- emitting a complete Schala animation stream or production packet;
- assigning any source frame to a native animation entrypoint;
- selecting a ROM address, expanded allocation, pointer, or instruction site;
- installing an expanded-bank reader adapter;
- claiming a battle sprite or logical PC `$07` runtime; or
- declaring the remaining Magus-adjacent auxiliary tail free.

The machine-readable authority is
`references/schala_animation_semantic_contract_v0.json`, reproduced by
`tools/audit_schala_animation_semantic_contract_v0.py`. The current report is
68,305 bytes with SHA-256
`50374adab6ad07522184b8b0ffc26300f3dd15abe7e817bd48263b20c3a2b015`.
It contains decoded metadata and hashes, never extracted stream bytes.

## Exact inputs and output

The audit accepts one input argument, `--rom`, and emits canonical JSON only to
standard output. It has no output-file, build, patch, allocation, or install
mode.

The complete machine inputs are:

1. A private, headerless 4 MiB Chrono Trigger US Rev0 ROM, accepted only at:
   SHA-1 `de5822f4f2f7a55acb8926d4c0eaa63d5d989312` and SHA-256
   `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
2. `references/schala_current_body_packet_v0.json`, exactly 11,953 bytes,
   SHA-256
   `c5a04304739e5fac3125cb840e9745bafae0f45b0b2869b4743b5d25c1c1313b`.
   The audit also rebuilds this report from its source authoring inputs and
   requires byte equality; a matching stale report is not enough.

The ignored nested checkout at `references/ct_disassembly`, expected at commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1` from
`https://github.com/dscotton/ct_disassembly`, is an interpretive reference only.
Its labels and commentary aid interpretation, but the auditor does not read or
verify that checkout, and a clean Project Epoch clone does not contain or need
it. Canonical ROM preimages are the byte authority.

The JSON output records scope, inputs, canonical engine profiles, consumer
roles, current authoring coverage, stop gates, evidence labels, and explicit
nonclaims. It contains no pixel rows, tile words, primary or auxiliary byte
streams, patch payload, save/state/trace content, or private ROM path.

## Native stream contract

### Facing order and source order are different namespaces

The engine's four primary facing blocks use numeric values `$00-$03` in order:

1. up;
2. down;
3. left; and
4. right.

The existing cardinal source roles were authored in down, up, left, right
order. That order remains untouched in the 16-frame packet. The auditor
records both orders and requires
`source_role_order_is_engine_facing_order = false`; it does not silently
reorder art or reinterpret a source ordinal as an engine position.

The numeric immediate order and dispatch geometry are `verified-static` from
the canonical `$C0:5535-$C0:5544` preimage. The human-readable direction names
are `documented` by the interpretive disassembly and are not represented as a
machine-input claim.

### Primary stream

The root word at `$E4:FFE4` resolves to the primary pointer table at
`$E4:2600`. The table supplies eight boundaries for the seven vanilla PCs.
Each PC span divides into four equal facing blocks. The primary stream unit is
an assembly-frame ID, and `$FF` is the field loop/end marker.

Animation `N` begins at byte offset `N * 4` within the selected facing block.
This is an entrypoint rule, not a four-byte record rule. One sequence may be a
suffix of another, and two entrypoints may overlap. Candidate authoring is
valid only when every shared primary token and every shared auxiliary token
agrees at the same position.

### Auxiliary timing/control stream

The root word at `$E4:FFE6` resolves to the auxiliary pointer table at
`$E4:2800`. The pinned nine-word sequence is:

`A800, A928, AA20, AB3C, AC58, AD70, AEC0, B600, B614`.

For PCs `$00-$05`, the next playable-PC pointer bounds the auxiliary span. For
Magus, the required span is derived from the primary facing size:
`$E4:AEC0-$E4:AFB4`. This is exactly one Magus primary facing block. The next
table pointer is `$E4:B600`, not `$E4:AFB4`, and the successor `$E4:B614`
proves that `$E4:B600-$E4:B613` is an occupied table entry. Its actor meaning
is not classified here. `$E4:AFB4-$E4:B5FF` also remains unclassified and is
not free space.

The canonical PC evidence establishes:

- one auxiliary block per PC, equal in length to one primary facing block;
- a nonzero field or battle value is consumed as a raw delay;
- zero reaches a consumer-specific stop, reset, or repeat branch;
- battle preloading shifts each of the first eight auxiliary values right
  once; and
- at every declared field, menu, and battle anchor, the first auxiliary zero aligns
  with the first primary `$FF` in all four facings.

It does not establish global equality of every auxiliary-zero position and
every primary-`$FF` position across a whole block. The audit deliberately
requires that stronger and false inference to remain absent.

## Consumer namespaces

### Field

The automatic field entrypoint minimum is:

| Entrypoint | Proved consumer condition |
|---:|---|
| `$00` | default/reset path |
| `$01` | walking path below the run threshold |
| `$06` | normal run path outside the alternate-player branch |
| `$17` | alternate player run branch when `$1D32 == 0`, `$1D33 == 0`, and `$E5 == 0` |
| `$19` | player no-movement branch when `$62 == 2` |
| `$1B` | special movement with move-mode bit 2 and a vertical facing component |
| `$21` | rare idle-counter and RNG branch |

Event operations `$AA`, `$AB`, `$AE`, `$B3`, `$B4`, and `$B7` consume the
animation-entrypoint namespace. Operation `$AC` instead selects a static
assembly-frame ID. A complete playable-PC location-event operand census is
still open.

### Menu

The party-exchange menu span `$C2:C973-$C2:C9AD` proves three roles written to
the walking-sprite animation field at `$1811` plus the character slot offset:

| Entrypoint | Proved menu role |
|---:|---|
| `$00` | reset sweep before highlighting, with the loop passing indices `$08` through `$00` |
| `$01` | hovered slot read from `$0F0D` |
| `$0B` | picked slot read from `$0F00` when bit 7 is clear |

The pointer setup span `$C2:F422-$C2:F4EB` assigns bank `$E4`, resolves the
primary and auxiliary roots through `$E4:FFE4/$E4:FFE6`, and reads both tables
from bank `$E4`. The menu tick at `$C2:F69D-$C2:F706` independently applies
the `animation ID * 4` rule to the primary and auxiliary bases.

### Battle fixed minimum

The battle fixed-entrypoint minimum is
`$00, $03, $08, $0A, $0C, $12, $1A, $23`. These are engine anchors. They are
not Schala pose bindings, and the visual meanings of `$08`, `$0A`, and `$0C`
remain unresolved.

The transition branches are exact:

- Battle start at `$C1:34DB` writes raw `$30`, which selects entrypoint `$0C`,
  only for a slot whose `$A09B` is clear; otherwise that slot receives `$00`.
- Service-dispatch ID 9 at `$C1:354D` writes raw `$20`, entrypoint `$08`, to
  all three PC offset words. The later `$96F5` presence gate decides which
  slots are processed.
- Service-dispatch ID 8 at `$C1:356D` returns early when
  `EventCommandD8Settings` bit 0 is set. Otherwise raw `$28`, entrypoint
  `$0A`, is selected only for a slot whose `$A09B` is clear; a set `$A09B`
  selects `$00`.
- The `$12` override occurs only after the state-table scan is exhausted, when
  critical-status bit 0 is set and the slot's `$A09B` is clear.

Battle animation command `$02` adds `entrypoint * 4` to both the primary and
auxiliary bases. The auxiliary reader at `$C1:42D0` and primary reader at
`$C1:4300` remain fixed to bank `$E4`.

## Decoded battle state table

`$CC:F77F-$CC:F7BF` is exactly sixteen four-field records followed by a
terminating `$FF` at `$CC:F7BF`. The complete 65-byte span has SHA-256
`1cfdd78e4dbe9c9c759d7b267053078b62ecd48fd1cf44d1df02346098cf07d7`.
The four decoded fields are a status-base-relative offset, required mask,
requested state value, and animation selector.

| Record | Status offset | Mask | Requested state | State write | Selector |
|---:|---:|---:|---:|:---:|---:|
| 0 | `$00` | `$80` | `$81` | suppressed by high bit | `$08` |
| 1 | `$01` | `$80` | `$02` | yes | `$00` |
| 2 | `$01` | `$04` | `$04` | yes | `$1A` |
| 3 | `$01` | `$02` | `$05` | yes | `$08` |
| 4 | `$01` | `$08` | `$08` | yes | `$FF` control case |
| 5 | `$01` | `$20` | `$0D` | yes | `$03` |
| 6 | `$01` | `$01` | `$09` | yes | `$03` |
| 7 | `$01` | `$40` | `$0E` | yes | `$03` |
| 8 | `$04` | `$80` | `$03` | yes | `$03` |
| 9 | `$09` | `$80` | `$03` | yes | `$03` |
| 10 | `$04` | `$40` | `$06` | yes | `$03` |
| 11 | `$09` | `$40` | `$06` | yes | `$03` |
| 12 | `$04` | `$04` | `$07` | yes | `$23` |
| 13 | `$09` | `$04` | `$07` | yes | `$23` |
| 14 | `$03` | `$80` | `$0C` | yes | `$03` |
| 15 | `$08` | `$80` | `$0C` | yes | `$03` |

The scan takes the first matching record in table order. Record 0 has one
additional branch: per-slot `$A119 != 0` forces record 0 to match even if its
status mask does not. No other record receives that treatment.

Before the scan, the default selector is `$00` when per-slot `$A09B` is
nonzero and `$03` when `$A09B` is zero. If no record matches, that default is
used unless the later, separately gated critical override selects `$12`.

Selector `$FF` is not dispatched literally. When record 4 matches:

- `$A0A7 != 0` skips the matched record and resumes scanning; and
- `$A0A7 == 0` substitutes entrypoint `$03`.

The meaning of `$A0A7` itself remains unresolved. Only these two branches are
claimed.

## Fixed-bank setup and reader census

Every source site in this census is covered by a pinned canonical code span:

| Context | Fixed-bank sites |
|---|---|
| Field auxiliary timing | `$C0:CA35`, `$C0:CA3D` |
| Field primary frame tile bank | `$C0:CBEE` |
| Battle state-transition reads | `$C1:2EBA`, `$C1:2EEB` |
| Battle pre-animation copies | `$C1:3639`, `$C1:3650` |
| Battle animation tick | `$C1:42D0`, `$C1:4300` |
| Battle PC pointer setup | `$CC:E9BC`, `$CC:E9C5`, `$CC:E9CE`, `$CC:E9D3`, `$CC:E9DC`, `$CC:E9E5`, `$CC:E9EF`, `$CC:E9F5`, `$CC:E9FB`, `$CC:EA01` |
| Menu PC pointer setup | `$C2:F42D`, `$C2:F431`, `$C2:F4C3`, `$C2:F4C8`, `$C2:F4E1`, `$C2:F4E6` |

The positive claim is limited: the canonical field, battle, and menu consumers
listed above resolve or read player-character animation data in fixed bank
`$E4`. This is a constraint on future architecture. It is not evidence that an
expanded-bank adapter exists, that any instruction site is approved for a
hook, or that any expanded address is allocated.

## Current authoring coverage

The report requires the exact existing 16-frame order and covers each frame
once:

- four cardinal idle source roles;
- three down-facing walk source roles;
- one battle-ready source pose;
- two battle-cast source poses; and
- six basic-attack source poses.

Every association remains `source-role-only-unbound` with `native_binding =
null` and `timing_binding = null`. The roles help identify missing art without
turning the current sequence into a native animation table.

The next safe authoring step is to enumerate complete facing coverage and
source-frame/timing token sequences for each actually used role. Normal
attack, cast, item, hurt, KO, revive, victory, and all eight Schala tech action
packages still require consumer-to-entrypoint mapping. Visual names must not
be inferred from a fixed numeric anchor alone.

## Fail-closed gates

The audit stops without a report if any of the following changes:

1. complete ROM size, SHA-1, or SHA-256;
2. current-body report size, hash, fresh rebuild, frame identities, or exact
   source order;
3. any pinned engine code/table span or SHA-256;
4. any primary boundary, any of the nine auxiliary pointers, or any of the six
   `$E4:FFE0-$E4:FFEB` roots;
5. four-facing span geometry, primary terminator-mask equality, or one-facing
   auxiliary length;
6. a canonical per-PC primary or auxiliary profile hash;
7. declared-anchor bounds, early termination, facing disagreement, or
   primary/auxiliary terminator misalignment;
8. the 16-record state-table geometry, values, selector set, terminator,
   record-0 special case, default behavior, or selector-`$FF` rule;
9. the battle fixed minimum or menu `$00/$01/$0B` roles;
10. the fixed-bank setup/reader census or its expanded-bank nonclaim;
11. a conflicting token at any overlapping candidate sequence position;
12. any production-facing scope flag; or
13. any forbidden raw-data field, leaked private ROM path, unsupported JSON
    value type, nested-schema drift, or exact-report identity drift.

The tool cannot make a ROM mutation. It neither calls the ROM-write-intent
guard nor qualifies for an exception, because it performs no write and emits
no patch or animation binary.

## Tests and reproduction

Set `CT_US_REV0_ROM` to the private canonical ROM for the ROM-backed tests:

```powershell
$env:CT_US_REV0_ROM = (Resolve-Path -LiteralPath '<private canonical ROM>')
python -m unittest tests.test_schala_animation_semantic_contract_v0 -v
```

To run the auditor directly:

```powershell
python tools/audit_schala_animation_semantic_contract_v0.py `
  --rom $env:CT_US_REV0_ROM
```

The focused suite covers:

- engine order, nine auxiliary pointers, six roots, and all fixed-bank sites;
- overlap acceptance and conflict rejection using abstract metadata tokens;
- absence of an output destination in the command-line parser;
- fail-closed handling of an explicitly configured missing ROM;
- a closed nested metadata shape that rejects unknown maps, integer/tuple
  streams, case-varied forbidden keys, and long encoded strings;
- canonical identity and every preimage span;
- exact primary/auxiliary profile geometry and anchor alignment;
- the Magus `$AFB4` end derivation and occupied `$B600/$B614` successors;
- all 16 decoded state records, record 0, defaults, selector `$FF`, and critical
  gate;
- exact battle-start/service 8/service 9/menu conditions;
- source-order separation and the 16 unbound authoring roles;
- static-evidence ceilings and production nonclaims;
- deliberate ROM/table/root/span mutations failing closed;
- no explicit artifact-write calls during report construction; and
- byte equality among fresh report generation, CLI standard output, and the
  pinned JSON report.

The current canonical-ROM result is 21 tests passed. Set
`PYTHONDONTWRITEBYTECODE=1` as shown by the repository validation workflow when
literal absence of incidental Python bytecode cache writes is required.

## Evidence labels

- `verified-static`: directly reproduced from the hash-gated canonical ROM or
  deterministic source-report rebuild.
- `documented`: direction names or commentary carried only by the separately
  identified interpretive disassembly reference.
- `hypothesis`: a current Schala source frame's authoring-role association;
  useful for planning but not a native binding.
- `not performed`: no new emulator/runtime trace was needed or claimed for
  this metadata-only v0 contract.

Runtime evidence remains mandatory before a future production installation
can claim real PC `$07` behavior, expanded-bank reading, menu/battle parity, or
safe allocation ownership.
