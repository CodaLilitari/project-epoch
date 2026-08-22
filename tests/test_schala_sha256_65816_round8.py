from __future__ import annotations

import hashlib
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import validate_schala_sha256_65816_round8 as TOOL  # noqa: E402


class SchalaSha25665816Round8Tests(unittest.TestCase):
    def test_proven_baseline_fast_and_builder_inputs_are_frozen(self) -> None:
        hashes = TOOL.validate_frozen_inputs()
        self.assertEqual(len(hashes), 8)

    def test_relocatable_source_contract_and_exact_bounds(self) -> None:
        result = TOOL.validate_source_contract()
        self.assertEqual(
            result["source_sha256"],
            "90c2c7d887089e01c717c7356c0bd4d65b595c4793b05ea18c18bd309cb3cdf3",
        )
        self.assertEqual(result["scratch_size"], 0xC2)
        self.assertEqual(result["code_limit"], 0x6000)
        self.assertEqual(result["table_bytes"], 0x4000)
        self.assertEqual(result["entry_save_frame_size"], 10)
        self.assertEqual(result["max_nested_jsr_count"], 2)
        self.assertEqual(result["max_stack_growth_after_entry"], 14)
        self.assertEqual(result["max_stack_growth_with_caller_jsl"], 17)
        self.assertEqual(result["rounds"], 64)
        self.assertEqual(result["groups"], 8)
        self.assertEqual(result["rounds_per_group"], 8)
        self.assertEqual(result["runtime_k_table_bytes"], 0)
        self.assertFalse(result["runtime_round_counter_traffic"])
        self.assertFalse(result["placed"])
        self.assertFalse(result["writes_bank_30"])

    def test_compile_time_k_constants_match_proven_baseline(self) -> None:
        bases, constants = TOOL.parse_round_constants()
        self.assertEqual(bases, tuple(range(0, 64, 8)))
        self.assertEqual(len(constants), 64)
        source = TOOL.ASM_PATH.read_text(encoding="utf-8")
        corrupted = source.replace("$428A, $2F98", "$428A, $2F99", 1)
        with self.assertRaises(TOOL.Round8Sha256Error):
            TOOL.parse_round_constants(corrupted)

    def test_symbolic_mapping_realigns_after_each_eight_rounds(self) -> None:
        states = TOOL.validate_symbolic_group_mapping()
        self.assertEqual(len(states), 8)
        self.assertEqual(
            states[0],
            (
                "!PE_SHA_A",
                "!PE_SHA_B",
                "!PE_SHA_C",
                "!PE_SHA_D",
                "!PE_SHA_E",
                "!PE_SHA_F",
                "!PE_SHA_G",
                "!PE_SHA_H",
            ),
        )
        self.assertEqual(states[-1][0], "!PE_SHA_B")
        self.assertEqual(states[-1][-1], "!PE_SHA_A")
        source = TOOL.ASM_PATH.read_text(encoding="utf-8")
        corrupted = source.replace(
            "!PE_SHA_H, !PE_SHA_A, !PE_SHA_B, !PE_SHA_C, "
            "!PE_SHA_D, !PE_SHA_E, !PE_SHA_F, !PE_SHA_G",
            "!PE_SHA_G, !PE_SHA_A, !PE_SHA_B, !PE_SHA_C, "
            "!PE_SHA_D, !PE_SHA_E, !PE_SHA_F, !PE_SHA_H",
            1,
        )
        with self.assertRaises(TOOL.Round8Sha256Error):
            TOOL.validate_symbolic_group_mapping(corrupted)

    def test_generated_table_consumer_and_geometry_are_exact(self) -> None:
        result = TOOL.validate_table_consumer()
        self.assertEqual(result["table_bytes"], 0x4000)
        self.assertEqual(result["transform_count"], 4)
        self.assertEqual(result["basis_entries"], 4096)
        self.assertEqual(
            result["include_sha256"],
            "7455ce0e13d243cee1c8bd0a36c8ef3582f1df4176a155f837300b907b98e61a",
        )

    def test_source_derived_model_matches_standard_sha256(self) -> None:
        messages = (
            b"",
            b"abc",
            b"a" * 55,
            b"a" * 56,
            b"a" * 64,
            bytes(range(256)),
        )
        for message in messages:
            with self.subTest(size=len(message)):
                self.assertEqual(
                    TOOL.sha256_round8_source_model(message),
                    hashlib.sha256(message).digest(),
                )

    def test_profile_vectors_match_all_slots_and_remain_slot_bound(self) -> None:
        patterns = (
            bytes(TOOL.baseline.SLOT_SIZE),
            bytes(
                index & 0xFF
                for index in range(TOOL.baseline.SLOT_SIZE)
            ),
            bytes(
                (index * 73 + 19) & 0xFF
                for index in range(TOOL.baseline.SLOT_SIZE)
            ),
        )
        for serialized in patterns:
            digests = []
            for slot_number in range(1, 4):
                modeled = TOOL.profile1_digest_model(
                    serialized,
                    slot_number,
                )
                direct = hashlib.sha256(
                    serialized
                    + TOOL.baseline.binding_trailer(slot_number)
                ).digest()
                self.assertEqual(modeled, direct)
                digests.append(modeled)
            self.assertEqual(len(set(digests)), 3)

    def test_final_block_source_oracle_is_exact(self) -> None:
        for slot_number in range(1, 4):
            with self.subTest(slot=slot_number):
                block = TOOL.profile1_final_block_from_source(slot_number)
                self.assertEqual(
                    block[:16],
                    TOOL.baseline.binding_trailer(slot_number),
                )
                self.assertEqual(block[16:56], b"\x80" + bytes(39))
                self.assertEqual(
                    block[56:],
                    (
                        TOOL.baseline.PROFILE_MESSAGE_SIZE * 8
                    ).to_bytes(8, "big"),
                )

    def test_benchmark_is_baseline_equivalent_and_keeps_result_abi(self) -> None:
        result = TOOL.validate_benchmark_wrapper()
        self.assertTrue(result["equivalent_after_approved_substitutions"])
        self.assertEqual(result["entry_calls"], 2)
        self.assertEqual(result["result_address"], 0x7E5F00)
        self.assertEqual(result["expected_vector_bytes"], 0x60)
        self.assertEqual(result["sigma_table_bytes"], 0x4000)
        self.assertEqual(result["data_span_bytes"], 0x4060)
        self.assertEqual(
            result["source_sha256"],
            "67aad7bcdb59d200d5c6747ebf338d7993a94072879b0e88e7d7d348709f004f",
        )

    def test_exact_types_and_lengths_fail_closed(self) -> None:
        with self.assertRaises(TOOL.Round8Sha256Error):
            TOOL.sha256_round8_source_model(bytearray())
        with self.assertRaises(TOOL.Round8Sha256Error):
            TOOL.profile1_digest_model(
                bytes(TOOL.baseline.SLOT_SIZE - 1),
                1,
            )
        for invalid_slot in (0, 4, True, "1"):
            with self.subTest(slot=invalid_slot):
                with self.assertRaises(
                    TOOL.baseline.Sha256PrototypeError,
                ):
                    TOOL.baseline.binding_trailer(invalid_slot)

    def test_official_asar_code_table_and_group_geometry(self) -> None:
        if not TOOL.DEFAULT_ASAR_PATH.is_file():
            self.skipTest("official private Asar 1.91 is not staged")
        result = TOOL.run_asar_syntax()
        self.assertEqual(result["assembled_size"], 0x14000)
        self.assertEqual(result["code_start"], 0)
        self.assertEqual(result["code_size"], 0x4A26)
        self.assertLessEqual(result["code_size"], 0x6000)
        self.assertEqual(result["table_start"], 0x10000)
        self.assertEqual(result["table_size"], 0x4000)
        self.assertEqual(
            result["group_sizes"],
            (0x6F8, 0x6F8, 0x980, 0x980, 0x980, 0x980, 0x980, 0x980),
        )
        self.assertEqual(
            result["assembled_sha256"],
            "e78567f3302fcdf08a789ff1b525c00ebd1705fb52241baa62b941c0eb37ce22",
        )
        self.assertEqual(
            result["asar_sha256"],
            "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8",
        )


if __name__ == "__main__":
    unittest.main()
