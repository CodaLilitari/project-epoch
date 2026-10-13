"""Reproduce the private first-escape review and emit public-safe metadata.

Read-only: no emulator, image emission, input mutation or publication. Raw
ROM/event/save/state/trace/screenshot payloads are never returned. Exact private
fixtures are required; missing or changed evidence refuses.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "private/research/pc07_escape_commit_independent_review_20261013"
RUN = ROOT / "private/test_runs/pc07_escape_commit_v2_run1"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def audit():
    source = REVIEW / "review_escape_v2.py"
    saved = REVIEW / "review_receipt.json"
    need(identity(source)["sha256"] == "7a5bed1ad7cd0e08f2ecf07190eacf415d1fa1bd9aea5270b7365af1ed427f32", "review source drift")
    need(identity(saved)["sha256"] == "3ff22606f13a1919e32d227c9c22af9eadac30931685c59ed6a619129b288556", "review receipt drift")
    spec = importlib.util.spec_from_file_location("epoch_first_escape_review", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    review = module.review()
    need(encoded(review) == saved.read_bytes(), "independent receipt reproduction")
    need(review["status"] == "independently-qualified-first-escape-commit", "native review not accepted")
    root_witness = REVIEW / "root_reproduction.json"
    need(identity(root_witness)["sha256"] == "6452dd26aacc9de970c6677ebcefcc6654ae1f47fe7b2ed6e2d2da5ea2c015ef", "root reproduction witness drift")
    need(json.loads(root_witness.read_bytes()) == review, "root reproduction JSON result agreement")
    need(root_witness.read_bytes().replace(b"\r\n", b"\n") == saved.read_bytes() + b"\n", "explicit stdout-only newline transformation")
    run = json.loads((RUN / "receipt.json").read_bytes())
    obs = run["observations"]
    need(hashlib.sha256(encoded(obs)).hexdigest() == review["frozen_validator_result_sha256"], "original observations differ from freshly validated result")
    need(run["records"] == 402532 and run["failure"] is None and run["returncode"] == 63, "run outcome drift")
    need(obs["preparation_pairs"] == 4642 and obs["attack_prefix"]["ordinary_attack_observed"], "actual Attack/preparation prefix")
    need(obs["first_commit_only"] and not obs["full_field_return_proved"], "first-commit scope")
    hp = [{key: row[key] for key in (
        "slot", "logical", "live_hp_before_first_commit", "work_hp_at_attack_ready",
        "work_hp_at_commit_entry", "live_hp_at_first_commit_return")}
        for row in review["hp_status_review"]["records"]]
    need([r["live_hp_at_first_commit_return"] for r in hp] == [739, 603, 608], "observed independent HP values")
    status_changes = [{"slot": row["slot"], "logical": row["logical"],
                       "work_changes_ready_to_commit_entry": row["all_work_changes_ready_to_commit_entry"],
                       "native_cleanup_stores": row["selected_native_cleanup_writes"],
                       "live_offsets_1D_through_26_zero_at_cut": not any(row["live_status_at_commit_return"])}
                      for row in review["hp_status_review"]["records"]]
    groups = [{key: row[key] for key in ("slot", "logical", "bytes", "source_start", "destination_start", "last_readback_row")}
              for row in review["direct_copy_review"]["groups"]]
    image = review["read_only_image_requalification"]
    need(image["intent"]["status"] == "metadata-valid" and image["complete_diff"]["status"] == "images-valid", "archived image guards")
    return {
        "schema": "project-epoch-pc07-first-escape-commit-2026-10-13-v1",
        "date": "2026-10-13",
        "status": "independently-reviewed-local-checkpoint-goal-active",
        "evidence_level": "one emulator-assisted native first escape commit; exact independent offline reproduction",
        "human_report": identity(ROOT / "docs/pc07_first_escape_commit_2026_10_13.md"),
        "auditor": identity(Path(__file__).resolve()),
        "run_receipt": identity(RUN / "receipt.json"),
        "original_run_status_preserved": run["status"],
        "independent_receipt": identity(saved),
        "independent_reproducer": identity(source),
        "review_source_manifest": identity(REVIEW / "source_manifest.json"),
        "root_reproduction_stdout": identity(root_witness),
        "root_reproduction_JSON_equal_receipt": True,
        "root_stdout_bytes_equal_receipt": False,
        "root_reproduction_format_note": "Windows stdout uses CRLF and one extra print newline; normalizing CRLF yields exact receipt bytes plus one LF; the executed reproducer internally checks exact receipt bytes",
        "source_bundle_sha256": review["launcher_bundle_sha256"],
        "source_rows_rehashed": review["source_rows_rehashed"],
        "run_artifacts_rehashed": review["recorded_artifacts_rehashed"],
        "original_inputs_rehashed": review["original_inputs_rehashed"],
        "staged_runtime_files_rehashed": review["staged_runtime_files_rehashed"],
        "staged_inputs_reconstructed": review["staged_inputs_reconstructed"],
        "trace": review["trace"],
        "rows": review["rows"],
        "successful_complete_runs": 1,
        "repeat_pair": False,
        "private_image_sha256": "6d420e3daa6761a6ca2b0dd6bfc9119aa15967124f92c5d731a431f76726eefa",
        "new_image_emitted_for_this_run": False,
        "archived_intent_and_complete_diff_passed": True,
        "changed_bytes_relative_to_inert_scaffold": image["complete_diff"]["changed_byte_count"],
        "authored_event": review["authored_event"],
        "event_transform": identity(ROOT / "tools/transform_pc07_escape_event_v1.py"),
        "preparation_byte_write_readback_pairs": obs["preparation_pairs"],
        "debugger_cpu_edits": 0,
        "escape_counter_or_result_injection": False,
        "native_Attack_and_readiness_prefix_validated": True,
        "native_LR_qualifying_ticks": review["direct_counter_review"]["native_LR_qualifying_ticks"],
        "native_escape_request_publications": review["direct_counter_review"]["native_escape_publications"],
        "native_commit_read_write_snapshot_readback_triples": review["direct_copy_review"]["triples"],
        "native_copy_groups": groups,
        "actual_entry_pc_hex": "C1B442",
        "actual_call_site_hex": "C18215",
        "actual_pre_RTS_pc_hex": "C1B487",
        "actual_return_cut_pc_hex": "C18218",
        "actual_cut_row": review["direct_copy_review"]["actual_cut_row"],
        "cut_before_inventory_commit": True,
        "HP_values": hp,
        "status_cleanup": status_changes,
        "status_changes_not_individual_damage_attribution": True,
        "snapshot_count": review["snapshots_checked"],
        "SRAM_snapshots_equal_input": review["SRAM_snapshots_unchanged"],
        "all48_stored_names_including_Epoch_preserved": review["all48_names_Epoch_and_five_reserves_preserved"],
        "reserve_PC02_through_PC06_records_preserved": True,
        "active_PC00_PC01_PC07_updates_only_witnessed_commit_writes": True,
        "declared_compatibility_and_guard_checks_passed": True,
        "bootstrap_rear_guard_hex": "2CF0..2CFF; prior field extension2D00..2D0F is not preserved",
        "graphics_branch": "accepted Crono donor diagnostic; separate Schala appearance run is not merged",
        "Schala_presentation_reference": "docs/pc07_schala_presentation_2026_10_13.md",
        "screenshots_in_this_checkpoint": False,
        "empty_documentary_PNGs": ["post_load.png", "compatibility_staged.png"],
        "focused_synthetic_review_tests": 3,
        "deferred_stop_execution_excluded": True,
        "shutdown_SRAM_authoritative": False,
        "first_commit_only": True,
        "second_commit_observed": False,
        "full_field_return_proved": False,
        "normal_save_or_coldload_proved": False,
        "victory_or_progression_proved": False,
        "Epoch_vehicle_behavior_proved": False,
        "full_WRAM_reconciled": False,
        "global_interrupt_safety_proved": False,
        "playable_release": False,
        "production_approved": False,
        "publication_performed_by_auditor": False,
        "next_gate": "native inventory merge, second live commit and actual field restoration before normal save/cold-load",
        "reproduction": "python -B tools/audit_pc07_first_escape_commit_2026_10_13.py",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
