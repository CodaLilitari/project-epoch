from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
EDITOR_PATH = TOOLS / "edit_retroarch_bsv2_inputs.py"
INSPECTOR_PATH = TOOLS / "inspect_retroarch_bsv2_inputs.py"
RASTATE_PATH = TOOLS / "retroarch_rastate.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RASTATE = load_module("retroarch_rastate", RASTATE_PATH)
EDITOR = load_module("edit_retroarch_bsv2_inputs", EDITOR_PATH)
INSPECTOR = load_module("inspect_retroarch_bsv2_inputs", INSPECTOR_PATH)


def make_movie(values: list[int]) -> bytes:
    state = bytes((0, 0)) + struct.pack("<III", 0, 0, 0)
    frames = []
    for value in values:
        event = struct.pack("<BBBBHh", 0, 1, 0, 0, 3, value)
        frames.append(
            struct.pack("<I", 0)
            + b"\x00"
            + struct.pack("<H", 1)
            + event
            + b"f"
        )
    header = struct.pack(
        "<10I",
        EDITOR.MAGIC,
        EDITOR.VERSION,
        0,
        len(state),
        0,
        0,
        len(frames),
        0,
        0,
        0,
    )
    return header + state + b"".join(frames)


class Bsv2InspectorTests(unittest.TestCase):
    def test_groups_contiguous_nonzero_values(self) -> None:
        source = make_movie([0, 1, 1, 0, 2, 2, 2, 0])
        spans = INSPECTOR.find_nonzero_spans(source)

        self.assertEqual(len(spans), 2)
        self.assertEqual((spans[0].start, spans[0].duration), (1, 2))
        self.assertEqual(spans[0].value, 1)
        self.assertEqual((spans[1].start, spans[1].duration), (4, 3))
        self.assertEqual(spans[1].value, 2)


if __name__ == "__main__":
    unittest.main()
