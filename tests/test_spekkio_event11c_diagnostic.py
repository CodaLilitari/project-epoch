from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "inject_spekkio_event11c_diagnostic.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    tools_path = str(ROOT / "tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    spec.loader.exec_module(module)
    return module


TOOL = load_module("inject_spekkio_event11c_diagnostic", TOOL_PATH)


def make_movie() -> tuple[bytes, bytes]:
    core = bytearray(TOOL.STATE_LENGTH)
    core[:len(TOOL.STATE_PREFIX)] = TOOL.STATE_PREFIX
    base = TOOL.WRAM_BASE
    core[base + TOOL.LOCATION_OFFSET:base + TOOL.LOCATION_OFFSET + 2] = (
        0x01D1
    ).to_bytes(2, "little")
    core[base + TOOL.EXPLORE_MODE_OFFSET] = 1
    core[base + TOOL.DIALOG_STATE_OFFSET] = 0
    core[base + TOOL.STORYLINE_OFFSET] = 0xD5
    core[base + TOOL.MAGIC_FLAGS_OFFSET] = 0xFF
    core[base + TOOL.ROBO_FLAGS_OFFSET] = 0xFF
    core[base + TOOL.LAP_SCRATCH_OFFSET] = 0
    core[base + TOOL.ACTIVE_PARTY_OFFSET:
         base + TOOL.ACTIVE_PARTY_OFFSET + 3] = bytes((6, 4, 3))
    core[base + TOOL.EPOCH_NAME_START:
         base + TOOL.EPOCH_NAME_END] = b"EPOCH "
    for offset in (0x2830, 0x2831, 0x2832, 0x2834):
        core[base + offset] = 8
    for offset in (0x2837, 0x2838, 0x2839, 0x283B):
        core[base + offset] = 0xFF
    for offset in (0x262D, 0x267D, 0x26CD, 0x276D):
        core[base + offset:base + offset + 2] = b"\xAA\x55"

    state_block = (
        bytes((0, 0))
        + struct.pack("<III", len(core), len(core), len(core))
        + bytes(core)
    )
    header = struct.pack(
        "<10I",
        TOOL.bsv2.MAGIC,
        TOOL.bsv2.VERSION,
        0x2D206BF7,
        len(state_block),
        0x12345678,
        0,
        0,
        0,
        0,
        0,
    )
    return header + state_block, bytes(core)


class SpekkioEvent11CDiagnosticTests(unittest.TestCase):
    def test_prepares_frog_robo_profile_with_exact_scope(self) -> None:
        movie, source_core = make_movie()
        result, manifest = TOOL.inject_diagnostic(
            movie,
            profile_name="frog-robo",
            expected_core_sha256=hashlib.sha256(source_core).hexdigest(),
        )
        core = TOOL.current_state.extract_raw_initial_core_state(result)
        base = TOOL.WRAM_BASE
        self.assertEqual(core[base + TOOL.STORYLINE_OFFSET], 0x4C)
        self.assertEqual(core[base + TOOL.LAP_SCRATCH_OFFSET], 3)
        self.assertEqual(core[base + TOOL.MAGIC_FLAGS_OFFSET], 0xE7)
        self.assertEqual(core[base + TOOL.ROBO_FLAGS_OFFSET], 0xFE)
        self.assertEqual(
            core[
                base + TOOL.ACTIVE_PARTY_OFFSET:
                base + TOOL.ACTIVE_PARTY_OFFSET + 3
            ],
            bytes((6, 4, 3)),
        )
        self.assertEqual(core[base + 0x2834], 0)
        self.assertEqual(core[base + 0x283B], 0x1F)
        self.assertEqual(core[base + 0x276D:base + 0x276F], b"\x00\x00")
        self.assertEqual(core[base + 0x2830], 8)
        self.assertEqual(core[base + 0x2837], 0xFF)
        self.assertTrue(manifest["replay_frames_preserved"])
        self.assertTrue(manifest["candidate_and_guards_zero"])
        self.assertTrue(manifest["epoch_name_preserved"])

    def test_prepares_crono_marle_lucca_profile(self) -> None:
        movie, source_core = make_movie()
        result, manifest = TOOL.inject_diagnostic(
            movie,
            profile_name="crono-marle-lucca",
            expected_core_sha256=hashlib.sha256(source_core).hexdigest(),
        )
        core = TOOL.current_state.extract_raw_initial_core_state(result)
        base = TOOL.WRAM_BASE
        self.assertEqual(
            core[
                base + TOOL.ACTIVE_PARTY_OFFSET:
                base + TOOL.ACTIVE_PARTY_OFFSET + 3
            ],
            bytes((0, 1, 2)),
        )
        self.assertEqual(core[base + TOOL.MAGIC_FLAGS_OFFSET], 0xB8)
        self.assertEqual(
            [core[base + offset] for offset in (0x2830, 0x2831, 0x2832)],
            [0, 0, 0],
        )
        self.assertEqual(
            [core[base + offset] for offset in (0x2837, 0x2838, 0x2839)],
            [0x1F, 0x1F, 0x1F],
        )
        self.assertEqual(manifest["prepared_active_party_hex"], "000102")

    def test_rejects_wrong_hash_or_location(self) -> None:
        movie, source_core = make_movie()
        with self.assertRaisesRegex(TOOL.DiagnosticError, "SHA-256"):
            TOOL.inject_diagnostic(
                movie,
                profile_name="frog-robo",
                expected_core_sha256="0" * 64,
            )

        changed = bytearray(source_core)
        changed[
            TOOL.WRAM_BASE + TOOL.LOCATION_OFFSET:
            TOOL.WRAM_BASE + TOOL.LOCATION_OFFSET + 2
        ] = (0x01D0).to_bytes(2, "little")
        changed_movie = TOOL.bsv2.replace_initial_core_state(
            movie,
            bytes(changed),
        )
        with self.assertRaisesRegex(TOOL.DiagnosticError, "Spekkio"):
            TOOL.inject_diagnostic(
                changed_movie,
                profile_name="frog-robo",
                expected_core_sha256=hashlib.sha256(changed).hexdigest(),
            )

    def test_rejects_candidate_or_pc07_source(self) -> None:
        movie, source_core = make_movie()
        changed = bytearray(source_core)
        changed[TOOL.WRAM_BASE + TOOL.CANDIDATE_START] = 1
        changed_movie = TOOL.bsv2.replace_initial_core_state(
            movie,
            bytes(changed),
        )
        with self.assertRaisesRegex(TOOL.DiagnosticError, "candidate range"):
            TOOL.inject_diagnostic(
                changed_movie,
                profile_name="frog-robo",
                expected_core_sha256=hashlib.sha256(changed).hexdigest(),
            )

        changed = bytearray(source_core)
        changed[TOOL.WRAM_BASE + TOOL.ACTIVE_PARTY_OFFSET] = 7
        changed_movie = TOOL.bsv2.replace_initial_core_state(
            movie,
            bytes(changed),
        )
        with self.assertRaisesRegex(TOOL.DiagnosticError, "PC \\$07"):
            TOOL.inject_diagnostic(
                changed_movie,
                profile_name="frog-robo",
                expected_core_sha256=hashlib.sha256(changed).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
