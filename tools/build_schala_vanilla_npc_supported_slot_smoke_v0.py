#!/usr/bin/env python3
"""Build a private Lucca-slot replay ROM from vanilla Schala NPC data.

This diagnostic derives Schala's canonical NPC-family graphics, assembly,
animation, auxiliary timing, and twelve-color palette from the user's exact
Chrono Trigger US Rev0 ROM.  It installs those assets only over Lucca's
already-supported field-data windows so the ordinary seven-PC field loader can
be exercised without making any logical PC $07, expanded-ROM, save, Tech,
item, recruitment, or production-allocation claim.

The NPC stream's nine numeric entrypoints do not yet have proved PC semantics.
This builder preserves those nine bounded source entrypoints by number only as
a private diagnostic hypothesis.  It gives selectors $09-$46 an explicit copy
of the source entrypoint-zero cell for the corresponding facing and shared
timing stream.  The result tests the complete provider stream while remaining
fail-closed for higher playable-PC selectors; it is not a complete or
semantically named animation set.

All ROM output is restricted to the ignored ``private`` tree.  The project-wide
write-intent and complete-diff guard must pass before any image is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

import build_schala_vanilla_npc_compat_v0 as provider
import validate_rom_write_intents as write_guard


VERSION = "0.2.2"
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
    / "schala_vanilla_npc_supported_slot_smoke_v0"
    / "schala_vanilla_npc_lucca_slot_smoke_v0_full_provider.sfc"
)

EXPECTED_ROM_SIZE = provider.CANONICAL_ROM_SIZE
EXPECTED_ROM_SHA256 = provider.CANONICAL_ROM_SHA256
EXPECTED_OUTPUT_SHA256 = (
    "75dc966ce377accf19ce1a7eb2ac200d5f68fbb94b9436eee7f09e613cc4ad42"
)

LUCCA_LOGICAL_ID = 2
LUCCA_GRAPHICS_START = 0x136B40
LUCCA_GRAPHICS_END = 0x140000
LUCCA_ASSEMBLY_START = 0x1C4E70
LUCCA_ASSEMBLY_END = 0x1C7490
LUCCA_PRIMARY_START = 0x243880
LUCCA_PRIMARY_END = 0x243CF0
LUCCA_AUX_START = 0x24AA20
LUCCA_AUX_END = 0x24AB3C
LUCCA_PALETTE_START = 0x240030
LUCCA_PALETTE_SIZE = 0x18

FACING_COUNT = 4
ENTRYPOINT_STRIDE = 4
LUCCA_FACING_SIZE = 0x11C
MAPPED_ENTRYPOINT_COUNT = LUCCA_FACING_SIZE // ENTRYPOINT_STRIDE
MAPPED_ENTRYPOINT_MAX = MAPPED_ENTRYPOINT_COUNT - 1
SOURCE_ENTRYPOINT_COUNT = provider.ENTRYPOINTS_PER_FACING
PRIMARY_TERMINATOR = 0xFF
AUX_TERMINATOR = 0x00

HEADER_COMPLEMENT = 0x00FFDC
HEADER_CHECKSUM = 0x00FFDE

EXPECTED_LUCCA_GRAPHICS_SHA256 = (
    "057719bb3ecfdd79b7bca4f3e6e3f49ba5d1fb86f3ca83aa4a5f4832fbd77d92"
)
EXPECTED_LUCCA_ASSEMBLY_SHA256 = (
    "d7fde66a7c71a33fb23c3bd5531e8f89241751b08d120f2bcebad09a8b3634ce"
)
EXPECTED_LUCCA_PRIMARY_SHA256 = (
    "850c331267d16be7b11611d4f69d2120fac8e0f314102794b47b09fa7c200607"
)
EXPECTED_LUCCA_AUX_SHA256 = (
    "ab76d471427face95fd53534352f59dbf4e2f301bf41e27d480b82e62e16645c"
)
EXPECTED_LUCCA_PALETTE_SHA256 = (
    "2084c2e5c29c159e535c87a8cd602672e056e24ba2f1da2051a83c2a82775dbe"
)


class SmokeBuildError(ValueError):
    """Raised when a private diagnostic invariant cannot be proved."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact_slice(data: bytes, start: int, end: int, label: str) -> bytes:
    if start < 0 or end < start or end > len(data):
        raise SmokeBuildError(f"{label} lies outside the ROM")
    result = data[start:end]
    if len(result) != end - start:
        raise SmokeBuildError(f"{label} is truncated")
    return result


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
            LUCCA_PRIMARY_START,
            LUCCA_PRIMARY_END,
            EXPECTED_LUCCA_PRIMARY_SHA256,
            "Lucca primary animation",
        ),
        (
            LUCCA_AUX_START,
            LUCCA_AUX_END,
            EXPECTED_LUCCA_AUX_SHA256,
            "Lucca auxiliary animation",
        ),
        (
            LUCCA_PALETTE_START,
            LUCCA_PALETTE_START + LUCCA_PALETTE_SIZE,
            EXPECTED_LUCCA_PALETTE_SHA256,
            "Lucca field palette",
        ),
    )
    for start, end, expected_hash, label in expected_regions:
        if sha256(_exact_slice(rom, start, end, label)) != expected_hash:
            raise SmokeBuildError(f"{label} preimage hash mismatch")


def _provider_assets(source_rom: bytes) -> dict[str, bytes]:
    try:
        bundle = provider.build_bundle(source_rom)
    except provider.CompatibilityBuildError as exc:
        raise SmokeBuildError(f"provider rejected source ROM: {exc}") from exc
    artifacts = dict(bundle.artifacts)
    expected_names = set(provider.EXPECTED_ARTIFACT_NAMES)
    if set(artifacts) != expected_names:
        raise SmokeBuildError("provider artifact set drifted")
    return artifacts


def build_safe_fallback_streams(
    provider_primary: bytes,
    provider_aux: bytes,
) -> tuple[bytes, bytes, tuple[int, ...], int, tuple[tuple[int, ...], ...]]:
    """Preserve bounded source entries and map high selectors to entry zero."""

    if len(provider_primary) != provider.FACING_COUNT * provider.PRIMARY_FACING_SIZE:
        raise SmokeBuildError("provider primary facing geometry drifted")
    if len(provider_aux) != provider.PRIMARY_FACING_SIZE:
        raise SmokeBuildError("provider auxiliary geometry drifted")

    facing_frames: list[int] = []
    terminator_offsets: list[tuple[int, ...]] = []
    for facing in range(FACING_COUNT):
        start = facing * provider.PRIMARY_FACING_SIZE
        block = provider_primary[start : start + provider.PRIMARY_FACING_SIZE]
        if len(block) != provider.PRIMARY_FACING_SIZE:
            raise SmokeBuildError("provider primary facing is truncated")
        if block[1] != PRIMARY_TERMINATOR:
            raise SmokeBuildError(
                "provider entrypoint zero lacks immediate primary termination"
            )
        frame = block[0]
        if frame == PRIMARY_TERMINATOR or frame >= provider.ASSEMBLY_RECORD_COUNT:
            raise SmokeBuildError("provider entrypoint-zero frame is invalid")
        facing_frames.append(frame)

        facing_terminators: list[int] = []
        for selector in range(SOURCE_ENTRYPOINT_COUNT):
            offset = selector * ENTRYPOINT_STRIDE
            try:
                terminator = block.index(PRIMARY_TERMINATOR, offset)
            except ValueError as exc:
                raise SmokeBuildError(
                    "provider primary entrypoint lacks an in-block terminator"
                ) from exc
            live = block[offset:terminator]
            if any(
                frame_id >= provider.ASSEMBLY_RECORD_COUNT for frame_id in live
            ):
                raise SmokeBuildError(
                    "provider primary entrypoint has invalid frame references"
                )
            facing_terminators.append(terminator - offset)
        terminator_offsets.append(tuple(facing_terminators))

    delay = provider_aux[0]
    if delay == AUX_TERMINATOR or provider_aux[1] != AUX_TERMINATOR:
        raise SmokeBuildError(
            "provider entrypoint zero lacks a nonzero delay and termination"
        )

    aux_terminator_offsets: list[int] = []
    for selector in range(SOURCE_ENTRYPOINT_COUNT):
        offset = selector * ENTRYPOINT_STRIDE
        try:
            terminator = provider_aux.index(AUX_TERMINATOR, offset)
        except ValueError as exc:
            raise SmokeBuildError(
                "provider auxiliary entrypoint lacks an in-block terminator"
            ) from exc
        aux_terminator_offsets.append(terminator - offset)
    if any(
        tuple(aux_terminator_offsets) != facing_offsets
        for facing_offsets in terminator_offsets
    ):
        raise SmokeBuildError(
            "provider primary and auxiliary entrypoint terminators diverge"
        )

    primary = bytearray([PRIMARY_TERMINATOR] * (FACING_COUNT * LUCCA_FACING_SIZE))
    auxiliary = bytearray([AUX_TERMINATOR] * LUCCA_FACING_SIZE)
    auxiliary[: provider.PRIMARY_FACING_SIZE] = provider_aux
    for facing in range(FACING_COUNT):
        source_start = facing * provider.PRIMARY_FACING_SIZE
        destination_start = facing * LUCCA_FACING_SIZE
        primary[
            destination_start : destination_start + provider.PRIMARY_FACING_SIZE
        ] = provider_primary[
            source_start : source_start + provider.PRIMARY_FACING_SIZE
        ]

    source_aux_fallback = provider_aux[:ENTRYPOINT_STRIDE]
    for selector in range(SOURCE_ENTRYPOINT_COUNT, MAPPED_ENTRYPOINT_COUNT):
        offset = selector * ENTRYPOINT_STRIDE
        auxiliary[offset : offset + ENTRYPOINT_STRIDE] = source_aux_fallback
        for facing in range(FACING_COUNT):
            source_start = facing * provider.PRIMARY_FACING_SIZE
            fallback = provider_primary[
                source_start : source_start + ENTRYPOINT_STRIDE
            ]
            destination = facing * LUCCA_FACING_SIZE + offset
            primary[destination : destination + ENTRYPOINT_STRIDE] = fallback

    return (
        bytes(primary),
        bytes(auxiliary),
        tuple(facing_frames),
        delay,
        tuple(terminator_offsets),
    )


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


def build_diagnostic(source_rom: bytes) -> tuple[bytes, dict[str, Any]]:
    validate_input(source_rom)
    artifacts = _provider_assets(source_rom)
    graphics = artifacts[provider.GRAPHICS_FILENAME]
    assembly = artifacts[provider.ASSEMBLY_FILENAME]
    provider_primary = artifacts[provider.PRIMARY_FILENAME]
    provider_aux = artifacts[provider.AUX_FILENAME]
    palette = artifacts[provider.PALETTE_FILENAME]

    if len(graphics) > LUCCA_GRAPHICS_END - LUCCA_GRAPHICS_START:
        raise SmokeBuildError("provider graphics exceed Lucca window")
    if len(assembly) > LUCCA_ASSEMBLY_END - LUCCA_ASSEMBLY_START:
        raise SmokeBuildError("provider assembly exceeds Lucca window")
    if len(palette) != LUCCA_PALETTE_SIZE:
        raise SmokeBuildError("provider palette is not twelve colors")

    (
        primary,
        auxiliary,
        facing_frames,
        delay,
        terminator_offsets,
    ) = build_safe_fallback_streams(provider_primary, provider_aux)
    if len(primary) != LUCCA_PRIMARY_END - LUCCA_PRIMARY_START:
        raise SmokeBuildError("fallback primary does not fill Lucca span")
    if len(auxiliary) != LUCCA_AUX_END - LUCCA_AUX_START:
        raise SmokeBuildError("fallback auxiliary does not fill Lucca span")

    image = bytearray(source_rom)
    changes: list[dict[str, Any]] = []
    _write_region(
        image,
        LUCCA_GRAPHICS_START,
        graphics,
        "vanilla Schala NPC graphics over Lucca packet prefix",
        changes,
    )
    _write_region(
        image,
        LUCCA_ASSEMBLY_START,
        assembly,
        "vanilla Schala NPC assembly over Lucca packet prefix",
        changes,
    )
    _write_region(
        image,
        LUCCA_PRIMARY_START,
        primary,
        "bounded Schala provider stream over Lucca primary animation span",
        changes,
    )
    _write_region(
        image,
        LUCCA_AUX_START,
        auxiliary,
        "bounded Schala provider timing over Lucca auxiliary animation span",
        changes,
    )
    _write_region(
        image,
        LUCCA_PALETTE_START,
        palette,
        "vanilla Schala NPC twelve-color palette over Lucca field palette",
        changes,
    )
    _update_checksum(source_rom, image, changes)
    result = bytes(image)
    validate_output_checksum(result)
    if (
        EXPECTED_OUTPUT_SHA256 != "PENDING"
        and sha256(result) != EXPECTED_OUTPUT_SHA256
    ):
        raise SmokeBuildError("diagnostic output SHA-256 drifted")

    report: dict[str, Any] = {
        "schema_version": 1,
        "builder_version": VERSION,
        "builder_sha256": sha256(pathlib.Path(__file__).read_bytes()),
        "provider_builder_sha256": sha256(pathlib.Path(provider.__file__).read_bytes()),
        "write_guard_sha256": sha256(pathlib.Path(write_guard.__file__).read_bytes()),
        "status": "private-supported-slot-provider-diagnostic-static-pass",
        "evidence_level": "verified-static",
        "artifact_class": "private-diagnostic-only",
        "source_rom_sha256": sha256(source_rom),
        "output_rom_sha256": sha256(result),
        "reproduction": {
            "command_template": (
                "py -3 tools/"
                "build_schala_vanilla_npc_supported_slot_smoke_v0.py "
                "--rom <canonical-private-rom.sfc> "
                "--output <ignored-private-output.sfc>"
            ),
            "steps": [
                (
                    "Provide the exact canonical headerless US Rev0 ROM "
                    "under ignored private storage."
                ),
                (
                    "Run the command template with distinct private input "
                    "and output paths."
                ),
                (
                    "Require the adjacent manifest to report images-valid, "
                    "exact preimages, and complete diff coverage."
                ),
                (
                    "Verify the complete output SHA-256 before using the "
                    "diagnostic in a replay."
                ),
            ],
            "required_source_sha256": sha256(source_rom),
            "expected_output_sha256": sha256(result),
        },
        "supported_logical_id": LUCCA_LOGICAL_ID,
        "logical_pc_07": False,
        "source_npc_id": provider.SOURCE_NPC_ID,
        "source_palette_variant_npc_id": provider.PALETTE_VARIANT_NPC_ID,
        "provider": {
            "derived_in_memory_from_canonical_rom": True,
            "graphics_sha256": sha256(graphics),
            "graphics_size": len(graphics),
            "assembly_sha256": sha256(assembly),
            "assembly_size": len(assembly),
            "assembly_record_count": len(assembly) // provider.ASSEMBLY_RECORD_SIZE,
            "source_primary_sha256": sha256(provider_primary),
            "source_primary_size": len(provider_primary),
            "source_auxiliary_sha256": sha256(provider_aux),
            "source_auxiliary_size": len(provider_aux),
            "palette_sha256": sha256(palette),
            "palette_size": len(palette),
        },
        "fallback_contract": {
            "source_entrypoint_cells_copied": list(
                range(SOURCE_ENTRYPOINT_COUNT)
            ),
            "source_entrypoint_semantics_claimed": False,
            "diagnostic_numeric_equivalence_only": True,
            "fallback_source_entrypoint": 0,
            "source_facing_block_order_preserved": True,
            "human_direction_names_claimed": False,
            "facing_entrypoint_zero_frame_ids": list(facing_frames),
            "entrypoint_zero_delay": delay,
            "source_terminator_offsets_by_facing": [
                list(offsets) for offsets in terminator_offsets
            ],
            "mapped_selector_minimum": 0,
            "mapped_selector_maximum": MAPPED_ENTRYPOINT_MAX,
            "mapped_selector_count": MAPPED_ENTRYPOINT_COUNT,
            "entrypoint_stride": ENTRYPOINT_STRIDE,
            "primary_terminator": PRIMARY_TERMINATOR,
            "auxiliary_terminator": AUX_TERMINATOR,
            "fallback_selector_minimum": SOURCE_ENTRYPOINT_COUNT,
            "fallback_sequence_shape": (
                "exact-source-entrypoint-zero-four-byte-cell"
            ),
            "complete_animation_semantics_claimed": False,
        },
        "write_policy": {
            "overwrites_existing_vanilla_data": True,
            "replaced_owner": "Lucca",
            "purpose": "temporary supported-slot field-provider replay",
            "exact_canonical_preimage_required": True,
            "production_use_forbidden": True,
            "epoch_data_changed": False,
            "source_npc_09_data_changed": False,
            "graphics_source_entries_07_and_08_changed": False,
        },
        "palette_contract": {
            "vanilla_custom_colors_loaded": 12,
            "indices_13_15_present": False,
            "purpose": "canonical-NPC field compatibility replay",
        },
        "character_record_changed": False,
        "roster_changed": False,
        "tech_or_item_data_changed": False,
        "save_layout_changed": False,
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
    """Declare every mutation for the mandatory complete-diff guard."""

    provider_report = report["provider"]
    writes = [
        _write_intent(
            source,
            target,
            write_id="schala-npc-smoke-graphics",
            classification="private-diagnostic-replacement",
            start=LUCCA_GRAPHICS_START,
            size=provider_report["graphics_size"],
            owner="schala-vanilla-npc-supported-slot-smoke",
            payload_kind="graphics",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-npc-smoke-assembly",
            classification="private-diagnostic-replacement",
            start=LUCCA_ASSEMBLY_START,
            size=provider_report["assembly_size"],
            owner="schala-vanilla-npc-supported-slot-smoke",
            payload_kind="graphics",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-npc-smoke-primary-fallback",
            classification="private-diagnostic-replacement",
            start=LUCCA_PRIMARY_START,
            size=LUCCA_PRIMARY_END - LUCCA_PRIMARY_START,
            owner="schala-vanilla-npc-supported-slot-smoke",
            payload_kind="table",
            table_id="lucca_animation",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-npc-smoke-auxiliary-fallback",
            classification="private-diagnostic-replacement",
            start=LUCCA_AUX_START,
            size=LUCCA_AUX_END - LUCCA_AUX_START,
            owner="schala-vanilla-npc-supported-slot-smoke",
            payload_kind="table",
            table_id="lucca_aux_animation",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-npc-smoke-palette",
            classification="private-diagnostic-replacement",
            start=LUCCA_PALETTE_START,
            size=LUCCA_PALETTE_SIZE,
            owner="schala-vanilla-npc-supported-slot-smoke",
            payload_kind="palette",
        ),
        _write_intent(
            source,
            target,
            write_id="schala-npc-smoke-checksum",
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
        "manifest_id": "schala-vanilla-npc-supported-slot-smoke-v0",
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
    final_report = {
        **report,
        "write_intent_manifest": write_intents,
        "write_intent_audit": write_audit,
    }
    manifest_bytes = (
        json.dumps(final_report, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    manifest_path = resolved.with_suffix(".manifest.json")
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise SmokeBuildError(
            "refusing to overwrite a different existing diagnostic manifest"
        )

    resolved.parent.mkdir(parents=True, exist_ok=True)
    if not resolved.exists():
        resolved.write_bytes(rom)
    if not manifest_path.exists():
        manifest_path.write_bytes(manifest_bytes)
    return resolved, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=pathlib.Path, default=DEFAULT_ROM)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
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
                "mapped_selector_maximum": report["fallback_contract"][
                    "mapped_selector_maximum"
                ],
                "logical_pc_07": report["logical_pc_07"],
                "runtime_verified": report["runtime_verified"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
