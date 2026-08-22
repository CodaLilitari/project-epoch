# Vanilla Magus recruitment runtime trace

Status: completed current-core reference trace  
Evidence: `verified-runtime` for the bounded paths and artifacts below  
Production ROM integration: not performed  
Last updated: 2026-07-26

## Result

Project Epoch now has a deterministic reference trace of both vanilla North
Cape branches on RetroArch 1.22.2 with the current bsnes core:

- choosing to fight Magus reaches the native Frog-versus-Magus battle;
- choosing not to fight registers Magus in reserve before name entry;
- accepting the default name opens the native full-party exchange screen;
- the native exchange can then replace Frog with the newly registered Magus.

The decisive full-party transitions are:

```text
before recruitment
active  04 01 03
roster  04 01 03 83 81 84 02 05 80

at Magus name entry
active  04 01 03
roster  04 01 03 06 81 84 02 05 80
joined  FE

after selecting Magus in party exchange
active  06 01 03
roster  06 01 03 04 81 84 02 05 80
joined  FE
```

Before recruitment the joined mask is `$FC`; registration changes it to
`$FE`, setting Magus's vanilla joined bit. IDs `$00-$06` are the seven vanilla
PCs, high-bit-set entries are inactive, and `$80` is empty. Magus `$06` first
occupies the reserve position previously holding inactive Frog `$83`; the
exchange then moves Frog `$04` into reserve.

Every inspected checkpoint preserved the exact `$7E2CA0-$7E2CEF` candidate
canary once, the four-byte front guard remained zero, and the sixteen-byte rear
guard remained zero. The source SRAM and every named disposable SRAM below
remained byte-identical. No ROM byte, Epoch name byte, save slot, or production
allocation was changed. Live Epoch name bytes remained
`a4 c9 c8 bc c1 00` at `$7E2C4D-$7E2C52` through the decision, registration,
name-entry, and party-swap checkpoints.

## Source save provenance

The selected source is Outrunner's SRM listed by
[Zophar's Domain](https://www.zophar.net/savestates/snes/chrono-trigger.html)
as a late-game save after recovering Crono.

| Artifact | SHA-256 | Evidence |
| --- | --- | --- |
| Downloaded archive `zophar_7175_after_crono_return.zip` | `0a49d5634b6739202b9be7f1992b59d285f8589087056c75fd84d92111c80ca2` | `documented` source plus local hash |
| Extracted `ChronoTrigger.srm` | `a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9` | `verified-static` structure and checksums |
| Included `ChronoTrigger.txt` | `9e32a2de4672afc239122d1735e861f94829ec65674f1640cefdd197394a2160` | `documented` source description |

The archive contains only one 8 KiB SRM, one readme, and one emulator frame
file. It contains no ROM. All downloaded and extracted files remain ignored
under `private/downloads/chrono_trigger_saves/`.

`tools/inspect_ct_srm.py` independently validates the exact 8 KiB size, all
three slot magic values, and the game's chained-carry slot checksum. Its
relevant results are:

| Slot | Location | Storyline | Active | Compact roster | Result |
| ---: | ---: | ---: | --- | --- | --- |
| 1 | `$01F0` | `$03` | `00 80 80` | `00 80 80 80 80 80 80 80 80` | valid |
| 2 | `$01F6` | `$D2` | `04 03 01` | `04 03 01 84 83 02 81 05 80` | valid; pre-Magus |
| 3 | `$01D0` | `$D5` | `06 04 03` | `06 04 03 02 00 84 05 01 80` | valid |

The included readme identifies slot 2 as "The New King," immediately before
the second meeting with Magus. Runtime loading confirmed that it reaches the
North Cape overworld with Magus absent from the roster.

Other acquired candidates were retained privately with hashes but were not
used for this trace. The emuWorks files are ZSNES 1.51 states, as their
[source page](https://games.technoplaza.net/snes/chronotrigger/savestates.php)
states, so their emulator-state payloads were not treated as transferable
current-bsnes evidence.

## SRAM and replay isolation

Current bsnes opens a same-stem SRAM itself even when RetroArch reports that
frontend SRAM loading or saving was skipped. Each replay therefore used:

1. a clean, same-stem disposable ROM copy;
2. a same-stem disposable copy of the source SRAM;
3. an isolated save directory;
4. complete SRAM hashes before and after the bounded run.

There is one additional BSV2 trap: a recorded movie's initial state includes
the core's cartridge SRAM. Reusing an older boot-zero movie would restore that
movie's embedded SRAM over the desired downloaded save in emulated memory.
The corrected route recorded a fresh zero-input movie while the selected SRAM
was loaded:

```text
private/test_runs/retroarch/current/north_cape_boot_zero_fresh.bsv
SHA-256 fbdf79557ee217bc217cee8fe7698c5a9e7a9d9794a01d7898272703309aa2bd
frames  3598
CRC32   2D206BF7
BSV ID  6A668FDB
```

Its save-select screen exposed the expected three source titles. The source
SRAM was never used as an emulator output file.

## Decision checkpoint

Slot 2 was loaded normally. After entering North Cape, the route walked to the
north end, faced the sparkle, and triggered the complete Magus/Janus scene.
Dialogue was advanced with bounded, release-separated, single-frame Confirm
inputs. The exact choice checkpoint is:

| Artifact | SHA-256 |
| --- | --- |
| Zero-input BSV2 checkpoint | `b3cf2dee018c7d2f150663bb9a88113b2254d6c12e49358253fe1a8f9c6ec7f5` |
| RASTATE | `2bed44501a3ed2fabdc7788264520c7d5453a0300cf102cb3712207895737667` |
| Raw core state | `4d6870a90f51f6c3c5b4fd889f92d3a5dfa7ff9c17c8d7b78ac32c9f20706b22` |
| Screenshot | `0e272c1b0c4ffa43bb81f1effb1137fa62c6640604f2a25fcc527f87342e9385` |

Runtime anchors are location `$01AC`, storyline `$D3`, active party
`04 01 03`, and roster `04 01 03 83 81 84 02 05 80`. The default choice is
the fight branch.

## Fight branch

`north_cape_decision_fight_yes.bsv` adds only one Player-1 Confirm value at
frame 200 and hashes to
`ee061357b0a6923d5d6f2cee52e3943e10eaad95dd133aa0503f085f3721e16a`.
Bounded dialogue checkpoints then reach the actual narrative encounter:

| Artifact | SHA-256 |
| --- | --- |
| Final prelude replay | `65f617eac8a0f783c1a21ddf07a40779f515f837d6be46ec055f1f73e818c6c7` |
| Battle RASTATE | `3452ce75a5f2e39305044c210cd9643bba00322d26e810157fd46087dc844fda` |
| Raw battle core state | `6b4ec897c6967e22836773f7662ca466fa63ac651242f2d739c842b1594fe59c` |
| Battle screenshot | `ff61466a9c63040b00ee15728b253aa76a2193d6881a63e3802ddfd4cd3a6460` |
| Zero-input battle checkpoint | `9d995f2a346eef5ed42b2c53656dd63cad8fe5eee746b2b13bb665a2c292d131` |
| 600-frame idle RASTATE | `dd53b89b785ddd039bb3d2360cd97caf798f5f29f742bcec68a4ad7566890b78` |
| 600-frame raw core state | `3823c13e16b7e9b1742246c59c2adc603180cc994acba97ff81703ba8e10736c` |
| 600-frame screenshot | `e9a35a682c603c0d248835754bd1ec15b0bddcde5dd1b3cfdb05c37d7a4dfba3` |

The screen visibly contains Frog's native battle command menu and Magus as the
opponent. The staged battle formation is `04 83 83`, which is expected for the
solo duel. This is ordinary location-event encounter evidence and supersedes
the old synthetic field-object launch for encounter semantics. Replaying the
zero-input checkpoint for 600 frames remains in the native battle; Magus's AI
acts and Frog's HP changes, while the canary, both guards, joined mask, Epoch
name, and disposable SRAM remain exact.

Down at frames `60-63` followed by A at `64-67` opens Frog's native Tech
submenu with Heal, Leap Slash, and Water 2 visible. The accepted movie hashes
to `d62df86f2915e9d1f09dab37f5895fbbe466f54e26032fa69ac7a07f1d3c4c7c`;
its RASTATE hashes to
`20ba12597bf4644a90c1cbe44971c94cc600d0959de8149660284cf177fa6a6d`.
No tech is selected or cast. A separate matched 1,200-frame A-only run is not
attack-resolution evidence: Magus remains `6666/6666` HP in both it and the
same-timing zero-input control. It instead proves the first A stops at target
choice. Releasing input for four frames and pressing A again completes the
normal attack. At the matched 1,500-frame endpoint, the accepted two-A route
has lowered Magus to `6137/6666` (529 damage) and returned to the stable command
menu, while the zero-input control remains `6666/6666`. The two-A movie hashes
to `b82d9bc969544e5c4a07f005c456b395259187fedea6b7bd4cd7d92469d76cdd`;
its RASTATE hashes to
`192eb14c9344e808ad3167caa3fb27af016272c824032011f5cbd27bb0740633`.

A separate bounded extension of the Tech-open route presses A at frames
`620-623` to select Heal, releases for four frames, and presses A at `628-631`
to confirm Frog. At frame 1,500 the matched no-cast control remains in the
Tech menu at `837/999` HP and `99/99` MP. The cast route has returned to the
stable command menu at `999/999` HP and `97/99` MP, with Magus unchanged at
`6666/6666`. This proves one native Heal selection, self-target confirmation,
2-MP charge, and effect cycle. The movie hashes to
`663e050eec4a26d1041f7444e1954e8202d1ef06766e9609338c33cfee8b4c25`;
its RASTATE hashes to
`9e6218033a97159056bf7e2988efd7e1704bbd4f67f9e290f9105283be799638`.

## Recruitment branch

The branch selector replay presses Down for two frames at frame 200 and
Confirm for one frame at frame 500. It hashes to
`1040febd0a8efe7267b4bfae8e5fa1e24ec93aea057acdb0430274033f2d08f4`.
After the party walks away, Magus calls them back and the route reaches name
entry.

At name entry, before accepting a name:

- RASTATE SHA-256:
  `f0b1e43777b0d26f49f3a3ef63031b51c97f9b21e1a38918248edc81542e7445`;
- raw core-state SHA-256:
  `b976fad8aac50626cfc8f7842d385ad2360fe5b15d54b6d0ee01ff5287ae0f37`;
- screenshot SHA-256:
  `06ef98cf2b55ecf66d38ee72f3d69d0d9ef958c3a30e6d631e789946fb29aaf9`;
- active party: `04 01 03`;
- roster: `04 01 03 06 81 84 02 05 80`;
- joined mask: `$FE`, changed from the pre-decision `$FC`;
- Epoch name: `a4 c9 c8 bc c1 00`, unchanged.

This proves Magus is already registered in reserve before the name is
accepted. A one-frame Player-1 Start at frame 200 accepts the default name:

| Artifact | SHA-256 |
| --- | --- |
| Name-accept replay | `b81a82287aface40bb59de34d0089900af2b5dfc77de053aee9d3153e58cfc74` |
| Party-exchange RASTATE | `82335862d34aa8842e6cfc08562e3fee1cd1a0f0276fa48df2497685ba625542` |
| Raw core state | `10ab080cd7b74ecd75057d647b43af35ea85f44d6f5ca956285b25b248b572aa` |
| Screenshot | `5a38c2f78013e04f6ce8308967ee8d28acb2f965765e56b4240c6a9e1c7c9e01` |

The resulting screen is the native full-party replacement UI. The calibrated
swap replay then uses Confirm at frames 800-801, Left at 1200-1201, and
Confirm at 1600-1601:

| Artifact | SHA-256 |
| --- | --- |
| Magus swap replay | `8e3f26b8af01b3cf0e1fc56df10f38ac1dfa4a6d745ceab23d04ba67e9cf7197` |
| Post-swap RASTATE | `083ebcad17fc2dd3ecf793b4562900e493f344c294bacd8b798c3d5b288a3498` |
| Raw core state | `bd1f33db5da744908fbe1ecb6138cf1488bcb129b200501c270123530e9eaa1a` |
| Screenshot | `49577e3406306c170024c1dd33f3e873873d3e731031f1a7af5405424f6f0687` |

The final active formation is Magus/Marle/Robo (`06 01 03`), with Frog in
reserve. The disposable SRAM still hashes to the unmodified source value
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

## What this requires for Schala

The trace does not prove that vanilla ID `$07` is a safe eighth PC. It proves
the user-facing sequence and gives the Project Epoch adapters a concrete
behavioral target:

1. initialize Schala's independent record and validate persistent state;
2. query active-party capacity explicitly;
3. on a full party, register logical PC `$07` in reserve without displacement;
4. run Schala's independent name-entry adapter without touching Epoch at
   `$7E2C4D-$7E2C52`;
5. open the eight-character-safe party exchange;
6. commit joined state, starting grants, and persistence atomically;
7. on an open-party branch, use active insertion only after the capacity query
   proves a high-bit-set slot exists.

Registration before naming is useful reference behavior, but Project Epoch
must remain fail-closed: a reset or interrupted flow must not leave a
half-initialized PC `$07`, duplicate grants, or a joined bit that disagrees
with the sidecar and roster.

## Reproduction and retention

Validate the source SRAM without loading an emulator:

```powershell
python tools\inspect_ct_srm.py `
  private\downloads\chrono_trigger_saves\zophar_7175_after_crono_return\ChronoTrigger.srm `
  --require-valid-slot
```

Inspect any BSV2 or captured state with:

```powershell
python tools\inspect_retroarch_bsv2_inputs.py <movie.bsv>

python tools\inspect_current_wram_candidate.py <state.auto> `
  --srm <same-stem-disposable.srm> `
  --slot 2 `
  --require-canary
```

Replay only against isolated same-stem disposable ROM/SRAM fixtures with the
pinned RetroArch/core hashes in
`docs/current_emulator_replay_harness_2026-07-26.md`. The 95 accepted
party-exchange, North Cape, bounded battle-control, native save/reload, and
Lavos-route artifacts plus the later valid-sidecar compatibility controls are
explicitly listed in
`references/current_emulator_accepted_artifacts_v1.json`; failed, exploratory,
and unreplayed calibrations are intentionally absent. Build the local curated
manifest with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec references\current_emulator_accepted_artifacts_v1.json `
  --output private\test_runs\retroarch\current\accepted_evidence_manifest.json
```

The resulting
`private/test_runs/retroarch/current/accepted_evidence_manifest.json` has
SHA-256
`8bfef666d0f2133a37c1f60c2dab0bf216f04c7834d4396fd0e02ed1d37f3c15`.
Do not distribute the private evidence tree or any downloaded save.
