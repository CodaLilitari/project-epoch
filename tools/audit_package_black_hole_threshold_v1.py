"""Read-only pinned-ROM proof of Black Hole's inclusive comparison boundary.

This emits metadata and an original instruction-semantics truth-table hash.
It writes no ROM, patch, source extraction, trace, or output file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROM_SIZE=0x400000
ROM_SHA256='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
SOURCE_REVISION='eeae27acdb6565e96d1d796a3d60792c250c0aa1'
SOURCE_SHA256='298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa'
SPANS=(
    ('black-hole-effect-and-mask-tail',0xC1F132,0xC1F1C7,'f94e11174a1a852b30352a765aedddd47195e9324fb71e00e19be4c9fd0c89aa'),
    ('boss-and-threshold-branches',0xC1F139,0xC1F14A,'ca28e738c8ef98f0f9e4a636df0bad111395294fb648a8ada14bbaeb6cb8abb2'),
    ('inclusive-threshold-counterexample',0xC1F144,0xC1F14A,'c6f99397ead976a855cd7f8dc2c5fb643d6370fdb3be3efb16228355e1499859'),
    ('survivor-mask-exhaustion',0xC1F156,0xC1F1C7,'440f24c139b59e2e701637bf2c38bbb1ce4c15e1adb77a3482a7f4144d530a47'),
)


def comparison_accepts(roll:int,threshold:int)->bool:
    """Unsigned 8-bit CMP, then BEQ success, then BCS survivor, else success."""
    if type(roll) is not int or type(threshold) is not int or not 0<=roll<=255 or not 0<=threshold<=255:
        raise ValueError('comparison inputs must be bytes')
    zero=roll==threshold
    carry=roll>=threshold
    if zero: return True
    if carry: return False
    return True


def audit(rom:bytes)->dict:
    if type(rom) is not bytes or len(rom)!=ROM_SIZE or hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
        raise ValueError('canonical US Rev0 ROM identity required')
    def at(address,size):
        return rom[address&0x3FFFFF:(address&0x3FFFFF)+size]
    spans=[]
    for role,start,end,expected in SPANS:
        actual=hashlib.sha256(at(start,end-start)).hexdigest()
        if actual!=expected: raise ValueError('canonical span drift: '+role)
        spans.append({'role':role,'cpu_start':f'{start:06X}','cpu_end_exclusive':f'{end:06X}',
                      'size':end-start,'sha256':actual})
    checks=[]
    for address,opcode,operand,mnemonic in (
        (0xC1F139,0x89,0x80,'BIT immediate, 8-bit'),
        (0xC1F13F,0xA9,100,'LDA immediate, 8-bit'),
        (0xC1F144,0xC5,0x1C,'CMP direct page, 8-bit'),
    ):
        data=at(address,2)
        if data[0]!=opcode or data[1]!=operand: raise ValueError('instruction assertion failed')
        checks.append({'address':f'{address:06X}','instruction':mnemonic,'operand':operand})
    for address,opcode,target,mnemonic in (
        (0xC1F13B,0xD0,0xC1F156,'BNE'),
        (0xC1F146,0xF0,0xC1F14A,'BEQ'),
        (0xC1F148,0xB0,0xC1F156,'BCS'),
    ):
        data=at(address,2)
        destination=(address&0xFF0000)|((address+2+int.from_bytes(data[1:],'little',signed=True))&0xFFFF)
        if data[0]!=opcode or destination!=target: raise ValueError('branch assertion failed')
        checks.append({'address':f'{address:06X}','instruction':mnemonic,'destination':f'{target:06X}'})
    data=at(0xC1F141,3)
    if data[0]!=0x20 or int.from_bytes(data[1:],'little')!=0xAF22: raise ValueError('RNG call assertion failed')
    checks.append({'address':'C1F141','instruction':'JSR','destination':'C1AF22'})
    data=at(0xC1F1C0,3)
    if data[0]!=0x8D or int.from_bytes(data[1:],'little')!=0xAE94: raise ValueError('alternate flag store assertion failed')
    checks.append({'address':'C1F1C0','instruction':'STA absolute','operand':'AE94'})
    truth=bytes(int(comparison_accepts(roll,threshold)) for threshold in range(256) for roll in range(256))
    if any(comparison_accepts(roll,threshold)!=(roll<=threshold) for threshold in range(256) for roll in range(256)):
        raise ValueError('reviewed CMP/BEQ/BCS semantics changed')
    return {
        'schema':'project-epoch-black-hole-threshold-v1','evidence_level':'verified-static',
        'rom':{'size':ROM_SIZE,'sha256':ROM_SHA256},
        'source':{'revision':SOURCE_REVISION,'bank_C1_asm_sha256':SOURCE_SHA256,
                  'url':f'https://github.com/dscotton/ct_disassembly/blob/{SOURCE_REVISION}/bank_C1.asm#L30747-L30767'},
        'correction':{'proposed_id':'MAP-009','scope':'Black Hole nonboss comparison; boss path bypasses this comparison',
                      'wrong_claims':[{'lines':[30747,30754],'claim':'roll strictly below the threshold succeeds'},
                                      {'lines':[30767,30767],'claim':'roll greater than or equal to 40 takes survivor path'}],
                      'corrected_predicate':'roll <= threshold succeeds; only roll > threshold takes survivor path',
                      'equality_counterexample':{'roll':40,'threshold':40,'cmp_zero':True,'cmp_carry':True,'first_taken_branch':'C1F146 -> C1F14A'},
                      'uniform_rng_distribution_proved':False,'threshold_40_source':'pinned upstream annotation; this audit does not derive the Tech parameter table'},
        'spans':spans,'instruction_assertions':checks,
        'original_semantics_truth_table':{'byte_count':len(truth),'order':'threshold 0..255 outer, roll 0..255 inner; success=1, survivor=0',
                                         'sha256':hashlib.sha256(truth).hexdigest(),'all_65536_pairs_match_inclusive_unsigned_predicate':True},
        'limitations':['No RNG-distribution proof or probability claim.','No dynamic equality-boundary execution in this artifact.',
                       'Semantic instruction labels are reviewed interpretations, not auto-derived from hashes.',
                       'No hook, allocation, high selector, helper installation, or ROM mutation.'],
    }


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(audit(args.rom.read_bytes()),indent=2))
