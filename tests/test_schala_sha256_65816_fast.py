from __future__ import annotations

import hashlib
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import validate_schala_sha256_65816_fast as TOOL  # noqa: E402


class SchalaSha25665816FastTests(unittest.TestCase):
    def test_proven_baseline_files_are_unchanged(self) -> None:
        hashes = TOOL.validate_baseline_unchanged()
        self.assertEqual(len(hashes), 4)

    def test_relocatable_source_contract_and_performance_mechanism(self) -> None:
        result = TOOL.validate_source_contract()
        self.assertEqual(result["scratch_size"], 0xC2)
        self.assertEqual(result["entry_save_frame_size"], 10)
        self.assertEqual(result["max_nested_jsr_count"], 2)
        self.assertEqual(result["max_stack_growth_after_entry"], 14)
        self.assertEqual(result["max_stack_growth_with_caller_jsl"], 17)
        self.assertEqual(result["algorithm_table_bytes"], 0x120)
        self.assertEqual(result["lookup_table_bytes"], 0)
        self.assertEqual(result["baseline_bit_steps_per_block"], 8608)
        self.assertEqual(result["fast_bit_steps_per_block"], 1408)
        self.assertEqual(result["baseline_bit_steps_per_digest"], 352928)
        self.assertEqual(result["fast_bit_steps_per_digest"], 57728)
        self.assertGreater(result["bit_step_reduction_percent"], 83)
        self.assertFalse(result["placed"])
        self.assertFalse(result["writes_bank_30"])

    def test_every_primitive_uses_the_pinned_fixed_decomposition(self) -> None:
        sequences = TOOL.parse_primitive_sequences()
        self.assertEqual(set(sequences), set(TOOL.PRIMITIVE_EXPECTATIONS))
        for name, (_, _, expected) in TOOL.PRIMITIVE_EXPECTATIONS.items():
            with self.subTest(primitive=name):
                self.assertEqual(sequences[name], expected)

    def test_authored_macro_bodies_pass_lane_exhaustion(self) -> None:
        result = TOOL.verify_macro_oracles()
        self.assertEqual(result["macro_count"], 8)
        self.assertEqual(result["vectors_per_macro"], 65536)
        self.assertEqual(result["comparisons"], 524288)

    def test_primitives_and_sigmas_pass_high_coverage_32bit_oracle(self) -> None:
        result = TOOL.verify_primitive_and_sigma_oracles()
        self.assertEqual(result["vectors"], 196608)
        self.assertEqual(result["primitive_count"], 12)
        self.assertEqual(result["sigma_count"], 4)
        self.assertEqual(result["comparisons"], 3145728)

    def test_source_derived_digest_model_matches_standard_vectors(self) -> None:
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
                    TOOL.sha256_fast_source_model(message),
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

    def test_exact_types_and_lengths_fail_closed(self) -> None:
        with self.assertRaises(TOOL.FastSha256Error):
            TOOL.sha256_fast_source_model(bytearray())
        with self.assertRaises(TOOL.FastSha256Error):
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

    def test_official_asar_raw_syntax_probe(self) -> None:
        if not TOOL.DEFAULT_ASAR_PATH.is_file():
            self.skipTest("official private Asar 1.91 is not staged")
        result = TOOL.run_asar_syntax()
        self.assertEqual(result["assembled_size"], 2000)
        self.assertEqual(
            result["assembled_sha256"],
            "ad43218b8804d23fe9733be31352e2636c24a0b9eb8bef5be78e385b3ae117de",
        )
        self.assertEqual(
            result["asar_sha256"],
            "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8",
        )


if __name__ == "__main__":
    unittest.main()
