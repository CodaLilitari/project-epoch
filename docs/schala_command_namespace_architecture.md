# Project Epoch Schala command-namespace architecture

Status: selected proposal; transport verified-static, runtime proof pending  
Last updated: 2026-07-25  
Logical character ID: `$07`

## Decision

Use globally unique raw high-bit action IDs for Schala:

| IDs | Kind | Commands |
| --- | --- | --- |
| `$80-$87` | singles | Astral Pin, Veil, Crescent Wake, Stillpoint, Recall, Sanctuary, Rift Bloom, Astral Gate |
| `$88-$8D` | duals | Horizon Arc, Quiet Heaven, Eventide, Oathguard, Phase Engine, Star Pounce |
| `$8E-$8F` | triples | New Dawn, Little Star |
| `$90` | basic attack | Focus Pulse |

The machine-readable assignment and constrained UI labels live in
`tools/schala_command_layout.py`.

Do not assign `$7C-$7F` as player commands; they remain reserved
player-command IDs after vanilla's seven basic actions. This is not a global
free-space claim: the separate PC type-2 animation-config namespace has fixed
engine producers for rows `$7C`, `$7D`, and `$7F` (as well as `$79-$7B`).
Row `$7E` has no fixed producer in the current direct-address opcode census,
but remains unclaimed rather than free. Do not use `$F0-$FF`; battle-menu code
treats that range as a marker family, with `$FB-$FF` having established
special meanings.

## Why this is the smallest complete identity

`verified-static`

Vanilla named player actions occupy `$01-$74` and basic attacks occupy
`$75-$7B`. Schala needs 17 identities, so four low-byte gaps are insufficient.

Owner-scoped aliases are invalid because a vanilla partner can open and select
a Schala dual/triple tech. A queue sidecar is technically possible but would
need another proved live byte plus clearing, targeting, MP, execution, and
animation transport hooks. Raw `$80-$90` IDs are already globally unique and
survive the existing byte-wide transport intact.

## Proved transport path

`verified-static`

The seven-byte battle-menu descriptor is:

```text
+0 action ID
+1 primary target
+2 secondary target / disabled bit
+3 participant-0 MP
+4 partner-slot nibbles or $FF for a single
+5 participant-1 MP
+6 participant-2 MP
```

The selected descriptor is copied to `$7E9EE3-$7E9EE9` at
`$C1:0D4D-$C1:0DD9`. `BattleMenu_CommitAction` at `$C1:161A` writes the
queued record at `$7E93EE + slot*7`, including the raw ID at queue byte `+6`.
`Battle_ExecQueuedTech` loads that byte to `$7EB18C` and then `$7EAE93`.
No mask, sign conversion, or truncation occurs in this path.

`$C1:17FE` does not need an ID-class patch: descriptor byte `+4 == $FF`
routes Schala singles to the existing single path, while partner nibbles route
duals/triples to the combo path.

The raw ID is also copied to target state `$B192 + slot*4`. The known
downstream AI condition reader at `$C1:94AB/$C1:94C0` performs equality only,
so vanilla scripts cannot accidentally match a new high ID. Runtime
watchpoints remain required for indirect consumers.

## Command-list construction

`proposal`, with hook boundaries `verified-static`

Replace each vanilla single/dual/triple builder bundle at:

- `$C1:FB62-$C1:FB68`;
- `$C1:FB6D-$C1:FB73`;
- `$C1:FB78-$C1:FB7E`;

with `BuildActionsForSlot`:

1. IDs `$00-$06` call the three vanilla builders unchanged.
2. Every actor then calls an extended builder for learned Schala combinations
   that include that actor.
3. ID `$07` skips the vanilla builders and receives eight extended singles,
   six duals, and two triples.

The existing list partitions fit the launch set: eight single rows, six dual
rows, and two triple rows. Each vanilla partner gains at most one Schala dual.
Schala's six duals must retain six explicit participant groups.

Patch the section-marker probes at `$CC:E769/$CC:E773` from signed-negative
tests to explicit `$FF` tests; otherwise a high first dual/triple ID would
suppress its heading.

## Core sparse action table

`proposal`

Relocate `CharTechIdTables` to a sparse 145-record table indexed directly by
raw IDs `$00-$90`:

- copy `$00-$7B` byte-for-byte;
- emit explicit invalid **player-command** records for `$7C-$7F`;
- append the 17 authored Project Epoch records at `$80-$90`.

Those sparse command records are not the PC type-2 animation-config rows at
the same numeric indices. The latter are a distinct table/selector namespace
and must preserve the fixed internal `$7C/$7D/$7F` consumers proved in
`docs/battle_action_package_topology_census_v0.md`.

Each record remains 11 bytes, so the existing unsigned `id*11` machinery can
stay intact after its absolute base operands are retargeted. Set PC7's
`CharTechBase` to `$80`.

Principal long-operand sites to retarget:

```text
$C1:CB55/$CB6E/$CB87/$CBA0
$C1:D546/$D593/$D5A3/$D5CD/$D61F/$D694/$D6A4/$D732
$C1:F482/$F5B7
```

Relocate/extend the participant-pattern, component property, and component MP
tables separately. Schala's eight single components may use `$49-$50`;
component bit 7 remains reserved for existing empty/magic semantics. Add
explicit `[07,FF,FF]` and combination participant patterns.

## Mandatory high-ID edges

The raw byte transport does not make direct tables or signed UI checks safe.
These must be patched before any `$80` command is emitted:

1. **Signed list checks.** At `$C2:BD9F`, test explicitly for `$FF` rather
   than using `BMI`. Patch `$CC:E769/$CC:E773` as described above.
2. **Names.** Branch high IDs to `ExtNames` at battle `$C1:0B57-$C1:0B73`,
   main menu `$C2:BDB2-$C2:BDDC`, and learned-text control
   `$C2:5A8E-$C2:5AA8`.
3. **Descriptions.** Patch the common resolver `$CD:031E-$CD:0332` and the
   main path `$C2:BE41-$C2:BE74`. The vanilla `$CC:3A09` table has only 121
   pointers.
4. **Target modes.** Branch at `$C1:C22C-$C1:C259` and
   `$C2:B452-$C2:B45B`. `$CC:1ACB[$80+]` is occupied by later item/basic
   target semantics and must not be overwritten.
5. **Main-menu state.** Add high-ID sources for `$C2:BDB2/$C2:BDEB`,
   `$C2:B3F9-$C2:B448`, and `$C2:BC22-$C2:BC4D`. `$7E7700[$80+]` belongs
   to item state, not extended tech state.
6. **Shared participant timing finalization.** Branch high IDs at `$C1:BDF1-$C1:BDF5`,
   `$C1:BE6D-$C1:BE71`, and `$C1:BEEA-$C1:BEEE`.
   The earlier refund label does not establish a rollback or failure-only API;
   successful and failed queued Techs share this routine. See
   [MAP-007](DATA_MAPPING_CORRECTIONS.md#map-007--queued-tech-finalization-is-shared-by-success-and-failure).
7. **Player animation.** Branch at `$C1:45AA-$C1:45BB` to an extended
   16-record animation-config table and rejoin at `$C1:45EC`. ID `$80`
   otherwise aliases enemy attack-animation data at `$CD:4926`.
8. **Basic attack.** Adapt the direct `$CC:2583` consumer so `$00-$06`
   preserve their seven vanilla results and PC7 resolves `$90` from named
   expanded data. Do not append at `$CC:258A`; that byte begins HP-growth
   data. The standard formula-1 path overwrites the command for animation
   selection, so the occupied `$CC:F63C` approach-policy table and all three
   separate seven-entry `$CD:4000/$4007/$400E` selector families also need
   independent PC7 adapters. Their direct-ID boundary results are occupied;
   see `docs/pc7_attack_adapter_audit.md`. Focus weapon IDs and the downstream
   15-byte/fanout boundary are in
   `docs/schala_focus_pulse_adapter_architecture.md`.
9. **Executor hazard.** `$C1:D70A-$C1:D713` reads
   `$7EB1F5 + action_id*11`; `$80` would reach arbitrary `$7EB775`.
   High IDs must use an explicit extended runtime flag or branch to the normal
   next-participant path after runtime tracing establishes the intended flag.

Custom animation packages require a bank-qualified resolver, but a Schala
command ID does not automatically become the same-numbered package selector.
The selected source-only v0 design preserves the canonical `$00-$7F` package
path and keeps candidate Project Epoch package selectors `$80-$8F` explicitly
unbound behind separately authored action-config records. It does not copy or
relocate the canonical `TechAnimPtrTable`; that table ends immediately before
another owner at `$CD:5FF0`. Expanded packages also remain blocked by command
`$1E`'s fixed-`$CE` subscript lookup and the independent fixed-bank auxiliary
readers selected by action-config bytes `+3` through `+5`. See
`docs/schala_player_tech_package_bank_adapter_v0.md`.

## Test gate

- [ ] `$00-$7B` sparse-table records produce byte-identical vanilla results.
- [ ] `$7C-$7F` remain invalid and are never emitted as player commands;
      no global-unused claim is made for the same numeric values.
- [ ] `$80-$90` survive list build, selection, target choice, queue commit,
      execution, participant timing finalization, animation, and result-state copy.
- [ ] Every name, description, MP cost, target, and property resolves from
      Project Epoch data, never adjacent vanilla/item/enemy data.
- [ ] `$C1:D70D` semantics are established by a watchpoint trace.
- [ ] Vanilla and Schala combo eligibility works from either partner's menu.
- [ ] Learn messages and saved learned/group state round-trip.
- [ ] All eight singles, six duals, two triples, and Focus Pulse execute in
      deterministic battle tests.

The ID assignment is now pinned for tooling, but it remains a proposal until
these runtime gates pass.
