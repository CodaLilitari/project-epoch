; Original Project Epoch ROM-source package helper, synthetic v1.
; Pure relocatable include: no cartridge mutation, game hook or allocation.
; This separately versioned source preserves the completed v0 unchanged.
; Caller: native M0/X0, D=0000, DBR=7E; JML tails retain the incoming frame.
; IRQ/NMI sources disabled only by the isolated synthetic harness.
; PE_PH1_BINDINGS: sixteen 16-byte records (all words):
; valid=1, root, bank, exact descriptor end low, end carry, target count,
; reserved=0, reserved=0. End carry is 0/1; carry 1 requires low=0.
; PE_PH1_TARGETS: sixteen 64-byte arrays of at most 32 allowed direct offsets.
; Registry/target fixture identities and source bytes are immutable while called.
; Only banks 41/42 are admitted by this test version, never WRAM or mirrors.
; The exact target allowlist is transport authority, not stream certification.
; No pointed stream is read/executed here. Static command certification remains
; separate, and these synthetic byte fixtures are not installable packages.
; PE_PH1_SCRATCH is a diagnostic $80-byte WRAM fixture, not game ownership.

!PH1_INDEX = $00
!PH1_ROOT = $02
!PH1_BANK = $04
!PH1_MASK0 = $06
!PH1_MASK1 = $08
!PH1_SIZE = $0A
!PH1_END = $0C
!PH1_CARRY = $0E
!PH1_COUNT = $10
!PH1_CURSOR = $12
!PH1_REMAIN = $14
!PH1_MASK = $16
!PH1_OWNER = $18
!PH1_STATUS = $1A
!PH1_BRANCH = $1C
!PH1_POINTER = $1E
!PH1_COUNT0 = $20
!PH1_TARGET_BASE = $22
!PH1_TARGET_COUNT = $24
!PH1_EXPECTED_END = $26
!PH1_EXPECTED_CARRY = $28

macro PH1_RequireZero()
    BEQ ?ok
    BRL EpochPackageHelperV1RomSource_Refuse
?ok:
endmacro

macro PH1_RequireCarryClear()
    BCC ?ok
    BRL EpochPackageHelperV1RomSource_Refuse
?ok:
endmacro

EpochPackageHelperV1RomSource_Start:
    PHP
    PHA
    PHX
    PHY
    PHB

    ; Canonical dispatch does not inspect the branch flag or registry.
    LDA.w $9877
    CMP.w #$0100
    %PH1_RequireCarryClear()
    CMP.w #$0080
    BCS .high
    PLB
    PLY
    PLX
    PLA
    PLP
    LDA.w $9877
    ASL A
    JML !PE_PH1_CANONICAL_TAIL
.high:
    CMP.w #$0090
    %PH1_RequireCarryClear()
    LDA.w $A0B3
    AND.w #$FF00
    %PH1_RequireZero()

    ; Preserve incoming I/D/V; arithmetic below must be binary.
    SEP #$20
    LDA.b $08,s
    STA.l !PE_PH1_SCRATCH+!PH1_STATUS
    REP #$20
    CLD
    LDA.w $9877
    SEC
    SBC.w #$0080
    ASL A
    ASL A
    ASL A
    ASL A
    STA.l !PE_PH1_SCRATCH+!PH1_INDEX
    TAX
    ASL A
    ASL A
    STA.l !PE_PH1_SCRATCH+!PH1_TARGET_BASE
    LDA.l !PE_PH1_BINDINGS,X
    CMP.w #$0001
    %PH1_RequireZero()
    LDA.l !PE_PH1_BINDINGS+$0C,X
    %PH1_RequireZero()
    LDA.l !PE_PH1_BINDINGS+$0E,X
    %PH1_RequireZero()
    LDA.l !PE_PH1_BINDINGS+$0A,X
    CMP.w #$0021
    %PH1_RequireCarryClear()
    STA.l !PE_PH1_SCRATCH+!PH1_TARGET_COUNT
    LDA.l !PE_PH1_BINDINGS+$06,X
    STA.l !PE_PH1_SCRATCH+!PH1_EXPECTED_END
    LDA.l !PE_PH1_BINDINGS+$08,X
    CMP.w #$0002
    %PH1_RequireCarryClear()
    STA.l !PE_PH1_SCRATCH+!PH1_EXPECTED_CARRY
    CMP.w #$0000
    BEQ .expected_end_valid
    LDA.l !PE_PH1_SCRATCH+!PH1_EXPECTED_END
    %PH1_RequireZero()
.expected_end_valid:
    LDA.l !PE_PH1_BINDINGS+$04,X
    CMP.w #$0041
    BEQ .bank_ok
    CMP.w #$0042
    %PH1_RequireZero()
.bank_ok:
    STA.l !PE_PH1_SCRATCH+!PH1_BANK
    LDA.l !PE_PH1_BINDINGS+$02,X
    CMP.w #$FFFD
    %PH1_RequireCarryClear()
    STA.l !PE_PH1_SCRATCH+!PH1_ROOT
    TAX
    LDA.w $A0B3
    STA.l !PE_PH1_SCRATCH+!PH1_BRANCH

    ; Read source through DBR while every scratch/output access is long.
    SEP #$20
    LDA.l !PE_PH1_SCRATCH+!PH1_BANK
    PHA
    PLB
    REP #$20
    LDA.w $0000,X
    XBA
    STA.l !PE_PH1_SCRATCH+!PH1_MASK0
    INX
    INX
    LDA.w $0000,X
    XBA
    STA.l !PE_PH1_SCRATCH+!PH1_MASK1
    INX
    INX
    TXA
    STA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    LDA.l !PE_PH1_SCRATCH+!PH1_MASK0
    JSR EpochPackageHelperV1RomSource_CountBits
    STA.l !PE_PH1_SCRATCH+!PH1_COUNT0
    LDA.l !PE_PH1_SCRATCH+!PH1_MASK1
    JSR EpochPackageHelperV1RomSource_CountBits
    CLC
    ADC.l !PE_PH1_SCRATCH+!PH1_COUNT0
    STA.l !PE_PH1_SCRATCH+!PH1_COUNT
    STA.l !PE_PH1_SCRATCH+!PH1_REMAIN
    ASL A
    CLC
    ADC.w #$0004
    STA.l !PE_PH1_SCRATCH+!PH1_SIZE
    CLC
    ADC.l !PE_PH1_SCRATCH+!PH1_ROOT
    STA.l !PE_PH1_SCRATCH+!PH1_END
    LDA.w #$0000
    ADC.w #$0000
    STA.l !PE_PH1_SCRATCH+!PH1_CARRY
    BEQ .extent_ok
    LDA.l !PE_PH1_SCRATCH+!PH1_END
    %PH1_RequireZero()
.extent_ok:
    LDA.l !PE_PH1_SCRATCH+!PH1_END
    CMP.l !PE_PH1_SCRATCH+!PH1_EXPECTED_END
    %PH1_RequireZero()
    LDA.l !PE_PH1_SCRATCH+!PH1_CARRY
    CMP.l !PE_PH1_SCRATCH+!PH1_EXPECTED_CARRY
    %PH1_RequireZero()
    ; Validate all pointers in both masks before the first publication.
    LDA.l !PE_PH1_SCRATCH+!PH1_REMAIN
    BEQ .validated
.preflight:
    LDA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    TAX
    LDA.w $0000,X
    CMP.w #$FFFF
    BNE .not_ffff
    BRL EpochPackageHelperV1RomSource_Refuse
.not_ffff:
    STA.l !PE_PH1_SCRATCH+!PH1_POINTER
    CMP.l !PE_PH1_SCRATCH+!PH1_ROOT
    BCC .pointer_ok
    LDA.l !PE_PH1_SCRATCH+!PH1_CARRY
    BEQ .check_low_end
    BRL EpochPackageHelperV1RomSource_Refuse
.check_low_end:
    LDA.l !PE_PH1_SCRATCH+!PH1_POINTER
    CMP.l !PE_PH1_SCRATCH+!PH1_END
    BCS .pointer_ok
    BRL EpochPackageHelperV1RomSource_Refuse
.pointer_ok:
    ; Match every pointer in both branches against the exact target allowlist.
    ; The selected pointer list is not allowed to hide an invalid other branch.
    LDA.l !PE_PH1_SCRATCH+!PH1_TARGET_COUNT
    BEQ .target_missing
    TAY
    LDA.l !PE_PH1_SCRATCH+!PH1_TARGET_BASE
    TAX
.target_search:
    LDA.l !PE_PH1_TARGETS,X
    CMP.l !PE_PH1_SCRATCH+!PH1_POINTER
    BEQ .target_found
    INX
    INX
    DEY
    BNE .target_search
.target_missing:
    BRL EpochPackageHelperV1RomSource_Refuse
.target_found:
    LDA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    TAX
    INX
    INX
    TXA
    STA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    LDA.l !PE_PH1_SCRATCH+!PH1_REMAIN
    DEC A
    STA.l !PE_PH1_SCRATCH+!PH1_REMAIN
    BEQ .validated
    BRL .preflight
.validated:
    LDA.l !PE_PH1_SCRATCH+!PH1_ROOT
    STA.l $7E9878
    CLC
    ADC.w #$0004
    STA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    LDA.l !PE_PH1_SCRATCH+!PH1_MASK1
    STA.l $7E0082
    LDA.l !PE_PH1_SCRATCH+!PH1_BRANCH
    BEQ .primary
    LDA.l !PE_PH1_SCRATCH+!PH1_COUNT0
    ASL A
    CLC
    ADC.l !PE_PH1_SCRATCH+!PH1_CURSOR
    STA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    LDA.l !PE_PH1_SCRATCH+!PH1_MASK1
    BRA .mask_chosen
.primary:
    LDA.l !PE_PH1_SCRATCH+!PH1_MASK0
.mask_chosen:
    STA.l !PE_PH1_SCRATCH+!PH1_MASK
    STA.l $7E0080
    LDA.w #$0000
    STA.l !PE_PH1_SCRATCH+!PH1_OWNER
    ; Native clears only A0B3, preserving its already-zero adjacent byte.
    SEP #$20
    STA.l $7EA0B3
    REP #$20
.publish_loop:
    LDA.l !PE_PH1_SCRATCH+!PH1_MASK
    ASL A
    STA.l !PE_PH1_SCRATCH+!PH1_MASK
    STA.l $7E0080
    BCC .next_owner
    LDA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    TAX
    LDA.w $0000,X
    STA.l !PE_PH1_SCRATCH+!PH1_POINTER
    INX
    INX
    TXA
    STA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    LDA.l !PE_PH1_SCRATCH+!PH1_OWNER
    TAX
    LDA.w #$0001
    STA.l $7E5DAC,X
    TXA
    ASL A
    ASL A
    TAX
    LDA.l !PE_PH1_SCRATCH+!PH1_POINTER
    STA.l $7E5DBD,X
    LDA.l !PE_PH1_SCRATCH+!PH1_BANK
    STA.l $7E5DBF,X
.next_owner:
    LDA.l !PE_PH1_SCRATCH+!PH1_OWNER
    INC A
    STA.l !PE_PH1_SCRATCH+!PH1_OWNER
    CMP.w #$0010
    BEQ .done
    BRL .publish_loop
.done:
    ; Replace only the saved P byte; restore stack/DBR before setting outputs.
    SEP #$20
    LDA.l !PE_PH1_SCRATCH+!PH1_STATUS
    AND.b #$4C
    ORA.b #$23
    STA.b $08,s
    REP #$20
    PLB
    PLY
    PLX
    PLA
    LDA.l !PE_PH1_SCRATCH+!PH1_CURSOR
    TAX
    LDY.w #$0010
    LDA.w #$0000
    PLP
    JML !PE_PH1_SUCCESS_TAIL

EpochPackageHelperV1RomSource_Refuse:
    ; Every branch here has the original eight-byte saved context intact.
    REP #$20
    PLB
    PLY
    PLX
    PLA
    PLP
    JML !PE_PH1_REFUSAL_TAIL

EpochPackageHelperV1RomSource_CountBits:
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
EpochPackageHelperV1RomSource_End:
