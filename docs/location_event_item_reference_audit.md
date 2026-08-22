# Location-event item and absolute-memory reference audit

Status: complete for Chrono Trigger US Rev0  
Evidence: `verified-static`  
Date: 2026-07-27

## Decision

No valid canonical location-event script claims item IDs `$E8-$EE`.

The range may be upgraded from `hypothesis: unclaimed pending event-script
audit` to **`verified-static: unclaimed by canonical location events`**. This
does not make the bytes general free space and does not authorize installing
native item records. Project Epoch still requires the classification,
description, shop/menu, battle, equipment, visual, save, and New Game+
adapters in `docs/schala_item_namespace_architecture.md`.

## Canonical input

The scanner accepts only the headerless 4 MiB US Rev0 ROM:

- SHA-1:
  `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- SHA-256:
  `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`

No decompressed script, ROM byte range, save, or trace is written by the
source-controlled tool.

## Engine route proved

The byte-matched disassembly establishes this route:

1. The 512 location records begin at `$F6:0000`, are `$0E` bytes each, and
   carry a 16-bit event index at record offset `+$08`.
2. `$C0:56D4-$C0:5706` multiplies that index by three and reads the long
   packet pointer from `$FC:F9F0`.
3. `$C3:0557-$C3:08B2` decompresses the packet into `$7F:2000`.
4. `$C0:58DE-$C0:5AB6` walks object bytecode through the 256-entry dispatch
   table at `$C0:5D6E`.

The scanner implements both LZ widths, literal groups, copy groups, and
partial-group addenda. It then validates the object count and pointer table
and walks every contiguous object range with the command sizes implied by the
dispatch handlers. The five variable-width opcodes (`$2E`, `$4E`, `$88`,
`$F1`, and `$FF`) are decoded from their mode or length operands.

## Coverage

`tools/audit_location_event_items.py` examined:

- all 512 location records;
- all 513 pointer-table entries `$000-$200`;
- 497 event IDs referenced by the location table;
- 489 structurally valid referenced event IDs;
- 462 distinct valid compressed packets after pointer-alias deduplication;
- 145,615 commands in those distinct packets;
- 155,780 command instances when event-ID aliases are counted separately.

The 16 pointer-table IDs not selected by any location record were also
checked:

- `$04B-$051` all point to `$DB:7FF2`, a valid zero-length packet;
- `$066-$06E` all point to `$F6:FFFC`, which is not a valid compressed
  packet.

Eight location records also select non-script placeholders:

| Event IDs | Location IDs | Pointer | Structural result |
| --- | --- | --- | --- |
| `$0E7-$0EB` | `$1C0`, `$1C4-$1C7` | `$F9:AFE9` | first copy token reads before any output |
| `$140-$142` | `$1CD-$1CF` | `$FA:FAA0` | first copy token reads before any output |

These 24 entries are not partially parsed or silently ignored: the report
labels them as empty/non-packet pointer-table entries. They cannot contain
executable event commands under the canonical decompressor.

## Item-bearing operations

Static reconstruction identified every event opcode that carries or obtains
an item ID:

| Opcode | Meaning | Encoding |
| ---: | --- | --- |
| `$C7` | add item from script memory | indirect through `$7F:0200 + slot*2` |
| `$C9` | conditional inventory item check | fixed item operand |
| `$CA` | add item | fixed item operand |
| `$CB` | remove item | fixed item operand |
| `$D5` | equip item on PC | second fixed operand |
| `$D7` | get item quantity | first fixed operand |

Across the 462 distinct valid packets, the scanner found:

| Opcode | References | Distinct fixed IDs | Fixed range |
| ---: | ---: | ---: | --- |
| `$C7` | 25 | n/a | runtime-derived |
| `$C9` | 56 | 13 | `$BD-$E7` |
| `$CA` | 323 | 88 | `$06-$E3` |
| `$CB` | 88 | 24 | `$3D-$E7` |
| `$D5` | 6 | 2 | `$00-$3D` |
| `$D7` | 12 | 8 | `$D0-$E7` |

There are zero fixed operands in `$E8-$EE`.

All 25 `$C7` sites resolve without an unknown producer. Each source slot is
populated by opcode `$48` from one of these runtime addresses:

```text
$7E2677-$7E267A
$7E26C7-$7E26CA
$7E2717-$7E271A
$7E2767-$7E276A
$7E27B7-$7E27BA
```

Those are offsets `+$27-$2A` in five vanilla `$50`-byte PC records: the four
equipment fields. The sites are generic equipment-return/pass-through logic,
not encoded ownership of any particular high item ID. The audit reports them
separately as `runtime_equipment_passthrough`; none remains
`computed_unresolved`.

This distinction matters for Project Epoch: a future Schala item could flow
through a generic inventory transport only after Project Epoch places that
item in live equipment state. Such transport is compatibility behavior, not
a vanilla reference to or claim on `$E8-$EE`.

## Compatibility-block absolute-memory addendum

The same complete parser now inventories opcodes `$48-$4E`, which read, write,
or copy through explicit 24-bit addresses. Across the 462 unique valid
packets it finds 1,511 such commands. Exactly 12 overlap
`$7E:2830-$7E:287F`, all in event `$11C`, object `$09`, referenced only by
location `$1D1`:

| Operation | Event offsets | Vanilla fields |
| --- | --- | --- |
| write tech counts from script memory | `$05C0/$0609/$0652/$06B4` | `$2830/$2831/$2832/$2834` |
| read learned masks | `$05C5/$060E/$0657/$06B9` | `$2837/$2838/$2839/$283B` |
| write learned masks after the script's `$E0` OR | `$05CD/$0616/$065F/$06C1` | `$2837/$2838/$2839/$283B` |

The command offsets in this table use the event-data coordinate system after
the one-byte object count. The relocation report names these
`event_data_command_offset`; its `packet_opcode_offset`,
`packet_address_operand_offset`, and `changed_offsets` instead index the full
decompressed packet including that object-count byte.

This is a mandatory compatibility-relocation consumer. The corresponding
candidate fields are `$2CA0/$2CA1/$2CA2/$2CA4` and
`$2CA7/$2CA8/$2CA9/$2CAB`. Leaving the canonical operands unchanged after
using `$7E2830-$287F` as Schala's record would corrupt that record. A future
implementation must recompile this one packet with pinned translated
operands or prove an exact-address resolver; it must not globally reinterpret
arbitrary event memory.

The source audit now constructs that one decompressed-packet translation
entirely in memory and rejects any preimage drift. Event `$11C` is pinned to
SNES pointer `$FA:B19E` / file `$3AB19E`; its compressed packet is `$0776`
bytes and decompresses to `$0C6B` bytes. The transform:

- requires the exact 12 `(object, command offset, opcode, address, width)`
  tuples above;
- requires the complete `$0C6B`-byte decompressed packet SHA-256, so drift
  anywhere outside those tuples is rejected too;
- changes only the 24 low/high address-operand bytes needed for the exact
  `$0470` relocation delta;
- reparses the transformed packet and requires the 12 translated addresses;
- requires no remaining absolute-memory overlap with `$7E2830-$287F` and
  requires the destination `$7E2CA0-$2CEF` hit set to be exactly those 12
  translations; and
- preserves the decompressed packet length and every non-address byte.

The pinned decompressed source SHA-256 is
`31d5b222828eca6c1c91a309f1543a8fdccf2e2f5deea7a4074b7376eaa70d8a`;
the translated in-memory SHA-256 is
`8e2952bd5e8c25eaf0ad4244dece929b6f4fc1eea8317ea707fcd782c898e50b`.
These hashes and edit metadata are evidence, not distributed packet data.
Across all 1,511 canonical absolute-memory commands, the destination
`$7E2CA0-$2CEF` has zero pre-existing hits.
The tool does not recompress the packet, select ROM space, write an image, or
emit a patch. Production installation remains blocked on a named expanded
allocation and installed-path runtime proof; the volatile-WRAM execution below
does not satisfy that installation gate.

### Static invocation route and runtime gate

The packet has 21 objects. Spekkio is object `$0A`; its activation function
calls magic-grant object `$09`, function `$03`, at decompressed offset `$0948`.
The ordinary first-grant route sets storyline `$4C`, records three completed
laps in script byte `$0E` (physical WRAM `$7F021C`), then makes that call.
The grant sets storyline `$4D`.

Only active PCs whose bit in `$7F01E0` is clear are processed. Crono, Marle,
Lucca, and Frog account for the 12 compatibility accesses; Robo has flag and
presentation handling but no count/mask write. Since only three PCs can be
active, a complete runtime matrix needs at least two party compositions. A
controlled diagnostic may enter a talkable location-`$1D1` state, set
storyline `$4C`, set `$7F021C=03`, clear only the intended active-PC grant
bits, then press A. That is a diagnostic shortcut into the canonical call,
not a naturally reached save or recruitment proof.

An exhaustive local fixture scan found no checksum-valid ordinary-New-Game
save at storyline `$48-$4C` or location `$1D1`. The late-game End-of-Time
slot at location `$1D0` is suitable only for navigation calibration or as a
post-grant no-write control unless its live state is explicitly and
reproducibly prepared as a private diagnostic.

#### Controlled current-bsnes vanilla baseline

`verified-runtime` for the exact prepared routes below; no translated packet
was installed.

The private current-bsnes harness reached a talkable location-`$1D1`
checkpoint and used `tools/inject_spekkio_event11c_diagnostic.py` to prepare
two matched zero/canary profiles. The Magus/Robo/Frog profile preserves the
source save's active party `06 04 03`; the Crono/Marle/Lucca profile
synthetically supplies active bytes `00 01 02`. Both set only the bounded
story/lap/grant fields needed to enter the canonical object `$09` function
`$03` route.

The terminal results match the static prediction:

| Profile | Story | Tech counts `$2830-$2836` | Learned masks `$2837-$283D` | Remaining TP |
| --- | ---: | --- | --- | --- |
| Magus/Robo/Frog | `$4D` | `08 08 08 08 03 08 08` | seven `$FF` bytes | Frog `160` |
| Crono/Marle/Lucca | `$4D` | `03 03 03 08 08 08 08` | seven `$FF` bytes | Crono/Marle/Lucca `160/150/160` |

Both routes finish with magic flags `$5F`, Robo flags `$00`, and lap byte
`$03`. For each profile the fail-closed pair comparator finds exactly 80
differences, all at state offsets `20260..20339`, which map exactly to
`$7E2CA0-$2CEF`. Normalizing only that candidate span reproduces the zero
core hash. Both guards and the Epoch name remain exact, each pair's
screenshots are byte-identical, and all four disposable SRAMs remain
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

This proves the terminal behavior of the two vanilla branches containing the
12 statically identified operations. It does not prove that no transient
access occurred elsewhere, because this current-bsnes replay is endpoint
evidence rather than an instruction watchpoint trace.

#### Native Mesen instruction trace

`verified-runtime` for the exact unmodified vanilla instructions, targets,
values, and order below; the translated packet remains uninstalled.

A separate Mesen 2.1.1 test-runner route starts from a native private
location-`$1D1` checkpoint and prepares the same bounded two-profile state
directly in volatile WRAM. `tools/mesen_event11c_trace.lua` has no ROM or SRAM
write path; the disposable SRAM remains byte-exact at SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.
Its broad execution callback returns no replacement value and routes only
exact PCs `$C0:6797` (`LDA [$CD]`) and `$C0:6822`
(`STA [$D0]`). The collector resolves the live 24-bit pointer from direct page
`$0100`, samples reads before the load, and samples writes on the immediately
following instruction.

Each zero/canary pair repeats the same sequence. Collapsing the matched pairs,
the four accepted runs observe these 12 unique operations:

| Profile | Seq. | Relative frame | Access | Target | Value | PC |
| --- | ---: | ---: | --- | --- | ---: | --- |
| Crono/Marle/Lucca | 0 | 793 | write | `$7E2830` | `$03` | `$C0:6822` |
|  | 1 | 793 | read | `$7E2837` | `$1F` | `$C0:6797` |
|  | 2 | 793 | write | `$7E2837` | `$FF` | `$C0:6822` |
|  | 3 | 1086 | write | `$7E2831` | `$03` | `$C0:6822` |
|  | 4 | 1090 | read | `$7E2838` | `$1F` | `$C0:6797` |
|  | 5 | 1090 | write | `$7E2838` | `$FF` | `$C0:6822` |
|  | 6 | 1875 | write | `$7E2832` | `$03` | `$C0:6822` |
|  | 7 | 1879 | read | `$7E2839` | `$1F` | `$C0:6797` |
|  | 8 | 1879 | write | `$7E2839` | `$FF` | `$C0:6822` |
| Magus/Robo/Frog | 0 | 985 | write | `$7E2834` | `$03` | `$C0:6822` |
|  | 1 | 989 | read | `$7E283B` | `$1F` | `$C0:6797` |
|  | 2 | 989 | write | `$7E283B` | `$FF` | `$C0:6822` |

The zero and canary variants have byte-identical callback sequences for each
profile. All four terminate with collector success, no overflow, no unexpected
watched-handler access, storyline `$4D`, magic flags `$5F`, all learned masks
`$FF`, and the same terminal counts as the current-bsnes controls. The
candidate matches its prepared zero/canary value at both endpoints; both
guards and Epoch name `a4c9c8bcc100` remain exact. Pair screenshots are also
byte-identical.

The curated public hash contract is
`references/mesen_event11c_trace_accepted_artifacts_v1.json`; all traces,
screenshots, the native checkpoint, ROM, and accepted emulator runtime remain
under `private/`. The guarded reproduction entry point is
`tools/run_mesen_event11c_trace.py`; it stages an isolated emulator and
disposable matching ROM/SRAM pair before invoking the pinned collector. This
closes the transient instruction-level baseline for the 12
canonical old-block accesses. It does not prove the translated operands,
candidate ownership, or that no unrelated non-event code accesses either
WRAM range.

#### Native Mesen volatile relocated-packet trace

`verified-runtime` for the exact translated operands in the already-
decompressed `$7F2000-$7F2C6A` WRAM buffer; no ROM installation

`tools/mesen_event11c_relocated_trace.lua` adds a second fail-closed route. It
requires the entire live `$0C6B`-byte source packet before writing, verifies
all 12 sites and exactly 24 changed operand bytes, applies those bytes in
volatile WRAM, and requires the entire transformed packet both after
preparation and at termination. All of the collector's explicit `write8` and
`write16` calls target `snesWorkRam`. Before the grant profile is prepared, it
copies all `$50` bytes from `$7E2830-$287F` to `$7E2CA0-$2CEF`.

The first calibration used a canary across the entire old block and correctly
exposed normal equipped-rock recalculation at `$2857-$285B`. The accepted
matrix therefore limits its old zero/canary control to the event-target span
`$2830-$283B`, leaving the existing learned-mask/rock-flag tail untouched.
After preparation, every old-block byte must remain exact. Candidate changes
are limited to the predicted relocated count/mask fields; candidate non-target
bytes, both guards, and Epoch remain exact.

Every routed callback also binds the interpreter access to its source command:
CPU Y equals one of
`$05C0/$05C5/$05CD/$0609/$060E/$0616/$0652/$0657/$065F/$06B4/$06B9/$06C1`,
direct page is `$0100`, M is set, the live opcode/operand agrees with the
`$CD/$D0` pointer, and low A before each write equals the deferred stored byte.
The strict four-set validator proves source compatibility identity plus
zero/canary candidate and callback identity.

| Profile / variant | Trace bytes / SHA-256 | Endpoint PNG bytes / SHA-256 |
| --- | --- | --- |
| Magus/Robo/Frog zero | `5884` / `645f6f4c1ce5ffac18a3a3cb8caf8b5115303fa4a3a5f2b32a089f55e70306fe` | `9503` / `0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb` |
| Magus/Robo/Frog canary | `5886` / `27d1330a474391220b47a4a154d06e1ee6d416771456e94110d2332c82d1e7fe` | `9503` / `0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb` |
| Crono/Marle/Lucca zero | `7715` / `70006be6c842a940de366a9102c7ee80db1f8829f9078d3bf5369368a69f090b` | `10421` / `312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96` |
| Crono/Marle/Lucca canary | `7717` / `579fa7aaace23cbb1fdd1b0a040a00073552eafef2f8337ce4a616b3d644f595` | `10421` / `312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96` |

Exact image acceptance pins the field frame to zero modulo 16 and Spekkio's
sprite frame to 22 for Magus/Robo/Frog or 4 for Crono/Marle/Lucca. This is the
deterministic endpoint added after the exact PNG gate exposed adjacent
idle-frame variation.

The current accepted private root is
`private/test_runs/mesen2/event11c_relocated_accepted_hardened_v4`; a second
safe-launcher pass reproduced all hashes under
`private/test_runs/mesen2/event11c_relocated_launcher_replay_hardened_v4`. The
two four-trace sets pass the schema-v2/version-2 validator and are
byte-identical across all eight artifacts. The
8,934-byte current public acceptance contract is
`references/mesen_event11c_relocated_trace_accepted_artifacts_v3.json`,
SHA-256
`839b86310dbe33273cf14ffec01386aa4ee6b88426b100be2cdc65d17a0790cc`.
Acceptance v1 and v2 and their accepted/replay roots remain retained as
historical evidence. V2 mislabeled the incompatible hardened shape as
trace-v1/collector version 1. The current validator requires trace schema v2
and collector version 2 because the shape removed synthesized
`absolute_frame`, added phase fields, and narrowed the explicit-write scope.
The collector, validator, and launcher are pinned at
`35700` / `4413876f258c091a728a8d6d53e2aea824206c5e7f9852ca476b5ee5c974070c`,
`24820` / `2025a749fc3081ff7a6dfeb49b7b1c9aa6ae31241c4744be14c23d63e06de186`,
and
`43512` / `78371ecb3974046d170d6613239d08c3b7a56252681af0bb352dac12e4676b4c`
bytes / SHA-256, respectively.
The launcher exact-byte compiles and executes the pinned Python modules. It
reads and hashes the legacy launcher source for provenance without executing
it, stages the ROM, SRAM, emulator, verified collector/checkpoint, and
host-derived raw packets privately, then stages collector outputs before
publishing each trace/PNG pair with exclusive `xb` creation. Pair-publication
rollback is limited to files whose identities still match this invocation.
All staging and packet bytes are deleted; source ROM, SRAM, checkpoint, shared
saves, and staged inputs remain exact.

This closes only the volatile already-decompressed event-consumer gate. It is
not a claim that loading the checkpoint or executing the game leaves all
transient emulator state unchanged. It is not evidence for recompression, ROM
allocation, pointer installation, a hook, global candidate ownership, natural
PC `$07`, or save/load/New Game+ integration.

No absolute command, including an overlapping 16-bit or block-copy extent,
touches `$285C-$287F`. This is bounded negative event-script evidence, not a
claim that the tail is free or unused; initialization, save/load, New Game+,
and reset still move or clear it in bulk.

## Reproduction

Run:

```powershell
python tools\audit_location_event_items.py `
  "private\input\rom_archive\Chrono Trigger (USA).sfc"

python -m unittest tests.test_location_event_item_audit -v

python -m unittest tests.test_spekkio_event11c_diagnostic -v

python tools\compare_current_wram_canary_pair.py `
  <zero.state.auto> <canary.state.auto> `
  --srm <matching-disposable.srm> --slot 3

python tools\run_mesen_event11c_trace.py `
  --profile frog-robo `
  --variant zero `
  --output-dir private\test_runs\mesen2\<fresh-run>\frog-robo\zero

python tools\validate_mesen_event11c_trace.py `
  private\test_runs\mesen2\event11c_trace_accepted_v1\crono-marle-lucca\zero\trace.json `
  private\test_runs\mesen2\event11c_trace_accepted_v1\crono-marle-lucca\canary\trace.json `
  private\test_runs\mesen2\event11c_trace_accepted_v1\frog-robo\zero\trace.json `
  private\test_runs\mesen2\event11c_trace_accepted_v1\frog-robo\canary\trace.json

python tools\run_mesen_event11c_relocated_trace.py `
  --profile frog-robo `
  --variant zero `
  --output-dir private\test_runs\mesen2\<fresh-relocated-run>\frog-robo\zero

python tools\validate_mesen_event11c_relocated_trace.py `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\crono-marle-lucca\zero\trace.json `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\crono-marle-lucca\canary\trace.json `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\frog-robo\zero\trace.json `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\frog-robo\canary\trace.json

python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_spekkio_event11c_canary_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\spekkio_event11c_canary_manifest.json
```

Expected decision fields:

```text
candidate_fixed_hits: []
computed_unresolved: []
runtime_equipment_passthrough: 25 entries
candidate_range_unclaimed: true
absolute_memory_references.total: 1511
absolute_memory_references.compatibility_event_ids: [284]
absolute_memory_references.compatibility_location_ids: [465]
absolute_memory_references.tail_hits: []
absolute_memory_references.relocated_candidate_preexisting_hits: []
absolute_memory_references.relocation_plan.edit_count: 12
absolute_memory_references.relocation_plan.changed_byte_count: 24
```

Nine synthetic tests cover a full literal group, an addendum/partial
group, all six item-bearing opcodes, a constant-derived `$C7`, a recognized
equipment-field `$C7`, an unresolved non-equipment `$C7`, and complete
256-opcode size-table coverage, absolute read/write/copy extents, an exact
relocation, and a drifted-preimage rejection. A tenth canonical-ROM test pins
all 12 compatibility hits, the empty tail, packet identity, translated hash,
and exact relocation metadata.

As an independent private cross-check, the canonical run matched Temporal
Redux commit `365086c1c0a33144b24bff4933998bdff82c9940` for all 489 valid
event-ID decompressions and for every one of the 155,780 command-instance
lengths. Temporal Redux is not a build or audit dependency.

## Limits

- This is a static reference/ownership audit, not runtime proof of every
  story branch.
- It covers the canonical SNES US Rev0 location table and all of its pointer
  entries. It does not claim coverage for modified ROMs, battle-scene
  bytecode, overworld UI bytecode, or arbitrary hand-written expanded event
  packets.
- Generic memory-writing opcodes could mutate inventory WRAM directly in a
  future hack. No canonical script ownership is inferred from hypothetical
  post-patch behavior.
- The current-bsnes grant runs are explicitly prepared volatile-WRAM
  diagnostics, not naturally reached first-grant saves, normal progression,
  or recruitment proof.
- The original native Mesen runs individually trace the 12 unmodified
  old-block accesses. A separate accepted run validates the translated
  operands only after patching the already-decompressed live WRAM packet.
- No recompressed or ROM-installed translated packet was executed. The
  post-install route must still write the relocated compatibility fields while
  preserving a real Schala `$7E2830-$287F` record through the remaining
  lifecycle matrix.
- The result approves the candidate namespace only. The seven original
  Schala items must remain authoring-only until the item adapters and runtime
  test matrix pass.
