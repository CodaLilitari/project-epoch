# Project Epoch PC `$07` graphics and menu hook audit

Status: verified-static surface map; no production hooks installed  
Source: canonical US v1.0 ROM plus `ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`  
Last updated: 2026-07-25

## Executive result

There is no unused eighth entry in the playable graphics tables. Logical
character `$07` reaches NPC data, an animation end sentinel, the Epoch
portrait path, the overworld palette staging area, or active menu scratch
records depending on context. A genuine Schala implementation needs
context-specific resolvers; increasing a loop bound is unsafe.

The earlier Lucca-to-Magus diagnostic proves only selected supported-slot
paths. In particular, its coherent small save-preview portrait does not prove
the full 36-tile status portrait path.

## Core bank `$E4` tables

`verified-static`

| Table | Address/stride | IDs `$00-$06` | What logical `$07` reaches |
| --- | --- | --- | --- |
| graphics packet pointers | `$E4:2000`, 3 bytes | seven full 24-bit pointers | `$E4:2015`, first NPC/monster pointer |
| assembly packet pointers | `$E4:2300`, 3 bytes | seven full 24-bit pointers | `$DD:B608`, occupied NPC assembly |
| animation base boundaries | `$E4:2600`, 2 bytes | seven starts | `$4ED0`, Magus-end/NPC-start sentinel required to derive stride |
| auxiliary animation pointers | `$E4:2800`, 2 bytes | seven offsets | `$B600`, occupied |
| palette pointers | `$E4:2A00`, 2 bytes | seven offsets | first NPC palette record |
| sprite descriptors | `$E4:F000`, 5 bytes | seven `[gfx,assembly,palette,anim,size]` records | `$E4:F023`, occupied NPC descriptor |

The roots at `$E4:FFE0-$E4:FFEA` are 16-bit offsets into fixed bank `$E4`.
Entries 7/8 and descriptor `$E4:F023` must remain untouched.

## Context map and minimum hooks

| Context | Vanilla behavior/collision | Candidate hook boundary | Required Project Epoch behavior |
| --- | --- | --- | --- |
| Field descriptor | `$C0:448D` multiplies ID by 5 and reads `$E4:F000`; ID7 reads NPC0 | before the multiply at `$C0:448D` | dispatch ID7 to a relocated Schala descriptor |
| Field non-flipped tiles | `$C0:E687` recognizes only banks `$7F/$D2/$D3/$D4`, otherwise assumes `$D5` | `$C0:E687` | make the source-bank path generic so expanded-ROM graphics decode correctly |
| Battle graphics setup | `$CC:E980` reads active ID, then `$E4:2000/$2300/$2600/$2800`; animation bank is forced to `$E4` | before arithmetic at `$CC:E980` | fill `$7E1C57/$1C78/$1C99/$1CBA` and stride fields from Schala pointers, then rejoin |
| Battle animation readers | readers at `$C1:2EBA/$2EEB/$3639/$3650/$42D0/$4300` hardcode bank `$E4` | each fixed-bank reader or one common relocated reader | accept the resolved animation bank |
| Overworld tiles | `$C2:2BBC` uses `$7F9000 + id*$400`; ID7 lands at `$7FAC00`, the palette region | `$C2:2BBC` | stage and resolve Schala's dedicated overworld tile page |
| Overworld palettes | `$C2:2BCF` uses `$7FAC00 + id*$40`; `$C2:28ED` uses `$7F8E00 + id*$20` | `$C2:2BCF`, `$C2:28ED` | resolve dedicated Schala palette rows |
| Menu walking sprite | `$C2:F422` selects `$E4:F000`; ID7 reads NPC0 | `$C2:F436/$C2:F44F` | resolve the Schala descriptor |
| Menu sprite record | `$7E1800 + id*$40`; ID7 is `$7E19C0`, already an active caster/exchange scratch slot | menu ID-to-slot helper `$C2:F626` plus all `$19C0` consumers | virtualize logical ID to a deliberate display slot; do not promote `$19C0` by changing bounds |
| Full status portrait | `$FF0000-$FF1F7F` is loaded as seven 36-tile faces; ID7 tile base aliases Crono | tile selector `$C2:EC3E`, palette selector `$C2:EC77`, and portrait DMA plan | dynamically load Schala's relocated 36-tile face into a shared VRAM slot |
| Name-entry portrait | pseudo-ID7 deliberately selects the Epoch portrait at `$FF:EB88` | context split at `$C2:E44D` | preserve Epoch naming; only playable-ID context may select Schala |
| Element icon | seven-byte map at `$C2:A2C6`; ID7 reads following code | `$C2:A279/$C2:A27C` | return Schala's deliberate element/type icon |
| Save preview | `$C2:D19F`, active ID read at `$C2:D1C1`, then ID×`$50` from slot offset `$0200`; ID7 reads `$0430` tech state | immediately after `$C2:D1C1` | synthesize preview stats/name/portrait from the validated sidecar |
| Normal menu record | `$C2:8839` computes `$7E2600 + id*$50` | `$C2:8839` unless natural `$2830` record architecture is adopted | resolve the real Schala record |
| Battle record load | `$FD:AE52` computes the record source | `$FD:AE52` unless natural `$2830` record architecture is adopted | resolve the real Schala record |

## Seven-only buffers and loops

`verified-static`

- Field PC registry uses `$018D-$0193` for IDs 0-6. `$0194-$0196` already
  hold active-party IDs; event add/remove cannot extend the registry in place.
- Menu walking-sprite records use seven `$40`-byte records at
  `$7E1800-$19BF`. `$19C0` and `$1A00` are scratch records.
- Menu VRAM words exist for seven PCs and a separate scratch slot. A logical
  eighth record needs virtualization or a redesigned allocation.
- Battle/menu name bootstrap loops copy seven names.
- The nine-entry roster container itself can carry arbitrary nonnegative ID7,
  and party exchange has room for three active plus five reserve characters.
  Downstream fixed tables and buffers are the blockers.

## Portrait distinction

Two independently relevant paths must not be conflated:

1. The Lucca-to-Magus diagnostic copies a documented `$200`-byte region and
   produced a coherent small save-preview icon in Lucca's supported row
   (`verified-runtime`).
2. The main status/party portrait upload covers `$1F80` bytes and uses
   36-tile (`$480`-byte) per-character bases plus a seven-entry palette table
   (`verified-static`).

Production Schala needs an original full 36-tile face and an explicit small
save-preview strategy. Passing one path does not validate the other.

## Asset placement consequences

- Graphics and assembly pointers are full 24-bit values, but the field
  non-flip decoder must stop assuming bank `$D5`.
- Several palette and animation paths force bank `$E4`; relocated assets
  require reader patches. There is no approved free block in `$E4`.
- Overworld art is separately staged and cannot reuse the normal field sheet
  implicitly.
- Schala's playable frames must follow the standard walk/idle organization if
  the common selectors are retained.
- Originality, tile count, palette, and frame requirements remain in
  `docs/schala_sprite_asset_spec_v0.md`.

## Activation gate

Do not place logical `$07` in an active party until the field, battle,
overworld, menu-sprite, portrait, icon, preview, and record paths above have
either a resolver or a proved safe shared adapter. All vanilla `$00-$06`
outputs must remain byte-for-byte equivalent at the adapter boundary.
