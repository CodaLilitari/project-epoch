# V4 ROM/NMI continuation receipt

**Historical paused receipt, superseded by the completed corrected pair.**
After the user extended the work session, `sampledwitness1` and
`sampledwitness2` each passed all 152 cases with identical traces. Current
results and exact identities are in the [final report](schala_package_helper_v4_rom_nmi.md)
and [acceptance reference](../references/schala_package_helper_v4_rom_nmi.json).
The text below remains the historical state at the pause. Its original
7,829-byte file is preserved under ignored
`private/test_runs/package_helper_v4_rom_nmi_20260908_paused_receipt_history/`
with SHA-256
`cbaab3cd8b762e7eabf330f97d37e892b91b6bd63325a38ca280805bad7b1711`.

Written 2026-09-08 during the authorized six-hour work session. This is a
human-readable recovery receipt for the separately owned v4 experiment.
It does not supersede the original design, accepted calibration or earlier
v2/v3 evidence. No Git action was performed by this subtask.

## Current state

The original-cartridge helper/NMI matrix is **not accepted yet**. One
two-case calibrated pilot passed. The first 152-case native matrix completed
all records but its host validator rejected four sampled initialization-clear
intervals. A separately numbered, narrowly checked correction is prepared
with 81 native-envelope/source tests and eleven metadata tests passing.
There is no new native run under that corrected source revision and no
accepted v4 reference. The metadata collector deliberately has empty native
acceptance constants.

The coordinating root review session and another review agent reported
`Error running remote compact task: Connection failed: error sending request`
when team status was checked after the new source review request. New
emulator launches remain paused pending that required review/authorization.
The completed calibration author was resumed to independently review the
new source and rejected trace offline. This connection failure is a workflow
blocker; it is not a native emulator, helper or cartridge failure.

## Frozen native source proposed for the next review

The protocol is `project-epoch-package-helper-v4-rom-nmi-calibrated-v3`.

| File | SHA-256 |
| --- | --- |
| `tools/run_schala_package_helper_v4_rom_nmi.py` | `11de12477a82059dcd50d714dfd8b3ca20fdf7de3b7befe4d9e0cb5ea63289f9` |
| `tools/mesen_schala_package_helper_v4_rom_nmi.lua` | `0db3a1c287bc1118f326643c318e7bee899cc5b191aa55325fae202366d0d1ff` |
| `tests/test_schala_package_helper_v4_rom_nmi.py` | `48f4d95aae835c9e65fe580c4b16ee74d5ce9594cac4281698bbb1f91e85b8e1` |
| `docs/schala_package_helper_v4_rom_nmi_phase_extension.md` | `8eeab277bad8da9a2fe8e599c7fbb1ea32841565599a4512099873cf70fd48fb` |

The original cartridge and 577-byte ROM helper remain unchanged. The
accepted timing-calibration reference remains pinned to
`8efb143221fa29fbd7e1e06ff077d1675050bc618cd08664270ff913d334dbfb`.
Its metadata collector revalidates both full 22-group runs. Current v4
launch staging guards 52 named files and archives exactly 45 source/reference
files. The original code, package and registry remain at `$410000`, `$420000`
and `$430000`; the actual native handler/vector remain `$008080`/`$00FFEA`.

The correction retains the general 32-clock first-pending-to-first-clear
sample limit. Exactly 38 clocks is allowed only for a complete original
`STA $7E5DBD,X` at `$4101DF` followed by `LDA $05,S` at `$4101E3`: preceding
execution, low/high publication writes, next execution and first stack read.
Exact CPU states, opcode bytes/PCs/ordinals, physical addresses, accumulator
bytes, +40/+8/+0/+30 master-clock and +5/+1/+0/+4 CPU-cycle differences are
required. Source explains initialization clearing before the unretained
opcode fetch; the next retained data read occurs later. This does not claim
38 clocks of actual pending DMA or widen the general timeout.

## Preserved attempts

All directories below are ignored under `private/test_runs/`.

| Run suffix after `package_helper_v4_rom_nmi_20260908_` | State | Trace SHA-256 |
| --- | --- | --- |
| `pilot1` | 2 native records completed; inherited whole-fixture VBlank condition rejected post-RTI raster wrap | `5344fbd723568a078b8e2233f77bfb11a31930fd2079a17a071cb455fe5b5a2a` |
| `pilot2` | 2 calibrated records passed; original cold boot/idle, native NMI and full ledger independently reviewed | `f61cad80bb75e209568415828df683e5cff2e97c2f373390aeac6ce4b853ffa9` |
| `final1` | 152 native records completed; 148 passed and 4 rejected the old 32-clock sampled-clear bound | `69f2173421da9d5d0dada58e096b8937fbb6819f3ac6b95f656997f10895b061` |

`pilot2/manifest.json` is SHA-256
`bdfd55bc6c78f2c75fd0efd45300b923eebc11e899ffe5ba6a1380099b00c631`.
`final1/host_rejection.json` is SHA-256
`71d6d469963f43aa1ab00a2cdfc03ae6a7d664aa7b7b340d1ca2ed758c2eb45c`.
The rejected full trace is 217,544,660 bytes, with `error:null` and no partial
events. Its four affected cases are selector `$80`, branch `$40`, SP `$1FEF`,
first-JSR NMI boundary, incoming statuses `$00/$C3/$4C/$8F`.

The corrected validator passes all 152 old records in an exploratory offline
revalidation. That does not change the old run's protocol, source archive,
trace, rejection or evidence status. Neither rejected run has an acceptance
manifest. Historical archives retain exactly 30/41/41 files respectively.

Independent peer review reproduced the old validator's exact four failures,
ran all 81 native-envelope tests, revalidated all 152 records through the new
validator and checked the pinned CPU/DMA/9F/A3 source derivation. It reported
no blocking defect in the narrow witness. A final provenance-only delta adds
the exact script/debugger callback source pins and citations; no acceptance
logic or emulator instruction changed. Root's changed-source launch review
remains pending after the connection failure.

The peer then reviewed that final provenance delta and the bounded metadata
read change, verified the final hashes, reran all 92 combined tests, and
revalidated historical inventories 30/41/41 plus all 18 source spans. It
reported no blocking finding. No changed-source native run was launched by
either author or reviewer.

## Next actions after independent review

1. Verify the four proposed native source identities above, review the narrow
   source-derived sampled-clear witness, and run the 81 native-envelope plus
   eleven metadata tests. Record independent review before a new native launch.
2. If approved, run two fresh 152-case matrices with identical frozen sources,
   distinct new directories and repetitions 1/2. Never reuse rejected
   `final1`. Preserve and report any new rejection before changing source.
3. Only after both pass, populate `RUNS`, `TRACE_SHA256`, `TESTS_SHA256` and
   `HOST_TEST_COUNT` in the separately authored
   `tools/collect_schala_package_helper_v4_rom_nmi_evidence.py`. The planned
   report is `docs/schala_package_helper_v4_rom_nmi.md`; it currently says
   pending and needs actual paired results.
4. Revalidate all actual native events/complete WRAM ledgers before the
   unchanged normal-v3 projections; compare the exact pair, current/prepared/
   staged/archive identities, direct staged input reconstruction and preserved
   history. Regenerate the public metadata reference byte-exact with LF.
5. Obtain final independent evidence review, then let root update the shared
   developer log/AGENTS/milestone and GitHub. Raw traces, ROMs, SRAM and native
   executables remain private. No production hook or PC-$07 claim follows.

The bounded host checks are:

```powershell
python -m unittest discover -s tests -p test_schala_package_helper_v4_rom_nmi.py
python -m unittest discover -s tests -p test_schala_package_helper_v4_rom_nmi_evidence.py
```

The draft metadata already rejects empty/missing/extra historical archives,
requires exact prepared source/archive hashes, rederives LF `inputs.lua`,
checks stem-matched zero 8192-byte SRAM and source-to-staged identity, and
rechecks current source, its own file, report and metadata tests after full
collection. Its final constants remain deliberately unpopulated.
The metadata JSON reader also bounds each buffered read to that file's checked
extent within the declared ceiling. This avoids reserving the full 1-GiB
trace allowance while reading a small receipt; the earlier draft hit a
`MemoryError` on that unnecessary allocation. Two added host tests cover the
small-read extent and preservation of the explicit maximum-size refusal.
