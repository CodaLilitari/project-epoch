; Deterministic raw-binary syntax wrapper for the round8/table SHA candidate.
; This is not a ROM builder or a production allocation manifest.

norom
!PE_SHA256_SCRATCH = $7E1000

org $000000
EpochSha256Round8_SyntaxProbeStart:
incsrc "schala_sidecar_sha256_profile1_round8.asm"
EpochSha256Round8_SyntaxProbeEnd:

assert EpochSha256Round8_SyntaxProbeEnd-EpochSha256Round8_SyntaxProbeStart <= $6000
assert bank(EpochSha256Round8_SyntaxProbeStart) == bank(EpochSha256Round8_SyntaxProbeEnd-1)

org $010000
EpochSha256Round8_SyntaxTablesStart:
incsrc "schala_sidecar_sha256_sigma_tables.asm"
EpochSha256Round8_SyntaxTablesEnd:

assert EpochSha256Round8_SyntaxTablesEnd-EpochSha256Round8_SyntaxTablesStart == $4000
assert bank(EpochSha256Round8_SyntaxTablesStart) == bank(EpochSha256Round8_SyntaxTablesEnd-1)
