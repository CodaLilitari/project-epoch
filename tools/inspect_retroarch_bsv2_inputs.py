#!/usr/bin/env python3
"""Inspect tagged input spans in a RetroArch BSV2 replay."""

from __future__ import annotations

import argparse
import dataclasses
import pathlib

from edit_retroarch_bsv2_inputs import InputEvent, parse_movie, sha256


@dataclasses.dataclass(frozen=True)
class InputSpan:
    start: int
    end: int
    port: int
    device: int
    index: int
    input_id: int
    value: int

    @property
    def duration(self) -> int:
        return self.end - self.start


def find_nonzero_spans(source: bytes) -> tuple[InputSpan, ...]:
    info = parse_movie(source)
    spans: list[InputSpan] = []
    active: dict[tuple[int, int, int, int, int], int] = {}

    for frame in info.frames:
        current = {
            (
                event.port,
                event.device,
                event.index,
                event.input_id,
                event.value,
            )
            for event in frame.inputs
            if event.value
        }
        for identity, start in tuple(active.items()):
            if identity not in current:
                port, device, index, input_id, value = identity
                spans.append(
                    InputSpan(
                        start=start,
                        end=frame.number,
                        port=port,
                        device=device,
                        index=index,
                        input_id=input_id,
                        value=value,
                    )
                )
                del active[identity]
        for identity in current:
            active.setdefault(identity, frame.number)

    for identity, start in active.items():
        port, device, index, input_id, value = identity
        spans.append(
            InputSpan(
                start=start,
                end=info.frame_count,
                port=port,
                device=device,
                index=index,
                input_id=input_id,
                value=value,
            )
        )

    spans.sort(
        key=lambda span: (
            span.start,
            span.port,
            span.device,
            span.index,
            span.input_id,
            span.value,
        )
    )
    return tuple(spans)


def describe_event(event: InputEvent) -> str:
    return (
        f"port={event.port},device={event.device},index={event.index},"
        f"id={event.input_id},value={event.value}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    args = parser.parse_args()

    source = args.movie.read_bytes()
    info = parse_movie(source)
    spans = find_nonzero_spans(source)
    event_counts = [len(frame.inputs) for frame in info.frames]
    checkpoint_frames = [
        frame.number for frame in info.frames if frame.token != ord("f")
    ]

    print(f"path={args.movie}")
    print(f"sha256={sha256(source)}")
    print(f"version={info.header_words[1]}")
    print(f"content_crc32=0x{info.content_crc32:08X}")
    print(f"identifier=0x{info.identifier:016X}")
    print(f"initial_state_size={info.initial_state.size}")
    print(f"initial_state_compression={info.initial_state.compression}")
    print(f"initial_state_encoding={info.initial_state.encoding}")
    print(f"initial_state_decoded_size={info.initial_state.decoded_size}")
    print(f"initial_state_encoded_size={info.initial_state.encoded_size}")
    print(f"initial_state_payload_size={info.initial_state.payload_size}")
    print(f"frames={info.frame_count}")
    print(f"frames_without_input_events={event_counts.count(0)}")
    print(f"minimum_input_events={min(event_counts, default=0)}")
    print(f"maximum_input_events={max(event_counts, default=0)}")
    print(
        "checkpoint_frames="
        + (",".join(map(str, checkpoint_frames)) or "none")
    )
    print(f"nonzero_spans={len(spans)}")
    for span in spans:
        print(
            f"input={span.start}:{span.duration}:port={span.port}:"
            f"device={span.device}:index={span.index}:id={span.input_id}:"
            f"value={span.value}"
        )


if __name__ == "__main__":
    main()
