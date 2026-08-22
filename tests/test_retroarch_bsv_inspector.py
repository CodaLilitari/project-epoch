from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "inspect_retroarch_bsv_inputs.py"
SPEC = importlib.util.spec_from_file_location("bsv_inspector", TOOL_PATH)
assert SPEC and SPEC.loader
INSPECTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = INSPECTOR
SPEC.loader.exec_module(INSPECTOR)


def make_movie(state: bytes, frames: list[list[int]]) -> bytes:
    header = b"BSV1" + struct.pack("<III", 7, 11, len(state))
    inputs = b"".join(struct.pack("<24B", *frame) for frame in frames)
    return header + state + inputs


class BsvInspectorTests(unittest.TestCase):
    def test_groups_contiguous_values_by_stream_slot(self) -> None:
        frames = [[0] * 24 for _ in range(4)]
        frames[1][4] = 1
        frames[2][4] = 1
        frames[2][0] = 255
        info, spans = INSPECTOR.parse_movie(make_movie(b"state", frames))

        self.assertEqual(info.state_size, 5)
        self.assertEqual(info.input_offset, 21)
        self.assertEqual(info.poll_frames, 4)
        self.assertEqual(
            spans,
            (
                INSPECTOR.InputSpan(1, 3, 4, 1),
                INSPECTOR.InputSpan(2, 3, 0, 255),
            ),
        )

    def test_splits_when_nonzero_value_changes(self) -> None:
        frames = [[0] * 24 for _ in range(3)]
        frames[0][2] = 1
        frames[1][2] = 2
        _, spans = INSPECTOR.parse_movie(make_movie(b"", frames))
        self.assertEqual(
            spans,
            (
                INSPECTOR.InputSpan(0, 1, 2, 1),
                INSPECTOR.InputSpan(1, 2, 2, 2),
            ),
        )

    def test_rejects_truncated_poll_frame(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "24 one-byte"):
            INSPECTOR.parse_movie(make_movie(b"", []) + b"\0")

    def test_rejects_wrong_magic(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "BSV1"):
            INSPECTOR.parse_movie(b"NOPE" + b"\0" * 12)


if __name__ == "__main__":
    unittest.main()
