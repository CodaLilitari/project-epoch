# Project Epoch: Schala appears as PC07

October 13, 2026. Status: instrumented SNES prototype; the playable-eighth-character goal remains active.

Schala's retail sprites and full six-letter battle HUD name now run as logical
PC07 in a continuous field-to-battle preview. The seven original characters
retain their separate records. Epoch's stored name and captured SRAM remain
preserved. This is a concrete appearance milestone on the SNES route.

The implementation adapts the NPC graphics to the PC readers instead of
assuming their formats and bank behavior are interchangeable. Missing numeric
animation selectors receive copies of retail Schala poses. These are fallback
poses, not newly authored attack or casting animations. The observed preview
includes field movement and battle rendering and stops before a player Attack.

## Four distinct observations

| Observation | What the recorded run establishes |
| --- | --- |
| Field-to-battle handoff | Independent logical PC07 moves with Crono and Marle, reaches the prepared destination event, and enters the native battle handoff. |
| Ordinary Attack | On the earlier donor-appearance image, PC07 completes an ordinary critical Attack for 962 damage, returns through cleanup, and becomes ready again. |
| Schala presentation | On the separate presentation image, retail Schala renders in field and battle with the full visible name **Schala**. All 96 sampled presentation windows and eight tile-copy/control windows pass review. |
| First escape record commit | On the earlier donor-appearance image, an authored escape-enabled encounter reaches the native 240-byte party copy. PC07's live HP changes from 968 to her own battle result, 608; PC00 and PC01 receive their separate 739 and 603 HP. |

These observations are complementary. They are not one combined Schala
appearance, Attack, escape and save run. The escape evidence stops at the first
record commit; later max-HP/status processing, the second commit, and complete
field restoration remain outside it.

## What is preserved

The Schala presentation run checks the seven original records, all 48 original
stored-name bytes including Epoch, original body palettes, and captured SRAM.
The escape run permits the legitimate battle updates to active PCs00/01 while
preserving inactive PCs02-06, all stored names, and all 26 SRAM snapshots.
Logical PC07, a graphics source index, and the vehicle's name selector are
separate namespaces. These checks do not establish boarding, time travel or
every vehicle interaction.

Both diagnostics use 4,642 explicitly recorded debugger preparation
write/readback pairs to establish the selected record, roster, compatibility
storage and authored event fixtures. The ordinary actions and observed native
record copies are game execution. No CPU-register or escape-result injection
is used. Native recruitment and persistent installation of that setup remain
work to do.

## Review and corrections

An initial presentation validator incorrectly expected a temporary HUD buffer
to retain name cells after the command menu reused it. The original rejection
is preserved. An additive temporal validator checks the actual write/readback
windows, and visual inspection establishes the complete six-letter name; no
unrecorded VRAM-upload ledger is claimed. Independent review and root
reproduction qualify the same preserved run.

The escape run has a separate independent review of all 240 source-read,
destination-write and immediate-readback triples, the controller-driven escape
counter, source identities, and preservation snapshots. Its 402,532-row trace
is private. The public report publishes the result, hashes and reproduction
limits, not the game data.

The field and Attack public reproductions now have additive v2 adapters for
their exact archived ROM-write guard. Earlier live-path checks correctly
refused after the guard grew new presentation contracts. The adapters preserve
the old source bundles and evidence; they do not silently waive source drift.

## Next implementation boundary

Complete the selected native battle-to-field return, then implement and prove
a normal save and a genuine cold load of the independent PC07 state. Menus,
Techs, recruitment, complete animation coverage, victory/progression, broader
scene coverage, and the full vehicle/interrupt matrix remain open. No general
playable release or absence-of-slowdown claim is made.

The SNES route remains primary. The separately documented Ghidra and
recompilation tests provide a comparative fallback, not evidence that a native
PC port already supports this character.

## Reports and reproducible metadata

- [Field-to-battle report](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/pc07_field_battle_handoff_2026_10_13.md) and [v2 reproduction](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/pc07_field_battle_handoff_2026_10_13_v2.md).
- [Ordinary Attack report](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/pc07_first_attack_checkpoint_2026_10_13.md) and [v2 reproduction](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/pc07_first_attack_checkpoint_2026_10_13_v2.md).
- [Schala presentation report](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/pc07_schala_presentation_2026_10_13.md).
- [First escape commit report](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/pc07_first_escape_commit_2026_10_13.md).
- [Practical recompilation and Ghidra tests](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/recomp_tool_practical_assessment_2026_10_13.md).
- [Machine-readable milestone index](https://gitlab.com/codalilitari/project-epoch/-/blob/main/references/pc07_milestone_2026_10_13.json).

Exact native reproduction requires the pinned private fixtures and locally held
game inputs. The public repository is not a self-contained game distribution.
Original source builders, guarded write contracts, focused host tests and
curated evidence metadata are published; ROMs, saves, emulator states,
extracted payloads and raw traces stay private.

Direction and supplied portfolio screenshot: Andrei Pemberton. Implementation,
research and evidence review: Coda through Codex, with independent AI review.
Existing community mappings by Mauron, Vehek and JLukas, and event insertion
work in Temporal Redux / Jets of Time, are credited and rechecked. This report
makes no first-discovery claim for those mappings. Chrono Trigger and its
character artwork belong to their respective rights holders.
