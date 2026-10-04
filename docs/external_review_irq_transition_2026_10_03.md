# IRQ transition v1 review and disposition

This review belongs to the separately versioned
[IRQ request-transition packet](schala_irq_request_transition_v1.md). The
earlier October 3 review report and private drafts remain unchanged. Review
advice, reproduced calculations and final-source validation are separate claims.

## Native independent review

Three native Codex collaborators separately implemented/audited the register
core, CPU acceptance gates and source/event order. The coordinator inspected
the source, ran the combined suite, and built the composition and metadata.
The event-order reviewer independently compared 12,000 hostile core inputs
with a separately written imperative interpretation of the pinned source.
No state mismatch was found. This is host comparison, not an emulator run.

That reviewer found four missing Exec guards: arbitrary initial event positions,
a duration budget crossed inside recursive refresh, reuse after a refused
VBlank boundary, and master-clock arithmetic outside uint64. All four were
fixed with regression cases and independently retested. The reviewer also
corrected the census wording: inconsistent cached/register enables can make
an otherwise unequal-timer context match vacuously. Those states remain in
the hostile input domain rather than being silently dropped.

The final suite passes 81 tests. Both root and peer generated the same complete
35,737-byte reference, SHA-256
`846a54df9c490cee263bb86cf1b351683262562915eaecb148e3c182bd1686a7`.
The peer rechecked fourteen upstream identities and all eight final original
source/test identities. Its earlier 32,639-byte report is preserved separately
with SHA-256 `b56a52d830ca728119d4c79cdd289f7632e285e5c51bc53e3f530d61fbb9af0f`;
it is not relabeled as a final-source result. The existing 178 phase tests also
pass. No native phase/helper matrix was repeated.

## Grok subscription review

The coordinator used the installed external-reviewers skill
and the existing Grok Build project session
`01a10469-782e-79c1-bd85-71071fc07e34`. A bounded source packet and a subsequent
verification/thank-you follow-up both returned in that session. The current
catalog retained the previously selected `grok-4.7` / `xhigh`; response metadata
named `grok-4.7-build`. These are provider/client labels, not an independent
backend attestation.

Before both sends, the official background CLI usage view showed SuperGrok
weekly usage at 18%. The user's explicit confirmation that paid extra usage
is disabled remained in force. The existing helper, empty child USERPROFILE,
preserved HOME, dedicated GROK_HOME, sanitized environment, startup guard and
tool-denied invocation were retained. No API key, billing setting or normal
account configuration was changed. The first usage-only probe ignored the
attempted quit controls and its exact owned child was terminated after reading
usage; the second probe exited normally. Neither probe made a model call.

Only the explicit project source/text packet was sent. No ROM, SRAM, state,
raw game trace, private history or unrelated account material was included.
The official final export contains exactly all eight saved user/assistant
messages from the four project exchanges. Each message was checked against
its saved packet or answer after newline normalization. The 83,232-byte export
hashes to `c6c79c8b6d90c7bc2e26f54c3a5cc267ce0d486a2daa63187877dea932cd68c9`.
The export and full answers remain private. The separate
[review metadata](../references/external_review_irq_transition_2026_10_03.json)
contains non-secret references and hashes only.

## Findings and limits

1. **Recursive DRAM arithmetic:** Grok agreed that the projected event and
   counter order gives the stated offsets inside the unscripted host model.
   Root and native-peer runs independently reproduce them. Its reply explicitly
   did not claim test execution.
2. **Sharper H10 counterexample:** accepted and independently reproduced.
   A synthetic ten-clock line-boundary callback on the arming line gives
   match +124740, flag +124744 and source +124744. It is now a regression and
   emitted metadata case, marked outside the ordinary callback hypothesis.
3. **Whole-program callback closure:** accepted as an unresolved premise.
   Render/control/SPC, debugger, memory-handler, coprocessor and DMA/HDMA
   bodies are not proved free of additional reentry or register writes.
   Setting a premise boolean cannot authenticate that antecedent. The report
   claims a conditional implication and keeps the game deadline null.
4. **Exact seed and synthetic scripts:** strengthened. The theorem entry
   requires the exact modeled v3 seed and constructs the event cursor itself.
   It has no callback argument. Scripted counterexamples explicitly say the
   ordinary callback hypothesis does not apply. Independent source review
   verifies this final code; Grok's closure reply had only the described change,
   and correctly did not claim it inspected that new entry point.
5. **Missing timer/ack race hooks:** retained as scope limits. The separate
   register core models these operations, but the fixed-register scheduler
   does not schedule arbitrary DMA/debugger writes between nested returns.
   Such an input cannot receive a game deadline. The no-write premise covers
   all relevant writers, not merely CPU stores.

The final Grok reply had no blocking objection to publication with those
conditions and repeated that it had not run the tests or seen the new entry
point. This is a bounded review disposition, not a consensus certificate or
proof of the actual game callback antecedent. The same-session follow-up
delivered thanks for the useful H10 contribution and our independent result.
No reviewer remains running. The earlier Claude Code timeout is preserved as
delivery unknown and was not retried. Earlier Antigravity reviews were reused
as prior context, not reported as new reviews of this implementation.
