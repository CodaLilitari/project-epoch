from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_schala_glass_focus_pulse_v0.py"
SOURCE_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "focus"
    / "glass_focus_pulse_v0.json"
)
MANIFEST_PATH = (
    ROOT
    / "assets"
    / "source"
    / "schala"
    / "v0"
    / "focus"
    / "glass_focus_pulse_manifest_v0.json"
)

SPEC = importlib.util.spec_from_file_location(
    "validate_schala_glass_focus_pulse_v0", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class GlassFocusPulseSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_raw, cls.source = TOOL.load_json(SOURCE_PATH)
        _, cls.manifest = TOOL.load_json(MANIFEST_PATH)
        cls.validated = TOOL.validate_source(cls.source)
        cls.report = TOOL.validation_report(cls.source_raw, cls.source)

    def test_manifest_pins_source_validator_dependencies_and_evidence(
        self,
    ) -> None:
        TOOL.verify_manifest(
            self.manifest, self.source_raw, self.report
        )
        self.assertEqual(
            self.manifest["status"],
            "source-only-vertical-slice-unbound",
        )
        self.assertIs(
            self.manifest["generated_artifact_policy"][
                "binary_files_emitted"
            ],
            False,
        )

    def test_identity_is_only_e8_visual0_action90_pc07(self) -> None:
        self.assertEqual(
            self.source["binding_identity"],
            {
                "logical_pc_id": 7,
                "action_id": 0x90,
                "item_id": 0xE8,
                "focus_visual_id": 0,
                "binding_state": "unbound",
            },
        )
        item_ids = [
            value
            for key, value in TOOL._walk(self.source)
            if key == "item_id"
        ]
        self.assertEqual(item_ids, [0xE8])
        self.assertNotIn(0xE9, item_ids)
        self.assertNotIn(0xEA, item_ids)
        self.assertNotIn(0xEB, item_ids)

    def test_every_native_and_runtime_binding_is_null(self) -> None:
        bindings = self.source["native_runtime_bindings"]
        self.assertTrue(bindings)
        self.assertTrue(all(value is None for value in bindings.values()))
        for recipe in self.source["audio_recipes"]:
            self.assertIsNone(recipe["native_sfx_id"])
            self.assertIsNone(recipe["runtime_pointer"])
            self.assertIsNone(recipe["rendered_audio_path"])
        self.assertIs(self.report["rom_installable"], False)
        self.assertEqual(self.report["allocation_status"], "unbound")

    def test_six_dedicated_basic_attack_frames_are_ordered_and_bounded(
        self,
    ) -> None:
        frames = self.validated["frames"]
        self.assertEqual(tuple(frames), TOOL.FRAME_IDS)
        for index, (frame_id, phase) in enumerate(TOOL.FRAME_PHASES):
            frame = frames[frame_id]
            self.assertEqual(frame["sequence_index"], index)
            self.assertEqual(frame["context"], "battle_action")
            self.assertEqual(frame["category"], "basic_attack")
            self.assertEqual(frame["phase"], phase)
            self.assertEqual(frame["direction"], "right")
            self.assertEqual(
                TOOL._parse_pixels(frame, TOOL.FRAME_DIMENSIONS)[:2],
                TOOL.FRAME_DIMENSIONS,
            )
            self.assertLessEqual(
                self.validated["frame_occupied"][frame_id], 16
            )
        self.assertIs(
            self.report["frames"]["assembly_packability_claimed"], False
        )

    def test_frame_4bpp_validation_is_round_trip_and_deterministic(
        self,
    ) -> None:
        aggregate = bytearray()
        serialized = []
        for frame_id in TOOL.FRAME_IDS:
            frame = self.validated["frames"][frame_id]
            width, height, pixels = TOOL._parse_pixels(
                frame, TOOL.FRAME_DIMENSIONS
            )
            packed = TOOL.encode_snes_4bpp(pixels, width, height)
            self.assertEqual(
                TOOL.decode_snes_4bpp(packed, width, height), pixels
            )
            aggregate.extend(packed)
            serialized.append(pixels)
        self.assertEqual(len(set(serialized)), 6)
        self.assertEqual(bytes(aggregate), self.validated["frame_bytes"])
        self.assertEqual(
            TOOL.sha256(bytes(aggregate)),
            self.report["frames"]["validation_4bpp_sha256"],
        )

    def test_six_standalone_focus_inserts_use_only_existing_focus_colors(
        self,
    ) -> None:
        inserts = self.validated["inserts"]
        self.assertEqual(tuple(inserts), TOOL.INSERT_IDS)
        for insert_id, vocabulary in TOOL.INSERT_VOCABULARY:
            insert = inserts[insert_id]
            self.assertEqual(insert["vocabulary"], vocabulary)
            width, height, pixels = TOOL._parse_pixels(
                insert, TOOL.INSERT_DIMENSIONS
            )
            self.assertEqual((width, height), (16, 16))
            self.assertTrue(
                set(pixels).issubset(TOOL.FOCUS_INSERT_INDICES)
            )
            self.assertIn(13, pixels)
            self.assertIn(14, pixels)
            self.assertLessEqual(
                self.validated["insert_occupied"][insert_id], 4
            )
        impact = inserts["glass_focus_impact_arc_v0"]
        width, height, pixels = TOOL._parse_pixels(
            impact, TOOL.INSERT_DIMENSIONS
        )
        tiles = tuple(TOOL.iter_tiles(pixels, width, height))
        self.assertEqual(
            {
                tile_index: sum(
                    pixel != 0 for pixel in tiles[tile_index]
                )
                for tile_index in (
                    TOOL.IMPACT_ARC_CORRECTED_TILE_VISIBLE_COUNTS
                )
            },
            TOOL.IMPACT_ARC_CORRECTED_TILE_VISIBLE_COUNTS,
        )

    def test_each_insert_is_used_exactly_once_by_the_attack_sequence(
        self,
    ) -> None:
        actual = [
            self.validated["frames"][frame_id]["focus_insert_id"]
            for frame_id in TOOL.FRAME_IDS
        ]
        self.assertEqual(tuple(actual), TOOL.FRAME_INSERT_IDS)
        self.assertEqual(set(actual), set(TOOL.INSERT_IDS))

    def test_existing_gameplay_palette_is_referenced_not_copied(self) -> None:
        self.assertNotIn("palette", self.source)
        dependency = self.source["palette_dependency"]
        self.assertEqual(dependency["palette_id"], TOOL.PALETTE_ID)
        self.assertEqual(dependency["allowed_indices"], list(range(16)))
        self.assertEqual(
            dependency["focus_insert_indices"],
            list(TOOL.FOCUS_INSERT_INDICES),
        )
        self.assertIs(dependency["embedded_palette_copy"], False)
        self.assertEqual(
            len(self.validated["palette_bytes"]), 0x20
        )
        self.assertEqual(
            TOOL.sha256(self.validated["palette_bytes"]),
            self.report["palette"]["packed_bgr555_sha256"],
        )

    def test_audio_is_exactly_two_integer_only_source_recipes(self) -> None:
        recipes = self.validated["audio_recipes"]
        self.assertEqual(
            tuple(recipe["id"] for recipe in recipes), TOOL.AUDIO_IDS
        )
        self.assertEqual(
            tuple(recipe["role"] for recipe in recipes), ("swing", "hit")
        )
        for recipe in recipes:
            self.assertEqual(recipe["sample_rate_hz"], 32000)
            self.assertIs(type(recipe["duration_samples"]), int)
            self.assertGreater(recipe["duration_samples"], 0)
            for oscillator in recipe["oscillators"]:
                for field in (
                    "start_frequency_millihz",
                    "end_frequency_millihz",
                    "amplitude_q15",
                    "phase_q16",
                ):
                    self.assertIs(type(oscillator[field]), int)
            self.assertIs(type(recipe["noise"]["seed"]), int)
        expected = TOOL.canonical_json_bytes(
            self.source["audio_recipes"]
        )
        self.assertEqual(
            expected, self.validated["audio_recipe_bytes"]
        )
        self.assertEqual(
            TOOL.sha256(expected),
            self.report["audio_recipes"]["canonical_sha256"],
        )
        self.assertIs(
            self.report["audio_recipes"]["rendered_audio_emitted"], False
        )

    def test_provenance_declares_same_project_reuse_truthfully(self) -> None:
        visual = self.source["provenance"]["visual_authorship"]
        self.assertIs(
            visual["same_project_original_body_pixels_reused"], True
        )
        self.assertEqual(
            visual["same_project_source_path"],
            TOOL.GAMEPLAY_REL.as_posix(),
        )
        for field in (
            "external_imported_layers",
            "external_imported_pixels",
            "rom_or_extracted_tile_input",
            "npc_sprite_input",
            "vanilla_playable_character_sprite_input",
            "official_art_pixel_input",
            "concept_bitmap_input",
            "concept_pixels_sampled",
            "concept_palette_sampled",
            "automatic_resizing",
        ):
            self.assertIs(visual[field], False)
        audio = self.source["provenance"]["audio_authorship"]
        for field in (
            "sampled_audio_input",
            "rom_or_extracted_sfx_input",
            "copied_vanilla_sfx_parameters",
            "rendered_audio_committed",
        ):
            self.assertIs(audio[field], False)
        correction = self.source["provenance"][
            "playable_pc_metadata_correction"
        ]
        self.assertEqual(
            correction["affected_asset_id"],
            "glass_focus_impact_arc_v0",
        )
        self.assertEqual(
            correction["affected_candidate_tile_indices"], [0, 2]
        )
        self.assertEqual(correction["candidate_tile_count"], 174)
        self.assertEqual(correction["reference_tile_count"], 7264)
        self.assertEqual(
            correction["audit_tool_path"],
            "tools/audit_schala_glass_focus_originality.py",
        )
        self.assertEqual(correction["asset_count"], 12)
        self.assertEqual(correction["excluded_candidate_tile_count"], 80)
        self.assertEqual(correction["compared_candidate_tile_count"], 94)
        self.assertEqual(correction["excluded_reference_tile_count"], 59)
        self.assertEqual(correction["compared_reference_tile_count"], 7205)
        self.assertEqual(
            correction["pre_correction_visible_pattern_match_count"], 6
        )
        self.assertEqual(
            correction["post_correction_exact_index_match_count"], 0
        )
        self.assertEqual(
            correction["post_correction_visible_pattern_match_count"], 0
        )
        self.assertIs(
            correction["reference_pixels_displayed_or_exported"], False
        )
        self.assertIs(correction["npc_originality_claimed"], False)

    def test_validation_report_emits_no_binary_or_runtime_claim(self) -> None:
        self.assertIs(self.report["binary_files_emitted"], False)
        self.assertIs(self.report["rom_installable"], False)
        self.assertEqual(
            self.report["runtime_use_policy"],
            "reject-before-any-native-or-wram-write",
        )
        self.assertIs(
            self.report["provenance"]["validator_rom_accessed"], False
        )
        self.assertNotIn("rom_accessed", self.report["provenance"])
        self.assertIs(
            self.report["provenance"][
                "recorded_playable_pc_metadata_correction"
            ]["originality_auditor_rom_accessed"],
            True,
        )
        self.assertIs(
            self.report["provenance"][
                "sampled_or_extracted_audio_imported"
            ],
            False,
        )


class GlassFocusPulseMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_raw, cls.source = TOOL.load_json(SOURCE_PATH)
        _, cls.manifest = TOOL.load_json(MANIFEST_PATH)
        cls.report = TOOL.validation_report(cls.source_raw, cls.source)

    def assert_rejected(self, source: dict) -> None:
        with self.assertRaises(TOOL.FocusSourceError):
            TOOL.validate_source(source)

    def assert_manifest_rejected(self, manifest: dict) -> None:
        with self.assertRaises(TOOL.FocusSourceError):
            TOOL.verify_manifest(
                manifest, self.source_raw, self.report
            )

    def test_rejects_boolean_source_or_manifest_schema(self) -> None:
        modified = copy.deepcopy(self.source)
        modified["schema_version"] = True
        self.assert_rejected(modified)

        manifest = copy.deepcopy(self.manifest)
        manifest["schema_version"] = True
        self.assert_manifest_rejected(manifest)

    def test_rejects_source_identity_narrative_type_or_text_drift(
        self,
    ) -> None:
        for field, values in {
            "created": ([], "2026-07-29"),
            "author": ({}, "Unknown"),
            "scope_statement": (
                1,
                "Runtime-ready Glass Focus with NPC originality proved.",
            ),
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    modified = copy.deepcopy(self.source)
                    modified[field] = value
                    self.assert_rejected(modified)

    def test_rejects_visual_and_audio_narrative_drift(self) -> None:
        for section in ("visual_authorship", "audio_authorship"):
            for field in ("method", "statement"):
                with self.subTest(section=section, field=field):
                    modified = copy.deepcopy(self.source)
                    modified["provenance"][section][field] = (
                        "NPC-derived and runtime-ready."
                    )
                    self.assert_rejected(modified)

        modified = copy.deepcopy(self.source)
        modified["frames"][0]["composition"] = (
            "Copied from a canonical NPC and installed at runtime."
        )
        self.assert_rejected(modified)

    def test_rejects_reference_classification_or_use_drift(self) -> None:
        for reference_index in range(len(self.source["references"])):
            for field in ("source_classification", "use"):
                with self.subTest(
                    reference_index=reference_index, field=field
                ):
                    modified = copy.deepcopy(self.source)
                    modified["references"][reference_index][field] = (
                        "runtime-integrated-NPC-source"
                    )
                    self.assert_rejected(modified)

    def test_rejects_originality_scope_command_and_count_drift(self) -> None:
        correction_fields = {
            "audit_scope": "All tiles compared; NPC originality proved.",
            "method": "visual inspection",
            "audit_command": "python unpinned.py --output report.bin",
            "correction": "Copied reference pixels.",
            "asset_count": True,
            "excluded_candidate_tile_count": 79,
            "compared_candidate_tile_count": 95,
            "excluded_reference_tile_count": 58,
            "compared_reference_tile_count": 7206,
        }
        for field, value in correction_fields.items():
            with self.subTest(field=field):
                modified = copy.deepcopy(self.source)
                modified["provenance"][
                    "playable_pc_metadata_correction"
                ][field] = value
                self.assert_rejected(modified)

    def test_rejects_manifest_narrative_and_originality_overclaims(
        self,
    ) -> None:
        for field, value in {
            "created": [],
            "modified": "tomorrow",
            "author": 7,
            "review_status": "runtime and NPC review complete",
            "provenance_statement": "NPC originality proven; ROM installed.",
        }.items():
            with self.subTest(field=field):
                modified = copy.deepcopy(self.manifest)
                modified[field] = value
                self.assert_manifest_rejected(modified)

        modified = copy.deepcopy(self.manifest)
        modified["originality_audit"]["npc_originality_claimed"] = True
        self.assert_manifest_rejected(modified)

        modified = copy.deepcopy(self.manifest)
        modified["evidence"]["rom_integration"] = "verified-runtime"
        self.assert_manifest_rejected(modified)

    def test_rejects_manifest_originality_report_pin_drift(self) -> None:
        for field, value in (
            ("path", "references/other.json"),
            ("sha256", "0" * 64),
            ("size", 0),
            ("dependency_scope", "runtime-input"),
            ("reproduction", "python unpinned.py"),
        ):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.manifest)
                modified["originality_audit"][field] = value
                self.assert_manifest_rejected(modified)

    def test_rejects_any_external_or_rom_pixel_input(self) -> None:
        for field in (
            "external_imported_pixels",
            "rom_or_extracted_tile_input",
            "npc_sprite_input",
            "vanilla_playable_character_sprite_input",
        ):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.source)
                modified["provenance"]["visual_authorship"][field] = True
                self.assert_rejected(modified)

    def test_rejects_false_denial_of_same_project_body_reuse(self) -> None:
        modified = copy.deepcopy(self.source)
        modified["provenance"]["visual_authorship"][
            "same_project_original_body_pixels_reused"
        ] = False
        self.assert_rejected(modified)
        modified = copy.deepcopy(self.source)
        modified["provenance"]["playable_pc_metadata_correction"][
            "npc_originality_claimed"
        ] = True
        self.assert_rejected(modified)

        modified = copy.deepcopy(self.source)
        modified["provenance"]["playable_pc_metadata_correction"][
            "post_correction_exact_index_match_count"
        ] = False
        self.assert_rejected(modified)

    def test_rejects_other_focus_item_or_visual_identity(self) -> None:
        for field, value in (("item_id", 0xE9), ("focus_visual_id", 1)):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.source)
                modified["binding_identity"][field] = value
                self.assert_rejected(modified)

    def test_rejects_boolean_substituted_for_identity_integer(self) -> None:
        modified = copy.deepcopy(self.source)
        modified["binding_identity"]["focus_visual_id"] = False
        self.assert_rejected(modified)

    def test_rejects_non_null_native_runtime_binding(self) -> None:
        for field in self.source["native_runtime_bindings"]:
            with self.subTest(field=field):
                modified = copy.deepcopy(self.source)
                modified["native_runtime_bindings"][field] = 1
                self.assert_rejected(modified)

    def test_rejects_palette_copy_or_non_focus_insert_color(self) -> None:
        modified = copy.deepcopy(self.source)
        modified["palette_dependency"]["embedded_palette_copy"] = True
        self.assert_rejected(modified)

        modified = copy.deepcopy(self.source)
        modified["focus_inserts"][0]["rows"][0] = (
            "20000000 00000000"
        )
        self.assert_rejected(modified)

    def test_rejects_rendered_or_native_audio_binding(self) -> None:
        for field, value in (
            ("native_sfx_id", 1),
            ("runtime_pointer", 0x123456),
            ("rendered_audio_path", "focus.wav"),
        ):
            with self.subTest(field=field):
                modified = copy.deepcopy(self.source)
                modified["audio_recipes"][0][field] = value
                self.assert_rejected(modified)

    def test_rejects_boolean_substituted_for_audio_integer(self) -> None:
        modified = copy.deepcopy(self.source)
        modified["audio_recipes"][0]["duration_samples"] = True
        self.assert_rejected(modified)

    def test_duplicate_json_key_hook_fails_closed(self) -> None:
        with self.assertRaises(TOOL.FocusSourceError):
            TOOL._reject_duplicate_keys(
                [("schema_version", 1), ("schema_version", 2)]
            )

    def test_rejects_hidden_extra_source_frame_or_insert_fields(self) -> None:
        for target in ("source", "frame", "insert"):
            with self.subTest(target=target):
                modified = copy.deepcopy(self.source)
                if target == "source":
                    modified["hidden_runtime_binding"] = 0
                elif target == "frame":
                    modified["frames"][0]["hidden_binary_payload"] = "00"
                else:
                    modified["focus_inserts"][0][
                        "hidden_native_palette_id"
                    ] = 0
                self.assert_rejected(modified)


if __name__ == "__main__":
    unittest.main()
