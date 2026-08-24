# Schala vanilla-NPC source compatibility v0

Status: private compatibility prototype; `verified-static` source reconstruction

Runtime status: bounded supported-Lucca field replay accepted; the provider
builder itself remains read-only and `verified-static`

Production status: ineligible

## Decision

Project Epoch's first visual compatibility pass derives Schala's existing
vanilla NPC family from the user's pinned clean ROM at local build time. This
provided the native-style first-pass source for the supported-slot adapter test
recorded below.

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
8. accepts only the exact six artifact basenames before creating the staging
   directory, rejecting absolute or traversing names from synthetic callers;
9. refuses incomplete, unexpected, or differing existing output; and
10. supports a `--metadata-only` mode whose standard output is byte-identical
   to the checked metadata report and writes nothing.

The builder neither mutates a ROM nor emits a same-size ROM image, so it does
not invoke the ROM-write-intent guard. A private supported-slot diagnostic may
replace an exact named vanilla-owner envelope only through pinned canonical
preimages and the complete fail-closed intent/diff audit. Any production
installer must instead use named expanded allocations, adapted readers, pinned
hook preimages, and the complete guard required by `AGENTS.md`.

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
| `tools/build_schala_vanilla_npc_compat_v0.py` | 36,018 | `0ad950e0e069b1171a306da52479014ac896f1d3d4c7e773896f63db34b6c1a9` |
| `tests/test_schala_vanilla_npc_compat_v0.py` | 15,097 | `612fffd23f848122dee4b5b0b18c74cbf0bdec4a4f0235a4b6beb7f9f03503cc` |
| `references/schala_vanilla_npc_compat_v0.json` | 6,610 | `b5e7348b8bd4b186586d9397b24a3f50ae3a7e83d1605a079276db444ae484b9` |

The reference JSON's `next_gate` is the static provider's prerequisite
contract, not the current project milestone. The separate supported-slot
installer and runtime record below now satisfy that prerequisite at their
bounded Lucca-field ceiling; the pinned static artifact remains unchanged for
provenance.

The reference JSON contains no graphics, assembly words, animation sequences,
palette values, screenshots, or other extracted packet bytes. The private
binary outputs and their manifest must stay ignored and must never enter a
commit, archive, release, or public repository.

### Private supported-slot installer

`tools/build_schala_vanilla_npc_supported_slot_smoke_v0.py` rebuilds the
provider in memory and creates only an ignored, disposable Lucca-slot
diagnostic. It requires the exact canonical preimages and declares precisely
these six writes before invoking the project guard:

| Diagnostic write | File span, half-open | Bytes |
| --- | --- | ---: |
| Provider graphics over Lucca prefix | `$136B40-$137520` | 2,528 |
| Provider assembly over Lucca prefix | `$1C4E70-$1C5208` | 920 |
| Lucca primary animation | `$243880-$243CF0` | 1,136 |
| Lucca auxiliary timing | `$24AA20-$24AB3C` | 284 |
| Lucca twelve-color field palette | `$240030-$240048` | 24 |
| SNES checksum pair | `$00FFDC-$00FFE0` | 4 |

The complete-diff audit covers every changed byte and rejects any mutation
outside those declarations. The provider source spans, NPC descriptor table,
PC/NPC routing tables, graphics entries `$07/$08`, Epoch data, Lucca tails,
record, roster, Tech, item, and save regions remain exact negative controls.

Each source facing exposes nine four-byte entrypoint starts. The installer
copies entrypoint cells `$00-$08` by numeric position only and makes no claim
that a source number has the same semantic role in the PC consumer. Lucca
selectors `$09-$46` receive the corresponding facing's exact source
entrypoint-zero cell, while the shared auxiliary table receives its exact
entrypoint-zero timing cell. This is a documented safe fallback shape, not a
complete animation-role map.

## Accepted supported-slot diagnostic

The private supported-slot field replay is now accepted as bounded
`verified-runtime` evidence. A separate fail-closed builder derives the five
provider assets in memory from the pinned clean ROM, installs them only over
Lucca's existing graphics, assembly, primary-animation, auxiliary-animation,
and twelve-color field-palette windows, and runs the complete ROM-write intent
and diff audit before writing an ignored diagnostic image. It leaves NPC
`$09`, descriptor `$E4:F050`, graphics entries `$07/$08`, the Epoch paths,
roster, record, Tech, item, and save data unchanged.

Two fresh diagnostic runs and two matched clean-ROM controls began before
Continue/load on RetroArch 1.22.2 with the pinned current bsnes core. The
recorded schedule exercised bounded up, down, left, right, and B+right run
movement. At the inspected checkpoints where the control renders Lucca, the
diagnostic coherently renders the canonical-ROM-derived Schala NPC-family
sprite; both repeated endpoint states and endpoint frames are deterministic.
The relocation-candidate canary,
front and rear guards, saved `$0430-$047F` bytes, roster, joined mask, Epoch
name, and isolated no-load/no-save boundary match the control.

The provider's nine source entrypoint cells are preserved by numeric position
only. Selectors `$09-$46` use the corresponding facing's entrypoint-zero cell
and the shared entrypoint-zero timing cell as an explicit fallback. This does
not assign semantic names to those source entrypoints or prove which high
selectors the accepted route requested.

Exact artifacts, hashes, frame schedule, reproduction steps, negative
controls, and nonclaims are in
[`schala_vanilla_npc_supported_slot_smoke_v0.md`](schala_vanilla_npc_supported_slot_smoke_v0.md).
Only after a separate natural logical-PC-`$07` diagnostic may this provider be
connected to the eighth identity. Battle, menu walking, overworld, portrait,
save preview, damage, casting, victory, death, and every other context remain
separate adapter gates.

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
