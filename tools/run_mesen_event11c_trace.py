#!/usr/bin/env python3
"""Run one event-$11C Mesen trace with canonical private-path guards."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
COLLECTOR = (ROOT / "tools" / "mesen_event11c_trace.lua").resolve(strict=True)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_event11c_trace.py"
).resolve(strict=True)

DEFAULT_MESEN = PRIVATE_ROOT / "tools" / "mesen2" / "app" / "Mesen.exe"
DEFAULT_ROM = (
    PRIVATE_ROOT
    / "test_runs"
    / "mesen2"
    / "event11c_checkpoint_v5"
    / "project_epoch_mesen_event11c_clean.sfc"
)
DEFAULT_STATE = (
    PRIVATE_ROOT
    / "test_runs"
    / "mesen2"
    / "event11c_checkpoint_v5"
    / "spekkio_talkable.mss"
)
DEFAULT_SRAM = (
    PRIVATE_ROOT
    / "tools"
    / "mesen2"
    / "app"
    / "Saves"
    / "project_epoch_mesen_event11c_clean.srm"
)

EXPECTED_HASHES = {
    "archive": "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe",
    "collector": "c6f8480b4dcfd0ff917529c96629bf8dce3da228bc0be07217639b4bec906931",
    "harfbuzz": "eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d",
    "mesen": "d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b",
    "mesen_core": "65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74",
    "nesdb": "cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307",
    "rom": "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9",
    "settings": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    "skia": "9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd",
    "state": "26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e",
    "sram": "a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9",
    "validator": "9dab9e43eae63d0200c2502753b62ffd7c9e368d9a0bca85ba5295a8b9978def",
}
TRACE_SCHEMA = "project-epoch-mesen-event11c-access-trace-v1"
EXPECTED_EXIT_CODE = 41
MAX_TRACE_BYTES = 1024 * 1024
EXPECTED_OUTPUTS = {
    ("frog-robo", "zero"): {
        "trace": (
            1717,
            "b8072a76df2ddbfc68f246f063cf325b079fba515b373e511f0e7feaa2d11bf6",
        ),
        "screenshot": (
            9503,
            "0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb",
        ),
    },
    ("frog-robo", "canary"): {
        "trace": (
            1719,
            "021acbda6a32513974ea378566279cbe918543222def941e2d79338faddb00cb",
        ),
        "screenshot": (
            9503,
            "0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb",
        ),
    },
    ("crono-marle-lucca", "zero"): {
        "trace": (
            2509,
            "943f9f0f7817c9b38221f04b7dd82448a3ada409ff7624141be4a6cbc077ec5d",
        ),
        "screenshot": (
            10421,
            "312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96",
        ),
    },
    ("crono-marle-lucca", "canary"): {
        "trace": (
            2511,
            "d7f8e285d8dc09d7eea68c4907f38da487e8110ce8177cd879b62de5b3884111",
        ),
        "screenshot": (
            10421,
            "312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96",
        ),
    },
}


class TraceLaunchError(RuntimeError):
    """Raised when a trace launch fails a safety or evidence check."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_strict_validator() -> Any:
    actual = sha256_file(VALIDATOR_PATH)
    if actual != EXPECTED_HASHES["validator"]:
        raise TraceLaunchError(
            "strict validator SHA-256 mismatch: "
            f"expected {EXPECTED_HASHES['validator']}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(
        "_project_epoch_mesen_trace_validator",
        VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise TraceLaunchError(f"cannot load strict validator: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STRICT_VALIDATOR = _load_strict_validator()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def canonical_private_root() -> Path:
    lexical_private_root = ROOT / "private"
    try:
        private_root = lexical_private_root.resolve(strict=True)
    except OSError as exc:
        raise TraceLaunchError(
            f"workspace private directory does not exist: {lexical_private_root}"
        ) from exc
    if not private_root.is_dir():
        raise TraceLaunchError(
            f"workspace private path is not a directory: {private_root}"
        )
    if private_root != lexical_private_root:
        raise TraceLaunchError(
            "workspace private directory itself must not be a link or junction"
        )
    return private_root


def resolve_private_file(raw_path: str | Path, label: str) -> Path:
    private_root = canonical_private_root()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise TraceLaunchError(f"{label} is not an existing file: {candidate}") from exc
    if not resolved.is_file():
        raise TraceLaunchError(f"{label} is not a file: {resolved}")
    if not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"{label} resolves outside {private_root}: {resolved}"
        )
    return resolved


def prepare_private_output_dir(
    raw_path: str | Path,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> Path:
    private_root = canonical_private_root()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if os.path.lexists(candidate):
        raise TraceLaunchError(
            f"output directory must be a new path: {candidate}"
        )
    resolved = candidate.resolve(strict=False)
    if not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"output directory resolves outside {private_root}: {resolved}"
        )
    for forbidden_root in forbidden_roots:
        forbidden = forbidden_root.resolve(strict=True)
        if _inside(resolved, forbidden) or _inside(forbidden, resolved):
            raise TraceLaunchError(
                f"output directory overlaps protected tree: {forbidden}"
            )
    resolved.mkdir(parents=True, exist_ok=False)
    resolved = resolved.resolve(strict=True)
    if not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"created output directory escaped {private_root}: {resolved}"
        )
    if not resolved.is_dir():
        raise TraceLaunchError(f"output path is not a directory: {resolved}")
    return resolved


def require_hash(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise TraceLaunchError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def require_artifact(
    path: Path,
    expected: tuple[int, str],
    label: str,
) -> dict[str, Any]:
    expected_size, expected_hash = expected
    actual_size = path.stat().st_size
    actual_hash = sha256_file(path)
    if actual_size != expected_size or actual_hash != expected_hash:
        raise TraceLaunchError(
            f"{label} does not match accepted artifact: expected "
            f"{expected_size}/{expected_hash}, got {actual_size}/{actual_hash}"
        )
    return {
        "path": str(path),
        "size": actual_size,
        "sha256": actual_hash,
    }


def snapshot_private_files(directory: Path) -> dict[str, tuple[int, str]]:
    private_root = canonical_private_root()
    resolved_root = directory.resolve(strict=True)
    if not resolved_root.is_dir() or not _inside(resolved_root, private_root):
        raise TraceLaunchError(
            f"snapshot directory is not safely under private/: {resolved_root}"
        )
    snapshot: dict[str, tuple[int, str]] = {}
    for candidate in sorted(resolved_root.rglob("*")):
        if not candidate.is_file():
            continue
        resolved = candidate.resolve(strict=True)
        if not _inside(resolved, resolved_root):
            raise TraceLaunchError(
                f"snapshot file escapes guarded directory: {candidate}"
            )
        relative = resolved.relative_to(resolved_root).as_posix()
        if relative in snapshot:
            raise TraceLaunchError(
                f"duplicate canonical snapshot path: {relative}"
            )
        snapshot[relative] = (resolved.stat().st_size, sha256_file(resolved))
    return snapshot


def load_trace(path: Path, profile: str, variant: str) -> dict[str, Any]:
    size = path.stat().st_size
    if size > MAX_TRACE_BYTES:
        raise TraceLaunchError(f"trace exceeds {MAX_TRACE_BYTES} bytes: {size}")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise TraceLaunchError(f"trace contains duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        with path.open("r", encoding="utf-8") as handle:
            trace = json.load(handle, object_pairs_hook=reject_duplicate)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TraceLaunchError(f"could not parse trace JSON: {path}") from exc
    try:
        exact_profile, exact_variant = STRICT_VALIDATOR.validate_trace_document(
            trace,
            label=str(path),
        )
    except STRICT_VALIDATOR.TraceValidationError as exc:
        raise TraceLaunchError(f"strict trace validation failed: {exc}") from exc
    if exact_profile != profile or exact_variant != variant:
        raise TraceLaunchError("trace profile or variant mismatch")
    return trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one pinned Mesen event-$11C trace. All emulator inputs and "
            "outputs are resolved beneath this workspace's ignored private/ tree."
        )
    )
    parser.add_argument(
        "--profile",
        required=True,
        choices=("frog-robo", "crono-marle-lucca"),
    )
    parser.add_argument("--variant", required=True, choices=("zero", "canary"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=60)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.timeout < 1 or args.timeout > 300:
        raise TraceLaunchError("--timeout must be between 1 and 300 seconds")

    mesen = resolve_private_file(args.mesen, "Mesen executable")
    rom = resolve_private_file(args.rom, "canonical ROM")
    state = resolve_private_file(args.state, "native checkpoint")
    sram = resolve_private_file(args.sram, "disposable SRAM")
    private_root = canonical_private_root()
    archive = resolve_private_file(
        mesen.parent.parent / "Mesen_2.1.1_Windows.zip",
        "official Mesen archive",
    )
    harfbuzz = resolve_private_file(
        mesen.parent / "libHarfBuzzSharp.dll",
        "HarfBuzz runtime",
    )
    mesen_core = resolve_private_file(
        mesen.parent / "MesenCore.dll",
        "Mesen emulation core",
    )
    nesdb = resolve_private_file(
        mesen.parent / "MesenNesDB.txt",
        "Mesen database",
    )
    settings = resolve_private_file(
        mesen.parent / "settings.json",
        "portable Mesen settings",
    )
    skia = resolve_private_file(
        mesen.parent / "libSkiaSharp.dll",
        "Skia runtime",
    )
    shared_saves = (mesen.parent / "Saves").resolve(strict=True)
    shared_saves_before = snapshot_private_files(shared_saves)
    output_dir = prepare_private_output_dir(
        args.output_dir,
        forbidden_roots=(shared_saves,),
    )

    trace_path = output_dir / "trace.json"
    screenshot_path = output_dir / "endpoint.png"
    error_path = output_dir / "trace.json.observer-error"
    collisions = [
        path
        for path in (trace_path, screenshot_path, error_path)
        if os.path.lexists(path)
    ]
    if collisions:
        joined = ", ".join(str(path) for path in collisions)
        raise TraceLaunchError(f"refusing to overwrite existing output: {joined}")

    pinned_inputs = {
        "archive": archive,
        "collector": COLLECTOR,
        "harfbuzz": harfbuzz,
        "mesen": mesen,
        "mesen_core": mesen_core,
        "nesdb": nesdb,
        "rom": rom,
        "settings": settings,
        "skia": skia,
        "state": state,
        "sram": sram,
        "validator": VALIDATOR_PATH,
    }
    before = {
        label: require_hash(path, EXPECTED_HASHES[label], label)
        for label, path in pinned_inputs.items()
    }
    process_error: Exception | None = None
    completed: subprocess.CompletedProcess[str] | None = None
    staged_changed: list[str] = []
    with tempfile.TemporaryDirectory(
        prefix=".event11c_staging_",
        dir=output_dir,
    ) as staging_directory:
        staging_root = Path(staging_directory).resolve(strict=True)
        if not _inside(staging_root, private_root):
            raise TraceLaunchError("temporary staging directory escaped private/")
        staged_app = staging_root / "app"
        staged_saves = staged_app / "Saves"
        staged_saves.mkdir(parents=True)
        staged_runtime_sources = {
            "mesen": mesen,
            "mesen_core": mesen_core,
            "harfbuzz": harfbuzz,
            "skia": skia,
            "nesdb": nesdb,
            "settings": settings,
        }
        staged_runtime_names = {
            "mesen": "Mesen.exe",
            "mesen_core": "MesenCore.dll",
            "harfbuzz": "libHarfBuzzSharp.dll",
            "skia": "libSkiaSharp.dll",
            "nesdb": "MesenNesDB.txt",
            "settings": "settings.json",
        }
        staged_runtime: dict[str, Path] = {}
        for label, source_path in staged_runtime_sources.items():
            destination = staged_app / staged_runtime_names[label]
            shutil.copyfile(source_path, destination)
            staged_runtime[label] = destination.resolve(strict=True)

        unique_stem = f"pe_event11c_{secrets.token_hex(12)}"
        staged_rom = (staging_root / f"{unique_stem}.sfc").resolve(strict=False)
        staged_sram = (
            staged_saves / f"{unique_stem}.srm"
        ).resolve(strict=False)
        shutil.copyfile(rom, staged_rom)
        shutil.copyfile(sram, staged_sram)
        staged_rom = staged_rom.resolve(strict=True)
        staged_sram = staged_sram.resolve(strict=True)

        staged_files = {
            **staged_runtime,
            "rom": staged_rom,
            "sram": staged_sram,
        }
        for label, path in staged_files.items():
            if not _inside(path, staging_root):
                raise TraceLaunchError(
                    f"staged {label} escaped private temporary root"
                )
            require_hash(path, EXPECTED_HASHES[label], f"staged {label}")

        environment = os.environ.copy()
        environment.update(
            {
                "PE_STATE_PATH": str(state),
                "PE_TRACE_OUT": str(trace_path),
                "PE_TRACE_SCREENSHOT": str(screenshot_path),
                "PE_PROFILE": args.profile,
                "PE_VARIANT": args.variant,
            }
        )
        command = [
            str(staged_runtime["mesen"]),
            "--testRunner",
            f"--timeout={args.timeout}",
            "--doNotSaveSettings",
            "--debug.scriptWindow.allowIoOsAccess=true",
            "--snes.port1.type=SnesController",
            str(COLLECTOR),
            str(staged_rom),
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            completed = subprocess.run(
                command,
                cwd=staged_app,
                env=environment,
                capture_output=True,
                text=True,
                timeout=args.timeout + 15,
                check=False,
                creationflags=creation_flags,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            process_error = exc
        for label, path in staged_files.items():
            try:
                if sha256_file(path) != EXPECTED_HASHES[label]:
                    staged_changed.append(f"staged {label} changed")
            except OSError:
                staged_changed.append(f"staged {label} missing")
        staged_save_entries = sorted(
            path.name for path in staged_saves.iterdir() if path.is_file()
        )
        if staged_save_entries != [staged_sram.name]:
            staged_changed.append(
                "staged Saves directory contains unexpected files"
            )

    changed: list[str] = []
    for label, path in pinned_inputs.items():
        try:
            after = sha256_file(path)
        except OSError:
            changed.append(f"{label} missing")
            continue
        if after != before[label]:
            changed.append(f"{label} changed")
    if changed:
        raise TraceLaunchError(
            "immutable emulator input mutation detected: " + ", ".join(changed)
        )
    shared_saves_after = snapshot_private_files(shared_saves)
    if shared_saves_after != shared_saves_before:
        raise TraceLaunchError("shared Mesen Saves directory changed")
    if staged_changed:
        raise TraceLaunchError(
            "disposable emulator input mutation detected: "
            + ", ".join(staged_changed)
        )
    if process_error is not None:
        raise TraceLaunchError(f"Mesen launch failed: {process_error}") from process_error
    assert completed is not None
    if completed.returncode != EXPECTED_EXIT_CODE:
        detail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        suffix = f": {detail}" if detail else ""
        raise TraceLaunchError(
            f"Mesen returned {completed.returncode}, expected "
            f"{EXPECTED_EXIT_CODE}{suffix}"
        )
    if error_path.exists():
        raise TraceLaunchError(f"collector reported an observer error: {error_path}")
    if not trace_path.is_file() or not screenshot_path.is_file():
        raise TraceLaunchError("Mesen did not produce both required outputs")

    trace = load_trace(trace_path, args.profile, args.variant)
    expected_outputs = EXPECTED_OUTPUTS[(args.profile, args.variant)]
    trace_artifact = require_artifact(
        trace_path,
        expected_outputs["trace"],
        "trace JSON",
    )
    screenshot_artifact = require_artifact(
        screenshot_path,
        expected_outputs["screenshot"],
        "endpoint PNG",
    )
    return {
        "status": "accepted-private-diagnostic-case",
        "profile": args.profile,
        "variant": args.variant,
        "exit_code": completed.returncode,
        "callback_count": len(trace.get("callbacks", [])),
        "trace": trace_artifact,
        "screenshot": screenshot_artifact,
        "immutable_inputs_preserved": True,
        "shared_mesen_saves_preserved": True,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except TraceLaunchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
