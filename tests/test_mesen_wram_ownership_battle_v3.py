from __future__ import annotations

import copy
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_collector_v3.py"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_trace_v3.py"
)
LAUNCHER_PATH = (
    ROOT / "tools" / "run_mesen_wram_ownership_battle_trace_v3.py"
)
CONTRACT_PATH = (
    ROOT / "references" / "mesen_wram_ownership_battle_scenarios_v3.json"
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
    "build_mesen_wram_ownership_battle_collector_v3_test",
    BUILDER_PATH,
)
VALIDATOR = load_module(
    "validate_mesen_wram_ownership_battle_trace_v3_test",
    VALIDATOR_PATH,
)
LAUNCHER = load_module(
    "run_mesen_wram_ownership_battle_trace_v3_test",
    LAUNCHER_PATH,
)
BASE = VALIDATOR._BASE


OLD_COMPATIBILITY = bytes(
    (index * 37 + 11) & 0xFF for index in range(0x50)
)
ROSTER = bytes.fromhex(VALIDATOR.EXPECTED_ROSTER)
JOINED = bytes((VALIDATOR.EXPECTED_JOINED,))
EPOCH = bytes.fromhex("a4c9c8bcc100")


def expected_candidate(variant: str) -> bytes:
    return (
        bytes(0x50)
        if variant == "zero"
        else bytes(BASE.CANDIDATE_CANARY)
    )


def pre_ranges(variant: str) -> dict[str, bytes]:
    return {
        "old-compatibility": OLD_COMPATIBILITY,
        "roster": ROSTER,
        "joined": JOINED,
        "epoch-name": EPOCH,
        "front-guard": bytes(0x04),
        "candidate": expected_candidate(variant),
        "rear-guard": bytes(0x10),
    }


def _range_byte(
    ranges: dict[str, bytes],
    address: int,
) -> int:
    range_name = BASE.ADDRESS_RANGE_NAME[address]
    watched_range = next(
        row for row in BASE.WATCHED_RANGES if row["name"] == range_name
    )
    return ranges[range_name][address - watched_range["start_address"]]


def callback_rows(
    scenario: str,
    ranges: dict[str, bytes],
) -> list[dict[str, object]]:
    schedules: dict[str, list[tuple[int, str, int, int]]] = {
        "calibration": [],
        "battle-idle": [
            (10, "read", 0x7E2830, 0xC01234),
        ],
        "battle-command-roundtrip": [
            (10, "read", 0x7E2831, 0xC11234),
            (30, "read", 0x7E2980, 0xC15678),
            (40, "read", 0x7E29AF, 0xC189AB),
        ],
        "battle-command-down": [
            (10, "read", 0x7E2832, 0xC21234),
            (30, "read", 0x7E2C4D, 0xC25678),
        ],
    }
    return [
        {
            "seq": sequence,
            "frame": frame,
            "access": access,
            "address": address,
            "value": _range_byte(ranges, address),
            "pc24": pc24,
        }
        for sequence, (frame, access, address, pc24) in enumerate(
            schedules[scenario]
        )
    ]


def post_ranges(
    before: dict[str, bytes],
    callbacks: list[dict[str, object]],
) -> dict[str, bytes]:
    result = {
        name: bytearray(source) for name, source in before.items()
    }
    for callback in callbacks:
        if callback["access"] != "write":
            continue
        address = int(callback["address"])
        range_name = BASE.ADDRESS_RANGE_NAME[address]
        watched_range = next(
            row
            for row in BASE.WATCHED_RANGES
            if row["name"] == range_name
        )
        offset = address - watched_range["start_address"]
        result[range_name][offset] = int(callback["value"])
    return {
        name: bytes(source) for name, source in result.items()
    }


def snapshot(ranges: dict[str, bytes]) -> dict[str, object]:
    return {
        BASE.SNAPSHOT_FIELD_BY_RANGE[watched_range["name"]]: ranges[
            watched_range["name"]
        ].hex()
        for watched_range in BASE.WATCHED_RANGES
    }


def counters(
    callbacks: list[dict[str, object]],
) -> list[dict[str, object]]:
    observed = Counter(
        (callback["address"], callback["access"])
        for callback in callbacks
    )
    return [
        {
            "address": address,
            "read_count": observed[(address, "read")],
            "write_count": observed[(address, "write")],
        }
        for address in BASE.WATCHED_ADDRESSES
    ]


def battle_snapshot(
    scenario: str,
    phase: str,
) -> dict[str, object]:
    command_state = VALIDATOR.EXPECTED_ATTACK_COMMAND_STATE
    if phase == "post" and scenario == "battle-command-down":
        command_state = VALIDATOR.EXPECTED_TECH_COMMAND_STATE
    return {
        "location": 0x01DB,
        "storyline": 0xD6,
        "pending_request": 0x01,
        "explore_mode": 0,
        "dialog_state": 0,
        "active_party_hex": VALIDATOR.EXPECTED_ACTIVE,
        "roster_hex": VALIDATOR.EXPECTED_ROSTER,
        "joined": VALIDATOR.EXPECTED_JOINED,
        "battle_ids_hex": VALIDATOR.EXPECTED_BATTLE_IDS,
        "battle_current_hp": list(VALIDATOR.EXPECTED_FULL_HP),
        "battle_max_hp": list(VALIDATOR.EXPECTED_FULL_HP),
        "battle_ui_hex": "0059ac",
        "command_state_hex": command_state,
        "command_ready": True,
    }


def make_trace(scenario: str, variant: str) -> dict[str, object]:
    before = pre_ranges(variant)
    callbacks = callback_rows(scenario, before)
    after = post_ranges(before, callbacks)
    contract = VALIDATOR.SCENARIO_CONTRACTS[scenario]
    return {
        "schema": VALIDATOR.SCHEMA,
        "collector_version": VALIDATOR.COLLECTOR_VERSION,
        "scenario": scenario,
        "variant": variant,
        "collector_explicit_write_scope": (
            "snes-work-ram-preparation-before-counters-arm-only"
        ),
        "checkpoint": {
            "id": VALIDATOR.CHECKPOINT_ID,
            "state_size": VALIDATOR.CHECKPOINT_SIZE,
            "state_sha256": VALIDATOR.CHECKPOINT_SHA256,
            "source_frame": VALIDATOR.CHECKPOINT_FRAME,
            "direct_page": VALIDATOR.CHECKPOINT_DIRECT_PAGE,
            "location": VALIDATOR.CHECKPOINT_LOCATION,
        },
        "scenario_contract": {
            "terminal_frame_min": contract["terminal_frame_min"],
            "terminal_frame_max": contract["terminal_frame_max"],
            "expected_access_class": contract["expected_access_class"],
            "inputs": [
                copy.deepcopy(row) for row in contract["inputs"]
            ],
        },
        "observer": {
            "mechanism": "snes-work-ram-read-write-memory-callbacks",
            "memory_type": "snes-work-ram",
            "counter_granularity": "byte-address-and-access",
            "callback_limit": VALIDATOR.CALLBACK_LIMIT,
            "counters_cover_every_watched_byte": True,
        },
        "watched_ranges": [
            copy.deepcopy(row) for row in BASE.WATCHED_RANGES
        ],
        "preparation": {
            "completed_before_counters_armed": True,
            "counters_zero_after_preparation": True,
            "writes": copy.deepcopy(
                VALIDATOR._expected_preparation_writes(
                    scenario,
                    variant,
                )
            ),
        },
        "pre_battle": battle_snapshot(scenario, "pre"),
        "pre": snapshot(before),
        "callbacks": callbacks,
        "counters": counters(callbacks),
        "post": snapshot(after),
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


BASE_CONFIGURATION_FIELDS = (
    "COLLECTOR",
    "COLLECTOR_SHA256",
    "VALIDATOR_PATH",
    "VALIDATOR_SHA256",
    "SCENARIO_CONTRACT_PATH",
    "SCENARIO_CONTRACT_SHA256",
    "SCENARIO_CONTRACT_SCHEMA",
    "TRACE_SCHEMA",
    "SCENARIOS",
    "VARIANTS",
    "EXPECTED_OUTPUTS",
    "MAX_TRACE_BYTES",
    "RUNTIME_HASHES",
    "PINNED_SIZES",
    "_validate_scenario_contract",
)


@contextmanager
def preserve_launcher_base_configuration():
    saved = {
        name: getattr(LAUNCHER.BASE, name)
        for name in BASE_CONFIGURATION_FIELDS
    }
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(LAUNCHER.BASE, name, value)


class MesenWramOwnershipBattleV3Tests(unittest.TestCase):
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
                self.assertEqual(
                    hashlib.sha256(source).hexdigest(),
                    digest,
                )

        base_source = BUILDER.BASE_COLLECTOR.read_bytes()
        self.assertEqual(len(base_source), BUILDER.BASE_COLLECTOR_SIZE)
        self.assertEqual(
            hashlib.sha256(base_source).hexdigest(),
            BUILDER.BASE_COLLECTOR_SHA256,
        )
        generated = BUILDER.build_collector(base_source)
        self.assertEqual(len(generated), LAUNCHER.GENERATED_COLLECTOR_SIZE)
        self.assertEqual(
            hashlib.sha256(generated).hexdigest(),
            LAUNCHER.GENERATED_COLLECTOR_SHA256,
        )
        self.assertEqual(LAUNCHER._verify_ancestry(), LAUNCHER.ANCESTRY_PINS)

    def test_builder_rejects_nonexact_base_preimages(self) -> None:
        base_source = BUILDER.BASE_COLLECTOR.read_bytes()
        changed = bytearray(base_source)
        changed[0] ^= 0x01
        with self.assertRaisesRegex(
            BUILDER.CollectorBuildError,
            "SHA-256 drifted",
        ):
            BUILDER.build_collector(bytes(changed))
        with self.assertRaisesRegex(
            BUILDER.CollectorBuildError,
            "size drifted",
        ):
            BUILDER.build_collector(base_source[:-1])
        with self.assertRaisesRegex(
            BUILDER.CollectorBuildError,
            "occur exactly once",
        ):
            BUILDER._replace_once("old old", "old", "new", "synthetic")

    def test_builder_scenario_input_and_endframe_transforms(self) -> None:
        generated = BUILDER.build_collector().decode("utf-8")
        for scenario in BUILDER.SCENARIOS:
            self.assertIn(f'["{scenario.name}"] = {{', generated)
            self.assertIn(
                f"terminal_frame = {scenario.terminal_frame}",
                generated,
            )
        self.assertIn(
            '{ button = "down", json_button = "DOWN", '
            "first = 20, last = 23 }",
            generated,
        )
        self.assertIn(
            '{ button = "up", json_button = "UP", '
            "first = 32, last = 35 }",
            generated,
        )
        self.assertNotIn(BUILDER.OLD_INPUT_DISPATCH, generated)
        self.assertIn("pending_fixed_terminal = true", generated)
        self.assertIn(
            "if pending_fixed_terminal then\n"
            "\t\t\tpending_fixed_terminal = false\n"
            "\t\t\temit_trace(true)",
            generated,
        )
        self.assertIn(f'"schema":"{BUILDER.TRACE_SCHEMA}"', generated)
        self.assertIn(
            f'"collector_version":{BUILDER.COLLECTOR_VERSION}',
            generated,
        )
        self.assertIn('"direct_page":0,', generated)
        self.assertIn('"location":475', generated)
        self.assertIn(
            '"old-compatibility",\n'
            '\t\t"roster",\n'
            '\t\t"joined",',
            generated,
        )

    def test_validator_accepts_synthetic_eight_trace_set(self) -> None:
        traces = make_trace_set()
        for trace in traces:
            self.assertEqual(
                VALIDATOR.validate_trace_document(trace),
                (trace["scenario"], trace["variant"]),
            )
        report = VALIDATOR.validate_trace_documents(traces)
        self.assertEqual(report["trace_count"], 8)
        self.assertEqual(report["watched_byte_count"], 196)
        self.assertTrue(report["candidate_and_guards_zero_access"])
        self.assertTrue(report["roster_joined_epoch_writes_forbidden"])
        self.assertTrue(report["counter_callback_reconciliation"])
        self.assertTrue(
            report[
                "all_scenarios_share_one_normalized_checkpoint_preimage"
            ]
        )
        self.assertGreater(
            report["old_compatibility_reads_in_zero_variants"],
            0,
        )
        self.assertEqual(
            report["old_compatibility_writes_in_zero_variants"],
            0,
        )

    def test_validator_pins_schema_state_direct_page_and_battle_shape(
        self,
    ) -> None:
        mutations = (
            ("schema", lambda trace: trace.__setitem__("schema", "v4")),
            (
                "state size",
                lambda trace: trace["checkpoint"].__setitem__(
                    "state_size",
                    VALIDATOR.CHECKPOINT_SIZE + 1,
                ),
            ),
            (
                "state hash",
                lambda trace: trace["checkpoint"].__setitem__(
                    "state_sha256",
                    "0" * 64,
                ),
            ),
            (
                "direct page",
                lambda trace: trace["checkpoint"].__setitem__(
                    "direct_page",
                    0x0100,
                ),
            ),
            (
                "location",
                lambda trace: trace["pre_battle"].__setitem__(
                    "location",
                    0x01D1,
                ),
            ),
            (
                "battle UI",
                lambda trace: trace["post_battle"].__setitem__(
                    "battle_ui_hex",
                    "0058ac",
                ),
            ),
            (
                "extra battle field",
                lambda trace: trace["post_battle"].__setitem__(
                    "untrusted",
                    True,
                ),
            ),
        )
        for label, mutate in mutations:
            trace = make_trace("battle-idle", "zero")
            mutate(trace)
            with self.subTest(label=label):
                with self.assertRaises(VALIDATOR.TraceValidationError):
                    VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_candidate_or_guard_access(self) -> None:
        for address in (0x7E2CA0, 0x7E2C9C, 0x7E2CF0):
            trace = make_trace("battle-idle", "zero")
            trace["callbacks"].append(
                {
                    "seq": len(trace["callbacks"]),
                    "frame": 50,
                    "access": "read",
                    "address": address,
                    "value": 0,
                    "pc24": 0xC01234,
                }
            )
            trace["counters"] = counters(trace["callbacks"])
            with self.subTest(address=f"{address:06X}"):
                with self.assertRaisesRegex(
                    VALIDATOR.TraceValidationError,
                    "illegally accesses",
                ):
                    VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_roster_joined_or_epoch_writes(self) -> None:
        for address in (0x7E2980, 0x7E29AF, 0x7E2C4D):
            trace = make_trace("battle-idle", "zero")
            trace["callbacks"].append(
                {
                    "seq": len(trace["callbacks"]),
                    "frame": 50,
                    "access": "write",
                    "address": address,
                    "value": _range_byte(pre_ranges("zero"), address),
                    "pc24": 0xC01234,
                }
            )
            trace["counters"] = counters(trace["callbacks"])
            with self.subTest(address=f"{address:06X}"):
                with self.assertRaisesRegex(
                    VALIDATOR.TraceValidationError,
                    "illegally writes",
                ):
                    VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-idle", "zero")
        trace["callbacks"].append(
            {
                "seq": len(trace["callbacks"]),
                "frame": 50,
                "access": "write",
                "address": 0x7E2830,
                "value": OLD_COMPATIBILITY[0],
                "pc24": 0xC01234,
            }
        )
        trace["counters"] = counters(trace["callbacks"])
        with self.assertRaisesRegex(
            VALIDATOR.TraceValidationError,
            "unapproved old-compatibility write",
        ):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_counter_or_callback_reconciliation_drift(
        self,
    ) -> None:
        trace = make_trace("battle-idle", "zero")
        unused = next(
            row
            for row in trace["counters"]
            if row["read_count"] == 0 and row["write_count"] == 0
        )
        unused["read_count"] = 1
        with self.assertRaisesRegex(
            VALIDATOR.TraceValidationError,
            "does not reconcile callbacks",
        ):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-idle", "zero")
        trace["callbacks"][0]["value"] ^= 0x01
        with self.assertRaisesRegex(
            VALIDATOR.TraceValidationError,
            "read value does not match",
        ):
            VALIDATOR.validate_trace_document(trace)

        trace = make_trace("battle-idle", "zero")
        old = bytearray.fromhex(
            trace["post"]["old_compatibility_hex"]
        )
        old[1] ^= 0x01
        trace["post"]["old_compatibility_hex"] = old.hex()
        with self.assertRaisesRegex(
            VALIDATOR.TraceValidationError,
            "does not reconcile callbacks",
        ):
            VALIDATOR.validate_trace_document(trace)

    def test_validator_rejects_pair_and_cross_scenario_drift(self) -> None:
        traces = make_trace_set()
        canary = find_trace(traces, "battle-idle", "canary")
        canary["callbacks"][0]["pc24"] ^= 0x01
        with self.assertRaisesRegex(
            VALIDATOR.TraceValidationError,
            "zero/canary callbacks differ",
        ):
            VALIDATOR.validate_trace_documents(traces)

        traces = make_trace_set()
        for variant in ("zero", "canary"):
            trace = find_trace(traces, "battle-idle", variant)
            for phase in ("pre", "post"):
                old = bytearray.fromhex(
                    trace[phase]["old_compatibility_hex"]
                )
                old[10] ^= 0x01
                trace[phase]["old_compatibility_hex"] = old.hex()
            trace["callbacks"][0]["value"] = bytearray.fromhex(
                trace["pre"]["old_compatibility_hex"]
            )[0]
        with self.assertRaisesRegex(
            VALIDATOR.TraceValidationError,
            "canonical checkpoint preimage",
        ):
            VALIDATOR.validate_trace_documents(traces)

    def test_contract_pins_timelines_inputs_outputs_and_controls(self) -> None:
        source = CONTRACT_PATH.read_bytes()
        self.assertEqual(len(source), LAUNCHER.SCENARIO_CONTRACT_SIZE)
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            LAUNCHER.SCENARIO_CONTRACT_SHA256,
        )
        contract = json.loads(source)
        LAUNCHER._validate_scenario_contract(contract)
        self.assertEqual(
            contract["scenarios"],
            LAUNCHER._expected_contract_scenarios(),
        )
        self.assertEqual(
            len(contract["accepted_outputs"]),
            len(LAUNCHER.EXPECTED_OUTPUTS),
        )
        for expected in LAUNCHER.EXPECTED_OUTPUTS.values():
            self.assertEqual(set(expected), {"trace"})
            size, digest = expected["trace"]
            self.assertGreater(size, 0)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(
            contract["trace_contract"]["screenshot_policy"],
            "supporting-presentation-only-not-an-acceptance-gate",
        )
        self.assertEqual(
            contract["trace_contract"]["nonzero_scenario_capture_phase"],
            "endFrame-after-terminal-input-poll",
        )
        self.assertEqual(
            contract["trace_contract"]["calibration_capture_phase"],
            "inputPolled-immediately-after-observer-arm",
        )
        self.assertEqual(
            contract["checkpoint"]["direct_page"],
            "0000",
        )
        self.assertEqual(
            contract["controls"]["ram_power_on_state"],
            "AllZeros",
        )
        self.assertEqual(
            contract["controls"]["fixed_rom_name"],
            "project_epoch_mesen_lavos_clean.sfc",
        )

        mutations = (
            (
                "schema",
                lambda row: row.__setitem__("schema", "v4"),
            ),
            (
                "checkpoint",
                lambda row: row["checkpoint"].__setitem__(
                    "direct_page",
                    "0100",
                ),
            ),
            (
                "timeline",
                lambda row: row["scenarios"][2]["inputs"][0].__setitem__(
                    "start_frame",
                    21,
                ),
            ),
            (
                "capture phase",
                lambda row: row["trace_contract"].__setitem__(
                    "calibration_capture_phase",
                    "endFrame",
                ),
            ),
            (
                "accepted output",
                lambda row: row["accepted_outputs"][0].__setitem__(
                    "trace_sha256",
                    "0" * 64,
                ),
            ),
            (
                "battle anchor",
                lambda row: row["battle_anchors"].__setitem__(
                    "battle_ids_hex",
                    "ff0102cdffffccffffffcb00",
                ),
            ),
            (
                "launch profile",
                lambda row: row["controls"].__setitem__(
                    "ram_power_on_state",
                    "Random",
                ),
            ),
        )
        for label, mutate in mutations:
            drifted = copy.deepcopy(contract)
            mutate(drifted)
            with self.subTest(label=label):
                with self.assertRaises(LAUNCHER.BASE.TraceLaunchError):
                    LAUNCHER._validate_scenario_contract(drifted)

    def test_derived_base_has_fixed_rom_name_allzeros_and_png_policy(
        self,
    ) -> None:
        source = LAUNCHER.BASE_LAUNCHER_PATH.read_text(encoding="utf-8")
        source = LAUNCHER._replace_once(
            source,
            'unique_stem = f"pe_wram_ownership_{secrets.token_hex(12)}"',
            'unique_stem = "project_epoch_mesen_lavos_clean"',
            "fixed ROM/SRAM stem",
        )
        source = LAUNCHER._replace_once(
            source,
            (
                '                "--snes.port1.type=SnesController",\n'
                "                str(staged_collector),\n"
            ),
            (
                '                "--snes.port1.type=SnesController",\n'
                '                "--snes.ramPowerOnState=AllZeros",\n'
                "                str(staged_collector),\n"
            ),
            "deterministic RAM launch profile",
        )
        source = LAUNCHER._replace_once(
            source,
            """\
                    describe_artifact_bytes(
                        screenshot_bytes,
                        "endpoint PNG",
                        png=True,
                        expected=expected_outputs["screenshot"],
                    )
""",
            """\
                    # Battle-v3 screenshots are presentation-only.  Their
                    # per-run hashes are retained, but they cannot gate trace
                    # acceptance because the renderer buffer varies.
""",
            "presentation-only screenshot policy",
        )
        derived = source.encode("utf-8")
        self.assertEqual(len(derived), LAUNCHER.DERIVED_BASE_LAUNCHER_SIZE)
        self.assertEqual(
            hashlib.sha256(derived).hexdigest(),
            LAUNCHER.DERIVED_BASE_LAUNCHER_SHA256,
        )
        self.assertIn(
            'unique_stem = "project_epoch_mesen_lavos_clean"',
            source,
        )
        self.assertIn("--snes.ramPowerOnState=AllZeros", source)
        self.assertNotIn(
            'expected=expected_outputs["screenshot"]',
            source,
        )

    def test_accepted_mode_without_pins_fails_before_private_resolution(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory).resolve() / "private"
            source_parent = private_root / "test_runs" / "mesen2"
            source_parent.mkdir(parents=True)
            args = LAUNCHER.build_parser().parse_args(
                [
                    "--scenario",
                    "battle-idle",
                    "--variant",
                    "zero",
                    "--output-dir",
                    str(private_root / "never-created"),
                ]
            )
            ancestry = {"synthetic": "exact"}
            with preserve_launcher_base_configuration():
                with (
                    mock.patch.object(
                        LAUNCHER,
                        "PRIVATE_ROOT",
                        private_root,
                    ),
                    mock.patch.object(
                        LAUNCHER,
                        "EXPECTED_OUTPUTS",
                        {},
                    ),
                    mock.patch.object(
                        LAUNCHER,
                        "_verify_ancestry",
                        return_value=ancestry,
                    ),
                    mock.patch.object(
                        LAUNCHER.BASE,
                        "resolve_private_file",
                        side_effect=AssertionError(
                            "private inputs must not resolve"
                        ),
                    ) as resolve_private,
                ):
                    with self.assertRaisesRegex(
                        LAUNCHER.BASE.TraceLaunchError,
                        "no accepted output contract",
                    ):
                        LAUNCHER.run(args)
            resolve_private.assert_not_called()
            self.assertFalse(os.path.lexists(args.output_dir))
            self.assertEqual(list(source_parent.iterdir()), [])

    def test_private_generated_source_staging_and_result_decoration(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory).resolve() / "private"
            source_parent = private_root / "test_runs" / "mesen2"
            source_parent.mkdir(parents=True)
            args = LAUNCHER.build_parser().parse_args(
                [
                    "--scenario",
                    "battle-command-down",
                    "--variant",
                    "canary",
                    "--output-dir",
                    str(private_root / "synthetic-output"),
                    "--exploratory",
                ]
            )
            ancestry = {Path("synthetic"): "exact"}
            observed_generated_path: Path | None = None

            def fake_base_run(
                observed_args: object,
            ) -> dict[str, object]:
                nonlocal observed_generated_path
                self.assertIs(observed_args, args)
                observed_generated_path = Path(LAUNCHER.BASE.COLLECTOR)
                self.assertTrue(observed_generated_path.is_file())
                observed_generated_path.relative_to(source_parent)
                self.assertEqual(
                    hashlib.sha256(
                        observed_generated_path.read_bytes()
                    ).hexdigest(),
                    LAUNCHER.GENERATED_COLLECTOR_SHA256,
                )
                self.assertEqual(
                    LAUNCHER.BASE.RUNTIME_HASHES["state"],
                    LAUNCHER.CHECKPOINT_SHA256,
                )
                self.assertEqual(
                    LAUNCHER.BASE.PINNED_SIZES["state"],
                    261_614,
                )
                return {
                    "status": "synthetic-private-run",
                    "trace": {},
                    "screenshot": {},
                }

            with preserve_launcher_base_configuration():
                with (
                    mock.patch.object(
                        LAUNCHER,
                        "PRIVATE_ROOT",
                        private_root,
                    ),
                    mock.patch.object(
                        LAUNCHER,
                        "_verify_ancestry",
                        side_effect=(ancestry, ancestry),
                    ) as verify_ancestry,
                    mock.patch.object(
                        LAUNCHER.BASE,
                        "run",
                        side_effect=fake_base_run,
                    ) as base_run,
                ):
                    result = LAUNCHER.run(args)

            verify_ancestry.assert_has_calls([mock.call(), mock.call()])
            base_run.assert_called_once_with(args)
            self.assertIsNotNone(observed_generated_path)
            assert observed_generated_path is not None
            self.assertFalse(os.path.lexists(observed_generated_path))
            self.assertEqual(list(source_parent.iterdir()), [])
            self.assertTrue(result["generated_collector_source_deleted"])
            self.assertEqual(
                result["launch_profile"],
                {
                    "fixed_rom_name": (
                        "project_epoch_mesen_lavos_clean.sfc"
                    ),
                    "ram_power_on_state": "AllZeros",
                },
            )
            self.assertEqual(
                result["trace"]["evidence_level"],
                "exploratory-verified-runtime",
            )
            self.assertEqual(
                result["screenshot"]["evidence_level"],
                "supporting-presentation-only",
            )
            self.assertFalse(
                result["screenshot"]["acceptance_gate"]
            )

    def test_private_generated_source_is_deleted_when_base_run_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory).resolve() / "private"
            source_parent = private_root / "test_runs" / "mesen2"
            source_parent.mkdir(parents=True)
            args = LAUNCHER.build_parser().parse_args(
                [
                    "--scenario",
                    "battle-idle",
                    "--variant",
                    "zero",
                    "--output-dir",
                    str(private_root / "synthetic-output"),
                    "--exploratory",
                ]
            )
            ancestry = {Path("synthetic"): "exact"}
            observed_generated_path: Path | None = None

            def fail_base_run(_args: object) -> dict[str, object]:
                nonlocal observed_generated_path
                observed_generated_path = Path(LAUNCHER.BASE.COLLECTOR)
                self.assertTrue(observed_generated_path.is_file())
                raise LAUNCHER.BASE.TraceLaunchError(
                    "synthetic base failure"
                )

            with preserve_launcher_base_configuration():
                with (
                    mock.patch.object(
                        LAUNCHER,
                        "PRIVATE_ROOT",
                        private_root,
                    ),
                    mock.patch.object(
                        LAUNCHER,
                        "_verify_ancestry",
                        return_value=ancestry,
                    ),
                    mock.patch.object(
                        LAUNCHER.BASE,
                        "run",
                        side_effect=fail_base_run,
                    ),
                ):
                    with self.assertRaisesRegex(
                        LAUNCHER.BASE.TraceLaunchError,
                        "synthetic base failure",
                    ):
                        LAUNCHER.run(args)

            self.assertIsNotNone(observed_generated_path)
            assert observed_generated_path is not None
            self.assertFalse(os.path.lexists(observed_generated_path))
            self.assertEqual(list(source_parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
