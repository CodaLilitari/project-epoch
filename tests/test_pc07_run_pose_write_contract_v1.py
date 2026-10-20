"""Focused current-image guard checks; no historical validation chain."""
from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import pc07_run_pose_write_contract_v1 as contract
import validate_rom_write_intents as guard


class RunPoseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (contract.ROOT / contract.SOURCE["path"]).is_file():
            raise unittest.SkipTest("private accepted ROM fixture is not distributed")
        cls.context = contract.source_snapshot()
        cls.snap = cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__, None, None, None)
        cls.manifest = contract.template("private/test_runs/pc07_run_pose_test/diagnostic.sfc")

    def test_exact_minimal_delta_and_stream_isolation(self):
        result = guard.audit_pc07_run_pose_images(self.manifest, self.snap["source"], self.snap["target"])
        self.assertEqual(result["primary_frame_references_changed"], 8)
        self.assertTrue(result["inverse_restores_parent"])
        self.assertEqual(result["npc_protected_spans_unchanged"], 13)
        self.assertEqual(self.snap["streams"]["entrypoints_checked"], 1024)
        self.assertEqual(self.snap["source"][contract.PRIMARY:contract.PRIMARY + 24],
                         self.snap["target"][contract.PRIMARY:contract.PRIMARY + 24])

    def test_extra_changes_refused(self):
        for offset in (0, 0x240C00, 0x420000, 0x421000, 0x425118, 0x480400):
            with self.subTest(offset=hex(offset)):
                target = bytearray(self.snap["target"])
                target[offset] ^= 1
                with self.assertRaises(ValueError):
                    guard.audit_pc07_run_pose_images(self.manifest, self.snap["source"], bytes(target))

    def test_declared_extra_span_and_false_evidence_refused(self):
        for key, value in (("production_approval", True), ("native_execution", True),
                           ("sections", self.manifest["sections"] + [{"id": "extra"}])):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = value
            with self.assertRaises(ValueError):
                guard.validate_pc07_run_pose_manifest(manifest)

    def test_source_drift_refused(self):
        source = bytearray(self.snap["source"])
        source[0x480400] ^= 1
        with self.assertRaises(ValueError):
            guard.audit_pc07_run_pose_images(self.manifest, bytes(source), self.snap["target"])

    def test_output_escape_refused(self):
        for output in ("diagnostic.sfc", "private/test_runs/pc07_run_pose_test/../diagnostic.sfc",
                       "private/test_runs/pc07_run_pose_test/link/diagnostic.sfc"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                contract.output_path(output)


if __name__ == "__main__":
    unittest.main()
