from __future__ import annotations

import importlib.util
import pathlib
import random
import re
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT / "tools" / "generate_schala_sha256_65816_sigma_tables.py"
)
SPEC = importlib.util.spec_from_file_location(
    "generate_schala_sha256_65816_sigma_tables",
    TOOL_PATH,
)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class SchalaSha256SigmaTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = TOOL.generate_tables()

    def test_exact_geometry_and_transform_order(self) -> None:
        self.assertEqual(
            tuple(self.tables),
            ("BigSigma0", "BigSigma1", "SmallSigma0", "SmallSigma1"),
        )
        self.assertEqual(TOOL.BYTE_TABLE_SIZE, 0x400)
        self.assertEqual(TOOL.TRANSFORM_SIZE, 0x1000)
        self.assertEqual(TOOL.TABLE_SIZE, 0x4000)
        for positions in self.tables.values():
            self.assertEqual(len(positions), 4)
            for entries in positions:
                self.assertEqual(len(entries), 256)
                self.assertTrue(all(0 <= value <= 0xFFFFFFFF for value in entries))

    def test_all_4096_basis_entries_match_direct_definitions(self) -> None:
        checked = 0
        for name, transform in TOOL.TRANSFORMS:
            for position in range(4):
                for byte_value in range(256):
                    basis = TOOL.basis_value(position, byte_value)
                    self.assertEqual(
                        self.tables[name][position][byte_value],
                        transform(basis),
                    )
                    checked += 1
        self.assertEqual(checked, 4 * 4 * 256)

    def test_byte_decomposition_reconstructs_adversarial_inputs(self) -> None:
        values = (
            0x00000000,
            0xFFFFFFFF,
            0x80000000,
            0x00000001,
            0xAAAAAAAA,
            0x55555555,
            0x01234567,
            0x89ABCDEF,
            0x00FF00FF,
            0xFF00FF00,
        )
        for name, transform in TOOL.TRANSFORMS:
            for value in values:
                with self.subTest(transform=name, value=f"{value:08X}"):
                    self.assertEqual(
                        TOOL.reconstruct(name, value, self.tables),
                        transform(value),
                    )

    def test_byte_decomposition_reconstructs_deterministic_random_inputs(
        self,
    ) -> None:
        random_source = random.Random(0x50453037)
        values = [random_source.getrandbits(32) for _ in range(4096)]
        for name, transform in TOOL.TRANSFORMS:
            for value in values:
                self.assertEqual(
                    TOOL.reconstruct(name, value, self.tables),
                    transform(value),
                )

    def test_entry_word_order_matches_core_numeric_halves(self) -> None:
        self.assertEqual(TOOL.entry_words(0x01234567), (0x0123, 0x4567))
        self.assertEqual(TOOL.entry_words(0x89ABCDEF), (0x89AB, 0xCDEF))

    def test_rendered_include_contract_and_exact_labels(self) -> None:
        source = TOOL.render_include(self.tables)
        text = source.decode("ascii")
        self.assertEqual(
            TOOL.DEFAULT_OUTPUT.name,
            "schala_sidecar_sha256_sigma_tables.asm",
        )
        self.assertNotRegex(text, r"(?im)^\s*(org|lorom|hirom|exhirom)\b")
        self.assertIn("EpochSha256SigmaTables_Start:", text)
        self.assertIn("EpochSha256SigmaTables_End:", text)
        for name, _ in TOOL.TRANSFORMS:
            self.assertIn(
                f"EpochSha256SigmaTables_{name}_Start:",
                text,
            )
            self.assertIn(
                f"EpochSha256SigmaTables_{name}_End:",
                text,
            )
            for position in range(4):
                self.assertIn(
                    f"EpochSha256SigmaTables_{name}_Byte{position}:",
                    text,
                )
        self.assertIn(
            "EpochSha256SigmaTables_End-"
            "EpochSha256SigmaTables_Start == $4000",
            text,
        )
        self.assertIn(
            "bank(EpochSha256SigmaTables_End-1)",
            text,
        )
        self.assertTrue(source.endswith(b"\n"))

    def test_rendered_dw_stream_is_exact_16_kib_table_payload(self) -> None:
        text = TOOL.render_include(self.tables).decode("ascii")
        words: list[int] = []
        for line in text.splitlines():
            if not line.startswith("    dw "):
                continue
            words.extend(
                int(token[1:], 16)
                for token in line.removeprefix("    dw ").split(",")
            )
        self.assertEqual(len(words), TOOL.TABLE_SIZE // 2)
        expected_words = [
            word
            for name, _ in TOOL.TRANSFORMS
            for position in range(4)
            for entry in self.tables[name][position]
            for word in TOOL.entry_words(entry)
        ]
        self.assertEqual(words, expected_words)

    def test_render_is_deterministic_and_ascii_only(self) -> None:
        first = TOOL.render_include()
        second = TOOL.render_include()
        self.assertEqual(first, second)
        self.assertEqual(first, first.decode("ascii").encode("ascii"))
        report = TOOL.generated_report(first)
        self.assertEqual(report["binary_table_size"], 0x4000)
        self.assertFalse(report["contains_game_data"])
        self.assertFalse(report["placed"])
        self.assertRegex(report["output_sha256"], r"^[0-9a-f]{64}$")

    def test_write_and_check_are_exact_and_fail_on_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "tables.inc"
            written = TOOL.write_include(output)
            self.assertEqual(written["status"], "written")
            checked = TOOL.check_include(output)
            self.assertEqual(checked["status"], "current")
            self.assertEqual(
                written["output_sha256"],
                checked["output_sha256"],
            )
            corrupted = bytearray(output.read_bytes())
            match = re.search(br"\$[0-9A-F]{4}", corrupted)
            assert match is not None
            corrupted[match.start() + 1] ^= 1
            output.write_bytes(corrupted)
            with self.assertRaises(TOOL.SigmaTableError):
                TOOL.check_include(output)

    def test_committed_asm_source_unit_matches_generator(self) -> None:
        report = TOOL.check_include(TOOL.DEFAULT_OUTPUT)
        self.assertEqual(report["status"], "current")
        self.assertEqual(report["binary_table_size"], 0x4000)

    def test_exact_type_and_range_rejections(self) -> None:
        for value in (-1, 0x1_0000_0000, True, b"\x00"):
            with self.subTest(value=value):
                with self.assertRaises(TOOL.SigmaTableError):
                    TOOL.big_sigma0(value)
        for position in (-1, 4, True):
            with self.assertRaises(TOOL.SigmaTableError):
                TOOL.basis_value(position, 0)
        with self.assertRaises(TOOL.SigmaTableError):
            TOOL.reconstruct("unknown", 0, self.tables)


if __name__ == "__main__":
    unittest.main()
