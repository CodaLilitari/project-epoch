from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "run_mesen_event11c_relocated_trace.py"
ACCEPTANCE_SPEC = (
    ROOT
    / "references"
    / "mesen_event11c_relocated_trace_accepted_artifacts_v3.json"
)


def load_module(name: str, path: Path) -> types.ModuleType:
    source = path.read_bytes()
    code = compile(source, str(path), "exec", dont_inherit=True)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except Exception:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return module


TOOL = load_module("run_mesen_event11c_relocated_trace", TOOL_PATH)


def make_exact_edit_fixture() -> tuple[bytes, bytes, tuple[object, ...]]:
    source = bytearray(TOOL.EVENT_DECOMPRESSED_SIZE)
    transformed = bytearray(source)
    edits: list[object] = []
    delta = (
        TOOL.AUDIT.RELOCATED_COMPATIBILITY_WRAM_START
        - TOOL.AUDIT.COMPATIBILITY_WRAM_START
    )
    for command_offset, opcode, old_address, width in (
        TOOL.AUDIT.EXPECTED_COMPATIBILITY_RELOCATION_SITES
    ):
        new_address = old_address + delta
        source[command_offset + 1] = opcode
        transformed[command_offset + 1] = opcode
        source[
            command_offset + 2:command_offset + 5
        ] = old_address.to_bytes(3, "little")
        transformed[
            command_offset + 2:command_offset + 5
        ] = new_address.to_bytes(3, "little")
        edits.append(
            types.SimpleNamespace(
                event_id=TOOL.EVENT_ID,
                object_id=TOOL.AUDIT.COMPATIBILITY_EVENT_OBJECT_ID,
                event_data_command_offset=command_offset,
                packet_opcode_offset=command_offset + 1,
                opcode=opcode,
                packet_address_operand_offset=command_offset + 2,
                old_address=old_address,
                new_address=new_address,
                width=width,
            )
        )
    return bytes(source), bytes(transformed), tuple(edits)


def make_synthetic_provenance() -> object:
    source, transformed, _edits = make_exact_edit_fixture()
    changed_offsets = tuple(
        index
        for index, (old, new) in enumerate(zip(source, transformed))
        if old != new
    )
    return TOOL.PacketProvenance(
        source=source,
        transformed=transformed,
        source_sha256=hashlib.sha256(source).hexdigest(),
        transformed_sha256=hashlib.sha256(transformed).hexdigest(),
        compressed_size=TOOL.EVENT_COMPRESSED_SIZE,
        changed_offsets=changed_offsets,
        edit_count=TOOL.EXPECTED_EDIT_COUNT,
    )


class RunMesenEvent11cRelocatedTraceTests(unittest.TestCase):
    def test_acceptance_spec_pins_sources_and_safe_artifacts(self) -> None:
        spec = json.loads(ACCEPTANCE_SPEC.read_text(encoding="utf-8"))
        self.assertEqual(
            spec["schema"],
            "project-epoch-mesen-event11c-relocated-acceptance-v3",
        )
        self.assertEqual(spec["collector"]["schema"], TOOL.TRACE_SCHEMA)
        self.assertEqual(spec["collector"]["version"], 2)
        self.assertFalse(spec["launcher"]["legacy_source_executed"])
        self.assertTrue(spec["launcher"]["pinned_modules_exact_byte_compiled"])
        self.assertTrue(
            spec["launcher"]["collector_and_state_staged_from_verified_bytes"]
        )
        self.assertTrue(spec["launcher"]["collector_outputs_staged_before_publish"])
        self.assertTrue(spec["launcher"]["exclusive_output_publication"])
        self.assertEqual(spec["controls"]["screenshot_field_frame_mod16"], 0)
        self.assertEqual(
            spec["controls"]["screenshot_spekkio_sprite_frame"],
            {"crono-marle-lucca": 4, "frog-robo": 22},
        )
        source_rows = (
            ("collector", TOOL.COLLECTOR),
            ("validator", TOOL.VALIDATOR_PATH),
            ("launcher", TOOL_PATH),
        )
        for key, path in source_rows:
            self.assertEqual(
                spec[key]["path"],
                path.relative_to(ROOT).as_posix(),
            )
            self.assertEqual(spec[key]["size"], path.stat().st_size)
            self.assertEqual(spec[key]["sha256"], TOOL.sha256_file(path))

        artifact_paths = [row["path"] for row in spec["artifacts"]]
        self.assertEqual(artifact_paths, sorted(artifact_paths))
        self.assertEqual(len(artifact_paths), len(set(artifact_paths)))
        forbidden = {".sfc", ".smc", ".srm", ".mss", ".state", ".bin"}
        self.assertTrue(
            all(
                Path(path).suffix.lower() not in forbidden
                and "\\" not in path
                and not path.startswith("/")
                and ".." not in Path(path).parts
                for path in artifact_paths
            )
        )

        artifact_contract = {
            (
                row["path"].split("/", 2)[0],
                row["path"].split("/", 2)[1],
                Path(row["path"]).name,
            ): (row["size"], row["sha256"])
            for row in spec["artifacts"]
        }
        for (profile, variant), outputs in TOOL.EXPECTED_OUTPUTS.items():
            self.assertEqual(
                artifact_contract[(profile, variant, "trace.json")],
                outputs["trace"],
            )
            self.assertEqual(
                artifact_contract[(profile, variant, "endpoint.png")],
                outputs["screenshot"],
            )

    def test_all_imported_sources_and_collector_are_hash_pinned(self) -> None:
        expected = {
            TOOL.OLD_LAUNCHER_PATH: TOOL.OLD_LAUNCHER_SHA256,
            TOOL.AUDIT_PATH: TOOL.AUDIT_SHA256,
            TOOL.COLLECTOR: TOOL.COLLECTOR_SHA256,
            TOOL.VALIDATOR_PATH: TOOL.VALIDATOR_SHA256,
        }
        for path, expected_hash in expected.items():
            with self.subTest(path=path.name):
                self.assertEqual(TOOL.sha256_file(path), expected_hash)

    def test_exact_byte_loader_never_uses_sourcefileloader_or_legacy_exec(
        self,
    ) -> None:
        launcher_source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertNotIn("spec_from_file_location", launcher_source)
        self.assertFalse(hasattr(TOOL, "OLD_LAUNCHER"))
        self.assertEqual(
            hashlib.sha256(TOOL._OLD_LAUNCHER_SOURCE).hexdigest(),
            TOOL.OLD_LAUNCHER_SHA256,
        )
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "pinned_fixture.py"
            source_path.write_text("VALUE = 73\n", encoding="utf-8")
            expected = TOOL.sha256_file(source_path)
            module_name = "_project_epoch_exact_byte_fixture"
            try:
                loaded = TOOL._load_pinned_module(
                    module_name,
                    source_path,
                    expected,
                )
                self.assertEqual(loaded.VALUE, 73)
                self.assertIsNone(loaded.__loader__)
                self.assertIsNone(loaded.__spec__)
            finally:
                sys.modules.pop(module_name, None)

    def test_import_does_not_require_private_tree(self) -> None:
        real_resolve = Path.resolve

        def guarded_resolve(
            path: Path,
            strict: bool = False,
        ) -> Path:
            if strict and "private" in tuple(
                part.casefold() for part in path.parts
            ):
                raise AssertionError(
                    "module import attempted strict private-path access"
                )
            return real_resolve(path, strict=strict)

        with mock.patch.object(Path, "resolve", guarded_resolve):
            imported = load_module(
                "run_mesen_event11c_relocated_trace_clean_import",
                TOOL_PATH,
            )
        self.assertEqual(imported.PRIVATE_ROOT.name, "private")

    def test_parser_exposes_no_user_packet_paths(self) -> None:
        destinations = {
            action.dest for action in TOOL.build_parser()._actions
        }
        self.assertNotIn("source_packet", destinations)
        self.assertNotIn("transformed_packet", destinations)
        self.assertIn("exploratory", destinations)

    def test_default_run_refuses_before_private_path_resolution(self) -> None:
        args = types.SimpleNamespace(
            profile="frog-robo",
            variant="zero",
            output_dir=Path("does-not-exist"),
            mesen=Path("does-not-exist"),
            rom=Path("does-not-exist"),
            state=Path("does-not-exist"),
            sram=Path("does-not-exist"),
            timeout=60,
            exploratory=False,
        )
        with mock.patch.object(TOOL, "EXPECTED_OUTPUTS", {}):
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "no accepted output contract",
            ):
                TOOL.run(args)

    def test_private_path_guards_reject_outside_and_save_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            workspace = temp_root / "workspace"
            private_root = workspace / "private"
            private_root.mkdir(parents=True)
            saves = private_root / "tools" / "mesen2" / "app" / "Saves"
            saves.mkdir(parents=True)
            with mock.patch.object(TOOL, "ROOT", workspace):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "resolves outside",
                ):
                    TOOL.prepare_private_output_dir(
                        temp_root / "outside-output"
                    )
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "overlaps protected tree",
                ):
                    TOOL.prepare_private_output_dir(
                        saves / "trace-output",
                        forbidden_roots=(saves,),
                    )

    def test_exact_twelve_edit_twenty_four_diff_contract(self) -> None:
        source, transformed, edits = make_exact_edit_fixture()
        changed = TOOL.validate_exact_relocation_edits(
            source,
            transformed,
            edits,
        )
        self.assertEqual(len(changed), TOOL.EXPECTED_DIFF_COUNT)

    def test_relocation_contract_rejects_one_extra_diff(self) -> None:
        source, transformed, edits = make_exact_edit_fixture()
        drifted = bytearray(transformed)
        drifted[0] ^= 1
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "exact 24 approved byte diffs",
        ):
            TOOL.validate_exact_relocation_edits(
                source,
                bytes(drifted),
                edits,
            )

    def test_noncanonical_rom_is_rejected_before_packet_staging(self) -> None:
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "canonical ROM provenance failed",
        ):
            TOOL.validate_packet_provenance(b"not a ROM")

    @unittest.skipUnless(
        TOOL.DEFAULT_ROM.is_file(),
        "canonical private ROM is intentionally absent in clean checkout",
    )
    def test_private_canonical_rom_derives_exact_packet_provenance(self) -> None:
        provenance = TOOL.derive_event11c_packets(TOOL.DEFAULT_ROM)
        self.assertEqual(
            provenance.source_sha256,
            TOOL.SOURCE_PACKET_SHA256,
        )
        self.assertEqual(
            provenance.transformed_sha256,
            TOOL.TRANSFORMED_PACKET_SHA256,
        )
        self.assertEqual(provenance.edit_count, TOOL.EXPECTED_EDIT_COUNT)
        self.assertEqual(
            len(provenance.changed_offsets),
            TOOL.EXPECTED_DIFF_COUNT,
        )

    def test_packet_files_exist_only_during_disposable_staging(self) -> None:
        provenance = make_synthetic_provenance()
        staged_paths: list[Path] = []
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            private_root = workspace / "private"
            private_root.mkdir(parents=True)
            with mock.patch.object(TOOL, "ROOT", workspace):
                with mock.patch.object(
                    TOOL,
                    "SOURCE_PACKET_SHA256",
                    provenance.source_sha256,
                ):
                    with mock.patch.object(
                        TOOL,
                        "TRANSFORMED_PACKET_SHA256",
                        provenance.transformed_sha256,
                    ):
                        with tempfile.TemporaryDirectory(
                            dir=private_root,
                        ) as staging_directory:
                            staged_paths = list(
                                TOOL.write_private_packet_files(
                                    Path(staging_directory),
                                    provenance,
                                ).values()
                            )
                            self.assertTrue(
                                all(path.is_file() for path in staged_paths)
                            )
                            self.assertEqual(
                                TOOL.sha256_file(staged_paths[0]),
                                provenance.source_sha256,
                            )
                            self.assertEqual(
                                TOOL.sha256_file(staged_paths[1]),
                                provenance.transformed_sha256,
                            )
                self.assertTrue(
                    all(not os.path.lexists(path) for path in staged_paths)
                )

    def test_exclusive_pair_publish_rolls_back_only_created_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory).resolve(strict=True)
            trace_path = output_root / "trace.json"
            screenshot_path = output_root / "endpoint.png"
            screenshot_path.write_bytes(b"preexisting victim")
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "refusing to overwrite endpoint PNG",
            ):
                TOOL.publish_output_pair(
                    output_root,
                    trace_path,
                    b'{"safe":true}\n',
                    screenshot_path,
                    b"\x89PNG\r\n\x1a\nsafe",
                )
            self.assertFalse(os.path.lexists(trace_path))
            self.assertEqual(
                screenshot_path.read_bytes(),
                b"preexisting victim",
            )

    def test_full_exploratory_run_isolated_and_deletes_staging(self) -> None:
        provenance = make_synthetic_provenance()
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            private_root = workspace / "private"
            app_root = private_root / "tools" / "mesen2" / "app"
            shared_saves = app_root / "Saves"
            shared_saves.mkdir(parents=True)
            for name in (
                "Mesen.exe",
                "MesenCore.dll",
                "libHarfBuzzSharp.dll",
                "libSkiaSharp.dll",
                "MesenNesDB.txt",
                "settings.json",
            ):
                (app_root / name).write_bytes(
                    f"synthetic {name}\n".encode("ascii")
                )
            (app_root.parent / "Mesen_2.1.1_Windows.zip").write_bytes(
                b"synthetic archive\n"
            )
            rom = private_root / "canonical.sfc"
            state = private_root / "checkpoint.mss"
            sram = private_root / "disposable.srm"
            rom.write_bytes(b"synthetic ROM\n")
            state.write_bytes(b"synthetic state\n")
            sram.write_bytes(b"synthetic SRAM\n")
            sentinel = shared_saves / "unrelated.srm"
            sentinel.write_bytes(b"must remain exact\n")
            sentinel_hash = TOOL.sha256_file(sentinel)
            output_dir = private_root / "trace-output"
            args = TOOL.build_parser().parse_args(
                [
                    "--profile",
                    "frog-robo",
                    "--variant",
                    "zero",
                    "--output-dir",
                    str(output_dir),
                    "--mesen",
                    str(app_root / "Mesen.exe"),
                    "--rom",
                    str(rom),
                    "--state",
                    str(state),
                    "--sram",
                    str(sram),
                    "--exploratory",
                ]
            )
            observed_packet_paths: list[Path] = []
            observed_staged_paths: list[Path] = []

            def fake_run(
                command: list[str],
                **kwargs: object,
            ) -> subprocess.CompletedProcess[str]:
                environment = kwargs["env"]
                assert isinstance(environment, dict)
                source_path = Path(environment["PE_SOURCE_PACKET"])
                transformed_path = Path(
                    environment["PE_TRANSFORMED_PACKET"]
                )
                state_path = Path(environment["PE_STATE_PATH"])
                collector_path = Path(command[-2])
                staged_trace_path = Path(environment["PE_TRACE_OUT"])
                staged_screenshot_path = Path(
                    environment["PE_TRACE_SCREENSHOT"]
                )
                observed_packet_paths.extend(
                    (source_path, transformed_path)
                )
                observed_staged_paths.extend(
                    (
                        state_path,
                        collector_path,
                        staged_trace_path,
                        staged_screenshot_path,
                    )
                )
                self.assertEqual(
                    TOOL.sha256_file(source_path),
                    provenance.source_sha256,
                )
                self.assertEqual(
                    TOOL.sha256_file(transformed_path),
                    provenance.transformed_sha256,
                )
                self.assertEqual(state_path.read_bytes(), state.read_bytes())
                self.assertEqual(
                    TOOL.sha256_file(collector_path),
                    TOOL.COLLECTOR_SHA256,
                )
                self.assertNotEqual(collector_path, TOOL.COLLECTOR)
                self.assertNotEqual(state_path, state)
                self.assertNotEqual(staged_trace_path, output_dir / "trace.json")
                self.assertFalse((output_dir / "trace.json").exists())
                self.assertFalse((output_dir / "endpoint.png").exists())
                staged_rom = Path(command[-1])
                staged_sram = (
                    Path(kwargs["cwd"])
                    / "Saves"
                    / f"{staged_rom.stem}.srm"
                )
                self.assertTrue(staged_rom.is_file())
                self.assertTrue(staged_sram.is_file())
                staged_trace_path.write_text(
                    "{}",
                    encoding="utf-8",
                )
                staged_screenshot_path.write_bytes(
                    b"\x89PNG\r\n\x1a\nsynthetic"
                )
                return subprocess.CompletedProcess(
                    command,
                    TOOL.EXPECTED_EXIT_CODE,
                    stdout="",
                    stderr="",
                )

            hash_side_effect = (
                lambda path, _expected, _label: TOOL.sha256_file(path)
            )
            state_hash = TOOL.sha256_file(state)
            with mock.patch.dict(
                TOOL.PINNED_HASHES,
                {"state": state_hash},
                clear=False,
            ):
                with mock.patch.object(TOOL, "ROOT", workspace):
                    with mock.patch.object(
                        TOOL,
                        "SOURCE_PACKET_SHA256",
                        provenance.source_sha256,
                    ):
                        with mock.patch.object(
                            TOOL,
                            "TRANSFORMED_PACKET_SHA256",
                            provenance.transformed_sha256,
                        ):
                            with mock.patch.object(
                                TOOL,
                                "require_hash",
                                side_effect=hash_side_effect,
                            ):
                                with mock.patch.object(
                                    TOOL,
                                    "derive_event11c_packets",
                                    return_value=provenance,
                                ):
                                    with mock.patch.object(
                                        TOOL.subprocess,
                                        "run",
                                        side_effect=fake_run,
                                    ):
                                        with mock.patch.object(
                                            TOOL,
                                            "load_trace_bytes",
                                            return_value={
                                                "callbacks": [{}, {}]
                                            },
                                        ):
                                            result = TOOL.run(args)

            self.assertEqual(
                result["status"],
                "exploratory-private-diagnostic-case-not-accepted",
            )
            self.assertTrue(result["disposable_staging_deleted"])
            self.assertEqual(TOOL.sha256_file(sentinel), sentinel_hash)
            self.assertTrue(
                all(
                    not os.path.lexists(path)
                    for path in (
                        observed_packet_paths + observed_staged_paths
                    )
                )
            )
            self.assertEqual(
                list(output_dir.glob(".event11c_relocated_staging_*")),
                [],
            )
            self.assertEqual(
                sorted(path.name for path in output_dir.iterdir()),
                ["endpoint.png", "trace.json"],
            )


if __name__ == "__main__":
    unittest.main()
