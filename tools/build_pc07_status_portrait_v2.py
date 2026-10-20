"""Emit a separately guarded private full-status portrait candidate."""
from pathlib import Path
import argparse
import json
import pc07_status_portrait_write_contract_v2 as contract
import validate_rom_write_intents as guard


def build(output):
    output = Path(output).absolute()
    relative = (output/'diagnostic.sfc').relative_to(contract.ROOT).as_posix()
    contract.output_path(relative)
    contract.need(not output.exists(), 'fresh private output directory required')
    with contract.source_snapshot(output/'assembly') as snap:
        manifest = contract.template(relative)
        intent = guard.validate_pc07_status_portrait_v2_manifest(manifest)
        diff = guard.audit_pc07_status_portrait_v2_images(manifest,snap['source'],snap['target'])
        contract.need(intent['status'] == 'metadata-valid' and diff['status'] == 'images-valid' and
                      diff['complete_diff_coverage'] is True, 'both current shared guards before emission')
        contract.need(not guard.APPROVED_PRODUCTION_ALLOCATIONS and not guard.APPROVED_PRODUCTION_HOOKS,
                      'production catalogs stay empty')
        names = ('tools/build_pc07_status_portrait_v2.py','tools/pc07_status_portrait_write_contract_v2.py',
                 'tools/native_pc07_status_portrait_codec_v1.py','tools/native_pc07_status_portrait_helpers_v2.py',
                 'asm/pc07_status_portrait_v2.asm','tools/pc07_run_pose_write_contract_v1.py','tools/validate_rom_write_intents.py')
        receipt = {'schema':'project-epoch-private-pc07-status-portrait-build-v2','emitted':True,
                   'source':contract.SOURCE,'target':manifest['target'],'manifest':manifest,
                   'implementation_inputs':[contract.identity(name,contract.resolve(name).read_bytes()) for name in names],
                   'current_shared_intent':intent,'current_shared_diff':diff,'art_encoding':snap['art'],
                   'assembly':snap['assembly'],'evidence_level':manifest['evidence_level'],
                   'native_execution':False,'production_approval':False,'single_source_snapshot':True,
                   'historical_builders_or_validators_executed':False,
                   'limits':['Dedicated menu portrait graphics are preloaded once; status consumer and names are qualified.',
                             'Native PC07/Crono roundtrip and other six controls remain required.',
                             'Save-preview PC07 handling and Epoch naming consumer stay unchanged.',
                             'No new physical stack, interrupt, DMA timing or full-game ownership proof.'],
                   'reproduction':'python -B tools/build_pc07_status_portrait_v2.py --output private/test_runs/pc07_status_portrait_<fresh-name>'}
        for name,raw in (('write_intents.json',contract.encoded(manifest)),('diagnostic.sfc',snap['target']),
                         ('receipt.json',contract.encoded(receipt))):
            with contract.resolve((output/name).relative_to(contract.ROOT).as_posix()).open('xb') as stream:
                stream.write(raw)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps({'status':'guarded-private-image-emitted','output':str(args.output),
                      'target':result['target'],'diff':result['current_shared_diff']}))
