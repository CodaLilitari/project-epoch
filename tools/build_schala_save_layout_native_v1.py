"""Prepare/audit two private CMP operand changes; emission needs a reviewed bundle.

Default CLI operation is read-only inspection. The unchanged SNES ROM header
checksum is intentional: exactly two operand bytes may differ. This diagnostic
is not a distributable patch, a new record, or a production installation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import schala_save_layout_native_v1 as contract
import validate_rom_write_intents as guard


def build_image(source: bytes, output: Path) -> tuple[bytes, dict]:
    static = contract.source_contract(source)
    output = contract.private_path(output)
    contract.require(output.suffix.lower() == ".sfc", "private output must be .sfc")
    image = bytearray(source)
    for start, old, new in contract.PATCHES:
        image[start:start + len(old)] = new
    target = bytes(image)
    writes = []
    for index, (start, old, new) in enumerate(contract.PATCHES):
        writes.append({"write_id": f"save-layout-native-v1-cmp-{index}",
            "classification": "private-diagnostic-replacement", "file_start": start,
            "size": len(old), "owner": "epoch-private-save-layout-native-v1",
            "payload_kind": "code", "evidence": "verified-static",
            "preimage_sha256": contract.sha256(old), "replacement_sha256": contract.sha256(new),
            "allocation_id": None, "hook_id": None, "table_id": None,
            "header_field_id": None, "replacement_hex": None})
    manifest = {"schema_version": 1, "manifest_id": "save-layout-native-v1",
        "build_mode": "private-diagnostic", "source_kind": guard.CANONICAL_SOURCE_KIND,
        "source_size": len(source), "source_sha256": contract.sha256(source),
        "target_size": len(target), "target_sha256": contract.sha256(target),
        "output_path": output.relative_to(contract.ROOT).as_posix(), "allocations": [], "writes": writes}
    # Both checks precede any output creation. No catalog override is supplied.
    guard.validate_manifest(manifest)
    audit = guard.audit_images(manifest, source, target)
    return target, {"contract": static, "write_intent_manifest": manifest, "write_intent_audit": audit}


def emit(source: bytes, output: Path, reviewed_bundle: str) -> dict:
    before = contract.bundle_identity()
    contract.require(reviewed_bundle == before["sha256"], "exact reviewed source-bundle hash required")
    destination = contract.private_path(output, must_not_exist=True)
    target, report = build_image(source, destination)
    contract.require(contract.bundle_identity() == before, "source changed during audit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation; never replace an existing diagnostic or input.
    with destination.open("xb") as handle:
        handle.write(target)
    report["source_bundle"] = before
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=contract.DEFAULT_ROM)
    parser.add_argument("--output", type=Path, default=contract.ROOT / "private/test_runs/save_layout_native_v1/diagnostic.sfc")
    parser.add_argument("--emit-reviewed-bundle", help="emit only after independent review of this exact bundle hash")
    args = parser.parse_args()
    source = args.rom.read_bytes()
    if args.emit_reviewed_bundle:
        report = emit(source, args.output, args.emit_reviewed_bundle)
    else:
        _image, report = build_image(source, args.output)
        report["source_bundle"] = contract.bundle_identity()
        report["emitted"] = False
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
