#!/usr/bin/env python3
"""
Build the Project Epoch Lucca -> Magus ROM-only clone diagnostic v1.

The builder reads the canonical clean Chrono Trigger US Rev 0 ROM and emits
only an IPS patch, a Markdown report, and a JSON manifest. It never writes a
patched ROM.

The runtime hook is retained only to reproduce an earlier negative experiment.
Static reconstruction has since proved that its hook site is field-sprite
setup and that its apparent zero run is occupied enemy-reward data. Never use
the runtime-hook output as a base for further work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zlib
from dataclasses import asdict, dataclass

import validate_rom_write_intents as write_guard


VERSION = "1.3.0"
EXPECTED_SIZE = 0x400000
EXPECTED_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"

LUCCA = 2
MAGUS = 6

# Character graphics-source tables, verified against the clean ROM and the
# graphics loader beginning near file 0x0CE97E.
SPRITE_TABLES = [
    (0x242000, 3, "sprite graphics packet pointer"),
    (0x242300, 3, "sprite assembly packet pointer"),
    (0x242600, 2, "auxiliary graphics table A"),
    (0x242800, 2, "auxiliary graphics table B"),
]

# Public single-tech table families. There are eight single techs per PC.
TECH_TABLES = [
    (0x0C15CF, 11, "single-tech names"),
    (0x0C1ACD, 2, "single-tech targeting"),
    (0x0C214B, 12, "single-tech properties and power"),
    (0x0C253C, 1, "single-tech MP costs"),
    (0x0D45AD, 7, "single-tech graphics, sound, and effect selectors"),
]

# The seven 32x32, 4bpp portrait tile blocks are contiguous in this order:
# Marle, Lucca, Ayla, Crono, Frog, Robo, Magus. Each block is 0x200 bytes.
PORTRAIT_LUCCA_TILES = 0x3F1380
PORTRAIT_MAGUS_TILES = 0x3F1D80
PORTRAIT_TILE_LENGTH = 0x200
PORTRAIT_LUCCA_PALETTE = 0x3F2020
PORTRAIT_MAGUS_PALETTE = 0x3F1F80
PORTRAIT_PALETTE_LENGTH = 0x20

# Three seven-byte per-character attack-selector families. Static engine
# lookups index each family with the logical PC ID. Family A's exact runtime
# condition is still unresolved; its per-PC table shape is verified.
ATTACK_SELECTOR_FAMILIES = [
    (0x0D4000, "attack selector family A (precise condition unresolved)"),
    (0x0D4007, "normal-attack selector"),
    (0x0D400E, "critical-attack selector"),
]

# This byte is both family-normal[PC $07] and family-critical[Crono $00].
# It is occupied by vanilla behavior and must not be treated as a free slot.
OVERLOADED_PC7_ATTACK_BYTE = 0x0D400E

# TP thresholds have a two-byte dummy entry followed by eight u16 thresholds
# for each of the seven playable PCs.
TP_REQUIREMENT_BASE = 0x0C26F8
TP_REQUIREMENT_DUMMY_COUNT = 1
TP_REQUIREMENT_COUNT = 8
TP_REQUIREMENT_STRIDE = 2

# Documented per-character menu selector that v0 omitted.
LUCCA_MENU_ELEMENT = 0x02A2C8
MAGUS_MENU_ELEMENT = 0x02A2CC

# Retired runtime clone hook inherited from v0. Static reconstruction identifies
# HOOK_OFFSET as Field_SpriteAnimComputeBase: it reads the active-party ID and
# computes graphics/animation table indexes. It is not a character-record
# initialization hook. The mode remains available solely so the previously
# recorded negative experiment can be reproduced.
HOOK_OFFSET = 0x0CE980
HOOK_EXPECTED = bytes.fromhex("b9 80 29 0a")
HOOK_BYTES = bytes.fromhex("5c f6 63 cc")  # JML $CC63F6
HOOK_RETURN_OFFSET = 0x0CE984
HOOK_RETURN_EXPECTED = bytes.fromhex("48")
CAVE_OFFSET = 0x0C63F6
CAVE_ZERO_RUN_END = 0x0C6482
CAVE_BOUNDARY_BEFORE = 0x08
CAVE_BOUNDARY_AFTER = 0x98
# Static reconstruction identifies this entire region as the 256-entry,
# seven-byte EnemyRewardTable. Zero-valued records remain occupied data.
ENEMY_REWARD_TABLE_START = 0x0C5E00
ENEMY_REWARD_TABLE_END = 0x0C6500
ENEMY_REWARD_RECORD_COUNT = 256
ENEMY_REWARD_RECORD_STRIDE = 7
CAVE_BYTES = bytes.fromhex(
    "08 da 5a e2 20 c2 10 b9 80 29 c9 02 d0 21 a2 00 00 "
    "bf e0 27 7e 9f a0 26 7e e8 e0 50 00 d0 f2 "
    "af 36 28 7e 8f 32 28 7e af 3d 28 7e 8f 39 28 7e "
    "7a fa 28 b9 80 29 0a 5c 84 e9 cc"
)
CAVE_CONTEXT_OFFSET = 0x0C63E8
CAVE_CONTEXT_EXPECTED = bytes.fromhex(
    "eb 02 f4 01 c3 c3 78 5a 01 78 00 00 bf 08 00 00 "
    + "00 " * 0x38
)

HEADER_COMPLEMENT = 0x00FFDC
HEADER_CHECKSUM = 0x00FFDE

GUARDED_TABLES = (
    ("menu_element_icon_map", 0x02A2C6, 0x02A2CD),
    ("tech_names", 0x0C15CF, 0x0C1ACB),
    ("tech_target_modes", 0x0C1ACB, 0x0C1BB5),
    ("tech_properties", 0x0C214B, 0x0C249F),
    ("tech_mp_costs", 0x0C253B, 0x0C2583),
    ("tp_thresholds", 0x0C26FA, 0x0C276A),
    ("attack_selector_families", 0x0D4000, 0x0D4015),
    ("tech_effect_selectors", 0x0D45AD, 0x0D4735),
    ("pc_graphics_pointer_entries", 0x242000, 0x242015),
    ("pc_assembly_pointer_entries", 0x242300, 0x242315),
    ("pc_aux_graphics_entries", 0x242600, 0x24260E),
    ("pc_aux_animation_entries", 0x242800, 0x24280E),
)


@dataclass(frozen=True)
class Change:
    offset: int
    length: int
    description: str
    evidence: str
    old_sha256: str
    new_sha256: str
    old_hex: str | None = None
    new_hex: str | None = None


@dataclass(frozen=True)
class BuildResult:
    patched: bytes
    ips: bytes
    changes: tuple[Change, ...]
    runtime_hook: str


def digest(data: bytes, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def validate_input(orig: bytes) -> None:
    if len(orig) != EXPECTED_SIZE:
        raise ValueError(
            f"expected an unheadered 4 MiB ROM, got {len(orig):#x} bytes"
        )
    actual_sha1 = digest(orig, "sha1")
    if actual_sha1 != EXPECTED_SHA1:
        raise ValueError(
            f"input SHA-1 mismatch: expected {EXPECTED_SHA1}, got {actual_sha1}"
        )


def _change(
    offset: int,
    old: bytes,
    new: bytes,
    description: str,
    evidence: str,
) -> Change:
    show_hex = len(old) <= 0x20
    return Change(
        offset=offset,
        length=len(old),
        description=description,
        evidence=evidence,
        old_sha256=digest(old, "sha256"),
        new_sha256=digest(new, "sha256"),
        old_hex=old.hex(" ") if show_hex else None,
        new_hex=new.hex(" ") if show_hex else None,
    )


def clone_region(
    rom: bytearray,
    src: int,
    dst: int,
    length: int,
    description: str,
    evidence: str,
    changes: list[Change],
) -> None:
    old = bytes(rom[dst : dst + length])
    new = bytes(rom[src : src + length])
    if len(old) != length or len(new) != length:
        raise ValueError(f"clone region outside ROM: {src:#x} -> {dst:#x}")
    rom[dst : dst + length] = new
    if old != new:
        changes.append(_change(dst, old, new, description, evidence))


def write_region(
    rom: bytearray,
    dst: int,
    new: bytes,
    description: str,
    evidence: str,
    changes: list[Change],
) -> None:
    old = bytes(rom[dst : dst + len(new)])
    if len(old) != len(new):
        raise ValueError(f"write region outside ROM: {dst:#x}")
    rom[dst : dst + len(new)] = new
    if old != new:
        changes.append(_change(dst, old, new, description, evidence))


def update_header_checksum(
    orig: bytes, rom: bytearray, changes: list[Change]
) -> None:
    old_sum = int.from_bytes(
        orig[HEADER_CHECKSUM : HEADER_CHECKSUM + 2], "little"
    )
    delta = (sum(rom) - sum(orig)) & 0xFFFF
    new_sum = (old_sum + delta) & 0xFFFF
    new_complement = new_sum ^ 0xFFFF
    write_region(
        rom,
        HEADER_COMPLEMENT,
        new_complement.to_bytes(2, "little"),
        "SNES header checksum complement",
        "verified-static",
        changes,
    )
    write_region(
        rom,
        HEADER_CHECKSUM,
        new_sum.to_bytes(2, "little"),
        "SNES header checksum",
        "verified-static",
        changes,
    )


def validate_header_checksum(rom: bytes) -> None:
    stored_complement = int.from_bytes(
        rom[HEADER_COMPLEMENT : HEADER_COMPLEMENT + 2], "little"
    )
    stored_sum = int.from_bytes(
        rom[HEADER_CHECKSUM : HEADER_CHECKSUM + 2], "little"
    )
    if (stored_complement ^ stored_sum) != 0xFFFF:
        raise AssertionError("SNES checksum and complement do not XOR to 0xFFFF")
    if (sum(rom) & 0xFFFF) != stored_sum:
        raise AssertionError("SNES stored checksum does not match ROM byte sum")


def make_ips(orig: bytes, modified: bytes) -> bytes:
    if len(orig) != len(modified):
        raise ValueError("this IPS builder requires equal input and output sizes")
    out = bytearray(b"PATCH")
    index = 0
    while index < len(orig):
        if orig[index] == modified[index]:
            index += 1
            continue
        start = index
        data = bytearray()
        while (
            index < len(orig)
            and orig[index] != modified[index]
            and len(data) < 0xFFFF
        ):
            data.append(modified[index])
            index += 1
        if start == int.from_bytes(b"EOF", "big"):
            raise ValueError("IPS record would collide with the EOF sentinel")
        out += start.to_bytes(3, "big")
        out += len(data).to_bytes(2, "big")
        out += data
    out += b"EOF"
    return bytes(out)


def apply_ips(orig: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b"PATCH"):
        raise ValueError("invalid IPS header")
    out = bytearray(orig)
    cursor = 5
    while patch[cursor : cursor + 3] != b"EOF":
        if cursor + 5 > len(patch):
            raise ValueError("truncated IPS record")
        offset = int.from_bytes(patch[cursor : cursor + 3], "big")
        size = int.from_bytes(patch[cursor + 3 : cursor + 5], "big")
        cursor += 5
        if size:
            data = patch[cursor : cursor + size]
            if len(data) != size:
                raise ValueError("truncated IPS data")
            out[offset : offset + size] = data
            cursor += size
        else:
            if cursor + 3 > len(patch):
                raise ValueError("truncated IPS RLE record")
            run_length = int.from_bytes(patch[cursor : cursor + 2], "big")
            value = patch[cursor + 2]
            out[offset : offset + run_length] = bytes([value]) * run_length
            cursor += 3
    if cursor + 3 != len(patch):
        raise ValueError("unexpected IPS data after EOF")
    return bytes(out)


def validate_output_paths(
    rom_path: pathlib.Path,
    out_path: pathlib.Path,
    report_path: pathlib.Path,
    manifest_path: pathlib.Path,
) -> None:
    """Reject aliases that could overwrite an input or another artifact."""
    labeled_paths = {
        "input ROM": rom_path.resolve(),
        "IPS output": out_path.resolve(),
        "report output": report_path.resolve(),
        "manifest output": manifest_path.resolve(),
    }
    items = tuple(labeled_paths.items())
    for index, (left_label, left_path) in enumerate(items):
        for right_label, right_path in items[index + 1 :]:
            if left_path == right_path:
                raise ValueError(
                    f"path collision: {left_label} and {right_label} both "
                    f"resolve to {left_path}"
                )


def _assert_retired_invariants(orig: bytes, patched: bytes) -> None:
    for base, stride, _ in SPRITE_TABLES:
        entry7 = slice(base + 7 * stride, base + 8 * stride)
        entry8 = slice(base + 8 * stride, base + 9 * stride)
        if patched[entry7] != orig[entry7]:
            raise AssertionError(f"graphics table entry 7 changed at {base:#x}")
        if patched[entry8] != orig[entry8]:
            raise AssertionError(f"graphics table entry 8 changed at {base:#x}")
    if (
        patched[OVERLOADED_PC7_ATTACK_BYTE]
        != orig[OVERLOADED_PC7_ATTACK_BYTE]
    ):
        raise AssertionError(
            "overloaded PC $07 normal/Crono critical byte changed at 0x0D400E"
        )


def _guard_table_id(change: Change) -> str | None:
    end = change.offset + change.length
    for table_id, start, table_end in GUARDED_TABLES:
        if start <= change.offset and end <= table_end:
            return table_id
    return None


def _guard_write(
    orig: bytes,
    patched: bytes,
    change: Change,
) -> dict[str, object]:
    table_id = _guard_table_id(change)
    payload_kind = "table"
    classification = "private-diagnostic-replacement"
    owner = "lucca-to-magus-clone"
    header_field_id = None

    if table_id is None:
        if (
            PORTRAIT_LUCCA_TILES
            <= change.offset
            and change.offset + change.length
            <= PORTRAIT_LUCCA_TILES + PORTRAIT_TILE_LENGTH
        ):
            payload_kind = "graphics"
        elif (
            PORTRAIT_LUCCA_PALETTE
            <= change.offset
            and change.offset + change.length
            <= PORTRAIT_LUCCA_PALETTE + PORTRAIT_PALETTE_LENGTH
        ):
            payload_kind = "palette"
        elif change.offset in {HOOK_OFFSET, CAVE_OFFSET}:
            payload_kind = "code"
        else:
            raise AssertionError(
                f"unclassified clone diagnostic write at {change.offset:#x}"
            )

    start = change.offset
    end = start + change.length
    return {
        "write_id": f"lucca-clone-{start:06x}",
        "classification": classification,
        "file_start": start,
        "size": change.length,
        "owner": owner,
        "payload_kind": payload_kind,
        "evidence": "verified-static",
        "preimage_sha256": digest(orig[start:end], "sha256"),
        "replacement_sha256": digest(patched[start:end], "sha256"),
        "allocation_id": None,
        "hook_id": None,
        "table_id": table_id,
        "header_field_id": header_field_id,
        "replacement_hex": None,
    }


def make_write_intent_manifest(
    orig: bytes,
    result: BuildResult,
) -> dict[str, object]:
    writes = [
        _guard_write(orig, result.patched, change)
        for change in result.changes
        if change.offset not in {HEADER_COMPLEMENT, HEADER_CHECKSUM}
    ]
    writes.append(
        {
            "write_id": "lucca-clone-checksum",
            "classification": "managed-header-field",
            "file_start": HEADER_COMPLEMENT,
            "size": 4,
            "owner": "rom_checksum_finalizer",
            "payload_kind": "header",
            "evidence": "verified-static",
            "preimage_sha256": digest(
                orig[HEADER_COMPLEMENT : HEADER_CHECKSUM + 2],
                "sha256",
            ),
            "replacement_sha256": digest(
                result.patched[HEADER_COMPLEMENT : HEADER_CHECKSUM + 2],
                "sha256",
            ),
            "allocation_id": None,
            "hook_id": None,
            "table_id": None,
            "header_field_id": "hirom_checksum_pair",
            "replacement_hex": None,
        }
    )
    stem = (
        "ct_lucca_to_magus_clone_static_v1"
        if result.runtime_hook == "none"
        else "ct_lucca_to_magus_clone_runtime_v1_unsafe"
    )
    return {
        "schema_version": write_guard.SCHEMA_VERSION,
        "manifest_id": stem.replace("_", "-"),
        "build_mode": "private-diagnostic",
        "source_kind": write_guard.CANONICAL_SOURCE_KIND,
        "source_size": len(orig),
        "source_sha256": digest(orig, "sha256"),
        "target_size": len(result.patched),
        "target_sha256": digest(result.patched, "sha256"),
        "output_path": f"private/virtual/{stem}.sfc",
        "allocations": [],
        "writes": sorted(
            writes,
            key=lambda item: (item["file_start"], item["write_id"]),
        ),
    }


def audit_write_intents(
    orig: bytes,
    result: BuildResult,
) -> tuple[dict[str, object], dict[str, object]]:
    intents = make_write_intent_manifest(orig, result)
    try:
        audit = write_guard.audit_images(intents, orig, result.patched)
    except write_guard.WriteIntentError as exc:
        if (
            result.runtime_hook != "provisional"
            or "enemy_reward_table" not in str(exc)
        ):
            raise
        audit = {
            "schema_version": write_guard.SCHEMA_VERSION,
            "validator_version": write_guard.VERSION,
            "validator_sha256": digest(
                pathlib.Path(write_guard.__file__).read_bytes(),
                "sha256",
            ),
            "status": "expected-rejected-retired-unsafe",
            "reason": str(exc),
            "production_input": False,
            "rom_modified": False,
        }
    else:
        if result.runtime_hook == "provisional":
            raise AssertionError("retired unsafe clone unexpectedly passed guard")
    return intents, audit


def build_patch(orig: bytes, runtime_hook: str = "none") -> BuildResult:
    validate_input(orig)
    if runtime_hook not in {"none", "provisional"}:
        raise ValueError(f"unsupported runtime hook mode: {runtime_hook}")

    rom = bytearray(orig)
    changes: list[Change] = []

    for base, stride, label in SPRITE_TABLES:
        clone_region(
            rom,
            base + MAGUS * stride,
            base + LUCCA * stride,
            stride,
            f"Magus -> Lucca {label}",
            "verified-static",
            changes,
        )

    lucca_first_tech = LUCCA * 8
    magus_first_tech = MAGUS * 8
    for base, stride, label in TECH_TABLES:
        clone_region(
            rom,
            base + magus_first_tech * stride,
            base + lucca_first_tech * stride,
            8 * stride,
            f"Magus -> Lucca {label}, eight single-tech slots",
            "documented",
            changes,
        )

    clone_region(
        rom,
        PORTRAIT_MAGUS_TILES,
        PORTRAIT_LUCCA_TILES,
        PORTRAIT_TILE_LENGTH,
        "Magus -> Lucca portrait tile graphics",
        "verified-static",
        changes,
    )
    clone_region(
        rom,
        PORTRAIT_MAGUS_PALETTE,
        PORTRAIT_LUCCA_PALETTE,
        PORTRAIT_PALETTE_LENGTH,
        "Magus -> Lucca portrait palette",
        "documented",
        changes,
    )
    for base, label in ATTACK_SELECTOR_FAMILIES:
        clone_region(
            rom,
            base + MAGUS,
            base + LUCCA,
            1,
            f"Magus -> Lucca {label}",
            "verified-static",
            changes,
        )
    lucca_tp = (
        TP_REQUIREMENT_BASE
        + (TP_REQUIREMENT_DUMMY_COUNT + LUCCA * TP_REQUIREMENT_COUNT)
        * TP_REQUIREMENT_STRIDE
    )
    magus_tp = (
        TP_REQUIREMENT_BASE
        + (TP_REQUIREMENT_DUMMY_COUNT + MAGUS * TP_REQUIREMENT_COUNT)
        * TP_REQUIREMENT_STRIDE
    )
    clone_region(
        rom,
        magus_tp,
        lucca_tp,
        TP_REQUIREMENT_COUNT * TP_REQUIREMENT_STRIDE,
        "Magus -> Lucca single-tech TP-learning thresholds",
        "verified-static",
        changes,
    )
    clone_region(
        rom,
        MAGUS_MENU_ELEMENT,
        LUCCA_MENU_ELEMENT,
        1,
        "Magus -> Lucca menu element icon",
        "documented",
        changes,
    )

    if runtime_hook == "provisional":
        if (
            ENEMY_REWARD_TABLE_END - ENEMY_REWARD_TABLE_START
            != ENEMY_REWARD_RECORD_COUNT * ENEMY_REWARD_RECORD_STRIDE
            or not (
                ENEMY_REWARD_TABLE_START
                <= CAVE_OFFSET
                < CAVE_OFFSET + len(CAVE_BYTES)
                <= ENEMY_REWARD_TABLE_END
            )
        ):
            raise AssertionError("retired shim bounds no longer match reward table")
        if orig[HOOK_OFFSET : HOOK_OFFSET + len(HOOK_EXPECTED)] != HOOK_EXPECTED:
            raise AssertionError("runtime hook site does not match clean ROM")
        if (
            orig[
                HOOK_RETURN_OFFSET : HOOK_RETURN_OFFSET
                + len(HOOK_RETURN_EXPECTED)
            ]
            != HOOK_RETURN_EXPECTED
        ):
            raise AssertionError("runtime hook return site does not match clean ROM")
        if (
            orig[
                CAVE_CONTEXT_OFFSET : CAVE_CONTEXT_OFFSET
                + len(CAVE_CONTEXT_EXPECTED)
            ]
            != CAVE_CONTEXT_EXPECTED
        ):
            raise AssertionError("provisional cave context does not match clean ROM")
        if (
            orig[CAVE_OFFSET - 1] != CAVE_BOUNDARY_BEFORE
            or orig[CAVE_ZERO_RUN_END] != CAVE_BOUNDARY_AFTER
        ):
            raise AssertionError("provisional cave boundary bytes changed")
        if any(orig[CAVE_OFFSET:CAVE_ZERO_RUN_END]):
            raise AssertionError("provisional zero-run bytes are not all zero")
        write_region(
            rom,
            HOOK_OFFSET,
            HOOK_BYTES,
            "JML to provisional Lucca runtime-record clone shim",
            "hypothesis",
            changes,
        )
        write_region(
            rom,
            CAVE_OFFSET,
            CAVE_BYTES,
            (
                "retired runtime clone shim overwriting EnemyRewardTable "
                "records at $CC:63F6"
            ),
            "verified-static",
            changes,
        )

    update_header_checksum(orig, rom, changes)
    patched = bytes(rom)
    validate_header_checksum(patched)
    _assert_retired_invariants(orig, patched)

    ips = make_ips(orig, patched)
    if apply_ips(orig, ips) != patched:
        raise AssertionError("self-check failed: IPS does not reproduce patched bytes")

    result = BuildResult(
        patched=patched,
        ips=ips,
        changes=tuple(changes),
        runtime_hook=runtime_hook,
    )
    audit_write_intents(orig, result)
    return result


def make_manifest(orig: bytes, result: BuildResult) -> dict[str, object]:
    write_intents, write_audit = audit_write_intents(orig, result)
    return {
        "schema_version": 1,
        "builder": "build_lucca_to_magus_clone_v1.py",
        "builder_version": VERSION,
        "builder_sha256": digest(
            pathlib.Path(__file__).read_bytes(),
            "sha256",
        ),
        "diagnostic": "Lucca -> Magus ROM-only supported-slot clone",
        "artifact_class": "diagnostic-only",
        "production_input": False,
        "rom_installable": False,
        "runtime_hook": result.runtime_hook,
        "input": {
            "size": len(orig),
            "sha1": digest(orig, "sha1"),
            "sha256": digest(orig, "sha256"),
        },
        "output_patch": {
            "format": "IPS",
            "size": len(result.ips),
            "crc32": f"{zlib.crc32(result.ips) & 0xFFFFFFFF:08X}",
            "md5": digest(result.ips, "md5"),
            "sha256": digest(result.ips, "sha256"),
        },
        "patched_rom_verification": {
            "size": len(result.patched),
            "sha1": digest(result.patched, "sha1"),
            "sha256": digest(result.patched, "sha256"),
            "written_to_disk": False,
        },
        "invariants": {
            "graphics_entries_7_and_8_unchanged": True,
            "overloaded_attack_byte_0d400e_unchanged": True,
            "save_file_written_by_builder": False,
            "patched_rom_emitted": False,
            "runtime_hook_quarantined": result.runtime_hook == "provisional",
            "runtime_hook_known_unsafe": result.runtime_hook == "provisional",
        },
        "runtime_save_risk": (
            None
            if result.runtime_hook == "none"
            else (
                "The provisional hook overwrites Lucca's live WRAM record. "
                "It also writes $7E2832/$7E2839, structurally corresponding "
                "to save-slot $0432/$0439 inside the conventionally labeled "
                "$0430 region. An in-game save may serialize these changes; "
                "test with a disposable SRM and do not save."
            )
        ),
        "architecture_warning": (
            "File 0x0D400E / SNES $CD:400E is both PC $07's normal-attack "
            "lookup and Crono's critical-attack lookup. It is not free space."
        ),
        "cave_warning": (
            None
            if result.runtime_hook == "none"
            else (
                "$CC:63F6-$CC:642F lies inside EnemyRewardTable "
                "$CC:5E00-$CC:64FF (256 records x 7 bytes). The zero-valued "
                "records are occupied game data. This experimental output "
                "is known unsafe and is retained only for reproduction."
            )
        ),
        "write_intent_manifest": write_intents,
        "write_intent_audit": write_audit,
        "changes": [
            {
                **asdict(change),
                "offset_hex": f"0x{change.offset:06X}",
                "length_hex": f"0x{change.length:X}",
            }
            for change in result.changes
        ],
    }


def make_report(orig: bytes, result: BuildResult) -> str:
    manifest = make_manifest(orig, result)
    patch_info = manifest["output_patch"]
    output_stem = (
        "ct_lucca_to_magus_clone_static_v1"
        if result.runtime_hook == "none"
        else "ct_lucca_to_magus_clone_runtime_v1_UNSAFE"
    )
    if result.runtime_hook == "none":
        output_path = f"output/patches/{output_stem}.ips"
        report_path = f"output/reports/{output_stem}.md"
        manifest_path = f"output/manifests/{output_stem}.json"
    else:
        output_path = f"output/experimental/{output_stem}.ips"
        report_path = f"output/experimental/{output_stem}.md"
        manifest_path = f"output/experimental/{output_stem}.json"
    lines = [
        "# Project Epoch diagnostic: Lucca -> Magus clone v1\n",
        "\n",
        "This is a supported-slot character-data probe, not a production ",
        "eighth-character patch. The builder never opens or writes a save ",
        "file and never emits a patched ROM.\n",
        "\n",
        "## Build\n",
        "\n",
        f"- Builder version: `{VERSION}`\n",
        f"- Builder SHA-256: `{manifest['builder_sha256']}`\n",
        (
            "- Write-intent guard status: "
            f"`{manifest['write_intent_audit']['status']}`\n"
        ),
        (
            "- Write-intent guard SHA-256: "
            f"`{manifest['write_intent_audit']['validator_sha256']}`\n"
        ),
        f"- Input ROM SHA-1: `{EXPECTED_SHA1}`\n",
        f"- Runtime hook mode: `{result.runtime_hook}`\n",
        f"- IPS size: `{patch_info['size']}` bytes\n",
        f"- IPS CRC32: `{patch_info['crc32']}`\n",
        f"- IPS MD5: `{patch_info['md5']}`\n",
        f"- IPS SHA-256: `{patch_info['sha256']}`\n",
        "\n",
        "## Reproduction\n",
        "\n",
        "From the workspace root, with the canonical ROM stored privately:\n",
        "\n",
        "```text\n",
        "python tools/build_lucca_to_magus_clone_v1.py ",
        '"private/input/rom_archive/Chrono Trigger (USA).sfc" ',
        f"--runtime-hook {result.runtime_hook} ",
        f"-o {output_path} ",
        f"--report {report_path} ",
        f"--manifest {manifest_path}\n",
        "```\n",
        "\n",
        "## Added beyond recovered v0\n",
        "\n",
        "- Magus portrait tile graphics are copied over Lucca's full ",
        "`0x200`-byte portrait block.\n",
        "- All three per-PC attack-selector families are cloned, correcting ",
        "the interim single-byte pairing.\n",
        "- Magus's eight TP-learning thresholds are copied over Lucca's.\n",
        "- Magus menu element icon is copied over Lucca's.\n",
        "- Graphics table entries 7 and 8 are explicitly verified unchanged.\n",
        "- The generated IPS is applied in memory and compared byte-for-byte ",
        "with the intended patched image before output.\n",
        "\n",
        "## Still unmapped or runtime-dependent\n",
        "\n",
        "- Variable-length status-menu and battle-menu tech descriptions.\n",
        "- Double/triple-tech eligibility and party-combination logic.\n",
        "- Equipment legality and weapon-specific critical-hit rates.\n",
        "- Event dialogue, recruit/lock flags, and save-select before Continue.\n",
        "- Battle-only animation paths not covered by the cloned single-tech ",
        "selector table.\n",
        "\n",
        "## Occupied attack-table byte\n",
        "\n",
        "File `0x0D400E` (SNES `$CD:400E`) is overloaded: logical PC ",
        "`$07` reaches it through the normal-attack table, while Crono ",
        "reaches the same byte through the critical-attack table. The build ",
        "verifies that it remains unchanged. A real eighth character needs ",
        "an expanded or remapped lookup rather than a write there.\n",
        "\n",
    ]
    if result.runtime_hook == "provisional":
        lines.extend(
            [
                "## Save-data warning\n",
                "\n",
                "The hook overwrites Lucca's live `$50`-byte WRAM character ",
                "record and writes `$7E2832/$7E2839`. By the known WRAM/save ",
                "layout, those two bytes structurally correspond to save-slot ",
                "`$0432/$0439`, inside the conventionally labeled `$0430` ",
                "region. If the game is saved afterward, its normal save ",
                "routine may serialize these changes into SRAM. Use only a ",
                "disposable copy of the SRM and do not save in-game until ",
                "serialization has been traced.\n",
                "\n",
                "## Known occupied-data collision\n",
                "\n",
                "Static reconstruction proves that `$CC:63F6-$CC:642F` lies ",
                "inside `EnemyRewardTable` at `$CC:5E00-$CC:64FF`, containing ",
                "256 seven-byte enemy records. The apparent zero run is made ",
                "of zero-valued records, not free space. The hook site at ",
                "`$CC:E980` is field sprite/animation setup rather than ",
                "character-record initialization. This output is retired, ",
                "known unsafe, and retained only to reproduce the recorded ",
                "negative result. Do not build on it.\n",
                "\n",
            ]
        )
    lines.extend(["## Changes\n", "\n"])
    for change in result.changes:
        lines.append(
            f"- `0x{change.offset:06X}` length `0x{change.length:X}` "
            f"[{change.evidence}]: {change.description}\n"
        )
    lines.extend(
        [
            "\n",
            "## Technical sources\n",
            "\n",
            "- Data Crystal, Chrono Trigger Tech and Attack Documentation: ",
            "https://datacrystal.tcrf.net/wiki/",
            "Chrono_Trigger_%28SNES%29/Tech_and_Attack_Documentation\n",
            "- Chrono Compendium, Changing the status menu portraits: ",
            "https://www.chronocompendium.com/Term/",
            "Changing_the_status_menu_portraits.html\n",
        ]
    )
    return "".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", help="clean unheadered Chrono Trigger US Rev 0 ROM")
    parser.add_argument(
        "--runtime-hook",
        choices=("none", "provisional"),
        default="none",
        help=(
            "reproduce the retired, known-unsafe runtime-record experiment "
            "(overwrites enemy-reward data)"
        ),
    )
    parser.add_argument(
        "-o",
        "--out",
        default=None,
    )
    parser.add_argument(
        "--report",
        default=None,
    )
    parser.add_argument(
        "--manifest",
        default=None,
    )
    args = parser.parse_args()

    rom_path = pathlib.Path(args.rom)
    if args.runtime_hook == "none":
        output_stem = "ct_lucca_to_magus_clone_static_v1"
        default_out = f"output/patches/{output_stem}.ips"
        default_report = f"output/reports/{output_stem}.md"
        default_manifest = f"output/manifests/{output_stem}.json"
    else:
        output_stem = "ct_lucca_to_magus_clone_runtime_v1_UNSAFE"
        default_out = f"output/experimental/{output_stem}.ips"
        default_report = f"output/experimental/{output_stem}.md"
        default_manifest = f"output/experimental/{output_stem}.json"
    out_path = pathlib.Path(args.out or default_out)
    report_path = pathlib.Path(args.report or default_report)
    manifest_path = pathlib.Path(args.manifest or default_manifest)
    validate_output_paths(rom_path, out_path, report_path, manifest_path)

    orig = rom_path.read_bytes()
    result = build_patch(orig, runtime_hook=args.runtime_hook)
    manifest = make_manifest(orig, result)

    for path in (out_path, report_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_bytes(result.ips)
    report_path.write_text(make_report(orig, result), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {out_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
