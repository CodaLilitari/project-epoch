from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "compare_bsnes2014_states.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("compare_bsnes2014_states", TOOL_PATH)


def make_state(fill: int = 0) -> bytearray:
    state = bytearray([fill]) * TOOL.PINNED_STATE_LENGTH
    state[:4] = b"BST1"
    return state


class CompareBsnes2014StatesTests(unittest.TestCase):
    def test_accepts_identity_and_learned_control_differences(self) -> None:
        baseline = make_state()
        repeated = bytearray(baseline)
        candidate = bytearray(baseline)
        repeated[0x2260] = 1
        candidate[0x2260] = 2
        candidate[TOOL.ROM_ID_START : TOOL.ROM_ID_START + 3] = b"abc"

        result = TOOL.compare_with_control(
            bytes(baseline), bytes(repeated), bytes(candidate)
        )

        self.assertTrue(result["equivalent_at_checkpoint"])
        self.assertTrue(result["wram_identical"])
        self.assertEqual(result["unexplained_payload_difference_count"], 0)

    def test_rejects_unexplained_payload_difference(self) -> None:
        baseline = make_state()
        repeated = bytearray(baseline)
        candidate = bytearray(baseline)
        repeated[0x2260] = 1
        candidate[0x3000] = 1

        result = TOOL.compare_with_control(
            bytes(baseline), bytes(repeated), bytes(candidate)
        )

        self.assertFalse(result["equivalent_at_checkpoint"])
        self.assertEqual(
            result["unexplained_payload_difference_ranges"],
            ["0x3000-0x3000"],
        )

    def test_rejects_wram_difference_even_if_control_also_varies_there(
        self,
    ) -> None:
        baseline = make_state()
        repeated = bytearray(baseline)
        candidate = bytearray(baseline)
        target = TOOL.PINNED_WRAM_STATE_OFFSET + 0x1234
        repeated[target] = 1
        candidate[target] = 2

        result = TOOL.compare_with_control(
            bytes(baseline), bytes(repeated), bytes(candidate)
        )

        self.assertFalse(result["equivalent_at_checkpoint"])
        self.assertFalse(result["wram_identical"])

    def test_accepts_candidate_that_exactly_matches_repeated_payload(
        self,
    ) -> None:
        baseline = make_state()
        repeated = bytearray(baseline)
        candidate = bytearray(baseline)
        targets = [
            TOOL.PINNED_WRAM_STATE_OFFSET + 0x1234,
            0x30000,
        ]
        for target in targets:
            repeated[target] = 7
            candidate[target] = 7
        candidate[TOOL.ROM_ID_START : TOOL.ROM_ID_START + 3] = b"abc"

        result = TOOL.compare_with_control(
            bytes(baseline), bytes(repeated), bytes(candidate)
        )

        self.assertTrue(result["equivalent_at_checkpoint"])
        self.assertTrue(result["payload_matches_repeated_baseline"])
        self.assertTrue(result["wram_matches_repeated_baseline"])
        self.assertTrue(result["matches_one_control_run_ignoring_identity"])

    def test_formats_contiguous_ranges(self) -> None:
        self.assertEqual(
            TOOL.format_ranges({1, 2, 3, 7, 9, 10}),
            ["0x1-0x3", "0x7-0x7", "0x9-0xA"],
        )

    def test_rejects_wrong_length_or_magic(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "length"):
            TOOL.validate_state(b"BST1")
        wrong_magic = bytes(make_state())[4:] + b"\x00\x00\x00\x00"
        with self.assertRaisesRegex(RuntimeError, "BST1"):
            TOOL.validate_state(wrong_magic)


if __name__ == "__main__":
    unittest.main()
