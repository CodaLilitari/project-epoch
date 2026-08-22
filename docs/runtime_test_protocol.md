# Lucca -> Magus diagnostic test protocol

## Purpose

This test asks whether the currently mapped ROM and runtime character-data
layers are enough to make supported character ID `$02` (Lucca) behave like
Magus. It is not an eighth-character implementation.

The first run of this protocol is complete. See
`docs/emulator_test_results_2026-07-25.md`. The static graphics clone reaches
the loaded field; the provisional runtime-record hook does not persist its
intended Magus-to-Lucca record copy. Static reconstruction later proved that
the hook is field sprite setup and its payload overwrites enemy-reward data.
The runtime artifact is retired and retained only for reproducibility.

## Safety

- Work only with copies of the clean ROM and save.
- Do not use the provisional-runtime IPS for normal play or further
  development. If reproducing the historical negative result, use it only in
  an isolated emulator run.
- Disable autosave or automatic SRAM preservation if the emulator supports it.
- Do not use the game's Save command during the test.
- Delete the disposable test SRM afterward if the emulator writes one.

The patch builder never opens or writes an SRM. The patched game attempts to
overwrite Lucca's live WRAM character record, and the normal save routine
serializes the affected regions. The patch also replaces vanilla
enemy-reward records in ROM.

## Inputs

- Canonical unheadered Chrono Trigger (USA) Rev 0 ROM:
  SHA-1 `de5822f4f2f7a55acb8926d4c0eaa63d5d989312`
- A disposable copy of the original, unmodified Lavos save
- Quarantined
  `output/experimental/ct_lucca_to_magus_clone_runtime_v1_UNSAFE.ips`

The recovered `chrono_trigger.srm` is 8192 bytes and has SHA-256:

`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`

The IPS SHA-256 must be:

`484bad4051f39d92015f57a927471d8287ca4e3652a1eef5a9475fabbf4b3cae`

## Run

1. Apply the IPS to a copy of the canonical ROM.
2. Start with the disposable, unmodified save. Do not load a save that has
   already been used with an earlier clone experiment.
3. Continue the game and place Lucca in the active party.
4. Record each checkpoint below before advancing to the next.
5. If the game crashes, corrupts the roster, or produces invalid equipment,
   stop and preserve the emulator log/state separately from the original save.

## Checkpoints

| Checkpoint | Record |
| --- | --- |
| Continue/save-select | Lucca name, portrait, level, HP/MP, sprite |
| Main roster | portrait, name, level, element icon, equipment |
| Party exchange | portrait, field sprite, selection behavior |
| Field | sprite, palette, animation, collision, transitions |
| Basic attack | animation, weapon/effect, damage, critical behavior |
| Tech learning | TP thresholds and next-tech progression |
| Tech menu | eight names, descriptions, MP, learned state |
| Single techs | target rules, animation, effect, damage, stability |
| Battle exit | field sprite and menu state remain coherent |

For every mismatch, note whether it appears before or after Lucca enters a
party-slot graphics-loading path. That timing distinguishes static table gaps
from a hook that executes too late.

## Interpretation

- The static-only IPS isolates ROM table and portrait changes.
- The provisional-runtime IPS adds the live Magus-to-Lucca WRAM clone.
- A difference between those builds identifies behavior dependent on the
  runtime record or hook timing.
- Success does not validate logical ID `$07` or any backing storage. `$0480`
  and the former `$CC:63F6` “cave” are both retired.
