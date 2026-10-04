# Chrono Trigger public research refresh — October 3, 2026

Evidence level: `documented`. Checked October 4 UTC / October 3 in the
workspace's America/New_York timezone. This is a bounded primary-source
refresh against [September 8](online_research_2026_09_08.md), not a new ROM
mapping proof. Commit times are distinct from lookup/crawler times.

No newly verified complete matching-C Chrono Trigger decompilation, playable
SNES-derived native CT port, or reproducible additive eighth-PC patch retaining
all seven original PCs was found in the checked sources. This does not assert
that no private, unindexed or unmerged work exists.

## Changes that matter

**Pseudoarc's randomizer advanced 22 commits.** Current checked head is
[`b2d8c0ba5836e23fc51c483f83b254176c7b3846`](https://github.com/Pseudoarc/ctrando/commit/b2d8c0ba5836e23fc51c483f83b254176c7b3846),
September 21. The comparison contains 17 changed files. The September 10
[`fe0c0cb72c0e67af6561cf311d69220309afb8ca`](https://github.com/Pseudoarc/ctrando/commit/fe0c0cb72c0e67af6561cf311d69220309afb8ca)
fixes an R-Series Beast Toss animation softlock. Its author describes a target
counter advancing past the exact value awaited by the caster. The fix adds a
counter handshake before the target advances again. This is a concrete lead
for our completion-protocol work; the upstream diagnosis/fix has not been
independently reproduced against Epoch's canonical ROM in this refresh.
It does not establish a new playable identity. The checked
[CharID enum](https://github.com/Pseudoarc/ctrando/blob/b2d8c0ba5836e23fc51c483f83b254176c7b3846/src/ctrando/common/ctenums.py#L24)
still enumerates exactly the seven vanilla PCs, IDs 0 through 6.

**The mstan SNESRecomp repository moved into RetroPortingToolKit and advanced
substantially.** The checked head is
[`88a9f7f51be3b1f0a805821e0fff7aa6f9e2246e`](https://github.com/RetroPortingToolKit/snesrecomp/commit/88a9f7f51be3b1f0a805821e0fff7aa6f9e2246e),
October 3. GitHub reports 434 commits ahead of the September pin. The retained
comparison response is capped at 250 commit entries and 300 files; this is not
a claim to have reviewed all 434 commits. Its current
[README](https://github.com/RetroPortingToolKit/snesrecomp/blob/88a9f7f51be3b1f0a805821e0fff7aa6f9e2246e/README.md)
describes a general framework requiring game-specific analysis, integration
and validation. The listed public game projects do not include Chrono Trigger,
and the compatibility table explicitly excludes ExHiROM. The latest-release
endpoint still reports `v0.2.0-alpha`, July 20; new source activity is not a new
release. The checked [LICENSE](https://github.com/RetroPortingToolKit/snesrecomp/blob/88a9f7f51be3b1f0a805821e0fff7aa6f9e2246e/LICENSE)
is PolyForm Noncommercial 1.0.0. No framework code was imported or installed.

The practical decision is to keep the canonical SNES patch effort on its
existing evidence path. The randomizer's counter-handshake fix deserves a
separate, bounded canonical-source audit later. The framework remains a useful
parallel research lead; it does not currently remove our ExHiROM, PC-ID,
save-lifecycle, graphics, interrupt or action-completion obligations.

## Exact unchanged comparison points

| Repository | Checked default-branch commit | Commit date UTC | Since September 8 |
|---|---|---|---|
| [dscotton/ct_disassembly](https://github.com/dscotton/ct_disassembly) | `eeae27acdb6565e96d1d796a3d60792c250c0aa1` | July 11 | Unchanged |
| [DocDamage/chronotrigger_disassembly](https://github.com/DocDamage/chronotrigger_disassembly) | `487a698bc1fd25cd564853cffe03c26902b7bbeb` | August 18 | Unchanged |
| [OnemusCT/temporal-redux](https://github.com/OnemusCT/temporal-redux) | `d8d4e38c0bf08b51a29441ef7ea2a489d63da58f` | September 2 | Unchanged |
| [GitExl/CTViewer](https://github.com/GitExl/CTViewer) | `2e5a206e09f0028fd5a1ca6cb9a9ed18bfc64fea` | July 19 | Unchanged |
| [nmrugg/chrono-editor](https://github.com/nmrugg/chrono-editor) | `66cbee13fe00fc46ca0aba56b61986adb3946618` | June 22 | Unchanged |
| [sp00nznet/snesrecomp](https://github.com/sp00nznet/snesrecomp) | `644c7647a9b2a6f286abe14ff07e1751e98c4a17` | September 7 | Unchanged |
| [springah/ct_pm](https://github.com/springah/ct_pm) | `1a3b457c230ffd714c3677f5f41a51e3e5343e72` | September 5 | Unchanged |

The two disassemblies were already known in September; rediscovering their
links is not new progress. `maci0/ct-recomp` remains HTTP 404 in this check.
That is an access observation, not evidence of abandonment or a legal event.

## Coverage and provenance limits

Direct attempts to refresh the old Chrono Compendium eighth-character and
Schala discussion URLs failed with connection/TLS errors. Their September
reply dates have not been promoted to fresh October observations. The
[author's disassembly discussion](https://www.reddit.com/r/chronotrigger/comments/1s12mi8/rom_disassembly/)
led back to the already tracked repositories. Search snippets and unrelated
recompilation/character rumors were not accepted as release evidence.
Authenticated GitHub repository search returned HTTP 422 because of the
account restriction, while direct repository/commit/compare reads succeeded.
The failed queries are retained; general web search supplied additional leads.

Private receipts are under `private/research/public_refresh_20261003b/`:
`heads.json`, individual repository responses, `ctrando_compare.json`,
`framework_compare.json`, `framework_release.json`, `forum_receipts.json`,
and `source_receipts.json`. The latter retains the failed initial animation
source path and the successful corrected path. Public, hash-only provenance
is [the source manifest](../references/online_research_2026_10_03.json).
No ROM, patch, save, extracted asset or upstream binary was downloaded.

To repeat the metadata check, query `repos/OWNER/REPO/commits?per_page=1`
through `gh api`, compare the exact September and October commit IDs with
`repos/OWNER/REPO/compare/BASE...HEAD`, and retrieve the exact commit-pinned
raw source URLs in the manifest. Do not overwrite this dated receipt with a
later head. A future source import needs its own license and provenance review.
