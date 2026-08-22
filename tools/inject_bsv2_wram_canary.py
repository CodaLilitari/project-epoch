#!/usr/bin/env python3
"""Inject the Project Epoch WRAM canary into a raw-state BSV2 checkpoint.

The input must be a current RetroArch BSV2 replay whose initial core state is
uncompressed and raw (encoding 0).  The live WRAM base is derived from the
selected save slot's Lucca and Magus records, or accepted from the exact pinned
current-bsnes layout when no loaded save exists at a title/attract checkpoint.
Only the zero-filled candidate range $7E2CA0-$7E2CEF is changed; the replay
frames remain byte-identical.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib

import edit_retroarch_bsv2_inputs as bsv2
import inject_bsv_wram_canary as canary


PINNED_CURRENT_STATE_LENGTH = 290_423
PINNED_CURRENT_CORE_PREFIX = b"BST1" + b"\x77\x6E\x04\x00" + b"115.1\x00"
PINNED_CURRENT_WRAM_STATE_OFFSET = 0x2284


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_raw_initial_core_state(movie: bytes) -> bytes:
    info = bsv2.parse_movie(movie)
    state = info.initial_state
    if state.compression != 0 or state.encoding != 0:
        raise RuntimeError(
            "BSV2 initial state must be uncompressed raw encoding 0"
        )
    if not (
        state.decoded_size == state.encoded_size == state.payload_size
    ):
        raise RuntimeError("raw BSV2 initial-state sizes are inconsistent")
    payload_offset = state.offset + bsv2.INITIAL_STATE_PREFIX_SIZE
    core_state = movie[payload_offset : payload_offset + state.payload_size]
    if len(core_state) < 8 or core_state[:4] != b"BST1":
        raise RuntimeError("BSV2 payload is not a BST1 core state")
    return core_state


def inject_canary(
    movie: bytes,
    sram: bytes | None,
    *,
    save_slot: int = 1,
    allow_existing: bool = False,
    use_pinned_current_layout: bool = False,
) -> tuple[bytes, int, int]:
    info = bsv2.parse_movie(movie)
    core_state = extract_raw_initial_core_state(movie)
    if use_pinned_current_layout:
        if sram is not None:
            raise RuntimeError(
                "pinned current layout and SRAM-derived layout are exclusive"
            )
        if (
            len(core_state) != PINNED_CURRENT_STATE_LENGTH
            or not core_state.startswith(PINNED_CURRENT_CORE_PREFIX)
        ):
            raise RuntimeError("not the pinned current-bsnes raw core state")
        wram_base = PINNED_CURRENT_WRAM_STATE_OFFSET
    else:
        if sram is None:
            raise RuntimeError("SRAM is required to derive the live WRAM base")
        wram_base = canary.locate_live_wram_base(
            core_state, sram, save_slot=save_slot
        )
    target_offset = wram_base + canary.TARGET_WRAM_OFFSET
    target_end = target_offset + canary.TARGET_LENGTH
    if target_end > len(core_state):
        raise RuntimeError("candidate WRAM block extends beyond core state")
    target_before = core_state[target_offset:target_end]
    expected = canary.make_canary()
    if target_before == expected and allow_existing:
        return movie, wram_base, target_offset
    if any(target_before):
        raise RuntimeError("candidate WRAM block is not all zero in source state")

    changed_state = bytearray(core_state)
    changed_state[target_offset:target_end] = expected
    result = bsv2.replace_initial_core_state(movie, bytes(changed_state))

    new_info = bsv2.parse_movie(result)
    old_frames = movie[
        bsv2.HEADER_SIZE + info.initial_state.size :
    ]
    new_frames = result[
        bsv2.HEADER_SIZE + new_info.initial_state.size :
    ]
    if new_frames != old_frames:
        raise AssertionError("canary injection changed replay frames")
    changed_core_state = extract_raw_initial_core_state(result)
    differences = {
        index
        for index, (before, after) in enumerate(
            zip(core_state, changed_core_state, strict=True)
        )
        if before != after
    }
    allowed = set(range(target_offset, target_end))
    if not differences or differences - allowed:
        raise AssertionError("canary injection escaped the candidate block")
    return result, wram_base, target_offset


def validate_private_output(path: pathlib.Path) -> pathlib.Path:
    workspace = pathlib.Path(__file__).resolve().parents[1]
    private_root = (workspace / "private").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError(
            "output must remain under the workspace private/ tree"
        ) from exc
    if resolved.suffix.lower() != ".bsv":
        raise RuntimeError("output must use the .bsv replay suffix")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    layout = parser.add_mutually_exclusive_group(required=True)
    layout.add_argument("--srm", type=pathlib.Path)
    layout.add_argument(
        "--pinned-current-layout",
        action="store_true",
        help=(
            "use the exact current-bsnes 115.1 raw-state layout; intended "
            "for title/attract checkpoints with no loaded save anchor"
        ),
    )
    parser.add_argument("--slot", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="accept an initial state that already contains the exact canary",
    )
    parser.add_argument("-o", "--out", required=True, type=pathlib.Path)
    args = parser.parse_args()

    movie = args.movie.read_bytes()
    sram = None if args.srm is None else args.srm.read_bytes()
    result, wram_base, target_offset = inject_canary(
        movie,
        sram,
        save_slot=args.slot,
        allow_existing=args.allow_existing,
        use_pinned_current_layout=args.pinned_current_layout,
    )
    output = validate_private_output(args.out)
    if output.exists() and output.read_bytes() != result:
        raise RuntimeError(f"refusing to overwrite changed output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)

    print(f"input_movie_sha256={sha256(movie)}")
    if sram is not None:
        print(f"input_sram_sha256={sha256(sram)}")
        print(f"save_slot={args.slot}")
        print("wram_anchor_method=save-record-match")
    else:
        print("wram_anchor_method=pinned-current-core-layout")
    print(f"state_wram_base=0x{wram_base:X}")
    print(f"target_wram=7E:{canary.TARGET_WRAM_OFFSET:04X}")
    print(f"target_state_offset=0x{target_offset:X}")
    print(f"target_length=0x{canary.TARGET_LENGTH:X}")
    print(f"canary_sha256={sha256(canary.make_canary())}")
    print(f"output_movie_sha256={sha256(result)}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
