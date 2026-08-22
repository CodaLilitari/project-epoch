#!/usr/bin/env python3
"""Build the isolated runtime manifest for the fast SHA-256 candidate.

This path deliberately uses a separate static-manifest pin, source closure,
ROM identity, runtime captures, and timing contract.  It imports the baseline
runtime validator as a library but never changes or relaxes its default pins.
No Chrono Trigger ROM, save, movie, or state is accepted.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
from collections.abc import Mapping, Sequence

import build_sha256_65816_runtime_evidence_manifest as baseline
import inspect_schala_sha256_65816_benchmark_state as state_inspector


VERSION = "1.0.0"

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (WORKSPACE_ROOT / "private").resolve()
BENCHMARK_ROOT = PRIVATE_ROOT / "test_runs" / "sha256_65c816"

DEFAULT_STATIC_MANIFEST = (
    BENCHMARK_ROOT
    / "schala_sha256_profile1_fast_benchmark.current_sources.manifest.json"
)
DEFAULT_STATES = (
    BENCHMARK_ROOT
    / "fast_runtime_run1"
    / "schala_sha256_profile1_fast_benchmark.state.auto",
    BENCHMARK_ROOT
    / "fast_runtime_run2"
    / "schala_sha256_profile1_fast_benchmark.state.auto",
)
DEFAULT_LOGS = (
    BENCHMARK_ROOT / "fast_runtime_run1" / "benchmark.log",
    BENCHMARK_ROOT / "fast_runtime_run2" / "benchmark.log",
)
DEFAULT_RUN_CONFIGS = (
    BENCHMARK_ROOT / "retroarch-fast-benchmark-run1.cfg",
    BENCHMARK_ROOT / "retroarch-fast-benchmark-run2.cfg",
)
DEFAULT_OUTPUT = BENCHMARK_ROOT / "fast_runtime_evidence_manifest.json"

FAST_ROM_SHA256 = (
    "c0aab3909bf6068090d778c1cd3eae92c4093177b73fdb2bf19590480c6c22da"
)
FAST_RESULT_SHA256 = (
    "92a12e353b112ffa03f86566cf59e15354b758a2981e80d5a1b7f259f8ab5bfe"
)
FAST_SCRATCH_GUARDS_SHA256 = (
    "c6586caf1a3ba9032a06b084611f156d75129c42c71f66de32b7fc54a734c038"
)


FAST_RUNTIME_PINS = dataclasses.replace(
    baseline.DEFAULT_PINS,
    static_manifest=baseline.FilePin(
        8_705,
        "0beb9e3e23cf060de7b6c69170cefd235b7ebf36caf45b30f87eef63bba58231",
    ),
    run_configs=(
        baseline.FilePin(
            315,
            "ff8423fa4d251492d46d267435bb24d727e889c5f73a9136493844b799a7ffc9",
        ),
        baseline.FilePin(
            315,
            "271773a9d79056f0449207493c79fa85a5827248e5873b1b5df39899d93b5509",
        ),
    ),
    logs=(
        baseline.FilePin(
            3_258,
            "49f9e3075572ad90c5322af2fac61afe04bca712dca28ec4ae86075ed4ca0910",
        ),
        baseline.FilePin(
            3_258,
            "99926cf38e7dead6e3fc99ce6487db6ac1a547ae2e2e8f1e9fb28f56bf4ba861",
        ),
    ),
    rom_sha256=FAST_ROM_SHA256,
    required_assembly_paths=(
        "asm/schala_sidecar_sha256_profile1_fast.asm",
        "asm/schala_sidecar_sha256_profile1_fast_benchmark.asm",
    ),
)


class FastCandidateEvidenceError(RuntimeError):
    """Raised when fast-candidate evidence cannot be accepted."""


@dataclasses.dataclass(frozen=True)
class FastCandidatePins:
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
    baseline_elapsed_frames: tuple[int, int, int]


DEFAULT_FAST_PINS = FastCandidatePins(
    runtime=FAST_RUNTIME_PINS,
    state_sha256=(
        "38f323db1e717778780f61d4c8c31f198b8b95f23f85fce58b5dc2dc706cae4a",
        "a87fc78b0f9d2e2e1ed2d8fbdd94d9971c54170193e4216ace11497ae3a71be4",
    ),
    core_state_sha256=(
        "e1d572b2a34c9c6fe95fc3aa3f5a72135afe600ec29db65dc6f0cc58fecc6077",
        "d3dd87b72f5b64884d685968b64f772f64737d02f28a8b7f31028c39ad616f0d",
    ),
    result_sha256=FAST_RESULT_SHA256,
    scratch_with_guards_sha256=FAST_SCRATCH_GUARDS_SHA256,
    sram_sha256=state_inspector.ZERO_SRAM_SHA256,
    elapsed_frames=(123, 123, 124),
    final_frame=371,
    core_difference_count=130_481,
    bounded_serializer_difference_count=8,
    irrelevant_wram_difference_count=130_473,
    baseline_elapsed_frames=(366, 367, 366),
)


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise FastCandidateEvidenceError(detail)


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


def _workspace_windows_relative(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise FastCandidateEvidenceError(
            f"fast runtime path escapes the workspace: {path}"
        ) from exc
    return str(relative)


def validate_fast_log(
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
    """Validate the fast run's exact relative-config logging convention."""
    path = baseline.validate_private_file(path, f"fast run {run_index} log")
    record = baseline.validate_pin(
        path,
        pin,
        f"fast run {run_index} log",
    )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FastCandidateEvidenceError(
            f"fast run {run_index} log is not UTF-8"
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
            raise FastCandidateEvidenceError(
                f"fast run {run_index} log is missing: {fragment}"
            )
    durations = list(baseline.DURATION_RE.finditer(text))
    if len(durations) != 1:
        raise FastCandidateEvidenceError(
            f"fast run {run_index} log has no unique duration"
        )
    duration = {
        key: int(durations[0].group(key))
        for key in ("hours", "minutes", "seconds")
    }
    record["content_path_logged"] = False
    record["frontend_reported_duration"] = duration
    record["config_path_form"] = "workspace-relative-windows"
    return path, record, duration


def _validate_fast_identity(
    manifest: Mapping[str, object],
    pins: FastCandidatePins,
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
        "fast ROM identity mismatch",
    )
    _require(
        static.get("manifest", {}).get("sha256")
        == pins.runtime.static_manifest.sha256,
        "current-source static manifest identity mismatch",
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
        slots = result.get("slots")
        _require(
            isinstance(slots, list) and len(slots) == 3,
            f"run {index + 1} slot results are missing",
        )
        elapsed = tuple(slot.get("elapsed_frames") for slot in slots)
        _require(
            elapsed == pins.elapsed_frames,
            f"run {index + 1} fast frame contract mismatch",
        )
        _require(
            result.get("final_frame") == pins.final_frame,
            f"run {index + 1} completion frame mismatch",
        )
        decoded_results.append(result)
    _require(
        decoded_results[0] == decoded_results[1],
        "decoded fast results differ between runs",
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
        "fast full-core difference count mismatch",
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
        "fast serializer difference count mismatch",
    )
    _require(
        irrelevant.get("differing_byte_count")
        == pins.irrelevant_wram_difference_count,
        "fast irrelevant-WRAM difference count mismatch",
    )
    _require(
        irrelevant.get("defined_evidence_difference_count") == 0,
        "fast defined evidence contains a WRAM difference",
    )
    _require(
        reproducibility.get("unaccounted_difference_count") == 0,
        "fast captures contain an unaccounted difference",
    )


def build_in_memory(
    *,
    static_manifest: pathlib.Path = DEFAULT_STATIC_MANIFEST,
    states: Sequence[pathlib.Path] = DEFAULT_STATES,
    logs: Sequence[pathlib.Path] = DEFAULT_LOGS,
    run_configs: Sequence[pathlib.Path] = DEFAULT_RUN_CONFIGS,
    base_config: pathlib.Path = baseline.DEFAULT_BASE_CONFIG,
    retroarch_exe: pathlib.Path = baseline.DEFAULT_RETROARCH_EXE,
    core: pathlib.Path = baseline.DEFAULT_CORE,
    core_info: pathlib.Path = baseline.DEFAULT_CORE_INFO,
    output: pathlib.Path = DEFAULT_OUTPUT,
    pins: FastCandidatePins = DEFAULT_FAST_PINS,
    inspector: baseline.Inspector = state_inspector.inspect_path,
) -> baseline.RuntimeEvidenceResult:
    if len(states) != 2 or len(logs) != 2 or len(run_configs) != 2:
        raise FastCandidateEvidenceError(
            "exactly two fast states, logs, and configs are required"
        )
    output = baseline.validate_private_output(output)
    static_source, static = baseline.validate_static_build(
        static_manifest,
        pins.runtime,
    )
    rom_path = static["rom_path"]
    sram_path = static["sram_path"]
    expected_rom = (
        BENCHMARK_ROOT / "schala_sha256_profile1_fast_benchmark.sfc"
    )
    expected_sram = (
        BENCHMARK_ROOT / "schala_sha256_profile1_fast_benchmark.srm"
    )
    if pins is DEFAULT_FAST_PINS:
        _require(
            rom_path.resolve() == expected_rom.resolve(),
            "default fast ROM path changed",
        )
        _require(
            sram_path.resolve() == expected_sram.resolve(),
            "default fast SRAM path changed",
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
            f"fast run {index} RASTATE",
        )
        for index, path in enumerate(states, start=1)
    ]
    _require(
        len(set(resolved_states)) == 2,
        "fast runtime states must be distinct files",
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
        log_path, log_record, duration = validate_fast_log(
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
            "standalone-sha256-fast-candidate-runtime-evidence"
        ),
        "status": "verified-runtime-standalone-fast-candidate",
        "evidence_level": (
            "verified-runtime-standalone-fast-candidate"
        ),
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
            "historical_drifted_manifest_accepted": False,
        },
        "runtime_toolchain": toolchain,
        "base_config": base_record,
        "runs": run_entries,
        "reproducibility": reproducibility,
    }
    _validate_fast_identity(manifest, pins)

    timing = manifest["reproducibility"]["timing"]
    elapsed = pins.elapsed_frames
    seconds = [
        round(frames / pins.runtime.frames_per_second, 6)
        for frames in elapsed
    ]
    speedups = [
        round(base_frames / fast_frames, 6)
        for base_frames, fast_frames in zip(
            pins.baseline_elapsed_frames,
            elapsed,
            strict=True,
        )
    ]
    timing.update(
        {
            "slot_elapsed_frames": list(elapsed),
            "slot_elapsed_seconds": seconds,
            "completion_frame": pins.final_frame,
            "completion_seconds": round(
                pins.final_frame / pins.runtime.frames_per_second,
                6,
            ),
            "classification": (
                "measured-fast-candidate-not-production-approved"
            ),
            "production_timing_approved": False,
        }
    )
    manifest["fast_candidate"] = {
        "candidate_only": True,
        "baseline_behavior_or_pins_modified": False,
        "elapsed_frames": list(elapsed),
        "elapsed_seconds": seconds,
        "baseline_elapsed_frames": list(pins.baseline_elapsed_frames),
        "speedup_over_correctness_baseline": speedups,
        "result_record_sha256": pins.result_sha256,
        "scratch_with_guards_sha256": (
            pins.scratch_with_guards_sha256
        ),
        "sram_sha256": pins.sram_sha256,
        "production_approved": False,
    }
    manifest["conclusion"] = {
        "fast_candidate_correct_for_pinned_zero_slots": True,
        "valid_call_abi_preserved": True,
        "invalid_call_failed_closed": True,
        "scratch_guards_preserved": True,
        "defined_evidence_reproduced_twice": True,
        "production_timing_approved": False,
        "decision": (
            "fast candidate correctness and approximately threefold speedup "
            "accepted as standalone evidence only; no production promotion"
        ),
    }
    manifest["reproduction"] = {
        "working_directory": ".",
        "manifest_command": [
            "python",
            "tools/build_sha256_65816_fast_runtime_evidence_manifest.py",
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
        "fast implementation remains a separate evidence-gated candidate",
        "approximately two seconds per digest remains unapproved for production",
        "does not supersede or weaken the pinned correctness baseline",
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
    print(f"verified={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
