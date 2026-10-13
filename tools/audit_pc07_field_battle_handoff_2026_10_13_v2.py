"""Read-only reproduction of the frozen field/battle handoff after guard drift.

The one permitted source resolution is pinned below. No original source,
evidence, image, save, or patch is written. See the v2 companion report.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BASE = "pc07_field_battle_handoff_2026_10_13"
RUN_RECEIPT = "private/test_runs/pc07_field_battle_route_v2_run1/receipt.json"
RUN_RECEIPT_SHA = "b963773dc8c56dafcf8cc1725e63d0bd2100100f163d4ee46406bf72261f411b"
REFERENCE = f"references/{BASE}.json"
REFERENCE_SHA = "8aa574931621bea81350516d2f054d96dbbf8728933d372650d7fbb057ae9d13"
BUNDLE_SHA = "26114966b15ab41b807de0d8ab467db1e8e1a2ad6651855f439e74cd8b5dc9fd"
GUARD = "tools/validate_rom_write_intents.py"
ARCHIVE = "private/research/pc07_first_attack_builder_20261013/validate_rom_write_intents.before.py"
GUARD_ROW = {"path": GUARD, "bytes": 39623,
             "sha256": "d109fa0ca691652a82c1d8f3ffab7ebbec7c57342e5cc1c6e472dea60bc8aac2"}
COLLECTOR = "private/research/pc07_field_battle_collector_v2_20261013"
RUNNER = f"{COLLECTOR}/run_route_v2.py"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular_bytes(path):
    path = Path(path)
    for part in (path, *path.parents):
        if part.is_symlink() or (
                part.exists() and getattr(part.stat(), "st_file_attributes", 0) & 0x400):
            raise ValueError(f"symlink/reparse input refused: {part}")
    if not path.is_file():
        raise ValueError(f"regular input file required: {path}")
    return path.read_bytes()


def checked(relative, digest, size=None, reader=regular_bytes):
    raw = reader(ROOT / relative)
    if sha(raw) != digest or (size is not None and len(raw) != size):
        raise ValueError(f"source identity mismatch: {relative}")
    return raw


def identity(relative):
    raw = regular_bytes(ROOT / relative)
    return {"path": relative, "bytes": len(raw), "sha256": sha(raw)}


def prepare_sources(reader=regular_bytes):
    """Verify all frozen rows and supporting pins before executing project code."""
    receipt_raw = checked(RUN_RECEIPT, RUN_RECEIPT_SHA, 58728, reader)
    reference_raw = checked(REFERENCE, REFERENCE_SHA, 7334, reader)
    receipt = json.loads(receipt_raw.decode("utf-8"))
    reference = json.loads(reference_raw.decode("utf-8"))
    bundle = receipt["source_bundle"]
    rows = bundle["sources"]
    if len(rows) != 54 or bundle["sha256"] != BUNDLE_SHA:
        raise ValueError("frozen 54-row source bundle required")
    if sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()) != BUNDLE_SHA:
        raise ValueError("frozen source row hash mismatch")
    if len({row["path"] for row in rows}) != 54:
        raise ValueError("duplicate frozen source path")
    if [row for row in rows if row["path"] == GUARD] != [GUARD_ROW]:
        raise ValueError("exact historical guard row required")
    source_bytes = {}
    for row in rows:
        if set(row) != {"path", "bytes", "sha256"}:
            raise ValueError("unexpected historical source row fields")
        relative = ARCHIVE if row["path"] == GUARD else row["path"]
        source_bytes[row["path"]] = checked(relative, row["sha256"], row["bytes"], reader)
    # The pinned public reference owns these identities. It is never regenerated
    # from current source or accepted merely because its parsed claims look right.
    extra_rows = [reference[key] for key in
                  ("human_report", "auditor", "independent_receipt", "independent_reproducer")]
    disposition = reference["uninstalled_battle_adapter_source_review"]
    extra_rows += [disposition[key] for key in ("facts", "reproducer", "receipt")]
    for row in extra_rows:
        source_bytes[row["path"]] = checked(row["path"], row["sha256"], row["bytes"], reader)
    return {"rows": rows, "source_bytes": source_bytes, "reference": reference}


def load_verified(name, relative, raw):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / relative)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(raw.decode("utf-8"), module.__file__, "exec"), module.__dict__)
    return module


@contextlib.contextmanager
def historical_imports(prepared):
    """Adapt only run_route_v2.read_pinned and the historical guard import.

    The runner performs its pin loop at import time. Execute its original AST
    statements in two phases, separated at the PINS assignment, so its already
    defined read_pinned can be wrapped before that loop. No node is rewritten or
    omitted; its bundle(), validator and imported frozen review remain original.
    """
    prior_modules = set(sys.modules)
    prior_path = list(sys.path)
    project_names = {Path(row["path"]).stem for row in prepared["rows"]
                     if row["path"].endswith(".py")}
    project_names.update({"validate_rom_write_intents", "run_route_v2", "epoch_handoff_v1"})
    if project_names.intersection(prior_modules):
        raise ValueError("fresh Python process required; historical project module already imported")
    sys.path[:0] = [str(ROOT / COLLECTOR), str(ROOT / "tools")]
    try:
        load_verified("validate_rom_write_intents", ARCHIVE, prepared["source_bytes"][GUARD])
        raw = prepared["source_bytes"][RUNNER]
        filename = str(ROOT / RUNNER)
        tree = ast.parse(raw.decode("utf-8"), filename=filename)
        splits = [i for i, node in enumerate(tree.body)
                  if isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "PINS"]
        if len(splits) != 1:
            raise ValueError("frozen runner PINS boundary shape mismatch")
        split = splits[0]
        if not (isinstance(tree.body[split - 1], ast.FunctionDef)
                and tree.body[split - 1].name == "read_pinned"
                and isinstance(tree.body[split + 1], ast.For)):
            raise ValueError("frozen runner read_pinned/PINS/loop sequence mismatch")
        runner = types.ModuleType("run_route_v2")
        runner.__file__ = filename
        runner.__package__ = ""
        sys.modules[runner.__name__] = runner
        first = ast.Module(body=tree.body[:split], type_ignores=[])
        rest = ast.Module(body=tree.body[split:], type_ignores=[])
        exec(compile(first, filename, "exec"), runner.__dict__)
        original_read = runner.read_pinned

        def historical_read(path, digest, size=None):
            if Path(path).absolute() == (ROOT / GUARD).absolute():
                if digest != GUARD_ROW["sha256"] or size != GUARD_ROW["bytes"]:
                    raise ValueError("historical guard requested with unapproved identity")
                return checked(ARCHIVE, digest, size)
            return original_read(path, digest, size)

        runner.read_pinned = historical_read
        exec(compile(rest, filename, "exec"), runner.__dict__)
        if runner.bundle() != {"sha256": BUNDLE_SHA, "sources": prepared["rows"]}:
            raise ValueError("historical runner bundle changed after source resolution")
        yield
    finally:
        sys.path[:] = prior_path
        for name in list(set(sys.modules) - prior_modules):
            module_path = getattr(sys.modules.get(name), "__file__", None)
            if module_path is not None and Path(module_path).absolute().is_relative_to(ROOT):
                del sys.modules[name]


def audit():
    prepared = prepare_sources()
    with historical_imports(prepared):
        old = prepared["reference"]["auditor"]["path"]
        original = load_verified("epoch_handoff_v1", old, prepared["source_bytes"][old])
        checkpoint = original.audit()
        if checkpoint != prepared["reference"]:
            raise ValueError("frozen public checkpoint reproduction mismatch")
    # Refuse source drift during the read-only replay as well as before imports.
    after = prepare_sources()
    if prepared != after:
        raise ValueError("frozen inputs changed during reproduction")
    return {
        "schema": "project-epoch-pc07-field-battle-handoff-reproduction-2026-10-13-v2",
        "evidence_level": "read-only offline reproduction of the unchanged accepted checkpoint",
        "human_report": identity(f"docs/{BASE}_v2.md"),
        "auditor": identity(f"tools/audit_{BASE}_v2.py"),
        "frozen_public_reference": identity(REFERENCE),
        "source_resolution": {
            "source_count": 54, "source_bundle_sha256": BUNDLE_SHA,
            "resolved_source_count": 1, "logical_guard": GUARD_ROW,
            "archived_guard": identity(ARCHIVE),
            "all_source_rows_verified_before_project_execution": True,
            "all_source_rows_rechecked_after_reproduction": True,
            "runner_adapter": "original AST split before PINS; exact guard-only read_pinned wrapper",
            "global_filesystem_patch": False,
            "unchanged_frozen_public_report_reproduced": True,
        },
        "frozen_checkpoint_v1": checkpoint,
        "new_emulator_run": False, "new_rom_or_patch_emitted": False,
        "frozen_sources_or_evidence_modified": False,
        "publication_performed": False,
        "reproduction": f"python -B tools/audit_{BASE}_v2.py",
        "refusal_check": f"python -B tools/audit_{BASE}_v2.py --check-resolution-refusal",
    }


def check_resolution_refusal():
    """One focused corruption check, with project-code loading forbidden."""
    original_loader = globals()["load_verified"]
    executions = []

    def forbidden_loader(*args, **kwargs):
        executions.append(args[0])
        raise AssertionError("project code executed before refusal")

    def corrupt_archive(path):
        raw = regular_bytes(path)
        return bytes([raw[0] ^ 1]) + raw[1:] if path == ROOT / ARCHIVE else raw

    globals()["load_verified"] = forbidden_loader
    try:
        try:
            prepared = prepare_sources(reader=corrupt_archive)
            with historical_imports(prepared):
                raise AssertionError("corrupt historical guard was accepted")
        except ValueError as error:
            if str(error) != f"source identity mismatch: {ARCHIVE}":
                raise
        else:
            raise AssertionError("archive corruption must refuse")
        if executions:
            raise AssertionError("refusal happened after project execution")
        return {"status": "passed", "case": "one-byte corrupt historical guard",
                "project_source_executions": 0, "files_written": 0}
    finally:
        globals()["load_verified"] = original_loader


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-resolution-refusal", action="store_true")
    args = parser.parse_args()
    result = check_resolution_refusal() if args.check_resolution_refusal else audit()
    if not args.check_resolution_refusal:
        companion = ROOT / f"references/{BASE}_v2.json"
        if companion.exists() and result != json.loads(regular_bytes(companion).decode("utf-8")):
            raise ValueError("v2 companion does not match the reproduced report")
    print(json.dumps(result, indent=2))
