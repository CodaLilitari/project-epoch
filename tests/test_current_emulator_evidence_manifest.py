from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "build_current_emulator_evidence_manifest.py"


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "current_emulator_manifest", TOOL_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


class CurrentEmulatorManifestTests(unittest.TestCase):
    def test_manifest_is_sorted_hashed_and_classified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "roms").mkdir()
            (root / "roms" / "clean.sfc").write_bytes(b"rom")
            (root / "field_canary.bsv").write_bytes(b"movie")
            (root / "run.log").write_bytes(b"log")

            manifest = TOOL.build_manifest(root)
            artifacts = manifest["artifacts"]

        self.assertEqual(
            [entry["path"] for entry in artifacts],
            ["field_canary.bsv", "roms/clean.sfc", "run.log"],
        )
        self.assertEqual(
            [entry["evidence_level"] for entry in artifacts],
            ["verified-runtime", "test-fixture", "verified-runtime"],
        )
        self.assertTrue(all(len(entry["sha256"]) == 64 for entry in artifacts))

    def test_excludes_requested_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            output = root / "manifest.json"
            output.write_bytes(b"old")
            (root / "input.log").write_bytes(b"log")
            manifest = TOOL.build_manifest(root, excluded={output})

        self.assertEqual(
            [entry["path"] for entry in manifest["artifacts"]],
            ["input.log"],
        )

    def test_curated_manifest_includes_only_accepted_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "accepted.state.auto").write_bytes(b"accepted")
            (root / "exploratory.state.auto").write_bytes(b"exploratory")
            manifest = TOOL.build_manifest(
                root,
                accepted=[
                    {
                        "path": "accepted.state.auto",
                        "evidence_level": "verified-runtime",
                        "reproduction_group": "play-replay",
                    }
                ],
                acceptance_spec_sha256="a" * 64,
            )

        self.assertTrue(manifest["curated"])
        self.assertEqual(
            manifest["schema"],
            "project-epoch-current-emulator-evidence-v2",
        )
        self.assertEqual(manifest["acceptance_spec_sha256"], "a" * 64)
        self.assertEqual(
            [entry["path"] for entry in manifest["artifacts"]],
            ["accepted.state.auto"],
        )
        self.assertEqual(
            manifest["artifacts"][0]["status"], "accepted"
        )

    def test_acceptance_spec_rejects_traversal_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            traversal = root / "traversal.json"
            traversal.write_text(
                json.dumps(
                    {
                        "schema": "project-epoch-emulator-acceptance-v1",
                        "artifacts": [
                            {
                                "path": "../outside",
                                "evidence_level": "verified-runtime",
                                "reproduction_group": "play-replay",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "relative"):
                TOOL.load_acceptance_spec(traversal)

            duplicate = root / "duplicate.json"
            duplicate.write_text(
                json.dumps(
                    {
                        "schema": "project-epoch-emulator-acceptance-v1",
                        "artifacts": [
                            {
                                "path": "same.log",
                                "evidence_level": "verified-runtime",
                                "reproduction_group": "play-replay",
                            },
                            {
                                "path": "same.log",
                                "evidence_level": "verified-runtime",
                                "reproduction_group": "play-replay",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                TOOL.load_acceptance_spec(duplicate)

    def test_curated_manifest_rejects_missing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
                TOOL.build_manifest(
                    root,
                    accepted=[
                        {
                            "path": "missing.bsv",
                            "evidence_level": "verified-runtime",
                            "reproduction_group": "edit-replay",
                        }
                    ],
                )


if __name__ == "__main__":
    unittest.main()
