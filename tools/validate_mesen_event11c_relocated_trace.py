#!/usr/bin/env python3
"""Validate four private volatile event-$11C relocation traces.

The validator consumes compact JSON only.  It does not read a ROM, SRAM,
savestate, decompressed event packet, or screenshot.  Every accepted runtime
field is checked against the pinned source-only relocation contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-mesen-event11c-relocated-trace-v2"
COLLECTOR_VERSION = 2
MAX_TRACE_BYTES = 1024 * 1024

PACKET_BASE_WRAM_OFFSET = 0x12000
PACKET_LENGTH = 0x0C6B
SOURCE_PACKET_SHA256 = (
    "31d5b222828eca6c1c91a309f1543a8f"
    "dccf2e2f5deea7a4074b7376eaa70d8a"
)
TRANSFORMED_PACKET_SHA256 = (
    "8e2952bd5e8c25eaf0ad4244dece929b"
    "6f4fc1eea8317ea707fcd782c898e50b"
)
RELOCATION_DELTA = 0x0470

OLD_BLOCK_START = 0x2830
CANDIDATE_START = 0x2CA0
BLOCK_LENGTH = 0x50
READ_PC24 = 0xC06797
WRITE_PC24 = 0xC06822
CHECKPOINT_DIRECT_PAGE = 0x0100

OLD_EVENT_TARGET_LENGTH = 0x0C
OLD_TARGET_CANARY = bytes.fromhex("471eea9705fecea2040cc7e0")
EXPECTED_SOURCE_COMPATIBILITY_SHA256 = (
    "6007023eefa73f3f9c70da546f921dce"
    "866d3131e8c98ba978785f7ac28f82c1"
)

TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "collector_version",
        "profile",
        "variant",
        "collector_explicit_write_scope",
        "source_compatibility_hex",
        "candidate_copy_match_before_profile",
        "packet",
        "observer",
        "pre",
        "callbacks",
        "post",
        "termination",
    }
)
PACKET_KEYS = frozenset(
    {
        "base_wram_offset",
        "length",
        "source_sha256",
        "transformed_sha256",
        "changed_byte_count",
        "edit_count",
        "edits",
        "live_source_match_before",
        "exact_expected_diff",
        "live_transformed_match_after_prepare",
        "live_transformed_match_at_end",
    }
)
PACKET_EDIT_KEYS = frozenset(
    {
        "seq",
        "event_data_command_offset",
        "opcode_offset",
        "opcode",
        "operand_offset",
        "old_address",
        "new_address",
        "changed_offsets",
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
        "candidate_tech_counts_hex",
        "candidate_learned_masks_hex",
        "old_block_hex",
        "candidate_hex",
        "old_block_matches_variant",
        "candidate_non_target_preserved",
        "front_guard_hex",
        "rear_guard_hex",
        "epoch_name_hex",
    }
)
CALLBACK_KEYS = frozenset(
    {
        "seq",
        "frame",
        "access",
        "address",
        "raw_wram_offset",
        "value",
        "pc24",
        "cpu_y",
        "command_offset",
        "opcode_offset",
        "opcode",
        "operand_offset",
        "operand_address",
        "direct_page",
        "memory_flag_set",
        "accumulator",
        "deferred_value",
    }
)
TERMINATION_KEYS = frozenset(
    {
        "collector_stopped",
        "success",
        "overflow",
        "observer_error",
        "screenshot_phase_mod16",
        "spekkio_sprite_frame",
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
}
EXPECTED_TERMINATION = {
    "collector_stopped": True,
    "success": True,
    "overflow": False,
    "observer_error": None,
    "screenshot_phase_mod16": 0,
    "unexpected_accesses": 0,
}

# event-data command offset, opcode, operand address, frame, access, value
RELOCATION_SITES = (
    (0x05C0, 0x4C, 0x7E2830, 793, "write", 0x03),
    (0x05C5, 0x48, 0x7E2837, 793, "read", 0x1F),
    (0x05CD, 0x4C, 0x7E2837, 793, "write", 0xFF),
    (0x0609, 0x4C, 0x7E2831, 1086, "write", 0x03),
    (0x060E, 0x48, 0x7E2838, 1090, "read", 0x1F),
    (0x0616, 0x4C, 0x7E2838, 1090, "write", 0xFF),
    (0x0652, 0x4C, 0x7E2832, 1875, "write", 0x03),
    (0x0657, 0x48, 0x7E2839, 1879, "read", 0x1F),
    (0x065F, 0x4C, 0x7E2839, 1879, "write", 0xFF),
    (0x06B4, 0x4C, 0x7E2834, 985, "write", 0x03),
    (0x06B9, 0x48, 0x7E283B, 989, "read", 0x1F),
    (0x06C1, 0x4C, 0x7E283B, 989, "write", 0xFF),
)


def _build_packet_edits() -> tuple[dict[str, Any], ...]:
    edits: list[dict[str, Any]] = []
    for seq, (
        command_offset,
        opcode,
        old_address,
        _frame,
        _access,
        _value,
    ) in enumerate(RELOCATION_SITES):
        new_address = old_address + RELOCATION_DELTA
        operand_offset = command_offset + 2
        changed_offsets = [
            operand_offset + byte_index
            for byte_index in range(3)
            if (
                (old_address >> (byte_index * 8)) & 0xFF
                != (new_address >> (byte_index * 8)) & 0xFF
            )
        ]
        if len(changed_offsets) != 2:
            raise AssertionError("each relocation site must change two bytes")
        edits.append(
            {
                "seq": seq,
                "event_data_command_offset": command_offset,
                "opcode_offset": command_offset + 1,
                "opcode": opcode,
                "operand_offset": operand_offset,
                "old_address": old_address,
                "new_address": new_address,
                "changed_offsets": changed_offsets,
            }
        )
    if len(edits) != 12:
        raise AssertionError("relocation contract must contain 12 site edits")
    return tuple(edits)


EXPECTED_PACKET_EDITS = _build_packet_edits()

PROFILE_CONTRACTS = {
    "crono-marle-lucca": {
        "active_party_hex": "000102",
        "pre_magic_flags": 0x18,
        "post_dialog_state": 2,
        "count_indices": (0, 1, 2),
        "mask_indices": (0, 1, 2),
        "pre_counts_hex": "00000008080808",
        "post_counts_hex": "03030308080808",
        "pre_masks_hex": "1f1f1fffffffff",
        "spekkio_sprite_frame": 4,
        "callback_site_indices": tuple(range(0, 9)),
    },
    "frog-robo": {
        "active_party_hex": "060403",
        "pre_magic_flags": 0x47,
        "post_dialog_state": 0,
        "count_indices": (4,),
        "mask_indices": (4,),
        "pre_counts_hex": "08080808000808",
        "post_counts_hex": "08080808030808",
        "pre_masks_hex": "ffffffff1fffff",
        "spekkio_sprite_frame": 22,
        "callback_site_indices": (9, 10, 11),
    },
}
VARIANTS = frozenset({"zero", "canary"})
EXPECTED_COMBINATIONS = frozenset(
    (profile, variant)
    for profile in PROFILE_CONTRACTS
    for variant in VARIANTS
)


class TraceValidationError(RuntimeError):
    """A relocated event trace violated the pinned contract."""


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def _require_object(value: Any, label: str) -> Mapping[str, Any]:
    if type(value) is not dict:
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


def _require_int(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if type(value) is not int:
        _fail(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        _fail(f"{label} is below {minimum}")
    if maximum is not None and value > maximum:
        _fail(f"{label} is above {maximum}")
    return value


def _require_lower_hex(value: Any, length: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or re.fullmatch(r"[0-9a-f]+", value) is None
    ):
        _fail(f"{label} must be exactly {length} lowercase hexadecimal digits")
    return value


def _validate_packet(value: Any, label: str) -> None:
    packet = _require_object(value, label)
    _require_exact_keys(packet, PACKET_KEYS, label)
    expected_scalars = {
        "base_wram_offset": PACKET_BASE_WRAM_OFFSET,
        "length": PACKET_LENGTH,
        "source_sha256": SOURCE_PACKET_SHA256,
        "transformed_sha256": TRANSFORMED_PACKET_SHA256,
        "changed_byte_count": 24,
        "edit_count": 12,
        "live_source_match_before": True,
        "exact_expected_diff": True,
        "live_transformed_match_after_prepare": True,
        "live_transformed_match_at_end": True,
    }
    for key, expected in expected_scalars.items():
        _require_exact_scalar(packet[key], expected, f"{label}.{key}")

    edits = packet["edits"]
    if type(edits) is not list or len(edits) != 12:
        _fail(f"{label}.edits must contain exactly 12 records")
    for index, (raw, expected) in enumerate(
        zip(edits, EXPECTED_PACKET_EDITS, strict=True)
    ):
        edit_label = f"{label}.edits[{index}]"
        edit = _require_object(raw, edit_label)
        _require_exact_keys(edit, PACKET_EDIT_KEYS, edit_label)
        for key, expected_value in expected.items():
            _require_exact_scalar(
                edit[key],
                expected_value,
                f"{edit_label}.{key}",
            )


def _validate_observer(value: Any, label: str) -> None:
    observer = _require_object(value, label)
    _require_exact_keys(observer, OBSERVER_KEYS, label)
    for key, expected in EXPECTED_OBSERVER.items():
        _require_exact_scalar(observer[key], expected, f"{label}.{key}")


def _prepared_candidate(
    source_compatibility: bytes,
    profile: str,
) -> bytes:
    result = bytearray(source_compatibility)
    contract = PROFILE_CONTRACTS[profile]
    for index in contract["count_indices"]:
        result[index] = 0
    for index in contract["mask_indices"]:
        result[7 + index] &= 0x1F
    return bytes(result)


def _terminal_candidate(prepared: bytes, profile: str) -> bytes:
    result = bytearray(prepared)
    contract = PROFILE_CONTRACTS[profile]
    for index in contract["count_indices"]:
        result[index] = 3
    for index in contract["mask_indices"]:
        result[7 + index] = 0xFF
    return bytes(result)


def _expected_old_block(source_compatibility: bytes, variant: str) -> str:
    result = bytearray(source_compatibility)
    result[:OLD_EVENT_TARGET_LENGTH] = (
        b"\x00" * OLD_EVENT_TARGET_LENGTH
        if variant == "zero"
        else OLD_TARGET_CANARY
    )
    return result.hex()


def _expected_semantic_snapshot(
    profile: str,
    *,
    post: bool,
) -> dict[str, Any]:
    contract = PROFILE_CONTRACTS[profile]
    return {
        "location": 0x01D1,
        "storyline": 0x4D if post else 0x4C,
        "lap_scratch": 0x03,
        "magic_flags": 0x5F if post else contract["pre_magic_flags"],
        "robo_flags": 0,
        "explore_mode": 0 if post else 1,
        "dialog_state": contract["post_dialog_state"] if post else 0,
        "leader_x": 1925 if post else 1568,
        "leader_y": 3061 if post else 2623,
        "active_party_hex": contract["active_party_hex"],
        "candidate_tech_counts_hex": (
            contract["post_counts_hex"] if post else contract["pre_counts_hex"]
        ),
        "candidate_learned_masks_hex": (
            "ffffffffffffff" if post else contract["pre_masks_hex"]
        ),
        "old_block_matches_variant": True,
        "candidate_non_target_preserved": True,
        "front_guard_hex": "00000000",
        "rear_guard_hex": "00000000000000000000000000000000",
        "epoch_name_hex": "a4c9c8bcc100",
    }


def _validate_snapshot(
    value: Any,
    *,
    profile: str,
    variant: str,
    source_compatibility: bytes,
    post: bool,
    label: str,
) -> None:
    snapshot = _require_object(value, label)
    _require_exact_keys(snapshot, SNAPSHOT_KEYS, label)
    expected = _expected_semantic_snapshot(profile, post=post)
    expected["old_block_hex"] = _expected_old_block(
        source_compatibility,
        variant,
    )
    prepared = _prepared_candidate(source_compatibility, profile)
    candidate = _terminal_candidate(prepared, profile) if post else prepared
    expected["candidate_hex"] = candidate.hex()

    for key, expected_value in expected.items():
        if type(expected_value) is str and key.endswith("_hex"):
            _require_lower_hex(
                snapshot[key],
                len(expected_value),
                f"{label}.{key}",
            )
        _require_exact_scalar(
            snapshot[key],
            expected_value,
            f"{label}.{key}",
        )

    candidate_hex = _require_lower_hex(
        snapshot["candidate_hex"],
        BLOCK_LENGTH * 2,
        f"{label}.candidate_hex",
    )
    candidate_bytes = bytes.fromhex(candidate_hex)
    _require_exact_scalar(
        candidate_bytes[:7].hex(),
        snapshot["candidate_tech_counts_hex"],
        f"{label}.candidate count projection",
    )
    _require_exact_scalar(
        candidate_bytes[7:14].hex(),
        snapshot["candidate_learned_masks_hex"],
        f"{label}.candidate mask projection",
    )


def _expected_callbacks(profile: str) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for seq, site_index in enumerate(
        PROFILE_CONTRACTS[profile]["callback_site_indices"]
    ):
        (
            command_offset,
            opcode,
            old_address,
            frame,
            access,
            value,
        ) = RELOCATION_SITES[site_index]
        address = old_address + RELOCATION_DELTA
        result.append(
            {
                "seq": seq,
                "frame": frame,
                "access": access,
                "address": address,
                "raw_wram_offset": address - 0x7E0000,
                "value": value,
                "pc24": READ_PC24 if access == "read" else WRITE_PC24,
                "cpu_y": command_offset,
                "command_offset": command_offset,
                "opcode_offset": command_offset + 1,
                "opcode": opcode,
                "operand_offset": command_offset + 2,
                "operand_address": address,
                "direct_page": CHECKPOINT_DIRECT_PAGE,
                "memory_flag_set": True,
                "accumulator": None if access == "read" else value,
                "deferred_value": None if access == "read" else value,
            }
        )
    return tuple(result)


def _validate_callbacks(value: Any, profile: str, label: str) -> None:
    if type(value) is not list:
        _fail(f"{label} must be a JSON array")
    expected_callbacks = _expected_callbacks(profile)
    if len(value) != len(expected_callbacks):
        _fail(
            f"{label} must contain exactly {len(expected_callbacks)} records"
        )

    for index, (raw, expected) in enumerate(
        zip(value, expected_callbacks, strict=True)
    ):
        callback_label = f"{label}[{index}]"
        callback = _require_object(raw, callback_label)
        _require_exact_keys(callback, CALLBACK_KEYS, callback_label)
        for key, expected_value in expected.items():
            _require_exact_scalar(
                callback[key],
                expected_value,
                f"{callback_label}.{key}",
            )

        _require_exact_scalar(
            callback["memory_flag_set"],
            True,
            f"{callback_label}.memory_flag_set",
        )

        if callback["access"] == "write":
            accumulator = _require_int(
                callback["accumulator"],
                f"{callback_label}.accumulator",
                minimum=0,
                maximum=0xFF,
            )
            if accumulator != callback["deferred_value"]:
                _fail(
                    f"{callback_label} accumulator does not match deferred write"
                )
            if callback["deferred_value"] != callback["value"]:
                _fail(
                    f"{callback_label} deferred write does not match stored value"
                )
        else:
            _require_exact_scalar(
                callback["accumulator"],
                None,
                f"{callback_label}.accumulator",
            )
            _require_exact_scalar(
                callback["deferred_value"],
                None,
                f"{callback_label}.deferred_value",
            )


def _validate_termination(value: Any, label: str, profile: str) -> None:
    termination = _require_object(value, label)
    _require_exact_keys(termination, TERMINATION_KEYS, label)
    for key, expected in EXPECTED_TERMINATION.items():
        _require_exact_scalar(termination[key], expected, f"{label}.{key}")
    _require_exact_scalar(
        termination["spekkio_sprite_frame"],
        PROFILE_CONTRACTS[profile]["spekkio_sprite_frame"],
        f"{label}.spekkio_sprite_frame",
    )


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    """Validate one decoded trace and return profile/variant."""

    trace = _require_object(value, label)
    _require_exact_keys(trace, TOP_LEVEL_KEYS, label)
    _require_exact_scalar(trace["schema"], SCHEMA, f"{label}.schema")
    _require_exact_scalar(
        trace["collector_version"],
        COLLECTOR_VERSION,
        f"{label}.collector_version",
    )
    _require_exact_scalar(
        trace["collector_explicit_write_scope"],
        "snes-work-ram-via-write8-write16-only",
        f"{label}.collector_explicit_write_scope",
    )
    _require_exact_scalar(
        trace["candidate_copy_match_before_profile"],
        True,
        f"{label}.candidate_copy_match_before_profile",
    )

    profile = trace["profile"]
    if type(profile) is not str or profile not in PROFILE_CONTRACTS:
        _fail(f"{label}.profile is unknown: {profile!r}")
    variant = trace["variant"]
    if type(variant) is not str or variant not in VARIANTS:
        _fail(f"{label}.variant is unknown: {variant!r}")

    source_hex = _require_lower_hex(
        trace["source_compatibility_hex"],
        BLOCK_LENGTH * 2,
        f"{label}.source_compatibility_hex",
    )
    source_compatibility = bytes.fromhex(source_hex)
    if (
        hashlib.sha256(source_compatibility).hexdigest()
        != EXPECTED_SOURCE_COMPATIBILITY_SHA256
    ):
        _fail(f"{label}.source_compatibility_hex does not match checkpoint")

    _validate_packet(trace["packet"], f"{label}.packet")
    _validate_observer(trace["observer"], f"{label}.observer")
    _validate_snapshot(
        trace["pre"],
        profile=profile,
        variant=variant,
        source_compatibility=source_compatibility,
        post=False,
        label=f"{label}.pre",
    )
    _validate_callbacks(trace["callbacks"], profile, f"{label}.callbacks")
    _validate_snapshot(
        trace["post"],
        profile=profile,
        variant=variant,
        source_compatibility=source_compatibility,
        post=True,
        label=f"{label}.post",
    )
    _validate_termination(
        trace["termination"],
        f"{label}.termination",
        profile,
    )
    return profile, variant


def validate_trace_documents(traces: Sequence[Any]) -> dict[str, Any]:
    """Validate exactly one zero/canary trace for both profiles."""

    if len(traces) != 4:
        _fail("trace set must contain exactly four documents")

    by_combination: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, value in enumerate(traces):
        profile, variant = validate_trace_document(
            value,
            label=f"traces[{index}]",
        )
        key = (profile, variant)
        if key in by_combination:
            _fail(f"duplicate trace combination: {profile}/{variant}")
        by_combination[key] = _require_object(value, f"traces[{index}]")

    actual = frozenset(by_combination)
    if actual != EXPECTED_COMBINATIONS:
        missing = sorted(EXPECTED_COMBINATIONS - actual)
        extra = sorted(actual - EXPECTED_COMBINATIONS)
        _fail(f"trace combinations mismatch: missing={missing}, extra={extra}")

    source_values = {
        trace["source_compatibility_hex"]
        for trace in by_combination.values()
    }
    if len(source_values) != 1:
        _fail("all four traces must copy the same source compatibility block")

    for profile in PROFILE_CONTRACTS:
        zero = by_combination[(profile, "zero")]
        canary = by_combination[(profile, "canary")]
        if zero["callbacks"] != canary["callbacks"]:
            _fail(f"{profile} zero/canary callbacks are not identical")
        for phase in ("pre", "post"):
            if zero[phase]["candidate_hex"] != canary[phase]["candidate_hex"]:
                _fail(
                    f"{profile} zero/canary candidate {phase} differs"
                )
            zero_without_old = {
                key: value
                for key, value in zero[phase].items()
                if key != "old_block_hex"
            }
            canary_without_old = {
                key: value
                for key, value in canary[phase].items()
                if key != "old_block_hex"
            }
            if zero_without_old != canary_without_old:
                _fail(
                    f"{profile} zero/canary {phase} differs outside old block"
                )

    return {
        "schema": SCHEMA,
        "collector_version": COLLECTOR_VERSION,
        "status": "accepted-private-volatile-relocation-trace-set",
        "trace_count": 4,
        "profiles": sorted(PROFILE_CONTRACTS),
        "variants": sorted(VARIANTS),
        "source_compatibility_identical": True,
        "zero_canary_callbacks_identical": True,
        "candidate_pairs_identical": True,
    }


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TraceValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_trace(path: pathlib.Path) -> Mapping[str, Any]:
    """Load one size-bounded JSON trace with duplicate-key rejection."""

    resolved = path.resolve(strict=True)
    if resolved.suffix != ".json" or not resolved.is_file():
        _fail(f"trace input must be an existing .json file: {path}")
    if resolved.stat().st_size > MAX_TRACE_BYTES:
        _fail(f"trace input exceeds {MAX_TRACE_BYTES} bytes: {path}")
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


def validate_trace_files(paths: Sequence[pathlib.Path]) -> dict[str, Any]:
    if len(paths) != 4:
        _fail("exactly four trace paths are required")
    resolved = [path.resolve(strict=True) for path in paths]
    if len(set(resolved)) != 4:
        _fail("trace paths must be unique")
    return validate_trace_documents([load_trace(path) for path in resolved])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "trace",
        nargs=4,
        type=pathlib.Path,
        metavar="TRACE_JSON",
        help="four compact trace JSON files, in any order",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    print(
        json.dumps(
            validate_trace_files(args.trace),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
