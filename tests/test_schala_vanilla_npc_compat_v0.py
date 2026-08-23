from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "build_schala_vanilla_npc_compat_v0.py"
REFERENCE_PATH = (
    ROOT / "references" / "schala_vanilla_npc_compat_v0.json"
)


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "build_schala_vanilla_npc_compat_v0", TOOL_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load compatibility builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


class SchalaVanillaNpcCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reference_raw = REFERENCE_PATH.read_bytes()
        cls.reference = json.loads(cls.reference_raw.decode("utf-8"))
        cls.rom_available = TOOL.DEFAULT_ROM.is_file()
        if cls.rom_available:
            cls.rom = TOOL.DEFAULT_ROM.read_bytes()
            cls.bundle = TOOL.build_bundle(cls.rom)

    def require_rom(self) -> None:
        if not self.rom_available:
            self.skipTest("private canonical ROM is unavailable")

    def test_checked_reference_is_canonical_metadata_only_json(self) -> None:
        self.assertEqual(
            self.reference_raw, TOOL.canonical_json(self.reference)
        )
        self.assertEqual(self.reference["schema_version"], 1)
        self.assertEqual(
            self.reference["status"],
            "pass-private-canonical-npc-compatibility-source",
        )
        self.assertFalse(
            self.reference["evidence"]["runtime_logical_pc_07_exercised"]
        )
        self.assertFalse(
            self.reference["eligibility"]["source_control_raw_bytes"]
        )
        self.assertFalse(
            self.reference["intent"]["crimson_echoes_material_included"]
        )

    def test_checked_metadata_contains_no_raw_payload_fields(self) -> None:
        self.assertEqual(len(self.reference_raw), 6_610)
        self.assertEqual(
            hashlib.sha256(self.reference_raw).hexdigest(),
            "b5e7348b8bd4b186586d9397b24a3f50ae3a7e83d1605a079276db444ae484b9",
        )
        allowed_mapping_keys = {
            "": {
                "assembly", "auxiliary_animation", "bundle_id",
                "canonical_rom", "decoder_dependency", "descriptor_family",
                "eligibility", "evidence", "graphics", "intent",
                "next_gate", "nonclaims", "palette", "preservation",
                "primary_animation", "private_outputs", "schema_version",
                "source_descriptor", "status",
            },
            "descriptor_family": {
                "palette_only_variant", "same_geometry_npc_ids",
                "table_file_offset", "table_sha256", "table_size",
            },
            "descriptor_family.palette_only_variant": {
                "file_offset", "npc_id", "palette_selector",
                "semantic_identity", "sha256", "snes_address",
            },
            "graphics": {
                "compressed_file_offset", "compressed_sha256",
                "compressed_size", "compression", "decoded_sha256",
                "decoded_size", "pointer_entry_snes_address",
                "pointer_snes_address", "selector", "tile_4bpp_count",
            },
            "graphics.compression": {
                "addendum_count", "back_reference_width_bits",
            },
            "private_outputs": {
                TOOL.ASSEMBLY_FILENAME, TOOL.AUX_FILENAME,
                TOOL.GRAPHICS_FILENAME, TOOL.PALETTE_FILENAME,
                TOOL.PRIMARY_FILENAME,
            },
            "source_descriptor": {
                "fields", "file_offset", "npc_id", "sha256",
                "snes_address",
            },
            "source_descriptor.fields": {
                "animation_selector", "assembly_selector",
                "graphics_selector", "palette_selector", "size_class",
            },
        }

        simple_mappings = {
            "assembly", "auxiliary_animation", "canonical_rom",
            "decoder_dependency", "eligibility", "evidence", "intent",
            "palette", "preservation", "primary_animation",
        }
        for path in simple_mappings:
            allowed_mapping_keys[path] = set(self.reference[path])
        for filename in allowed_mapping_keys["private_outputs"]:
            allowed_mapping_keys[f"private_outputs.{filename}"] = {
                "sha256", "size"
            }

        seen_mappings: set[str] = set()

        def walk(value: object, path: str = "") -> None:
            if isinstance(value, dict):
                self.assertIn(path, allowed_mapping_keys)
                self.assertEqual(set(value), allowed_mapping_keys[path])
                seen_mappings.add(path)
                for key, nested in value.items():
                    nested_path = f"{path}.{key}" if path else str(key)
                    walk(nested, nested_path)
            elif isinstance(value, list):
                self.assertIn(
                    path,
                    {
                        "assembly.flag_families",
                        "descriptor_family.same_geometry_npc_ids",
                        "nonclaims",
                    },
                )
                for nested in value:
                    self.assertIsInstance(nested, (str, int))
            else:
                self.assertIsInstance(value, (str, int, bool))
                if isinstance(value, str):
                    self.assertLessEqual(len(value), 256)

        walk(self.reference)
        self.assertEqual(seen_mappings, set(allowed_mapping_keys))

    def test_canonical_rom_rebuild_matches_checked_reference(self) -> None:
        self.require_rom()
        self.assertEqual(self.bundle.report_bytes, self.reference_raw)

    def test_bundle_has_exact_private_artifacts(self) -> None:
        self.require_rom()
        expected = {
            TOOL.GRAPHICS_FILENAME: (
                2_528,
                "69322758b77fff5701cb0d5edb4ca34ab4109c2313ececd37bc018106fe84b73",
            ),
            TOOL.ASSEMBLY_FILENAME: (
                920,
                "ed6ad15d16d60b2135d1af3bc6fb10de283dcda744d06da33ea37699373d2314",
            ),
            TOOL.PRIMARY_FILENAME: (
                144,
                "9331925cce8129be325dfe52107bbdf9721fc642db1d9f7216f9017f810cd4ff",
            ),
            TOOL.AUX_FILENAME: (
                36,
                "58d697a461a3674556a92d05e2b26df3c37badcd0068edc54f95e2b394e2052d",
            ),
            TOOL.PALETTE_FILENAME: (
                24,
                "8d5953b31b0ca6624d94c0c29935d34519418bc04f9e780fc466dca0c0c9ef3d",
            ),
        }
        for filename, (size, digest) in expected.items():
            data = self.bundle.artifacts[filename]
            self.assertEqual(len(data), size, filename)
            self.assertEqual(TOOL.sha256(data), digest, filename)
        self.assertEqual(
            self.bundle.artifacts[TOOL.MANIFEST_FILENAME],
            self.reference_raw,
        )

    def test_native_packet_geometry_is_exact(self) -> None:
        assembly = self.reference["assembly"]
        graphics = self.reference["graphics"]
        animation = self.reference["primary_animation"]
        palette = self.reference["palette"]
        self.assertEqual(graphics["tile_4bpp_count"], 79)
        self.assertEqual(assembly["record_count"], 23)
        self.assertEqual(assembly["record_size"], 0x28)
        self.assertEqual(assembly["distinct_tile_indexes"], 79)
        self.assertEqual(assembly["minimum_tile_index"], 0)
        self.assertEqual(assembly["maximum_tile_index"], 78)
        self.assertEqual(
            assembly["flag_families"],
            ["$0000", "$4000-horizontal-flip"],
        )
        self.assertEqual(animation["facing_count"], 4)
        self.assertEqual(animation["bytes_per_facing"], 36)
        self.assertEqual(animation["entrypoints_per_facing"], 9)
        self.assertEqual(animation["referenced_frame_count"], 23)
        self.assertEqual(animation["referenced_frame_maximum"], 22)
        self.assertEqual(palette["custom_color_count"], 12)

    def test_preservation_flags_remain_false(self) -> None:
        self.assertTrue(
            all(value is False for value in self.reference["preservation"].values())
        )
        self.assertFalse(
            self.reference["eligibility"]["production_rom_install"]
        )
        self.assertFalse(self.reference["eligibility"]["public_patch"])
        self.assertFalse(
            self.reference["eligibility"]["logical_pc_07_runtime"]
        )

    def test_corrupted_rom_fails_closed_before_bundle_exists(self) -> None:
        self.require_rom()
        corrupted = bytearray(self.rom)
        corrupted[0] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.CompatibilityBuildError, "canonical ROM SHA-1 gate failed"
        ):
            TOOL.build_bundle(bytes(corrupted))

    def test_output_guard_rejects_nonprivate_path(self) -> None:
        with self.assertRaisesRegex(
            TOOL.CompatibilityBuildError, "must remain below workspace private"
        ):
            TOOL.validate_private_output_dir(ROOT / "output" / "compat")

    def test_private_write_is_idempotent_and_refuses_conflicts(self) -> None:
        self.require_rom()
        TOOL.PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=TOOL.PRIVATE_ROOT, prefix="compat-test-"
        ) as temporary:
            output_dir = pathlib.Path(temporary) / "bundle"
            resolved = TOOL.write_bundle(self.bundle, output_dir)
            self.assertTrue(resolved.is_relative_to(TOOL.PRIVATE_ROOT))
            TOOL.write_bundle(self.bundle, output_dir)
            for filename, expected in self.bundle.artifacts.items():
                self.assertEqual((output_dir / filename).read_bytes(), expected)

            conflict = output_dir / TOOL.GRAPHICS_FILENAME
            conflict.write_bytes(b"different")
            with self.assertRaisesRegex(
                TOOL.CompatibilityBuildError,
                "refusing to overwrite a different existing artifact",
            ):
                TOOL.write_bundle(self.bundle, output_dir)
            self.assertEqual(conflict.read_bytes(), b"different")

    def test_descriptor_family_is_independently_pinned(self) -> None:
        self.require_rom()
        primary, variant = TOOL._read_descriptor_family(self.rom)
        self.assertEqual(primary, TOOL.NPC_DESCRIPTOR)
        self.assertEqual(variant, TOOL.PALETTE_VARIANT_DESCRIPTOR)
        mutated = bytearray(self.rom)
        mutated[TOOL.PALETTE_VARIANT_DESCRIPTOR_FILE] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.CompatibilityBuildError, "NPC descriptor table SHA-256 drifted"
        ):
            TOOL._read_descriptor_family(bytes(mutated))

    def test_existing_artifact_reparse_is_rejected_before_read(self) -> None:
        self.require_rom()
        with tempfile.TemporaryDirectory(
            dir=TOOL.PRIVATE_ROOT, prefix="compat-reparse-test-"
        ) as temporary:
            output_dir = pathlib.Path(temporary) / "bundle"
            TOOL.write_bundle(self.bundle, output_dir)
            guarded = output_dir / TOOL.GRAPHICS_FILENAME
            real_is_reparse = TOOL._is_reparse

            def fake_is_reparse(path: pathlib.Path) -> bool:
                return pathlib.Path(path) == guarded or real_is_reparse(path)

            with mock.patch.object(
                TOOL, "_is_reparse", side_effect=fake_is_reparse
            ):
                with self.assertRaisesRegex(
                    TOOL.CompatibilityBuildError, "reparse point"
                ):
                    TOOL.write_bundle(self.bundle, output_dir)

    def test_staging_failure_leaves_no_partial_promoted_bundle(self) -> None:
        self.require_rom()
        with tempfile.TemporaryDirectory(
            dir=TOOL.PRIVATE_ROOT, prefix="compat-stage-test-"
        ) as temporary:
            parent = pathlib.Path(temporary)
            output_dir = parent / "bundle"
            real_writer = TOOL._write_exclusive_file
            calls = 0

            def failing_writer(path: pathlib.Path, data: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("injected staging failure")
                real_writer(path, data)

            with mock.patch.object(
                TOOL, "_write_exclusive_file", side_effect=failing_writer
            ):
                with self.assertRaisesRegex(OSError, "injected staging failure"):
                    TOOL.write_bundle(self.bundle, output_dir)
            self.assertFalse(os.path.lexists(output_dir))
            self.assertEqual(
                [path for path in parent.iterdir() if ".staging-" in path.name],
                [],
            )

    def test_metadata_only_cli_is_byte_exact_and_does_not_use_output(self) -> None:
        self.require_rom()
        completed = subprocess.run(
            [
                sys.executable,
                str(TOOL_PATH),
                "--rom",
                str(TOOL.DEFAULT_ROM),
                "--output-dir",
                str(ROOT / "outside-is-ignored-in-metadata-mode"),
                "--metadata-only",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        self.assertEqual(completed.stdout, self.reference_raw)
        self.assertEqual(completed.stderr, b"")
        self.assertFalse((ROOT / "outside-is-ignored-in-metadata-mode").exists())


if __name__ == "__main__":
    unittest.main()
