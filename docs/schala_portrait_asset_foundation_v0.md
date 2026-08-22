# Project Epoch: Schala portrait asset foundation v0

Status: original target-size source and deterministic packer complete  
ROM integration status: not performed; existing PC `$07` graphics gates remain  
Evidence date: 2026-07-25  

## Outcome

Two original portrait canvases now exist as reviewable, source-controlled
palette-index rows:

- `schala_portrait_full_48x48_v0`: 48x48 pixels, 36 tiles, `0x480` packed
  bytes;
- `schala_portrait_preview_32x32_v0`: 32x32 pixels, 16 tiles, `0x200` packed
  bytes.

The preview was composed independently at 32x32. It is not a resize or crop of
the full portrait. Its bangs, braid, collar, mantle edge, and seven-pixel
shoulder crescent use different geometry while preserving the same material
hierarchy.

The visual vocabulary follows the written design: a high knot with a separate
side braid, cool indigo hair, a darker asymmetric mantle, warm ivory at the
center, old-gold crescent clasps, and a restrained rose-violet eye accent. Both
portraits use a resolved three-quarter expression and keep the face warmer than
the hair and mantle.

## Provenance and originality boundary

The canonical source is:

`assets/source/schala/v0/portrait/schala_portraits_v0.json`

SHA-256:

`55f5ba865ef60e0e663268f9dc7e3cbccc556b5fc42b0a72f8e4732c769ea3d9`

Every source pixel is represented by one hexadecimal palette index. The rows
were authored on clean native-size canvases. No ROM, save, emulator state,
extracted NPC tile, extracted playable-character tile, official artwork, or
imported bitmap layer was inspected or used while placing the pixels.

The two generated concepts were consulted only for high-level silhouette,
material, and mood:

- `schala_playable_concept_v0.png`:
  `4799352c9e4a273bc88be56e1f9d472b1a1723411956857160ab89919d7bfd45`;
- `schala_playable_sprite_reference_v1.png`:
  `8b9d38332eb4b1b7f66ad5ce4bff995772fa890cb3561bcb62ba6f42f9fcc456`.

The v1 reference was created with the OpenAI built-in image-generation
workflow. Its exact prompt is preserved at
`assets/concepts/schala_playable_sprite_reference_v1.prompt.txt`, SHA-256
`fe153468cd3363f92482546e4cda930ec13b989064751216adb8a583c237b611`.
The earlier v0 generator and prompt remain unknown rather than inferred.

Both are recorded as `generated-concept-reference`, `rom_eligible: false`, and
`pixels_or_palette_sampled: false`. Neither concept file is an input to the
packer.

The source-controlled provenance and output manifest is:

`assets/source/schala/v0/manifest.json`

SHA-256:

`e5f83ca8c2f0acecdda684d90f89e13f243ae62457fdcd08083593e41f605fa5`

## Deterministic build

Builder:

`tools/build_schala_portraits_v0.py`

Builder version: `1.0.0`  
Builder SHA-256:
`9960def61ea76a41ef0ecd7c9f38294f6d87f7c599bdbac7139a9b0081f51663`

Reproduction command:

```powershell
python tools/build_schala_portraits_v0.py `
  --output-dir private/build/schala_portraits_v0
```

The builder:

1. validates the 16-entry indexed palette and both native-size row sets;
2. rejects imported/ROM-derived provenance flags;
3. rejects an exact 32x32 crop or common nearest-neighbor reduction of the
   full portrait;
4. packs row-major SNES 4bpp tiles and a 16-color little-endian BGR555 palette;
5. decodes those packed bytes back to indices and fails on any round-trip
   difference;
6. renders the PNG previews from the decoded packed bytes and quantized SNES
   palette, not directly from the source rows;
7. verifies every output against the pinned source manifest.

Generated files remain under ignored `private/` output. They are not ROMs,
patches, saves, or extracted game data.

| Private generated output | Size | SHA-256 |
|---|---:|---|
| `schala_portrait_full_48x48_v0.4bpp` | `0x480` | `dce1df4d6ec2b8322ce684ba017008d19580d23ffb39b7e687414d7451e47ac4` |
| `schala_portrait_preview_32x32_v0.4bpp` | `0x200` | `904e2c54654e23f1db48977a7befd599af4c63e6ee8fbd0752d9bc59bbf20b54` |
| `schala_portrait_palette_v0.bin` | `0x20` | `29c74205a1d5266ab93504e45f7bd40e400f65dd7f72d69e08e4aab601768a20` |
| `schala_portrait_full_48x48_v0.png` | 1,358 bytes | `ab9ac28009c74ed5961b80a9f65c54f75aa9b038093f8dff1610e1a88a8f5364` |
| `schala_portrait_preview_32x32_v0.png` | 1,137 bytes | `3ddcd312b45f67bf95629b16404e74bc0ae4fdb1108dbe48dde7cb006d3b9df2` |
| `schala_portrait_build_manifest_v0.json` | 1,481 bytes | `c452076c89cefd22eaf1d160d04d8108a771a07ca9901bf79cd0e082191511ee` |

## Originality audit support

`audit_reference_tiles_in_memory` compares candidate tiles against
caller-provided comparison tiles, including horizontal, vertical, and combined
flips. Fully transparent tiles and one- or two-pixel coincidences are listed
for review rather than treated as automatic failures. The function has no ROM
or file-reading path, so a future gated audit can decode canonical comparison
tiles in memory without writing extracted copyrighted graphics to disk.

The current full and preview portraits share no non-trivial exact 8x8 tile with
each other.

The project has deliberately not run a comparison against NPC or playable-PC
tiles in this step. Therefore:

- original authored source and deterministic packing: **[verified-static]**;
- concept-to-pixel non-derivation declaration: **[verified-static]** from the
  recorded pipeline and inputs;
- visual quality and final art approval: **[proposal]**, pending human review;
- no-match claim against canonical game tiles: **[gate]**, pending the in-memory
  canonical comparison;
- in-game palette selection, loading, DMA, and rendering:
  **not verified-runtime**.

## Tests

`tests/test_schala_portraits_v0.py` contains ten focused checks covering:

- canonical source and output hashes;
- native dimensions and distinct canvas IDs;
- non-ROM-eligible concept declarations;
- four-bit source indices and a 16-entry palette;
- exact `0x480`, `0x200`, and `0x20` packed sizes;
- lossless SNES 4bpp round trips;
- indexed PNGs rendered from packed bytes and the quantized palette;
- no exact crop, common nearest-neighbor resize, or shared non-trivial tile
  between the two portraits;
- deterministic private-output reproduction;
- exact and flipped in-memory match detection plus trivial-tile handling.

Run:

```powershell
python -m unittest tests.test_schala_portraits_v0 -v
```

Passing these tests makes the portraits ROM-ready in source format only. It
does not allocate a graphics index, approve an expanded-ROM address, or prove
logical PC `$07` in any runtime path.
