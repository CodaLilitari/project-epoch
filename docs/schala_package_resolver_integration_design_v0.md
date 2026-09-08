# Player-Tech package resolver integration design v0

Date: 2026-09-08. Gate: `BA-NATIVE-INTEGRATION-DESIGN`.

Status: `design-in-progress`; canonical entry, continuation, and caller
obligations are `verified-static`. A subsequent repeated
[primary clean-ROM observation](schala_package_resolver_observation_v0.md)
now confirms one ordinary entry/return/publication and completion path.
The experiment plan below records the initial design: its primary baseline
is complete, while alternate inputs and other integration obligations stay
open. No live hook, rejection continuation,
expanded-ROM helper, allocation, or scratch region is approved by this
document. Production high selectors remain unbound.

The 537-byte helper's completed synthetic execution proof remains intact.
The first bounded read-only capture of the actual canonical resolver and its
caller is now complete in the linked observation. The important integration
problem is rejection: declining a descriptor publication does not yet define
how the surrounding battle action finishes safely.

## Source provenance and boundaries

Primary evidence is the user's local, headerless US Rev0 ROM, read in memory:
4,194,304 bytes, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Every span below was independently hashed against that identity on
2026-09-08. Canonical bytes are neither reproduced in this document nor
installed anywhere by this work.

The navigation and annotation source is
[dscotton/ct_disassembly, commit eeae27acdb6565e96d1d796a3d60792c250c0aa1](https://github.com/dscotton/ct_disassembly/tree/eeae27acdb6565e96d1d796a3d60792c250c0aa1),
locally preserved at `private/research/ct_disassembly_eeae27a`. Its
`bank_C1.asm` is unchanged from that commit and has SHA-256
`298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa`.
Annotations are secondary evidence; canonical instruction bytes decide a
conflict. A concrete annotation correction appears below.

All ranges in the following table are half-open CPU bus ranges.

| Source span | Length | SHA-256 | Evidence role |
| --- | ---: | --- | --- |
| `$C1:4090-$C1:409C` | 12 | `44120c3dc47c4c65db83c27ca3306f6a948a65d0d4535aee824eed9082e72872` | Ordinary caller's alternate-branch producer |
| `$C1:40AD-$C1:40ED` | 64 | `2adb6b1ad231dc5bd91cabd37e48b3f64e31803c2913360be64aa378f33ed4bf` | Call, script loop, completion waits, saved-byte restoration |
| `$C1:4310-$C1:432C` | 28 | `797fef4227ddc1fdf7225d7e39bb52d5c9cb9e24ebe4d57b67122aa3db727e37` | Config clear and action-type dispatcher |
| `$C1:45A0-$C1:4612` | 114 | `e4792a2406f40aed51cd3f68d5463bd4c53ec2acf4bdc63293fed09b1250c1f0` | PC-type check, config and auxiliary lookup before candidate hook |
| `$C1:4612-$C1:4616` | 4 | `de49003154a89c179eab719b3741a288e7f53742ff31e29bc446923aa2cbd2ac` | Candidate exact overwritten instruction span |
| `$C1:4612-$C1:4682` | 112 | `a68be4a9dfa59349976827ca080eec58a5057e8144c5ba18a4609bceae291968` | Canonical resolver through success tail transfer |
| `$C1:4833-$C1:48EC` | 185 | `640f3fc03f7287806cca4b0ea552f6d74033c78da2b71e7e9b95e1f98ba35f58` | Common graphics/auxiliary loader through RTS |
| `$C1:4BBE-$C1:4C9E` | 224 | `d65a749d8401c79fae00a9ba24b85ea0b1e83246a06448735339834e0747945e` | Active-script owner dispatch |
| `$C1:4C9E-$C1:4CF0` | 82 | `f9eee9ad39ebab931c5a65d55bbff45585670770b528be2f10d65e9cc7dab561` | Bank-qualified live command dispatch |
| `$C1:4CF0-$C1:4D04` | 20 | `5e3e65e7fc683da6fa456fbe499b2cab80825745a86db42c2f5b3ec82aa7cc7c` | Terminal handler and distinct synchronization handler |
| `$C1:7A63-$C1:7A6B` | 8 | `e5a449366a0a43d8946ada789564a45409e824c2e88b9603ceafaf6b0239ce47` | Four action-type targets, consumed privately |

The existing [package adapter contract](schala_player_tech_package_bank_adapter_v0.md),
[symbolic package proof](schala_symbolic_high_package_v0.md), and
[native helper proof](schala_package_helper_conformance_v0.md) remain the
authority for their own closed scopes. This pass does not repeat the
completed command grammar, package census, or `$1E/$1F` reconstruction.

## Exact hook geometry and ordinary caller path

The action phase calls `$C1:4310` from `$C1:40AD`. The dispatcher clears
sixteen config bytes `$9877-$9886`, sets `$987C` to `$FF`, chooses the action
type, and uses the indirect `JSR` at `$C1:4328`. Its four verified targets
are `$C1:475A`, `$C1:432C`, `$C1:45A0`, and `$C1:475B` for types 0-3.
These are action types, not character or package IDs.

Type 2 reaches `$C1:45A0`. An actor index below three takes the PC reader at
`$C1:45AA`; other actors take the enemy reader at `$C1:4682`. The PC path
uses the existing seven-byte action-config row and resolves its auxiliary
fields before reaching `$C1:4612`. In particular, reads from `$D1:0060`,
`$CD:692C`, and `$CD:656E` have already occurred. A package hook at `$4612`
cannot retrospectively validate or protect those earlier config readers.
An extended config must retain deliberately proved canonical auxiliary
selectors or pass separately adapted readers before this boundary.

The exact candidate span contains `LDA $9877` followed by `ASL A`. The
four-byte instruction-aligned extent can encode a future `JML` without
touching the `TAX` at `$C1:4616`. The address and hash define a candidate,
not authorization to overwrite it. All incoming-control-flow and live-state
checks must precede any production catalog promotion.

On the ordinary path, entry requires native mode, M=0, X=0, D=`$0000`, and
DBR=`$7E`. The battle boot establishes D and DBR, and this PC loader changes
M to 16-bit immediately before the auxiliary reads. Those facts support a
static path argument; the linked native probe records the values for one
ordinary primary invocation, without promoting all possible callers.
The helper entry value of A is the last auxiliary pointer read, not the
package selector. X belongs to that auxiliary lookup; Y must be preserved
unless the selected route deliberately defines its final value.

The selector word at `$7E9877` has a zero high byte on this path: config
clear writes `$9878`, and the PC row copy later writes only the low selector
byte. At `$C1:4093-$409B`, the ordinary caller masks `$AE94` with `$40` and
stores X as a word at `$A0B3`. Thus this producer supplies `$0000` or `$0040`.
The helper's all-256-byte branch matrix is a deliberately broader synthetic
contract, not evidence that vanilla naturally produces every such value.

Two return words remain above SP at entry, on this ordinary path:

| Relative stack position | Expected word or byte | Origin |
| --- | --- | --- |
| SP+1, SP+2 | `$432A` | Return address pushed by indirect JSR at `$C1:4328` |
| SP+3, SP+4 | `$40AF` | Return address pushed by JSR at `$C1:40AD` |
| SP+5 | Saved caller DP `$A4` byte | PHA at `$C1:4092` |

The first two words are stored return addresses; RTS resumes one address
later. These stack observations are expectations for the bounded ordinary
path, not a claim about every possible entry into the routine.

## Canonical and successful continuations

For selectors `$00-$7F`, replay the overwritten `LDA $9877` / `ASL A` and
tail-transfer to `$C1:4616`. Restore all saved caller state before replay;
A and N/Z/C then reflect those two original instructions. Keep the original
root table and parser active. The v0 helper already proves this routing with
synthetic inputs, and the linked clean-ROM capture confirms one ordinary
canonical invocation. The high-selector cartridge path remains uninstalled.

For an explicitly bound high selector, the proposed success entry is
`$C1:4833`. The helper must first satisfy its exact installed-state contract:
root and masks, all ordered word publications, consumed selected-list
cursor, A/B zero, Y=`$0010`, P=`(entry P & $4C) | $23`, D=`$0000`, DBR=`$7E`,
and unchanged return words and SP. This is the state immediately before the
common loader, not the eventual state returned by the entire graphics load.

The common loader uses config `$987A/$987B`, optionally `$987C`, parses
the fixed-bank auxiliary header, decompresses graphics, builds OAM, and
pumps frames during those operations. Its RTS at `$C1:48EB` returns to
`$C1:432B`; that RTS resumes `$C1:40B0`. This return chain is why the helper
must use tail transfers and preserve the original near-call frame. A new
JSL/RTL pairing cannot be substituted without an independently proved
trampoline and stack transformation.

The later direct script dispatcher reads the published three-byte pointer
into DP `$E6-$E8` and uses long-indirect indexed addressing at `$C1:4CC4`.
That is the existing bank-qualified consumer. Source-bank acceptance in the
helper and actual ExHiROM ROM reads are nevertheless unproved: v0 accepts
only `$7E/$7F`, and synthetic WRAM is not cartridge memory.

## Rejection is a separate integration contract

The current refusal tail proves exact context restoration and no published
descriptor output. It does not implement battle-action cancellation.

Three tempting shortcuts are unsupported:

1. Returning the unchanged helper entry context through an RTS leaves M=0.
   The caller and normal common-loader route require M=1. In expanded code,
   RTS also retains the expanded program bank, so the original near-return
   address would be interpreted in the wrong bank unless a bank-correct
   trampoline first restores that context.
2. Jumping directly to `$C1:4833` on refusal runs graphics and auxiliary
   consumers without a successful package installation. No safe error
   meaning for that state has been established.
3. Installing the symbolic package's terminal-only `$00` stream does not
   establish a complete no-op action. `$00` clears its current script active
   flag at `$C1:4CF0-$4CF6`. It does not itself increment `$9876`.

After the load returns, `$C1:40B0-$40D2` pumps frames and scripts until
`$9876` becomes nonzero. The following sequence also waits for `$5D9B` to
clear before restoring the caller's saved `$A4` byte. Another script,
callback, or game state could affect these latches, so the static evidence
does not assert that every terminal-only configuration hangs. It establishes
that terminal closure by itself does not prove action-lifecycle completion.

A later rejection contract must name the exact pre-rejection state,
permitted cleanup writes, width/register state, bank-correct return route,
and completion-latch behavior. It must show that no stale script is run,
no partial graphics state is consumed, no unrelated active owner is cleared,
and no action/queue lifecycle is silently skipped. No such cancellation
adapter is selected or authored here. The next clean-ROM observation should
record the existing completion behavior before choosing one.

## Mapping correction with cited wrong source

`BA-MAP-ACTIVE-OWNER-COUNT-20260908`, evidence `verified-static`.

The pinned upstream
[bank_C1.asm line 9811](https://github.com/dscotton/ct_disassembly/blob/eeae27acdb6565e96d1d796a3d60792c250c0aa1/bank_C1.asm#L9811)
describes `BattleAnim_RunActiveScripts` as running "for 8 slots". That
annotation is wrong for the complete canonical routine at
`$C1:4BBE-$C1:4C9E` (224 bytes, hash above).

The routine contains thirteen distinct active-owner checks: owners
`$00-$04` and `$08-$0F`. Owner `$04` additionally depends on `$AE99|$AE9A`;
`$A3D1` can bypass the eight effect-owner checks. Owners `$05-$07` have no
direct dispatch in this specific routine. The correction is thirteen
possible checked owners with conditional dispatch, not thirteen necessarily
running scripts or thirteen playable characters.

This does not contradict the sixteen-bit descriptor format or the helper's
all-sixteen-owner publication tests. Those prove descriptor transport, while
this consumer has a distinct, narrower dispatch topology. It also does not
prove that owners `$05-$07` are unused globally. The original snapshot stays
unchanged; this correction preserves its exact citation and the independent
canonical evidence instead of silently editing the historical source.

The terminal-only lifecycle finding above is a newly specified limit, not a
correction to the symbolic proof: that proof expressly claims selection,
transport, and stream closure rather than a runnable battle action. The
`$0000/$0040` ordinary flag producer similarly narrows a real caller path;
it does not invalidate the broader synthetic flag tests.

## Placement and interrupts remain independent gates

Use the separate placement/interrupt design for exact proposed names and
geometry. The existing inert scaffold's simple expanded-bank pool is
`$41-$7D`; it excludes the mirrored `$40` bank and WRAM `$7E/$7F`. A proposal
inside that pool is not an approved allocation. The v0 helper's registry,
scratch, synthetic stack, and three synthetic tails are not reusable game
ownership evidence.

The helper temporarily changes DBR, changes arithmetic mode, uses stack and
scratch, and publishes multiple bytes before returning. The existing game's
interrupt handlers save context and establish their own working context,
but every reachable call, scratch access, and publication observer still
needs a closure audit and runtime evidence. Disabling IRQ with SEI would
not disable NMI, and disabling NMI without timing evidence is not an adopted
solution. No real interrupt policy is approved here.

## Next measurable experiment and completion criteria

First run a clean-ROM observation, without code injection, ROM mutation,
CPU-state edits, scratch canaries, or forced flags. Use one existing
reproducible battle setup and recorded inputs; record the actual setup
provenance if a new battle capture must be created.

Capture entry at `$C1:4612`, canonical replay continuation `$C1:4616`,
installer completion `$C1:467F`, common loader `$C1:4833`, return chain
`$C1:48EB/$C1:432B/$C1:40B0`, active-script entry `$C1:4C9E`, and completion
waits `$C1:40CE/$C1:40E7`. At minimum record CPU A/X/Y/P/D/DBR/PBR/SP, the
two return words and saved-byte context, config/branch inputs, masks, exact
ordered pointer/activation writes, and `$9876/$5D9B` transitions. Preserve
all private traces with input, ROM, collector, emulator, and output hashes.

A run that misses an address is an incomplete observation, not a pass. A
naturally observed primary branch proves only that branch; an alternate
branch requires a separately recorded real action context. An injected
alternate flag would be a separate diagnostic and must not be reported as
ordinary play. Native CPU evidence should confirm or correct the static ABI
before a guarded hook experiment is designed.

After that observation, the integration gate still needs source-bank access
proof, approved named code/data placement, scratch/interrupt ownership, and
the explicit refusal/lifecycle contract. Production installation requires
the existing fail-closed complete-diff audit and exact promoted catalogs.
Completing this design alone cannot promote those catalogs.

## Reproducing the static evidence

Read only `private/input/rom_archive/Chrono Trigger (USA).sfc`, validate the
full identity above, and convert each `$C0-$FF` CPU address to file offset
with `address & $3FFFFF`. SHA-256 the half-open span and compare every table
row above. Confirm the annotated source's exact Git commit, clean file
status, and SHA-256 before using its line citations. Reconstruct the two
near-call return words from the instruction lengths and compare the reader,
consumer, and latch branches at their named addresses. Emit only metadata;
keep canonical bytes and any raw trace in ignored private storage.

This pass generated this original design document only. It launched no
emulator, mutated no ROM, and changed no catalog. Its own content hash is
recorded by the parent integration checkpoint, avoiding a self-referential
hash inside the document.
