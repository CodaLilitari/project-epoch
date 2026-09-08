"""Read-only stop/default-handler completion contract and policy intersection.

This is a reviewed bounded semantic model, not a CPU emulator or a proof of
all battle-command side effects. It changes no existing authoring policy.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import sys
import audit_schala_expanded_package_command_policy_v0 as policy

ROOT=Path(__file__).resolve().parents[1]
ROM=ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
SOURCE_REVISION='eeae27acdb6565e96d1d796a3d60792c250c0aa1'
SOURCE_SHA='298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa'
SPANS=(
    ('stop',0xC14CF0,0xC14CF7,'6b6ae5cc58afc13a72560a847a3fee2162fb54d4ebc452c0d4ee175305a01118'),
    ('default',0xC14CF7,0xC14D04,'3ecae483e18298b9f38e37cbd69662a65e1c6ff345e6f34fc568478d3e38ae6b'),
    ('pointer-advance',0xC175BB,0xC175CC,'81ec99810c0832f34277d117410919282e14891d51bb3869533e60ae3ef97142'),
    ('dispatch-control',0xC14CBF,0xC14CEF,'de7765406557d36ba72360c5830144026feaea182ea1887ca7ceb81949a7b2ed'),
    ('package-wait',0xC140CE,0xC140D3,'abdedd4f211f2e8cf12dc01899734d4f870bfa697b1a37d742cc23501597d2e1'),
    ('scene-wait',0xC140E7,0xC140EC,'d1f67450f4b76233667c43435c1a5829936c308a7b90b86cdfc67330ae9f9f3a'),
    ('counter-reset',0xCCF0E9,0xCCF0EC,'fb5a84e33ae83efddc90e0bda1b7aedb191b9e179ae2d1017e8a19bd09424161'),
)


def require(condition,message):
    if not condition:raise ValueError(message)


def integer(value,maximum,name):
    require(type(value) is int and 0<=value<=maximum,'invalid '+name)


@dataclass(frozen=True)
class HandlerState:
    pointer:int
    owner_active:bool
    package_counter:int
    scene_busy:int
    mode_a3d1:int


def step(opcode:int,state:HandlerState,*,direct_page:int=0,processor_decimal:bool=False)->HandlerState:
    """Only 00/01 under the declared native M1/X0/DBR7E entry contract.

    The model tracks selected semantic fields, not the complete CPU or WRAM.
    Same-value DP stores in the A3D1-set default path remain documented effects.
    """
    require(type(state) is HandlerState,'exact immutable state required')
    integer(opcode,255,'opcode');require(opcode in (0,1),'unsupported handler')
    integer(direct_page,65535,'direct page');require(direct_page==0,'D=0 is mandatory')
    require(type(processor_decimal) is bool and processor_decimal is False,'binary arithmetic required')
    integer(state.pointer,0xFFFFFF,'pointer');require(type(state.owner_active) is bool,'active flag type')
    for name in ('package_counter','scene_busy','mode_a3d1'):integer(getattr(state,name),255,name)
    if opcode==0:return HandlerState(state.pointer,False,state.package_counter,state.scene_busy,state.mode_a3d1)
    counter=(state.package_counter+1)&255 if state.mode_a3d1==0 else state.package_counter
    return HandlerState(state.pointer,state.owner_active,counter,state.scene_busy,state.mode_a3d1)


def caller_wait(counter:int,scene_busy:int)->str:
    integer(counter,255,'package counter');integer(scene_busy,255,'scene busy')
    if counter==0:return 'continue-package-loop'
    if scene_busy!=0:return 'wait-for-scene'
    return 'both-observed-waits-satisfied'


def identity(path:Path,expected:str|None=None):
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    require(expected is None or digest==expected,'source identity drift: '+path.name)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':digest}


def audit(rom:bytes):
    require(type(rom) is bytes and len(rom)==0x400000 and hashlib.sha256(rom).hexdigest()==ROM_SHA,'canonical ROM identity')
    def data(address,size):return rom[address&0x3FFFFF:(address&0x3FFFFF)+size]
    spans=[]
    for name,start,end,pin in SPANS:
        digest=hashlib.sha256(data(start,end-start)).hexdigest();require(digest==pin,'canonical span drift')
        spans.append({'name':name,'cpu_start':f'{start:06X}','cpu_end_exclusive':f'{end:06X}','size':end-start,'sha256':digest})
    checks=[]
    for address,opcode,operand in (
        (0xC14CF0,0xAE,0xA010),(0xC14CF3,0x9E,0x5DAC),(0xC14CF7,0xAD,0xA3D1),
        (0xC14CFD,0x4C,0x75BB),(0xC14D00,0xEE,0x9876),(0xC175C3,0x69,0),
        (0xC14CBF,0x9C,0xA00F),(0xC14CD4,0xFC,0x7A6B),(0xC14CD7,0xAD,0xA00F),
        (0xC140CE,0xAD,0x9876),(0xC140E7,0xAD,0x5D9B),(0xCCF0E9,0x9C,0x9876)):
        b=data(address,3);require(b[0]==opcode and int.from_bytes(b[1:],'little')==operand,'selected absolute/word operand drift')
        checks.append({'cpu_address':f'{address:06X}','opcode':f'{opcode:02X}','operand':f'{operand:04X}'})
    for address,opcode,operand in (
        (0xC175BB,0xC2,0x21),(0xC175BD,0x65,0xE6),(0xC175BF,0x85,0xE6),
        (0xC175C1,0xA5,0xE8),(0xC175C6,0x85,0xE8),(0xC175C9,0xE2,0x20),
        (0xC14CCD,0xC2,0x20),(0xC14CD2,0xE2,0x20)):
        require(data(address,2)==bytes((opcode,operand)),'selected width/DP operand drift')
        checks.append({'cpu_address':f'{address:06X}','opcode':f'{opcode:02X}','operand':f'{operand:02X}'})
    for address,opcode in ((0xC14CFC,0x7B),(0xC175C8,0x7B),(0xC14CC2,0x7B),(0xC14CD1,0x7B),
                           (0xC14CF6,0x60),(0xC14D03,0x60),(0xC175CB,0x60)):
        require(data(address,1)==bytes((opcode,)),'selected single opcode drift')
        checks.append({'cpu_address':f'{address:06X}','opcode':f'{opcode:02X}'})
    for address,opcode,target in ((0xC14CFA,0xF0,0xC14D00),(0xC14CDA,0xD0,0xC14CBF),
                                  (0xC140D1,0xF0,0xC140B0),(0xC140EA,0xD0,0xC140E1)):
        b=data(address,2);actual=(address&0xFF0000)|((address+2+int.from_bytes(b[1:],'little',signed=True))&65535)
        require(b[0]==opcode and actual==target,'selected branch destination drift')
        checks.append({'cpu_address':f'{address:06X}','opcode':f'{opcode:02X}','destination':f'{target:06X}'})
    grammar=policy.grammar
    table_spec=next(s for s in grammar.MACHINE_SPANS if s.name=='command_dispatch_table')
    table=grammar._observe_span(rom,table_spec)
    handlers=grammar._dispatch_handlers(rom);defaults={i for i,h in enumerate(handlers) if h==0x4CF7}
    allowed=policy.allowed_opcode_profile()
    require(handlers[1]==0x4CF7 and len(defaults)==70 and defaults.isdisjoint(allowed),'default-policy intersection drift')
    cases=[]
    for opcode in (0,1):
        for mode in (0,1):
            initial=HandlerState(0x423000,True,0,0,mode);after=step(opcode,initial)
            cases.append({'opcode':f'{opcode:02X}','before':asdict(initial),'after':asdict(after),
                'caller_wait':caller_wait(after.package_counter,after.scene_busy),
                'same_value_dp_word_stores':opcode==1 and mode!=0})
    for mode in range(256):
        for counter in range(256):
            state=HandlerState(0x42FFFF,True,counter,1,mode)
            stopped=step(0,state);default=step(1,state)
            require(stopped.pointer==state.pointer and stopped.package_counter==counter and not stopped.owner_active,'stop model invariant')
            require(default.pointer==state.pointer and default.owner_active and default.package_counter==((counter+1)&255 if mode==0 else counter),'default model invariant')
    return {'schema':'project-epoch-package-completion-contract-v1','date':'2026-09-08','evidence_level':'verified-static',
        'canonical_rom':{'size':len(rom),'sha256':ROM_SHA},'spans':spans,'selected_instruction_assertions':checks,
        'dispatch_table':table,'direct_default_handler_opcode_count':len(defaults),'allowed_v0_opcode_count':len(allowed),
        'default_handler_opcodes_allowed_by_v0':[],'canonical_01_is_default':True,'bounded_original_examples':cases,
        'exhaustive_mode_counter_pairs':65536,'current_policy_unchanged':True,
        'limits':['native M1/X0, D0, DBR7E and binary arithmetic are explicit semantic premises',
            'only command00/default01 selected effects are modeled, not arbitrary allowed command side effects',
            'DP E6/E7 and E8/E9 are rewritten with the same values on the A3D1-set default path',
            'no claim that these are the only global or aliased writers of completion state',
            'no newly authored completion policy, stream, native diagnostic, game hook or allocation is approved'],
        'production_approval':False}


def collect():
    report=audit(ROM.read_bytes())
    report['sources']={
        'auditor':identity(Path(__file__).resolve()),
        'tests':identity(ROOT/'tests/test_schala_package_completion_contract_v1.py'),
        'annotation':identity(ROOT/'private/research/ct_disassembly_eeae27a/bank_C1.asm',SOURCE_SHA),
        'policy':identity(Path(policy.__file__)),
        'policy_reference':identity(policy.REFERENCE_PATH,policy.REFERENCE_SHA256),
        'grammar':identity(Path(policy.grammar.__file__)),
        'grammar_reference':identity(policy.grammar.REFERENCE_PATH,policy.grammar.REFERENCE_SHA256)}
    report['wrong_annotation']={'revision':SOURCE_REVISION,'line':9969,
        'url':f'https://github.com/dscotton/ct_disassembly/blob/{SOURCE_REVISION}/bank_C1.asm#L9969',
        'claim':'A3D1-set default handler consumes the command',
        'correction':'D0 supplies zero advance, so the pointer remains on the same command; no completion-counter increment'}
    report['reproduce']=['python','-B','tools/audit_schala_package_completion_contract_v1.py']
    return report


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode('utf-8'))
