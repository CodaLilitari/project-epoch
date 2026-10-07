"""Audit seven private menu operand relocations; default operation emits nothing.

Exactly fourteen operand bytes differ. Opcode bytes, the seven-record bound,
ROM size and header are preserved. An emitted diagnostic is not a release patch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import schala_compat_menu_v1 as contract
import validate_rom_write_intents as guard


def build_image(source: bytes, output: Path) -> tuple[bytes, dict]:
    static = contract.source_contract(source)
    destination = contract.private_path(output)
    contract.require(destination.suffix.lower() == ".sfc", "private output must be .sfc")
    image = bytearray(source)
    writes = []
    for index, (start, old, new) in enumerate(contract.OPERAND_PATCHES):
        contract.require(source[start:start + len(old)] == old, "operand preimage mismatch")
        image[start:start + len(old)] = new
        writes.append({
            "write_id": f"compat-menu-v1-operand-{index}",
            "classification": "private-diagnostic-replacement", "file_start": start, "size": 2,
            "owner": "epoch-private-compat-menu-v1", "payload_kind": "code", "evidence": "verified-static",
            "preimage_sha256": contract.sha256(old), "replacement_sha256": contract.sha256(new),
            "allocation_id": None, "hook_id": None, "table_id": None,
            "header_field_id": None, "replacement_hex": None,
        })
    target = bytes(image)
    # Independently require the complete observed diff to be those 14 operands.
    expected = {start + offset for start, old, _new in contract.OPERAND_PATCHES for offset in range(len(old))}
    changed = {i for i, (before, after) in enumerate(zip(source, target)) if before != after}
    contract.require(len(target) == len(source) and len(expected) == 14 and changed == expected,
                     "complete diff differs from the fourteen operands")
    for start, original, _role in contract.UNCHANGED_WITNESSES:
        contract.require(target[start:start + len(original)] == original, "unchanged instruction was altered")
    manifest = {
        "schema_version": 1, "manifest_id": "compat-menu-v1-seven-operands",
        "build_mode": "private-diagnostic", "source_kind": guard.CANONICAL_SOURCE_KIND,
        "source_size": len(source), "source_sha256": contract.sha256(source),
        "target_size": len(target), "target_sha256": contract.sha256(target),
        "output_path": destination.relative_to(contract.ROOT).as_posix(), "allocations": [],
        "writes": sorted(writes, key=lambda row: (row["file_start"], row["write_id"])),
    }
    # Both fail-closed shared checks precede any possible filesystem emission.
    guard.validate_manifest(manifest)
    audit = guard.audit_images(manifest, source, target)
    return target, {"schema": contract.SCHEMA + "-build", "contract": static,
                    "write_intent_manifest": manifest, "write_intent_audit": audit,
                    "changed_file_offsets": sorted(changed), "emitted": False}


def emit(source: bytes, output: Path, reviewed_bundle: str) -> dict:
    before = contract.bundle_identity()
    contract.require(reviewed_bundle == before["sha256"], "exact reviewed source-bundle hash required")
    destination = contract.private_path(output, must_not_exist=True)
    receipt_path = contract.private_path(destination.with_suffix(".sfc.manifest.json"), must_not_exist=True)
    target, report = build_image(source, destination)
    contract.require(contract.bundle_identity() == before, "source changed during audit")
    report.update(source_bundle=before, emitted=True,
                  output_path=str(destination), manifest_path=str(receipt_path),
                  reproduction=["python", "tools/build_schala_compat_menu_v1.py", "--rom",
                                str(contract.DEFAULT_ROM), "--output", str(destination),
                                "--emit-reviewed-bundle", before["sha256"]])
    receipt = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the receipt first. No existing output or receipt is overwritten.
    with receipt_path.open("xb") as manifest_file:
        with destination.open("xb") as image_file:
            image_file.write(target)
        manifest_file.write(receipt)
    contract.require(contract.sha256(destination.read_bytes()) == report["write_intent_manifest"]["target_sha256"],
                     "emitted image identity mismatch")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=contract.DEFAULT_ROM)
    parser.add_argument("--output", type=Path,
                        default=contract.ROOT / "private/test_runs/compat_menu_v1/diagnostic.sfc")
    parser.add_argument("--emit-reviewed-bundle", help="explicit private emission after review of this bundle hash")
    args = parser.parse_args()
    source = args.rom.read_bytes()
    if args.emit_reviewed_bundle:
        report = emit(source, args.output, args.emit_reviewed_bundle)
    else:
        _target, report = build_image(source, args.output)
        report["source_bundle"] = contract.bundle_identity()
        report["reproduction"] = ["python", "tools/build_schala_compat_menu_v1.py", "--rom", str(args.rom), "--output", str(args.output)]
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
