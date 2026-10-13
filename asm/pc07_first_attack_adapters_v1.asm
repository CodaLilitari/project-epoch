; Project Epoch: uninstalled, fixed-slot diagnostic candidate v1, 2026-10-13.
; Original source. No org/base, allocation, hook emission, or ROM is supplied.
; Include the separately pinned asm/pc07_donor_read_adapters_v2.asm unchanged
; for its field helper and six consumer-specific donor-read helpers.
;
; Common required entry: native E0, M8/X16, binary arithmetic, D0000,
; DBR7E, hidden B00, naturally entered through a JSL at the named hook.
; Exact admitted party is 00/01/07 with candidate07 in active slot2 only.
; Stable binding and equipment predicates are caller/observer obligations.
; These routines are NOT an admission checker or a generic invalid-ID API.
; In particular D760 never returns FF as a invented safe slot.
; All helpers balance their own stack; peak counts include the JSL frame.
; This does not establish physical stack ownership or interrupt compatibility.

; [FDB298,FDB29D): TAY / TXA / STA $B1BE,Y. JSL + NOP.
; A is logical ID, X is active slot. Suppress only the illegal map[07] store.
; Preserve Y=logical ID, A=slot, and original TXA flags. Peak 4 bytes.
Pc07BattleMapPublishV1:
    php
    cmp.b #$07
    beq .candidate
    plp
    tay
    txa
    sta.w $B1BE,y
    rtl
.candidate:
    plp
    tay
    txa
    rtl

; Shared [C1C975,C1C97A), [C1CA29,C1CA2E), [C1CCDA,C1CCDF).
; LDA $AEFF,X / CMP #$FF -> JSL + NOP. X remains the active slot.
; PC07 takes the existing FF exit; other IDs/FF replay the original result.
; CMP overwrites C/N/Z exactly as the original final comparison. Peak 3.
Pc07EmptyTechEntryV1:
    lda.w $AEFF,x
    cmp.b #$07
    bne .canonical
    lda.b #$FF
.canonical:
    cmp.b #$FF
    rtl

; [FDAF55,FDAF59): STA.l $001C4C,X -> JSL.
; Fixed donor weapon55 has ownership mask80 and donor00 remains in slot0.
; The candidate's weapon record at X000A instead publishes actor mask20.
; Entry A80, DP02=2, roster/AF0A slot2=07 are externally required.
; Original STA does not change flags: restore all A/P exactly. Peak 5.
Pc07WeaponOwnerV1:
    php
    pha
    cmp.b #$80
    bne .original
    cpx.w #$000A
    bne .original
    lda.b $02
    cmp.b #$02
    bne .original
    lda.w $2982
    cmp.b #$07
    bne .original
    lda.w $AF0C
    cmp.b #$07
    bne .original
    lda.b #$20
    sta.l $001C4C,x
    pla
    plp
    rtl
.original:
    pla
    sta.l $001C4C,x
    plp
    rtl

; [CCE980,CCE98A): LDA roster,Y / ASL / PHA / CLC / ADC roster,Y / TAX.
; Replacement: JSL here / PHA / TXA / NOP / NOP / NOP / NOP (10 bytes).
; Y=active slot, stable roster ID00..07. Map07 to graphics donor00 only.
; Return A=2*donor and X=3*donor with balanced helper stack. Inline PHA
; creates the original one-byte saved doubled index; inline TXA supplies
; original A and N/Z at CCE98A. Original bounded ADC produces C=V=0.
; Y/D/DBR/B preserved. Peak 5; continuation SP is original entry SP-1.
Pc07BattleGraphicsIndicesV1:
    php
    lda.w $2980,y
    cmp.b #$07
    bne .resolved
    lda.b #$00
.resolved:
    pha
    asl
    clc
    adc $01,s
    tax
    pla
    asl
    plp
    clc
    clv
    rtl

; [C18050,C18054): LDA $B1BE,X / INC -> JSL.
; X is logical ID; return slot2+1=3 for07. Preserve X and original C/V.
; No B1C5 read. Peak 4 bytes.
Pc07InitialTurnSlotV1:
    php
    cpx.w #$0007
    bne .original
    plp
    lda.b #$02
    inc
    rtl
.original:
    plp
    lda.w $B1BE,x
    inc
    rtl

; [C1D55E,C1D562): LDA.l $CC249F,X -> JSL.
; Canonical action75 row selects target offset0 = 00/FF/FF, components
; 3A/80/80, with component3A MP cost0. X is target offset, NOT PC ID.
; Return07 only for this declared Attack in active slot2; the three
; original STA instructions then publish07/FF/FF with no donor00 prefix.
; All other admitted contexts perform the original read. Preserve C/V,
; hidden B, X/Y/D/DBR; N/Z come only from the final LDA. Peak 4 bytes.
Pc07AttackFirstParticipantV1:
    php
    cpx.w #$0000
    bne .original
    lda.w $AE92
    cmp.b #$01
    bne .original
    lda.w $B18C
    cmp.b #$75
    bne .original
    lda.w $B18B
    cmp.b #$02
    bne .original
    lda.w $AE91
    cmp.b #$02
    bne .original
    lda.w $2982
    cmp.b #$07
    bne .original
    lda.w $AF01
    cmp.b #$07
    bne .original
    lda.w $AF0C
    cmp.b #$07
    bne .original
    plp
    lda.b #$07
    rtl
.original:
    plp
    lda.l $CC249F,x
    rtl

; [C1D605,C1D60A): LDA $B1BE,X / CMP #$FF -> JSL + NOP.
; X remains logical07 for the candidate; A=slot2 and C/N/Z=0.
; Canonical values execute the original map read and comparison. Peak 4.
Pc07EffectActorSlotV1:
    php
    cpx.w #$0007
    bne .original
    plp
    lda.b #$02
    cmp.b #$FF
    rtl
.original:
    plp
    lda.w $B1BE,x
    cmp.b #$FF
    rtl

; [C1D760,C1D764): LDA $B1BE,X / TAX -> JSL.
; The next instruction indexes A0D1 by X. Valid candidate binding is a
; hard premise; FF would be an invalid large index, not a refusal result.
; Entry X logical07 becomes X0002/A02; B00 is required for 16-bit TAX.
; Preserve C/V; N/Z exactly match TAX. Peak 4 bytes.
Pc07MpActorSlotV1:
    php
    cpx.w #$0007
    bne .original
    plp
    lda.b #$02
    tax
    rtl
.original:
    plp
    lda.w $B1BE,x
    tax
    rtl
Pc07BattleAdaptersCandidateV1End:
