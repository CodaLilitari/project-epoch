# Project Epoch — PE-000 Character Data Atlas v0

> [!WARNING]
> **Superseded historical planning artifact (2026-08-24).** This v0 document is
> retained for provenance only; it is not the current Project Epoch data map,
> and its poison-save trace plan must not be executed. Project Epoch now
> verifies exactly seven `$50` PC records at slot-relative `$0200-$042F`.
> `$0430-$047F` is the vanilla seven-PC Tech/compatibility block—not an
> Epoch/vehicle or eighth-PC record—and must be preserved. `$0430-$0436` and
> `$0437-$043D` are the confirmed seven-PC Tech-progress and learned-mask
> arrays; later compatibility bytes are partially, not completely, mapped.
> `$0480` lies inside vanilla's first `$05B0` serialized bytes and is not
> approved storage. Base-record stat order and the separate growth-array order
> are distinct. Use the
> [current corrected map](../docs/project_epoch_corrected_character_data_map_v1.md),
> [playable-record schema audit](../docs/pc_init_record_schema_audit.md),
> [SRAM sidecar audit](../docs/sram_gap_sidecar_audit.md), and
> [developer guide](../docs/schala_eighth_character_developer_guide.md) for implementation
> decisions.

Prepared by Lily. Scope: establish the known save/runtime character-data namespaces before PE-001 menu trace or any new patch.

## Verdict

Yes: PE-000 should precede PE-001. The next patch should not be authored until the project has a concrete atlas of:

1. save-slot character records,
2. runtime/WRAM character buffers,
3. active-party identity bytes,
4. name slots,
5. Epoch's vehicle/non-PC data,
6. all places where raw party ID `$07` is resolved as if it were a normal PC.

The vanilla isolation test proved that an edited active-party byte `$07` alone makes vanilla CT render Epoch at save-select, LV-star garbage in menus, missing Marle/Lucca, duplicate Magus, and Gaspar/Old-Man sprite behavior. So `$07` is not just a graphics-loader problem. It is a character-data-resolution problem.

## Source anchors

### DataCrystal SRAM layout

DataCrystal says:

```text
SRAM file: 0x2000 bytes
Slot #1: 0x0000-0x09FF, 0x0A00 bytes
Slot #2: 0x0A00-0x13FF
Slot #3: 0x1400-0x1DFF
Checksums: 0x1FF0, 3 slots × 2 bytes

Save slot:
0x000 item type, 0x100 item count
0x200 characters
0x580 party members
0x5B0 names, 8 slots × 6 bytes
0x5E0 gold

Character structure: 0x50 bytes
```

Important contradiction: DataCrystal labels the character area as length `560`, while also naming Crono, Marle, Lucca, Robo, Frog, Ayla, Magus, and Epoch and defining records as `$50` bytes. `7 × $50 = $230 = 560`; `8 × $50 = $280 = 640`. Save-editor source and the actual Lavos save both support eight `$50` records ending at `$47F`, with Epoch/record-7 beginning at `$430`.

### EpochEditor / mcred source

EpochEditor constants:

```text
SRAM_FILE_LENGTH = 0x2000
SLOT_LENGTH = 0x0A00
FIRST_CHARACTER_OFFSET = 0x200
CHARACTER_SHEET_LENGTH = 0x50
PARTY_MEMBER_ONE/TWO/THREE = 0x580/0x581/0x582
MAX_CHARACTER_INDEX = 6
EMPTY_PARTY_SLOT = 0x80
GOLD_OFFSET = 0x5E0
```

EpochEditor `GameSlot` allocates `CharacterSheets = new ICharacterSheet[8]`, while party-member editing clamps valid party IDs to `$00-$06`. mcred's older editor explicitly defines:

```text
Crono  0x200
Marle  0x250
Lucca  0x2A0
Robo   0x2F0
Frog   0x340
Ayla   0x390
Magus  0x3E0
Epoch  0x430
```

That supports: eight save/editor character records exist, but only seven are valid active-party PC IDs.

## Character record field map, save-slot-relative

Based on DataCrystal and EpochEditor:

| Offset | Size | Field |
|---:|---:|---|
| `$00` | 1 | Name ID |
| `$01` | 1 | Character ID |
| `$03` | 2 | Current HP |
| `$05` | 2 | Max HP |
| `$07` | 2 | Current MP |
| `$09` | 2 | Max MP / Base Max HP, naming differs by source |
| `$0B` | 1 | Base Power |
| `$0C` | 1 | Base Stamina |
| `$0D` | 1 | Base Speed |
| `$0E` | 1 | Base Magic |
| `$0F` | 1 | Base Hit |
| `$10` | 1 | Base Evade |
| `$11` | 1 | Base Magic Defense |
| `$12` | 1 | Level |
| `$13` | 3 | Experience |
| `$27` | 1 | Helmet |
| `$28` | 1 | Armor |
| `$29` | 1 | Weapon |
| `$2A` | 1 | Accessory |
| `$2B` | 2 | Exp To Level |
| `$36` | 1 | Current Power |
| `$37` | 1 | Current Stamina |
| `$38` | 1 | Current Speed |
| `$39` | 1 | Current Magic |
| `$3A` | 1 | Current Hit |
| `$3B` | 1 | Current Evade |
| `$3C` | 1 | Current Magic Defense |
| `$3D` | 1 | Current Attack |
| `$3E` | 1 | Current Defense |
| `$3F` | 2 | Current Max HP |

Offsets `$02`, `$16-$26`, `$2D-$35`, and `$41-$4F` remain unmapped in this local atlas and require trace/source confirmation.

## Lavos SRM slot 1 observed records

Source save: uploaded `chrono_trigger.srm`, slot #1 base `$0000`, party bytes `$00 $01 $02` before editing.

| Rec | Slot-relative offset | Label | NameId | Name | CharId | Level | HP | MP | EXP | Equip bytes |
|---:|---:|---|---:|---|---:|---:|---|---|---:|---|
| 0 | `$0200` | Crono | `$00` | Crono | `$86` | 53 | 969/969 | 93/93 | 296708 | `8F 6B 55 9F` |
| 1 | `$0250` | Marle | `$01` | Marle | `$2A` | 54 | 898/898 | 97/97 | 306674 | `8F 6C 1A 9E` |
| 2 | `$02A0` | Lucca | `$02` | Lucca | `$1A` | 54 | 909/909 | 99/99 | 302182 | `8A 7A 28 A3` |
| 3 | `$02F0` | Robo | `$03` | Robo | `$44` | 51 | 922/999 | 51/83 | 266834 | `8E 69 37 98` |
| 4 | `$0340` | Frog | `$04` | Frog | `$24` | 49 | 604/894 | 61/87 | 249003 | `85 69 42 B4` |
| 5 | `$0390` | Ayla | `$05` | Ayla | `$1C` | 50 | 877/963 | 80/86 | 253250 | `81 62 45 AC` |
| 6 | `$03E0` | Magus | `$06` | Magus | `$42` | 51 | 844/952 | 92/98 | 260274 | `87 6F 4B 95` |
| 7 | `$0430` | Epoch / vehicle record | `$08` | out-of-name-table | `$08` | 192 | 1287/771 | 65535/65279 | 8446176 | `00 00 00 00` |

Record 7 raw first 0x50 bytes:

```text
0430: 08 08 08 07 05 03 03 ff ff ff fe f8 e0 e0 e0 e0
0440: c0 e0 c0 e0 e0 80 00 e0 00 00 00 00 00 80 00 80
0450: 00 80 00 00 00 00 00 00 00 00 00 00 ff ff ff ff
0460: ff ff 00 00 00 00 00 03 00 0a 00 00 07 00 0a 00
0470: 00 0f 00 0a 00 00 14 00 0a 00 00 1e 00 0a 00 00
```

This is not a normal PC record. It has an out-of-table `NameId` (`$08`) even though the name table has only 8 slots indexed `$00-$07`, impossible HP/MP-like values, and the `EXP = $80E0E0` pattern seen in the LV-star menu bug.

## Region after Epoch record

Slot-relative `$0480-$057F` in the uploaded Lavos save is all zero in slot #1. This is tempting as a Magus2/Gaspar save backing area, but PE-000 must not mark it safe yet. DataCrystal does not document this range; zero-filled save bytes can be unused, reserved, or conditionally used by event state. If Project Epoch uses `$0480` as save record 8, it should be versioned and guarded, not assumed vanilla-free.

## Namespaces to keep separate

```text
Active-party ID namespace:
  $00-$06 = vanilla playable PCs
  $07     = Project Epoch candidate logical PC, currently undefined in vanilla
  $80     = empty party slot in save/editor tooling

Save/editor record namespace:
  record 0 = $0200 Crono
  record 1 = $0250 Marle
  record 2 = $02A0 Lucca
  record 3 = $02F0 Robo
  record 4 = $0340 Frog
  record 5 = $0390 Ayla
  record 6 = $03E0 Magus
  record 7 = $0430 Epoch / vehicle data, preserve
  record 8 = $0480 candidate Project Epoch backing record, unverified save-space safety

Name namespace:
  8 slots only: $5B0-$5DF
  $5E0 begins gold
  no safe vanilla name slot 8

Graphics/source namespace:
  low indices are occupied engine actor/vehicle/NPC data
  do not write table entries 7 or 8
```

## What PE-000 should map before PE-001 patching

1. Which bytes from save `$0200-$047F` are copied to runtime WRAM, and where.
2. Whether save `$0480-$04CF` is ever copied/read by vanilla routines.
3. Whether save-select uses direct SRAM offsets or a WRAM mirror.
4. Whether the in-game menu detail panel reads `$7E2600 + id*$50`, `$7E2400 + offset`, or another compact table.
5. Whether record 7's `$80E0E0` EXP pattern reaches WRAM, and at which address.
6. How Epoch's save/editor record is consumed by vehicle/time-machine systems versus PC UI.
7. Where the party-swap menu maps `$07` to the Gaspar/Old-Man sprite.
8. Which routines distinguish party ID, character record index, character ID byte, portrait ID, and sprite/graphics source.

## Trace plan

Run against vanilla ROM first, with diagnostic saves only.

### Diagnostic saves

- Baseline vanilla save: party `$00 $01 $02`.
- Unknown-ID fuzzer: party `$00 $06 $07`, all records unchanged.
- Record-7 poison: party `$00 $06 $07`, set record 7 EXP to `$112233`, HP/MP/stats to recognizable values.
- Record-8 poison: party `$00 $06 $07`, set `$0480-$04CF` as Magus clone or poison pattern `$445566` in EXP-like field.
- Combined poison: record 7 EXP `$778899`, record 8 EXP `$AABBCC`.
- Duplicate control: party `$00 $06 $06`.

### Mesen-S break/watch targets

- Save party bytes in SRAM/mirror: slot-relative `$0580-$0582`; runtime `$7E2980-$7E2982`.
- Candidate WRAM PC buffer: `$7E2600-$7E287F` if community/TASVideos mapping is correct.
- Naive runtime record 7 window: `$7E2830-$7E287F`.
- Search patterns:
  - `$80E0E0` as bytes `E0 E0 80`
  - `$112233` as bytes `33 22 11`
  - `$445566` as bytes `66 55 44`
  - `$778899` as bytes `99 88 77`
  - `$AABBCC` as bytes `CC BB AA`

### Expected output

For each subsystem, record:

```text
subsystem name
routine PC/SNES address
input party byte read source
computed index/pointer
data source address
whether it reads save record 7, record 8, WRAM OOB, hardcoded ROM, or compact table
first safe hook point
```

## Patch implication

Do not author another guessed patch until this atlas is complete. The first production patch should be a small adapter at a known character-data resolution point, not another graphics or sanitizer hook.

Proposed adapter shape:

```text
GetPlayableRecordPtr(logical_id):
    if logical_id <= $06:
        return vanilla PC record/buffer
    if logical_id == $07:
        return ProjectEpoch backing record/buffer
```

The graphics-source adapter remains separate:

```text
GetGraphicsSource(logical_id):
    if logical_id <= $06:
        return vanilla source
    if logical_id == $07:
        Phase 1: return Magus graphics source $06
        Phase 2: return expanded-ROM Gaspar/Schala source
```

## PE-000 decision

PE-001 should be renamed or preceded by:

```text
PE-000 Character Data Atlas
```

PE-001 Menu Data Source Trace then becomes one subsection of PE-000 rather than the next standalone patch attempt.
