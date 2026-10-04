# Project Epoch current handoff

Updated 2026-10-03. This page is the short resume point; the append-only
[developer log](DEVELOPER_LOG.md) and individual evidence packets retain the
full history. The project is research in progress, not a playable eighth-PC
release. The open integration gate is `BA-NATIVE-INTEGRATION-DESIGN`.

## Authoritative locations and resumption

- Local workspace: `C:\CHRONO TRIGGER`.
- GitHub: [CodaLilitari/project-epoch](https://github.com/CodaLilitari/project-epoch).
- GitLab: [codalilitari/project-epoch](https://gitlab.com/codalilitari/project-epoch).
- Portfolio: [Project Epoch case](https://richard-pemberton-research.darkahn.chatgpt.site/#project-epoch).

On resumption, both hosted main branches and the local checkout were exactly
`a0b17f6227ed6a54cdfb7c63e726feb94d26b89d`. The old GitHub account path
returned 404 through the authenticated API. The local `origin` URL was
corrected to the verified CodaLilitari repository; the private archive remote
was left unchanged. GitLab's later project activity was not a newer source
commit. The portfolio already linked to GitLab and accurately described
unfinished research, private game inputs, and no finished playable patch.

The September 8 session was interrupted with unfinished sources. October 3
is a new resumption date, not twenty-five days of elapsed engineering work.
The exact interrupted files were preserved in an ignored recovery archive
before editing. Historical September reports and accepted references remain
unchanged.

## Completed foundations to preserve

The original 577-byte stack-local helper already has repeated synthetic
cartridge-ROM execution and minimal-handler NMI proofs. The canonical game
has repeated primary/alternate resolver observations, one successful queued
action, and a natural failed Cure lifecycle. These prove their declared
contexts. They do not approve game code placement, game stack ownership,
partial-publication safety, a new late-rejection cleanup path, or PC `$07`.

The saved mapping distinctions, empty production allocation/hook catalogs,
safe-empty save policy, and all earlier conditional scene/IRQ packets remain
mandatory. Start with [the developer guide](schala_eighth_character_developer_guide.md)
and [the correction register](DATA_MAPPING_CORRECTIONS.md) before reusing an
older annotation. Do not repeat accepted native matrices without source drift
or a newly identified boundary.

## Work in progress at this checkpoint

1. The additive [scene `$80` remaining-return packet](schala_scene80_remaining_returns_v2.md)
   is accepted after independent root review, 38 tests and exact repeated CLI
   reproduction. Its two old frontiers now have conditional return proofs;
   this does not establish legal inputs or physical stack/memory ownership.
2. The [scene `$8B` copy-producer packet](schala_scene8b_copy_producers_v1.md)
   is accepted after independent peer/root review, 52 tests and exact CLI
   reproduction. Four stubs reduce to three pointer producers with explicit
   input/alias premises. The separate [half-fill packet](schala_scene8b_half_fill_v1.md)
   is now accepted with 38 tests and independently repeated metadata. Zero s
   causes 16,384 word stores under fixed-target premises; positive s fits the
   $380 comparison interval exactly for 1..224. This proves no legal script
   domain or ownership of that interval.
3. The [actual-game NMI observer](normal_nmi_stack_observation_v1.md) now has
   two identical full traces across five selected intervals, independently
   revalidated with complete observed WRAM reconciliation. Each reaches 34
   bytes below handler entry, 38 including its existing hardware frame.
   The accepted metadata preserves all limits and the failed earlier run.
   Its 80 observer and 46 acceptance tests pass. Preserve this pair; it is
   neither a whole-NMI bound nor helper-preemption/stack-ownership proof.
4. Follow the [interrupt strategy review](schala_package_interrupt_strategy_review_2026_10_03.md).
   Do not borrow the game's busy byte as a helper lock. The exact small
   original-cartridge fixture has a reviewed 67,112-clock conditional timing
   envelope, excluding DMA/HDMA and interrupt work. The general 32-target
   registry has a much larger envelope.
5. The [resolver-phase v2 observation](schala_package_resolver_phase_v2.md)
   now repeats identically in two isolated runs: 2,261 records, eight earlier
   interrupt contexts and the following IRQ/NMI pair, with 161 engine fields
   per record. Preserve the intentionally rejected v1 pilot and its unchanged
   protocol. The 43 v1, 34 v2 and 39 acceptance tests pass. HDMA is enabled
   for all eight unfinished channels at resolver entry; no-pending snapshots
   do not prove no future service. IRQ circuit counters and relevant overclock
   settings were not captured, so no interrupt deadline is certified.
6. The [HDMA timing model](schala_package_hdma_timing_v1.md) is now accepted
   as conditional static evidence: 13 tests and two root CLI reproductions
   match the independent peer and author exactly. Generic service is 472
   clocks; the fixed-fixture phase refinement is 106,342. Explicit line/frame
   minima and unproved configuration/cache binding prevent treating this as
   an admission certificate. The frozen report records preparation status;
   this handoff and the latest developer-log entry record root acceptance.
7. The separate [v3 observer](schala_package_resolver_phase_v3.md) now passes
   twice: 2,263 identical records, 163 engine fields and exact complete v2
   projection. It captures internalRegisters.hCounter/vCounter and a post-load
   line-0-to-line-1 crossing under guarded zero extras. The crossing occurs in
   historical NMI context 1; preserve the rejected main-context-only pilot.
   Hidden cache values remain unobserved and a valid-source-state premise is
   explicit. All 178 phase tests pass. Read the external review disposition
   before treating file consistency as authenticated execution evidence.
8. The separate [IRQ request-transition v1 packet](schala_irq_request_transition_v1.md)
   is accepted at source-conditional-host-model: 81 tests and identical independent
   root/peer metadata, SHA-256
   `846a54df9c490cee263bb86cf1b351683262562915eaecb148e3c182bd1686a7`.
   It pins fourteen Mesen files and the accepted v3 reference, models recursive
   DRAM Exec order, all uint8 pending counts, explicit register operations and
   separate CPU sampling/selection gates. The existing 178 phase tests pass;
   no native matrix was rerun. Exact observed-seed hypotheses give host-model
   offsets 124740/124744/124748; the abstract 1360-clock floor gives
   124372/124376/124380. Neither is a certified game deadline. Unknown
   callback/register/reset premises refuse. Preserve the older private drafts
   and earlier peer generation rather than relabeling them accepted.
9. Next: design a bounded source/observation closure packet for DMA/HDMA bus
   effects and omitted renderer/control/SPC/debugger/coprocessor callbacks.
   Reverse DMA can write IRQ enables/timers; DMA source reads can acknowledge
   TIMEUP. Unknown reentry can duplicate H6 or H10 and defeat a generic
   four-clock spacing assumption. Use the current phase evidence to separate
   already-known inputs from genuinely missing observations before proposing
   another native run. The [new review disposition](external_review_irq_transition_2026_10_03.md)
   records the verified H10 counterexample and final review limits.
   HDMA source-read/rendering isolation, wrapper cost, physical stack ownership
   and pre-effect versus later-resolver lifecycle remain separate obligations.
   No phase rule, high-selector binding or game insertion is approved.

The [October research refresh](online_research_2026_10_03.md) found 22 new
randomizer commits, including a useful Beast Toss counter-handshake fix, and
434 reported SNESRecomp commits since the prior pin. Its comparison response
is capped, ExHiROM remains unsupported there, and no new additive eighth-PC
release was verified. The two tracked disassemblies and main mapping/editor
tools are unchanged. Chrono Compendium refresh failed; no old forum timestamp
is claimed as freshly verified.

Earlier review state: Antigravity returned two bounded reviews, independently
dispositioned in [the review note](external_review_2026_10_03.md). Claude Code
job `8cf82ea83be948d89d7af51a80e106fe` timed out after 1,800 seconds with
delivery unknown; do not blindly retry. Grok startup isolation is solved with
a per-child empty USERPROFILE while preserving HOME and the dedicated profile.
Its model catalog and SuperGrok 17%, then 18%, weekly usage were observed.
Andrei confirmed paid extra usage is disabled. Grok returned the IRQ-timing
review and a same-session follow-up; the official export was checked against
all four saved messages. Session: 01a10469-782e-79c1-bd85-71071fc07e34.
Receipts are in private/reviews/20261003b/grok_irq_review_live/ and
grok_irq_followup/. Two initial claims were corrected, not adopted by
consensus. See the full disposition before reusing its advice. Refresh usage
before future dispatch. The old chat reached its native subagent limit.

The fresh continuation has completed the IRQ transition checkpoint. Three
native collaborators and root independently checked the implementation; the
final peer output equals the root reference byte for byte. Two further Grok
messages in the same project session reviewed the model and received our
verified H10 correction/thanks. Fresh usage was 18% before each send, model
options and helper source were unchanged, and the final official export now
matches all eight saved messages. See private/reviews/20261003c/ and the new
review disposition. No reviewer remains running. The next source/observation
closure design is step 9 above; do not restart the completed transition model.

All ROMs, SRAMs, emulator states, raw traces and extracted data stay under
ignored `private/`. Source-controlled outputs contain original tools, tests,
hashes and bounded analysis. No production selector or game hook is installed.

The v3/research checkpoint is GitHub commit
`7ac6499ae484a6598c1727659f18979aaf838a74`. Authenticated commit and branch
reads agree with the remote, and all 16 changed files were downloaded at that
exact commit and matched to committed local bytes. The private publication
receipt is private/test_runs/counters_checkpoint_20261003_publication.json.
At the October 3 final host check, GitLab main remains `a0b17f6`. The
synchronization question remains unanswered. The portfolio was refreshed,
still accurately described the unfinished project, and was left unchanged.
The newer IRQ transition publication receipt is retained separately at
private/test_runs/irq_request_transition_v1_publication_20261003.json; use its
exact commit and downloaded-byte comparisons for this checkpoint's host state.
