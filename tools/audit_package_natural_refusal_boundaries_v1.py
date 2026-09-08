"""Canonical metadata-only queue, selected-target death and refusal boundary audit.

Selected instruction interpretations are reviewed assertions, not automatically
derived from hashes. Existing preparation/finalizer spans are reused unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import audit_package_cancellation_boundaries_v1 as prior

ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA="298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa"
SPANS=(
    ("queue-commit",0xC1161A,0xC1172A,"25a4741004ba44a6142785bd822812809acf6ad470f28415bbce82ecc35390b9"),
    ("queue-selected-fields",0xC116E6,0xC11713,"02dd0d7e38ce227be6a1971a9d4209dbc103e43bd055a492f4740162da2f59bf"),
    ("pending-first-hp",0xC1EC8F,0xC1ECA3,"86c35afbcbda563a31d906cac34a2f60e821645c621448ed16b7af94ef76dd42"),
    ("negative-hp-death-clamp",0xC1ECC7,0xC1ED17,"e851bfa66320e6dae1f9c0d5fef62903fa447a5051f4075a167ca47061575574"),
    ("selected-dead-target",0xC1C355,0xC1C371,"37fa65aeec1a93c0360b13159306e8d0a63234be092cd52ea3be3cc9ddb95b8c"),
    ("ready-list-insertion",0xC11B7C,0xC11B83,"1074eec1a292d91ad5ad1792a5be500487980c2559b79eebb83a4bc79dff9b9e"),
    ("failure-latch",0xC1C72B,0xC1C731,"00b61d4af0ecdd4432fdb986f4a98d3ff2acad576bcd41b9f071247c7267f18c"),
)


def audit(rom):
    inherited=prior.audit(rom)
    def data(address,size): return rom[address&0x3fffff:(address&0x3fffff)+size]
    spans=[]
    for role,start,end,expected in SPANS:
        value=hashlib.sha256(data(start,end-start)).hexdigest()
        if value!=expected: raise ValueError("natural-refusal canonical span drift")
        spans.append({"role":role,"cpu_start":f"{start:06X}","cpu_end_exclusive":f"{end:06X}","size":end-start,"sha256":value})
    checks=[]
    # Fixed-length absolute/indexed memory instructions. M-state preconditions
    # below distinguish byte queue/status writes from the observed word HP pass.
    for address,opcode,operand,instruction in (
        (0xC11B7C,0xAD,0x95D6,"LDA absolute; ready queue head"),
        (0xC11B80,0x9D,0xA6D9,"STA absolute,X; ready-list insertion"),
        (0xC116F2,0x9D,0x93EE,"STA absolute,X; queue ready flags"),
        (0xC116FA,0x9D,0x93EF,"STA absolute,X; command flags"),
        (0xC11700,0x9D,0x93F0,"STA absolute,X; copied menu field $9615"),
        (0xC11703,0xAD,0xA62D,"LDA absolute; selected target"),
        (0xC11706,0x9D,0x93F1,"STA absolute,X; queued target"),
        (0xC1170B,0x9D,0x93F3,"STA absolute,X; participant descriptor"),
        (0xC11710,0x9D,0x93F4,"STA absolute,X; queued action ID"),
        (0xC1EC99,0xBD,0x5E30,"LDA absolute,X; current HP word"),
        (0xC1EC9D,0xF9,0xB328,"SBC absolute,Y; first pending result word"),
        (0xC1ECA0,0x9D,0x5E30,"STA absolute,X; first HP result word"),
        (0xC1ECC7,0xBD,0x5E30,"LDA absolute,X; HP clamp input"),
        (0xC1ED04,0xBD,0x5E4A,"LDA absolute,X; current status byte 0"),
        (0xC1ED09,0x9D,0x5E4A,"STA absolute,X; death status"),
        (0xC1ED0F,0x9D,0x5E30,"STA absolute,X; zero HP clamp"),
        (0xC1C356,0xAD,0xB2AE,"LDA absolute; queued selected target"),
        (0xC1C359,0x20,0xC8F7,"JSR near; expand target identity"),
        (0xC1C367,0xBD,0x5E4A,"LDA absolute,X; selected target status"),
        (0xC1C36E,0x4C,0xC72B,"JMP near; selected dead target failure"),
        (0xC1C72D,0x8D,0xAF23,"STA absolute; invalid-target flag"),
    ):
        b=data(address,3)
        if b[0]!=opcode or int.from_bytes(b[1:],"little")!=operand: raise ValueError("selected canonical instruction drift")
        checks.append({"cpu_address":f"{address:06X}","instruction":instruction,"operand":f"{operand:04X}"})
    for address,opcode,operand,instruction in (
        (0xC1EC8F,0xC2,0x20,"REP; M=0 before HP subtraction"),
        (0xC1ECDC,0xE2,0x20,"SEP; M=1 for death status"),
        (0xC1ED07,0x09,0x80,"ORA immediate; set death bit"),
        (0xC1ED0C,0xC2,0x20,"REP; M=0 before zero HP store"),
        (0xC1C365,0xE2,0x20,"SEP; M=1 before selected-target check"),
        (0xC1C36A,0x89,0x80,"BIT immediate; selected target death bit"),
        (0xC1C72B,0xA9,0x01,"LDA immediate; failure flag value"),
    ):
        if data(address,2)!=bytes((opcode,operand)): raise ValueError("selected width/immediate assertion drift")
        checks.append({"cpu_address":f"{address:06X}","instruction":instruction,"operand":f"{operand:02X}"})
    for address,opcode,target,instruction in (
        (0xC1ECCA,0x30,0xC1ECDB,"BMI; negative HP enters death/clamp path"),
        (0xC1ECCF,0xF0,0xC1ECDB,"BEQ; zero HP enters death/clamp path"),
        (0xC1ECF5,0x90,0xC1ED04,"BCC; PC result slots bypass enemy reward call"),
        (0xC1C36C,0xF0,0xC1C371,"BEQ; living selected target skips failure JMP"),
    ):
        b=data(address,2)
        actual=(address&0xff0000)|((address+2+int.from_bytes(b[1:],"little",signed=True))&0xffff)
        if b[0]!=opcode or actual!=target: raise ValueError("selected relative branch drift")
        checks.append({"cpu_address":f"{address:06X}","instruction":instruction,"destination":f"{target:06X}"})
    for address,opcode,instruction in ((0xC1EC9C,0x38,"SEC before subtraction"),(0xC1ED0E,0x7B,"TDC supplies zero when D=0"),(0xC1C730,0x60,"RTS from invalid-target flag setter")):
        if data(address,1)!=bytes((opcode,)): raise ValueError("selected single-opcode drift")
        checks.append({"cpu_address":f"{address:06X}","instruction":instruction})
    roles={"queued-tech-preparation","prepare-charge-and-commit","shared-success-failure-tail","queue-and-partner-release","participant-atb-finalizer"}
    reused=[s for s in inherited["spans"] if s["role"] in roles]
    if len(reused)!=5: raise ValueError("prior cancellation span contract changed")
    return {"schema":"project-epoch-natural-refusal-boundaries-v1","date":"2026-09-08","evidence_level":"verified-static",
        "canonical_rom":{"size":prior.ROM_SIZE,"sha256":prior.ROM_SHA256},
        "annotation_source":{"revision":prior.SOURCE_REVISION,"sha256":SOURCE_SHA,
            "url":f"https://github.com/dscotton/ct_disassembly/blob/{prior.SOURCE_REVISION}/bank_C1.asm"},
        "new_spans":spans,"selected_instruction_assertions":checks,
        "reused_cancellation_spans":reused,
        "reused_auditor":{"path":"tools/audit_package_cancellation_boundaries_v1.py","sha256":hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest()},
        "scope":["Queue fields are interpreted under the observed M=1/D=0/DBR=7E menu contract; selected instructions alone do not prove every menu predecessor.",
            "The first pending HP word may wrap negative before later canonical death handling and zero clamp; no all-healing/overflow behavior claim.",
            "For the selected-dead-target path, status bit80 takes the AF23=1 setter and returns to the queued-Tech validation check.",
            "The existing shared finalizer/queue spans are reused, not relabeled as MP refund or fully decoded anew.",
            "Runtime witness pairing, full watched memory ledger and later next-command progression belong to the separate observer.",
            "No natural failure, high-selector refusal, game hook, allocation or PC07 is proved by this static artifact alone."],
        "reproduce":["python","-B","tools/audit_package_natural_refusal_boundaries_v1.py","--rom","private/input/rom_archive/Chrono Trigger (USA).sfc"],
        "production_approval":False,"rom_mutated":False}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.rom.read_bytes()),indent=2))
