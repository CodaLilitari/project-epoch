; Original Project Epoch ROM-source package helper, synthetic stack-local v2.
; Pure relocatable include: no cartridge mutation, game hook or allocation.
; This separately versioned source preserves completed v0 and v1 unchanged.
; Caller: native M0/X0, D=0000, DBR=7E; JML tails retain the incoming frame.
; IRQ/NMI sources disabled only by the isolated synthetic harness.
; PE_PH2_BINDINGS: sixteen 16-byte records (all words):
; valid=1, root, bank, exact descriptor end low, end carry, target count,
; reserved=0, reserved=0. End carry is 0/1; carry 1 requires low=0.
; PE_PH2_TARGETS: sixteen 64-byte arrays of at most 32 allowed direct offsets.
; Registry/target fixture identities and source bytes are immutable while called.
; Only banks 41/42 are admitted by this test version, never WRAM or mirrors.
; The exact target allowlist is transport authority, not stream certification.
; No pointed stream is read/executed here. Static command certification remains
; separate, and these synthetic byte fixtures are not installable packages.
; No global scratch is used. Locals are 42 bytes at $01-$2A,S after allocation.
; Saved DBR/Y/X/A/P lie at $2B/$2C/$2E/$30/$32,S, respectively.
; Caller guarantees eight initial push bytes and the caller frame are writable
; bank-zero WRAM; the diagnostic launcher enforces an exact entry-SP allowlist.
; High routes additionally refuse before allocating if current S < $002C.
; This leaves deepest S >= 0 after locals plus the local JSR (52 total bytes).
; A stack frame and its contents confer no real-game stack/interrupt ownership.

!PH2_INDEX = $00
!PH2_ROOT = $02
!PH2_BANK = $04
!PH2_MASK0 = $06
!PH2_MASK1 = $08
!PH2_SIZE = $0A
!PH2_END = $0C
!PH2_CARRY = $0E
!PH2_COUNT = $10
!PH2_CURSOR = $12
!PH2_REMAIN = $14
!PH2_MASK = $16
!PH2_OWNER = $18
!PH2_STATUS = $1A
!PH2_BRANCH = $1C
!PH2_POINTER = $1E
!PH2_COUNT0 = $20
!PH2_TARGET_BASE = $22
!PH2_TARGET_COUNT = $24
!PH2_EXPECTED_END = $26
!PH2_EXPECTED_CARRY = $28

macro PH2_RequireZero()
    BEQ ?ok
    BRL EpochPackageHelperV2Stack_RefuseFramed
?ok:
endmacro

macro PH2_RequireCarryClear()
    BCC ?ok
    BRL EpochPackageHelperV2Stack_RefuseFramed
?ok:
endmacro

macro PH2_RequireZeroUnframed()
    BEQ ?ok
    BRL EpochPackageHelperV2Stack_RefuseUnframed
?ok:
endmacro

macro PH2_RequireCarryClearUnframed()
    BCC ?ok
    BRL EpochPackageHelperV2Stack_RefuseUnframed
?ok:
endmacro

EpochPackageHelperV2Stack_Start:
    PHP
    PHA
    PHX
    PHY
    PHB

    ; Canonical dispatch does not inspect the branch flag or registry.
    LDA.w $9877
    CMP.w #$0100
    %PH2_RequireCarryClearUnframed()
    CMP.w #$0080
    BCS .high
    PLB
    PLY
    PLX
    PLA
    PLP
    LDA.w $9877
    ASL A
    JML !PE_PH2_CANONICAL_TAIL
.high:
    CMP.w #$0090
    %PH2_RequireCarryClearUnframed()
    LDA.w $A0B3
    AND.w #$FF00
    %PH2_RequireZeroUnframed()

    ; Save original status before changing flags; frame arithmetic is binary.
    CLD
    TSC
    CMP.w #$002C
    BCS .stack_room
    BRL EpochPackageHelperV2Stack_RefuseUnframed
.stack_room:
    SEC
    SBC.w #$002A
    TCS
    SEP #$20
    LDA.b $32,s
    STA.b !PH2_STATUS+1,s
    REP #$20
    LDA.w $9877
    SEC
    SBC.w #$0080
    ASL A
    ASL A
    ASL A
    ASL A
    STA.b !PH2_INDEX+1,s
    TAX
    ASL A
    ASL A
    STA.b !PH2_TARGET_BASE+1,s
    LDA.l !PE_PH2_BINDINGS,X
    CMP.w #$0001
    %PH2_RequireZero()
    LDA.l !PE_PH2_BINDINGS+$0C,X
    %PH2_RequireZero()
    LDA.l !PE_PH2_BINDINGS+$0E,X
    %PH2_RequireZero()
    LDA.l !PE_PH2_BINDINGS+$0A,X
    CMP.w #$0021
    %PH2_RequireCarryClear()
    STA.b !PH2_TARGET_COUNT+1,s
    LDA.l !PE_PH2_BINDINGS+$06,X
    STA.b !PH2_EXPECTED_END+1,s
    LDA.l !PE_PH2_BINDINGS+$08,X
    CMP.w #$0002
    %PH2_RequireCarryClear()
    STA.b !PH2_EXPECTED_CARRY+1,s
    CMP.w #$0000
    BEQ .expected_end_valid
    LDA.b !PH2_EXPECTED_END+1,s
    %PH2_RequireZero()
.expected_end_valid:
    LDA.l !PE_PH2_BINDINGS+$04,X
    CMP.w #$0041
    BEQ .bank_ok
    CMP.w #$0042
    %PH2_RequireZero()
.bank_ok:
    STA.b !PH2_BANK+1,s
    LDA.l !PE_PH2_BINDINGS+$02,X
    CMP.w #$FFFD
    %PH2_RequireCarryClear()
    STA.b !PH2_ROOT+1,s
    TAX
    LDA.w $A0B3
    STA.b !PH2_BRANCH+1,s

    ; Read source through DBR; locals remain S-relative, outputs explicitly long.
    SEP #$20
    LDA.b !PH2_BANK+1,s
    PHA
    PLB
    REP #$20
    LDA.w $0000,X
    XBA
    STA.b !PH2_MASK0+1,s
    INX
    INX
    LDA.w $0000,X
    XBA
    STA.b !PH2_MASK1+1,s
    INX
    INX
    TXA
    STA.b !PH2_CURSOR+1,s
    LDA.b !PH2_MASK0+1,s
    JSR EpochPackageHelperV2Stack_CountBits
    STA.b !PH2_COUNT0+1,s
    LDA.b !PH2_MASK1+1,s
    JSR EpochPackageHelperV2Stack_CountBits
    CLC
    ADC.b !PH2_COUNT0+1,s
    STA.b !PH2_COUNT+1,s
    STA.b !PH2_REMAIN+1,s
    ASL A
    CLC
    ADC.w #$0004
    STA.b !PH2_SIZE+1,s
    CLC
    ADC.b !PH2_ROOT+1,s
    STA.b !PH2_END+1,s
    LDA.w #$0000
    ADC.w #$0000
    STA.b !PH2_CARRY+1,s
    BEQ .extent_ok
    LDA.b !PH2_END+1,s
    %PH2_RequireZero()
.extent_ok:
    LDA.b !PH2_END+1,s
    CMP.b !PH2_EXPECTED_END+1,s
    %PH2_RequireZero()
    LDA.b !PH2_CARRY+1,s
    CMP.b !PH2_EXPECTED_CARRY+1,s
    %PH2_RequireZero()
    ; Validate all pointers in both masks before the first publication.
    LDA.b !PH2_REMAIN+1,s
    BEQ .validated
.preflight:
    LDA.b !PH2_CURSOR+1,s
    TAX
    LDA.w $0000,X
    CMP.w #$FFFF
    BNE .not_ffff
    BRL EpochPackageHelperV2Stack_RefuseFramed
.not_ffff:
    STA.b !PH2_POINTER+1,s
    CMP.b !PH2_ROOT+1,s
    BCC .pointer_ok
    LDA.b !PH2_CARRY+1,s
    BEQ .check_low_end
    BRL EpochPackageHelperV2Stack_RefuseFramed
.check_low_end:
    LDA.b !PH2_POINTER+1,s
    CMP.b !PH2_END+1,s
    BCS .pointer_ok
    BRL EpochPackageHelperV2Stack_RefuseFramed
.pointer_ok:
    ; Match every pointer in both branches against the exact target allowlist.
    ; The selected pointer list is not allowed to hide an invalid other branch.
    LDA.b !PH2_TARGET_COUNT+1,s
    BEQ .target_missing
    TAY
    LDA.b !PH2_TARGET_BASE+1,s
    TAX
.target_search:
    LDA.l !PE_PH2_TARGETS,X
    CMP.b !PH2_POINTER+1,s
    BEQ .target_found
    INX
    INX
    DEY
    BNE .target_search
.target_missing:
    BRL EpochPackageHelperV2Stack_RefuseFramed
.target_found:
    LDA.b !PH2_CURSOR+1,s
    TAX
    INX
    INX
    TXA
    STA.b !PH2_CURSOR+1,s
    LDA.b !PH2_REMAIN+1,s
    DEC A
    STA.b !PH2_REMAIN+1,s
    BEQ .validated
    BRL .preflight
.validated:
    LDA.b !PH2_ROOT+1,s
    STA.l $7E9878
    CLC
    ADC.w #$0004
    STA.b !PH2_CURSOR+1,s
    LDA.b !PH2_MASK1+1,s
    STA.l $7E0082
    LDA.b !PH2_BRANCH+1,s
    BEQ .primary
    LDA.b !PH2_COUNT0+1,s
    ASL A
    CLC
    ADC.b !PH2_CURSOR+1,s
    STA.b !PH2_CURSOR+1,s
    LDA.b !PH2_MASK1+1,s
    BRA .mask_chosen
.primary:
    LDA.b !PH2_MASK0+1,s
.mask_chosen:
    STA.b !PH2_MASK+1,s
    STA.l $7E0080
    LDA.w #$0000
    STA.b !PH2_OWNER+1,s
    ; Native clears only A0B3, preserving its already-zero adjacent byte.
    SEP #$20
    STA.l $7EA0B3
    REP #$20
.publish_loop:
    LDA.b !PH2_MASK+1,s
    ASL A
    STA.b !PH2_MASK+1,s
    STA.l $7E0080
    BCC .next_owner
    LDA.b !PH2_CURSOR+1,s
    TAX
    LDA.w $0000,X
    STA.b !PH2_POINTER+1,s
    INX
    INX
    TXA
    STA.b !PH2_CURSOR+1,s
    LDA.b !PH2_OWNER+1,s
    TAX
    LDA.w #$0001
    STA.l $7E5DAC,X
    TXA
    ASL A
    ASL A
    TAX
    LDA.b !PH2_POINTER+1,s
    STA.l $7E5DBD,X
    LDA.b !PH2_BANK+1,s
    STA.l $7E5DBF,X
.next_owner:
    LDA.b !PH2_OWNER+1,s
    INC A
    STA.b !PH2_OWNER+1,s
    CMP.w #$0010
    BEQ .done
    BRL .publish_loop
.done:
    ; Stage all returned values while every local is still allocated.
    SEP #$20
    LDA.b !PH2_STATUS+1,s
    AND.b #$4C
    ORA.b #$23
    STA.b $32,s
    REP #$20
    LDA.b !PH2_CURSOR+1,s
    STA.b $2E,s
    LDA.w #$0010
    STA.b $2C,s
    LDA.w #$0000
    STA.b $30,s
EpochPackageHelperV2Stack_ReleaseSuccess:
    ; No local is read or written after this release.
    TSC
    CLC
    ADC.w #$002A
    TCS
    PLB
    PLY
    PLX
    PLA
    PLP
    JML !PE_PH2_SUCCESS_TAIL

EpochPackageHelperV2Stack_RefuseFramed:
    ; All framed refusals preserve the original saved registers/status.
    REP #$20
    TSC
    CLC
    ADC.w #$002A
    TCS
EpochPackageHelperV2Stack_RefuseUnframed:
    ; Early refusals arrive with only the eight saved context bytes.
    REP #$20
    PLB
    PLY
    PLX
    PLA
    PLP
    JML !PE_PH2_REFUSAL_TAIL

EpochPackageHelperV2Stack_CountBits:
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
EpochPackageHelperV2Stack_End:
