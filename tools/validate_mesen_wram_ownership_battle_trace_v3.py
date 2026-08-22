#!/usr/bin/env python3
"""Validate bounded native-Mesen Lavos battle WRAM-ownership traces.

This source-only validator consumes compact JSON and never reads a ROM, SRAM,
savestate, screenshot, or raw emulator trace.  It reuses the exact accepted v1
schema machinery, then adds battle pre/post anchors and a generic old-block
access census.  Candidate/guard accesses and roster/joined/Epoch writes remain
unconditionally forbidden.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import types
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Final


ROOT = Path(__file__).resolve().parents[1]
BASE_VALIDATOR_PATH = ROOT / "tools" / "validate_mesen_wram_ownership_trace.py"
BASE_VALIDATOR_SIZE: Final = 29_388
BASE_VALIDATOR_SHA256: Final = (
    "89a7dc86c6b5b10dc984b778451152e4"
    "734b5c553a669b7ee033e465ca87f2ba"
)

SCHEMA: Final = "project-epoch-mesen-wram-ownership-battle-trace-v3"
COLLECTOR_VERSION: Final = 3
MAX_TRACE_BYTES: Final = 4 * 1024 * 1024
CALLBACK_LIMIT: Final = 16_384
CHECKPOINT_ID: Final = "lavos-core-command-ready-canonical-v1"
CHECKPOINT_SIZE: Final = 261_614
CHECKPOINT_SHA256: Final = (
    "d5825ffff2f2a3b7edbe3c37e711815"
    "5d67727dc02ed672d13257f3824482b8b"
)
CHECKPOINT_FRAME: Final = 5_651
CHECKPOINT_DIRECT_PAGE: Final = 0x0000
CHECKPOINT_LOCATION: Final = 0x01DB

EXPECTED_ACTIVE: Final = "000102"
EXPECTED_ROSTER: Final = "000102828004030605"
EXPECTED_JOINED: Final = 0xFE
EXPECTED_BATTLE_IDS: Final = "000102cdffffccffffffcb00"
EXPECTED_FULL_HP: Final = (969, 898, 909, 8000, 12000, 20000)
EXPECTED_ATTACK_COMMAND_STATE: Final = "0000000000ffff000100000000"
EXPECTED_TECH_COMMAND_STATE: Final = "0001000000ffff000100000000"

BATTLE_SNAPSHOT_KEYS: Final = frozenset(
    {
        "location",
        "storyline",
        "pending_request",
        "explore_mode",
        "dialog_state",
        "active_party_hex",
        "roster_hex",
        "joined",
        "battle_ids_hex",
        "battle_current_hp",
        "battle_max_hp",
        "battle_ui_hex",
        "command_state_hex",
        "command_ready",
    }
)
TOP_LEVEL_KEYS: Final = frozenset(
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
        "pre_battle",
        "pre",
        "callbacks",
        "counters",
        "post",
        "post_battle",
        "termination",
    }
)


class BattleTraceValidationError(RuntimeError):
    """The private battle ownership trace violates its pinned contract."""


def _load_exact_base() -> types.ModuleType:
    try:
        source = BASE_VALIDATOR_PATH.read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"cannot read accepted base validator: {BASE_VALIDATOR_PATH}"
        ) from exc
    if len(source) != BASE_VALIDATOR_SIZE:
        raise RuntimeError("accepted base validator size drifted")
    actual = hashlib.sha256(source).hexdigest()
    if actual != BASE_VALIDATOR_SHA256:
        raise RuntimeError(
            "accepted base validator SHA-256 drifted: "
            f"expected {BASE_VALIDATOR_SHA256}, got {actual}"
        )
    code = compile(source, str(BASE_VALIDATOR_PATH), "exec", dont_inherit=True)
    module = types.ModuleType(
        "_project_epoch_mesen_wram_ownership_validator_v1_for_battle_v3"
    )
    module.__file__ = str(BASE_VALIDATOR_PATH)
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    exec(code, module.__dict__)
    return module


_BASE = _load_exact_base()
TraceValidationError = _BASE.TraceValidationError


def _pulse(button: str, start: int, width: int = 4) -> dict[str, Any]:
    return {
        "port": 1,
        "button": button,
        "start_frame": start,
        "end_frame": start + width - 1,
    }


SCENARIO_CONTRACTS: Final = {
    "calibration": {
        "terminal_frame_min": 0,
        "terminal_frame_max": 0,
        "expected_access_class": "none",
        "inputs": (),
    },
    "battle-idle": {
        "terminal_frame_min": 60,
        "terminal_frame_max": 60,
        "expected_access_class": "battle-ownership-census",
        "inputs": (),
    },
    "battle-command-roundtrip": {
        "terminal_frame_min": 60,
        "terminal_frame_max": 60,
        "expected_access_class": "battle-ownership-census",
        "inputs": (_pulse("DOWN", 20), _pulse("UP", 32)),
    },
    "battle-command-down": {
        "terminal_frame_min": 60,
        "terminal_frame_max": 60,
        "expected_access_class": "battle-ownership-census",
        "inputs": (_pulse("DOWN", 20),),
    },
}
VARIANTS: Final = frozenset({"zero", "canary"})
EXPECTED_COMBINATIONS: Final = frozenset(
    (scenario, variant)
    for scenario in SCENARIO_CONTRACTS
    for variant in VARIANTS
)


_BASE.SCHEMA = SCHEMA
_BASE.COLLECTOR_VERSION = COLLECTOR_VERSION
_BASE.MAX_TRACE_BYTES = MAX_TRACE_BYTES
_BASE.CALLBACK_LIMIT = CALLBACK_LIMIT
_BASE.CHECKPOINT_ID = CHECKPOINT_ID
_BASE.CHECKPOINT_SIZE = CHECKPOINT_SIZE
_BASE.CHECKPOINT_SHA256 = CHECKPOINT_SHA256
_BASE.CHECKPOINT_FRAME = CHECKPOINT_FRAME
_BASE.CHECKPOINT_DIRECT_PAGE = CHECKPOINT_DIRECT_PAGE
_BASE.CHECKPOINT_LOCATION = CHECKPOINT_LOCATION
_BASE.SCENARIO_CONTRACTS = SCENARIO_CONTRACTS
_BASE.VARIANTS = VARIANTS
_BASE.EXPECTED_COMBINATIONS = EXPECTED_COMBINATIONS
_BASE.EXPECTED_OBSERVER = {
    **_BASE.EXPECTED_OBSERVER,
    "callback_limit": CALLBACK_LIMIT,
}


def _expected_preparation_writes(
    scenario: str,
    variant: str,
) -> list[dict[str, Any]]:
    del scenario
    writes: list[dict[str, Any]] = []
    if variant == "canary":
        for index, byte in enumerate(_BASE.CANDIDATE_CANARY):
            writes.append(
                {
                    "seq": index,
                    "width": 1,
                    "raw_wram_offset": 0x2CA0 + index,
                    "value": byte,
                    "label": "candidate-variant",
                }
            )
    return writes


_BASE._expected_preparation_writes = _expected_preparation_writes


def _validate_callbacks_battle_v3(
    value: Any,
    scenario: str,
    terminal_frame_max: int,
    label: str,
) -> list[Mapping[str, Any]]:
    callbacks_value = _BASE._require_array(value, label)
    if len(callbacks_value) > CALLBACK_LIMIT:
        _BASE._fail(f"{label} exceeds callback limit {CALLBACK_LIMIT}")

    callbacks: list[Mapping[str, Any]] = []
    previous_frame = -1
    for index, callback_value in enumerate(callbacks_value):
        callback_label = f"{label}[{index}]"
        callback = _BASE._require_object(callback_value, callback_label)
        _BASE._require_exact_keys(
            callback,
            _BASE.CALLBACK_KEYS,
            callback_label,
        )
        _BASE._require_exact_scalar(
            callback["seq"],
            index,
            f"{callback_label}.seq",
        )
        frame = _BASE._require_int(
            callback["frame"],
            f"{callback_label}.frame",
            minimum=0,
            maximum=terminal_frame_max,
        )
        if frame < previous_frame:
            _BASE._fail(f"{label} frames must be nondecreasing")
        previous_frame = frame

        access = callback["access"]
        if type(access) is not str or access not in {"read", "write"}:
            _BASE._fail(f"{callback_label}.access must be 'read' or 'write'")
        address = _BASE._require_int(
            callback["address"],
            f"{callback_label}.address",
            minimum=0,
            maximum=0xFFFFFF,
        )
        if address not in _BASE.WATCHED_ADDRESS_SET:
            _BASE._fail(f"{callback_label}.address is outside watched ranges")
        _BASE._require_int(
            callback["value"],
            f"{callback_label}.value",
            minimum=0,
            maximum=0xFF,
        )
        _BASE._require_int(
            callback["pc24"],
            f"{callback_label}.pc24",
            minimum=0,
            maximum=0xFFFFFF,
        )

        range_name = _BASE.ADDRESS_RANGE_NAME[address]
        if range_name in {"candidate", "front-guard", "rear-guard"}:
            _BASE._fail(f"{callback_label} illegally accesses {range_name}")
        if access == "write" and range_name in {
            "epoch-name",
            "roster",
            "joined",
        }:
            _BASE._fail(f"{callback_label} illegally writes {range_name}")
        if access == "write" and range_name == "old-compatibility":
            _BASE._fail(
                f"{callback_label} is an unapproved old-compatibility write"
            )
        # Old-compatibility reads are the subject of this census.  They remain
        # byte-exact, ordered, counter-reconciled, and pair-matched.
        callbacks.append(callback)

    if scenario == "calibration" and callbacks:
        _BASE._fail("calibration must have zero armed watched-range callbacks")
    return callbacks


def _reconcile_snapshots_battle_v3(
    pre: Mapping[str, bytes],
    callbacks: Sequence[Mapping[str, Any]],
    post: Mapping[str, bytes],
    scenario: str,
    label: str,
) -> None:
    del scenario
    simulated = _BASE._snapshot_address_map(pre)
    for index, callback in enumerate(callbacks):
        address = callback["address"]
        value = callback["value"]
        if callback["access"] == "read":
            if simulated[address] != value:
                _BASE._fail(
                    f"{label}.callbacks[{index}] read value does not match "
                    "the simulated watched byte"
                )
        else:
            simulated[address] = value
    expected_post = _BASE._snapshot_address_map(post)
    for address in _BASE.WATCHED_ADDRESSES:
        if simulated[address] != expected_post[address]:
            _BASE._fail(
                f"{label}.post does not reconcile callbacks at "
                f"${address:06X}"
            )


_BASE._validate_callbacks = _validate_callbacks_battle_v3
_BASE._reconcile_snapshots = _reconcile_snapshots_battle_v3
_ORIGINAL_VALIDATE_TRACE_DOCUMENT = _BASE.validate_trace_document


def _require_exact_number_array(
    value: Any,
    expected: tuple[int, ...],
    label: str,
) -> None:
    rows = _BASE._require_array(value, label)
    if len(rows) != len(expected):
        _BASE._fail(f"{label} must contain exactly {len(expected)} values")
    for index, (actual, wanted) in enumerate(zip(rows, expected, strict=True)):
        _BASE._require_exact_scalar(actual, wanted, f"{label}[{index}]")


def _validate_battle_snapshot(
    value: Any,
    *,
    scenario: str,
    phase: str,
    range_snapshot: Mapping[str, Any],
    label: str,
) -> None:
    battle = _BASE._require_object(value, label)
    _BASE._require_exact_keys(battle, BATTLE_SNAPSHOT_KEYS, label)
    expected_scalars = {
        "location": 0x01DB,
        "storyline": 0xD6,
        "pending_request": 0x01,
        "explore_mode": 0,
        "dialog_state": 0,
        "active_party_hex": EXPECTED_ACTIVE,
        "roster_hex": EXPECTED_ROSTER,
        "joined": EXPECTED_JOINED,
        "battle_ids_hex": EXPECTED_BATTLE_IDS,
        "battle_ui_hex": "0059ac",
        "command_ready": True,
    }
    for key, expected in expected_scalars.items():
        _BASE._require_exact_scalar(battle[key], expected, f"{label}.{key}")
    _require_exact_number_array(
        battle["battle_current_hp"],
        EXPECTED_FULL_HP,
        f"{label}.battle_current_hp",
    )
    _require_exact_number_array(
        battle["battle_max_hp"],
        EXPECTED_FULL_HP,
        f"{label}.battle_max_hp",
    )
    command_state = EXPECTED_ATTACK_COMMAND_STATE
    if phase == "post" and scenario == "battle-command-down":
        command_state = EXPECTED_TECH_COMMAND_STATE
    _BASE._require_exact_scalar(
        battle["command_state_hex"],
        command_state,
        f"{label}.command_state_hex",
    )

    roster_hex = _BASE._require_lower_hex(
        range_snapshot["roster_hex"],
        18,
        f"{label}.range_roster_hex",
    )
    joined_hex = _BASE._require_lower_hex(
        range_snapshot["joined_hex"],
        2,
        f"{label}.range_joined_hex",
    )
    if roster_hex != battle["roster_hex"]:
        _BASE._fail(f"{label} roster disagrees with watched-range snapshot")
    if joined_hex != f"{battle['joined']:02x}":
        _BASE._fail(f"{label} joined flag disagrees with watched-range snapshot")


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    """Validate one decoded battle trace and return scenario/variant."""

    trace = _BASE._require_object(value, label)
    _BASE._require_exact_keys(trace, TOP_LEVEL_KEYS, label)
    stripped = {
        key: field_value
        for key, field_value in trace.items()
        if key not in {"pre_battle", "post_battle"}
    }
    scenario, variant = _ORIGINAL_VALIDATE_TRACE_DOCUMENT(
        stripped,
        label=label,
    )
    _validate_battle_snapshot(
        trace["pre_battle"],
        scenario=scenario,
        phase="pre",
        range_snapshot=_BASE._require_object(trace["pre"], f"{label}.pre"),
        label=f"{label}.pre_battle",
    )
    _validate_battle_snapshot(
        trace["post_battle"],
        scenario=scenario,
        phase="post",
        range_snapshot=_BASE._require_object(trace["post"], f"{label}.post"),
        label=f"{label}.post_battle",
    )
    return scenario, variant


def _without_candidate(snapshot: Any, label: str) -> dict[str, Any]:
    value = _BASE._require_object(snapshot, label)
    return {
        key: field_value
        for key, field_value in value.items()
        if key != "candidate_hex"
    }


def validate_trace_documents(traces: Sequence[Any]) -> dict[str, Any]:
    """Validate one zero/canary trace for all four bounded battle scenarios."""

    if len(traces) != len(EXPECTED_COMBINATIONS):
        _BASE._fail(
            f"trace set must contain exactly {len(EXPECTED_COMBINATIONS)} "
            "documents"
        )

    by_combination: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, value in enumerate(traces):
        scenario, variant = validate_trace_document(
            value,
            label=f"traces[{index}]",
        )
        key = (scenario, variant)
        if key in by_combination:
            _BASE._fail(f"duplicate trace combination: {scenario}/{variant}")
        by_combination[key] = _BASE._require_object(
            value,
            f"traces[{index}]",
        )
    actual = frozenset(by_combination)
    if actual != EXPECTED_COMBINATIONS:
        missing = sorted(EXPECTED_COMBINATIONS - actual)
        extra = sorted(actual - EXPECTED_COMBINATIONS)
        _BASE._fail(
            f"trace combinations mismatch: missing={missing}, extra={extra}"
        )

    old_block_read_count = 0
    old_block_write_count = 0
    shared_pre_without_candidate: dict[str, Any] | None = None
    shared_pre_battle: Mapping[str, Any] | None = None
    for scenario in SCENARIO_CONTRACTS:
        zero = by_combination[(scenario, "zero")]
        canary = by_combination[(scenario, "canary")]
        for field in (
            "callbacks",
            "counters",
            "termination",
            "pre_battle",
            "post_battle",
        ):
            if zero[field] != canary[field]:
                _BASE._fail(f"{scenario} zero/canary {field} differs")
        for phase in ("pre", "post"):
            if _without_candidate(
                zero[phase],
                f"{scenario}/zero.{phase}",
            ) != _without_candidate(
                canary[phase],
                f"{scenario}/canary.{phase}",
            ):
                _BASE._fail(
                    f"{scenario} zero/canary {phase} differs outside candidate"
                )
        normalized_pre = _without_candidate(
            zero["pre"],
            f"{scenario}/zero.pre",
        )
        if shared_pre_without_candidate is None:
            shared_pre_without_candidate = normalized_pre
            shared_pre_battle = _BASE._require_object(
                zero["pre_battle"],
                f"{scenario}/zero.pre_battle",
            )
        else:
            if normalized_pre != shared_pre_without_candidate:
                _BASE._fail(
                    f"{scenario} pre snapshot does not share the canonical "
                    "checkpoint preimage"
                )
            if zero["pre_battle"] != shared_pre_battle:
                _BASE._fail(
                    f"{scenario} battle pre-snapshot does not share the "
                    "canonical checkpoint preimage"
                )
        for callback in zero["callbacks"]:
            if (
                isinstance(callback, Mapping)
                and 0x7E2830 <= callback.get("address", -1) <= 0x7E287F
            ):
                if callback.get("access") == "read":
                    old_block_read_count += 1
                elif callback.get("access") == "write":
                    old_block_write_count += 1

    return {
        "schema": SCHEMA,
        "collector_version": COLLECTOR_VERSION,
        "status": "validated-private-battle-wram-ownership-trace-set",
        "trace_count": len(traces),
        "scenarios": list(SCENARIO_CONTRACTS),
        "variants": sorted(VARIANTS),
        "watched_byte_count": len(_BASE.WATCHED_ADDRESSES),
        "candidate_and_guards_zero_access": True,
        "roster_joined_epoch_writes_forbidden": True,
        "counter_callback_reconciliation": True,
        "zero_canary_observations_identical": True,
        "zero_canary_endpoints_equivalent_after_candidate_normalization": True,
        "all_scenarios_share_one_normalized_checkpoint_preimage": True,
        "old_compatibility_reads_in_zero_variants": old_block_read_count,
        "old_compatibility_writes_in_zero_variants": old_block_write_count,
    }


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BattleTraceValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_trace(path: Path) -> Mapping[str, Any]:
    if path.suffix.lower() != ".json" or not path.is_file():
        raise BattleTraceValidationError(
            f"trace input must be an existing .json file: {path}"
        )
    if path.stat().st_size > MAX_TRACE_BYTES:
        raise BattleTraceValidationError(
            f"trace input exceeds {MAX_TRACE_BYTES} bytes: {path}"
        )
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except BattleTraceValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BattleTraceValidationError(
            f"cannot decode trace JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise BattleTraceValidationError(f"trace root must be an object: {path}")
    return value


def validate_trace_files(paths: Sequence[Path]) -> dict[str, Any]:
    return validate_trace_documents([load_trace(path) for path in paths])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", nargs="+", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_trace_files(args.trace)
    except (
        BattleTraceValidationError,
        TraceValidationError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
