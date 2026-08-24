from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
SPEC_PATH = (
    ROOT
    / "references"
    / "current_schala_vanilla_npc_supported_slot_accepted_artifacts_v1.json"
)
GENERIC_LOADER_PATH = ROOT / "tools" / "build_current_emulator_evidence_manifest.py"
FORBIDDEN_SUFFIXES = {".sfc", ".smc", ".srm", ".sav", ".mss"}
EXPECTED_LOGS = {
    "clean_motion_r2.log",
    "clean_repeat2.log",
    "provider_motion.log",
    "provider_repeat2.log",
}
EXPECTED_VIDEOS = {
    "clean_motion_r2.mkv",
    "clean_repeat2.mkv",
    "provider_motion.mkv",
    "provider_repeat2.mkv",
}
EXPECTED_STATES = {
    "states/clean_control_run.state.auto",
    "states/clean_repeat2.state.auto",
    "states/provider_repeat2.state.auto",
    "states/schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.state.auto",
}
EXPECTED_MOTION_FRAMES = {
    f"frames/{variant}_{frame}.png"
    for variant in ("clean", "provider")
    for frame in (710, 830, 950, 1070, 1190, 1590)
}
EXPECTED_CONTROL_FRAMES = {
    "frames/clean_100.png",
    "frames/provider_100.png",
}
EXPECTED_REPEAT_FRAMES = {
    "frames/clean_repeat2_1590.png",
    "frames/provider_repeat2_1590.png",
}
EXPECTED_BSVS = {"clean_motion.bsv", "provider_motion.bsv"}


def load_tool_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MOVIE = load_tool_module(
    "edit_retroarch_bsv2_inputs_for_schala_acceptance",
    TOOLS_DIR / "edit_retroarch_bsv2_inputs.py",
)
INSPECTOR = load_tool_module(
    "inspect_current_wram_candidate_for_schala_acceptance",
    TOOLS_DIR / "inspect_current_wram_candidate.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_generic_loader():
    spec = importlib.util.spec_from_file_location(
        "current_emulator_evidence_manifest_for_schala_acceptance_test",
        GENERIC_LOADER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {GENERIC_LOADER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CurrentSchalaVanillaNpcSupportedSlotAcceptedArtifactsV1Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        cls.rows = cls.spec["artifacts"]
        cls.by_path = {row["path"]: row for row in cls.rows}

    def test_generic_acceptance_schema_and_loader_compatibility(self) -> None:
        self.assertEqual(
            self.spec["schema"],
            "project-epoch-emulator-acceptance-v1",
        )
        loader = load_generic_loader()
        acceptance_sha256, accepted = loader.load_acceptance_spec(SPEC_PATH)
        self.assertEqual(acceptance_sha256, sha256_file(SPEC_PATH))
        self.assertEqual(
            [row["path"] for row in accepted],
            [row["path"] for row in self.rows],
        )
        self.assertTrue(
            all(
                set(row) == {
                    "path",
                    "evidence_level",
                    "reproduction_group",
                }
                for row in accepted
            )
        )

    def test_build_and_private_manifest_binding(self) -> None:
        binding = self.spec["build_binding"]
        canonical = binding["canonical_rom"]
        diagnostic = binding["runtime_diagnostic_rom"]
        self.assertEqual(canonical["size"], 0x400000)
        self.assertEqual(
            canonical["sha256"],
            "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9",
        )
        self.assertEqual(diagnostic["size"], 0x400000)
        self.assertEqual(
            diagnostic["sha256"],
            "75dc966ce377accf19ce1a7eb2ac200d5f68fbb94b9436eee7f09e613cc4ad42",
        )

        hardened = binding["hardened_reproduction"]
        source_pins = (
            {
                "path": hardened["builder_path"],
                "size": hardened["builder_size"],
                "sha256": hardened["builder_sha256"],
            },
            binding["provider_builder"],
            binding["write_guard"],
        )
        for row in source_pins:
            path = ROOT / Path(row["path"])
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(path.stat().st_size, row["size"], str(path))
            self.assertEqual(sha256_file(path), row["sha256"], str(path))
        self.assertEqual(hardened["builder_version"], "0.2.2")
        self.assertEqual(
            hardened["reproduced_rom_sha256"], diagnostic["sha256"]
        )

        private_run_root = (
            ROOT
            / "private"
            / "test_runs"
            / "schala_vanilla_npc_supported_slot_smoke_v0"
        )
        if not private_run_root.exists():
            return

        receipts = (
            binding["runtime_build_receipt"],
            hardened,
        )
        decoded: list[dict[str, object]] = []
        for row in receipts:
            path = ROOT / Path(row["private_manifest_path"])
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(path.stat().st_size, row["private_manifest_size"])
            self.assertEqual(
                sha256_file(path), row["private_manifest_sha256"], str(path)
            )
            decoded.append(json.loads(path.read_text(encoding="utf-8")))

        runtime_manifest, hardened_manifest = decoded
        runtime_receipt = binding["runtime_build_receipt"]
        self.assertEqual(
            runtime_manifest["builder_version"],
            runtime_receipt["builder_version"],
        )
        self.assertEqual(
            runtime_manifest["builder_sha256"],
            runtime_receipt["builder_sha256"],
        )
        self.assertEqual(
            runtime_manifest["output_rom_sha256"], diagnostic["sha256"]
        )

        self.assertEqual(
            hardened_manifest["builder_version"], hardened["builder_version"]
        )
        self.assertEqual(
            hardened_manifest["builder_sha256"], hardened["builder_sha256"]
        )
        self.assertEqual(hardened_manifest["evidence_level"], "verified-static")
        self.assertGreaterEqual(len(hardened_manifest["reproduction"]["steps"]), 4)
        self.assertEqual(
            hardened_manifest["output_rom_sha256"], diagnostic["sha256"]
        )
        audit = hardened_manifest["write_intent_audit"]
        self.assertEqual(audit["status"], hardened["guard_status"])
        self.assertEqual(
            audit["complete_diff_coverage"], hardened["complete_diff_coverage"]
        )
        self.assertEqual(
            audit["preimages_verified"], hardened["preimages_verified"]
        )
        self.assertEqual(audit["changed_byte_count"], hardened["changed_byte_count"])
        self.assertEqual(audit["total_declared_bytes"], hardened["declared_byte_count"])
        self.assertEqual(audit["write_count"], hardened["write_count"])
        self.assertEqual(
            audit["production_allocations_currently_approved"],
            hardened["production_allocations"],
        )
        self.assertEqual(
            audit["production_hooks_currently_approved"],
            hardened["production_hooks"],
        )

    def test_movies_bind_content_identity_and_executed_window(self) -> None:
        bindings = self.spec["movie_bindings"]
        self.assertEqual(
            [row["path"] for row in bindings],
            ["clean_motion.bsv", "provider_motion.bsv"],
        )
        build = self.spec["build_binding"]
        expected_roms = {
            "clean_motion.bsv": build["canonical_rom"]["sha256"],
            "provider_motion.bsv": build["runtime_diagnostic_rom"]["sha256"],
        }
        artifact_root = ROOT / Path(self.spec["artifact_root"])
        if not artifact_root.exists():
            return
        for row in bindings:
            self.assertEqual(row["bound_rom_sha256"], expected_roms[row["path"]])
            source = (artifact_root / row["path"]).read_bytes()
            info = MOVIE.parse_movie(source)
            self.assertEqual(f"{info.content_crc32:08X}", row["content_crc32"])
            self.assertEqual(info.identifier, row["identifier"])
            self.assertEqual(info.frame_count, row["recorded_frame_count"])
            self.assertEqual(row["executed_frame_count"], 1600)
            self.assertLessEqual(
                row["executed_frame_count"], row["recorded_frame_count"]
            )

    def test_endpoint_states_match_decoded_witness_contract(self) -> None:
        contract = self.spec["state_witness_contract"]
        self.assertEqual(
            {row["path"] for row in contract["states"]}, EXPECTED_STATES
        )
        artifact_root = ROOT / Path(self.spec["artifact_root"])
        if not artifact_root.exists():
            return

        sram_row = contract["sram_reference"]
        sram_path = ROOT / Path(sram_row["path"])
        self.assertTrue(sram_path.is_file(), str(sram_path))
        self.assertEqual(sram_path.stat().st_size, sram_row["size"])
        self.assertEqual(sha256_file(sram_path), sram_row["sha256"])
        sram = sram_path.read_bytes()
        expected = contract["expected"]

        for state_row in contract["states"]:
            state_path = artifact_root / state_row["path"]
            inspection = INSPECTOR.inspect_candidate(
                state_path.read_bytes(),
                sram,
                save_slot=contract["save_slot"],
            )
            self.assertEqual(
                inspection["wram_anchor_method"],
                expected["wram_anchor_method"],
            )
            self.assertEqual(
                inspection["core_state_length"], expected["core_state_length"]
            )
            self.assertEqual(
                inspection["core_state_sha256"], state_row["core_state_sha256"]
            )
            self.assertEqual(
                inspection["target_state_offset"], expected["target_state_offset"]
            )
            self.assertEqual(inspection["target_length"], expected["target_length"])
            self.assertEqual(
                inspection["expected_canary_sha256"], expected["canary_sha256"]
            )
            self.assertEqual(
                inspection["actual_target_sha256"], expected["canary_sha256"]
            )
            self.assertTrue(inspection["canary_matches"])
            self.assertTrue(inspection["candidate_invariants_ok"])
            self.assertEqual(
                inspection["canary_occurrences"], expected["canary_occurrences"]
            )
            self.assertEqual(
                inspection["front_guard_hex"], expected["front_guard_hex"]
            )
            self.assertEqual(
                inspection["rear_guard_hex"], expected["rear_guard_hex"]
            )
            self.assertEqual(
                inspection["pc07_record_2830_287f_sha256"],
                expected["compatibility_block_sha256"],
            )
            self.assertEqual(
                inspection["saved_slot_record_0430_047f_sha256"],
                expected["compatibility_block_sha256"],
            )
            self.assertEqual(
                inspection["pc07_record_matches_saved_slot"],
                expected["compatibility_matches_saved_slot"],
            )
            self.assertEqual(
                inspection["active_party_2980_2982_hex"],
                expected["active_party_hex"],
            )
            self.assertEqual(
                inspection["roster_2980_2988_hex"], expected["roster_hex"]
            )
            self.assertEqual(
                inspection["joined_flags_29af"], expected["joined_flags"]
            )
            self.assertEqual(
                inspection["epoch_name_2c4d_2c52_hex"],
                expected["epoch_name_hex"],
            )
            self.assertEqual(
                inspection["location_id_0100"], expected["location_id"]
            )
            self.assertEqual(
                inspection["explore_mode_011f"], expected["explore_mode"]
            )

    def test_curated_allowlist_is_exact_sorted_and_metadata_only(self) -> None:
        expected = (
            EXPECTED_LOGS
            | EXPECTED_VIDEOS
            | EXPECTED_STATES
            | EXPECTED_MOTION_FRAMES
            | EXPECTED_CONTROL_FRAMES
            | EXPECTED_REPEAT_FRAMES
            | EXPECTED_BSVS
        )
        paths = [row["path"] for row in self.rows]
        self.assertEqual(len(paths), 30)
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(set(paths), expected)
        self.assertEqual(len(paths), len(set(paths)))

        for row in self.rows:
            relative = PurePosixPath(row["path"])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            self.assertEqual(relative.as_posix(), row["path"])
            self.assertNotIn(relative.suffix.lower(), FORBIDDEN_SUFFIXES)
            self.assertIsInstance(row["size"], int)
            self.assertGreater(row["size"], 0)
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(row["evidence_level"], "verified-runtime")
            self.assertEqual(
                row["reproduction_group"],
                "edit-replay" if relative.suffix == ".bsv" else "play-replay",
            )

        serialized = SPEC_PATH.read_text(encoding="utf-8").lower()
        self.assertNotIn('"path": "clean_motion.log"', serialized)
        self.assertNotIn('"path": "clean_motion.mkv"', serialized)
        self.assertNotIn('"path": "title_', serialized)
        self.assertNotIn('"path": "raw_', serialized)

    def test_scope_and_replay_relationships_are_fail_closed(self) -> None:
        scope = self.spec["acceptance_scope"]
        self.assertEqual(scope["supported_logical_id"], 2)
        self.assertEqual(scope["source_npc_id"], 9)
        self.assertEqual(scope["successful_runs_per_variant"], 2)
        self.assertEqual(
            scope["motion_checkpoint_frames"],
            [710, 830, 950, 1070, 1190, 1590],
        )
        self.assertFalse(scope["logical_pc_07"])
        self.assertFalse(scope["production_input"])

        self.assertEqual(
            self.by_path["frames/provider_100.png"]["sha256"],
            self.by_path["frames/clean_100.png"]["sha256"],
        )
        for variant in ("provider", "clean"):
            self.assertEqual(
                self.by_path[f"frames/{variant}_1590.png"]["sha256"],
                self.by_path[f"frames/{variant}_repeat2_1590.png"]["sha256"],
            )
        self.assertEqual(
            self.by_path[
                "states/schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.state.auto"
            ]["sha256"],
            self.by_path["states/provider_repeat2.state.auto"]["sha256"],
        )
        self.assertEqual(
            self.by_path["states/clean_control_run.state.auto"]["sha256"],
            self.by_path["states/clean_repeat2.state.auto"]["sha256"],
        )

    def test_private_runtime_and_artifacts_match_when_present(self) -> None:
        # A checkout without private evidence can still validate the public
        # allowlist. If the private root is present, every pin is mandatory:
        # no per-file skips and no partial evidence set are accepted.
        artifact_root = ROOT / Path(self.spec["artifact_root"])
        if not artifact_root.exists():
            return
        self.assertTrue(artifact_root.is_dir())

        for row in self.rows:
            path = artifact_root / Path(*PurePosixPath(row["path"]).parts)
            self.assertTrue(path.is_file(), f"missing accepted artifact: {path}")
            self.assertEqual(path.stat().st_size, row["size"], str(path))
            self.assertEqual(sha256_file(path), row["sha256"], str(path))

        for key in ("frontend", "core"):
            row = self.spec["runtime"][key]
            path = ROOT / Path(row["path"])
            self.assertTrue(path.is_file(), f"missing pinned runtime: {path}")
            self.assertEqual(path.stat().st_size, row["size"])
            self.assertEqual(sha256_file(path), row["sha256"])

    def test_accepted_logs_prove_success_markers_and_exclude_errors(self) -> None:
        artifact_root = ROOT / Path(self.spec["artifact_root"])
        if not artifact_root.exists():
            return
        self.assertEqual(
            set(self.spec["observations"]["accepted_run_logs"]),
            EXPECTED_LOGS,
        )
        core_path = self.spec["runtime"]["core"]["path"]
        allowed_audio_errors = {
            "[ERROR] Failed to initialize audio driver. Will continue without audio.",
            "[ERROR] failed_to_start_audio_driver",
        }
        for relative in EXPECTED_LOGS:
            text = (artifact_root / relative).read_text(
                encoding="utf-8", errors="strict"
            )
            self.assertIn(f'Loading dynamic libretro core from: "{core_path}"', text)
            self.assertIn("[Replay] Starting movie playback.", text)
            self.assertIn("[Replay] Input replay movie playback ended.", text)
            errors = {
                line for line in text.splitlines() if line.startswith("[ERROR]")
            }
            self.assertTrue(errors)
            self.assertEqual(errors, allowed_audio_errors)
            self.assertNotIn("Failed to deserialize checkpoint", text)
            self.assertNotIn("Failed to load movie file", text)
            self.assertIn("Geometry: 256x224", text)
            self.assertIn("FPS: 60.10", text)
            self.assertIn("Sample rate: 48000.00 Hz", text)


if __name__ == "__main__":
    unittest.main()
