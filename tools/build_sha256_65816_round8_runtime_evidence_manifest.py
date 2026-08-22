#!/usr/bin/env python3
"""Build fail-closed runtime evidence for the isolated round8 SHA candidate.

This path has its own static-manifest, source, generated-table, ROM, capture,
and timing pins.  It imports the baseline validator only as a library and does
not modify or relax either the baseline or fast-candidate defaults.  The
predeclared stop rule is strict: any digest taking more than 30 NMI frames
halts this line of work pending an explicit binding-profile/threat-model or
algorithm decision.  No Chrono Trigger ROM, save, movie, or state is accepted.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
from collections.abc import Callable, Mapping, Sequence

import build_sha256_65816_runtime_evidence_manifest as baseline
import generate_schala_sha256_65816_sigma_tables as sigma_generator
import inspect_schala_sha256_65816_benchmark_state as state_inspector


VERSION = "1.0.0"

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (WORKSPACE_ROOT / "private").resolve()
BENCHMARK_ROOT = PRIVATE_ROOT / "test_runs" / "sha256_65c816_round8"

DEFAULT_STATIC_MANIFEST = (
    BENCHMARK_ROOT
    / "schala_sha256_profile1_round8_benchmark.manifest.json"
)
DEFAULT_STATES = (
    BENCHMARK_ROOT
    / "runtime_run1"
    / "schala_sha256_profile1_round8_benchmark.state.auto",
    BENCHMARK_ROOT
    / "runtime_run2"
    / "schala_sha256_profile1_round8_benchmark.state.auto",
)
DEFAULT_LOGS = (
    BENCHMARK_ROOT / "runtime_run1" / "benchmark.log",
    BENCHMARK_ROOT / "runtime_run2" / "benchmark.log",
)
DEFAULT_RUN_CONFIGS = (
    BENCHMARK_ROOT / "retroarch-round8-benchmark-run1.cfg",
    BENCHMARK_ROOT / "retroarch-round8-benchmark-run2.cfg",
)
DEFAULT_GENERATED_TABLE = (
    WORKSPACE_ROOT / "asm" / "schala_sidecar_sha256_sigma_tables.asm"
)
DEFAULT_TABLE_GENERATOR_SOURCE = (
    WORKSPACE_ROOT
    / "tools"
    / "generate_schala_sha256_65816_sigma_tables.py"
)
DEFAULT_OUTPUT = BENCHMARK_ROOT / "runtime_evidence_manifest.json"

ROUND8_ROM_SHA256 = (
    "47aca086d0c714a549312d75317b4fc6c4e7aca4d0af9e3a072ef8625f59028e"
)
ROUND8_RESULT_SHA256 = (
    "58af32127cdf9b0f8a11fee2d2a4bb90f8e847bda1492ad5aae9092e1f700c75"
)
ROUND8_SCRATCH_GUARDS_SHA256 = (
    "14cc30162870a2fbac89a49a07568a31c194c9ed7d8cc7d0b2250486e103303f"
)
STOP_THRESHOLD_FRAMES = 30
STOP_GATE_CLASSIFICATION = (
    "predeclared-greater-than-30-frame-stop-gate-triggered"
)
REQUIRED_DECISION_CLASS = "binding-profile-threat-model-or-algorithm"


ROUND8_RUNTIME_PINS = dataclasses.replace(
    baseline.DEFAULT_PINS,
    static_manifest=baseline.FilePin(
        8_923,
        "46636c5c33683622f9f742ebf0fae610d7186d28d88330a5af801d52063f2620",
    ),
    run_configs=(
        baseline.FilePin(
            324,
            "8566b9543042543d05247c6ea35bb07c1c01bd69c1d2579a381bc0bfceeb1737",
        ),
        baseline.FilePin(
            324,
            "5ec3ad914d8a33377eae126e3fcb396362496c9b4542a64273e33d62a72ab321",
        ),
    ),
    logs=(
        baseline.FilePin(
            3_307,
            "91f3027714b55921305d9ae2661fac6b329373cacf11ad4bad80e884c6a48fa8",
        ),
        baseline.FilePin(
            3_307,
            "da5677b0a0ce433da7874d89ed09b66fdd014b5d635db0d374acd35275be9ee3",
        ),
    ),
    rom_sha256=ROUND8_ROM_SHA256,
    required_assembly_paths=(
        "asm/schala_sidecar_sha256_profile1_round8.asm",
        "asm/schala_sidecar_sha256_profile1_round8_benchmark.asm",
        "asm/schala_sidecar_sha256_sigma_tables.asm",
    ),
)


class Round8EvidenceError(RuntimeError):
    """Raised when round8 evidence cannot be accepted fail closed."""


@dataclasses.dataclass(frozen=True)
class Round8CandidatePins:
    runtime: baseline.RuntimePins
    state_sha256: tuple[str, str]
    core_state_sha256: tuple[str, str]
    result_sha256: str
    scratch_with_guards_sha256: str
    sram_sha256: str
    elapsed_frames: tuple[int, int, int]
    final_frame: int
    core_difference_count: int
    bounded_serializer_difference_count: int
    irrelevant_wram_difference_count: int
    generated_table: baseline.FilePin
    table_generator_source: baseline.FilePin
    stop_threshold_frames: int = STOP_THRESHOLD_FRAMES


DEFAULT_ROUND8_PINS = Round8CandidatePins(
    runtime=ROUND8_RUNTIME_PINS,
    state_sha256=(
        "591218c3f4ce8bb19aba51163850d84416a5d1058791a2fde5bf55bd76a0623f",
        "6974a1f1a50d365b5778963807bd35b7060ff1366f44a98aafe21eb2b398a808",
    ),
    core_state_sha256=(
        "223ae3c3c3b5aec26b6949a3972d02765cef1e5662d3b025bfe19fad6394c48e",
        "8ff1733af3ee1c1b7bd81004dec0861316b9deb236e21603c353b66aa51dd01f",
    ),
    result_sha256=ROUND8_RESULT_SHA256,
    scratch_with_guards_sha256=ROUND8_SCRATCH_GUARDS_SHA256,
    sram_sha256=state_inspector.ZERO_SRAM_SHA256,
    elapsed_frames=(68, 69, 69),
    final_frame=207,
    core_difference_count=130_502,
    bounded_serializer_difference_count=8,
    irrelevant_wram_difference_count=130_494,
    generated_table=baseline.FilePin(
        62_520,
        "7455ce0e13d243cee1c8bd0a36c8ef3582f1df4176a155f837300b907b98e61a",
    ),
    table_generator_source=baseline.FilePin(
        11_861,
        "d48aa84d93b8cd8f20229839439eca08b651167f198a9dd826b94f1614ff97d8",
    ),
)


GeneratedTableValidator = Callable[
    [pathlib.Path],
    Mapping[str, object],
]


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise Round8EvidenceError(detail)


def _workspace_windows_relative(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise Round8EvidenceError(
            f"round8 runtime path escapes the workspace: {path}"
        ) from exc
    return str(relative)


def _named_spans(
    reproducibility: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    raw = reproducibility.get("defined_evidence_spans")
    _require(isinstance(raw, list), "defined evidence spans are missing")
    result: dict[str, Mapping[str, object]] = {}
    for item in raw:
        _require(isinstance(item, Mapping), "defined evidence span is malformed")
        name = item.get("name")
        _require(isinstance(name, str), "defined evidence span has no name")
        _require(name not in result, f"duplicate defined evidence span {name}")
        result[name] = item
    _require(
        set(result) == {"sram", "scratch_with_guards", "result_record"},
        "defined evidence span set changed",
    )
    return result


def validate_round8_log(
    path: pathlib.Path,
    pin: baseline.FilePin,
    *,
    run_index: int,
    base_config: pathlib.Path,
    run_config: pathlib.Path,
    core: pathlib.Path,
    sram: pathlib.Path,
    state: pathlib.Path,
    pins: baseline.RuntimePins,
) -> tuple[pathlib.Path, dict[str, object], dict[str, int]]:
    """Validate the round8 run's exact relative-config log convention."""
    path = baseline.validate_private_file(path, f"round8 run {run_index} log")
    record = baseline.validate_pin(
        path,
        pin,
        f"round8 run {run_index} log",
    )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise Round8EvidenceError(
            f"round8 run {run_index} log is not UTF-8"
        ) from exc
    state_base = state.with_suffix("")
    required = (
        f"RetroArch {pins.retroarch_version} (Git {pins.retroarch_git})",
        f'Loading dynamic libretro core from: "{core.resolve()}".',
        (
            'Loading config: "'
            f'{_workspace_windows_relative(base_config)}".'
        ),
        (
            'Appending config: "'
            f'{_workspace_windows_relative(run_config)}".'
        ),
        f'Redirecting save file to "{sram.resolve()}".',
        f'Redirecting save state to "{state_base.resolve()}".',
        "[Content] Content loading skipped.",
        "[SRAM] Skipping SRAM load.",
        f'Auto save state to "{state.resolve()}" succeeded.',
    )
    for fragment in required:
        if fragment not in text:
            raise Round8EvidenceError(
                f"round8 run {run_index} log is missing: {fragment}"
            )
    durations = list(baseline.DURATION_RE.finditer(text))
    if len(durations) != 1:
        raise Round8EvidenceError(
            f"round8 run {run_index} log has no unique duration"
        )
    duration = {
        key: int(durations[0].group(key))
        for key in ("hours", "minutes", "seconds")
    }
    record["content_path_logged"] = False
    record["frontend_reported_duration"] = duration
    record["config_path_form"] = "workspace-relative-windows"
    return path, record, duration


def validate_generated_table(
    path: pathlib.Path,
    generator_source: pathlib.Path,
    *,
    pins: Round8CandidatePins,
    validator: GeneratedTableValidator,
) -> dict[str, object]:
    """Pin both deterministic generator inputs and its current output."""
    table_path = path.resolve()
    generator_path = generator_source.resolve()
    try:
        table_path.relative_to(WORKSPACE_ROOT)
        generator_path.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise Round8EvidenceError(
            "round8 generated-table closure must remain in the workspace"
        ) from exc
    table_record = baseline.validate_pin(
        table_path,
        pins.generated_table,
        "round8 generated sigma table",
    )
    generator_record = baseline.validate_pin(
        generator_path,
        pins.table_generator_source,
        "round8 sigma-table generator source",
    )
    try:
        raw_report = validator(table_path)
    except Exception as exc:
        raise Round8EvidenceError(
            f"round8 generated sigma table failed deterministic check: {exc}"
        ) from exc
    _require(
        isinstance(raw_report, Mapping),
        "round8 generated-table validator report is malformed",
    )
    report = dict(raw_report)
    expected = {
        "specification": "project-epoch-sha256-sigma-byte-tables-v1",
        "output_size": pins.generated_table.size,
        "output_sha256": pins.generated_table.sha256,
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
    for key, value in expected.items():
        _require(
            report.get(key) == value,
            f"round8 generated-table validator {key} mismatch",
        )
    return {
        "table": table_record,
        "generator_source": generator_record,
        "deterministic_check": report,
    }


def _validate_round8_identity(
    manifest: Mapping[str, object],
    pins: Round8CandidatePins,
) -> None:
    runs = manifest.get("runs")
    reproducibility = manifest.get("reproducibility")
    static = manifest.get("static_build")
    _require(isinstance(runs, list) and len(runs) == 2, "two runs are required")
    _require(
        isinstance(reproducibility, Mapping),
        "reproducibility report is missing",
    )
    _require(isinstance(static, Mapping), "static build report is missing")
    _require(
        static.get("rom", {}).get("sha256") == pins.runtime.rom_sha256,
        "round8 ROM identity mismatch",
    )
    _require(
        static.get("manifest", {}).get("sha256")
        == pins.runtime.static_manifest.sha256,
        "round8 source-pinned static manifest identity mismatch",
    )

    decoded_results: list[Mapping[str, object]] = []
    for index, run in enumerate(runs):
        _require(isinstance(run, Mapping), f"run {index + 1} is malformed")
        state = run.get("state")
        inspector = run.get("inspector")
        _require(
            isinstance(state, Mapping) and isinstance(inspector, Mapping),
            f"run {index + 1} identity is missing",
        )
        _require(
            state.get("sha256") == pins.state_sha256[index],
            f"run {index + 1} RASTATE pin mismatch",
        )
        core_state = inspector.get("core_state")
        result = inspector.get("result")
        memory = inspector.get("memory_layout")
        _require(
            isinstance(core_state, Mapping)
            and isinstance(result, Mapping)
            and isinstance(memory, Mapping),
            f"run {index + 1} inspector report is incomplete",
        )
        _require(
            core_state.get("sha256") == pins.core_state_sha256[index],
            f"run {index + 1} core-state pin mismatch",
        )
        _require(
            result.get("record_sha256") == pins.result_sha256,
            f"run {index + 1} result-record pin mismatch",
        )
        _require(
            result.get("scratch_with_guards_sha256")
            == pins.scratch_with_guards_sha256,
            f"run {index + 1} scratch/guard pin mismatch",
        )
        _require(
            memory.get("sram_sha256") == pins.sram_sha256,
            f"run {index + 1} SRAM pin mismatch",
        )
        _require(
            memory.get("sram_all_zero") is True,
            f"run {index + 1} SRAM is not all zero",
        )
        slots = result.get("slots")
        _require(
            isinstance(slots, list) and len(slots) == 3,
            f"run {index + 1} slot results are missing",
        )
        elapsed = tuple(slot.get("elapsed_frames") for slot in slots)
        _require(
            elapsed == pins.elapsed_frames,
            f"run {index + 1} round8 frame contract mismatch",
        )
        _require(
            result.get("final_frame") == pins.final_frame,
            f"run {index + 1} completion frame mismatch",
        )
        decoded_results.append(result)
    _require(
        decoded_results[0] == decoded_results[1],
        "decoded round8 results differ between runs",
    )

    spans = _named_spans(reproducibility)
    _require(
        spans["result_record"].get("sha256") == pins.result_sha256,
        "cross-run result span hash mismatch",
    )
    _require(
        spans["scratch_with_guards"].get("sha256")
        == pins.scratch_with_guards_sha256,
        "cross-run scratch/guard span hash mismatch",
    )
    _require(
        spans["sram"].get("sha256") == pins.sram_sha256,
        "cross-run SRAM span hash mismatch",
    )
    _require(
        reproducibility.get("full_core_state_difference_count")
        == pins.core_difference_count,
        "round8 full-core difference count mismatch",
    )
    bounded = reproducibility.get("bounded_non_wram_difference")
    irrelevant = reproducibility.get("uncleared_irrelevant_wram")
    _require(
        isinstance(bounded, Mapping) and isinstance(irrelevant, Mapping),
        "bounded difference reports are missing",
    )
    _require(
        bounded.get("differing_byte_count")
        == pins.bounded_serializer_difference_count,
        "round8 serializer difference count mismatch",
    )
    _require(
        irrelevant.get("differing_byte_count")
        == pins.irrelevant_wram_difference_count,
        "round8 irrelevant-WRAM difference count mismatch",
    )
    _require(
        irrelevant.get("defined_evidence_difference_count") == 0,
        "round8 defined evidence contains a WRAM difference",
    )
    _require(
        reproducibility.get("unaccounted_difference_count") == 0,
        "round8 captures contain an unaccounted difference",
    )


def build_stop_gate(
    elapsed_frames: Sequence[int],
    *,
    threshold_frames: int,
) -> dict[str, object]:
    """Apply the exact predeclared strict-greater-than-30 stop rule."""
    _require(
        threshold_frames == STOP_THRESHOLD_FRAMES,
        "round8 stop threshold must remain exactly 30 frames",
    )
    _require(
        len(elapsed_frames) == 3
        and all(type(value) is int and value >= 0 for value in elapsed_frames),
        "round8 stop-gate frame vector is malformed",
    )
    triggering_slots = [
        index
        for index, frames in enumerate(elapsed_frames, start=1)
        if frames > threshold_frames
    ]
    _require(
        bool(triggering_slots),
        "round8 capture did not trigger the required >30-frame stop gate",
    )
    return {
        "predeclared": True,
        "scope": "single-slot-digest-elapsed-frames",
        "comparison": "strictly-greater-than",
        "threshold_frames": threshold_frames,
        "observed_elapsed_frames": list(elapsed_frames),
        "triggering_slots": triggering_slots,
        "triggered": True,
        "classification": STOP_GATE_CLASSIFICATION,
        "further_optimization_authorized": False,
        "integration_authorized": False,
        "production_authorized": False,
        "required_explicit_decision": {
            "status": "required-before-further-work",
            "decision_class": REQUIRED_DECISION_CLASS,
            "binding_profile_or_threat_model_route": (
                "explicitly revise and document the binding profile or threat "
                "model before selecting an acceptable primitive"
            ),
            "algorithm_route": (
                "explicitly select a different algorithm and document how it "
                "meets the chosen binding guarantees"
            ),
        },
    }


def build_in_memory(
    *,
    static_manifest: pathlib.Path = DEFAULT_STATIC_MANIFEST,
    states: Sequence[pathlib.Path] = DEFAULT_STATES,
    logs: Sequence[pathlib.Path] = DEFAULT_LOGS,
    run_configs: Sequence[pathlib.Path] = DEFAULT_RUN_CONFIGS,
    generated_table: pathlib.Path = DEFAULT_GENERATED_TABLE,
    table_generator_source: pathlib.Path = DEFAULT_TABLE_GENERATOR_SOURCE,
    base_config: pathlib.Path = baseline.DEFAULT_BASE_CONFIG,
    retroarch_exe: pathlib.Path = baseline.DEFAULT_RETROARCH_EXE,
    core: pathlib.Path = baseline.DEFAULT_CORE,
    core_info: pathlib.Path = baseline.DEFAULT_CORE_INFO,
    output: pathlib.Path = DEFAULT_OUTPUT,
    pins: Round8CandidatePins = DEFAULT_ROUND8_PINS,
    inspector: baseline.Inspector = state_inspector.inspect_path,
    table_validator: GeneratedTableValidator = sigma_generator.check_include,
) -> baseline.RuntimeEvidenceResult:
    if len(states) != 2 or len(logs) != 2 or len(run_configs) != 2:
        raise Round8EvidenceError(
            "exactly two round8 states, logs, and configs are required"
        )
    output = baseline.validate_private_output(output)
    static_source, static = baseline.validate_static_build(
        static_manifest,
        pins.runtime,
    )
    rom_path = static["rom_path"]
    sram_path = static["sram_path"]
    expected_rom = (
        BENCHMARK_ROOT / "schala_sha256_profile1_round8_benchmark.sfc"
    )
    expected_sram = (
        BENCHMARK_ROOT / "schala_sha256_profile1_round8_benchmark.srm"
    )
    if pins is DEFAULT_ROUND8_PINS:
        _require(
            rom_path.resolve() == expected_rom.resolve(),
            "default round8 ROM path changed",
        )
        _require(
            sram_path.resolve() == expected_sram.resolve(),
            "default round8 SRAM path changed",
        )
        _require(
            generated_table.resolve() == DEFAULT_GENERATED_TABLE.resolve(),
            "default round8 generated-table path changed",
        )
        _require(
            table_generator_source.resolve()
            == DEFAULT_TABLE_GENERATOR_SOURCE.resolve(),
            "default round8 table-generator path changed",
        )

    generated = validate_generated_table(
        generated_table,
        table_generator_source,
        pins=pins,
        validator=table_validator,
    )
    source_paths = {
        record["path"] for record in static["assembly_sources"]
    }
    _require(
        generated["table"]["path"] in source_paths,
        "generated sigma table is outside the static source closure",
    )

    toolchain = baseline.validate_runtime_tools(
        retroarch_exe,
        core,
        core_info,
        pins.runtime,
    )
    base_config, base_record = baseline.validate_base_config(
        base_config,
        pins.runtime,
    )
    resolved_states = [
        baseline.validate_private_file(
            path,
            f"round8 run {index} RASTATE",
        )
        for index, path in enumerate(states, start=1)
    ]
    _require(
        len(set(resolved_states)) == 2,
        "round8 runtime states must be distinct files",
    )

    run_entries: list[dict[str, object]] = []
    reports: list[dict[str, object]] = []
    cores: list[bytes] = []
    for offset in range(2):
        run_index = offset + 1
        config_path, config_record = baseline.validate_run_config(
            run_configs[offset],
            pins.runtime.run_configs[offset],
            run_index=run_index,
            sram_path=sram_path,
            state_path=resolved_states[offset],
        )
        log_path, log_record, duration = validate_round8_log(
            logs[offset],
            pins.runtime.logs[offset],
            run_index=run_index,
            base_config=base_config,
            run_config=config_path,
            core=core,
            sram=sram_path,
            state=resolved_states[offset],
            pins=pins.runtime,
        )
        report, _rastate, core_state = baseline.inspect_run(
            resolved_states[offset],
            inspector=inspector,
            pins=pins.runtime,
        )
        reports.append(report)
        cores.append(core_state)
        run_entries.append(
            {
                "run": run_index,
                "config": config_record,
                "log": log_record,
                "state": baseline.file_record(resolved_states[offset]),
                "inspector": report,
                "command": baseline.normalized_run_command(
                    retroarch_exe=retroarch_exe,
                    base_config=base_config,
                    run_config=config_path,
                    core=core,
                    log=log_path,
                    rom=rom_path,
                    max_frames=pins.runtime.max_frames,
                ),
                "max_frames": pins.runtime.max_frames,
                "frontend_reported_duration": duration,
            }
        )

    reproducibility = baseline.compare_runs(
        reports,
        cores,
        pins=pins.runtime,
    )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "builder_version": VERSION,
        "artifact_class": (
            "standalone-sha256-round8-candidate-runtime-evidence"
        ),
        "status": "verified-runtime-standalone-round8-candidate-stopped",
        "evidence_level": "verified-runtime-standalone-round8-candidate",
        "private_only": True,
        "production_input": False,
        "chrono_trigger_input_read": False,
        "project_epoch_hooks_installed": False,
        "project_epoch_allocations_approved": False,
        "output": {
            "path": baseline.display_path(output),
            "self_hash_embedded": False,
        },
        "builder_source": baseline.file_record(
            pathlib.Path(__file__).resolve()
        ),
        "baseline_runtime_validator_source": baseline.file_record(
            pathlib.Path(baseline.__file__).resolve()
        ),
        "inspector_source": baseline.file_record(
            pathlib.Path(state_inspector.__file__).resolve()
        ),
        "static_build": {
            "manifest": static["manifest"],
            "rom": static["rom"],
            "sram": static["sram"],
            "assembly_sources": static["assembly_sources"],
            "builder_source": static["builder_source"],
            "host_audit_status": static_source["host_audit"]["status"],
            "production_guard_approval": False,
            "source_closure_current_and_exact": True,
            "historical_drifted_manifest_accepted": False,
        },
        "generated_sigma_table": generated,
        "runtime_toolchain": toolchain,
        "base_config": base_record,
        "runs": run_entries,
        "reproducibility": reproducibility,
    }
    _validate_round8_identity(manifest, pins)

    stop_gate = build_stop_gate(
        pins.elapsed_frames,
        threshold_frames=pins.stop_threshold_frames,
    )
    seconds = [
        round(frames / pins.runtime.frames_per_second, 6)
        for frames in pins.elapsed_frames
    ]
    timing = manifest["reproducibility"]["timing"]
    timing.update(
        {
            "slot_elapsed_frames": list(pins.elapsed_frames),
            "slot_elapsed_seconds": seconds,
            "completion_frame": pins.final_frame,
            "completion_seconds": round(
                pins.final_frame / pins.runtime.frames_per_second,
                6,
            ),
            "classification": STOP_GATE_CLASSIFICATION,
            "production_timing_approved": False,
            "integration_timing_approved": False,
        }
    )
    manifest["round8_candidate"] = {
        "candidate_only": True,
        "baseline_or_fast_behavior_or_pins_modified": False,
        "correct_standalone_for_pinned_zero_slots": True,
        "elapsed_frames": list(pins.elapsed_frames),
        "elapsed_seconds": seconds,
        "completion_frame": pins.final_frame,
        "result_record_sha256": pins.result_sha256,
        "scratch_with_guards_sha256": pins.scratch_with_guards_sha256,
        "sram_sha256": pins.sram_sha256,
        "integration_approved": False,
        "production_approved": False,
    }
    manifest["stop_gate"] = stop_gate
    manifest["conclusion"] = {
        "round8_correct_for_pinned_zero_slots": True,
        "valid_call_abi_preserved": True,
        "invalid_call_failed_closed": True,
        "scratch_guards_preserved": True,
        "defined_evidence_reproduced_twice": True,
        "stop_gate_triggered": True,
        "integration_approved": False,
        "production_timing_approved": False,
        "explicit_decision_required": REQUIRED_DECISION_CLASS,
        "decision": (
            "stop: the correct standalone round8 candidate exceeded the "
            "predeclared 30-frame ceiling and cannot proceed without an "
            "explicit binding-profile/threat-model or algorithm decision"
        ),
    }
    manifest["reproduction"] = {
        "working_directory": ".",
        "manifest_command": [
            "python",
            "tools/build_sha256_65816_round8_runtime_evidence_manifest.py",
        ],
        "generated_table_check_command": [
            "python",
            "tools/generate_schala_sha256_65816_sigma_tables.py",
            "--check",
        ],
        "run_commands": [entry["command"] for entry in run_entries],
        "historical_command_not_embedded_as_a_state_field": True,
    }
    manifest["limitations"] = [
        "standalone original synthetic cartridge only",
        "all-zero 8 KiB SRAM vectors only",
        "minimal synthetic NMI handler only",
        "frame counts are coarse NMI-frame measurements, not cycle traces",
        "does not approve any Chrono Trigger hook or ROM allocation",
        "does not prove a Chrono Trigger WRAM scratch allocation",
        "does not approve save, load, New Game+, erase, or preview integration",
        "full-state hashes are not claimed deterministic; only named evidence spans are",
        "round8 remains a separate evidence-gated standalone candidate",
        "the strict greater-than-30-frame stop gate is triggered",
        "further optimization and integration require an explicit binding-profile/threat-model or algorithm decision",
        "does not supersede or weaken the pinned baseline or fast-candidate evidence paths",
    ]

    encoded = (
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return baseline.RuntimeEvidenceResult(
        manifest=manifest,
        manifest_bytes=encoded,
    )


def write_manifest(
    result: baseline.RuntimeEvidenceResult,
    output: pathlib.Path = DEFAULT_OUTPUT,
) -> pathlib.Path:
    return baseline.write_manifest(result, output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static-manifest",
        type=pathlib.Path,
        default=DEFAULT_STATIC_MANIFEST,
    )
    parser.add_argument(
        "--state",
        type=pathlib.Path,
        action="append",
        dest="states",
    )
    parser.add_argument(
        "--log",
        type=pathlib.Path,
        action="append",
        dest="logs",
    )
    parser.add_argument(
        "--run-config",
        type=pathlib.Path,
        action="append",
        dest="run_configs",
    )
    parser.add_argument(
        "--generated-table",
        type=pathlib.Path,
        default=DEFAULT_GENERATED_TABLE,
    )
    parser.add_argument(
        "--table-generator-source",
        type=pathlib.Path,
        default=DEFAULT_TABLE_GENERATOR_SOURCE,
    )
    parser.add_argument(
        "--base-config",
        type=pathlib.Path,
        default=baseline.DEFAULT_BASE_CONFIG,
    )
    parser.add_argument(
        "--retroarch-exe",
        type=pathlib.Path,
        default=baseline.DEFAULT_RETROARCH_EXE,
    )
    parser.add_argument(
        "--core",
        type=pathlib.Path,
        default=baseline.DEFAULT_CORE,
    )
    parser.add_argument(
        "--core-info",
        type=pathlib.Path,
        default=baseline.DEFAULT_CORE_INFO,
    )
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_in_memory(
        static_manifest=args.static_manifest,
        states=args.states or DEFAULT_STATES,
        logs=args.logs or DEFAULT_LOGS,
        run_configs=args.run_configs or DEFAULT_RUN_CONFIGS,
        generated_table=args.generated_table,
        table_generator_source=args.table_generator_source,
        base_config=args.base_config,
        retroarch_exe=args.retroarch_exe,
        core=args.core,
        core_info=args.core_info,
        output=args.output,
    )
    output = write_manifest(result, args.output)
    print(f"runs={len(result.manifest['runs'])}")
    print(
        "manifest_sha256="
        f"{hashlib.sha256(result.manifest_bytes).hexdigest()}"
    )
    print(f"stop_gate={result.manifest['stop_gate']['classification']}")
    print(f"verified={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
