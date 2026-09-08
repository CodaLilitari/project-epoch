# v2 stack helper: original interrupt fixture preparation

Status: prepared design only, `hypothesis`, 2026-09-08. The normal v2
conformance harness disables IRQ/NMI. This document records a bounded next
experiment; no interrupt was injected or accepted as evidence here.

## Reuse the unchanged original carrier

The existing original SHA benchmark already contains a minimal NMI handler
and an RTI-only IRQ handler. A future interrupt experiment can reuse those
bytes without changing a ROM or importing a Chrono Trigger handler. The
carrier remains eight MiB with SHA-256
`e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd`.

A read-only check of that exact carrier found:

| Role | Exact pinned location | Result |
| --- | --- | --- |
| Native NMI vector | File `$40FFEA-$40FFEC`, mirrored header copy `$00FFEA-$00FFEC` | Both select CPU `$008020`. |
| Native IRQ vector | File `$40FFEE-$40FFF0`, mirrored header copy `$00FFEE-$00FFF0` | Both select CPU `$008030`. |
| Original NMI code | CPU `$008020-$008030`, file `$408020-$408030` | 16 bytes, SHA-256 `7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448`. |
| Original IRQ code | CPU `$008030-$008031`, file `$408030-$408031` | One RTI byte, SHA-256 `c3641f8544d7c02f3580b07c0f9887f0c6a27ff5ab1d4a3e29caf197cfc299ae`. |

The corresponding original source is
`asm/schala_sidecar_sha256_profile1_benchmark.asm`, SHA-256
`1f8a9a1bce6320d8571389aa6b81e054151d24d3dc561e0ea6968d2a95d7e7f2`.
Its NMI performs PHP, selects a 16-bit accumulator, saves A, increments the
long-addressed word `$7E5EF0`, restores A and P, then RTI. It does not use
helper locals, D-relative addressing, DBR-relative data, X, or Y. The IRQ
contains only RTI. This is a bounded static inventory of original diagnostic
code, not a whole-carrier rebuild or a game interrupt proof.

Under native interrupt entry rules, the proposed minimal NMI contribution
is four hardware-frame bytes plus three explicitly saved bytes; the proposed
IRQ contribution is the four hardware-frame bytes. The experiment must
measure those depths and the restored CPU state rather than infer runtime
success from the arithmetic. No nested-interrupt behavior is selected yet.

## Keep the experiment separately numbered

Preserve all normal v2 sources, accepted runs, hashes, and disabled-interrupt
claims. Use a separate collector/protocol and evidence reference for the
interrupt variant. Its source bytes may reuse the unchanged helper binary,
but its handler, injection mechanism, read/write allowances, and trace scope
are different evidence.

Before execution, establish a documented, reproducible Mesen mechanism that
causes a real native interrupt entry at a selected boundary. A direct edit of
SP/PC plus a fabricated return frame would be a different synthetic mechanism
and must not be reported as hardware entry. Do not assume that an undocumented
`setState` property delivers an NMI or that changing `$4200` at an arbitrary
PPU phase produces the intended event. Record the selected mechanism and
its independently observed vector fetch, stack frame, handler entry, and RTI.

Use only the synthetic SP `$1FEF` and SP `$06D8` placements initially. The
normal helper's low-SP boundary cases demonstrate no interrupt reserve and
must be excluded. At the helper's deepest 52-byte point, a further seven-byte
minimal NMI would reach entry SP minus 59: `$1FB4` or `$069D` for those two
fixtures. This arithmetic supplies test expectations, not game stack-floor
ownership. The independently reviewed real-game 35-byte IRQ and unresolved
normal-NMI paths are separate contracts.

## Boundary matrix

The future native fixture should pause at exact assembled instruction
boundaries and request one interrupt at a time, covering:

1. Before the first helper PHP; after all context saves; before and after the
   allocating TCS. Initial eight-push safety remains a caller precondition.
2. Both CountBits entries, where the local JSR reaches the deepest normal
   helper stack; both source banks; each descriptor branch.
3. After the source-bank PHA and after its matching PLB, preserving temporary
   DBR and the current saved/frame state.
4. Pointer preflight, including a refusal caused by the unselected branch;
   the last successful preflight before any publication.
5. Each publication instruction boundary: activation word, direct offset,
   and bank word. CPU interrupt boundaries are not automatically byte-level
   interruption points inside a word store.
6. Before and after staging saved P/X/Y/A; before and after releasing TCS;
   between each register/status pull; immediately before the final JML.
7. Unframed refusal, framed refusal, canonical bypass, and success, including
   incoming decimal and interrupt-mask flags and the success M=1 tail state.

The original minimal NMI does not read owner publications. Passing its
preemption matrix would establish frame/register survivability under that
handler, not atomic visibility to the real game's NMI services.

## Required acceptance evidence

Keep every observed helper PC, expand the execution whitelist only by the
exact pinned handler instructions and explicit interrupt boundaries, and
record every vector read, hardware-stack write, handler instruction, and RTI
continuation. The resumed helper must finish at the expected tail with exact
A/X/Y/P/DBR/D/SP and the existing ordered publication contract.

Retain pointwise stack access and SP evidence. The additional allowed writes
are only the actual native interrupt frame, the handler's declared three
NMI save bytes, and `$7E5EF0-$7E5EF2` for the NMI counter. Prove the counter's
expected single increment, preserve surrounding guards, and preserve the
complete registry/target inputs and retired `$7E4000-$7E4080` scratch. A
complete WRAM diff must account for every changed byte.

At frame release, an interrupt may reuse the now-released local bytes. The
success outputs must already reside in their saved slots; a later read from
released locals is a failure even if the unpreempted run happened to retain
those bytes. Compare resumed results with the matching normal v2 case and
retain repeated traces and all source/carrier/runtime identities.

This prepared experiment supplies no authorization for an actual game hook,
production allocation, global scratch claim, save behavior, Schala command
binding, or logical PC `$07` runtime integration.
