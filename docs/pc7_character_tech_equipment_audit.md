# Project Epoch PC `$07` character, tech, and equipment audit

Status: verified-static surface map; high-ID command overlay selected as proposal  
Source: canonical US v1.0 ROM plus `ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`  
Last updated: 2026-07-25

## Executive result

Three architectural facts control the implementation:

1. A natural eighth live record at `$7E2830` collides with all persistent
   tech-learning/group state. Either that state or the record must move.
2. Equipment already gives logical ID `$07` a unique permission bit `$01`.
3. The low action-command namespace has only four unused IDs, while the
   proposed launch set needs 17 new actions. Raw `$80-$90` identities survive
   the byte-wide battle transport and are the selected overlay, but signed UI
   checks and direct tables must be patched explicitly.

## Character record and initialization

`verified-static`

| Surface | Vanilla shape | ID `$07` consequence | Required change |
| --- | --- | --- | --- |
| initial records | `CharInitData` `$CC:0000`, seven × `$50`, ends `$CC:0230` | next bytes are starting tech state | relocate/expand or initialize Schala separately |
| new-game seed | `$C2:956E` copies `$280` bytes `$CC:0000->$7E2600` | copies seven records plus tech arrays as one block | split record and tech initialization |
| init copy helper | `$FD:B33F` stops at `$0230` | excludes an eighth record | extend only after destination architecture is safe |
| live records | `$7E2600 + id*$50` | ID7 aliases `$7E2830` tech state | relocate the `$2830-$287F` compatibility block or patch all record consumers |
| menu record load | `$C2:8839` | aliases tech state | use natural record only after relocation; otherwise resolve |
| battle record load | `$FD:AE52` | aliases tech state | same |
| battle record commit | `$C1:B442` | writes battle results into tech state | same |
| battle reload | `$C1:CF15` | reads the same natural formula | same |

Preferred direction: relocate the full vanilla `$7E2830-$7E287F`
compatibility block to candidate `$7E2CA0-$7E2CEF`, use
`$7E2830-$7E287F` as Schala's natural live record, and rewrite save/load so
vanilla slot offsets `$0430-$047F` retain their original meanings. This
preserves the many existing `id*$50` consumers. The candidate has static
front/rear bounds and survives loaded-field/menu-entry canaries, but remains
unapproved until the full mode-transition matrix in
`docs/wram_compatibility_block_audit.md` passes.

## Persistent tech state collision

`verified-static`

- `$7E2830-$2836`: seven single-tech progress counts.
- `$7E2837-$283D`: seven learned-single masks.
- `$7E283E-$284C`: 15 dual-tech group masks.
- `$7E284D-$285B`: 15 triple/rock-tech group masks.
- The remaining bytes through `$287F` must be treated as part of the
  compatibility relocation until individually mapped.

Adding Schala's single group plus six one-wide dual groups and two one-wide
triple groups grows the learned-state model by nine groups. Relevant gates:

- `Tech_CheckComboReqs` `$C1:F533`, seven-PC reject at `$C1:F555`.
- Tech-next/learn paths `$C1:F45F/$C1:F46F/$C1:F4DF/$C1:F508`.
- Menu rebuild `$FF:F813`, including absent mask `$FE` at `$FF:F84F`,
  37-group bound at `$FF:F863`, seven-PC loop at `$FF:F8B9`, and dual/triple
  counts at `$FF:F910/$FF:F936`.
- Single boundaries at `$FD:A89D` have starts
  `01,09,11,19,21,29,31,39`; ID7 has a start but no valid end.
- `CharTechRangeTable` `$C2:BD40` contains 37 boundaries for 36 groups.
- Combination requirements at `$CC:2778-$CC:2982` use bank-local 16-bit
  pointers. Moving them outside bank `$CC` requires reader changes.

## Growth and base-tech tables

`verified-static`

| Table | Shape/address | ID7 state | Consumers/gate |
| --- | --- | --- | --- |
| HP growth | `$CC:258A`, seven × 8 | falls into MP data | relocate to eight rows; `$C1:F885/$F894` |
| MP growth | `$CC:25C2`, seven × 8 | falls into stat data | relocate to eight rows; `$C1:F8D0/$F8DF` |
| stat growth | `$CC:25FA`, eight × 7 | record 7 exists but is zero | populate deliberately |
| TP thresholds | `$CC:26FA`, seven × 16 | falls into next table | relocate to eight rows; TP award begins `$C1:F39A` |
| tech base/count | `$CC:276A`, seven × 2 | next data is dual requirements | relocate/extend; `$C1:F45F/$C1:F4DF` |

## Basic attack and equipment

`verified-static`

- Basic-action map `$CC:2583-$2589` contains seven IDs `$75-$7B`. ID7
  reads the first HP-growth byte at `$CC:258A`. Load site: `$C1:BFFF`.
- The direct-PC-ID approach-policy table `$CC:F63C-$CC:F643` has eight
  occupied bytes. ID7 reaches `$FF` in bounds and takes the nonzero pathfind
  branch; the byte is not a free eighth entry. Consumer: `$C1:4A44`.
- Three seven-byte attack-animation selector maps begin
  `$CD:4000/$4007/$400E`. Loads occur at
  `$C1:438B/$43C4/$43F8`. ID7 respectively reaches the next selector family,
  Crono's active critical selector at `$CD:400E`, and the following record at
  `$CD:4015`. All three consumers need independent expanded data; none may be
  extended in place. The complete fail-closed boundary proof is
  `docs/pc7_attack_adapter_audit.md`.
- `Item_CheckCharCanEquip` `$C2:93A8` ANDs an item's equip mask with
  `CharPartyFlagTable[id]`. ID7 maps to `$01`.
- Schala-only equipment can use mask `$01`; a general item must change from
  `$FE` to `$FF` if Schala may equip it.
- Equipment roster scan `$C2:8900` stops at seven and depends on seven-entry
  menu buffers; changing only its bound is unsafe.
- Element/type icon map `$C2:A2C6` has seven entries; hook `$C2:A27C`.
- The attack-formula pointer table at `$C2:91DB` already has eight entries;
  ID7 selects the standard Power/weapon formula.

Several unnamed weapon IDs exist, but none is declared free. Every candidate
needs reference, event, inventory, graphics, shop, and treasure audits before
reuse. A production builder should preferably allocate expanded item data
rather than silently repurpose an unknown vanilla ID.

The proposed Star of Zeal MP-discount effect is not a generic weapon property:
battle and menu MP discount paths currently inspect accessories. The lower-risk
launch version is the design document's Magic-bonus fallback.

## Action-command namespace decision

`verified-static`

- Named player actions occupy IDs `$01-$74`.
- The seven basic attacks occupy `$75-$7B`.
- Only `$7C-$7F` remain before bit-7/sentinel semantics.
- Schala's launch set requires:
  - 8 singles;
  - 6 duals;
  - 2 triples;
  - 1 basic attack;
  - total: 17 actions.

At least 13 additional identities are needed beyond the four appendable IDs.
Deleting or replacing vanilla commands is not acceptable.

The selected proposal uses globally unique raw IDs:

- `$80-$87`: eight Schala singles;
- `$88-$8D`: six Schala duals;
- `$8E-$8F`: two Schala triples;
- `$90`: Schala's Focus Pulse basic action.

`verified-static`: these IDs pass unchanged through the seven-byte battle-menu
descriptor, queue byte `+6`, `$7EB18C`, and `$7EAE93`. No queue sidecar or
owner alias is required. `$7C-$7F` remain untouched, and `$F0-$FF` remain
reserved for the battle marker family.

The high-bit overlay is not yet runtime-approved. Signed list tests, names,
descriptions, target modes, main-menu state, ATB refund, player animation,
and the `$C1:D70D` runtime-flag reader need explicit branches. The complete
address map and test gate are in
`docs/schala_command_namespace_architecture.md`; the pinned machine-readable
assignment is in `tools/schala_command_layout.py`.

## Tech table collisions and readers

`verified-static`

| Data | Vanilla extent | Immediate following data | Principal readers to retarget |
| --- | --- | --- | --- |
| names `$CC:15CF` | 116 × 11, IDs 1-`$74` | other fixed data | `$C1:0B69`, `$C2:5AA8`, `$C2:BDD9` |
| target modes `$CC:1ACB` | IDs 0-`$74`, 2 bytes | item/enemy targets at `$1BB5` | `$C1:C253/$C259`, `$C1:C9BC/$C9C9`, `$C1:CA9E/$CAAB`, `$C1:CD49/$CD56`, `$C2:B457` |
| per-character command records `$CC:1BEB` | 124 × 11, IDs 0-`$7B` | tech properties at `$213F` | learning, MP helpers, action dispatch, combo learning |
| properties `$CC:214B` | 72 × 12, IDs 0-`$47` | participant lists at `$249F` | `Battle_LoadTechProps` `$C1:D5EF` |
| participant lists `$CC:249F` | variable three-byte records | record 7 is first dual | add explicit `[07,FF,FF]`; do not infer record 7 |
| MP costs `$CC:253B` | IDs 1-`$47` | basic-action map at `$2583` | menu and battle MP readers |

## Multi-tech builder constraints

`verified-static`

- Dual builder `$C1:CA1A` assumes action IDs `$39-$65`, three actions per
  group, and at most six per actor.
- Triple builder `$C1:CCCB` assumes IDs `$66-$74`, one action per group.
- Six Schala duals have six different participant masks, so they must be six
  one-wide groups or a data-driven equivalent. Packing them into two
  three-wide vanilla-shaped groups would produce incorrect eligibility.
- Battle combatant ID-to-slot table `$7EB1BE` is cleared for seven bytes at
  `$FD:B28A`; ID7 otherwise reads stale `$B1C5`.

## Fit of the proposed creative mechanics

The stock executor can directly support straightforward one-target, line,
circle, all-enemy, revive, and barrier primitives. These proposed moves need
compound/custom handling or a deliberate simplification:

- Stillpoint: damage plus Slow.
- Sanctuary: cleanse plus party barrier.
- Astral Gate: all-enemy damage plus self penalty.
- Horizon Arc: mixed Lightning/Shadow.
- Phase Engine: enemies damaged while allies are buffed.
- New Dawn: living-party heal, one revive, and enemy damage use incompatible
  target sets.

The content design already permits safe fallbacks where needed. Originality is
preserved by names, balance, targeting combinations, animation composition,
and authored data; it does not require forcing an unsafe compound primitive.

## Activation gate

Before encoding any Schala action:

- choose and document the command-namespace extension;
- prove the live-record/tech-state relocation and save compatibility;
- relocate/extend growth, basic-action, selector, tech-base, group, and
  learned-state tables;
- extend combatant and menu buffers safely;
- allocate item IDs only after an ownership audit;
- run menu, MP, learning, basic attack, critical, battle exit, and save/load
  checkpoints for every new action.
