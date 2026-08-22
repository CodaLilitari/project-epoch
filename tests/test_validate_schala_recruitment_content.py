from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TOOL_PATH = TOOLS / "validate_schala_recruitment_content.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("validate_schala_recruitment_content", TOOL_PATH)


class ValidateSchalaRecruitmentContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.content = TOOL.load_content()

    def test_canonical_content_validates(self) -> None:
        TOOL.validate_content(self.content)

    def test_manifest_pins_original_unmapped_pack(self) -> None:
        result = TOOL.manifest(self.content)
        self.assertEqual(result["logical_pc_id"], 7)
        self.assertEqual(result["authoring_status"], "authoring-only-unmapped")
        self.assertEqual(result["evidence_level"], "hypothesis")
        self.assertEqual(result["node_count"], 28)
        self.assertEqual(result["dialogue_count"], 11)
        self.assertEqual(result["binding_count"], 29)
        self.assertEqual(result["scenario_count"], 7)
        self.assertEqual(result["mapped_binding_count"], 0)
        self.assertEqual(
            result["canonical_sha256"],
            "fbffbc7bd9bed555ed7966ed62f6b9b247b4403986fef358711e9e00e13520eb",
        )

    def test_dialogue_is_explicitly_original_authoring(self) -> None:
        dialogue_nodes = [
            node for node in self.content["nodes"] if node["type"] == "dialogue"
        ]
        self.assertTrue(dialogue_nodes)
        self.assertTrue(
            all(
                node["dialogue_source"] == "written-for-project-epoch"
                for node in dialogue_nodes
            )
        )
        self.assertFalse(
            self.content["provenance"]["rom_or_event_bytes_imported"]
        )
        self.assertFalse(
            self.content["provenance"]["copied_vanilla_dialogue"]
        )

    def test_rejects_logical_pc_identity_drift(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["logical_pc_id"] = 6
        with self.assertRaisesRegex(RuntimeError, "logical PC 7"):
            TOOL.validate_content(changed)

    def test_rejects_any_mapped_runtime_binding(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["runtime_bindings"][0]["mapping_status"] = "verified-static"
        changed["runtime_bindings"][0]["engine_address"] = 0x123456
        with self.assertRaisesRegex(RuntimeError, "must remain unmapped"):
            TOOL.validate_content(changed)

    def test_rejects_node_runtime_binding(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["nodes"][0]["runtime_binding"] = {"opcode": 1}
        with self.assertRaisesRegex(RuntimeError, "trace approval"):
            TOOL.validate_content(changed)

    def test_rejects_provenance_that_imports_event_bytes(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["provenance"]["rom_or_event_bytes_imported"] = True
        with self.assertRaisesRegex(RuntimeError, "prohibited"):
            TOOL.validate_content(changed)

    def test_rejects_missing_party_full_branch_effect(self) -> None:
        changed = copy.deepcopy(self.content)
        reserve = next(
            node
            for node in changed["nodes"]
            if node["node_id"] == "insert_reserve_party"
        )
        reserve["operations"].pop()
        with self.assertRaisesRegex(RuntimeError, "expected effects mismatch"):
            TOOL.validate_content(changed)

    def test_rejects_duplicate_grant_without_guard(self) -> None:
        changed = copy.deepcopy(self.content)
        commit = next(
            node
            for node in changed["nodes"]
            if node["node_id"] == "commit_recruitment"
        )
        commit["operations"][1] = {
            "op": "emit",
            "effect": "grant_original_glass_focus_and_regent_mantle",
        }
        with self.assertRaisesRegex(RuntimeError, "expected effects mismatch"):
            TOOL.validate_content(changed)

    def test_rejects_missing_new_game_plus_idempotence_scenario(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["acceptance_scenarios"] = [
            scenario
            for scenario in changed["acceptance_scenarios"]
            if scenario["scenario_id"]
            != "new_game_plus_preserved_join_is_idempotent"
        ]
        with self.assertRaisesRegex(RuntimeError, "scenario inventory"):
            TOOL.validate_content(changed)

    def test_rejects_dangling_branch_reference(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["nodes"][0]["then"] = "missing_node"
        with self.assertRaisesRegex(RuntimeError, "unknown node reference"):
            TOOL.validate_content(changed)


if __name__ == "__main__":
    unittest.main()
