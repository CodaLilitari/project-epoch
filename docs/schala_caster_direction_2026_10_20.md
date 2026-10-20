# Schala casting and dream-tech direction — October 20

Andrei's current direction is a retail-faithful, weapon-free caster. It takes
precedence over the historical, unimplemented "Astral Regent" proposal in
`schala_character_design_v0.md`. Preserve that older document and its source
hashes as historical work; its travel costume, alternate palette, proposed
Shadow kit and equipment names are not the current implementation brief.

## Basic Attack

- Cast a magical bolt. Never switch to a physical whack, gun butt, hammer,
  blade swing or other weapon animation at close range or on a critical hit.
- Keep the retail robe, covered feet, hair and palette. Preserve suitable
  existing PC07 sprites and every original NPC asset.
- Keep the game's target-facing choice. A target to Schala's left correctly
  needs a left-facing pose; explicit left/right artwork supports that choice.
- Add a front-facing cast. In the existing four-facing provider, "front" or
  toward the screen corresponds to down-facing. A distinct downward hand
  gesture for a tech is a separate pose requirement, not automatically a fifth
  facing. Let actual tech choreography establish the needed poses.

The first October20 battle-pose candidate installs Lily's two horizontal
casting poses and their explicit mirrors, plus recoil and KO. It still uses
the inherited Crono Attack movement, package, effect and damage behavior.
Those sprite bindings do **not** establish an all-range magical basic Attack.
Front-facing work begins as a separate private art study; it is not installed
in that earlier candidate. The later stationary-caster candidate now appends
front preparation/release and selects ranged normal/critical Attacks without
approaching, including at close range. Coda chose stationary basic casting;
any future close-up spell choreography will be specific to a Tech. This changes
presentation only: basic Attack damage and MP cost remain unchanged. See
`schala_caster_attack_2026_10_20.md` for its guarded build, native matrix and
same-image Epoch house-roundtrip evidence. Support remains bounded to PC07
in the third active party position.

Lucca/Marle are useful comparison subjects, not wholesale behavior donors:
their close-range and projectile branches must be distinguished. A ranged
package alone does not establish a weapon-free projectile, sound or damage
formula. The dedicated route investigation is under
`private/research/pc07_battle_pose_20261020/engineering/`.

## Single Techs

Use Magus's single Techs as the starting template, reworked around dreams and
the Dream Devourer instead of a void/Shadow presentation. This is Andrei's
content direction; the exact names, effects, costs and balance remain to be
specified and encoded deliberately. Dream theming does not by itself define a
new elemental type or authorize rewriting the engine's elemental system.

Keep playable Magus and his original Techs intact. Schala needs her own
intentional action/config/package bindings in the already researched expanded
namespaces. An identical number in those different namespaces is not a binding.
Reuse the completed command grammar and package research rather than repeat it.
No new Tech has been installed by this direction note or the battle-pose build.

Andrei subsequently proposed a prismatic color treatment instead of Shadow
colors. Finish and test the aimed casting poses first, then compare actual
visual studies with the collaborators. Keep the prismatic treatment in spell
effects; preserve Schala's retail body palette and original Magus effects.
This is a proposed visual direction, not an installed palette or elemental rule.

## Existing content preservation, including cheat-accessible items

Andrei explicitly requires preserving everything that already exists, even
when ordinary gameplay does not use it. This includes unused weapons for
vanilla characters that players equip through cheat codes, as well as existing
equipment, Techs, graphics, palettes, scripts and their original identifiers.
Do not recycle a record or asset because it is marked unused, unreferenced,
cut or debug-only. Treat such content as occupied and preserve its behavior.

Schala's equipment and Techs require separately named expanded storage and
explicit new mappings. Keep legacy ID resolution unchanged, retain original
records and resources byte-for-byte, and check affected cheat-accessible
equipment/Tech paths when their consumers change. A copied donor is a new
resource; modifying the donor in place is not an acceptable implementation.
Unknown occupancy remains reserved until provenance establishes otherwise.

## Portrait and the player's Epoch name

Andrei requests Schala's portrait from her concept illustration, pixelized to
match the original seven portraits' tight crop and style. The actual format is
48x48, 36 SNES 4bpp tiles and a sixteen-color BGR555 palette. Built-in image
generation supplies the concept-derived artwork; native conversion is recorded
separately. Do not call it hand-drawn original art.

Andrei rejected the later angular V3 image as too Janus-like and preferred the
earlier softer face. Retain that likeness. The selected V2 conversion preserves
the purple collar and eye color. Its private selected-art manifest records
root's current integration choice and the preserved alternatives.

Schala must use her own portrait graphics, palette and mapping, not a Crono
fallback. The status panel's legacy PC07 name currently aliases Epoch's name
buffer. That is a consumer defect to correct, not the intended character model.
The actual vehicle is player-renamable: preserve its saved name, editable naming
screen and identity. Schala's qualified UI rendering must not overwrite or
relabel that storage. Include a non-default vehicle name in the focused native
compatibility check. Do not generalize status evidence to every name consumer.

## Evidence and scope

This is a record of current user decisions and the resulting implementation
requirements. The guarded battle-pose receipt, native observations, art studies
and future ranged-attack work carry their own evidence levels. Keep proposed,
encoded, installed, observed and accepted states separate.

Machine-readable counterpart: `references/schala_caster_direction_2026_10_20.json`.
