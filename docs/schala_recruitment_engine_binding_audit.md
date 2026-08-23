# Schala recruitment engine-binding audit

Status: static routing audit complete; no recruitment binding installed  
Evidence: `verified-static` unless a row says otherwise  
Last updated: 2026-07-25  
Target: Project Epoch Schala, logical playable PC `$07`

## Outcome

The 29 dependencies in
`assets/source/schala/v0/content/schala_recruitment_content_v0.json` now have a
bounded engine audit. The audit identifies reusable vanilla primitives and the
specific Project Epoch adapters still required, but it deliberately installs
nothing:

- all 29 authoring bindings remain `unmapped`;
- all `engine_address`, `event_opcode`, `data_table`, and `encoded_value`
  fields remain `null`;
- no event bytecode, dialogue encoding, map data, graphics, ROM allocation, or
  ROM patch was created;
- no vanilla dialogue, event, map, or graphics bytes were copied;
- the audit report emits only addresses, counts, hashes, and classifications.

This distinction is important. A verified dispatcher entry proves how the
vanilla engine transports an operation. It does not prove that PC `$07`, a new
item, a new action, a new map, or a new storage allocation is safe at the
operation's destination.

The most consequential findings are:

1. Vanilla party operation 1 can transport character ID `$07`, but it is not
   an “add only if space exists” primitive. When all three active slots are
   occupied it replaces active slot 3 and shifts the displaced character into
   the reserve list. The recruitment graph therefore needs a proved open-slot
   helper before active insertion.
2. Vanilla naming cannot be reused for Schala by passing character ID `$07`.
   The name-entry screen computes `$7E:2C23 + id*6`; ID `$07` is
   `$7E:2C4D`, the existing Epoch/time-machine name. The dialogue PC-name table
   also has a null entry for PC `$07`. Schala needs independent live name
   storage plus name-entry and dialogue-substitution adapters.
3. `CharPartyFlagTable` does contain a bit-0 mask for entry `$07`, but that
   local table fact is not proof that the surrounding roster, menu, graphics,
   save, battle, or New Game+ paths accept PC `$07`.
4. The New Game+ partial loader is a stable hook surface, not an event-script
   condition. Project Epoch must normalize sidecar policy at that loader before
   the authored quest graph evaluates its state.

No production recruitment event should be compiled until these and the other
gates in this document are closed.

## Pinned evidence and reproduction

### Canonical ROM

The audit accepts only a headerless Chrono Trigger US Rev0 ROM:

| Property | Value |
| --- | --- |
| Size | `$400000` bytes |
| SHA-1 | `de5822f4f2f7a55acb8926d4c0eaa63d5d989312` |
| SHA-256 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |

The ROM is a local-only input and is never emitted by the audit.

### Authored recruitment source

| Property | Value |
| --- | --- |
| Path | `assets/source/schala/v0/content/schala_recruitment_content_v0.json` |
| File SHA-256 | `00c750b2f9be163c75d75af947d1ea2a2ee39d16adfc0640e9292ad487b66412` |
| Binding count | `29` |
| Installed binding count | `0` |

### Reconstructed engine source

Pinned `ct_disassembly` commit:
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`

| Source | SHA-256 |
| --- | --- |
| `bank_C0.asm` | `b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8` |
| `bank_C1.asm` | `298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa` |
| `bank_C2.asm` | `d96c0d9707d9150dbdb3ad7d995f7ae135e87ebb6329691cab2eb86447611032` |
| `bank_FF.asm` | `18f30c2a4f547722f30934bde43eb6a638d9467aa064e21340aa2065ab71829e` |

Run the metadata-only audit:

```powershell
python tools/audit_schala_recruitment_engine_bindings.py `
  --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
```

Run its focused tests:

```powershell
python tests/test_schala_recruitment_engine_binding_audit.py -v
```

The audit fails closed if the source hashes, ROM identity, 29-binding inventory,
null-binding contract, dispatcher targets, party mask, name table, save
descriptor table, or New Game+ loader hash drift.

## Binding disposition

“Primitive proved” means only that the named vanilla transport or operation was
verified in the canonical ROM and pinned reconstruction. It does not authorize
an encoded value or an installation.

| # | Binding | Static finding | Required gate before binding |
| ---: | --- | --- | --- |
| 1 | `quest_entry_dispatch` | The location-event load and dispatch route is proved. | Allocate original Silent Palace map/event data, build its location record and exits deterministically, then trace the installed trigger. |
| 2 | `quest_unlock_flag` | The sidecar host format assigns quest flag bit 0; generic event-memory and absolute-memory operations exist. | Create a named live quest mirror, load it only from a fully valid sidecar, and hook save/load/erase. |
| 3 | `anchor_counter` | The sidecar host format assigns `$79`, valid range 0-3; generic read/write/increment operations exist. | Define the live mirror and a saturating/validated update adapter; prove each anchor event and persistence. |
| 4 | `ward_resolved_flag` | The sidecar host format assigns quest flag bit 1. | Bind a live flag only after the unlock-plus-three-anchors invariant is enforced at load and mutation. |
| 5 | `recruited_flag` | The sidecar host format assigns quest flag bit 2. | Keep persistent joined state synchronized with roster bit 0 and PC `$07` initialization across load, erase, and New Game+. |
| 6 | `join_grant_guard_flag` | The sidecar host format assigns quest flag bit 3. | Implement an atomic, crash-safe grant/roster/persist sequence and prove repeat entry cannot duplicate items or techs. |
| 7 | `new_game_plus_context_query` | The partial-loader route at `$FF:FAED-$FF:FBD2`, called at `$C2:E6D8`, is proved. No stable location-event opcode exposes this context. | Hook the loader and apply the host-tested retain/reset policy before entering the quest graph. |
| 8 | `magus_presence_query` | Event opcode `$D2` reaches `$C0:38E8`, then party operation 0; operand `$06` is Magus. | Compile this only as a dialogue branch and verify both runtime branches. It must never gate recruitment eligibility. |
| 9 | `party_capacity_query` | Active slots are `$7E:2980-$7E:2982`; a high-bit-set slot is empty. No semantic event opcode answers “is there room?” | Add a named helper/adapter and test every active-party occupancy and order. |
| 10 | `logical_pc_07_runtime_record` | Natural record candidate `$7E:2830-$7E:287F` remains preferred. | Relocate the complete vanilla compatibility block to candidate `$7E:2CA0-$7E:2CEF` and finish the required runtime canary matrix before declaring either range. |
| 11 | `logical_pc_07_roster_insert` | Event `$D0` at `$C0:38BE` reaches party operation 4, which registers a missing character in reserve slots. | Complete PC `$07` record, roster, menu, graphics, equipment, and save adapters; prove idempotence. |
| 12 | `logical_pc_07_active_party_insert` | Event `$D3` at `$C0:3919` reaches party operation 1. | Call only after the open-slot helper succeeds; prove no displacement, no duplicate roster entry, and correct PC `$07` record loading. |
| 13 | `logical_pc_07_reserve_insert` | Event `$D0` / party operation 4 provides the reserve-registration primitive. | Use after the full-party branch and only after all PC `$07` consumers accept the ID. |
| 14 | `party_exchange_ui` | Event `$C8` with the party request route reaches `$C0:0CF0`, `$C0:19C7`, then `MenuOverlay_Launch` `$C2:8000` mode 5 / screen 7. | Complete all eight-character menu adapters and verify return-to-field state before encoding the request. |
| 15 | `starting_tech_unlocks` | Sidecar fields `$66-$67` define host-side single-tech progress; there is no semantic event primitive for Schala’s high action IDs. | Install the PC `$07` tech record, high-ID action adapters, learned-tech representation, live/sidecar synchronization, and a one-time semantic grant helper. |
| 16 | `starting_loadout_inventory` | Event `$CA` adds an item and `$D5` equips one through proved inventory/party dispatchers. | Install original item descriptors and every sanitizer/classification/equip adapter for the selected IDs before granting or equipping them. |
| 17 | `pendant_shard_inventory` | Event `$C9/$CA/$CB` provides test/add/remove primitives. | Select and install an approved original item ID/descriptor and prove key-item classification, capacity behavior, idempotence, and consumption policy. |
| 18 | `dialogue_text_storage` | `$B8` sets a 24-bit dialogue table pointer; textbox commands route through `Dialog_RenderRequest` `$C0:20F2` to `Text_RenderStringVec` `$C2:0003`. | Implement an original-text encoder, named expanded allocations, pointer emission, and deterministic validation. |
| 19 | `dialogue_choice_dispatch` | Decision textboxes `$C0/$C3` route through `$C0:3643/$C0:36AA`; the result is stored at `$7F:0A80 + object`, and `$1A` branches on it. | Compile the original accept/decline text and verify both paths, cancellation behavior, and re-entry without mutation. |
| 20 | `silent_palace_map` | Event `$E0` reaches the location-change handler at `$C0:3AB7`. | Author an original compact map, event packet, exits, location metadata, and expanded allocations; prove entry/exit and reload. |
| 21 | `schala_event_object` | Event `$81` reaches the direct-PC-object loader at `$C0:4476`. | Complete PC `$07` field descriptor/graphics resolution or create a separately proved event-object adapter; trace spawn, animation, reload, and removal. |
| 22 | `schala_original_field_sprite` | Original source work is partial; a private canonical-ROM-derived vanilla Schala provider now supplies 23 records and 79 tiles, but the vanilla PC sprite tables still provide no free PC `$07` entry. | First prove the private provider through a supported-slot field replay with explicit entrypoint fallback. Then install bounded PC `$07` source resolvers without overwriting entries `$07/$08` or NPC `$09`; final distributable art remains a separate original-art gate. |
| 23 | `schala_original_battle_sprite` | Original source work is partial; the private vanilla NPC-family provider has no proved battle semantics, and vanilla low source indices beyond `$06` are occupied actors or vehicles. | Inventory and prove the required battle roles before choosing compatible or original frames, then install bounded PC `$07` battle resolvers without overwriting existing sources. |
| 24 | `schala_original_portraits` | Original portrait source is complete, but its menu/save-preview installation is unmapped. | Allocate/install portrait tiles and palette and adapt every PC-count/index consumer in menus and save preview. |
| 25 | `guest_veil_demonstration` | Event `$D8` reaches battle launch at `$C0:3A83`; this proves only encounter launch. | Implement and trace a safe guest-caster/component/effect route for original Veil, or replace the scene with a non-battle original effect. |
| 26 | `save_sidecar_persistence` | The three-record `$30:7E00-$30:7FDF` v1 sidecar format and validation policy are host-defined and tested. | Hook normal save, full load, save preview, and exact-slot erase; reproduce all validation classes at runtime and power-cycle test all slots. |
| 27 | `new_game_plus_transfer` | The host sidecar model defines retain and reset branches; the vanilla partial loader and its caller are proved. | Hook `$FF:FAED` safely, apply the selected policy once, rebind the vanilla checksum, and test both branches without duplicate grants. |
| 28 | `scene_music` | Event `$EA` reaches `$C0:3C2F`; current song state is `$7E:29AE`. | Choose a non-conflicting scene track and prove start, map transition, battle interruption, and restoration policy. |
| 29 | `scene_sound_effects` | Event `$E8` reaches `$C0:3C11`. | Select and audition non-conflicting ward-release/join cues and verify timing; no encoded IDs are approved yet. |

All rows remain `unmapped` in the authored JSON. The table is an
implementation routing plan, not a patch manifest.

## Engine routes proved by the audit

### Location-event lifecycle

The location record supplies an event ID through the table rooted at
`$F6:0008`. The corresponding event pointer table is rooted at `$FC:F9F0`.
The event packet is decompressed at `$C0:56D4` to `$7F:2000`, initialized at
`$C0:5709`, and its initialization script is entered through `$C0:595C`.
Object-script slices are selected at `$C0:5A93`. The command jump table begins
at `$C0:5D6E`.

This proves where a deterministic original event builder must connect. It does
not identify a free event ID, location ID, pointer-table slot, or ROM range.

### Quest state primitives

The following command targets are verified:

| Opcode | Target | Primitive |
| ---: | --- | --- |
| `$12` | `$C0:62DE` | script-memory comparison |
| `$16` | `$C0:63E6` | event-memory conditional |
| `$48` | `$C0:6792` | 24-bit absolute read |
| `$4A` | `$C0:67D7` | 24-bit absolute immediate write |
| `$53` | `$C0:693D` | event-memory read |
| `$56` | `$C0:69A6` | event-memory write |
| `$65` | `$C0:6B76` | event-memory bit set |
| `$71` | `$C0:6C69` | script-memory increment |

These are generic mechanisms, not permission to assign Project Epoch state to
an arbitrary WRAM address. The quest graph must read and mutate named live
state whose ownership, reset behavior, validation, and sidecar synchronization
are already proved.

### Dialogue and choices

Verified routes:

- `$B8 -> $C0:3557`: load a 24-bit dialogue-table pointer;
- `$BB -> $C0:3570`, `$C1 -> $C0:35B5`, `$C2 -> $C0:35FC`:
  textbox variants;
- `$C0 -> $C0:3643`, `$C3 -> $C0:36AA`: decision textboxes;
- shared decision setup at `$C0:3674` stores the choice result at
  `$7F:0A80 + object`;
- `$1A -> $C0:6568`: branch on the stored result;
- `Dialog_RenderRequest` `$C0:20F2` ultimately calls
  `Text_RenderStringVec` `$C2:0003`.

Original text encoding, a new pointer table, and expanded storage remain
unmapped. This audit does not extract or reproduce any vanilla strings.

### Party and roster

Event commands reach `Party_DispatchOp` `$C2:8C36` through the C2 party vector
at `$C2:8004`. Its verified operation table begins at `$C2:8C5B`:

| Operation | Target | Relevant behavior |
| ---: | --- | --- |
| `$00` | `$C2:8C75` | query active slots |
| `$01` | `$C2:8C79` | add to active formation |
| `$02` | `$C2:8CA2` | remove from active formation |
| `$03` | `$C2:8CCF` | query nine-slot roster |
| `$04` | `$C2:8CE5` | register in reserve if missing |
| `$05` | `$C2:8CF7` | mark roster entry inactive |
| `$06` | `$C2:8D05` | recalculate party HP/equipment state |
| `$07` | `$C2:8D45` | additional party maintenance |
| `$08` | `$C2:8D63` | additional party maintenance |
| `$09` | `$C2:8D6A` | additional party maintenance |
| `$0A` | `$C2:8D8F` | equip item |
| `$0B` | `$C2:8C5A` | no-op/return |
| `$0C` | `$C2:8E1E` | item quantity |

Every operation returns through `Menu_LoadPartyD1Recs` at `$C2:834D`. For an
active ID it resolves the character’s D1 record through `$C2:F5ED`. Therefore
even a roster-only event is unsafe for PC `$07` until natural record and
graphics/equipment adapters are present.

#### Full-active-party hazard

Party operation 1 first searches `$7E:2980-$7E:2982` for a high-bit-set empty
slot. If none exists, it writes the new ID to `$7E:2982` and shifts the
displaced ID into the reserve portion of the nine-slot list. That behavior is
valid vanilla party machinery, but it does not match the authored Silent
Palace full-party branch.

Required recruitment rule:

```text
if an active slot is empty:
    initialize/register PC $07, then use active insertion
else:
    initialize/register PC $07 in reserve, then offer party exchange
```

Do not call `$D3` speculatively and try to repair the formation afterward.

#### Vanilla North Cape behavioral reference

`verified-runtime` on RetroArch 1.22.2/current bsnes

The actual full-party Magus recruitment path now provides a clean behavioral
reference. Before recruitment, active party `04 01 03` and compact roster
`04 01 03 83 81 84 02 05 80` contain no Magus. At Magus name entry, before
the name is accepted, the active formation is unchanged and the roster is
`04 01 03 06 81 84 02 05 80`: Magus `$06` has been registered in reserve.
Accepting the default name opens native party exchange. Selecting Magus then
produces active party `06 01 03` and roster
`06 01 03 04 81 84 02 05 80`, moving Frog `$04` to reserve.

That sequence supports the authored full-party rule: reserve registration
must precede an optional replacement UI. It does not authorize PC `$07`,
prove an eight-character menu, or remove the need for the explicit capacity
query. The complete source-save provenance, replay inputs, hashes, canary
checks, and fight-branch control are in
`docs/vanilla_magus_recruitment_runtime_trace_2026-07-26.md`.

### PC `$07` naming collision

Two independent static facts block direct reuse of the vanilla naming path:

1. `NameEntry_SetupScreen` `$C2:E40E` computes the destination as
   `$7E:2C23 + id*6`. ID `$07` therefore targets `$7E:2C4D`, which belongs to
   Epoch.
2. The dialogue PC-name address table at `$C2:5FD8` contains valid addresses
   for IDs `$00-$06` and `$0000` for entry `$07`. Text control `$20`
   separately prints Epoch’s name from `$7E:2C4D`.

The Project Epoch sidecar already reserves six independent Schala-name bytes
at offset `$60`. A future runtime adapter must copy a validated name to
separately owned live storage, route name-entry commit there, teach dialogue
substitution how to resolve logical PC `$07`, and preserve Epoch’s six bytes
unchanged.

The North Cape reference also confirms the visible ordering available to the
player: roster registration can occur before name acceptance, and the
full-party replacement screen can follow it. Schala may follow that ordering
only after her independent live-name destination and interruption-safe
recruitment transaction exist; passing `$07` to vanilla name entry remains
forbidden.

### Source-only recruitment transaction

The original authoring graph is a narrative state machine, not a safe engine
write ordering: its symbolic recruitment/grant action precedes the capacity
branch and must not be compiled literally.

`tools/schala_recruitment_transaction.py` now provides a host-tested,
runtime-unverified contract with distinct boundaries for:

1. a checksum-bound persisted sidecar plus an explicit PC `$07`
   record-readiness token;
2. reversible live reserve staging that leaves the sidecar unchanged;
3. independent opaque six-byte naming;
4. a capacity-safe commit only after a caller-supplied completion witness
   asserts all three grant components;
5. optional party exchange as a post-commit action; and
6. later sequence increment and checksum binding computed from the exact
   serialized vanilla `$A00` slot bytes, after its roster and joined bit agree
   that PC `$07` is recruited.

The model rejects state disagreement among the recruited flag, joined-mask bit
`$01`, exact PC `$07` roster presence, and the grant guard. It prefers an
existing inactive `$87` cell, leaves all active bytes unchanged on the full
branch, requires exact sealed host types, revalidates each derivation and the
serialized slot's PC `$07` membership, and makes already-recruited entry
effect-free. Names remain opaque: Epoch safety is represented by carrying its
separate six-byte buffer unchanged, not by prohibiting equal displayed values.

The focused tests use a synthetic `host-fixture` record only. No production
record-readiness token, live grant observation, live-name address, hook, or
allocation is approved.
The complete contract and evidence boundary are in
`docs/schala_recruitment_transaction_contract.md`.

### Inventory and equipment

Verified event routes:

- `$C9 -> $C0:3780`: test item quantity/presence;
- `$CA -> $C0:37B1`: add item;
- `$CB -> $C0:37E3`: remove item;
- `$D5 -> $C0:3A68`: equip through party operation `$0A`.

The inventory commands enter `Battle_ServiceCallEntry` `$C1:8003`, then
`Battle_InventoryGoldApiVec` `$C1:CFC2`; add and remove implementations begin
at `$C1:D005` and `$C1:D056`.

This proves byte transport for candidate item IDs `$E8-$EE`. It does not prove
global availability or installability. The item overlay still needs named
expanded allocations and every classification, sanitizer, equipment, shop,
menu, description, and visual adapter required by its separate audits.

### Save, load, and New Game+

The vanilla save writer is `$FF:F9FB`. Its eight-entry descriptor table begins
at `$FF:FA7B`; the complete `$28`-byte table has SHA-256:

`30dfb2fbcf65bb8a21f09a2f1048d0615cf9b5127b02db9e1a94ee66f453d12a`

The full loader begins at `$FF:FAA3`. The separate New Game+ partial loader
occupies `$FF:FAED-$FF:FBD2` and has SHA-256:

`b61e4ce9bb771450419cdb7ef558af98180c20ab8bbc83d99f7ea9b142a3cd77`

Its caller invokes it at `$C2:E6D8`. Neither path currently reads or writes the
Project Epoch sidecar. The host-side codec and policy in
`tools/schala_sidecar.py` are specifications for future hooks, not proof that
the game persists PC `$07`.

## Required implementation order

The static routes imply the following dependency order:

1. Finish the full `$7E:2830-$7E:287F` compatibility-block relocation proof
   and only then establish natural PC `$07` live record ownership.
2. Implement sidecar save, full-load, erase, save-preview, and New Game+ hooks;
   populate live state only after all v1 validation checks pass.
3. Add independent Schala live-name storage plus name-entry and
   dialogue-substitution adapters, preserving Epoch.
4. Complete PC `$07` roster, menu, field, battle, portrait, equipment, item,
   and tech-index adapters before any recruitment event can make `$07` joined
   or active.
5. Use the private vanilla-derived provider for supported-slot field adapter
   diagnostics, then finish original distributable Schala field/battle art and
   the original Silent Palace map, dialogue, and event source. Allocate every
   installed packet in named expanded space through a deterministic builder.
6. Add explicit helpers for validated quest-state access, active-party
   capacity, one-time item/tech grants, and atomic recruitment commit.
7. Compile the authored graph only after each dependency has a proved binding.
   Use `$D3` only on the open-slot branch and `$D0` on the full-party reserve
   branch.
8. Implement the guest Veil presentation only after the high-action-ID and
   guest-caster route is proved; otherwise use an original non-battle scene
   that does not pretend to prove playable tech execution.
9. Select music/SFX IDs and restoration policy, then run the complete field,
   menu, battle, save/load, New Game+, erase, reset, attract-mode, and
   power-cycle matrix.

## Production stop conditions

Stop without emitting a patch if any of the following remains true:

- a recruitment binding in the authoring JSON would have to be guessed;
- the natural PC `$07` record or relocation destination has not passed its
  complete runtime matrix;
- ID `$07` still reaches Epoch’s name storage or a null dialogue-name pointer;
- party insertion is attempted without a proved capacity branch;
- original item or action records are absent or any high-ID adapter remains
  incomplete;
- the sidecar is not integrated across save, load, erase, New Game+, preview,
  and power-cycle;
- any map, text, graphics, event, or code space is assumed free because it is
  zero-filled or adjacent to a known table;
- the deterministic builder cannot reproduce the output with hashes and an
  evidence manifest.

Until those conditions are cleared, the correct evidence claim is:

> The vanilla engine routes needed by the authored recruitment flow are
> substantially mapped, but Schala recruitment remains uninstalled and
> runtime-unverified.
