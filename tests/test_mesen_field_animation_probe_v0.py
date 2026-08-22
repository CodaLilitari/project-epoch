from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
import zlib


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = ROOT / "tools" / "run_mesen_field_animation_probe_v0.py"
COLLECTOR_PATH = ROOT / "tools" / "mesen_field_animation_probe_v0.lua"


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


TOOL = load_module("mesen_field_animation_probe_v0", LAUNCHER_PATH)


def make_rom() -> bytearray:
    rom = bytearray(TOOL.ROM_SIZE)
    for pc, (_, opcode, _) in TOOL.WATCHED.items():
        rom[TOOL.hirom_file_offset(pc)] = opcode
    return rom


def make_synthetic_png() -> bytes:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        return (
            len(payload).to_bytes(4, "big")
            + chunk_type
            + payload
            + crc.to_bytes(4, "big")
        )

    ihdr = (
        (1).to_bytes(4, "big")
        + (1).to_bytes(4, "big")
        + bytes((8, 0, 0, 0, 0))
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + chunk(b"IEND", b"")
    )


def snapshot() -> dict[str, object]:
    return {
        "location": 0x01D1,
        "explore_mode": 1,
        "dialog_state": 0,
        "field_phase_mod16": 7,
        "leader_object": 0x0E,
        "leader_x": 1568,
        "leader_y": 2623,
        "active_party_hex": "060403",
    }


def mapping_rows() -> list[dict[str, object]]:
    return [
        {
            "pc24": pc,
            "role": role,
            "opcode": opcode,
            "mapped_address": mapped,
            "mapping_is_prg_rom": True,
        }
        for pc, (role, opcode, mapped) in TOOL.WATCHED.items()
    ]


def base_record(
    pc: int,
    binding: dict[str, int],
    *,
    frame: int,
    selector: int = 0,
    cursor: int = 0,
    stream_address: int | None = None,
    stream_value: int | None = None,
) -> dict[str, object]:
    role, opcode, _ = TOOL.WATCHED[pc]
    return {
        "seq": -1,
        "frame": frame,
        "pc24": pc,
        "role": role,
        "opcode": opcode,
        "cpu": {
            "a": 0x1234,
            "x": binding["object_slot"],
            "y": 0,
            "d": 0x0100,
            "ps": 0x30,
            "sp": 0x01FF,
            "db": None,
        },
        "object_slot": binding["object_slot"],
        "object_status": binding["object_status"],
        "object_id": binding["logical_pc_id"],
        "selector": selector,
        "cursor": cursor,
        "alt_mode": 0,
        "alt_selector": 0,
        "facing": 3 if binding["logical_pc_id"] == 6 else 0,
        "delay": 0,
        "timing_base": binding["timing_base"],
        "main_base": binding["main_base"],
        "facing_stride": 0x00F4,
        "cached_frame": 0,
        "assembly_bank": 0xDC,
        "assembly_base": 0,
        "dp_c1": 0,
        "dp_d6": 0,
        "dp_d8": 0xE4,
        "dp_d9": 0,
        "stream_address": stream_address,
        "stream_value": stream_value,
    }


def special_right_rows(pc: int, rom: bytearray) -> list[dict[str, object]]:
    magus = dict(TOOL.EXPECTED_BINDINGS[2])
    if pc == 0xC0CBC2:
        triples = [
            (20, 1, 0xE44DE1),
            (27, 2, 0xE44DE2),
            (34, 3, 0xE44DE3),
            (41, 4, 0xE44DE4),
            (48, 5, 0xE44DE5),
            (55, 0, 0xE44DE0),
            (62, 1, 0xE44DE1),
            (69, 2, 0xE44DE2),
            (76, 3, 0xE44DE3),
            (83, 4, 0xE44DE4),
            (90, 5, 0xE44DE5),
            (97, 0, 0xE44DE0),
        ]
    elif pc == 0xC0CA35:
        triples = [
            (20, 1, 0xE4AEC5),
            (27, 2, 0xE4AEC6),
            (34, 3, 0xE4AEC7),
            (41, 4, 0xE4AEC8),
            (48, 5, 0xE4AEC9),
            (55, 6, 0xE4AECA),
            (62, 1, 0xE4AEC5),
            (69, 2, 0xE4AEC6),
            (76, 3, 0xE4AEC7),
            (83, 4, 0xE4AEC8),
            (90, 5, 0xE4AEC9),
            (97, 6, 0xE4AECA),
        ]
    elif pc == 0xC0CA3D:
        triples = [(55, 6, 0xE4AEC4), (97, 6, 0xE4AEC4)]
    else:
        triples = [
            (frame, cursor, None)
            for frame, cursor in zip(
                (20, 27, 34, 41, 48, 55, 62, 69, 76, 83, 90, 97),
                (1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0),
                strict=True,
            )
        ]
    rows: list[dict[str, object]] = []
    for frame, cursor, address in triples:
        if address is None and pc in (0xC0CC04,):
            address = 0xE44000 + frame
        value = None
        if address is not None:
            value = (address ^ 0x5A) & 0xFF
            rom[TOOL.hirom_file_offset(address)] = value
        rows.append(
            base_record(
                pc,
                magus,
                frame=frame,
                selector=1,
                cursor=cursor,
                stream_address=address,
                stream_value=value,
            )
        )
    return rows


def make_trace(route: str = "idle", repetition: int = 1) -> tuple[dict[str, object], bytes]:
    rom = make_rom()
    records: list[dict[str, object]] = []
    bindings = [dict(row) for row in TOOL.EXPECTED_BINDINGS]
    for pc in TOOL.ORDERED_PCS:
        special = special_right_rows(pc, rom) if route == "right" else []
        records.extend(special)
        remaining = TOOL.EXPECTED_COUNTS[route][f"{pc:06X}"] - len(special)
        for index in range(remaining):
            binding = bindings[index % len(bindings)]
            stream_address = None
            stream_value = None
            if pc in (0xC0CA35, 0xC0CA3D, 0xC0CBC2, 0xC0CC04):
                stream_address = 0xE40000 + ((pc + index * 17) & 0xFFFF)
                stream_value = (stream_address ^ pc ^ index) & 0xFF
                rom[TOOL.hirom_file_offset(stream_address)] = stream_value
            records.append(
                base_record(
                    pc,
                    binding,
                    frame=(index % TOOL.TERMINAL_FRAME) + 1,
                    stream_address=stream_address,
                    stream_value=stream_value,
                )
            )
    for sequence, record in enumerate(records):
        record["seq"] = sequence
    trace: dict[str, object] = {
        "schema": TOOL.TRACE_SCHEMA,
        "evidence_level": TOOL.EVIDENCE_LEVEL,
        "collector_version": TOOL.COLLECTOR_VERSION,
        "emulator": "Mesen 2.1.1",
        "route": route,
        "repetition": repetition,
        "observer": {
            "mechanism": "broad-exec-callback-exact-pc-router",
            "write_calls": 0,
            "watched_pc_mappings": mapping_rows(),
        },
        "input_contract": {
            "terminal_frame": TOOL.TERMINAL_FRAME,
            "right_start_frame": TOOL.RIGHT_START_FRAME if route == "right" else None,
            "right_end_frame": TOOL.RIGHT_END_FRAME if route == "right" else None,
        },
        "checkpoint_bindings": bindings,
        "pre": snapshot(),
        "counts": dict(TOOL.EXPECTED_COUNTS[route]),
        "records": records,
        "post": snapshot(),
        "termination": {
            "collector_stopped": True,
            "success": True,
            "overflow": False,
            "observer_error": None,
        },
    }
    return trace, bytes(rom)


class MesenFieldAnimationProbeV0Tests(unittest.TestCase):
    def test_clean_clone_import_does_not_require_private_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            tools = repo / "tools"
            tools.mkdir()
            copied = tools / LAUNCHER_PATH.name
            copied.write_bytes(LAUNCHER_PATH.read_bytes())
            module = load_module("clean_clone_field_probe", copied)
            self.assertEqual(module.ROOT, repo.resolve())
            self.assertFalse((repo / "private").exists())

    def test_tracked_root_and_collector_pin_are_exact(self) -> None:
        self.assertEqual(TOOL.ROOT, ROOT)
        self.assertEqual(TOOL.COLLECTOR, COLLECTOR_PATH)
        source = COLLECTOR_PATH.read_bytes()
        self.assertEqual(len(source), TOOL.COLLECTOR_SIZE)
        self.assertEqual(hashlib.sha256(source).hexdigest(), TOOL.COLLECTOR_SHA256)

    def test_idle_synthetic_trace_passes(self) -> None:
        trace, rom = make_trace("idle")
        summary = TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)
        self.assertEqual(summary["record_count"], 1152)
        self.assertFalse(summary["complete_selector_01_loop"])

    def test_right_synthetic_trace_passes_and_closes_loop(self) -> None:
        trace, rom = make_trace("right")
        summary = TOOL.validate_trace_document(trace, route="right", repetition=1, rom_bytes=rom)
        self.assertEqual(summary["record_count"], 1118)
        self.assertTrue(summary["complete_selector_01_loop"])

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(TOOL.ProbeError, "duplicate JSON key"):
            TOOL.decode_json_object(b'{"schema":1,"schema":2}', "duplicate")

    def test_trace_maximum_size_is_enforced_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "trace.json"
            path.write_bytes(b"{" + b" " * 20 + b"}")
            with mock.patch.object(TOOL, "MAX_TRACE_BYTES", 8):
                with self.assertRaisesRegex(TOOL.ProbeError, "size is outside"):
                    TOOL.load_trace_file(path, output_root=root)

    def test_missing_trace_and_invalid_png_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(TOOL.ProbeError, "not directly inside"):
                TOOL.load_trace_file(root / "missing.json", output_root=root)
        with self.assertRaisesRegex(TOOL.ProbeError, "valid PNG"):
            TOOL.validate_png_bytes(b"not-a-png")
        with self.assertRaises(TOOL.ProbeError):
            TOOL.validate_png_bytes(b"\x89PNG\r\n\x1a\nsynthetic")
        valid_png = make_synthetic_png()
        TOOL.validate_png_bytes(valid_png)
        corrupted = bytearray(valid_png)
        corrupted[-5] ^= 0x01
        with self.assertRaisesRegex(TOOL.ProbeError, "CRC"):
            TOOL.validate_png_bytes(bytes(corrupted))

    def test_extra_top_level_key_is_rejected(self) -> None:
        trace, rom = make_trace()
        trace["unexpected"] = 1
        with self.assertRaisesRegex(TOOL.ProbeError, "keys drifted"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_mapping_duplicate_or_wrong_address_is_rejected(self) -> None:
        trace, rom = make_trace()
        rows = trace["observer"]["watched_pc_mappings"]
        rows[1] = copy.deepcopy(rows[0])
        with self.assertRaisesRegex(TOOL.ProbeError, "mapping drifted"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)
        trace, rom = make_trace()
        trace["observer"]["watched_pc_mappings"][0]["mapped_address"] += 1
        with self.assertRaisesRegex(TOOL.ProbeError, "mapping drifted"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_boolean_cannot_substitute_for_integer_mapping_field(self) -> None:
        trace, rom = make_trace()
        trace["observer"]["watched_pc_mappings"][0]["opcode"] = True
        with self.assertRaises(TOOL.ProbeError):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_checkpoint_binding_mutation_is_rejected(self) -> None:
        trace, rom = make_trace()
        trace["checkpoint_bindings"][2]["logical_pc_id"] = 7
        with self.assertRaisesRegex(TOOL.ProbeError, "binding drifted"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_record_object_binding_mutation_is_rejected(self) -> None:
        trace, rom = make_trace()
        trace["records"][0]["object_id"] = 7
        with self.assertRaisesRegex(TOOL.ProbeError, "violates checkpoint binding"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_record_and_count_disagreement_is_rejected(self) -> None:
        trace, rom = make_trace()
        trace["records"].pop()
        with self.assertRaisesRegex(TOOL.ProbeError, "record count"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_static_opcode_mutation_is_rejected(self) -> None:
        trace, rom = make_trace()
        changed = bytearray(rom)
        changed[TOOL.hirom_file_offset(0xC0CA18)] ^= 0xFF
        with self.assertRaisesRegex(TOOL.ProbeError, "opcode preimage"):
            TOOL.validate_trace_document(
                trace,
                route="idle",
                repetition=1,
                rom_bytes=bytes(changed),
            )

    def test_static_stream_byte_mutation_is_rejected(self) -> None:
        trace, rom = make_trace()
        record = next(row for row in trace["records"] if row["stream_address"] is not None)
        changed = bytearray(rom)
        changed[TOOL.hirom_file_offset(record["stream_address"])] ^= 0xFF
        with self.assertRaisesRegex(TOOL.ProbeError, "stream byte disagrees"):
            TOOL.validate_trace_document(
                trace,
                route="idle",
                repetition=1,
                rom_bytes=bytes(changed),
            )

    def test_unclean_termination_is_rejected(self) -> None:
        trace, rom = make_trace()
        trace["termination"]["success"] = False
        with self.assertRaisesRegex(TOOL.ProbeError, "terminate cleanly"):
            TOOL.validate_trace_document(trace, route="idle", repetition=1, rom_bytes=rom)

    def test_right_loop_mutation_is_rejected(self) -> None:
        trace, rom = make_trace("right")
        record = next(
            row
            for row in trace["records"]
            if row["pc24"] == 0xC0CBC2
            and row["object_id"] == 6
            and row["selector"] == 1
        )
        record["frame"] += 1
        with self.assertRaisesRegex(TOOL.ProbeError, "main selector-01 loop"):
            TOOL.validate_trace_document(trace, route="right", repetition=1, rom_bytes=rom)

    def test_minimal_environment_drops_unrelated_and_secret_values(self) -> None:
        environment = TOOL.minimal_subprocess_environment(
            {
                "PATH": "safe",
                "TEMP": "temp",
                "AWS_SECRET_ACCESS_KEY": "secret",
                "PE_UNRELATED": "remove",
            }
        )
        self.assertEqual(environment["PATH"], "safe")
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)
        self.assertNotIn("PE_UNRELATED", environment)
        self.assertEqual(environment["PE_LAUNCH_PROTOCOL"], TOOL.LAUNCH_PROTOCOL)

    def test_wrong_process_exit_is_rejected(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with self.assertRaisesRegex(TOOL.ProbeError, "expected 41"):
            TOOL.require_expected_process_exit(completed)
        TOOL.require_expected_process_exit(
            subprocess.CompletedProcess([], TOOL.EXPECTED_EXIT_CODE, stdout="", stderr="")
        )

    def test_launch_and_exact_host_timeout_fail_closed(self) -> None:
        timeout = subprocess.TimeoutExpired(["Mesen.exe"], 88)
        with self.assertRaisesRegex(TOOL.ProbeError, "exact host timeout of 88 seconds"):
            TOOL.require_process_result(None, timeout, effective_timeout=88)
        with self.assertRaisesRegex(TOOL.ProbeError, "launch failed"):
            TOOL.require_process_result(
                None,
                OSError("synthetic launch failure"),
                effective_timeout=88,
            )

    def test_copy_failure_is_wrapped_and_never_creates_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            destination = root / "destination.bin"
            source.write_bytes(b"synthetic")
            with mock.patch.object(
                TOOL.shutil,
                "copyfile",
                side_effect=OSError("synthetic copy failure"),
            ):
                with self.assertRaisesRegex(TOOL.ProbeError, "failed to stage runtime"):
                    TOOL.copy_new_regular_file(source, destination, "runtime")
            self.assertFalse(os.path.lexists(destination))

    def test_source_or_staged_hash_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "guarded.bin"
            path.write_bytes(b"before")
            expected = {"guarded": hashlib.sha256(b"before").hexdigest()}
            TOOL.require_file_hashes_unchanged(
                {"guarded": path},
                expected,
                "synthetic source",
            )
            path.write_bytes(b"after")
            with self.assertRaisesRegex(TOOL.ProbeError, "synthetic source changed"):
                TOOL.require_file_hashes_unchanged(
                    {"guarded": path},
                    expected,
                    "synthetic source",
                )

    def test_surviving_staging_root_and_save_entries_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "staging"
            staging.mkdir()
            with self.assertRaisesRegex(TOOL.ProbeError, "was not deleted"):
                TOOL.require_staging_removed(staging)
            staging.rmdir()
            TOOL.require_staging_removed(staging)
        TOOL.require_exact_staged_save_entries(["nonce.srm"], "nonce.srm")
        with self.assertRaisesRegex(TOOL.ProbeError, "Saves directory drifted"):
            TOOL.require_exact_staged_save_entries(
                ["nonce.srm", "unexpected.bak"],
                "nonce.srm",
            )

    def test_manifest_records_launcher_version_hash_and_effective_timeouts(self) -> None:
        identities = {
            key: {"size": size, "sha256": digest}
            for key, (size, digest) in TOOL.PINNED_IDENTITIES.items()
        }
        manifest = TOOL.build_host_manifest(
            route="idle",
            repetition=1,
            mesen_timeout=73,
            launcher_identity={"size": 123, "sha256": "a" * 64},
            inputs=identities,
            trace_artifact={"path": "private/test_runs/x/trace.json", "size": 1, "sha256": "b" * 64},
            screenshot_artifact={"path": "private/test_runs/x/endpoint.png", "size": 1, "sha256": "c" * 64},
            summary={"record_count": 1},
        )
        self.assertEqual(manifest["launcher"]["version"], TOOL.LAUNCHER_VERSION)
        self.assertEqual(manifest["launcher"]["sha256"], "a" * 64)
        self.assertEqual(manifest["timeouts"]["mesen_test_runner_seconds"], 73)
        self.assertEqual(manifest["timeouts"]["host_subprocess_seconds"], 88)
        self.assertEqual(
            manifest["runtime"]["provenance_only_not_staged_or_executed"]["archive"]["sha256"],
            TOOL.PINNED_IDENTITIES["archive"][1],
        )

    def test_invalid_timeout_fails_before_private_resolution(self) -> None:
        args = TOOL.build_parser().parse_args(
            [
                "--route",
                "idle",
                "--repetition",
                "1",
                "--output-dir",
                "private/test_runs/new",
                "--timeout",
                "0",
            ]
        )
        with mock.patch.object(
            TOOL,
            "canonical_private_root",
            side_effect=AssertionError("must not resolve private inputs"),
        ):
            with self.assertRaisesRegex(TOOL.ProbeError, "timeout"):
                TOOL.run(args)

    def test_new_output_must_be_inside_exact_workspace_private_test_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            (private / "test_runs").mkdir(parents=True)
            outside = repo / "lookalike-private" / "test_runs" / "case"
            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=private / "test_runs",
            ):
                with self.assertRaisesRegex(TOOL.ProbeError, "strictly under"):
                    TOOL.prepare_private_output_dir(outside)
                created = TOOL.prepare_private_output_dir(
                    repo / "private" / "test_runs" / "nested" / "case"
                )
                self.assertEqual(created, (private / "test_runs" / "nested" / "case").resolve())

    def test_output_rejects_traversal_existing_and_protected_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            test_runs = private / "test_runs"
            test_runs.mkdir(parents=True)
            existing = test_runs / "existing"
            existing.mkdir()
            protected = test_runs / "protected"
            protected.mkdir()
            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=test_runs,
            ):
                with self.assertRaisesRegex(TOOL.ProbeError, "traversal"):
                    TOOL.prepare_private_output_dir(Path("private/test_runs/a/../b"))
                with self.assertRaisesRegex(TOOL.ProbeError, "new path"):
                    TOOL.prepare_private_output_dir(existing)
                with self.assertRaisesRegex(TOOL.ProbeError, "overlaps protected"):
                    TOOL.prepare_private_output_dir(
                        protected / "child",
                        forbidden_roots=(protected,),
                    )

    def test_output_rejects_rom_state_checkpoint_parent_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            test_runs = private / "test_runs"
            checkpoint = test_runs / "checkpoint"
            saves = private / "tools" / "mesen" / "Saves"
            checkpoint.mkdir(parents=True)
            saves.mkdir(parents=True)
            rom = checkpoint / "source.sfc"
            state = checkpoint / "source.mss"
            rom.write_bytes(b"synthetic-rom")
            state.write_bytes(b"synthetic-state")
            protected = tuple(
                dict.fromkeys((rom.parent, state.parent, saves))
            )
            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=test_runs,
            ):
                with self.assertRaisesRegex(TOOL.ProbeError, "overlaps protected"):
                    TOOL.prepare_private_output_dir(
                        checkpoint / "new-output",
                        forbidden_roots=protected,
                    )
                ordinary = TOOL.prepare_private_output_dir(
                    test_runs / "ordinary" / "new-output",
                    forbidden_roots=protected,
                )
                self.assertEqual(
                    ordinary,
                    (test_runs / "ordinary" / "new-output").resolve(),
                )

    def test_output_rejects_symlink_or_dangling_target_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            test_runs = private / "test_runs"
            test_runs.mkdir(parents=True)
            target = test_runs / "target"
            target.mkdir()
            link = test_runs / "link"
            dangling = test_runs / "dangling"
            try:
                os.symlink(target, link, target_is_directory=True)
                os.symlink(test_runs / "missing", dangling, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=test_runs,
            ):
                with self.assertRaises(TOOL.ProbeError):
                    TOOL.prepare_private_output_dir(link / "child")
                with self.assertRaisesRegex(TOOL.ProbeError, "new path"):
                    TOOL.prepare_private_output_dir(dangling)

    def test_output_deterministically_rejects_mocked_reparse_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            test_runs = private / "test_runs"
            mocked_reparse = test_runs / "junction"
            mocked_reparse.mkdir(parents=True)
            real_is_reparse = TOOL._is_reparse

            def fake_is_reparse(path: Path) -> bool:
                return Path(path) == mocked_reparse or real_is_reparse(path)

            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=test_runs,
            ), mock.patch.object(TOOL, "_is_reparse", side_effect=fake_is_reparse):
                with self.assertRaisesRegex(TOOL.ProbeError, "reparse point"):
                    TOOL.prepare_private_output_dir(mocked_reparse / "child")

    def test_output_deterministically_rejects_dangling_target_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            test_runs = private / "test_runs"
            test_runs.mkdir(parents=True)
            dangling = test_runs / "dangling"
            real_lexists = TOOL.os.path.lexists

            def fake_lexists(path: str | os.PathLike[str]) -> bool:
                return Path(path) == dangling or real_lexists(path)

            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=test_runs,
            ), mock.patch.object(TOOL.os.path, "lexists", side_effect=fake_lexists):
                with self.assertRaisesRegex(TOOL.ProbeError, "new path"):
                    TOOL.prepare_private_output_dir(dangling)

    def test_private_file_resolution_rejects_reparse_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            private.mkdir()
            source = private / "source.bin"
            source.write_bytes(b"x")
            link = private / "link.bin"
            try:
                os.symlink(source, link)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=private / "test_runs",
            ):
                with self.assertRaisesRegex(TOOL.ProbeError, "reparse"):
                    TOOL.resolve_private_file(link, "linked input")

    def test_private_file_deterministically_rejects_mocked_reparse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            private = repo / "private"
            private.mkdir()
            source = private / "source.bin"
            source.write_bytes(b"x")
            real_is_reparse = TOOL._is_reparse

            def fake_is_reparse(path: Path) -> bool:
                return Path(path) == source or real_is_reparse(path)

            with mock.patch.multiple(
                TOOL,
                ROOT=repo,
                PRIVATE_ROOT_LEXICAL=private,
                PRIVATE_TEST_RUNS_LEXICAL=private / "test_runs",
            ), mock.patch.object(TOOL, "_is_reparse", side_effect=fake_is_reparse):
                with self.assertRaisesRegex(TOOL.ProbeError, "reparse"):
                    TOOL.resolve_private_file(source, "mocked linked input")

    def test_lua_is_launcher_bound_and_contains_no_emulated_write_call(self) -> None:
        source = COLLECTOR_PATH.read_text(encoding="utf-8")
        compact = "".join(
            line.split("--", 1)[0] + "\n" for line in source.splitlines()
        )
        self.assertNotRegex(compact, r"emu\.write(?:16)?\s*\(")
        self.assertNotRegex(compact, r"emu\.save\w*\s*\(")
        for required in (
            "PE_WORKSPACE_PRIVATE_ROOT",
            "PE_OUTPUT_ROOT",
            "PE_STAGING_ROOT",
            "PE_LAUNCH_PROTOCOL",
            "PE_LAUNCH_NONCE",
        ):
            self.assertIn(required, source)
        self.assertIn('private_root .. "/test_runs"', source)

    def test_launcher_has_no_rom_or_patch_output_option(self) -> None:
        parser_help = TOOL.build_parser().format_help()
        self.assertNotIn("--output-rom", parser_help)
        self.assertNotIn("--patch", parser_help)


if __name__ == "__main__":
    unittest.main()
