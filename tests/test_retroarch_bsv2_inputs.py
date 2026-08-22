from __future__ import annotations

import argparse
import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "edit_retroarch_bsv2_inputs.py"
RASTATE_PATH = ROOT / "tools" / "retroarch_rastate.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RASTATE = load_module("retroarch_rastate", RASTATE_PATH)
TOOL = load_module("bsv2_input_tool", TOOL_PATH)


def state_block(payload: bytes = b"state") -> bytes:
    return (
        bytes((0, 0))
        + struct.pack("<III", len(payload), len(payload), len(payload))
        + payload
    )


def input_event(
    input_id: int,
    value: int = 0,
    *,
    port: int = 0,
    device: int = 1,
    index: int = 0,
    pad: int = 0,
) -> bytes:
    return struct.pack(
        "<BBBBHh", port, device, index, pad, input_id, value
    )


def frame(
    events: list[bytes],
    *,
    keyboard_events: list[bytes] | None = None,
    token: bytes = b"f",
    checkpoint: bytes = b"",
) -> bytes:
    keys = keyboard_events or []
    return (
        struct.pack("<I", 0)
        + bytes((len(keys),))
        + b"".join(keys)
        + struct.pack("<H", len(events))
        + b"".join(events)
        + token
        + checkpoint
    )


def make_movie(frames: list[bytes]) -> bytes:
    initial = state_block()
    header = struct.pack(
        "<10I",
        TOOL.MAGIC,
        TOOL.VERSION,
        0x12345678,
        len(initial),
        0x89ABCDEF,
        0x01234567,
        len(frames),
        0,
        0,
        0,
    )
    return header + initial + b"".join(frames)


def joypad_frame(values: dict[int, int] | None = None) -> bytes:
    values = values or {}
    return frame(
        [input_event(input_id, values.get(input_id, 0)) for input_id in range(12)]
        + [
            input_event(input_id, port=1)
            for input_id in range(12)
        ]
    )


class Bsv2InputToolTests(unittest.TestCase):
    def test_parses_real_shaped_regular_frames(self) -> None:
        source = make_movie([frame([]), joypad_frame(), joypad_frame()])
        info = TOOL.parse_movie(source)

        self.assertEqual(info.content_crc32, 0x12345678)
        self.assertEqual(info.identifier, 0x0123456789ABCDEF)
        self.assertEqual(info.frame_count, 3)
        self.assertEqual(len(info.frames[0].inputs), 0)
        self.assertEqual(len(info.frames[1].inputs), 24)
        self.assertEqual(info.initial_state.payload_size, 5)

    def test_edits_only_matching_p1_value_fields(self) -> None:
        source = make_movie(
            [joypad_frame(), joypad_frame(), joypad_frame(), joypad_frame()]
        )
        result, info, changed = TOOL.edit_movie(
            source,
            [(1, 4, 2, 1, "up"), (3, 11, 1, 1, "r")],
        )

        self.assertEqual(len(result), len(source))
        self.assertEqual(changed, 3)
        expected_offsets = {
            info.frames[1].inputs[4].value_offset,
            info.frames[2].inputs[4].value_offset,
            info.frames[3].inputs[11].value_offset,
        }
        changed_offsets = {
            index
            for index, (before, after) in enumerate(zip(source, result))
            if before != after
        }
        self.assertEqual(changed_offsets, expected_offsets)
        parsed_result = TOOL.parse_movie(result)
        self.assertEqual(parsed_result.frames[1].inputs[4].value, 1)
        self.assertEqual(parsed_result.frames[1].inputs[16].value, 0)

    def test_rejects_target_frame_without_matching_event(self) -> None:
        source = make_movie([frame([]), joypad_frame()])
        with self.assertRaisesRegex(RuntimeError, "0 matching Player-1"):
            TOOL.edit_movie(source, [(0, 3, 1, 1, "start")])

    def test_rejects_duplicate_matching_event(self) -> None:
        source = make_movie(
            [frame([input_event(3), input_event(3)])]
        )
        with self.assertRaisesRegex(RuntimeError, "2 matching Player-1"):
            TOOL.edit_movie(source, [(0, 3, 1, 1, "start")])

    def test_rejects_any_nonzero_source_by_default(self) -> None:
        source = make_movie([joypad_frame({3: 1}), joypad_frame()])
        with self.assertRaisesRegex(RuntimeError, "nonzero input values"):
            TOOL.edit_movie(source, [(1, 0, 1, 1, "b")])

    def test_preserves_existing_nonoverlapping_input_when_allowed(self) -> None:
        source = make_movie([joypad_frame({3: 1}), joypad_frame()])
        result, _, changed = TOOL.edit_movie(
            source,
            [(1, 0, 1, 1, "b")],
            allow_existing_inputs=True,
        )
        info = TOOL.parse_movie(result)
        self.assertEqual(changed, 1)
        self.assertEqual(info.frames[0].inputs[3].value, 1)
        self.assertEqual(info.frames[1].inputs[0].value, 1)

    def test_rejects_overlap_even_when_existing_values_are_allowed(self) -> None:
        source = make_movie([joypad_frame({3: 1})])
        with self.assertRaisesRegex(RuntimeError, "overlaps existing value"):
            TOOL.edit_movie(
                source,
                [(0, 3, 1, 1, "start")],
                allow_existing_inputs=True,
            )

    def test_parses_v2_checkpoint_without_decoding_it(self) -> None:
        checkpoint = state_block(b"checkpoint")
        source = make_movie(
            [frame([], token=b"C", checkpoint=checkpoint)]
        )
        info = TOOL.parse_movie(source)
        self.assertEqual(info.frames[0].token, ord("C"))
        self.assertEqual(info.frames[0].end, len(source))

    def test_rejects_trailing_bytes_and_state_size_mismatch(self) -> None:
        source = make_movie([frame([])])
        with self.assertRaisesRegex(RuntimeError, "trailing bytes"):
            TOOL.parse_movie(source + b"x")

        changed = bytearray(source)
        struct.pack_into("<I", changed, 12, 1)
        with self.assertRaisesRegex(RuntimeError, "size mismatch"):
            TOOL.parse_movie(bytes(changed))

    def test_rejects_input_past_end(self) -> None:
        source = make_movie([joypad_frame()])
        with self.assertRaisesRegex(RuntimeError, "exceeds 1 replay frames"):
            TOOL.edit_movie(source, [(0, 0, 2, 1, "b")])

    def test_parses_named_press(self) -> None:
        self.assertEqual(TOOL.parse_press("12:start:3"), (12, 3, 3, 1, "start"))
        for spec in ("-1:start", "1:nope", "1:start:0", "x:start"):
            with self.subTest(spec=spec):
                with self.assertRaises(argparse.ArgumentTypeError):
                    TOOL.parse_press(spec)

    def test_replaces_initial_state_without_changing_frames(self) -> None:
        source = make_movie([joypad_frame(), joypad_frame()])
        core_state = b"BST1" + struct.pack("<I", 13) + b"12345"
        result = TOOL.replace_initial_core_state(source, core_state)
        old_info = TOOL.parse_movie(source)
        new_info = TOOL.parse_movie(result)

        self.assertEqual(new_info.initial_state.encoding, 0)
        self.assertEqual(new_info.initial_state.payload_size, len(core_state))
        self.assertEqual(
            result[
                TOOL.HEADER_SIZE + new_info.initial_state.size :
            ],
            source[
                TOOL.HEADER_SIZE + old_info.initial_state.size :
            ],
        )
        payload_start = TOOL.HEADER_SIZE + TOOL.INITIAL_STATE_PREFIX_SIZE
        self.assertEqual(
            result[payload_start : payload_start + len(core_state)],
            core_state,
        )

    def test_rejects_invalid_replacement_state(self) -> None:
        source = make_movie([joypad_frame()])
        with self.assertRaisesRegex(RuntimeError, "not a BST1"):
            TOOL.replace_initial_core_state(source, b"bad")
        with self.assertRaisesRegex(RuntimeError, "length field"):
            TOOL.replace_initial_core_state(
                source,
                b"BST1" + struct.pack("<I", 999) + b"x",
            )


if __name__ == "__main__":
    unittest.main()
