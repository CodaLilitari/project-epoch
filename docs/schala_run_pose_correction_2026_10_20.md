# Schala normal-run pose correction — October 20

Andrei clarified the main-body art scope: preserve suitable existing PC07
sprites, rearrange animation references where that suffices, and author new
poses only for genuine gaps. His example of casting while running was a
hypothesis, not a reported playtest. Lily's corrected v2 casting preparation
and release are the preferred art basis; this does not select her whole sheet
or install those study frames.

## Minimal correction

The accepted V5 image's normal-run selector `$06` reaches assembly frames
`$13/$14` in every facing. The actual reference board shows the outstretched
casting poses. A separate private candidate changes only those two frame IDs
per facing, reusing the existing directional movement art:

| Facing | Old pair | New pair | Primary-relative offset |
|---|---|---|---|
| Up | `$13,$14` | `$04,$06` | `$0018` |
| Down | `$13,$14` | `$08,$0A` | `$041C` |
| Left | `$13,$14` | `$0C,$0D` | `$0820` |
| Right | `$13,$14` | `$0E,$0F` | `$0C24` |

This is movement-art reuse, not a newly drawn running cycle. All 23 body
assembly frames and their graphics remain unchanged, including the casting
frames for appropriate future uses. Timing remains `$0A/$0A`; the original
terminators remain in place. No weapon graphics are added.

The current-operation guard checks all 1,024 legal selector/facing entrypoints:
only `$06` changes its reached frame sequence. The empty `$02` suffix remains
empty. The preceding `$05` initialization can read ahead into these bytes,
but its unchanged terminator ends its active sequence before them.

The candidate changes 16 bytes in six declared spans: eight primary frame
references and two four-byte header checksum/complement pairs. Both current
shared write guards pass before image emission, the complete diff restores
the exact parent when reversed, and all thirteen original NPC protected spans
remain equal. The shared palette, body graphics/assembly and world-map V5
bytes remain unchanged. Production hook/allocation catalogs remain closed.

## Deliberately separate bindings

The established menu roles `$00/$01/$0B` and fixed battle/status anchors do not
include `$06`. Explicit event and battle-script commands can nevertheless
request `$06`; an explicit request inherits the corrected movement. The
canonical event census does not establish PC07 attribution or reachability.
Static event `$AC` assembly-frame references remain unchanged.

Alternate run `$17` is a separate leader-only branch and remains unchanged.
This candidate retains the previously supported third-party position; it does
not claim expanded leader support. Idle and walking retain their existing
frame sequences.

KO requires a separate focused correction: the zero-HP status path selects
`$08`, currently a casting frame, but `$08` shares that token with the tail of
`$07` and serves other conditions. Blindly replacing it changes both entries.
Likewise, the donor Attack package IDs do not identify its sprite-animation
requests. Observe those consumers before binding Lily's casting or a new
recoil/KO pose. A complete replacement sheet is unnecessary.

## Build and checks

- Parent: `private/test_runs/pc07_worldmap_coda_v5_v1/diagnostic.sfc`, SHA-256
  `ec7e5c089116c37510aea2bacc7a82c4131432eef414bdb8f6ef89723d6c6724`.
- New private candidate: `private/test_runs/pc07_run_pose_v1/diagnostic.sfc`,
  SHA-256 `00e3440c2927834554c7e3f872a5b995b76e53e1e6775ddd76abe9bac0b8f18f`.
- Construction receipt: `private/test_runs/pc07_run_pose_v1/receipt.json`.
- Reproduce into a fresh private destination:
  `python -B tools/build_pc07_run_pose_v1.py --output private/test_runs/pc07_run_pose_<fresh-name>`.
- Focused checks:
  `python -B -m unittest discover -s tests -p test_pc07_run_pose_write_contract_v1.py -v`.
  Five tests pass, including refusal of source drift, undeclared graphics,
  palette, timing and world-map changes, forged manifest scope/evidence and
  unsafe output paths. Private fixture tests skip when the ROM is absent.

The builder reads one current parent image and its immediate accepted receipt.
It does not run old builders, validators, world-map/Epoch/save observations or
reconstruct the historical chain. ROMs, saves, screenshots and extracted
reference art stay private. No publication is part of this pass.

## Native comparison

Two fresh headless Snes9x processes imported the same preserved battery and
followed the same 16-step input plan plus the final observer-stop command.
Each reached frame 3286 and retained
587 read-only end-frame snapshots in map `$01DA`, with logical `$00/$01/$07`
at object offsets `$02/$04/$10`. There were no savestates, runtime memory
writes, frontend windows or save-back to the source battery.

The baseline reaches `$06` with frames `$13/$14` in all four directions.
The candidate reaches exactly the four replacement pairs above. Both also
reach walking `$01` and idle `$00`; the final stop returns both to down-facing
idle frame `$01`. All paired observations agree on location, identities,
positions, facing and selector. Both emulated batteries, staged batteries
and source battery remain unchanged.

The two result files and screenshots are under
`private/test_runs/pc07_run_pose_observation_v1/{baseline,candidate}/`.
Root independently inspected both `run_down.png` captures at frame3086:
Schala's whole body is visible, and the baseline outstretched casting arm is
replaced by her directional movement robe pose. The first upward capture
partially clips her at the screen edge; it is retained but is not the primary
visual comparison.

The bounded comparison report is
`private/test_runs/pc07_run_pose_observation_v1/comparison_v1.json`; it finds
274 changed cached-frame observations and equality of every other recorded
field, including the original two party objects. The same folder contains
`before_after_run_down_3x.png` and a delivery manifest for the new packet.
The runtime sources and exact reproduction instructions are in
`private/research/pc07_run_pose_20261020/runtime/README.md`.

This supports a native functional correction for the sampled third-position
field route. These are end-frame snapshots and rendered frames, not CPU bus
attribution, continuous instruction coverage, proof of every scripted use or
a complete playthrough. The original V5 build remains preserved separately.
