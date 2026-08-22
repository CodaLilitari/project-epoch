from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "schala_sidecar.py"

SPEC = importlib.util.spec_from_file_location("schala_sidecar", TOOL_PATH)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def sample_sidecar(sequence: int = 0x1234):
    return TOOL.SchalaSidecarV1(
        character_record=bytes(range(TOOL.CHARACTER_RECORD_SIZE)),
        name=bytes.fromhex("9C A2 9B 8A A5 AA"),
        tech_progress=3,
        learned_mask=0xE0,
        combo_state=bytes(range(0x10, 0x20)),
        quest_state=TOOL.encode_quest_state(
            TOOL.QuestStateV1(
                quest_unlocked=True,
                anchor_count=3,
                ward_resolved=True,
                schala_recruited=True,
                join_grant_applied=True,
            )
        ),
        reserved=bytes(TOOL.RESERVED_SIZE),
        flags=TOOL.FLAG_INITIALIZED | TOOL.FLAG_NG_PLUS_RETAIN,
        sequence=sequence,
        vanilla_slot_checksum=0x91D6,
    )


class SchalaSidecarTests(unittest.TestCase):
    def test_layout_exactly_fills_candidate_gap(self) -> None:
        self.assertEqual(
            TOOL.SIDECAR_SIZE * TOOL.SIDECAR_SLOT_COUNT,
            TOOL.SIDECAR_AREA_LENGTH,
        )
        self.assertEqual(
            TOOL.SIDECAR_AREA_OFFSET + TOOL.SIDECAR_AREA_LENGTH,
            TOOL.GLOBAL_METADATA_OFFSET,
        )
        self.assertEqual(TOOL.slot_file_offset(1), 0x1E00)
        self.assertEqual(TOOL.slot_file_offset(2), 0x1EA0)
        self.assertEqual(TOOL.slot_file_offset(3), 0x1F40)

    def test_round_trip(self) -> None:
        source = sample_sidecar()
        encoded = TOOL.encode_sidecar(source)
        self.assertEqual(len(encoded), TOOL.SIDECAR_SIZE)
        self.assertEqual(TOOL.decode_sidecar(encoded), source)

    def test_checksum_detects_corruption(self) -> None:
        encoded = bytearray(TOOL.encode_sidecar(sample_sidecar()))
        encoded[0x42] ^= 0x80
        with self.assertRaisesRegex(TOOL.SidecarError, "CRC mismatch"):
            TOOL.decode_sidecar(bytes(encoded))

    def test_binding_detects_different_vanilla_slot(self) -> None:
        encoded = TOOL.encode_sidecar(sample_sidecar())
        self.assertEqual(
            TOOL.decode_sidecar(
                encoded, expected_vanilla_checksum=0x91D6
            ).vanilla_slot_checksum,
            0x91D6,
        )
        with self.assertRaisesRegex(TOOL.SidecarError, "bound to vanilla"):
            TOOL.decode_sidecar(
                encoded, expected_vanilla_checksum=0x1234
            )

    def test_uninitialized_record_is_rejected(self) -> None:
        with self.assertRaisesRegex(TOOL.SidecarError, "uninitialized"):
            TOOL.decode_sidecar(b"\xFF" * TOOL.SIDECAR_SIZE)

    def test_install_preserves_vanilla_slots_and_metadata(self) -> None:
        sram = bytes((index * 17 + 9) & 0xFF for index in range(TOOL.SRAM_SIZE))
        encoded = TOOL.encode_sidecar(sample_sidecar())
        installed = TOOL.install_sidecar(sram, 2, encoded)
        start = TOOL.slot_file_offset(2)
        end = start + TOOL.SIDECAR_SIZE

        self.assertEqual(installed[:start], sram[:start])
        self.assertEqual(installed[start:end], encoded)
        self.assertEqual(installed[end:], sram[end:])
        self.assertEqual(
            installed[: TOOL.SIDECAR_AREA_OFFSET],
            sram[: TOOL.SIDECAR_AREA_OFFSET],
        )
        self.assertEqual(
            installed[TOOL.GLOBAL_METADATA_OFFSET :],
            sram[TOOL.GLOBAL_METADATA_OFFSET :],
        )

    def test_bad_slot_is_rejected(self) -> None:
        for slot in (0, 4):
            with self.assertRaisesRegex(TOOL.SidecarError, "1, 2, or 3"):
                TOOL.slot_file_offset(slot)

    def test_wrong_field_length_is_rejected(self) -> None:
        source = sample_sidecar()
        bad = TOOL.dataclasses.replace(source, character_record=b"\x00")
        with self.assertRaisesRegex(TOOL.SidecarError, "character_record"):
            TOOL.encode_sidecar(bad)

    def test_header_and_quest_state_semantics_are_strict(self) -> None:
        with self.assertRaisesRegex(TOOL.SidecarError, "initialized"):
            TOOL.encode_sidecar(
                TOOL.dataclasses.replace(sample_sidecar(), flags=0)
            )
        with self.assertRaisesRegex(TOOL.SidecarError, "unknown header"):
            TOOL.encode_sidecar(
                TOOL.dataclasses.replace(sample_sidecar(), flags=0x81)
            )
        with self.assertRaisesRegex(TOOL.SidecarError, "reserved"):
            TOOL.encode_sidecar(
                TOOL.dataclasses.replace(
                    sample_sidecar(),
                    reserved=b"\x01" + bytes(TOOL.RESERVED_SIZE - 1),
                )
            )
        with self.assertRaisesRegex(TOOL.SidecarError, "anchor_count"):
            TOOL.encode_quest_state(TOOL.QuestStateV1(anchor_count=4))
        with self.assertRaisesRegex(TOOL.SidecarError, "ward_resolved"):
            TOOL.encode_quest_state(
                TOOL.QuestStateV1(ward_resolved=True, anchor_count=3)
            )
        with self.assertRaisesRegex(TOOL.SidecarError, "requires"):
            TOOL.encode_quest_state(
                TOOL.QuestStateV1(join_grant_applied=True)
            )

    def test_single_tech_state_uses_high_bit_first_mask(self) -> None:
        self.assertEqual(TOOL.learned_mask_for_count(0), 0x00)
        self.assertEqual(TOOL.learned_mask_for_count(3), 0xE0)
        self.assertEqual(TOOL.learned_mask_for_count(8), 0xFF)
        with self.assertRaisesRegex(TOOL.SidecarError, "high-bit-first"):
            TOOL.encode_sidecar(
                TOOL.dataclasses.replace(sample_sidecar(), learned_mask=0x07)
            )

    def test_load_classifies_uninitialized_invalid_stale_and_valid(self):
        encoded = TOOL.encode_sidecar(sample_sidecar())
        self.assertEqual(
            TOOL.classify_sidecar(
                b"\xFF" * TOOL.SIDECAR_SIZE, 0x91D6
            ).status,
            "uninitialized",
        )
        corrupt = bytearray(encoded)
        corrupt[0x42] ^= 1
        self.assertEqual(
            TOOL.classify_sidecar(bytes(corrupt), 0x91D6).status,
            "invalid",
        )
        self.assertEqual(
            TOOL.classify_sidecar(encoded, 0x1234).status, "stale"
        )
        loaded = TOOL.classify_sidecar(encoded, 0x91D6)
        self.assertEqual(loaded.status, "valid")
        self.assertEqual(loaded.value, sample_sidecar())

    def test_invalidate_erases_only_selected_sidecar(self) -> None:
        sram = bytes((index * 13 + 5) & 0xFF for index in range(TOOL.SRAM_SIZE))
        installed = TOOL.install_sidecar(
            sram, 2, TOOL.encode_sidecar(sample_sidecar())
        )
        invalidated = TOOL.invalidate_sidecar(installed, 2)
        start = TOOL.slot_file_offset(2)
        end = start + TOOL.SIDECAR_SIZE
        self.assertEqual(
            invalidated[start:end], b"\xFF" * TOOL.SIDECAR_SIZE
        )
        self.assertEqual(invalidated[:start], installed[:start])
        self.assertEqual(invalidated[end:], installed[end:])

    def test_new_game_plus_retain_rebinds_without_duplicate_reset(self):
        source = sample_sidecar(sequence=0x1234)
        retained = TOOL.apply_new_game_plus_policy(
            source,
            new_vanilla_checksum=0xBEEF,
            reset_character_record=b"\xAA" * TOOL.CHARACTER_RECORD_SIZE,
            reset_name=b"RESET!",
        )
        self.assertEqual(retained.character_record, source.character_record)
        self.assertEqual(retained.quest_state, source.quest_state)
        self.assertEqual(retained.sequence, 0x1235)
        self.assertEqual(retained.vanilla_slot_checksum, 0xBEEF)

    def test_new_game_plus_reset_clears_progress_and_grant_guards(self):
        source = TOOL.dataclasses.replace(
            sample_sidecar(), flags=TOOL.FLAG_INITIALIZED
        )
        reset_record = b"\xAA" * TOOL.CHARACTER_RECORD_SIZE
        reset = TOOL.apply_new_game_plus_policy(
            source,
            new_vanilla_checksum=0xBEEF,
            reset_character_record=reset_record,
            reset_name=b"SCHALA",
        )
        self.assertEqual(reset.character_record, reset_record)
        self.assertEqual(reset.name, b"SCHALA")
        self.assertEqual(reset.tech_progress, 0)
        self.assertEqual(reset.learned_mask, 0)
        self.assertEqual(reset.combo_state, bytes(TOOL.COMBO_STATE_SIZE))
        self.assertEqual(
            TOOL.decode_quest_state(reset.quest_state), TOOL.QuestStateV1()
        )
        self.assertEqual(reset.flags, TOOL.FLAG_INITIALIZED)
        self.assertEqual(reset.sequence, 0x1235)
        self.assertEqual(reset.vanilla_slot_checksum, 0xBEEF)


if __name__ == "__main__":
    unittest.main()
