#!/usr/bin/env python3
"""Validate Schala's original authoring-only command content.

The JSON contains original design data, not ROM records. Native target,
property, animation, and effect bindings intentionally remain null until the
corresponding readers and primitives have been traced.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib

import schala_command_layout


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "content"
    / "schala_tech_content_v0.json"
)
MAX_DESCRIPTION_CHARS = 48
ALLOWED_KINDS = frozenset({"single", "dual", "triple", "basic"})
ALLOWED_TARGETS = frozenset(
    {
        "one_enemy",
        "one_ally",
        "one_fallen_ally",
        "enemy_line",
        "enemy_circle",
        "all_enemies",
        "all_allies",
        "all_enemies_and_allies",
    }
)


def canonical_bytes(content: dict[str, object]) -> bytes:
    return (
        json.dumps(
            content,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_content(path: pathlib.Path = CONTENT_PATH) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_content(content: dict[str, object]) -> None:
    schala_command_layout.validate_layout()
    if content.get("schema_version") != 1:
        raise RuntimeError("unsupported Schala content schema")
    if content.get("logical_pc_id") != schala_command_layout.SCHALA_ID:
        raise RuntimeError("Schala logical PC ID changed")
    if content.get("content_origin") != "project-epoch-original":
        raise RuntimeError("content must be marked Project Epoch original")
    if content.get("rom_encoding_status") != "authoring-only-unmapped":
        raise RuntimeError("content must remain authoring-only until mapped")

    provenance = content.get("provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError("missing content provenance")
    if provenance.get("rom_or_npc_data_imported") is not False:
        raise RuntimeError("ROM or NPC data import is prohibited")
    if provenance.get("copied_vanilla_records") is not False:
        raise RuntimeError("copied vanilla records are prohibited")

    commands = content.get("commands")
    if not isinstance(commands, list):
        raise RuntimeError("commands must be a list")
    if len(commands) != len(schala_command_layout.COMMANDS):
        raise RuntimeError("content command count does not match layout")

    by_id: dict[int, dict[str, object]] = {}
    descriptions: set[str] = set()
    for command in commands:
        if not isinstance(command, dict):
            raise RuntimeError("command entry must be an object")
        action_id = command.get("action_id")
        if not isinstance(action_id, int):
            raise RuntimeError("command action ID must be an integer")
        if action_id in by_id:
            raise RuntimeError(f"duplicate command ID ${action_id:02X}")
        by_id[action_id] = command

        for field in (
            "design_name",
            "ui_name",
            "description",
            "animation_family",
        ):
            value = command.get(field)
            if not isinstance(value, str) or not value:
                raise RuntimeError(f"${action_id:02X}: invalid {field}")
            try:
                value.encode("ascii")
            except UnicodeEncodeError as exc:
                raise RuntimeError(
                    f"${action_id:02X}: {field} must be ASCII"
                ) from exc
        if len(command["ui_name"]) > schala_command_layout.MAX_UI_NAME_CHARS:
            raise RuntimeError(f"${action_id:02X}: UI name exceeds budget")
        if len(command["description"]) > MAX_DESCRIPTION_CHARS:
            raise RuntimeError(f"${action_id:02X}: description exceeds budget")
        if command["description"] in descriptions:
            raise RuntimeError(f"${action_id:02X}: duplicate description")
        descriptions.add(command["description"])

        if command.get("kind") not in ALLOWED_KINDS:
            raise RuntimeError(f"${action_id:02X}: invalid command kind")
        if command.get("target") not in ALLOWED_TARGETS:
            raise RuntimeError(f"${action_id:02X}: invalid target")
        participants = command.get("participants")
        if not isinstance(participants, list) or not participants:
            raise RuntimeError(f"${action_id:02X}: invalid participants")
        if len(participants) != len(set(participants)):
            raise RuntimeError(f"${action_id:02X}: repeated participant")
        if schala_command_layout.SCHALA_ID not in participants:
            raise RuntimeError(f"${action_id:02X}: Schala is not a participant")

        mp_budget = command.get("mp_budget")
        if not isinstance(mp_budget, dict):
            raise RuntimeError(f"${action_id:02X}: invalid MP budget")
        expected_keys = {str(participant) for participant in participants}
        if set(mp_budget) != expected_keys:
            raise RuntimeError(
                f"${action_id:02X}: MP budget does not match participants"
            )
        if any(
            not isinstance(value, int) or not 0 <= value <= 99
            for value in mp_budget.values()
        ):
            raise RuntimeError(f"${action_id:02X}: invalid MP value")

        effects = command.get("effects")
        if not isinstance(effects, list) or not effects:
            raise RuntimeError(f"${action_id:02X}: effects must be nonempty")
        if any(
            not isinstance(effect, dict)
            or not isinstance(effect.get("type"), str)
            or not isinstance(effect.get("scale"), str)
            for effect in effects
        ):
            raise RuntimeError(f"${action_id:02X}: malformed effect")
        learning = command.get("learning")
        if (
            not isinstance(learning, dict)
            or not isinstance(learning.get("type"), str)
            or not isinstance(learning.get("value"), int)
        ):
            raise RuntimeError(f"${action_id:02X}: malformed learning rule")
        if command.get("primitive_binding") is not None:
            raise RuntimeError(
                f"${action_id:02X}: native binding requires trace approval"
            )

    expected = {
        command.action_id: command
        for command in schala_command_layout.COMMANDS
    }
    if set(by_id) != set(expected):
        raise RuntimeError("content IDs do not match the pinned layout")
    for action_id, layout in expected.items():
        content_command = by_id[action_id]
        if (
            content_command["design_name"] != layout.design_name
            or content_command["ui_name"] != layout.ui_name
            or content_command["kind"] != layout.kind
            or tuple(content_command["participants"]) != layout.participants
        ):
            raise RuntimeError(
                f"${action_id:02X}: content disagrees with command layout"
            )

    counts = collections.Counter(
        command["kind"] for command in commands
    )
    if counts != {"single": 8, "dual": 6, "triple": 2, "basic": 1}:
        raise RuntimeError(f"unexpected content kind counts: {dict(counts)}")


def manifest(content: dict[str, object]) -> dict[str, object]:
    validate_content(content)
    commands = content["commands"]
    return {
        "content_id": content["content_id"],
        "logical_pc_id": content["logical_pc_id"],
        "content_origin": content["content_origin"],
        "rom_encoding_status": content["rom_encoding_status"],
        "canonical_sha256": sha256(canonical_bytes(content)),
        "command_count": len(commands),
        "kind_counts": dict(
            sorted(collections.Counter(
                command["kind"] for command in commands
            ).items())
        ),
        "action_range": [
            min(command["action_id"] for command in commands),
            max(command["action_id"] for command in commands),
        ],
        "native_bindings_present": any(
            command["primitive_binding"] is not None for command in commands
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "content",
        nargs="?",
        type=pathlib.Path,
        default=CONTENT_PATH,
    )
    args = parser.parse_args()
    print(json.dumps(manifest(load_content(args.content)), indent=2))


if __name__ == "__main__":
    main()
