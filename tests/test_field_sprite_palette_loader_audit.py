from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "audit_field_sprite_palette_loader.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_field_sprite_palette_loader", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def put_snes(rom: bytearray, address: int, payload: bytes) -> None:
    offset = TOOL.snes_to_file(address)
    rom[offset : offset + len(payload)] = payload


def make_contract_rom() -> bytearray:
    rom = bytearray(TOOL.CANONICAL_ROM_SIZE)

    for pc_id in range(TOOL.PC_COUNT):
        descriptor = (
            TOOL.PC_DESCRIPTOR_TABLE_FILE
            + pc_id * TOOL.PC_DESCRIPTOR_STRIDE
        )
        rom[descriptor + TOOL.DESCRIPTOR_PALETTE_BYTE] = pc_id
        pointer = pc_id * TOOL.VANILLA_PALETTE_BYTES
        pointer_offset = TOOL.PALETTE_POINTER_TABLE_FILE + pc_id * 2
        rom[pointer_offset : pointer_offset + 2] = pointer.to_bytes(
            2, "little"
        )

    id7_descriptor = (
        TOOL.PC_DESCRIPTOR_TABLE_FILE
        + TOOL.PC_COUNT * TOOL.PC_DESCRIPTOR_STRIDE
    )
    rom[
        id7_descriptor + TOOL.DESCRIPTOR_PALETTE_BYTE
    ] = TOOL.COLLIDING_ID7_PALETTE_ID
    id7_pointer = TOOL.PC_COUNT * TOOL.VANILLA_PALETTE_BYTES
    id7_pointer_offset = TOOL.PALETTE_POINTER_TABLE_FILE + TOOL.PC_COUNT * 2
    rom[id7_pointer_offset : id7_pointer_offset + 2] = id7_pointer.to_bytes(
        2, "little"
    )

    for writer in TOOL.SOURCE_KEY_WRITERS:
        put_snes(
            rom,
            writer.signature_start_snes,
            writer.descriptor_read + TOOL.SOURCE_WRITER_COMMON,
        )

    for path in TOOL.COPY_PATHS:
        put_snes(rom, path.row_preamble_snes, path.row_preamble)
        put_snes(rom, path.copy_setup_snes, TOOL.COPY_SETUP_SIGNATURE)

    put_snes(
        rom, TOOL.SHADOW_MIRROR_SNES, TOOL.SHADOW_MIRROR_SIGNATURE
    )
    put_snes(rom, TOOL.CGRAM_UPLOAD_SNES, TOOL.CGRAM_UPLOAD_SIGNATURE)
    return rom


class FieldSpritePaletteLoaderAuditTests(unittest.TestCase):
    def test_layout_exposes_twelve_vs_fifteen_color_boundary(self) -> None:
        TOOL.validate_layout_constants()
        self.assertEqual(TOOL.VANILLA_PALETTE_BYTES, 0x18)
        self.assertEqual(TOOL.VANILLA_VISIBLE_COLOR_COUNT, 12)
        self.assertEqual(TOOL.FULL_VISIBLE_PALETTE_BYTES, 0x1E)
        self.assertEqual(TOOL.FULL_VISIBLE_COLOR_COUNT, 15)
        self.assertEqual(
            TOOL.PALETTE_DESTINATION_OFFSET
            + TOOL.FULL_VISIBLE_PALETTE_BYTES,
            TOOL.SPRITE_PALETTE_ROW_BYTES,
        )

    def test_static_contract_pins_five_paths_and_ten_moves(self) -> None:
        rom = make_contract_rom()
        TOOL.validate_static_contract(bytes(rom))
        self.assertEqual(len(TOOL.COPY_PATHS), 5)
        self.assertEqual(
            sum(2 for _path in TOOL.COPY_PATHS),
            10,
        )

    def test_copy_count_mutation_is_rejected(self) -> None:
        rom = make_contract_rom()
        site = TOOL.COPY_PATHS[2].first_copy_snes
        rom[TOOL.snes_to_file(site) + 1] = 0x1D
        with self.assertRaisesRegex(ValueError, "shadow copies"):
            TOOL.validate_static_contract(bytes(rom))

    def test_mirror_delta_mutation_is_rejected(self) -> None:
        rom = make_contract_rom()
        setup = TOOL.COPY_PATHS[0].copy_setup_snes
        signature_offset = TOOL.COPY_SETUP_SIGNATURE.index(
            bytes.fromhex("69 00 02")
        )
        rom[TOOL.snes_to_file(setup) + signature_offset + 2] = 0x03
        with self.assertRaisesRegex(ValueError, "shadow copies"):
            TOOL.validate_static_contract(bytes(rom))

    def test_exact_three_source_key_writers_are_required(self) -> None:
        rom = make_contract_rom()
        rom[0x0200:0x0203] = TOOL.STA_OBJECT_PALETTE_KEY
        with self.assertRaisesRegex(ValueError, "unexpected writers"):
            TOOL.validate_static_contract(bytes(rom))

    def test_ffff_sentinel_is_outside_byte_times_18_domain(self) -> None:
        self.assertEqual(TOOL.MAX_GENERATED_PALETTE_SOURCE_KEY, 0x17E8)
        self.assertEqual(TOOL.SCHALA_EXPANDED_PALETTE_SENTINEL, 0xFFFF)
        self.assertGreater(
            TOOL.SCHALA_EXPANDED_PALETTE_SENTINEL,
            TOOL.MAX_GENERATED_PALETTE_SOURCE_KEY,
        )

    def test_report_preserves_color_zero_and_fills_row_boundary(self) -> None:
        report = TOOL.audit_rom(bytes(make_contract_rom()))
        destination = report["destination_contract"]
        adapter = report["adapter_contract"]
        self.assertEqual(destination["destination_first_color"], 1)
        self.assertEqual(destination["vanilla_destination_last_color"], 12)
        self.assertEqual(destination["untouched_tail_colors"], [13, 14, 15])
        self.assertEqual(adapter["expanded_copy_bytes_each_shadow"], 0x1E)
        self.assertEqual(adapter["expanded_visible_color_count"], 15)
        self.assertEqual(adapter["individual_mvn_sites_to_adapt"], 10)

    def test_occupied_id7_descriptor_is_not_a_pc_palette_row(self) -> None:
        report = TOOL.audit_rom(bytes(make_contract_rom()))
        collision = report["source_contract"]["logical_id7_collision"]
        self.assertEqual(collision["palette_id"], 0x85)
        self.assertEqual(collision["generated_source_key"], 0x0C78)

    def test_rom_gate_rejects_unpinned_input_before_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "wrong.sfc"
            path.write_bytes(b"\x00" * TOOL.CANONICAL_ROM_SIZE)
            with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                TOOL.verify_canonical_rom(path)


if __name__ == "__main__":
    unittest.main()
