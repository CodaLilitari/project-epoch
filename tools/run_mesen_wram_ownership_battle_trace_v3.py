#!/usr/bin/env python3
"""Run one isolated derived native-Mesen Lavos battle ownership trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from typing import Any, Final, Mapping


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
BASE_LAUNCHER_PATH = ROOT / "tools" / "run_mesen_wram_ownership_trace.py"
BASE_LAUNCHER_SIZE: Final = 40_447
BASE_LAUNCHER_SHA256: Final = (
    "80f25f577da219d383829dfc977564d8"
    "295d1e0691ae4a2823da3e41079fa203"
)
DERIVED_BASE_LAUNCHER_SIZE: Final = 40_460
DERIVED_BASE_LAUNCHER_SHA256: Final = (
    "a2ce3b712edaa8e270c2cbcf08229dd8"
    "ad5b7b03654f2d805549c3ebd9ae10cf"
)
BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_battle_collector_v3.py"
)
BUILDER_SIZE: Final = 21_160
BUILDER_SHA256: Final = (
    "443d521ffa435ffddaa2b9ebdd68bc66"
    "c22b144e125fe91e9bebef38817cdf91"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_battle_trace_v3.py"
)
VALIDATOR_SIZE: Final = 20_095
VALIDATOR_SHA256: Final = (
    "b5ecc2c3cd81d34e5cc94428fcd45bbd"
    "39496c4ba1080a97db3c47380a6f5155"
)
SCENARIO_CONTRACT_PATH = (
    ROOT / "references" / "mesen_wram_ownership_battle_scenarios_v3.json"
)
SCENARIO_CONTRACT_SIZE: Final = 7_042
SCENARIO_CONTRACT_SHA256: Final = (
    "934e56f08585e315c37287f935177347"
    "3125874f6ca6296f10e0af746c20f83a"
)
GENERATED_COLLECTOR_SIZE: Final = 41_269
GENERATED_COLLECTOR_SHA256: Final = (
    "7491d1c6a8a3962884baeaf9997df465"
    "9c4a53d3f67b3c6ac69999d08f6ee68b"
)

TRACE_SCHEMA: Final = "project-epoch-mesen-wram-ownership-battle-trace-v3"
SCENARIO_CONTRACT_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-battle-scenarios-v3"
)
SCENARIOS: Final = (
    "calibration",
    "battle-idle",
    "battle-command-roundtrip",
    "battle-command-down",
)
VARIANTS: Final = ("zero", "canary")
EXPECTED_OUTPUTS: Final = {
    ("calibration", "zero"): {
        "trace": (
            13_396,
            "b4eb138e3403bef904dcd30017840263"
            "5fc87f13f794c1f3fdfce8f0a6d0e78d",
        ),
    },
    ("calibration", "canary"): {
        "trace": (
            20_146,
            "0d024d4470ea38d18520b9b2bc177f6"
            "7efc9d259ba4cc580bd8cc796ce38d1dc",
        ),
    },
    ("battle-idle", "zero"): {
        "trace": (
            13_418,
            "b58ac92a65796b771075eb9547e55114"
            "cf6bbee276972a82aca861c065d17498",
        ),
    },
    ("battle-idle", "canary"): {
        "trace": (
            20_168,
            "febe03672487cd2e53e1ea9271e5a421"
            "cf0149fec8207e5e84f8bdb9272a76cf",
        ),
    },
    ("battle-command-roundtrip", "zero"): {
        "trace": (
            13_546,
            "4e46c7cc583f61fffe8d1b056d989c8"
            "afb87f5c162a2dc047840a4e2d1a38387",
        ),
    },
    ("battle-command-roundtrip", "canary"): {
        "trace": (
            20_296,
            "dd9c0d336b4d5094f2f4c915ff96d204"
            "f55572965811606fe86fa8b4dac94988",
        ),
    },
    ("battle-command-down", "zero"): {
        "trace": (
            13_484,
            "400d34011e92910a5cec0053db79fbcf"
            "bbb94d534480fe50c79f6509573b86ed",
        ),
    },
    ("battle-command-down", "canary"): {
        "trace": (
            20_234,
            "0630f040c03f2d4a205628a42b024ff9"
            "3e5bdd266a7f8a32f521153bba32f4bb",
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


def _require_pinned_source(
    path: Path,
    *,
    size: int,
    sha256: str,
    label: str,
) -> bytes:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read pinned {label}: {path}") from exc
    if len(source) != size:
        raise RuntimeError(
            f"{label} size drifted: expected {size}, got {len(source)}"
        )
    actual = _sha256_bytes(source)
    if actual != sha256:
        raise RuntimeError(
            f"{label} SHA-256 drifted: expected {sha256}, got {actual}"
        )
    return source


def _load_exact_module(
    name: str,
    path: Path,
    *,
    size: int,
    sha256: str,
) -> types.ModuleType:
    source = _require_pinned_source(
        path,
        size=size,
        sha256=sha256,
        label=path.name,
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


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label} base-launcher preimage must occur once, found {count}"
        )
    return source.replace(old, new, 1)


def _load_derived_base() -> types.ModuleType:
    source = _require_pinned_source(
        BASE_LAUNCHER_PATH,
        size=BASE_LAUNCHER_SIZE,
        sha256=BASE_LAUNCHER_SHA256,
        label="accepted ownership launcher v1",
    ).decode("utf-8")
    source = _replace_once(
        source,
        'unique_stem = f"pe_wram_ownership_{secrets.token_hex(12)}"',
        'unique_stem = "project_epoch_mesen_lavos_clean"',
        "fixed ROM/SRAM stem",
    )
    source = _replace_once(
        source,
        """\
                "--snes.port1.type=SnesController",
                str(staged_collector),
""",
        """\
                "--snes.port1.type=SnesController",
                "--snes.ramPowerOnState=AllZeros",
                str(staged_collector),
""",
        "deterministic RAM launch profile",
    )
    source = _replace_once(
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
    if len(derived) != DERIVED_BASE_LAUNCHER_SIZE:
        raise RuntimeError("derived ownership launcher size drifted")
    actual = _sha256_bytes(derived)
    if actual != DERIVED_BASE_LAUNCHER_SHA256:
        raise RuntimeError(
            "derived ownership launcher SHA-256 drifted: "
            f"expected {DERIVED_BASE_LAUNCHER_SHA256}, got {actual}"
        )
    code = compile(
        derived,
        f"{BASE_LAUNCHER_PATH}#battle-v3-derived",
        "exec",
        dont_inherit=True,
    )
    module = types.ModuleType(
        "_project_epoch_wram_ownership_launcher_v1_for_battle_v3"
    )
    module.__file__ = str(BASE_LAUNCHER_PATH)
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    exec(code, module.__dict__)
    return module


BASE = _load_derived_base()
BUILDER = _load_exact_module(
    "_project_epoch_wram_ownership_battle_collector_builder_v3",
    BUILDER_PATH,
    size=BUILDER_SIZE,
    sha256=BUILDER_SHA256,
)


ANCESTRY_PINS: Final = {
    BASE_LAUNCHER_PATH: BASE_LAUNCHER_SHA256,
    ROOT / "tools" / "mesen_wram_ownership_trace.lua": (
        "d5dd2b2d7085237844d95ab04f7007b6"
        "b2d17b2e1160f23857018319380b7569"
    ),
    ROOT / "tools" / "validate_mesen_wram_ownership_trace.py": (
        "89a7dc86c6b5b10dc984b778451152e4"
        "734b5c553a669b7ee033e465ca87f2ba"
    ),
    BUILDER_PATH: BUILDER_SHA256,
    VALIDATOR_PATH: VALIDATOR_SHA256,
    SCENARIO_CONTRACT_PATH: SCENARIO_CONTRACT_SHA256,
}


def _verify_ancestry() -> dict[Path, str]:
    result: dict[Path, str] = {}
    for path, expected in ANCESTRY_PINS.items():
        actual = _sha256_file(path)
        if actual != expected:
            raise BASE.TraceLaunchError(
                f"battle-v3 ancestry drifted at {path}: "
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
        raise BASE.TraceLaunchError("battle-v3 scenario schema drifted")
    if contract.get("version") != 3:
        raise BASE.TraceLaunchError("battle-v3 scenario version drifted")
    if contract.get("acceptance_status") != "accepted-exact-trace-hashes":
        raise BASE.TraceLaunchError("battle-v3 acceptance status drifted")
    if contract.get("evidence_level") != "verified-runtime":
        raise BASE.TraceLaunchError("battle-v3 evidence level drifted")

    trace = contract.get("trace_contract")
    if (
        not isinstance(trace, dict)
        or trace.get("schema") != TRACE_SCHEMA
        or trace.get("collector_version") != 3
        or trace.get("trace_count") != 8
        or trace.get("variants") != list(VARIANTS)
        or trace.get("nonzero_scenario_capture_phase")
        != "endFrame-after-terminal-input-poll"
        or trace.get("calibration_capture_phase")
        != "inputPolled-immediately-after-observer-arm"
        or trace.get("screenshot_policy")
        != "supporting-presentation-only-not-an-acceptance-gate"
    ):
        raise BASE.TraceLaunchError("battle-v3 trace contract drifted")

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
        raise BASE.TraceLaunchError("battle-v3 checkpoint contract drifted")

    sources = contract.get("sources")
    expected_sources = {
        "base_collector": (
            "tools/mesen_wram_ownership_trace.lua",
            40_088,
            (
                "d5dd2b2d7085237844d95ab04f7007b6"
                "b2d17b2e1160f23857018319380b7569"
            ),
        ),
        "collector_builder": (
            "tools/build_mesen_wram_ownership_battle_collector_v3.py",
            BUILDER_SIZE,
            BUILDER_SHA256,
        ),
        "base_validator": (
            "tools/validate_mesen_wram_ownership_trace.py",
            29_388,
            (
                "89a7dc86c6b5b10dc984b778451152e4"
                "734b5c553a669b7ee033e465ca87f2ba"
            ),
        ),
        "validator": (
            "tools/validate_mesen_wram_ownership_battle_trace_v3.py",
            VALIDATOR_SIZE,
            VALIDATOR_SHA256,
        ),
        "base_launcher": (
            "tools/run_mesen_wram_ownership_trace.py",
            BASE_LAUNCHER_SIZE,
            BASE_LAUNCHER_SHA256,
        ),
    }
    if not isinstance(sources, dict):
        raise BASE.TraceLaunchError("battle-v3 source pins are missing")
    for key, (path, size, digest) in expected_sources.items():
        row = sources.get(key)
        if (
            not isinstance(row, dict)
            or row.get("path") != path
            or row.get("size") != size
            or row.get("sha256") != digest
        ):
            raise BASE.TraceLaunchError(f"battle-v3 {key} pin drifted")
    generated = sources.get("generated_collector")
    if (
        not isinstance(generated, dict)
        or generated.get("source_controlled") is not False
        or generated.get("staged_private_only") is not True
        or generated.get("size") != GENERATED_COLLECTOR_SIZE
        or generated.get("sha256") != GENERATED_COLLECTOR_SHA256
    ):
        raise BASE.TraceLaunchError("battle-v3 generated collector pin drifted")

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
        raise BASE.TraceLaunchError("battle-v3 private-input pins drifted")

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
        raise BASE.TraceLaunchError("battle-v3 scenario timelines drifted")

    accepted_outputs = contract.get("accepted_outputs")
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
    actual_accepted_outputs = [
        {
            "scenario": row.get("scenario"),
            "variant": row.get("variant"),
            "trace_size": row.get("trace_size"),
            "trace_sha256": row.get("trace_sha256"),
        }
        for row in accepted_outputs
        if isinstance(row, dict)
    ] if isinstance(accepted_outputs, list) else []
    if actual_accepted_outputs != expected_accepted_outputs:
        raise BASE.TraceLaunchError("battle-v3 accepted trace pins drifted")

    battle_anchors = contract.get("battle_anchors")
    if (
        not isinstance(battle_anchors, dict)
        or battle_anchors.get("location") != "01DB"
        or battle_anchors.get("storyline") != "D6"
        or battle_anchors.get("pending_request") != "01"
        or battle_anchors.get("explore_mode") != "00"
        or battle_anchors.get("dialog_state") != "00"
        or battle_anchors.get("active_party_hex") != "000102"
        or battle_anchors.get("roster_hex") != "000102828004030605"
        or battle_anchors.get("joined_hex") != "FE"
        or battle_anchors.get("battle_ids_hex")
        != "000102cdffffccffffffcb00"
        or battle_anchors.get("battle_current_and_max_hp")
        != [969, 898, 909, 8000, 12000, 20000]
        or battle_anchors.get("attack_command_state_hex")
        != "0000000000ffff000100000000"
        or battle_anchors.get("tech_command_state_hex")
        != "0001000000ffff000100000000"
    ):
        raise BASE.TraceLaunchError("battle-v3 battle anchors drifted")

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
        raise BASE.TraceLaunchError("battle-v3 watched ranges drifted")

    controls = contract.get("controls")
    if (
        not isinstance(controls, dict)
        or controls.get("candidate_and_guards_zero_access_required") is not True
        or controls.get("roster_joined_epoch_writes_forbidden") is not True
        or controls.get("old_compatibility_accesses_are_census_subject")
        is not True
        or controls.get("old_compatibility_writes_forbidden") is not True
        or controls.get("counter_callback_reconciliation_required") is not True
        or controls.get("zero_canary_pair_identity_required") is not True
        or controls.get("all_pre_snapshots_share_one_checkpoint_required")
        is not True
        or controls.get("independent_replay_trace_identity_required") is not True
        or controls.get("no_attack_item_tech_execution_or_save_input") is not True
        or controls.get("ram_power_on_state") != "AllZeros"
        or controls.get("fixed_rom_name")
        != "project_epoch_mesen_lavos_clean.sfc"
    ):
        raise BASE.TraceLaunchError("battle-v3 safety controls drifted")


def _configure_base(generated_path: Path) -> None:
    BASE.COLLECTOR = generated_path
    BASE.COLLECTOR_SHA256 = GENERATED_COLLECTOR_SHA256
    BASE.VALIDATOR_PATH = VALIDATOR_PATH
    BASE.VALIDATOR_SHA256 = VALIDATOR_SHA256
    BASE.SCENARIO_CONTRACT_PATH = SCENARIO_CONTRACT_PATH
    BASE.SCENARIO_CONTRACT_SHA256 = SCENARIO_CONTRACT_SHA256
    BASE.SCENARIO_CONTRACT_SCHEMA = SCENARIO_CONTRACT_SCHEMA
    BASE.TRACE_SCHEMA = TRACE_SCHEMA
    BASE.SCENARIOS = SCENARIOS
    BASE.VARIANTS = VARIANTS
    BASE.EXPECTED_OUTPUTS = EXPECTED_OUTPUTS
    BASE.MAX_TRACE_BYTES = 4 * 1024 * 1024
    BASE.RUNTIME_HASHES = {
        **BASE.RUNTIME_HASHES,
        "rom": (
            "06d1c2b06b716052c5596aaa0c2e5632"
            "a027fee1a9a28439e509f813c30829a9"
        ),
        "state": CHECKPOINT_SHA256,
        "sram": SRAM_SHA256,
    }
    BASE.PINNED_SIZES = {
        **BASE.PINNED_SIZES,
        "rom": 4_194_304,
        "state": 261_614,
        "sram": 8_192,
    }
    BASE._validate_scenario_contract = _validate_scenario_contract


def run(args: argparse.Namespace) -> dict[str, Any]:
    before = _verify_ancestry()
    generated = BUILDER.build_collector()
    if len(generated) != GENERATED_COLLECTOR_SIZE:
        raise BASE.TraceLaunchError("battle-v3 generated collector size drifted")
    actual_generated = _sha256_bytes(generated)
    if actual_generated != GENERATED_COLLECTOR_SHA256:
        raise BASE.TraceLaunchError(
            "battle-v3 generated collector hash drifted: "
            f"expected {GENERATED_COLLECTOR_SHA256}, got {actual_generated}"
        )

    source_parent = (
        PRIVATE_ROOT / "test_runs" / "mesen2"
    ).resolve(strict=True)
    generated_path_after: Path | None = None
    with tempfile.TemporaryDirectory(
        prefix=".mesen_wram_battle_source_",
        dir=source_parent,
    ) as directory:
        source_root = Path(directory).resolve(strict=True)
        generated_path = source_root / "battle_collector_v3.lua"
        with generated_path.open("xb") as handle:
            handle.write(generated)
        generated_path = generated_path.resolve(strict=True)
        generated_path_after = generated_path
        if _sha256_file(generated_path) != GENERATED_COLLECTOR_SHA256:
            raise BASE.TraceLaunchError(
                "battle-v3 generated collector changed while staging"
            )
        _configure_base(generated_path)
        result = BASE.run(args)

    if generated_path_after is None or os.path.lexists(generated_path_after):
        raise BASE.TraceLaunchError(
            "battle-v3 generated collector source was not deleted"
        )
    after = _verify_ancestry()
    if after != before:
        raise BASE.TraceLaunchError("battle-v3 ancestry changed during execution")
    result["generated_collector_sha256"] = GENERATED_COLLECTOR_SHA256
    result["generated_collector_source_deleted"] = True
    result["derived_base_launcher_sha256"] = DERIVED_BASE_LAUNCHER_SHA256
    result["trace_schema"] = TRACE_SCHEMA
    result["capture_phase"] = "endFrame-after-terminal-input-poll"
    result["launch_profile"] = {
        "fixed_rom_name": "project_epoch_mesen_lavos_clean.sfc",
        "ram_power_on_state": "AllZeros",
    }
    result["trace"]["evidence_level"] = (
        "exploratory-verified-runtime"
        if args.exploratory
        else "verified-runtime"
    )
    result["screenshot"]["evidence_level"] = "supporting-presentation-only"
    result["screenshot"]["acceptance_gate"] = False
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
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="run strict controls without an accepted exact trace-hash claim",
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
        BASE.TraceLaunchError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
