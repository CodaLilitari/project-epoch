#!/usr/bin/env python3
"""Run one private exploratory Mesen trace of relocated event $11C.

This launcher does not install anything into a ROM.  It derives the exact
source and transformed decompressed event packets in memory, writes them only
inside a disposable private staging directory, and asks the pinned Lua
collector to compare and apply that packet to live Work RAM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from typing import Any, NamedTuple


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
OLD_LAUNCHER_PATH = (
    ROOT / "tools" / "run_mesen_event11c_trace.py"
).resolve(strict=True)
AUDIT_PATH = (
    ROOT / "tools" / "audit_location_event_items.py"
).resolve(strict=True)
COLLECTOR = (
    ROOT / "tools" / "mesen_event11c_relocated_trace.lua"
).resolve(strict=True)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_event11c_relocated_trace.py"
).resolve(strict=True)

OLD_LAUNCHER_SHA256 = (
    "61915fa772761667c7d286a9a0bce3ce"
    "fbfb6c730cd311c521168d409acf5f0e"
)
AUDIT_SHA256 = (
    "cb39dd4485e6330c4f9d5b8817fe8e6"
    "a161cb2e965020cb1cd10a3fd30f7812a"
)
# These two hashes are intentionally explicit trust roots.  They are replaced
# with the frozen collaborator outputs before this launcher is accepted.
COLLECTOR_SHA256 = (
    "4413876f258c091a728a8d6d53e2aea8"
    "24206c5e7f9852ca476b5ee5c974070c"
)
VALIDATOR_SHA256 = (
    "2025a749fc3081ff7a6dfeb49b7b1c9a"
    "a6ae31241c4744be14c23d63e06de186"
)


class TraceLaunchError(RuntimeError):
    """Raised when a trace launch fails a safety or evidence check."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_pinned_bytes(
    path: Path,
    expected_sha256: str,
    label: str,
) -> bytes:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read pinned {label}: {path}") from exc
    actual_sha256 = hashlib.sha256(source).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"{label} SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    return source


def _load_pinned_module(name: str, path: Path, expected_sha256: str) -> Any:
    source = _read_pinned_bytes(path, expected_sha256, path.name)
    code = compile(source, str(path), "exec", dont_inherit=True)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except Exception:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return module


_OLD_LAUNCHER_SOURCE = _read_pinned_bytes(
    OLD_LAUNCHER_PATH,
    OLD_LAUNCHER_SHA256,
    "legacy safety-helper provenance",
)
COLLECTOR_SOURCE_BYTES = _read_pinned_bytes(
    COLLECTOR,
    COLLECTOR_SHA256,
    "relocated trace collector",
)
AUDIT = _load_pinned_module(
    "_project_epoch_event11c_relocation_audit",
    AUDIT_PATH,
    AUDIT_SHA256,
)
STRICT_VALIDATOR = _load_pinned_module(
    "_project_epoch_event11c_relocated_validator",
    VALIDATOR_PATH,
    VALIDATOR_SHA256,
)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def canonical_private_root() -> Path:
    lexical_private_root = ROOT / "private"
    try:
        private_root = lexical_private_root.resolve(strict=True)
    except OSError as exc:
        raise TraceLaunchError(
            f"workspace private directory does not exist: {lexical_private_root}"
        ) from exc
    if not private_root.is_dir():
        raise TraceLaunchError(
            f"workspace private path is not a directory: {private_root}"
        )
    if private_root != lexical_private_root:
        raise TraceLaunchError(
            "workspace private directory itself must not be a link or junction"
        )
    return private_root


def resolve_private_file(raw_path: str | Path, label: str) -> Path:
    private_root = canonical_private_root()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise TraceLaunchError(f"{label} is not an existing file: {candidate}") from exc
    if not resolved.is_file():
        raise TraceLaunchError(f"{label} is not a file: {resolved}")
    if not _inside(resolved, private_root):
        raise TraceLaunchError(f"{label} resolves outside {private_root}: {resolved}")
    return resolved


def prepare_private_output_dir(
    raw_path: str | Path,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> Path:
    private_root = canonical_private_root()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if os.path.lexists(candidate):
        raise TraceLaunchError(f"output directory must be a new path: {candidate}")
    resolved = candidate.resolve(strict=False)
    if not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"output directory resolves outside {private_root}: {resolved}"
        )
    for forbidden_root in forbidden_roots:
        forbidden = forbidden_root.resolve(strict=True)
        if _inside(resolved, forbidden) or _inside(forbidden, resolved):
            raise TraceLaunchError(
                f"output directory overlaps protected tree: {forbidden}"
            )
    resolved.mkdir(parents=True, exist_ok=False)
    resolved = resolved.resolve(strict=True)
    if not resolved.is_dir() or not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"created output directory escaped {private_root}: {resolved}"
        )
    return resolved


def require_hash(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise TraceLaunchError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def snapshot_private_files(directory: Path) -> dict[str, tuple[int, str]]:
    private_root = canonical_private_root()
    resolved_root = directory.resolve(strict=True)
    if not resolved_root.is_dir() or not _inside(resolved_root, private_root):
        raise TraceLaunchError(
            f"snapshot directory is not safely under private/: {resolved_root}"
        )
    snapshot: dict[str, tuple[int, str]] = {}
    for candidate in sorted(resolved_root.rglob("*")):
        if not candidate.is_file():
            continue
        resolved = candidate.resolve(strict=True)
        if not _inside(resolved, resolved_root):
            raise TraceLaunchError(
                f"snapshot file escapes guarded directory: {candidate}"
            )
        relative = resolved.relative_to(resolved_root).as_posix()
        if relative in snapshot:
            raise TraceLaunchError(f"duplicate canonical snapshot path: {relative}")
        snapshot[relative] = (resolved.stat().st_size, sha256_file(resolved))
    return snapshot


DEFAULT_MESEN = PRIVATE_ROOT / "tools" / "mesen2" / "app" / "Mesen.exe"
DEFAULT_ROM = (
    PRIVATE_ROOT
    / "test_runs"
    / "mesen2"
    / "event11c_checkpoint_v5"
    / "project_epoch_mesen_event11c_clean.sfc"
)
DEFAULT_STATE = (
    PRIVATE_ROOT
    / "test_runs"
    / "mesen2"
    / "event11c_checkpoint_v5"
    / "spekkio_talkable.mss"
)
DEFAULT_SRAM = (
    PRIVATE_ROOT
    / "tools"
    / "mesen2"
    / "app"
    / "Saves"
    / "project_epoch_mesen_event11c_clean.srm"
)

RUNTIME_HASHES = {
    "archive": "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe",
    "harfbuzz": "eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d",
    "mesen": "d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b",
    "mesen_core": "65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74",
    "nesdb": "cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307",
    "settings": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    "skia": "9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd",
    "state": "26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e",
    "sram": "a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9",
}

TRACE_SCHEMA = "project-epoch-mesen-event11c-relocated-trace-v2"
EXPECTED_EXIT_CODE = 41
MAX_TRACE_BYTES = 1024 * 1024
MAX_SCREENSHOT_BYTES = 16 * 1024 * 1024
CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)
EVENT_ID = 0x11C
EVENT_SNES_POINTER = 0xFAB19E
EVENT_FILE_POINTER = 0x3AB19E
EVENT_COMPRESSED_SIZE = 0x0776
EVENT_DECOMPRESSED_SIZE = 0x0C6B
SOURCE_PACKET_SHA256 = (
    "31d5b222828eca6c1c91a309f1543a8f"
    "dccf2e2f5deea7a4074b7376eaa70d8a"
)
TRANSFORMED_PACKET_SHA256 = (
    "8e2952bd5e8c25eaf0ad4244dece929b"
    "6f4fc1eea8317ea707fcd782c898e50b"
)
EXPECTED_EDIT_COUNT = 12
EXPECTED_DIFF_COUNT = 24

PINNED_HASHES = {
    "archive": RUNTIME_HASHES["archive"],
    "audit": AUDIT_SHA256,
    "collector": COLLECTOR_SHA256,
    "harfbuzz": RUNTIME_HASHES["harfbuzz"],
    "host_safety": OLD_LAUNCHER_SHA256,
    "mesen": RUNTIME_HASHES["mesen"],
    "mesen_core": RUNTIME_HASHES["mesen_core"],
    "nesdb": RUNTIME_HASHES["nesdb"],
    "rom": CANONICAL_ROM_SHA256,
    "settings": RUNTIME_HASHES["settings"],
    "skia": RUNTIME_HASHES["skia"],
    "state": RUNTIME_HASHES["state"],
    "sram": RUNTIME_HASHES["sram"],
    "validator": VALIDATOR_SHA256,
}

EXPECTED_OUTPUTS: dict[
    tuple[str, str],
    dict[str, tuple[int, str]],
] = {
    ("frog-robo", "zero"): {
        "trace": (
            5884,
            "645f6f4c1ce5ffac18a3a3cb8caf8b5115303fa4a3a5f2b32a089f55e70306fe",
        ),
        "screenshot": (
            9503,
            "0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb",
        ),
    },
    ("frog-robo", "canary"): {
        "trace": (
            5886,
            "27d1330a474391220b47a4a154d06e1ee6d416771456e94110d2332c82d1e7fe",
        ),
        "screenshot": (
            9503,
            "0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb",
        ),
    },
    ("crono-marle-lucca", "zero"): {
        "trace": (
            7715,
            "70006be6c842a940de366a9102c7ee80db1f8829f9078d3bf5369368a69f090b",
        ),
        "screenshot": (
            10421,
            "312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96",
        ),
    },
    ("crono-marle-lucca", "canary"): {
        "trace": (
            7717,
            "579fa7aaace23cbb1fdd1b0a040a00073552eafef2f8337ce4a616b3d644f595",
        ),
        "screenshot": (
            10421,
            "312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96",
        ),
    },
}


class PacketProvenance(NamedTuple):
    """Exact packet bytes plus the evidence needed to stage them safely."""

    source: bytes
    transformed: bytes
    source_sha256: str
    transformed_sha256: str
    compressed_size: int
    changed_offsets: tuple[int, ...]
    edit_count: int


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_exact_relocation_edits(
    source: bytes,
    transformed: bytes,
    edits: tuple[Any, ...],
) -> tuple[int, ...]:
    """Require the audit builder's exact 12 edits and exact 24 byte diffs."""
    if len(source) != len(transformed):
        raise TraceLaunchError("relocated event packet changed size")
    expected_sites = tuple(AUDIT.EXPECTED_COMPATIBILITY_RELOCATION_SITES)
    if len(edits) != EXPECTED_EDIT_COUNT or len(edits) != len(expected_sites):
        raise TraceLaunchError(
            f"relocated event requires exactly {EXPECTED_EDIT_COUNT} edits"
        )
    delta = (
        AUDIT.RELOCATED_COMPATIBILITY_WRAM_START
        - AUDIT.COMPATIBILITY_WRAM_START
    )
    for edit, (command_offset, opcode, old_address, width) in zip(
        edits,
        expected_sites,
        strict=True,
    ):
        expected = (
            EVENT_ID,
            AUDIT.COMPATIBILITY_EVENT_OBJECT_ID,
            command_offset,
            command_offset + 1,
            opcode,
            command_offset + 2,
            old_address,
            old_address + delta,
            width,
        )
        actual = (
            edit.event_id,
            edit.object_id,
            edit.event_data_command_offset,
            edit.packet_opcode_offset,
            edit.opcode,
            edit.packet_address_operand_offset,
            edit.old_address,
            edit.new_address,
            edit.width,
        )
        if actual != expected:
            raise TraceLaunchError(
                "relocated event edit metadata does not match the exact "
                f"pinned site at packet offset ${command_offset:04X}"
            )
        old_operand = old_address.to_bytes(3, "little")
        new_operand = (old_address + delta).to_bytes(3, "little")
        if (
            source[command_offset + 1] != opcode
            or transformed[command_offset + 1] != opcode
            or source[command_offset + 2:command_offset + 5]
            != old_operand
            or transformed[command_offset + 2:command_offset + 5]
            != new_operand
        ):
            raise TraceLaunchError(
                "relocated event packet bytes do not match the exact "
                f"old/new operands at packet offset ${command_offset:04X}"
            )

    changed_offsets = tuple(
        index
        for index, (old, new) in enumerate(zip(source, transformed))
        if old != new
    )
    expected_changed_offsets = tuple(
        byte_offset
        for command_offset, _opcode, _address, _width in expected_sites
        for byte_offset in (command_offset + 2, command_offset + 3)
    )
    if (
        len(changed_offsets) != EXPECTED_DIFF_COUNT
        or changed_offsets != expected_changed_offsets
    ):
        raise TraceLaunchError(
            "relocated event does not contain the exact 24 approved byte diffs"
        )
    return changed_offsets


def validate_packet_provenance(rom: bytes) -> PacketProvenance:
    """Derive and validate both event packets from one canonical ROM image."""
    try:
        identity = AUDIT.validate_canonical_rom(rom)
    except AUDIT.AuditError as exc:
        raise TraceLaunchError(
            f"canonical ROM provenance failed: {exc}"
        ) from exc
    if (
        identity.get("size") != CANONICAL_ROM_SIZE
        or identity.get("sha256") != CANONICAL_ROM_SHA256
    ):
        raise TraceLaunchError("canonical ROM identity metadata drifted")

    try:
        snes_pointer, file_pointer = AUDIT.event_pointer(rom, EVENT_ID)
    except AUDIT.AuditError as exc:
        raise TraceLaunchError(f"event $11C pointer lookup failed: {exc}") from exc
    if (
        snes_pointer != EVENT_SNES_POINTER
        or file_pointer != EVENT_FILE_POINTER
    ):
        raise TraceLaunchError(
            "event $11C pointer drifted: expected "
            f"${EVENT_SNES_POINTER:06X}/file ${EVENT_FILE_POINTER:06X}, got "
            f"${snes_pointer:06X}/file ${file_pointer:06X}"
        )

    try:
        packet = AUDIT.decompress_packet(rom, file_pointer)
    except AUDIT.AuditError as exc:
        raise TraceLaunchError(
            f"event $11C decompression failed: {exc}"
        ) from exc
    source = bytes(packet.data)
    source_sha256 = _sha256_bytes(source)
    if (
        packet.compressed_size != EVENT_COMPRESSED_SIZE
        or len(source) != EVENT_DECOMPRESSED_SIZE
        or source_sha256 != SOURCE_PACKET_SHA256
    ):
        raise TraceLaunchError(
            "event $11C source packet provenance does not match exact "
            "compressed/decompressed size and SHA-256"
        )

    try:
        transformed, edits = AUDIT.build_relocated_compatibility_event(
            EVENT_ID,
            source,
        )
    except AUDIT.AuditError as exc:
        raise TraceLaunchError(
            f"event $11C relocation builder failed: {exc}"
        ) from exc
    transformed = bytes(transformed)
    transformed_sha256 = _sha256_bytes(transformed)
    if (
        len(transformed) != EVENT_DECOMPRESSED_SIZE
        or transformed_sha256 != TRANSFORMED_PACKET_SHA256
    ):
        raise TraceLaunchError(
            "event $11C transformed packet size or SHA-256 drifted"
        )
    changed_offsets = validate_exact_relocation_edits(
        source,
        transformed,
        tuple(edits),
    )
    return PacketProvenance(
        source=source,
        transformed=transformed,
        source_sha256=source_sha256,
        transformed_sha256=transformed_sha256,
        compressed_size=packet.compressed_size,
        changed_offsets=changed_offsets,
        edit_count=len(edits),
    )


def derive_event11c_packets(rom_path: Path) -> PacketProvenance:
    try:
        rom = rom_path.read_bytes()
    except OSError as exc:
        raise TraceLaunchError(f"could not read canonical ROM: {rom_path}") from exc
    return validate_packet_provenance(rom)


def write_private_packet_files(
    staging_root: Path,
    provenance: PacketProvenance,
) -> dict[str, Path]:
    """Write raw packets exclusively beneath a fresh disposable root."""
    actual_changed_offsets = tuple(
        index
        for index, (old, new) in enumerate(
            zip(provenance.source, provenance.transformed)
        )
        if old != new
    )
    if (
        len(provenance.source) != EVENT_DECOMPRESSED_SIZE
        or len(provenance.transformed) != EVENT_DECOMPRESSED_SIZE
        or provenance.compressed_size != EVENT_COMPRESSED_SIZE
        or provenance.source_sha256 != SOURCE_PACKET_SHA256
        or provenance.transformed_sha256 != TRANSFORMED_PACKET_SHA256
        or _sha256_bytes(provenance.source) != SOURCE_PACKET_SHA256
        or _sha256_bytes(provenance.transformed)
        != TRANSFORMED_PACKET_SHA256
        or provenance.edit_count != EXPECTED_EDIT_COUNT
        or provenance.changed_offsets != actual_changed_offsets
        or len(actual_changed_offsets) != EXPECTED_DIFF_COUNT
    ):
        raise TraceLaunchError(
            "refusing to stage packet bytes without exact pinned provenance"
        )
    private_root = canonical_private_root()
    resolved_root = staging_root.resolve(strict=True)
    if (
        not resolved_root.is_dir()
        or not _inside(resolved_root, private_root)
    ):
        raise TraceLaunchError(
            "packet staging root is not safely beneath private/"
        )
    packet_root = resolved_root / "event11c_packets"
    packet_root.mkdir(exist_ok=False)
    paths = {
        "source_packet": packet_root / "source.bin",
        "transformed_packet": packet_root / "transformed.bin",
    }
    payloads = {
        "source_packet": (
            provenance.source,
            provenance.source_sha256,
        ),
        "transformed_packet": (
            provenance.transformed,
            provenance.transformed_sha256,
        ),
    }
    for label, path in paths.items():
        if os.path.lexists(path):
            raise TraceLaunchError(f"refusing to overwrite staged {label}")
        with path.open("xb") as handle:
            handle.write(payloads[label][0])
        resolved = path.resolve(strict=True)
        if not _inside(resolved, resolved_root) or resolved != path:
            raise TraceLaunchError(f"staged {label} escaped disposable root")
        expected_bytes, expected_hash = payloads[label]
        if (
            resolved.stat().st_size != len(expected_bytes)
            or sha256_file(resolved) != expected_hash
        ):
            raise TraceLaunchError(f"staged {label} failed exact hash check")
        paths[label] = resolved
    return paths


def load_trace_bytes(
    data: bytes,
    profile: str,
    variant: str,
    *,
    label: str = "trace",
) -> dict[str, Any]:
    if len(data) > MAX_TRACE_BYTES:
        raise TraceLaunchError(
            f"trace exceeds {MAX_TRACE_BYTES} bytes: {len(data)}"
        )
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise TraceLaunchError(
                    f"trace contains duplicate JSON key: {key}"
                )
            result[key] = value
        return result

    try:
        text = data.decode("utf-8")
        trace = json.loads(text, object_pairs_hook=reject_duplicate)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TraceLaunchError(f"could not parse trace JSON: {label}") from exc
    try:
        exact_profile, exact_variant = (
            STRICT_VALIDATOR.validate_trace_document(
                trace,
                label=label,
            )
        )
    except STRICT_VALIDATOR.TraceValidationError as exc:
        raise TraceLaunchError(
            f"strict trace validation failed: {exc}"
        ) from exc
    if exact_profile != profile or exact_variant != variant:
        raise TraceLaunchError("trace profile or variant mismatch")
    return trace


def load_trace(path: Path, profile: str, variant: str) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TraceLaunchError(f"could not read trace JSON: {path}") from exc
    return load_trace_bytes(data, profile, variant, label=str(path))


def read_direct_file(
    path: Path,
    label: str,
    *,
    root: Path,
    maximum: int,
    allow_empty: bool = False,
) -> bytes:
    if path.parent != root:
        raise TraceLaunchError(f"{label} is not a direct child of {root}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise TraceLaunchError(f"{label} is missing: {path}") from exc
    if (
        not resolved.is_file()
        or resolved != path
        or resolved.parent != root
    ):
        raise TraceLaunchError(f"{label} is not a direct regular file")
    try:
        with resolved.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise TraceLaunchError(f"{label} is not a regular file")
            data = handle.read(maximum + 1)
    except OSError as exc:
        raise TraceLaunchError(f"could not read {label}: {resolved}") from exc
    try:
        current = path.stat(follow_symlinks=False)
        still_direct = path.resolve(strict=True) == path
    except OSError as exc:
        raise TraceLaunchError(f"{label} changed while being read") from exc
    if (
        not still_direct
        or not stat.S_ISREG(current.st_mode)
        or (current.st_dev, current.st_ino)
        != (opened.st_dev, opened.st_ino)
    ):
        raise TraceLaunchError(f"{label} changed while being read")
    if len(data) > maximum:
        raise TraceLaunchError(f"{label} exceeds {maximum} bytes")
    if not allow_empty and not data:
        raise TraceLaunchError(f"{label} is empty")
    return data


def describe_artifact_bytes(
    data: bytes,
    label: str,
    *,
    png: bool = False,
    expected: tuple[int, str] | None = None,
) -> dict[str, Any]:
    if not data:
        raise TraceLaunchError(f"{label} is empty")
    if png and data[:8] != b"\x89PNG\r\n\x1a\n":
        raise TraceLaunchError(f"{label} is not a PNG")
    actual = (len(data), hashlib.sha256(data).hexdigest())
    if expected is not None and actual != expected:
        raise TraceLaunchError(
            f"{label} does not match accepted artifact: expected "
            f"{expected[0]}/{expected[1]}, got {actual[0]}/{actual[1]}"
        )
    return {"size": actual[0], "sha256": actual[1]}


def publish_output_pair(
    output_root: Path,
    trace_path: Path,
    trace_bytes: bytes,
    screenshot_path: Path,
    screenshot_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_artifact = describe_artifact_bytes(trace_bytes, "trace JSON")
    screenshot_artifact = describe_artifact_bytes(
        screenshot_bytes,
        "endpoint PNG",
        png=True,
    )
    created: list[tuple[Path, tuple[int, int]]] = []
    try:
        for path, data, label in (
            (trace_path, trace_bytes, "trace JSON"),
            (screenshot_path, screenshot_bytes, "endpoint PNG"),
        ):
            if path.parent != output_root or os.path.lexists(path):
                raise TraceLaunchError(f"refusing to overwrite {label}: {path}")
            try:
                with path.open("xb") as handle:
                    file_stat = os.fstat(handle.fileno())
                    created.append(
                        (path, (file_stat.st_dev, file_stat.st_ino))
                    )
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise TraceLaunchError(
                    f"refusing to overwrite {label}: {path}"
                ) from exc
            observed = read_direct_file(
                path,
                label,
                root=output_root,
                maximum=max(len(data), 1),
            )
            if observed != data:
                raise TraceLaunchError(f"published {label} bytes changed")
    except Exception:
        for path, identity in reversed(created):
            try:
                current = path.stat(follow_symlinks=False)
                if (
                    stat.S_ISREG(current.st_mode)
                    and (current.st_dev, current.st_ino) == identity
                ):
                    path.unlink()
            except OSError:
                pass
        raise
    trace_artifact["path"] = str(trace_path)
    screenshot_artifact["path"] = str(screenshot_path)
    return trace_artifact, screenshot_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one isolated relocated-event-$11C Mesen trace. The source "
            "and transformed packets are derived internally and exist only "
            "inside disposable private staging."
        )
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=("frog-robo", "crono-marle-lucca"),
    )
    parser.add_argument("--variant", required=True, choices=("zero", "canary"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help=(
            "allow a strict but non-accepted exploratory run without an "
            "exact output hash contract"
        ),
    )
    return parser


def _packet_summary(provenance: PacketProvenance) -> dict[str, Any]:
    return {
        "event_id": f"{EVENT_ID:03X}",
        "event_snes_pointer": f"{EVENT_SNES_POINTER:06X}",
        "event_file_pointer": f"{EVENT_FILE_POINTER:06X}",
        "compressed_size": provenance.compressed_size,
        "decompressed_size": len(provenance.source),
        "source_sha256": provenance.source_sha256,
        "transformed_sha256": provenance.transformed_sha256,
        "edit_count": provenance.edit_count,
        "diff_count": len(provenance.changed_offsets),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    case = (args.profile, args.variant)
    exploratory = bool(args.exploratory)
    expected_outputs = EXPECTED_OUTPUTS.get(case)
    if not exploratory and expected_outputs is None:
        raise TraceLaunchError(
            "this relocated trace has no accepted output contract; "
            "use --exploratory for a strict non-accepted diagnostic run"
        )
    if args.timeout < 1 or args.timeout > 300:
        raise TraceLaunchError("--timeout must be between 1 and 300 seconds")

    mesen = resolve_private_file(args.mesen, "Mesen executable")
    rom = resolve_private_file(args.rom, "canonical ROM")
    state = resolve_private_file(args.state, "native checkpoint")
    sram = resolve_private_file(args.sram, "disposable SRAM")
    private_root = canonical_private_root()
    archive = resolve_private_file(
        mesen.parent.parent / "Mesen_2.1.1_Windows.zip",
        "official Mesen archive",
    )
    harfbuzz = resolve_private_file(
        mesen.parent / "libHarfBuzzSharp.dll",
        "HarfBuzz runtime",
    )
    mesen_core = resolve_private_file(
        mesen.parent / "MesenCore.dll",
        "Mesen emulation core",
    )
    nesdb = resolve_private_file(
        mesen.parent / "MesenNesDB.txt",
        "Mesen database",
    )
    settings = resolve_private_file(
        mesen.parent / "settings.json",
        "portable Mesen settings",
    )
    skia = resolve_private_file(
        mesen.parent / "libSkiaSharp.dll",
        "Skia runtime",
    )
    shared_saves = (mesen.parent / "Saves").resolve(strict=True)
    shared_saves_before = snapshot_private_files(shared_saves)

    pinned_inputs = {
        "archive": archive,
        "audit": AUDIT_PATH,
        "collector": COLLECTOR,
        "harfbuzz": harfbuzz,
        "host_safety": OLD_LAUNCHER_PATH,
        "mesen": mesen,
        "mesen_core": mesen_core,
        "nesdb": nesdb,
        "rom": rom,
        "settings": settings,
        "skia": skia,
        "state": state,
        "sram": sram,
        "validator": VALIDATOR_PATH,
    }
    before = {
        label: require_hash(path, PINNED_HASHES[label], label)
        for label, path in pinned_inputs.items()
    }
    try:
        state_bytes = state.read_bytes()
    except OSError as exc:
        raise TraceLaunchError(f"could not read native checkpoint: {state}") from exc
    if hashlib.sha256(state_bytes).hexdigest() != PINNED_HASHES["state"]:
        raise TraceLaunchError("native checkpoint changed while being captured")
    if hashlib.sha256(COLLECTOR_SOURCE_BYTES).hexdigest() != before["collector"]:
        raise TraceLaunchError("in-memory collector provenance drifted")
    provenance = derive_event11c_packets(rom)

    output_dir = prepare_private_output_dir(
        args.output_dir,
        forbidden_roots=(shared_saves,),
    )
    trace_path = output_dir / "trace.json"
    screenshot_path = output_dir / "endpoint.png"
    if any(os.path.lexists(path) for path in (trace_path, screenshot_path)):
        raise TraceLaunchError("refusing to overwrite relocated trace output")

    completed: subprocess.CompletedProcess[str] | None = None
    process_error: Exception | None = None
    staging_error: Exception | None = None
    staged_changed: list[str] = []
    staging_root_after: Path | None = None
    trace: dict[str, Any] | None = None
    trace_bytes: bytes | None = None
    screenshot_bytes: bytes | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix=".event11c_relocated_staging_",
            dir=output_dir,
        ) as staging_directory:
            staging_root = Path(staging_directory).resolve(strict=True)
            staging_root_after = staging_root
            if not _inside(staging_root, private_root):
                raise TraceLaunchError(
                    "temporary staging directory escaped private/"
                )
            staged_app = staging_root / "app"
            staged_saves = staged_app / "Saves"
            staged_saves.mkdir(parents=True)
            staged_runtime_sources = {
                "mesen": mesen,
                "mesen_core": mesen_core,
                "harfbuzz": harfbuzz,
                "skia": skia,
                "nesdb": nesdb,
                "settings": settings,
            }
            staged_runtime_names = {
                "mesen": "Mesen.exe",
                "mesen_core": "MesenCore.dll",
                "harfbuzz": "libHarfBuzzSharp.dll",
                "skia": "libSkiaSharp.dll",
                "nesdb": "MesenNesDB.txt",
                "settings": "settings.json",
            }
            staged_runtime: dict[str, Path] = {}
            for label, source_path in staged_runtime_sources.items():
                destination = staged_app / staged_runtime_names[label]
                shutil.copyfile(source_path, destination)
                staged_runtime[label] = destination.resolve(strict=True)

            unique_stem = f"pe_event11c_relocated_{secrets.token_hex(12)}"
            staged_rom = staging_root / f"{unique_stem}.sfc"
            staged_sram = staged_saves / f"{unique_stem}.srm"
            staged_collector = staging_root / f"{unique_stem}.lua"
            staged_state = staging_root / f"{unique_stem}.mss"
            shutil.copyfile(rom, staged_rom)
            shutil.copyfile(sram, staged_sram)
            with staged_collector.open("xb") as handle:
                handle.write(COLLECTOR_SOURCE_BYTES)
            with staged_state.open("xb") as handle:
                handle.write(state_bytes)
            staged_rom = staged_rom.resolve(strict=True)
            staged_sram = staged_sram.resolve(strict=True)
            staged_collector = staged_collector.resolve(strict=True)
            staged_state = staged_state.resolve(strict=True)
            packet_paths = write_private_packet_files(
                staging_root,
                provenance,
            )
            staged_outputs = staging_root / "outputs"
            staged_outputs.mkdir(exist_ok=False)
            staged_trace = staged_outputs / "trace.json"
            staged_screenshot = staged_outputs / "endpoint.png"
            staged_error = staged_outputs / "trace.json.observer-error"
            for path in (staged_trace, staged_screenshot):
                with path.open("xb"):
                    pass
                if path.resolve(strict=True) != path:
                    raise TraceLaunchError("staged output path escaped staging")

            staged_files = {
                **staged_runtime,
                "collector": staged_collector,
                "rom": staged_rom,
                "sram": staged_sram,
                "state": staged_state,
                **packet_paths,
            }
            staged_expected = {
                label: before[label]
                for label in (
                    "mesen",
                    "mesen_core",
                    "harfbuzz",
                    "skia",
                    "nesdb",
                    "settings",
                    "rom",
                    "sram",
                    "state",
                )
            }
            staged_expected.update(
                {
                    "collector": before["collector"],
                    "source_packet": provenance.source_sha256,
                    "transformed_packet": provenance.transformed_sha256,
                }
            )
            for label, path in staged_files.items():
                if not _inside(path, staging_root):
                    raise TraceLaunchError(
                        f"staged {label} escaped private temporary root"
                    )
                if sha256_file(path) != staged_expected[label]:
                    raise TraceLaunchError(
                        f"staged {label} failed exact pre-launch hash check"
                    )

            environment = os.environ.copy()
            environment.update(
                {
                    "PE_STATE_PATH": str(staged_state),
                    "PE_TRACE_OUT": str(staged_trace),
                    "PE_TRACE_SCREENSHOT": str(staged_screenshot),
                    "PE_SOURCE_PACKET": str(packet_paths["source_packet"]),
                    "PE_TRANSFORMED_PACKET": str(
                        packet_paths["transformed_packet"]
                    ),
                    "PE_PROFILE": args.profile,
                    "PE_VARIANT": args.variant,
                }
            )
            command = [
                str(staged_runtime["mesen"]),
                "--testRunner",
                f"--timeout={args.timeout}",
                "--doNotSaveSettings",
                "--debug.scriptWindow.allowIoOsAccess=true",
                "--snes.port1.type=SnesController",
                str(staged_collector),
                str(staged_rom),
            ]
            creation_flags = (
                subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            try:
                completed = subprocess.run(
                    command,
                    cwd=staged_app,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout + 15,
                    check=False,
                    creationflags=creation_flags,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                process_error = exc

            for label, path in staged_files.items():
                try:
                    if sha256_file(path) != staged_expected[label]:
                        staged_changed.append(f"staged {label} changed")
                except OSError:
                    staged_changed.append(f"staged {label} missing")
            try:
                staged_save_entries = sorted(
                    path.name
                    for path in staged_saves.iterdir()
                    if path.is_file()
                )
            except OSError:
                staged_changed.append("staged Saves directory missing")
            else:
                if staged_save_entries != [staged_sram.name]:
                    staged_changed.append(
                        "staged Saves directory contains unexpected files"
                    )
            if (
                process_error is None
                and completed is not None
                and completed.returncode == EXPECTED_EXIT_CODE
            ):
                if os.path.lexists(staged_error):
                    raise TraceLaunchError(
                        "collector reported a staged observer error"
                    )
                trace_bytes = read_direct_file(
                    staged_trace,
                    "staged trace JSON",
                    root=staged_outputs,
                    maximum=MAX_TRACE_BYTES,
                )
                screenshot_bytes = read_direct_file(
                    staged_screenshot,
                    "staged endpoint PNG",
                    root=staged_outputs,
                    maximum=MAX_SCREENSHOT_BYTES,
                )
                describe_artifact_bytes(
                    screenshot_bytes,
                    "staged endpoint PNG",
                    png=True,
                )
                trace = load_trace_bytes(
                    trace_bytes,
                    args.profile,
                    args.variant,
                    label=str(staged_trace),
                )
                if not exploratory:
                    assert expected_outputs is not None
                    describe_artifact_bytes(
                        trace_bytes,
                        "trace JSON",
                        expected=expected_outputs["trace"],
                    )
                    describe_artifact_bytes(
                        screenshot_bytes,
                        "endpoint PNG",
                        png=True,
                        expected=expected_outputs["screenshot"],
                    )
    except Exception as exc:
        staging_error = exc

    changed: list[str] = []
    for label, path in pinned_inputs.items():
        try:
            after = sha256_file(path)
        except OSError:
            changed.append(f"{label} missing")
            continue
        if after != before[label]:
            changed.append(f"{label} changed")
    if changed:
        raise TraceLaunchError(
            "immutable emulator input mutation detected: "
            + ", ".join(changed)
        )
    shared_saves_after = snapshot_private_files(shared_saves)
    if shared_saves_after != shared_saves_before:
        raise TraceLaunchError("shared Mesen Saves directory changed")
    if (
        staging_root_after is not None
        and os.path.lexists(staging_root_after)
    ):
        raise TraceLaunchError(
            "disposable packet/ROM staging directory was not deleted"
        )
    if staged_changed:
        raise TraceLaunchError(
            "disposable emulator input mutation detected: "
            + ", ".join(staged_changed)
        )
    if staging_error is not None:
        if isinstance(staging_error, TraceLaunchError):
            raise staging_error
        raise TraceLaunchError(
            f"private relocated-trace staging failed: {staging_error}"
        ) from staging_error
    if process_error is not None:
        raise TraceLaunchError(
            f"Mesen launch failed: {process_error}"
        ) from process_error
    assert completed is not None
    if completed.returncode != EXPECTED_EXIT_CODE:
        detail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        suffix = f": {detail}" if detail else ""
        raise TraceLaunchError(
            f"Mesen returned {completed.returncode}, expected "
            f"{EXPECTED_EXIT_CODE}{suffix}"
        )
    if trace is None or trace_bytes is None or screenshot_bytes is None:
        raise TraceLaunchError(
            "Mesen did not produce both valid relocated-trace outputs"
        )
    trace_artifact, screenshot_artifact = publish_output_pair(
        output_dir,
        trace_path,
        trace_bytes,
        screenshot_path,
        screenshot_bytes,
    )
    if exploratory:
        status = "exploratory-private-diagnostic-case-not-accepted"
    else:
        status = "accepted-private-diagnostic-case"

    return {
        "status": status,
        "profile": args.profile,
        "variant": args.variant,
        "exit_code": completed.returncode,
        "callback_count": len(trace.get("callbacks", [])),
        "packet_provenance": _packet_summary(provenance),
        "trace": trace_artifact,
        "screenshot": screenshot_artifact,
        "immutable_inputs_preserved": True,
        "shared_mesen_saves_preserved": True,
        "disposable_staging_deleted": True,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except TraceLaunchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
