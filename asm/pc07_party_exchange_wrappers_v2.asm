; Original exchange wrappers v2: defer changed frames to the native animator.
; Public V1 entry labels remain stable for the existing observer interface.
; Mandatory native E0, binary arithmetic, D0/DBR7E at hook sites.
; No new WRAM mapping or out-of-task frame upload. Native timing remains to observe.
; Unchanged parent hook spans/continuations are in the v1 design_v1.json.
macro PeSave()
    php
    rep #$30
    pha
    phx
    phy
    phd
    phb
endmacro
macro PeRestore()
    rep #$30
    plb
    pld
    ply
    plx
    pla
    plp
endmacro
; Only selected RTS-only, non-yielding C2 callees. Five native return bytes.
; Existing immutable C2800D is RTL. Never call task Sleep/exit with this bridge.
macro PeNear(target)
    phk
    per ?back-1
    pea.w $800C
    jml <target>
?back:
endmacro

; JSL replacement of MVN7E7E/INC at C2887C. M16/X16.
PeExchangeNameV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    lda.w $9A90
    and.w #$00FF
    cmp.w #$0007
    bne .normal
    %PeRestore()
    php
    phx
    ldx.w #$2093
    lda.w #$0005
    mvn $7E,$41
    plx
    inx
    inx
    inx
    inx
    inx
    inx
    plp
    inc
    rtl
.normal:
    %PeRestore()
    mvn $7E,$7E
    inc
    rtl

; JSL at C2A200, M16/X16. Only the low-HP color threshold, NOT numeric HP.
; Existing fixture derivedMaxHP1029 renders029 through the native3-digit string.
; Do not clamp or change live/display numerical HP here.
PeExchangeHpThresholdV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    lda.w $9A90
    and.w #$00FF
    cmp.w #$0007
    bne .normal
    %PeRestore()
    lda.l $7E286F
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
    cmp.w $9A93
    rtl
.normal:
    %PeRestore()
    lda.w $0D38,x
    cmp.w $9A93
    rtl

; JML whole-short-function entry C2C997; retain original PHP/near RTS frame.
PeExchangeAnimationV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    %PeRestore()
    php
    lda.w $2980,x
    bmi .done
    rep #$30
    and.w #$00FF
    jsr PeExchangeMapV1
    bcc .done
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    tya
    sta.w $1811,x
.done:
    jml $C2C9AC
.normal:
    %PeRestore()
    php
    lda.w $2980,x
    jml $C2C99B

; JML C2CDB0. M16/X16. Failed local mapping skips publication, not a fake slot.
PeExchangeBoxLookupV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    jsr PeExchangeSixthGlyphV2
    %PeRestore()
    lda.w $9A90
    php
    pha
    and.w #$00FF
    jsr PeExchangeMapV1
    bcc .skip
    asl
    asl
    asl
    asl
    asl
    asl
    tay
    sta.w $0D2C
    pla
    plp
    jml $C2CDB6
.skip:
    pla
    plp
    jml $C2CDC7
.normal:
    %PeRestore()
    lda.w $9A90
    %PeNear($C2F626)
    jml $C2CDB6

; JML C2CE55. M8/X16, B0 established by TDC at CE4A.
PeExchangePlaceLookupV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    %PeRestore()
    lda.w $2980,y
    php
    rep #$20
    pha
    and.w #$00FF
    jsr PeExchangeMapV1
    bcc .skip
    asl
    asl
    asl
    asl
    asl
    asl
    tay
    sta.w $0D2C
    pla
    plp
    jml $C2CE5B
.skip:
    pla
    plp
    jml $C2CE6A
.normal:
    %PeRestore()
    lda.w $2980,y
    %PeNear($C2F626)
    jml $C2CE5B

; JML C2CCBD; this function already has the original PHP saved by CCB3.
PeExchangeDimLookupV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    %PeRestore()
    lda.w $2980,x
    and.w #$00FF
    jsr PeExchangeMapV1
    bcc .skip
    asl
    asl
    asl
    asl
    asl
    tay
    clc
    jml $C2CCC7
.skip:
    jml $C2CCD9
.normal:
    %PeRestore()
    lda.w $297F,x
    and.w #$FF00
    lsr
    lsr
    lsr
    tay
    jml $C2CCC7

; JML C2C6DB. The native caller already refuses selected locked/empty flags.
PeExchangeSwapGateV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .native
    jsr PeExchangeSwapAllowedV1
    bcc .refuse
.native:
    %PeRestore()
    %PeNear($C2C70C)
    %PeNear($C2EAC2)
    jml $C2C6E1
.refuse:
    %PeRestore()
    %PeNear($C2EAC2)
    jml $C2C6E1

; JML C2CB0A. Vanilla cache first, original physical palette dimming last.
PeExchangeCacheV1:
    %PeNear($C2F5A7)
    %PeSave()
    jsr PeExchangeAdmissionV1
    bcc .skip
    jsr PeExchangePaletteV1
.skip:
    %PeRestore()
    %PeNear($C2CC4F)
    jml $C2CB10

; JML prelude C2CCDB. The original near caller and its future PHP stay intact.
PeExchangeDrawRefreshV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .native
    jsr PeExchangeRefreshV1
    bcc .refuse
.native:
    %PeRestore()
    php
    rep #$30
    lda.w #$0006
    jml $C2CCE1
.refuse:
    %PeRestore()
    jml $C2CD2A

; JML prelude C2CDE3; runs BEFORE CE2A clears the old07 tag.
PeExchangePlaceRefreshV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .native
    jsr PeExchangeRefreshV1
    bcc .refuse
.native:
    %PeRestore()
    php
    rep #$30
    lda.w $0D36
    jml $C2CDE9
.refuse:
    %PeRestore()
    jml $C2CE29

; JML C2C85B. Bound page changes use immediate rows/placement, no C8BA tween.
PeExchangePageV1:
    %PeSave()
    jsr PeExchangeContextV1
    bcc .normal
    jsr PeExchangeAdmissionV1
    bcc .unchanged
    sep #$20
    lda.b $5A
    and.b #$08
    beq .down
    lda.b #$03
    sta.b $54
    lda.b $80
    beq .unchanged
    dec.b $80
    bra .changed
.down:
    lda.b #$06
    sta.b $54
    lda.b $80
    bne .unchanged
    inc.b $80
.changed:
    stz.w $0D9E
    rep #$30
    %PeNear($C2CCDB)
    %PeNear($C2CDE3)
    %PeNear($C2CC4F)
    ldx.w #$FBE3
    %PeNear($C28385)
    sep #$20
    inc.w $0D15
.unchanged:
    %PeRestore()
    jml $C2C887
.normal:
    %PeRestore()
    lda.b $5A
    and.b #$08
    jml $C2C85F

; M16/X16,D0/DBR7E. Caller has admitted stable compact context.
; Patch palette/D1 only for the visible borrowed physical record; preserve041B.
; Other registers and hardware multiplier are clobbered, caller saves context.
PeExchangePaletteV1:
    lda.w #$0007
    jsr PeExchangeMapV1
    bcc .done
    asl
    asl
    asl
    asl
    asl
    tay
    phy
    ldx.w #$0000
.copy:
    lda.l $E40C00,x
    sta.w $95A2,y
    inx
    inx
    iny
    iny
    cpx.w #$0018
    bne .copy
    ply
    tya
    clc
    adc.w #$95BA
    tay
    lda.w $041B
    pha
    lda.w #$0007
    %PeNear($C2F5ED)
    mvn $7E,$D1
    pla
    sta.w $041B
.done:
    rts

; M16/X16,D0/DBR7E; C1 success, C0 refusal with no mapping writes.
; Old tag must be captured before clear. Locals: newOffset1,S / oldOffset3,S.
; No sleep/yield. Only pointer/base-palette preparation here; the existing
; animator owns frame staging after its reset. This is not a global DMA proof.
PeExchangeRefreshV1:
    jsr PeExchangeAdmissionV1
    bcs +
    rts
+
    ; Native item caches are ready before CA30. Rebuild actual derived stats
    ; through the ordinary loader/commit pair; never clamp the display copy.
    lda.w #$0007
    %PeNear($C28816)
PeExchangeStatsLoadedV1:
    %PeNear($C29137)
PeExchangeStatsCommittedV1:
    lda.w #$FFFF
    pha
    ldx.w #$0000
.scan:
    lda.w $1800,x
    and.w #$00FF
    cmp.w #$0007
    bne .next
    lda $01,s
    cmp.w #$FFFF
    beq +
    pla
    clc
    rts
+
    txa
    sta $01,s
.next:
    txa
    clc
    adc.w #$0040
    tax
    cpx.w #$01C0
    bne .scan
    lda.w #$0007
    jsr PeExchangeMapV1
    bcc .have_new
    asl
    asl
    asl
    asl
    asl
    asl
.have_new:
    pha
    cmp $03,s
    bne +
    brl .palette
+
    lda $03,s
    cmp.w #$FFFF
    beq .new
    tax
    clc
    adc.w #$1800
    tcd
    txa
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    sep #$30
    sta.b $00
    stz.b $01
    stz.b $11
    lda.b #$01
    sta.b $17
    %PeNear($C2F422)
    ; F422 invalidates03/12. The ordinary animator owns the next frame upload.
    rep #$30
    lda.w #$0000
    tcd
    lda $03,s
    jsr PeExchangeRestoreD1V2
.new:
    lda $01,s
    cmp.w #$FFFF
    bne +
    brl .palette
+
    clc
    adc.w #$1800
    tcd
    sep #$20
    lda.b #$FF
    sta.b $00
    sta.b $03
    sta.b $12
    stz.b $01
    stz.b $11
    lda.b #$01
    sta.b $02
    sta.b $17
    lda.b #$80
    sta.b $18
    lda.b #$42
    sta.b $06
    sta.b $09
    sta.b $1D
    sta.b $20
    rep #$20
    lda.w #$0000
    sta.b $04
    lda.w #$1000
    sta.b $07
    lda.w #$4000
    sta.b $0A
    lda.w #$5100
    sta.b $0C
    lda.w #$0404
    sta.b $14
    ; Leave03/12=FF. Publish below, then F657 resets its own pool and services
    ; dirty visible records with its existing budget. Do not queue here.
    rep #$30
    lda.w #$0000
    tcd
.palette:
    jsr PeExchangePaletteV1
    lda $01,s
    cmp.w #$FFFF
    beq .done
    tax
    sep #$20
    lda.b #$07
    sta.w $1800,x
    stz.w $1818,x
    rep #$20
.done:
    pla
    pla
    sep #$20
    inc.w $0D15
    rep #$20
    sec
    rts

; M16/X16,D0/DBR7E. A=old physical offset (id*40), already bounded0..180.
; F422 restored only the 24 base colors. Restore this owner's six D1 colors.
; Native F5ED returns X=D1 source/A=5, preservesY and its entryP. Its temporary
; 041B write is restored; MVN returns DBR7E. X/Y/A are caller-saved scratch.
PeExchangeRestoreD1V2:
    pha
    lsr
    clc
    adc.w #$95BA
    tay
    lda.w $041B
    pha
    lda $03,s
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    %PeNear($C2F5ED)
PeExchangeOldD1SourceV2:
    mvn $7E,$D1
    pla
    sta.w $041B
    pla
    rts
; Selected C2CDB0 post-row call only, after native FF:BE0E rendering.
; FF:C5BE control05 prints5 name glyphs then one blank before LV. Fill only
; that spare sixth glyph for07, retaining the preceding name tile attribute.
; DP61 is the existing roster-box base; all other names/layouts are untouched.
PeExchangeSixthGlyphV2:
    lda.w $9A90
    and.w #$00FF
    cmp.w #$0007
    bne .done
    ldx.w $0061
    lda.w $9AE5
    and.w #$00FF
    pha
    lda.w $00CE,x
    and.w #$FF00
    ora $01,s
    sta.w $00D0,x
    pla
.done:
    rts
PeExchangeWrappersV1End:
