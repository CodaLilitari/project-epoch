from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_sha256_65816_standalone_benchmark as TOOL  # noqa: E402


def synthetic_spans() -> tuple[TOOL.DeclaredSpan, ...]:
    return (
        TOOL.DeclaredSpan(
            "hirom_header_vectors",
            TOOL.HIROM_HEADER_SPAN[0],
            TOOL.HIROM_HEADER_SPAN[1],
            "test header",
        ),
        TOOL.DeclaredSpan(
            "reset_benchmark",
            0x408000,
            0x408004,
            "test boot",
        ),
        TOOL.DeclaredSpan(
            "exhirom_header_vectors",
            TOOL.EXHIROM_HEADER_SPAN[0],
            TOOL.EXHIROM_HEADER_SPAN[1],
            "test header mirror",
        ),
        TOOL.DeclaredSpan(
            "sha256_code",
            0x410000,
            0x410004,
            "test core",
        ),
        TOOL.DeclaredSpan(
            "test_vectors",
            0x420000,
            0x420004,
            "test data",
        ),
    )


def synthetic_final_image() -> bytes:
    image = bytearray([TOOL.FILL_BYTE]) * TOOL.TARGET_SIZE
    header = bytearray([TOOL.FILL_BYTE]) * TOOL.HEADER_SIZE
    header[:21] = b"EPOCH SHA256 TEST    "
    header[TOOL.HEADER_MAP_MODE] = TOOL.EXHIROM_FAST
    header[TOOL.HEADER_CARTRIDGE_TYPE] = (
        TOOL.CARTRIDGE_ROM_RAM_BATTERY
    )
    header[TOOL.HEADER_ROM_SIZE] = TOOL.ROM_SIZE_8_MIB
    header[TOOL.HEADER_SRAM_SIZE] = TOOL.SRAM_SIZE_8_KIB
    image[
        TOOL.HIROM_HEADER_SPAN[0] : TOOL.HIROM_HEADER_SPAN[1]
    ] = header
    image[
        TOOL.EXHIROM_HEADER_SPAN[0] : TOOL.EXHIROM_HEADER_SPAN[1]
    ] = header
    image[0x408000:0x408004] = b"\x78\x18\xfb\xdb"
    image[0x410000:0x410004] = b"\x08\xc2\x30\x6b"
    image[0x420000:0x420004] = b"\x00\x01\x02\x03"
    TOOL.finalize_dual_header_checksums(image)
    return bytes(image)


class Sha25665816StandaloneBenchmarkTests(unittest.TestCase):
    def test_pinned_blank_source_and_zero_sram_hashes(self) -> None:
        blank = bytes([TOOL.FILL_BYTE]) * TOOL.TARGET_SIZE
        self.assertEqual(TOOL.sha256_bytes(blank), TOOL.BLANK_SOURCE_SHA256)
        self.assertEqual(
            TOOL.sha256_bytes(bytes(TOOL.SRAM_SIZE)),
            TOOL.ZERO_SRAM_SHA256,
        )

    def test_private_output_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="sha_builder_paths_",
            dir=TOOL.PRIVATE_ROOT,
        ) as directory:
            root = pathlib.Path(directory)
            resolved = TOOL.validate_private_path(
                root / "benchmark.sfc",
                suffixes=frozenset({".sfc"}),
            )
            self.assertTrue(resolved.is_relative_to(TOOL.PRIVATE_ROOT))
            with self.assertRaises(TOOL.BenchmarkBuildError):
                TOOL.validate_private_path(
                    ROOT / "benchmark.sfc",
                    suffixes=frozenset({".sfc"}),
                )
            with self.assertRaises(TOOL.BenchmarkBuildError):
                TOOL.validate_private_path(
                    root / "benchmark.bin",
                    suffixes=frozenset({".sfc"}),
                )

    def test_nocash_symbols_parse_exact_format(self) -> None:
        parsed = TOOL.parse_nocash_symbols(
            b";no$sns symbolic information file\n"
            b"00410000 Benchmark_CoreStart\n"
            b"004105BD Benchmark_CoreEnd\n"
            b"0041015B :macro_0_AbiD\n"
        )
        self.assertEqual(parsed["Benchmark_CoreStart"], 0x410000)
        self.assertEqual(parsed["Benchmark_CoreEnd"], 0x4105BD)
        self.assertEqual(parsed[":macro_0_AbiD"], 0x41015B)
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.parse_nocash_symbols(b"41:0000 BadFormat\n")
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.parse_nocash_symbols(b"00410000 Duplicate\n00410001 Duplicate\n")
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.parse_nocash_symbols(b"01410000 OutsideBus\n")

    def test_label_spans_map_into_exact_windows(self) -> None:
        symbols = {
            "Benchmark_BootStart": 0x008000,
            "Benchmark_BootEnd": 0x008100,
            "Benchmark_CoreStart": 0x410000,
            "Benchmark_CoreEnd": 0x410600,
            "Benchmark_DataStart": 0x420000,
            "Benchmark_DataEnd": 0x420040,
        }
        spans = TOOL.declared_spans_from_symbols(symbols)
        by_id = {span.span_id: span for span in spans}
        self.assertEqual(by_id["reset_benchmark"].file_start, 0x408000)
        self.assertEqual(by_id["reset_benchmark"].size, 0x100)
        self.assertEqual(by_id["sha256_code"].file_start, 0x410000)
        self.assertEqual(by_id["test_vectors"].file_start, 0x420000)

        outside = dict(symbols)
        outside["Benchmark_CoreStart"] = 0x430000
        outside["Benchmark_CoreEnd"] = 0x430100
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.declared_spans_from_symbols(outside)

    def test_declared_spans_reject_overlap_and_duplicate_ids(self) -> None:
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.validate_declared_spans(
                (
                    TOOL.DeclaredSpan("one", 1, 5, "test"),
                    TOOL.DeclaredSpan("two", 4, 8, "test"),
                )
            )
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.validate_declared_spans(
                (
                    TOOL.DeclaredSpan("same", 1, 2, "test"),
                    TOOL.DeclaredSpan("same", 3, 4, "test"),
                )
            )

    def test_declared_span_import_rejects_any_outside_change(self) -> None:
        spans = synthetic_spans()
        untrusted = bytearray(synthetic_final_image())
        imported = TOOL.import_declared_spans(bytes(untrusted), spans)
        self.assertEqual(bytes(imported), bytes(untrusted))

        untrusted[0] = 0
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.import_declared_spans(bytes(untrusted), spans)

    def test_declared_span_import_requires_output_in_every_span(self) -> None:
        spans = synthetic_spans()
        untrusted = bytearray(synthetic_final_image())
        untrusted[0x420000:0x420004] = b"\xff" * 4
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.import_declared_spans(bytes(untrusted), spans)

    def test_dual_headers_and_complete_diff_validate(self) -> None:
        image = synthetic_final_image()
        report = TOOL.validate_final_image(image, synthetic_spans())
        self.assertEqual(report["status"], "complete-diff-valid")
        self.assertTrue(report["all_changed_bytes_declared"])
        self.assertEqual(report["declared_span_count"], 5)
        self.assertEqual(report["target_sha256"], TOOL.sha256_bytes(image))
        self.assertEqual(len(report["headers"]), 2)

    def test_final_validation_rejects_mismatched_header_copy(self) -> None:
        image = bytearray(synthetic_final_image())
        image[TOOL.HIROM_HEADER_SPAN[0]] ^= 1
        with self.assertRaises(TOOL.BenchmarkBuildError):
            TOOL.validate_final_image(bytes(image), synthetic_spans())

    def test_source_closure_hashes_only_asm_and_rejects_binary(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="sha_builder_sources_",
            dir=ROOT / "asm",
        ) as directory:
            source_root = pathlib.Path(directory)
            child = source_root / "child.asm"
            entry = source_root / "entry.asm"
            child.write_text("db $01\n", encoding="utf-8")
            entry.write_text('incsrc "child.asm"\n', encoding="utf-8")
            records = TOOL.collect_assembly_sources(entry)
            self.assertEqual(
                {record["path"] for record in records},
                {
                    TOOL.workspace_relative(child),
                    TOOL.workspace_relative(entry),
                },
            )

            child.write_text('incbin "payload.bin"\n', encoding="utf-8")
            with self.assertRaises(TOOL.BenchmarkBuildError):
                TOOL.collect_assembly_sources(entry)

            entry.write_text('incsrc "../../../escape.asm"\n', encoding="utf-8")
            with self.assertRaises(TOOL.BenchmarkBuildError):
                TOOL.collect_assembly_sources(entry)

    @unittest.skipUnless(
        TOOL.DEFAULT_ASAR_ARCHIVE.is_file()
        and TOOL.DEFAULT_ASAR_EXE.is_file(),
        "pinned private Asar toolchain is unavailable",
    )
    def test_pinned_asar_toolchain_hashes_and_machine_types(self) -> None:
        report = TOOL.validate_asar_toolchain()
        self.assertEqual(
            report["extracted_executable"]["pe_machine"],
            "0x8664",
        )
        self.assertEqual(report["extracted_dll"]["pe_machine"], "0x014C")
        self.assertFalse(
            report["python_inprocess_dll"]["usable_with_bundled_runtime"]
        )
        self.assertEqual(
            report["selected_interface"],
            "pinned CLI on a validated temporary target below private/",
        )

    @unittest.skipUnless(
        TOOL.DEFAULT_ASSEMBLY.is_file()
        and TOOL.DEFAULT_ASAR_ARCHIVE.is_file()
        and TOOL.DEFAULT_ASAR_EXE.is_file(),
        "standalone wrapper or pinned private Asar is unavailable",
    )
    def test_full_build_stays_in_memory_until_explicit_write(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="sha_builder_integration_",
            dir=TOOL.PRIVATE_ROOT,
        ) as directory:
            root = pathlib.Path(directory)
            rom = root / "benchmark.sfc"
            srm = root / "benchmark.srm"
            manifest = root / "benchmark.manifest.json"
            result = TOOL.build_in_memory(
                output_rom=rom,
                output_srm=srm,
                output_manifest=manifest,
            )
            self.assertEqual(len(result.rom), TOOL.TARGET_SIZE)
            self.assertEqual(len(result.sram), TOOL.SRAM_SIZE)
            self.assertEqual(
                result.manifest["host_audit"]["status"],
                "complete-diff-valid",
            )
            self.assertEqual(
                result.manifest["builder_source"]["sha256"],
                TOOL.sha256_path(pathlib.Path(TOOL.__file__)),
            )
            self.assertFalse(rom.exists())
            self.assertFalse(srm.exists())
            self.assertFalse(manifest.exists())

    def test_write_is_idempotent_but_refuses_different_existing_data(self) -> None:
        result = TOOL.BuildResult(
            rom=b"rom",
            sram=b"sram",
            manifest={},
            manifest_bytes=b"{}\n",
        )
        with tempfile.TemporaryDirectory(
            prefix="sha_builder_write_",
            dir=TOOL.PRIVATE_ROOT,
        ) as directory:
            root = pathlib.Path(directory)
            rom = root / "benchmark.sfc"
            srm = root / "benchmark.srm"
            manifest = root / "benchmark.manifest.json"
            TOOL.write_build(
                result,
                output_rom=rom,
                output_srm=srm,
                output_manifest=manifest,
            )
            TOOL.write_build(
                result,
                output_rom=rom,
                output_srm=srm,
                output_manifest=manifest,
            )
            rom.write_bytes(b"different")
            with self.assertRaises(TOOL.BenchmarkBuildError):
                TOOL.write_build(
                    result,
                    output_rom=rom,
                    output_srm=srm,
                    output_manifest=manifest,
                )


if __name__ == "__main__":
    unittest.main()
