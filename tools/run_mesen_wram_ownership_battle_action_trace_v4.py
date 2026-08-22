#!/usr/bin/env python3
"""Run one isolated native-Mesen Lavos action/recovery ownership trace.

The launcher exact-loads the exploratory v4 launcher and substitutes the
bounded action collector, validator, and accepted scenario contract.
Disposable ROM/SRAM/state staging, immutable-input checks, shared-save
preservation, all-zero power-on RAM, exclusive output creation,
generated-source deletion, and presentation-only screenshots stay inherited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any, Final, Mapping


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
PROBE_LAUNCHER_PATH = (
    ROOT / "tools" / "run_mesen_wram_ownership_battle_action_probe_v4.py"
)
PROBE_LAUNCHER_SIZE: Final = 17_296
PROBE_LAUNCHER_SHA256: Final = (
    "98d67dfab86323958491b20c04845566"
    "4d0253f0de1f8eab551e39885b0527b7"
)

BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_action_collector_v4.py"
)
BUILDER_SIZE: Final = 14_769
BUILDER_SHA256: Final = (
    "6be1f408ceb04c8c211aa5365b92f3d9"
    "b0c5aa00354434bd431ac8c028057af8"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_action_trace_v4.py"
)
VALIDATOR_SIZE: Final = 20_306
VALIDATOR_SHA256: Final = (
    "f7f23cdb9c196d4d0642cf2bb9aa2040"
    "834bd89fb0a5bb6044f65218e6974b3c"
)
SCENARIO_CONTRACT_PATH = (
    ROOT
    / "references"
    / "mesen_wram_ownership_battle_action_scenarios_v4.json"
)
SCENARIO_CONTRACT_SIZE: Final = 12_552
SCENARIO_CONTRACT_SHA256: Final = (
    "ad6d686bdc01f93ce9abed3c21beb4a2"
    "bac5d5142883f94fc29c6e3f06c6f727"
)
REPLAY_VALIDATOR_PATH = (
    ROOT
    / "tools"
    / "validate_mesen_wram_ownership_battle_action_replay_v4.py"
)
REPLAY_VALIDATOR_SIZE: Final = 6_077
REPLAY_VALIDATOR_SHA256: Final = (
    "dbe2a1a0e2e2217f7379ed7d6e127674"
    "532a9aff5f6900de5a69ac62f89fb099"
)

GENERATED_COLLECTOR_SIZE: Final = 51_620
GENERATED_COLLECTOR_SHA256: Final = (
    "dc9a2cb3dc91fd9b4182511cec632773"
    "c8ed80725577fd4c1d15e3d719cde408"
)
TRACE_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-trace-v4"
)
SCENARIO_CONTRACT_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-scenarios-v4"
)
SCENARIOS: Final = (
    "battle-action-control",
    "battle-attack-target-hold",
    "battle-attack-recovery",
)
VARIANTS: Final = ("zero", "canary")
EXPECTED_OUTPUTS: Final = {
    ("battle-action-control", "zero"): {
        "trace": (
            192_051,
            "2d0b222b0f7e0151108e9c8471b89536"
            "56e2e1a064e3b4c8b69e33e274150569",
        ),
    },
    ("battle-action-control", "canary"): {
        "trace": (
            198_801,
            "885299cd5066c4f7bd3b46a4411bab3a"
            "42e4e3e07234e1b6057b5606b90ddb35",
        ),
    },
    ("battle-attack-target-hold", "zero"): {
        "trace": (
            24_788,
            "fc4264a8fe5df5dff4e34b0ab4bf80cf"
            "8787c04395f80658aff421c9e220dd03",
        ),
    },
    ("battle-attack-target-hold", "canary"): {
        "trace": (
            31_538,
            "ca3fd8d70f8555362554cefbd66a69b74"
            "bcc379e7f83c834b49b455da0bb2398",
        ),
    },
    ("battle-attack-recovery", "zero"): {
        "trace": (
            150_494,
            "cc0e37b6f1c14377d8b5c1e5870a6368"
            "7e2136a11fc2a7b90211c2efa11e14e0",
        ),
    },
    ("battle-attack-recovery", "canary"): {
        "trace": (
            157_244,
            "655e5fab21c48983968aa3616de10837f"
            "85cee31234767354e35fba4549713fa",
        ),
    },
}

CHECKPOINT_SHA256: Final = (
    "d5825ffff2f2a3b7edbe3c37e711815"
    "5d67727dc02ed672d13257f3824482b8b"
)
SRAM_SHA256: Final = (
    "cc5fa36da8185128e510c63f637842c7"
    "7cf09dde413a196c3ab770656abff203"
)
DEFAULT_MESEN = PRIVATE_ROOT / "tools" / "mesen2" / "app" / "Mesen.exe"
DEFAULT_ROM = (
    PRIVATE_ROOT / "input" / "rom_archive" / "Chrono Trigger (USA).sfc"
)
DEFAULT_STATE = (
    PRIVATE_ROOT
    / "test_runs"
    / "mesen2"
    / "lavos_battle_checkpoint_accepted_v1"
    / "battle_ready.mss"
)
DEFAULT_SRAM = (
    PRIVATE_ROOT / "input" / "lavos_save" / "chrono_trigger.srm"
)


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_exact_module(
    name: str,
    path: Path,
    *,
    size: int,
    sha256: str,
) -> types.ModuleType:
    source = path.read_bytes()
    if len(source) != size:
        raise RuntimeError(
            f"{path.name} size drifted: expected {size}, got {len(source)}"
        )
    actual = _sha256_bytes(source)
    if actual != sha256:
        raise RuntimeError(
            f"{path.name} SHA-256 drifted: expected {sha256}, got {actual}"
        )
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


PROBE = _load_exact_module(
    "_project_epoch_action_probe_launcher_for_action_v4",
    PROBE_LAUNCHER_PATH,
    size=PROBE_LAUNCHER_SIZE,
    sha256=PROBE_LAUNCHER_SHA256,
)
BUILDER = _load_exact_module(
    "_project_epoch_battle_action_builder_v4",
    BUILDER_PATH,
    size=BUILDER_SIZE,
    sha256=BUILDER_SHA256,
)
V3 = PROBE.V3
TraceLaunchError = PROBE.TraceLaunchError


ANCESTRY_PINS: Final = {
    **PROBE.ANCESTRY_PINS,
    PROBE_LAUNCHER_PATH: PROBE_LAUNCHER_SHA256,
    BUILDER_PATH: BUILDER_SHA256,
    VALIDATOR_PATH: VALIDATOR_SHA256,
    REPLAY_VALIDATOR_PATH: REPLAY_VALIDATOR_SHA256,
    SCENARIO_CONTRACT_PATH: SCENARIO_CONTRACT_SHA256,
}


def _verify_ancestry() -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path, expected in ANCESTRY_PINS.items():
        actual = _sha256_file(path)
        if actual != expected:
            raise TraceLaunchError(
                f"battle-action-v4 ancestry drifted at {path}: "
                f"expected {expected}, got {actual}"
            )
        result[path] = actual
    return result


def _expected_contract_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "name": scenario.name,
            "terminal_frame": scenario.terminal_frame,
            "expected_access_class": scenario.expected_access_class,
            "inputs": [
                {
                    "button": pulse.json_button,
                    "start_frame": pulse.start_frame,
                    "end_frame": pulse.end_frame,
                }
                for pulse in scenario.pulses
            ],
        }
        for scenario in BUILDER.SCENARIOS
    ]


EXPECTED_ENDPOINT_CONTRACTS: Final = {
    "battle-action-control": {
        "timeline_rows": 269,
        "last_signature_frame": 603,
        "terminal_frame": 606,
        "battle_current_hp": [739, 821, 712, 8000, 12000, 20000],
        "battle_ui_hex": "03bf59",
        "command_state_hex": "00000000000102000300000000",
        "causal_milestones": [
            "frame-336-enemy-action-damages-only-party",
            "frame-363-follow-on-action-request-transition",
        ],
    },
    "battle-attack-target-hold": {
        "timeline_rows": 17,
        "last_signature_frame": 60,
        "terminal_frame": 60,
        "battle_current_hp": [969, 898, 909, 8000, 12000, 20000],
        "battle_ui_hex": "0059ac",
        "command_state_hex": "0000000000ffff000100000000",
        "causal_milestones": [
            "frame-20-attack-target-selection-state",
        ],
    },
    "battle-attack-recovery": {
        "timeline_rows": 206,
        "last_signature_frame": 606,
        "terminal_frame": 606,
        "battle_current_hp": [739, 821, 712, 7038, 12000, 20000],
        "battle_ui_hex": "003a00",
        "command_state_hex": "01000000ff01ff010100000000",
        "causal_milestones": [
            "frame-32-player-command-enqueue",
            "frame-337-enemy-action-damages-only-party",
            "frame-373-player-command-dequeue",
            "frame-375-crono-critical-marker-ae9b-bit-80",
            "frame-557-player-attack-damages-enemy-slot-3",
            "frame-606-command-ready-recovery",
        ],
    },
}


EXPECTED_SOURCE_PINS: Final = {
    "v3_collector_builder": (
        "tools/build_mesen_wram_ownership_battle_collector_v3.py",
        21_160,
        "443d521ffa435ffddaa2b9ebdd68bc66c22b144e125fe91e9bebef38817cdf91",
    ),
    "v3_generated_collector": (
        None,
        41_269,
        "7491d1c6a8a3962884baeaf9997df4659c4a53d3f67b3c6ac69999d08f6ee68b",
    ),
    "probe_collector_builder": (
        "tools/build_mesen_wram_ownership_battle_action_probe_v4.py",
        PROBE.BUILDER_SIZE,
        PROBE.BUILDER_SHA256,
    ),
    "probe_generated_collector": (
        None,
        PROBE.GENERATED_COLLECTOR_SIZE,
        PROBE.GENERATED_COLLECTOR_SHA256,
    ),
    "collector_builder": (
        "tools/build_mesen_wram_ownership_battle_action_collector_v4.py",
        BUILDER_SIZE,
        BUILDER_SHA256,
    ),
    "generated_collector": (
        None,
        GENERATED_COLLECTOR_SIZE,
        GENERATED_COLLECTOR_SHA256,
    ),
    "v3_validator": (
        "tools/validate_mesen_wram_ownership_battle_trace_v3.py",
        20_095,
        PROBE.V3_VALIDATOR_SHA256,
    ),
    "probe_validator": (
        "tools/validate_mesen_wram_ownership_battle_action_probe_v4.py",
        PROBE.VALIDATOR_SIZE,
        PROBE.VALIDATOR_SHA256,
    ),
    "validator": (
        "tools/validate_mesen_wram_ownership_battle_action_trace_v4.py",
        VALIDATOR_SIZE,
        VALIDATOR_SHA256,
    ),
    "replay_validator": (
        "tools/validate_mesen_wram_ownership_battle_action_replay_v4.py",
        REPLAY_VALIDATOR_SIZE,
        REPLAY_VALIDATOR_SHA256,
    ),
    "v3_launcher": (
        "tools/run_mesen_wram_ownership_battle_trace_v3.py",
        PROBE.V3_LAUNCHER_SIZE,
        PROBE.V3_LAUNCHER_SHA256,
    ),
    "probe_launcher": (
        "tools/run_mesen_wram_ownership_battle_action_probe_v4.py",
        PROBE_LAUNCHER_SIZE,
        PROBE_LAUNCHER_SHA256,
    ),
}


def _validate_scenario_contract(contract: Mapping[str, Any]) -> None:
    if (
        contract.get("schema") != SCENARIO_CONTRACT_SCHEMA
        or contract.get("version") != 4
        or contract.get("acceptance_status")
        != "accepted-exact-trace-hashes"
        or contract.get("evidence_level")
        != "verified-runtime"
    ):
        raise TraceLaunchError("battle-action-v4 evidence status drifted")

    trace = contract.get("trace_contract")
    if (
        not isinstance(trace, dict)
        or trace.get("schema") != TRACE_SCHEMA
        or trace.get("collector_version") != 4
        or trace.get("trace_count") != 6
        or trace.get("variants") != list(VARIANTS)
        or trace.get("capture_phase")
        != "endFrame-after-terminal-input-poll"
        or trace.get("timeline_policy")
        != "frame-zero-plus-signature-changes-only"
        or trace.get("screenshot_policy")
        != "supporting-presentation-only-not-an-acceptance-gate"
    ):
        raise TraceLaunchError("battle-action-v4 trace contract drifted")

    checkpoint = contract.get("checkpoint")
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("id")
        != "lavos-core-command-ready-canonical-v1"
        or checkpoint.get("private_path")
        != (
            "private/test_runs/mesen2/"
            "lavos_battle_checkpoint_accepted_v1/battle_ready.mss"
        )
        or checkpoint.get("size") != 261_614
        or checkpoint.get("sha256") != CHECKPOINT_SHA256
        or checkpoint.get("source_frame") != 5_651
        or checkpoint.get("direct_page") != "0000"
        or checkpoint.get("location") != "01DB"
        or checkpoint.get("decoded_state_size") != 324_388
        or checkpoint.get("decoded_state_sha256")
        != (
            "8369e220290e1afc27138df5a1f999de"
            "e83cb4fdb462bc13c152ef1c313ecf4c"
        )
    ):
        raise TraceLaunchError("battle-action-v4 checkpoint contract drifted")

    sources = contract.get("sources")
    if (
        not isinstance(sources, dict)
        or set(sources) != set(EXPECTED_SOURCE_PINS)
    ):
        raise TraceLaunchError("battle-action-v4 source set drifted")
    for key, (path, size, digest) in EXPECTED_SOURCE_PINS.items():
        row = sources.get(key)
        if (
            not isinstance(row, dict)
            or row.get("size") != size
            or row.get("sha256") != digest
            or (path is not None and row.get("path") != path)
        ):
            raise TraceLaunchError(f"battle-action-v4 {key} pin drifted")
    generated_policies = {
        "v3_generated_collector": "compiled_in_memory_only",
        "probe_generated_collector": "compiled_in_memory_only",
        "generated_collector": "staged_private_only",
    }
    if any(
        sources[key].get(policy) is not True
        for key, policy in generated_policies.items()
    ) or sources["generated_collector"].get("deleted_after_each_run") is not True:
        raise TraceLaunchError("battle-action-v4 source policy drifted")

    private_inputs = contract.get("private_inputs")
    if (
        not isinstance(private_inputs, dict)
        or private_inputs.get("canonical_rom_size") != 4_194_304
        or private_inputs.get("canonical_rom_sha256")
        != (
            "06d1c2b06b716052c5596aaa0c2e5632"
            "a027fee1a9a28439e509f813c30829a9"
        )
        or private_inputs.get("recovered_lavos_sram_size") != 8_192
        or private_inputs.get("recovered_lavos_sram_sha256") != SRAM_SHA256
    ):
        raise TraceLaunchError("battle-action-v4 private-input pins drifted")

    scenarios = contract.get("scenarios")
    actual_scenarios = [
        {
            "name": row.get("name"),
            "terminal_frame": row.get("terminal_frame"),
            "expected_access_class": row.get("expected_access_class"),
            "inputs": row.get("inputs"),
        }
        for row in scenarios
        if isinstance(row, dict)
    ] if isinstance(scenarios, list) else []
    if actual_scenarios != _expected_contract_scenarios():
        raise TraceLaunchError("battle-action-v4 scenario timelines drifted")
    if contract.get("endpoint_contracts") != EXPECTED_ENDPOINT_CONTRACTS:
        raise TraceLaunchError("battle-action-v4 endpoint contract drifted")
    expected_accepted_outputs = [
        {
            "scenario": scenario,
            "variant": variant,
            "trace_size": EXPECTED_OUTPUTS[(scenario, variant)]["trace"][0],
            "trace_sha256": EXPECTED_OUTPUTS[(scenario, variant)]["trace"][1],
        }
        for scenario in SCENARIOS
        for variant in VARIANTS
    ]
    if contract.get("accepted_outputs") != expected_accepted_outputs:
        raise TraceLaunchError("battle-action-v4 accepted outputs drifted")
    if contract.get("replay_contract") != {
        "schema": (
            "project-epoch-mesen-wram-ownership-battle-action-replay-v4"
        ),
        "trace_count_per_root": 6,
        "semantic_validation_required_for_each_root": True,
        "exact_trace_byte_identity_required": True,
        "screenshots_in_acceptance_gate": False,
    }:
        raise TraceLaunchError("battle-action-v4 replay contract drifted")

    preimage = contract.get("battle_preimage")
    if (
        not isinstance(preimage, dict)
        or preimage.get("active_party_hex") != "000102"
        or preimage.get("roster_hex") != "000102828004030605"
        or preimage.get("joined_hex") != "FE"
        or preimage.get("battle_ids_hex")
        != "000102cdffffccffffffcb00"
        or preimage.get("battle_current_and_max_hp")
        != [969, 898, 909, 8000, 12000, 20000]
        or preimage.get("battle_ui_hex") != "0059ac"
        or preimage.get("command_state_hex")
        != "0000000000ffff000100000000"
        or preimage.get("inflight_action_request_hex")
        != "0003024300008006ff006000"
        or preimage.get("inflight_action_targets_hex")
        != "03000102ffffffffffffffff"
        or preimage.get("logic_busy_hex")
        != "01000000000000010b0001"
    ):
        raise TraceLaunchError("battle-action-v4 preimage anchors drifted")

    watched = contract.get("watched_ranges")
    expected_ranges = [
        ("old-compatibility", "7E2830", "7E287F", 80),
        ("roster", "7E2980", "7E2988", 9),
        ("joined", "7E29AF", "7E29AF", 1),
        ("epoch-name", "7E2C4D", "7E2C52", 6),
        ("front-guard", "7E2C9C", "7E2C9F", 4),
        ("candidate", "7E2CA0", "7E2CEF", 80),
        ("rear-guard", "7E2CF0", "7E2CFF", 16),
    ]
    actual_ranges = [
        (
            row.get("name"),
            row.get("start"),
            row.get("end"),
            row.get("length"),
        )
        for row in watched
        if isinstance(row, dict)
    ] if isinstance(watched, list) else []
    if actual_ranges != expected_ranges:
        raise TraceLaunchError("battle-action-v4 watched ranges drifted")

    controls = contract.get("controls")
    required_true = {
        "zero_canary_pair_identity_required",
        "candidate_canary_written_before_observers_arm",
        "candidate_and_guards_zero_access_required",
        "roster_joined_epoch_writes_forbidden",
        "old_compatibility_writes_forbidden",
        "counter_callback_reconciliation_required",
        "all_pre_snapshots_share_one_checkpoint_required",
        "independent_replay_trace_identity_required",
        "generated_collector_private_and_deleted",
        "immutable_inputs_and_shared_saves_required",
        "no_rom_sram_or_state_write_api_added",
        "no_lavos_victory_or_teardown_claim",
    }
    if (
        not isinstance(controls, dict)
        or any(controls.get(key) is not True for key in required_true)
        or controls.get("ram_power_on_state") != "AllZeros"
        or controls.get("fixed_rom_name")
        != "project_epoch_mesen_lavos_clean.sfc"
    ):
        raise TraceLaunchError("battle-action-v4 safety controls drifted")


def _configure_v3_module() -> None:
    V3.BUILDER = BUILDER
    V3.BUILDER_PATH = BUILDER_PATH
    V3.BUILDER_SIZE = BUILDER_SIZE
    V3.BUILDER_SHA256 = BUILDER_SHA256
    V3.VALIDATOR_PATH = VALIDATOR_PATH
    V3.VALIDATOR_SIZE = VALIDATOR_SIZE
    V3.VALIDATOR_SHA256 = VALIDATOR_SHA256
    V3.SCENARIO_CONTRACT_PATH = SCENARIO_CONTRACT_PATH
    V3.SCENARIO_CONTRACT_SIZE = SCENARIO_CONTRACT_SIZE
    V3.SCENARIO_CONTRACT_SHA256 = SCENARIO_CONTRACT_SHA256
    V3.GENERATED_COLLECTOR_SIZE = GENERATED_COLLECTOR_SIZE
    V3.GENERATED_COLLECTOR_SHA256 = GENERATED_COLLECTOR_SHA256
    V3.TRACE_SCHEMA = TRACE_SCHEMA
    V3.SCENARIO_CONTRACT_SCHEMA = SCENARIO_CONTRACT_SCHEMA
    V3.SCENARIOS = SCENARIOS
    V3.VARIANTS = VARIANTS
    V3.EXPECTED_OUTPUTS = EXPECTED_OUTPUTS
    V3.ANCESTRY_PINS = ANCESTRY_PINS
    V3._verify_ancestry = _verify_ancestry
    V3._validate_scenario_contract = _validate_scenario_contract


_configure_v3_module()


def run(args: argparse.Namespace) -> dict[str, Any]:
    result = V3.run(args)
    result["status"] = (
        "exploratory-battle-action-exact-endpoint-trace"
        if args.exploratory
        else "accepted-battle-action-exact-trace"
    )
    result["accepted_evidence"] = not args.exploratory
    result["action_contract_sha256"] = SCENARIO_CONTRACT_SHA256
    result["limitations"] = [
        "acceptance is bounded to this exact scenario and JSON trace hash",
        "player route is one Crono critical Attack, not a noncritical matrix",
        "no Lavos victory or battle teardown claim",
        "no WRAM allocation or relocation approval",
    ]
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="retain strict controls but do not make an acceptance claim",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except (
        OSError,
        RuntimeError,
        ValueError,
        TraceLaunchError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
