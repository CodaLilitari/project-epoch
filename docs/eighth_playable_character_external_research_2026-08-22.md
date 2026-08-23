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

## 2026-08-23 Schala-art provenance supplement

The follow-up provenance review did **not** establish a Crimson Echoes-owned
playable-Schala sprite packet or any exact Crimson Echoes frame suitable for
Project Epoch. No creator was contacted, and no community pixels were imported.

The public record is internally inconsistent about the historical project
relationship, so the more conservative attribution boundary applies:

- The Chrono Wiki retrospective says Schala had been scheduled to replace Ayla
  in Crimson Echoes, but that the playable plan was abandoned because adding a
  character was too difficult:
  <https://www.chronowiki.org/wiki/Crimson_Echoes%3ASchala>.
- A contemporaneous Chrono Compendium post by ZeaLitY lists Crimson Echoes and
  "the Schala project" as separate efforts:
  <https://www.chronocompendium.com/Forums/index.php?topic=6867.0>.
- Justin3009's 2008 video, "Chrono Trigger - Schala Project," describes only
  walking in four directions, idle faces, a sad pose, and a portrait. It says
  the portrait was modified from official anime art and then edited and
  colored again. The video does not identify a source file, pixel author,
  license, or non-vanilla frame:
  <https://www.youtube.com/watch?v=sFqtflPixrY>.
- Direct review of the live 92-second video shows field and menu
  demonstrations, but no battle, executed attack, executed Tech, or other
  additional playable-role animation. The preserved Chrono Wiki Project
  Schala JPEG is byte-exact
  with the video's current `hqdefault` thumbnail (13,946 bytes; SHA-256
  `5A0B9E580CB8270D027C6CD74692FE78DFF84009469AB03D2F6E69B8DDDAF834`).
  Its visible Schala pose agrees with the vanilla front/down idle pose. This is
  corroborative visual evidence, not a source-level proof for every video
  frame:
  <https://cdn.wikimg.net/en/chronowiki/images/e/ee/Schala_Project.jpg>.
- Justin3009's current `Project-Fonts` repository describes Schala Project as a
  community ROM hack in which Schala would replace Magus. It attributes the
  original font to Vivify93 and later font variants to several contributors;
  the repository contains fonts, not a licensed Schala gameplay sprite source:
  <https://github.com/justin3009/Project-Fonts>.
- The current third-party Crimson Echoes sprite inventory lists Glenn as its
  only playable-character sheet and no Schala sheet among its eleven entries.
  This is bounded negative corroboration, not proof that no private or omitted
  asset ever existed:
  <https://www.spriters-resource.com/snes/chronotriggercrimsonechoeshack/>.
- The Flames of Eternity RC-7D changelog says Schala and Magus were changed to
  hug in 65 million B.C. That proves changed event presentation, not a new
  Schala pixel or assembly record. The same public page still discusses
  playable Schala as unimplemented:
  <https://metronomeproject.blogspot.com/2014/11/rc-7d-unleashed.html>.

### Direct Project Schala prototype audit

The 2008 Project Schala video establishes a successful **partial presentation
replacement over Magus's supported logical PC `$06` slot**. It does not
establish a complete Schala character, a released patch, coexistence with
Magus, or natural PC `$07` support.

The primary-source video and its currently available author comments were
reviewed directly on 2026-08-23. The public video was decoded only in a
temporary local audit directory; neither it nor derived frames, comments, game
data, a ROM, a save, or an emulator state entered the repository. The audited
video-only stream was 92.084 seconds and had SHA-256
`3DD73036D46B848B8C142564BA5FA164B2B17C19F7D7FF54CB11401EC48E6DCA`.
The review produced this evidence matrix:

| Consumer or behavior | What the video establishes | Boundary exposed |
|---|---|---|
| Save select and Continue | The preview names Schala, displays her small purple field icon and HP/MP, and loads successfully. | This is Magus-slot presentation through the vanilla save path, not evidence for an eighth save record. |
| Party exchange and main menu | Schala occupies Magus's seventh roster position, can be selected and reordered, and supplies the menu walking sprite in several roles. | Magus cannot coexist as an independently selectable eighth PC. At about 0:11 and again near 1:12, Frog's separate sprite/stat row is also visibly labeled Schala; the exact cause is unproved, but name isolation is demonstrably incomplete. |
| Field graphics | Four-direction walking and several idle/emotive roles render as Schala. | An unconverted role near 1:13 visibly falls back to Magus, proving the role set is incomplete. |
| Name and dialogue | The speaker label is Schala. | The accompanying lines are Magus's existing party-exchange dialogue, consistent with dynamic PC-name substitution rather than authored Schala events. |
| Portrait and status | A custom blue-haired portrait and the Schala name render. | Element remains Shadow; level, EXP and stats are inherited; equipment remains DoomSickle, Aeon Helm, Gloom Cape and PrismSpecs. |
| Single-Tech menu | The menu opens and lists Lightning 2, Ice 2, Fire 2, Dark Bomb, Magic Wall, Dark Mist, Black Hole and Dark Matter. | These are Magus's eight single Techs. No cast, target, effect, MP deduction, damage, learning or battle animation is demonstrated. |
| Battle and recruitment | Nothing in the video proves these paths. | No normal/critical attack, damage/death/victory role, original weapon, original Tech, recruitment event, save/NG+ matrix or separate Magus is shown. |

Justin3009's own surviving comments agree with the visual boundary. The author
describes the contemporary build as a skin for the time being, says Schala was
temporarily replacing Magus, acknowledges that incomplete insertion allowed
Magus sprites to appear, and identifies graphics/assembly/animation editing as
the feasible part while Tech work remained difficult and unfinished. Other
comments describe planned weapons, element, Tech names, dialogue and event
coding in future tense, later identify the project as on hiatus, and discuss a
possible redo rather than a completed release. These comments are historical
project-status evidence, not a license grant.

The duplicate Schala label beside Frog is a useful warning rather than an
offset lead: a six-letter label can appear correct in one consumer while a
second PC is mislabeled in another. Without the historical patch or source,
the video cannot distinguish a serialized-name mutation, a menu buffer or
stride error, a dialogue-name adapter, or a recording-build-specific edit.
Project Epoch must continue to prove its independent live-name, menu,
dialogue, save and load adapters instead of reproducing the visible symptom.

No public Project Schala IPS, deterministic builder, gameplay source or
licensed sprite packet was found in the bounded search. The follow-up archive
and primary-thread hunt did prove two related facts without proving that the
artifacts were byte-identical. First, Justin3009
[privately sent Vehek a Project-Schala-era patch for debugging](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129838#msg129838)
on 2008-12-30, and Vehek immediately
[reported debugger observations](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129864#msg129864)
from it. Second, surviving videos demonstrate that the unreleased Project
Schala line later reached a substantially developed gameplay state, including
a rescue sequence, Dream Devourer work, and a dungeon preview. In direct
Project Schala context, forum participant Schala Zeal
[asked about posting her retained sprite sheet](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg221097#msg221097),
and Justin
[stated in March 2016 that he still held an incomplete copy and IPS](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg221099#msg221099).
The evidence does not establish that Vehek's 2008 patch or Justin's retained
IPS contained the later rescue/Dream Devourer state. No surviving public file
or source license was located. See
`docs/recovered_2008_eighth_character_prototype_audit_2026-08-23.md` for the
full chronology, source links, archive audit, and bounded-negative search.

A separate
[March 2009 `8thy` post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg150985#msg150985)
also documents Schala as the natural-eighth graphics test identity with
palette and sprite-assembly separation working. Animation cloning remained
open, and a
[same-day post says the eighth PC used Gaspar's party-exchange area](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg151078#msg151078).
This upgrades the historical record to a visible Schala-as-PC8 proof of
concept, not a complete eighth character or a safe Gaspar-preserving menu
architecture.

For Project Epoch, the unrecovered Schala prototype is therefore a useful
supported-slot comparison target. Its positive cases identify consumers that
can inherit an existing-PC path: player name, portrait, field/menu graphics,
save preview, Continue/load and party exchange. Its negative cases identify
independent families that a real character must replace: complete animation
roles, element, equipment, stats, Tech names/properties/costs/effects/learning,
attacks, dialogue/events and battle behavior. If an exact historical patch or
source is recovered, analyze it only in ignored private space: hash it,
produce a metadata-only complete write-span census, classify each write
against Project Epoch's table map, and run the ROM write-intent guard before
any same-size image or derived patch is emitted. Do not import or redistribute
its bytes without source and permission provenance.

Even a complete Magus-slot replacement would not resolve the natural-PC `$07`
problems: the eighth live record, save and Tech-progress storage, Epoch naming
collision, graphics-source collisions, high action/Tech namespaces,
eight-character roster/recruitment logic, or preservation of Magus as a
separate playable character.

These sources prove historical interest and a prototype presentation, not a
reusable art grant. They also do not prove that a displayed gameplay pose was
new rather than assembled from the vanilla NPC family. The derivative portrait
is excluded independently because Project Epoch does not need it and cannot
establish clean contributor ownership over the official-art base.

The contact search found only general Compendium/FoE support or development
mailboxes and Justin3009's public GitHub/Twitter route. None was proved to be a
current email for the author of an identified additional Schala frame or to
carry authority to license that frame. Guessing a recipient would therefore
weaken rather than repair provenance. No outreach was sent.

Artifact recovery is a separate question from art licensing. When inspected
on 2026-08-23, Justin3009's
[Chrono Compendium profile](https://www.chronocompendium.com/Forums/index.php?action=profile;u=806)
reported last activity on 2026-08-20, and
[Vehek's profile](https://www.chronocompendium.com/Forums/index.php?action=profile;u=1235)
reported activity on 2026-08-22. These time-sensitive observations identify
plausible contact routes, but do not establish consent, current possession, or
authority to license any asset. No recovery request was sent.

The resulting policy is asset-specific rather than project-wide:

1. Vanilla Schala data may continue to be reconstructed transiently from the
   user's pinned clean ROM for private compatibility testing. It is Square
   Enix material and is not represented as Crimson Echoes or Schala Project
   property.
2. No Crimson Echoes, Flames of Eternity, or Schala Project pixels enter the
   build merely because they resemble or lightly edit vanilla art.
3. If a future audit isolates a genuinely additional frame, its exact bytes or
   lossless source, revision, transformation history, pixel author, and current
   authorizing contact must be pinned before outreach.
4. Any request must cover only that contributor's identified original addition,
   must disclose Project Epoch's AI-assisted workflow, and must treat refusal
   or silence as no permission. A general project-team approval cannot grant
   rights over vanilla Chrono Trigger material or another contributor's work.
5. Until all of those conditions are met, the vanilla-only compatibility
   provider and independently authored replacement-art path remain sufficient;
   community art is neither a dependency nor a production input.
