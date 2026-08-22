from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_mesen_event11c_trace.py"
ACCEPTANCE_SPEC_PATH = (
    ROOT / "references" / "mesen_event11c_trace_accepted_artifacts_v1.json"
)


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("validate_mesen_event11c_trace", TOOL_PATH)


def observer() -> dict[str, object]:
    return {
        "read_pc24": 0xC06797,
        "read_mapped_address": 0x6797,
        "read_mapping_is_prg_rom": True,
        "write_pc24": 0xC06822,
        "write_mapped_address": 0x6822,
        "write_mapping_is_prg_rom": True,
        "mechanism": "broad-exec-callback-exact-pc-router",
        "checkpoint_direct_page": 0x0100,
        "checkpoint_frame": 3237,
    }


def snapshots(profile: str) -> tuple[dict[str, object], dict[str, object]]:
    if profile == "frog-robo":
        active_party = "060403"
        pre_magic = 0x47
        robo = 0
        pre_counts = "08080808000808"
        pre_masks = "ffffffff1fffff"
        post_counts = "08080808030808"
        post_dialog = 0
    else:
        active_party = "000102"
        pre_magic = 0x18
        robo = 0
        pre_counts = "00000008080808"
        pre_masks = "1f1f1fffffffff"
        post_counts = "03030308080808"
        post_dialog = 2

    common = {
        "location": 0x01D1,
        "lap_scratch": 3,
        "robo_flags": robo,
        "dialog_state": 0,
        "active_party_hex": active_party,
        "candidate_matches_variant": True,
        "front_guard_hex": "00000000",
        "rear_guard_hex": "00000000000000000000000000000000",
        "epoch_name_hex": "a4c9c8bcc100",
    }
    pre = {
        **common,
        "storyline": 0x4C,
        "magic_flags": pre_magic,
        "explore_mode": 1,
        "leader_x": 1568,
        "leader_y": 2623,
        "tech_counts_hex": pre_counts,
        "learned_masks_hex": pre_masks,
    }
    post = {
        **common,
        "storyline": 0x4D,
        "magic_flags": 0x5F,
        "explore_mode": 0,
        "dialog_state": post_dialog,
        "leader_x": 1925,
        "leader_y": 3061,
        "tech_counts_hex": post_counts,
        "learned_masks_hex": "ffffffffffffff",
    }
    return pre, post


def callback(
    seq: int,
    frame: int,
    access: str,
    address: int,
    value: int,
) -> dict[str, object]:
    return {
        "seq": seq,
        "frame": frame,
        "absolute_frame": 3237 + frame,
        "access": access,
        "address": address,
        "raw_wram_offset": address - 0x7E0000,
        "value": value,
        "pc24": 0xC06797 if access == "read" else 0xC06822,
    }


def callbacks(profile: str) -> list[dict[str, object]]:
    if profile == "frog-robo":
        rows = (
            (985, "write", 0x7E2834, 3),
            (989, "read", 0x7E283B, 0x1F),
            (989, "write", 0x7E283B, 0xFF),
        )
    else:
        rows = (
            (793, "write", 0x7E2830, 3),
            (793, "read", 0x7E2837, 0x1F),
            (793, "write", 0x7E2837, 0xFF),
            (1086, "write", 0x7E2831, 3),
            (1090, "read", 0x7E2838, 0x1F),
            (1090, "write", 0x7E2838, 0xFF),
            (1875, "write", 0x7E2832, 3),
            (1879, "read", 0x7E2839, 0x1F),
            (1879, "write", 0x7E2839, 0xFF),
        )
    return [
        callback(seq, frame, access, address, value)
        for seq, (frame, access, address, value) in enumerate(rows)
    ]


def make_trace(profile: str, variant: str) -> dict[str, object]:
    pre, post = snapshots(profile)
    return {
        "schema": "project-epoch-mesen-event11c-access-trace-v1",
        "collector_version": 2,
        "profile": profile,
        "variant": variant,
        "observer": observer(),
        "pre": pre,
        "callbacks": callbacks(profile),
        "post": post,
        "termination": {
            "collector_stopped": True,
            "success": True,
            "overflow": False,
            "observer_error": None,
            "unexpected_accesses": 0,
        },
    }


def make_trace_set() -> list[dict[str, object]]:
    return [
        make_trace(profile, variant)
        for profile in ("frog-robo", "crono-marle-lucca")
        for variant in ("zero", "canary")
    ]


class MesenEvent11CTraceTests(unittest.TestCase):
    def test_source_acceptance_spec_is_bounded_and_pins_tools(self) -> None:
        source = json.loads(ACCEPTANCE_SPEC_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            source["schema"],
            "project-epoch-mesen-event11c-acceptance-v1",
        )
        for tool_name in ("collector", "validator", "launcher"):
            contract = source[tool_name]
            tool_path = ROOT / contract["path"]
            tool_bytes = tool_path.read_bytes()
            self.assertEqual(len(tool_bytes), contract["size"])
            self.assertEqual(
                hashlib.sha256(tool_bytes).hexdigest(),
                contract["sha256"],
            )

        artifacts = source["artifacts"]
        self.assertEqual(len(artifacts), 8)
        paths = [entry["path"] for entry in artifacts]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(
            {
                pathlib.PurePosixPath(path).parent.as_posix()
                for path in paths
            },
            {
                "frog-robo/zero",
                "frog-robo/canary",
                "crono-marle-lucca/zero",
                "crono-marle-lucca/canary",
            },
        )
        for entry in artifacts:
            relative = pathlib.PurePosixPath(entry["path"])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            self.assertNotIn(
                relative.suffix.lower(),
                {".sfc", ".smc", ".srm", ".mss", ".state"},
            )
            self.assertEqual(entry["evidence_level"], "verified-runtime")
            self.assertEqual(entry["reproduction_group"], "mesen-trace")
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(entry["size"], 0)

    def test_accepts_exact_four_trace_contract(self) -> None:
        report = TOOL.validate_trace_documents(make_trace_set())
        self.assertEqual(report["trace_count"], 4)
        self.assertTrue(report["zero_canary_callbacks_identical"])

    def test_loads_only_unique_json_files_below_private(self) -> None:
        private_root = ROOT / "private"
        private_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_root) as directory:
            run_root = pathlib.Path(directory)
            paths = []
            for index, trace in enumerate(make_trace_set()):
                path = run_root / f"trace-{index}.json"
                path.write_text(json.dumps(trace), encoding="utf-8")
                paths.append(path)
            report = TOOL.validate_trace_files(paths)
            self.assertEqual(report["status"], "accepted-private-diagnostic-trace-set")

            with self.assertRaisesRegex(
                TOOL.TraceValidationError,
                "paths must be unique",
            ):
                TOOL.validate_trace_files([paths[0]] * 4)

    def test_rejects_path_outside_private_before_reading(self) -> None:
        outside = ROOT / "references" / "not-a-trace.json"
        with self.assertRaisesRegex(TOOL.TraceValidationError, "private/"):
            TOOL.validate_private_trace_path(outside)

    def test_rejects_duplicate_json_keys(self) -> None:
        private_root = ROOT / "private"
        private_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_root) as directory:
            path = pathlib.Path(directory) / "duplicate.json"
            path.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            with self.assertRaisesRegex(
                TOOL.TraceValidationError,
                "duplicate JSON key",
            ):
                TOOL.load_private_trace(path)

    def test_rejects_schema_version_or_unknown_fields(self) -> None:
        cases = []
        wrong_schema = make_trace("frog-robo", "zero")
        wrong_schema["schema"] = "untrusted"
        cases.append(wrong_schema)
        wrong_version = make_trace("frog-robo", "zero")
        wrong_version["collector_version"] = 1
        cases.append(wrong_version)
        extra = make_trace("frog-robo", "zero")
        extra["source_rom"] = "forbidden.sfc"
        cases.append(extra)

        for trace in cases:
            with self.subTest(trace=trace):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_callback_pc_address_value_or_sequence(self) -> None:
        for field, replacement in (
            ("pc24", 0xC06798),
            ("address", 0x7E283A),
            ("value", 0x20),
            ("seq", 1),
        ):
            trace = make_trace("frog-robo", "zero")
            trace["callbacks"][0][field] = replacement
            with self.subTest(field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_preservation_or_failed_termination(self) -> None:
        mutations = (
            ("pre", "candidate_matches_variant", False),
            ("post", "front_guard_hex", "01000000"),
            ("post", "rear_guard_hex", "00" * 15 + "01"),
            ("post", "epoch_name_hex", "000000000000"),
            ("termination", "success", False),
            ("termination", "overflow", True),
            ("termination", "observer_error", "callback failed"),
            ("termination", "unexpected_accesses", 1),
        )
        for section, field, replacement in mutations:
            trace = make_trace("frog-robo", "zero")
            trace[section][field] = replacement
            with self.subTest(section=section, field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_callback_timing_drift(self) -> None:
        traces = make_trace_set()
        canary = next(
            trace
            for trace in traces
            if trace["profile"] == "frog-robo"
            and trace["variant"] == "canary"
        )
        canary["callbacks"][0]["frame"] += 1
        canary["callbacks"][0]["absolute_frame"] += 1
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            r"\.frame must be",
        ):
            TOOL.validate_trace_documents(traces)

    def test_rejects_duplicate_profile_variant_combination(self) -> None:
        traces = copy.deepcopy(make_trace_set())
        traces[-1]["variant"] = "zero"
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "duplicate trace combination",
        ):
            TOOL.validate_trace_documents(traces)


if __name__ == "__main__":
    unittest.main()
