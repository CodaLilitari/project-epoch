"""Read-only receipt audit for the October 13 tool assessment. Emits JSON to stdout.

Consumes existing private research artifacts; never downloads, launches a tool,
generates game code, modifies ROMs, or publishes. Missing private evidence refuses.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
CT = ROOT / "private/research/ct_recomp_test_20261013"
GH = ROOT / "private/research/recomp_tool_assessment_20261013"


def identity(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit():
    ct = read(CT / "receipt.json")
    assert identity(CT / "receipt.json")["sha256"] == "85deb068bd23050fb2745833b18253e69f136e52123bb55d763718c2488a90b7"
    assert ct["source_files_verified"] == 135
    assert ct["source_unchanged"] and ct["canonical_rom_unchanged"]
    assert [(s["test_count"], s["failures"], s["skipped"]) for s in ct["suites"]] == [(23, 0, 0), (9, 0, 0)]
    suites = [{"source": s["source"], "test_count": s["test_count"],
               "failures": s["failures"], "skipped": s["skipped"],
               "cases": [{k: c[k] for k in ("name", "status", "time_seconds")}
                         for c in s["cases"]]} for s in ct["suites"]]
    gh = read(GH / "ghidra_probe.json")
    assert identity(GH / "ghidra_probe.json")["sha256"] == "3f77f4b6d1531375249cbd5d6091a85a2bd3403c973d0acf2388025ea33cbb8b"
    assert len(gh["cases"]) == 5
    log = (GH / "ghidra_stdout.txt").read_text(encoding="utf-8")
    assert "EpochOriginalCases_v5" in log and "EPOCH_PROBE_WRITTEN" in log
    follow = read(GH / "mapping_review_v1/receipt.json")
    for name, expected in follow["artifacts"].items():
        assert identity(GH / "mapping_review_v1" / name)["sha256"] == expected
    assert [r["accepted"] for r in follow["headers"]] == [False, True, True]
    assert not follow["rom_initialized_writable_blocks"]
    indirect_path = GH / "indirect_verification_v1/assessment_v1.json"
    indirect = read(indirect_path)
    assert identity(indirect_path)["sha256"] == "cad83dba63eea0d29b1a8b114e7ad1b15d9f0c4d00448ad53d114db2cc3af28c"
    assert indirect["checks_passed"] and len(indirect["cases"]) == 6
    assert all(not c["emulator_last_step_ok"] for c in indirect["cases"][:4])
    assert all(c["emulator_last_step_ok"] for c in indirect["cases"][4:])
    assert indirect["cases"][1]["decompile_completed"]
    assert identity(GH / "indirect_verification_v1/run_isolated3/indirect_probe.json")["sha256"] == indirect["output_sha256"]
    review = read(GH / "claude_review_receipt.json")
    assert hashlib.sha256(review["answer"].encode()).hexdigest() == review["job"]["answer_sha256"]
    assert review["job"]["state"] == "returned"
    archives = []
    for item in read(GH / "download_receipt.json"):
        actual = identity(Path(item["path"]))
        assert (actual["sha256"], actual["bytes"]) == (item["sha256"], item["bytes"])
        archives.append({**actual, "url": item["url"], "digest_source": item["verified_against"]})
    evidence_paths = [CT / n for n in ["receipt.json", "assessment.md", "reproduce_receipt.py"]]
    evidence_paths += [GH / n for n in ["assessment.json", "assess_ghidra_results.py", "ghidra_probe.json", "ghidra_run_receipt.json", "ghidra_stdout.txt", "ghidra_mapping.json", "ghidra_mapping_receipt.json", "mapping_review_v1/receipt.json", "claude_review_receipt.json"]]
    evidence_paths += [GH / "indirect_verification_v1" / n for n in ["assessment_v1.json", "verify_existing_v1.py", "run_isolated3/source_snapshot/verify_results_first_receipt.py", "run_isolated3/run_receipt.json"]]
    report = ROOT / "docs/recomp_tool_practical_assessment_2026_10_13.md"
    return {
        "schema": "project-epoch-recomp-practical-assessment-2026-10-13-v1",
        "date": "2026-10-13",
        "evidence_level": "executed bounded local tool tests; source review; no eighth-character or production proof",
        "human_report": identity(report),
        "auditor": identity(Path(__file__).resolve()),
        "decision": "retain SNES implementation baseline; ct-recomp is now a working comparative research tool; no route migration",
        "ct_recomp": {**{k: ct[k] for k in ["source_commit", "source_files_verified", "source_unchanged", "canonical_rom_unchanged", "system_packages_installed", "frontend_built", "engine_c_harness_check_count", "game_tests_selected", "remaining_nonengine_tests_not_run", "headless_binary", "independent_emulator_comparison", "human_visual_inspection", "pc07_tested", "full_game_correctness_established", "performance_comparison", "epoch_vehicle_tested"]}, "suites": suites},
        "generic_cli": {"release": ct["cli_release"], "result": ct["cli_synthetic_result"], "generated_output_compiled_or_executed": False, "inspected_current_head": "e54427bad93fb75729ce8214fdd7a46e197e6223", "current_readme_ExHiROM_supported": False},
        "ghidra": {"version": "12.1.4", "extension": "ghidra-snes 1.3.0", "extension_metadata_version": "12.0.4", "probe_count": 5, "hidden_B_selected_case_matches": True, "automatic_PLP_width_counterexample": True, "manual_context_is_synthetic_broad_assertion": True, "indexed_jump_original_probe_decompile_failed": True, "canonical_selected_spans_match": 3, "whole_mapping_verified": False, "expanded_header_candidates": follow["headers"], "expanded_import_succeeded": False, "canonical_initialized_writable_blocks": []},
        "ghidra_indirect_followup": {k: indirect[k] for k in ["evidence_level", "checks_passed", "cases", "fixture_sha256", "output_sha256", "installed_and_recompiled_sla_sha256", "release_archive_contains_sla", "conclusion", "limits"]},
        "external_review": {"provider": "Claude Code", "reported_model": review["job"]["observed_cli_models"], "backend_independently_attested": False, "answer_sha256": review["job"]["answer_sha256"], "status": "returned and inspected; consequential claims independently checked or explicitly left open", "reviewer_executed_tools": False},
        "archives": archives,
        "evidence_artifacts": [identity(p) for p in evidence_paths],
        "rom_modified": False,
        "production_bindings_or_allocations_approved": False,
        "publication": False,
        "reproduction": ["python -B tools/audit_recomp_tool_assessment_2026_10_13.py", "python -B private/research/ct_recomp_test_20261013/reproduce_receipt.py", "python -B private/research/recomp_tool_assessment_20261013/assess_ghidra_results.py", "python -B private/research/recomp_tool_assessment_20261013/indirect_verification_v1/verify_existing_v1.py"],
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
