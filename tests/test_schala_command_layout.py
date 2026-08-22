from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "schala_command_layout.py"


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "schala_command_layout",
        TOOL_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


class SchalaCommandLayoutTests(unittest.TestCase):
    def test_layout_validates(self) -> None:
        TOOL.validate_layout()

    def test_exact_id_assignment(self) -> None:
        self.assertEqual(
            {
                command.design_name: command.action_id
                for command in TOOL.COMMANDS
            },
            {
                "Astral Pin": 0x80,
                "Veil": 0x81,
                "Crescent Wake": 0x82,
                "Stillpoint": 0x83,
                "Recall": 0x84,
                "Sanctuary": 0x85,
                "Rift Bloom": 0x86,
                "Astral Gate": 0x87,
                "Horizon Arc": 0x88,
                "Quiet Heaven": 0x89,
                "Eventide": 0x8A,
                "Oathguard": 0x8B,
                "Phase Engine": 0x8C,
                "Star Pounce": 0x8D,
                "New Dawn": 0x8E,
                "Little Star": 0x8F,
                "Focus Pulse": 0x90,
            },
        )

    def test_does_not_consume_vanilla_gap_or_marker_ids(self) -> None:
        ids = {command.action_id for command in TOOL.COMMANDS}
        self.assertTrue(ids.isdisjoint(TOOL.PRESERVED_GAP_IDS))
        self.assertTrue(ids.isdisjoint(TOOL.MARKER_FAMILY))
        self.assertTrue(all(value > TOOL.VANILLA_LAST_ACTION_ID for value in ids))

    def test_all_ui_labels_fit_source_budget(self) -> None:
        self.assertTrue(
            all(
                len(command.ui_name) <= TOOL.MAX_UI_NAME_CHARS
                for command in TOOL.COMMANDS
            )
        )

    def test_manifest_is_json_ready(self) -> None:
        result = TOOL.manifest()
        self.assertEqual(result["extended_action_range"], [0x80, 0x90])
        self.assertEqual(len(result["commands"]), 17)

    def test_rejects_duplicate_or_noncontiguous_id(self) -> None:
        changed = list(TOOL.COMMANDS)
        changed[-1] = TOOL.dataclasses.replace(changed[-1], action_id=0x8F)
        with self.assertRaisesRegex(RuntimeError, "contiguous"):
            TOOL.validate_layout(tuple(changed))

    def test_rejects_ui_name_over_budget(self) -> None:
        changed = list(TOOL.COMMANDS)
        changed[0] = TOOL.dataclasses.replace(
            changed[0],
            ui_name="Way Too Long",
        )
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            TOOL.validate_layout(tuple(changed))


if __name__ == "__main__":
    unittest.main()
