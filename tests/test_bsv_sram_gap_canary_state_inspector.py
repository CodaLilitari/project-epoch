from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
CANARY_PATH = TOOLS / "inject_bsv_sram_gap_canary.py"
INSPECTOR_PATH = TOOLS / "inspect_bsv_sram_gap_canary_state.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CANARY = load_module("inject_bsv_sram_gap_canary", CANARY_PATH)
INSPECTOR = load_module(
    "bsv_sram_gap_canary_state_inspector",
    INSPECTOR_PATH,
)


def make_state() -> bytes:
    state = bytearray(CANARY.PINNED_STATE_LENGTH)
    state[:4] = b"BST1"
    gap_start = CANARY.PINNED_SRAM_STATE_OFFSET + CANARY.GAP_OFFSET
    state[gap_start : gap_start + CANARY.GAP_LENGTH] = CANARY.make_canary()
    return bytes(state)


class BsvSramGapCanaryStateInspectorTests(unittest.TestCase):
    def test_recognizes_exact_canary_and_matching_sram(self) -> None:
        baseline = make_state()
        result = INSPECTOR.inspect_state(
            baseline,
            baseline_state=baseline,
        )
        self.assertTrue(result["canary_matches"])
        self.assertTrue(result["sram_matches_baseline"])
        self.assertEqual(
            result["canary_occurrences"],
            [CANARY.PINNED_SRAM_STATE_OFFSET + CANARY.GAP_OFFSET],
        )

    def test_detects_gap_and_guard_changes(self) -> None:
        baseline = make_state()
        changed = bytearray(baseline)
        gap_start = CANARY.PINNED_SRAM_STATE_OFFSET + CANARY.GAP_OFFSET
        changed[gap_start + 3] ^= 0xFF
        changed[CANARY.PINNED_SRAM_STATE_OFFSET + 4] ^= 0xFF
        result = INSPECTOR.inspect_state(
            bytes(changed),
            baseline_state=baseline,
        )
        self.assertFalse(result["canary_matches"])
        self.assertFalse(result["sram_matches_baseline"])
        self.assertFalse(result["vanilla_region_matches_baseline"])
        self.assertFalse(result["gap_matches_baseline"])
        self.assertTrue(result["metadata_matches_baseline"])

    def test_extracts_embedded_state(self) -> None:
        state = make_state()
        movie = (
            b"BSV1"
            + struct.pack("<III", 0, 0, len(state))
            + state
            + bytes(12)
        )
        self.assertEqual(INSPECTOR.embedded_state(movie), state)

    def test_rejects_other_state_layout_or_wrapper(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pinned"):
            INSPECTOR.inspect_state(bytes(100))
        bad = bytearray(make_state())
        bad[:4] = b"NOPE"
        with self.assertRaisesRegex(RuntimeError, "BST1"):
            INSPECTOR.inspect_state(bytes(bad))


if __name__ == "__main__":
    unittest.main()
