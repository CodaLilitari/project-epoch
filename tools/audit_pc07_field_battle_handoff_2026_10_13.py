"""Recheck private evidence and emit the curated public checkpoint as JSON.

No emulator, image emission, mutation, upload, or publication is performed.
The exact private evidence packet is required; missing evidence refuses.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "private/research/pc07_field_battle_route_v2_review_20261013"
RUN = ROOT / "private/test_runs/pc07_field_battle_route_v2_run1"


def identity(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def audit():
    source = REVIEW / "reproduce_review.py"
    assert identity(source)["sha256"] == "0fbd49fc49418097b261ce5f2117ea3606def4a46e9c1f511509013463bf2cb4"
    expected = REVIEW / "receipt.json"
    assert identity(expected)["sha256"] == "7482b311ecf4f66c92ed772bf8dfb5bf084ea6cfaa6a5b085f75b7f324b78380"
    spec = importlib.util.spec_from_file_location("epoch_handoff_review", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    independent = module.derive()
    assert (json.dumps(independent, indent=2) + "\n").encode() == expected.read_bytes()
    run = json.loads((RUN / "receipt.json").read_text(encoding="utf-8"))
    assert run["records"] == 250006 and run["failure"] is None
    obs = run["observations"]
    assert not obs["battle_initialization_proved"] and not obs["ordinary_attack_proved"]
    packet = ROOT / "private/research/pc07_battle_adapters_20261013"
    facts = packet / "claude_disposition_facts_v1.json"
    reproducer = packet / "reproduce_claude_disposition_v1.py"
    assert identity(facts)["sha256"] == "9711c66002c28dfca81c90f7ae5d74ba61dda5d35f4b1795b782e3f15adb0be3"
    assert identity(reproducer)["sha256"] == "1fdc06d88dfe4bdf2eb064642ccfe79df66d2e74d3842d3a0adebbc6e5dc7955"
    spec2 = importlib.util.spec_from_file_location("epoch_adapter_source_disposition", reproducer)
    module2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(module2)
    source_facts = module2.reproduce()
    assert source_facts == json.loads(facts.read_text(encoding="utf-8"))
    return {
        "schema": "project-epoch-pc07-field-battle-handoff-2026-10-13-v1",
        "date": "2026-10-13",
        "status": "independently-reviewed-local-checkpoint-goal-active",
        "evidence_level": "one emulator-assisted continuous route; exact independent offline reproduction",
        "human_report": identity(ROOT / "docs/pc07_field_battle_handoff_2026_10_13.md"),
        "auditor": identity(Path(__file__).resolve()),
        "run_receipt": identity(RUN / "receipt.json"),
        "independent_receipt": identity(expected),
        "independent_reproducer": identity(source),
        "source_bundle_sha256": run["source_bundle"]["sha256"],
        "source_count": len(run["source_bundle"]["sources"]),
        "trace": identity(RUN / "events.jsonl"),
        "records": run["records"],
        "snapshot_count": 15,
        "all_snapshot_sram_equal_input": True,
        "all_snapshot_original_seven_records_equal_baseline": True,
        "all_snapshot_epoch_name_bytes_equal_baseline": True,
        "candidate_hp": 968,
        "donor_hp": 969,
        "preparation_byte_write_readback_pairs": 4641,
        "destination_preparation_pairs": 1916,
        "destination_actual_changed_bytes": 1718,
        "native_helper_groups": obs["native_helper_groups"],
        "pending_lifecycle": obs["pending_lifecycle"],
        "native_candidate_export_hex_29BA_29BE": "0B09080F03",
        "terminal": {"site": "C018A7 before JSL C10000", "poll": 2811,
                     "physical_stop_before_instruction_proved": False,
                     "post_cut_execution_excluded": True,
                     "shutdown_sram_authoritative": False},
        "root_visual_inspection": {"path": "private/test_runs/pc07_field_battle_route_v2_run1/pre_battle_jsl.png", "scope": "final field scene only; identity comes from trace, not appearance"},
        "documentary_limits": ["post_load.png and compatibility_staged.png are empty; all WRAM/SRAM snapshots exist"],
        "battle_initialization_proved": False,
        "ordinary_attack_proved": False,
        "save_cold_load_proved": False,
        "epoch_vehicle_behavior_proved": False,
        "global_wram_or_interrupt_closure": False,
        "playable_release": False,
        "new_rom_or_patch_emitted": False,
        "uninstalled_battle_adapter_source_review": {
            "facts": identity(facts), "reproducer": identity(reproducer),
            "receipt": identity(packet / "claude_disposition_receipt_v1.json"),
            "evidence_level": "source-only; no hook installation or native battle execution",
            "slot2_weapon_mask_production": "20 hex",
            "selected_attack_plus4_consumer_proved": False,
            "actual_hook_entry_dbr_witness": False,
            "canonical_partner_derivations_checked": 116,
            "computed_target_closure": False,
            "reproduction": "python -B private/research/pc07_battle_adapters_20261013/reproduce_claude_disposition_v1.py"},
        "publication": False,
        "preserved_rejected_pilot": "private/test_runs/pc07_field_battle_route_v1_run1",
        "next_gate": "qualify and place separately guarded battle adapters, then observe first ordinary Attack; preserve vehicle and save obligations",
        "reproduction": "python -B tools/audit_pc07_field_battle_handoff_2026_10_13.py",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
