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
TOOL_PATH = TOOLS_DIR / "audit_schala_current_body_packet.py"
REPORT_PATH = ROOT / "references" / "schala_current_body_packet_v0.json"

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_current_body_packet", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaCurrentBodyPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validated = TOOL.load_validated_inputs()
        cls.compiled = TOOL.compile_current_body_packet(
            cls.validated["frames"],
            cls.validated["foundation"],
            cls.validated["packet_helper"],
        )
        cls.measurements = TOOL.require_expected_packet(
            cls.compiled,
            cls.validated["palette"],
            cls.validated["foundation_packet"],
        )
        cls.report = TOOL.build_report()

    def test_all_source_and_behavior_dependencies_are_exactly_pinned(
        self,
    ) -> None:
        self.assertEqual(len(TOOL.SOURCE_ARTIFACTS), 4)
        self.assertEqual(len(TOOL.BEHAVIOR_DEPENDENCIES), 3)
        self.assertEqual(
            TOOL.verify_behavior_dependencies(),
            list(TOOL.BEHAVIOR_DEPENDENCIES),
        )
        for record in (*TOOL.SOURCE_ARTIFACTS, *TOOL.BEHAVIOR_DEPENDENCIES):
            path = ROOT.joinpath(*pathlib.PurePosixPath(record["path"]).parts)
            raw = path.read_bytes()
            self.assertEqual(len(raw), record["size"])
            self.assertEqual(TOOL.sha256(raw), record["sha256"])

    def test_dependency_drift_fails_before_helper_import(self) -> None:
        target_record = TOOL.BEHAVIOR_DEPENDENCIES[0]
        target = ROOT.joinpath(
            *pathlib.PurePosixPath(target_record["path"]).parts
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
            TOOL.importlib,
            "import_module",
            side_effect=AssertionError("helper imported before hash gate"),
        ), self.assertRaisesRegex(
            TOOL.CurrentBodyPacketError,
            "behavior dependency.*SHA-256 drifted",
        ):
            TOOL._load_helpers()

    def test_source_drift_fails_before_json_parsing(self) -> None:
        target_record = TOOL.SOURCE_ARTIFACTS[2]
        target = ROOT.joinpath(
            *pathlib.PurePosixPath(target_record["path"]).parts
        ).resolve()
        target_raw = target.read_bytes()
        original_read_bytes = pathlib.Path.read_bytes

        def drifted_read_bytes(path: pathlib.Path) -> bytes:
            if path.resolve() == target:
                return target_raw[:-1] + bytes((target_raw[-1] ^ 1,))
            return original_read_bytes(path)

        with mock.patch.object(
            pathlib.Path, "read_bytes", drifted_read_bytes
        ), self.assertRaisesRegex(
            TOOL.CurrentBodyPacketError,
            "source artifact.*SHA-256 drifted",
        ):
            TOOL.load_validated_inputs()

    def test_cli_accepts_no_rom_or_output_path(self) -> None:
        parser = TOOL.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions}, {"help"}
        )
        for forbidden in (
            ["--rom", "clean.sfc"],
            ["--output", "report.json"],
            ["--output-dir", "private/build"],
        ):
            with self.subTest(arguments=forbidden), contextlib.redirect_stderr(
                io.StringIO()
            ), self.assertRaises(SystemExit):
                parser.parse_args(forbidden)

    def test_existing_sources_remain_unbound_and_share_one_palette(self) -> None:
        focus_raw = TOOL.FOCUS_SOURCE_REL
        source = json.loads((ROOT / focus_raw).read_text(encoding="utf-8"))
        self.assertFalse(source["rom_installable"])
        self.assertTrue(
            all(
                value is None
                for value in source["native_runtime_bindings"].values()
            )
        )
        self.assertEqual(
            self.validated["palette"],
            self.validated["focus_helper"].validate_source(source)[
                "palette_bytes"
            ],
        )
        focus_manifest = json.loads(
            (ROOT / TOOL.FOCUS_MANIFEST_REL).read_text(encoding="utf-8")
        )
        self.assertFalse(
            focus_manifest["expected_validation"]["frames"][
                "assembly_packability_claimed"
            ]
        )

    def test_exact_sixteen_frame_inventory_and_provisional_order(self) -> None:
        self.assertEqual(
            tuple(frame["id"] for frame in self.validated["frames"]),
            TOOL.BODY_FRAME_IDS,
        )
        self.assertEqual(len(set(TOOL.BODY_FRAME_IDS)), 16)
        inventory = self.report["frame_inventory"]
        self.assertEqual(
            tuple(row["frame_id"] for row in inventory),
            TOOL.BODY_FRAME_IDS,
        )
        self.assertEqual(
            tuple(row["source_ordinal"] for row in inventory),
            tuple(range(16)),
        )
        self.assertFalse(
            self.report["scope"]["source_ordinals_are_native_animation_ids"]
        )

    def test_exact_packet_sizes_hashes_and_tile_bounds(self) -> None:
        packet = self.report["packet"]
        self.assertEqual(packet["graphics"]["size"], 0x0B60)
        self.assertEqual(
            packet["graphics"]["sha256"],
            "361ea69917d97a8c68e4450df0b944e43c9dad73b3aca2ecf52304ed70484a66",
        )
        self.assertEqual(
            packet["graphics"]["tile_count_including_reserved_blank"],
            91,
        )
        self.assertEqual(
            packet["graphics"]["nontransparent_unique_tile_count"], 90
        )
        self.assertEqual(packet["graphics"]["maximum_tile_index"], 0x5A)
        self.assertEqual(packet["assembly"]["size"], 0x0280)
        self.assertEqual(
            packet["assembly"]["sha256"],
            "b14735361a2546337d32ad3f8318a4138980c16515a7cbcc48a1b92de89d69d1",
        )
        self.assertEqual(packet["assembly"]["record_count"], 16)
        self.assertEqual(packet["palette"]["size"], 0x20)
        self.assertEqual(
            packet["palette"]["sha256"],
            "782a063ffc99087cca1b64876cd024a5c5c7e6c6193c8f9ff224e9ed88ead5ea",
        )

    def test_all_frames_fit_four_objects_and_expected_canvases(self) -> None:
        records = self.compiled["frame_records"]
        counts = [record["active_object_count"] for record in records]
        self.assertEqual(counts.count(3), 1)
        self.assertEqual(counts.count(4), 15)
        three_object = [
            record["frame_id"]
            for record in records
            if record["active_object_count"] == 3
        ]
        self.assertEqual(
            three_object, ["schala_field_walk_down_f01_v0"]
        )
        self.assertTrue(
            all(
                record["canvas"]
                == ({"width": 24, "height": 32} if index < 7 else {"width": 40, "height": 40})
                for index, record in enumerate(records)
            )
        )

    def test_every_record_is_native_shaped_and_reconstructs_exactly(
        self,
    ) -> None:
        helper = self.validated["packet_helper"]
        assembly = self.compiled["assembly"]
        self.assertEqual(len(assembly), 16 * helper.FRAME_RECORD_SIZE)
        for source, record in zip(
            self.validated["frames"],
            self.compiled["frame_records"],
            strict=True,
        ):
            start = record["frame_index"] * helper.FRAME_RECORD_SIZE
            raw_record = assembly[start : start + helper.FRAME_RECORD_SIZE]
            self.assertEqual(len(raw_record), 0x28)
            words = [
                int.from_bytes(raw_record[offset : offset + 2], "little")
                for offset in range(0, 0x20, 2)
            ]
            self.assertEqual(len(words), 16)
            self.assertTrue(all(word <= 0x07FF for word in words))
            reconstructed = helper.reconstruct_frame(
                self.compiled["graphics"], assembly, record
            )
            self.assertEqual(
                reconstructed,
                (
                    source["width"],
                    source["height"],
                    tuple(source["pixels"]),
                ),
            )

    def test_addition_preserves_the_complete_ten_frame_prefix(self) -> None:
        foundation = self.validated["foundation_packet"]
        self.assertTrue(
            self.compiled["graphics"].startswith(foundation["graphics"])
        )
        self.assertEqual(
            self.compiled["assembly"][: len(foundation["assembly"])],
            foundation["assembly"],
        )
        self.assertEqual(self.measurements["new_unique_tile_count"], 10)
        self.assertEqual(
            self.measurements["new_assembly_record_count"], 6
        )

    def test_focus_inserts_and_audio_are_excluded_from_body_packet(self) -> None:
        inventory_ids = {
            row["frame_id"] for row in self.report["frame_inventory"]
        }
        self.assertTrue(inventory_ids.isdisjoint(TOOL.FOCUS_INSERT_IDS))
        self.assertTrue(inventory_ids.isdisjoint(TOOL.AUDIO_RECIPE_IDS))
        excluded = self.report["excluded_source_components"]
        self.assertEqual(
            tuple(excluded["focus_insert_ids"]), TOOL.FOCUS_INSERT_IDS
        )
        self.assertEqual(
            tuple(excluded["audio_recipe_ids"]), TOOL.AUDIO_RECIPE_IDS
        )
        self.assertFalse(self.report["scope"]["focus_inserts_composited"])

    def test_changed_inventory_and_invalid_pixels_fail_closed(self) -> None:
        helper = self.validated["packet_helper"]
        foundation = self.validated["foundation"]
        reordered = list(self.validated["frames"])
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaisesRegex(
            TOOL.CurrentBodyPacketError, "pinned body inventory"
        ):
            TOOL.compile_current_body_packet(
                reordered, foundation, helper
            )

        invalid = [dict(frame) for frame in self.validated["frames"]]
        invalid[0]["pixels"] = (16,) + tuple(invalid[0]["pixels"])[1:]
        with self.assertRaisesRegex(
            TOOL.CurrentBodyPacketError, "outside 4bpp"
        ):
            TOOL.compile_current_body_packet(invalid, foundation, helper)

    def test_five_object_shape_and_signed_coordinate_overflow_fail(self) -> None:
        helper = self.validated["packet_helper"]
        isolated = {(0, 0), (2, 0), (4, 0), (0, 2), (2, 2)}
        with self.assertRaisesRegex(ValueError, "four disjoint"):
            helper.select_object_origins(isolated, 5, 3)
        for value in (-129, 128):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "signed byte"
            ):
                helper._signed_byte(value)

    def test_packet_measurement_drift_fails_closed(self) -> None:
        modified = dict(self.compiled)
        modified["graphics"] = self.compiled["graphics"][:-1] + bytes(
            (self.compiled["graphics"][-1] ^ 1,)
        )
        with self.assertRaisesRegex(
            TOOL.CurrentBodyPacketError, "measurements drifted"
        ):
            TOOL.require_expected_packet(
                modified,
                self.validated["palette"],
                self.validated["foundation_packet"],
            )

    def test_report_has_bounded_evidence_and_explicit_nonclaims(self) -> None:
        self.assertEqual(
            self.report["evidence"]["native_shaped_packet_fit"],
            "verified-static",
        )
        self.assertEqual(
            self.report["evidence"]["source_order"],
            "proposal-only-not-native-animation-semantics",
        )
        self.assertEqual(
            self.report["evidence"]["runtime_rendering"],
            "not performed",
        )
        joined = " ".join(self.report["nonclaims"])
        for required in (
            "animation-slot",
            "expanded-bank",
            "action $90",
            "ROM allocation",
            "logical PC $07",
            "241-packet",
            "Epoch",
        ):
            self.assertIn(required, joined)

    def test_report_serializes_metadata_not_pixels_or_binary(self) -> None:
        forbidden_keys = {
            "rows",
            "pixels",
            "tile_bytes",
            "tile_words",
            "assembly_bytes",
            "palette_bytes",
            "graphics_bytes",
            "decoded_bytes",
            "image",
        }

        def visit(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.report)
        encoded = TOOL.canonical_report_bytes(self.report)
        self.assertNotIn(b".sfc", encoded)
        self.assertNotIn(b"private/", encoded)

    def test_report_generation_does_not_read_pinned_report_or_write(self) -> None:
        original_read_bytes = pathlib.Path.read_bytes

        def guarded_read_bytes(path: pathlib.Path) -> bytes:
            if path.resolve() == REPORT_PATH.resolve():
                raise AssertionError("report read during report generation")
            return original_read_bytes(path)

        with mock.patch.object(
            pathlib.Path, "read_bytes", guarded_read_bytes
        ), mock.patch.object(
            pathlib.Path,
            "write_bytes",
            side_effect=AssertionError("binary file write attempted"),
        ), mock.patch.object(
            pathlib.Path,
            "write_text",
            side_effect=AssertionError("text file write attempted"),
        ):
            regenerated = TOOL.build_report()
        self.assertEqual(regenerated, self.report)

    def test_cli_stdout_is_byte_identical_to_pinned_report(self) -> None:
        expected = REPORT_PATH.read_bytes()
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(completed.stdout, expected)
        self.assertEqual(
            completed.stdout, TOOL.canonical_report_bytes(self.report)
        )


if __name__ == "__main__":
    unittest.main()
