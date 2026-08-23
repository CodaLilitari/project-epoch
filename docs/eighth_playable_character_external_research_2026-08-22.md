# Current public eighth-character research survey

Status: bounded Internet and public-source survey; no ROM or save mutation

Date inspected: 2026-08-22

Project target: a natural logical PC `$07`, currently designed as Schala

## Result

This survey did not find a published, reproducible SNES implementation of a
natural eighth playable-character slot. That is a bounded search result, not
proof that no private, unindexed, Discord-only, or abandoned implementation
exists.

The newest useful evidence divides into two categories:

1. Mauron's first-person progress reports confirm that an eighth character
   still required substantial assembly work in 2022 and that, by March 2024,
   data documentation and expansion notes were in good shape while the menu
   sprite problem and actual implementation remained open.
2. Current open-source Chrono Trigger tooling contains reusable techniques for
   repointing player-Tech animation scripts into arbitrary banks and expanding
   their pointer domain. It still models exactly seven playable identities and
   therefore is not an eighth-character implementation.

Project Epoch can use those findings as design and cross-check inputs. They do
not relax any production gate, assign a ROM/WRAM/SRAM range, or prove that a
vanilla table row belongs to PC `$07`.

## Evidence table

| Source | Pinned observation | Evidence grade | Safe use here |
| --- | --- | --- | --- |
| [Mauron, Chrono Compendium post, 2024-03-03](https://www.chronocompendium.com/Forums/index.php?topic=13512.msg236343#msg236343) | Reports that data documentation and expansion notes were largely ready, but the menu-sprite issue still needed experimentation and the work still had to be implemented. | `documented/reconnaissance`, first-person project status | Treat the menu walking-sprite/display path and data expansion as independent gates. Do not infer that a patch exists. |
| [Mauron, Chrono Compendium post, 2022-05-11](https://www.chronocompendium.com/Forums/index.php?topic=13742.msg234721#msg234721) | Describes a working eighth character as still needing a "fair amount of ASM work." | `documented/reconnaissance`, first-person project status | Confirms that a one-byte unlock or an unused sprite cannot be a sufficient architecture. |
| [Schala Edition discussion with Mauron's earlier implementation intent](https://gamefaqs.gamespot.com/boards/563538-chrono-trigger/78807721) | Mauron says an extra playable character is a major undertaking and states an intent to finish an eighth-character patch eventually for Schala Edition. The page does not provide a patch or source implementation. | `documented/reconnaissance`, historical first-person intent | Use only as chronology. Later 2024 status is the stronger implementation ceiling. |
| [The historical `8thy` project thread](https://www.chronocompendium.com/Forums/index.php?topic=4100.0) | Mauron posted an architecture split in [2018](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg227860#msg227860). A test IPS was linked in [May 2021](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg233559#msg233559) and relinked in [August 2021](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg233867#msg233867), followed by a [November 2021 report](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg234057#msg234057) that it did not boot correctly. Mauron reported in [February 2023](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg235738#msg235738) that progress continued slowly. No public source or reuse license was found. | `documented/reconnaissance`, binary/prototype history only | Preserve as provenance and test-case history. Do not download, redistribute, decompile, or import the unlicensed IPS as implementation source. |
| [Hi-Tech editor thread](https://www.chronocompendium.com/Forums/index.php?topic=10245.0) | Beta 12 began conditional support work in 2015; the first-party thread reaches [Beta 34 in 2025](https://www.chronocompendium.com/Forums/index.php?topic=10245.msg237285#msg237285), but its current changelog does not claim a natural PC `$07` implementation. No public source license was found. | `documented/reconnaissance`, editor capability only | Editor detection or compatibility for a hypothetical patch is not the patch, runtime architecture, or ownership proof. |
| [`Pseudoarc/ctrando` at inspected default-branch commit `20609d5`](https://github.com/Pseudoarc/ctrando/commit/20609d50932a84be58f6281d23b3f4e4d4c4e167) | Active public source inspected at an exact commit. Its [`CharID`](https://github.com/Pseudoarc/ctrando/blob/20609d50932a84be58f6281d23b3f4e4d4c4e167/src/ctrando/common/ctenums.py#L25-L34) enumerates Crono through Magus only. | `documented/reconnaissance`; seven-PC ceiling independently inspected | Cross-check seven-PC assumptions and locate adapters. It is evidence against calling the current project an eighth-slot solution. |
| [`apply_mauron_player_tech_patch`](https://github.com/Pseudoarc/ctrando/blob/20609d50932a84be58f6281d23b3f4e4d4c4e167/src/ctrando/base/basepatch.py#L266-L326) in the same repository | Pseudoarc's MIT-licensed Python host plumbing allocates separate local-root and bank tables for player-Tech animation packages. The embedded 65C816 routine is explicitly called Mauron's patch, but no separate Mauron license or source provenance was found; the first 128 root words are copied from the user's canonical ROM at runtime. | `documented/reconnaissance`, semantic design reference only | Independently reconstruct the bank-qualified package behavior. Do not copy the opaque routine, canonical resolver payload, allocator choice, or hook. Pin Project Epoch's own canonical preimages, named expanded allocations, complete-diff audit, and fail-closed write-intent guard before any installation. |
| [`OnemusCT/temporal-redux` at commit `d0becaf`](https://github.com/OnemusCT/temporal-redux/commit/d0becafe4ae58a5e159d5f84024df63698d1e5e2) | Active GPL-3.0 editor/remake inspected at its 2026-08-09 default-branch head. Its inherited [`CharID`](https://github.com/OnemusCT/temporal-redux/blob/d0becafe4ae58a5e159d5f84024df63698d1e5e2/sourcefiles/jetsoftime/ctenums.py#L24-L31) still enumerates exactly seven PCs. | `documented/reconnaissance`; seven-PC tooling | Continue using bounded parser comparisons only. It is not a natural eighth-slot implementation. |
| [`GitExl/CTViewer` at commit `2e5a206`](https://github.com/GitExl/CTViewer/commit/2e5a206e09f0028fd5a1ca6cb9a9ed18bfc64fea) | Current MIT-licensed viewer parses SNES/PC scene maps, actor sprites, and animation from script data. It is a viewer, not a PC `$07` implementation. | `documented/reconnaissance` | Use as an independent parser/visualization cross-check for event, actor, and animation boundaries; never as ownership proof. |
| [`dscotton/ct_disassembly` at commit `eeae27a`](https://github.com/dscotton/ct_disassembly/commit/eeae27acdb6565e96d1d796a3d60792c250c0aa1) | Current CC0-1.0 disassembly contains a hazardous [`CHAR_EIGHTH = $07` / "free slot" annotation](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/enums.asm#L638-L646), while its naming code separately records that slot 7 is Epoch and an eighth PC needs new storage. | `documented/reconnaissance`, internally qualified annotation | Use labels to find readers, never to infer a globally free ID, record, graphics row, name, or attack byte. Project Epoch's canonical evidence remains authoritative. |
| [`DocDamage/chronotrigger_disassembly` at commit `487a698`](https://github.com/DocDamage/chronotrigger_disassembly/commit/487a698bc1fd25cd564853cffe03c26902b7bbeb) | MIT-licensed 2026 disassembly/pass notes; no natural PC `$07` implementation or claim was found. | `documented/reconnaissance` | Use as a second annotation/source-location lead, followed by canonical preimage and runtime verification. |
| [`nmrugg/chrono-editor` at commit `66cbee1`](https://github.com/nmrugg/chrono-editor/commit/66cbee13fe00fc46ca0aba56b61986adb3946618) | MIT-licensed sprite/editor tooling updated in 2026; no eighth-character architecture was found. | `documented/reconnaissance` | Potential independent compression/decompression cross-check for original Schala assets; never copy extracted game graphics or promote tool output without round-trip proof. |
| [`maci0/ct-recomp` at inspected commit `836da54`](https://github.com/maci0/ct-recomp/commit/836da543fddcb4166ba0fb62587d427352437c5f) | A newly active 2026 recompilation/decompilation effort. No PC `$07` claim or repository license was found, and its workflow is organized around a source ROM and extracted assets. | `documented/reconnaissance`, no reuse permission | Do not import it. Its architecture may be revisited for the separate standalone-engine project only after a license and clean game-data boundary exist. |
| [`Schala/KajarEngine`](https://github.com/Schala/KajarEngine) | GPL-3.0 standalone Rust/Bevy engine for user-supplied Steam data. Its contribution policy excludes game disassembly and modded assets. | `documented/reconnaissance`; different platform and architecture | Keep for the separately proposed standalone-engine project. It does not solve the SNES logical-PC `$07` work and should not receive Project Epoch disassembly-derived contributions. |
| [`julianxhokaxhiu/CTNx`](https://github.com/julianxhokaxhiu/CTNx) | GPL-3.0 mod platform for the native Steam release. | `documented/reconnaissance`; different executable | Potential future Windows-port research only. It is not a natural eighth SNES slot or an SNES patch source. |

## Technique accepted for further study

The immediately useful external lead is the arbitrary-bank player-Tech
animation design exposed by `ctrando`'s host plumbing. Project Epoch's current
static census already
proves this native route shape:

```text
route-specific input
    -> package/config selector
    -> bank-qualified descriptor root
    -> descriptor relations
    -> bank-qualified direct script entrypoints
```

An explicit bank table is therefore architecturally compatible with the need
to move Schala-owned scripts into named expanded allocations. The adoption
boundary is deliberately narrow:

- inspect the MIT-licensed host plumbing and the documented behavior while
  treating the attributed Mauron machine routine as unlicensed/unknown for
  reuse;
- derive Project Epoch source from independently reconstructed semantics, not
  from an opaque machine-code blob;
- pin every vanilla hook preimage and document every preserved instruction;
- use only source-controlled named expanded allocations;
- preserve all vanilla `$00-$06` routes byte-for-byte in behavior;
- keep player-command IDs, internal animation-config rows, package selectors,
  descriptor roots, and script entrypoints as separate namespaces;
- run the fail-closed intent and complete-diff audit before any same-size ROM
  mutation or patch emission; and
- require runtime replays for menu, field, battle, load, New Game+, and
  teardown paths before promotion.

No upstream machine patch, free-space choice, or payload was imported by this
survey.

The follow-up source comparison found two additional reasons not to use the
upstream serializer as a preservation oracle:

- its companion config relocation rewrites fixed producers for rows `$79`,
  `$7A`, and `$7F`, but no corresponding source rewrite was found for the
  newly censused `$7B-$7D` producers; and
- its high-level reader reduces the two exact descriptor masks to role counts
  and writes fresh consecutive pointers, so sparse mask placement and shared
  pointer aliases are not necessarily preserved.

Those are coverage/search leads, not claims that the upstream project is
incorrect. Project Epoch retains its exact mask, alias, bank-qualified
identity, and fixed-producer ledgers as the stronger preservation boundary.

## What was not adopted

- The current `ctrando` seven-character enumeration is not extended by merely
  appending Schala. Project Epoch has already proved collisions in names,
  initialization, runtime compatibility state, graphics, Tech progress,
  attack selectors, menus, save data, and other consumers.
- Community labels such as "8th Char" remain search leads only. They do not
  establish namespace ownership; Project Epoch's canonical trace already
  disproved the apparent standalone eighth attack byte.
- Schala Edition's rescue/event content does not make Schala a natural eighth
  playable identity.
- Crimson Echoes material is useful for event and regression ideas, not as
  proof of an eighth saved/runtime record. No new public source tree found in
  this survey changed that assessment.
- NPC Schala/Gaspar sprites and fan sprite sheets are not automatically
  reusable art or complete playable packets. Project Epoch now permits one
  narrower exception: the user's canonical vanilla Schala NPC family may be
  reconstructed locally as an ignored, non-redistributable first-pass adapter
  diagnostic. Final distributable replacement art still requires original,
  provenance-backed frames. Crimson Echoes additions remain disabled unless
  their exact source and reuse permission can be proved.

## Search method and limitations

The survey used general web search, exact-phrase searches for Mauron's status
reports, GitHub repository and code search, GitHub repository metadata, and
exact default-branch source inspection. Technical conclusions above rely on
first-party project posts or repository source rather than secondary summaries.

Representative queries included:

- `Chrono Trigger eighth playable character SNES hack Mauron 2024`
- `site:chronocompendium.com/Forums eighth character Chrono Trigger Mauron`
- `site:github.com Chrono Trigger 8th character playable SNES`
- exact searches for `8th character`, `playable Schala`, `CharID`, and
  Mauron's arbitrary-bank player-Tech patch

The public web is incomplete. Search results can omit private repositories,
Discord messages, deleted downloads, unindexed forum pages, works in progress,
and source shared only person-to-person. The correct conclusion is therefore
"no complete public implementation found in this bounded 2026-08-22 survey,"
not "none exists." A historical test IPS proves only that a binary prototype
was circulated; it does not prove correct operation, source availability,
licensing, or compatibility with Project Epoch's preservation invariants.

## Project decision

Continue the evidence-gated natural-PC `$07` architecture. Add the pinned
`ctrando` animation-bank technique to the research queue as a licensed design
reference, and use current CTViewer only as an independent parsing/visual QA
cross-check. Neither source enters the trusted production hook or allocation
catalog until its relevant behavior is independently reconstructed and proved.
