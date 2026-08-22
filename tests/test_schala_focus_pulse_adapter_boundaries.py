from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

AUDIT_PATH = TOOLS_DIR / "audit_schala_focus_pulse_adapter_boundaries.py"
REFERENCE_PATH = (
    ROOT / "references" / "schala_focus_pulse_adapter_boundaries.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_focus_pulse_adapter_boundaries",
    AUDIT_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class SchalaFocusPulseAdapterBoundaryTests(unittest.TestCase):
    def test_reference_contract_is_pinned_and_regions_are_exact(self) -> None:
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
        self.assertEqual(len(AUDIT.REGION_SPECS), 10)
        for spec in AUDIT.REGION_SPECS:
            self.assertEqual(
                spec.end_exclusive - spec.start,
                spec.entry_count * spec.entry_width,
            )

    def test_focus_action_90_collision_geometry_is_fail_closed(self) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        actions = regions["character_action_records"]
        properties = regions["tech_property_records"]
        lookup = actions.start + AUDIT.FOCUS_ACTION_ID * actions.entry_width

        self.assertEqual(actions.entry_count, 124)
        self.assertEqual(actions.entry_width, 11)
        self.assertEqual(lookup, 0xCC221B)
        self.assertFalse(actions.start <= lookup < actions.end_exclusive)
        self.assertTrue(properties.start <= lookup < properties.end_exclusive)
        self.assertEqual(
            divmod(lookup - properties.start, properties.entry_width),
            (18, 4),
        )
        self.assertEqual(AUDIT.ACTION_DIRECT_CONSUMERS[4], 0xC1D546)

    def test_focus_weapon_collisions_are_inside_enemy_records(self) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        configs = regions["weapon_attack_config_records"]
        enemy = regions["enemy_attack_animation_records"]

        self.assertEqual((configs.entry_count, configs.entry_width), (95, 15))
        self.assertEqual(len(AUDIT.WEAPON_BRANCHES), 3)
        self.assertEqual(
            [offset for _, offset, _ in AUDIT.WEAPON_BRANCHES],
            [0, 5, 10],
        )
        self.assertTrue(
            all(
                len(consumers) == 5
                for _, _, consumers in AUDIT.WEAPON_BRANCHES
            )
        )
        for collision in AUDIT.WEAPON_COLLISION_SPECS:
            with self.subTest(weapon_id=f"{collision.weapon_id:02X}"):
                lookup = (
                    configs.start
                    + collision.weapon_id * configs.entry_width
                )
                self.assertEqual(lookup, collision.lookup_start)
                self.assertEqual(
                    collision.lookup_end_exclusive - collision.lookup_start,
                    configs.entry_width,
                )
                self.assertTrue(
                    enemy.start
                    <= collision.lookup_start
                    < collision.lookup_end_exclusive
                    <= enemy.end_exclusive
                )

    def test_three_selector_extension_hits_tech_pointer_table(self) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        source = regions["pc_attack_selector_families"]
        resolver = regions["normal_attack_animation_offsets"]
        tech = regions["tech_animation_pointer_table"]

        self.assertEqual((source.entry_count, source.entry_width), (21, 1))
        self.assertEqual((resolver.entry_count, resolver.entry_width), (21, 2))
        self.assertEqual(AUDIT.FIRST_EXTENSION_SELECTORS, (0x13, 0x14, 0x15))
        self.assertTrue(
            resolver.start + 0x13 * 2 < resolver.end_exclusive
        )
        self.assertTrue(
            resolver.start + 0x14 * 2 < resolver.end_exclusive
        )
        self.assertEqual(
            resolver.start + 0x15 * 2,
            resolver.end_exclusive,
        )
        self.assertEqual(resolver.end_exclusive, tech.start)

    def test_downstream_fanout_geometry_and_consumers_are_exact(self) -> None:
        regions = {spec.name: spec for spec in AUDIT.REGION_SPECS}
        self.assertEqual(
            (
                regions["normal_attack_graphics_pointers"].entry_count,
                regions["normal_attack_graphics_pointers"].entry_width,
            ),
            (48, 2),
        )
        self.assertEqual(
            (
                regions["normal_attack_ce_animation_offsets"].entry_count,
                regions["normal_attack_ce_animation_offsets"].entry_width,
            ),
            (95, 2),
        )
        self.assertEqual(
            (
                regions["normal_attack_aux_frame_offsets"].entry_count,
                regions["normal_attack_aux_frame_offsets"].entry_width,
            ),
            (95, 2),
        )
        self.assertEqual(
            AUDIT.FANOUT_SPECS,
            (
                (
                    0x7E987E,
                    "normal_attack_graphics_pointers",
                    0xC14408,
                    0x7E987F,
                ),
                (
                    0x7E9884,
                    "normal_attack_ce_animation_offsets",
                    0xC14420,
                    0x7E9885,
                ),
                (
                    0x7E9881,
                    "normal_attack_aux_frame_offsets",
                    0xC14414,
                    0x7E9882,
                ),
            ),
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_rom_yields_bounded_hashes_and_lookup_facts(self) -> None:
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
        selector = result["bounded_lookup_facts"][
            "normal_attack_selectors"
        ]
        self.assertEqual(
            (
                selector["vanilla_selector_min"],
                selector["vanilla_selector_max"],
                selector["vanilla_unique_selector_count"],
            ),
            ("00", "12", 19),
        )
        self.assertEqual(
            result["bounded_lookup_facts"]["focus_action_collision"][
                "lookup_snes_address"
            ],
            "CC221B",
        )
        self.assertEqual(
            [
                row["lookup_snes_start"]
                for row in result["bounded_lookup_facts"][
                    "focus_weapon_collisions"
                ]
            ],
            ["CD4DAD", "CD4DBC", "CD4DCB", "CD4DDA"],
        )
        self.assertFalse(
            result["conclusion"]["canonical_in_place_write_approved"]
        )
        self.assertFalse(
            result["conclusion"][
                "rom_save_state_trace_mutation_performed"
            ]
        )
        self.assertFalse(
            result["conclusion"]["patch_rom_or_output_file_emitted"]
        )
        self.assertEqual(hashlib.sha256(ROM_PATH.read_bytes()).hexdigest(), before_sha256)
        after_stat = ROM_PATH.stat()
        self.assertEqual(after_stat.st_size, before_stat.st_size)
        self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_report_never_exposes_table_or_rom_bytes(self) -> None:
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
            [spec.expected_sha256 for spec in AUDIT.REGION_SPECS],
        )
        self.assertTrue(all(len(value) == 64 for value in observed_hashes))

        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(str(ROM_PATH), serialized)
        self.assertNotIn('"sha1"', serialized)
        self.assertNotIn('"sha1"', REFERENCE_PATH.read_text(encoding="utf-8"))
        for forbidden_key in (
            '"observed_bytes"',
            '"observed_bytes_hex"',
            '"table_bytes"',
            '"raw_rom"',
            '"rom_bytes"',
            '"save_bytes"',
            '"state_bytes"',
            '"trace_bytes"',
            '"file_offset"',
        ):
            self.assertNotIn(forbidden_key, serialized)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_rom_identity_fails_closed_before_region_audit(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        mutated[0x100] ^= 0x01

        with self.assertRaisesRegex(
            AUDIT.FocusPulseBoundaryAuditError,
            "ROM hash does not match",
        ):
            AUDIT.audit_rom(bytes(mutated))
        with self.assertRaisesRegex(
            AUDIT.FocusPulseBoundaryAuditError,
            "expected 0x400000 ROM bytes",
        ):
            AUDIT.audit_rom(canonical[:-1])

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_every_bounded_region_preimage_fails_closed(self) -> None:
        canonical = ROM_PATH.read_bytes()
        identity = {
            "identity": "test identity gate bypass",
            "size": len(canonical),
            "sha1": AUDIT.CANONICAL_ROM_SHA1,
            "sha256": AUDIT.CANONICAL_ROM_SHA256,
        }

        for spec in AUDIT.REGION_SPECS:
            with self.subTest(region=spec.name):
                mutated = bytearray(canonical)
                mutated[AUDIT.snes_hirom_to_file(spec.start)] ^= 0x01
                with mock.patch.object(
                    AUDIT,
                    "validate_canonical_rom",
                    return_value=identity,
                ):
                    with self.assertRaisesRegex(
                        AUDIT.FocusPulseBoundaryAuditError,
                        f"bounded region bytes drifted: {spec.name}",
                    ):
                        AUDIT.audit_rom(bytes(mutated))

    def test_contract_drift_and_duplicate_keys_fail_closed(self) -> None:
        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["normal_attack_selector_boundary"][
            "resolver_direct_consumer_pc"
        ] = "C1442D"
        with self.assertRaisesRegex(
            AUDIT.FocusPulseBoundaryAuditError,
            "reference selector boundary drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["weapon_attack_config"]["record_geometry"][
            "branch_destinations"
        ][0] = "7E9879"
        with self.assertRaisesRegex(
            AUDIT.FocusPulseBoundaryAuditError,
            "reference weapon config geometry drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["weapon_attack_config"]["focus_weapon_collisions"][0][
            "observed_bytes_hex"
        ] = "00"
        with self.assertRaisesRegex(
            AUDIT.FocusPulseBoundaryAuditError,
            "reference Focus weapon collision keys drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        with self.assertRaisesRegex(
            AUDIT.FocusPulseBoundaryAuditError,
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
