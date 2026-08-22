# Project Epoch: Schala portrait originality audit v0

Status: bounded canonical-ROM comparison complete  
Evidence: **verified-static**  
Evidence date: 2026-07-25  

## Result

The original packed Schala portraits produced **zero matches** against the
known uncompressed vanilla menu-portrait tiles:

| Comparison | Result |
|---|---:|
| Candidate tiles presented | 52 |
| Non-trivial candidate tiles compared | 48 |
| Trivial candidate tiles excluded | 4 |
| Canonical reference tiles compared | 252 |
| Trivial reference tiles excluded | 0 |
| Exact palette-index matches, including H/V/HV flips | 0 |
| Visible-pattern matches after palette-index renaming | 0 |

The four excluded candidate tiles are tiles 0, 5, 6, and 18 of the 48x48
portrait. They contain zero, one, zero, and zero visible pixels respectively.
No 32x32 preview tile was excluded. Blank tiles and tiles containing at most
two non-zero pixels are deliberately treated as uninformative coincidences,
not as evidence for or against originality.

This clears the bounded uncompressed-menu-portrait comparison gate. It does
not claim that every graphic in the ROM was searched.

## Exact audited inputs

The command refuses to compare unless the complete, headerless ROM has all
three canonical identity properties:

| Canonical ROM property | Required value |
|---|---|
| Size | `0x400000` bytes |
| SHA-1 | `de5822f4f2f7a55acb8926d4c0eaa63d5d989312` |
| SHA-256 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |

Only file range `$3F0000-$3F1F7F` is decoded. It contains `0x1F80` bytes, or
252 aligned SNES 4bpp tiles: seven 48x48 menu portraits at 36 tiles each.
The canonical ROM remains a private runtime input.

The candidates are rebuilt in memory from
`assets/source/schala/v0/portrait/schala_portraits_v0.json`, SHA-256
`55f5ba865ef60e0e663268f9dc7e3cbccc556b5fc42b0a72f8e4732c769ea3d9`.
The audit decodes the resulting packed bytes rather than comparing directly
against the JSON rows:

| Packed candidate | Size | SHA-256 |
|---|---:|---|
| `schala_portrait_full_48x48_v0.4bpp` | `0x480` | `dce1df4d6ec2b8322ce684ba017008d19580d23ffb39b7e687414d7451e47ac4` |
| `schala_portrait_preview_32x32_v0.4bpp` | `0x200` | `904e2c54654e23f1db48977a7befd599af4c63e6ee8fbd0752d9bc59bbf20b54` |

## Comparison method

`tools/audit_schala_portrait_originality.py` performs two comparisons for
each non-trivial candidate tile:

1. exact 4bpp palette-index equality;
2. equality of visible region geometry after renaming non-zero palette
   indices by first occurrence.

Both checks include identity, horizontal, vertical, and combined
horizontal/vertical reference transforms. Pattern comparison keeps index zero
fixed, so it preserves the transparent/background mask while ignoring how the
visible colors happen to be numbered.

Palette-invariant matches would be review leads only. A common silhouette or
simple partition can coincide without copied pixels; single-visible-index
patterns are therefore explicitly marked high-risk for false positives. Even
an exact match would require human provenance review before a copying
conclusion. This run produced neither kind of match.

The report contains only hashes, counts, candidate/reference tile indices, and
reference file offsets when matches exist. It never emits or writes canonical
tile bytes, decoded reference pixels, or reference palettes.

## Reproduction

Tool version: `1.0.0`  
Tool SHA-256:
`06ce3802c8fe56d652e5dd40e0d4936a975b2c3c108e4db514a8402cce62c700`

Run:

```powershell
python tools/audit_schala_portrait_originality.py `
  --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
```

The deterministic metadata-only JSON report is printed to standard output.
No reference-art output file is created.

Focused tests:

```powershell
python -m unittest tests.test_schala_portrait_originality_audit -v
```

`tests/test_schala_portrait_originality_audit.py` SHA-256:
`f991947345bb8ff2cc7f8209825b99ee6a7469550c5e69d520c079b1b0e70200`

All five tests pass. They cover visible-index renaming with zero pinned,
flipped exact and renamed-pattern detection, trivial-tile exclusion, aligned
4bpp decoding, and rejection of an unpinned ROM.

## Coverage limit

This audit does **not** cover compressed NPC graphics, field sprites, battle
sprites, animation frames, or arbitrary 4bpp-looking data elsewhere in the
ROM. In particular, it does not compare against Schala's compressed NPC
sprite data. The no-match statement is strictly:

> The two new packed Project Epoch portrait assets share no non-trivial exact
> or visible-palette-renaming-invariant 8x8 tile pattern with the canonical
> uncompressed menu-portrait range `$3F0000-$3F1F7F`, including H/V/HV flips.

Independent authorship remains supported separately by the source provenance
and clean target-size authoring process. This audit is corroborating evidence,
not a substitute for that provenance.
