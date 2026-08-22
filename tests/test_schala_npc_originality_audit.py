from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "audit_schala_npc_originality.py"
REPORT_PATH = (
    ROOT / "references" / "schala_npc_originality_audit_v0.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_npc_originality", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def descriptor_table_digest(rom: bytes) -> str:
    start = TOOL.NPC_DESCRIPTOR_TABLE_FILE
    end = start + TOOL.NPC_DESCRIPTOR_TABLE_SIZE
    return TOOL.sha256(rom[start:end])


def pointer_table_digest(rom: bytes) -> str:
    start = TOOL.GFX_POINTER_TABLE_FILE
    end = start + TOOL.GFX_POINTER_TABLE_SIZE
    return TOOL.sha256(rom[start:end])


class SchalaNpcOriginalityUnitTests(unittest.TestCase):
    def test_behavior_dependency_identities_are_exactly_pinned(self) -> None:
        verified = TOOL.verify_behavior_dependencies()
        self.assertEqual(verified, list(TOOL.BEHAVIOR_DEPENDENCIES))
        self.assertEqual(
            [record["path"] for record in verified],
            [
                "tools/audit_ct_compressed_sprite_corpus.py",
                "tools/audit_location_event_items.py",
                "tools/audit_schala_gameplay_originality.py",
                "tools/build_schala_gameplay_foundation_v0.py",
                "tools/validate_schala_glass_focus_pulse_v0.py",
            ],
        )

    def test_dependency_drift_is_rejected_before_helper_execution(self) -> None:
        target = (
            ROOT / TOOL.BEHAVIOR_DEPENDENCIES[0]["path"]
        ).resolve()
        target_raw = target.read_bytes()
        original_read_bytes = pathlib.Path.read_bytes

        def drifted_read_bytes(path: pathlib.Path) -> bytes:
            if path.resolve() == target:
                return target_raw[:-1] + bytes((target_raw[-1] ^ 1,))
            return original_read_bytes(path)

        with mock.patch.object(
            pathlib.Path, "read_bytes", drifted_read_bytes
        ), mock.patch.object(
            TOOL,
            "validate_canonical_rom",
            side_effect=AssertionError(
                "canonical-ROM helper ran before dependency gate"
            ),
        ), self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError,
            "behavior dependency.*SHA-256 drifted",
        ):
            TOOL.build_report(ROM_PATH)

    def test_parser_has_only_required_rom_input(self) -> None:
        parser = TOOL.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions},
            {"help", "rom"},
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    ["--rom", "clean.sfc", "--output", "forbidden.json"]
                )

    def test_expected_bounded_counts_are_exact(self) -> None:
        self.assertEqual(
            TOOL.REFERENCE_EXPECTED_COUNTS,
            {
                "tile_count": 79,
                "excluded_trivial_tile_count": 1,
                "compared_tile_count": 78,
            },
        )
        gameplay = TOOL.CANDIDATE_EXPECTED_COUNTS[
            "gameplay_foundation"
        ]
        glass = TOOL.CANDIDATE_EXPECTED_COUNTS["glass_focus"]
        self.assertEqual(
            (
                gameplay["tile_occurrence_count"],
                gameplay["excluded_trivial_tile_occurrence_count"],
                gameplay["compared_tile_occurrence_count"],
                gameplay["exact_index_match_count"],
                gameplay["visible_pattern_match_count"],
            ),
            (159, 59, 100, 0, 0),
        )
        self.assertEqual(
            (
                glass["tile_occurrence_count"],
                glass["excluded_trivial_tile_occurrence_count"],
                glass["compared_tile_occurrence_count"],
                glass["exact_index_match_count"],
                glass["visible_pattern_match_count"],
            ),
            (174, 80, 94, 0, 0),
        )

    def test_candidate_count_or_match_drift_fails_closed(self) -> None:
        for candidate_set in ("gameplay_foundation", "glass_focus"):
            expected = dict(
                TOOL.CANDIDATE_EXPECTED_COUNTS[candidate_set]
            )
            for field in (
                "compared_tile_occurrence_count",
                "exact_index_match_count",
                "visible_pattern_match_count",
            ):
                with self.subTest(candidate_set=candidate_set, field=field):
                    drifted = dict(expected)
                    drifted[field] += 1
                    with self.assertRaises(
                        TOOL.SchalaNpcOriginalityError
                    ):
                        TOOL.require_expected_candidate_counts(
                            candidate_set, drifted
                        )

    def test_candidate_source_hash_drift_fails_before_parsing(self) -> None:
        original_read_bytes = pathlib.Path.read_bytes

        for source_path, loader, label in (
            (
                TOOL.GAMEPLAY_SOURCE_PATH,
                TOOL._gameplay_candidates,
                "gameplay",
            ),
            (
                TOOL.GLASS_SOURCE_PATH,
                TOOL._glass_candidates,
                "Glass",
            ),
        ):
            source_raw = source_path.read_bytes()

            def drifted_read_bytes(path: pathlib.Path) -> bytes:
                if path.resolve() == source_path.resolve():
                    return source_raw[:-1] + bytes((source_raw[-1] ^ 1,))
                return original_read_bytes(path)

            with self.subTest(source=label), mock.patch.object(
                pathlib.Path, "read_bytes", drifted_read_bytes
            ), self.assertRaisesRegex(
                TOOL.SchalaNpcOriginalityError, "SHA-256 drifted"
            ):
                loader()

    def test_strict_sprite_decoder_is_imported_not_duplicated(self) -> None:
        self.assertIs(
            TOOL.corpus.decode_c3_sprite_packet,
            sys.modules[
                "audit_ct_compressed_sprite_corpus"
            ].decode_c3_sprite_packet,
        )

    def test_palette_pattern_and_all_flips_are_the_comparison_policy(self) -> None:
        self.assertEqual(
            TOOL.TRANSFORMS,
            ("identity", "horizontal", "vertical", "combined"),
        )
        reference = tuple(
            2 if (x, y) in {(0, 0), (1, 1), (3, 4)} else 0
            for y in range(8)
            for x in range(8)
        )
        renamed_horizontal = tuple(
            7 if reference[y * 8 + (7 - x)] else 0
            for y in range(8)
            for x in range(8)
        )
        candidates = {"synthetic": (8, 8, renamed_horizontal)}
        references = ((0,) * 64, reference)
        expected = {
            "asset_count": 1,
            "tile_occurrence_count": 1,
            "excluded_trivial_tile_occurrence_count": 0,
            "compared_tile_occurrence_count": 1,
            "exact_index_match_count": 0,
            "visible_pattern_match_count": 1,
            "framed_candidate_pixels_sha256": (
                TOOL._framed_candidate_pixels_sha256(
                    "synthetic", candidates
                )
            ),
        }
        with mock.patch.dict(
            TOOL.CANDIDATE_EXPECTED_COUNTS,
            {"synthetic": expected},
            clear=False,
        ):
            self.assertEqual(
                TOOL.compare_candidate_set(
                    "synthetic", candidates, references
                ),
                expected,
            )


@unittest.skipUnless(ROM_PATH.is_file(), "canonical private ROM unavailable")
class SchalaNpcOriginalityCanonicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rom = ROM_PATH.read_bytes()

    def test_wrong_rom_rejected_before_chain_inspection(self) -> None:
        wrong = bytearray(self.rom)
        wrong[-1] ^= 1
        with mock.patch.object(
            TOOL,
            "inspect_location_event_chain",
            side_effect=AssertionError("chain inspection must not run"),
        ), self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError, "SHA-(1|256)"
        ):
            temporary = ROOT / "private" / "wrong-never-written.sfc"
            original_read_bytes = pathlib.Path.read_bytes

            def wrong_rom_read_bytes(path: pathlib.Path) -> bytes:
                if path.resolve() == temporary.resolve():
                    return bytes(wrong)
                return original_read_bytes(path)

            with mock.patch.object(
                pathlib.Path, "read_bytes", wrong_rom_read_bytes
            ):
                TOOL.build_report(temporary)

    def test_location_record_mutation_is_rejected(self) -> None:
        mutated = bytearray(self.rom)
        mutated[TOOL.LOCATION_RECORD_FILE] ^= 1
        with self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError, "location.*record.*drifted"
        ):
            TOOL.inspect_location_event_chain(bytes(mutated))

    def test_event_pointer_and_packet_mutations_are_rejected(self) -> None:
        pointer_mutation = bytearray(self.rom)
        pointer_mutation[TOOL.EVENT_POINTER_ENTRY_FILE] ^= 1
        with self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError, "pointer entry.*drifted"
        ):
            TOOL.inspect_location_event_chain(bytes(pointer_mutation))

        packet_mutation = bytearray(self.rom)
        packet_mutation[TOOL.EVENT_PACKET_FILE + 100] ^= 1
        with self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError,
            "compressed packet SHA-256 drifted",
        ):
            TOOL.inspect_location_event_chain(bytes(packet_mutation))

    def test_sprite_table_mutations_are_rejected(self) -> None:
        for offset, expected_message in (
            (
                TOOL.GFX_POINTER_TABLE_FILE,
                "graphics pointer table SHA-256 drifted",
            ),
            (
                TOOL.NPC_DESCRIPTOR_TABLE_FILE,
                "NPC descriptor table SHA-256 drifted",
            ),
        ):
            with self.subTest(offset=offset):
                mutated = bytearray(self.rom)
                mutated[offset] ^= 1
                with self.assertRaisesRegex(
                    TOOL.SchalaNpcOriginalityError,
                    expected_message,
                ):
                    TOOL.inspect_sprite_chain(bytes(mutated))

    def test_descriptor_mutation_is_rejected_after_table_gate(self) -> None:
        mutated = bytearray(self.rom)
        mutated[TOOL.PRIMARY_NPC_DESCRIPTOR_FILE + 1] ^= 1
        mutated_bytes = bytes(mutated)
        with mock.patch.object(
            TOOL,
            "NPC_DESCRIPTOR_TABLE_SHA256",
            descriptor_table_digest(mutated_bytes),
        ), self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError,
            r"NPC \$09 descriptor SHA-256 drifted",
        ):
            TOOL.inspect_sprite_chain(mutated_bytes)

    def test_pointer_mutation_is_rejected_after_table_gate(self) -> None:
        mutated = bytearray(self.rom)
        mutated[TOOL.GFX_POINTER_ENTRY_FILE] ^= 1
        mutated_bytes = bytes(mutated)
        with mock.patch.object(
            TOOL,
            "GFX_POINTER_TABLE_SHA256",
            pointer_table_digest(mutated_bytes),
        ), self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError,
            r"selector \$26 pointer entry SHA-256 drifted",
        ):
            TOOL.inspect_sprite_chain(mutated_bytes)

    def test_cd_is_the_sole_same_geometry_palette_variant(self) -> None:
        metadata, _ = TOOL.inspect_sprite_chain(self.rom)
        family = metadata["descriptor_family"]
        self.assertEqual(
            family["same_geometry_npc_ids"],
            [TOOL.PRIMARY_NPC_ID, TOOL.PALETTE_VARIANT_NPC_ID],
        )
        primary = family["primary"]["fields"]
        variant = family["sole_same_geometry_palette_variant"]
        self.assertEqual(variant["only_differing_field"], "palette")
        for field in ("gfx_selector", "assembly", "animation", "size"):
            self.assertEqual(primary[field], variant["fields"][field])
        self.assertNotEqual(primary["palette"], variant["fields"]["palette"])

    def test_extra_same_geometry_descriptor_is_rejected(self) -> None:
        mutated = bytearray(self.rom)
        extra_id = 0x0A
        start = (
            TOOL.NPC_DESCRIPTOR_TABLE_FILE
            + extra_id * TOOL.NPC_DESCRIPTOR_WIDTH
        )
        mutated[start : start + TOOL.NPC_DESCRIPTOR_WIDTH] = (
            TOOL.PRIMARY_NPC_DESCRIPTOR
        )
        mutated_bytes = bytes(mutated)
        with mock.patch.object(
            TOOL,
            "NPC_DESCRIPTOR_TABLE_SHA256",
            descriptor_table_digest(mutated_bytes),
        ), self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError, "geometry.*family drifted"
        ):
            TOOL.inspect_sprite_chain(mutated_bytes)

    def test_sprite_packet_hash_size_and_shared_decoder_are_pinned(self) -> None:
        with mock.patch.object(
            TOOL.corpus,
            "decode_c3_sprite_packet",
            wraps=TOOL.corpus.decode_c3_sprite_packet,
        ) as decoder:
            metadata, packet_data = TOOL.inspect_sprite_chain(self.rom)
        decoder.assert_called_once_with(self.rom, TOOL.SPRITE_PACKET_FILE)
        packet = metadata["sprite_packet"]
        self.assertEqual(packet["compressed_size"], 2447)
        self.assertEqual(
            packet["compressed_sha256"],
            TOOL.SPRITE_PACKET_COMPRESSED_SHA256,
        )
        self.assertEqual(packet["decompressed_size"], 2528)
        self.assertEqual(
            packet["decompressed_sha256"],
            TOOL.SPRITE_PACKET_DECOMPRESSED_SHA256,
        )
        self.assertEqual(packet["tile_4bpp_count"], 79)
        self.assertEqual(
            TOOL.sha256(packet_data),
            TOOL.SPRITE_PACKET_DECOMPRESSED_SHA256,
        )

    def test_sprite_packet_mutation_is_rejected(self) -> None:
        mutated = bytearray(self.rom)
        mutated[TOOL.SPRITE_PACKET_FILE + 100] ^= 1
        with self.assertRaisesRegex(
            TOOL.SchalaNpcOriginalityError,
            "compressed packet SHA-256 drifted",
        ):
            TOOL.inspect_sprite_chain(bytes(mutated))

    def test_build_report_performs_no_filesystem_writes(self) -> None:
        original_open = pathlib.Path.open

        def read_only_open(
            path: pathlib.Path, mode: str = "r", *args: object, **kwargs: object
        ):
            if any(marker in mode for marker in ("w", "a", "x", "+")):
                raise AssertionError(f"unexpected write open: {path}")
            return original_open(path, mode, *args, **kwargs)

        with mock.patch.object(pathlib.Path, "open", read_only_open):
            report = TOOL.build_report(ROM_PATH)
        self.assertIs(report["files_emitted"], False)


@unittest.skipUnless(
    ROM_PATH.is_file() and REPORT_PATH.is_file(),
    "canonical ROM or checked report unavailable",
)
class SchalaNpcOriginalityReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected_raw = REPORT_PATH.read_bytes()
        cls.expected = json.loads(cls.expected_raw)

    def test_report_schema_anchor_counts_and_claim_boundaries(self) -> None:
        self.assertEqual(
            self.expected["schema_version"], TOOL.REPORT_SCHEMA_VERSION
        )
        semantic = self.expected["semantic_identity"]
        self.assertEqual(semantic["evidence"], "documented")
        self.assertEqual(
            semantic["anchor"]["commit"], TOOL.SEMANTIC_ANCHOR_COMMIT
        )
        self.assertEqual(
            semantic["anchor"]["url"], TOOL.SEMANTIC_ANCHOR_URL
        )
        self.assertEqual(semantic["anchor"]["lines"], "188-201")
        self.assertEqual(
            self.expected["behavior_dependencies"],
            list(TOOL.BEHAVIOR_DEPENDENCIES),
        )
        self.assertEqual(
            self.expected["reference_scope"]["compared_tile_count"], 78
        )
        for candidate_set in ("gameplay_foundation", "glass_focus"):
            self.assertEqual(
                self.expected["candidate_sets"][candidate_set]["counts"],
                TOOL.CANDIDATE_EXPECTED_COUNTS[candidate_set],
            )
        claims = self.expected["claims"]
        for field in (
            "global_npc_originality_claimed",
            "near_match_analysis_claimed",
            "silhouette_analysis_claimed",
            "animation_analysis_claimed",
            "assembly_layout_analysis_claimed",
            "runtime_semantic_identity_claimed",
        ):
            self.assertIs(claims[field], False)

    def test_report_is_metadata_only(self) -> None:
        lowered = self.expected_raw.lower()
        for forbidden in (
            b'"decoded_bytes"',
            b'"decoded_pixels"',
            b'"pixel_data"',
            b'"image_data"',
            b'"output_path"',
            b"private\\\\input",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn(str(ROM_PATH).encode("utf-8"), self.expected_raw)
        self.assertTrue(self.expected_raw.endswith(b"\n"))
        self.assertNotIn(b"\r", self.expected_raw)

    def test_build_report_exactly_reproduces_checked_report(self) -> None:
        self.assertEqual(TOOL.build_report(ROM_PATH), self.expected)
        self.assertEqual(
            TOOL.canonical_report_bytes(self.expected), self.expected_raw
        )

    def test_generation_does_not_read_checked_report(self) -> None:
        original_read_bytes = pathlib.Path.read_bytes

        def guarded_read_bytes(path: pathlib.Path) -> bytes:
            if path.resolve() == REPORT_PATH.resolve():
                raise AssertionError("generator read its checked report")
            return original_read_bytes(path)

        with mock.patch.object(
            pathlib.Path, "read_bytes", guarded_read_bytes
        ):
            self.assertEqual(TOOL.build_report(ROM_PATH), self.expected)

    def test_cli_stdout_is_byte_identical_and_writes_nothing(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        before = {
            path: (path.stat().st_size, path.stat().st_mtime_ns)
            for path in (
                TOOL_PATH,
                REPORT_PATH,
                TOOL.GAMEPLAY_SOURCE_PATH,
                TOOL.GLASS_SOURCE_PATH,
                TOOL.GLASS_MANIFEST_PATH,
                ROM_PATH,
            )
        }
        completed = subprocess.run(
            [
                sys.executable,
                str(TOOL_PATH),
                "--rom",
                str(ROM_PATH),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            env=environment,
        )
        after = {
            path: (path.stat().st_size, path.stat().st_mtime_ns)
            for path in before
        }
        self.assertEqual(completed.stdout, self.expected_raw)
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
