#!/usr/bin/env python3
"""Validate zero-only exploratory Lavos battle-action ownership probes.

The validator consumes compact JSON only.  It exact-loads the accepted v3
battle validator and retains its 196-byte watcher rules: candidate and guards
may not be accessed, old compatibility bytes may not be written, protected
party/Epoch metadata may not be written, and access counters must reconcile
with callbacks.  V4 adds a compact action-state timeline while deliberately
leaving action-result endpoints exploratory.
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
V3_VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_trace_v3.py"
)
V3_VALIDATOR_SIZE: Final = 20_095
V3_VALIDATOR_SHA256: Final = (
    "b5ecc2c3cd81d34e5cc94428fcd45bbd"
    "39496c4ba1080a97db3c47380a6f5155"
)

SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-probe-trace-v4"
)
COLLECTOR_VERSION: Final = 4
MAX_TRACE_BYTES: Final = 4 * 1024 * 1024
MAX_TIMELINE_ROWS: Final = 1_501
EXPECTED_FULL_HP: Final = (969, 898, 909, 8000, 12000, 20000)
EXPECTED_INITIAL_ACTION: Final = {
    "current_hp": list(EXPECTED_FULL_HP),
    "status_hex": "00" * 24,
    "target_state_hex": "00" * 13,
    "target_list_hex": "00" * 12,
    "pc_fifo_hex": "ffffffff0003",
    "menu_ready_hex": "00ffffff00010000",
    "pc_command_records_hex": "8100000000ff000000000000ff000000000000ff00",
    "action_request_hex": "0003024300008006ff006000",
    "action_targets_hex": "03000102ffffffffffffffff",
    "logic_busy_hex": "01000000000000010b0001",
    "action_slots_hex": "03ffffffffffffffffffff06",
    "ai_state_hex": "000000",
    "resolution_flags_hex": "000000",
    "battle_ui_hex": "0059ac",
    "command_state_hex": "0000000000ffff000100000000",
}


def _pulse(button: str, start: int, width: int = 4) -> dict[str, Any]:
    return {
        "port": 1,
        "button": button,
        "start_frame": start,
        "end_frame": start + width - 1,
    }


SCENARIO_CONTRACTS: Final = {
    "enemy-inflight-resolution": {
        "terminal_frame_min": 1_500,
        "terminal_frame_max": 1_500,
        "expected_access_class": (
            "exploratory-battle-action-ownership-census"
        ),
        "inputs": (),
    },
    "attack-target-hold": {
        "terminal_frame_min": 60,
        "terminal_frame_max": 60,
        "expected_access_class": (
            "exploratory-battle-action-ownership-census"
        ),
        "inputs": (_pulse("A", 20),),
    },
    "attack-action-horizon": {
        "terminal_frame_min": 1_500,
        "terminal_frame_max": 1_500,
        "expected_access_class": (
            "exploratory-battle-action-ownership-census"
        ),
        "inputs": (_pulse("A", 20), _pulse("A", 32)),
    },
}
VARIANTS: Final = frozenset({"zero"})
EXPECTED_COMBINATIONS: Final = frozenset(
    (scenario, "zero") for scenario in SCENARIO_CONTRACTS
)
ACTION_ROW_KEYS: Final = frozenset(
    {
        "frame",
        "current_hp",
        "status_hex",
        "target_state_hex",
        "target_list_hex",
        "pc_fifo_hex",
        "menu_ready_hex",
        "pc_command_records_hex",
        "action_request_hex",
        "action_targets_hex",
        "logic_busy_hex",
        "action_slots_hex",
        "ai_state_hex",
        "resolution_flags_hex",
        "battle_ui_hex",
        "command_state_hex",
    }
)
ACTION_HEX_LENGTHS: Final = {
    "status_hex": 48,
    "target_state_hex": 26,
    "target_list_hex": 24,
    "pc_fifo_hex": 12,
    "menu_ready_hex": 16,
    "pc_command_records_hex": 42,
    "action_request_hex": 24,
    "action_targets_hex": 24,
    "logic_busy_hex": 22,
    "action_slots_hex": 24,
    "ai_state_hex": 6,
    "resolution_flags_hex": 6,
    "battle_ui_hex": 6,
    "command_state_hex": 26,
}


class ActionProbeValidationError(RuntimeError):
    """A v4 exploratory action trace violates its source contract."""


def _load_exact_v3_validator() -> types.ModuleType:
    try:
        source = V3_VALIDATOR_PATH.read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"cannot read exact v3 validator: {V3_VALIDATOR_PATH}"
        ) from exc
    if len(source) != V3_VALIDATOR_SIZE:
        raise RuntimeError("v3 validator size drifted")
    actual = hashlib.sha256(source).hexdigest()
    if actual != V3_VALIDATOR_SHA256:
        raise RuntimeError(
            "v3 validator SHA-256 drifted: "
            f"expected {V3_VALIDATOR_SHA256}, got {actual}"
        )
    code = compile(source, str(V3_VALIDATOR_PATH), "exec", dont_inherit=True)
    name = "_project_epoch_battle_validator_v3_for_action_probe_v4"
    module = types.ModuleType(name)
    module.__file__ = str(V3_VALIDATOR_PATH)
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


_V3 = _load_exact_v3_validator()
_BASE = _V3._BASE
TraceValidationError = _V3.TraceValidationError
BattleTraceValidationError = _V3.BattleTraceValidationError
_V3_PRE_BATTLE_VALIDATOR = _V3._validate_battle_snapshot

_V3.SCHEMA = SCHEMA
_V3.COLLECTOR_VERSION = COLLECTOR_VERSION
_V3.SCENARIO_CONTRACTS = SCENARIO_CONTRACTS
_V3.VARIANTS = VARIANTS
_V3.EXPECTED_COMBINATIONS = EXPECTED_COMBINATIONS
_BASE.SCHEMA = SCHEMA
_BASE.COLLECTOR_VERSION = COLLECTOR_VERSION
_BASE.SCENARIO_CONTRACTS = SCENARIO_CONTRACTS
_BASE.VARIANTS = VARIANTS
_BASE.EXPECTED_COMBINATIONS = EXPECTED_COMBINATIONS


def _expected_preparation_writes(
    scenario: str,
    variant: str,
) -> list[dict[str, Any]]:
    del scenario
    if variant != "zero":
        _BASE._fail("battle-action probes are zero-only")
    return []


_BASE._expected_preparation_writes = _expected_preparation_writes


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


def _require_bounded_hp(value: Any, label: str) -> list[int]:
    rows = _BASE._require_array(value, label)
    if len(rows) != len(EXPECTED_FULL_HP):
        _BASE._fail(
            f"{label} must contain exactly {len(EXPECTED_FULL_HP)} values"
        )
    result: list[int] = []
    for index, (actual, maximum) in enumerate(
        zip(rows, EXPECTED_FULL_HP, strict=True)
    ):
        result.append(
            _BASE._require_int(
                actual,
                f"{label}[{index}]",
                minimum=0,
                maximum=maximum,
            )
        )
    return result


def _validate_battle_snapshot_v4(
    value: Any,
    *,
    scenario: str,
    phase: str,
    range_snapshot: Mapping[str, Any],
    label: str,
) -> None:
    if phase == "pre":
        _V3_PRE_BATTLE_VALIDATOR(
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
    }
    for key, expected in persistent.items():
        _BASE._require_exact_scalar(battle[key], expected, f"{label}.{key}")
    current_hp = _require_bounded_hp(
        battle["battle_current_hp"],
        f"{label}.battle_current_hp",
    )
    _require_exact_number_array(
        battle["battle_max_hp"],
        EXPECTED_FULL_HP,
        f"{label}.battle_max_hp",
    )
    if scenario == "attack-target-hold" and tuple(current_hp) != EXPECTED_FULL_HP:
        _BASE._fail("attack-target-hold must retain the full-HP control anchor")
    _BASE._require_lower_hex(
        battle["battle_ui_hex"],
        6,
        f"{label}.battle_ui_hex",
    )
    _BASE._require_lower_hex(
        battle["command_state_hex"],
        26,
        f"{label}.command_state_hex",
    )
    if type(battle["command_ready"]) is not bool:
        _BASE._fail(f"{label}.command_ready must be boolean")

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


_V3._validate_battle_snapshot = _validate_battle_snapshot_v4


def _validate_action_timeline(
    value: Any,
    *,
    scenario: str,
    terminal_frame: int,
    pre_battle: Mapping[str, Any],
    post_battle: Mapping[str, Any],
    label: str,
) -> list[Mapping[str, Any]]:
    rows_value = _BASE._require_array(value, label)
    if not rows_value or len(rows_value) > MAX_TIMELINE_ROWS:
        _BASE._fail(
            f"{label} must contain 1..{MAX_TIMELINE_ROWS} change rows"
        )
    rows: list[Mapping[str, Any]] = []
    prior_frame = -1
    prior_signature: tuple[Any, ...] | None = None
    for index, row_value in enumerate(rows_value):
        row_label = f"{label}[{index}]"
        row = _BASE._require_object(row_value, row_label)
        _BASE._require_exact_keys(row, ACTION_ROW_KEYS, row_label)
        frame = _BASE._require_int(
            row["frame"],
            f"{row_label}.frame",
            minimum=0,
            maximum=terminal_frame,
        )
        if frame < prior_frame:
            _BASE._fail(f"{label} frames must be nondecreasing")
        prior_frame = frame
        hp = _require_bounded_hp(
            row["current_hp"],
            f"{row_label}.current_hp",
        )
        hex_values: list[str] = []
        for key, length in ACTION_HEX_LENGTHS.items():
            hex_values.append(
                _BASE._require_lower_hex(
                    row[key],
                    length,
                    f"{row_label}.{key}",
                )
            )
        signature = (tuple(hp), *hex_values)
        if signature == prior_signature:
            _BASE._fail(f"{row_label} duplicates the prior action signature")
        prior_signature = signature
        rows.append(row)

    first = rows[0]
    _BASE._require_exact_scalar(first["frame"], 0, f"{label}[0].frame")
    for key, expected in EXPECTED_INITIAL_ACTION.items():
        _BASE._require_exact_scalar(
            first[key],
            expected,
            f"{label}[0].{key}",
        )
    if first["current_hp"] != pre_battle["battle_current_hp"]:
        _BASE._fail("initial timeline HP disagrees with pre-battle snapshot")
    if first["battle_ui_hex"] != pre_battle["battle_ui_hex"]:
        _BASE._fail("initial timeline UI disagrees with pre-battle snapshot")
    if first["command_state_hex"] != pre_battle["command_state_hex"]:
        _BASE._fail(
            "initial timeline command state disagrees with pre-battle snapshot"
        )

    last = rows[-1]
    if last["current_hp"] != post_battle["battle_current_hp"]:
        _BASE._fail("terminal timeline HP disagrees with post-battle snapshot")
    if last["battle_ui_hex"] != post_battle["battle_ui_hex"]:
        _BASE._fail("terminal timeline UI disagrees with post-battle snapshot")
    if last["command_state_hex"] != post_battle["command_state_hex"]:
        _BASE._fail(
            "terminal timeline command state disagrees with post-battle snapshot"
        )

    if scenario == "attack-target-hold":
        target_state = bytes.fromhex(last["target_state_hex"])
        if target_state[0] != 1 or target_state[4] != 7:
            _BASE._fail(
                "attack-target-hold did not reach Attack target-selection state"
            )
        if last["target_list_hex"] == "00" * 12:
            _BASE._fail("attack-target-hold has an empty target list")
        if tuple(last["current_hp"]) != EXPECTED_FULL_HP:
            _BASE._fail("attack-target-hold changed combatant HP")
    return rows


TOP_LEVEL_KEYS: Final = frozenset(
    set(_V3.TOP_LEVEL_KEYS) | {"action_timeline"}
)


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    """Validate one decoded zero-only exploratory v4 trace."""

    trace = _BASE._require_object(value, label)
    _BASE._require_exact_keys(trace, TOP_LEVEL_KEYS, label)
    stripped = {
        key: field_value
        for key, field_value in trace.items()
        if key != "action_timeline"
    }
    scenario, variant = _V3.validate_trace_document(
        stripped,
        label=label,
    )
    if variant != "zero":
        _BASE._fail("battle-action probes are zero-only")
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
    """Validate one zero trace for each provisional discovery scenario."""

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
        _BASE._fail("provisional action-probe combinations mismatch")

    shared_pre: Mapping[str, Any] | None = None
    shared_battle: Mapping[str, Any] | None = None
    timeline_rows: dict[str, int] = {}
    for scenario in SCENARIO_CONTRACTS:
        trace = by_combination[(scenario, "zero")]
        normalized = _V3._without_candidate(
            trace["pre"],
            f"{scenario}.pre",
        )
        if shared_pre is None:
            shared_pre = normalized
            shared_battle = trace["pre_battle"]
        elif normalized != shared_pre or trace["pre_battle"] != shared_battle:
            _BASE._fail(
                f"{scenario} does not share the canonical checkpoint preimage"
            )
        timeline_rows[scenario] = len(trace["action_timeline"])
    return {
        "schema": SCHEMA,
        "collector_version": COLLECTOR_VERSION,
        "status": "validated-exploratory-zero-only-action-probe-set",
        "trace_count": len(traces),
        "scenarios": list(SCENARIO_CONTRACTS),
        "variants": ["zero"],
        "watched_byte_count": len(_BASE.WATCHED_ADDRESSES),
        "candidate_and_guards_any_access_forbidden": True,
        "old_compatibility_writes_forbidden": True,
        "roster_joined_epoch_writes_forbidden": True,
        "counter_callback_reconciliation": True,
        "shared_checkpoint_preimage": True,
        "timeline_rows": timeline_rows,
        "accepted_evidence": False,
    }


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActionProbeValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_trace(path: Path) -> Mapping[str, Any]:
    if path.suffix.lower() != ".json" or not path.is_file():
        raise ActionProbeValidationError(
            f"trace input must be an existing .json file: {path}"
        )
    if path.stat().st_size > MAX_TRACE_BYTES:
        raise ActionProbeValidationError(
            f"trace input exceeds {MAX_TRACE_BYTES} bytes: {path}"
        )
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except ActionProbeValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActionProbeValidationError(
            f"cannot decode trace JSON {path}: {exc}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ActionProbeValidationError(f"trace root must be an object: {path}")
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
