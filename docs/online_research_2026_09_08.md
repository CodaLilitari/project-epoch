# Chrono Trigger online research refresh - 2026-09-08

Evidence level: `documented` public-source reconnaissance. This is a dated
source/metadata inspection, not a new canonical-ROM audit or runtime test.
No ROM, patch, save, extracted asset, or upstream binary was downloaded.
Lookup completed: 2026-09-08 05:04:17 UTC. HTTP status checks used anonymous
GET requests to the exact GitHub page/API URLs below; no account access was
used. General web search supplied leads, followed by primary-source page,
GitHub API, and commit-pinned source inspection.

## Result and comparison boundary

There is fresh work on editors, randomizers, and general SNES recompilation
frameworks. This bounded search found no newly published, reproducible SNES
eighth-PC implementation retaining all seven vanilla PCs, and no newly
verified complete matching-C Chrono Trigger decompilation or SNES-derived
native Chrono Trigger port.

The tracked comparison baselines are the August 22 external survey and
August 23 clean-room/recompilation audit. The recovered August 31 task had
already revisited the two disassemblies, `ctrando`, `CTViewer`, the two
`snesrecomp` frameworks, and the unavailable `ct-recomp` repository. Therefore
August discoveries and the `ct-recomp` 404 are not presented as September news.
All commit dates below are UTC, distinct from inspection dates and crawler
timestamps. Default-branch comparisons do not exhaust private work or every
unmerged branch.

## Fresh changes relevant to data mapping

### Temporal Redux: September 2 save-state work

Current head is
[`d8d4e38c0bf08b51a29441ef7ea2a489d63da58f`](https://github.com/OnemusCT/temporal-redux/commit/d8d4e38c0bf08b51a29441ef7ea2a489d63da58f),
2026-09-02. It is nine commits ahead of the tracked August 22 survey pin
`d0becafe4ae58a5e159d5f84024df63698d1e5e2`: one August 29 backend change and
eight September 2 commits. The substantive September commit
[`07c77d6cc18f1d66ef57b94c4067fd47ad2566b9`](https://github.com/OnemusCT/temporal-redux/commit/07c77d6cc18f1d66ef57b94c4067fd47ad2566b9)
adds save-state and bulk-import work across practice-state UI, dump import and
application, inventory, field grouping, scanner, and memory definitions.
The inspected
[`memorymap.py`](https://github.com/OnemusCT/temporal-redux/blob/d8d4e38c0bf08b51a29441ef7ea2a489d63da58f/sourcefiles/practice/memorymap.py)
represents named memory fields with explicit addresses, lengths, masks, and
disabled state. This is a useful new cross-check lead for future memory-map
and replay tooling; its definitions have not been audited here against the
canonical ROM.

Its current
[`CharID`](https://github.com/OnemusCT/temporal-redux/blob/d8d4e38c0bf08b51a29441ef7ea2a489d63da58f/sourcefiles/jetsoftime/ctenums.py)
still contains Crono through Magus, IDs 0-6. Save-state editing is not evidence
of an eighth runtime/save record or Project Epoch sidecar safety.

### ctrando: active through September 7, plus a corrected historical caveat

Current head is
[`d6a28183183ae18fbf62a357c09f3dffc227710e`](https://github.com/Pseudoarc/ctrando/commit/d6a28183183ae18fbf62a357c09f3dffc227710e),
2026-09-07. September changes include multiworld/treasure work, location-map
fixes, event insertion fixes, and Lavos-gauntlet changes. Its current
[`CharID`](https://github.com/Pseudoarc/ctrando/blob/d6a28183183ae18fbf62a357c09f3dffc227710e/src/ctrando/common/ctenums.py)
still enumerates exactly seven playable identities. These changes establish
continued tool development, not additive PC `$07` support.

An important correction to the tracked August 22 survey is now necessary.
That survey described an animation reader which reduced object masks to role
counts. On August 26,
[`c7c57a33d6a552560a5afc4309754b6b723e6e3b`](https://github.com/Pseudoarc/ctrando/commit/c7c57a33d6a552560a5afc4309754b6b723e6e3b)
changed the representation to retain absent object positions as `None`, read
each main/miss mask bit separately, and reconstruct masks from those positions.
It also introduced separate player-Tech, enemy-Tech, and enemy-attack classes.
On August 30,
[`590befca24206ab9aa1b33537223b7a1f90a3624`](https://github.com/Pseudoarc/ctrando/commit/590befca24206ab9aa1b33537223b7a1f90a3624)
fixed authoring operations to assign fixed object positions and preserve the
intended player/enemy script class. These are August changes, not discoveries
that occurred after the August 31 stopping point.

The current model addresses the earlier sparse-position concern. Preservation
of every original pointer alias/shared suffix is not established by this
inspection. Project Epoch must retain its exact-mask, bank-qualified-pointer,
token-ownership, and interpreter-pinned proof requirements. No upstream
allocation, hook, machine routine, or game-derived script was adopted.

## Decompilation, disassembly, and port status

The following exact heads were rechecked through GitHub's public repository
and commit APIs on September 8:

| Project | Current commit hash | Commit date | Change from tracked August survey |
| --- | --- | --- | --- |
| [dscotton/ct_disassembly](https://github.com/dscotton/ct_disassembly/commit/eeae27acdb6565e96d1d796a3d60792c250c0aa1) | `eeae27acdb6565e96d1d796a3d60792c250c0aa1` | 2026-07-11 | Unchanged |
| [DocDamage/chronotrigger_disassembly](https://github.com/DocDamage/chronotrigger_disassembly/commit/487a698bc1fd25cd564853cffe03c26902b7bbeb) | `487a698bc1fd25cd564853cffe03c26902b7bbeb` | 2026-08-18 | Unchanged |
| [GitExl/CTViewer](https://github.com/GitExl/CTViewer/commit/2e5a206e09f0028fd5a1ca6cb9a9ed18bfc64fea) | `2e5a206e09f0028fd5a1ca6cb9a9ed18bfc64fea` | 2026-07-19 | Unchanged |
| [nmrugg/chrono-editor](https://github.com/nmrugg/chrono-editor/commit/66cbee13fe00fc46ca0aba56b61986adb3946618) | `66cbee13fe00fc46ca0aba56b61986adb3946618` | 2026-06-22 | Unchanged |

The first two are disassemblies. The latter two are viewers/editors. Their
annotations remain independent comparison leads, not new production address
or allocation authority. The dscotton `CHAR_EIGHTH` label does not override
Project Epoch's demonstrated namespace collisions.

The public [maci0/ct-recomp page](https://github.com/maci0/ct-recomp) and
[repository API](https://api.github.com/repos/maci0/ct-recomp) both returned
404. This repeats the August 31 observation; it does not establish deletion,
privatization, a rename, abandonment, or a legal takedown. No new source head,
license, build, or progress claim could be verified. The prior preserved
revision `76f9714747b35ff6835d2f7fbd877b1042482215` remains historical and quarantined;
its build-graph conclusions are not promoted to current status.

There is substantial fresh activity in the general framework
[mstan/snesrecomp](https://github.com/mstan/snesrecomp/commit/63135041fe09ae370c9a4e4da3dbf76ef1811744):
38 reachable commits returned by the September 1 onward query, current head
`63135041fe09ae370c9a4e4da3dbf76ef1811744` dated September 8. Changes include
[inline-argument provenance](https://github.com/mstan/snesrecomp/commit/c6d0ca8be5b030f1fcac745f0b12c232bf312601),
runtime localization, diagnostics, S-DD1 mapping/runtime work, and host audio
and presentation support. Its [released CLI](https://github.com/mstan/snesrecomp/releases/tag/v0.2.0-alpha)
is still the July 20 `v0.2.0-alpha`, whose release notes require game-specific
configuration and host integration to obtain a playable port. The current
README identifies a hybrid static/native path with an interpreter fallback;
this is not a completed Chrono Trigger decompilation. The project adopted its
PolyForm Noncommercial license on
[August 1](https://github.com/mstan/snesrecomp/commit/868df639d0736a5365aa633f3a587af52720c608),
so the license itself is not September news.

The separate MIT-licensed
[sp00nznet/snesrecomp](https://github.com/sp00nznet/snesrecomp/commit/644c7647a9b2a6f286abe14ff07e1751e98c4a17)
has six September 7 commits, current head
`644c7647a9b2a6f286abe14ff07e1751e98c4a17`. These add CPU helpers, deterministic
capture, scripted mouse input, and PPU/snapshot inspection. Its
[headless harness change](https://github.com/sp00nznet/snesrecomp/commit/8de722083bf4cb77cf228d09f0a4276bf02b668b)
could inform later diagnostic design. It supplies hardware services for a
separately authored/recompiled game; it is not a Chrono Trigger implementation.

A fresh repository search also found September activity in
[springah/ct_pm](https://github.com/springah/ct_pm/commit/1a3b457c230ffd714c3677f5f41a51e3e5343e72),
head `1a3b457c230ffd714c3677f5f41a51e3e5343e72` dated September 5. Its own
README identifies an Android v2.1.5 library loader for aarch64 Linux handhelds,
with user-supplied game libraries/data. This is a different porting technique
and game version, not an SNES decompilation or eighth-character patch. No
binary or game data was acquired and its playability claims were not tested.

## Public eighth-character and editor threads

The live final page of
[`8th Playable Character Possible?!`](https://www.chronocompendium.com/Forums/index.php?topic=4100.525)
still ends at reply 536 on February 28, 2023, with Mauron's slow-progress status.
The historical linked 2021 IPS remains prototype evidence; this refresh did
not download it. Mauron's
[March 3, 2024 status](https://www.chronocompendium.com/Forums/index.php?topic=13512.msg236343#msg236343)
still describes data documentation/expansion notes as substantially ready
while menu sprites and actual implementation remain open. Both pages were
read live, so their old dates are not being mistaken for new announcements.

The live final page of the
[Hi-Tech editor thread](https://www.chronocompendium.com/Forums/index.php?topic=10245.105)
shows Beta 34 as the latest author release, November 21, 2025. Later posts on
August 23, 2026 report continuing Geyser ghost-effect and palette issues; they
are user bug reports, not a new release or independently reproduced defect.
No September update was visible on that final page. Attached patches, saves,
and external screenshots were not opened.

[Chronotools](https://bisqwit.iki.fi/source/chronotools.html) still lists
version 1.15.9 and August 12, 2026 as its update date. It remains translation,
compression, relocation, and event tooling, with the author's explicit
compatibility limits. No new eighth-character claim was found.

Replacement-character demonstrations and Schala rescue/event content are not
counted as additive eight-PC evidence. The negative result is bounded by
public indexing and accessible pages; it cannot exclude private repositories,
Discord-only work, unindexed patches, or unannounced progress.

## Reproduction and Project Epoch implication

Reproduce the metadata check with GitHub REST endpoints
`/repos/{owner}/{repo}`, `/commits?per_page=1`, and
`/commits?since=2026-09-01T00:00:00Z&per_page=100`; pin any subsequent content
inspection to the full commit hashes above. Compare the tracked tool pins via
GitHub `/compare/{old}...{new}`. Reopen the exact final forum pages and compare
the final reply numbers/dates rather than search crawler dates. The report's
file hash can be recorded with
`Get-FileHash -Algorithm SHA256 -LiteralPath 'docs/online_research_2026_09_08.md'`.
These steps retrieve metadata and source text only; they require no ROM or
binary download. Counts describe the returned reachable history, not a
measurement of engineering effort.

At the start of this refresh, the practical next step was the independent,
source-only `BA-SYMBOLIC-HIGH-PACKAGE` gate. Use the newer sparse-mask representation and
memory-editor work as focused comparison leads if needed. No finding here
approves a production hook, ROM/WRAM/SRAM allocation, selector/action binding,
runtime helper, or PC `$07` installation.
