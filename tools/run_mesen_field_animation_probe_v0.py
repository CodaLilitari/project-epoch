#!/usr/bin/env python3
"""Run one isolated exploratory native-Mesen field-animation probe v0.

Importing this module reads no private path. Private runtime inputs are
resolved, hash-gated, staged, and rechecked only when :func:`run` executes.
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
import zlib
from typing import Any, Final, Mapping, Sequence


ROOT: Final = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT_LEXICAL: Final = ROOT / "private"
PRIVATE_TEST_RUNS_LEXICAL: Final = PRIVATE_ROOT_LEXICAL / "test_runs"
COLLECTOR: Final = ROOT / "tools" / "mesen_field_animation_probe_v0.lua"

LAUNCHER_VERSION: Final = 1
COLLECTOR_VERSION: Final = 1
LAUNCH_PROTOCOL: Final = "project-epoch-field-animation-launcher-v0"
TRACE_SCHEMA: Final = "project-epoch-private-mesen-field-animation-probe-v0"
HOST_SCHEMA: Final = "project-epoch-private-mesen-field-animation-probe-host-v0"
EVIDENCE_LEVEL: Final = "exploratory-runtime-not-accepted"
EXPECTED_EXIT_CODE: Final = 41
TERMINAL_FRAME: Final = 240
RIGHT_START_FRAME: Final = 20
RIGHT_END_FRAME: Final = 99
HOST_TIMEOUT_GRACE_SECONDS: Final = 15
MAX_TRACE_BYTES: Final = 16 * 1024 * 1024
MAX_SCREENSHOT_BYTES: Final = 16 * 1024 * 1024
ROM_SIZE: Final = 4 * 1024 * 1024

COLLECTOR_SIZE: Final = 19_345
COLLECTOR_SHA256: Final = (
    "9abca7bad4d7c11da1bf66462881de7e"
    "ed246d195e8ef9c884f4c945f11583c7"
)
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

DEFAULT_MESEN: Final = (
    PRIVATE_ROOT_LEXICAL / "tools" / "mesen2" / "app" / "Mesen.exe"
)
DEFAULT_ROM: Final = (
    PRIVATE_ROOT_LEXICAL
    / "test_runs"
    / "mesen2"
    / "event11c_checkpoint_v5"
    / "project_epoch_mesen_event11c_clean.sfc"
)
DEFAULT_STATE: Final = (
    PRIVATE_ROOT_LEXICAL
    / "test_runs"
    / "mesen2"
    / "event11c_checkpoint_v5"
    / "spekkio_talkable.mss"
)
DEFAULT_SRAM: Final = (
    PRIVATE_ROOT_LEXICAL
    / "tools"
    / "mesen2"
    / "app"
    / "Saves"
    / "project_epoch_mesen_event11c_clean.srm"
)

PINNED_IDENTITIES: Final[dict[str, tuple[int, str]]] = {
    "archive": (
        34_058_170,
        "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe",
    ),
    "mesen": (
        70_470_144,
        "d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b",
    ),
    "mesen_core": (
        7_143_424,
        "65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74",
    ),
    "harfbuzz": (
        1_804_872,
        "eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d",
    ),
    "skia": (
        9_414_216,
        "9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd",
    ),
    "nesdb": (
        559_118,
        "cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307",
    ),
    "settings": (
        3,
        "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    ),
    "rom": (ROM_SIZE, CANONICAL_ROM_SHA256),
    "state": (
        133_993,
        "26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e",
    ),
    "sram": (
        8_192,
        "a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9",
    ),
    "collector": (COLLECTOR_SIZE, COLLECTOR_SHA256),
}

RUNTIME_NAMES: Final = {
    "mesen": "Mesen.exe",
    "mesen_core": "MesenCore.dll",
    "harfbuzz": "libHarfBuzzSharp.dll",
    "skia": "libSkiaSharp.dll",
    "nesdb": "MesenNesDB.txt",
    "settings": "settings.json",
}

WATCHED: Final = {
    0xC0CA18: ("timing-selector-load", 0xBD, 0xCA18),
    0xC0CA35: ("timing-stream-read", 0xBF, 0xCA35),
    0xC0CA3D: ("timing-reload-read", 0xBF, 0xCA3D),
    0xC0CB3A: ("main-facing-pointer-entry", 0xBD, 0xCB3A),
    0xC0CBC2: ("main-frame-stream-read", 0xA7, 0xCBC2),
    0xC0CC04: ("frame-cache-compare", 0xDD, 0xCC04),
}
ORDERED_PCS: Final = tuple(WATCHED)

EXPECTED_BINDINGS: Final = (
    {
        "object_slot": 0x08,
        "logical_pc_id": 0x03,
        "object_status": 0x02,
        "main_base": 0x3CF0,
        "timing_base": 0xAB3C,
    },
    {
        "object_slot": 0x0A,
        "logical_pc_id": 0x04,
        "object_status": 0x01,
        "main_base": 0x4160,
        "timing_base": 0xAC58,
    },
    {
        "object_slot": 0x0E,
        "logical_pc_id": 0x06,
        "object_status": 0x00,
        "main_base": 0x4B00,
        "timing_base": 0xAEC0,
    },
)
BINDING_BY_SLOT: Final = {
    row["object_slot"]: row for row in EXPECTED_BINDINGS
}
BINDING_SLOT_BY_ID: Final = {
    row["logical_pc_id"]: row["object_slot"] for row in EXPECTED_BINDINGS
}

EXPECTED_COUNTS: Final = {
    "idle": {f"{pc:06X}": 192 for pc in ORDERED_PCS},
    "right": {
        "C0CA18": 188,
        "C0CA35": 188,
        "C0CA3D": 178,
        "C0CB3A": 188,
        "C0CBC2": 188,
        "C0CC04": 188,
    },
}

TRACE_TOP_KEYS: Final = {
    "schema",
    "evidence_level",
    "collector_version",
    "emulator",
    "route",
    "repetition",
    "observer",
    "input_contract",
    "checkpoint_bindings",
    "pre",
    "counts",
    "records",
    "post",
    "termination",
}
OBSERVER_KEYS: Final = {"mechanism", "write_calls", "watched_pc_mappings"}
MAPPING_KEYS: Final = {
    "pc24",
    "role",
    "opcode",
    "mapped_address",
    "mapping_is_prg_rom",
}
INPUT_KEYS: Final = {"terminal_frame", "right_start_frame", "right_end_frame"}
BINDING_KEYS: Final = {
    "object_slot",
    "logical_pc_id",
    "object_status",
    "main_base",
    "timing_base",
}
SNAPSHOT_KEYS: Final = {
    "location",
    "explore_mode",
    "dialog_state",
    "field_phase_mod16",
    "leader_object",
    "leader_x",
    "leader_y",
    "active_party_hex",
}
RECORD_KEYS: Final = {
    "seq",
    "frame",
    "pc24",
    "role",
    "opcode",
    "cpu",
    "object_slot",
    "object_status",
    "object_id",
    "selector",
    "cursor",
    "alt_mode",
    "alt_selector",
    "facing",
    "delay",
    "timing_base",
    "main_base",
    "facing_stride",
    "cached_frame",
    "assembly_bank",
    "assembly_base",
    "dp_c1",
    "dp_d6",
    "dp_d8",
    "dp_d9",
    "stream_address",
    "stream_value",
}
CPU_KEYS: Final = {"a", "x", "y", "d", "ps", "sp", "db"}
TERMINATION_KEYS: Final = {
    "collector_stopped",
    "success",
    "overflow",
    "observer_error",
}

REPARSE_ATTRIBUTE: Final = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)


class ProbeError(RuntimeError):
    """Fail-closed path, input, trace, or process error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_lexical_traversal(path: Path, label: str) -> None:
    if any(part in {".", ".."} for part in path.parts):
        raise ProbeError(f"{label} contains lexical traversal")


def _is_reparse(path: Path) -> bool:
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & REPARSE_ATTRIBUTE
    )


def _require_real_directory(path: Path, label: str) -> Path:
    if not os.path.lexists(path):
        raise ProbeError(f"{label} does not exist: {path}")
    if _is_reparse(path):
        raise ProbeError(f"{label} is a symlink, junction, or reparse point: {path}")
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise ProbeError(f"{label} is not a directory: {path}")
    return path.resolve(strict=True)


def canonical_private_root() -> Path:
    workspace = ROOT.resolve(strict=True)
    lexical = PRIVATE_ROOT_LEXICAL
    private_root = _require_real_directory(lexical, "workspace private root")
    expected = workspace / "private"
    if private_root != expected:
        raise ProbeError(
            f"workspace private root resolved away from {expected}: {private_root}"
        )
    return private_root


def _require_no_reparse_chain(root: Path, candidate: Path, label: str) -> None:
    root_absolute = Path(os.path.abspath(root))
    candidate_absolute = Path(os.path.abspath(candidate))
    try:
        relative = candidate_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise ProbeError(f"{label} is outside {root_absolute}: {candidate}") from exc
    current = root_absolute
    for part in relative.parts:
        current = current / part
        if not os.path.lexists(current):
            raise ProbeError(f"{label} path component does not exist: {current}")
        if _is_reparse(current):
            raise ProbeError(
                f"{label} crosses a symlink, junction, or reparse point: {current}"
            )


def resolve_private_file(
    raw_path: str | Path,
    label: str,
    *,
    private_root: Path | None = None,
) -> Path:
    root = canonical_private_root() if private_root is None else private_root
    raw = Path(raw_path)
    _reject_lexical_traversal(raw, label)
    candidate = raw if raw.is_absolute() else ROOT / raw
    if not os.path.lexists(candidate):
        raise ProbeError(f"{label} is not an existing file: {candidate}")
    _require_no_reparse_chain(root, candidate, label)
    resolved = candidate.resolve(strict=True)
    if not _inside(resolved, root):
        raise ProbeError(f"{label} resolved outside {root}: {resolved}")
    metadata = candidate.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ProbeError(f"{label} is not a direct regular file: {candidate}")
    return resolved


def resolve_private_directory(
    raw_path: str | Path,
    label: str,
    *,
    private_root: Path | None = None,
) -> Path:
    root = canonical_private_root() if private_root is None else private_root
    raw = Path(raw_path)
    _reject_lexical_traversal(raw, label)
    candidate = raw if raw.is_absolute() else ROOT / raw
    _require_no_reparse_chain(root, candidate, label)
    resolved = _require_real_directory(candidate, label)
    if not _inside(resolved, root):
        raise ProbeError(f"{label} resolved outside {root}: {resolved}")
    return resolved


def _ensure_real_child_directories(root: Path, parts: Sequence[str]) -> Path:
    current = root
    for part in parts:
        if part in {"", ".", ".."}:
            raise ProbeError("output directory contains an invalid segment")
        current = current / part
        if os.path.lexists(current):
            _require_real_directory(current, "output parent")
        else:
            current.mkdir()
            if _is_reparse(current):
                raise ProbeError(f"created output parent became a reparse point: {current}")
    return current


def prepare_private_output_dir(
    raw_path: str | Path,
    *,
    private_root: Path | None = None,
    forbidden_roots: Sequence[Path] = (),
) -> Path:
    root = canonical_private_root() if private_root is None else private_root
    raw = Path(raw_path)
    _reject_lexical_traversal(raw, "output directory")
    candidate = raw if raw.is_absolute() else ROOT / raw
    candidate = Path(os.path.abspath(candidate))
    if os.path.lexists(candidate):
        raise ProbeError(f"output directory must be a new path: {candidate}")

    test_runs_lexical = root / "test_runs"
    if os.path.lexists(test_runs_lexical):
        test_runs = _require_real_directory(
            test_runs_lexical,
            "workspace private test-runs root",
        )
    else:
        test_runs_lexical.mkdir()
        test_runs = _require_real_directory(
            test_runs_lexical,
            "workspace private test-runs root",
        )
    # Containment is first enforced on the absolute lexical path. Resolving an
    # untrusted path here would silently turn an in-tree symlink/junction into
    # its target and could bypass the reparse-point rejection below.
    if candidate == test_runs or not _inside(candidate, test_runs):
        raise ProbeError(
            f"output must be strictly under workspace {test_runs}: {candidate}"
        )

    for forbidden in forbidden_roots:
        protected = forbidden.resolve(strict=True)
        if _inside(candidate, protected) or _inside(protected, candidate):
            raise ProbeError(f"output overlaps protected directory: {protected}")

    relative = candidate.relative_to(test_runs)
    parent = _ensure_real_child_directories(test_runs, relative.parts[:-1])
    final = parent / relative.parts[-1]
    if os.path.lexists(final):
        raise ProbeError(f"output target appeared before creation: {final}")
    final.mkdir()
    if _is_reparse(final):
        raise ProbeError(f"created output is a reparse point: {final}")
    resolved = final.resolve(strict=True)
    if resolved == test_runs or not _inside(resolved, test_runs):
        raise ProbeError(f"created output escaped workspace test-runs root: {resolved}")
    for forbidden in forbidden_roots:
        protected = forbidden.resolve(strict=True)
        if _inside(resolved, protected) or _inside(protected, resolved):
            raise ProbeError(f"created output overlaps protected directory: {protected}")
    return resolved


def require_identity(path: Path, label: str) -> dict[str, Any]:
    expected_size, expected_sha256 = PINNED_IDENTITIES[label]
    actual_size = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_size != expected_size or actual_sha256 != expected_sha256:
        raise ProbeError(
            f"{label} identity mismatch: expected {expected_size}/{expected_sha256}, "
            f"got {actual_size}/{actual_sha256}"
        )
    return {
        "path": path,
        "size": actual_size,
        "sha256": actual_sha256,
    }


def snapshot_private_files(root: Path) -> dict[str, tuple[int, str]]:
    resolved_root = _require_real_directory(root, "snapshot root")
    result: dict[str, tuple[int, str]] = {}
    for candidate in sorted(root.rglob("*")):
        if _is_reparse(candidate):
            raise ProbeError(f"snapshot tree contains a reparse point: {candidate}")
        metadata = candidate.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ProbeError(f"snapshot tree contains a non-regular file: {candidate}")
        resolved = candidate.resolve(strict=True)
        if not _inside(resolved, resolved_root):
            raise ProbeError(f"snapshot file escaped guarded tree: {candidate}")
        relative = resolved.relative_to(resolved_root).as_posix()
        result[relative] = (metadata.st_size, sha256_file(candidate))
    return result


def require_file_hashes_unchanged(
    paths: Mapping[str, Path],
    expected_sha256: Mapping[str, str],
    label: str,
) -> None:
    """Fail if a guarded file disappeared, changed, or the guard set drifted."""

    if set(paths) != set(expected_sha256):
        raise ProbeError(f"{label} guard set drifted")
    changed: list[str] = []
    for name, path in paths.items():
        try:
            if sha256_file(path) != expected_sha256[name]:
                changed.append(name)
        except OSError:
            changed.append(name)
    if changed:
        raise ProbeError(f"{label} changed: " + ", ".join(sorted(changed)))


def require_staging_removed(path: Path) -> None:
    if os.path.lexists(path):
        raise ProbeError(f"disposable staging root was not deleted: {path}")


def copy_new_regular_file(source: Path, destination: Path, label: str) -> None:
    if os.path.lexists(destination):
        raise ProbeError(f"refusing to overwrite staged {label}: {destination}")
    try:
        shutil.copyfile(source, destination)
    except OSError as exc:
        raise ProbeError(f"failed to stage {label}: {exc}") from exc
    if _is_reparse(destination):
        raise ProbeError(f"staged {label} became a reparse point")
    metadata = destination.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ProbeError(f"staged {label} is not a direct regular file")


def require_exact_staged_save_entries(
    entries: Sequence[str],
    expected_sram_name: str,
) -> None:
    if list(entries) != [expected_sram_name]:
        raise ProbeError(f"staged Saves directory drifted: {list(entries)!r}")


def validate_png_bytes(source: bytes) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    if not isinstance(source, bytes) or not source.startswith(signature):
        raise ProbeError("endpoint screenshot is not a structurally valid PNG")
    position = len(signature)
    chunk_index = 0
    saw_ihdr = False
    saw_idat = False
    saw_iend = False
    while position < len(source):
        if len(source) - position < 12:
            raise ProbeError("endpoint PNG has a truncated chunk header")
        length = int.from_bytes(source[position : position + 4], "big")
        chunk_type = source[position + 4 : position + 8]
        position += 8
        if not all(
            ord("A") <= byte <= ord("Z") or ord("a") <= byte <= ord("z")
            for byte in chunk_type
        ):
            raise ProbeError("endpoint PNG has an invalid chunk type")
        chunk_end = position + length
        crc_end = chunk_end + 4
        if chunk_end < position or crc_end > len(source):
            raise ProbeError("endpoint PNG has a truncated chunk payload")
        payload = source[position:chunk_end]
        recorded_crc = int.from_bytes(source[chunk_end:crc_end], "big")
        computed_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if recorded_crc != computed_crc:
            raise ProbeError("endpoint PNG chunk CRC drifted")

        if chunk_index == 0:
            if chunk_type != b"IHDR" or length != 13:
                raise ProbeError("endpoint PNG does not start with one IHDR")
            width = int.from_bytes(payload[0:4], "big")
            height = int.from_bytes(payload[4:8], "big")
            bit_depth = payload[8]
            color_type = payload[9]
            allowed_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if (
                width < 1
                or width > 16_384
                or height < 1
                or height > 16_384
                or color_type not in allowed_depths
                or bit_depth not in allowed_depths[color_type]
                or payload[10] != 0
                or payload[11] != 0
                or payload[12] not in (0, 1)
            ):
                raise ProbeError("endpoint PNG IHDR fields are invalid")
            saw_ihdr = True
        elif chunk_type == b"IHDR":
            raise ProbeError("endpoint PNG contains a duplicate IHDR")

        if chunk_type == b"IDAT":
            if not saw_ihdr or saw_iend:
                raise ProbeError("endpoint PNG IDAT ordering is invalid")
            saw_idat = True
        if chunk_type == b"IEND":
            if length != 0 or not saw_idat or saw_iend:
                raise ProbeError("endpoint PNG IEND is invalid")
            saw_iend = True
            position = crc_end
            if position != len(source):
                raise ProbeError("endpoint PNG has trailing bytes after IEND")
            break

        position = crc_end
        chunk_index += 1
    if not saw_ihdr or not saw_idat or not saw_iend:
        raise ProbeError("endpoint PNG is missing IHDR, IDAT, or IEND")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode_json_object(source: bytes, label: str) -> dict[str, Any]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProbeError(f"{label} is not UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ProbeError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise ProbeError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProbeError(f"{label} root must be one JSON object")
    return value


def read_direct_regular_file(
    path: Path,
    label: str,
    *,
    parent: Path,
    maximum: int,
) -> bytes:
    if path.parent != parent or not os.path.lexists(path):
        raise ProbeError(f"{label} is not directly inside {parent}: {path}")
    if _is_reparse(path):
        raise ProbeError(f"{label} is a reparse point: {path}")
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ProbeError(f"{label} is not a regular file")
    if metadata.st_size <= 0 or metadata.st_size > maximum:
        raise ProbeError(f"{label} size is outside 1..{maximum}: {metadata.st_size}")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise ProbeError(f"{label} changed identity while opening")
        source = handle.read(maximum + 1)
    if len(source) > maximum:
        raise ProbeError(f"{label} exceeds {maximum} bytes")
    return source


def load_trace_file(path: Path, *, output_root: Path) -> dict[str, Any]:
    source = read_direct_regular_file(
        path,
        "trace JSON",
        parent=output_root,
        maximum=MAX_TRACE_BYTES,
    )
    return decode_json_object(source, str(path))


def _require_exact_keys(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ProbeError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise ProbeError(f"{label} keys drifted; missing={missing}, extra={extra}")
    return value


def _require_int(value: Any, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise ProbeError(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def _require_nullable_int(
    value: Any,
    minimum: int,
    maximum: int,
    label: str,
) -> int | None:
    if value is None:
        return None
    return _require_int(value, minimum, maximum, label)


def hirom_file_offset(address: int) -> int:
    bank = (address >> 16) & 0xFF
    low = address & 0xFFFF
    if bank < 0xC0 or bank > 0xFF:
        raise ProbeError(f"address is outside canonical HiROM banks: {address:06X}")
    return ((bank & 0x3F) << 16) | low


def _validate_snapshot(value: Any, label: str) -> Mapping[str, Any]:
    snapshot = _require_exact_keys(value, SNAPSHOT_KEYS, label)
    exact = {
        "location": 0x01D1,
        "explore_mode": 1,
        "dialog_state": 0,
        "leader_object": 0x0E,
        "leader_x": 1568,
        "leader_y": 2623,
        "active_party_hex": "060403",
    }
    for key, expected in exact.items():
        if snapshot[key] != expected or type(snapshot[key]) is not type(expected):
            raise ProbeError(f"{label}.{key} drifted")
    _require_int(snapshot["field_phase_mod16"], 0, 15, f"{label}.field_phase_mod16")
    return snapshot


def _validate_right_loop(records: Sequence[Mapping[str, Any]]) -> None:
    main_expected = [
        (20, 1, 0xE44DE1),
        (27, 2, 0xE44DE2),
        (34, 3, 0xE44DE3),
        (41, 4, 0xE44DE4),
        (48, 5, 0xE44DE5),
        (55, 0, 0xE44DE0),
        (62, 1, 0xE44DE1),
        (69, 2, 0xE44DE2),
        (76, 3, 0xE44DE3),
        (83, 4, 0xE44DE4),
        (90, 5, 0xE44DE5),
        (97, 0, 0xE44DE0),
    ]
    timing_expected = [
        (20, 1, 0xE4AEC5),
        (27, 2, 0xE4AEC6),
        (34, 3, 0xE4AEC7),
        (41, 4, 0xE4AEC8),
        (48, 5, 0xE4AEC9),
        (55, 6, 0xE4AECA),
        (62, 1, 0xE4AEC5),
        (69, 2, 0xE4AEC6),
        (76, 3, 0xE4AEC7),
        (83, 4, 0xE4AEC8),
        (90, 5, 0xE4AEC9),
        (97, 6, 0xE4AECA),
    ]
    reload_expected = [(55, 6, 0xE4AEC4), (97, 6, 0xE4AEC4)]

    def select(pc: int) -> list[tuple[int, int, int]]:
        return [
            (row["frame"], row["cursor"], row["stream_address"])
            for row in records
            if row["pc24"] == pc
            and row["object_slot"] == 0x0E
            and row["object_id"] == 0x06
            and row["selector"] == 0x01
        ]

    if select(0xC0CBC2) != main_expected:
        raise ProbeError("right-route main selector-01 loop drifted")
    if select(0xC0CA35) != timing_expected:
        raise ProbeError("right-route timing selector-01 loop drifted")
    if select(0xC0CA3D) != reload_expected:
        raise ProbeError("right-route timing reload sequence drifted")
    for pc in (0xC0CA18, 0xC0CB3A, 0xC0CC04):
        count = sum(
            1
            for row in records
            if row["pc24"] == pc
            and row["object_slot"] == 0x0E
            and row["object_id"] == 0x06
            and row["selector"] == 0x01
        )
        if count != 12:
            raise ProbeError(f"right-route selector-01 count drifted at {pc:06X}")


def validate_trace_document(
    trace: Mapping[str, Any],
    *,
    route: str,
    repetition: int,
    rom_bytes: bytes,
) -> dict[str, Any]:
    document = _require_exact_keys(trace, TRACE_TOP_KEYS, "trace")
    if document["schema"] != TRACE_SCHEMA:
        raise ProbeError("trace schema drifted")
    if document["evidence_level"] != EVIDENCE_LEVEL:
        raise ProbeError("trace evidence label drifted")
    if (
        document["collector_version"] != COLLECTOR_VERSION
        or type(document["collector_version"]) is not int
    ):
        raise ProbeError("trace collector version drifted")
    if document["emulator"] != "Mesen 2.1.1":
        raise ProbeError("trace emulator label drifted")
    if route not in EXPECTED_COUNTS or document["route"] != route:
        raise ProbeError("trace route drifted")
    _require_int(repetition, 1, 99, "expected repetition")
    if document["repetition"] != repetition or type(document["repetition"]) is not int:
        raise ProbeError("trace repetition drifted")
    if not isinstance(rom_bytes, bytes) or len(rom_bytes) != ROM_SIZE:
        raise ProbeError(f"ROM snapshot must be exactly {ROM_SIZE} bytes")

    observer = _require_exact_keys(document["observer"], OBSERVER_KEYS, "observer")
    if (
        observer["mechanism"] != "broad-exec-callback-exact-pc-router"
        or observer["write_calls"] != 0
        or type(observer["write_calls"]) is not int
    ):
        raise ProbeError("observer contract drifted")
    mappings = observer["watched_pc_mappings"]
    if not isinstance(mappings, list) or len(mappings) != len(ORDERED_PCS):
        raise ProbeError("watched-PC mappings must contain exactly six rows")
    seen_mapping_pcs: set[int] = set()
    for index, (row, pc) in enumerate(zip(mappings, ORDERED_PCS, strict=True)):
        mapping = _require_exact_keys(row, MAPPING_KEYS, f"mapping[{index}]")
        role, opcode, mapped_address = WATCHED[pc]
        expected = {
            "pc24": pc,
            "role": role,
            "opcode": opcode,
            "mapped_address": mapped_address,
            "mapping_is_prg_rom": True,
        }
        _require_int(mapping["pc24"], 0, 0xFFFFFF, f"mapping[{index}].pc24")
        _require_int(mapping["opcode"], 0, 0xFF, f"mapping[{index}].opcode")
        _require_int(
            mapping["mapped_address"],
            0,
            0xFFFFFF,
            f"mapping[{index}].mapped_address",
        )
        if type(mapping["mapping_is_prg_rom"]) is not bool:
            raise ProbeError(f"mapping[{index}].mapping_is_prg_rom must be boolean")
        if mapping != expected:
            raise ProbeError(f"watched-PC mapping drifted at row {index}")
        if pc in seen_mapping_pcs:
            raise ProbeError(f"duplicate watched-PC mapping: {pc:06X}")
        seen_mapping_pcs.add(pc)
        if rom_bytes[hirom_file_offset(pc)] != opcode:
            raise ProbeError(f"canonical opcode preimage drifted at {pc:06X}")
    if seen_mapping_pcs != set(ORDERED_PCS):
        raise ProbeError("watched-PC mapping set is incomplete")

    input_contract = _require_exact_keys(
        document["input_contract"],
        INPUT_KEYS,
        "input_contract",
    )
    expected_input = {
        "terminal_frame": TERMINAL_FRAME,
        "right_start_frame": RIGHT_START_FRAME if route == "right" else None,
        "right_end_frame": RIGHT_END_FRAME if route == "right" else None,
    }
    _require_int(
        input_contract["terminal_frame"],
        0,
        100_000,
        "input_contract.terminal_frame",
    )
    for key in ("right_start_frame", "right_end_frame"):
        _require_nullable_int(
            input_contract[key],
            0,
            100_000,
            f"input_contract.{key}",
        )
    if input_contract != expected_input:
        raise ProbeError("input contract drifted")

    bindings = document["checkpoint_bindings"]
    if not isinstance(bindings, list) or len(bindings) != len(EXPECTED_BINDINGS):
        raise ProbeError("checkpoint bindings must contain exactly three rows")
    for index, (row, expected) in enumerate(
        zip(bindings, EXPECTED_BINDINGS, strict=True)
    ):
        binding = _require_exact_keys(row, BINDING_KEYS, f"binding[{index}]")
        for key in BINDING_KEYS:
            _require_int(binding[key], 0, 0xFFFF, f"binding[{index}].{key}")
        if binding != expected:
            raise ProbeError(f"checkpoint object/PC binding drifted at row {index}")

    _validate_snapshot(document["pre"], "pre")
    _validate_snapshot(document["post"], "post")

    expected_counts = EXPECTED_COUNTS[route]
    counts = _require_exact_keys(document["counts"], set(expected_counts), "counts")
    if counts != expected_counts:
        raise ProbeError("exact-PC callback counts drifted")
    for key, value in counts.items():
        _require_int(value, 0, 20_000, f"counts.{key}")

    records = document["records"]
    if not isinstance(records, list):
        raise ProbeError("records must be an array")
    if len(records) != sum(expected_counts.values()):
        raise ProbeError("record count disagrees with expected exact-PC counts")
    derived_counts = {key: 0 for key in expected_counts}
    active_seen: set[tuple[int, int]] = set()
    validated_records: list[Mapping[str, Any]] = []
    for sequence, raw_record in enumerate(records):
        record = _require_exact_keys(raw_record, RECORD_KEYS, f"record[{sequence}]")
        if record["seq"] != sequence or type(record["seq"]) is not int:
            raise ProbeError(f"record[{sequence}] sequence drifted")
        _require_int(record["frame"], 1, TERMINAL_FRAME, f"record[{sequence}].frame")
        pc = _require_int(record["pc24"], 0, 0xFFFFFF, f"record[{sequence}].pc24")
        if pc not in WATCHED:
            raise ProbeError(f"record[{sequence}] has an unexpected PC")
        role, opcode, _ = WATCHED[pc]
        _require_int(record["opcode"], 0, 0xFF, f"record[{sequence}].opcode")
        if record["role"] != role or record["opcode"] != opcode:
            raise ProbeError(f"record[{sequence}] role/opcode drifted")
        derived_counts[f"{pc:06X}"] += 1

        cpu = _require_exact_keys(record["cpu"], CPU_KEYS, f"record[{sequence}].cpu")
        for key in ("a", "x", "y", "d"):
            _require_int(cpu[key], 0, 0xFFFF, f"record[{sequence}].cpu.{key}")
        _require_int(cpu["ps"], 0, 0xFF, f"record[{sequence}].cpu.ps")
        _require_nullable_int(cpu["sp"], 0, 0xFFFF, f"record[{sequence}].cpu.sp")
        _require_nullable_int(cpu["db"], 0, 0xFF, f"record[{sequence}].cpu.db")

        byte_fields = (
            "object_status",
            "object_id",
            "selector",
            "cursor",
            "alt_mode",
            "alt_selector",
            "delay",
            "cached_frame",
            "assembly_bank",
            "dp_d8",
        )
        _require_int(record["object_slot"], 0, 0x7F, f"record[{sequence}].object_slot")
        for key in byte_fields:
            _require_int(record[key], 0, 0xFF, f"record[{sequence}].{key}")
        _require_int(record["facing"], 0, 3, f"record[{sequence}].facing")
        for key in (
            "timing_base",
            "main_base",
            "facing_stride",
            "assembly_base",
            "dp_c1",
            "dp_d6",
            "dp_d9",
        ):
            _require_int(record[key], 0, 0xFFFF, f"record[{sequence}].{key}")

        stream_address = record["stream_address"]
        stream_value = record["stream_value"]
        if pc in (0xC0CA35, 0xC0CA3D, 0xC0CBC2, 0xC0CC04):
            address = _require_int(
                stream_address,
                0xE40000,
                0xE4FFFF,
                f"record[{sequence}].stream_address",
            )
            value = _require_int(
                stream_value,
                0,
                0xFF,
                f"record[{sequence}].stream_value",
            )
            if rom_bytes[hirom_file_offset(address)] != value:
                raise ProbeError(
                    f"record[{sequence}] stream byte disagrees with canonical ROM"
                )
        elif stream_address is not None or stream_value is not None:
            raise ProbeError(f"record[{sequence}] unexpectedly resolves a stream byte")

        slot = record["object_slot"]
        object_id = record["object_id"]
        if slot in BINDING_BY_SLOT:
            binding = BINDING_BY_SLOT[slot]
            if (
                object_id != binding["logical_pc_id"]
                or record["object_status"] != binding["object_status"]
                or record["main_base"] != binding["main_base"]
                or record["timing_base"] != binding["timing_base"]
            ):
                raise ProbeError(f"record[{sequence}] violates checkpoint binding")
            active_seen.add((slot, object_id))
        elif object_id in BINDING_SLOT_BY_ID:
            raise ProbeError(f"record[{sequence}] moves a bound PC to another object slot")
        validated_records.append(record)
    if derived_counts != counts:
        raise ProbeError("record-derived counts disagree with trace counts")
    expected_active = {
        (row["object_slot"], row["logical_pc_id"]) for row in EXPECTED_BINDINGS
    }
    if active_seen != expected_active:
        raise ProbeError("records do not cover every checkpoint object/PC binding")
    if route == "right":
        _validate_right_loop(validated_records)

    termination = _require_exact_keys(
        document["termination"],
        TERMINATION_KEYS,
        "termination",
    )
    expected_termination = {
        "collector_stopped": True,
        "success": True,
        "overflow": False,
        "observer_error": None,
    }
    for key in ("collector_stopped", "success", "overflow"):
        if type(termination[key]) is not bool:
            raise ProbeError(f"termination.{key} must be boolean")
    if termination["observer_error"] is not None:
        raise ProbeError("termination.observer_error must be null")
    if termination != expected_termination:
        raise ProbeError("collector did not terminate cleanly")

    active_record_count = sum(
        1 for row in validated_records if row["object_slot"] in BINDING_BY_SLOT
    )
    return {
        "route": route,
        "repetition": repetition,
        "exact_pc_counts": dict(counts),
        "record_count": len(records),
        "checkpoint_binding_record_count": active_record_count,
        "complete_selector_01_loop": route == "right",
    }


def minimal_subprocess_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    inherited = os.environ if source is None else source
    allow = {
        "COMSPEC",
        "NUMBER_OF_PROCESSORS",
        "OS",
        "PATH",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "PROCESSOR_IDENTIFIER",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "WINDIR",
    }
    result = {key: value for key, value in inherited.items() if key.upper() in allow}
    result["PE_LAUNCH_PROTOCOL"] = LAUNCH_PROTOCOL
    return result


def require_expected_process_exit(
    completed: subprocess.CompletedProcess[str],
    *,
    observer_error: str | None = None,
) -> None:
    if completed.returncode == EXPECTED_EXIT_CODE:
        return
    details: list[str] = []
    if observer_error:
        details.append(f"collector: {observer_error}")
    process_detail = (completed.stderr or completed.stdout or "").strip()
    if process_detail:
        details.append(process_detail[-2000:])
    suffix = ": " + " | ".join(details) if details else ""
    raise ProbeError(
        f"Mesen returned {completed.returncode}, expected {EXPECTED_EXIT_CODE}{suffix}"
    )


def require_process_result(
    completed: subprocess.CompletedProcess[str] | None,
    process_error: Exception | None,
    *,
    effective_timeout: int,
) -> subprocess.CompletedProcess[str]:
    if process_error is not None:
        if isinstance(process_error, subprocess.TimeoutExpired):
            raise ProbeError(
                f"Mesen exceeded the exact host timeout of {effective_timeout} seconds"
            ) from process_error
        raise ProbeError(f"Mesen launch failed: {process_error}") from process_error
    if completed is None:
        raise ProbeError("Mesen did not return a process result")
    return completed


def describe_artifact(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def build_host_manifest(
    *,
    route: str,
    repetition: int,
    mesen_timeout: int,
    launcher_identity: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
    trace_artifact: Mapping[str, Any],
    screenshot_artifact: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    host_timeout = mesen_timeout + HOST_TIMEOUT_GRACE_SECONDS
    return {
        "schema": HOST_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "route": route,
        "repetition": repetition,
        "launcher": {
            "version": LAUNCHER_VERSION,
            "protocol": LAUNCH_PROTOCOL,
            "size": launcher_identity["size"],
            "sha256": launcher_identity["sha256"],
        },
        "collector": {
            "version": COLLECTOR_VERSION,
            "size": inputs["collector"]["size"],
            "sha256": inputs["collector"]["sha256"],
        },
        "timeouts": {
            "mesen_test_runner_seconds": mesen_timeout,
            "host_subprocess_seconds": host_timeout,
            "host_grace_seconds": HOST_TIMEOUT_GRACE_SECONDS,
        },
        "runtime": {
            "executed_program": {
                "name": "Mesen.exe",
                "size": inputs["mesen"]["size"],
                "sha256": inputs["mesen"]["sha256"],
            },
            "staged_runtime_inputs": {
                key: {
                    "size": inputs[key]["size"],
                    "sha256": inputs[key]["sha256"],
                }
                for key in (
                    "mesen_core",
                    "harfbuzz",
                    "skia",
                    "nesdb",
                    "settings",
                )
            },
            "provenance_only_not_staged_or_executed": {
                "archive": {
                    "size": inputs["archive"]["size"],
                    "sha256": inputs["archive"]["sha256"],
                }
            },
        },
        "private_inputs": {
            key: {
                "size": inputs[key]["size"],
                "sha256": inputs[key]["sha256"],
            }
            for key in ("rom", "state", "sram")
        },
        "reproduction": {
            "python_executable": str(Path(sys.executable).resolve(strict=True)),
            "argv_shape": [
                "tools/run_mesen_field_animation_probe_v0.py",
                "--route",
                route,
                "--repetition",
                str(repetition),
                "--output-dir",
                "<new-path-strictly-under-workspace-private/test_runs>",
                "--timeout",
                str(mesen_timeout),
            ],
            "effective_timeouts": {
                "mesen_test_runner_seconds": mesen_timeout,
                "host_subprocess_seconds": host_timeout,
            },
        },
        "artifacts": {
            "trace": dict(trace_artifact),
            "endpoint_png": dict(screenshot_artifact),
        },
        "summary": dict(summary),
        "preservation_checks": {
            "pinned_source_files_rehashed_equal_after_process": True,
            "shared_mesen_saves_snapshot_equal_after_process": True,
            "staged_input_files_rehashed_equal_before_teardown": True,
            "disposable_staging_root_absent_after_teardown": True,
        },
        "nonclaims": [
            "This is private exploratory runtime evidence, not accepted evidence.",
            "The launcher does not check the entire worktree or every emulator-owned path.",
            "The endpoint PNG is supporting presentation only.",
            "No production allocation, ROM hook, PC $07 sprite, menu behavior, battle behavior, or save behavior is established.",
        ],
    }


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    if os.path.lexists(path):
        raise ProbeError(f"refusing to overwrite JSON output: {path}")
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", required=True, choices=("idle", "right"))
    parser.add_argument("--repetition", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=90)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.repetition < 1 or args.repetition > 99:
        raise ProbeError("--repetition must be between 1 and 99")
    if args.timeout < 1 or args.timeout > 300:
        raise ProbeError("--timeout must be between 1 and 300 seconds")
    host_timeout = args.timeout + HOST_TIMEOUT_GRACE_SECONDS

    private_root = canonical_private_root()
    collector = COLLECTOR.resolve(strict=True)
    collector_identity = require_identity(collector, "collector")
    launcher = Path(__file__).resolve(strict=True)
    launcher_identity = {
        "path": launcher,
        "size": launcher.stat().st_size,
        "sha256": sha256_file(launcher),
    }

    mesen = resolve_private_file(args.mesen, "Mesen executable", private_root=private_root)
    rom = resolve_private_file(args.rom, "canonical ROM", private_root=private_root)
    state = resolve_private_file(args.state, "native checkpoint", private_root=private_root)
    sram = resolve_private_file(args.sram, "disposable SRAM", private_root=private_root)
    runtime_paths = {
        "mesen": mesen,
        "mesen_core": resolve_private_file(
            mesen.parent / "MesenCore.dll", "Mesen core", private_root=private_root
        ),
        "harfbuzz": resolve_private_file(
            mesen.parent / "libHarfBuzzSharp.dll",
            "HarfBuzz runtime",
            private_root=private_root,
        ),
        "skia": resolve_private_file(
            mesen.parent / "libSkiaSharp.dll",
            "Skia runtime",
            private_root=private_root,
        ),
        "nesdb": resolve_private_file(
            mesen.parent / "MesenNesDB.txt", "Mesen database", private_root=private_root
        ),
        "settings": resolve_private_file(
            mesen.parent / "settings.json", "portable settings", private_root=private_root
        ),
    }
    archive = resolve_private_file(
        mesen.parent.parent / "Mesen_2.1.1_Windows.zip",
        "official Mesen archive",
        private_root=private_root,
    )
    shared_saves = resolve_private_directory(
        mesen.parent / "Saves", "shared Mesen Saves", private_root=private_root
    )

    all_paths = {
        "archive": archive,
        **runtime_paths,
        "rom": rom,
        "state": state,
        "sram": sram,
        "collector": collector,
    }
    identities = {
        label: require_identity(path, label) for label, path in all_paths.items()
    }
    before_hashes = {label: row["sha256"] for label, row in identities.items()}
    before_hashes["launcher"] = launcher_identity["sha256"]
    shared_saves_before = snapshot_private_files(shared_saves)

    rom_bytes = rom.read_bytes()
    state_bytes = state.read_bytes()
    collector_bytes = collector.read_bytes()
    if hashlib.sha256(rom_bytes).hexdigest() != before_hashes["rom"]:
        raise ProbeError("canonical ROM changed while being captured")
    if hashlib.sha256(state_bytes).hexdigest() != before_hashes["state"]:
        raise ProbeError("checkpoint changed while being captured")
    if hashlib.sha256(collector_bytes).hexdigest() != before_hashes["collector"]:
        raise ProbeError("collector changed while being captured")

    protected_output_roots = tuple(
        dict.fromkeys((rom.parent, state.parent, shared_saves))
    )
    output_root = prepare_private_output_dir(
        args.output_dir,
        private_root=private_root,
        forbidden_roots=protected_output_roots,
    )
    trace_path = output_root / "trace.json"
    screenshot_path = output_root / "endpoint.png"
    manifest_path = output_root / "host_manifest.json"

    completed: subprocess.CompletedProcess[str] | None = None
    process_error: Exception | None = None
    staged_changes: list[str] = []
    staged_save_entries: list[str] = []
    staging_root_after: Path | None = None
    observer_error: str | None = None
    expected_staged_sram_name: str | None = None
    with tempfile.TemporaryDirectory(
        prefix=".mesen_field_animation_probe_",
        dir=output_root,
    ) as staging_directory:
        staging_root = Path(staging_directory).resolve(strict=True)
        staging_root_after = staging_root
        if _is_reparse(staging_root) or not _inside(staging_root, output_root):
            raise ProbeError("temporary staging root is unsafe")
        staged_app = staging_root / "app"
        staged_saves = staged_app / "Saves"
        staged_saves.mkdir(parents=True)
        staged_files: dict[str, Path] = {}
        for label, destination_name in RUNTIME_NAMES.items():
            destination = staged_app / destination_name
            copy_new_regular_file(all_paths[label], destination, label)
            staged_files[label] = destination.resolve(strict=True)

        stem = f"pe_field_anim_{secrets.token_hex(12)}"
        staged_rom = staging_root / f"{stem}.sfc"
        staged_state = staging_root / f"{stem}.mss"
        staged_sram = staged_saves / f"{stem}.srm"
        expected_staged_sram_name = staged_sram.name
        staged_collector = staging_root / f"{stem}.lua"
        for label, destination, source in (
            ("rom", staged_rom, rom_bytes),
            ("state", staged_state, state_bytes),
            ("sram", staged_sram, sram.read_bytes()),
            ("collector", staged_collector, collector_bytes),
        ):
            with destination.open("xb") as handle:
                handle.write(source)
            staged_files[label] = destination.resolve(strict=True)

        staged_expected = {
            label: before_hashes[label]
            for label in (
                "mesen",
                "mesen_core",
                "harfbuzz",
                "skia",
                "nesdb",
                "settings",
                "rom",
                "state",
                "sram",
                "collector",
            )
        }
        for label, path in staged_files.items():
            if not _inside(path, staging_root) or _is_reparse(path):
                raise ProbeError(f"staged {label} escaped or became a reparse point")
            if sha256_file(path) != staged_expected[label]:
                raise ProbeError(f"staged {label} failed pre-launch identity check")

        staged_profile = _ensure_real_child_directories(
            staging_root,
            ("profile",),
        )
        staged_appdata = _ensure_real_child_directories(
            staged_profile,
            ("AppData", "Roaming"),
        )
        staged_localappdata = _ensure_real_child_directories(
            staged_profile,
            ("AppData", "Local"),
        )
        staged_temp = _ensure_real_child_directories(
            staging_root,
            ("temp",),
        )
        environment = minimal_subprocess_environment()
        profile_drive, profile_tail = os.path.splitdrive(str(staged_profile))
        environment.update(
            {
                "APPDATA": str(staged_appdata),
                "HOME": str(staged_profile),
                "LOCALAPPDATA": str(staged_localappdata),
                "TEMP": str(staged_temp),
                "TMP": str(staged_temp),
                "USERPROFILE": str(staged_profile),
                "PE_LAUNCH_NONCE": secrets.token_hex(16),
                "PE_WORKSPACE_PRIVATE_ROOT": str(private_root),
                "PE_OUTPUT_ROOT": str(output_root),
                "PE_STAGING_ROOT": str(staging_root),
                "PE_ROUTE": args.route,
                "PE_REPETITION": str(args.repetition),
                "PE_STATE_PATH": str(staged_state),
                "PE_TRACE_OUT": str(trace_path),
                "PE_TRACE_SCREENSHOT": str(screenshot_path),
            }
        )
        if profile_drive:
            environment["HOMEDRIVE"] = profile_drive
            environment["HOMEPATH"] = profile_tail or os.sep
        command = [
            str(staged_files["mesen"]),
            "--testRunner",
            f"--timeout={args.timeout}",
            "--doNotSaveSettings",
            "--debug.scriptWindow.allowIoOsAccess=true",
            "--snes.port1.type=SnesController",
            str(staged_collector),
            str(staged_rom),
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            completed = subprocess.run(
                command,
                cwd=staged_app,
                env=environment,
                capture_output=True,
                text=True,
                timeout=host_timeout,
                check=False,
                creationflags=creation_flags,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            process_error = exc

        error_path = Path(str(trace_path) + ".observer-error")
        if os.path.lexists(error_path):
            try:
                observer_error = read_direct_regular_file(
                    error_path,
                    "collector observer error",
                    parent=output_root,
                    maximum=64 * 1024,
                ).decode("utf-8", errors="replace").strip()
            except ProbeError as exc:
                observer_error = f"unreadable observer error: {exc}"
        for label, path in staged_files.items():
            try:
                if sha256_file(path) != staged_expected[label]:
                    staged_changes.append(label)
            except OSError:
                staged_changes.append(label)
        try:
            staged_save_entries = sorted(
                child.name for child in staged_saves.iterdir()
            )
        except OSError:
            staged_changes.append("Saves-directory")

    if staging_root_after is None:
        raise ProbeError("disposable staging root was not created")
    require_staging_removed(staging_root_after)

    guarded_sources = {**all_paths, "launcher": launcher}
    require_file_hashes_unchanged(
        guarded_sources,
        before_hashes,
        "pinned source file",
    )
    if snapshot_private_files(shared_saves) != shared_saves_before:
        raise ProbeError("shared Mesen Saves snapshot changed")
    if staged_changes:
        raise ProbeError("staged input changed: " + ", ".join(staged_changes))
    if expected_staged_sram_name is None:
        raise ProbeError("staged SRAM name was not established")
    require_exact_staged_save_entries(
        staged_save_entries,
        expected_staged_sram_name,
    )
    completed = require_process_result(
        completed,
        process_error,
        effective_timeout=host_timeout,
    )
    require_expected_process_exit(completed, observer_error=observer_error)

    trace = load_trace_file(trace_path, output_root=output_root)
    summary = validate_trace_document(
        trace,
        route=args.route,
        repetition=args.repetition,
        rom_bytes=rom_bytes,
    )
    screenshot_bytes = read_direct_regular_file(
        screenshot_path,
        "endpoint PNG",
        parent=output_root,
        maximum=MAX_SCREENSHOT_BYTES,
    )
    validate_png_bytes(screenshot_bytes)

    trace_artifact = describe_artifact(trace_path)
    screenshot_artifact = describe_artifact(screenshot_path)
    manifest = build_host_manifest(
        route=args.route,
        repetition=args.repetition,
        mesen_timeout=args.timeout,
        launcher_identity=launcher_identity,
        inputs=identities,
        trace_artifact=trace_artifact,
        screenshot_artifact=screenshot_artifact,
        summary=summary,
    )
    _write_new_json(manifest_path, manifest)
    return {
        "status": "private-exploratory-probe-complete",
        "evidence_level": EVIDENCE_LEVEL,
        "route": args.route,
        "repetition": args.repetition,
        "exit_code": completed.returncode,
        "trace": trace_artifact,
        "endpoint_png": screenshot_artifact,
        "host_manifest": describe_artifact(manifest_path),
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except ProbeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
