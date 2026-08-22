# Recovery state - 2026-07-25

## Source conversation

- Title: `Chrono Trigger 8th Character`
- Conversation ID: `69f1efdd-b298-83ea-a50e-0e60834641be`
- Last recovered engineering step: Lucca-to-Magus ROM-only clone diagnostic v0.

## Recovered stopping point

The project deliberately moved away from directly patching logical PC `$07`.

The controlled baseline became:

> Can the ROM clone all known Magus character data over Lucca, without modifying the save file?

The recovered v0 patch attempts:

- four graphics-source table entries, Magus ID `$06` to Lucca ID `$02`;
- five single-tech table families for eight techs;
- Magus portrait palette over Lucca;
- a runtime hook at file `0x0CE980` with code at file `0x0C63F6`;
- Magus runtime record `$7E27E0-$7E282F` over Lucca `$7E26A0-$7E26EF`;
- Magus-to-Lucca tech-progress and learned-mask bytes. These are
  `$7E2836->$7E2832` and `$7E283D->$7E2839`, structurally corresponding to
  save-slot `$0436->$0432` and `$043D->$0439`.

## Verified during recovery

- Clean ROM size: `0x400000`.
- Clean ROM SHA-1: `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`.
- Original `ctsave16-lavos.zip` recovered under ignored private input;
  SHA-256 `6c95375fd3b3d5ce568cf76bdfcdc5c475bea8ff5059d9ce63d36d8bdf364ad4`.
- Extracted `chrono_trigger.srm` size: `0x2000`; SHA-256
  `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.
- The save-editor “record 7/Epoch” interpretation is not a valid PC record.
  In the recovered save, `$0430-$0436` are the seven PCs' tech-progress
  counters (`08 08 08 07 05 03 03`) and `$0437-$043D` are their learned-tech
  masks (`FF FF FF FE F8 E0 E0`). Preserve the full `$0430` region while the
  remaining bytes are mapped.
- Recovered v0 builder reproduces the supplied 510-byte IPS exactly.
- Supplied and reproduced v0 IPS SHA-256:
  `39b9a3ea6c7354f5ecfcfe312a79a97fd29ece635deb3beb8e4468e5581a2626`.
- The portrait layout is seven contiguous `0x200`-byte 4bpp tile blocks:
  Marle `0x3F1180`, Lucca `0x3F1380`, Ayla `0x3F1580`,
  Crono `0x3F1780`, Frog `0x3F1980`, Robo `0x3F1B80`,
  Magus `0x3F1D80`.
- Magus portrait tiles and palette can therefore be cloned independently to Lucca.
- Three verified per-PC attack-selector families begin at `0x0D4000`,
  `0x0D4007`, and `0x0D400E`. The Lucca destinations are `0x0D4002`,
  `0x0D4009`, and `0x0D4010`; Magus sources are `0x0D4006`, `0x0D400D`,
  and `0x0D4014`.
- File `0x0D400E` is overloaded: PC `$07` reaches it through the normal
  family and Crono reaches it through the critical family. It is occupied.
- The verified TP-learning table begins at `0x0C26F8`; Lucca's `0x10`-byte
  block is `0x0C271A`, and Magus's is `0x0C275A`.
- Documented menu element icon: Lucca `0x02A2C8`, Magus `0x02A2CC`.

## Open runtime questions

- Resolved: `$CC:63F6-$CC:642F` lies inside `EnemyRewardTable`,
  `$CC:5E00-$CC:64FF` (256 seven-byte records). The zeros are data, not a
  code cave. The runtime artifact is known unsafe and retired.
- Resolved: `$CC:E980` is part of `Field_SpriteAnimComputeBase`. It reads
  active-party IDs and derives field graphics/animation indexes; it is not a
  character-record initialization hook.
- A deterministic bsnes2014 run now proves the hook does not leave Lucca's
  live `$50`-byte record cloned at the loaded-field checkpoint. The static
  reconstruction explains why this site was the wrong architectural layer.
- Whether the clone remains stable in field, party exchange, and battle.
- Static reconstruction identifies `SaveSlot_Write` at `$FF:F9FB`,
  `SaveSlot_LoadRegions` at `$FF:FAA3`, three `$A00` slot bases, eight source
  regions, and a checksum over the whole slot. The retired hook's
  `$7E2832/$7E2839` writes would serialize at slot `$0432/$0439`.
- Which variable-length status-menu and battle-menu tech text structures must also be cloned.
- Which equipment, critical-hit, and battle animation selectors remain keyed to Lucca.
