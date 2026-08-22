# Project Epoch Schala progression foundation v0

Status: original authoring data and deterministic overlay format complete;
runtime binding gated  
Last updated: 2026-07-25  
Logical playable identity: `$07`

## Result

Schala now has an independently authored level policy, base profile, HP/MP
growth, seven-stat growth row, single-tech TP cadence, and starting loadout.
None of the values were copied or modified from a vanilla character record or
growth row.

Canonical source:

`assets/source/schala/v0/content/schala_progression_v0.json`

Canonical normalized SHA-256:

`17e25577bfb80998e33c5ac0890147231a5e1d3674de8af97e6fdf242f51aab5`

The source is `authoring-only-unmapped`. It does not claim that the vanilla
record, growth readers, TP reader, equipment readers, or save system can
consume logical PC `$07`.

## Recruitment level policy

`proposal`

Schala enters at the median active-party level, clamped to levels 30-45. An
unavailable or empty party-level input falls back to level 35. This avoids a
fixed late-game level and prevents an overleveled save from recruiting a
level-99 Schala immediately.

The runtime initializer must derive the level from distinct party records,
bind the shared experience curve, and compute the live record only after the
natural PC `$07` record and compatibility-block relocation are active.

## Original stat direction

`proposal`

Level-one basis, shown in the engine's runtime-confirmed stat order:

| HP | MP | Power | Stamina | Speed | Hit | Evade | Magic | MDef |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 65 | 14 | 2 | 5 | 10 | 7 | 9 | 10 | 10 |

HP growth brackets:

| Through level | Gain per level |
| ---: | ---: |
| 10 | 10 |
| 30 | 14 |
| 60 | 15 |
| 99 | 16 |

MP growth brackets:

| Through level | Gain per level |
| ---: | ---: |
| 10 | 2 |
| 30 | 2 |
| 60 | 1 |
| 99 | 1 |

Stat growth, in hundredths per level and engine serialization order:

| Power | Stamina | Speed | Hit | Evade | Magic | MDef |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 65 | 0 | 30 | 45 | 105 | 150 |

The `$C1:F630` level-up path proves that the encoded order is Power,
Stamina, Speed, Hit, Evade, Magic, Magic Defense. An older disassembly data
label placed Magic before Hit; the Project Epoch source/compiler now pins the
runtime order explicitly. The authored meanings and projections did not
change—only their safe serialized positions did.

The host model projects:

| Level | HP | MP | Power | Stamina | Speed | Hit | Evade | Magic | MDef |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 435 | 72 | 9 | 23 | 10 | 15 | 22 | 40 | 53 |
| 35 | 510 | 77 | 10 | 27 | 10 | 17 | 24 | 45 | 61 |
| 37 | 540 | 79 | 11 | 28 | 10 | 17 | 25 | 47 | 64 |
| 45 | 660 | 87 | 13 | 33 | 10 | 20 | 28 | 56 | 76 |
| 50 | 735 | 92 | 14 | 36 | 10 | 21 | 31 | 61 | 83 |

This expresses the design target directly: low HP, Power, and Stamina; fixed
middle-speed movement; high Magic without overtaking Magus at the intended
recruitment band; and good but not self-sufficient Magic Defense before
equipment. These are balance targets, not runtime evidence. Equal-level,
equal-equipment emulator comparisons remain mandatory.

## Single-tech progression

`verified-static` for the source and host conversion; runtime reader gated

Schala begins with Astral Pin, Veil, and Crescent Wake. The engine-facing
learned count is three and its high-bit-first mask is `$E0`; `$07` would be the
wrong bit order for the vanilla single-tech mask.

The authored cumulative targets and their engine-step form are:

| Tech index | Cumulative TP after recruitment | Step cost |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 1 | 0 | 0 |
| 2 | 0 | 0 |
| 3 | 100 | 100 |
| 4 | 250 | 150 |
| 5 | 500 | 250 |
| 6 | 900 | 400 |
| 7 | 1400 | 500 |

The starting `TP to next` value is therefore 100. The production adapter must
move the TP threshold reader away from the seven-row vanilla table and keep
Schala's learned count/mask in the Project Epoch sidecar.

## Starting loadout

`proposal`

- helmet: none (`$FF` Project Epoch null sentinel);
- armor: Regent Mantle `$EC`;
- weapon: Glass Focus `$E8`;
- accessory: none (`$FF` Project Epoch null sentinel).

Both actual items are original Project Epoch records. This document does not
claim that `$FF` is a valid vanilla equipment value; the overlay initializer
must translate the null sentinel only after the equipment record behavior is
traced.

## Deterministic overlay

`verified-static`

`tools/schala_progression.py` validates the source and emits a compact
Project Epoch descriptor. It intentionally is not a vanilla `$50`-byte
character record.

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `$00` | 1 | descriptor version |
| `$01` | 1 | logical PC ID |
| `$02` | 1 | level-policy ID |
| `$03-$05` | 3 | minimum, maximum, fallback level |
| `$06-$07` | 2 | learned count and high-bit-first mask |
| `$08-$0B` | 4 | basic action, element, equip bit, flags |
| `$0C-$0F` | 4 | level-one HP and MP |
| `$10-$16` | 7 | level-one stats: Pwr, Sta, Spd, Hit, Eva, Mag, MDef |
| `$17` | 1 | reserved, zero |
| `$18-$1F` | 8 | HP growth brackets |
| `$20-$27` | 8 | MP growth brackets |
| `$28-$2E` | 7 | stat growth in the same engine order |
| `$2F` | 1 | reserved, zero |
| `$30-$3F` | 16 | eight little-endian TP step costs |
| `$40-$43` | 4 | helmet, armor, weapon, accessory overlay IDs |
| `$44-$45` | 2 | initial TP-to-next value |
| `$46-$47` | 2 | reserved, zero |

Descriptor size: `$48` bytes  
Descriptor SHA-256:
`b95a0a3d8397706f2c83472539ee208ebaef1af3e9e6057691b0b1c00dedaaff`

Reproduction:

```text
python tools/schala_progression.py \
  --output-dir private/build/schala_progression_v0
```

Nine focused tests cover provenance, source normalization, descriptor
round-trip, reserved bytes, the median/clamp policy, projections and caps,
high-bit tech masks, TP delta conversion, the original loadout, and explicit
runtime gates.

## Remaining gates

- Map live-record bytes `$01` and `$02` before emitting a full record.
- Bind the shared experience curve and `exp to next` values.
- Implement current-stat, attack, defense, and max-HP recomputation.
- Relocate or redirect all HP, MP, stat, and TP table readers for ID `$07`.
- Translate overlay null equipment safely.
- Initialize the record at recruitment and New Game+ reset.
- Save and reload the record, learned count/mask, and TP remainder.
- Run equal-level/equal-equipment damage and durability comparisons.

Until those gates pass, the descriptor is new data ready for an expanded-ROM
allocation, but it is not ROM-installable and does not make Schala playable.
