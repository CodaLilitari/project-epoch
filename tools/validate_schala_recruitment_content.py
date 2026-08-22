#!/usr/bin/env python3
"""Validate Schala's original authoring-only recruitment specification.

The input is a symbolic narrative state machine. It is deliberately unable to
name event opcodes, ROM addresses, table entries, or encoded values.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "content"
    / "schala_recruitment_content_v0.json"
)

TOP_LEVEL_KEYS = {
    "schema_version",
    "content_id",
    "logical_pc_id",
    "content_origin",
    "authoring_status",
    "evidence_level",
    "provenance",
    "quest",
    "state_variables",
    "runtime_bindings",
    "entry_node",
    "nodes",
    "acceptance_scenarios",
}
STATE_TYPES = {
    "quest_unlocked": "bool",
    "anchor_count": "int_0_3",
    "ward_resolved": "bool",
    "schala_recruited": "bool",
    "schala_join_grant_applied": "bool",
    "magus_present": "bool",
    "party_has_open_slot": "bool",
    "is_new_game_plus": "bool",
}
REQUIRED_BINDING_IDS = {
    "quest_entry_dispatch",
    "quest_unlock_flag",
    "anchor_counter",
    "ward_resolved_flag",
    "recruited_flag",
    "join_grant_guard_flag",
    "new_game_plus_context_query",
    "magus_presence_query",
    "party_capacity_query",
    "logical_pc_07_runtime_record",
    "logical_pc_07_roster_insert",
    "logical_pc_07_active_party_insert",
    "logical_pc_07_reserve_insert",
    "party_exchange_ui",
    "starting_tech_unlocks",
    "starting_loadout_inventory",
    "pendant_shard_inventory",
    "dialogue_text_storage",
    "dialogue_choice_dispatch",
    "silent_palace_map",
    "schala_event_object",
    "schala_original_field_sprite",
    "schala_original_battle_sprite",
    "schala_original_portraits",
    "guest_veil_demonstration",
    "save_sidecar_persistence",
    "new_game_plus_transfer",
    "scene_music",
    "scene_sound_effects",
}
BINDING_KEYS = {
    "binding_id",
    "purpose",
    "mapping_status",
    "engine_address",
    "event_opcode",
    "data_table",
    "encoded_value",
}
UNMAPPED_FIELDS = {
    "engine_address",
    "event_opcode",
    "data_table",
    "encoded_value",
}
COMMON_NODE_KEYS = {"node_id", "type", "mapping_status", "runtime_binding"}
NODE_KEYS = {
    "branch": COMMON_NODE_KEYS | {"condition", "then", "else"},
    "dialogue": COMMON_NODE_KEYS
    | {"speaker", "text", "dialogue_source", "next"},
    "choice": COMMON_NODE_KEYS | {"prompt", "options"},
    "action": COMMON_NODE_KEYS | {"operations", "next"},
    "end": COMMON_NODE_KEYS | {"outcome"},
}
ALLOWED_EFFECTS = {
    "evaluate_project_epoch_state_without_duplicate_join_grants",
    "unlock_astral_pin_veil_and_crescent_wake",
    "grant_original_glass_focus_and_regent_mantle",
    "register_logical_pc_07_once",
    "add_logical_pc_07_to_active_party",
    "register_logical_pc_07_in_reserve",
    "open_party_exchange_for_optional_swap",
}
REQUIRED_SCENARIOS = {
    "magus_present_accept_open_slot",
    "magus_absent_accept_open_slot",
    "decline_without_mutation",
    "party_full_accept_to_reserve",
    "already_recruited_is_idempotent",
    "new_game_plus_preserved_join_is_idempotent",
    "new_game_plus_reset_branch_can_recruit_once",
}


def canonical_bytes(content: dict[str, Any]) -> bytes:
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


def load_content(path: pathlib.Path = CONTENT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_ascii_text(value: Any, context: str, maximum: int = 240) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise RuntimeError(f"{context}: invalid text")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeError(f"{context}: text must be ASCII") from exc


def _validate_state(state: Any, context: str) -> None:
    if not isinstance(state, dict) or set(state) != set(STATE_TYPES):
        raise RuntimeError(f"{context}: state variables do not match schema")
    for name, expected_type in STATE_TYPES.items():
        value = state[name]
        if expected_type == "bool":
            if not isinstance(value, bool):
                raise RuntimeError(f"{context}: {name} must be boolean")
        elif (
            expected_type == "int_0_3"
            and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 0 <= value <= 3
            )
        ):
            raise RuntimeError(f"{context}: {name} must be from 0 through 3")


def _node_references(node: dict[str, Any]) -> list[str]:
    if node["type"] == "branch":
        return [node["then"], node["else"]]
    if node["type"] in {"dialogue", "action"}:
        return [node["next"]]
    if node["type"] == "choice":
        return [option["next"] for option in node["options"]]
    return []


def _validate_operation(operation: Any, context: str) -> None:
    if not isinstance(operation, dict) or "op" not in operation:
        raise RuntimeError(f"{context}: malformed symbolic operation")
    op = operation["op"]
    if op == "set_if_false":
        if set(operation) != {"op", "variable", "value"}:
            raise RuntimeError(f"{context}: malformed set_if_false")
        if (
            operation["variable"] != "schala_recruited"
            or operation["value"] is not True
        ):
            raise RuntimeError(f"{context}: unsafe recruitment state update")
    elif op == "emit_once":
        if set(operation) != {"op", "guard", "effects"}:
            raise RuntimeError(f"{context}: malformed emit_once")
        if operation["guard"] != "schala_join_grant_applied":
            raise RuntimeError(f"{context}: wrong one-time grant guard")
        effects = operation["effects"]
        if (
            not isinstance(effects, list)
            or not effects
            or len(effects) != len(set(effects))
            or not set(effects) <= ALLOWED_EFFECTS
        ):
            raise RuntimeError(f"{context}: invalid one-time effects")
    elif op == "emit":
        if set(operation) != {"op", "effect"}:
            raise RuntimeError(f"{context}: malformed emit")
        if operation["effect"] not in ALLOWED_EFFECTS:
            raise RuntimeError(f"{context}: unknown symbolic effect")
    else:
        raise RuntimeError(f"{context}: unsupported symbolic operation {op!r}")


def _run_scenario(
    nodes: dict[str, dict[str, Any]],
    entry_node: str,
    initial_state: dict[str, Any],
    choices: dict[str, str],
) -> tuple[str, list[str], dict[str, Any], list[str]]:
    state = dict(initial_state)
    effects: list[str] = []
    trace: list[str] = []
    current = entry_node
    for _ in range(len(nodes) + 1):
        if current in trace:
            raise RuntimeError(f"scenario entered a cycle at {current}")
        trace.append(current)
        node = nodes[current]
        node_type = node["type"]
        if node_type == "branch":
            condition = node["condition"]
            current = (
                node["then"]
                if state[condition["variable"]] == condition["equals"]
                else node["else"]
            )
        elif node_type == "dialogue":
            current = node["next"]
        elif node_type == "choice":
            choice_id = choices.get(current)
            options = {
                option["choice_id"]: option["next"]
                for option in node["options"]
            }
            if choice_id not in options:
                raise RuntimeError(f"scenario lacks a valid choice for {current}")
            current = options[choice_id]
        elif node_type == "action":
            for operation in node["operations"]:
                if operation["op"] == "set_if_false":
                    if state[operation["variable"]] is False:
                        state[operation["variable"]] = operation["value"]
                elif operation["op"] == "emit_once":
                    if state[operation["guard"]] is False:
                        effects.extend(operation["effects"])
                        state[operation["guard"]] = True
                else:
                    effects.append(operation["effect"])
            current = node["next"]
        else:
            return node["outcome"], effects, state, trace
    raise RuntimeError("scenario exceeded the acyclic node budget")


def validate_content(content: dict[str, Any]) -> None:
    if set(content) != TOP_LEVEL_KEYS:
        raise RuntimeError("recruitment content top-level schema changed")
    if content["schema_version"] != 1:
        raise RuntimeError("unsupported recruitment content schema")
    if content["logical_pc_id"] != 7:
        raise RuntimeError("Schala must remain logical PC 7")
    if content["content_origin"] != "project-epoch-original":
        raise RuntimeError("recruitment content must be Project Epoch original")
    if content["authoring_status"] != "authoring-only-unmapped":
        raise RuntimeError("recruitment content must remain authoring-only")
    if content["evidence_level"] != "hypothesis":
        raise RuntimeError("unimplemented recruitment content is hypothesis")

    provenance = content["provenance"]
    expected_provenance = {
        "dialogue_source",
        "rom_or_event_bytes_imported",
        "copied_vanilla_dialogue",
        "copied_npc_sprite_data",
        "notes",
    }
    if not isinstance(provenance, dict) or set(provenance) != expected_provenance:
        raise RuntimeError("recruitment provenance schema changed")
    if provenance["dialogue_source"] != "written-for-project-epoch":
        raise RuntimeError("dialogue provenance must identify original writing")
    for prohibited in (
        "rom_or_event_bytes_imported",
        "copied_vanilla_dialogue",
        "copied_npc_sprite_data",
    ):
        if provenance[prohibited] is not False:
            raise RuntimeError(f"{prohibited} is prohibited")
    _require_ascii_text(provenance["notes"], "provenance notes", 320)

    quest = content["quest"]
    if not isinstance(quest, dict) or set(quest) != {
        "title",
        "placement",
        "premise",
        "recruitment_agency",
    }:
        raise RuntimeError("quest summary schema changed")
    if quest["title"] != "The Silent Palace":
        raise RuntimeError("recruitment quest identity changed")
    for key, value in quest.items():
        _require_ascii_text(value, f"quest {key}", 320)

    state_variables = content["state_variables"]
    if not isinstance(state_variables, list):
        raise RuntimeError("state_variables must be a list")
    by_state_name: dict[str, dict[str, Any]] = {}
    for variable in state_variables:
        if not isinstance(variable, dict) or set(variable) != {
            "name",
            "type",
            "purpose",
            "mapping_status",
            "runtime_binding",
        }:
            raise RuntimeError("state variable schema changed")
        name = variable["name"]
        if name in by_state_name:
            raise RuntimeError(f"duplicate state variable {name}")
        by_state_name[name] = variable
        if variable["mapping_status"] != "unmapped":
            raise RuntimeError(f"{name}: state binding must remain unmapped")
        if variable["runtime_binding"] is not None:
            raise RuntimeError(f"{name}: runtime binding requires trace approval")
        _require_ascii_text(variable["purpose"], f"{name} purpose")
    if {
        name: variable["type"]
        for name, variable in by_state_name.items()
    } != STATE_TYPES:
        raise RuntimeError("state variable names or types changed")

    bindings = content["runtime_bindings"]
    if not isinstance(bindings, list):
        raise RuntimeError("runtime_bindings must be a list")
    binding_ids: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != BINDING_KEYS:
            raise RuntimeError("runtime binding schema changed")
        binding_id = binding["binding_id"]
        if binding_id in binding_ids:
            raise RuntimeError(f"duplicate runtime binding {binding_id}")
        binding_ids.add(binding_id)
        _require_ascii_text(binding_id, "binding ID", 80)
        _require_ascii_text(binding["purpose"], f"{binding_id} purpose")
        if binding["mapping_status"] != "unmapped":
            raise RuntimeError(f"{binding_id}: binding must remain unmapped")
        for field in UNMAPPED_FIELDS:
            if binding[field] is not None:
                raise RuntimeError(
                    f"{binding_id}: {field} requires trace approval"
                )
    if binding_ids != REQUIRED_BINDING_IDS:
        raise RuntimeError("runtime binding inventory changed")

    nodes_list = content["nodes"]
    if not isinstance(nodes_list, list) or not nodes_list:
        raise RuntimeError("nodes must be a nonempty list")
    nodes: dict[str, dict[str, Any]] = {}
    dialogue_texts: set[str] = set()
    outcomes: set[str] = set()
    for node in nodes_list:
        if not isinstance(node, dict):
            raise RuntimeError("node must be an object")
        node_type = node.get("type")
        if node_type not in NODE_KEYS or set(node) != NODE_KEYS[node_type]:
            raise RuntimeError(f"{node.get('node_id', '?')}: node schema changed")
        node_id = node["node_id"]
        _require_ascii_text(node_id, "node ID", 80)
        if node_id in nodes:
            raise RuntimeError(f"duplicate node {node_id}")
        nodes[node_id] = node
        if node["mapping_status"] != "unmapped":
            raise RuntimeError(f"{node_id}: node must remain unmapped")
        if node["runtime_binding"] is not None:
            raise RuntimeError(f"{node_id}: runtime binding requires trace approval")

        if node_type == "branch":
            condition = node["condition"]
            if (
                not isinstance(condition, dict)
                or set(condition) != {"variable", "equals"}
                or condition["variable"] not in STATE_TYPES
            ):
                raise RuntimeError(f"{node_id}: malformed condition")
            expected_type = STATE_TYPES[condition["variable"]]
            value = condition["equals"]
            if expected_type == "bool" and not isinstance(value, bool):
                raise RuntimeError(f"{node_id}: boolean condition changed")
            if expected_type == "int_0_3" and value not in range(4):
                raise RuntimeError(f"{node_id}: counter condition out of range")
        elif node_type == "dialogue":
            if node["dialogue_source"] != "written-for-project-epoch":
                raise RuntimeError(f"{node_id}: dialogue provenance changed")
            _require_ascii_text(node["speaker"], f"{node_id} speaker", 24)
            _require_ascii_text(node["text"], f"{node_id} dialogue")
            if node["text"] in dialogue_texts:
                raise RuntimeError(f"{node_id}: duplicate dialogue")
            dialogue_texts.add(node["text"])
        elif node_type == "choice":
            _require_ascii_text(node["prompt"], f"{node_id} prompt", 80)
            options = node["options"]
            if not isinstance(options, list) or len(options) != 2:
                raise RuntimeError(f"{node_id}: expected accept/decline pair")
            choice_ids: set[str] = set()
            for option in options:
                if not isinstance(option, dict) or set(option) != {
                    "choice_id",
                    "label",
                    "next",
                }:
                    raise RuntimeError(f"{node_id}: malformed choice option")
                choice_ids.add(option["choice_id"])
                _require_ascii_text(
                    option["label"],
                    f"{node_id} {option['choice_id']} label",
                    40,
                )
            if choice_ids != {"accept", "decline"}:
                raise RuntimeError(f"{node_id}: choices must be accept/decline")
        elif node_type == "action":
            operations = node["operations"]
            if not isinstance(operations, list) or not operations:
                raise RuntimeError(f"{node_id}: action must not be empty")
            for index, operation in enumerate(operations):
                _validate_operation(operation, f"{node_id} operation {index}")
        else:
            _require_ascii_text(node["outcome"], f"{node_id} outcome", 80)
            if node["outcome"] in outcomes:
                raise RuntimeError(f"{node_id}: duplicate outcome")
            outcomes.add(node["outcome"])

    entry_node = content["entry_node"]
    if entry_node != "entry_already_recruited" or entry_node not in nodes:
        raise RuntimeError("recruitment entry guard changed")
    for node in nodes.values():
        for reference in _node_references(node):
            if reference not in nodes:
                raise RuntimeError(
                    f"{node['node_id']}: unknown node reference {reference}"
                )

    reachable: set[str] = set()
    pending = [entry_node]
    while pending:
        node_id = pending.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        pending.extend(_node_references(nodes[node_id]))
    if reachable != set(nodes):
        raise RuntimeError(
            f"unreachable recruitment nodes: {sorted(set(nodes) - reachable)}"
        )

    scenarios = content["acceptance_scenarios"]
    if not isinstance(scenarios, list):
        raise RuntimeError("acceptance_scenarios must be a list")
    scenario_ids: set[str] = set()
    scenario_results: dict[str, tuple[str, list[str], dict[str, Any], list[str]]] = {}
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {
            "scenario_id",
            "initial_state",
            "choices",
            "expected_outcome",
            "expected_effects",
            "expected_final_state",
        }:
            raise RuntimeError("acceptance scenario schema changed")
        scenario_id = scenario["scenario_id"]
        if scenario_id in scenario_ids:
            raise RuntimeError(f"duplicate acceptance scenario {scenario_id}")
        scenario_ids.add(scenario_id)
        _validate_state(scenario["initial_state"], scenario_id)
        if not isinstance(scenario["choices"], dict):
            raise RuntimeError(f"{scenario_id}: choices must be an object")
        expected_effects = scenario["expected_effects"]
        if (
            not isinstance(expected_effects, list)
            or not set(expected_effects) <= ALLOWED_EFFECTS
        ):
            raise RuntimeError(f"{scenario_id}: unknown expected effect")
        expected_final = scenario["expected_final_state"]
        if not isinstance(expected_final, dict) or not set(expected_final) <= set(
            STATE_TYPES
        ):
            raise RuntimeError(f"{scenario_id}: invalid expected final state")

        result = _run_scenario(
            nodes,
            entry_node,
            scenario["initial_state"],
            scenario["choices"],
        )
        scenario_results[scenario_id] = result
        outcome, effects, final_state, _trace = result
        if outcome != scenario["expected_outcome"]:
            raise RuntimeError(f"{scenario_id}: expected outcome mismatch")
        if effects != expected_effects:
            raise RuntimeError(f"{scenario_id}: expected effects mismatch")
        for name, expected_value in expected_final.items():
            if final_state[name] != expected_value:
                raise RuntimeError(f"{scenario_id}: final {name} mismatch")
    if scenario_ids != REQUIRED_SCENARIOS:
        raise RuntimeError("acceptance scenario inventory changed")

    trace_requirements = {
        "magus_present_accept_open_slot": "magus_observation",
        "magus_absent_accept_open_slot": "schala_without_magus",
        "decline_without_mutation": "decline_line",
        "party_full_accept_to_reserve": "insert_reserve_party",
        "already_recruited_is_idempotent": "already_recruited_line",
        "new_game_plus_preserved_join_is_idempotent": "already_recruited_line",
        "new_game_plus_reset_branch_can_recruit_once": "new_game_plus_guard",
    }
    for scenario_id, required_node in trace_requirements.items():
        if required_node not in scenario_results[scenario_id][3]:
            raise RuntimeError(
                f"{scenario_id}: did not exercise {required_node}"
            )


def manifest(content: dict[str, Any]) -> dict[str, Any]:
    validate_content(content)
    nodes = content["nodes"]
    return {
        "content_id": content["content_id"],
        "logical_pc_id": content["logical_pc_id"],
        "authoring_status": content["authoring_status"],
        "evidence_level": content["evidence_level"],
        "canonical_sha256": sha256(canonical_bytes(content)),
        "node_count": len(nodes),
        "dialogue_count": sum(node["type"] == "dialogue" for node in nodes),
        "binding_count": len(content["runtime_bindings"]),
        "scenario_count": len(content["acceptance_scenarios"]),
        "outcomes": sorted(
            node["outcome"] for node in nodes if node["type"] == "end"
        ),
        "mapped_binding_count": sum(
            binding["mapping_status"] != "unmapped"
            for binding in content["runtime_bindings"]
        ),
        "node_type_counts": dict(
            sorted(collections.Counter(node["type"] for node in nodes).items())
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
