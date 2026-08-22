from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

TOOL_PATH = TOOLS_DIR / "audit_pc_init_record_schema.py"
DOCUMENT_PATH = ROOT / "docs" / "pc_init_record_schema_audit.md"
SPEC = importlib.util.spec_from_file_location(
    "audit_pc_init_record_schema", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)


def iter_mapping_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from iter_mapping_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from iter_mapping_keys(child)


class PcInitRecordSchemaAuditTests(unittest.TestCase):
    def test_primary_field_schema_covers_exactly_0x50_bytes(self) -> None:
        result = TOOL.validate_field_schema()
        self.assertEqual(result["record_size"], 0x50)
        self.assertEqual(result["coverage"], "$00-$4F")
        self.assertEqual(
            result["unmapped_fields"], ["unmapped_1c", "unmapped_4f"]
        )
        approved_evidence = {
            "verified-static",
            "verified-runtime",
            "documented",
            "hypothesis",
        }
        self.assertTrue(
            all(
                field["evidence"] in approved_evidence
                for field in TOOL.FIELD_SCHEMA
            )
        )

    def test_byte_01_decoding_preserves_low_nibble_as_unmapped(self) -> None:
        result = TOOL.decode_byte01(0x42)
        self.assertEqual(result["selected_high_nibble"]["bit"], "$40")
        self.assertEqual(result["selected_high_nibble"]["slot"], 1)
        self.assertEqual(result["low_nibble"], "$02")
        self.assertEqual(result["low_nibble_status"], "unmapped")

    def test_byte_01_selector_uses_engine_priority(self) -> None:
        result = TOOL.decode_byte01(0xF7)
        self.assertEqual(result["selected_high_nibble"]["bit"], "$80")
        self.assertEqual(result["selected_high_nibble"]["slot"], 0)
        self.assertEqual(result["low_nibble"], "$07")

    def test_starting_tech_mask_is_high_bit_first(self) -> None:
        self.assertEqual(
            [TOOL.expected_high_first_mask(count) for count in range(4)],
            [0x00, 0x80, 0xC0, 0xE0],
        )
        with self.assertRaisesRegex(TOOL.AuditError, "outside 0..8"):
            TOOL.expected_high_first_mask(9)

    def test_stat_projection_uses_actual_engine_growth_order(self) -> None:
        record = bytearray(TOOL.PC_RECORD_SIZE)
        record[0x12] = 11
        record[0x0D] = 12
        record[0x2F:0x36] = bytes((10, 20, 0, 30, 40, 50, 60))
        growth = bytes((10, 20, 0, 30, 40, 50, 60))

        result = TOOL.project_level_stats(record, growth)

        self.assertEqual(result["power"]["projected"], 11)
        self.assertEqual(result["stamina"]["projected"], 22)
        self.assertEqual(result["speed"]["projected"], 12)
        self.assertEqual(result["hit"]["projected"], 33)
        self.assertEqual(result["evade"]["projected"], 44)
        self.assertEqual(result["magic"]["projected"], 55)
        self.assertEqual(result["magic_defense"]["projected"], 66)
        self.assertFalse(result["speed"]["recomputed"])

    def test_pinned_disassembly_sources_and_anchors(self) -> None:
        result = TOOL.validate_disassembly_sources()
        self.assertEqual(result["commit"], TOOL.PINNED_DISASSEMBLY_COMMIT)
        self.assertEqual(set(result["files"]), set(TOOL.PINNED_SOURCE_HASHES))

    def test_rom_identity_gate_rejects_unpinned_input(self) -> None:
        with self.assertRaisesRegex(TOOL.AuditError, "SHA-1 mismatch"):
            TOOL.validate_canonical_rom(bytes(TOOL.CANONICAL_ROM_SIZE))

    def test_document_covers_critical_fields_and_routes(self) -> None:
        text = DOCUMENT_PATH.read_text(encoding="utf-8")
        for token in (
            "`+$01`",
            "`+$02`",
            "`+$16-$18`",
            "`+$2F-$35`",
            "`+$36-$4F`",
            "`$C2:956E`",
            "`$FD:B2DE`",
            "`$FD:B33F`",
            "`$C2:8839`",
            "`$FD:AE52`",
            "`$C1:B442`",
            "`$C1:F630`",
            "`$C1:F871`",
            "`$C1:F39A`",
            "`$C1:F29C`",
            "`$7E:283E-$7E:2856`",
            "event `$11C`",
        ):
            self.assertIn(token, text)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_audit_proves_record_and_table_invariants(self) -> None:
        result = TOOL.audit(ROM_PATH)
        tables = result["record_and_tables"]

        self.assertEqual(
            result["status"], "audit_only_no_pc07_record_installed"
        )
        self.assertEqual(
            tables["char_init"]["sha256"], TOOL.CHAR_INIT_SHA256
        )
        self.assertEqual(
            tables["compatibility_collision"]["record_07_status"],
            "not a vanilla PC record",
        )
        self.assertEqual(tables["byte_02"]["canonical_seed_set"], ("$80",))
        self.assertEqual(
            tables["growth_tables"]["stat"]["engine_order"],
            (
                "power",
                "stamina",
                "speed_ignored",
                "hit",
                "evade",
                "magic",
                "magic_defense",
            ),
        )
        self.assertEqual(
            tables["tech_points"]["u16_thresholds_per_row"], 8
        )
        attract = tables["fd_attract_hp_mp_overlay"]
        self.assertEqual(attract["pointer_table_address"], "$FD:B99C-$FD:B9A1")
        self.assertEqual(attract["pointer_count"], 3)
        self.assertEqual(
            attract["pointer_words"], ("$B9A2", "$B9DA", "$BA12")
        )
        self.assertEqual(attract["data_extent"], "$FD:B9A2-$FD:BA49")
        self.assertEqual(
            [
                row["file_offset"]
                for row in attract["bounded_seven_row_blocks"]
            ],
            ["0x3DB9A2", "0x3DB9DA", "0x3DBA12"],
        )
        self.assertTrue(
            all(
                row["record_plus_2d_matches_threshold"]
                for row in tables["tech_points"]["template_bindings"]
            )
        )
        combo = tables["combo_learn_group_index"]
        self.assertEqual(combo["live_group_count"], 25)
        self.assertEqual(combo["sentinel_record_index"], 25)
        self.assertEqual(combo["maximum_live_index"], 24)
        self.assertEqual(
            combo["maximum_effective_wram_address"], "$7E:2856"
        )
        self.assertEqual(combo["rock_flags_start"], "$7E:2857")
        self.assertFalse(combo["rock_flags_reachable_by_this_path"])
        self.assertEqual(combo["pc07_participant_group_count"], 0)
        self.assertEqual(
            combo["relocated_effective_wram_range"],
            "$7E:2CAE-$7E:2CC6",
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_join_overrides_are_explicit_and_bounded(self) -> None:
        result = TOOL.audit(ROM_PATH)["record_and_tables"]
        stat_exceptions = {
            (row["pc"], row["stat"])
            for row in result["growth_tables"]["stat"][
                "join_template_projection_exceptions"
            ]
        }
        self.assertEqual(
            stat_exceptions,
            {
                ("Marle", "evade"),
                ("Lucca", "evade"),
                ("Lucca", "magic"),
                ("Lucca", "magic_defense"),
                ("Robo", "hit"),
                ("Robo", "evade"),
                ("Magus", "hit"),
            },
        )
        self.assertEqual(
            result["experience"]["xp_to_next_exceptions"],
            [
                {
                    "pc_id": 6,
                    "pc": "Magus",
                    "level": 37,
                    "actual": 9200,
                    "shared_curve_at_level": 7940,
                    "matching_table_indices": [40],
                }
            ],
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_byte_02_seed_drift_fails_even_without_hash_gate(self) -> None:
        rom = bytearray(ROM_PATH.read_bytes())
        rom[TOOL.CHAR_INIT_FILE + 2] = 0
        with self.assertRaisesRegex(TOOL.AuditError, r"\+02"):
            TOOL.audit_record_tables(rom, check_hashes=False)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_zero_stat_growth_row_is_not_silently_repurposed(self) -> None:
        rom = bytearray(ROM_PATH.read_bytes())
        rom[
            TOOL.STAT_GROWTH_FILE
            + 7 * TOOL.STAT_GROWTH_ROW_SIZE
        ] = 1
        with self.assertRaisesRegex(TOOL.AuditError, "row 7"):
            TOOL.audit_record_tables(rom, check_hashes=False)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_combo_index_requires_one_final_sentinel(self) -> None:
        rom = bytearray(ROM_PATH.read_bytes())
        final_record = (
            TOOL.DUAL_TECH_REQ_FILE
            + (TOOL.DUAL_TECH_REQ_RECORD_COUNT - 1)
            * TOOL.DUAL_TECH_REQ_RECORD_SIZE
        )
        rom[final_record] = 0xFE
        with self.assertRaisesRegex(TOOL.AuditError, "sentinel"):
            TOOL.audit_combo_learn_group_index(
                rom, check_hashes=False
            )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_report_contains_no_raw_record_payload_key(self) -> None:
        result = TOOL.audit(ROM_PATH)
        keys = {str(key).lower() for key in iter_mapping_keys(result)}
        self.assertNotIn("raw", keys)
        self.assertNotIn("raw_bytes", keys)
        self.assertNotIn("records", keys)
        self.assertIn("semantic metadata only", result["copyright_boundary"])


if __name__ == "__main__":
    unittest.main()
