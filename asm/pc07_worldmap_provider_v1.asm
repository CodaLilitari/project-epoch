; Original diagnostic world-map provider candidate. No asset included here.
; Native entry premises: E0, M16/X16, D=$0000, binary arithmetic.
; The original C2 near caller frame remains on stack; never RTL here.
; Hooks replace exactly PHB / AND #$00FF. Vanilla dispatch preserves their
; post-state including P, then resumes the unmodified canonical suffix.
; Candidate placement is synthetic/proposed until the separate guard admits it.
!Main = $0400                 ; CPU480400, 0400 bytes
!AuxTop = $0800               ; CPU480800, 0040 bytes
!AuxBottom = $0840            ; CPU480840, 0040 bytes
!Palette = $0880              ; CPU480880, 0010 bytes

PeWorldMainHookV1:
    phb
    and.w #$00FF
    php
    cmp.w #$0007
    bne PeWorldMainDispatchNativeV1
    cpy.w #$B800
    bne PeWorldMainDispatchNativeV1
    plp
PeWorldMainCopyV1:
    ldx.w #!Main
    lda.w #$03FF
    mvn $7F,$48
    ; Preserve the canonical ID07 routine's post-register values.
    ldx.w #$B000
    clc
    clv
PeWorldMainReturnV1:
    jml $C22BCD              ; native PLB / RTS
PeWorldMainDispatchNativeV1:
    plp
PeWorldMainNativeV1:
    jml $C22BC0              ; native XBA following displaced AND

PeWorldAuxHookV1:
    phb
    and.w #$00FF
    php
    cmp.w #$0007
    bne PeWorldAuxDispatchNativeV1
    cpy.w #$BC80
    bne PeWorldAuxDispatchNativeV1
    plp
    ; These are the same two scratch words written by native ID07.
    lda.w #$ADC0
    sta.b $08
    sty.b $0A
PeWorldAuxTopCopyV1:
    ldx.w #!AuxTop
    lda.w #$003F
    mvn $7F,$48
PeWorldAuxBottomCopyV1:
    ldx.w #!AuxBottom
    ldy.w #$BE80
    lda.w #$003F
    mvn $7F,$48
    ldx.w #$B000
    clc
    clv
PeWorldAuxReturnV1:
    jml $C22BF9              ; native PLB / RTS
PeWorldAuxDispatchNativeV1:
    plp
PeWorldAuxNativeV1:
    jml $C22BD3              ; native XBA following displaced AND

PeWorldPaletteHookV1:
    phb
    and.w #$00FF
    php
    cmp.w #$0007
    bne PeWorldPaletteDispatchNativeV1
    cpy.w #$8DC0
    bne PeWorldPaletteDispatchNativeV1
    plp
PeWorldPaletteCopyV1:
    ldx.w #!Palette
    lda.w #$000F
    mvn $7F,$48
    ldx.w #$8EF0
    clc
    clv
PeWorldPaletteReturnV1:
    jml $C22900              ; native PLB / RTS
PeWorldPaletteDispatchNativeV1:
    plp
PeWorldPaletteNativeV1:
    jml $C228F1              ; native first ASL following displaced AND
PeWorldProviderEndV1:
