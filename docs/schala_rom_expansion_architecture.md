# Project Epoch production ROM expansion architecture

Status: inert scaffold verified-static with legacy and current-core bounded runtime controls; PC `$07` not activated  
Last updated: 2026-07-26  
Source model: unheadered Chrono Trigger US Rev 0, 4 MiB fast HiROM  
Target model: 8 MiB fast ExHiROM

## Outcome

`tools/schala_rom_scaffold.py` now creates an inert 8 MiB ExHiROM image
entirely in memory. It does not install hooks, emit copyrighted data, write a
ROM, or activate Schala. Its purpose is to make every future code/data
allocation explicit and reproducible.

Canonical inert target:

- size: `0x800000`;
- map mode: `$35` (fast ExHiROM);
- ROM-size code: `$0D` (8 MiB);
- SHA-256:
  `26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93`;
- CRC32: `100CA949`;
- SNES checksum: `$396E`;
- SNES checksum complement: `$C691`.

These values apply only to the pinned clean ROM expanded without Project Epoch
allocations.

## Inert runtime checkpoint

`verified-runtime` for one bounded bsnes2014 checkpoint

The ignored local inert image was run for 3,600 no-input frames with RetroArch
1.7.1 and the pinned bsnes2014 Performance core. A clean ROM was run twice
under the identical configuration. All three runs exited successfully and
produced the same `329133`-byte BST1 state layout.

`tools/compare_bsnes2014_states.py` learns run-to-run payload variance from the
two clean states before comparing the inert image:

- the complete 128 KiB live WRAM image at state offset `$4AA3` is
  byte-identical;
- after excluding the BST1 ROM-SHA identity field at `$08-$47`, the inert
  comparison differs at exactly five payload bytes;
- the same five offsets vary between the two clean runs:
  `$2260`, `$25627-$25628`, `$2562D`, and `$25635`;
- there are zero unexplained payload differences.

Local state hashes:

- clean run 1:
  `22f6727119d09eef2e0037d55562bd883a93011afdb49905f69fd4692ae8578d`;
- clean run 2:
  `ab6184ba053339d080199190fb9739904598562cd291358a2c817a55c2b610cc`;
- inert ExHiROM:
  `47a0604c1fec3e90cbe9ee41b0a6a59c81d5ad97d5c91f28b3b752aeffbf7367`.

This proves checkpoint equivalence within measured core variance. By itself,
this boot checkpoint does not prove input handling, soft reset, saves, New
Game+, long-run attract behavior, or another emulator.

### Current bsnes field/menu/Equipment parity

`verified-runtime` for the listed current-core checkpoints

RetroArch 1.22.2 and current bsnes 115 regenerated the loaded-field state from
the canonical ROM and an isolated disposable SRAM. The exact raw checkpoint
was rebound to the clean inert ExHiROM by changing only the BSV2 content CRC;
the embedded core state and complete replay frames were preserved.

Matched 4 MiB and 8 MiB runs produced byte-identical raw current-core states
and pixel-identical screenshots for:

- 600-frame field idle;
- native main-menu entry and idle;
- Equipment entry with a tagged switch from Crono to Marle;
- the complete 3,599-frame field-idle replay.

The full-run raw core-state SHA-256 is
`cfc1faaa60ef4b76129f70e29a74668fed15533e2e1ae4acc9c4c3cf099ca22b`
under both mappings; the screenshot SHA-256 is
`4f283cfd6a1364b3b7cc38929543afffab6df3afbf35ba01e9dcccb33be32eef`.
At every checkpoint the `$7E2CA0-$7E2CEF` canary remains exact once and its
guards remain zero.

Complete hashes and reproduction commands are in
`docs/current_emulator_replay_harness_2026-07-26.md`. This strengthens inert
mapping compatibility; it does not prove party exchange, battle, save,
New Game+, attract mode, or production PC `$07` hooks on the current core.

### Menu, party-exchange, and battle checkpoints

`verified-runtime` for three additional state-replay checkpoints

The same inert transformation was applied to the supported-slot diagnostic
base used by the existing deterministic transition movies. The resulting
ignored 8 MiB test ROM has:

- SHA-256:
  `2dc889e565086cf1bcd8676f58d3428a4c3a65709839ab121f622a0db654836f`;
- CRC32: `73E36AF4`;
- no Project Epoch allocation or PC `$07` hook.

`tools/rebind_retroarch_bsv_rom_identity.py` pins the source movie identity,
updates only the BSV content CRC32 and the BST1 ROM-SHA wrapper field, and
asserts that the serialized core payload and complete controller-input stream
are unchanged. All three rebound movies retain the same zero-input stream
SHA-256:
`b30a8aa73669089db966896deb88bd2ac39774158c98a8e6ff78ed71575b541f`.

| Checkpoint | Rebound BSV SHA-256 | 3,600-frame state SHA-256 |
| --- | --- | --- |
| Full main menu idle | `12d2e4f2a427eab8194917e1710658035de08318c224ec80e9b9a97e232de475` | `aa434a4a9b3cd0e6a8a80c26f75a0c3ba387fe64e49a7eda211ec6262f9c8efa` |
| Post-swap party exchange idle | `799f28fcc544be657d727e31c9277996040eb445f9922b3e44627604e15d2e4a` | `2d1c3e3a96e468f43a8e9156e843d97738164b8fe5f9144cfb498161a7e61da7` |
| Native battle-engine idle | `2f7124b134d587d3b71148b5f8babf2d74ff2751a1bbae8753ffccd392f4ca1e` | `e7a7254c2ac0cf4b0df85a7342b61ebcc16cbaa1eaa76b23ddf200aa2d98523e` |

For every checkpoint:

- playback completed without a CRC warning or failed state save;
- the `$7E2CA0-$7E2CEF` canary remained exact once, with its four-byte
  structural front and sixteen-byte rear guards still zero;
- the complete candidate state payload matches a repeated 4 MiB control
  byte-for-byte after excluding the BST1 ROM identity field;
- all 128 KiB of WRAM therefore match that repeated control exactly;
- `tools/compare_bsnes2014_states.py --require-equivalent` passes with zero
  unexplained payload differences.

The corresponding repeated 4 MiB control state hashes are
`f0328e4936e998dc9cc120a39a6c9c996cf3f1e5de35516e45e205b8376ffd51`,
`5fa04732ec3c46e0dc6c97b34cc09c84e1b688f62d70c1d21b0abb085d4422fa`,
and
`a4fd1fa8c9825b716de84e067052abe2b054520e01fbe0e84029eff0b481d9d5`.

These movies begin at already established engine checkpoints. They prove
continued menu, party-exchange, and battle execution under the inert ExHiROM
mapping, not field-to-menu input, an ordinary encounter trigger, attack/tech
execution, victory/exit, save/load, or recruitment.

### All-slot Continue and full-load replay

`verified-runtime` for vanilla title-to-field load behavior

Three recorded input streams select Continue and load save slots 1, 2, and 3.
After rebinding their content identity to the inert 8 MiB diagnostic base,
each ran for 3,600 frames and reached the same loaded-field state as a repeated
4 MiB control.

| Slot | Input-stream SHA-256 | Rebound BSV SHA-256 | ExHiROM state SHA-256 |
| ---: | --- | --- | --- |
| 1 | `d793996d8f498909cc90bc1799bdb4c37e2098f9ea7550c5b393d5ff178e0c99` | `ac21c636c3ba0b25d8852f3ce58c16d00bad44cc0d721a156857953e95c703b0` | `3db6225a444a5a4ed4ebea6fb84268f080bb43f35c721610c576ec8a7c5b58b0` |
| 2 | `f5442a20684cf891fca11224d960101c7c7ea7b2e9e93f3d3d651115e9c2ae8d` | `684267874c602e5d3264fee1c15cfb271b8f1e0fcc98548aed793bdfe4bd0cf6` | `e0fa3dd2b5e0a47de4ca865b8a98917dd50fe30cd5f261e19f4ff2429ab15ac2` |
| 3 | `33e8d6eb6cbb334f474406bfba6620dc06b1ede9b1307d6a1200eb7f0e1d4402` | `1c076021d3395b7a8959304211d615349528342be013c35799413f4bcd408878` | `bb44df4f4dd502f11f265ac5f1d8921d87e0547f3d921587cd429b56188e0050` |

For all three:

- playback and state save completed with no CRC mismatch or failure;
- the complete serialized payload and all WRAM exactly match the repeated
  4 MiB control after excluding ROM identity;
- there are zero unexplained state differences;
- `$7E2CA0-$7E2CEF` is all zero with zero guards, matching the known cold
  initialization negative control.

This verifies the inert mapping through real title-menu input and the vanilla
full-load path for all slots. It does not verify a Project Epoch translated
save, Schala sidecar restoration, an in-game save write, New Game+, or erase.

### Independent-emulator preparation

The official portable Snes9x 1.63 Windows x64 release is staged only under
ignored `private/tools/` for the independent runtime gate:

- source:
  `https://github.com/snes9xgit/snes9x/releases/download/1.63/snes9x-1.63-win32-x64.zip`;
- archive SHA-256:
  `e2bd103819051eae57d163cdbbf6b3b92db73fdd4a6a0ee6a939e507eaa95db8`;
- executable SHA-256:
  `c843d906c1fa1fefa672e99cfd218041d229ef7598bce720465fe7a0905f3a4b`;
- license SHA-256:
  `70efeee282d82a6e9d26aeed5466d08c632369858371dc6a4644c8dcedc2be78`.

It has not yet been executed. Running newly downloaded software remains an
explicit user-confirmation boundary, and no independent-emulator result may
be claimed until that run occurs.

## Mapping and reserved ranges

`verified-static`

```text
file $000000-$3FFFFF  canonical vanilla ROM; CPU $C0:0000-$FF:FFFF
file $400000-$40FFFF  reserved mirror of vanilla bank $C0
file $410000-$7DFFFF  approved explicit allocation pool
file $7E0000-$7FFFFF  reserved/noncanonical tail
```

ExHiROM remaps low CPU bank `$00`'s high half to the upper ROM. Chrono Trigger
uses `$00:FF00` and other `$00:Fxxx` reset, interrupt, soft-reset, and data
paths. The scaffold therefore mirrors and reserves the complete first
vanilla bank at file `$400000-$40FFFF`; bank `$40` is never an allocation
pool.

CPU banks `$7E/$7F` are WRAM. Although fragmented low-bank mirrors can make
parts of file `$7E0000-$7FFFFF` reachable in some mappings, Project Epoch
conservatively excludes that tail. Normal allocations use simple full banks
`$41-$7D` only.

Both the original header copy at file `$00FFC0` and ExHiROM header copy at
`$40FFC0` receive map mode `$35`, size code `$0D`, and one Python-computed
checksum/complement pair.

## Allocation contract

Every expanded block must have a manifest record:

```text
allocation_id
file_start / file_end_exclusive
snes_start / snes_end_exclusive
size and power-of-two alignment
kind: code | table | graphics | palette | text | event | reserved
owner
evidence level
no_bank_cross
source artifact/hash
consuming hooks or pointer fixups
```

The validator rejects duplicate IDs, overlaps, bank `$40`, the `$7E/$7F`
tail, SNES/file mapping mismatches, non-power-of-two alignment, and
unapproved bank crossing. It never scans for or claims "free space."

Suggested coarse bank ownership, to be frozen only when the first production
builder is written:

```text
$41  runtime adapters and trampolines
$42  character/growth/equipment tables
$43  command, target, property, MP, animation, and learned-group tables
$44  text, names, descriptions, dialogue, and event metadata
$45-$47  field/battle graphics packets and assembly data
$48  full and preview portraits plus palettes
$49  recruitment event/location data
```

These are planning boundaries, not current allocations.

## Deterministic build chain

`proposal`

1. Validate the source size, SHA-1, fast-HiROM mode, declared size, and
   checksum.
2. Build the inert ExHiROM image in memory.
3. Validate an explicit allocation manifest.
4. Compile owned source assets/tables deterministically.
5. Assemble a pinned Asar 1.91 overlay with explicit `org` addresses and no
   freespace search. Disable assembler-owned checksum repair.
6. Assert every vanilla hook preimage before replacing it.
7. Recompute both header checksum copies in Python.
8. Compare the final source/target diff against the union of named
   allocations, header fields, and declared hook spans.
9. Produce a BPS patch with a pinned Flips version; do not use IPS for the
   expanded production image.
10. Emit source/target hashes, tool hashes/versions, allocation manifest,
    hook report, BPS hash, and deterministic reapplication proof.

No build step may write a full ROM outside ignored `private/` verification
paths, and no full ROM belongs in a release.

## Pointer and code rules

- Use `JSL/RTL` for deliberately matched cross-bank calls and returns. An
  intercepted routine that must retain an existing near `JSR` frame uses
  `JML` entry and tail transfers to bank-correct continuations instead;
  do not apply `RTL` to that near-call frame. See the September 8
  [MAP-006 correction and evidence](DATA_MAPPING_CORRECTIONS.md#map-006--a-cross-bank-tail-transfer-must-preserve-its-existing-call-frame).
- A vanilla 16-bit bank-local pointer table cannot point to `$41-$7D`;
  patch its reader or install a same-bank trampoline.
- Full 24-bit graphics pointers may target expanded banks only after every
  fixed-bank decoder is patched, including field non-flip code at `$C0:E687`.
- Keep each default allocation within one 64 KiB bank. Split large graphics
  assets deliberately and record every segment.
- Preserve vanilla `$00-$06` output at each adapter boundary.
- Never assemble over an address merely because the inert scaffold contains
  `$FF`; the manifest is the sole ownership authority.

## Approval gates

- [x] Canonical input validation.
- [x] Inert 8 MiB expansion.
- [x] Low-bank `$00` boot/data mirror.
- [x] Dual-header checksum validation.
- [x] Canonical address translation and allocation rejection tests.
- [x] 3,600-frame no-input bsnes2014 checkpoint with clean-control state
      equivalence and byte-identical WRAM.
- [x] 3,600-frame full-menu, post-swap party-exchange, and battle-engine
      checkpoint replays with canary preservation and payload-exact repeated
      controls.
- [x] Title-screen Continue and vanilla full load for all three slots with
      recorded input and payload-exact repeated controls.
- [ ] Pin and hash Asar and Flips executables.
- [ ] Freeze production bank ownership.
- [ ] Add hook-preimage and diff-coverage machinery.
- [ ] Produce and reapply an inert BPS expansion patch in ignored test space.
- [ ] Interrupt, soft-reset, translated save/write/load, and New Game+ tests in
      bsnes2014 and a second accurate emulator.
- [ ] Only then install non-inert Project Epoch allocations and PC `$07`
      adapters.

An inert ExHiROM that boots is evidence for the expansion scaffold only. It is
not evidence that Schala, her records, graphics, commands, items, or events
work.
