#!/usr/bin/env python3
"""Pinned Project Epoch command identities for playable Schala.

These are logical action IDs and UI labels, not encoded ROM records. The
production builder will consume this manifest after the high-ID readers and
expanded data tables are implemented.
"""

from __future__ import annotations

import dataclasses
import json


SCHALA_ID = 0x07
FIRST_EXTENDED_ID = 0x80
LAST_EXTENDED_ID = 0x90
VANILLA_LAST_ACTION_ID = 0x7B
PRESERVED_PLAYER_COMMAND_GAP_IDS = frozenset(range(0x7C, 0x80))
MARKER_FAMILY = frozenset(range(0xF0, 0x100))
MAX_UI_NAME_CHARS = 10


@dataclasses.dataclass(frozen=True)
class CommandSpec:
    action_id: int
    design_name: str
    ui_name: str
    kind: str
    participants: tuple[int, ...]


COMMANDS = (
    CommandSpec(0x80, "Astral Pin", "Astral Pin", "single", (7,)),
    CommandSpec(0x81, "Veil", "Veil", "single", (7,)),
    CommandSpec(0x82, "Crescent Wake", "Cres. Wake", "single", (7,)),
    CommandSpec(0x83, "Stillpoint", "Stillpoint", "single", (7,)),
    CommandSpec(0x84, "Recall", "Recall", "single", (7,)),
    CommandSpec(0x85, "Sanctuary", "Sanctuary", "single", (7,)),
    CommandSpec(0x86, "Rift Bloom", "Rift Bloom", "single", (7,)),
    CommandSpec(0x87, "Astral Gate", "AstralGate", "single", (7,)),
    CommandSpec(0x88, "Horizon Arc", "HorizonArc", "dual", (0, 7)),
    CommandSpec(0x89, "Quiet Heaven", "Q. Heaven", "dual", (1, 7)),
    CommandSpec(0x8A, "Eventide", "Eventide", "dual", (2, 7)),
    CommandSpec(0x8B, "Oathguard", "Oathguard", "dual", (4, 7)),
    CommandSpec(0x8C, "Phase Engine", "PhaseGear", "dual", (3, 7)),
    CommandSpec(0x8D, "Star Pounce", "StarPounce", "dual", (5, 7)),
    CommandSpec(0x8E, "New Dawn", "New Dawn", "triple", (0, 1, 7)),
    CommandSpec(0x8F, "Little Star", "LittleStar", "triple", (2, 3, 7)),
    CommandSpec(0x90, "Focus Pulse", "FocusPulse", "basic", (7,)),
)


def validate_layout(commands: tuple[CommandSpec, ...] = COMMANDS) -> None:
    ids = [command.action_id for command in commands]
    if ids != list(range(FIRST_EXTENDED_ID, LAST_EXTENDED_ID + 1)):
        raise RuntimeError("Schala action IDs must be contiguous $80-$90")
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate Schala action ID")
    if any(
        action_id <= VANILLA_LAST_ACTION_ID
        or action_id in PRESERVED_PLAYER_COMMAND_GAP_IDS
        or action_id in MARKER_FAMILY
        for action_id in ids
    ):
        raise RuntimeError("Schala action ID collides with a reserved namespace")

    expected_counts = {"single": 8, "dual": 6, "triple": 2, "basic": 1}
    actual_counts = {
        kind: sum(command.kind == kind for command in commands)
        for kind in expected_counts
    }
    if actual_counts != expected_counts:
        raise RuntimeError(
            f"unexpected command-kind counts: {actual_counts!r}"
        )

    for command in commands:
        if len(command.ui_name) > MAX_UI_NAME_CHARS:
            raise RuntimeError(
                f"UI name {command.ui_name!r} exceeds "
                f"{MAX_UI_NAME_CHARS} visible characters"
            )
        if SCHALA_ID not in command.participants:
            raise RuntimeError(f"{command.design_name} omits Schala")
        if len(set(command.participants)) != len(command.participants):
            raise RuntimeError(f"{command.design_name} repeats a participant")
        expected_participants = {
            "single": 1,
            "dual": 2,
            "triple": 3,
            "basic": 1,
        }[command.kind]
        if len(command.participants) != expected_participants:
            raise RuntimeError(
                f"{command.design_name} has the wrong participant count"
            )


def manifest() -> dict[str, object]:
    validate_layout()
    return {
        "logical_character_id": SCHALA_ID,
        "extended_action_range": [
            FIRST_EXTENDED_ID,
            LAST_EXTENDED_ID,
        ],
        "preserved_player_command_gap_ids": sorted(
            PRESERVED_PLAYER_COMMAND_GAP_IDS
        ),
        "marker_family": [min(MARKER_FAMILY), max(MARKER_FAMILY)],
        "commands": [
            {
                "action_id": command.action_id,
                "action_id_hex": f"${command.action_id:02X}",
                "design_name": command.design_name,
                "ui_name": command.ui_name,
                "kind": command.kind,
                "participants": list(command.participants),
            }
            for command in COMMANDS
        ],
    }


def main() -> None:
    print(json.dumps(manifest(), indent=2))


if __name__ == "__main__":
    main()
