from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "run_mesen_wram_ownership_trace.py"
SCENARIO_CONTRACT = (
    ROOT / "references" / "mesen_wram_ownership_scenarios_v1.json"
)
ACCEPTANCE_SPEC = (
    ROOT
    / "references"
    / "mesen_wram_ownership_accepted_artifacts_v1.json"
)


def load_module(name: str, path: Path) -> types.ModuleType:
    source = path.read_bytes()
    code = compile(source, str(path), "exec", dont_inherit=True)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except Exception:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return module


TOOL = load_module("run_mesen_wram_ownership_trace", TOOL_PATH)


class FakeValidator:
    def __init__(self, scenario: str, variant: str) -> None:
        self.scenario = scenario
        self.variant = variant
        self.calls = 0

    def validate_trace_document(
        self,
        value: object,
        *,
        label: str = "trace",
    ) -> tuple[str, str]:
        self.calls += 1
        if not isinstance(value, dict):
            raise AssertionError(f"{label} was not decoded to an object")
        return self.scenario, self.variant


class RunMesenWramOwnershipTraceTests(unittest.TestCase):
    def test_acceptance_spec_pins_sources_and_safe_artifacts(self) -> None:
        spec = json.loads(ACCEPTANCE_SPEC.read_text(encoding="utf-8"))
        self.assertEqual(
            spec["schema"],
            "project-epoch-mesen-wram-ownership-acceptance-v1",
        )
        self.assertEqual(spec["evidence_level"], "verified-runtime")
        source_rows = (
            ("scenario_contract", TOOL.SCENARIO_CONTRACT_PATH),
            ("collector", TOOL.COLLECTOR),
            ("validator", TOOL.VALIDATOR_PATH),
            ("launcher", TOOL_PATH),
        )
        for key, path in source_rows:
            row = spec["sources"][key]
            self.assertEqual(row["path"], path.relative_to(ROOT).as_posix())
            self.assertEqual(row["size"], path.stat().st_size)
            self.assertEqual(row["sha256"], TOOL.sha256_file(path))

        artifact_paths = [row["path"] for row in spec["artifacts"]]
        self.assertEqual(artifact_paths, sorted(artifact_paths))
        self.assertEqual(len(artifact_paths), 16)
        self.assertEqual(len(artifact_paths), len(set(artifact_paths)))
        forbidden = {".sfc", ".smc", ".srm", ".mss", ".state", ".sav"}
        self.assertTrue(
            all(
                Path(path).suffix.lower() not in forbidden
                and "\\" not in path
                and not path.startswith("/")
                and ".." not in Path(path).parts
                for path in artifact_paths
            )
        )
        artifact_contract = {
            (
                row["path"].split("/", 2)[0],
                row["path"].split("/", 2)[1],
                Path(row["path"]).name,
            ): (row["size"], row["sha256"])
            for row in spec["artifacts"]
        }
        for (scenario, variant), outputs in TOOL.EXPECTED_OUTPUTS.items():
            self.assertEqual(
                artifact_contract[(scenario, variant, "trace.json")],
                outputs["trace"],
            )
            self.assertEqual(
                artifact_contract[(scenario, variant, "endpoint.png")],
                outputs["screenshot"],
            )

    def test_scenario_contract_pins_ranges_timelines_and_policies(self) -> None:
        source = SCENARIO_CONTRACT.read_bytes()
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            TOOL.SCENARIO_CONTRACT_SHA256,
        )
        contract = json.loads(source)
        TOOL._validate_scenario_contract(contract)
        self.assertEqual(
            contract["schema"],
            "project-epoch-mesen-wram-ownership-scenarios-v1",
        )
        self.assertEqual(contract["trace_contract"]["trace_count"], 8)
        self.assertEqual(
            contract["acceptance_status"],
            "accepted-exact-artifact-hashes",
        )
        self.assertEqual(
            contract["trace_contract"]["event11c_screenshot_capture_phase"],
            "endFrame-canonical-png-after-route-endpoint-freeze",
        )
        self.assertEqual(
            contract["trace_contract"]["event11c_screenshot_size"],
            9503,
        )
        self.assertEqual(
            contract["trace_contract"]["event11c_screenshot_sha256"],
            (
                "0882eb8e58d053a0e5b2222c9615ab5"
                "a1e4530d8849ddd7388e491803417b7fb"
            ),
        )
        self.assertEqual(
            contract["trace_contract"]["variants"],
            ["zero", "canary"],
        )
        for key, path, expected_size, expected_hash in (
            (
                "collector",
                TOOL.COLLECTOR,
                40088,
                TOOL.COLLECTOR_SHA256,
            ),
            (
                "validator",
                TOOL.VALIDATOR_PATH,
                29388,
                TOOL.VALIDATOR_SHA256,
            ),
        ):
            row = contract["sources"][key]
            self.assertEqual(row["status"], "frozen-exact-source")
            self.assertEqual(row["size"], expected_size)
            self.assertEqual(row["size"], path.stat().st_size)
            self.assertEqual(row["sha256"], expected_hash)
            self.assertEqual(row["sha256"], TOOL.sha256_file(path))
        self.assertIsNone(contract["sources"]["launcher"]["sha256"])
        self.assertEqual(
            [
                (
                    row["name"],
                    row["start"],
                    row["end"],
                    row["length"],
                )
                for row in contract["watched_ranges"]
            ],
            [
                ("old-compatibility", "7E2830", "7E287F", 80),
                ("roster", "7E2980", "7E2988", 9),
                ("joined", "7E29AF", "7E29AF", 1),
                ("epoch-name", "7E2C4D", "7E2C52", 6),
                ("front-guard", "7E2C9C", "7E2C9F", 4),
                ("candidate", "7E2CA0", "7E2CEF", 80),
                ("rear-guard", "7E2CF0", "7E2CFF", 16),
            ],
        )
        scenarios = {
            row["name"]: row for row in contract["scenarios"]
        }
        self.assertEqual(
            scenarios["calibration"]["terminal"],
            {"kind": "exact-relative-frame", "frame": 0},
        )
        self.assertEqual(
            scenarios["field-idle"]["terminal"]["frame"],
            600,
        )
        self.assertEqual(
            scenarios["main-menu"]["terminal"]["frame"],
            600,
        )
        self.assertIn(
            {"frames": "60-61", "player": 1, "input": "x"},
            scenarios["main-menu"]["timeline"],
        )
        self.assertEqual(
            scenarios["event11c-frog"]["terminal"]["minimum_frame"],
            1500,
        )
        self.assertEqual(
            scenarios["event11c-frog"]["terminal"]["maximum_frame"],
            2400,
        )
        for name in TOOL.SCENARIOS:
            policy = scenarios[name]["access_policy"]
            self.assertIn("candidate", policy["zero_access_ranges"])
            self.assertIn(
                "front-guard",
                policy["zero_access_ranges"],
            )
            self.assertIn(
                "rear-guard",
                policy["zero_access_ranges"],
            )
        self.assertEqual(
            scenarios["event11c-frog"]["expected_access_class"],
            "old-compatibility-positive-control",
        )
        for name in ("field-idle", "main-menu"):
            self.assertIn(
                "old-compatibility",
                scenarios[name]["access_policy"][
                    "write_forbidden_ranges"
                ],
            )
        self.assertEqual(
            [
                (row["access"], row["address"])
                for row in scenarios["event11c-frog"]["access_policy"][
                    "required_old_block_filtered_subsequence"
                ]
            ],
            [
                ("write", "7E2834"),
                ("read", "7E283B"),
                ("write", "7E283B"),
            ],
        )
        event_policy = scenarios["event11c-frog"]["access_policy"]
        self.assertEqual(
            event_policy["other_old_compatibility_reads"],
            "measured-and-pair-identical",
        )
        self.assertEqual(
            event_policy["allowed_old_compatibility_writes"],
            [
                "the two required event-control writes",
                (
                    "other observed unmodified-game writes only when they "
                    "are same-value and the complete zero/canary callback "
                    "streams are identical"
                ),
            ],
        )
        self.assertEqual(
            event_policy["other_old_compatibility_writes"],
            "same-value-no-net-change-and-pair-identical",
        )
        self.assertEqual(
            contract["variant_preparation"]["scope"],
            [
                {
                    "range": "candidate",
                    "start": "7E2CA0",
                    "end": "7E2CEF",
                    "length": 80,
                }
            ],
        )
        preparation = contract["preparation_contract"]
        self.assertTrue(preparation["completed_before_counters_armed"])
        self.assertTrue(preparation["counters_zero_after_preparation"])
        self.assertEqual(preparation["active_party_writes"], [])
        self.assertEqual(preparation["old_block_variant_writes"], [])
        self.assertEqual(
            [
                (
                    row["seq"],
                    row["width"],
                    row["raw_wram_offset"],
                    row["value"],
                    row["label"],
                )
                for row in preparation[
                    "event11c_frog_writes_before_candidate_variant"
                ]
            ],
            [
                (0, 1, 0x10000, 0x4C, "storyline"),
                (1, 1, 0x1021C, 0x03, "lap-scratch"),
                (2, 1, 0x101E0, 0x47, "magic-flags"),
                (3, 1, 0x101E2, 0x00, "robo-flags"),
                (4, 1, 0x2834, 0x00, "frog-tech-count"),
                (5, 1, 0x283B, 0x1F, "frog-learned-mask"),
                (6, 2, 0x276D, 0x0000, "frog-remaining-tp"),
            ],
        )

    def test_import_does_not_touch_private_tree_or_load_validator(self) -> None:
        real_resolve = Path.resolve

        def guarded_resolve(
            path: Path,
            strict: bool = False,
        ) -> Path:
            if strict and "private" in tuple(
                part.casefold() for part in path.parts
            ):
                raise AssertionError(
                    "module import attempted strict private-path access"
                )
            return real_resolve(path, strict=strict)

        with mock.patch.object(Path, "resolve", guarded_resolve):
            imported = load_module(
                "run_mesen_wram_ownership_trace_clean_import",
                TOOL_PATH,
            )
        self.assertEqual(imported.PRIVATE_ROOT.name, "private")
        self.assertNotIn(
            "_project_epoch_mesen_wram_ownership_validator",
            sys.modules,
        )

    def test_parser_has_exact_scenarios_and_no_raw_packet_paths(self) -> None:
        actions = {
            action.dest: action for action in TOOL.build_parser()._actions
        }
        self.assertEqual(actions["scenario"].choices, TOOL.SCENARIOS)
        self.assertEqual(actions["variant"].choices, TOOL.VARIANTS)
        self.assertIn("exploratory", actions)
        self.assertNotIn("source_packet", actions)
        self.assertNotIn("transformed_packet", actions)
        launcher_source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertNotIn("PE_SOURCE_PACKET", launcher_source)
        self.assertNotIn("PE_TRANSFORMED_PACKET", launcher_source)

    def test_default_run_has_exact_output_contract_before_trust_resolution(
        self,
    ) -> None:
        self.assertEqual(
            set(TOOL.EXPECTED_OUTPUTS),
            {
                (scenario, variant)
                for scenario in TOOL.SCENARIOS
                for variant in TOOL.VARIANTS
            },
        )
        for outputs in TOOL.EXPECTED_OUTPUTS.values():
            self.assertEqual(set(outputs), {"trace", "screenshot"})
            for size, digest in outputs.values():
                self.assertGreater(size, 0)
                self.assertRegex(digest, r"^[0-9a-f]{64}$")

        args = types.SimpleNamespace(
            scenario="calibration",
            variant="zero",
            output_dir=Path("does-not-exist"),
            mesen=Path("does-not-exist"),
            rom=Path("does-not-exist"),
            state=Path("does-not-exist"),
            sram=Path("does-not-exist"),
            timeout=60,
            exploratory=False,
        )
        with mock.patch.object(
            TOOL,
            "load_trust_roots",
            side_effect=AssertionError("trust roots must not load"),
        ):
            with self.assertRaisesRegex(
                AssertionError,
                "trust roots must not load",
            ):
                TOOL.run(args)

    def test_unpinned_source_marker_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "no frozen exact SHA-256 pin",
        ):
            TOOL._read_pinned_bytes(
                TOOL_PATH,
                "UNPINNED-SOURCE-SHA256",
                "synthetic source",
            )

    def test_exact_byte_module_loader_never_uses_sourcefileloader(self) -> None:
        launcher_source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertNotIn("SourceFileLoader", launcher_source)
        self.assertNotIn("spec_from_file_location", launcher_source)
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "pinned_fixture.py"
            source_path.write_text("VALUE = 91\n", encoding="utf-8")
            expected = TOOL.sha256_file(source_path)
            module_name = "_project_epoch_ownership_exact_byte_fixture"
            try:
                loaded = TOOL._load_pinned_module(
                    module_name,
                    source_path,
                    expected,
                )
                self.assertEqual(loaded.VALUE, 91)
                self.assertIsNone(loaded.__loader__)
                self.assertIsNone(loaded.__spec__)
            finally:
                sys.modules.pop(module_name, None)

    def test_private_path_guards_reject_outside_and_save_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            workspace = temp_root / "workspace"
            private_root = workspace / "private"
            private_root.mkdir(parents=True)
            saves = private_root / "tools" / "mesen2" / "app" / "Saves"
            saves.mkdir(parents=True)
            with mock.patch.object(TOOL, "ROOT", workspace):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "resolves outside",
                ):
                    TOOL.prepare_private_output_dir(
                        temp_root / "outside-output"
                    )
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "overlaps protected tree",
                ):
                    TOOL.prepare_private_output_dir(
                        saves / "trace-output",
                        forbidden_roots=(saves,),
                    )

    def test_duplicate_trace_keys_are_rejected_before_validator(self) -> None:
        validator = FakeValidator("calibration", "zero")
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "duplicate JSON key",
        ):
            TOOL.load_trace_bytes(
                b'{"schema":"one","schema":"two"}',
                "calibration",
                "zero",
                validator,
                label="synthetic trace",
            )
        self.assertEqual(validator.calls, 0)

    def test_exclusive_pair_publish_rolls_back_only_created_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory).resolve(strict=True)
            trace_path = output_root / "trace.json"
            screenshot_path = output_root / "endpoint.png"
            screenshot_path.write_bytes(b"preexisting victim")
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "refusing to overwrite endpoint PNG",
            ):
                TOOL.publish_output_pair(
                    output_root,
                    trace_path,
                    b'{"safe":true}\n',
                    screenshot_path,
                    b"\x89PNG\r\n\x1a\nsafe",
                )
            self.assertFalse(os.path.lexists(trace_path))
            self.assertEqual(
                screenshot_path.read_bytes(),
                b"preexisting victim",
            )

    def test_full_exploratory_run_isolated_preserves_inputs_and_cleans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            private_root = workspace / "private"
            app_root = private_root / "tools" / "mesen2" / "app"
            shared_saves = app_root / "Saves"
            shared_saves.mkdir(parents=True)
            runtime_names = (
                "Mesen.exe",
                "MesenCore.dll",
                "libHarfBuzzSharp.dll",
                "libSkiaSharp.dll",
                "MesenNesDB.txt",
                "settings.json",
            )
            for name in runtime_names:
                (app_root / name).write_bytes(
                    f"synthetic {name}\n".encode("ascii")
                )
            archive = app_root.parent / "Mesen_2.1.1_Windows.zip"
            archive.write_bytes(b"synthetic archive\n")
            rom = private_root / "canonical.sfc"
            state = private_root / "checkpoint.mss"
            sram = private_root / "disposable.srm"
            rom.write_bytes(b"synthetic ROM\n")
            state.write_bytes(b"synthetic state\n")
            sram.write_bytes(b"synthetic SRAM\n")
            sentinel = shared_saves / "unrelated.srm"
            sentinel.write_bytes(b"must remain exact\n")

            source_root = workspace / "source"
            source_root.mkdir()
            collector_path = source_root / "collector.lua"
            validator_path = source_root / "validator.py"
            contract_path = source_root / "contract.json"
            collector_source = b"-- synthetic exact collector\n"
            contract_source = b'{"synthetic":"contract"}\n'
            collector_path.write_bytes(collector_source)
            validator_path.write_bytes(b"# synthetic validator\n")
            contract_path.write_bytes(contract_source)

            source_hashes_before = {
                path: TOOL.sha256_file(path)
                for path in (
                    collector_path,
                    validator_path,
                    contract_path,
                    rom,
                    state,
                    sram,
                    sentinel,
                )
            }
            output_dir = private_root / "trace-output"
            args = TOOL.build_parser().parse_args(
                [
                    "--scenario",
                    "field-idle",
                    "--variant",
                    "canary",
                    "--output-dir",
                    str(output_dir),
                    "--mesen",
                    str(app_root / "Mesen.exe"),
                    "--rom",
                    str(rom),
                    "--state",
                    str(state),
                    "--sram",
                    str(sram),
                    "--exploratory",
                ]
            )
            validator = FakeValidator("field-idle", "canary")
            trust = TOOL.TrustRoots(
                collector_source=collector_source,
                validator=validator,
                scenario_contract={},
                scenario_contract_source=contract_source,
            )
            observed_staged_paths: list[Path] = []

            def fake_run(
                command: list[str],
                **kwargs: object,
            ) -> subprocess.CompletedProcess[str]:
                environment = kwargs["env"]
                self.assertIsInstance(environment, dict)
                assert isinstance(environment, dict)
                self.assertEqual(environment["PE_SCENARIO"], "field-idle")
                self.assertEqual(environment["PE_VARIANT"], "canary")
                for key in (
                    "PE_STATE_PATH",
                    "PE_TRACE_OUT",
                    "PE_TRACE_SCREENSHOT",
                ):
                    self.assertIn(key, environment)
                self.assertNotIn("PE_SOURCE_PACKET", environment)
                self.assertNotIn("PE_TRANSFORMED_PACKET", environment)

                state_path = Path(environment["PE_STATE_PATH"])
                staged_trace = Path(environment["PE_TRACE_OUT"])
                staged_screenshot = Path(
                    environment["PE_TRACE_SCREENSHOT"]
                )
                staged_collector = Path(command[-2])
                staged_rom = Path(command[-1])
                staged_sram = (
                    Path(kwargs["cwd"])
                    / "Saves"
                    / f"{staged_rom.stem}.srm"
                )
                observed_staged_paths.extend(
                    (
                        state_path,
                        staged_trace,
                        staged_screenshot,
                        staged_collector,
                        staged_rom,
                        staged_sram,
                    )
                )
                self.assertEqual(state_path.read_bytes(), state.read_bytes())
                self.assertEqual(
                    staged_collector.read_bytes(),
                    collector_source,
                )
                self.assertNotEqual(state_path, state)
                self.assertNotEqual(staged_collector, collector_path)
                self.assertNotEqual(staged_rom, rom)
                self.assertNotEqual(staged_sram, sram)
                self.assertFalse((output_dir / "trace.json").exists())
                self.assertFalse((output_dir / "endpoint.png").exists())
                staged_trace.write_text(
                    '{"callbacks":[]}\n',
                    encoding="utf-8",
                )
                staged_screenshot.write_bytes(
                    b"\x89PNG\r\n\x1a\nsynthetic"
                )
                return subprocess.CompletedProcess(
                    command,
                    TOOL.EXPECTED_EXIT_CODE,
                    stdout="",
                    stderr="",
                )

            synthetic_sizes = {
                "archive": archive.stat().st_size,
                "harfbuzz": (app_root / "libHarfBuzzSharp.dll").stat().st_size,
                "mesen": (app_root / "Mesen.exe").stat().st_size,
                "mesen_core": (app_root / "MesenCore.dll").stat().st_size,
                "nesdb": (app_root / "MesenNesDB.txt").stat().st_size,
                "settings": (app_root / "settings.json").stat().st_size,
                "skia": (app_root / "libSkiaSharp.dll").stat().st_size,
                "rom": rom.stat().st_size,
                "state": state.stat().st_size,
                "sram": sram.stat().st_size,
            }
            hash_side_effect = (
                lambda path, _expected, _label: TOOL.sha256_file(path)
            )
            with mock.patch.object(TOOL, "ROOT", workspace):
                with mock.patch.object(TOOL, "COLLECTOR", collector_path):
                    with mock.patch.object(
                        TOOL,
                        "VALIDATOR_PATH",
                        validator_path,
                    ):
                        with mock.patch.object(
                            TOOL,
                            "SCENARIO_CONTRACT_PATH",
                            contract_path,
                        ):
                            with mock.patch.object(
                                TOOL,
                                "PINNED_SIZES",
                                synthetic_sizes,
                            ):
                                with mock.patch.object(
                                    TOOL,
                                    "load_trust_roots",
                                    return_value=trust,
                                ):
                                    with mock.patch.object(
                                        TOOL,
                                        "require_hash",
                                        side_effect=hash_side_effect,
                                    ):
                                        with mock.patch.object(
                                            TOOL.subprocess,
                                            "run",
                                            side_effect=fake_run,
                                        ):
                                            result = TOOL.run(args)

            self.assertEqual(
                result["status"],
                "exploratory-private-diagnostic-case-not-accepted",
            )
            self.assertTrue(result["immutable_inputs_preserved"])
            self.assertTrue(result["shared_mesen_saves_preserved"])
            self.assertTrue(result["disposable_staging_deleted"])
            self.assertEqual(validator.calls, 1)
            for path, expected in source_hashes_before.items():
                self.assertEqual(TOOL.sha256_file(path), expected)
            self.assertTrue(
                all(not os.path.lexists(path) for path in observed_staged_paths)
            )
            self.assertEqual(
                list(output_dir.glob(".mesen_wram_ownership_staging_*")),
                [],
            )
            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir()),
                ["endpoint.png", "trace.json"],
            )


if __name__ == "__main__":
    unittest.main()
