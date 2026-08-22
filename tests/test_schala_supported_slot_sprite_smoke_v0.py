from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "build_schala_supported_slot_sprite_smoke_v0.py"
SPEC = importlib.util.spec_from_file_location(
    "build_schala_supported_slot_sprite_smoke_v0", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaSupportedSlotSpriteSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = TOOL.DEFAULT_ROM.read_bytes()
        cls.output, cls.report = TOOL.build_diagnostic(cls.source)
        source_raw, source = TOOL.gameplay.load_json(
            TOOL.gameplay.DEFAULT_SOURCE
        )
        cls.packet_outputs = TOOL.packet_builder.build_outputs(
            source_raw, source
        )

    def test_canonical_rom_and_packet_preimages_are_pinned(self) -> None:
        TOOL.validate_input(self.source)
        self.assertEqual(
            TOOL.sha256(self.source), TOOL.EXPECTED_ROM_SHA256
        )
        bad = bytearray(self.source)
        bad[0] ^= 1
        with self.assertRaisesRegex(TOOL.SmokeBuildError, "SHA-256"):
            TOOL.validate_input(bytes(bad))

    def test_graphics_and_four_cardinal_records_are_installed_exactly(
        self,
    ) -> None:
        graphics = self.packet_outputs[TOOL.packet_builder.GRAPHICS_FILENAME]
        assembly = self.packet_outputs[TOOL.packet_builder.ASSEMBLY_FILENAME][
            : 4 * TOOL.packet_builder.FRAME_RECORD_SIZE
        ]
        self.assertEqual(
            self.output[
                TOOL.LUCCA_GRAPHICS_START :
                TOOL.LUCCA_GRAPHICS_START + len(graphics)
            ],
            graphics,
        )
        self.assertEqual(
            self.output[
                TOOL.LUCCA_ASSEMBLY_START :
                TOOL.LUCCA_ASSEMBLY_START + len(assembly)
            ],
            assembly,
        )

    def test_animation_blocks_map_only_non_sentinels_to_cardinal_idles(
        self,
    ) -> None:
        original = self.source[
            TOOL.LUCCA_ANIMATION_START : TOOL.LUCCA_ANIMATION_END
        ]
        actual = self.output[
            TOOL.LUCCA_ANIMATION_START : TOOL.LUCCA_ANIMATION_END
        ]
        for facing, frame_index in enumerate(
            TOOL.CARDINAL_IDLE_FRAME_INDICES
        ):
            start = facing * TOOL.LUCCA_ANIMATION_BLOCK_SIZE
            end = start + TOOL.LUCCA_ANIMATION_BLOCK_SIZE
            for before, after in zip(original[start:end], actual[start:end]):
                self.assertEqual(after, 0xFF if before == 0xFF else frame_index)

    def test_palette_smoke_loads_only_the_vanilla_twelve_color_prefix(
        self,
    ) -> None:
        palette = self.packet_outputs[TOOL.packet_builder.PALETTE_FILENAME]
        self.assertEqual(
            self.output[
                TOOL.LUCCA_PALETTE_START :
                TOOL.LUCCA_PALETTE_START + TOOL.LUCCA_PALETTE_SIZE
            ],
            palette[2:26],
        )
        contract = self.report["palette_contract"]
        self.assertEqual(contract["schala_visible_colors"], 15)
        self.assertEqual(contract["vanilla_custom_colors_loaded"], 12)
        self.assertFalse(contract["indices_13_15_runtime_correct"])

    def test_only_declared_diagnostic_ranges_and_checksum_change(
        self,
    ) -> None:
        allowed = (
            (
                TOOL.LUCCA_GRAPHICS_START,
                TOOL.LUCCA_GRAPHICS_START
                + len(
                    self.packet_outputs[
                        TOOL.packet_builder.GRAPHICS_FILENAME
                    ]
                ),
            ),
            (
                TOOL.LUCCA_ASSEMBLY_START,
                TOOL.LUCCA_ASSEMBLY_START
                + 4 * TOOL.packet_builder.FRAME_RECORD_SIZE,
            ),
            (TOOL.LUCCA_ANIMATION_START, TOOL.LUCCA_ANIMATION_END),
            (
                TOOL.LUCCA_PALETTE_START,
                TOOL.LUCCA_PALETTE_START + TOOL.LUCCA_PALETTE_SIZE,
            ),
            (TOOL.HEADER_COMPLEMENT, TOOL.HEADER_CHECKSUM + 2),
        )
        for index, (before, after) in enumerate(
            zip(self.source, self.output)
        ):
            if before == after:
                continue
            self.assertTrue(
                any(start <= index < end for start, end in allowed),
                f"unexpected ROM change at 0x{index:X}",
            )
        TOOL.validate_output_checksum(self.output)
        self.assertEqual(
            TOOL.sha256(self.output),
            "6c45548175ed77c93eb17e0461dba344669e0af3b3239eab949b63fe1044e355",
        )

    def test_manifest_never_claims_pc7_or_production_readiness(self) -> None:
        self.assertEqual(self.report["supported_logical_id"], 2)
        self.assertEqual(
            self.report["artifact_class"], "private-diagnostic-only"
        )
        policy = self.report["write_policy"]
        self.assertTrue(policy["overwrites_existing_vanilla_data"])
        self.assertEqual(policy["replaced_owner"], "Lucca")
        self.assertTrue(policy["exact_canonical_preimage_required"])
        self.assertTrue(policy["production_use_forbidden"])
        self.assertFalse(policy["epoch_data_changed"])
        self.assertFalse(policy["graphics_source_entries_07_and_08_changed"])
        self.assertFalse(self.report["logical_pc_07"])
        self.assertFalse(self.report["character_record_changed"])
        self.assertFalse(self.report["roster_changed"])
        self.assertFalse(self.report["tech_or_item_data_changed"])
        self.assertFalse(self.report["save_layout_changed"])
        self.assertFalse(self.report["runtime_verified"])
        self.assertFalse(self.report["rom_installable"])
        self.assertFalse(self.report["production_input"])

    def test_output_guard_rejects_nonprivate_or_wrong_suffix(self) -> None:
        with self.assertRaisesRegex(TOOL.SmokeBuildError, "private"):
            TOOL._require_private_output(ROOT / "output" / "smoke.sfc")
        with self.assertRaisesRegex(TOOL.SmokeBuildError, ".sfc"):
            TOOL._require_private_output(
                ROOT / "private" / "test_runs" / "smoke.bin"
            )
        with self.assertRaisesRegex(TOOL.SmokeBuildError, "must differ"):
            TOOL._require_distinct_input_output(
                TOOL.DEFAULT_ROM,
                TOOL.DEFAULT_ROM,
            )

    def test_output_guard_refuses_to_replace_a_different_rom(self) -> None:
        output = (
            ROOT
            / "private"
            / "test_runs"
            / "schala_supported_slot_sprite_smoke_v0"
            / "write_guard_test.sfc"
        )
        manifest = output.with_suffix(".manifest.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        original = b"not the diagnostic ROM"
        output.write_bytes(original)
        try:
            with self.assertRaisesRegex(
                TOOL.SmokeBuildError,
                "refusing to overwrite",
            ):
                TOOL.write_outputs(
                    self.source,
                    self.output,
                    self.report,
                    output,
                )
            self.assertEqual(output.read_bytes(), original)
        finally:
            output.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)

    def test_project_write_guard_covers_the_complete_diagnostic_diff(
        self,
    ) -> None:
        intents = TOOL.build_write_intent_manifest(
            self.source,
            self.output,
            self.report,
            TOOL.DEFAULT_OUTPUT,
        )
        audit = TOOL.write_guard.audit_images(
            intents,
            self.source,
            self.output,
        )
        self.assertEqual(audit["status"], "images-valid")
        self.assertTrue(audit["complete_diff_coverage"])
        self.assertTrue(audit["preimages_verified"])
        self.assertFalse(audit["rom_modified"])
        self.assertEqual(
            intents["output_path"],
            (
                "private/test_runs/schala_supported_slot_sprite_smoke_v0/"
                "schala_lucca_slot_sprite_smoke_v0.sfc"
            ),
        )


if __name__ == "__main__":
    unittest.main()
