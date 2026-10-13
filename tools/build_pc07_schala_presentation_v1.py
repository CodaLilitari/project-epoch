"""Derive a private PC-sized presentation provider from canonical retail Schala.

This pure compiler returns bytes in memory. Its CLI emits metadata only. It
neither changes ROMs nor assigns a production graphics index. The expanded
addresses below are named private diagnostic proposals, not game ownership.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import build_schala_vanilla_npc_compat_v0 as npc
import build_schala_vanilla_npc_supported_slot_smoke_v0 as previous

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PINS = {
    "tools/build_schala_vanilla_npc_compat_v0.py": "0ad950e0e069b1171a306da52479014ac896f1d3d4c7e773896f63db34b6c1a9",
    "tools/build_schala_vanilla_npc_supported_slot_smoke_v0.py": "d5b43ee02d7a5064cd2cd673f743aa92826d94213e7f1cdb1b811ea2ed3f301b",
}
SELECTORS = 256
FACING_SIZE = (SELECTORS + 1) * 4
ALLOCATIONS = {
    "retail-schala-raw-graphics": 0x420000,
    "retail-schala-assembly": 0x421000,
    "retail-schala-primary": 0x424000,
    "retail-schala-timing": 0x425100,
}


@dataclass(frozen=True)
class Presentation:
    assets: dict[str, bytes]
    metadata: dict


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compile_provider(rom: bytes) -> Presentation:
    for name, digest in SOURCE_PINS.items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("retail provider dependency drift: " + name)
    original = npc.build_bundle(rom)
    a = original.artifacts
    source_primary, source_aux = a[npc.PRIMARY_FILENAME], a[npc.AUX_FILENAME]
    # Reuse the accepted numeric-cell conversion and its source validation.
    old_primary, old_aux, facing_frames, _, _ = previous.build_safe_fallback_streams(source_primary, source_aux)
    primary = bytearray()
    for facing in range(4):
        block = source_primary[facing * 36:(facing + 1) * 36]
        primary.extend(block + block[:4] * (SELECTORS - 9 + 1))
    auxiliary = source_aux + source_aux[:4] * (SELECTORS - 9 + 1)
    if len(primary) != 4 * FACING_SIZE or len(auxiliary) != FACING_SIZE:
        raise ValueError("expanded animation geometry")
    for facing in range(4):
        block = bytes(primary[facing * FACING_SIZE:(facing + 1) * FACING_SIZE])
        if block[:len(old_aux)] != old_primary[facing * len(old_aux):(facing + 1) * len(old_aux)]:
            raise ValueError("accepted facing-prefix reproduction")
        for selector in range(SELECTORS):
            start = selector * 4
            if len(block[start:start + 8]) != 8 or len(auxiliary[start:start + 8]) != 8:
                raise ValueError("eight-byte native initialization read leaves provider")
            end = block.index(0xFF, start)
            timing_end = auxiliary.index(0, start)
            if end - start != timing_end - start or any(frame >= 23 for frame in block[start:end]):
                raise ValueError("unbounded frame/timing stream")
    if auxiliary[:len(old_aux)] != old_aux:
        raise ValueError("accepted auxiliary-prefix reproduction")
    assets = {
        "retail-schala-raw-graphics": a[npc.GRAPHICS_FILENAME],
        "retail-schala-assembly": a[npc.ASSEMBLY_FILENAME],
        "retail-schala-primary": bytes(primary),
        "retail-schala-timing": auxiliary,
    }
    return Presentation(assets, {
        "schema": "project-epoch-pc07-retail-schala-presentation-v1",
        "evidence_level": "verified-static-private-provider",
        "canonical_sha256": sha(rom), "retail_npc_id": 9,
        "logical_pc_identity": 7, "name_requested": "Schala",
        "name_runtime_installed": False,
        "source_frame_count": 23, "source_tile_count": 79,
        "facing_count": 4, "selectors_per_facing": SELECTORS,
        "facing_stride": FACING_SIZE,
        "extra_retail_guard_cells_per_facing_and_timing": 1,
        "native_init_eight_byte_reads_bounded": True,
        "first_nine_numeric_cells_preserved": True,
        "fallback_selector_range": [9, 255],
        "fallback": "exact retail entry-zero cell for the corresponding facing",
        "fallback_frame_indices": list(facing_frames),
        "entrypoint_semantic_equivalence_proved": False,
        "bounded_primary_and_timing_entries_checked": 4 * SELECTORS,
        "prior_supported_slot_prefix_reproduced": True,
        "retail_palette_cpu_address": 0xE40C00,
        "retail_palette_size": 24,
        "sources": SOURCE_PINS,
        "allocations": [{"id": name, "private_proposed_cpu_address": ALLOCATIONS[name],
                         "bytes": len(data), "sha256": sha(data)} for name, data in assets.items()],
        "rom_emitted": False, "runtime_integration": False,
        "production_approval": False,
        "reproduction": "python -B tools/build_pc07_schala_presentation_v1.py",
    })


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rom", type=Path, default=npc.DEFAULT_ROM)
    args = ap.parse_args()
    print(json.dumps(compile_provider(args.rom.read_bytes()).metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
