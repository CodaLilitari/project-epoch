"""Original tiny files and phase specimens; no game or native-run data."""
import contextlib
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_package_resolver_phase_v2 as a
import run_package_resolver_phase_v2 as observer
import test_package_resolver_phase_v2 as specimen

class OriginalPair(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='epoch_phase_acceptance_original_')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        for name in ('private/test_runs','tools','tests'):(self.root/name).mkdir(parents=True)
        for name in ('tools/audit_package_resolver_phase_v2.py','tests/test_audit_package_resolver_phase_v2.py',a.UTILITY_PIN[0]):
            (self.root/name).write_bytes(('original identity '+name+'\n').encode())
        self.paths={}
        for key in ('launcher','collector','tests','v1_launcher','reference_trace','rom','sram','state',*observer.safe.RUNTIME_NAMES):
            p=self.root/'tools'/(key+('.lua' if key=='collector' else '.bin'))
            p.write_bytes(('original source '+key+'\n').encode());self.paths[key]=p
        self.trace,self.reference=specimen.specimen()
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(a,'ROOT',self.root))
        self.stack.enter_context(mock.patch.object(a.files,'ROOT',self.root))
        self.stack.enter_context(mock.patch.object(a,'observer_module',return_value=observer))
        self.stack.enter_context(mock.patch.object(observer,'reference_records',return_value=self.reference))
        self.stack.enter_context(mock.patch.object(a,'current_sources',side_effect=lambda obs,ledger:(self.paths,{k:ledger.file(p) for k,p in self.paths.items()})))
        self.first=self.build('first','a'*24);self.second=self.build('second','b'*24)
    def put(self,p,v):p.write_bytes(a.serial(v))
    def get(self,p):return json.loads(p.read_bytes())
    def build(self,name,token):
        base=self.root/'private/test_runs'/name;archive=base/'source_archive';archive.mkdir(parents=True)
        stage=base/'staged';(stage/'app/Saves').mkdir(parents=True);(stage/'profile').mkdir();(stage/'temp').mkdir()
        archives={}
        for k in ('launcher','collector','tests','v1_launcher'):
            p=archive/(k+self.paths[k].suffix);shutil.copyfile(self.paths[k],p);archives[k]=p
        stem='pe_resolver_phase_v2_'+token
        staged={k:stage/'app'/n for k,n in observer.safe.RUNTIME_NAMES.items()}
        staged.update(rom=stage/(stem+'.sfc'),state=stage/(stem+'.mss'),sram=stage/'app/Saves'/(stem+'.srm'),collector=stage/'collector.lua')
        for k,p in staged.items():shutil.copyfile(self.paths[k],p)
        receipt={'schema':observer.SCHEMA,'source_hashes':{k:a.sha(p.read_bytes()) for k,p in self.paths.items()},
          'staged_hashes':{k:a.sha(p.read_bytes()) for k,p in staged.items()},
          'source_archive_hashes':{k:a.sha(p.read_bytes()) for k,p in archives.items()},
          'source_archive_files':{k:p.name for k,p in archives.items()}}
        self.put(base/'launch_inputs.json',receipt);self.put(base/'trace.json',self.trace)
        process={'schema':observer.SCHEMA,'returncode':52,'exception':None};self.put(base/'process_receipt.json',process)
        summary=observer.summarize(self.trace,self.reference)
        self.put(base/'manifest.json',{**receipt,'evidence_level':'exploratory-runtime-not-accepted','observations':summary,
          'trace_sha256':a.sha((base/'trace.json').read_bytes()),'process_receipt_sha256':a.sha(a.serial(process)),
          'sources_staged_archives_unchanged':True,'checkpoint_load_only':True,
          'controller_schedule_reused':True,'rom_cpu_memory_edits':False,'production_approval':False})
        (base/'process.log').write_bytes(b'[CPU] Uninitialized memory read: original fixture\n')
        return base
    def call(self):return a.audit_pair(self.first,self.second)
    def reject(self,match='.'):
        with self.assertRaisesRegex((a.files.AuditError,observer.PhaseError),match):self.call()
    def mutate(self,name,fn):
        p=self.second/name;v=self.get(p);fn(v);self.put(p,v)
    def test_original_pair_full_semantics_and_metadata(self):
        v=self.call();self.assertTrue(v['full_trace_bytes_identical']);self.assertFalse(v['production_approval'])
        self.assertTrue(v['native_process_exit_receipts_checked'])
        self.assertEqual(v['runs'][0]['uninitialized_read_diagnostics'],1)
        self.assertEqual(v['runs'][0]['projection']['interrupt_entry_counts'],{'battle-irq':2,'normal-nmi':2})
        def walk(x):
            if isinstance(x,dict):
                self.assertFalse({'cpu','stack','gates','records','trampolines'}&set(x))
                for y in x.values():walk(y)
            elif isinstance(x,list):
                for y in x:walk(y)
        walk(v)
    def test_same_root(self):
        with self.assertRaisesRegex(a.files.AuditError,'distinct'):a.audit_pair(self.first,self.first)
    def test_outside_private_root(self):
        with self.assertRaisesRegex(a.files.AuditError,'private'):a.audit_pair(self.root/'tools',self.second)
    def test_nested_roots(self):
        child=self.first/'child';child.mkdir()
        with self.assertRaisesRegex(a.files.AuditError,'nested'):a.audit_pair(self.first,child)
    def test_host_error_marker(self):(self.second/'host_rejection.json').write_bytes(b'{}');self.reject('error marker')
    def test_native_error_marker(self):(self.second/'trace.json.error.txt').write_bytes(b'fixture');self.reject('error marker')
    def test_process_non_success(self):self.mutate('process_receipt.json',lambda v:v.update(returncode=93));self.reject('process')
    def test_process_bool(self):self.mutate('process_receipt.json',lambda v:v.update(returncode=True));self.reject('process')
    def test_process_exception(self):self.mutate('process_receipt.json',lambda v:v.update(exception='timeout'));self.reject('process')
    def test_process_version(self):self.mutate('process_receipt.json',lambda v:v.update(schema=observer.v1.SCHEMA));self.reject('process')
    def test_process_extra_claim(self):self.mutate('process_receipt.json',lambda v:v.update(verified=True));self.reject('process')
    def test_missing_process_receipt(self):(self.second/'process_receipt.json').unlink();self.reject('missing')
    def test_extra_archive(self):(self.second/'source_archive/extra.py').write_bytes(b'extra');self.reject('archive inventory')
    def test_archive_corruption(self):(self.second/'source_archive/launcher.bin').write_bytes(b'changed');self.reject('archive byte')
    def test_staged_collector_corruption(self):(self.second/'staged/collector.lua').write_bytes(b'changed');self.reject('staged byte')
    def test_extra_staged_save(self):(self.second/'staged/app/Saves/extra.srm').write_bytes(b'fixture');self.reject('save inventory')
    def test_missing_staged_state(self):next((self.second/'staged').glob('*.mss')).unlink();self.reject('stage inventory')
    def test_extra_stage_entry(self):(self.second/'staged/extra').write_bytes(b'fixture');self.reject('stage inventory')
    def test_stale_source_receipt(self):self.mutate('launch_inputs.json',lambda v:v['source_hashes'].update(launcher='0'*64));self.reject('prelaunch')
    def test_extra_receipt_key(self):self.mutate('launch_inputs.json',lambda v:v.update(accepted=True));self.reject('launch shape')
    def test_extra_manifest_key(self):self.mutate('manifest.json',lambda v:v.update(accepted=True));self.reject('manifest')
    def test_forged_summary(self):self.mutate('manifest.json',lambda v:v['observations'].update(record_count=1));self.reject('manifest')
    def test_forged_process_hash(self):self.mutate('manifest.json',lambda v:v.update(process_receipt_sha256='0'*64));self.reject('manifest')
    def test_promotion_flag(self):self.mutate('manifest.json',lambda v:v.update(production_approval=True));self.reject('manifest')
    def test_partial_json(self):(self.second/'trace.json').write_bytes(b'{');self.reject('partial')
    def test_duplicate_json(self):(self.second/'trace.json').write_bytes(b'{"schema":1,"schema":2}');self.reject('duplicate')
    def test_engine_key_missing_actual_trace_revalidation(self):
        self.mutate('trace.json',lambda v:v['records'][2]['engine'].pop('cpu.needNmi'));self.reject('engine')
    def test_missing_early_context_refuses_actual_validator(self):
        self.mutate('trace.json',lambda v:v.update(records=[r for r in v['records'] if r['context_id']!=1]));self.reject('historical')
    def test_trace_unchanged_hash_does_not_substitute_revalidation(self):
        self.mutate('trace.json',lambda v:v.update(error='failed'));self.reject('completion')
    def test_hardlinked_trace_refuses(self):
        p=self.second/'trace.json';p.unlink();os.link(self.first/'trace.json',p);self.reject('aliased')
    def test_hardlinked_process_receipt_refuses(self):
        p=self.second/'process_receipt.json';p.unlink();os.link(self.first/'process_receipt.json',p);self.reject('aliased')
    def test_valid_different_trace_pair_refuses(self):
        p=self.second/'trace.json';v=self.get(p);v['records'][0]['engine']['cpu.needNmi']=True;self.put(p,v)
        summary=observer.summarize(v,self.reference)
        self.mutate('manifest.json',lambda m:m.update(observations=summary,trace_sha256=a.sha(p.read_bytes())))
        self.reject('trace pair')
    def test_source_drift_is_rechecked(self):
        original=a.files.FileLedger.recheck
        def drift(ledger):self.paths['launcher'].write_bytes(b'drift');original(ledger)
        with mock.patch.object(a.files.FileLedger,'recheck',drift):self.reject('drift')
    def test_success_reads_without_native_execution(self):
        with mock.patch.object(observer.subprocess,'run',side_effect=AssertionError('native forbidden')):self.call()

class DirectContracts(unittest.TestCase):
    def test_frozen_observer_pins_match_actual_source(self):
        self.assertIs(a.observer_module(a.files.FileLedger()),observer)
    def test_current_source_drift_refuses_before_trace_reads(self):
        pins=copy.deepcopy(a.OBSERVER_PINS);name=next(iter(pins));pins[name]=(pins[name][0],'0'*64)
        with mock.patch.object(a,'OBSERVER_PINS',pins):
            with self.assertRaisesRegex(a.files.AuditError,'observer pin'):a.observer_module(a.files.FileLedger())
    def test_provisional_unfrozen_source_refuses(self):
        with mock.patch.object(a,'OBSERVER_PINS',{}):
            with self.assertRaisesRegex(a.files.AuditError,'not frozen'):a.observer_module(a.files.FileLedger())
    def test_selected_hardware_never_defaults_missing_field(self):
        trace,ref=specimen.specimen();summary=observer.summarize(trace,ref)
        row=next(r for r in trace['records'] if r['kind']=='resolver-entry');del row['engine']['cpu.needNmi']
        with self.assertRaises(KeyError):a.compact(trace,summary)
    def test_pending_false_is_not_future_absence_claim(self):
        trace,ref=specimen.specimen();v=a.compact(trace,observer.summarize(trace,ref))
        self.assertFalse(v['future_dma_absence_proved']);self.assertFalse(v['deadline_certified'])

if __name__=='__main__':unittest.main()
