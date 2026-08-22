# Project Epoch emulator update, 2026-08-22

Status: installed and boundedly validated  
Evidence: `verified-runtime` only for the exact new runs described here  
Production ROM integration: not performed  
Historical evidence reclassification: not permitted

## Result

RetroArch itself did not require a version jump. At retrieval time on
2026-08-22, the newest official stable frontend was still
[RetroArch 1.22.2](https://github.com/libretro/RetroArch/releases/tag/v1.22.2),
Git `69a4f0e`. Project Epoch's preserved portable archive was already the exact
official Win64 stable package, so it was extracted into two new directories on
`C:` without running an installer or changing a user profile.

The substantive update is the official rolling `bsnes_libretro.dll` obtained
from the
[Libretro Win64 current-core buildbot](https://buildbot.libretro.com/nightly/windows/x86_64/latest/bsnes_libretro.dll.zip).
The URL is mutable. The exact archive downloaded on 2026-08-22 is therefore
preserved under ignored `private/` storage and pinned below.

The update passed two separate checks:

1. two independent executions of Project Epoch's original standalone round8
   SHA-256 diagnostic; and
2. two isolated 120-frame boots of exact disposable copies of the canonical
   clean Chrono Trigger ROM.

No Project Epoch ROM was built or installed, no hook or allocation was
promoted, and no existing ROM, SRAM, state, log, manifest, emulator directory,
or accepted historical evidence file was overwritten.

## Side-by-side installations

### Restored historical harness

Path:

```text
private\tools\RetroArch-1.22.2-ProjectEpoch-20260724
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `retroarch.exe` | 18,641,482 | `81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a` |
| `cores\bsnes_libretro.dll` | 5,609,890 | `003c7de04adef5f64fa106ef5175a0f66b08032001bde0383af97c5e5b81d470` |
| `info\bsnes_libretro.info` | 4,193 | `fc6f9bb67e99848bfcad99e5e4bb028a9ce998d3bbd0195fded36edef5ed1506` |

These bytes reproduce the old tool pins. They do not change the provenance of
the accepted July logs, whose runtime path was
`private\tools\RetroArch-1.22.2`. The restored `C:` copy is a convenience and a
future replay input, not a reason to edit those logs or manifests.

### Current rolling-core harness

Path:

```text
private\tools\RetroArch-1.22.2-ProjectEpoch-current-20260822
```

| File | Bytes | SHA-256 |
|---|---:|---|
| `retroarch.exe` | 18,641,482 | `81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a` |
| `cores\bsnes_libretro.dll` | 5,661,090 | `bb00b395dcac6db960ecacaaf40ea9906fea9b7e23cedf55f8d117c44fcdde78` |
| `info\bsnes_libretro.info` | 4,193 | `fc6f9bb67e99848bfcad99e5e4bb028a9ce998d3bbd0195fded36edef5ed1506` |

The core-info file still reports display version 115. That display string is
not a binary identity. The new DLL differs in both size and SHA-256 from the
July DLL, so it is a separate runtime evidence line.

The portable frontend created `info\core_info.cache` and
`config\bsnes\bsnes.opt` inside this new directory on first use. It did not
touch a pre-existing RetroArch profile.

## Download provenance

### RetroArch

- Official portable package:
  [stable 1.22.2 Win64 `RetroArch.7z`](https://buildbot.libretro.com/stable/1.22.2/windows/x86_64/RetroArch.7z)
- Preserved archive:
  `private/downloads/RetroArch-1.22.2-Win64.7z`
- Size: 202,509,078 bytes
- SHA-256:
  `b2139b1d0f9d4526dc6b5ce23cbb3efdc766096fa6f2c3df016818b486ac6372`

### Rolling bsnes core

- Response date: `2026-08-22T17:50:04Z`
- HTTP `Last-Modified`: `2026-08-22T05:01:07Z`
- HTTP `Content-Length`: 1,056,730
- HTTP ETag: `"223719998"`; this is opaque and is **not** treated as a
  cryptographic hash
- Preserved archive:
  `private/downloads/bsnes_libretro-2026-08-22-win64.zip`
- Archive SHA-256:
  `60441409e6877b52bb135588cba1b278d7713db0ec512b188aae66599ced3081`
- Extracted DLL SHA-256:
  `bb00b395dcac6db960ecacaaf40ea9906fea9b7e23cedf55f8d117c44fcdde78`
- Preserved HTTP headers SHA-256:
  `9c096a38f81d8bc59c2645338df7f171ce03e6a9ed7087c1c38db48f8e6eb6ea`

The observed official
[`libretro/bsnes-libretro`](https://github.com/libretro/bsnes-libretro)
source head was
`6d19eef5835a792e241e33194b4c1e9b75405b88`. Libretro's recipe builds this
core from that repository's `master` branch, but the rolling binary has no
per-artifact source-commit attestation. Treating the DLL as a build of that
exact commit is an inference, not proved provenance.

## Standalone round8 compatibility evidence

The current core ran two fresh copies of the source-built, all-Project-Epoch
standalone round8 cartridge. It did not read a Chrono Trigger ROM, save, or
state.

Both current-core RASTATE files:

- passed `tools/inspect_schala_sha256_65816_benchmark_state.py`;
- remained format `BST1`, serializer `115.1`, 290,423 core-state bytes;
- produced elapsed vectors `68, 69, 69` and final frame 207;
- produced result-record SHA-256
  `58af32127cdf9b0f8a11fee2d2a4bb90f8e847bda1492ad5aae9092e1f700c75`;
- produced scratch-with-guards SHA-256
  `14cc30162870a2fbac89a49a07568a31c194c9ed7d8cc7d0b2250486e103303f`;
- preserved all-zero SRAM SHA-256
  `9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47`.

The two full states are intentionally not byte-identical. Their 130,502
differences consist of the exact known eight-byte serializer span
`$021E-$0225` plus 130,494 bytes of uncleared WRAM outside every defined
result, scratch/guard, and SRAM evidence span. There are zero unaccounted
differences.

Private evidence:

- tree:
  `private/test_runs/retroarch/bsnes-current-20260822-round8-smoke/`
- manifest SHA-256:
  `244ae601c59252e2649bc0213856af9a84cb5c9e73337ed56ce631aab953abb3`
- `SHA256SUMS.txt`: 14 entries, all reverified

This confirms compatibility with the isolated diagnostic. It does not remove
the predeclared 30-frame stop gate: all three digests still take more than 30
frames, so synchronous or cooperative production integration remains barred.

## Canonical clean-ROM boot smoke

Two hidden-window runs each used an exact disposable copy of the canonical
4 MiB clean ROM and an independent all-zero 8 KiB same-stem SRAM. Each ran for
exactly 120 frontend frames, exited with code 0, logged successful core load
and autosave serialization, and left both ROM and SRAM bytes unchanged.

Across the two 290,423-byte core states, all differences are confined to:

- the same exact eight serializer bytes at `$021E-$0225`; and
- 41,291 bytes in the volatile WRAM serialization span.

There are zero differences outside those two bounded regions. The early boot
thumbnails are black and make no visual-title claim; this is a load, bounded
execution, and serialization smoke only.

Private evidence:

- tree:
  `private/test_runs/retroarch/bsnes-current-20260822-clean-rom-smoke/`
- manifest SHA-256:
  `1fc4b32a1509e413b307e847a466879095fe005686c4a7553c6aa6be2e183a74`
- `SHA256SUMS.txt`: 14 entries, all reverified

The canonical source ROM was never a live output path. Both runs used copies
under ignored `private/` storage.

## SRAM rule remains mandatory

Current bsnes can open its same-stem SRAM directly even when RetroArch logs
`[SRAM] Skipping SRAM load` and receives `--sram-mode=noload-nosave`.
The new runs again changed the disposable files' timestamps, although their
all-zero bytes remained identical. Every future run must continue to use:

1. a uniquely named disposable ROM copy;
2. a same-stem disposable SRAM copy in an isolated directory;
3. before-and-after hashes; and
4. no save-state reuse across unpinned core binaries.

## Historical evidence and test behavior

The accepted baseline, fast, and round8 manifests remain byte-for-byte
unchanged:

| Historical manifest | SHA-256 |
|---|---|
| baseline | `4eb566a7a7b657cad7c8c0a0f58d481156ec5f834482e3584d074673311a0cac` |
| fast candidate | `c464ab1006847797e6b85fc85c80a03d978f5537e11fa6baed4d4093fff4840e` |
| round8 candidate | `ad20b04e0be5345184db3246bb6be02bd669ad0cb50d5b4799e3b9e874be7a45` |

The historical builders still default to the original `D:` paths because the
accepted logs contain those paths. The two live accepted-artifact tests now
include the missing toolchain files in their `skipUnless` predicates. With
`D:` unavailable, they report two explicit environment-gated skips instead
of errors; all synthetic builder and fail-closed tests still execute.

## Reproduction variables

Use the bundled Python runtime while the old `D:` Python installation is not
mounted:

```powershell
$epochPython = 'python'
$currentRetroArch = 'private\tools\RetroArch-1.22.2-ProjectEpoch-current-20260822\retroarch.exe'
$currentBsnes = 'private\tools\RetroArch-1.22.2-ProjectEpoch-current-20260822\cores\bsnes_libretro.dll'
```

Exact per-run command arrays, configs, logs, state identities, input hashes,
and comparison boundaries are in the two private manifests. Never point their
output directories at a preserved save or historical evidence tree.

## Evidence boundary

These checks establish only that the pinned 2026-08-22 core:

- loads and executes the source-built standalone cartridge correctly at its
  accepted evidence spans;
- loads the clean US Rev 0 game image for 120 bounded frames; and
- emits serializer-115.1 states that the current extraction tooling can read.

They do not prove a full gameplay replay, old save-state interchange,
Project Epoch PC `$07`, Schala field or battle rendering, save/load behavior,
an approved ROM allocation, or acceptable production SHA timing. Those gates
remain separate.
