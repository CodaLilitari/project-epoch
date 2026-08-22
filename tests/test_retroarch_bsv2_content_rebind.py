from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest
import zlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def load_module(name: str, filename: str):
    path = TOOLS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RASTATE = load_module("retroarch_rastate", "retroarch_rastate.py")
EDITOR = load_module(
    "edit_retroarch_bsv2_inputs", "edit_retroarch_bsv2_inputs.py"
)
TOOL = load_module(
    "rebind_retroarch_bsv2_content_crc",
    "rebind_retroarch_bsv2_content_crc.py",
)


def make_movie(content_crc: int) -> bytes:
    core_state = b"BST1" + struct.pack("<I", 9) + b"x"
    state = (
        bytes((0, 0))
        + struct.pack("<III", 9, 9, 9)
        + core_state
    )
    frame = struct.pack("<I", 0) + b"\x00\x00\x00f"
    return (
        struct.pack(
            "<10I",
            EDITOR.MAGIC,
            EDITOR.VERSION,
            content_crc,
            len(state),
            0,
            0,
            1,
            0,
            0,
            0,
        )
        + state
        + frame
    )


class RetroArchBsv2ContentRebindTests(unittest.TestCase):
    def test_changes_only_content_crc_field(self) -> None:
        source_rom = b"source-rom"
        target_rom = b"target-rom"
        movie = make_movie(zlib.crc32(source_rom) & 0xFFFFFFFF)
        result, source_crc, target_crc = TOOL.rebind_movie(
            movie,
            target_rom,
            expected_source_rom=source_rom,
        )

        changed = {
            index
            for index, pair in enumerate(zip(movie, result, strict=True))
            if pair[0] != pair[1]
        }
        self.assertTrue(changed)
        self.assertTrue(changed <= set(range(8, 12)))
        self.assertEqual(source_crc, zlib.crc32(source_rom) & 0xFFFFFFFF)
        self.assertEqual(target_crc, zlib.crc32(target_rom) & 0xFFFFFFFF)
        self.assertEqual(EDITOR.parse_movie(result).content_crc32, target_crc)

    def test_rejects_wrong_expected_source(self) -> None:
        movie = make_movie(0x12345678)
        with self.assertRaisesRegex(RuntimeError, "expected source"):
            TOOL.rebind_movie(
                movie,
                b"target",
                expected_source_rom=b"wrong-source",
            )


if __name__ == "__main__":
    unittest.main()
