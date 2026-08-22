#!/usr/bin/env python3
"""Derive a zero-only Lavos action-timeline probe from battle collector v3.

This is an exploratory source builder, not an accepted evidence contract.  It
loads the exact source-controlled v3 builder, requires the exact 41,269-byte
generated collector, and applies count-checked text transforms.  The v3
196-byte ownership watcher, callback/counter reconciliation, protected-range
rules, checkpoint preparation, and end-frame capture remain intact.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys
import types
from typing import Final


ROOT = Path(__file__).resolve().parents[1]
V3_BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_collector_v3.py"
)
V3_BUILDER_SIZE: Final = 21_160
V3_BUILDER_SHA256: Final = (
    "443d521ffa435ffddaa2b9ebdd68bc66"
    "c22b144e125fe91e9bebef38817cdf91"
)
V3_GENERATED_SIZE: Final = 41_269
V3_GENERATED_SHA256: Final = (
    "7491d1c6a8a3962884baeaf9997df465"
    "9c4a53d3f67b3c6ac69999d08f6ee68b"
)

TRACE_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-probe-trace-v4"
)
COLLECTOR_VERSION: Final = 4
MAX_FRAME: Final = 1_500


class ActionProbeBuildError(RuntimeError):
    """The exact v3 preimage or one deterministic transform drifted."""


@dataclass(frozen=True)
class Pulse:
    button: str
    json_button: str
    start_frame: int
    end_frame: int

    def __post_init__(self) -> None:
        if self.button not in {
            "a",
            "b",
            "x",
            "y",
            "l",
            "r",
            "up",
            "down",
            "left",
            "right",
            "start",
            "select",
        }:
            raise ValueError(f"unsupported SNES input: {self.button}")
        if self.json_button != self.button.upper():
            raise ValueError("JSON button label must be uppercase")
        if not (0 <= self.start_frame <= self.end_frame <= MAX_FRAME):
            raise ValueError("input pulse lies outside the probe timeline")


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
        "enemy-inflight-resolution",
        (),
        1_500,
        "exploratory-battle-action-ownership-census",
    ),
    Scenario(
        "attack-target-hold",
        (_pulse("a", 20),),
        60,
        "exploratory-battle-action-ownership-census",
    ),
    Scenario(
        "attack-action-horizon",
        (_pulse("a", 20), _pulse("a", 32)),
        1_500,
        "exploratory-battle-action-ownership-census",
    ),
)
SCENARIO_NAMES: Final = tuple(scenario.name for scenario in SCENARIOS)


def sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _load_exact_v3_builder() -> types.ModuleType:
    try:
        source = V3_BUILDER_PATH.read_bytes()
    except OSError as exc:
        raise ActionProbeBuildError(
            f"cannot read exact v3 builder: {V3_BUILDER_PATH}"
        ) from exc
    if len(source) != V3_BUILDER_SIZE:
        raise ActionProbeBuildError("v3 builder size drifted")
    actual = sha256_bytes(source)
    if actual != V3_BUILDER_SHA256:
        raise ActionProbeBuildError(
            "v3 builder SHA-256 drifted: "
            f"expected {V3_BUILDER_SHA256}, got {actual}"
        )
    code = compile(source, str(V3_BUILDER_PATH), "exec", dont_inherit=True)
    name = "_project_epoch_battle_collector_builder_v3_for_action_probe_v4"
    module = types.ModuleType(name)
    module.__file__ = str(V3_BUILDER_PATH)
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
        raise ActionProbeBuildError(
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
        raise ActionProbeBuildError(f"{label} start marker is missing")
    if source.find(start_marker, start + 1) >= 0:
        raise ActionProbeBuildError(f"{label} start marker is not unique")
    end = source.find(end_marker, start + len(start_marker))
    if end < 0:
        raise ActionProbeBuildError(f"{label} end marker is missing")
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


ACTION_CONSTANTS_LUA: Final = """\
local ACTION_TARGET_STATE_START = 0x9609
local ACTION_TARGET_STATE_END = 0x9615
local PC_COMMAND_RECORDS_START = 0x93EE
local PC_COMMAND_RECORDS_END = 0x9402
local PC_FIFO_START = 0x99D4
local PC_FIFO_END = 0x99D9
local TARGET_LIST_START = 0xA62D
local TARGET_LIST_END = 0xA638
local MENU_READY_START = 0xA6D9
local MENU_READY_END = 0xA6E0
local RESOLUTION_FLAG_0 = 0xAEC8
local ACTION_REQUEST_START = 0xAE90
local ACTION_REQUEST_END = 0xAE9B
local ACTION_TARGETS_START = 0xAECB
local ACTION_TARGETS_END = 0xAED6
local AI_STATE_START = 0xAF22
local AI_STATE_END = 0xAF24
local RESOLUTION_FLAG_1 = 0xB252
local LOGIC_BUSY_START = 0xB2B6
local LOGIC_BUSY_END = 0xB2C0
local RESOLUTION_FLAG_2 = 0xB315
local ACTION_SLOTS_START = 0xB3AC
local ACTION_SLOTS_END = 0xB3B7
local BATTLE_STATUS_CUR0 = 0x1D
local BATTLE_STATUS_CUR3 = 0x20

"""


ACTION_TIMELINE_LUA: Final = """\
local action_timeline = {}

local function selected_status_hex()
\tlocal parts = {}
\tfor _, slot in ipairs(LAVOS_SLOTS) do
\t\tlocal record = battle_record_offset(slot)
\t\ttable.insert(
\t\t\tparts,
\t\t\tvalues_hex(
\t\t\t\trange_values(
\t\t\t\t\trecord + BATTLE_STATUS_CUR0,
\t\t\t\t\trecord + BATTLE_STATUS_CUR3
\t\t\t\t)
\t\t\t)
\t\t)
\tend
\treturn table.concat(parts)
end

local function resolution_flags_hex()
\treturn string.format(
\t\t"%02x%02x%02x",
\t\tread8(RESOLUTION_FLAG_0),
\t\tread8(RESOLUTION_FLAG_1),
\t\tread8(RESOLUTION_FLAG_2)
\t)
end

local function action_signature(frame)
\treturn {
\t\tframe = frame,
\t\tcurrent_hp = battle_hp_values(BATTLE_CURRENT_HP),
\t\tstatus_hex = selected_status_hex(),
\t\ttarget_state_hex = values_hex(
\t\t\trange_values(ACTION_TARGET_STATE_START, ACTION_TARGET_STATE_END)
\t\t),
\t\ttarget_list_hex = values_hex(
\t\t\trange_values(TARGET_LIST_START, TARGET_LIST_END)
\t\t),
\t\tpc_fifo_hex = values_hex(
\t\t\trange_values(PC_FIFO_START, PC_FIFO_END)
\t\t),
\t\tmenu_ready_hex = values_hex(
\t\t\trange_values(MENU_READY_START, MENU_READY_END)
\t\t),
\t\tpc_command_records_hex = values_hex(
\t\t\trange_values(PC_COMMAND_RECORDS_START, PC_COMMAND_RECORDS_END)
\t\t),
\t\taction_request_hex = values_hex(
\t\t\trange_values(ACTION_REQUEST_START, ACTION_REQUEST_END)
\t\t),
\t\taction_targets_hex = values_hex(
\t\t\trange_values(ACTION_TARGETS_START, ACTION_TARGETS_END)
\t\t),
\t\tlogic_busy_hex = values_hex(
\t\t\trange_values(LOGIC_BUSY_START, LOGIC_BUSY_END)
\t\t),
\t\taction_slots_hex = values_hex(
\t\t\trange_values(ACTION_SLOTS_START, ACTION_SLOTS_END)
\t\t),
\t\tai_state_hex = values_hex(
\t\t\trange_values(AI_STATE_START, AI_STATE_END)
\t\t),
\t\tresolution_flags_hex = resolution_flags_hex(),
\t\tbattle_ui_hex = battle_ui_hex(),
\t\tcommand_state_hex = command_state_hex(),
\t}
end

local function action_signature_key(row)
\treturn table.concat({
\t\tnumber_array_json(row.current_hp),
\t\trow.status_hex,
\t\trow.target_state_hex,
\t\trow.target_list_hex,
\t\trow.pc_fifo_hex,
\t\trow.menu_ready_hex,
\t\trow.pc_command_records_hex,
\t\trow.action_request_hex,
\t\trow.action_targets_hex,
\t\trow.logic_busy_hex,
\t\trow.action_slots_hex,
\t\trow.ai_state_hex,
\t\trow.resolution_flags_hex,
\t\trow.battle_ui_hex,
\t\trow.command_state_hex,
\t}, "|")
end

local function action_signature_json(row)
\treturn table.concat({
\t\t"{",
\t\t'"frame":', tostring(row.frame), ",",
\t\t'"current_hp":', number_array_json(row.current_hp), ",",
\t\t'"status_hex":', json_string(row.status_hex), ",",
\t\t'"target_state_hex":', json_string(row.target_state_hex), ",",
\t\t'"target_list_hex":', json_string(row.target_list_hex), ",",
\t\t'"pc_fifo_hex":', json_string(row.pc_fifo_hex), ",",
\t\t'"menu_ready_hex":', json_string(row.menu_ready_hex), ",",
\t\t'"pc_command_records_hex":',
\t\tjson_string(row.pc_command_records_hex), ",",
\t\t'"action_request_hex":', json_string(row.action_request_hex), ",",
\t\t'"action_targets_hex":', json_string(row.action_targets_hex), ",",
\t\t'"logic_busy_hex":', json_string(row.logic_busy_hex), ",",
\t\t'"action_slots_hex":', json_string(row.action_slots_hex), ",",
\t\t'"ai_state_hex":', json_string(row.ai_state_hex), ",",
\t\t'"resolution_flags_hex":',
\t\tjson_string(row.resolution_flags_hex), ",",
\t\t'"battle_ui_hex":', json_string(row.battle_ui_hex), ",",
\t\t'"command_state_hex":', json_string(row.command_state_hex),
\t\t"}",
\t})
end

local function record_action_signature(frame)
\tlocal row = action_signature(frame)
\tlocal prior = action_timeline[#action_timeline]
\tif prior == nil or action_signature_key(prior) ~= action_signature_key(row) then
\t\ttable.insert(action_timeline, row)
\tend
end

local function action_timeline_json()
\tlocal rows = {}
\tfor _, row in ipairs(action_timeline) do
\t\ttable.insert(rows, action_signature_json(row))
\tend
\treturn "[" .. table.concat(rows, ",") .. "]"
end

"""


ROUTE_ENDPOINT_LUA: Final = """\
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
end

local function route_endpoint_matches(route)
\tif scenario_name == "attack-target-hold" then
\t\tif not base_battle_anchor_matches(route) then
\t\t\treturn false
\t\tend
\t\tlocal row = action_timeline[#action_timeline]
\t\treturn row ~= nil
\t\t\tand row.target_state_hex:sub(1, 2) == "01"
\t\t\tand row.target_state_hex:sub(9, 10) == "07"
\t\t\tand row.target_list_hex ~= "000000000000000000000000"
\tend
\treturn persistent_battle_anchor_matches(route)
end

"""


def build_collector() -> bytes:
    """Return deterministic exploratory battle-action collector bytes."""

    v3 = _load_exact_v3_builder()
    base = v3.build_collector()
    if len(base) != V3_GENERATED_SIZE:
        raise ActionProbeBuildError("generated v3 collector size drifted")
    actual = sha256_bytes(base)
    if actual != V3_GENERATED_SHA256:
        raise ActionProbeBuildError(
            "generated v3 collector SHA-256 drifted: "
            f"expected {V3_GENERATED_SHA256}, got {actual}"
        )
    try:
        source = base.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ActionProbeBuildError(
            "generated v3 collector is not UTF-8"
        ) from exc

    source = _replace_once(
        source,
        "local EXPECTED_TECH_COMMAND_STATE = "
        '"0001000000ffff000100000000"\n\n',
        "local EXPECTED_TECH_COMMAND_STATE = "
        '"0001000000ffff000100000000"\n\n'
        + ACTION_CONSTANTS_LUA,
        "action constants",
    )
    source = _replace_region(
        source,
        "local SCENARIOS = {",
        "local state_path =",
        _scenario_lua(),
        "scenario tables",
    )
    source = _replace_once(
        source,
        'assert(variant == "zero" or variant == "canary", '
        '"unknown PE_VARIANT")',
        'assert(variant == "zero", "battle-action probe is zero-only")',
        "zero-only variant",
    )
    source = _replace_once(
        source,
        "local function route_has_full_hp(route)",
        ACTION_TIMELINE_LUA + "local function route_has_full_hp(route)",
        "action timeline functions",
    )
    source = _replace_once(
        source,
        "\tpre_ranges = capture_ranges()\n"
        "\tpre_route = route_snapshot()\n"
        "\tprepared = true\n",
        "\tpre_ranges = capture_ranges()\n"
        "\tpre_route = route_snapshot()\n"
        "\taction_timeline = {}\n"
        "\trecord_action_signature(0)\n"
        "\tprepared = true\n",
        "initial action signature",
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
        "local function route_endpoint_matches(route)",
        "local function emit_trace(",
        ROUTE_ENDPOINT_LUA,
        "route endpoint",
    )
    source = _replace_once(
        source,
        '\t\t\'"pre_battle":\', route_json(pre_route), ",",\n'
        '\t\t\'"pre":\', snapshot_json(pre_ranges), ",",\n',
        '\t\t\'"pre_battle":\', route_json(pre_route), ",",\n'
        '\t\t\'"action_timeline":\', action_timeline_json(), ",",\n'
        '\t\t\'"pre":\', snapshot_json(pre_ranges), ",",\n',
        "action timeline trace field",
    )
    source = _replace_once(
        source,
        "\tfunction()\n"
        "\t\tif pending_fixed_terminal then\n",
        "\tfunction()\n"
        "\t\tif prepared and tracing then\n"
        "\t\t\trecord_action_signature(relative_frame)\n"
        "\t\tend\n"
        "\t\tif pending_fixed_terminal then\n",
        "end-frame action signature",
    )
    source = _replace_once(
        source,
        '"schema":"project-epoch-mesen-wram-ownership-battle-trace-v3"',
        f'"schema":"{TRACE_SCHEMA}"',
        "trace schema",
    )
    source = _replace_once(
        source,
        '"collector_version":3',
        f'"collector_version":{COLLECTOR_VERSION}',
        "collector version",
    )
    return source.encode("utf-8")


def main() -> int:
    source = build_collector()
    print(
        f"size={len(source)} sha256={sha256_bytes(source)} "
        f"scenarios={','.join(SCENARIO_NAMES)} variants=zero"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
