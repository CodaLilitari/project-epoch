; Private full-status portrait v2. Separately derived from the accepted17b parent.
; Preserves rejected v1 unchanged; fixes its observed VBlank/HDMA overrun.
; A fourth initial forced-blank preload descriptor places36tiles at VRAMword
; 1B00..1D40. All three original preload records and all seven faces stay exact.
; Menu-specific source/native census is required; this is not global VRAM ownership.
; No per-redraw transfer, shared Crono slot, persistent cache, or new WRAM owner.
; Status PC07 lowtileB0 plus temporaryDP01=0D yields0DB0..0DD3, palette3.
; Own palette branch restoresDP01=0E before the original continuation.
; Six fixed Schala glyphs replace only visible name lowbytes; all other selected
; PCs restore the sixth detail lowbyte00. Vehicle name and NPC assets untouched.
; Preload entryC29751 is nativeM16X16 AFFFF XFCA7 Y0C18 D0 DBR7E;
; return emulates SEP20/LDA20 rather than18 only in this exact qualified context.
; Tile/palette contexts retain v1 qualification, with palette DP01 now0D.
; Explicit stack peak11 including JSL and temporary DBR; not interrupt ownership.

Pc07StatusPortraitTilesV2:
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
    beq .schala_name
    lda.b #$00
    sta.l $7E2FB6
    bra .rows
.schala_name
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
    bne .original
    lda.b #$0D
    sta.l $7E0001
    rep #$30
    ply
    plx
    pla
    plp
    lda.b #$B0
    rtl
.original
    rep #$30
    ply
    plx
    pla
    plp
    lda.l $FFCE70,x
    rtl

Pc07StatusPortraitPaletteV2:
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
    cmp.b #$0D
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
    lda.b #$0E
    sta.l $7E0001
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

Pc07StatusPortraitPreloadV2:
    php
    rep #$30
    pha
    phx
    phy
    cmp.w #$FFFF
    bne .original
    cpx.w #$FCA7
    bne .original
    cpy.w #$0C18
    bne .original
    tdc
    bne .original
    sep #$20
    phb
    pla
    cmp.b #$7E
    bne .original
    rep #$20
    lda.w #$1B00
    sta.l $7E0C18
    lda.w #$1000
    sta.l $7E0C1A
    lda.w #$804A
    sta.l $7E0C1C
    lda.w #$0004
    sta.l $7E0C1E
    rep #$30
    ply
    plx
    pla
    plp
    sep #$20
    lda.b #$20
    rtl
.original
    rep #$30
    ply
    plx
    pla
    plp
    sep #$20
    lda.b #$18
    rtl
