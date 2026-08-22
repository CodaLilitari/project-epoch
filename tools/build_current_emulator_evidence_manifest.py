#!/usr/bin/env python3
"""Build a deterministic hash manifest for local current-emulator evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections.abc import Iterable, Mapping


DEFAULT_ROOT = pathlib.Path("private/test_runs/retroarch/current")
DEFAULT_OUTPUT = DEFAULT_ROOT / "evidence_manifest.json"

REPRODUCTION_GROUPS = {
    "configuration": (
        "Create with apply_patch from the values documented in "
        "docs/current_emulator_replay_harness_2026-07-26.md."
    ),
    "stage-fixture": (
        "Copy the pinned clean ROM and recovered SRAM to isolated, "
        "same-stem files under current/roms and current/saves."
    ),
    "record-replay": (
        "Record with RetroArch -R, current bsnes, the null config, a "
        "disposable same-stem SRAM, and the documented max-frame count."
    ),
    "edit-replay": (
        "Run tools/edit_retroarch_bsv2_inputs.py or "
        "tools/inject_bsv2_wram_canary.py with the documented inputs."
    ),
    "play-replay": (
        "Play with RetroArch -P and the documented current-core config; "
        "capture logs, screenshots/video, or an on-exit RASTATE."
    ),
    "sram-diagnostic": (
        "Run the bounded current-bsnes save-directory probes documented in "
        "the current emulator replay harness."
    ),
}
EVIDENCE_LEVELS = {
    "verified-runtime",
    "verified-static",
    "documented",
    "hypothesis",
    "test-fixture",
    "diagnostic",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def classify(relative: pathlib.PurePath) -> tuple[str, str]:
    name = relative.name.lower()
    suffixes = "".join(relative.suffixes).lower()
    if relative.parts[0] in ("roms", "saves"):
        return "test-fixture", "stage-fixture"
    if suffixes == ".cfg":
        return "test-harness", "configuration"
    if "sram_" in name and name.endswith(".log"):
        return "diagnostic", "sram-diagnostic"
    if name.endswith(".bsv"):
        if "canary" in name or "candidate" in name:
            return "verified-runtime", "edit-replay"
        return "verified-runtime", "record-replay"
    if (
        name.endswith(".log")
        or name.endswith(".png")
        or name.endswith(".mkv")
        or name.endswith(".state.auto")
    ):
        return "verified-runtime", "play-replay"
    return "documented", "configuration"


def validate_relative_artifact_path(value: object) -> pathlib.PurePosixPath:
    if not isinstance(value, str) or not value:
        raise ValueError("accepted artifact path must be a nonempty string")
    relative = pathlib.PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(
            f"accepted artifact path must stay relative to the root: {value}"
        )
    if relative.as_posix() != value:
        raise ValueError(
            f"accepted artifact path must use normalized POSIX syntax: {value}"
        )
    return relative


def load_acceptance_spec(
    path: pathlib.Path,
) -> tuple[str, list[dict[str, str]]]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("schema") != "project-epoch-emulator-acceptance-v1":
        raise ValueError("unsupported acceptance-spec schema")
    raw_artifacts = source.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise ValueError("acceptance spec must contain a nonempty artifacts list")

    accepted: list[dict[str, str]] = []
    seen: set[pathlib.PurePosixPath] = set()
    for raw in raw_artifacts:
        if not isinstance(raw, Mapping):
            raise ValueError("each accepted artifact must be an object")
        relative = validate_relative_artifact_path(raw.get("path"))
        if relative in seen:
            raise ValueError(f"duplicate accepted artifact path: {relative}")
        seen.add(relative)

        evidence_level = raw.get("evidence_level")
        if evidence_level not in EVIDENCE_LEVELS:
            raise ValueError(
                f"invalid evidence level for {relative}: {evidence_level}"
            )
        reproduction_group = raw.get("reproduction_group")
        if reproduction_group not in REPRODUCTION_GROUPS:
            raise ValueError(
                "invalid reproduction group for "
                f"{relative}: {reproduction_group}"
            )
        accepted.append(
            {
                "path": relative.as_posix(),
                "evidence_level": str(evidence_level),
                "reproduction_group": str(reproduction_group),
            }
        )
    return sha256(path), accepted


def accepted_artifacts(
    root: pathlib.Path,
    accepted: Iterable[Mapping[str, str]],
    *,
    excluded: set[pathlib.Path],
) -> list[dict[str, object]]:
    root = root.resolve()
    artifacts: list[dict[str, object]] = []
    for entry in accepted:
        relative = validate_relative_artifact_path(entry.get("path"))
        path = (root / pathlib.Path(*relative.parts)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"accepted artifact escapes root: {relative}"
            ) from exc
        if path in excluded:
            raise ValueError(
                f"accepted artifact is also excluded output: {relative}"
            )
        if not path.is_file():
            raise FileNotFoundError(
                f"accepted artifact does not exist: {relative}"
            )
        artifacts.append(
            {
                "path": relative.as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
                "evidence_level": entry["evidence_level"],
                "reproduction_group": entry["reproduction_group"],
                "status": "accepted",
            }
        )
    artifacts.sort(key=lambda entry: str(entry["path"]))
    return artifacts


def build_manifest(
    root: pathlib.Path,
    *,
    excluded: set[pathlib.Path] | None = None,
    accepted: Iterable[Mapping[str, str]] | None = None,
    acceptance_spec_sha256: str | None = None,
) -> dict[str, object]:
    root = root.resolve()
    excluded = {path.resolve() for path in (excluded or set())}
    if accepted is None:
        artifacts: list[dict[str, object]] = []
        for path in sorted(
            (
                candidate
                for candidate in root.rglob("*")
                if candidate.is_file()
                and candidate.resolve() not in excluded
            ),
            key=lambda candidate: candidate.relative_to(root).as_posix(),
        ):
            relative = pathlib.PurePosixPath(path.relative_to(root).as_posix())
            evidence_level, reproduction_group = classify(relative)
            artifacts.append(
                {
                    "path": relative.as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                    "evidence_level": evidence_level,
                    "reproduction_group": reproduction_group,
                }
            )
        schema = "project-epoch-current-emulator-evidence-v1"
        curated = False
    else:
        artifacts = accepted_artifacts(
            root, accepted, excluded=excluded
        )
        schema = "project-epoch-current-emulator-evidence-v2"
        curated = True

    result: dict[str, object] = {
        "schema": schema,
        "local_only": True,
        "curated": curated,
        "root": DEFAULT_ROOT.as_posix(),
        "guide": "docs/current_emulator_replay_harness_2026-07-26.md",
        "reproduction_groups": REPRODUCTION_GROUPS,
        "artifacts": artifacts,
    }
    if acceptance_spec_sha256 is not None:
        result["acceptance_spec_sha256"] = acceptance_spec_sha256
    return result


def validate_private_output(path: pathlib.Path) -> pathlib.Path:
    workspace = pathlib.Path(__file__).resolve().parents[1]
    private_root = (workspace / "private").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError(
            "manifest output must remain under the workspace private/ tree"
        ) from exc
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--acceptance-spec",
        type=pathlib.Path,
        help=(
            "include only explicitly accepted artifacts from this "
            "source-controlled JSON spec"
        ),
    )
    args = parser.parse_args()

    output = validate_private_output(args.output)
    accepted = None
    acceptance_spec_sha256 = None
    if args.acceptance_spec is not None:
        acceptance_spec_sha256, accepted = load_acceptance_spec(
            args.acceptance_spec
        )
    manifest = build_manifest(
        args.root,
        excluded={output},
        accepted=accepted,
        acceptance_spec_sha256=acceptance_spec_sha256,
    )
    encoded = (
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    print(f"artifacts={len(manifest['artifacts'])}")
    print(f"manifest_sha256={hashlib.sha256(encoded).hexdigest()}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
