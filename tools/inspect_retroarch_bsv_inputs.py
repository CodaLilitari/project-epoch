#!/usr/bin/env python3
"""Inspect a pinned RetroArch v1.7.1 BSV1 callback stream.

The installed v1.7.1 frontend records one byte per libretro input callback.
For the pinned bsnes2014 core, one calibrated auto-joypad latch is twelve
player-1 callbacks followed by twelve player-2 callbacks, each in joypad-ID
order.  Newer versioned RetroArch replay files use a different format and are
intentionally out of scope.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import struct


BUTTONS_PER_PORT = 12
PORTS_PER_LATCH = 2
STREAM_SLOTS_PER_LATCH = BUTTONS_PER_PORT * PORTS_PER_LATCH
BYTES_PER_VALUE = 1
BYTES_PER_POLL_FRAME = STREAM_SLOTS_PER_LATCH * BYTES_PER_VALUE


@dataclasses.dataclass(frozen=True)
class MovieInfo:
    state_size: int
    input_offset: int
    poll_frames: int
    header_words: tuple[int, int, int]


@dataclasses.dataclass(frozen=True)
class InputSpan:
    start: int
    end: int
    slot: int
    value: int

    @property
    def duration(self) -> int:
        return self.end - self.start


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_movie(source: bytes) -> tuple[MovieInfo, tuple[InputSpan, ...]]:
    if len(source) < 16 or source[:4] != b"BSV1":
        raise RuntimeError("not a supported BSV1 movie")

    header_words = struct.unpack_from("<III", source, 4)
    state_size = header_words[2]
    input_offset = 16 + state_size
    if input_offset > len(source):
        raise RuntimeError("embedded savestate extends beyond the movie")

    input_size = len(source) - input_offset
    if input_size % BYTES_PER_POLL_FRAME:
        raise RuntimeError(
            "input stream is not 24 one-byte callback values per joypad latch"
        )

    poll_frames = input_size // BYTES_PER_POLL_FRAME
    spans: list[InputSpan] = []
    active: dict[int, tuple[int, int]] = {}

    for frame in range(poll_frames):
        frame_offset = input_offset + frame * BYTES_PER_POLL_FRAME
        values = struct.unpack_from("<24B", source, frame_offset)
        for slot, value in enumerate(values):
            previous = active.get(slot)
            if previous is not None and previous[1] != value:
                start, old_value = previous
                spans.append(InputSpan(start, frame, slot, old_value))
                del active[slot]
            if value and slot not in active:
                active[slot] = (frame, value)

    for slot, (start, value) in active.items():
        spans.append(InputSpan(start, poll_frames, slot, value))

    spans.sort(key=lambda span: (span.start, span.slot, span.end, span.value))
    return (
        MovieInfo(
            state_size=state_size,
            input_offset=input_offset,
            poll_frames=poll_frames,
            header_words=header_words,
        ),
        tuple(spans),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    args = parser.parse_args()

    source = args.movie.read_bytes()
    info, spans = parse_movie(source)

    print(f"path={args.movie}")
    print(f"sha256={sha256(source)}")
    print(
        "header_words="
        + ",".join(f"0x{word:08X}" for word in info.header_words)
    )
    print(f"state_size={info.state_size}")
    print(f"state_sha256={sha256(source[16:info.input_offset])}")
    print(f"input_offset={info.input_offset}")
    print(f"poll_frames={info.poll_frames}")
    print(f"input_sha256={sha256(source[info.input_offset:])}")
    print(f"nonzero_spans={len(spans)}")
    for span in spans:
        print(
            f"input={span.start}:{span.slot}:{span.duration}:"
            f"value={span.value}"
        )


if __name__ == "__main__":
    main()
