"""Package the accepted development snapshot and explicit demo allowlist.

Never emits a ROM, battery, emulator, raw trace, or private correspondence.
An installed private accepted target is required; no old build chain is run.
"""
from io import BytesIO
from pathlib import Path
import argparse
import json
import zipfile
import epoch_bps_v1 as bps
import epoch_development_bps_export_contract_v1 as contract
import validate_rom_write_intents as guard

DEMO = {'bytes': 462332, 'sha256': '0e49b1bca0295ed6ff3068879a62d26f24cc92ff0c15d08325400d321046867a'}
DEMO_PREFIX = 'project_epoch_development_demo/'
DEMO_FILES = (
    'states/epoch_dev_d4b691_schala_status.mss',
    'states/epoch_dev_d4b691_field_ready.mss',
    'screenshots/01_final_portrait_status_native.png',
    'screenshots/01_final_portrait_status_4x.png',
    'screenshots/02_prior17b156_field_running_native.png',
    'screenshots/03_prior9f6787_natural_cast_native.png',
    'screenshots/04_prior17b156_world_map_schala_epoch_native.png',
    'screenshots/05_INJECTED_prior17b156_front_cast_study_native.png',
    'DEVELOPMENT-NOT-PLAYABLE.md', 'manifest.json',
)
ZIP_NAME = 'project-epoch-dev-2026-10-20.zip'
PUBLIC_MANIFEST = 'release-manifest.json'
README = '''PROJECT EPOCH - 2026-10-20 DEVELOPMENT SNAPSHOT
NOT TRULY PLAYABLE. NOT A COMPLETE EIGHTH-CHARACTER MOD.

This download is for inspecting a development checkpoint. It does not offer
a supported playthrough, recruitment path, completed Tech set or balanced
Schala. Use a separate ROM copy and separate emulator working directory.
Equipment/base balance remains the diagnostic donor setup; it is not the
intended pure-caster design. The Tech tab can still show the vehicle's name.

INSTALL THE PATCH
1. Obtain your own clean, unheadered Chrono Trigger (USA), revision 0 ROM.
   Required length: 4,194,304 bytes; no 512-byte copier header.
   SHA256: 06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9
2. Apply project-epoch-development-2026-10-20-v1.bps with a BPS-compatible
   patcher, such as Floating IPS, saving to a NEW file. Do not patch another
   hack or an already patched ROM. This is one clean-to-final BPS patch.
3. Confirm the output is 8,388,608 bytes and has SHA256:
   d4b6915dc85ef2bc782583de4478f9ed61e07f68fb2dde58b9cced4350ba3117
   If the source or target identity differs, stop; this package does not match.
   PowerShell: (Get-FileHash -LiteralPath 'your-copy.sfc' -Algorithm SHA256).Hash
4. Open that exact patched copy in the tested Mesen build, then load one of
   the supplied .mss files using Mesen's load-state-from-file command.

TESTED EMULATOR / STATES
Mesen 2.1.1+137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1; state format 4.
No emulator is included. Compatibility with other builds/emulators is unproved.
The status state shows Schala's portrait and corrected menu numbers/colors.
The field state permits the tested X/A/Down/Down route to Schala's status.
From the status state, B then B returns to the field. Use your configured SNES
buttons. See demo/DEVELOPMENT-NOT-PLAYABLE.md for the exact demo boundaries.
States include emulator machine state and save RAM; use a disposable separate
emulator directory so they cannot replace your own game's battery data.

WHAT THIS DOES AND DOES NOT SHOW
The final menu displays Schala with her own portrait and name, HP608/969 in
ordinary white, MP93/93, and Attack236 for this prepared record. Original PC
portraits and the separately named Epoch vehicle were preserved in the tested
contexts. Earlier retained observations cover casting, movement and a flying
Epoch land/disembark/house/return/reboard route, on their labeled earlier builds.
Those are not fresh all-game tests of this final image. The front-cast study
image is explicitly injected diagnostic evidence, not ordinary gameplay.
There is no claim of complete Techs, correct growth, balanced equipment,
recruitment, final projectile placement in every facing/context, all-menu naming,
victory progression,
generalized save/load safety across all slots and lifecycle paths, a complete
playthrough, or universal vehicle preservation.
Do not use this checkpoint for an important ongoing save.

CONTENTS / PROVENANCE
The package contains one deterministic BPS patch, two selected Mesen states,
six labeled screenshots, manifests and instructions. No complete ROM, separate
battery, emulator, raw trace or private correspondence is included. ROM and
states must not be committed to the source repository. The patch exporter
checks the exact clean input, final target and immediate guarded build receipt,
runs the shared export intent/complete-diff gate, and applies the whole patch
in memory before release. This is artifact consistency, not a new playtest.
Source: https://gitlab.com/codalilitari/project-epoch
See docs/epoch_development_release_2026_10_20.md for exact reproduction.
'''


def demo_files(raw):
    contract.pin(raw, DEMO, 'selected demo ZIP')
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        expected = [DEMO_PREFIX + name for name in DEMO_FILES]
        contract.need(sorted(archive.namelist()) == sorted(expected), 'demo ZIP exact allowlist')
        content = {name: archive.read(DEMO_PREFIX + name) for name in DEMO_FILES}
    manifest = json.loads(content['manifest.json'])
    contract.need(manifest['required_patched_ROM_sha256'] == contract.TARGET['sha256'] and
                  manifest['ROM_included'] is False and manifest['standalone_battery_included'] is False,
                  'demo target/scope differs')
    contract.need({row['file'] for row in manifest['files']} == set(DEMO_FILES) - {'manifest.json'},
                  'demo manifest exact allowlist')
    for row in manifest['files']:
        contract.pin(content[row['file']], row, 'demo file ' + row['file'])
    return {'demo/' + name: value for name, value in content.items()}, manifest


def zip_bytes(files):
    """Stable ZIP entries, timestamps, order and compression settings."""
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            contract.need('..' not in name.split('/') and not name.startswith('/'), 'unsafe ZIP member')
            info = zipfile.ZipInfo(name, (2026, 10, 20, 0, 0, 0))
            info.create_system = 0
            info.external_attr = 0x20
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def build(source_path, target_path, receipt_path, demo_path, output):
    output = Path(output).absolute()
    relative = (output / contract.NAME).relative_to(contract.ROOT).as_posix()
    contract.output_path(relative)
    contract.need(not output.exists(), 'fresh release directory required')
    source, target, receipt = [Path(p).read_bytes() for p in (source_path, target_path, receipt_path)]
    demo, demo_manifest = demo_files(Path(demo_path).read_bytes())
    with contract.source_snapshot(source, target, receipt):
        manifest = contract.template(relative)
        intent = guard.validate_epoch_development_bps_export_v1_manifest(manifest)
        patch, actions = bps.encode(source, target, contract.METADATA)
        audit = guard.audit_epoch_development_bps_export_v1_patch(manifest, source, target, patch)
        contract.need(intent['status'] == 'metadata-valid' and audit['status'] == 'patch-valid' and
                      audit['complete_diff_coverage'], 'shared guards must precede patch emission')
        contract.need(not guard.APPROVED_PRODUCTION_ALLOCATIONS and not guard.APPROVED_PRODUCTION_HOOKS,
                      'production catalogs remain empty')
        files = {contract.NAME: patch, 'README.txt': README.encode(), **demo}
        public = {
            'schema': 'project-epoch-development-release-v1', 'date': '2026-10-20',
            'status': 'DEVELOPMENT SNAPSHOT - NOT TRULY PLAYABLE',
            'patch': {'file': contract.NAME, 'bytes': len(patch), 'sha256': contract.sha(patch),
                      'format': 'BPS1', 'source': contract.SOURCE, 'target': contract.TARGET,
                      'source_title': 'Chrono Trigger (USA), revision 0', 'copier_header_bytes': 0},
            'immediate_guarded_build_receipt': contract.RECEIPT,
            'guard_and_apply': audit, 'encoding_actions': actions,
            'tested_emulator': demo_manifest['emulator'], 'savestate_format': 4,
            'demo_evidence': 'See demo/manifest.json; earlier-build and injected images are labeled.',
            'complete_playthrough_verified': False, 'complete_PC07_verified': False,
            'critical_HP_color_runtime_verified': False, 'balance_or_equipment_changed': False,
            'known_open': ['Tech-tab vehicle-name alias', 'pure-caster balance/equipment and growth',
                           'complete Techs and projectile placement', 'ordinary recruitment and full progression'],
            'ROM_included': False, 'standalone_battery_included': False,
            'selected_savestates_included': True, 'source_git_savestates_allowed': False,
            'files': [{'file': name, 'bytes': len(raw), 'sha256': contract.sha(raw)}
                      for name, raw in sorted(files.items())],
            'reproduction': 'tools/export_epoch_development_bps_v1.py; exact private accepted inputs required',
            'evidence_level': 'guarded export and complete in-memory patch roundtrip; bounded native evidence retained',
        }
        files[PUBLIC_MANIFEST] = contract.encoded(public)
        bundle = zip_bytes(files)
        # ZIP CRC and exact contents, without a filesystem extraction.
        with zipfile.ZipFile(BytesIO(bundle)) as archive:
            contract.need(sorted(archive.namelist()) == sorted(files) and archive.testzip() is None,
                          'combined ZIP exact allowlist/CRC')
            for name, raw in files.items():
                contract.need(archive.read(name) == raw, 'ZIP byte identity ' + name)
        implementation = ('tools/epoch_bps_v1.py', 'tools/epoch_development_bps_export_contract_v1.py',
                          'tools/export_epoch_development_bps_v1.py', 'tools/validate_rom_write_intents.py')
        receipt_out = {'schema': 'project-epoch-development-export-receipt-v1', 'emitted': True,
                       'intent': intent, 'audit': audit, 'manifest': manifest,
                       'patch': public['patch'], 'selected_demo_archive': DEMO,
                       'bundle': {'file': ZIP_NAME, 'bytes': len(bundle), 'sha256': contract.sha(bundle)},
                       'bundle_members': sorted(files), 'source_inputs': [
                           {'path': name, 'sha256': contract.sha((contract.ROOT / name).read_bytes())}
                           for name in implementation], 'ROM_written': False,
                       'historical_builders_or_validators_executed': False,
                       'production_catalogs_remain_empty': True}
        # Only this explicit set may be written; no source image is emitted.
        outputs = {contract.NAME: patch, ZIP_NAME: bundle, PUBLIC_MANIFEST: files[PUBLIC_MANIFEST],
                   'README.txt': files['README.txt'], 'export-receipt.json': contract.encoded(receipt_out)}
        output.mkdir(parents=True, exist_ok=False)
        for name, raw in outputs.items():
            with (output / name).open('xb') as handle:
                handle.write(raw)
    return receipt_out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--demo-zip', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source, args.target, args.receipt, args.demo_zip, args.output)
    print(json.dumps({'status': 'guarded-development-export', 'patch': result['patch'],
                      'bundle': result['bundle'], 'audit': result['audit']}))
