"""Build the fixed private PC07 native save-transition diagnostic.

Default: in-memory plan with shared intent and complete-diff audits. Emission
requires the exact current reviewed source bundle, a fresh private destination
and matching fresh assembly of the existing original helpers. No ROM is passed
to Asar. This builder does not launch an emulator or claim native execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_original_snes_package_cartridge_v1 as assembler
import pc07_native_save_transition_write_contract_v1 as contract
import validate_rom_write_intents as guard

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-epoch-private-pc07-native-save-transition-build-v1'


def bundle():
    spec = contract.reference()
    names = [row['path'] for row in spec['sources']] + [
        'tools/build_pc07_native_save_transition_diagnostic_v1.py',
        'tools/pc07_native_save_transition_write_contract_v1.py',
        'tools/validate_rom_write_intents.py',
        'references/pc07_native_save_transition_private_contract_v1.json',
    ]
    sources = []
    for name in sorted(set(names)):
        data = (ROOT/name).read_bytes()
        sources.append({'path': name, 'bytes': len(data), 'sha256': contract.sha(data)})
    return {'sources': sources,
            'sha256': contract.sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode())}


def build(output):
    identity = bundle()
    canonical = contract.read_checked(
        ROOT/'private/input/rom_archive/Chrono Trigger (USA).sfc', 0x400000,
        '06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9')
    source, target, spec = contract.recipe(canonical)
    manifest = contract.build_manifest(source, target, output)
    intent = guard.validate_pc07_native_save_transition_manifest(manifest)
    audit = guard.audit_pc07_native_save_transition_images(manifest, source, target)
    if (intent['status'] != 'metadata-valid' or audit['status'] != 'images-valid'
            or not audit['complete_diff_coverage'] or bundle() != identity
            or guard.APPROVED_PRODUCTION_ALLOCATIONS or guard.APPROVED_PRODUCTION_HOOKS):
        raise ValueError('shared guard/source/catalog invariant')
    return target, {
        'schema': SCHEMA, 'source_bundle': identity,
        'target_sha256': contract.sha(target), 'target_bytes': len(target),
        'output_path': output, 'manifest': manifest,
        'intent_audit': intent, 'complete_diff_audit': audit,
        'evidence_level': 'verified-static-private-diagnostic',
        'emitted': False, 'native_execution': False, 'production_approval': False,
        'event_preparation_removed_at_runtime': False,
    }


def emit(output, reviewed):
    destination = contract.prior.field.output_path(output)
    if destination.parent.exists():
        raise ValueError('fresh private build directory required')
    image, receipt = build(output)
    if type(reviewed) is not str or receipt['source_bundle']['sha256'] != reviewed:
        raise ValueError('current exact reviewed source bundle required')
    assembler.verify_asar()
    destination.parent.mkdir(parents=True, exist_ok=False)
    assembly = []
    for component in contract.reference()['assembly_components']:
        source = ROOT/component['source']
        wrapper = ('arch 65816\nnorom\norg $000000\n'
                   f'base ${component["cpu_address"]:06X}\nincsrc "{source.as_posix()}"\n')
        data, evidence = assembler.assemble_raw(
            destination.parent, component['id'], wrapper, maximum=component['bytes'])
        if len(data) != component['bytes'] or contract.sha(data) != component['sha256']:
            raise ValueError('fresh original assembly mismatch')
        assembly.append(evidence)
    qualified, current = build(output)
    if qualified != image or current != receipt:
        raise ValueError('image/source drift before emission')
    contract.prior.field.output_path(output)
    assembler.exclusive(destination, image)
    if destination.read_bytes() != image:
        raise ValueError('emitted image readback mismatch')
    receipt.update(
        emitted=True, output_path=str(destination), assembly=assembly,
        reproduction=['python', '-B', 'tools/build_pc07_native_save_transition_diagnostic_v1.py',
                      '--output', output, '--emit-reviewed-bundle', reviewed])
    assembler.exclusive(destination.parent/'build_receipt.json',
                        (json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode())
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--emit-reviewed-bundle')
    args = parser.parse_args()
    report = (emit(args.output, args.emit_reviewed_bundle)
              if args.emit_reviewed_bundle is not None else build(args.output)[1])
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
