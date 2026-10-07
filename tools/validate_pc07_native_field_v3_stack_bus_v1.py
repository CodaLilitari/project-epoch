"""Additive bank-00 stack-bus check for the frozen native field v3 observation.

The existing v3 runner and collector remain unchanged. This read-only wrapper
pins that runner, checks every helper stack row against the selected native SP
contract, then invokes its original helper validator. Other WRAM mirrors are not
admitted by inference. This closes one host-validation alias gap; it establishes
neither arbitrary interrupt safety nor global stack ownership, and runs no CPU.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import run_mesen_pc07_field_probe_v3 as frozen

SCHEMA = "project-epoch-pc07-native-field-v3-stack-bus-v1"
FROZEN_RUNNER_SHA256 = "d06c2dcf0790e79117d17fd31552e0a4c5b449154b2c36173681641a96fa9204"
FROZEN_RUNNER_PATH = Path(__file__).resolve().parent / "run_mesen_pc07_field_probe_v3.py"


def validate_native_helper(rows):
    """Return the frozen helper receipt plus this explicit stack-bus constraint."""
    if hashlib.sha256(FROZEN_RUNNER_PATH.read_bytes()).hexdigest() != FROZEN_RUNNER_SHA256:
        raise ValueError("frozen native field v3 runner source identity changed")
    checked = 0
    for row in rows:
        if row["kind"] not in ("helper-stack-read", "helper-stack-write"):
            continue
        address, physical = row.get("address"), row.get("physical")
        if (type(address) is not int or type(physical) is not int
                or not 0 <= address < 0x2000 or physical != address):
            raise ValueError("native stack bus must be exact bank00 low WRAM with address == physical")
        checked += 1
    result = frozen.validate_native_helper(rows)
    return {**result, "stack_bus_contract": {
        "schema": SCHEMA,
        "frozen_runner_sha256": FROZEN_RUNNER_SHA256,
        "checked_stack_events": checked,
        "exact_bank00_low_wram": True,
        "physical_equals_bus": True,
        "other_mirrors_admitted": False,
        "evidence": "additive offline validation of the selected native helper windows",
        "new_native_run": False,
    }}
