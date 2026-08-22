from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def load_module(name: str, filename: str):
    path = TOOLS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RASTATE = load_module("retroarch_rastate", "retroarch_rastate.py")
LEGACY = load_module("inject_bsv_wram_canary", "inject_bsv_wram_canary.py")
EDITOR = load_module(
    "edit_retroarch_bsv2_inputs", "edit_retroarch_bsv2_inputs.py"
)
TOOL = load_module("inject_bsv2_wram_canary", "inject_bsv2_wram_canary.py")
INSPECTOR = load_module(
    "inspect_current_wram_candidate", "inspect_current_wram_candidate.py"
)


def make_fixture() -> tuple[bytes, bytes, int]:
    state_size = 0x21000
    wram_base = 0x100
    core_state = bytearray(state_size)
    core_state[:4] = b"BST1"
    struct.pack_into("<I", core_state, 4, state_size)

    sram = bytearray(LEGACY.SAVE_SLOT_LENGTH)
    lucca = bytes((index * 3 + 1) & 0xFF for index in range(0x50))
    magus = bytes((index * 5 + 7) & 0xFF for index in range(0x50))
    sram[
        LEGACY.LUCCA_SAVE_OFFSET :
        LEGACY.LUCCA_SAVE_OFFSET + LEGACY.RECORD_LENGTH
    ] = lucca
    sram[
        LEGACY.MAGUS_SAVE_OFFSET :
        LEGACY.MAGUS_SAVE_OFFSET + LEGACY.RECORD_LENGTH
    ] = magus
    core_state[
        wram_base + LEGACY.LUCCA_WRAM_OFFSET :
        wram_base + LEGACY.LUCCA_WRAM_OFFSET + LEGACY.RECORD_LENGTH
    ] = lucca
    core_state[
        wram_base + LEGACY.MAGUS_WRAM_OFFSET :
        wram_base + LEGACY.MAGUS_WRAM_OFFSET + LEGACY.RECORD_LENGTH
    ] = magus
    core_state[
        wram_base + INSPECTOR.ROSTER_WRAM_OFFSET :
        wram_base + INSPECTOR.ROSTER_WRAM_OFFSET + INSPECTOR.ROSTER_LENGTH
    ] = bytes.fromhex("000102828004030605")
    core_state[wram_base + INSPECTOR.JOINED_FLAGS_WRAM_OFFSET] = 0xFC
    core_state[
        wram_base
        + INSPECTOR.EPOCH_NAME_WRAM_OFFSET : wram_base
        + INSPECTOR.EPOCH_NAME_WRAM_OFFSET
        + INSPECTOR.EPOCH_NAME_LENGTH
    ] = b"EPOCH "
    core_state[
        wram_base
        + INSPECTOR.LOCATION_ID_WRAM_OFFSET : wram_base
        + INSPECTOR.LOCATION_ID_WRAM_OFFSET
        + 2
    ] = (0x01DA).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.PENDING_REQUEST_WRAM_OFFSET
    ] = 0x21
    core_state[wram_base + INSPECTOR.EXPLORE_MODE_WRAM_OFFSET] = 1
    core_state[wram_base + INSPECTOR.DIALOG_STATE_WRAM_OFFSET] = 0
    core_state[wram_base + INSPECTOR.LEADER_OBJECT_WRAM_OFFSET] = 2
    core_state[
        wram_base + INSPECTOR.OBJECT_X_WRAM_OFFSET + 2 :
        wram_base + INSPECTOR.OBJECT_X_WRAM_OFFSET + 4
    ] = (0x0B80).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.OBJECT_Y_WRAM_OFFSET + 2 :
        wram_base + INSPECTOR.OBJECT_Y_WRAM_OFFSET + 4
    ] = (0x3CFF).to_bytes(2, "little")
    core_state[wram_base + INSPECTOR.STORYLINE_WRAM_OFFSET] = 0xD6
    core_state[
        wram_base + INSPECTOR.EVENT11C_MAGIC_FLAGS_WRAM_OFFSET
    ] = 0xA5
    core_state[
        wram_base + INSPECTOR.EVENT11C_ROBO_FLAGS_WRAM_OFFSET
    ] = 0x5A
    core_state[
        wram_base + INSPECTOR.EVENT11C_LAP_SCRATCH_WRAM_OFFSET
    ] = 3
    core_state[
        wram_base + INSPECTOR.BATTLE_PC1_CURRENT_HP_WRAM_OFFSET :
        wram_base + INSPECTOR.BATTLE_PC1_CURRENT_HP_WRAM_OFFSET + 2
    ] = (0x1111).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.BATTLE_PC1_MAX_HP_WRAM_OFFSET :
        wram_base + INSPECTOR.BATTLE_PC1_MAX_HP_WRAM_OFFSET + 2
    ] = (0x2222).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.BATTLE_PC1_CURRENT_MP_WRAM_OFFSET :
        wram_base + INSPECTOR.BATTLE_PC1_CURRENT_MP_WRAM_OFFSET + 2
    ] = (0x0033).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.BATTLE_PC1_MAX_MP_WRAM_OFFSET :
        wram_base + INSPECTOR.BATTLE_PC1_MAX_MP_WRAM_OFFSET + 2
    ] = (0x0044).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.BATTLE_SLOT03_CURRENT_HP_WRAM_OFFSET :
        wram_base + INSPECTOR.BATTLE_SLOT03_CURRENT_HP_WRAM_OFFSET + 2
    ] = (0x1234).to_bytes(2, "little")
    core_state[
        wram_base + INSPECTOR.BATTLE_SLOT03_MAX_HP_WRAM_OFFSET :
        wram_base + INSPECTOR.BATTLE_SLOT03_MAX_HP_WRAM_OFFSET + 2
    ] = (0x5678).to_bytes(2, "little")
    pc0_start = wram_base + INSPECTOR.FIELD_PC_RECORD_BASE_WRAM_OFFSET
    core_state[
        pc0_start
        + INSPECTOR.FIELD_PC_EQUIPMENT_OFFSET : pc0_start
        + INSPECTOR.FIELD_PC_EQUIPMENT_OFFSET
        + INSPECTOR.FIELD_PC_EQUIPMENT_LENGTH
    ] = bytes.fromhex("10203040")
    core_state[
        pc0_start + INSPECTOR.FIELD_PC_CURRENT_ATTACK_OFFSET
    ] = 0x55
    core_state[
        wram_base + INSPECTOR.FIELD_INVENTORY_ITEM_WRAM_OFFSET + 3
    ] = 0xC5
    core_state[
        wram_base + INSPECTOR.FIELD_INVENTORY_QUANTITY_WRAM_OFFSET + 3
    ] = 0x21
    battle_item_start = (
        wram_base
        + INSPECTOR.BATTLE_INVENTORY_WRAM_OFFSET
        + 8 * INSPECTOR.BATTLE_INVENTORY_ROW_SIZE
    )
    core_state[
        battle_item_start :
        battle_item_start + INSPECTOR.BATTLE_INVENTORY_ROW_SIZE
    ] = bytes.fromhex("c581022000")

    state_block = (
        bytes((0, 0))
        + struct.pack("<III", state_size, state_size, state_size)
        + core_state
    )
    frame = struct.pack("<I", 0) + b"\x00\x00\x00f"
    header = struct.pack(
        "<10I",
        EDITOR.MAGIC,
        EDITOR.VERSION,
        0,
        len(state_block),
        0,
        0,
        1,
        0,
        0,
        0,
    )
    return header + state_block + frame, bytes(sram), wram_base


class Bsv2WramCanaryTests(unittest.TestCase):
    def test_injects_only_candidate_and_inspector_finds_it(self) -> None:
        movie, sram, expected_base = make_fixture()
        result, base, target = TOOL.inject_canary(movie, sram)

        self.assertEqual(base, expected_base)
        self.assertEqual(target, base + LEGACY.TARGET_WRAM_OFFSET)
        before = TOOL.extract_raw_initial_core_state(movie)
        after = TOOL.extract_raw_initial_core_state(result)
        changed = {
            index
            for index, pair in enumerate(zip(before, after, strict=True))
            if pair[0] != pair[1]
        }
        self.assertTrue(changed)
        self.assertTrue(
            changed
            <= set(range(target, target + LEGACY.TARGET_LENGTH))
        )
        inspection = INSPECTOR.inspect_candidate(result, sram)
        self.assertTrue(inspection["canary_matches"])
        self.assertTrue(inspection["candidate_invariants_ok"])
        self.assertEqual(inspection["canary_occurrences"], [target])
        self.assertEqual(inspection["active_party_2980_2982_hex"], "000102")
        self.assertEqual(
            inspection["roster_2980_2988_hex"], "000102828004030605"
        )
        self.assertEqual(inspection["joined_flags_29af"], 0xFC)
        self.assertEqual(inspection["save_counter_299c"], 0)
        self.assertEqual(
            inspection["pc07_record_2830_287f_sha256"],
            inspection["saved_slot_record_0430_047f_sha256"],
        )
        self.assertTrue(inspection["pc07_record_matches_saved_slot"])
        self.assertEqual(
            inspection["epoch_name_2c4d_2c52_hex"], b"EPOCH ".hex()
        )
        self.assertEqual(inspection["location_id_0100"], 0x01DA)
        self.assertEqual(inspection["pending_request_0117"], 0x21)
        self.assertEqual(inspection["explore_mode_011f"], 1)
        self.assertEqual(inspection["dialog_state_0162"], 0)
        self.assertEqual(inspection["leader_object_0197"], 2)
        self.assertEqual(inspection["leader_x"], 0x0B80)
        self.assertEqual(inspection["leader_y"], 0x3CFF)
        self.assertEqual(inspection["storyline_7f0000"], 0xD6)
        self.assertEqual(inspection["tech_counts_2830_2836_hex"], "00" * 7)
        self.assertEqual(
            inspection["learned_masks_2837_283d_hex"],
            "00" * 7,
        )
        self.assertEqual(inspection["event11c_magic_flags_7f01e0"], 0xA5)
        self.assertEqual(inspection["event11c_robo_flags_7f01e2"], 0x5A)
        self.assertEqual(inspection["event11c_lap_scratch_7f021c"], 3)
        self.assertEqual(inspection["crono_remaining_tp_262d"], 0)
        self.assertEqual(inspection["marle_remaining_tp_267d"], 0)
        self.assertEqual(inspection["lucca_remaining_tp_26cd"], 0x8B88)
        self.assertEqual(inspection["frog_remaining_tp_276d"], 0)
        self.assertEqual(inspection["battle_pc1_current_hp_5e30"], 0x1111)
        self.assertEqual(inspection["battle_pc1_max_hp_5e32"], 0x2222)
        self.assertEqual(inspection["battle_pc1_current_mp_5e34"], 0x0033)
        self.assertEqual(inspection["battle_pc1_max_mp_5e36"], 0x0044)
        self.assertEqual(inspection["battle_slot03_current_hp_5fb0"], 0x1234)
        self.assertEqual(inspection["battle_slot03_max_hp_5fb2"], 0x5678)
        self.assertEqual(len(inspection["battle_combatant_records"]), 12)
        self.assertEqual(
            inspection["battle_combatant_records"][0],
            {
                "slot": 0,
                "record_wram": "$7E:5E2D",
                "identity": 0,
                "current_hp": 0x1111,
                "max_hp": 0x2222,
                "current_mp": 0x0033,
                "max_mp": 0x0044,
                "level": 0,
                "current_status_hex": "0000000000",
            },
        )
        self.assertEqual(
            inspection["battle_combatant_records"][3],
            {
                "slot": 3,
                "record_wram": "$7E:5FAD",
                "identity": 0,
                "current_hp": 0x1234,
                "max_hp": 0x5678,
                "current_mp": 0,
                "max_mp": 0,
                "level": 0,
                "current_status_hex": "0000000000",
            },
        )
        self.assertEqual(len(inspection["field_pc_records"]), 7)
        self.assertEqual(
            inspection["field_pc_records"][0],
            {
                "pc_id": 0,
                "record_wram": "$7E:2600",
                "equipment_wram": "$7E:2627",
                "equipment_hex": "10203040",
                "current_attack": 0x55,
            },
        )
        self.assertEqual(
            inspection["field_inventory_rows"],
            [{"slot": 3, "item_id": 0xC5, "quantity": 0x21}],
        )
        battle_row_8 = [
            row
            for row in inspection["battle_inventory_rows"]
            if row["row"] == 8
        ]
        self.assertEqual(
            battle_row_8,
            [
                {
                    "row": 8,
                    "wram": "$7E:15A8",
                    "item_id": 0xC5,
                    "target_mode": 0x81,
                    "flags": 0x02,
                    "quantity": 0x20,
                    "reserved": 0,
                    "record_hex": "c581022000",
                }
            ],
        )

        duplicate_core = bytearray(after)
        duplicate_start = expected_base + 0x7000
        duplicate_core[
            duplicate_start : duplicate_start + LEGACY.TARGET_LENGTH
        ] = LEGACY.make_canary()
        duplicate_movie = EDITOR.replace_initial_core_state(
            result, bytes(duplicate_core)
        )
        duplicate_inspection = INSPECTOR.inspect_candidate(
            duplicate_movie, sram
        )
        self.assertTrue(duplicate_inspection["canary_matches"])
        self.assertFalse(duplicate_inspection["candidate_invariants_ok"])
        self.assertEqual(
            duplicate_inspection["canary_occurrences"],
            [target, duplicate_start],
        )

    def test_rejects_nonzero_candidate(self) -> None:
        movie, sram, base = make_fixture()
        info = EDITOR.parse_movie(movie)
        core_state = bytearray(TOOL.extract_raw_initial_core_state(movie))
        core_state[base + LEGACY.TARGET_WRAM_OFFSET] = 1
        changed = EDITOR.replace_initial_core_state(movie, bytes(core_state))

        with self.assertRaisesRegex(RuntimeError, "not all zero"):
            TOOL.inject_canary(changed, sram)

    def test_pinned_current_layout_supports_title_checkpoint(self) -> None:
        movie, sram, _ = make_fixture()
        core_state = bytearray(TOOL.PINNED_CURRENT_STATE_LENGTH)
        core_state[: len(TOOL.PINNED_CURRENT_CORE_PREFIX)] = (
            TOOL.PINNED_CURRENT_CORE_PREFIX
        )
        pinned_movie = EDITOR.replace_initial_core_state(
            movie, bytes(core_state)
        )

        result, base, target = TOOL.inject_canary(
            pinned_movie,
            None,
            use_pinned_current_layout=True,
        )
        self.assertEqual(base, TOOL.PINNED_CURRENT_WRAM_STATE_OFFSET)
        self.assertEqual(target, base + LEGACY.TARGET_WRAM_OFFSET)
        before = TOOL.extract_raw_initial_core_state(pinned_movie)
        after = TOOL.extract_raw_initial_core_state(result)
        differences = {
            index
            for index, pair in enumerate(zip(before, after, strict=True))
            if pair[0] != pair[1]
        }
        self.assertEqual(
            differences,
            set(range(target, target + LEGACY.TARGET_LENGTH)),
        )

        with self.assertRaisesRegex(RuntimeError, "exclusive"):
            TOOL.inject_canary(
                pinned_movie,
                sram,
                use_pinned_current_layout=True,
            )
        with self.assertRaisesRegex(RuntimeError, "SRAM is required"):
            TOOL.inject_canary(pinned_movie, None)

        wrong_prefix = bytearray(before)
        wrong_prefix[8] ^= 0x01
        wrong_movie = EDITOR.replace_initial_core_state(
            pinned_movie, bytes(wrong_prefix)
        )
        with self.assertRaisesRegex(RuntimeError, "not the pinned"):
            TOOL.inject_canary(
                wrong_movie,
                None,
                use_pinned_current_layout=True,
            )

    def test_inspects_rastate_container(self) -> None:
        movie, sram, base = make_fixture()
        core_state = TOOL.extract_raw_initial_core_state(movie)
        container = RASTATE.make_minimal_container(core_state)
        result = INSPECTOR.inspect_candidate(container, sram)

        self.assertEqual(result["container"], "RASTATE")
        self.assertEqual(result["state_wram_base"], base)
        self.assertTrue(result["target_all_zero"])

    def test_inspector_uses_pinned_current_layout_after_reset(self) -> None:
        state_size = INSPECTOR.PINNED_CURRENT_STATE_LENGTH
        core_state = bytearray(state_size)
        core_state[: len(INSPECTOR.PINNED_CURRENT_CORE_PREFIX)] = (
            INSPECTOR.PINNED_CURRENT_CORE_PREFIX
        )
        struct.pack_into("<I", core_state, 4, state_size)
        container = RASTATE.make_minimal_container(bytes(core_state))
        _, sram, _ = make_fixture()

        result = INSPECTOR.inspect_candidate(container, sram)
        self.assertEqual(
            result["wram_anchor_method"], "pinned-current-core-layout"
        )
        self.assertEqual(
            result["state_wram_base"],
            INSPECTOR.PINNED_CURRENT_WRAM_STATE_OFFSET,
        )
        self.assertTrue(result["target_all_zero"])


if __name__ == "__main__":
    unittest.main()
