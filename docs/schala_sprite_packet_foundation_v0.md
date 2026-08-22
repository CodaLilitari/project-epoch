# Project Epoch Schala sprite-packet foundation v0

Status: partial native-shaped packet foundation  
Production ROM integration: not performed  
Runtime verification: supported Lucca-slot field load/movement only  
Last updated: 2026-07-26

## Result

Schala's ten original gameplay frames now compile into the same bounded
size-class-0 frame shape used by all seven vanilla playable characters:

- ten `$28`-byte assembly records;
- sixteen little-endian tile words per record;
- four signed X/Y coordinate pairs per record;
- four 16x16 sprite-object slots per frame;
- one raw, deduplicated SNES 4bpp graphics packet;
- one sixteen-color BGR555 palette.

The compiler reconstructs every source pixel exactly from the serialized
graphics and assembly packets. This proves that the current ten frames fit
the audited packet envelope. A separate private diagnostic now verifies that
the first four cardinal records can be fetched and rendered after a real
Continue/load and field movement in Lucca's supported slot. Neither result
proves expanded-ROM reads, complete animation semantics, battle staging,
full-palette selection, or logical PC `$07`.

The canonical pixels remain:

`assets/source/schala/v0/gameplay/schala_gameplay_foundation_v0.json`

Source SHA-256:
`9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2`

They are original Project Epoch target-grid art. No NPC or playable-character
sprite data is consumed by this compiler.

## Deterministic compiler

Tool:

`tools/build_schala_sprite_packet_foundation_v0.py`

Tool SHA-256:
`dc264823fdb479fef3c0a0d94e68da40b6bb0e51040c94392e678f970c3c60fb`

Focused tests:

`tests/test_schala_sprite_packet_foundation_v0.py`

Test-source SHA-256:
`d2c425f57b15cdfe8661d677a6c19e61f937afd71f6f4f09e817b738dfa879a7`

Reproduction:

```text
python tools/build_schala_sprite_packet_foundation_v0.py \
  --output-dir private/build/schala_sprite_packet_foundation_v0
python -m unittest tests.test_schala_sprite_packet_foundation_v0 -v
```

Ten focused tests pass. Generated artifacts stay under the ignored
`private/build` tree and must not be committed.

## Packet measurements

| Output | Size | SHA-256 |
| --- | ---: | --- |
| raw graphics | `$0A20` (81 tiles) | `61bdecf43ad967ff5bd3c7604d7ce0708305a516e1e17d7cbbcabe949f3c791f` |
| assembly | `$0190` (10 records) | `11c7d77ec789853aca496b1bd38fdef35c437c31407000af74c7aa498bebb540` |
| palette | `$0020` | `782a063ffc99087cca1b64876cd024a5c5c7e6c6193c8f9ff224e9ed88ead5ea` |
| frame map | `15,727` bytes | `0a4ca814b39de2e10eb120fbf17a5359dc20c7d2819645a7a11f75af68c6c814` |
| reconstructed QA sheet | `3,219` bytes | `de89381fc1c3a81a6ee116d60700e8f0ab50ea259d15766f1de9965a046aacf2` |

Tile zero is an explicitly reserved transparent tile. The other eighty tiles
are the exact unique nontransparent source tiles already measured by the art
foundation. The compiler emits no `$4000` horizontal-flip words; independently
authored left/right keys remain independent.

The reconstructed QA sheet has the same hash as the earlier packed-source QA
sheet because reconstruction is pixel-exact.

## Object-cover algorithm

For each source frame, the compiler:

1. marks every 8x8 cell containing a visible pixel;
2. enumerates 2x2-tile object origins capable of covering those cells;
3. chooses the smallest set of at most four objects in which every visible
   cell is covered exactly once;
4. breaks deterministic ties by outside-canvas transparent cells,
   inside-canvas transparent cells, and coordinate order;
5. writes transparent tile zero for object cells beyond the authoring canvas;
6. pads an unused object slot with transparent tiles when fewer than four
   objects are required.

Nine current frames require four active objects. The middle downward-walk key
requires three; its fourth engine slot is fully transparent. All visible cells
are disjoint across active objects, avoiding order-dependent overlap.

The 24x32 and sparse 40x40 canvases sometimes need an object to extend one
transparent 8x8 cell beyond the canvas. No visible pixel is clipped or
invented.

## Serialized order and coordinates

The first `$20` bytes contain the sixteen tile words in the field decoder's
stream order: the two top tiles of objects 0-3, followed by the two bottom
tiles of objects 0-3. The last eight bytes contain the four signed X/Y pairs.

The deterministic authoring anchor is source bottom-center. That anchor makes
the packet self-consistent and exactly reconstructable, but its final actor
origin still requires emulator calibration before installation. The compiler
rejects any coordinate outside signed-byte range, any tile index above
`$07FF`, any nontransparent frame needing more than four objects, and any
serialized reconstruction mismatch.

The vanilla envelope and field decode evidence are recorded in
`docs/pc_sprite_packet_envelope_audit.md`.

## Supported-slot runtime smoke

`verified-runtime` for the private Lucca-slot diagnostic only

The accepted replay begins before Continue, loads slot 1, initializes the
field from the diagnostic ROM, and adds a calibrated movement pulse. Recorded
frame 2540 shows Crono, Marle, and the original Schala cardinal packet
separated on the field. The paired clean-ROM control renders vanilla Lucca
instead.

The 3,000-frame run uses SRAM mode `noload-nosave`, a ROM-identity-matched
BSV, and the pinned RetroArch/bsnes2014 environment. Full commands, artifact
hashes, the clean control, and the rejected inherited-state checkpoint are in
`docs/schala_supported_slot_sprite_smoke_v0.md`.

This validates the packet's supported-slot fetch, assembly, and field-render
shape. It does not validate the diagnostic's deliberately incomplete palette:
the vanilla field path still supplies only colors 1-12.

## Explicit boundary

This packet remains partial and is not ROM-installable. It does not contain:

- the complete field and battle frame inventory;
- four equal facing blocks or any animation blob;
- the auxiliary animation family;
- graphics, assembly, animation, or palette ROM addresses;
- the expanded-bank fix for the hard-coded non-flipped tile reader;
- a Schala palette adapter; the vanilla field path copies only `$18` bytes
  (twelve character-specific colors), while this original art deliberately
  uses all fifteen visible indices;
- PC `$07` descriptor and pointer adapters;
- battle staging/DMA proof;
- battle runtime evidence or any PC `$07` runtime evidence.

The next art step is to complete the semantic frame inventory under this
compiler. The next engine step is the full-palette field adapter followed by
the smallest inert expanded-bank packet read after the generic non-flip
decoder and pointer adapters are independently proved. Neither step
authorizes a production playable-character patch by itself.
