# Project Epoch: Schala gameplay sprite foundation v0

Status: partial animation foundation  
ROM integration: not performed  
Evidence: `verified-static` for source validation and deterministic packing;
`proposal` for the visual design

This report records the first original gameplay pixels for playable Schala.
It is intentionally bounded. It is not a full field sheet, a full battle
sheet, a graphics-source allocation, or a playable PC `$07` implementation.
The source now has a separate native-shaped partial packet compiler documented
in `docs/schala_sprite_packet_foundation_v0.md`; that does not make the sheet
complete or ROM-integrated.

## 1. Deliverables

Canonical editable source:

- `assets/source/schala/v0/gameplay/schala_gameplay_foundation_v0.json`
- SHA-256:
  `9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2`
- format: uppercase hexadecimal 4bpp palette-index rows, split into visible
  8-pixel cells
- classification: `original-hand-pixelled-target-grid`

Pinned gameplay-specific manifest:

- `assets/source/schala/v0/gameplay/manifest_v0.json`
- separate from the existing portrait manifest
- records the canonical source, builder, reproduction command, and every
  generated output hash and size

Deterministic builder:

- `tools/build_schala_gameplay_foundation_v0.py`
- SHA-256:
  `e43f5d5b6fe30c5746ef04822f98f120165ecbea8393143e5b93941fdeb6cf8f`
- builder version: `1.0.0`

Focused checks:

- `tests/test_schala_gameplay_foundation_v0.py`
- `tests/test_schala_gameplay_originality_audit.py`
- eighteen tests passed across the two modules on 2026-07-25

Generated `.4bpp`, palette, build-manifest, individual PNG, and contact-sheet
artifacts are local-only under:

`private/build/schala_gameplay_foundation_v0/`

That directory is ignored and must not be committed. The generated build
manifest has SHA-256
`352c88a8a6ef3b396ad2ace4f0300fbd9a6a1ea0b715b94392bfaf197102b2ec`.
The 4x contact sheet has SHA-256
`de89381fc1c3a81a6ee116d60700e8f0ab50ea259d15766f1de9965a046aacf2`.

## 2. Originality and provenance boundary

The initial source was created on clean target grids without reading any ROM,
save, emulator state, extracted tile, NPC graphic, playable-character graphic,
portrait pixel, or official-art pixel.

The two concept images are recorded by path and hash for project provenance,
but the pixel author did not open them. Their high-level direction was consumed
only through the written sprite specification: high knot, side lock, short
asymmetric mantle, split ivory over-tunic, visible legs, crescent vocabulary,
and casting-only focus. No concept pixel or palette value was sampled, traced,
quantized, transformed, or resized.

The source declares all prohibited import and derivation flags as false. The
builder rejects the source if any flag changes or if either concept becomes
ROM-eligible, sampled, or opened by the pixel author.

A later metadata-only originality audit identified incidental three- and
four-pixel edge-fragment matches. No reference pixel was displayed, rendered,
exported, traced, sampled, or supplied to the pixel author. Five redundant
Schala-only edge fragments were removed while retaining the already-present
adjacent silhouette edge. The final packed source has zero exact or
palette-renaming-invariant matches against all 7,264 tiles in the seven
canonical playable-character graphics windows. See
`docs/schala_gameplay_originality_audit_v0.md`.

## 3. Foundation frame set

All field frames use a native 24x32 canvas. All battle frames use a native
40x40 canvas.

| Context | Frame | Purpose |
|---|---|---|
| Field | `schala_field_idle_down_f00_v0` | Front cardinal idle |
| Field | `schala_field_idle_up_f00_v0` | Back cardinal idle |
| Field | `schala_field_idle_left_f00_v0` | Independently authored left profile |
| Field | `schala_field_idle_right_f00_v0` | Independently authored right profile |
| Field | `schala_field_walk_down_f00_v0` | Left-step walk key |
| Field | `schala_field_walk_down_f01_v0` | Passing walk key |
| Field | `schala_field_walk_down_f02_v0` | Right-step walk key |
| Battle | `schala_battle_ready_f00_v0` | Planted neutral ready pose |
| Battle | `schala_battle_cast_gather_f00_v0` | Compact focus-gather key |
| Battle | `schala_battle_cast_release_f00_v0` | Open-ring release key |

The three walk frames are a complete downward key cycle at the source-art
level. Timing and engine assembly are not defined.

The floating focus and palette index 15 are absent from all field locomotion
and the neutral battle-ready pose. They appear only in the two casting keys.

## 4. Palette and packed format

The foundation uses exactly one sixteen-entry gameplay palette. Index 0 is
transparent. Indices 1-15 retain the semantic jobs in
`docs/schala_sprite_asset_spec_v0.md`: outline; three mantle values; three hair
values; three skin values; two ivory values; two old-gold values; and one
rose-violet magic accent.

The builder quantizes the authored sRGB targets to SNES BGR555 and writes a
`0x20`-byte palette. It packs each 8x8 tile as SNES planar 4bpp:

- 24x32 field frame: 12 tiles, `0x180` bytes
- 40x40 battle frame: 25 tiles, `0x320` bytes

Every PNG is decoded from the packed 4bpp and quantized palette bytes. It is
not rendered directly from an alternate bitmap master.

## 5. Deterministic reproduction

From the workspace root:

```text
python tools/build_schala_gameplay_foundation_v0.py --output-dir private/build/schala_gameplay_foundation_v0
python -m unittest tests.test_schala_gameplay_foundation_v0 -v
```

The first command verifies the pinned source and output hashes before writing.
Use `--skip-manifest-verification` only while intentionally editing canonical
source and before repinning the reviewed manifest.

## 6. Validation results

The focused suite verifies:

- all ten required frame IDs and native dimensions;
- four cardinal idles and downward cycle indices 0, 1, and 2;
- one ordered sixteen-entry palette with transparent index 0;
- every source pixel fits 4bpp;
- exact SNES 4bpp encode/decode round trips;
- private output reproducibility and pinned hashes;
- clean-room provenance and unsampled concept references;
- per-frame occupied-cell limits;
- the 352-tile gameplay ceiling;
- focus absence from locomotion and neutral ready;
- PNG pixels decoded from packed bytes;
- no non-trivial exact or H/V/HV-flipped tile shared between the field and
  battle contexts.
- zero exact or palette-renaming-invariant matches against all seven canonical
  playable-character graphics windows, including H/V/HV flips.

Measured source-art budget:

| Measure | Result |
|---|---:|
| Maximum occupied cells in a field frame | 12 |
| Occupied cells in battle ready | 12 |
| Maximum occupied cells in an extended cast frame | 14 |
| Unique nontransparent field tiles | 58 |
| Unique nontransparent battle tiles | 22 |
| Unique nontransparent gameplay tiles total | 80 |
| Gameplay ceiling | 352 |

Exact or flipped sharing inside one context is permitted and reported because
stable head, torso, and leg vocabulary is desirable within an animation set.
Cross-context sharing is rejected so a field tile cannot silently stand in for
the independently authored battle vocabulary. Fully transparent and at-most-
two-pixel coincidences are reported as trivial rather than failed.

## 7. What remains

This foundation deliberately leaves the following unfinished:

- diagonal field idles and all remaining directional walk cycles;
- field interaction, cast, hurt, and event-extension poses;
- battle idle motion, advance, retreat, basic attack, item, hurt, KO, revive,
  victory, and any additional cast timing keys;
- focus insert vocabulary beyond the two keys;
- rerun the complete future sheets against the conservative 241-packet
  compressed NPC/enemy corpus; the current ten frames already have a bounded
  zero-match result against the one documented Schala-family packet, and the
  raw playable-character windows are complete;
- assembly shapes for the remaining frames, animation-slot/facing maps,
  mirroring policy, DMA timing, and expanded-ROM addresses; the current ten
  frames now fit four-object `$28`-byte records and reconstruct exactly;
- palette selection and runtime rendering in field, battle, menu, roster,
  party exchange, save-select, and New Game+ paths.

Accordingly, these pixels are `verified-static` as an original, deterministic
partial source foundation. They are not a complete playable sheet and are not
ROM-ready or runtime-verified.
