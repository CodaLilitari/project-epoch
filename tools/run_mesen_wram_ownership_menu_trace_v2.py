#!/usr/bin/env python3
"""Run one isolated derived Mesen menu-ownership trace v2 case."""

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


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
BASE_LAUNCHER_PATH = ROOT / "tools" / "run_mesen_wram_ownership_trace.py"
BASE_LAUNCHER_SHA256: Final = (
    "80f25f577da219d383829dfc977564d8"
    "295d1e0691ae4a2823da3e41079fa203"
)
BUILDER_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_menu_collector_v2.py"
)
BUILDER_SHA256: Final = (
    "bb68dbe03d2a92dac265dd5c0b378a56"
    "e942229f0d5cf1c209a11ac86b82823a"
)
VALIDATOR_PATH = (
    ROOT / "tools" / "validate_mesen_wram_ownership_menu_trace_v2.py"
)
VALIDATOR_SHA256: Final = (
    "2dc71df20769644f6065f36311095ea7"
    "882142d066dbd717f36994521a94922b"
)
SCENARIO_CONTRACT_PATH = (
    ROOT / "references" / "mesen_wram_ownership_menu_scenarios_v2.json"
)
SCENARIO_CONTRACT_SHA256: Final = (
    "e0dbb86a513de2a45bf9c1a83af0b50b"
    "0bef08d5b20b5e21398de6da29222c99"
)
GENERATED_COLLECTOR_SIZE: Final = 41089
GENERATED_COLLECTOR_SHA256: Final = (
    "7ec953af6e4899b4a91f8a5edf9f5e20"
    "236b9a32dbdff4ad1fbb3813efc71f05"
)
TRACE_SCHEMA: Final = "project-epoch-mesen-wram-ownership-menu-trace-v2"
SCENARIO_CONTRACT_SCHEMA: Final = (
    "project-epoch-mesen-wram-ownership-menu-scenarios-v2"
)
SCENARIOS: Final = (
    "equipment-owner-switch",
    "tech-owner-switch",
    "item-list-cancel",
    "party-page-cancel",
)
VARIANTS: Final = ("zero", "canary")
TECH_OWNER_SWITCH_WRITES: Final = (
    (124, 221, "7E2857", "00", "C282E7"),
    (125, 221, "7E2858", "00", "C282E7"),
    (127, 221, "7E2859", "00", "C282F3"),
    (129, 221, "7E285A", "00", "C282F3"),
    (131, 221, "7E285B", "00", "C282F3"),
)

EXPECTED_OUTPUTS: dict[
    tuple[str, str],
    dict[str, tuple[int, str]],
] = {
    ("equipment-owner-switch", "zero"): {
        "trace": (
            23127,
            "f15a149dcc34a1a7e0362993b0fbf0f"
            "34dcef19eaa16da8fc744917dd0069d7b",
        ),
        "screenshot": (
            15661,
            "b4660241d539692f9618cb710ead3d16"
            "316a8eba4cde8cb5fc2e2759f8b98ba4",
        ),
    },
    ("equipment-owner-switch", "canary"): {
        "trace": (
            29877,
            "00213f5c1fe77ac1d2f5b6aa61b2e58"
            "94d9f85d70c97cdcf1b6629aac4ead54c",
        ),
        "screenshot": (
            15661,
            "b4660241d539692f9618cb710ead3d16"
            "316a8eba4cde8cb5fc2e2759f8b98ba4",
        ),
    },
    ("tech-owner-switch", "zero"): {
        "trace": (
            24343,
            "d0bcfc8c9fbd52a6e5ec266bc585bce"
            "6450cb724cf202802d798ef5a64572d25",
        ),
        "screenshot": (
            12064,
            "018ad6afe24e5d5075e13a338d610cf4"
            "cd8eded9b286deb09eb29fbc366ccad5",
        ),
    },
    ("tech-owner-switch", "canary"): {
        "trace": (
            31093,
            "4c79ead1194c86f709899aadc4abe37d"
            "6738656446de187eb71991c8e2addf47",
        ),
        "screenshot": (
            12064,
            "018ad6afe24e5d5075e13a338d610cf4"
            "cd8eded9b286deb09eb29fbc366ccad5",
        ),
    },
    ("item-list-cancel", "zero"): {
        "trace": (
            23122,
            "8e2cedd68f0e56821e9c4d494ba47618"
            "f6a9a6b1768c3618984f54b92b33c7ab",
        ),
        "screenshot": (
            10689,
            "e93a7d8bf3dbe50c911d840adec72fd2"
            "6075e79d881977e067328f3e4f9c4c14",
        ),
    },
    ("item-list-cancel", "canary"): {
        "trace": (
            29872,
            "16f33fa3347830792ebf4178a838050b"
            "f12f1d8affc15ba6c9de9ddf0c51f28a",
        ),
        "screenshot": (
            10689,
            "e93a7d8bf3dbe50c911d840adec72fd2"
            "6075e79d881977e067328f3e4f9c4c14",
        ),
    },
    ("party-page-cancel", "zero"): {
        "trace": (
            192711,
            "a034cebf816d2faede9079727a085b008"
            "26dbbd77ff83e36bec75b6fc6a4d3c8",
        ),
        "screenshot": (
            9392,
            "43925f2efef2175fee4219226cb98a1d"
            "30210b314b099b6ea2b4ca6b466c2ffd",
        ),
    },
    ("party-page-cancel", "canary"): {
        "trace": (
            199461,
            "1f075ef894a995a3ed59cfac7d33665"
            "b5b7d991ac4e89c893427bddf1172e276",
        ),
        "screenshot": (
            9392,
            "43925f2efef2175fee4219226cb98a1d"
            "30210b314b099b6ea2b4ca6b466c2ffd",
        ),
    },
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_exact_module(
    name: str,
    path: Path,
    expected_sha256: str,
) -> types.ModuleType:
    source = path.read_bytes()
    actual = hashlib.sha256(source).hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(
            f"{path.name} SHA-256 drifted: expected {expected_sha256}, "
            f"got {actual}"
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


BASE = _load_exact_module(
    "_project_epoch_wram_ownership_launcher_v1_for_menu_v2",
    BASE_LAUNCHER_PATH,
    BASE_LAUNCHER_SHA256,
)
BUILDER = _load_exact_module(
    "_project_epoch_wram_ownership_menu_collector_builder_v2",
    BUILDER_PATH,
    BUILDER_SHA256,
)


ANCESTRY_PINS: Final = {
    ROOT / "references" / "mesen_wram_ownership_scenarios_v1.json": (
        "e9ea3ec765d3c14511f11815f1155c66"
        "c63f4cda1b23d445a2274ade0d8831d9"
    ),
    ROOT / "references" / "mesen_wram_ownership_accepted_artifacts_v1.json": (
        "b8f863ab2db7ed5f17222c59044a0263"
        "05a05db86a7a0303fc3db84bfa197142"
    ),
    ROOT / "tools" / "mesen_wram_ownership_trace.lua": (
        "d5dd2b2d7085237844d95ab04f7007b6"
        "b2d17b2e1160f23857018319380b7569"
    ),
    ROOT / "tools" / "validate_mesen_wram_ownership_trace.py": (
        "89a7dc86c6b5b10dc984b778451152e4"
        "734b5c553a669b7ee033e465ca87f2ba"
    ),
    BASE_LAUNCHER_PATH: BASE_LAUNCHER_SHA256,
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
                f"menu-v2 ancestry drifted at {path}: "
                f"expected {expected}, got {actual}"
            )
        result[path] = actual
    return result


def _expected_contract_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "name": scenario.name,
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
        raise BASE.TraceLaunchError("menu-v2 scenario contract schema drifted")
    if contract.get("version") != 2:
        raise BASE.TraceLaunchError("menu-v2 scenario contract version drifted")
    if contract.get("acceptance_status") != "accepted-exact-artifact-hashes":
        raise BASE.TraceLaunchError(
            "menu-v2 scenario contract acceptance status drifted"
        )

    trace = contract.get("trace_contract")
    if (
        not isinstance(trace, dict)
        or trace.get("schema") != TRACE_SCHEMA
        or trace.get("collector_version") != 2
        or trace.get("trace_count") != 8
        or trace.get("variants") != list(VARIANTS)
        or trace.get("terminal_frame") != 600
    ):
        raise BASE.TraceLaunchError("menu-v2 trace contract drifted")

    sources = contract.get("sources")
    if not isinstance(sources, dict):
        raise BASE.TraceLaunchError("menu-v2 source pins are missing")
    expected_sources = {
        "collector_builder": (
            "tools/build_mesen_wram_ownership_menu_collector_v2.py",
            BUILDER_SHA256,
        ),
        "validator": (
            "tools/validate_mesen_wram_ownership_menu_trace_v2.py",
            VALIDATOR_SHA256,
        ),
    }
    for key, (path, digest) in expected_sources.items():
        row = sources.get(key)
        if (
            not isinstance(row, dict)
            or row.get("path") != path
            or row.get("sha256") != digest
        ):
            raise BASE.TraceLaunchError(f"menu-v2 {key} pin drifted")
    generated = sources.get("generated_collector")
    if (
        not isinstance(generated, dict)
        or generated.get("source_controlled") is not False
        or generated.get("staged_private_only") is not True
        or generated.get("size") != GENERATED_COLLECTOR_SIZE
        or generated.get("sha256") != GENERATED_COLLECTOR_SHA256
    ):
        raise BASE.TraceLaunchError("menu-v2 generated collector pin drifted")

    raw_scenarios = contract.get("scenarios")
    if not isinstance(raw_scenarios, list):
        raise BASE.TraceLaunchError("menu-v2 scenarios are missing")
    actual_scenarios = [
        {
            "name": row.get("name"),
            "inputs": row.get("inputs"),
        }
        for row in raw_scenarios
        if isinstance(row, dict)
    ]
    if actual_scenarios != _expected_contract_scenarios():
        raise BASE.TraceLaunchError("menu-v2 scenario timelines drifted")

    accepted_outputs = contract.get("accepted_outputs")
    expected_accepted_outputs = [
        {
            "scenario": scenario,
            "variant": variant,
            "trace_size": EXPECTED_OUTPUTS[(scenario, variant)]["trace"][0],
            "trace_sha256": EXPECTED_OUTPUTS[(scenario, variant)]["trace"][1],
            "screenshot_size": EXPECTED_OUTPUTS[
                (scenario, variant)
            ]["screenshot"][0],
            "screenshot_sha256": EXPECTED_OUTPUTS[
                (scenario, variant)
            ]["screenshot"][1],
        }
        for scenario in SCENARIOS
        for variant in VARIANTS
    ]
    if not isinstance(accepted_outputs, list) or [
        {
            "scenario": row.get("scenario"),
            "variant": row.get("variant"),
            "trace_size": row.get("trace_size"),
            "trace_sha256": row.get("trace_sha256"),
            "screenshot_size": row.get("screenshot_size"),
            "screenshot_sha256": row.get("screenshot_sha256"),
        }
        for row in accepted_outputs
        if isinstance(row, dict)
    ] != expected_accepted_outputs:
        raise BASE.TraceLaunchError("menu-v2 accepted output pins drifted")

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
    if not isinstance(watched, list) or [
        (
            row.get("name"),
            row.get("start"),
            row.get("end"),
            row.get("length"),
        )
        for row in watched
        if isinstance(row, dict)
    ] != expected_ranges:
        raise BASE.TraceLaunchError("menu-v2 watched ranges drifted")

    controls = contract.get("controls")
    expected_tech_writes = [
        {
            "seq": seq,
            "frame": frame,
            "access": "write",
            "address": address,
            "value": value,
            "pc24": pc24,
        }
        for seq, frame, address, value, pc24 in TECH_OWNER_SWITCH_WRITES
    ]
    if (
        not isinstance(controls, dict)
        or controls.get("candidate_and_guards_zero_access_required") is not True
        or controls.get("old_compatibility_writes_otherwise_forbidden")
        is not True
        or controls.get("tech_owner_switch_exact_same_value_writes")
        != expected_tech_writes
        or controls.get(
            "tech_owner_switch_old_block_pre_post_bytes_2857_285b"
        )
        != "0000000000"
        or controls.get(
            "tech_owner_switch_old_block_net_change_forbidden"
        )
        is not True
        or controls.get("roster_joined_epoch_writes_forbidden") is not True
        or controls.get("counter_callback_reconciliation_required") is not True
        or controls.get("zero_canary_pair_identity_required") is not True
        or controls.get(
            "input_schedule_has_no_final_item_use_equipment_change_party_swap_or_save_confirmation"
        )
        is not True
    ):
        raise BASE.TraceLaunchError("menu-v2 protected-write controls drifted")


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
    BASE._validate_scenario_contract = _validate_scenario_contract


def run(args: argparse.Namespace) -> dict[str, Any]:
    before = _verify_ancestry()
    generated = BUILDER.build_collector()
    if len(generated) != GENERATED_COLLECTOR_SIZE:
        raise BASE.TraceLaunchError("menu-v2 generated collector size drifted")
    actual_generated_hash = hashlib.sha256(generated).hexdigest()
    if actual_generated_hash != GENERATED_COLLECTOR_SHA256:
        raise BASE.TraceLaunchError(
            "menu-v2 generated collector hash drifted: "
            f"expected {GENERATED_COLLECTOR_SHA256}, "
            f"got {actual_generated_hash}"
        )

    source_parent = (
        PRIVATE_ROOT / "test_runs" / "mesen2"
    ).resolve(strict=True)
    generated_path_after: Path | None = None
    with tempfile.TemporaryDirectory(
        prefix=".mesen_wram_menu_source_",
        dir=source_parent,
    ) as directory:
        source_root = Path(directory).resolve(strict=True)
        generated_path = source_root / "menu_collector_v2.lua"
        with generated_path.open("xb") as handle:
            handle.write(generated)
        generated_path = generated_path.resolve(strict=True)
        generated_path_after = generated_path
        if _sha256_file(generated_path) != GENERATED_COLLECTOR_SHA256:
            raise BASE.TraceLaunchError(
                "menu-v2 generated collector changed while staging"
            )
        _configure_base(generated_path)
        result = BASE.run(args)

    if generated_path_after is None or os.path.lexists(generated_path_after):
        raise BASE.TraceLaunchError(
            "menu-v2 generated collector source was not deleted"
        )
    after = _verify_ancestry()
    if after != before:
        raise BASE.TraceLaunchError("menu-v2 ancestry changed during execution")
    result["generated_collector_sha256"] = GENERATED_COLLECTOR_SHA256
    result["generated_collector_source_deleted"] = True
    result["trace_schema"] = TRACE_SCHEMA
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mesen", type=Path, default=BASE.DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=BASE.DEFAULT_ROM)
    parser.add_argument("--state", type=Path, default=BASE.DEFAULT_STATE)
    parser.add_argument("--sram", type=Path, default=BASE.DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help="run strict controls without an accepted exact output claim",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
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
