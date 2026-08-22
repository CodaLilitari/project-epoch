#!/usr/bin/env python3
"""Verify the Project Epoch WRAM candidate canary in bsnes2014 states."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import inject_bsv_wram_canary as canary_tool


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_state(state: bytes) -> dict[str, object]:
    if len(state) != canary_tool.PINNED_STATE_LENGTH:
        raise RuntimeError(
            "state length does not match the pinned bsnes2014 layout"
        )
    start = (
        canary_tool.PINNED_WRAM_STATE_OFFSET
        + canary_tool.TARGET_WRAM_OFFSET
    )
    end = start + canary_tool.TARGET_LENGTH
    actual = state[start:end]
    expected = canary_tool.make_canary()
    occurrences: list[int] = []
    cursor = 0
    while True:
        hit = state.find(expected, cursor)
        if hit < 0:
            break
        occurrences.append(hit)
        cursor = hit + 1
    return {
        "state_length": len(state),
        "state_sha256": sha256(state),
        "target_wram": f"7E:{canary_tool.TARGET_WRAM_OFFSET:04X}",
        "target_state_offset": start,
        "target_length": canary_tool.TARGET_LENGTH,
        "expected_canary_sha256": sha256(expected),
        "actual_target_sha256": sha256(actual),
        "canary_matches": actual == expected,
        "target_all_zero": not any(actual),
        "canary_occurrences": occurrences,
        "front_guard_hex": state[start - 4 : start].hex(),
        "rear_guard_hex": state[end : end + 0x10].hex(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("states", nargs="+", type=pathlib.Path)
    parser.add_argument(
        "--require-canary",
        action="store_true",
        help="exit with an error if any state lacks the exact canary",
    )
    parser.add_argument(
        "--require-zero",
        action="store_true",
        help="exit with an error unless every candidate block is all zero",
    )
    args = parser.parse_args()
    if args.require_canary and args.require_zero:
        parser.error("--require-canary and --require-zero are mutually exclusive")

    failed = False
    for path in args.states:
        result = inspect_state(path.read_bytes())
        result["path"] = str(path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if not result["canary_matches"]:
            if args.require_canary:
                failed = True
        if args.require_zero and not result["target_all_zero"]:
            failed = True
    if args.require_canary and failed:
        raise SystemExit("one or more states did not preserve the canary")
    if args.require_zero and failed:
        raise SystemExit("one or more candidate blocks was not all zero")


if __name__ == "__main__":
    main()
