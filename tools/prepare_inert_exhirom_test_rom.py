#!/usr/bin/env python3
"""Write the inert Project Epoch ExHiROM only to ignored private test space."""

from __future__ import annotations

import argparse
import pathlib
import zlib

import schala_rom_scaffold


WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (WORKSPACE_ROOT / "private").resolve()


def validate_private_output(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise RuntimeError("output must remain under the workspace private/ tree") from exc
    if resolved.suffix.lower() not in {".sfc", ".smc"}:
        raise RuntimeError("test ROM output must use .sfc or .smc")
    return resolved


def write_inert_test_rom(
    source_path: pathlib.Path,
    output_path: pathlib.Path,
    *,
    expected_source_sha1: str = schala_rom_scaffold.EXPECTED_SOURCE_SHA1,
) -> tuple[bytes, pathlib.Path]:
    source = source_path.read_bytes()
    target = schala_rom_scaffold.expand_exhirom_scaffold(
        source,
        expected_sha1=expected_source_sha1,
    )
    resolved_output = validate_private_output(output_path)
    if source_path.resolve() == resolved_output:
        raise RuntimeError("source and output paths must differ")
    if resolved_output.exists() and resolved_output.read_bytes() != target:
        raise RuntimeError("refusing to overwrite a different existing file")
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_bytes(target)
    return target, resolved_output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument(
        "--expected-source-sha1",
        default=schala_rom_scaffold.EXPECTED_SOURCE_SHA1,
        help=(
            "pin a known diagnostic 4 MiB source instead of the canonical "
            "clean-ROM SHA-1"
        ),
    )
    args = parser.parse_args()

    target, output = write_inert_test_rom(
        args.source,
        args.output,
        expected_source_sha1=args.expected_source_sha1,
    )
    print(f"source_sha1={schala_rom_scaffold.digest(args.source.read_bytes(), 'sha1')}")
    print(f"target_sha256={schala_rom_scaffold.digest(target)}")
    print(f"target_crc32={zlib.crc32(target) & 0xFFFFFFFF:08X}")
    print(f"target_size=0x{len(target):X}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
