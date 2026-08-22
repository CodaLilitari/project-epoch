#!/usr/bin/env python3
"""Compare matched current-core zero/canary states fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import inject_bsv_wram_canary as canary
import inspect_current_wram_candidate as inspector


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compare_pair(
    canary_source: bytes,
    zero_source: bytes,
    sram: bytes,
    *,
    save_slot: int = 1,
) -> dict[str, object]:
    canary_core, canary_container = inspector.extract_core_state(
        canary_source
    )
    zero_core, zero_container = inspector.extract_core_state(zero_source)
    canary_result = inspector.inspect_candidate(
        canary_source,
        sram,
        save_slot=save_slot,
    )
    zero_result = inspector.inspect_candidate(
        zero_source,
        sram,
        save_slot=save_slot,
    )

    if len(canary_core) != len(zero_core):
        raise RuntimeError("matched core-state lengths differ")
    if (
        canary_result["state_wram_base"]
        != zero_result["state_wram_base"]
        or canary_result["target_state_offset"]
        != zero_result["target_state_offset"]
    ):
        raise RuntimeError("matched states resolve different WRAM layouts")
    if not canary_result["candidate_invariants_ok"]:
        raise RuntimeError("canary state fails candidate invariants")
    if (
        not zero_result["target_all_zero"]
        or zero_result["canary_occurrences"]
        or any(bytes.fromhex(str(zero_result["front_guard_hex"])))
        or any(bytes.fromhex(str(zero_result["rear_guard_hex"])))
    ):
        raise RuntimeError("zero state fails candidate or guard invariants")

    start = int(canary_result["target_state_offset"])
    end = start + canary.TARGET_LENGTH
    differences = tuple(
        index
        for index, (zero_byte, canary_byte) in enumerate(
            zip(zero_core, canary_core, strict=True)
        )
        if zero_byte != canary_byte
    )
    expected_differences = tuple(range(start, end))
    if differences != expected_differences:
        raise RuntimeError(
            "matched cores differ outside or incompletely within the canary"
        )

    normalized = bytearray(canary_core)
    normalized[start:end] = zero_core[start:end]
    normalized_bytes = bytes(normalized)
    if normalized_bytes != zero_core:
        raise AssertionError("normalized canary core does not match control")

    return {
        "schema": "project-epoch-current-canary-pair-v1",
        "save_slot": save_slot,
        "canary_container": canary_container,
        "zero_container": zero_container,
        "canary_container_sha256": sha256(canary_source),
        "zero_container_sha256": sha256(zero_source),
        "canary_core_sha256": sha256(canary_core),
        "zero_core_sha256": sha256(zero_core),
        "normalized_canary_core_sha256": sha256(normalized_bytes),
        "core_state_length": len(canary_core),
        "state_wram_base": canary_result["state_wram_base"],
        "target_state_offset": start,
        "target_length": canary.TARGET_LENGTH,
        "difference_count": len(differences),
        "difference_start": differences[0],
        "difference_end_exclusive": differences[-1] + 1,
        "equivalent_except_canary": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zero_state", type=pathlib.Path)
    parser.add_argument("canary_state", type=pathlib.Path)
    parser.add_argument("--srm", required=True, type=pathlib.Path)
    parser.add_argument("--slot", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()

    result = compare_pair(
        args.canary_state.read_bytes(),
        args.zero_state.read_bytes(),
        args.srm.read_bytes(),
        save_slot=args.slot,
    )
    result["zero_path"] = str(args.zero_state)
    result["canary_path"] = str(args.canary_state)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
