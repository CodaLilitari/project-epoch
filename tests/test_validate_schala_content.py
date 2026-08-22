from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
TOOL_PATH = TOOLS / "validate_schala_content.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("validate_schala_content", TOOL_PATH)


class ValidateSchalaContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.content = TOOL.load_content()

    def test_canonical_content_validates(self) -> None:
        TOOL.validate_content(self.content)

    def test_manifest_pins_original_unmapped_pack(self) -> None:
        result = TOOL.manifest(self.content)
        self.assertEqual(result["command_count"], 17)
        self.assertEqual(result["action_range"], [0x80, 0x90])
        self.assertEqual(
            result["canonical_sha256"],
            "90f43fb7602682911829a1077fb91b824a61e9071931eec1e0832c8a96590c2b",
        )
        self.assertEqual(
            result["kind_counts"],
            {"basic": 1, "dual": 6, "single": 8, "triple": 2},
        )
        self.assertFalse(result["native_bindings_present"])

    def test_every_command_matches_pinned_identity_layout(self) -> None:
        by_id = {
            command["action_id"]: command
            for command in self.content["commands"]
        }
        for layout in TOOL.schala_command_layout.COMMANDS:
            command = by_id[layout.action_id]
            self.assertEqual(command["design_name"], layout.design_name)
            self.assertEqual(command["ui_name"], layout.ui_name)
            self.assertEqual(tuple(command["participants"]), layout.participants)

    def test_rejects_untraced_native_binding(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["commands"][0]["primitive_binding"] = {"effect_id": 1}
        with self.assertRaisesRegex(RuntimeError, "trace approval"):
            TOOL.validate_content(changed)

    def test_rejects_participant_mp_mismatch(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["commands"][8]["mp_budget"] = {"7": 6}
        with self.assertRaisesRegex(RuntimeError, "participants"):
            TOOL.validate_content(changed)

    def test_rejects_provenance_that_imports_rom_data(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["provenance"]["rom_or_npc_data_imported"] = True
        with self.assertRaisesRegex(RuntimeError, "prohibited"):
            TOOL.validate_content(changed)

    def test_rejects_identity_drift(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["commands"][0]["ui_name"] = "Other"
        with self.assertRaisesRegex(RuntimeError, "disagrees"):
            TOOL.validate_content(changed)


if __name__ == "__main__":
    unittest.main()
