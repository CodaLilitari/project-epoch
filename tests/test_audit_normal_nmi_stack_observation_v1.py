"""Original filesystem/trace specimens for the acceptance auditor.

These tiny JMP/RTI programs and synthetic metadata are authored test data,
not retail ROM bytes, actual emulator captures, or evidence of runtime success.
The full observer validator runs on them; only source inventory and the prior
entry-context witnesses are substituted by these explicit original fixtures.
"""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_normal_nmi_stack_observation_v1 as audit
import test_normal_nmi_stack_observation_v1 as specimen


class StrictInput(unittest.TestCase):
    def test_duplicate_top_level_json(self):
        with self.assertRaisesRegex(audit.AuditError, 'duplicate'):
            audit.strict_json(b'{"a":1,"a":2}', 'test')

    def test_duplicate_nested_json(self):
        with self.assertRaisesRegex(audit.AuditError, 'duplicate'):
            audit.strict_json(b'{"a":{"b":1,"b":2}}', 'test')

    def test_nonfinite_json(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value), self.assertRaisesRegex(audit.AuditError, 'nonfinite'):
                audit.strict_json(('{"a":' + value + '}').encode(), 'test')

    def test_partial_json(self):
        with self.assertRaisesRegex(audit.AuditError, 'partial'):
            audit.strict_json(b'{"intervals":[', 'test')

    def test_nonobject_json(self):
        with self.assertRaisesRegex(audit.AuditError, 'object'):
            audit.strict_json(b'[]', 'test')

    def test_fixed_observer_source_pins(self):
        for relative, (size, pin) in audit.OBSERVER_PINS.items():
            raw = (audit.ROOT / relative).read_bytes()
            self.assertEqual((len(raw), audit.sha(raw)), (size, pin))

    def test_current_source_pin_mismatch_refuses_before_loading_inputs(self):
        relative, (size, _) = next(iter(audit.OBSERVER_PINS.items()))
        with mock.patch.object(audit, 'OBSERVER_PINS', {relative: (size, '0' * 64)}):
            with self.assertRaisesRegex(audit.AuditError, 'current observer source pin'):
                audit.current_sources(audit.FileLedger())


class OriginalPair(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='epoch_nmi_auditor_original_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'private/test_runs').mkdir(parents=True)
        (self.root / 'tools').mkdir()
        (self.root / 'tests').mkdir()
        self.auditor_path = self.root / 'tools/audit_normal_nmi_stack_observation_v1.py'
        self.auditor_path.write_bytes(b'original synthetic auditor identity\n')
        (self.root / 'tests/test_audit_normal_nmi_stack_observation_v1.py').write_bytes(b'original synthetic test identity\n')
        self.paths = {}
        for key in ('launcher', 'collector', 'tests', 'reference_trace', 'rom', 'sram', 'state', *audit.observer.safe.RUNTIME_NAMES):
            suffix = '.lua' if key == 'collector' else '.py' if key in ('launcher', 'tests') else '.bin'
            path = self.root / 'tools' / (key + suffix)
            path.write_bytes(('original synthetic ' + key + '\n').encode())
            self.paths[key] = path
        rom = bytearray([0xEA]) * 0x400000
        begin = audit.observer.ENTRY - 0xC00000
        rom[begin:begin + 3] = bytes([0x4C, audit.observer.EXIT & 255, audit.observer.EXIT >> 8 & 255])
        rom[audit.observer.EXIT - 0xC00000] = 0x40
        self.paths['rom'].write_bytes(rom)
        self.read_rom = lambda pc, n: bytes(rom[pc - 0xC00000:pc - 0xC00000 + n])
        intervals = []
        for poll in audit.observer.POLLS:
            row, _ = specimen.envelope()
            row['poll'] = poll
            # Original bus observation of zero completion state. No CPU operand
            # bytes or game data are copied into this specimen.
            row['events'].insert(1, specimen.bus('read', 0x7E9876, 0, clock=106))
            intervals.append(row)
        self.trace = {'schema': audit.observer.SCHEMA, 'error': None, 'pilot': False,
            'intervals': intervals, 'baseline': {'location': 0x1DB, 'party': [0, 1, 2]},
            'resolver': {'poll': 378, 'cpu': specimen.cpu(0xC14612), 'selector': 8, 'branch': 0},
            'terminal_poll': 930}
        prior = {row['poll']: {'cpu': row['events'][0]['cpu'], 'stack': row['entry_marker']['hardware']}
                 for row in intervals}
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(audit, 'ROOT', self.root))
        self.stack.enter_context(mock.patch.object(audit, '__file__', str(self.auditor_path)))
        self.stack.enter_context(mock.patch.object(audit.observer, 'reference_entries', return_value=prior))
        self.stack.enter_context(mock.patch.object(audit.observer, 'reference_resolver', return_value={'cpu': self.trace['resolver']['cpu']}))

        def sources(ledger):
            return self.paths, {key: ledger.file(path) for key, path in self.paths.items()}

        self.stack.enter_context(mock.patch.object(audit, 'current_sources', side_effect=sources))
        self.first = self.build('first', 'a' * 24)
        self.second = self.build('second', 'b' * 24)

    def put_json(self, path, value):
        path.write_bytes(audit.serial(value))

    def read_json(self, path):
        return json.loads(path.read_bytes())

    def build(self, name, token):
        base = self.root / 'private/test_runs' / name
        (base / 'source_archive').mkdir(parents=True)
        stage = base / 'staged'
        (stage / 'app/Saves').mkdir(parents=True)
        (stage / 'profile').mkdir()
        (stage / 'temp').mkdir()
        source_hashes = {key: audit.sha(path.read_bytes()) for key, path in self.paths.items()}
        archives = {}
        for key in ('launcher', 'collector', 'tests'):
            path = base / 'source_archive' / (key + self.paths[key].suffix)
            shutil.copyfile(self.paths[key], path)
            archives[key] = path
        stem = 'pe_nmi_stack_' + token
        staged = {key: stage / 'app' / name for key, name in audit.observer.safe.RUNTIME_NAMES.items()}
        staged.update(rom=stage / (stem + '.sfc'), state=stage / (stem + '.mss'),
                      sram=stage / 'app/Saves' / (stem + '.srm'), collector=stage / 'collector.lua')
        for key, path in staged.items():
            shutil.copyfile(self.paths[key], path)
        receipt = {'schema': audit.observer.SCHEMA, 'pilot': False, 'source_hashes': source_hashes,
            'staged_hashes': {key: audit.sha(path.read_bytes()) for key, path in staged.items()},
            'source_archive_hashes': {key: audit.sha(path.read_bytes()) for key, path in archives.items()},
            'source_archive_files': {key: path.name for key, path in archives.items()}}
        self.put_json(base / 'launch_inputs.json', receipt)
        self.put_json(base / 'trace.json', self.trace)
        summary = audit.observer.summarize(self.trace, self.read_rom, pilot=False)
        manifest = {**receipt, 'evidence_level': 'exploratory-runtime-not-accepted', 'observations': summary,
            'trace_sha256': audit.sha((base / 'trace.json').read_bytes()),
            'sources_staged_archives_unchanged': True, 'checkpoint_load_only': True,
            'controller_schedule_reused': True, 'rom_cpu_memory_edits': False, 'production_approval': False}
        self.put_json(base / 'manifest.json', manifest)
        (base / 'process.log').write_bytes(b'')
        return base

    def call(self):
        return audit.audit_pair(self.first, self.second)

    def reject(self, pattern=None):
        with self.assertRaisesRegex(audit.AuditError, pattern or '.'):
            self.call()

    def change_manifest(self, change):
        path = self.second / 'manifest.json'
        value = self.read_json(path)
        change(value)
        self.put_json(path, value)

    def reseal_trace(self, change, *, valid=False):
        path = self.second / 'trace.json'
        trace = self.read_json(path)
        change(trace)
        self.put_json(path, trace)
        def manifest(value):
            value['trace_sha256'] = audit.sha(path.read_bytes())
            if valid:
                value['observations'] = audit.observer.summarize(trace, self.read_rom, pilot=False)
        self.change_manifest(manifest)

    def test_original_full_pair_revalidates_and_emits_only_metadata(self):
        result = self.call()
        self.assertEqual(result['interval_count_per_run'], 5)
        self.assertEqual(result['minimum_recorded_sp'], 0x600)
        self.assertFalse(result['process_exit_code_independently_recorded'])
        self.assertFalse(result['production_approval'])
        self.assertTrue(result['full_trace_bytes_identical'])
        for run in result['runs']:
            for row in run['intervals']:
                self.assertEqual(row['publication_access_counts']['completion_and_config'], {'reads': 1, 'writes': 0})
                self.assertTrue(row['minimum_recorded_sites'])
        forbidden = {'cpu', 'code', 'events', 'stack', 'wram_before', 'wram_after', 'publication_accesses', 'value'}
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for item in value.values(): check(item)
            elif isinstance(value, list):
                for item in value: check(item)
        check(result)

    def test_single_root_refused(self):
        self.second = self.first
        self.reject('distinct')

    def test_nested_root_refused(self):
        self.second = self.first / 'nested'
        self.second.mkdir()
        self.reject('nested')

    def test_outside_private_run_root_refused(self):
        self.second = self.root / 'tools'
        self.reject('private/test_runs')

    def test_lexical_traversal_refused(self):
        self.second = self.first / '..' / 'second'
        self.reject('traversal')

    def test_reused_isolated_stem_refused(self):
        stage = self.second / 'staged'
        for directory in (stage, stage / 'app/Saves'):
            for path in list(directory.iterdir()):
                if path.name.startswith('pe_nmi_stack_' + 'b' * 24):
                    path.rename(path.with_name(path.name.replace('b' * 24, 'a' * 24)))
        self.reject('stem reused')

    def test_hardlinked_trace_refused(self):
        target = self.second / 'trace.json'
        target.unlink()
        os.link(self.first / 'trace.json', target)
        self.reject('alias one physical')

    def test_pilot_receipt_refused(self):
        path = self.second / 'launch_inputs.json'
        value = self.read_json(path); value['pilot'] = True; self.put_json(path, value)
        self.reject('pilot')

    def test_pilot_trace_refused_even_with_resealed_hash(self):
        self.reseal_trace(lambda x: x.update(pilot=True))
        self.reject('trace protocol')

    def test_missing_interval_refused(self):
        self.reseal_trace(lambda x: x['intervals'].pop())
        self.reject('inventory')

    def test_early_terminal_refused(self):
        self.reseal_trace(lambda x: x.update(terminal_poll=381))
        self.reject('terminal')

    def test_trace_error_refused(self):
        self.reseal_trace(lambda x: x.update(error='original error specimen'))
        self.reject('trace protocol')

    def test_partial_trace_refused(self):
        (self.second / 'trace.json').write_bytes(b'{"schema":')
        self.reject('partial')

    def test_duplicate_trace_key_refused(self):
        path = self.second / 'trace.json'
        path.write_bytes(path.read_bytes().replace(b'"pilot":false', b'"pilot":false,"pilot":false', 1))
        self.reject('duplicate')

    def test_wrong_instruction_source_refused(self):
        self.reseal_trace(lambda x: x['intervals'][0]['events'][0]['code'].__setitem__(0, 0xEA))
        self.reject('opcode peeks differ')

    def test_unexplained_wram_change_refused(self):
        self.reseal_trace(lambda x: x['intervals'][0]['wram_after'].__setitem__(0x3000, 1))
        self.reject('WRAM')

    def test_wrong_prior_entry_cpu_refused(self):
        self.reseal_trace(lambda x: x['intervals'][0]['events'][0]['cpu'].update(a=1))
        self.reject('source-pinned actual')

    def test_forged_observation_summary_refused(self):
        self.change_manifest(lambda x: x['observations'].update(minimum_recorded_sp=0))
        self.reject('completed manifest')

    def test_truthy_integer_not_boolean_refused(self):
        self.change_manifest(lambda x: x.update(sources_staged_archives_unchanged=1))
        self.reject('completed manifest')

    def test_production_promotion_refused(self):
        self.change_manifest(lambda x: x.update(production_approval=True))
        self.reject('completed manifest')

    def test_staged_runtime_drift_refused(self):
        (self.second / 'staged/app/Mesen.exe').write_bytes(b'drift')
        self.reject('staged bytes')

    def test_staged_rom_drift_refused(self):
        path = next((self.second / 'staged').glob('*.sfc'))
        with path.open('r+b') as stream: stream.write(b'X')
        self.reject('staged bytes')

    def test_staged_state_drift_refused(self):
        next((self.second / 'staged').glob('*.mss')).write_bytes(b'drift')
        self.reject('staged bytes')

    def test_staged_sram_drift_refused(self):
        next((self.second / 'staged/app/Saves').glob('*.srm')).write_bytes(b'drift')
        self.reject('staged bytes')

    def test_archive_drift_refused(self):
        (self.second / 'source_archive/launcher.py').write_bytes(b'drift')
        self.reject('archive bytes')

    def test_missing_archive_refused(self):
        (self.second / 'source_archive/collector.lua').unlink()
        self.reject('archive inventory')

    def test_extra_archive_refused(self):
        (self.second / 'source_archive/extra.py').write_bytes(b'extra')
        self.reject('archive inventory')

    def test_forged_launch_hash_refused(self):
        path = self.second / 'launch_inputs.json'
        value = self.read_json(path); value['source_hashes']['launcher'] = '0' * 64
        self.put_json(path, value)
        self.reject('prelaunch receipt')

    def test_archive_filename_traversal_refused(self):
        path = self.second / 'launch_inputs.json'
        value = self.read_json(path); value['source_archive_files']['launcher'] = '../launcher.py'
        self.put_json(path, value)
        self.reject('prelaunch receipt')

    def test_extra_save_refused(self):
        (self.second / 'staged/app/Saves/extra.srm').write_bytes(b'extra')
        self.reject('save inventory')

    def test_extra_rom_refused(self):
        (self.second / 'staged/extra.sfc').write_bytes(b'extra')
        self.reject('stage inventory')

    def test_host_error_marker_refused(self):
        (self.second / 'host_rejection.json').write_bytes(b'{}')
        self.reject('error marker')

    def test_native_error_marker_refused(self):
        (self.second / 'trace.json.error.txt').write_bytes(b'error')
        self.reject('error marker')

    def test_missing_manifest_refused(self):
        (self.second / 'manifest.json').unlink()
        self.reject('missing')

    def test_missing_process_log_refused(self):
        (self.second / 'process.log').unlink()
        self.reject('missing')

    def test_distinct_individually_valid_traces_refused(self):
        def change(trace):
            for row in trace['intervals']:
                for event in row['events']:
                    event['timing']['masterClock'] += 12
                    event['timing']['memoryManager.masterClock'] += 12
                    event['timing']['cpu.cycleCount'] += 2
        self.reseal_trace(change, valid=True)
        self.reject('full trace pair differs')

    def test_source_change_during_pair_validation_refused(self):
        original = audit.verify_run
        calls = []
        def wrapped(*args):
            value = original(*args); calls.append(1)
            if len(calls) == 2: self.paths['launcher'].write_bytes(b'changed during validation')
            return value
        with mock.patch.object(audit, 'verify_run', side_effect=wrapped):
            self.reject('file drift')

    def test_archive_inventory_change_during_validation_refused(self):
        original = audit.verify_run
        calls = []
        def wrapped(*args):
            value = original(*args); calls.append(1)
            if len(calls) == 2: (self.first / 'source_archive/late.py').write_bytes(b'late')
            return value
        with mock.patch.object(audit, 'verify_run', side_effect=wrapped):
            self.reject('inventory drift')

    def test_cli_refusal_emits_no_acceptance_metadata(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = audit.main(['--run-a', str(self.first), '--run-b', str(self.first)])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('refused', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
