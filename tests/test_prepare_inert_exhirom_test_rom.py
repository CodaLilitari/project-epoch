from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SCAFFOLD_PATH = TOOLS / "schala_rom_scaffold.py"
PREPARE_PATH = TOOLS / "prepare_inert_exhirom_test_rom.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load_module("schala_rom_scaffold", SCAFFOLD_PATH)
TOOL = load_module("prepare_inert_exhirom_test_rom", PREPARE_PATH)


class PrepareInertExHiRomTests(unittest.TestCase):
    def test_accepts_private_sfc_path(self) -> None:
        path = ROOT / "private" / "test_runs" / "example.sfc"
        self.assertEqual(TOOL.validate_private_output(path), path.resolve())

    def test_rejects_output_outside_private(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "private"):
            TOOL.validate_private_output(ROOT / "output" / "example.sfc")

    def test_rejects_non_rom_suffix(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "sfc"):
            TOOL.validate_private_output(
                ROOT / "private" / "test_runs" / "example.bin"
            )

    def test_write_passes_explicit_diagnostic_source_hash(self) -> None:
        private_root = ROOT / "private"
        private_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_root) as directory:
            root = pathlib.Path(directory)
            source = root / "diagnostic.sfc"
            output = root / "expanded.sfc"
            source.write_bytes(b"diagnostic")
            with mock.patch.object(
                TOOL.schala_rom_scaffold,
                "expand_exhirom_scaffold",
                return_value=b"expanded",
            ) as expand:
                target, resolved = TOOL.write_inert_test_rom(
                    source,
                    output,
                    expected_source_sha1="abc123",
                )

            expand.assert_called_once_with(
                b"diagnostic",
                expected_sha1="abc123",
            )
            self.assertEqual(target, b"expanded")
            self.assertEqual(resolved, output.resolve())
            self.assertEqual(output.read_bytes(), b"expanded")


if __name__ == "__main__":
    unittest.main()
