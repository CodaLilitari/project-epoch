; Project Epoch, private fixed-slot presentation candidate v1, 2026-10-13.
; Original relocatable source. No ROM mutation or production allocation.
; Root's diagnostic placement is $411000; provider bank is $42.
; Retail source is NPC09, never a replacement for canonical donor00.
;
; Every entry requires native E0 and M8. Battle entries require X16/D0/
; DBR7E; field publication requires X16/D0100/DBR00. Field timing requires
; X16/D0100/DBR00, but field bank selection accepts either original X width.
; No arithmetic depends on decimal mode. Hidden B, Y, D and DBR are preserved.
; These predicates restrict routing; they do not establish stack/interrupt
; ownership, stable binding, complete graphics semantics, or runtime success.
;
; Provider geometry: raw $420000, assembly $421000, primary $424000,
; four $0404-byte facings, timing $425100..$425503. Each facing and timing
; block has 256 selectable four-byte cells plus one copied entry-zero guard
; cell. The guard covers C13639/C13650's unconditional eight-byte init copy.

; [C0454D,C04552): LDA #01 / STA $1600,X. JSL + one NOP.
; X is the doubled object slot. $019B is an absolute WORD pointer to the
; third active object, NOT immediate #$019B (accepted fixture value is0010).
; Preserve all original CPU effects; add only the qualified pointer writes.
; Stack peak: JSL3 + PHP1 + full accumulator2 = 6 bytes.
Pc07SchalaFieldPublishV1:
    lda.b #$01
    sta.w $1600,x
    php
    rep #$20
    pha
    sep #$20
    cpx.w $019B
    bne .done
    lda.l $7E1100,x
    cmp.b #$02
    bne .done
    lda.l $7E1101,x
    cmp.b #$07
    bne .done
    lda.l $7E2982
    cmp.b #$07
    bne .done
    rep #$20
    lda.w #$0000
    sta.l $7E1280,x
    lda.w #$1000
    sta.l $7E1380,x
    lda.w #$0C00
    sta.l $7E1400,x
    lda.w #$0404
    sta.l $7E1480,x
    lda.w #$4000
    sta.l $7E1500,x
    lda.w #$5100
    sta.l $7E1580,x
    sep #$20
    lda.b #$42
    sta.l $7E1200,x
    sta.l $7E1300,x
.done:
    rep #$20
    pla
    plp
    rtl
Pc07SchalaFieldPublishV1End:

; [C0CBEE,C0CBF2): LDA #E4 / STA $D8. The three [$D6] primary reads
; already use a full bank byte. X is this object's index (usually X8).
; REP10 never truncates the original registers; PLP restores original widths.
; Published provider identity additionally requires base4000 and stride0404.
; All P except final LDA N/Z, and original X/Y/B, are preserved. Peak4.
Pc07SchalaFieldPrimaryBankV1:
    php
    rep #$10
    cpx.w $019B
    bne .original
    lda.l $7E1100,x
    cmp.b #$02
    bne .original
    lda.l $7E1101,x
    cmp.b #$07
    bne .original
    lda.l $7E2982
    cmp.b #$07
    bne .original
    lda.l $7E1500,x
    bne .original
    lda.l $7E1501,x
    cmp.b #$40
    bne .original
    lda.l $7E1480,x
    cmp.b #$04
    bne .original
    lda.l $7E1481,x
    cmp.b #$04
    bne .original
    plp
    lda.b #$42
    sta.b $D8
    rtl
.original:
    plp
    lda.b #$E4
    sta.b $D8
    rtl
Pc07SchalaFieldPrimaryBankV1End:

; [C0CA35,C0CA39) and [C0CA3D,C0CA41): LDA.l $E40000,X.
; X is a timing pointer, not an object. DP6D is an EIGHT-bit object index:
; C0A819 stores it under X8; do not read an unproved DP6E as its high byte.
; Compare low byte to slot-pointer019B and require pointer high019C=0, then
; load the qualified WORD slot pointer. X/P restored before final LDA.
; Published timing base5100 and effective X5100..5503 also must match. Peak6.
Pc07SchalaFieldTimingReadV1:
    php
    phx
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
    lda.l $7E1580,x
    bne .original_pop
    lda.l $7E1581,x
    cmp.b #$51
    bne .original_pop
    plx
    cpx.w #$5100
    bcc .original
    cpx.w #$5504
    bcs .original
    plp
    lda.l $420000,x
    rtl
.original_pop:
    plx
.original:
    plp
    lda.l $E40000,x
    rtl
Pc07SchalaFieldTimingReadV1End:

; [CCEA1C,CCEA28): replay LDX80/LDA82/STA966E,X/LDA83/STAA2C8,X.
; Pointer loop slot DP80=0002 and roster2982=07 select this provider.
; Other PCs' original pointers and stride remain unchanged. Low-word and
; bank publications use the already existing slot2 pointer cells only.
; A/P after replay are restored exactly, although the published stride is
; intentionally0404. Original X=slot, Y, B, D, DBR preserved. Peak6.
Pc07SchalaBattlePublishV1:
    ldx.b $80
    lda.b $82
    sta.w $966E,x
    lda.b $83
    sta.w $A2C8,x
    php
    rep #$20
    pha
    sep #$20
    cpx.w #$0002
    bne .done
    lda.l $7E2982
    cmp.b #$07
    bne .done
    rep #$20
    lda.w #$0000
    sta.l $7E1C5D
    lda.w #$1000
    sta.l $7E1C7E
    lda.w #$4000
    sta.l $7E1C9F
    lda.w #$5100
    sta.l $7E1CC0
    sep #$20
    lda.b #$42
    sta.l $7E1C5F
    sta.l $7E1C80
    sta.l $7E1CA1
    sta.l $7E1CC2
    lda.b #$04
    sta.l $7E9670
    sta.l $7EA2CA
.done:
    rep #$20
    pla
    plp
    rtl
Pc07SchalaBattlePublishV1End:

; Shared fixed-bank read replacement. Owner is a full DP WORD, not pointerX.
; Require slot0002, logical roster07, the exact published 24-bit base for
; this stream, and the inclusive provider pointer domain. A low comes from
; the selected ROM read; all other registers and incoming C/V/I/D/X/M stay
; as at the replaced LDA, with N/Z from the final read. Stack peak6.
macro Pc07SchalaBattleRead(label, owner, base_cell, base_hi, low, high)
<label>:
    php
    phx
    ldx.b <owner>
    cpx.w #$0002
    bne ?original_pop
    lda.l $7E2982
    cmp.b #$07
    bne ?original_pop
    lda.l <base_cell>
    bne ?original_pop
    lda.l <base_cell>+1
    cmp.b #<base_hi>
    bne ?original_pop
    lda.l <base_cell>+2
    cmp.b #$42
    bne ?original_pop
    plx
    cpx.w #<low>
    bcc ?original
    cpx.w #<high>
    bcs ?original
    plp
    lda.l $420000,x
    rtl
?original_pop:
    plx
?original:
    plp
    lda.l $E40000,x
    rtl
endmacro

; C12EBA/C12EEB: DP94 drives C12E4C slot*3 and C12E9F active-slot latch.
%Pc07SchalaBattleRead(Pc07SchalaBattleTimingOwner94V1, $94, $7E1CC0, $51, $5100, $5504)
%Pc07SchalaBattleRead(Pc07SchalaBattlePrimaryOwner94V1, $94, $7E1C9F, $40, $4000, $5010)
; C13639/C13650: DP80 loop initialized by STX80 atC135E7; increments0..2.
; C142D0/C14300: C14273 STX80 stores the selected slot; only fullWORD0002
; qualifies even though the original update scheduler ranges through slot10.
%Pc07SchalaBattleRead(Pc07SchalaBattleTimingOwner80V1, $80, $7E1CC0, $51, $5100, $5504)
%Pc07SchalaBattleRead(Pc07SchalaBattlePrimaryOwner80V1, $80, $7E1C9F, $40, $4000, $5010)
Pc07SchalaPresentationV1End:
