from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

AUDIT_PATH = (
    TOOLS_DIR / "audit_schala_focus_weapon_aux_adapter_boundaries.py"
)
REFERENCE_PATH = (
    ROOT
    / "references"
    / "schala_focus_weapon_aux_adapter_boundaries.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_focus_weapon_aux_adapter_boundaries",
    AUDIT_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class SchalaFocusWeaponAuxAdapterBoundaryTests(unittest.TestCase):
    def test_reference_contract_is_pinned_and_shape_is_exact(self) -> None:
        source = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(source), AUDIT.REFERENCE_SIZE)
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            AUDIT.REFERENCE_SHA256,
        )

        contract = AUDIT.load_reference_contract()
        AUDIT._validate_spec_geometry()
        self.assertEqual(
            [row["name"] for row in contract["regions"]],
            [spec.name for spec in AUDIT.REGION_SPECS],
        )
        self.assertEqual(
            [row["name"] for row in contract["bounded_preimages"]],
            [spec.name for spec in AUDIT.PREIMAGE_SPECS],
        )
        self.assertEqual(len(AUDIT.REGION_SPECS), 6)
        self.assertEqual(len(AUDIT.PREIMAGE_SPECS), 6)

    def test_auxiliary_tables_are_three_exact_consecutive_60_byte_extents(
        self,
    ) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        enemy_records = regions["enemy_attack_animation_records"]
        palette = regions["weapon_palette_index_values"]
        swing = regions["weapon_swing_sfx"]
        hit = regions["weapon_hit_sfx"]

        self.assertEqual(
            (enemy_records.entry_count, enemy_records.entry_width),
            (0x100, 6),
        )
        self.assertEqual(
            enemy_records.end_exclusive - enemy_records.start,
            0x600,
        )
        for table in (palette, swing, hit):
            self.assertEqual(
                (table.entry_count, table.entry_width),
                (0x60, 1),
            )
            self.assertEqual(table.end_exclusive - table.start, 0x60)
        self.assertEqual(palette.end_exclusive, swing.start)
        self.assertEqual(swing.end_exclusive, hit.start)
        self.assertEqual(hit.end_exclusive, 0xCD6E0C)

        payload = regions["weapon_palette_rows"]
        self.assertEqual(
            (payload.entry_count, payload.entry_width),
            (64, 6),
        )
        self.assertEqual(payload.end_exclusive - payload.start, 0x180)

    def test_focus_palette_overrun_owns_hit_sfx_entries_28_through_2b(
        self,
    ) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        palette = regions["weapon_palette_index_values"]
        hit = regions["weapon_hit_sfx"]

        self.assertEqual(
            tuple(row.weapon_id for row in AUDIT.PALETTE_COLLISIONS),
            AUDIT.FOCUS_WEAPON_IDS,
        )
        for index, collision in enumerate(AUDIT.PALETTE_COLLISIONS):
            with self.subTest(weapon_id=f"{collision.weapon_id:02X}"):
                self.assertEqual(
                    collision.lookup,
                    palette.start + collision.weapon_id,
                )
                self.assertFalse(
                    palette.start
                    <= collision.lookup
                    < palette.end_exclusive
                )
                self.assertTrue(
                    hit.start <= collision.lookup < hit.end_exclusive
                )
                self.assertEqual(
                    collision.owner_entry_index,
                    0x28 + index,
                )

    def test_focus_sfx_overruns_own_reachable_enemy_attack_package_bytes(
        self,
    ) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        preimages = {spec.name: spec for spec in AUDIT.PREIMAGE_SPECS}

        for table_name, collisions in (
            ("weapon_swing_sfx", AUDIT.SWING_COLLISIONS),
            ("weapon_hit_sfx", AUDIT.HIT_COLLISIONS),
        ):
            table = regions[table_name]
            for collision in collisions:
                with self.subTest(
                    table=table_name,
                    weapon_id=f"{collision.weapon_id:02X}",
                ):
                    owner = preimages[collision.owner_region]
                    self.assertEqual(
                        collision.lookup,
                        table.start + collision.weapon_id,
                    )
                    self.assertFalse(
                        table.start
                        <= collision.lookup
                        < table.end_exclusive
                    )
                    self.assertTrue(
                        owner.start
                        <= collision.lookup
                        < owner.end_exclusive
                    )
                    self.assertEqual(
                        collision.owner_byte_offset,
                        collision.lookup - owner.start,
                    )

        self.assertEqual(
            [
                (row.owner_selector_id, row.owner_byte_offset)
                for row in AUDIT.HIT_COLLISIONS
            ],
            [(2, 0x11), (2, 0x12), (2, 0x13), (3, 0)],
        )

    def test_enemy_attack_package_boundaries_and_reference_counts_are_pinned(
        self,
    ) -> None:
        contract = AUDIT.load_reference_contract()
        preimages = {spec.name: spec for spec in AUDIT.PREIMAGE_SPECS}

        self.assertEqual(
            AUDIT.BOUNDARY_OFFSETS,
            (0x6E0C, 0x6E4A, 0x6E83, 0x6E97, 0x6EAF),
        )
        self.assertEqual(
            (
                preimages["reachable_enemy_attack_package_00"].start,
                preimages[
                    "reachable_enemy_attack_package_00"
                ].end_exclusive,
            ),
            (0xCD6E0C, 0xCD6E4A),
        )
        self.assertEqual(
            (
                preimages["reachable_enemy_attack_package_02"].start,
                preimages[
                    "reachable_enemy_attack_package_02"
                ].end_exclusive,
            ),
            (0xCD6E83, 0xCD6E97),
        )
        self.assertEqual(
            (
                preimages["reachable_enemy_attack_package_03"].start,
                preimages[
                    "reachable_enemy_attack_package_03"
                ].end_exclusive,
            ),
            (0xCD6E97, 0xCD6EAF),
        )
        self.assertEqual(
            contract["attack_package_resolution"][
                "enemy_attack_selector_reference_counts"
            ],
            [
                {"selector_id": "00", "record_count": 3},
                {"selector_id": "01", "record_count": 2},
                {"selector_id": "02", "record_count": 1},
                {"selector_id": "03", "record_count": 90},
                {"selector_id": "04", "record_count": 4},
            ],
        )

    def test_consumer_sources_and_fixed_palette_banks_are_exact(self) -> None:
        contract = AUDIT.load_reference_contract()
        palette = contract["palette_consumers"]
        audio = contract["weapon_audio_consumers"]
        resolution = contract["attack_package_resolution"]

        self.assertEqual(
            (
                palette[0]["weapon_id_load_pc"],
                palette[0]["palette_index_lookup_pc"],
                palette[0]["palette_payload_consumer_pc"],
            ),
            ("CCE718", "CCE71C", "CCE739"),
        )
        self.assertEqual(
            (
                palette[1]["weapon_id_load_pc"],
                palette[1]["palette_index_lookup_pc"],
            ),
            ("C2F606", "C2F610"),
        )
        self.assertEqual(
            [
                (
                    row["helper_call_pc"],
                    row["mvn_pc"],
                    row["source_bank"],
                )
                for row in palette[1]["fixed_source_bank_callers"]
            ],
            [
                ("C28366", "C28369", "D1"),
                ("C2F5D6", "C2F5D9", "D1"),
            ],
        )
        self.assertEqual(audio["weapon_id_cache"]["cache_store_pc"], "C14349")
        self.assertEqual(
            [row["lookup_pc"] for row in audio["commands"]],
            ["C161EF", "C161F9"],
        )
        self.assertEqual(
            (
                resolution["selector_record_lookup_pc"],
                resolution["selector_store_pc"],
                resolution["selector_source"],
                resolution["offset_lookup_pc"],
                resolution["first_package_dereference_pc"],
            ),
            ("C144B4", "C144B8", "7E9877", "C14535", "C14541"),
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_rom_yields_only_bounded_hashes_and_geometry(
        self,
    ) -> None:
        before_stat = ROM_PATH.stat()
        rom = ROM_PATH.read_bytes()
        before_sha256 = hashlib.sha256(rom).hexdigest()

        result = AUDIT.audit_rom(rom)

        self.assertEqual(result["schema"], AUDIT.SCHEMA)
        self.assertEqual(result["evidence_level"], "verified-static")
        self.assertEqual(
            result["rom"]["sha256"],
            AUDIT.CANONICAL_ROM_SHA256,
        )
        self.assertEqual(
            [row["observed_sha256"] for row in result["regions"]],
            [spec.expected_sha256 for spec in AUDIT.REGION_SPECS],
        )
        self.assertEqual(
            [
                row["observed_sha256"]
                for row in result["bounded_preimages"]
            ],
            [spec.expected_sha256 for spec in AUDIT.PREIMAGE_SPECS],
        )
        self.assertEqual(
            [row["stored_offset"] for row in result["boundary_offsets"]],
            ["6E0C", "6E4A", "6E83", "6E97", "6EAF"],
        )
        self.assertEqual(
            [
                row["record_count"]
                for row in result[
                    "enemy_attack_selector_reference_counts"
                ]
            ],
            [3, 2, 1, 90, 4],
        )
        self.assertTrue(
            result["conclusion"][
                "reachable_enemy_attack_package_collision_proved"
            ]
        )
        self.assertFalse(
            result["conclusion"]["canonical_in_place_write_approved"]
        )
        self.assertFalse(
            result["conclusion"]["allocation_or_hook_approved"]
        )
        self.assertFalse(
            result["conclusion"]["source_only_descriptor_bound"]
        )
        self.assertFalse(
            result["conclusion"][
                "rom_save_state_trace_mutation_performed"
            ]
        )
        self.assertFalse(
            result["conclusion"]["patch_rom_or_output_file_emitted"]
        )

        self.assertEqual(
            hashlib.sha256(ROM_PATH.read_bytes()).hexdigest(),
            before_sha256,
        )
        after_stat = ROM_PATH.stat()
        self.assertEqual(after_stat.st_size, before_stat.st_size)
        self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_report_never_exposes_table_payload_or_rom_bytes(self) -> None:
        result = AUDIT.audit_rom(ROM_PATH.read_bytes())
        observed_hashes: list[str] = []

        def inspect(value: object) -> None:
            self.assertNotIsInstance(value, bytes)
            self.assertNotIsInstance(value, bytearray)
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "observed_sha256":
                        self.assertIsInstance(child, str)
                        observed_hashes.append(child)
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        inspect(result)
        self.assertEqual(
            observed_hashes,
            [
                *[spec.expected_sha256 for spec in AUDIT.REGION_SPECS],
                *[spec.expected_sha256 for spec in AUDIT.PREIMAGE_SPECS],
            ],
        )
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(str(ROM_PATH), serialized)
        self.assertNotIn('"sha1"', serialized)
        for forbidden_key in (
            '"observed_bytes"',
            '"observed_bytes_hex"',
            '"table_bytes"',
            '"payload_bytes"',
            '"raw_rom"',
            '"rom_bytes"',
            '"save_bytes"',
            '"state_bytes"',
            '"trace_bytes"',
            '"file_offset"',
        ):
            self.assertNotIn(forbidden_key, serialized)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_rom_identity_fails_closed_before_bounded_audit(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        mutated[0x100] ^= 0x01

        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "ROM hash does not match",
        ):
            AUDIT.audit_rom(bytes(mutated))
        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "expected 0x400000 ROM bytes",
        ):
            AUDIT.audit_rom(canonical[:-1])

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_every_region_and_preimage_fails_closed_on_byte_drift(
        self,
    ) -> None:
        canonical = ROM_PATH.read_bytes()

        for spec in AUDIT.REGION_SPECS:
            with self.subTest(region=spec.name):
                mutated = bytearray(canonical)
                mutated[AUDIT.snes_hirom_to_file(spec.start)] ^= 0x01
                with self.assertRaisesRegex(
                    AUDIT.FocusWeaponAuxBoundaryAuditError,
                    f"bounded region bytes drifted: {spec.name}",
                ):
                    AUDIT._region_observation(bytes(mutated), spec)

        for spec in AUDIT.PREIMAGE_SPECS:
            with self.subTest(preimage=spec.name):
                mutated = bytearray(canonical)
                mutated[AUDIT.snes_hirom_to_file(spec.start)] ^= 0x01
                with self.assertRaisesRegex(
                    AUDIT.FocusWeaponAuxBoundaryAuditError,
                    f"bounded preimage bytes drifted: {spec.name}",
                ):
                    AUDIT._preimage_observation(bytes(mutated), spec)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_boundary_offset_observation_fails_closed_independently(
        self,
    ) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        offset_region = {
            spec.name: spec for spec in AUDIT.REGION_SPECS
        }["attack_animation_package_offsets"]
        table_start = AUDIT.snes_hirom_to_file(offset_region.start)
        mutated[table_start + 8] ^= 0x01

        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "attack package boundary offset drifted: 04",
        ):
            AUDIT._observe_boundary_offsets(bytes(mutated))

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_enemy_selector_reference_counts_fail_closed_independently(
        self,
    ) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        enemy_region = {
            spec.name: spec for spec in AUDIT.REGION_SPECS
        }["enemy_attack_animation_records"]
        table_start = AUDIT.snes_hirom_to_file(enemy_region.start)
        first_selector_zero = next(
            index
            for index in range(0, enemy_region.entry_count * 6, 6)
            if mutated[table_start + index] == 0
        )
        mutated[table_start + first_selector_zero] = 0xFF

        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "enemy Attack-animation selector reference count drifted: 00",
        ):
            AUDIT._observe_enemy_selector_reference_counts(bytes(mutated))

    def test_contract_drift_duplicate_keys_and_bool_coercion_fail_closed(
        self,
    ) -> None:
        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["palette_consumers"][1]["fixed_source_bank_callers"][0][
            "source_bank"
        ] = "CE"
        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "palette_consumers",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["focus_lookup_collisions"]["swing_sfx"]["collisions"][0][
            "observed_bytes_hex"
        ] = "00"
        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "focus_lookup_collisions",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["attack_package_resolution"]["boundary_offsets"][4][
            "stored_offset"
        ] = "6EB0"
        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "attack_package_resolution",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["attack_package_resolution"][
            "enemy_attack_selector_reference_counts"
        ][3]["record_count"] = 89
        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "attack_package_resolution",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["regions"][0]["entry_count"] = True
        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "reference region contract drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        with self.assertRaisesRegex(
            AUDIT.FocusWeaponAuxBoundaryAuditError,
            "duplicate JSON key",
        ):
            AUDIT._reject_duplicate_keys([("scope", 1), ("scope", 2)])

    def test_cli_and_source_expose_no_write_destination(self) -> None:
        parser = AUDIT.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions},
            {"help", "rom", "compact"},
        )

        source = AUDIT_PATH.read_text(encoding="utf-8")
        for forbidden_write in (
            ".write_bytes(",
            ".write_text(",
            "open(\"wb\"",
            "open('wb'",
            "open(\"w\"",
            "open('w'",
            "open(\"a\"",
            "open('a'",
            "shutil.copy",
            "subprocess.",
        ):
            self.assertNotIn(forbidden_write, source)
        for forbidden_cli in (
            "--output",
            "--patch",
            "--state",
            "--save",
            "--trace",
        ):
            self.assertNotIn(forbidden_cli, source)


if __name__ == "__main__":
    unittest.main()
