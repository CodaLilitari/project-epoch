#!/usr/bin/env python3
"""Run one isolated Mesen WRAM-ownership trace.

The launcher is deliberately fail-closed.  It stages a complete pinned Mesen
2.1.1 app, a uniquely named ROM/SRAM pair, the exact verified checkpoint and
collector bytes, and both collector outputs beneath a disposable private
directory.  It never accepts raw packet or arbitrary collector inputs.

Default runs enforce the frozen trace/PNG hashes.  ``--exploratory`` retains
the same input, staging, validation, preservation, and exclusive-publication
controls but deliberately makes no acceptance claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from typing import Any, Mapping, NamedTuple


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
COLLECTOR = ROOT / "tools" / "mesen_wram_ownership_trace.lua"
VALIDATOR_PATH = ROOT / "tools" / "validate_mesen_wram_ownership_trace.py"
SCENARIO_CONTRACT_PATH = (
    ROOT / "references" / "mesen_wram_ownership_scenarios_v1.json"
)

# Exact source trust roots.  The launcher reads, hashes, and stages these bytes
# directly; the Python validator is compiled from the same verified bytes.
COLLECTOR_SHA256 = (
    "d5dd2b2d7085237844d95ab04f7007b6"
    "b2d17b2e1160f23857018319380b7569"
)
VALIDATOR_SHA256 = (
    "89a7dc86c6b5b10dc984b778451152e4"
    "734b5c553a669b7ee033e465ca87f2ba"
)
SCENARIO_CONTRACT_SHA256 = (
    "e9ea3ec765d3c14511f11815f1155c66"
    "c63f4cda1b23d445a2274ade0d8831d9"
)

SCENARIO_CONTRACT_SCHEMA = (
    "project-epoch-mesen-wram-ownership-scenarios-v1"
)
TRACE_SCHEMA = "project-epoch-mesen-wram-ownership-trace-v1"
SCENARIOS = (
    "calibration",
    "field-idle",
    "main-menu",
    "event11c-frog",
)
VARIANTS = ("zero", "canary")


class TraceLaunchError(RuntimeError):
    """Raised when a launch fails a safety or evidence check."""


class TrustRoots(NamedTuple):
    """Exact source bytes/modules captured before private inputs are touched."""

    collector_source: bytes
    validator: Any
    scenario_contract: Mapping[str, Any]
    scenario_contract_source: bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256_pin(value: str) -> bool:
    return (
        len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _read_pinned_bytes(
    path: Path,
    expected_sha256: str,
    label: str,
) -> bytes:
    if not _valid_sha256_pin(expected_sha256):
        raise TraceLaunchError(
            f"{label} has no frozen exact SHA-256 pin; execution is disabled"
        )
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise TraceLaunchError(f"cannot read pinned {label}: {path}") from exc
    actual_sha256 = hashlib.sha256(source).hexdigest()
    if actual_sha256 != expected_sha256:
        raise TraceLaunchError(
            f"{label} SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    return source


def _load_pinned_module(
    name: str,
    path: Path,
    expected_sha256: str,
) -> Any:
    """Compile and execute the exact bytes that were just hash-verified."""

    source = _read_pinned_bytes(path, expected_sha256, path.name)
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


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TraceLaunchError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode_json_object(source: bytes, label: str) -> dict[str, Any]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TraceLaunchError(f"{label} is not UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except TraceLaunchError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise TraceLaunchError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TraceLaunchError(f"{label} must contain one JSON object")
    return value


def _validate_scenario_contract(
    contract: Mapping[str, Any],
) -> None:
    if contract.get("schema") != SCENARIO_CONTRACT_SCHEMA:
        raise TraceLaunchError("scenario contract schema drifted")
    if contract.get("version") != 1:
        raise TraceLaunchError("scenario contract version drifted")
    if contract.get("acceptance_status") != "accepted-exact-artifact-hashes":
        raise TraceLaunchError("scenario contract acceptance status drifted")

    trace_contract = contract.get("trace_contract")
    if not isinstance(trace_contract, dict):
        raise TraceLaunchError("scenario contract trace_contract is missing")
    if (
        trace_contract.get("schema") != TRACE_SCHEMA
        or trace_contract.get("collector_version") != 1
        or trace_contract.get("trace_count") != 8
        or trace_contract.get("variants") != list(VARIANTS)
        or trace_contract.get("event11c_screenshot_capture_phase")
        != "endFrame-canonical-png-after-route-endpoint-freeze"
        or trace_contract.get("event11c_screenshot_size") != 9503
        or trace_contract.get("event11c_screenshot_sha256")
        != (
            "0882eb8e58d053a0e5b2222c9615ab5"
            "a1e4530d8849ddd7388e491803417b7fb"
        )
    ):
        raise TraceLaunchError("scenario trace contract drifted")

    scenarios = contract.get("scenarios")
    if not isinstance(scenarios, list):
        raise TraceLaunchError("scenario definitions are missing")
    if [row.get("name") for row in scenarios if isinstance(row, dict)] != list(
        SCENARIOS
    ):
        raise TraceLaunchError("scenario names/order drifted")

    expected_ranges = [
        ("old-compatibility", "7E2830", "7E287F", 80),
        ("roster", "7E2980", "7E2988", 9),
        ("joined", "7E29AF", "7E29AF", 1),
        ("epoch-name", "7E2C4D", "7E2C52", 6),
        ("front-guard", "7E2C9C", "7E2C9F", 4),
        ("candidate", "7E2CA0", "7E2CEF", 80),
        ("rear-guard", "7E2CF0", "7E2CFF", 16),
    ]
    watched = contract.get("watched_ranges")
    if not isinstance(watched, list) or len(watched) != len(expected_ranges):
        raise TraceLaunchError("watched-range contract drifted")
    actual_ranges = [
        (
            row.get("name"),
            row.get("start"),
            row.get("end"),
            row.get("length"),
        )
        for row in watched
        if isinstance(row, dict)
    ]
    if actual_ranges != expected_ranges:
        raise TraceLaunchError("watched-range order or bounds drifted")

    sources = contract.get("sources")
    if not isinstance(sources, dict):
        raise TraceLaunchError("scenario source pins are missing")
    expected_sources = (
        ("collector", "tools/mesen_wram_ownership_trace.lua", COLLECTOR_SHA256),
        (
            "validator",
            "tools/validate_mesen_wram_ownership_trace.py",
            VALIDATOR_SHA256,
        ),
    )
    for key, expected_path, expected_hash in expected_sources:
        row = sources.get(key)
        if (
            not isinstance(row, dict)
            or row.get("path") != expected_path
            or row.get("sha256") != expected_hash
        ):
            raise TraceLaunchError(f"scenario {key} source pin drifted")


def load_trust_roots() -> TrustRoots:
    """Capture and bind every source-controlled executable trust root."""

    contract_source = _read_pinned_bytes(
        SCENARIO_CONTRACT_PATH,
        SCENARIO_CONTRACT_SHA256,
        "WRAM ownership scenario contract",
    )
    contract = _decode_json_object(
        contract_source,
        "WRAM ownership scenario contract",
    )
    _validate_scenario_contract(contract)
    collector_source = _read_pinned_bytes(
        COLLECTOR,
        COLLECTOR_SHA256,
        "WRAM ownership collector",
    )
    validator = _load_pinned_module(
        "_project_epoch_mesen_wram_ownership_validator",
        VALIDATOR_PATH,
        VALIDATOR_SHA256,
    )
    if not callable(getattr(validator, "validate_trace_document", None)):
        raise TraceLaunchError(
            "pinned validator has no validate_trace_document entrypoint"
        )
    return TrustRoots(
        collector_source=collector_source,
        validator=validator,
        scenario_contract=contract,
        scenario_contract_source=contract_source,
    )


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
        raise TraceLaunchError(f"{label} resolves outside {private_root}: {resolved}")
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
        raise TraceLaunchError(f"output directory must be a new path: {candidate}")
    resolved = candidate.resolve(strict=False)
    if not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"output directory resolves outside {private_root}: {resolved}"
        )
    for forbidden_root in forbidden_roots:
        protected = forbidden_root.resolve(strict=True)
        if _inside(resolved, protected) or _inside(protected, resolved):
            raise TraceLaunchError(
                f"output directory overlaps protected tree: {protected}"
            )
    resolved.mkdir(parents=True, exist_ok=False)
    resolved = resolved.resolve(strict=True)
    if not resolved.is_dir() or not _inside(resolved, private_root):
        raise TraceLaunchError(
            f"created output directory escaped {private_root}: {resolved}"
        )
    return resolved


def require_hash(path: Path, expected: str, label: str) -> str:
    if not _valid_sha256_pin(expected):
        raise TraceLaunchError(f"{label} has no valid SHA-256 pin")
    actual = sha256_file(path)
    if actual != expected:
        raise TraceLaunchError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )
    return actual


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
            raise TraceLaunchError(f"duplicate canonical snapshot path: {relative}")
        snapshot[relative] = (resolved.stat().st_size, sha256_file(resolved))
    return snapshot


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

RUNTIME_HASHES = {
    "archive": "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe",
    "harfbuzz": "eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d",
    "mesen": "d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b",
    "mesen_core": "65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74",
    "nesdb": "cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307",
    "settings": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    "skia": "9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd",
    "rom": "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9",
    "state": "26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e",
    "sram": "a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9",
}
PINNED_SIZES = {
    "archive": 34058170,
    "harfbuzz": 1804872,
    "mesen": 70470144,
    "mesen_core": 7143424,
    "nesdb": 559118,
    "settings": 3,
    "skia": 9414216,
    "rom": 4194304,
    "state": 133993,
    "sram": 8192,
}

EXPECTED_EXIT_CODE = 41
MAX_TRACE_BYTES = 4 * 1024 * 1024
MAX_SCREENSHOT_BYTES = 16 * 1024 * 1024

EXPECTED_OUTPUTS: dict[
    tuple[str, str],
    dict[str, tuple[int, str]],
] = {
    ("calibration", "zero"): {
        "trace": (
            12567,
            "688afc735e1c3f4d462ae9c9d618e9e"
            "24ef079b3d6ee3e35613865264fcbf973",
        ),
        "screenshot": (
            12563,
            "74fad510dd4efcc5c30807b8bd82c3ae"
            "39f564b6cea60ad972f8fac12284c91c",
        ),
    },
    ("calibration", "canary"): {
        "trace": (
            19317,
            "e364fda5e2b47394a970b68f99e78ad4"
            "10aef7cc225ba17368e5a1ba895d6200",
        ),
        "screenshot": (
            12563,
            "74fad510dd4efcc5c30807b8bd82c3ae"
            "39f564b6cea60ad972f8fac12284c91c",
        ),
    },
    ("field-idle", "zero"): {
        "trace": (
            50208,
            "d6a5d0cbbd39708a7970108d1027a99b"
            "42e8b6ded2d7558d55998fa958dc1168",
        ),
        "screenshot": (
            12563,
            "74fad510dd4efcc5c30807b8bd82c3ae"
            "39f564b6cea60ad972f8fac12284c91c",
        ),
    },
    ("field-idle", "canary"): {
        "trace": (
            56958,
            "47a350123dbc79d6f54087914980ff1d1"
            "fd45d5a64f04550397f8243ec6ca315",
        ),
        "screenshot": (
            12563,
            "74fad510dd4efcc5c30807b8bd82c3ae"
            "39f564b6cea60ad972f8fac12284c91c",
        ),
    },
    ("main-menu", "zero"): {
        "trace": (
            22932,
            "de4eaf7b9753af0ee50fd862ec7239d9"
            "d0bf27d6c265bb06306c664adb381ec0",
        ),
        "screenshot": (
            15428,
            "765689bbc5df5fd3e9e0f058817d3838d"
            "828e5b029fe25c4290e9dcce03f7b61",
        ),
    },
    ("main-menu", "canary"): {
        "trace": (
            29682,
            "471c9b9879f4285d9c6e7f4543c1d99"
            "d511231636d97de194a247759c9a415eb",
        ),
        "screenshot": (
            15428,
            "765689bbc5df5fd3e9e0f058817d3838d"
            "828e5b029fe25c4290e9dcce03f7b61",
        ),
    },
    ("event11c-frog", "zero"): {
        "trace": (
            117164,
            "7a9e179ecd783a5636bb7bb31b880137"
            "1c329116d9b94186859d1509e96dd7b4",
        ),
        "screenshot": (
            9503,
            "0882eb8e58d053a0e5b2222c9615ab5"
            "a1e4530d8849ddd7388e491803417b7fb",
        ),
    },
    ("event11c-frog", "canary"): {
        "trace": (
            123922,
            "5915bae9499c00e99ef2852c985a0434"
            "6918afaa3448433f477ccd89e367d0fa",
        ),
        "screenshot": (
            9503,
            "0882eb8e58d053a0e5b2222c9615ab5"
            "a1e4530d8849ddd7388e491803417b7fb",
        ),
    },
}


def read_direct_file(
    path: Path,
    label: str,
    *,
    root: Path,
    maximum: int,
    allow_empty: bool = False,
) -> bytes:
    resolved_root = root.resolve(strict=True)
    if path.parent.resolve(strict=True) != resolved_root:
        raise TraceLaunchError(f"{label} is not directly inside {resolved_root}")
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise TraceLaunchError(f"{label} is missing: {path}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise TraceLaunchError(f"{label} is not a direct regular file")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise TraceLaunchError(f"{label} could not be resolved") from exc
    if resolved != path or resolved.parent != resolved_root:
        raise TraceLaunchError(f"{label} escaped its guarded directory")
    if metadata.st_size > maximum:
        raise TraceLaunchError(f"{label} exceeds {maximum} bytes")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino)
                != (metadata.st_dev, metadata.st_ino)
            ):
                raise TraceLaunchError(f"{label} changed identity while opening")
            data = handle.read(maximum + 1)
    except OSError as exc:
        raise TraceLaunchError(f"could not read {label}: {path}") from exc
    if len(data) > maximum:
        raise TraceLaunchError(f"{label} exceeds {maximum} bytes")
    if not allow_empty and not data:
        raise TraceLaunchError(f"{label} is empty")
    return data


def load_trace_bytes(
    source: bytes,
    scenario: str,
    variant: str,
    validator: Any,
    *,
    label: str,
) -> dict[str, Any]:
    trace = _decode_json_object(source, label)
    try:
        observed = validator.validate_trace_document(trace, label=label)
    except Exception as exc:
        raise TraceLaunchError(f"strict trace validation failed: {exc}") from exc
    if observed != (scenario, variant):
        raise TraceLaunchError(
            "strict validator returned the wrong scenario/variant: "
            f"{observed!r}"
        )
    return trace


def describe_artifact_bytes(
    data: bytes,
    label: str,
    *,
    png: bool = False,
    expected: tuple[int, str] | None = None,
) -> dict[str, Any]:
    if not data:
        raise TraceLaunchError(f"{label} is empty")
    if png and data[:8] != b"\x89PNG\r\n\x1a\n":
        raise TraceLaunchError(f"{label} is not a PNG")
    actual = (len(data), hashlib.sha256(data).hexdigest())
    if expected is not None and actual != expected:
        raise TraceLaunchError(
            f"{label} does not match accepted artifact: expected "
            f"{expected[0]}/{expected[1]}, got {actual[0]}/{actual[1]}"
        )
    return {"size": actual[0], "sha256": actual[1]}


def publish_output_pair(
    output_root: Path,
    trace_path: Path,
    trace_bytes: bytes,
    screenshot_path: Path,
    screenshot_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_artifact = describe_artifact_bytes(trace_bytes, "trace JSON")
    screenshot_artifact = describe_artifact_bytes(
        screenshot_bytes,
        "endpoint PNG",
        png=True,
    )
    created: list[tuple[Path, tuple[int, int]]] = []
    try:
        for path, data, label in (
            (trace_path, trace_bytes, "trace JSON"),
            (screenshot_path, screenshot_bytes, "endpoint PNG"),
        ):
            if path.parent != output_root or os.path.lexists(path):
                raise TraceLaunchError(f"refusing to overwrite {label}: {path}")
            try:
                with path.open("xb") as handle:
                    identity = os.fstat(handle.fileno())
                    created.append((path, (identity.st_dev, identity.st_ino)))
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise TraceLaunchError(
                    f"refusing to overwrite {label}: {path}"
                ) from exc
            observed = read_direct_file(
                path,
                label,
                root=output_root,
                maximum=max(len(data), 1),
            )
            if observed != data:
                raise TraceLaunchError(f"published {label} bytes changed")
    except Exception:
        for path, identity in reversed(created):
            try:
                current = path.stat(follow_symlinks=False)
                if (
                    stat.S_ISREG(current.st_mode)
                    and (current.st_dev, current.st_ino) == identity
                ):
                    path.unlink()
            except OSError:
                pass
        raise
    trace_artifact["path"] = str(trace_path)
    screenshot_artifact["path"] = str(screenshot_path)
    return trace_artifact, screenshot_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    parser.add_argument("--variant", required=True, choices=VARIANTS)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help=(
            "run the strict source/input/validation controls without claiming "
            "an accepted exact output hash"
        ),
    )
    return parser


def _verify_pinned_sizes(paths: Mapping[str, Path]) -> None:
    for label, expected in PINNED_SIZES.items():
        actual = paths[label].stat().st_size
        if actual != expected:
            raise TraceLaunchError(
                f"{label} size mismatch: expected {expected}, got {actual}"
            )


def run(args: argparse.Namespace) -> dict[str, Any]:
    case = (args.scenario, args.variant)
    exploratory = bool(args.exploratory)
    expected_outputs = EXPECTED_OUTPUTS.get(case)
    if not exploratory and expected_outputs is None:
        raise TraceLaunchError(
            "this ownership trace has no accepted output contract; "
            "use --exploratory for a strict non-accepted diagnostic run"
        )
    if args.timeout < 1 or args.timeout > 300:
        raise TraceLaunchError("--timeout must be between 1 and 300 seconds")

    # Fail closed on unfrozen/mismatched source trust roots before resolving
    # any user-selected private input or creating the output directory.
    trust = load_trust_roots()

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
    if not shared_saves.is_dir() or not _inside(shared_saves, private_root):
        raise TraceLaunchError("shared Mesen Saves path is not a private directory")
    shared_saves_before = snapshot_private_files(shared_saves)

    pinned_inputs = {
        "archive": archive,
        "collector": COLLECTOR,
        "harfbuzz": harfbuzz,
        "mesen": mesen,
        "mesen_core": mesen_core,
        "nesdb": nesdb,
        "rom": rom,
        "scenario_contract": SCENARIO_CONTRACT_PATH,
        "settings": settings,
        "skia": skia,
        "state": state,
        "sram": sram,
        "validator": VALIDATOR_PATH,
    }
    expected_hashes = {
        **RUNTIME_HASHES,
        "collector": COLLECTOR_SHA256,
        "scenario_contract": SCENARIO_CONTRACT_SHA256,
        "validator": VALIDATOR_SHA256,
    }
    before = {
        label: require_hash(path, expected_hashes[label], label)
        for label, path in pinned_inputs.items()
    }
    _verify_pinned_sizes(
        {
            label: pinned_inputs[label]
            for label in PINNED_SIZES
        }
    )
    try:
        state_bytes = state.read_bytes()
    except OSError as exc:
        raise TraceLaunchError(f"could not read native checkpoint: {state}") from exc
    if hashlib.sha256(state_bytes).hexdigest() != before["state"]:
        raise TraceLaunchError("native checkpoint changed while being captured")
    if hashlib.sha256(trust.collector_source).hexdigest() != before["collector"]:
        raise TraceLaunchError("in-memory collector provenance drifted")
    if (
        hashlib.sha256(trust.scenario_contract_source).hexdigest()
        != before["scenario_contract"]
    ):
        raise TraceLaunchError("in-memory scenario contract provenance drifted")

    output_dir = prepare_private_output_dir(
        args.output_dir,
        forbidden_roots=(shared_saves,),
    )
    trace_path = output_dir / "trace.json"
    screenshot_path = output_dir / "endpoint.png"
    if any(os.path.lexists(path) for path in (trace_path, screenshot_path)):
        raise TraceLaunchError("refusing to overwrite ownership trace output")

    completed: subprocess.CompletedProcess[str] | None = None
    process_error: Exception | None = None
    staging_error: Exception | None = None
    staged_changed: list[str] = []
    staging_root_after: Path | None = None
    trace: dict[str, Any] | None = None
    trace_bytes: bytes | None = None
    screenshot_bytes: bytes | None = None
    collector_error_detail: str | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix=".mesen_wram_ownership_staging_",
            dir=output_dir,
        ) as staging_directory:
            staging_root = Path(staging_directory).resolve(strict=True)
            staging_root_after = staging_root
            if not _inside(staging_root, private_root):
                raise TraceLaunchError(
                    "temporary staging directory escaped private/"
                )
            staged_app = staging_root / "app"
            staged_saves = staged_app / "Saves"
            staged_saves.mkdir(parents=True)
            runtime_sources = {
                "mesen": mesen,
                "mesen_core": mesen_core,
                "harfbuzz": harfbuzz,
                "skia": skia,
                "nesdb": nesdb,
                "settings": settings,
            }
            runtime_names = {
                "mesen": "Mesen.exe",
                "mesen_core": "MesenCore.dll",
                "harfbuzz": "libHarfBuzzSharp.dll",
                "skia": "libSkiaSharp.dll",
                "nesdb": "MesenNesDB.txt",
                "settings": "settings.json",
            }
            staged_runtime: dict[str, Path] = {}
            for label, source_path in runtime_sources.items():
                destination = staged_app / runtime_names[label]
                shutil.copyfile(source_path, destination)
                staged_runtime[label] = destination.resolve(strict=True)

            unique_stem = f"pe_wram_ownership_{secrets.token_hex(12)}"
            staged_rom = staging_root / f"{unique_stem}.sfc"
            staged_sram = staged_saves / f"{unique_stem}.srm"
            staged_collector = staging_root / f"{unique_stem}.lua"
            staged_state = staging_root / f"{unique_stem}.mss"
            shutil.copyfile(rom, staged_rom)
            shutil.copyfile(sram, staged_sram)
            with staged_collector.open("xb") as handle:
                handle.write(trust.collector_source)
            with staged_state.open("xb") as handle:
                handle.write(state_bytes)
            staged_rom = staged_rom.resolve(strict=True)
            staged_sram = staged_sram.resolve(strict=True)
            staged_collector = staged_collector.resolve(strict=True)
            staged_state = staged_state.resolve(strict=True)

            staged_outputs = staging_root / "outputs"
            staged_outputs.mkdir(exist_ok=False)
            staged_trace = staged_outputs / "trace.json"
            staged_screenshot = staged_outputs / "endpoint.png"
            staged_error = staged_outputs / "trace.json.observer-error"
            for path in (staged_trace, staged_screenshot):
                with path.open("xb"):
                    pass
                if path.resolve(strict=True) != path:
                    raise TraceLaunchError("staged output path escaped staging")

            staged_files = {
                **staged_runtime,
                "collector": staged_collector,
                "rom": staged_rom,
                "sram": staged_sram,
                "state": staged_state,
            }
            staged_expected = {
                label: before[label]
                for label in (
                    "mesen",
                    "mesen_core",
                    "harfbuzz",
                    "skia",
                    "nesdb",
                    "settings",
                    "rom",
                    "sram",
                    "state",
                )
            }
            staged_expected["collector"] = before["collector"]
            for label, path in staged_files.items():
                if not _inside(path, staging_root):
                    raise TraceLaunchError(
                        f"staged {label} escaped private temporary root"
                    )
                if sha256_file(path) != staged_expected[label]:
                    raise TraceLaunchError(
                        f"staged {label} failed exact pre-launch hash check"
                    )

            environment = os.environ.copy()
            environment.update(
                {
                    "PE_SCENARIO": args.scenario,
                    "PE_VARIANT": args.variant,
                    "PE_STATE_PATH": str(staged_state),
                    "PE_TRACE_OUT": str(staged_trace),
                    "PE_TRACE_SCREENSHOT": str(staged_screenshot),
                }
            )
            command = [
                str(staged_runtime["mesen"]),
                "--testRunner",
                f"--timeout={args.timeout}",
                "--doNotSaveSettings",
                "--debug.scriptWindow.allowIoOsAccess=true",
                "--snes.port1.type=SnesController",
                str(staged_collector),
                str(staged_rom),
            ]
            creation_flags = (
                subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
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

            if os.path.lexists(staged_error):
                try:
                    collector_error_bytes = read_direct_file(
                        staged_error,
                        "staged collector error",
                        root=staged_outputs,
                        maximum=64 * 1024,
                    )
                    collector_error_detail = collector_error_bytes.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()
                except Exception as exc:
                    collector_error_detail = (
                        f"unreadable staged collector error: {exc}"
                    )

            for label, path in staged_files.items():
                try:
                    if sha256_file(path) != staged_expected[label]:
                        staged_changed.append(f"staged {label} changed")
                except OSError:
                    staged_changed.append(f"staged {label} missing")
            try:
                staged_save_entries = sorted(
                    path.name
                    for path in staged_saves.iterdir()
                    if path.is_file()
                )
            except OSError:
                staged_changed.append("staged Saves directory missing")
            else:
                if staged_save_entries != [staged_sram.name]:
                    staged_changed.append(
                        "staged Saves directory contains unexpected files"
                    )

            if (
                process_error is None
                and completed is not None
                and completed.returncode == EXPECTED_EXIT_CODE
            ):
                if os.path.lexists(staged_error):
                    raise TraceLaunchError(
                        "collector reported a staged observer error"
                    )
                trace_bytes = read_direct_file(
                    staged_trace,
                    "staged trace JSON",
                    root=staged_outputs,
                    maximum=MAX_TRACE_BYTES,
                )
                screenshot_bytes = read_direct_file(
                    staged_screenshot,
                    "staged endpoint PNG",
                    root=staged_outputs,
                    maximum=MAX_SCREENSHOT_BYTES,
                )
                describe_artifact_bytes(
                    screenshot_bytes,
                    "staged endpoint PNG",
                    png=True,
                )
                trace = load_trace_bytes(
                    trace_bytes,
                    args.scenario,
                    args.variant,
                    trust.validator,
                    label=str(staged_trace),
                )
                if not exploratory:
                    assert expected_outputs is not None
                    describe_artifact_bytes(
                        trace_bytes,
                        "trace JSON",
                        expected=expected_outputs["trace"],
                    )
                    describe_artifact_bytes(
                        screenshot_bytes,
                        "endpoint PNG",
                        png=True,
                        expected=expected_outputs["screenshot"],
                    )
    except Exception as exc:
        staging_error = exc

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
            "immutable emulator/source input mutation detected: "
            + ", ".join(changed)
        )
    shared_saves_after = snapshot_private_files(shared_saves)
    if shared_saves_after != shared_saves_before:
        raise TraceLaunchError("shared Mesen Saves directory changed")
    if staging_root_after is not None and os.path.lexists(staging_root_after):
        raise TraceLaunchError(
            "disposable ROM/SRAM/checkpoint staging directory was not deleted"
        )
    if staged_changed:
        raise TraceLaunchError(
            "disposable emulator input mutation detected: "
            + ", ".join(staged_changed)
        )
    if staging_error is not None:
        if isinstance(staging_error, TraceLaunchError):
            raise staging_error
        raise TraceLaunchError(
            f"private ownership-trace staging failed: {staging_error}"
        ) from staging_error
    if process_error is not None:
        raise TraceLaunchError(f"Mesen launch failed: {process_error}") from process_error
    assert completed is not None
    if completed.returncode != EXPECTED_EXIT_CODE:
        process_detail = (completed.stderr or completed.stdout or "").strip()
        detail_parts = []
        if collector_error_detail:
            detail_parts.append(f"collector: {collector_error_detail}")
        if process_detail:
            detail_parts.append(process_detail[-1600:])
        detail = " | ".join(detail_parts)
        suffix = f": {detail}" if detail else ""
        raise TraceLaunchError(
            f"Mesen returned {completed.returncode}, expected "
            f"{EXPECTED_EXIT_CODE}{suffix}"
        )
    if trace is None or trace_bytes is None or screenshot_bytes is None:
        raise TraceLaunchError(
            "Mesen did not produce both valid ownership-trace outputs"
        )

    trace_artifact, screenshot_artifact = publish_output_pair(
        output_dir,
        trace_path,
        trace_bytes,
        screenshot_path,
        screenshot_bytes,
    )
    status = (
        "exploratory-private-diagnostic-case-not-accepted"
        if exploratory
        else "accepted-private-diagnostic-case"
    )
    return {
        "status": status,
        "scenario": args.scenario,
        "variant": args.variant,
        "exit_code": completed.returncode,
        "callback_count": len(trace.get("callbacks", [])),
        "trace": trace_artifact,
        "screenshot": screenshot_artifact,
        "immutable_inputs_preserved": True,
        "shared_mesen_saves_preserved": True,
        "disposable_staging_deleted": True,
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
