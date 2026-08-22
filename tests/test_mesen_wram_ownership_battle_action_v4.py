from __future__ import annotations

import copy
import difflib
import hashlib
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PROBE_BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_action_probe_v4.py"
)
BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_action_collector_v4.py"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_action_trace_v4.py"
)
LAUNCHER_PATH = (
    ROOT / "tools" / "run_mesen_wram_ownership_battle_action_trace_v4.py"
)
REPLAY_VALIDATOR_PATH = (
    ROOT
    / "tools"
    / "validate_mesen_wram_ownership_battle_action_replay_v4.py"
)
CONTRACT_PATH = (
    ROOT
    / "references"
    / "mesen_wram_ownership_battle_action_scenarios_v4.json"
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


PROBE_BUILDER = load_module(
    "build_mesen_wram_ownership_battle_action_probe_v4_accepted_test",
    PROBE_BUILDER_PATH,
)
BUILDER = load_module(
    "build_mesen_wram_ownership_battle_action_collector_v4_test",
    BUILDER_PATH,
)
VALIDATOR = load_module(
    "validate_mesen_wram_ownership_battle_action_trace_v4_test",
    VALIDATOR_PATH,
)
LAUNCHER = load_module(
    "run_mesen_wram_ownership_battle_action_trace_v4_test",
    LAUNCHER_PATH,
)
REPLAY_VALIDATOR = load_module(
    "validate_mesen_wram_ownership_battle_action_replay_v4_test",
    REPLAY_VALIDATOR_PATH,
)
BASE = VALIDATOR._BASE
V3 = VALIDATOR._V3
PROBE_VALIDATOR = VALIDATOR._PROBE


OLD_COMPATIBILITY = bytes(
    (index * 37 + 11) & 0xFF for index in range(0x50)
)
EPOCH_NAME = bytes.fromhex("a4c9c8bcc100")


def expected_candidate(variant: str) -> bytes:
    if variant == "zero":
        return bytes(0x50)
    return bytes(BASE.CANDIDATE_CANARY)


def watched_range_bytes(variant: str) -> dict[str, bytes]:
    return {
        "old-compatibility": OLD_COMPATIBILITY,
        "roster": bytes.fromhex(V3.EXPECTED_ROSTER),
        "joined": bytes((V3.EXPECTED_JOINED,)),
        "epoch-name": EPOCH_NAME,
        "front-guard": bytes(0x04),
        "candidate": expected_candidate(variant),
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


def counter_for(trace: dict[str, object], address: int) -> dict[str, int]:
    counters = trace["counters"]
    assert isinstance(counters, list)
    return next(row for row in counters if row["address"] == address)


def battle_snapshot(
    scenario: str,
    phase: str,
) -> dict[str, object]:
    if phase == "pre":
        current_hp = list(PROBE_VALIDATOR.EXPECTED_FULL_HP)
        battle_ui = PROBE_VALIDATOR.EXPECTED_INITIAL_ACTION["battle_ui_hex"]
        command_state = PROBE_VALIDATOR.EXPECTED_INITIAL_ACTION[
            "command_state_hex"
        ]
    else:
        endpoint = VALIDATOR.EXPECTED_ENDPOINTS[scenario]["last"]
        current_hp = copy.deepcopy(endpoint["current_hp"])
        battle_ui = endpoint["battle_ui_hex"]
        command_state = endpoint["command_state_hex"]
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
        "battle_current_hp": current_hp,
        "battle_max_hp": list(PROBE_VALIDATOR.EXPECTED_FULL_HP),
        "battle_ui_hex": battle_ui,
        "command_state_hex": command_state,
        "command_ready": True,
    }


def initial_action_row() -> dict[str, object]:
    return {
        "frame": 0,
        **copy.deepcopy(PROBE_VALIDATOR.EXPECTED_INITIAL_ACTION),
    }


MILESTONES: dict[str, dict[int, tuple[str, object]]] = {
    "battle-action-control": {
        336: (
            "current_hp",
            [739, 821, 712, 8000, 12000, 20000],
        ),
        363: (
            "action_request_hex",
            "00030200000000ffff000000",
        ),
    },
    "battle-attack-target-hold": {
        20: (
            "target_state_hex",
            "01010000070000000000000000",
        ),
    },
    "battle-attack-recovery": {
        32: ("pc_fifo_hex", "00ffffff0103"),
        337: (
            "current_hp",
            [739, 821, 712, 8000, 12000, 20000],
        ),
        373: ("pc_fifo_hex", "ffffffff0003"),
        375: (
            "action_request_hex",
            "00000100000010ffff000080",
        ),
        557: (
            "current_hp",
            [739, 821, 712, 7038, 12000, 20000],
        ),
    },
}


def action_timeline(scenario: str) -> list[dict[str, object]]:
    endpoint_contract = VALIDATOR.EXPECTED_ENDPOINTS[scenario]
    row_count = endpoint_contract["row_count"]
    last = copy.deepcopy(endpoint_contract["last"])
    last_frame = int(last["frame"])
    milestones = MILESTONES[scenario]
    middle_count = row_count - 2
    generic_count = middle_count - len(milestones)
    if generic_count == 1:
        generic_frames = [1]
    else:
        generic_frames = [
            1 + ((last_frame - 2) * index // (generic_count - 1))
            for index in range(generic_count)
        ]
    frames = sorted([*generic_frames, *milestones])
    applied: set[int] = set()
    rows = [initial_action_row()]
    for index, frame in enumerate(frames, start=1):
        row = initial_action_row()
        row["frame"] = frame
        row["ai_state_hex"] = f"{index:06x}"
        if frame in milestones and frame not in applied:
            key, value = milestones[frame]
            row[key] = copy.deepcopy(value)
            applied.add(frame)
        rows.append(row)
    rows.append(last)
    assert len(rows) == row_count
    assert applied == set(milestones)
    return rows


def make_trace(scenario: str, variant: str) -> dict[str, object]:
    ranges = watched_range_bytes(variant)
    contract = VALIDATOR.SCENARIO_CONTRACTS[scenario]
    callbacks: list[dict[str, object]] = []
    counters = zero_counters()
    if scenario == "battle-attack-recovery":
        callbacks = [
            {
                "seq": 0,
                "frame": 377,
                "access": "read",
                "address": 0x7E2980,
                "value": 0,
                "pc24": 0xC14A43,
            },
            {
                "seq": 1,
                "frame": 377,
                "access": "read",
                "address": 0x7E2980,
                "value": 0,
                "pc24": 0xC1438A,
            },
        ]
        next(
            row for row in counters if row["address"] == 0x7E2980
        )["read_count"] = 2
    return {
        "schema": VALIDATOR.SCHEMA,
        "collector_version": VALIDATOR.COLLECTOR_VERSION,
        "scenario": scenario,
        "variant": variant,
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
            "writes": copy.deepcopy(
                VALIDATOR._expected_preparation_writes(scenario, variant)
            ),
        },
        "pre_battle": battle_snapshot(scenario, "pre"),
        "action_timeline": action_timeline(scenario),
        "pre": snapshot(ranges),
        "callbacks": callbacks,
        "counters": counters,
        "post": snapshot(ranges),
        "post_battle": battle_snapshot(scenario, "post"),
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


def make_trace_set() -> list[dict[str, object]]:
    return [
        make_trace(scenario, variant)
        for scenario in VALIDATOR.SCENARIO_CONTRACTS
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


class MesenWramOwnershipBattleActionV4Tests(unittest.TestCase):
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

    def test_builder_diff_scope_is_exact_and_watcher_is_unchanged(self) -> None:
        probe = PROBE_BUILDER.build_collector().decode("utf-8")
        accepted = BUILDER.build_collector().decode("utf-8")
        changes = [
            opcode
            for opcode in difflib.SequenceMatcher(
                None,
                probe.splitlines(keepends=True),
                accepted.splitlines(keepends=True),
                autojunk=False,
            ).get_opcodes()
            if opcode[0] != "equal"
        ]
        self.assertEqual(
            changes,
            [
                ("replace", 159, 163, 159, 163),
                ("replace", 165, 166, 165, 166),
                ("replace", 171, 175, 171, 175),
                ("replace", 180, 181, 180, 181),
                ("replace", 182, 183, 182, 183),
                ("replace", 185, 186, 185, 186),
                ("replace", 199, 200, 199, 200),
                ("replace", 1147, 1150, 1147, 1150),
                ("insert", 1238, 1238, 1238, 1387),
                ("replace", 1241, 1250, 1390, 1392),
                ("replace", 1251, 1252, 1393, 1403),
                ("replace", 1428, 1429, 1579, 1580),
            ],
        )
        for fragment in (
            "local OLD_BLOCK_START = 0x2830",
            "local CANDIDATE_START = 0x2CA0",
            "local REAR_GUARD_END = 0x2CFF",
            "local CALLBACK_LIMIT = 16384",
            "counters_match",
            '"action_timeline":',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, accepted)
        self.assertIn(
            'assert(variant == "zero" or variant == "canary"',
            accepted,
        )
        self.assertIn(
            '"schema":"project-epoch-mesen-wram-ownership-'
            'battle-action-trace-v4"',
            accepted,
        )
        self.assertEqual(accepted.count("emu.write("), probe.count("emu.write("))
        self.assertEqual(
            accepted.count("emu.write16("),
            probe.count("emu.write16("),
        )

    def test_builder_rejects_probe_preimage_drift(self) -> None:
        with mock.patch.object(BUILDER, "PROBE_BUILDER_SHA256", "0" * 64):
            with self.assertRaisesRegex(
                BUILDER.BattleActionBuildError,
                "SHA-256 drifted",
            ):
                BUILDER.build_collector()

    def test_validator_accepts_synthetic_six_trace_set(self) -> None:
        traces = make_trace_set()
        for trace in traces:
            self.assertEqual(
                VALIDATOR.validate_trace_document(trace),
                (trace["scenario"], trace["variant"]),
            )
        report = VALIDATOR.validate_trace_documents(traces)
        self.assertEqual(report["trace_count"], 6)
        self.assertEqual(report["watched_byte_count"], 196)
        self.assertTrue(report["candidate_and_guards_any_access_forbidden"])
        self.assertTrue(report["old_compatibility_writes_forbidden"])
        self.assertTrue(report["roster_joined_epoch_writes_forbidden"])
        self.assertTrue(report["counter_callback_reconciliation"])
        self.assertTrue(report["zero_canary_observations_identical"])
        self.assertTrue(report["shared_checkpoint_preimage"])
        self.assertEqual(report["attack_recovery_enemy_slot3_hp"], 7038)
        self.assertEqual(report["attack_recovery_critical_marker_frame"], 375)
        self.assertEqual(
            report["attack_recovery_critical_marker"],
            "AE9B-bit-80",
        )
        self.assertEqual(
            report["attack_recovery_exact_roster_read_pcs"],
            ["C14A43", "C1438A"],
        )

    def test_validator_rejects_endpoint_and_causal_milestone_drift(
        self,
    ) -> None:
        trace = make_trace("battle-action-control", "zero")
        trace["action_timeline"][-1]["battle_ui_hex"] = "03bf58"
        with self.assertRaises(Exception):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-action-control", "zero")
        milestone = next(
            row
            for row in trace["action_timeline"]
            if (
                row["frame"] == 363
                and row["action_request_hex"]
                == "00030200000000ffff000000"
            )
        )
        milestone["action_request_hex"] = "00030201000000ffff000000"
        with self.assertRaisesRegex(Exception, "missing causal milestone"):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-attack-recovery", "zero")
        critical = next(
            row
            for row in trace["action_timeline"]
            if row["frame"] == 375
        )
        critical["action_request_hex"] = "00000100000010ffff000000"
        with self.assertRaisesRegex(Exception, "missing causal milestone"):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_candidate_access_and_canary_prep_drift(
        self,
    ) -> None:
        trace = make_trace("battle-attack-target-hold", "zero")
        trace["callbacks"] = [
            {
                "seq": 0,
                "frame": 50,
                "access": "read",
                "address": 0x7E2CA0,
                "value": 0,
                "pc24": 0xC01234,
            }
        ]
        counter_for(trace, 0x7E2CA0)["read_count"] = 1
        with self.assertRaisesRegex(Exception, "illegally accesses candidate"):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-attack-target-hold", "canary")
        trace["preparation"]["writes"][0]["value"] ^= 0x01
        with self.assertRaises(Exception):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-attack-recovery", "zero")
        trace["callbacks"][0]["pc24"] = 0xC14A44
        with self.assertRaisesRegex(Exception, "exact callback route drifted"):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_pair_and_cross_scenario_drift(self) -> None:
        traces = make_trace_set()
        canary = find_trace(traces, "battle-action-control", "canary")
        canary["action_timeline"][1]["ai_state_hex"] = "ffffff"
        VALIDATOR.validate_trace_document(canary)
        with self.assertRaisesRegex(
            Exception,
            "zero/canary action_timeline differs",
        ):
            VALIDATOR.validate_trace_documents(traces)

        traces = make_trace_set()
        for variant in ("zero", "canary"):
            trace = find_trace(
                traces,
                "battle-attack-target-hold",
                variant,
            )
            for phase in ("pre", "post"):
                old = bytearray.fromhex(
                    trace[phase]["old_compatibility_hex"]
                )
                old[10] ^= 0x01
                trace[phase]["old_compatibility_hex"] = old.hex()
        with self.assertRaisesRegex(
            Exception,
            "canonical checkpoint preimage",
        ):
            VALIDATOR.validate_trace_documents(traces)

    def test_contract_and_source_pins_are_fail_closed(self) -> None:
        source = CONTRACT_PATH.read_bytes()
        contract = json.loads(source)
        LAUNCHER._validate_scenario_contract(contract)
        self.assertEqual(
            contract["acceptance_status"],
            "accepted-exact-trace-hashes",
        )
        expected_outputs = [
            {
                "scenario": scenario,
                "variant": variant,
                "trace_size": LAUNCHER.EXPECTED_OUTPUTS[
                    (scenario, variant)
                ]["trace"][0],
                "trace_sha256": LAUNCHER.EXPECTED_OUTPUTS[
                    (scenario, variant)
                ]["trace"][1],
            }
            for scenario in LAUNCHER.SCENARIOS
            for variant in LAUNCHER.VARIANTS
        ]
        self.assertEqual(contract["accepted_outputs"], expected_outputs)
        self.assertEqual(len(LAUNCHER.EXPECTED_OUTPUTS), 6)
        self.assertEqual(
            contract["replay_contract"],
            {
                "schema": (
                    "project-epoch-mesen-wram-ownership-"
                    "battle-action-replay-v4"
                ),
                "trace_count_per_root": 6,
                "semantic_validation_required_for_each_root": True,
                "exact_trace_byte_identity_required": True,
                "screenshots_in_acceptance_gate": False,
            },
        )
        self.assertEqual(
            contract["scenarios"],
            LAUNCHER._expected_contract_scenarios(),
        )
        self.assertEqual(
            contract["endpoint_contracts"],
            LAUNCHER.EXPECTED_ENDPOINT_CONTRACTS,
        )
        self.assertEqual(contract["trace_contract"]["trace_count"], 6)
        self.assertEqual(
            contract["trace_contract"]["variants"],
            ["zero", "canary"],
        )
        for key, (path, size, digest) in LAUNCHER.EXPECTED_SOURCE_PINS.items():
            row = contract["sources"][key]
            with self.subTest(source=key):
                if path is not None:
                    self.assertEqual(row["path"], path)
                self.assertEqual(row["size"], size)
                self.assertEqual(row["sha256"], digest)

        mutations = (
            (
                "source",
                lambda row: row["sources"]["validator"].__setitem__(
                    "sha256",
                    "0" * 64,
                ),
            ),
            (
                "scenario",
                lambda row: row["scenarios"][2].__setitem__(
                    "terminal_frame",
                    607,
                ),
            ),
            (
                "endpoint",
                lambda row: row["endpoint_contracts"][
                    "battle-action-control"
                ].__setitem__("last_signature_frame", 606),
            ),
            (
                "output",
                lambda row: row["accepted_outputs"][0].__setitem__(
                    "trace_sha256",
                    "0" * 64,
                ),
            ),
            (
                "control",
                lambda row: row["controls"].__setitem__(
                    "candidate_and_guards_zero_access_required",
                    False,
                ),
            ),
        )
        for label, mutate in mutations:
            drifted = copy.deepcopy(contract)
            mutate(drifted)
            with self.subTest(mutation=label):
                with self.assertRaises(LAUNCHER.TraceLaunchError):
                    LAUNCHER._validate_scenario_contract(drifted)

    def test_launcher_parser_supports_both_variants(self) -> None:
        for variant in LAUNCHER.VARIANTS:
            args = LAUNCHER.build_parser().parse_args(
                [
                    "--scenario",
                    "battle-attack-recovery",
                    "--variant",
                    variant,
                    "--output-dir",
                    "private/test_runs/mesen2/not-created",
                    "--exploratory",
                ]
            )
            with self.subTest(variant=variant):
                self.assertEqual(args.variant, variant)
                self.assertTrue(args.exploratory)
                self.assertEqual(args.timeout, 120)

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                LAUNCHER.build_parser().parse_args(
                    [
                        "--scenario",
                        "battle-attack-recovery",
                        "--variant",
                        "random",
                        "--output-dir",
                        "private/test_runs/mesen2/not-created",
                        "--exploratory",
                    ]
                )

    def test_launcher_default_mode_is_accepted_without_invoking_mesen(
        self,
    ) -> None:
        args = LAUNCHER.build_parser().parse_args(
            [
                "--scenario",
                "battle-action-control",
                "--variant",
                "canary",
                "--output-dir",
                "private/test_runs/mesen2/never-created",
            ]
        )
        base_result = {
            "status": "synthetic",
            "trace": {},
            "screenshot": {},
        }
        with mock.patch.object(
            LAUNCHER.V3,
            "run",
            return_value=base_result,
        ) as mocked:
            result = LAUNCHER.run(args)
        mocked.assert_called_once_with(args)
        self.assertEqual(result["status"], "accepted-battle-action-exact-trace")
        self.assertTrue(result["accepted_evidence"])

    def test_launcher_exploratory_result_is_explicitly_unaccepted(
        self,
    ) -> None:
        args = LAUNCHER.build_parser().parse_args(
            [
                "--scenario",
                "battle-attack-recovery",
                "--variant",
                "zero",
                "--output-dir",
                "private/test_runs/mesen2/never-created",
                "--exploratory",
            ]
        )
        base_result = {
            "status": "synthetic",
            "trace": {},
            "screenshot": {},
        }
        with mock.patch.object(
            LAUNCHER.V3,
            "run",
            return_value=base_result,
        ) as mocked:
            result = LAUNCHER.run(args)
        mocked.assert_called_once_with(args)
        self.assertEqual(
            result["status"],
            "exploratory-battle-action-exact-endpoint-trace",
        )
        self.assertFalse(result["accepted_evidence"])
        self.assertEqual(
            result["action_contract_sha256"],
            LAUNCHER.SCENARIO_CONTRACT_SHA256,
        )
        self.assertEqual(len(LAUNCHER.EXPECTED_OUTPUTS), 6)

    def test_replay_validator_accepts_exact_roots_and_rejects_byte_drift(
        self,
    ) -> None:
        traces = make_trace_set()
        by_case = {
            (trace["scenario"], trace["variant"]): trace
            for trace in traces
        }
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            primary_root = temp_root / "primary"
            replay_root = temp_root / "replay"
            for scenario in REPLAY_VALIDATOR.SCENARIOS:
                for variant in REPLAY_VALIDATOR.VARIANTS:
                    relative = Path(scenario) / variant / "trace.json"
                    payload = json.dumps(
                        by_case[(scenario, variant)],
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    for root in (primary_root, replay_root):
                        path = root / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(payload)

            report = REPLAY_VALIDATOR.validate_replay_roots(
                primary_root,
                replay_root,
            )
            self.assertEqual(
                report["status"],
                "validated-exact-independent-replay",
            )
            self.assertEqual(report["trace_count_per_root"], 6)
            self.assertTrue(report["trace_bytes_identical"])
            self.assertFalse(report["screenshots_in_acceptance_gate"])

            drifted = (
                replay_root
                / "battle-action-control"
                / "zero"
                / "trace.json"
            )
            drifted.write_bytes(drifted.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                REPLAY_VALIDATOR.ReplayValidationError,
                "replay trace differs",
            ):
                REPLAY_VALIDATOR.validate_replay_roots(
                    primary_root,
                    replay_root,
                )


if __name__ == "__main__":
    unittest.main()
