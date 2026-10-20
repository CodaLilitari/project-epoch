# Project Epoch development download — October 20, 2026

**Development snapshot. Not truly playable. Not a complete eighth-character mod.**

This package makes the current diagnostic checkpoint inspectable. It is not a
supported playthrough, completed recruitment system, complete Tech set, or
balanced Schala. Use separate copies of the ROM and emulator working directory;
do not use an important ongoing save. The stats and equipment still come from
the diagnostic donor record. The user explicitly chose to fix calculation and
display first, with balance and equipment handled separately.

The final image is the accepted menu stats, V6B portrait and HP-color build.
The release process exports that immutable image; it does not rebuild the old
research chain or introduce another ROM mutation. The selected Mesen states
have separate fresh-process restore and controller checks.

## Download identities

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `project-epoch-dev-2026-10-20.zip` | 492,200 | `9eff5a5b1078b5117c0710e50be502512c0367d27ea7a30584068088e3fd0598` |
| `project-epoch-development-2026-10-20-v1.bps` | 58,987 | `4cb81f836bb06ef74575c00bccc9cb91a8936f2ca5169644e52aee7a0c4c5349` |
| Required clean US revision-0 input | 4,194,304 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| Resulting diagnostic image | 8,388,608 | `d4b6915dc85ef2bc782583de4478f9ed61e07f68fb2dde58b9cced4350ba3117` |

The clean input must have **no 512-byte copier header**. The result is the
existing eight-MiB ExHiROM development image. Apply this one BPS directly to
the exact clean ROM, not to another patch or a previous Epoch build. A
BPS-compatible patcher such as Floating IPS can produce a new output file.
Check the resulting size and SHA-256 before loading a state. No ROM is included.

The bundle contains the BPS, `README.txt`, `release-manifest.json`, and an
explicit `demo/` allowlist: two Mesen states, six captioned images, the demo
manifest and detailed limitations. It includes no separate battery file,
emulator, raw trace, extracted art source, or private correspondence. States
include machine state and save RAM, so isolate the emulator directory from
your own playthrough. The states are download assets only and must not enter
the source repository.

## What can be inspected

The tested emulator is **Mesen
2.1.1+137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1**, state format 4. Compatibility
with other versions or emulators is unproved. Open the exact patched image,
then load a supplied state with Mesen's load-state-from-file command.

- `epoch_dev_d4b691_schala_status.mss` opens the corrected status view. B, then
  B, returns to the field on the tested route.
- `epoch_dev_d4b691_field_ready.mss` opens a controller-ready field checkpoint.
  X, A, Down, Down reaches Schala's status with the configured SNES buttons.

The final view shows Schala's own portrait and six-letter name, HP 608/969 in
ordinary white, MP 93/93 and Attack 236 for this prepared record. Native
observations verify the corrected initial stat calculation and HP threshold
source; they do not approve those donor stats as her final balance.

The included older casting, running and world-map images retain their actual
build labels. The front-facing cast image is explicitly an **injected study**.
The earlier flying-Epoch test covered landing, disembarking, entering a house,
returning to the world map and reboarding; it was not a cold-load or SRAM-save
test. None of these older captures becomes a new final-build gameplay test
merely by appearing in this download.

Open work includes the Tech-tab vehicle-name alias, complete Techs and growth,
pure-caster balance/equipment, final projectile placement in every facing and
context, recruitment, full progression, and generalized save/load safety across
all slots and lifecycle paths. Existing separately documented slot-0 save/load
proof is retained. No full-playthrough or universal vehicle-preservation claim
is made. Critical-HP coloring has static boundary checks, not a native low-HP
fixture in this final run.

## Reproduction and guards

The source-controlled exporter requires three exact local inputs: clean ROM,
accepted final image, and its immediate guarded build receipt. It additionally
requires the exact selected demo archive. Private inputs and generated outputs
stay ignored. The exact source/target/receipt identities are pinned in
`tools/epoch_development_bps_export_contract_v1.py`.

```powershell
python -B tools/export_epoch_development_bps_v1.py --source "private/input/rom_archive/Chrono Trigger (USA).sfc" --target private/test_runs/pc07_menu_stats_portrait_v2/diagnostic.sfc --receipt private/test_runs/pc07_menu_stats_portrait_v2/receipt.json --demo-zip private/research/epoch_update_20261020/runtime/project_epoch_development_demo_20261020_v1.zip --output private/research/epoch_update_20261020/release/reproduced_v1
```

The output directory must be fresh. The command writes only the BPS, combined
ZIP, installation text and two manifests/receipts. It does **not** write a ROM.
The ZIP has fixed entry order, timestamp and compression settings; use the same
Python/zlib runtime to reproduce its compressed bytes exactly. BPS bytes do not
depend on ZIP compression.

Before writing the patch, the exporter runs the two named APIs in the shared
`tools/validate_rom_write_intents.py` guard. The export intent is fixed to the
accepted binary and receipt. The audit accounts for every clean-image
difference plus the complete appended extent, restores the source as a separate
inverse check, and applies the entire BPS in memory to the exact target.
Production hook/allocation catalogs remain empty. This is a narrowly authorized
diagnostic export, not a promotion of historical allocations to production.

The BPS encoder uses source reads/copies for unchanged or moved data, bounded
literal searches, and overlapping target copies for repeated fill. It follows
the [original BPS format specification](https://github.com/Sir-Walrus/Flips/blob/master/bps_spec.md).
The decoder checks source, target and patch CRCs, action bounds, relative-copy
direction, complete output extent and unused trailing data.

Ten focused tests cover hand-encoded format vectors, overlapping copies,
negative relative offsets, deterministic encoding/ZIP order, corrupt patch and
wrong source/target/receipt refusal. Private-input guard tests skip cleanly when
the local accepted artifacts are absent. No historical build/test chain runs.

An independent application check also passed using unchanged Mesen
`BpsPatcher`/`CRC32` source at revision
`137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`. The four upstream source blobs
were verified against that revision and compiled with the already installed
WSL compiler. A small compare-only wrapper added the patch-CRC check and
compared all 8,388,608 output bytes with the accepted image in memory. It wrote
no ROM. A separate package inspection verified all 13 ZIP members, their
hashes, and unchanged demo payloads. This confirms format interoperability and
artifact identity, not broader game safety.

```powershell
python -B -m unittest discover -s tests -p test_epoch_development_bps_v1.py -v
```

The initial local package is retained separately because two instruction
phrases were clarified before publication. Both exports produce identical BPS
bytes and the same target image. The final ZIP identity above is authoritative.

See [the menu stats/portrait report](schala_menu_stats_portrait_2026_10_20.md)
for the actual engine changes and retained runtime boundaries, and
[`references/epoch_development_release_2026_10_20.json`](../references/epoch_development_release_2026_10_20.json)
for the machine-readable release record. Publication is a separate action from
this local engineering checkpoint.
