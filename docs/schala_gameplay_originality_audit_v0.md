# Project Epoch: Schala gameplay originality audit v0

Status: bounded comparison complete  
Evidence: `verified-static`  
ROM integration: not performed  
Last updated: 2026-07-25

## Result

The revised packed Schala gameplay foundation has:

- **zero exact palette-index tile matches**; and
- **zero palette-renaming-invariant visible-pattern matches**

against all 7,264 raw 8x8 tiles in the seven canonical playable-character
graphics windows, including horizontal, vertical, and combined flips.

This is strong bounded evidence that the current Schala pixels are new data,
not a recolor or tile copy of a vanilla playable character. It is not a
near-match or artistic-similarity proof, and this playable-PC audit does not
cover NPC/enemy graphics, portraits, assembly data, animation data, or VFX.
The later companion `docs/schala_npc_originality_audit_v0.md` separately
covers the one 79-tile packet reached through the documented Schala NPC
chain; it is not a global NPC/enemy result.

## Canonical inputs

The audit rejects any ROM that is not the headerless Chrono Trigger US v1.0
image with SHA-1:

`de5822f4f2f7a55acb8926d4c0eaa63d5d989312`

Revised Schala gameplay source:

`assets/source/schala/v0/gameplay/schala_gameplay_foundation_v0.json`

SHA-256:

`9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2`

## Reference coverage

The seven `$E4:2000` pointers select raw, tile-aligned PC graphics. Same-bank
windows end at the next PC start or the bank boundary. Ayla ends at
`$D5:8C00`, the earliest non-PC graphics pointer in the bounded canonical
`$E4:2015-$E4:22E7` table.

| PC | SNES start | File range | Bytes | Tiles |
|---|---:|---:|---:|---:|
| Crono | `$D2:72C0` | `$1272C0-$12FFFF` | `$8D40` | 1,130 |
| Marle | `$D4:0000` | `$140000-$147C3F` | `$7C40` | 994 |
| Lucca | `$D3:6B40` | `$136B40-$13FFFF` | `$94C0` | 1,190 |
| Robo | `$D4:7C40` | `$147C40-$14FFFF` | `$83C0` | 1,054 |
| Frog | `$D3:0000` | `$130000-$136B3F` | `$6B40` | 858 |
| Ayla | `$D5:0000` | `$150000-$158BFF` | `$8C00` | 1,120 |
| Magus | `$D2:0000` | `$120000-$1272BF` | `$72C0` | 918 |
| **Total** | | | `$38C00` | **7,264** |

The tool validates all seven pointer-table entries before comparing. It reads
and decodes the reference windows only in memory. No reference tile bytes,
decoded pixels, palettes, or images are written or included in an artifact.

## Comparison policy

The final packed source contains 159 tile occurrences. Candidate and reference
tiles with at most two visible pixels are listed as trivial and excluded from
automatic matching; 59 candidate and 59 reference occurrences fell into that
class.

Every remaining tile is checked in four orientations:

1. identity;
2. horizontal flip;
3. vertical flip; and
4. horizontal plus vertical flip.

Two comparisons are made:

- exact 4bpp palette-index geometry;
- visible-region geometry after nonzero palette indices are renamed by first
  occurrence while transparent index zero remains fixed.

The second check detects a copied shape even if its visible color indices were
renumbered.

## Incidental-match correction

The first audit of source SHA-256
`2d4779bb5a201e407acb0f0e662097a1344753b8c4c7cf1322f53b8c9eb92b88`
reported nine exact and fourteen visible-pattern matches. Every result was the
same kind of sparse top-left cell fragment: only three or four outline pixels
at the edge of a front-facing field frame.

No reference tile was displayed, rendered, exported, or supplied to the pixel
author. Using only the match metadata, the redundant fragment was removed
from five Schala frames. Their adjacent center cells already contained the
retained silhouette edge. The revised audit then returned zero matches in
both comparison modes.

This adjustment is recorded in the editable source and manifest. It does not
derive Schala pixels from a canonical sprite; it removes an independently
authored incidental coincidence without exposing the reference pixels.

## Reproduction

```text
python tools/audit_schala_gameplay_originality.py --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
python -m unittest tests.test_schala_gameplay_originality_audit -v
```

Tool SHA-256:

`77f6724c5a0bfc73e26239337325f0a094920954023978aae97c641a0804f0be`

Seven focused audit tests pass. Combined with the eleven gameplay
source/packing checks, the current foundation has eighteen focused checks.

## Remaining originality gates

- extend the current one-packet Schala-family comparison to the complete
  future candidate sheets and the conservative 241-packet compressed corpus;
- perform bounded near-match and silhouette review without exporting
  copyrighted reference graphics;
- repeat the audit after the complete field and battle frame set exists;
- obtain human review at 1x scale; and
- keep concept images, official art, extracted pixels, and reference palettes
  out of every ROM-eligible source and build path.
