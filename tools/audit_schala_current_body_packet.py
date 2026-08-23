#!/usr/bin/env python3
"""Audit the native-shaped packet fit of Schala's current body frames.

This source-only auditor combines the ten existing gameplay-foundation frames
with the six existing Glass Focus basic-Attack body poses.  It validates and
packs them entirely in memory, reconstructs every source canvas from the
serialized graphics and assembly bytes, and emits metadata-only JSON on
standard output.

It reads no ROM, save, emulator state, trace, or extracted game asset.  It has
no output-file option and writes no graphics, assembly, palette, image, ROM,
patch, or private artifact.  Its provisional source ordinals are not native
animation IDs, action bindings, pointers, allocations, or PC $07 integration.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import pathlib
import struct
import sys
from collections.abc import Sequence
from types import ModuleType
from typing import Any


AUDITOR_VERSION = "1.0.0"
REPORT_SCHEMA_VERSION = 1
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

GAMEPLAY_SOURCE_REL = pathlib.Path(
    "assets/source/schala/v0/gameplay/"
    "schala_gameplay_foundation_v0.json"
)
GAMEPLAY_MANIFEST_REL = pathlib.Path(
    "assets/source/schala/v0/gameplay/manifest_v0.json"
)
FOCUS_SOURCE_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_v0.json"
)
FOCUS_MANIFEST_REL = pathlib.Path(
    "assets/source/schala/v0/focus/glass_focus_pulse_manifest_v0.json"
)

SOURCE_ARTIFACTS: tuple[dict[str, Any], ...] = (
    {
        "path": GAMEPLAY_SOURCE_REL.as_posix(),
        "size": 25193,
        "sha256": (
            "9c0d4dd9a83b6c77822286fb89deb04a7f1ae49261dedb1013e108f598af6db2"
        ),
        "role": "ten original gameplay-foundation body frames and palette",
    },
    {
        "path": GAMEPLAY_MANIFEST_REL.as_posix(),
        "size": 5473,
        "sha256": (
            "6f1475c2945a2f4df922d6f8b4969e346e5846152284742ceb9f04b9bc3e3f65"
        ),
        "role": "gameplay provenance and deterministic-output contract",
    },
    {
        "path": FOCUS_SOURCE_REL.as_posix(),
        "size": 32967,
        "sha256": (
            "cb705f5faa5b01fd365c57d69428a64c3df5cb40170b68130043d4c4d3dd0869"
        ),
        "role": "six Glass Focus basic-Attack body poses and unbound media source",
    },
    {
        "path": FOCUS_MANIFEST_REL.as_posix(),
        "size": 6284,
        "sha256": (
            "dabbaa5b6a85d295f7726aa44683d96d6a8e0fbbf2d052e47c9b5d1b711c73f0"
        ),
        "role": "Glass Focus provenance, null bindings, and source-only boundary",
    },
)

BEHAVIOR_DEPENDENCIES: tuple[dict[str, Any], ...] = (
    {
        "path": "tools/build_schala_gameplay_foundation_v0.py",
        "size": 25402,
        "sha256": (
            "e43f5d5b6fe30c5746ef04822f98f120165ecbea8393143e5b93941fdeb6cf8f"
        ),
        "role": "indexed-source validation and SNES 4bpp/palette codecs",
    },
    {
        "path": "tools/build_schala_sprite_packet_foundation_v0.py",
        "size": 21211,
        "sha256": (
            "dc264823fdb479fef3c0a0d94e68da40b6bb0e51040c94392e678f970c3c60fb"
        ),
        "role": "four-object cover, native record serialization, and reconstruction",
    },
    {
        "path": "tools/validate_schala_glass_focus_pulse_v0.py",
        "size": 59563,
        "sha256": (
            "0a51bd8b6ccb30893e5adc8da78f00b61f98242a5ba0daf3403f33e2f4e3f93f"
        ),
        "role": "Glass Focus source, provenance, palette, and binding validation",
    },
)

GAMEPLAY_FRAME_IDS = (
    "schala_field_idle_down_f00_v0",
    "schala_field_idle_up_f00_v0",
    "schala_field_idle_left_f00_v0",
    "schala_field_idle_right_f00_v0",
    "schala_field_walk_down_f00_v0",
    "schala_field_walk_down_f01_v0",
    "schala_field_walk_down_f02_v0",
    "schala_battle_ready_f00_v0",
    "schala_battle_cast_gather_f00_v0",
    "schala_battle_cast_release_f00_v0",
)

FOCUS_BODY_FRAME_IDS = (
    "schala_battle_basic_attack_draw_f00_v0",
    "schala_battle_basic_attack_open_f01_v0",
    "schala_battle_basic_attack_pulse_f02_v0",
    "schala_battle_basic_attack_followthrough_f03_v0",
    "schala_battle_basic_attack_recoil_f04_v0",
    "schala_battle_basic_attack_recover_f05_v0",
)

BODY_FRAME_IDS = GAMEPLAY_FRAME_IDS + FOCUS_BODY_FRAME_IDS

FOCUS_INSERT_IDS = (
    "glass_focus_closed_crescent_v0",
    "glass_focus_open_ring_v0",
    "glass_focus_quarter_turn_ring_v0",
    "glass_focus_edge_on_ring_v0",
    "glass_focus_collapse_point_v0",
    "glass_focus_impact_arc_v0",
)

AUDIO_RECIPE_IDS = ("focus_swing_v0", "focus_hit_v0")

EXPECTED_PACKET = {
    "frame_count": 16,
    "record_size": 0x28,
    "assembly_size": 0x280,
    "assembly_sha256": (
        "b14735361a2546337d32ad3f8318a4138980c16515a7cbcc48a1b92de89d69d1"
    ),
    "tile_count_including_blank": 91,
    "nontransparent_unique_tile_count": 90,
    "graphics_size": 0x0B60,
    "graphics_sha256": (
        "361ea69917d97a8c68e4450df0b944e43c9dad73b3aca2ecf52304ed70484a66"
    ),
    "maximum_tile_index": 0x5A,
    "palette_size": 0x20,
    "palette_sha256": (
        "782a063ffc99087cca1b64876cd024a5c5c7e6c6193c8f9ff224e9ed88ead5ea"
    ),
    "three_object_frame_count": 1,
    "four_object_frame_count": 15,
}

EXPECTED_FOUNDATION_PREFIX = {
    "frame_count": 10,
    "graphics_size": 0x0A20,
    "graphics_sha256": (
        "61bdecf43ad967ff5bd3c7604d7ce0708305a516e1e17d7cbbcabe949f3c791f"
    ),
    "assembly_size": 0x0190,
    "assembly_sha256": (
        "11c7d77ec789853aca496b1bd38fdef35c437c31407000af74c7aa498bebb540"
    ),
}


class CurrentBodyPacketError(RuntimeError):
    """Raised when the additive packet audit cannot prove its contract."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_report_bytes(report: dict[str, Any]) -> bytes:
    return (
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _require_digest(
    raw: bytes,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> None:
    if len(raw) != expected_size:
        raise CurrentBodyPacketError(
            f"{label} size drifted: expected {expected_size}, got {len(raw)}"
        )
    actual = sha256(raw)
    if actual != expected_sha256:
        raise CurrentBodyPacketError(
            f"{label} SHA-256 drifted: expected {expected_sha256}, got {actual}"
        )


def verify_behavior_dependencies() -> list[dict[str, Any]]:
    """Hash-gate behavior-bearing helpers before importing or executing them."""

    verified: list[dict[str, Any]] = []
    for record in BEHAVIOR_DEPENDENCIES:
        relative = pathlib.PurePosixPath(record["path"])
        path = ROOT.joinpath(*relative.parts)
        raw = path.read_bytes()
        _require_digest(
            raw,
            record["size"],
            record["sha256"],
            f"behavior dependency {record['path']}",
        )
        verified.append(dict(record))
    return verified


def _load_helpers() -> tuple[ModuleType, ModuleType, ModuleType]:
    verify_behavior_dependencies()
    tools_text = str(TOOLS_DIR)
    if tools_text not in sys.path:
        sys.path.insert(0, tools_text)
    foundation = importlib.import_module(
        "build_schala_gameplay_foundation_v0"
    )
    packet = importlib.import_module(
        "build_schala_sprite_packet_foundation_v0"
    )
    focus = importlib.import_module(
        "validate_schala_glass_focus_pulse_v0"
    )
    return foundation, packet, focus


def _read_pinned_json(record: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    relative = pathlib.PurePosixPath(record["path"])
    path = ROOT.joinpath(*relative.parts)
    raw = path.read_bytes()
    _require_digest(
        raw,
        record["size"],
        record["sha256"],
        f"source artifact {record['path']}",
    )
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CurrentBodyPacketError(
            f"source artifact {record['path']} is not UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise CurrentBodyPacketError(
            f"source artifact {record['path']} must be a JSON object"
        )
    return raw, value


def _require_gameplay_manifest(
    manifest: dict[str, Any], source_raw: bytes
) -> None:
    if manifest.get("status") != "partial-animation-foundation":
        raise CurrentBodyPacketError("gameplay manifest status drifted")
    if manifest.get("rom_integration") is not False:
        raise CurrentBodyPacketError(
            "gameplay manifest must remain non-integrated"
        )
    canonical = manifest.get("canonical_source")
    if not isinstance(canonical, dict):
        raise CurrentBodyPacketError(
            "gameplay manifest canonical_source is missing"
        )
    expected = {
        "path": GAMEPLAY_SOURCE_REL.as_posix(),
        "sha256": sha256(source_raw),
        "source_classification": "original-hand-pixelled-target-grid",
        "frame_count": len(GAMEPLAY_FRAME_IDS),
    }
    if canonical != expected:
        raise CurrentBodyPacketError(
            "gameplay manifest canonical source drifted"
        )
    builder = manifest.get("builder")
    if not isinstance(builder, dict):
        raise CurrentBodyPacketError("gameplay manifest builder is missing")
    if (
        builder.get("path")
        != "tools/build_schala_gameplay_foundation_v0.py"
        or builder.get("sha256")
        != BEHAVIOR_DEPENDENCIES[0]["sha256"]
    ):
        raise CurrentBodyPacketError("gameplay manifest builder drifted")


def _require_frame_identity(
    actual_gameplay: Sequence[str], actual_focus: Sequence[str]
) -> None:
    if tuple(actual_gameplay) != GAMEPLAY_FRAME_IDS:
        raise CurrentBodyPacketError("gameplay frame identity/order drifted")
    if tuple(actual_focus) != FOCUS_BODY_FRAME_IDS:
        raise CurrentBodyPacketError(
            "Glass Focus body frame identity/order drifted"
        )
    combined = tuple(actual_gameplay) + tuple(actual_focus)
    if combined != BODY_FRAME_IDS or len(set(combined)) != len(combined):
        raise CurrentBodyPacketError(
            "combined body frame identity is incomplete or duplicated"
        )


def load_validated_inputs() -> dict[str, Any]:
    """Load and validate only the four pinned Project Epoch source artifacts."""

    foundation, packet, focus = _load_helpers()
    source_records = {record["path"]: record for record in SOURCE_ARTIFACTS}
    gameplay_raw, gameplay_source = _read_pinned_json(
        source_records[GAMEPLAY_SOURCE_REL.as_posix()]
    )
    gameplay_manifest_raw, gameplay_manifest = _read_pinned_json(
        source_records[GAMEPLAY_MANIFEST_REL.as_posix()]
    )
    focus_raw, focus_source = _read_pinned_json(
        source_records[FOCUS_SOURCE_REL.as_posix()]
    )
    focus_manifest_raw, focus_manifest = _read_pinned_json(
        source_records[FOCUS_MANIFEST_REL.as_posix()]
    )

    _require_gameplay_manifest(gameplay_manifest, gameplay_raw)
    try:
        gameplay_frames = foundation.validate_source(gameplay_source)
        validated_focus = focus.validate_source(focus_source)
        focus_report = focus.validation_report(focus_raw, focus_source)
        focus.verify_manifest_core(
            focus_manifest, focus_raw, focus_report
        )
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        raise CurrentBodyPacketError(
            f"existing Schala source validation failed: {exc}"
        ) from exc

    _require_frame_identity(
        tuple(foundation.REQUIRED_FRAME_IDS), tuple(focus.FRAME_IDS)
    )
    if tuple(gameplay_frames) != GAMEPLAY_FRAME_IDS:
        raise CurrentBodyPacketError(
            "validated gameplay frame mapping drifted"
        )
    if tuple(validated_focus["frames"]) != FOCUS_BODY_FRAME_IDS:
        raise CurrentBodyPacketError(
            "validated Focus frame mapping drifted"
        )
    if tuple(validated_focus["inserts"]) != FOCUS_INSERT_IDS:
        raise CurrentBodyPacketError("Focus insert identity/order drifted")
    if tuple(focus.AUDIO_IDS) != AUDIO_RECIPE_IDS:
        raise CurrentBodyPacketError("Focus audio recipe identity drifted")
    if focus_report["frames"].get("assembly_packability_claimed") is not False:
        raise CurrentBodyPacketError(
            "Glass Focus source must retain its internal no-packability claim"
        )
    if focus_report.get("rom_installable") is not False:
        raise CurrentBodyPacketError("Glass Focus became ROM-installable")
    if focus_report.get("allocation_status") != "unbound":
        raise CurrentBodyPacketError("Glass Focus allocation became bound")
    bindings = focus_source.get("native_runtime_bindings")
    if not isinstance(bindings, dict) or any(
        value is not None for value in bindings.values()
    ):
        raise CurrentBodyPacketError(
            "Glass Focus contains a non-null native/runtime binding"
        )

    gameplay_palette = foundation.encode_snes_palette(
        foundation.palette_rgb(gameplay_source)
    )
    focus_palette = validated_focus["palette_bytes"]
    if focus_palette != gameplay_palette:
        raise CurrentBodyPacketError(
            "Glass Focus palette dependency differs from gameplay palette"
        )

    frames: list[dict[str, Any]] = []
    for frame_id in GAMEPLAY_FRAME_IDS:
        frame = gameplay_frames[frame_id]
        width, height, pixels = foundation.frame_pixels(frame)
        frames.append(
            {
                "id": frame_id,
                "source_set": "gameplay_foundation",
                "context": frame["context"],
                "width": width,
                "height": height,
                "pixels": tuple(pixels),
            }
        )
    for frame_id in FOCUS_BODY_FRAME_IDS:
        frame = validated_focus["frames"][frame_id]
        width, height, pixels = focus._parse_pixels(
            frame, focus.FRAME_DIMENSIONS
        )
        frames.append(
            {
                "id": frame_id,
                "source_set": "glass_focus_body",
                "context": frame["context"],
                "width": width,
                "height": height,
                "pixels": tuple(pixels),
            }
        )
    if tuple(frame["id"] for frame in frames) != BODY_FRAME_IDS:
        raise CurrentBodyPacketError(
            "constructed body frame sequence drifted"
        )

    try:
        foundation_packet = packet.compile_packets(
            gameplay_raw, gameplay_source
        )
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        raise CurrentBodyPacketError(
            f"existing ten-frame packet validation failed: {exc}"
        ) from exc

    return {
        "foundation": foundation,
        "packet_helper": packet,
        "focus_helper": focus,
        "gameplay_source_raw": gameplay_raw,
        "gameplay_manifest_raw": gameplay_manifest_raw,
        "focus_source_raw": focus_raw,
        "focus_manifest_raw": focus_manifest_raw,
        "palette": gameplay_palette,
        "frames": frames,
        "foundation_packet": foundation_packet,
    }


def compile_current_body_packet(
    frames: Sequence[dict[str, Any]],
    foundation: ModuleType,
    packet: ModuleType,
) -> dict[str, Any]:
    """Compile validated original body pixels using the existing packet form."""

    if tuple(frame.get("id") for frame in frames) != BODY_FRAME_IDS:
        raise CurrentBodyPacketError(
            "packet input frame sequence is not the pinned body inventory"
        )
    tile_bank: list[tuple[int, ...]] = [packet.BLANK_TILE]
    tile_indices: dict[tuple[int, ...], int] = {packet.BLANK_TILE: 0}
    assembly = bytearray()
    frame_records: list[dict[str, Any]] = []

    for source_ordinal, frame in enumerate(frames):
        frame_id = frame["id"]
        width = frame["width"]
        height = frame["height"]
        pixels = tuple(frame["pixels"])
        if width % 8 or height % 8 or len(pixels) != width * height:
            raise CurrentBodyPacketError(
                f"{frame_id}: invalid target-grid dimensions or pixels"
            )
        if any(type(value) is not int or not 0 <= value <= 0xF for value in pixels):
            raise CurrentBodyPacketError(
                f"{frame_id}: pixel index lies outside 4bpp"
            )
        occupied = packet.occupied_cells(pixels, width, height)
        try:
            active_origins = packet.select_object_origins(
                occupied, width // 8, height // 8
            )
        except ValueError as exc:
            raise CurrentBodyPacketError(
                f"{frame_id}: four-object cover failed: {exc}"
            ) from exc
        if len(active_origins) > packet.OBJECT_COUNT:
            raise CurrentBodyPacketError(
                f"{frame_id}: more than four active objects"
            )
        padded_origins: tuple[tuple[int, int] | None, ...] = (
            *active_origins,
            *(
                None
                for _ in range(packet.OBJECT_COUNT - len(active_origins))
            ),
        )
        ordered_tiles = packet._ordered_object_tiles(
            pixels, width, height, padded_origins
        )
        words: list[int] = []
        for tile in ordered_tiles:
            if tile not in tile_indices:
                next_index = len(tile_bank)
                if next_index > packet.TILE_INDEX_MASK:
                    raise CurrentBodyPacketError(
                        "$07FF tile-index ceiling exceeded"
                    )
                tile_indices[tile] = next_index
                tile_bank.append(tile)
            words.append(tile_indices[tile])
        if len(words) != packet.TILE_WORD_COUNT or any(
            word & ~packet.TILE_INDEX_MASK for word in words
        ):
            raise CurrentBodyPacketError(
                f"{frame_id}: invalid tile-word stream"
            )

        anchor_x = width // 2
        anchor_y = height
        coordinate_bytes = bytearray()
        for origin in padded_origins:
            if origin is None:
                x_offset = 0
                y_offset = 0
            else:
                x_offset = origin[0] * 8 - anchor_x
                y_offset = origin[1] * 8 - anchor_y
            try:
                coordinate_bytes.extend(
                    (
                        packet._signed_byte(x_offset),
                        packet._signed_byte(y_offset),
                    )
                )
            except ValueError as exc:
                raise CurrentBodyPacketError(
                    f"{frame_id}: assembly coordinate overflow"
                ) from exc
        record = struct.pack("<16H", *words) + bytes(coordinate_bytes)
        if len(record) != packet.FRAME_RECORD_SIZE:
            raise CurrentBodyPacketError(
                f"{frame_id}: assembly record is not $28 bytes"
            )
        assembly.extend(record)
        frame_records.append(
            {
                "frame_id": frame_id,
                "frame_index": source_ordinal,
                "source_set": frame["source_set"],
                "context": frame["context"],
                "canvas": {"width": width, "height": height},
                "anchor": {"x": anchor_x, "y": anchor_y},
                "active_object_count": len(active_origins),
                "occupied_source_cell_count": len(occupied),
                "record_sha256": sha256(record),
            }
        )

    graphics = b"".join(
        foundation.encode_snes_4bpp(tile, 8, 8) for tile in tile_bank
    )
    assembly_bytes = bytes(assembly)
    for frame, frame_record in zip(frames, frame_records, strict=True):
        reconstructed = packet.reconstruct_frame(
            graphics, assembly_bytes, frame_record
        )
        expected = (
            frame["width"],
            frame["height"],
            tuple(frame["pixels"]),
        )
        if reconstructed != expected:
            raise CurrentBodyPacketError(
                f"{frame['id']}: serialized reconstruction mismatch"
            )

    return {
        "graphics": graphics,
        "assembly": assembly_bytes,
        "tile_count": len(tile_bank),
        "maximum_tile_index": max(tile_indices.values()),
        "frame_records": frame_records,
        "all_frames_reconstruct_exactly": True,
    }


def require_expected_packet(
    compiled: dict[str, Any],
    palette: bytes,
    foundation_packet: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless the additive packet has the pinned exact result."""

    graphics = compiled["graphics"]
    assembly = compiled["assembly"]
    frame_records = compiled["frame_records"]
    object_counts = [
        record["active_object_count"] for record in frame_records
    ]
    actual = {
        "frame_count": len(frame_records),
        "record_size": len(assembly) // len(frame_records),
        "assembly_size": len(assembly),
        "assembly_sha256": sha256(assembly),
        "tile_count_including_blank": compiled["tile_count"],
        "nontransparent_unique_tile_count": compiled["tile_count"] - 1,
        "graphics_size": len(graphics),
        "graphics_sha256": sha256(graphics),
        "maximum_tile_index": compiled["maximum_tile_index"],
        "palette_size": len(palette),
        "palette_sha256": sha256(palette),
        "three_object_frame_count": object_counts.count(3),
        "four_object_frame_count": object_counts.count(4),
    }
    if actual != EXPECTED_PACKET:
        raise CurrentBodyPacketError(
            f"current body packet measurements drifted: {actual}"
        )

    foundation_graphics = foundation_packet["graphics"]
    foundation_assembly = foundation_packet["assembly"]
    actual_prefix = {
        "frame_count": len(GAMEPLAY_FRAME_IDS),
        "graphics_size": len(foundation_graphics),
        "graphics_sha256": sha256(foundation_graphics),
        "assembly_size": len(foundation_assembly),
        "assembly_sha256": sha256(foundation_assembly),
    }
    if actual_prefix != EXPECTED_FOUNDATION_PREFIX:
        raise CurrentBodyPacketError(
            f"existing ten-frame packet identity drifted: {actual_prefix}"
        )
    if not graphics.startswith(foundation_graphics):
        raise CurrentBodyPacketError(
            "additive graphics packet changed the ten-frame prefix"
        )
    if assembly[: len(foundation_assembly)] != foundation_assembly:
        raise CurrentBodyPacketError(
            "additive assembly packet changed an existing ten-frame record"
        )
    return {
        "packet": actual,
        "foundation_prefix": actual_prefix,
        "foundation_prefix_preserved": True,
        "new_unique_tile_count": (
            actual["tile_count_including_blank"]
            - foundation_packet["tile_count"]
        ),
        "new_assembly_record_count": (
            actual["frame_count"] - len(GAMEPLAY_FRAME_IDS)
        ),
    }


def build_report() -> dict[str, Any]:
    validated = load_validated_inputs()
    compiled = compile_current_body_packet(
        validated["frames"],
        validated["foundation"],
        validated["packet_helper"],
    )
    measurements = require_expected_packet(
        compiled,
        validated["palette"],
        validated["foundation_packet"],
    )
    frame_rows = []
    for record in compiled["frame_records"]:
        frame_rows.append(
            {
                "active_object_count": record["active_object_count"],
                "assembly_record_sha256": record["record_sha256"],
                "canvas": [
                    record["canvas"]["width"],
                    record["canvas"]["height"],
                ],
                "context": record["context"],
                "frame_id": record["frame_id"],
                "occupied_source_cell_count": record[
                    "occupied_source_cell_count"
                ],
                "source_ordinal": record["frame_index"],
                "source_set": record["source_set"],
            }
        )

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "audit": "project-epoch-schala-current-body-packet-v0",
        "auditor_version": AUDITOR_VERSION,
        "status": "partial-current-source-packability-verified",
        "scope": {
            "body_frame_count": len(BODY_FRAME_IDS),
            "gameplay_foundation_frame_count": len(GAMEPLAY_FRAME_IDS),
            "glass_focus_body_frame_count": len(FOCUS_BODY_FRAME_IDS),
            "source_ordinals_are_native_animation_ids": False,
            "animation_blob_emitted": False,
            "focus_inserts_composited": False,
            "rom_accessed": False,
            "files_written": False,
        },
        "source_artifacts": [dict(record) for record in SOURCE_ARTIFACTS],
        "behavior_dependencies": [
            dict(record) for record in BEHAVIOR_DEPENDENCIES
        ],
        "frame_inventory": frame_rows,
        "packet": {
            "record_shape": {
                "record_size": EXPECTED_PACKET["record_size"],
                "tile_word_count": 16,
                "coordinate_pair_count": 4,
                "maximum_active_object_count": 4,
                "tile_index_mask": "$07FF",
                "unsupported_flag_word_count": 0,
            },
            "graphics": {
                "size": EXPECTED_PACKET["graphics_size"],
                "sha256": EXPECTED_PACKET["graphics_sha256"],
                "tile_count_including_reserved_blank": EXPECTED_PACKET[
                    "tile_count_including_blank"
                ],
                "nontransparent_unique_tile_count": EXPECTED_PACKET[
                    "nontransparent_unique_tile_count"
                ],
                "maximum_tile_index": EXPECTED_PACKET[
                    "maximum_tile_index"
                ],
            },
            "assembly": {
                "size": EXPECTED_PACKET["assembly_size"],
                "sha256": EXPECTED_PACKET["assembly_sha256"],
                "record_count": EXPECTED_PACKET["frame_count"],
            },
            "palette": {
                "size": EXPECTED_PACKET["palette_size"],
                "sha256": EXPECTED_PACKET["palette_sha256"],
                "shared_existing_gameplay_palette": True,
                "second_palette_embedded": False,
            },
            "all_frames_reconstruct_exactly": compiled[
                "all_frames_reconstruct_exactly"
            ],
        },
        "additive_result": {
            "existing_ten_frame_graphics_prefix_preserved": measurements[
                "foundation_prefix_preserved"
            ],
            "existing_ten_frame_assembly_prefix_preserved": measurements[
                "foundation_prefix_preserved"
            ],
            "existing_foundation": measurements["foundation_prefix"],
            "new_unique_tile_count": measurements["new_unique_tile_count"],
            "new_assembly_record_count": measurements[
                "new_assembly_record_count"
            ],
        },
        "excluded_source_components": {
            "focus_insert_ids": list(FOCUS_INSERT_IDS),
            "focus_insert_policy": (
                "semantic-vocabulary-reference-not-composited"
            ),
            "audio_recipe_ids": list(AUDIO_RECIPE_IDS),
            "audio_recipe_policy": "validated-by-source-but-not-packet-data",
        },
        "evidence": {
            "source_identity": "verified-static",
            "native_shaped_packet_fit": "verified-static",
            "serialized_reconstruction": "verified-static",
            "visual_design": "proposal",
            "source_order": "proposal-only-not-native-animation-semantics",
            "runtime_rendering": "not performed",
            "rom_integration": "not performed",
        },
        "nonclaims": [
            "No animation-slot semantics or four-facing animation blob.",
            "No auxiliary-animation-family compiler or binding.",
            "No battle staging, DMA, timing, or expanded-bank read proof.",
            "No graphics, assembly, animation, palette, effect, or sound pointer.",
            "No action $90, item $E8, sound, or runtime descriptor binding.",
            "No ROM allocation, ROM write, patch, save, state, or trace.",
            "No logical PC $07 runtime identity, save/load, or New Game+ proof.",
            "No full 241-packet compressed-corpus or near-match originality claim.",
            "No change to Epoch or to any existing Project Epoch artifact.",
        ],
        "serialization_boundary": (
            "Only paths, IDs, counts, dimensions, hashes, evidence labels, "
            "and explicit nonclaims are serialized. No source rows, pixels, "
            "tile bytes, tile words, assembly bytes, palette bytes, images, "
            "ROM bytes, or decoded copyrighted data are included."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    sys.stdout.buffer.write(canonical_report_bytes(build_report()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
