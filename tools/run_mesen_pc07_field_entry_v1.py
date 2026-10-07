"""Plan or collect one clean-ROM entry/movement observation, without mutation.

Default is read-only. Reuses the pinned isolated runtime launcher support.
An observed baseline is not PC07 construction, movement, or allocation proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import audit_location_event_items as parser
import run_mesen_save_layout_native_v1 as runtime

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='project-epoch-pc07-field-entry-v1'
COLLECTOR=ROOT/'tools/mesen_pc07_field_entry_v1.lua'
ROM=ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA='06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
STATE=ROOT/'private/test_runs/mesen2/load_entry_checkpoint_v1_native_save_run2/load_entry.mss'
STATE_SHA='cdbfc74c21a6a345f5c9b7d74fce9159b95a3ff735ecd92afde70332bce0a5e1'
SRAM=ROOT/'private/test_runs/mesen2/save_layout_native_v1_save_run1/trace.terminal.sram.bin'
SRAM_SHA='0032c1cdb1600ec0eba51243200e1361d54014eb2755d6ace0cf4661d2f341e8'
DESIGN='private/research/pc07_field_route_v1/field_route_design.json'
PINNED={
    DESIGN:'243b78eeca4b645c749af299ffa679e21d158464f746685f60d53c50afefd37b',
    'tools/audit_location_event_items.py':'cb39dd4485e6330c4f9d5b8817fe8e6a161cb2e965020cb1cd10a3fd30f7812a',
    'tools/run_mesen_save_layout_native_v1.py':'847bf77d28757ddad07b75b30d9071534b4792f7ad09a6cb3762153c8c29cd75',
    'references/ct_disassembly/bank_C0.asm':'b5b209cd03ae430f095482a429798ee3600d97af3774841c069d8f9a071140b8',
    'references/ct_disassembly/bank_C2.asm':'d96c0d9707d9150dbdb3ad7d995f7ae135e87ebb6329691cab2eb86447611032',
    'references/ct_disassembly/bank_E4.asm':'160bdd0ef4791f81a468ca0088f65a79fa6fbd638584fece50d6735950b29fda',
    'references/ct_disassembly/bank_FF.asm':'18f30c2a4f547722f30934bde43eb6a638d9467aa064e21340aa2065ab71829e',
}
LABELS=('scene_entry','canonical_event_ready','poll_90','poll_150','poll_210','poll_300')

def sha(data):return hashlib.sha256(data).hexdigest()

def private_path(path):
    candidate=(path if path.is_absolute() else ROOT/path)
    resolved=candidate.resolve();private=(ROOT/'private').resolve()
    if not resolved.is_relative_to(private) or resolved==private or candidate.is_symlink():
        raise ValueError('output must be a nonsymlink path below private/')
    return resolved

def bundle():
    for path,digest in PINNED.items():runtime.read_regular(ROOT/path,digest=digest)
    paths=(*PINNED,'tools/run_mesen_pc07_field_entry_v1.py','tools/mesen_pc07_field_entry_v1.lua',
           'tests/test_mesen_pc07_field_entry_v1.py')
    rows=[{'path':path,'sha256':sha((ROOT/path).read_bytes()),'bytes':(ROOT/path).stat().st_size} for path in paths]
    return {'sha256':sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),'sources':rows}

def comparison_inputs(rom):
    parser.validate_canonical_rom(rom)
    design=json.loads((ROOT/DESIGN).read_text())
    if parser.location_event_ids(rom)[0x1DA]!=0x125:raise ValueError('selected location/event association')
    snes,offset=parser.event_pointer(rom,0x125)
    packet=parser.decompress_packet(rom,offset).data
    scene=design['selected_scene']
    if snes!=0xFADCC8 or len(packet)!=2361 or sha(packet)!=scene['decompressed_sha256']:
        raise ValueError('selected canonical event packet drift')
    commands=parser.parse_event(0x125,packet)
    # Exact five source copies at C05CEC..C05D36, including their shared bytes.
    builtins=rom[0x5D37:0x5D57]+rom[0x5D50:0x5D70]*3+rom[0x5D68:0x5D6E]
    spans=design['provenance']['source_anchors']
    for span in spans:
        start=int(span['cpu_start'],16)-0xC00000
        if sha(rom[start:start+span['size']])!=span['canonical_rom_span_sha256']:
            raise ValueError('design native span drift: '+span['id'])
    return packet,builtins,{'location':0x1DA,'event_id':0x125,'packet_pointer':snes,
        'packet_bytes':len(packet),'packet_sha256':sha(packet),'parsed_command_count':len(commands),
        'builtin_wram_start':0x7F3700,'builtin_bytes':len(builtins),'builtin_sha256':sha(builtins),
        'stored_near_return':0x0111,'actual_next_pc':0xC00112,'source_spans':spans,
        'entry_pc':0xC00085,'packet_ready_pc':0xC05D36,'canonical_object_count':packet[0],
        'input_schedule':{'Left':[120,131],'Right':[180,191],'stop_poll':300},
        'interpretation':'Canonical dedicated PC loaders may reach the shared role path; generic80 is recorded only if native execution reaches it.'}

def check_ready_snapshot(wram,row,packet,builtins):
    if len(wram)!=0x20000:raise ValueError('WRAM size')
    c=row['cpu']
    if c['k']!=0xC0 or c['pc']!=0x5D36 or c['d']!=0x100 or c['dbr']!=0 or c['emulationMode'] or c['ps']&0x30!=0x20:
        raise ValueError('canonical packet-ready native context')
    if row['location']!=0x1DA or row['stored_near_return']!=0x0111:
        raise ValueError('packet-ready location/return word')
    sp=c['sp']
    if not 0<=sp<0x1FFE or wram[sp+1:sp+3]!=b'\x11\x01':raise ValueError('captured near return stack bytes')
    if wram[0x12000:0x12000+len(packet)]!=packet:raise ValueError('captured canonical packet mismatch')
    if wram[0x13700:0x13700+len(builtins)]!=builtins:raise ValueError('captured canonical builtin mismatch')

def collect(args):
    identity=bundle()
    original={'rom':(ROM,runtime.read_regular(ROM,size=0x400000,digest=ROM_SHA)),
              'state':(STATE,runtime.read_regular(STATE,size=93029,digest=STATE_SHA)),
              'sram':(SRAM,runtime.read_regular(SRAM,size=8192,digest=SRAM_SHA))}
    for name,(size,digest) in runtime.RUNTIME.items():
        path=ROOT/'private/tools/mesen2/app'/name
        original[name]=(path,runtime.read_regular(path,size=size,digest=digest))
    packet,builtins,contract=comparison_inputs(original['rom'][1])
    output=private_path(args.output)
    if any(path.resolve().is_relative_to(output) for path,_ in original.values()):raise ValueError('output contains input')
    report={'schema':SCHEMA+'-run','source_bundle':identity,'input_contract':contract,
        'inputs':{name:{'path':str(path),'bytes':len(data),'sha256':sha(data)} for name,(path,data) in original.items()},
        'launch_executed':False,'evidence':'verified-static-plan','rom_unmodified':True,
        'debugger_wram_cpu_writes':False,'acquisition_then_checkpoint_replay':True,'direct_coldboot':False,
        'playable_pc07':False,'whole_engine_proved':False,'deferred_stop_excluded':True,
        'shutdown_sram_authoritative':False}
    if not args.run_reviewed_bundle:
        runtime.check_inputs(original)
        if bundle()!=identity:raise ValueError('plan source drift')
        return report
    if args.run_reviewed_bundle!=identity['sha256']:raise ValueError('exact reviewed bundle required')
    if output.exists():raise ValueError('fresh private run directory required')
    output.mkdir(parents=True)
    app=output/'app';(app/'Saves').mkdir(parents=True)
    for name in runtime.RUNTIME:(app/name).write_bytes(original[name][1])
    expected={'diagnostic.sfc':original['rom'][1],'entry.mss':original['state'][1],
              'input.sram':original['sram'][1],'collector.lua':COLLECTOR.read_bytes(),
              'canonical_packet.bin':packet,'canonical_builtins.bin':builtins}
    for name,data in expected.items():(output/name).write_bytes(data)
    (app/'Saves/diagnostic.srm').write_bytes(original['sram'][1])
    env={key:value for key,value in os.environ.items() if not key.startswith('PE_FIELD_ENTRY_')}
    env.update(PE_FIELD_ENTRY_OUTPUT=str(output),PE_FIELD_ENTRY_STATE=str(output/'entry.mss'),
               PE_FIELD_ENTRY_SRAM=str(output/'input.sram'),PE_FIELD_ENTRY_PACKET=str(output/'canonical_packet.bin'),
               PE_FIELD_ENTRY_BUILTINS=str(output/'canonical_builtins.bin'),PE_FIELD_ENTRY_BUNDLE=identity['sha256'])
    command=[str(app/'Mesen.exe'),'--testRunner','--timeout=120','--doNotSaveSettings',
             '--debug.scriptWindow.allowIoOsAccess=true','--snes.port1.type=SnesController',
             str(output/'collector.lua'),str(output/'diagnostic.sfc')]
    (output/'plan.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    process=None;failure=None;attempted=False;launched=False
    try:
        runtime.check_inputs(original)
        if bundle()!=identity:raise ValueError('source drift before launch')
        attempted=True
        process=subprocess.run(command,cwd=app,env=env,capture_output=True,text=True,timeout=140,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        launched=True
        if process.returncode!=63 or (output/'failure.txt').exists():raise ValueError('collector failure')
        rows=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
        if rows[0].get('schema')!=SCHEMA or rows[0].get('source_bundle')!=identity['sha256'] or rows[-1]['kind']!='success':raise ValueError('trace envelope')
        snaps=[row for row in rows if row['kind']=='snapshot']
        if tuple(row['label'] for row in snaps)!=LABELS:raise ValueError('snapshot sequence')
        for row in snaps:
            label=row['label']
            if (output/(label+'.sram.bin')).read_bytes()!=original['sram'][1]:raise ValueError('observed SRAM drift')
            if (output/(label+'.wram.bin')).stat().st_size!=0x20000:raise ValueError('WRAM snapshot size')
        check_ready_snapshot((output/'canonical_event_ready.wram.bin').read_bytes(),snaps[1],packet,builtins)
        returns=[r for r in rows if r['kind']=='decompression-caller-return']
        if len(returns)!=1 or returns[0]['context']['cpu']['k']!=0xC0 or returns[0]['context']['cpu']['pc']!=0x112:
            raise ValueError('actual native decompression caller return')
        report['records']=len(rows)
        report['observed_exec_sites']={f'{pc:06X}':sum(r['kind']=='exec' and r['site']==pc for r in rows)
                                       for pc in sorted({r['site'] for r in rows if r['kind']=='exec'})}
        report['packet_builtin_stack_and_caller_checked']=True
        report['movement_and_call_semantics_review_pending']=True
    except subprocess.TimeoutExpired as exc:launched=True;failure=repr(exc)
    except Exception as exc:failure=repr(exc)
    finally:
        try:
            runtime.check_inputs(original)
            if bundle()!=identity:raise ValueError('source changed during observation')
            if any((output/name).read_bytes()!=data for name,data in expected.items()):raise ValueError('immutable staged input drift')
        except Exception as exc:failure=repr(exc)
        report.update(launch_executed=launched,launch_attempted=attempted,
            status='quarantined-failure' if failure else 'collected-awaiting-entry-movement-review',
            evidence='rejected-pilot' if failure else 'observed-runtime',failure=failure,
            returncode=process.returncode if process else None)
        report['artifacts']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
            for p in output.iterdir() if p.is_file() and p.suffix in ('.jsonl','.bin','.png','.txt')}
        (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if failure:raise RuntimeError(failure)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--run-reviewed-bundle')
    print(json.dumps(collect(p.parse_args()),indent=2))
