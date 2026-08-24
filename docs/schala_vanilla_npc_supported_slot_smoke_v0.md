# Schala vanilla-NPC supported-slot smoke v0

Status: `verified-runtime` for the bounded private field replay described here
Logical PC `$07`: not exercised
Production integration: not performed
Last updated: 2026-08-24

## Result

The canonical vanilla Schala NPC-family provider now survives a fresh
Continue/load and a calibrated field-motion sequence through the ordinary
seven-PC Lucca path on the current bsnes core. Two provider executions and two
matched clean-ROM controls completed the same 1,600-frame window. At the
inspected checkpoints, the provider renders Schala where the control renders
Lucca while Crono, Marle, and field geometry remain coherent. Exact endpoint
witnesses preserve party state and the protected Project Epoch WRAM candidate.

This is the first accepted runtime use of the complete compatibility provider:
23 assembly records, 79 referenced tiles, four bounded primary-facing streams,
one shared auxiliary stream, and the native twelve-color field palette. It is
not a natural eighth-character or production result. The diagnostic installs
the provider only over Lucca-owned field data, and the replay exercises only
the selectors reached by this load and movement sequence.

The accepted observations are:

- the replay begins before Continue/load, so Schala's appearance follows a
  fresh field-provider fetch rather than inherited sprite state;
- the provider and clean control are pixel-identical while both are still
  black at the accepted extracted frame 100;
- Schala remains coherent at the inspected checkpoints after Up, Down,
  Left, Right, and B+Right movement, with no missing tiles, disappearance, or
  visible pointer escape at those checkpoints; the accepted logs and endpoint
  states show that all four executions completed without a freeze or crash;
- the sparkle visible after the Left interval is also present in the clean
  Lucca control and is therefore treated as location behavior, not a provider
  defect;
- both provider endpoints are byte-identical to each other, and both clean
  endpoints are byte-identical to each other;
- the extracted frame at 1,590 is byte-identical between repetitions of the
  same case; and
- every accepted endpoint retains the exact WRAM canary once, zero front and
  rear guards, and matching party/name/compatibility witnesses.

Evidence level is deliberately split:

- `verified-static`: exact source derivation, provider geometry, write spans,
  canonical preimages, output hash, and complete-diff coverage;
- `verified-runtime`: the four current-bsnes executions, their recorded input
  window, videos, inspected-checkpoint comparisons, repeat endpoints, and
  state witnesses;
- `hypothesis`: any semantic name assigned to one of the NPC provider's nine
  source entrypoints, or any claim that selectors not reached here behave as a
  finished playable-PC animation set.

## Private diagnostic build

The four accepted emulator executions used the diagnostic ROM emitted by
builder version `0.2.0`, whose historical source SHA-256 was
`81b82df62198b63c05d42e71626c88c8757513193967d44ebf50843798e90a68`.
That runtime build receipt is preserved unchanged. The tracked fail-closed
builder, `tools/build_schala_vanilla_npc_supported_slot_smoke_v0.py`, is now
version `0.2.2`, 26,389 bytes, with SHA-256
`d5b43ee02d7a5064cd2cd673f743aa92826d94213e7f1cdb1b811ea2ed3f301b`.
It derives all provider bytes in memory through
`tools/build_schala_vanilla_npc_compat_v0.py`; no extracted provider payload is
tracked.

The hardened `0.2.2` reproduction emits the exact same 4,194,304-byte ROM and
SHA-256 as the historical runtime build. Its new manifest adds the explicit
evidence level and reproduction contract and records the current builder
identity. The four BSV carriers remain bound to the same ROM bytes by their
content CRCs and the pinned output SHA-256; no emulator rerun is claimed merely
from reproducing those bytes.

Pinned inputs and outputs:

| Object | Bytes | SHA-256 |
| --- | ---: | --- |
| canonical headerless US Rev0 ROM | 4,194,304 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| private diagnostic ROM, historical runtime build and hardened reproduction | 4,194,304 | `75dc966ce377accf19ce1a7eb2ac200d5f68fbb94b9436eee7f09e613cc4ad42` |
| preserved runtime build manifest, builder `0.2.0` | 12,111 | `86c5b73dd8770981807d706affd5dea75d49be604821fbac8a1bdedae175cb06` |
| hardened reproduction manifest, builder `0.2.2` | 12,626 | `cfd9c5384d6b856ae4980b9b7d422b9f8adfe8a7f525e0a1429941d94d8fd167` |

The provider payload reconstructed from the canonical ROM is:

| Component | Bytes | SHA-256 |
| --- | ---: | --- |
| graphics, 79 tiles | 2,528 | `69322758b77fff5701cb0d5edb4ca34ab4109c2313ececd37bc018106fe84b73` |
| assembly, 23 x `$28`-byte records | 920 | `ed6ad15d16d60b2135d1af3bc6fb10de283dcda744d06da33ea37699373d2314` |
| four source primary blocks | 144 | `9331925cce8129be325dfe52107bbdf9721fc642db1d9f7216f9017f810cd4ff` |
| shared source auxiliary block | 36 | `58d697a461a3674556a92d05e2b26df3c37badcd0068edc54f95e2b394e2052d` |
| twelve-color field palette | 24 | `8d5953b31b0ca6624d94c0c29935d34519418bc04f9e780fc466dca0c0c9ef3d` |

The builder requires exact canonical preimages and declares these complete
same-size-ROM write envelopes:

| Purpose | File span | Declared bytes | Replacement SHA-256 |
| --- | --- | ---: | --- |
| checksum complement and checksum | `$00FFDC-$00FFE0` | 4 | `621a7aa967c8b582ffe7492b1e4e35195c6004b954cabf348c4a80c4aa6ebf42` |
| provider graphics over Lucca prefix | `$136B40-$137520` | 2,528 | `69322758b77fff5701cb0d5edb4ca34ab4109c2313ececd37bc018106fe84b73` |
| provider assembly over Lucca prefix | `$1C4E70-$1C5208` | 920 | `ed6ad15d16d60b2135d1af3bc6fb10de283dcda744d06da33ea37699373d2314` |
| provider palette over Lucca field palette | `$240030-$240048` | 24 | `8d5953b31b0ca6624d94c0c29935d34519418bc04f9e780fc466dca0c0c9ef3d` |
| bounded primary provider table | `$243880-$243CF0` | 1,136 | `0111bb6b666f6ba08d77be7efb02db06c00eac8febb8c1338ae7abc3666ac610` |
| bounded auxiliary provider table | `$24AA20-$24AB3C` | 284 | `7aa0c1e3cc39d131ccb5b0d99c02325c3a1ee764ae16293c5bf753ec908d9631` |

The write-intent guard used SHA-256
`418d958b32206945a91f15fcbcf13c932970b23d60e07cfde1dd2d027ecd3978`.
It returned `images-valid`, verified every preimage, and covered the complete
diff: 3,759 changed bytes inside 4,896 declared bytes, with no undeclared
mutation. The difference between declared and changed byte counts consists of
same-value bytes inside the exact bounded replacement spans.

No other Lucca data is changed. The builder changes no pointer table, graphics
source entry `$07` or `$08`, NPC `$09`, NPC descriptor `$E4:F050`, Epoch data,
character record, roster, Tech, item, or save structure. This is intentional
in-place destruction of disposable Lucca-owned diagnostic data, not a proposed
production allocation.

### Entrypoint fallback contract

Each source facing has nine four-byte numeric entrypoint starts. The builder
copies entrypoints `$00-$08` exactly by numeric position, without assigning
human direction or playable-PC semantics. Source primary and auxiliary
terminator deltas are identical for all four facing blocks:

`[1, 4, 0, 1, 1, 1, 2, 5, 1]`

The zero delta at entrypoint `$02` is a valid already-terminated source cell.
For every higher Lucca selector `$09-$46`, the builder installs an exact copy
of that facing's source entrypoint-zero four-byte primary cell and the shared
entrypoint-zero auxiliary cell. This makes every cell in the bounded Lucca
tables structurally terminating. It does not prove that all 71 selectors were
requested at runtime, that they are semantically equivalent, or that the
fallback is suitable for production animation.

## Current emulator and replay carrier

The accepted environment is:

| Component | Bytes | SHA-256 |
| --- | ---: | --- |
| RetroArch 1.22.2, Git `69a4f0e` | 18,641,482 | `81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a` |
| current `bsnes_libretro.dll` | 5,661,090 | `bb00b395dcac6db960ecacaaf40ea9906fea9b7e23cedf55f8d117c44fcdde78` |
| current bsnes core-info file | 4,193 | `fc6f9bb67e99848bfcad99e5e4bb028a9ce998d3bbd0195fded36edef5ed1506` |
| null-driver configuration | 974 | `ca07bf904bc1273c0b2dbce047dfe7cbb1f0f6a9fa4ce4fd8cbce9bc5192544d` |
| auto-state override | 215 | `51e7c109cc8a7d22f489b828356918fe1a652b9216d9a6d45fdd77fc87c041a1` |
| original 3,599-frame zero-input carrier | 711,421 | `5c3fc0c4f8f6dc1a8e7afec94337db511115e82fd1b10bc2f1e41606a20be696` |

The run logs identify RetroArch 1.22.2, core geometry 256x224, 60.10 fps,
and a 48,000 Hz nominal sample rate. The null audio driver does not initialize,
as expected for this headless configuration; execution and video recording
continue. Every accepted log reports replay start and end, successful
auto-state creation, `SRAM will not be saved`, `Skipping SRAM load`, and normal
core unload.

The source BSV contains 3,599 frames. Each accepted invocation used
`--max-frames=1600`, so only frames 0-1,599 belong to this runtime claim. This
distinction prevents the unused tail of the carrier from being mistaken for
executed coverage.

### Initial state and exact inputs

A clean-ROM title RASTATE was captured after 1,750 frames. Its private
container is 660,888 bytes with SHA-256
`a17c5018188c589c6a7ca828c0014f75e40ca0c925136091ae831f0ac94327a0`.
The replay editor replaced the zero carrier's initial state with the sole raw
290,423-byte current-bsnes core-state chunk. The canary injector then used its
pinned current-bsnes layout to write only `$7E2CA0-$7E2CEF`, at core-state
offset `$4F24`, before the movie CRC was bound independently to the diagnostic
and clean ROMs.

The final provider and clean BSVs contain the same input events:

| Frame interval, inclusive | Player-1 input | Purpose |
| --- | --- | --- |
| 60-61 | Left | choose Continue |
| 210-219 | A | load the selected save |
| 650-709 | Up | calibrated field movement |
| 770-829 | Down | calibrated field movement |
| 890-949 | Left | calibrated field movement |
| 1010-1069 | Right | calibrated field movement |
| 1130-1189 | B+Right | calibrated run movement |

No other Player-1 joypad value is nonzero. The parsed BSV header facts are:

| Movie | Bytes | Content CRC-32 | SHA-256 |
| --- | ---: | --- | --- |
| provider | 974,373 | `1B7ABABC` | `1bf62c5ec245b036fff8ce54239a960a79ad8d6711c93a19ac2bb4066c2a3eba` |
| clean control | 974,373 | `2D206BF7` | `0b5556e02d471a079f5d55957a9d2a13bd159794fa1189a193a07efc409f2b09` |

Both have identifier `1785104185`, 3,599 replay frames, and a raw uncompressed
initial-state block of 290,437 bytes containing a 290,423-byte core state.

## Accepted run receipts

Four executions are accepted: two provider runs and two clean controls. The
second run in each pair used a same-byte ROM copy with a distinct stem so its
video, log, save, and auto-state destinations could not alias the first run.
All are below
`private/test_runs/schala_vanilla_npc_supported_slot_smoke_v0/current_core_full_provider/`.
The accepted video/log/state stems are `provider_motion`, `provider_repeat2`,
`clean_motion_r2` with state stem `clean_control_run`, and `clean_repeat2`.
The exact 30-artifact metadata allowlist is
[`current_schala_vanilla_npc_supported_slot_accepted_artifacts_v1.json`](../references/current_schala_vanilla_npc_supported_slot_accepted_artifacts_v1.json);
it excludes every ROM/SRAM image, setup intermediate, and rejected run.

| Case | Video bytes | Video SHA-256 | Log SHA-256 | Endpoint state SHA-256 |
| --- | ---: | --- | --- | --- |
| provider, first | 812,592 | `40ec168875b245daca44dd7bcfd97d2b69a10bf0e1daa4614a7d5802b0de3b69` | `beddcb3351e0e0a4f7fb215b0af637eb12b8d86c414ce82f598cff5669b128e2` | `7a8f91acc43f831e5719a5859659dc62cfde3432b320cc5193a081ef2ea52f12` |
| provider, repeat | 812,592 | `8d371f8a9442437617680f56744bdd834f1799f66be71509d50271d108d2ad17` | `d9cfb386b5d6077ccaef05869526a6b1f247845acd8220fedc71f5db49456c2a` | `7a8f91acc43f831e5719a5859659dc62cfde3432b320cc5193a081ef2ea52f12` |
| clean, first | 810,040 | `e02fe3e2c14433e9d02c1ed540509a219b1f93435cd1450e3ffdd1641a2f3b7a` | `544a8c450ffc6815cbc6ea986a9925cd839e839f447d9d5dd5445f2c3d23a99d` | `459c0bcfdfecc350846f5434e849f7e6a3d8f44d331362cedb8fe67683141ba9` |
| clean, repeat | 810,040 | `f8843d9210e1dc52ac6a4eee22d02b75c32abffe66ac70d83be0e5387d49804d` | `b2f8b2aa62f212958c724d8b7466622e2d36c78c45cd38f310132f81409d7436` | `459c0bcfdfecc350846f5434e849f7e6a3d8f44d331362cedb8fe67683141ba9` |

The container-level videos differ between repetitions because they are
separate recording/muxing runs. The emulator endpoints do not: the two
provider RASTATEs are exact 893,840-byte matches, and the two clean RASTATEs
are exact 893,840-byte matches. Their decoded core-state receipts are:

| Case | Core-state bytes | Core-state SHA-256 |
| --- | ---: | --- |
| provider, both repetitions | 290,423 | `ef69214e24bc6323182c1368b974f135322f400b9e6f0b6a7b59cfe6b2a0a902` |
| clean, both repetitions | 290,423 | `0f1ffe1ad166cc81a875e248b0200291b33e6cc8cdc3c28a3c5f667b77efb084` |

### State witnesses

`tools/inspect_current_wram_candidate.py --require-canary` independently
decoded every endpoint. All four states report:

| Witness | Exact result |
| --- | --- |
| canary SHA-256 | `4e3df1af239b20cefae9d9a2219f384a4934b1916da11b001b9e501b84e06290` |
| canary occurrences | exactly one, at core-state offset `$4F24` |
| front guard | `00000000` |
| rear guard | `00000000000000000000000000000000` |
| `$7E2830-$7E287F` compatibility-block SHA-256 | `b70a2e5d291811c9f58689d7d0dbbfe89b913a3c0b1ef846de4607f0af6d9c73` |
| compatibility block matches save slot `$0430-$047F` | true |
| active party `$7E2980-$7E2982` | `000102` |
| roster `$7E2980-$7E2988` | `000102828004030605` |
| joined flags `$7E29AF` | `$FE` |
| Epoch name `$7E2C4D-$7E2C52` | `a4c9c8bcc100` |
| field location / explore mode | `$01DA` / `$01` |

The four same-stem SRAM files used only as inspector references are each
8,192 bytes and hash to
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.
The emulator logs independently confirm that disk SRAM was neither loaded nor
saved during the accepted executions.

These witnesses prove only that the protected range and selected surrounding
state survived this particular load-and-field interval. They do not declare
`$7E2CA0-$7E2CEF` globally free or approve its production use.

### Visual receipts

The following private PNGs were decoded from the accepted recordings. They
remain ignored evidence; their hashes are recorded here without embedding any
image or game data. Visual assessment is limited to the listed checkpoints; it
is not a frame-by-frame census of the 1,600-frame execution window.

| Frame | Provider SHA-256 | Clean SHA-256 | Role |
| ---: | --- | --- | --- |
| 100 | `9fa593b0f76924bc13a299a078cf53922283161622ae1f4d19020b0fb14d466a` | same | pre-load black control |
| 710 | `2bc61746272e495e1380fd62773a8386c7675aefe8b789a26cad978e8d6d8188` | `914bd774d78a9aba589e39efa8645bd082ef96f7ba7f716e9fe528bffdf5db43` | after Up interval |
| 830 | `fbcda5a26fa86fa34ec6d399281f3491d89d80c726472ea207484f3027a15d1e` | `08a3c5e6bdf41415ebb4915832d20cf45b2f21166e564466aa8f17c871d0c745` | after Down interval |
| 950 | `d521a55b92f6e53fa5244b73758f141110263b797b76b1f645608db8ade7361e` | `8c31e1a293decdff937d33e6fa6383c647800a30d59ba63cb557d9c7549e4b4d` | after Left; matched location sparkle |
| 1070 | `3e2d197b60dd7cac3b4a473f2f96bebfb0bcd77d73c0bbbbda95b8b0afb2c7f7` | `47cf6765aa47a02fa70c21611496a6a08872c8f0d2cda56928441f8ceada0e4f` | after Right interval |
| 1190 | `bccc321713ffe4f4f7b567ad8aebf9c74a9f11d9070a21fbc4e9d30595f03b41` | `26aa7c967be2cd8ab72219be64dfad96db296802d92873943f5bc5c32cdebaa8` | after B+Right run interval |
| 1590 | `e8a03834c1a7a202dbdb63e50134a10a18e51043d1ffa6cd80462138fc792751` | `f7ab63c2e6dcd591c65cbba264dfbbd9514550236cb19984c668c0219647963b` | settled repeat-comparison endpoint |

Each frame-1,590 hash is exact across the first and repeat recording of its
own case.

## Reproduction

All generated ROMs, manifests, saves, movies, videos, logs, states, and PNGs
must remain below ignored `private/` paths. Use same-stem disposable content;
never run against or overwrite the pinned source ROM or a recovered save.

From the repository root, create the private roots, reproduce the hardened
diagnostic, and make the exact disposable content/SRAM copies. The four SRM
copies are inspector references only: the emulator commands below use
`noload-nosave`, so none is loaded or saved by RetroArch.

```powershell
$testRoot = 'private/test_runs/schala_vanilla_npc_supported_slot_smoke_v0'
$runRoot = "$testRoot/reproduction_current_bsnes_v022"
$buildRoot = "$runRoot/build"
$stateRoot = "$runRoot/states"
$saveRoot = "$runRoot/saves"
$cleanSource = 'private/input/rom_archive/Chrono Trigger (USA).sfc'
$srmSource = 'private/input/lavos_save/chrono_trigger.srm'
$providerFirst = "$buildRoot/schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.sfc"

if (Test-Path -LiteralPath $runRoot) {
  throw "Refusing to reuse reproduction root: $runRoot"
}
New-Item -ItemType Directory -Force -Path $runRoot, $buildRoot, $stateRoot, $saveRoot | Out-Null

py -3 tools/build_schala_vanilla_npc_supported_slot_smoke_v0.py `
  --rom $cleanSource `
  --output $providerFirst

if ((Get-FileHash -Algorithm SHA256 -LiteralPath $providerFirst).Hash.ToLowerInvariant() -ne
    '75dc966ce377accf19ce1a7eb2ac200d5f68fbb94b9436eee7f09e613cc4ad42') {
  throw 'Hardened diagnostic ROM hash mismatch.'
}

Copy-Item -LiteralPath $cleanSource -Destination "$runRoot/title_seed_clean.sfc"
Copy-Item -LiteralPath $cleanSource -Destination "$runRoot/clean_control_run.sfc"
Copy-Item -LiteralPath $cleanSource -Destination "$runRoot/clean_repeat2.sfc"
Copy-Item -LiteralPath $providerFirst -Destination "$runRoot/provider_repeat2.sfc"

foreach ($stem in @(
  'schala_vanilla_npc_lucca_slot_smoke_v0_full_provider',
  'provider_repeat2',
  'clean_control_run',
  'clean_repeat2'
)) {
  Copy-Item -LiteralPath $srmSource -Destination "$saveRoot/$stem.srm"
}

py -3 -m unittest `
  tests.test_schala_vanilla_npc_supported_slot_smoke_v0 `
  tests.test_rom_write_intent_guard -v
```

The accepted `autostate-title.cfg` was these exact four LF-terminated UTF-8
lines. It is 215 bytes with SHA-256
`51e7c109cc8a7d22f489b828356918fe1a652b9216d9a6d45fdd77fc87c041a1`:

```text
savestate_auto_load = "false"
savestate_auto_save = "true"
savestate_thumbnail_enable = "false"
savestate_directory = "private\test_runs\schala_vanilla_npc_supported_slot_smoke_v0\current_core_full_provider\states"
```

For a safe rerun, create the same four-setting contract under the isolated
reproduction root. Only the state-directory value changes, so this new config
is not represented as the byte-identical accepted config:

```powershell
$autoConfig = "$runRoot/autostate-title.cfg"
$stateConfigPath = $stateRoot.Replace('/', '\')
$autoConfigLines = @(
  'savestate_auto_load = "false"',
  'savestate_auto_save = "true"',
  'savestate_thumbnail_enable = "false"',
  "savestate_directory = `"$stateConfigPath`""
)
[IO.File]::WriteAllText(
  $autoConfig,
  (($autoConfigLines -join "`n") + "`n"),
  [Text.UTF8Encoding]::new($false)
)
```

Capture the title RASTATE from the clean-ROM zero-input carrier, stopping at
frame 1,750 and enabling only the local auto-state override:

```powershell
$retroarch = 'private/tools/RetroArch-1.22.2-ProjectEpoch-current-20260822/retroarch.exe'
$core = 'private/tools/RetroArch-1.22.2-ProjectEpoch-current-20260822/cores/bsnes_libretro.dll'
$baseConfig = 'private/test_runs/retroarch/current/retroarch-current-null.cfg'
$zeroMovie = 'private/test_runs/retroarch/current/boot_zero_3600.bsv'

& $retroarch `
  -c $baseConfig `
  --appendconfig $autoConfig `
  -L $core `
  -P $zeroMovie `
  --sram-mode=noload-nosave `
  --max-frames=1750 `
  --verbose `
  --log-file "$runRoot/title_seed.log" `
  "$runRoot/title_seed_clean.sfc"
```

Replace the carrier state, inject the protected-range canary, and produce one
CRC-bound movie for each ROM:

```powershell
py -3 tools/edit_retroarch_bsv2_inputs.py `
  $zeroMovie `
  "$runRoot/title_raw_base.bsv" `
  --initial-rastate "$stateRoot/title_seed_clean.state.auto"

py -3 tools/inject_bsv2_wram_canary.py `
  "$runRoot/title_raw_base.bsv" `
  --pinned-current-layout `
  -o "$runRoot/title_raw_canary_clean.bsv"

py -3 tools/rebind_retroarch_bsv2_content_crc.py `
  "$runRoot/title_raw_canary_clean.bsv" `
  $providerFirst `
  --expected-source-rom "$runRoot/title_seed_clean.sfc" `
  -o "$runRoot/title_raw_canary_provider.bsv"

py -3 tools/rebind_retroarch_bsv2_content_crc.py `
  "$runRoot/title_raw_canary_clean.bsv" `
  "$runRoot/clean_control_run.sfc" `
  --expected-source-rom "$runRoot/title_seed_clean.sfc" `
  -o "$runRoot/title_raw_canary_clean_crc.bsv"
```

Add the exact matched input schedule:

```powershell
$presses = @(
  '--press', '60:left:2',
  '--press', '210:a:10',
  '--press', '650:up:60',
  '--press', '770:down:60',
  '--press', '890:left:60',
  '--press', '1010:right:60',
  '--press', '1130:b:60',
  '--press', '1130:right:60'
)

py -3 tools/edit_retroarch_bsv2_inputs.py `
  "$runRoot/title_raw_canary_provider.bsv" `
  "$runRoot/provider_motion.bsv" `
  @presses

py -3 tools/edit_retroarch_bsv2_inputs.py `
  "$runRoot/title_raw_canary_clean_crc.bsv" `
  "$runRoot/clean_motion.bsv" `
  @presses
```

The exact reproduction content/movie/receipt/state mapping is:

| Case | Content ROM | Input movie | Video and log stem | Automatic state |
| --- | --- | --- | --- | --- |
| provider, first | `$buildRoot/schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.sfc` | `$runRoot/provider_motion.bsv` | `$runRoot/provider_motion` | `$stateRoot/schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.state.auto` |
| provider, repeat | `$runRoot/provider_repeat2.sfc` | `$runRoot/provider_motion.bsv` | `$runRoot/provider_repeat2` | `$stateRoot/provider_repeat2.state.auto` |
| clean, first | `$runRoot/clean_control_run.sfc` | `$runRoot/clean_motion.bsv` | `$runRoot/clean_motion_r2` | `$stateRoot/clean_control_run.state.auto` |
| clean, repeat | `$runRoot/clean_repeat2.sfc` | `$runRoot/clean_motion.bsv` | `$runRoot/clean_repeat2` | `$stateRoot/clean_repeat2.state.auto` |

Run all four cases independently with those exact mappings. RetroArch derives
the state stem from the content basename, not the video/log stem:

```powershell
$runs = @(
  [pscustomobject]@{
    Content = $providerFirst
    Movie = "$runRoot/provider_motion.bsv"
    Receipt = "$runRoot/provider_motion"
  },
  [pscustomobject]@{
    Content = "$runRoot/provider_repeat2.sfc"
    Movie = "$runRoot/provider_motion.bsv"
    Receipt = "$runRoot/provider_repeat2"
  },
  [pscustomobject]@{
    Content = "$runRoot/clean_control_run.sfc"
    Movie = "$runRoot/clean_motion.bsv"
    Receipt = "$runRoot/clean_motion_r2"
  },
  [pscustomobject]@{
    Content = "$runRoot/clean_repeat2.sfc"
    Movie = "$runRoot/clean_motion.bsv"
    Receipt = "$runRoot/clean_repeat2"
  }
)

foreach ($run in $runs) {
  & $retroarch `
    -c $baseConfig `
    --appendconfig $autoConfig `
    -L $core `
    -P $run.Movie `
    -r "$($run.Receipt).mkv" `
    --sram-mode=noload-nosave `
    --max-frames=1600 `
    --verbose `
    --log-file "$($run.Receipt).log" `
    $run.Content
  if ($LASTEXITCODE -ne 0) { throw "RetroArch failed for $($run.Receipt)." }
}
```

Inspect all four endpoint states against their exact same-stem disposable SRM
references:

```powershell
$endpoints = @(
  [pscustomobject]@{
    Stem = 'schala_vanilla_npc_lucca_slot_smoke_v0_full_provider'
    State = "$stateRoot/schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.state.auto"
  },
  [pscustomobject]@{
    Stem = 'provider_repeat2'
    State = "$stateRoot/provider_repeat2.state.auto"
  },
  [pscustomobject]@{
    Stem = 'clean_control_run'
    State = "$stateRoot/clean_control_run.state.auto"
  },
  [pscustomobject]@{
    Stem = 'clean_repeat2'
    State = "$stateRoot/clean_repeat2.state.auto"
  }
)

foreach ($endpoint in $endpoints) {
  py -3 tools/inspect_current_wram_candidate.py `
    --srm "$saveRoot/$($endpoint.Stem).srm" `
    --slot 1 `
    --require-canary `
    $endpoint.State
  if ($LASTEXITCODE -ne 0) { throw "State inspection failed for $($endpoint.Stem)." }
}
```

The exact four-run hashes above are the acceptance authority. A later replay
is a new run and must receive its own receipts rather than inheriting this
status from a matching command line.

## Rejected artifact

An initial clean-control launch used an incorrectly constructed content path.
RetroArch failed to deserialize/load that movie. The 1,601-byte
`clean_motion.mkv` and its corresponding `clean_motion.log` are retained only
as ignored diagnostic history and are not accepted evidence. The valid clean
control is `clean_motion_r2.mkv` with the hash in the accepted table.

## Explicit nonclaims and remaining gates

- This is not logical PC `$07`, Schala recruitment, an eighth roster member,
  or an eighth saved character record.
- This does not approve `$7E2CA0-$7E2CEF` as free WRAM. It is one bounded
  field-path canary result; the remaining menu, battle, save, New Game+,
  attract, and reset matrix still governs that candidate.
- This is not a production ROM, patch, hook, allocation, graphics-bank
  adapter, or expanded-ROM read.
- This does not prove animation semantics for the nine source entrypoints or
  runtime execution of every `$00-$46` selector. The fallback is a private
  diagnostic safety measure only.
- This tests the vanilla field loader's twelve character-specific colors.
  Schala's indices 13-15 remain absent and still require the uninstalled full-
  palette adapter for the original fifteen-color artwork.
- This does not exercise battle graphics, battle DMA, attacks, casting,
  damage, victory, death, overworld, menu walking, portrait, status page,
  party exchange, save preview, Tech, item, or equipment paths.
- `noload-nosave` isolation proves no persistence behavior. Save, load,
  New Game+, erase, sidecar binding, and migration remain separate gates.
- The canonical Schala NPC-derived payload, ROMs, states, videos, and frames
  remain private copyrighted diagnostic material. Their hashes and metadata
  may be tracked; their bytes may not be committed or redistributed.
- This provider does not supersede or license the original Project Epoch art.
  It is a first-pass compatibility source pending a deliberate Chrono
  Trigger-style replacement-art redraw.

See [Schala vanilla-NPC source compatibility v0](schala_vanilla_npc_source_compatibility_v0.md)
for the static source chain and [the current replay harness](current_emulator_replay_harness_2026-07-26.md)
for the BSV2 and current-core state format boundaries.
