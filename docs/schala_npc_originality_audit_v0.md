# Schala NPC originality audit v0

## Outcome and evidence boundary

This source-only audit compares two exact Project Epoch Schala candidate sets
with one canonical compressed sprite packet reached through a pinned static
chain:

`location $14E -> event $0CE -> object $0F -> NPC $09 -> gfx selector $26`

The canonical byte chain and comparison result are `verified-static`. The
human-readable identity **Schala** is `documented`, not runtime-proved: the
pinned Pseudoarc/jetsoftime source at commit
`3af9a5a8fa5db7cd47740c791fa6580f7a4efa44` identifies location `$14E`,
object `$0F` as Schala
([source lines 188-201](https://github.com/Pseudoarc/jetsoftime/blob/3af9a5a8fa5db7cd47740c791fa6580f7a4efa44/sourcefiles/bossrandoevent.py#L188-L201)).

Both candidate sets have zero exact-index matches and zero
palette-renaming-invariant matches against the nontrivial tiles in that one
packet:

| Scope | Total tile occurrences | Excluded as trivial | Compared | Exact | Palette-pattern |
|---|---:|---:|---:|---:|---:|
| Canonical selector `$26` reference | 79 | 1 | 78 | n/a | n/a |
| Gameplay foundation | 159 | 59 | 100 | 0 | 0 |
| Glass Focus | 174 | 80 | 94 | 0 | 0 |

This is deliberately not a global NPC/enemy-corpus originality result. It
does not analyze near matches, silhouettes, animation, assembly layout,
palettes as art, or runtime semantic identity.

## Canonical chain

The audit first hash-gates the complete headerless Chrono Trigger US Rev0 ROM:

- size: `4194304`
- SHA-1: `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- SHA-256:
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`

It then verifies these exact stages before comparing any tiles:

| Stage | Canonical fact | SHA-256 |
|---|---|---|
| Location record | `$F6:1244-$F6:1251`, file `0x361244`, 14 bytes | `24cd1462f7836fd003542aa24d3e54d31a22b2f13ac097b60fca735619270aa2` |
| Event field | `$F6:124C`, file `0x36124C`, event `$0CE` | `5be57e88da9e860c2cd355ae7cbb4d18f972a0f751d61b79c08e03ea08f7a952` |
| Event pointer entry | `$FC:FC5A`, file `0x3CFC5A`, points to `$F9:69CE` | `8b6087b2ccd3f258baf933877765dcc21310f921b0b8019124de11aa102c1eff` |
| Compressed event packet | file `0x3969CE`, 942 bytes | `083fe7d4acda8e841ebd115bf32e205caec728e1c1a62c7550a412fcf33d9439` |
| Decompressed event packet | 1,435 bytes, 17 objects | `0fdd87278dbeb3e95b385e1493ffb507e1e755e54c36a0055cdac9fa60e03179` |

The decompressed event parser requires object `$0F` to begin at event-data
offset `$0569`. The command there must be opcode `$82` with NPC operand `$09`;
the next object begins at `$057D`.

The sprite tables and descriptor family are separately pinned:

- graphics pointer table `$E4:2000-$E4:22FF`:
  `a4929e157e37543fee84c0ad87a8dd3cd7e23e864648401fdbd58652b16afaa4`
- NPC descriptor table `$E4:F023-$E4:F522`:
  `17ae540728c200cf02d60943b8ccdae87edc8cb425e603a24343c078732e3b8a`
- NPC `$09` at `$E4:F050`: fields
  `[gfx $26, assembly $1B, palette $80, animation $3B, size $00]`,
  SHA-256
  `dcfb1fcb9573e7cbf2cba1290b2bd187889a84efdbb67a4ca7d654288158eae8`
- NPC `$CD` at `$E4:F424`: fields
  `[gfx $26, assembly $1B, palette $9F, animation $3B, size $00]`,
  SHA-256
  `41e0318fa8379ff61f108f09ea78356903f09f780d2d52af2a70610dc8243186`

Across all 256 canonical NPC descriptor records, `$CD` is the only record
with the same gfx/assembly/animation/size tuple as `$09`, and it differs from
`$09` only in the palette byte. This is a static descriptor-family statement,
not a runtime claim that every use of `$09` or `$CD` is semantically Schala.

Selector `$26` has one pointer-table occurrence and resolves through
`$E4:2072` to `$D9:E2CE`:

- pointer-entry SHA-256:
  `7822e4cd703e8fb82ba2766461562c543e736992295644f3fa683f3a0da1005f`
- compressed packet: 2,447 bytes, SHA-256
  `db9b1e5967ad25ba7af2692e077fa7da73e3d9659280d81fbe8f00c64109e1a3`
- decompressed packet: 2,528 bytes / 79 4bpp tiles, SHA-256
  `69322758b77fff5701cb0d5edb4ca34ab4109c2313ececd37bc018106fe84b73`
- compression form: 12-bit back-references, zero addenda

The sprite packet is decoded in memory by importing the strict decoder from
`tools/audit_ct_compressed_sprite_corpus.py`; the logic is not copied into
this audit. The location event uses the established event-packet decoder and
parser from `tools/audit_location_event_items.py`.

Before the first imported helper call, the audit verifies every
behavior-bearing dependency by exact byte size and SHA-256:

| Dependency | Size | SHA-256 |
|---|---:|---|
| `tools/audit_ct_compressed_sprite_corpus.py` | 34,780 | `5dcba015098dcf5a9ec754a5537f35ab67144f0ac09d166e7644741a74ae990d` |
| `tools/audit_location_event_items.py` | 39,560 | `cb39dd4485e6330c4f9d5b8817fe8e6a161cb2e965020cb1cd10a3fd30f7812a` |
| `tools/audit_schala_gameplay_originality.py` | 14,624 | `77f6724c5a0bfc73e26239337325f0a094920954023978aae97c641a0804f0be` |
| `tools/build_schala_gameplay_foundation_v0.py` | 25,402 | `e43f5d5b6fe30c5746ef04822f98f120165ecbea8393143e5b93941fdeb6cf8f` |
| `tools/validate_schala_glass_focus_pulse_v0.py` | 59,563 | `0a51bd8b6ccb30893e5adc8da78f00b61f98242a5ba0daf3403f33e2f4e3f93f` |

These identities and their roles are serialized in the metadata report.
Missing or drifted dependency bytes abort before the canonical-ROM helper,
event decoder, sprite decoder, candidate packer, transform logic, or Glass
validator can run.

## Candidate inputs

The gameplay set is read only from:

`assets/source/schala/v0/gameplay/schala_gameplay_foundation_v0.json`

- size: `25193`
- SHA-256:
  `9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2`
- 10 source assets
- framed decoded-candidate SHA-256:
  `d367e7dd2c163aa47bdaf93df466b9767d64d51a99be5f42a0d39bec978c580b`

The Glass Focus set is read only from:

`assets/source/schala/v0/focus/glass_focus_pulse_v0.json`

- size: `32967`
- SHA-256:
  `cb705f5faa5b01fd365c57d69428a64c3df5cb40170b68130043d4c4d3dd0869`
- 12 visual assets: six body frames and six Focus inserts
- framed decoded-candidate SHA-256:
  `3b7504fb82ceecb1afa39b5e0019e5b552a6f6575d3a7792f3200402acf2dd9d`

Its source-only manifest is also pinned at 6,284 bytes with SHA-256
`dabbaa5b6a85d295f7726aa44683d96d6a8e0fbbf2d052e47c9b5d1b711c73f0`.
The audit invokes the established source validation and manifest-core checks
before accepting those candidates.

Any source hash, packed-candidate hash, asset count, tile count, exclusion
count, reference hash, or match-count change causes the audit to fail closed.

## Comparison policy

The comparison is tile-occurrence based and uses the existing Project Epoch
method:

1. Decode the canonical packet and candidates as SNES 4bpp in memory.
2. Count but exclude any tile occurrence with at most two non-zero pixels.
3. Index each retained canonical reference tile in identity, horizontal,
   vertical, and combined horizontal/vertical orientations.
4. Check exact palette-index equality.
5. Check a palette-renaming-invariant pattern where transparent index zero is
   fixed and non-zero palette labels are renamed by first appearance.

Zero matches is bounded evidence against exact or palette-label-renamed copies
under those four orientations. It is not proof against resemblance or
derivation under any other metric.

## Reproduction

The command accepts only `--rom` and writes deterministic UTF-8/LF JSON to
standard output:

```powershell
& 'python' `
  tools\audit_schala_npc_originality.py `
  --rom 'private\input\rom_archive\Chrono Trigger (USA).sfc'
```

The checked metadata report is:

`references/schala_npc_originality_audit_v0.json`

The focused regression is:

```powershell
& 'python' `
  tests\test_schala_npc_originality_audit.py -v
```

The 24 focused tests cover the behavior-dependency gates and their
before-helper ordering; the ROM gate; location, event, table, descriptor,
pointer, and packet mutations; descriptor-family/palette relation; strict
decoder use; packet hashes and sizes; both candidate source gates; bounded
count and match drift; report schema; report-generation independence;
byte-identical stdout; and no filesystem writes.

## Source-controlled artifacts

| File | Size | SHA-256 |
|---|---:|---|
| `tools/audit_schala_npc_originality.py` | 38,224 | `1e81065d4fbb9041a7c671f19b8a52b5971d1beb8a908e74d38c8a7a2a99b348` |
| `tests/test_schala_npc_originality_audit.py` | 19,794 | `af6b7b5e7880c70588aceb7f5b816d3ae4f47e3e5832732721c200f4986115c7` |
| `references/schala_npc_originality_audit_v0.json` | 10,708 | `2ae3250385c2c93f0ff159380c834e0e28a6cc0ab99254d8e4f7b9b4ba2b2848` |

The report contains only bounded addresses, descriptor field values, hashes,
sizes, and counts. It contains no packet bytes, decoded pixels, palettes, or
images. The tool has no output-file option and does not mutate the ROM or
write a patch, save, state, trace, decoded packet, rendered asset, or other
artifact.
