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

AUDIT_PATH = TOOLS_DIR / "audit_pc7_battle_progression_boundaries.py"
REFERENCE_PATH = ROOT / "references" / "pc7_battle_progression_boundaries.json"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_pc7_battle_progression_boundaries", AUDIT_PATH
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class Pc7BattleProgressionBoundaryTests(unittest.TestCase):
    def test_reference_contract_is_pinned_and_geometry_is_exact(self) -> None:
        source = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(source), AUDIT.REFERENCE_SIZE)
        self.assertEqual(hashlib.sha256(source).hexdigest(), AUDIT.REFERENCE_SHA256)

        contract = AUDIT.load_reference_contract()
        AUDIT._validate_specs()
        self.assertEqual(
            [row["name"] for row in contract["spans"]],
            [spec.name for spec in AUDIT.SPAN_SPECS],
        )
        self.assertEqual(
            [row["name"] for row in contract["instruction_sites"]],
            [spec.name for spec in AUDIT.SITE_SPECS],
        )

    def test_pc07_geometry_exposes_both_independent_bounds(self) -> None:
        self.assertEqual(AUDIT.PC07_NATURAL_RECORD, 0x7E2830)
        self.assertEqual(AUDIT.BATTLE_ID_MAP_BASE, 0x7EB1BE)
        self.assertEqual(AUDIT.BATTLE_ID_MAP_END_EXCLUSIVE, 0x7EB1C5)
        self.assertEqual(
            AUDIT.PC07_DIRECT_MAP_ADDRESS,
            AUDIT.BATTLE_ID_MAP_END_EXCLUSIVE,
        )
        self.assertEqual(AUDIT.RESERVE_XP_NUMERATOR, 15)
        self.assertEqual(AUDIT.RESERVE_XP_DENOMINATOR, 20)
        self.assertEqual(
            AUDIT.RESERVE_XP_NUMERATOR * 100 // AUDIT.RESERVE_XP_DENOMINATOR,
            75,
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_rom_yields_only_bounded_hash_observations(self) -> None:
        rom = ROM_PATH.read_bytes()
        before = hashlib.sha256(rom).hexdigest()

        result = AUDIT.audit_rom(rom)

        self.assertEqual(result["schema"], AUDIT.SCHEMA)
        self.assertEqual(result["evidence_level"], "verified-static")
        self.assertEqual(result["rom"]["sha256"], AUDIT.CANONICAL_ROM_SHA256)
        self.assertEqual(
            [row["observed_sha256"] for row in result["spans"]],
            [spec.expected_sha256 for spec in AUDIT.SPAN_SPECS],
        )
        self.assertEqual(
            [row["observed_sha256"] for row in result["instruction_sites"]],
            [spec.expected_sha256 for spec in AUDIT.SITE_SPECS],
        )
        self.assertEqual(
            result["derived_geometry"][
                "vanilla_logical_ids_processed_by_reserve_scan"
            ],
            ["00", "01", "02", "03", "04", "05", "06"],
        )
        self.assertFalse(
            result["derived_geometry"]["pc07_map_lookup_in_initialized_extent"]
        )
        self.assertFalse(result["conclusion"]["reserve_pc07_supported_by_vanilla"])
        self.assertFalse(result["conclusion"]["extend_bound_only_is_safe"])
        self.assertTrue(
            result["conclusion"][
                "explicit_pc07_active_membership_adapter_required"
            ]
        )
        self.assertFalse(result["conclusion"]["rom_save_state_mutation_performed"])
        self.assertFalse(result["conclusion"]["patch_or_rom_emitted"])
        self.assertEqual(hashlib.sha256(rom).hexdigest(), before)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_output_contains_no_rom_bytes_or_local_path(self) -> None:
        result = AUDIT.audit_rom(ROM_PATH.read_bytes())
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(str(ROM_PATH), serialized)
        for forbidden_key in (
            '"observed_bytes_hex"',
            '"expected_bytes_hex"',
            '"file_offset"',
            '"raw_rom"',
            '"rom_bytes"',
            '"save_bytes"',
            '"state_bytes"',
        ):
            self.assertNotIn(forbidden_key, serialized)
        hashes = [
            row["observed_sha256"]
            for group in (result["spans"], result["instruction_sites"])
            for row in group
        ]
        self.assertEqual(len(hashes), len(AUDIT.SPAN_SPECS) + len(AUDIT.SITE_SPECS))
        self.assertTrue(all(len(value) == 64 for value in hashes))

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_rom_identity_fails_closed_before_bounded_audit(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        mutated[0x100] ^= 0x01
        with self.assertRaisesRegex(
            AUDIT.BattleProgressionAuditError, "ROM hash does not match"
        ):
            AUDIT.audit_rom(bytes(mutated))
        with self.assertRaisesRegex(
            AUDIT.BattleProgressionAuditError, "expected 0x400000 ROM bytes"
        ):
            AUDIT.audit_rom(canonical[:-1])

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_bounded_preimages_are_independently_pinned(self) -> None:
        canonical = ROM_PATH.read_bytes()
        identity = {
            "identity": "test identity gate bypass",
            "size": len(canonical),
            "sha1": AUDIT.CANONICAL_ROM_SHA1,
            "sha256": AUDIT.CANONICAL_ROM_SHA256,
        }
        for spec in AUDIT.SPAN_SPECS:
            mutated = bytearray(canonical)
            mutated[AUDIT.snes_hirom_to_file(spec.start)] ^= 0x01
            with mock.patch.object(
                AUDIT, "validate_canonical_rom", return_value=identity
            ):
                with self.assertRaisesRegex(
                    AUDIT.BattleProgressionAuditError,
                    f"bounded bytes drifted: {spec.name}",
                ):
                    AUDIT.audit_rom(bytes(mutated))

        for spec in AUDIT.SITE_SPECS:
            mutated = bytearray(canonical)
            mutated[AUDIT.snes_hirom_to_file(spec.start)] ^= 0x01
            with self.assertRaisesRegex(
                AUDIT.BattleProgressionAuditError,
                f"bounded bytes drifted: {spec.name}",
            ):
                AUDIT._observe(
                    bytes(mutated),
                    spec.start,
                    spec.size,
                    spec.expected_sha256,
                    spec.name,
                )

    def test_contract_drift_and_duplicate_keys_fail_closed(self) -> None:
        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["instruction_sites"][0]["claim"] = "invented"
        with self.assertRaisesRegex(
            AUDIT.BattleProgressionAuditError,
            "reference instruction-site contract drifted",
        ):
            AUDIT._validate_reference_contract(contract)
        with self.assertRaisesRegex(
            AUDIT.BattleProgressionAuditError, "duplicate JSON key"
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
        ):
            self.assertNotIn(forbidden_write, source)


if __name__ == "__main__":
    unittest.main()
