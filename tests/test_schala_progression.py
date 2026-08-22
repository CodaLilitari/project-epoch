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
TOOL_PATH = TOOLS_DIR / "schala_progression.py"
SPEC = importlib.util.spec_from_file_location("schala_progression", TOOL_PATH)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = TOOL.load_content()
        cls.descriptor = TOOL.descriptor_from_content(cls.content)
        cls.encoded = TOOL.encode_descriptor(cls.descriptor)

    def test_source_is_original_and_explicitly_unmapped(self) -> None:
        self.assertEqual(
            self.content["content_origin"], "project-epoch-original"
        )
        self.assertEqual(
            self.content["rom_encoding_status"], "authoring-only-unmapped"
        )
        provenance = self.content["provenance"]
        self.assertFalse(provenance["rom_or_npc_data_imported"])
        self.assertFalse(provenance["copied_vanilla_record"])
        self.assertFalse(provenance["copied_vanilla_growth_row"])

    def test_overlay_is_fixed_size_and_hash_pinned(self) -> None:
        self.assertEqual(len(self.encoded), 0x48)
        self.assertEqual(
            TOOL.sha256(self.encoded),
            "b95a0a3d8397706f2c83472539ee208ebaef1af3e9e6057691b0b1c00dedaaff",
        )
        report = TOOL.manifest(self.content)
        self.assertEqual(
            report["source_normalized_sha256"],
            "17e25577bfb80998e33c5ac0890147231a5e1d3674de8af97e6fdf242f51aab5",
        )
        self.assertFalse(report["vanilla_character_record"])
        self.assertFalse(report["rom_installable"])

    def test_descriptor_round_trips_and_rejects_reserved_bytes(self) -> None:
        self.assertEqual(
            TOOL.decode_descriptor(self.encoded), self.descriptor
        )
        corrupt = bytearray(self.encoded)
        corrupt[0x17] = 1
        with self.assertRaisesRegex(TOOL.ProgressionError, "reserved"):
            TOOL.decode_descriptor(bytes(corrupt))

    def test_recruitment_level_uses_clamped_party_median(self) -> None:
        self.assertEqual(
            TOOL.select_recruitment_level([], self.descriptor), 35
        )
        self.assertEqual(
            TOOL.select_recruitment_level([12, 20, 25], self.descriptor), 30
        )
        self.assertEqual(
            TOOL.select_recruitment_level([32, 37, 41], self.descriptor), 37
        )
        self.assertEqual(
            TOOL.select_recruitment_level([70, 50, 60], self.descriptor), 45
        )

    def test_authored_growth_has_expected_midgame_profiles(self) -> None:
        self.assertEqual(
            TOOL.STAT_NAMES,
            (
                "power",
                "stamina",
                "speed",
                "hit",
                "evade",
                "magic",
                "magic_defense",
            ),
        )
        self.assertEqual(
            self.descriptor.base_stats,
            (2, 5, 10, 7, 9, 10, 10),
        )
        self.assertEqual(
            self.descriptor.stat_growth,
            (25, 65, 0, 30, 45, 105, 150),
        )
        level_35 = TOOL.project_level(35, self.descriptor)
        self.assertEqual(level_35["hp"], 510)
        self.assertEqual(level_35["mp"], 77)
        self.assertEqual(
            level_35["stats"],
            {
                "power": 10,
                "stamina": 27,
                "speed": 10,
                "magic": 45,
                "hit": 17,
                "evade": 24,
                "magic_defense": 61,
            },
        )
        level_37 = TOOL.project_level(37, self.descriptor)
        self.assertEqual(level_37["hp"], 540)
        self.assertEqual(level_37["mp"], 79)
        self.assertEqual(level_37["stats"]["magic"], 47)
        self.assertEqual(level_37["stats"]["power"], 11)

    def test_caps_are_respected_at_level_99(self) -> None:
        level_99 = TOOL.project_level(99, self.descriptor)
        self.assertEqual(level_99["hp"], 999)
        self.assertEqual(level_99["mp"], 99)
        self.assertEqual(level_99["stats"]["magic"], 99)
        self.assertEqual(level_99["stats"]["magic_defense"], 99)
        self.assertEqual(level_99["stats"]["speed"], 10)

    def test_tech_progress_uses_high_bit_mask_and_delta_costs(self) -> None:
        tech = self.content["single_tech_progression"]
        self.assertEqual(tech["starting_learned_count"], 3)
        self.assertEqual(tech["starting_learned_mask"], 0xE0)
        self.assertEqual(
            tech["engine_step_costs"], [0, 0, 0, 100, 150, 250, 400, 500]
        )
        self.assertEqual(self.descriptor.initial_tp_to_next, 100)
        bad = dataclasses.replace(
            self.descriptor, starting_learned_mask=0x07
        )
        with self.assertRaisesRegex(TOOL.ProgressionError, "mask"):
            TOOL.encode_descriptor(bad)

    def test_starting_loadout_uses_only_original_item_ids(self) -> None:
        self.assertEqual(
            self.descriptor.starting_loadout,
            (TOOL.NO_ITEM, 0xEC, 0xE8, TOOL.NO_ITEM),
        )

    def test_all_runtime_gates_remain_named(self) -> None:
        self.assertEqual(
            set(self.content["runtime_gates"]), TOOL.KNOWN_RUNTIME_GATES
        )
        self.assertIn(
            "record_byte_01_semantics", self.content["runtime_gates"]
        )
        self.assertIn(
            "save_and_load_round_trip", self.content["runtime_gates"]
        )


if __name__ == "__main__":
    unittest.main()
