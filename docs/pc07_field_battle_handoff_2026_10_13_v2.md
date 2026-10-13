# Field-to-battle handoff: archived-source reproduction v2

This additive auditor reproduces the accepted October 13 field-to-battle
checkpoint after the shared ROM write guard advanced. It preserves the original
[report](pc07_field_battle_handoff_2026_10_13.md), public reference, independent
review, collector, source pins, trace and snapshots. It adds no emulator result.

The original advertised auditor now fails at the frozen runner's import-time
source check because the live `tools/validate_rom_write_intents.py` no longer has
the historical identity. The accepted run requires exactly 39,623 bytes with
SHA-256 `d109fa0ca691652a82c1d8f3ffab7ebbec7c57342e5cc1c6e472dea60bc8aac2`.
Those exact bytes already exist at
`private/research/pc07_first_attack_builder_20261013/validate_rom_write_intents.before.py`.
The newer guard remains the current guard; this adapter serves only the older
read-only evidence reproduction.

## Reproduction

From the repository root, using a fresh Python process with the existing private
evidence packet and locally owned canonical ROM available:

```powershell
python -B tools/audit_pc07_field_battle_handoff_2026_10_13_v2.py
python -B tools/audit_pc07_field_battle_handoff_2026_10_13_v2.py --check-resolution-refusal
```

The first command prints the reproduced v2 metadata and checks it against the
v2 reference if that reference exists. The second changes one archive byte only
in memory and requires refusal before any project source executes. Neither
command writes files, launches an emulator, builds an image, emits a patch,
changes saves, or publishes anything. Missing evidence and mismatched identities
refuse; there is no substitute trace or weakened validator.

Before executing any historical project source, the adapter checks the exact
accepted receipt, the original public reference, all 54 source rows, their exact
row count and canonical JSON bundle digest
`26114966b15ab41b807de0d8ab467db1e8e1a2ad6651855f439e74cd8b5dc9fd`.
Only the one exact historical guard row resolves to the named archive. The other
53 sources retain their original paths and byte identities. Supporting frozen
review, report and disposition identities are also checked. Symlinks and Windows
reparse points are refused.

The runner checks its sources during import, before an ordinary caller can
replace its reader. The adapter therefore parses the verified runner into its
original AST statements and executes them in two phases at the exact `PINS`
assignment. After the first phase defines `read_pinned`, a wrapper resolves only
the exact historical guard request to its checked archive. Every other request
uses the original reader. The second phase executes every remaining original
statement, including the unchanged pin loop. No AST node or source file is
rewritten, removed, or skipped. The historical guard is imported from verified
archive bytes; no global `Path` or filesystem method is patched.

The unchanged original auditor then executes the full frozen independent
review and its source-only battle-adapter disposition. Its reproduced checkpoint
must equal the pinned original public JSON. The independent review itself still
requires byte-identical reproduction of its frozen receipt. All source pins are
checked again after reproduction, and temporary project imports are removed.

## Evidence retained

The accepted checkpoint remains one emulator-assisted continuous route with
250,006 records, 15 snapshots, 4,641 preparation/readback pairs, six native helper
calls in two groups, and the pre-instruction evidence cut at `C018A7` before its
battle-entry JSL. The route ends at that evidence boundary. Deferred execution
after the cut is excluded, and shutdown SRAM is not authoritative.

Original seven-character records, Epoch name bytes and snapshot SRAM retain the
original preservation results. Battle initialization, ordinary Attack,
save/cold-load, vehicle behavior and global WRAM/interrupt closure remain outside
this older checkpoint. Later project milestones do not retroactively change its
claims. The nested `frozen_checkpoint_v1` in the new reference is the unchanged
original public report, including its historical next gate.

The public v2 reference records the new auditor/report hashes, exact archive
identity, unchanged 54-row bundle, and complete reproduced original checkpoint.
The private trace, ROM, saves, snapshots and extracted game data remain local.
