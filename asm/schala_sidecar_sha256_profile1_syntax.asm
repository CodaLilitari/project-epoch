; Deterministic raw-binary syntax wrapper for Asar.
;
; This is not a ROM builder and must never be used as a Project Epoch
; allocation manifest.  $7E1000 is a synthetic-probe scratch address only.

norom
!PE_SHA256_SCRATCH = $7E1000
org $000000
EpochSha256_SyntaxProbeStart:
incsrc "schala_sidecar_sha256_profile1.asm"
EpochSha256_SyntaxProbeEnd:

assert EpochSha256_SyntaxProbeEnd-EpochSha256_SyntaxProbeStart < $10000
assert bank(EpochSha256_SyntaxProbeStart) == bank(EpochSha256_SyntaxProbeEnd-1)
