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
   registry has a much larger envelope. A new read-only resolver-phase
   observer is being prepared to expose pending interrupt and DMA/HDMA state;
   no phase admission rule or game insertion is approved.

All ROMs, SRAMs, emulator states, raw traces and extracted data stay under
ignored `private/`. Source-controlled outputs contain original tools, tests,
hashes and bounded analysis. No production selector or game hook is installed.
