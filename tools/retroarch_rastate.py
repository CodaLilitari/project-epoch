#!/usr/bin/env python3
"""Parse RetroArch's chunked RASTATE container without decoding core state."""

from __future__ import annotations

import dataclasses
import struct


MAGIC = b"RASTATE"
VERSION = 1
HEADER_SIZE = 8
CHUNK_HEADER_SIZE = 8
MEMORY_TAG = b"MEM "
END_TAG = b"END "
ALIGNMENT = 8


@dataclasses.dataclass(frozen=True)
class Chunk:
    tag: bytes
    offset: int
    payload_offset: int
    payload_size: int
    end: int


@dataclasses.dataclass(frozen=True)
class Container:
    version: int
    chunks: tuple[Chunk, ...]


def _align(value: int) -> int:
    return (value + ALIGNMENT - 1) & ~(ALIGNMENT - 1)


def parse_container(source: bytes) -> Container:
    if len(source) < HEADER_SIZE or source[:7] != MAGIC:
        raise RuntimeError("not a RetroArch RASTATE container")
    version = source[7]
    if version != VERSION:
        raise RuntimeError(f"unsupported RASTATE version {version}")

    cursor = HEADER_SIZE
    chunks: list[Chunk] = []
    saw_end = False
    while cursor < len(source):
        if cursor % ALIGNMENT:
            raise RuntimeError(f"chunk at unaligned offset {cursor}")
        if cursor + CHUNK_HEADER_SIZE > len(source):
            raise RuntimeError(f"truncated chunk header at offset {cursor}")
        tag = source[cursor : cursor + 4]
        payload_size = struct.unpack_from("<I", source, cursor + 4)[0]
        payload_offset = cursor + CHUNK_HEADER_SIZE
        payload_end = payload_offset + payload_size
        if payload_end > len(source):
            raise RuntimeError(
                f"truncated {tag!r} payload at offset {payload_offset}"
            )
        end = _align(payload_end)
        if end > len(source):
            raise RuntimeError(f"truncated padding after {tag!r}")
        if any(source[payload_end:end]):
            raise RuntimeError(f"nonzero padding after {tag!r}")

        chunks.append(
            Chunk(
                tag=tag,
                offset=cursor,
                payload_offset=payload_offset,
                payload_size=payload_size,
                end=end,
            )
        )
        cursor = end
        if tag == END_TAG:
            if payload_size:
                raise RuntimeError("END chunk must have an empty payload")
            saw_end = True
            break

    if not saw_end:
        raise RuntimeError("RASTATE container has no END chunk")
    if cursor != len(source):
        raise RuntimeError(
            f"RASTATE container has {len(source) - cursor} trailing bytes"
        )
    return Container(version=version, chunks=tuple(chunks))


def extract_memory(source: bytes) -> bytes:
    container = parse_container(source)
    memory_chunks = [
        chunk for chunk in container.chunks if chunk.tag == MEMORY_TAG
    ]
    if len(memory_chunks) != 1:
        raise RuntimeError(
            f"RASTATE has {len(memory_chunks)} MEM chunks; expected one"
        )
    chunk = memory_chunks[0]
    return source[
        chunk.payload_offset : chunk.payload_offset + chunk.payload_size
    ]


def make_minimal_container(core_state: bytes) -> bytes:
    if not core_state:
        raise RuntimeError("core state must not be empty")
    output = bytearray(MAGIC + bytes((VERSION,)))
    output.extend(MEMORY_TAG)
    output.extend(struct.pack("<I", len(core_state)))
    output.extend(core_state)
    output.extend(bytes(_align(len(output)) - len(output)))
    output.extend(END_TAG)
    output.extend(struct.pack("<I", 0))
    result = bytes(output)
    if extract_memory(result) != core_state:
        raise AssertionError("minimal RASTATE reconstruction failed")
    return result
