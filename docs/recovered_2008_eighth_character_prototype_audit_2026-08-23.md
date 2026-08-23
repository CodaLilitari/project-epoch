# Recovered 2008 eighth-character prototypes and Project Schala build hunt

Status: read-only public-source and recovered-artifact audit

Date inspected: 2026-08-23

Evidence labels follow the Project Epoch vocabulary:

- `verified-static`: reproduced from an exact hashed local artifact recovered
  from the public Kajar attachment archive; and
- `documented`: stated by a named developer or tester in the cited primary
  forum/video record. Retrospective statements are identified by their
  statement date and are not treated as recovered-artifact verification.

`bounded negative` is used only as a scope qualifier: not found within the
named search surfaces, without claiming that a private or unindexed copy
cannot exist.

## Outcome

A substantially developed **Project Schala gameplay build was publicly
demonstrated**. A development patch was privately transferred during a
Project-Schala-era sprite-assembly debugging exchange, and Justin3009 later
reported retaining an incomplete Project Schala copy and IPS. No public
download of a Schala-specific build has yet been recovered.

The strongest chain is first-person and unusually direct:

1. Justin3009 reported integrating the contemporary eighth-character patch
   into the Project Schala ROM on 2008-11-23, initially to separate playable
   graphics from Magus's enemy/event representation. He later clarified that
   the actual project still replaced Magus rather than providing a completed
   natural eighth PC.
2. On 2008-12-28, Justin offered Vehek IPS patches of the generic
   eighth-character and variable-width-font projects. On 2008-12-30, while
   they were debugging Schala/Magus sprite assembly, Vehek asked to see “your
   patch” and Justin said he would send it privately. Forty-seven minutes
   later, Vehek reported observations from a ROM in Geiger's debugger and soon
   diagnosed that its expanded-ROM marker had been lost. The sequence strongly
   documents a private development transfer, but the surviving posts do not
   identify the transmitted filename, container, or precise relationship to
   either previously offered IPS.
3. By early 2009, the project thread described a rescue sequence, a working
   Dream Devourer map/event, and intended new Techs, dialogue, and items. The
   surviving creator videos independently show the rescue route, Dream
   Devourer battle work, and a later dungeon preview.
4. Justin announced a pause in the Magus-replacement line in April 2009 because
   conversion to a true eighth PC would require reworking the project.
   Surviving November-December 2009 videos show that development or preview
   work subsequently continued.
5. Most importantly for recovery, Justin stated on 2016-03-21 that he still
   had an incomplete copy and IPS from the earlier project. A
   [creator comment currently labeled 13 years ago](https://www.youtube.com/watch?v=IHtpTBGhRyM&lc=UgxKhQxHfqFnEi6_1XB4AaABAg)
   had said all progress was lost. The exact comment date is not exposed on the
   currently accessible surface, so it is only approximately 2013. The dated
   2016 first-person statement is the later and stronger possession evidence.

This is not recovered-artifact verification or proof that the file is still
held in 2026. It is `documented` first-person evidence that Justin still
possessed an incomplete Project Schala copy and IPS in March 2016. Separately,
Vehek was the apparent recipient of an unnamed December 2008 development
patch; the surviving posts do not establish that these were the same artifact.
Those two people are now the highest-probability recovery route.

Primary chronology:

- [Project Schala begins and cannot yet use a true eighth PC](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118232#msg118232)
- [Justin integrates the contemporary eighth-character patch](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118460#msg118460)
- [Playable/enemy Magus graphics separation and future-redo warning](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg118492#msg118492)
- [Justin offers IPS copies for debugging](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129070#msg129070)
- [Justin privately sends Vehek the patch](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129838#msg129838)
- [Vehek immediately reports debugger evidence](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129864#msg129864)
- [Vehek identifies the expansion/header failure](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg129872#msg129872)
- [Dream Devourer map/event progress](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg144154#msg144154)
- [Planned Tech, dialogue, and item work](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg149860#msg149860)
- [Project still replaces Magus and pauses for a true eighth PC](https://www.chronocompendium.com/Forums/index.php?topic=6288.msg156907#msg156907)
- [Justin reports retaining an incomplete copy and IPS in 2016](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg221099#msg221099)

Surviving creator videos:

- [initial field/menu presentation](https://www.youtube.com/watch?v=sFqtflPixrY)
- [Schala rescue sequence](https://www.youtube.com/watch?v=XGoS88HzKv0)
- [Dream Devourer AI test](https://www.youtube.com/watch?v=Udoj1lYoG8c)
- [side-quest development preview](https://www.youtube.com/watch?v=8fjFWMQjB-E)
- [final beta preview](https://www.youtube.com/watch?v=IHtpTBGhRyM)

An independent mirror of the old ROMhacking.net forum also preserves Justin's
contemporaneous explanation that the current
[Project Schala build replaced Magus](https://ximwix.net/mirrors/rhdn-old/index.php%40topic%3D4801.915.html#msg120438)
and that coexistence depended on the separate eighth-character work.

## Documented March 2009 Schala-as-PC8 graphics diagnostic

Schala graphics developed in the Project Schala context were used as the test
identity in a separate generic `8thy` diagnostic:

- On [2009-03-12](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg150985#msg150985),
  Justin reported Schala's graphics working in the eighth-character ROM without
  palette or sprite-assembly conflicts. He explicitly called it a proof of
  concept and selected Schala as the official test identity. Animation data
  still needed to be cloned and repaired.
- Later that day he reported that
  [the eighth character used Gaspar's party-exchange area](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg151078#msg151078),
  while Vehek's separate Gaspar experiment appeared only through a forced
  ninth-character condition.

This is `documented` evidence for a visible Schala-as-PC8 graphics diagnostic,
not a complete natural eighth PC. It does not prove independent runtime and
save records, attacks, Tech execution/learning, complete animation, stable
party exchange, recruitment, naming, load/New Game+, or coexistence with both
Magus and Gaspar. The two Tinypic proof screenshots linked from the post were
not preserved by the tested web archives.

The occupied Gaspar party-exchange display area is especially useful negative
evidence: Project Epoch must continue to give Schala an independent party/menu
route and must not consume that Gaspar display route as its architecture.

## Public Kajar attachment archive

The still-live public archive is:

<https://chronofan.com/Black/Other/Attachments/Kajar%20Laboratories.7z>

Retrieval identity:

| Property | Observation |
|---|---|
| HTTP status | `200` |
| Content type | `application/x-7z-compressed` |
| Size | `40,344,158` bytes |
| SHA-256 | `DC06EBD5CF5527B444F10B5E52C33D4499BDED6AEA1911402236E809A706A5B9` |
| Server `Last-Modified` | `Sun, 12 Jan 2014 11:02:46 GMT` |
| Archive entries | 601 file/directory entries |

The server date describes this preserved archive object, not the original
forum upload dates. Its internal file dates are mostly 2009 preservation
timestamps and likewise must not be promoted to authoring dates without
separate evidence.

The archive closes one important ambiguity:

- `Chrono_Trigger_-_Schala_Project` contains only Justin3009's screenshot.
- `Playable_character_mod__Schala` contains visual sprite experiments, not a
  ROM patch or source build.
- No Schala-named IPS, BPS, xdelta, ROM, source tree, or emulator state appears
  in the complete outer inventory.

The public bundle therefore contains no Schala-named IPS or gameplay build.
Because the December 2008 private exchange preserved neither a filename nor a
hash, the inventory cannot determine whether any generically named file is
identical to or descended from the privately exchanged patch. No screenshot or
sprite file is treated as a code build or reuse grant.

## Valuable recovered eighth-character family

The same archive did preserve a 2008 eighth-character prototype lineage. These
are not the Schala-specific gameplay build, but they are the closest surviving
related binaries, a documented precursor family, and direct technical context
for the private project.

All files remain unchanged under ignored `recovered/`; none is committed or
redistributed.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `Mauron_character8.ips` | 533 | `86D19470E0F41C06E87539286C5FAEAD223D5356CB6D959C66F7D8A436F2D76E` |
| `Vehek_Chrono Trigger-NPC Sprite Data mod.ips` | 173 | `2A7ABCA722CAEBD27812B9B8D8CD646CCC61AFD6F3669E285810DA2331F282E6` |
| `Vehek_Gato-8thchar.Flux` | 1,384 | `E7EA54278B182450F4FDDB72D2BE11AB6EB4BF3AB4BD14672EFA09DB4F8A16DD` |
| `justin3009_8th Char almost Playable.ips` | 97,754 | `EFAA1960278456028FB420612DA8415BB9CD78D506365A152DD4349185B044C5` |
| `justin3009_Chrono Trigger - 8th Character 6 Letters.ips` | 110,672 | `8468AA907860CBB235D3355B56944AACBB778AA3D8087B883E4B40905AB0C7C5` |
| `justin3009_Chrono Trigger - Fresh Rom (Unheader - 8th Character) - 10-15-2008.ips` | 110,709 | `08487A3BA9B7EF789129F92851B643C0B4193A5D892D8B36126323285A725401` |
| `justin3009_Chrono Trigger - Fresh Rom (Unheader - 8th Character).ips` | 109,411 | `771E17D5E6C51FA01FBDBA1012BEF61A3E9FF08DDB0449076D6921F6C405E7BC` |
| `magustrigger_chrono96.rar` | 99,998 | `11035B7A6EC69F771A8B2C19EBA11F76B2177B3C2248ED577E900CF4695AF639` |
| `magustrigger_epoch.rar` | 91,982 | `E382B0DF0B58C9F2707A1E994C42B684CE8DB22997D410E1AE9E108A7CDE3689` |

The Temporal Flux event export contains an author note identifying a `LoadPC`
operation for the eighth-character slot. It is useful event-command evidence,
not a complete PC implementation or production binding.

The two nested archives contain historical emulator states:

| State | Format evidence | Bytes | SHA-256 |
|---|---|---:|---|
| `chrono96.008` | gzip-wrapped `#!snes9x:0001`; uncompressed size 430,944 | 100,394 | `80F94A2A0C35D0365409DC5A6DF944EA6CFE2D1F5D59AE604D77FD8D35F41C8A` |
| `epoch.zs1` | `ZSNES Save State File V0.6` | 274,047 | `65DD2EF86C38C6A8774CF535D0850BF385580A9543E5E171F288FADDCAAAA95A` |

Their embedded/archive timestamps are 2008-02-17 and 2008-02-18, months
before Project Schala began. They belong to the general eighth-character
experiments and must not be described as Project Schala states.

## Payload-free metadata audit of recovered IPS files

`tools/audit_historical_ips_metadata.py` parses the IPS files read-only,
resolves record overlap in memory, compares writes with the pinned canonical
US Rev0 ROM, and emits only metadata. It has no output-file destination and
cannot emit a patched image or patch payload.

All six recovered IPS files have no truncate marker. The auditor parses that
optional classic-IPS field for input validation but rejects every
truncate-bearing patch: a deletion or size extension cannot be represented
truthfully by the address/value lineage and protected-range reports promised
here. Report provenance is therefore limited to caller-supplied read-only
input; the exact archive origin is established separately by the pinned hashes
and recovery record in this document.

The parser also enforces per-patch 8 MiB input and declared-write limits before
RLE expansion, plus a 65,536-record ceiling. A whole audit is limited to eight
patches and 16 MiB each of aggregate input, declared writes, and effective
writes. CLI path metadata is preflighted before any patch is read; each input
is then opened once, checked as a regular file through that handle, and read
with a hard `limit + 1` bound so a stat/read growth race cannot cause an
unbounded allocation. Effective writes use a compact value buffer, presence
bitset, and packed offset array rather than a per-byte Python dictionary.
Directed subset comparisons use one pass and are capped at 67,108,864 address
visits. The six-file recovered audit consumes 429,252 input bytes, 8,474,412
declared/effective writes, 30 directed relations, and 42,372,060 address
visits. Configured limits and actual totals are included in every JSON report.
The public multi-patch report accepts either no reference or the exact pinned
canonical ROM—arbitrary reference bytes remain confined to lower-level
synthetic tests. Each report binds its protected-range conclusions to the
current write-guard version, canonical source identity, and deterministic
SHA-256 identities of both policy catalogs.

“Effective bytes” below means distinct final write addresses after overlapping
IPS records are resolved. It includes both changed bytes and same-value writes;
for example, Mauron's 542 changed and 6 same-value addresses total 548
effective bytes.

| Patch | Records (of which RLE) | Canonical bytes changed | Same-value canonical writes | Expansion writes | Nonzero expansion writes | Projected size |
|---|---:|---:|---:|---:|---:|---:|
| Mauron component | 35 (10) | 542 | 6 | 0 | 0 | 4 MiB |
| Vehek NPC-sprite adapter | 17 (0) | 31 | 49 | 0 | 0 | 4 MiB |
| Justin `almost Playable` | 249 (120) | 13,185 | 638 | 2,097,152 | 68,088 | 6 MiB |
| Justin `8th Character 6 Letters` | 332 (127) | 22,202 | 1,650 | 2,097,152 | 70,529 | 6 MiB |
| Justin dated `10-15-2008` | 337 (129) | 22,970 | 1,779 | 2,097,152 | 70,541 | 6 MiB |
| Justin undated `Fresh Rom` | 312 (128) | 21,276 | 1,476 | 2,097,152 | 70,529 | 6 MiB |

The projected target hashes are reproducibility fingerprints under the tool's
explicit zero-fill IPS semantics. No target image was written:

| Patch | In-memory projected target SHA-256 |
|---|---|
| Mauron component | `E0A9F29A8E1E76693CAD4F32F5A6053B24BDEEC36A9865F8D120FE21615F3CD9` |
| Vehek NPC-sprite adapter | `BAED6ECB46615A57D5AA9F1D361C521A78940A3C3C7A4F9D9CFE14FC8D10176D` |
| Justin `almost Playable` | `91E79A0FEADEFCF90FF0E4B52CD74C4BCDB0B6E2C05C4F05ED97E994B469A65E` |
| Justin `8th Character 6 Letters` | `103B7465023F15BC4BDBC953C4E1CD765DE74542B00E8C9BC07FF7E5A787E02F` |
| Justin dated `10-15-2008` | `07F322BBC5A0172305C4597461F35671732D08F83E3547E9ABF9FAB8E382E226` |
| Justin undated `Fresh Rom` | `301C85C7C2084034518024B062E5314139C1C4EE0A00568F1DCBA2BFAD34A36C` |

### Proven lineage

The relationship is stronger than shared filenames or forum chronology:

- all 548 effective bytes written by `Mauron_character8.ips` are present at
  the same addresses with identical values in Justin's `almost Playable`
  patch; and
- all 80 effective bytes written by Vehek's NPC-sprite adapter are likewise a
  byte-identical subset of that same Justin patch.

The three later Justin variants still cover every Mauron and Vehek address,
but change 29-31 Mauron bytes and one Vehek byte. This proves a composite
lineage followed by revision. It does not establish a source license.

The original `8thy` thread also anchors the archive filenames to the 2008
development sequence:

- [`8th Char almost Playable`](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg87989#msg87989)
  corresponds to Justin's 2008-01-30 “almost” walking-graphics snapshot;
- the undated [`Fresh Rom (Unheader - 8th Character)`](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg89870#msg89870)
  belongs to the rolling February/March fresh-unheadered-ROM snapshot line,
  with a later [updated attachment post](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg90611#msg90611);
- [`8th Character 6 Letters`](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg113053#msg113053)
  is the 2008-09-15 combined eighth-character/six-letter package; and
- the dated [`10-15-2008` build](https://www.chronocompendium.com/Forums/index.php?topic=4100.msg114999#msg114999)
  follows Justin's report of a working eighth save portrait, with explicit
  warnings about broken End-of-Time text and the third save row.

These are generic `8thy` prototypes that the thread discusses as a base for
different possible characters. Their recovery does not make any of them the
missing Project Schala gameplay IPS.

### Negative-control value for Project Epoch

The historical family is invaluable partly because it records approaches that
Project Epoch has now independently proved unsafe:

- `almost Playable` and the undated `Fresh Rom` mutate file `$0D400E`.
  Project Epoch's canonical static/runtime audit proves that location is shared
  by logical PC `$07` normal-Attack indexing and Crono's critical selector. It
  is not a free eighth-character byte.
- All four large Justin composites write the occupied low graphics, assembly,
  and sprite-descriptor neighborhoods that Project Epoch now protects.
- The three six-letter/fresh variants touch the null PC-name entry `$07`
  adjacent to Epoch's separate naming path. A correct Schala implementation
  still needs an independent name adapter.
- All four composites expand to 6 MiB and write through the bank `$40`
  mirror/header area. This is historical ExHiROM experimentation, not an
  approved Project Epoch allocation architecture.
- Each composite changes 13,185-22,970 canonical bytes and writes the complete
  2 MiB extension. They are broad opaque prototypes, not production payloads.

The recovered files therefore serve as:

- a subsystem and chronology census;
- a binary lineage/provenance witness;
- a regression and negative-control catalog; and
- evidence that old “almost playable” success does not establish safe solutions
  for the natural PC `$07` persistence, naming, attack, graphics, menu, battle,
  and Epoch conflicts now known to Project Epoch.

They do **not** populate the trusted production hook or allocation catalogs.
No patched ROM image was written, and none is accepted as a production input
or applied to the user's canonical on-disk ROM.

## Search coverage and bounded negative result

No public Schala-specific patch was found in:

- the complete Chronofan Kajar attachment archive inventory;
- the surviving 52-page Project Schala thread and its two deleted attachments,
  which the posts identify as visual assets rather than builds;
- exact and alias searches for the project title, video IDs, creator handles,
  likely IPS names, and attachment names;
- Internet Archive metadata and tested Wayback captures of the project thread
  and legacy forum URL forms;
- the creator's current GitHub repositories and complete `Project-Fonts`
  object history;
- the inspected ROMhacking.net preservation corpus and Zophar's Chrono Trigger
  patch list;
- metadata-only central-directory scans of three Internet Archive SNES-hack
  collections totaling 1,597 indexed entries, plus a separate 183-entry Chrono
  Trigger collection;
- public GitLab and Codeberg repository-name searches for the title, creator
  aliases, and surviving video IDs; or
- the Project Schala YouTube descriptions and surviving public comments.

The absence is bounded. Private messages, deleted file-host links, personal
backups, unindexed archives, and community-admin attachment backups remain
outside that proof.

## Reproduction

The local recovered inputs and clean ROM remain ignored. Python 3.13.15 was
used for the verified run. On the verified Windows system, the launcher is not
on `PATH`; the task-specific variable below locates it without embedding a user
profile name. Readers with another Python installation may substitute their
own interpreter. From the repository root, the metadata audit can be
reproduced without writing a ROM:

```powershell
$epochPythonLauncher = Join-Path $env:LOCALAPPDATA `
  'Programs\Python\Launcher\py.exe'

& $epochPythonLauncher -3.13 tools/audit_historical_ips_metadata.py `
  --reference-rom 'private/input/rom_archive/Chrono Trigger (USA).sfc' `
  'recovered/kajar_laboratories_2014/Kajar Laboratories/8th_Playable_Character_Possible___-_Find_Out_Inside_/Mauron_character8.ips' `
  'recovered/kajar_laboratories_2014/Kajar Laboratories/8th_Playable_Character_Possible___-_Find_Out_Inside_/Vehek_Chrono Trigger-NPC Sprite Data mod.ips' `
  'recovered/kajar_laboratories_2014/Kajar Laboratories/8th_Playable_Character_Possible___(Updating_)/justin3009_8th Char almost Playable.ips' `
  'recovered/kajar_laboratories_2014/Kajar Laboratories/8th_Playable_Character_Possible___(Updating_)/justin3009_Chrono Trigger - 8th Character 6 Letters.ips' `
  'recovered/kajar_laboratories_2014/Kajar Laboratories/8th_Playable_Character_Possible___(Updating_)/justin3009_Chrono Trigger - Fresh Rom (Unheader - 8th Character) - 10-15-2008.ips' `
  'recovered/kajar_laboratories_2014/Kajar Laboratories/8th_Playable_Character_Possible___(Updating_)/justin3009_Chrono Trigger - Fresh Rom (Unheader - 8th Character).ips'
```

Focused verification:

```powershell
& $epochPythonLauncher -3.13 `
  -m unittest tests.test_historical_ips_metadata -v
```

Verification on 2026-08-23 passed all 9 focused tests and the complete 906-test
repository suite; 22 environment-dependent tests were skipped.

## Recovery decision

The public hunt is now at the point of diminishing returns. Both strongest
profiles showed recent activity: when inspected on 2026-08-23,
[Justin3009's Compendium profile](https://www.chronocompendium.com/Forums/index.php?action=profile;u=806)
reported last activity on 2026-08-20, and
[Vehek's profile](https://www.chronocompendium.com/Forums/index.php?action=profile;u=1235)
reported activity on 2026-08-22. These observations are time-sensitive and do
not imply consent to contact or willingness to answer.

The highest-value next action is a polite, narrowly scoped recovery request to:

1. Justin3009, because he reported still holding an incomplete Project Schala
   copy and IPS in 2016; and
2. Vehek, because the December 2008 exchange strongly indicates that he
   received and debugged the unnamed private development patch.

The first request should ask for metadata rather than a ROM: original filename,
format, byte length, hashes, approximate date, target ROM/header requirements,
and whether an IPS, Temporal Flux project/export, source notes, readme, or old
private-message record survives. It should separately ask whether private
forensic inspection and any redistribution are permitted. A ROM should not be
requested or accepted when a patch can be reconstructed by its owner against
their own clean copy.

Any recovered file should first be preserved unchanged and privately hashed.
Before any execution, it should receive the same metadata-only write census,
malware/archive inspection, provenance record, and no-production-import
classification used here. It must not be committed, redistributed, or treated
as permission to reuse community art or opaque assembly.
