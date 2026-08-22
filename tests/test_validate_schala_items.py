from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_schala_items.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("validate_schala_items", TOOL_PATH)


class ValidateSchalaItemsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.content = TOOL.load_content()

    def test_canonical_items_validate(self) -> None:
        TOOL.validate_content(self.content)

    def test_manifest_pins_candidate_namespace(self) -> None:
        result = TOOL.manifest(self.content)
        self.assertEqual(result["item_count"], 7)
        self.assertEqual(result["item_range"], [0xE8, 0xEE])
        self.assertEqual(
            result["canonical_sha256"],
            "dfa3f66d079a8921ff088b99f2ba507cf205525ab47fb11da609704e90c2fd85",
        )
        self.assertEqual(result["reserved_following_ids"], [0xEF, 0xF0, 0xF1])
        self.assertEqual(
            result["class_counts"],
            {"accessory": 1, "armor": 1, "key": 1, "weapon": 4},
        )
        self.assertFalse(result["native_bindings_present"])
        self.assertEqual(
            result["candidate_namespace_status"],
            TOOL.NAMESPACE_STATUS,
        )

    def test_rejects_changed_namespace_audit_evidence(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["candidate_namespace_evidence"][
            "computed_unresolved"
        ] = 1
        with self.assertRaisesRegex(RuntimeError, "audit evidence"):
            TOOL.validate_content(changed)

    def test_exact_item_assignment(self) -> None:
        self.assertEqual(
            {
                item["design_name"]: item["item_id"]
                for item in self.content["items"]
            },
            {
                "Glass Focus": 0xE8,
                "Tide Lens": 0xE9,
                "Night Prism": 0xEA,
                "Star of Zeal": 0xEB,
                "Regent Mantle": 0xEC,
                "Crescent Clasp": 0xED,
                "Pendant Shard": 0xEE,
            },
        )

    def test_schala_gear_uses_bit_zero_and_key_does_not(self) -> None:
        for item in self.content["items"]:
            expected = 0 if item["logical_class"] == "key" else 1
            self.assertEqual(item["equip_mask"], expected)

    def test_rejects_range_or_marker_collision(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["items"][-1]["item_id"] = 0xF0
        with self.assertRaisesRegex(RuntimeError, "battle marker"):
            TOOL.validate_content(changed)

    def test_rejects_untraced_native_binding(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["items"][0]["native_binding"] = {"weapon_record": 1}
        with self.assertRaisesRegex(RuntimeError, "trace approval"):
            TOOL.validate_content(changed)

    def test_rejects_provenance_that_imports_rom_data(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["provenance"]["copied_vanilla_records"] = True
        with self.assertRaisesRegex(RuntimeError, "prohibited"):
            TOOL.validate_content(changed)

    def test_rejects_equippable_or_sellable_pendant_shard(self) -> None:
        changed = copy.deepcopy(self.content)
        changed["items"][-1]["sellable"] = True
        with self.assertRaisesRegex(RuntimeError, "inert and unsellable"):
            TOOL.validate_content(changed)


if __name__ == "__main__":
    unittest.main()
