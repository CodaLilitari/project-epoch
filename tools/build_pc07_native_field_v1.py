"""Build one guarded private ExHiROM field-helper diagnostic from source.

Default is an in-memory plan. Only --emit-reviewed-bundle writes a game image,
after the distinct intent and complete-diff APIs in the shared guard pass.
This does not approve a production allocation or an eighth playable character.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import build_original_snes_package_cartridge_v1 as assembler
import pc07_private_expanded_write_contract_v1 as contract
import schala_compat_menu_v1 as compatibility
import schala_rom_scaffold as scaffold
import validate_rom_write_intents as guard

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-epoch-native-field-diagnostic-build-v1'
ASM = ROOT / 'asm/pc07_donor_read_adapters_v2.asm'
ASM_SHA = 'df0584a820d3b6b4994298cc1f0d6b3ffc4089797b42c5d6c6217d02a4e5a914'
COMPONENT = ROOT / 'private/test_runs/pc07_donor_native_source_v2/adapters.bin'
COMPONENT_SHA = '315f409ece80e84c656930c47bc5a0d6e0f97d83aecc95b7c474abc2056750e7'
REVIEW = ROOT / 'private/test_runs/pc07_donor_native_source_v2/source_review.json'
REVIEW_SHA = '5b1ea5cff78b79f2f1a12a008e6731873eb20adb9535012bf482f540e484c7ca'
HOOK = bytes.fromhex('22000041eaea')
PREIMAGE = bytes.fromhex('8d0242c8a905')
PINNED = {
    'asm/pc07_donor_read_adapters_v2.asm': ASM_SHA,
    REVIEW.relative_to(ROOT).as_posix(): REVIEW_SHA,
    'tools/schala_compat_menu_v1.py': '4b679c79791a8d2ec879f2f9e1e5ad5b46bb4655f59c7d00d217cc3613c35f59',
    'tools/schala_rom_scaffold.py': 'a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a',
}
SOURCES = (*PINNED, 'tools/build_pc07_native_field_v1.py',
           'tools/pc07_private_expanded_write_contract_v1.py',
           'tools/validate_rom_write_intents.py',
           'tools/build_original_snes_package_cartridge_v1.py',
           'tools/original_snes_diagnostic_write_contract_v1.py',
           'tools/original_snes_package_fixtures_v1.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bundle():
    for name, expected in PINNED.items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError('pinned source drift: ' + name)
    rows = [{'path': name, 'bytes': (ROOT / name).stat().st_size,
             'sha256': sha((ROOT / name).read_bytes())} for name in SOURCES]
    return {'sha256': sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()),
            'sources': rows}


def component():
    data = COMPONENT.read_bytes()
    if len(data) != 157 or sha(data) != COMPONENT_SHA or sha(ASM.read_bytes()) != ASM_SHA:
        raise ValueError('reviewed component/source identity mismatch')
    return data


def build_image(canonical: bytes, helper: bytes, destination: Path):
    """Construct in memory, then run both shared fail-closed audit entrypoints."""
    before = bundle()
    if type(helper) is not bytes or len(helper) != 157 or sha(helper) != COMPONENT_SHA:
        raise ValueError('exact original helper component required')
    source = scaffold.expand_exhirom_scaffold(canonical)
    scaffold.validate_exhirom_scaffold(source, source=canonical)
    if sha(source) != scaffold.EXPECTED_INERT_SCAFFOLD_SHA256:
        raise ValueError('inert scaffold identity')
    target = bytearray(source)
    for start, old, new in compatibility.PATCHES:
        if target[start:start + len(old)] != old:
            raise ValueError('compatibility instruction preimage')
        target[start:start + len(new)] = new
    for start in (0x448D, 0x40448D):
        if target[start:start + 6] != PREIMAGE:
            raise ValueError('field instruction/mirror preimage')
        target[start:start + 6] = HOOK
    if target[0x410000:0x410000 + len(helper)] != b'\xff' * len(helper):
        raise ValueError('expanded helper preimage')
    target[0x410000:0x410000 + len(helper)] = helper
    # Each already valid complement/checksum pair contributes exactly 0x1FE.
    checksum = sum(target) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, 'little') + checksum.to_bytes(2, 'little')
    for start in (0xFFDC, 0x40FFDC):
        target[start:start + 4] = pair
    target = bytes(target)
    relative = destination.relative_to(ROOT).as_posix()
    manifest = contract.build_manifest(source, target, relative)
    intent = guard.validate_pc07_private_expanded_manifest(manifest)
    audit = guard.audit_pc07_private_expanded_images(manifest, source, target)
    if bundle() != before:
        raise ValueError('source changed during construction/audit')
    return target, {'schema': SCHEMA, 'source_bundle': before,
                    'canonical_sha256': sha(canonical), 'inert_source_sha256': sha(source),
                    'target_sha256': sha(target), 'target_bytes': len(target),
                    'manifest': manifest, 'intent_audit': intent, 'complete_diff_audit': audit,
                    'evidence': 'guarded-static-construction-only', 'emitted': False,
                    'production_approved': False, 'native_execution': False,
                    'requires_debugger_record_event_preparation': True}


def emit(canonical, output, reviewed_bundle):
    before = bundle()
    if reviewed_bundle != before['sha256']:
        raise ValueError('exact reviewed builder bundle required')
    # The contract rejects traversal and every alias in the parent chain.
    destination = contract.output_path(output.relative_to(ROOT).as_posix())
    directory = destination.parent
    if directory.exists():
        raise ValueError('fresh build directory required')
    directory.mkdir(parents=True, exist_ok=False)
    assembler.verify_asar()
    wrapper = 'arch 65816\nnorom\norg $000000\nincsrc "' + ASM.as_posix() + '"\n'
    helper, assembly = assembler.assemble_raw(directory, 'adapters', wrapper, maximum=157)
    if helper != component():
        raise ValueError('fresh assembly differs from reviewed component')
    image, receipt = build_image(canonical, helper, destination)
    receipt.update(assembly=assembly, emitted=True, output_path=str(destination),
                   reproduction=['python', '-B', 'tools/build_pc07_native_field_v1.py',
                                 '--rom', str(compatibility.DEFAULT_ROM), '--output', str(destination),
                                 '--emit-reviewed-bundle', before['sha256']])
    if bundle() != before:
        raise ValueError('source drift before emission')
    # Both shared audits have completed; exclusive writes never replace a run.
    assembler.exclusive(destination, image)
    assembler.exclusive(directory / 'build_receipt.json',
                        (json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode())
    if sha(destination.read_bytes()) != receipt['target_sha256']:
        raise ValueError('emitted image identity mismatch')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=compatibility.DEFAULT_ROM)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--emit-reviewed-bundle')
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    canonical = args.rom.read_bytes()
    if args.emit_reviewed_bundle:
        result = emit(canonical, output, args.emit_reviewed_bundle)
    else:
        _, result = build_image(canonical, component(), output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
