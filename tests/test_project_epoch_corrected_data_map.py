from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = (
    ROOT
    / "references"
    / "project_epoch_corrected_character_data_map_v1.json"
)
DOC_PATH = ROOT / "docs" / "project_epoch_corrected_character_data_map_v1.md"
LEGACY_ATLAS_PATH = ROOT / "references" / "project_epoch_character_data_atlas_v0.md"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_map() -> dict[str, object]:
    return json.loads(
        MAP_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


class ProjectEpochCorrectedDataMapTests(unittest.TestCase):
    def test_metadata_sources_and_scope_are_pinned(self) -> None:
        data = load_map()
        self.assertEqual(
            data["schema"], "project-epoch-corrected-character-data-map-v1"
        )
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["status"], "canonical-current")
        self.assertEqual(data["as_of"], "2026-08-24")
        self.assertEqual(data["canonical_rom"]["size"], 0x400000)
        self.assertEqual(
            data["canonical_rom"]["sha256"],
            "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9",
        )
        self.assertIn("not a complete ROM", data["scope"]["completeness_claim"])
        self.assertIn(
            "supported-slot emulator replay",
            data["scope"]["research_change"],
        )

        source_ids = [source["id"] for source in data["sources"]]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        runtime_source = next(
            source
            for source in data["sources"]
            if source["id"] == "schala-npc-supported-slot-runtime"
        )
        self.assertEqual(
            runtime_source,
            {
                "id": "schala-npc-supported-slot-runtime",
                "kind": "canonical-rom-and-runtime-audit",
                "path": "docs/schala_vanilla_npc_supported_slot_smoke_v0.md",
            },
        )
        allowed_source_kinds = {
            "project-document",
            "canonical-rom-audit",
            "canonical-rom-and-runtime-audit",
            "deterministic-source-contract",
            "canonical-rom-audit-and-source-contract",
        }
        root_resolved = ROOT.resolve()
        for source in data["sources"]:
            source_path = Path(source["path"])
            self.assertFalse(source_path.is_absolute())
            resolved = (ROOT / source_path).resolve()
            self.assertTrue(resolved.is_relative_to(root_resolved))
            self.assertTrue(resolved.is_file(), source["path"])
            self.assertIn(source["kind"], allowed_source_kinds)

        for detail_name, source_id in data["detail_table_sources"].items():
            self.assertIn(detail_name, data)
            self.assertIn(source_id, source_ids)

    def test_entry_ids_enums_evidence_and_sources_are_closed(self) -> None:
        data = load_map()
        entries = data["entries"]
        self.assertGreaterEqual(len(entries), 32)
        entry_ids = [entry["id"] for entry in entries]
        self.assertEqual(len(entry_ids), len(set(entry_ids)))

        allowed_evidence = set(data["evidence_levels"])
        allowed_accuracy = set(data["historical_accuracy_values"])
        allowed_applicability = set(data["project_epoch_applicability_values"])
        allowed_status = set(data["map_status_values"])
        source_ids = {source["id"] for source in data["sources"]}

        for entry in entries:
            self.assertRegex(entry["id"], r"^[a-z0-9]+(?:[.-][a-z0-9]+)+$")
            self.assertIn(entry["historical_accuracy"], allowed_accuracy)
            self.assertIn(
                entry["project_epoch_applicability"], allowed_applicability
            )
            self.assertIn(entry["map_status"], allowed_status)
            self.assertTrue(entry["historical_comparison"])
            self.assertTrue(entry["vanilla_ownership"])
            self.assertTrue(entry["pc07_consequence"])
            self.assertTrue(entry["required_action"])
            self.assertTrue(entry["evidence"])
            self.assertTrue(entry["sources"])
            self.assertTrue(set(entry["sources"]).issubset(source_ids))
            for assertion in entry["evidence"]:
                self.assertIn(assertion["level"], allowed_evidence)
                self.assertTrue(assertion["statement"])

    def test_all_absolute_locations_have_exact_half_open_geometry(self) -> None:
        data = load_map()
        allowed_spaces = set(data["address_spaces"])
        all_locations = [
            location
            for entry in data["entries"]
            for location in entry["locations"]
        ]
        all_locations.extend(data["pc_graphics_windows"])
        all_locations.extend(data["pc_assembly_windows"])
        all_locations.extend(data["pc_animation_windows"])

        for location in all_locations:
            self.assertIn(location["space"], allowed_spaces)
            width = 4 if location["space"] == "sram-slot-relative" else 6
            self.assertRegex(location["start"], rf"^[0-9A-F]{{{width}}}$")
            self.assertRegex(
                location["end_exclusive"], rf"^[0-9A-F]{{{width}}}$"
            )
            start = int(location["start"], 16)
            end = int(location["end_exclusive"], 16)
            self.assertGreater(end, start)
            self.assertEqual(location["size"], end - start, location)
            if location["space"] == "wram":
                self.assertGreaterEqual(start, 0x7E0000)
                self.assertLessEqual(end, 0x800000)
            if location["space"] == "snes-rom-bus":
                self.assertGreaterEqual(start, 0xC00000)
                self.assertLessEqual(end, 0x1000000)
            if location["space"] == "sram-slot-relative":
                self.assertLessEqual(end, 0x0A00)
            if location["space"] == "rom-file-headerless":
                self.assertGreaterEqual(start, 0)
                self.assertLessEqual(end, data["canonical_rom"]["size"])
            if location["space"] == "expanded-exhirom-file":
                self.assertGreaterEqual(start, 0x400000)
                self.assertLessEqual(end, data["expanded_scaffold"]["size"])
            if location["space"] == "sram-bus":
                self.assertGreaterEqual(start, 0x306000)
                self.assertLessEqual(end, 0x308000)

    def test_pc_record_schema_is_contiguous_exactly_0050_bytes(self) -> None:
        data = load_map()
        rows = data["pc_record_schema"]
        allowed_evidence = set(data["evidence_levels"])
        cursor = 0
        for row in rows:
            start = int(row["start"], 16)
            end = int(row["end_exclusive"], 16)
            self.assertEqual(start, cursor, row)
            self.assertGreater(end, start)
            self.assertEqual(row["size"], end - start)
            self.assertIn(row["evidence"], allowed_evidence)
            cursor = end
        self.assertEqual(cursor, 0x50)

        by_start = {row["start"]: row for row in rows}
        self.assertIn("logical and portrait", by_start["00"]["meaning"])
        self.assertIn("base max MP", by_start["09"]["meaning"])
        self.assertIn("base Magic", by_start["0E"]["meaning"])
        self.assertIn("base Hit", by_start["0F"]["meaning"])
        self.assertIn("unmapped tail", by_start["4F"]["meaning"])

    def test_graphics_and_assembly_windows_are_seven_pc_hash_metadata(self) -> None:
        data = load_map()
        expected_pcs = {"Crono", "Marle", "Lucca", "Robo", "Frog", "Ayla", "Magus"}
        for key in (
            "pc_graphics_windows",
            "pc_assembly_windows",
            "pc_animation_windows",
        ):
            rows = data[key]
            self.assertEqual({row["pc"] for row in rows}, expected_pcs)
            self.assertEqual(len(rows), 7)
            for row in rows:
                self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
        robo = next(
            row for row in data["pc_assembly_windows"] if row["pc"] == "Robo"
        )
        self.assertIn("minimum", robo["qualification"])
        self.assertEqual(
            sum(row["tiles"] for row in data["pc_graphics_windows"]), 7264
        )
        magus_animation = next(
            row for row in data["pc_animation_windows"] if row["pc"] == "Magus"
        )
        self.assertEqual(
            (magus_animation["start"], magus_animation["end_exclusive"]),
            ("E44B00", "E44ED0"),
        )
        self.assertEqual(magus_animation["bytes_per_facing"], 0xF4)

    def test_high_risk_historical_corrections_remain_fail_closed(self) -> None:
        entries = {entry["id"]: entry for entry in load_map()["entries"]}

        records = entries["save.pc-records-and-compatibility-block"]
        self.assertIn("not Epoch", records["vanilla_ownership"])
        self.assertEqual(records["locations"][0]["end_exclusive"], "0430")
        self.assertEqual(records["locations"][1]["start"], "0430")

        serializer = entries["save.serializer-and-0480"]
        self.assertEqual(serializer["map_status"], "rejected-allocation")
        self.assertIn("0480", serializer["pc07_consequence"])

        growth = entries["growth.hp-mp-stat-tp-families"]
        self.assertEqual(growth["locations"][1]["start"], "CC25C2")
        self.assertIn("MP-growth", growth["locations"][1]["role"])

        melchior = entries["graphics.melchior-npc-descriptor-collision"]
        self.assertIn("NPC", melchior["title"])
        self.assertIn("not proof that Melchior was a PC", melchior["vanilla_ownership"])
        self.assertEqual(melchior["locations"][0]["start"], "E4F023")

        selectors = entries["attack.animation-selector-families"]
        self.assertIn("Crono", selectors["vanilla_ownership"])
        self.assertEqual(selectors["map_status"], "negative-control")

        reserve = entries["battle.id-to-slot-and-reserve-xp"]
        self.assertEqual(reserve["locations"][0]["end_exclusive"], "7EB1C5")
        self.assertEqual(reserve["locations"][1]["start"], "C1F9EB")
        self.assertIn("stops before 07", reserve["vanilla_ownership"])

        tech_state = entries["tech.progress-learned-and-combo-state"]
        self.assertEqual(tech_state["locations"][-1]["start"], "7E2857")
        self.assertEqual(tech_state["locations"][-1]["end_exclusive"], "7E285C")

        tech_tables = entries["tech.names-targets-properties-mp-costs"]
        by_role = {location["role"]: location for location in tech_tables["locations"]}
        property_row = next(
            location
            for role, location in by_role.items()
            if "property records" in role
        )
        self.assertEqual(
            (property_row["start"], property_row["end_exclusive"]),
            ("CC213F", "CC249F"),
        )
        self.assertTrue(
            any(
                location["start"] == "CC253B" and location["size"] == 1
                for location in tech_tables["locations"]
            )
        )

        package = entries["tech.animation-package-selector-namespace"]
        self.assertIn("creates no mapping", package["pc07_consequence"])

        expansion = entries["expansion.exhirom-map-mode-boundary"]
        self.assertEqual(expansion["locations"][0]["space"], "expanded-exhirom-file")

        palette = entries["graphics.palette-and-overworld-paths"]
        self.assertIn("schala-npc-supported-slot-runtime", palette["sources"])
        runtime_statement = next(
            assertion["statement"]
            for assertion in palette["evidence"]
            if assertion["level"] == "verified-runtime"
        )
        self.assertIn("matched clean controls", runtime_statement)
        self.assertIn("Lucca's supported field path", runtime_statement)
        self.assertIn("without establishing PC 07", runtime_statement)

    def test_markdown_parity_supersession_and_privacy_boundaries(self) -> None:
        data = load_map()
        markdown = DOC_PATH.read_text(encoding="utf-8")
        legacy = LEGACY_ATLAS_PATH.read_text(encoding="utf-8")

        expected_entry_ids = {entry["id"] for entry in data["entries"]}
        ledger_statuses: dict[str, str] = {}
        for line in markdown.splitlines():
            if not line.startswith("| `"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != 4:
                continue
            entry_id = cells[0].strip("`")
            if entry_id in expected_entry_ids:
                ledger_statuses[entry_id] = cells[3].strip("`")

        for entry in data["entries"]:
            self.assertIn(f"`{entry['id']}`", markdown)
            self.assertEqual(ledger_statuses.get(entry["id"]), entry["map_status"])
        self.assertEqual(len(ledger_statuses), len(data["entries"]))
        self.assertIn("Superseded historical planning artifact", legacy)
        self.assertIn("must not be executed", legacy)
        self.assertIn("project_epoch_corrected_character_data_map_v1", legacy)

        public_text = MAP_PATH.read_text(encoding="utf-8") + markdown + legacy[:1800]
        self.assertNotRegex(public_text, r"[A-Za-z]:\\")
        self.assertNotRegex(public_text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
        for forbidden in (
            '"rom_bytes"',
            '"save_bytes"',
            '"state_bytes"',
            '"raw_trace"',
            '"payload_hex"',
            '"credential"',
        ):
            self.assertNotIn(forbidden, public_text)


if __name__ == "__main__":
    unittest.main()
