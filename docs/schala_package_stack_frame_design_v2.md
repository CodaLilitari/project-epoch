# Package helper v2 stack-frame design

Status: source design, `hypothesis`, 2026-09-08. This document defines a
reviewable next implementation. It is not an assembled helper, a runtime
result, or approval to use the game's stack, hook, or production ROM.

The recommended first implementation uses **42 bytes of stack-relative
locals**, preserves D unchanged, and retains the original eight-byte context
save. Its deepest existing local JSR brings the maximum additional depth to
52 bytes below helper entry SP. A direct-page frame is viable but requires
two more saved bytes and an additional interrupt-facing D contract.

## Why stack-relative addressing fits this source

The frozen v1 ROM-source helper has 42 scratch bytes, offsets `$00-$29`.
Its 66 scratch references consist of 29 `LDA`, 29 `STA`, three `ADC`, and
five `CMP` operations. There is no scratch `LDX`, `STX`, `INC`, or `DEC`
operation requiring an indirect rewrite. All four operations have a native
`d,S` form. Stack-relative addressing uses bank zero and an unsigned
eight-bit offset from S; direct-page addressing similarly uses bank zero
but adds D and incurs a penalty when D is not page-aligned. These CPU rules
are documented in WDC's [W65C816S datasheet, sections 3.5.17, 3.5.23 and
opcode tables](https://www.wdc65xx.com/wdc/documentation/w65c816s.pdf).

The helper's `CountBits` routine accesses only registers and makes no local
frame access. The source-bank switch performs its local read before PHA,
then PLB immediately restores the base stack depth. It performs no local
access between those two instructions. Those properties permit constant
stack-relative local offsets in the body without assuming that every
possible future callee has the same property.

The recommendation is specific to
`asm/schala_package_helper_v1_rom_source.asm`, SHA-256
`0a71029770a494707cc03eae6d80461de6de3a30544dc01cc632bf82d1079e9b`.
The original v0 helper used 34 scratch bytes; its 44-byte planning example
must not be copied to this larger v1-derived frame.

## Preferred frame: S-relative, unchanged D

Keep the incoming ABI: native mode, M=0/X=0, D=`$0000`, DBR=`$7E`, and an
existing return frame retained by JML entry/tails. Save the original
`PHP/PHA/PHX/PHY/PHB` context before changing flags. Canonical selectors
should take the existing bypass without allocating locals or inspecting
the registry/branch word.

Allocate the frame only after the early high-selector and branch-word
checks pass. Clear the decimal flag **before** using SBC to reserve the
frame. Incoming status values include decimal mode in the current test
matrix; the saved PHP byte is still the authoritative original status.

At the body base, SP is `entry_SP - $32`: eight saved bytes plus `$2A`
local bytes. Local offset N lives at `$01+N,S`. The frame is:

| Body S-relative byte offsets | Contents |
| --- | --- |
| `$01-$2A` | 42 local bytes, corresponding to v1 offsets `$00-$29` |
| `$2B` | Saved DBR |
| `$2C-$2D` | Saved Y, low then high |
| `$2E-$2F` | Saved X, low then high |
| `$30-$31` | Saved A, low then high |
| `$32` | Saved P |
| `$33` onward | The caller's pre-existing stack contents; never helper locals |

For example, the v1 local cursor at offset `$12` becomes `$13,S`, and
the local saved-status copy at `$1A` becomes `$1B,S`. Read original P
from `$32,S` after allocation. The working frame's maximum offset is only
`$32`, comfortably within the native unsigned byte displacement; this is
an encoding observation, not a guarantee of valid physical stack memory.

Conceptual prologue after saving eight context bytes and passing early
checks:

```asm
; Native M=0. The saved PHP byte still contains the entry decimal flag.
CLD
TSC
SEC
SBC.w #$002A
TCS
; Body local N is now accessed as $01+N,S.
```

Only the original locals move. Reads of descriptor data still use the
selected source DBR, registry/target reads remain explicitly qualified, and
all existing engine publications must retain their explicit addresses.
In particular, `$7E0080/$7E0082` are outputs, not new frame offsets.

### Exact exits

Use two visibly distinct refusal exits. A refusal before allocation restores
the original eight context bytes directly. A refusal after allocation adds
`$2A` to S, then reaches that same eight-byte restore. Routing one class to
the other is a frame-corruption bug even if both labels ultimately use JML.
Macros should name their intended refusal target explicitly or belong to
clearly separate before/after-allocation families.

For success, write the intended return register values into their saved
slots **before releasing the locals**:

| Saved slot | Success value |
| --- | --- |
| `$2E,S` word | Final descriptor cursor, including the established 16-bit wrap |
| `$2C,S` word | `$0010` |
| `$30,S` word | `$0000` |
| `$32,S` byte | `(entry_P & $4C) | $23` |

Then reserve no further temporary state: set M=0, use binary arithmetic to
add `$2A` to S, and execute `PLB/PLY/PLX/PLA/PLP` before the success JML.
This differs deliberately from v1's final read of its global cursor after
restoring registers. Reading a local cursor after releasing the frame
would read memory that an interrupt is allowed to reuse. Returning X via
its saved slot avoids that lifetime error.

Refusal leaves the saved register/status slots unchanged. Canonical bypass
also restores them unchanged, then reproduces the displaced `LDA/ASL`
and jumps to its established canonical continuation. No new long return
instruction should be introduced into the retained near-call frame.

The body reserves 50 bytes including saves. Its local JSR uses two more,
for a 52-byte maximum. The single-byte bank PHA is shallower. Canonical
bypass and early refusal remain at eight saved bytes rather than paying
for the full body frame.

## Alternative frame: D points to allocated stack locals

The alternative adds PHD to the eight context saves, reserves 42 bytes,
and sets D to `S+1`. Existing local offsets can then use direct-page
addressing without a `+1` translation. Engine outputs still need their
explicit long addresses. The saved layout relative to D is:

| D-relative byte offsets | Contents |
| --- | --- |
| `$00-$29` | 42 locals |
| `$2A-$2B` | Saved D, low then high |
| `$2C` | Saved DBR |
| `$2D-$2E` | Saved Y |
| `$2F-$30` | Saved X |
| `$31-$32` | Saved A |
| `$33` | Saved P |

After releasing the frame, PLD must precede restoration of DBR/Y/X/A/P.
The main helper uses 52 bytes including saved context; `CountBits` makes
its maximum 54. This does not count hardware interrupt entry.

The normal battle NMI and IRQ prologues save incoming D, assign D=0 for
their services, and restore incoming D. That is positive static evidence
for this alternative. It does not substitute for testing interruptions
when D actually points into a helper frame, or for proving every handler
that may be installed during the helper lifetime. The latest ordinary
resolver observation begins with D=0 and cannot alone prove preservation
of the proposed nonzero D value.

The D-relative alternative can become more attractive if a future immutable
ROM registry reader truly needs direct-page indirect addressing. That is a
new design requirement; it is not present in the current v1 source.

## Stack budget comparison and limits

| Design | Locals | Saved context | Deepest local call | Additional helper depth |
| --- | ---: | ---: | ---: | ---: |
| Current v1 global scratch | 0 on stack | 8 | 2 | 10 |
| Proposed S-relative locals | 42 | 8 | 2 | 52 |
| Proposed D-relative locals | 42 | 10 | 2 | 54 |

For the checkpoint's observed entry SP `$06D8`, the S-relative body's
base S would be `$06A6`, and its deepest local JSR would reach `$06A4`.
Adding the independently closed non-nested IRQ contribution of 35 bytes
would reach `$0681`. A guarded short NMI nested at that exact IRQ peak
would reach `$0674`. The D-relative version is two bytes deeper at every
corresponding point.

Those addresses are arithmetic planning results. No document here has
declared `$0674` a safe game stack floor. Normal NMI already has a separately
identified 40-byte conditional path, and its complete service tree and
nesting behavior remain unresolved. See the
[interrupt closure report](schala_package_interrupt_closure_v1.md).

Both proposals need a caller guarantee that the entire frame and interrupt
reserve are backed by writable stack memory. Bank-zero stack-relative
addressing is not interchangeable with arbitrary `$7E` WRAM placement.
The synthetic fixture and eventual game entry must each prove their own
range. A prologue cannot rescue an invalid incoming stack merely by
checking it after its first pushes.

## Required diagnostic evidence before adoption

The next source version should preserve v0 and v1 and receive its own
binary, source and evidence identities. Its initial synthetic matrix must
check:

1. Canonical bypass, every early refusal, every framed refusal, and both
   successful branch routes; all accepted native-width status values,
   especially incoming decimal mode.
2. Final A/X/Y/P/DBR/D/SP, exact ordered owner-publication bytes, unchanged
   immutable registry/targets/source bytes, full WRAM differences, and no
   access to the retired global scratch span.
3. Stack writes restricted to the exact save/local/local-call interval;
   guards and the pre-existing caller frame intact; no local access after
   frame release; explicit allowed execution code/tail spans.
4. At least the existing synthetic stack placement and a separate placement
   numerically matching the observed game SP, each in a wholly synthetic
   fixture. Matching the number `$06D8` does not make it a game test.
5. Deliberate interruption at allocation/deallocation, bank-switch, pointer
   validation, and publication boundaries using an independently scoped
   interrupt fixture. The fixture must itself have known stack, register,
   scratch, read/write and entry/RTI contracts.

The first four items can establish source and synthetic CPU behavior. Item
five must distinguish an original interrupt fixture from execution of actual
game handlers. Even passing all five does not close real normal-NMI service
ownership, action cancellation, a ROM registry certificate, production
allocation, or the guarded game hook.

The source inventory and frame arithmetic in this document were reviewed
directly; no helper was assembled or emulator run for this design. To
reproduce the inventory, find `PE_PH1_SCRATCH` references in the pinned v1
source and group the 66 executable references by mnemonic. To reproduce
the layout, begin at entry S, apply the native push widths in the stated
order, subtract `$2A`, and verify each local/saved byte against the tables.
