#!/usr/bin/env python3
"""Verify the SRAM-gap canary and its guards in a pinned bsnes2014 state."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import inject_bsv_sram_gap_canary as canary_tool


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_state(state: bytes) -> None:
    if len(state) != canary_tool.PINNED_STATE_LENGTH:
        raise RuntimeError(
            "state length does not match the pinned bsnes2014 layout"
        )
    if state[:4] != b"BST1":
        raise RuntimeError("state does not have the pinned BST1 wrapper")


def embedded_state(movie: bytes) -> bytes:
    start, end = canary_tool.locate_embedded_state(movie)
    state = movie[start:end]
    _validate_state(state)
    return state


def inspect_state(
    state: bytes,
    *,
    baseline_state: bytes | None = None,
) -> dict[str, object]:
    _validate_state(state)
    if baseline_state is not None:
        _validate_state(baseline_state)

    sram_start = canary_tool.PINNED_SRAM_STATE_OFFSET
    sram_end = sram_start + canary_tool.EXPECTED_SRAM_SIZE
    gap_start = sram_start + canary_tool.GAP_OFFSET
    gap_end = gap_start + canary_tool.GAP_LENGTH
    metadata_start = sram_start + canary_tool.METADATA_OFFSET
    sram = state[sram_start:sram_end]
    gap = state[gap_start:gap_end]
    expected = canary_tool.make_canary()

    occurrences: list[int] = []
    cursor = 0
    while True:
        hit = state.find(expected, cursor)
        if hit < 0:
            break
        occurrences.append(hit)
        cursor = hit + 1

    result: dict[str, object] = {
        "state_length": len(state),
        "state_sha256": sha256(state),
        "sram_state_offset": sram_start,
        "sram_length": len(sram),
        "sram_sha256": sha256(sram),
        "gap_state_offset": gap_start,
        "gap_length": len(gap),
        "expected_canary_sha256": sha256(expected),
        "actual_gap_sha256": sha256(gap),
        "canary_matches": gap == expected,
        "canary_occurrences": occurrences,
        "vanilla_region_sha256": sha256(
            state[sram_start:gap_start]
        ),
        "metadata_sha256": sha256(state[metadata_start:sram_end]),
    }

    if baseline_state is not None:
        baseline_sram = baseline_state[sram_start:sram_end]
        result.update(
            {
                "baseline_state_sha256": sha256(baseline_state),
                "baseline_sram_sha256": sha256(baseline_sram),
                "sram_matches_baseline": sram == baseline_sram,
                "vanilla_region_matches_baseline": (
                    state[sram_start:gap_start]
                    == baseline_state[sram_start:gap_start]
                ),
                "gap_matches_baseline": (
                    state[gap_start:gap_end]
                    == baseline_state[gap_start:gap_end]
                ),
                "metadata_matches_baseline": (
                    state[metadata_start:sram_end]
                    == baseline_state[metadata_start:sram_end]
                ),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("states", nargs="+", type=pathlib.Path)
    parser.add_argument(
        "--baseline-movie",
        type=pathlib.Path,
        help="compare the complete SRAM image with this BSV's initial state",
    )
    parser.add_argument(
        "--require-canary",
        action="store_true",
        help="fail unless every state contains the exact gap canary once",
    )
    parser.add_argument(
        "--require-sram-match",
        action="store_true",
        help="fail unless every complete SRAM image matches --baseline-movie",
    )
    args = parser.parse_args()
    if args.require_sram_match and args.baseline_movie is None:
        parser.error("--require-sram-match requires --baseline-movie")

    baseline = None
    if args.baseline_movie is not None:
        baseline = embedded_state(args.baseline_movie.read_bytes())

    failed = False
    for path in args.states:
        result = inspect_state(path.read_bytes(), baseline_state=baseline)
        result["path"] = str(path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.require_canary and (
            not result["canary_matches"]
            or result["canary_occurrences"]
            != [result["gap_state_offset"]]
        ):
            failed = True
        if args.require_sram_match and not result["sram_matches_baseline"]:
            failed = True
    if failed:
        raise SystemExit("one or more states failed the SRAM canary policy")


if __name__ == "__main__":
    main()
