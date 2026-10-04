"""Source-pinned, metadata-only IRQ transition composition. No native run.

The v3 reference is reused by its exact identity. It supplies an observation,
not the callback/write closure required for a game deadline. This auditor
never reads a ROM, save, raw game trace, or emulator state.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
from itertools import product
import json
from pathlib import Path

from schala_irq_exec_v1 import ExecModel, NestedEvent, CONDITIONAL_PREMISES, require
from schala_irq_transition_core_v1 import IrqState, TickContext, process_irq_counters
from schala_irq_cpu_gate_v1 import (CpuGateState, sample_cpu_cycle, instruction_boundary,
    set_interrupt_disable, clear_irq_source, PPU_IRQ)

ROOT=Path(__file__).resolve().parents[1]
REVISION='137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1'
PHASE_PIN=('references/schala_package_resolver_phase_v3.json',63846,
    'ef647b161531bc1d207f3aa1feacb4b8d669863e04b7390348d0d16381a3d1c1')
UPSTREAM_PIN=('references/mesen_irq_transition_sources_v1.json',7340,
    'bbef4d4282eb7e696c9e51a6b1c110720634c44dbdb4c175bc31193f670830e6')
ORIGINAL_FILES=(
    'tools/schala_irq_transition_core_v1.py','tests/test_schala_irq_transition_core_v1.py',
    'tools/schala_irq_exec_v1.py','tests/test_schala_irq_exec_v1.py',
    'tools/schala_irq_cpu_gate_v1.py','tests/test_schala_irq_cpu_gate_v1.py',
    'tools/audit_schala_irq_request_transition_v1.py','tests/test_audit_schala_irq_request_transition_v1.py')
SPANS=(
    ('InternalRegisters.h',81,162,'consume pending, update counters, compare and arm'),
    ('InternalRegisters.cpp',180,187,'flag setter clears source but never asserts'),
    ('InternalRegisters.cpp',246,255,'TIMEUP read captures old flag then conditionally clears'),
    ('InternalRegisters.cpp',299,375,'NMITIMEN and immediate timer-write comparison'),
    ('InternalRegisters.cpp',394,413,'serializer replaces counters and pending state'),
    ('SnesMemoryManager.cpp',179,275,'nested refresh and event-before-current-phase Exec'),
    ('SnesMemoryManager.cpp',293,328,'DMA source reads may have register side effects'),
    ('SnesMemoryManager.cpp',360,388,'reverse DMA may write IRQ control registers'),
    ('SnesDmaController.cpp',347,405,'HDMA request flags and separate service dispatch'),
    ('SnesPpu.cpp',395,511,'ordinary line rule and renderer/control/frame callback frontier'),
    ('BaseCartridge.h',144,149,'conditional virtual coprocessor synchronization'),
    ('Emulator.h',308,313,'PPU debugger callback frontier'),
    ('SnesDebugger.cpp',413,439,'PPU callback SPC/DSP and debugger frontier'),
    ('SnesConsole.cpp',72,107,'end-frame callback and reset frontier'),
    ('SnesCpu.cpp',29,83,'post-op acceptance selection and WAI pre-idle wake snapshot'),
    ('SnesCpu.cpp',121,130,'DMA service precedes sampling'),
    ('SnesCpu.Shared.h',315,367,'NMI sampling, IRQ sample and source mask operations'),
    ('SnesCpuTypes.h',5,78,'CPU byte types, status mask, source bits and stop states'),
    ('SnesCpu.Instructions.h',505,534,'frame/vector work after selection; outside model'),
)


def serial(value):
    return (json.dumps(value,indent=2)+'\n').encode('utf-8')


def identity(relative, size=None, digest=None):
    require(type(relative) is str and not Path(relative).is_absolute() and '..' not in Path(relative).parts,
            'bounded repository path')
    raw=(ROOT/relative).read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    require(size is None or len(raw)==size,'size drift: '+relative)
    require(digest is None or sha==digest,'hash drift: '+relative)
    return {'path':relative,'size_bytes':len(raw),'sha256':sha}


def observed_seed(reference):
    require(reference['schema']=='project-epoch-package-resolver-phase-v3-accepted-pair','v3 schema')
    require(reference['full_trace_bytes_identical'] is True and len(reference['runs'])==2,'accepted pair')
    require(reference['deadline_certified'] is False and reference['production_approval'] is False,
            'preserve v3 non-admission')
    entries=[]
    for run in reference['runs']:
        selected=[x for x in run['projection']['phases'] if x['kind']=='resolver-entry']
        require(len(selected)==1,'one resolver entry')
        entries.append(selected[0])
    require(entries[0]==entries[1],'pair seed equality')
    row=entries[0]
    require((row['master_clock'],row['scanline'],row['hclock'])==(2155080050,119,754),'exact raster seed')
    h=row['hardware']
    expected={'internalRegisters.hCounter':186,'internalRegisters.vCounter':119,
        'internalRegisters.enableHorizontalIrq':False,'internalRegisters.enableVerticalIrq':True,
        'internalRegisters.horizontalTimer':0,'internalRegisters.verticalTimer':211,
        'internalRegisters.needIrq':0,'internalRegisters.irqFlag':False,'internalRegisters.irqLevel':False,
        'internalRegisters.enableNmi':True,'internalRegisters.nmiFlag':False,
        'cpu.irqSource':0,'cpu.prevIrqSource':0,'cpu.irqLock':False,'cpu.needNmi':False,'cpu.nmiFlagCounter':0,
        'dmaController.hdmaChannels':255,'dmaController.dmaPending':False,'dmaController.dmaStartDelay':False,
        'dmaController.needToProcess':False,'dmaController.hdmaPending':False,'dmaController.hdmaInitPending':False}
    require(all(type(h[k]) is type(v) and h[k]==v for k,v in expected.items()),'exact hardware seed types and values')
    require(row['dma_active_channels']==[] and row['hdma_unfinished_enabled_channels']==list(range(8)),
            'HDMA is enabled, not future-absent')
    state=IrqState(h_counter=186,v_counter=119,h_timer=0,v_timer=211,
        v_enabled=True,irq_enabled_cache=True,nmi_enabled=True)
    return row,state


def kernel(state, **kwargs):
    args=dict(clock=2155080050,line=119,hclock=754,premises=CONDITIONAL_PREMISES)
    args.update(kwargs)
    return ExecModel(state,**args)


def request_offsets(summary):
    return {name:next(x['offset'] for x in summary['changes'] if x['field']==field and x['after'] is True)
            for name,field in (('match','irq_level'),('flag','irq_flag'),('source','ppu_irq_source'))}


def conditional_request(state):
    require(type(state) is IrqState and state==IrqState(h_counter=186,v_counter=119,h_timer=0,v_timer=211,
        v_enabled=True,irq_enabled_cache=True,nmi_enabled=True),'conditional theorem requires exact modeled v3 seed')
    runs=[]
    for length in (1360,1364):
        result=kernel(state,line_clocks=length).run_until(lambda x:x.state.ppu_irq_source)
        offsets=request_offsets(result)
        expected=(124372,124376,124380) if length==1360 else (124740,124744,124748)
        require(tuple(offsets.values())==expected,'conditional offset regression')
        result['request_offsets']=offsets
        runs.append(result)
    return {'premises':asdict(CONDITIONAL_PREMISES),
        'premises_are_runtime_certificates':False,
        'fixed_registers_cover':'all CPU, DMA/HDMA, debugger, external and state-load routes',
        'additional_requirements':['exact initial v3 seed',
            'no earlier pending/source state or unknown IRQ source',
            'no counter-changing reentry beyond pinned midline DRAM refresh',
            'ordinary source raster; no wrap before V211; minimum line1360',
            'no intervening TIMEUP acknowledgment; no reset/load/clock replacement'],
        'lower_offset_derivation':'(211-119)*1360-754+6; then +4 and +8. Refresh only occupies H532..578; H6/H10/H14 are unique under these premises.',
        'stronger_ordinary_line_derivation':'(211-119)*1364-754+6; then +4 and +8. Short line240 is not reached.',
        'scenarios':runs,'game_deadline':None,'game_helper_admitted':False}


def adversaries(state):
    pending=[]
    for need,flag in ((1,False),(1,True),(2,False),(3,False),(255,False)):
        result=kernel(replace(state,need_irq=need,irq_flag=flag)).run_until(lambda x:x.state.ppu_irq_source)
        source=next(x['offset'] for x in result['changes'] if x['field']=='ppu_irq_source' and x['after'])
        pending.append({'initial_need':need,'initial_flag':flag,'first_source_offset':source})
    require([x['first_source_offset'] for x in pending]==[124748,4,8,12,1020],'pending regression')
    refresh=[]
    for h in (532,534,536,538):
        m=kernel(replace(state,h_counter=0),clock=10+(538-h),hclock=10,
                 next_event='refresh',next_event_h=h)
        r=m.run_until(lambda x:x.hclock>=754,max_clocks=800)
        require(r['counter_h']==186,'equal refresh endpoint')
        refresh.append({'refresh_h':h,'final_h':r['counter_h'],
            'counter_calls':r['irq_counter_calls'],'distinct_tick_clocks':r['distinct_tick_clocks'],
            'tick_ledger_sha256':r['tick_ledger_sha256'],
            'at_event':[list(t) for t in m.ticks if h-4<=t[2]<=h+44]})
    same=kernel(replace(state,h_counter=131,h_timer=140,h_enabled=True,v_enabled=False),
        clock=534,hclock=534,next_event='refresh',next_event_h=538)
    same_result=same.run_until(lambda x:x.state.ppu_irq_source,max_clocks=80)
    require(request_offsets(same_result)=={'match':40,'flag':44,'source':44},'same-clock flag/source')
    nested=kernel(state,callbacks=tuple(NestedEvent(line,0,6) for line in range(120,166)))
    nested_result=nested.run_until(lambda x:x.state.ppu_irq_source)
    require(nested_result['line']==165 and request_offsets(nested_result)=={'match':61996,'flag':62000,'source':62004},
            'synthetic repeated-H6 callback counterexample')
    h10=kernel(state,callbacks=(NestedEvent(211,0,10),))
    h10_result=h10.run_until(lambda x:x.state.ppu_irq_source)
    require(request_offsets(h10_result)=={'match':124740,'flag':124744,'source':124744},'synthetic same-H10 source collapse')
    return {'pending':pending,'refresh_endpoint_scenarios':refresh,
        'horizontal_match_near_refresh':same_result,
        'unclosed_line_callback_counterexample':nested_result,
        'unclosed_h10_callback_counterexample':h10_result,
        'line_callback_is_observed_native_behavior':False}


def finite_pending():
    digest=hashlib.sha256(); count=0
    for need,flag,source,he,ve,cache,level in product(range(256),(False,True),(False,True),
            (False,True),(False,True),(False,True),(False,True)):
        state=IrqState(need_irq=need,irq_flag=flag,ppu_irq_source=source,
            h_enabled=he,v_enabled=ve,irq_enabled_cache=cache,irq_level=level,
            h_counter=2,v_counter=3,h_timer=511,v_timer=511)
        result=process_irq_counters(state,TickContext(14,119,225,False))
        digest.update(serial({'in':asdict(state),'out':asdict(result.state),
            'events':[asdict(e) for e in result.events]}))
        count+=1
    require(count==16384,'complete declared pending equivalence product')
    return {'cases':count,'ordered_projection_sha256':digest.hexdigest(),
        'scope':'all uint8 pending x flag/source/register-enables/cached-enable/level booleans at fixed H14 with unequal timer/counter values, including vacuous matches in incoherent enable-cache states; not all reachable emulator states'}


def cpu_examples():
    def decide(s):return instruction_boundary(s,callbacks_closed=True).selected
    source=CpuGateState(irq_source=PPU_IRQ)
    sampled=sample_cpu_cycle(source,dma_irq_lock=False,callbacks_closed=True)
    r={'source_before_sample':decide(source),'sampled':decide(sampled),
       'sample_then_sei':decide(set_interrupt_disable(sampled,True)),
       'sample_then_source_clear':decide(clear_irq_source(sampled,PPU_IRQ)),
       'dma_lock':decide(sample_cpu_cycle(source,dma_irq_lock=True,callbacks_closed=True)),
       'nmi_priority':decide(replace(sampled,need_nmi=True)),
       'handler_entry_proved':False,'selection_master_clock':None}
    require(list(r.values())[:6]==['none','irq','irq','irq','none','nmi'],'CPU selection examples')
    return r


def collect():
    phase_id=identity(*PHASE_PIN)
    upstream_id=identity(*UPSTREAM_PIN)
    manifest=json.loads((ROOT/UPSTREAM_PIN[0]).read_bytes())
    require(manifest['schema']=='project-epoch-irq-transition-upstream-sources-v1'
            and manifest['revision']==REVISION and len(manifest['sources'])==14,'source manifest')
    sources=[]
    for x in manifest['sources']:
        item=identity(x['path'],x['size_bytes'],x['sha256'])
        raw=(ROOT/x['path']).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(blob==x['git_blob_sha1'],'source Git blob identity')
        sources.append(item)
    originals=[identity(x) for x in ORIGINAL_FILES]
    for x in ORIGINAL_FILES:
        require(b'\r' not in (ROOT/x).read_bytes(),'original source must be LF: '+x)
    reference=json.loads((ROOT/PHASE_PIN[0]).read_bytes())
    row,state=observed_seed(reference)
    by_name={Path(x['path']).name:x for x in manifest['sources']}
    spans=[]
    for name,first,last,role in SPANS:
        x=by_name[name];lines=(ROOT/x['path']).read_bytes().splitlines(keepends=True)
        require(1<=first<=last<=len(lines),'source span')
        spans.append({'source':x['upstream_path'],'first_line':first,'last_line':last,'role':role,
            'sha256':hashlib.sha256(b''.join(lines[first-1:last])).hexdigest(),
            'url':f'https://github.com/SourMesen/Mesen2/blob/{REVISION}/{x["upstream_path"]}#L{first}-L{last}'})
    return {'schema':'project-epoch-irq-request-transition-v1','evidence_level':'source-conditional-host-model',
        'source_commit':REVISION,'phase_reference':phase_id,'upstream_reference':upstream_id,
        'source_identities':sources,'original_source_identities':originals,'source_spans':spans,
        'observed_seed':row,'cache_enable_bootstrap':'irq_enabled_cache derived from register enables under valid-source-state premise; no hidden-field observation',
        'unused_core_field':'auto_joy_enabled defaults false in this projection; it is not asserted observed and no NMITIMEN write is performed',
        'request_model':conditional_request(state),'adversaries':adversaries(state),
        'pending_census':finite_pending(),'cpu_gate_examples':cpu_examples(),
        'native_pair_reexecuted':False,'raw_game_data_emitted':False,
        'game_deadline_certified':False,'cpu_acceptance_deadline_certified':False,
        'handler_entry_proved':False,'production_approval':False,
        'open_gates':['DMA/HDMA source-read and reverse-write isolation',
            'debugger/PPU/render/control/SPC/coprocessor callback closure',
            'cache/bootstrap and runtime fixed-register/reset premises',
            'wrapper cost, physical stack ownership and game interrupt policy',
            'pre-effect refusal lifecycle and later resolver completion'],
        'reproduce':['python -B -m unittest discover -s tests -p "test*schala_irq*v1.py"',
            'python -B tools/audit_schala_irq_request_transition_v1.py --output private/test_runs/UNIQUE_irq_request_v1.json',
            'Compare exact output bytes to references/schala_irq_request_transition_v1.json; upstream sources are recoverable by exact URLs.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=collect()
    # Refuse overwrite, including any predecessor packet or accepted reference.
    with args.output.open('xb') as f:f.write(serial(result))
    print(json.dumps({'output':str(args.output),'sha256':hashlib.sha256(serial(result)).hexdigest(),
        'evidence_level':result['evidence_level'],'game_deadline_certified':False}))


if __name__=='__main__':main()
