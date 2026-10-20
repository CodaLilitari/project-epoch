# Project Epoch development update — October 20, 2026

**IN DEVELOPMENT — NOT YET TRULY PLAYABLE**

Project Epoch is research and original tooling toward adding Schala as an eighth playable character in the SNES version of *Chrono Trigger*. The current diagnostic preview brings together a separate PC07 identity, native party selection, targeted movement and battle poses, a stationary ranged Attack, a world-map sprite, and a dedicated status portrait with corrected first-menu statistics. It is not a finished mod or a complete playthrough experience.

The supported field/battle route remains primarily the **third active party position, slot 2**, with Crono and Marle retained in the first two positions in the principal fixtures. The current menu correction does not repeat every older field, battle, vehicle or save test. Each result below retains its own evidence boundary.

## Revised portrait and correct first-menu statistics

The full status screen now displays Schala's own 48 × 48 portrait, with a calmer expression and closer reference to her original concept art. The current V6 palette-B revision was accepted for this development preview after in-game inspection. It occupies separately appended graphics and palette storage; all seven original portrait assets remain preserved. Its 36 SNES 4bpp tiles are preloaded once during menu initialization under forced blank, without another portrait transfer on every redraw.

The first status opening also now calculates her derived values correctly. The retained test record contains base maximum HP 969, but its battle-reused tail held 1,029, and the original menu startup loop stopped after the seven original characters. The old first panel therefore displayed 608/029 HP and Attack 48. A qualified extension allows initialized PC07 through the original calculation once, producing **HP 608/969, MP 93/93, Attack 236 and Defense 211** before selection. A separate threshold correction makes ordinary HP white instead of falsely red.

These are calculation and display fixes. **Base stats, equipment, level, growth and damage balance are unchanged and remain donor-derived.** The high physical Attack and existing loadout are diagnostic baggage, not the intended finished balance for a pure caster. Focused native checks cover first selection, Crono/Marle controls, return to Schala and menu reopening. Critical-HP boundary cases have static coverage in this latest pass, not a new native low-HP fixture.

[The published portrait screenshot](https://richard-pemberton-research.darkahn.chatgpt.site/projects/project-epoch/schala-portrait-stats-2026-10-20.png) is a plain 4× nearest-neighbor enlargement of an actual native first-selection capture, not a reconstructed screen. The small save-card portrait remains unsupported and skipped. The Tech tab still displays the vehicle's test name, **Wings**, for PC07; that separate name consumer is unfinished. The vehicle's actual stored name remains preserved.

Sources: [menu statistics, portrait and HP-color correction](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_menu_stats_portrait_2026_10_20.md), [dedicated portrait integration](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_status_portrait_2026_10_20.md).

## Targeted running, casting, recoil and KO work

The current body work preserves the suitable installed frames and adds or redirects only the poses needed by traced consumers. Normal running now reuses the existing directional movement art instead of the outstretched casting frames. Lily's horizontal casting preparation and release are installed; selected Red recoil/KO artwork and qualified KO handling correct the observed recoil and disappearance/standing-at-zero-HP problems. Coda's later refinement adds front and rear casting gestures while preserving the earlier successful frames, retail NPC artwork and shared body palette.

The currently supported PC07 Attack now casts from her existing position at both near and far distances. Normal and critical animation routes use ranged projectile/impact packages, retain the engine's target-facing choice, and avoid the physical approach and weapon swing. This is a weapon-free visual action, **not a new magical damage formula or a finished Tech**. Equipment, damage resolution, result handling and action cleanup remain inherited.

The stationary-Attack packet contains twelve native cases: one ordinary-input Schala critical Attack, one ordinary-input Crono control and ten declared animation-context injections. A later four-case front/rear pose packet also injects animation context after damage calculation. These tests show their selected facing, stationary animation and completed cleanup; they are not all naturally occurring unforced Attacks. Exact front palm-to-projectile/impact alignment remains open because the selected front target falls under the battle HUD. The small travel effect is still low contrast in the inspected scene.

[A preserved ordinary-input casting capture](https://richard-pemberton-research.darkahn.chatgpt.site/projects/project-epoch/schala-natural-cast-prior-2026-10-20.png) comes from the earlier `9f678764` stationary-caster build, with no animation-context injection. It records the body pose; the associated report records completed action cleanup. It is not a fresh battle observation on the final portrait/stat candidate.

Sources: [normal-run correction](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_run_pose_correction_2026_10_20.md), [casting, recoil and KO pass](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_battle_pose_pass_2026_10_20.md), [stationary casting Attack](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_caster_attack_2026_10_20.md), [front/rear refinement and limits](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_caster_pose_refinement_2026_10_20.md).

## Party selection, world travel and persistence

The native party menu pages eight logical identities across seven physical display records, retaining Gaspar's presenter. Both reserve pages and selected remove/reselect routes have native evidence. This does not mean eight simultaneous character sprites plus Gaspar. All seven original playable identities remain available; their original records are preserved.

Schala's selected world-map sprite has observed walking in all four directions and both prolonged-idle frames. A separate flying-Epoch route boards, flies, lands, disembarks, visits an Ioka hut, returns to the world map and boards again. The vehicle retains its new landing position through that scene transition. Affected field and vehicle regressions were checked on the casting-refinement parent; the latest menu-only delta preserves those bytes and carries forward those bounded results without claiming a new whole-game replay.

Selected events now insert PCs before NPCs, following existing community work on follower order. This has scoped field regression evidence. It is not a global event conversion or a broad vanilla-versus-mod slowdown benchmark.

A separate normal save and fresh-process battery load preserve a changed slot-0 formation. The design uses a separate 80-byte live PC07 record and three versioned 160-byte sidecars in the original 8 KiB SRAM, with CRC16 and full-slot SHA-256 binding. This provides bounded slot-0 persistence evidence, not universal RAM ownership or complete save-lifecycle support. Other physical save slots, New Game+, erase, mutable recruitment metadata and corrupt native-runtime cases remain unqualified. A supplied emulator state, when packaged, is a convenience for the preview and is not substitute evidence for native save/load behavior.

Sources: [party selection and native save/load](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_party_selection_milestone_2026_10_15.md), [world-map and flying-Epoch milestone](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_worldmap_milestone_2026_10_17.md).

## What remains unfinished

- Other active party positions, broader events/scenes and a continuous full-game playthrough.
- Native recruitment, story integration, pure-caster growth, balance and equipment.
- A complete Tech set, dual/triple-Tech behavior and the separate Tech-tab name consumer.
- The small save-card portrait and separate character/vehicle rename paths.
- Other save slots, New Game+, erase and the remaining malformed-runtime/save-lifecycle matrix.
- Remaining effect alignment, inherited rendering overlaps, sound/art polish and a broad performance comparison.

Prismatic dream-Tech work remains offline color study. The unchanged native Magus Dark Mist effect was observed to understand its palette and blending behavior; no prismatic or new Schala Tech is installed. Existing content, including unused, debug and cheat-accessible items and Techs, is preserved rather than treated as free space.

Source: [current caster direction and preservation requirement](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_caster_direction_2026_10_20.md), [prismatic studies](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/schala_prismatic_study_2026_10_20.md).

## Diagnostic preview package

**IN DEVELOPMENT — NOT YET TRULY PLAYABLE.** The diagnostic package contains one deterministic BPS patch, two matching Mesen preview states, six labeled screenshots, manifests and instructions. No ROM, standalone battery, emulator, raw trace or private correspondence is included.

- [Download the development preview ZIP](https://richard-pemberton-research.darkahn.chatgpt.site/projects/project-epoch/downloads/project-epoch-dev-2026-10-20.zip) — 492,200 bytes.
- [Download the BPS patch only](https://richard-pemberton-research.darkahn.chatgpt.site/projects/project-epoch/downloads/project-epoch-development-2026-10-20-v1.bps) — 58,987 bytes.
- [Installation and state instructions](https://richard-pemberton-research.darkahn.chatgpt.site/projects/project-epoch/downloads/README.txt).
- [Release manifest and per-file checksums](https://richard-pemberton-research.darkahn.chatgpt.site/projects/project-epoch/downloads/release-manifest.json).

Apply the patch to your own clean, unheadered *Chrono Trigger (USA)* Rev 0 input, exactly 4,194,304 bytes, SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`. The output must be 8,388,608 bytes, SHA-256 `d4b6915dc85ef2bc782583de4478f9ed61e07f68fb2dde58b9cced4350ba3117`. This is one clean-to-final patch, not a patch for another hack or an earlier Project Epoch image. The exporter verifies the complete patch roundtrip against the exact target in memory. A separate check using the unchanged, revision-pinned Mesen BPS implementation also produced the exact 8,388,608 target bytes; source, target and patch CRC checks passed. These checks establish artifact consistency and format interoperability, not a new playthrough.

The two final-build states pass fresh-process restoration and controller transitions from status to field and from field to status. They use Mesen `2.1.1+137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`, state format 4. Other builds/emulators are unqualified. Follow the README and use a separate emulator working directory: states contain save RAM and should not replace an important ongoing save. The capture task did not test a new battle continuation or replace the separate native battery save/load result. Earlier-build and injected screenshots inside the package retain their individual labels.

ZIP SHA-256: `9eff5a5b1078b5117c0710e50be502512c0367d27ea7a30584068088e3fd0598`.
BPS SHA-256: `4cb81f836bb06ef74575c00bccc9cb91a8936f2ca5169644e52aee7a0c4c5349`.

Source reproduction: [development release report](https://gitlab.com/codalilitari/project-epoch/-/blob/main/docs/epoch_development_release_2026_10_20.md) and [deterministic exporter](https://gitlab.com/codalilitari/project-epoch/-/blob/main/tools/export_epoch_development_bps_v1.py), with the exact locally held inputs required by their contracts. The source repository does not include the ROM or preview states.

## Attribution and evidence

Direction and in-game review: Andrei Pemberton. Implementation, targeted art refinement, research and evidence reconciliation: Coda through Codex. Horizontal casting contribution: Lily; selected recoil/KO contribution: Red. Additional independent visual/source reviews are credited in their individual reports. Existing community mappings and event-order work are credited and checked; no first-discovery or outside endorsement claim is made. *Chrono Trigger* and its original character artwork belong to their respective rights holders.

This report summarizes source-pinned construction, focused synthetic checks, actual native observations and visual inspection without treating them as interchangeable. It does not claim a finished playable character, complete compatibility or zero slowdown.

Published portrait screenshot SHA-256: `bd01fae992cd997345b669f6f14ed97423bd1a684d13ed7e9fa1dc5fbf04b4e5`. The machine-readable companion records its byte size and dimensions.

Preserved natural-casting screenshot SHA-256: `93fc2c7adab87f7fdb811686aa3a47cc9a97cc751d9e9f3ae60d34a610036cbf`. Its originating build and evidence limits are recorded in the machine-readable companion.
