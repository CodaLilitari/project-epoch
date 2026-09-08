"""Original metadata specimens; no native trace or private artifact dependency."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import collect_schala_package_helper_v4_rom_nmi_evidence as evidence


class HistoricalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='epoch-v4-metadata-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.sources={'one':self.root/'tools/one.py','two':self.root/'tools/two.py'}
        for key,path in self.sources.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(('original host metadata specimen '+key+'\n').encode())
        self.directory=self.root/'private/test_runs'/(evidence.PREFIX+'specimen')
        self.archive=self.directory/'source_archive';self.archive.mkdir(parents=True)
        for path in self.sources.values():(self.archive/path.name).write_bytes(path.read_bytes())
        self.receipt={'source_hashes':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in self.sources.items()}}
        self.receipt['source_archive_hashes']=dict(self.receipt['source_hashes'])
        self.save_receipt()
        (self.directory/'trace.json').write_bytes(b'{"original_host_specimen":true}\n')
        (self.directory/'case_contract.json').write_bytes(b'[]\n')
        (self.directory/'staged').mkdir()
        (self.directory/'staged/collector.lua').write_bytes(b'-- original metadata specimen\n')
        (self.directory/'host_rejection.json').write_bytes(b'{"status":"original rejected host specimen"}\n')
        history=(('specimen','Original host-only history specimen',hashlib.sha256((self.directory/'trace.json').read_bytes()).hexdigest(),None,
            hashlib.sha256((self.directory/'launch_inputs.json').read_bytes()).hexdigest(),
            hashlib.sha256((self.directory/'host_rejection.json').read_bytes()).hexdigest()),)
        for target,value in (('ROOT',self.root),('HISTORY',history)):
            handle=patch.object(evidence,target,value);handle.start();self.addCleanup(handle.stop)
        handle=patch.object(evidence,'source_paths',return_value=self.sources);handle.start();self.addCleanup(handle.stop)
        handle=patch.object(evidence,'checked',side_effect=lambda p:p);handle.start();self.addCleanup(handle.stop)
        handle=patch.object(evidence,'read_json',side_effect=lambda p,**_:json.loads(p.read_bytes()));handle.start();self.addCleanup(handle.stop)

    def save_receipt(self):
        (self.directory/'launch_inputs.json').write_text(json.dumps(self.receipt),encoding='utf-8')

    def refuses(self):
        with self.assertRaises(evidence.v.ConformanceError):evidence.history_metadata()

    def test_exact_original_two_file_history_accepts(self):
        result=evidence.history_metadata()
        self.assertEqual(len(result),1)
        self.assertEqual(len(result[0]['source_archive']),2)

    def test_empty_archive_refuses(self):
        original=Path.iterdir
        with patch.object(Path,'iterdir',lambda path:iter(()) if path==self.archive else original(path)):
            self.refuses()

    def test_one_missing_archive_file_refuses(self):
        (self.archive/'two.py').unlink();self.refuses()

    def test_extra_archive_file_refuses(self):
        (self.archive/'extra.py').write_bytes(b'original extra specimen');self.refuses()

    def test_empty_archive_receipt_refuses(self):
        self.receipt['source_archive_hashes']={};self.save_receipt();self.refuses()

    def test_unknown_archive_receipt_key_refuses(self):
        self.receipt['source_archive_hashes']['unknown']='0'*64;self.save_receipt();self.refuses()

    def test_changed_archived_bytes_refuse(self):
        (self.archive/'one.py').write_bytes(b'changed original host specimen');self.refuses()

    def test_archive_and_guarded_receipt_disagreement_refuses(self):
        self.receipt['source_archive_hashes']['one']='0'*64;self.save_receipt();self.refuses()

    def test_rejected_history_cannot_gain_manifest(self):
        (self.directory/'manifest.json').write_bytes(b'{}\n');self.refuses()

    def test_prepared_receipt_byte_drift_refuses_even_if_json_is_unchanged(self):
        path=self.directory/'launch_inputs.json';path.write_bytes(path.read_bytes()+b'\n');self.refuses()

    def test_prepared_receipt_cannot_disappear(self):
        (self.directory/'launch_inputs.json').unlink()
        with self.assertRaises(FileNotFoundError):evidence.history_metadata()

    def test_rejection_receipt_byte_drift_refuses(self):
        path=self.directory/'host_rejection.json';path.write_bytes(path.read_bytes()+b' ');self.refuses()

    def test_rejection_receipt_cannot_disappear(self):
        (self.directory/'host_rejection.json').unlink()
        with self.assertRaises(FileNotFoundError):evidence.history_metadata()


class BoundedJsonReadTests(unittest.TestCase):
    def test_tiny_receipt_uses_its_extent_not_the_one_gib_ceiling(self):
        with tempfile.TemporaryDirectory(prefix='epoch-v4-json-') as directory:
            path=Path(directory)/'original-receipt.json';path.write_bytes(b'{}')
            with patch.object(evidence,'checked',side_effect=lambda p:p),patch.object(
                evidence.v.SAFE,'read_direct_regular_file',return_value=b'{}') as reader:
                self.assertEqual(evidence.read_json(path),{})
                self.assertEqual(reader.call_args.kwargs['maximum'],2)

    def test_declared_size_ceiling_still_refuses_before_read(self):
        with tempfile.TemporaryDirectory(prefix='epoch-v4-json-') as directory:
            path=Path(directory)/'original-receipt.json';path.write_bytes(b'{}')
            with patch.object(evidence,'checked',side_effect=lambda p:p),patch.object(
                evidence.v.SAFE,'read_direct_regular_file') as reader:
                with self.assertRaises(evidence.v.ConformanceError):evidence.read_json(path,maximum=1)
                reader.assert_not_called()


class ProtocolLabelProjectionTests(unittest.TestCase):
    def specimen(self,root):
        old='project-epoch-package-helper-v4-rom-nmi-calibrated-v2'
        prefix=('{"schema":"'+old+'","records":[').encode()
        suffix=('{"original_metadata_specimen":"'+old+'"}],"error":null}\n').encode()
        path=root/'original-trace.json';path.write_bytes(prefix+suffix)
        return path,old,suffix

    def test_only_initial_protocol_header_changes(self):
        with tempfile.TemporaryDirectory(prefix='epoch-v4-projection-') as directory:
            root=Path(directory);path,old,suffix=self.specimen(root)
            with patch.object(evidence,'ROOT',root),patch.object(evidence,'checked',side_effect=lambda p:p):
                result=evidence.protocol_label_projection(path,hashlib.sha256(path.read_bytes()).hexdigest())
            expected=('{"schema":"'+evidence.v.SCHEMA+'","records":[').encode()+suffix
            self.assertEqual(result['projected_sha256'],hashlib.sha256(expected).hexdigest())
            self.assertIn(old.encode(),suffix)

    def test_original_hash_drift_refuses(self):
        with tempfile.TemporaryDirectory(prefix='epoch-v4-projection-') as directory:
            root=Path(directory);path,_,_=self.specimen(root)
            with patch.object(evidence,'ROOT',root),patch.object(evidence,'checked',side_effect=lambda p:p):
                with self.assertRaises(evidence.v.ConformanceError):evidence.protocol_label_projection(path,'0'*64)

    def test_unexpected_initial_header_refuses(self):
        with tempfile.TemporaryDirectory(prefix='epoch-v4-projection-') as directory:
            root=Path(directory);path,_,_=self.specimen(root);path.write_bytes(b' '+path.read_bytes())
            with patch.object(evidence,'ROOT',root),patch.object(evidence,'checked',side_effect=lambda p:p):
                with self.assertRaises(evidence.v.ConformanceError):
                    evidence.protocol_label_projection(path,hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
