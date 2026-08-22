#!/usr/bin/env python3
"""Rebind a pinned RetroArch BSV state to a byte-verified target ROM.

The BSV1 movie contains a BST1 savestate followed by its input stream.  The
pinned RetroArch/bsnes2014 state wrapper stores the loaded ROM's lowercase
SHA-256 text at state bytes $08-$47.  The BSV header also stores the content
CRC-32 at file bytes $08-$0B.  This helper replaces only those two identity
fields.  It never edits the serialized core payload or recorded controller
inputs.

This is a test-fixture operation, not a production ROM patch.  It is useful
when an inert ExHiROM expansion is byte-identical to a proven 4 MiB execution
checkpoint apart from header/mirror/unused-bank layout.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import struct
import zlib


BSV_MAGIC = b"BSV1"
BSV_HEADER_SIZE = 16
BSV_CONTENT_CRC_OFFSET = 0x08
BST_MAGIC = b"BST1"
ROM_ID_STATE_START = 0x08
ROM_ID_LENGTH = 0x40
PINNED_STATE_LENGTH = 329_133
SHA256_TEXT = re.compile(rb"[0-9a-f]{64}\Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def locate_state(movie: bytes) -> tuple[int, int]:
    if len(movie) < BSV_HEADER_SIZE or movie[:4] != BSV_MAGIC:
        raise RuntimeError("not a supported BSV1 movie")
    state_size = struct.unpack_from("<I", movie, 12)[0]
    if state_size != PINNED_STATE_LENGTH:
        raise RuntimeError(
            "embedded state length does not match the pinned bsnes2014 layout"
        )
    state_start = BSV_HEADER_SIZE
    state_end = state_start + state_size
    if state_end > len(movie):
        raise RuntimeError("embedded savestate extends beyond the movie")
    if movie[state_start : state_start + 4] != BST_MAGIC:
        raise RuntimeError("embedded state does not have a BST1 wrapper")
    return state_start, state_end


def embedded_rom_identity(movie: bytes) -> str:
    state_start, _ = locate_state(movie)
    start = state_start + ROM_ID_STATE_START
    value = movie[start : start + ROM_ID_LENGTH]
    if SHA256_TEXT.fullmatch(value) is None:
        raise RuntimeError("embedded ROM identity is not lowercase SHA-256 text")
    return value.decode("ascii")


def rebind_movie(
    movie: bytes,
    target_rom: bytes,
    *,
    expected_source_identity: str | None = None,
) -> tuple[bytes, str, str]:
    state_start, state_end = locate_state(movie)
    source_identity = embedded_rom_identity(movie)
    if (
        expected_source_identity is not None
        and source_identity != expected_source_identity.lower()
    ):
        raise RuntimeError(
            "embedded source ROM identity does not match the pinned expectation"
        )

    target_identity = sha256(target_rom)
    target_crc32 = zlib.crc32(target_rom) & 0xFFFFFFFF
    identity_start = state_start + ROM_ID_STATE_START
    identity_end = identity_start + ROM_ID_LENGTH
    rebound = bytearray(movie)
    struct.pack_into("<I", rebound, BSV_CONTENT_CRC_OFFSET, target_crc32)
    rebound[identity_start:identity_end] = target_identity.encode("ascii")
    result = bytes(rebound)

    differences = {
        offset
        for offset, (before, after) in enumerate(zip(movie, result, strict=True))
        if before != after
    }
    allowed = set(range(identity_start, identity_end)) | set(
        range(BSV_CONTENT_CRC_OFFSET, BSV_CONTENT_CRC_OFFSET + 4)
    )
    if differences - allowed:
        raise AssertionError("ROM identity rebind escaped the two metadata fields")
    if result[state_end:] != movie[state_end:]:
        raise AssertionError("ROM identity rebind changed recorded inputs")
    if embedded_rom_identity(result) != target_identity:
        raise AssertionError("rebound identity verification failed")
    return result, source_identity, target_identity


def validate_private_output(path: pathlib.Path) -> pathlib.Path:
    workspace = pathlib.Path(__file__).resolve().parents[1]
    private_root = (workspace / "private").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("output must remain under the workspace private/ tree") from exc
    if resolved.suffix.lower() != ".bsv":
        raise RuntimeError("output must use the .bsv movie suffix")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    parser.add_argument("target_rom", type=pathlib.Path)
    parser.add_argument("-o", "--out", required=True, type=pathlib.Path)
    parser.add_argument(
        "--expected-source-rom",
        type=pathlib.Path,
        help="require the embedded identity to match this source ROM",
    )
    args = parser.parse_args()

    movie = args.movie.read_bytes()
    target_rom = args.target_rom.read_bytes()
    source_content_crc32 = struct.unpack_from(
        "<I", movie, BSV_CONTENT_CRC_OFFSET
    )[0]
    expected = None
    if args.expected_source_rom is not None:
        expected = sha256(args.expected_source_rom.read_bytes())
    rebound, source_identity, target_identity = rebind_movie(
        movie,
        target_rom,
        expected_source_identity=expected,
    )
    output = validate_private_output(args.out)
    if output.exists() and output.read_bytes() != rebound:
        raise RuntimeError("refusing to overwrite a different existing movie")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rebound)

    _, state_end = locate_state(movie)
    print(f"input_movie_sha256={sha256(movie)}")
    print(f"source_content_crc32={source_content_crc32:08X}")
    print(f"source_rom_identity={source_identity}")
    print(f"target_content_crc32={zlib.crc32(target_rom) & 0xFFFFFFFF:08X}")
    print(f"target_rom_sha256={target_identity}")
    print(f"input_stream_sha256={sha256(movie[state_end:])}")
    print(f"output_movie_sha256={sha256(rebound)}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
