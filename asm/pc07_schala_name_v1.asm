; Project Epoch: original fixed-name private diagnostic helpers, 2026-10-13.
; No org/base, ROM emission, allocation approval, or editable name is supplied.
; E0, M8/X16, D0000, DBR7E, hidden B00; entered by a native JSL.
; The admitted route has party00/01/07 and BattleGaugeDisplayType ($9F20)=2.
; Stored PC00..06 names, Epoch's $7E2C4D..52, and SRAM are never written.

; Replaces [CCE616,CCE63B), 37 complete instruction bytes. The existing
; diagnostic's donor-name JSL occupies the first four bytes of that span.
; X is the logical PC ID; DP82 is the existing slot*5 name-buffer offset.
; Normal00..06 reproduce the full original span. Candidate07 publishes the
; first five letters to its existing five-byte buffer; the renderer below
; appends the sixth letter without enlarging any shared buffer/table stride.
; Candidate output X=0 matches the previous donor00 span, Y=DP82 and B=0.
; Final A/N/Z describe the fifth glyph; other P bits match entry.
; Additional stack peak including JSL: four bytes. No private WRAM scratch.
Pc07SchalaBattleNameSourceV1:
    php
    cpx.w #$0007
    beq .candidate
    plp
    lda.l $CCF846,x
    tax
    ldy.b $82
    lda.w $2C23,x
    sta.w $9403,y
    lda.w $2C24,x
    sta.w $9404,y
    lda.w $2C25,x
    sta.w $9405,y
    lda.w $2C26,x
    sta.w $9406,y
    lda.w $2C27,x
    sta.w $9407,y
    rtl
.candidate:
    plp
    ldx.w #$0000
    ldy.b $82
    lda.l Pc07SchalaFixedNameV1+0
    sta.w $9403,y
    lda.l Pc07SchalaFixedNameV1+1
    sta.w $9404,y
    lda.l Pc07SchalaFixedNameV1+2
    sta.w $9405,y
    lda.l Pc07SchalaFixedNameV1+3
    sta.w $9406,y
    lda.l Pc07SchalaFixedNameV1+4
    sta.w $9407,y
    rtl
Pc07SchalaBattleNameSourceV1End:

; Replaces [C1034E,C10353): STZ $A10F / REP #$20, after both native
; five-cell name rows have been drawn. DP80 is active slot; DP84 is the
; original lower-row byte offset in tilemap $0CC0. Only exact logical07 in
; display type2 receives one extra lower tile and its upper-row blank.
; Type1 uses this sixth lower cell for the gauge; it MUST be refused by the
; diagnostic host/observer. The helper safely skips it but makes no display
; success claim there. Other modes are similarly outside this v1 contract.
; All A/B/X/Y/P are restored before the original STZ/REP executes. Thus
; continuation C10353 has M16 with the original other state and flag effects.
; Extra stack peak including JSL: ten bytes; physical/interrupt qualification
; belongs to the diagnostic observer, not this source declaration.
Pc07SchalaBattleNameSixthCellV1:
    php
    rep #$20
    pha
    phx
    phy
    sep #$20
    ldx.b $80
    lda.w $2980,x
    cmp.b #$07
    bne .restore
    lda.w $9F20
    cmp.b #$02
    bne .restore
    ldy.b $84
    lda.l Pc07SchalaFixedNameV1+5
    sta.w $0CCA,y
    lda.b #$2D
    sta.w $0CCB,y
    lda.b #$FF
    sta.w $0C8A,y
    lda.b #$2D
    sta.w $0C8B,y
.restore:
    rep #$20
    ply
    plx
    pla
    plp
    stz.w $A10F
    rep #$20
    rtl
Pc07SchalaBattleNameSixthCellV1End:

; Authored text in the source-verified CT alphabet: uppercase A=$A0,
; lowercase a=$BA. C101A9's encoder passes each >=$73 glyph through and
; assigns its upper tile $FF. This literal is fixed diagnostic ROM storage,
; not a new live/saved name slot, global name selector, or player renaming UI.
Pc07SchalaFixedNameV1:
    db $B2,$BC,$C1,$BA,$C5,$BA ; Schala
Pc07SchalaFixedNameV1End:
