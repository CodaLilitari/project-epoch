; Original private Project Epoch test boot and observation tails.
; Raw binary component only. The Python builder owns the guarded image assembly.
norom
org $000000
base $008000

OriginalPackageTest_Reset:
    SEI
    CLC
    XCE
    REP #$30
    LDX.w #$1FFF
    TXS
    LDA.w #$0000
    TCD
    SEP #$20
    LDA.b #$00
    STA.l $004200
    LDA.b #$80
    STA.l $002100
    LDA.b #$7E
    PHA
    PLB
    REP #$30
    JMP OriginalPackageTest_Park

padbyte $EA
pad $000040
OriginalPackageTest_Park:
    BRA OriginalPackageTest_Park

pad $000060
OriginalPackageTest_ObservedEntryBridge:
    JML $410000

pad $000080
OriginalPackageTest_Nmi:
    PHP
    REP #$20
    PHA
    LDA.l $7E5EF0
    INC A
    STA.l $7E5EF0
    PLA
    PLP
    RTI

pad $000090
OriginalPackageTest_Irq:
    RTI

pad $0000A0
OriginalPackageTest_Trap:
    SEI
    BRA OriginalPackageTest_Trap

pad $000100
OriginalPackageTest_CanonicalTail:
    BRA OriginalPackageTest_CanonicalTail
pad $000110
OriginalPackageTest_SuccessTail:
    BRA OriginalPackageTest_SuccessTail
pad $000120
OriginalPackageTest_RefusalTail:
    BRA OriginalPackageTest_RefusalTail
OriginalPackageTest_End:
