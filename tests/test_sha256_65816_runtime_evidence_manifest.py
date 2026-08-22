from __future__ import annotations

import dataclasses
import json
import pathlib
import struct
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_sha256_65816_runtime_evidence_manifest as TOOL  # noqa: E402
import inspect_schala_sha256_65816_benchmark_state as INSPECTOR  # noqa: E402
import retroarch_rastate  # noqa: E402


def put_u16(target: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", target, offset, value)


def passing_core() -> bytes:
    core = bytearray(INSPECTOR.BST_WRAM_OFFSET + INSPECTOR.WRAM_SIZE)
    core[:4] = INSPECTOR.BST_MAGIC
    version = INSPECTOR.BST_VERSION.encode("ascii") + b"\x00"
    core[
        INSPECTOR.BST_VERSION_OFFSET :
        INSPECTOR.BST_VERSION_OFFSET + len(version)
    ] = version
    result = bytearray(INSPECTOR.RESULT_SIZE)
    result[:8] = INSPECTOR.RESULT_MAGIC
    for offset, value in (
        (0x08, 1),
        (0x0A, INSPECTOR.RESULT_SIZE),
        (0x0C, 0xA55A),
        (0x0E, 0),
        (0x10, 0xA55A),
        (0x12, 1100),
        (0x14, 0xFFFF),
        (0x16, 1),
        (0x18, INSPECTOR.EXPECTED_ABI_MASK),
        (0x1A, INSPECTOR.EXPECTED_P),
        (0x1C, 1),
        (0x1E, 0x6A00),
        (0x20, INSPECTOR.EXPECTED_Y),
        (0x22, INSPECTOR.EXPECTED_D),
        (0x24, INSPECTOR.EXPECTED_SP),
        (0x26, INSPECTOR.EXPECTED_SP),
        (0x28, INSPECTOR.EXPECTED_DBR),
        (0x2A, 1),
        (0x2C, 1),
        (0x2E, 4),
    ):
        put_u16(result, offset, value)

    starts = (1, 367, 734)
    ends = (367, 734, 1100)
    for slot, record, start, end in zip(
        range(1, 4),
        INSPECTOR.SLOT_RECORDS,
        starts,
        ends,
        strict=True,
    ):
        values = (
            (0x00, slot),
            (0x02, INSPECTOR.EXPECTED_BASES[slot]),
            (0x04, 0),
            (0x06, start),
            (0x08, end),
            (0x0A, end - start),
            (0x0C, INSPECTOR.EXPECTED_ABI_MASK),
            (0x0E, INSPECTOR.EXPECTED_P),
            (0x10, INSPECTOR.EXPECTED_P),
            (0x12, slot),
            (0x14, INSPECTOR.EXPECTED_BASES[slot]),
            (0x16, INSPECTOR.EXPECTED_Y),
            (0x18, INSPECTOR.EXPECTED_D),
            (0x1A, INSPECTOR.EXPECTED_SP),
            (0x1C, INSPECTOR.EXPECTED_SP),
            (0x1E, INSPECTOR.EXPECTED_DBR),
            (0x20, INSPECTOR.EXPECTED_DBR),
            (0x42, 1),
        )
        for relative, value in values:
            put_u16(result, record + relative, value)
        result[record + 0x22 : record + 0x42] = bytes.fromhex(
            INSPECTOR.EXPECTED_DIGESTS[slot]
        )

    wram = INSPECTOR.BST_WRAM_OFFSET
    core[
        wram + INSPECTOR.RESULT_ADDRESS :
        wram + INSPECTOR.RESULT_ADDRESS + INSPECTOR.RESULT_SIZE
    ] = result
    core[
        wram + INSPECTOR.SCRATCH_FRONT :
        wram + INSPECTOR.SCRATCH_START
    ] = INSPECTOR.GUARD_BYTES
    core[
        wram + INSPECTOR.SCRATCH_END :
        wram + INSPECTOR.SCRATCH_REAR_END
    ] = INSPECTOR.GUARD_BYTES
    core[4:8] = len(core).to_bytes(4, "little")
    return bytes(core)


def file_pin(path: pathlib.Path) -> TOOL.FilePin:
    return TOOL.FilePin(path.stat().st_size, TOOL.sha256_path(path))


def record(path: pathlib.Path) -> dict[str, object]:
    return {
        "path": TOOL.workspace_relative(path),
        "size": path.stat().st_size,
        "sha256": TOOL.sha256_path(path),
    }


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


@dataclasses.dataclass
class Fixture:
    root: pathlib.Path
    static_manifest: pathlib.Path
    states: tuple[pathlib.Path, pathlib.Path]
    logs: tuple[pathlib.Path, pathlib.Path]
    configs: tuple[pathlib.Path, pathlib.Path]
    base_config: pathlib.Path
    retroarch: pathlib.Path
    core: pathlib.Path
    core_info: pathlib.Path
    output: pathlib.Path
    pins: TOOL.RuntimePins

    def kwargs(self) -> dict[str, object]:
        return {
            "static_manifest": self.static_manifest,
            "states": self.states,
            "logs": self.logs,
            "run_configs": self.configs,
            "base_config": self.base_config,
            "retroarch_exe": self.retroarch,
            "core": self.core,
            "core_info": self.core_info,
            "output": self.output,
            "pins": self.pins,
        }


def make_fixture(root: pathlib.Path) -> Fixture:
    root.mkdir(parents=True, exist_ok=True)
    rom = root / "benchmark.sfc"
    sram = root / "benchmark.srm"
    rom.write_bytes(b"original-standalone-rom-fixture")
    sram.write_bytes(bytes(INSPECTOR.SRAM_SIZE))

    sources = (
        root / "source" / "core.asm",
        root / "source" / "wrapper.asm",
    )
    builder = root / "source" / "builder.py"
    write_text(sources[0], "db $01\n")
    write_text(sources[1], 'incsrc "core.asm"\n')
    write_text(builder, "VERSION = 1\n")

    static_manifest = root / "static.manifest.json"
    static = {
        "schema_version": 1,
        "artifact_class": "standalone-original-diagnostic-rom",
        "status": "verified-static-host-build",
        "evidence_level": "verified-static",
        "private_only": True,
        "production_input": False,
        "chrono_trigger_source_rom_read": False,
        "project_epoch_production_catalogs_used": False,
        "project_epoch_hooks_installed": False,
        "project_epoch_rom_write_guard": {
            "used_as_production_approval": False,
        },
        "host_audit": {
            "status": "complete-diff-valid",
            "all_changed_bytes_declared": True,
            "target_sha256": TOOL.sha256_path(rom),
        },
        "outputs": {
            "rom": record(rom),
            "sram": record(sram),
        },
        "assembly_sources": [record(path) for path in sources],
        "builder_source": record(builder),
    }
    write_text(
        static_manifest,
        json.dumps(static, indent=2, sort_keys=True) + "\n",
    )

    core1 = passing_core()
    core2 = bytearray(core1)
    for index, offset in enumerate(range(0x021E, 0x0226), start=1):
        core2[offset] = index
    core2[INSPECTOR.BST_WRAM_OFFSET + 0x1000] ^= 1
    states = (
        root / "run1" / "benchmark.state.auto",
        root / "run2" / "benchmark.state.auto",
    )
    states[0].parent.mkdir(parents=True, exist_ok=True)
    states[1].parent.mkdir(parents=True, exist_ok=True)
    states[0].write_bytes(retroarch_rastate.make_minimal_container(core1))
    states[1].write_bytes(
        retroarch_rastate.make_minimal_container(bytes(core2))
    )

    base_config = root / "base.cfg"
    write_text(
        base_config,
        "\n".join(
            f'{key} = "{value}"'
            for key, value in TOOL.BASE_CONFIG_EXPECTED.items()
        )
        + "\n",
    )
    configs = (root / "run1.cfg", root / "run2.cfg")
    for config, state in zip(configs, states, strict=True):
        values = {
            "savestate_auto_load": "false",
            "savestate_auto_save": "true",
            "savestate_file_compression": "false",
            "save_file_compression": "false",
            "savefile_directory": str(root.resolve()),
            "savestate_directory": str(state.parent.resolve()),
            "runtime_log": "false",
        }
        write_text(
            config,
            "\n".join(
                f'{key} = "{value}"' for key, value in values.items()
            )
            + "\n",
        )

    retroarch = root / "tools" / "retroarch.exe"
    core = root / "tools" / "bsnes_libretro.dll"
    core_info = root / "tools" / "bsnes_libretro.info"
    retroarch.parent.mkdir(parents=True, exist_ok=True)
    retroarch.write_bytes(b"synthetic-retroarch")
    core.write_bytes(b"synthetic-bsnes")
    write_text(
        core_info,
        'corename = "bsnes"\n'
        'display_version = "115"\n'
        "firmware_count = 20\n",
    )

    logs = (
        states[0].parent / "benchmark.log",
        states[1].parent / "benchmark.log",
    )
    for log, config, state in zip(logs, configs, states, strict=True):
        state_base = state.with_suffix("")
        write_text(
            log,
            "\n".join(
                (
                    "[INFO] RetroArch 1.22.2 (Git 69a4f0e)",
                    (
                        "[INFO] [Core] Loading dynamic libretro core from: "
                        f'"{core.resolve()}".'
                    ),
                    (
                        '[INFO] [Config] Loading config: '
                        f'"{base_config.resolve()}".'
                    ),
                    (
                        '[INFO] [Config] Appending config: '
                        f'"{config.resolve()}".'
                    ),
                    (
                        '[INFO] [Override] Redirecting save file to '
                        f'"{sram.resolve()}".'
                    ),
                    (
                        '[INFO] [Override] Redirecting save state to '
                        f'"{state_base.resolve()}".'
                    ),
                    "[INFO] [Content] Content loading skipped.",
                    "[INFO] [SRAM] Skipping SRAM load.",
                    (
                        '[INFO] [State] Auto save state to '
                        f'"{state.resolve()}" succeeded.'
                    ),
                    (
                        "[INFO] [Runtime] Content ran for a total of: "
                        "00 hours, 00 minutes, 03 seconds."
                    ),
                )
            )
            + "\n",
        )

    pins = dataclasses.replace(
        TOOL.DEFAULT_PINS,
        static_manifest=file_pin(static_manifest),
        retroarch_exe=file_pin(retroarch),
        core=file_pin(core),
        core_info=file_pin(core_info),
        base_config=file_pin(base_config),
        run_configs=(file_pin(configs[0]), file_pin(configs[1])),
        logs=(file_pin(logs[0]), file_pin(logs[1])),
        rom_size=rom.stat().st_size,
        rom_sha256=TOOL.sha256_path(rom),
        rastate_size=states[0].stat().st_size,
        core_state_size=len(core1),
        max_frames=12,
        required_assembly_paths=tuple(
            TOOL.workspace_relative(path) for path in sources
        ),
        required_static_builder_path=TOOL.workspace_relative(builder),
    )
    return Fixture(
        root=root,
        static_manifest=static_manifest,
        states=states,
        logs=logs,
        configs=configs,
        base_config=base_config,
        retroarch=retroarch,
        core=core,
        core_info=core_info,
        output=root / "runtime.manifest.json",
        pins=pins,
    )


def replace_state_core(path: pathlib.Path, core: bytes) -> None:
    path.write_bytes(retroarch_rastate.make_minimal_container(core))


class Sha25665816RuntimeEvidenceManifestTests(unittest.TestCase):
    def fixture_context(self):
        return tempfile.TemporaryDirectory(
            prefix="sha_runtime_manifest_",
            dir=TOOL.PRIVATE_ROOT,
        )

    def test_two_inspector_passes_build_exact_span_manifest(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            calls: list[pathlib.Path] = []

            def inspector(path: pathlib.Path):
                calls.append(path.resolve())
                return INSPECTOR.inspect_path(path)

            result = TOOL.build_in_memory(
                **fixture.kwargs(),
                inspector=inspector,
            )
            self.assertEqual(calls, [path.resolve() for path in fixture.states])
            self.assertEqual(
                result.manifest["evidence_level"],
                "verified-runtime-standalone",
            )
            comparison = result.manifest["reproducibility"]
            self.assertEqual(comparison["full_core_state_difference_count"], 9)
            self.assertEqual(
                comparison["bounded_non_wram_difference"][
                    "differing_byte_count"
                ],
                8,
            )
            self.assertEqual(
                comparison["uncleared_irrelevant_wram"][
                    "differing_byte_count"
                ],
                1,
            )
            self.assertEqual(
                [span["name"] for span in comparison["defined_evidence_spans"]],
                ["sram", "scratch_with_guards", "result_record"],
            )
            self.assertFalse(
                comparison["timing"]["production_timing_approved"]
            )
            TOOL.write_manifest(result, fixture.output)
            TOOL.write_manifest(result, fixture.output)
            self.assertEqual(
                fixture.output.read_bytes(),
                result.manifest_bytes,
            )

    def test_result_padding_difference_is_rejected_between_runs(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            core = bytearray(
                retroarch_rastate.extract_memory(fixture.states[1].read_bytes())
            )
            core[
                INSPECTOR.BST_WRAM_OFFSET
                + INSPECTOR.RESULT_ADDRESS
                + 0x74
            ] ^= 1
            replace_state_core(fixture.states[1], bytes(core))
            fixture.pins = dataclasses.replace(
                fixture.pins,
                rastate_size=fixture.states[1].stat().st_size,
            )
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "defined evidence span differs|decoded benchmark results differ",
            ):
                TOOL.build_in_memory(**fixture.kwargs())

    def test_scratch_difference_is_rejected_between_runs(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            core = bytearray(
                retroarch_rastate.extract_memory(fixture.states[1].read_bytes())
            )
            core[
                INSPECTOR.BST_WRAM_OFFSET
                + INSPECTOR.SCRATCH_START
                + 0x10
            ] ^= 1
            replace_state_core(fixture.states[1], bytes(core))
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "defined evidence span differs",
            ):
                TOOL.build_in_memory(**fixture.kwargs())

    def test_unexpected_non_wram_difference_is_rejected(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            core = bytearray(
                retroarch_rastate.extract_memory(fixture.states[1].read_bytes())
            )
            core[0x100] ^= 1
            replace_state_core(fixture.states[1], bytes(core))
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "outside the bounded",
            ):
                TOOL.build_in_memory(**fixture.kwargs())

    def test_missing_log_fact_fails_even_with_updated_log_pin(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            text = fixture.logs[0].read_text(encoding="utf-8")
            write_text(
                fixture.logs[0],
                text.replace("[INFO] [SRAM] Skipping SRAM load.\n", ""),
            )
            fixture.pins = dataclasses.replace(
                fixture.pins,
                logs=(file_pin(fixture.logs[0]), fixture.pins.logs[1]),
            )
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "Skipping SRAM load",
            ):
                TOOL.build_in_memory(**fixture.kwargs())

    def test_unsafe_static_manifest_fails_with_updated_manifest_pin(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            source = json.loads(
                fixture.static_manifest.read_text(encoding="utf-8")
            )
            source["production_input"] = True
            write_text(
                fixture.static_manifest,
                json.dumps(source, indent=2, sort_keys=True) + "\n",
            )
            fixture.pins = dataclasses.replace(
                fixture.pins,
                static_manifest=file_pin(fixture.static_manifest),
            )
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "production_input",
            ):
                TOOL.build_in_memory(**fixture.kwargs())

    def test_tool_pin_output_scope_and_conflict_fail_closed(self) -> None:
        with self.fixture_context() as directory:
            fixture = make_fixture(pathlib.Path(directory))
            fixture.core.write_bytes(b"different")
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "bsnes libretro core",
            ):
                TOOL.build_in_memory(**fixture.kwargs())

            with self.assertRaises(TOOL.RuntimeEvidenceError):
                TOOL.validate_private_output(ROOT / "outside.json")

            fixture = make_fixture(pathlib.Path(directory) / "second")
            result = TOOL.build_in_memory(**fixture.kwargs())
            fixture.output.write_bytes(b"different")
            with self.assertRaisesRegex(
                TOOL.RuntimeEvidenceError,
                "refusing to overwrite",
            ):
                TOOL.write_manifest(result, fixture.output)


if __name__ == "__main__":
    unittest.main()
