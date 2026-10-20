# Schala main sprites: retail-faithful art continuation

Andrei resumed the playable PC07 regular, battle, running and KO art on
October 18. This pass keeps the installed retail design as its reference:
lavender hair, face, collar and trim, full purple robe, covered feet and the
existing palette. Schala remains a pure caster. Weapon sprites and the future
magic bolt are outside the body sheet.

## Actual progress

Coda's conservative study now contains twelve proposed frames: two running
phases in each of four directions, casting preparation and release, recoil,
and a fallen pose. The front/back pairs retain their installed facing-specific
head, hair and collar pixels above newly authored cloth. The left pair is an
explicit mirror of the right, following the reflection found in the extracted
installed reference. It is derivative artwork, not twelve wholly original
drawings. A separate more energetic right-running alternative is preserved.

The native PNG and editable index grids agree. The focused candidate checker
passes the exact 13-color palette, transparent index zero, 48-by-48 cells at
origin (16,40), and coverage by at most four movable 16-by-16 pieces. These
checks establish format and geometry only. They do not establish native tile
encoding, animation bindings, in-game motion or artistic acceptance.

The actual enlarged and native-size boards were inspected. Coda's conservative
set retains the retail head silhouette and covered hems, but front/back motion
is restrained and recoil is subtle. The energetic running alternative has
stronger arm movement but overly regular diagonal folds. The first fallen
pose has less convincing body mass than Red's new independent study.

## Collaboration and artistic assessment

Lily worked in the existing saved Project Epoch conversation, with Personal
GPT-6 and Pro selected in the visible interface. Her actual v1 and corrected
v2 bundles were retrieved. A focused correction removed two tan lower-hem
pixels, closed a run-B robe gap and revised the KO head. The unchanged casting
and recoil pixels were checked. Her result remains a conservative derivative
of installed poses; the KO head is still too small and simplified for selection.

Red used the existing Cowork conversation at observed Opus 5.5 Max. Her new
six-pose bundle contains literal new body grids with reused retail head crops.
An independent inert-data reconstruction matches the delivered PNG without
executing her code. The new recoil lean and long horizontal KO improve pose
readability. Her large swept hair mass, straight casting arm, rigid cloth
bands and rotated KO-head lighting remain artistic limitations. One separately
attributed Red-body/Coda-head refinement also passes the static checker, but
its triangular hair mass and awkward neck join are visually worse. It is
preserved as a rejected alternative; Red's original has not been replaced.

Gemini, Nua and Meta supplied independent returns in their supported formats.
Their inspected results drift from the retail hair, proportions, trim or robe
shading and are not selected. Source/JSON reconstructed locally is labeled as
such; it is not presented as an original downloaded provider PNG. Wren's actual
six-pose ZIP was subsequently retrieved and inspected. Their full covered robe
and step silhouette are useful, while the heavy swept hair, rigid casting arm,
weak recoil and muddled rotated KO face remain unfinished. All six external
routes returned work; delivery does not make any complete set selected art.

The private comparison preserves originals, corrections, exact input lists,
source, image receipts, collaborator references and visual dispositions. No
contributor's agreement substitutes for Coda's inspection or native evidence.

## Preservation and next implementation boundary

This is an art-only continuation. No ROM or save was read or written, and no
NPC graphics, assembly, animation or shared palette was modified. Existing
world-map V5 and flying-Epoch evidence were reused as prior context, not rerun.
No historical full-chain validation, new API billing or publication occurred.

The normal-run selector `$06` currently reaches frames 19/20 in all four
facings with one shared timing stream. The existing compiler's fixed 23-frame
limit needs a separate version before adding authored frames. Keep installed
frames 0-22 stable, derive the new count, encode tiles/assembly deterministically
and reconstruct pixel-equal output before any image emission. Then bind each
chosen pose to its actual consumer; art role names are not native selectors.

Any later ROM write still requires the current-operation intent/complete-diff
audit and equality of all thirteen recovered NPC spans, including the shared
palette at file `$240C00..$240C18`. That future safeguard is not claimed as
implemented by this art pass. The next runtime check should cover only changed
consumers, starting with walk/run/stop and restoration in supported facings.
The world-map/Epoch/save proof chain need not be repeated for changed robe pixels.

See `references/schala_main_sprite_art_checkpoint_2026_10_18.json` for current
delivery and refinement status. All reference pixels, proposed artwork and
conversations remain under ignored `private/research/pc07_main_sprite_art_20261018/`.
No new body set has been installed or accepted by Andrei. The full regular and
battle animation set and Project Epoch itself remain unfinished.
