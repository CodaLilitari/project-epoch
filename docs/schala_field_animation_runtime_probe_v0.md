# Schala Field-Animation Runtime Probe v0

Evidence level: `exploratory-runtime-not-accepted`.

This probe narrows the vanilla field-animation contract at six exact program
counters. It is a diagnostic foundation for later Schala PC `$07` adapter
work; it is not a production patch or accepted runtime evidence.

## Identity receipts

| Input or source | Bytes | SHA-256 |
|---|---:|---|
| Canonical US Rev0 ROM, private only | 4,194,304 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| Native field checkpoint, private only | 133,993 | `26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e` |
| Disposable checkpoint SRAM, private only | 8,192 | `a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9` |
| Executed Mesen 2.1.1 program, private only | 70,470,144 | `d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b` |
| Staged Mesen core, private only | 7,143,424 | `65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74` |
| Tracked Lua collector | 19,345 | `9abca7bad4d7c11da1bf66462881de7eed246d195e8ef9c884f4c945f11583c7` |
| Tracked Python launcher | 55,200 | `d5cde9c33fddcfbacbae6aa28af6e820238226115bfe9b9f5775976570b75b96` |
| Tracked synthetic test module | 30,429 | `3ed78c6d3154468a5d4cd1428902bd974ac5c723443bcb328b5b5733b8ea3c03` |
| Earlier private exploratory aggregate | 11,615 | `829a0fe484f35737668b398f9adebb2740db30e8137065ec15af819aec4ae5e1` |

The Mesen archive is provenance only and was neither staged nor executed. Its
SHA-256 is `23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe`.

## Fresh tracked-harness reproduction

Four fresh runs used a 90-second Mesen test-runner timeout and an exact
105-second host timeout. Each route was repeated twice from the same pinned
checkpoint.

| Route | Runs | Counts at `C0:CA18`, `C0:CA35`, `C0:CA3D`, `C0:CB3A`, `C0:CBC2`, `C0:CC04` | Total records per run | Checkpoint-binding records per run | Normalized trace SHA-256 | Normalized semantic-manifest SHA-256 |
|---|---:|---|---:|---:|---|---|
| Idle | 2 | 192, 192, 192, 192, 192, 192 | 1,152 | 864 | `ff98496173d8b536007124b5deff3de195c044f5f4431b6d7b64783fcfcd68db` | `4cde0dddf5d0398380fbd38a83e93dc3faef1c7e6aacf889b3042f3bdb60db6d` |
| Right | 2 | 188, 188, 178, 188, 188, 188 | 1,118 | 830 | `d671b78795b2187522289c034a4963ef495c47b1b7150dfdc3e23ab91896f81d` | `c24cc516a7534b3f200eec3a5651d3e7d82e6b7afdbc3b1cae07d1992e1fc2a8` |

For the normalized trace receipt, only the top-level repetition number was
replaced with zero before sorted-key compact JSON serialization plus one line
feed. For the normalized semantic-manifest receipt, run-specific artifact
identities, reproduction fields, output paths, and top-level repetition were
excluded. Schema, evidence label, route, launcher and collector identities,
timeouts, runtime, private-input identities, summary with repetition replaced
by zero, preservation checks, and nonclaims were retained. Both repetitions
produced the same normalized hash for their route.

The four private trace/host-manifest receipts were:

| Case | Trace bytes / SHA-256 | Host-manifest bytes / SHA-256 |
|---|---|---|
| Idle 1 | 560,121 / `0970d464a7e138a8b5d4f70c2f546881335c58838e187980eeed220d3308f85e` | 4,125 / `8aa8bc7624ecba164f54878b5d777347cf7f9593e438a4083d9499fd0fb9076e` |
| Idle 2 | 560,121 / `eabc106d83821a2897da7eb92c9d2b45ac9c031e78e63c33acc4ff86f7966469` | 4,125 / `c766ae391b126af5c09488528bbe2392a86422454c7a0cb37e693661ddd83eb8` |
| Right 1 | 543,795 / `2dec6063e54968f691cc7661401592448147641042c3b83bc3593aaabe4303f6` | 4,129 / `2d85c9bfbe7ed1bf6d5081f891cc77faad3ed26420bea01b0ef0895138eab07b` |
| Right 2 | 543,795 / `61b594b488d688e00c8520c92429164a230940a5bdf847fd8e45c15f16daa496` | 4,129 / `7272fbb22393cc81b9c9798af7677f95bf9e8a582f8d5645e429e193f9fd7630` |

## Bounded conclusions

- Both idle runs reproduced the exact six-checkpoint counts and exact
  checkpoint bindings for the three active vanilla party objects.
- Both blocked Right-input runs reproduced a complete selector-`$01`,
  reset-to-reset loop from relative frame 55 through frame 97. The validated
  loop contains six executed main-frame reads and the paired timing
  zero/reload observations.
- The two repetitions of each route are semantically identical under the
  normalization described above.
- The observer reports zero explicit emulated-memory-write API calls. The
  tracked collector has no emulated-memory write or save-state-emission API
  call; it loads the pinned native checkpoint, reads state, records the trace,
  takes one endpoint screenshot, and stops the disposable emulator process.
- Each successful host manifest records that all pinned source files were
  rehashed equal, the shared Mesen `Saves` snapshot remained equal, every
  staged input was rehashed equal before teardown, and its disposable staging
  root was absent afterward. Mesen received a disposable process profile and
  `--doNotSaveSettings`.

## Reproduction boundary

Run the tracked launcher once per route with a new output directory strictly
below this workspace's ignored `private/test_runs` tree:

```text
python tools/run_mesen_field_animation_probe_v0.py --route idle --repetition 1 --output-dir private/test_runs/<new-idle-run> --timeout 90
python tools/run_mesen_field_animation_probe_v0.py --route right --repetition 1 --output-dir private/test_runs/<new-right-run> --timeout 90
```

Importing the Python module requires no private tree. Execution is separately
gated on the exact private ROM, checkpoint, SRAM, collector, emulator, runtime,
database, and settings identities. Output paths that are existing, dangling,
outside the exact workspace-private root, overlapping the protected ROM/state
checkpoint or shared `Saves` trees, or reached through a symlink, junction, or
reparse point are rejected.

## Nonclaims

- No difference was detected in the named source and staged ROM/SRAM hashes
  across their guarded intervals. No ROM or patch was emitted. No ROM, save,
  state, trace, image, emulator binary/archive, or extracted stream is included
  here.
- This does not establish a Schala adapter, an eighth-character runtime
  record, PC `$07` field or battle graphics, animation-slot semantics,
  auxiliary-animation semantics, a production allocation, or a safe hook.
- The Right route does not establish a runtime read of the main-stream `$FF`
  terminator; its loop conclusion is limited to the observed timing-controlled
  reset path.
- The endpoint screenshots are presentation-only private artifacts and are not
  semantic evidence.
- The preservation checks cover the named pinned files, shared `Saves`
  snapshot, staged files, and disposable staging directory. They are not an
  audit of the entire worktree or every emulator-owned host path.
