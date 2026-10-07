; Source-only native candidates for the bounded PC07 donor prototype.
; No address allocation, hook installation, or runtime acceptance is implied.
; Entry for every routine: native mode, A8/X16, entered by JSL.
; No routine changes X/Y/D/DBR. Hidden B is preserved. Incoming P is restored
; before the final LDA, which supplies exactly the intended N/Z result.
;
; These are consumer-specific graphics/name/action lookups, never a global
; logical-ID rewrite. Epoch's naming selector07 and 7E2C4D..52 stay untouched.

; Replaces C0448D..C04491: STA $4202 / LDA #$05 (five bytes).
; Field ABI additionally requires DBR00 and X=current doubled object offset.
; Only the actual active role2 object with logical07 and roster07 gets donor0.
; Every other invocation publishes its original A low to the multiply unit.
; Deepest additional stack is five bytes including the JSL frame.
Pc07FieldGraphicsDonorV1:
    php
    pha
    cmp.b #$07
    bne .original
    lda.l $7E1101,x
    cmp.b #$07
    bne .original
    lda.l $7E1100,x
    cmp.b #$02
    bne .original
    lda.l $7E2982
    cmp.b #$07
    bne .original
    cpx.w $019B
    bne .original
    pla
    lda.b #$00
    bra .publish
.original:
    pla
.publish:
    sta.w $4202
    plp
    lda.b #$05
    rtl
Pc07FieldGraphicsDonorV1End:

; For the named logical-PC table consumer only, X07 selects donor00.
; Every X other than0007 uses the exact original long-indexed table read.
; Restoring P after CPX prevents leaking the comparison's carry flag.
; Deepest additional stack is four bytes including the JSL frame.
macro Pc07DonorRead(label, address)
<label>:
    php
    cpx.w #$0007
    bne ?original
    plp
    lda.l <address>
    rtl
?original:
    plp
    lda.l <address>,x
    rtl
endmacro

; CCE616's temporary battle display name; never the Epoch name-entry path.
%Pc07DonorRead(Pc07BattleNameDonorV1, $CCF846)
; C1BFFF: donor00's existing ordinary Attack action75.
%Pc07DonorRead(Pc07BasicActionDonorV1, $CC2583)
; C14A44: donor00's approach policy.
%Pc07DonorRead(Pc07ApproachDonorV1, $CCF63C)
; C143C4 / C143F8 / C1438B: normal, pathfinding and critical selectors.
%Pc07DonorRead(Pc07NormalAttackSelectorV1, $CD4000)
%Pc07DonorRead(Pc07PathAttackSelectorV1, $CD4007)
%Pc07DonorRead(Pc07CriticalAttackSelectorV1, $CD400E)
Pc07DonorReadAdaptersV1End:
