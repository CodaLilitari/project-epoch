from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "inspect_ct_srm.py"
SPEC = importlib.util.spec_from_file_location("inspect_ct_srm", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {PATH}")
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class InspectCtSrmTests(unittest.TestCase):
    def test_checksum_chains_carry_between_words(self) -> None:
        slot = bytearray(TOOL.SLOT_SIZE)
        slot[-2:] = b"\xFF\xFF"
        slot[-4:-2] = b"\x01\x00"
        self.assertEqual(TOOL.slot_checksum(bytes(slot)), 1)

    def test_inspects_valid_slot_and_routing_anchors(self) -> None:
        sram = bytearray(TOOL.SRAM_SIZE)
        slot = bytearray(TOOL.SLOT_SIZE)
        slot[TOOL.ACTIVE_PARTY_OFFSET : TOOL.ACTIVE_PARTY_OFFSET + 9] = (
            bytes.fromhex("000102828004030605")
        )
        slot[
            TOOL.LOCATION_BLOCK_OFFSET : TOOL.LOCATION_BLOCK_OFFSET + 2
        ] = (0x01DA).to_bytes(2, "little")
        slot[TOOL.EVENT_FLAGS_OFFSET] = 0xD6
        slot[
            TOOL.EPOCH_NAME_OFFSET : TOOL.EPOCH_NAME_OFFSET + TOOL.NAME_LENGTH
        ] = b"EPOCH "
        for pc_id in range(TOOL.PC_COUNT):
            slot[
                TOOL.PC_RECORD_OFFSET
                + pc_id * TOOL.PC_RECORD_SIZE
                + TOOL.PC_LEVEL_OFFSET
            ] = 40 + pc_id
        sram[: TOOL.SLOT_SIZE] = slot
        checksum = TOOL.slot_checksum(bytes(slot))
        sram[TOOL.CHECKSUM_TABLE_OFFSET : TOOL.CHECKSUM_TABLE_OFFSET + 2] = (
            checksum.to_bytes(2, "little")
        )
        sram[TOOL.MAGIC_TABLE_OFFSET : TOOL.MAGIC_TABLE_OFFSET + 2] = (
            TOOL.SLOT_MAGIC.to_bytes(2, "little")
        )

        result = TOOL.inspect_sram(bytes(sram))
        inspected = result["slots"][0]
        self.assertTrue(inspected["valid"])
        self.assertEqual(inspected["location_id"], 0x01DA)
        self.assertEqual(inspected["storyline"], 0xD6)
        self.assertEqual(inspected["active_party_hex"], "000102")
        self.assertEqual(inspected["roster_hex"], "000102828004030605")
        self.assertEqual(inspected["pc_levels"], list(range(40, 47)))
        self.assertEqual(inspected["epoch_name_hex"], b"EPOCH ".hex())

    def test_rejects_wrong_length(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly"):
            TOOL.inspect_sram(bytes(TOOL.SRAM_SIZE - 1))


if __name__ == "__main__":
    unittest.main()
