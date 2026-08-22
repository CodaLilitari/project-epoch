#!/usr/bin/env python3
"""Validate two complete battle-action v4 trace roots and exact replay identity.

The six traces in each root must independently pass the accepted v4 semantic
validator.  Each replay JSON file must then be byte-for-byte identical to its
matching primary trace.  Screenshots are intentionally outside this gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any, Final


ROOT = Path(__file__).resolve().parents[1]
TRACE_VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_action_trace_v4.py"
)
TRACE_VALIDATOR_SIZE: Final = 20_306
TRACE_VALIDATOR_SHA256: Final = (
    "f7f23cdb9c196d4d0642cf2bb9aa2040"
    "834bd89fb0a5bb6044f65218e6974b3c"
)
SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-replay-v4"
)
SCENARIOS: Final = (
    "battle-action-control",
    "battle-attack-target-hold",
    "battle-attack-recovery",
)
VARIANTS: Final = ("zero", "canary")
TRACE_RELATIVE_PATHS: Final = tuple(
    Path(scenario) / variant / "trace.json"
    for scenario in SCENARIOS
    for variant in VARIANTS
)


class ReplayValidationError(RuntimeError):
    """A trace root is incomplete, invalid, or not an exact replay."""


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _load_exact_trace_validator() -> types.ModuleType:
    source = TRACE_VALIDATOR_PATH.read_bytes()
    if len(source) != TRACE_VALIDATOR_SIZE:
        raise ReplayValidationError("battle-action trace validator size drifted")
    actual = _sha256_bytes(source)
    if actual != TRACE_VALIDATOR_SHA256:
        raise ReplayValidationError(
            "battle-action trace validator SHA-256 drifted: "
            f"expected {TRACE_VALIDATOR_SHA256}, got {actual}"
        )
    code = compile(source, str(TRACE_VALIDATOR_PATH), "exec", dont_inherit=True)
    name = "_project_epoch_battle_action_trace_validator_for_replay_v4"
    module = types.ModuleType(name)
    module.__file__ = str(TRACE_VALIDATOR_PATH)
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


TRACE_VALIDATOR = _load_exact_trace_validator()


def _resolve_trace_paths(root: Path, label: str) -> list[Path]:
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ReplayValidationError(
            f"{label} trace root does not exist: {root}"
        ) from exc
    if not resolved_root.is_dir():
        raise ReplayValidationError(
            f"{label} trace root is not a directory: {resolved_root}"
        )
    paths: list[Path] = []
    for relative in TRACE_RELATIVE_PATHS:
        path = (resolved_root / relative).resolve(strict=False)
        try:
            path.relative_to(resolved_root)
        except ValueError as exc:
            raise ReplayValidationError(
                f"{label} trace escaped its root: {relative}"
            ) from exc
        if not path.is_file():
            raise ReplayValidationError(
                f"{label} trace is missing: {relative.as_posix()}"
            )
        paths.append(path)
    return paths


def validate_replay_roots(primary_root: Path, replay_root: Path) -> dict[str, Any]:
    primary_paths = _resolve_trace_paths(primary_root, "primary")
    replay_paths = _resolve_trace_paths(replay_root, "replay")
    if primary_paths[0].parents[2] == replay_paths[0].parents[2]:
        raise ReplayValidationError("primary and replay roots must differ")

    primary_summary = TRACE_VALIDATOR.validate_trace_files(primary_paths)
    replay_summary = TRACE_VALIDATOR.validate_trace_files(replay_paths)
    if primary_summary != replay_summary:
        raise ReplayValidationError(
            "primary and replay semantic summaries differ"
        )

    artifacts: list[dict[str, Any]] = []
    for relative, primary, replay in zip(
        TRACE_RELATIVE_PATHS,
        primary_paths,
        replay_paths,
        strict=True,
    ):
        primary_bytes = primary.read_bytes()
        replay_bytes = replay.read_bytes()
        if primary_bytes != replay_bytes:
            raise ReplayValidationError(
                f"replay trace differs: {relative.as_posix()}"
            )
        artifacts.append(
            {
                "path": relative.as_posix(),
                "size": len(primary_bytes),
                "sha256": _sha256_bytes(primary_bytes),
            }
        )

    return {
        "schema": SCHEMA,
        "status": "validated-exact-independent-replay",
        "trace_count_per_root": len(primary_paths),
        "trace_bytes_identical": True,
        "screenshots_in_acceptance_gate": False,
        "semantic_summary": primary_summary,
        "artifacts": artifacts,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_replay_roots(
            args.primary_root,
            args.replay_root,
        )
    except (
        ReplayValidationError,
        TRACE_VALIDATOR.BattleActionValidationError,
        TRACE_VALIDATOR.ActionProbeValidationError,
        TRACE_VALIDATOR.BattleTraceValidationError,
        TRACE_VALIDATOR.TraceValidationError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
