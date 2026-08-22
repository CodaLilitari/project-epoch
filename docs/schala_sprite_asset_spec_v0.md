# Project Epoch: Schala sprite asset specification v0

Status: original-art production proposal  
Implementation status: vanilla PC packet envelope measured; full sheet and
PC `$07` integration remain blocked  
Companion design: `docs/schala_character_design_v0.md`  

This document turns the approved visual direction into a bounded, auditable
asset pipeline. It does not allocate ROM space, assign a graphics-source index,
or authorize an eighth-character patch.

## Current implementation boundary

The first partial target-grid gameplay source is implemented and documented
in `docs/schala_gameplay_sprite_foundation_v0.md`.

- ten original indexed frames: four cardinal field idles, three downward walk
  keys, battle ready, cast gather, and cast release;
- canonical source SHA-256:
  `9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2`;
- exact deterministic SNES 4bpp packing and palette output;
- eighteen focused source, packing, and originality checks;
- no imported, traced, sampled, transformed, or resized NPC/PC/concept pixels;
- zero exact or palette-renaming-invariant matches against all 7,264 raw
  tiles in the seven canonical playable-character graphics windows;
- the ten frames compile into ten native-shaped `$28`-byte assembly records
  and an 81-tile raw graphics packet with exact serialized reconstruction;
- no animation blob, complete sheet, ROM allocation, or runtime integration.

This advances the source-art gate but does not satisfy the complete frame,
canonical compressed-graphics comparison, or ROM-integration gates below.
The partial packet compiler and its explicit boundary are documented in
`docs/schala_sprite_packet_foundation_v0.md`.

## 1. Evidence labels used here

- **[verified-static]** Proven directly from the canonical ROM or the current
  deterministic clone builder.
- **[concept-observation]** A visible feature of the generated concept image;
  not proof of a ROM capability and not final art.
- **[proposal]** An art, naming, budget, or workflow target.
- **[gate]** A condition that must be satisfied before an asset can enter a ROM
  build.

## 2. Concept references and their limits

The broad character reference is:

`assets/concepts/schala_playable_concept_v0.png`

SHA-256:

`4799352c9e4a273bc88be56e1f9d472b1a1723411956857160ab89919d7bfd45`

**[concept-observation]** The image shows a cool indigo-haired traveler in an
ivory split tunic, an indigo-violet mantle with restrained gold celestial
marks, crescent ornaments, a ring-like focus, and blue-lavender ward effects.

The tighter sprite-production reference is:

`assets/concepts/schala_playable_sprite_reference_v1.png`

SHA-256:

`8b9d38332eb4b1b7f66ad5ce4bff995772fa890cb3561bcb62ba6f42f9fcc456`

**[concept-observation]** This second image establishes a high knot, short
braid, shorter mantle, visible legs, and a casting-only focus. It was generated
from a prompt that explicitly prohibited tracing, copied tiles, borrowed
poses, NPC-gown geometry, and permanent weapons.

**[gate]** Both PNGs are concept only. They must never be cropped, scaled,
quantized, traced, tile-sampled, palette-sampled, or otherwise converted into a
ROM asset. Final pixels must be placed by hand on a clean target-resolution
canvas. The concepts may remain open only as high-level shape, material, and
mood references.

The large reference figures deliberately exaggerate hair flow, garment detail,
and effect size. None of those pixel counts establish a field-sprite, battle-
sprite, portrait, tile, palette, or object-allocation budget.

## 3. Reconciled color and silhouette direction

### 3.1 Color hierarchy

The character-design document proposed midnight teal, warm ivory, old gold,
rose-violet magic, and deep indigo hair. The concept renders the mantle closer
to indigo-violet and its effects closer to blue-lavender. The ROM direction
combines them as follows.

- **[proposal] Mantle:** indigo-teal, with midnight teal in its darkest two
  values and a restrained indigo highlight. It must read cooler and darker than
  the ivory garment, but greener and less luminous than the hair.
- **[proposal] Inner garment:** warm ivory, never pure white. The warm value
  separates it from snow and from blue-white magic effects.
- **[proposal] Metal:** muted old gold. Bright yellow is reserved for one-pixel
  specular accents and is not a large fill color.
- **[proposal] Hair:** deep indigo through desaturated steel blue. Hair
  highlights are brighter and bluer than mantle highlights so the two masses
  do not merge.
- **[proposal] Magic:** a blue-white core with a rose-violet rim or terminal
  spark. Rose is an action accent, not a dominant garment color.
- **[proposal] Skin:** a compact warm three-value ramp chosen for readability,
  not sampled from the concept.

The concept's gold constellation pattern is reduced at game scale. Field
frames may use at most two isolated gold pixels on the mantle; battle casting
frames may use at most four. The portrait may carry a clearer two- or
three-mark motif. This prevents crawling noise during movement.

### 3.2 Silhouette translation

- **[proposal]** Retain a short asymmetric mantle and split over-tunic.
- **[proposal]** Replace the concept's long loose hair mass with a half-up
  indigo shape, one side braid or trailing lock, and a crescent clasp. Hair may
  reach mid-back in battle key art but must clear the feet in every field frame.
- **[proposal]** Keep the crescent clasp on one shoulder and one small belt
  focus. Do not give Schala a permanent staff, scythe, or cape silhouette.
- **[proposal]** Show the floating ring focus only during basic attack, casting,
  and selected tech frames.
- **[proposal]** Normal field poses fit a nominal 24×32-pixel body box. Battle
  anticipation and follow-through may use a nominal 40×40-pixel action box.
  These are authoring canvases, not packet guarantees. **[verified-static]**
  Every vanilla PC uses a four-object, sixteen-tile-word frame record; each
  finished frame must be packable into that envelope unless a separately
  reviewed renderer expansion is proved.

The desired read at 1× scale is: indigo hair above a light vertical center,
dark asymmetric shoulder shape, split ivory hem, and two visible feet.

## 4. Platform and project constraints

- **[verified-static]** Existing playable-character graphics use separate
  graphics-packet and assembly-packet pointer tables. A new graphics-source
  destination has not been established.
- **[verified-static]** The vanilla field palette path copies `$18` bytes,
  twelve character-specific colors, into entries 1-12 of an allocated sprite
  row. Schala's original palette uses visible indices 1-15, so logical PC
  `$07` requires a separately proved full-palette adapter; it may not inherit
  stale/shared values for indices 13-15.
- **[verified-static]** All seven playable descriptors use size class 0. One
  frame is a `$28`-byte record: sixteen tile words followed by four coordinate
  pairs. The common field path builds four sprite objects and decodes `$200`
  bytes, then queues two `$100`-byte transfers.
- **[verified-static]** Assembly tile indices are masked with `$07FF`, and
  `$4000` selects the horizontal decode path. `$FF` is the animation frame
  sentinel, so the unchanged format can address frames `$00-$FE`: at most 255
  records or `$27D8` assembly bytes. Ayla reaches that record ceiling.
- **[verified-static]** Canonical animation blobs contain four equal facing
  blocks. Their measured complete sizes range from `$3D0` to `$540`, with
  61-84 four-byte slots per facing.
- **[verified-static]** The seven exact raw PC graphics windows contain 858
  to 1,190 tiles each and 7,264 total. The audited PC path indexes raw 4bpp
  data directly; it is not the compressed NPC packet path.
- **[verified-static]** Low graphics-source indices beyond `$06` are occupied
  by existing engine actors or vehicles and cannot be borrowed.
- **[verified-static]** The full status/party portrait upload contains seven
  `0x480`-byte 4bpp faces: thirty-six 8×8 tiles forming a 48×48 image. Logical
  ID7 aliases another face in the vanilla selector.
- **[verified-static]** The smaller save-preview path uses a distinct
  `0x200`-byte 4bpp block: sixteen 8×8 tiles forming a 32×32 image. The
  supported-slot diagnostic rendered this path coherently
  (`verified-runtime`).
- **[verified-static]** Existing portrait palettes occupy `0x20` bytes, or
  sixteen SNES color entries.
- **[gate]** The complete semantic field/battle frame list, auxiliary
  animation data, battle-specific staging/timing, tile-reuse choices, and
  expanded-bank adapters remain to be proved before final packing. Exact
  vanilla PC packet metadata and the bounded unknowns are recorded in
  `docs/pc_sprite_packet_envelope_audit.md`.
- **[gate]** A provenance-backed expanded graphics destination must be found or
  created. No existing actor pointer or zero-filled area may be overwritten
  merely because it appears unused.

SNES-native art is authored as indexed 4bpp tiles: one transparent palette
entry and at most fifteen visible entries per assigned palette. This is the
working art constraint even if later tracing reveals that some effects use a
separate palette.

## 5. Palette specification

### 5.1 Gameplay body palette

**[proposal]** Use one sixteen-entry indexed palette for Schala's body art.
Index 0 is transparent. The remaining entries have fixed semantic jobs so
frames cannot silently introduce extra colors.

| Index | Semantic use | Starting sRGB target | Notes |
|---:|---|---|---|
| 0 | Transparent | `#FF00FF` preview only | Export alpha/index 0; preview magenta is never encoded as visible color. |
| 1 | Universal outline | `#101528` | Near-black navy, not absolute black. |
| 2 | Mantle deepest | `#17283A` | Midnight teal anchor. |
| 3 | Mantle middle | `#293D61` | Indigo-teal bridge. |
| 4 | Mantle light | `#465A86` | Restrained indigo highlight. |
| 5 | Hair shadow | `#182B59` | Bluer than mantle deepest. |
| 6 | Hair middle | `#3F5F9A` | Main hair read. |
| 7 | Hair light | `#829FD0` | Use sparingly on moving locks. |
| 8 | Skin shadow | `#915748` | Warm low value. |
| 9 | Skin middle | `#C77D60` | Main face/hand color. |
| 10 | Skin light | `#EDB58E` | Small facial/hand highlights. |
| 11 | Ivory shadow | `#A99E8D` | Also permitted for boot highlights. |
| 12 | Warm ivory | `#DDD1BB` | Never expand to pure white. |
| 13 | Old-gold shadow | `#76531D` | Clasp, trim, focus rim. |
| 14 | Old-gold light | `#C69C42` | One-pixel accents and readable trim. |
| 15 | Rose-violet accent | `#B64FA9` | Magic glints only; not a garment fill. |

These hex values are art-direction starting points, not encoded palette bytes.
The palette compiler must quantize each channel to SNES 5-bit color, render the
result through the test harness, and allow hand correction. Any correction
updates the palette source and manifest; it is never patched directly into an
output ROM.

### 5.2 Effect palette

**[proposal]** Prefer existing, traced battle-effect primitives for rings,
barriers, star points, and impact flashes. If a character-specific effect
palette is proven safe, it may add blue-white and pale lavender values while
retaining rose-violet at the edge. Until then, every character-owned focus tile
must fit the gameplay body palette.

### 5.3 Portrait palette

**[proposal]** The portrait set receives a reviewed sixteen-entry palette, but
its material hierarchy must match the gameplay palette:

- 1 transparent/background entry;
- 3 outline and deep-shadow entries;
- 3 hair entries;
- 3 skin entries;
- 3 mantle/ivory entries;
- 2 gold entries;
- 1 rose-violet eye or magic accent.

No portrait color may be sampled from the concept image. The final full and
preview portrait palette must be produced from the hand-pixeled portraits
themselves and stored as a reviewed indexed source. Prefer one shared
sixteen-entry palette only if both traced paths can select it without loss.

## 6. Asset budget

### 6.1 Hard source-art budget

This is a production ceiling, not a ROM allocation claim.

| Category | Logical-frame ceiling | Unique 8×8 tile ceiling | Raw 4bpp ceiling |
|---|---:|---:|---:|
| Shared body, face, hair, and garment vocabulary | n/a | 48 | `0x0600` bytes |
| Field direction and locomotion deltas | 32 | 104 | `0x0D00` bytes |
| Field interaction and casting deltas | 10 | 40 | `0x0500` bytes |
| Battle stance, movement, and basic attack deltas | 16 | 56 | `0x0700` bytes |
| Battle cast, item, hurt, KO, revive, victory deltas | 20 | 72 | `0x0900` bytes |
| Character-owned focus/crescent inserts | 12 | 32 | `0x0400` bytes |
| **Gameplay total** | **90 maximum** | **352 maximum** | **`0x2C00` bytes raw** |
| Full status/party portrait | 1 frame | 36 | `0x0480` bytes |
| Small save-preview portrait | 1 frame | 16 | `0x0200` bytes |
| Optional original VFX, separately gated | 16 | 48 | `0x0600` bytes |

Logical frames may reuse all or part of other frames. The unique-tile ceiling is
the controlling source budget. Transparent duplicate tiles count once.

**[verified-static]** The current 352-tile source ceiling is below both the
largest measured raw PC graphics window (Lucca: 1,190 tiles, `$94C0` bytes)
and the `$07FF` tile-index encoding capacity. The 90-frame source ceiling is
below the unchanged-format limit of 255 assembly records.

**[gate]** Those comparisons do not allocate ROM space or prove that an
arbitrary canvas packs correctly. Every emitted frame must fit four sprite
objects and sixteen tile words; every final packet, animation blob, and
expanded-bank read must pass the compiler and runtime gates in
`docs/pc_sprite_packet_envelope_audit.md`.

### 6.2 Object and frame box budget

- Normal field frame: target 3×4 8-pixel cells; no more than 12 occupied cells.
- Extended field cast: target 4×4 cells; no more than 16 occupied cells.
- Normal battle frame: target 4×4 cells; no more than 16 occupied cells.
- Extended battle action: a sparse 5×5 authoring canvas is permitted only
  when its visible cells pack into four sprite objects and sixteen tile words;
  no more than 16 occupied cells.
- Floating focus: no more than four occupied 8×8 cells in any one frame.
- Full status/party portrait: exactly 6×6 tiles, 48×48 pixels.
- Small save-preview portrait: exactly 4×4 tiles, 32×32 pixels.

The cell and canvas choices are **[proposal]** authoring limits. The
four-object/sixteen-word ceiling is **[verified-static]** for the unchanged
vanilla PC path. A compiler must still prove each frame's actual assembly
coverage; an occupied-cell count alone is not sufficient.

## 7. Required frame categories

### 7.1 Field animation set

**[proposal]** Author all directional intent first; later packing may mirror
safe side directions if tracing proves that vanilla player packets do so.

| Category | Source-frame budget | Required read |
|---|---:|---|
| Idle/turn | 8 | One clean facing for each cardinal and diagonal direction. |
| Walk | 24 | Three-step cycle across eight directions; feet and split hem must alternate clearly. |
| Interact/use | 2 | Reach/open and present/receive poses without the focus. |
| Field cast | 4 | Raise hand, form focus, release ring, recover. |
| Field hurt/stagger | 2 | Compact silhouette; no floor-length hair smear. |
| **Field total** | **40** | Must remain readable on snow, grass, stone, and dark interiors. |

If the traced engine requires ladder, climb, push, pull, sleep, sit, laugh, or
other event poses, they enter a separately numbered extension sheet. Do not
silently substitute another PC's frames.

### 7.2 Battle animation set

| Category | Source-frame budget | Required read |
|---|---:|---|
| Ready/idle | 4 | Planted stance; subtle mantle and hand motion only. |
| Advance/retreat | 4 | Fast travel silhouette with no persistent focus. |
| Basic attack | 6 | Draw crescent ring, short pulse, recoil, recover. |
| Generic cast | 6 | Two-step hand geometry, orbiting focus, collapse/release. |
| Item/use | 2 | Neutral presentation pose distinct from spellcasting. |
| Hurt/critical | 4 | Fragility communicated without losing facing. |
| KO/revive | 4 | Fall, down, rise, ready. |
| Victory | 4 | Focus closes into clasp; gaze returns to party. |
| Tech-specific body accents | 6 | At most two unique body poses shared across the eight single techs. |
| **Battle total** | **40** | Spell identity should come primarily from traced VFX, not oversized body sheets. |

The eight single techs do not receive eight independent full-body animations.
Astral Pin, Veil, Crescent Wake, Stillpoint, Recall, Sanctuary, Rift Bloom, and
Astral Gate share the generic casting vocabulary, with timing, focus orientation,
and external effects providing differentiation.

### 7.3 Focus and effect vocabulary

**[proposal]** Limit Schala-owned inserts to:

1. closed crescent;
2. open ring;
3. quarter-turn ring;
4. edge-on ring;
5. four-point star;
6. collapsing point;
7. small ward arc;
8. small impact arc.

Barrier ovals, large rings, lightning, fire, healing columns, revival effects,
and area impacts should reuse traced engine effect systems where technically and
artistically appropriate. Reuse of a general engine effect is not permission to
copy an NPC body tile into Schala's character packet.

## 8. Portrait specification

- **[verified-static]** Full status/party footprint: 48×48 pixels, thirty-six
  8×8 4bpp tiles, `0x480` tile bytes, and a selected sixteen-entry
  `0x20`-byte palette.
- **[verified-static]** Small save-preview footprint: 32×32 pixels, sixteen
  8×8 4bpp tiles and `0x200` tile bytes. It is an independent selector/load
  path, not proof that the full portrait works.
- **[proposal]** View: three-quarter angle, alert and resolved rather than
  ceremonial.
- **[proposal]** Crop: hair knot/upper hair mass, face, crescent clasp, and a
  small piece of asymmetric mantle remain visible.
- **[proposal]** Expression: relaxed brow, level gaze, closed neutral mouth.
- **[proposal]** Lighting: warm face light against cool hair and mantle; no
  photographic gradients or automatic downsampling.
- **[proposal]** At least two pixels separate the hair highlight from the
  brightest ivory wherever practical, preventing the portrait from becoming a
  single pale mass.

Author the full face at 48×48 and the preview at 32×32 from their first
committed pixels. The preview may simplify the same authored design, but it
must not be an automatically resized full portrait. A larger sketch may guide
composition, but no resize output may enter either indexed source.

The full portrait requires dynamic loading/resolution rather than the vanilla
ID7 tile-base alias. The preview needs a sidecar-aware resolver rather than
reading slot `$0430` as a character record. Both remain **[gate]** items.

Current source status:

- **[verified-static]** Independent 48x48 and 32x32 indexed sources and their
  deterministic `0x480`/`0x200`/`0x20` packed outputs are complete; see
  `docs/schala_portrait_asset_foundation_v0.md`.
- **[verified-static]** The 48 non-trivial candidate portrait tiles have zero
  exact or palette-renaming-invariant matches against all 252 canonical
  uncompressed menu-portrait tiles, including H/V/HV flips; see
  `docs/schala_portrait_originality_audit_v0.md`.
- **[gate]** Compressed NPC/field/battle comparisons and in-game loading are
  not covered by that bounded audit.

## 9. Original-art production pipeline

1. **Lock references.** Record this spec, the companion character-design
   document, and the concept PNG hash in the asset manifest.
2. **Create clean masters.** Start new transparent, indexed canvases at target
   resolution. Do not import the concept or any extracted game art as a layer.
3. **Block silhouette in two values.** Validate body, hair, mantle, hem, and
   feet before color or detail.
4. **Apply semantic palette indices.** Use the fixed index jobs from Section 5;
   never paint with arbitrary RGB values inside a production sheet.
5. **Author shared vocabulary.** Complete reusable face, hair, torso, hem, hand,
   and foot tiles before frame deltas.
6. **Complete field frames.** Test the movement loops at 1× and integer zoom.
7. **Complete battle frames.** Add the generic cast and focus vocabulary;
   tech-specific effects remain separate.
8. **Author both portraits independently.** Create the 48×48 full face and
   32×32 preview from the same material hierarchy, without copied sprite
   pixels or automatic resizing.
9. **Run originality audit.** Compare tile hashes in memory against canonical
   PC and NPC tiles, including horizontal/vertical flips. Do not write
   extracted comparison tiles to disk.
10. **Pack deterministically.** A source-controlled builder converts indexed
    PNGs plus frame metadata into tiles, palettes, and assembly data. Identical
    inputs must produce identical outputs and hashes.
11. **Render from packed bytes.** QA images and animation strips must be
    decoded from the packed output, not from the source PNGs.
12. **Integrate only after tracing.** The patch builder may consume the packed
    asset only after all graphics, palette, DMA, and PC-ID gates are satisfied.

No manual hex editing is part of this pipeline.

## 10. File naming and package layout

### 10.1 Canonical names

Use lowercase ASCII, underscores, zero-padded frame numbers, and explicit
version suffixes.

```text
assets/source/schala/v0/
  manifest.json
  palette/
    schala_gameplay_palette_v0.png
    schala_portrait_palette_v0.png
  field/
    schala_field_down_idle_f00_v0.png
    schala_field_down_walk_f00_v0.png
    schala_field_ne_cast_f02_v0.png
  battle/
    schala_battle_idle_f00_v0.png
    schala_battle_attack_f03_v0.png
    schala_battle_cast_release_f04_v0.png
  portrait/
    schala_portrait_full_48x48_v0.png
    schala_portrait_preview_32x32_v0.png
  focus/
    schala_focus_open_ring_f00_v0.png
  metadata/
    schala_field_frames_v0.json
    schala_battle_frames_v0.json
    schala_tile_usage_v0.json
```

Packed and rendered QA artifacts belong under ignored build/output locations,
not beside editable source art.

Do not use names such as `magus_body`, `schala_npc_edit`, `gaspar_slot`, or
`portrait_copy`. Such names indicate a prohibited derivation or a namespace
shortcut.

### 10.2 Manifest provenance

Every editable and packed asset must record:

- relative path;
- SHA-256;
- dimensions and indexed-color mode;
- palette version;
- author or producing agent;
- creation and modification date;
- tool and tool version;
- source classification: `original-hand-pixelled`, `generated-concept-reference`,
  or `deterministic-packed-output`;
- references consulted by path and hash;
- explicit statement that no NPC or PC tiles were imported;
- review status and reviewer;
- builder version and command for packed outputs.

Each concept PNG's manifest entry must be
`generated-concept-reference` and `rom_eligible: false`. If its original prompt,
generator, or creation metadata is unavailable, record `unknown`; do not invent
it.

## 11. Acceptance tests

### 11.1 Source and provenance

- [ ] Both concept PNG hashes exactly match the values in Section 2.
- [ ] Both concepts are marked `rom_eligible: false`.
- [ ] No concept, NPC, or PC bitmap appears as a layer in an editable master.
- [ ] Every source and packed file has a manifest SHA-256.
- [ ] A clean build reproduces every packed byte and reported hash.

### 11.2 Palette and pixel format

- [ ] Gameplay sheets use index 0 for transparency and no more than fifteen
      visible indices.
- [ ] Indexed source contains no unintended alpha values or RGB-only pixels.
- [ ] SNES 5-bit quantization is rendered and manually reviewed.
- [ ] Warm ivory remains distinct from snow and spell-white.
- [ ] Hair remains distinct from the indigo-teal mantle on all test backgrounds.
- [ ] Rose-violet is limited to magic accents.

### 11.3 Frame and tile budget

- [ ] All required field and battle categories are present.
- [ ] No logical-frame or unique-tile ceiling in Section 6 is exceeded.
- [ ] Normal and extended poses remain within the provisional body boxes.
- [ ] Final assembly count and decoded packet size fit the measured vanilla
      envelope or an independently approved expansion.
- [ ] Focus tiles are absent from locomotion and neutral field frames.

### 11.4 Originality

- [ ] No non-trivial 8×8 tile exactly matches a canonical PC or NPC tile,
      including horizontal and vertical flips.
- [ ] Fully transparent tiles and trivial one- or two-pixel coincidences are
      excluded from automatic failure but listed for review.
- [ ] Near-match review finds no traced outline, face, hair, garment, or pose.
- [ ] Side-by-side silhouette review confirms the result is not a Magus, Marle,
      or NPC body recolor.
- [ ] Comparison is performed in memory; extracted copyrighted tiles are not
      saved or committed.

### 11.5 Visual and animation QA

- [ ] Idle, walk, cast, hurt, KO, revive, and victory loops are reviewed at 1×.
- [ ] Split hems alternate consistently and never exchange front/back layers.
- [ ] Hair never merges with feet or becomes a floor-length smear.
- [ ] Crescent clasp stays on the intended shoulder in mirrored frames.
- [ ] Constellation marks do not crawl or flicker during ordinary movement.
- [ ] Test renders pass on dark stone, bright snow, green field, warm interior,
      and battle-flash backgrounds.
- [ ] Portrait and gameplay sprite read as the same design without sharing
      copied pixels.
- [ ] Full 48×48 and preview 32×32 portraits remain legible and consistent
      without either being an automatically resized derivative.

### 11.6 ROM integration gates

- [ ] A safe graphics source and pointer path exist for logical PC `$07`.
- [ ] Graphics and assembly packets are decoded and traced for all load paths.
- [ ] Palette selection is correct in field, battle, menu, roster, party
      exchange, and save-select.
- [ ] No actor/vehicle graphics entry is overwritten.
- [ ] No zero run is treated as free without provenance.
- [ ] Recorded emulator tests cover field transitions, all animation categories,
      battle entry/exit, menu redraw, saving, reloading, and New Game+.

Passing the art tests makes an asset **ROM-ready in form**, not a verified
eighth-character implementation. Only recorded runtime evidence can supply that
final label.
