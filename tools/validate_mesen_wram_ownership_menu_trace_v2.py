#!/usr/bin/env python3
"""Strict validator for the derived Mesen menu-ownership trace v2 set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any, Final, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
BASE_VALIDATOR = ROOT / "tools" / "validate_mesen_wram_ownership_trace.py"
BASE_VALIDATOR_SHA256: Final = (
    "89a7dc86c6b5b10dc984b778451152e4"
    "734b5c553a669b7ee033e465ca87f2ba"
)
SCHEMA: Final = "project-epoch-mesen-wram-ownership-menu-trace-v2"
COLLECTOR_VERSION: Final = 2
SCENARIO_NAMES: Final = (
    "equipment-owner-switch",
    "tech-owner-switch",
    "item-list-cancel",
    "party-page-cancel",
)
VARIANTS: Final = frozenset({"zero", "canary"})


def _load_exact_base() -> types.ModuleType:
    source = BASE_VALIDATOR.read_bytes()
    actual = hashlib.sha256(source).hexdigest()
    if actual != BASE_VALIDATOR_SHA256:
        raise RuntimeError(
            "accepted v1 ownership validator drifted: "
            f"expected {BASE_VALIDATOR_SHA256}, got {actual}"
        )
    code = compile(source, str(BASE_VALIDATOR), "exec", dont_inherit=True)
    name = "_project_epoch_wram_ownership_validator_v1_for_menu_v2"
    module = types.ModuleType(name)
    module.__file__ = str(BASE_VALIDATOR)
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


def _pulse(
    button: str,
    start: int,
    end: int | None = None,
) -> dict[str, Any]:
    return {
        "port": 1,
        "button": button,
        "start_frame": start,
        "end_frame": start + 1 if end is None else end,
    }


SCENARIO_CONTRACTS: Final = {
    "equipment-owner-switch": {
        "terminal_frame_min": 600,
        "terminal_frame_max": 600,
        "expected_access_class": "ownership-negative-control",
        "inputs": (
            _pulse("X", 60),
            _pulse("A", 180),
            _pulse("DOWN", 300, 303),
            _pulse("B", 420),
        ),
    },
    "tech-owner-switch": {
        "terminal_frame_min": 600,
        "terminal_frame_max": 600,
        "expected_access_class": "ownership-negative-control",
        "inputs": (
            _pulse("X", 60),
            _pulse("RIGHT", 120, 123),
            _pulse("RIGHT", 160, 163),
            _pulse("A", 220),
            _pulse("DOWN", 300, 303),
            _pulse("B", 420),
        ),
    },
    "item-list-cancel": {
        "terminal_frame_min": 600,
        "terminal_frame_max": 600,
        "expected_access_class": "ownership-negative-control",
        "inputs": (
            _pulse("X", 60),
            _pulse("RIGHT", 120, 123),
            _pulse("A", 180),
            _pulse("B", 420),
        ),
    },
    "party-page-cancel": {
        "terminal_frame_min": 600,
        "terminal_frame_max": 600,
        "expected_access_class": "ownership-negative-control",
        "inputs": (
            _pulse("X", 60),
            _pulse("RIGHT", 120, 123),
            _pulse("RIGHT", 160, 163),
            _pulse("RIGHT", 200, 203),
            _pulse("RIGHT", 240, 243),
            _pulse("A", 300),
            _pulse("RIGHT", 380, 383),
            _pulse("B", 500),
        ),
    },
}


_BASE = _load_exact_base()
_BASE.SCHEMA = SCHEMA
_BASE.COLLECTOR_VERSION = COLLECTOR_VERSION
_BASE.SCENARIO_CONTRACTS = SCENARIO_CONTRACTS
_BASE.VARIANTS = VARIANTS
_BASE.EXPECTED_COMBINATIONS = frozenset(
    (scenario, variant)
    for scenario in SCENARIO_CONTRACTS
    for variant in VARIANTS
)

TraceValidationError = _BASE.TraceValidationError

TECH_OWNER_SWITCH_WRITES: Final = (
    (124, 221, 0x7E2857, 0x00, 0xC282E7),
    (125, 221, 0x7E2858, 0x00, 0xC282E7),
    (127, 221, 0x7E2859, 0x00, 0xC282F3),
    (129, 221, 0x7E285A, 0x00, 0xC282F3),
    (131, 221, 0x7E285B, 0x00, 0xC282F3),
)
_ORIGINAL_VALIDATE_CALLBACKS = _BASE._validate_callbacks
_ORIGINAL_RECONCILE_SNAPSHOTS = _BASE._reconcile_snapshots


def _validate_callbacks_menu_v2(
    value: Any,
    scenario: str,
    terminal_frame_max: int,
    label: str,
) -> list[Mapping[str, Any]]:
    """Permit only the observed same-value Tech-page sorting writes."""

    if scenario != "tech-owner-switch":
        return _ORIGINAL_VALIDATE_CALLBACKS(
            value,
            scenario,
            terminal_frame_max,
            label,
        )
    raw_callbacks = value if isinstance(value, list) else []
    observed_writes = tuple(
        (
            callback.get("seq"),
            callback.get("frame"),
            callback.get("address"),
            callback.get("value"),
            callback.get("pc24"),
        )
        for callback in raw_callbacks
        if isinstance(callback, Mapping)
        and callback.get("access") == "write"
        and type(callback.get("address")) is int
        and 0x7E2830 <= callback["address"] <= 0x7E287F
    )
    if observed_writes != TECH_OWNER_SWITCH_WRITES:
        _BASE._fail(
            "tech-owner-switch old-compatibility write sequence mismatch: "
            f"expected={TECH_OWNER_SWITCH_WRITES!r}, "
            f"got={observed_writes!r}"
        )

    # The accepted v1 callback validator permits old-block writes only for its
    # event positive control.  Reuse that structural path after proving the
    # exact menu sequence above, while disabling the unrelated event target.
    original_event_sequence = _BASE.EVENT11C_FROG_SEQUENCE
    try:
        _BASE.EVENT11C_FROG_SEQUENCE = ()
        return _ORIGINAL_VALIDATE_CALLBACKS(
            value,
            "event11c-frog",
            terminal_frame_max,
            label,
        )
    finally:
        _BASE.EVENT11C_FROG_SEQUENCE = original_event_sequence


def _reconcile_snapshots_menu_v2(
    pre: Mapping[str, bytes],
    callbacks: Sequence[Mapping[str, Any]],
    post: Mapping[str, bytes],
    scenario: str,
    label: str,
) -> None:
    # The v1 event reconciliation path rejects every non-target old-block
    # write whose value differs from the simulated byte.  The menu sequence
    # has no event target identities, so this proves all five are same-value.
    reconciliation_scenario = (
        "event11c-frog"
        if scenario == "tech-owner-switch"
        else scenario
    )
    _ORIGINAL_RECONCILE_SNAPSHOTS(
        pre,
        callbacks,
        post,
        reconciliation_scenario,
        label,
    )


_BASE._validate_callbacks = _validate_callbacks_menu_v2
_BASE._reconcile_snapshots = _reconcile_snapshots_menu_v2


def _old_compatibility_write_diagnostics(value: Any) -> str:
    """Summarize rejected old-block writes without weakening validation."""

    if not isinstance(value, Mapping):
        return ""
    callbacks = value.get("callbacks")
    if not isinstance(callbacks, list):
        return ""
    writes: list[str] = []
    for callback in callbacks:
        if not isinstance(callback, Mapping):
            continue
        address = callback.get("address")
        if (
            callback.get("access") != "write"
            or type(address) is not int
            or not (0x7E2830 <= address <= 0x7E287F)
        ):
            continue
        writes.append(
            "seq={seq} frame={frame} address=${address:06X} "
            "value=${value:02X} pc=${pc24:06X}".format(
                seq=callback.get("seq", -1),
                frame=callback.get("frame", -1),
                address=address,
                value=callback.get("value", -1),
                pc24=callback.get("pc24", -1),
            )
        )
        if len(writes) == 16:
            break
    return "; ".join(writes)


def validate_trace_document(
    value: Any,
    *,
    label: str = "trace",
) -> tuple[str, str]:
    try:
        return _BASE.validate_trace_document(value, label=label)
    except TraceValidationError as exc:
        if "unapproved old-compatibility write" not in str(exc):
            raise
        diagnostics = _old_compatibility_write_diagnostics(value)
        if not diagnostics:
            raise
        raise TraceValidationError(
            f"{exc}; rejected old-block writes: {diagnostics}"
        ) from exc


def validate_trace_documents(traces: Sequence[Any]) -> dict[str, Any]:
    result = _BASE.validate_trace_documents(traces)
    result["schema"] = SCHEMA
    result["collector_version"] = COLLECTOR_VERSION
    result["status"] = "valid-private-menu-ownership-trace-set-v2"
    return result


def load_trace(path: Path) -> Mapping[str, Any]:
    return _BASE.load_trace(path)


def validate_trace_files(paths: Sequence[Path]) -> dict[str, Any]:
    if len(paths) != 8:
        raise TraceValidationError("exactly eight trace paths are required")
    resolved = [path.resolve(strict=True) for path in paths]
    if len(set(resolved)) != 8:
        raise TraceValidationError("trace paths must be unique")
    return validate_trace_documents([load_trace(path) for path in resolved])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "trace",
        nargs=8,
        type=Path,
        metavar="TRACE_JSON",
        help="eight menu-v2 trace JSON files, in any order",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = validate_trace_files(args.trace)
    except (OSError, TraceValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
