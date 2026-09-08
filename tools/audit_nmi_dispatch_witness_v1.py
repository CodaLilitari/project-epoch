"""Metadata-only reuse of accepted native NMI dispatch register snapshots.

Full accepted context evidence is revalidated before this bounded projection.
Computed table targets are static recipes, not observed pointer bus reads.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys
import collect_package_resolver_context_evidence_v1 as context
import audit_schala_nmi_mode_inputs_v1 as mode
import audit_schala_scene_dispatch_inputs_v1 as scene

ROOT=Path(__file__).resolve().parents[1]
PINS={
 'context_reference':('references/package_resolver_context_v1.json','d7eb845a97f1398996ff28936b0117a423b6534aa1d518fbf49023e28317fd99'),
 'context_collector':('tools/collect_package_resolver_context_evidence_v1.py','c68696d1a0d050dbbbea833299a1ed959d53d68ffaae992c600cd968a3b1532b'),
 'mode_reference':('references/schala_nmi_mode_inputs_v1.json','dc715f6726e482a00e649d15252b5ca42f933f82198d8520c78d7867f3932530'),
 'mode_auditor':('tools/audit_schala_nmi_mode_inputs_v1.py','2372dd5c829f889ca0069227d1d4322726ce2c893c4e55cdf1471a3f0f28614f'),
 'scene_reference':('references/schala_scene_dispatch_inputs_v1.json','d5604c65934dff1dfa4796ea3d990e227065e9b28a5499695f590fff912a8c13'),
 'scene_auditor':('tools/audit_schala_scene_dispatch_inputs_v1.py','3aef357ad9c557d21015711e834d37a370737228665cca4c2ece4745a71f4d30'),
}


def require(test,message):
    if not test:raise ValueError(message)


def serial(value):return (json.dumps(value,indent=2)+'\n').encode('utf-8')
def compact(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()


def identity(path,expected=None):
    raw=path.read_bytes();digest=sha(raw)
    require(expected is None or digest==expected,'source identity drift: '+path.name)
    return {'path':path.relative_to(ROOT).as_posix(),'size':len(raw),'sha256':digest}


def exact_int(value,low,high,name):require(type(value) is int and low<=value<=high,'exact '+name)


def project_validated_records(records,mode_cells,scene_cells):
    """Selected-field projection; caller must first run the full context proof.

    This function still rejects malformed selected CPU/context/stack fields.
    Original host tests can exercise it with abbreviated records; they do not
    turn those specimens into accepted context traces.
    """
    require(type(records) is list,'record list')
    entries={};exits={};modes={};scenes=defaultdict(list);selected=[]
    kinds={'interrupt-entry','interrupt-rti','nmi-mode-dispatch','nmi-scene-dispatch'}
    for ordinal,r in enumerate(records):
        require(type(r) is dict,'record object')
        if r.get('kind') not in kinds or r.get('context_kind')!='normal-nmi':continue
        cid=r.get('context_id');exact_int(cid,1,1000000,'context ID')
        require(type(r.get('context_depth')) is int and r['context_depth']==1,'normal-NMI context depth')
        cpu=r.get('cpu');require(type(cpu) is dict and set(cpu)=={'a','x','y','d','dbr','sp','ps','k','pc','emulationMode'},'selected CPU schema')
        require(cpu['emulationMode'] is False,'native CPU required')
        for key,value in cpu.items():
            if key!='emulationMode':exact_int(value,0,255 if key in ('ps','k','dbr') else 65535,'CPU '+key)
        exact_int(r.get('address'),0,0xFFFFFF,'record address')
        require(r['address']==(cpu['k']<<16)|cpu['pc'],'selected PC consistency')
        require(type(r.get('stack')) is list and len(r['stack'])==12,'selected stack extent')
        for value in r['stack']:exact_int(value,0,255,'stack byte')
        require(type(r.get('wram')) is dict,'selected WRAM object')
        for key in ('007E','007F'):exact_int(r['wram'].get(key),0,255,'WRAM '+key)
        require(type(r.get('timing')) is dict,'selected timing object')
        for key in ('memoryManager.masterClock','cpu.cycleCount','ppu.frameCount'):exact_int(r['timing'].get(key),0,2**64-1,'timing '+key)
        selected.append(ordinal)
        destination={'interrupt-entry':entries,'interrupt-rti':exits,'nmi-mode-dispatch':modes}.get(r['kind'])
        if destination is not None:
            require(cid not in destination,'duplicate selected context boundary');destination[cid]=(ordinal,r)
        else:scenes[cid].append((ordinal,r))
    require(entries and set(entries)==set(exits)==set(modes) and set(scenes)<=set(entries),'complete one-mode-per-NMI paired topology')
    mode_rows=[];scene_rows=[];context_rows=[]
    for cid,(entry_i,e) in sorted(entries.items()):
        exit_i,z=exits[cid];mode_i,m=modes[cid]
        require(entry_i<mode_i<exit_i,'entry/mode/pre-RTI order')
        require(e['address']==0xD1E77C and z['address']==0xD1E898 and m['address']==0xCD0C99,'exact normal-NMI sites')
        require(all(e['cpu'][key]==z['cpu'][key] for key in ('a','x','y','d','dbr','sp','emulationMode')) and e['stack'][:4]==z['stack'][:4],
            'paired pre-RTI register/stack-frame preservation')
        require(e['wram']['007F']==0 and m['wram']['007F']==1,'busy-zero prefix/active busy snapshots')
        c=m['cpu'];source=e['cpu'];mode_byte=m['wram']['007E']
        require(mode_byte==1 and e['wram']['007E']==1,'bounded witness mode-one input')
        require(c['a']==2 and c['x']==2 and c['y']==0xCC90 and c['d']==0 and c['dbr']==0 and c['ps']&0x34==0x24,'mode register recipe')
        require(source['sp']-c['sp']==12,'nine software saves plus JSL stack delta')
        expected=[0xDD,0xE7,0xD1,source['d']&255,source['d']>>8,source['dbr'],
            source['y']&255,source['y']>>8,source['x']&255,source['x']>>8,source['a']&255,source['a']>>8]
        require(m['stack']==expected,'actual mode snapshot does not match entry saves and pinned JSL return')
        for a,b in ((e,m),(m,z)):
            require(all(a['timing'][key]<b['timing'][key] for key in ('memoryManager.masterClock','cpu.cycleCount')),'strict paired clock/cycle order')
            require(a['timing']['ppu.frameCount']<=b['timing']['ppu.frameCount'],'paired frame reversal')
        cell=mode.index_contract(mode_byte,c['a']>>8)
        pinned=mode_cells[mode_byte]
        require(pinned['mode']==mode_byte and pinned['x']==cell['x'] and pinned['pointer_byte_addresses']==cell['pointer_byte_addresses'],'static mode reference differs')
        mode_rows.append({'context_id':cid,'record_ordinal':mode_i,'entry_ordinal':entry_i,'pre_rti_ordinal':exit_i,
            'mode_byte':mode_byte,'x':c['x'],'a':c['a'],'entry_sp':source['sp'],'mode_sp':c['sp'],
            'snapshot_matches_nine_saved_bytes_and_jsl':True,'static_pointer_byte_addresses':cell['pointer_byte_addresses'],
            'static_selected_target':pinned['target']})
        observed=scenes.get(cid,[])
        for scene_i,s in observed:
            require(mode_i<scene_i<exit_i and s['address']==0xCD16AF,'scene observation detached from containing NMI')
            cpu=s['cpu'];index=cpu['x']
            require(cpu['a']==index and 0<=index<=252 and index%2==0 and cpu['d']==0 and cpu['dbr']==0x7E and cpu['ps']&0x34==0x24,'scene observed index/ABI')
            require(s['wram']['007E']==1 and s['wram']['007F']==1 and source['sp']-cpu['sp']==24,'scene mode/busy/observed stack delta')
            require(all(m['timing'][key]<s['timing'][key]<z['timing'][key] for key in ('memoryManager.masterClock','cpu.cycleCount')),'scene clock/cycle outside parent dispatch/return')
            derived=128+index//2;cell=scene.index_contract(derived,0);pinned=scene_cells[derived-128]
            require(pinned['command']==derived and pinned['x']==index and pinned['pointer_byte_addresses']==cell['pointer_byte_addresses'],'static scene reference differs')
            scene_rows.append({'context_id':cid,'record_ordinal':scene_i,'a':cpu['a'],'x':index,'sp':cpu['sp'],
                'derived_command_byte':derived,'static_pointer_byte_addresses':cell['pointer_byte_addresses'],
                'static_selected_target':pinned['target']})
        context_rows.append({'context_id':cid,'entry_ordinal':entry_i,'mode_ordinal':mode_i,'scene_ordinals':[i for i,_ in observed],
            'pre_rti_ordinal':exit_i,'entry_sp':source['sp'],'pre_rti_sp':z['cpu']['sp']})
    # Lists are hashed in trace order. Aggregates alone never establish which
    # original native records supplied the result.
    mode_rows.sort(key=lambda r:r['record_ordinal']);scene_rows.sort(key=lambda r:r['record_ordinal'])
    histogram=Counter(r['derived_command_byte'] for r in scene_rows)
    return {'normal_nmi_pairs':len(entries),'mode_observations':len(mode_rows),'scene_observations':len(scene_rows),
        'nmi_contexts_with_scene_observations':len(scenes),'scene_derived_command_count':len(histogram),
        'scene_derived_commands':[{'command':f'{command:02X}','count':count} for command,count in sorted(histogram.items())],
        'selected_record_ordinals_sha256':sha(compact(selected)),
        'selected_complete_records_sha256':sha(compact([records[i] for i in selected])),
        'mode_projection_sha256':sha(compact(mode_rows)),'scene_projection_sha256':sha(compact(scene_rows)),
        'context_projection_sha256':sha(compact(context_rows)),
        'mode_entry_stack_deltas':sorted({entries[r['context_id']][1]['cpu']['sp']-r['mode_sp'] for r in mode_rows}),
        'scene_entry_stack_deltas':sorted({entries[r['context_id']][1]['cpu']['sp']-r['sp'] for r in scene_rows}),
        'mode_register_summary':{'a':2,'x':2,'y':0xCC90,'d':0,'dbr':0,'mode_byte':1,'hidden_b':0},
        'mode_all_snapshot_save_frames_match':True,'scene_all_observed_hidden_b_zero':True,
        'mode_static_target':mode_cells[1]['target'],'mode_minimum_observed_sp':min(r['mode_sp'] for r in mode_rows),
        'scene_minimum_observed_sp':min((r['sp'] for r in scene_rows),default=None),
        'context_scene_count_histogram':[{'scene_observations':n,'contexts':count} for n,count in sorted(Counter(len(scenes.get(cid,[])) for cid in entries).items())],
        'target_pointer_bus_reads_observed':False,'scene_command_fetch_bytes_observed':False,
        'complete_legal_input_domains_proved':False,'full_stack_low_water_proved':False,'production_approval':False}


def collect():
    sources={name:identity(ROOT/path,pin) for name,(path,pin) in PINS.items()}
    rebuilt=context.collect()
    require(serial(rebuilt)==(ROOT/PINS['context_reference'][0]).read_bytes(),'full accepted context pair revalidation drift')
    # Regenerate both static references to preserve their current interpreter,
    # canonical bytes and complete pinned dependency chains.
    mode_data=mode.collect();scene_data=scene.collect()
    require(serial(mode_data)==(ROOT/PINS['mode_reference'][0]).read_bytes(),'mode input reference drift')
    require(serial(scene_data)==(ROOT/PINS['scene_reference'][0]).read_bytes(),'scene input reference drift')
    projections=[];run_refs=[]
    for run in rebuilt['runs']:
        path=ROOT/run['trace']['path'];raw=path.read_bytes()
        require(len(raw)==run['trace']['size'] and sha(raw)==context.TRACE_SHA256,'accepted full trace identity changed after validation')
        result=project_validated_records(json.loads(raw)['records'],mode_data['b_zero_mode_cells'],scene_data['b_zero_syntax_cells'])
        require((result['normal_nmi_pairs'],result['mode_observations'],result['scene_observations'],result['nmi_contexts_with_scene_observations'],result['scene_derived_command_count'])==(1201,1201,3097,657,44),'frozen witness count drift')
        projections.append(result);run_refs.append(run)
    require(projections[0]==projections[1],'reused native pair projections differ')
    sources['auditor']=identity(Path(__file__).resolve());sources['tests']=identity(ROOT/'tests/test_nmi_dispatch_witness_v1.py')
    return {'schema':'project-epoch-nmi-dispatch-witness-v1','date':'2026-09-08','evidence_level':'verified-runtime',
        'evidence_scope':'reuse-only register/stack snapshots from the accepted bounded clean-ROM context pair',
        'sources':sources,'revalidated_runs':run_refs,'observations':projections[0],
        'limits':['The complete prior context validator and exact static reference reproduction run before projection.',
            'Entry is after the native hardware frame; 12/24-byte deltas are measured from that recorded SP, not interrupted-main SP.',
            'Each mode stack snapshot matches nine saved entry-register bytes and the pinned JSL return; nonstack alias ownership remains unproved.',
            'All observed mode inputs are 1 and all observed scene indices have B0; no other mode or scene lifetime is covered.',
            'Scene command bytes and targets are reconstructed from canonical local instruction/table recipes, not observed stream or pointer bus reads.',
            '44 derived command values are an observed-context subset, not a complete legal command or script corpus.',
            'Snapshot minima are not full stack low-water measurements, interrupt reserve recommendations or helper preemption evidence.',
            'No native run, ROM mutation, production placement, high-package binding or PC07 integration is added.'],
        'reproduce':['python','-B','tools/audit_nmi_dispatch_witness_v1.py'],'production_approval':False}


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    sys.stdout.buffer.write(serial(collect()))
