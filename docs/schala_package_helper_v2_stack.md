# Original package helper v2: stack-owned temporary state

Date: 2026-09-08. Subgate: `BA-NATIVE-STACK-FRAME-CONFORMANCE`, within
`BA-NATIVE-INTEGRATION-DESIGN`. This separately versioned implementation follows
[the reviewed stack-frame design](schala_package_stack_frame_design_v2.md).

Status: `verified-runtime` for the original synthetic normal-call contract.
Two fresh, isolated, source-matched runs passed all 2,980 cases each. Their
complete 70,196,608-byte traces are byte-identical, SHA-256
`41931d1424daf97d633aa446c4c964e3aa3fecedb6b62ea494400c0161071a9f`.
The accepted pair has 5,960 cases in total; each run has 1,426 successful
transports, 1,158 refusals and 396 canonical paths. Independent review covered
the assembly, instruction-owned SP/access evidence, and complete final-write
ledger. Forty-eight original host tests pass.

The [metadata reference](../references/schala_package_helper_v2_stack.json)
retains the accepted pair, source/runtime/input identities, full private
artifact manifests, preserved exploratory history and previous source versions.
Its [read-only evidence collector](../tools/collect_schala_package_helper_v2_stack_evidence.py)
revalidates both complete native traces and regenerates the metadata without
launching another emulator. Real game stack ownership and interrupts remain
separate gates.

## What changed

The v1 helper stored 42 temporary bytes in synthetic global WRAM. V2 stores
those bytes in its own stack frame, with native unsigned `d,S` addressing.
D remains unchanged. Existing registry, immutable ROM-source reads, pointer
preflight, canonical bypass, and publication addresses retain their v1 roles.
The frozen v0 and v1 assembly, tests, traces and references are preserved.

The stack geometry is explicit. After eight bytes of `PHP/PHA/PHX/PHY/PHB`
saves, the high path clears decimal mode, checks the floor, and reserves
`$2A` bytes. Relative to the resulting S, local bytes occupy `$01-$2A`;
saved DBR, Y, X, A and P begin at `$2B/$2C/$2E/$30/$32`. The body uses
50 bytes including saves; `CountBits` adds a two-byte near-call return,
for a maximum of 52 bytes below entry S. That routine makes no local-frame
access while its return address changes S. The single-byte source-bank
PHA/PLB pair likewise makes no local-frame access between its push and pull.

Successful final X, Y, A and P values are staged into their saved slots before
releasing the locals. Framed refusal releases exactly 42 bytes; early refusal
and canonical bypass restore only the original eight saved bytes. Clearing the decimal flag
before the subtraction and retaining binary arithmetic through release are
necessary because the fixture deliberately includes incoming decimal status.
The direct-page register remains `$0000` throughout the helper.

The native floor check occurs after the initial eight saves. It accepts entry
SP `$0034`, whose deepest helper S is `$0000`, and refuses high paths at
`$0033` and `$0008` before local allocation or ROM reads. The caller must
already guarantee writable memory for the initial saves and its pre-existing
frame. The launcher enforces a finite set of synthetic stack placements;
this check does not rescue an arbitrary invalid incoming stack.

## Immutable carrier and retained namespaces

The carrier remains the unchanged original eight-MiB SHA benchmark, SHA-256
`e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd`.
Its bytes are original diagnostic code/data, with no Chrono Trigger content.
The descriptor-shaped byte spans, complete bank words `$0041/$0042`, sixteen
registry records, and per-selector target arrays are exactly the fixture
identities described in [the frozen v1 report](schala_package_helper_v1_rom_source.md).
The pointed bytes are neither read nor executed as streams.

The helper executes at synthetic WRAM `$7F8000`; setup uses the separate
four-byte JML bridge at `$7FF100` so that Mesen observes the first helper PHP.
The bridge's redirected setup instruction itself is not part of the observed
helper interval. Exact terminal observation addresses remain `$7FF000`,
`$7FF010`, and `$7FF020`; their STP instructions are not executed.
No ROM image is written, no patch is emitted, and no production catalog changes.

## Normal conformance matrix and evidence contract

The 1,454 v1 cases run at each of synthetic SP `$1FEF` and `$06D8`. The latter
is numerically equal to one observed vanilla checkpoint entry; this test still
uses original synthetic memory and is not an execution of the game resolver.
An additional 72 cases exercise `$0034/$0033/$0008`, six canonical/primary/
alternate/unbound/wide-input routes, and four native status patterns, for
2,980 cases in a full run.

Every case compares final A/X/Y/P/DBR/D/SP, exact ordered owner-publication
bytes, exact ordered CPU ROM reads, complete WRAM differences, and unchanged
registry/target snapshots. The complete WRAM diff permits only the declared
per-case stack interval and existing publication outputs. Its exact ordered
byte list must also equal the final observed CPU write at every changed address,
compared with the known setup baseline. This includes every stack byte and
refuses unexplained changes even inside the maximum frame span. All 128 bytes at
retired global scratch `$7E4000-$7E4080` must remain `$A5`; data-read guards
also reject accesses to that span. Snapshot/setup reads are debugger actions,
separate from the observed native CPU callback interval.

The strengthened collector retains every observed helper PC and the exact
terminal tail. It refuses execution outside the assembled helper span and
those tails. This is a complete execution-span guard, not an independently
disassembled instruction-start allowlist.

Each stack access records its owning execution ordinal, physical WRAM address,
byte value, live SP and read/write mode. The offline validator derives its
owning opcode from the exact assembled bytes and retained PC sequence.
A stack-relative access must lie strictly above live S, match the instruction's
unsigned operand one-or-two-byte address span, and use the opcode's read/write mode.
This is an operand-ownership and liveness check; it does not independently
emulate each instruction's M-state byte width.
Push/pull/call/return accesses may equal the callback's current S because
Mesen observes those operations at different points in their SP update.
Access ownership must be monotonic and cannot refer to a terminal observation.

SP observations record execution ordinal, PC and SP after every executed
SP-changing instruction. The validator reconstructs the complete required
observation sequence from the retained PCs and assembled opcode bytes, refusing
missing, shifted, duplicated or extra observations. It also checks the exact
route-specific minimum: 8 bytes for unframed paths, 50 for framed refusals
before descriptor reads, and 52 after `CountBits` is reached. These checks
prevent a lone minimum-SP snapshot from standing in for complete observations.

## Preserved exploratory history

- `package_helper_v2_stack_20260908_explore1`: 130 native cases passed before
  the collector added post-instruction SP observations. This is a limited
  exploratory subset, not the final evidence source.
- `package_helper_v2_stack_20260908_explore2`: the full attempt exceeded its
  240-second finite emulator bound. Its prepared inputs, isolated stage and
  process log remain preserved. The then in-memory collector did not finish
  a trace. This was a collector/run-bound failure, not a successful full run.
- `package_helper_v2_stack_20260908_explore3`: all 2,980 cases passed with a
  streaming collector and 900-second finite bound. Independent review then
  demonstrated that removing most SP metadata could still pass its offline
  validator, and stack accesses lacked owning instruction ordinals. The
  assembly had no discovered defect. The exact pre-hardening source bytes
  were preserved under `package_helper_v2_stack_20260908_before_exec_ownership_sources`.
- `package_helper_v2_stack_20260908_execownership1`: 130 fresh native cases
  passed after both instruction-ownership evidence gaps were closed; the
  full pair and final-write-ledger hardening followed separately.

- `package_helper_v2_stack_20260908_final1` and `final2`: two full 2,980-case
  runs produced byte-identical traces with complete instruction-owned stack
  evidence. During final report review, a further offline acceptance gap was
  identified: an unexplained final stack delta could hide inside the permitted
  frame span. Their exact source versions and artifacts remain preserved under
  `package_helper_v2_stack_20260908_before_complete_diff_ledger_sources`.
  Every historical final1 record passes the stronger final-write-ledger check,
  but these runs retain their historical source revision.

- `package_helper_v2_stack_20260908_finalledger1` and `finalledger2`: the final
  accepted, source-matched pair. All 2,980 cases pass in each, under the stronger
  byte-ledger validator; their complete traces are byte-identical. These runs
  were required after that validator source change and new failing metadata
  boundary. The assembly and Lua observer remained unchanged.

Forty-eight original host tests cover the frame policy and adversarial evidence
rejections, including omission of a nonminimum SP observation, retaining only
the minimum, shifted/extra observations, wrong instruction ownership, and a
local read at unallocated S. Four further tests reject unexplained stack
differences, changed unvisited call-depth bytes, incorrect final values, and
omitted required stack changes. The validator-only opcode specimen in those tests
is original synthetic metadata, not a claimed emulator trace.

## Exact normal-run observations

Each accepted run retains 2,140,126 execution PCs: 2,137,146 helper instruction
observations and 2,980 terminal observations whose STP is not executed. It also
retains 1,096,204 instruction-owned stack accesses and 43,656 mandatory
post-SP-change observations. The exact source-read sequence has 53,748 ROM
byte reads; 1,095,290 total CPU data reads pass the finite read contract.

| Synthetic entry SP | Cases per run | Lowest observed S | Meaning |
| --- | ---: | --- | --- |
| `$1FEF` | 1,454 | `$1FBB` | Full 52-byte helper depth |
| `$06D8` | 1,454 | `$06A4` | Same complete matrix at a second synthetic placement |
| `$0034` | 24 | `$0000` | Exact helper-only floor, with byte zero intact |
| `$0033` | 24 | `$002B` | High paths refuse before local allocation |
| `$0008` | 24 | `$0000` | Eight context saves only; no interrupt reserve |

For the two complete 1,454-case blocks, the final route, CPU state apart from
its explicitly different SP, ordered existing output writes, ROM reads and
immutable input snapshots match the frozen v1 native trace exactly. That
comparison hashes to
`47cd832dd4a0eaf9caf4bd623e0d2783abb832a0e106efa8aaabaf7af589245d`.
V1's source and accepted evidence remain unchanged; its reference still hashes
to `d8b9c9ea589e33517331e377c084c0fadf91a42f1e665f5adbfb9c7895931c92`.

The accepted source freeze is:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| [Original v2 assembly](../asm/schala_package_helper_v2_stack.asm) | 8,617 | `7ee849f04444567ae6a67f5642edc0ec0b7ef09f41c7ea5f2b1773e6373fdb5f` |
| [Launcher and validator](../tools/run_schala_package_helper_v2_stack.py) | 22,162 | `88214b069ef49c3e512e625640fd67aa39019441119e8306782f225b9e48c251` |
| [Lua observer](../tools/mesen_schala_package_helper_v2_stack.lua) | 11,656 | `1cbe17e731871f2a8bcfc940b5c503215c511d77b67e7acb7978cdfe2b6b26c3` |
| [48 host tests](../tests/test_schala_package_helper_v2_stack.py) | 11,104 | `3b71e286d694c3adee2b1ccce648b1f5475a8da85591a29d4a0c1dd63fbffedb` |

The assembled 577-byte helper hashes to
`77dc3224baaa93077218d43d64cbef10bb55494a37057c1a5bfcf0d8fd6758f8`.
The two final manifests hash to
`739690a870193684797c19c2800d7639b473f2a9554c237b587c16f0bee902e6`
and `eb305f20e70069429213e85df0fc5f625a766aae24ba6a06bbaa97ec7d7e0ad0`.
The repeated full case contract hashes to
`5c46bd0e5885a2a463f02399f6cd9879b13b2ab25d2af19d5c705b43d05e7d76`.

## Reproduction and remaining boundary

Use fresh ignored output directories:

```powershell
python -B -m unittest discover -s tests -p test_schala_package_helper_v2_stack.py -v
python -B tools/collect_schala_package_helper_v2_stack_evidence.py
python -B tools/run_schala_package_helper_v2_stack.py --output-dir private/test_runs/package_helper_v2_stack_NEW1 --repetition 1 --timeout 900
python -B tools/run_schala_package_helper_v2_stack.py --output-dir private/test_runs/package_helper_v2_stack_NEW2 --repetition 2 --timeout 900
```

The launcher pins the original carrier, Asar, Mesen executable/core and runtime,
stages fresh isolated profiles and zero SRAM, and records source/staged hashes
before and after execution. Completed records are streamed to the private trace;
a progress receipt is updated every 50 cases. The finite collection time is
instrumentation overhead and is not a gameplay timing benchmark.

IRQ/NMI sources are disabled during this normal matrix. The separately scoped
[original interrupt-fixture preparation](schala_package_helper_v2_stack_interrupt_preparation.md)
is a plan, not an interrupt result. Low stack-floor tests have no interrupt
reserve and must remain outside preemption experiments. Real game stack
ownership, full normal-NMI service closure, cancellation, immutable-ROM registry
certification, helper execution from ROM, named production placement, a guarded
game hook, complete authored command streams and logical PC `$07` remain open.
