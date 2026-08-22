; Project Epoch SHA-256 binding profile $01, source-only 65C816 prototype.
;
; This file is an includable Asar source unit.  It deliberately contains no
; mapping directive, org, hook, ROM allocation, or WRAM allocation.  The
; includer must provide a proved scratch address:
;
;   !PE_SHA256_SCRATCH = $7Exxxx
;
; The scratch span must be writable and wholly contained in one bank.  No
; Project Epoch address is approved by this source.  In particular, this file
; does not claim $7E2CA0 or any canonical-ROM zero run.
;
; Entry ABI: EpochSha256_Profile1Digest (JSL / RTL)
; ------------------------------------------------
; Preconditions:
;   - native mode;
;   - 16-bit accumulator and 16-bit index registers (M=0, X=0);
;   - A = physical save slot number $0001, $0002, or $0003;
;   - X = matching SRAM slot low word $6000, $6A00, or $7400;
;   - bank $30 contains the finalized vanilla save slot.
;
; Results:
;   - caller A/X/Y/P/DBR/D are restored exactly;
;   - !PE_SHA256_SCRATCH+$00A0..+$00BF contains the 32 digest bytes
;     in standard SHA-256 big-endian order on success;
;   - !PE_SHA256_SCRATCH+$00C0 is $0000 on success or $FFFF when
;     slot number and slot base do not form one of the exact pairs above;
;   - invalid arguments do not modify the output span.
;
; Side effects and bounds:
;   - reads exactly $0A00 bytes from the selected bank-$30 slot;
;   - writes only the caller-provided $00C2-byte scratch span;
;   - maximum additional stack use after entry is 16 bytes: the 10-byte
;     save frame plus three nested 2-byte JSR return addresses;
;   - including the caller's 3-byte JSL return, total stack growth is 19 bytes;
;   - not reentrant and not approved across NMI/IRQ; an eventual caller must
;     prove interrupt preservation/resumption as well as exclusive scratch;
;   - no sidecar, SRAM, ROM, hook, or checksum bytes are written.
;
; Profile $01 hashes:
;   exact $0A00 slot ||
;   "PE07BIND", $02, $01, physical_slot, $00, $00, $0A, $00, $00
;
; The $0A10-byte message pads to exactly 41 SHA-256 compression blocks.
; This is a correctness-first prototype, not a timing-approved routine.

!PE_SHA256_SCRATCH_LO   = (!PE_SHA256_SCRATCH&$00FFFF)
!PE_SHA256_SCRATCH_BANK = ((!PE_SHA256_SCRATCH>>16)&$FF)
!PE_SHA256_SCRATCH_SIZE = $00C2

assert !PE_SHA256_SCRATCH_BANK == $7E || !PE_SHA256_SCRATCH_BANK == $7F, "SHA scratch must be WRAM"
assert !PE_SHA256_SCRATCH_LO+!PE_SHA256_SCRATCH_SIZE <= $10000, "SHA scratch crosses a bank"

; Eight 32-bit chaining words, stored as numeric high/low 16-bit halves.
!PE_SHA_STATE       = $0000
; Eight 32-bit working words a..h.
!PE_SHA_WORK        = $0020
; Circular 16-word message schedule.
!PE_SHA_W           = $0040
; Shared helper input, rotate/shift result, sigma result, T1, T2, temporary.
!PE_SHA_INPUT       = $0080
!PE_SHA_ROT         = $0084
!PE_SHA_SIGMA       = $0088
!PE_SHA_T1          = $008C
!PE_SHA_T2          = $0090
!PE_SHA_TEMP        = $0094
; Saved input cursor, physical slot, block index, round index.
!PE_SHA_CURSOR      = $0098
!PE_SHA_SLOT        = $009A
!PE_SHA_BLOCK       = $009C
!PE_SHA_ROUND       = $009E
; Public result bytes and status word.
!PE_SHA_OUTPUT      = $00A0
!PE_SHA_STATUS      = $00C0

; 32-bit word offsets within the work array.
!PE_SHA_A = $00
!PE_SHA_B = $04
!PE_SHA_C = $08
!PE_SHA_D = $0C
!PE_SHA_E = $10
!PE_SHA_F = $14
!PE_SHA_G = $18
!PE_SHA_H = $1C


EpochSha256_Profile1Digest:
    PHP
    REP #$30
    CLD
    PHA
    PHX
    PHY
    PHD
    PHB

    ; Capture the ABI inputs before changing DBR.
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

    ; Fail closed unless physical slot and native slot base match exactly.
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
    JSR.w EpochSha256_InitializeState
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_BLOCK

.SlotBlockLoop:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_BLOCK
    CMP.w #$0028
    BEQ .FinalBlock
    JSR.w EpochSha256_LoadSlotBlock
    JSR.w EpochSha256_CompressBlock
    INC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_BLOCK
    BRL .SlotBlockLoop

.FinalBlock:
    JSR.w EpochSha256_LoadProfile1FinalBlock
    JSR.w EpochSha256_CompressBlock
    JSR.w EpochSha256_EmitDigest
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATUS

.Return:
    PLB
    PLD
    PLY
    PLX
    PLA
    PLP
    RTL


; Initialize the eight chaining words.
EpochSha256_InitializeState:
    LDX.w #$0000
.Loop:
    LDA.l EpochSha256_InitialState,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_STATE,X
    INX
    INX
    CPX.w #$0020
    BNE .Loop
    RTS


; Load one 64-byte slot block and convert each big-endian message half into
; the numeric 16-bit representation used by the compression core.
EpochSha256_LoadSlotBlock:
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


; Construct the only padded block for the fixed $0A10-byte profile message.
EpochSha256_LoadProfile1FinalBlock:
    LDX.w #$0000
.ZeroLoop:
    STZ.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W,X
    INX
    INX
    CPX.w #$0040
    BNE .ZeroLoop

    ; "PE07BIND"
    LDA.w #$5045
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$00
    LDA.w #$3037
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$02
    LDA.w #$4249
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$04
    LDA.w #$4E44
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$06
    ; Version $02, profile $01, physical slot, zero.
    LDA.w #$0201
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$08
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SLOT
    XBA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$0A
    ; Little-endian serialized length $0A00, then two reserved zero bytes.
    LDA.w #$000A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$0C
    ; SHA padding begins immediately after the 16-byte trailer.
    LDA.w #$8000
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$10
    ; 20608 bits = $0000000000005080, big-endian.
    LDA.w #$5080
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$3E
    RTS


; Compress the current 16-word input block with a 16-word circular schedule.
EpochSha256_CompressBlock:
    ; a..h = current chaining state.
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
    ; For t >= 16:
    ; W[t] = W[t-16] + sigma0(W[t-15]) + W[t-7] + sigma1(W[t-2]).
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
    JSR.w EpochSha256_SmallSigma0

    ; Start with W[(t+0) mod 16] + sigma0.
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

    ; Add W[(t+9) mod 16], which is W[t-7].
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

    ; sigma1(W[(t+14) mod 16]), which is W[t-2].
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
    JSR.w EpochSha256_SmallSigma1

    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_TEMP

    ; Replace the circular W[t mod 16] entry.
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
    ; T1 starts with h + Sigma1(e).
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_E+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    JSR.w EpochSha256_BigSigma1

    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_H+2
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_WORK+!PE_SHA_H
    ADC.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1

    ; Ch(e,f,g) = g xor (e and (f xor g)).
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

    ; Add K[t].
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROUND
    ASL A
    ASL A
    TAX
    CLC
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    ADC.l EpochSha256_K+2,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1+2
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1
    ADC.l EpochSha256_K,X
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_T1

    ; Add W[t].
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
    JSR.w EpochSha256_BigSigma0

    ; Maj(a,b,c) = (a and b) or (c and (a or b)).
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
    ; H[i] = H[i] + working[i], modulo 2^32.
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
EpochSha256_BigSigma0:
    LDX.w #$0002
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$000D
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$0016
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; Sigma1(x) = ROTR6(x) xor ROTR11(x) xor ROTR25(x).
EpochSha256_BigSigma1:
    LDX.w #$0006
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$000B
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$0019
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; sigma0(x) = ROTR7(x) xor ROTR18(x) xor SHR3(x).
EpochSha256_SmallSigma0:
    LDX.w #$0007
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$0012
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$0003
    JSR.w EpochSha256_ShiftInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; sigma1(x) = ROTR17(x) xor ROTR19(x) xor SHR10(x).
EpochSha256_SmallSigma1:
    LDX.w #$0011
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$0013
    JSR.w EpochSha256_RotateInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2

    LDX.w #$000A
    JSR.w EpochSha256_ShiftInputRight
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    EOR.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SIGMA+2
    RTS


; Rotate the shared 32-bit input right by X bits.  The word is represented as
; high numeric half at +0 and low numeric half at +2.
EpochSha256_RotateInputRight:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
.Loop:
    ; First LSR exposes old low bit 0.  ROR high injects it at bit 31 and
    ; exposes old high bit 0; ROR low injects that bit at bit 15.
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    LSR A
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    ROR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    ROR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    DEX
    BNE .Loop
    RTS


; Shift the shared 32-bit input right by X bits.
EpochSha256_ShiftInputRight:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_INPUT+2
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
.Loop:
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LSR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT
    LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    ROR A
    STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_ROT+2
    DEX
    BNE .Loop
    RTS


; Convert numeric 16-bit halves to the standard byte order.
EpochSha256_EmitDigest:
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


; Standard SHA-256 initial state, high numeric half then low numeric half.
EpochSha256_InitialState:
    dw $6A09,$E667
    dw $BB67,$AE85
    dw $3C6E,$F372
    dw $A54F,$F53A
    dw $510E,$527F
    dw $9B05,$688C
    dw $1F83,$D9AB
    dw $5BE0,$CD19
EpochSha256_InitialState_End:


; Standard SHA-256 round constants, high numeric half then low numeric half.
EpochSha256_K:
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
EpochSha256_K_End:


EpochSha256_SourceEnd:

assert bank(EpochSha256_Profile1Digest) == bank(EpochSha256_SourceEnd-1), "SHA source crosses a bank"
