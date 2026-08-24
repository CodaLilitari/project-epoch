# `maci0/ct-recomp` legitimacy and reuse audit — 2026-08-23

## Bottom line

Pinned audit target:
[`76f9714747b35ff6835d2f7fbd877b1042482215`](https://github.com/maci0/ct-recomp/tree/76f9714747b35ff6835d2f7fbd877b1042482215).

The repository is real and contains substantial reverse-engineering work, but
its front-page description is materially broader than its build graph proves.
The most accurate short classification is:

> a byte-exact SNES transliteration/reassembly and extensive asset-rebuild
> framework, accompanied by a substantial but incomplete matching-C corpus
> that is not integrated into the whole-game build.

It is not a native Windows, Linux, or macOS port. It does not produce a host
executable, and it still requires SNES hardware or an emulator. It is not an
emulator wrapper either: the emulator is a test oracle, not part of the game
deliverable.

The repository must remain quarantined because it has no detected
project-level license and directly tracks a full retail-ROM prefix plus large
amounts of extracted game content. Project Epoch copied no source, label,
payload, address claim, or test vector from it. One neutral address lead was
useful only after the snapshot's semantic label was rejected and the behavior
was independently rederived from Project Epoch's pinned CC0 disassembly and
canonical clean ROM.

## Acquisition and preservation

The public repository was created on 2026-08-16. Its root commit is
[`8f325dcab3dc656860eee2bc8db2202588c3c181`](https://github.com/maci0/ct-recomp/commit/8f325dcab3dc656860eee2bc8db2202588c3c181),
and the README first appeared in
[`ee830c3ad90e79a34133e4399488aa95734aeb4f`](https://github.com/maci0/ct-recomp/commit/ee830c3ad90e79a34133e4399488aa95734aeb4f).
The audited head was committed on 2026-08-23, about 6.6 days after repository
creation.

The local preservation set contains:

- a complete, non-shallow Git clone with push disabled;
- a clean detached audit worktree at exact head `76f9714`;
- a complete all-refs Git bundle, verified by `git bundle verify` and
  `git fsck --full`;
- bundle size: 221,586,087 bytes; and
- bundle SHA-256:
  `E5D0E83E93FBBAF698378A931EA27888F4AF21B6DE41BF7FB4B96845D8874E58`.

The bundle and checkout remain ignored and local-only. They are not Project
Epoch source artifacts and must never be pushed.

At the audited head, the public tree has 7,988 tracked files, 723,782,447
bytes (690.25 MiB), and 64 linear commits. It has no merge commits or signed
commits. At audit time GitHub showed one unprotected `main` branch and no
tags, releases, issues, pull requests, stars, forks, or subscribers.

## Claim matrix

| Claim or category | Verdict | Reason |
| --- | --- | --- |
| Full matching C decompilation | **No** | The principal full-ROM build is generated inline 65816 assembly/literal bytes, while the genuine matching-C corpus is incomplete and build-disconnected. |
| Partial matching C decompilation | **Yes, substantial** | 2,626 manifest-backed low-level C routines are compiled and compared per function against pinned expected and canonical bytes. |
| Byte-exact reassembly/transliteration | **Yes in architecture** | Recognized instructions are emitted as 65816 assembly and remaining bytes as literals, then rebuilt as a SNES ROM. Local execution was intentionally not attempted in this audit. |
| Asset rebuild | **Yes, substantial but incomplete** | Thousands of editable assets and many lossless round trips exist, but the repository's own completion audit retains partial rows and semantic gaps. |
| Host static recompilation | **No** | Output code still targets WDC 65816 and produces a SNES cartridge image. |
| Native desktop port | **No** | No host application entry point, graphics/audio/input platform layer, or native executable build exists. |
| Emulator wrapper | **No** | Vendored emulator code is used by tests; it is not linked into the deliverable. |
| Safe Project Epoch code donor | **No** | No project license, tracked retail ROM, extracted payload, unreliable semantic labels, and different proof boundaries. |

## What the principal build actually does

### Default transliteration/reassembly

[`tools/dec/translit.py`](https://github.com/maci0/ct-recomp/blob/76f9714747b35ff6835d2f7fbd877b1042482215/tools/dec/translit.py)
reads the canonical source ROM, emits decoded instructions where its decoder
has an instruction, and emits every other byte as literal `db` data. The
result is assembled back into a SNES image and compared with the original.

That is useful, reproducible reassembly infrastructure. It is not a
source-independent reconstruction: undecoded code and data are serialized
directly from the original image.

### Advertised “C-native” build

[`tools/build/c_native_build.py`](https://github.com/maci0/ct-recomp/blob/76f9714747b35ff6835d2f7fbd877b1042482215/tools/build/c_native_build.py#L128-L223)
compiles the generated C modules for the original 65816 CPU, extracts symbol
bytes, and attempts to place them at their ROM offsets. Its acceptance logic
has a decisive circularity:

1. output begins as a complete copy of the original ROM;
2. a compiled function is written only when its bytes already equal the
   corresponding original-ROM slice;
3. overruns and byte mismatches are recorded, skipped, and printed as
   warnings;
4. the build fails if zero functions match, but it does not require every
   expected function to exist or require zero main-lane mismatches; and
5. the final full-image hash can therefore stay green because every skipped
   span remains the untouched original bytes.

The separate 55-function cc65 sidecar lane does fail on its own mismatch list.
That does not close the main-lane hole. A valid full-game gate must start from
an independently defined image or fail unless the complete expected function
set is present, every body is placed, and the mismatch count is zero.

The label “C-native” is also easy to misread: this compiler targets SNES 65816,
not the host machine.

## Generated C versus genuine matching C

The checked-in `src` directory contains 166 files and 132,883,985 bytes.
Conservatively identified generated sources account for 99.522 percent of that
size.

The monolithic byte-exact source has 40,696 registry slices:

- 40,691 are inline 65816 assembly or literal-byte bodies;
- five are pure-C splices; and
- 3,712 bodies use literal-byte fallback according to the final status ledger.

The 64 bank modules and nine concern modules are generated splits of those
bodies. They provide navigation and a C compiler container, but not 73
independently maintained gameplay modules.

The generated pseudocode is a different readability artifact. It models CPU
registers, flags, stack behavior, volatile memory, and generated labels. Its
reported 40,211/40,696 “structured C” ratio means that the generator emitted at
least one non-comment expression for a slice. It does not mean 98.8 percent of
the game has been semantically recovered into portable, build-driving C.

The strongest work lives separately under `tools/compiler/corpus`:

- exactly 2,626 `fn_*.c` files;
- exactly 2,626 `fn_*` manifest properties;
- 1,629,609 bytes and 51,120 lines; and
- per-function compilation to 65816 followed by comparison with pinned
  expected bytes and the canonical ROM slice.

That is legitimate matching-decompilation methodology. The internal
[`docs/internals/compiler.md`](https://github.com/maci0/ct-recomp/blob/76f9714747b35ff6835d2f7fbd877b1042482215/docs/internals/compiler.md)
still says 2,627 in several places; the tracked file set and manifest both say
2,626. The repository's provisional denominator is 3,033 candidate real
functions after excluding identified artifacts, which would put the corpus at
about 86.6 percent of that author-controlled estimate. Neither the 3,033
denominator nor the semantic function topology has been independently proved
here.

Most importantly, the full-ROM build does not consume this 2,626-function
corpus. The repository therefore has a substantial matching-C workstream, not
a matching-C whole-game build.

## Function-boundary and semantic-label quality

The repository's deeper documentation correctly warns that 40,696 is not a
normal source-level function count. The registry comes from aggressive linear
and target-seeded decoding, and its history records duplicate, contained,
fallthrough, branch, and jump-table artifact classes. The slices remain useful
byte-exact address regions, but percentages using 40,696 require that caveat.

Semantic labels are not reliable enough to import. Three independently checked
examples are sufficient:

- snapshot `$C1:CA1A` is named as window-layout work, while the pinned CC0
  disassembly and canonical control flow identify the dual-Tech entry builder;
- snapshot `$C1:F623` is named as a window-layout item builder, while the
  independent path processes level-ups; and
- snapshot `$C1:F9EB` is named `WindowLayoutPass2`, while the independent path
  grants reserve-party XP.

This is why Project Epoch treats every external label as a search hypothesis,
not as evidence.

## Asset work

The public tree tracks 3,072 asset files totaling about 39.4 MiB. Major groups
include audio, structural data, text, planar graphics, tables, palettes,
compressed graphics, and credits. Many codecs have byte-exact no-op
round-trip and confined-edit tests. This is meaningful tool work.

“Every asset extracted to modern editable formats” is still too broad. The
repository's own completion material retains partial status for:

- unresolved code fragments and raw/comment representations;
- generated fallback palettes for some compressed graphics;
- incomplete runtime/visual validation;
- partially mapped audio arrangement and package roles;
- raw-hex tables without recovered semantics; and
- at least one compressed-text family without a completed codec.

The calibrated description is “extensive asset extraction and reinsertion,
with documented remaining semantic and runtime gaps.”

## Retail-ROM and license boundary

No project-level license file was detected. Licenses inside vendored tools do
not license the surrounding repository or extracted game data.

The tracked `build/ct_lz_alloc_proof.sfc` is 4,201,851 bytes. Its first exactly
4,194,304 bytes hash to canonical Chrono Trigger US Rev0:

- prefix SHA-256:
  `06D1C2B06B716052C5596AAA0C2E5632A027FEE1A9A28439E509F813C30829A9`;
- trailing data: 7,547 bytes; and
- complete file SHA-256:
  `1C36815DE1437840C49C1915E8C30A1F7AC3425BDC3FBE2875DABE01F1ED4485`.

The tree also tracks extracted dialogue, audio, graphics, palettes, binary
tables, generated literal-byte C, and other game representations. Regardless
of any eventual legal interpretation, it provides no affirmative clean-room
reuse path for Project Epoch.

## CI and execution status

All 48 visible GitHub Actions runs failed before creating a job at audit time.
The [latest audited run](https://github.com/maci0/ct-recomp/actions/runs/32642974503)
reports an invalid workflow file and points to `.github/workflows/ci.yml` line
25. The unquoted `run:` scalar contains a colon in its fallback message, which
breaks YAML parsing. Public CI therefore supplied zero executed jobs and zero
check-run corroboration.

Even after fixing YAML, the workflow does not provision the ignored source ROM
and does not install cc65 although the C-native test requires `cl65`. Several
purported stop-the-line checks use `command || echo`, including the emulator
boot, LZ size, and C syntax paths, so those steps can remain green after the
underlying command fails.

Project Epoch did not execute any `ct-recomp` code, compiler, test, emulator,
or build script. Static inspection found:

- unauthenticated vendored compiler, assembler, and emulator binaries;
- networked package installation without a hash-locked Python dependency set;
- inherited environment and shared temporary-path behavior; and
- emulator tooling capable of touching save/runtime locations.

The available host also lacks the exact claimed toolchain. A future execution
audit would require an offline, bounded, throwaway harness with verified tool
hashes and no access to Project Epoch ROMs, saves, emulator profiles, Git
credentials, or working tree. Tests executed from the snapshot in this audit:
**zero**.

## Public provenance and commentary

The repository owner uses a long-lived GitHub account created in 2013 and has
many public repositories. The profile self-reports senior architecture,
compiler/decompilation, container, and model-inference experience. This makes
the account less consistent with a disposable hoax, but it remains
author-controlled evidence rather than independent validation.

The root commit contains `Co-Authored-By: internal-model`. That proves some
model-assisted authorship was disclosed. It does not identify Gemini, OpenAI,
the exact model, the prompting workflow, the share of generated work, or the
depth of human review. Calling the project “Gemini output” would therefore be
unsupported.

Exact-name, URL, author, and distinctive-phrase searches across major web and
fan-community indexes found no independent discussion or validation at audit
time. Direct Reddit and Bluesky API access was blocked, and Chrono Compendium's
guest search presented a CAPTCHA, so the defensible conclusion is **not yet
independently discussed or validated in the sources searched**, not “nobody
has ever discussed it.”

The closest independent community item is a
[June 2025 Reddit thread asking whether a Chrono Trigger decompilation exists](https://www.reddit.com/r/chronotrigger/comments/1lo6x8k/decomp_of_chrono_trigger/).
Visible replies through June 2026 do not mention this repository. A current
[game-file-reversing directory](https://velocityra.github.io/awesome-game-file-format-reversing/games/s/)
lists CTNx, `ct-fmv`, and CTViewer but not `ct-recomp`. Those absences are
consistent with a project only days old; they are not a rejection or quality
verdict.

## What Project Epoch learned safely

Three neutral address clusters were checked independently:

1. **Reserve XP: new blocker.** Canonical `$C1:F9EB-$C1:FA60` grants 75
   percent XP to joined, inactive logical IDs but stops before `$07`. The
   associated active-membership table has only seven initialized bytes, so
   changing one loop bound is unsafe. This is now pinned by the independent
   read-only audit in `docs/pc7_battle_progression_boundary_audit.md`.
2. **Field refresh: sharper lifecycle seam.** Canonical
   `Field_RefreshPartyObjectsIfChanged` reruns startup through exactly the seven
   PC object-registry entries `$018D-$0193`. Generic LoadPC syntax can carry ID
   `$07` without giving it a refresh-registry entry. This adds a concrete
   watchpoint and failure mode to an already-known architecture boundary.
3. **Party cursor map: corroboration, not capacity.** Canonical
   `$C2:CD2B-$C2:CD9A` builds eight cursor-map entries from the nine-position
   roster. The map already fits three active plus five reserves; downstream
   name, portrait, walking-sprite, palette, and record consumers remain the
   actual hazards.

The snapshot's tech, item, name, graphics, palette, animation, save-layout,
and numeric-seven labels added no trustworthy implementation source. Several
conflicted with stronger existing Project Epoch audits. No snapshot material
was promoted to a production catalog.

## Decision

`ct-recomp` is neither an empty fake nor the claimed completed whole-game C
decompilation. Its author has built a large byte-exact reconstruction and asset
tooling corpus plus genuine matching-C work. The headline compresses those
different maturity levels into a completion claim the build graph does not
support.

Project Epoch will retain the complete snapshot only as local preservation and
an adversarial address index. Reuse remains prohibited. Any future lead must
pass the same process used for reserve XP:

1. record only the neutral address or question;
2. discard the snapshot's name and semantic explanation;
3. rederive behavior from the pinned CC0 disassembly and canonical clean ROM;
4. pin exact bounds and hashes in a source-only auditor;
5. label static, runtime, proposal, and unresolved evidence separately; and
6. approve no hook or allocation until Project Epoch's own runtime matrix
   passes.
