; Project Epoch SHA-256 binding profile $01, optimized source-only candidate.
;
; This is separate from the proven correctness-first baseline.  It preserves
; the baseline ABI, profile, scratch layout, output, and bounds, but replaces
; variable one-bit rotate loops with fixed byte/word transforms plus at most
; three unrolled one-bit steps per primitive.
;
; This file is an includable Asar source unit.  It contains no mapping
; directive, org, hook, ROM allocation, or selected WRAM allocation.
; The includer supplies a separately proved scratch address:
;
;   !PE_SHA256_SCRATCH = $7Exxxx or $7Fxxxx
;
; Entry ABI: EpochSha256Fast_Profile1Digest (JSL / RTL)
; ----------------------------------------------------
; Preconditions:
;   - native mode;
;   - 16-bit accumulator and 16-bit index registers (M=0, X=0);
;   - A = physical save slot number $0001, $0002, or $0003;
;   - X = matching SRAM slot low word $6000, $6A00, or $7400;
;   - bank $30 contains the finalized vanilla save slot.
;
; Results:
;   - caller A/X/Y/P/DBR/D are restored exactly;
;   - scratch +$00A0..+$00BF contains standard big-endian digest bytes;
;   - scratch +$00C0 is $0000 on success or $FFFF for an invalid pair;
;   - invalid arguments do not modify the output span.
;
; Bounds:
;   - reads exactly $0A00 selected bank-$30 bytes;
;   - writes only the caller-provided $00C2-byte scratch span;
;   - maximum stack growth after entry is 14 bytes: the 10-byte save frame
;     plus two nested 2-byte JSR return addresses;
;   - including the caller's 3-byte JSL return, total growth is 17 bytes;
;   - no sidecar, SRAM, ROM, hook, or checksum bytes are written;
;   - not reentrant and not approved across NMI/IRQ.
;
; Profile $01 message:
;   exact $0A00 slot ||
;   "PE07BIND", $02, $01, physical_slot, $00, $00, $0A, $00, $00
;
; The fixed $0A10-byte message pads to 41 compression blocks.

!PE_SHA256_SCRATCH_LO   = (!PE_SHA256_SCRATCH&$00FFFF)
!PE_SHA256_SCRATCH_BANK = ((!PE_SHA256_SCRATCH>>16)&$FF)
!PE_SHA256_SCRATCH_SIZE = $00C2

assert !PE_SHA256_SCRATCH_BANK == $7E || !PE_SHA256_SCRATCH_BANK == $7F, "fast SHA scratch must be WRAM"
assert !PE_SHA256_SCRATCH_LO+!PE_SHA256_SCRATCH_SIZE <= $10000, "fast SHA scratch crosses a bank"

!PE_SHA_STATE       = $0000
!PE_SHA_WORK        = $0020
!PE_SHA_W           = $0040
!PE_SHA_INPUT       = $0080
!PE_SHA_ROT         = $0084
!PE_SHA_SIGMA       = $0088
!PE_SHA_T1          = $008C
!PE_SHA_T2          = $0090
!PE_SHA_TEMP        = $0094
!PE_SHA_CURSOR      = $0098
!PE_SHA_SLOT        = $009A
!PE_SHA_BLOCK       = $009C
!PE_SHA_ROUND       = $009E
!PE_SHA_OUTPUT      = $00A0
!PE_SHA_STATUS      = $00C0

!PE_SHA_A = $00
!PE_SHA_B = $04
!PE_SHA_C = $08
!PE_SHA_D = $0C
!PE_SHA_E = $10
!PE_SHA_F = $14
!PE_SHA_G = $18
!PE_SHA_H = $1C


; Fixed transforms used by the four optimized sigma functions.  Every macro
; operates on numeric high/low halves at INPUT/ROT and returns in 16-bit M
; mode.  The byte transforms intentionally address the little-endian scratch
; representation directly.

macro EpochSha256Fast_CopyInput()
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
endmacro

macro EpochSha256Fast_Swap16()
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
endmacro

; ROTR8: conceptual bytes A B C D -> D A B C.
macro EpochSha256Fast_Rotr8()
    SEP #$20
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+1
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+1
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+3
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+3
    REP #$20
endmacro

; ROTR24 (ROTL8): conceptual bytes A B C D -> B C D A.
macro EpochSha256Fast_Rotr24()
    SEP #$20
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+3
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+1
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+1
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+3
    REP #$20
endmacro

; SHR8: conceptual bytes A B C D -> 00 A B C.
macro EpochSha256Fast_Shr8()
    SEP #$20
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+1
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+1
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+3
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+3
    REP #$20
endmacro

macro EpochSha256Fast_Ror1()
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    LSR A
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    ROR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    ROR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
endmacro

macro EpochSha256Fast_Rol1()
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    ASL A
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    ROL A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    ROL A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
endmacro

macro EpochSha256Fast_Shr1()
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LSR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    ROR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
endmacro


EpochSha256Fast_Profile1Digest:
    PHP
    REP #$30
    CLD
    PHA
    PHX
    PHY
    PHD
    PHB

    STA.l !PE_SHA256_SCRATCH+!PE_SHA_SLOT
    TXA
    STA.l !PE_SHA256_SCRATCH+!PE_SHA_CURSOR

    SEP #$20
    LDA.b #!PE_SHA256_SCRATCH_BANK
    PHA
    PLB
    REP #$30

    LDA.w #$FFFF
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATUS

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SLOT
    CMP.w #$0001
    BEQ .ValidateSlot1
    CMP.w #$0002
    BEQ .ValidateSlot2
    CMP.w #$0003
    BEQ .ValidateSlot3
    BRL .Return

.ValidateSlot1:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_CURSOR
    CMP.w #$6000
    BEQ .ArgumentsValid
    BRL .Return

.ValidateSlot2:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_CURSOR
    CMP.w #$6A00
    BEQ .ArgumentsValid
    BRL .Return

.ValidateSlot3:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_CURSOR
    CMP.w #$7400
    BEQ .ArgumentsValid
    BRL .Return

.ArgumentsValid:
    JSR.w EpochSha256Fast_InitializeState
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_BLOCK

.SlotBlockLoop:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_BLOCK
    CMP.w #$0028
    BEQ .FinalBlock
    JSR.w EpochSha256Fast_LoadSlotBlock
    JSR.w EpochSha256Fast_CompressBlock
    INC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_BLOCK
    BRL .SlotBlockLoop

.FinalBlock:
    JSR.w EpochSha256Fast_LoadProfile1FinalBlock
    JSR.w EpochSha256Fast_CompressBlock
    JSR.w EpochSha256Fast_EmitDigest
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATUS

.Return:
    PLB
    PLD
    PLY
    PLX
    PLA
    PLP
    RTL


EpochSha256Fast_InitializeState:
    LDX.w #$0000
.Loop:
    LDA.l EpochSha256Fast_InitialState,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE,X
    INX
    INX
    CPX.w #$0020
    BNE .Loop
    RTS


EpochSha256Fast_LoadSlotBlock:
    LDX.w !PE_SHA256_SCRATCH_LO+!PE_SHA_CURSOR
    LDY.w #$0000
.WordLoop:
    LDA.l $300000,X
    XBA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    INX
    INX
    LDA.l $300000,X
    XBA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y
    INX
    INX
    TYA
    CLC
    ADC.w #$0004
    TAY
    CPY.w #$0040
    BNE .WordLoop
    STX.w !PE_SHA256_SCRATCH_LO+!PE_SHA_CURSOR
    RTS


EpochSha256Fast_LoadProfile1FinalBlock:
    LDX.w #$0000
.ZeroLoop:
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,X
    INX
    INX
    CPX.w #$0040
    BNE .ZeroLoop

    LDA.w #$5045
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$00
    LDA.w #$3037
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$02
    LDA.w #$4249
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$04
    LDA.w #$4E44
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$06
    LDA.w #$0201
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$08
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SLOT
    XBA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$0A
    LDA.w #$000A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$0C
    LDA.w #$8000
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$10
    LDA.w #$5080
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$3E
    RTS


EpochSha256Fast_CompressBlock:
    LDX.w #$0000
.CopyState:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK,X
    INX
    INX
    CPX.w #$0020
    BNE .CopyState

    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND

.RoundLoop:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    CMP.w #$0010
    BCS .ExpandSchedule
    BRL .ScheduleReady

.ExpandSchedule:
    ; sigma0(W[(t+1) mod 16])
    CLC
    ADC.w #$0001
    AND.w #$000F
    ASL A
    ASL A
    TAY
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    JSR.w EpochSha256Fast_SmallSigma0

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    AND.w #$000F
    ASL A
    ASL A
    TAY
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP

    ; W[(t+9) mod 16] = W[t-7].
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    CLC
    ADC.w #$0009
    AND.w #$000F
    ASL A
    ASL A
    TAY
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP

    ; sigma1(W[(t+14) mod 16]) = sigma1(W[t-2]).
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    CLC
    ADC.w #$000E
    AND.w #$000F
    ASL A
    ASL A
    TAY
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    JSR.w EpochSha256Fast_SmallSigma1

    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    AND.w #$000F
    ASL A
    ASL A
    TAY
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y

.ScheduleReady:
    ; T1 = h + Sigma1(e) + Ch(e,f,g) + K[t] + W[t].
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    JSR.w EpochSha256Fast_BigSigma1

    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_H+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_H
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_F
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G
    AND.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_F+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G+2
    AND.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2

    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    ASL A
    ASL A
    TAX
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    ADC.l EpochSha256Fast_K+2,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1
    ADC.l EpochSha256Fast_K,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    AND.w #$000F
    ASL A
    ASL A
    TAY
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+2,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,Y
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1

    ; T2 = Sigma0(a) + Maj(a,b,c).
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    JSR.w EpochSha256Fast_BigSigma0

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A
    AND.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A
    ORA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B
    AND.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_C
    ORA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP

    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A+2
    AND.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A+2
    ORA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B+2
    AND.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_C+2
    ORA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2

    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T2+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T2

    ; h=g, g=f, f=e.
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_H
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_H+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_F
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_F+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_G+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_F
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_F+2

    ; e = d + T1.
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_D+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_D
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E

    ; d=c, c=b, b=a.
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_C
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_D
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_C+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_D+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_C
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_C+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_B+2

    ; a = T1 + T2.
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T2+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_A

    INC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    CMP.w #$0040
    BEQ .RoundsComplete
    BRL .RoundLoop

.RoundsComplete:
    LDX.w #$0000
.StateAddLoop:
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE+2,X
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+2,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE+2,X
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE,X
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE,X
    TXA
    CLC
    ADC.w #$0004
    TAX
    CPX.w #$0020
    BNE .StateAddLoop
    RTS


; Sigma0(x) = ROTR2(x) xor ROTR13(x) xor ROTR22(x).
EpochSha256Fast_BigSigma0:
EpochSha256Fast_Rotr2_Start:
    %EpochSha256Fast_CopyInput()
    %EpochSha256Fast_Ror1()
    %EpochSha256Fast_Ror1()
EpochSha256Fast_Rotr2_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Rotr13_Start:
    %EpochSha256Fast_Swap16()
    %EpochSha256Fast_Rol1()
    %EpochSha256Fast_Rol1()
    %EpochSha256Fast_Rol1()
EpochSha256Fast_Rotr13_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Rotr22_Start:
    %EpochSha256Fast_Rotr24()
    %EpochSha256Fast_Rol1()
    %EpochSha256Fast_Rol1()
EpochSha256Fast_Rotr22_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; Sigma1(x) = ROTR6(x) xor ROTR11(x) xor ROTR25(x).
EpochSha256Fast_BigSigma1:
EpochSha256Fast_Rotr6_Start:
    %EpochSha256Fast_Rotr8()
    %EpochSha256Fast_Rol1()
    %EpochSha256Fast_Rol1()
EpochSha256Fast_Rotr6_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Rotr11_Start:
    %EpochSha256Fast_Rotr8()
    %EpochSha256Fast_Ror1()
    %EpochSha256Fast_Ror1()
    %EpochSha256Fast_Ror1()
EpochSha256Fast_Rotr11_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Rotr25_Start:
    %EpochSha256Fast_Rotr24()
    %EpochSha256Fast_Ror1()
EpochSha256Fast_Rotr25_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; sigma0(x) = ROTR7(x) xor ROTR18(x) xor SHR3(x).
EpochSha256Fast_SmallSigma0:
EpochSha256Fast_Rotr7_Start:
    %EpochSha256Fast_Rotr8()
    %EpochSha256Fast_Rol1()
EpochSha256Fast_Rotr7_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Rotr18_Start:
    %EpochSha256Fast_Swap16()
    %EpochSha256Fast_Ror1()
    %EpochSha256Fast_Ror1()
EpochSha256Fast_Rotr18_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Shr3_Start:
    %EpochSha256Fast_CopyInput()
    %EpochSha256Fast_Shr1()
    %EpochSha256Fast_Shr1()
    %EpochSha256Fast_Shr1()
EpochSha256Fast_Shr3_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; sigma1(x) = ROTR17(x) xor ROTR19(x) xor SHR10(x).
EpochSha256Fast_SmallSigma1:
EpochSha256Fast_Rotr17_Start:
    %EpochSha256Fast_Swap16()
    %EpochSha256Fast_Ror1()
EpochSha256Fast_Rotr17_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Rotr19_Start:
    %EpochSha256Fast_Swap16()
    %EpochSha256Fast_Ror1()
    %EpochSha256Fast_Ror1()
    %EpochSha256Fast_Ror1()
EpochSha256Fast_Rotr19_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

EpochSha256Fast_Shr10_Start:
    %EpochSha256Fast_Shr8()
    %EpochSha256Fast_Shr1()
    %EpochSha256Fast_Shr1()
EpochSha256Fast_Shr10_End:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


EpochSha256Fast_EmitDigest:
    LDX.w #$0000
.Loop:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE,X
    XBA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_OUTPUT,X
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE+2,X
    XBA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_OUTPUT+2,X
    TXA
    CLC
    ADC.w #$0004
    TAX
    CPX.w #$0020
    BNE .Loop
    RTS


EpochSha256Fast_InitialState:
    dw $6A09,$E667
    dw $BB67,$AE85
    dw $3C6E,$F372
    dw $A54F,$F53A
    dw $510E,$527F
    dw $9B05,$688C
    dw $1F83,$D9AB
    dw $5BE0,$CD19
EpochSha256Fast_InitialState_End:

assert EpochSha256Fast_InitialState_End-EpochSha256Fast_InitialState == $0020, "fast SHA initial table size"
assert bank(EpochSha256Fast_InitialState) == bank(EpochSha256Fast_InitialState_End-1), "fast SHA initial table crosses bank"


EpochSha256Fast_K:
    dw $428A,$2F98
    dw $7137,$4491
    dw $B5C0,$FBCF
    dw $E9B5,$DBA5
    dw $3956,$C25B
    dw $59F1,$11F1
    dw $923F,$82A4
    dw $AB1C,$5ED5
    dw $D807,$AA98
    dw $1283,$5B01
    dw $2431,$85BE
    dw $550C,$7DC3
    dw $72BE,$5D74
    dw $80DE,$B1FE
    dw $9BDC,$06A7
    dw $C19B,$F174
    dw $E49B,$69C1
    dw $EFBE,$4786
    dw $0FC1,$9DC6
    dw $240C,$A1CC
    dw $2DE9,$2C6F
    dw $4A74,$84AA
    dw $5CB0,$A9DC
    dw $76F9,$88DA
    dw $983E,$5152
    dw $A831,$C66D
    dw $B003,$27C8
    dw $BF59,$7FC7
    dw $C6E0,$0BF3
    dw $D5A7,$9147
    dw $06CA,$6351
    dw $1429,$2967
    dw $27B7,$0A85
    dw $2E1B,$2138
    dw $4D2C,$6DFC
    dw $5338,$0D13
    dw $650A,$7354
    dw $766A,$0ABB
    dw $81C2,$C92E
    dw $9272,$2C85
    dw $A2BF,$E8A1
    dw $A81A,$664B
    dw $C24B,$8B70
    dw $C76C,$51A3
    dw $D192,$E819
    dw $D699,$0624
    dw $F40E,$3585
    dw $106A,$A070
    dw $19A4,$C116
    dw $1E37,$6C08
    dw $2748,$774C
    dw $34B0,$BCB5
    dw $391C,$0CB3
    dw $4ED8,$AA4A
    dw $5B9C,$CA4F
    dw $682E,$6FF3
    dw $748F,$82EE
    dw $78A5,$636F
    dw $84C8,$7814
    dw $8CC7,$0208
    dw $90BE,$FFFA
    dw $A450,$6CEB
    dw $BEF9,$A3F7
    dw $C671,$78F2
EpochSha256Fast_K_End:

assert EpochSha256Fast_K_End-EpochSha256Fast_K == $0100, "fast SHA K table size"
assert bank(EpochSha256Fast_K) == bank(EpochSha256Fast_K_End-1), "fast SHA K table crosses bank"


EpochSha256Fast_SourceEnd:

assert bank(EpochSha256Fast_Profile1Digest) == bank(EpochSha256Fast_SourceEnd-1), "fast SHA source crosses a bank"
