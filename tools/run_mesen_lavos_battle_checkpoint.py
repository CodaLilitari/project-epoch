#!/usr/bin/env python3
"""Acquire one isolated native-Mesen Lavos Core battle checkpoint.

The launcher is intentionally private-only and fail-closed. It stages pinned
Mesen 2.1.1 runtime files, the canonical clean ROM, the recovered pre-Lavos
SRAM, and the exact collector beneath a disposable directory. Default runs
enforce the frozen deterministic state/trace hashes. ``--exploratory`` keeps
the same strict controls without making an acceptance claim. Screenshots are
supporting per-run presentation artifacts and are never acceptance hash gates.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import types
from typing import Any, Final, Mapping
import zlib


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
BASE_LAUNCHER_PATH = ROOT / "tools" / "run_mesen_wram_ownership_trace.py"
BASE_LAUNCHER_SHA256: Final = (
    "80f25f577da219d383829dfc977564d8"
    "295d1e0691ae4a2823da3e41079fa203"
)
COLLECTOR_PATH = ROOT / "tools" / "mesen_lavos_battle_checkpoint.lua"
COLLECTOR_SIZE: Final = 14_672
COLLECTOR_SHA256: Final = (
    "3bcc3146d9b5ef7fe7287f9031b7ad6f"
    "2d0c0423bfcf7c5f910efac4431cce11"
)
VERIFIER_PATH = (
    ROOT / "tools" / "mesen_lavos_battle_checkpoint_verify.lua"
)
VERIFIER_SIZE: Final = 10_301
VERIFIER_SHA256: Final = (
    "87191b6df43ca7e72c469912822a5ed2"
    "922a394fe68ac9e3305eb8cf92ae3555"
)
ACCEPTANCE_CONTRACT_PATH = (
    ROOT
    / "references"
    / "mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json"
)
ACCEPTANCE_CONTRACT_SIZE: Final = 4_983
ACCEPTANCE_CONTRACT_SHA256: Final = (
    "67cc7c9f7460a3de30a23c90aca53a07"
    "9b8334c5e80c1975651fcdc60ba08564"
)
ACCEPTANCE_CONTRACT_SCHEMA: Final = (
    "project-epoch-mesen-lavos-battle-checkpoint-acceptance-v1"
)
PRESENTATION_MANIFEST_SCHEMA: Final = (
    "project-epoch-mesen-lavos-battle-checkpoint-presentation-v1"
)
DETERMINISTIC_ARTIFACT_NAMES: Final = (
    "battle_ready.mss",
    "checkpoint.tsv",
    "fresh_load_control.tsv",
    "fresh_load_down.tsv",
)
PRESENTATION_ARTIFACT_NAMES: Final = (
    "endpoint.png",
    "command_down.png",
)

DEFAULT_MESEN = PRIVATE_ROOT / "tools" / "mesen2" / "app" / "Mesen.exe"
DEFAULT_ROM = (
    PRIVATE_ROOT / "input" / "rom_archive" / "Chrono Trigger (USA).sfc"
)
DEFAULT_SRAM = (
    PRIVATE_ROOT / "input" / "lavos_save" / "chrono_trigger.srm"
)

FIXED_ROM_NAME: Final = "project_epoch_mesen_lavos_clean.sfc"
FIXED_ROM_STEM: Final = "project_epoch_mesen_lavos_clean"
EXPECTED_EXIT_CODE: Final = 39
EXPECTED_VERIFY_EXIT_CODE: Final = 47
EXPECTED_CAPTURE_OFFSET: Final = 360
EXPECTED_VERIFY_TERMINAL_FRAME: Final = 60
TRACE_SCHEMA: Final = "project-epoch-mesen-lavos-battle-checkpoint-v1"
MAX_TRACE_BYTES: Final = 512 * 1024
MAX_SCREENSHOT_BYTES: Final = 16 * 1024 * 1024
MAX_STATE_BYTES: Final = 4 * 1024 * 1024

RUNTIME_HASHES: Final = {
    "archive": "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe",
    "harfbuzz": "eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d",
    "mesen": "d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b",
    "mesen_core": "65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74",
    "nesdb": "cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307",
    "settings": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    "skia": "9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd",
    "rom": "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9",
    "sram": "cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203",
}
PINNED_SIZES: Final = {
    "archive": 34_058_170,
    "harfbuzz": 1_804_872,
    "mesen": 70_470_144,
    "mesen_core": 7_143_424,
    "nesdb": 559_118,
    "settings": 3,
    "skia": 9_414_216,
    "rom": 4_194_304,
    "sram": 8_192,
}

TRACE_COLUMNS: Final = (
    "event",
    "frame",
    "stage",
    "location",
    "storyline",
    "pending",
    "explore",
    "dialog",
    "leader_x",
    "leader_y",
    "active",
    "roster",
    "joined",
    "battle_ids",
    "battle_current_hp",
    "battle_max_hp",
    "battle_ui",
    "command_state",
    "battle_launch_seen",
    "candidate_zero",
    "front_guard_zero",
    "rear_guard_zero",
    "epoch_exact",
    "sram_exact",
)
EXPECTED_ACTIVE: Final = "000102"
EXPECTED_ROSTER: Final = "000102828004030605"
EXPECTED_BATTLE_IDENTITIES: Final = {
    0: 0x00,
    1: 0x01,
    2: 0x02,
    3: 0xCD,
    6: 0xCC,
    10: 0xCB,
}
VERIFY_COLUMNS: Final = (
    "event",
    "mode",
    "relative_frame",
    "location",
    "storyline",
    "pending",
    "explore",
    "dialog",
    "active",
    "roster",
    "joined",
    "battle_ids",
    "battle_current_hp",
    "battle_max_hp",
    "battle_ui",
    "command_state",
    "candidate_zero",
    "front_guard_zero",
    "rear_guard_zero",
    "epoch_exact",
    "sram_exact",
)


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
    "_project_epoch_wram_ownership_launcher_for_lavos_checkpoint",
    BASE_LAUNCHER_PATH,
    BASE_LAUNCHER_SHA256,
)
TraceLaunchError = BASE.TraceLaunchError


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _require_pinned_source(
    path: Path,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> bytes:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise TraceLaunchError(
            f"cannot read pinned {label}: {path}"
        ) from exc
    if len(source) != expected_size:
        raise TraceLaunchError(
            f"{label} size mismatch: "
            f"expected {expected_size}, got {len(source)}"
        )
    actual = _sha256_bytes(source)
    if actual != expected_sha256:
        raise TraceLaunchError(
            f"{label} SHA-256 mismatch: "
            f"expected {expected_sha256}, got {actual}"
        )
    return source


def _require_collector_source() -> bytes:
    return _require_pinned_source(
        COLLECTOR_PATH,
        COLLECTOR_SIZE,
        COLLECTOR_SHA256,
        "Lavos checkpoint collector",
    )


def _require_verifier_source() -> bytes:
    return _require_pinned_source(
        VERIFIER_PATH,
        VERIFIER_SIZE,
        VERIFIER_SHA256,
        "Lavos checkpoint fresh-load verifier",
    )


def _canonical_hex(value: str, length: int, label: str) -> str:
    if (
        len(value) != length
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TraceLaunchError(f"{label} is not canonical lowercase hex")
    return value


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TraceLaunchError(
                f"acceptance contract has duplicate key {key!r}"
            )
        result[key] = value
    return result


def _decode_json_object(source: bytes, label: str) -> dict[str, Any]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TraceLaunchError(f"{label} is not UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except TraceLaunchError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise TraceLaunchError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TraceLaunchError(f"{label} must contain one JSON object")
    return value


def _validate_acceptance_contract(
    contract: Mapping[str, Any],
) -> dict[str, tuple[int, str]]:
    if contract.get("schema") != ACCEPTANCE_CONTRACT_SCHEMA:
        raise TraceLaunchError("acceptance contract schema drifted")
    if contract.get("version") != 1:
        raise TraceLaunchError("acceptance contract version drifted")
    if (
        contract.get("acceptance_status")
        != "accepted-exact-deterministic-artifact-hashes"
    ):
        raise TraceLaunchError("acceptance contract status drifted")
    if contract.get("evidence_level") != "verified-runtime":
        raise TraceLaunchError("acceptance contract evidence level drifted")

    emulator = contract.get("emulator")
    if not isinstance(emulator, dict):
        raise TraceLaunchError("acceptance contract emulator pins are missing")
    expected_emulator = {
        "name": "Mesen",
        "version": "2.1.1",
        "archive_size": PINNED_SIZES["archive"],
        "archive_sha256": RUNTIME_HASHES["archive"],
        "exe_size": PINNED_SIZES["mesen"],
        "exe_sha256": RUNTIME_HASHES["mesen"],
        "core_size": PINNED_SIZES["mesen_core"],
        "core_sha256": RUNTIME_HASHES["mesen_core"],
    }
    for key, expected_value in expected_emulator.items():
        if emulator.get(key) != expected_value:
            raise TraceLaunchError(
                f"acceptance contract emulator {key} pin drifted"
            )

    sources = contract.get("sources")
    if not isinstance(sources, dict):
        raise TraceLaunchError("acceptance contract source pins are missing")
    expected_sources = {
        "base_launcher": (
            "tools/run_mesen_wram_ownership_trace.py",
            BASE_LAUNCHER_PATH.stat().st_size,
            BASE_LAUNCHER_SHA256,
        ),
        "collector": (
            "tools/mesen_lavos_battle_checkpoint.lua",
            COLLECTOR_SIZE,
            COLLECTOR_SHA256,
        ),
        "fresh_load_verifier": (
            "tools/mesen_lavos_battle_checkpoint_verify.lua",
            VERIFIER_SIZE,
            VERIFIER_SHA256,
        ),
    }
    if set(sources) != set(expected_sources):
        raise TraceLaunchError("acceptance contract source set drifted")
    for label, expected in expected_sources.items():
        record = sources.get(label)
        if not isinstance(record, dict):
            raise TraceLaunchError(
                f"acceptance contract {label} source pin is missing"
            )
        actual = (
            record.get("path"),
            record.get("size"),
            record.get("sha256"),
        )
        if actual != expected:
            raise TraceLaunchError(
                f"acceptance contract {label} source pin drifted"
            )

    private_inputs = contract.get("private_inputs")
    if not isinstance(private_inputs, dict):
        raise TraceLaunchError("acceptance contract private pins are missing")
    expected_private = {
        "canonical_rom": (
            PINNED_SIZES["rom"],
            RUNTIME_HASHES["rom"],
        ),
        "recovered_pre_lavos_sram": (
            PINNED_SIZES["sram"],
            RUNTIME_HASHES["sram"],
        ),
    }
    if set(private_inputs) != set(expected_private):
        raise TraceLaunchError("acceptance contract private-input set drifted")
    for label, expected in expected_private.items():
        record = private_inputs.get(label)
        if not isinstance(record, dict):
            raise TraceLaunchError(
                f"acceptance contract {label} pin is missing"
            )
        if (record.get("size"), record.get("sha256")) != expected:
            raise TraceLaunchError(
                f"acceptance contract {label} pin drifted"
            )

    artifacts = contract.get("accepted_deterministic_artifacts")
    if not isinstance(artifacts, dict):
        raise TraceLaunchError(
            "acceptance contract deterministic artifacts are missing"
        )
    if set(artifacts) != set(DETERMINISTIC_ARTIFACT_NAMES):
        raise TraceLaunchError(
            "acceptance contract deterministic artifact set drifted"
        )
    expected_artifacts: dict[str, tuple[int, str]] = {}
    for name in DETERMINISTIC_ARTIFACT_NAMES:
        record = artifacts.get(name)
        if not isinstance(record, dict):
            raise TraceLaunchError(
                f"acceptance contract artifact {name} is missing"
            )
        size = record.get("size")
        sha256 = record.get("sha256")
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or size <= 0
            or not isinstance(sha256, str)
        ):
            raise TraceLaunchError(
                f"acceptance contract artifact {name} pin is invalid"
            )
        _canonical_hex(
            sha256,
            64,
            f"acceptance contract artifact {name} SHA-256",
        )
        if record.get("evidence_level") != "verified-runtime":
            raise TraceLaunchError(
                f"acceptance contract artifact {name} evidence drifted"
            )
        expected_artifacts[name] = (size, sha256)

    presentation = contract.get("presentation_policy")
    if not isinstance(presentation, dict):
        raise TraceLaunchError(
            "acceptance contract presentation policy is missing"
        )
    expected_presentation = {
        "artifacts": list(PRESENTATION_ARTIFACT_NAMES),
        "accepted_deterministic_artifact": False,
        "hash_gated_for_acceptance": False,
        "may_vary_between_equivalent_runs": True,
        "per_run_manifest": "presentation_manifest.json",
        "per_run_manifest_schema": PRESENTATION_MANIFEST_SCHEMA,
        "per_run_evidence_level": "verified-runtime",
    }
    for key, expected_value in expected_presentation.items():
        if (
            key not in presentation
            or presentation.get(key) != expected_value
        ):
            raise TraceLaunchError(
                f"acceptance contract presentation policy {key} drifted"
            )
    overlap = set(artifacts).intersection(PRESENTATION_ARTIFACT_NAMES)
    if overlap:
        raise TraceLaunchError(
            "presentation artifacts entered the deterministic acceptance set"
        )
    return expected_artifacts


def _load_acceptance_contract(
) -> tuple[bytes, dict[str, Any], dict[str, tuple[int, str]]]:
    source = _require_pinned_source(
        ACCEPTANCE_CONTRACT_PATH,
        ACCEPTANCE_CONTRACT_SIZE,
        ACCEPTANCE_CONTRACT_SHA256,
        "Lavos checkpoint acceptance contract",
    )
    contract = _decode_json_object(
        source,
        "Lavos checkpoint acceptance contract",
    )
    expected = _validate_acceptance_contract(contract)
    return source, contract, expected


def _verify_accepted_deterministic_artifacts(
    outputs: Mapping[str, bytes],
    expected: Mapping[str, tuple[int, str]],
) -> dict[str, dict[str, Any]]:
    required = set(DETERMINISTIC_ARTIFACT_NAMES)
    if set(outputs) != required or set(expected) != required:
        raise TraceLaunchError(
            "accepted deterministic artifact set is incomplete or unexpected"
        )
    records: dict[str, dict[str, Any]] = {}
    for name in DETERMINISTIC_ARTIFACT_NAMES:
        source = outputs[name]
        actual = (len(source), _sha256_bytes(source))
        if actual != expected[name]:
            raise TraceLaunchError(
                f"{name} does not match accepted deterministic artifact: "
                f"expected {expected[name][0]}/{expected[name][1]}, "
                f"got {actual[0]}/{actual[1]}"
            )
        records[name] = _artifact_record(source)
    return records


def _checkpoint_artifact_sections(
    deterministic_outputs: Mapping[str, bytes],
) -> dict[str, Any]:
    if set(deterministic_outputs) != set(DETERMINISTIC_ARTIFACT_NAMES):
        raise TraceLaunchError(
            "checkpoint deterministic artifact set is incomplete or unexpected"
        )
    return {
        "artifact_policy": {
            "deterministic_artifacts": list(
                DETERMINISTIC_ARTIFACT_NAMES
            ),
            "default_acceptance_gate": "exact-size-and-sha256",
            "accepted_contract": (
                "references/"
                "mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json"
            ),
            "presentation_artifacts": list(PRESENTATION_ARTIFACT_NAMES),
            "presentation_artifacts_accepted": False,
            "presentation_hash_gated_for_acceptance": False,
            "presentation_metadata": "presentation_manifest.json",
            "presentation_policy": "supporting-presentation-only",
        },
        "artifacts": {
            name: _artifact_record(deterministic_outputs[name])
            for name in DETERMINISTIC_ARTIFACT_NAMES
        },
    }


def _build_presentation_manifest(
    presentation_outputs: Mapping[str, bytes],
) -> dict[str, Any]:
    if set(presentation_outputs) != set(PRESENTATION_ARTIFACT_NAMES):
        raise TraceLaunchError(
            "presentation artifact set is incomplete or unexpected"
        )
    artifacts: dict[str, dict[str, Any]] = {}
    for name in PRESENTATION_ARTIFACT_NAMES:
        source = presentation_outputs[name]
        record = BASE.describe_artifact_bytes(
            source,
            f"presentation artifact {name}",
            png=True,
        )
        artifacts[name] = {
            **record,
            "evidence_level": "verified-runtime",
            "acceptance_role": "supporting-presentation-only",
        }
    return {
        "schema": PRESENTATION_MANIFEST_SCHEMA,
        "version": 1,
        "evidence_level": "verified-runtime",
        "accepted_deterministic_artifact": False,
        "hash_gated_for_acceptance": False,
        "may_vary_between_equivalent_runs": True,
        "artifacts": artifacts,
    }


def _json_bytes(document: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            document,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        ).encode("utf-8")
        + b"\n"
    )


def _command_cursor(command_state: str, label: str) -> tuple[int, int]:
    _canonical_hex(command_state, 26, label)
    fields = bytes.fromhex(command_state)
    menu_slot = fields[0]
    if menu_slot > 2:
        raise TraceLaunchError(f"{label} active menu slot is invalid")
    cursor = fields[1 + menu_slot]
    if cursor > 2:
        raise TraceLaunchError(f"{label} cursor row is invalid")
    active_ready_pc = fields[7]
    ready_count = fields[8]
    if active_ready_pc > 2 or ready_count == 0 or ready_count > 3:
        raise TraceLaunchError(f"{label} ready-PC state is invalid")
    battler = fields[4 + active_ready_pc]
    if battler > 2 or fields[9 + battler] != 0:
        raise TraceLaunchError(f"{label} active battler is not menu-ready")
    return menu_slot, cursor


def _parse_uint(value: str, label: str, *, maximum: int) -> int:
    if not value or not value.isascii() or not value.isdecimal():
        raise TraceLaunchError(f"{label} is not a canonical unsigned integer")
    if len(value) > 1 and value.startswith("0"):
        raise TraceLaunchError(f"{label} has a leading zero")
    parsed = int(value)
    if parsed < 0 or parsed > maximum:
        raise TraceLaunchError(f"{label} is out of range")
    return parsed


def parse_checkpoint_trace(source: bytes) -> dict[str, Any]:
    """Parse and validate the deterministic collector TSV."""

    if not source or len(source) > MAX_TRACE_BYTES:
        raise TraceLaunchError("checkpoint trace size is invalid")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TraceLaunchError("checkpoint trace is not UTF-8") from exc
    if "\r" in text or not text.endswith("\n"):
        raise TraceLaunchError(
            "checkpoint trace must use canonical LF lines and a final newline"
        )
    lines = text[:-1].split("\n")
    if len(lines) < 5:
        raise TraceLaunchError("checkpoint trace has too few rows")
    if tuple(lines[0].split("\t")) != TRACE_COLUMNS:
        raise TraceLaunchError("checkpoint trace header drifted")

    rows: list[dict[str, Any]] = []
    prior_frame = -1
    for row_number, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(TRACE_COLUMNS):
            raise TraceLaunchError(
                f"checkpoint trace row {row_number} has the wrong field count"
            )
        raw = dict(zip(TRACE_COLUMNS, fields, strict=True))
        event = raw["event"]
        stage = raw["stage"]
        if event not in {
            "start",
            "stage",
            "probe",
            "battle-launch",
            "capture-queued",
            "success",
            "failure",
        }:
            raise TraceLaunchError(
                f"checkpoint trace row {row_number} has an unknown event"
            )
        if stage not in {
            "boot",
            "lavos-tunnel-route",
            "lavos-dialogue",
            "battle-settle",
        }:
            raise TraceLaunchError(
                f"checkpoint trace row {row_number} has an unknown stage"
            )
        frame = _parse_uint(
            raw["frame"],
            f"checkpoint trace row {row_number} frame",
            maximum=20_000,
        )
        if frame < prior_frame:
            raise TraceLaunchError("checkpoint trace frames are not monotonic")
        prior_frame = frame
        location = _canonical_hex(
            raw["location"],
            4,
            f"checkpoint trace row {row_number} location",
        )
        storyline = _canonical_hex(
            raw["storyline"],
            2,
            f"checkpoint trace row {row_number} storyline",
        )
        pending = _canonical_hex(
            raw["pending"],
            2,
            f"checkpoint trace row {row_number} pending",
        )
        explore = _canonical_hex(
            raw["explore"],
            2,
            f"checkpoint trace row {row_number} explore",
        )
        dialog = _canonical_hex(
            raw["dialog"],
            2,
            f"checkpoint trace row {row_number} dialog",
        )
        active = _canonical_hex(
            raw["active"],
            6,
            f"checkpoint trace row {row_number} active party",
        )
        roster = _canonical_hex(
            raw["roster"],
            18,
            f"checkpoint trace row {row_number} roster",
        )
        joined = _canonical_hex(
            raw["joined"],
            2,
            f"checkpoint trace row {row_number} joined flags",
        )
        battle_ids = _canonical_hex(
            raw["battle_ids"],
            24,
            f"checkpoint trace row {row_number} battle IDs",
        )
        battle_ui = _canonical_hex(
            raw["battle_ui"],
            6,
            f"checkpoint trace row {row_number} battle UI",
        )
        command_state = _canonical_hex(
            raw["command_state"],
            26,
            f"checkpoint trace row {row_number} command state",
        )
        leader_x = _parse_uint(
            raw["leader_x"],
            f"checkpoint trace row {row_number} leader X",
            maximum=65_535,
        )
        leader_y = _parse_uint(
            raw["leader_y"],
            f"checkpoint trace row {row_number} leader Y",
            maximum=65_535,
        )
        current_hp_parts = raw["battle_current_hp"].split(",")
        maximum_hp_parts = raw["battle_max_hp"].split(",")
        if len(current_hp_parts) != 6 or len(maximum_hp_parts) != 6:
            raise TraceLaunchError(
                f"checkpoint trace row {row_number} has invalid HP columns"
            )
        current_hp = [
            _parse_uint(
                value,
                f"checkpoint trace row {row_number} current HP",
                maximum=65_535,
            )
            for value in current_hp_parts
        ]
        maximum_hp = [
            _parse_uint(
                value,
                f"checkpoint trace row {row_number} max HP",
                maximum=65_535,
            )
            for value in maximum_hp_parts
        ]
        booleans: dict[str, bool] = {}
        for key in (
            "battle_launch_seen",
            "candidate_zero",
            "front_guard_zero",
            "rear_guard_zero",
            "epoch_exact",
            "sram_exact",
        ):
            value = raw[key]
            if value not in {"true", "false"}:
                raise TraceLaunchError(
                    f"checkpoint trace row {row_number} has invalid {key}"
                )
            booleans[key] = value == "true"
        rows.append(
            {
                "event": event,
                "frame": frame,
                "stage": stage,
                "location": location,
                "storyline": storyline,
                "pending": pending,
                "explore": explore,
                "dialog": dialog,
                "leader_x": leader_x,
                "leader_y": leader_y,
                "active": active,
                "roster": roster,
                "joined": joined,
                "battle_ids": battle_ids,
                "battle_current_hp": current_hp,
                "battle_max_hp": maximum_hp,
                "battle_ui": battle_ui,
                "command_state": command_state,
                **booleans,
            }
        )

    milestones = [
        (row["event"], row["stage"])
        for row in rows
        if row["event"] != "probe"
    ]
    if milestones != [
        ("start", "boot"),
        ("stage", "lavos-tunnel-route"),
        ("stage", "lavos-dialogue"),
        ("battle-launch", "lavos-dialogue"),
        ("stage", "battle-settle"),
        ("capture-queued", "battle-settle"),
        ("success", "battle-settle"),
    ]:
        raise TraceLaunchError(
            "checkpoint trace milestone order or cardinality drifted"
        )
    if rows[0]["frame"] != 0:
        raise TraceLaunchError("checkpoint trace does not begin at frame zero")

    endpoint = rows[-1]
    if (
        endpoint["stage"] != "battle-settle"
        or endpoint["location"] != "01db"
        or endpoint["storyline"] != "d6"
        or endpoint["pending"] != "01"
        or endpoint["explore"] != "00"
        or endpoint["dialog"] != "00"
        or endpoint["active"] != EXPECTED_ACTIVE
        or endpoint["roster"] != EXPECTED_ROSTER
        or endpoint["joined"] != "fe"
        or not endpoint["battle_launch_seen"]
    ):
        raise TraceLaunchError("checkpoint terminal gameplay anchor drifted")
    identities = bytes.fromhex(endpoint["battle_ids"])
    for slot, expected in EXPECTED_BATTLE_IDENTITIES.items():
        if identities[slot] != expected:
            raise TraceLaunchError(
                f"checkpoint terminal battle identity drifted in slot {slot}"
            )
    if (
        any(value == 0 for value in endpoint["battle_current_hp"])
        or endpoint["battle_current_hp"] != endpoint["battle_max_hp"]
    ):
        raise TraceLaunchError(
            "checkpoint terminal combatants are not alive at full HP"
        )
    _command_cursor(
        endpoint["command_state"],
        "checkpoint terminal command state",
    )
    for key in (
        "candidate_zero",
        "front_guard_zero",
        "rear_guard_zero",
        "epoch_exact",
        "sram_exact",
    ):
        if not endpoint[key]:
            raise TraceLaunchError(
                f"checkpoint terminal protected invariant failed: {key}"
            )
    battle_launch_frame = next(
        row["frame"] for row in rows if row["event"] == "battle-launch"
    )
    capture_queued_frame = next(
        row["frame"] for row in rows if row["event"] == "capture-queued"
    )
    if (
        capture_queued_frame - battle_launch_frame
        != EXPECTED_CAPTURE_OFFSET
    ):
        raise TraceLaunchError(
            "checkpoint capture was not queued at the fixed battle offset"
        )
    endpoint_without_absolute_frame = {
        key: value
        for key, value in endpoint.items()
        if key != "frame"
    }
    return {
        "schema": TRACE_SCHEMA,
        "version": 1,
        "status": "exploratory-native-checkpoint",
        "endpoint": endpoint_without_absolute_frame,
        "capture_queued_frames_after_battle_launch": EXPECTED_CAPTURE_OFFSET,
        "_absolute_endpoint_frame": endpoint["frame"],
    }


def parse_verification_trace(
    source: bytes,
    expected_mode: str,
) -> dict[str, Any]:
    """Validate one deterministic fresh-load control/down proof."""

    if expected_mode not in {"control", "down"}:
        raise TraceLaunchError("fresh-load verification mode is invalid")
    if not source or len(source) > 128 * 1024:
        raise TraceLaunchError("fresh-load verification trace size is invalid")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TraceLaunchError(
            "fresh-load verification trace is not UTF-8"
        ) from exc
    if "\r" in text or not text.endswith("\n"):
        raise TraceLaunchError(
            "fresh-load verification trace is not canonical LF text"
        )
    lines = text[:-1].split("\n")
    if len(lines) != 3 or tuple(lines[0].split("\t")) != VERIFY_COLUMNS:
        raise TraceLaunchError(
            "fresh-load verification trace shape or header drifted"
        )

    rows: list[dict[str, Any]] = []
    for row_number, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(VERIFY_COLUMNS):
            raise TraceLaunchError(
                f"fresh-load verification row {row_number} field count drifted"
            )
        raw = dict(zip(VERIFY_COLUMNS, fields, strict=True))
        if raw["event"] not in {"baseline", "success"}:
            raise TraceLaunchError(
                f"fresh-load verification row {row_number} event drifted"
            )
        if raw["mode"] != expected_mode:
            raise TraceLaunchError(
                f"fresh-load verification row {row_number} mode drifted"
            )
        relative_frame = _parse_uint(
            raw["relative_frame"],
            f"fresh-load verification row {row_number} frame",
            maximum=EXPECTED_VERIFY_TERMINAL_FRAME,
        )
        location = _canonical_hex(
            raw["location"],
            4,
            f"fresh-load verification row {row_number} location",
        )
        storyline = _canonical_hex(
            raw["storyline"],
            2,
            f"fresh-load verification row {row_number} storyline",
        )
        pending = _canonical_hex(
            raw["pending"],
            2,
            f"fresh-load verification row {row_number} pending",
        )
        explore = _canonical_hex(
            raw["explore"],
            2,
            f"fresh-load verification row {row_number} explore",
        )
        dialog = _canonical_hex(
            raw["dialog"],
            2,
            f"fresh-load verification row {row_number} dialog",
        )
        active = _canonical_hex(
            raw["active"],
            6,
            f"fresh-load verification row {row_number} active",
        )
        roster = _canonical_hex(
            raw["roster"],
            18,
            f"fresh-load verification row {row_number} roster",
        )
        joined = _canonical_hex(
            raw["joined"],
            2,
            f"fresh-load verification row {row_number} joined",
        )
        battle_ids = _canonical_hex(
            raw["battle_ids"],
            24,
            f"fresh-load verification row {row_number} battle IDs",
        )
        battle_ui = _canonical_hex(
            raw["battle_ui"],
            6,
            f"fresh-load verification row {row_number} battle UI",
        )
        command_state = _canonical_hex(
            raw["command_state"],
            26,
            f"fresh-load verification row {row_number} command state",
        )
        current_parts = raw["battle_current_hp"].split(",")
        maximum_parts = raw["battle_max_hp"].split(",")
        if len(current_parts) != 6 or len(maximum_parts) != 6:
            raise TraceLaunchError(
                f"fresh-load verification row {row_number} HP shape drifted"
            )
        current_hp = [
            _parse_uint(
                value,
                f"fresh-load verification row {row_number} current HP",
                maximum=65_535,
            )
            for value in current_parts
        ]
        maximum_hp = [
            _parse_uint(
                value,
                f"fresh-load verification row {row_number} max HP",
                maximum=65_535,
            )
            for value in maximum_parts
        ]
        protected: dict[str, bool] = {}
        for key in (
            "candidate_zero",
            "front_guard_zero",
            "rear_guard_zero",
            "epoch_exact",
            "sram_exact",
        ):
            if raw[key] not in {"true", "false"}:
                raise TraceLaunchError(
                    f"fresh-load verification row {row_number} {key} drifted"
                )
            protected[key] = raw[key] == "true"
        row = {
            "event": raw["event"],
            "mode": expected_mode,
            "relative_frame": relative_frame,
            "location": location,
            "storyline": storyline,
            "pending": pending,
            "explore": explore,
            "dialog": dialog,
            "active": active,
            "roster": roster,
            "joined": joined,
            "battle_ids": battle_ids,
            "battle_current_hp": current_hp,
            "battle_max_hp": maximum_hp,
            "battle_ui": battle_ui,
            "command_state": command_state,
            **protected,
        }
        if (
            location != "01db"
            or storyline != "d6"
            or pending != "01"
            or explore != "00"
            or dialog != "00"
            or active != EXPECTED_ACTIVE
            or roster != EXPECTED_ROSTER
            or joined != "fe"
            or any(value == 0 for value in current_hp)
            or current_hp != maximum_hp
            or not all(protected.values())
        ):
            raise TraceLaunchError(
                f"fresh-load verification row {row_number} anchor drifted"
            )
        _command_cursor(
            command_state,
            f"fresh-load verification row {row_number} command state",
        )
        identities = bytes.fromhex(battle_ids)
        for slot, expected in EXPECTED_BATTLE_IDENTITIES.items():
            if identities[slot] != expected:
                raise TraceLaunchError(
                    "fresh-load verification battle identity drifted "
                    f"in slot {slot}"
                )
        rows.append(row)
    if [
        (row["event"], row["relative_frame"]) for row in rows
    ] != [
        ("baseline", 0),
        ("success", EXPECTED_VERIFY_TERMINAL_FRAME),
    ]:
        raise TraceLaunchError(
            "fresh-load verification milestone order drifted"
        )
    return {
        "mode": expected_mode,
        "baseline": rows[0],
        "endpoint": rows[1],
    }


def _decompress_exact(source: bytes, expected: int, label: str) -> bytes:
    if expected < 0:
        raise TraceLaunchError(f"{label} has an invalid decoded length")
    decoder = zlib.decompressobj()
    try:
        decoded = decoder.decompress(source, expected + 1)
        if len(decoded) > expected or decoder.unconsumed_tail:
            raise TraceLaunchError(f"{label} exceeds its decoded length")
        decoded += decoder.flush(expected - len(decoded) + 1)
    except zlib.error as exc:
        raise TraceLaunchError(f"{label} is not valid zlib") from exc
    if (
        len(decoded) != expected
        or not decoder.eof
        or decoder.unused_data
        or decoder.unconsumed_tail
    ):
        raise TraceLaunchError(f"{label} zlib envelope or length drifted")
    return decoded


def parse_mesen_state(source: bytes) -> dict[str, Any]:
    """Validate the Mesen 2.1.1 MSS envelope and compressed payloads."""

    if len(source) < 64 * 1024 or len(source) > MAX_STATE_BYTES:
        raise TraceLaunchError("native Mesen state size is invalid")
    if source[:3] != b"MSS":
        raise TraceLaunchError("native Mesen state magic is invalid")
    try:
        (
            emulator_version,
            format_version,
            console_type,
            framebuffer_size,
            width,
            height,
            scale,
            compressed_frame_size,
        ) = struct.unpack_from("<8I", source, 3)
    except struct.error as exc:
        raise TraceLaunchError("native Mesen state header is truncated") from exc
    if (
        emulator_version != 131_329
        or format_version != 4
        or console_type != 0
        or framebuffer_size != 122_368
        or width != 256
        or height != 239
        or scale != 100
        or compressed_frame_size == 0
    ):
        raise TraceLaunchError("native Mesen state header fields drifted")
    cursor = 3 + 8 * 4
    frame_end = cursor + compressed_frame_size
    if frame_end + 4 > len(source):
        raise TraceLaunchError("native Mesen screenshot payload is truncated")
    framebuffer = _decompress_exact(
        source[cursor:frame_end],
        framebuffer_size,
        "native Mesen screenshot payload",
    )
    cursor = frame_end
    rom_name_length = struct.unpack_from("<I", source, cursor)[0]
    cursor += 4
    if rom_name_length == 0 or rom_name_length > 255:
        raise TraceLaunchError("native Mesen ROM-name length is invalid")
    name_end = cursor + rom_name_length
    if name_end + 9 > len(source):
        raise TraceLaunchError("native Mesen ROM-name field is truncated")
    try:
        rom_name = source[cursor:name_end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TraceLaunchError("native Mesen ROM name is not UTF-8") from exc
    if rom_name != FIXED_ROM_NAME:
        raise TraceLaunchError(
            f"native Mesen ROM name drifted: expected {FIXED_ROM_NAME}, "
            f"got {rom_name}"
        )
    cursor = name_end
    compressed = source[cursor]
    state_size, stored_state_size = struct.unpack_from("<II", source, cursor + 1)
    cursor += 9
    if compressed != 1:
        raise TraceLaunchError("native Mesen state payload is not compressed")
    if (
        state_size < 64 * 1024
        or state_size > 16 * 1024 * 1024
        or stored_state_size == 0
        or cursor + stored_state_size != len(source)
    ):
        raise TraceLaunchError("native Mesen state payload lengths drifted")
    state = _decompress_exact(
        source[cursor:],
        state_size,
        "native Mesen state payload",
    )
    return {
        "emulator_version": emulator_version,
        "format_version": format_version,
        "console_type": console_type,
        "framebuffer_size": framebuffer_size,
        "width": width,
        "height": height,
        "scale": scale,
        "rom_name": rom_name,
        "decoded_state_size": state_size,
        "decoded_state_sha256": _sha256_bytes(state),
        "framebuffer_sha256": _sha256_bytes(framebuffer),
    }


def _zlib_stored(source: bytes) -> bytes:
    """Return a canonical RFC 1950 stream containing stored DEFLATE blocks."""

    result = bytearray(b"\x78\x01")
    cursor = 0
    if not source:
        result.extend(b"\x01\x00\x00\xff\xff")
    while cursor < len(source):
        chunk = source[cursor : cursor + 65_535]
        cursor += len(chunk)
        result.append(1 if cursor == len(source) else 0)
        result.extend(struct.pack("<H", len(chunk)))
        result.extend(struct.pack("<H", len(chunk) ^ 0xFFFF))
        result.extend(chunk)
    result.extend(struct.pack(">I", zlib.adler32(source) & 0xFFFFFFFF))
    return bytes(result)


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type)
    checksum = binascii.crc32(data, checksum) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", checksum)
    )


def _paeth(left: int, up: int, upper_left: int) -> int:
    predictor = left + up - upper_left
    left_distance = abs(predictor - left)
    up_distance = abs(predictor - up)
    upper_left_distance = abs(predictor - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def canonicalize_png(source: bytes) -> bytes:
    """Re-encode Mesen's endpoint RGB PNG with deterministic stored blocks."""

    if source[:8] != b"\x89PNG\r\n\x1a\n":
        raise TraceLaunchError("checkpoint PNG signature is invalid")
    cursor = 8
    ihdr: bytes | None = None
    idat_parts: list[bytes] = []
    chunk_types: list[bytes] = []
    while cursor < len(source):
        if cursor + 12 > len(source):
            raise TraceLaunchError("checkpoint PNG chunk is truncated")
        length = struct.unpack_from(">I", source, cursor)[0]
        chunk_type = source[cursor + 4 : cursor + 8]
        data_start = cursor + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(source):
            raise TraceLaunchError("checkpoint PNG chunk data is truncated")
        data = source[data_start:data_end]
        expected_crc = struct.unpack_from(">I", source, data_end)[0]
        actual_crc = binascii.crc32(chunk_type)
        actual_crc = binascii.crc32(data, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise TraceLaunchError("checkpoint PNG chunk CRC is invalid")
        chunk_types.append(chunk_type)
        if chunk_type == b"IHDR":
            if ihdr is not None:
                raise TraceLaunchError("checkpoint PNG has duplicate IHDR")
            ihdr = data
        elif chunk_type == b"IDAT":
            idat_parts.append(data)
        elif chunk_type != b"IEND":
            raise TraceLaunchError("checkpoint PNG has an unexpected chunk")
        cursor = crc_end
        if chunk_type == b"IEND":
            break
    if cursor != len(source) or not chunk_types:
        raise TraceLaunchError("checkpoint PNG has trailing or missing chunks")
    if (
        chunk_types[0] != b"IHDR"
        or chunk_types[-1] != b"IEND"
        or ihdr is None
        or not idat_parts
        or len(ihdr) != 13
    ):
        raise TraceLaunchError("checkpoint PNG chunk order is invalid")
    width, height, depth, color, compression, filtering, interlace = (
        struct.unpack(">IIBBBBB", ihdr)
    )
    if (
        width != 256
        or height != 224
        or depth != 8
        or color != 2
        or compression != 0
        or filtering != 0
        or interlace != 0
    ):
        raise TraceLaunchError("checkpoint PNG format drifted")
    expected_filtered_size = height * (width * 3 + 1)
    filtered = _decompress_exact(
        b"".join(idat_parts),
        expected_filtered_size,
        "checkpoint PNG IDAT",
    )
    bytes_per_pixel = 3
    row_bytes = width * bytes_per_pixel
    if len(filtered) != height * (row_bytes + 1):
        raise TraceLaunchError("checkpoint PNG scanline length drifted")
    rows: list[bytes] = []
    prior = bytes(row_bytes)
    source_cursor = 0
    for _ in range(height):
        filter_type = filtered[source_cursor]
        source_cursor += 1
        encoded = filtered[source_cursor : source_cursor + row_bytes]
        source_cursor += row_bytes
        decoded = bytearray(row_bytes)
        for index, value in enumerate(encoded):
            left = decoded[index - bytes_per_pixel] if index >= 3 else 0
            up = prior[index]
            upper_left = prior[index - bytes_per_pixel] if index >= 3 else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _paeth(left, up, upper_left)
            else:
                raise TraceLaunchError("checkpoint PNG uses an unknown filter")
            decoded[index] = (value + predictor) & 0xFF
        row = bytes(decoded)
        rows.append(row)
        prior = row
    canonical_scanlines = b"".join(b"\x00" + row for row in rows)
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", _zlib_stored(canonical_scanlines)),
            _png_chunk(b"IEND", b""),
        )
    )


def canonicalize_mesen_state(source: bytes) -> bytes:
    """Normalize only the non-authoritative MSS preview framebuffer."""

    parse_mesen_state(source)
    compressed_frame_size = struct.unpack_from("<I", source, 31)[0]
    tail_start = 35 + compressed_frame_size
    canonical_frame = _zlib_stored(bytes(122_368))
    canonical = (
        source[:31]
        + struct.pack("<I", len(canonical_frame))
        + canonical_frame
        + source[tail_start:]
    )
    parse_mesen_state(canonical)
    return canonical


def _artifact_record(source: bytes) -> dict[str, Any]:
    return {"size": len(source), "sha256": _sha256_bytes(source)}


def _read_output(
    path: Path,
    label: str,
    *,
    root: Path,
    maximum: int,
) -> bytes:
    return BASE.read_direct_file(
        path,
        label,
        root=root,
        maximum=maximum,
    )


def _publish_outputs(
    output_dir: Path,
    outputs: Mapping[str, bytes],
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    created: list[tuple[Path, tuple[int, int]]] = []
    try:
        for filename, source in outputs.items():
            destination = output_dir / filename
            if (
                destination.parent != output_dir
                or os.path.lexists(destination)
            ):
                raise TraceLaunchError(
                    f"refusing to overwrite checkpoint output: {destination}"
                )
            try:
                with destination.open("xb") as handle:
                    identity = os.fstat(handle.fileno())
                    created.append(
                        (destination, (identity.st_dev, identity.st_ino))
                    )
                    handle.write(source)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError as exc:
                raise TraceLaunchError(
                    f"refusing to overwrite checkpoint output: {destination}"
                ) from exc
            observed = BASE.read_direct_file(
                destination,
                f"published {filename}",
                root=output_dir,
                maximum=max(len(source), 1),
            )
            if observed != source:
                raise TraceLaunchError(f"published {filename} bytes changed")
            records[filename] = {
                "path": str(destination),
                **_artifact_record(source),
            }
    except Exception:
        for destination, identity in reversed(created):
            try:
                current = destination.stat(follow_symlinks=False)
                if (
                    stat.S_ISREG(current.st_mode)
                    and (current.st_dev, current.st_ino) == identity
                ):
                    destination.unlink()
            except OSError:
                pass
        raise
    return records


def _verify_pinned_sizes(paths: Mapping[str, Path]) -> None:
    for label, expected in PINNED_SIZES.items():
        actual = paths[label].stat().st_size
        if actual != expected:
            raise TraceLaunchError(
                f"{label} size mismatch: expected {expected}, got {actual}"
            )


def _run_fresh_verification(
    *,
    mode: str,
    staged_runtime: Mapping[str, Path],
    staged_app: Path,
    staged_verifier: Path,
    staged_rom: Path,
    staged_sram: Path,
    canonical_state: Path,
    staged_outputs: Path,
) -> tuple[bytes, bytes, dict[str, Any]]:
    trace_path = staged_outputs / f"fresh_load_{mode}.tsv"
    screenshot_path = staged_outputs / f"fresh_load_{mode}.png"
    error_path = staged_outputs / f"fresh_load_{mode}.error.txt"
    for path in (trace_path, screenshot_path):
        with path.open("xb"):
            pass
        if path.resolve(strict=True) != path:
            raise TraceLaunchError(
                f"fresh-load {mode} output escaped staging"
            )
    environment = os.environ.copy()
    environment.update(
        {
            "PE_VERIFY_MODE": mode,
            "PE_VERIFY_STATE": str(canonical_state),
            "PE_SRAM_PATH": str(staged_sram),
            "PE_VERIFY_TRACE": str(trace_path),
            "PE_VERIFY_SCREENSHOT": str(screenshot_path),
            "PE_VERIFY_ERROR": str(error_path),
        }
    )
    command = [
        str(staged_runtime["mesen"]),
        "--testRunner",
        "--timeout=60",
        "--doNotSaveSettings",
        "--debug.scriptWindow.allowIoOsAccess=true",
        "--snes.ramPowerOnState=AllZeros",
        "--snes.port1.type=SnesController",
        str(staged_verifier),
        str(staged_rom),
    ]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            command,
            cwd=staged_app,
            env=environment,
            capture_output=True,
            text=True,
            timeout=75,
            check=False,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TraceLaunchError(
            f"fresh-load {mode} Mesen launch failed: {exc}"
        ) from exc
    error_detail = ""
    if os.path.lexists(error_path):
        error_detail = _read_output(
            error_path,
            f"fresh-load {mode} verifier error",
            root=staged_outputs,
            maximum=64 * 1024,
        ).decode("utf-8", errors="replace").strip()
    if completed.returncode != EXPECTED_VERIFY_EXIT_CODE:
        process_detail = (completed.stderr or completed.stdout or "").strip()
        details = " | ".join(
            part for part in (error_detail, process_detail[-1600:]) if part
        )
        suffix = f": {details}" if details else ""
        raise TraceLaunchError(
            f"fresh-load {mode} verifier returned {completed.returncode}, "
            f"expected {EXPECTED_VERIFY_EXIT_CODE}{suffix}"
        )
    if os.path.lexists(error_path):
        raise TraceLaunchError(
            f"fresh-load {mode} verifier reported an error: {error_detail}"
        )
    trace_bytes = _read_output(
        trace_path,
        f"fresh-load {mode} TSV",
        root=staged_outputs,
        maximum=128 * 1024,
    )
    raw_screenshot = _read_output(
        screenshot_path,
        f"fresh-load {mode} PNG",
        root=staged_outputs,
        maximum=MAX_SCREENSHOT_BYTES,
    )
    BASE.describe_artifact_bytes(
        raw_screenshot,
        f"fresh-load {mode} PNG",
        png=True,
    )
    screenshot = canonicalize_png(raw_screenshot)
    document = parse_verification_trace(trace_bytes, mode)
    return trace_bytes, screenshot, document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--mesen", type=Path, default=DEFAULT_MESEN)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--sram", type=Path, default=DEFAULT_SRAM)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--exploratory",
        action="store_true",
        help=(
            "run strict source/input/output controls without enforcing or "
            "claiming the accepted deterministic artifact hashes"
        ),
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.timeout < 30 or args.timeout > 420:
        raise TraceLaunchError("--timeout must be between 30 and 420 seconds")
    exploratory = bool(args.exploratory)
    acceptance_source: bytes | None = None
    accepted_expected: dict[str, tuple[int, str]] | None = None
    if not exploratory:
        (
            acceptance_source,
            _acceptance_contract,
            accepted_expected,
        ) = _load_acceptance_contract()

    # Capture source-controlled executable trust roots before resolving private
    # inputs or creating any output directory.
    collector_source = _require_collector_source()
    verifier_source = _require_verifier_source()
    mesen = BASE.resolve_private_file(args.mesen, "Mesen executable")
    rom = BASE.resolve_private_file(args.rom, "canonical ROM")
    sram = BASE.resolve_private_file(args.sram, "recovered pre-Lavos SRAM")
    private_root = BASE.canonical_private_root()
    archive = BASE.resolve_private_file(
        mesen.parent.parent / "Mesen_2.1.1_Windows.zip",
        "official Mesen archive",
    )
    runtime_paths = {
        "mesen": mesen,
        "mesen_core": BASE.resolve_private_file(
            mesen.parent / "MesenCore.dll",
            "Mesen emulation core",
        ),
        "harfbuzz": BASE.resolve_private_file(
            mesen.parent / "libHarfBuzzSharp.dll",
            "HarfBuzz runtime",
        ),
        "skia": BASE.resolve_private_file(
            mesen.parent / "libSkiaSharp.dll",
            "Skia runtime",
        ),
        "nesdb": BASE.resolve_private_file(
            mesen.parent / "MesenNesDB.txt",
            "Mesen database",
        ),
        "settings": BASE.resolve_private_file(
            mesen.parent / "settings.json",
            "portable Mesen settings",
        ),
    }
    shared_saves = (mesen.parent / "Saves").resolve(strict=True)
    if (
        not shared_saves.is_dir()
        or not BASE._inside(shared_saves, private_root)
    ):
        raise TraceLaunchError(
            "shared Mesen Saves path is not a private directory"
        )
    shared_saves_before = BASE.snapshot_private_files(shared_saves)

    pinned_inputs = {
        "archive": archive,
        **runtime_paths,
        "rom": rom,
        "sram": sram,
        "collector": COLLECTOR_PATH,
        "verifier": VERIFIER_PATH,
        "base_launcher": BASE_LAUNCHER_PATH,
    }
    if acceptance_source is not None:
        pinned_inputs["acceptance_contract"] = ACCEPTANCE_CONTRACT_PATH
    expected_hashes = {
        **RUNTIME_HASHES,
        "collector": COLLECTOR_SHA256,
        "verifier": VERIFIER_SHA256,
        "base_launcher": BASE_LAUNCHER_SHA256,
    }
    if acceptance_source is not None:
        expected_hashes["acceptance_contract"] = (
            ACCEPTANCE_CONTRACT_SHA256
        )
    before = {
        label: BASE.require_hash(path, expected_hashes[label], label)
        for label, path in pinned_inputs.items()
    }
    _verify_pinned_sizes(
        {label: pinned_inputs[label] for label in PINNED_SIZES}
    )
    if _sha256_bytes(collector_source) != before["collector"]:
        raise TraceLaunchError("in-memory collector provenance drifted")
    if _sha256_bytes(verifier_source) != before["verifier"]:
        raise TraceLaunchError("in-memory verifier provenance drifted")
    if (
        acceptance_source is not None
        and _sha256_bytes(acceptance_source)
        != before["acceptance_contract"]
    ):
        raise TraceLaunchError(
            "in-memory acceptance-contract provenance drifted"
        )

    output_dir = BASE.prepare_private_output_dir(
        args.output_dir,
        forbidden_roots=(shared_saves,),
    )
    completed: subprocess.CompletedProcess[str] | None = None
    process_error: Exception | None = None
    staging_error: Exception | None = None
    staged_changed: list[str] = []
    staging_root_after: Path | None = None
    trace_bytes: bytes | None = None
    screenshot_bytes: bytes | None = None
    state_bytes: bytes | None = None
    trace_document: dict[str, Any] | None = None
    state_document: dict[str, Any] | None = None
    collector_error_detail: str | None = None
    control_trace_bytes: bytes | None = None
    down_trace_bytes: bytes | None = None
    down_screenshot_bytes: bytes | None = None
    verification_documents: dict[str, dict[str, Any]] | None = None

    try:
        with tempfile.TemporaryDirectory(
            prefix=".mesen_lavos_checkpoint_staging_",
            dir=output_dir,
        ) as staging_directory:
            staging_root = Path(staging_directory).resolve(strict=True)
            staging_root_after = staging_root
            if not BASE._inside(staging_root, private_root):
                raise TraceLaunchError(
                    "temporary staging directory escaped private/"
                )
            staged_app = staging_root / "app"
            staged_saves = staged_app / "Saves"
            staged_saves.mkdir(parents=True)
            runtime_names = {
                "mesen": "Mesen.exe",
                "mesen_core": "MesenCore.dll",
                "harfbuzz": "libHarfBuzzSharp.dll",
                "skia": "libSkiaSharp.dll",
                "nesdb": "MesenNesDB.txt",
                "settings": "settings.json",
            }
            staged_runtime: dict[str, Path] = {}
            for label, source_path in runtime_paths.items():
                destination = staged_app / runtime_names[label]
                shutil.copyfile(source_path, destination)
                staged_runtime[label] = destination.resolve(strict=True)

            staged_rom = staging_root / FIXED_ROM_NAME
            staged_sram = staged_saves / f"{FIXED_ROM_STEM}.srm"
            staged_collector = staging_root / "mesen_lavos_checkpoint.lua"
            staged_verifier = (
                staging_root / "mesen_lavos_checkpoint_verify.lua"
            )
            shutil.copyfile(rom, staged_rom)
            shutil.copyfile(sram, staged_sram)
            with staged_collector.open("xb") as handle:
                handle.write(collector_source)
            with staged_verifier.open("xb") as handle:
                handle.write(verifier_source)
            staged_rom = staged_rom.resolve(strict=True)
            staged_sram = staged_sram.resolve(strict=True)
            staged_collector = staged_collector.resolve(strict=True)
            staged_verifier = staged_verifier.resolve(strict=True)

            staged_outputs = staging_root / "outputs"
            staged_outputs.mkdir(exist_ok=False)
            staged_trace = staged_outputs / "checkpoint.tsv"
            staged_screenshot = staged_outputs / "endpoint.png"
            staged_state = staged_outputs / "battle_ready.mss"
            staged_error = staged_outputs / "collector-error.txt"
            for path in (staged_trace, staged_screenshot, staged_state):
                with path.open("xb"):
                    pass
                if path.resolve(strict=True) != path:
                    raise TraceLaunchError("staged output path escaped staging")

            staged_files = {
                **staged_runtime,
                "collector": staged_collector,
                "verifier": staged_verifier,
                "rom": staged_rom,
                "sram": staged_sram,
            }
            staged_expected = {
                label: before[label]
                for label in (
                    "mesen",
                    "mesen_core",
                    "harfbuzz",
                    "skia",
                    "nesdb",
                    "settings",
                    "rom",
                    "sram",
                )
            }
            staged_expected["collector"] = before["collector"]
            staged_expected["verifier"] = before["verifier"]
            for label, path in staged_files.items():
                if not BASE._inside(path, staging_root):
                    raise TraceLaunchError(
                        f"staged {label} escaped private temporary root"
                    )
                if BASE.sha256_file(path) != staged_expected[label]:
                    raise TraceLaunchError(
                        f"staged {label} failed exact pre-launch hash check"
                    )

            environment = os.environ.copy()
            environment.update(
                {
                    "PE_SRAM_PATH": str(staged_sram),
                    "PE_CHECKPOINT_TRACE": str(staged_trace),
                    "PE_CHECKPOINT_STATE": str(staged_state),
                    "PE_CHECKPOINT_SCREENSHOT": str(staged_screenshot),
                    "PE_CHECKPOINT_ERROR": str(staged_error),
                }
            )
            command = [
                str(staged_runtime["mesen"]),
                "--testRunner",
                f"--timeout={args.timeout}",
                "--doNotSaveSettings",
                "--debug.scriptWindow.allowIoOsAccess=true",
                "--snes.ramPowerOnState=AllZeros",
                "--snes.port1.type=SnesController",
                str(staged_collector),
                str(staged_rom),
            ]
            creation_flags = (
                subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            try:
                completed = subprocess.run(
                    command,
                    cwd=staged_app,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout + 30,
                    check=False,
                    creationflags=creation_flags,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                process_error = exc

            if os.path.lexists(staged_error):
                try:
                    collector_error_detail = _read_output(
                        staged_error,
                        "staged collector error",
                        root=staged_outputs,
                        maximum=64 * 1024,
                    ).decode("utf-8", errors="replace").strip()
                except Exception as exc:
                    collector_error_detail = (
                        f"unreadable staged collector error: {exc}"
                    )

            for label, path in staged_files.items():
                try:
                    if BASE.sha256_file(path) != staged_expected[label]:
                        staged_changed.append(f"staged {label} changed")
                except OSError:
                    staged_changed.append(f"staged {label} missing")
            try:
                staged_save_entries = sorted(
                    path.name
                    for path in staged_saves.iterdir()
                    if path.is_file()
                )
            except OSError:
                staged_changed.append("staged Saves directory missing")
            else:
                if staged_save_entries != [staged_sram.name]:
                    staged_changed.append(
                        "staged Saves directory contains unexpected files"
                    )

            if (
                process_error is None
                and completed is not None
                and completed.returncode == EXPECTED_EXIT_CODE
            ):
                if os.path.lexists(staged_error):
                    raise TraceLaunchError(
                        "collector reported a staged observer error"
                    )
                trace_bytes = _read_output(
                    staged_trace,
                    "staged checkpoint TSV",
                    root=staged_outputs,
                    maximum=MAX_TRACE_BYTES,
                )
                raw_screenshot_bytes = _read_output(
                    staged_screenshot,
                    "staged checkpoint PNG",
                    root=staged_outputs,
                    maximum=MAX_SCREENSHOT_BYTES,
                )
                raw_state_bytes = _read_output(
                    staged_state,
                    "staged native checkpoint",
                    root=staged_outputs,
                    maximum=MAX_STATE_BYTES,
                )
                BASE.describe_artifact_bytes(
                    raw_screenshot_bytes,
                    "staged checkpoint PNG",
                    png=True,
                )
                trace_document = parse_checkpoint_trace(trace_bytes)
                canonicalize_png(raw_screenshot_bytes)
                state_bytes = canonicalize_mesen_state(raw_state_bytes)
                state_document = parse_mesen_state(state_bytes)
                canonical_state = (
                    staging_root / "canonical_battle_ready.mss"
                )
                with canonical_state.open("xb") as handle:
                    handle.write(state_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                canonical_state = canonical_state.resolve(strict=True)
                if not BASE._inside(canonical_state, staging_root):
                    raise TraceLaunchError(
                        "canonical state escaped private staging"
                    )
                canonical_state_hash = BASE.sha256_file(canonical_state)

                (
                    control_trace_bytes,
                    screenshot_bytes,
                    control_document,
                ) = _run_fresh_verification(
                    mode="control",
                    staged_runtime=staged_runtime,
                    staged_app=staged_app,
                    staged_verifier=staged_verifier,
                    staged_rom=staged_rom,
                    staged_sram=staged_sram,
                    canonical_state=canonical_state,
                    staged_outputs=staged_outputs,
                )
                (
                    down_trace_bytes,
                    down_screenshot_bytes,
                    down_document,
                ) = _run_fresh_verification(
                    mode="down",
                    staged_runtime=staged_runtime,
                    staged_app=staged_app,
                    staged_verifier=staged_verifier,
                    staged_rom=staged_rom,
                    staged_sram=staged_sram,
                    canonical_state=canonical_state,
                    staged_outputs=staged_outputs,
                )
                if BASE.sha256_file(canonical_state) != canonical_state_hash:
                    raise TraceLaunchError(
                        "canonical state changed during fresh-load verification"
                    )
                control_baseline = {
                    key: value
                    for key, value in control_document["baseline"].items()
                    if key != "mode"
                }
                down_baseline = {
                    key: value
                    for key, value in down_document["baseline"].items()
                    if key != "mode"
                }
                if control_baseline != down_baseline:
                    raise TraceLaunchError(
                        "fresh-load control/down baselines differ"
                    )
                if (
                    control_document["baseline"]["battle_ui"]
                    != trace_document["endpoint"]["battle_ui"]
                    or control_document["baseline"]["command_state"]
                    != trace_document["endpoint"]["command_state"]
                ):
                    raise TraceLaunchError(
                        "fresh-loaded command state does not match capture"
                    )
                comparable_control = {
                    key: value
                    for key, value in control_document["endpoint"].items()
                    if key not in {"mode", "battle_ui", "command_state"}
                }
                comparable_down = {
                    key: value
                    for key, value in down_document["endpoint"].items()
                    if key not in {"mode", "battle_ui", "command_state"}
                }
                if comparable_control != comparable_down:
                    raise TraceLaunchError(
                        "Down proof changed a non-command endpoint anchor"
                    )
                control_menu_slot, control_cursor = _command_cursor(
                    control_document["endpoint"]["command_state"],
                    "fresh-load control endpoint command state",
                )
                baseline_menu_slot, baseline_cursor = _command_cursor(
                    control_document["baseline"]["command_state"],
                    "fresh-load control baseline command state",
                )
                down_menu_slot, down_cursor = _command_cursor(
                    down_document["endpoint"]["command_state"],
                    "fresh-load Down endpoint command state",
                )
                if (
                    control_menu_slot != baseline_menu_slot
                    or control_cursor != baseline_cursor
                ):
                    raise TraceLaunchError(
                        "control proof did not restore the command cursor"
                    )
                if (
                    control_menu_slot != down_menu_slot
                    or down_cursor != (control_cursor + 1) % 3
                ):
                    raise TraceLaunchError(
                        "Down proof did not advance the command cursor: "
                        f"control={control_menu_slot}/{control_cursor}, "
                        f"down={down_menu_slot}/{down_cursor}"
                    )
                if screenshot_bytes == down_screenshot_bytes:
                    raise TraceLaunchError(
                        "Down proof did not change the rendered command menu"
                    )
                verification_documents = {
                    "control": control_document,
                    "down": down_document,
                    "proof": {
                        "baseline_exact": True,
                        "non_command_anchors_exact": True,
                        "command_cursor_advanced": True,
                        "control_cursor_restored": True,
                        "control_cursor": control_cursor,
                        "down_cursor": down_cursor,
                        "rendered_menu_changed": True,
                    },
                }

                # Recheck every disposable input after both fresh processes.
                for label, path in staged_files.items():
                    try:
                        if BASE.sha256_file(path) != staged_expected[label]:
                            staged_changed.append(
                                f"staged {label} changed after fresh load"
                            )
                    except OSError:
                        staged_changed.append(
                            f"staged {label} missing after fresh load"
                        )
                try:
                    final_save_entries = sorted(
                        path.name
                        for path in staged_saves.iterdir()
                        if path.is_file()
                    )
                except OSError:
                    staged_changed.append(
                        "staged Saves directory missing after fresh load"
                    )
                else:
                    if final_save_entries != [staged_sram.name]:
                        staged_changed.append(
                            "staged Saves directory changed after fresh load"
                        )
    except Exception as exc:
        staging_error = exc

    changed: list[str] = []
    for label, path in pinned_inputs.items():
        try:
            after = BASE.sha256_file(path)
        except OSError:
            changed.append(f"{label} missing")
            continue
        if after != before[label]:
            changed.append(f"{label} changed")
    if changed:
        raise TraceLaunchError(
            "immutable emulator/source input mutation detected: "
            + ", ".join(changed)
        )
    if BASE.snapshot_private_files(shared_saves) != shared_saves_before:
        raise TraceLaunchError("shared Mesen Saves directory changed")
    if staging_root_after is not None and os.path.lexists(staging_root_after):
        raise TraceLaunchError(
            "disposable ROM/SRAM staging directory was not deleted"
        )
    if staged_changed:
        raise TraceLaunchError(
            "disposable emulator input mutation detected: "
            + ", ".join(staged_changed)
        )
    if staging_error is not None:
        if isinstance(staging_error, TraceLaunchError):
            raise staging_error
        raise TraceLaunchError(
            f"private Lavos-checkpoint staging failed: {staging_error}"
        ) from staging_error
    if process_error is not None:
        raise TraceLaunchError(
            f"Mesen launch failed: {process_error}"
        ) from process_error
    assert completed is not None
    if completed.returncode != EXPECTED_EXIT_CODE:
        process_detail = (completed.stderr or completed.stdout or "").strip()
        detail_parts = []
        if collector_error_detail:
            detail_parts.append(f"collector: {collector_error_detail}")
        if process_detail:
            detail_parts.append(process_detail[-1600:])
        detail = " | ".join(detail_parts)
        suffix = f": {detail}" if detail else ""
        raise TraceLaunchError(
            f"Mesen returned {completed.returncode}, expected "
            f"{EXPECTED_EXIT_CODE}{suffix}"
        )
    if (
        trace_bytes is None
        or screenshot_bytes is None
        or state_bytes is None
        or trace_document is None
        or state_document is None
        or control_trace_bytes is None
        or down_trace_bytes is None
        or down_screenshot_bytes is None
        or verification_documents is None
    ):
        raise TraceLaunchError(
            "Mesen did not produce all valid checkpoint outputs"
        )

    deterministic_outputs = {
        "battle_ready.mss": state_bytes,
        "checkpoint.tsv": trace_bytes,
        "fresh_load_control.tsv": control_trace_bytes,
        "fresh_load_down.tsv": down_trace_bytes,
    }
    presentation_outputs = {
        "endpoint.png": screenshot_bytes,
        "command_down.png": down_screenshot_bytes,
    }
    if not exploratory:
        if accepted_expected is None:
            raise TraceLaunchError(
                "accepted run has no deterministic artifact contract"
            )
        _verify_accepted_deterministic_artifacts(
            deterministic_outputs,
            accepted_expected,
        )

    presentation_document = _build_presentation_manifest(
        presentation_outputs
    )
    presentation_bytes = _json_bytes(presentation_document)
    checkpoint_document = {
        **{
            key: value
            for key, value in trace_document.items()
            if not key.startswith("_")
        },
        "status": "validated-native-checkpoint",
        "runtime": {
            f"{label}_sha256": before[label]
            for label in (
                "archive",
                "base_launcher",
                "collector",
                "harfbuzz",
                "mesen",
                "mesen_core",
                "nesdb",
                "rom",
                "settings",
                "skia",
                "sram",
                "verifier",
            )
        },
        "launch_profile": {
            "fixed_rom_name": FIXED_ROM_NAME,
            "ram_power_on_state": "AllZeros",
            "controller": "SnesController",
            "test_runner": True,
            "settings_writes_disabled": True,
        },
        "native_state": state_document,
        "fresh_load_verification": verification_documents,
        "normalization": {
            "mss_preview_framebuffer": (
                "all-zero-non-authoritative-preview-canonicalized"
            ),
            "presentation_png": (
                "decoded-rgb-preserved-filter0-stored-deflate"
            ),
        },
        **_checkpoint_artifact_sections(deterministic_outputs),
    }
    checkpoint_bytes = _json_bytes(checkpoint_document)
    artifacts = _publish_outputs(
        output_dir,
        {
            **deterministic_outputs,
            **presentation_outputs,
            "checkpoint.json": checkpoint_bytes,
            "presentation_manifest.json": presentation_bytes,
        },
    )
    return {
        "status": (
            "exploratory-private-checkpoint-not-accepted"
            if exploratory
            else "accepted-private-checkpoint"
        ),
        "exit_code": completed.returncode,
        "endpoint_frame": trace_document["_absolute_endpoint_frame"],
        "accepted_deterministic_artifacts": not exploratory,
        "presentation_artifacts_accepted": False,
        "artifacts": artifacts,
        "immutable_inputs_preserved": True,
        "shared_mesen_saves_preserved": True,
        "disposable_staging_deleted": True,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except TraceLaunchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
