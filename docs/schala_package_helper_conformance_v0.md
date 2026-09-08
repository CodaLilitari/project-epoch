# Original package helper: native conformance v0

Gate: `BA-NATIVE-HELPER-CONFORMANCE`.
Status: `complete-native-synthetic`, 2026-09-08. Evidence level:
`verified-runtime`, scope `synthetic-only`.

This continues the completed source-only symbolic package and bank-qualified
descriptor model with original 65C816 instructions. It tests the helper in
Mesen's SNES CPU, using synthetic WRAM fixtures and an existing original
standalone benchmark cartridge. It does not execute Chrono Trigger, change a
cartridge image, install a game hook, or bind a production high selector.

## Scope and source contract

The relocatable include is `asm/schala_package_helper_v0.asm`. The caller
supplies a registry, scratch address, and three tail destinations. The v0
registry has sixteen six-byte entries: an exact validity word `$0001`, a
descriptor offset, and a bank word. All other validity words are unbound.
Only synthetic WRAM bank words `$007E` and `$007F` are accepted in this
conformance version. These are diagnostic identities, not approved game
allocations or the eventual ROM-bank policy.

Entry requires native mode, 16-bit A/X/Y, D=`$0000`, DBR=`$7E`, and the
selector word at `$7E9877`. The branch word at `$7EA0B3` must have a zero high
byte on the high path. Descriptor and direct-stream fixtures must remain
immutable and disjoint from the code, registry, scratch, stack, and input and
publication regions. The completed static stream-policy validator remains a
separate prerequisite: this helper validates descriptor bounds and pointers;
it does not reinterpret or certify a command stream.

The helper preserves the incoming context while deciding the route. It reads
both big-endian owner masks, counts both pointer lists, and validates every
pointer before publishing any output. It rejects a descriptor that extends
beyond its physical 64 KiB source bank, `$FFFF` direct pointers, and pointers
inside its own descriptor. An extent ending exactly at `$10000` is valid;
the physical end remains `$10000` in the host model while native X wraps to
`$0000`. A nonzero branch byte selects the second list.

| Route | Native result |
| --- | --- |
| Canonical selector `$00-$7F` | Restore the incoming context, replay `LDA $9877` / `ASL A`, and jump to the canonical tail. Do not consult the branch word or binding registry. A and N/Z/C reflect that replay; the other entry registers and status bits are preserved. |
| Bound high selector `$80-$8F` with valid inputs | Publish the root, masks, and selected owner entries; consume DP `$80` to zero and clear only the low branch byte. Exit with A=`$0000`, X equal to the native selected-list end, Y=`$0010`, P=`(entry P & $4C) | $23`, original DBR/D/SP, and the original return bytes intact. |
| Invalid or unbound input | Jump to the refusal tail with the original A/X/Y/P/DBR/D/SP and return bytes. No publication is allowed. Bounded scratch and stack writes are permitted. |

Owner activation is a full word `$0001` at `$7E5DAC + owner`; adjacent owners
therefore overlap by one byte. Script offset and bank are separate words at
`$7E5DBD + 4*owner` and `$7E5DBF + 4*owner`. The harness must replay and compare
these ordered byte writes rather than treating activation as a byte flag.

This contract concerns final native state and the permitted publication
footprint. Preflight deliberately precedes publication, so it does not claim
instruction-for-instruction or intermediate-state equivalence to the vanilla
routine. Synthetic IRQ, NMI, and DMA sources are disabled. A real game
interrupt policy is unresolved.

## Isolated execution and evidence

`tools/run_schala_package_helper_conformance_v0.py` assembles a raw `norom`
binary with the existing pinned Asar 1.91. Its collector is
`tools/mesen_schala_package_helper_conformance_v0.lua`. Execution uses the
existing pinned Mesen 2.1.1 runtime and a uniquely named copy of the existing
original SHA benchmark image. The launcher stages only the exact runtime
allowlist, creates a new zero-filled disposable SRAM, and redirects its
profile and temporary directories into the unique ignored test directory.
It does not copy any shared saves or touch an existing emulator session.

The project also retains its previously proved six-operation
[Mesen MCP bridge](project_epoch_mesen_mcp_feasibility_2026-08-31.md) for
bounded checkpoint and memory observations. This helper test uses a dedicated
Lua collector through Mesen's test runner, which supplies the original-code
injection and exact CPU fixture needed by this gate. The existing MCP
interface is unchanged; these native runs were not MCP calls.

The collector loads original code and synthetic fixtures into WRAM, sets
documented CPU state, and records actual CPU execution through the selected
tail. It captures all CPU writes and compares all 128 KiB of WRAM with its
pre-execution baseline. Code, registry, fixtures, return bytes, and guards
must remain unchanged. Only the declared output addresses, the `$80`-byte
synthetic scratch window, and the bounded ten-byte stack window may change;
the canonical path may not write scratch.

The source model supplies expected routing, registers, flags, selected
owners, and bank-qualified publication values. The emulator supplies the
observed CPU state and memory effects. Independent source review supplements
that comparison; agreement does not prove production integration.

Synthetic addresses are deliberately explicit:

| Role | Test address or half-open span |
| --- | --- |
| Binding registry | `$7E3000-$7E3060` |
| Scratch | `$7E4000-$7E4080` |
| Maximum helper stack footprint | `$7E1FE6-$7E1FF0` |
| Initial SP | `$1FEF` |
| Original helper code | Tested at `$7F8000` and `$7F9000`, 537 bytes each |
| Canonical / success / refusal tails | `$7FF000` / `$7FF010` / `$7FF020` |

None of these spans establishes ownership in Chrono Trigger. No same-size
ROM mutation or patch is performed, so this is not an exception to the
canonical-ROM write-intent guard. Future game mutations must pass that guard
with separately approved hooks and allocations.

## Reproduction and current result

All three current-source full runs pass 879 cases: 471 high-path successes,
216 refusals, and 192 canonical-path cases. Two independent launches at
`$7F8000` produce byte-identical traces. A third launch at `$7F9000` passes the
same contract with the separately assembled relocated binary. This proves
the two tested placements, not every possible placement.

The matrix includes all 128 canonical selectors; all 256 branch-byte values;
every owner bit through both masks; all sixteen bound high selectors through
both branches; sparse, full, and empty masks; repeated and distinct pointers;
both diagnostic source banks; exact bank endpoints and overflow; invalid
validity, bank, branch, and selector words; and invalid selected or unselected
pointers. It also covers all 64 entry status bytes compatible with native
M=0/X=0 across canonical, both success branches, and refusal routes.

Both the final CPU state and every permitted publication agree with the
pinned host model. The complete WRAM diff and CPU write callbacks show no
undeclared writes, including writes later restored to their baseline value.
All source and staged runtime/image/SRAM input hashes remain unchanged.
Independent source review found no remaining blocker after the boundary,
source-span, and reproduction corrections.

| Artifact | SHA-256 |
| --- | --- |
| Original helper source | `26987977881f24cbe234262f59c4a3f8de438e4bde3eb053375f0f29ae436f80` |
| Raw helper at `$7F8000` | `bf9f2f9a1e3e7f680ebfbbab38d0e2a3de15a0e85ec3836066eaeb6170dc057f` |
| Raw helper at `$7F9000` | `4ccf5cb8c9a67e42f44ac78a22f1b2367ce8713688bd391afd637e88e3bc3ce1` |
| Shared 879-case contract | `31bced8f3838f9c107fc3a662cb54c3717c46665d7983cc78a7361ce4228e905` |
| Both original-placement traces | `5726e9e8c92231e07a5833063375a6c717a9bc336394b02cb93df58e2d290833` |
| Relocated trace | `b88353b86413f491114c5cda88fa474e09942696ddb2450379ca7920d78139a6` |

The complete metadata reference is
`references/schala_package_helper_conformance_v0.json`. Private evidence is
retained in `private/test_runs/package_helper_conformance_20260908_run1`,
`private/test_runs/package_helper_conformance_20260908_run2`, and
`private/test_runs/package_helper_conformance_20260908_relocated`.
The preliminary mechanism smoke and 129-case subset are separate exploratory
artifacts; neither substitutes for these final complete runs.

For the relocation comparison, preserve record order and the fields `name`,
`route`, `cpu`, `instructions`, `writes`, and `changes`; remove only memory
pairs in scratch `$7E4000-$7E407F` or stack `$7E1FE6-$7E1FEF`, preserving all
remaining pair order. Serialize that row list with Python
`json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n"`, encoded as
UTF-8. All three normalized SHA-256 values are
`a903c0de53d89eaae4fad5a24aa7a2a8088a1e01139f6ea8f1afb2fb699368bb`.
The relocated binaries differ only at offsets 181 and 192, the high operands
of the two local `JSR` instructions. The raw relocated trace remains distinct.

The stored `instructions` / `cpu_instruction_counts` fields report collector
execution-callback counts, including terminal observation before the tail
stub executes: 16-1,458 per case. They are not cycle or game-timing evidence.
Refusal before particular descriptor reads is a source-inspected property;
this collector captures writes and terminal CPU state, not read callbacks.

All 30 focused harness tests pass. The complete project suite runs 1,042 tests
in 42.501 seconds: 1,020 pass, zero fail, and the same 22 explicit optional
cases skip. All 193 Python sources under `tools/` and `tests/` compile in
memory. The suite log and compilation manifest remain in
`private/test_runs/package_helper_suite_20260908_01`.

Run from the project root with a fresh private output directory:

```powershell
python -B tools/run_schala_package_helper_conformance_v0.py --output-dir private/test_runs/package_helper_NEW1 --repetition 1 --timeout 120 --code-base 0x7F8000
python -B tools/run_schala_package_helper_conformance_v0.py --output-dir private/test_runs/package_helper_NEW2 --repetition 2 --timeout 120 --code-base 0x7F8000
python -B tools/run_schala_package_helper_conformance_v0.py --output-dir private/test_runs/package_helper_NEW3 --repetition 1 --timeout 120 --code-base 0x7F9000
python -B -m unittest discover -s tests
```

`--smoke` tests only the collector mechanism; `--limit` produces only
a subset and must never be reported as the complete gate.

Every raw binary, generated wrapper, fixture, trace, staged runtime, cartridge,
SRAM, and process log remains under ignored `private/`. Tracked references
contain original source, test contracts, hashes, and evidence summaries only.

## Remaining integration work

Passing this gate can establish native execution of this bounded descriptor
helper. It cannot establish expanded-ROM reads, the chosen game hook's live
ABI, approved code and scratch placement, interrupt compatibility, command
execution, a Schala battle action, or a true playable PC `$07`.

The next gate, `BA-NATIVE-INTEGRATION-DESIGN`, must connect the proved helper contract to the
actual fixed-bank resolver: identify the exact hook preimage and continuation
state, select named expanded allocations, prove source-bank access, and resolve
scratch and interrupt ownership. Production high selectors remain unbound
until those obligations and the existing static stream policy are satisfied.
