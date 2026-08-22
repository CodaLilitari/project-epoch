from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_action_probe_v4.py"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_action_probe_v4.py"
)
LAUNCHER_PATH = (
    ROOT / "tools" / "run_mesen_wram_ownership_battle_action_probe_v4.py"
)
CONTRACT_PATH = (
    ROOT
    / "references"
    / "mesen_wram_ownership_battle_action_probe_scenarios_v4.json"
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


BUILDER = load_module(
    "build_mesen_wram_ownership_battle_action_probe_v4_test",
    BUILDER_PATH,
)
VALIDATOR = load_module(
    "validate_mesen_wram_ownership_battle_action_probe_v4_test",
    VALIDATOR_PATH,
)
LAUNCHER = load_module(
    "run_mesen_wram_ownership_battle_action_probe_v4_test",
    LAUNCHER_PATH,
)
BASE = VALIDATOR._BASE
V3 = VALIDATOR._V3


def watched_range_bytes() -> dict[str, bytes]:
    return {
        "old-compatibility": bytes(0x50),
        "roster": bytes.fromhex(V3.EXPECTED_ROSTER),
        "joined": bytes((V3.EXPECTED_JOINED,)),
        "epoch-name": bytes.fromhex("a4c9c8bcc100"),
        "front-guard": bytes(0x04),
        "candidate": bytes(0x50),
        "rear-guard": bytes(0x10),
    }


def snapshot(ranges: dict[str, bytes]) -> dict[str, str]:
    return {
        BASE.SNAPSHOT_FIELD_BY_RANGE[row["name"]]: ranges[row["name"]].hex()
        for row in BASE.WATCHED_RANGES
    }


def zero_counters() -> list[dict[str, int]]:
    return [
        {
            "address": address,
            "read_count": 0,
            "write_count": 0,
        }
        for address in BASE.WATCHED_ADDRESSES
    ]


def battle_snapshot() -> dict[str, object]:
    return {
        "location": 0x01DB,
        "storyline": 0xD6,
        "pending_request": 0x01,
        "explore_mode": 0,
        "dialog_state": 0,
        "active_party_hex": V3.EXPECTED_ACTIVE,
        "roster_hex": V3.EXPECTED_ROSTER,
        "joined": V3.EXPECTED_JOINED,
        "battle_ids_hex": V3.EXPECTED_BATTLE_IDS,
        "battle_current_hp": list(VALIDATOR.EXPECTED_FULL_HP),
        "battle_max_hp": list(VALIDATOR.EXPECTED_FULL_HP),
        "battle_ui_hex": "0059ac",
        "command_state_hex": "0000000000ffff000100000000",
        "command_ready": True,
    }


def initial_action_row() -> dict[str, object]:
    return {
        "frame": 0,
        **copy.deepcopy(VALIDATOR.EXPECTED_INITIAL_ACTION),
    }


def make_trace(scenario: str) -> dict[str, object]:
    ranges = watched_range_bytes()
    contract = VALIDATOR.SCENARIO_CONTRACTS[scenario]
    timeline = [initial_action_row()]
    if scenario == "attack-target-hold":
        endpoint = initial_action_row()
        endpoint["frame"] = 20
        endpoint["target_state_hex"] = "01010000070000000000000000"
        endpoint["target_list_hex"] = "03ffffffffffffffffffffff"
        timeline.append(endpoint)
    return {
        "schema": VALIDATOR.SCHEMA,
        "collector_version": VALIDATOR.COLLECTOR_VERSION,
        "scenario": scenario,
        "variant": "zero",
        "collector_explicit_write_scope": (
            "snes-work-ram-preparation-before-counters-arm-only"
        ),
        "checkpoint": {
            "id": V3.CHECKPOINT_ID,
            "state_size": V3.CHECKPOINT_SIZE,
            "state_sha256": V3.CHECKPOINT_SHA256,
            "source_frame": V3.CHECKPOINT_FRAME,
            "direct_page": V3.CHECKPOINT_DIRECT_PAGE,
            "location": V3.CHECKPOINT_LOCATION,
        },
        "scenario_contract": {
            "terminal_frame_min": contract["terminal_frame_min"],
            "terminal_frame_max": contract["terminal_frame_max"],
            "expected_access_class": contract["expected_access_class"],
            "inputs": copy.deepcopy(list(contract["inputs"])),
        },
        "observer": {
            "mechanism": "snes-work-ram-read-write-memory-callbacks",
            "memory_type": "snes-work-ram",
            "counter_granularity": "byte-address-and-access",
            "callback_limit": V3.CALLBACK_LIMIT,
            "counters_cover_every_watched_byte": True,
        },
        "watched_ranges": [
            copy.deepcopy(row) for row in BASE.WATCHED_RANGES
        ],
        "preparation": {
            "completed_before_counters_armed": True,
            "counters_zero_after_preparation": True,
            "writes": [],
        },
        "pre_battle": battle_snapshot(),
        "action_timeline": timeline,
        "pre": snapshot(ranges),
        "callbacks": [],
        "counters": zero_counters(),
        "post": snapshot(ranges),
        "post_battle": battle_snapshot(),
        "termination": {
            "collector_stopped": True,
            "success": True,
            "overflow": False,
            "observer_error": None,
            "counters_armed": True,
            "preparation_writes_after_arm": 0,
            "terminal_frame": contract["terminal_frame_min"],
            "unexpected_accesses": 0,
        },
    }


def counter_for(trace: dict[str, object], address: int) -> dict[str, int]:
    counters = trace["counters"]
    assert isinstance(counters, list)
    return next(row for row in counters if row["address"] == address)


class MesenBattleActionProbeV4Tests(unittest.TestCase):
    def test_source_contract_and_generated_collector_pins(self) -> None:
        for path, size, digest in (
            (
                BUILDER_PATH,
                LAUNCHER.BUILDER_SIZE,
                LAUNCHER.BUILDER_SHA256,
            ),
            (
                VALIDATOR_PATH,
                LAUNCHER.VALIDATOR_SIZE,
                LAUNCHER.VALIDATOR_SHA256,
            ),
            (
                CONTRACT_PATH,
                LAUNCHER.SCENARIO_CONTRACT_SIZE,
                LAUNCHER.SCENARIO_CONTRACT_SHA256,
            ),
        ):
            source = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertEqual(len(source), size)
                self.assertEqual(hashlib.sha256(source).hexdigest(), digest)

        generated = BUILDER.build_collector()
        self.assertEqual(len(generated), LAUNCHER.GENERATED_COLLECTOR_SIZE)
        self.assertEqual(
            hashlib.sha256(generated).hexdigest(),
            LAUNCHER.GENERATED_COLLECTOR_SHA256,
        )
        self.assertEqual(LAUNCHER._verify_ancestry(), LAUNCHER.ANCESTRY_PINS)

    def test_builder_is_deterministic_and_preserves_v3_watcher(self) -> None:
        first = BUILDER.build_collector()
        second = BUILDER.build_collector()
        self.assertEqual(first, second)
        text = first.decode("utf-8")
        for fragment in (
            "local OLD_BLOCK_START = 0x2830",
            "local CANDIDATE_START = 0x2CA0",
            "local REAR_GUARD_END = 0x2CFF",
            "local CALLBACK_LIMIT = 16384",
            "counters_match",
            'assert(variant == "zero", "battle-action probe is zero-only")',
            '"action_timeline":',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertNotIn(
            'assert(variant == "zero" or variant == "canary"',
            text,
        )
        self.assertEqual(text.count("emu.write("), 1)
        self.assertEqual(text.count("emu.write16("), 1)

    def test_builder_rejects_v3_builder_source_drift(self) -> None:
        with mock.patch.object(
            BUILDER,
            "V3_BUILDER_SHA256",
            "0" * 64,
        ):
            with self.assertRaisesRegex(
                BUILDER.ActionProbeBuildError,
                "SHA-256 drifted",
            ):
                BUILDER.build_collector()

    def test_contract_validates_and_is_explicitly_unaccepted(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        LAUNCHER._validate_scenario_contract(contract)
        self.assertEqual(
            contract["acceptance_status"],
            "exploratory-zero-only-no-accepted-hashes",
        )
        self.assertTrue(contract["controls"]["accepted_mode_forbidden"])
        self.assertTrue(contract["controls"]["zero_variant_only"])

    def test_launcher_refuses_accepted_mode_before_runtime(self) -> None:
        args = LAUNCHER.build_parser().parse_args(
            [
                "--scenario",
                "attack-target-hold",
                "--output-dir",
                "private/test_runs/mesen2/never-created",
            ]
        )
        with mock.patch.object(LAUNCHER.V3, "run") as mocked:
            with self.assertRaisesRegex(
                LAUNCHER.TraceLaunchError,
                "exploratory zero-only",
            ):
                LAUNCHER.run(args)
            mocked.assert_not_called()

    def test_validator_accepts_synthetic_zero_only_set(self) -> None:
        traces = [
            make_trace(scenario)
            for scenario in VALIDATOR.SCENARIO_CONTRACTS
        ]
        for trace in traces:
            self.assertEqual(
                VALIDATOR.validate_trace_document(trace),
                (trace["scenario"], "zero"),
            )
        report = VALIDATOR.validate_trace_documents(traces)
        self.assertFalse(report["accepted_evidence"])
        self.assertEqual(report["trace_count"], 3)
        self.assertTrue(report["shared_checkpoint_preimage"])

    def test_validator_rejects_candidate_access(self) -> None:
        trace = make_trace("attack-action-horizon")
        trace["callbacks"] = [
            {
                "seq": 0,
                "frame": 100,
                "access": "read",
                "address": 0x7E2CA0,
                "value": 0,
                "pc24": 0xC01234,
            }
        ]
        counter_for(trace, 0x7E2CA0)["read_count"] = 1
        with self.assertRaisesRegex(Exception, "illegally accesses candidate"):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_old_compatibility_write(self) -> None:
        trace = make_trace("attack-action-horizon")
        trace["callbacks"] = [
            {
                "seq": 0,
                "frame": 100,
                "access": "write",
                "address": 0x7E2830,
                "value": 0,
                "pc24": 0xC01234,
            }
        ]
        counter_for(trace, 0x7E2830)["write_count"] = 1
        with self.assertRaisesRegex(
            Exception,
            "unapproved old-compatibility write",
        ):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_protected_roster_write(self) -> None:
        trace = make_trace("attack-action-horizon")
        trace["callbacks"] = [
            {
                "seq": 0,
                "frame": 100,
                "access": "write",
                "address": 0x7E2980,
                "value": 0,
                "pc24": 0xC01234,
            }
        ]
        counter_for(trace, 0x7E2980)["write_count"] = 1
        with self.assertRaisesRegex(Exception, "illegally writes roster"):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_timeline_shape_and_order_drift(self) -> None:
        trace = make_trace("attack-action-horizon")
        del trace["action_timeline"][0]["logic_busy_hex"]
        with self.assertRaisesRegex(Exception, "keys mismatch"):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("attack-action-horizon")
        duplicate = copy.deepcopy(trace["action_timeline"][0])
        duplicate["frame"] = 10
        trace["action_timeline"].append(duplicate)
        with self.assertRaisesRegex(Exception, "duplicates the prior"):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_target_hold_without_target_state(self) -> None:
        trace = make_trace("attack-target-hold")
        trace["action_timeline"] = [initial_action_row()]
        with self.assertRaisesRegex(Exception, "target-selection"):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_target_hold_hp_change(self) -> None:
        trace = make_trace("attack-target-hold")
        trace["post_battle"]["battle_current_hp"][0] -= 1
        trace["action_timeline"][-1]["current_hp"][0] -= 1
        with self.assertRaisesRegex(Exception, "full-HP control"):
            VALIDATOR.validate_trace_document(trace)


if __name__ == "__main__":
    unittest.main()
