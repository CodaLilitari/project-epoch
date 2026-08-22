from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "prepare_emulator_test_runs.py"
SPEC = importlib.util.spec_from_file_location(
    "prepare_emulator_test_runs", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class PrepareEmulatorTestRunsTests(unittest.TestCase):
    def test_normal_path_excludes_retired_unsafe_variant(self) -> None:
        specs = TOOL.variant_specs()
        self.assertEqual(tuple(spec[0] for spec in specs), ("static",))
        self.assertTrue(all(spec[3] == "none" for spec in specs))

    def test_retired_unsafe_variant_requires_explicit_opt_in(self) -> None:
        specs = TOOL.variant_specs(include_retired_unsafe=True)
        by_name = {spec[0]: spec for spec in specs}
        self.assertIn(TOOL.RETIRED_UNSAFE_VARIANT, by_name)
        self.assertEqual(
            by_name[TOOL.RETIRED_UNSAFE_VARIANT][3],
            "provisional",
        )


if __name__ == "__main__":
    unittest.main()
