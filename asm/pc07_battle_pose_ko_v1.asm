; Private PC07-only KO helpers. No ROM emitter or canonical data table edits.
; Builder guards the named expanded allocation and both exact hook preimages.
; Private placement: direct helper $490000, status helper $490080.
; Requires native E0, M8/X16. Status entry requires the existing battle D=0.
; The global qualifiers use long addressing and do not depend on DBR.
; No XCE/REP/SEP: hidden B and width bits are not modified.
;
; C141A5..C141A9: BF 42 5F D1, LDA.l $D15F42,X.
; Qualify the exact slot2 PC07 provider. Preserve X/Y/B/D/DBR and C/V/I/D/M/X;
; final N/Z come from the replacement LDA, as for the original instruction.
; Explicit stack: JSL3 + PHP1 + PHX2 = 6 bytes; no interrupt reserve claimed.
Pc07DirectKoFrameV1:
    php
    phx
    cpx.w #$001C
    bcc .original
    cpx.w #$0020
    bcs .original
    lda.l $7E2982
    cmp.b #$07
    bne .original
    lda.l $7E1C5D
    bne .original
    lda.l $7E1C5E
    bne .original
    lda.l $7E1C5F
    cmp.b #$42
    bne .original
    lda.l $7E1C7E
    bne .original
    lda.l $7E1C7F
    cmp.b #$10
    bne .original
    lda.l $7E1C80
    cmp.b #$42
    bne .original
    plx
    plp
    lda.b #$1A
    rtl
.original:
    plx
    plp
    lda.l $D15F42,x
    rtl
Pc07DirectKoFrameV1End:

; C1300D..C13011: 85 84 A4 94, STA dp84 / LDY dp94.
; Incoming A is a matched status-table selector. Only selector08 + slot2 +
; roster07 + exact provider changes to private selectorF0. Original07/08
; stream bytes remain intact. Next C13011 needs original X (table row index).
; Preserve X/B/D/DBR; Y and final NZ equal the original LDY dp94 effects.
; A low and hidden B are restored on both routes. Only original dp84 receives
; F0 on qualification. PLP restores P before the original LDY supplies N/Z.
; Only non-stack store is the original dp84 store, with its qualified value.
; Explicit stack: JSL3 + PHP1 + PHA1 + PHX2 = 7 bytes; no interrupt reserve.
Pc07StatusKoSelectorV1:
    php
    pha
    phx
    cmp.b #$08
    bne .original
    ldx.b $94
    cpx.w #$0002
    bne .original
    lda.l $7E2982
    cmp.b #$07
    bne .original
    lda.l $7E1C5D
    bne .original
    lda.l $7E1C5E
    bne .original
    lda.l $7E1C5F
    cmp.b #$42
    bne .original
    lda.l $7E1C7E
    bne .original
    lda.l $7E1C7F
    cmp.b #$10
    bne .original
    lda.l $7E1C80
    cmp.b #$42
    bne .original
    lda.b #$F0
    sta.b $84
    plx
    pla
    plp
    ldy.b $94
    rtl
.original:
    plx
    pla
    plp
    sta.b $84
    ldy.b $94
    rtl
Pc07StatusKoSelectorV1End:
