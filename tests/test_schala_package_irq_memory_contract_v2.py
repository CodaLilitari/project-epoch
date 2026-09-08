"""Original synthetic CPU specimens; no game input or native execution."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_schala_package_irq_memory_contract_v2 as v

BASE = 0xC00000
SAVE = bytes.fromhex("C2 30 48 DA 5A 8B 0B")
RESTORE = bytes.fromhex("C2 30 2B AB 7A FA 68 40")
ZERO_D = bytes.fromhex("A9 00 00 5B")
ZERO_BANK = bytes.fromhex("E2 20 A9 00 48 AB C2 20")


def specimen(body=b"", *, program=None, extra=None, **kwargs):
    program = SAVE + body + RESTORE if program is None else program
    pieces = {BASE: program, **(extra or {})}
    memory = {address + index: byte for address, data in pieces.items()
              for index, byte in enumerate(data)}
    def read(address, count):
        return bytes(memory[a] for a in range(address, address + count) if a in memory)
    bounds = tuple((address, address + len(data)) for address, data in pieces.items())
    return v.walk_memory(read, entry=BASE, bounds=bounds, **kwargs)


class IrqMemoryContractTests(unittest.TestCase):
    def fails(self, body=b"", *, pattern=None, **kwargs):
        with self.assertRaisesRegex(v.ContractError, pattern or "."):
            specimen(body, **kwargs)

    def test_all_native_widths_preserve_all_symbolic_saved_bytes(self):
        result = specimen()
        self.assertEqual(result["maximum_depth_including_hardware"], 13)
        self.assertEqual(len(result["balanced_rti_contexts"]), 4)
        self.assertEqual(result["physical_wram_write_bytes"], [])

    def test_unsaved_accumulator_change_refuses(self):
        self.fails(program=bytes.fromhex("C2 30 A9 00 00 40"), pattern="restoration")

    def test_unsaved_hidden_b_change_refuses(self):
        self.fails(program=bytes.fromhex("C2 30 A9 01 00 E2 20 40"))

    def test_swapped_accumulator_index_saves_refuse(self):
        self.fails(program=bytes.fromhex("C2 30 48 DA 68 FA 40"), pattern="restoration")

    def test_wrong_d_restore_refuses(self):
        self.fails(program=SAVE + bytes.fromhex("2B A9 00 00 5B AB 7A FA 68 40"))

    def test_wrong_dbr_restore_refuses(self):
        self.fails(program=SAVE + bytes.fromhex("2B AB E2 20 A9 00 48 AB C2 30 7A FA 68 40"))

    def test_direct_write_requires_known_d(self):
        self.fails(bytes.fromhex("85 70"), pattern="unknown D")

    def test_absolute_write_requires_known_dbr(self):
        self.fails(bytes.fromhex("8D 00 30"), pattern="unknown DBR")

    def test_long_store_needs_no_incoming_bank(self):
        r = specimen(bytes.fromhex("8F 00 30 7E"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x3000, 0x3001])

    def test_dp_word_uses_d_plus_operand_and_two_bytes(self):
        r = specimen(bytes.fromhex("A9 00 05 5B 85 B0"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x5B0, 0x5B1])

    def test_dp_bank_zero_word_wrap(self):
        r = specimen(bytes.fromhex("A9 FF FF 5B 85 00"))
        self.assertEqual(r["ordinary_cpu_write_contexts"][0]["bus_addresses_in_write_order"],
                         ["$00FFFF", "$000000"])

    def test_absolute_word_advances_to_next_bank(self):
        r = specimen(ZERO_BANK + bytes.fromhex("8D FF FF"))
        self.assertEqual(r["ordinary_cpu_write_contexts"][0]["bus_addresses_in_write_order"],
                         ["$00FFFF", "$010000"])

    def test_absolute_high_byte_alias_detected(self):
        self.fails(ZERO_BANK + bytes.fromhex("8D A4 06"), pattern="aliases")

    def test_dp_alias_to_live_irq_save_refuses(self):
        self.fails(bytes.fromhex("A9 90 06 5B 85 10"), pattern="aliases")

    def test_long_bank80_mirror_alias_refuses(self):
        self.fails(bytes.fromhex("8F A0 06 80"), pattern="aliases")

    def test_long_bank40_has_no_wram_mirror(self):
        r = specimen(bytes.fromhex("8F A0 06 40"))
        self.assertEqual(r["physical_wram_write_bytes"], [])

    def test_protected_caller_write_refuses(self):
        self.fails(bytes.fromhex("8F DC 06 7E"), pattern="aliases")

    def test_caller_high_byte_only_write_refuses(self):
        self.fails(bytes.fromhex("8F DD 06 7E"), pattern="aliases")

    def test_m8_store_preserves_single_byte_footprint(self):
        r = specimen(ZERO_D + bytes.fromhex("E2 20 85 70"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x70])

    def test_x_width_controls_stx_and_sty_independently(self):
        r = specimen(bytes.fromhex("E2 20 A9 7E 48 AB C2 20 E2 10 8E 00 30 8C 10 30"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x3000, 0x3010])

    def test_m16_rmw_writes_high_first(self):
        r = specimen(ZERO_D + bytes.fromhex("E6 70"))
        self.assertEqual(r["ordinary_cpu_write_contexts"][0]["bus_addresses_in_write_order"],
                         ["$000071", "$000070"])

    def test_mvn_expands_inclusive_count_and_sets_dbr(self):
        r = specimen(bytes.fromhex("A0 00 40 A9 02 00 54 7E CE 8D 10 40"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x4000, 0x4001, 0x4002, 0x4010, 0x4011])

    def test_mvn_zero_count_still_writes_one_byte(self):
        r = specimen(bytes.fromhex("A0 00 40 A9 00 00 54 7E CE"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x4000])

    def test_mvn_destination_wrap_stays_in_destination_bank(self):
        r = specimen(bytes.fromhex("A0 FF FF A9 01 00 54 7F CE"))
        self.assertEqual(r["physical_wram_write_bytes"], [0x10000, 0x1FFFF])

    def test_mvn_unknown_destination_refuses(self):
        self.fails(bytes.fromhex("A9 00 00 54 7E CE"), pattern="MVN")

    def test_mvn_unknown_count_refuses(self):
        self.fails(bytes.fromhex("A0 00 40 54 7E CE"), pattern="MVN")

    def test_mvn_x8_requires_separate_semantics(self):
        self.fails(bytes.fromhex("A0 00 40 A9 00 00 E2 10 54 7E CE"), pattern="MVN")

    def test_mvn_live_stack_alias_refuses(self):
        self.fails(bytes.fromhex("A0 9F 06 A9 02 00 54 7E CE"), pattern="aliases")

    def test_mvn_large_extent_refuses(self):
        self.fails(bytes.fromhex("A0 00 40 A9 FF FF 54 7E CE"), pattern="extent")

    def test_nested_near_and_long_calls_preserve_and_count(self):
        body = bytes.fromhex("20 00 01")
        extra = {BASE + 0x100: bytes.fromhex("22 00 02 C1 60"),
                 0xC10200: bytes.fromhex("8B AB 6B")}
        r = specimen(body, extra=extra)
        self.assertEqual(r["maximum_depth_including_hardware"], 19)
        self.assertEqual(len(r["direct_calls"]), 2)

    def test_data_pop_cannot_consume_call_frame(self):
        self.fails(bytes.fromhex("20 00 01"), extra={BASE + 0x100: bytes.fromhex("68 60")})

    def test_return_kind_mismatch_refuses(self):
        self.fails(bytes.fromhex("20 00 01"), extra={BASE + 0x100: bytes.fromhex("6B")})

    def test_leftover_local_cannot_be_skipped(self):
        self.fails(bytes.fromhex("20 00 01"), extra={BASE + 0x100: bytes.fromhex("48 60")})

    def test_irq_unmasking_refuses(self):
        self.fails(bytes.fromhex("C2 04"), pattern="unmasking")

    def test_php_plp_restores_exact_widths(self):
        r = specimen(bytes.fromhex("08 E2 30 28"))
        self.assertEqual(len(r["balanced_rti_contexts"]), 4)

    def test_unknown_plp_refuses(self):
        self.fails(bytes.fromhex("E2 20 48 28"), pattern="typed PHP")

    def test_all_branch_outcomes_checked(self):
        self.fails(bytes.fromhex("D0 04 8F A0 06 7E"), pattern="aliases")

    def test_unknown_control_flow_refuses(self):
        for op in (0xFC, 0x7C, 0x5C, 0x1B, 0x9A, 0xFB):
            with self.subTest(op=op): self.fails(bytes([op, 0, 0, 0]))

    def test_stack_guard_rejects_non_wram_sp_and_booleans(self):
        for sp in (True, 0x2000, -1, 3):
            with self.subTest(sp=sp): self.fails(interrupted_sp=sp)

    def test_stack_push_depth_cannot_wrap(self):
        self.fails(interrupted_sp=5, protected=())

    def test_stack_depth_equal_to_sp_ends_at_zero(self):
        r = specimen(interrupted_sp=13, protected=())
        self.assertEqual(r["lowest_sp"], 0)
        self.fails(interrupted_sp=12, protected=())

    def test_protected_stack_overlap_is_not_assumed_away(self):
        self.fails(protected=((0x690, 0x6A1),))

    def test_state_budget_fail_closed(self):
        self.fails(state_budget=2)

    def test_truncated_instruction_refuses(self):
        self.fails(program=b"\xA9")

    def test_branch_into_operand_refuses_before_interpreting_byte(self):
        self.fails(bytes.fromhex("D0 01 A9 00 00"), pattern="operand|overlapping")

    def test_same_pc_incompatible_widths_refuse(self):
        self.fails(bytes.fromhex("D0 02 E2 20 A9 00 00"), pattern="incompatible width")

    def test_initial_hardware_overlap_refuses_even_at_immediate_rti(self):
        self.fails(program=b"\x40", protected=((0x06A1, 0x06A2),), pattern="initial native hardware")

    def test_instruction_cannot_straddle_program_bank(self):
        state = v.initial_state(0xC0FFFF, False, False)
        with self.assertRaisesRegex(v.ContractError, "program-bank"):
            v.decode(lambda address, count: bytes.fromhex("A9 00 00")[:count],
                     state, ((0xC0FFFF, 0xC10002),))

    def test_physical_bank_mirror_geometry(self):
        for bank in (0, 0x3F, 0x80, 0xBF):
            self.assertEqual(v.physical_wram(bank << 16 | 0x1FFF), 0x1FFF)
            self.assertIsNone(v.physical_wram(bank << 16 | 0x2000))
        for bank in (0x40, 0x7D, 0xC0, 0xFF):
            self.assertIsNone(v.physical_wram(bank << 16 | 0x600))
        self.assertEqual(v.physical_wram(0x7F0600), 0x10600)


if __name__ == "__main__":
    unittest.main()
