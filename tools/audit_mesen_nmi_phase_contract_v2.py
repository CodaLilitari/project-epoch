"""Read-only correction of the published Mesen NMI Lua observability contract.

Pins upstream bytes, the exact historical claim, and both failed/successful
exploratory receipts. Does not launch an emulator or promote a runtime proof.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import audit_mesen_nmi_request_source_v1 as prior

ROOT=Path(__file__).resolve().parents[1]
PUBLICATION='9e42e747fc523d7a99dad90ce21940dfbd18c51c'
PPU_SHA='5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180'
EXCLUSION_SHA='7b96d992d9395abd46a8060e7c09a65aa31fb2508a4127242c5f60c8fd3fc724'
PRIOR_DOC_SHA='c8262bf4ea157e58f17e55bbd0d9581055424798c463807c804f019ec62725cd'
FLAGS={'internalRegisters.nmiFlag','internalRegisters.enableNmi','internalRegisters.enableHorizontalIrq',
       'internalRegisters.enableVerticalIrq','internalRegisters.enableAutoJoypadRead','cpu.nmiFlagCounter',
       'cpu.needNmi','cpu.irqLock','cpu.irqSource','cpu.prevIrqSource','dmaController.needToProcess',
       'dmaController.hdmaChannels','dmaController.hdmaPending','dmaController.hdmaInitPending',
       'dmaController.dmaStartDelay','dmaController.dmaPending'}
TIMING={'masterClock','memoryManager.masterClock','cpu.cycleCount','frameCount','ppu.frameCount',
        'ppu.scanline','memoryManager.hClock','clockRate'}


def require(value,message):
    if not value:raise ValueError(message)


def source_span(raw:bytes,start:int,end:int,expected:str)->dict:
    lines=raw.splitlines(keepends=True)
    require(0<start<=end<=len(lines),'invalid source line span')
    selected=b''.join(lines[start-1:end]);digest=hashlib.sha256(selected).hexdigest()
    require(digest==expected,'source line span drift')
    return {'first_line':start,'last_line':end,'bytes':len(selected),'sha256':digest,
            'encoding':'exact upstream UTF-8 bytes, including original LF line endings'}


def phase_witness(record:dict)->dict:
    before=record['preparation']['latch_rise']['before'];after=record['preparation']['latch_rise']['after']
    baseline=record['events'][0]
    require(baseline['kind']=='fixture-baseline','missing fixture baseline')
    require(set(baseline['flags'])==FLAGS and set(baseline['timing'])==TIMING,'observed runtime key inventory drift')
    require(before['latch'] is False and after['latch'] is True and not(before['peek']&128) and after['peek']&128,'missing observed latch transition')
    require(before['clock']<after['clock']<baseline['timing']['memoryManager.masterClock'],'transition/baseline clock order')
    require(baseline['timing']['ppu.scanline']==after['scanline']+1,'baseline not one observed scanline after rise')
    return {'case':record['name'],'preparation':record['preparation'],'baseline_timing':baseline['timing'],
            'observed_flag_keys':sorted(baseline['flags']),'observed_timing_keys':sorted(baseline['timing']),
            'interpretation':'two consecutive idle-instruction samples bracket the natural latch rise; no exact edge clock is inferred'}


def collect()->dict:
    original=prior.collect() # verifies all 24 pinned source blobs and original fixture identities
    ppu=ROOT/'private/research/mesen_timing_api_2_1_1/SnesPpu.cpp'
    ppu_id=prior.identity(ppu,PPU_SHA);exclusion=source_span(ppu.read_bytes(),2287,2292,EXCLUSION_SHA)
    historic=subprocess.run(['git','show',PUBLICATION+':docs/mesen_nmi_request_source_v1.md'],cwd=ROOT,
                            capture_output=True,check=True).stdout
    require(hashlib.sha256(historic).hexdigest()==PRIOR_DOC_SHA,'historical published claim drift')
    require('`ppu.nmiScanline`' in historic.decode().splitlines()[93] and '`ppu.nmiScanline`' in historic.decode().splitlines()[108],
            'historical wrong claim line anchors drift')
    prior_ids=[prior.identity(ROOT/p,h) for p,h in (
        ('tools/audit_mesen_nmi_request_source_v1.py','d3fd8af81c89fcc8040f5daedafe328a975d5cd7f7dfef01043a9810514225d2'),
        ('references/mesen_nmi_request_source_v1.json','e126a4eabc8def87b7055d80298a85658126fa593cc6f63023484bc189fa6494'))]
    failed=ROOT/'private/test_runs/package_helper_v2_nmi_20260908_pilot1'
    failed_ids=[prior.identity(failed/p,h) for p,h in (
        ('trace.json','afb1fac64efd1cf2fba526478a4d39667d831a8aaa9d927813fcf03333f8338d'),
        ('launch_inputs.json','6e956dce76467b4f9551de08df08a23d4315f7ac9ad0433397a36bd3ea53c6fb'),
        ('staged/collector.lua','803176d842464bccac0c2a894b5ed8d8626032a1e72c8276c1dcc465f03517e0'))]
    failure=json.loads((failed/'trace.json').read_bytes())
    require(failure['records']==[] and failure['partial_events']==[] and "nil value (field 'ppu.nmiScanline')" in failure['error'],
            'failed pilot interpretation changed')
    pilot=ROOT/'private/test_runs/package_helper_v2_nmi_20260908_pilot4/trace.json'
    pilot_id=prior.identity(pilot,'86afd09fa16a4d49fff5f5e55766f4b8fab6255366e2bb4e09892db5b0711937')
    trace=json.loads(pilot.read_bytes())
    require(trace['error'] is None and trace['partial_events']==[] and len(trace['records'])==2,'pilot completion drift')
    return {'schema':'project-epoch-mesen-nmi-phase-contract-v2','date':'2026-09-08',
        'evidence_scope':'verified-static source correction plus exact exploratory runtime key/phase witnesses; no matched interrupt acceptance',
        'audit_source':prior.identity(Path(__file__).resolve()),'upstream_commit':prior.COMMIT,
        'upstream_tree':original['upstream_tree'],'source_manifest':original['source_manifest'],
        'prior_source_and_reference_preserved':prior_ids,
        'incorrect_published_claim':{'commit':PUBLICATION,'path':'docs/mesen_nmi_request_source_v1.md',
            'original_bytes':len(historic),'original_sha256':PRIOR_DOC_SHA,'phase_claim_lines':[93,94],
            'inventory_claim_line':109,'serialization_attribution_lines':[113,115],
            'correction':'ppu.nmiScanline is hidden from the Lua Map serialization; do not require, assign, or substitute this key'},
        'correct_source':{'file':ppu_id,'exclusion':exclusion,'public_scanline_line':2255,
            'url':f'https://github.com/SourMesen/Mesen2/blob/{prior.COMMIT}/Core/SNES/SnesPpu.cpp#L2287'},
        'failed_pilot':{'artifacts':failed_ids,'error':failure['error'],'completed_records':0,'active_events':0,
            'interpretation':'preparation failed before a fixture baseline or interrupt request; this is not a failed hardware NMI'},
        'corrected_phase_contract':{'phase_source':'observe false then true internalRegisters.nmiFlag while original idle CPU instructions advance emulation',
            'cross_check':'debugger peek of 4210 bit7 at both samples; no side-effecting CPU register read',
            'interior_gate':'first observed later instruction on scanline observed-rise.scanline+1 with latch true and all declared interrupt/DMA pending state clear',
            'bounds':'finite full-master-clock wait; request and complete before declared VBlank phase limit',
            'forbidden_mutations':['PPU scanline or clocks','NMI latch/countdown/need flag','manufactured hardware stack frames'],
            'allowed_fixture_setup':'declared original WRAM code/data and baseline CPU state outside observation; normal debugger register writes4200/420B/420C',
            'required_getState_flag_keys':sorted(FLAGS),'required_getState_timing_keys':sorted(TIMING)},
        'exploratory_corrected_key_phase_receipt':{'trace':pilot_id,'witnesses':[phase_witness(r) for r in trace['records']],
            'limitation':'this collector checks only the source/key/phase correction; interrupt proof requires the separate native validator and independent review'},
        'production_approval':False,'serialization':'UTF-8 indented JSON, LF, one trailing newline',
        'reproduce':'python -B tools/audit_mesen_nmi_phase_contract_v2.py'}


if __name__=='__main__':sys.stdout.buffer.write((json.dumps(collect(),indent=2)+'\n').encode())
