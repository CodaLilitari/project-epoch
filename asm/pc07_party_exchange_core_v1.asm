; Original exchange core v1. Unplaced SOURCE ONLY; native E0, M16/X16,
; binary arithmetic, D0000/DBR7E, stable menu roster for each call.
; No new persistent WRAM. Ordinary stack bytes are not a proved game allocation.
; All entries here are same-bank JSR/RTS helpers. Wrappers supply long boundaries.
;
; PeExchangeContextV1: C1 iff mode5/argument0/full exchange layout; preserves X/Y.
PeExchangeContextV1:
    lda.w $0A00
    and.w #$00FF
    cmp.w #$0005
    bne .no
    lda.w $0A01
    bne .no
    lda.w $0D36
    and.w #$00FF
    bne .no
    sec
    rts
.no:
    clc
    rts

; PeExchangeAdmissionV1: C1 iff semantic roster + exact native compact mirror,
; three active/eight total/five reserve/page0or1. A clobbered; X/Y preserved.
; Locals after pushes: emptyCount 1,S; seenMask3,S; savedY5,S; savedX7,S.
PeExchangeAdmissionV1:
    phx
    phy
    lda.w #$0000
    pha
    pha
    jsr PeExchangeContextV1
    bcs +
    brl .bad
+
    lda.w $2980
    and.w #$00FF
    beq +
    brl .bad
+
    lda.w $2981
    and.w #$00FF
    cmp.w #$0001
    beq +
    brl .bad
+
    lda.w $2982
    and.w #$00FF
    cmp.w #$0008
    bcc +
    brl .bad
+
    lda.w $29AF
    and.w #$00FF
    cmp.w #$00FF
    beq +
    brl .bad
+
    lda.w $0073
    and.w #$00FF
    cmp.w #$0003
    beq +
    brl .bad
+
    lda.w $0075
    and.w #$00FF
    cmp.w #$0008
    beq +
    brl .bad
+
    lda.w $0F0C
    and.w #$00FF
    cmp.w #$0005
    beq +
    brl .bad
+
    lda.w $0080
    and.w #$00FF
    cmp.w #$0002
    bcc +
    brl .bad
+
    ldx.w #$0000
    ldy.w #$0000
.scan:
    lda.w $2980,x
    and.w #$00FF
    cmp.w #$0080
    beq .empty
    cmp.w #$0008
    bcc +
    brl .bad
+
    pha
    lda.w $0D5F,y
    and.w #$00FF
    cmp $01,s
    beq +
    pla
    brl .bad
+
    pla
    phx
    asl
    tax
    lda.l PeExchangeBitsV1,x
    pha
    and $07,s
    beq .newbit
    pla
    plx
    brl .bad
.newbit:
    pla
    ora $05,s
    sta $05,s
    plx
    iny
    bra .next
.empty:
    lda $01,s
    inc
    sta $01,s
.next:
    inx
    cpx.w #$0009
    bne .scan
    cpy.w #$0008
    bne .bad
    lda $01,s
    cmp.w #$0001
    bne .bad
    lda $03,s
    cmp.w #$00FF
    bne .bad
    pla
    pla
    ply
    plx
    sec
    rts
.bad:
    pla
    pla
    ply
    plx
    clc
    rts

; Fast lookup only: an already admitted stable compact roster is a caller premise.
; Admission runs at refresh/swap/page boundaries, not every animation visit.
; Input A=logicalID. C1/A=physical0..6 iff visible; C0/A=FFFF otherwise.
; X/Y/D/DBR preserved. Local ID/page/count bounds still reject malformed indexes.
; Sole offscreen compact entry is [7-4*page]; one roster-byte read.
PeExchangeMapV1:
    phx
    pha
    cmp.w #$0008
    bcs .bad
    lda.w $0073
    and.w #$00FF
    cmp.w #$0003
    bne .bad
    lda.w $0075
    and.w #$00FF
    cmp.w #$0008
    bne .bad
    lda.w $0080
    and.w #$00FF
    cmp.w #$0002
    bcs .bad
    asl
    asl
    eor.w #$0007
    tax
    lda.w $0D5F,x
    and.w #$00FF
    cmp.w #$0008
    bcs .bad
    cmp $01,s
    beq .bad
    pha
    lda $03,s
    cmp.w #$0007
    beq .borrow
    sta $01,s
.borrow:
    pla
    sta $01,s
    pla
    plx
    sec
    rts
.bad:
    pla
    plx
    lda.w #$FFFF
    clc
    rts

; Checked entry for boundary use/tests. Preserves input across admission.
PeExchangeCheckedMapV1:
    pha
    jsr PeExchangeAdmissionV1
    bcc .bad
    pla
    jmp PeExchangeMapV1
.bad:
    pla
    lda.w #$FFFF
    clc
    rts

; Source indices are existing 0F00/0F01, not row/page coordinates.
; C1 admits index2 <-> occupied reserve3..8; locks/empties also retain the
; caller's native BVS refusal before this new gate. X/Y preserved.
PeExchangeSwapAllowedV1:
    phx
    phy
    jsr PeExchangeAdmissionV1
    bcc .bad
    lda.w $0F00
    and.w #$00FF
    cmp.w #$0002
    beq .first_active
    lda.w $0F01
    and.w #$00FF
    cmp.w #$0002
    bne .bad
    lda.w $0F00
    and.w #$00FF
    bra .reserve
.first_active:
    lda.w $0F01
    and.w #$00FF
.reserve:
    cmp.w #$0003
    bcc .bad
    cmp.w #$0009
    bcs .bad
    tax
    lda.w $2980,x
    and.w #$00FF
    cmp.w #$0080
    beq .bad
    ply
    plx
    sec
    rts
.bad:
    ply
    plx
    clc
    rts

PeExchangeBitsV1:
    dw $0001,$0002,$0004,$0008,$0010,$0020,$0040,$0080
PeExchangeCoreV1End:
