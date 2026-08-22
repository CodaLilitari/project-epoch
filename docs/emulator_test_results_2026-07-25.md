# Emulator test results - 2026-07-25

## Outcome

The v1 Lucca-to-Magus static diagnostic is now `verified-runtime` through
boot, Continue/save-select, save-slot load, field rendering, and field
movement on the recovered Lavos save.

The quarantined provisional-runtime hook build also boots and reaches the
field, but its intended `$50`-byte Magus-to-Lucca live character-record copy
does not persist at the field checkpoint. That is a verified negative result.
Subsequent static reconstruction proves the shim overwrites enemy-reward data
and the hook site is field sprite/animation setup, so the experiment is now
retired as known unsafe.

This is still the supported Lucca slot `$02` acting as a Magus-clone
diagnostic. It is not logical PC `$07`, an eighth roster slot, or Lily as an
independent character.

## Test environment

- RetroArch 1.7.1:
  SHA-256
  `bb8d1bb0a781c3fab2c4d08dd9d1dd1abe365cd5c339af6353870e73bdd79a76`
- bsnes2014 Performance core:
  SHA-256
  `4d1708574ae059cb4f43ad995c0276ca03e2693bc6a7612e4e8f4343d48a317d`
- Canonical clean ROM:
  SHA-1 `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- Recovered Lavos SRM:
  SHA-256
  `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`
- Static patched ROM:
  SHA-256
  `4c4ea60434e22c19df0278aeb89ab03f566cdf7323c6fd0a31d2f6739d80666e`
- Provisional-runtime patched ROM:
  SHA-256
  `b0538af193fbac24773a78b593de12fed47eb63e7e4dd70cfb11994f9f5e8f43`

All ROMs, saves, BSV movies, videos, screenshots, and emulator states are
under ignored `private/` paths.

## Safety controls

- Both builds used isolated ROM and SRM copies prepared by
  `tools/prepare_emulator_test_runs.py`.
- The preparer now emits only the static supported-slot diagnostic by default.
  Reproducing the retired enemy-reward-overwriting runtime experiment requires
  the explicit `--include-retired-unsafe` flag.
- RetroArch used an isolated configuration with configuration persistence,
  SRAM autosave, audio, video display, and physical input disabled.
- A separate no-SRAM configuration enabled only an exit savestate for the
  paired live-record comparison.
- Test playback used SRAM mode `noload-nosave`; the BSV's embedded state
  supplied the disposable SRM image.
- No in-game save was made.
- The canonical SRM and both disposable SRM copies retained SHA-256
  `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.

## Checkpoint results

| Checkpoint | Static v1 | Provisional runtime v1 |
| --- | --- | --- |
| 600-frame boot | Pass, exit 0 | Pass, exit 0 |
| Continue/save-select | Pass | Pass |
| Lucca row portrait | Coherent Magus portrait | Coherent Magus portrait |
| Lucca name and level | Still Lucca, level 54 | Still Lucca, level 54 |
| Load slot 1 | Pass | Pass |
| Field graphics | Coherent purple-caped Magus-like third sprite | Pixel-identical to static at frame 2500 |
| Field movement/follow | Pass for the recorded movement segment | Not separately extended beyond the matching field checkpoint |
| Live Lucca record after load | Original Lucca record | Original Lucca record; clone did not persist |
| Main menu/techs | Not reached at this final-battle save point | Not reached |
| Battle | Not reached | Not reached |
| In-game save | Deliberately not attempted | Deliberately not attempted |

The save-select still saying `Lucca` while showing Magus is expected for the
static diagnostic: portrait and ROM lookup layers are cloned, while the
live/save character identity remains Lucca.

## Runtime-record evidence

Paired bsnes2014 automatic states were captured at the same deterministic
field checkpoint:

- Static state SHA-256:
  `399def4c7e35baad1b5d2cedc9b18176c5aea985e9be7c1c2d6fe6d00bfde68c`
- Provisional-runtime state SHA-256:
  `ed19aab0af6a2cedfd0331ffd53f04d90c443334f03d0415b44fdeb3a07b7e32`

`tools/inspect_clone_state_records.py` found:

- the recovered save's Lucca and Magus records differ in 56 of 80 bytes;
- live Lucca record at state offset `28995`;
- live Magus record at state offset `29315`;
- offset delta `0x140`, matching `$7E26A0 -> $7E27E0`;
- the provisional-runtime state's live Lucca record is still byte-for-byte
  the original Lucca record.

The byte-matched static reconstruction identifies `$CC:E980` as part of
`Field_SpriteAnimComputeBase`, not record initialization, and identifies
`$CC:63F6-$CC:642F` as part of `EnemyRewardTable`. A clean boot and matching
field graphics were not evidence that the hook worked; the artifact is
retained only for reproducibility.

The static and provisional-runtime screenshots at video frame 2500 are
byte-identical:

SHA-256
`9874bfff2370158e02f619279dd6db1a5de4a9a88c9c956fb861e861a99d9a52`

## Relocated-WRAM transition checkpoints

The `$7E2CA0-$7E2CEF` compatibility-block canary was carried through three
additional native engine states:

- full main menu, zero-input checkpoint BSV
  `c2ccf3523fca23f7a0294527b6dad50081c00156d2a70b072faa47b19838c79b`;
- party exchange after an actual Crono/Frog roster swap, zero-input checkpoint
  BSV
  `9ac8f2eec7629e1a53ba8a45bb1c79520c866c836472bebbdcb68369acf73de8`;
- battle engine, zero-input checkpoint BSV
  `f11688de39206cde3a7655e945fa035b7f0b150ba6ee1160fbeb905dfc6fc689`.

Each state was replayed for 600 frames against the unchanged static ROM with
SRAM loading and saving disabled. The canary remained exact once at state
offset `30531`, and its four-byte structural front and sixteen-byte rear
guards remained zero. The party test changed `$7E2980` from
`00 01 02 82 80 04 03 06 05` to
`04 01 02 82 80 00 03 06 05`, proving a real native swap.

The battle was initiated diagnostically with an already loaded field object.
It proves entry into and continued execution of the real battle engine, but
not ordinary encounter semantics. Attack, tech, death/victory, and field
return remain separate tests.

### Battle-menu input calibration

Historical erratum (2026-07-26): the twelve legacy editor positions were
two-byte groups in a one-byte callback stream. They covered the six
even-numbered joypad IDs on player 1 followed by the same six IDs on player 2;
they were not all twelve player-1 controls. Player-1 slots 0-5 changed state
and player-2 slots 6-11 matched idle. The checkpoint and canary results remain
valid, but the original input-coverage description was too broad.
Runtime latches correlate slot 2 with Up, slot 3 with previous-PC/Left, and
slot 4 with Confirm. Confirm advanced the native menu state from
`$06E2/$06E6/$06E7 = 11 00 55` to `12 02 54`.

All twelve runs preserved the exact `$7E2CA0-$7E2CEF` canary and zero guards.
No ordinary attack, queue insertion, damage, victory, or field return was
proved, so this is a menu-input calibration result rather than a battle-action
pass.

## Inert ExHiROM control checkpoint

The inert 8 MiB ExHiROM scaffold was run for 3,600 no-input frames with the
same RetroArch/bsnes2014 environment. Two identical clean-ROM runs provide a
control for nondeterministic state bytes.

`tools/compare_bsnes2014_states.py` reports:

- BST1 state length `329133` for all three runs;
- byte-identical 128 KiB WRAM between clean run 1 and the inert image;
- five non-identity payload differences in the inert comparison;
- those exact five offsets also vary between the two clean runs;
- zero unexplained payload differences;
- `equivalent_at_checkpoint: true`.

State SHA-256 values:

- clean run 1:
  `22f6727119d09eef2e0037d55562bd883a93011afdb49905f69fd4692ae8578d`;
- clean run 2:
  `ab6184ba053339d080199190fb9739904598562cd291358a2c817a55c2b610cc`;
- inert:
  `47a0604c1fec3e90cbe9ee41b0a6a59c81d5ad97d5c91f28b3b752aeffbf7367`.

This is a bounded `verified-runtime` expansion check, not a PC `$07` result.
The remaining reset, save-write/translated-load, New Game+, long-run attract,
and second-emulator matrix is still mandatory.

### Inert ExHiROM transition-state replay

The inert transformation was also applied to the supported-slot static base
used by the three relocation-canary checkpoints. The ignored 8 MiB target is
SHA-256
`2dc889e565086cf1bcd8676f58d3428a4c3a65709839ab121f622a0db654836f`
and CRC32 `73E36AF4`.

`tools/rebind_retroarch_bsv_rom_identity.py` changed only each movie's BSV
content CRC32 and BST1 ROM-SHA wrapper. It verified that the serialized core
payload and input bytes were unchanged; all three input streams remain
SHA-256
`b30a8aa73669089db966896deb88bd2ac39774158c98a8e6ff78ed71575b541f`.

After 3,600 frames, full-menu idle, post-swap party-exchange idle, and native
battle-engine idle each:

- preserved the exact `$7E2CA0-$7E2CEF` canary and zero guards;
- saved without CRC or state-save warnings;
- matched a repeated 4 MiB control across the entire serialized core payload
  after excluding the expected BST1 ROM identity field;
- matched all 128 KiB of WRAM byte-for-byte;
- passed `compare_bsnes2014_states.py --require-equivalent` with zero
  unexplained differences.

| Checkpoint | Rebound BSV SHA-256 | ExHiROM output state SHA-256 |
| --- | --- | --- |
| Full main menu | `12d2e4f2a427eab8194917e1710658035de08318c224ec80e9b9a97e232de475` | `aa434a4a9b3cd0e6a8a80c26f75a0c3ba387fe64e49a7eda211ec6262f9c8efa` |
| Post-swap party exchange | `799f28fcc544be657d727e31c9277996040eb445f9922b3e44627604e15d2e4a` | `2d1c3e3a96e468f43a8e9156e843d97738164b8fe5f9144cfb498161a7e61da7` |
| Native battle engine | `2f7124b134d587d3b71148b5f8babf2d74ff2751a1bbae8753ffccd392f4ca1e` | `e7a7254c2ac0cf4b0df85a7342b61ebcc16cbaa1eaa76b23ddf200aa2d98523e` |

These are state-replay checkpoints, not end-to-end transitions. They do not
yet cover menu-opening input, a normal encounter, attack/tech execution,
victory/exit, or PC `$07`.

### Inert ExHiROM all-slot Continue replay

Three movies with real controller input selected Continue and loaded slots 1,
2, and 3 on the inert 8 MiB diagnostic base. Each 3,600-frame ExHiROM result
matched its repeated 4 MiB control across the complete serialized payload and
all WRAM after excluding ROM identity. All comparisons have zero unexplained
differences and pass `--require-equivalent`.

| Slot | Rebound BSV SHA-256 | ExHiROM state SHA-256 |
| ---: | --- | --- |
| 1 | `ac21c636c3ba0b25d8852f3ce58c16d00bad44cc0d721a156857953e95c703b0` | `3db6225a444a5a4ed4ebea6fb84268f080bb43f35c721610c576ec8a7c5b58b0` |
| 2 | `684267874c602e5d3264fee1c15cfb271b8f1e0fcc98548aed793bdfe4bd0cf6` | `e0fa3dd2b5e0a47de4ca865b8a98917dd50fe30cd5f261e19f4ff2429ab15ac2` |
| 3 | `1c076021d3395b7a8959304211d615349528342be013c35799413f4bcd408878` | `bb44df4f4dd502f11f265ac5f1d8921d87e0547f3d921587cd429b56188e0050` |

The `$7E2CA0-$7E2CEF` candidate block is all zero in every output, exactly as
in the 4 MiB controls. This is the expected cold-initialization negative
control; it is not canary-preservation evidence. The result verifies the
inert mapping through title input and vanilla full load, but not Project Epoch
save translation or sidecar restoration.

## Key local evidence

| Artifact | SHA-256 |
| --- | --- |
| Static save-select BSV | `f5abf149de01d3b663c3444b851da49af3bc1e7118b1590de59859a369169d80` |
| Static save-select video | `d3e06048317efa322a0e92bc9451870f9bc445f91b4aec8a0c0a57d41a4b3ba8` |
| Static save-select frame | `123f220656e84c70ca1156ac9d3cb0697883f2f0141308e1a92499652ee6f1b7` |
| Static slot-load BSV | `16b6b4d517d9089cf249c2a9aaad2d7918a466fe48463df008f0173f32820060` |
| Static field video | `06e4e8fff4cc0083e33853ab936ea8bac3ad70d9c1bbf698a3da79e8913989f9` |
| Static moved-party BSV | `34c2572dabb2e4a9f9630b4b7c506f0ea4ccbea0871a0c37ca5c79658405f1d4` |
| Static moved-party video | `222c01f6b8215ffda88f417dc90112e56ea60c8a0cbe2e05f3dd2a5194836a34` |
| Provisional-runtime slot-load BSV | `3924f8bae1f7fb1e73fdc92f46f9e9c910dbcc3f8736538d0bb8798c8343833d` |
| Provisional-runtime field video | `2b519dfbfff4a20f2c3b2f6534f8d19f387da1dc4f3ba29d9f9d61d9172b811a` |

## Automated checks

All 148 unit tests pass:

- 11 recovered clone builder/save/IPS checks;
- 44 BSV, canary, state-inspection/comparison, and ROM-identity-rebinding
  checks;
- 14 sidecar and ten-descriptor save-layout checks;
- 34 command-layout plus tech, item, and recruitment-content checks;
- 13 ExHiROM scaffold and inert-ROM preparation checks;
- 6 canonical location-event item-reference audit checks;
- 26 original gameplay-sprite and portrait build/originality checks.

All 22 source-controlled Python tools also pass syntax compilation.

## Next engineering step

1. Keep the runtime shim retired and use only named expanded-ROM allocations
   for future code.
2. Enumerate record, party, save, menu, equipment, graphics, and tech callers
   from the byte-matched static reconstruction.
3. Build explicit logical-ID adapters for Schala rather than looking for a
   replacement global copy hook.
4. Repeat menu, tech, equipment, basic-attack, battle, and battle-exit
   checkpoints on a save/location where those systems are available.
5. Only after the supported seven-PC clone surface is complete should work
   activate logical PC `$07` as an independent Schala slot.
