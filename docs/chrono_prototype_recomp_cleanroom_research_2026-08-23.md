# Chrono Trigger prototype, recompilation, and clean-room research

Status: public-source and repository-metadata audit; no prototype ROM, patched
ROM, save, state, extracted game asset, proprietary source, or private
communication committed

Date: 2026-08-23

Target: evidence that can narrow Project Epoch's natural playable PC `$07`
work without weakening its default-deny ROM ownership rules

## Executive result

Several relevant historical and modern artifacts **do** exist:

- a dumped November 17, 1994 SNES sample/prerelease build;
- a dumped May 19, 2001 PlayStation review build;
- documented leaked Crimson Echoes alpha and late-beta builds;
- a privately exchanged December 2008 Project Schala diagnostic IPS;
- public partial disassemblies, editors, parsers, and content patches; and
- a new August 2026 repository that claims a byte-identical C reconstruction
  of the US SNES ROM.

No verified public evidence was found for:

- an official Square or Square Enix Chrono Trigger source tree;
- an official Chrono Trigger development-tool archive;
- a public dump of the earlier V-Jump alpha;
- a public Nintendo DS prototype/debug dump;
- a complete DS-gameplay-to-SNES backport; or
- a complete additive eighth-PC patch that predates Project Epoch and retains
  every vanilla playable character.

The new full-reconstruction claim is
[`maci0/ct-recomp`](https://github.com/maci0/ct-recomp), created August 16,
2026. A private ignored checkout was pinned at
`0b293606f562552c847e1170125b28dcf1c99963`. Its Git object graph passed
`git fsck --full`; the checkout was clean; it contained 7,981 tracked paths
and no tracked `rom/` path or SNES ROM-image extension. It nevertheless tracks
extensive extracted dialogue, graphics-related, palette, table, binary, and
audio material. No project-level license was detected. It is therefore a
quarantined community reconstruction, **not** recovered Square source, a
licensed code donor, or a production mapping authority.

The highest-value new low-contamination evidence is instead first-person
material deliberately published in 2026 by original Chrono Trigger staff.
Those accounts describe the development hosts, tools, and authoring workflow
at an interface level without supplying source or game payloads.

## Method and evidence limits

The search used:

- DuckDuckGo HTML/Lite queries in English and Japanese;
- GitHub repository search, repository metadata, public trees, READMEs, and
  exact remote HEADs;
- Hidden Palace preservation metadata;
- Chrono Compendium project and modification pages;
- first-person former-developer notes; and
- current Project Epoch canonical-ROM/disassembly evidence for bounded
  collision checks.

Search-result snippets were treated only as leads. A claim was retained only
when a direct project, author, forum, catalog, or repository surface supported
it. One automated TCRF prototype fetch served LLM-targeted prompt-injection
text; it was ignored. No technical conclusion in this audit depends on that
response.

Evidence language follows the repository doctrine:

- `verified-static`: directly reproduced from pinned repository metadata,
  public source, or current canonical-ROM evidence;
- `documented`: supported by a direct public author, project, forum, or
  preservation source but not independently reconstructed here;
- `hypothesis`: a lead that still needs a canonical static or runtime test;
- `bounded negative`: not found in the stated survey, without claiming global
  nonexistence; and
- `quarantined`: known to contain or depend on proprietary/extracted payloads
  and forbidden as a Project Epoch production input.

## Artifact existence ledger

| Artifact | Result | Evidence and boundary |
| --- | --- | --- |
| November 17, 1994 SNES sample/prerelease | Exists; `documented` public dump metadata | [Hidden Palace](https://hiddenpalace.org/Chrono_Trigger_%28Nov_17%2C_1994_prototype%29), [Chrono Compendium](https://www.chronocompendium.com/Term/Chrono_Trigger_Prerelease.html), and [sample-cartridge metadata](https://superfamicom.org/info/chrono-trigger-sample) identify the later Japanese sample build. It is a proprietary binary, not source or a tool archive. |
| Earlier V-Jump alpha | Existed as demonstrated software; recovered public dump not verified | [Translated contemporary/developer material](https://shmuplations.com/chronotrigger/) and [prerelease coverage](https://www.chronocompendium.com/Term/Chrono_Trigger_Prerelease_Coverage.html) support the earlier build's existence. No independently catalogued dump or hash was found. Do not conflate it with the November sample. |
| Functional eighth PC in the SNES prerelease | Not established; `bounded negative` | Public prerelease documentation describes incomplete remnants and undefined-data experiments, not a complete Gaspar or Schala PC. No extra complete playable animation/record/Tech/save implementation was identified. Prototype remnants are trace questions, never production definitions. |
| May 19, 2001 PlayStation review build | Exists; `documented` public dump metadata | [Hidden Palace](https://hiddenpalace.org/Final_Fantasy_Chronicles%3A_Chrono_Trigger_%28May_19%2C_2001_prototype%29) records a CD-R marked “Reviewable,” a build three days before final, and its preservation history. It is not a debug source tree and has little direct bearing on SNES PC `$07`. |
| Nintendo DS show/demo build | Existed at E3/Leipzig; public dump not verified | Contemporary [GameSpot](https://www.gamespot.com/articles/e3-2008-chrono-trigger-ds-hands-on/1100-6194298/) and [Pocket Gamer](https://www.pocketgamer.com/chrono-trigger/gc-2008-hands-on-with-chrono-trigger-ds/) hands-on coverage supports playable prerelease software. No reliable dump catalog, hash, kiosk image, or debug build was found. |
| Official Square CT source or CT-specific tool archive | Not found; `bounded negative` | No credible official tree was found for SNES, PS1, DS, mobile, or Steam. Surveyed Nintendo Gigaleak inventories produced no Chrono Trigger entry. Fan disassembly and reconstruction must not be relabeled official source. |
| Crimson Echoes leaked builds | Exist; `documented` | The [contemporary project thread](https://www.chronocompendium.com/Forums/index.php?topic=5639.0) and an [independent scholarly history](https://spectrum.library.concordia.ca/id/eprint/986367/13/Iantorno_MA_F2019.pdf) document an early alpha and later beta/release-candidate family. The later build is reported playable end-to-end. No sanctioned final release or separately verified source/Temporal Flux project tree was found. |
| December 2008 Project Schala diagnostic IPS | Existed; privately confirmed by contemporaneous posts | [Vehek requested it](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129837#msg129837), [Justin said he sent it by PM](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129838#msg129838), and the same-day [runtime-bank](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129864#msg129864) and [ExHiROM](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129872#msg129872) diagnoses prove subsequent use. It was a Magus-replacement diagnostic, not additive PC `$07`; no public copy/hash is verified. |
| Complete additive eighth-PC patch before Epoch | Not found; `bounded negative` | Historical work demonstrates graphics/menu experiments, replacements, and incomplete natural-ID attempts. None proves a complete new record, independent naming, field/battle identity, Tech/growth/save support, and coexistence with all seven vanilla PCs. |
| Full DS gameplay backport to SNES | Not found; `bounded negative` | No source-backed port of Lost Sanctum, Dimensional Vortex, Arena of Ages, Dream Devourer, or the DS item/enemy systems was found. Script, graphics, or music adaptations are not engine ports. |

## Authentic 2026 developer material

### Oki_Takana development memos

Oki_Takana's intentionally public
[development memo 1](https://note.com/oki_takana/n/n2a274c1cb250?hl=en) and
[development memo 3](https://note.com/oki_takana/n/n909f27bc7915?hl=en)
describe, at an interface/process level:

- an approximately two-year development;
- an initial 24-Mbit target that expanded to 32 Mbit;
- PC-98 development hosts;
- IS-Character SFC, IS-Sound, and IS-Debugger hardware/tools;
- proprietary hexadecimal-oriented event/scenario tooling; and
- hexadecimal character/effect animation sequences with numeric coordinates
  in a vertically oriented sequencer.

These statements strengthen Project Epoch's current model of variable,
command-like animation streams. They specifically argue against treating a
four-byte entrypoint stride as a four-byte fixed record or a zero value as a
universal terminator. They publish no formats, source, addresses, tool
binaries, or reusable graphics.

### Keizo Kokubo assembler statement

[Keizo Kokubo's retrospective](https://note.com/holy_sloth7171/n/nf00145930b15?hl=en)
states that he wrote a 65816 assembler used on Final Fantasy V and Chrono
Trigger. A [staff-credit transcription](https://hakuteikoubou.skr.jp/storage/staff/1990_SFC/CT.html)
independently corroborates his main-programmer credit.

This proves an internal assembler existed. No public binary, source, manual,
format specification, or reuse license for it was found.

## Modern reconstruction and disassembly projects

### `maci0/ct-recomp`

Public identity checked on 2026-08-23:

- repository: [`maci0/ct-recomp`](https://github.com/maci0/ct-recomp);
- created: 2026-08-16;
- pinned acquisition:
  [`0b293606f562552c847e1170125b28dcf1c99963`](https://github.com/maci0/ct-recomp/tree/0b293606f562552c847e1170125b28dcf1c99963);
- upstream description: a byte-identical decompilation and asset rebuild;
- project-level license: none detected;
- tracked paths: 7,981 at the pinned commit;
- Git integrity: `git fsck --full` passed locally;
- tracked ROM image: none observed; and
- tracked extracted game content: extensive.

Classification: `quarantined`.

The repository's existence and its own claims are verified. Its provenance,
semantic correctness, independent authorship, and byte-identical build claim
have not been independently reproduced. The absence of a ROM image does not
make tracked extracted dialogue, audio, graphics, palettes, and binary tables
clean or licensed.

Rules:

1. Never copy source, generated C, labels, addresses, assets, data tables, or
   test vectors from this repository into Project Epoch.
2. Never use it to populate the production hook or allocation catalogs.
3. Never publish its extracted payloads, a rebuilt ROM, or derivatives through
   the Epoch repository.
4. If its byte-identity claim is evaluated later, perform that work only in
   ignored quarantine and report neutral pass/fail metadata and hashes.
5. Re-derive every potentially useful interface fact independently from the
   pinned clean US Rev0 ROM before it can affect implementation.

### `ThisIsAkill/ChronoRET`

[`ThisIsAkill/ChronoRET`](https://github.com/ThisIsAkill/ChronoRET), exact
remote HEAD
[`ff6a5819f83ca88c382c1d3a0dacb36f3dd7a3a6`](https://github.com/ThisIsAkill/ChronoRET/tree/ff6a5819f83ca88c382c1d3a0dacb36f3dd7a3a6),
is a small tools-only
matching-disassembly project. Its public README reports 16,460 matched bytes,
about 4.6% of executable code, across selected banks and describes a workflow
that requires the user's own ROM. Its public tree is compact and does not
bundle a ROM.

Classification: `documented/specification-only`. No project-level license was
detected, so its implementation cannot be copied. Its progress claims and
labels remain hypotheses until independently checked.

### Licensed and bounded public tools

| Project | Pinned/current identity | License | Safe immediate use |
| --- | --- | --- | --- |
| [dscotton/ct_disassembly](https://github.com/dscotton/ct_disassembly) | Project Epoch pin `eeae27acdb6565e96d1d796a3d60792c250c0aa1` | CC0-1.0 | Search/control-flow index; rederive every label and table boundary. |
| [DocDamage/chronotrigger_disassembly](https://github.com/DocDamage/chronotrigger_disassembly) | Remote HEAD `487a698bc1fd25cd564853cffe03c26902b7bbeb` | MIT | Independent second disassembly/map oracle; not PC `$07` or free-space proof. |
| [Chronotools](https://bisqwit.iki.fi/source/chronotools.html) | Version 1.15.9, 2026-08-12 | GPL | Differential compression, relocation, checksum, cross-reference, and event parsing. Do not adopt its generic allocation policy. |
| [CTViewer](https://github.com/GitExl/CTViewer) | Remote HEAD `2e5a206e09f0028fd5a1ca6cb9a9ed18bfc64fea` | MIT | Independent scene/sprite/animation parser and visual QA oracle. |
| [chrono-editor](https://github.com/nmrugg/chrono-editor) | Remote HEAD `66cbee13fe00fc46ca0aba56b61986adb3946618` | MIT | Compression and sprite-packet differential round trips. |
| [Temporal Redux](https://github.com/OnemusCT/temporal-redux) | Pin per owning Epoch audit | GPL-3.0 | Event parser/command comparison; known incomplete behavior and generic allocation remain unsafe. |
| [Jets of Time / `ctrando`](https://github.com/Pseudoarc/ctrando) | Pin per owning Epoch audit | MIT overall | Host parsing and deterministic transform comparison; separately attributed opaque assembly is not automatically MIT. |
| [KajarEngine](https://github.com/Schala/KajarEngine) | Remote HEAD `c8d4f07541cec8277d7d9feba8617d3541655a2e` | GPL-3.0 | Future standalone-engine design using user-supplied data; not SNES source or PC `$07`. |

### False and unrelated leads

- [`joshuazhang447/chrono-trigger-native-port`](https://github.com/joshuazhang447/chrono-trigger-native-port)
  is a mislabeled repository. Its public README and tree describe a Max Payne
  Mobile Switch wrapper. It contains no demonstrated Chrono Trigger port.
- [`buzzer-re/Chrono-Trigger-C`](https://github.com/buzzer-re/Chrono-Trigger-C)
  is an archived SDL2 reference remake, not a matching decompilation or
  complete standalone engine. It has no detected project-level license.
- `ct_nx`, CTNx, and CTExt wrap or modify user-supplied official mobile/Steam
  binaries. They are not standalone Chrono Trigger engines and do not map
  SNES PC `$07`.
- The Nintendo Gigaleak proves that unrelated Nintendo development material
  leaked; it does not establish a Square Chrono Trigger source archive.

## DS, save, and content-port findings

### Partial backports that exist

The Chrono Compendium's
[modification catalog](https://pki.chronocompendium.com/Term/Modifications_%28Chrono_Trigger%29.html)
documents:

- **Chrono Trigger Soundtrack Expansion**, which recreates PS1/DS and
  prerelease music for the SNES sound engine and offers a data-only hacker
  variant; and
- **Chrono Trigger Complete**, which adapts DS-era script material while
  explicitly not adding DS gameplay content.

These projects can identify music-engine or text-capacity questions. They do
not identify free space in `vanilla.snes`, transport DS engine code, or prove
eighth-PC capacity.

### DS save tooling

[`turtle-insect/ChronoTrigger`](https://github.com/turtle-insect/ChronoTrigger),
remote HEAD `c8330043ff458b2722a545db6d705729c5d86aaa`, is GPL-licensed DS save-editor
source. Its public model describes exactly seven character records, three
party bytes, `$80` as empty, and the airship name separately. This is useful
documented namespace corroboration:

- seven serialized playable-character records do not imply an eighth PC;
- `$80` is an empty party value, not playable identity `$07`; and
- the vehicle name is a separate consumer from playable names.

It is not proof that the SNES and DS runtime serializers are identical.

[`Whivel/ChronoDSTranslator`](https://github.com/Whivel/ChronoDSTranslator),
remote HEAD `bc0038f83df4b7ac6e58257f095da48df8096d18`, is labelled GPL but includes
ILSpy-decompiled material of unclear original provenance. Its apparent
NitroFS message/pointer-table behavior is a format hypothesis only. Its weak
magic/bounds handling and user-selected insertion space make it unsuitable as
an Epoch implementation source or allocator.

## A verified fan-patch collision example

The public [Chrono Trigger MSU-1 project](https://github.com/qwertymodo/ChronoTrigger-MSU1)
is a legitimate music hack, but another patch's working locations are not
Project Epoch free space.

Its documented/assembled write sites include SNES/file locations corresponding
to `$C5:F370`, `$C3:257B`, and `$FA:96B1`. Current pinned disassembly evidence
places:

- `$C5:F370` inside compressed `OverworldTiles_0000`;
- `$C3:257B` inside occupied opaque bank `$C3` data; and
- `$FA:96B1` inside occupied whole-bank opaque data.

The example is intentionally adversarial: a mature patch can function while
owning collisions or assumptions that are unacceptable for another project.
No patch-specific location may populate Epoch's empty trusted allocation
catalog.

## Project Schala thread findings that remain useful

The complete 52-page Project Schala thread confirms a substantial
Schala-over-Magus prototype and a later plan to redo it around a genuine
eighth-PC framework. It does not reveal a completed hidden PC `$07` build.

Useful independently checked facts include:

- Magus graphics `$120000-$1272BF`;
- palette `$240090-$2400A7`;
- exact sprite-assembly half-open range `$1C0000-$1C27B0`;
- playable animation `$244B00-$244ECF`;
- ExHiROM map byte `$40FFD5=$35` in a correctly recognized historical build;
- animation entrypoint selector multiplied by four, without proving fixed
  four-byte records;
- 15 visible portrait colors plus transparency;
- full status portrait and small save portrait as separate consumers; and
- relocation of complete related Tech families as the correct solution class,
  while historical banks `$5E/$5F` remain patch-specific and unsafe.

New `hypothesis` for the remaining item-adapter census:

- Justin labelled `$3FB310-$3FB4F3` as data or pointers that classify items,
  weapons, armor, and accessories in
  [this December 2008 post](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg125813#msg125813).

That range must be independently decoded against the pinned clean ROM before
it can affect Schala item IDs `$E8-$EE`.

## Why another version cannot donate “free space”

A prototype, PS1/DS build, decompilation, or fan patch can differ from US SNES
Rev0 because of link order, localization, conditional compilation, table
movement, platform wrappers, or different asset packing. An absent or zero
range elsewhere proves nothing about ownership in `vanilla.snes`.

Before a canonical span could ever be considered unowned, Epoch would need:

1. no static inbound references;
2. no computed-table reachability;
3. no DMA, decompression, or indirect reads;
4. no runtime access across field, menu, battle, save/load, New Game+,
   attract/demo, reset, and ending paths;
5. an exact approved hook span and pinned preimage; and
6. a fail-closed complete-diff/write-intent result.

Production payloads still belong only in source-controlled named expanded
allocations. The trusted canonical-ROM hook and allocation catalogs remain
empty.

## Clean-room protocol for quarantined material

1. Record upstream URL, exact commit/build identity, acquisition date, size,
   integrity result, and license/provenance status.
2. Keep ROMs, patches, states, extracted assets, generated game data, and mixed
   reconstructions under ignored private quarantine.
3. Disable upstream pushing from quarantine checkouts.
4. Do not expose quarantined code/data to the production implementer as source,
   addresses, labels, or copied tests.
5. Convert only independently observable behavior into neutral questions or
   specifications.
6. Re-derive each game-specific fact from the pinned clean US Rev0 ROM with a
   reproducible scanner, exact arithmetic, reader/writer census, negative
   controls, and proportionate runtime evidence.
7. Compare against at least one independent, licensed public oracle when
   possible; agreement increases confidence but never proves unobserved
   consumers absent.
8. Write original implementation and tests. Any GPL incorporation requires an
   explicit project-wide licensing decision; unlicensed code is not copied.
9. Keep production hooks exact and allocations named; run
   `tools/validate_rom_write_intents.py` and the complete-diff audit before any
   same-size mutation or patch emission.
10. Publish only original source, specifications, hashes, reproduction steps,
    and evidence labels—never proprietary payloads.

## Immediate Project Epoch actions

1. Add `$3FB310-$3FB4F3` to the item-classification adapter census as an
   unverified lead and independently decode every consumer.
2. Use the Oki_Takana authoring description to strengthen variable-length
   animation-stream negative tests; do not infer a new format or terminator.
3. Pin and differential-test Chronotools 1.15.9 against Epoch's own
   compression/event parsers using the user's private clean ROM.
4. Add DocDamage's MIT disassembly as a second search index and record every
   disagreement with the pinned CC0 disassembly.
5. Keep `ct-recomp` quarantined. A later integrity/build audit may verify only
   its own public claim and return neutral hashes/pass-fail metadata; it cannot
   authorize source or data reuse.
6. Continue the existing runtime matrix for natural `$7E2830-$7E287F` PC `$07`
   and candidate compatibility relocation `$7E2CA0-$7E2CEF`; no prototype or
   reconstruction changes that evidence gate.

## User-facing link sheet

These pages identify the artifacts and tools without linking directly to ROM
payloads:

- [SNES prototype metadata](https://hiddenpalace.org/Chrono_Trigger_%28Nov_17%2C_1994_prototype%29)
- [Chrono Trigger prerelease encyclopedia](https://www.chronocompendium.com/Term/Chrono_Trigger_Prerelease.html)
- [PS1 review-build metadata](https://hiddenpalace.org/Final_Fantasy_Chronicles%3A_Chrono_Trigger_%28May_19%2C_2001_prototype%29)
- [Project Schala thread](https://www.chronocompendium.com/Forums/index.php?topic=6288.0)
- [Chrono Trigger modification catalog](https://pki.chronocompendium.com/Term/Modifications_%28Chrono_Trigger%29.html)
- [Oki_Takana development memo 1](https://note.com/oki_takana/n/n2a274c1cb250?hl=en)
- [Oki_Takana development memo 3](https://note.com/oki_takana/n/n909f27bc7915?hl=en)
- [Keizo Kokubo retrospective](https://note.com/holy_sloth7171/n/nf00145930b15?hl=en)
- [`maci0/ct-recomp`](https://github.com/maci0/ct-recomp)
- [`ThisIsAkill/ChronoRET`](https://github.com/ThisIsAkill/ChronoRET)
- [Chronotools](https://bisqwit.iki.fi/source/chronotools.html)
- [CC0 Chrono Trigger disassembly](https://github.com/dscotton/ct_disassembly)
- [MIT Chrono Trigger disassembly](https://github.com/DocDamage/chronotrigger_disassembly)
- [CTViewer](https://github.com/GitExl/CTViewer)
- [chrono-editor](https://github.com/nmrugg/chrono-editor)
- [KajarEngine](https://github.com/Schala/KajarEngine)

## Conclusion

The search did uncover a major new fan reconstruction and unusually valuable
first-person developer documentation. It did not uncover an official source
leak or a ready-made eighth-PC implementation. The new information reduces
blind reverse engineering—especially around variable animation streams,
historical toolchain expectations, competing parsers, and item-classification
questions—but it does not eliminate the subsystem-by-subsystem proof required
for natural PC `$07`.
