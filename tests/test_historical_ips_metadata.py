from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

AUDIT_PATH = TOOLS_DIR / "audit_historical_ips_metadata.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_historical_ips_metadata",
    AUDIT_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)

ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)
RECOVERED_ROOT = (
    ROOT
    / "recovered"
    / "kajar_laboratories_2014"
    / "Kajar Laboratories"
)
EARLY_DIR = (
    RECOVERED_ROOT
    / "8th_Playable_Character_Possible___-_Find_Out_Inside_"
)
LATE_DIR = (
    RECOVERED_ROOT
    / "8th_Playable_Character_Possible___(Updating_)"
)
LOCAL_PATCHES = {
    "Mauron_character8.ips": EARLY_DIR / "Mauron_character8.ips",
    "Vehek_Chrono Trigger-NPC Sprite Data mod.ips": (
        EARLY_DIR / "Vehek_Chrono Trigger-NPC Sprite Data mod.ips"
    ),
    "justin3009_8th Char almost Playable.ips": (
        LATE_DIR / "justin3009_8th Char almost Playable.ips"
    ),
    "justin3009_Chrono Trigger - 8th Character 6 Letters.ips": (
        LATE_DIR / "justin3009_Chrono Trigger - 8th Character 6 Letters.ips"
    ),
    "dated": (
        LATE_DIR
        / (
            "justin3009_Chrono Trigger - Fresh Rom (Unheader - 8th "
            "Character) - 10-15-2008.ips"
        )
    ),
    "undated": (
        LATE_DIR
        / (
            "justin3009_Chrono Trigger - Fresh Rom (Unheader - 8th "
            "Character).ips"
        )
    ),
}
LOCAL_AVAILABLE = ROM_PATH.exists() and all(
    path.exists() for path in LOCAL_PATCHES.values()
)


def literal(offset: int, payload: bytes) -> bytes:
    return (
        offset.to_bytes(3, "big")
        + len(payload).to_bytes(2, "big")
        + payload
    )


def rle(offset: int, size: int, value: int) -> bytes:
    return (
        offset.to_bytes(3, "big")
        + b"\x00\x00"
        + size.to_bytes(2, "big")
        + bytes([value])
    )


def make_patch(*records: bytes, truncate: int | None = None) -> bytes:
    tail = b"" if truncate is None else truncate.to_bytes(3, "big")
    return b"PATCH" + b"".join(records) + b"EOF" + tail


class HistoricalIpsMetadataTests(unittest.TestCase):
    def test_parser_handles_literal_rle_overlap_and_truncate(self) -> None:
        source = make_patch(
            literal(2, b"ABC"),
            rle(4, 3, 0x5A),
            literal(3, b"q"),
            truncate=9,
        )
        patch = AUDIT.parse_ips(source)
        self.assertEqual(len(patch.records), 3)
        self.assertEqual(patch.truncate_size, 9)
        parsed_writes = patch.effective_writes()
        self.assertEqual(
            dict(parsed_writes.items()),
            {2: ord("A"), 3: ord("q"), 4: 0x5A, 5: 0x5A, 6: 0x5A},
        )
        self.assertLess(parsed_writes.storage_bytes, 64)

        with self.assertRaisesRegex(
            AUDIT.IpsAuditError,
            "truncate records are unsupported",
        ):
            AUDIT.audit_patch(
                source,
                label="synthetic-truncate.ips",
                reference=bytes(8),
            )

        audited_source = make_patch(
            literal(2, b"ABC"),
            rle(4, 3, 0x5A),
            literal(3, b"q"),
        )
        original_effective_writes = AUDIT.IpsPatch.effective_writes
        with mock.patch.object(
            AUDIT.IpsPatch,
            "effective_writes",
            autospec=True,
            side_effect=original_effective_writes,
        ) as effective_writes:
            report, writes = AUDIT.audit_patch(
                audited_source,
                label="synthetic.ips",
                reference=bytes(8),
            )
        effective_writes.assert_called_once()
        self.assertEqual(writes[3], ord("q"))
        self.assertEqual(report["ips"]["record_count"], 3)
        self.assertEqual(report["ips"]["literal_record_count"], 2)
        self.assertEqual(report["ips"]["rle_record_count"], 1)
        self.assertEqual(report["ips"]["declared_write_bytes"], 7)
        self.assertEqual(report["ips"]["effective_write_bytes"], 5)
        self.assertEqual(report["ips"]["overwritten_record_bytes"], 2)
        self.assertEqual(
            report["reference_comparison"]["projected_target_size"],
            8,
        )

    def test_malformed_inputs_fail_closed(self) -> None:
        cases = (
            (b"NOTIPS", "header"),
            (b"PATCH", "missing EOF"),
            (b"PATCH\x00\x00\x01", "truncated record size"),
            (b"PATCH\x00\x00\x01\x00\x02x", "truncated literal"),
            (
                b"PATCH\x00\x00\x01\x00\x00\x00",
                "truncated RLE size",
            ),
            (
                b"PATCH\x00\x00\x01\x00\x00\x00\x01",
                "truncated RLE value",
            ),
            (
                b"PATCH\x00\x00\x01\x00\x00\x00\x00xEOF",
                "zero-length RLE",
            ),
            (b"PATCHEOFx", "unexpected bytes"),
            (b"PATCHEOFxx", "unexpected bytes"),
            (b"PATCHEOFxxxx", "unexpected bytes"),
        )
        for source, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(AUDIT.IpsAuditError, message):
                    AUDIT.parse_ips(source)

    def test_resource_budgets_fail_closed_before_expansion(self) -> None:
        one_rle = make_patch(rle(0, 5, 0xAA))
        with mock.patch.object(AUDIT, "MAX_DECLARED_WRITE_BYTES", 4):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "declared-write budget",
            ):
                AUDIT.parse_ips(one_rle)

        two_records = make_patch(literal(0, b"a"), literal(2, b"b"))
        with mock.patch.object(AUDIT, "MAX_RECORD_COUNT", 1):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "record-count budget",
            ):
                AUDIT.parse_ips(two_records)

        with mock.patch.object(
            AUDIT,
            "MAX_PATCH_FILE_BYTES",
            len(one_rle) - 1,
        ):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "file-size budget",
            ):
                AUDIT.parse_ips(one_rle)
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "file-size budget",
            ):
                AUDIT._read_file(
                    AUDIT_PATH,
                    "IPS patch",
                    max_bytes=1,
                )

        empty = make_patch()
        with mock.patch.object(AUDIT, "MAX_PATCH_COUNT", 1):
            with mock.patch.object(
                AUDIT,
                "audit_patch",
                side_effect=AssertionError("patch processing began"),
            ) as audit_patch:
                with self.assertRaisesRegex(
                    AUDIT.IpsAuditError,
                    "patch-count budget",
                ):
                    AUDIT.audit_many((("a", empty), ("b", empty)))
                audit_patch.assert_not_called()
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "patch-count budget",
            ):
                AUDIT._preflight_patch_paths((AUDIT_PATH, AUDIT_PATH))

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                AUDIT,
                "_read_file",
                side_effect=AssertionError("patch read began"),
            ) as read_file,
            mock.patch.object(
                AUDIT,
                "_read_canonical_rom",
                side_effect=AssertionError("reference read began"),
            ) as read_reference,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = AUDIT.main((str(AUDIT_PATH), str(AUDIT_PATH)))
        self.assertEqual(result, 1)
        self.assertIn("patch labels must be unique", stderr.getvalue())
        read_file.assert_not_called()
        read_reference.assert_not_called()

        with mock.patch.object(
            AUDIT,
            "MAX_TOTAL_PATCH_FILE_BYTES",
            len(empty) * 2 - 1,
        ):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "aggregate input-size budget",
            ):
                AUDIT.audit_many((("a", empty), ("b", empty)))

        with mock.patch.object(
            AUDIT,
            "MAX_TOTAL_DECLARED_WRITE_BYTES",
            9,
        ):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "aggregate declared-write budget",
            ):
                AUDIT.audit_many((("a", one_rle), ("b", one_rle)))

        with mock.patch.object(AUDIT, "MAX_RELATION_ADDRESS_VISITS", 10):
            boundary = AUDIT.audit_many(
                (("a", one_rle), ("b", one_rle))
            )
        self.assertEqual(
            boundary["resource_budget"]["actual"][
                "relation_address_visits"
            ],
            10,
        )
        with (
            mock.patch.object(AUDIT, "MAX_RELATION_ADDRESS_VISITS", 9),
            mock.patch.object(
                AUDIT,
                "compare_writes",
                side_effect=AssertionError("comparison began"),
            ) as compare_writes,
        ):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "relation-address-visit budget",
            ):
                AUDIT.audit_many((("a", one_rle), ("b", one_rle)))
            compare_writes.assert_not_called()

        with mock.patch.object(
            AUDIT,
            "MAX_TOTAL_EFFECTIVE_WRITE_BYTES",
            9,
        ):
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "aggregate effective-write budget",
            ):
                AUDIT.audit_many((("a", one_rle), ("b", one_rle)))

        with tempfile.TemporaryDirectory() as raw_directory:
            oversized = Path(raw_directory) / "oversized.sfc"
            oversized.write_bytes(bytes(AUDIT.CANONICAL_ROM_SIZE + 1))
            with mock.patch.object(
                AUDIT,
                "_read_bounded",
                side_effect=AssertionError("oversized reference was read"),
            ) as read_bounded:
                with self.assertRaisesRegex(
                    AUDIT.IpsAuditError,
                    "file-size budget",
                ):
                    AUDIT._read_canonical_rom(oversized)
                read_bounded.assert_not_called()

        class TrackingBytesIO(io.BytesIO):
            requested_size: int | None = None

            def read(self, size: int = -1) -> bytes:
                self.requested_size = size
                return super().read(size)

        growing_stream = TrackingBytesIO(b"12345")
        with self.assertRaisesRegex(
            AUDIT.IpsAuditError,
            "file-size budget",
        ):
            AUDIT._read_bounded(
                growing_stream,
                "IPS patch",
                max_bytes=4,
            )
        self.assertEqual(growing_stream.requested_size, 5)

    def test_address_space_boundary_and_duplicate_labels(self) -> None:
        accepted = make_patch(literal(0xFFFFFF, b"\xAA"))
        self.assertEqual(AUDIT.parse_ips(accepted).records[0].end, 0x1000000)
        rejected = make_patch(literal(0xFFFFFF, b"\xAA\xBB"))
        with self.assertRaisesRegex(
            AUDIT.IpsAuditError,
            "exceeds 24-bit address space",
        ):
            AUDIT.parse_ips(rejected)

        empty = make_patch()
        self.assertEqual(AUDIT.parse_ips(empty).records, ())
        with self.assertRaisesRegex(AUDIT.IpsAuditError, "labels must be unique"):
            AUDIT.audit_many((("same", empty), ("same", empty)))

    def test_audit_serializes_metadata_but_never_payload(self) -> None:
        payload = b"UNIQUE_PAYLOAD_DO_NOT_SERIALIZE"
        source = make_patch(literal(0x100, payload))
        report = AUDIT.audit_many(
            [("sample.ips", source)],
            reference=None,
        )
        serialized = json.dumps(report, sort_keys=True)
        self.assertNotIn(payload.decode("ascii"), serialized)
        self.assertNotIn(payload.hex(), serialized)
        self.assertEqual(
            report["artifact_provenance"],
            "caller-supplied-read-only-input",
        )
        self.assertIn("IPS structure", report["evidence_scope"])
        self.assertNotIn("archive", report["artifact_provenance"])
        self.assertEqual(
            report["policy"]["canonical_source_sha256"],
            AUDIT.CANONICAL_ROM_SHA256,
        )
        self.assertEqual(report["resource_budget"]["actual"]["patch_count"], 1)
        self.assertEqual(
            report["resource_budget"]["limits"]["patch_count"],
            AUDIT.MAX_PATCH_COUNT,
        )
        self.assertFalse(report["safety"]["patched_image_emitted"])
        self.assertFalse(report["safety"]["patch_payload_serialized"])
        self.assertFalse(
            report["safety"]["production_hook_or_allocation_approved"]
        )
        with self.assertRaisesRegex(
            AUDIT.IpsAuditError,
            "reference ROM must be exactly",
        ):
            AUDIT.audit_many(
                [("sample.ips", source)],
                reference=b"not canonical",
            )
        with mock.patch.object(
            AUDIT,
            "audit_patch",
            side_effect=AssertionError("patch audit began"),
        ) as audit_patch:
            with self.assertRaisesRegex(
                AUDIT.IpsAuditError,
                "not pinned US Rev0",
            ):
                AUDIT.audit_many(
                    [("sample.ips", source)],
                    reference=bytes(AUDIT.CANONICAL_ROM_SIZE),
                )
            audit_patch.assert_not_called()

    def test_relations_distinguish_address_and_value_subsets(self) -> None:
        small = {1: 0x10, 2: 0x20}
        exact_superset = {1: 0x10, 2: 0x20, 3: 0x30}
        changed_superset = {1: 0x10, 2: 0x21, 3: 0x30}
        missing = {1: 0x10}

        exact = AUDIT.compare_writes("small", small, "exact", exact_superset)
        self.assertTrue(exact["address_subset"])
        self.assertTrue(exact["address_value_subset"])

        changed = AUDIT.compare_writes(
            "small", small, "changed", changed_superset
        )
        self.assertTrue(changed["address_subset"])
        self.assertFalse(changed["address_value_subset"])
        self.assertEqual(changed["different_value_same_address_bytes"], 1)

        absent = AUDIT.compare_writes("small", small, "missing", missing)
        self.assertFalse(absent["address_subset"])
        self.assertEqual(absent["missing_address_bytes"], 1)

    def test_cli_has_no_output_or_mutation_destination(self) -> None:
        parser = AUDIT.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions},
            {"help", "patch", "reference_rom", "compact"},
        )
        source = AUDIT_PATH.read_text(encoding="utf-8")
        for forbidden_write in (
            ".write_bytes(",
            ".write_text(",
            "open(\"wb\"",
            "open('wb'",
            "open(\"w\"",
            "open('w'",
            "open(\"a\"",
            "open('a'",
        ):
            self.assertNotIn(forbidden_write, source)

    def test_cli_leaves_input_directory_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            patch_path = directory / "synthetic.ips"
            patch_path.write_bytes(make_patch(literal(0x20, b"safe")))

            def snapshot() -> dict[str, tuple[int, str]]:
                return {
                    path.name: (
                        path.stat().st_size,
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                    for path in directory.iterdir()
                }

            before = snapshot()
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = AUDIT.main([str(patch_path), "--compact"])
            self.assertEqual(result, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(snapshot(), before)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report["patches"][0]["label"], patch_path.name)
            self.assertNotIn(str(patch_path), stdout.getvalue())

    @unittest.skipUnless(
        LOCAL_AVAILABLE,
        "canonical ROM or recovered historical IPS family unavailable",
    )
    def test_recovered_family_identities_and_lineage(self) -> None:
        expected = {
            "Mauron_character8.ips": (
                533,
                "86d19470e0f41c06e87539286c5faead"
                "223d5356cb6d959c66f7d8a436f2d76e",
            ),
            "Vehek_Chrono Trigger-NPC Sprite Data mod.ips": (
                173,
                "2a7abca722caebd27812b9b8d8cd646c"
                "cc61afd6f3669e285810da2331f282e6",
            ),
            "justin3009_8th Char almost Playable.ips": (
                97754,
                "efaa1960278456028fb420612da8415b"
                "b9cd78d506365a152dd4349185b044c5",
            ),
            "justin3009_Chrono Trigger - 8th Character 6 Letters.ips": (
                110672,
                "8468aa907860cbb235d3355b56944aac"
                "bb778aa3d8087b883e4b40905ab0c7c5",
            ),
            "dated": (
                110709,
                "08487a3ba9b7ef789129f92851b643c0"
                "b4193a5d892d8b36126323285a725401",
            ),
            "undated": (
                109411,
                "771e17d5e6c51fa01fbdba1012bef61a"
                "3e9ff08ddb0449076d6921f6c405e7bc",
            ),
        }
        inputs: list[tuple[str, bytes]] = []
        for label, path in LOCAL_PATCHES.items():
            source = path.read_bytes()
            size, digest = expected[label]
            self.assertEqual(len(source), size)
            self.assertEqual(hashlib.sha256(source).hexdigest(), digest)
            inputs.append((label, source))

        report = AUDIT.audit_many(
            inputs,
            reference=AUDIT._read_canonical_rom(ROM_PATH),
        )
        self.assertEqual(report["evidence_level"], "verified-static")
        self.assertEqual(
            report["artifact_provenance"],
            "caller-supplied-read-only-input",
        )
        self.assertFalse(report["safety"]["rom_patch_save_or_state_written"])
        self.assertEqual(
            report["resource_budget"]["actual"],
            {
                "patch_count": 6,
                "patch_file_bytes": 429252,
                "declared_write_bytes": 8474412,
                "effective_write_bytes": 8474412,
                "directed_relation_count": 30,
                "relation_address_visits": 42372060,
            },
        )
        by_label = {row["label"]: row for row in report["patches"]}
        expected_metadata = {
            "Mauron_character8.ips": (
                35,
                10,
                542,
                6,
                0,
                0,
                0x400000,
                "e0a9f29a8e1e76693cad4f32f5a6053b"
                "24bdeec36a9865f8d120fe21615f3cd9",
            ),
            "Vehek_Chrono Trigger-NPC Sprite Data mod.ips": (
                17,
                0,
                31,
                49,
                0,
                0,
                0x400000,
                "baed6ecb46615a57d5aa9f1d361c521a"
                "78940a3c3c7a4f9d9cfe14fc8d10176d",
            ),
            "justin3009_8th Char almost Playable.ips": (
                249,
                120,
                13185,
                638,
                2097152,
                68088,
                0x600000,
                "91e79a0feadefcf90ff0e4b52cd74c4b"
                "cdb0b6e2c05c4f05ed97e994b469a65e",
            ),
            "justin3009_Chrono Trigger - 8th Character 6 Letters.ips": (
                332,
                127,
                22202,
                1650,
                2097152,
                70529,
                0x600000,
                "103b7465023f15bc4bdbc953c4e1cd76"
                "5de74542b00e8c9bc07ff7e5a787e02f",
            ),
            "dated": (
                337,
                129,
                22970,
                1779,
                2097152,
                70541,
                0x600000,
                "07f322bbc5a0172305c4597461f35671"
                "732d08f83e3547e9abf9fab8e382e226",
            ),
            "undated": (
                312,
                128,
                21276,
                1476,
                2097152,
                70529,
                0x600000,
                "301c85c7c2084034518024b062e53141"
                "39c1c4ee0a00568f1dcba2bfad34a36c",
            ),
        }
        for label, expected_row in expected_metadata.items():
            row = by_label[label]
            comparison = row["reference_comparison"]
            actual_row = (
                row["ips"]["record_count"],
                row["ips"]["rle_record_count"],
                comparison["changed_bytes_within_reference"],
                comparison["same_value_writes_within_reference"],
                comparison["effective_expansion_writes"],
                comparison["nonzero_expansion_writes"],
                comparison["projected_target_size"],
                comparison["projected_target_sha256"],
            )
            self.assertEqual(actual_row, expected_row, label)

        almost = by_label["justin3009_8th Char almost Playable.ips"]
        six = by_label[
            "justin3009_Chrono Trigger - 8th Character 6 Letters.ips"
        ]
        dated = by_label["dated"]
        undated = by_label["undated"]
        for row in (almost, six, dated, undated):
            self.assertEqual(
                row["reference_comparison"]["projected_target_size"],
                0x600000,
            )
        self.assertTrue(
            almost["probes"]["pc07_crono_critical_shared_selector"][
                "changes_reference"
            ]
        )
        self.assertFalse(
            six["probes"]["pc07_crono_critical_shared_selector"]["covered"]
        )
        self.assertFalse(
            dated["probes"]["pc07_crono_critical_shared_selector"]["covered"]
        )
        self.assertTrue(
            undated["probes"]["pc07_crono_critical_shared_selector"][
                "changes_reference"
            ]
        )

        relations = {
            (row["source"], row["target"]): row
            for row in report["directed_subset_relations"]
        }
        for component in (
            "Mauron_character8.ips",
            "Vehek_Chrono Trigger-NPC Sprite Data mod.ips",
        ):
            relation = relations[
                (component, "justin3009_8th Char almost Playable.ips")
            ]
            self.assertTrue(relation["address_subset"])
            self.assertTrue(relation["address_value_subset"])

        true_value_subsets = {
            (row["source"], row["target"])
            for row in report["directed_subset_relations"]
            if row["address_value_subset"]
        }
        self.assertEqual(
            true_value_subsets,
            {
                (
                    "Mauron_character8.ips",
                    "justin3009_8th Char almost Playable.ips",
                ),
                (
                    "Vehek_Chrono Trigger-NPC Sprite Data mod.ips",
                    "justin3009_8th Char almost Playable.ips",
                ),
            },
        )
        self.assertEqual(len(report["directed_subset_relations"]), 30)

        def intersections(
            row: dict[str, object],
            family: str,
        ) -> dict[str, int | None]:
            project_epoch = row["project_epoch_intersections"]
            assert isinstance(project_epoch, dict)
            entries = project_epoch[family]
            assert isinstance(entries, list)
            return {
                entry["id"]: entry["changed_reference_bytes"]
                for entry in entries
            }

        protected_expectation = {
            "epoch_menu_portrait_pointer": 2,
            "graphics_pointer_entries_07_08": 2,
            "assembly_pointer_entries_07_08": 3,
            "sprite_descriptor_entries_07_08": 4,
            "bank40_boot_and_lowbank_mirror": 65536,
        }
        for row in (almost, six, dated, undated):
            protected = intersections(row, "protected_ranges")
            for range_id, changed in protected_expectation.items():
                self.assertEqual(protected[range_id], changed)

        for row in (almost, undated):
            protected = intersections(row, "protected_ranges")
            self.assertEqual(
                protected["pc07_crono_critical_shared_selector"],
                1,
            )
            known = intersections(row, "known_tables")
            self.assertEqual(known["attack_selector_families"], 1)
        for row in (six, dated):
            protected = intersections(row, "protected_ranges")
            self.assertNotIn(
                "pc07_crono_critical_shared_selector",
                protected,
            )

        for row in (six, dated, undated):
            protected = intersections(row, "protected_ranges")
            self.assertEqual(
                protected["pc_name_pointer_entry_07_epoch_split"],
                2,
            )
        mauron = by_label["Mauron_character8.ips"]
        self.assertEqual(
            intersections(mauron, "known_tables")["char_init_records"],
            54,
        )


if __name__ == "__main__":
    unittest.main()
