from __future__ import annotations

import argparse
import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "edit_retroarch_bsv_inputs.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("bsv_input_tool", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def make_movie(state: bytes = b"state", poll_frames: int = 4) -> bytes:
    header = b"BSV1" + bytes(8) + struct.pack("<I", len(state))
    inputs = bytes(poll_frames * TOOL.BYTES_PER_POLL_FRAME)
    return header + state + inputs


class BsvInputToolTests(unittest.TestCase):
    def test_edits_only_selected_stream_values(self) -> None:
        source = make_movie()
        inputs = [
            (1, 4, 2, 1, "slot4"),
            (3, 11, 1, 1, "slot11"),
        ]
        result, state_size, input_offset, poll_frames = TOOL.edit_movie(
            source, inputs
        )

        self.assertEqual(state_size, 5)
        self.assertEqual(input_offset, 21)
        self.assertEqual(poll_frames, 4)
        self.assertEqual(result[:input_offset], source[:input_offset])

        values = result[input_offset:]
        expected_nonzero = {
            1 * TOOL.STREAM_SLOTS_PER_LATCH + 4,
            2 * TOOL.STREAM_SLOTS_PER_LATCH + 4,
            3 * TOOL.STREAM_SLOTS_PER_LATCH + 11,
        }
        self.assertEqual(
            {index for index, value in enumerate(values) if value},
            expected_nonzero,
        )
        self.assertTrue(all(values[index] == 1 for index in expected_nonzero))

    def test_rejects_nonzero_source_input(self) -> None:
        source = bytearray(make_movie())
        source[-1] = 1
        with self.assertRaisesRegex(RuntimeError, "not all zero"):
            TOOL.edit_movie(bytes(source), [])

    def test_preserves_existing_nonoverlapping_input_when_allowed(self) -> None:
        source = bytearray(make_movie())
        input_offset = 16 + 5
        existing_offset = (
            input_offset
            + 1 * TOOL.BYTES_PER_POLL_FRAME
            + 3 * TOOL.BYTES_PER_VALUE
        )
        source[existing_offset] = 1

        result, _, _, _ = TOOL.edit_movie(
            bytes(source),
            [(2, 4, 1, 1, "slot4")],
            allow_existing_inputs=True,
        )
        self.assertEqual(
            result[existing_offset],
            1,
        )
        with self.assertRaisesRegex(RuntimeError, "overlaps"):
            TOOL.edit_movie(
                bytes(source),
                [(1, 3, 1, 1, "slot3")],
                allow_existing_inputs=True,
            )

    def test_rejects_truncated_input_frame(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "24 one-byte"):
            TOOL.edit_movie(make_movie() + b"\x00", [])

    def test_rejects_input_past_end(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exceeds 4 poll frames"):
            TOOL.edit_movie(make_movie(), [(3, 0, 2, 1, "slot0")])

    def test_parses_calibrated_stream_slot(self) -> None:
        self.assertEqual(
            TOOL.parse_slot("12:7:3"),
            (12, 7, 3, 1, "slot7"),
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            TOOL.parse_slot("12:24")

    def test_sets_explicit_raw_stream_value(self) -> None:
        source = make_movie()
        raw = TOOL.parse_raw_value("1:5:0x3:2")
        result, _, input_offset, _ = TOOL.edit_movie(source, [raw])

        first = result[
            input_offset
            + 1 * TOOL.BYTES_PER_POLL_FRAME
            + 5 * TOOL.BYTES_PER_VALUE
        ]
        second = result[
            input_offset
            + 2 * TOOL.BYTES_PER_POLL_FRAME
            + 5 * TOOL.BYTES_PER_VALUE
        ]
        self.assertEqual((first, second), (3, 3))

    def test_rejects_invalid_raw_stream_value(self) -> None:
        for spec in ("1:5:0", "1:5:-1", "1:5:256", "1:24:3"):
            with self.subTest(spec=spec):
                with self.assertRaises(argparse.ArgumentTypeError):
                    TOOL.parse_raw_value(spec)


if __name__ == "__main__":
    unittest.main()
