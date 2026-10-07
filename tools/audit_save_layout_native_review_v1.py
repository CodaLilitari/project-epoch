"""Additive checks prompted by the completed Claude Code source review.

Preserves every accepted source and native run. This is read-only revalidation
of the fixed translated stream and observed global metadata publications.
It neither reruns the emulator nor approves a new layout or production hook.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import schala_save_layout_native_v1 as c
import schala_save_layout as layout
import revalidate_save_layout_native_chain_v1 as chain

def physical_stream(regions):
    result=[]
    for r in regions:
        c.require(r.bank in (0,0x7E,0x7F), 'unsupported stream bank')
        end=r.address+r.length
        c.require(r.length>0 and 0<=r.address<end<=0x10000, 'stream extent')
        c.require(r.bank!=0 or end<=0x2000, 'bank00 outside low WRAM mirror')
        result.extend(range(r.address+(0x10000 if r.bank==0x7F else 0),end+(0x10000 if r.bank==0x7F else 0)))
    return result

def check_stream(translated=layout.PROJECT_EPOCH_REGIONS, vanilla=layout.VANILLA_REGIONS):
    proposed,old=physical_stream(translated),physical_stream(vanilla)
    c.require(len(proposed)==len(old)==0x834 and len(set(proposed))==len(proposed), 'physical stream overlap/size')
    c.require(old[0x430:0x480]==list(range(0x2830,0x2880)), 'canonical compatibility slot offset')
    normalized=[a-0x470 if 0x2CA0<=a<0x2CF0 else a for a in proposed]
    c.require(normalized==old, 'translated stream not byte-position-equivalent to vanilla')
    return {'serialized_bytes':len(old),'unique_physical_bytes':len(set(proposed)),
            'canonical_offset':0x430,'canonical_length':80,'ordered_physical_equivalence':True,
            'translated_physical_stream_sha256':hashlib.sha256(b''.join(a.to_bytes(3,'little') for a in proposed)).hexdigest()}

def check_metadata(records,snapshots,mode,slot):
    bus=[r for r in records if r['kind']=='bus']
    global_writes=[r for r in bus if r['space']=='sram' and r['op']=='write' and r['address'] in (0x1FE0,0x1FE1)]
    before=snapshots['entry'][1][0x1FE0:0x1FE2]
    after=snapshots['terminal'][1][0x1FE0:0x1FE2]
    if mode=='load':
        c.require(not global_writes and after==before, 'load changed global metadata')
        return {'before_hex':before.hex(),'after_hex':after.hex(),'writes':0}
    counter_reads=[r for r in bus if (r['space'],r['op'],r['pc'],r['address'])==('sram','read',0xFFFA6B,0x1FE1)]
    compare_reads=[r for r in bus if (r['space'],r['op'],r['pc'],r['address'])==('wram','read',0xFFFA6F,0x299E)]
    c.require(len(counter_reads)==len(compare_reads)==1, 'native counter comparison observations')
    counter=counter_reads[0]['value']
    c.require(counter==before[1], 'global counter changed before native read')
    increment=counter==compare_reads[0]['value']
    expected=[(0xFFFA67,0x1FE0,slot)]
    if increment: expected.append((0xFFFA75,0x1FE1,(counter+1)&255))
    c.require([(r['pc'],r['address'],r['value']) for r in global_writes]==expected,
              'global metadata value/context/count differs from source')
    restored=next(i for i,r in enumerate(records) if r['kind']=='snapshot' and r['name']=='restored')
    c.require(all(i>restored for i,r in enumerate(records) if r in global_writes), 'metadata publication before restoration')
    c.require(after==bytes((slot,(counter+1)&255 if increment else counter)), 'terminal global metadata')
    base=slot*0xA00
    c.require(snapshots['terminal'][1][base+0x430:base+0x480]==snapshots['entry'][0][0x2830:0x2880],
              'saved compatibility at wrong canonical slot offset')
    comparisons=[r['cpu']['a'] for r in records if r['kind']=='exec' and r['pc']==c.MODES['save']['cmp']]
    c.require(comparisons==list(range(5,51,5)), 'late/additional comparison outside ten-loop witness')
    return {'before_hex':before.hex(),'after_hex':after.hex(),'writes':len(global_writes),
            'active_slot_publication':slot,'counter_increment':increment,
            'comparison_value':compare_reads[0]['value'],'source_contexts_checked':True}

def audit():
    ref=chain.read_reference(chain.REFERENCE.read_bytes())
    captured=chain.capture_artifacts(ref)
    chain.revalidate(ref,captured)
    c.source_contract(captured['private/input/rom_archive/Chrono Trigger (USA).sfc'])
    result={'schema':'project-epoch-native-save-layout-review-addendum-v1',
            'evidence_level':'read-only-revalidation-of-verified-runtime-instrumented-chain',
            'chain_reference_sha256':chain.REFERENCE_SHA256,'native_bundle_sha256':chain.NATIVE_BUNDLE_SHA256,
            'claude_answer_sha256':'85ef62a4780de6061388110d14f3a7f803ab632fb84de6abf2bad079a7700edd',
            'stream':check_stream(),'runs':{},'native_execution':False,'image_emitted':False,
            'limitations':['The external reviewer did not receive five bundle dependencies; local checks supply these particular omitted checks, not blanket external approval.',
                           'Only the actual slot0 runs are revalidated; no slot1/2 native coverage is added.',
                           'Evidence still ends before RTL. Post-failure/post-stop execution and battery files remain undefined/excluded.',
                           'DMA callbacks are a source/runtime premise; last CPU exec context is not proof of DMA ownership.',
                           'The old generic host overlap limitation and frozen native validator remain unchanged. This additive audit enforces physical ordered equivalence separately.']}
    for mode,dirs in chain.RUNS.items():
        for name in dirs:
            prefix=chain.BASE+name+'/trace'
            rows=[json.loads(line) for line in captured[prefix+'.jsonl'].splitlines()]
            snapshots={label:(captured[prefix+'.'+label+'.wram.bin'],captured[prefix+'.'+label+'.sram.bin'])
                       for label in ('entry','prepared','table','copy_complete','restored','terminal')}
            result['runs'][name]=check_metadata(rows,snapshots,mode,0)
    chain.recheck_artifacts(ref,captured)
    return result

if __name__=='__main__': print(json.dumps(audit(),indent=2,sort_keys=True))
