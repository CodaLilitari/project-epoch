; Source-only native candidates for the bounded PC07 donor prototype.
; No address allocation, hook installation, or runtime acceptance is implied.
; Entry for every routine: native mode, A8/X16, entered by JSL.
; All routines preserve X/D/DBR and hidden B. Table readers preserve Y;
; the field routine increments Y once, matching the replaced INY. Incoming P
; is restored before the final LDA supplies the intended N/Z result.
;
; These are consumer-specific graphics/name/action lookups, never a global
; logical-ID rewrite. Epoch's naming selector07 and 7E2C4D..52 stay untouched.

; Replaces [C0448D,C04493): STA $4202 / INY / LDA #$05 (six bytes).
; Candidate hook encoding is JSL plus two NOPs; no address is assigned.
; V1 is rejected: its stated five-byte span split LDA and omitted INY.
; Field ABI additionally requires DBR00 and X=current doubled object offset.
; Only the actual active role2 object with logical07 and roster07 gets donor0.
; Every other invocation publishes its original A low to the multiply unit.
; Deepest additional stack is five bytes including the JSL frame.
Pc07FieldGraphicsDonorV2:
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
    iny
    lda.b #$05
    rtl
Pc07FieldGraphicsDonorV2End:

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
%Pc07DonorRead(Pc07BattleNameDonorV2, $CCF846)
; C1BFFF: donor00's existing ordinary Attack action75.
%Pc07DonorRead(Pc07BasicActionDonorV2, $CC2583)
; C14A44: donor00's approach policy.
%Pc07DonorRead(Pc07ApproachDonorV2, $CCF63C)
; C143C4 / C143F8 / C1438B: normal, pathfinding and critical selectors.
%Pc07DonorRead(Pc07NormalAttackSelectorV2, $CD4000)
%Pc07DonorRead(Pc07PathAttackSelectorV2, $CD4007)
%Pc07DonorRead(Pc07CriticalAttackSelectorV2, $CD400E)
Pc07DonorReadAdaptersV2End:
