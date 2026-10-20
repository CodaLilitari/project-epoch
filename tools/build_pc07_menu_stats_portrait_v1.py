"""Emit one guarded private menu-stats and portrait revision."""
from pathlib import Path
import argparse
import json
import pc07_menu_stats_portrait_write_contract_v1 as contract
import validate_rom_write_intents as guard

def build(output):
    output=Path(output).absolute()
    relative=(output/'diagnostic.sfc').relative_to(contract.ROOT).as_posix()
    contract.output_path(relative); contract.need(not output.exists(),'fresh output directory')
    with contract.source_snapshot(output/'assembly') as snap:
        manifest=contract.template(relative)
        intent=guard.validate_pc07_menu_stats_portrait_v1_manifest(manifest)
        diff=guard.audit_pc07_menu_stats_portrait_v1_images(manifest,snap['source'],snap['target'])
        contract.need(intent['status']=='metadata-valid' and diff['status']=='images-valid' and diff['complete_diff_coverage'] is True,
                      'shared intent and complete-diff guards before emission')
        contract.need(not guard.APPROVED_PRODUCTION_HOOKS and not guard.APPROVED_PRODUCTION_ALLOCATIONS,'production remains closed')
        names=('tools/build_pc07_menu_stats_portrait_v1.py','tools/pc07_menu_stats_portrait_write_contract_v1.py',
               'tools/native_pc07_menu_stats_helper_v1.py','tools/native_pc07_status_portrait_codec_v1.py',
               'asm/pc07_menu_stats_v1.asm','tools/pc07_run_pose_write_contract_v1.py','tools/validate_rom_write_intents.py')
        receipt={'schema':'project-epoch-private-pc07-menu-stats-portrait-build-v1','emitted':True,
                 'source':contract.SOURCE,'target':manifest['target'],'manifest':manifest,
                 'implementation_inputs':[contract.identity(n,contract.resolve(n).read_bytes()) for n in names],
                 'current_shared_intent':intent,'current_shared_diff':diff,'assembly':snap['assembly'],
                 'evidence_level':manifest['evidence_level'],'native_execution':False,'production_approval':False,
                 'single_source_snapshot':True,'historical_builders_or_validators_executed':False,
                 'limits':['Native initial menu and safe-empty controls remain required.',
                           'Base balance, growth, equipment IDs, spell damage and save layout are unchanged.',
                           'Whole-game stack and interrupt ownership are not established by this local gate.',
                           'Art likeness remains a visual judgment separate from its byte-exact native conversion.'],
                 'reproduction':'python -B tools/build_pc07_menu_stats_portrait_v1.py --output private/test_runs/pc07_menu_stats_portrait_<fresh-name>'}
        for name,raw in (('write_intents.json',contract.encoded(manifest)),('diagnostic.sfc',snap['target']),('receipt.json',contract.encoded(receipt))):
            with contract.resolve((output/name).relative_to(contract.ROOT).as_posix()).open('xb') as stream: stream.write(raw)
    return receipt
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); result=build(args.output)
    print(json.dumps({'status':'guarded-private-image-emitted','target':result['target'],'diff':result['current_shared_diff']}))
