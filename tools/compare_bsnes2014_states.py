#!/usr/bin/env python3
"""Compare pinned bsnes2014 states with a repeated-run control.

RetroArch's BST1 wrapper stores the loaded ROM SHA-256 in the state header.
The pinned bsnes2014 core also emits a few run-to-run-variant payload bytes.
This helper learns those payload offsets from two runs of the same baseline
ROM, then reports whether a candidate ROM changes any additional state bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


PINNED_STATE_LENGTH = 329_133
PINNED_WRAM_STATE_OFFSET = 0x4AA3
WRAM_LENGTH = 0x20000
ROM_ID_START = 0x08
ROM_ID_LENGTH = 0x40


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_state(state: bytes) -> None:
    if len(state) != PINNED_STATE_LENGTH:
        raise RuntimeError(
            "state length does not match the pinned bsnes2014 layout"
        )
    if state[:4] != b"BST1":
        raise RuntimeError("state does not have a BST1 wrapper")


def differing_offsets(left: bytes, right: bytes) -> set[int]:
    validate_state(left)
    validate_state(right)
    return {
        offset
        for offset, (left_byte, right_byte) in enumerate(zip(left, right))
        if left_byte != right_byte
    }


def format_ranges(offsets: set[int]) -> list[str]:
    if not offsets:
        return []
    ordered = sorted(offsets)
    ranges: list[str] = []
    start = previous = ordered[0]
    for offset in ordered[1:]:
        if offset != previous + 1:
            ranges.append(f"0x{start:X}-0x{previous:X}")
            start = offset
        previous = offset
    ranges.append(f"0x{start:X}-0x{previous:X}")
    return ranges


def compare_with_control(
    baseline: bytes,
    repeated_baseline: bytes,
    candidate: bytes,
) -> dict[str, object]:
    control_differences = differing_offsets(baseline, repeated_baseline)
    candidate_differences = differing_offsets(baseline, candidate)
    rom_id_offsets = set(range(ROM_ID_START, ROM_ID_START + ROM_ID_LENGTH))
    control_payload = control_differences - rom_id_offsets
    candidate_payload = candidate_differences - rom_id_offsets
    unexplained_payload = candidate_payload - control_payload
    payload_offsets = set(range(len(baseline))) - rom_id_offsets
    payload_matches_baseline = all(
        baseline[offset] == candidate[offset] for offset in payload_offsets
    )
    payload_matches_repeated_baseline = all(
        repeated_baseline[offset] == candidate[offset]
        for offset in payload_offsets
    )

    wram_offsets = set(
        range(PINNED_WRAM_STATE_OFFSET, PINNED_WRAM_STATE_OFFSET + WRAM_LENGTH)
    )
    wram_differences = candidate_differences & wram_offsets
    repeated_wram_differences = {
        offset
        for offset in wram_offsets
        if repeated_baseline[offset] != candidate[offset]
    }
    identity_differences = candidate_differences & rom_id_offsets
    matches_one_control_run = (
        payload_matches_baseline or payload_matches_repeated_baseline
    )

    return {
        "baseline_sha256": sha256(baseline),
        "repeated_baseline_sha256": sha256(repeated_baseline),
        "candidate_sha256": sha256(candidate),
        "state_length": len(baseline),
        "rom_identity_range": (
            f"0x{ROM_ID_START:X}-"
            f"0x{ROM_ID_START + ROM_ID_LENGTH - 1:X}"
        ),
        "identity_difference_count": len(identity_differences),
        "identity_difference_ranges": format_ranges(identity_differences),
        "control_payload_difference_count": len(control_payload),
        "control_payload_difference_ranges": format_ranges(control_payload),
        "candidate_payload_difference_count": len(candidate_payload),
        "candidate_payload_difference_ranges": format_ranges(candidate_payload),
        "unexplained_payload_difference_count": len(unexplained_payload),
        "unexplained_payload_difference_ranges": format_ranges(
            unexplained_payload
        ),
        "wram_state_offset": PINNED_WRAM_STATE_OFFSET,
        "wram_length": WRAM_LENGTH,
        "wram_difference_count": len(wram_differences),
        "wram_difference_ranges": format_ranges(wram_differences),
        "wram_repeated_baseline_difference_count": len(
            repeated_wram_differences
        ),
        "wram_repeated_baseline_difference_ranges": format_ranges(
            repeated_wram_differences
        ),
        "candidate_payload_within_control_variance": not unexplained_payload,
        "payload_matches_baseline": payload_matches_baseline,
        "payload_matches_repeated_baseline": (
            payload_matches_repeated_baseline
        ),
        "matches_one_control_run_ignoring_identity": matches_one_control_run,
        "wram_identical": not wram_differences,
        "wram_matches_repeated_baseline": not repeated_wram_differences,
        "equivalent_at_checkpoint": (
            matches_one_control_run
            or (not unexplained_payload and not wram_differences)
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=pathlib.Path)
    parser.add_argument("repeated_baseline", type=pathlib.Path)
    parser.add_argument("candidate", type=pathlib.Path)
    parser.add_argument(
        "--require-equivalent",
        action="store_true",
        help="exit with an error unless candidate differences are explained",
    )
    args = parser.parse_args()

    result = compare_with_control(
        args.baseline.read_bytes(),
        args.repeated_baseline.read_bytes(),
        args.candidate.read_bytes(),
    )
    result["baseline_path"] = str(args.baseline)
    result["repeated_baseline_path"] = str(args.repeated_baseline)
    result["candidate_path"] = str(args.candidate)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_equivalent and not result["equivalent_at_checkpoint"]:
        raise SystemExit("candidate state is not equivalent at this checkpoint")


if __name__ == "__main__":
    main()
