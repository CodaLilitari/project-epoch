from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "schala_rom_scaffold.py"
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location("schala_rom_scaffold", TOOL_PATH)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def synthetic_hirom() -> bytes:
    image = bytearray(TOOL.EXPECTED_SOURCE_SIZE)
    header = TOOL.HIROM_HEADER
    image[header + TOOL.HEADER_MAP_MODE] = TOOL.HIROM_FAST
    image[header + TOOL.HEADER_ROM_SIZE] = TOOL.ROM_SIZE_4_MIB
    image[header + TOOL.HEADER_COMPLEMENT : header + TOOL.HEADER_COMPLEMENT + 2] = (
        b"\xFF\xFF"
    )
    checksum = sum(image) & 0xFFFF
    complement = checksum ^ 0xFFFF
    image[header + TOOL.HEADER_COMPLEMENT : header + TOOL.HEADER_COMPLEMENT + 2] = (
        complement.to_bytes(2, "little")
    )
    image[header + TOOL.HEADER_CHECKSUM : header + TOOL.HEADER_CHECKSUM + 2] = (
        checksum.to_bytes(2, "little")
    )
    return bytes(image)


class ExHiRomScaffoldTests(unittest.TestCase):
    def test_inert_expansion_and_headers(self) -> None:
        source = synthetic_hirom()
        result = TOOL.expand_exhirom_scaffold(
            source, expected_sha1=TOOL.digest(source, "sha1")
        )
        TOOL.validate_exhirom_scaffold(result)
        self.assertEqual(len(result), TOOL.TARGET_SIZE)
        self.assertEqual(
            result[TOOL.EXHIROM_HEADER + TOOL.HEADER_MAP_MODE],
            TOOL.EXHIROM_FAST,
        )
        self.assertEqual(
            result[TOOL.EXHIROM_HEADER + TOOL.HEADER_ROM_SIZE],
            TOOL.ROM_SIZE_8_MIB,
        )
        self.assertEqual(
            result[TOOL.ALLOCATION_START :],
            bytes([TOOL.FILL_BYTE])
            * (TOOL.TARGET_SIZE - TOOL.ALLOCATION_START),
        )

    def test_bank00_dependencies_are_mirrored(self) -> None:
        source = bytearray(synthetic_hirom())
        source[0xF700:0xF704] = b"DATA"
        # Restore the checksum after changing the synthetic source.
        source[
            TOOL.HIROM_HEADER + TOOL.HEADER_COMPLEMENT :
            TOOL.HIROM_HEADER + TOOL.HEADER_CHECKSUM + 2
        ] = b"\xFF\xFF\x00\x00"
        checksum = sum(source) & 0xFFFF
        source[
            TOOL.HIROM_HEADER + TOOL.HEADER_COMPLEMENT :
            TOOL.HIROM_HEADER + TOOL.HEADER_COMPLEMENT + 2
        ] = (checksum ^ 0xFFFF).to_bytes(2, "little")
        source[
            TOOL.HIROM_HEADER + TOOL.HEADER_CHECKSUM :
            TOOL.HIROM_HEADER + TOOL.HEADER_CHECKSUM + 2
        ] = checksum.to_bytes(2, "little")
        source_bytes = bytes(source)
        result = TOOL.expand_exhirom_scaffold(
            source_bytes, expected_sha1=TOOL.digest(source_bytes, "sha1")
        )
        self.assertEqual(result[0x40F700:0x40F704], b"DATA")
        self.assertEqual(TOOL.exhirom_snes_to_file(0x00F700), 0x40F700)

    def test_address_translation(self) -> None:
        pairs = (
            (0xC00000, 0x000000),
            (0xFFFFFF, 0x3FFFFF),
            (0x410000, 0x410000),
            (0x7DFFFF, 0x7DFFFF),
            (0x808000, 0x008000),
            (0x00F700, 0x40F700),
            (0x3F8000, 0x7F8000),
        )
        for snes, file_offset in pairs:
            self.assertEqual(
                TOOL.exhirom_snes_to_file(snes), file_offset, hex(snes)
            )
        self.assertIsNone(TOOL.exhirom_snes_to_file(0x003000))
        self.assertIsNone(TOOL.exhirom_snes_to_file(0x7E8000))


class AllocationTests(unittest.TestCase):
    def allocation(self, **updates):
        values = {
            "allocation_id": "runtime",
            "file_start": 0x410000,
            "size": 0x100,
            "snes_start": 0x410000,
            "kind": "code",
            "owner": "runtime",
            "evidence": "hypothesis",
            "alignment": 0x10,
            "no_bank_cross": True,
        }
        values.update(updates)
        return TOOL.Allocation(**values)

    def test_valid_nonoverlapping_allocations_and_manifest(self) -> None:
        allocations = (
            self.allocation(),
            self.allocation(
                allocation_id="tables",
                file_start=0x420000,
                snes_start=0x420000,
                kind="table",
            ),
        )
        TOOL.validate_allocations(allocations)
        manifest = TOOL.allocation_manifest(allocations)
        json.dumps(manifest, sort_keys=True)
        self.assertEqual(manifest["mapping"]["map_mode"], 0x35)
        self.assertEqual(manifest["allocation_pool"]["capacity"], 0x3D0000)
        self.assertEqual(
            manifest["source_requirements"]["sha1"],
            TOOL.EXPECTED_SOURCE_SHA1,
        )
        self.assertEqual(
            manifest["reserved_ranges"][0]["file_start"], 0x400000
        )

    def test_rejects_overlap(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlaps"):
            TOOL.validate_allocations(
                (
                    self.allocation(size=0x200),
                    self.allocation(
                        allocation_id="other",
                        file_start=0x410100,
                        snes_start=0x410100,
                    ),
                )
            )

    def test_rejects_bank_crossing(self) -> None:
        with self.assertRaisesRegex(ValueError, "crosses a bank"):
            TOOL.validate_allocations(
                (
                    self.allocation(
                        file_start=0x41FFF0,
                        snes_start=0x41FFF0,
                        size=0x20,
                    ),
                )
            )

    def test_rejects_reserved_bank40_and_tail(self) -> None:
        for file_start in (0x408000, 0x7E0000):
            with self.subTest(file_start=file_start):
                with self.assertRaisesRegex(
                    ValueError, "outside approved expanded banks"
                ):
                    TOOL.validate_allocations(
                        (
                            self.allocation(
                                file_start=file_start,
                                snes_start=file_start,
                            ),
                        )
                    )

    def test_rejects_snes_file_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "mapping mismatch"):
            TOOL.validate_allocations(
                (self.allocation(snes_start=0xC10000),)
            )


@unittest.skipUnless(ROM_PATH.exists(), "local clean ROM is not available")
class CanonicalRomTests(unittest.TestCase):
    def test_canonical_source_builds_without_pc7_changes(self) -> None:
        source = ROM_PATH.read_bytes()
        result = TOOL.expand_exhirom_scaffold(source)
        self.assertEqual(
            TOOL.digest(result), TOOL.EXPECTED_INERT_SCAFFOLD_SHA256
        )
        expected_mutations = {
            TOOL.HIROM_HEADER + TOOL.HEADER_MAP_MODE,
            TOOL.HIROM_HEADER + TOOL.HEADER_ROM_SIZE,
            TOOL.HIROM_HEADER + TOOL.HEADER_COMPLEMENT,
            TOOL.HIROM_HEADER + TOOL.HEADER_COMPLEMENT + 1,
            TOOL.HIROM_HEADER + TOOL.HEADER_CHECKSUM,
            TOOL.HIROM_HEADER + TOOL.HEADER_CHECKSUM + 1,
        }
        actual_mutations = {
            offset
            for offset, (old, new) in enumerate(
                zip(source, result[: TOOL.EXPECTED_SOURCE_SIZE], strict=True)
            )
            if old != new
        }
        self.assertEqual(actual_mutations, expected_mutations)
        mirror_mutations = {
            offset
            for offset, (old, new) in enumerate(
                zip(
                    source[:0x10000],
                    result[TOOL.BOOT_MIRROR_START : TOOL.BOOT_MIRROR_END],
                    strict=True,
                )
            )
            if old != new
        }
        self.assertEqual(
            mirror_mutations,
            expected_mutations,
        )


if __name__ == "__main__":
    unittest.main()
