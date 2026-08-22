from __future__ import annotations

import dataclasses
import json
import pathlib
import sys
import tempfile
import unittest
from collections.abc import Callable, Mapping


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_sha256_65816_fast_runtime_evidence_manifest as FAST  # noqa: E402
import build_sha256_65816_round8_runtime_evidence_manifest as ROUND8  # noqa: E402
import build_sha256_65816_runtime_evidence_manifest as BASE  # noqa: E402
import inspect_schala_sha256_65816_benchmark_state as INSPECTOR  # noqa: E402
import retroarch_rastate  # noqa: E402
from tests.test_sha256_65816_runtime_evidence_manifest import (  # noqa: E402
    Fixture,
    file_pin,
    make_fixture,
    record,
    write_text,
)


TableValidator = Callable[[pathlib.Path], Mapping[str, object]]


def table_report(pin: BASE.FilePin) -> dict[str, object]:
    return {
        "specification": "project-epoch-sha256-sigma-byte-tables-v1",
        "output_size": pin.size,
        "output_sha256": pin.sha256,
        "binary_table_size": 16_384,
        "transform_count": 4,
        "byte_tables_per_transform": 4,
        "entries_per_byte_table": 256,
        "entry_size": 4,
        "entry_word_order": "numeric-high16,numeric-low16",
        "input_byte_order": "Byte0=bits31..24,Byte3=bits7..0",
        "contains_game_data": False,
        "placed": False,
        "status": "current",
    }


@dataclasses.dataclass
class Round8Fixture:
    fixture: Fixture
    pins: ROUND8.Round8CandidatePins
    generated_table: pathlib.Path
    generator_source: pathlib.Path
    validator: TableValidator

    def kwargs(self) -> dict[str, object]:
        values = self.fixture.kwargs()
        values.update(
            {
                "pins": self.pins,
                "generated_table": self.generated_table,
                "table_generator_source": self.generator_source,
                "table_validator": self.validator,
            }
        )
        return values


def make_round8_fixture(root: pathlib.Path) -> Round8Fixture:
    fixture = make_fixture(root)

    generated_table = root / "source" / "sigma_tables.asm"
    generator_source = root / "source" / "generate_sigma_tables.py"
    write_text(generated_table, "db $00,$01,$02,$03\n")
    write_text(generator_source, "VERSION = 1\n")

    static_source = json.loads(
        fixture.static_manifest.read_text(encoding="utf-8")
    )
    static_source["assembly_sources"].append(record(generated_table))
    write_text(
        fixture.static_manifest,
        json.dumps(static_source, indent=2, sort_keys=True) + "\n",
    )

    for log, config in zip(
        fixture.logs,
        fixture.configs,
        strict=True,
    ):
        text = log.read_text(encoding="utf-8")
        text = text.replace(
            str(fixture.base_config.resolve()),
            str(fixture.base_config.resolve().relative_to(ROOT)),
        )
        text = text.replace(
            str(config.resolve()),
            str(config.resolve().relative_to(ROOT)),
        )
        write_text(log, text)

    fixture.pins = dataclasses.replace(
        fixture.pins,
        static_manifest=file_pin(fixture.static_manifest),
        logs=(file_pin(fixture.logs[0]), file_pin(fixture.logs[1])),
        required_assembly_paths=(
            *fixture.pins.required_assembly_paths,
            BASE.workspace_relative(generated_table),
        ),
    )
    reports = [
        INSPECTOR.inspect_path(path)
        for path in fixture.states
    ]
    cores = [
        retroarch_rastate.extract_memory(path.read_bytes())
        for path in fixture.states
    ]
    comparison = BASE.compare_runs(reports, cores, pins=fixture.pins)
    result = reports[0]["result"]
    table_pin = file_pin(generated_table)
    pins = ROUND8.Round8CandidatePins(
        runtime=fixture.pins,
        state_sha256=tuple(
            BASE.sha256_path(path) for path in fixture.states
        ),
        core_state_sha256=tuple(
            report["core_state"]["sha256"] for report in reports
        ),
        result_sha256=result["record_sha256"],
        scratch_with_guards_sha256=result[
            "scratch_with_guards_sha256"
        ],
        sram_sha256=reports[0]["memory_layout"]["sram_sha256"],
        elapsed_frames=tuple(
            slot["elapsed_frames"] for slot in result["slots"]
        ),
        final_frame=result["final_frame"],
        core_difference_count=comparison[
            "full_core_state_difference_count"
        ],
        bounded_serializer_difference_count=comparison[
            "bounded_non_wram_difference"
        ]["differing_byte_count"],
        irrelevant_wram_difference_count=comparison[
            "uncleared_irrelevant_wram"
        ]["differing_byte_count"],
        generated_table=table_pin,
        table_generator_source=file_pin(generator_source),
    )
    fixture.output = root / "round8.runtime.manifest.json"

    expected_path = generated_table.resolve()

    def validator(path: pathlib.Path) -> Mapping[str, object]:
        if path.resolve() != expected_path:
            raise ValueError("unexpected generated-table path")
        return table_report(table_pin)

    return Round8Fixture(
        fixture=fixture,
        pins=pins,
        generated_table=generated_table,
        generator_source=generator_source,
        validator=validator,
    )


class Sha25665816Round8RuntimeEvidenceManifestTests(unittest.TestCase):
    def fixture_context(self):
        return tempfile.TemporaryDirectory(
            prefix="sha_round8_runtime_manifest_",
            dir=ROUND8.PRIVATE_ROOT,
        )

    def test_separate_round8_path_preserves_existing_defaults(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            baseline_before = BASE.DEFAULT_PINS
            fast_runtime_before = FAST.FAST_RUNTIME_PINS
            fast_candidate_before = FAST.DEFAULT_FAST_PINS
            result = ROUND8.build_in_memory(**setup.kwargs())
            self.assertEqual(BASE.DEFAULT_PINS, baseline_before)
            self.assertEqual(FAST.FAST_RUNTIME_PINS, fast_runtime_before)
            self.assertEqual(FAST.DEFAULT_FAST_PINS, fast_candidate_before)
            self.assertIsNot(ROUND8.ROUND8_RUNTIME_PINS, BASE.DEFAULT_PINS)
            self.assertEqual(
                result.manifest["status"],
                "verified-runtime-standalone-round8-candidate-stopped",
            )
            candidate = result.manifest["round8_candidate"]
            self.assertTrue(candidate["candidate_only"])
            self.assertFalse(
                candidate["baseline_or_fast_behavior_or_pins_modified"]
            )
            self.assertFalse(candidate["integration_approved"])
            self.assertFalse(candidate["production_approved"])
            self.assertFalse(
                result.manifest["static_build"][
                    "historical_drifted_manifest_accepted"
                ]
            )

    def test_stop_gate_is_exact_strict_and_fail_closed(self) -> None:
        gate = ROUND8.build_stop_gate(
            (30, 31, 30),
            threshold_frames=30,
        )
        self.assertEqual(gate["triggering_slots"], [2])
        self.assertEqual(
            gate["classification"],
            ROUND8.STOP_GATE_CLASSIFICATION,
        )
        self.assertEqual(
            gate["required_explicit_decision"]["decision_class"],
            ROUND8.REQUIRED_DECISION_CLASS,
        )
        self.assertFalse(gate["further_optimization_authorized"])
        self.assertFalse(gate["integration_authorized"])
        self.assertFalse(gate["production_authorized"])

        with self.assertRaisesRegex(
            ROUND8.Round8EvidenceError,
            "threshold must remain exactly 30",
        ):
            ROUND8.build_stop_gate((31, 31, 31), threshold_frames=31)
        with self.assertRaisesRegex(
            ROUND8.Round8EvidenceError,
            "did not trigger",
        ):
            ROUND8.build_stop_gate((30, 30, 30), threshold_frames=30)

    def test_frame_contract_is_exact_before_gate_classification(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            wrong = dataclasses.replace(
                setup.pins,
                elapsed_frames=(
                    setup.pins.elapsed_frames[0] + 1,
                    setup.pins.elapsed_frames[1],
                    setup.pins.elapsed_frames[2],
                ),
            )
            setup.pins = wrong
            with self.assertRaisesRegex(
                ROUND8.Round8EvidenceError,
                "frame contract mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

    def test_state_and_core_state_pins_are_exact(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            setup.pins = dataclasses.replace(
                setup.pins,
                state_sha256=("0" * 64, setup.pins.state_sha256[1]),
            )
            with self.assertRaisesRegex(
                ROUND8.Round8EvidenceError,
                "RASTATE pin mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            setup.pins = dataclasses.replace(
                setup.pins,
                core_state_sha256=(
                    setup.pins.core_state_sha256[0],
                    "f" * 64,
                ),
            )
            with self.assertRaisesRegex(
                ROUND8.Round8EvidenceError,
                "core-state pin mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

    def test_result_scratch_and_zero_sram_pins_are_independent(self) -> None:
        fields = (
            ("result_sha256", "result-record pin mismatch"),
            (
                "scratch_with_guards_sha256",
                "scratch/guard pin mismatch",
            ),
            ("sram_sha256", "SRAM pin mismatch"),
        )
        for field, message in fields:
            with self.subTest(field=field):
                with self.fixture_context() as directory:
                    setup = make_round8_fixture(pathlib.Path(directory))
                    setup.pins = dataclasses.replace(
                        setup.pins,
                        **{field: "0" * 64},
                    )
                    with self.assertRaisesRegex(
                        ROUND8.Round8EvidenceError,
                        message,
                    ):
                        ROUND8.build_in_memory(**setup.kwargs())

    def test_difference_counts_cannot_be_broadened(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            setup.pins = dataclasses.replace(
                setup.pins,
                irrelevant_wram_difference_count=(
                    setup.pins.irrelevant_wram_difference_count + 1
                ),
            )
            with self.assertRaisesRegex(
                ROUND8.Round8EvidenceError,
                "irrelevant-WRAM difference count mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

    def test_generated_table_and_generator_are_pinned_separately(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            setup.pins = dataclasses.replace(
                setup.pins,
                generated_table=BASE.FilePin(
                    setup.pins.generated_table.size,
                    "0" * 64,
                ),
            )
            with self.assertRaisesRegex(
                BASE.RuntimeEvidenceError,
                "generated sigma table SHA-256 mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            setup.pins = dataclasses.replace(
                setup.pins,
                table_generator_source=BASE.FilePin(
                    setup.pins.table_generator_source.size,
                    "f" * 64,
                ),
            )
            with self.assertRaisesRegex(
                BASE.RuntimeEvidenceError,
                "generator source SHA-256 mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

    def test_generated_table_report_drift_is_rejected(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            report = table_report(setup.pins.generated_table)
            report["status"] = "stale"

            def stale_validator(
                _path: pathlib.Path,
            ) -> Mapping[str, object]:
                return report

            setup.validator = stale_validator
            with self.assertRaisesRegex(
                ROUND8.Round8EvidenceError,
                "validator status mismatch",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

    def test_static_source_drift_is_rejected_before_runtime_claim(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            write_text(
                setup.generated_table,
                setup.generated_table.read_text(encoding="utf-8")
                + "db $ff\n",
            )
            with self.assertRaisesRegex(
                BASE.RuntimeEvidenceError,
                "assembly source .* no longer matches its manifest",
            ):
                ROUND8.build_in_memory(**setup.kwargs())

    def test_round8_manifest_write_is_idempotent_and_conflict_safe(self) -> None:
        with self.fixture_context() as directory:
            setup = make_round8_fixture(pathlib.Path(directory))
            result = ROUND8.build_in_memory(**setup.kwargs())
            ROUND8.write_manifest(result, setup.fixture.output)
            ROUND8.write_manifest(result, setup.fixture.output)
            setup.fixture.output.write_bytes(b"different")
            with self.assertRaisesRegex(
                BASE.RuntimeEvidenceError,
                "refusing to overwrite",
            ):
                ROUND8.write_manifest(result, setup.fixture.output)

    @unittest.skipUnless(
        ROUND8.DEFAULT_STATIC_MANIFEST.is_file()
        and ROUND8.DEFAULT_GENERATED_TABLE.is_file()
        and ROUND8.DEFAULT_TABLE_GENERATOR_SOURCE.is_file()
        and all(path.is_file() for path in ROUND8.DEFAULT_STATES)
        and all(path.is_file() for path in ROUND8.DEFAULT_LOGS)
        and all(path.is_file() for path in ROUND8.DEFAULT_RUN_CONFIGS)
        and BASE.DEFAULT_RETROARCH_EXE.is_file()
        and BASE.DEFAULT_CORE.is_file()
        and BASE.DEFAULT_CORE_INFO.is_file(),
        "private round8 evidence or its pinned toolchain is unavailable",
    )
    def test_live_round8_candidate_matches_every_pin_and_stops(self) -> None:
        result = ROUND8.build_in_memory()
        candidate = result.manifest["round8_candidate"]
        self.assertEqual(candidate["elapsed_frames"], [68, 69, 69])
        self.assertEqual(
            candidate["result_record_sha256"],
            ROUND8.ROUND8_RESULT_SHA256,
        )
        self.assertEqual(
            candidate["scratch_with_guards_sha256"],
            ROUND8.ROUND8_SCRATCH_GUARDS_SHA256,
        )
        gate = result.manifest["stop_gate"]
        self.assertTrue(gate["triggered"])
        self.assertEqual(gate["triggering_slots"], [1, 2, 3])
        self.assertEqual(gate["threshold_frames"], 30)
        self.assertEqual(
            result.manifest["conclusion"]["explicit_decision_required"],
            ROUND8.REQUIRED_DECISION_CLASS,
        )
        self.assertFalse(
            result.manifest["conclusion"]["integration_approved"]
        )
        self.assertFalse(
            result.manifest["conclusion"]["production_timing_approved"]
        )


if __name__ == "__main__":
    unittest.main()
