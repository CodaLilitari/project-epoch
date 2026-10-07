#!/usr/bin/env python3
"""Acquire a private clean-ROM cold-boot load boundary, or replay that boundary.

Requires an explicit private SRAM file and SHA-256. No emulator runs at import.
The MSS is at C2E657; CPU/WRAM/SRAM observations are before FFFAA3's PHP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "tools/run_mesen_lavos_battle_checkpoint.py"
BASE_SHA = "377024c212a72c4e2f3b000e44a7573cedd94093f86463c665be8925ae8c6321"
COLLECTOR = ROOT / "tools/mesen_load_entry_checkpoint_v1.lua"
SCHEMA = "project-epoch-load-entry-checkpoint-v1"
ARTIFACTS = ("checkpoint.tsv", "endpoint.png", "load_entry.mss",
             "entry_wram.bin", "entry_sram.bin", "entry_cpu.txt")
CPU_KEYS = ("k", "pc", "sp", "ps", "d", "dbr", "a", "x", "y")
REPLAY_ENV = ("PE_LOAD_ENTRY_STATE", "PE_LOAD_ENTRY_EXPECT_WRAM", "PE_LOAD_ENTRY_EXPECT_CPU")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_argument(value: str) -> str:
    value = value.lower()
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise argparse.ArgumentTypeError("an explicit 64-hex SHA-256 is required")
    return value


def parse_cpu(raw: bytes) -> dict[str, int | bool]:
    lines = raw.decode("ascii").splitlines()
    if len(lines) != 10 or lines[-1] != "emulationMode=false":
        raise ValueError("CPU tuple shape/native mode")
    result: dict[str, int | bool] = {"emulationMode": False}
    for key, line in zip(CPU_KEYS, lines[:-1]):
        prefix = key + "="
        if not line.startswith(prefix) or not line[len(prefix):].isdigit():
            raise ValueError("CPU tuple field: " + key)
        value = int(line[len(prefix):])
        if value > (255 if key in ("k", "ps", "dbr") else 65535):
            raise ValueError("CPU tuple range: " + key)
        result[key] = value
    if (result["k"], result["pc"], result["d"], result["dbr"]) != (255, 0xFAA3, 0, 0x7E):
        raise ValueError("load-entry CPU boundary")
    if result["ps"] & 0x30 != 0x30:
        raise ValueError("load-entry widths")
    if result["sp"] > 0x1FFC:
        raise ValueError("caller frame outside low-WRAM mirror")
    return result


def trace_rows(raw: str) -> list[tuple[str, dict[str, str]]]:
    rows = []
    for line in raw.splitlines():
        cells = line.split("\t")
        if len(cells) < 3 or not cells[1].isdigit():
            raise ValueError("trace row shape")
        values = {}
        for cell in cells[2:]:
            key, sep, value = cell.partition("=")
            if not sep or not key or key in values:
                raise ValueError("trace field shape")
            values[key] = value
        rows.append((cells[0], values))
    return rows


def validate_capture(directory: Path, sram: bytes, *, replay: bool) -> dict:
    """Validate emitted boundaries, not emulator authenticity or whole-loader behavior."""
    if len(sram) != 8192:
        raise ValueError("input SRAM size")
    wram = (directory / "entry_wram.bin").read_bytes()
    if len(wram) != 0x20000 or (directory / "entry_sram.bin").read_bytes() != sram:
        raise ValueError("entry WRAM size or exact SRAM")
    if not (directory / "load_entry.mss").stat().st_size:
        raise ValueError("empty checkpoint")
    cpu = parse_cpu((directory / "entry_cpu.txt").read_bytes())
    sp = cpu["sp"]
    if bytes(wram[(sp + i) & 0xFFFF] for i in (1, 2, 3)) != b"\x5a\xe6\xc2":
        raise ValueError("native caller return frame")
    if wram[0x79] != 0:
        raise ValueError("selected physical slot")
    rows = trace_rows((directory / "checkpoint.tsv").read_text(encoding="utf-8"))
    kinds = [kind for kind, _ in rows]
    if not kinds or kinds[-1] != "success" or kinds.count("success") != 1 or kinds.count("load-entry") != 1:
        raise ValueError("load-entry/success trace cardinality")
    if any(kind.startswith("failure:") for kind in kinds):
        raise ValueError("failure in successful trace")
    entry_index = kinds.index("load-entry")
    entry = rows[entry_index][1]
    if entry_index != len(rows) - 2 or entry.get("slot") != "0" or entry.get("return_frame") != "5ae6c2":
        raise ValueError("load-entry trace boundary")
    if any(entry.get("cpu." + key) != str(cpu[key]) for key in CPU_KEYS):
        raise ValueError("CPU tuple differs from trace")
    validation = []
    if replay:
        if kinds.count("checkpoint-restored") != 1 or kinds.index("checkpoint-restored") >= entry_index:
            raise ValueError("missing successful replay restore")
        restored = rows[kinds.index("checkpoint-restored")][1]
        if (restored.get("cpu.k"), restored.get("cpu.pc")) != ("194", str(0xE657)):
            raise ValueError("restored caller PC")
        if "load-caller" in kinds or any(kind.startswith("validation-") for kind in kinds):
            raise ValueError("replay presented as cold-boot validation")
    else:
        if kinds.count("load-caller") != 1 or "checkpoint-restored" in kinds:
            raise ValueError("cold-boot caller cardinality")
        caller_index = kinds.index("load-caller")
        caller = rows[caller_index][1]
        if caller_index >= entry_index or (caller.get("cpu.k"), caller.get("cpu.pc"), caller.get("slot")) != ("194", str(0xE657), "0"):
            raise ValueError("cold-boot caller boundary")
        pending = []
        for index, (kind, values) in enumerate(rows):
            if kind == "outside-scope-validation":
                if (index >= caller_index or pending or validation or values.get("scope") != "outside-D0"
                        or not values.get("cpu.d", "").isdigit() or int(values["cpu.d"]) == 0
                        or (values.get("cpu.k"), values.get("cpu.pc")) != ("255", str(0xF9C4))
                        or "slot" in values):
                    raise ValueError("outside-D0 validation scope/order")
                continue
            if not kind.startswith("validation-"):
                continue
            if index >= caller_index or values.get("slot") != "0":
                raise ValueError("validation ordering/slot")
            expected = ("validation-entry", "validation-compare", "validation-return")[len(pending)]
            if kind != expected:
                raise ValueError("unmatched native validation")
            pending.append(values)
            if len(pending) == 3:
                begin, compare, end = pending
                if any(row.get("cpu.k") != "255" or row.get("cpu.d") != "0" for row in pending):
                    raise ValueError("validation CPU context")
                if [row.get("cpu.pc") for row in pending] != [str(x) for x in (0xF9C4, 0xF9E3, 0xF9FA)]:
                    raise ValueError("validation native PCs")
                checksum = int.from_bytes(sram[0x1FF0:0x1FF2], "little")
                if (compare.get("stored_checksum"), compare.get("cpu.a"), compare.get("magic")) != (str(checksum), str(checksum), str(0xE41B)):
                    raise ValueError("native checksum equality")
                if sram[0x1FF8:0x1FFA] != b"\x1b\xe4" or compare.get("cpu.x") != "0" or compare.get("cpu.dbr") != "48" or int(compare["cpu.ps"]) & 0x30:
                    raise ValueError("checksum magic/index/widths")
                if end.get("result") != "0" or any(begin.get(key) != end.get(key) for key in ("cpu.sp", "cpu.dbr", "return_frame")):
                    raise ValueError("validation result/return context")
                if not re.fullmatch(r"[0-9a-f]{6}", begin.get("return_frame", "")):
                    raise ValueError("validation return frame")
                validation.append({"entry": begin, "compare": compare, "return": end})
                pending = []
        if pending or not validation:
            raise ValueError("missing completed selected-slot validation")
    return {
        "schema": "project-epoch-native-entry-contract-v1", "mode": "load",
        "checkpoint_pc": "C2E657", "entry_pc": "FFFAA3", "caller_stored_return": "C2E65A",
        "physical_slot": 0, "cpu": cpu, "wram_bytes": len(wram), "sram_bytes": len(sram),
        "cold_boot": not replay, "validation_observed_this_process": not replay,
        "native_validation_sequences": validation,
        "scope": "selected-slot preview validation then pre-region-copy entry; not whole-loader proof",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sram", type=Path, required=True, help="Exact existing private SRAM path")
    parser.add_argument("--sram-sha256", type=sha256_argument, required=True)
    parser.add_argument("--verify-from", type=Path, help="Accepted cold-boot acquisition; replay is not cold boot")
    args = parser.parse_args()
    raw = BASE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError("base launcher drift")
    mod = types.ModuleType("_load_entry_lavos_base")
    mod.__file__ = str(BASE_PATH)
    sys.modules[mod.__name__] = mod
    exec(compile(raw, str(BASE_PATH), "exec"), mod.__dict__)
    base = mod.BASE
    mesen = base.resolve_private_file(mod.DEFAULT_MESEN, "Mesen")
    shared = (mesen.parent / "Saves").resolve(strict=True)
    shared_before = base.snapshot_private_files(shared)
    names = {"mesen": "Mesen.exe", "mesen_core": "MesenCore.dll", "harfbuzz": "libHarfBuzzSharp.dll",
             "skia": "libSkiaSharp.dll", "nesdb": "MesenNesDB.txt", "settings": "settings.json"}
    inputs = {key: base.resolve_private_file(mesen.parent / name, key) for key, name in names.items()}
    inputs.update(rom=base.resolve_private_file(mod.DEFAULT_ROM, "ROM"),
                  sram=base.resolve_private_file(args.sram, "explicit SRAM"),
                  archive=base.resolve_private_file(mesen.parent.parent / "Mesen_2.1.1_Windows.zip", "archive"))
    pins = {**mod.RUNTIME_HASHES, "sram": args.sram_sha256}
    before = {key: base.require_hash(path, pins[key], key) for key, path in inputs.items()}
    for key, path in inputs.items():
        if path.stat().st_size != (8192 if key == "sram" else mod.PINNED_SIZES[key]):
            raise ValueError("input size: " + key)
    input_sram = inputs["sram"].read_bytes()
    sources = {"runner": Path(__file__).resolve(), "collector": COLLECTOR, "base": BASE_PATH}
    source_hashes = {key: sha(path) for key, path in sources.items()}
    verify_paths = {}
    prior = None
    if args.verify_from:
        prior = base.resolve_private_file(args.verify_from / "receipt.json", "acquisition receipt")
        prior_doc = json.loads(prior.read_text(encoding="utf-8"))
        if prior_doc.get("schema") != SCHEMA or prior_doc.get("accepted") is not True or prior_doc.get("acquisition_mode") != "cold-boot":
            raise ValueError("requires accepted cold-boot acquisition")
        if prior_doc.get("input_hashes") != before:
            raise ValueError("replay input identity differs from acquisition")
        for key, name in (("state", "load_entry.mss"), ("wram", "entry_wram.bin"), ("cpu", "entry_cpu.txt"),
                          ("sram", "entry_sram.bin"), ("contract", "native_entry_contract.json"), ("trace", "checkpoint.tsv")):
            path = base.resolve_private_file(prior.parent / name, "acquisition " + key)
            meta = prior_doc["artifacts"][name]
            if sha(path) != meta["sha256"] or path.stat().st_size != meta["bytes"]:
                raise ValueError("acquisition artifact drift: " + key)
            verify_paths[key] = path
        cold_contract = validate_capture(prior.parent, input_sram, replay=False)
        if json.loads(verify_paths["contract"].read_text(encoding="utf-8")) != cold_contract:
            raise ValueError("acquisition detail contract differs from its artifacts")
        verify_paths["receipt"] = prior
    verify_hashes = {key: sha(path) for key, path in verify_paths.items()}
    out = base.prepare_private_output_dir(args.output_dir, forbidden_roots=(shared,))
    app = out / "isolated_runtime"
    (app / "Saves").mkdir(parents=True)
    for key, name in names.items():
        shutil.copyfile(inputs[key], app / name)
    rom, sram, lua = out / "load_entry_clean.sfc", app / "Saves/load_entry_clean.srm", out / COLLECTOR.name
    for source, target in ((inputs["rom"], rom), (inputs["sram"], sram), (COLLECTOR, lua)):
        shutil.copyfile(source, target)
    staged = {**{key: app / name for key, name in names.items()}, "rom": rom, "sram": sram, "collector": lua}
    env = os.environ.copy()
    for key in REPLAY_ENV:
        env.pop(key, None)
    env.update(PE_LOAD_ENTRY_SRAM=str(sram), PE_LOAD_ENTRY_OUTPUT=str(out))
    if verify_paths:
        for key in ("state", "wram", "cpu"):
            target = out / ("verify_input." + key)
            shutil.copyfile(verify_paths[key], target)
            staged["verify_" + key] = target
        env.update(PE_LOAD_ENTRY_STATE=str(staged["verify_state"]), PE_LOAD_ENTRY_EXPECT_WRAM=str(staged["verify_wram"]), PE_LOAD_ENTRY_EXPECT_CPU=str(staged["verify_cpu"]))
    staged_before = {key: sha(path) for key, path in staged.items()}
    if any(staged_before[key] != before[key] for key in before if key != "archive") or staged_before["collector"] != source_hashes["collector"]:
        raise ValueError("staging mismatch")
    if any(staged_before["verify_" + key] != verify_hashes[key] for key in ("state", "wram", "cpu") if verify_paths):
        raise ValueError("replay staging mismatch")
    cmd = [str(app / "Mesen.exe"), "--testRunner", "--timeout=120", "--doNotSaveSettings",
           "--debug.scriptWindow.allowIoOsAccess=true", "--snes.ramPowerOnState=AllZeros",
           "--snes.port1.type=SnesController", str(lua), str(rom)]
    completed, error = None, None
    try:
        completed = subprocess.run(cmd, cwd=app, env=env, capture_output=True, text=True, timeout=145,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except Exception as exc:
        error = repr(exc)
    after = {key: sha(path) for key, path in inputs.items()}
    staged_after = {key: sha(path) for key, path in staged.items()}
    source_after = {key: sha(path) for key, path in sources.items()}
    shared_preserved = shared_before == base.snapshot_private_files(shared)
    verify_preserved = verify_hashes == {key: sha(path) for key, path in verify_paths.items()}
    changes = [key for key in staged if staged_before[key] != staged_after[key]]
    preserved = before == after and source_hashes == source_after and shared_preserved and verify_preserved and set(changes) <= {"sram"}
    accepted = bool(completed and completed.returncode == 49 and preserved)
    if accepted:
        try:
            contract = validate_capture(out, input_sram, replay=bool(verify_paths))
            if verify_paths:
                for key, name in (("wram", "entry_wram.bin"), ("cpu", "entry_cpu.txt"), ("sram", "entry_sram.bin"), ("state", "load_entry.mss")):
                    if (out / name).read_bytes() != verify_paths[key].read_bytes():
                        raise ValueError("replay output differs: " + key)
                contract["cold_boot_validation_receipt"] = {"path": str(prior), "sha256": verify_hashes["receipt"]}
            (out / "native_entry_contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8", newline="\n")
        except Exception as exc:
            accepted, error = False, repr(exc)
    artifacts = {name: {"bytes": (out / name).stat().st_size, "sha256": sha(out / name)}
                 for name in (*ARTIFACTS, "native_entry_contract.json") if (out / name).is_file()}
    accepted = accepted and set(artifacts) == set((*ARTIFACTS, "native_entry_contract.json"))
    reproduction = ["python", "tools/run_mesen_load_entry_checkpoint_v1.py", "--output-dir",
                    "private/test_runs/mesen2/NEW_EMPTY_LOAD_ENTRY_RUN", "--sram", str(inputs["sram"]), "--sram-sha256", args.sram_sha256]
    if args.verify_from:
        reproduction += ["--verify-from", str(prior.parent)]
    receipt = {
        "schema": SCHEMA, "accepted": accepted,
        "evidence_level": "observed-runtime-checkpoint" if accepted else "rejected-pilot",
        "acquisition_mode": "checkpoint-replay" if verify_paths else "cold-boot",
        "fresh_process_resume": bool(verify_paths), "rom_mutated": False,
        "checkpoint_pc": "C2E657", "observed_entry_pc": "FFFAA3", "caller_stored_return": "C2E65A",
        "execution_boundary": "MSS at caller C2E657; CPU/WRAM/SRAM before FFFAA3 PHP; deferred stop permits later execution",
        "input_paths": {key: str(path) for key, path in inputs.items()}, "input_hashes": before, "input_hashes_after": after,
        "source_hashes": source_hashes, "source_hashes_after": source_after,
        "staged_hashes_before": staged_before, "staged_hashes_after": staged_after, "staged_changes": changes,
        "immutable_inputs_preserved": before == after, "shared_saves_preserved": shared_preserved,
        "all_preservation_checks_pass": preserved, "verification_input_paths": {key: str(path) for key, path in verify_paths.items()},
        "verification_input_hashes": verify_hashes, "artifacts": artifacts, "command": cmd, "reproduction": reproduction,
        "returncode": completed.returncode if completed else None, "process_error": error,
        "stdout": completed.stdout if completed else None, "stderr": completed.stderr if completed else None,
        "limitations": ["bounded selected-slot validation and pre-copy entry, not whole-loader or PC07 proof",
                        "checkpoint replay is not cold boot; native validation belongs to its referenced acquisition",
                        "SRAM hash establishes input identity, not evidence that a future native save produced it",
                        "exact entry CPU tuple and WRAM/SRAM equality, not complete hardware/timing equality",
                        "post-stop disposable SRAM may differ; entry SRAM must equal the exact input",
                        "inputPolled counts are not independently verified video-frame counts; screenshot is optional presentation"],
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"accepted": accepted, "output_dir": str(out), "receipt_sha256": sha(out / "receipt.json"), "returncode": receipt["returncode"]}, indent=2))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
