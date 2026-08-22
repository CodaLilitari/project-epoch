from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "schala_save_layout.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("schala_save_layout", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def patterned_bank(seed: int) -> bytes:
    return bytes((index * 29 + seed) & 0xFF for index in range(0x10000))


class SchalaSaveLayoutTests(unittest.TestCase):
    def test_layout_validates(self) -> None:
        TOOL.validate_layout()

    def test_descriptor_counts_and_patch_constants(self) -> None:
        table = TOOL.encode_region_table(TOOL.PROJECT_EPOCH_REGIONS)
        self.assertEqual(len(TOOL.PROJECT_EPOCH_REGIONS), 10)
        self.assertEqual(len(table), 0x32)
        self.assertEqual(TOOL.TABLE_COPY_MVN_A, 0x31)
        self.assertEqual(TOOL.TABLE_LOOP_STOP, 0x32)
        self.assertLessEqual(len(table), TOOL.TABLE_STAGING_CAPACITY)

    def test_destination_offsets_preserve_vanilla_layout(self) -> None:
        ranges = TOOL.destination_ranges(TOOL.PROJECT_EPOCH_REGIONS)
        self.assertEqual(
            [(start, end) for start, end, _ in ranges[:3]],
            [(0x0000, 0x0430), (0x0430, 0x0480), (0x0480, 0x05B0)],
        )
        self.assertEqual(ranges[-1][1], TOOL.SERIALIZED_BYTES)

    def test_split_serialization_matches_vanilla_when_compatibility_moves(
        self,
    ) -> None:
        banks = {
            0x00: patterned_bank(3),
            0x7E: patterned_bank(7),
            0x7F: patterned_bank(11),
        }
        expected = TOOL.serialize_regions(banks, TOOL.VANILLA_REGIONS)

        moved_7e = bytearray(banks[0x7E])
        moved_7e[0x2CA0:0x2CF0] = moved_7e[0x2830:0x2880]
        moved_7e[0x2830:0x2880] = bytes([0xE7]) * 0x50
        project_epoch_banks = {**banks, 0x7E: bytes(moved_7e)}
        actual = TOOL.serialize_regions(
            project_epoch_banks,
            TOOL.PROJECT_EPOCH_REGIONS,
        )
        self.assertEqual(actual, expected)

    def test_schala_record_is_not_serialized_into_vanilla_slot(self) -> None:
        banks = {
            0x00: patterned_bank(3),
            0x7E: bytearray(patterned_bank(7)),
            0x7F: patterned_bank(11),
        }
        banks[0x7E][0x2CA0:0x2CF0] = banks[0x7E][0x2830:0x2880]
        first = TOOL.serialize_regions(
            {**banks, 0x7E: bytes(banks[0x7E])},
            TOOL.PROJECT_EPOCH_REGIONS,
        )
        banks[0x7E][0x2830:0x2880] = bytes([0x5A]) * 0x50
        second = TOOL.serialize_regions(
            {**banks, 0x7E: bytes(banks[0x7E])},
            TOOL.PROJECT_EPOCH_REGIONS,
        )
        self.assertEqual(first, second)

    def test_translated_full_load_restores_compatibility_not_pc07(self) -> None:
        source_banks = {
            0x00: patterned_bank(3),
            0x7E: bytearray(patterned_bank(7)),
            0x7F: patterned_bank(11),
        }
        expected_compatibility = bytes(
            source_banks[0x7E][0x2830:0x2880]
        )
        serialized_prefix = TOOL.serialize_regions(
            {**source_banks, 0x7E: bytes(source_banks[0x7E])},
            TOOL.VANILLA_REGIONS,
        )
        serialized_slot = (
            serialized_prefix
            + bytes([0xA5]) * (TOOL.SLOT_SIZE - len(serialized_prefix))
        )

        precleared_pc07 = bytes([0x00]) * 0x50
        destination_7e = bytearray(patterned_bank(19))
        destination_7e[0x2830:0x2880] = precleared_pc07
        destination_7e[0x2CA0:0x2CF0] = bytes([0xCC]) * 0x50
        restored = TOOL.restore_regions_from_slot(
            serialized_slot,
            {
                0x00: patterned_bank(23),
                0x7E: bytes(destination_7e),
                0x7F: patterned_bank(29),
            },
            TOOL.PROJECT_EPOCH_REGIONS,
        )

        self.assertEqual(
            restored[0x7E][0x2CA0:0x2CF0],
            expected_compatibility,
        )
        self.assertEqual(
            restored[0x7E][0x2830:0x2880],
            precleared_pc07,
        )

    def test_translated_round_trip_preserves_slot_prefix_and_tail(self) -> None:
        source_7e = bytearray(patterned_bank(31))
        source_7e[0x2CA0:0x2CF0] = bytes(
            (index * 7 + 5) & 0xFF for index in range(0x50)
        )
        source_7e[0x2830:0x2880] = bytes([0x5A]) * 0x50
        source_banks = {
            0x00: patterned_bank(37),
            0x7E: bytes(source_7e),
            0x7F: patterned_bank(41),
        }
        serialized_prefix = TOOL.serialize_regions(
            source_banks,
            TOOL.PROJECT_EPOCH_REGIONS,
        )
        tail = bytes(
            (index * 13 + 9) & 0xFF
            for index in range(TOOL.SLOT_SIZE - TOOL.SERIALIZED_BYTES)
        )
        serialized_slot = serialized_prefix + tail

        empty_7e = bytearray([0xE1]) * 0x10000
        empty_7e[0x2830:0x2880] = bytes([0x00]) * 0x50
        restored = TOOL.restore_regions_from_slot(
            serialized_slot,
            {
                0x00: bytes([0xE2]) * 0x10000,
                0x7E: bytes(empty_7e),
                0x7F: bytes([0xE3]) * 0x10000,
            },
            TOOL.PROJECT_EPOCH_REGIONS,
        )
        rebuilt = TOOL.serialize_regions(
            restored,
            TOOL.PROJECT_EPOCH_REGIONS,
        )

        self.assertEqual(rebuilt, serialized_prefix)
        self.assertEqual(serialized_slot[TOOL.SERIALIZED_BYTES:], tail)
        self.assertEqual(
            restored[0x7E][0x2830:0x2880],
            bytes([0x00]) * 0x50,
        )

    def test_restore_fails_closed_on_shape_overlap_and_short_table(
        self,
    ) -> None:
        slot = bytes([0xA5]) * TOOL.SLOT_SIZE
        banks = {
            0x00: patterned_bank(3),
            0x7E: patterned_bank(7),
            0x7F: patterned_bank(11),
        }
        for malformed in (slot[:-1], bytearray(slot)):
            with self.subTest(kind=type(malformed).__name__):
                with self.assertRaisesRegex(
                    RuntimeError, "immutable bytes of length"
                ):
                    TOOL.restore_regions_from_slot(
                        malformed,
                        banks,
                        TOOL.PROJECT_EPOCH_REGIONS,
                    )

        overlap = (
            TOOL.SaveRegion(0x2400, 0x7E, 0x0430, "first"),
            TOOL.SaveRegion(0x2420, 0x7E, 0x0404, "overlap"),
        )
        with self.assertRaisesRegex(RuntimeError, "overlaps first"):
            TOOL.restore_regions_from_slot(slot, banks, overlap)

        with self.assertRaisesRegex(
            RuntimeError, r"writes natural PC \$07"
        ):
            TOOL.restore_regions_from_slot(
                slot,
                banks,
                TOOL.VANILLA_REGIONS,
            )

        with self.assertRaisesRegex(
            RuntimeError, "does not consume the exact serialized prefix"
        ):
            TOOL.restore_regions_from_slot(
                slot,
                banks,
                TOOL.PROJECT_EPOCH_REGIONS[:-1],
            )

        malformed_regions = (
            (TOOL.SaveRegion(-1, 0x7E, 0x0834, "negative"), "address"),
            (TOOL.SaveRegion(0x2400, 0x100, 0x0834, "bank"), "bank"),
            (TOOL.SaveRegion(0x2400, 0x7E, True, "bool"), "length"),
            (TOOL.SaveRegion(0x2400, 0x7E, 0x0834, ""), "label"),
        )
        for region, message in malformed_regions:
            with self.subTest(message=message):
                with self.assertRaisesRegex(RuntimeError, message):
                    TOOL.restore_regions_from_slot(slot, banks, (region,))

    def test_manifest_exposes_exact_compatibility_destination(self) -> None:
        manifest = TOOL.manifest()
        region = manifest["regions"][1]
        self.assertEqual(region["label"], "relocated_compatibility")
        self.assertEqual(region["destination_start"], 0x0430)
        self.assertEqual(region["destination_end_exclusive"], 0x0480)
        self.assertEqual(
            manifest["restore_contract"],
            {
                "input_slot_bytes": 0x0A00,
                "copied_prefix_bytes": 0x0834,
                "serialized_compatibility_start": 0x0430,
                "serialized_compatibility_end_exclusive": 0x0480,
                "relocated_compatibility_wram_start": 0x2CA0,
                "relocated_compatibility_wram_end_exclusive": 0x2CF0,
                "natural_pc07_wram_start": 0x2830,
                "natural_pc07_wram_end_exclusive": 0x2880,
                "natural_pc07_restore_action": "preserve-precleared",
            },
        )
        self.assertEqual(
            manifest["initialization_contract"]["normal_new_game"],
            {
                "vanilla_seed_bytes": 0x0280,
                "vanilla_pc_record_bytes": 0x0230,
                "compatibility_destination": 0x2CA0,
                "pc07_destination": 0x2830,
            },
        )

    def test_new_game_seed_is_split_without_aliasing_pc07(self) -> None:
        seed = bytes((index * 17 + 3) & 0xFF for index in range(0x280))
        pc07 = bytes((index * 19 + 5) & 0xFF for index in range(0x50))
        original_7e = bytes([0xE1]) * 0x10000
        result = TOOL.split_new_game_seed(
            seed,
            {0x7E: original_7e, 0x7F: patterned_bank(11)},
            pc07,
        )

        self.assertEqual(result[0x7E][0x2600:0x2830], seed[:0x230])
        self.assertEqual(result[0x7E][0x2CA0:0x2CF0], seed[0x230:])
        self.assertEqual(result[0x7E][0x2830:0x2880], pc07)
        expected_7e = bytearray(original_7e)
        expected_7e[0x2600:0x2830] = seed[:0x230]
        expected_7e[0x2830:0x2880] = pc07
        expected_7e[0x2CA0:0x2CF0] = seed[0x230:]
        self.assertEqual(result[0x7E], bytes(expected_7e))

    def test_attract_finalize_preserves_vanilla_records(self) -> None:
        original_7e = bytearray(patterned_bank(23))
        vanilla_records = bytes(original_7e[0x2600:0x2830])
        compatibility = bytes([0xC7]) * 0x50
        pc07 = bytes([0x57]) * 0x50
        result = TOOL.finalize_attract_pc07_layout(
            {0x7E: bytes(original_7e)},
            compatibility,
            pc07,
        )

        self.assertEqual(result[0x7E][0x2600:0x2830], vanilla_records)
        self.assertEqual(result[0x7E][0x2CA0:0x2CF0], compatibility)
        self.assertEqual(result[0x7E][0x2830:0x2880], pc07)

    def test_new_game_plus_split_preserves_pc07_and_roster(self) -> None:
        slot = bytearray(patterned_bank(31)[:TOOL.SLOT_SIZE])
        compatibility = bytes((index * 7 + 9) & 0xFF for index in range(0x50))
        slot[0x0430:0x0480] = compatibility
        original_7e = bytearray(patterned_bank(37))
        pc07 = bytes([0x07]) * 0x50
        roster_joined = bytes([0xA7]) * 0x30
        original_7e[0x2830:0x2880] = pc07
        original_7e[0x2980:0x29B0] = roster_joined
        original_7e[0x2CA0:0x2CF0] = bytes([0xCC]) * 0x50

        result = TOOL.restore_new_game_plus_regions_from_slot(
            bytes(slot),
            {0x7E: bytes(original_7e)},
        )
        self.assertEqual(result[0x7E][0x2CA0:0x2CF0], compatibility)
        self.assertEqual(result[0x7E][0x2830:0x2880], pc07)
        self.assertEqual(result[0x7E][0x2980:0x29B0], roster_joined)
        self.assertEqual(result[0x7E][0x2400:0x2830], slot[0x0000:0x0430])
        self.assertEqual(result[0x7E][0x2880:0x2980], slot[0x0480:0x0580])
        self.assertEqual(result[0x7E][0x2C23:0x2C56], slot[0x05B0:0x05E3])

    def test_initialization_transitions_reject_malformed_shapes(self) -> None:
        banks = {0x7E: patterned_bank(7)}
        with self.assertRaisesRegex(RuntimeError, "new-game seed"):
            TOOL.split_new_game_seed(bytes(0x27F), banks, bytes(0x50))
        with self.assertRaisesRegex(RuntimeError, r"PC \$07 record"):
            TOOL.split_new_game_seed(bytes(0x280), banks, bytearray(0x50))
        with self.assertRaisesRegex(RuntimeError, "compatibility template"):
            TOOL.finalize_attract_pc07_layout(
                banks,
                bytes(0x4F),
                bytes(0x50),
            )
        with self.assertRaisesRegex(RuntimeError, "too short"):
            TOOL.restore_new_game_plus_regions_from_slot(
                bytes(TOOL.SLOT_SIZE),
                {0x7E: bytes(0x2CEF)},
            )


if __name__ == "__main__":
    unittest.main()
