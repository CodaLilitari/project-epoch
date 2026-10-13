# Project Epoch: practical recompilation and Ghidra assessment

Date: 2026-10-13. Coda, collaborating with Andrei. Local research after explicit
resumption; no publication is implied by this document. The corresponding
machine record is `references/recomp_tool_practical_assessment_2026_10_13.json`.

**The CT-specific recompiler now works in our local headless test environment.
That makes it a credible experimental alternative, but it has not demonstrated
an easier eighth-character implementation.** Keep the existing SNES prototype
as the implementation baseline while comparing one concrete Epoch change on
the working recompilation build. Ghidra is useful auxiliary tooling with
observed SNES-extension limitations; it is not an automatic porting solution.

## What was actually downloaded and tested

| Tool | Executed result | Practical disposition |
| --- | --- | --- |
| [ThisIsAkill/ct-recomp](https://github.com/ThisIsAkill/ct-recomp/tree/a6b49257e527d1f219ce6466075b5e035dd8e5f2), commit `a6b49257e527d1f219ce6466075b5e035dd8e5f2` | Downloaded, verified all 135 source files, built using existing WSL Ubuntu, passed 23 engine tests and nine selected ROM-backed tests, including a Gato victory replay. | Usable headless research build. An Epoch-specific modification and independent-emulator comparison remain necessary. |
| [Ghidra 12.1.4](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build) with [ghidra-snes 1.3.0](https://github.com/joshleaves/ghidra-snes) | Installed privately with a portable JDK; ran five original 65816 probes and read-only canonical/expanded-loader checks. | Use for inspected disassembly, references and bounded analysis. Width context and individual instruction semantics require validation. |
| [RetroPortingToolKit/snesrecomp v0.2.0-alpha](https://github.com/RetroPortingToolKit/snesrecomp/releases/tag/v0.2.0-alpha) | Downloaded the Windows CLI; `--help` and a build on an original synthetic cartridge exited zero and generated 101 files. Generated output was not compiled or executed. | Useful optional generator. Generation success is not game execution. Its inspected current README lists ExHiROM as unsupported. |

All installations and generated outputs are project-local under ignored
`private/tools` and `private/research`. Canonical game inputs were hashed before
and after and remained unchanged. Generated game-derived C/overlays, Ghidra
projects, game data, saves and raw logs remain private. No new system software,
paid API route, ROM download, game patch or publication was needed for these
tool tests.

## The CT recompiler result and its limits

The source revision is unchanged from the earlier source review. The new
evidence is an actual build and selected execution, so this does not repeat the
old assessment under a new date. Existing WSL GCC/G++ 15.2.0 and CMake 4.2.3
produced a Release headless executable. SDL2 was absent; interactive display,
audio and native Windows frontend behavior were not qualified.

The synthetic suite passed 23/23 tests. Eleven C tests performed 20,105,284
CHECK evaluations; that is not a count of independent gameplay scenarios.
The nine selected game tests passed:

| Test group | Observed scope |
| --- | --- |
| Boot and menu | 1,500/1,700 frames; supplied nonblack, audio and required-PC gates. The inherited `boot_interp` test name is misleading: this invocation uses native dispatch. |
| Native/interpreter comparisons | Boot (1,500 frames), Leene Square (9,210), Gato battle (11,000), and Gato victory (13,950). The victory test checked enemy HP zero and the watched Crono HP byte nonzero at frame 13,400. |
| Host stack | 10,600-frame replay, deepest measured host C stack 2,729 bytes against the test's 32,768-byte ceiling. This says nothing about guest SNES stack ownership. |
| Rendering heuristic | Zero detected flicker frames over frames 10,680–11,100 against the supplied maximum of 20; no human visual review. |
| Native coverage | Passed the supplied >=49% gate over 11,000 frames. The successful output did not print the exact percentage. |

The comparisons use per-frame hashes of CPU, WRAM, SRAM, VRAM, CGRAM, OAM,
rendered frame and APU state, comparing native dispatch with this same
project's interpreter. Both share hardware/runtime code. This is not agreement
with Mesen, a complete campaign test, a performance comparison or an eighth-PC
test. Six overlay entries remain interpreted because an X-width question at
PLX is unresolved. Another 31 non-engine cases in this configuration were not
run; the game build's duplicate 23 engine tests were not repeated.

The build retains the SNES memory model and its existing consumers. Host C
generation does not itself expand the roster, disambiguate Epoch's name and
vehicle contexts, fix fixed-size tables, supply native recruitment, or extend
save/load semantics. Those requirements survive a route change.

## Ghidra observations

The NSA tool is Ghidra. We exercised the actual 12.1.4 distribution with
ghidra-snes 1.3.0 and portable Temurin 21.0.12.1+1. The extension metadata says
12.0.4; successful bounded tests on 12.1.4 are not general compatibility proof.

The five original-byte probes establish:

1. A selected REP/SEP sequence preserves hidden accumulator B correctly:
   after loading `$1234`, changing to M8, loading `$56` and TAX under X16,
   Ghidra p-code reaches C=X=`$1256`.
2. A PHP/SEP/PLP sequence restoring M16 is automatically misdecoded at its
   following immediate LDA: length two instead of three. Ghidra nevertheless
   reports completed decompilation. A success flag is not semantic validation.
3. Explicit long reads and writes preserve distinct `$7E` and `$7F` addresses
   in the observed pseudocode.
4. Indexed indirect JMP disassembles but decompilation fails in the original
   fixture. Claude identified a p-code defect, independently confirmed in the
   separate known-index/mapped-target experiment below. This is not merely
   missing jump-table resolution.
5. Clearing the bad suffix, explicitly asserting the whole context register
   over the short original test suffix and redisassembling restores its correct
   lengths. This broad annotation is deliberately synthetic; it is not a
   general recipe for asserting real-game M/X/E context. The unknown native
   status-pull operation remains in the decompilation.

The canonical 4 MiB image imports using the SNES loader. Three selected spans
match their canonical bytes; WRAM is uninitialized, and the low-half `$410000`
alias is absent in this view. These three checks are not whole-map coverage.
A separate fresh import confirms none of the initialized ROM blocks is marked
writable.

The unchanged accepted 8 MiB diagnostic is rejected by the stock header
detector with “Multiple valid SNES ROM headers found.” A second original
diagnostic calls the installed extension's header/checksum APIs for all three
candidates. The headers whose titles start at file offsets `$00FFC0` and
`$40FFC0` both pass all six predicates as ExHiROM, with declared size 8 MiB and
stored/computed checksum 56,679. The LoROM candidate fails earlier checks.
This directly confirms the ambiguity; it is not an invalid-image diagnosis.
No headers were rewritten to accommodate the tool. Expanded mapping still
needs a tested importer or explicit read-only mapping.

Claude Code reviewed only the bounded original-source/result packet and ran
nothing. Root independently checked the returned claims. Its useful concerns
include output freshness, context breadth, missing PBR/DBR/D premises, and the
indirect-jump p-code. The original driver did not prevent stale output reuse;
the actual accepted log records creation of its fresh v5 project and its
output marker, and a separate offline assessor checks the result hashes and
case expectations. New follow-up drivers require fresh output directories,
explicit markers and hashed result files. Preserve the original probes and
failed harness pilots rather than rewriting their history.

The separate six-case indirect-transfer experiment sets X using an actual
`LDX #$0002`, explicitly initializes PBR=`$C0`, and maps the pointer tables and
target bytes. Opcodes `$7C`, `$FC`, `$6C` and `$DC` all generate an extra
three-byte load followed by a direct transfer to a temporary in Ghidra's
`unique` address space. Its p-code emulator enters that space and fails its
next instruction decode. Direct `$4C` jump and `$20` call controls reach their
mapped targets and write their expected markers. Three indirect cases fail
decompilation; **`$FC` completes without warnings and emits a wrong temporary
address call**. Absence of warnings is therefore insufficient too.

The release ZIP contains language sources but no compiled `.sla`; Ghidra
compiled those sources locally. A separate compile of the unchanged sources
produces the same SHA-256 as the loaded processor artifact:
`fdf8a34533d88d506a799feae4c1039dc71d82d4a946d2da0e723842f0b0d671`.
This ties the result to the actual build, rather than an assumed shipped
binary. The final fixture uses native E0/M16/X16, ordinary nonwrapping
pointers, explicit synthetic function bodies and a nonwritable code block.
It is a bounded Ghidra experiment, not native SNES execution or a full CPU
conformance matrix. No extension fix or upstream report has been published.

## Other new tools and community evidence

The tested generic CLI release is commit
`ead6f15c5d91e555ad0b6a7b178bf3a4ca2af738`; the inspected newer framework head is
`e54427bad93fb75729ce8214fdd7a46e197e6223` (October 11). Do not attribute newer
source features to the tested July binary. The [current README](https://github.com/RetroPortingToolKit/snesrecomp/blob/e54427bad93fb75729ce8214fdd7a46e197e6223/README.md)
supports standard HiROM and lists ExHiROM/ExLoROM as unsupported. Its current
PolyForm Noncommercial license supersedes the old release's no-license wording.

The recent [Mega Man X releases](https://github.com/mstan/MegaManXSNESRecomp/releases/tag/v2.2.1-alpha)
provide implementation precedents for added character behavior. They are
upstream claims, not locally reproduced Chrono Trigger roster evidence. The
similarly named `sp00nznet/snesrecomp` is a distinct project; neither repository
name nor an AI-assisted porting story proves a complete CT decompilation.

Reuse the existing community maps, source corrections and accepted Epoch
experiments. This assessment contributes new local build/tool observations;
it does not claim first discovery of character addresses or a previously
unknown eighth-character method.

## Reproduction and next decision

The machine record records exact release/archive, receipt and result hashes.
Private packet reproduction is read-only:

```powershell
python -B private/research/ct_recomp_test_20261013/reproduce_receipt.py
python -B private/research/recomp_tool_assessment_20261013/assess_ghidra_results.py
```

Exact original build commands are preserved in
`private/research/ct_recomp_test_20261013/build_engine.sh` and `build_game.sh`.
Fresh builds should use fresh output paths; the historical scripts reuse their
own log destinations. Ghidra's final runs, original synthetic bytes, sources,
command lines and result hashes are preserved in the private assessment.

The useful comparison is one bounded Epoch change in both environments:
retaining logical `$07` and its independent state through an ordinary action
without replacing a vanilla PC or touching Epoch's vehicle/name namespace.
Count the actual adapters, fixes and evidence needed on each route. Until
that comparison succeeds, “the recompiler runs” and “recompilation is easier
for the eighth character” remain different claims. SNES compatibility and
PC-only host freedom also remain different product choices; no PC-only
commitment has been made.
