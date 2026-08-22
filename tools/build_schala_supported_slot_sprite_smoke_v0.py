#!/usr/bin/env python3
"""Build a private Lucca-slot smoke ROM for Schala's partial sprite packet.

This is a visual packet diagnostic, not an eighth-character implementation.
It temporarily replaces Lucca's supported graphics/assembly/palette data and
maps every Lucca animation byte to one of Schala's four original cardinal
idles.  It never edits PC identity, records, roster, techs, items, or saves.

The output is deliberately restricted to the ignored ``private`` tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

import build_schala_gameplay_foundation_v0 as gameplay
import build_schala_sprite_packet_foundation_v0 as packet_builder
import validate_rom_write_intents as write_guard


VERSION = "1.1.0"
ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve()
DEFAULT_ROM = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)
DEFAULT_OUTPUT = (
    ROOT
    / "private"
    / "test_runs"
    / "schala_supported_slot_sprite_smoke_v0"
    / "schala_lucca_slot_sprite_smoke_v0.sfc"
)

EXPECTED_ROM_SIZE = 0x400000
EXPECTED_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)

LUCCA_LOGICAL_ID = 2
LUCCA_GRAPHICS_START = 0x136B40
LUCCA_GRAPHICS_END = 0x140000
LUCCA_ASSEMBLY_START = 0x1C4E70
LUCCA_ASSEMBLY_END = 0x1C7490
LUCCA_ANIMATION_START = 0x243880
LUCCA_ANIMATION_END = 0x243CF0
LUCCA_PALETTE_START = 0x240030
LUCCA_PALETTE_SIZE = 0x18
LUCCA_ANIMATION_BLOCK_SIZE = 0x11C
CARDINAL_IDLE_FRAME_INDICES = (0, 1, 2, 3)

HEADER_COMPLEMENT = 0x00FFDC
HEADER_CHECKSUM = 0x00FFDE

EXPECTED_LUCCA_GRAPHICS_SHA256 = (
    "057719bb3ecfdd79b7bca4f3e6e3f49ba5d1fb86f3ca83aa4a5f4832fbd77d92"
)
EXPECTED_LUCCA_ASSEMBLY_SHA256 = (
    "d7fde66a7c71a33fb23c3bd5531e8f89241751b08d120f2bcebad09a8b3634ce"
)
EXPECTED_LUCCA_ANIMATION_SHA256 = (
    "850c331267d16be7b11611d4f69d2120fac8e0f314102794b47b09fa7c200607"
)


class SmokeBuildError(ValueError):
    """Raised when a diagnostic preimage or output invariant is violated."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_input(rom: bytes) -> None:
    if len(rom) != EXPECTED_ROM_SIZE:
        raise SmokeBuildError(
            f"expected 0x{EXPECTED_ROM_SIZE:X} bytes, got 0x{len(rom):X}"
        )
    if sha256(rom) != EXPECTED_ROM_SHA256:
        raise SmokeBuildError("canonical ROM SHA-256 mismatch")
    expected_regions = (
        (
            LUCCA_GRAPHICS_START,
            LUCCA_GRAPHICS_END,
            EXPECTED_LUCCA_GRAPHICS_SHA256,
            "Lucca graphics",
        ),
        (
            LUCCA_ASSEMBLY_START,
            LUCCA_ASSEMBLY_END,
            EXPECTED_LUCCA_ASSEMBLY_SHA256,
            "Lucca assembly",
        ),
        (
            LUCCA_ANIMATION_START,
            LUCCA_ANIMATION_END,
            EXPECTED_LUCCA_ANIMATION_SHA256,
            "Lucca animation",
        ),
    )
    for start, end, expected_hash, label in expected_regions:
        if sha256(rom[start:end]) != expected_hash:
            raise SmokeBuildError(f"{label} preimage hash mismatch")


def _write_region(
    image: bytearray,
    start: int,
    data: bytes,
    label: str,
    changes: list[dict[str, Any]],
) -> None:
    end = start + len(data)
    if start < 0 or end > len(image):
        raise SmokeBuildError(f"{label} write lies outside ROM")
    old = bytes(image[start:end])
    image[start:end] = data
    if old != data:
        changes.append(
            {
                "label": label,
                "file_start": start,
                "file_end_exclusive": end,
                "size": len(data),
                "old_sha256": sha256(old),
                "new_sha256": sha256(data),
            }
        )


def _update_checksum(
    source: bytes,
    image: bytearray,
    changes: list[dict[str, Any]],
) -> None:
    old_sum = int.from_bytes(
        source[HEADER_CHECKSUM : HEADER_CHECKSUM + 2], "little"
    )
    delta = (sum(image) - sum(source)) & 0xFFFF
    new_sum = (old_sum + delta) & 0xFFFF
    _write_region(
        image,
        HEADER_COMPLEMENT,
        (new_sum ^ 0xFFFF).to_bytes(2, "little"),
        "SNES checksum complement",
        changes,
    )
    _write_region(
        image,
        HEADER_CHECKSUM,
        new_sum.to_bytes(2, "little"),
        "SNES checksum",
        changes,
    )


def validate_output_checksum(image: bytes) -> None:
    complement = int.from_bytes(
        image[HEADER_COMPLEMENT : HEADER_COMPLEMENT + 2], "little"
    )
    checksum = int.from_bytes(
        image[HEADER_CHECKSUM : HEADER_CHECKSUM + 2], "little"
    )
    if complement ^ checksum != 0xFFFF:
        raise SmokeBuildError("output checksum pair is invalid")
    if sum(image) & 0xFFFF != checksum:
        raise SmokeBuildError("output checksum does not match ROM bytes")


def _smoke_animation(source_blob: bytes) -> bytes:
    if len(source_blob) != LUCCA_ANIMATION_BLOCK_SIZE * 4:
        raise SmokeBuildError("Lucca animation is not four equal blocks")
    output = bytearray(source_blob)
    for facing, frame_index in enumerate(CARDINAL_IDLE_FRAME_INDICES):
        start = facing * LUCCA_ANIMATION_BLOCK_SIZE
        end = start + LUCCA_ANIMATION_BLOCK_SIZE
        for index in range(start, end):
            if output[index] != 0xFF:
                output[index] = frame_index
    return bytes(output)


def build_diagnostic(
    source_rom: bytes,
) -> tuple[bytes, dict[str, Any]]:
    validate_input(source_rom)
    source_raw, source = gameplay.load_json(gameplay.DEFAULT_SOURCE)
    packet_outputs = packet_builder.build_outputs(source_raw, source)
    packet_builder.verify_exact_reconstruction(source, packet_outputs)

    graphics = packet_outputs[packet_builder.GRAPHICS_FILENAME]
    assembly = packet_outputs[packet_builder.ASSEMBLY_FILENAME][
        : len(CARDINAL_IDLE_FRAME_INDICES) * packet_builder.FRAME_RECORD_SIZE
    ]
    palette = packet_outputs[packet_builder.PALETTE_FILENAME]
    if len(graphics) > LUCCA_GRAPHICS_END - LUCCA_GRAPHICS_START:
        raise SmokeBuildError("partial graphics exceed Lucca window")
    if len(assembly) > LUCCA_ASSEMBLY_END - LUCCA_ASSEMBLY_START:
        raise SmokeBuildError("partial assembly exceeds Lucca window")
    if len(palette) != 0x20:
        raise SmokeBuildError("Schala palette is not 0x20 bytes")

    image = bytearray(source_rom)
    changes: list[dict[str, Any]] = []
    _write_region(
        image,
        LUCCA_GRAPHICS_START,
        graphics,
        "Schala partial graphics over Lucca packet prefix",
        changes,
    )
    _write_region(
        image,
        LUCCA_ASSEMBLY_START,
        assembly,
        "Schala four cardinal assembly records over Lucca prefix",
        changes,
    )
    smoke_animation = _smoke_animation(
        source_rom[LUCCA_ANIMATION_START:LUCCA_ANIMATION_END]
    )
    _write_region(
        image,
        LUCCA_ANIMATION_START,
        smoke_animation,
        "Lucca animation bytes mapped to Schala cardinal idles",
        changes,
    )
    _write_region(
        image,
        LUCCA_PALETTE_START,
        palette[2 : 2 + LUCCA_PALETTE_SIZE],
        "Schala colors 1-12 over Lucca field palette",
        changes,
    )
    _update_checksum(source_rom, image, changes)
    result = bytes(image)
    validate_output_checksum(result)

    report = {
        "schema_version": 1,
        "builder_version": VERSION,
        "builder_sha256": sha256(pathlib.Path(__file__).read_bytes()),
        "write_guard_sha256": sha256(
            pathlib.Path(write_guard.__file__).read_bytes()
        ),
        "status": "supported-slot-private-sprite-smoke-diagnostic",
        "artifact_class": "private-diagnostic-only",
        "write_policy": {
            "overwrites_existing_vanilla_data": True,
            "replaced_owner": "Lucca",
            "purpose": "temporary supported-slot visual test",
            "exact_canonical_preimage_required": True,
            "production_use_forbidden": True,
            "epoch_data_changed": False,
            "graphics_source_entries_07_and_08_changed": False,
        },
        "source_rom_sha256": sha256(source_rom),
        "output_rom_sha256": sha256(result),
        "source_art_sha256": sha256(source_raw),
        "graphics_packet_sha256": sha256(graphics),
        "assembly_prefix_sha256": sha256(assembly),
        "supported_logical_id": LUCCA_LOGICAL_ID,
        "logical_pc_07": False,
        "character_record_changed": False,
        "roster_changed": False,
        "tech_or_item_data_changed": False,
        "save_layout_changed": False,
        "cardinal_idle_frame_indices": list(CARDINAL_IDLE_FRAME_INDICES),
        "animation_semantics": (
            "every non-FF Lucca animation byte maps to one cardinal idle"
        ),
        "palette_contract": {
            "schala_visible_colors": 15,
            "vanilla_custom_colors_loaded": 12,
            "indices_13_15_runtime_correct": False,
            "purpose": "shape/order smoke only",
        },
        "runtime_verified": False,
        "rom_installable": False,
        "production_input": False,
        "changes": sorted(changes, key=lambda item: item["file_start"]),
    }
    return result, report


def _require_private_output(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(PRIVATE_ROOT):
        raise SmokeBuildError("diagnostic output must remain under private/")
    if resolved.suffix.lower() != ".sfc":
        raise SmokeBuildError("diagnostic output must use .sfc")
    return resolved


def _require_distinct_input_output(
    input_path: pathlib.Path,
    output_path: pathlib.Path,
) -> pathlib.Path:
    resolved_output = _require_private_output(output_path)
    if input_path.resolve() == resolved_output:
        raise SmokeBuildError("source ROM and diagnostic output must differ")
    return resolved_output


def _write_intent(
    source: bytes,
    target: bytes,
    *,
    write_id: str,
    classification: str,
    start: int,
    size: int,
    owner: str,
    payload_kind: str,
    table_id: str | None = None,
    header_field_id: str | None = None,
) -> dict[str, Any]:
    end = start + size
    return {
        "write_id": write_id,
        "classification": classification,
        "file_start": start,
        "size": size,
        "owner": owner,
        "payload_kind": payload_kind,
        "evidence": "verified-static",
        "preimage_sha256": sha256(source[start:end]),
        "replacement_sha256": sha256(target[start:end]),
        "allocation_id": None,
        "hook_id": None,
        "table_id": table_id,
        "header_field_id": header_field_id,
        "replacement_hex": None,
    }


def build_write_intent_manifest(
    source: bytes,
    target: bytes,
    report: dict[str, Any],
    output_path: pathlib.Path,
) -> dict[str, Any]:
    """Declare every diagnostic ROM mutation for the project-wide guard."""

    graphics_size = next(
        item["size"]
        for item in report["changes"]
        if item["label"].startswith("Schala partial graphics")
    )
    assembly_size = next(
        item["size"]
        for item in report["changes"]
        if item["label"].startswith("Schala four cardinal assembly")
    )
    writes = [
        _write_intent(
            source,
            target,
            write_id="schala-smoke-graphics",
            classification="private-diagnostic-replacement",
            start=LUCCA_GRAPHICS_START,
            size=graphics_size,
            owner="schala-supported-slot-smoke",
            payload_kind="graphics",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-smoke-assembly",
            classification="private-diagnostic-replacement",
            start=LUCCA_ASSEMBLY_START,
            size=assembly_size,
            owner="schala-supported-slot-smoke",
            payload_kind="graphics",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-smoke-animation",
            classification="private-diagnostic-replacement",
            start=LUCCA_ANIMATION_START,
            size=LUCCA_ANIMATION_END - LUCCA_ANIMATION_START,
            owner="schala-supported-slot-smoke",
            payload_kind="table",
            table_id="lucca_animation",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-smoke-palette",
            classification="private-diagnostic-replacement",
            start=LUCCA_PALETTE_START,
            size=LUCCA_PALETTE_SIZE,
            owner="schala-supported-slot-smoke",
            payload_kind="palette",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-smoke-checksum",
            classification="managed-header-field",
            start=HEADER_COMPLEMENT,
            size=4,
            owner="rom_checksum_finalizer",
            payload_kind="header",
            header_field_id="hirom_checksum_pair",
        ),
    ]
    relative_output = output_path.resolve().relative_to(ROOT).as_posix()
    return {
        "schema_version": write_guard.SCHEMA_VERSION,
        "manifest_id": "schala-supported-slot-sprite-smoke-v0",
        "build_mode": "private-diagnostic",
        "source_kind": write_guard.CANONICAL_SOURCE_KIND,
        "source_size": len(source),
        "source_sha256": sha256(source),
        "target_size": len(target),
        "target_sha256": sha256(target),
        "output_path": relative_output,
        "allocations": [],
        "writes": sorted(
            writes,
            key=lambda item: (item["file_start"], item["write_id"]),
        ),
    }


def write_outputs(
    source_rom: bytes,
    rom: bytes,
    report: dict[str, Any],
    output_path: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path]:
    resolved = _require_private_output(output_path)
    if resolved.exists() and resolved.read_bytes() != rom:
        raise SmokeBuildError(
            "refusing to overwrite a different existing diagnostic ROM"
        )
    write_intents = build_write_intent_manifest(
        source_rom,
        rom,
        report,
        resolved,
    )
    write_audit = write_guard.audit_images(
        write_intents,
        source_rom,
        rom,
    )
    report = {
        **report,
        "write_intent_manifest": write_intents,
        "write_intent_audit": write_audit,
    }

    resolved.parent.mkdir(parents=True, exist_ok=True)
    if not resolved.exists():
        resolved.write_bytes(rom)
    manifest_path = resolved.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=pathlib.Path, default=DEFAULT_ROM)
    parser.add_argument(
        "--output", type=pathlib.Path, default=DEFAULT_OUTPUT
    )
    args = parser.parse_args()

    output = _require_distinct_input_output(args.rom, args.output)
    source_rom = args.rom.read_bytes()
    result, report = build_diagnostic(source_rom)
    rom_path, manifest_path = write_outputs(
        source_rom,
        result,
        report,
        output,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(rom_path),
                "manifest": str(manifest_path),
                "output_rom_sha256": report["output_rom_sha256"],
                "logical_pc_07": report["logical_pc_07"],
                "runtime_verified": report["runtime_verified"],
                "palette_indices_13_15_runtime_correct": report[
                    "palette_contract"
                ]["indices_13_15_runtime_correct"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
