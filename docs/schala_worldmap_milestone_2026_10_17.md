# Schala world-map checkpoint — October 17, 2026

**Coda V5 now renders as Schala on the native world map, with all four walking
directions and both prolonged-idle frames observed.** Project Epoch remains unfinished. This
report records new work without replaying the accepted October 15 validation
chain. Its machine-readable companion is
[`references/schala_worldmap_milestone_2026_10_17.json`](../references/schala_worldmap_milestone_2026_10_17.json).

## Preserved playable milestone

The accepted October 15 parent image is SHA-256
`7098f38c0b28b7806a1f69d092f7f3fd765544935e8667f5f6dfb495d386f95f`.
Its existing evidence establishes native party-menu removal/reselection, both
reserve pages, field return, an ordinary PC07 Attack and changed-formation normal
save/fresh load. Schala's retail field/battle presentation, full name, restored
reserve graphics and Gaspar preservation are part of that bounded checkpoint.
Active leaders 00/01 remain fixed; Schala occupies the third active position or
reserve. The [October 15 report](schala_party_selection_milestone_2026_10_15.md)
retains the exact claims and limitations. Those results are reused as accepted
evidence, not retested or extended by this art work.

## New source and asset findings

The private reference packet extracts the original seven world-map character
sets and Schala's retail NPC reference. Corrected NPC palette routing is
explicitly distinguished from a preserved earlier wrong-palette diagnostic.
Copyrighted reference pixels, raw graphics, ROMs and saves remain excluded from
Git and public reports. Exact private review attachments are separately
authorized; no public asset distribution is implied.

The world-map contract is **nine 16×16 images**, packed as SNES 4bpp tiles but
using transparent index 0 and at most seven opaque colors. Eight images occupy
a 0x400-byte main page; the ninth uses two 0x40-byte auxiliary halves. A 16×16
image uses tiles n, n+1, n+16 and n+17 rather than four consecutive tiles.
Native attributes supply mirrored walking/right-facing frames. The final two
images form the prolonged-idle animation; their encoded script counts are not
a new measurement of elapsed animation time.

[MAP-014](DATA_MAPPING_CORRECTIONS.md#map-014--world-map-auxiliary-tiles-are-graphics-and-palette-copies-are-eight-colors)
corrects two earlier project annotations. The `$C22BCF` auxiliary copy supplies
graphics, not palettes. The actual palette routine `$C228ED` uses a 0x20-byte
source stride but copies only 0x10 bytes, or eight colors. Logical ID07's
unmodified main-page calculation reaches occupied auxiliary graphics; it does
not identify a spare eighth page or the Epoch vehicle. Nine bounded canonical
spans match between the clean US Rev0 source and accepted 7098 image.

The strict exporter reconstructs all seven original sets against the extracted
raw assets: **28 exact comparisons** across main graphics, auxiliary halves
and copied palette bytes. It also checks binary transparency, dimensions,
color count and exact SNES color representability. It refuses invalid input
without silently correcting it. Separate disclosed palette conversions remain
distinct from the original submitted artwork. Export acceptance proves format
and pixel roundtrip, not artistic quality or native rendering.

## Independent art collaboration

Six external routes received the shared native-size reference brief, alongside
Coda's own coded pixel-grid attempt. Provider/model labels below are observed
UI labels, not independently verified backend identities. Private conversation
links, account information and reference attachments are excluded here.

| Collaborator / route | Observed mode | Returned evidence |
|---|---|---|
| Red / Claude Cowork | Opus 5.5 Max | Actual downloaded archive; source grids, JSON and indexed/RGBA PNG twins agree; original colors pass strict export unchanged |
| Wren / Primary Grok Bot | Provider-managed | Downloaded archive; PNG, JSON and literal source grids independently agree; original color-level refusal and separate conversion recorded |
| Lily / ChatGPT | GPT-6 Pro | Actual downloaded bundle; indexed PNG/JSON/palette agree; strict export accepted |
| Gemini | Argon High | Returned code/JSON reconstructed locally by Coda; provider explicitly did not execute or deliver binary output |
| Nua / Muse | Provider-managed | Exact returned JSON reconstructed locally; original provider media was not successfully downloaded |
| Meta AI | Thinking | Actual downloaded PNG/JSON/source agree; optional GIF was not received |
| Coda / local coded attempt | Explicit pixel grids | Version 5 native sheet and animation preview produced locally; private candidate only |

Coda compared all seven completed author candidates beside two retail references.
Red's sheet was the initial engineering pilot. Andrei then preferred Coda's
slimmer V5 proportions and judged Red's silhouette too large; **Coda V5 is now
the selected candidate**. Its original PNG SHA-256 is
`014fb4b0571099f9f285b0a710ad964dff84881a69a33701a70bc8981baad2a9`.
The original pixels and RGB values pass strict export unchanged. All author
originals, including Red's earlier pilot, remain preserved.

Following Andrei's suggestion, Coda inspected the
[Schala illustration](https://www.creativeuncut.com/gallery-01/ct-schala.html)
in a gallery crediting Akira Toriyama for the character designs. A separate
manual V6 proposal explores its high tied ponytail, swept fringe, earrings,
wide pale-edged collar and draped robe. V6 is an optional proposal; V5 retains
the user's preferred proportions. Both native sheets and their exact pixel
grids remain editable. This reference review does not authenticate the original
drawing's publication provenance or establish final artistic approval.

Wren, Gemini and Meta AI have separately labeled SNES palette conversions;
geometry, transparency and color count are preserved, with each RGB channel
moving at most 4/255. Nua's explicit conversion changes no visible color.
Lily, Red and Coda's v5 candidate need no conversion. Coda also explored a
generated concept and a coded reduction; that separate concept did not meet
the native geometry/color/transparency contract and was not selected. This
single result is not a general claim about generative art methods.

## Bounded provider and test fixture

The emitted private candidate adds **136 bytes of original code** at CPU `$480000`.
Three exact four-byte hooks at `$C228ED`, `$C22BBC` and `$C22BCF` provide the
third active member's palette, main page and auxiliary tiles. Only ID07 with
the exact third-slot destination selects new data; all other calls resume the
native path. Its five named immutable allocations plus three hooks and two
checksum headers form **ten exact write spans**. There is no new persistent
WRAM allocation. Existing hooks and occupied allocations are preserved through
the accepted allocation census and the completed current-parent complete-diff
audit. Production catalogs remain unchanged.

Actual assembled-byte checks passed **87 vanilla dispatch cases and 84 PC07
cases**. A separate source review found no ABI counterexample under native
E0/M16/X16/D0 and decimal-clear premises. The temporary PHP adds one stack byte
beyond native PHB; it is released before returning through the inherited near
frame. Fourteen new guard checks cover refusal and synthetic complete-diff
mechanics. These are source/host results; the separate native observation below
establishes actual caller state, uploads and selected rendering.

An explicitly **synthetic recruited-start** battery retains a genuine source
save's world-map location 01F0, original seven records, names including Epoch,
storyline/event state and other slots. It authors the admitted roster and binds
the accepted PC07 record to the new full A00 slot using the v2 CRC/SHA profile.
It changes 169 bytes within five declared spans. This does not prove native
recruitment, initialized newly granted vanilla-PC stats, a normal field exit
to the world map, or native saving of this fixture.

## Guarded emission and reproduction

The public [provider source snapshot](../asm/pc07_worldmap_provider_v1.asm)
contains the original assembly only; its [provenance index](../references/pc07_worldmap_public_source_snapshot_2026_10_17.json)
records a byte-identical copy of the private source used for this milestone.
No asset payload is embedded. The shared guard's two new diagnostic entry
points require the separately staged private `pc07_worldmap_write_contract_v1`
module, as the existing private-composition entry points do. The private builder,
sealed recipe, art and game inputs named below are not included in the public
checkout. This is an inspectable source snapshot, not a self-contained build.

The exact selected recipe is
`private/research/pc07_worldmap_art_20261017/integration_coda_v1/selected_coda_v5_recipe_v1.json`,
SHA-256 `722442f9383754a34f75bbd9e6fcc7a2dad93374b89d4be40a5a1deff8287401`.
It pins Coda's `coda/v5/export/` payloads and the unchanged reviewed provider.
A separate guarded operation emitted
`private/test_runs/pc07_worldmap_coda_v5_v1/diagnostic.sfc`, SHA-256
`ec7e5c089116c37510aea2bacc7a82c4131432eef414bdb8f6ef89723d6c6724`.
Both current shared audits passed before emission: **ten declared spans,
1,320 changed bytes, complete diff coverage and exact inverse restoration to
7098**. The operation used one captured input set and target buffer; no prior
builder/validator chain was replayed. The receipt is
`private/test_runs/pc07_worldmap_coda_v5_v1/receipt.json`. The earlier Red image
and sealed recipe remain unchanged in their own directories.

For a deliberately new local reconstruction, retain the exact sealed recipe
and its required private inputs, then use a fresh output directory:

```text
python -B private/research/pc07_worldmap_art_20261017/integration_coda_v1/build_v1.py --output private/test_runs/pc07_worldmap_coda_v5_rebuild_01 --emit
```

Omit `--emit` to prepare only the audited manifest, labels and receipt. The
strict asset export is independently reproducible into a new private directory:

```text
python -B private/research/pc07_worldmap_art_20261017/export_tools/export_worldmap_v1.py --png private/research/pc07_worldmap_art_20261017/coda/v5/coda_schala_worldmap_v5_native.png --output private/research/pc07_worldmap_art_20261017/coda_export_reproduction_01
```

These commands describe reproduction, not work rerun for this report. Existing
accepted receipts remain the normal resume point.

## Accepted native world-map observation

The final observer-v4 recording passes in
`private/test_runs/pc07_worldmap_observer_v4_coda_v5_run1/`. A fresh Mesen
process cold-boots the explicit fixture and uses controller input only. There
is no savestate or debugger game-state injection. The current recording's
independent validator accepts all 1,168 provider source bytes with their
read/write/readback evidence, nine native copy calls, three actual caller
returns, and the corresponding VRAM/CGRAM uploads. Original 00/01 destination
graphics and palettes remain equal to their native sources. The battery and
staged inputs remain unchanged; the child exits 64 without timeout.

The selected route produces 949 third-member draw nodes and 4,745 shadow-OAM
stores/readbacks, with all four walking-animation directions and both idle
frames. Read-only position snapshots also show actual third-member displacement
left, down, up and right. These position samples are separate from CPU store
attribution and do not prove general map traversal. The accepted trace is
7,980,289 bytes, SHA-256
`a6c0ac4bbe377b08297d69e9a2e17e8398dc3c305b5dd9ee4fe0600607c73747`.
The validation report is `validation_v4.json`; its identity and source hashes
are retained in `observer_v4/final_handoff_v4.json` in the private art packet.

Earlier attempts are preserved. V1 sampled VRAM before pending DMA had run;
the corrected source-pinned observation uses later actual CPU cuts. V2 and V3
reached transport/rendering but failed the strict all-direction gate because
terrain and follower distance prevented the proposed input routes. One cheap
Snes9x navigation pilot found a clear bridge route before the final detailed
Mesen recording. No art or provider change was required for this route repair,
and no historical validation chain was replayed.

Root inspected the actual down/up/right/auxiliary-idle screenshots, the
70-capture contact sheet and the enlarged downward-motion first frame. The
sprites remain readable at the original scale; V5's strong pale trim remains
an artistic refinement question. This is still/sequence inspection, not a
claim of real-time playback review. Two lossless APNGs retain every captured
frame, including duplicates, at nearest-neighbor 3x scale. Their timing uses
recorded frame differences divided by nominal 60 Hz, with the last interval
repeated; it is not a measurement of wall-clock timing. The exact decoded
frames and contact-sheet cells were checked once by the rendering utility.

The private motion files are under
`private/research/pc07_worldmap_art_20261017/visual_review/coda_v5_observer_v4_motion_v1/`.
The code/recipe packet is `integration_coda_v1/`; the original provider and
fixture remain under `integration_candidate/`. Reproduction starts from these
accepted receipts and one current input snapshot, without recursively running
old builders or validators.

## Current follow-up and scope

Lily also received the actual V5 ROM, battery fixture, source, art and a runnable
Linux Snes9x libretro core with a small standard-library Python harness. The
observed conversation was Personal, GPT-6 Pro. Her returned report and process
artifacts record one unchanged 3,752-frame run, exit 0, six native captures and
unchanged SRAM. The downloaded PNGs agree with her result file, and her
2,700-frame ready capture is byte-identical to the local smoke capture. This
is separately obtained reviewer execution evidence, not a locally observed
remote process or a substitute for the accepted Mesen recording.

Root read the complete returned review and inspected its six-capture montage.
Lily independently favored V5's proportions, while identifying the bright
vertical trim and broad forehead band as future refinements. Her earlier simple
input route did not prove up/right follower movement; she explicitly retained
that limit. The final clear-route Mesen result above supplies its own separate
four-direction and idle evidence. No V6 replacement or further art edit was
performed in response to the review.

The exact private runnable packet is
`private/reviews/20261017_runtime/lily/epoch-coda-v5-runnable-review-2026-10-17.zip`
(4,960,179 bytes, SHA-256
`bf4403fa451e64a7977cc6ff764351c7967ce8924f7d4edc8dd5e05991ce320f`).
The returned 217,077-byte output archive has SHA-256
`026378b9658a76b3759f2bfe0c60da26373d0643f39de19cebab69e64df13e14`.
It contains the review, process output and captures, not ROM/save/core inputs.

## Flying Epoch: parked position survives the hut roundtrip

Andrei's requested functional check now passes separately in
`private/test_runs/pc07_epoch_scene_roundtrip_v2_run1/validation_v1.json`.
In one Snes9x process, the party boards the flying Epoch, moves it from pixel
position **544,512 to 544,480**, lands and disembarks, enters the Ioka hut
on map `$0115`, returns to world map `$01F3`, and boards the ship again at
the unchanged **544,480** position. All three members board. The full roster,
PC07 record and Epoch name remain equal, and SRAM remains unchanged.

Root inspected the actual interior, returned-world and reboarded screenshots.
The 4,164-frame functional recording and nine read-only full-WRAM captures
support this selected scene transition. This is explicitly **not an SRAM-save
or cold-load persistence test**, and it makes no CPU-write attribution claim.
Its result identity is 2,282,187 bytes, SHA-256
`1052782260be077466fefa9868a7af6553451b6d259cfd0e88ce4301e98dc10c`.
Exact inputs, source identities, controls and reproduction commands are indexed
in `private/research/pc07_epoch_scene_roundtrip_20261017/final_handoff_v2.json`.

The start uses genuine late-game TechnoPlaza state10 vehicle/location/event
data, with Schala deliberately added using the established bound-v2 fixture
mechanism. The fixture changes 167 bytes in five declared spans and preserves
the original vehicle data, location, events, names and other save slots. It
does not establish native recruitment. The earlier process is preserved as
partial: boarding/flight/landing worked, but our hut approach missed the native
two-point cover predicate. Correcting the exact foot position and adding
read-only entrance observations resolved that route issue without a ROM edit.

Era changes, other vehicle routes, arbitrary active positions, new-game
recruitment and production release remain outside this selected proof.
The next art task is documented in
[`schala_main_sprite_art_brief_2026_10_17.md`](schala_main_sprite_art_brief_2026_10_17.md):
independent hand-authored main PC poses, with no weapons and a casting gesture
plus separate magic bolt for ordinary Attack. That work is separate from
world-map V5 and has not changed this ROM.
