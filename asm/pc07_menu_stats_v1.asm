; Bounded menu-startup derived-stat extension, private diagnostic v1.
; Hook C299C1 replaces LDA dp02 / CMP #0007; original BCC at C299C6 stays.
; Native entry E0,M16,X16,D0,DBR7E. The canonical enclosing loop establishes
; widths and owns DP02. ID07 is published only by the accepted sidecar loader;
; safe-empty leaves its identity zero. No new scratch or persistent state.
; For counter7 AND live identity07 only, clear Carry to admit one final pass.
; Every other counter/identity has the exact original A/P comparison result.
; X/Y/D/DBR and all nonstack memory are unchanged. Peak stack: JSL3 + PHP1
; + PHA2 = 6 bytes; this is local use, not a whole-menu interrupt bound.
Pc07MenuRecomputeGateV1:
    lda.b $02
    cmp.w #$0007
    bne .done
    php
    pha
    sep #$20
    lda.l $7E2830
    cmp.b #$07
    bne .refuse
    rep #$20
    pla
    plp
    clc
    rtl
.refuse
    rep #$20
    pla
    plp
.done
    rtl
