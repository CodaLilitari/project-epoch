"""Extend the accepted occupied-span metadata for one private caster candidate.

No ROM input or historical builder execution. Retain every accepted span and
the entire reserved KO helper allocation, including its still-FF padding.
"""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
PINS=(
    {'path':'private/research/pc07_battle_pose_20261020/engineering/allocation_census_v1.json','bytes':19929,
     'sha256':'bbb17c2644b585329290965ffd4f8dc63b353bf47c116eb8e80574840a0487f9'},
    {'path':'private/test_runs/pc07_battle_pose_v1/receipt.json','bytes':37601,
     'sha256':'4cc9afaaacffd89c2177fe6bd632c885f74ae88381943b2d774e0a00c86e1f69'},
)
CURRENT={'path':'private/test_runs/pc07_battle_pose_v1/diagnostic.sfc','bytes':0x800000,
         'sha256':'7549c49c3fec255ea559e8b1e0420a7b6285d921948f9550308291270db470e5'}
NEW=(('pc07-caster-front-graphics-append',0x420E00,0x420F40),
     ('pc07-caster-front-assembly-append',0x4214B0,0x421500),
     ('pc07-caster-attack-helpers',0x490100,0x490380))

def need(test,message):
    if not test:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read_pin(row):
    raw=(ROOT/row['path']).read_bytes()
    need(len(raw)==row['bytes'] and sha(raw)==row['sha256'],'pinned accepted metadata drift')
    return json.loads(raw)

def derive():
    census,parent=[read_pin(row)for row in PINS]
    need(parent['emitted'] is True and parent['target']=={k:CURRENT[k]for k in ('bytes','sha256')}
         and parent['manifest']['output']==CURRENT['path'],'immediate current-parent binding')
    need(parent['current_shared_diff']['complete_diff_coverage'] is True
         and parent['current_shared_diff']['status']=='images-valid'
         and parent['current_shared_intent']['status']=='metadata-valid','accepted current construction')
    need(parent['manifest']['named_allocation_provenance']['accepted_census']==PINS[0],'accepted prior census binding')
    fill=census['inherited_expanded_fill']
    need(fill=={'start':0x410000,'end':0x7E0000,'fill':255} and census['FF_alone_is_authority'] is False,'scaffold provenance')
    occupied=list(census['occupied_spans'])
    for prefix,rows in (('battle-v1',parent['manifest']['sections']),
                        ('battle-reservation',parent['manifest']['named_allocation_provenance']['new_allocations'])):
        for index,row in enumerate(rows):
            start,size=row['file_start'],row['bytes']
            need(type(start)is int and type(size)is int and 0<=start<start+size<=0x800000,'occupied bounds')
            occupied.append({'id':f'{prefix}:{index}:{row["id"]}','file_start':start,'bytes':size,'file_end_exclusive':start+size})
    need(len(occupied)==143,'117 inherited plus23 battle spans plus3 complete reservations')
    proposed=[]
    for name,start,end in NEW:
        need(fill['start']<=start<end<=fill['end'],'expanded reservation bounds')
        overlap=[row['id']for row in occupied if start<row['file_end_exclusive'] and row['file_start']<end]
        need(not overlap,'new reservation overlaps accepted ownership')
        proposed.append({'id':name,'file_start':start,'bytes':end-start,'file_end_exclusive':end,'overlapping_occupied_ids':overlap})
    return {'schema':'epoch-private-caster-attack-allocation-census-v1','sources':list(PINS),'current_parent':CURRENT,
            'inherited_expanded_fill':fill,'inert_scaffold_sha256':census['inert_scaffold_sha256'],
            'occupied_spans':sorted(occupied,key=lambda row:(row['file_start'],row['id'])),'new_allocations':proposed,
            'new_allocations_disjoint':True,'FF_alone_is_authority':False,'whole_previous_KO_reservation_preserved':True,
            'evidence_level':'accepted-placement-metadata-reuse-with-explicit-interval-comparison',
            'ROM_read':False,'ROM_written':False,'historical_builders_or_validators_executed':False,'production_approval':False,
            'reproduction':'python -B tools/build_pc07_caster_attack_allocation_census_v1.py <fresh-output.json>'}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output',type=Path);args=ap.parse_args()
    value=derive();raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb')as stream:stream.write(raw)
    print(json.dumps({'path':str(args.output),'bytes':len(raw),'sha256':sha(raw),'occupied_records':len(value['occupied_spans'])}))
