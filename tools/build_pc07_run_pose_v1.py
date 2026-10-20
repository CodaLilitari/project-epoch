"""Build only the private normal-run frame remap; both shared audits precede emission."""
from pathlib import Path
import argparse
import json
import pc07_run_pose_write_contract_v1 as contract
import validate_rom_write_intents as guard


def build(output):
    output = Path(output).absolute()
    relative = (output / "diagnostic.sfc").relative_to(contract.ROOT).as_posix()
    contract.output_path(relative)
    contract.need(not output.exists(), "fresh output directory required")
    with contract.source_snapshot() as snap:
        manifest = contract.template(relative)
        intent = guard.validate_pc07_run_pose_manifest(manifest)
        diff = guard.audit_pc07_run_pose_images(manifest, snap["source"], snap["target"])
        contract.need(intent["status"] == "metadata-valid" and diff["status"] == "images-valid", "current shared guards")
        sources = []
        for path in (Path(__file__).resolve(), Path(contract.__file__).resolve(), Path(guard.__file__).resolve()):
            raw = path.read_bytes()
            sources.append({"path": path.relative_to(contract.ROOT).as_posix(), "bytes": len(raw), "sha256": contract.sha(raw)})
        receipt = {"schema": "project-epoch-private-pc07-run-pose-build-v1", "emitted": True,
                   "source": contract.SOURCE, "target": manifest["target"], "manifest": manifest,
                   "implementation_inputs": sources, "current_shared_intent": intent, "current_shared_diff": diff,
                   "evidence_level": "guarded-private-static-run-remap", "native_execution": False,
                   "production_approval": False, "single_source_snapshot": True,
                   "historical_builders_or_validators_executed": False,
                   "reproduction": "python -B tools/build_pc07_run_pose_v1.py --output private/test_runs/pc07_run_pose_<fresh-name>"}
        output.mkdir(parents=True, exist_ok=False)
        for name, raw in (("write_intents.json", contract.encoded(manifest)),
                          ("diagnostic.sfc", snap["target"]), ("receipt.json", contract.encoded(receipt))):
            with (output / name).open("xb") as stream:
                stream.write(raw)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = build(args.output)
    print(json.dumps({"status": "guarded-private-image-emitted", "output": str(args.output),
                      "target": receipt["target"], "diff": receipt["current_shared_diff"]}))
