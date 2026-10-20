# Schala prismatic effect study — October 20

The leading offline color study is A: pearl, cyan and lilac. Coda and Lily
independently prefer it to the warmer gold/rose/lilac study C and the more
saturated magenta/cyan/gold study B. This is an art direction, not an installed
Schala Tech, new element, or demonstrated animated effect.

The study decodes the actual initial Dark Mist background layer and changes
only its three visible colors. The source is 256x160 with 88 opaque tilemap
cells. Of its 19,976 opaque pixels, 16,804 (84.1%) use the brightest color.
That distribution makes the offline alternatives resemble filled disks with
colored edges. Native windows, blending, raster effects and later palette
reloads have not been modeled by the still-image comparison.

The source pass reads 3,897 selected ROM bytes. The background records at
`$D16240` use palette IDs at offsets +2/+3. Although palette records have an
eight-byte stride, the selected readers at `$CD1021` and `$CD1049` copy six
bytes: three BGR555 colors. The older eight-byte-copy annotation is incorrect.
Config byte +4 and command `$60` belong to a separate foreground path; none
of the four selected Magus packages establishes that as this background's
recolor control. Original Magus resources remain unchanged.

Lily's completed review in the saved **Chrono Trigger 8th Character**
conversation used the visible Personal GPT-6 Pro selection. She reported
opening the three supplied PNGs and selected source/metrics files in the ZIP.
The actual ROM was supplied, but she explicitly did not inspect its bytes,
run it, or rebuild it. Her recommendation is to retain the compact front/rear
casts and observe one unchanged native Dark Mist action through onset, peak
and fade with its displayed palette and blend/window state. Coda agrees.

The private packet is
`private/research/pc07_prismatic_techs_20261020/`. The exact completed response
is `collaboration/lily_response_v1.txt`; the source study and comparison are
under `source_study_v1/` and `color_study_v1/`. The exact saved conversation
reference is retained in the private collaboration records.

Claude Code's separate image/source critique completed with included usage
and paid usage disabled. The observed CLI response reports claude-opus-5-5
with the selected Max effort; this is provider metadata, not independent
backend attestation. The exact answer is `collaboration/claude_response_v1.txt`.
It prefers C provisionally, citing color separation, and agrees that actual
native blending must decide the comparison. It finds the front gesture less
readable than Lily does. Coda retains the paired gesture for now; these are
different artistic judgments, not an objective pass/fail vote.

Claude also points out that the up-fixture ring is near Schala's torso. Coda's
inspection confirms that the stills do not establish separated-target impact
alignment. The front target is below the HUD. Both alignment questions remain
open despite successful facing, stationary-body and action-lifecycle checks.
No binary ROM inspection is claimed for the Claude route. Wren's requested Grok Bot
desktop conversation is unavailable through this session's browser-only
computer controls; the signed-in bot browser view did not expose the thread.
No ordinary Grok or Grok Build conversation was substituted.

The separate unchanged native baseline now completes one Magus Dark Mist
action through the retained Spekkio checkpoint and ordinary controller input.
The observed package/effect completion boundary is 431 emulated frames after
resolver entry. It shows traveling purple mist over a lightened field. During
the sampled broad-mist phase, a separate high CGRAM ramp is lightened and BG3
uses half-additive subscreen compositing; raster/window changes prevent treating
end-frame settings as constant over the whole image. Both palette halves return
to their original ramp by cleanup. This materially limits the initial-circle
study: a bright pearl recolor could wash out, but no recolor has been tested.

The actual six-frame board and phase-specific state are in
`private/research/pc07_prismatic_techs_20261020/native_dark_mist_v1/`.
The completed run and two preparation failures remain distinct. All original
and staged inputs were unchanged; no old proof chain was replayed. Preserve
all original Magus and unused/cheat-accessible assets. A future Schala effect
needs its own named expanded resources and deliberate action/package mapping.
