#!/usr/bin/env python3
"""Add deterministic joypad inputs to a RetroArch BSV2 replay.

RetroArch 1.22.2 records tagged input events in BSV version 2.  This tool
changes only the signed 16-bit value of an existing event whose port, device,
index, and joypad ID all match.  It never inserts records or changes a frame's
size, so the replay's offsets and back references remain intact.

Use a zero-input replay recorded with the exact frontend, core, content, and
configuration under test.  This is intentionally separate from the legacy
RetroArch v1.7.1 BSV1 callback-stream editor.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import struct
from typing import TypeAlias

import retroarch_rastate


MAGIC = 0x42535632
VERSION = 2
HEADER_WORDS = 10
HEADER_SIZE = HEADER_WORDS * 4
INITIAL_STATE_PREFIX_SIZE = 14
KEY_EVENT_SIZE = 12
INPUT_EVENT_SIZE = 8
REGULAR_FRAME_TOKEN = ord("f")
LEGACY_CHECKPOINT_TOKEN = ord("c")
V2_CHECKPOINT_TOKEN = ord("C")
LIBRETRO_DEVICE_JOYPAD = 1
PLAYER_ONE_PORT = 0
PLAYER_ONE_INDEX = 0
MAX_EVENTS_PER_FRAME = 4096

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

InputEdit: TypeAlias = tuple[int, int, int, int, str]


@dataclasses.dataclass(frozen=True)
class InputEvent:
    port: int
    device: int
    index: int
    pad: int
    input_id: int
    value: int
    value_offset: int

    @property
    def identity(self) -> tuple[int, int, int, int]:
        return self.port, self.device, self.index, self.input_id


@dataclasses.dataclass(frozen=True)
class FrameInfo:
    number: int
    start: int
    end: int
    back_distance: int
    keyboard_events: int
    token: int
    inputs: tuple[InputEvent, ...]


@dataclasses.dataclass(frozen=True)
class StateBlockInfo:
    offset: int
    size: int
    compression: int
    encoding: int
    decoded_size: int
    encoded_size: int
    payload_size: int


@dataclasses.dataclass(frozen=True)
class MovieInfo:
    header_words: tuple[int, ...]
    content_crc32: int
    identifier: int
    frame_count: int
    initial_state: StateBlockInfo
    frames: tuple[FrameInfo, ...]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(source: bytes, offset: int, size: int, label: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(source):
        raise RuntimeError(f"truncated {label} at offset {offset}")


def _parse_state_block(
    source: bytes,
    offset: int,
    *,
    declared_size: int | None,
    label: str,
) -> tuple[StateBlockInfo, int]:
    _require(source, offset, INITIAL_STATE_PREFIX_SIZE, f"{label} prefix")
    compression = source[offset]
    encoding = source[offset + 1]
    decoded_size, encoded_size, payload_size = struct.unpack_from(
        "<III", source, offset + 2
    )
    size = INITIAL_STATE_PREFIX_SIZE + payload_size
    if declared_size is not None and size != declared_size:
        raise RuntimeError(
            f"{label} size mismatch: header={declared_size}, body={size}"
        )
    _require(source, offset, size, label)
    if compression not in (0, 1, 2):
        raise RuntimeError(f"unsupported {label} compression {compression}")
    if encoding not in (0, 1):
        raise RuntimeError(f"unsupported {label} encoding {encoding}")
    return (
        StateBlockInfo(
            offset=offset,
            size=size,
            compression=compression,
            encoding=encoding,
            decoded_size=decoded_size,
            encoded_size=encoded_size,
            payload_size=payload_size,
        ),
        offset + size,
    )


def parse_movie(source: bytes) -> MovieInfo:
    """Parse a complete BSV2 movie without decoding embedded core states."""
    if len(source) < HEADER_SIZE:
        raise RuntimeError("file is too short for a BSV2 header")

    header_words = struct.unpack_from("<10I", source)
    if header_words[0] != MAGIC:
        raise RuntimeError("not a supported BSV2 movie")
    if header_words[1] != VERSION:
        raise RuntimeError(f"unsupported BSV version {header_words[1]}")

    initial_state, cursor = _parse_state_block(
        source,
        HEADER_SIZE,
        declared_size=header_words[3],
        label="initial state",
    )
    frame_count = header_words[6]
    frames: list[FrameInfo] = []

    for frame_number in range(frame_count):
        frame_start = cursor
        _require(source, cursor, 5, f"frame {frame_number} header")
        back_distance = struct.unpack_from("<I", source, cursor)[0]
        cursor += 4
        keyboard_events = source[cursor]
        cursor += 1

        keyboard_bytes = keyboard_events * KEY_EVENT_SIZE
        _require(
            source,
            cursor,
            keyboard_bytes + 2,
            f"frame {frame_number} keyboard/input counts",
        )
        cursor += keyboard_bytes
        input_count = struct.unpack_from("<H", source, cursor)[0]
        cursor += 2
        if input_count > MAX_EVENTS_PER_FRAME:
            raise RuntimeError(
                f"frame {frame_number} has implausible input count "
                f"{input_count}"
            )

        _require(
            source,
            cursor,
            input_count * INPUT_EVENT_SIZE + 1,
            f"frame {frame_number} input records",
        )
        events: list[InputEvent] = []
        for _ in range(input_count):
            event_offset = cursor
            port, device, index, pad, input_id, value = struct.unpack_from(
                "<BBBBHh", source, event_offset
            )
            events.append(
                InputEvent(
                    port=port,
                    device=device,
                    index=index,
                    pad=pad,
                    input_id=input_id,
                    value=value,
                    value_offset=event_offset + 6,
                )
            )
            cursor += INPUT_EVENT_SIZE

        token = source[cursor]
        cursor += 1
        if token == REGULAR_FRAME_TOKEN:
            pass
        elif token == LEGACY_CHECKPOINT_TOKEN:
            _require(
                source,
                cursor,
                8,
                f"frame {frame_number} legacy checkpoint size",
            )
            checkpoint_size = struct.unpack_from("<Q", source, cursor)[0]
            cursor += 8
            _require(
                source,
                cursor,
                checkpoint_size,
                f"frame {frame_number} legacy checkpoint",
            )
            cursor += checkpoint_size
        elif token == V2_CHECKPOINT_TOKEN:
            _, cursor = _parse_state_block(
                source,
                cursor,
                declared_size=None,
                label=f"frame {frame_number} checkpoint",
            )
        else:
            token_label = chr(token) if 32 <= token <= 126 else f"0x{token:02X}"
            raise RuntimeError(
                f"frame {frame_number} has unsupported token {token_label!r}"
            )

        frames.append(
            FrameInfo(
                number=frame_number,
                start=frame_start,
                end=cursor,
                back_distance=back_distance,
                keyboard_events=keyboard_events,
                token=token,
                inputs=tuple(events),
            )
        )

    if cursor != len(source):
        raise RuntimeError(
            f"movie has {len(source) - cursor} trailing bytes after "
            f"{frame_count} frames"
        )

    identifier = header_words[4] | (header_words[5] << 32)
    return MovieInfo(
        header_words=header_words,
        content_crc32=header_words[2],
        identifier=identifier,
        frame_count=frame_count,
        initial_state=initial_state,
        frames=tuple(frames),
    )


def parse_press(spec: str) -> InputEdit:
    parts = spec.lower().split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(
            "input must be FRAME:BUTTON[:DURATION]"
        )
    try:
        frame = int(parts[0])
        duration = int(parts[2]) if len(parts) == 3 else 1
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "frame and duration must be integers"
        ) from exc
    button = parts[1]
    if frame < 0 or duration < 1:
        raise argparse.ArgumentTypeError(
            "frame must be non-negative and duration must be positive"
        )
    if button not in LIBRETRO_JOYPAD_IDS:
        valid = ", ".join(LIBRETRO_JOYPAD_IDS)
        raise argparse.ArgumentTypeError(
            f"unknown button {button!r}; expected one of: {valid}"
        )
    return frame, LIBRETRO_JOYPAD_IDS[button], duration, 1, button


def replace_initial_core_state(source: bytes, core_state: bytes) -> bytes:
    """Replace the BSV2 initial state with an uncompressed raw core state."""
    info = parse_movie(source)
    if len(core_state) < 8 or core_state[:4] != b"BST1":
        raise RuntimeError("replacement core state is not a BST1 state")
    declared_core_size = struct.unpack_from("<I", core_state, 4)[0]
    if declared_core_size != len(core_state):
        raise RuntimeError(
            "replacement BST1 length field does not match the state"
        )

    state_block = (
        bytes((0, 0))
        + struct.pack(
            "<III", len(core_state), len(core_state), len(core_state)
        )
        + core_state
    )
    old_start = HEADER_SIZE
    old_end = old_start + info.initial_state.size
    header = bytearray(source[:HEADER_SIZE])
    struct.pack_into("<I", header, 12, len(state_block))
    result = bytes(header) + state_block + source[old_end:]
    replaced_info = parse_movie(result)
    if replaced_info.frame_count != info.frame_count:
        raise AssertionError("initial-state replacement changed frame count")
    if result[
        HEADER_SIZE + len(state_block) :
    ] != source[old_end:]:
        raise AssertionError("initial-state replacement changed replay frames")
    return result


def edit_movie(
    source: bytes,
    inputs: list[InputEdit],
    *,
    allow_existing_inputs: bool = False,
) -> tuple[bytes, MovieInfo, int]:
    """Return an in-place-sized edit, parsed metadata, and changed values."""
    info = parse_movie(source)
    existing_nonzero = [
        (frame.number, event)
        for frame in info.frames
        for event in frame.inputs
        if event.value
    ]
    if existing_nonzero and not allow_existing_inputs:
        frame_number, event = existing_nonzero[0]
        raise RuntimeError(
            "source replay contains nonzero input values; first at "
            f"frame {frame_number}, event {event.identity}; refusing to "
            "edit without --allow-existing-inputs"
        )

    output = bytearray(source)
    changed_values = 0
    target_prefix = (
        PLAYER_ONE_PORT,
        LIBRETRO_DEVICE_JOYPAD,
        PLAYER_ONE_INDEX,
    )
    for frame, input_id, duration, value, label in inputs:
        if frame + duration > info.frame_count:
            raise RuntimeError(
                f"{label} input at {frame}..{frame + duration - 1} "
                f"exceeds {info.frame_count} replay frames"
            )
        for current in range(frame, frame + duration):
            matches = [
                event
                for event in info.frames[current].inputs
                if event.identity == (*target_prefix, input_id)
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"frame {current} has {len(matches)} matching Player-1 "
                    f"{label} events; expected exactly one"
                )
            event = matches[0]
            current_value = struct.unpack_from(
                "<h", output, event.value_offset
            )[0]
            if current_value != 0:
                raise RuntimeError(
                    f"{label} input at frame {current} overlaps existing "
                    f"value {current_value}"
                )
            struct.pack_into("<h", output, event.value_offset, value)
            changed_values += 1

    return bytes(output), info, changed_values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument(
        "--press",
        action="append",
        default=[],
        type=parse_press,
        metavar="FRAME:BUTTON[:DURATION]",
        help="press a tagged Player-1 joypad button for one or more frames",
    )
    parser.add_argument(
        "--allow-existing-inputs",
        action="store_true",
        help=(
            "preserve existing nonzero values while adding only "
            "non-overlapping Player-1 inputs"
        ),
    )
    parser.add_argument(
        "--initial-rastate",
        type=pathlib.Path,
        help=(
            "replace the replay's initial state with the sole MEM core-state "
            "chunk from a compatible RASTATE file"
        ),
    )
    args = parser.parse_args()

    source = args.source.read_bytes()
    working = source
    if args.initial_rastate is not None:
        working = replace_initial_core_state(
            working,
            retroarch_rastate.extract_memory(
                args.initial_rastate.read_bytes()
            ),
        )
    result, info, changed_values = edit_movie(
        working,
        args.press,
        allow_existing_inputs=args.allow_existing_inputs,
    )
    if args.output.exists() and args.output.read_bytes() != result:
        raise RuntimeError(f"refusing to overwrite changed output: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)

    print(f"source_sha256={sha256(source)}")
    if working != source:
        print(f"initial_state_replaced_sha256={sha256(working)}")
    print(f"output_sha256={sha256(result)}")
    print(f"content_crc32=0x{info.content_crc32:08X}")
    print(f"identifier=0x{info.identifier:016X}")
    print(f"initial_state_size={info.initial_state.size}")
    print(f"frames={info.frame_count}")
    print(f"changed_values={changed_values}")
    for frame, _, duration, value, label in args.press:
        print(f"input={frame}:p1:{label}:{duration}:value={value}")


if __name__ == "__main__":
    main()
