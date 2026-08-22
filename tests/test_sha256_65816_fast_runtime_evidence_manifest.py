from __future__ import annotations

import dataclasses
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_sha256_65816_fast_runtime_evidence_manifest as FAST  # noqa: E402
import build_sha256_65816_runtime_evidence_manifest as BASE  # noqa: E402
import inspect_schala_sha256_65816_benchmark_state as INSPECTOR  # noqa: E402
import retroarch_rastate  # noqa: E402
from tests.test_sha256_65816_runtime_evidence_manifest import (  # noqa: E402
    Fixture,
    file_pin,
    make_fixture,
    write_text,
)


def make_fast_fixture(root: pathlib.Path) -> tuple[Fixture, FAST.FastCandidatePins]:
    fixture = make_fixture(root)
    for log, config in zip(fixture.logs, fixture.configs, strict=True):
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
        logs=(file_pin(fixture.logs[0]), file_pin(fixture.logs[1])),
    )

    reports = [INSPECTOR.inspect_path(path) for path in fixture.states]
    cores = [
        retroarch_rastate.extract_memory(path.read_bytes())
        for path in fixture.states
    ]
    comparison = BASE.compare_runs(reports, cores, pins=fixture.pins)
    result = reports[0]["result"]
    fast_pins = FAST.FastCandidatePins(
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
        baseline_elapsed_frames=(700, 700, 700),
    )
    fixture.output = root / "fast.runtime.manifest.json"
    return fixture, fast_pins


def fast_kwargs(
    fixture: Fixture,
    pins: FAST.FastCandidatePins,
) -> dict[str, object]:
    values = fixture.kwargs()
    values["pins"] = pins
    return values


class Sha25665816FastRuntimeEvidenceManifestTests(unittest.TestCase):
    def fixture_context(self):
        return tempfile.TemporaryDirectory(
            prefix="sha_fast_runtime_manifest_",
            dir=FAST.PRIVATE_ROOT,
        )

    def test_separate_fast_path_preserves_baseline_defaults(self) -> None:
        with self.fixture_context() as directory:
            fixture, pins = make_fast_fixture(pathlib.Path(directory))
            baseline_before = BASE.DEFAULT_PINS
            result = FAST.build_in_memory(**fast_kwargs(fixture, pins))
            self.assertEqual(BASE.DEFAULT_PINS, baseline_before)
            self.assertIsNot(FAST.FAST_RUNTIME_PINS, BASE.DEFAULT_PINS)
            self.assertEqual(
                result.manifest["status"],
                "verified-runtime-standalone-fast-candidate",
            )
            candidate = result.manifest["fast_candidate"]
            self.assertTrue(candidate["candidate_only"])
            self.assertFalse(candidate["baseline_behavior_or_pins_modified"])
            self.assertFalse(candidate["production_approved"])
            self.assertEqual(
                candidate["elapsed_frames"],
                list(pins.elapsed_frames),
            )
            self.assertTrue(
                all(
                    speedup > 1
                    for speedup in candidate[
                        "speedup_over_correctness_baseline"
                    ]
                )
            )
            self.assertFalse(
                result.manifest["static_build"][
                    "historical_drifted_manifest_accepted"
                ]
            )

    def test_frame_contract_is_exact_and_fail_closed(self) -> None:
        with self.fixture_context() as directory:
            fixture, pins = make_fast_fixture(pathlib.Path(directory))
            wrong = dataclasses.replace(
                pins,
                elapsed_frames=(
                    pins.elapsed_frames[0] + 1,
                    pins.elapsed_frames[1],
                    pins.elapsed_frames[2],
                ),
            )
            with self.assertRaisesRegex(
                FAST.FastCandidateEvidenceError,
                "frame contract mismatch",
            ):
                FAST.build_in_memory(**fast_kwargs(fixture, wrong))

    def test_state_and_core_state_pins_are_exact(self) -> None:
        with self.fixture_context() as directory:
            fixture, pins = make_fast_fixture(pathlib.Path(directory))
            wrong_state = dataclasses.replace(
                pins,
                state_sha256=("0" * 64, pins.state_sha256[1]),
            )
            with self.assertRaisesRegex(
                FAST.FastCandidateEvidenceError,
                "RASTATE pin mismatch",
            ):
                FAST.build_in_memory(**fast_kwargs(fixture, wrong_state))

            wrong_core = dataclasses.replace(
                pins,
                core_state_sha256=(pins.core_state_sha256[0], "f" * 64),
            )
            with self.assertRaisesRegex(
                FAST.FastCandidateEvidenceError,
                "core-state pin mismatch",
            ):
                FAST.build_in_memory(**fast_kwargs(fixture, wrong_core))

    def test_result_scratch_and_sram_pins_are_independent(self) -> None:
        with self.fixture_context() as directory:
            fixture, pins = make_fast_fixture(pathlib.Path(directory))
            cases = (
                (
                    dataclasses.replace(pins, result_sha256="0" * 64),
                    "result-record pin mismatch",
                ),
                (
                    dataclasses.replace(
                        pins,
                        scratch_with_guards_sha256="0" * 64,
                    ),
                    "scratch/guard pin mismatch",
                ),
                (
                    dataclasses.replace(pins, sram_sha256="0" * 64),
                    "SRAM pin mismatch",
                ),
            )
            for wrong, message in cases:
                with self.subTest(message=message):
                    with self.assertRaisesRegex(
                        FAST.FastCandidateEvidenceError,
                        message,
                    ):
                        FAST.build_in_memory(
                            **fast_kwargs(fixture, wrong)
                        )

    def test_difference_counts_cannot_be_broadened(self) -> None:
        with self.fixture_context() as directory:
            fixture, pins = make_fast_fixture(pathlib.Path(directory))
            wrong = dataclasses.replace(
                pins,
                irrelevant_wram_difference_count=(
                    pins.irrelevant_wram_difference_count + 1
                ),
            )
            with self.assertRaisesRegex(
                FAST.FastCandidateEvidenceError,
                "irrelevant-WRAM difference count mismatch",
            ):
                FAST.build_in_memory(**fast_kwargs(fixture, wrong))

    def test_fast_manifest_write_is_idempotent_and_conflict_safe(self) -> None:
        with self.fixture_context() as directory:
            fixture, pins = make_fast_fixture(pathlib.Path(directory))
            result = FAST.build_in_memory(**fast_kwargs(fixture, pins))
            FAST.write_manifest(result, fixture.output)
            FAST.write_manifest(result, fixture.output)
            fixture.output.write_bytes(b"different")
            with self.assertRaisesRegex(
                BASE.RuntimeEvidenceError,
                "refusing to overwrite",
            ):
                FAST.write_manifest(result, fixture.output)

    @unittest.skipUnless(
        FAST.DEFAULT_STATIC_MANIFEST.is_file()
        and all(path.is_file() for path in FAST.DEFAULT_STATES)
        and all(path.is_file() for path in FAST.DEFAULT_LOGS)
        and all(path.is_file() for path in FAST.DEFAULT_RUN_CONFIGS)
        and BASE.DEFAULT_RETROARCH_EXE.is_file()
        and BASE.DEFAULT_CORE.is_file()
        and BASE.DEFAULT_CORE_INFO.is_file(),
        "private fast-candidate evidence or its pinned toolchain is unavailable",
    )
    def test_live_fast_candidate_matches_every_pin(self) -> None:
        result = FAST.build_in_memory()
        self.assertEqual(
            result.manifest["fast_candidate"]["elapsed_frames"],
            [123, 123, 124],
        )
        self.assertEqual(
            result.manifest["fast_candidate"]["result_record_sha256"],
            FAST.FAST_RESULT_SHA256,
        )
        self.assertFalse(
            result.manifest["conclusion"]["production_timing_approved"]
        )

    @unittest.skipUnless(
        (
            FAST.BENCHMARK_ROOT
            / "schala_sha256_profile1_fast_benchmark.manifest.json"
        ).is_file(),
        "historical drifted fast manifest is unavailable",
    )
    def test_historical_drifted_fast_manifest_is_rejected(self) -> None:
        historical = (
            FAST.BENCHMARK_ROOT
            / "schala_sha256_profile1_fast_benchmark.manifest.json"
        )
        with self.assertRaisesRegex(
            BASE.RuntimeEvidenceError,
            "static build manifest (?:size|SHA-256) mismatch",
        ):
            FAST.build_in_memory(static_manifest=historical)


if __name__ == "__main__":
    unittest.main()
