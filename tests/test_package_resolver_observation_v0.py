"""Synthetic metadata checks for the checkpoint observer's evidence summary.

These fixtures are authored from the stated ABI and return contract. They
contain no ROM bytes, saved-state content, or copied runtime observations,
and these tests never launch Mesen or resolve any private game input.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_package_resolver_observation_v0 as tool


def synthetic_trace(*, selector=0x12, branch=0, actor=1, stack_pointer=0x1200):
    """One independent, minimal resolver/return witness with arbitrary data."""
    return {
        "schema": tool.SCHEMA,
        "error": None,
        "records": [
            {"kind": "baseline"},
            {
                "kind": "resolver-entry",
                "cpu": {
                    "d": 0,
                    "dbr": 0x7E,
                    "sp": stack_pointer,
                    "ps": 0x04,
                    "emulationMode": False,
                },
                "stack": [0x2A, 0x43, 0xAF, 0x40, 0x91, 0x82, 0x73, 0x64],
                "selector_word": selector,
                "branch_word": branch,
                "wram": {"AE91": actor, "AE92": 2},
            },
            {"kind": "resolver-tail", "cpu": {"sp": stack_pointer, "ps": 0x23}},
            {"kind": "common-loader-entry", "cpu": {"sp": stack_pointer, "ps": 0x20}},
            {"kind": "common-loader-rts", "cpu": {"sp": stack_pointer, "ps": 0xA4}},
            {"kind": "dispatcher-rts", "cpu": {"sp": (stack_pointer + 2) & 0xFFFF, "ps": 0x21}},
            {"kind": "caller-resume", "cpu": {"sp": (stack_pointer + 4) & 0xFFFF, "ps": 0x24}},
            {"kind": "terminal"},
        ],
    }


class ResolverObservationSummaryTests(unittest.TestCase):
    def test_invalid_schema_or_collector_error_is_rejected(self):
        for changes in ({"schema": "unrelated-trace"}, {"schema": None},
                        {"error": "collector stopped before completion"}):
            with self.subTest(changes=changes):
                trace = synthetic_trace()
                trace.update(changes)
                with self.assertRaises(tool.ObservationError):
                    tool.summarize(trace)

    def test_record_container_and_bounds_are_enforced(self):
        for records in (None, {}, [], [{"kind": "baseline"}],
                        [{"kind": "baseline"}] * 4097):
            with self.subTest(record_type=type(records),
                              count=len(records) if records is not None else None):
                trace = synthetic_trace()
                trace["records"] = records
                with self.assertRaises(tool.ObservationError):
                    tool.summarize(trace)

    def test_missing_or_displaced_baseline_and_terminal_are_rejected(self):
        for index, replacement in ((0, {"kind": "menu-observation"}),
                                   (-1, {"kind": "caller-resume"})):
            with self.subTest(index=index):
                trace = synthetic_trace()
                trace["records"][index] = replacement
                with self.assertRaises(tool.ObservationError):
                    tool.summarize(trace)

    def test_no_resolver_cannot_claim_entry_or_return_conformance(self):
        trace = synthetic_trace()
        trace["records"] = [{"kind": "baseline"}, {"kind": "terminal"}]
        result = tool.summarize(trace)
        self.assertFalse(result["resolver_observed"])
        self.assertEqual(result["resolver_invocations"], 0)
        self.assertFalse(result["entry_abi_matches_static_contract"])
        self.assertFalse(result["paired_return_chain_matches_static_contract"])
        self.assertFalse(result["paired_pc_action_completion_observed"])
        self.assertFalse(result["all_entry_return_frames_match"])
        self.assertEqual(result["observed_branch_words"], [])
        self.assertEqual(result["entry_stack_pointers"], [])

    def test_expected_primary_and_alternate_chains_pass(self):
        for branch in (0, 0x40):
            for actor, selector in ((0, 0), (1, 0x12), (2, 0x7F)):
                with self.subTest(branch=branch, actor=actor, selector=selector):
                    result = tool.summarize(synthetic_trace(
                        actor=actor, selector=selector, branch=branch))
                    self.assertTrue(result["resolver_observed"])
                    self.assertTrue(result["entry_abi_matches_static_contract"])
                    self.assertTrue(result["paired_return_chain_matches_static_contract"])
                    self.assertTrue(result["all_entry_return_frames_match"])
                    self.assertEqual(result["resolver_invocations"], 1)
                    self.assertEqual(result["observed_branch_words"], [branch])
                    self.assertEqual(result["entry_stack_pointers"], [0x1200])
                    self.assertEqual(result["event_counts"]["resolver-entry"], 1)

    def test_enemy_actor_or_non_player_tech_type_fails_entry_contract(self):
        for key, values in (("AE91", (3, 7, 0xFF)), ("AE92", (0, 1, 3, 0xFF))):
            for value in values:
                with self.subTest(key=key, value=value):
                    trace = synthetic_trace()
                    trace["records"][1]["wram"][key] = value
                    self.assertFalse(tool.summarize(trace)["entry_abi_matches_static_contract"])

    def test_invalid_direct_page_bank_mode_or_width_fails_entry_contract(self):
        mutations = (("d", 1), ("d", 0x100), ("dbr", 0), ("dbr", 0x7F),
                     ("emulationMode", True), ("ps", 0x10), ("ps", 0x20), ("ps", 0x30))
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                trace = synthetic_trace()
                trace["records"][1]["cpu"][key] = value
                self.assertFalse(tool.summarize(trace)["entry_abi_matches_static_contract"])

    def test_each_return_address_byte_and_truncation_fails_entry_frame_check(self):
        for index in range(4):
            with self.subTest(index=index):
                trace = synthetic_trace()
                trace["records"][1]["stack"][index] ^= 1
                result = tool.summarize(trace)
                self.assertFalse(result["entry_abi_matches_static_contract"])
                self.assertFalse(result["all_entry_return_frames_match"])
        trace = synthetic_trace()
        trace["records"][1]["stack"] = [0x2A, 0x43, 0xAF]
        self.assertFalse(tool.summarize(trace)["all_entry_return_frames_match"])

    def test_high_selectors_and_unproved_branch_words_fail_entry_contract(self):
        for key, values in (("selector_word", (0x80, 0xFF, 0x100, 0xFFFF)),
                            ("branch_word", (1, 0x41, 0x80, 0x100, 0xFFFF))):
            for value in values:
                with self.subTest(key=key, value=value):
                    trace = synthetic_trace()
                    trace["records"][1][key] = value
                    self.assertFalse(tool.summarize(trace)["entry_abi_matches_static_contract"])

    def test_each_missing_return_stage_prevents_complete_chain(self):
        for index in range(2, 7):
            trace = synthetic_trace()
            with self.subTest(missing=trace["records"][index]["kind"]):
                del trace["records"][index]
                result = tool.summarize(trace)
                self.assertTrue(result["entry_abi_matches_static_contract"])
                self.assertFalse(result["paired_return_chain_matches_static_contract"])

    def test_wrong_stack_pointer_at_any_return_stage_fails_chain(self):
        for index in range(2, 7):
            trace = synthetic_trace()
            with self.subTest(stage=trace["records"][index]["kind"]):
                trace["records"][index]["cpu"]["sp"] += 1
                self.assertFalse(tool.summarize(trace)["paired_return_chain_matches_static_contract"])

    def test_wrong_processor_width_at_any_return_stage_fails_chain(self):
        for index in range(2, 7):
            for status in (0x00, 0x10, 0x30):
                trace = synthetic_trace()
                with self.subTest(stage=trace["records"][index]["kind"], status=status):
                    trace["records"][index]["cpu"]["ps"] = status
                    self.assertFalse(tool.summarize(trace)["paired_return_chain_matches_static_contract"])

    def test_out_of_order_return_stages_cannot_form_valid_chain(self):
        for first in range(2, 6):
            with self.subTest(swapped_index=first):
                trace = synthetic_trace()
                records = trace["records"]
                records[first], records[first + 1] = records[first + 1], records[first]
                self.assertFalse(tool.summarize(trace)["paired_return_chain_matches_static_contract"])

    def test_incomplete_invocation_cannot_borrow_next_invocations_return_chain(self):
        trace = synthetic_trace()
        # The first invocation reaches only its tail before a new invocation.
        first_prefix = trace["records"][:3]
        next_invocation = copy.deepcopy(synthetic_trace(stack_pointer=0x1300)["records"][1:])
        trace["records"] = first_prefix + next_invocation
        result = tool.summarize(trace)
        self.assertEqual(result["resolver_invocations"], 2)
        self.assertTrue(result["entry_abi_matches_static_contract"])
        self.assertFalse(result["paired_return_chain_matches_static_contract"])

    def test_all_invocations_must_pass_while_unrelated_observations_are_allowed(self):
        trace = synthetic_trace()
        second = synthetic_trace(branch=0x40, stack_pointer=0x1300)
        trace["records"][-1:] = [{"kind": "menu-observation"}] + second["records"][1:]
        result = tool.summarize(trace)
        self.assertTrue(result["entry_abi_matches_static_contract"])
        self.assertTrue(result["paired_return_chain_matches_static_contract"])
        self.assertEqual(result["observed_branch_words"], [0, 0x40])
        self.assertEqual(result["entry_stack_pointers"], [0x1200, 0x1300])
        trace["records"][8]["wram"]["AE92"] = 1
        result = tool.summarize(trace)
        self.assertFalse(result["entry_abi_matches_static_contract"])
        self.assertTrue(result["paired_return_chain_matches_static_contract"])

    def test_prior_enemy_completion_does_not_complete_later_pc_invocation(self):
        trace = synthetic_trace()
        earlier_action = [
            {"kind": "caller-package-latch", "wram": {"9876": 1}},
            {"kind": "caller-effect-latch", "wram": {"5D9B": 0}},
            {"kind": "branch-producer-complete"},
        ]
        trace["records"][1:1] = earlier_action
        result = tool.summarize(trace)
        self.assertTrue(result["entry_abi_matches_static_contract"])
        self.assertTrue(result["paired_return_chain_matches_static_contract"])
        self.assertFalse(result["paired_pc_action_completion_observed"])

    def test_later_action_completion_cannot_be_borrowed_across_either_boundary(self):
        completed_latches = [
            {"kind": "caller-package-latch", "wram": {"9876": 1}},
            {"kind": "caller-effect-latch", "wram": {"5D9B": 0}},
        ]
        for boundary in ("branch-producer-complete", "resolver-entry"):
            with self.subTest(boundary=boundary):
                trace = synthetic_trace()
                if boundary == "resolver-entry":
                    next_action = synthetic_trace(stack_pointer=0x1300)["records"][1:-1]
                else:
                    next_action = [{"kind": boundary}]
                trace["records"][-1:-1] = next_action + copy.deepcopy(completed_latches)
                result = tool.summarize(trace)
                self.assertTrue(result["paired_return_chain_matches_static_contract"])
                self.assertFalse(result["paired_pc_action_completion_observed"])

    def test_same_window_completion_requires_ordered_ready_latch_values(self):
        scenarios = (
            (1, 0, False, True),
            (0xFF, 0, False, True),
            (1, 0, True, False),
            (0, 0, False, False),
            (1, 1, False, False),
        )
        for package, effect, reversed_order, expected in scenarios:
            with self.subTest(package=package, effect=effect, reversed_order=reversed_order):
                trace = synthetic_trace()
                latches = [
                    {"kind": "caller-package-latch", "wram": {"9876": package}},
                    {"kind": "caller-effect-latch", "wram": {"5D9B": effect}},
                ]
                if reversed_order:
                    latches.reverse()
                trace["records"][-1:-1] = latches
                result = tool.summarize(trace)
                self.assertTrue(result["entry_abi_matches_static_contract"])
                self.assertTrue(result["paired_return_chain_matches_static_contract"])
                self.assertEqual(result["paired_pc_action_completion_observed"], expected)


if __name__ == "__main__":
    unittest.main()
