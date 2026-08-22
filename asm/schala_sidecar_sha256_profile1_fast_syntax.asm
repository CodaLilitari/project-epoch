; Deterministic raw-binary syntax wrapper for the optimized SHA candidate.
; This is not a ROM builder or a production allocation manifest.

norom
!PE_SHA256_SCRATCH = $7E1000
org $000000
EpochSha256Fast_SyntaxProbeStart:
incsrc "schala_sidecar_sha256_profile1_fast.asm"
EpochSha256Fast_SyntaxProbeEnd:

assert EpochSha256Fast_SyntaxProbeEnd-EpochSha256Fast_SyntaxProbeStart < $10000
assert bank(EpochSha256Fast_SyntaxProbeStart) == bank(EpochSha256Fast_SyntaxProbeEnd-1)
