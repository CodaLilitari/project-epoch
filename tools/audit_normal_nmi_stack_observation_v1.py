#!/usr/bin/env python3
"""Read-only acceptance of two matching full normal-NMI observation runs.

Only compact original metadata is emitted. Trace bytes, CPU/register arrays,
instruction peeks, bus values and WRAM snapshots remain in private run roots.
No run is accepted until both complete traces independently revalidate against
the current pinned observer and every source/staged/archive file is checked.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

import run_normal_nmi_stack_observation_v1 as observer

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'project-epoch-normal-nmi-stack-observation-v1-accepted-pair'
OBSERVER_PINS = {
    'tools/run_normal_nmi_stack_observation_v1.py': (32546, 'bb4bddb1f995124ebdd269a0b937ad988d972ad524d6237073cdeb1ae0b60784'),
    'tools/mesen_normal_nmi_stack_observation_v1.lua': (8496, '77a39e798cb0b82c30e8d46cf3ecf64987ce30bf3902308b98fa2549177a8ee4'),
    'tests/test_normal_nmi_stack_observation_v1.py': (20641, '0e8420e13806d9b637367bbfed717fdaeff08454fccded7bdc44e82f7c12c2de'),
}
MAX_FILE = 128 * 1024 * 1024
MAX_RECEIPT = 32 * 1024 * 1024
MAX_LOG = 32 * 1024 * 1024
RECEIPT_KEYS = {'schema', 'pilot', 'source_hashes', 'staged_hashes',
                'source_archive_hashes', 'source_archive_files'}
MANIFEST_KEYS = RECEIPT_KEYS | {'evidence_level', 'observations', 'trace_sha256',
    'sources_staged_archives_unchanged', 'checkpoint_load_only',
    'controller_schedule_reused', 'rom_cpu_memory_edits', 'production_approval'}
PUBLICATION_RANGES = (
    ('owners_and_script_pointers', 0x5DAC, 0x5DFD),
    ('completion_and_config', 0x9876, 0x987C),
    ('branch_word', 0xA0B3, 0xA0B5),
)


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def serial(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw, label):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key in ' + label)
            result[key] = value
        return result

    def nonfinite(_):
        raise AuditError('nonfinite JSON in ' + label)

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError('invalid or partial JSON in ' + label) from exc
    require(type(value) is dict, 'JSON object required: ' + label)
    return value


def direct_path(path, *, directory=False):
    path = Path(path)
    require('..' not in path.parts, 'lexical traversal refused')
    path = path if path.is_absolute() else ROOT / path
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise AuditError('path outside workspace') from exc
    current = ROOT
    for part in ('', *relative.parts):
        if part:
            current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise AuditError('missing required path: ' + str(current)) from exc
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, 'st_file_attributes', 0) & 0x400),
                'symlink, junction or reparse path refused')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            'direct directory required' if directory else 'direct regular file required')
    require(path.resolve(strict=True) == path, 'path resolves away from its identity')
    return path


class FileLedger:
    """Hashes actual files and checks them again after paired validation."""
    def __init__(self):
        self.files = {}
        self.directories = {}

    def file(self, path, *, maximum=MAX_FILE, allow_empty=False, retain=False):
        path = direct_path(path)
        before = path.stat()
        require((0 if allow_empty else 1) <= before.st_size <= maximum, 'file size bound: ' + path.name)
        digest = hashlib.sha256()
        chunks = []
        count = 0
        with path.open('rb') as handle:
            opened = os.fstat(handle.fileno())
            require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'file changed on open')
            while chunk := handle.read(min(1024 * 1024, maximum + 1 - count)):
                count += len(chunk)
                require(count <= maximum, 'file grew beyond bound')
                digest.update(chunk)
                if retain:
                    chunks.append(chunk)
            after = os.fstat(handle.fileno())
        require((before.st_size, before.st_mtime_ns, before.st_ino, before.st_dev) ==
                (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev) and count == before.st_size,
                'file changed during read')
        identity = {'path': path.relative_to(ROOT).as_posix(), 'size_bytes': count,
                    'sha256': digest.hexdigest()}
        if path in self.files:
            require(self.files[path][0] == identity, 'file drift during audit')
        self.files[path] = (identity, maximum, allow_empty)
        return (identity, b''.join(chunks)) if retain else identity

    def json(self, path, *, maximum=MAX_RECEIPT):
        identity, raw = self.file(path, maximum=maximum, retain=True)
        return strict_json(raw, Path(path).name), identity, raw

    def inventory(self, path):
        path = direct_path(path, directory=True)
        names = sorted(p.name for p in path.iterdir())
        if path in self.directories:
            require(self.directories[path] == names, 'directory inventory drift')
        self.directories[path] = names
        return names

    def recheck(self):
        for path, (_, maximum, allow_empty) in list(self.files.items()):
            self.file(path, maximum=maximum, allow_empty=allow_empty)
        for path in list(self.directories):
            self.inventory(path)


def current_sources(ledger):
    for relative, (size, pin) in OBSERVER_PINS.items():
        identity = ledger.file(ROOT / relative)
        require((identity['size_bytes'], identity['sha256']) == (size, pin), 'current observer source pin: ' + relative)
    paths = observer.source_paths()
    for key, (relative, size, pin) in observer.context.PINNED.items():
        path = ROOT / relative
        identity = ledger.file(path)
        require((identity['size_bytes'], identity['sha256']) == (size, pin), 'canonical input pin: ' + key)
        paths[key] = path
    for key, filename in observer.safe.RUNTIME_NAMES.items():
        path = observer.safe.DEFAULT_MESEN.parent / filename
        identity = ledger.file(path)
        require((identity['size_bytes'], identity['sha256']) == observer.safe.PINNED_IDENTITIES[key],
                'runtime input pin: ' + key)
        paths[key] = path
    sources = {key: ledger.file(path) for key, path in paths.items()}
    _, size, pin = observer.REFERENCE_TRACE
    require((sources['reference_trace']['size_bytes'], sources['reference_trace']['sha256']) == (size, pin),
            'accepted reference trace pin')
    return paths, sources


def compact_interval(row, result):
    minimum = result['minimum_recorded_sp']
    sites = Counter((e['kind'], observer.pc_of(e['cpu'])) for e in row['events']
                    if e['cpu']['sp'] == minimum)
    counts = {name: {'reads': 0, 'writes': 0} for name, _, _ in PUBLICATION_RANGES}
    for event in row['events']:
        if event['kind'] not in ('read', 'write'):
            continue
        address = observer.physical_wram(event['address'])
        if address is None:
            continue
        for name, start, end in PUBLICATION_RANGES:
            if start <= address < end:
                counts[name][event['kind'] + 's'] += 1
    require(sum(sum(v.values()) for v in counts.values()) == len(result['publication_accesses']),
            'publication projection disagrees with revalidated summary')
    scalar_keys = ('poll', 'execution_observations', 'executed_instructions', 'bus_events',
        'entry_sp', 'minimum_instruction_boundary_sp', 'minimum_recorded_sp',
        'additional_bytes_below_handler_entry', 'bytes_below_interrupted_sp_including_existing_hardware_frame',
        'master_clocks', 'execution_projection_sha256', 'wram_changed_bytes',
        'wram_before_sha256', 'wram_after_sha256')
    return {**{key: result[key] for key in scalar_keys},
        'minimum_recorded_sites': [{'event_kind': kind, 'pc': pc, 'observations': count}
                                   for (kind, pc), count in sorted(sites.items())],
        'publication_access_counts': counts,
        'sp_change_count': len(result['sp_changes']),
        'call_return_transition_counts': dict(sorted(Counter(x['kind'] for x in result['observed_call_return_transitions']).items()))}


def verify_run(directory, paths, sources, ledger, read_rom):
    require(not (directory / 'host_rejection.json').exists() and
            not (directory / 'trace.json.error.txt').exists(), 'retained host/native error marker')
    ledger.inventory(directory)
    launch, launch_id, launch_raw = ledger.json(directory / 'launch_inputs.json')
    manifest, manifest_id, manifest_raw = ledger.json(directory / 'manifest.json')
    require(set(launch) == RECEIPT_KEYS and set(manifest) == MANIFEST_KEYS, 'exact launch/manifest shape')
    require(launch['pilot'] is False and manifest['pilot'] is False, 'two full runs required; pilot refused')
    source_hashes = {key: row['sha256'] for key, row in sources.items()}
    archive_paths = {key: directory / 'source_archive' / (key + path.suffix)
                     for key, path in paths.items()
                     if key not in {*observer.context.PINNED, *observer.safe.RUNTIME_NAMES, 'reference_trace'}}
    require(ledger.inventory(directory / 'source_archive') == sorted(p.name for p in archive_paths.values()),
            'exact complete source archive inventory')
    archives = {key: ledger.file(path) for key, path in archive_paths.items()}
    require(all((row['size_bytes'], row['sha256']) == (sources[key]['size_bytes'], sources[key]['sha256'])
                for key, row in archives.items()), 'source archive bytes differ')
    stage = directory / 'staged'
    names = ledger.inventory(stage)
    rom_names = [name for name in names if re.fullmatch(r'pe_nmi_stack_[0-9a-f]{24}\.sfc', name)]
    require(len(rom_names) == 1, 'one exact isolated staged ROM name')
    stem = rom_names[0][:-4]
    require(names == sorted(['app', 'collector.lua', stem + '.sfc', stem + '.mss', 'profile', 'temp']),
            'exact stage inventory')
    staged_paths = {key: stage / 'app' / name for key, name in observer.safe.RUNTIME_NAMES.items()}
    staged_paths.update(rom=stage / (stem + '.sfc'), state=stage / (stem + '.mss'),
                        sram=stage / 'app/Saves' / (stem + '.srm'), collector=stage / 'collector.lua')
    require(ledger.inventory(stage / 'app/Saves') == [stem + '.srm'], 'exact staged save inventory')
    staged = {key: ledger.file(path) for key, path in staged_paths.items()}
    require(all((row['size_bytes'], row['sha256']) == (sources[key]['size_bytes'], sources[key]['sha256'])
                for key, row in staged.items()), 'staged bytes differ from source')
    receipt = {'schema': observer.SCHEMA, 'pilot': False, 'source_hashes': source_hashes,
        'staged_hashes': {key: row['sha256'] for key, row in staged.items()},
        'source_archive_hashes': {key: row['sha256'] for key, row in archives.items()},
        'source_archive_files': {key: path.name for key, path in archive_paths.items()}}
    require(launch_raw == serial(receipt), 'actual files do not reproduce exact prelaunch receipt')
    trace, trace_id, _ = ledger.json(directory / 'trace.json', maximum=observer.MAX_TRACE)
    try:
        summary = observer.summarize(trace, read_rom, pilot=False)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise AuditError('full trace revalidation failed: ' + str(exc)) from exc
    expected_manifest = {**receipt, 'evidence_level': 'exploratory-runtime-not-accepted',
        'observations': summary, 'trace_sha256': trace_id['sha256'],
        'sources_staged_archives_unchanged': True, 'checkpoint_load_only': True,
        'controller_schedule_reused': True, 'rom_cpu_memory_edits': False, 'production_approval': False}
    require(manifest_raw == serial(expected_manifest), 'completed manifest does not reproduce actual validated evidence')
    process_id = ledger.file(directory / 'process.log', maximum=MAX_LOG, allow_empty=True)
    projection = [compact_interval(row, result) for row, result in
                  zip(trace['intervals'], summary['intervals'], strict=True)]
    return {'directory': directory.relative_to(ROOT).as_posix(), 'staged_stem': stem,
        'artifacts': {'launch_inputs': launch_id, 'manifest': manifest_id, 'trace': trace_id, 'process_log': process_id},
        'staged_identities': staged, 'archived_identities': archives,
        'revalidated_summary_sha256': sha(serial(summary)), 'compact_projection_sha256': sha(serial(projection)),
        'intervals': projection}


def audit_pair(first, second):
    runs_root = direct_path(ROOT / 'private/test_runs', directory=True)
    directories = [direct_path(path, directory=True) for path in (first, second)]
    for directory in directories:
        require(directory != runs_root and directory.is_relative_to(runs_root), 'run root outside private/test_runs')
    require(directories[0] != directories[1] and not os.path.samefile(*directories), 'two distinct run roots required')
    require(not directories[0].is_relative_to(directories[1]) and
            not directories[1].is_relative_to(directories[0]), 'nested run roots refused')
    ledger = FileLedger()
    paths, sources = current_sources(ledger)
    _, rom = ledger.file(paths['rom'], retain=True)

    def read_rom(address, count):
        require(type(address) is int and type(count) is int and count > 0 and
                0xC00000 <= address < address + count <= 0x1000000, 'canonical ROM extent')
        return rom[address - 0xC00000:address - 0xC00000 + count]

    runs = [verify_run(directory, paths, sources, ledger, read_rom) for directory in directories]
    require(runs[0]['staged_stem'] != runs[1]['staged_stem'], 'same isolated launch stem reused')
    for filename in ('trace.json', 'manifest.json', 'launch_inputs.json'):
        require(not os.path.samefile(directories[0] / filename, directories[1] / filename),
                'paired evidence files alias one physical file')
    require(runs[0]['artifacts']['trace']['sha256'] == runs[1]['artifacts']['trace']['sha256'],
            'full trace pair differs')
    require(runs[0]['revalidated_summary_sha256'] == runs[1]['revalidated_summary_sha256'] and
            runs[0]['intervals'] == runs[1]['intervals'], 'revalidated pair differs')
    auditor = ledger.file(Path(__file__).resolve())
    tests = ledger.file(ROOT / 'tests/test_audit_normal_nmi_stack_observation_v1.py')
    ledger.recheck()
    intervals = runs[0]['intervals']
    return {'schema': SCHEMA, 'evidence_level': 'verified-runtime',
        'evidence_scope': 'two identical selected clean-ROM normal-NMI observation traces; handler-entry through pre-RTI only',
        'acceptance_auditor': auditor, 'acceptance_tests': tests, 'source_identities': sources,
        'runs': runs, 'full_trace_bytes_identical': True, 'revalidated_summaries_identical': True,
        'interval_count_per_run': len(intervals),
        'minimum_recorded_sp': min(row['minimum_recorded_sp'] for row in intervals),
        'maximum_observed_depth_including_existing_hardware_frame': max(
            row['bytes_below_interrupted_sp_including_existing_hardware_frame'] for row in intervals),
        'raw_game_data_emitted': False, 'native_hardware_pushes_captured': False,
        'process_exit_code_independently_recorded': False,
        'process_exit_provenance': 'pinned runner checks exit 52 before manifest emission; no separate exit-code receipt exists',
        'full_cpu_alu_independently_reexecuted': False, 'all_game_nmi_paths_proved': False,
        'publication_preemption_proved': False, 'production_stack_headroom_proved': False,
        'production_approval': False,
        'reproduce': ['python', '-B', 'tools/audit_normal_nmi_stack_observation_v1.py',
                      '--run-a', runs[0]['directory'], '--run-b', runs[1]['directory']]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-a', type=Path, required=True)
    parser.add_argument('--run-b', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit_pair(args.run_a, args.run_b)
    except (AuditError, observer.ObservationError, OSError, KeyError, TypeError, ValueError) as exc:
        print('normal-NMI acceptance refused: ' + str(exc), file=sys.stderr)
        return 1
    sys.stdout.buffer.write((json.dumps(result, indent=2, allow_nan=False) + '\n').encode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
