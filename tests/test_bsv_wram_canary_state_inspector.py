from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
CANARY_PATH = TOOLS / "inject_bsv_wram_canary.py"
INSPECTOR_PATH = TOOLS / "inspect_bsv_wram_canary_state.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CANARY = load_module("inject_bsv_wram_canary", CANARY_PATH)
INSPECTOR = load_module("bsv_wram_canary_state_inspector", INSPECTOR_PATH)


class BsvWramCanaryStateInspectorTests(unittest.TestCase):
    def make_state(self, *, intact: bool = True) -> bytes:
        state = bytearray(CANARY.PINNED_STATE_LENGTH)
        start = CANARY.PINNED_WRAM_STATE_OFFSET + CANARY.TARGET_WRAM_OFFSET
        state[start : start + CANARY.TARGET_LENGTH] = CANARY.make_canary()
        if not intact:
            state[start + 7] ^= 0xFF
        return bytes(state)

    def test_recognizes_exact_canary(self) -> None:
        result = INSPECTOR.inspect_state(self.make_state())
        self.assertTrue(result["canary_matches"])
        self.assertEqual(
            result["canary_occurrences"],
            [
                CANARY.PINNED_WRAM_STATE_OFFSET
                + CANARY.TARGET_WRAM_OFFSET
            ],
        )

    def test_detects_corruption(self) -> None:
        result = INSPECTOR.inspect_state(self.make_state(intact=False))
        self.assertFalse(result["canary_matches"])
        self.assertFalse(result["target_all_zero"])
        self.assertEqual(result["canary_occurrences"], [])

    def test_recognizes_cleared_candidate_block(self) -> None:
        state = bytearray(CANARY.PINNED_STATE_LENGTH)
        result = INSPECTOR.inspect_state(bytes(state))
        self.assertFalse(result["canary_matches"])
        self.assertTrue(result["target_all_zero"])

    def test_rejects_other_state_layout(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pinned"):
            INSPECTOR.inspect_state(bytes(100))


if __name__ == "__main__":
    unittest.main()
