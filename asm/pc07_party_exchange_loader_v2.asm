; Original slot0 loader, party-exchange candidate v2; no assigned new game span.
; Bounded roster: slots0/1=00/01, slot2=02..07; each00..07 and one80; joinedFF.
; PC07 may occupy slot2 or reserves. All metadata remains diagnostic.
; JML entry from whole C2E657..C2E65C. Mandatory E0 and physical stack premise:
; SP0A7D, inherited scheduler PER826B at SP+1. Initial pushes need that premise.
; Qualified caller M8/X8, D0/DBR7E, decimal clear, DP79=0 and DP51word=0.
; Native validation/load and SHA are separately accepted contracts. This source
; does not install ten-region LOAD or preview hooks, or claim interrupt ownership.
; Fixed32-byte ROM metadata is validated, not published as mutable live metadata.

Pc07LoaderV2:
    php
    rep #$30
    pha
    phx
    phy
    phd
    phb
    jsr Pc07LoaderPremisesV2
    bcs Pc07LoaderEntryAcceptedV2
Pc07LoaderRefusedEntryV2:
    brl Pc07LoaderRestoreFailureV2
Pc07LoaderEntryAcceptedV2:
    ldx.w #$0000
    lda.w #$0000
.preclear
    sta.l $7E2830,x
    inx
    inx
    cpx.w #$0050
    bne .preclear
Pc07LoaderPreclearedV2:
    sep #$30
    jsl Pc07ValidateSelectedSlotV2
    bcs Pc07LoaderVanillaValidV2
Pc07LoaderRefusedVanillaV2:
    brl Pc07LoaderRestoreFailureV2
Pc07LoaderVanillaValidV2:
    ; Give native load the original caller's complete CPU context.
    rep #$30
    plb
    pld
    ply
    plx
    pla
    plp
Pc07LoaderPreservedLoadCallV2:
    jsl Pc07LoaderPreserveTailV2
Pc07LoaderNativeLoadReturnedV2:
    ; The original load restores entry P and returns A0032/X34/Y32 for ten
    ; regions under X8. Save that actual result before any sidecar work.
    php
    rep #$30
    pha
    phx
    phy
    phd
    phb
    jsr Pc07LoaderPremisesV2
    bcs Pc07LoaderPostLoadContextV2
Pc07LoaderRefusedPostLoadContextV2:
    brl Pc07LoaderSafeEmptyV2
Pc07LoaderPostLoadContextV2:
    jsr Pc07LoaderRosterV2
    bcs Pc07LoaderRosterAcceptedV2
Pc07LoaderRefusedRosterV2:
    brl Pc07LoaderSafeEmptyV2
Pc07LoaderRosterAcceptedV2:
    ldx.w #$0000
.zero_scan
    lda.l $7EAE00,x
    bne Pc07LoaderRefusedScratchV2
    inx
    inx
    cpx.w #$00C2
    bne .zero_scan
    jsr Pc07LoaderEnvelopeV2
    bcs Pc07LoaderEnvelopeAcceptedV2
Pc07LoaderRefusedEnvelopeV2:
    brl Pc07LoaderSafeEmptyV2
Pc07LoaderRefusedScratchV2:
    brl Pc07LoaderSafeEmptyV2
Pc07LoaderEnvelopeAcceptedV2:
    ; First borrowed scratch store. CRC field bytes A/B are virtual zero.
    lda.w #$FFFF
    sta.l $7EAE00
    ldx.w #$0000
Pc07LoaderCrcByteV2:
    cpx.w #$000A
    beq .virtual_zero
    cpx.w #$000B
    beq .virtual_zero
    sep #$20
    lda.l $307E00,x
    rep #$20
    and.w #$00FF
    bra .feed
.virtual_zero
    lda.w #$0000
.feed
    xba
    eor.l $7EAE00
    ldy.w #$0008
.bit
    asl a
    bcc .no_xor
    eor.w #$1021
.no_xor
    dey
    bne .bit
    sta.l $7EAE00
    inx
    cpx.w #$00A0
    bne Pc07LoaderCrcByteV2
Pc07LoaderCrcCompareV2:
    cmp.l $307E0A
    beq Pc07LoaderCrcAcceptedV2
Pc07LoaderRefusedCrcV2:
    brl Pc07LoaderClearSafeEmptyV2
Pc07LoaderCrcAcceptedV2:
    lda.w #$0000
    sta.l $7EAE00
    lda.w #$0001
    ldx.w #$6000
Pc07LoaderDigestCallV2:
    jsl EpochSha256Round8_Profile1Digest
Pc07LoaderDigestReturnedV2:
    lda.l $7EAEC0
    beq Pc07LoaderDigestStatusAcceptedV2
Pc07LoaderRefusedDigestStatusV2:
    brl Pc07LoaderClearSafeEmptyV2
Pc07LoaderDigestStatusAcceptedV2:
    ldx.w #$0000
.compare
    lda.l $7EAEA0,x
    cmp.l $307E80,x
    bne Pc07LoaderRefusedDigestV2
    inx
    inx
    cpx.w #$0020
    bne .compare
    jsr Pc07LoaderRosterV2
    bcs Pc07LoaderPublishV2
Pc07LoaderRefusedLateRosterV2:
    brl Pc07LoaderClearSafeEmptyV2
Pc07LoaderRefusedDigestV2:
    brl Pc07LoaderClearSafeEmptyV2
Pc07LoaderPublishV2:
    ; Publication is last, after all envelope, CRC, binding and roster checks.
    ldx.w #$0000
.record
    lda.l $307E10,x
    sta.l $7E2830,x
    inx
    inx
    cpx.w #$0050
    bne .record
Pc07LoaderPublishedV2:
    jsr Pc07LoaderClearScratchV2
    bra Pc07LoaderRestoreSuccessV2
Pc07LoaderClearSafeEmptyV2:
    jsr Pc07LoaderClearScratchV2
Pc07LoaderSafeEmptyV2:
    ; Exact07 sanitation must run even beside malformed unrelated roster bytes.
    rep #$10
    sep #$20
    ldx.w #$0000
.roster
    lda.l $7E2980,x
    cmp.b #$07
    bne .next
    lda.b #$87
    sta.l $7E2980,x
.next
    inx
    cpx.w #$0009
    bne .roster
    lda.l $7E29AF
    and.b #$FE
    sta.l $7E29AF
Pc07LoaderSanitizedV2:
Pc07LoaderRestoreSuccessV2:
    rep #$30
    plb
    pld
    ply
    plx
    pla
    plp
Pc07LoaderSuccessV2:
    jml $C2E694
Pc07LoaderRestoreFailureV2:
    rep #$30
    plb
    pld
    ply
    plx
    pla
    plp
Pc07LoaderFailureV2:
    jml $C2E646

Pc07LoaderClearScratchV2:
    rep #$30
    ldx.w #$0000
    lda.w #$0000
.clear
    sta.l $7EAE00,x
    inx
    inx
    cpx.w #$00C2
    bne .clear
Pc07LoaderScratchRestoredV2:
    rts

Pc07LoaderPremisesV2:
    ; Ten saved bytes + near frame: P+0C, DBR+03, inherited PER+0D.
    tsc
    cmp.w #$0A71
    bne .bad
    lda $0C,s
    and.w #$0038
    cmp.w #$0030
    bne .bad
    tdc
    bne .bad
    lda $03,s
    and.w #$00FF
    cmp.w #$007E
    bne .bad
    lda.l $7E0079
    and.w #$00FF
    bne .bad
    lda.l $7E0051
    bne .bad
    lda $0D,s
    cmp.w #$826B
    bne .bad
    sec
    rts
.bad
    clc
    rts

Pc07LoaderRosterV2:
    ; Entry M16/X16. Caller already owns its saved CPU context and near frame.
    ; Read-only: A/X/Y/flags clobbered; M16/X16 on every return; C=admitted.
    ; Locked 00/01 prefix plus exactly one each of 02..07/80 in seven cells
    ; proves the whole nine-cell permutation without scratch or stack locals.
    lda.l $7E2980
    cmp.w #$0100
    bne .bad
    sep #$20
    lda.l $7E2982
    cmp.b #$02
    bcc .bad8
    cmp.b #$08
    bcs .bad8
    lda.l $7E29AF
    cmp.b #$FF
    bne .bad8
    lda.b #$02
.token
    ldx.w #$0002
    ldy.w #$0000
.scan
    cmp.l $7E2980,x
    bne .next
    iny
.next
    inx
    cpx.w #$0009
    bne .scan
    cpy.w #$0001
    bne .bad8
    cmp.b #$80
    beq .good8
    inc a
    cmp.b #$08
    bne .token
    lda.b #$80
    bra .token
.good8
    rep #$20
    sec
    rts
.bad8
    rep #$20
.bad
    clc
    rts

Pc07LoaderEnvelopeV2:
    lda.l $307FF8
    cmp.w #$E41B
    bne .bad
    lda.l $307FF0
    cmp.l $307E0C
    bne .bad
    sep #$20
    ldx.w #$0000
.header
    cpx.w #$000A
    bcc .header_byte
    cpx.w #$000E
    bcc .next
.header_byte
    lda.l $307E00,x
    cmp.l Pc07LoaderHeaderFixtureV2,x
    bne .bad8
.next
    inx
    cpx.w #$0010
    bne .header
    rep #$20
    ldx.w #$0000
.metadata
    lda.l $307E60,x
    cmp.l Pc07LoaderMetadataFixtureV2,x
    bne .bad
    inx
    inx
    cpx.w #$0020
    bne .metadata
    sec
    rts
.bad8
    rep #$20
.bad
    clc
    rts

; Tail preservation adapted from the accepted save wrapper. Native ten-region
; load preserves entry P (M8/X8) and returns its own fullA/X/Y. The actual native
; returned A is staged over dead locals; X/Y are never changed by this helper.
Pc07LoaderPreserveTailV2:
    php
    rep #$20
    lda.l $7E98B8
    pha
    lda.l $7E98BA
    pha
    lda.l $7E98BC
    pha
    lda.l $7E98BE
    pha
    lda.l $7E98C0
    pha
    sep #$20
    lda $0B,s
    pha
    plp
Pc07LoaderNativeLoadCallV2:
    jsl $FFFAA3
Pc07LoaderNativeCopyReturnedV2:
    rep #$20
    pha
    lda $03,s
    sta.l $7E98C0
    lda $05,s
    sta.l $7E98BE
    lda $07,s
    sta.l $7E98BC
    lda $09,s
    sta.l $7E98BA
    lda $0B,s
    sta.l $7E98B8
    lda $01,s
    sta $0B,s
    tsc
    cld
    clc
    adc.w #$000A
    tcs
    pla
    plp
    rtl
Pc07LoaderCodeEndV2:

Pc07LoaderHeaderFixtureV2:
    db $50,$45,$30,$37,$02,$01,$90,$00,$00,$00,$00,$00,$00,$00,$01,$01
Pc07LoaderMetadataFixtureV2:
    db $B2,$BC,$C1,$BA,$C5,$BA,$03,$E0
    db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    db $0F,$03,$00,$00,$00,$00,$00,$00
Pc07LoaderSourceEndV2:
assert Pc07LoaderMetadataFixtureV2-Pc07LoaderHeaderFixtureV2 == $10
assert Pc07LoaderSourceEndV2-Pc07LoaderMetadataFixtureV2 == $20
assert Pc07LoaderSourceEndV2-Pc07LoaderV2 < $0400
