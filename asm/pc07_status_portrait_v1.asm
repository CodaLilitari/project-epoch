; Private full-size STATUS portrait routing. No cartridge data is replaced.
; Tile entry is native M8/X8 at C2EC3E; palette entry M16/X16 at C2EC8B.
; Qualification: D0/DBR7E, status tilemap2EDE/attributes0E, matching selected
; identity9A90/0D46, and exact original indices. Epoch naming uses2E96/16.
; New graphics4A1000, palette4A1480, fixed name4A14A0. Originals remain in ROM.
; Status's legacy five-cell name originates from the vehicle buffer for id07.
; Replace only six displayed name glyph lowbytes; preserve all tile attributes,
; work buffers and Epoch's stored/name-entry identity. No editable name added.
; Visible list rows2EC6/3046/31C6 are qualified by0D5F[0413+row], scroll0..5.
; Their sixth glyph replaces a blank; the following LV label remains intact.
; The first existing36-tile VRAM slot is refreshed for both PC07 and Crono.
; Only a complete aligned8-byte queue record is committed; index publishes last.
; No persistent scratch, slot-state cache, canonical data-table edits or IRQ mask.
; Explicit stack peak JSL3 + PHP1 + A2 + X2 + Y2 + temporary DBR1 =11.
; This local bound is not a proof of physical stack or interrupt ownership.

Pc07StatusPortraitTilesV1:
    php
    rep #$30
    pha
    phx
    phy
    tdc
    beq +
    brl .original
+
    sep #$20
    phb
    pla
    cmp.b #$7E
    beq +
    brl .original
+
    rep #$20
    lda.l $7E0061
    cmp.w #$2EDE
    beq +
    brl .original
+
    sep #$20
    lda.l $7E0001
    cmp.b #$0E
    beq +
    brl .original
+
    lda.l $7E0D46
    cmp.b #$08
    bcc .identity
    brl .original
.identity
    cmp.l $7E9A90
    beq +
    brl .original
+
    txa
    cmp.l $7E0D46
    beq +
    brl .original
+
    cmp.b #$07
    bne .rows
    lda.l $4A14A0
    sta.l $7E2FAC
    lda.l $4A14A1
    sta.l $7E2FAE
    lda.l $4A14A2
    sta.l $7E2FB0
    lda.l $4A14A3
    sta.l $7E2FB2
    lda.l $4A14A4
    sta.l $7E2FB4
    lda.l $4A14A5
    sta.l $7E2FB6
.rows
    rep #$20
    lda.l $7E0413
    and.w #$00FF
    cmp.w #$0006
    bcc +
    brl .after_names
+
    tax
    sep #$20
    lda.l $7E0D5F,x
    cmp.b #$07
    bne .row1
    lda.l $4A14A0
    sta.l $7E2EC6
    lda.l $4A14A1
    sta.l $7E2EC8
    lda.l $4A14A2
    sta.l $7E2ECA
    lda.l $4A14A3
    sta.l $7E2ECC
    lda.l $4A14A4
    sta.l $7E2ECE
    lda.l $4A14A5
    sta.l $7E2ED0
.row1
    inx
    lda.l $7E0D5F,x
    cmp.b #$07
    bne .row2
    lda.l $4A14A0
    sta.l $7E3046
    lda.l $4A14A1
    sta.l $7E3048
    lda.l $4A14A2
    sta.l $7E304A
    lda.l $4A14A3
    sta.l $7E304C
    lda.l $4A14A4
    sta.l $7E304E
    lda.l $4A14A5
    sta.l $7E3050
.row2
    inx
    lda.l $7E0D5F,x
    cmp.b #$07
    bne .after_names
    lda.l $4A14A0
    sta.l $7E31C6
    lda.l $4A14A1
    sta.l $7E31C8
    lda.l $4A14A2
    sta.l $7E31CA
    lda.l $4A14A3
    sta.l $7E31CC
    lda.l $4A14A4
    sta.l $7E31CE
    lda.l $4A14A5
    sta.l $7E31D0
.after_names
    sep #$20
    lda.l $7E0D46
    cmp.b #$07
    beq .queue
    cmp.b #$00
    beq .queue
    brl .original
.queue
    lda.l $7E0D11
    cmp.b #$F1
    bcc +
    brl .original
+
    and.b #$07
    beq +
    brl .original
+
    rep #$20
    lda.l $7E0D11
    and.w #$00FF
    tax
    lda.w #$2010
    sta.l $7E0C00,x
    lda.l $7E0D46
    and.w #$00FF
    beq .crono
    lda.w #$1000
    sta.l $7E0C02,x
    lda.w #$804A
    bra .record_tail
.crono
    lda.w #$0000
    sta.l $7E0C02,x
    lda.w #$80FF
.record_tail
    sta.l $7E0C04,x
    lda.w #$0004
    sta.l $7E0C06,x
    sep #$20
    txa
    cld
    clc
    adc.b #$08
    sta.l $7E0D11
.original
    rep #$30
    ply
    plx
    pla
    plp
    lda.l $FFCE70,x
    rtl

Pc07StatusPortraitPaletteV1:
    php
    rep #$30
    pha
    phx
    phy
    cmp.w #$001F
    beq +
    brl .original
+
    cpx.w #$CE50
    beq +
    brl .original
+
    cpy.w #$94E0
    beq +
    brl .original
+
    tdc
    beq +
    brl .original
+
    sep #$20
    phb
    pla
    cmp.b #$7E
    beq +
    brl .original
+
    rep #$20
    lda.l $7E0061
    cmp.w #$2EDE
    beq +
    brl .original
+
    sep #$20
    lda.l $7E0001
    cmp.b #$0E
    beq +
    brl .original
+
    lda.l $7E0D46
    cmp.b #$07
    beq +
    brl .original
+
    lda.l $7E9A90
    cmp.b #$07
    beq +
    brl .original
+
    rep #$30
    ply
    plx
    pla
    plp
    ldx.w #$1480
    mvn $7E,$4A
    ldx.w #$CE70
    inc.w $0D15
    rtl
.original
    rep #$30
    ply
    plx
    pla
    plp
    mvn $7E,$FF
    inc.w $0D15
    rtl
