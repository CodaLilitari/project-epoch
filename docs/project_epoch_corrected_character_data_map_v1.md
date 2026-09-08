# Project Epoch corrected character data map v1

Status: canonical current publication ledger for the Project Epoch character and
logical-PC-`$07` surface

Date consolidated: 2026-08-24

Canonical machine-readable source:
[`references/project_epoch_corrected_character_data_map_v1.json`](../references/project_epoch_corrected_character_data_map_v1.json)

## Scope and nonclaim

This document consolidates the corrections already established by Project
Epoch's canonical-ROM audits, pinned static reconstruction, accepted runtime
traces, and bounded audit of the surviving Chrono Compendium eighth-character
and Project Schala threads. This revision incorporates one separately
documented private supported-slot emulator replay into the palette entry. It
adds no new PC `$07` ownership conclusion, forum claim, allocation, or hook.

It is the current corrected map for the character, party, save, runtime-record,
progression, naming, graphics, menu, battle, Tech, item, equipment, recruitment,
and expansion boundaries relevant to a genuine logical PC `$07`. It is **not**
a claim to map every byte, event, routine, RAM address, or subsystem in Chrono
Trigger.

The older
[`references/project_epoch_character_data_atlas_v0.md`](../references/project_epoch_character_data_atlas_v0.md)
is retained for provenance only. Its eighth-record interpretation and poison-
save plan are superseded and must not be used.

## Evidence and ownership rules

- `verified-static`: independently established from the pinned canonical ROM,
  a hash-gated deterministic audit, or the pinned byte-matched disassembly.
- `verified-runtime`: reproduced in the tracked emulator harness with accepted
  inputs and artifact hashes.
- `documented`: an exact technical or participant source, not independently
  promoted to runtime fact.
- `hypothesis`: a bounded question or design awaiting proof.

The machine-readable JSON uses half-open ranges: the start is included and
`end_exclusive` is not. In this document, compact address and record-byte
ranges include both endpoints unless the table explicitly says "end
exclusive". For example, `$0200-$042F` covers `$230` bytes, while the same
JSON span ends at `$0430`. Zeroes, `$FF`, an eighth physical value, or a routine
accepting byte `$07` do not establish free storage. `proposal-unbound` means the proposed architecture
has no approved production allocation or hook.

## High-impact corrections to community maps

1. Slot-relative `$0430` is not an eighth PC or Epoch/vehicle record. Seven
   `$50` PC records end at `$042F`; `$0430-$047F` is the saved seven-PC Tech and
   compatibility block.
2. `$0480` is not free backing storage. It lies inside vanilla's first `$05B0`
   serialized bytes, and the checksum covers the complete `$0A00` slot.
3. Runtime `$7E2830-$7E287F` is record-shaped only because the engine computes
   `$7E2600 + id*$50`; in unmodified vanilla it is live Tech/compatibility
   state. It becomes a natural PC `$07` record only after complete relocation.
4. `$CC:0230-$CC:027F` is the compatibility template after exactly seven
   initialization records, not an incomplete eighth record.
5. `$CC:25C2` begins the seven-row MP-growth table, not an eighth HP row. The
   eighth stat-growth row at `$CC:262B-$CC:2631` is real but all zero and does
   not define the missing HP, MP, TP, initialization, Tech, or persistence
   data.
6. Base/live record stats use Power, Stamina, Speed, Magic, Hit, Evade, Magic
   Defense. Growth/progression rows use Power, Stamina, Speed, Hit, Evade,
   Magic, Magic Defense. They are different and must remain separate.
7. `$CD:400E` is not an independent eighth-character attack byte. It begins
   the seven-entry critical-selector family and is Crono's runtime-confirmed
   critical selector; raw PC `$07` merely falls into it from the preceding
   family.
8. `$C2:A2CD` is code, not an eighth element row. `$E4:F023` is occupied NPC
   descriptor data, not a free PC descriptor. The historical Melchior fix
   repurposed or relocated an **NPC graphics-source slot**; Melchior was never
   a PC.
9. The word after Magus in `$E4:2600` is the required Magus-end/NPC-start
   animation sentinel, not an eighth animation start.
10. Seven `$40` menu walking-sprite records end at `$7E19C0`; that successor is
    active caster/party-exchange scratch associated historically with the
    Gaspar display, not an eighth persistent character record.
11. `$C1:F9EB-$C1:FA60` is reserve-XP processing, not window-layout data. It
    awards 75 percent XP to joined inactive IDs `$00-$06` and stops before
    `$07`; the associated active-membership map is also exactly seven bytes.
12. Project Schala used Magus's supported logical PC `$06` paths. It is useful
    replacement-path evidence, not proof that Schala and Magus coexisted as
    complete PCs.

## Corrected namespace and subsystem ledger

The stable IDs below exactly match the canonical JSON. Detailed sources,
evidence statements, historical assessments, and limitations live in that
file.

| Stable ID | Corrected ownership or boundary | PC `$07` consequence and rule | Status |
| --- | --- | --- | --- |
| `identity.logical-pc-and-editor-namespaces` | Logical PC, save/editor record, graphics source, naming entry, and empty `$80` are independent namespaces. | Resolve `$07` per consumer; never apply a global `$07->$06` or `$07->Epoch` rewrite. | `verified-boundary` |
| `party.active-and-joined-state` | Active IDs are slot `+$0580-$0582` / WRAM `$7E2980-$2982`; joined bit `$01` corresponds to ID `$07`; the field registry has only seven bytes at `$018D-$0193`, followed by active-ID cache `$0194-$0196`. | Transport and a flag do not establish downstream validity; add an explicit field-refresh path and publish only after sidecar and duplicate-free roster validation. | `adapter-required` |
| `save.pc-records-and-compatibility-block` | PC records are `+$0200-$042F`; `+$0430-$047F` is Tech/compatibility state, with counters at `+$0430-$0436` and learned masks at `+$0437-$043D`. | Preserve the complete block; never deserialize it as Schala. | `verified-boundary` |
| `save.serializer-and-0480` | Three `$A00` slots occupy `$30:6000-$30:7DFF`; the first serialized region is `+$0000-$05AF`; eight save descriptors occupy `$FF:FA7B-$FF:FAA2`; global metadata is `$30:7FE0-$30:7FFF`. | `+$0480` is occupied serialized state, not a candidate record; descriptor and global-metadata successors cannot be extended in place. | `rejected-allocation` |
| `save.global-sidecar-candidate` | Global SRAM `$30:7E00-$30:7FDF` is a bounded `$1E0` candidate for three `$A0` records, not approved ownership. | Complete save/load/erase/NG+/power-cycle/timing/atomicity proof before use. | `proposal-unbound` |
| `runtime.natural-record-and-compatibility-relocation` | Seven live records occupy `$7E2600-$282F`; `$7E2830-$287F` is compatibility state; `$7E2CA0-$2CEF` is an unapproved relocation candidate. | Natural PC `$07` is valid only after the complete owner and every lifecycle consumer move. | `proposal-unbound` |
| `initialization.seven-record-seed-and-attract-hazard` | `$CC:0000-$022F` is seven records; the `$280` seed includes a `$50` compatibility tail. Attract loops eight destinations from seven-row HP/MP sources. | Add explicit Schala initialization; never extend one bound into adjacent owners. | `adapter-required` |
| `stats.record-versus-growth-order` | Record order and growth order differ, especially Magic/Hit/Evade. | Use separately named schemas; one shared ordering corrupts stats. | `verified-boundary` |
| `growth.hp-mp-stat-tp-families` | HP and MP have seven `$08`-byte rows, stat growth has a real eighth `$07`-byte row that is all zero, and TP has seven `$10`-byte rows. | Raw ID `$07` aliases adjacent tables for HP, MP, and TP; the stat row is in bounds but supplies no usable growth. Relocate/adapt every family and author Schala's rows. | `adapter-required` |
| `battle.record-commit` | `$C1:B442` commits slot work records through `$7E2600 + id*$50`. | A visually successful battle can still overwrite Tech state; adapt commit or finish relocation first. | `adapter-required` |
| `battle.id-to-slot-and-reserve-xp` | `$7E:B1BE-$B1C4` is a seven-byte active map; `$C1:F9EB-$FA60` handles 75-percent reserve XP for IDs `$00-$06`. | Supply explicit active-membership and reserve-XP adapters; do not widen into `$7E:B1C5`. | `adapter-required` |
| `tech.progress-learned-and-combo-state` | `$2830-$2836` counts, `$2837-$283D` learned masks, `$283E-$284C` dual groups, `$284D-$2856` ordinary triple groups, and `$2857-$285B` equipped-rock flags are mapped owners. | Appending an eighth counter, mask, or group overwrites the next live family. | `adapter-required` |
| `events.location-11c-tech-grants` | Spekkio event `$11C` contains twelve absolute accesses to selected `$2830/$2837` Tech-state bytes. | Relocation requires a pinned event translation plus installed lifecycle guards. | `proposal-unbound` |
| `names.pc-fields-dialogue-and-epoch` | `$7E2C23` has eight six-byte fields; field 7 at `$2C4D` is independently Epoch-facing, and dialogue PC-name entry 7 is null. | Give Schala independent live/dialogue/menu/save/load naming; preserve Epoch. | `adapter-required` |
| `graphics.pc-pointer-families` | Graphics `$E4:2000`, assembly `$2300`, auxiliary `$2800`, palette `$2A00`, animation, and descriptor `$F000` families expose seven PC entries followed by occupied owners or sentinels. | Resolve PC `$07` independently in field, battle, menu, overworld, palette, and animation contexts. | `adapter-required` |
| `graphics.melchior-npc-descriptor-collision` | `$E4:F023-$F027` is the first occupied NPC descriptor; historical testimony associates the redirected occupant with Melchior. | Keep the NPC descriptor and users unchanged; Melchior's NPC slot is not eighth-PC capacity. | `negative-control` |
| `graphics.animation-boundary-and-entrypoints` | Eight words at `$E4:2600` delimit seven PC spans; entrypoint stride four does not mean fixed four-byte records. | Relocate and resolve a complete compatible animation package without overwriting the sentinel. | `adapter-required` |
| `graphics.palette-and-overworld-paths` | Five field reload paths contain ten exact `$18`-byte primary/mirror copies; fixed-bank readers and independent overworld formulas have their own bounds. At six inspected motion checkpoints, a repeated clean-controlled replay verifies the canonical Schala NPC provider only through Lucca's twelve-color field path. | A supported field render does not validate logical PC `$07`, battle, menu, portrait, save-preview, or overworld presentation. | `adapter-required` |
| `menu.walking-sprites-and-gaspar-scratch` | Seven `$40` records occupy `$7E1800-$19BF`; `$19C0` is active scratch, historically the Gaspar-area collision. | Virtualize a deliberate display record; do not expand the persistent record loop in place. | `adapter-required` |
| `menu.full-portraits-and-save-preview` | `$FF0000-$FF1F7F` is seven `$480` full faces; seven palette pointers follow elsewhere; Epoch naming and `$200` save preview are distinct routes. | Resolve an original full portrait and separate preview without aliasing Epoch. | `proposal-unbound` |
| `menu.element-icon-table` | `$C2:A2C6-$A2CC` is seven selector bytes; `$C2:A2CD` begins code. | Return Schala's icon at the consumer; never append at `$A2CD`. | `adapter-required` |
| `tech.owner-ranges-and-combo-groups` | `$CC:276A-$2777` has seven owner entries followed by requirements; dual/triple builders assume fixed groups. | Relocate owner/group metadata and bind Schala's groups explicitly. | `adapter-required` |
| `actions.player-command-namespace` | Player actions `$01-$74`, basic attacks `$75-$7B`, reserved `$7C-$7F`, proposed Schala `$80-$90`, and marker `$F0-$FF` are distinct policy ranges. | High-byte transport alone does not provide table rows or signed-check safety. | `proposal-unbound` |
| `tech.animation-package-selector-namespace` | `$C1:4612-$4681` resolves canonical package selectors `$00-$7F`; candidate `$80-$8F` is separate from same-numbered action commands, while command `$1E` and auxiliary readers retain fixed-bank behavior. | Numeric equality creates no action-to-package binding; preserve the canonical path and bind each high package deliberately. | `proposal-unbound` |
| `tech.names-targets-properties-mp-costs` | Names, targets, 124 command records, 72 property records rooted at `$CC:213F`, and MP-cost ID-0 alignment plus IDs `$01-$47` each have independent bounds. | A visible Tech list does not prove battle execution, learning, persistence, or ownership; preserve each exact existing owner. | `adapter-required` |
| `attack.basic-action-selector` | `$CC:2583-$2589` contains seven attacks; `$CC:258A` begins HP growth. | Resolve Schala at `$C1:BFFF`; do not append into HP data. | `adapter-required` |
| `attack.approach-policy` | `$CC:F63C-$F643` contains eight occupied values; entry 7 is `$FF`. | Preserve the existing value and add a deliberate PC `$07` policy resolver. | `adapter-required` |
| `attack.animation-selector-families` | `$CD:4000/$4007/$400E` begin three adjacent seven-entry families; `$CD:400E[0]` belongs to Crono's critical path. | Never patch file `$0D400E` as Schala's independent byte. | `negative-control` |
| `equipment.permission-bit-and-menu-bound` | Permission bit `$01` exists for ID `$07`, while common `$FE` masks and menu loops exclude it. | A bit is not full equipment support; adapt masks, menus, formulas, animations, and persistence. | `adapter-required` |
| `items.candidate-e8-ee-scope` | IDs `$E8-$EE` are unclaimed only by the completed canonical location-event census; they are not globally free. | Finish all classifiers and bind expanded descriptors before installing records. | `proposal-unbound` |
| `recruitment.operation-one-and-roster-capacity` | The nine-position roster can fit eight PCs, but party operation 1 replaces active slot 3 when full. | Test for an open active slot; register Schala in reserve on the full branch. | `adapter-required` |
| `project-schala.magus-replacement-scope` | Historical Schala used Magus's supported PC `$06` content paths. | Retain as a supported-slot consumer checklist, never as natural-PC-`$07` or coexistence evidence. | `negative-control` |
| `expansion.exhirom-map-mode-boundary` | File `$40FFD5` is the mirrored ExHiROM map-mode byte; `$35` is structural metadata. | Preserve both headers and named allocations; never treat the header as code/data space. | `verified-boundary` |

## Complete `$50` playable-record byte schema

This schema applies to a genuine record. It must not be projected onto vanilla
`$7E2830` or save `+$0430` before the compatibility relocation.

| Offset | Size | Primary meaning | Evidence qualification |
| --- | ---: | --- | --- |
| `+$00` | 1 | Logical/portrait identity | `verified-static` |
| `+$01` | 1 | Innate-element selector plus unmapped low flags | high nibble mapped; low nibble unresolved |
| `+$02` | 1 | PC progress flags | bits 0 and 4 mapped |
| `+$03-$04` | 2 | Current HP | little-endian u16 |
| `+$05-$06` | 2 | Base max HP | little-endian u16 |
| `+$07-$08` | 2 | Current MP | little-endian u16 |
| `+$09-$0A` | 2 | Base max MP | little-endian u16 |
| `+$0B` | 1 | Base Power | persistent |
| `+$0C` | 1 | Base Stamina | persistent |
| `+$0D` | 1 | Base Speed | persistent; not growth-recomputed |
| `+$0E` | 1 | Base Magic | persistent |
| `+$0F` | 1 | Base Hit | persistent |
| `+$10` | 1 | Base Evade | persistent |
| `+$11` | 1 | Base Magic Defense | persistent |
| `+$12` | 1 | Level | capped at 99 |
| `+$13-$15` | 3 | Cumulative EXP | little-endian u24 |
| `+$16-$18` | 3 | Cumulative TP | little-endian u24 |
| `+$19` | 1 | Combatant category mask | partially mapped |
| `+$1A` | 1 | Secondary combatant effect/category flags | partially mapped |
| `+$1B` | 1 | Enemy-side attack variant/context | partially mapped; PC templates seed zero |
| `+$1C` | 1 | Unmapped | do not infer free space |
| `+$1D-$21` | 5 | Current status groups 0-4 | partially mapped |
| `+$22-$26` | 5 | Permanent/equipment status and immunity groups 0-4 | partially mapped |
| `+$27` | 1 | Helmet item ID | equipment source |
| `+$28` | 1 | Armor item ID | equipment source |
| `+$29` | 1 | Weapon item ID | equipment source |
| `+$2A` | 1 | Accessory item ID | equipment source |
| `+$2B-$2C` | 2 | Remaining EXP to next level | little-endian u16 |
| `+$2D-$2E` | 2 | Remaining TP to next single Tech | little-endian u16 |
| `+$2F-$35` | 7 | Level-1 stat baselines | Power, Stamina, unused Speed, Hit, Evade, Magic, Magic Defense |
| `+$36-$3C` | 7 | Equipment-adjusted/live stats | Power, Stamina, Speed, Magic, Hit, Evade, Magic Defense |
| `+$3D` | 1 | Derived Attack | recomputed |
| `+$3E` | 1 | Derived Defense | recomputed |
| `+$3F-$42` | 4 | Context-derived tail | menu adjusted-max-HP view; battle element modifiers |
| `+$43-$47` | 5 | Battle weapon descriptor remainder | reloaded from equipment |
| `+$48-$4A` | 3 | Battle armor descriptor | reloaded from equipment |
| `+$4B-$4E` | 4 | Battle accessory descriptor | reloaded from equipment |
| `+$4F` | 1 | Unmapped tail byte | initial `$FF` is not free-space evidence |

The JSON validates these rows as one contiguous, non-overlapping `$50`-byte
schema.

## Exact seven-PC raw graphics windows

These are raw 4bpp playable graphics, not compressed NPC packets. The hashes
pin the current canonical boundaries without publishing game bytes.

| PC | SNES range, end exclusive | Bytes | Tiles | SHA-256 |
| --- | --- | ---: | ---: | --- |
| Crono | `$D2:72C0-$D3:0000` | `$8D40` | 1,130 | `76042f388cf45e7cf55574b9fa92fa97d32c7fe8ff4028c01d70019ed51cd56b` |
| Marle | `$D4:0000-$D4:7C40` | `$7C40` | 994 | `a9c78414e6cf797dba1aecef3657a9dd046aaacecd72c92ddccc210394928251` |
| Lucca | `$D3:6B40-$D4:0000` | `$94C0` | 1,190 | `057719bb3ecfdd79b7bca4f3e6e3f49ba5d1fb86f3ca83aa4a5f4832fbd77d92` |
| Robo | `$D4:7C40-$D5:0000` | `$83C0` | 1,054 | `83423301a98103b3370b4d665564c898291a933ca7a509168c2d54268124cb0b` |
| Frog | `$D3:0000-$D3:6B40` | `$6B40` | 858 | `afcdc471602d3add1f44ad87fd3290ecff9fd3f364ab60cbbb06be032818cfb1` |
| Ayla | `$D5:0000-$D5:8C00` | `$8C00` | 1,120 | `9df8eab8777f02acab1709c771bda63dba1a81abc8d1a2840ff464c5fe675c3e` |
| Magus | `$D2:0000-$D2:72C0` | `$72C0` | 918 | `fb506e919f31a5b6b1c50fa06a7d497629105283d39c5316063596237935914a` |

## Exact seven-PC assembly envelopes

Every record is `$28` bytes: sixteen little-endian tile-selection words plus
four X/Y coordinate pairs. Robo's end is the derived minimum referenced extent,
not an ownership claim over the rest of bank `$DC`.

| PC | SNES range, end exclusive | Records | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- |
| Crono | `$DC:27B0-$DC:4E70` | 248 | `$26C0` | `263492d1dd49e0c9a6747bf64734841e5db787e29ca613ef4e4399017690a03e` |
| Marle | `$DC:9AD8-$DC:C080` | 241 | `$25A8` | `2824a7be4da3ff40a51910a75d12af21dbac6ccedacb6326fcd44b0256bd5d3b` |
| Lucca | `$DC:4E70-$DC:7490` | 244 | `$2620` | `d7fde66a7c71a33fb23c3bd5531e8f89241751b08d120f2bcebad09a8b3634ce` |
| Robo | `$DC:C080-$DC:DF70` minimum | 198 | `$1EF0` | `8e8d67ab57dd9ed648ab06781c7066721c610c0a8957d0e72fccd39f153ef5ea` |
| Frog | `$DC:7490-$DC:9AD8` | 245 | `$2648` | `ae11b0b72e41cea97b4e216e8a3dc959aa4f699bf7c77dbee012595e3087d559` |
| Ayla | `$DE:0000-$DE:27D8` | 255 | `$27D8` | `5003d41b09d5f557a809388a7036cf1a9dabe897c20961c1b9f9f5c0cc572eea` |
| Magus | `$DC:0000-$DC:27B0` | 254 | `$27B0` | `05a78400c3268d0017244c43b80103bf10f9158340f96a610f6bc388717ceee6` |

## Exact seven-PC animation windows

Eight boundary words at `$E4:2600` delimit these seven blobs. Each blob divides
into four equal facing spans; the reported entrypoint count is based on the
four-byte entrypoint stride and is not a count of fixed-size animation records.

| PC | SNES range, end exclusive | Bytes | Bytes/facing | Entrypoints/facing | SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| Crono | `$E4:3000-$E4:34A0` | `$4A0` | `$128` | 74 | `43c629e4e3ab32a5bce56189cb4ef7821d920b6c12318aa45edd742eded95dff` |
| Marle | `$E4:34A0-$E4:3880` | `$3E0` | `$0F8` | 62 | `7fc62fe6ed719de9e3448c68d03f90f171ba4b31a420db58a0c9fe20bac751bf` |
| Lucca | `$E4:3880-$E4:3CF0` | `$470` | `$11C` | 71 | `850c331267d16be7b11611d4f69d2120fac8e0f314102794b47b09fa7c200607` |
| Robo | `$E4:3CF0-$E4:4160` | `$470` | `$11C` | 71 | `3fd15908dd98720e53c3601b3750ec587717997d1b7f1ab65be6ce69ccf57fe6` |
| Frog | `$E4:4160-$E4:45C0` | `$460` | `$118` | 70 | `48ec0306a22490165efb296fad3dc4f8353c49db10f01c28713bb80776fd3ceb` |
| Ayla | `$E4:45C0-$E4:4B00` | `$540` | `$150` | 84 | `ece49a6d2c7dc2af775489f49b917c55672991c766758c3444ba0b2545b87717` |
| Magus | `$E4:4B00-$E4:4ED0` | `$3D0` | `$0F4` | 61 | `2875f534a1baa2e7064a62f05d5efaaf9e130dea9de195e66f256571c2464896` |

## Maintenance and publication contract

1. The JSON is the canonical machine-readable ledger. Every stable entry ID,
   source, evidence level, range, and status must validate before publication.
2. This Markdown document must contain every canonical entry ID and the same
   complete `$50` record coverage.
3. A correction may be promoted only from cited current evidence. Forum posts
   remain historical claims until independently verified.
4. `verified-static` and `verified-runtime` may coexist within one entry only
   as separate statements; a runtime observation never generalizes beyond its
   recorded path.
5. `unclaimed-in-stated-scope`, bounded candidates, and zero-filled regions
   must never be rendered as globally free or production-ready.
6. New findings update the JSON, this rendering, the developer guide change
   log, and the relevant deterministic audit together.
7. No ROM, save, state, trace payload, extracted game data, private path,
   credential, or private correspondence belongs in either map.

## Validation

```powershell
python -m unittest tests.test_project_epoch_corrected_data_map -v
python -m json.tool references/project_epoch_corrected_character_data_map_v1.json > $null
```

The validation is metadata-only and does not require or open a ROM.
