"""Read-only revalidation of the exact accepted instrumented save/load chain.

No emulator, image emission, subprocess or output file operation is used. All
inputs and frozen sources are captured and pinned before computation, replayed
from those bytes, then rechecked. Public output contains metadata only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references/schala_save_layout_native_chain_v1.json"
REFERENCE_SHA256 = "7ee90c74c042b8b5fdcd60dd4b8475a4d7c548f70992b3641fda2dbdce38b0a4"
NATIVE_BUNDLE_SHA256 = "a280927788eee65f2bac11d2acb0f3740e9fa0f80172f02254e7dc1c288247cb"
BASE = "private/test_runs/mesen2/"
ACQUISITIONS = {
    "save": ["save_entry_checkpoint_v1_run4", "save_entry_checkpoint_v1_resume2"],
    "load": ["load_entry_checkpoint_v1_native_save_run2", "load_entry_checkpoint_v1_native_save_resume1"],
}
RUNS = {mode: [f"save_layout_native_v1_{mode}_run{i}" for i in (1, 2)] for mode in ("save", "load")}


class ChainError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ChainError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def checked_path(name):
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts and path.as_posix() == name,
            "noncanonical reference path")
    resolved = (ROOT / path).resolve()
    require(resolved.is_relative_to(ROOT) and not (ROOT / path).is_symlink(), "path escape/symlink")
    return resolved


def read_reference(raw):
    require(sha(raw) == REFERENCE_SHA256, "reference identity drift")
    ref = decode(raw)
    require(ref["schema"] == "project-epoch-save-layout-native-chain-v1" and
            ref["evidence_level"] == "verified-runtime-instrumented", "reference scope")
    require(ref["native_bundle"]["sha256"] == NATIVE_BUNDLE_SHA256 and
            ref["acquisitions"] == ACQUISITIONS and ref["native_runs"] == RUNS, "chain identity")
    names = [row[0] for row in ref["artifact_inventory"]]
    require(len(names) == 150 and names == sorted(set(names)), "artifact inventory duplication/omission")
    for name in names:
        checked_path(name)
    require(ref["review_status"]["claude_code_second_audit"] == "pending-at-reference-creation" and
            ref["review_status"]["final_external_approval_claimed"] is False, "review status drift")
    return ref


def capture_artifacts(ref):
    captured = {}
    for name, size, digest in ref["artifact_inventory"]:
        raw = checked_path(name).read_bytes()
        require(len(raw) == size and sha(raw) == digest, "artifact identity drift: " + name)
        captured[name] = raw
    return captured


def recheck_artifacts(ref, captured):
    for name, size, digest in ref["artifact_inventory"]:
        raw = checked_path(name).read_bytes()
        require(len(raw) == size and sha(raw) == digest and raw == captured[name],
                "artifact changed during revalidation: " + name)


def load_captured(name, path, captured):
    """Execute the same pinned source bytes that were captured, never main()."""
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(captured[path], module.__file__, "exec", dont_inherit=True), module.__dict__)
    return module


class CapturedPath:
    """Read-only path facade for the load acquisition's existing validator."""
    def __init__(self, path, captured):
        self.path, self.captured = path, captured

    def __truediv__(self, child):
        return CapturedPath(self.path + "/" + child, self.captured)

    def read_bytes(self):
        return self.captured[self.path]

    def read_text(self, encoding="utf-8"):
        return self.read_bytes().decode(encoding)

    def stat(self):
        return types.SimpleNamespace(st_size=len(self.read_bytes()))


def verify_equal_groups(ref, captured):
    for paths in ref["byte_equality_groups"]:
        require(len(paths) >= 2 and all(p in captured for p in paths), "equality group inventory")
        require(all(captured[p] == captured[paths[0]] for p in paths[1:]),
                "byte equality failed: " + paths[0])


def relative_input(path):
    resolved = Path(path).resolve()
    require(resolved.is_relative_to(ROOT), "receipt input outside workspace")
    return resolved.relative_to(ROOT).as_posix()


def revalidate(ref, captured):
    verify_equal_groups(ref, captured)
    # Dependency order ensures imports bind to captured, pinned local sources.
    modules = {}
    for name in ("schala_rom_scaffold", "schala_save_layout", "inspect_ct_srm",
                 "validate_rom_write_intents", "schala_save_layout_native_v1",
                 "build_schala_save_layout_native_v1", "validate_mesen_save_layout_native_v1"):
        modules[name] = load_captured(name, "tools/" + name + ".py", captured)
    contract = modules["schala_save_layout_native_v1"]
    validator = modules["validate_mesen_save_layout_native_v1"]
    builder = modules["build_schala_save_layout_native_v1"]
    require(contract.bundle_identity() == ref["native_bundle"], "native bundle source drift")
    acquisition_validator = load_captured("_epoch_chain_load_acquisition",
        "tools/run_mesen_load_entry_checkpoint_v1.py", captured)
    produced = captured[ref["produced_sram"]]
    require(len(produced) == 8192 and sha(produced) == ref["produced_sram_sha256"], "produced SRAM identity")
    acquisition_results = {}
    for mode, dirs in ACQUISITIONS.items():
        for index, name in enumerate(dirs):
            directory = BASE + name
            receipt = decode(captured[directory + "/receipt.json"])
            require(receipt["accepted"] is True and receipt["rom_mutated"] is False and
                    receipt["process_error"] is None and receipt["fresh_process_resume"] is bool(index),
                    "acquisition receipt status")
            require(receipt["source_hashes"] == receipt["source_hashes_after"] ==
                    ref["acquisition_execution_source_receipts"][name], "historical execution source receipt mismatch")
            require(receipt["input_hashes"] == receipt["input_hashes_after"], "acquisition input preservation")
            for key, path in receipt["input_paths"].items():
                require(sha(captured[relative_input(path)]) == receipt["input_hashes"][key], "acquisition input hash")
            for filename, identity in receipt["artifacts"].items():
                raw = captured[directory + "/" + filename]
                require(len(raw) == identity["bytes"] and sha(raw) == identity["sha256"], "receipt artifact mismatch")
            archived_collector = captured[directory + f"/mesen_{mode}_entry_checkpoint_v1.lua"]
            require(sha(archived_collector) == receipt["source_hashes"]["collector"], "archived execution collector")
            if index:
                parent = BASE + dirs[0]
                for key, filename in (("state",f"{mode}_entry.mss"),("wram","entry_wram.bin"),
                                      ("cpu","entry_cpu.txt"),("receipt","receipt.json")):
                    require(receipt["verification_input_hashes"][key] == sha(captured[parent+"/"+filename]),
                            "fresh-process verification lineage")
            if mode == "load":
                require(captured[directory+"/entry_sram.bin"] == produced, "coldboot/replay changed produced SRAM")
                result = acquisition_validator.validate_capture(CapturedPath(directory,captured),produced,replay=bool(index))
                stored = decode(captured[directory+"/native_entry_contract.json"])
                if index:
                    provenance = stored.pop("cold_boot_validation_receipt")
                    expected_receipt = BASE + dirs[0] + "/receipt.json"
                    require(relative_input(provenance["path"]) == expected_receipt and
                            provenance["sha256"] == sha(captured[expected_receipt]), "replay coldboot receipt link")
                require(result == stored, "load acquisition revalidation mismatch")
                require(result["cold_boot"] is (not bool(index)) and
                        result["validation_observed_this_process"] is (not bool(index)), "coldboot/replay scope")
                acquisition_results[name] = {"cold_boot": result["cold_boot"],
                    "selected_slot_native_validation_sequences":len(result["native_validation_sequences"])}
            else:
                rows = acquisition_validator.trace_rows(captured[directory+"/checkpoint.tsv"].decode())
                kinds = [kind for kind,_ in rows]
                require(kinds[-2:] == ["save-entry","success"] and kinds.count("save-entry") == 1,
                        "save acquisition terminal cardinality")
                cpu = dict(line.split("=",1) for line in captured[directory+"/entry_cpu.txt"].decode().splitlines())
                require(cpu.pop("emulationMode") == "false", "save CPU native mode")
                require(all(rows[-2][1].get("cpu."+key) == value for key,value in cpu.items()), "save entry CPU tuple")
                require((cpu["k"],cpu["pc"],cpu["d"],cpu["dbr"]) == ("255",str(0xF9FB),"0","126"), "save entry CPU boundary")
                if not index:
                    require(kinds.count("save-caller") == 1 and kinds.index("save-caller") < len(rows)-2,
                            "save actual caller missing")
                acquisition_results[name] = {"fresh_process_resume":bool(index),"entry_tuple_revalidated":True}
    reports = {}
    canonical = captured["private/input/rom_archive/Chrono Trigger (USA).sfc"]
    for mode, dirs in RUNS.items():
        for name in dirs:
            directory = BASE + name
            receipt = decode(captured[directory+"/run_receipt.json"])
            require(receipt["status"] == "accepted-instrumented-interval" and receipt["returncode"] == 62 and
                    receipt["failure"] is None and receipt["shutdown_sram_is_authoritative"] is False,
                    "native receipt status")
            require(receipt["source_bundle"] == ref["native_bundle"], "native receipt source bundle")
            entry_bytes = captured[directory+"/entry_contract.json"]
            entry = decode(entry_bytes)
            contract.entry_contract(entry,mode)
            require(entry == receipt["entry_contract"] and sha(entry_bytes) == receipt["entry_contract_sha256"], "native entry binding")
            require(sha(captured[directory+"/entry.mss"]) == entry["checkpoint_sha256"] and
                    len(captured[directory+"/entry.mss"]) == entry["checkpoint_size"], "native checkpoint binding")
            if mode == "load":
                require(entry["sram_sha256"] == sha(produced), "downstream load contract SRAM lineage")
            image, build = builder.build_image(canonical,ROOT/directory/"diagnostic.sfc")
            require(image == captured[directory+"/diagnostic.sfc"] and build == receipt["build"],
                    "guarded builder revalidation mismatch")
            build_receipt = decode(captured[directory+"/build_receipt.json"])
            require(build_receipt["build"] == build and build_receipt["source_bundle"] == ref["native_bundle"], "prelaunch build receipt")
            raw = captured[directory+"/trace.jsonl"]
            records = [validator.strict_json(line) for line in raw.splitlines()]
            snapshots = {stage:(captured[directory+f"/trace.{stage}.wram.bin"],
                               captured[directory+f"/trace.{stage}.sram.bin"]) for stage in validator.SNAPSHOTS}
            result = validator.validate_records(records,snapshots,entry,sha(entry_bytes),NATIVE_BUNDLE_SHA256)
            result["trace_sha256"] = sha(raw)
            result["snapshot_hashes"] = {stage:{"wram":sha(w),"sram":sha(s)} for stage,(w,s) in snapshots.items()}
            require(result == receipt["validation"], "native source validator no longer reproduces receipt")
            reports[name] = result
    for dirs in RUNS.values():
        require(reports[dirs[0]] == reports[dirs[1]], "native pair metadata equality")
    return {"schema":"project-epoch-save-layout-native-chain-revalidation-v1",
        "evidence_level":"verified-runtime-instrumented","reference_sha256":REFERENCE_SHA256,
        "native_bundle_sha256":NATIVE_BUNDLE_SHA256,"artifact_count":len(captured),
        "byte_equality_group_count":len(ref["byte_equality_groups"]),
        "produced_sram_sha256":sha(produced),"acquisitions":acquisition_results,
        "save_pair":reports[RUNS["save"][0]],"load_pair":reports[RUNS["load"][0]],
        "review_status_at_reference_creation":ref["review_status"],"limitations":ref["limitations"],
        "native_execution_performed":False,"image_emitted":False,"read_only":True}


def audit():
    reference_bytes = REFERENCE.read_bytes()
    own_source = Path(__file__).read_bytes()
    ref = read_reference(reference_bytes)
    captured = capture_artifacts(ref)
    result = revalidate(ref,captured)
    recheck_artifacts(ref,captured)
    require(REFERENCE.read_bytes() == reference_bytes and Path(__file__).read_bytes() == own_source,
            "auditor/reference drift during revalidation")
    result["auditor_sha256"] = sha(own_source)
    return result


if __name__ == "__main__":
    print(json.dumps(audit(),indent=2,sort_keys=True))
