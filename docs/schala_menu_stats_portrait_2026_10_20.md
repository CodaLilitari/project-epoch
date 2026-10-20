# Schala: first-menu stat correction and concept portrait candidate

This private checkpoint fixes a confirmed initialization error: on the first
menu opening, Schala could display **608/29 HP and Attack 48**, although her
base maximum HP was 969. Later native selection already recalculated the
same record to **608/969 HP and Attack 236**. The new candidate includes her
initialized record in that startup recalculation. It also replaces only her
appended full-menu portrait graphics and palette with the reviewed V6B art.

Andrei explicitly chose **“Fix calculation/display first; balance separately.”**
No base stat, growth rate, level, EXP, equipment ID, item definition or spell
damage change is part of this checkpoint. The existing Crono-derived test
profile remains a diagnostic profile, not a finished pure-caster balance.

**Native status: final v2 passed the focused numeric, portrait and HP-color checks.** The first Schala panel now
shows **608/969 HP in ordinary white, 93/93 MP, Attack 236 and Defense 211**. The new V6B portrait
renders in her dedicated portrait slot. Crono/Marle controls, Schala to Crono
to Schala, and close/reopen pass with the unchanged Wings fixture. Base stats
and equipment remain untouched, as requested.

## Why the first display was wrong

The canonical startup loop at `$C2:99B2` recalculates records `$00–$06` only.
Schala's valid record is `$7E2830–$7E287F`, with identity `$07`. Its base maximum
HP is stored at `+$05`; the menu's derived maximum HP uses `+$3F–$40`. Battle
reuses that tail. The retained fixture has `$0405` (1,029) there, which the
native three-digit number renderer displays as `029`. Its saved derived
Attack is 48. A later detail selection already runs the normal computation
and produces maximum HP 969 and Attack 236.

This behavior was documented in the existing party-menu threshold wrapper.
The new evidence connects the reused first/later native captures to the
startup loop and supplies a narrow repair. It is not a claim that the record
layout or tail reuse was newly discovered. The existing low-HP threshold
adapter stays intact; its seven-entry cache is not extended into occupied
`$0D46–$0D47`.

## Narrow implementation

The five original bytes at `$C2:99C1`, `LDA $02; CMP #$0007`, become a call to a
30-byte helper at `$4A0400`, followed by one NOP. The original branch, loop
body, record loader, formulas and exit remain byte-identical.

At counter 7, the helper checks the live identity byte. Only identity `$07`
clears Carry and admits one additional iteration of the original loop.
Counter 8 exits normally. Other identities retain the original comparison
result; a cleared SafeEmpty record is skipped. The accepted loader preclears
all 80 bytes before validation and publishes the record only after its
existing integrity and roster checks. Entry-premise refusal before preclear
remains a separate failure path; arbitrary corrupted live memory is not
certified by an identity comparison.

For the admitted record, the existing loader copies 80 bytes to `$9A90` and
sets the live pointer to `$2830`. The existing commit writes current HP at
`$2833–$2834` and eleven derived bytes at `$2866–$2870`. It preserves identity,
base HP/MP, base stats, equipment, level and growth fields. Its eighth physical
attack-formula table entry already exists, so this repair adds no donor table
row and overwrites no unused canonical content.

The normal routine also refreshes its temporary record/name/arithmetic work
buffers. The source Epoch name is only read; it is not rewritten. The actual
vehicle name remains Wings in the custom fixture. The separate Tech-tab name
alias and Schala's eventual rename UI remain open work.

The new helper reserves `$4A0400–$4A043F`, immediately after the existing
portrait helper reservation and before its art data. Allocation checks reuse
the immediate accepted parent census: 195 occupied section/reservation
entries are checked. The literal fill bytes alone are not allocation proof.
The helper owns no new WRAM scratch and adds at most six local stack bytes,
including its JSL frame; that is not a whole-game stack/interrupt bound.

## Portrait revision

V6B uses the tighter concept-oriented face and relaxed eyes selected after
independent comparison with V2/V5. Palette B replaces two duplicate white
palette bins with actual source colors, retaining the gold earring/tie more
clearly. No spatial pixel painting was applied during that palette correction.
The exact native format remains 48 by 48 pixels, 36 row-major SNES 4bpp tiles
(1,152 bytes) and 16 BGR555 entries (32 bytes). Index 0 remains reserved and
unused by the opaque portrait. Native encode/decode roundtrip is exact.

This is an approved candidate for in-game review, not final user acceptance
of likeness. Art provenance and independent-review limits are recorded in
`private/research/pc07_portrait_20261020/native_conversion_v6b/ART_REVIEW.md`.
Only the existing Schala payloads at `$4A1000–$4A149F` change. Original seven
portrait assets and palettes, NPC art, world sprites, body/battle poses,
portrait hooks, dedicated VRAM destination and preload timing remain exact.
There is still no graphics DMA on each portrait redraw.

## Retained numeric/art v1 observation

The focused audit captures two startup generations, each executing exactly
IDs 0 through 7. Sixteen before/after gate comparisons pass. Each PC07 pass
records all 80 actual source reads and 13 actual committed bytes: current HP
plus the eleven derived fields. The first pass changes only record offsets
`+$3D`, `+$3F` and `+$40` from the stale fixture: Attack becomes 236 and derived
maximum HP becomes 969 before any status display. Reopening recalculates the
same correct values without changing any record byte.

The seven original records are byte-identical immediately across each new
PC07 pass, comparing the counter-7 snapshot with counter 8. This is a direct
within-run comparison, not a claim that all characters equal a hypothetical
unchanging save record. Base HP/MP, equipment and unrelated PC07 fields also
remain exact. The measured canonical PC07 iteration takes 14,068 master
clocks on each observed initialization.

All ten captured PC07/control/return/reopen screens pass their numeric,
portrait, palette and original-face VRAM checks. All 1,150 observed status
end-frames are BG mode 1, brightness 15 and nonblank. Exactly two 1,152-byte
portrait DMAs occur, one on each initial forced-blank menu opening, taking
9,558 master clocks each. There is no per-redraw portrait graphics upload.
Palette/VRAM bytes compare exactly; rendered screenshot comparisons allow
one RGB level for conversion.

The actual Wings vehicle-name bytes remain unchanged. Source and staged ROMs
and batteries remain unchanged by observation. The 13 protected NPC ROM spans
are equal; this focused menu run does not claim new NPC execution, a new
flying-Epoch test, a save/cold-load test, a level-up test, or full-game coverage.
SafeEmpty refusal is supported by current-loader source qualification and
all-identity helper cases, not a new native SafeEmpty run.

Native evidence is
`private/research/pc07_portrait_20261020/runtime/candidate_stats_portrait_audit_v1.json`,
SHA256 `1e0b597a4fb811207f68e173c0c32a1b1d7a522d5276a71ac73002bdb076f92d`.
The fixed first panel is the run's `schala_first.png`; the original captures
and read-only observation trace remain preserved.

## Separate HP-color correction in final candidate v2

Final screenshot review found another display error: although the numbers
were now correct, Schala's 608 HP remained red at 969 maximum HP. Her actual
five current and five permanent status bytes were all zero. The native color
branch at `$C2:A200` compares a low-HP threshold; it does not read those status
flags.

The installed older adapter at `$47:0205` serves the party-exchange screen.
It requires the exchange layout flag `$0D36` to be zero. The ordinary menu's
observed flag is `$FF`, so that helper fell back to the seven-entry threshold
cache. For PC07, index `$0E` reads occupied `$0D46–$0D47`, which instead hold
portrait/window state. A preliminary message incorrectly called the captured
`mode` field `$0A00`; the collector defines it as `$0D36`. The corrected address
is used in the code, guard and diagnosis.

Candidate v2 preserves v1 unchanged and adds a separately allocated adapter at
`$4A0440` (103 bytes within reservation `$4A0440–$4A053F`). At the existing
panel hook, it requires D0/DBR7E, X=`$000E`, normal layout `$FF`, matching work
and live identity `$07`, and live-record pointer `$2830`. The source-owned
callsite establishes M16/X16. It divides the menu work record's derived
maximum HP at `$9ACF` by ten, then compares the result with current HP at
`$9A93`. Thus 608/969 uses threshold 96 and ordinary color. Equality and values
below the threshold retain the native critical-color rule.

All rejected contexts restore their entry registers and tail-delegate to the
unchanged `$47:0205` helper, preserving the existing party-exchange behavior
and original-PC path. No cache is extended, no WRAM owner is added, and no art,
numeric fix, equipment, base stat or save byte changes. Its nine-byte local
stack contribution includes the JSL frame and is not a global stack bound.

The focused static checks pass 273 cases, covering threshold boundaries,
qualifier failures, all authored instructions/conditional edges, independent
Asar equality and eight guard refusals. The corrected test-harness divider
uses the low eight bits written to the hardware divisor; an initial harness
failure did not require an assembly change. Four declared image spans cover
113 changed bytes. The complete original fallback helper is source-pinned.

**HP-color native result: passed.** The short route captures three distinct
operand/context groups (Crono, Marle and Schala), each occurring twice across
initialization/reopen. The auditor checks the first captured CPU/source/
decision sample per distinct group and retains the repeated occurrence counts.
For Schala, actual `$9ACF/$9AD0` reads produce maximum HP 969, the helper
returns threshold 96 with the expected comparison flags, and `$0D5D` stays
zero. The occupied fallback word is actually `$DC00` in that captured context,
confirming that it was UI state rather than a usable eighth threshold.

All six captured normal/control/reopen screens pass. Schala's current and
maximum HP digit attributes are zero, so 608/969 renders in ordinary white.
The author inspected the final enlarged native screenshot. All 760 observed
status end-frames remain BG mode 1, brightness 15 and nonblank. The portrait
palette, own-art VRAM and original-seven portrait region remain exact; Wings
and source/staged ROMs and batteries are unchanged.

The new audit is
`private/research/pc07_portrait_20261020/runtime/candidate_hp_color_audit_v1.json`,
SHA256 `7b89e2cde02711f02b70f6db87e99bddd1ad2b135767c3388dab7d20b25baea4`.
The requested final capture is
`private/research/pc07_portrait_20261020/runtime/schala_fixed_portrait_stats_white_hp_native_4x.png`.

Critical-HP thresholds/equality are covered by the new instruction-model
cases; no critical-HP native fixture was fabricated. The earlier 80-read/
13-write numeric matrix, all-eight portrait/tab matrices, NPC execution,
flying Epoch and save/cold-load routes were not rerun. Their retained evidence
and limits remain distinct from this new color observation.

## Verification and reproduction

The scoped helper tests execute **647 cases** across every live identity byte,
loop completion, boundary counters and flag representatives. Every authored
instruction and conditional edge executes. The model checks A/P, untouched
X/Y/D/DBR, balanced stack, six-byte local stack peak, and absence of nonstack
writes. Asar independently produces the same 30 helper bytes.

After the art/source pins were sealed, the shared intent and complete-diff
guards accepted the exact candidate and rejected ten altered manifest/image/
source cases. The emitted image has six declared spans and 1,191 changed
bytes. Only five canonical instruction bytes and the paired checksum fields
change; canonical game data, all prior expanded code, 13 protected NPC spans,
vehicle/world-map consumers and save inputs remain unchanged.

```
python -B -m unittest discover -s tests -p test_pc07_menu_hp_color_v1.py -v
python -B tools/build_pc07_menu_hp_color_v1.py --output private/test_runs/pc07_menu_stats_portrait_<fresh-name>
```

The final local image is
`private/test_runs/pc07_menu_stats_portrait_v2/diagnostic.sfc`, SHA256
`d4b6915dc85ef2bc782583de4478f9ed61e07f68fb2dde58b9cced4350ba3117`.
Its sibling `receipt.json` has SHA256
`6cd8051e1bc9c7be691fb5a3f770132dfe82fd562cd7abc51fad282f1fa473fd`.

Its immediate parent is the retained numeric/art-v1 image,
`private/test_runs/pc07_menu_stats_portrait_v1/diagnostic.sfc`, SHA256
`c020bca3e766191a8db00bd0d4f75f9d2f16b3cd884c58184af8792f84f55244`,
whose receipt is
`7ba2adfec600df29ddf50932df31480777c6f75412d07bb4879794d536c55f2b`.
That prior image was built from accepted portrait-v2
`773e32de495acad1ac6d12fbe15101f45bc0240e65af47e4de19a318d54de128`;
its builder/tests remain preserved separately. Reproducing the final color
delta does not rerun those earlier builders or suites.

The builder uses one immediate source snapshot and its accepted receipt,
without executing historical builders or validation chains. ROMs, batteries,
traces and extracted or generated game-art payloads remain local and ignored.
No Git push, public ROM distribution, portfolio publication or full-game
completion is asserted here. Growth integration, caster balance, equipment
policy, magic damage and the Tech-tab name alias remain separate requirements.
