# Successful queued-Tech transaction observation v1

Status: `verified-runtime`, two byte-identical source-matched observations
after independent review. Date: 2026-09-08. This report is not a production
installation approval.

The ordinary supported-PC action prepares effects and spends MP before entering
the player-Tech package resolver. It applies prepared HP results after the
animation finishes. Refusing only at the resolver therefore occurs after the
observed MP charge and after effect preparation. A future high-package refusal
needs an earlier, separately proved transaction boundary or an explicit complete
rollback contract. This observation executes a successful canonical action; it
does not execute a refusal or certify any cancellation destination.

The new evidence extends the existing
[primary resolver observation](../references/package_resolver_observation_v0.json)
and [interrupt-context observation](schala_package_resolver_context_v1.md).
It follows one queued action from entry through its actual near-return caller,
rather than assigning all records in a time window to that action. Every raw
trace, state, SRAM, ROM and staged emulator remains ignored under `private/`.
The tracked deliverables are original observer/validator source, original
synthetic adversarial tests, this report and a metadata-only reference.

## Declared setup and provenance

The launcher fixes the canonical US Rev0 4 MiB ROM, the recovered pre-Lavos
8 KiB SRAM, and the accepted command-ready Lavos battle checkpoint. Their
SHA-256 identities are:

| Input | SHA-256 |
| --- | --- |
| Clean ROM | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| Recovered SRAM | `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203` |
| Battle-ready state, 261,614 bytes | `d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b` |

The checkpoint provenance is recorded in
[its existing acceptance reference](../references/mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json).
Its acquisition collector explicitly copies the recovered SRAM bytes into
emulated SRAM, then uses controller input to reach the battle-ready state. The
checkpoint launcher normalizes the non-authoritative preview framebuffer and
verifies fresh reloads; it does not thereby prove that this state was acquired
by an unassisted player session. The current observer loads that exact saved
state, then supplies Down on input polls 20-23 and A on polls 60-63, 100-103
and 140-143. It supplies no other input and stops at poll 1200.

Current execution uses an isolated Mesen 2.1.1 copy, private profile, disposable
game filenames and save directory. Only the checkpoint load and enumerated
joypad schedule affect emulation. There is no injected code, CPU-register edit,
canary, forced game flag, ROM change or installed helper. The launcher checks
all input, runtime and observer source hashes before and after execution and
requires the exact staged save-directory contents. A prelaunch manifest and
exact copies of the original source files preserve the revision even if a run
is later rejected. The observer exposes no arbitrary collector, checkpoint,
input schedule or mutation option.

## Observed action and boundaries

The primary replay has one invocation, transaction ID 1. It enters
`$C1BB49` at poll 373 with SP `$06EA`, D `$0000`, DBR `$7E`, M=1, X=0,
and the first queued-action pointer `$93EE`. Its saved near-return word is
`$85D0`; the actual return is observed at `$C185D1` with SP `$06EC` at
poll 994. The complete retained 16-byte outer stack snapshot survives the
outer boundaries, and the actual RTS preserves A/X/Y/D/DBR/P and removes
exactly the two near-return bytes.

| Boundary | CPU address | Input poll | SP | Meaning in this observation |
| --- | --- | ---: | --- | --- |
| Queued Tech entry | `$C1BB49` | 373 | `$06EA` | Owns this invocation and queue pointer |
| Target validation returned | `$C1BB8B` | 374 | `$06EA` | Participant list is `$00,$FF,$FF`; failure flags clear |
| Before effect preparation | `$C1BBD4` | 374 | `$06EA` | Exact A=0, X=0, Y=3, P=`$22`, D=0, DBR=`$7E` |
| Participant MP deduction | `$C1CC71` | 376 | `$06E8` | Three separately paired calls; one charge and two empty entries |
| Package resolver entry | `$C14612` | 378 | `$06D8` | Canonical selector `$08`, branch `$0000` |
| Pending result application | `$C1EC7F` | 993 | `$06E4` | Nested result-wrapper frame retained |
| Shared finalizer entry | `$C1BDB3` | 994 | `$06E8` | Near return `$BC5C`, followed by queue release |
| Actual queued-action caller | `$C185D1` | 994 | `$06EC` | ID 1 closes after this snapshot |

The trace retains full CPU register metadata at the sampled boundaries. The
validator checks the applicable width/addressing contract, exact saved frames,
call/return register continuity and queue pointer, rather than assuming a
watchpoint label supplies them. Resolver returns are nested inside the wider
transaction: `$432A/$40AF` at resolver SP `$06D8` are not the queued-action
return word. The first caller resumes at `$C140B0` with SP `$06DC`; its retained
stack and D/DBR/M/X context are checked throughout the latch waits.

The action/config ID and package selector are both `$08` in this canonical
example. This equality is observed for this binding only. It assigns no
Schala action, high package selector, logical PC `$07` or expanded allocation.

## Memory namespaces and direct write evidence

The participant IDs are at `$7EB2EA-$7EB2EC`. The nearby
`$7EB3BA-$7EB3BC` bytes are copied accessory IDs used by MP-discount logic;
they are not participant IDs. The mapping at `$7EB1BE-$7EB1C4` is a seven-entry
logical-PC-to-battle-slot map. The `$15`-byte queue snapshot consists of three
seven-byte records at `$93EE`, `$93F5` and `$93FC`. It is not seven three-byte
records. These statements are supported by the pinned canonical `bank_C1.asm`
instruction spans and the live indexing/pointer evidence.

The battle-record snapshot has eleven records of `$80` bytes at `$7E5E2D`.
Within each record, current HP is offset `+3`, maximum HP `+5`, current MP
`+7` and maximum MP `+9`, each a word. Every actual CPU write to those eight
bytes per battler is recorded, along with the queue, `$B18E-$B1BD`, eleven
ATB-rate/status bytes, `$AF22/$AF23`, and the two completion latches.

The validator maintains a byte ledger across that exact watched set. A write
callback snapshot precedes the write; its address/value updates the ledger,
and the next retained snapshot must equal it. Every sampled change through
the actual transaction caller must therefore have a matching actual write.
This is a watched-range proof, not a full-WRAM diff or proof that effect
preparation has no other side effects. The ledger ends at this invocation's
caller; later command activity at terminal cannot donate evidence to it.

The three MP calls have participant arguments `$00,$FF,$FF` and cost
arguments 20, 0 and 0. The first call writes both bytes of `$7E5E34` from
93 to 73; its write callbacks report the continuation PC `$C1CC8F` of the
canonical word store. The validator pairs these writes with this call's own
near frame, register state, pre-RTS readback and caller readback. The `$FF`
calls write no MP. The other two live party MP words stay 97 and 99 throughout
the owned transaction. This covers the three live party records, not every
serialized playable-character record.

HP pending terms are the three four-byte-per-battler arrays at `$B328`,
`$B354` and `$B380`. Their combined region is `$84` bytes. They are distinct
from the separately observed `$B18E-$B1BD` pending-results region. Canonical
`$C1EC99-$C1ECA0` loads current HP, sets carry, subtracts the first term at
`$B328,Y` and stores the word. For every battler, the trace supplies the
pre-store HP/term/flags, matching X/Y and accumulator, the two actual byte
writes, and an immediate `$C1ECA3` execution readback before the next result
instruction. The readback proves a completed store; the pre-store execution
watchpoint alone would not.

| Battle slot | HP before first pass | First pending term | HP after actual store |
| --- | ---: | ---: | ---: |
| 3 | 8,000 | 1,663 | 6,337 |
| 6 | 12,000 | 1,665 | 10,335 |
| 10 | 20,000 | 80 | 19,920 |

All other first-pass terms are zero. Eleven paired store/readback witnesses
are required. Operand values here are debugger snapshots tied to canonical
instruction semantics; they are not a separate trace of every CPU operand
read. Later HP passes and clamping execute and their watched writes reconcile
with the byte ledger, but this report does not generalize the first-pass
arithmetic proof to all result semantics.

The shared finalizer clears the selected record and the queue-release path
returns to its real caller. The other two queued records and the validated
participant mapping remain unchanged through that caller. The target-result
clear has a separate snapshot witness: `$AD89-$AD9A` is preserved; index byte
`$AD9B` and all `$B0` bytes at `$AD9C-$AE4B` are zero afterward. These table
stores are not in the write callback set, so the table claim is explicitly
snapshot-only.

## History, tests and remaining gate

The root exploratory run `package_transaction_20260908_explore1` captured
1,266 records but was rejected by its former 4 MiB host read limit. The trace
and staged collector remain unchanged. The first hardened replay added eleven
HP readbacks and the real HP-term region. It was rejected because the new
validator incorrectly assumed that the target-result clear preserved only
16 header bytes and that the original `$AC`-byte snapshot covered the table.
Pinned canonical `$FDACEE-$FDACFC` instead clears `$AD9B` and the complete
`$AD9C-$AE4B` table. The corrected `$C3`-byte snapshot at `$AD89` preserves
18 header bytes and checks 177 cleared bytes. This is an explicitly retained
exploratory observer correction; no conflicting published map is alleged.

The corrected `package_transaction_20260908_hardened2` trace passes all current
checks. Independent review reran all 41 tests, revalidated the trace and all
five archived original sources, and rejected additional adversarial changes
to the last active caller's pending data, clock, transaction ID and program
bank. The frozen final pair then repeated in
`private/test_runs/package_transaction_20260908_final1` and
`private/test_runs/package_transaction_20260908_final2`. Each contains 1,277
records, including 150 watched transaction writes, 18 resolver publication
writes, eight latch writes and eleven HP readbacks. Both complete traces,
manifests and prelaunch manifests are byte-identical:

| Artifact in each final run | Bytes | SHA-256 |
| --- | ---: | --- |
| `trace.json` | 6,113,025 | `fc9e89c139d00a23ab67a84ee77f497e6dfe63133c14509b23f50ce72d0523e7` |
| `manifest.json` | 11,409 | `44b746ad5924ee085a7d203b84cf3f22480838d8bbea751ccef98149a508378d` |
| `launch_inputs.json` | 2,442 | `bad38935adf7604e296b0ce03b77ef3cc529a79670c4d2ce7013b8d2bc6017e8` |

The [accepted metadata reference](../references/package_transaction_observation_v1.json)
records all original source hashes, input/runtime identities, source archives,
canonical instruction-span hashes, witness ordinals and historical artifact
identities. The older failed runs lack a full prelaunch source archive;
their staged Lua and raw trace identities are available, and this report does
not reconstruct or certify a missing historical launcher revision.

Run the original synthetic adversarial tests with:

```powershell
python -B -m unittest discover -s tests -p test_package_transaction_observation_v1.py
```

The 41 tests reject missing or cross-invocation witnesses, incorrect CPU shape,
stack/return damage, width and addressing drift, mismatched MP ownership,
missing actual HP/MP stores, false readbacks, wrong queue/table bounds and
clock inconsistencies. Original fixtures also accept full-clock rollover and
demonstrate that accessory bytes do not stand in for participant IDs.

Reproduce an observation in a new private directory:

```powershell
python -B tools/run_package_transaction_observation_v1.py --output-dir private/test_runs/package_transaction_NEW_UNIQUE
```

Revalidate the accepted pair and reproduce its metadata without launching an
emulator or writing a file:

```powershell
python -B tools/collect_package_transaction_evidence_v1.py
```

This verifies current and archived sources, pinned artifact hashes, exact
staged input/runtime bytes and save entries, and reruns the strict trace
validator. Serialize the returned object as indented JSON, UTF-8, LF and one
trailing newline to reproduce the tracked reference byte for byte.

The trace's `frame` field is a relative input-poll ordinal. Timing uses full
`memoryManager.masterClock`; generic `masterClock` must equal its low 32 bits.
CPU cycles and frame counts are checked separately for monotonicity. This
does not convert input polls into CPU cycles or wall-clock duration.

The remaining refusal gate is to prove a natural unsuccessful route and its
complete queue/participant/ATB/result lifecycle, then design an explicit
preparation-time high-package preflight. This successful trace supplies the
before/after action boundary and explains why resolver-only refusal is too
late for the observed MP charge. It does not approve a production hook,
scratch/stack ownership, interrupt schedule, expanded-cartridge placement,
high selector or eighth playable character.
