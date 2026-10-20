# Schala full status portrait — October 20

The separately guarded v2 candidate adds Schala's own 48×48 portrait and her
six-letter name to the full status panel and scrolling character list. Its
private image is `private/test_runs/pc07_status_portrait_v2/diagnostic.sfc`,
SHA256 `773e32de495acad1ac6d12fbe15101f45bc0240e65af47e4de19a318d54de128`.
**The selected controller-only native status route passes:** Schala displays
her own portrait and six-letter name, all seven original faces remain intact,
and the repeated-transfer display failure is gone in the observed frames.
A separate items/Techs/settings return route also passes. The original v1
was rejected after an actual display failure; its source, image, art and
evidence remain preserved.

## Why v1 was rejected

V1 used a shared display slot and queued 1,152 portrait bytes on every
qualifying Crono/Schala redraw. All 1,017 synthetic helper cases passed, and
the native VRAM, palette, tilemap and 98 CPU-return comparisons were correct.
Nevertheless, the visible menu corrupted when the extra transfer ran. Static
correctness of data and registers did not establish display scheduling safety.

A separate read-only timing pilot measured 9,558 master clocks from the
instruction before the DMA start through its actual completion and following
TDC. The earlier callback immediately after the DMA register write occurred
before the stall; its 24-clock interval was not the transfer duration. In the
measured Schala frame, the additional transfer ran from scanline 244 to 251;
remaining menu work pushed HDMA enable to scanline 0 and display restoration
to scanline 1. The Marle control enabled HDMA at 254 and restored the display
at 256. This is a measured selected-menu frame overrun, not a universal DMA
budget. A transfer only on selection changes could still produce a corrupt
transition frame, so v2 removes transfers from the redraw path altogether.

V1 also left the sixth detail-name glyph behind after leaving Schala, because
the original text consumer redraws only five glyphs. V2 restores that sixth
low byte to the original blank for every other qualified selected character.

Rejected v1 SHA256:
`c3a2ff596b3d77040b0fde4e52dd4816faa76a69f8b8df491b4f12a247a2cc28`.
The retained timing pilot is under
`private/research/pc07_portrait_20261020/runtime/runs/rejected_v1_completion_timing_pilot_v1/`.

## Selected art and native format

The selected art is the concept-derived V2 `reserved_purple_green13` candidate.
The generated source was converted deterministically using nearest-neighbor
resampling without dithering, thirteen general opaque palette colors, and
reserved source purple and green colors. This is generated concept-derived
art followed by coded conversion. Root selected this version for preview and
integration. The latest user request asks for closer fidelity to the original
concept art, superseding that preview choice. This image remains a provisional
integration asset; final user art approval is not claimed.

The native image is 48×48 pixels: six by six row-major 8×8 tiles, 36 SNES
4bpp tiles totaling 1,152 bytes, with a separate 32-byte BGR555 palette.
Index zero is reserved and unused; the pale background remains opaque.
The indexed image, packed tiles and palette round-trip exactly. The integration
codec independently reproduces the selected converter's bytes. Art was not
changed to repair the display failure.

Selection manifest:
`private/research/pc07_portrait_20261020/selected_art_v1/manifest_v1.json`,
SHA256 `c83a77f0c1ab3f446590d1640f2bf8ddd01c07094cb14fdaf7845a09c531cced`.

## Dedicated menu graphics and exact hooks

V2 uses three pinned instruction hooks, each in a separate private contract:

| Original CPU span | Expanded helper | Purpose |
| --- | --- | --- |
| `$C2:9751`, four bytes | `$4A:0300`, 84 bytes | Append one descriptor during full-menu initialization |
| `$C2:EC3E`, four bytes | `$4A:0000`, 366 bytes | Qualified displayed names and Schala's tile base |
| `$C2:EC8B`, six bytes | `$4A:0200`, 134 bytes | Qualified Schala palette; restore temporary attribute byte |

The preload hook replaces `SEP #$20; LDA #$18`. In its exact observed/source
context, it appends an eight-byte descriptor at `$7E0C18` and returns count
`$20`; the original `STA $0D11` and queue flush still run. The three original
preload records remain exact. The additional descriptor copies `$4A:1000`
to VRAM word interval `$1B00–$1D40`, end exclusive, during the menu's existing
blank initialization. No portrait graphics are transferred by the redraw hook,
and no persistent cache or new WRAM owner is introduced.

The corresponding tile IDs are `$1B0–$1D3`. With palette 3, the actual tilemap
words are `$0DB0–$0DD3`; tile word `$0DB0` resolves to VRAM byte `$3600`.
The status tile helper temporarily changes DP byte `$01` from `$0E` to `$0D`
for Schala's existing 6×6 renderer. The palette helper restores `$0E` before
the original continuation. All other character paths retain their original
portrait selection. All seven original faces remain in their original VRAM
slots; Crono's source image and display slot are not used for Schala.

The first proposed interval, `$1980–$1BC0`, was rejected because the naming
keyboard's canonical DMA occupies `$1800–$1B00`. The selected interval follows
that keyboard and ends before the `$1E00` icon preload. A source-pinned census
checks 154 ROM queue call sites, the actual preload descriptors, bounded
sprite/text/save-preview producer families, 91 retained native DMA records,
and 19 retained menu captures. Those captures also contain no existing
references to the selected tile IDs in the inspected menu tilemaps. Zero
contents alone are not allocation authority. The census is conditional on
the native bounded producer data and menu lifetime; it is not whole-game
VRAM ownership or proof of every menu transition.

Named expanded reservations, end exclusive:

| Purpose | File span |
| --- | --- |
| Three portrait/name helpers | `$4A0000–$4A0400` |
| Schala's 36 portrait tiles | `$4A1000–$4A1480` |
| Schala's 16-color palette | `$4A1480–$4A14A0` |
| Fixed six-letter Schala string | `$4A14A0–$4A14A6` |

The immediate parent receipt supplies the inherited allocation census. Its
sections and complete reservations bring the checked occupied set to 180
spans. New reservations are disjoint and inside the inherited expansion;
fill is only a preimage check. Production allocation/hook catalogs stay empty.

## Schala's displayed name and Epoch's vehicle name

The parent status menu copied Epoch's vehicle-name bytes for logical ID 07
into the name work buffer, then printed five cells. The new helper changes
only six displayed glyph low bytes: detail cells beginning at `$7E2FAC`, and
the matching visible row at `$7E2EC6`, `$7E3046`, or `$7E31C6`. Row identity
comes from `$7E0D5F[scroll + row]`, with scroll restricted to 0–5. Attributes,
selection highlights and the adjacent LV label are preserved. When another
character is selected, detail cell `$7E2FB6` becomes its original blank again.

This is a fixed displayed name. It does not create an editable or saved name
record. The legacy work buffer, Epoch's `$7E2C4D–$7E2C52` name, serialized
vehicle data and Epoch's naming consumer remain untouched. The vehicle
naming screen has different destination/attribute qualifiers. A proper Schala
renaming UI remains unresolved. The small save-preview portrait consumer is
unchanged and does not gain the new full portrait.

## Scoped validation and native results

Six focused v2 tests pass, covering 863 executions of the new helpers: 680
tile/name, 97 palette, and 86 preload cases. Every new helper instruction and
both outcomes of each conditional branch are exercised. Cases check all 256
logical inputs and scroll values, exact context refusals, original CPU/flag
postconditions with the declared Schala tile/count differences, ordered
writes, temporary attribute restoration, sixth-cell cleanup, untouched queue
state on redraw, and complete-diff/manifest rejection. The unchanged v1 CPU
interpreter is reused; historical helper suites are not rerun.

Independent Asar assembly matches the bounded opcode encoder. Both shared
guards accept 1,766 changed bytes in eleven declared spans and prove complete
inverse restoration of the immediate parent. Fourteen canonical instruction
bytes and the checksums change; all other canonical bytes, including unused
assets, remain exact. All thirteen protected NPC spans, previous expanded
helpers/body art, world-map assets, Epoch naming and save-preview paths are
unchanged. The explicit helper stack peak is eleven bytes including JSL,
not a proof of physical stack or interrupt ownership.

The emitted v2 passes the selected native controller route with the custom
Wings vehicle-name fixture. Seventeen audited captures cover all eight
characters and PC07→Crono→PC07; every portrait pixel comparison passes with
one-level integer color tolerance. All seven original face regions remain
exact, and 114 native hook-context comparisons pass. Schala's detail and left
names are correct, the sixth character clears on leaving her, and neighboring
attributes/LV cells remain intact. The actual Schala screenshot was inspected.

All 2,140 observed status end-frames use BG mode 1, brightness 15 and a nonblank
display. The new portrait transfer occurs exactly twice, once for each tested
full-menu initialization across close/reopen. Each costs 9,558 master clocks
under initial forced blank, at scanlines 176→183 and 183→190. There is no
per-redraw graphics transfer. Both initial queues preserve the original three
records and append only the fourth descriptor. At the observed Schala
transition, HDMA/display restore at scanlines 254/256; on the Crono return,
they restore at 258/260. These are measured examples, not universal timing
bounds. Queue high-water remains 112 bytes in this route.

The vehicle name remains Wings, and the input battery is unchanged. The run
uses normal controller input, with no save-state input or game-state injection.
Closing and reopening the menu is observed. A separate controller-only
lifecycle audit passes thirteen captures across items, Techs and settings,
with three returns to Schala's status portrait. Both portrait graphics regions
and Wings remain intact; 711 observed status end-frames are mode 1, nonblank
and full brightness. That run performs one initial portrait upload, with
unchanged source/staged ROM and battery. This covers those three transitions,
not every menu or equipment operation. The actual Epoch
naming screen remains a distinct unobserved route; preserving its source and
vehicle bytes does not claim that runtime test. This menu test is not a new
vehicle-flight regression or a complete game validation.

The lifecycle audit also exposes an unresolved consumer: the Tech tab's left
list still calls PC07 **Wings**, using Epoch's vehicle name. The status-only
name fix does not cover this other UI. Separately, the user requested a stats
correction; enlarged screenshot review confirms the first status display has
HP 608/29 while raw PC07 HP is 608/base max 969. MP is 93/93 and attack 48.
Exact record/consumer tracing is required before correcting this maximum-HP
anomaly. Portrait acceptance does not validate stats, equipment, growth or
caster balance.

Native audits:
`private/research/pc07_portrait_20261020/runtime/candidate_wings_lifecycle_audit_v1.json`
and
`private/research/pc07_portrait_20261020/runtime/candidate_wings_status_audit_v2.json`.
An additional read-only internal source review found no concrete helper,
preload or addressing defect. Its explicit limits—isolated helper tests and
conditional dynamic destination families—remain visible in this checkpoint.

## Reproduction and private scope

```
python -B tools/build_pc07_status_portrait_v2.py --output private/test_runs/pc07_status_portrait_<fresh-name>
python -B -m unittest discover -s tests -p test_pc07_status_portrait_v2.py -v
```

The builder pins immediate parent
`17b156701321ec11b5ed115dff0964665160bc99a857641d42078a7d73e3cb3e`,
selected art, native-context reports, the menu census and exact helper source.
Intent and complete-diff guards run before emission. No historical build chain
is replayed. The v2 emitted receipt is
`private/test_runs/pc07_status_portrait_v2/receipt.json`, SHA256
`884e7735b8244e5633acc55544e0b942e80a608cc90400ec8ff60ed1bb07dc7f`.

Static evidence lives under
`private/research/pc07_portrait_20261020/engineering/static_review_v2/`;
runtime evidence is under the sibling `runtime/` directory. ROMs, saves,
traces and derived/extracted game art remain private and ignored. This
checkpoint asserts no Git push, external ROM distribution, portfolio
publication, production approval or full-game completion.
