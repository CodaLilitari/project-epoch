#!/usr/bin/env python3
"""Generate original lookup tables for the 65C816 SHA-256 round8 candidate.

The output is an unplaced Asar include.  It contains no ROM mapping, address,
hook, or game data.  Every entry is derived from the public SHA-256 rotate and
shift definitions in this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections.abc import Callable, Iterable
from typing import Final


ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_sigma_tables.asm"
)

WORD_MASK: Final = 0xFFFFFFFF
BYTE_COUNT: Final = 4
BYTE_VALUES: Final = 0x100
ENTRY_SIZE: Final = 4
BYTE_TABLE_SIZE: Final = BYTE_VALUES * ENTRY_SIZE
TRANSFORM_SIZE: Final = BYTE_COUNT * BYTE_TABLE_SIZE
TABLE_SIZE: Final = 4 * TRANSFORM_SIZE
ENTRIES_PER_LINE: Final = 4
SPEC_ID: Final = "project-epoch-sha256-sigma-byte-tables-v1"


class SigmaTableError(ValueError):
    """Raised when generated table data violates its fixed contract."""


def _require_u32(value: object, field: str = "value") -> int:
    if type(value) is not int or not 0 <= value <= WORD_MASK:
        raise SigmaTableError(f"{field} must be an exact unsigned 32-bit int")
    return value


def rotate_right(value: int, count: int) -> int:
    value = _require_u32(value)
    if type(count) is not int or not 1 <= count <= 31:
        raise SigmaTableError("rotate count must be an exact int from 1 to 31")
    return ((value >> count) | (value << (32 - count))) & WORD_MASK


def big_sigma0(value: int) -> int:
    value = _require_u32(value)
    return (
        rotate_right(value, 2)
        ^ rotate_right(value, 13)
        ^ rotate_right(value, 22)
    )


def big_sigma1(value: int) -> int:
    value = _require_u32(value)
    return (
        rotate_right(value, 6)
        ^ rotate_right(value, 11)
        ^ rotate_right(value, 25)
    )


def small_sigma0(value: int) -> int:
    value = _require_u32(value)
    return (
        rotate_right(value, 7)
        ^ rotate_right(value, 18)
        ^ (value >> 3)
    )


def small_sigma1(value: int) -> int:
    value = _require_u32(value)
    return (
        rotate_right(value, 17)
        ^ rotate_right(value, 19)
        ^ (value >> 10)
    )


Transform = tuple[str, Callable[[int], int]]
TRANSFORMS: Final[tuple[Transform, ...]] = (
    ("BigSigma0", big_sigma0),
    ("BigSigma1", big_sigma1),
    ("SmallSigma0", small_sigma0),
    ("SmallSigma1", small_sigma1),
)


def basis_value(byte_position: int, byte_value: int) -> int:
    """Return one conceptual big-endian input byte in its 32-bit position."""

    if type(byte_position) is not int or not 0 <= byte_position < BYTE_COUNT:
        raise SigmaTableError("byte_position must be an exact int from 0 to 3")
    if type(byte_value) is not int or not 0 <= byte_value < BYTE_VALUES:
        raise SigmaTableError("byte_value must be an exact int from 0 to 255")
    return byte_value << (24 - 8 * byte_position)


def generate_tables() -> dict[str, tuple[tuple[int, ...], ...]]:
    """Generate four transforms x four byte positions x 256 u32 entries."""

    generated: dict[str, tuple[tuple[int, ...], ...]] = {}
    for name, transform in TRANSFORMS:
        positions = tuple(
            tuple(
                transform(basis_value(position, byte_value))
                for byte_value in range(BYTE_VALUES)
            )
            for position in range(BYTE_COUNT)
        )
        generated[name] = positions
    validate_tables(generated)
    return generated


def validate_tables(
    tables: dict[str, tuple[tuple[int, ...], ...]],
) -> None:
    if type(tables) is not dict:
        raise SigmaTableError("tables must be an exact dict")
    expected_names = tuple(name for name, _ in TRANSFORMS)
    if tuple(tables) != expected_names:
        raise SigmaTableError("table transform order or names changed")
    for name, transform in TRANSFORMS:
        positions = tables[name]
        if type(positions) is not tuple or len(positions) != BYTE_COUNT:
            raise SigmaTableError(f"{name} must have four position tables")
        for position, entries in enumerate(positions):
            if type(entries) is not tuple or len(entries) != BYTE_VALUES:
                raise SigmaTableError(
                    f"{name} byte {position} must have 256 entries"
                )
            for byte_value, actual in enumerate(entries):
                expected = transform(basis_value(position, byte_value))
                if type(actual) is not int or actual != expected:
                    raise SigmaTableError(
                        f"{name} byte {position} entry {byte_value} changed"
                    )


def reconstruct(
    transform_name: str,
    value: int,
    tables: dict[str, tuple[tuple[int, ...], ...]] | None = None,
) -> int:
    """Reconstruct one transform by XORing its four byte contributions."""

    value = _require_u32(value)
    if tables is None:
        tables = generate_tables()
    if type(tables) is not dict or transform_name not in tables:
        raise SigmaTableError(f"unknown transform {transform_name!r}")
    positions = tables[transform_name]
    if type(positions) is not tuple or len(positions) != BYTE_COUNT:
        raise SigmaTableError(
            f"{transform_name} must have four position tables"
        )
    result = 0
    for position in range(BYTE_COUNT):
        entries = positions[position]
        if type(entries) is not tuple or len(entries) != BYTE_VALUES:
            raise SigmaTableError(
                f"{transform_name} byte {position} must have 256 entries"
            )
        shift = 24 - 8 * position
        byte_value = (value >> shift) & 0xFF
        entry = entries[byte_value]
        result ^= _require_u32(
            entry,
            f"{transform_name} byte {position} entry {byte_value}",
        )
    return result


def entry_words(value: int) -> tuple[int, int]:
    """Return the core's numeric high-half, numeric low-half word order."""

    value = _require_u32(value)
    return value >> 16, value & 0xFFFF


def _chunks(values: tuple[int, ...], size: int) -> Iterable[tuple[int, ...]]:
    if len(values) % size:
        raise AssertionError("table line grouping must divide exactly")
    for start in range(0, len(values), size):
        yield values[start : start + size]


def render_include(
    tables: dict[str, tuple[tuple[int, ...], ...]] | None = None,
) -> bytes:
    """Render the deterministic, unplaced Asar table include."""

    if tables is None:
        tables = generate_tables()
    validate_tables(tables)

    lines = [
        "; GENERATED FILE - DO NOT EDIT BY HAND.",
        ";",
        "; Generator: tools/generate_schala_sha256_65816_sigma_tables.py",
        f"; Specification: {SPEC_ID}",
        "; Original mathematical data only; contains no game or ROM bytes.",
        ";",
        "; Contract:",
        ";   - unplaced Asar include (the consumer supplies mapping and org);",
        ";   - transforms: BigSigma0, BigSigma1, SmallSigma0, SmallSigma1;",
        ";   - Byte0 is input bits 31..24; Byte3 is input bits 7..0;",
        ";   - index each byte table with (conceptual_input_byte << 2);",
        ";   - each entry is dw numeric_high_16,numeric_low_16;",
        ";   - each byte table is $0400, each transform $1000, total $4000.",
        "",
        "EpochSha256SigmaTables_Start:",
    ]

    for name, _ in TRANSFORMS:
        transform_start = f"EpochSha256SigmaTables_{name}_Start"
        transform_end = f"EpochSha256SigmaTables_{name}_End"
        lines.extend(("", f"{transform_start}:"))
        for position, entries in enumerate(tables[name]):
            label = f"EpochSha256SigmaTables_{name}_Byte{position}"
            end_label = f"{label}_End"
            shift_high = 31 - position * 8
            shift_low = shift_high - 7
            lines.extend(
                (
                    "",
                    (
                        f"; {name} contribution from conceptual input bits "
                        f"{shift_high}..{shift_low}."
                    ),
                    f"{label}:",
                )
            )
            for chunk in _chunks(entries, ENTRIES_PER_LINE):
                words = [
                    word
                    for entry in chunk
                    for word in entry_words(entry)
                ]
                lines.append(
                    "    dw " + ",".join(f"${word:04X}" for word in words)
                )
            lines.extend(
                (
                    f"{end_label}:",
                    (
                        f'assert {end_label}-{label} == $0400, '
                        f'"{name} Byte{position} table size"'
                    ),
                )
            )
        lines.extend(
            (
                f"{transform_end}:",
                (
                    f"assert {transform_end}-{transform_start} == $1000, "
                    f'"{name} transform table size"'
                ),
            )
        )

    lines.extend(
        (
            "",
            "EpochSha256SigmaTables_End:",
            (
                "assert EpochSha256SigmaTables_End-"
                "EpochSha256SigmaTables_Start == $4000, "
                '"SHA-256 sigma table total size"'
            ),
            (
                "assert bank(EpochSha256SigmaTables_Start) == "
                "bank(EpochSha256SigmaTables_End-1), "
                '"SHA-256 sigma tables cross a bank"'
            ),
            "",
        )
    )
    rendered = "\n".join(lines).encode("ascii")
    if not rendered.endswith(b"\n"):
        raise AssertionError("generated include must end in one newline")
    return rendered


def generated_report(source: bytes) -> dict[str, object]:
    return {
        "specification": SPEC_ID,
        "output_size": len(source),
        "output_sha256": hashlib.sha256(source).hexdigest(),
        "binary_table_size": TABLE_SIZE,
        "transform_count": len(TRANSFORMS),
        "byte_tables_per_transform": BYTE_COUNT,
        "entries_per_byte_table": BYTE_VALUES,
        "entry_size": ENTRY_SIZE,
        "entry_word_order": "numeric-high16,numeric-low16",
        "input_byte_order": "Byte0=bits31..24,Byte3=bits7..0",
        "contains_game_data": False,
        "placed": False,
    }


def write_include(path: pathlib.Path = DEFAULT_OUTPUT) -> dict[str, object]:
    source = render_include()
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source)
    report = generated_report(source)
    report["output"] = str(path)
    report["status"] = "written"
    return report


def check_include(path: pathlib.Path = DEFAULT_OUTPUT) -> dict[str, object]:
    path = pathlib.Path(path)
    if not path.is_file():
        raise SigmaTableError(f"generated include is missing: {path}")
    expected = render_include()
    actual = path.read_bytes()
    if actual != expected:
        raise SigmaTableError(
            "generated include differs from deterministic generator output"
        )
    report = generated_report(actual)
    report["output"] = str(path)
    report["status"] = "current"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the existing include without writing it",
    )
    args = parser.parse_args()
    report = (
        check_include(args.output)
        if args.check
        else write_include(args.output)
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
