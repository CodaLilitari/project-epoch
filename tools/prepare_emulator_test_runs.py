#!/usr/bin/env python3
"""Prepare isolated emulator ROM/SRM pairs without touching canonical inputs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "tools" / "build_lucca_to_magus_clone_v1.py"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)
SAVE_PATH = ROOT / "private" / "input" / "lavos_save" / "chrono_trigger.srm"
RUN_ROOT = ROOT / "private" / "test_runs"

EXPECTED_SAVE_SHA256 = (
    "cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203"
)

RETIRED_UNSAFE_VARIANT = "runtime_unsafe"


def digest(data: bytes, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def load_builder():
    spec = importlib.util.spec_from_file_location("clone_builder_v1", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load builder: {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_if_absent_or_equal(path: pathlib.Path, data: bytes) -> None:
    if path.exists():
        existing = path.read_bytes()
        if existing != data:
            raise RuntimeError(
                f"refusing to overwrite changed test artifact: {path}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def prepare_variant(
    builder,
    clean_rom: bytes,
    clean_save: bytes,
    directory: str,
    stem: str,
    runtime_hook: str,
) -> dict[str, object]:
    result = builder.build_patch(clean_rom, runtime_hook=runtime_hook)
    run_dir = RUN_ROOT / directory
    rom_out = run_dir / f"{stem}.sfc"
    save_out = run_dir / f"{stem}.srm"
    write_if_absent_or_equal(rom_out, result.patched)
    write_if_absent_or_equal(save_out, clean_save)
    return {
        "runtime_hook": runtime_hook,
        "rom": {
            "path": str(rom_out.relative_to(ROOT)).replace("\\", "/"),
            "size": len(result.patched),
            "sha1": digest(result.patched, "sha1"),
            "sha256": digest(result.patched, "sha256"),
        },
        "save": {
            "path": str(save_out.relative_to(ROOT)).replace("\\", "/"),
            "size": len(clean_save),
            "sha256": digest(clean_save, "sha256"),
        },
        "ips": {
            "size": len(result.ips),
            "sha256": digest(result.ips, "sha256"),
        },
    }


def variant_specs(
    include_retired_unsafe: bool = False,
) -> tuple[tuple[str, str, str, str], ...]:
    """Return the diagnostic variants that may be prepared.

    The retired runtime experiment overwrites occupied EnemyRewardTable data.
    It is therefore excluded from the normal path and must be requested
    explicitly for historical reproduction.
    """

    specs = [
        (
            "static",
            "static",
            "chrono_trigger_lucca_magus_static",
            "none",
        )
    ]
    if include_retired_unsafe:
        specs.append(
            (
                RETIRED_UNSAFE_VARIANT,
                "runtime_unsafe",
                "chrono_trigger_lucca_magus_runtime_UNSAFE",
                "provisional",
            )
        )
    return tuple(specs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-retired-unsafe",
        action="store_true",
        help=(
            "also reproduce the quarantined runtime experiment that "
            "overwrites occupied EnemyRewardTable records"
        ),
    )
    args = parser.parse_args()

    builder = load_builder()
    clean_rom = ROM_PATH.read_bytes()
    clean_save = SAVE_PATH.read_bytes()
    builder.validate_input(clean_rom)
    if digest(clean_save, "sha256") != EXPECTED_SAVE_SHA256:
        raise RuntimeError("recovered Lavos save hash mismatch")

    variants = {
        name: prepare_variant(
            builder,
            clean_rom,
            clean_save,
            directory,
            stem,
            runtime_hook,
        )
        for name, directory, stem, runtime_hook in variant_specs(
            args.include_retired_unsafe
        )
    }
    manifest = {
        "canonical_inputs_unchanged": True,
        "builder_version": builder.VERSION,
        "retired_unsafe_variant_included": args.include_retired_unsafe,
        "retired_unsafe_variant_requires_explicit_opt_in": True,
        "variants": variants,
    }
    manifest_path = RUN_ROOT / "test_run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {manifest_path}")
    for name, variant in variants.items():
        print(f"{name}: {variant['rom']['path']}")


if __name__ == "__main__":
    main()
