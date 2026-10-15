; Original diagnostic slot0/v2 sidecar writer, party-exchange candidate v2.
; SOURCE ONLY; relocatable labels, no assigned new game span.
; Mandatory PRE-ENTRY premises: native E0 and the qualified C2CF51 physical
; stack context (entry SP0A78, original outer return C2CF54). Initial pushes
; precede runtime checks; this is not an arbitrary-caller-safe API.
; Existing preservation wrapper remains unchanged at442100. The nested JSL
; adds three bytes during native save. Original round8 SHA/sigma are unchanged.
;
; Bounded roster: slots0/1=00/01, slot2=02..07; each00..07 and one80 once.
; PC07 may occupy slot2 or reserves; joinedFF. Metadata is the explicit original
;32-byte fixture below, with no new live metadata address. Techs/quest are NOT
; implemented by writing these declared diagnostic fields. Sequence is fixed0.
; Source has no interrupt masking or ownership claim. Sidecar/stack/scratch
; ownership, physical placement and combined native integration remain gates.

Pc07WriterSaveV2:
    php
    rep #$30
    pha
    phx
    phy
    phd
    phb
    jsr Pc07WriterPremisesV2
    bcs Pc07WriterEntryAcceptedV2
Pc07WriterRefusedBeforeInvalidationV2:
    brl Pc07WriterRestoreReturnV2
Pc07WriterEntryAcceptedV2:
    sep #$20
    lda.b #$00
Pc07WriterInvalidateV2:
    sta.l $307E00
    rep #$30
    plb
    pld
    ply
    plx
    pla
    plp
Pc07WriterPreservedSaveCallV2:
    jsl $442100
Pc07WriterNativeSaveReturnedV2:
    php
    rep #$30
    pha
    phx
    phy
    phd
    phb
    jsr Pc07WriterPremisesV2
    bcs Pc07WriterPostSaveAcceptedV2
Pc07WriterRefusedPostSavePremiseV2:
    brl Pc07WriterRestoreReturnV2
Pc07WriterPostSaveAcceptedV2:
    jsr Pc07WriterFinalizedSlotV2
    bcs Pc07WriterFinalizedAcceptedV2
Pc07WriterRefusedFinalizedSlotV2:
    brl Pc07WriterRestoreReturnV2
Pc07WriterFinalizedAcceptedV2:
    ldx.w #$0000
.zero_scan
    lda.l $7EAE00,x
    bne Pc07WriterRefusedScratchV2
    inx
    inx
    cpx.w #$00C2
    bne .zero_scan
    lda.w #$0001
    ldx.w #$6000
Pc07WriterDigestCallV2:
    jsl EpochSha256Round8_Profile1Digest
Pc07WriterDigestPreClearV2:
    lda.l $7EAEC0
    beq Pc07WriterDigestStatusZeroV2
Pc07WriterRefusedDigestStatusV2:
    brl Pc07WriterClearV2
Pc07WriterRefusedScratchV2:
    brl Pc07WriterRestoreReturnV2
Pc07WriterDigestStatusZeroV2:
    jsr Pc07WriterPremisesV2
    bcs Pc07WriterPostDigestPremiseAcceptedV2
Pc07WriterRefusedPostDigestPremiseV2:
    brl Pc07WriterClearV2
Pc07WriterPostDigestPremiseAcceptedV2:
    jsr Pc07WriterFinalizedSlotV2
    bcs Pc07WriterBodyV2
Pc07WriterRefusedPostDigestSlotV2:
    brl Pc07WriterClearV2

Pc07WriterBodyV2:
    ; Byte0 stays invalid. Header byte0 exists only as a CRC/format fixture.
    sep #$20
    ldx.w #$0001
.header
    lda.l Pc07WriterHeaderFixtureV2,x
    sta.l $307E00,x
    inx
    cpx.w #$0010
    bne .header
    rep #$20
    lda.l $307FF0
    sta.l $307E0C
    ldx.w #$0000
.record
    lda.l $7E2830,x
    sta.l $307E10,x
    inx
    inx
    cpx.w #$0050
    bne .record
    ldx.w #$0000
.metadata
    lda.l Pc07WriterMetadataFixtureV2,x
    sta.l $307E60,x
    inx
    inx
    cpx.w #$0020
    bne .metadata
    ldx.w #$0000
.digest
    lda.l $7EAEA0,x
    sta.l $307E80,x
    inx
    inx
    cpx.w #$0020
    bne .digest

Pc07WriterCrcV2:
    ; Digest has been copied; borrowedAE00 now holds CRC, no new WRAM region.
    lda.w #$FFFF
    sta.l $7EAE00
    ldx.w #$0000
.byte
    cpx.w #$0000
    beq .virtual_magic
    cpx.w #$000A
    beq .virtual_zero
    cpx.w #$000B
    beq .virtual_zero
    sep #$20
    lda.l $307E00,x
    rep #$20
    and.w #$00FF
    bra .feed
.virtual_magic
    lda.w #$0050
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
    bne .byte
Pc07WriterCrcStoredV2:
    sta.l $307E0A
    ; Only an invalid record may be committed. An unexpected magic mutation
    ; refuses and re-invalidates rather than validating someone else's bytes.
    sep #$20
    lda.l $307E00
    beq Pc07WriterCommitV2
Pc07WriterRefusedMagicBeforeCommitV2:
    lda.b #$00
    sta.l $307E00
    rep #$20
    bra Pc07WriterClearV2
Pc07WriterCommitV2:
    lda.b #$50
    sta.l $307E00
Pc07WriterCommittedV2:
    rep #$30
Pc07WriterClearV2:
    ldx.w #$0000
    lda.w #$0000
.clear
    sta.l $7EAE00,x
    inx
    inx
    cpx.w #$00C2
    bne .clear
Pc07WriterScratchRestoredV2:
    bra Pc07WriterRestoreReturnV2
Pc07WriterRestoreReturnV2:
    rep #$30
    plb
    pld
    ply
    plx
    pla
    plp
Pc07WriterOuterReturnV2:
    rtl

Pc07WriterPremisesV2:
    ; Ten saved context bytes plus this near frame: saved P+0C/DBR+03.
    tsc
    cmp.w #$0A6C
    bne .bad
    lda $0C,s
    and.w #$0038
    cmp.w #$0020
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
    cmp.w #$CF54
    bne .bad
    sep #$20
    lda $0F,s
    cmp.b #$C2
    rep #$20
    bne .bad
    ; ABI/slot admission is complete; a policy refusal still refuses save.
    jmp Pc07WriterLiveRosterV2
.bad
    clc
    rts

Pc07WriterLiveRosterV2:
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

Pc07WriterFinalizedSlotV2:
    ; Native save is the accepted opaque contract, not a new checksum engine.
    ; Its finalized checksum lives at307FF0, outside the fullA00 slot.
    lda.l $307FF8
    cmp.w #$E41B
    bne .bad
    jmp Pc07WriterSerializedRosterV2
.bad
    clc
    rts

Pc07WriterSerializedRosterV2:
    ; Entry M16/X16. Caller already owns its saved CPU context and near frame.
    ; Read-only: A/X/Y/flags clobbered; M16/X16 on every return; C=admitted.
    ; Locked 00/01 prefix plus exactly one each of 02..07/80 in seven cells
    ; proves the whole nine-cell permutation without scratch or stack locals.
    lda.l $306580
    cmp.w #$0100
    bne .bad
    sep #$20
    lda.l $306582
    cmp.b #$02
    bcc .bad8
    cmp.b #$08
    bcs .bad8
    lda.l $3065AF
    cmp.b #$FF
    bne .bad8
    lda.b #$02
.token
    ldx.w #$0002
    ldy.w #$0000
.scan
    cmp.l $306580,x
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
Pc07WriterCodeEndV2:

Pc07WriterHeaderFixtureV2:
    db $50,$45,$30,$37,$02,$01,$90,$00,$00,$00,$00,$00,$00,$00,$01,$01
Pc07WriterMetadataFixtureV2:
    ; Exact32-byte authored v2/recruited_fixture_v2.json metadata, noliveaddress.
    db $B2,$BC,$C1,$BA,$C5,$BA,$03,$E0
    db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    db $0F,$03,$00,$00,$00,$00,$00,$00
Pc07WriterSourceEndV2:
assert Pc07WriterMetadataFixtureV2-Pc07WriterHeaderFixtureV2 == $10
assert Pc07WriterSourceEndV2-Pc07WriterMetadataFixtureV2 == $20
assert Pc07WriterSourceEndV2-Pc07WriterSaveV2 < $0400
