# Original package helper v3: immutable ROM code and registry

Date: 2026-09-08. Subgate `BA-NATIVE-ROM-CODE-REGISTRY-CONFORMANCE`, within
`BA-NATIVE-INTEGRATION-DESIGN`.

Status: `verified-runtime` for the original synthetic ROM-code/ROM-registry
normal-call contract. Two fresh isolated runs passed all 3,184 cases each,
for 6,368 total cases. Their complete 113,917,080-byte traces are byte-identical,
SHA-256 `f9d042c5d76a15a717c7330204d0764a2783191875ac3c91b727a799e6450710`.
Each run contains 2,560 successful transports, 384 canonical paths and 240
refusals. Independent source review covered the native observation contract,
strict evidence schema and prelaunch source-history preservation. Fifty-two
original host tests pass.

The [metadata reference](../references/schala_package_helper_v3_rom.json)
records both full run manifests, exact source/runtime/staged identities,
per-case input hashes and preserved exploratory history. Its
[read-only collector](../tools/collect_schala_package_helper_v3_rom_evidence.py)
revalidates both complete native traces and reproduces the reference without
launching an emulator.

## Experiment and source continuity

V3 executes the unchanged 577-byte v2 stack-frame implementation from CPU
`$41:0000`, and reads its registry and allowlists from immutable bank `$43`.
Its original, certified descriptor fixtures occupy bank `$42`. This closes a
separate placement and input-storage question left open by the earlier helper
proofs. The completed v2 assembly, collectors, tests, reports and references
are preserved. The same assembly is relocated with different explicitly bound
diagnostic symbols; its resulting ROM code SHA-256 is
`7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b`.

The independently reviewed [original cartridge builder](original_snes_package_cartridge_v1.md)
passed the original-diagnostic complete-diff guard before writing either of two
byte-identical eight-MiB cartridges. The v3 launcher accepts only the first
reviewed cartridge, SHA-256
`1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b`,
and reconciles its completed-build receipt, immutable components, fixed bridge
and tails, command-policy certificate and target identity. Each emulator run
gets a byte-exact private copy and a separate zero-filled 8-KiB SRAM. This
harness does not mutate the image or build a patch. No Chrono Trigger bytes
are an input to this experiment.

The source is [the original fixture module](../tools/original_snes_package_fixtures_v1.py).
Four diagnostic bindings `$80-$83` use masks `$FFFF/$FFFF`, `$A501/$0080`,
`$8000/$0000`, and `$0000/$0001` respectively. Their descriptor roots are
`$42:0000/$0100/$0200/$0300`; per-package original terminal targets are fixed
at root `+$80` and, where required, `+$81`. Repeated pointers and an empty
selected mask occur deliberately. The entire 897-byte descriptor/terminal
payload and the complete 1,280-byte registry/allowlist payload are identity-bound.
The twelve remaining registry records `$84-$8F` are zero and unbound.
These bindings belong only to the original diagnostic cartridge; production
selectors and production allocation/hook catalogs remain unbound and empty.

Each package is certified under the existing interpreter-pinned flat-direct
policy, including both masks, exact original named spans, complete token
ownership and terminal `$00`. The CPU reads descriptor pointer words and the
allowlist, but does not read or execute the pointed terminal streams. A source
certificate proves their static admissibility; this experiment proves transport.

## Normal-call matrix and observations

Each completed full run has 3,184 cases, split equally between synthetic entry
SP `$1FEF` and `$06D8`. The latter deliberately reuses the numeric SP from an
observed vanilla checkpoint, while all memory and execution here are original
synthetic fixtures. At each SP the matrix includes:

- All 128 canonical selectors with a hostile 16-bit flag word.
- All 256 flag bytes for each of the four immutable high bindings.
- All twelve unbound records with flags `$00/$40/$FF`.
- Four unsupported/wide selectors with three flags, and each bound selector
  with the two unsupported wide flags `$0100/$FFFF`.
- All 64 native M0/X0 status-byte combinations across six canonical,
  primary, alternate, empty-mask and unbound routes.

The helper's stack contract remains 42 local bytes, eight saved-context bytes,
and a two-byte CountBits return, for a 52-byte maximum. An unbound high record
allocates the 50-byte frame and reads its two-byte validity word, then refuses
before CountBits. Canonical and unsupported/wide-input exits use only the
eight saved bytes. V3 does not repeat v2's completed low-SP floor matrix.

The entry bridge is original ROM `$00:8060`; its redirected setup JML is not
observed. The first helper PHP at `$41:0000` and every subsequent helper
instruction are observed. Exact route-tail addresses `$00:8100/$8110/$8120`
are observed and intercepted before their BRA executes. The fail-closed
execution guard permits only the exact 577-byte helper span and these tails;
it does not independently disassemble every permissible instruction start.
Every retained pre-execution opcode peek must equal the exact mapped ROM
byte. Mesen's pinned callback implementation supplies a debugger Peek, so this
is not an independent observation of the actual opcode bus fetch. The pinned
source derivation is retained in the [Mesen callback provenance note](mesen_nmi_request_source_v1.md),
with exact `SnesDebugger.cpp`, `Debugger.cpp` and `ScriptManager.h` source links.

The source-derived ordered ROM-read contract includes registry-header words,
descriptor masks, every direct pointer in both masks, every corresponding
allowlist lookup and the selected publication pass, retaining bank `$42/$43`
interleaving. CPU data-read guards reject all other ROM regions. Native final
A/X/Y/D/DBR/SP/P and emulation mode, ordered publication bytes, complete PC
sequence, instruction-owned stack accesses, and every required post-stack-change
SP observation must agree with their exact contracts.

Every changed WRAM byte must equal the final observed CPU write to that byte,
starting from the explicit `$A5` baseline plus the four declared selector/flag
setup bytes. This full final-diff ledger includes stack bytes. Stack-relative
accesses must be strictly above the live SP and within the owning instruction's
one-or-two-byte unsigned operand span. This guard does not independently
emulate M-state-dependent access width. Synthetic `$7E:4000` scratch remains
untouched, and immutable input snapshots match before and after every case.
IRQ, NMI, DMA and HDMA are disabled in this normal-call proof.

The identical per-run observation totals are:

| Observation | Count |
| --- | ---: |
| Executed helper instructions | 2,537,920 |
| Intercepted terminal tails, observed but not executed | 3,184 |
| Pre-execution PC/opcode-peek pairs | 2,541,104 |
| CPU data reads | 1,248,552 |
| Descriptor-bank `$42` byte reads | 94,736 |
| Registry/allowlist-bank `$43` byte reads | 126,864 |
| Instruction-owned stack accesses | 1,561,056 |
| Required post-stack-change SP observations | 52,720 |
| Ordered CPU byte writes | 737,192 |
| Final changed WRAM bytes, summed across cases | 218,904 |

Observed minimum SP values are `$1FBB` and `$06A4`, exactly 52 below their
respective entry values. The full case-contract SHA-256 is
`cfb9f96fb99bb93e4fb1348170d2ec509c9c3d5acfacafd2a7e936e9a5be3258`;
per-case immutable-input hash records are identical across runs, SHA-256
`e80e2d6e6d7fa0c44c5d2c9942e64dba46e6f2ce47447557ea1377bc22b44021`.
Each run checks 25 guarded input/source files, including the test source,
and retains all 19 guarded source-format files before native execution.

## Evidence history and review corrections

The initial 130-case `explore1` run passed: 128 canonical inputs and the first
two flag values for binding `$80`. Its private trace SHA-256 is
`28024b8d62bda5fcb3e0d42987438cc555e992c500e5e9ac5811b12069e3066f`.
That subset and its original source identities remain preserved. Its original
launcher SHA-256 is `f3becf3da6a2f2c60f0500c368d762afc73c6f8816900e535e202d5c1bb39b47`;
the complete pre-hardening source archive manifest is
`c58c474cb338b816e0397fc33018536916291ef090f5db41c02d21a5985d2d99`. Independent
review found no observed native defect, but reproduced a validator schema gap:
Python equality admitted floating-point aliases in native CPU and address/byte
evidence. Strict exact keys, scalar types and native widths now reject these
aliases before semantic comparison. All 130 old records pass the stricter
validator offline. Fifty-two original host tests pass, including exhaustive
one-byte corruption of every immutable input byte and targeted malformed
metadata and source-archive cases.

The current launcher guards tests as well as every executable source and
imported policy/reference. Before process launch it archives each guarded
`.py/.asm/.lua/.json` file under a collision-safe label-and-hash filename,
writes a source snapshot manifest and a prepared launch receipt, and checks
all original, archived and staged hashes after execution. These original source
snapshots survive even when a later run fails before producing an accepted
manifest. The earlier exploratory sources were separately archived before
hardening, preserving the original evidence version without rewriting it.

## Reproduction and limits

Run the original host tests without private game data:

```powershell
python -B -m unittest discover -s tests -p test_schala_package_helper_v3_rom.py
```

Revalidate the accepted private evidence and emit metadata to standard output:

```powershell
python -B tools/collect_schala_package_helper_v3_rom_evidence.py
```

Once the separately reviewed original cartridge exists locally, use a new
private directory for each full native repetition:

```powershell
python -B tools/run_schala_package_helper_v3_rom.py --output-dir private/test_runs/package_helper_v3_rom_NEW1 --repetition 1 --timeout 900
python -B tools/run_schala_package_helper_v3_rom.py --output-dir private/test_runs/package_helper_v3_rom_NEW2 --repetition 2 --timeout 900
```

This is original diagnostic ROM-code, ROM-registry and descriptor transport
conformance. It does not install or execute a game resolver hook, prove real
game stack ownership or interruption, complete an action or animation, bind
Schala actions, or implement logical PC `$07`. The separate NMI pilot and real
game lifecycle observations retain their own source and evidence scopes.
