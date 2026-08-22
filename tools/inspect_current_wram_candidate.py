#!/usr/bin/env python3
"""Inspect Project Epoch's WRAM candidate in BSV2 or RASTATE core state."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import inject_bsv2_wram_canary as bsv2_canary
import inject_bsv_wram_canary as canary
import retroarch_rastate


PINNED_CURRENT_STATE_LENGTH = 290_423
PINNED_CURRENT_CORE_PREFIX = b"BST1" + b"\x77\x6E\x04\x00" + b"115.1\x00"
PINNED_CURRENT_WRAM_STATE_OFFSET = 0x2284
ACTIVE_PARTY_WRAM_OFFSET = 0x2980
ACTIVE_PARTY_LENGTH = 3
ROSTER_WRAM_OFFSET = 0x2980
ROSTER_LENGTH = 9
JOINED_FLAGS_WRAM_OFFSET = 0x29AF
SAVE_COUNTER_WRAM_OFFSET = 0x299C
PC07_RECORD_WRAM_OFFSET = 0x2830
PC07_RECORD_LENGTH = 0x50
PC07_RECORD_SAVE_OFFSET = 0x0430
SAVE_SLOT_LENGTH = 0x0A00
EPOCH_NAME_WRAM_OFFSET = 0x2C4D
EPOCH_NAME_LENGTH = 6
LOCATION_ID_WRAM_OFFSET = 0x0100
PENDING_REQUEST_WRAM_OFFSET = 0x0117
EXPLORE_MODE_WRAM_OFFSET = 0x011F
DIALOG_STATE_WRAM_OFFSET = 0x0162
LEADER_OBJECT_WRAM_OFFSET = 0x0197
OBJECT_X_WRAM_OFFSET = 0x1800
OBJECT_Y_WRAM_OFFSET = 0x1880
STORYLINE_WRAM_OFFSET = 0x10000
TECH_COUNTS_WRAM_OFFSET = 0x2830
TECH_COUNTS_LENGTH = 7
LEARNED_MASKS_WRAM_OFFSET = 0x2837
LEARNED_MASKS_LENGTH = 7
EVENT11C_MAGIC_FLAGS_WRAM_OFFSET = 0x101E0
EVENT11C_ROBO_FLAGS_WRAM_OFFSET = 0x101E2
EVENT11C_LAP_SCRATCH_WRAM_OFFSET = 0x1021C
CRONO_REMAINING_TP_WRAM_OFFSET = 0x262D
MARLE_REMAINING_TP_WRAM_OFFSET = 0x267D
LUCCA_REMAINING_TP_WRAM_OFFSET = 0x26CD
FROG_REMAINING_TP_WRAM_OFFSET = 0x276D
BATTLE_PC1_CURRENT_HP_WRAM_OFFSET = 0x5E30
BATTLE_PC1_MAX_HP_WRAM_OFFSET = 0x5E32
BATTLE_PC1_CURRENT_MP_WRAM_OFFSET = 0x5E34
BATTLE_PC1_MAX_MP_WRAM_OFFSET = 0x5E36
BATTLE_SLOT03_CURRENT_HP_WRAM_OFFSET = 0x5FB0
BATTLE_SLOT03_MAX_HP_WRAM_OFFSET = 0x5FB2
BATTLE_COMBATANT_RECORD_BASE_WRAM_OFFSET = 0x5E2D
BATTLE_COMBATANT_RECORD_STRIDE = 0x80
BATTLE_COMBATANT_RECORD_COUNT = 12
BATTLE_COMBATANT_CURRENT_HP_OFFSET = 0x03
BATTLE_COMBATANT_MAX_HP_OFFSET = 0x05
BATTLE_COMBATANT_CURRENT_MP_OFFSET = 0x07
BATTLE_COMBATANT_MAX_MP_OFFSET = 0x09
BATTLE_COMBATANT_LEVEL_OFFSET = 0x12
BATTLE_COMBATANT_CURRENT_STATUS_OFFSET = 0x1D
BATTLE_COMBATANT_CURRENT_STATUS_LENGTH = 5
FIELD_PC_RECORD_BASE_WRAM_OFFSET = 0x2600
FIELD_PC_RECORD_SIZE = 0x50
FIELD_PC_RECORD_COUNT = 7
FIELD_PC_EQUIPMENT_OFFSET = 0x27
FIELD_PC_EQUIPMENT_LENGTH = 4
FIELD_PC_CURRENT_ATTACK_OFFSET = 0x3D
FIELD_INVENTORY_ITEM_WRAM_OFFSET = 0x2400
FIELD_INVENTORY_QUANTITY_WRAM_OFFSET = 0x2500
FIELD_INVENTORY_SLOT_COUNT = 0x100
BATTLE_INVENTORY_WRAM_OFFSET = 0x1580
BATTLE_INVENTORY_LENGTH = 0x500
BATTLE_INVENTORY_ROW_SIZE = 5


def _battle_combatant_rows(
    core_state: bytes,
    wram_base: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for slot in range(BATTLE_COMBATANT_RECORD_COUNT):
        record_wram = (
            BATTLE_COMBATANT_RECORD_BASE_WRAM_OFFSET
            + slot * BATTLE_COMBATANT_RECORD_STRIDE
        )
        record_start = wram_base + record_wram
        status_start = (
            record_start + BATTLE_COMBATANT_CURRENT_STATUS_OFFSET
        )
        rows.append(
            {
                "slot": slot,
                "record_wram": f"$7E:{record_wram:04X}",
                "identity": core_state[record_start],
                "current_hp": int.from_bytes(
                    core_state[
                        record_start
                        + BATTLE_COMBATANT_CURRENT_HP_OFFSET :
                        record_start
                        + BATTLE_COMBATANT_CURRENT_HP_OFFSET
                        + 2
                    ],
                    "little",
                ),
                "max_hp": int.from_bytes(
                    core_state[
                        record_start
                        + BATTLE_COMBATANT_MAX_HP_OFFSET :
                        record_start
                        + BATTLE_COMBATANT_MAX_HP_OFFSET
                        + 2
                    ],
                    "little",
                ),
                "current_mp": int.from_bytes(
                    core_state[
                        record_start
                        + BATTLE_COMBATANT_CURRENT_MP_OFFSET :
                        record_start
                        + BATTLE_COMBATANT_CURRENT_MP_OFFSET
                        + 2
                    ],
                    "little",
                ),
                "max_mp": int.from_bytes(
                    core_state[
                        record_start
                        + BATTLE_COMBATANT_MAX_MP_OFFSET :
                        record_start
                        + BATTLE_COMBATANT_MAX_MP_OFFSET
                        + 2
                    ],
                    "little",
                ),
                "level": core_state[
                    record_start + BATTLE_COMBATANT_LEVEL_OFFSET
                ],
                "current_status_hex": core_state[
                    status_start :
                    status_start + BATTLE_COMBATANT_CURRENT_STATUS_LENGTH
                ].hex(),
            }
        )
    return rows


def _field_pc_rows(
    core_state: bytes,
    wram_base: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for pc_id in range(FIELD_PC_RECORD_COUNT):
        record_start = (
            wram_base
            + FIELD_PC_RECORD_BASE_WRAM_OFFSET
            + pc_id * FIELD_PC_RECORD_SIZE
        )
        equipment_start = record_start + FIELD_PC_EQUIPMENT_OFFSET
        equipment_end = equipment_start + FIELD_PC_EQUIPMENT_LENGTH
        rows.append(
            {
                "pc_id": pc_id,
                "record_wram": (
                    f"$7E:{FIELD_PC_RECORD_BASE_WRAM_OFFSET + pc_id * FIELD_PC_RECORD_SIZE:04X}"
                ),
                "equipment_wram": (
                    f"$7E:{FIELD_PC_RECORD_BASE_WRAM_OFFSET + pc_id * FIELD_PC_RECORD_SIZE + FIELD_PC_EQUIPMENT_OFFSET:04X}"
                ),
                "equipment_hex": core_state[
                    equipment_start:equipment_end
                ].hex(),
                "current_attack": core_state[
                    record_start + FIELD_PC_CURRENT_ATTACK_OFFSET
                ],
            }
        )
    return rows


def _field_inventory_rows(
    core_state: bytes,
    wram_base: int,
) -> list[dict[str, object]]:
    item_start = wram_base + FIELD_INVENTORY_ITEM_WRAM_OFFSET
    quantity_start = wram_base + FIELD_INVENTORY_QUANTITY_WRAM_OFFSET
    rows: list[dict[str, object]] = []
    for slot in range(FIELD_INVENTORY_SLOT_COUNT):
        quantity = core_state[quantity_start + slot]
        if quantity == 0:
            continue
        rows.append(
            {
                "slot": slot,
                "item_id": core_state[item_start + slot],
                "quantity": quantity,
            }
        )
    return rows


def _battle_inventory_rows(
    core_state: bytes,
    wram_base: int,
) -> list[dict[str, object]]:
    start = wram_base + BATTLE_INVENTORY_WRAM_OFFSET
    rows: list[dict[str, object]] = []
    for relative in range(0, BATTLE_INVENTORY_LENGTH, BATTLE_INVENTORY_ROW_SIZE):
        record = core_state[
            start + relative : start + relative + BATTLE_INVENTORY_ROW_SIZE
        ]
        quantity = record[3]
        if quantity == 0:
            continue
        rows.append(
            {
                "row": relative // BATTLE_INVENTORY_ROW_SIZE,
                "wram": f"$7E:{BATTLE_INVENTORY_WRAM_OFFSET + relative:04X}",
                "item_id": record[0],
                "target_mode": record[1],
                "flags": record[2],
                "quantity": quantity,
                "reserved": record[4],
                "record_hex": record.hex(),
            }
        )
    return rows


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_core_state(source: bytes) -> tuple[bytes, str]:
    if source[:4] == b"2VSB":
        return bsv2_canary.extract_raw_initial_core_state(source), "BSV2"
    if source[:7] == b"RASTATE":
        return retroarch_rastate.extract_memory(source), "RASTATE"
    if source[:4] == b"BST1":
        return source, "BST1"
    raise RuntimeError("unsupported state container")


def inspect_candidate(
    source: bytes,
    sram: bytes,
    *,
    save_slot: int = 1,
) -> dict[str, object]:
    core_state, container = extract_core_state(source)
    anchor_method = "loaded-record-pair"
    try:
        wram_base = canary.locate_live_wram_base(
            core_state, sram, save_slot=save_slot
        )
    except RuntimeError:
        if not (
            len(core_state) == PINNED_CURRENT_STATE_LENGTH
            and core_state.startswith(PINNED_CURRENT_CORE_PREFIX)
        ):
            raise
        wram_base = PINNED_CURRENT_WRAM_STATE_OFFSET
        anchor_method = "pinned-current-core-layout"
    start = wram_base + canary.TARGET_WRAM_OFFSET
    end = start + canary.TARGET_LENGTH
    active_party_start = wram_base + ACTIVE_PARTY_WRAM_OFFSET
    roster_start = wram_base + ROSTER_WRAM_OFFSET
    live_pc07_start = wram_base + PC07_RECORD_WRAM_OFFSET
    live_pc07 = core_state[
        live_pc07_start : live_pc07_start + PC07_RECORD_LENGTH
    ]
    saved_pc07_start = (
        (save_slot - 1) * SAVE_SLOT_LENGTH + PC07_RECORD_SAVE_OFFSET
    )
    saved_pc07 = sram[
        saved_pc07_start : saved_pc07_start + PC07_RECORD_LENGTH
    ]
    leader_object = core_state[wram_base + LEADER_OBJECT_WRAM_OFFSET]
    leader_x_start = wram_base + OBJECT_X_WRAM_OFFSET + leader_object
    leader_y_start = wram_base + OBJECT_Y_WRAM_OFFSET + leader_object
    actual = core_state[start:end]
    expected = canary.make_canary()
    front_guard = core_state[start - 4 : start]
    rear_guard = core_state[end : end + 0x10]
    occurrences: list[int] = []
    cursor = 0
    while True:
        hit = core_state.find(expected, cursor)
        if hit < 0:
            break
        occurrences.append(hit)
        cursor = hit + 1
    candidate_invariants_ok = (
        actual == expected
        and occurrences == [start]
        and not any(front_guard)
        and not any(rear_guard)
    )
    return {
        "container": container,
        "container_length": len(source),
        "container_sha256": sha256(source),
        "core_state_length": len(core_state),
        "core_state_sha256": sha256(core_state),
        "state_wram_base": wram_base,
        "wram_anchor_method": anchor_method,
        "target_wram": f"7E:{canary.TARGET_WRAM_OFFSET:04X}",
        "target_state_offset": start,
        "target_length": canary.TARGET_LENGTH,
        "expected_canary_sha256": sha256(expected),
        "actual_target_sha256": sha256(actual),
        "canary_matches": actual == expected,
        "candidate_invariants_ok": candidate_invariants_ok,
        "target_all_zero": not any(actual),
        "canary_occurrences": occurrences,
        "front_guard_hex": front_guard.hex(),
        "rear_guard_hex": rear_guard.hex(),
        "active_party_2980_2982_hex": core_state[
            active_party_start : active_party_start + ACTIVE_PARTY_LENGTH
        ].hex(),
        "roster_2980_2988_hex": core_state[
            roster_start : roster_start + ROSTER_LENGTH
        ].hex(),
        "joined_flags_29af": core_state[
            wram_base + JOINED_FLAGS_WRAM_OFFSET
        ],
        "save_counter_299c": core_state[
            wram_base + SAVE_COUNTER_WRAM_OFFSET
        ],
        "pc07_record_2830_287f_sha256": sha256(live_pc07),
        "saved_slot_record_0430_047f_sha256": sha256(saved_pc07),
        "pc07_record_matches_saved_slot": live_pc07 == saved_pc07,
        "epoch_name_2c4d_2c52_hex": core_state[
            wram_base
            + EPOCH_NAME_WRAM_OFFSET : wram_base
            + EPOCH_NAME_WRAM_OFFSET
            + EPOCH_NAME_LENGTH
        ].hex(),
        "location_id_0100": int.from_bytes(
            core_state[
                wram_base
                + LOCATION_ID_WRAM_OFFSET : wram_base
                + LOCATION_ID_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "pending_request_0117": core_state[
            wram_base + PENDING_REQUEST_WRAM_OFFSET
        ],
        "explore_mode_011f": core_state[
            wram_base + EXPLORE_MODE_WRAM_OFFSET
        ],
        "dialog_state_0162": core_state[
            wram_base + DIALOG_STATE_WRAM_OFFSET
        ],
        "leader_object_0197": leader_object,
        "leader_x": int.from_bytes(
            core_state[leader_x_start : leader_x_start + 2], "little"
        ),
        "leader_y": int.from_bytes(
            core_state[leader_y_start : leader_y_start + 2], "little"
        ),
        "storyline_7f0000": core_state[
            wram_base + STORYLINE_WRAM_OFFSET
        ],
        "tech_counts_2830_2836_hex": core_state[
            wram_base
            + TECH_COUNTS_WRAM_OFFSET : wram_base
            + TECH_COUNTS_WRAM_OFFSET
            + TECH_COUNTS_LENGTH
        ].hex(),
        "learned_masks_2837_283d_hex": core_state[
            wram_base
            + LEARNED_MASKS_WRAM_OFFSET : wram_base
            + LEARNED_MASKS_WRAM_OFFSET
            + LEARNED_MASKS_LENGTH
        ].hex(),
        "event11c_magic_flags_7f01e0": core_state[
            wram_base + EVENT11C_MAGIC_FLAGS_WRAM_OFFSET
        ],
        "event11c_robo_flags_7f01e2": core_state[
            wram_base + EVENT11C_ROBO_FLAGS_WRAM_OFFSET
        ],
        "event11c_lap_scratch_7f021c": core_state[
            wram_base + EVENT11C_LAP_SCRATCH_WRAM_OFFSET
        ],
        "crono_remaining_tp_262d": int.from_bytes(
            core_state[
                wram_base
                + CRONO_REMAINING_TP_WRAM_OFFSET : wram_base
                + CRONO_REMAINING_TP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "marle_remaining_tp_267d": int.from_bytes(
            core_state[
                wram_base
                + MARLE_REMAINING_TP_WRAM_OFFSET : wram_base
                + MARLE_REMAINING_TP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "lucca_remaining_tp_26cd": int.from_bytes(
            core_state[
                wram_base
                + LUCCA_REMAINING_TP_WRAM_OFFSET : wram_base
                + LUCCA_REMAINING_TP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "frog_remaining_tp_276d": int.from_bytes(
            core_state[
                wram_base
                + FROG_REMAINING_TP_WRAM_OFFSET : wram_base
                + FROG_REMAINING_TP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_pc1_current_hp_5e30": int.from_bytes(
            core_state[
                wram_base
                + BATTLE_PC1_CURRENT_HP_WRAM_OFFSET : wram_base
                + BATTLE_PC1_CURRENT_HP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_pc1_max_hp_5e32": int.from_bytes(
            core_state[
                wram_base
                + BATTLE_PC1_MAX_HP_WRAM_OFFSET : wram_base
                + BATTLE_PC1_MAX_HP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_pc1_current_mp_5e34": int.from_bytes(
            core_state[
                wram_base
                + BATTLE_PC1_CURRENT_MP_WRAM_OFFSET : wram_base
                + BATTLE_PC1_CURRENT_MP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_pc1_max_mp_5e36": int.from_bytes(
            core_state[
                wram_base
                + BATTLE_PC1_MAX_MP_WRAM_OFFSET : wram_base
                + BATTLE_PC1_MAX_MP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_slot03_current_hp_5fb0": int.from_bytes(
            core_state[
                wram_base
                + BATTLE_SLOT03_CURRENT_HP_WRAM_OFFSET : wram_base
                + BATTLE_SLOT03_CURRENT_HP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_slot03_max_hp_5fb2": int.from_bytes(
            core_state[
                wram_base
                + BATTLE_SLOT03_MAX_HP_WRAM_OFFSET : wram_base
                + BATTLE_SLOT03_MAX_HP_WRAM_OFFSET
                + 2
            ],
            "little",
        ),
        "battle_combatant_records": _battle_combatant_rows(
            core_state, wram_base
        ),
        "field_pc_records": _field_pc_rows(core_state, wram_base),
        "field_inventory_rows": _field_inventory_rows(
            core_state, wram_base
        ),
        "battle_inventory_rows": _battle_inventory_rows(
            core_state, wram_base
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("states", nargs="+", type=pathlib.Path)
    parser.add_argument("--srm", required=True, type=pathlib.Path)
    parser.add_argument("--slot", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--require-canary", action="store_true")
    parser.add_argument("--require-zero", action="store_true")
    args = parser.parse_args()
    if args.require_canary and args.require_zero:
        parser.error("--require-canary and --require-zero are mutually exclusive")

    sram = args.srm.read_bytes()
    failed = False
    for path in args.states:
        result = inspect_candidate(
            path.read_bytes(), sram, save_slot=args.slot
        )
        result["path"] = str(path)
        print(json.dumps(result, indent=2, sort_keys=True))
        if args.require_canary and not result["candidate_invariants_ok"]:
            failed = True
        if args.require_zero and not result["target_all_zero"]:
            failed = True
    if failed:
        raise SystemExit("one or more states failed the requested condition")


if __name__ == "__main__":
    main()
