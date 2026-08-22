#!/usr/bin/env python3
"""Validate the four private Mesen event-$11C access traces.

The validator accepts JSON traces only after resolving them below the
workspace ``private/`` tree.  It never opens a ROM, save RAM, savestate, or
screenshot.  The contract is intentionally fail-closed: unknown fields,
collector versions, profiles, variants, callbacks, and terminal states are
rejected.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (WORKSPACE_ROOT / "private").resolve()
SCHEMA = "project-epoch-mesen-event11c-access-trace-v1"
COLLECTOR_VERSION = 2
MAX_TRACE_BYTES = 1024 * 1024

READ_PC24 = 0xC06797
WRITE_PC24 = 0xC06822
CHECKPOINT_FRAME = 3237
CHECKPOINT_DIRECT_PAGE = 0x0100

TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "collector_version",
        "profile",
        "variant",
        "observer",
        "pre",
        "callbacks",
        "post",
        "termination",
    }
)
OBSERVER_KEYS = frozenset(
    {
        "read_pc24",
        "read_mapped_address",
        "read_mapping_is_prg_rom",
        "write_pc24",
        "write_mapped_address",
        "write_mapping_is_prg_rom",
        "mechanism",
        "checkpoint_direct_page",
        "checkpoint_frame",
    }
)
SNAPSHOT_KEYS = frozenset(
    {
        "location",
        "storyline",
        "lap_scratch",
        "magic_flags",
        "robo_flags",
        "explore_mode",
        "dialog_state",
        "leader_x",
        "leader_y",
        "active_party_hex",
        "tech_counts_hex",
        "learned_masks_hex",
        "candidate_matches_variant",
        "front_guard_hex",
        "rear_guard_hex",
        "epoch_name_hex",
    }
)
CALLBACK_KEYS = frozenset(
    {
        "seq",
        "frame",
        "absolute_frame",
        "access",
        "address",
        "raw_wram_offset",
        "value",
        "pc24",
    }
)
TERMINATION_KEYS = frozenset(
    {
        "collector_stopped",
        "success",
        "overflow",
        "observer_error",
        "unexpected_accesses",
    }
)
EXPECTED_OBSERVER = {
    "read_pc24": READ_PC24,
    "read_mapped_address": 0x6797,
    "read_mapping_is_prg_rom": True,
    "write_pc24": WRITE_PC24,
    "write_mapped_address": 0x6822,
    "write_mapping_is_prg_rom": True,
    "mechanism": "broad-exec-callback-exact-pc-router",
    "checkpoint_direct_page": CHECKPOINT_DIRECT_PAGE,
    "checkpoint_frame": CHECKPOINT_FRAME,
}
EXPECTED_TERMINATION = {
    "collector_stopped": True,
    "success": True,
    "overflow": False,
    "observer_error": None,
    "unexpected_accesses": 0,
}


def _callback(
    access: str,
    address: int,
    value: int,
    frame: int,
) -> tuple[str, int, int, int, int, int]:
    raw_wram_offset = address - 0x7E0000
    pc24 = READ_PC24 if access == "read" else WRITE_PC24
    return access, address, raw_wram_offset, value, pc24, frame


PROFILE_CONTRACTS = {
    "frog-robo": {
        "active_party_hex": "060403",
        "pre_magic_flags": 0x47,
        "pre_robo_flags": 0x00,
        "pre_tech_counts_hex": "08080808000808",
        "pre_learned_masks_hex": "ffffffff1fffff",
        "post_tech_counts_hex": "08080808030808",
        "post_dialog_state": 0,
        "callbacks": (
            _callback("write", 0x7E2834, 0x03, 985),
            _callback("read", 0x7E283B, 0x1F, 989),
            _callback("write", 0x7E283B, 0xFF, 989),
        ),
    },
    "crono-marle-lucca": {
        "active_party_hex": "000102",
        "pre_magic_flags": 0x18,
        "pre_robo_flags": 0x00,
        "pre_tech_counts_hex": "00000008080808",
        "pre_learned_masks_hex": "1f1f1fffffffff",
        "post_tech_counts_hex": "03030308080808",
        "post_dialog_state": 2,
        "callbacks": (
            _callback("write", 0x7E2830, 0x03, 793),
            _callback("read", 0x7E2837, 0x1F, 793),
            _callback("write", 0x7E2837, 0xFF, 793),
            _callback("write", 0x7E2831, 0x03, 1086),
            _callback("read", 0x7E2838, 0x1F, 1090),
            _callback("write", 0x7E2838, 0xFF, 1090),
            _callback("write", 0x7E2832, 0x03, 1875),
            _callback("read", 0x7E2839, 0x1F, 1879),
            _callback("write", 0x7E2839, 0xFF, 1879),
        ),
    },
}
VARIANTS = frozenset({"zero", "canary"})
EXPECTED_COMBINATIONS = frozenset(
    (profile, variant)
    for profile in PROFILE_CONTRACTS
    for variant in VARIANTS
)


class TraceValidationError(RuntimeError):
    """The private trace set does not satisfy the accepted contract."""


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def _require_object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{label} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        _fail(f"{label} keys mismatch: missing={missing}, extra={extra}")


def _require_exact_scalar(actual: Any, expected: Any, label: str) -> None:
    if type(actual) is not type(expected) or actual != expected:
        _fail(f"{label} must be {expected!r}, got {actual!r}")


def _require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        _fail(f"{label} must be an integer")
    return value


def _require_lower_hex(value: Any, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or re.fullmatch(r"[0-9a-f]+", value) is None
    ):
        _fail(f"{label} must be exactly {length} lowercase hexadecimal digits")
    return value


def _expected_snapshot(
    profile: str,
    *,
    post: bool,
) -> dict[str, Any]:
    contract = PROFILE_CONTRACTS[profile]
    if post:
        return {
            "location": 0x01D1,
            "storyline": 0x4D,
            "lap_scratch": 0x03,
            "magic_flags": 0x5F,
            "robo_flags": contract["pre_robo_flags"],
            "explore_mode": 0,
            "dialog_state": contract["post_dialog_state"],
            "leader_x": 1925,
            "leader_y": 3061,
            "active_party_hex": contract["active_party_hex"],
            "tech_counts_hex": contract["post_tech_counts_hex"],
            "learned_masks_hex": "ffffffffffffff",
            "candidate_matches_variant": True,
            "front_guard_hex": "00000000",
            "rear_guard_hex": "00000000000000000000000000000000",
            "epoch_name_hex": "a4c9c8bcc100",
        }
    return {
        "location": 0x01D1,
        "storyline": 0x4C,
        "lap_scratch": 0x03,
        "magic_flags": contract["pre_magic_flags"],
        "robo_flags": contract["pre_robo_flags"],
        "explore_mode": 1,
        "dialog_state": 0,
        "leader_x": 1568,
        "leader_y": 2623,
        "active_party_hex": contract["active_party_hex"],
        "tech_counts_hex": contract["pre_tech_counts_hex"],
        "learned_masks_hex": contract["pre_learned_masks_hex"],
        "candidate_matches_variant": True,
        "front_guard_hex": "00000000",
        "rear_guard_hex": "00000000000000000000000000000000",
        "epoch_name_hex": "a4c9c8bcc100",
    }


def _validate_snapshot(
    value: Any,
    profile: str,
    *,
    post: bool,
    label: str,
) -> None:
    snapshot = _require_object(value, label)
    _require_exact_keys(snapshot, SNAPSHOT_KEYS, label)
    for key, expected in _expected_snapshot(profile, post=post).items():
        if isinstance(expected, str) and key.endswith("_hex"):
            _require_lower_hex(snapshot[key], len(expected), f"{label}.{key}")
        _require_exact_scalar(snapshot[key], expected, f"{label}.{key}")


def _validate_observer(value: Any, label: str) -> None:
    observer = _require_object(value, label)
    _require_exact_keys(observer, OBSERVER_KEYS, label)
    for key, expected in EXPECTED_OBSERVER.items():
        _require_exact_scalar(observer[key], expected, f"{label}.{key}")


def _validate_callbacks(value: Any, profile: str, label: str) -> None:
    if not isinstance(value, list):
        _fail(f"{label} must be a JSON array")
    expected_callbacks = PROFILE_CONTRACTS[profile]["callbacks"]
    if len(value) != len(expected_callbacks):
        _fail(
            f"{label} must contain exactly {len(expected_callbacks)} records"
        )

    previous_frame = -1
    previous_absolute_frame = -1
    for seq, (record_value, expected) in enumerate(
        zip(value, expected_callbacks, strict=True)
    ):
        record_label = f"{label}[{seq}]"
        record = _require_object(record_value, record_label)
        _require_exact_keys(record, CALLBACK_KEYS, record_label)
        access, address, raw_offset, access_value, pc24, expected_frame = (
            expected
        )
        fixed = {
            "seq": seq,
            "access": access,
            "address": address,
            "raw_wram_offset": raw_offset,
            "value": access_value,
            "pc24": pc24,
        }
        for key, expected_value in fixed.items():
            _require_exact_scalar(
                record[key],
                expected_value,
                f"{record_label}.{key}",
            )

        frame = _require_int(record["frame"], f"{record_label}.frame")
        if frame != expected_frame:
            _fail(
                f"{record_label}.frame must be {expected_frame}, got {frame}"
            )
        absolute_frame = _require_int(
            record["absolute_frame"],
            f"{record_label}.absolute_frame",
        )
        if not 0 <= frame <= 2400:
            _fail(f"{record_label}.frame is outside the bounded run")
        if absolute_frame != CHECKPOINT_FRAME + frame:
            _fail(
                f"{record_label}.absolute_frame is not checkpoint + frame"
            )
        if frame < previous_frame or absolute_frame < previous_absolute_frame:
            _fail(f"{record_label} is not in chronological order")
        previous_frame = frame
        previous_absolute_frame = absolute_frame


def _validate_termination(value: Any, label: str) -> None:
    termination = _require_object(value, label)
    _require_exact_keys(termination, TERMINATION_KEYS, label)
    for key, expected in EXPECTED_TERMINATION.items():
        _require_exact_scalar(termination[key], expected, f"{label}.{key}")


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    """Validate one decoded trace and return its profile/variant identity."""

    trace = _require_object(value, label)
    _require_exact_keys(trace, TOP_LEVEL_KEYS, label)
    _require_exact_scalar(trace["schema"], SCHEMA, f"{label}.schema")
    _require_exact_scalar(
        trace["collector_version"],
        COLLECTOR_VERSION,
        f"{label}.collector_version",
    )

    profile = trace["profile"]
    if not isinstance(profile, str) or profile not in PROFILE_CONTRACTS:
        _fail(f"{label}.profile is unknown: {profile!r}")
    variant = trace["variant"]
    if not isinstance(variant, str) or variant not in VARIANTS:
        _fail(f"{label}.variant is unknown: {variant!r}")

    _validate_observer(trace["observer"], f"{label}.observer")
    _validate_snapshot(trace["pre"], profile, post=False, label=f"{label}.pre")
    _validate_callbacks(trace["callbacks"], profile, f"{label}.callbacks")
    _validate_snapshot(
        trace["post"],
        profile,
        post=True,
        label=f"{label}.post",
    )
    _validate_termination(trace["termination"], f"{label}.termination")
    return profile, variant


def validate_trace_documents(
    traces: Sequence[Any],
) -> dict[str, Any]:
    """Validate exactly one zero/canary trace for both bounded profiles."""

    if len(traces) != len(EXPECTED_COMBINATIONS):
        _fail("trace set must contain exactly four documents")

    by_combination: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, value in enumerate(traces):
        profile, variant = validate_trace_document(
            value,
            label=f"traces[{index}]",
        )
        combination = (profile, variant)
        if combination in by_combination:
            _fail(f"duplicate trace combination: {profile}/{variant}")
        by_combination[combination] = _require_object(
            value,
            f"traces[{index}]",
        )

    actual_combinations = frozenset(by_combination)
    if actual_combinations != EXPECTED_COMBINATIONS:
        missing = sorted(EXPECTED_COMBINATIONS - actual_combinations)
        extra = sorted(actual_combinations - EXPECTED_COMBINATIONS)
        _fail(f"trace combinations mismatch: missing={missing}, extra={extra}")

    for profile in PROFILE_CONTRACTS:
        zero_callbacks = by_combination[(profile, "zero")]["callbacks"]
        canary_callbacks = by_combination[(profile, "canary")]["callbacks"]
        if zero_callbacks != canary_callbacks:
            _fail(
                f"{profile} zero/canary callback records are not identical"
            )

    return {
        "schema": SCHEMA,
        "collector_version": COLLECTOR_VERSION,
        "status": "accepted-private-diagnostic-trace-set",
        "trace_count": 4,
        "profiles": sorted(PROFILE_CONTRACTS),
        "variants": sorted(VARIANTS),
        "zero_canary_callbacks_identical": True,
    }


def validate_private_trace_path(
    path: pathlib.Path,
    *,
    workspace_root: pathlib.Path = WORKSPACE_ROOT,
) -> pathlib.Path:
    """Resolve one JSON input below the workspace's private tree."""

    workspace = workspace_root.resolve()
    private_root = (workspace / "private").resolve()
    candidate = path if path.is_absolute() else workspace / path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise TraceValidationError(
            f"trace input must remain below private/: {path}"
        ) from exc
    if resolved.suffix != ".json":
        _fail(f"trace input must use the .json suffix: {path}")
    if not resolved.is_file():
        _fail(f"trace input does not exist or is not a file: {path}")
    if resolved.stat().st_size > MAX_TRACE_BYTES:
        _fail(f"trace input exceeds {MAX_TRACE_BYTES} bytes: {path}")
    return resolved


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TraceValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_private_trace(
    path: pathlib.Path,
    *,
    workspace_root: pathlib.Path = WORKSPACE_ROOT,
) -> Mapping[str, Any]:
    """Read one size-bounded, private JSON trace with duplicate-key rejection."""

    resolved = validate_private_trace_path(
        path,
        workspace_root=workspace_root,
    )
    try:
        value = json.loads(
            resolved.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TraceValidationError(
            f"cannot decode trace JSON {resolved}: {exc}"
        ) from exc
    return _require_object(value, str(resolved))


def validate_trace_files(
    paths: Sequence[pathlib.Path],
    *,
    workspace_root: pathlib.Path = WORKSPACE_ROOT,
) -> dict[str, Any]:
    """Load and validate four unique private JSON files."""

    if len(paths) != 4:
        _fail("exactly four trace paths are required")
    resolved_paths = [
        validate_private_trace_path(path, workspace_root=workspace_root)
        for path in paths
    ]
    if len(set(resolved_paths)) != len(resolved_paths):
        _fail("trace paths must be unique")
    traces = [
        load_private_trace(path, workspace_root=workspace_root)
        for path in resolved_paths
    ]
    return validate_trace_documents(traces)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "trace",
        nargs=4,
        type=pathlib.Path,
        metavar="PRIVATE_TRACE_JSON",
        help="four private trace JSON files, in any order",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = validate_trace_files(args.trace)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
