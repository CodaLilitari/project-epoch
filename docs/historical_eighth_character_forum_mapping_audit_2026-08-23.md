# Historical eighth-character forum mapping audit

Status: bounded primary-forum claim audit; no historical patch applied and no
ROM, save, state, graphics, or forum payload committed  
Date inspected: 2026-08-23  
Target: Project Epoch natural logical PC `$07`, currently designed as Schala

## Result

The historical developers did publish a substantial amount of data mapping,
mostly in the Chrono Compendium's long-running
[`8th Playable Character Possible?!` thread](https://www.chronocompendium.com/Forums/index.php?topic=4100.0).
The mapping is useful, but it is not a latent implementation specification.
It mixes five different kinds of evidence:

1. correct table roots and runtime-record formulas;
2. collisions that were initially mislabeled as unused eighth-character data;
3. experimental fixes tied to one evolving 6 MiB patch layout;
4. global substitutions that made PC `$07` display by moving or replacing the
   NPC, menu, portrait, or Tech data it collided with; and
5. later architectural observations that correctly conclude whole table
   families and consumers must be expanded or adapted.

The separate
[`Project Schala` thread](https://www.chronocompendium.com/Forums/index.php?topic=6288.0)
contains much less natural-PC mapping. Its author explicitly began with a
Magus-slot replacement because the eighth character was not ready, briefly
imported selected `8thy` graphics/assembly work, and later said the project
would need to be redone for a real eighth character. That material is valuable
as a supported-PC `$06` consumer checklist and as expanded-ROM debugging
history. It is not evidence that Schala and Magus coexisted as two complete
playable records.

Project Epoch can retain the verified boundary leads and the later separation
of base, Tech, character-specific, and name work. It must not reuse the old
addresses as allocations, install the historical patches, or inherit their
collision-based substitutions.

The publication-facing consolidation of the corrected ownership, collision,
evidence, and adapter status is
[`project_epoch_corrected_character_data_map_v1.md`](project_epoch_corrected_character_data_map_v1.md).
This historical ledger remains the claim-level source for the forum links and
verdicts; the corrected map is the canonical current implementation view.

## Verification method

Forum posts were treated as first-person historical claims, not byte
authority. The survey covered all 537 surviving posts exposed across the 36
pages of topic 4100 and all 780 posts exposed across the 52 pages of topic
6288. The old RHDN discussion mirror corroborates Magus-replacement scope but
did not add a natural-PC mapping. No logged-in or visible-screen session was
used. Each concrete address or behavior below was checked against one or more
of:

- the pinned headerless Chrono Trigger US Rev0 ROM, SHA-256
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`;
- the pinned CC0 `ct_disassembly` at
  `eeae27acdb6565e96d1d796a3d60792c250c0aa1`;
- current Project Epoch canonical-ROM audits; and
- existing current-core runtime traces where the distinction matters.

The following read-only, metadata-only audits were rerun during this review and
passed without writing an image or patch:

```powershell
python tools/audit_pc_init_record_schema.py --rom CANONICAL_ROM --compact
python tools/audit_pc7_attack_adapter_boundaries.py CANONICAL_ROM --compact
python tools/audit_pc_sprite_packet_envelopes.py --rom CANONICAL_ROM
python tools/audit_schala_recruitment_engine_bindings.py --rom CANONICAL_ROM --compact
```

Verdicts used below:

- `confirmed boundary`: the post found a real table, formula, collision, or
  consumer boundary, although its proposed fix may still be unusable;
- `mixed`: part of the observation is correct but its ownership or implied
  eighth-character meaning is wrong;
- `patch-specific`: meaningful only after the historical patch's own
  relocations and substitutions;
- `replacement-only`: demonstrates a supported Magus `$06` consumer, not
  natural PC `$07`; and
- `rejected`: contradicted by current static/runtime evidence or unsafe for
  Project Epoch.

## Generic `8thy` claim ledger

### Record, initialization, growth, and persistence

| Historical claim | Current verification | Verdict and safe use |
| --- | --- | --- |
| Justin initially called file `$0C0230-$0C0261` incomplete extra-character data and edited it as though an eighth record began there ([2007 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg71405#msg71405)). | Vanilla has exactly seven `$50` initialization records at `$CC:0000-$CC:022F`. `$CC:0230-$CC:027F` is seven-PC Tech/compatibility state, copied together with those seven records by the normal `$280`-byte new-game seed. | `rejected` as an eighth record. This is the most consequential old-map error. |
| Vehek later corrected the old label: `$0C0230-$0C0236` is the seven-byte “next Tech to learn” array, not character eight ([2007 correction](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg75297#msg75297)). | Current canonical-ROM reconstruction confirms `$2830-$2836` as seven single-Tech progress counters; learned masks and combo state follow. | `confirmed boundary`. Retain the correction and relocate the complete `$50` compatibility block before using the natural record window. |
| Justin mapped `$7E2830-$7E287F` as record-shaped PC `$07` fields, including HP, MP, base stats, level, EXP, equipment, Attack, and Defense ([2007 map](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg72728#msg72728)). | The engine's natural record formula really is `$7E2600 + id*$50`, so logical ID `$07` resolves to `$7E2830`. In unmodified vanilla, however, that window contains compatibility state, so `$2857` is rock/Tech state rather than equipment. In a real `$50` record, `+$27` would be only the helmet byte, followed by armor, weapon, and accessory. The post's widths/labels are also incomplete: HP/MP are 16-bit; EXP is `$2843-$2845`; `$2846` begins cumulative TP; `$286C` is the last live-stat byte; derived Attack/Defense are `$286D/$286E`. Its base-stat order at `+$0B-$11` matches the record layout, while the separate growth/progression arrays use `Power, Stamina, Speed, Hit, Evade, Magic, Magic Defense`. | `mixed`. It is a useful future record-window and field-family lead only after the compatibility block is completely relocated; use the current `$50` schema, not the forum's widths/labels. Initialization, menu, battle, save/load, event, and reset consumers still need adapters. |
| Mauron moved character/Tech data to expanded-ROM addresses and moved live Tech state to `$7E2880`, reporting incomplete testing ([2008 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg87876#msg87876)). | Relocation is the correct class of solution, but those addresses belong to that historical composite. Project Epoch still has unclosed ownership and lifecycle gates for its candidate `$7E2CA0-$7E2CEF` compatibility destination and uses named ExHiROM allocations rather than inherited free-space locations. | `patch-specific`. Preserve the architectural lesson, not the addresses or bytes. |
| Vehek mapped an all-zero candidate stat-growth row at file `$0C262B`, while a later post called `$0C25C2` an eighth HP-growth row ([stat row](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg115110#msg115110), [HP claim](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg115635#msg115635)). | The first claim is exact: `$CC:25FA` has eight seven-byte stat rows and row 7 is `$CC:262B-$2631`, all zero. The second is wrong: `$CC:25C2` begins the seven-row MP table. HP row 7 aliases MP data; MP row 7 aliases stat data. | `mixed`. The zero stat row is a genuine lead but is not a finished definition; it supplies no eighth HP, MP, TP, record, or persistence row. |
| Later posts recognized that MP growth collided with stat growth and that the eighth row could not be obtained by simply walking the existing tables ([2015 progress report](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg220398#msg220398)). | HP and MP each have exactly seven rows. Stat growth has eight rows, but row 7 is all zero and is not a complete Schala definition; TP-to-next also has seven rows. The attract/demo initializer additionally loops eight destinations while reading only seven HP/MP rows. | `confirmed boundary`. All initialization and growth families need explicit PC `$07` adapters and authored data. |
| Mauron and Vehek identified seven-character loop bounds in HP/MP restoration and menu-stat recomputation around `$C2:8D14/$C2:8D5A` and `$C2:99C3` ([restoration bounds](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg115857#msg115857), [menu bound](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg115866#msg115866)). | The canonical instruction preimages and seven-character bounds are real. Merely extending them in vanilla would process compatibility bytes as a record and cross other seven-entry tables. | `confirmed boundary`. Retain as adapter/test breakpoints only after a real record, relocation, and every dependent table are ready. |
| Mauron identified file `$3FFA7B-$3FFAA2` as eight five-byte save-copy descriptors ([2008 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg90100#msg90100)). | Current reconstruction independently confirms the descriptor table at `$FF:FA7B`, exactly eight × five bytes (`$28` total), with loader code immediately following. | `confirmed boundary`. This is a genuinely correct map, but the table cannot be extended in place; Project Epoch's translated layout and sidecar must preserve its existing regions. |

### Graphics, assembly, animation, portraits, and menus

| Historical claim | Current verification | Verdict and safe use |
| --- | --- | --- |
| Justin identified file `$242000` and `$242300` as graphics and sprite-assembly pointer roots, then made raw ID `$07` borrow Ayla data ([2007 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg71405#msg71405)). | The roots are correct: `$E4:2000` and `$E4:2300` contain full 24-bit pointers. There are only seven PC entries. Index `$07` reaches the first occupied NPC graphics pointer and occupied NPC assembly data. | `confirmed boundary`, `rejected` ownership. Keep the roots as resolver hook leads; never overwrite entries `$07/$08`. |
| Vehek showed that raw field PC `$07` could be made to look coherent by altering the first NPC sprite descriptor at file `$24F023`, then later appended pointers in regions labeled unused and redirected NPC users away from index `$07` ([descriptor post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg71625#msg71625), [adapter post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg72661#msg72661)). A later post explicitly says the normal occupant was Melchior and had been moved elsewhere ([2009 explanation](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg152748#msg152748)). | `$E4:F023` is exactly the first occupied five-byte NPC descriptor. The graphics pointer root is the complete 256×3 `$E4:2000-$22FF` table, so `$E4:22E8-$22FF` is indexed table storage even if some entries look empty. The assembly tail likewise lacks ownership/free-space proof. Current audits also show ID `$07` colliding with NPC/vehicle/sentinel data in assembly, animation, auxiliary-animation, and palette families. | `confirmed collision`, but the historical fix is a global source-index substitution that displaced Melchior, not a free slot. It is a useful negative control for field/NPC regressions. |
| In Project Schala debugging, Justin placed a proposed assembly pointer at file `$2425B5` but called its index `$E8`; Vehek corrected it to `$E7` ([proposal](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129196#msg129196), [correction](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129253#msg129253)). | The arithmetic is correct: `$242300-$2425B4` contains 231 three-byte entries, indices `$00-$E6`, so `$2425B5` is index `$E7`. That does not prove the zero-looking tail is allocatable or that any canonical consumer safely accepts the added entry. | `confirmed arithmetic`, `rejected allocation`. Useful as a reminder to separate index math from ownership proof. |
| Justin found that the apparent eighth animation boundary around file `$24260E` interfered with Magus/NPC data ([2007 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg73196#msg73196)). | `$E4:2600` is a boundary table. The word after the seventh PC start is the Magus-end/NPC-start sentinel required to derive Magus's animation extent; it is not an eighth start record. Auxiliary animation index `$07` is occupied too. | `confirmed boundary`. A Schala animation package must be relocated and resolved; it cannot be appended over the sentinel. |
| Vehek later mapped animation entrypoint selection as selector × 4 in the auxiliary stream, with zero participating in stop/reset behavior ([2009 post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg130904#msg130904)). | Current animation audits independently confirm a four-byte entrypoint-pointer stride for primary and auxiliary selectors. Zero's behavior is consumer-specific; four bytes is not a fixed animation-record length and zero is not a universal terminator rule. | `confirmed bounded format lead`. Retain the stride, not the generalized zero/record interpretation. |
| JLukas pointed to file `$3FCE70-$3FCE77` for portrait indexing and the palette pointers that follow ([2007 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg72784#msg72784)); Mauron later described expanding/moving this data for an eighth character ([2016 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg224177#msg224177)). | Eight physical bytes precede `$FF:CE78`, and raw ID `$07` can reach the eighth, but only seven full `$480`-byte faces exist and current evidence does not grant the eighth byte/palette path as a playable Schala row. In the full-status route ID7 aliases existing face data; the separate name-entry pseudo-ID7 route deliberately selects Epoch. Save preview is another independent `$200`-byte path. | `mixed`. The posts correctly found a menu boundary and the need to relocate/expand it, but their moved address is not Project Epoch allocation authority and does not solve all portrait paths. |
| Justin mapped `$C2:A2C6-$C2:A2CC` as seven character type/element-icon selectors and warned that changing `$C2:A2CD` crashed the menu ([2007 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg72728#msg72728)). | Current source reconstruction confirms a seven-byte table ending exclusively at `$C2:A2CD`; `$C2:A2CD` is the first instruction of `Menu_RebuildCharListScreen`, not row 8. | `confirmed boundary`. Add a resolver at the consumer; do not append a byte in place. |
| The 2009 Schala-as-PC8 diagnostic reported clean graphics/palette/assembly separation, but animation cloning remained open; a same-day post placed PC8 in Gaspar's party-exchange display area ([graphics report](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg150985#msg150985), [Gaspar collision](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg151078#msg151078)). | Current menu audit finds exactly seven `$40`-byte walking-sprite records at `$7E1800-$19BF`; the next records are active menu/caster/exchange scratch. Gaspar-area reuse therefore demonstrates a display-slot collision, not added capacity. | `confirmed negative control`. Do not use the Gaspar slot; virtualize a deliberate display record and preserve the party-exchange presenter. |
| Vehek documented custom bank-`$41` field-graphics loader code at file `$24F540-$24F5D3` during the Schala PC8 test ([2009 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg150938#msg150938)). | This is useful precedent that expanded-bank assets required custom reader logic. It does not cover the canonical non-flipped field decoder's bank assumptions or the battle/menu/animation/palette fixed-bank readers, and the canonical code gap is not an approved allocation. | `patch-specific` architectural lead. Independently implement bank-qualified readers in named expanded allocations; do not copy the old routine or site. |
| Later forum work said the “lag” occurred because added PC objects were ordered after NPCs, requiring per-location event-object rewrites. Mauron documented inserting ID7 objects after PC objects and adjusting object-target commands, including Drawing Status index = object number × 2 ([2016 diagnosis](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg224174#msg224174), [2018 loader rule](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg227149#msg227149), [rewrite notes](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg228406#msg228406), [index rule](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg228413#msg228413)). | Project Epoch's static event census proves canonical generic PC loaders use only operands `$00-$06`, but inter-object calls, jumps, fallthrough, startup order, and loader lifetime are not yet a closed runtime model. | `documented lead`, not yet promoted. Preserve it as an event-auditor and regression target, not an automatic global rewrite recipe. |

### Attacks, Techs, names, and party handling

| Historical claim | Current verification | Verdict and safe use |
| --- | --- | --- |
| Vehek made a generic LoadPC operand `$07` display on a field map, and Justin separately wrote `$07` into active slot 3 while observing the displaced PC move to reserve ([LoadPC test](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg71403#msg71403), [party-slot test](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg71444#msg71444)). | Event opcodes `$80/$81` and the roster machinery can transport the byte, and party operation 1 really can displace active slot 3. Downstream graphics, record, name, Tech, menu, battle, and persistence consumers remain seven-PC or occupied at index `$07`. | `confirmed transport`, not playable identity. This directly motivates the explicit open-slot helper and reserve-registration full-party branch. |
| Mauron initially treated `$CC:258A` as PC `$07`'s basic-Attack action byte; Vehek corrected it as the first HP-growth byte, after which Mauron identified the seven valid action IDs at `$CC:2583-$2589` ([initial claim](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg140227#msg140227), [correction](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg140229#msg140229), [seven-entry map](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg140273#msg140273)). | Current canonical audit confirms the seven-entry basic-action table and that direct ID `$07` falls through to `$CC:258A`, HP-growth data. | `confirmed correction`. The whole action-selector consumer needs an adapter; never append into the growth table. |
| Justin catalogued `$CD:400E` / file `$0D400E` as “8th Char's Attack byte” ([2008 post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg87946#msg87946)). | The table family consists of consecutive seven-entry normal/pathfind/critical selector tables. PC `$07` indexing into the second family falls through to `$CD:400E`, which is simultaneously Crono's runtime-confirmed critical selector in the third family. | `rejected`. Never patch it as an independent PC `$07` byte. Expand or intercept all three consumers. |
| The team observed that raw PC `$07` inherited the first eight dual Techs immediately following Magus's single-Tech rows, and later concluded new Tech data must be inserted between Magus singles and the dual-Tech families ([2008 discussion](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg87892#msg87892), [2016 conclusion](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg224194#msg224194)). | Current audits confirm seven single-Tech progress bytes/masks, fixed contiguous single/dual/triple data families, and no vanilla combo participant mask using PC `$07`'s bit. A naive extra combo row would collide with rock flags. | `confirmed boundary`. Use an expanded Schala Tech namespace and adapt every direct/signed/table consumer; never insert into the vanilla span without relocating the whole family. |
| Mauron found menu checks around `$C2:BD11/$C2:BD17` and later produced a separate visible Tech list with additional edits, explicitly noting incomplete single/dual coverage ([2008 lead](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg87904#msg87904), [2009 test](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg156833#msg156833)). | These are useful consumer leads, but a visible menu list does not prove targeting, properties, MP costs, learning, animation/effect selection, queues, battle execution, or persistence. Project Epoch's command and Tech-package audits keep those bindings separate. | `patch-specific` lead. Re-trace the consumers from canonical preimages; do not transplant the edits. |
| The thread proposed using or relocating the Epoch/name ranges for PC `$07`, including a modified-ROM name layout at `$7E2900`; Vehek later observed one modified ID7 name read from `$7E2CA3` ([relocation](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg89821#msg89821), [watchpoint observation](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg89836#msg89836)). | Vanilla name entry computes `$7E:2C23 + id*6`; ID `$07` targets the independently used Epoch name at `$7E:2C4D`, and dialogue PC-name pointer entry 7 is null. `$7E2900` is serialized vanilla state. The `$2CA3` access came from their modified layout, so it does not establish vanilla ownership, but it falls inside Project Epoch's still-unapproved `$2CA0-$2CEF` relocation candidate. | `rejected` storage plan, useful adversarial watchpoint. Preserve Epoch and keep the full candidate range canaried through installed name/menu/battle/save tests before allocation approval. |
| A 2009 experiment attempted an additional reserve slot by moving a battle-flags byte and listed many pointer edits while warning testing was incomplete ([experiment](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg153187#msg153187)). | The vanilla nine-entry roster can already hold three active characters plus five reserves and a terminator/empty representation. The real hazard is operation 1: with three active PCs it replaces active slot 3 and moves the displaced PC to reserve. | `rejected` as Project Epoch architecture. Preserve battle flags and implement an explicit capacity branch using reserve registration on the full-party path. |
| Mauron's 2018 rebuild separated generic eighth-character base work, Tech expansion, Schala-specific graphics/assembly, and six-letter names ([architecture post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg227860#msg227860)). | This separation matches Project Epoch's namespace doctrine and independent adapter families. The post does not publish source, allocation provenance, complete consumer coverage, or a reuse license. Later public test-patch history still contains a nonboot report. | `documented architectural guidance`. Retain the separation; independently implement and verify every component. |

## Project Schala claim ledger

| Historical claim | Current verification | Verdict and safe use |
| --- | --- | --- |
| Justin opened the project by saying Schala could not yet be PC8 and therefore had to replace an existing character ([opening post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118232#msg118232)); an [old RHDN discussion mirror](https://ximwix.net/mirrors/rhdn-old/index.php%40topic%3D4801.915.html#msg120438) independently describes the same replacement/future-coexistence split. | The surviving prototype video presents Schala through Magus's supported logical PC `$06` record, equipment, element, Tech list, save preview, menus, and dialogue-name route. | `replacement-only`, explicit first-party scope with independent contemporaneous corroboration. It is a PC `$06` consumer checklist, not PC `$07` evidence. |
| An experimental build imported only the `8thy` graphics, assembly, and pointer changes while trying to keep enemy/NPC Magus distinct ([2008 post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118460#msg118460)). | Graphics-source identity, playable logical ID, and enemy/NPC descriptors are separate namespaces. Keeping the enemy Magus sprite does not prove a second playable record, Tech set, name, persistence path, or roster slot. | `mixed`, experimental integration evidence only. |
| FaustWolf mapped Magus's unheadered-ROM graphics `$120000-$1272BF`, palette `$240090-$2400A7`, assembly `$1C0000-$1C27BF`, playable animation `$244B00-$244ECF`, and enemy animation `$249C80-$249D6F` ([2008 map](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118488#msg118488)); Vehek later corrected the assembly size to `$27B0` ([correction](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129890#msg129890)). | Current canonical audits independently confirm the graphics, 24-byte/twelve-character-color palette, and playable-animation ranges. The exact assembly extent is `$1C0000-$1C27AF` (end exclusive `$1C27B0`), so the original end was 16 bytes too late. The enemy-animation range has not been independently re-proved here. | `mixed`, with valuable replacement-source boundaries. Use the corrected ranges only for supported-slot comparison and canonical preimage checks; they do not add PC `$07` capacity or license payload reuse. |
| Magus's enemy palette was copied to an apparently empty expanded-ROM index and repointed, with an explicit note that the work would need to be redone when PC8 worked ([palette post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118492#msg118492)). | This is an enemy/palette replacement in that build's expansion map. Project Epoch's PC palette path has separate field, battle, menu, portrait, overworld, and 12-color-versus-16-color constraints; zero-looking expanded bytes are not allocations. | `patch-specific` and `replacement-only`. Useful only as evidence that enemy Magus preservation is an independent task. |
| Justin summarized a shifted prototype namespace as “8th = Epoch, Epoch = 9th empty slot” ([2009 post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg134556#msg134556)). | Logical PC `$07`, vanilla Epoch naming ID/path `$07`, graphics indices, party-exchange display records, roster positions, and save-editor empty `$80` are different namespaces. A prototype moving one pseudo-entry does not merge them. | `rejected` as an engine model. Preserve the namespace separation in every adapter and test. |
| Justin isolated a one-byte difference at expanded file `$40FFD5`; Vehek then observed a pointer intended for `$419080` reading `$019080` and diagnosed that the ROM was no longer recognized as expanded ([byte comparison](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129070#msg129070), [debugger observation](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129864#msg129864), [diagnosis](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129872#msg129872)). | File `$40FFD5` is the mirrored header's map-mode byte inside file `$40FFC0-$40FFFF`. `$35` is the required fast-ExHiROM value; the compared `$15` is not fast HiROM (`$31`) and did not preserve ExHiROM detection. Project Epoch validates both header copies, map mode, ROM size, checksums, source mirror, and fill invariants before any expanded allocation is accepted. | `confirmed historical debugger evidence` and negative control. Preserve the alias symptom as an ExHiROM header regression test; never allocate or casually edit this span. |
| Justin later described new Techs/items as future work limited by unfinished `8thy`, and explicitly said the current Project Schala replaced Magus and would have to be redone for coexistence ([scope post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg149860#msg149860), [replacement confirmation](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg156907#msg156907)). | The surviving video still shows Magus's Shadow element, equipment, all eight single Techs, and at least one Magus sprite role. Battle, recruitment, learning, New Game+, and coexistence are unproved. | `replacement-only`, with incomplete content conversion. Do not import it as Schala character data. |

## What Project Epoch should actually retain

The forum research materially strengthens five current decisions:

1. **Relocate complete ownership domains, not the convenient first bytes.**
   The same false eighth-record label survived long enough to create cascading
   Tech/save/growth bugs. Project Epoch's full `$50` compatibility relocation
   and sidecar lifecycle proof are necessary, not conservative excess.
2. **Resolve PC `$07` by context.** The old prototypes repeatedly made progress
   by moving the NPC, Gaspar, portrait, Epoch, or adjacent Tech data out of the
   way. Those are collision demonstrations. Project Epoch must preserve each
   existing owner and dispatch Schala to named expanded data.
3. **Expand whole adjacent families.** The attack and Tech discoveries correctly
   show why appending one byte/row aliases the next family. Consumers, signed
   checks, table bases, sentinels, and persistence must change together.
4. **Keep the 2018 component split.** Generic PC `$07` plumbing, Schala content,
   Tech expansion, and independent naming should remain separable build units
   with their own evidence and licenses.
5. **Use Project Schala only as a replacement-path comparison.** It identifies
   save-preview, field/menu sprite, portrait, label, party-exchange, element,
   equipment, and Tech-menu consumers. It cannot answer any natural-ID `$07`
   storage, coexistence, or capacity question.

## Explicit non-adoptions

This audit does not approve:

- any recovered or linked IPS as a source or production input;
- file `$0D400E` as Schala's attack selector;
- graphics, assembly, descriptor, animation, palette, portrait, or icon index
  `$07` as free;
- `$7E2830-$7E287F` as a live Schala record before the compatibility relocation
  and lifecycle matrix pass;
- Epoch's name field or null dialogue-name entry as Schala storage;
- Gaspar/menu scratch as an eighth persistent display record;
- the historical `$7E2880`, `$00F2F0`, expanded-bank, or 6 MiB locations as
  Project Epoch allocations;
- an event opcode accepting operand `$07` as downstream playable-PC validity;
- Project Schala's Magus-slot data, sprites, Techs, equipment, or palette as
  original Schala content; or
- a production patch, hook, or allocation.

## Next evidence gate

The forum ledger is now useful as a regression checklist. Before any production
PC `$07` activation, the remaining Project Epoch adapter/runtime matrix still
needs to close the natural record and relocated compatibility lifecycle,
field/battle/menu graphics and palettes, independent naming, portrait and save
preview, attacks, full Tech behavior/learning, equipment/items, capacity-safe
recruitment, normal save, all slots, erase, New Game+, reset, attract/demo, and
Epoch preservation. Historical success in one consumer does not waive another.
