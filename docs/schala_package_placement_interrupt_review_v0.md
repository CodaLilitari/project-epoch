# Package-helper placement and interrupt review v0

Date: 2026-09-08. Gate: `BA-NATIVE-INTEGRATION-DESIGN`.
Status: design reviewed; installation remains gated.
Evidence: `verified-static` for the pinned source, canonical instruction spans,
and candidate allocation geometry below; `hypothesis` for proposed placement
and production integration. No emulator was launched for this review.

Subsequent evidence: the separate
[primary resolver observation](schala_package_resolver_observation_v0.md)
now records ordinary entry SP `$06D8` and its expected return chain twice.
It does not establish maximum stack depth, interrupt nesting, scratch
ownership, or expanded-ROM helper behavior. The original review and its
remaining proof requirements below retain that distinction.

## Decision and scope

Keep the completed 537-byte synthetic helper and its three native runs intact.
Define a separate ROM-capable helper version after the live resolver observer
establishes its actual calling context. The current helper explicitly accepts
only bank words `$007E/$007F`, so changing a registry bank to `$43` cannot make
it read expanded ROM. That rejection is deliberate, not a mapping defect.

Use candidate code space in bank `$41` and package metadata in bank `$43`.
Keep production scratch unbound. In particular, the synthetic `$7E4000`
workspace collides with a proved vanilla menu write and must not become a
persistent game allocation. The synthetic stack origin is also unrelated to
the game's reset stack.

This review changes no production catalog, selector binding, ROM, patch,
save, state, or upstream disassembly. It does not repeat the completed
synthetic matrix or the canonical command census.

## Named candidate expanded spans

`tools/schala_rom_scaffold.py` defines the simple full-bank pool as file/CPU
`$410000-$7E0000`, with the end exclusive. Bank `$40` is the protected boot
and low-bank data mirror; file `$7E0000-$800000` is excluded because CPU
banks `$7E/$7F` are WRAM. The pool is a geometric envelope, not granted
ownership of every byte in it.

The following five records pass `validate_allocations` together, including
alignment, non-overlap, bank boundaries, and address translation at both
ends. Their evidence field is `hypothesis`, owner is
`battle-package-integration-design`, and `no_bank_cross` is true. They consume
1,257 candidate bytes. Every range in this table is half-open.

| Candidate ID | File and canonical CPU span | Size | Kind / alignment | Purpose |
| --- | --- | --- | --- | --- |
| `pe.ba.helper.code.v1-candidate` | `$410000-$410400` | `$400` | code / `$100` | Bounded capacity for the next original helper, including its entry dispatch. The next assembly must fit; this does not assert that it will remain 537 bytes. |
| `pe.ba.helper.refusal.v1-candidate` | `$410400-$410480` | `$80` | reserved / `$80` | Separate capacity for the eventual proved refusal continuation. No refusal behavior or code is assigned here. |
| `pe.ba.package.registry.v1-candidate` | `$430000-$430060` | `$60` | table / 2 | Sixteen six-byte records under the current registry shape. An immutable ROM registry removes the synthetic `$7E3000` fixture from the proposed live design. |
| `pe.ba.package80.descriptor.v1-candidate` | `$430100-$430108` | 8 | table / 2 | One deliberately authored two-mask, repeated-pointer test descriptor. |
| `pe.ba.package80.stream.v1-candidate` | `$430200-$430201` | 1 | table / 1 | One original terminal-only stream, for a later bounded integration diagnostic. |

These names are review coordinates, not entries in
`APPROVED_PRODUCTION_ALLOCATIONS`. Both trusted production catalogs remain
empty in `tools/validate_rom_write_intents.py`. A candidate record accepted by
the scaffold geometry validator is still rejected as an untrusted production
allocation by the write-intent guard. No payload hash or consuming hook is
approved by this table.

The bank choice follows the existing coarse plan in
`schala_rom_expansion_architecture.md`: `$41` for runtime adapters and `$43`
for command-related tables. It deliberately differs from the symbolic
fixture's bank `$42`; fixture addresses never established ownership. Moving
that original test package requires re-encoding its deliberate bank-qualified
binding and pointers, then passing the existing descriptor/stream policy.
It must not silently relocate canonical auxiliary-reader values or assign
Schala action semantics to the donor row.

Before installation, the next source must accept only deliberately allowed
ROM source banks and require its source records to belong to named spans.
The package must pass the pinned command grammar, both masks, shared/suffix
entrypoints, disjoint ownership, decoded `$1E` exclusion, and terminal `$00`
requirements. Merely accepting all banks `$41-$7D` is not an ownership check.

## Scratch and stack evidence

The synthetic runner declares scratch `$7E4000-$7E4080`. The original helper
currently references scratch offsets `$00-$21`; `$80` is the harness's
allowed window, not proof that all 128 bytes are needed or that any are free
in the game. It additionally writes DP `$80-$83` and the established resolver
publication fields. Those existing output fields do not authorize another
temporary workspace.

Two canonical code sites give positive contrary evidence against treating
`$7E4000` as globally free:

* At `$C2:9B40-$C2:9B4B`, the menu loads X=`$3E00`, Y=`$3E80`, and
  A=`$077F`, then executes `MVN $7E,$7E`. The resulting 1,920 destination
  bytes are `$7E3E80-$7E45FF`, inclusive. They cover the entire synthetic
  scratch window.
* At `$C2:298C-$C2:2996`, the overworld loader explicitly sets destination
  offset `$4000` and bank `$7E`; its following code calls the decompressor.
  This pins a second context using that address without asserting an audited
  full decompression extent here.

These findings refine the existing synthetic-only restriction; they do not
contradict the helper's successful synthetic tests. A future battle-local
reuse proposal would need a lifetime proof covering retained field/menu data,
all interrupt consumers, and restoration before leaving the battle context.
An unchanged canary during one battle would not establish that lifetime.

The synthetic SP is `$1FEF`, with ten allowed bytes below and including its
next push address. Canonical reset code `$FD:C000-$FD:C007` instead initializes
SP to `$06FF`. Reset does not establish the later resolver's exact SP or the
lowest live stack boundary. The live observer must record that boundary at
the actual indirect-call frame and measure additional interrupt/callee depth.

The current helper's extra maximum is ten bytes after entry: eight saved
context bytes plus its deepest two-byte local `JSR`. The original caller's
return frame is already above entry SP. A native interrupt adds its four-byte
hardware frame and the inspected battle handler saves nine register bytes;
temporary pushes, interrupt callees, and possible nesting add further depth.
Thirteen interrupt bytes is therefore a starting contribution, not a proved
maximum. The instruction semantics are documented in WDC's
[W65C816S datasheet, sections 2.18, 3.2, and 7.1](https://www.wdc65xx.com/wdc/documentation/w65c816s.pdf).

A stack-relative local frame is a possible later alternative to global
scratch, but it would require a new source implementation and actual stack
headroom evidence. This review does not choose a live scratch address or
authorize a stack-frame rewrite.

## Exact interrupt context established statically

Canonical stubs `$00:FF10` and `$00:FF14` transfer through WRAM `$000500` and
`$000504`. Battle initialization at `$D1:F1B0-$D1:F1D6` installs long-jump
targets `$D1:E77C` for NMI and `$D1:FE97` for IRQ. This explains why a future
observer must snapshot the current WRAM trampolines rather than assume that
the vector label identifies the current handler in every game mode.

The normal battle NMI prologue saves A, X, Y, DBR, and D after selecting
16-bit register widths. It sets D to zero and uses long or direct-page
accesses before `MVN $7E,$7E` at `$D1:E7AC` establishes DBR=`$7E`. Its busy
guard branches directly to the restore sequence at `$D1:E891`. The normal
epilogue restores D, DBR, Y, X, A, then executes RTI at `$D1:E898`.

The battle IRQ at `$D1:FE97` likewise saves those registers and establishes
D=0. Its initial accesses are direct-page or long until it explicitly selects
DBR=0 at `$D1:FEB4`. Later branches either select DBR=`$7E` for the display
configuration call or use a long access before the field DMA service. The
epilogue restores the saved context and executes RTI at `$D1:FEF3`.

These entry sequences do not immediately misinterpret the helper's temporary
source DBR. In native mode an interrupt does not automatically reset DBR;
`MVN` assigns its destination bank to DBR. Those CPU rules are documented in
[WDC sections 7.11 and 7.18](https://www.wdc65xx.com/wdc/documentation/w65c816s.pdf).
The register saves are positive evidence, but they do not prove the complete
interrupt call tree leaves helper scratch, DP `$80-$83`, or partially
published owner state untouched.

An alternate handler begins at `$D1:F4C0`, saves the same context, sets D=0,
and calls services before explicitly selecting DBR=`$7E` at `$D1:F4F4`.
Its restore/RTI ends at `$D1:F558`. This review does not establish whether
that handler can be active at the resolver candidate. Its called services
must not be assumed independent of incoming DBR merely from its prologue.

The normal NMI explicitly saves/restores only DP `$00-$2A` through block
moves to `$7ECC65`; this is not a blanket preservation promise for all direct
page. Called services and alternate dispatch branches remain a separate
closure and runtime gate. The current helper also performs validation before
its first publication, which changes the duration and ordering of intermediate
states. Final-state synthetic equivalence alone does not settle who can
observe those intermediate states.

## Read-only Mesen observation: what it can and cannot settle

The existing project MCP bridge proves one fixed field-checkpoint observation.
Its six exposed operations do not supply a battle input replay or arbitrary
execution callbacks. Preserve that surface. A separate bounded collector can
use the established hidden Mesen launcher and an exact disposable battle
checkpoint, with no ROM/WRAM/state mutation by the observer.

The first observation should record, for every bounded resolver invocation:

1. Entry at `$C1:4612`, canonical continuation, parser exit, common loader,
   and return to the actual caller; record A/X/Y/P/DBR/D/SP, the original
   return bytes, selector/config identity, and the branch word.
2. Current `$000500-$000507` trampoline bytes and every actual interrupt
   entry/return occurring in that window, with nesting and stack minima.
3. Ordered accesses to DP `$80-$83`, root/branch fields, owner publication
   fields, and any explicitly proposed scratch span. Attribute accesses to
   the main call versus an interrupt context.
4. Frame/scanline or cycle timestamps, overflow/dropped-record counters,
   immutable input identities, and a repeatable bounded input schedule.

A successful read-only trace can establish the observed caller ABI, live
handler selection, stack headroom for that execution, and concrete conflicting
memory users. It cannot execute an absent high selector, show reads from
uninstalled expanded data, inject interruptions at every helper boundary, or
prove a finite collection of untouched bytes is globally free. After design,
the ROM-capable version still needs targeted expanded-read and interruption
tests, followed by the separately guarded game installation.

## Contradictions and corrections to earlier guidance

One architecture instruction is too broad. At project commit
`a01ab3af3ab2c1c1d22c24828ac0ad51ed5d0c84`,
`docs/schala_rom_expansion_architecture.md`, under "Pointer and code rules",
says: "Use `JSL/RTL` for cross-bank runtime helpers."

That is appropriate for a new paired long call, but it is not the calling
convention of this intercepted resolver. The source adapter identifies an
existing bank-local indirect-`JSR` frame at `$C1:4612`; the current helper
preserves it and uses `JML` tails. An unconditional `RTL` would consume a
different return-frame shape. Correct guidance must distinguish paired
`JSL/RTL` calls from `JML` entry/tail transfers that retain an existing frame.
See `schala_player_tech_package_bank_adapter_v0.md`, "Candidate helper ABI",
and `asm/schala_package_helper_v0.asm`, canonical/success/refusal exits.

No additional contradiction of the canonical character-data mapping was
found in this bounded placement review. The scratch collisions and reset SP
are newly pinned constraints; they must not be reported as failures of an
earlier claim of game ownership, since that ownership was explicitly absent.

## Evidence provenance and reproduction

Canonical input is the private headerless US Rev0 ROM, 4,194,304 bytes,
SHA-256 `06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
Its identity was checked before reading the spans below. No bytes were
exported into this document. Each span is half-open and has a SHA-256 of the
exact canonical bytes.

| Role | CPU span | Bytes | SHA-256 |
| --- | --- | --- | --- |
| Native trampolines | `$C0FF10-$C0FF18` | 8 | `f3288e3ad2ccd368f44986d97c03a675641cdf43e7fd8a4b7bcbd886f6464f09` |
| Battle vector installation | `$D1F1B0-$D1F1D7` | 39 | `e44fbe1c3ced6fd6730f1c09bfab3e2220cd022777d80f64493202e43d70b21e` |
| Normal NMI prologue | `$D1E77C-$D1E7CC` | 80 | `0ee3b242e1811ef61c9402abe32a50c0a6fb6b0461bb4c3c72e7e624cc874ea3` |
| Normal NMI epilogue | `$D1E87A-$D1E899` | 31 | `3506d00fa4aa18ee5c9c49efc33ee2aa5253a0571cf0bbf77270eb176e5237dd` |
| Battle IRQ | `$D1FE97-$D1FEF4` | 93 | `cc06d1d9a49444be184db23bce01e1552c68497b288589d9f3d6475308942633` |
| Alternate NMI prologue | `$D1F4C0-$D1F4F5` | 53 | `79a16c51f1a3a18a4203b76372c66956a4a11645ba644b9324f697a0a491f883` |
| Alternate NMI epilogue | `$D1F551-$D1F559` | 8 | `210a63f913857e3046eeb3f40b5d09f3ef8f0776c926081ae5f1b9e3c74178ea` |
| Menu scratch collision | `$C29B40-$C29B4C` | 12 | `338a80c89593f32eeeb4c666e399c60eeb8ef6605dd1326f52c3a75ab4c95395` |
| Overworld destination | `$C2298C-$C22997` | 11 | `f014459c9a5df222b1f0e19e97b43d048e76d48169f7a1ba48697381e180e0a9` |
| Reset stack | `$FDC000-$FDC008` | 8 | `2a6477619775f64770cf7050c5801f42470de5649cb17081a0d40c746792eca0` |

Instruction interpretation was checked against the local, private
`dscotton/ct_disassembly` checkout at commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`. All annotated bytes in these
intervals match the canonical ROM. The normal NMI interval has one unannotated
three-byte `JMP $E891` at `$D1:E79C`, which was decoded and checked directly
against the ROM; it is not an annotation mismatch. This is a bounded
comparison, not an assertion that the whole upstream disassembly is complete
or correct.

Additional source identities inspected:

| Source | SHA-256 |
| --- | --- |
| `tools/schala_rom_scaffold.py` | `a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a` |
| `tools/validate_rom_write_intents.py` | `418d958b32206945a91f15fcbcf13c932970b23d60e07cfde1dd2d027ecd3978` |
| `asm/schala_package_helper_v0.asm` | `26987977881f24cbe234262f59c4a3f8de438e4bde3eb053375f0f29ae436f80` |
| Private upstream `bank_D1.asm` | `020f6df9efd22cc12a35608da6523b5d2e5d76d965d94567e0b74d50ab9eacea` |
| Private upstream `bank_C0.asm` | `b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8` |

The scaffold was last changed at project commit
`a01ab3af3ab2c1c1d22c24828ac0ad51ed5d0c84`; the write-intent guard at
`04481c7c3afed3940b068e88b4e33408626f7a18`. This report's final file hash
belongs in the current integration checkpoint, rather than editing the
historical native-conformance checkpoint.

To reproduce the span hashes, first require the full canonical SHA-256 above,
translate a CPU address in `$C0-$FF` to file offset `address - $C00000`, and
hash each exact half-open slice in the table. Do not substitute a patched ROM
or a headered image. Compare upstream instruction annotations only inside
the listed intervals and decode the stated unannotated jump separately.

To reproduce candidate geometry without loading a ROM, instantiate the five
`schala_rom_scaffold.Allocation` records in the candidate table with the
documented owner/evidence, run `validate_allocations`, and check
`exhirom_snes_to_file` for the first and last byte of each. The result on
2026-09-08 is five valid candidate records, 1,257 bytes, zero overlaps, and
zero production catalog entries. This review's checks are read-only and
require no new full synthetic-emulator run.
