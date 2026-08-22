# Schala Focus Pulse adapter architecture

Status: boundary geometry `verified-static`; architecture selected but no hook,
expanded allocation, ROM mutation, or runtime PC `$07` proof is approved.

Focus Pulse joins three independent namespaces:

- logical playable PC `$07`;
- basic action `$90`;
- original Focus weapons `$E8-$EB`.

All three byte identities survive transport, but none can be fed directly to
the corresponding vanilla table. Direct indexing reaches active data owned by
another subsystem.

## Action-record boundary

Vanilla `CharTechIdTables` occupies `$CC:1BEB-$CC:213E`: 124 records of
11 bytes for action IDs `$00-$7B`. A direct `$90` lookup computes:

```text
$CC:1BEB + $90 * 11 = $CC:221B
```

`$CC:221B` is byte 4 of TechProperty record 18. It is not an action record and
cannot be overwritten. The direct action-record consumers listed in
`docs/schala_command_namespace_architecture.md` must branch `$80-$90` to the
named sparse expanded action table before Focus Pulse can be queued.

## Equipped-weapon Attack configuration

The basic-Attack animation path loads the equipped weapon ID from
`$7E1C48 + actor_slot*5`, multiplies it by 15, and indexes
`$CD:4015-$CD:45A5`. That canonical region is exactly 95 records of 15 bytes.
Each record contains three five-byte branches:

| Branch | Record offset | Direct loads |
| --- | ---: | --- |
| noncritical with `$9930=0` | `$00` | `$C1:4399/$43A0/$43A7/$43AE/$43B5` |
| noncritical with `$9930!=0` | `$05` | `$C1:43CD/$43D4/$43DB/$43E2/$43E9` |
| critical with `$AE9B` bit `$80` | `$0A` | `$C1:4360/$4367/$436E/$4375/$437C` |

The five bytes populate `$987A/$987B/$987E/$9881/$9884`. Their complete
semantic formats are not yet proved, so the new source descriptor must retain
explicit field names tied to those destinations rather than inventing labels.

Direct Focus-weapon lookups are:

| Focus ID | Computed 15-byte span | Existing owner |
| --- | --- | --- |
| `$E8` | `$CD:4DAD-$CD:4DBB` | enemy Attack-animation records |
| `$E9` | `$CD:4DBC-$CD:4DCA` | enemy Attack-animation records |
| `$EA` | `$CD:4DCB-$CD:4DD9` | enemy Attack-animation records |
| `$EB` | `$CD:4DDA-$CD:4DE8` | enemy Attack-animation records |

All four spans fall inside the active `$CD:4926-$CD:4F25` enemy
Attack-animation table. The item overlay must intercept `$E8-$EB` before the
multiply; no canonical record may be replaced.

## PC Attack-selector boundary

The three logical-PC selector families at `$CD:4000/$4007/$400E` reference
19 distinct selector IDs, `$00-$12`. Their resolver at
`$CD:5EC6-$CD:5EEF` contains 21 words.

Schala needs three deliberate branch selectors. Treating the next three IDs
as append space fails:

| Proposed selector | Resolver address | Status |
| ---: | --- | --- |
| `$13` | `$CD:5EEC` | inside the canonical resolver but not proved free |
| `$14` | `$CD:5EEE` | inside the canonical resolver but not proved free |
| `$15` | `$CD:5EF0` | collides with `TechAnimPtrTable[0]` |

Therefore the PC `$07` selector adapter and resolver must be expanded
together. `$13/$14` may not be claimed merely because no vanilla selector
family currently names them.

## Downstream fanout

The 15-byte record does not contain self-sufficient pointers. Three fields
immediately index more fixed canonical regions:

| Source field | Consumer | Canonical region |
| --- | --- | --- |
| `$987E` | `$C1:4408` | `$D1:0000-$D1:005F`, 48 words |
| `$9884` | `$C1:4420` | `$CD:64B0-$CD:656D`, 95 words |
| `$9881` | `$C1:4414` | `$CD:686E-$CD:692B`, 95 words |
| PC selector in `$9877` | `$C1:442C` | `$CD:5EC6-$CD:5EEF`, 21 words |

An expanded 15-byte record alone is consequently insufficient. Every new
field value must either:

1. resolve through a named expanded counterpart at these four consumers; or
2. be replaced by an expanded descriptor carrying explicit pointers that a
new bounded loader translates into the existing WRAM outputs.

The second form is preferred for original Focus graphics because the current
animation loader ultimately assumes fixed canonical banks. The exact pointer
and staging policy remains unbound until the original attack frames, palette,
and script packet are complete.

## Weapon palette and sound boundary

The remaining weapon-presentation tables are also fixed to the vanilla
96-weapon domain:

| Meaning | Canonical region | Direct consumer |
| --- | --- | --- |
| palette-row map | `$CD:6CEC-$CD:6D4B` | `$CC:E71C` and `$C2:F610` |
| swing SFX | `$CD:6D4C-$CD:6DAB` | animation command `$7C` at `$C1:61EF` |
| hit SFX | `$CD:6DAC-$CD:6E0B` | animation command `$7D` at `$C1:61F9` |

The battle path obtains the equipped weapon from
`$7E1C48 + actor_slot*5`. The menu path obtains it from
`$7E2629 + logical_pc_id*$50`. The Attack-animation setup also caches the
equipped weapon at `$7EA4E7`; commands `$7C/$7D` use that byte for the two
SFX lookups.

Direct `$E8-$EB` palette-map lookups compute `$CD:6DD4-$CD:6DD7`, which are
already hit-SFX entries `$28-$2B`. Direct swing lookups compute
`$CD:6E34-$CD:6E37`, inside the reachable selector-`$00` enemy Attack
package at `$CD:6E0C-$CD:6E49`. Direct hit lookups compute
`$CD:6E94-$CD:6E97`: the first three bytes are inside selector package `$02`
at `$CD:6E83-$CD:6E96`, and the final byte begins selector package `$03` at
`$CD:6E97`. The attack-package offset table at `$CD:5FF0-$CD:61EF` and its
enemy-action consumer at `$C1:4535` establish those owners. The first byte of
each six-byte `EnemyAttackAnimRecords` row supplies the selector at
`$C1:44B4`; selectors `$00/$02/$03` appear in 3, 1, and 90 canonical enemy
Attack rows respectively. These are reachable enemy packages, not PC
normal-Attack packages or merely nonzero padding. The PC Attack path instead
uses the independent resolver at `$C1:442C`.

The mapped palette row is another fixed dependency. Vanilla has 64 six-byte
rows at `$D1:4B00-$D1:4C7F`. Battle copies directly from bank `$D1` at
`$CC:E739`; both menu callers likewise use a hard-coded `MVN` source bank
`$D1` at `$C2:8369/$F5D9`. A Focus branch therefore needs an explicit
six-byte expanded palette source and must adapt all three copy contexts. A
new high map value alone cannot name an expanded-bank row.

The existing opaque
`FocusWeaponVisualDescriptorV1.expanded_downstream_binding_ptr` can remain a
locator for a future separately versioned composite packet. That target
packet still needs distinct semantics for at least:

- an exact six-byte `palette_source_ptr:u24`;
- one `swing_sfx:u8`;
- one independent `hit_sfx:u8`;
- the still-unbound graphics/animation fanout described above.

This is a field requirement, not a frozen binary layout. V1 remains unchanged
and its pointer remains zero. No palette pointer, sound ID, packet allocation,
or hook preimage is selected by this audit.

## Minimum safe implementation

The production path must preserve all vanilla results and add only explicit
PC `$07`/Focus branches:

1. Resolve basic action `$90` from the sparse `$00-$90` expanded action table.
2. Resolve PC `$07` approach policy and all three Attack selectors from a
   dedicated PC Attack descriptor.
3. Resolve `$E8-$EB` before the canonical `weapon_id*15` calculation and load
   a Focus visual descriptor into `$987A/$987B/$987E/$9881/$9884`.
4. Adapt the four downstream consumers above for expanded pointers or
   explicitly allocated expanded lookup rows.
5. Route Focus palette resolution through one six-byte source abstraction at
   the battle copy and both hard-banked menu copies.
6. Branch `$E8-$EB` before the separate `$C1:61EF/$C1:61F9` swing/hit table
   reads; byte-wide item transport does not make either direct table safe.
7. Keep the current item descriptor's `weapon_visual_ptr` zero until that
   target schema, original assets, and named expanded allocation are pinned.

No step may append at `$CC:213F`, `$CD:45A6`, or `$CD:5EF0`, and no step may
reuse the four enemy-animation spans above.

## Frozen unbound source schemas

The allocation-neutral v1 source contract now keeps the PC/action decision
separate from equipped-weapon presentation. This avoids duplicating action
`$90` four times and does not couple Schala's logical identity to one Focus
item. The layouts are proposals over the verified-static boundary geometry;
they are not native records or runtime evidence.

The single `$10`-byte `PcAttackDescriptorV1` is:

| Offset | Size | Field | Unbound v1 value |
| ---: | ---: | --- | --- |
| `$00` | 1 | version | `$01` |
| `$01` | 1 | logical PC | `$07` |
| `$02` | 1 | basic action | `$90` |
| `$03` | 1 | binding state | `$00`, the only legal v1 state |
| `$04` | 1 | value consumed by the `$C1:4A48` zero/nonzero test | `$00`, unbound |
| `$05` | 1 | `$7E9877` value for noncritical `$9930=0` | `$00`, unbound |
| `$06` | 1 | `$7E9877` value for noncritical `$9930!=0` | `$00`, unbound |
| `$07` | 1 | `$7E9877` value for critical `$AE9B` bit `$80` | `$00`, unbound |
| `$08` | 3 | opaque expanded action-record pointer | `$000000` |
| `$0B` | 3 | opaque expanded selector-binding pointer | `$000000` |
| `$0E` | 2 | reserved | zero |

Its exact unbound bytes have SHA-256
`04fe0da97fe577ce1139d4ec550e793332cc14fca2770e4d9e8c6dbf61665c70`.
Zero at offsets `$04-$07` is a placeholder, not an approved approach policy
or selector. A runtime resolver must reject the record before writing
`$7E9877`.

Each Focus weapon uses a separate `$18`-byte
`FocusWeaponVisualDescriptorV1`:

| Offset | Size | Field | Unbound v1 value |
| ---: | ---: | --- | --- |
| `$00` | 1 | version | `$01` |
| `$01` | 1 | item ID | `$E8-$EB` |
| `$02` | 1 | Focus visual ID | `$00-$03` |
| `$03` | 1 | binding state | `$00`, the only legal v1 state |
| `$04` | 5 | noncritical `$9930=0` values | zero |
| `$09` | 5 | noncritical `$9930!=0` values | zero |
| `$0E` | 5 | critical `$AE9B` bit `$80` values | zero |
| `$13` | 3 | opaque expanded downstream-binding pointer | `$000000` |
| `$16` | 2 | reserved | zero |

Every five-byte block is ordered only by the proved WRAM destinations
`$7E987A,$7E987B,$7E987E,$7E9881,$7E9884`; it deliberately assigns no
graphics, effect, palette, or SFX meaning to those bytes. Four records form a
`$60`-byte table with SHA-256
`087736c36206aa1c3937ac823817c1f2924ab6a662b2bdc6a19af801ee31047f`.

`tools/schala_focus_attack_descriptors.py` cross-validates the identities
against the existing command and original-item authoring sources. It also
hash-gates and field-validates both verified-static boundary contracts,
requires the exact four-record `$E8-$EB`/visual-`0-3` table order, round-trips
both layouts, and rejects booleans plus every nonzero unresolved value,
pointer, or reserved byte. It opens no ROM and emits only a JSON manifest on
standard output, not a project binary. The existing item overlay's
`weapon_visual_ptr` remains zero. A future bound form requires a separately
versioned schema, original assets, named expanded allocations, approved hook
preimages, and runtime proof.

## Evidence gate

- [x] Action, weapon-config, selector-resolver, and downstream table extents
      are pinned to the canonical US Rev0 ROM by hashes.
- [x] `$90` and `$E8-$EB` direct collisions are calculated and classified.
- [x] The first three-selector extension is proved not capacity-safe.
- [x] Freeze the allocation-neutral PC Attack and Focus visual descriptor
      schemas with all pointers unbound.
- [x] Pin all palette-map, palette-payload, swing-SFX, hit-SFX, and reachable
      Attack-package collisions for `$E8-$EB`.
- [ ] Complete original Focus Pulse field/battle frames, palette/effect
      sources, and audio recipes for all four Focus weapons.
- [ ] Select named expanded allocations and exact vanilla hook preimages.
- [ ] Prove byte-identical `$00-$06` and vanilla-weapon behavior.
- [ ] Prove PC `$07` noncritical `$9930=0`, noncritical `$9930!=0`, and
      critical branches, including damage and command recovery.
- [ ] Prove every Focus weapon in menu, equip, palette, battle, SFX, victory,
      teardown, save/load, New Game+, and reset paths.

The current milestone is an architecture boundary, not a playable or
installable Focus Pulse.

## Reproduction

The pinned contract is
`references/schala_focus_pulse_adapter_boundaries.json` (`9754` bytes,
SHA-256
`544ae648957407e2992e1e780f5831e55243a4cb88413727269bda40ce605318`).
The read-only auditor is
`tools/audit_schala_focus_pulse_adapter_boundaries.py` (`34134` bytes,
SHA-256
`a8b3a3464a9bc9da493055566e5678934835f171ba9d0c96d7f71bab1f699355`);
its focused test is
`tests/test_schala_focus_pulse_adapter_boundaries.py` (`14208` bytes,
SHA-256
`d7c2b8de8ea5e622ef38d0574000d3f805c23e015e0ed2aa43ccb22f583b71ff`).

```powershell
$epochPython = 'python'

& $epochPython tools\audit_schala_focus_pulse_adapter_boundaries.py `
  'private\input\rom_archive\Chrono Trigger (USA).sfc'

& $epochPython tests\test_schala_focus_pulse_adapter_boundaries.py -v
```

The current focused result is 11/11 passing tests. The auditor accepts only
the pinned headerless US Rev0 ROM, has no output-file destination, emits no
table bytes, and reports only region hashes, geometry, addresses, and bounded
collision facts.

### Auxiliary palette/SFX reproduction

The companion contract is
`references/schala_focus_weapon_aux_adapter_boundaries.json` (`12908` bytes,
SHA-256
`19f3e77db5fa7c31ec781100a69725d2bcb691432981f4800a8831f8cd1f4a99`).
Its read-only auditor is
`tools/audit_schala_focus_weapon_aux_adapter_boundaries.py` (`37242` bytes,
SHA-256
`95494481f13c2ef0932910ed3758343deea8ff65882723ff0ac27b754edec9a5`);
the focused test is
`tests/test_schala_focus_weapon_aux_adapter_boundaries.py` (`19792` bytes,
SHA-256
`79a74110ebfffe699876417069bc2ee3ab0bc6f5929900636dae262412528d59`).

```powershell
& $epochPython tools\audit_schala_focus_weapon_aux_adapter_boundaries.py `
  'private\input\rom_archive\Chrono Trigger (USA).sfc'

& $epochPython tests\test_schala_focus_weapon_aux_adapter_boundaries.py -v
```

The current result is 14/14 passing tests. The audit validates six complete
regions, six bounded collision/package preimages, the first five enemy
Attack-package offsets, and their exact reference counts across 256 canonical
enemy Attack-animation records. Its report contains hashes, addresses,
geometry, and owner labels only. It has no output-file destination and
performs no ROM, patch, save, state, trace, allocation, hook, or descriptor
mutation.

### Unbound schema reproduction

The source-only descriptor builder is
`tools/schala_focus_attack_descriptors.py` (`24469` bytes, SHA-256
`875116aa20a6ff64379f55ae8be37d4ad98b747e60c6436098a092ac806fbbb3`).
Its focused test is
`tests/test_schala_focus_attack_descriptors.py` (`13445` bytes, SHA-256
`7db3ef8839a571d367e0ecdfd6caa87fb968152771b20ba5c5ce3cec787d2e08`).

```powershell
& $epochPython tools\schala_focus_attack_descriptors.py
& $epochPython tests\test_schala_focus_attack_descriptors.py -v
```

The current result is 16/16 passing tests. The manifest pins both boundary
contract hashes and both generated-in-memory descriptor hashes, labels the
binary layout as a source-only proposal over verified-static geometry, and
requires `allocation_status: unbound`, `rom_installable: false`, and
`reject-before-any-wram-write`.
