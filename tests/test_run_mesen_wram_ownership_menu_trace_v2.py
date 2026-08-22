from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT / "tools" / "run_mesen_wram_ownership_menu_trace_v2.py"
)
ACCEPTANCE_SPEC = (
    ROOT
    / "references"
    / "mesen_wram_ownership_menu_accepted_artifacts_v2.json"
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


TOOL = load_module(
    "run_mesen_wram_ownership_menu_trace_v2_test",
    TOOL_PATH,
)

BASE_CONFIGURATION_NAMES = (
    "COLLECTOR",
    "COLLECTOR_SHA256",
    "VALIDATOR_PATH",
    "VALIDATOR_SHA256",
    "SCENARIO_CONTRACT_PATH",
    "SCENARIO_CONTRACT_SHA256",
    "SCENARIO_CONTRACT_SCHEMA",
    "TRACE_SCHEMA",
    "SCENARIOS",
    "VARIANTS",
    "EXPECTED_OUTPUTS",
    "_validate_scenario_contract",
)


def save_base_configuration() -> dict[str, object]:
    return {
        name: getattr(TOOL.BASE, name)
        for name in BASE_CONFIGURATION_NAMES
    }


def restore_base_configuration(values: dict[str, object]) -> None:
    for name, value in values.items():
        setattr(TOOL.BASE, name, value)


def minimal_args(*, exploratory: bool) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        scenario="equipment-owner-switch",
        variant="zero",
        exploratory=exploratory,
    )


class RunMesenWramOwnershipMenuTraceV2Tests(unittest.TestCase):
    def test_acceptance_spec_pins_sources_and_safe_artifacts(self) -> None:
        spec = json.loads(ACCEPTANCE_SPEC.read_text(encoding="utf-8"))
        self.assertEqual(
            spec["schema"],
            "project-epoch-mesen-wram-ownership-menu-acceptance-v2",
        )
        self.assertEqual(spec["evidence_level"], "verified-runtime")
        source_rows = (
            ("scenario_contract", TOOL.SCENARIO_CONTRACT_PATH),
            ("collector_builder", TOOL.BUILDER_PATH),
            ("validator", TOOL.VALIDATOR_PATH),
            ("launcher", TOOL_PATH),
        )
        for key, path in source_rows:
            row = spec["sources"][key]
            self.assertEqual(row["path"], path.relative_to(ROOT).as_posix())
            self.assertEqual(row["size"], path.stat().st_size)
            self.assertEqual(
                row["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

        generated = TOOL.BUILDER.build_collector()
        generated_row = spec["sources"]["generated_collector"]
        self.assertEqual(generated_row["size"], len(generated))
        self.assertEqual(
            generated_row["sha256"],
            hashlib.sha256(generated).hexdigest(),
        )
        self.assertFalse(generated_row["source_controlled"])
        self.assertTrue(generated_row["staged_private_only"])

        test_paths = [
            ROOT / row["path"] for row in spec["sources"]["tests"]
        ]
        self.assertEqual(
            {path.name for path in test_paths},
            {
                "test_build_mesen_wram_ownership_menu_collector_v2.py",
                "test_mesen_wram_ownership_menu_trace_v2.py",
                "test_run_mesen_wram_ownership_menu_trace_v2.py",
            },
        )
        for row, path in zip(
            spec["sources"]["tests"],
            test_paths,
            strict=True,
        ):
            self.assertEqual(row["size"], path.stat().st_size)
            self.assertEqual(
                row["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

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

    def test_current_sources_contract_and_generated_collector_are_pinned(
        self,
    ) -> None:
        verified = TOOL._verify_ancestry()
        self.assertEqual(set(verified), set(TOOL.ANCESTRY_PINS))
        for path, expected in TOOL.ANCESTRY_PINS.items():
            self.assertEqual(verified[path], expected)

        contract = json.loads(
            TOOL.SCENARIO_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        TOOL._validate_scenario_contract(contract)

        generated = TOOL.BUILDER.build_collector()
        self.assertEqual(len(generated), TOOL.GENERATED_COLLECTOR_SIZE)
        self.assertEqual(
            hashlib.sha256(generated).hexdigest(),
            TOOL.GENERATED_COLLECTOR_SHA256,
        )

    def test_contract_rejects_a_source_pin_change(self) -> None:
        contract = json.loads(
            TOOL.SCENARIO_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        contract["sources"]["validator"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            TOOL.BASE.TraceLaunchError,
            "validator pin drifted",
        ):
            TOOL._validate_scenario_contract(contract)

    def test_run_fails_on_ancestry_drift_before_build_or_base_launch(
        self,
    ) -> None:
        with mock.patch.object(
            TOOL,
            "_sha256_file",
            return_value="0" * 64,
        ):
            with mock.patch.object(
                TOOL.BUILDER,
                "build_collector",
                side_effect=AssertionError(
                    "collector must not build after ancestry drift"
                ),
            ) as build:
                with mock.patch.object(
                    TOOL.BASE,
                    "run",
                    side_effect=AssertionError(
                        "base launcher must not run after ancestry drift"
                    ),
                ) as base_run:
                    with self.assertRaisesRegex(
                        TOOL.BASE.TraceLaunchError,
                        "menu-v2 ancestry drifted",
                    ):
                        TOOL.run(minimal_args(exploratory=True))
        build.assert_not_called()
        base_run.assert_not_called()

    def test_accepted_outputs_cover_all_cases_and_default_reaches_base(
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
        saved = save_base_configuration()
        staged_path: Path | None = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                private_root = Path(directory).resolve(strict=True) / "private"
                source_parent = private_root / "test_runs" / "mesen2"
                source_parent.mkdir(parents=True)
                with mock.patch.object(
                    TOOL,
                    "PRIVATE_ROOT",
                    private_root,
                ):
                    with mock.patch.object(
                        TOOL,
                        "_verify_ancestry",
                        return_value={Path("pin"): "stable"},
                    ):
                        with mock.patch.object(
                            TOOL.BASE,
                            "run",
                            return_value={
                                "status": "synthetic-accepted-base-run"
                            },
                        ) as base_run:
                            result = TOOL.run(
                                minimal_args(exploratory=False)
                            )
                            base_run.assert_called_once()
                staged_path = Path(TOOL.BASE.COLLECTOR)
                self.assertFalse(os.path.lexists(staged_path))
                self.assertEqual(list(source_parent.iterdir()), [])
                self.assertEqual(
                    result["status"],
                    "synthetic-accepted-base-run",
                )
        finally:
            restore_base_configuration(saved)
        self.assertIsNotNone(staged_path)

    def test_private_generated_source_is_deleted_after_mocked_success(
        self,
    ) -> None:
        saved = save_base_configuration()
        observed: list[Path] = []
        try:
            with tempfile.TemporaryDirectory() as directory:
                private_root = Path(directory).resolve(strict=True) / "private"
                source_parent = private_root / "test_runs" / "mesen2"
                source_parent.mkdir(parents=True)

                def fake_base_run(args: object) -> dict[str, object]:
                    staged = Path(TOOL.BASE.COLLECTOR).resolve(strict=True)
                    staged.relative_to(private_root)
                    self.assertEqual(
                        staged.read_bytes(),
                        TOOL.BUILDER.build_collector(),
                    )
                    observed.append(staged)
                    return {"status": "synthetic-base-run-without-mesen"}

                with mock.patch.object(
                    TOOL,
                    "PRIVATE_ROOT",
                    private_root,
                ):
                    with mock.patch.object(
                        TOOL,
                        "_verify_ancestry",
                        return_value={Path("pin"): "stable"},
                    ) as ancestry:
                        with mock.patch.object(
                            TOOL.BASE,
                            "run",
                            side_effect=fake_base_run,
                        ) as base_run:
                            with mock.patch.object(
                                TOOL.BASE.subprocess,
                                "run",
                                side_effect=AssertionError(
                                    "Mesen must not be invoked"
                                ),
                            ):
                                result = TOOL.run(
                                    minimal_args(exploratory=True)
                                )

                self.assertEqual(base_run.call_count, 1)
                self.assertEqual(ancestry.call_count, 2)
                self.assertEqual(len(observed), 1)
                self.assertFalse(os.path.lexists(observed[0]))
                self.assertEqual(list(source_parent.iterdir()), [])
                self.assertTrue(
                    result["generated_collector_source_deleted"]
                )
                self.assertEqual(
                    result["generated_collector_sha256"],
                    TOOL.GENERATED_COLLECTOR_SHA256,
                )
                self.assertEqual(result["trace_schema"], TOOL.TRACE_SCHEMA)
        finally:
            restore_base_configuration(saved)


if __name__ == "__main__":
    unittest.main()
