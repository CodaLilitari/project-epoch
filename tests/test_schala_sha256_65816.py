from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_schala_sha256_65816.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_schala_sha256_65816",
    TOOL_PATH,
)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class SchalaSha25665816Tests(unittest.TestCase):
    def test_relocatable_source_contract_and_table_sizes(self) -> None:
        result = TOOL.validate_source_contract()
        self.assertEqual(result["scratch_size"], 0xC2)
        self.assertEqual(result["initial_word_count"], 8)
        self.assertEqual(result["round_constant_count"], 64)
        self.assertEqual(result["profile_block_count"], 41)
        self.assertEqual(result["entry_save_frame_size"], 10)
        self.assertEqual(result["max_nested_jsr_count"], 3)
        self.assertEqual(result["max_stack_growth_after_entry"], 16)
        self.assertEqual(result["max_stack_growth_with_caller_jsl"], 19)
        self.assertFalse(result["writes_bank_30"])
        self.assertFalse(result["placed"])
        source = TOOL.ASM_PATH.read_text(encoding="utf-8")
        self.assertRegex(
            source,
            r"EpochSha256_Profile1Digest:\s*PHP\s*REP\s+#\$30\s*CLD",
        )

    def test_standard_sha256_vectors_match_hashlib(self) -> None:
        vectors = (
            b"",
            b"abc",
            b"a" * 55,
            b"a" * 56,
            b"a" * 64,
            bytes(range(256)),
        )
        for message in vectors:
            with self.subTest(size=len(message)):
                self.assertEqual(
                    TOOL.sha256_16bit_lane_model(message),
                    hashlib.sha256(message).digest(),
                )

    def test_profile_trailer_and_fixed_message_shape(self) -> None:
        self.assertEqual(
            TOOL.binding_trailer(1).hex(),
            "5045303742494e4402010100000a0000",
        )
        self.assertEqual(
            TOOL.binding_trailer(2).hex(),
            "5045303742494e4402010200000a0000",
        )
        self.assertEqual(
            TOOL.binding_trailer(3).hex(),
            "5045303742494e4402010300000a0000",
        )
        self.assertEqual(
            TOOL.SLOT_SIZE + len(TOOL.binding_trailer(1)),
            TOOL.PROFILE_MESSAGE_SIZE,
        )
        padded_size = (
            TOOL.PROFILE_MESSAGE_SIZE
            + 1
            + ((56 - (TOOL.PROFILE_MESSAGE_SIZE + 1) % 64) % 64)
            + 8
        )
        self.assertEqual(padded_size // 64, TOOL.PROFILE_BLOCK_COUNT)

    def test_source_final_block_reconstructs_exact_conceptual_bytes(self) -> None:
        for slot_number in range(1, 4):
            with self.subTest(slot=slot_number):
                block = TOOL.profile1_final_block_from_source(slot_number)
                self.assertEqual(len(block), 64)
                self.assertEqual(
                    block[:0x10],
                    TOOL.binding_trailer(slot_number),
                )
                self.assertEqual(block[0x10], 0x80)
                self.assertEqual(block[0x11:0x38], bytes(0x27))
                self.assertEqual(
                    block[0x38:],
                    (TOOL.PROFILE_MESSAGE_SIZE * 8).to_bytes(8, "big"),
                )

    def test_all_zero_slot_vectors_are_pinned_for_all_physical_slots(self) -> None:
        serialized = bytes(TOOL.SLOT_SIZE)
        for slot_number, expected in TOOL.EXPECTED_ZERO_SLOT_DIGESTS.items():
            with self.subTest(slot=slot_number):
                self.assertEqual(
                    TOOL.profile1_digest_model(
                        serialized,
                        slot_number,
                    ).hex(),
                    expected,
                )

    def test_patterned_slots_match_direct_hashlib_and_remain_slot_bound(self) -> None:
        patterns = (
            bytes(index & 0xFF for index in range(TOOL.SLOT_SIZE)),
            bytes((index * 73 + 19) & 0xFF for index in range(TOOL.SLOT_SIZE)),
        )
        for serialized in patterns:
            digests = []
            for slot_number in range(1, 4):
                modeled = TOOL.profile1_digest_model(
                    serialized,
                    slot_number,
                )
                direct = hashlib.sha256(
                    serialized + TOOL.binding_trailer(slot_number)
                ).digest()
                self.assertEqual(modeled, direct)
                digests.append(modeled)
            self.assertEqual(len(set(digests)), 3)

    def test_single_byte_change_changes_the_profile_digest(self) -> None:
        baseline = bytes(TOOL.SLOT_SIZE)
        mutated = bytearray(baseline)
        mutated[0x430] = 1
        self.assertNotEqual(
            TOOL.profile1_digest_model(baseline, 1),
            TOOL.profile1_digest_model(bytes(mutated), 1),
        )

    def test_exact_types_lengths_and_slots_fail_closed(self) -> None:
        with self.assertRaises(TOOL.Sha256PrototypeError):
            TOOL.sha256_16bit_lane_model(bytearray())
        with self.assertRaises(TOOL.Sha256PrototypeError):
            TOOL.profile1_digest_model(bytes(TOOL.SLOT_SIZE - 1), 1)
        for invalid_slot in (0, 4, True, "1"):
            with self.subTest(slot=invalid_slot):
                with self.assertRaises(TOOL.Sha256PrototypeError):
                    TOOL.binding_trailer(invalid_slot)

    def test_official_asar_syntax_probe_when_staged(self) -> None:
        if not TOOL.DEFAULT_ASAR_PATH.is_file():
            self.skipTest("official private Asar 1.91 is not staged")
        result = TOOL.run_asar_syntax()
        self.assertGreater(result["assembled_size"], 0)
        self.assertEqual(len(result["assembled_sha256"]), 64)
        self.assertEqual(
            result["asar_sha256"],
            "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8",
        )


if __name__ == "__main__":
    unittest.main()
