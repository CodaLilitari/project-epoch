"""Verify pinned Mesen source and emit a metadata-only NMI request design.

This reads existing sources/artifacts only. It does not execute an interrupt,
launch an emulator, write a register, assemble code, or modify any image.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_ROOT=ROOT/'private/research/mesen_nmi_request_2_1_1'
COMMIT='137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1'
MANIFEST_SHA='c7d42d4952ec19b421312b3d8f446c3742a755f538f10aac38e450875ac57745'
TREE_SHA='ce0f115f9df7f02a99b4c66c8e949d7e47e38a79dec0b29e1a6e2efe9187c77f'
PRIOR_SOURCES=('Core/Debugger/LuaApi.cpp','Core/SNES/SnesCpu.cpp','Core/SNES/SnesCpu.Shared.h',
               'Core/SNES/SnesCpu.Instructions.h','Core/SNES/SnesMemoryManager.cpp','Core/SNES/SnesPpu.cpp','Core/SNES/SnesConsole.cpp')


def identity(path:Path,expected:str|None=None)->dict:
    data=path.read_bytes();sha=hashlib.sha256(data).hexdigest()
    if expected is not None and sha!=expected:raise ValueError('pinned source/artifact drift: '+str(path))
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(data),'sha256':sha}


def collect()->dict:
    manifest_path=SOURCE_ROOT/'source_manifest.json';tree_path=SOURCE_ROOT/'upstream_tree.json'
    manifest_id=identity(manifest_path,MANIFEST_SHA);tree_id=identity(tree_path,TREE_SHA)
    manifest=json.loads(manifest_path.read_bytes());tree=json.loads(tree_path.read_bytes())
    if manifest['commit']!=COMMIT or tree.get('truncated') is not False:raise ValueError('wrong or incomplete upstream tree')
    entries={e['path']:e for e in tree['tree']}; sources=[]
    for entry in manifest['sources']:
        relative=entry['upstream_path'];p=SOURCE_ROOT/Path(relative).name
        item=identity(p,entry['sha256']);data=p.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=entry['git_blob_sha1'] or blob!=entries[relative]['sha'] or len(data)!=entry['size']:raise ValueError('upstream blob mismatch')
        sources.append({**item,'upstream_path':relative,'git_blob_sha1':blob,'url':f'https://github.com/SourMesen/Mesen2/blob/{COMMIT}/{relative}'})
    for relative in PRIOR_SOURCES:
        p=ROOT/'private/research/mesen_timing_api_2_1_1'/Path(relative).name;data=p.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=entries[relative]['sha']:raise ValueError('existing pinned source differs from same upstream tree')
        sources.append({**identity(p),'upstream_path':relative,'git_blob_sha1':blob,'url':f'https://github.com/SourMesen/Mesen2/blob/{COMMIT}/{relative}'})
    helper=ROOT/'private/test_runs/package_helper_v2_stack_20260908_finalledger1/helper.bin'
    helper_id=identity(helper,'77dc3224baaa93077218d43d64cbef10bb55494a37057c1a5bfcf0d8fd6758f8')
    code=helper.read_bytes()
    if len(code)!=577 or code[0xEE]!=0x20 or int.from_bytes(code[0xEF:0xF1],'little')!=0x8232:raise ValueError('selected helper JSR changed')
    carrier=ROOT/'private/test_runs/sha256_65c816/schala_sha256_profile1_benchmark.sfc'
    carrier_id=identity(carrier,'e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd');rom=carrier.read_bytes()
    if len(rom)!=8*1024*1024 or rom[0x40FFEA:0x40FFEC]!=rom[0xFFEA:0xFFEC] or int.from_bytes(rom[0x40FFEA:0x40FFEC],'little')!=0x8020:raise ValueError('native NMI vector mismatch')
    handler=rom[0x408020:0x408030]
    handler_sha=hashlib.sha256(handler).hexdigest()
    if handler_sha!='7455f84c456c0cfb47a1422ba3cf633cc4ec752ce9c8f30027b21520993af448':raise ValueError('original NMI handler drift')
    return {'schema':'project-epoch-mesen-nmi-request-source-v1','date':'2026-09-08',
        'evidence_level':'verified-static','evidence_scope':'pinned emulator source and original fixture bytes; runtime trigger is an unexecuted prediction',
        'source_revision':COMMIT,'source_manifest':manifest_id,'upstream_tree':tree_id,'source_files':sources,
        'audit_source':identity(Path(__file__).resolve()),'helper':helper_id,'original_carrier':carrier_id,
        'original_nmi_handler':{'cpu_start':'008020','cpu_end_exclusive':'008030','size':16,'sha256':handler_sha,'native_vector_cpu':'00FFEA'},
        'trigger_plan':{'kind':'debugger write through emulated register path','cpu_address':'004200','value':128,
            'api':'emu.write(0x004200,0x80,emu.memType.snesMemory)','pre_exec_cpu_address':'7F80EE',
            'normal_execution_ordinal':87,'predicted_service_continuation':'7F8232',
            'cpu_delay_cycles':2,'current_instruction_finishes_before_service':True,'register_write_advances_cpu_cycles':False,
            'preconditions':{'internalRegisters.nmiFlag':True,'internalRegisters.enableNmi':False,
                'internalRegisters.enableHorizontalIrq':False,'internalRegisters.enableVerticalIrq':False,
                'internalRegisters.enableAutoJoypadRead':False,'cpu.nmiFlagCounter':0,'cpu.needNmi':False,
                'cpu.irqLock':False,'cpu.irqSource':0,'cpu.prevIrqSource':0,'dmaController.needToProcess':False,'dmaController.hdmaChannels':0},
            'require_native_serialized_keys_and_types_at_runtime':True,'natural_ppu_latch_required':True,'never_assign_nmi_or_ppu_internal_state':True,
            'preparation':'run an explicit original idle fixture to an interior VBlank boundary; drain old requests before fixture baseline; no direct PPU timing edit',
            'one_shot':'disable NMI at handler entry through 4200=0 and record that debugger event; stop before another frame-edge request',
            'safe_initial_entry_sps':['1FEF','06D8'],'excluded_low_entry_sps':['0034','0033','0008']},
        'predicted_stack':{'helper_bytes_after_jsr':52,'native_hardware_bytes':4,'original_handler_save_bytes':3,'combined_maximum_bytes':59,
            'initial_1FEF':{'after_jsr':'1FBB','handler_entry':'1FB7','minimum':'1FB4'},
            'initial_06D8':{'after_jsr':'06A4','handler_entry':'06A0','minimum':'069D'}},
        'mandatory_witnesses':['4200 debugger-event before/after state and unchanged CPU/master clocks',
            'two JSR near-frame writes then four distinct hardware-frame writes','00FFEA/00FFEB actual vector reads',
            '008020 handler entry with hardware frame and native P transform','complete handler instruction and stack-access evidence',
            'one 16-bit counter increment at 7E5EF0 plus guards','pre-RTI and actual 7F8232 post-RTI continuation',
            'unchanged helper result and full final WRAM diff explained by complete CPU writes'],
        'limitations':['not a physical-SNES timing validation','register debugger event is not a CPU store instruction',
            'minimum original-handler fixture only; no normal-game NMI, IRQ nesting, publication visibility or game-stack ownership',
            'helper plus handler must remain inside declared PPU phase; missed phase or pre-existing request refuses'],
        'interrupt_executed':False,'rom_mutated':False,'production_approval':False,
        'reproduce':'python -B tools/audit_mesen_nmi_request_source_v1.py','serialization':'UTF-8 indented JSON, LF, one trailing newline'}


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(collect(),indent=2))
