# Project Epoch Schala current-body packet audit v0

Status: partial current-source packability verified  
Evidence: `verified-static` for source identity, native-shaped packet fit, and
exact serialized reconstruction  
ROM integration: not performed  
Runtime verification added by this audit: none  

## Outcome

The ten unchanged gameplay-foundation frames and six unchanged Glass Focus
basic-Attack body poses fit together in one deterministic, native-shaped
partial packet:

- 16 provisional source records, each exactly `$28` bytes;
- 91 deduplicated tiles including reserved transparent tile 0;
- 90 nontransparent unique tiles and highest tile index `$005A`;
- `$0B60` bytes of raw 4bpp graphics;
- `$0280` bytes of assembly records;
- the existing `$20`-byte gameplay palette; and
- exact reconstruction of all 16 source canvases from the serialized graphics
  and assembly bytes.

The audit is additive. The complete graphics and assembly prefixes for the
previous ten-frame foundation are byte-identical to the accepted packet. The
six Glass Focus body poses add only ten unique tiles and six assembly records.

This result closes an external packet-form question for the already-authored
Glass Focus poses. It does not change the Glass Focus manifest's truthful
internal field `assembly_packability_claimed: false`; that source and manifest
remain unchanged. This independent audit supplies the new bounded evidence.

## Source-controlled artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `tools/audit_schala_current_body_packet.py` | 29,448 | `00db7f71e9c85b5a3efc4b3bccdbc7d7d7407b731f9780ab02a13cfd9fa90789` |
| `tests/test_schala_current_body_packet.py` | 15,462 | `608bff2ee7d7dfb9f5cc2009662afe3f04673ca8377496691ca18e118ddd0fb1` |
| `references/schala_current_body_packet_v0.json` | 11,953 | `c5a04304739e5fac3125cb840e9745bafae0f45b0b2869b4743b5d25c1c1313b` |

The reference report contains paths, IDs, dimensions, counts, hashes, evidence
labels, and explicit nonclaims only. It contains no source rows, pixels, tile
bytes, tile words, assembly bytes, palette bytes, images, ROM bytes, or decoded
copyrighted data.

## Pinned existing inputs

All four existing Project Epoch artifacts are consumed unchanged:

| Input | Bytes | SHA-256 |
|---|---:|---|
| `assets/source/schala/v0/gameplay/schala_gameplay_foundation_v0.json` | 25,193 | `9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2` |
| `assets/source/schala/v0/gameplay/manifest_v0.json` | 5,473 | `6f1475c2945a2f4df922d6f8b4969e346e5846152284742ceb9f04b9bc3e3f65` |
| `assets/source/schala/v0/focus/glass_focus_pulse_v0.json` | 32,967 | `fe7ccfc67c523e2a7edfeba9b14b855b3d14c92d1ef2d46076a6c57ce1765aa0` |
| `assets/source/schala/v0/focus/glass_focus_pulse_manifest_v0.json` | 6,284 | `e14efe2dac41758fca34aeb64019caa7d104be8ac5f6f939c23374b65d597a87` |

The auditor hash-gates these behavior-bearing helpers before importing them:

| Helper | Bytes | SHA-256 |
|---|---:|---|
| `tools/build_schala_gameplay_foundation_v0.py` | 25,402 | `e43f5d5b6fe30c5746ef04822f98f120165ecbea8393143e5b93941fdeb6cf8f` |
| `tools/build_schala_sprite_packet_foundation_v0.py` | 21,211 | `dc264823fdb479fef3c0a0d94e68da40b6bb0e51040c94392e678f970c3c60fb` |
| `tools/validate_schala_glass_focus_pulse_v0.py` | 59,563 | `061a7169f1bbd6c57409fba52b36a4cbf76ff3d9fcd32665b946558feafa9b4e` |

Dependency drift stops the audit before helper execution. The gameplay
manifest is cross-checked against the ten-frame source. The complete Glass
Focus validator and manifest contract are rerun, including the shared palette,
null native/runtime bindings, unbound allocation, and non-installable status.

## Provisional body-frame inventory

The deterministic order is an authoring and packet-audit order only. A
`source_ordinal` is not a native animation frame ID or semantic engine slot.

| Ordinal | Source | Frame | Canvas | Active objects |
|---:|---|---|---:|---:|
| 0 | gameplay foundation | `schala_field_idle_down_f00_v0` | 24x32 | 4 |
| 1 | gameplay foundation | `schala_field_idle_up_f00_v0` | 24x32 | 4 |
| 2 | gameplay foundation | `schala_field_idle_left_f00_v0` | 24x32 | 4 |
| 3 | gameplay foundation | `schala_field_idle_right_f00_v0` | 24x32 | 4 |
| 4 | gameplay foundation | `schala_field_walk_down_f00_v0` | 24x32 | 4 |
| 5 | gameplay foundation | `schala_field_walk_down_f01_v0` | 24x32 | 3 |
| 6 | gameplay foundation | `schala_field_walk_down_f02_v0` | 24x32 | 4 |
| 7 | gameplay foundation | `schala_battle_ready_f00_v0` | 40x40 | 4 |
| 8 | gameplay foundation | `schala_battle_cast_gather_f00_v0` | 40x40 | 4 |
| 9 | gameplay foundation | `schala_battle_cast_release_f00_v0` | 40x40 | 4 |
| 10 | Glass Focus body | `schala_battle_basic_attack_draw_f00_v0` | 40x40 | 4 |
| 11 | Glass Focus body | `schala_battle_basic_attack_open_f01_v0` | 40x40 | 4 |
| 12 | Glass Focus body | `schala_battle_basic_attack_pulse_f02_v0` | 40x40 | 4 |
| 13 | Glass Focus body | `schala_battle_basic_attack_followthrough_f03_v0` | 40x40 | 4 |
| 14 | Glass Focus body | `schala_battle_basic_attack_recoil_f04_v0` | 40x40 | 4 |
| 15 | Glass Focus body | `schala_battle_basic_attack_recover_f05_v0` | 40x40 | 4 |

Fifteen frames use four active 16x16 objects. The middle downward-walk key
uses three and retains the existing deterministic transparent fourth slot.
Every visible source cell is covered exactly once. No record needs an
unsupported flag or a tile index above `$07FF`.

## Exact aggregate identity

| In-memory serialization | Size | SHA-256 |
|---|---:|---|
| Raw graphics | `$0B60` (2,912 bytes) | `361ea69917d97a8c68e4450df0b944e43c9dad73b3aca2ecf52304ed70484a66` |
| Assembly | `$0280` (640 bytes) | `b14735361a2546337d32ad3f8318a4138980c16515a7cbcc48a1b92de89d69d1` |
| Existing gameplay palette | `$0020` (32 bytes) | `782a063ffc99087cca1b64876cd024a5c5c7e6c6193c8f9ff224e9ed88ead5ea` |

The preserved ten-frame prefix remains:

| Existing prefix | Size | SHA-256 |
|---|---:|---|
| Raw graphics | `$0A20` (2,592 bytes) | `61bdecf43ad967ff5bd3c7604d7ce0708305a516e1e17d7cbbcabe949f3c791f` |
| Assembly | `$0190` (400 bytes) | `11c7d77ec789853aca496b1bd38fdef35c437c31407000af74c7aa498bebb540` |

The bytes exist only transiently in memory for serialization and
reconstruction. They are represented in source control only by their metadata
hashes and sizes.

## Deliberately excluded source components

The six standalone Focus inserts remain validated source vocabulary and are
not composited or appended as unused body-packet data:

- closed crescent;
- open ring;
- quarter-turn ring;
- edge-on ring;
- collapse point; and
- impact arc.

The `focus_swing_v0` and `focus_hit_v0` integer-only audio recipes are also
validated by their existing source contract but are not graphics-packet data.
No native sound ID or audio record is assigned.

## Reproduction

From the workspace root, using a Python environment with the existing Pillow
dependency:

```powershell
python tools/audit_schala_current_body_packet.py
python tests/test_schala_current_body_packet.py -v
```

The first command emits canonical UTF-8/LF JSON only to stdout. It accepts no
ROM, source override, output file, or output directory. The 18 focused tests
verify exact dependency identities, source/manifest boundaries, frame order,
palette identity, four-object coverage, record and tile bounds, aggregate
hashes, unchanged ten-frame prefixes, exact reconstruction, negative failures,
metadata-only serialization, no-write behavior, and byte-identical report
reproduction without reading the pinned report.

Neighboring suites that must remain unchanged and passing are:

- `tests/test_schala_gameplay_foundation_v0.py`;
- `tests/test_schala_sprite_packet_foundation_v0.py`;
- `tests/test_schala_glass_focus_pulse_v0.py`;
- `tests/test_schala_gameplay_originality_audit.py`;
- `tests/test_schala_glass_focus_originality.py`; and
- `tests/test_schala_npc_originality_audit.py`.

## Evidence boundary and stop gates

This audit adds `verified-static` evidence only for exact source identity,
native-shaped packet fit, deterministic serialization, bounds, and exact
reconstruction. The visual design and provisional source order remain
`proposal`.

It supplies no new `verified-runtime` result and makes no claim for:

- native animation-slot semantics or a four-facing animation blob;
- the `$E4:2800` auxiliary-animation family;
- battle staging, DMA, timing, or expanded-bank reads;
- graphics, assembly, animation, palette, effect, or sound pointers;
- action `$90`, item `$E8`, or runtime descriptor execution;
- logical PC `$07`, save/load, New Game+, or recruitment;
- a ROM allocation, ROM write, patch, or production hook;
- any change to Epoch or an existing Project Epoch artifact; or
- the complete 241-packet compressed-corpus, near-match, silhouette,
  animation, or finished-sheet originality gates.

The audit fails closed on any source, manifest, or helper drift; non-null
binding; palette difference; frame identity change; fifth-object need;
coordinate, tile-index, or record overflow; unsupported flag; prefix change;
or reconstruction mismatch.

The next safe source-only engine step is to map the exact semantic animation
slots and auxiliary-animation contract before authoring the remaining field
and battle inventory. The complete future sheet must then be checked against
the conservative 241-packet corpus and pass the bounded near-match/silhouette
review before any explicit expanded allocation or PC `$07` integration.
