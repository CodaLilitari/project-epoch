# Canonical resolver and interrupt context observation v1

Date: 2026-09-08. Gate: `BA-NATIVE-INTEGRATION-DESIGN`.

Status: `verified-runtime` for two identical, bounded clean-ROM observations.
This establishes the recorded ordinary resolver and interrupt context. No
helper, ROM hook, high package selector, new scratch region, or PC `$07` is
installed or approved.

Two fresh isolated Mesen runs reproduce 11,905 records each, including 2,402
paired handler entries and pre-RTI observations, one ordinary PC resolver
invocation, and one scene-latch clear attributed to that PC's observation
window. The direct-page memory callback has a positive control. The short
resolver interval contains no interrupt entry, so this result does not test
an interrupt arriving while a new helper changes registers or publishes data.

The [machine-readable reference](../references/package_resolver_context_v1.json)
records the accepted pair, exact input/source/runtime hashes, seven pinned
Mesen source files, canonical code-span hashes, and the scoped observations.
The [earlier primary observation](schala_package_resolver_observation_v0.md)
remains a separate completed result. This pass adds native handler-context
and clock interpretation rather than replacing that earlier evidence.

## What the repeated runs establish

| Observation | Result per run | Scope |
| --- | --- | --- |
| Paired normal NMI entries / pre-RTI points | 1,201 | `$D1:E77C` to `$D1:E898` |
| Paired battle IRQ entries / pre-RTI points | 1,201 | `$D1:FE97` to `$D1:FEF3` |
| Register and return-frame comparison | All 2,402 pairs pass | A/X/Y/D/DBR/SP match handler entry; the native four-byte hardware frame is unchanged |
| Native entry status relation | All entries pass | Live P equals saved hardware P with Decimal cleared and Interrupt Disable set |
| IRQ saved Interrupt Disable bit | Zero in all 1,201 observed IRQ frames | An observation, not a universal IRQ precondition |
| Maximum observed handler nesting | One | The current replay does not exercise nested handlers |
| Minimum recorded handler-entry SP | `$06C1` | Entry snapshots only |
| Minimum SP among recorded handler snapshots | `$06A2` | Includes the added display-handler watchpoint; not a complete stack low-water measurement |
| Ordinary PC resolver | Actor `$00`, type `$02`, selector `$08`, branch `$0000` | Same supported PC action context as the primary observation |
| Resolver entry SP | `$06D8` | Does not establish stack space available to another helper |
| Entry-to-pre-JMP-tail interval | 4,244 master clocks; 548 CPU-cycle-counter increments | `$C1:4612` through the pre-execution callback at `$C1:467F` |
| Interrupt entries inside that interval | Zero | No native helper/interruption interaction was tested |
| Direct-page physical callback control | One matched canonical write | `$C1:4627` writes physical WRAM `$0081`; the memory callback reports next PC `$C1:4629` |
| Targeted temporary callbacks | 32 reads and 36 writes, all in main context | These observed accesses are the canonical resolver's `$0080-$0083` operations |
| PC-scoped NMI scene clear | One complete witness | Pre-STZ state, actual zero write, post-write readback, and later same-PC caller read |

The handler comparison occurs **before RTI executes**. It compares the restored
registers and SP at that boundary and verifies the unchanged native hardware
return frame. Live P at pre-RTI is intentionally not compared with handler-entry
P: the canonical epilogue changes width and flags, and RTI restores the saved
status from the hardware frame. This is not an immediate post-RTI capture for
every pair.

The scratch callbacks cover physical WRAM `$0080-$0083` and `$4000-$407F`,
including CPU low-bank mirrors. They run during the short resolver interval,
and during handlers within the PC observation window. No targeted access was
observed in those handlers. This does not prove either region is game-owned
scratch. The separately proved menu/overworld collision at `$7E4000` remains
decisive, and unobserved interrupt paths remain unproved.

The PC observation window begins at its resolver entry and ends at the next
action's branch producer, or the terminal boundary. In these runs that is poll
378 through the producer at poll 1133. It includes the post-action interval;
it is not presented as an exact complete action-lifetime model. The 1,510
handler pairs entering that window are accordingly a window count, not a
count restricted to time while the action is still executing.

## Exact scene-latch attribution

The collector's `nmi-effect-latch-clear` event is an execution watchpoint before
the STZ instruction at `$CD:164D`. Its snapshot still contains `$5D9B=1`.
Counting that watchpoint alone as a completed write would be wrong. The
validator requires the following stronger witness in the same NMI context:

| Step | Record index | Relative input poll | Evidence |
| --- | ---: | ---: | --- |
| Pre-STZ execution watchpoint | 10,119 | 927 | Context 1855, normal NMI, `$5D9B=1` |
| Actual write callback | 10,120 | 927 | Address `$7E5D9B`, value zero, same context; CPU PC has advanced to `$CD:1650` |
| Pre-RTI snapshot after the write | 10,121 | 927 | Same context, `$5D9B=0` |
| Main caller's effect-latch read | 10,580 | 992 | `$C1:40E7`, `$5D9B=0`, still in the same PC observation window |

There is also an earlier clear in NMI context 395 at poll 197. It belongs
outside the captured PC window, during the preceding actor `$03` action. It
is counted separately and cannot satisfy the PC-scoped witness. Likewise, a
later caller read after the next action producer cannot be borrowed to prove
the preceding PC's completion.

The [cancellation contract](schala_package_cancellation_contract_v1.md) explains
why this latch is a scene-script lifetime condition. A refusal adapter must
not clear it merely to make a wait terminate. This observation supplies a
concrete normal-NMI completion witness, not permission to replace its owner.

## Clock interpretation and the 32-bit API limit

The timing report uses `memoryManager.masterClock`, the full serialized SNES
counter. It also records the generic `masterClock`, verifies that it equals
the full counter's low 32 bits, and checks monotonic full clock, CPU cycles,
frame count, and input-poll count. The eight timing keys are exact; an old
exploratory trace containing a larger set is preserved but rejected by the
current strict schema.

The official Mesen 2.1.1 implementation exposes an important distinction:
[`LuaApi::GetState`, lines 1071-1091](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/Debugger/LuaApi.cpp#L1071)
adds its generic `masterClock` through a `uint32_t` local even though
[`SnesConsole::GetMasterClock`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesConsole.cpp#L179)
and the underlying
[`SnesMemoryManager` counter](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp#L393)
use 64 bits. Subtracting only the generic values across a wrap would therefore
misreport an interval. The unit tests include such a wrap with monotonic full
time; these particular native replays do not themselves cross a 32-bit wrap.

The 4,244-clock interval is approximately 0.198 milliseconds at the observed
NTSC rate of 21,477,270 master clocks per second. It ends before the JMP at
`$C1:467F`, excludes the common graphics loader and later action, and is an
emulated-clock measurement rather than wall time spent by the host process.
The 548 increment difference comes from the emulator's 64-bit
[`cpu.cycleCount`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L305);
it is not an instruction count. The frame fields come from the PPU's
[frame-counter state](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L85).
Input-poll ordinals remain a separate counter.

## Review correction: a pending IRQ can outlive SEI

During review, a proposed universal check that IRQ hardware frames must always
have saved I=0 was withdrawn. It was not published as accepted evidence.
Mesen's
[`CheckForInterrupts`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.cpp#L46)
uses a previously sampled IRQ source, while
[`SEI`](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L261)
sets the flag after its addressing-cycle work. The
[previous-cycle sampling](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Shared.h#L336)
can therefore permit a pending IRQ to stack an updated I=1 value.

The final validator records the observed saved-I counts instead. A synthetic
fixture accepts this latency boundary, preventing reintroduction of the
overstrong rule. It does not claim the current battle checkpoint reaches
that timing case. The status relation retained by the validator follows the
[native hardware-entry implementation](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesCpu.Instructions.h#L521):
the saved P is pushed before I is set and Decimal is cleared.

The synthetic nesting fixture now uses NMI inside IRQ. These tests validate
metadata pairing and the specified architectural boundary; they do not turn
every possible LIFO event arrangement into runtime evidence of a reachable
hardware schedule.

## Frozen sources and evidence identities

The canonical ROM, SRAM, and checkpoint remain local-only and unchanged:

| Input | Size | SHA-256 |
| --- | ---: | --- |
| Headerless US Rev0 ROM | 4,194,304 | `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9` |
| Recovered pre-Lavos SRAM | 8,192 | `cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203` |
| Accepted battle-ready Mesen state | 261,614 | `d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b` |

Source and runtime identities:

| File | SHA-256 |
| --- | --- |
| `tools/run_package_resolver_context_v1.py` | `88ccf83e83a68f7bbdc3c65e626b1480041c9e95db4fe36541a6c267b8030214` |
| `tools/mesen_package_resolver_context_v1.lua` | `f7b74d551b74e1b81f0b1be68f07a96ab1a6915a42d6d1d0d832b6d7be5b6519` |
| `tests/test_package_resolver_context_v1.py` | `8927c5ee0d2b29a89e59f5a9534a1a42c0e42511a6efaa8f07b8d590de53d86a` |
| Pinned Mesen executable | `d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b` |
| Pinned Mesen core DLL | `65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74` |

The five timing/API source identities requested for interpretation are below.
Their local files and Git blob hashes were independently matched to GitHub's
tree at exact 2.1.1 commit `137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1`.
The reference also includes the two additional IRQ-pipeline files. No emulator
rebuild is claimed.

| Official source file | SHA-256 |
| --- | --- |
| `Core/Debugger/LuaApi.cpp` | `fd1292483bd2e7fa1f5a13c392afadcae2d9ff418cab216c964d623f97e10e24` |
| `Core/SNES/SnesConsole.cpp` | `cdfa45011f3dfd39fa5a8686e7f827cb8ea660d5a1b79ecb20da9d0c2606c706` |
| `Core/SNES/SnesCpu.Shared.h` | `dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f` |
| `Core/SNES/SnesMemoryManager.cpp` | `2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58` |
| `Core/SNES/SnesPpu.cpp` | `5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180` |

Both accepted runs have trace SHA-256
`6174e223615cbbcc44e1f53862a14f7e103a6c9ed1f850625ebc289624f33679`
and manifest SHA-256
`abc8abbbf135fb1bc4e79ad4b893977015936fb55b4f76746dabd19b573a5c13`.
Their private directories are `private/test_runs/resolver_context_20260908_final1`
and `private/test_runs/resolver_context_20260908_final2`. Raw traces, process
logs, staged emulator files, and all game artifacts remain ignored.

The earlier `resolver_context_20260908_explore1` and
`resolver_context_20260908_hardened1` directories remain unchanged. The first
used the older timing-key shape; the second preceded the final validator
freeze. Final native runs were repeated after the source changes. Private
per-run manifests retain the launcher's exploratory evidence label; the
separate accepted reference records the reviewed, repeated `verified-runtime`
scope rather than rewriting those historical manifests.

## Reproduction and next gate

Run the 30 adversarial tests:

```powershell
python -B -m unittest discover -s tests -p test_package_resolver_context_v1.py
```

They reject wrong CPU/event shapes, unknown execution sites, mismatched or
missing handler pairs, register/frame damage, reversed clocks or polls,
missing resolver tails, missing mirror controls, and false scene-clear or
cross-action attribution. They also exercise valid full-clock rollover and
the pending-IRQ status exception using original synthetic metadata.

Reproduce another isolated observation using a fresh directory:

```powershell
python -B tools/run_package_resolver_context_v1.py --output-dir private/test_runs/resolver_context_NEW_UNIQUE
```

The launcher pins inputs and emulator files, stages exact copies in an
isolated private profile, uses a supported SNES controller and the fixed
input schedule, and verifies source/staged hashes and exact save-directory
contents afterward. It injects no ROM bytes, code, CPU state, memory canary,
or forced game flag. Loading the pinned checkpoint and sending the recorded
ordinary controller inputs are the declared setup actions.

Reproduce the accepted metadata from the already captured frozen pair:

```powershell
python -B tools/collect_package_resolver_context_evidence_v1.py
```

The metadata collector runs the strict validator again, verifies the frozen
source and artifact hashes, checks the official source blobs, and prints
deterministic JSON. It writes no file and launches no emulator. Serialize its
object as indented JSON with UTF-8, LF, and one trailing newline to reproduce
`references/package_resolver_context_v1.json` byte for byte.

The remaining integration work still includes the
[interrupt/scratch closure](schala_package_interrupt_closure_v1.md), native
expanded-ROM reads, actual stack/scratch ownership, the alternate ordinary
resolver branch, and transaction-level refusal. Neither a quiet 0.198 ms
canonical resolver interval nor preserved handler registers establishes that
a larger helper can safely run in the same place.
