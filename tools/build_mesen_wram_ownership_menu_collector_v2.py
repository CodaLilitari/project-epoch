#!/usr/bin/env python3
"""Derive the menu-ownership collector from the accepted v1 collector.

The accepted v1 source remains byte-for-byte immutable.  This builder requires
its exact preimage and changes only the scenario table, input-contract encoder,
input scheduler, trace schema, and collector version.  It returns source bytes;
the v2 launcher stages those bytes only inside its disposable private run.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Final


ROOT = Path(__file__).resolve().parents[1]
BASE_COLLECTOR = ROOT / "tools" / "mesen_wram_ownership_trace.lua"
BASE_COLLECTOR_SHA256: Final = (
    "d5dd2b2d7085237844d95ab04f7007b6"
    "b2d17b2e1160f23857018319380b7569"
)
TRACE_SCHEMA: Final = "project-epoch-mesen-wram-ownership-menu-trace-v2"
COLLECTOR_VERSION: Final = 2


class CollectorBuildError(RuntimeError):
    """Raised when the accepted base source or a transform preimage drifts."""


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
        if not (0 <= self.start_frame <= self.end_frame <= 600):
            raise ValueError("input pulse lies outside the bounded timeline")


@dataclass(frozen=True)
class Scenario:
    name: str
    pulses: tuple[Pulse, ...]
    terminal_frame: int = 600


def _pulse(button: str, start: int, width: int = 2) -> Pulse:
    return Pulse(button, button.upper(), start, start + width - 1)


SCENARIOS: Final = (
    Scenario(
        "equipment-owner-switch",
        (
            _pulse("x", 60),
            _pulse("a", 180),
            _pulse("down", 300, 4),
            _pulse("b", 420),
        ),
    ),
    Scenario(
        "tech-owner-switch",
        (
            _pulse("x", 60),
            _pulse("right", 120, 4),
            _pulse("right", 160, 4),
            _pulse("a", 220),
            _pulse("down", 300, 4),
            _pulse("b", 420),
        ),
    ),
    Scenario(
        "item-list-cancel",
        (
            _pulse("x", 60),
            _pulse("right", 120, 4),
            _pulse("a", 180),
            _pulse("b", 420),
        ),
    ),
    Scenario(
        "party-page-cancel",
        (
            _pulse("x", 60),
            _pulse("right", 120, 4),
            _pulse("right", 160, 4),
            _pulse("right", 200, 4),
            _pulse("right", 240, 4),
            _pulse("a", 300),
            _pulse("right", 380, 4),
            _pulse("b", 500),
        ),
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
    return """local function scenario_contract_json()
\tlocal pulses = {}
\tfor _, scheduled in ipairs(INPUT_TIMELINES[scenario_name]) do
\t\ttable.insert(pulses, table.concat({
\t\t\t'{"port":1,"button":',
\t\t\tjson_string(scheduled.json_button),
\t\t\t',"start_frame":',
\t\t\ttostring(scheduled.first),
\t\t\t',"end_frame":',
\t\t\ttostring(scheduled.last),
\t\t\t"}",
\t\t}))
\tend
\treturn table.concat({
\t\t"{",
\t\t'"terminal_frame_min":',
\t\ttostring(scenario.minimum_terminal_frame), ",",
\t\t'"terminal_frame_max":', tostring(scenario.maximum_frame), ",",
\t\t'"expected_access_class":"ownership-negative-control",',
\t\t'"inputs":[', table.concat(pulses, ","), "]",
\t\t"}",
\t})
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
    """Return the deterministic menu-v2 Lua collector bytes."""

    if base_source is None:
        try:
            base_source = BASE_COLLECTOR.read_bytes()
        except OSError as exc:
            raise CollectorBuildError(
                f"cannot read accepted base collector: {BASE_COLLECTOR}"
            ) from exc
    if sha256_bytes(base_source) != BASE_COLLECTOR_SHA256:
        raise CollectorBuildError("accepted base collector SHA-256 drifted")
    try:
        source = base_source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CollectorBuildError("accepted base collector is not UTF-8") from exc

    scenario_start = source.find("local SCENARIOS = {")
    scenario_end = source.find("local state_path = assert(", scenario_start)
    if scenario_start < 0 or scenario_end < 0:
        raise CollectorBuildError("scenario-table preimage markers are missing")
    source = (
        source[:scenario_start]
        + _scenario_lua()
        + source[scenario_end:]
    )

    contract_start = source.find("local function scenario_contract_json()")
    contract_end = source.find(
        "local function event_control_matches()",
        contract_start,
    )
    if contract_start < 0 or contract_end < 0:
        raise CollectorBuildError(
            "scenario-contract function preimage markers are missing"
        )
    source = (
        source[:contract_start]
        + _scenario_contract_lua()
        + source[contract_end:]
    )

    source = _replace_once(
        source,
        OLD_INPUT_DISPATCH,
        NEW_INPUT_DISPATCH,
        "input scheduler",
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
