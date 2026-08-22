#!/usr/bin/env python3
"""Derive the bounded Lavos action/recovery collector from probe v4.

The exploratory probe builder and its generated collector are exact ancestry
preimages.  This builder changes only the scenario table, zero/canary gate,
trace schema, access-class table, and exact causal endpoint predicates.  The
196-byte watcher, action timeline, preparation, callback/counter
reconciliation, preservation rules, and end-frame capture remain inherited.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys
import types
from typing import Final


ROOT = Path(__file__).resolve().parents[1]
PROBE_BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_action_probe_v4.py"
)
PROBE_BUILDER_SIZE: Final = 16_877
PROBE_BUILDER_SHA256: Final = (
    "d50ebfe12ec81c318b61aa189a30ca04"
    "eeadba181c1d43a3300e58b26f50ca6e"
)
PROBE_GENERATED_SIZE: Final = 46_650
PROBE_GENERATED_SHA256: Final = (
    "8957872bb9a32931be6a8e1f56d0a953"
    "a605659e30b6d77d2d1ec14de52a1e65"
)
TRACE_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-trace-v4"
)
COLLECTOR_VERSION: Final = 4


class BattleActionBuildError(RuntimeError):
    """The exact probe preimage or a deterministic transform drifted."""


@dataclass(frozen=True)
class Pulse:
    button: str
    json_button: str
    start_frame: int
    end_frame: int


@dataclass(frozen=True)
class Scenario:
    name: str
    pulses: tuple[Pulse, ...]
    terminal_frame: int
    expected_access_class: str


def _pulse(button: str, start: int, width: int = 4) -> Pulse:
    return Pulse(button, button.upper(), start, start + width - 1)


SCENARIOS: Final = (
    Scenario(
        "battle-action-control",
        (),
        606,
        "battle-action-ownership-census",
    ),
    Scenario(
        "battle-attack-target-hold",
        (_pulse("a", 20),),
        60,
        "battle-action-ownership-census",
    ),
    Scenario(
        "battle-attack-recovery",
        (_pulse("a", 20), _pulse("a", 32)),
        606,
        "battle-action-ownership-census",
    ),
)
SCENARIO_NAMES: Final = tuple(scenario.name for scenario in SCENARIOS)


def sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _load_exact_probe_builder() -> types.ModuleType:
    try:
        source = PROBE_BUILDER_PATH.read_bytes()
    except OSError as exc:
        raise BattleActionBuildError(
            f"cannot read exact action-probe builder: {PROBE_BUILDER_PATH}"
        ) from exc
    if len(source) != PROBE_BUILDER_SIZE:
        raise BattleActionBuildError("action-probe builder size drifted")
    actual = sha256_bytes(source)
    if actual != PROBE_BUILDER_SHA256:
        raise BattleActionBuildError(
            "action-probe builder SHA-256 drifted: "
            f"expected {PROBE_BUILDER_SHA256}, got {actual}"
        )
    code = compile(source, str(PROBE_BUILDER_PATH), "exec", dont_inherit=True)
    name = "_project_epoch_battle_action_probe_builder_for_v4"
    module = types.ModuleType(name)
    module.__file__ = str(PROBE_BUILDER_PATH)
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


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise BattleActionBuildError(
            f"{label} preimage must occur exactly once, found {count}"
        )
    return source.replace(old, new, 1)


def _replace_region(
    source: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = source.find(start_marker)
    if start < 0:
        raise BattleActionBuildError(f"{label} start marker is missing")
    if source.find(start_marker, start + 1) >= 0:
        raise BattleActionBuildError(f"{label} start marker is not unique")
    end = source.find(end_marker, start + len(start_marker))
    if end < 0:
        raise BattleActionBuildError(f"{label} end marker is missing")
    return source[:start] + replacement + source[end:]


def _scenario_lua() -> str:
    lines = ["local SCENARIOS = {"]
    for scenario in SCENARIOS:
        lines.extend(
            [
                f'\t["{scenario.name}"] = {{',
                f"\t\tterminal_frame = {scenario.terminal_frame},",
                f"\t\tminimum_terminal_frame = {scenario.terminal_frame},",
                f"\t\tmaximum_frame = {scenario.terminal_frame},",
                "\t\tphase_stable = false,",
                "\t},",
            ]
        )
    lines.extend(["}", "", "local INPUT_TIMELINES = {"])
    for scenario in SCENARIOS:
        lines.append(f'\t["{scenario.name}"] = {{')
        for pulse in scenario.pulses:
            lines.append(
                "\t\t{ "
                f'button = "{pulse.button}", '
                f'json_button = "{pulse.json_button}", '
                f"first = {pulse.start_frame}, "
                f"last = {pulse.end_frame} "
                "},"
            )
        lines.append("\t},")
    lines.extend(["}", ""])
    return "\n".join(lines)


def _scenario_contract_lua() -> str:
    classes = "\n".join(
        f'\t["{scenario.name}"] = "{scenario.expected_access_class}",'
        for scenario in SCENARIOS
    )
    return f"""\
local EXPECTED_ACCESS_CLASSES = {{
{classes}
}}

local function scenario_contract_json()
\tlocal pulses = {{}}
\tfor _, scheduled in ipairs(INPUT_TIMELINES[scenario_name]) do
\t\ttable.insert(pulses, table.concat({{
\t\t\t'{{"port":1,"button":',
\t\t\tjson_string(scheduled.json_button),
\t\t\t',"start_frame":',
\t\t\ttostring(scheduled.first),
\t\t\t',"end_frame":',
\t\t\ttostring(scheduled.last),
\t\t\t"}}",
\t\t}}))
\tend
\treturn table.concat({{
\t\t"{{",
\t\t'"terminal_frame_min":',
\t\ttostring(scenario.minimum_terminal_frame), ",",
\t\t'"terminal_frame_max":', tostring(scenario.maximum_frame), ",",
\t\t'"expected_access_class":',
\t\tjson_string(EXPECTED_ACCESS_CLASSES[scenario_name]), ",",
\t\t'"inputs":[', table.concat(pulses, ","), "]",
\t\t"}}",
\t}})
end

"""


ENDPOINT_LUA: Final = """\
local function route_has_expected_max_hp(route)
\tfor index, expected in ipairs(EXPECTED_FULL_HP) do
\t\tif route.battle_max_hp[index] ~= expected then
\t\t\treturn false
\t\tend
\tend
\treturn true
end

local function persistent_battle_anchor_matches(route)
\treturn route.location == 0x01DB
\t\tand route.storyline == 0xD6
\t\tand route.pending_request == 0x01
\t\tand route.explore_mode == 0
\t\tand route.dialog_state == 0
\t\tand route.active_party_hex == "000102"
\t\tand route.roster_hex == "000102828004030605"
\t\tand route.joined == EXPECTED_JOINED
\t\tand route.battle_ids_hex == EXPECTED_BATTLE_IDS
\t\tand route_has_expected_max_hp(route)
\t\tand route.command_ready
end

local EXPECTED_ACTION_ENDPOINTS = {
\t["battle-action-control"] = {
\t\trow_count = 269,
\t\tlast_frame = 603,
\t\tcurrent_hp = { 739, 821, 712, 8000, 12000, 20000 },
\t\tstatus_hex = "000000000000000000000000000000000000000000000000",
\t\ttarget_state_hex = "00000000000000000000000000",
\t\ttarget_list_hex = "000000000000000000000000",
\t\tpc_fifo_hex = "ffffffff0003",
\t\tmenu_ready_hex = "000102ff00030002",
\t\tpc_command_records_hex =
\t\t\t"8100000000ff008100000000ff008100000000ff00",
\t\taction_request_hex = "00060273000020ffff000000",
\t\taction_targets_hex = "0102ffffffffffffffffffff",
\t\tlogic_busy_hex = "0100000100000001040000",
\t\taction_slots_hex = "ffffffffffffffffffffff03",
\t\tai_state_hex = "000000",
\t\tresolution_flags_hex = "030308",
\t\tbattle_ui_hex = "03bf59",
\t\tcommand_state_hex = "00000000000102000300000000",
\t},
\t["battle-attack-target-hold"] = {
\t\trow_count = 17,
\t\tlast_frame = 60,
\t\tcurrent_hp = { 969, 898, 909, 8000, 12000, 20000 },
\t\tstatus_hex = "000000000000000000000000000000000000000000000000",
\t\ttarget_state_hex = "01010000070000000000000000",
\t\ttarget_list_hex = "03ffffffffffffffffffffff",
\t\tpc_fifo_hex = "ffffffff0003",
\t\tmenu_ready_hex = "00ffffff00010001",
\t\tpc_command_records_hex =
\t\t\t"8100000000ff000000000000ff000000000000ff00",
\t\taction_request_hex = "0003024300008006ff006000",
\t\taction_targets_hex = "03000102ffffffffffffffff",
\t\tlogic_busy_hex = "01000000000000010b0001",
\t\taction_slots_hex = "03ffffffffffffffffffff06",
\t\tai_state_hex = "000000",
\t\tresolution_flags_hex = "000000",
\t\tbattle_ui_hex = "0059ac",
\t\tcommand_state_hex = "0000000000ffff000100000000",
\t},
\t["battle-attack-recovery"] = {
\t\trow_count = 206,
\t\tlast_frame = 606,
\t\tcurrent_hp = { 739, 821, 712, 7038, 12000, 20000 },
\t\tstatus_hex = "000000000000000000000000000000000000000000000000",
\t\ttarget_state_hex = "00010000070000000000000000",
\t\ttarget_list_hex = "03ffffffffffffffffffffff",
\t\tpc_fifo_hex = "ffffffff0003",
\t\tmenu_ready_hex = "ff01ffff01010102",
\t\tpc_command_records_hex =
\t\t\t"0000000000ff008100000000ff000000000000ff00",
\t\taction_request_hex = "00000100000000ffff000000",
\t\taction_targets_hex = "01ffffffffffffffffffffff",
\t\tlogic_busy_hex = "0100000100000001040000",
\t\taction_slots_hex = "ffffffffffffffffffffff00",
\t\tai_state_hex = "000000",
\t\tresolution_flags_hex = "000808",
\t\tbattle_ui_hex = "003a00",
\t\tcommand_state_hex = "01000000ff01ff010100000000",
\t},
}

local function number_arrays_equal(actual, expected)
\tif #actual ~= #expected then
\t\treturn false
\tend
\tfor index, value in ipairs(expected) do
\t\tif actual[index] ~= value then
\t\t\treturn false
\t\tend
\tend
\treturn true
end

local function action_row_matches(row, expected)
\treturn row.frame == expected.last_frame
\t\tand number_arrays_equal(row.current_hp, expected.current_hp)
\t\tand row.status_hex == expected.status_hex
\t\tand row.target_state_hex == expected.target_state_hex
\t\tand row.target_list_hex == expected.target_list_hex
\t\tand row.pc_fifo_hex == expected.pc_fifo_hex
\t\tand row.menu_ready_hex == expected.menu_ready_hex
\t\tand row.pc_command_records_hex == expected.pc_command_records_hex
\t\tand row.action_request_hex == expected.action_request_hex
\t\tand row.action_targets_hex == expected.action_targets_hex
\t\tand row.logic_busy_hex == expected.logic_busy_hex
\t\tand row.action_slots_hex == expected.action_slots_hex
\t\tand row.ai_state_hex == expected.ai_state_hex
\t\tand row.resolution_flags_hex == expected.resolution_flags_hex
\t\tand row.battle_ui_hex == expected.battle_ui_hex
\t\tand row.command_state_hex == expected.command_state_hex
end

local function timeline_has_hp(frame, expected_hp)
\tfor _, row in ipairs(action_timeline) do
\t\tif row.frame == frame
\t\t\tand number_arrays_equal(row.current_hp, expected_hp)
\t\tthen
\t\t\treturn true
\t\tend
\tend
\treturn false
end

local function timeline_has_field(frame, field, expected_value)
\tfor _, row in ipairs(action_timeline) do
\t\tif row.frame == frame and row[field] == expected_value then
\t\t\treturn true
\t\tend
\tend
\treturn false
end

local function causal_milestones_match()
\tif scenario_name == "battle-action-control" then
\t\treturn timeline_has_hp(336, { 739, 821, 712, 8000, 12000, 20000 })
\t\t\tand timeline_has_field(
\t\t\t\t363,
\t\t\t\t"action_request_hex",
\t\t\t\t"00030200000000ffff000000"
\t\t\t)
\telseif scenario_name == "battle-attack-target-hold" then
\t\treturn timeline_has_field(
\t\t\t20,
\t\t\t"target_state_hex",
\t\t\t"01010000070000000000000000"
\t\t)
\telseif scenario_name == "battle-attack-recovery" then
\t\treturn timeline_has_field(32, "pc_fifo_hex", "00ffffff0103")
\t\t\tand timeline_has_field(373, "pc_fifo_hex", "ffffffff0003")
\t\t\tand timeline_has_field(
\t\t\t\t375,
\t\t\t\t"action_request_hex",
\t\t\t\t"00000100000010ffff000080"
\t\t\t)
\t\t\tand timeline_has_hp(
\t\t\t\t337,
\t\t\t\t{ 739, 821, 712, 8000, 12000, 20000 }
\t\t\t)
\t\t\tand timeline_has_hp(
\t\t\t\t557,
\t\t\t\t{ 739, 821, 712, 7038, 12000, 20000 }
\t\t\t)
\tend
\treturn false
end

local function route_endpoint_matches(route)
\tif not persistent_battle_anchor_matches(route) then
\t\treturn false
\tend
\tlocal expected = EXPECTED_ACTION_ENDPOINTS[scenario_name]
\tlocal row = action_timeline[#action_timeline]
\treturn expected ~= nil
\t\tand #action_timeline == expected.row_count
\t\tand row ~= nil
\t\tand action_row_matches(row, expected)
\t\tand number_arrays_equal(route.battle_current_hp, expected.current_hp)
\t\tand route.battle_ui_hex == expected.battle_ui_hex
\t\tand route.command_state_hex == expected.command_state_hex
\t\tand causal_milestones_match()
end

"""


def build_collector() -> bytes:
    """Return deterministic accepted-candidate battle-action collector bytes."""

    probe = _load_exact_probe_builder()
    base = probe.build_collector()
    if len(base) != PROBE_GENERATED_SIZE:
        raise BattleActionBuildError("generated action-probe size drifted")
    actual = sha256_bytes(base)
    if actual != PROBE_GENERATED_SHA256:
        raise BattleActionBuildError(
            "generated action-probe SHA-256 drifted: "
            f"expected {PROBE_GENERATED_SHA256}, got {actual}"
        )
    source = base.decode("utf-8")
    source = _replace_region(
        source,
        "local SCENARIOS = {",
        "local state_path =",
        _scenario_lua(),
        "scenario tables",
    )
    source = _replace_once(
        source,
        'assert(variant == "zero", "battle-action probe is zero-only")',
        'assert(variant == "zero" or variant == "canary", '
        '"unknown PE_VARIANT")',
        "zero/canary variants",
    )
    source = _replace_region(
        source,
        "local EXPECTED_ACCESS_CLASSES = {",
        "local function event_control_matches()",
        _scenario_contract_lua(),
        "scenario contract",
    )
    source = _replace_region(
        source,
        "local function route_has_expected_max_hp(route)",
        "local function emit_trace(",
        ENDPOINT_LUA,
        "exact action endpoints",
    )
    source = _replace_once(
        source,
        (
            '"schema":"project-epoch-mesen-wram-ownership-'
            'battle-action-probe-trace-v4"'
        ),
        f'"schema":"{TRACE_SCHEMA}"',
        "accepted trace schema",
    )
    return source.encode("utf-8")


def main() -> int:
    source = build_collector()
    print(
        f"size={len(source)} sha256={sha256_bytes(source)} "
        f"scenarios={','.join(SCENARIO_NAMES)} variants=zero,canary"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
