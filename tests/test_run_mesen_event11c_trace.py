from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

from tests.test_mesen_event11c_trace import make_trace


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "run_mesen_event11c_trace.py"


def load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_module("run_mesen_event11c_trace", TOOL_PATH)


class RunMesenEvent11cTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        TOOL.PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)

    def test_source_collector_hash_is_pinned(self) -> None:
        self.assertEqual(
            TOOL.sha256_file(TOOL.COLLECTOR),
            TOOL.EXPECTED_HASHES["collector"],
        )

    def test_expected_outputs_match_public_acceptance_contract(self) -> None:
        contract_path = (
            ROOT
            / "references"
            / "mesen_event11c_trace_accepted_artifacts_v1.json"
        )
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        actual: dict[tuple[str, str], dict[str, tuple[int, str]]] = {}
        for entry in contract["artifacts"]:
            parts = Path(entry["path"]).parts
            profile, variant, filename = parts
            kind = "trace" if filename == "trace.json" else "screenshot"
            actual.setdefault((profile, variant), {})[kind] = (
                entry["size"],
                entry["sha256"],
            )
        self.assertEqual(actual, TOOL.EXPECTED_OUTPUTS)

    def test_artifact_hash_gate_rejects_nonaccepted_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "endpoint.png"
            path.write_bytes(b"not an accepted image")
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "does not match accepted artifact",
            ):
                TOOL.require_artifact(
                    path,
                    TOOL.EXPECTED_OUTPUTS[("frog-robo", "zero")][
                        "screenshot"
                    ],
                    "endpoint PNG",
                )

    def test_private_snapshot_records_size_and_hash(self) -> None:
        with tempfile.TemporaryDirectory(dir=TOOL.PRIVATE_ROOT) as directory:
            root = Path(directory)
            (root / "safe.bin").write_bytes(b"safe")
            snapshot = TOOL.snapshot_private_files(root)
            self.assertEqual(snapshot["safe.bin"][0], 4)

    def test_existing_file_outside_workspace_private_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(delete=True) as handle:
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError, "resolves outside"
            ):
                TOOL.resolve_private_file(handle.name, "test input")

    def test_output_path_outside_workspace_private_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "private" / "looks-private"
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError, "resolves outside"
            ):
                TOOL.prepare_private_output_dir(candidate)

    def test_existing_or_dangling_output_path_is_rejected(self) -> None:
        candidate = TOOL.PRIVATE_ROOT / "synthetic-dangling-output"
        with mock.patch.object(TOOL.os.path, "lexists", return_value=True):
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "must be a new path",
            ):
                TOOL.prepare_private_output_dir(candidate)

    def test_output_path_cannot_overlap_protected_save_tree(self) -> None:
        with tempfile.TemporaryDirectory(dir=TOOL.PRIVATE_ROOT) as directory:
            save_root = Path(directory) / "Saves"
            save_root.mkdir()
            output = save_root / "trace-run"
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "overlaps protected tree",
            ):
                TOOL.prepare_private_output_dir(
                    output,
                    forbidden_roots=(save_root,),
                )
            self.assertFalse(TOOL.os.path.lexists(output))

    def test_trace_loader_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory(dir=TOOL.PRIVATE_ROOT) as directory:
            trace_path = Path(directory) / "trace.json"
            trace_path.write_text(
                '{"schema":"first","schema":"second"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError, "duplicate JSON key"
            ):
                TOOL.load_trace(trace_path, "frog-robo", "zero")

    def test_trace_loader_accepts_only_clean_success(self) -> None:
        trace = make_trace("frog-robo", "zero")
        with tempfile.TemporaryDirectory(dir=TOOL.PRIVATE_ROOT) as directory:
            trace_path = Path(directory) / "trace.json"
            trace_path.write_text(json.dumps(trace), encoding="utf-8")
            loaded = TOOL.load_trace(trace_path, "frog-robo", "zero")
        self.assertEqual(len(loaded["callbacks"]), 3)

    def test_trace_loader_rejects_failed_termination(self) -> None:
        trace = make_trace("frog-robo", "zero")
        trace["termination"]["success"] = False
        with tempfile.TemporaryDirectory(dir=TOOL.PRIVATE_ROOT) as directory:
            trace_path = Path(directory) / "trace.json"
            trace_path.write_text(json.dumps(trace), encoding="utf-8")
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError, "strict trace validation failed"
            ):
                TOOL.load_trace(trace_path, "frog-robo", "zero")

    def test_failed_staging_copy_does_not_touch_shared_mesen_saves(self) -> None:
        TOOL.PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TOOL.PRIVATE_ROOT) as directory:
            fixture_root = Path(directory)
            app_root = fixture_root / "tools" / "mesen2" / "app"
            save_root = app_root / "Saves"
            save_root.mkdir(parents=True)
            for name in (
                "Mesen.exe",
                "MesenCore.dll",
                "libHarfBuzzSharp.dll",
                "libSkiaSharp.dll",
                "MesenNesDB.txt",
                "settings.json",
            ):
                (app_root / name).write_bytes(b"synthetic fixture\n")
            archive = app_root.parent / "Mesen_2.1.1_Windows.zip"
            archive.write_bytes(b"synthetic archive\n")
            rom = fixture_root / "input.sfc"
            state = fixture_root / "checkpoint.mss"
            sram = fixture_root / "input.srm"
            rom.write_bytes(b"synthetic ROM\n")
            state.write_bytes(b"synthetic state\n")
            sram.write_bytes(b"synthetic SRAM\n")
            sentinel = save_root / "unrelated.srm"
            sentinel.write_bytes(b"must remain exact\n")
            before = TOOL.sha256_file(sentinel)
            output_dir = fixture_root / "output"
            parser = TOOL.build_parser()
            args = parser.parse_args(
                [
                    "--profile",
                    "frog-robo",
                    "--variant",
                    "zero",
                    "--output-dir",
                    str(output_dir),
                    "--mesen",
                    str(app_root / "Mesen.exe"),
                    "--rom",
                    str(rom),
                    "--state",
                    str(state),
                    "--sram",
                    str(sram),
                ]
            )
            with mock.patch.object(TOOL, "require_hash", return_value="fixture"):
                with mock.patch.object(
                    TOOL.shutil,
                    "copyfile",
                    side_effect=OSError("injected copy failure"),
                ):
                    with self.assertRaisesRegex(OSError, "injected copy failure"):
                        TOOL.run(args)
            self.assertEqual(TOOL.sha256_file(sentinel), before)
            self.assertEqual(
                [path.name for path in save_root.iterdir()],
                ["unrelated.srm"],
            )


if __name__ == "__main__":
    unittest.main()
