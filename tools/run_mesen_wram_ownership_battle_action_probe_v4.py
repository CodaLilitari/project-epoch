#!/usr/bin/env python3
"""Run one isolated zero-only native-Mesen Lavos action discovery probe.

This launcher cannot produce accepted evidence.  It exact-loads the v3
battle launcher, substitutes the pinned v4 builder/validator/contract, and
retains disposable ROM/SRAM/state staging, immutable-input postchecks,
shared-save preservation, fixed ROM naming, all-zero power-on RAM, exclusive
output creation, generated-source deletion, and presentation-only screenshots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import types
from typing import Any, Final, Mapping


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
V3_LAUNCHER_PATH = (
    ROOT / "tools" / "run_mesen_wram_ownership_battle_trace_v3.py"
)
V3_LAUNCHER_SIZE: Final = 23_798
V3_LAUNCHER_SHA256: Final = (
    "ed3bc349bc97705a434c2cef14e7f80c"
    "517a2a5ca143f40a4c77ccb84eb49095"
)
V3_BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_collector_v3.py"
)
V3_BUILDER_SHA256: Final = (
    "443d521ffa435ffddaa2b9ebdd68bc66"
    "c22b144e125fe91e9bebef38817cdf91"
)
V3_VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_trace_v3.py"
)
V3_VALIDATOR_SHA256: Final = (
    "b5ecc2c3cd81d34e5cc94428fcd45bbd"
    "39496c4ba1080a97db3c47380a6f5155"
)

BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_action_probe_v4.py"
)
BUILDER_SIZE: Final = 16_877
BUILDER_SHA256: Final = (
    "d50ebfe12ec81c318b61aa189a30ca04"
    "eeadba181c1d43a3300e58b26f50ca6e"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_action_probe_v4.py"
)
VALIDATOR_SIZE: Final = 18_791
VALIDATOR_SHA256: Final = (
    "5da3bbdc8817085a302eba7426f1b6b54"
    "54096dd5e0e6caa9de7cfa2564c6921"
)
SCENARIO_CONTRACT_PATH = (
    ROOT
    / "references"
    / "mesen_wram_ownership_battle_action_probe_scenarios_v4.json"
)
SCENARIO_CONTRACT_SIZE: Final = 8_027
SCENARIO_CONTRACT_SHA256: Final = (
    "9596c869550a279feb57d8f69746dc5b"
    "2aa067ff2c8953f79243fbd6c2b09d3e"
)

GENERATED_COLLECTOR_SIZE: Final = 46_650
GENERATED_COLLECTOR_SHA256: Final = (
    "8957872bb9a32931be6a8e1f56d0a953"
    "a605659e30b6d77d2d1ec14de52a1e65"
)
TRACE_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-probe-trace-v4"
)
SCENARIO_CONTRACT_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-action-probe-scenarios-v4"
)
SCENARIOS: Final = (
    "enemy-inflight-resolution",
    "attack-target-hold",
    "attack-action-horizon",
)
VARIANTS: Final = ("zero",)
EXPECTED_OUTPUTS: Final = {}

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
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read pinned source: {path}") from exc
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


V3 = _load_exact_module(
    "_project_epoch_battle_launcher_v3_for_action_probe_v4",
    V3_LAUNCHER_PATH,
    size=V3_LAUNCHER_SIZE,
    sha256=V3_LAUNCHER_SHA256,
)
BUILDER = _load_exact_module(
    "_project_epoch_battle_action_probe_builder_v4",
    BUILDER_PATH,
    size=BUILDER_SIZE,
    sha256=BUILDER_SHA256,
)
TraceLaunchError = V3.BASE.TraceLaunchError


ANCESTRY_PINS: Final = {
    V3_LAUNCHER_PATH: V3_LAUNCHER_SHA256,
    V3_BUILDER_PATH: V3_BUILDER_SHA256,
    V3_VALIDATOR_PATH: V3_VALIDATOR_SHA256,
    BUILDER_PATH: BUILDER_SHA256,
    VALIDATOR_PATH: VALIDATOR_SHA256,
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


def _validate_scenario_contract(contract: Mapping[str, Any]) -> None:
    if contract.get("schema") != SCENARIO_CONTRACT_SCHEMA:
        raise TraceLaunchError("battle-action-v4 scenario schema drifted")
    if contract.get("version") != 4:
        raise TraceLaunchError("battle-action-v4 scenario version drifted")
    if (
        contract.get("acceptance_status")
        != "exploratory-zero-only-no-accepted-hashes"
        or contract.get("evidence_level")
        != "hypothesis-pending-runtime-probe"
    ):
        raise TraceLaunchError("battle-action-v4 evidence status drifted")

    trace = contract.get("trace_contract")
    if (
        not isinstance(trace, dict)
        or trace.get("schema") != TRACE_SCHEMA
        or trace.get("collector_version") != 4
        or trace.get("trace_count") != 3
        or trace.get("variants") != ["zero"]
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

    expected_sources = {
        "v3_collector_builder": (
            "tools/build_mesen_wram_ownership_battle_collector_v3.py",
            21_160,
            V3_BUILDER_SHA256,
        ),
        "v3_generated_collector": (
            None,
            41_269,
            (
                "7491d1c6a8a3962884baeaf9997df465"
                "9c4a53d3f67b3c6ac69999d08f6ee68b"
            ),
        ),
        "collector_builder": (
            "tools/build_mesen_wram_ownership_battle_action_probe_v4.py",
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
            V3_VALIDATOR_SHA256,
        ),
        "validator": (
            "tools/validate_mesen_wram_ownership_battle_action_probe_v4.py",
            VALIDATOR_SIZE,
            VALIDATOR_SHA256,
        ),
        "v3_launcher": (
            "tools/run_mesen_wram_ownership_battle_trace_v3.py",
            V3_LAUNCHER_SIZE,
            V3_LAUNCHER_SHA256,
        ),
    }
    sources = contract.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(expected_sources):
        raise TraceLaunchError("battle-action-v4 source set drifted")
    for key, (path, size, digest) in expected_sources.items():
        row = sources.get(key)
        if (
            not isinstance(row, dict)
            or row.get("size") != size
            or row.get("sha256") != digest
            or (path is not None and row.get("path") != path)
        ):
            raise TraceLaunchError(f"battle-action-v4 {key} pin drifted")
    if (
        sources["v3_generated_collector"].get("compiled_in_memory_only")
        is not True
        or sources["generated_collector"].get("staged_private_only")
        is not True
        or sources["generated_collector"].get("deleted_after_each_run")
        is not True
    ):
        raise TraceLaunchError(
            "battle-action-v4 generated-source policy drifted"
        )

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
        "zero_variant_only",
        "accepted_mode_forbidden",
        "candidate_and_guards_zero_access_required",
        "roster_joined_epoch_writes_forbidden",
        "old_compatibility_writes_forbidden",
        "counter_callback_reconciliation_required",
        "all_pre_snapshots_share_one_checkpoint_required",
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
    if not args.exploratory:
        raise TraceLaunchError(
            "battle-action v4 is an exploratory zero-only probe; "
            "--exploratory is required and accepted mode is forbidden"
        )
    args.variant = "zero"
    result = V3.run(args)
    result["status"] = "exploratory-zero-only-battle-action-probe"
    result["variant"] = "zero"
    result["accepted_evidence"] = False
    result["probe_contract_sha256"] = SCENARIO_CONTRACT_SHA256
    result["limitations"] = [
        "fixed horizons are discovery endpoints, not accepted action predicates",
        "no Lavos victory or battle teardown claim",
        "no WRAM allocation or relocation approval",
    ]
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="required; this provisional v4 launcher has no accepted mode",
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
