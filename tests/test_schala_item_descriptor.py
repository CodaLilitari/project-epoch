from __future__ import annotations

import dataclasses
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "schala_item_descriptor.py"
SPEC = importlib.util.spec_from_file_location(
    "schala_item_descriptor", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaItemDescriptorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = TOOL.items.load_content()
        cls.table, cls.descriptors = TOOL.build_unbound_table(cls.content)

    def test_table_has_seven_fixed_size_original_records(self) -> None:
        self.assertEqual(len(self.descriptors), 7)
        self.assertEqual(len(self.table), 0xE0)
        self.assertEqual(
            [value.item_id for value in self.descriptors],
            list(range(0xE8, 0xEF)),
        )

    def test_every_descriptor_round_trips(self) -> None:
        for descriptor in self.descriptors:
            encoded = TOOL.encode_descriptor(descriptor)
            self.assertEqual(len(encoded), TOOL.DESCRIPTOR_SIZE)
            self.assertEqual(TOOL.decode_descriptor(encoded), descriptor)

    def test_manifest_pins_unbound_table(self) -> None:
        result = TOOL.manifest(self.content)
        self.assertEqual(result["descriptor_size"], 0x20)
        self.assertEqual(result["descriptor_count"], 7)
        self.assertEqual(result["table_size"], 0xE0)
        self.assertEqual(
            result["table_sha256"],
            "b3b5b267ee60e69d8506897092289134d176592264207f1918c7a5459873fc1a",
        )
        self.assertFalse(result["description_pointers_bound"])
        self.assertFalse(result["weapon_visual_pointers_bound"])
        self.assertFalse(result["rom_installable"])

    def test_focus_weapons_have_distinct_visual_ids_and_direct_magic(self):
        weapons = [
            value
            for value in self.descriptors
            if value.logical_class == TOOL.CLASS_IDS["weapon"]
        ]
        self.assertEqual(
            [value.focus_visual_id for value in weapons], [0, 1, 2, 3]
        )
        self.assertEqual(
            [value.magic_amount for value in weapons], [1, 2, 3, 5]
        )
        self.assertTrue(
            all(value.stat_mask == TOOL.STAT_MAGIC for value in weapons)
        )

    def test_crescent_clasp_keeps_independent_stat_amounts(self) -> None:
        clasp = self.descriptors[5]
        self.assertEqual(
            clasp.stat_mask,
            TOOL.STAT_MAGIC | TOOL.STAT_MAGIC_DEFENSE,
        )
        self.assertEqual(clasp.magic_amount, 4)
        self.assertEqual(clasp.magic_defense_amount, 4)

    def test_pendant_shard_is_inert_key_item(self) -> None:
        shard = self.descriptors[-1]
        self.assertEqual(shard.logical_class, TOOL.CLASS_IDS["key"])
        self.assertEqual(shard.flags, TOOL.FLAG_KEY_ITEM)
        self.assertEqual(shard.equip_mask, 0)
        self.assertEqual(shard.focus_visual_id, TOOL.NO_FOCUS_VISUAL)

    def test_unknown_flags_and_reserved_bytes_are_rejected(self) -> None:
        with self.assertRaisesRegex(TOOL.ItemDescriptorError, "unknown"):
            TOOL.encode_descriptor(
                dataclasses.replace(
                    self.descriptors[0],
                    flags=self.descriptors[0].flags | 0x80,
                )
            )
        encoded = bytearray(TOOL.encode_descriptor(self.descriptors[0]))
        encoded[-1] = 1
        with self.assertRaisesRegex(TOOL.ItemDescriptorError, "reserved"):
            TOOL.decode_descriptor(bytes(encoded))

    def test_unbound_pointers_are_explicit_and_u24_checked(self) -> None:
        self.assertTrue(
            all(
                value.description_ptr == 0
                and value.weapon_visual_ptr == 0
                for value in self.descriptors
            )
        )
        with self.assertRaisesRegex(
            TOOL.ItemDescriptorError, "three bytes"
        ):
            TOOL.encode_descriptor(
                dataclasses.replace(
                    self.descriptors[0], description_ptr=0x1000000
                )
            )


if __name__ == "__main__":
    unittest.main()
