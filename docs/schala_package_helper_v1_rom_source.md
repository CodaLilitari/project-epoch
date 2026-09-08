# Original package helper v1: immutable expanded-ROM source proof

Date: 2026-09-08. Subgate: `BA-NATIVE-ROM-SOURCE-TRANSPORT`, within
`BA-NATIVE-INTEGRATION-DESIGN`. Evidence: `verified-runtime`, limited to the
original helper and unchanged synthetic ExHiROM carrier described here.
Production integration remains gated.

## Result and why this route was chosen

A separately versioned 676-byte original helper reads descriptor-shaped bytes
through the actual emulated SNES bus from ExHiROM banks `$41` and `$42`, then
publishes the selected direct offsets with their exact source bank. Two fresh
isolated Mesen 2.1.1 runs with a complete execution-span guard passed 1,454 cases each. Their complete raw traces are
byte-identical. Each run contains 709 successful transports, 553 refusals, and
192 canonical-path cases, including the repeated status-bit cases.

This closes a specific limitation of the completed v0 synthetic proof: v0
intentionally admitted only WRAM source banks `$7E/$7F`. Its source and three
accepted runs remain unchanged. The new source is
[`asm/schala_package_helper_v1_rom_source.asm`](../asm/schala_package_helper_v1_rom_source.asm).
It still executes from synthetic WRAM at `$7F8000`. Execution of helper code
from a production ROM allocation has not been demonstrated.

No ROM was mutated or rebuilt. The launcher accepts only the already-existing,
original eight-MiB SHA benchmark with SHA-256
`e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd`.
That carrier contains original diagnostic code and data, not Chrono Trigger
bytes. The proof deliberately interprets two fixed spans as descriptor-shaped
byte fixtures. It does not execute or certify the pointed bytes as battle
commands. This route avoids inventing an exception to the ROM write guard;
all trusted production hook and allocation catalogs remain empty.

## Exact fixture contract

All ranges in this document are half-open. Bank values below are complete
16-bit registry words, so `$0141` is distinct from accepted `$0041`.

| Original byte fixture | CPU/file span | Pointer occurrences | SHA-256 |
| --- | --- | --- | --- |
| SHA code interpreted only as descriptor-shaped data | `$410002-$410016` | 8 | `d6b8165c0913a74324c7d46b24330ddd7fbcd99cf05b12d2fabf9b82fe2b91e7` |
| SHA constants interpreted only as descriptor-shaped data | `$420000-$420020` | 14 | `04f93fd18db0bc237c01a03fe85c033f2c090085f0cd3d6301669ae4cc2bb8ab` |

The v1 source admits only bank words `$0041/$0042`. Every other low bank byte,
including `$7E/$7F`, is refused before any ROM-source read. Tests also cover
nonzero high bank bytes. Candidate production bank `$43` remains refused;
these fixture identities do not promote the earlier bank-`$43` proposal.

The synthetic registry is sixteen 16-byte records at `$7E3000-$7E3100`.
Each record consists of eight little-endian words:

| Offset | Field | Requirement |
| --- | --- | --- |
| `+0` | valid | Exactly one for a bound test entry; zero remains unbound. |
| `+2` | descriptor root | Header fits entirely in one physical source bank. |
| `+4` | source bank word | Exactly `$0041` or `$0042`. |
| `+6` | exact descriptor end, low word | Must equal the endpoint computed from both masks. |
| `+8` | exact descriptor end, carry word | Zero or one; one requires the low word to be zero. |
| `+A` | allowed target count | At most 32 words in that selector's fixed 64-byte array. |
| `+C`, `+E` | reserved | Both zero. |

The sixteen separate target arrays occupy `$7E3100-$7E3500`. Every pointer in
both descriptor branches must match an entry in the selected exact target
array before the first publication. `$FFFF` and descriptor/entry overlap are
refused independently of the allowlist. Repeated descriptor pointers remain
valid. A bad pointer in the unselected branch refuses the whole transport.
The declared descriptor endpoint prevents a changed mask from silently
extending the read extent beyond the fixture contract.

This allowlist supplies bounded transport identities. It is not a substitute
for the authored-package validator's decoded command grammar, token ownership,
shared/suffix-entry checks, strict decoded-`$1E` exclusion, disjoint named
allocations, or terminal-stream policy. A future ROM registry needs a builder
that binds its exact target sets to those certificates. This diagnostic does
not claim such a production registry or a valid playable action package.

The caller ABI remains native M=0/X=0, D=`$0000`, DBR=`$7E`, with `JML` tails
retaining the original incoming return frame. Canonical selectors bypass the
registry and branch-word checks, then reproduce the displaced `LDA/ASL`
result. Refusal restores the complete entry context and publishes nothing.
Success preserves the established v0 output contract and ordered word-write
footprints, including adjacent owner activation bytes. Refusal here means a
synthetic terminal result; it does not complete the real game's cancellation
lifecycle.

## What the collector actually observes

The original helper is assembled as a raw `norom` binary and injected only
into diagnostic WRAM. Each case begins from a complete known WRAM fill,
explicit input writes, eight-byte saved-context capacity plus the two-byte
local call frame, and isolated zero SRAM. The helper's synthetic scratch
remains `$7E4000-$7E4080`; this is the address already proved unsuitable as
unqualified game scratch. No ownership claim is added.

The collector uses Mesen's CPU `callbackType.read` callbacks on
`memType.snesMemory`, separately from instruction execution callbacks and
host/debugger memory inspection. A separate execution callback refuses every
observed PC outside the exact assembled helper span or three exact terminal
observation addresses. Every case retains its complete PC sequence, from the
first helper instruction to its matching terminal address. Offline validation
requires the exact entry and terminal, an instruction-count match, and every
intermediate PC inside the exact helper extent. Terminal STP instructions are
observation points; the collector switches cases before executing them.
This is an extent guard, not an independently disassembled instruction-start
guard.

Mesen's redirect behavior needs explicit treatment. A `setState` redirect made
inside an execution callback executes the selected first opcode without a
second callback. The harness therefore redirects first to a separate original
four-byte `JML` setup bridge at `$7FF100-$7FF104`. That setup instruction has no
helper-state side effects. Its destination is the exact assembled helper
entry, whose first `PHP` now receives its own callback. The unobserved setup
bridge is outside the complete observed helper interval. It is not a game hook
or a permitted execution destination inside that interval.

Each accepted run retains 1,049,158 observed PCs: 1,047,704 helper instruction
observations and 1,454 final terminal observations. The complete sequences
exclude every pointed stream and other ROM/WRAM execution address directly,
in addition to the frozen helper source's control-flow restrictions.

The data-read collector records every byte read from banks
`$41/$42`, including the exact address, value, and order. The expected trace
contains only both mask words, the complete pointer preflight, and the
selected pointer reread. No pointed stream is read or executed.

Every other CPU data read must lie in the exact synthetic registry, target,
input, scratch, or stack spans. An unrecognized bank or WRAM alias therefore
cannot silently provide source data. Each accepted run checks 543,631 CPU
data reads, including 26,690 exact ROM-source byte reads. Instruction-count
fields contain execution callback counts, including terminal observations;
they are not cycle or frame timing measurements.

The collector also captures every CPU write and compares the complete
128-KiB WRAM image against its pre-call baseline. The existing independent
v0 evidence validator checks final CPU registers/flags, the exact ordered
publication bytes, bounded stack and scratch writes, and all other WRAM
changes. The new validator additionally checks the ordered ROM reads and
complete before/after byte snapshots of the 1,280-byte registry/target region.
Those actual snapshots are compared to the authored input bytes, then hashed.
The registry and target bytes remain unchanged through every case.

ROM, zero SRAM, runtime files, collector, and source files are hash-checked
before and after execution. Staged copies are also compared with their source
hashes before launch. A prepared `launch_inputs.json` retains provenance if a
later run fails. Each launch has a new hidden process and isolated profile,
app/save directory, ROM basename, and temporary directories. Interrupt sources
are disabled under this synthetic harness; real NMI/IRQ ownership remains a
separate gate.

## Validation and reproducibility

The deterministic matrix covers all 128 canonical selectors, all 256 branch
bytes for each source bank, all 256 possible bank low bytes, nonzero bank high
bytes, all sixteen high-selector registry positions, reserved fields, target
count limits, wrong descriptor endpoints, physical-bank root limits, invalid
selected and unselected target sets, and all 64 native-width status values
across four routes. The existing v0 proof supplies its own larger family of
authored descriptor shapes; this new proof does not claim every owner bit or
every descriptor geometry through the two immutable ROM fixtures.

The 32 host tests include independent evidence rejection for changed CPU
status, wrong/missing/reordered ROM reads, wrong source bank, unexpected
writes, restored-but-still-forbidden input writes, altered full WRAM diffs,
changed input snapshots, forbidden execution spans, an early terminal,
a byte adjacent to a terminal, a wrong final tail, missing PC sequences,
an instruction-count mismatch, and a wrong entry. Their original host fixture also covers exact
`$10000` endpoint wrapping without pretending that this host-only geometry
was exercised in the two native ROM fixtures.

Reproduce host checks without any private ROM:

```powershell
python -B -m unittest discover -s tests -p test_schala_package_helper_v1_rom_source.py
```

Reproduce the native proof with the pinned existing carrier, Asar 1.91,
and Mesen 2.1.1 already present at the launcher's private paths. Each output
path must be new:

```powershell
python -B tools/run_schala_package_helper_v1_rom_source.py --output-dir private/test_runs/package_helper_v1_rom_source_NEW1 --repetition 1 --timeout 90
python -B tools/run_schala_package_helper_v1_rom_source.py --output-dir private/test_runs/package_helper_v1_rom_source_NEW2 --repetition 2 --timeout 90
```

| Accepted artifact | Exact identity |
| --- | --- |
| Helper source | `0a71029770a494707cc03eae6d80461de6de3a30544dc01cc632bf82d1079e9b` |
| Raw helper, 676 bytes at `$7F8000` | `9a8554aa0045163abcc15f021fb80dc6606f3d6ce444dea682ff04ec6cc46b63` |
| Launcher | `29d11882f02c74f4212bea0c964f208dbb1366b16fc688be96908c125fa740ff` |
| Collector | `3c4f7bfc994e583c3a1f258f8a24e48da762c524ab40a5c8669b43b67ba4d83c` |
| Both complete 1,454-case contracts | `4735df3a5b5c1ee1e6d6a76d842f88b25ebeaf4e1234ba3bff6a02ad7523dd48` |
| Both complete raw traces, 20,145,935 bytes each | `bb5a9f54a57fb59072f6b9011bc80c4ba761b13d820e9df5acaee44b1e5595c9` |
| Both before/after WRAM input hash tables | `65d0c3a398a79a667c3bc1c42074672a7d5bb480c283898ced8f002fead4556d` |

Accepted private directories are
`package_helper_v1_rom_source_20260908_execguard2` and
`package_helper_v1_rom_source_20260908_execguard3` below `private/test_runs/`.
The source-controlled
[`references/schala_package_helper_v1_rom_source.json`](../references/schala_package_helper_v1_rom_source.json)
contains exact source/runtime/artifact identities, each run's manifest and
route counts, reproduction commands, and the retained exploratory history.
Only metadata and original source are tracked. Raw binaries, traces, ROMs,
SRAM, emulator files, and intermediate stages remain private and ignored.

## Development history and limitations

The first 130-case exploratory run exposed a bug in this new v1 source: after
checking the declared end carry against two, the code used the comparison's
stale Z flag after a store. That made a valid zero carry follow the nonzero
path and reject nonzero low endpoints. An explicit `CMP #$0000` now establishes
the intended branch condition. The failed 673-byte binary and trace remain
preserved under `..._explore1`; they are not positive conformance evidence.
The corrected 676-byte subset passed under `..._explore2`.

A complete 1,454-case exploratory run, `..._explore3`, then passed with full
registry/target snapshots. The collector was subsequently strengthened to
bound every CPU data read, and the launcher gained a prepared provenance
record. The first prepared attempt, historically named `..._final1`, failed
before emulator launch because its metadata included a Python `WindowsPath`.
The metadata now serializes runtime sizes alongside the already recorded
hashes. That prepared-only directory is preserved and is not an accepted run.
Those initial paired runs, `..._final2` and `..._final3`, passed the prior
read/write/state contract using identical frozen source files. A subsequent
review identified that the no-stream-execution claim should be checked by the
runtime collector, not supported only by the frozen helper's geometry.

The complete-execution addition first produced `..._execguard1`. Its full
matrix passed the earlier data/state checks, but the new validator rejected
its sequences because they began after the first helper opcode. This exposed
the `setState` callback boundary described above. The original entry bridge
resolved that observation gap without changing the helper assembly or binary.
The definitive `..._execguard2` and `..._execguard3` pair now passes the stronger
contract with identical frozen sources and byte-identical full traces.

The exact earlier reference remains at
[`schala_package_helper_v1_rom_source_before_exec_guard.json`](../references/schala_package_helper_v1_rom_source_before_exec_guard.json),
SHA-256 `0494c43bab6358c395a1f05daefec8d17a277c14182c07f3d674338f62c849b4`.
The current reference retains its earlier runs and identities as historical
evidence rather than silently assigning them the stronger contract. Original
source versions are preserved privately; where source text was recovered by
reversing the small instrumentation edit, its exact bytes were checked against
the independently frozen pre-edit hash. The rejected pre-bridge run and source
version are also preserved. A separate exact comparison of the old and new
per-case CPU state, reads, writes, complete WRAM changes, and input snapshots
finds them unchanged; only the execution-observation instrumentation differs.
The shared projection hash is recorded in the current reference.

These are corrections to newly authored diagnostic code and tooling. They
contradict no earlier verified canonical Chrono Trigger data map. The v0
WRAM-bank restriction remains correct for that version; v1 is an additional
scoped implementation, not evidence that the old annotation was wrong.

The next integration work still needs an actual refusal lifecycle, immutable
named ROM registry/target certificates, guarded production code/data placement
including the separately proposed bank `$43`, real scratch/stack and interrupt
ownership, and a certified command stream that satisfies the caller's
completion latches. This result supplies no game hook, action completion,
animation, save behavior, Schala action binding, or logical PC `$07` runtime
claim.
