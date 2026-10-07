"""Reproduce the public October 7 checkpoint from pinned private metadata.

No emulator, ROM mutation or publication. Default compares the public JSON;
--write creates it exclusively. Raw game inputs and traces are never copied.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = 'docs/pc07_native_field_checkpoint_2026_10_07.md'
OUTPUT = ROOT / 'references/pc07_native_field_checkpoint_2026_10_07.json'
RUN = 'private/test_runs/pc07_field_probe_v3_run1/receipt.json'
REVIEW = 'private/research/pc07_native_field_v3_review_20261007/receipt.json'
PINS = {
    RUN: '042e6805cad04baaef5c395ca9357cd66f53c06e3bfe19e470d841d9afee2449',
    REVIEW: 'fdfb4f48b23ec7aa694ba7f0d68831e994f39259f33ba80266db07c65cfb8032',
    REPORT: '864025bfe031eced273df52d5449aa62c0854c8495ae031067240e43f96baeec',
}


def identity(path):
    data = (ROOT / path).read_bytes()
    return {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def build():
    for path, expected in PINS.items():
        if identity(path)['sha256'] != expected:
            raise ValueError('pinned metadata drift: ' + path)
    run = json.loads((ROOT / RUN).read_bytes())
    review = json.loads((ROOT / REVIEW).read_bytes())
    for row in run['source_bundle']['sources']:
        if identity(row['path'])['sha256'] != row['sha256']:
            raise ValueError('run dependency drift: ' + row['path'])
    return {
        'schema': 'project-epoch-public-checkpoint-v1',
        'date': '2026-10-07',
        'project': 'Project Epoch',
        'status': 'paused-at-user-request',
        'goal_complete': False,
        'playable_release': False,
        'route': {'primary': 'SNES', 'recompilation': 'comparative fallback; no route switch'},
        'evidence_level': 'verified-runtime, one instrumented selected-field run; independent offline review',
        'headline': 'Logical PC07 moves with a qualified native ROM graphics helper in a prepared field scene.',
        'native_run_count': 1,
        'native_reruns_for_review': 0,
        'scope': {'location_hex': '01DA', 'event_hex': '0125', 'last_controller_poll': 400,
                  'trace_records': run['records'], 'debugger_preparation_byte_pairs': 2725,
                  'debugger_cpu_edits': 0, 'helper_cpu_address_hex': '410000',
                  'hook_cpu_span_hex': ['C0448D', 'C04493'], 'span_end_exclusive': True,
                  'guarded_changed_bytes_relative_to_inert_scaffold': 191,
                  'game_rom_bytes': 8388608, 'production_hook_or_allocation_approved': False},
        'preparation': ['checkpoint replay', 'compatibility block copy', 'independent record',
                        'roster and joined state', 'transformed selected event and length'],
        'observations': run['observations'],
        'independent_review': {
            'source_files_verified': review['source_files_verified'],
            'file_identities_rechecked_at_end': review['files_rechecked_at_end'],
            'receipt_reproduced_by_root': True,
            'movement_coordinate_byte_stores_per_actor': 2480,
            'stack_bus_events': 30,
            'original_seven_records_preserved': True,
            'epoch_name_preserved_in_snapshots': 10,
            'sram_preserved_in_snapshots': 10,
            'observed_sram_writes': 0,
            'coverage': 'Declared watched intervals and snapshots, not a global WRAM ledger.',
        },
        'visual_inspection': {'by': 'root', 'screenshots': ['poll_180.png', 'poll_400.png'],
                              'images_public': False, 'independent_reviewers_viewed_images': False},
        'validation_correction': review['additive_stack_bus_audit'],
        'focused_tests': {'native_helper_host_validator': 13, 'private_expanded_write_contract': 17,
                          'existing_rom_write_guard': 16, 'total_passed': 46,
                          'scope': 'Focused host tests; not a full repository suite or extra emulator runs.'},
        'epoch_preservation': {
            'naming_selector_hex': '07', 'name_wram_span_hex': ['7E2C4D', '7E2C53'],
            'span_end_exclusive': True, 'new_playable_name_storage_required': True,
            'global_id_rewrite_allowed': False, 'vehicle_behaviour_verified': False,
        },
        'community_reuse': {
            'novel_mapping_discovery_claimed': False,
            'credits': ['Mauron', 'Vehek', 'JLukas', 'Temporal Redux / Jets of Time'],
            'implementation_reference': 'https://github.com/OnemusCT/temporal-redux/blob/365086c1c0a33144b24bff4933998bdff82c9940/sourcefiles/jetsoftime/ctevent.py',
            'method': 'Reuse pinned community mappings and insertion methods; validate the selected dependencies and retain corrections.',
        },
        'not_proved': ['native recruitment and event installation', 'destination event0126 execution',
                      'battle participation and ordinary Attack', 'PC07 Tech and menu support',
                      'PC07 normal save and cold-load persistence', 'authored Schala graphics',
                      'Epoch vehicle naming UI, boarding, travel and save/load',
                      'interrupt safety', 'global stack and memory ownership',
                      'whole-game compatibility', 'absence of slowdown', 'a playable eighth-character release'],
        'next_after_explicit_resume': 'Reuse this field checkpoint and the static event0126 transform for the bounded ordinary-Attack experiment; do not repeat completed mapping surveys or native matrices without a named missing condition.',
        'identities': {
            'human_report': identity(REPORT), 'private_run_receipt': identity(RUN),
            'private_review_receipt': identity(REVIEW),
            'private_trace': review['trace'],
            'private_diagnostic_rom_sha256': review['guarded_rom_sha256'],
            'run_source_bundle_sha256': run['source_bundle']['sha256'],
            'source_manifest': run['source_bundle']['sources'],
            'json_builder': identity('tools/build_pc07_native_field_checkpoint_v1.py'),
        },
        'reproduction': {
            'public_json': 'python -B tools/build_pc07_native_field_checkpoint_v1.py',
            'offline_review': review['reproduction'],
            'future_native_run': run['reproduction'],
            'focused_tests': [
                'python -B -m unittest discover -s tests -p test_mesen_pc07_field_probe_v3.py',
                'python -B -m unittest discover -s tests -p test_pc07_private_expanded_write_contract_v1.py',
                'python -B -m unittest discover -s tests -p test_rom_write_intent_guard.py'],
            'private_fixture_requirement': 'Native observation, review and JSON regeneration require exact private fixtures and locally held game inputs. The public checkout alone is insufficient. Focused synthetic host tests can be inspected and run without distributed ROM data.',
            'frozen_run_receipt_status': run['status'],
            'status_explanation': 'The raw receipt predates independent review and is preserved unchanged. Later review is additive.',
        },
        'distribution': {'contains_rom_save_state_game_assets_or_raw_trace': False,
                         'private_paths_are_metadata_references_only': True},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    encoded = (json.dumps(build(), indent=2, sort_keys=True) + '\n').encode()
    if args.write:
        with OUTPUT.open('xb') as stream:
            stream.write(encoded)
    elif OUTPUT.read_bytes() != encoded:
        raise ValueError('public checkpoint JSON differs from pinned metadata')
    print(json.dumps({'status': 'verified', **identity(OUTPUT.relative_to(ROOT).as_posix()),
                      'evidence': 'deterministic metadata reproduction; no new native execution'}))
