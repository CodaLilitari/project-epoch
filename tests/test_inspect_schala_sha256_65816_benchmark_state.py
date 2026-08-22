from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
PATH = TOOLS / "inspect_schala_sha256_65816_benchmark_state.py"
LIVE_STATES = (
    ROOT
    / "private"
    / "test_runs"
    / "sha256_65c816"
    / "runtime_run1"
    / "schala_sha256_profile1_benchmark.state.auto",
    ROOT
    / "private"
    / "test_runs"
    / "sha256_65c816"
    / "runtime_run2"
    / "schala_sha256_profile1_benchmark.state.auto",
)
SPEC = importlib.util.spec_from_file_location("sha_benchmark_state", PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)

import retroarch_rastate  # noqa: E402


def put_u16(target: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", target, offset, value)


def passing_rastate() -> bytes:
    core = bytearray(TOOL.BST_WRAM_OFFSET + TOOL.WRAM_SIZE)
    core[:4] = TOOL.BST_MAGIC
    core[
        TOOL.BST_VERSION_OFFSET :
        TOOL.BST_VERSION_OFFSET + len(TOOL.BST_VERSION) + 1
    ] = TOOL.BST_VERSION.encode("ascii") + b"\x00"
    wram = TOOL.BST_WRAM_OFFSET
    result = bytearray(TOOL.RESULT_SIZE)
    result[:8] = TOOL.RESULT_MAGIC
    put_u16(result, 0x08, 1)
    put_u16(result, 0x0A, TOOL.RESULT_SIZE)
    put_u16(result, 0x0C, 0xA55A)
    put_u16(result, 0x0E, 0)
    put_u16(result, 0x10, 0xA55A)
    put_u16(result, 0x12, 1100)
    put_u16(result, 0x14, 0xFFFF)
    put_u16(result, 0x16, 1)
    put_u16(result, 0x18, TOOL.EXPECTED_ABI_MASK)
    put_u16(result, 0x1A, TOOL.EXPECTED_P)
    put_u16(result, 0x1C, 1)
    put_u16(result, 0x1E, 0x6A00)
    put_u16(result, 0x20, TOOL.EXPECTED_Y)
    put_u16(result, 0x22, TOOL.EXPECTED_D)
    put_u16(result, 0x24, TOOL.EXPECTED_SP)
    put_u16(result, 0x26, TOOL.EXPECTED_SP)
    put_u16(result, 0x28, TOOL.EXPECTED_DBR)
    put_u16(result, 0x2A, 1)
    put_u16(result, 0x2C, 1)
    put_u16(result, 0x2E, 4)

    starts = (1, 367, 734)
    ends = (367, 734, 1100)
    for slot, record, start, end in zip(
        range(1, 4),
        TOOL.SLOT_RECORDS,
        starts,
        ends,
        strict=True,
    ):
        put_u16(result, record + 0x00, slot)
        put_u16(result, record + 0x02, TOOL.EXPECTED_BASES[slot])
        put_u16(result, record + 0x04, 0)
        put_u16(result, record + 0x06, start)
        put_u16(result, record + 0x08, end)
        put_u16(result, record + 0x0A, end - start)
        put_u16(result, record + 0x0C, TOOL.EXPECTED_ABI_MASK)
        put_u16(result, record + 0x0E, TOOL.EXPECTED_P)
        put_u16(result, record + 0x10, TOOL.EXPECTED_P)
        put_u16(result, record + 0x12, slot)
        put_u16(result, record + 0x14, TOOL.EXPECTED_BASES[slot])
        put_u16(result, record + 0x16, TOOL.EXPECTED_Y)
        put_u16(result, record + 0x18, TOOL.EXPECTED_D)
        put_u16(result, record + 0x1A, TOOL.EXPECTED_SP)
        put_u16(result, record + 0x1C, TOOL.EXPECTED_SP)
        put_u16(result, record + 0x1E, TOOL.EXPECTED_DBR)
        put_u16(result, record + 0x20, TOOL.EXPECTED_DBR)
        result[record + 0x22 : record + 0x42] = bytes.fromhex(
            TOOL.EXPECTED_DIGESTS[slot]
        )
        put_u16(result, record + 0x42, 1)

    core[
        wram + TOOL.RESULT_ADDRESS :
        wram + TOOL.RESULT_ADDRESS + TOOL.RESULT_SIZE
    ] = result
    core[
        wram + TOOL.SCRATCH_FRONT : wram + TOOL.SCRATCH_START
    ] = TOOL.GUARD_BYTES
    core[
        wram + TOOL.SCRATCH_END : wram + TOOL.SCRATCH_REAR_END
    ] = TOOL.GUARD_BYTES
    core[4:8] = len(core).to_bytes(4, "little")
    return retroarch_rastate.make_minimal_container(bytes(core))


class BenchmarkStateInspectorTests(unittest.TestCase):
    @unittest.skipUnless(
        all(path.is_file() for path in LIVE_STATES),
        "private standalone benchmark states are not staged",
    )
    def test_live_private_runs_match_defined_evidence_spans(self) -> None:
        reports = [TOOL.inspect_path(path) for path in LIVE_STATES]
        self.assertTrue(all(report["passed"] for report in reports))
        self.assertEqual(
            reports[0]["result"]["record_sha256"],
            reports[1]["result"]["record_sha256"],
        )
        self.assertEqual(
            reports[0]["result"]["scratch_with_guards_sha256"],
            reports[1]["result"]["scratch_with_guards_sha256"],
        )
        self.assertEqual(
            reports[0]["memory_layout"]["sram_sha256"],
            reports[1]["memory_layout"]["sram_sha256"],
        )

    def test_passing_current_bsnes_state_decodes_exact_contract(self) -> None:
        result = TOOL.inspect_rastate_bytes(passing_rastate())
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["core_state"]["serializer_version"],
            TOOL.BST_VERSION,
        )
        self.assertEqual(
            result["memory_layout"]["sram_sha256"],
            TOOL.ZERO_SRAM_SHA256,
        )
        self.assertEqual(
            [slot["elapsed_frames"] for slot in result["result"]["slots"]],
            [366, 367, 366],
        )
        self.assertEqual(result["result"]["failure_count"], 0)

    def test_wrong_digest_fails_closed(self) -> None:
        source = bytearray(passing_rastate())
        core = bytearray(retroarch_rastate.extract_memory(bytes(source)))
        offset = (
            TOOL.BST_WRAM_OFFSET
            + TOOL.RESULT_ADDRESS
            + TOOL.SLOT_RECORDS[0]
            + 0x22
        )
        core[offset] ^= 1
        with self.assertRaisesRegex(TOOL.BenchmarkStateError, "digest mismatch"):
            TOOL.inspect_rastate_bytes(
                retroarch_rastate.make_minimal_container(bytes(core))
            )

    def test_status_guard_and_sram_corruption_fail_closed(self) -> None:
        base = retroarch_rastate.extract_memory(passing_rastate())
        cases = (
            (
                TOOL.BST_WRAM_OFFSET
                + TOOL.RESULT_ADDRESS
                + TOOL.SLOT_RECORDS[1]
                + 0x04,
                "status",
            ),
            (
                TOOL.BST_WRAM_OFFSET + TOOL.SCRATCH_FRONT,
                "front scratch guard",
            ),
            (TOOL.BST_SRAM_OFFSET, "SRAM is not all zero"),
        )
        for offset, message in cases:
            with self.subTest(offset=offset):
                core = bytearray(base)
                core[offset] ^= 1
                with self.assertRaisesRegex(TOOL.BenchmarkStateError, message):
                    TOOL.inspect_rastate_bytes(
                        retroarch_rastate.make_minimal_container(bytes(core))
                    )

    def test_duplicate_magic_is_rejected(self) -> None:
        core = bytearray(retroarch_rastate.extract_memory(passing_rastate()))
        core[TOOL.BST_WRAM_OFFSET + 0x100 : TOOL.BST_WRAM_OFFSET + 0x108] = (
            TOOL.RESULT_MAGIC
        )
        with self.assertRaisesRegex(TOOL.BenchmarkStateError, "found 2"):
            TOOL.inspect_rastate_bytes(
                retroarch_rastate.make_minimal_container(bytes(core))
            )

    def test_wrong_serializer_and_truncation_are_rejected(self) -> None:
        core = bytearray(retroarch_rastate.extract_memory(passing_rastate()))
        core[TOOL.BST_VERSION_OFFSET : TOOL.BST_VERSION_OFFSET + 5] = b"114.0"
        with self.assertRaisesRegex(
            TOOL.BenchmarkStateError, "unsupported bsnes serializer"
        ):
            TOOL.inspect_rastate_bytes(
                retroarch_rastate.make_minimal_container(bytes(core))
            )
        with self.assertRaises(TOOL.BenchmarkStateError):
            TOOL.inspect_rastate_bytes(passing_rastate()[:-17])

    def test_exact_bytes_type_is_required(self) -> None:
        with self.assertRaisesRegex(
            TOOL.BenchmarkStateError, "immutable bytes"
        ):
            TOOL.inspect_rastate_bytes(bytearray())


if __name__ == "__main__":
    unittest.main()
