from __future__ import annotations

import copy
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_menu_trace_v2.py"
)
V1_HELPER_PATH = ROOT / "tests" / "test_mesen_wram_ownership_trace.py"


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


V1_HELPER = load_module(
    "test_mesen_wram_ownership_trace_helper_for_menu_v2",
    V1_HELPER_PATH,
)
TOOL = load_module(
    "validate_mesen_wram_ownership_menu_trace_v2_test",
    TOOL_PATH,
)


def make_trace(scenario: str, variant: str) -> dict[str, object]:
    trace = V1_HELPER.make_trace("main-menu", variant)
    contract = TOOL.SCENARIO_CONTRACTS[scenario]
    trace["schema"] = TOOL.SCHEMA
    trace["collector_version"] = TOOL.COLLECTOR_VERSION
    trace["scenario"] = scenario
    trace["scenario_contract"] = {
        "terminal_frame_min": contract["terminal_frame_min"],
        "terminal_frame_max": contract["terminal_frame_max"],
        "expected_access_class": contract["expected_access_class"],
        "inputs": [copy.deepcopy(row) for row in contract["inputs"]],
    }
    trace["termination"]["terminal_frame"] = 600
    if scenario == "tech-owner-switch":
        for phase in ("pre", "post"):
            old = bytearray.fromhex(
                trace[phase]["old_compatibility_hex"]
            )
            for address in range(0x7E2857, 0x7E285C):
                old[address - 0x7E2830] = 0
            trace[phase]["old_compatibility_hex"] = old.hex()

        callbacks = trace["callbacks"]
        writes = {
            row[0]: row for row in TOOL.TECH_OWNER_SWITCH_WRITES
        }
        while len(callbacks) <= max(writes):
            seq = len(callbacks)
            if seq in writes:
                _, frame, address, value, pc24 = writes[seq]
                access = "write"
            else:
                frame = 220 if seq < min(writes) else 221
                access = "read"
                address = 0x7E2830
                value = V1_HELPER.OLD_BASE[0]
                pc24 = 0xC01234
            callbacks.append(
                {
                    "seq": seq,
                    "frame": frame,
                    "access": access,
                    "address": address,
                    "value": value,
                    "pc24": pc24,
                }
            )
        trace["counters"] = V1_HELPER.counters(callbacks)
    return trace


def make_trace_set() -> list[dict[str, object]]:
    return [
        make_trace(scenario, variant)
        for scenario in TOOL.SCENARIO_NAMES
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


def append_callback(
    trace: dict[str, object],
    *,
    access: str,
    address: int,
    value: int,
) -> None:
    callbacks = trace["callbacks"]
    assert isinstance(callbacks, list)
    callbacks.append(
        {
            "seq": len(callbacks),
            "frame": 500,
            "access": access,
            "address": address,
            "value": value,
            "pc24": 0xC01234,
        }
    )
    trace["counters"] = V1_HELPER.counters(callbacks)


class MesenWramOwnershipMenuTraceV2Tests(unittest.TestCase):
    def test_accepts_each_synthetic_document_and_exact_eight_set(self) -> None:
        traces = make_trace_set()
        for trace in traces:
            with self.subTest(
                scenario=trace["scenario"],
                variant=trace["variant"],
            ):
                self.assertEqual(
                    TOOL.validate_trace_document(trace),
                    (trace["scenario"], trace["variant"]),
                )

        report = TOOL.validate_trace_documents(traces)
        self.assertEqual(report["schema"], TOOL.SCHEMA)
        self.assertEqual(
            report["collector_version"],
            TOOL.COLLECTOR_VERSION,
        )
        self.assertEqual(
            report["status"],
            "valid-private-menu-ownership-trace-set-v2",
        )
        self.assertEqual(report["trace_count"], 8)
        self.assertEqual(report["watched_byte_count"], 196)
        self.assertTrue(report["candidate_and_guards_zero_access"])
        self.assertTrue(report["counter_callback_reconciliation"])
        self.assertTrue(report["zero_canary_observations_identical"])

    def test_rejects_v1_schema_and_collector_version(self) -> None:
        trace = make_trace("equipment-owner-switch", "zero")
        trace["schema"] = "project-epoch-mesen-wram-ownership-trace-v1"
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

        trace = make_trace("equipment-owner-switch", "zero")
        trace["collector_version"] = 1
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

    def test_rejects_candidate_and_guard_access(self) -> None:
        for address in (0x7E2C9C, 0x7E2CA0, 0x7E2CF0):
            trace = make_trace("item-list-cancel", "zero")
            append_callback(
                trace,
                access="read",
                address=address,
                value=0,
            )
            with self.subTest(address=f"{address:06X}"):
                with self.assertRaisesRegex(
                    TOOL.TraceValidationError,
                    "illegally accesses",
                ):
                    TOOL.validate_trace_document(trace)

    def test_rejects_epoch_roster_and_joined_writes(self) -> None:
        protected = (
            (0x7E2C4D, V1_HELPER.EPOCH[0]),
            (0x7E2980, V1_HELPER.ROSTER[0]),
            (0x7E29AF, V1_HELPER.JOINED[0]),
        )
        for address, value in protected:
            trace = make_trace("party-page-cancel", "zero")
            append_callback(
                trace,
                access="write",
                address=address,
                value=value,
            )
            with self.subTest(address=f"{address:06X}"):
                with self.assertRaisesRegex(
                    TOOL.TraceValidationError,
                    "illegally writes",
                ):
                    TOOL.validate_trace_document(trace)

    def test_rejects_unapproved_old_block_write_and_counter_drift(
        self,
    ) -> None:
        trace = make_trace("item-list-cancel", "zero")
        append_callback(
            trace,
            access="write",
            address=0x7E2830,
            value=V1_HELPER.OLD_BASE[0],
        )
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "old-compatibility",
        ):
            TOOL.validate_trace_document(trace)

        trace = make_trace("item-list-cancel", "zero")
        trace["counters"][0]["read_count"] += 1
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "does not reconcile callbacks",
        ):
            TOOL.validate_trace_document(trace)

    def test_rejects_scenario_timeline_drift(self) -> None:
        trace = make_trace("tech-owner-switch", "zero")
        trace["scenario_contract"]["inputs"][1]["start_frame"] = 121
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

    def test_exact_set_rejects_missing_duplicate_and_pair_divergence(
        self,
    ) -> None:
        traces = make_trace_set()
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "exactly eight",
        ):
            TOOL.validate_trace_documents(traces[:-1])

        traces = make_trace_set()
        traces[-1] = copy.deepcopy(traces[-2])
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "duplicate trace combination",
        ):
            TOOL.validate_trace_documents(traces)

        traces = make_trace_set()
        canary = find_trace(
            traces,
            "equipment-owner-switch",
            "canary",
        )
        canary["callbacks"][0]["pc24"] ^= 1
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "zero/canary callbacks differ",
        ):
            TOOL.validate_trace_documents(traces)

        traces = make_trace_set()
        canary = find_trace(traces, "party-page-cancel", "canary")
        for phase in ("pre", "post"):
            roster = bytearray.fromhex(
                canary[phase]["roster_hex"]
            )
            roster[1] ^= 1
            canary[phase]["roster_hex"] = roster.hex()
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "endpoints differ outside candidate",
        ):
            TOOL.validate_trace_documents(traces)


if __name__ == "__main__":
    unittest.main()
