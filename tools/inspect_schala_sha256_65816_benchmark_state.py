#!/usr/bin/env python3
"""Inspect the standalone Project Epoch SHA-256 benchmark RASTATE.

The accepted layout is deliberately pinned to current bsnes serializer 115.1.
This tool does not inspect or modify a game ROM, save, or game-derived state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
from collections.abc import Sequence
from typing import Final

import retroarch_rastate


BST_MAGIC: Final = b"BST1"
BST_VERSION: Final = "115.1"
BST_VERSION_OFFSET: Final = 8
BST_SRAM_OFFSET: Final = 0x022E
BST_WRAM_OFFSET: Final = 0x2284
SRAM_SIZE: Final = 0x2000
WRAM_SIZE: Final = 0x20000
ZERO_SRAM_SHA256: Final = (
    "9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47"
)

RESULT_MAGIC: Final = b"PESHA816"
RESULT_ADDRESS: Final = 0x5F00
RESULT_SIZE: Final = 0x0140
SCRATCH_FRONT: Final = 0x3FF0
SCRATCH_START: Final = 0x4000
SCRATCH_END: Final = 0x40C2
SCRATCH_REAR_END: Final = 0x40D2
GUARD_BYTES: Final = b"\x5A\xA5" * 8

SLOT_RECORDS: Final = (0x30, 0x80, 0xD0)
SLOT_RECORD_SIZE: Final = 0x50
EXPECTED_P: Final = 0x008D
EXPECTED_Y: Final = 0xA55A
EXPECTED_D: Final = 0x1234
EXPECTED_DBR: Final = 0x0012
EXPECTED_SP: Final = 0x1FFC
EXPECTED_ABI_MASK: Final = 0x007F
EXPECTED_DIGESTS: Final = {
    1: "878829ba5210cd4d1defacbedb6c485407a25dc8be2cf46ae2bd90636b9ebdbd",
    2: "45351b0ff714359ed22d687605b843658bf8ce3e2d997199ce0077323cde00b5",
    3: "716b7eb41aa41f3febfb7843cb18174a01ba869cf2a634b0fe53f0d58cdd59b2",
}
EXPECTED_BASES: Final = {1: 0x6000, 2: 0x6A00, 3: 0x7400}


class BenchmarkStateError(ValueError):
    """Raised when a state cannot be promoted as passing evidence."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise BenchmarkStateError(f"truncated word at 0x{offset:X}")
    return struct.unpack_from("<H", data, offset)[0]


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise BenchmarkStateError(detail)


def _bst_version(core: bytes) -> str:
    _require(core.startswith(BST_MAGIC), "core state is not BST1")
    _require(len(core) >= BST_VERSION_OFFSET + 2, "truncated BST1 header")
    declared = int.from_bytes(core[4:8], "little")
    _require(
        declared == len(core),
        f"BST1 declared size {declared} does not match {len(core)}",
    )
    terminator = core.find(b"\x00", BST_VERSION_OFFSET, BST_VERSION_OFFSET + 32)
    _require(terminator >= 0, "BST1 version is not terminated")
    try:
        version = core[BST_VERSION_OFFSET:terminator].decode("ascii")
    except UnicodeDecodeError as exc:
        raise BenchmarkStateError("BST1 version is not ASCII") from exc
    _require(
        version == BST_VERSION,
        f"unsupported bsnes serializer {version!r}; expected {BST_VERSION}",
    )
    return version


def _decode_slot(result: bytes, record: int, slot: int) -> dict[str, object]:
    base = EXPECTED_BASES[slot]
    _require(_u16(result, record + 0x00) == slot, f"slot {slot} ID mismatch")
    _require(
        _u16(result, record + 0x02) == base,
        f"slot {slot} base mismatch",
    )
    status = _u16(result, record + 0x04)
    frame_start = _u16(result, record + 0x06)
    frame_end = _u16(result, record + 0x08)
    elapsed = _u16(result, record + 0x0A)
    abi_mask = _u16(result, record + 0x0C)
    p_expected = _u16(result, record + 0x0E)
    p_actual = _u16(result, record + 0x10)
    a_actual = _u16(result, record + 0x12)
    x_actual = _u16(result, record + 0x14)
    y_actual = _u16(result, record + 0x16)
    d_actual = _u16(result, record + 0x18)
    sp_expected = _u16(result, record + 0x1A)
    sp_actual = _u16(result, record + 0x1C)
    dbr_expected = _u16(result, record + 0x1E)
    dbr_actual = _u16(result, record + 0x20)
    digest = result[record + 0x22 : record + 0x42]
    digest_ok = _u16(result, record + 0x42)

    _require(status == 0, f"slot {slot} status is 0x{status:04X}")
    _require(elapsed > 0, f"slot {slot} elapsed frame count is zero")
    _require(
        elapsed == ((frame_end - frame_start) & 0xFFFF),
        f"slot {slot} elapsed frame count is inconsistent",
    )
    _require(
        abi_mask == EXPECTED_ABI_MASK,
        f"slot {slot} ABI mask is 0x{abi_mask:04X}",
    )
    _require(
        p_expected == EXPECTED_P and p_actual == EXPECTED_P,
        f"slot {slot} processor flags were not restored",
    )
    _require(a_actual == slot, f"slot {slot} A was not restored")
    _require(x_actual == base, f"slot {slot} X was not restored")
    _require(y_actual == EXPECTED_Y, f"slot {slot} Y was not restored")
    _require(d_actual == EXPECTED_D, f"slot {slot} D was not restored")
    _require(
        sp_expected == EXPECTED_SP and sp_actual == EXPECTED_SP,
        f"slot {slot} stack pointer was not restored",
    )
    _require(
        dbr_expected == EXPECTED_DBR and dbr_actual == EXPECTED_DBR,
        f"slot {slot} DBR was not restored",
    )
    expected_digest = bytes.fromhex(EXPECTED_DIGESTS[slot])
    _require(digest == expected_digest, f"slot {slot} digest mismatch")
    _require(digest_ok == 1, f"slot {slot} digest flag is not one")

    return {
        "slot": slot,
        "sram_base": base,
        "status": status,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "elapsed_frames": elapsed,
        "abi_mask": abi_mask,
        "p_expected": p_expected,
        "p_actual": p_actual,
        "a_actual": a_actual,
        "x_actual": x_actual,
        "y_actual": y_actual,
        "d_actual": d_actual,
        "sp_expected": sp_expected,
        "sp_actual": sp_actual,
        "dbr_expected": dbr_expected,
        "dbr_actual": dbr_actual,
        "digest": digest.hex(),
        "digest_ok": True,
    }


def inspect_rastate_bytes(source: bytes) -> dict[str, object]:
    if type(source) is not bytes:
        raise BenchmarkStateError("RASTATE source must be immutable bytes")
    try:
        core = retroarch_rastate.extract_memory(source)
    except RuntimeError as exc:
        raise BenchmarkStateError(str(exc)) from exc
    version = _bst_version(core)

    hits: list[int] = []
    cursor = 0
    while True:
        found = core.find(RESULT_MAGIC, cursor)
        if found < 0:
            break
        hits.append(found)
        cursor = found + 1
    _require(
        len(hits) == 1,
        f"expected one committed result record, found {len(hits)}",
    )
    result_offset = hits[0]
    wram_offset = result_offset - RESULT_ADDRESS
    _require(
        wram_offset == BST_WRAM_OFFSET,
        f"unexpected current-bsnes WRAM offset 0x{wram_offset:X}",
    )
    _require(
        wram_offset + WRAM_SIZE <= len(core),
        "current-bsnes WRAM image is truncated",
    )
    result = core[result_offset : result_offset + RESULT_SIZE]
    _require(len(result) == RESULT_SIZE, "result record is truncated")
    _require(result[:8] == RESULT_MAGIC, "result commit magic mismatch")
    _require(_u16(result, 0x08) == 1, "unsupported result version")
    _require(_u16(result, 0x0A) == RESULT_SIZE, "result length mismatch")
    _require(_u16(result, 0x0C) == 0xA55A, "benchmark overall status failed")
    _require(_u16(result, 0x0E) == 0, "benchmark failure count is nonzero")
    _require(_u16(result, 0x10) == 0xA55A, "completion word is missing")
    final_frame = _u16(result, 0x12)
    _require(_u16(result, 0x2E) == 4, "benchmark call count is not four")

    invalid = {
        "status": _u16(result, 0x14),
        "output_unchanged": _u16(result, 0x16),
        "abi_mask": _u16(result, 0x18),
        "p_actual": _u16(result, 0x1A),
        "a_actual": _u16(result, 0x1C),
        "x_actual": _u16(result, 0x1E),
        "y_actual": _u16(result, 0x20),
        "d_actual": _u16(result, 0x22),
        "sp_expected": _u16(result, 0x24),
        "sp_actual": _u16(result, 0x26),
        "dbr_actual": _u16(result, 0x28),
    }
    _require(invalid["status"] == 0xFFFF, "invalid call did not fail closed")
    _require(
        invalid["output_unchanged"] == 1,
        "invalid call modified the digest output",
    )
    _require(
        invalid["abi_mask"] == EXPECTED_ABI_MASK,
        "invalid-call ABI restoration failed",
    )
    _require(invalid["p_actual"] == EXPECTED_P, "invalid-call P mismatch")
    _require(invalid["a_actual"] == 1, "invalid-call A mismatch")
    _require(invalid["x_actual"] == 0x6A00, "invalid-call X mismatch")
    _require(invalid["y_actual"] == EXPECTED_Y, "invalid-call Y mismatch")
    _require(invalid["d_actual"] == EXPECTED_D, "invalid-call D mismatch")
    _require(
        invalid["sp_expected"] == EXPECTED_SP
        and invalid["sp_actual"] == EXPECTED_SP,
        "invalid-call SP mismatch",
    )
    _require(
        invalid["dbr_actual"] == EXPECTED_DBR,
        "invalid-call DBR mismatch",
    )
    _require(_u16(result, 0x2A) == 1, "front-guard result flag failed")
    _require(_u16(result, 0x2C) == 1, "rear-guard result flag failed")

    slots = [
        _decode_slot(result, record, slot)
        for slot, record in enumerate(SLOT_RECORDS, start=1)
    ]
    _require(
        slots[1]["frame_start"] == slots[0]["frame_end"]
        and slots[2]["frame_start"] == slots[1]["frame_end"],
        "slot timing records are not contiguous",
    )
    _require(
        final_frame == slots[2]["frame_end"],
        "final frame does not match slot-3 completion",
    )

    front = core[
        wram_offset + SCRATCH_FRONT : wram_offset + SCRATCH_START
    ]
    rear = core[
        wram_offset + SCRATCH_END : wram_offset + SCRATCH_REAR_END
    ]
    _require(front == GUARD_BYTES, "front scratch guard was modified")
    _require(rear == GUARD_BYTES, "rear scratch guard was modified")
    scratch_with_guards = core[
        wram_offset + SCRATCH_FRONT : wram_offset + SCRATCH_REAR_END
    ]

    sram = core[BST_SRAM_OFFSET : BST_SRAM_OFFSET + SRAM_SIZE]
    _require(len(sram) == SRAM_SIZE, "current-bsnes SRAM image is truncated")
    _require(not any(sram), "benchmark SRAM is not all zero")
    _require(
        sha256(sram) == ZERO_SRAM_SHA256,
        "benchmark SRAM all-zero hash mismatch",
    )

    return {
        "evidence_level": "verified-runtime-standalone",
        "passed": True,
        "rastate": {
            "size": len(source),
            "sha256": sha256(source),
        },
        "core_state": {
            "format": "BST1",
            "serializer_version": version,
            "size": len(core),
            "sha256": sha256(core),
        },
        "memory_layout": {
            "sram_offset": BST_SRAM_OFFSET,
            "sram_size": SRAM_SIZE,
            "sram_sha256": sha256(sram),
            "sram_all_zero": True,
            "wram_offset": wram_offset,
            "wram_size": WRAM_SIZE,
            "result_offset": result_offset,
            "result_address": RESULT_ADDRESS,
            "result_size": RESULT_SIZE,
        },
        "result": {
            "magic": RESULT_MAGIC.decode("ascii"),
            "version": _u16(result, 0x08),
            "length": _u16(result, 0x0A),
            "overall_status": _u16(result, 0x0C),
            "failure_count": _u16(result, 0x0E),
            "completion_word": _u16(result, 0x10),
            "final_frame": final_frame,
            "call_count": _u16(result, 0x2E),
            "record_sha256": sha256(result),
            "scratch_with_guards_sha256": sha256(scratch_with_guards),
            "front_guard": front.hex(),
            "rear_guard": rear.hex(),
            "invalid_call": invalid,
            "slots": slots,
        },
        "limitations": [
            "standalone synthetic cartridge only",
            "minimal benchmark NMI handler only",
            "does not approve a game hook, allocation, or interrupt policy",
        ],
    }


def inspect_path(path: pathlib.Path) -> dict[str, object]:
    path = path.resolve()
    if not path.is_file():
        raise BenchmarkStateError(f"RASTATE does not exist: {path}")
    result = inspect_rastate_bytes(path.read_bytes())
    result["path"] = str(path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rastate", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(inspect_path(args.rastate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
