# Community modding reconnaissance for Project Epoch

Status: bounded source survey; no ROM changes, hooks, allocations, or assets  
Date: 2026-07-27  
Scope: Crimson Echoes / Flames of Eternity, Temporal Flux and Temporal Redux,
Jets of Time, Chrono Compendium and Data Crystal notes, and general ExHiROM
documentation

## Executive result

Community material is useful for:

- locating likely event commands, tables, and breakpoint candidates;
- learning historical Temporal Flux workflows;
- identifying common sprite, palette, recruitment, and New Game+ failure modes;
- finding open-source parsers whose output can be independently checked; and
- constructing a broader test matrix.

It does **not** prove that logical PC `$07` is supported, that an apparent
eighth table entry belongs to a playable character, or that any ROM/WRAM/SRAM
range is free. It cannot populate Project Epoch's empty trusted production
hook or allocation catalogs.

The strongest result of this survey is cautionary: several frequently cited
community references encode exactly the false eighth-record, false
eighth-attack-byte, and generic-free-space assumptions that Project Epoch has
already rejected through bounded static and runtime work.

No local Crimson Echoes, Kajar Labs, or Flames of Eternity technical text
corpus was found. The workspace contains only incidental names in Temporal
Redux / Jets of Time lookup data. Public project-era posts are therefore
reconnaissance sources, not a locally pinned implementation reference. This
bounded survey also found no trustworthy public source tree or developer note
showing a real eighth playable PC in Crimson Echoes or Flames of Eternity.
That is not proof that no such private material ever existed.

## Evidence grades used here

- `verified-static`: reproduced by existing Project Epoch canonical-ROM,
  reconstructed-source, or locally pinned source inspection.
- `documented/reconnaissance`: a public document, project post, source
  description, or unrerun historical observation useful for deciding what to
  inspect next.
- `unsafe counterexample`: real public documentation or code that demonstrates
  an assumption Project Epoch must not inherit.
- `hypothesis`: a plausible lead or expert/community assertion that still
  requires canonical static and runtime proof.

This note does not downgrade evidence in the subsystem audits. For example,
the North Cape ordering has separate `verified-runtime` evidence; it is
summarized here as reconnaissance and linked to the owning audit.

## Source and claim matrix

| Source or observation | Grade | Useful guidance | Project Epoch boundary |
| --- | --- | --- | --- |
| [Chrono Compendium Chrono Trigger tutorials](https://www.chronocompendium.com/Term/Tutorials_(Chrono_Trigger).html) | `documented/reconnaissance` | Index to historical graphics, portrait, event, naming, tech, and repointing tutorials. | A tutorial index is not proof that its offsets, free-space labels, or table meanings are complete. |
| [Crimson Echoes help-wanted thread](https://www.chronocompendium.com/Forums/index.php?topic=5639.0) | `documented/reconnaissance` | Project-era evidence that Crimson Echoes used Temporal Flux and depended on event polish, sprite work, and sprite-assembly knowledge. | It documents workflow and staffing needs, not an eighth-character architecture. |
| [Crimson Echoes beta-testing thread](https://www.chronocompendium.com/Forums/index.php?topic=7105.0) | `documented/reconnaissance` | Historical reports of event/flag, palette/darkness, map-corruption, naming/description, and Epoch presentation failures. | Tester reports motivate regression coverage; they do not establish engine ownership or a safe hook. |
| [Temporal Flux Event Encyclopedia](https://www.chronocompendium.com/Term/Temporal_Flux_Event_Encyclopedia.html) | `documented/reconnaissance` | Event-language guide, including special dialogues, naming, save/load interactions, and End of Time party selection. | The existence of an event opcode proves only bytecode syntax. It does not prove that operand `$07` is a valid playable identity downstream. |
| [Temporal Redux](https://github.com/OnemusCT/temporal-redux) README and local snapshot | `documented/reconnaissance` | Temporal Redux identifies itself as a Temporal Flux remake built with substantial [Jets of Time](https://github.com/Pseudoarc/jetsoftime) code. It is useful as an independently implemented parser and command catalog. | Its README says strings cannot be edited, records UI crashes, and says commands and menus have not been extensively tested. Project Epoch may cross-check parsing, but cannot treat the UI labels as engine proof. |
| Temporal Redux PC lookup is exactly `$00-$06` for Crono through Magus and `$07` for Epoch | `verified-static` | Confirms that the community editor itself keeps the final game's PC-name namespace separate from an imagined eighth playable PC. See the public [`lookups.py`](https://github.com/OnemusCT/temporal-redux/blob/main/sourcefiles/editorui/lookups.py). | Never relabel the editor's `$07` Epoch entry as Schala. Project Epoch's logical PC `$07` needs context-specific adapters. |
| Temporal Redux / Jets raw load-PC opcodes `$80/$81` and party/name helpers accept a byte operand | `unsafe counterexample` | The public [`eventcommand.py`](https://github.com/OnemusCT/temporal-redux/blob/main/sourcefiles/jetsoftime/eventcommand.py) is useful for finding opcode encoders and dispatcher breakpoints. | Parser acceptance is only transport. Operand `$07` reaches occupied graphics tables, Epoch naming, or seven-only consumers. A syntactically valid command is not a valid playable-PC operation. |
| Temporal Redux labels `$D3` generically as "Add PC to Party" | `unsafe counterexample` | Locates the active-party insertion command and its related `$D0` reserve-registration command. | The label hides the full-party behavior: operation 1 replaces active slot 3 and moves the displaced PC to reserve. Capacity must be checked before `$D3`; the full branch must use `$D0` then party exchange. |
| Vanilla full-party North Cape recruitment orders reserve registration, name entry, then party exchange | `documented/reconnaissance` backed by existing local `verified-runtime` evidence | Provides the correct behavioral model for a full-party recruit: register the recruit in reserve, allow naming, then offer optional replacement. See [the recruitment engine audit](schala_recruitment_engine_binding_audit.md) and [the runtime trace](vanilla_magus_recruitment_runtime_trace_2026-07-26.md). | The Magus path proves ordering for vanilla PC `$06`; it does not authorize PC `$07`, prove an eight-character menu, or remove the explicit capacity branch. |
| Vanilla name-entry ID `$07` targets Epoch at `$7E:2C4D`; dialogue PC-name entry 7 is null | `verified-static` | Identifies exact naming adapters and preservation canaries. | Never call the vanilla PC-name path with logical PC `$07`. Schala needs independent live storage, dialogue substitution, save, and load handling while Epoch remains byte-exact. |
| Vanilla raw PC `$07` graphics lookup reaches occupied NPC/vehicle/sentinel data | `verified-static` | Identifies field, battle, menu, portrait, palette, and animation resolver boundaries. See [the graphics/menu hook audit](pc7_graphics_menu_hook_audit.md). | Do not overwrite graphics entries `$07/$08`, treat the animation boundary as a record, or infer a playable sprite source from a raw opcode. |
| Vanilla has exactly seven initialization records and seven HP, MP, and TP rows | `verified-static` | Defines required initialization, growth, and learning adapters. See [the PC initialization schema audit](pc_init_record_schema_audit.md). | `$CC:0230` is compatibility/tech state, not record 7. HP row 7 enters MP data, MP row 7 enters stat data, TP row 7 enters the next table, and the all-zero stat row 7 is not a finished definition. |
| [Data Crystal SRAM map](https://datacrystal.tcrf.net/wiki/Chrono_Trigger_%28SNES%29/RAM_map) labels the `$0200` region as Crono through Epoch | `unsafe counterexample` | Correctly points toward the `$A00` slot, three party bytes, names area, and `$50`-byte vanilla record shape. | Its stated character length is 560 decimal (`$230`), exactly seven `$50` records, not eight. It also publishes the misleading Magic-before-Hit stat order. Use it only to choose verification targets. |
| [EpochEditor constants](https://raw.githubusercontent.com/codergal6502/EpochEditor/main/src/EpochEditor.SramUtilities/SramConstants.cs) restrict party IDs to `$00-$06` and use `$80` for empty, while [GameSlot.cs](https://raw.githubusercontent.com/codergal6502/EpochEditor/main/src/EpochEditor.SramUtilities/GameSlot.cs) allocates and serializes eight `$50` sheets | `unsafe counterexample` | Source-level example of how a save tool can reproduce a community map while still handling the active-party namespace differently. | Its eighth write begins at slot-relative `$0430` and would treat tech state as a character. Never use this editor behavior as a Project Epoch serializer specification. |
| [Data Crystal Tech and Attack Documentation](https://datacrystal.tcrf.net/wiki/Chrono_Trigger_%28SNES%29/Tech_and_Attack_Documentation) lists `$C0230-$C0236` progress and `$C0237-$C023D` learned masks | `documented/reconnaissance` | Useful index to seven tech owners, tech properties, names, targeting, MP cost, animation/effect candidates, and attack breakpoints. | The page repeatedly marks fields unknown or unexplored. Every table end, selector, signed check, and direct index still needs a canonical audit. |
| The same Tech page calls file `$0D400E` an "8th Char's Attack byte" | `unsafe counterexample` | It identified a selector worth tracing. | Project Epoch proved that byte is shared by PC `$07` normal-attack indexing and Crono critical-attack indexing. It is not free and must not be patched as a standalone eighth-character byte. |
| [Respecting Sprites](https://pki.chronocompendium.com/Term/Modifications_%28Chrono_Trigger%29.html) description | `documented/reconnaissance` | Reports that vanilla paths inconsistently choose palettes by PC index, sprite palette pointer, or palette-index arithmetic, and that later-game/NG+ fixes were needed. | This is a strong test-matrix lead, not code-level proof. Schala still needs audited menu, field, battle, load, and NG+ palette paths. |
| [Status-menu portrait guide](https://www.chronocompendium.com/Term/Changing_the_status_menu_portraits.html) | `documented/reconnaissance` | Historical format notes for the seven 48-by-48, 15-visible-color portraits and their palettes. | It documents replacement of existing portraits, not a safe eighth portrait entry, small save-preview path, or expanded-ROM DMA plan. |
| [Jets of Time repository](https://github.com/Pseudoarc/jetsoftime) and [release history](https://github.com/Pseudoarc/jetsoftime/releases) | `documented/reconnaissance` | Open-source examples for event parsing, recruitment edits, deterministic transforms, duplicate existing characters, and additional dual-tech work. | Duplicate use of IDs `$00-$06` is not a logical PC `$07` implementation. Algorithms must be isolated, pinned, and independently checked before adoption. |
| Compendium [free-space and repointing tutorial](https://www.chronocompendium.com/Term/Claim_Free_Space_and_Repoint_Data_in_Temporal_Flux.html) | `unsafe counterexample` | Historical explanation of pointer changes and expanded-ROM workflows. | Debugger `JUNK/---` labels and repeated bytes are not provenance. They cannot establish ownership or satisfy the complete-diff and write-intent guard. |
| Temporal Redux / Jets free-space and ExHiROM machinery | `unsafe counterexample` for Project Epoch production use | Public [`ctrom.py`](https://github.com/OnemusCT/temporal-redux/blob/main/sourcefiles/jetsoftime/ctrom.py), [`byteops.py`](https://github.com/OnemusCT/temporal-redux/blob/main/sourcefiles/jetsoftime/byteops.py), and [`freespace.py`](https://github.com/OnemusCT/temporal-redux/blob/main/sourcefiles/jetsoftime/freespace.py) show a practical 4-to-6 MiB workflow and general allocator. | Project Epoch uses an inert 8 MiB fast-ExHiROM scaffold and source-controlled named allocations. Generic 6 MiB assumptions, zero/RLE heuristics, and a global free-space pool are not compatible production authority. |
| [SNESdev HiROM](https://snes.nesdev.org/wiki/HiROM), [ROM file formats](https://snes.nesdev.org/wiki/ROM_file_formats), and [ROM header](https://snes.nesdev.org/wiki/ROM_header) | `documented/reconnaissance` | Hardware-level guidance for ExHiROM mapping, header placement, map mode, ROM size, and SRAM-size fields. | Mapping documentation proves address translation only. It does not assign Chrono Trigger data ownership or approve a hook/allocation. |
| Community claims that an eighth character is a major undertaking and prerelease remnants are not a working PC | `hypothesis` | Expert-community corroboration in the [Schala Edition discussion](https://gamefaqs.gamespot.com/boards/563538-chrono-trigger/78807721) and [prerelease discussion](https://gamefaqs.gamespot.com/boards/563538-chrono-trigger/72677877) supports a broad adapter audit rather than a one-byte unlock. | Forum expertise is not a pinned trace. Historical Gaspar/Schala concepts or unused sprites cannot establish final-ROM capacity. |

## Crimson Echoes and Flames of Eternity: what can be adopted

The available Crimson Echoes material is strongest as process evidence:

1. Temporal Flux event editing can sustain a large story modification.
2. Sprite assembly and palette behavior need specialist attention.
3. Event flags, map integrity, names/descriptions, and Epoch-specific visuals
   can fail independently even when a large hack otherwise plays.
4. Late beta testing is not a substitute for subsystem-level deterministic
   replays.

The material does not show:

- a new logical playable ID;
- an eighth `$50` initialization record;
- an eighth save record;
- an eighth growth or tech-learning row;
- independent ID-7 naming;
- safe ID-7 field and battle graphics resolution; or
- a production allocation layout suitable for Project Epoch.

Flames of Eternity search results were dominated by release, patch, review,
and later bug-fix pages rather than source or engineering documentation.
Those downloads are intentionally excluded from this reconnaissance. Without
a source tree, exact revision, and reproducible comparison, Flames of
Eternity must not be reverse-used as an architectural authority.

## Temporal Redux and Jets of Time: safe use

The local Temporal Redux snapshot has already served as an independent parser
cross-check for canonical event decompression and command lengths. That is an
appropriate use: compare a bounded result, require exact agreement, and keep
the Project Epoch audit independent.

The following uses are also appropriate:

- enumerate event opcodes and locate candidate dispatchers;
- compare event packet boundaries and pointer decoding;
- inspect how a modern tool represents reserve, active-party, naming, item,
  and sprite commands;
- build synthetic parser tests around ambiguous commands; and
- inspect open-source algorithms before writing an independently proved
  implementation.

The following uses are not appropriate:

- accepting a menu label as complete runtime semantics;
- passing `$07` because a command encoder accepts any byte;
- importing community lookup names as namespace ownership;
- trusting `UNUSED`, `JUNK`, zeros, `$FF`, or RLE runs as free space;
- emitting a 6 MiB image as the Project Epoch production base;
- allowing an allocator to choose anonymous expanded addresses; or
- copying a patch/write path that bypasses
  `tools/validate_rom_write_intents.py`.

## Subsystem consequences

### Recruitment

The public command catalogs give useful names to `$D0`, `$D3`, `$C8`, and
related checks. The canonical dispatcher and North Cape trace provide the
semantics Project Epoch may rely on:

```text
if an active slot is open:
    prepare and register PC $07
    insert PC $07 into the open active slot
else:
    prepare and register PC $07 in reserve
    commit the independent Schala name
    offer party exchange
```

The generic `$D3` helper is not a capacity helper. Repair after speculative
insertion is forbidden because downstream record, graphics, menu, and save
consumers can run between writes.

### Naming and Epoch preservation

Community tools correctly expose eight names in some contexts because the
eighth final-game identity is Epoch. An eight-entry name display is not an
eight-PC proof. Project Epoch must keep these namespaces explicit:

- logical playable PC `$07`: Schala candidate;
- vanilla naming ID `$07`: Epoch;
- dialogue PC-name entries: only `$00-$06` valid in vanilla;
- save-editor empty party slot: `$80`.

Epoch's six live name bytes are a mandatory canary across recruitment,
name-entry, save, load, New Game+, and erase tests.

### Graphics and palettes

Raw event opcodes can transport `$07`, but the resulting field, battle, menu,
overworld, portrait, palette, and animation indices are occupied or
seven-bound. Community sprite-insertion and palette notes should guide visual
test cases, never table ownership.

Schala's final distributable playable art must remain original and
provenance-backed. A private compatibility provider may reconstruct the
canonical vanilla NPC family locally from the user's pinned clean ROM, but its
bytes must stay ignored and it cannot establish table ownership, a complete
playable packet, or a final-art claim. No occupied graphics-table entry may be
overwritten. Community or Crimson Echoes additions remain reference-only until
their exact provenance and reuse permission are proved.

### Character records, growth, and techs

Public references that visually extend a table to an "eighth" row repeatedly
cross real boundaries. Project Epoch must preserve the verified shapes:

- seven `$50` initialization records;
- seven HP growth rows;
- seven MP growth rows;
- seven TP/tech-learning rows;
- seven learned-progress bytes and seven learned masks;
- a stat-growth row 7 that is all zero and not a complete definition; and
- a normal new-game `$280` copy comprising seven records plus a `$50`
  compatibility span.

Any eighth source row must live in a named expanded allocation and be reached
through a bounded adapter. It must not be appended in place across the
verified table end.

### Expansion and allocation

General ExHiROM references remain valuable for address translation and header
rules. Project Epoch's structural contract is narrower:

- the base is the validated inert 8 MiB fast-ExHiROM scaffold;
- both header copies and the source/mirror/fill invariants remain exact;
- production payloads use source-controlled named expanded allocations;
- vanilla hooks require approved exact spans and pinned preimages;
- all same-size mutations pass the fail-closed write-intent and complete-diff
  audit; and
- a booting expanded image proves only scaffold execution, never allocation
  ownership.

The 6 MiB Temporal Redux / Jets machinery is a useful implementation study,
not a compatible production builder.

## Practical adoption checklist

Before adopting any community-derived tip:

- [ ] Record the direct source URL, source type, date accessed, and exact
      revision or commit when available.
- [ ] Assign one of this note's evidence grades; default to
      `documented/reconnaissance`.
- [ ] Rewrite the tip as a bounded trace question, not as a fact to install.
- [ ] Verify the canonical US Rev0 preimage and exact table or instruction
      boundary.
- [ ] Identify the logical PC ID, computed index, pointer, source table,
      consumer, and fail behavior separately.
- [ ] Check every direct index, signed comparison, loop bound, and table end
      reached by `$07`.
- [ ] Prove that apparent zero, `$FF`, `UNUSED`, `JUNK`, or post-table bytes
      are not owned before considering them; do not treat appearance as proof.
- [ ] Keep Epoch naming, state, graphics, and vehicle paths as explicit
      preservation canaries.
- [ ] For recruitment, branch on capacity first; use active insertion only on
      the open-slot branch and reserve registration plus party exchange on the
      full branch.
- [ ] Require pinned provenance for every Schala graphics source: canonical-ROM
      provenance and private-only handling for the Phase A donor, Project Epoch
      provenance for Phase B originals, and explicit author/license provenance
      for any community addition. Portraits, items, techs, descriptions, and
      progression data remain original and provenance-backed.
- [ ] Place all new production data only in a source-controlled named 8 MiB
      expanded allocation.
- [ ] Require exact pinned preimages for any vanilla instruction hook.
- [ ] Run `tools/validate_rom_write_intents.py` and the complete-diff audit
      before writing a same-size image or emitting a patch.
- [ ] Prove vanilla IDs `$00-$06` remain equivalent at each adapter boundary.
- [ ] Exercise PC `$07` across reset, new game, Continue for all slots, field,
      menu, equipment, party exchange, naming, battle, save, reload, New
      Game+, erase, and attract/demo paths.
- [ ] Promote the result to `verified-static` or `verified-runtime` only in
      the owning subsystem audit with hashes and reproduction steps.

Until every relevant checklist item passes, a community source may guide a
breakpoint or test case, but it never proves ownership or playable-PC `$07`
support.
