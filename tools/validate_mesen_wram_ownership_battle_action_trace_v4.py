#!/usr/bin/env python3
"""Validate bounded native-Mesen Lavos action/recovery ownership traces.

This source-only validator exact-loads the exploratory v4 validator and keeps
all v3 ownership protections.  It adds exact control, Attack target-hold, and
Attack recovery endpoints plus causal action milestones and zero/canary pair
identity.  It never reads a ROM, save, state, screenshot, or raw emulator log.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys
import types
from typing import Any, Final


ROOT = Path(__file__).resolve().parents[1]
PROBE_VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_action_probe_v4.py"
)
PROBE_VALIDATOR_SIZE: Final = 18_791
PROBE_VALIDATOR_SHA256: Final = (
    "5da3bbdc8817085a302eba7426f1b6b54"
    "54096dd5e0e6caa9de7cfa2564c6921"
)
SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-trace-v4"
)
COLLECTOR_VERSION: Final = 4


def _pulse(button: str, start: int, width: int = 4) -> dict[str, Any]:
    return {
        "port": 1,
        "button": button,
        "start_frame": start,
        "end_frame": start + width - 1,
    }


SCENARIO_CONTRACTS: Final = {
    "battle-action-control": {
        "terminal_frame_min": 606,
        "terminal_frame_max": 606,
        "expected_access_class": "battle-action-ownership-census",
        "inputs": (),
    },
    "battle-attack-target-hold": {
        "terminal_frame_min": 60,
        "terminal_frame_max": 60,
        "expected_access_class": "battle-action-ownership-census",
        "inputs": (_pulse("A", 20),),
    },
    "battle-attack-recovery": {
        "terminal_frame_min": 606,
        "terminal_frame_max": 606,
        "expected_access_class": "battle-action-ownership-census",
        "inputs": (_pulse("A", 20), _pulse("A", 32)),
    },
}
VARIANTS: Final = frozenset({"zero", "canary"})
EXPECTED_COMBINATIONS: Final = frozenset(
    (scenario, variant)
    for scenario in SCENARIO_CONTRACTS
    for variant in VARIANTS
)
EXPECTED_ENDPOINTS: Final = {
    "battle-action-control": {
        "row_count": 269,
        "last": {
            "frame": 603,
            "current_hp": [739, 821, 712, 8000, 12000, 20000],
            "status_hex": "00" * 24,
            "target_state_hex": "00" * 13,
            "target_list_hex": "00" * 12,
            "pc_fifo_hex": "ffffffff0003",
            "menu_ready_hex": "000102ff00030002",
            "pc_command_records_hex": (
                "8100000000ff008100000000ff008100000000ff00"
            ),
            "action_request_hex": "00060273000020ffff000000",
            "action_targets_hex": "0102ffffffffffffffffffff",
            "logic_busy_hex": "0100000100000001040000",
            "action_slots_hex": "ffffffffffffffffffffff03",
            "ai_state_hex": "000000",
            "resolution_flags_hex": "030308",
            "battle_ui_hex": "03bf59",
            "command_state_hex": "00000000000102000300000000",
        },
    },
    "battle-attack-target-hold": {
        "row_count": 17,
        "last": {
            "frame": 60,
            "current_hp": [969, 898, 909, 8000, 12000, 20000],
            "status_hex": "00" * 24,
            "target_state_hex": "01010000070000000000000000",
            "target_list_hex": "03ffffffffffffffffffffff",
            "pc_fifo_hex": "ffffffff0003",
            "menu_ready_hex": "00ffffff00010001",
            "pc_command_records_hex": (
                "8100000000ff000000000000ff000000000000ff00"
            ),
            "action_request_hex": "0003024300008006ff006000",
            "action_targets_hex": "03000102ffffffffffffffff",
            "logic_busy_hex": "01000000000000010b0001",
            "action_slots_hex": "03ffffffffffffffffffff06",
            "ai_state_hex": "000000",
            "resolution_flags_hex": "000000",
            "battle_ui_hex": "0059ac",
            "command_state_hex": "0000000000ffff000100000000",
        },
    },
    "battle-attack-recovery": {
        "row_count": 206,
        "last": {
            "frame": 606,
            "current_hp": [739, 821, 712, 7038, 12000, 20000],
            "status_hex": "00" * 24,
            "target_state_hex": "00010000070000000000000000",
            "target_list_hex": "03ffffffffffffffffffffff",
            "pc_fifo_hex": "ffffffff0003",
            "menu_ready_hex": "ff01ffff01010102",
            "pc_command_records_hex": (
                "0000000000ff008100000000ff000000000000ff00"
            ),
            "action_request_hex": "00000100000000ffff000000",
            "action_targets_hex": "01ffffffffffffffffffffff",
            "logic_busy_hex": "0100000100000001040000",
            "action_slots_hex": "ffffffffffffffffffffff00",
            "ai_state_hex": "000000",
            "resolution_flags_hex": "000808",
            "battle_ui_hex": "003a00",
            "command_state_hex": "01000000ff01ff010100000000",
        },
    },
}


class BattleActionValidationError(RuntimeError):
    """A bounded v4 action trace violates its exact contract."""


def _load_exact_probe_validator() -> types.ModuleType:
    try:
        source = PROBE_VALIDATOR_PATH.read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"cannot read exact action-probe validator: {PROBE_VALIDATOR_PATH}"
        ) from exc
    if len(source) != PROBE_VALIDATOR_SIZE:
        raise RuntimeError("action-probe validator size drifted")
    actual = hashlib.sha256(source).hexdigest()
    if actual != PROBE_VALIDATOR_SHA256:
        raise RuntimeError(
            "action-probe validator SHA-256 drifted: "
            f"expected {PROBE_VALIDATOR_SHA256}, got {actual}"
        )
    code = compile(source, str(PROBE_VALIDATOR_PATH), "exec", dont_inherit=True)
    name = "_project_epoch_battle_action_probe_validator_for_v4"
    module = types.ModuleType(name)
    module.__file__ = str(PROBE_VALIDATOR_PATH)
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


_PROBE = _load_exact_probe_validator()
_V3 = _PROBE._V3
_BASE = _PROBE._BASE
TraceValidationError = _PROBE.TraceValidationError
BattleTraceValidationError = _PROBE.BattleTraceValidationError
ActionProbeValidationError = _PROBE.ActionProbeValidationError
_PROBE_ACTION_TIMELINE_VALIDATOR = _PROBE._validate_action_timeline

for module in (_PROBE, _V3, _BASE):
    module.SCHEMA = SCHEMA
    module.COLLECTOR_VERSION = COLLECTOR_VERSION
    module.SCENARIO_CONTRACTS = SCENARIO_CONTRACTS
    module.VARIANTS = VARIANTS
    module.EXPECTED_COMBINATIONS = EXPECTED_COMBINATIONS


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
_V3._expected_preparation_writes = _expected_preparation_writes


def _validate_battle_snapshot(
    value: Any,
    *,
    scenario: str,
    phase: str,
    range_snapshot: Mapping[str, Any],
    label: str,
) -> None:
    if phase == "pre":
        _PROBE._V3_PRE_BATTLE_VALIDATOR(
            value,
            scenario=scenario,
            phase=phase,
            range_snapshot=range_snapshot,
            label=label,
        )
        return
    battle = _BASE._require_object(value, label)
    _BASE._require_exact_keys(battle, _V3.BATTLE_SNAPSHOT_KEYS, label)
    persistent = {
        "location": 0x01DB,
        "storyline": 0xD6,
        "pending_request": 0x01,
        "explore_mode": 0,
        "dialog_state": 0,
        "active_party_hex": _V3.EXPECTED_ACTIVE,
        "roster_hex": _V3.EXPECTED_ROSTER,
        "joined": _V3.EXPECTED_JOINED,
        "battle_ids_hex": _V3.EXPECTED_BATTLE_IDS,
        "command_ready": True,
    }
    for key, expected in persistent.items():
        _BASE._require_exact_scalar(battle[key], expected, f"{label}.{key}")
    endpoint = EXPECTED_ENDPOINTS[scenario]["last"]
    _BASE._require_exact_scalar(
        battle["battle_current_hp"],
        endpoint["current_hp"],
        f"{label}.battle_current_hp",
    )
    _BASE._require_exact_scalar(
        battle["battle_max_hp"],
        list(_PROBE.EXPECTED_FULL_HP),
        f"{label}.battle_max_hp",
    )
    _BASE._require_exact_scalar(
        battle["battle_ui_hex"],
        endpoint["battle_ui_hex"],
        f"{label}.battle_ui_hex",
    )
    _BASE._require_exact_scalar(
        battle["command_state_hex"],
        endpoint["command_state_hex"],
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


_V3._validate_battle_snapshot = _validate_battle_snapshot


def _timeline_contains(
    rows: Sequence[Mapping[str, Any]],
    *,
    frame: int,
    key: str,
    value: Any,
) -> bool:
    return any(row["frame"] == frame and row[key] == value for row in rows)


def _expected_callbacks(scenario: str) -> list[dict[str, Any]]:
    if scenario != "battle-attack-recovery":
        return []
    return [
        {
            "seq": 0,
            "frame": 377,
            "access": "read",
            "address": 0x7E2980,
            "value": 0,
            "pc24": 0xC14A43,
        },
        {
            "seq": 1,
            "frame": 377,
            "access": "read",
            "address": 0x7E2980,
            "value": 0,
            "pc24": 0xC1438A,
        },
    ]


def _validate_action_timeline(
    value: Any,
    *,
    scenario: str,
    terminal_frame: int,
    pre_battle: Mapping[str, Any],
    post_battle: Mapping[str, Any],
    label: str,
) -> list[Mapping[str, Any]]:
    rows = _PROBE_ACTION_TIMELINE_VALIDATOR(
        value,
        scenario="enemy-inflight-resolution",
        terminal_frame=terminal_frame,
        pre_battle=pre_battle,
        post_battle=post_battle,
        label=label,
    )
    endpoint = EXPECTED_ENDPOINTS[scenario]
    if len(rows) != endpoint["row_count"]:
        _BASE._fail(
            f"{label} must contain exactly {endpoint['row_count']} rows"
        )
    if rows[-1] != endpoint["last"]:
        _BASE._fail(f"{label} exact terminal action signature drifted")

    if scenario == "battle-action-control":
        required = (
            (
                336,
                "current_hp",
                [739, 821, 712, 8000, 12000, 20000],
            ),
            (
                363,
                "action_request_hex",
                "00030200000000ffff000000",
            ),
        )
    elif scenario == "battle-attack-target-hold":
        required = (
            (
                20,
                "target_state_hex",
                "01010000070000000000000000",
            ),
        )
    else:
        required = (
            (32, "pc_fifo_hex", "00ffffff0103"),
            (373, "pc_fifo_hex", "ffffffff0003"),
            (
                375,
                "action_request_hex",
                "00000100000010ffff000080",
            ),
            (
                337,
                "current_hp",
                [739, 821, 712, 8000, 12000, 20000],
            ),
            (
                557,
                "current_hp",
                [739, 821, 712, 7038, 12000, 20000],
            ),
        )
    for frame, key, expected in required:
        if not _timeline_contains(
            rows,
            frame=frame,
            key=key,
            value=expected,
        ):
            _BASE._fail(
                f"{label} is missing causal milestone "
                f"frame={frame} field={key}"
            )
    return rows


_PROBE._validate_action_timeline = _validate_action_timeline


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    """Validate one exact bounded action trace."""

    trace = _BASE._require_object(value, label)
    _BASE._require_exact_keys(trace, _PROBE.TOP_LEVEL_KEYS, label)
    stripped = {
        key: field_value
        for key, field_value in trace.items()
        if key != "action_timeline"
    }
    scenario, variant = _V3.validate_trace_document(
        stripped,
        label=label,
    )
    if trace["callbacks"] != _expected_callbacks(scenario):
        _BASE._fail(f"{scenario} exact callback route drifted")
    termination = _BASE._require_object(
        trace["termination"],
        f"{label}.termination",
    )
    terminal_frame = _BASE._require_int(
        termination["terminal_frame"],
        f"{label}.termination.terminal_frame",
        minimum=0,
        maximum=SCENARIO_CONTRACTS[scenario]["terminal_frame_max"],
    )
    _validate_action_timeline(
        trace["action_timeline"],
        scenario=scenario,
        terminal_frame=terminal_frame,
        pre_battle=_BASE._require_object(
            trace["pre_battle"],
            f"{label}.pre_battle",
        ),
        post_battle=_BASE._require_object(
            trace["post_battle"],
            f"{label}.post_battle",
        ),
        label=f"{label}.action_timeline",
    )
    return scenario, variant


def validate_trace_documents(traces: Sequence[Any]) -> dict[str, Any]:
    """Validate exact zero/canary pairs for all three action scenarios."""

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
    if frozenset(by_combination) != EXPECTED_COMBINATIONS:
        _BASE._fail("battle-action trace combinations mismatch")

    shared_pre: Mapping[str, Any] | None = None
    shared_battle: Mapping[str, Any] | None = None
    old_reads = 0
    roster_reads = 0
    for scenario in SCENARIO_CONTRACTS:
        zero = by_combination[(scenario, "zero")]
        canary = by_combination[(scenario, "canary")]
        for key in (
            "callbacks",
            "counters",
            "pre_battle",
            "post_battle",
            "action_timeline",
            "termination",
        ):
            if zero[key] != canary[key]:
                _BASE._fail(f"{scenario} zero/canary {key} differs")
        for phase in ("pre", "post"):
            if _V3._without_candidate(
                zero[phase],
                f"{scenario}/zero.{phase}",
            ) != _V3._without_candidate(
                canary[phase],
                f"{scenario}/canary.{phase}",
            ):
                _BASE._fail(
                    f"{scenario} zero/canary {phase} differs outside candidate"
                )
        normalized = _V3._without_candidate(
            zero["pre"],
            f"{scenario}/zero.pre",
        )
        if shared_pre is None:
            shared_pre = normalized
            shared_battle = zero["pre_battle"]
        elif normalized != shared_pre or zero["pre_battle"] != shared_battle:
            _BASE._fail(
                f"{scenario} does not share the canonical checkpoint preimage"
            )
        if zero["callbacks"] != _expected_callbacks(scenario):
            _BASE._fail(f"{scenario} exact callback route drifted")
        for callback in zero["callbacks"]:
            address = callback.get("address", -1)
            if callback.get("access") == "read":
                if 0x7E2830 <= address <= 0x7E287F:
                    old_reads += 1
                if 0x7E2980 <= address <= 0x7E2988:
                    roster_reads += 1

    return {
        "schema": SCHEMA,
        "collector_version": COLLECTOR_VERSION,
        "status": "validated-private-battle-action-wram-ownership-trace-set",
        "trace_count": len(traces),
        "scenarios": list(SCENARIO_CONTRACTS),
        "variants": sorted(VARIANTS),
        "watched_byte_count": len(_BASE.WATCHED_ADDRESSES),
        "candidate_and_guards_any_access_forbidden": True,
        "old_compatibility_writes_forbidden": True,
        "roster_joined_epoch_writes_forbidden": True,
        "counter_callback_reconciliation": True,
        "zero_canary_observations_identical": True,
        "shared_checkpoint_preimage": True,
        "old_compatibility_reads_in_zero_variants": old_reads,
        "roster_reads_in_zero_variants": roster_reads,
        "action_control_party_hp": [739, 821, 712],
        "attack_recovery_party_hp": [739, 821, 712],
        "attack_recovery_enemy_slot3_hp": 7038,
        "attack_recovery_critical_marker_frame": 375,
        "attack_recovery_critical_marker": "AE9B-bit-80",
        "attack_recovery_exact_roster_read_pcs": ["C14A43", "C1438A"],
        "target_hold_full_hp": True,
    }


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BattleActionValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_trace(path: Path) -> Mapping[str, Any]:
    if path.suffix.lower() != ".json" or not path.is_file():
        raise BattleActionValidationError(
            f"trace input must be an existing .json file: {path}"
        )
    if path.stat().st_size > _PROBE.MAX_TRACE_BYTES:
        raise BattleActionValidationError(
            f"trace input exceeds {_PROBE.MAX_TRACE_BYTES} bytes: {path}"
        )
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except BattleActionValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BattleActionValidationError(
            f"cannot decode trace JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise BattleActionValidationError(
            f"trace root must be an object: {path}"
        )
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
        BattleActionValidationError,
        ActionProbeValidationError,
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
