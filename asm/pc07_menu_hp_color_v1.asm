; Private normal-menu PC07 HP color adapter v1.
; C2A200 native panel entry establishes M16/X16, D0/DBR7E. The record
; selector sets X=2*(id&7), DP6F to its live source, and9A90 to its copy.
; Only normal-layout FF / own record07 / pointer2830 / X000E uses this
; calculation. Refusals restore all context then taildelegate470205,
; preserving the existing party-exchange helper and every canonical PC.
; Source is the current menu work record's derived maxHP, not baseHP or
; occupied0D46/47. Native divisor10, equality is critical as in vanilla.
; Temporary stack only: PHP1+PHA2+PHX2+PHB1=6, JSL3 => local peak9.
Pc07MenuHpColorV1:
    php
    rep #$30
    pha
    phx
    tdc
    bne .fallback
    cpx.w #$000E
    bne .fallback
    sep #$20
    phb
    pla
    cmp.b #$7E
    bne .fallback
    lda.l $7E0D36
    cmp.b #$FF
    bne .fallback
    lda.l $7E9A90
    cmp.b #$07
    bne .fallback
    lda.l $7E2830
    cmp.b #$07
    bne .fallback
    rep #$20
    lda.l $7E006F
    cmp.w #$2830
    bne .fallback
    plx
    pla
    plp
    lda.l $7E9ACF
    sta.l $004204
    sep #$20
    lda.b #$0A
    sta.l $004206
    rep #$20
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    lda.l $004214
    cmp.l $7E9A93
    rtl
.fallback
    rep #$30
    plx
    pla
    plp
    jml $470205
