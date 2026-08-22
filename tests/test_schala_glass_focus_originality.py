from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "audit_schala_glass_focus_originality.py"
REPORT_PATH = ROOT / "references" / "schala_glass_focus_originality_v0.json"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_glass_focus_originality", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class GlassFocusOriginalityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_contract_pins_twelve_assets_and_bounded_counts(self) -> None:
        candidate = self.expected["candidate_scope"]
        reference = self.expected["reference_scope"]
        self.assertEqual(candidate["asset_count"], 12)
        self.assertEqual(len(candidate["asset_ids"]), 12)
        self.assertEqual(candidate["tile_occurrence_count"], 174)
        self.assertEqual(candidate["excluded_tile_occurrence_count"], 80)
        self.assertEqual(candidate["compared_tile_occurrence_count"], 94)
        self.assertEqual(reference["tile_count"], 7264)
        self.assertEqual(reference["excluded_trivial_tile_count"], 59)
        self.assertEqual(reference["compared_tile_count"], 7205)
        self.assertEqual(
            self.expected["results"],
            {
                "exact_index_match_count": 0,
                "visible_pattern_match_count": 0,
            },
        )

    def test_contract_pins_source_tool_command_and_transforms(self) -> None:
        self.assertEqual(
            self.expected["canonical_source"]["sha256"],
            TOOL.sha256(TOOL.SOURCE_PATH.read_bytes()),
        )
        self.assertEqual(
            self.expected["tool"]["sha256"],
            TOOL.sha256(TOOL_PATH.read_bytes()),
        )
        self.assertEqual(
            self.expected["reproduction"], TOOL.REPRODUCTION_COMMAND
        )
        self.assertEqual(
            self.expected["comparison_policy"]["transforms"],
            list(TOOL.TRANSFORMS),
        )

    def test_contract_denies_npc_and_output_claims(self) -> None:
        self.assertIs(self.expected["npc_originality_claimed"], False)
        self.assertIs(self.expected["files_emitted"], False)
        self.assertIn(
            "does not cover NPC",
            self.expected["reference_scope"]["coverage_limit"],
        )
        serialized = json.dumps(self.expected, sort_keys=True).lower()
        for forbidden_key in (
            '"raw_bytes"',
            '"decoded_pixels"',
            '"image_data"',
            '"output_path"',
        ):
            self.assertNotIn(forbidden_key, serialized)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_build_report_exactly_reproduces_contract(self) -> None:
        self.assertEqual(TOOL.build_report(ROM_PATH), self.expected)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_stdout_command_exactly_reproduces_contract(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--rom", str(ROM_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        self.assertEqual(completed.stdout, REPORT_PATH.read_bytes())
        self.assertEqual(completed.stderr, b"")

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_reproduction_does_not_read_existing_report(self) -> None:
        original_read_bytes = pathlib.Path.read_bytes

        def guarded_read_bytes(path: pathlib.Path) -> bytes:
            if path.resolve() == REPORT_PATH.resolve():
                raise AssertionError("wrapper read its existing output")
            return original_read_bytes(path)

        with mock.patch.object(
            pathlib.Path, "read_bytes", guarded_read_bytes
        ), mock.patch.object(
            TOOL.focus,
            "verify_manifest",
            side_effect=AssertionError(
                "wrapper invoked full self-dependent verification"
            ),
        ), mock.patch.object(
            TOOL.focus,
            "verify_originality_report_file",
            side_effect=AssertionError(
                "wrapper invoked originality-output verification"
            ),
        ):
            self.assertEqual(TOOL.build_report(ROM_PATH), self.expected)

    def test_full_validator_rejects_stale_report_bytes(self) -> None:
        source_raw, source = TOOL.focus.load_json(TOOL.SOURCE_PATH)
        source_report = TOOL.focus.validation_report(source_raw, source)
        _, manifest = TOOL.focus.load_json(TOOL.MANIFEST_PATH)
        original_read_bytes = pathlib.Path.read_bytes

        def stale_report_bytes(path: pathlib.Path) -> bytes:
            if path.resolve() == REPORT_PATH.resolve():
                return b'{"stale":true}\n'
            return original_read_bytes(path)

        with mock.patch.object(
            pathlib.Path, "read_bytes", stale_report_bytes
        ), self.assertRaisesRegex(
            TOOL.focus.FocusSourceError, "originality report file drifted"
        ):
            TOOL.focus.verify_manifest(
                manifest, source_raw, source_report
            )

    def test_wrong_rom_is_rejected_before_any_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wrong = pathlib.Path(directory) / "wrong.sfc"
            wrong.write_bytes(b"\x00" * TOOL.pc_audit.CANONICAL_ROM_SIZE)
            with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                TOOL.build_report(wrong)

    def test_count_drift_fails_closed(self) -> None:
        drifted = dict(TOOL.EXPECTED_COUNTS)
        drifted["compared_candidate_tile_count"] += 1
        with self.assertRaises(TOOL.GlassFocusOriginalityError):
            TOOL._require_expected_counts(drifted)

    def test_cli_exposes_no_source_or_output_destination(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--rom", completed.stdout)
        self.assertNotIn("--source", completed.stdout)
        self.assertNotIn("--output", completed.stdout)


if __name__ == "__main__":
    unittest.main()
