# Logical PC `$07` Attack adapter audit

Status: `verified-static` for the five canonical table boundaries below and
`verified-runtime` only for the accepted Crono critical-Attack route. No hook,
expanded allocation, ROM mutation, patch, or logical-PC-`$07` execution is
approved by this audit.

## Why an adapter is mandatory

Vanilla Attack dispatch uses the logical PC ID as a direct one-byte index. The
relevant consumers do not mask `$07`, rewrite it to a vanilla ID, or check the
table length first. Four tables contain only seven PC entries, so an eighth
lookup reads the next table or record. The remaining table has an eighth byte,
but that byte is already occupied and changes approach behavior.

| Consumer | Canonical extent | Logical PC `$07` result | Consequence |
| --- | --- | --- | --- |
| basic Attack action ID at `$CC:2583` | seven bytes through `$CC:2589` | `$CC:258A`, the first HP-growth byte | Fallthrough collision; the basic-action table cannot be extended in place. |
| approach policy at `$CC:F63C` | eight bytes through `$CC:F643` | occupied value `$FF` at `$CC:F643` | In bounds but not free; its nonzero branch forces the pathfind route. |
| Attack animation family A at `$CD:4000` | seven bytes through `$CD:4006` | `$CD:4007`, entry 0 of the next selector family | Fallthrough collision. |
| pathfind-success animation family at `$CD:4007` | seven bytes through `$CD:400D` | `$CD:400E`, Crono's critical selector | Fallthrough collision with active vanilla behavior. |
| critical animation family B at `$CD:400E` | seven bytes through `$CD:4014` | `$CD:4015`, the following normal-Attack configuration record | Fallthrough collision. |

The `$CC:F63C` table is indexed by logical PC ID, not by a separate sprite
source index. Its common melee-versus-ranged interpretation remains a
hypothesis; only the direct index and zero-versus-nonzero branch behavior are
proved here.

## Runtime bridge

The accepted native-Mesen recovery trace makes one part of this static chain
concrete:

- Crono's queued Attack has `$AE9B` bit `$80` set at frame 375, identifying a
  critical outcome.
- At frame 377, the only watched callbacks are reads of roster byte
  `$7E2980=$00`, advancing to `$C1:4A43` and `$C1:438A`.
- The latter route selects `$CD:400E[0]`. Therefore file byte `$0D400E` is
  actively used by Crono's critical Attack and cannot be repurposed as a PC
  `$07` normal-Attack byte.

This runtime evidence covers one Crono critical Attack only. It does not cover
noncritical Attack, attacks by the other PCs, or an actual logical PC `$07`.

## Required implementation shape

A production PC `$07` Attack implementation needs all of these adapters:

1. Preserve the seven vanilla results at the basic-action consumer near
   `$C1:BFFF`, while resolving a separately authored action ID for `$07`.
2. Preserve the eight occupied vanilla approach-policy bytes at the consumer
   near `$C1:4A44`, while resolving Schala's deliberate policy independently.
3. Preserve all three seven-entry animation-selector families at consumers
   near `$C1:438B`, `$C1:43C4`, and `$C1:43F8`, while resolving `$07` from
   named expanded data.
4. Keep the new descriptors in source-controlled expanded allocations. Do not
   append to any canonical table or overwrite `$CC:F643`, `$CC:258A`,
   `$CD:4007`, `$CD:400E`, or `$CD:4015`.
5. Prove `$00-$06` parity, then replay noncritical and critical outcomes,
   approach/pathfind branches, damage, recovery, hurt/death, victory, and
   teardown before enabling the PC `$07` route.

The hook sites and expanded addresses remain unapproved. They require pinned
instruction preimages, complete-diff intent auditing, named production
allocations, and native runtime evidence.

## Reproduction

The source-only contract is
`references/pc7_attack_adapter_boundaries.json` (`6227` bytes, SHA-256
`f89bbfce542bb16944b62bc00822e7f8348acb794bedd149f38e7dd02c78caf7`).
It is enforced by
`tools/audit_pc7_attack_adapter_boundaries.py` (`16682` bytes, SHA-256
`c24adeab074149f8403f1532b0e9254d10ad738a871565c723c9ded78bc94602`)
and `tests/test_pc7_attack_adapter_boundaries.py` (`9188` bytes, SHA-256
`195c95cfd1d228682ddba0107934d86ae49228026a08848481d9a03047ce723e`).

The audit accepts only the pinned headerless US Rev0 ROM, reads it without
mutation, prints table hashes plus five bounded lookup-byte observations, and
has no output-file, ROM, patch, save, or state write path:

```powershell
$epochPython = 'python'

& $epochPython tools\audit_pc7_attack_adapter_boundaries.py `
  'private\input\rom_archive\Chrono Trigger (USA).sfc'

& $epochPython tests\test_pc7_attack_adapter_boundaries.py -v
```

The current focused result is 8/8 passing tests. The contract and generated
JSON contain no table dump: table preimages are represented only by SHA-256
digests.
