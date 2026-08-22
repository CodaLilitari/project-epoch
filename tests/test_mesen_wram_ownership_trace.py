from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from collections import Counter


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_mesen_wram_ownership_trace.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("validate_mesen_wram_ownership_trace", TOOL_PATH)

OLD_BASE = bytes((index * 37 + 11) & 0xFF for index in range(0x50))
ROSTER = bytes.fromhex("060403868184020580")
JOINED = bytes.fromhex("fe")
EPOCH = bytes.fromhex("a4c9c8bcc100")


def expected_candidate(variant: str) -> bytes:
    return (
        bytes(0x50)
        if variant == "zero"
        else bytes(TOOL.CANDIDATE_CANARY)
    )


def pre_ranges(scenario: str, variant: str) -> dict[str, bytes]:
    old = bytearray(OLD_BASE)
    if scenario == "event11c-frog":
        old[0x04] = 0
        old[0x0B] = 0x1F
    return {
        "old-compatibility": bytes(old),
        "roster": ROSTER,
        "joined": JOINED,
        "epoch-name": EPOCH,
        "front-guard": bytes(0x04),
        "candidate": expected_candidate(variant),
        "rear-guard": bytes(0x10),
    }


def callback_rows(
    scenario: str,
    ranges: dict[str, bytes],
) -> list[dict[str, object]]:
    if scenario == "calibration":
        rows: list[tuple[int, str, int, int, int]] = []
    elif scenario == "field-idle":
        rows = [
            (100, "read", 0x7E2830, ranges["old-compatibility"][0], 0xC01234),
            (200, "read", 0x7E2C4D, ranges["epoch-name"][0], 0xC05678),
            (300, "read", 0x7E2980, ranges["roster"][0], 0xC089AB),
            (400, "read", 0x7E29AF, ranges["joined"][0], 0xC0ABCD),
        ]
    elif scenario == "main-menu":
        rows = [
            (80, "read", 0x7E2980, ranges["roster"][0], 0xC28CCF),
            (100, "read", 0x7E29AF, ranges["joined"][0], 0xC28D10),
            (120, "read", 0x7E2C4D, ranges["epoch-name"][0], 0xC25A00),
            (180, "read", 0x7E2830, ranges["old-compatibility"][0], 0xC2B452),
        ]
    else:
        rows = [
            # Noise through the same absolute-read handler proves the
            # positive-control filter is target-identity-specific, not PC-only.
            (500, "read", 0x7E2980, ranges["roster"][0], 0xC06799),
            (800, "read", 0x7E2830, ranges["old-compatibility"][0], 0xC01234),
            (985, "write", 0x7E2834, 0x03, 0xC06824),
            (989, "read", 0x7E283B, 0x1F, 0xC06799),
            (989, "write", 0x7E283B, 0xFF, 0xC06824),
            (1100, "read", 0x7E2C4D, ranges["epoch-name"][0], 0xC05678),
        ]
    return [
        {
            "seq": seq,
            "frame": frame,
            "access": access,
            "address": address,
            "value": value,
            "pc24": pc24,
        }
        for seq, (frame, access, address, value, pc24) in enumerate(rows)
    ]


def post_ranges(
    before: dict[str, bytes],
    callbacks: list[dict[str, object]],
) -> dict[str, bytes]:
    result = {name: bytearray(value) for name, value in before.items()}
    for callback in callbacks:
        if callback["access"] != "write":
            continue
        address = int(callback["address"])
        range_name = TOOL.ADDRESS_RANGE_NAME[address]
        watched_range = next(
            item
            for item in TOOL.WATCHED_RANGES
            if item["name"] == range_name
        )
        result[range_name][address - watched_range["start_address"]] = int(
            callback["value"]
        )
    return {name: bytes(value) for name, value in result.items()}


def snapshot(ranges: dict[str, bytes]) -> dict[str, object]:
    return {
        TOOL.SNAPSHOT_FIELD_BY_RANGE[watched_range["name"]]: ranges[
            watched_range["name"]
        ].hex()
        for watched_range in TOOL.WATCHED_RANGES
    }


def counters(
    callbacks: list[dict[str, object]],
) -> list[dict[str, object]]:
    observed = Counter(
        (callback["address"], callback["access"]) for callback in callbacks
    )
    return [
        {
            "address": address,
            "read_count": observed[(address, "read")],
            "write_count": observed[(address, "write")],
        }
        for address in TOOL.WATCHED_ADDRESSES
    ]


def make_trace(scenario: str, variant: str) -> dict[str, object]:
    before = pre_ranges(scenario, variant)
    callbacks = callback_rows(scenario, before)
    after = post_ranges(before, callbacks)
    contract = TOOL.SCENARIO_CONTRACTS[scenario]
    terminal_frame = contract["terminal_frame_min"]
    return {
        "schema": "project-epoch-mesen-wram-ownership-trace-v1",
        "collector_version": 1,
        "scenario": scenario,
        "variant": variant,
        "collector_explicit_write_scope": (
            "snes-work-ram-preparation-before-counters-arm-only"
        ),
        "checkpoint": {
            "id": "event11c-checkpoint-v5-spekkio-talkable",
            "state_size": 133_993,
            "state_sha256": (
                "26788b52f63a32a7539d8acb18495df"
                "1a458064f700d5411916e2bfc34c4522e"
            ),
            "source_frame": 3237,
            "direct_page": 0x0100,
            "location": 0x01D1,
        },
        "scenario_contract": {
            "terminal_frame_min": contract["terminal_frame_min"],
            "terminal_frame_max": contract["terminal_frame_max"],
            "expected_access_class": contract["expected_access_class"],
            "inputs": [copy.deepcopy(row) for row in contract["inputs"]],
        },
        "observer": {
            "mechanism": "snes-work-ram-read-write-memory-callbacks",
            "memory_type": "snes-work-ram",
            "counter_granularity": "byte-address-and-access",
            "callback_limit": 4096,
            "counters_cover_every_watched_byte": True,
        },
        "watched_ranges": [
            copy.deepcopy(watched_range)
            for watched_range in TOOL.WATCHED_RANGES
        ],
        "preparation": {
            "completed_before_counters_armed": True,
            "counters_zero_after_preparation": True,
            "writes": copy.deepcopy(
                TOOL._expected_preparation_writes(scenario, variant)
            ),
        },
        "pre": snapshot(before),
        "callbacks": callbacks,
        "counters": counters(callbacks),
        "post": snapshot(after),
        "termination": {
            "collector_stopped": True,
            "success": True,
            "overflow": False,
            "observer_error": None,
            "counters_armed": True,
            "preparation_writes_after_arm": 0,
            "terminal_frame": terminal_frame,
            "unexpected_accesses": 0,
        },
    }


def make_trace_set() -> list[dict[str, object]]:
    return [
        make_trace(scenario, variant)
        for scenario in (
            "calibration",
            "field-idle",
            "main-menu",
            "event11c-frog",
        )
        for variant in ("zero", "canary")
    ]


def find_trace(
    traces: list[dict[str, object]],
    scenario: str,
    variant: str,
) -> dict[str, object]:
    return next(
        trace
        for trace in traces
        if trace["scenario"] == scenario and trace["variant"] == variant
    )


class MesenWramOwnershipTraceTests(unittest.TestCase):
    def test_accepts_exact_eight_trace_contract(self) -> None:
        report = TOOL.validate_trace_documents(make_trace_set())
        self.assertEqual(report["trace_count"], 8)
        self.assertEqual(report["watched_byte_count"], 196)
        self.assertTrue(report["counter_callback_reconciliation"])
        self.assertTrue(report["zero_canary_observations_identical"])

    def test_schema_intentionally_has_no_screenshot_field(self) -> None:
        trace = make_trace("calibration", "zero")
        trace["screenshot_sha256"] = "0" * 64
        with self.assertRaisesRegex(TOOL.TraceValidationError, "extra"):
            TOOL.validate_trace_document(trace)

    def test_rejects_missing_scenario_and_duplicate_combination(self) -> None:
        traces = make_trace_set()[:-1]
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "exactly eight",
        ):
            TOOL.validate_trace_documents(traces)

        traces = make_trace_set()
        traces[-1] = copy.deepcopy(traces[-2])
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "duplicate trace combination",
        ):
            TOOL.validate_trace_documents(traces)

    def test_rejects_unknown_or_missing_fields(self) -> None:
        trace = make_trace("field-idle", "zero")
        trace["observer"]["untrusted"] = True
        with self.assertRaisesRegex(TOOL.TraceValidationError, "extra"):
            TOOL.validate_trace_document(trace)

        trace = make_trace("field-idle", "zero")
        del trace["checkpoint"]["state_size"]
        with self.assertRaisesRegex(TOOL.TraceValidationError, "missing"):
            TOOL.validate_trace_document(trace)

    def test_rejects_bool_as_int(self) -> None:
        trace = make_trace("calibration", "zero")
        trace["collector_version"] = True
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

        trace = make_trace("field-idle", "zero")
        trace["counters"][0]["read_count"] = True
        with self.assertRaisesRegex(TOOL.TraceValidationError, "integer"):
            TOOL.validate_trace_document(trace)

    def test_loader_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "trace.json"
            path.write_text(
                '{"schema":"one","schema":"two"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                TOOL.TraceValidationError,
                "duplicate JSON key",
            ):
                TOOL.load_trace(path)

    def test_rejects_access_mismatch(self) -> None:
        trace = make_trace("event11c-frog", "zero")
        trace["callbacks"][2]["access"] = "read"
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "event-PC access sequence mismatch",
        ):
            TOOL.validate_trace_document(trace)

    def test_rejects_unaccounted_or_reordered_counters(self) -> None:
        trace = make_trace("field-idle", "zero")
        unused = next(
            row
            for row in trace["counters"]
            if row["read_count"] == 0 and row["write_count"] == 0
        )
        unused["write_count"] = 1
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "does not reconcile callbacks",
        ):
            TOOL.validate_trace_document(trace)

        trace = make_trace("field-idle", "zero")
        trace["counters"][0], trace["counters"][1] = (
            trace["counters"][1],
            trace["counters"][0],
        )
        with self.assertRaisesRegex(TOOL.TraceValidationError, "address"):
            TOOL.validate_trace_document(trace)

    def test_rejects_candidate_or_guard_access(self) -> None:
        for address, value in (
            (0x7E2CA0, 0),
            (0x7E2C9C, 0),
            (0x7E2CF0, 0),
        ):
            trace = make_trace("field-idle", "zero")
            trace["callbacks"].append(
                {
                    "seq": len(trace["callbacks"]),
                    "frame": 500,
                    "access": "read",
                    "address": address,
                    "value": value,
                    "pc24": 0xC01234,
                }
            )
            trace["counters"] = counters(trace["callbacks"])
            with self.subTest(address=address):
                with self.assertRaisesRegex(
                    TOOL.TraceValidationError,
                    "illegally accesses",
                ):
                    TOOL.validate_trace_document(trace)

    def test_rejects_epoch_roster_or_joined_write(self) -> None:
        for address, value in (
            (0x7E2C4D, EPOCH[0]),
            (0x7E2980, ROSTER[0]),
            (0x7E29AF, JOINED[0]),
        ):
            trace = make_trace("field-idle", "zero")
            trace["callbacks"].append(
                {
                    "seq": len(trace["callbacks"]),
                    "frame": 500,
                    "access": "write",
                    "address": address,
                    "value": value,
                    "pc24": 0xC01234,
                }
            )
            trace["counters"] = counters(trace["callbacks"])
            with self.subTest(address=address):
                with self.assertRaisesRegex(
                    TOOL.TraceValidationError,
                    "illegally writes",
                ):
                    TOOL.validate_trace_document(trace)

    def test_rejects_old_compatibility_write_outside_event(self) -> None:
        trace = make_trace("field-idle", "zero")
        trace["callbacks"].append(
            {
                "seq": len(trace["callbacks"]),
                "frame": 500,
                "access": "write",
                "address": 0x7E2830,
                "value": OLD_BASE[0],
                "pc24": 0xC01234,
            }
        )
        trace["counters"] = counters(trace["callbacks"])
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "unapproved old-compatibility write",
        ):
            TOOL.validate_trace_document(trace)

    def test_allows_measured_event_old_compatibility_write(self) -> None:
        trace = make_trace("event11c-frog", "zero")
        trace["callbacks"].insert(
            2,
            {
                "seq": 2,
                "frame": 900,
                "access": "write",
                "address": 0x7E2830,
                "value": OLD_BASE[0],
                "pc24": 0xC01234,
            },
        )
        for seq, callback in enumerate(trace["callbacks"]):
            callback["seq"] = seq
        trace["counters"] = counters(trace["callbacks"])
        TOOL.validate_trace_document(trace)

        trace["callbacks"][2]["value"] ^= 1
        trace["counters"] = counters(trace["callbacks"])
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "non-target event old-compatibility write is not same-value",
        ):
            TOOL.validate_trace_document(trace)

    def test_rejects_checkpoint_range_or_endpoint_drift(self) -> None:
        trace = make_trace("field-idle", "zero")
        trace["checkpoint"]["state_sha256"] = "0" * 64
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

        trace = make_trace("field-idle", "zero")
        trace["watched_ranges"][5]["start_address"] = 0x7E2CA1
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

        trace = make_trace("field-idle", "zero")
        old = bytearray.fromhex(trace["post"]["old_compatibility_hex"])
        old[20] ^= 1
        trace["post"]["old_compatibility_hex"] = old.hex()
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "does not reconcile callbacks",
        ):
            TOOL.validate_trace_document(trace)

    def test_rejects_event_order_value_or_pc_changes(self) -> None:
        trace = make_trace("event11c-frog", "zero")
        trace["callbacks"][3], trace["callbacks"][4] = (
            trace["callbacks"][4],
            trace["callbacks"][3],
        )
        trace["callbacks"][3]["seq"] = 3
        trace["callbacks"][4]["seq"] = 4
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

        trace = make_trace("event11c-frog", "zero")
        trace["callbacks"][2]["value"] = 4
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "old-compatibility write|event-PC access sequence mismatch",
        ):
            TOOL.validate_trace_document(trace)

        trace = make_trace("event11c-frog", "zero")
        trace["callbacks"][2]["pc24"] = 0xC06821
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "old-compatibility write|event-PC access sequence mismatch",
        ):
            TOOL.validate_trace_document(trace)

    def test_rejects_preparation_drift_or_post_arm_write(self) -> None:
        trace = make_trace("event11c-frog", "zero")
        trace["preparation"]["writes"][0]["value"] = 0x4D
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

        trace = make_trace("field-idle", "zero")
        trace["termination"]["preparation_writes_after_arm"] = 1
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

    def test_rejects_pair_observation_or_endpoint_divergence(self) -> None:
        traces = make_trace_set()
        canary = find_trace(traces, "field-idle", "canary")
        canary["callbacks"][0]["pc24"] = 0xC01235
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "zero/canary callbacks differ",
        ):
            TOOL.validate_trace_documents(traces)

        traces = make_trace_set()
        canary = find_trace(traces, "calibration", "canary")
        canary["pre"]["joined_hex"] = "fc"
        canary["post"]["joined_hex"] = "fc"
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "endpoints differ outside candidate",
        ):
            TOOL.validate_trace_documents(traces)

    def test_rejects_calibration_access(self) -> None:
        trace = make_trace("calibration", "zero")
        trace["callbacks"] = [
            {
                "seq": 0,
                "frame": 0,
                "access": "read",
                "address": 0x7E2830,
                "value": OLD_BASE[0],
                "pc24": 0xC01234,
            }
        ]
        trace["counters"] = counters(trace["callbacks"])
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "calibration must have zero",
        ):
            TOOL.validate_trace_document(trace)


if __name__ == "__main__":
    unittest.main()
