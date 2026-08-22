#!/usr/bin/env python3
"""Validate private Mesen WRAM-ownership traces for the $2CA0 candidate.

The validator consumes compact JSON only.  It never reads a ROM, SRAM,
savestate, screenshot, or raw emulator trace.  Screenshot identity belongs to
the separate acceptance layer and is intentionally absent from this schema.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "project-epoch-mesen-wram-ownership-trace-v1"
COLLECTOR_VERSION = 1
MAX_TRACE_BYTES = 2 * 1024 * 1024
CALLBACK_LIMIT = 4096

CHECKPOINT_ID = "event11c-checkpoint-v5-spekkio-talkable"
CHECKPOINT_SIZE = 133_993
CHECKPOINT_SHA256 = (
    "26788b52f63a32a7539d8acb18495df"
    "1a458064f700d5411916e2bfc34c4522e"
)
CHECKPOINT_FRAME = 3237
CHECKPOINT_DIRECT_PAGE = 0x0100
CHECKPOINT_LOCATION = 0x01D1

CANARY_SEED = b"Project Epoch WRAM 2CA0 compatibility canary v1"
CANDIDATE_CANARY = hashlib.shake_256(CANARY_SEED).digest(0x50)
EXPECTED_EPOCH_NAME = bytes.fromhex("a4c9c8bcc100")

READ_ABS8_CALLBACK_PC = 0xC06799
WRITE_ABS_FROM_MEM8_PC = 0xC06824

TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "collector_version",
        "scenario",
        "variant",
        "collector_explicit_write_scope",
        "checkpoint",
        "scenario_contract",
        "observer",
        "watched_ranges",
        "preparation",
        "pre",
        "callbacks",
        "counters",
        "post",
        "termination",
    }
)
CHECKPOINT_KEYS = frozenset(
    {
        "id",
        "state_size",
        "state_sha256",
        "source_frame",
        "direct_page",
        "location",
    }
)
SCENARIO_CONTRACT_KEYS = frozenset(
    {
        "terminal_frame_min",
        "terminal_frame_max",
        "expected_access_class",
        "inputs",
    }
)
INPUT_KEYS = frozenset({"port", "button", "start_frame", "end_frame"})
OBSERVER_KEYS = frozenset(
    {
        "mechanism",
        "memory_type",
        "counter_granularity",
        "callback_limit",
        "counters_cover_every_watched_byte",
    }
)
WATCHED_RANGE_KEYS = frozenset({"name", "start_address", "length"})
PREPARATION_KEYS = frozenset(
    {
        "completed_before_counters_armed",
        "counters_zero_after_preparation",
        "writes",
    }
)
PREPARATION_WRITE_KEYS = frozenset(
    {"seq", "width", "raw_wram_offset", "value", "label"}
)
SNAPSHOT_KEYS = frozenset(
    {
        "old_compatibility_hex",
        "roster_hex",
        "joined_hex",
        "epoch_name_hex",
        "front_guard_hex",
        "candidate_hex",
        "rear_guard_hex",
    }
)
CALLBACK_KEYS = frozenset(
    {"seq", "frame", "access", "address", "value", "pc24"}
)
COUNTER_KEYS = frozenset({"address", "read_count", "write_count"})
TERMINATION_KEYS = frozenset(
    {
        "collector_stopped",
        "success",
        "overflow",
        "observer_error",
        "counters_armed",
        "preparation_writes_after_arm",
        "terminal_frame",
        "unexpected_accesses",
    }
)

WATCHED_RANGES = (
    {"name": "old-compatibility", "start_address": 0x7E2830, "length": 0x50},
    {"name": "roster", "start_address": 0x7E2980, "length": 0x09},
    {"name": "joined", "start_address": 0x7E29AF, "length": 0x01},
    {"name": "epoch-name", "start_address": 0x7E2C4D, "length": 0x06},
    {"name": "front-guard", "start_address": 0x7E2C9C, "length": 0x04},
    {"name": "candidate", "start_address": 0x7E2CA0, "length": 0x50},
    {"name": "rear-guard", "start_address": 0x7E2CF0, "length": 0x10},
)
WATCHED_ADDRESSES = tuple(
    address
    for watched_range in WATCHED_RANGES
    for address in range(
        watched_range["start_address"],
        watched_range["start_address"] + watched_range["length"],
    )
)
WATCHED_ADDRESS_SET = frozenset(WATCHED_ADDRESSES)
ADDRESS_RANGE_NAME = {
    address: watched_range["name"]
    for watched_range in WATCHED_RANGES
    for address in range(
        watched_range["start_address"],
        watched_range["start_address"] + watched_range["length"],
    )
}


def _pulse(button: str, start: int) -> dict[str, Any]:
    return {
        "port": 1,
        "button": button,
        "start_frame": start,
        "end_frame": start + 1,
    }


SCENARIO_CONTRACTS: dict[str, dict[str, Any]] = {
    "calibration": {
        "terminal_frame_min": 0,
        "terminal_frame_max": 0,
        "expected_access_class": "none",
        "inputs": (),
    },
    "field-idle": {
        "terminal_frame_min": 600,
        "terminal_frame_max": 600,
        "expected_access_class": "ownership-negative-control",
        "inputs": (),
    },
    "main-menu": {
        "terminal_frame_min": 600,
        "terminal_frame_max": 600,
        "expected_access_class": "ownership-negative-control",
        "inputs": (_pulse("X", 60),),
    },
    "event11c-frog": {
        "terminal_frame_min": 1500,
        "terminal_frame_max": 2400,
        "expected_access_class": "old-compatibility-positive-control",
        "inputs": tuple(_pulse("A", start) for start in range(60, 1141, 120)),
    },
}
VARIANTS = frozenset({"zero", "canary"})
EXPECTED_COMBINATIONS = frozenset(
    (scenario, variant)
    for scenario in SCENARIO_CONTRACTS
    for variant in VARIANTS
)

EXPECTED_OBSERVER = {
    "mechanism": "snes-work-ram-read-write-memory-callbacks",
    "memory_type": "snes-work-ram",
    "counter_granularity": "byte-address-and-access",
    "callback_limit": CALLBACK_LIMIT,
    "counters_cover_every_watched_byte": True,
}
EXPECTED_TERMINATION = {
    "collector_stopped": True,
    "success": True,
    "overflow": False,
    "observer_error": None,
    "counters_armed": True,
    "preparation_writes_after_arm": 0,
    "unexpected_accesses": 0,
}

# frame, access, address, value, native event-handler PC
EVENT11C_FROG_SEQUENCE = (
    (985, "write", 0x7E2834, 0x03, WRITE_ABS_FROM_MEM8_PC),
    (989, "read", 0x7E283B, 0x1F, READ_ABS8_CALLBACK_PC),
    (989, "write", 0x7E283B, 0xFF, WRITE_ABS_FROM_MEM8_PC),
)
EVENT11C_FROG_WRITES = frozenset(
    row for row in EVENT11C_FROG_SEQUENCE if row[1] == "write"
)

SNAPSHOT_FIELD_BY_RANGE = {
    "old-compatibility": "old_compatibility_hex",
    "roster": "roster_hex",
    "joined": "joined_hex",
    "epoch-name": "epoch_name_hex",
    "front-guard": "front_guard_hex",
    "candidate": "candidate_hex",
    "rear-guard": "rear_guard_hex",
}


class TraceValidationError(RuntimeError):
    """The private ownership trace set violates its pinned contract."""


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def _require_object(value: Any, label: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        _fail(f"{label} must be a JSON object")
    return value


def _require_array(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{label} must be a JSON array")
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
        _fail(f"{label} must be at least {minimum}")
    if maximum is not None and value > maximum:
        _fail(f"{label} must be at most {maximum}")
    return value


def _require_lower_hex(value: Any, length: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or re.fullmatch(r"[0-9a-f]+", value) is None
    ):
        _fail(f"{label} must be exactly {length} lowercase hexadecimal digits")
    return value


def _validate_checkpoint(value: Any, label: str) -> None:
    checkpoint = _require_object(value, label)
    _require_exact_keys(checkpoint, CHECKPOINT_KEYS, label)
    expected = {
        "id": CHECKPOINT_ID,
        "state_size": CHECKPOINT_SIZE,
        "state_sha256": CHECKPOINT_SHA256,
        "source_frame": CHECKPOINT_FRAME,
        "direct_page": CHECKPOINT_DIRECT_PAGE,
        "location": CHECKPOINT_LOCATION,
    }
    for key, expected_value in expected.items():
        _require_exact_scalar(
            checkpoint[key], expected_value, f"{label}.{key}"
        )


def _validate_scenario_contract(
    value: Any,
    scenario: str,
    label: str,
) -> None:
    contract = _require_object(value, label)
    _require_exact_keys(contract, SCENARIO_CONTRACT_KEYS, label)
    expected = SCENARIO_CONTRACTS[scenario]
    for key in (
        "terminal_frame_min",
        "terminal_frame_max",
        "expected_access_class",
    ):
        _require_exact_scalar(contract[key], expected[key], f"{label}.{key}")
    inputs = _require_array(contract["inputs"], f"{label}.inputs")
    if len(inputs) != len(expected["inputs"]):
        _fail(
            f"{label}.inputs must contain exactly "
            f"{len(expected['inputs'])} records"
        )
    for index, (actual_input, expected_input) in enumerate(
        zip(inputs, expected["inputs"], strict=True)
    ):
        input_label = f"{label}.inputs[{index}]"
        row = _require_object(actual_input, input_label)
        _require_exact_keys(row, INPUT_KEYS, input_label)
        for key, expected_value in expected_input.items():
            _require_exact_scalar(
                row[key], expected_value, f"{input_label}.{key}"
            )


def _validate_observer(value: Any, label: str) -> None:
    observer = _require_object(value, label)
    _require_exact_keys(observer, OBSERVER_KEYS, label)
    for key, expected in EXPECTED_OBSERVER.items():
        _require_exact_scalar(observer[key], expected, f"{label}.{key}")


def _validate_watched_ranges(value: Any, label: str) -> None:
    ranges = _require_array(value, label)
    if len(ranges) != len(WATCHED_RANGES):
        _fail(f"{label} must contain exactly {len(WATCHED_RANGES)} ranges")
    for index, (actual, expected) in enumerate(
        zip(ranges, WATCHED_RANGES, strict=True)
    ):
        range_label = f"{label}[{index}]"
        row = _require_object(actual, range_label)
        _require_exact_keys(row, WATCHED_RANGE_KEYS, range_label)
        for key, expected_value in expected.items():
            _require_exact_scalar(
                row[key], expected_value, f"{range_label}.{key}"
            )


def _event_fixture_writes() -> list[dict[str, Any]]:
    rows = (
        (1, 0x10000, 0x4C, "storyline"),
        (1, 0x1021C, 0x03, "lap-scratch"),
        (1, 0x101E0, 0x47, "magic-flags"),
        (1, 0x101E2, 0x00, "robo-flags"),
        (1, 0x2834, 0x00, "frog-tech-count"),
        (1, 0x283B, 0x1F, "frog-learned-mask"),
        (2, 0x276D, 0x0000, "frog-remaining-tp"),
    )
    return [
        {
            "seq": seq,
            "width": width,
            "raw_wram_offset": offset,
            "value": write_value,
            "label": write_label,
        }
        for seq, (width, offset, write_value, write_label) in enumerate(rows)
    ]


def _expected_preparation_writes(
    scenario: str,
    variant: str,
) -> list[dict[str, Any]]:
    writes = _event_fixture_writes() if scenario == "event11c-frog" else []
    if variant == "canary":
        for index, byte in enumerate(CANDIDATE_CANARY):
            writes.append(
                {
                    "seq": len(writes),
                    "width": 1,
                    "raw_wram_offset": 0x2CA0 + index,
                    "value": byte,
                    "label": "candidate-variant",
                }
            )
    return writes


def _validate_preparation(
    value: Any,
    scenario: str,
    variant: str,
    label: str,
) -> None:
    preparation = _require_object(value, label)
    _require_exact_keys(preparation, PREPARATION_KEYS, label)
    _require_exact_scalar(
        preparation["completed_before_counters_armed"],
        True,
        f"{label}.completed_before_counters_armed",
    )
    _require_exact_scalar(
        preparation["counters_zero_after_preparation"],
        True,
        f"{label}.counters_zero_after_preparation",
    )
    writes = _require_array(preparation["writes"], f"{label}.writes")
    expected_writes = _expected_preparation_writes(scenario, variant)
    if len(writes) != len(expected_writes):
        _fail(
            f"{label}.writes must contain exactly "
            f"{len(expected_writes)} records"
        )
    for index, (actual, expected) in enumerate(
        zip(writes, expected_writes, strict=True)
    ):
        write_label = f"{label}.writes[{index}]"
        row = _require_object(actual, write_label)
        _require_exact_keys(row, PREPARATION_WRITE_KEYS, write_label)
        for key, expected_value in expected.items():
            _require_exact_scalar(
                row[key], expected_value, f"{write_label}.{key}"
            )


def _expected_candidate(variant: str) -> bytes:
    return bytes(0x50) if variant == "zero" else CANDIDATE_CANARY


def _validate_snapshot(
    value: Any,
    variant: str,
    label: str,
) -> dict[str, bytes]:
    snapshot = _require_object(value, label)
    _require_exact_keys(snapshot, SNAPSHOT_KEYS, label)
    result: dict[str, bytes] = {}
    for watched_range in WATCHED_RANGES:
        name = watched_range["name"]
        field = SNAPSHOT_FIELD_BY_RANGE[name]
        encoded = _require_lower_hex(
            snapshot[field],
            watched_range["length"] * 2,
            f"{label}.{field}",
        )
        result[name] = bytes.fromhex(encoded)

    if result["candidate"] != _expected_candidate(variant):
        _fail(f"{label}.candidate_hex does not match variant {variant}")
    if result["front-guard"] != bytes(0x04):
        _fail(f"{label}.front_guard_hex must remain zero")
    if result["rear-guard"] != bytes(0x10):
        _fail(f"{label}.rear_guard_hex must remain zero")
    if result["epoch-name"] != EXPECTED_EPOCH_NAME:
        _fail(f"{label}.epoch_name_hex does not preserve Epoch")
    return result


def _validate_callbacks(
    value: Any,
    scenario: str,
    terminal_frame_max: int,
    label: str,
) -> list[Mapping[str, Any]]:
    callbacks_value = _require_array(value, label)
    if len(callbacks_value) > CALLBACK_LIMIT:
        _fail(f"{label} exceeds callback limit {CALLBACK_LIMIT}")

    callbacks: list[Mapping[str, Any]] = []
    previous_frame = -1
    for index, callback_value in enumerate(callbacks_value):
        callback_label = f"{label}[{index}]"
        callback = _require_object(callback_value, callback_label)
        _require_exact_keys(callback, CALLBACK_KEYS, callback_label)
        _require_exact_scalar(callback["seq"], index, f"{callback_label}.seq")
        frame = _require_int(
            callback["frame"],
            f"{callback_label}.frame",
            minimum=0,
            maximum=terminal_frame_max,
        )
        if frame < previous_frame:
            _fail(f"{label} frames must be nondecreasing")
        previous_frame = frame
        access = callback["access"]
        if type(access) is not str or access not in {"read", "write"}:
            _fail(f"{callback_label}.access must be 'read' or 'write'")
        address = _require_int(
            callback["address"],
            f"{callback_label}.address",
            minimum=0,
            maximum=0xFFFFFF,
        )
        if address not in WATCHED_ADDRESS_SET:
            _fail(f"{callback_label}.address is outside watched ranges")
        _require_int(
            callback["value"],
            f"{callback_label}.value",
            minimum=0,
            maximum=0xFF,
        )
        _require_int(
            callback["pc24"],
            f"{callback_label}.pc24",
            minimum=0,
            maximum=0xFFFFFF,
        )

        range_name = ADDRESS_RANGE_NAME[address]
        if range_name in {"candidate", "front-guard", "rear-guard"}:
            _fail(f"{callback_label} illegally accesses {range_name}")
        if (
            access == "write"
            and range_name in {"epoch-name", "roster", "joined"}
        ):
            _fail(f"{callback_label} illegally writes {range_name}")
        if (
            access == "write"
            and range_name == "old-compatibility"
            and scenario != "event11c-frog"
        ):
            _fail(
                f"{callback_label} is an unapproved old-compatibility "
                "write"
            )
        callbacks.append(callback)

    if scenario == "calibration" and callbacks:
        _fail("calibration must have zero armed watched-range callbacks")

    if scenario == "event11c-frog":
        target_identities = {
            (985, "write", 0x7E2834, WRITE_ABS_FROM_MEM8_PC),
            (989, "read", 0x7E283B, READ_ABS8_CALLBACK_PC),
            (989, "write", 0x7E283B, WRITE_ABS_FROM_MEM8_PC),
        }
        filtered = tuple(
            (
                callback["frame"],
                callback["access"],
                callback["address"],
                callback["value"],
                callback["pc24"],
            )
            for callback in callbacks
            if (
                callback["frame"],
                callback["access"],
                callback["address"],
                callback["pc24"],
            )
            in target_identities
        )
        if filtered != EVENT11C_FROG_SEQUENCE:
            _fail(
                "event11c-frog native event-PC access sequence mismatch: "
                f"expected={EVENT11C_FROG_SEQUENCE!r}, got={filtered!r}"
            )
    return callbacks


def _validate_counters(
    value: Any,
    callbacks: Sequence[Mapping[str, Any]],
    label: str,
) -> None:
    counters = _require_array(value, label)
    if len(counters) != len(WATCHED_ADDRESSES):
        _fail(
            f"{label} must contain exactly "
            f"{len(WATCHED_ADDRESSES)} address records"
        )
    observed = Counter(
        (callback["address"], callback["access"]) for callback in callbacks
    )
    for index, (counter_value, expected_address) in enumerate(
        zip(counters, WATCHED_ADDRESSES, strict=True)
    ):
        counter_label = f"{label}[{index}]"
        counter = _require_object(counter_value, counter_label)
        _require_exact_keys(counter, COUNTER_KEYS, counter_label)
        _require_exact_scalar(
            counter["address"],
            expected_address,
            f"{counter_label}.address",
        )
        read_count = _require_int(
            counter["read_count"],
            f"{counter_label}.read_count",
            minimum=0,
        )
        write_count = _require_int(
            counter["write_count"],
            f"{counter_label}.write_count",
            minimum=0,
        )
        if read_count != observed[(expected_address, "read")]:
            _fail(f"{counter_label}.read_count does not reconcile callbacks")
        if write_count != observed[(expected_address, "write")]:
            _fail(f"{counter_label}.write_count does not reconcile callbacks")


def _snapshot_address_map(
    snapshot: Mapping[str, bytes],
) -> dict[int, int]:
    result: dict[int, int] = {}
    for watched_range in WATCHED_RANGES:
        name = watched_range["name"]
        start = watched_range["start_address"]
        for index, byte in enumerate(snapshot[name]):
            result[start + index] = byte
    return result


def _reconcile_snapshots(
    pre: Mapping[str, bytes],
    callbacks: Sequence[Mapping[str, Any]],
    post: Mapping[str, bytes],
    scenario: str,
    label: str,
) -> None:
    simulated = _snapshot_address_map(pre)
    for index, callback in enumerate(callbacks):
        address = callback["address"]
        value = callback["value"]
        if callback["access"] == "read":
            if simulated[address] != value:
                _fail(
                    f"{label}.callbacks[{index}] read value does not match "
                    "the simulated watched byte"
                )
        else:
            event_write = (
                callback["frame"],
                callback["access"],
                address,
                value,
                callback["pc24"],
            )
            if (
                scenario == "event11c-frog"
                and ADDRESS_RANGE_NAME[address] == "old-compatibility"
                and event_write not in EVENT11C_FROG_WRITES
                and simulated[address] != value
            ):
                _fail(
                    f"{label}.callbacks[{index}] non-target event "
                    "old-compatibility write is not same-value"
                )
            simulated[address] = value
    expected_post = _snapshot_address_map(post)
    for address in WATCHED_ADDRESSES:
        if simulated[address] != expected_post[address]:
            _fail(
                f"{label}.post does not reconcile callbacks at "
                f"${address:06X}"
            )


def _validate_termination(
    value: Any,
    scenario: str,
    label: str,
) -> None:
    termination = _require_object(value, label)
    _require_exact_keys(termination, TERMINATION_KEYS, label)
    for key, expected in EXPECTED_TERMINATION.items():
        _require_exact_scalar(termination[key], expected, f"{label}.{key}")
    terminal_frame = _require_int(
        termination["terminal_frame"],
        f"{label}.terminal_frame",
        minimum=0,
    )
    contract = SCENARIO_CONTRACTS[scenario]
    if not (
        contract["terminal_frame_min"]
        <= terminal_frame
        <= contract["terminal_frame_max"]
    ):
        _fail(
            f"{label}.terminal_frame is outside the pinned "
            f"{scenario} range"
        )


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    """Validate one decoded trace and return its scenario and variant."""

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
        "snes-work-ram-preparation-before-counters-arm-only",
        f"{label}.collector_explicit_write_scope",
    )

    scenario = trace["scenario"]
    if type(scenario) is not str or scenario not in SCENARIO_CONTRACTS:
        _fail(f"{label}.scenario is unknown: {scenario!r}")
    variant = trace["variant"]
    if type(variant) is not str or variant not in VARIANTS:
        _fail(f"{label}.variant is unknown: {variant!r}")

    _validate_checkpoint(trace["checkpoint"], f"{label}.checkpoint")
    _validate_scenario_contract(
        trace["scenario_contract"],
        scenario,
        f"{label}.scenario_contract",
    )
    _validate_observer(trace["observer"], f"{label}.observer")
    _validate_watched_ranges(
        trace["watched_ranges"],
        f"{label}.watched_ranges",
    )
    _validate_preparation(
        trace["preparation"],
        scenario,
        variant,
        f"{label}.preparation",
    )
    pre = _validate_snapshot(trace["pre"], variant, f"{label}.pre")
    terminal_max = SCENARIO_CONTRACTS[scenario]["terminal_frame_max"]
    callbacks = _validate_callbacks(
        trace["callbacks"],
        scenario,
        terminal_max,
        f"{label}.callbacks",
    )
    _validate_counters(trace["counters"], callbacks, f"{label}.counters")
    post = _validate_snapshot(trace["post"], variant, f"{label}.post")
    _reconcile_snapshots(pre, callbacks, post, scenario, label)
    _validate_termination(
        trace["termination"],
        scenario,
        f"{label}.termination",
    )

    if scenario == "event11c-frog":
        if pre["old-compatibility"][0x04] != 0x00:
            _fail(f"{label}.pre Frog tech-count fixture mismatch")
        if pre["old-compatibility"][0x0B] != 0x1F:
            _fail(f"{label}.pre Frog learned-mask fixture mismatch")
    return scenario, variant


def _without_candidate(snapshot: Any, label: str) -> dict[str, Any]:
    value = _require_object(snapshot, label)
    return {
        key: field_value
        for key, field_value in value.items()
        if key != "candidate_hex"
    }


def validate_trace_documents(traces: Sequence[Any]) -> dict[str, Any]:
    """Validate one zero/canary trace for each of four scenarios."""

    if len(traces) != 8:
        _fail("trace set must contain exactly eight documents")

    by_combination: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, value in enumerate(traces):
        scenario, variant = validate_trace_document(
            value,
            label=f"traces[{index}]",
        )
        key = (scenario, variant)
        if key in by_combination:
            _fail(f"duplicate trace combination: {scenario}/{variant}")
        by_combination[key] = _require_object(value, f"traces[{index}]")

    actual = frozenset(by_combination)
    if actual != EXPECTED_COMBINATIONS:
        missing = sorted(EXPECTED_COMBINATIONS - actual)
        extra = sorted(actual - EXPECTED_COMBINATIONS)
        _fail(f"trace combinations mismatch: missing={missing}, extra={extra}")

    for scenario in SCENARIO_CONTRACTS:
        zero = by_combination[(scenario, "zero")]
        canary = by_combination[(scenario, "canary")]
        if zero["callbacks"] != canary["callbacks"]:
            _fail(f"{scenario} zero/canary callbacks differ")
        if zero["counters"] != canary["counters"]:
            _fail(f"{scenario} zero/canary counters differ")
        if zero["termination"] != canary["termination"]:
            _fail(f"{scenario} zero/canary termination differs")
        for phase in ("pre", "post"):
            zero_normalized = _without_candidate(
                zero[phase], f"{scenario}/zero.{phase}"
            )
            canary_normalized = _without_candidate(
                canary[phase], f"{scenario}/canary.{phase}"
            )
            if zero_normalized != canary_normalized:
                _fail(
                    f"{scenario} zero/canary {phase} endpoints differ "
                    "outside candidate"
                )

    return {
        "schema": SCHEMA,
        "collector_version": COLLECTOR_VERSION,
        "status": "accepted-private-wram-ownership-trace-set",
        "trace_count": 8,
        "scenarios": sorted(SCENARIO_CONTRACTS),
        "variants": sorted(VARIANTS),
        "watched_byte_count": len(WATCHED_ADDRESSES),
        "candidate_and_guards_zero_access": True,
        "counter_callback_reconciliation": True,
        "zero_canary_observations_identical": True,
        "zero_canary_endpoints_equivalent_after_candidate_normalization": True,
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
    if len(paths) != 8:
        _fail("exactly eight trace paths are required")
    resolved = [path.resolve(strict=True) for path in paths]
    if len(set(resolved)) != 8:
        _fail("trace paths must be unique")
    return validate_trace_documents([load_trace(path) for path in resolved])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "trace",
        nargs=8,
        type=pathlib.Path,
        metavar="TRACE_JSON",
        help="eight compact trace JSON files, in any order",
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
