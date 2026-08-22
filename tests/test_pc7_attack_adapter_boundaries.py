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

AUDIT_PATH = TOOLS_DIR / "audit_pc7_attack_adapter_boundaries.py"
REFERENCE_PATH = ROOT / "references" / "pc7_attack_adapter_boundaries.json"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_pc7_attack_adapter_boundaries",
    AUDIT_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class Pc7AttackAdapterBoundaryTests(unittest.TestCase):
    def test_reference_contract_is_pinned_and_geometry_is_exact(self) -> None:
        source = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(source), AUDIT.REFERENCE_SIZE)
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            AUDIT.REFERENCE_SHA256,
        )

        contract = AUDIT.load_reference_contract()
        AUDIT._validate_spec_geometry()

        self.assertEqual(
            [row["name"] for row in contract["tables"]],
            [spec.name for spec in AUDIT.TABLE_SPECS],
        )
        self.assertEqual(
            sum(spec.entry_count for spec in AUDIT.TABLE_SPECS),
            36,
        )

    def test_pc07_boundary_chain_is_explicit_and_non_free(self) -> None:
        by_name = {spec.name: spec for spec in AUDIT.TABLE_SPECS}

        self.assertEqual(
            by_name["basic_attack_action_ids"].pc7_address,
            0xCC258A,
        )
        self.assertEqual(
            by_name["basic_attack_action_ids"].collision_name,
            "hp_growth_table",
        )
        self.assertTrue(by_name["attack_approach_policy"].pc7_in_extent)
        self.assertEqual(
            by_name["attack_approach_policy"].branch_behavior,
            "nonzero-forces-pathfind",
        )
        self.assertEqual(
            by_name["pc_attack_anim_ids_a"].pc7_address,
            by_name["pc_attack_anim_ids_pathfind_success"].start,
        )
        self.assertEqual(
            by_name[
                "pc_attack_anim_ids_pathfind_success"
            ].pc7_address,
            by_name["pc_attack_anim_ids_b_critical"].start,
        )
        self.assertEqual(
            by_name["pc_attack_anim_ids_b_critical"].pc7_address,
            0xCD4015,
        )
        for spec in AUDIT.TABLE_SPECS:
            if not spec.pc7_in_extent:
                self.assertEqual(spec.pc7_address, spec.end_exclusive)
                self.assertEqual(spec.classification, "fallthrough-collision")

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_rom_yields_only_bounded_observations(self) -> None:
        rom = ROM_PATH.read_bytes()
        before = hashlib.sha256(rom).hexdigest()

        result = AUDIT.audit_rom(rom)

        self.assertEqual(result["schema"], AUDIT.SCHEMA)
        self.assertEqual(result["evidence_level"], "verified-static")
        self.assertEqual(result["rom"]["sha1"], AUDIT.CANONICAL_ROM_SHA1)
        self.assertEqual(
            result["rom"]["sha256"],
            AUDIT.CANONICAL_ROM_SHA256,
        )
        self.assertEqual(
            [row["observed_sha256"] for row in result["tables"]],
            [spec.expected_sha256 for spec in AUDIT.TABLE_SPECS],
        )
        self.assertEqual(
            [
                row["pc07_lookup"]["observed_byte_hex"]
                for row in result["tables"]
            ],
            [
                f"{spec.pc7_expected:02x}"
                for spec in AUDIT.TABLE_SPECS
            ],
        )
        self.assertEqual(
            [
                row["pc07_lookup"]["classification"]
                for row in result["tables"]
            ],
            [spec.classification for spec in AUDIT.TABLE_SPECS],
        )
        self.assertFalse(
            result["conclusion"]["in_place_eighth_entry_writes_approved"]
        )
        self.assertTrue(
            result["conclusion"]["expanded_adapter_required"]
        )
        self.assertFalse(
            result["conclusion"]["rom_save_state_mutation_performed"]
        )
        self.assertFalse(result["conclusion"]["patch_or_rom_emitted"])
        self.assertEqual(hashlib.sha256(rom).hexdigest(), before)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_output_exposes_only_table_hashes_and_pc07_bytes(
        self,
    ) -> None:
        result = AUDIT.audit_rom(ROM_PATH.read_bytes())
        observed_table_hashes: list[str] = []
        observed_pc7_hex: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "observed_sha256":
                        self.assertIsInstance(child, str)
                        observed_table_hashes.append(child)
                    elif key == "observed_byte_hex":
                        self.assertIsInstance(child, str)
                        observed_pc7_hex.append(child)
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(result)
        self.assertEqual(
            observed_table_hashes,
            [spec.expected_sha256 for spec in AUDIT.TABLE_SPECS],
        )
        self.assertEqual(
            observed_pc7_hex,
            [
                f"{spec.pc7_expected:02x}"
                for spec in AUDIT.TABLE_SPECS
            ],
        )
        self.assertTrue(all(len(value) == 64 for value in observed_table_hashes))
        self.assertTrue(all(len(value) == 2 for value in observed_pc7_hex))

        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(str(ROM_PATH), serialized)
        for forbidden_key in (
            '"observed_bytes_hex"',
            '"file_offset"',
            '"raw_rom"',
            '"rom_bytes"',
            '"save_bytes"',
            '"state_bytes"',
        ):
            self.assertNotIn(forbidden_key, serialized)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_rom_identity_fails_closed_before_bounded_audit(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        mutated[0x100] ^= 0x01

        with self.assertRaisesRegex(
            AUDIT.AttackBoundaryAuditError,
            "ROM hash does not match",
        ):
            AUDIT.audit_rom(bytes(mutated))
        with self.assertRaisesRegex(
            AUDIT.AttackBoundaryAuditError,
            "expected 0x400000 ROM bytes",
        ):
            AUDIT.audit_rom(canonical[:-1])

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_bounded_table_preimages_are_independently_pinned(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        first = AUDIT.TABLE_SPECS[0]
        mutated[AUDIT.snes_hirom_to_file(first.start)] ^= 0x01
        identity = {
            "identity": "test identity gate bypass",
            "size": len(mutated),
            "sha1": AUDIT.CANONICAL_ROM_SHA1,
            "sha256": AUDIT.CANONICAL_ROM_SHA256,
        }

        with mock.patch.object(
            AUDIT,
            "validate_canonical_rom",
            return_value=identity,
        ):
            with self.assertRaisesRegex(
                AUDIT.AttackBoundaryAuditError,
                "bounded table bytes drifted: basic_attack_action_ids",
            ):
                AUDIT.audit_rom(bytes(mutated))

    def test_contract_drift_and_duplicate_json_keys_fail_closed(self) -> None:
        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["tables"][0]["pc07_lookup"]["expected_byte_hex"] = "00"
        with self.assertRaisesRegex(
            AUDIT.AttackBoundaryAuditError,
            "reference table contract drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        with self.assertRaisesRegex(
            AUDIT.AttackBoundaryAuditError,
            "duplicate JSON key",
        ):
            AUDIT._reject_duplicate_keys([("scope", 1), ("scope", 2)])

    def test_cli_exposes_no_output_or_mutation_destination(self) -> None:
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
        ):
            self.assertNotIn(forbidden_write, source)


if __name__ == "__main__":
    unittest.main()
