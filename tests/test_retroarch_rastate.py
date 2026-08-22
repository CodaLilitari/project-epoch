from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "retroarch_rastate.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("retroarch_rastate", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def chunk(tag: bytes, payload: bytes) -> bytes:
    value = tag + struct.pack("<I", len(payload)) + payload
    return value + bytes((-len(value)) % 8)


class RetroArchRastateTests(unittest.TestCase):
    def test_extracts_memory_from_multichunk_container(self) -> None:
        source = (
            b"RASTATE\x01"
            + chunk(b"RPLY", b"replay")
            + chunk(b"MEM ", b"core-state")
            + chunk(b"END ", b"")
        )
        info = TOOL.parse_container(source)

        self.assertEqual(
            [entry.tag for entry in info.chunks],
            [b"RPLY", b"MEM ", b"END "],
        )
        self.assertEqual(TOOL.extract_memory(source), b"core-state")

    def test_builds_minimal_container_with_alignment(self) -> None:
        core_state = b"BST1" + bytes(range(13))
        source = TOOL.make_minimal_container(core_state)

        self.assertEqual(len(source) % 8, 0)
        self.assertEqual(TOOL.extract_memory(source), core_state)
        self.assertEqual(source[-8:], b"END " + bytes(4))

    def test_rejects_truncated_nonzero_padded_and_duplicate_memory(self) -> None:
        valid = b"RASTATE\x01" + chunk(b"MEM ", b"x") + chunk(b"END ", b"")
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            TOOL.parse_container(valid[:-1])

        changed = bytearray(valid)
        memory_payload_end = 8 + 8 + 1
        changed[memory_payload_end] = 1
        with self.assertRaisesRegex(RuntimeError, "nonzero padding"):
            TOOL.parse_container(bytes(changed))

        duplicate = (
            b"RASTATE\x01"
            + chunk(b"MEM ", b"a")
            + chunk(b"MEM ", b"b")
            + chunk(b"END ", b"")
        )
        with self.assertRaisesRegex(RuntimeError, "2 MEM chunks"):
            TOOL.extract_memory(duplicate)


if __name__ == "__main__":
    unittest.main()
