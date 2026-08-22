from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "tools" / "build_lucca_to_magus_clone_v1.py"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)
SAVE_PATH = ROOT / "private" / "input" / "lavos_save" / "chrono_trigger.srm"
EXPECTED_SAVE_SHA256 = (
    "cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203"
)

if str(BUILDER_PATH.parent) not in sys.path:
    sys.path.insert(0, str(BUILDER_PATH.parent))
SPEC = importlib.util.spec_from_file_location("clone_builder_v1", BUILDER_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILDER
SPEC.loader.exec_module(BUILDER)


@unittest.skipUnless(ROM_PATH.exists(), "local clean ROM is not available")
class CloneBuilderRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.orig = ROM_PATH.read_bytes()

    def assert_all_differences_are_reported(self, result) -> None:
        covered: set[int] = set()
        for change in result.changes:
            region = range(change.offset, change.offset + change.length)
            covered.update(region)
            self.assertTrue(
                any(
                    self.orig[offset] != result.patched[offset]
                    for offset in region
                ),
                change.description,
            )
        unexpected = [
            offset
            for offset, (old, new) in enumerate(
                zip(self.orig, result.patched, strict=True)
            )
            if old != new and offset not in covered
        ]
        self.assertEqual(unexpected, [])

    def test_input_identity(self) -> None:
        BUILDER.validate_input(self.orig)
        self.assertEqual(len(self.orig), BUILDER.EXPECTED_SIZE)
        self.assertEqual(
            BUILDER.digest(self.orig, "sha1"), BUILDER.EXPECTED_SHA1
        )

    def test_static_clone_layers(self) -> None:
        result = BUILDER.build_patch(self.orig, runtime_hook="none")
        patched = result.patched

        for base, stride, _ in BUILDER.SPRITE_TABLES:
            lucca = slice(
                base + BUILDER.LUCCA * stride,
                base + (BUILDER.LUCCA + 1) * stride,
            )
            magus = slice(
                base + BUILDER.MAGUS * stride,
                base + (BUILDER.MAGUS + 1) * stride,
            )
            self.assertEqual(patched[lucca], self.orig[magus])
            for protected_index in (7, 8):
                protected = slice(
                    base + protected_index * stride,
                    base + (protected_index + 1) * stride,
                )
                self.assertEqual(patched[protected], self.orig[protected])

        self.assertEqual(
            patched[
                BUILDER.PORTRAIT_LUCCA_TILES :
                BUILDER.PORTRAIT_LUCCA_TILES
                + BUILDER.PORTRAIT_TILE_LENGTH
            ],
            self.orig[
                BUILDER.PORTRAIT_MAGUS_TILES :
                BUILDER.PORTRAIT_MAGUS_TILES
                + BUILDER.PORTRAIT_TILE_LENGTH
            ],
        )
        for base, _ in BUILDER.ATTACK_SELECTOR_FAMILIES:
            self.assertEqual(
                patched[base + BUILDER.LUCCA],
                self.orig[base + BUILDER.MAGUS],
            )
        self.assertEqual(
            patched[BUILDER.OVERLOADED_PC7_ATTACK_BYTE],
            self.orig[BUILDER.OVERLOADED_PC7_ATTACK_BYTE],
        )
        lucca_tp = (
            BUILDER.TP_REQUIREMENT_BASE
            + (
                BUILDER.TP_REQUIREMENT_DUMMY_COUNT
                + BUILDER.LUCCA * BUILDER.TP_REQUIREMENT_COUNT
            )
            * BUILDER.TP_REQUIREMENT_STRIDE
        )
        magus_tp = (
            BUILDER.TP_REQUIREMENT_BASE
            + (
                BUILDER.TP_REQUIREMENT_DUMMY_COUNT
                + BUILDER.MAGUS * BUILDER.TP_REQUIREMENT_COUNT
            )
            * BUILDER.TP_REQUIREMENT_STRIDE
        )
        tp_length = (
            BUILDER.TP_REQUIREMENT_COUNT * BUILDER.TP_REQUIREMENT_STRIDE
        )
        self.assertEqual(
            patched[lucca_tp : lucca_tp + tp_length],
            self.orig[magus_tp : magus_tp + tp_length],
        )
        self.assertEqual(
            patched[BUILDER.LUCCA_MENU_ELEMENT],
            self.orig[BUILDER.MAGUS_MENU_ELEMENT],
        )
        self.assertEqual(
            patched[
                BUILDER.HOOK_OFFSET :
                BUILDER.HOOK_OFFSET + len(BUILDER.HOOK_EXPECTED)
            ],
            self.orig[
                BUILDER.HOOK_OFFSET :
                BUILDER.HOOK_OFFSET + len(BUILDER.HOOK_EXPECTED)
            ],
        )
        BUILDER.validate_header_checksum(patched)
        self.assertEqual(
            BUILDER.apply_ips(self.orig, result.ips), result.patched
        )
        self.assert_all_differences_are_reported(result)
        intents, audit = BUILDER.audit_write_intents(self.orig, result)
        self.assertEqual(audit["status"], "images-valid")
        self.assertTrue(audit["complete_diff_coverage"])
        self.assertTrue(audit["preimages_verified"])
        self.assertEqual(intents["build_mode"], "private-diagnostic")

    def test_provisional_runtime_hook(self) -> None:
        result = BUILDER.build_patch(self.orig, runtime_hook="provisional")
        self.assertLessEqual(
            BUILDER.ENEMY_REWARD_TABLE_START, BUILDER.CAVE_OFFSET
        )
        self.assertLessEqual(
            BUILDER.CAVE_OFFSET + len(BUILDER.CAVE_BYTES),
            BUILDER.ENEMY_REWARD_TABLE_END,
        )
        self.assertEqual(
            BUILDER.ENEMY_REWARD_TABLE_END
            - BUILDER.ENEMY_REWARD_TABLE_START,
            BUILDER.ENEMY_REWARD_RECORD_COUNT
            * BUILDER.ENEMY_REWARD_RECORD_STRIDE,
        )
        self.assertEqual(
            self.orig[BUILDER.CAVE_OFFSET - 1], BUILDER.CAVE_BOUNDARY_BEFORE
        )
        self.assertEqual(
            self.orig[BUILDER.CAVE_ZERO_RUN_END],
            BUILDER.CAVE_BOUNDARY_AFTER,
        )
        self.assertFalse(
            any(self.orig[BUILDER.CAVE_OFFSET : BUILDER.CAVE_ZERO_RUN_END])
        )
        self.assertLessEqual(
            BUILDER.CAVE_OFFSET + len(BUILDER.CAVE_BYTES),
            BUILDER.CAVE_ZERO_RUN_END,
        )
        self.assertEqual(
            result.patched[
                BUILDER.HOOK_OFFSET :
                BUILDER.HOOK_OFFSET + len(BUILDER.HOOK_BYTES)
            ],
            BUILDER.HOOK_BYTES,
        )
        self.assertEqual(
            result.patched[
                BUILDER.CAVE_OFFSET :
                BUILDER.CAVE_OFFSET + len(BUILDER.CAVE_BYTES)
            ],
            BUILDER.CAVE_BYTES,
        )
        BUILDER.validate_header_checksum(result.patched)
        self.assertEqual(
            BUILDER.apply_ips(self.orig, result.ips), result.patched
        )
        self.assert_all_differences_are_reported(result)
        manifest = BUILDER.make_manifest(self.orig, result)
        self.assertTrue(manifest["invariants"]["runtime_hook_quarantined"])
        self.assertTrue(manifest["invariants"]["runtime_hook_known_unsafe"])
        self.assertIn("$0432/$0439", manifest["runtime_save_risk"])
        self.assertIn("EnemyRewardTable", manifest["cave_warning"])
        self.assertIn("known unsafe", manifest["cave_warning"])
        self.assertEqual(
            manifest["write_intent_audit"]["status"],
            "expected-rejected-retired-unsafe",
        )
        self.assertIn(
            "enemy_reward_table",
            manifest["write_intent_audit"]["reason"],
        )
        self.assertFalse(manifest["production_input"])


@unittest.skipUnless(SAVE_PATH.exists(), "recovered Lavos save is not available")
class RecoveredSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.save = SAVE_PATH.read_bytes()

    def test_original_save_identity(self) -> None:
        self.assertEqual(len(self.save), 0x2000)
        self.assertEqual(
            BUILDER.digest(self.save, "sha256"), EXPECTED_SAVE_SHA256
        )

    def test_original_slot_one_party(self) -> None:
        self.assertEqual(self.save[0x580:0x583], bytes((0, 1, 2)))

    def test_slot_0430_begins_with_seven_pc_tech_arrays(self) -> None:
        self.assertEqual(
            self.save[0x430:0x437],
            bytes.fromhex("08 08 08 07 05 03 03"),
        )
        self.assertEqual(
            self.save[0x437:0x43E],
            bytes.fromhex("FF FF FF FE F8 E0 E0"),
        )


class IpsCodecTests(unittest.TestCase):
    def test_round_trip_without_rle(self) -> None:
        orig = bytes(range(64))
        modified = bytearray(orig)
        modified[3:8] = b"abcde"
        modified[40] = 0xFF
        patch = BUILDER.make_ips(orig, bytes(modified))
        self.assertEqual(BUILDER.apply_ips(orig, patch), bytes(modified))

    def test_invalid_header_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BUILDER.apply_ips(b"\x00" * 16, b"NOT-IPS")

    def test_unequal_source_lengths_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BUILDER.make_ips(b"\x00", b"\x00\x01")


class OutputPathTests(unittest.TestCase):
    def test_input_output_collision_rejected(self) -> None:
        rom = ROOT / "same-file"
        with self.assertRaises(ValueError):
            BUILDER.validate_output_paths(
                rom,
                rom,
                ROOT / "report.md",
                ROOT / "manifest.json",
            )

    def test_output_output_collision_rejected(self) -> None:
        shared = ROOT / "shared-output"
        with self.assertRaises(ValueError):
            BUILDER.validate_output_paths(
                ROOT / "input.sfc",
                shared,
                shared,
                ROOT / "manifest.json",
            )


if __name__ == "__main__":
    unittest.main()
