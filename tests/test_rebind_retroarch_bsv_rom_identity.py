from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import struct
import sys
import unittest
import zlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "rebind_retroarch_bsv_rom_identity.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("rebind_retroarch_bsv_rom_identity", TOOL_PATH)


def make_movie(identity: str = "1" * 64) -> bytes:
    state = bytearray(TOOL.PINNED_STATE_LENGTH)
    state[:4] = b"BST1"
    state[
        TOOL.ROM_ID_STATE_START :
        TOOL.ROM_ID_STATE_START + TOOL.ROM_ID_LENGTH
    ] = identity.encode("ascii")
    inputs = bytes(range(48))
    return (
        b"BSV1"
        + struct.pack("<III", 0, 0x12345678, len(state))
        + bytes(state)
        + inputs
    )


class RebindRetroArchBsvRomIdentityTests(unittest.TestCase):
    def test_rebinds_only_wrapper_identity_and_preserves_inputs(self) -> None:
        movie = make_movie()
        target = b"expanded target"
        rebound, source, target_identity = TOOL.rebind_movie(movie, target)
        state_end = TOOL.BSV_HEADER_SIZE + TOOL.PINNED_STATE_LENGTH

        self.assertEqual(source, "1" * 64)
        self.assertEqual(target_identity, hashlib.sha256(target).hexdigest())
        self.assertEqual(rebound[state_end:], movie[state_end:])
        self.assertEqual(
            struct.unpack_from("<I", rebound, TOOL.BSV_CONTENT_CRC_OFFSET)[0],
            zlib.crc32(target) & 0xFFFFFFFF,
        )
        changed = {
            index
            for index, (before, after) in enumerate(
                zip(movie, rebound, strict=True)
            )
            if before != after
        }
        identity_start = TOOL.BSV_HEADER_SIZE + TOOL.ROM_ID_STATE_START
        self.assertTrue(changed)
        self.assertLessEqual(
            changed,
            set(range(identity_start, identity_start + TOOL.ROM_ID_LENGTH))
            | set(
                range(
                    TOOL.BSV_CONTENT_CRC_OFFSET,
                    TOOL.BSV_CONTENT_CRC_OFFSET + 4,
                )
            ),
        )

    def test_accepts_pinned_source_identity(self) -> None:
        movie = make_movie("a" * 64)
        TOOL.rebind_movie(
            movie,
            b"target",
            expected_source_identity="A" * 64,
        )

    def test_rejects_wrong_pinned_source_identity(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "pinned expectation"):
            TOOL.rebind_movie(
                make_movie("a" * 64),
                b"target",
                expected_source_identity="b" * 64,
            )

    def test_rejects_wrong_state_length_or_magic(self) -> None:
        short = b"BSV1" + struct.pack("<III", 0, 0, 4) + b"BST1"
        with self.assertRaisesRegex(RuntimeError, "length"):
            TOOL.locate_state(short)
        wrong_magic = bytearray(make_movie())
        wrong_magic[TOOL.BSV_HEADER_SIZE : TOOL.BSV_HEADER_SIZE + 4] = b"NOPE"
        with self.assertRaisesRegex(RuntimeError, "BST1"):
            TOOL.locate_state(bytes(wrong_magic))

    def test_rejects_non_hex_identity(self) -> None:
        movie = bytearray(make_movie())
        start = TOOL.BSV_HEADER_SIZE + TOOL.ROM_ID_STATE_START
        movie[start] = ord("z")
        with self.assertRaisesRegex(RuntimeError, "lowercase SHA-256"):
            TOOL.embedded_rom_identity(bytes(movie))

    def test_private_output_guard(self) -> None:
        private_path = ROOT / "private" / "test_runs" / "rebound.bsv"
        self.assertEqual(
            TOOL.validate_private_output(private_path),
            private_path.resolve(),
        )
        with self.assertRaisesRegex(RuntimeError, "private"):
            TOOL.validate_private_output(ROOT / "rebound.bsv")


if __name__ == "__main__":
    unittest.main()
