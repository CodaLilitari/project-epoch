# Playable-character `$50`-byte record schema audit

Status: complete bounded static audit; no PC `$07` record or ROM patch installed  
Evidence: `verified-static` unless a row says otherwise  
Last updated: 2026-07-27  
Target: Project Epoch logical playable PC `$07`

## Outcome

The canonical playable-character initialization record is now mapped closely
enough to define the remaining PC `$07` engineering gates without pretending
that the vanilla bytes after character 6 are a record.

The central results are:

1. Vanilla has exactly seven `$50`-byte records at
   `$CC:0000-$CC:022F`. A hypothetical record 7 would start at `$CC:0230`,
   but that address is the seven-character learned-tech compatibility state.
2. The normal new-game seed at `$C2:956E` copies `$280` bytes in one move.
   That is seven records plus `$50` bytes of compatibility state. It is not an
   eight-record copy.
3. The alternate attract/demo initializer at `$FD:B2DE` is independently
   unsafe for PC `$07`: its record-shaped destination loop runs eight times,
   while each selected HP/MP source block contains only seven eight-byte rows.
4. Record `+$01` is only partially mapped. Bits 7-4 select one of four innate
   element modifier slots; bits 3-0 remain unmapped. Schala's Shadow selector
   is high bit `$40`, but copying Magus's complete `$42` is not approved.
5. Record `+$02` is also only partially mapped. Bit 0 is the near-fatal flag
   and bit 4 is “all single techs learned.” Every canonical template starts at
   `$80`, but bit 7's meaning remains unmapped.
6. The actual stat-growth order is
   `Power, Stamina, Speed, Hit, Evade, Magic, Magic Defense`. Speed's growth
   column is skipped. This differs from the base-stat byte order.
7. The `$FF` run at `+$36-$4F` is a template sentinel, not free space and not
   a durable serialized payload. Menu and battle code recompute and repurpose
   that tail, and battle commits the entire first `$50` bytes back to the live
   record.

This audit does not authorize a production record, a graphics source, an item
record, a tech record, or an allocation. It emits no character-record bytes,
graphics, dialogue, saves, states, or patched ROM.

## Pinned evidence and reproduction

### Canonical ROM

The tool accepts only the headerless Chrono Trigger US Rev0 ROM:

| Property | Value |
| --- | --- |
| Size | `$400000` bytes |
| SHA-1 | `de5822f4f2f7a55acb8926d4c0eaa63d5d989312` |
| SHA-256 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |

The local ROM remains under `private/` and is never emitted.

### Reconstructed engine source

Pinned `ct_disassembly` commit:
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`.

The audit pins hashes and named anchors in `bank_C1.asm`, `bank_C2.asm`,
`bank_FD.asm`, `battle_work.asm`, and the eight relevant bank-CC table
definitions. Source drift fails closed.

### Canonical metadata-table hashes

| Table | Address/shape | SHA-256 |
| --- | --- | --- |
| PC initialization records | `$CC:0000`, 7 × `$50` | `083676606d3339767c5b189594390dccbcb922adf27380178a4cb96cadc35fa0` |
| compatibility span occupying record 7 | `$CC:0230`, `$50` bytes | `ca33129e383fea5c0ad8e176d7847f5118ccbbf77ea1098da9ec1f24c0451123` |
| HP growth | `$CC:258A`, 7 × 8 | `cefb961e2f1c15f0b129903c242c36f937d69c729699aad5c626fdd4c27fecc3` |
| MP growth | `$CC:25C2`, 7 × 8 | `b95a1315c22dde61e9d3811f94d517186db010323ba5e348ff22ab3caa7a7641` |
| stat growth | `$CC:25FA`, 8 × 7 | `899a8c7c2858b9e0190a37c5866fdb073c6167f2ab32be509cde49777fe8e94d` |
| EXP to next level | `$CC:2632`, 100 × 2 | `e487b79afff9984803da858c47042702a8bdda1fea95d427e16210b0743a0727` |
| TP to next single tech | `$CC:26FA`, 7 × `$10` bytes | `8a47a0529a92c6d02aa5598e19c35e53e115721f9aa4c1b43ebca222c69287df` |
| combo-group requirement index | `$CC:2778`, 25 live × 5 plus one terminator | `cbe1b5bf58a5b808ea161cc2e6a64b4c57a01871a96db1aef5e539e14370519f` |
| attract/demo HP/MP pointer table | `$FD:B99C`, 3 × 2 | `a0c4aff4501d253400f370a56c1cc1bff57def9f9e850c6f670fdfd85f0d2776` |

Run the metadata-only audit and save its report under the ignored private
tree:

```powershell
python tools/audit_pc_init_record_schema.py `
  --rom "private/input/rom_archive/Chrono Trigger (USA).sfc" `
  --output "private/build/pc_init_record_schema_audit/pc_init_record_schema_audit.json"
```

Run its focused tests:

```powershell
python tests/test_pc_init_record_schema_audit.py -v
```

The report contains addresses, counts, hashes, classifications, invariants,
and bounded exception lists only. It contains no raw record or table payload.

## Full primary byte map

The “primary meaning” column assigns every byte exactly once. The final tail
has additional context-specific views described later.

| Offset | Size | Primary meaning | Evidence and lifecycle |
| --- | ---: | --- | --- |
| `+$00` | 1 | logical/portrait identity | `verified-static`; used as the character index by growth and formula/name paths |
| `+$01` | 1 | innate-element selector plus unmapped low flags | `verified-static`; partial mapping: high nibble mapped, low nibble unmapped |
| `+$02` | 1 | PC progress flags | `verified-static`; partial mapping: bits 0 and 4 mapped |
| `+$03-$04` | 2 | current HP | little-endian u16 |
| `+$05-$06` | 2 | base max HP | little-endian u16; level growth mutates it |
| `+$07-$08` | 2 | current MP | little-endian u16 |
| `+$09-$0A` | 2 | base max MP | little-endian u16; level growth mutates it |
| `+$0B` | 1 | base Power | persistent base stat |
| `+$0C` | 1 | base Stamina | persistent base stat |
| `+$0D` | 1 | base Speed | persistent; not growth-recomputed |
| `+$0E` | 1 | base Magic | persistent base stat |
| `+$0F` | 1 | base Hit | persistent base stat |
| `+$10` | 1 | base Evade | persistent base stat |
| `+$11` | 1 | base Magic Defense | persistent base stat |
| `+$12` | 1 | level | capped at 99 |
| `+$13-$15` | 3 | cumulative EXP | little-endian u24; capped at 9,999,999 |
| `+$16-$18` | 3 | cumulative TP | little-endian u24; capped at 9,999,999 |
| `+$19` | 1 | combatant category mask | `verified-static`; partial mapping; PC templates seed zero |
| `+$1A` | 1 | secondary combatant effect/category flags | `verified-static`; partial mapping; PC templates seed zero |
| `+$1B` | 1 | enemy-side attack variant/context | `verified-static`; partial mapping; PC templates seed zero |
| `+$1C` | 1 | unmapped | PC templates seed zero |
| `+$1D-$21` | 5 | current status groups 0-4 | `verified-static`; partial mapping |
| `+$22-$26` | 5 | permanent/equipment status and immunity groups 0-4 | `verified-static`; partial mapping |
| `+$27` | 1 | helmet item ID | equipment source |
| `+$28` | 1 | armor item ID | equipment source |
| `+$29` | 1 | weapon item ID | equipment source |
| `+$2A` | 1 | accessory item ID | equipment source |
| `+$2B-$2C` | 2 | remaining EXP to next level | little-endian u16 |
| `+$2D-$2E` | 2 | remaining TP to next single tech | little-endian u16 |
| `+$2F-$35` | 7 | level-1 stat baselines | engine order is Power, Stamina, unused Speed, Hit, Evade, Magic, Magic Defense |
| `+$36-$3C` | 7 | equipment-adjusted/live stats | base-stat order: Power, Stamina, Speed, Magic, Hit, Evade, Magic Defense |
| `+$3D` | 1 | derived Attack | recomputed |
| `+$3E` | 1 | derived Defense | recomputed |
| `+$3F-$42` | 4 | context-derived tail | menu uses `+$3F-$40` for adjusted max HP; battle overwrites all four as element modifiers |
| `+$43-$47` | 5 | battle weapon descriptor remainder | reloaded from equipment data |
| `+$48-$4A` | 3 | battle armor descriptor | reloaded from equipment data |
| `+$4B-$4E` | 4 | battle accessory descriptor | reloaded from equipment data |
| `+$4F` | 1 | unmapped tail byte | initial `$FF` sentinel; no durable source meaning proved |

Canonical-template invariants:

- `+$00` is `$00-$06` in order;
- current HP equals base max HP and current MP equals base max MP;
- `+$19-$26` is zero;
- `+$31` is zero;
- `+$36-$4F` is `$FF`.

Those are observations about the seven vanilla templates. In particular,
zeroes and `$FF` bytes are not evidence of free space.

## Record `+$01`: innate element and unresolved low nibble

Two independent consumers establish the high-nibble behavior:

- `$FD:B3FE` initializes four battle element-modifier bytes to 4, checks bits
  `$80/$40/$20/$10` in that priority order, and changes the selected byte to 5.
- `$C1:E440` uses the same priority to select one of the four element bytes
  during the relevant damage-formula path.

The conventional element labels correlate with the vanilla characters:

| High bit | Conventional slot | Vanilla templates carrying it |
| ---: | --- | --- |
| `$80` | Lightning | Crono |
| `$40` | Shadow | Robo, Magus |
| `$20` | Water | Marle, Frog |
| `$10` | Fire | Lucca, Ayla |

The complete canonical `+$01` values are:

| PC | Value | High selector | Low nibble |
| --- | ---: | ---: | ---: |
| Crono | `$86` | `$80` | `$06` |
| Marle | `$2A` | `$20` | `$0A` |
| Lucca | `$1A` | `$10` | `$0A` |
| Robo | `$44` | `$40` | `$04` |
| Frog | `$24` | `$20` | `$04` |
| Ayla | `$1C` | `$10` | `$0C` |
| Magus | `$42` | `$40` | `$02` |

The bounded source audit found no direct runtime consumer of the low nibble in
the live PC record. That is not proof that it is globally unused.

PC `$07` rule: Schala's proposed Shadow identity selects high bit `$40`.
Do not finalize her complete `+$01` byte and do not copy Magus's `$42` until
the low nibble is either traced or deliberately replaced by a proved adapter.

## Record `+$02`: progress flags and unknown `$80` seed

All seven canonical templates seed `+$02` to `$80`.

Mapped bits:

| Bit | Meaning | Static route |
| ---: | --- | --- |
| `$01` | near-fatal/low-HP flag | `$C1:B093` clears it, then sets it when current HP is at most one eighth of base max HP; `$C1:302E` consumes it |
| `$10` | all single techs learned | `$C1:F52A` sets it when the learned count reaches the character maximum; `$C1:F23E` and `$C1:F3CE` suppress further TP learning |

Bits `$02`, `$04`, `$08`, `$20`, `$40`, and `$80` remain unmapped in this
bounded audit. In particular, `$80` is a canonical seed invariant, not a
proved semantic default for a new PC. PC `$07` must not ship until this bit is
traced across new game, load, battle, reset, and New Game+ or intentionally
owned by a validated adapter.

## Initialization and copy routes

### Normal new-game seed: `$C2:956E`

`NewGame_SeedCharStatsAndTechs` executes:

- source `$CC:0000`;
- destination `$7E:2600`;
- MVN count register `$027F`, meaning `$280` copied bytes.

The copied layout is:

```text
$000-$22F  seven PC records
+$230-$236  seven learned-single counts
+$237-$23D  seven learned-single masks
+$23E-$27F  remaining compatibility/tech state
```

Therefore `$7E:2830-$7E:287F` is populated with compatibility state. Calling it
an eighth record would conflate logical PC ID, live record storage, and
learned-tech storage.

### Alternate attract/demo initialization: `$FD:B2DE`

When `$7E:2989` bit 5 is set, `NewGame_InitCharacterData`:

1. calls `$FD:B33F`;
2. selects one of three HP/MP blocks through the three-word table at
   `$FD:B99C-$FD:B9A1` using `$7E:29AC`;
3. loops destinations in `$50`-byte strides through `Y=$027F`;
4. writes `$23` to record Power and Magic, `$80` to Stamina, and four u16
   HP/MP values from the selected source row.

The destination loop has eight iterations. Each selected HP/MP block has only
seven rows of 8 bytes. The eighth iteration therefore reads eight bytes beyond
that block and writes into the natural PC `$07` destination
`$7E:2830-$7E:287F`.

The first block begins immediately at `$FD:B9A2`, after the third pointer.
Its first two data bytes are `$20 $03`; they are an HP value, not a fourth
pointer. The audit pins the pointer table to six bytes so this boundary cannot
silently drift back into the first block. The three `$38`-byte blocks occupy
`$FD:B9A2-$FD:BA49`; the pinned next-data symbol begins at `$FD:BA4A`.

This route needs an explicit PC `$07` adapter even after the normal new-game
seed is split. A normal-mode-only fix is incomplete.

### Template copy helper: `$FD:B33F`

`CopyCharInitData` stops at source offset `$0230`; it copies exactly seven
records. It neither copies nor creates an eighth record.

### Post-battle combo-learning index

`verified-static`

The post-battle scan at `$C1:F25F-$C1:F2D9` resets `$7E:B2D2`, advances
through five-byte records at `$CC:2778`, and increments that counter once for
each rejected participant mask. The 26th record is the first and only
first-byte-`$FF` sentinel; the sentinel exits before `$C1:F29C` builds its
`$283E + counter` pointer.

There are therefore 25 reachable records: 15 dual groups followed by 10
triple groups. The largest live index is `$18`, so the read/modify/write at
`$C1:F5C1/$C1:F5C7` is bounded to `$7E:283E-$7E:2856`. It cannot reach the
equipped-rock flags at `$7E:2857-$7E:285B`.
None of the 25 participant masks uses bit `$01`, so vanilla defines no combo
group involving logical PC `$07`. Appending one active row in place would use
index `$19` and collide with the first rock flag at `$2857`; Schala's combo
state requires an explicitly expanded namespace.

`tools/audit_pc_init_record_schema.py` pins the canonical requirement table,
the exact scan and access code spans, and the corresponding disassembly
sources. It validates the sentinel, group/width shape, unique participant
keys, requirement-pointer extent, and maximum address while emitting no raw
table bytes. This closes this one computed consumer; it does not prove that
no other hidden `incbin`, computed-pointer, or block-move path reaches the
remaining compatibility bytes.

## Live menu and battle lifecycle

| Route | Behavior | PC `$07` gate |
| --- | --- | --- |
| `$C2:8839` | computes `$7E:2600 + id*$50` and copies `$50` bytes to the menu buffer | ID `$07` aliases compatibility state until relocation |
| `$C2:9137` | recomputes equipment data, writes current HP, and commits `+$36-$40` | requires valid item descriptors and a real record |
| `$C2:99B2` | recalculates only IDs `$00-$06` | hard-coded loop bound must be adapted |
| `$FD:AE52` | copies `$50` live bytes to an `$80`-byte battle record, then zeroes `+$50-$7F` | ID `$07` aliases compatibility state |
| `$C1:B442` | commits every byte `+$00-$4F` from battle work to the live record | ID `$07` would overwrite compatibility state |
| `$C1:CF15` | reloads weapon, helmet, armor, and accessory descriptors for each party record | item/source index adapters must accept ID `$07` |
| event `$11C`, object `$09`, location `$1D1` | 12 absolute commands update four tech counts and learned masks in `$2830-$283B` | translate the exact fields to `$2CA0-$2CAB`; unchanged operands would write Schala's record |

The preferred architecture remains:

- prove and relocate the complete vanilla compatibility block from
  `$7E:2830-$7E:287F` to candidate `$7E:2CA0-$7E:2CEF`;
- retain its vanilla save/editor meanings at slot-relative
  `$0430-$047F`;
- use natural live record `$7E:2830-$7E:287F` only after the relocation
  matrix passes.

This document does not declare `$7E:2CA0-$7E:2CEF` free.

## Stat baseline and growth semantics

`Battle_LevelUp_RecomputeStats` at `$C1:F630` uses record `+$00` to select
one seven-byte row at `$CC:25FA`.

The actual mapping is:

| Growth index | Stat destination | Baseline | Behavior |
| ---: | ---: | ---: | --- |
| 0 | Power `+$0B` | `+$2F` | recomputed |
| 1 | Stamina `+$0C` | `+$30` | recomputed |
| 2 | Speed `+$0D` | `+$31` | skipped; the baseline is zero |
| 3 | Hit `+$0F` | `+$32` | recomputed |
| 4 | Evade `+$10` | `+$33` | recomputed |
| 5 | Magic `+$0E` | `+$34` | recomputed |
| 6 | Magic Defense `+$11` | `+$35` | recomputed |

For the six recomputed stats:

```text
stat = baseline + floor(growth * (level - 1) / 100)
```

The routine caps the seven base-stat bytes at 99 and then caps Speed at 50.
Speed is preserved rather than derived from growth.

The stat table contains eight rows, but row 7 is all zero. This is a
`verified-static` collision fact, not a finished PC `$07` definition and not
proof of free authoring space.

The HP and MP growth tables each contain only seven rows. `$C1:F871` indexes
them directly by `record +$00`:

- HP row 7 enters MP-growth data;
- MP row 7 enters stat-growth data.

They must be relocated or resolved through bounded eight-character adapters.

### Join templates are not pure formula projections

Every vanilla template's cumulative EXP matches the shared curve at its
starting level, but several join-time base stats deliberately differ from the
baseline/growth projection:

- Marle: Evade;
- Lucca: Evade, Magic, Magic Defense;
- Robo: Hit, Evade;
- Magus: Hit.

This means baselines and growth are future level-up inputs. They are not a rule
that every join template must already equal the formula at recruitment.

For Schala, the builder must choose:

- deliberate authored join stats at the selected recruitment level;
- deliberate level-1 baselines;
- deliberate growth rows;
- a tested first-level-up transition between them.

Do not derive one set from the other by assuming all vanilla templates do so.

## EXP and TP fields

### EXP

`+$13-$15` is a u24 cumulative total. `$C1:F908` adds battle EXP and caps it at
9,999,999.

`+$2B-$2C` is the u16 remaining amount to the next level. `$C1:F7B9` consumes
it, increments the level, and reloads it from the shared 100-entry table at
`$CC:2632`.

All seven canonical total-EXP values equal the cumulative shared curve.
Six templates also seed `+$2B` from the table at their current level. Magus is
the explicit exception: his level-37 template seeds the value found at shared
table index 40. Treat this as a join-time exception, not a general formula.

### TP

`+$16-$18` is a u24 cumulative TP total, not a u16. `$C1:F427-$C1:F458`
propagates carry into the third byte and caps the total at 9,999,999.

`+$2D-$2E` is the u16 remaining amount to the next single tech.
`$C1:F39A` indexes `$CC:26FA` as:

```text
character_id * $10 + learned_single_count * 2
```

The TP table shape is seven rows × `$10` bytes, or eight u16 thresholds per
character. It is not 16 thresholds per character. Every canonical template's
`+$2D` matches its row at the seeded learned-single count.

PC `$07` has no TP row. Direct ID `$07` indexing enters the next table.

## Context-derived tail `+$36-$4F`

All canonical templates seed this 26-byte range to `$FF`, but the runtime does
not preserve it as an opaque source blob:

1. `$C2:9137` writes equipment-adjusted stats, Attack, Defense, and adjusted
   max HP through `+$40`.
2. `$FD:B3FE` overwrites `+$3F-$42` in battle work with four element
   modifiers.
3. `$C1:CF15` reloads equipment descriptors into `+$43-$4E` and battle-only
   helmet data at `+$70`.
4. `$C1:B442` commits the complete first `$50` work bytes back to live state.

HP accessories also temporarily increase base max HP at `+$05` in battle.
Both battle-end paths restore the backed-up base max HP before the `$50`-byte
commit.

Builder rule: author the stable source fields, seed the canonical sentinel tail
only where the relevant initialization route expects it, and then call the
proved recompute paths. Do not serialize battle residue or treat `$FF` as
permanent data.

## PC `$07` implementation checklist

A production eighth-character record remains blocked on all of the following:

1. Complete the remaining menu, battle, save, New Game+, attract/demo, erase,
   reset, and transition canaries for compatibility-block candidate
   `$7E:2CA0-$7E:2CEF`.
2. Split or adapt `$C2:956E` so the eighth record and relocated compatibility
   state are initialized as separate structures.
3. Adapt both `$FD:B33F` and the eight-iteration `$FD:B2DE` route.
4. Author a complete original `$50`-byte Schala record schema. The separate
   Project Epoch `$48`-byte progression descriptor must not be serialized as
   though it were a vanilla record.
5. Resolve the full `+$01` byte and the meaning/policy of `+$02` bit 7.
6. Add explicit eighth rows or bounded resolvers for HP, MP, stat, and TP
   growth data. A zero row or adjacent table is never an allocation.
7. Extend menu recomputation and every equipment descriptor/classification
   adapter before using original Schala items.
8. Prove first recruitment, reserve recruitment, first battle, battle exit,
   first level-up, first TP award, last single-tech learn, save/load, New
   Game+, exact-slot erase, attract/demo, and reset.
9. Re-run the metadata audit and focused/full test suites, preserve report
   hashes, and upgrade claims to `verified-runtime` only after recorded
   emulator reproduction.

Graphics and animation are separate namespaces. This record audit does not
permit overwriting graphics source index `$07`, relabeling the Schala NPC
descriptor as a PC, or treating adjacent actor data as free. The Phase A
provider may reconstruct the pinned canonical Schala family transiently from
the user's clean ROM only through independent PC `$07` adapters; no extracted
bytes enter source control. Phase B replacement art remains separately
original and provenance-backed.

## Evidence boundary

This work establishes static table bounds, record field semantics, copy
lengths, formulas, and known exceptions. It does not yet prove:

- the meaning of record `+$01` bits 3-0;
- the meaning of record `+$02` bits other than 0 and 4;
- a PC meaning for `+$1C` or `+$4F`;
- that the compatibility relocation candidate is runtime-safe;
- that any new item, tech, graphics, or ROM allocation is installed;
- that a full eighth-character save/load/recruitment path works.

Those remain explicit gates, not implied successes.
