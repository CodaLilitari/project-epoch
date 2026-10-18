# Schala main PC sprite direction — October 17, 2026

Andrei requested the next art stage after the world-map milestone: replace
copied filler poses in the current playable PC07 field/battle presentation
with genuinely authored sprite work. This stage concerns regular, battle,
running and KO sprites. It does not revise the selected world-map V5 set.

## Reference and authoring policy

Use the actual current playable PC07 sheet extracted from the accepted current
image beside the original seven playable characters. The retail NPC sheet
alone is insufficient. Preserve the existing presentation unchanged as the
comparison baseline. Identify repeated selectors and unique rendered frames
separately; many fallback cells can point to the same pose and are not that
many distinct missing animations. Keep uncertain animation semantics labeled.

Each contributor and Coda should make an independent attempt from the shared
reference packet, without seeing one another's new drafts first. Use manual
or coded pixel art with editable indexed grids/source and native-size PNGs.
Do not use generative images for this pass. First drafts are proposed artwork;
their pose labels are not proved native animation bindings.

**Retail design fidelity is mandatory.** Andrei corrected the first drafts
when new poses became altered costumes/anatomy, including bare feet. Preserve
Schala's existing long robe and covered feet, hair shape, collar/trim, body
proportions and pixel shading. No exposed legs/feet, invented shoes, shortened
robe, simplified thin limbs or redesigned hairstyle. New movement and gestures
must remain recognizably the same installed retail-derived character.

This correction rejects Coda v1's bare feet and the much larger design drift
in Nua/Gemini studies as integration candidates. A separate Coda v2 removes
32 upright lower-hem flesh-colored pixels, but that narrow repair does not
approve the remaining body shading/proportions. Retain originals for provenance;
do not present a palette-valid study as accepted retail-faithful art.

## Pure caster decision

Schala should have no weapon sprites. Her ordinary Attack should use
a casting gesture followed by a separate flying magic bolt. Lucca's ranged
attack is a behavior reference, not permission to give Schala a gun or copy a
weapon pose. Do not draw swords, guns, staffs or other held weapons.

Plan clear casting preparation/release/recovery, normal movement and running,
damage/recovery and KO poses while preserving Schala's distinctive hair, robe,
collar and proportions within the original party's pixel-art style. Keep any
bolt effect separately labeled from character frames and do not bake it into
her body sheet. The art decision does not yet change native effect routing,
equipment, damage, MP costs, animation binding or Tech behavior.

## Current status and boundaries

The original NPC Schala must remain unchanged. Andrei explicitly required
that none of this new art overwrite her NPC graphics or animation data.
Keep new poses in the separate playable-PC07 expanded provider. Before any
later ROM emission, audit its complete diff and verify equality of the
original NPC graphics, assembly, animation streams and source-table entries.
Shared source pointers are not permission to change their targets.

The recovered dependency map confirms that current PC07 graphics, assembly and
animation are separate expanded copies, but its palette still reads original
NPC Schala at file `$240C00..$240C18` (end exclusive). Keep that palette
unchanged. Any future PC07-only color change would require a separate guarded
allocation and binding, not an edit to the shared NPC palette. The private
`NPC_PRESERVATION_MAP_V1.json/.md` records 13 known protected source spans and
the remaining unknowns; it does not claim a new guard is already implemented.

Reference recovery and independent first-draft preparation began during the
remaining part of the authorized two-hour October17 continuation. The current
world-map ROM and accepted gameplay evidence remain unchanged. A complete main
sprite set, native pose mapping, ROM integration and gameplay acceptance are
separate unfinished work. Extracted game pixels, private candidates and exact
collaboration attachments remain local/ignored, with identities and receipts
in `private/research/pc07_main_sprite_art_20261017/`.

## First bounded batch

The recovered reference contains 23 installed assembly frames and 79 graphics
tiles. The 988 fallback selector cells are repeated references, not 988 missing
poses. In the current source, normal-run selector `$06` reaches the existing
outstretched-hand frames 19/20 in every facing. Correct role binding therefore
needs explicit work alongside the art; retaining an NPC selector number does
not establish the same playable-character meaning.

The shared first batch asks for two running poses in each direction, casting
windup/release, recoil and a fallen KO: twelve 48x48 canvases with native origin
(16,40), using the exact installed Schala palette. These are proposed roles,
not installed animation IDs. Four 16x16 pieces remain the eventual frame budget.

All six collaborators received independent requests. Coda produced a new
hand-drawn body/KO study while retaining the installed head details for visual
continuity. Lily returned a bundle and a corrected-origin revision; Wren
returned an independently drawn batch. Red's first delivered study uses
existing-pose shears and a rotated KO, openly labeled unfinished; a bounded
body/KO redraw returned as v2, followed by a retail-design correction v2.1.
The latter restores the inherited idle robe with new arms, but still has static
folds, a wave-like hurt gesture and simplified KO shading. Gemini's incorrect
palette was explicitly corrected; the reconstructed art remains rejected for
design drift. Nua's exact returned grids were reconstructed locally and rejected
for thin limbs, exposed legs and changed hair. Meta supplied an actual PNG with
unfinished sway/back-facing run frames and a block-like KO; provider editable
JSON was unavailable. All six contributions are closed for this work window.

None is selected or installed. Static dimensions, palette and pixel equality
checks do not settle artistic quality. Coda's run remains restrained and the
recoil subtle; Lily's KO is undersized and her corrected right-run draft has
one documented pixel asymmetry; Wren's back run is subtle and KO head is flat.
These are useful first drafts, not a completed replacement for every copied
pose. All original submissions and corrections are preserved separately.

After Andrei's correction, no new main-sprite candidate is accepted for
integration. The next art iteration should begin with a small retail-locked
pose comparison, correcting silhouette, clothing and gesture before expanding
the count. Do not repeat full validation chains to review art. No ROM/NPC/save
data was written during this main-sprite phase, and no new publication occurred.

The current machine-readable state is
[`schala_main_sprite_art_checkpoint_2026_10_17.json`](../references/schala_main_sprite_art_checkpoint_2026_10_17.json).
