from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def load_module(
    name: str,
    filename: str,
    *,
    directory: pathlib.Path = TOOLS,
):
    path = directory / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FIXTURE = load_module(
    "test_bsv2_wram_canary",
    "test_bsv2_wram_canary.py",
    directory=ROOT / "tests",
)
INJECTOR = load_module(
    "inject_bsv2_wram_canary",
    "inject_bsv2_wram_canary.py",
)
LEGACY = load_module(
    "inject_bsv_wram_canary",
    "inject_bsv_wram_canary.py",
)
TOOL = load_module(
    "compare_current_wram_canary_pair",
    "compare_current_wram_canary_pair.py",
)
EDITOR = load_module(
    "edit_retroarch_bsv2_inputs",
    "edit_retroarch_bsv2_inputs.py",
)


class CompareCurrentWramCanaryPairTests(unittest.TestCase):
    def test_accepts_exact_matched_pair(self) -> None:
        zero, sram, base = FIXTURE.make_fixture()
        with_canary, _, target = INJECTOR.inject_canary(zero, sram)
        result = TOOL.compare_pair(with_canary, zero, sram)

        self.assertTrue(result["equivalent_except_canary"])
        self.assertEqual(result["state_wram_base"], base)
        self.assertEqual(result["target_state_offset"], target)
        self.assertEqual(result["target_length"], LEGACY.TARGET_LENGTH)
        self.assertEqual(result["difference_count"], LEGACY.TARGET_LENGTH)
        self.assertEqual(result["difference_start"], target)
        self.assertEqual(
            result["difference_end_exclusive"],
            target + LEGACY.TARGET_LENGTH,
        )
        self.assertEqual(
            result["normalized_canary_core_sha256"],
            result["zero_core_sha256"],
        )

    def test_rejects_any_noncanary_drift_and_bad_zero_guard(self) -> None:
        zero, sram, base = FIXTURE.make_fixture()
        with_canary, _, _ = INJECTOR.inject_canary(zero, sram)

        drifted_core = bytearray(
            INJECTOR.extract_raw_initial_core_state(with_canary)
        )
        drifted_core[base + 0x100] ^= 0x01
        drifted = EDITOR.replace_initial_core_state(
            with_canary,
            bytes(drifted_core),
        )
        with self.assertRaisesRegex(RuntimeError, "outside or incompletely"):
            TOOL.compare_pair(drifted, zero, sram)

        guarded_core = bytearray(
            INJECTOR.extract_raw_initial_core_state(zero)
        )
        guarded_core[
            base + LEGACY.TARGET_WRAM_OFFSET - 1
        ] = 0x01
        guarded = EDITOR.replace_initial_core_state(
            zero,
            bytes(guarded_core),
        )
        with self.assertRaisesRegex(RuntimeError, "zero state fails"):
            TOOL.compare_pair(with_canary, guarded, sram)


if __name__ == "__main__":
    unittest.main()
