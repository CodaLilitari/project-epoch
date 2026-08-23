#!/usr/bin/env python3
"""Build a private vanilla-Schala sprite compatibility bundle.

The bundle is derived only from the user's hash-gated Chrono Trigger US Rev0
ROM.  Extracted graphics, assembly, animation, and palette bytes are written
only below the ignored workspace ``private`` tree.  The metadata report
contains addresses, selectors, sizes, counts, and hashes but no game bytes.

This is a field-asset compatibility input, not a ROM patch, a logical PC $07
implementation, a battle packet, or production artwork.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
import pathlib
import stat
import struct
import sys
import tempfile
from collections.abc import Mapping, Sequence


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_ROOT = ROOT / "tools"
PRIVATE_ROOT_LEXICAL = ROOT / "private"
PRIVATE_ROOT = PRIVATE_ROOT_LEXICAL.resolve()
REPARSE_ATTRIBUTE = 0x0400
DEFAULT_ROM = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "private" / "build" / "schala_vanilla_npc_compat_v0"
)

SCHEMA_VERSION = 1
BUNDLE_ID = "schala-vanilla-npc-compat-v0"

CORPUS_TOOL_PATH = TOOLS_ROOT / "audit_ct_compressed_sprite_corpus.py"
CORPUS_TOOL_SIZE = 34_780
CORPUS_TOOL_SHA256 = (
    "5dcba015098dcf5a9ec754a5537f35ab"
    "67144f0ac09d166e7644741a74ae990d"
)

CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

SOURCE_NPC_ID = 0x09
PALETTE_VARIANT_NPC_ID = 0xCD
NPC_DESCRIPTOR_TABLE_FILE = 0x24F023
NPC_DESCRIPTOR_TABLE_SIZE = 0x500
NPC_DESCRIPTOR_TABLE_SHA256 = (
    "17ae540728c200cf02d60943b8ccdae87"
    "edc8cb425e603a24343c078732e3b8a"
)
NPC_DESCRIPTOR_FILE = 0x24F050
NPC_DESCRIPTOR = bytes((0x26, 0x1B, 0x80, 0x3B, 0x00))
NPC_DESCRIPTOR_SHA256 = (
    "dcfb1fcb9573e7cbf2cba1290b2bd187"
    "889a84efdbb67a4ca7d654288158eae8"
)
PALETTE_VARIANT_DESCRIPTOR_FILE = 0x24F424
PALETTE_VARIANT_DESCRIPTOR = bytes((0x26, 0x1B, 0x9F, 0x3B, 0x00))
PALETTE_VARIANT_DESCRIPTOR_SHA256 = (
    "41e0318fa8379ff61f108f09ea783569"
    "03f09f780d2d52af2a70610dc8243186"
)
EXPECTED_GEOMETRY_FAMILY_IDS = (SOURCE_NPC_ID, PALETTE_VARIANT_NPC_ID)

GFX_SELECTOR = 0x26
GFX_POINTER_ENTRY_FILE = 0x242072
GFX_POINTER_ENTRY_SHA256 = (
    "7822e4cd703e8fb82ba2766461562c54"
    "3e736992295644f3fa683f3a0da1005f"
)
GFX_PACKET_SNES = 0xD9E2CE
GFX_PACKET_FILE = 0x19E2CE
GFX_COMPRESSED_SIZE = 2_447
GFX_COMPRESSED_SHA256 = (
    "db9b1e5967ad25ba7af2692e077fa7d"
    "a73e3d9659280d81fbe8f00c64109e1a3"
)
GFX_DECOMPRESSED_SIZE = 2_528
GFX_DECOMPRESSED_SHA256 = (
    "69322758b77fff5701cb0d5edb4ca34a"
    "b4109c2313ececd37bc018106fe84b73"
)
GFX_TILE_COUNT = 79

ASSEMBLY_SELECTOR = 0x1B
ASSEMBLY_POINTER_PAIR_FILE = 0x242351
ASSEMBLY_POINTER_PAIR_SIZE = 6
ASSEMBLY_POINTER_PAIR_SHA256 = (
    "336be35e14d8458e6ef0b0f37d15c9a"
    "8f2962264b06a65549224173222bc0205"
)
ASSEMBLY_START_SNES = 0xDE2B48
ASSEMBLY_END_SNES = 0xDE2EE0
ASSEMBLY_FILE = 0x1E2B48
ASSEMBLY_SIZE = 0x398
ASSEMBLY_SHA256 = (
    "ed6ad15d16d60b2135d1af3bc6fb10d"
    "e283dcda744d06da33ea37699373d2314"
)
ASSEMBLY_RECORD_SIZE = 0x28
ASSEMBLY_RECORD_COUNT = 23
ASSEMBLY_TILE_WORD_COUNT = 16
TILE_INDEX_MASK = 0x07FF
HORIZONTAL_FLIP_FLAG = 0x4000

ANIMATION_SELECTOR = 0x3B
PRIMARY_BOUNDARY_PAIR_FILE = 0x242676
PRIMARY_BOUNDARY_PAIR_SIZE = 4
PRIMARY_BOUNDARY_PAIR_SHA256 = (
    "ae4d73e8e8834c9ac7551c90f40d732"
    "05126a4721ecfad1f99aa768cf6ed3702"
)
PRIMARY_START = 0x67A0
PRIMARY_END = 0x6830
PRIMARY_FILE = 0x2467A0
PRIMARY_SIZE = 0x90
PRIMARY_SHA256 = (
    "9331925cce8129be325dfe52107bbdf97"
    "21fc642db1d9f7216f9017f810cd4ff"
)
FACING_COUNT = 4
PRIMARY_FACING_SIZE = 0x24
ENTRYPOINT_STRIDE = 4
ENTRYPOINTS_PER_FACING = 9
ANIMATION_TERMINATOR = 0xFF

AUX_POINTER_PAIR_FILE = 0x242876
AUX_POINTER_PAIR_SIZE = 4
AUX_POINTER_PAIR_SHA256 = (
    "c2613ea41dc4c31ba71e5692e9692d07"
    "103475c6bd001a1cd5eca43b3f366f86"
)
AUX_START = 0xBC38
AUX_END = 0xBC5C
AUX_FILE = 0x24BC38
AUX_SIZE = 0x24
AUX_SHA256 = (
    "58d697a461a3674556a92d05e2b26df3"
    "c37badcd0068edc54f95e2b394e2052d"
)

PALETTE_SELECTOR = 0x80
PALETTE_RECORD_SIZE = 0x18
PALETTE_FILE = 0x240C00
PALETTE_SIZE = 0x18
PALETTE_COLOR_COUNT = 12
PALETTE_SHA256 = (
    "8d5953b31b0ca6624d94c0c29935d345"
    "19418bc04f9e780fc466dca0c0c9ef3d"
)

GRAPHICS_FILENAME = "schala_vanilla_npc_gfx_raw.4bpp"
ASSEMBLY_FILENAME = "schala_vanilla_npc_assembly.bin"
PRIMARY_FILENAME = "schala_vanilla_npc_primary_animation.bin"
AUX_FILENAME = "schala_vanilla_npc_aux_animation.bin"
PALETTE_FILENAME = "schala_vanilla_npc_palette_12colors.bgr555"
MANIFEST_FILENAME = "schala_vanilla_npc_compat_manifest_v0.json"
EXPECTED_ARTIFACT_NAMES = frozenset(
    {
        GRAPHICS_FILENAME,
        ASSEMBLY_FILENAME,
        PRIMARY_FILENAME,
        AUX_FILENAME,
        PALETTE_FILENAME,
        MANIFEST_FILENAME,
    }
)


class CompatibilityBuildError(RuntimeError):
    """Raised when the compatibility bundle cannot be proved exactly."""


@dataclasses.dataclass(frozen=True)
class Bundle:
    artifacts: Mapping[str, bytes]
    report: Mapping[str, object]
    report_bytes: bytes


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def canonical_json(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )


def _exact_slice(data: bytes, start: int, size: int, label: str) -> bytes:
    if start < 0 or size < 0 or start + size > len(data):
        raise CompatibilityBuildError(f"{label} lies outside the ROM")
    result = data[start : start + size]
    if len(result) != size:
        raise CompatibilityBuildError(f"{label} is truncated")
    return result


def _require_hash(
    data: bytes, expected_size: int, expected_sha256: str, label: str
) -> None:
    if len(data) != expected_size:
        raise CompatibilityBuildError(
            f"{label} size drifted: {len(data):#x} != {expected_size:#x}"
        )
    actual = sha256(data)
    if actual != expected_sha256:
        raise CompatibilityBuildError(
            f"{label} SHA-256 drifted: {actual} != {expected_sha256}"
        )


def _load_corpus_tool():
    raw = CORPUS_TOOL_PATH.read_bytes()
    _require_hash(
        raw, CORPUS_TOOL_SIZE, CORPUS_TOOL_SHA256, "strict C3 decoder"
    )
    spec = importlib.util.spec_from_file_location(
        "project_epoch_ct_sprite_corpus", CORPUS_TOOL_PATH
    )
    if spec is None or spec.loader is None:
        raise CompatibilityBuildError("cannot load strict C3 decoder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORPUS = _load_corpus_tool()


def validate_canonical_rom(rom: bytes) -> None:
    if len(rom) != CANONICAL_ROM_SIZE:
        raise CompatibilityBuildError(
            f"expected headerless 4 MiB ROM, got {len(rom):#x} bytes"
        )
    if sha1(rom) != CANONICAL_ROM_SHA1:
        raise CompatibilityBuildError("canonical ROM SHA-1 gate failed")
    if sha256(rom) != CANONICAL_ROM_SHA256:
        raise CompatibilityBuildError("canonical ROM SHA-256 gate failed")


def _read_pointer_pair(
    rom: bytes,
    *,
    file_offset: int,
    expected_sha256: str,
    width: int,
    label: str,
) -> tuple[int, int, bytes]:
    raw = _exact_slice(rom, file_offset, width * 2, label)
    _require_hash(raw, width * 2, expected_sha256, label)
    return (
        int.from_bytes(raw[:width], "little"),
        int.from_bytes(raw[width:], "little"),
        raw,
    )


def _decode_graphics(rom: bytes) -> tuple[bytes, bytes]:
    entry = _exact_slice(
        rom, GFX_POINTER_ENTRY_FILE, 3, "graphics selector $26 entry"
    )
    _require_hash(
        entry, 3, GFX_POINTER_ENTRY_SHA256, "graphics selector $26 entry"
    )
    pointer = int.from_bytes(entry, "little")
    if pointer != GFX_PACKET_SNES:
        raise CompatibilityBuildError("graphics selector $26 pointer drifted")
    try:
        file_offset = CORPUS.snes_hirom_to_file(pointer)
        packet = CORPUS.decode_c3_sprite_packet(rom, file_offset)
    except CORPUS.AuditError as exc:
        raise CompatibilityBuildError(str(exc)) from exc
    if file_offset != GFX_PACKET_FILE:
        raise CompatibilityBuildError("graphics packet file mapping drifted")
    compressed = _exact_slice(
        rom, file_offset, packet.compressed_size, "compressed graphics packet"
    )
    _require_hash(
        compressed,
        GFX_COMPRESSED_SIZE,
        GFX_COMPRESSED_SHA256,
        "compressed graphics packet",
    )
    _require_hash(
        packet.data,
        GFX_DECOMPRESSED_SIZE,
        GFX_DECOMPRESSED_SHA256,
        "decoded graphics packet",
    )
    if packet.backref_width_bits != 12 or packet.addendum_count != 0:
        raise CompatibilityBuildError("graphics compression form drifted")
    if len(packet.data) // 0x20 != GFX_TILE_COUNT:
        raise CompatibilityBuildError("graphics tile count drifted")
    return compressed, packet.data


def _read_assembly(rom: bytes) -> tuple[bytes, dict[str, object]]:
    start, end, _ = _read_pointer_pair(
        rom,
        file_offset=ASSEMBLY_POINTER_PAIR_FILE,
        expected_sha256=ASSEMBLY_POINTER_PAIR_SHA256,
        width=3,
        label="assembly selector $1B/$1C pointer pair",
    )
    if (start, end) != (ASSEMBLY_START_SNES, ASSEMBLY_END_SNES):
        raise CompatibilityBuildError("assembly selector boundaries drifted")
    try:
        file_start = CORPUS.snes_hirom_to_file(start)
        file_end = CORPUS.snes_hirom_to_file(end)
    except CORPUS.AuditError as exc:
        raise CompatibilityBuildError(str(exc)) from exc
    if (file_start, file_end) != (
        ASSEMBLY_FILE,
        ASSEMBLY_FILE + ASSEMBLY_SIZE,
    ):
        raise CompatibilityBuildError("assembly file mapping drifted")
    assembly = _exact_slice(rom, file_start, file_end - file_start, "assembly")
    _require_hash(assembly, ASSEMBLY_SIZE, ASSEMBLY_SHA256, "assembly")
    if len(assembly) % ASSEMBLY_RECORD_SIZE:
        raise CompatibilityBuildError("assembly is not record-aligned")
    record_count = len(assembly) // ASSEMBLY_RECORD_SIZE
    if record_count != ASSEMBLY_RECORD_COUNT:
        raise CompatibilityBuildError("assembly record count drifted")

    tile_indexes: set[int] = set()
    flag_families: set[int] = set()
    flipped_word_count = 0
    for record_index in range(record_count):
        record_start = record_index * ASSEMBLY_RECORD_SIZE
        words = struct.unpack_from(
            f"<{ASSEMBLY_TILE_WORD_COUNT}H", assembly, record_start
        )
        for word in words:
            tile_indexes.add(word & TILE_INDEX_MASK)
            flags = word & ~TILE_INDEX_MASK
            flag_families.add(flags)
            if flags & HORIZONTAL_FLIP_FLAG:
                flipped_word_count += 1
    if flag_families != {0, HORIZONTAL_FLIP_FLAG}:
        raise CompatibilityBuildError(
            f"unsupported assembly flag families: {sorted(flag_families)}"
        )
    if tile_indexes != set(range(GFX_TILE_COUNT)):
        raise CompatibilityBuildError(
            "assembly does not reference exactly graphics tiles $00-$4E"
        )
    return assembly, {
        "record_count": record_count,
        "record_size": ASSEMBLY_RECORD_SIZE,
        "tile_word_count_per_record": ASSEMBLY_TILE_WORD_COUNT,
        "distinct_tile_indexes": len(tile_indexes),
        "minimum_tile_index": min(tile_indexes),
        "maximum_tile_index": max(tile_indexes),
        "flag_families": ["$0000", "$4000-horizontal-flip"],
        "horizontal_flip_word_count": flipped_word_count,
    }


def _read_animation(rom: bytes) -> tuple[bytes, bytes, dict[str, object]]:
    primary_start, primary_end, _ = _read_pointer_pair(
        rom,
        file_offset=PRIMARY_BOUNDARY_PAIR_FILE,
        expected_sha256=PRIMARY_BOUNDARY_PAIR_SHA256,
        width=2,
        label="primary animation selector $3B/$3C boundaries",
    )
    if (primary_start, primary_end) != (PRIMARY_START, PRIMARY_END):
        raise CompatibilityBuildError("primary animation boundaries drifted")
    primary = _exact_slice(
        rom,
        0x240000 + primary_start,
        primary_end - primary_start,
        "primary animation",
    )
    _require_hash(primary, PRIMARY_SIZE, PRIMARY_SHA256, "primary animation")
    if len(primary) != FACING_COUNT * PRIMARY_FACING_SIZE:
        raise CompatibilityBuildError("primary facing geometry drifted")
    if PRIMARY_FACING_SIZE % ENTRYPOINT_STRIDE:
        raise CompatibilityBuildError("primary facing is not entrypoint-aligned")
    facings = tuple(
        primary[index * PRIMARY_FACING_SIZE : (index + 1) * PRIMARY_FACING_SIZE]
        for index in range(FACING_COUNT)
    )
    if any(facing.index(ANIMATION_TERMINATOR) != 1 for facing in facings):
        raise CompatibilityBuildError("primary facing terminator alignment drifted")
    referenced_frames = set(primary)
    referenced_frames.discard(ANIMATION_TERMINATOR)
    if referenced_frames != set(range(ASSEMBLY_RECORD_COUNT)):
        raise CompatibilityBuildError(
            "primary animation no longer references exactly frames $00-$16"
        )

    aux_start, aux_end, _ = _read_pointer_pair(
        rom,
        file_offset=AUX_POINTER_PAIR_FILE,
        expected_sha256=AUX_POINTER_PAIR_SHA256,
        width=2,
        label="auxiliary animation selector $3B/$3C pointers",
    )
    if (aux_start, aux_end) != (AUX_START, AUX_END):
        raise CompatibilityBuildError("auxiliary animation boundaries drifted")
    aux = _exact_slice(
        rom,
        0x240000 + aux_start,
        aux_end - aux_start,
        "auxiliary animation",
    )
    _require_hash(aux, AUX_SIZE, AUX_SHA256, "auxiliary animation")
    if len(aux) != PRIMARY_FACING_SIZE:
        raise CompatibilityBuildError(
            "auxiliary animation size no longer matches one facing"
        )
    if any(
        facing.index(ANIMATION_TERMINATOR) != aux.index(0)
        for facing in facings
    ):
        raise CompatibilityBuildError(
            "primary/auxiliary initial terminator alignment drifted"
        )
    return primary, aux, {
        "facing_count": FACING_COUNT,
        "bytes_per_facing": PRIMARY_FACING_SIZE,
        "entrypoint_stride": ENTRYPOINT_STRIDE,
        "entrypoints_per_facing": ENTRYPOINTS_PER_FACING,
        "referenced_frame_minimum": min(referenced_frames),
        "referenced_frame_maximum": max(referenced_frames),
        "referenced_frame_count": len(referenced_frames),
        "auxiliary_bytes": len(aux),
        "initial_terminator_alignment": "all-four-facings",
    }


def _read_palette(rom: bytes) -> bytes:
    expected_file = 0x240000 + PALETTE_SELECTOR * PALETTE_RECORD_SIZE
    if expected_file != PALETTE_FILE:
        raise CompatibilityBuildError("palette selector mapping drifted")
    palette = _exact_slice(rom, PALETTE_FILE, PALETTE_SIZE, "palette")
    _require_hash(palette, PALETTE_SIZE, PALETTE_SHA256, "palette")
    if len(palette) // 2 != PALETTE_COLOR_COUNT:
        raise CompatibilityBuildError("palette color count drifted")
    return palette


def _descriptor_geometry(record: bytes) -> tuple[int, int, int, int]:
    if len(record) != len(NPC_DESCRIPTOR):
        raise CompatibilityBuildError("NPC descriptor width drifted")
    return record[0], record[1], record[3], record[4]


def _read_descriptor_family(rom: bytes) -> tuple[bytes, bytes]:
    table = _exact_slice(
        rom,
        NPC_DESCRIPTOR_TABLE_FILE,
        NPC_DESCRIPTOR_TABLE_SIZE,
        "NPC descriptor table",
    )
    _require_hash(
        table,
        NPC_DESCRIPTOR_TABLE_SIZE,
        NPC_DESCRIPTOR_TABLE_SHA256,
        "NPC descriptor table",
    )

    def descriptor(npc_id: int) -> bytes:
        start = npc_id * len(NPC_DESCRIPTOR)
        return table[start : start + len(NPC_DESCRIPTOR)]

    primary = descriptor(SOURCE_NPC_ID)
    variant = descriptor(PALETTE_VARIANT_NPC_ID)
    _require_hash(
        primary,
        len(NPC_DESCRIPTOR),
        NPC_DESCRIPTOR_SHA256,
        "NPC $09 descriptor",
    )
    _require_hash(
        variant,
        len(PALETTE_VARIANT_DESCRIPTOR),
        PALETTE_VARIANT_DESCRIPTOR_SHA256,
        "NPC $CD descriptor",
    )
    if primary != NPC_DESCRIPTOR:
        raise CompatibilityBuildError("NPC $09 descriptor fields drifted")
    if variant != PALETTE_VARIANT_DESCRIPTOR:
        raise CompatibilityBuildError("NPC $CD descriptor fields drifted")

    geometry = _descriptor_geometry(primary)
    family_ids = tuple(
        npc_id
        for npc_id in range(0x100)
        if _descriptor_geometry(descriptor(npc_id)) == geometry
    )
    if family_ids != EXPECTED_GEOMETRY_FAMILY_IDS:
        raise CompatibilityBuildError(
            "NPC $09 same-geometry descriptor family drifted"
        )
    differing_fields = tuple(
        index
        for index, (left, right) in enumerate(zip(primary, variant))
        if left != right
    )
    if differing_fields != (2,):
        raise CompatibilityBuildError(
            "NPC $CD is no longer a palette-only descriptor variant"
        )
    return primary, variant


def build_bundle(rom: bytes) -> Bundle:
    validate_canonical_rom(rom)
    descriptor, palette_variant_descriptor = _read_descriptor_family(rom)

    compressed, graphics = _decode_graphics(rom)
    assembly, assembly_analysis = _read_assembly(rom)
    primary, aux, animation_analysis = _read_animation(rom)
    palette = _read_palette(rom)

    artifacts = {
        GRAPHICS_FILENAME: graphics,
        ASSEMBLY_FILENAME: assembly,
        PRIMARY_FILENAME: primary,
        AUX_FILENAME: aux,
        PALETTE_FILENAME: palette,
    }
    outputs = {
        name: {"size": len(data), "sha256": sha256(data)}
        for name, data in artifacts.items()
    }
    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": BUNDLE_ID,
        "status": "pass-private-canonical-npc-compatibility-source",
        "evidence": {
            "packet_reconstruction": "verified-static",
            "npc_09_semantic_identity": "documented-cross-reference",
            "supported_slot_compatibility": "not-tested",
            "logical_pc_07_compatibility": "not-tested",
            "runtime_performed": False,
            "runtime_logical_pc_07_exercised": False,
            "rom_mutated": False,
            "patch_emitted": False,
        },
        "intent": {
            "intended_logical_pc_id": 7,
            "source_npc_id": SOURCE_NPC_ID,
            "source_palette_variant_npc_id": PALETTE_VARIANT_NPC_ID,
            "source_classification": (
                "canonical-rom-derived-private-compatibility"
            ),
            "first_pass_visual_source": "vanilla-schala-npc-family",
            "original_project_epoch_art_status": (
                "preserved-unchanged-deferred-replacement-art"
            ),
            "crimson_echoes_material_included": False,
        },
        "canonical_rom": {
            "variant": "Chrono Trigger US Rev0, headerless",
            "size": len(rom),
            "sha1": sha1(rom),
            "sha256": sha256(rom),
        },
        "decoder_dependency": {
            "path": "tools/audit_ct_compressed_sprite_corpus.py",
            "size": CORPUS_TOOL_SIZE,
            "sha256": CORPUS_TOOL_SHA256,
        },
        "source_descriptor": {
            "npc_id": SOURCE_NPC_ID,
            "snes_address": "$E4:F050",
            "file_offset": "0x24F050",
            "sha256": sha256(descriptor),
            "fields": {
                "graphics_selector": GFX_SELECTOR,
                "assembly_selector": ASSEMBLY_SELECTOR,
                "palette_selector": PALETTE_SELECTOR,
                "animation_selector": ANIMATION_SELECTOR,
                "size_class": 0,
            },
        },
        "descriptor_family": {
            "table_file_offset": "0x24F023",
            "table_size": NPC_DESCRIPTOR_TABLE_SIZE,
            "table_sha256": NPC_DESCRIPTOR_TABLE_SHA256,
            "same_geometry_npc_ids": list(EXPECTED_GEOMETRY_FAMILY_IDS),
            "palette_only_variant": {
                "npc_id": PALETTE_VARIANT_NPC_ID,
                "snes_address": "$E4:F424",
                "file_offset": "0x24F424",
                "sha256": sha256(palette_variant_descriptor),
                "palette_selector": PALETTE_VARIANT_DESCRIPTOR[2],
                "semantic_identity": "not-claimed",
            },
        },
        "graphics": {
            "selector": GFX_SELECTOR,
            "pointer_entry_snes_address": "$E4:2072",
            "pointer_snes_address": "$D9:E2CE",
            "compressed_file_offset": "0x19E2CE",
            "compressed_size": len(compressed),
            "compressed_sha256": sha256(compressed),
            "decoded_size": len(graphics),
            "decoded_sha256": sha256(graphics),
            "tile_4bpp_count": len(graphics) // 0x20,
            "compression": {
                "back_reference_width_bits": 12,
                "addendum_count": 0,
            },
        },
        "assembly": {
            "selector": ASSEMBLY_SELECTOR,
            "pointer_entry_snes_address": "$E4:2351",
            "start_snes_address": "$DE:2B48",
            "end_snes_address_exclusive": "$DE:2EE0",
            "file_offset": "0x1E2B48",
            "size": len(assembly),
            "sha256": sha256(assembly),
            **assembly_analysis,
        },
        "primary_animation": {
            "selector": ANIMATION_SELECTOR,
            "boundary_entry_snes_address": "$E4:2676",
            "start_snes_address": "$E4:67A0",
            "end_snes_address_exclusive": "$E4:6830",
            "file_offset": "0x2467A0",
            "size": len(primary),
            "sha256": sha256(primary),
            **animation_analysis,
        },
        "auxiliary_animation": {
            "selector": ANIMATION_SELECTOR,
            "pointer_entry_snes_address": "$E4:2876",
            "start_snes_address": "$E4:BC38",
            "end_snes_address_exclusive": "$E4:BC5C",
            "file_offset": "0x24BC38",
            "size": len(aux),
            "sha256": sha256(aux),
        },
        "palette": {
            "selector": PALETTE_SELECTOR,
            "start_snes_address": "$E4:0C00",
            "end_snes_address_exclusive": "$E4:0C18",
            "file_offset": "0x240C00",
            "size": len(palette),
            "sha256": sha256(palette),
            "custom_color_count": len(palette) // 2,
        },
        "private_outputs": outputs,
        "eligibility": {
            "source_control_raw_bytes": False,
            "private_local_build": True,
            "production_rom_install": False,
            "public_patch": False,
            "logical_pc_07_runtime": False,
            "battle_packet": False,
            "menu_packet": False,
            "crimson_echoes_provider": False,
        },
        "preservation": {
            "graphics_source_entries_07_and_08_changed": False,
            "npc_descriptor_e4_f023_changed": False,
            "source_npc_09_changed": False,
            "epoch_name_data_changed": False,
            "epoch_vehicle_data_changed": False,
            "save_data_changed": False,
            "roster_data_changed": False,
        },
        "nonclaims": [
            "The private bundle is not a complete playable-character packet.",
            "The 23 field records do not prove battle, menu, overworld, portrait, save-preview, or PC $07 behavior.",
            "No hook, expanded allocation, descriptor relocation, ROM mutation, or patch is approved.",
            "No Crimson Echoes or Flames of Eternity bytes, art, source, or permission are included.",
            "The metadata report contains no graphics, assembly words, animation sequences, palette values, images, or extracted packet bytes.",
        ],
        "next_gate": (
            "build a private supported-slot field diagnostic with an explicit "
            "animation-entrypoint fallback policy before connecting this "
            "visual provider to logical PC $07"
        ),
    }
    report_bytes = canonical_json(report)
    complete_artifacts = dict(artifacts)
    complete_artifacts[MANIFEST_FILENAME] = report_bytes
    return Bundle(
        artifacts=complete_artifacts,
        report=report,
        report_bytes=report_bytes,
    )


def _inside(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_lexical_traversal(path: pathlib.Path, label: str) -> None:
    if any(part in {".", ".."} for part in path.parts):
        raise CompatibilityBuildError(f"{label} contains lexical traversal")


def _is_reparse(path: pathlib.Path) -> bool:
    metadata = path.lstat()
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & REPARSE_ATTRIBUTE
    )


def _require_real_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    if not os.path.lexists(path):
        raise CompatibilityBuildError(f"{label} does not exist: {path}")
    if _is_reparse(path):
        raise CompatibilityBuildError(
            f"{label} is a symlink, junction, or reparse point: {path}"
        )
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise CompatibilityBuildError(f"{label} is not a directory: {path}")
    return path.resolve(strict=True)


def _canonical_private_root() -> pathlib.Path:
    workspace = ROOT.resolve(strict=True)
    lexical = pathlib.Path(os.path.abspath(PRIVATE_ROOT_LEXICAL))
    private_root = _require_real_directory(lexical, "workspace private root")
    expected = workspace / "private"
    if private_root != expected or private_root != PRIVATE_ROOT:
        raise CompatibilityBuildError(
            f"workspace private root resolved away from {expected}: "
            f"{private_root}"
        )
    return private_root


def _ensure_real_child_directories(
    root: pathlib.Path, parts: Sequence[str]
) -> pathlib.Path:
    current = root
    for part in parts:
        if part in {"", ".", ".."}:
            raise CompatibilityBuildError(
                "output directory contains an invalid segment"
            )
        current = current / part
        if os.path.lexists(current):
            _require_real_directory(current, "output parent")
        else:
            current.mkdir()
            if _is_reparse(current):
                raise CompatibilityBuildError(
                    f"created output parent became a reparse point: {current}"
                )
            _require_real_directory(current, "created output parent")
    return current


def validate_private_output_dir(path: pathlib.Path) -> pathlib.Path:
    private_root = _canonical_private_root()
    raw = pathlib.Path(path)
    _reject_lexical_traversal(raw, "output directory")
    candidate = raw if raw.is_absolute() else ROOT / raw
    candidate = pathlib.Path(os.path.abspath(candidate))
    if candidate == private_root or not _inside(candidate, private_root):
        raise CompatibilityBuildError(
            f"output must remain below workspace private/: {path}"
        )
    relative = candidate.relative_to(private_root)
    parent = _ensure_real_child_directories(
        private_root, relative.parts[:-1]
    )
    output = parent / relative.parts[-1]
    if os.path.lexists(output):
        _require_real_directory(output, "output directory")
    resolved = output.resolve(strict=os.path.lexists(output))
    if resolved == private_root or not _inside(resolved, private_root):
        raise CompatibilityBuildError(
            f"output resolved outside workspace private/: {resolved}"
        )
    return resolved


def _stat_identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def _stable_read_regular_file(path: pathlib.Path) -> bytes:
    if not os.path.lexists(path):
        raise CompatibilityBuildError(f"artifact disappeared: {path}")
    if _is_reparse(path):
        raise CompatibilityBuildError(
            f"artifact is a symlink, junction, or reparse point: {path}"
        )
    path_before = path.lstat()
    if not stat.S_ISREG(path_before.st_mode):
        raise CompatibilityBuildError(f"artifact is not a regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags)
    try:
        opened_before = os.fstat(descriptor)
        if _stat_identity(opened_before) != _stat_identity(path_before):
            raise CompatibilityBuildError(
                f"artifact changed while it was opened: {path}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if not os.path.lexists(path) or _is_reparse(path):
        raise CompatibilityBuildError(
            f"artifact path changed during validation: {path}"
        )
    path_after = path.lstat()
    identities = {
        _stat_identity(path_before),
        _stat_identity(opened_before),
        _stat_identity(opened_after),
        _stat_identity(path_after),
    }
    if len(identities) != 1:
        raise CompatibilityBuildError(
            f"artifact changed during validation: {path}"
        )
    return b"".join(chunks)


def _validate_complete_existing_bundle(
    bundle: Bundle, output_dir: pathlib.Path
) -> None:
    expected_names = set(bundle.artifacts)
    actual_names = {child.name for child in output_dir.iterdir()}
    if actual_names != expected_names:
        raise CompatibilityBuildError(
            "refusing incomplete or unexpected existing output directory: "
            f"{output_dir}"
        )
    for name, expected in bundle.artifacts.items():
        path = output_dir / name
        actual = _stable_read_regular_file(path)
        if actual != expected:
            raise CompatibilityBuildError(
                f"refusing to overwrite a different existing artifact: {path}"
            )


def _write_exclusive_file(path: pathlib.Path, data: bytes) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags, 0o600)
    try:
        remaining = memoryview(data)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise CompatibilityBuildError(
                    f"short write while staging artifact: {path}"
                )
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _cleanup_staging_directory(staging_dir: pathlib.Path) -> None:
    if not os.path.lexists(staging_dir):
        return
    if _is_reparse(staging_dir):
        raise CompatibilityBuildError(
            f"refusing to clean reparse staging directory: {staging_dir}"
        )
    for child in staging_dir.iterdir():
        if _is_reparse(child) or not stat.S_ISREG(child.lstat().st_mode):
            raise CompatibilityBuildError(
                f"refusing to clean unexpected staging entry: {child}"
            )
        child.unlink()
    staging_dir.rmdir()


def _validate_bundle_artifact_names(bundle: Bundle) -> None:
    actual = set(bundle.artifacts)
    if actual != EXPECTED_ARTIFACT_NAMES:
        raise CompatibilityBuildError(
            "bundle artifact name set drifted from the exact allowlist"
        )
    for name in actual:
        candidate = pathlib.Path(name)
        if (
            candidate.is_absolute()
            or len(candidate.parts) != 1
            or candidate.name != name
            or name in {"", ".", ".."}
        ):
            raise CompatibilityBuildError(
                f"bundle artifact name is not a single basename: {name!r}"
            )


def write_bundle(bundle: Bundle, output_dir: pathlib.Path) -> pathlib.Path:
    _validate_bundle_artifact_names(bundle)
    output_dir = validate_private_output_dir(output_dir)
    if os.path.lexists(output_dir):
        _validate_complete_existing_bundle(bundle, output_dir)
        return output_dir

    staging_dir = pathlib.Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.staging-", dir=output_dir.parent
        )
    )
    try:
        if _is_reparse(staging_dir):
            raise CompatibilityBuildError(
                f"created staging directory is a reparse point: {staging_dir}"
            )
        if staging_dir.resolve(strict=True).parent != output_dir.parent:
            raise CompatibilityBuildError("staging directory escaped output parent")

        ordered_names = [MANIFEST_FILENAME]
        ordered_names.extend(
            sorted(set(bundle.artifacts) - {MANIFEST_FILENAME})
        )
        for name in ordered_names:
            _write_exclusive_file(staging_dir / name, bundle.artifacts[name])

        _validate_complete_existing_bundle(bundle, staging_dir)
        validated_output = validate_private_output_dir(output_dir)
        if validated_output != output_dir:
            raise CompatibilityBuildError("output path drifted before promotion")
        if os.path.lexists(output_dir):
            raise CompatibilityBuildError(
                f"output target appeared before promotion: {output_dir}"
            )
        os.rename(staging_dir, output_dir)
        _validate_complete_existing_bundle(bundle, output_dir)
        return output_dir
    except Exception as exc:
        if os.path.lexists(staging_dir):
            try:
                _cleanup_staging_directory(staging_dir)
            except Exception as cleanup_exc:
                raise CompatibilityBuildError(
                    "bundle staging failed and could not be cleaned; "
                    f"inspect private path {staging_dir}: {exc}"
                ) from cleanup_exc
        raise


def _summary(bundle: Bundle, output_dir: pathlib.Path | None) -> dict[str, object]:
    return {
        "status": bundle.report["status"],
        "bundle_id": BUNDLE_ID,
        "output_dir": str(output_dir) if output_dir is not None else None,
        "graphics_tiles": GFX_TILE_COUNT,
        "assembly_records": ASSEMBLY_RECORD_COUNT,
        "primary_facing_count": FACING_COUNT,
        "palette_custom_colors": PALETTE_COLOR_COUNT,
        "runtime_logical_pc_07_exercised": False,
        "production_eligible": False,
        "crimson_echoes_material_included": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=pathlib.Path, default=DEFAULT_ROM)
    parser.add_argument(
        "--output-dir", type=pathlib.Path, default=DEFAULT_OUTPUT_DIR
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="emit metadata JSON to stdout and write no extracted artifacts",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rom = args.rom.read_bytes()
    bundle = build_bundle(rom)
    if args.metadata_only:
        sys.stdout.buffer.write(bundle.report_bytes)
        return 0
    output_dir = write_bundle(bundle, args.output_dir)
    print(json.dumps(_summary(bundle, output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
