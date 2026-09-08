# Project Epoch development-tools strategy - 2026-09-08

Evidence level: `documented` for public-source findings; `hypothesis` for
comparative engineering estimates. This is a focused answer to whether an old
Nintendo development kit or leaked material would materially shorten the
eighth-character project. It supplements, rather than repeats, the
[September 8 online survey](online_research_2026_09_08.md).

## Recommendation

Continue the targeted SNES extension with original 65C816 helpers and bounded
runtime proofs. The strongest presently available shortcut is better use of
public development tools and existing game-specific maps. A generic SNES
development kit does not contain Chrono Trigger's character implementation.

The project baseline inspected for this decision is the completed
`BA-SYMBOLIC-HIGH-PACKAGE` source/host proof. Its explicit selector `$80`
association is synthetic; production high selectors remain unbound. The next
gate is original native-helper conformance in an isolated synthetic harness.
The package proof is not a running eighth character, and this strategy review
promotes no hook, scratch area, allocation, or game integration.

The recommendation is an engineering judgment, not a measured guarantee that
no alternative could be faster. A complete, provenance-verified, buildable
retail Chrono Trigger source project with symbols and Square's authoring tools
would materially change this assessment. No such public project was verified
in this bounded search.

## What an old development kit would supply

Real official development tools existed. Intelligent Systems' own company
history lists Super Famicom development-support tools in its 1990 entry.
[Intelligent Systems history](https://intsys.co.jp/company/history.html)

There is also directly available manufacturer documentation. WDC's
assembler/linker manual describes SNES-specific linker options, Nintendo
debugger ISX output, symbol support, and SNES bank layouts. Its current public
W65C816S datasheet documents the processor's registers, modes, instructions,
and caveats. These are useful for assembly and register-boundary questions;
the WDC part's documentation is not by itself a complete specification of the
SNES's customized CPU or its peripheral timing.
[WDC assembler/linker manual, Nintendo-development section, PDF page 18](https://www.wdc65xx.com/wdc/documentation/Assembler_Linker.pdf),
[WDC W65C816S datasheet](https://www.wdc65xx.com/wdc/documentation/w65c816s.pdf)

Inference: those facilities help assemble, place, inspect, and debug a
program. They do not infer Square's roster layout, save serializer, graphics
tables, Tech namespaces, or seven-character assumptions from the compiled
retail game. An original game's symbols and source would be the substantial
shortcut. Possession of the generic development hardware or its SDK would not
establish possession of those game-specific materials.

## Nintendo leaks and the Chrono Trigger prerelease

Fresh searches for Chrono Trigger source-code leaks, Gigaleak associations,
Square source projects, and development tooling did not identify an
authenticated public retail SNES Chrono Trigger source tree or a released
Square-specific character-authoring kit. Results included unverified forum
claims, dialogue-script releases, community tools, and wrappers for later
game versions. None was accepted as evidence of the original retail source.
This is a search result, not proof of absence in private or unindexed archives.
The exact contents of the historical leak archives were not inspected.

The well-known November 17, 1994 prerelease is a different class of artifact.
The original translation researchers describe text extracted from a
prerelease ROM, including its embedded version-date string and debugging
text. That establishes a compiled prerelease artifact, not an editable retail
source project or a ready-to-enable eighth character.
[GlitterBerri and collaborators' prerelease investigation](https://glitterberri.com/chrono-trigger/unseen-prerelease-text/)

A prototype can provide historical comparisons and clues. Applying its
addresses, record meanings, or spare-looking regions to US Rev0 would require
fresh canonical evidence. This review fetched public documentation and source
metadata only; it obtained no leak archive, prototype ROM, SDK binary,
copyrighted game source, or game asset. The project's existing separation of
local game inputs from source-controlled original work remains intact.

## Public tools with practical value

| Tool or source | Verified capability | Project Epoch use and limit |
| --- | --- | --- |
| [Asar](https://github.com/RPGHacker/asar) | Its authors describe an assembler for patches and new images, supporting 65C816, SPC700, and Super FX. | A possible independent assembly check for original routines. An assembler's ability to modify a ROM does not approve a destination or bypass the project's complete-diff guard. |
| [PVSnesLib](https://github.com/alekmaul/pvsneslib) | Public C/assembly SNES SDK with compiler/linker, graphics, input, audio, and examples. | Useful reference for standalone synthetic harnesses or homebrew. Importing its runtime into Chrono Trigger would introduce a second set of memory, interrupt, and hardware assumptions; it is not a drop-in eighth-character extension. |
| [Mesen Community Edition](https://github.com/nesdev-org/MesenCE) | Public community successor supporting SNES. Its SNES debugger implements trace logging, code/data logging, memory-access tracking, read/write break conditions, and step-back support. | A concrete candidate for future trace tooling and independent checks. Keep the already-pinned evidence builds until any replacement passes the existing replay and collector checks. |
| Existing game-specific editors, disassemblies, and randomizers | Their current scopes and revisions are recorded in the separate September survey. | Reuse their mapping and format leads against the pinned canonical ROM. They do not establish additive PC `$07` support. |

The original
[SourMesen/Mesen2 repository](https://github.com/SourMesen/Mesen2) is archived
(June 4, 2026), and its README explicitly directs users to Mesen Community
Edition. The successor's
[SNES debugger source](https://github.com/nesdev-org/MesenCE/blob/c6cea79f36afd33954fde6174418b3d944d0da88/Core/SNES/Debugger/SnesDebugger.cpp)
was inspected for the listed capabilities; they were not exercised in this
research task. No tool was installed or replaced.

## How to make the present approach more efficient

Complete the native helper against the existing descriptor/ABI contract, then
move to the smallest runtime experiment that resolves an actual remaining
integration question. Reuse the completed command grammar and symbolic
package proof. Reaudit them only when source drift, a failing result, or a
new boundary case justifies it. Maintain one explicit unresolved integration
list so a passing host test cannot silently become a runtime claim.

For the stated objective of a true eighth character in SNES Chrono Trigger
while retaining the original seven, a whole-engine decompilation or native
rewrite is currently a larger dependency than the targeted patch. Recompiling
machine instructions can change their execution host while preserving the
same seven-character assumptions. Removing those assumptions still requires
game-specific understanding. A new homebrew implementation could make its
own roster easy to extend, but reproducing the surrounding game is a separate
project. These are scope and dependency assessments, not benchmark results.

## Reproduction, pins, and evidence boundaries

Inspection date: 2026-09-08. Public GitHub metadata was fetched anonymously
from each repository API and its default-branch commit endpoint. Commit dates
below are UTC, not crawler dates. No release binaries or repository archives
were acquired.

| Public repository | Inspected default branch | Head SHA-1 | Commit date |
| --- | --- | --- | --- |
| `nesdev-org/MesenCE` | `master` | `c6cea79f36afd33954fde6174418b3d944d0da88` | `2026-09-06T11:40:49Z` |
| `RPGHacker/asar` | `asar_19` | `5fd539cd510e4a26afef66fc14e35ca6d8ff0497` | `2025-09-21T00:41:50Z` |
| `alekmaul/pvsneslib` | `master` | `e090f001ccffdc0fb69f479a8c9703e30d07f6b1` | `2026-07-31T04:25:03Z` |

Reproduction steps:

1. Read the linked primary pages and the pinned MesenCE debugger source.
2. Query `https://api.github.com/repos/{owner}/{repo}` and then
   `https://api.github.com/repos/{owner}/{repo}/commits/{default_branch}`;
   retain branch, archived flag, commit hash, and UTC commit date.
3. Repeat the exact search families `"Chrono Trigger" "source code" "leak"`,
   `"Chrono Trigger" "Gigaleak"`, and Chrono Trigger Square development tools.
   Classify original source, disassembly, dialogue transcript, compiled
   prototype, wrapper, and SDK separately. A newly found artifact requires
   provenance and build inspection before changing the recommendation.
4. Reconcile findings against the current local milestone. The inspected
   `docs/schala_symbolic_high_package_v0.md` SHA-256 was
   `2ba5ce86b6aa1088956f98e5a70cfa1f9ce57827106a13aff080ba24efef39d6`.
   The inspected `docs/online_research_2026_09_08.md` SHA-256 was
   `853ea688def6c635548a6bb8e46c926c4051b60d792e2eac554baa5b10fa35d3`.

This document is original narrative and metadata. Its file hash is reported
with the handoff; hashes identify the inspected artifact, not the truth or
completeness of a public claim. No canonical bytes, native helper, generated
ROM, patch, or runtime result is produced by this research task.
