# Project Epoch: Schala tech primitive binding audit

Status: bounded `verified-static` control-flow audit; no native bindings installed  
Logical PC: `$07`  
Action namespace: proposed `$80-$90`  
Canonical ROM: US Rev0, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`  
Pinned reconstruction: `ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`; `bank_C1.asm` SHA-256
`298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa`;
`battle_work.asm` SHA-256
`aa7384d56be567947dd6dad2191058c27b419bcbbf57293a73f6bf296851587a`  
Authored input:
`assets/source/schala/v0/content/schala_tech_content_v0.json`, file SHA-256
`efb2468da3eaa9e8f1ae0cf059a1ee45deac80694b0cc6c1f2ad475ba40ff4a5`

## Scope and evidence boundary

This audit asks which of Schala's authored gameplay primitives can pass
through the existing battle executor. It does **not** select native property
records, copy vanilla tech records, assign free ROM space, or change any
`primitive_binding` field. The source JSON remains
`authoring-only-unmapped`.

The classifications are:

- **reuse**: the target shape and effect handler already exist. Project Epoch
  still needs original parameter records and every high-ID adapter.
- **extend**: the core handler can be retained, but high-ID Project Epoch data
  needs an additional per-action or per-component parameter source.
- **new code**: the executor cannot express the authored target/effect
  combination with its current control flow.

All conclusions below are `verified-static` unless explicitly marked
`hypothesis`. Runtime behavior, balance, animation timing, immunity behavior,
and exact status duration remain mandatory test gates.

## Executor facts that constrain the design

The player-tech executor at `$C1:D523` indexes the 11-byte action record, then
loops over at most three participant components at `$C1:D5B9-$C1:D72B`.
For each pass:

1. `$C1:D5CD` obtains that participant's component-property identity.
2. `$C1:D5EF` loads one 12-byte property record.
3. `$C1:D61F` obtains one secondary-effect parameter identity.
4. `$C1:D6A4` reloads one **action-global** element value.
5. `$C1:D704` dispatches exactly one primary effect handler.

The existing primary handlers relevant here are:

| Primitive | Handler path | Static result |
| --- | --- | --- |
| heal | `$C1:D221`, operands `$C1:D132`, magnitude `$C1:DA37` | reusable |
| cleanse / restore | `$C1:D23E`, cleanse core `$C1:DB5E`, optional heal `$C1:D250-$C1:D253` | reusable |
| status / barrier / Slow / Haste | `$C1:D267`, apply `$C1:DBAA`, timers `$C1:E006` | reusable |
| physical or magic damage | `$C1:D2DE`, magnitude `$C1:E0F5`, result aggregation `$C1:EB68` | reusable |
| post-damage secondary effect | selector `$C1:D61F`, apply `$C1:EA6F`, dispatch `$C1:EB1C` | reusable for damage components |

The post-damage handler at `$C1:EEF7` is a parameterized chance/status
application path. Together with the group-1 Slow timer path at
`$C1:E04C-$C1:E05B`, it provides a concrete safe direction for Stillpoint:
new Project Epoch secondary-effect parameters can combine damage with Slow
without a wholly new effect handler. The exact chance, immunity, and timer
behavior still require a deterministic runtime test.

All participant passes currently reuse the action's one target list. The
target count is saved at `$7E:B2ED` and restored at `$C1:D5BA`. Therefore,
different components may produce different effects on the **same** targets,
but cannot currently send damage to enemies and healing or buffs to allies.

The action's element is also shared by all participant passes. At
`$C1:EF3A`, resistance selection is a priority cascade:
Lightning, then Shadow, then Water, then Fire. Multiple bits do not create a
mixed-element calculation. Authored Lightning/Shadow or Fire/Shadow damage
therefore requires participant-specific element metadata and a high-ID branch
at `$C1:D6A4`; setting two vanilla bits would be incorrect.

## Target primitives

The existing menu and execution paths can represent every simple target
shape used by Schala:

| Authored target | Existing path | Classification |
| --- | --- | --- |
| one enemy | menu dispatcher `$C1:1F79`; execution single/reacquire paths `$C1:C335/$C1:C423` | reuse |
| one ally | same single-target machinery, PC-side mode | reuse |
| one fallen ally | dead-target mode at `$C1:C3DD-$C1:C420` | reuse |
| all living allies | `$C1:C37F-$C1:C3B5` | reuse |
| all living enemies | `$C1:C43B-$C1:C474` | reuse |
| enemy line | menu line collector `$C1:25A3` | reuse |
| enemy circle | menu radius collector `$C1:2701` | reuse |
| enemies and allies with different effects | no component-local target list | new code |

High action IDs must not index the vanilla target table at `$CC:1ACB`.
Battle readers at `$C1:C22C-$C1:C259`, the main-menu reader at `$C2:B452`,
and the battle-menu descriptor builders listed in
`docs/schala_command_namespace_architecture.md` still require explicit
Project Epoch branches.

## MP primitive

None of the 17 authored actions restores, drains, or damages MP. Their only
MP primitive is participant cost.

The executor validates costs at `$C1:D74F`. The three component-cost readers
at `$C1:CB48/$C1:CB61/$C1:CB7D` resolve through the vanilla component IDs and
`$CC:253B`. This is insufficient for the authored set because Schala's MP
budget varies between combinations, and an action's effect component should
not be forced to inherit another action's cost.

The safe extension is an original high-ID component descriptor keyed by
`(action ID, participant pass)`, with at least:

```text
actor identity
primary property identity
MP cost
secondary-effect identity
element
target profile
flags (including visual-only/no-result)
```

This is a data-model proposal, not an allocation. High-ID branches are needed
at `$C1:D5CD`, `$C1:D61F`, `$C1:D6A4`, `$C1:D74F`, and the three MP readers.
It lets Project Epoch author new parameters without copying any vanilla
record, and avoids coupling combo balance to a participant's existing single
tech.

## Per-action inventory

| ID | Action | Required primitives | Static classification |
| --- | --- | --- | --- |
| `$80` | Astral Pin | one enemy; low Shadow magic damage; 2 MP | **reuse** damage and target handlers; author a new property/element row |
| `$81` | Veil | one ally; magic barrier; 4 MP | **reuse** status application; **extend** if “short” must differ from the stock status timer |
| `$82` | Crescent Wake | enemy line; moderate Shadow magic damage; 6 MP | **reuse** line targeting and damage |
| `$83` | Stillpoint | one enemy; very-low Shadow damage plus Slow; 7 MP | **extend** with a new parameter row for the existing post-damage status handler at `$C1:EEF7`; runtime-test Slow immunity and duration |
| `$84` | Recall | one fallen ally; low-HP revive; 10 MP | **reuse** fallen-target plus restore/revive path; author and test the low-HP parameter |
| `$85` | Sanctuary | all allies; cleanse plus magic barrier; 12 MP | **new code**: a single-participant action receives one primary handler, and non-damage handlers do not receive the post-damage secondary-effect pass |
| `$86` | Rift Bloom | enemy circle; high Shadow magic damage; 14 MP | **reuse** radius targeting and damage |
| `$87` | Astral Gate | all enemies; very-high Shadow damage; one-turn self MDef penalty; 20 MP | damage is **reuse**; timed self MDef reduction needs **new code**, a timer, and guaranteed restoration |
| `$88` | Horizon Arc | enemy circle; Lightning plus Shadow damage; participant costs 8/6 | **extend** to participant-specific elements and original component properties; existing two-pass result summation can remain |
| `$89` | Quiet Heaven | all allies; moderate heal plus cleanse; participant costs 8/12 | primary effects are **reuse** across two passes; **extend** with action-owned components and direct costs |
| `$8A` | Eventide | enemy circle; Fire plus Shadow damage; participant costs 12/14 | **extend** to participant-specific elements and original component properties |
| `$8B` | Oathguard | all allies; modest heal plus magic barrier; participant costs 4/12 | primary effects are **reuse** across two passes; **extend** with action-owned components; “short” duration has the Veil caveat |
| `$8C` | Phase Engine | all enemies take Shadow damage; all allies gain brief speed; participant costs 3/7 | damage and Haste-like status are individually **reuse**; different target sets require **new code** or a component-local target-list extension; “brief” also needs duration proof |
| `$8D` | Star Pounce | one enemy; very-high physical damage led by Ayla; participant costs 4/6 | physical damage is **reuse**; **extend** with a visual-only/no-result Schala component whose MP is still charged |
| `$8E` | New Dawn | all enemies damaged; living allies strongly healed; one fallen ally revived; participant costs 20/15/20 | individual handlers are reusable, but three incompatible target sets and fallen-ally selection require **new multi-phase code** |
| `$8F` | Little Star | enemy circle; extreme Fire plus Shadow damage; participant costs 20/17/20 | **extend** to participant-specific elements and original component properties; a visual-only third pass is allowed by the proposed descriptor |
| `$90` | Focus Pulse | one enemy; low equipped-Focus weapon damage; 0 MP | **reuse** the standard weapon/formula-1 damage primitive only; launch remains blocked on the action, weapon-configuration, selector, downstream-presentation, palette, and SFX adapters; a true Power/Magic hybrid formula would require **new code** |

## Status and duration boundary

Barrier, Slow, and Haste-like effects all enter the generic status machinery
at `$C1:DBAA` and the timer initializer at `$C1:E006`. Static inspection
proves the reusable paths, but it does not establish a freely parameterized
per-tech duration. Until the timer-source initialization and expiry path are
traced at runtime:

- “short” barrier means stock barrier duration only as a `hypothesis`;
- “brief” speed-up means stock Haste-like duration only as a `hypothesis`;
- no action may claim a one-turn duration merely by choosing a property byte.

Astral Gate's MDef penalty is distinct from removing a barrier. This bounded
audit found no player-tech primary or secondary handler that subtracts live
MDef and restores it exactly one turn later. It remains a new-code gate.

## Safe first bindings

The lowest-risk implementation order is:

1. Astral Pin, Crescent Wake, Rift Bloom: one original damage property each,
   existing simple target geometry, one element.
2. Recall: existing fallen-target and revive control flow, with a new
   Project Epoch low-HP parameter and runtime death/revive coverage.
3. Stillpoint: damage plus the existing parameterized post-damage status
   handler, with deterministic Slow/immunity tests.
4. Veil: existing barrier application using stock duration first; add a
   duration parameter only after the timer path is proved.
5. Focus Pulse: standard weapon formula first, after the sparse `$90`
   action-record/property resolver, PC `$07` approach policy and all three
   Attack-selector branches, expanded selector resolution, the `$E8-$EB`
   equipped-weapon configuration resolver, all four fixed downstream fanout
   consumers, and the separate palette and SFX paths are adapted.
6. Add the high-ID per-component descriptor, then bind Horizon Arc,
   Eventide, Quiet Heaven, Oathguard, Star Pounce, and Little Star.
7. Hold Sanctuary, Astral Gate's penalty, Phase Engine, and New Dawn until
   their custom control-flow tests exist.

No binding is approved before the command-namespace gates, `$C1:D70D`
runtime-flag trace, live PC7 record/save gates, and deterministic battle
round trips pass.

## Reproduction

1. Verify the four SHA-256 input hashes and pinned reconstruction revision
   listed above.
2. Trace `$C1:D523-$C1:D74E` for action/component dispatch.
3. Trace `$C1:C1DD-$C1:C55F` and `$C1:1F79-$C1:282D` for execution/menu
   targeting.
4. Trace `$C1:D221-$C1:D2DD`, `$C1:DA37-$C1:DC63`, and
   `$C1:E006-$C1:E0F4` for heal, cleanse, status, revive, and timers.
5. Trace `$C1:D2DE-$C1:D53F` and `$C1:E0F5-$C1:EFC2` for damage,
   secondary effects, and elemental resistance.
6. Confirm that the authoring JSON still has 17 null `primitive_binding`
   values and remains `authoring-only-unmapped`.

This procedure emits no ROM bytes or copied vanilla records.
