"""Reproduce the bounded native Attack review and curate public metadata.

Read-only: no emulator launch, ROM emission, input mutation or publication.
Exact private evidence is required; missing or changed evidence refuses.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "private/research/pc07_first_attack_independent_review_20261013"
RUN = ROOT / "private/test_runs/pc07_first_attack_v2_run1"


def identity(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def audit():
    source = REVIEW / "review_v2.py"
    saved = REVIEW / "review_v2.json"
    assert identity(source)["sha256"] == "31463f43f479625208f82565da6cd6061b7c804fbb442c87b7d8345e1344c969"
    assert identity(saved)["sha256"] == "36cdac6bcac3d33baa906935c8a5348a9306841f203f8e1cafb08a2004e3bbb6"
    spec = importlib.util.spec_from_file_location("epoch_first_attack_review", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    review = module.review()
    assert (json.dumps(review, indent=2, sort_keys=True) + "\n").encode() == saved.read_bytes()
    assert review["status"] == "accepted-one-bounded-existing-native-run"
    run = json.loads((RUN / "receipt.json").read_bytes())
    assert run["records"] == 343387 and run["failure"] is None and run["returncode"] == 63
    obs = review["reused_validator_result"]
    facts = review["independent_action_facts"]
    assert obs["ordinary_attack_observed"] and obs["preparation_pairs"] == 4642
    assert not obs["save_cold_load_proved"] and not obs["vehicle_behavior_proved"]
    assert facts["damage"]["delta"] == 962 and facts["selector_family_observed"] == "critical"
    build_path = ROOT / "private/test_runs/pc07_first_attack_diagnostic_v1/build_receipt.json"
    assert identity(build_path)["sha256"] == "68c7847116774dd832247e79884d0effefab8da74d07d57b1c2e74c4dc4dad65"
    build = json.loads(build_path.read_bytes())
    assert build["emitted"] and not build["production_approved"]
    assert build["intent_audit"]["status"] == "metadata-valid"
    diff = build["complete_diff_audit"]
    assert diff["status"] == "images-valid" and diff["complete_diff_coverage"]
    assert diff["changed_byte_count"] == 481 and len(diff["changed_bytes_by_section"]) == 34
    return {
        "schema": "project-epoch-pc07-first-attack-checkpoint-2026-10-13-v1",
        "date": "2026-10-13",
        "status": "independently-reviewed-local-checkpoint-goal-active",
        "evidence_level": "one emulator-assisted native Attack diagnostic; exact independent offline reproduction",
        "human_report": identity(ROOT / "docs/pc07_first_attack_checkpoint_2026_10_13.md"),
        "auditor": identity(Path(__file__).resolve()),
        "run_receipt": identity(RUN / "receipt.json"),
        "independent_receipt": identity(saved),
        "independent_reproducer": identity(source),
        "source_bundle_sha256": review["source_bundle_sha256"],
        "source_rows_rehashed": review["source_rows_rehashed"],
        "receipt_artifacts_rehashed": len(review["receipt_artifacts_rehashed"]),
        "trace": identity(RUN / "events.jsonl"),
        "records": run["records"],
        "successful_complete_runs": 1,
        "repeat_pair": False,
        "preparation_byte_write_readback_pairs": obs["preparation_pairs"],
        "debugger_cpu_edits": 0,
        "native_work_copy_bytes": obs["native_work_copy_bytes"],
        "battle_hook_windows": review["hook_window_count"],
        "distinct_battle_hooks": review["distinct_hook_count"],
        "hook_counts": review["hook_counts"],
        "candidate_action": facts["candidate_action"],
        "selector_family_observed": facts["selector_family_observed"],
        "normal_or_path_selector_observed": facts["normal_or_path_selector_observed"],
        "damage": facts["damage"],
        "timeline": facts["timeline"],
        "readiness_publications": facts["readiness_publications"],
        "snapshot_count": 22,
        "all_snapshot_sram_equal_input": review["all_captured_sram_equal_original"],
        "all_snapshot_original_seven_live_records_equal_baseline": review["all_original_seven_live_record_snapshots_equal_source"],
        "all_snapshot_epoch_name_bytes_equal_baseline": review["epoch_name_snapshots_equal_source"],
        "candidate_live_record_preserved_during_action_and_readiness": review["candidate_live_record_preserved_during_action_and_readiness"],
        "candidate_live_hp": 968,
        "donor_live_hp": 969,
        "candidate_action_mp": 93,
        "shared_work_interval_distinction": facts["interpretation"],
        "entry_shared_work_before_action_publication": facts["entry_shared_work_before_action_publication"],
        "later_shared_work_at_readiness_cut": facts["later_shared_work_at_cut"],
        "declared_battle_ranges_reconciled": obs["declared_battle_ranges_reconciled"],
        "full_wram_reconciled": False,
        "global_interrupt_safety": False,
        "guard_scope": obs["guard_scope"],
        "selected_battle_initialization_observed": True,
        "ordinary_attack_observed": True,
        "battle_to_field_commit_proved": False,
        "victory_or_progression_proved": False,
        "save_cold_load_proved": False,
        "epoch_vehicle_behavior_proved": False,
        "playable_release": False,
        "production_approved": False,
        "private_image_construction": {
            "receipt": identity(build_path),
            "image_sha256": build["target_sha256"],
            "image_bytes": build["target_size"],
            "static_evidence_level": build["evidence_level"],
            "fixed_sections": 34,
            "changed_bytes_relative_to_inert_scaffold": 481,
            "original_component": {"address_hex": "410000", "bytes": 157},
            "new_component": {"address_hex": "410100", "bytes": 215},
            "intent_and_complete_diff_passed": True,
        },
        "preserved_incomplete_pilot": {
            "run": "private/test_runs/pc07_first_attack_v1_run1",
            "receipt": identity(REVIEW / "review_v1.json"),
            "closed_hook_windows_qualified": 24,
            "ordinary_attack_accepted": False,
            "full_run_accepted": False,
        },
        "observed_prefix_equivalence": review["v1_v2_observed_prefix_comparison"],
        "root_visual_inspection": {
            "snapshots": [identity(RUN / (name + ".png")) for name in ("pre_results", "attack_ready")],
            "scope": "borrowed Crono appearance only; trace and memory establish identity and timing",
        },
        "documentary_limits": ["post_load.png and compatibility_staged.png are empty; all 22 WRAM/SRAM snapshot pairs exist"],
        "deferred_stop_execution_excluded": True,
        "shutdown_sram_authoritative": False,
        "publication": False,
        "next_gate": "qualify native roster-based battle work-to-live commit and field return, then independent versioned save/cold-load; preserve Epoch vehicle/name",
        "reproduction": "python -B tools/audit_pc07_first_attack_checkpoint_2026_10_13.py",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
