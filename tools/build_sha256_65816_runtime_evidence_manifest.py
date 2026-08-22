#!/usr/bin/env python3
"""Build the private two-run runtime manifest for the SHA-256 benchmark.

The builder consumes only the original standalone benchmark artifacts and
current-bsnes RASTATE captures.  It does not read a Chrono Trigger ROM, SRM,
movie, or state.  Both captures must pass the dedicated state inspector and
must agree byte-for-byte in every defined evidence span.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
from collections.abc import Callable, Mapping, Sequence

import inspect_schala_sha256_65816_benchmark_state as state_inspector
import retroarch_rastate


VERSION = "1.0.0"

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (WORKSPACE_ROOT / "private").resolve()
BENCHMARK_ROOT = PRIVATE_ROOT / "test_runs" / "sha256_65c816"

DEFAULT_STATIC_MANIFEST = (
    BENCHMARK_ROOT / "schala_sha256_profile1_benchmark.manifest.json"
)
DEFAULT_ROM = BENCHMARK_ROOT / "schala_sha256_profile1_benchmark.sfc"
DEFAULT_SRAM = BENCHMARK_ROOT / "schala_sha256_profile1_benchmark.srm"
DEFAULT_BASE_CONFIG = (
    PRIVATE_ROOT
    / "test_runs"
    / "retroarch"
    / "current"
    / "retroarch-current-null.cfg"
)
DEFAULT_RUN_CONFIGS = (
    BENCHMARK_ROOT / "retroarch-benchmark-run1.cfg",
    BENCHMARK_ROOT / "retroarch-benchmark-run2.cfg",
)
DEFAULT_LOGS = (
    BENCHMARK_ROOT / "runtime_run1" / "benchmark.log",
    BENCHMARK_ROOT / "runtime_run2" / "benchmark.log",
)
DEFAULT_STATES = (
    BENCHMARK_ROOT
    / "runtime_run1"
    / "schala_sha256_profile1_benchmark.state.auto",
    BENCHMARK_ROOT
    / "runtime_run2"
    / "schala_sha256_profile1_benchmark.state.auto",
)
DEFAULT_RETROARCH_EXE = pathlib.Path(
    r"private\tools\RetroArch-1.22.2\retroarch.exe"
)
DEFAULT_CORE = pathlib.Path(
    r"private\tools\RetroArch-1.22.2\cores\bsnes_libretro.dll"
)
DEFAULT_CORE_INFO = pathlib.Path(
    r"private\tools\RetroArch-1.22.2\info\bsnes_libretro.info"
)
DEFAULT_OUTPUT = BENCHMARK_ROOT / "runtime_evidence_manifest.json"

EXPECTED_STATIC_MANIFEST_SHA256 = (
    "8cffbacdacb28424aa64ceae9eee1e0038a76395f2cfac869e88f4bdffbd004b"
)
EXPECTED_ROM_SHA256 = (
    "e438143c95006f587fc20e74ea1bb18407ff726abe0cb8cda922b65740992bdd"
)
EXPECTED_ZERO_SRAM_SHA256 = state_inspector.ZERO_SRAM_SHA256

CFG_LINE_RE = re.compile(
    r'^(?P<key>[A-Za-z0-9_]+)\s*=\s*"(?P<value>[^"]*)"$'
)
INFO_LINE_RE = re.compile(
    r"^(?P<key>[A-Za-z0-9_]+)\s*=\s*(?P<value>.+)$"
)
DURATION_RE = re.compile(
    r"Content ran for a total of: "
    r"(?P<hours>\d{2}) hours, (?P<minutes>\d{2}) minutes, "
    r"(?P<seconds>\d{2}) seconds\."
)


class RuntimeEvidenceError(RuntimeError):
    """Raised when runtime evidence cannot be accepted fail closed."""


@dataclasses.dataclass(frozen=True)
class FilePin:
    size: int
    sha256: str


@dataclasses.dataclass(frozen=True)
class RuntimePins:
    static_manifest: FilePin
    retroarch_exe: FilePin
    core: FilePin
    core_info: FilePin
    base_config: FilePin
    run_configs: tuple[FilePin, FilePin]
    logs: tuple[FilePin, FilePin]
    rom_size: int = 0x800000
    rom_sha256: str = EXPECTED_ROM_SHA256
    sram_size: int = 0x2000
    sram_sha256: str = EXPECTED_ZERO_SRAM_SHA256
    rastate_size: int = 290_448
    core_state_size: int = 290_423
    serializer_version: str = "115.1"
    retroarch_version: str = "1.22.2"
    retroarch_git: str = "69a4f0e"
    core_info_version: str = "115"
    frames_per_second: float = 60.10
    max_frames: int = 1800
    nondeterministic_core_start: int = 0x021E
    nondeterministic_core_end: int = 0x0226
    require_exact_nondeterministic_core_span: bool = True
    require_irrelevant_wram_difference: bool = True
    required_assembly_paths: tuple[str, ...] = (
        "asm/schala_sidecar_sha256_profile1.asm",
        "asm/schala_sidecar_sha256_profile1_benchmark.asm",
    )
    required_static_builder_path: str | None = (
        "tools/build_sha256_65816_standalone_benchmark.py"
    )


DEFAULT_PINS = RuntimePins(
    static_manifest=FilePin(
        8_623,
        EXPECTED_STATIC_MANIFEST_SHA256,
    ),
    retroarch_exe=FilePin(
        18_641_482,
        "81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a",
    ),
    core=FilePin(
        5_609_890,
        "003c7de04adef5f64fa106ef5175a0f66b08032001bde0383af97c5e5b81d470",
    ),
    core_info=FilePin(
        4_193,
        "fc6f9bb67e99848bfcad99e5e4bb028a9ce998d3bbd0195fded36edef5ed1506",
    ),
    base_config=FilePin(
        974,
        "ca07bf904bc1273c0b2dbce047dfe7cbb1f0f6a9fa4ce4fd8cbce9bc5192544d",
    ),
    run_configs=(
        FilePin(
            310,
            "3c3c359303a06639cf7258992c32727887dc41666aec1e44b3f0af3671589c6e",
        ),
        FilePin(
            310,
            "faf5ef95da4a1ebee80bb92148d402ed168bcf73bcb738efc5085b96f712c836",
        ),
    ),
    logs=(
        FilePin(
            3_259,
            "57bdb464456c60bc9af92a0e1ebd75192195453e93df2f57a3ab8ca2d5eee34e",
        ),
        FilePin(
            3_259,
            "22f7b173136f71c27d331e1d33bac965cd431a1bdfff60b2b41662eb5c2e15bd",
        ),
    ),
)


@dataclasses.dataclass(frozen=True)
class RuntimeEvidenceResult:
    manifest: Mapping[str, object]
    manifest_bytes: bytes


Inspector = Callable[[pathlib.Path], Mapping[str, object]]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workspace_relative(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise RuntimeEvidenceError(
            f"path must remain below the workspace: {path}"
        ) from exc
    return relative.as_posix()


def display_path(path: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def validate_private_file(path: pathlib.Path, label: str) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise RuntimeEvidenceError(
            f"{label} must remain below private/: {path}"
        ) from exc
    if not resolved.is_file():
        raise RuntimeEvidenceError(f"{label} is missing: {resolved}")
    return resolved


def validate_private_output(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise RuntimeEvidenceError(
            f"output must remain below private/: {path}"
        ) from exc
    if resolved.suffix.lower() != ".json":
        raise RuntimeEvidenceError("runtime manifest output must be JSON")
    return resolved


def file_record(path: pathlib.Path) -> dict[str, object]:
    return {
        "path": display_path(path),
        "size": path.stat().st_size,
        "sha256": sha256_path(path),
    }


def validate_pin(
    path: pathlib.Path,
    pin: FilePin,
    label: str,
) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeEvidenceError(f"{label} is missing: {path}")
    size = path.stat().st_size
    if size != pin.size:
        raise RuntimeEvidenceError(
            f"{label} size mismatch: expected {pin.size}, got {size}"
        )
    digest = sha256_path(path)
    if digest != pin.sha256:
        raise RuntimeEvidenceError(
            f"{label} SHA-256 mismatch: expected {pin.sha256}, got {digest}"
        )
    return {
        "path": display_path(path),
        "size": size,
        "sha256": digest,
    }


def _workspace_record_path(value: object, label: str) -> pathlib.Path:
    if not isinstance(value, str) or not value:
        raise RuntimeEvidenceError(f"{label} path is missing")
    pure = pathlib.PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise RuntimeEvidenceError(f"{label} path is not normalized: {value}")
    resolved = (WORKSPACE_ROOT / pathlib.Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise RuntimeEvidenceError(
            f"{label} path escapes the workspace: {value}"
        ) from exc
    return resolved


def _validate_manifest_file_record(
    record: object,
    label: str,
) -> tuple[pathlib.Path, dict[str, object]]:
    if not isinstance(record, Mapping):
        raise RuntimeEvidenceError(f"{label} record is missing")
    path = _workspace_record_path(record.get("path"), label)
    if not path.is_file():
        raise RuntimeEvidenceError(f"{label} is missing: {path}")
    expected_size = record.get("size")
    expected_hash = record.get("sha256")
    if type(expected_size) is not int or not isinstance(expected_hash, str):
        raise RuntimeEvidenceError(f"{label} record is malformed")
    actual = file_record(path)
    if (
        actual["size"] != expected_size
        or actual["sha256"] != expected_hash
    ):
        raise RuntimeEvidenceError(f"{label} no longer matches its manifest")
    return path, actual


def validate_static_build(
    path: pathlib.Path,
    pins: RuntimePins,
) -> tuple[dict[str, object], dict[str, object]]:
    path = validate_private_file(path, "static build manifest")
    manifest_record = validate_pin(
        path, pins.static_manifest, "static build manifest"
    )
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeEvidenceError("static build manifest is not valid JSON") from exc
    if not isinstance(source, Mapping):
        raise RuntimeEvidenceError("static build manifest root is not an object")

    exact = {
        "schema_version": 1,
        "artifact_class": "standalone-original-diagnostic-rom",
        "status": "verified-static-host-build",
        "evidence_level": "verified-static",
        "private_only": True,
        "production_input": False,
        "chrono_trigger_source_rom_read": False,
        "project_epoch_production_catalogs_used": False,
        "project_epoch_hooks_installed": False,
    }
    for key, expected in exact.items():
        if source.get(key) != expected:
            raise RuntimeEvidenceError(
                f"static build manifest {key} is not {expected!r}"
            )

    guard = source.get("project_epoch_rom_write_guard")
    if (
        not isinstance(guard, Mapping)
        or guard.get("used_as_production_approval") is not False
    ):
        raise RuntimeEvidenceError(
            "static build must not claim production guard approval"
        )
    audit = source.get("host_audit")
    if (
        not isinstance(audit, Mapping)
        or audit.get("status") != "complete-diff-valid"
        or audit.get("all_changed_bytes_declared") is not True
    ):
        raise RuntimeEvidenceError("static complete-diff audit is not valid")

    outputs = source.get("outputs")
    if not isinstance(outputs, Mapping):
        raise RuntimeEvidenceError("static output records are missing")
    rom_path, rom_record = _validate_manifest_file_record(
        outputs.get("rom"), "standalone ROM"
    )
    sram_path, sram_record = _validate_manifest_file_record(
        outputs.get("sram"), "disposable SRAM"
    )
    if (
        rom_record["size"] != pins.rom_size
        or rom_record["sha256"] != pins.rom_sha256
    ):
        raise RuntimeEvidenceError("standalone ROM does not match its runtime pin")
    if (
        sram_record["size"] != pins.sram_size
        or sram_record["sha256"] != pins.sram_sha256
    ):
        raise RuntimeEvidenceError("disposable SRAM is not the pinned zero image")
    if audit.get("target_sha256") != rom_record["sha256"]:
        raise RuntimeEvidenceError("static audit target does not match the ROM")

    raw_sources = source.get("assembly_sources")
    if not isinstance(raw_sources, list):
        raise RuntimeEvidenceError("static assembly source records are missing")
    source_records: dict[str, dict[str, object]] = {}
    for index, record in enumerate(raw_sources):
        source_path, actual = _validate_manifest_file_record(
            record, f"assembly source {index}"
        )
        relative = workspace_relative(source_path)
        if relative in source_records:
            raise RuntimeEvidenceError(f"duplicate assembly source {relative}")
        source_records[relative] = actual
    if set(source_records) != set(pins.required_assembly_paths):
        raise RuntimeEvidenceError(
            "static assembly source closure is not the required exact set"
        )

    raw_builder = source.get("builder_source")
    if pins.required_static_builder_path is None:
        if not isinstance(raw_builder, Mapping):
            raise RuntimeEvidenceError("static builder source record is missing")
        builder_path, builder_record = _validate_manifest_file_record(
            raw_builder, "static builder source"
        )
    else:
        builder_path, builder_record = _validate_manifest_file_record(
            raw_builder, "static builder source"
        )
        if workspace_relative(builder_path) != pins.required_static_builder_path:
            raise RuntimeEvidenceError("unexpected static builder source path")

    return dict(source), {
        "manifest": manifest_record,
        "rom": rom_record,
        "rom_path": rom_path,
        "sram": sram_record,
        "sram_path": sram_path,
        "assembly_sources": [
            source_records[key] for key in sorted(source_records)
        ],
        "builder_source": builder_record,
    }


def parse_key_value_file(
    path: pathlib.Path,
    *,
    pattern: re.Pattern[str],
    label: str,
) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeEvidenceError(f"{label} is not UTF-8") from exc
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        if match is None:
            raise RuntimeEvidenceError(f"malformed {label} line: {line}")
        key = match.group("key")
        if key in result:
            raise RuntimeEvidenceError(f"duplicate {label} key: {key}")
        result[key] = match.group("value")
    return result


def parse_core_info(path: pathlib.Path) -> dict[str, str]:
    parsed = parse_key_value_file(
        path,
        pattern=INFO_LINE_RE,
        label="bsnes core info",
    )
    normalized: dict[str, str] = {}
    for key, raw_value in parsed.items():
        value = raw_value.strip()
        if value.startswith('"') or value.endswith('"'):
            if (
                len(value) < 2
                or not value.startswith('"')
                or not value.endswith('"')
                or '"' in value[1:-1]
            ):
                raise RuntimeEvidenceError(
                    f"malformed quoted bsnes core info value for {key}"
                )
            value = value[1:-1]
        elif any(character.isspace() for character in value):
            raise RuntimeEvidenceError(
                f"malformed bare bsnes core info value for {key}"
            )
        normalized[key] = value
    return normalized


def validate_runtime_tools(
    retroarch_exe: pathlib.Path,
    core: pathlib.Path,
    core_info: pathlib.Path,
    pins: RuntimePins,
) -> dict[str, object]:
    retroarch_exe = retroarch_exe.resolve()
    core = core.resolve()
    core_info = core_info.resolve()
    executable = validate_pin(
        retroarch_exe, pins.retroarch_exe, "RetroArch executable"
    )
    core_record = validate_pin(core, pins.core, "bsnes libretro core")
    info_record = validate_pin(
        core_info, pins.core_info, "bsnes core info"
    )
    info = parse_core_info(core_info)
    if info.get("corename") != "bsnes":
        raise RuntimeEvidenceError("core info does not identify bsnes")
    if info.get("display_version") != pins.core_info_version:
        raise RuntimeEvidenceError("core info display version mismatch")
    return {
        "retroarch": {
            **executable,
            "version": pins.retroarch_version,
            "git": pins.retroarch_git,
        },
        "bsnes_core": {
            **core_record,
            "core_info": info_record,
            "core_info_display_version": info["display_version"],
            "serializer_version_required": pins.serializer_version,
        },
    }


BASE_CONFIG_EXPECTED = {
    "video_driver": "null",
    "audio_driver": "null",
    "input_driver": "null",
    "savestate_auto_load": "false",
    "savestate_auto_save": "false",
    "savestate_file_compression": "false",
    "save_file_compression": "false",
}
RUN_CONFIG_EXACT_KEYS = {
    "savestate_auto_load",
    "savestate_auto_save",
    "savestate_file_compression",
    "save_file_compression",
    "savefile_directory",
    "savestate_directory",
    "runtime_log",
}


def validate_base_config(
    path: pathlib.Path,
    pins: RuntimePins,
) -> tuple[pathlib.Path, dict[str, object]]:
    path = validate_private_file(path, "base RetroArch config")
    record = validate_pin(path, pins.base_config, "base RetroArch config")
    parsed = parse_key_value_file(
        path, pattern=CFG_LINE_RE, label="base RetroArch config"
    )
    for key, expected in BASE_CONFIG_EXPECTED.items():
        if parsed.get(key) != expected:
            raise RuntimeEvidenceError(
                f"base RetroArch config {key} is not {expected!r}"
            )
    return path, record


def validate_run_config(
    path: pathlib.Path,
    pin: FilePin,
    *,
    run_index: int,
    sram_path: pathlib.Path,
    state_path: pathlib.Path,
) -> tuple[pathlib.Path, dict[str, object]]:
    path = validate_private_file(path, f"run {run_index} config")
    record = validate_pin(path, pin, f"run {run_index} config")
    parsed = parse_key_value_file(
        path, pattern=CFG_LINE_RE, label=f"run {run_index} config"
    )
    if set(parsed) != RUN_CONFIG_EXACT_KEYS:
        raise RuntimeEvidenceError(
            f"run {run_index} config keys are not the exact bounded set"
        )
    expected = {
        "savestate_auto_load": "false",
        "savestate_auto_save": "true",
        "savestate_file_compression": "false",
        "save_file_compression": "false",
        "savefile_directory": str(sram_path.parent.resolve()),
        "savestate_directory": str(state_path.parent.resolve()),
        "runtime_log": "false",
    }
    for key, value in expected.items():
        if parsed.get(key) != value:
            raise RuntimeEvidenceError(
                f"run {run_index} config {key} mismatch"
            )
    return path, record


def validate_log(
    path: pathlib.Path,
    pin: FilePin,
    *,
    run_index: int,
    base_config: pathlib.Path,
    run_config: pathlib.Path,
    retroarch_exe: pathlib.Path,
    core: pathlib.Path,
    rom: pathlib.Path,
    sram: pathlib.Path,
    state: pathlib.Path,
    pins: RuntimePins,
) -> tuple[pathlib.Path, dict[str, object], dict[str, int]]:
    path = validate_private_file(path, f"run {run_index} log")
    record = validate_pin(path, pin, f"run {run_index} log")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeEvidenceError(f"run {run_index} log is not UTF-8") from exc
    state_base = state.with_suffix("")
    required = (
        f"RetroArch {pins.retroarch_version} (Git {pins.retroarch_git})",
        f'Loading dynamic libretro core from: "{core.resolve()}".',
        f'Loading config: "{base_config.resolve()}".',
        f'Appending config: "{run_config.resolve()}".',
        f'Redirecting save file to "{sram.resolve()}".',
        f'Redirecting save state to "{state_base.resolve()}".',
        "[Content] Content loading skipped.",
        "[SRAM] Skipping SRAM load.",
        f'Auto save state to "{state.resolve()}" succeeded.',
    )
    for fragment in required:
        if fragment not in text:
            raise RuntimeEvidenceError(
                f"run {run_index} log is missing: {fragment}"
            )
    if "Auto save state" in text and "Auto save state to" not in text:
        raise RuntimeEvidenceError(f"run {run_index} autosave log is malformed")
    if str(rom.resolve()) not in text and rom.name not in text:
        # Current RetroArch does not print the content path on every launch;
        # the exact redirect stem and command reconstruction remain required.
        content_path_logged = False
    else:
        content_path_logged = True
    durations = list(DURATION_RE.finditer(text))
    if len(durations) != 1:
        raise RuntimeEvidenceError(
            f"run {run_index} log has no unique duration"
        )
    duration = {
        key: int(durations[0].group(key))
        for key in ("hours", "minutes", "seconds")
    }
    record["content_path_logged"] = content_path_logged
    record["frontend_reported_duration"] = duration
    return path, record, duration


def _extract_core(state: pathlib.Path) -> tuple[bytes, bytes]:
    source = state.read_bytes()
    try:
        core = retroarch_rastate.extract_memory(source)
    except RuntimeError as exc:
        raise RuntimeEvidenceError(f"invalid RASTATE {state}: {exc}") from exc
    return source, core


def validate_inspector_report(
    report: Mapping[str, object],
    *,
    state: pathlib.Path,
    pins: RuntimePins,
) -> dict[str, object]:
    if report.get("passed") is not True:
        raise RuntimeEvidenceError(f"state inspector did not pass {state}")
    if report.get("evidence_level") != "verified-runtime-standalone":
        raise RuntimeEvidenceError("state inspector evidence level mismatch")
    rastate = report.get("rastate")
    core = report.get("core_state")
    layout = report.get("memory_layout")
    result = report.get("result")
    if not all(
        isinstance(item, Mapping)
        for item in (rastate, core, layout, result)
    ):
        raise RuntimeEvidenceError("state inspector report is incomplete")
    if (
        rastate.get("size") != pins.rastate_size
        or rastate.get("sha256") != sha256_path(state)
    ):
        raise RuntimeEvidenceError("inspector RASTATE identity mismatch")
    if (
        core.get("size") != pins.core_state_size
        or core.get("serializer_version") != pins.serializer_version
    ):
        raise RuntimeEvidenceError("inspector core-state signature mismatch")
    if (
        layout.get("sram_offset") != state_inspector.BST_SRAM_OFFSET
        or layout.get("sram_size") != pins.sram_size
        or layout.get("sram_sha256") != pins.sram_sha256
        or layout.get("sram_all_zero") is not True
        or layout.get("wram_offset") != state_inspector.BST_WRAM_OFFSET
        or layout.get("wram_size") != state_inspector.WRAM_SIZE
        or layout.get("result_address") != state_inspector.RESULT_ADDRESS
        or layout.get("result_size") != state_inspector.RESULT_SIZE
    ):
        raise RuntimeEvidenceError("inspector memory layout mismatch")
    if (
        result.get("record_sha256") is None
        or result.get("scratch_with_guards_sha256") is None
        or not isinstance(result.get("slots"), list)
        or not isinstance(result.get("invalid_call"), Mapping)
    ):
        raise RuntimeEvidenceError("inspector deterministic evidence is missing")
    normalized = dict(report)
    normalized["path"] = display_path(state)
    return normalized


def inspect_run(
    state: pathlib.Path,
    *,
    inspector: Inspector,
    pins: RuntimePins,
) -> tuple[dict[str, object], bytes, bytes]:
    state = validate_private_file(state, "run RASTATE")
    raw_source, core = _extract_core(state)
    report = inspector(state)
    if not isinstance(report, Mapping):
        raise RuntimeEvidenceError("state inspector did not return an object")
    normalized = validate_inspector_report(report, state=state, pins=pins)
    if normalized["rastate"]["sha256"] != sha256_bytes(raw_source):
        raise RuntimeEvidenceError("RASTATE changed during inspection")
    if normalized["core_state"]["sha256"] != sha256_bytes(core):
        raise RuntimeEvidenceError("core state changed during inspection")
    return normalized, raw_source, core


def _span(
    name: str,
    start: int,
    end: int,
    first: bytes,
    second: bytes,
) -> dict[str, object]:
    if not 0 <= start < end <= len(first) or len(first) != len(second):
        raise RuntimeEvidenceError(f"invalid deterministic span {name}")
    left = first[start:end]
    right = second[start:end]
    if left != right:
        raise RuntimeEvidenceError(
            f"defined evidence span differs between runs: {name}"
        )
    return {
        "name": name,
        "core_state_start": start,
        "core_state_end_exclusive": end,
        "size": end - start,
        "sha256": sha256_bytes(left),
        "identical_between_runs": True,
    }


def compare_runs(
    reports: Sequence[Mapping[str, object]],
    cores: Sequence[bytes],
    *,
    pins: RuntimePins,
) -> dict[str, object]:
    if len(reports) != 2 or len(cores) != 2:
        raise RuntimeEvidenceError("exactly two runtime captures are required")
    first, second = cores
    if len(first) != len(second):
        raise RuntimeEvidenceError("core-state lengths differ")

    wram = state_inspector.BST_WRAM_OFFSET
    result_start = wram + state_inspector.RESULT_ADDRESS
    result_end = result_start + state_inspector.RESULT_SIZE
    scratch_start = wram + state_inspector.SCRATCH_FRONT
    scratch_end = wram + state_inspector.SCRATCH_REAR_END
    sram_start = state_inspector.BST_SRAM_OFFSET
    sram_end = sram_start + pins.sram_size
    spans = (
        _span("sram", sram_start, sram_end, first, second),
        _span(
            "scratch_with_guards",
            scratch_start,
            scratch_end,
            first,
            second,
        ),
        _span("result_record", result_start, result_end, first, second),
    )
    if reports[0]["result"] != reports[1]["result"]:
        raise RuntimeEvidenceError(
            "decoded benchmark results differ between runs"
        )
    if (
        reports[0]["memory_layout"]["sram_sha256"]
        != reports[1]["memory_layout"]["sram_sha256"]
    ):
        raise RuntimeEvidenceError("decoded SRAM evidence differs")

    differences = [
        index
        for index, (left, right) in enumerate(zip(first, second, strict=True))
        if left != right
    ]
    wram_end = wram + state_inspector.WRAM_SIZE
    allowed_core = set(
        range(
            pins.nondeterministic_core_start,
            pins.nondeterministic_core_end,
        )
    )
    core_differences = {
        offset
        for offset in differences
        if not wram <= offset < wram_end
    }
    unexpected_core = core_differences - allowed_core
    if unexpected_core:
        raise RuntimeEvidenceError(
            "full states differ outside the bounded bsnes/WRAM regions"
        )
    if (
        pins.require_exact_nondeterministic_core_span
        and core_differences != allowed_core
    ):
        raise RuntimeEvidenceError(
            "the expected eight current-bsnes core bytes did not all differ"
        )

    evidence_offsets: set[int] = set()
    for span in spans:
        evidence_offsets.update(
            range(
                int(span["core_state_start"]),
                int(span["core_state_end_exclusive"]),
            )
        )
    wram_differences = {
        offset
        for offset in differences
        if wram <= offset < wram_end
    }
    if wram_differences & evidence_offsets:
        raise RuntimeEvidenceError("defined WRAM evidence is nondeterministic")
    if pins.require_irrelevant_wram_difference and not wram_differences:
        raise RuntimeEvidenceError(
            "independent runs did not expose the expected uncleared WRAM difference"
        )
    accounted = core_differences | wram_differences
    if accounted != set(differences):
        raise RuntimeEvidenceError("full-state differences are not accounted")

    result = reports[0]["result"]
    slots = result["slots"]
    elapsed = [int(slot["elapsed_frames"]) for slot in slots]
    seconds = [
        round(frames / pins.frames_per_second, 6)
        for frames in elapsed
    ]
    final_frames = int(result["final_frame"])
    return {
        "full_rastate_hashes_identical": (
            reports[0]["rastate"]["sha256"]
            == reports[1]["rastate"]["sha256"]
        ),
        "full_core_state_hashes_identical": (
            reports[0]["core_state"]["sha256"]
            == reports[1]["core_state"]["sha256"]
        ),
        "full_core_state_difference_count": len(differences),
        "bounded_non_wram_difference": {
            "start": pins.nondeterministic_core_start,
            "end_exclusive": pins.nondeterministic_core_end,
            "differing_byte_count": len(core_differences),
            "exact_expected_span": core_differences == allowed_core,
            "classification": "current-bsnes-serializer-nondeterminism",
        },
        "uncleared_irrelevant_wram": {
            "start": wram,
            "end_exclusive": wram_end,
            "differing_byte_count": len(wram_differences),
            "defined_evidence_difference_count": 0,
        },
        "unaccounted_difference_count": 0,
        "defined_evidence_spans": list(spans),
        "decoded_result_identical": True,
        "decoded_sram_identical": True,
        "scratch_and_guards_identical": True,
        "timing": {
            "frames_per_second": pins.frames_per_second,
            "slot_elapsed_frames": elapsed,
            "slot_elapsed_seconds": seconds,
            "completion_frame": final_frames,
            "completion_seconds": round(
                final_frames / pins.frames_per_second,
                6,
            ),
            "classification": "measured-performance-blocker",
            "production_timing_approved": False,
        },
        "interpretation": (
            "Full-state hashes are intentionally not the determinism boundary. "
            "The two captures differ only in the eight bounded current-bsnes "
            "core bytes and uncleared WRAM outside exact SRAM, scratch/guard, "
            "and result-record evidence spans."
        ),
    }


def normalized_run_command(
    *,
    retroarch_exe: pathlib.Path,
    base_config: pathlib.Path,
    run_config: pathlib.Path,
    core: pathlib.Path,
    log: pathlib.Path,
    rom: pathlib.Path,
    max_frames: int,
) -> list[str]:
    return [
        str(retroarch_exe.resolve()),
        "-c",
        display_path(base_config),
        "--appendconfig",
        display_path(run_config),
        "-L",
        str(core.resolve()),
        "--sram-mode=noload-nosave",
        f"--max-frames={max_frames}",
        "--verbose",
        "--log-file",
        display_path(log),
        display_path(rom),
    ]


def build_in_memory(
    *,
    static_manifest: pathlib.Path = DEFAULT_STATIC_MANIFEST,
    states: Sequence[pathlib.Path] = DEFAULT_STATES,
    logs: Sequence[pathlib.Path] = DEFAULT_LOGS,
    run_configs: Sequence[pathlib.Path] = DEFAULT_RUN_CONFIGS,
    base_config: pathlib.Path = DEFAULT_BASE_CONFIG,
    retroarch_exe: pathlib.Path = DEFAULT_RETROARCH_EXE,
    core: pathlib.Path = DEFAULT_CORE,
    core_info: pathlib.Path = DEFAULT_CORE_INFO,
    output: pathlib.Path = DEFAULT_OUTPUT,
    pins: RuntimePins = DEFAULT_PINS,
    inspector: Inspector = state_inspector.inspect_path,
) -> RuntimeEvidenceResult:
    if len(states) != 2 or len(logs) != 2 or len(run_configs) != 2:
        raise RuntimeEvidenceError(
            "exactly two states, logs, and run configs are required"
        )
    output = validate_private_output(output)
    static_source, static = validate_static_build(static_manifest, pins)
    rom_path = static["rom_path"]
    sram_path = static["sram_path"]
    if rom_path.resolve() != DEFAULT_ROM.resolve() and pins is DEFAULT_PINS:
        raise RuntimeEvidenceError("default static ROM path changed")
    if sram_path.resolve() != DEFAULT_SRAM.resolve() and pins is DEFAULT_PINS:
        raise RuntimeEvidenceError("default static SRAM path changed")

    toolchain = validate_runtime_tools(
        retroarch_exe, core, core_info, pins
    )
    base_config, base_record = validate_base_config(base_config, pins)

    resolved_states = [
        validate_private_file(path, f"run {index} RASTATE")
        for index, path in enumerate(states, start=1)
    ]
    if len(set(resolved_states)) != 2:
        raise RuntimeEvidenceError("runtime states must be distinct files")

    run_entries: list[dict[str, object]] = []
    reports: list[dict[str, object]] = []
    cores: list[bytes] = []
    for offset in range(2):
        run_index = offset + 1
        config_path, config_record = validate_run_config(
            run_configs[offset],
            pins.run_configs[offset],
            run_index=run_index,
            sram_path=sram_path,
            state_path=resolved_states[offset],
        )
        log_path, log_record, duration = validate_log(
            logs[offset],
            pins.logs[offset],
            run_index=run_index,
            base_config=base_config,
            run_config=config_path,
            retroarch_exe=retroarch_exe,
            core=core,
            rom=rom_path,
            sram=sram_path,
            state=resolved_states[offset],
            pins=pins,
        )
        report, _rastate, core_state = inspect_run(
            resolved_states[offset],
            inspector=inspector,
            pins=pins,
        )
        reports.append(report)
        cores.append(core_state)
        run_entries.append(
            {
                "run": run_index,
                "config": config_record,
                "log": log_record,
                "state": file_record(resolved_states[offset]),
                "inspector": report,
                "command": normalized_run_command(
                    retroarch_exe=retroarch_exe,
                    base_config=base_config,
                    run_config=config_path,
                    core=core,
                    log=log_path,
                    rom=rom_path,
                    max_frames=pins.max_frames,
                ),
                "max_frames": pins.max_frames,
                "frontend_reported_duration": duration,
            }
        )

    reproducibility = compare_runs(reports, cores, pins=pins)
    inspector_source = pathlib.Path(state_inspector.__file__).resolve()
    builder_source = pathlib.Path(__file__).resolve()
    manifest: dict[str, object] = {
        "schema_version": 1,
        "builder_version": VERSION,
        "artifact_class": "standalone-sha256-runtime-evidence",
        "status": "verified-runtime-standalone",
        "evidence_level": "verified-runtime-standalone",
        "private_only": True,
        "production_input": False,
        "chrono_trigger_input_read": False,
        "project_epoch_hooks_installed": False,
        "project_epoch_allocations_approved": False,
        "output": {
            "path": display_path(output),
            "self_hash_embedded": False,
        },
        "builder_source": file_record(builder_source),
        "inspector_source": file_record(inspector_source),
        "static_build": {
            "manifest": static["manifest"],
            "rom": static["rom"],
            "sram": static["sram"],
            "assembly_sources": static["assembly_sources"],
            "builder_source": static["builder_source"],
            "host_audit_status": static_source["host_audit"]["status"],
            "production_guard_approval": False,
        },
        "runtime_toolchain": toolchain,
        "base_config": base_record,
        "runs": run_entries,
        "reproducibility": reproducibility,
        "conclusion": {
            "native_sha256_correct_for_pinned_zero_slots": True,
            "valid_call_abi_preserved": True,
            "invalid_call_failed_closed": True,
            "scratch_guards_preserved": True,
            "production_timing_approved": False,
            "measured_per_digest_seconds": reproducibility["timing"][
                "slot_elapsed_seconds"
            ],
            "decision": (
                "correctness runtime proof accepted; measured timing is a "
                "production blocker"
            ),
        },
        "reproduction": {
            "working_directory": ".",
            "manifest_command": [
                "python",
                "tools/build_sha256_65816_runtime_evidence_manifest.py",
            ],
            "run_commands": [entry["command"] for entry in run_entries],
            "historical_command_not_embedded_as_a_state_field": True,
        },
        "limitations": [
            "standalone original synthetic cartridge only",
            "all-zero 8 KiB SRAM vectors only",
            "minimal synthetic NMI handler only",
            "frame counts are coarse NMI-frame measurements, not cycle traces",
            "does not approve any Chrono Trigger hook or ROM allocation",
            "does not prove a Chrono Trigger WRAM scratch allocation",
            "does not approve save, load, New Game+, erase, or preview integration",
            "approximately six seconds per digest is a measured production blocker",
            "full-state hashes are not claimed deterministic; only named evidence spans are",
        ],
    }
    encoded = (
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return RuntimeEvidenceResult(
        manifest=manifest,
        manifest_bytes=encoded,
    )


def write_manifest(
    result: RuntimeEvidenceResult,
    output: pathlib.Path = DEFAULT_OUTPUT,
) -> pathlib.Path:
    output = validate_private_output(output)
    if output.exists() and output.read_bytes() != result.manifest_bytes:
        raise RuntimeEvidenceError(
            f"refusing to overwrite a different runtime manifest: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        output.write_bytes(result.manifest_bytes)
    if (
        output.stat().st_size != len(result.manifest_bytes)
        or sha256_path(output) != sha256_bytes(result.manifest_bytes)
    ):
        raise RuntimeEvidenceError("runtime manifest failed read-back verification")
    return output


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
        "--base-config", type=pathlib.Path, default=DEFAULT_BASE_CONFIG
    )
    parser.add_argument(
        "--retroarch-exe", type=pathlib.Path, default=DEFAULT_RETROARCH_EXE
    )
    parser.add_argument("--core", type=pathlib.Path, default=DEFAULT_CORE)
    parser.add_argument(
        "--core-info", type=pathlib.Path, default=DEFAULT_CORE_INFO
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
        f"{sha256_bytes(result.manifest_bytes)}"
    )
    print(f"verified={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
