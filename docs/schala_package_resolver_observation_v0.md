# Canonical player-Tech resolver observation v0

Date: 2026-09-08. Evidence: `verified-runtime`, one ordinary primary PC
invocation from the accepted Lavos checkpoint, repeated independently.
Status: `complete-bounded-primary-observation`. The encompassing
`BA-NATIVE-INTEGRATION-DESIGN` remains in progress.

## Result

Two fresh isolated Mesen 2.1.1 launches reproduce the same 1,774-record trace
while running the unchanged canonical US Rev0 ROM. One PC type-2 action
reaches the player-Tech package resolver, returns through the expected call
frames, and later satisfies its own action-completion latches. No helper,
high selector, canary, ROM patch, CPU-state edit, or memory injection is used.

Both raw trace SHA-256 values are
`699776cf0d3c69fe13f7fbd7eb9240e47b56cc651395ac53cf15253c73b25190`.
The [metadata reference](../references/package_resolver_observation_v0.json)
binds sources, input/tool identities, complete private output identities,
the repeated observations, and reproduction commands. Raw records remain
private because they contain game-derived state and pointers.

This is a new runtime observation of the game's existing resolver. It is
separate from the original helper's completed synthetic conformance proof.

## Observed entry, publications, and return chain

At relative input poll 378, the actor index is `$00`, action type `$02`,
physical config row `$08`, and package selector `$08`. Branch word `$A0B3`
is `$0000`. No named Tech or row-`$01` meaning is inferred from the selection.
Entry is native mode, M=0/X=0, P=`$80`, D=`$0000`, DBR=`$7E`, SP=`$06D8`.
The two return words are `$432A` and `$40AF`, followed by saved caller state.

The eighteen publication bytes match the existing canonical host model in
value and order: activation, script-offset, and script-bank words for owners
`$00`, `$03`, and `$04`. The model privately reconstructs selector `$08` from
the pinned canonical ROM; no pointer payload is included in this report.
The tail's A/X/Y/P, root, consumed first mask, retained second mask, cleared
branch byte, SP, and all eight captured stack bytes also match.

| Watched entry | Observed SP | Relation |
| --- | --- | --- |
| Resolver `$C1:4612` | `$06D8` | Two original near-call frames retained |
| Resolver tail `$C1:467F` / common loader `$C1:4833` | `$06D8` | No new call frame |
| Common loader RTS `$C1:48EB` | `$06D8` | First original return about to execute |
| Dispatcher RTS `$C1:432B` | `$06DA` | First two-byte frame consumed |
| Caller `$C1:40B0` | `$06DC` | Both two-byte frames consumed |

The common loader and return observations occur at poll 413. A fixed watched
address can also be a loop head: the many later `caller-resume` records at
`$C1:40B0` are not hundreds of separate resolver calls. The summary pairs the
first ordered return stages with their actual resolver invocation.

The raw `selector_word` snapshot is meaningful as a selector only at entry.
After the root is stored at `$9878/$9879`, the word beginning at `$9877`
overlaps its low byte. Do not classify that later combined word as another
package selector.

## Completion belongs to the same PC action

The preceding enemy action also uses the common loader and completion
latches. Those earlier observations cannot establish the PC action's result.
The summary starts each PC window at its resolver entry and ends it at the
next resolver entry or next action's branch-producer event.

| Observed event within the PC window | Relative input poll |
| --- | ---: |
| Effect latch `$5D9B` becomes zero | 927 |
| Synchronization handler and actual `$9876=1` write | 991 |
| Caller reads nonzero `$9876`, with `$5D9B=0` | 991 |
| Subsequent effect wait reads `$5D9B=0` | 992 |
| Cleanup resets `$9876` | 993 |
| Next action producer, enemy actor `$06` | 1133 |

Both completion reads occur with SP=`$06DC`, before the next action producer.
Independent inspection confirmed the actor/type/config context through this
window. This proves the observed ordinary action's completion sequence. It
does not define how a refused or terminal-only new package should complete.

The trace field `frame` is a relative **input-poll count**, inherited from the
replay schedule. It is not a CPU-cycle or verified video-frame measurement.

## Method and reproducibility

The original runner is `tools/run_package_resolver_observation_v0.py`; the
collector is `tools/mesen_package_resolver_observation_v0.lua`. Before launch,
the runner verifies the exact ROM, SRAM, accepted native state, and emulator
identities. It copies only the explicit allowlist into a fresh ignored
directory, compares staged bytes to their pinned sources, creates isolated
profile/temp/Saves storage, and starts a hidden bounded process. The
controller type is explicitly `SnesController`.

The collector loads the accepted state and supplies ordinary Down at input
polls 20-23, A at 60-63, A at 100-103, and A at 140-143; all other input is
empty. It observes through poll 1200. The only emulation control operations
are state loading and this fixed joypad sequence. CPU and memory callbacks
only read state, with a 4,096-record limit. The host timeout is 75 seconds.

Source files, the canonical image, original SRAM/state, and every staged
input have unchanged post-run hashes. No existing emulator session or shared
save directory is used. No image or patch is produced, and production
write-intent catalogs remain unchanged.

Required private inputs are the project's existing pinned US Rev0 image,
recovered pre-Lavos SRAM, accepted `battle_ready.mss`, and Mesen toolchain.
The exact paths and identities are in the runner and reference; their absence
is not permission to substitute another image or state silently.

```powershell
python -B tools/run_package_resolver_observation_v0.py --output-dir private/test_runs/resolver_observation_NEW1
python -B tools/run_package_resolver_observation_v0.py --output-dir private/test_runs/resolver_observation_NEW2
python -B -m unittest tests.test_package_resolver_observation_v0 -q
```

Use fresh directories. Require matching trace hashes, one observed canonical
PC invocation, true entry/return/completion fields, and unchanged input hashes.
To reproduce the independent publication comparison, find the entry-to-tail
window, privately resolve its canonical selector with the pinned bank-adapter
model, replay each expected activation/offset/bank word as ordered low/high
bytes, and compare the eighteen `publication-write` observations. Compare
the tail fields and retained stack bytes against that same invocation.

Eighteen focused synthetic-metadata tests validate entry requirements, stack
and width transitions, missing or reordered stages, multiple invocations,
and completion attribution. Earlier enemy completion, later action
completion, reversed latch reads, or missing resolver observations cannot
produce a completed PC result.

## Preserved exploratory history

Three exploratory captures precede the final pair:

1. `resolver_observation_20260908_exploratory1` omitted an explicit controller
   setting. The sequence did not reach the PC resolver; it recorded an enemy
   action and reports `resolver_observed=false`. It is not resolver proof.
2. `resolver_observation_20260908_exploratory2` configured the controller and
   captured the valid PC entry, publications, and returns, but stopped at
   poll 600 while that PC action was still in progress. Earlier enemy
   completion at polls 332-333 must not be credited to it.
3. `resolver_observation_20260908_exploratory3` extended the bounded capture to
   1200 polls and paired completion with its invocation. It matches the final
   two source-aligned traces, but the final pair supplies independent replay.

Each private run retains its then-current launcher/collector identities and
trace. Historical evidence is not silently regenerated or promoted after a
source change.

## Remaining integration obligations

The completed primary observation can now be reused. It does not prove the
ordinary alternate branch, every caller, interrupt nesting, a high-selector
reader in expanded ROM, a cancellation path, or PC `$07` behavior. Live
scratch cannot use the test fixture's `$7E4000`, which has known vanilla
menu/overworld uses. The candidate expanded allocations remain design records.

Continue with the explicit refusal/action-lifecycle design and its permitted
cleanup/return state, then the separately versioned ROM-source reader and
scratch/interrupt ownership. The [integration design](schala_package_resolver_integration_design_v0.md)
and [placement review](schala_package_placement_interrupt_review_v0.md) identify
the exact unresolved proof obligations. No installation follows automatically
from this observation.
