#!/usr/bin/env python3
"""Build and audit the private standalone 65C816 SHA-256 benchmark ROM.

This is deliberately not a Chrono Trigger patch builder.  It never accepts a
source ROM.  A pinned Asar CLI is allowed to mutate only a temporary 8 MiB
all-$FF image below private/.  That output is treated as untrusted: only exact
source-labelled spans are imported into a fresh in-memory image, both ExHiROM
header checksum copies are finalized in Python, and complete diff coverage is
proved before the final private ROM is written.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import tempfile
import zipfile
from collections.abc import Mapping, Sequence

import schala_rom_scaffold as scaffold


VERSION = "1.0.2"

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (WORKSPACE_ROOT / "private").resolve()

DEFAULT_ASSEMBLY = (
    WORKSPACE_ROOT
    / "asm"
    / "schala_sidecar_sha256_profile1_benchmark.asm"
)
DEFAULT_ASAR_ARCHIVE = PRIVATE_ROOT / "tools" / "asar191.zip"
DEFAULT_ASAR_EXE = PRIVATE_ROOT / "tools" / "asar-1.91" / "asar.exe"
DEFAULT_OUTPUT_ROOT = PRIVATE_ROOT / "test_runs" / "sha256_65c816"
DEFAULT_OUTPUT_ROM = (
    DEFAULT_OUTPUT_ROOT / "schala_sha256_profile1_benchmark.sfc"
)
DEFAULT_OUTPUT_SRM = (
    DEFAULT_OUTPUT_ROOT / "schala_sha256_profile1_benchmark.srm"
)
DEFAULT_OUTPUT_MANIFEST = (
    DEFAULT_OUTPUT_ROOT / "schala_sha256_profile1_benchmark.manifest.json"
)

EXPECTED_ASAR_ARCHIVE_SIZE = 597_087
EXPECTED_ASAR_ARCHIVE_SHA256 = (
    "5d40f9cfa574360d8a3f382583556ba8757435274b35207977bf1cf20397b1e7"
)
EXPECTED_ASAR_EXE_SIZE = 501_248
EXPECTED_ASAR_EXE_SHA256 = (
    "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8"
)
EXPECTED_ASAR_DLL_SIZE = 379_392
EXPECTED_ASAR_DLL_SHA256 = (
    "bd25cd481dcb052d4e743380417a2a19c9e46c2be558a7ad754e1d7cc1f039de"
)
EXPECTED_ASAR_PY_SIZE = 14_076
EXPECTED_ASAR_PY_SHA256 = (
    "8f6a3c9c7431adfad545208c87aa68dfcdbc2f63a527b51975ddda3f5a5c95e0"
)

TARGET_SIZE = 0x800000
FILL_BYTE = 0xFF
BLANK_SOURCE_SHA256 = (
    "9f9b02f5ee6cbef5e018c1ee424095fc21a842ea6968c0d36114b5930dab2ba1"
)
SRAM_SIZE = 0x2000
ZERO_SRAM_SHA256 = (
    "9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47"
)

HEADER_SIZE = 0x40
HIROM_HEADER_SPAN = (0x00FFC0, 0x010000)
EXHIROM_HEADER_SPAN = (0x40FFC0, 0x410000)
HEADER_MAP_MODE = 0x15
HEADER_CARTRIDGE_TYPE = 0x16
HEADER_ROM_SIZE = 0x17
HEADER_SRAM_SIZE = 0x18
HEADER_COMPLEMENT = 0x1C
HEADER_CHECKSUM = 0x1E
EXHIROM_FAST = 0x35
ROM_SIZE_8_MIB = 0x0D
CARTRIDGE_ROM_RAM_BATTERY = 0x02
SRAM_SIZE_8_KIB = 0x03

NO_CASH_SYMBOL_RE = re.compile(
    r"^(?P<address>[0-9A-Fa-f]{8})\s+"
    r"(?P<label>[A-Za-z_:?.][A-Za-z0-9_:?.]*)$"
)
INCSRC_RE = re.compile(
    r'^\s*incsrc\s+"(?P<path>[^"]+)"', re.IGNORECASE | re.MULTILINE
)
INCBIN_RE = re.compile(r"^\s*incbin\b", re.IGNORECASE | re.MULTILINE)
FREESPACE_RE = re.compile(
    r"^\s*(?:freecode|freedata|freespace|autoclean)\b",
    re.IGNORECASE | re.MULTILINE,
)


class BenchmarkBuildError(RuntimeError):
    """Raised when the standalone build cannot remain fail closed."""


@dataclasses.dataclass(frozen=True)
class DeclaredSpan:
    span_id: str
    file_start: int
    file_end: int
    source: str

    @property
    def size(self) -> int:
        return self.file_end - self.file_start


@dataclasses.dataclass(frozen=True)
class AsarRun:
    untrusted_image: bytes
    symbols: Mapping[str, int]
    command: tuple[str, ...]
    stdout: bytes
    stderr: bytes


@dataclasses.dataclass(frozen=True)
class BuildResult:
    rom: bytes
    sram: bytes
    manifest: Mapping[str, object]
    manifest_bytes: bytes


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_relative(path: pathlib.Path) -> str:
    try:
        relative = path.resolve().relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise BenchmarkBuildError(
            f"path must remain below workspace: {path}"
        ) from exc
    return relative.as_posix()


def validate_private_path(
    path: pathlib.Path,
    *,
    suffixes: frozenset[str],
) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise BenchmarkBuildError(
            f"output must remain below private/: {path}"
        ) from exc
    if resolved.suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise BenchmarkBuildError(
            f"output {resolved.name} must use one of: {expected}"
        )
    return resolved


def _validate_exact_file(
    path: pathlib.Path,
    *,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> dict[str, object]:
    if not path.is_file():
        raise BenchmarkBuildError(f"{label} is missing: {path}")
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise BenchmarkBuildError(
            f"{label} size mismatch: expected {expected_size}, "
            f"got {actual_size}"
        )
    actual_hash = sha256_path(path)
    if actual_hash != expected_sha256:
        raise BenchmarkBuildError(
            f"{label} SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual_hash}"
        )
    return {
        "path": workspace_relative(path),
        "size": actual_size,
        "sha256": actual_hash,
    }


def _archive_member(
    archive: zipfile.ZipFile,
    name: str,
    *,
    expected_size: int,
    expected_sha256: str,
) -> dict[str, object]:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise BenchmarkBuildError(
            f"Asar archive is missing {name}"
        ) from exc
    if info.file_size != expected_size:
        raise BenchmarkBuildError(
            f"Asar archive member {name} has wrong size"
        )
    data = archive.read(info)
    actual_hash = sha256_bytes(data)
    if actual_hash != expected_sha256:
        raise BenchmarkBuildError(
            f"Asar archive member {name} has wrong SHA-256"
        )
    return {
        "path": name,
        "size": info.file_size,
        "sha256": actual_hash,
    }


def _pe_machine(path: pathlib.Path) -> int:
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise BenchmarkBuildError(f"not a PE image: {path}")
    pe_offset = int.from_bytes(data[0x3C:0x40], "little")
    if pe_offset + 6 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise BenchmarkBuildError(f"invalid PE header: {path}")
    return int.from_bytes(data[pe_offset + 4 : pe_offset + 6], "little")


def validate_asar_toolchain(
    archive_path: pathlib.Path = DEFAULT_ASAR_ARCHIVE,
    exe_path: pathlib.Path = DEFAULT_ASAR_EXE,
) -> dict[str, object]:
    archive_path = archive_path.resolve()
    exe_path = exe_path.resolve()
    archive_info = _validate_exact_file(
        archive_path,
        expected_size=EXPECTED_ASAR_ARCHIVE_SIZE,
        expected_sha256=EXPECTED_ASAR_ARCHIVE_SHA256,
        label="Asar 1.91 archive",
    )
    exe_info = _validate_exact_file(
        exe_path,
        expected_size=EXPECTED_ASAR_EXE_SIZE,
        expected_sha256=EXPECTED_ASAR_EXE_SHA256,
        label="Asar 1.91 executable",
    )

    with zipfile.ZipFile(archive_path) as archive:
        members = {
            "executable": _archive_member(
                archive,
                "asar.exe",
                expected_size=EXPECTED_ASAR_EXE_SIZE,
                expected_sha256=EXPECTED_ASAR_EXE_SHA256,
            ),
            "dll": _archive_member(
                archive,
                "dll/asar.dll",
                expected_size=EXPECTED_ASAR_DLL_SIZE,
                expected_sha256=EXPECTED_ASAR_DLL_SHA256,
            ),
            "python_binding": _archive_member(
                archive,
                "dll/bindings/python/asar.py",
                expected_size=EXPECTED_ASAR_PY_SIZE,
                expected_sha256=EXPECTED_ASAR_PY_SHA256,
            ),
        }

    if _pe_machine(exe_path) != 0x8664:
        raise BenchmarkBuildError("pinned Asar executable is not PE32+ x64")
    extracted_dll = exe_path.parent / "dll" / "asar.dll"
    # The installed layout keeps dll/ beside the archive extraction root,
    # rather than under the executable's parent on every installation.
    if not extracted_dll.exists():
        extracted_dll = exe_path.parent.parent / "dll" / "asar.dll"
    dll_info = _validate_exact_file(
        extracted_dll,
        expected_size=EXPECTED_ASAR_DLL_SIZE,
        expected_sha256=EXPECTED_ASAR_DLL_SHA256,
        label="Asar 1.91 DLL",
    )
    if _pe_machine(extracted_dll) != 0x014C:
        raise BenchmarkBuildError("pinned Asar DLL is not PE32 x86")

    version_run = subprocess.run(
        [str(exe_path), "--version"],
        check=False,
        capture_output=True,
        timeout=10,
    )
    version_output = version_run.stdout + version_run.stderr
    if version_run.returncode != 0 or b"Asar 1.91" not in version_output:
        raise BenchmarkBuildError("pinned Asar CLI did not report version 1.91")

    return {
        "archive": archive_info,
        "extracted_executable": {
            **exe_info,
            "pe_machine": "0x8664",
            "version_output_sha256": sha256_bytes(version_output),
        },
        "archive_members": members,
        "extracted_dll": {
            **dll_info,
            "pe_machine": "0x014C",
        },
        "python_inprocess_dll": {
            "usable_with_bundled_runtime": False,
            "bundled_python_pointer_bits": struct.calcsize("P") * 8,
            "dll_bits": 32,
            "reason": (
                "the official Asar 1.91 DLL is PE32 x86 while the bundled "
                "Python runtime is 64-bit; ctypes loading fails with "
                "Windows error 193"
            ),
        },
        "selected_interface": (
            "pinned CLI on a validated temporary target below private/"
        ),
    }


def collect_assembly_sources(
    entrypoint: pathlib.Path,
) -> tuple[dict[str, object], ...]:
    entrypoint = entrypoint.resolve()
    if not entrypoint.is_file():
        raise BenchmarkBuildError(f"assembly source is missing: {entrypoint}")
    pending = [entrypoint]
    seen: set[pathlib.Path] = set()
    records: list[dict[str, object]] = []
    asm_root = (WORKSPACE_ROOT / "asm").resolve()

    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        try:
            path.relative_to(asm_root)
        except ValueError as exc:
            raise BenchmarkBuildError(
                f"assembly include escapes asm/: {path}"
            ) from exc
        if path.suffix.lower() != ".asm":
            raise BenchmarkBuildError(
                f"assembly include is not an .asm file: {path}"
            )
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BenchmarkBuildError(
                f"assembly source is not UTF-8: {path}"
            ) from exc
        if INCBIN_RE.search(text):
            raise BenchmarkBuildError(
                f"binary includes are forbidden in standalone source: {path}"
            )
        if FREESPACE_RE.search(text):
            raise BenchmarkBuildError(
                f"freespace directives are forbidden: {path}"
            )
        records.append(
            {
                "path": workspace_relative(path),
                "size": len(raw),
                "sha256": sha256_bytes(raw),
            }
        )
        for match in INCSRC_RE.finditer(text):
            included = (path.parent / match.group("path")).resolve()
            pending.append(included)

    return tuple(sorted(records, key=lambda item: str(item["path"])))


def parse_nocash_symbols(source: bytes) -> dict[str, int]:
    try:
        text = source.decode("ascii")
    except UnicodeDecodeError as exc:
        raise BenchmarkBuildError("Asar symbol file is not ASCII") from exc
    result: dict[str, int] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        match = NO_CASH_SYMBOL_RE.fullmatch(stripped)
        if match is None:
            raise BenchmarkBuildError(
                f"unrecognized no$sns symbol line: {stripped}"
            )
        label = match.group("label")
        if label in result:
            raise BenchmarkBuildError(f"duplicate Asar symbol: {label}")
        address = int(match.group("address"), 16)
        if address > 0xFFFFFF:
            raise BenchmarkBuildError(
                f"Asar symbol lies outside the 24-bit SNES bus: {stripped}"
            )
        result[label] = address
    return result


def _label_span(
    symbols: Mapping[str, int],
    *,
    span_id: str,
    start_label: str,
    end_label: str,
    file_window: tuple[int, int],
) -> DeclaredSpan:
    try:
        snes_start = symbols[start_label]
        snes_end = symbols[end_label]
    except KeyError as exc:
        raise BenchmarkBuildError(
            f"benchmark source is missing required span label {exc.args[0]}"
        ) from exc
    size = snes_end - snes_start
    if not 0 < size <= 0x10000:
        raise BenchmarkBuildError(
            f"{span_id} source-label size is invalid: {size:#x}"
        )
    file_start = scaffold.exhirom_snes_to_file(snes_start)
    if file_start is None:
        raise BenchmarkBuildError(
            f"{span_id} start has no ExHiROM mapping: ${snes_start:06X}"
        )
    file_end = file_start + size
    if not (
        file_window[0] <= file_start < file_end <= file_window[1]
    ):
        raise BenchmarkBuildError(
            f"{span_id} lies outside its synthetic diagnostic window"
        )
    return DeclaredSpan(
        span_id=span_id,
        file_start=file_start,
        file_end=file_end,
        source=f"{start_label}..{end_label}",
    )


def declared_spans_from_symbols(
    symbols: Mapping[str, int],
) -> tuple[DeclaredSpan, ...]:
    spans = (
        DeclaredSpan(
            "hirom_header_vectors",
            HIROM_HEADER_SPAN[0],
            HIROM_HEADER_SPAN[1],
            "fixed standalone header copy",
        ),
        _label_span(
            symbols,
            span_id="reset_benchmark",
            start_label="Benchmark_BootStart",
            end_label="Benchmark_BootEnd",
            file_window=(0x408000, 0x40FFC0),
        ),
        DeclaredSpan(
            "exhirom_header_vectors",
            EXHIROM_HEADER_SPAN[0],
            EXHIROM_HEADER_SPAN[1],
            "fixed canonical ExHiROM header copy",
        ),
        _label_span(
            symbols,
            span_id="sha256_code",
            start_label="Benchmark_CoreStart",
            end_label="Benchmark_CoreEnd",
            file_window=(0x410000, 0x420000),
        ),
        _label_span(
            symbols,
            span_id="test_vectors",
            start_label="Benchmark_DataStart",
            end_label="Benchmark_DataEnd",
            file_window=(0x420000, 0x430000),
        ),
    )
    validate_declared_spans(spans)
    return tuple(sorted(spans, key=lambda item: item.file_start))


def validate_declared_spans(spans: Sequence[DeclaredSpan]) -> None:
    if not spans:
        raise BenchmarkBuildError("no standalone ROM spans were declared")
    ids: set[str] = set()
    previous: DeclaredSpan | None = None
    for span in sorted(spans, key=lambda item: item.file_start):
        if not span.span_id or span.span_id in ids:
            raise BenchmarkBuildError(
                f"duplicate or empty span ID: {span.span_id!r}"
            )
        ids.add(span.span_id)
        if not 0 <= span.file_start < span.file_end <= TARGET_SIZE:
            raise BenchmarkBuildError(
                f"{span.span_id} lies outside the 8 MiB image"
            )
        if previous is not None and previous.file_end > span.file_start:
            raise BenchmarkBuildError(
                f"{previous.span_id} overlaps {span.span_id}"
            )
        previous = span


def run_asar_untrusted(
    assembly_path: pathlib.Path,
    asar_exe: pathlib.Path,
) -> AsarRun:
    assembly_path = assembly_path.resolve()
    asar_exe = asar_exe.resolve()
    if not assembly_path.is_file():
        raise BenchmarkBuildError(
            f"assembly source is missing: {assembly_path}"
        )
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="sha256_65816_asar_",
        dir=PRIVATE_ROOT,
    ) as directory:
        temp_root = pathlib.Path(directory).resolve()
        try:
            temp_root.relative_to(PRIVATE_ROOT)
        except ValueError as exc:  # pragma: no cover - tempfile contract.
            raise BenchmarkBuildError(
                "temporary Asar directory escaped private/"
            ) from exc
        staging = temp_root / "untrusted_staging.sfc"
        symbols_path = temp_root / "untrusted_staging.sym"
        staging.write_bytes(bytes([FILL_BYTE]) * TARGET_SIZE)

        command = (
            str(asar_exe),
            "--no-title-check",
            "--fix-checksum=off",
            "--symbols=nocash",
            f"--symbols-path={symbols_path}",
            "-werror",
            assembly_path.name,
            str(staging),
        )
        completed = subprocess.run(
            command,
            cwd=assembly_path.parent,
            check=False,
            capture_output=True,
            timeout=60,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).decode(
                "utf-8", errors="replace"
            )
            raise BenchmarkBuildError(
                f"Asar failed with exit {completed.returncode}: {detail}"
            )
        if not symbols_path.is_file():
            raise BenchmarkBuildError("Asar did not emit the requested symbols")
        untrusted = staging.read_bytes()
        symbols = parse_nocash_symbols(symbols_path.read_bytes())
        return AsarRun(
            untrusted_image=untrusted,
            symbols=symbols,
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def import_declared_spans(
    untrusted: bytes,
    spans: Sequence[DeclaredSpan],
) -> bytearray:
    validate_declared_spans(spans)
    if len(untrusted) != TARGET_SIZE:
        raise BenchmarkBuildError(
            f"Asar changed image size to {len(untrusted):#x}"
        )
    ordered = sorted(spans, key=lambda item: item.file_start)
    cursor = 0
    for span in ordered:
        if any(value != FILL_BYTE for value in untrusted[cursor : span.file_start]):
            raise BenchmarkBuildError(
                f"Asar changed undeclared bytes before {span.span_id}"
            )
        if not any(
            value != FILL_BYTE
            for value in untrusted[span.file_start : span.file_end]
        ):
            raise BenchmarkBuildError(
                f"declared span {span.span_id} contains no assembler output"
            )
        cursor = span.file_end
    if any(value != FILL_BYTE for value in untrusted[cursor:]):
        raise BenchmarkBuildError(
            "Asar changed undeclared bytes after the final span"
        )

    candidate = bytearray([FILL_BYTE]) * TARGET_SIZE
    for span in ordered:
        candidate[span.file_start : span.file_end] = untrusted[
            span.file_start : span.file_end
        ]
    return candidate


def _write_u16(image: bytearray, offset: int, value: int) -> None:
    image[offset : offset + 2] = value.to_bytes(2, "little")


def finalize_dual_header_checksums(image: bytearray) -> None:
    if len(image) != TARGET_SIZE:
        raise BenchmarkBuildError("checksum finalizer requires exactly 8 MiB")
    for header in (scaffold.HIROM_HEADER, scaffold.EXHIROM_HEADER):
        _write_u16(image, header + HEADER_COMPLEMENT, 0xFFFF)
        _write_u16(image, header + HEADER_CHECKSUM, 0x0000)
    checksum = sum(image) & 0xFFFF
    complement = checksum ^ 0xFFFF
    for header in (scaffold.HIROM_HEADER, scaffold.EXHIROM_HEADER):
        _write_u16(image, header + HEADER_COMPLEMENT, complement)
        _write_u16(image, header + HEADER_CHECKSUM, checksum)


def _read_u16(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 2], "little")


def validate_final_image(
    image: bytes,
    spans: Sequence[DeclaredSpan],
) -> dict[str, object]:
    validate_declared_spans(spans)
    if len(image) != TARGET_SIZE:
        raise BenchmarkBuildError("final benchmark ROM is not exactly 8 MiB")
    checksum = sum(image) & 0xFFFF
    header_reports: list[dict[str, object]] = []
    for label, header in (
        ("hirom_copy", scaffold.HIROM_HEADER),
        ("canonical_exhirom", scaffold.EXHIROM_HEADER),
    ):
        if image[header + HEADER_MAP_MODE] != EXHIROM_FAST:
            raise BenchmarkBuildError(f"{label} map mode is not fast ExHiROM")
        if image[header + HEADER_CARTRIDGE_TYPE] != CARTRIDGE_ROM_RAM_BATTERY:
            raise BenchmarkBuildError(
                f"{label} does not declare ROM+RAM+battery"
            )
        if image[header + HEADER_ROM_SIZE] != ROM_SIZE_8_MIB:
            raise BenchmarkBuildError(f"{label} does not declare 8 MiB")
        if image[header + HEADER_SRAM_SIZE] != SRAM_SIZE_8_KIB:
            raise BenchmarkBuildError(f"{label} does not declare 8 KiB SRAM")
        complement = _read_u16(image, header + HEADER_COMPLEMENT)
        stored = _read_u16(image, header + HEADER_CHECKSUM)
        if complement ^ stored != 0xFFFF or stored != checksum:
            raise BenchmarkBuildError(f"{label} checksum pair is invalid")
        header_reports.append(
            {
                "copy": label,
                "file_offset": header,
                "map_mode": image[header + HEADER_MAP_MODE],
                "cartridge_type": image[
                    header + HEADER_CARTRIDGE_TYPE
                ],
                "rom_size_code": image[header + HEADER_ROM_SIZE],
                "sram_size_code": image[header + HEADER_SRAM_SIZE],
                "checksum": stored,
                "complement": complement,
            }
        )

    if (
        image[
            scaffold.HIROM_HEADER : scaffold.HIROM_HEADER + HEADER_SIZE
        ]
        != image[
            scaffold.EXHIROM_HEADER : scaffold.EXHIROM_HEADER + HEADER_SIZE
        ]
    ):
        raise BenchmarkBuildError("the two standalone header copies differ")

    ordered = sorted(spans, key=lambda item: item.file_start)
    cursor = 0
    changed_bytes = 0
    span_reports: list[dict[str, object]] = []
    for span in ordered:
        if any(value != FILL_BYTE for value in image[cursor : span.file_start]):
            raise BenchmarkBuildError(
                f"final image changed undeclared bytes before {span.span_id}"
            )
        payload = image[span.file_start : span.file_end]
        if not any(value != FILL_BYTE for value in payload):
            raise BenchmarkBuildError(
                f"final span {span.span_id} contains no output"
            )
        changed = sum(value != FILL_BYTE for value in payload)
        changed_bytes += changed
        span_reports.append(
            {
                "span_id": span.span_id,
                "file_start": span.file_start,
                "file_end_exclusive": span.file_end,
                "size": span.size,
                "source": span.source,
                "preimage_sha256": sha256_bytes(
                    bytes([FILL_BYTE]) * span.size
                ),
                "replacement_sha256": sha256_bytes(payload),
                "changed_byte_count": changed,
            }
        )
        cursor = span.file_end
    if any(value != FILL_BYTE for value in image[cursor:]):
        raise BenchmarkBuildError(
            "final image changed bytes after the final declared span"
        )
    if changed_bytes != sum(value != FILL_BYTE for value in image):
        raise BenchmarkBuildError("complete diff accounting mismatch")

    return {
        "status": "complete-diff-valid",
        "source_fill": FILL_BYTE,
        "source_size": TARGET_SIZE,
        "source_sha256": BLANK_SOURCE_SHA256,
        "target_size": len(image),
        "target_sha256": sha256_bytes(image),
        "changed_byte_count": changed_bytes,
        "declared_span_count": len(ordered),
        "all_changed_bytes_declared": True,
        "headers": header_reports,
        "spans": span_reports,
    }


def _normalized_command(
    assembly_path: pathlib.Path,
    asar_exe: pathlib.Path,
) -> list[str]:
    return [
        workspace_relative(asar_exe),
        "--no-title-check",
        "--fix-checksum=off",
        "--symbols=nocash",
        "--symbols-path=<private-temp>/untrusted_staging.sym",
        "-werror",
        workspace_relative(assembly_path),
        "<private-temp>/untrusted_staging.sfc",
    ]


def _output_record(path: pathlib.Path, data: bytes) -> dict[str, object]:
    return {
        "path": workspace_relative(path),
        "size": len(data),
        "sha256": sha256_bytes(data),
    }


def _validated_output_paths(
    output_rom: pathlib.Path,
    output_srm: pathlib.Path,
    output_manifest: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    output_rom = validate_private_path(
        output_rom, suffixes=frozenset({".sfc", ".smc"})
    )
    output_srm = validate_private_path(
        output_srm, suffixes=frozenset({".srm"})
    )
    output_manifest = validate_private_path(
        output_manifest, suffixes=frozenset({".json"})
    )
    if output_srm.stem != output_rom.stem:
        raise BenchmarkBuildError(
            "ROM and SRAM must use the same stem for current bsnes"
        )
    if len({output_rom, output_srm, output_manifest}) != 3:
        raise BenchmarkBuildError("output paths must be distinct")
    return output_rom, output_srm, output_manifest


def build_in_memory(
    *,
    assembly_path: pathlib.Path = DEFAULT_ASSEMBLY,
    asar_archive: pathlib.Path = DEFAULT_ASAR_ARCHIVE,
    asar_exe: pathlib.Path = DEFAULT_ASAR_EXE,
    output_rom: pathlib.Path = DEFAULT_OUTPUT_ROM,
    output_srm: pathlib.Path = DEFAULT_OUTPUT_SRM,
    output_manifest: pathlib.Path = DEFAULT_OUTPUT_MANIFEST,
) -> BuildResult:
    assembly_path = assembly_path.resolve()
    asar_archive = asar_archive.resolve()
    asar_exe = asar_exe.resolve()
    output_rom, output_srm, output_manifest = _validated_output_paths(
        output_rom, output_srm, output_manifest
    )

    toolchain = validate_asar_toolchain(asar_archive, asar_exe)
    sources = collect_assembly_sources(assembly_path)
    asar_run = run_asar_untrusted(assembly_path, asar_exe)
    spans = declared_spans_from_symbols(asar_run.symbols)
    candidate = import_declared_spans(asar_run.untrusted_image, spans)
    finalize_dual_header_checksums(candidate)
    rom = bytes(candidate)
    audit = validate_final_image(rom, spans)
    sram = bytes(SRAM_SIZE)
    if sha256_bytes(sram) != ZERO_SRAM_SHA256:
        raise AssertionError("internal zero-SRAM vector mismatch")

    manifest: dict[str, object] = {
        "schema_version": 1,
        "builder_version": VERSION,
        "builder_source": {
            "path": workspace_relative(pathlib.Path(__file__)),
            "size": pathlib.Path(__file__).stat().st_size,
            "sha256": sha256_path(pathlib.Path(__file__)),
        },
        "artifact_class": "standalone-original-diagnostic-rom",
        "status": "verified-static-host-build",
        "evidence_level": "verified-static",
        "private_only": True,
        "production_input": False,
        "chrono_trigger_source_rom_read": False,
        "project_epoch_production_catalogs_used": False,
        "project_epoch_hooks_installed": False,
        "project_epoch_rom_write_guard": {
            "used_as_production_approval": False,
            "reason": (
                "the existing guard recognizes only canonical or inert "
                "Chrono-derived sources; this original standalone diagnostic "
                "instead has a separate all-$FF complete-diff audit"
            ),
        },
        "assembly_sources": list(sources),
        "toolchain": toolchain,
        "assembler_run": {
            "interface": "pinned-cli-private-temporary-target",
            "command": _normalized_command(assembly_path, asar_exe),
            "exit_status": 0,
            "stdout_sha256": sha256_bytes(asar_run.stdout),
            "stderr_sha256": sha256_bytes(asar_run.stderr),
            "untrusted_output_sha256": sha256_bytes(
                asar_run.untrusted_image
            ),
            "untrusted_output_written_to_final_path": False,
            "only_declared_spans_imported": True,
        },
        "host_audit": audit,
        "outputs": {
            "rom": _output_record(output_rom, rom),
            "sram": {
                **_output_record(output_srm, sram),
                "initialization": "all-zero disposable 8 KiB",
            },
            "manifest": {
                "path": workspace_relative(output_manifest),
                "self_hash_embedded": False,
            },
        },
        "reproduction": {
            "working_directory": ".",
            "command": [
                "python",
                "tools/build_sha256_65816_standalone_benchmark.py",
                "--assembly",
                workspace_relative(assembly_path),
                "--asar-archive",
                workspace_relative(asar_archive),
                "--asar-exe",
                workspace_relative(asar_exe),
                "--output-rom",
                workspace_relative(output_rom),
                "--output-srm",
                workspace_relative(output_srm),
                "--manifest",
                workspace_relative(output_manifest),
            ],
        },
        "runtime_status": {
            "executed_by_this_builder": False,
            "supported_target": "RetroArch 1.22.2 / current bsnes 115",
            "claim": (
                "host construction only; emulator execution and digest "
                "inspection are separate evidence"
            ),
        },
        "limitations": [
            "does not approve any Chrono Trigger hook or allocation",
            "does not prove that any Chrono Trigger WRAM scratch span is free",
            "does not prove save, load, New Game+, erase, or preview integration",
            "does not make the SHA routine production-installable",
        ],
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return BuildResult(
        rom=rom,
        sram=sram,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
    )


def _refuse_conflicting_existing(
    artifacts: Sequence[tuple[pathlib.Path, bytes]],
) -> None:
    for path, expected in artifacts:
        if path.exists() and path.read_bytes() != expected:
            raise BenchmarkBuildError(
                f"refusing to overwrite a different existing artifact: {path}"
            )


def write_build(
    result: BuildResult,
    *,
    output_rom: pathlib.Path = DEFAULT_OUTPUT_ROM,
    output_srm: pathlib.Path = DEFAULT_OUTPUT_SRM,
    output_manifest: pathlib.Path = DEFAULT_OUTPUT_MANIFEST,
) -> None:
    output_rom, output_srm, output_manifest = _validated_output_paths(
        output_rom, output_srm, output_manifest
    )
    artifacts = (
        (output_rom, result.rom),
        (output_srm, result.sram),
        (output_manifest, result.manifest_bytes),
    )
    _refuse_conflicting_existing(artifacts)
    for path, data in artifacts:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        if path.stat().st_size != len(data) or sha256_path(path) != sha256_bytes(
            data
        ):
            raise BenchmarkBuildError(
                f"written artifact failed read-back verification: {path}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--assembly", type=pathlib.Path, default=DEFAULT_ASSEMBLY
    )
    parser.add_argument(
        "--asar-archive", type=pathlib.Path, default=DEFAULT_ASAR_ARCHIVE
    )
    parser.add_argument(
        "--asar-exe", type=pathlib.Path, default=DEFAULT_ASAR_EXE
    )
    parser.add_argument(
        "--output-rom", type=pathlib.Path, default=DEFAULT_OUTPUT_ROM
    )
    parser.add_argument(
        "--output-srm", type=pathlib.Path, default=DEFAULT_OUTPUT_SRM
    )
    parser.add_argument(
        "--manifest", type=pathlib.Path, default=DEFAULT_OUTPUT_MANIFEST
    )
    args = parser.parse_args()

    result = build_in_memory(
        assembly_path=args.assembly,
        asar_archive=args.asar_archive,
        asar_exe=args.asar_exe,
        output_rom=args.output_rom,
        output_srm=args.output_srm,
        output_manifest=args.manifest,
    )
    write_build(
        result,
        output_rom=args.output_rom,
        output_srm=args.output_srm,
        output_manifest=args.manifest,
    )
    print(f"rom_sha256={sha256_bytes(result.rom)}")
    print(f"sram_sha256={sha256_bytes(result.sram)}")
    print(f"manifest_sha256={sha256_bytes(result.manifest_bytes)}")
    print(f"wrote_rom={args.output_rom.resolve()}")
    print(f"wrote_srm={args.output_srm.resolve()}")
    print(f"wrote_manifest={args.manifest.resolve()}")


if __name__ == "__main__":
    main()
