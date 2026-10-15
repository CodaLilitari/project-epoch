# Schala native party-selection milestone — October 15, 2026

## Result and limits

The selected private native party-exchange milestone is complete. Schala is
logical PC07, can be removed from and reselected into the third active position,
and remains present in the reserve roster. The tested route includes reserve
paging, menu exit, field movement, an ordinary Attack, and a changed-formation
normal save followed by a fresh-process load. Project Epoch as a whole is not
complete, and this is not a generally playable release.

The admitted fixture keeps Crono/Marle active in positions one/two. It preserves
all eight logical characters in the nine-cell roster, with one empty reserve
cell. Arbitrary active positions, native recruitment, mutable grant/Tech state,
full Tech/equipment/progression, world-map art, other physical save slots,
New Game+, erase, and broad scene compatibility remain separate milestones.
Metadata and name producers still include fixed diagnostic data. No production
hook/allocation approval or production high-package binding is added.

## What changed

The exchange screen maps logical IDs onto its seven existing character display
records and pages reserves. It does not extend character storage into Gaspar's
occupied presenter record. Schala's full six-letter name uses the existing
blank before the level field through a local row hook.

The first candidate revealed a graphics defect on page changes. Forced frame
uploads outside the normal animator queued reads from staging buffers that the
next animator pass could reuse. The corrected component leaves dirty frame
fields for the normal animator after its staging reset, and restores the prior
owner's six additional palette bytes when changing physical display ownership.
The accepted settled snapshots show stable Schala frames, restored other
characters, matching returned-page palette data, and unchanged Gaspar state.

The field-return helper refreshes the selected Schala object after a swap. The
writer and loader share a semantic roster rule instead of requiring a single
byte-for-byte formation. Their invalidate-first, integrity-bound save and
publish-last load ordering remain in place.

## Recorded evidence

| Boundary | Accepted observation |
| --- | --- |
| Native menu and field | 23 controller actions; removal/reselection, both reserve pages, two exits; 13,510 matched watched write/readback pairs |
| Field and battle | Actual PC07 movement; independent 00/01/07 battle records; 67,714 matched suffix pairs |
| Ordinary Attack | Target HP 8000 to 7004, damage 996; MP remains 93; caller/cleanup returns and renewed readiness |
| Changed-formation save | Active 00/01/02, reserve 07/80/04/03/06/05; 2,270 SRAM write/readback pairs reconstruct all 8 KiB |
| Fresh-process load | Exact first-process battery staged before boot; roster and PC07 record restored at native return and two field ticks, separated by an actual field wait |
| Integrity and preservation | Native slot checksum, sidecar CRC16 and full-slot SHA-256 binding pass; original-seven/name/compatibility snapshots match across the save/load return; unrelated SRAM regions unchanged |

The corrected image is 8 MiB, SHA-256
`7098f38c0b28b7806a1f69d092f7f3fd765544935e8667f5f6dfb495d386f95f`.
Its private guard checked 21 declared spans, 3,334 changed bytes and exact
inverse restoration before emission. The actual changed-formation battery is
8 KiB, SHA-256
`27968c673ee76f868a0b656a6dca4f85b7c13162c9530198be4538cf024d20a3`.
ROMs, batteries, extracted assets and raw recordings remain local and ignored.

The menu/battle process and both save/load processes completed through actual
emulator execution. They use controller input, without savestate input or
debugger game-state writes. Root inspected the accepted menu/page/battle
captures. The loaded field capture contains overlapping party sprites and is
not used as a complete per-object rendering proof.

Two inspection assumptions were corrected without rebuilding or replaying the
game: borrowed scratch must be zero at the loader return, not indefinitely
after field initialization; and an inactive role80 suppresses normal rendering
before the engine reads the draw flag. The fresh trace records role80/ID07 with
draw01. Its rendering interpretation is canonical-source reasoning applied to
recorded state, not a captured renderer/OAM trace. The later nonzero scratch
booleans do not identify a specific writer. Historical validators and the
earlier stopped collector attempt are preserved.

## Evidence and reproduction entry points

- `private/research/pc07_party_exchange_battle_followup_v1_20261015/ACCEPTED_CHECKPOINT_V1.md`
- `private/test_runs/pc07_party_exchange_battle_v1_run1/`
- `private/research/pc07_party_exchange_save_followup_v1_20261015/validate_followup_v4.py`
- `private/test_runs/pc07_party_exchange_save_roundtrip_v2_run1_load/save_roundtrip_validation_v4.json`
- `private/research/pc07_party_exchange_save_followup_v1_20261015/RESERVED_OBJECT_VISIBILITY_V1.md`
- `private/research/pc07_party_exchange_build_v2_20261015/README.md`
- `references/schala_party_selection_milestone_2026_10_15.json`

The v4 inspector was executed once against the two new recordings and passed.
It checks current recorded boundaries and artifacts; it invokes no historical
validator or emulator and does not rehash a ROM. The saved launcher v2 provides
the reproduction path for a deliberately requested fresh recording under a new
run name. Existing accepted outputs must not be overwritten. Routine resume
should reuse this checkpoint and test only a changed or newly failing boundary.

This completes the short-term menu goal. The next useful scope is to choose
between broadening active-position/scene support and implementing truthful
native recruitment and mutable progression. Those require new bounded goals;
this checkpoint does not silently begin them.
