; Project Epoch standalone optimized SHA-256 profile-1 benchmark.
;
; This is an original synthetic ExHiROM diagnostic. It contains no Chrono
; Trigger data and is not a production allocation or hook. The private builder
; applies it only to an 8 MiB all-$FF image, audits the five labelled spans,
; finalizes both header checksums, and supplies disposable zero-filled SRAM.

arch 65816
exhirom

!BENCH_FRAME       = $7E5EF0
!BENCH_RESULT      = $7E5F00
!BENCH_RESULT_SIZE = $0140
!BENCH_SCRATCH     = $7E4000
!BENCH_FRONT_GUARD = $7E3FF0
!BENCH_REAR_GUARD  = $7E40C2

!BENCH_SLOT1_REC = $0030
!BENCH_SLOT2_REC = $0080
!BENCH_SLOT3_REC = $00D0
!BENCH_SLOT_REC_SIZE = $0050

!BENCH_EXPECTED_P = $008D
!BENCH_EXPECTED_Y = $A55A
!BENCH_EXPECTED_D = $1234
!BENCH_EXPECTED_DBR = $0012
!BENCH_ABI_ALL = $007F

; One valid-call result record, relative to its slot-record base.
!REC_SLOT       = $00
!REC_BASE       = $02
!REC_STATUS     = $04
!REC_FRAME0     = $06
!REC_FRAME1     = $08
!REC_ELAPSED    = $0A
!REC_ABI_MASK   = $0C
!REC_P_EXPECTED = $0E
!REC_P_ACTUAL   = $10
!REC_A_ACTUAL   = $12
!REC_X_ACTUAL   = $14
!REC_Y_ACTUAL   = $16
!REC_D_ACTUAL   = $18
!REC_SP_EXPECTED = $1A
!REC_SP_ACTUAL  = $1C
!REC_DBR_EXPECTED = $1E
!REC_DBR_ACTUAL = $20
!REC_DIGEST     = $22
!REC_DIGEST_OK  = $42


macro BenchmarkHeader()
    db "EPOCH SHA256 FAST    "
    db $35                     ; fast ExHiROM
    db $02                     ; ROM + RAM + battery
    db $0D                     ; 8 MiB ROM
    db $03                     ; 8 KiB SRAM
    db $01                     ; region
    db $00                     ; maker
    db $00                     ; version
    dw $FFFF                   ; checksum complement placeholder
    dw $0000                   ; checksum placeholder
endmacro

macro BenchmarkVectors()
    ; Native vectors $FFE0-$FFEF.
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Nmi
    dw Benchmark_Irq
    dw Benchmark_Irq
    ; Emulation vectors $FFF0-$FFFF.
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Irq
    dw Benchmark_Nmi
    dw Benchmark_Reset
    dw Benchmark_Irq
endmacro


; Run one valid slot with a hostile-but-supported caller context. The decimal
; flag is set, DBR and D are nonzero, and an NMI frame counter remains live.
macro BenchmarkRunValid(slot, base, record, expected)
    LDA.w #<slot>
    STA.l !BENCH_RESULT+<record>+!REC_SLOT
    LDA.w #<base>
    STA.l !BENCH_RESULT+<record>+!REC_BASE
    LDA.w #!BENCH_EXPECTED_P
    STA.l !BENCH_RESULT+<record>+!REC_P_EXPECTED
    LDA.w #!BENCH_EXPECTED_DBR
    STA.l !BENCH_RESULT+<record>+!REC_DBR_EXPECTED

    LDA.l !BENCH_FRAME
    STA.l !BENCH_RESULT+<record>+!REC_FRAME0

    LDA.w #!BENCH_EXPECTED_D
    TCD
    SEP #$20
    LDA.b #!BENCH_EXPECTED_DBR
    PHA
    PLB
    REP #$30
    TSC
    STA.l !BENCH_RESULT+<record>+!REC_SP_EXPECTED

    LDA.w #<slot>
    LDX.w #<base>
    LDY.w #!BENCH_EXPECTED_Y
    CLV
    SED
    SEC
    JSL EpochSha256Fast_Profile1Digest

    ; Capture A and P before any transfer instruction can alter flags.
    STA.l !BENCH_RESULT+<record>+!REC_A_ACTUAL
    PHP
    SEP #$20
    PLA
    STA.l !BENCH_RESULT+<record>+!REC_P_ACTUAL
    REP #$30

    TXA
    STA.l !BENCH_RESULT+<record>+!REC_X_ACTUAL
    TYA
    STA.l !BENCH_RESULT+<record>+!REC_Y_ACTUAL
    TDC
    STA.l !BENCH_RESULT+<record>+!REC_D_ACTUAL
    TSC
    STA.l !BENCH_RESULT+<record>+!REC_SP_ACTUAL
    PHB
    SEP #$20
    PLA
    STA.l !BENCH_RESULT+<record>+!REC_DBR_ACTUAL
    REP #$30
    CLD

    LDA.l !BENCH_FRAME
    STA.l !BENCH_RESULT+<record>+!REC_FRAME1
    SEC
    SBC.l !BENCH_RESULT+<record>+!REC_FRAME0
    STA.l !BENCH_RESULT+<record>+!REC_ELAPSED

    LDA.l !BENCH_SCRATCH+$C0
    STA.l !BENCH_RESULT+<record>+!REC_STATUS

    LDX.w #$0000
?CopyDigest:
    LDA.l !BENCH_SCRATCH+$A0,X
    STA.l !BENCH_RESULT+<record>+!REC_DIGEST,X
    INX
    INX
    CPX.w #$0020
    BNE ?CopyDigest

    LDA.w #$0000
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    LDA.l !BENCH_RESULT+<record>+!REC_A_ACTUAL
    CMP.w #<slot>
    BNE ?AbiX
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0001
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
?AbiX:
    LDA.l !BENCH_RESULT+<record>+!REC_X_ACTUAL
    CMP.w #<base>
    BNE ?AbiY
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0002
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
?AbiY:
    LDA.l !BENCH_RESULT+<record>+!REC_Y_ACTUAL
    CMP.w #!BENCH_EXPECTED_Y
    BNE ?AbiP
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0004
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
?AbiP:
    LDA.l !BENCH_RESULT+<record>+!REC_P_ACTUAL
    CMP.w #!BENCH_EXPECTED_P
    BNE ?AbiD
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0008
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
?AbiD:
    LDA.l !BENCH_RESULT+<record>+!REC_D_ACTUAL
    CMP.w #!BENCH_EXPECTED_D
    BNE ?AbiDbr
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0010
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
?AbiDbr:
    LDA.l !BENCH_RESULT+<record>+!REC_DBR_ACTUAL
    CMP.w #!BENCH_EXPECTED_DBR
    BNE ?AbiSp
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0020
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
?AbiSp:
    LDA.l !BENCH_RESULT+<record>+!REC_SP_ACTUAL
    CMP.l !BENCH_RESULT+<record>+!REC_SP_EXPECTED
    BNE ?CompareDigest
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    ORA.w #$0040
    STA.l !BENCH_RESULT+<record>+!REC_ABI_MASK

?CompareDigest:
    LDA.w #$0001
    STA.l !BENCH_RESULT+<record>+!REC_DIGEST_OK
    LDX.w #$0000
?DigestLoop:
    LDA.l !BENCH_RESULT+<record>+!REC_DIGEST,X
    CMP.l <expected>,X
    BNE ?DigestBad
    INX
    INX
    CPX.w #$0020
    BNE ?DigestLoop
    BRA ?DigestDone
?DigestBad:
    LDA.w #$0000
    STA.l !BENCH_RESULT+<record>+!REC_DIGEST_OK
?DigestDone:
endmacro


macro BenchmarkEvaluateSlot(record)
    LDA.l !BENCH_RESULT+<record>+!REC_STATUS
    BNE ?BadStatus
    BRA ?CheckDigest
?BadStatus:
    JSR.w Benchmark_IncrementFailure
?CheckDigest:
    LDA.l !BENCH_RESULT+<record>+!REC_DIGEST_OK
    CMP.w #$0001
    BEQ ?CheckAbi
    JSR.w Benchmark_IncrementFailure
?CheckAbi:
    LDA.l !BENCH_RESULT+<record>+!REC_ABI_MASK
    CMP.w #!BENCH_ABI_ALL
    BEQ ?CheckTime
    JSR.w Benchmark_IncrementFailure
?CheckTime:
    LDA.l !BENCH_RESULT+<record>+!REC_ELAPSED
    BNE ?Done
    JSR.w Benchmark_IncrementFailure
?Done:
endmacro


; Reset and interrupt code must stay in CPU bank $00.
org $008000
Benchmark_BootStart:
Benchmark_Reset:
    SEI
    CLC
    XCE
    REP #$30
    LDA.w #$1FFF
    TCS
    LDA.w #$0000
    TCD
    SEP #$20
    STZ.w $4200
    LDA.b #$80
    STA.w $2100
    REP #$30
    JSL Benchmark_Main
.Idle:
    WAI
    BRA .Idle

Benchmark_Nmi:
    PHP
    REP #$20
    PHA
    LDA.l !BENCH_FRAME
    INC A
    STA.l !BENCH_FRAME
    PLA
    PLP
    RTI

Benchmark_Irq:
    RTI
Benchmark_BootEnd:

assert bank(Benchmark_BootStart) == $00
assert bank(Benchmark_BootEnd-1) == $00
assert Benchmark_BootEnd <= $00FFC0


; Main benchmark and the relocatable SHA implementation share bank $41.
org $410000
Benchmark_CoreStart:
Benchmark_Main:
    REP #$30
    CLD

    ; Clear the frame counter and the versioned result body. Magic is committed
    ; last, so an interrupted run is never accepted as complete.
    LDA.w #$0000
    STA.l !BENCH_FRAME
    LDX.w #$0000
.ClearResult:
    STA.l !BENCH_RESULT,X
    INX
    INX
    CPX.w #!BENCH_RESULT_SIZE
    BNE .ClearResult

    ; Seed guards and the complete scratch span with visible canaries.
    LDA.w #$A55A
    LDX.w #$0000
.FrontGuard:
    STA.l !BENCH_FRONT_GUARD,X
    INX
    INX
    CPX.w #$0010
    BNE .FrontGuard
    LDX.w #$0000
.RearGuard:
    STA.l !BENCH_REAR_GUARD,X
    INX
    INX
    CPX.w #$0010
    BNE .RearGuard
    LDA.w #$C33C
    LDX.w #$0000
.Scratch:
    STA.l !BENCH_SCRATCH,X
    INX
    INX
    CPX.w #$00C2
    BNE .Scratch

    LDA.w #$0001
    STA.l !BENCH_RESULT+$08
    LDA.w #!BENCH_RESULT_SIZE
    STA.l !BENCH_RESULT+$0A
    LDA.w #$0004
    STA.l !BENCH_RESULT+$2E

    ; Enable NMI and synchronize immediately after the first vblank edge.
    SEP #$20
    LDA.b #$80
    STA.w $4200
    REP #$30
    WAI

    %BenchmarkRunValid($0001, $6000, !BENCH_SLOT1_REC, Benchmark_Expected1)
    %BenchmarkRunValid($0002, $6A00, !BENCH_SLOT2_REC, Benchmark_Expected2)
    %BenchmarkRunValid($0003, $7400, !BENCH_SLOT3_REC, Benchmark_Expected3)

    ; Invalid pair: slot 1 with slot-2 base. Output must remain the sentinel.
    LDA.w #$D00D
    LDX.w #$0000
.InvalidSeed:
    STA.l !BENCH_SCRATCH+$A0,X
    INX
    INX
    CPX.w #$0020
    BNE .InvalidSeed

    LDA.w #!BENCH_EXPECTED_D
    TCD
    SEP #$20
    LDA.b #!BENCH_EXPECTED_DBR
    PHA
    PLB
    REP #$30
    TSC
    STA.l !BENCH_RESULT+$24
    LDA.w #$0001
    LDX.w #$6A00
    LDY.w #!BENCH_EXPECTED_Y
    CLV
    SED
    SEC
    JSL EpochSha256Fast_Profile1Digest
    STA.l !BENCH_RESULT+$1C
    PHP
    SEP #$20
    PLA
    STA.l !BENCH_RESULT+$1A
    REP #$30
    TXA
    STA.l !BENCH_RESULT+$1E
    TYA
    STA.l !BENCH_RESULT+$20
    TDC
    STA.l !BENCH_RESULT+$22
    TSC
    STA.l !BENCH_RESULT+$26
    PHB
    SEP #$20
    PLA
    STA.l !BENCH_RESULT+$28
    REP #$30
    CLD
    LDA.l !BENCH_SCRATCH+$C0
    STA.l !BENCH_RESULT+$14

    LDA.w #$0001
    STA.l !BENCH_RESULT+$16
    LDX.w #$0000
.InvalidOutput:
    LDA.l !BENCH_SCRATCH+$A0,X
    CMP.w #$D00D
    BNE .InvalidOutputBad
    INX
    INX
    CPX.w #$0020
    BNE .InvalidOutput
    BRA .InvalidOutputDone
.InvalidOutputBad:
    LDA.w #$0000
    STA.l !BENCH_RESULT+$16
.InvalidOutputDone:

    LDA.w #$0000
    STA.l !BENCH_RESULT+$18
    LDA.l !BENCH_RESULT+$1C
    CMP.w #$0001
    BNE .InvalidAbiX
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0001
    STA.l !BENCH_RESULT+$18
.InvalidAbiX:
    LDA.l !BENCH_RESULT+$1E
    CMP.w #$6A00
    BNE .InvalidAbiY
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0002
    STA.l !BENCH_RESULT+$18
.InvalidAbiY:
    LDA.l !BENCH_RESULT+$20
    CMP.w #!BENCH_EXPECTED_Y
    BNE .InvalidAbiP
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0004
    STA.l !BENCH_RESULT+$18
.InvalidAbiP:
    LDA.l !BENCH_RESULT+$1A
    CMP.w #!BENCH_EXPECTED_P
    BNE .InvalidAbiD
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0008
    STA.l !BENCH_RESULT+$18
.InvalidAbiD:
    LDA.l !BENCH_RESULT+$22
    CMP.w #!BENCH_EXPECTED_D
    BNE .InvalidAbiDbr
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0010
    STA.l !BENCH_RESULT+$18
.InvalidAbiDbr:
    LDA.l !BENCH_RESULT+$28
    CMP.w #!BENCH_EXPECTED_DBR
    BNE .InvalidAbiSp
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0020
    STA.l !BENCH_RESULT+$18
.InvalidAbiSp:
    LDA.l !BENCH_RESULT+$26
    CMP.l !BENCH_RESULT+$24
    BNE .InvalidAbiDone
    LDA.l !BENCH_RESULT+$18
    ORA.w #$0040
    STA.l !BENCH_RESULT+$18
.InvalidAbiDone:

    JSR.w Benchmark_CheckGuards
    JSR.w Benchmark_Evaluate
    LDA.l !BENCH_FRAME
    STA.l !BENCH_RESULT+$12
    LDA.w #$A55A
    STA.l !BENCH_RESULT+$10

    ; Commit ASCII "PESHA816" last.
    LDA.w #$4550
    STA.l !BENCH_RESULT+$00
    LDA.w #$4853
    STA.l !BENCH_RESULT+$02
    LDA.w #$3841
    STA.l !BENCH_RESULT+$04
    LDA.w #$3631
    STA.l !BENCH_RESULT+$06

.Complete:
    WAI
    BRA .Complete


Benchmark_CheckGuards:
    LDA.w #$0001
    STA.l !BENCH_RESULT+$2A
    LDX.w #$0000
.Front:
    LDA.l !BENCH_FRONT_GUARD,X
    CMP.w #$A55A
    BNE .FrontBad
    INX
    INX
    CPX.w #$0010
    BNE .Front
    BRA .RearStart
.FrontBad:
    LDA.w #$0000
    STA.l !BENCH_RESULT+$2A
.RearStart:
    LDA.w #$0001
    STA.l !BENCH_RESULT+$2C
    LDX.w #$0000
.Rear:
    LDA.l !BENCH_REAR_GUARD,X
    CMP.w #$A55A
    BNE .RearBad
    INX
    INX
    CPX.w #$0010
    BNE .Rear
    RTS
.RearBad:
    LDA.w #$0000
    STA.l !BENCH_RESULT+$2C
    RTS


Benchmark_Evaluate:
    LDA.w #$0000
    STA.l !BENCH_RESULT+$0E
    %BenchmarkEvaluateSlot(!BENCH_SLOT1_REC)
    %BenchmarkEvaluateSlot(!BENCH_SLOT2_REC)
    %BenchmarkEvaluateSlot(!BENCH_SLOT3_REC)

    LDA.l !BENCH_RESULT+$14
    CMP.w #$FFFF
    BEQ .InvalidOutput
    JSR.w Benchmark_IncrementFailure
.InvalidOutput:
    LDA.l !BENCH_RESULT+$16
    CMP.w #$0001
    BEQ .InvalidAbi
    JSR.w Benchmark_IncrementFailure
.InvalidAbi:
    LDA.l !BENCH_RESULT+$18
    CMP.w #!BENCH_ABI_ALL
    BEQ .Front
    JSR.w Benchmark_IncrementFailure
.Front:
    LDA.l !BENCH_RESULT+$2A
    CMP.w #$0001
    BEQ .Rear
    JSR.w Benchmark_IncrementFailure
.Rear:
    LDA.l !BENCH_RESULT+$2C
    CMP.w #$0001
    BEQ .Overall
    JSR.w Benchmark_IncrementFailure
.Overall:
    LDA.l !BENCH_RESULT+$0E
    BNE .Failed
    LDA.w #$A55A
    STA.l !BENCH_RESULT+$0C
    RTS
.Failed:
    LDA.w #$DEAD
    STA.l !BENCH_RESULT+$0C
    RTS


Benchmark_IncrementFailure:
    LDA.l !BENCH_RESULT+$0E
    INC A
    STA.l !BENCH_RESULT+$0E
    RTS


!PE_SHA256_SCRATCH = !BENCH_SCRATCH
incsrc "schala_sidecar_sha256_profile1_fast.asm"
Benchmark_CoreEnd:

assert bank(Benchmark_CoreStart) == $41
assert bank(Benchmark_CoreEnd-1) == $41
assert Benchmark_CoreEnd <= $420000


org $420000
Benchmark_DataStart:
Benchmark_Expected1:
    db $87,$88,$29,$BA,$52,$10,$CD,$4D
    db $1D,$EF,$AC,$BE,$DB,$6C,$48,$54
    db $07,$A2,$5D,$C8,$BE,$2C,$F4,$6A
    db $E2,$BD,$90,$63,$6B,$9E,$BD,$BD
Benchmark_Expected2:
    db $45,$35,$1B,$0F,$F7,$14,$35,$9E
    db $D2,$2D,$68,$76,$05,$B8,$43,$65
    db $8B,$F8,$CE,$3E,$2D,$99,$71,$99
    db $CE,$00,$77,$32,$3C,$DE,$00,$B5
Benchmark_Expected3:
    db $71,$6B,$7E,$B4,$1A,$A4,$1F,$3F
    db $EB,$FB,$78,$43,$CB,$18,$17,$4A
    db $01,$BA,$86,$9C,$F2,$A6,$34,$B0
    db $FE,$53,$F0,$D5,$8C,$DD,$59,$B2
Benchmark_DataEnd:

assert Benchmark_DataEnd-Benchmark_DataStart == $0060
assert bank(Benchmark_DataStart) == $42
assert bank(Benchmark_DataEnd-1) == $42


org $C0FFC0
Benchmark_HiromHeaderStart:
%BenchmarkHeader()
%BenchmarkVectors()
Benchmark_HiromHeaderEnd:

org $00FFC0
Benchmark_ExHiromHeaderStart:
%BenchmarkHeader()
%BenchmarkVectors()
Benchmark_ExHiromHeaderEnd:

assert Benchmark_HiromHeaderEnd-Benchmark_HiromHeaderStart == $0040
assert Benchmark_ExHiromHeaderEnd-Benchmark_ExHiromHeaderStart == $0040
assert !BENCH_SLOT1_REC+!BENCH_SLOT_REC_SIZE == !BENCH_SLOT2_REC
assert !BENCH_SLOT2_REC+!BENCH_SLOT_REC_SIZE == !BENCH_SLOT3_REC
assert !BENCH_SLOT3_REC+!BENCH_SLOT_REC_SIZE <= !BENCH_RESULT_SIZE
