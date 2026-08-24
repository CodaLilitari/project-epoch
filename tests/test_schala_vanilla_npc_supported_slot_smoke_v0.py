from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = (
    TOOLS_DIR / "build_schala_vanilla_npc_supported_slot_smoke_v0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "build_schala_vanilla_npc_supported_slot_smoke_v0",
    TOOL_PATH,
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaVanillaNpcSupportedSlotSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TOOL.DEFAULT_ROM.is_file():
            raise unittest.SkipTest("canonical private ROM is not available")
        cls.source = TOOL.DEFAULT_ROM.read_bytes()
        cls.output, cls.report = TOOL.build_diagnostic(cls.source)
        cls.provider_artifacts = TOOL._provider_assets(cls.source)

    def test_canonical_rom_and_all_replaced_preimages_are_pinned(self) -> None:
        TOOL.validate_input(self.source)
        self.assertEqual(TOOL.sha256(self.source), TOOL.EXPECTED_ROM_SHA256)
        bad = bytearray(self.source)
        bad[0] ^= 1
        with self.assertRaisesRegex(TOOL.SmokeBuildError, "SHA-256"):
            TOOL.validate_input(bytes(bad))

    def test_provider_is_rebuilt_from_the_canonical_rom_in_memory(self) -> None:
        provider = TOOL.provider
        graphics = self.provider_artifacts[provider.GRAPHICS_FILENAME]
        assembly = self.provider_artifacts[provider.ASSEMBLY_FILENAME]
        palette = self.provider_artifacts[provider.PALETTE_FILENAME]
        self.assertEqual(len(graphics), provider.GFX_DECOMPRESSED_SIZE)
        self.assertEqual(TOOL.sha256(graphics), provider.GFX_DECOMPRESSED_SHA256)
        self.assertEqual(len(assembly), provider.ASSEMBLY_SIZE)
        self.assertEqual(TOOL.sha256(assembly), provider.ASSEMBLY_SHA256)
        self.assertEqual(len(palette), TOOL.LUCCA_PALETTE_SIZE)
        self.assertEqual(TOOL.sha256(palette), provider.PALETTE_SHA256)
        self.assertTrue(
            self.report["provider"]["derived_in_memory_from_canonical_rom"]
        )

    def test_full_provider_graphics_assembly_and_palette_are_installed(self) -> None:
        provider = TOOL.provider
        graphics = self.provider_artifacts[provider.GRAPHICS_FILENAME]
        assembly = self.provider_artifacts[provider.ASSEMBLY_FILENAME]
        palette = self.provider_artifacts[provider.PALETTE_FILENAME]
        self.assertEqual(
            self.output[
                TOOL.LUCCA_GRAPHICS_START : TOOL.LUCCA_GRAPHICS_START
                + len(graphics)
            ],
            graphics,
        )
        self.assertEqual(
            self.output[
                TOOL.LUCCA_ASSEMBLY_START : TOOL.LUCCA_ASSEMBLY_START
                + len(assembly)
            ],
            assembly,
        )
        self.assertEqual(
            self.output[
                TOOL.LUCCA_PALETTE_START : TOOL.LUCCA_PALETTE_START
                + TOOL.LUCCA_PALETTE_SIZE
            ],
            palette,
        )

    def test_source_entries_are_exact_and_high_selectors_use_entry_zero(
        self,
    ) -> None:
        provider = TOOL.provider
        provider_primary = self.provider_artifacts[provider.PRIMARY_FILENAME]
        provider_aux = self.provider_artifacts[provider.AUX_FILENAME]
        primary = self.output[TOOL.LUCCA_PRIMARY_START : TOOL.LUCCA_PRIMARY_END]
        auxiliary = self.output[TOOL.LUCCA_AUX_START : TOOL.LUCCA_AUX_END]
        self.assertEqual(len(primary), TOOL.FACING_COUNT * TOOL.LUCCA_FACING_SIZE)
        self.assertEqual(len(auxiliary), TOOL.LUCCA_FACING_SIZE)
        self.assertEqual(
            auxiliary[: provider.PRIMARY_FACING_SIZE],
            provider_aux,
        )
        for facing in range(TOOL.FACING_COUNT):
            source_start = facing * provider.PRIMARY_FACING_SIZE
            destination_start = facing * TOOL.LUCCA_FACING_SIZE
            self.assertEqual(
                primary[
                    destination_start :
                    destination_start + provider.PRIMARY_FACING_SIZE
                ],
                provider_primary[
                    source_start : source_start + provider.PRIMARY_FACING_SIZE
                ],
            )

        for selector in range(
            TOOL.SOURCE_ENTRYPOINT_COUNT,
            TOOL.MAPPED_ENTRYPOINT_COUNT,
        ):
            offset = selector * TOOL.ENTRYPOINT_STRIDE
            self.assertEqual(
                auxiliary[offset : offset + TOOL.ENTRYPOINT_STRIDE],
                provider_aux[: TOOL.ENTRYPOINT_STRIDE],
            )
            for facing in range(TOOL.FACING_COUNT):
                source_start = facing * provider.PRIMARY_FACING_SIZE
                base = facing * TOOL.LUCCA_FACING_SIZE + offset
                self.assertEqual(
                    primary[base : base + TOOL.ENTRYPOINT_STRIDE],
                    provider_primary[
                        source_start : source_start + TOOL.ENTRYPOINT_STRIDE
                    ],
                )

    def test_provider_numeric_entrypoints_remain_semantically_unbound(self) -> None:
        contract = self.report["fallback_contract"]
        self.assertEqual(
            contract["source_entrypoint_cells_copied"],
            list(range(TOOL.SOURCE_ENTRYPOINT_COUNT)),
        )
        self.assertFalse(contract["source_entrypoint_semantics_claimed"])
        self.assertTrue(contract["diagnostic_numeric_equivalence_only"])
        self.assertEqual(contract["fallback_source_entrypoint"], 0)
        self.assertEqual(
            contract["fallback_selector_minimum"],
            TOOL.SOURCE_ENTRYPOINT_COUNT,
        )
        self.assertEqual(contract["mapped_selector_minimum"], 0)
        self.assertEqual(
            contract["mapped_selector_maximum"], TOOL.MAPPED_ENTRYPOINT_MAX
        )
        self.assertEqual(
            contract["mapped_selector_count"], TOOL.MAPPED_ENTRYPOINT_COUNT
        )
        self.assertTrue(contract["source_facing_block_order_preserved"])
        self.assertFalse(contract["human_direction_names_claimed"])
        self.assertFalse(contract["complete_animation_semantics_claimed"])

    def test_only_declared_lucca_ranges_and_checksum_change(self) -> None:
        provider = TOOL.provider
        graphics_size = len(
            self.provider_artifacts[provider.GRAPHICS_FILENAME]
        )
        assembly_size = len(
            self.provider_artifacts[provider.ASSEMBLY_FILENAME]
        )
        allowed = (
            (
                TOOL.LUCCA_GRAPHICS_START,
                TOOL.LUCCA_GRAPHICS_START + graphics_size,
            ),
            (
                TOOL.LUCCA_ASSEMBLY_START,
                TOOL.LUCCA_ASSEMBLY_START + assembly_size,
            ),
            (TOOL.LUCCA_PRIMARY_START, TOOL.LUCCA_PRIMARY_END),
            (TOOL.LUCCA_AUX_START, TOOL.LUCCA_AUX_END),
            (
                TOOL.LUCCA_PALETTE_START,
                TOOL.LUCCA_PALETTE_START + TOOL.LUCCA_PALETTE_SIZE,
            ),
            (TOOL.HEADER_COMPLEMENT, TOOL.HEADER_CHECKSUM + 2),
        )
        for index, (before, after) in enumerate(zip(self.source, self.output)):
            if before == after:
                continue
            self.assertTrue(
                any(start <= index < end for start, end in allowed),
                f"unexpected ROM change at 0x{index:X}",
            )
        TOOL.validate_output_checksum(self.output)
        self.assertEqual(
            TOOL.sha256(self.output),
            TOOL.EXPECTED_OUTPUT_SHA256,
        )

        npc_table_start = TOOL.provider.NPC_DESCRIPTOR_TABLE_FILE
        npc_table_end = npc_table_start + TOOL.provider.NPC_DESCRIPTOR_TABLE_SIZE
        self.assertEqual(
            self.output[npc_table_start:npc_table_end],
            self.source[npc_table_start:npc_table_end],
        )

    def test_manifest_never_claims_pc7_or_production_readiness(self) -> None:
        self.assertEqual(self.report["supported_logical_id"], 2)
        self.assertEqual(self.report["source_npc_id"], 9)
        self.assertEqual(self.report["artifact_class"], "private-diagnostic-only")
        self.assertEqual(self.report["evidence_level"], "verified-static")
        reproduction = self.report["reproduction"]
        self.assertIn("--rom <canonical-private-rom.sfc>", reproduction["command_template"])
        self.assertIn("--output <ignored-private-output.sfc>", reproduction["command_template"])
        self.assertGreaterEqual(len(reproduction["steps"]), 4)
        self.assertEqual(
            reproduction["required_source_sha256"],
            TOOL.EXPECTED_ROM_SHA256,
        )
        self.assertEqual(
            reproduction["expected_output_sha256"],
            TOOL.EXPECTED_OUTPUT_SHA256,
        )
        self.assertNotRegex(reproduction["command_template"], r"[A-Za-z]:\\")
        policy = self.report["write_policy"]
        self.assertTrue(policy["overwrites_existing_vanilla_data"])
        self.assertEqual(policy["replaced_owner"], "Lucca")
        self.assertTrue(policy["exact_canonical_preimage_required"])
        self.assertTrue(policy["production_use_forbidden"])
        self.assertFalse(policy["epoch_data_changed"])
        self.assertFalse(policy["source_npc_09_data_changed"])
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
            TOOL._require_distinct_input_output(TOOL.DEFAULT_ROM, TOOL.DEFAULT_ROM)

    def test_output_guard_refuses_to_replace_a_different_rom(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="schala-provider-output-guard-",
            dir=TOOL.PRIVATE_ROOT,
        ) as temporary:
            output = pathlib.Path(temporary) / "diagnostic.sfc"
            original = b"not the diagnostic ROM"
            output.write_bytes(original)
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

    def test_output_guard_refuses_to_replace_a_different_manifest(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="schala-provider-manifest-guard-",
            dir=TOOL.PRIVATE_ROOT,
        ) as temporary:
            output = pathlib.Path(temporary) / "diagnostic.sfc"
            manifest = output.with_suffix(".manifest.json")
            output.write_bytes(self.output)
            original_manifest = b"not the diagnostic manifest\n"
            manifest.write_bytes(original_manifest)

            with self.assertRaisesRegex(
                TOOL.SmokeBuildError,
                "different existing diagnostic manifest",
            ):
                TOOL.write_outputs(
                    self.source,
                    self.output,
                    self.report,
                    output,
                )

            self.assertEqual(output.read_bytes(), self.output)
            self.assertEqual(manifest.read_bytes(), original_manifest)

    def test_project_write_guard_covers_the_complete_diagnostic_diff(self) -> None:
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
                "private/test_runs/"
                "schala_vanilla_npc_supported_slot_smoke_v0/"
                "schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.sfc"
            ),
        )

        tampered = bytearray(self.output)
        first = next(
            index
            for index in range(0x100, 0x1000)
            if tampered[index] != tampered[index + 1]
        )
        tampered[first], tampered[first + 1] = (
            tampered[first + 1],
            tampered[first],
        )
        tampered_intents = copy.deepcopy(intents)
        tampered_intents["target_sha256"] = TOOL.sha256(bytes(tampered))
        with self.assertRaisesRegex(
            TOOL.write_guard.WriteIntentError,
            "undeclared changed byte",
        ):
            TOOL.write_guard.audit_images(
                tampered_intents,
                self.source,
                bytes(tampered),
            )


if __name__ == "__main__":
    unittest.main()
