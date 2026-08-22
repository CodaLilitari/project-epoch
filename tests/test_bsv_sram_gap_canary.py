from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "inject_bsv_sram_gap_canary.py"

SPEC = importlib.util.spec_from_file_location("bsv_sram_gap_canary", TOOL_PATH)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def make_movie(state: bytes, inputs: bytes = b"") -> bytes:
    return (
        b"BSV1"
        + struct.pack("<III", 0, 0x12345678, len(state))
        + state
        + inputs
    )


class BsvSramGapCanaryTests(unittest.TestCase):
    def test_edits_only_candidate_gap(self) -> None:
        sram = bytes((index * 29 + 7) & 0xFF for index in range(0x2000))
        prefix = b"state-prefix"
        suffix = b"state-suffix"
        inputs = bytes(range(48))
        movie = make_movie(prefix + sram + suffix, inputs)

        patched, state_sram_offset = TOOL.inject_canary(movie, sram)
        self.assertEqual(state_sram_offset, len(prefix))
        state_start, state_end = TOOL.locate_embedded_state(patched)
        patched_state = patched[state_start:state_end]
        patched_sram = patched_state[len(prefix) : len(prefix) + len(sram)]

        self.assertEqual(patched_sram[: TOOL.GAP_OFFSET], sram[: TOOL.GAP_OFFSET])
        self.assertEqual(
            patched_sram[TOOL.GAP_OFFSET : TOOL.METADATA_OFFSET],
            TOOL.make_canary(),
        )
        self.assertEqual(
            patched_sram[TOOL.METADATA_OFFSET :],
            sram[TOOL.METADATA_OFFSET :],
        )
        self.assertEqual(patched[state_end:], inputs)

    def test_rejects_wrong_sram_size(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "0x2000-byte"):
            TOOL.inject_canary(make_movie(b"state"), b"\x00" * 16)

    def test_requires_unique_sram_image(self) -> None:
        sram = bytes((index * 31 + 3) & 0xFF for index in range(0x2000))
        movie = make_movie(sram + b"middle" + sram)
        with self.assertRaisesRegex(RuntimeError, "more than once"):
            TOOL.inject_canary(movie, sram)

    def test_rejects_truncated_state(self) -> None:
        movie = b"BSV1" + struct.pack("<III", 0, 0, 99) + b"short"
        with self.assertRaisesRegex(RuntimeError, "extends beyond"):
            TOOL.locate_embedded_state(movie)


if __name__ == "__main__":
    unittest.main()
