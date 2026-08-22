# Chrono Trigger compressed sprite reference-corpus audit

Status: `verified-static` for the bounded canonical tables and decoder results
described here.

This audit creates a metadata-only reference corpus for later Project Epoch
sprite-originality checks. It does not install anything and it does not claim
that any packet is Schala. The conservative comparison corpus is all 241
structurally valid compressed pointer entries `$07-$F7`; the narrower
descriptor-selected subset contains 237 of those packets.

## Canonical gate and sources

The command rejects the input before table parsing unless it is the exact
headerless Chrono Trigger US Rev0 ROM:

- size: `0x400000`
- SHA-1: `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- SHA-256:
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`

The implementation pins `references/ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1` and the relevant local source
files:

- `bank_C0.asm`, SHA-256
  `b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8`:
  NPC load `$C0:4590-$C0:46DE`, enemy load and direct/raw branch
  `$C0:46DF-$C0:485F`
- `bank_C3.asm`, SHA-256
  `11aa3492823ef8096961e1c129e4a5ee83418f6d1e19584455ff894d919ba134`:
  decompressor `$C3:0557-$C3:08B2`
- `bank_E4.asm`, SHA-256
  `160bdd0ef4791f81a468ca0088f65a79fa6fbd638584fece50d6735950b29fda`:
  descriptor and graphics-table labels

The read-only canonical ranges are:

| Table | Exact range | Shape | SHA-256 |
| --- | --- | --- | --- |
| PC/NPC/enemy graphics pointers | file `0x242000`, `$E4:2000-$E4:22FF` | 256 x 3 bytes | `a4929e157e37543fee84c0ad87a8dd3cd7e23e864648401fdbd58652b16afaa4` |
| NPC descriptors | file `0x24F023`, `$E4:F023-$E4:F522` | 256 x 5 bytes | `17ae540728c200cf02d60943b8ccdae87edc8cb425e603a24343c078732e3b8a` |
| Enemy descriptors | file `0x24F600`, `$E4:F600-$E4:FFFF` | 256 x 10 bytes | `347a3f7202e02581deca02d1fbabdb34e1fa5ed4548ab0731fa4af9a852fb287` |

The full pointer table is 256 entries. Its non-PC tail starts at index `$07`
and is 249 entries, not 256. Canonically, pointer slots `$F8-$FF` are null.
The structurally decoded compressed catalog is the 241 entries `$07-$F7`;
the seven explicitly pinned raw playable-PC sources `$00-$06` are never sent
through this decoder.

## Descriptor selection and the direct/raw distinction

The graphics selector is descriptor byte `+0`.

The audit retains aliases for:

- all 256 NPC descriptor IDs; and
- normal enemy IDs `$00-$F7`, all 248 records.

Their 504-byte selector vector has SHA-256
`97dc46cf43944d991b421162d2d7937a1c6fbb2a48061ff4d487b989586a6c53`.
This selects 237 unique graphics indexes and 237 unique pointers, with no
aliases at the pointer level.

The branch at `$C0:477A` compares the enemy/script ID, not the graphics-table
index. Therefore enemy IDs `$F8-$FF` are a separate direct/raw path. Their
eight 10-byte records occupy `$E4:FFB0-$E4:FFFF`, hash to
`273b7449cca59c3bce3e42af2c9a112ba3dcf5cc921870eb156c1af20b38e503`,
and carry selector sequence:

`03 06 06 06 00 00 00 00`

That selector sequence hashes to
`174cc6b1e3e2761d4a89171aec4272f8bcd69e7cd5bf5720902373954c0c7aac`
and targets the pinned raw PC pointer indexes. The 248 normal enemy records
at `$E4:F600-$E4:FFAF` independently hash to
`6f029d2969267d7a94367f68144a6ccc02af03e4005bfc0f9a4030fbd989a35a`.

Do not conflate those direct enemy IDs with pointer-table slots `$F8-$FF`:
the latter are separately null and unreferenced by this descriptor audit.

Four structurally valid compressed catalog entries are not selected by the
audited NPC and normal-enemy descriptors:

- `$47`
- `$4A`
- `$CC`
- `$E5`

They remain in the conservative 241-packet reference corpus. “Catalog-only”
means only that this descriptor scan does not select them; it is not proof
that the engine never uses them elsewhere.

## Independent decoder contract

The auditor does not infer a packet end from the next pointer. For each
selected catalog pointer it:

1. requires a `$C0-$FF` HiROM pointer;
2. reads the packet's own initial segment length;
3. takes the initial boundary marker's top bits as the 12- versus 11-bit
   back-reference format selector;
4. consumes control bits least-significant bit first;
5. decodes back-reference lengths as encoded high bits plus 3;
6. follows addendum boundaries only when their low-six-bit partial-group count
   is nonzero; and
7. stops only at that packet's zero-count boundary marker.

The engine's zero-control fast path always copies eight literals and does not
consult the partial-group counter. The strict decoder therefore accepts a zero
control only for an eight-control group and rejects a zero control paired with
any other addendum count.

The implementation fails closed on a zero or forward distance, any truncated
literal/token/header, a nonmonotonic addendum, a source-bank crossing, output
above `0x10000`, or output not aligned to one `0x20`-byte SNES 4bpp tile.

All 241 canonical catalog packets independently decode with the 12-bit
variant. None crosses its source CPU bank.

## Results

| Partition | Packets | Compressed bytes | Decompressed bytes | 4bpp tiles | Addenda |
| --- | ---: | ---: | ---: | ---: | --- |
| Conservative compressed catalog `$07-$F7` | 241 | 540,847 | 699,872 | 21,871 | 211 with one, 30 with none |
| NPC + enemy `$00-$F7` descriptor-selected subset | 237 | 540,276 | 699,200 | 21,850 | 207 with one, 30 with none |

Decompressed packet sizes range from 128 through 23,776 bytes. Compressed
packet sizes range from 39 through 18,466 bytes.

The aggregate digest is framed unambiguously as:

`SHA-256(domain || repeated(index_u8 || decoded_length_u32le || decoded_bytes))`

Rows are ordered by ascending graphics index. The domain is the ASCII bytes
`ProjectEpoch/ct-compressed-sprite-corpus/v0` followed by one NUL byte.

- conservative 241-packet digest:
  `01fe041352872a2efd8ba554722c71e71b9b20f70a32ee2ef33921286df2e418`
- descriptor-selected 237-packet digest:
  `87732136b365151b9d71d955c9bf196cf655df69ba05c1bb12b5c94378a0ac65`

The pinned report keeps only metadata: index, pointer, sizes, tile count,
format, addendum/segment counts, decoded SHA-256, selection flag, and complete
NPC/normal-enemy alias lists. It contains no ROM bytes, decoded bytes, pixel
data, image, save, state, trace, or patch.

## Reproduction

Run the read-only auditor with the project Python:

```powershell
& 'python' `
  'tools\audit_ct_compressed_sprite_corpus.py' `
  --rom 'private\input\rom_archive\Chrono Trigger (USA).sfc'
```

Its only data argument is required `--rom`; JSON is written only to stdout.
There is no output-file option. The emitted UTF-8/LF bytes must exactly match:

- `references/ct_compressed_sprite_corpus_v0.json`
- size: 147,507 bytes
- SHA-256:
  `ae7fb21d2f13cc1d58fa64fbe76a7086a08c0a10c28c7bd88aae857bd3e35f0e`

Run the focused regression:

```powershell
& 'python' `
  'tests\test_ct_compressed_sprite_corpus.py' -v
```

The source artifacts at this evidence point are:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/audit_ct_compressed_sprite_corpus.py` | 34,780 | `5dcba015098dcf5a9ec754a5537f35ab67144f0ac09d166e7644741a74ae990d` |
| `tests/test_ct_compressed_sprite_corpus.py` | 15,431 | `3c861355f5e35552244b258c5a2ba42c0881871615f8c8a1b814f70468f013a8` |
| `references/ct_compressed_sprite_corpus_v0.json` | 147,507 | `ae7fb21d2f13cc1d58fa64fbe76a7086a08c0a10c28c7bd88aae857bd3e35f0e` |

## Evidence boundary

This is `verified-static` evidence for canonical table identity, structural C3
decoding, and the descriptor aliases stated above. It does not:

- identify Schala or a playable PC `$07` sprite;
- make an originality or similarity finding;
- prove the four catalog-only packets unused;
- cover every special, menu, battle-global, or engine-global sprite source;
- provide runtime proof; or
- approve a hook, expanded allocation, ROM mutation, patch, or production
  binding.

The intended next use is a conservative metadata-only originality comparison
against all 241 decoded packets, performed in memory without publishing the
reference pixels.
