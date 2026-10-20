; Project Epoch: additive private Schala tile-bank adapter v4, 2026-10-20.
; Preserves the v3 source; extends only its exact guarded tile bound. Original source; no ROM emitter.
; Proposed root-owned placement413000. Hook [C0E699,C0E69D) is JML here,
; replacing A5 CF C9 7F (LDA dpCF / CMP #7F), with no new call frame.
;
; Entry: native E0, M8/X16, binary, D0100, DBR00. X is the computed source
; tile offset, Y the existing cache destination, DP C5 the saved callerY.
; The original C0E687 routine's near-return frame remains on the stack.
; All nonqualifying calls restore the exact replaced-span A/B/X/Y/P/D/DBR/SP
; then JML C0E69D; the canonical7F/D2/D3/D4/defaultD5 dispatch is untouched.
;
; Qualified route: CF42/CDCE0000; DP6D byte matches the selected object word
; at019B (high019C zero); that object is role02/logical07, roster2982=07,
; and its published graphics pointer is420000. X must be32-byte aligned and
; at most0F20, the last complete tile of the provider's0F40-byte payload.
; This is a consumer-specific route, not a generic relocation decoder.
;
; Qualification adds PHP1/PHA1/PHX2 =4 bytes and releases them completely.
; Candidate copy then repeats the canonical header (PHB + temporaryPHA,
; peak2), with sixteen word reads from42 rather thanD5. All32 destination
; bytes are the original $7F:Y..Y+31 sequence. JML C0E72D reuses the original
; PLB / TYA / CLC / ADC #0020 / STA2181 / LDY C5 / RTS. That tail restores
; DBR/Y, publishes the next WRAM-port pointer and consumes the bankC0 near
; frame. Final X/P/A and hardware effects equal that same copy/tail with
; source bank42; finalA=entryY+0020, C/V from that add, N/Z from savedY.
; Actual cache/stack ownership and instruction-owned reads/writes require
; the separate bounded native observer. No IRQ/NMI or whole-renderer proof.

Pc07SchalaTileBankV4:
    lda.b $CF
    cmp.b #$7F
    php
    pha
    phx
    lda.b $CF
    cmp.b #$42
    bne .original_pop
    lda.b $CD
    ora.b $CE
    bne .original_pop
    lda.b $6D
    cmp.l $7E019B
    bne .original_pop
    lda.l $7E019C
    bne .original_pop
    ldx.w $019B
    lda.l $7E1100,x
    cmp.b #$02
    bne .original_pop
    lda.l $7E1101,x
    cmp.b #$07
    bne .original_pop
    lda.l $7E2982
    cmp.b #$07
    bne .original_pop
    lda.l $7E1200,x
    cmp.b #$42
    bne .original_pop
    lda.l $7E1280,x
    bne .original_pop
    lda.l $7E1281,x
    bne .original_pop
    plx
    cpx.w #$0F21
    bcs .original
    txa
    and.b #$1F
    bne .original
    pla
    plp
    brl Pc07SchalaTileCopyV4
.original_pop:
    plx
.original:
    pla
    plp
    jml $C0E69D

Pc07SchalaTileCopyV4:
    phb
    lda.b #$7F
    pha
    plb
    rep #$20
Pc07SchalaTileReadsV4:
    lda.l $420000,x
    sta.w $0000,y
    lda.l $420002,x
    sta.w $0002,y
    lda.l $420004,x
    sta.w $0004,y
    lda.l $420006,x
    sta.w $0006,y
    lda.l $420008,x
    sta.w $0008,y
    lda.l $42000A,x
    sta.w $000A,y
    lda.l $42000C,x
    sta.w $000C,y
    lda.l $42000E,x
    sta.w $000E,y
    lda.l $420010,x
    sta.w $0010,y
    lda.l $420012,x
    sta.w $0012,y
    lda.l $420014,x
    sta.w $0014,y
    lda.l $420016,x
    sta.w $0016,y
    lda.l $420018,x
    sta.w $0018,y
    lda.l $42001A,x
    sta.w $001A,y
    lda.l $42001C,x
    sta.w $001C,y
    lda.l $42001E,x
    sta.w $001E,y
Pc07SchalaTileTailV4:
    jml $C0E72D
Pc07SchalaTileBankV4End:
