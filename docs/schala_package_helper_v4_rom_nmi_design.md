# Original ROM helper with real NMI: experiment v4 design

Date: 2026-09-08. Status: source design, before native launch. This is a
separate diagnostic that combines the immutable original-cartridge v3 helper
contract with the real register-edge interrupt observation contract proved by
the separately preserved v2 original-NMI experiment. No prior source or
accepted evidence will be changed.

The exact eight-MiB original cartridge is SHA-256
`1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b`.
The helper executes at `$410000`, using the `$420000` original package fixture
and `$430000` immutable registry. Its exact 577 bytes have SHA-256
`7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b`.
The cartridge's original idle loop is `$008040`, its setup JML bridge is
`$008060`, its NMI handler is `$008080-$00808F`, and its three observation
tails are `$008100/$008110/$008120`. The native NMI vector `$00FFEA` contains
`$8080`. The handler's sixteen bytes have SHA-256
`7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448`.
Its bytes equal the earlier original counter handler, but its execution
addresses and vector are different and must be checked independently.

The launcher will reuse the guarded original-build receipt and exact current
cartridge checks from v3. It will create an isolated runtime/profile and zero
SRAM under a new private run directory. The collector initializes synthetic
WRAM to `$A5`, changes only the two declared selector/branch input words, and
sets declared input CPU registers outside observation. It does not install
WRAM code, change ROM bytes, write interrupt frames, or set internal NMI/PPU
state. The original `$008040` loop supplies natural elapsed emulated time.

The current prerequisite is the corrected
[phase contract v2](mesen_nmi_phase_contract_v2.md), including MAP010's
exclusion of the unavailable `ppu.nmiScanline` field. The collector observes
a false-to-true VBlank latch transition and begins on the next observed
scanline with pending interrupt/DMA state clear. At one named helper
instruction, it writes the real emulated `$4200` register to `$80` through
the debugger memory API. This requests a native hardware NMI after that
instruction completes. It disables the one-shot request at the observed
handler entry. These debugger register events are distinguished from CPU
stores and do not advance the CPU clock themselves.

The pilot has two cases: selector `$80`, primary branch, status `$00`, the
first CountBits JSR, and synthetic entry SP `$1FEF/$06D8`. The proposed
152-case matrix covers five named success boundaries for all four immutable
bindings, both branch values `$00/$40`, and both entry SP values. These are
allocation TCS, first CountBits JSR, release TCS, final PLP, and terminal JML.
The remaining three representative native statuses `$C3/$4C/$8F` also run
at the first JSR for those sixteen binding/branch/stack combinations. Three
route families (canonical selector `$7F`, unsupported selector `$90`, and
immutable unbound selector `$84`) each cover two relevant release/return
boundaries, two SP values and statuses `$00/$8F`. This is 80 + 48 + 24 cases.
It is an explicitly selected boundary matrix, not every-instruction or
every-status preemption coverage. Both empty-branch fixtures are included.

The exact success sites and continuations derive from the current ROM bytes:

| Boundary | Trigger | Interrupted continuation | Helper depth before / after |
| --- | --- | --- | --- |
| Allocate TCS | `$410043` | `$410044` | 8 / 50 |
| First CountBits JSR | `$4100EE` | `$410232` | 50 / 52 |
| Release TCS | `$410215` | `$410216` | 50 / 8 |
| Restore P | `$41021A` | `$41021B` | 1 / 0 |
| Success JML | `$41021B` | `$008110` | 0 / 0 |

Canonical PLP/JML are `$410019/$41001E`; early-refusal PLP/JML are
`$41022D/$41022E`; framed-refusal TCS/JML are `$410226/$41022E`.
The exact instruction bytes must derive each continuation before launch.
The deepest tested combined frame is 52 helper bytes plus four native
hardware bytes plus three handler bytes, 59 total. No low-SP fixtures are
included because they do not reserve this interrupt space.

Acceptance requires the full ordered event stream, exact native four-byte
hardware stack writes and real `$FFEA/$FFEB` vector reads, all nine handler
instruction observations and fourteen handler memory operations, entry-P
transformation, one counter increment with readback, and exact CPU state
restored by the actual RTI. It checks the interrupted PBR `$41` inside the
helper and PBR `$00` after the terminal JML. TCS's pending-NMI conditional
idle read and subsequent interrupt dummy read remain distinct, with their
respective SP and pending-NMI states. Every execution value is labeled a
pre-execution debugger opcode peek, not an independent opcode bus fetch.

Every CPU read must belong to an exact immutable input span, the declared
pointwise stack, the handler counter, or a specifically owned native
interrupt operation. Every write must belong to declared outputs, stack, or
counter. The complete final 128-KiB WRAM diff must equal the final CPU-write
ledger, including retired stack bytes. Exact ROM registry/payload snapshots
before and after observation must agree with the verified cartridge.
Only after that native full-ledger check may a clearly labeled helper-only
projection remove interrupt operations and pass the unchanged v3 validator,
including exact opcode peeks, ordered ROM reads, outputs, CPU and live-stack
ownership. The projection's derived diff is not the native WRAM diff.

Host tests must reject the old `$7F` helper PBR, old `$8020` handler/vector,
missing/wrong hardware stack writes, collapsed TCS reads, detached RTI,
unexplained WRAM changes, retired-scratch or out-of-span ROM reads, altered
immutable inputs, and source/archive drift. Every dependency and transitive
fixture/policy source used by launch is archived before execution and checked
again afterward, alongside the immutable staged cartridge and SRAM. Accepted
evidence needs two fresh source-frozen matrices and independent review.

This experiment cannot approve Chrono Trigger's larger NMI/IRQ closure, a game
resolver hook, physical game stack ownership, an allocation, action effects,
save safety, or logical PC `$07`. It isolates original ROM execution and a
specific original native NMI handler under the declared synthetic fixtures.
