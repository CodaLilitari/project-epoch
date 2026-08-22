# Project Epoch Schala supported-slot sprite smoke v0

Status: `verified-runtime` for a private Lucca-slot field diagnostic  
Logical PC `$07`: not exercised  
Production ROM integration: not performed  
Last updated: 2026-07-26

## Result

Schala's current partial sprite packet was fetched and rendered by the
vanilla field path after a recorded Continue and slot-1 load. A calibrated
movement pulse then separated the three party members and showed the original
Schala cardinal-idle packet coherently beside Crono and Marle.

This proves only the following bounded surface:

- the private diagnostic can replace Lucca's supported graphics prefix,
  first four assembly records, field palette colors 1-12, and animation
  mapping;
- a real full-load/field-initialization path reads that diagnostic data;
- the current packet survives at least 3,000 recorded frames and a field
  movement transition without missing objects, exploding tiles, or a pointer
  crash;
- the corresponding clean-ROM control loads vanilla Lucca rather than the
  Schala packet.

It does **not** prove logical PC `$07`, an expanded-ROM allocation, a generic
graphics-bank adapter, a complete animation set, battle staging, or all
fifteen visible palette colors.

## Diagnostic artifact

Builder:

`tools/build_schala_supported_slot_sprite_smoke_v0.py`

Builder SHA-256:
`f346a5e9d20650027303c72b6fbdb8444ff07e7281101c29dadc4ea2e7701231`

Focused tests:

`tests/test_schala_supported_slot_sprite_smoke_v0.py`

Test-source SHA-256:
`bc4183bd3e5be450d3accb260a72def61374b58ec89557697ecd72ff02c8c739`

Write-intent guard:

- validator SHA-256:
  `66448eee38a68e3fda2f4fde7c47e4c3988c8bab9fabd208ae5363b5df6fd6cd`
- strict manifest SHA-256:
  `f019aaf79d472cf6118767877ebb642c4f6762c4df489f6ca9019dda3c51a1ec`
- result: `images-valid`, exact preimages verified, complete diff coverage;
- changed bytes: `3313` inside `3916` declared span bytes, with no undeclared
  mutation.

Private ROM SHA-256:
`6c45548175ed77c93eb17e0461dba344669e0af3b3239eab949b63fe1044e355`

The builder changes no character record, roster state, tech, item, save
layout, or logical identity. It is intentionally marked
`logical_pc_07: false` and `rom_installable: false`.

## Valid replay

The source movie is the established static-diagnostic slot-load movie:

- source BSV SHA-256:
  `16b6b4d517d9089cf249c2a9aaad2d7918a466fe48463df008f0173f32820060`;
- existing input: raw slot 3 at poll frames 1800-1801 and raw slot 4 at
  1950-1959;
- source-ROM SHA-256:
  `4c4ea60434e22c19df0278aeb89ab03f566cdf7323c6fd0a31d2f6739d80666e`.

`tools/rebind_retroarch_bsv_rom_identity.py` changed only the BSV content
CRC-32 and embedded BST1 ROM identity for the Schala diagnostic and clean
control. Its SHA-256 is
`88a35f5b6b773f833f79379aa8a95cca33beb1916e56068273ec104b05a62806`.

`tools/edit_retroarch_bsv_inputs.py` then preserved the existing inputs and
added a non-overlapping raw-slot-3 pulse at poll frames 2400-2579. The helper
now requires the explicit `--allow-existing-inputs` option for this operation
and rejects any overlap with an existing nonzero value.

Input editor SHA-256:
`60c42003b1c554c7a491b1df8daa61ddd4313d9c489b39876b959befe32209e2`

Final movies:

| Run | BSV SHA-256 | ROM SHA-256 |
| --- | --- | --- |
| Schala diagnostic | `251e11e611a88fcb9e87db918d2afa176fce6f0939a015477a37d492fcea3cc3` | `6c45548175ed77c93eb17e0461dba344669e0af3b3239eab949b63fe1044e355` |
| clean control | `08b42f256fe4f60c05082d4948c3d462e6ccc12c2f97243004bedfd710025146` | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |

### Reproduction

All outputs remain below `private/`:

```powershell
python tools/rebind_retroarch_bsv_rom_identity.py `
  private/test_runs/retroarch/probe_confirm_slot4_v2.bsv `
  private/test_runs/schala_supported_slot_sprite_smoke_v0/schala_lucca_slot_sprite_smoke_v0.sfc `
  --expected-source-rom private/test_runs/static/chrono_trigger_lucca_magus_static.sfc `
  --out private/test_runs/schala_supported_slot_sprite_smoke_v0/slot1_load_schala_rebound.bsv

python tools/edit_retroarch_bsv_inputs.py `
  private/test_runs/schala_supported_slot_sprite_smoke_v0/slot1_load_schala_rebound.bsv `
  private/test_runs/schala_supported_slot_sprite_smoke_v0/slot1_load_schala_move3.bsv `
  --slot 2400:3:180 `
  --allow-existing-inputs

& "private\tools\RetroArch\retroarch.exe" `
  -c private/test_runs/retroarch/retroarch-null.cfg `
  -L "private\tools\RetroArch\cores\bsnes2014_performance_libretro.dll" `
  -P private/test_runs/schala_supported_slot_sprite_smoke_v0/slot1_load_schala_move3.bsv `
  -r private/test_runs/schala_supported_slot_sprite_smoke_v0/slot1_load_schala_move3.mkv `
  --sram-mode noload-nosave `
  --max-frames 3000 `
  --verbose `
  --log-file private/test_runs/schala_supported_slot_sprite_smoke_v0/slot1_load_schala_move3.log `
  private/test_runs/schala_supported_slot_sprite_smoke_v0/schala_lucca_slot_sprite_smoke_v0.sfc
```

Repeat the two rebind/edit steps against the canonical private ROM to create
the clean control. The accepted visual evidence is decoded sequentially at
recorded video frame 2540; seeking directly into this old H.264 stream can
produce decoder artifacts and must not be used for comparison.

## Emulator evidence

Runtime:

- RetroArch SHA-256:
  `bb8d1bb0a781c3fab2c4d08dd9d1dd1abe365cd5c339af6353870e73bdd79a76`;
- bsnes2014-performance core SHA-256:
  `4d1708574ae059cb4f43ad995c0276ca03e2693bc6a7612e4e8f4343d48a317d`;
- video: 256x224 H.264 at 60 fps with FLAC audio;
- maximum run: 3,000 frames;
- SRAM mode: `noload-nosave`.

The Schala log reports content CRC-32 `8C66C040`, movie playback, recording,
and `SRAM will not be saved`, with no replay-identity mismatch. The clean log
reports content CRC-32 `2D206BF7` under the same conditions.

Private evidence hashes:

| Artifact | SHA-256 |
| --- | --- |
| Schala video | `a0fca85666e469cf0d11dfddab120b43c6e1c98aa6be39c61c6d0bf308d705b2` |
| Schala log | `95d2fd02a1129e7f77fff2ddd4a53d7e8240d60b06785786a6178b5772a1882c` |
| Schala frame 2540, 4x nearest-neighbor | `63abc7cb062c4b03ee0242eb601476092daae50eb7b71a7fcc7f3a50e466eba2` |
| clean-control video | `f67efacfaea4841d1e8ea065f68424c4a65b054577b69e618515d6f9661275e6` |
| clean-control log | `2874cb6d23f9aec6930cc546c62b54046900b5cc440be06dd1b651030f7ffdef` |
| clean-control frame 2540, 4x nearest-neighbor | `94463e5464e192b90f3640e2fbdc37f10de70889a37d3e90c469fc51d7feab52` |

The recordings and frames remain under ignored `private/test_runs`; they are
evidence, not distributable assets.

## Rejected checkpoint

An earlier zero-input field-idle checkpoint began with sprite state inherited
from the retired Magus-over-Lucca diagnostic. Rebinding that movie to the
Schala diagnostic and clean ROM produced pixel-identical field frames, proving
that the checkpoint could not establish a fresh ROM packet fetch. It is not
used as positive runtime evidence.

This negative control is why the accepted test begins before Continue/load
and performs field initialization after launch.

## Remaining gates

- The field loader copies only `$18` bytes, or twelve character-specific
  colors. Schala's source uses all fifteen visible indices; colors 13-15 still
  require a proved adapter.
- Only four cardinal idle records are installed in this diagnostic. Lucca's
  non-`$FF` animation bytes are deliberately collapsed onto those records.
- No battle graphics, battle DMA, menu portrait, status page, save
  translation, PC `$07` record, recruitment, tech, or item path is exercised.
- The diagnostic replaces supported Lucca data in place. Production work must
  use named expanded allocations and context-specific resolvers without
  overwriting graphics source index `$07` or `$08`.
- Before writing its ignored private ROM, builder v1.1 runs the project-wide
  write-intent audit. The audit verifies the canonical preimages, the complete
  target hashes, and that every changed byte belongs to the named Lucca
  diagnostic spans or the exact checksum field. It rejects all production
  use.
