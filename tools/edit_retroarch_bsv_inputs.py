#!/usr/bin/env python3
"""Add deterministic inputs to a RetroArch v1.7.1 BSV1 movie.

The Project Epoch emulator pin is RetroArch v1.7.1 (commit 6fc6bfbb24).
That release stores one byte for every libretro ``input_state`` callback and
does not store frame or input-ID metadata.  The pinned bsnes2014 core queries
the twelve SNES joypad IDs for player 1 and then the same twelve IDs for
player 2, so one calibrated auto-joypad latch is twenty-four bytes.

This is deliberately not a parser for the incompatible, versioned replay
format used by current RetroArch releases.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
from typing import TypeAlias


LIBRETRO_JOYPAD_IDS = {
    "b": 0,
    "y": 1,
    "select": 2,
    "start": 3,
    "up": 4,
    "down": 5,
    "left": 6,
    "right": 7,
    "a": 8,
    "x": 9,
    "l": 10,
    "r": 11,
}
BUTTONS_PER_PORT = 12
PORTS_PER_LATCH = 2
STREAM_SLOTS_PER_LATCH = BUTTONS_PER_PORT * PORTS_PER_LATCH
BYTES_PER_VALUE = 1
BYTES_PER_POLL_FRAME = STREAM_SLOTS_PER_LATCH * BYTES_PER_VALUE
InputEdit: TypeAlias = tuple[int, int, int, int, str]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_input_spec(
    spec: str,
    *,
    named_slots: dict[str, int] | None = None,
) -> InputEdit:
    parts = spec.lower().split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(
            "input must be POLL_FRAME:SLOT_OR_NAME[:DURATION]"
        )
    try:
        frame = int(parts[0])
        duration = int(parts[2]) if len(parts) == 3 else 1
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "frame and duration must be integers"
        ) from exc
    slot_text = parts[1]
    if frame < 0 or duration < 1:
        raise argparse.ArgumentTypeError(
            "frame must be non-negative and duration must be positive"
        )
    if named_slots is not None:
        if slot_text not in named_slots:
            valid = ", ".join(named_slots)
            raise argparse.ArgumentTypeError(
                f"unknown button {slot_text!r}; expected one of: {valid}"
            )
        slot = named_slots[slot_text]
        label = slot_text
    else:
        try:
            slot = int(slot_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "stream slot must be an integer"
            ) from exc
        if not 0 <= slot < STREAM_SLOTS_PER_LATCH:
            raise argparse.ArgumentTypeError("stream slot must be 0 through 23")
        label = f"slot{slot}"
    return frame, slot, duration, 1, label


def parse_press(spec: str) -> InputEdit:
    return parse_input_spec(spec, named_slots=LIBRETRO_JOYPAD_IDS)


def parse_slot(spec: str) -> InputEdit:
    return parse_input_spec(spec)


def parse_raw_value(spec: str) -> InputEdit:
    parts = spec.lower().split(":")
    if len(parts) not in (3, 4):
        raise argparse.ArgumentTypeError(
            "raw input must be POLL_FRAME:STREAM_SLOT:VALUE[:DURATION]"
        )
    try:
        frame = int(parts[0])
        slot = int(parts[1])
        value = int(parts[2], 0)
        duration = int(parts[3]) if len(parts) == 4 else 1
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "frame, slot, value, and duration must be integers"
        ) from exc
    if frame < 0 or duration < 1:
        raise argparse.ArgumentTypeError(
            "frame must be non-negative and duration must be positive"
        )
    if not 0 <= slot < STREAM_SLOTS_PER_LATCH:
        raise argparse.ArgumentTypeError("stream slot must be 0 through 23")
    if value == 0 or not 0 <= value <= 0xFF:
        raise argparse.ArgumentTypeError(
            "raw value must be a nonzero unsigned 8-bit integer"
        )
    return frame, slot, duration, value, f"slot{slot}"


def edit_movie(
    source: bytes,
    inputs: list[InputEdit],
    *,
    allow_existing_inputs: bool = False,
) -> tuple[bytes, int, int, int]:
    """Return the edited movie plus state size, input offset, and frame count."""
    if source[:4] != b"BSV1" or len(source) < 16:
        raise RuntimeError("not a supported BSV1 movie")

    state_size = struct.unpack_from("<I", source, 12)[0]
    input_offset = 16 + state_size
    if input_offset > len(source):
        raise RuntimeError("embedded savestate extends beyond the movie")

    input_size = len(source) - input_offset
    if input_size % BYTES_PER_POLL_FRAME:
        raise RuntimeError(
            "input stream is not 24 one-byte callback values per joypad latch"
        )
    if not allow_existing_inputs and any(source[input_offset:]):
        raise RuntimeError(
            "source input stream is not all zero; refusing to overwrite inputs"
        )

    poll_frames = input_size // BYTES_PER_POLL_FRAME
    output = bytearray(source)
    for frame, stream_slot, duration, value, label in inputs:
        if frame + duration > poll_frames:
            raise RuntimeError(
                f"{label} input at {frame}..{frame + duration - 1} "
                f"exceeds {poll_frames} poll frames"
            )
        for current in range(frame, frame + duration):
            value_offset = (
                input_offset
                + current * BYTES_PER_POLL_FRAME
                + stream_slot * BYTES_PER_VALUE
            )
            if output[value_offset] != 0:
                raise RuntimeError(
                    f"{label} input at {current} overlaps an existing "
                    "nonzero input value"
                )
            output[value_offset] = value

    return bytes(output), state_size, input_offset, poll_frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument(
        "--press",
        action="append",
        default=[],
        type=parse_press,
        metavar="POLL_FRAME:BUTTON[:DURATION]",
        help=(
            "set a libretro joypad-ID slot; only use when the core's BSV "
            "query order is proven; names target player 1"
        ),
    )
    parser.add_argument(
        "--slot",
        action="append",
        default=[],
        type=parse_slot,
        metavar="POLL_FRAME:STREAM_SLOT[:DURATION]",
        help=(
            "set a calibrated BSV input-call stream slot (0 through 23) "
            "for one or more input-poll frames"
        ),
    )
    parser.add_argument(
        "--raw-value",
        action="append",
        default=[],
        type=parse_raw_value,
        metavar="POLL_FRAME:STREAM_SLOT:VALUE[:DURATION]",
        help=(
            "set a calibrated BSV input-call stream slot to an explicit "
            "nonzero unsigned 8-bit value"
        ),
    )
    parser.add_argument(
        "--allow-existing-inputs",
        action="store_true",
        help=(
            "preserve existing nonzero input values while adding only "
            "non-overlapping pulses"
        ),
    )
    args = parser.parse_args()

    source = args.source.read_bytes()
    inputs = args.press + args.slot + args.raw_value
    result, state_size, input_offset, poll_frames = edit_movie(
        source,
        inputs,
        allow_existing_inputs=args.allow_existing_inputs,
    )
    if args.output.exists() and args.output.read_bytes() != result:
        raise RuntimeError(f"refusing to overwrite changed output: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)

    print(f"source_sha256={sha256(source)}")
    print(f"output_sha256={sha256(result)}")
    print(f"state_size={state_size}")
    print(f"input_offset={input_offset}")
    print(f"poll_frames={poll_frames}")
    for frame, _, duration, value, label in inputs:
        print(f"input={frame}:{label}:{duration}:value={value}")


if __name__ == "__main__":
    main()
