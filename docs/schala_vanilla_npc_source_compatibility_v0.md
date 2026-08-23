# Schala vanilla-NPC source compatibility v0

Status: private compatibility prototype; `verified-static` source reconstruction

Runtime status: not yet exercised

Production status: ineligible

## Decision

Project Epoch's first visual compatibility pass will derive Schala's existing
vanilla NPC family from the user's pinned clean ROM at local build time. This
is the shortest path to testing the real playable-character adapters with art
that already follows Chrono Trigger's native visual language.

This decision does not replace the original Project Epoch art. The current
ten-frame gameplay source, portraits, concepts, and Focus poses remain
preserved unchanged as deferred replacement-art research. They can return only
after a deliberate Chrono Trigger-style redraw and the existing originality,
packing, palette, and runtime gates.

No Crimson Echoes or Flames of Eternity material is included. A future
supplemental provider may be considered only when its exact source, author,
permission or license, transformations, and byte-level provenance are known.
Its absence must never prevent the vanilla-only provider from building.

## Why this is a useful first pass

The pinned vanilla Schala family is more complete than the current original
prototype in exactly the field-facing dimensions needed for early adapter
work:

| Component | Vanilla Schala compatibility source | Current original gameplay source |
| --- | ---: | ---: |
| Assembly records | 23 x `$28` bytes | 10 x `$28` bytes |
| Referenced graphics tiles | 79, exactly indices 0-78 | 81 including its blank tile |
| Primary facing blocks | 4 x 36 bytes | no complete animation blob |
| Entrypoints per facing | 9 | not yet bound |
| Character-specific colors | 12 | 15 visible colors |

The vanilla source therefore fits the already-proved twelve-color field loader
without requiring the uninstalled full-palette adapter. Its primary animation
data references all 23 assembly records and no out-of-range record. That makes
it a better diagnostic provider, not a complete playable-character packet.

## Pinned source chain

All values below are reconstructed only from the canonical headerless Chrono
Trigger US Rev0 ROM, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.

The source descriptor is NPC `$09` at file `$24F050` / SNES `$E4:F050`:

| Field | Selector | Resolved source | Size | SHA-256 |
| --- | ---: | --- | ---: | --- |
| Graphics | `$26` | compressed `$D9:E2CE`; decoded locally | 2,528 bytes / 79 tiles | `69322758b77fff5701cb0d5edb4ca34ab4109c2313ececd37bc018106fe84b73` |
| Assembly | `$1B` | `$DE:2B48-$DE:2EDF` | 920 bytes / 23 records | `ed6ad15d16d60b2135d1af3bc6fb10de283dcda744d06da33ea37699373d2314` |
| Primary animation | `$3B` | `$E4:67A0-$E4:682F` | 144 bytes | `9331925cce8129be325dfe52107bbdf9721fc642db1d9f7216f9017f810cd4ff` |
| Auxiliary animation | `$3B` | `$E4:BC38-$E4:BC5B` | 36 bytes | `58d697a461a3674556a92d05e2b26df3c37badcd0068edc54f95e2b394e2052d` |
| Palette | `$80` | `$E4:0C00-$E4:0C17` | 24 bytes / 12 colors | `8d5953b31b0ca6624d94c0c29935d34519418bc04f9e780fc466dca0c0c9ef3d` |

The 23 assembly records use every graphics tile index from 0 through 78.
Their only assembly-word flag families are `$0000` and horizontal flip
`$4000`; 82 tile words use the flip flag. The four aligned 36-byte primary
animation blocks expose nine four-byte entrypoint starts per facing and
reference records `$00-$16` collectively.

These are `verified-static` packet facts. The semantic role of every
entrypoint is not yet established.

## Builder and fail-closed boundary

`tools/build_schala_vanilla_npc_compat_v0.py` is a read-only ROM consumer. It:

1. requires the exact canonical ROM size, SHA-1, and SHA-256;
2. pins the exact size and SHA-256 of the existing strict C3 decoder before
   importing it;
3. validates the descriptor, pointer roots, compressed packet, decompression
   shape, assembly geometry, animation boundaries, palette shape, and all
   expected hashes;
4. emits no ROM, patch, save, state, image, or installed data;
5. permits extracted packet bytes only beneath the workspace's ignored
   `private/` directory;
6. rejects symlink, junction, and reparse-point output paths and validates
   stable regular-file identity before accepting an existing bundle;
7. writes a manifest-first sibling staging directory, verifies every staged
   byte, and promotes the complete directory atomically rather than exposing a
   partial final bundle;
8. refuses incomplete, unexpected, or differing existing output; and
9. supports a `--metadata-only` mode whose standard output is byte-identical
   to the checked metadata report and writes nothing.

The builder neither mutates a ROM nor emits a same-size ROM image, so it does
not invoke the ROM-write-intent guard. Any later builder that installs these
bytes into a ROM must use named expanded allocations, pinned hook preimages,
and the complete fail-closed intent/diff audit required by `AGENTS.md`.

### Reproduction

```powershell
python tools/build_schala_vanilla_npc_compat_v0.py `
  --rom 'private/input/rom_archive/Chrono Trigger (USA).sfc' `
  --output-dir private/build/schala_vanilla_npc_compat_v0

python tools/build_schala_vanilla_npc_compat_v0.py `
  --metadata-only > private/build/schala_vanilla_npc_compat_v0.metadata.json

python -m unittest tests.test_schala_vanilla_npc_compat_v0 -v
```

Checked source-control artifacts:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/build_schala_vanilla_npc_compat_v0.py` | 35,134 | `ab7e2346ffb2a3e9f117a4b814a07d3e8847fc5615e5dddd118f21fa4f3aa69e` |
| `tests/test_schala_vanilla_npc_compat_v0.py` | 13,982 | `4d61b692acfed15440a707364a8f1c867bbf4a2cc2a4ff65ee6baaeb1dd53065` |
| `references/schala_vanilla_npc_compat_v0.json` | 6,610 | `b5e7348b8bd4b186586d9397b24a3f50ae3a7e83d1605a079276db444ae484b9` |

The reference JSON contains no graphics, assembly words, animation sequences,
palette values, screenshots, or other extracted packet bytes. The private
binary outputs and their manifest must stay ignored and must never enter a
commit, archive, release, or public repository.

## Runtime contract for the next diagnostic

The next step is a private supported-slot field replay, not PC `$07`
integration. It must:

1. use the derived packet as an explicit visual provider without changing NPC
   `$09`, NPC descriptor `$E4:F050`, graphics entries `$07/$08`, the Epoch
   vehicle/name paths, roster data, save data, or the canonical ROM in place;
2. bind only entrypoints whose role has been proved, with a documented safe
   fallback for any missing or ambiguous playable-PC animation request;
3. compare against a clean control through Continue/load, field
   initialization, idle, all four directions, and calibrated movement;
4. preserve disposable save isolation and the existing WRAM/sidecar/Epoch
   canaries; and
5. record ROM, fixture, movie, emulator, screenshot, state, and output hashes.

Only after that supported-slot replay succeeds should this provider be
connected to a natural logical PC `$07` diagnostic. Battle, menu walking,
overworld, portrait, save preview, damage, casting, victory, death, and every
other context remain separate adapter gates.

## Explicit nonclaims

- This is not a complete playable Schala sprite sheet.
- This is not proof that NPC `$09` can be treated as PC `$07`.
- This is not a battle, menu, overworld, portrait, or save-preview packet.
- This does not approve a graphics-source index, hook, ROM allocation, or
  patch.
- This does not make extracted copyrighted game data redistributable.
- This does not establish that Crimson Echoes contains additional Schala art
  or that any such art is reusable.
- This does not retire or delete the original Project Epoch visual work.
