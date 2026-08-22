#!/usr/bin/env python3
"""Rebind only a RetroArch BSV2 content CRC to a byte-verified target ROM.

Current BSV2 stores the content CRC32 at header bytes $08-$0B.  Unlike the
legacy bsnes2014 wrapper, the current bsnes BST1 115.1 core state has no
lowercase ROM-SHA text field.  This helper changes only the BSV2 CRC field and
proves that the complete initial-state block and every replay frame remain
byte-identical.

Successful playback is still required to establish that a target ROM's mapper
and the embedded core state are compatible.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import struct
import zlib

import edit_retroarch_bsv2_inputs as bsv2


CONTENT_CRC_OFFSET = 8


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rebind_movie(
    movie: bytes,
    target_rom: bytes,
    *,
    expected_source_rom: bytes | None = None,
) -> tuple[bytes, int, int]:
    info = bsv2.parse_movie(movie)
    source_crc = info.content_crc32
    if expected_source_rom is not None:
        expected_crc = zlib.crc32(expected_source_rom) & 0xFFFFFFFF
        if source_crc != expected_crc:
            raise RuntimeError(
                "movie content CRC does not match the expected source ROM"
            )

    target_crc = zlib.crc32(target_rom) & 0xFFFFFFFF
    changed = bytearray(movie)
    struct.pack_into("<I", changed, CONTENT_CRC_OFFSET, target_crc)
    result = bytes(changed)
    rebound_info = bsv2.parse_movie(result)
    if rebound_info.content_crc32 != target_crc:
        raise AssertionError("rebound BSV2 CRC verification failed")

    differences = {
        index
        for index, pair in enumerate(zip(movie, result, strict=True))
        if pair[0] != pair[1]
    }
    allowed = set(range(CONTENT_CRC_OFFSET, CONTENT_CRC_OFFSET + 4))
    if differences - allowed:
        raise AssertionError("content rebind escaped the BSV2 CRC field")
    if result[:CONTENT_CRC_OFFSET] != movie[:CONTENT_CRC_OFFSET]:
        raise AssertionError("content rebind changed the BSV2 header prefix")
    if result[CONTENT_CRC_OFFSET + 4 :] != movie[CONTENT_CRC_OFFSET + 4 :]:
        raise AssertionError("content rebind changed state or replay frames")
    return result, source_crc, target_crc


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
    parser.add_argument("target_rom", type=pathlib.Path)
    parser.add_argument("-o", "--out", required=True, type=pathlib.Path)
    parser.add_argument(
        "--expected-source-rom",
        type=pathlib.Path,
        help="require the BSV2 CRC to match this source ROM",
    )
    args = parser.parse_args()

    movie = args.movie.read_bytes()
    target_rom = args.target_rom.read_bytes()
    expected_source = (
        args.expected_source_rom.read_bytes()
        if args.expected_source_rom is not None
        else None
    )
    result, source_crc, target_crc = rebind_movie(
        movie,
        target_rom,
        expected_source_rom=expected_source,
    )
    output = validate_private_output(args.out)
    if output.exists() and output.read_bytes() != result:
        raise RuntimeError(f"refusing to overwrite changed output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)

    print(f"input_movie_sha256={sha256(movie)}")
    print(f"source_content_crc32={source_crc:08X}")
    print(f"target_rom_sha256={sha256(target_rom)}")
    print(f"target_content_crc32={target_crc:08X}")
    print(f"output_movie_sha256={sha256(result)}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
