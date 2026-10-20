; Private PC07 all-range caster Attack consumers, native E0/M8/X16.
; Original source only. A separate guarded builder owns placement and hooks.
; Candidate windows: $490100..$490380, five independent $80-byte extents.
; Preserve X/Y/hidden B/D/DBR; incoming P restored before final LDA sets N/Z.
; All qualifier and publication memory uses long addressing. No REP/SEP/XCE.
; Deepest explicit stack: JSL3 + PHP1 = 4 bytes, including fallback helpers.
; That bound excludes interrupts and does not establish physical stack ownership.
;
; Qualifiers: actual Attack type1, actor slot2, roster07, exact current slot2
; graphics $420000 and assembly $421000. Selector/approach X must also be0007.
; Sound X is the equipped weapon ID, so sound uses owner0/map2/package04-or10.
; Failed selector/approach checks tail-call the unchanged installed helper;
; failed sound checks execute the exact original long-indexed table read.
; Keep action75, equipped weapon, pending results, NPC data and Epoch untouched.
;
; The five selected visual fields are an explicitly inspected effect family,
; not a logical donor/equipment swap. Runtime appearance remains to be checked.
; Audio4D shares the canonical audio18 sound-ID namespace; original actor pan
; stays intact. The unrequested7D path is unchanged; no impact override exists.
; This source does not claim auditory review or native execution.

; Replace existing JSL at $C14A44; fallback $410055.
; Facing already published. Clear only $7E9930 so near and far return.
Pc07CasterApproachV1:
    php
    cpx.w #$0007
    bne .original
    lda.l $7EAE91
    cmp.b #$02
    bne .original
    lda.l $7EAE92
    cmp.b #$01
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
    plp
    lda.b #$00
    sta.l $7E9930
    rtl
.original:
    plp
    jml $410055
Pc07CasterApproachV1End:

; Replace existing JSL at $C143C4; fallback $410067.
; Five visual fields already loaded; override before C14401 resolves pointers.
Pc07CasterNormalV1:
    php
    cpx.w #$0007
    bne .original
    lda.l $7EAE91
    cmp.b #$02
    bne .original
    lda.l $7EAE92
    cmp.b #$01
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
    lda.b #$07
    sta.l $7E987A
    lda.b #$0B
    sta.l $7E987B
    lda.b #$1A
    sta.l $7E987E
    lda.b #$09
    sta.l $7E9881
    lda.b #$04
    sta.l $7E9884
    plp
    lda.b #$04
    rtl
.original:
    plp
    jml $410067
Pc07CasterNormalV1End:

; Replace existing JSL at $C143F8; fallback $410079.
; Five visual fields already loaded; override before C14401 resolves pointers.
Pc07CasterPathV1:
    php
    cpx.w #$0007
    bne .original
    lda.l $7EAE91
    cmp.b #$02
    bne .original
    lda.l $7EAE92
    cmp.b #$01
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
    lda.b #$07
    sta.l $7E987A
    lda.b #$0B
    sta.l $7E987B
    lda.b #$1A
    sta.l $7E987E
    lda.b #$09
    sta.l $7E9881
    lda.b #$04
    sta.l $7E9884
    plp
    lda.b #$04
    rtl
.original:
    plp
    jml $410079
Pc07CasterPathV1End:

; Replace existing JSL at $C1438B; fallback $41008B.
; Five visual fields already loaded; override before C14401 resolves pointers.
Pc07CasterCriticalV1:
    php
    cpx.w #$0007
    bne .original
    lda.l $7EAE91
    cmp.b #$02
    bne .original
    lda.l $7EAE92
    cmp.b #$01
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
    lda.b #$07
    sta.l $7E987A
    lda.b #$0B
    sta.l $7E987B
    lda.b #$1A
    sta.l $7E987E
    lda.b #$09
    sta.l $7E9881
    lda.b #$04
    sta.l $7E9884
    plp
    lda.b #$10
    rtl
.original:
    plp
    jml $41008B
Pc07CasterCriticalV1End:

; Replace LDA.l $CD6D4C,X at $C161EF.
Pc07CasterSwingSoundV1:
    php
    lda.l $7EAE91
    cmp.b #$02
    bne .original
    lda.l $7EAE92
    cmp.b #$01
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
    lda.l $7EA010
    bne .original
    lda.l $7EA014
    cmp.b #$02
    bne .original
    lda.l $7E9877
    cmp.b #$04
    beq .ranged
    cmp.b #$10
    bne .original
.ranged:
    plp
    lda.b #$4D
    rtl
.original:
    plp
    lda.l $CD6D4C,x
    rtl
Pc07CasterSwingSoundV1End:

