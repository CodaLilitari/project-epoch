#!/usr/bin/env python3
"""Derive a bounded Lavos-battle ownership collector from accepted v1 source.

The accepted v1 Lua collector remains byte-for-byte immutable.  This builder
requires that exact source preimage and deterministically replaces only the
checkpoint identity, battle snapshots/anchors, scenario table, input schedule,
preservation rule, trace schema, and collector version.  The generated Lua is
staged beneath ignored ``private/`` storage by the battle-v3 launcher.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Final


ROOT = Path(__file__).resolve().parents[1]
BASE_COLLECTOR = ROOT / "tools" / "mesen_wram_ownership_trace.lua"
BASE_COLLECTOR_SIZE: Final = 40_088
BASE_COLLECTOR_SHA256: Final = (
    "d5dd2b2d7085237844d95ab04f7007b6"
    "b2d17b2e1160f23857018319380b7569"
)
TRACE_SCHEMA: Final = "project-epoch-mesen-wram-ownership-battle-trace-v3"
COLLECTOR_VERSION: Final = 3
CHECKPOINT_ID: Final = "lavos-core-command-ready-canonical-v1"
CHECKPOINT_SIZE: Final = 261_614
CHECKPOINT_SHA256: Final = (
    "d5825ffff2f2a3b7edbe3c37e711815"
    "5d67727dc02ed672d13257f3824482b8b"
)
CHECKPOINT_SOURCE_FRAME: Final = 5_651
CALLBACK_LIMIT: Final = 16_384


class CollectorBuildError(RuntimeError):
    """Raised when an accepted preimage or deterministic transform drifts."""


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
        if not (0 <= self.start_frame <= self.end_frame <= 60):
            raise ValueError("input pulse lies outside the bounded timeline")


@dataclass(frozen=True)
class Scenario:
    name: str
    pulses: tuple[Pulse, ...]
    terminal_frame: int
    expected_access_class: str


def _pulse(button: str, start: int, width: int = 4) -> Pulse:
    return Pulse(button, button.upper(), start, start + width - 1)


SCENARIOS: Final = (
    Scenario("calibration", (), 0, "none"),
    Scenario("battle-idle", (), 60, "battle-ownership-census"),
    Scenario(
        "battle-command-roundtrip",
        (_pulse("down", 20), _pulse("up", 32)),
        60,
        "battle-ownership-census",
    ),
    Scenario(
        "battle-command-down",
        (_pulse("down", 20),),
        60,
        "battle-ownership-census",
    ),
)
SCENARIO_NAMES: Final = tuple(scenario.name for scenario in SCENARIOS)


def sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise CollectorBuildError(
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
        raise CollectorBuildError(f"{label} start marker is missing")
    end = source.find(end_marker, start + len(start_marker))
    if end < 0:
        raise CollectorBuildError(f"{label} end marker is missing")
    if source.find(start_marker, start + 1) >= 0:
        raise CollectorBuildError(f"{label} start marker is not unique")
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


BATTLE_CONSTANTS_LUA: Final = """\
local PENDING_REQUEST = 0x0117
local BATTLE_UI_STATE_0 = 0x06E2
local BATTLE_UI_STATE_1 = 0x06E6
local BATTLE_UI_STATE_2 = 0x06E7
local ACTIVE_MENU_SLOT = 0x95D5
local COMMAND_CURSOR_ROWS = 0x95DC
local MENU_READY_BATTLERS = 0xA6D9
local ACTIVE_READY_PC = 0xA6DD
local PC_LOCK_STATUS = 0xA0D1
local COMMAND_REDRAW = 0xA43F
local BATTLE_RECORD_BASE = 0x5E2D
local BATTLE_RECORD_STRIDE = 0x80
local BATTLE_CURRENT_HP = 0x03
local BATTLE_MAX_HP = 0x05
local EXPECTED_ACTIVE = { 0x00, 0x01, 0x02 }
local EXPECTED_ROSTER = {
\t0x00, 0x01, 0x02, 0x82, 0x80, 0x04, 0x03, 0x06, 0x05,
}
local EXPECTED_JOINED = 0xFE
local EXPECTED_BATTLE_IDS = "000102cdffffccffffffcb00"
local EXPECTED_FULL_HP = { 969, 898, 909, 8000, 12000, 20000 }
local LAVOS_SLOTS = { 0, 1, 2, 3, 6, 10 }
local EXPECTED_ATTACK_COMMAND_STATE = "0000000000ffff000100000000"
local EXPECTED_TECH_COMMAND_STATE = "0001000000ffff000100000000"

"""


BATTLE_SNAPSHOT_LUA: Final = """\
local function battle_record_offset(slot)
\treturn BATTLE_RECORD_BASE + slot * BATTLE_RECORD_STRIDE
end

local function number_array_json(values)
\tlocal parts = {}
\tfor _, value in ipairs(values) do
\t\ttable.insert(parts, tostring(value))
\tend
\treturn "[" .. table.concat(parts, ",") .. "]"
end

local function battle_ids_hex()
\tlocal parts = {}
\tfor slot = 0, 11 do
\t\ttable.insert(
\t\t\tparts,
\t\t\tstring.format("%02x", read8(battle_record_offset(slot)))
\t\t)
\tend
\treturn table.concat(parts)
end

local function battle_hp_values(field_offset)
\tlocal values = {}
\tfor _, slot in ipairs(LAVOS_SLOTS) do
\t\ttable.insert(
\t\t\tvalues,
\t\t\tread16(battle_record_offset(slot) + field_offset)
\t\t)
\tend
\treturn values
end

local function battle_ui_hex()
\treturn string.format(
\t\t"%02x%02x%02x",
\t\tread8(BATTLE_UI_STATE_0),
\t\tread8(BATTLE_UI_STATE_1),
\t\tread8(BATTLE_UI_STATE_2)
\t)
end

local function command_state_hex()
\treturn table.concat({
\t\tvalues_hex(range_values(ACTIVE_MENU_SLOT, ACTIVE_MENU_SLOT)),
\t\tvalues_hex(range_values(COMMAND_CURSOR_ROWS, COMMAND_CURSOR_ROWS + 2)),
\t\tvalues_hex(range_values(MENU_READY_BATTLERS, MENU_READY_BATTLERS + 2)),
\t\tvalues_hex(range_values(ACTIVE_READY_PC, ACTIVE_READY_PC + 1)),
\t\tvalues_hex(range_values(PC_LOCK_STATUS, PC_LOCK_STATUS + 2)),
\t\tvalues_hex(range_values(COMMAND_REDRAW, COMMAND_REDRAW)),
\t})
end

local function command_ready()
\tlocal active_pc = read8(ACTIVE_READY_PC)
\tif active_pc > 2 then
\t\treturn false
\tend
\tlocal battler = read8(MENU_READY_BATTLERS + active_pc)
\tif battler >= 0x80 or read8(PC_LOCK_STATUS + battler) ~= 0 then
\t\treturn false
\tend
\tlocal menu_slot = read8(ACTIVE_MENU_SLOT)
\tif menu_slot > 2 then
\t\treturn false
\tend
\treturn read8(COMMAND_CURSOR_ROWS + menu_slot) <= 2
end

local function route_snapshot()
\treturn {
\t\tlocation = read16(LOCATION),
\t\tstoryline = read8(STORYLINE),
\t\tpending_request = read8(PENDING_REQUEST),
\t\texplore_mode = read8(EXPLORE_MODE),
\t\tdialog_state = read8(DIALOG_STATE),
\t\tactive_party_hex = values_hex(
\t\t\trange_values(ACTIVE_PARTY_START, ACTIVE_PARTY_START + 2)
\t\t),
\t\troster_hex = values_hex(
\t\t\trange_values(ACTIVE_PARTY_START, ACTIVE_PARTY_END)
\t\t),
\t\tjoined = read8(JOINED_FLAGS),
\t\tbattle_ids_hex = battle_ids_hex(),
\t\tbattle_current_hp = battle_hp_values(BATTLE_CURRENT_HP),
\t\tbattle_max_hp = battle_hp_values(BATTLE_MAX_HP),
\t\tbattle_ui_hex = battle_ui_hex(),
\t\tcommand_state_hex = command_state_hex(),
\t\tcommand_ready = command_ready(),
\t}
end

local function route_json(route)
\treturn table.concat({
\t\t"{",
\t\t'"location":', tostring(route.location), ",",
\t\t'"storyline":', tostring(route.storyline), ",",
\t\t'"pending_request":', tostring(route.pending_request), ",",
\t\t'"explore_mode":', tostring(route.explore_mode), ",",
\t\t'"dialog_state":', tostring(route.dialog_state), ",",
\t\t'"active_party_hex":', json_string(route.active_party_hex), ",",
\t\t'"roster_hex":', json_string(route.roster_hex), ",",
\t\t'"joined":', tostring(route.joined), ",",
\t\t'"battle_ids_hex":', json_string(route.battle_ids_hex), ",",
\t\t'"battle_current_hp":', number_array_json(route.battle_current_hp), ",",
\t\t'"battle_max_hp":', number_array_json(route.battle_max_hp), ",",
\t\t'"battle_ui_hex":', json_string(route.battle_ui_hex), ",",
\t\t'"command_state_hex":', json_string(route.command_state_hex), ",",
\t\t'"command_ready":', bool_json(route.command_ready),
\t\t"}",
\t})
end

"""


PREPARE_FIXTURE_LUA: Final = """\
local function route_has_full_hp(route)
\tfor index, expected in ipairs(EXPECTED_FULL_HP) do
\t\tif route.battle_current_hp[index] ~= expected
\t\t\tor route.battle_max_hp[index] ~= expected
\t\tthen
\t\t\treturn false
\t\tend
\tend
\treturn true
end

local function base_battle_anchor_matches(route)
\treturn route.location == 0x01DB
\t\tand route.storyline == 0xD6
\t\tand route.pending_request == 0x01
\t\tand route.explore_mode == 0
\t\tand route.dialog_state == 0
\t\tand route.active_party_hex == "000102"
\t\tand route.roster_hex == "000102828004030605"
\t\tand route.joined == EXPECTED_JOINED
\t\tand route.battle_ids_hex == EXPECTED_BATTLE_IDS
\t\tand route_has_full_hp(route)
\t\tand route.command_ready
end

local function prepare_fixture()
\tassert(post_load_exec_seen, "savestate did not resume through the exec hook")
\tassert(checkpoint_cpu ~= nil, "checkpoint CPU state was not captured")
\tassert(
\t\tcheckpoint_cpu.d == 0x0000,
\t\tstring.format(
\t\t\t"checkpoint direct-page preimage mismatch: got %04X",
\t\t\tcheckpoint_cpu.d
\t\t)
\t)
\tlocal route = route_snapshot()
\tassert(base_battle_anchor_matches(route), "checkpoint battle anchor mismatch")
\tassert(
\t\troute.command_state_hex == EXPECTED_ATTACK_COMMAND_STATE,
\t\t"checkpoint command-state preimage mismatch"
\t)
\tassert(
\t\trange_is_zero(FRONT_GUARD_START, REAR_GUARD_END),
\t\t"checkpoint candidate or guards are not zero"
\t)
\tassert(
\t\trange_matches(EPOCH_NAME_START, EXPECTED_EPOCH_NAME),
\t\t"checkpoint Epoch name mismatch"
\t)

\tif variant == "canary" then
\t\tfor index, value in ipairs(CANARY) do
\t\t\twram_write8(
\t\t\t\tCANDIDATE_START + index - 1,
\t\t\t\tvalue,
\t\t\t\t"candidate-variant"
\t\t\t)
\t\tend
\tend

\tassert(
\t\tvariant == "canary"
\t\t\tand range_matches(CANDIDATE_START, CANARY)
\t\t\tor variant == "zero"
\t\t\t\tand range_is_zero(CANDIDATE_START, CANDIDATE_END),
\t\t"candidate variant preparation mismatch"
\t)
\tassert(
\t\trange_is_zero(FRONT_GUARD_START, FRONT_GUARD_END),
\t\t"front guard changed during preparation"
\t)
\tassert(
\t\trange_is_zero(REAR_GUARD_START, REAR_GUARD_END),
\t\t"rear guard changed during preparation"
\t)
\tassert(
\t\trange_matches(EPOCH_NAME_START, EXPECTED_EPOCH_NAME),
\t\t"Epoch name changed during preparation"
\t)

\tpre_ranges = capture_ranges()
\tpre_route = route_snapshot()
\tprepared = true
end

"""


def _scenario_contract_lua() -> str:
    access_classes = {
        scenario.name: scenario.expected_access_class for scenario in SCENARIOS
    }
    lua_classes = "\n".join(
        f'\t["{name}"] = "{value}",' for name, value in access_classes.items()
    )
    return f"""\
local EXPECTED_ACCESS_CLASSES = {{
{lua_classes}
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


EVENT_CONTROL_LUA: Final = """\
local function event_control_matches()
\treturn true
end

"""


PRESERVATION_LUA: Final = """\
local function preservation_matches(post_ranges)
\tfor _, name in ipairs({
\t\t"old-compatibility",
\t\t"roster",
\t\t"joined",
\t\t"epoch-name",
\t\t"front-guard",
\t\t"candidate",
\t\t"rear-guard",
\t}) do
\t\tif not range_unchanged(pre_ranges[name], post_ranges[name]) then
\t\t\treturn false
\t\tend
\tend
\t-- Old-block reads remain observable, but this accepted bounded matrix
\t-- permits no native write or net mutation to the relocation source.
\treturn true
end

"""


ROUTE_ENDPOINT_LUA: Final = """\
local function route_endpoint_matches(route)
\tif not base_battle_anchor_matches(route) then
\t\treturn false
\tend
\tlocal expected_command = EXPECTED_ATTACK_COMMAND_STATE
\tif scenario_name == "battle-command-down" then
\t\texpected_command = EXPECTED_TECH_COMMAND_STATE
\tend
\treturn route.command_state_hex == expected_command
end

"""


OLD_INPUT_DISPATCH: Final = """\
\t\t\t\tif scenario_name == "main-menu" then
\t\t\t\t\tinput.x = pulse(relative_frame, 60, 61)
\t\t\t\telseif scenario_name == "event11c-frog" then
\t\t\t\t\tinput.a = pulse(relative_frame, 60, 61)
\t\t\t\t\t\tor pulse(relative_frame, 180, 181)
\t\t\t\t\t\tor pulse(relative_frame, 300, 301)
\t\t\t\t\t\tor pulse(relative_frame, 420, 421)
\t\t\t\t\t\tor pulse(relative_frame, 540, 541)
\t\t\t\t\t\tor pulse(relative_frame, 660, 661)
\t\t\t\t\t\tor pulse(relative_frame, 780, 781)
\t\t\t\t\t\tor pulse(relative_frame, 900, 901)
\t\t\t\t\t\tor pulse(relative_frame, 1020, 1021)
\t\t\t\t\t\tor pulse(relative_frame, 1140, 1141)
\t\t\t\tend
"""


NEW_INPUT_DISPATCH: Final = """\
\t\t\t\tfor _, scheduled in ipairs(INPUT_TIMELINES[scenario_name]) do
\t\t\t\t\tif pulse(
\t\t\t\t\t\trelative_frame,
\t\t\t\t\t\tscheduled.first,
\t\t\t\t\t\tscheduled.last
\t\t\t\t\t) then
\t\t\t\t\t\tinput[scheduled.button] = true
\t\t\t\t\tend
\t\t\t\tend
"""


def build_collector(base_source: bytes | None = None) -> bytes:
    """Return deterministic battle-v3 Lua collector bytes."""

    if base_source is None:
        try:
            base_source = BASE_COLLECTOR.read_bytes()
        except OSError as exc:
            raise CollectorBuildError(
                f"cannot read accepted base collector: {BASE_COLLECTOR}"
            ) from exc
    if len(base_source) != BASE_COLLECTOR_SIZE:
        raise CollectorBuildError("accepted base collector size drifted")
    if sha256_bytes(base_source) != BASE_COLLECTOR_SHA256:
        raise CollectorBuildError("accepted base collector SHA-256 drifted")
    try:
        source = base_source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CollectorBuildError("accepted base collector is not UTF-8") from exc

    source = _replace_once(
        source,
        "local LAP_SCRATCH = 0x1021C\n\n",
        "local LAP_SCRATCH = 0x1021C\n\n" + BATTLE_CONSTANTS_LUA,
        "battle constants insertion",
    )
    source = _replace_once(
        source,
        "local CALLBACK_LIMIT = 4096",
        f"local CALLBACK_LIMIT = {CALLBACK_LIMIT}",
        "callback limit",
    )
    source = _replace_once(
        source,
        "local EXPECTED_STATE_SIZE = 133993",
        f"local EXPECTED_STATE_SIZE = {CHECKPOINT_SIZE}",
        "checkpoint size",
    )
    source = _replace_once(
        source,
        'local CHECKPOINT_ID = "event11c-checkpoint-v5-spekkio-talkable"',
        f'local CHECKPOINT_ID = "{CHECKPOINT_ID}"',
        "checkpoint id",
    )
    source = _replace_once(
        source,
        "local CHECKPOINT_SOURCE_FRAME = 3237",
        f"local CHECKPOINT_SOURCE_FRAME = {CHECKPOINT_SOURCE_FRAME}",
        "checkpoint source frame",
    )
    source = _replace_once(
        source,
        """\
local EXPECTED_STATE_SHA256 =
\t"26788b52f63a32a7539d8acb18495df" ..
\t"1a458064f700d5411916e2bfc34c4522e"
""",
        f'local EXPECTED_STATE_SHA256 = "{CHECKPOINT_SHA256}"\n',
        "checkpoint hash",
    )
    source = _replace_once(
        source,
        "the 133,993-byte state",
        "the 261,614-byte state",
        "checkpoint-size comment",
    )
    source = _replace_once(
        source,
        "local pending_exit_code = nil\n",
        "local pending_exit_code = nil\nlocal pending_fixed_terminal = false\n",
        "fixed-terminal state",
    )

    source = _replace_region(
        source,
        "local SCENARIOS = {",
        "local state_path = assert(",
        _scenario_lua(),
        "scenario tables",
    )
    source = _replace_region(
        source,
        "local function route_snapshot()",
        "local serialized_state = read_file(state_path)",
        BATTLE_SNAPSHOT_LUA,
        "battle snapshot functions",
    )
    source = _replace_region(
        source,
        "local function prepare_fixture()",
        "local function counter_index_base(counters)",
        PREPARE_FIXTURE_LUA,
        "fixture preparation",
    )
    source = _replace_region(
        source,
        "local function scenario_contract_json()",
        "local function event_control_matches()",
        _scenario_contract_lua(),
        "scenario contract",
    )
    source = _replace_region(
        source,
        "local function event_control_matches()",
        "local function range_unchanged(pre, post)",
        EVENT_CONTROL_LUA,
        "event control",
    )
    source = _replace_region(
        source,
        "local function preservation_matches(post_ranges)",
        "local function protected_accesses_zero(counter_records)",
        PRESERVATION_LUA,
        "preservation rule",
    )
    source = _replace_region(
        source,
        "local function route_endpoint_matches(route)",
        "local function emit_trace(requested_success, require_canonical_event_png)",
        ROUTE_ENDPOINT_LUA,
        "battle endpoint rule",
    )
    source = _replace_once(
        source,
        OLD_INPUT_DISPATCH,
        NEW_INPUT_DISPATCH,
        "input scheduler",
    )
    source = _replace_once(
        source,
        """\
\t\t\t\tif scenario.terminal_frame ~= nil
\t\t\t\t\tand relative_frame == scenario.terminal_frame
\t\t\t\tthen
\t\t\t\t\temit_trace(true)
\t\t\t\t\treturn
\t\t\t\tend
""",
        """\
\t\t\t\tif scenario.terminal_frame ~= nil
\t\t\t\t\tand relative_frame == scenario.terminal_frame
\t\t\t\tthen
\t\t\t\t\tpending_fixed_terminal = true
\t\t\t\t\treturn
\t\t\t\tend
""",
        "fixed terminal scheduling",
    )
    source = _replace_once(
        source,
        """\
\tfunction()
\t\tif pending_exit_code ~= nil then
""",
        """\
\tfunction()
\t\tif pending_fixed_terminal then
\t\t\tpending_fixed_terminal = false
\t\t\temit_trace(true)
\t\t\treturn
\t\tend
\t\tif pending_exit_code ~= nil then
""",
        "end-frame fixed terminal",
    )
    source = _replace_once(
        source,
        '"schema":"project-epoch-mesen-wram-ownership-trace-v1"',
        f'"schema":"{TRACE_SCHEMA}"',
        "trace schema",
    )
    source = _replace_once(
        source,
        '"collector_version":1',
        f'"collector_version":{COLLECTOR_VERSION}',
        "collector version",
    )
    source = _replace_once(
        source,
        '\t\t\'"location":465\'',
        '\t\t\'"location":475\'',
        "checkpoint location",
    )
    source = _replace_once(
        source,
        '\t\t\'"direct_page":256,\'',
        '\t\t\'"direct_page":0,\'',
        "checkpoint direct page",
    )
    source = _replace_once(
        source,
        '\t\t\'"pre":\', snapshot_json(pre_ranges), ",",\n',
        (
            '\t\t\'"pre_battle":\', route_json(pre_route), ",",\n'
            '\t\t\'"pre":\', snapshot_json(pre_ranges), ",",\n'
        ),
        "pre-battle trace",
    )
    source = _replace_once(
        source,
        '\t\t\'"post":\', snapshot_json(post_ranges), ",",\n',
        (
            '\t\t\'"post":\', snapshot_json(post_ranges), ",",\n'
            '\t\t\'"post_battle":\', route_json(post_route), ",",\n'
        ),
        "post-battle trace",
    )
    return source.encode("utf-8")


def main() -> int:
    source = build_collector()
    print(
        f"size={len(source)} sha256={sha256_bytes(source)} "
        f"scenarios={','.join(SCENARIO_NAMES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
