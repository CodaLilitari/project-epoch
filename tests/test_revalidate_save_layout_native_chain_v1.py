"""Read-only integrity/lineage tests for the frozen accepted native chain."""
from pathlib import Path
import json
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import revalidate_save_layout_native_chain_v1 as audit


class ChainTests(unittest.TestCase):
    def test_reference_omission_rejected_before_artifact_access(self):
        ref=json.loads(audit.REFERENCE.read_bytes())
        ref["artifact_inventory"].pop()
        with mock.patch.object(audit,"checked_path") as access:
            with self.assertRaises(audit.ChainError): audit.read_reference(json.dumps(ref).encode())
            access.assert_not_called()

    def test_reference_duplicate_rejected_before_artifact_access(self):
        ref=json.loads(audit.REFERENCE.read_bytes())
        ref["artifact_inventory"].append(ref["artifact_inventory"][0])
        with mock.patch.object(audit,"checked_path") as access:
            with self.assertRaises(audit.ChainError): audit.read_reference(json.dumps(ref).encode())
            access.assert_not_called()

    def test_metadata_hash_cannot_substitute_for_actual_pair_equality(self):
        ref={"byte_equality_groups":[["first","second"]]}
        with self.assertRaises(audit.ChainError): audit.verify_equal_groups(ref,{"first":b"a","second":b"b"})

    def test_mid_audit_drift_rejected(self):
        ref={"artifact_inventory":[["private/example",1,audit.sha(b"a")]]}
        path=mock.Mock(); path.read_bytes.return_value=b"b"
        with mock.patch.object(audit,"checked_path",return_value=path):
            with self.assertRaises(audit.ChainError): audit.recheck_artifacts(ref,{"private/example":b"a"})

    def test_duplicate_json_and_path_escape_rejected(self):
        with self.assertRaises(audit.ChainError): audit.decode(b'{"a":1,"a":2}')
        with self.assertRaises(audit.ChainError): audit.checked_path("../outside")

    @unittest.skipUnless((audit.ROOT/audit.BASE/audit.RUNS["save"][0]/"trace.jsonl").exists(),
                         "exact private accepted chain unavailable")
    def test_complete_accepted_chain_read_only(self):
        result=audit.audit()
        self.assertEqual(result["artifact_count"],150)
        self.assertEqual(result["byte_equality_group_count"],53)
        self.assertEqual(result["save_pair"]["records"],18039)
        self.assertEqual(result["load_pair"]["records"],7524)
        self.assertEqual(result["produced_sram_sha256"],result["load_pair"]["entry_sram_sha256"])
        self.assertFalse(result["native_execution_performed"])
        self.assertFalse(result["image_emitted"])
        self.assertFalse(result["review_status_at_reference_creation"]["final_external_approval_claimed"])


if __name__=="__main__": unittest.main()
