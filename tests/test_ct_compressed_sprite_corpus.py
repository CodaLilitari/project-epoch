from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
from unittest import mock
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "audit_ct_compressed_sprite_corpus.py"
REFERENCE_PATH = (
    ROOT / "references" / "ct_compressed_sprite_corpus_v0.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_ct_compressed_sprite_corpus",
    TOOL_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def packet(main: bytes, marker: int) -> bytes:
    return len(main).to_bytes(2, "little") + main + bytes((marker,))


def backref_packet(width_bits: int) -> tuple[bytes, bytes]:
    literals = bytes(range(16))
    if width_bits == 12:
        token = (3 << 12) | 16
        marker = 0
    elif width_bits == 11:
        token = (3 << 11) | 16
        marker = 0x40
    else:
        raise AssertionError("test helper only supports 11/12")
    main = (
        b"\x00"
        + literals[:8]
        + b"\x00"
        + literals[8:]
        + b"\xFF"
        + token.to_bytes(2, "little") * 8
    )
    return packet(main, marker), literals * 4


def addendum_literal_packet() -> tuple[bytes, bytes]:
    literals = bytes(range(32))
    main = b"".join(
        b"\x00" + literals[start : start + 8]
        for start in range(0, 24, 8)
    )
    initial_boundary = 2 + len(main)
    addendum_start = initial_boundary + 3
    addendum = b"\x00" + literals[24:]
    final_boundary = addendum_start + len(addendum)
    result = (
        len(main).to_bytes(2, "little")
        + main
        + b"\x08"
        + final_boundary.to_bytes(2, "little")
        + addendum
        + b"\x00"
    )
    return result, literals


def malformed_zero_control_partial_packet() -> bytes:
    main = b"\x00" + bytes(range(8))
    main += b"\x7F"
    main += ((1 << 12) | 1).to_bytes(2, "little")
    main += (1).to_bytes(2, "little") * 6
    main += b"Z"
    initial_boundary = 2 + len(main)
    addendum_start = initial_boundary + 3
    addendum = b"\x00Q"
    final_boundary = addendum_start + len(addendum)
    return (
        len(main).to_bytes(2, "little")
        + main
        + b"\x01"
        + final_boundary.to_bytes(2, "little")
        + addendum
        + b"\x00"
    )


def addendum_11_bit_backref_packet() -> tuple[bytes, bytes]:
    literals = bytes(range(32))
    main = b"".join(
        b"\x00" + literals[start : start + 8]
        for start in range(0, 32, 8)
    )
    initial_boundary = 2 + len(main)
    addendum_start = initial_boundary + 3
    token = ((29 << 11) | 1).to_bytes(2, "little")
    addendum = b"\x01" + token
    final_boundary = addendum_start + len(addendum)
    result = (
        len(main).to_bytes(2, "little")
        + main
        + b"\x41"
        + final_boundary.to_bytes(2, "little")
        + addendum
        + b"\x40"
    )
    return result, literals + bytes((literals[-1],)) * 32


class C3DecoderUnitTests(unittest.TestCase):
    def test_12_bit_back_reference_vector(self) -> None:
        source, expected = backref_packet(12)
        decoded = AUDIT.decode_c3_sprite_packet(source, 0)
        self.assertEqual(decoded.data, expected)
        self.assertEqual(decoded.backref_width_bits, 12)
        self.assertEqual(decoded.compressed_size, len(source))
        self.assertEqual(decoded.addendum_count, 0)

    def test_11_bit_back_reference_vector(self) -> None:
        source, expected = backref_packet(11)
        decoded = AUDIT.decode_c3_sprite_packet(source, 0)
        self.assertEqual(decoded.data, expected)
        self.assertEqual(decoded.backref_width_bits, 11)
        self.assertEqual(decoded.compressed_size, len(source))
        self.assertEqual(decoded.addendum_count, 0)

    def test_lsb_first_literal_partial_group_and_addendum(self) -> None:
        source, expected = addendum_literal_packet()
        decoded = AUDIT.decode_c3_sprite_packet(source, 0)
        self.assertEqual(decoded.data, expected)
        self.assertEqual(decoded.backref_width_bits, 12)
        self.assertEqual(decoded.addendum_count, 1)
        self.assertEqual(decoded.segment_count, 2)
        self.assertEqual(decoded.compressed_size, len(source))

    def test_zero_control_partial_addendum_is_rejected(self) -> None:
        source = malformed_zero_control_partial_packet()
        with self.assertRaisesRegex(
            AUDIT.AuditError,
            "zero control byte cannot encode a partial",
        ):
            AUDIT.decode_c3_sprite_packet(source, 0)

    def test_11_bit_addendum_back_reference_vector(self) -> None:
        source, expected = addendum_11_bit_backref_packet()
        decoded = AUDIT.decode_c3_sprite_packet(source, 0)
        self.assertEqual(decoded.data, expected)
        self.assertEqual(decoded.backref_width_bits, 11)
        self.assertEqual(decoded.addendum_count, 1)
        self.assertEqual(decoded.segment_count, 2)
        self.assertEqual(decoded.compressed_size, len(source))

    def test_truncated_header_literal_and_backref_are_rejected(self) -> None:
        cases = {
            "header": b"\x01",
            "literal": packet(b"\x00", 0),
            "backref": packet(b"\x01\x34", 0),
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(AUDIT.AuditError):
                    AUDIT.decode_c3_sprite_packet(source, 0)

    def test_zero_and_forward_distances_are_rejected(self) -> None:
        zero_distance = packet(b"\x01\x00\x00", 0)
        forward_distance = packet(b"\x01\x01\x00", 0)
        with self.assertRaisesRegex(AUDIT.AuditError, "zero"):
            AUDIT.decode_c3_sprite_packet(zero_distance, 0)
        with self.assertRaisesRegex(AUDIT.AuditError, "forward"):
            AUDIT.decode_c3_sprite_packet(forward_distance, 0)

    def test_nonmonotonic_addendum_boundary_is_rejected(self) -> None:
        source = b"\x00\x00\x01\x04\x00\x00\x00"
        with self.assertRaisesRegex(AUDIT.AuditError, "nonmonotonic"):
            AUDIT.decode_c3_sprite_packet(source, 0)

    def test_output_cap_is_enforced(self) -> None:
        token = ((31 << 11) | 1).to_bytes(2, "little")
        main = b"\x00" + b"A" * 8
        main += (b"\xFF" + token * 8) * 241
        source = packet(main, 0x40)
        with self.assertRaisesRegex(AUDIT.AuditError, "0x10000"):
            AUDIT.decode_c3_sprite_packet(source, 0)

    def test_source_bank_crossing_is_rejected(self) -> None:
        source = bytearray(0x10001)
        start = 0xFFFC
        source[start : start + 2] = (2).to_bytes(2, "little")
        with self.assertRaisesRegex(AUDIT.AuditError, "crosses a CPU bank"):
            AUDIT.decode_c3_sprite_packet(bytes(source), start)

    def test_non_tile_aligned_output_is_rejected(self) -> None:
        source = packet(b"\x00" + b"ABCDEFGH", 0)
        with self.assertRaisesRegex(AUDIT.AuditError, "0x20-byte aligned"):
            AUDIT.decode_c3_sprite_packet(source, 0)

    def test_pointer_outside_hirom_is_rejected(self) -> None:
        for pointer in (0, 0xBFFFFF, 0x1000000):
            with self.subTest(pointer=pointer):
                with self.assertRaises(AUDIT.AuditError):
                    AUDIT.snes_hirom_to_file(pointer)


@unittest.skipUnless(ROM_PATH.is_file(), "canonical private ROM unavailable")
class CanonicalCompressedSpriteCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rom = ROM_PATH.read_bytes()
        cls.report = AUDIT.audit_rom_bytes(cls.rom)
        cls.rendered = AUDIT.render_report(cls.report)

    def test_wrong_rom_is_rejected_before_table_parsing(self) -> None:
        wrong = bytearray(self.rom)
        wrong[-1] ^= 1
        with mock.patch.object(
            AUDIT,
            "_read_tables",
            side_effect=AssertionError("table parser must not run"),
        ):
            with self.assertRaisesRegex(AUDIT.AuditError, "SHA-(1|256)"):
                AUDIT.audit_rom_bytes(bytes(wrong))

    def test_table_hashes_and_exact_entry_counts_are_pinned(self) -> None:
        tables = self.report["tables"]
        pointers = tables["graphics_pointers"]
        npc = tables["npc_descriptors"]
        enemy = tables["enemy_descriptors"]
        self.assertEqual(
            pointers["sha256"],
            AUDIT.GFX_POINTER_TABLE_SHA256,
        )
        self.assertEqual(
            npc["sha256"],
            AUDIT.NPC_DESCRIPTOR_TABLE_SHA256,
        )
        self.assertEqual(
            enemy["sha256"],
            AUDIT.ENEMY_DESCRIPTOR_TABLE_SHA256,
        )
        self.assertEqual(pointers["entry_count"], 256)
        self.assertEqual(pointers["non_pc_tail_entry_count"], 249)
        self.assertEqual(npc["entry_count"], 256)
        self.assertEqual(enemy["entry_count"], 256)
        self.assertEqual(
            enemy["normal_compressed_sha256"],
            AUDIT.NORMAL_ENEMY_DESCRIPTOR_TABLE_SHA256,
        )
        self.assertEqual(
            enemy["direct_raw_sha256"],
            AUDIT.DIRECT_ENEMY_DESCRIPTOR_TABLE_SHA256,
        )

    def test_full_catalog_and_selected_subset_counts_are_exact(self) -> None:
        corpus = self.report["corpus"]
        catalog = corpus["conservative_compressed_catalog"]
        selected = corpus["descriptor_selected_subset"]
        self.assertEqual(catalog["packet_count"], 241)
        self.assertEqual(catalog["decompressed_byte_count"], 699872)
        self.assertEqual(catalog["tile_4bpp_count"], 21871)
        self.assertEqual(catalog["one_addendum_packet_count"], 211)
        self.assertEqual(catalog["zero_addendum_packet_count"], 30)
        self.assertEqual(
            catalog["framed_decoded_corpus_sha256"],
            AUDIT.EXPECTED_CATALOG_SHA256,
        )
        self.assertEqual(selected["packet_count"], 237)
        self.assertEqual(selected["decompressed_byte_count"], 699200)
        self.assertEqual(selected["tile_4bpp_count"], 21850)
        self.assertEqual(selected["one_addendum_packet_count"], 207)
        self.assertEqual(selected["zero_addendum_packet_count"], 30)
        self.assertEqual(
            selected["framed_decoded_corpus_sha256"],
            AUDIT.EXPECTED_SELECTED_SHA256,
        )
        self.assertEqual(
            (catalog["minimum_decompressed_size"],
             catalog["maximum_decompressed_size"]),
            (128, 23776),
        )
        self.assertEqual(catalog["backref_12_bit_packet_count"], 241)
        self.assertEqual(catalog["backref_11_bit_packet_count"], 0)
        self.assertEqual(catalog["source_bank_crossing_count"], 0)

    def test_catalog_only_and_direct_raw_partitions_are_exact(self) -> None:
        selection = self.report["selection"]
        self.assertEqual(
            selection["catalog_only_unselected_gfx_indexes"],
            [0x47, 0x4A, 0xCC, 0xE5],
        )
        self.assertEqual(
            [
                row["gfx_selector"]
                for row in selection["direct_raw_enemy_descriptors"]
            ],
            [3, 6, 6, 6, 0, 0, 0, 0],
        )
        self.assertEqual(
            selection["descriptor_selected_selector_vector_byte_count"],
            504,
        )
        self.assertEqual(
            selection["descriptor_selected_selector_vector_sha256"],
            AUDIT.DESCRIPTOR_SELECTED_SELECTOR_VECTOR_SHA256,
        )
        self.assertEqual(
            selection["direct_raw_enemy_selector_sha256"],
            AUDIT.DIRECT_ENEMY_SELECTOR_SHA256,
        )
        self.assertIn(
            "enemy/script ID",
            selection["direct_raw_branch_operand"],
        )
        selected_indexes = {
            row["gfx_index"]
            for row in self.report["corpus"]["packets"]
            if row["descriptor_selected"]
        }
        self.assertFalse(
            selected_indexes & set(selection["raw_pc_gfx_indexes"])
        )
        self.assertEqual(selection["selected_pointer_alias_count"], 0)
        self.assertEqual(selection["catalog_pointer_alias_count"], 0)

    def test_all_descriptor_aliases_are_retained_as_metadata(self) -> None:
        packets = self.report["corpus"]["packets"]
        self.assertEqual(len(packets), 241)
        npc_ids = []
        enemy_ids = []
        for row in packets:
            aliases = row["selector_aliases"]
            npc_ids.extend(aliases["npc_ids"])
            enemy_ids.extend(aliases["normal_enemy_ids"])
            self.assertNotIn("decoded_bytes", row)
            self.assertNotIn("pixels", row)
        self.assertEqual(sorted(npc_ids), list(range(256)))
        self.assertEqual(sorted(enemy_ids), list(range(248)))

        by_index = {row["gfx_index"]: row for row in packets}
        for index in (0x47, 0x4A, 0xCC, 0xE5):
            self.assertFalse(by_index[index]["descriptor_selected"])
            self.assertEqual(by_index[index]["selector_aliases"]["npc_ids"], [])
            self.assertEqual(
                by_index[index]["selector_aliases"]["normal_enemy_ids"],
                [],
            )

    def test_report_generation_is_independent_of_pinned_report(self) -> None:
        with mock.patch.object(
            Path,
            "read_bytes",
            side_effect=AssertionError("report generation read a file"),
        ):
            regenerated = AUDIT.audit_rom_bytes(self.rom)
            rerendered = AUDIT.render_report(regenerated)
        self.assertEqual(rerendered, self.rendered)

    def test_report_is_utf8_lf_and_byte_identical_to_reference(self) -> None:
        expected = REFERENCE_PATH.read_bytes()
        self.assertEqual(self.rendered, expected)
        self.assertNotIn(b"\r", self.rendered)
        self.assertTrue(self.rendered.endswith(b"\n"))
        self.rendered.decode("utf-8")

    def test_cli_stdout_is_exact_and_has_no_output_destination(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(TOOL_PATH),
                "--rom",
                str(ROM_PATH),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout, self.rendered)
        self.assertEqual(result.stderr, b"")

        parser = AUDIT.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions},
            {"help", "rom"},
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    ["--rom", str(ROM_PATH), "--output", "forbidden.json"]
                )

    def test_report_contains_only_bounded_metadata(self) -> None:
        self.assertNotIn(str(ROM_PATH).encode("utf-8"), self.rendered)
        lowered = self.rendered.lower()
        self.assertNotIn(b"private\\\\input", lowered)
        self.assertNotIn(b"image_data", lowered)
        self.assertNotIn(b"pixel_data", lowered)
        self.assertEqual(
            hashlib.sha256(self.rom).hexdigest(),
            AUDIT.CANONICAL_ROM_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
