# Project Epoch Schala item namespace architecture

Status: authoring pack complete; `$E8-$EE` verified-static as unclaimed by canonical location events  
Last updated: 2026-07-25  
Logical character: Schala PC `$07`

## Outcome

Project Epoch reserves the following proposed byte IDs for original Schala
content:

| ID | Design name | UI label | Logical class |
| ---: | --- | --- | --- |
| `$E8` | Glass Focus | `GlassFocus` | weapon |
| `$E9` | Tide Lens | `Tide Lens` | weapon |
| `$EA` | Night Prism | `NightPrism` | weapon |
| `$EB` | Star of Zeal | `Star Zeal` | weapon |
| `$EC` | Regent Mantle | `RegentMtl` | armor |
| `$ED` | Crescent Clasp | `Cres.Clasp` | accessory |
| `$EE` | Pendant Shard | `Pend.Shard` | key item |

IDs `$EF-$F1` remain reserved. Never allocate `$F2+`: the vanilla sanitizer
rejects that range, and `$F0-$FF` also belongs to the battle marker family in
the command namespace.

The machine-readable source is
`assets/source/schala/v0/content/schala_item_content_v0.json`. Its normalized
canonical SHA-256 is
`dfa3f66d079a8921ff088b99f2ba507cf205525ab47fb11da609704e90c2fd85`.
`tools/validate_schala_items.py` pins the IDs, names, classes, equip masks,
original stats, provenance, and unmapped status.

## Evidence and caveat

`verified-static`

For `$E8-$EE` in the canonical ROM:

- the existing item-name slots are blank;
- primary consumable records are inert `0C 00 00`;
- secondary records are `FF FF FF FF`;
- none appears in the 24 shop inventories;
- none appears in the 256 enemy charm/drop records;
- none appears in the 249 reachable treasure records;
- none appears in the 28 starting-equipment fields;
- no pinned enum constant claims one;
- the sanitizer threshold at `$C2:99A3` accepts every ID below `$F2`.

The complete canonical location-event pointer table has now been audited:
all 513 entries, 489 valid referenced event IDs, 462 unique valid compressed
packets, and 145,615 unique-packet commands. Across 510 item-bearing
operations there are zero fixed `$E8-$EE` operands and zero unresolved
computed references. All 25 indirect `$C7` operations resolve to generic
vanilla equipment-field passthrough.

This upgrades the range to **`verified-static: unclaimed by canonical location
events`**. It does not make the IDs globally free or authorize native record
installation. The authoring pack deliberately keeps every native binding
null, and no ROM table or hook currently consumes these records. Full method,
coverage, reproduction, and limits are in
`docs/location_event_item_reference_audit.md`.

## Why a virtual overlay is required

The blank vanilla high-band bytes do not supply valid weapon, armor,
accessory, or key-item semantics. Project Epoch must classify `$E8-$EE` before
the vanilla `>= $BC` consumable decisions and resolve them through an
expanded-ROM descriptor.

The allocation-neutral version-1 descriptor is now frozen at `$20` bytes:

| Offset | Size | Field |
|---:|---:|---|
| `$00` | 1 | item ID |
| `$01` | 1 | logical class: weapon 0, armor 1, accessory 2, key 3 |
| `$02` | 1 | sort class; equal to logical class in v1 |
| `$03` | 1 | sellable, usable, equippable, key, and Focus flags |
| `$04` | 2 | price |
| `$06` | 1 | equip mask |
| `$07` | 1 | power or defense |
| `$08` | 1 | direct Magic Defense |
| `$09` | 1 | direct-stat mask |
| `$0A` | 1 | Magic modifier |
| `$0B` | 1 | Magic Defense modifier |
| `$0C` | 1 | elemental resistance mask; zero for every v1 Schala item |
| `$0D` | 1 | Focus visual ID 0-3 or `$FF` |
| `$0E` | 5 | secondary bytes; required zero in v1 |
| `$13` | 1 | reserved; required zero |
| `$14` | 3 | expanded description pointer |
| `$17` | 1 | reserved; required zero |
| `$18` | 3 | expanded weapon-visual pointer |
| `$1B` | 5 | reserved; required zero |

`tools/schala_item_descriptor.py` converts the seven original authoring
records into an unbound `$E0`-byte table. Its SHA-256 is:

`b3b5b267ee60e69d8506897092289134d176592264207f1918c7a5459873fc1a`

Eight focused tests pin field offsets, class/flag semantics, the four distinct
Focus IDs, direct Magic +1/+2/+3/+5, independent Magic/MDef +4 for Crescent
Clasp, inert Pendant Shard behavior, strict reserved bytes, and 24-bit pointer
bounds. Description and visual pointers remain zero, `rom_installable` is
false, and no expanded address has been allocated.

The direct-stat fields avoid the inexact vanilla boost-index vocabulary.
The four Focus visual source records now have a separate, unbound-only
`$18`-byte v1 schema in
`docs/schala_focus_pulse_adapter_architecture.md`. This does not bind the item
descriptor's `weapon_visual_ptr`: palettes, sounds, graphics, a separately
versioned bound form, and named expanded allocations are still missing. No
vanilla weapon table may be extended in place.

## Original authoring values

These are balance proposals, not native records:

| Item | Primary value | Original modifier |
| --- | ---: | --- |
| Glass Focus | attack 20 | Magic +1 |
| Tide Lens | attack 40 | Magic +2 |
| Night Prism | attack 60 | Magic +3 |
| Star of Zeal | attack 85 | Magic +5 |
| Regent Mantle | defense 76, MDef 20 | no copied status record |
| Crescent Clasp | n/a | Magic +4, MDef +4 |
| Pendant Shard | n/a | unsellable, unusable, never equipped |

All six pieces of equipment use mask `$01`, the genuine bit for logical PC
`$07`. Pendant Shard uses mask `$00`. Selected general equipment must be
changed deliberately to `$FF` if Schala may equip it, because vanilla `$FE`
explicitly excludes bit zero.

## Known vanilla records

`verified-static`

| Data | Canonical range |
| --- | --- |
| Weapon secondary | `$CC:0262-$CC:0423`, 90 x 5 |
| Armor secondary | `$CC:047E-$CC:04E0`, 33 x 3 |
| Accessory secondary | `$CC:052C-$CC:05CB`, 40 x 4 |
| Consumable/key secondary | `$CC:05CC-$CC:06A3`, 54 x 4 |
| Gear primary | `$CC:06A4-$CC:0A1B`, 148 x 6 |
| Accessory primary | `$CC:0A1C-$CC:0ABB`, 40 x 4 |
| Consumable primary | `$CC:0ABC-$CC:0B5D`, 54 x 3 |
| Names | `$CC:0B5E-$CC:15C3`, 242 x 11 |
| Targeting | `$CC:1BB5-$CC:1BEA` |
| Boosts | `$CC:29D7-$CC:2A04` |
| Equip/effect records | `$CC:2A05-$CC:2AAF` |
| Description pointers | `$CC:2EB1-$CC:3094` |
| Class metadata | `$FF:CF0E-$FF:CF2B` |

The existing 242-entry name table can carry `$E8-$EE`. High-band description
strings cannot be appended after the vanilla pointer table because strings
begin immediately at `$CC:3095`; the resolver must accept expansion-bank
pointers.

## Mandatory adapters

Central and menu:

- `Item_ClassifyId` at `$C2:8881`;
- cache construction at `$C2:9875`;
- equip-list numeric filter at `$C2:8953`;
- item-menu `>= $BC` branch at `$C2:AB2B`;
- shop detail and post-buy classification at `$C2:DD7C/$C2:DFAA`;
- description resolver at `$C2:F2F3`;
- equipped scan at `$C2:8900`, whose loop still stops at seven PCs at
  `$C2:8948`;
- preview/stat paths at `$C2:916E/$C2:926E/$C2:92CE`.

Battle:

- item-menu builders at `$FD:AF80` and `$FD:B655`;
- primary equipment application at `$C1:CE3A`;
- secondary resolver at `$FD:B033`;
- secondary copy at `$C1:CF15/$C1:CF2F/$C1:CF35`;
- basic-attack equip-mask reads at `$FD:AEF2/$FD:AF36`;
- direct weapon derivation at `$C1:FC9B`;
- accessory boost path `$C1:FC7F` through `$FD:B14D`.

Focus presentation:

- 15-byte weapon visual lookup at `$C1:434C-$C1:43ED`;
- animation roots `$D1:0000`, `$CD:686E`, `$CD:64B0`, `$CD:5EC6`;
- palette map `$CD:6CEC-$CD:6D4B`, read at `$CC:E71C/$C2:F610`;
- swing SFX `$CD:6D4C-$CD:6DAB`, read at `$C1:61EF`;
- hit SFX `$CD:6DAC-$CD:6E0B`, read at `$C1:61F9`;
- 64 six-byte palette rows at `$D1:4B00-$D1:4C7F`, copied through
  hard-coded bank-`$D1` paths in battle and both menu contexts.

The 15-byte lookup is now bounded exactly in
`docs/schala_focus_pulse_adapter_architecture.md`: its 95 canonical records
end at `$CD:45A6`, while direct `$E8-$EB` lookups land inside the active enemy
Attack-animation table. The same audit proves that Schala's three Attack
selectors cannot be appended safely and that four downstream fixed-table
consumers must be adapted with the Focus visual resolver. The auxiliary
palette/SFX audit additionally proves that direct `$E8-$EB` lookups collide
with the hit-SFX table and three reachable enemy Attack-animation packages.
Those package offsets belong to the enemy-action path, not the separate PC
normal-Attack resolver. Focus palette, swing sound, and hit sound therefore
require separate fields behind the still-unbound composite binding pointer;
no table may be extended in place.

## Structurally compatible paths

The following paths already carry byte-wide IDs and do not need a wider
inventory format:

- IDs at `$7E2400-$24FF` and quantities at `$7E2500-$25FF`;
- field add/remove/check APIs `$C1:CFE9/$C1:D005/$C1:D056`;
- battle reward merge and inventory backup/restore;
- event opcodes `C9/CA/CB`;
- treasure payloads;
- menu, battle, and field name indexing.

Compatibility here proves transport only. Classification, equipment
semantics, stats, descriptions, visuals, and event ownership still require
the adapters above.

## Approval gates

- [x] Candidate range survives structured owner scans listed above.
- [x] Every canonical location-event pointer/script path is audited for fixed
      and computed item references; `$E8-$EE` have no claims.
- [x] Original item source and provenance are machine-readable.
- [x] IDs, labels, class counts, masks, and null bindings are tested.
- [x] Freeze and test the allocation-neutral expanded descriptor binary
      layout; all native pointers remain unbound.
- [x] Author the Glass Focus `$E8`/visual-0 source slice with six Attack
      poses, six Focus inserts, and distinct unbound swing/hit audio recipes.
- [ ] Implement central, menu, shop, and battle classification adapters.
- [ ] Implement direct stat masks/amounts without aliasing vanilla boosts.
- [ ] Add original visual/audio source slices for Tide Lens, Night Prism, and
      Star of Zeal.
- [ ] Prove inventory sort, buy/sell, equip/unequip, stat preview, battle load,
      reward merge, save/load, and New Game+ behavior.
- [ ] Verify Pendant Shard is unsellable, unusable, non-equippable, and does
      not replace the vanilla Pendant.

Until the adapter matrix passes, these are original source records with
statically unclaimed candidate identities, not active ROM items.
