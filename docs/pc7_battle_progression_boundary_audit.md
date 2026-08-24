# Logical PC `$07` battle-progression boundary audit

Evidence: `verified-static` for the canonical observations; proposed adapter
requirements remain uninstalled architecture.

Canonical ROM: headerless Chrono Trigger US Rev0, SHA-256
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.

Interpretive source: pinned CC0 `dscotton/ct_disassembly` commit
`eeae27acdb6565e96d1d796a3d60792c250c0aa1`. The read-only auditor also pins
the relevant canonical code spans and instruction sites by SHA-256, so a
label or reconstruction change cannot silently alter the result.

## Result

Vanilla has two different post-battle XP paths:

- `$C1:F93E-$C1:F9EA` distributes full XP through the three active battle
  slots.
- `$C1:F9EB-$C1:FA60` scans recruited but inactive logical character IDs,
  targets `$7E2600 + id*$50`, awards `15/20` or 75 percent of the battle XP,
  and invokes the normal XP and level-up routines.

The reserve scan increments its logical ID and loops only while it is below
`$07`. It therefore processes `$00-$06` and never examines logical PC `$07`.
A correctly recruited Schala who is in reserve would receive no vanilla
post-battle XP.

Changing that comparison from seven to eight is not sufficient. The same
routine tests active membership through `$7E:B1BE + id`, but battle setup
clears exactly seven bytes at `$7E:B1BE-$7E:B1C4`. Direct ID `$07` reaches
adjacent `$7E:B1C5`, not a defined eighth character-to-slot entry. Widening
that table in place would overwrite unproved adjacent WRAM.

## Bounded evidence

| Span | Size | SHA-256 | Static meaning |
| --- | ---: | --- | --- |
| `$C1:F93E-$C1:F9EA` | `$AD` | `8fffca20160a25e4313ea3f8ceab3cf2331b67782bae53ff04bbd6b31c52e8c4` | three-slot active XP path before the reserve call |
| `$C1:F9EB-$C1:FA60` | `$76` | `c8a7be320e925d59a7b33e0da6992ce6ca9cd0f8568e7943292f2e564f8656a2` | joined/not-active reserve scan, 75-percent calculation, and exclusive `$07` bound |
| `$FD:B284-$FD:B2A1` | `$1E` | `12e4b050874981b04ca2c745a35eefafc5cc38c7baafa00d9cc343b42ced4e71` | seven-byte character-to-slot clear and three-active-slot publication |

Nine smaller instruction-site hashes independently pin the call edge, joined
mask read, active-map lookup, record-stride calculation, numerator,
denominator, loop bound, map-clear bound, and active-slot publication. They are
defined in `references/pc7_battle_progression_boundaries.json`; the auditor
emits only their addresses, sizes, hashes, and classifications, never ROM
bytes or local paths.

## Safe adapter contract

The eventual runtime adapter must:

1. preserve byte-for-byte-equivalent `$00-$06` targeting and XP results;
2. consider `$07` only after a valid v2 publication agrees with joined bit
   `$01` and exactly one serialized roster occurrence;
3. exclude `$07` when Schala is active, safe-empty, malformed, duplicated,
   unbound, or absent from the roster;
4. provide an explicit PC `$07` active-membership resolver instead of reading
   or widening `$7E:B1BE-$7E:B1C4` in place;
5. target natural record `$7E:2830` only after the complete vanilla
   compatibility block has been relocated; and
6. route level-up work through the still-required PC `$07` HP, MP, stat-growth,
   and current-stat adapters.

This is an adapter specification, not permission to install a hook. No ROM
allocation, hook span, WRAM owner, or runtime implementation is approved.

## Reproduction

```powershell
python tools/audit_pc7_battle_progression_boundaries.py `
  "private/input/rom_archive/Chrono Trigger (USA).sfc"

python -m unittest tests.test_pc7_battle_progression_boundaries
```

The audit is read-only. It cannot emit a ROM, save, state, patch, or report
file.

## Provenance boundary

An unlicensed, ROM-bearing external reconstruction supplied the neutral
address that prompted this check, but its semantic label for `$C1:F9EB` was
wrong. Project Epoch accepted neither that label nor any payload. The result
above was rederived from the pinned CC0 disassembly and canonical ROM, and the
external snapshot remains quarantined.

## Remaining runtime matrix

- Schala active: full XP through the ordinary three-slot path.
- Schala reserve: 75-percent XP, including multi-level progression.
- First level-up and HP/MP/stat-growth bracket crossings.
- Vanilla-only negative controls with identical records and results.
- Safe-empty, invalid-sidecar, duplicate-ID, and stray-joined-bit controls with
  no PC `$07` record write.
- Post-battle record commit, save, load, New Game+, and erase continuity.

Until those tests exist on an installable diagnostic, this audit remains
`verified-static`, not `verified-runtime`.
