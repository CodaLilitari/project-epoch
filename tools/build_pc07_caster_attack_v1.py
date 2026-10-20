"""Emit the fixed private caster candidate after both shared write guards.

Asar sees only original-source component bins. No historical recipes run;
one current ROM snapshot and its immediate receipt bind the accepted parent.
"""
from pathlib import Path
import argparse,json
import pc07_caster_attack_write_contract_v1 as contract
import validate_rom_write_intents as guard

def build(output):
    output=Path(output).absolute();relative=(output/'diagnostic.sfc').relative_to(contract.ROOT).as_posix()
    contract.output_path(relative);contract.need(not output.exists(),'fresh private output directory required')
    with contract.source_snapshot(output/'assembly')as snap:
        manifest=contract.template(relative)
        intent=guard.validate_pc07_caster_attack_manifest(manifest)
        diff=guard.audit_pc07_caster_attack_images(manifest,snap['source'],snap['target'])
        contract.need(intent['status']=='metadata-valid' and diff['status']=='images-valid'
                      and diff['complete_diff_coverage'] is True,'both shared guards required before emission')
        contract.need(not guard.APPROVED_PRODUCTION_ALLOCATIONS and not guard.APPROVED_PRODUCTION_HOOKS,'production catalogs stay empty')
        names=('tools/build_pc07_caster_attack_v1.py','tools/pc07_caster_attack_write_contract_v1.py',
               'tools/pc07_caster_attack_helper_encoding_v1.py','tools/native_pc07_caster_pose_codec_v1.py',
               'tools/native_pc07_pose_codec_v1.py','tools/native_pc07_pose_mirror_v1.py',
               'tools/pc07_run_pose_write_contract_v1.py','tools/validate_rom_write_intents.py')
        sources=[contract.identity(name,contract.resolve(name).read_bytes())for name in names]+snap['assembly']['source_inputs']
        receipt={'schema':'project-epoch-private-pc07-caster-attack-build-v1','emitted':True,'source':contract.SOURCE,
                 'target':manifest['target'],'manifest':manifest,'implementation_inputs':sources,
                 'current_shared_intent':intent,'current_shared_diff':diff,'art_encoding':snap['art'],'assembly':snap['assembly'],
                 'evidence_level':'guarded-private-static-stationary-caster-candidate','native_execution':False,
                 'production_approval':False,'single_source_snapshot':True,'historical_builders_or_validators_executed':False,
                 'limits':['Qualified Attack consumers are slot2 PC07 only; this is not a universal character implementation.',
                           'Front/down and horizontal casting art are bound; back-facing art remains unchanged.',
                           'All-range stationary behavior, projectile appearance, sound, result application and completion require native observation.',
                           'No impact-sound hook is installed; rooted selected packages have no command7D invocation.'],
                 'reproduction':'python -B tools/build_pc07_caster_attack_v1.py --output private/test_runs/pc07_caster_attack_<fresh-name>'}
        for name,raw in (('write_intents.json',contract.encoded(manifest)),('diagnostic.sfc',snap['target']),('receipt.json',contract.encoded(receipt))):
            path=contract.resolve((output/name).relative_to(contract.ROOT).as_posix())
            with path.open('xb')as stream:stream.write(raw)
    return receipt

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    result=build(args.output)
    print(json.dumps({'status':'guarded-private-image-emitted','output':str(args.output),'target':result['target'],
                      'diff':result['current_shared_diff']}))
