; Original Project Epoch package helper, synthetic conformance v0.
; Pure relocatable include: no cartridge, hook, allocation, or game data.
; Caller defines PE_PH_SCRATCH ($80-byte private synthetic workspace),
; PE_PH_BINDINGS (16*6 bytes: valid word, root word, bank word), and tails.
; Native M0/X0, D=0000, DBR=7E. IRQ/NMI sources disabled by synthetic harness.
; Source banks 7E/7F are diagnostic WRAM identities only, not game ownership.
; Descriptor/stream fixture spans must be immutable and disjoint from helper,
; registry, scratch, stack, and publication spans for the entire invocation.
; Static authored-stream certification remains a separate prerequisite.

!PH_INDEX = $00
!PH_ROOT = $02
!PH_BANK = $04
!PH_MASK0 = $06
!PH_MASK1 = $08
!PH_SIZE = $0A
!PH_END = $0C
!PH_CARRY = $0E
!PH_COUNT = $10
!PH_CURSOR = $12
!PH_REMAIN = $14
!PH_MASK = $16
!PH_OWNER = $18
!PH_STATUS = $1A
!PH_BRANCH = $1C
!PH_POINTER = $1E
!PH_COUNT0 = $20

macro PH_RequireZero()
    BEQ ?ok
    BRL EpochPackageHelper_Refuse
?ok:
endmacro

macro PH_RequireCarryClear()
    BCC ?ok
    BRL EpochPackageHelper_Refuse
?ok:
endmacro

EpochPackageHelper_Start:
    PHP
    PHA
    PHX
    PHY
    PHB

    ; Canonical dispatch does not inspect the branch flag or registry.
    LDA.w $9877
    CMP.w #$0100
    %PH_RequireCarryClear()
    CMP.w #$0080
    BCS .high
    PLB
    PLY
    PLX
    PLA
    PLP
    LDA.w $9877
    ASL A
    JML !PE_PH_CANONICAL_TAIL
.high:
    CMP.w #$0090
    %PH_RequireCarryClear()
    LDA.w $A0B3
    AND.w #$FF00
    %PH_RequireZero()

    ; Preserve incoming I/D/V; arithmetic below must be binary.
    SEP #$20
    LDA.b $08,s
    STA.l !PE_PH_SCRATCH+!PH_STATUS
    REP #$20
    CLD
    LDA.w $9877
    SEC
    SBC.w #$0080
    ASL A
    STA.l !PE_PH_SCRATCH+!PH_INDEX
    ASL A
    CLC
    ADC.l !PE_PH_SCRATCH+!PH_INDEX
    TAX
    LDA.l !PE_PH_BINDINGS,X
    CMP.w #$0001
    %PH_RequireZero()
    LDA.l !PE_PH_BINDINGS+$04,X
    CMP.w #$007E
    BEQ .bank_ok
    CMP.w #$007F
    %PH_RequireZero()
.bank_ok:
    STA.l !PE_PH_SCRATCH+!PH_BANK
    LDA.l !PE_PH_BINDINGS+$02,X
    CMP.w #$FFFD
    %PH_RequireCarryClear()
    STA.l !PE_PH_SCRATCH+!PH_ROOT
    TAX
    LDA.w $A0B3
    STA.l !PE_PH_SCRATCH+!PH_BRANCH

    ; Read source through DBR while every scratch/output access is long.
    SEP #$20
    LDA.l !PE_PH_SCRATCH+!PH_BANK
    PHA
    PLB
    REP #$20
    LDA.w $0000,X
    XBA
    STA.l !PE_PH_SCRATCH+!PH_MASK0
    INX
    INX
    LDA.w $0000,X
    XBA
    STA.l !PE_PH_SCRATCH+!PH_MASK1
    INX
    INX
    TXA
    STA.l !PE_PH_SCRATCH+!PH_CURSOR
    LDA.l !PE_PH_SCRATCH+!PH_MASK0
    JSR EpochPackageHelper_CountBits
    STA.l !PE_PH_SCRATCH+!PH_COUNT0
    LDA.l !PE_PH_SCRATCH+!PH_MASK1
    JSR EpochPackageHelper_CountBits
    CLC
    ADC.l !PE_PH_SCRATCH+!PH_COUNT0
    STA.l !PE_PH_SCRATCH+!PH_COUNT
    STA.l !PE_PH_SCRATCH+!PH_REMAIN
    ASL A
    CLC
    ADC.w #$0004
    STA.l !PE_PH_SCRATCH+!PH_SIZE
    CLC
    ADC.l !PE_PH_SCRATCH+!PH_ROOT
    STA.l !PE_PH_SCRATCH+!PH_END
    LDA.w #$0000
    ADC.w #$0000
    STA.l !PE_PH_SCRATCH+!PH_CARRY
    BEQ .extent_ok
    LDA.l !PE_PH_SCRATCH+!PH_END
    %PH_RequireZero()
.extent_ok:
    ; Validate all pointers in both masks before the first publication.
    LDA.l !PE_PH_SCRATCH+!PH_REMAIN
    BEQ .validated
.preflight:
    LDA.l !PE_PH_SCRATCH+!PH_CURSOR
    TAX
    LDA.w $0000,X
    CMP.w #$FFFF
    BNE .not_ffff
    BRL EpochPackageHelper_Refuse
.not_ffff:
    STA.l !PE_PH_SCRATCH+!PH_POINTER
    CMP.l !PE_PH_SCRATCH+!PH_ROOT
    BCC .pointer_ok
    LDA.l !PE_PH_SCRATCH+!PH_CARRY
    BEQ .check_low_end
    BRL EpochPackageHelper_Refuse
.check_low_end:
    LDA.l !PE_PH_SCRATCH+!PH_POINTER
    CMP.l !PE_PH_SCRATCH+!PH_END
    BCS .pointer_ok
    BRL EpochPackageHelper_Refuse
.pointer_ok:
    INX
    INX
    TXA
    STA.l !PE_PH_SCRATCH+!PH_CURSOR
    LDA.l !PE_PH_SCRATCH+!PH_REMAIN
    DEC A
    STA.l !PE_PH_SCRATCH+!PH_REMAIN
    BNE .preflight
.validated:
    LDA.l !PE_PH_SCRATCH+!PH_ROOT
    STA.l $7E9878
    CLC
    ADC.w #$0004
    STA.l !PE_PH_SCRATCH+!PH_CURSOR
    LDA.l !PE_PH_SCRATCH+!PH_MASK1
    STA.l $7E0082
    LDA.l !PE_PH_SCRATCH+!PH_BRANCH
    BEQ .primary
    LDA.l !PE_PH_SCRATCH+!PH_COUNT0
    ASL A
    CLC
    ADC.l !PE_PH_SCRATCH+!PH_CURSOR
    STA.l !PE_PH_SCRATCH+!PH_CURSOR
    LDA.l !PE_PH_SCRATCH+!PH_MASK1
    BRA .mask_chosen
.primary:
    LDA.l !PE_PH_SCRATCH+!PH_MASK0
.mask_chosen:
    STA.l !PE_PH_SCRATCH+!PH_MASK
    STA.l $7E0080
    LDA.w #$0000
    STA.l !PE_PH_SCRATCH+!PH_OWNER
    ; Native clears only A0B3, preserving its already-zero adjacent byte.
    SEP #$20
    STA.l $7EA0B3
    REP #$20
.publish_loop:
    LDA.l !PE_PH_SCRATCH+!PH_MASK
    ASL A
    STA.l !PE_PH_SCRATCH+!PH_MASK
    STA.l $7E0080
    BCC .next_owner
    LDA.l !PE_PH_SCRATCH+!PH_CURSOR
    TAX
    LDA.w $0000,X
    STA.l !PE_PH_SCRATCH+!PH_POINTER
    INX
    INX
    TXA
    STA.l !PE_PH_SCRATCH+!PH_CURSOR
    LDA.l !PE_PH_SCRATCH+!PH_OWNER
    TAX
    LDA.w #$0001
    STA.l $7E5DAC,X
    TXA
    ASL A
    ASL A
    TAX
    LDA.l !PE_PH_SCRATCH+!PH_POINTER
    STA.l $7E5DBD,X
    LDA.l !PE_PH_SCRATCH+!PH_BANK
    STA.l $7E5DBF,X
.next_owner:
    LDA.l !PE_PH_SCRATCH+!PH_OWNER
    INC A
    STA.l !PE_PH_SCRATCH+!PH_OWNER
    CMP.w #$0010
    BEQ .done
    BRL .publish_loop
.done:
    ; Replace only the saved P byte; restore stack/DBR before setting outputs.
    SEP #$20
    LDA.l !PE_PH_SCRATCH+!PH_STATUS
    AND.b #$4C
    ORA.b #$23
    STA.b $08,s
    REP #$20
    PLB
    PLY
    PLX
    PLA
    LDA.l !PE_PH_SCRATCH+!PH_CURSOR
    TAX
    LDY.w #$0010
    LDA.w #$0000
    PLP
    JML !PE_PH_SUCCESS_TAIL

EpochPackageHelper_Refuse:
    ; Every branch here has the original eight-byte saved context intact.
    REP #$20
    PLB
    PLY
    PLX
    PLA
    PLP
    JML !PE_PH_REFUSAL_TAIL

EpochPackageHelper_CountBits:
    LDX.w #$0000
    LDY.w #$0010
.loop:
    ASL A
    BCC .next
    INX
.next:
    DEY
    BNE .loop
    TXA
    RTS
EpochPackageHelper_End:
