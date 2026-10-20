"""Emit the private battle-pose candidate only after both shared guard APIs.

Asar receives original-source components only. One pinned current ROM snapshot
and immediate receipt replace historical chains. All outputs remain private.
"""
from pathlib import Path
import argparse
import json

import pc07_battle_pose_write_contract_v1 as contract
import validate_rom_write_intents as guard


def build(output):
    output = Path(output).absolute()
    relative = (output/"diagnostic.sfc").relative_to(contract.ROOT).as_posix()
    contract.output_path(relative)
    contract.need(not output.exists(), "fresh private output directory required")
    # The only preliminary writes are original assembly wrappers/components.
    with contract.source_snapshot(output/"assembly") as snap:
        manifest = contract.template(relative)
        intent = guard.validate_pc07_battle_pose_manifest(manifest)
        diff = guard.audit_pc07_battle_pose_images(manifest,snap["source"],snap["target"])
        contract.need(intent["status"] == "metadata-valid" and diff["status"] == "images-valid"
                      and diff["complete_diff_coverage"] is True, "both shared guards required")
        contract.need(not guard.APPROVED_PRODUCTION_ALLOCATIONS and not guard.APPROVED_PRODUCTION_HOOKS,
                      "production catalogs must stay empty")
        sources = []
        for name in ("tools/build_pc07_battle_pose_v1.py", "tools/pc07_battle_pose_write_contract_v1.py",
                     "tools/pc07_run_pose_write_contract_v1.py", "tools/validate_rom_write_intents.py",
                     "tools/native_pc07_pose_codec_v1.py", "tools/native_pc07_pose_mirror_v1.py"):
            sources.append(contract.source_identity(name,contract.resolve(name).read_bytes()))
        sources += snap["assembly"]["source_inputs"]
        receipt = {"schema":"project-epoch-private-pc07-battle-pose-build-v1","emitted":True,
                   "source":contract.SOURCE,"target":manifest["target"],"manifest":manifest,
                   "implementation_inputs":sources,"current_shared_intent":intent,"current_shared_diff":diff,
                   "art_encoding":snap["art"],"assembly":snap["assembly"],
                   "evidence_level":"guarded-private-static-battle-pose-append","native_execution":False,
                   "production_approval":False,"single_source_snapshot":True,
                   "historical_builders_or_validators_executed":False,
                   "limits":["KO helpers qualify only battle slot2 with published PC07 provider.",
                             "Up/down Attack and recoil retain existing art; horizontal poses are newly bound.",
                             "Native animation timing, sprite presentation and flying Epoch behavior require observation."],
                   "reproduction":"python -B tools/build_pc07_battle_pose_v1.py --output private/test_runs/pc07_battle_pose_<fresh-name>"}
        # No game image or patch exists before this point.
        for name,raw in (("write_intents.json",contract.encoded(manifest)),("diagnostic.sfc",snap["target"]),
                         ("receipt.json",contract.encoded(receipt))):
            path = contract.resolve((output/name).relative_to(contract.ROOT).as_posix())
            with path.open("xb") as stream: stream.write(raw)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    receipt = build(args.output)
    print(json.dumps({"status":"guarded-private-image-emitted","output":str(args.output),
                      "target":receipt["target"],"diff":receipt["current_shared_diff"]}))
