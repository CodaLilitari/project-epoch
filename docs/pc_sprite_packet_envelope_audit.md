# Project Epoch vanilla PC sprite-packet envelope audit

Status: `verified-static` metadata audit  
ROM integration: not performed  
Canonical target: headerless Chrono Trigger US Rev0  
Reconstruction: `references/ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`  
Last updated: 2026-07-25

## Executive result

All seven vanilla playable characters use the same size-class-0 frame format:
a `$28`-byte assembly record containing sixteen tile words and four coordinate
pairs. The field renderer builds four sprite objects from each record, decodes
sixteen 4bpp tiles (`$200` bytes), and queues two `$100`-byte transfers.

The animation data stores one-byte frame IDs and reserves `$FF` as its
end/loop value. The largest possible assembly envelope without changing that
format is therefore 255 records (`$00-$FE`), or `$27D8` bytes. Ayla reaches
that exact limit.

Six animation-derived assembly ends coincide exactly with the next canonical
packet pointer. Robo's stored frame bytes require `$DC:C080-$DC:DF6F`, but no
later same-bank pointer proves that `$DC:DF70` is the physical packet end.
The bytes through `$DC:FFFF` remain unclassified and are not free space.

This audit supplies the missing vanilla envelope for Schala's sprite compiler.
It does not allocate data, install a PC `$07` resolver, or prove an
expanded-ROM graphics bank in field or battle.

## Reproduction and copyright boundary

Run from the workspace root:

```text
python tools/audit_pc_sprite_packet_envelopes.py --rom "private/input/rom_archive/Chrono Trigger (USA).sfc"
python -m unittest tests.test_pc_sprite_packet_envelope_audit -v
```

Auditor SHA-256:
`270c340b148568ee153c7417f1daac3396a325ae526616de4c6643dd8184309a`  
Focused-test source SHA-256:
`e3a606f2c1f3b01f0fb6ac2231af33b85dea58ac0e1f31cf9e484617d8341cb2`

The tool requires the canonical ROM identity:

- size: `$400000`
- SHA-1: `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- SHA-256:
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`

It reads ROM data only in memory and emits hashes, addresses, counts, masks,
and ranges. It does not write or print source bytes, decoded pixels, palettes,
assembly records, or images. Eight focused synthetic tests validate the table
gates, four-facing animation division, record parsing, index/flip masks,
offset handling, out-of-window detection, and ROM identity rejection.

## Pinned table contract

`verified-static`

| Structure | Canonical root | Entry shape | PC entries |
| --- | --- | --- | --- |
| graphics pointers | `$E4:2000` | 24-bit pointer | 7 |
| assembly pointers | `$E4:2300` | 24-bit pointer | 7 |
| animation boundaries | `$E4:2600` | 16-bit bank-relative boundary | 8, including the PC6 end |
| sprite descriptors | `$E4:F000` | 5 bytes | 7 |

For PC IDs `$00-$06`, descriptor bytes are
`[graphics=id, assembly=id, palette=id, animation=id, size-class=0]`.
Logical ID `$07` is not another PC descriptor; it reaches occupied NPC data or
the animation end boundary depending on the table.

The relevant decoded instructions are:

- `$C0:448D-$C0:4555`: descriptor and pointer resolution;
- `$C0:CB3A-$C0:CBDB`: facing-block and animation-frame addressing;
- `$C0:CC04-$C0:CDC7`: size-class-0 frame decode and upload queue;
- `$C0:E534-$C0:E686`: horizontally flipped tile decode;
- `$C0:E687-$C0:E934`: non-flipped tile decode;
- `$C0:E952-$C0:E979`: one-cell field allocator;
- `$CC:E97E-$CC:EA30`: active-PC graphics/assembly/animation pointer setup.

## Exact raw graphics windows

`verified-static`

The six same-region ends are the next physical PC start or bank end. Ayla ends
at `$D5:8C00`, the earliest later non-PC graphics pointer in the bounded
canonical `$E4:2015-$E4:22E7` table. All windows are tile-aligned and total
7,264 raw 4bpp tiles.

| PC | SNES window, end exclusive | Bytes | Tiles | SHA-256 |
| --- | --- | ---: | ---: | --- |
| Crono | `$D2:72C0-$D3:0000` | `$8D40` | 1,130 | `76042f388cf45e7cf55574b9fa92fa97d32c7fe8ff4028c01d70019ed51cd56b` |
| Marle | `$D4:0000-$D4:7C40` | `$7C40` | 994 | `a9c78414e6cf797dba1aecef3657a9dd046aaacecd72c92ddccc210394928251` |
| Lucca | `$D3:6B40-$D4:0000` | `$94C0` | 1,190 | `057719bb3ecfdd79b7bca4f3e6e3f49ba5d1fb86f3ca83aa4a5f4832fbd77d92` |
| Robo | `$D4:7C40-$D5:0000` | `$83C0` | 1,054 | `83423301a98103b3370b4d665564c898291a933ca7a509168c2d54268124cb0b` |
| Frog | `$D3:0000-$D3:6B40` | `$6B40` | 858 | `afcdc471602d3add1f44ad87fd3290ecff9fd3f364ab60cbbb06be032818cfb1` |
| Ayla | `$D5:0000-$D5:8C00` | `$8C00` | 1,120 | `9df8eab8777f02acab1709c771bda63dba1a81abc8d1a2840ff464c5fe675c3e` |
| Magus | `$D2:0000-$D2:72C0` | `$72C0` | 918 | `fb506e919f31a5b6b1c50fa06a7d497629105283d39c5316063596237935914a` |

These are raw, directly indexed PC graphics in the audited path, not
compressed NPC packets.

## Assembly record format and envelopes

`verified-static`

Every vanilla PC descriptor selects size class 0. Its frame record is:

| Offset | Size | Proved consumption |
| --- | ---: | --- |
| `$00-$1F` | 16 little-endian words | sixteen tile selections |
| `$20-$27` | 8 bytes | four X/Y coordinate pairs |

The copy path masks each tile word with `$07FF`, giving an encoding envelope of
2,048 tile indices (`$000-$7FF`). Bit `$4000` selects the horizontal decode
path. The audit deliberately assigns no meaning to the remaining high bits.
Frog has an observed `$8000` bit in its referenced envelope; that bit remains
unclassified.

All stored non-`$FF` animation frame bytes were included when deriving the
minimum record span. Every referenced tile index remains inside its
character's exact raw graphics window:

| PC | Assembly envelope, end exclusive | Records | Bytes | Max tile / packet tiles | SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| Crono | `$DC:27B0-$DC:4E70` | 248 | `$26C0` | 989 / 1,130 | `263492d1dd49e0c9a6747bf64734841e5db787e29ca613ef4e4399017690a03e` |
| Marle | `$DC:9AD8-$DC:C080` | 241 | `$25A8` | 993 / 994 | `2824a7be4da3ff40a51910a75d12af21dbac6ccedacb6326fcd44b0256bd5d3b` |
| Lucca | `$DC:4E70-$DC:7490` | 244 | `$2620` | 953 / 1,190 | `d7fde66a7c71a33fb23c3bd5531e8f89241751b08d120f2bcebad09a8b3634ce` |
| Robo | `$DC:C080-$DC:DF70` minimum | 198 | `$1EF0` | 1,013 / 1,054 | `8e8d67ab57dd9ed648ab06781c7066721c610c0a8957d0e72fccd39f153ef5ea` |
| Frog | `$DC:7490-$DC:9AD8` | 245 | `$2648` | 838 / 858 | `ae11b0b72e41cea97b4e216e8a3dc959aa4f699bf7c77dbee012595e3087d559` |
| Ayla | `$DE:0000-$DE:27D8` | 255 | `$27D8` | 1,119 / 1,120 | `5003d41b09d5f557a809388a7036cf1a9dabe897c20961c1b9f9f5c0cc572eea` |
| Magus | `$DC:0000-$DC:27B0` | 254 | `$27B0` | 917 / 918 | `05a78400c3268d0017244c43b80103bf10f9158340f96a610f6bc388717ceee6` |

For Robo only, the bounded interval from `$DC:C080` to the bank end is
`$3F80` bytes with SHA-256
`d03d932e378f25ff77664aaf8ff1084381ccf1ba16d930ec94671bb3000f088e`.
The `$2090`-byte tail after the derived minimum is not classified or
available for allocation.

The largest referenced index across all PCs is below `$0800`, and the audit
found zero references outside the matching raw window. The `$07FF` mask
describes an index encoding capacity of `$10000` raw bytes at 32 bytes per
tile. It is not permission to use a 64 KiB packet: base-address wrap,
bank-local reads, allocation, and runtime timing remain separate constraints.

## Animation boundary results

`verified-static`

The eight values at `$E4:2600` split the PC data at `$E4:3000` into seven
blobs. `$CC:E97E` derives four equal facing blocks from each pair of adjacent
boundaries. Each facing block exposes animation entrypoints at four-byte
intervals. Four bytes is the entrypoint stride, not a fixed sequence-record
size: a sentinel-terminated sequence may continue beyond four bytes, and the
next entrypoint may address a suffix of that sequence.

| PC | Animation blob, end exclusive | Bytes | Bytes/facing | Entrypoints/facing | Max stored frame | SHA-256 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Crono | `$E4:3000-$E4:34A0` | `$4A0` | `$128` | 74 | `$F7` | `43c629e4e3ab32a5bce56189cb4ef7821d920b6c12318aa45edd742eded95dff` |
| Marle | `$E4:34A0-$E4:3880` | `$3E0` | `$0F8` | 62 | `$F0` | `7fc62fe6ed719de9e3448c68d03f90f171ba4b31a420db58a0c9fe20bac751bf` |
| Lucca | `$E4:3880-$E4:3CF0` | `$470` | `$11C` | 71 | `$F3` | `850c331267d16be7b11611d4f69d2120fac8e0f314102794b47b09fa7c200607` |
| Robo | `$E4:3CF0-$E4:4160` | `$470` | `$11C` | 71 | `$C5` | `3fd15908dd98720e53c3601b3750ec587717997d1b7f1ab65be6ce69ccf57fe6` |
| Frog | `$E4:4160-$E4:45C0` | `$460` | `$118` | 70 | `$F4` | `48ec0306a22490165efb296fad3dc4f8353c49db10f01c28713bb80776fd3ceb` |
| Ayla | `$E4:45C0-$E4:4B00` | `$540` | `$150` | 84 | `$FE` | `ece49a6d2c7dc2af775489f49b917c55672991c766758c3444ba0b2545b87717` |
| Magus | `$E4:4B00-$E4:4ED0` | `$3D0` | `$0F4` | 61 | `$FD` | `2875f534a1baa2e7064a62f05d5efaaf9e130dea9de195e66f256571c2464896` |

The observed canonical range is 61-84 four-byte-spaced entrypoints per facing
and `$3D0-$540` bytes per complete four-facing blob. These are measured
examples, not an inferred engine maximum or 61-84 independent animation
records. The hard unchanged-format constraint proved here is that `$FF`
cannot be a normal frame ID.

This envelope audit intentionally does not assign meanings or timing to those
entrypoints. A separate, prospective
`docs/schala_animation_semantic_contract_v0.md` audit must map the paired
`$E4:2800` timing/control stream, sentinels, callers, and fixed versus
data-driven selectors before Schala's animation IDs are bound.

## Decoded and field-transfer limits

`verified-static`

For size class 0:

- four sprite objects are built per frame;
- sixteen tile words are decoded;
- one decoded tile is 32 bytes;
- total decoded source data is `$200` bytes per frame;
- the field upload queue receives two `$100`-byte transfers;
- one field sprite-cache cell is allocated for the frame.

These numbers are the vanilla PC field path's hard packing target. The audit
does not yet promote a total battle-frame DMA budget to `verified-static`;
battle initialization and rendering use additional buffers and paths that
must be checked during the logical-ID adapter implementation.

## Consequences for Schala's compiler

1. A native-compatible Schala frame must compile to at most four sprite
   objects and sixteen tile words. A 24x32 or 40x40 source canvas is only an
   authoring canvas; dimensions alone do not prove that its occupied cells can
   be covered by four vanilla objects.
2. The current 352-unique-tile source ceiling is below both the largest
   measured raw PC packet (Lucca, 1,190 tiles) and the `$07FF` index encoding
   capacity. This is a data budget result, not an allocation result.
3. The current 90-frame authoring ceiling is below the 255-record unchanged-
   format limit. It still needs a deterministic assembly compiler and a
   complete animation-entrypoint semantic map.
4. Schala's animation data must have four equal facing blocks if the common
   selector remains in use. Her final entrypoint count and variable-length
   sequences must follow her required animations, not copy a vanilla
   character's count.
5. Relocated graphics remain blocked on the generic non-flip decoder and the
   fixed-bank animation readers identified in
   `docs/pc7_graphics_menu_hook_audit.md`.

## Remaining unknowns and gates

- Robo's `$DC:DF70-$DC:FFFF` tail is unclassified.
- The observed Frog `$8000` assembly-word bit is not assigned a meaning.
- The paired timing/control family rooted at `$E4:2800` still needs the
  prospective semantic-contract audit and a relocated-bank adapter.
- The exact semantic name of every animation entrypoint and every special
  field/event pose remains to be mapped before the full sheet is authored.
- Battle-specific staging, transfer timing, and expanded-bank reads need
  trace-backed regression tests.
- Menu walking sprites, overworld sprites, portraits, and effect sprites are
  separate formats and allocations.
- No ROM space is declared free, and no production hook is installed.
