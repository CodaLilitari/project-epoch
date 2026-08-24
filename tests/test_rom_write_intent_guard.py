from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "validate_rom_write_intents.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_rom_write_intents", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(
    *,
    write_id: str,
    classification: str,
    start: int,
    before: bytes,
    after: bytes,
    owner: str,
    payload_kind: str,
    evidence: str = "verified-static",
    allocation_id: str | None = None,
    hook_id: str | None = None,
    table_id: str | None = None,
    header_field_id: str | None = None,
    replacement_hex: str | None = None,
) -> dict[str, object]:
    return {
        "write_id": write_id,
        "classification": classification,
        "file_start": start,
        "size": len(before),
        "owner": owner,
        "payload_kind": payload_kind,
        "evidence": evidence,
        "preimage_sha256": hash_bytes(before),
        "replacement_sha256": hash_bytes(after),
        "allocation_id": allocation_id,
        "hook_id": hook_id,
        "table_id": table_id,
        "header_field_id": header_field_id,
        "replacement_hex": replacement_hex,
    }


def manifest(
    writes: list[dict[str, object]],
    *,
    mode: str,
    source_kind: str,
    source_sha256: str,
    target_sha256: str,
    size: int,
    allocations: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "manifest_id": "test-write-intents",
        "build_mode": mode,
        "source_kind": source_kind,
        "source_size": size,
        "source_sha256": source_sha256,
        "target_size": size,
        "target_sha256": target_sha256,
        "output_path": (
            "private/test_runs/write_guard/test.sfc"
            if mode == "private-diagnostic"
            else None
        ),
        "allocations": allocations or [],
        "writes": sorted(
            writes, key=lambda item: (item["file_start"], item["write_id"])
        ),
    }


class MetadataGuardTests(unittest.TestCase):
    def diagnostic_manifest(
        self, *, start: int = 0x1000, payload_kind: str = "graphics"
    ) -> dict[str, object]:
        before = b"\x01\x02\x03\x04"
        after = b"\x05\x06\x07\x08"
        intent = write(
            write_id="private-sprite-smoke",
            classification="private-diagnostic-replacement",
            start=start,
            before=before,
            after=after,
            owner="schala-supported-slot-smoke",
            payload_kind=payload_kind,
        )
        return manifest(
            [intent],
            mode="private-diagnostic",
            source_kind=TOOL.CANONICAL_SOURCE_KIND,
            source_sha256=TOOL.CANONICAL_SOURCE_SHA256,
            target_sha256="1" * 64,
            size=TOOL.scaffold.EXPECTED_SOURCE_SIZE,
        )

    def test_private_exact_preimage_diagnostic_is_metadata_valid(self) -> None:
        report = TOOL.validate_manifest(self.diagnostic_manifest())
        self.assertEqual(report["status"], "metadata-valid")
        self.assertEqual(report["write_count"], 1)
        self.assertFalse(report["rom_modified"])
        self.assertEqual(report["production_hooks_currently_approved"], 0)
        self.assertEqual(
            report["production_allocations_currently_approved"], 0
        )

    def test_diagnostic_must_be_private_and_named(self) -> None:
        bad = self.diagnostic_manifest()
        bad["build_mode"] = "production"
        bad["output_path"] = None
        bad["source_kind"] = TOOL.INERT_SOURCE_KIND
        bad["source_size"] = TOOL.scaffold.TARGET_SIZE
        bad["target_size"] = TOOL.scaffold.TARGET_SIZE
        bad["source_sha256"] = TOOL.INERT_SOURCE_SHA256
        with self.assertRaisesRegex(TOOL.WriteIntentError, "nonproduction"):
            TOOL.validate_manifest(bad)

        bad = self.diagnostic_manifest()
        bad["output_path"] = "../outside.sfc"
        with self.assertRaisesRegex(TOOL.WriteIntentError, "private/"):
            TOOL.validate_manifest(bad)

        bad = self.diagnostic_manifest()
        bad["output_path"] = "private"
        with self.assertRaisesRegex(TOOL.WriteIntentError, "below private/"):
            TOOL.validate_manifest(bad)

        bad = self.diagnostic_manifest()
        bad["output_path"] = "private/test_runs/not-a-rom.bin"
        with self.assertRaisesRegex(TOOL.WriteIntentError, "ROM image"):
            TOOL.validate_manifest(bad)

        bad = self.diagnostic_manifest()
        bad["writes"][0]["owner"] = ""
        with self.assertRaisesRegex(TOOL.WriteIntentError, "stable ID"):
            TOOL.validate_manifest(bad)

    def test_protected_vanilla_epoch_and_scaffold_ranges_are_denied(self) -> None:
        starts = (
            0x0D400E,
            0x0C63F6,
            0x025FE6,
            0x3FCE50,
            0x242015,
        )
        for start in starts:
            with self.subTest(start=start):
                bad = self.diagnostic_manifest(start=start)
                with self.assertRaisesRegex(
                    TOOL.WriteIntentError, "overlaps protected"
                ):
                    TOOL.validate_manifest(bad)

        bank40 = self.diagnostic_manifest(start=0x400100)
        bank40["source_kind"] = TOOL.INERT_SOURCE_KIND
        bank40["source_size"] = TOOL.scaffold.TARGET_SIZE
        bank40["target_size"] = TOOL.scaffold.TARGET_SIZE
        bank40["source_sha256"] = TOOL.INERT_SOURCE_SHA256
        with self.assertRaisesRegex(
            TOOL.WriteIntentError, "overlaps protected"
        ):
            TOOL.validate_manifest(bank40)

    def test_unknown_production_vanilla_write_is_not_relabelable(self) -> None:
        bad = self.diagnostic_manifest()
        bad["build_mode"] = "production"
        bad["output_path"] = None
        bad["source_kind"] = TOOL.INERT_SOURCE_KIND
        bad["source_size"] = TOOL.scaffold.TARGET_SIZE
        bad["target_size"] = TOOL.scaffold.TARGET_SIZE
        bad["source_sha256"] = TOOL.INERT_SOURCE_SHA256
        bad["writes"][0]["classification"] = "named-expanded-allocation"
        bad["writes"][0]["allocation_id"] = "fake-free-space"
        with self.assertRaisesRegex(TOOL.WriteIntentError, "not trusted"):
            TOOL.validate_manifest(bad)

    def test_table_diagnostic_rejects_in_place_extension(self) -> None:
        table = next(
            table
            for table in TOOL.KNOWN_TABLES
            if table.table_id == "tech_names"
        )
        bad = self.diagnostic_manifest(
            start=table.span.end - 2, payload_kind="table"
        )
        bad["writes"][0]["table_id"] = "tech_names"
        with self.assertRaisesRegex(
            TOOL.WriteIntentError, "in-place table extension"
        ):
            TOOL.validate_manifest(bad)

    def test_lucca_aux_diagnostic_is_exactly_bounded(self) -> None:
        table = next(
            table
            for table in TOOL.KNOWN_TABLES
            if table.table_id == "lucca_aux_animation"
        )
        valid = self.diagnostic_manifest(
            start=table.span.start,
            payload_kind="table",
        )
        valid["writes"][0]["table_id"] = table.table_id
        self.assertEqual(
            TOOL.validate_manifest(valid)["status"],
            "metadata-valid",
        )

        for start in (table.span.start - 1, table.span.end - 3):
            with self.subTest(start=start):
                bad = self.diagnostic_manifest(
                    start=start,
                    payload_kind="table",
                )
                bad["writes"][0]["table_id"] = table.table_id
                with self.assertRaisesRegex(
                    TOOL.WriteIntentError,
                    "in-place table extension",
                ):
                    TOOL.validate_manifest(bad)

    def test_exact_hook_requires_trusted_site_span_owner_and_bytes(self) -> None:
        preimage = bytes.fromhex("a90100")
        replacement = bytes.fromhex("220000")
        hook = TOOL.ApprovedHook(
            hook_id="test-field-resolver-hook",
            file_start=0x010000,
            preimage_hex=preimage.hex(),
            owner="field-palette-resolver",
            evidence="verified-static",
            source_kind=TOOL.INERT_SOURCE_KIND,
            purpose="unit-test exact instruction boundary",
        )
        intent = write(
            write_id="install-field-resolver-hook",
            classification="exact-instruction-hook",
            start=hook.file_start,
            before=preimage,
            after=replacement,
            owner=hook.owner,
            payload_kind="code",
            hook_id=hook.hook_id,
            replacement_hex=replacement.hex(),
        )
        good = manifest(
            [intent],
            mode="production",
            source_kind=TOOL.INERT_SOURCE_KIND,
            source_sha256=TOOL.INERT_SOURCE_SHA256,
            target_sha256="2" * 64,
            size=TOOL.scaffold.TARGET_SIZE,
        )
        TOOL.validate_manifest(good, hook_catalog=(hook,))
        with self.assertRaisesRegex(TOOL.WriteIntentError, "not trusted"):
            TOOL.validate_manifest(good)

        bad = copy.deepcopy(good)
        bad["writes"][0]["size"] = 2
        with self.assertRaisesRegex(TOOL.WriteIntentError, "exact approved"):
            TOOL.validate_manifest(bad, hook_catalog=(hook,))

    def test_hook_cannot_overlap_a_data_table(self) -> None:
        preimage = b"\xEA\xEA"
        replacement = b"\x80\x00"
        hook = TOOL.ApprovedHook(
            hook_id="mislabelled-table-hook",
            file_start=0x0C15CF,
            preimage_hex=preimage.hex(),
            owner="bad-hook",
            evidence="verified-static",
            source_kind=TOOL.INERT_SOURCE_KIND,
            purpose="negative test",
        )
        intent = write(
            write_id="mislabelled-table-hook-write",
            classification="exact-instruction-hook",
            start=hook.file_start,
            before=preimage,
            after=replacement,
            owner=hook.owner,
            payload_kind="code",
            hook_id=hook.hook_id,
            replacement_hex=replacement.hex(),
        )
        bad = manifest(
            [intent],
            mode="production",
            source_kind=TOOL.INERT_SOURCE_KIND,
            source_sha256=TOOL.INERT_SOURCE_SHA256,
            target_sha256="3" * 64,
            size=TOOL.scaffold.TARGET_SIZE,
        )
        with self.assertRaisesRegex(TOOL.WriteIntentError, "data table"):
            TOOL.validate_manifest(bad, hook_catalog=(hook,))

    def test_expanded_write_requires_exact_trusted_named_allocation(self) -> None:
        allocation = TOOL.ApprovedAllocation(
            allocation_id="test-schala-palette",
            file_start=0x410000,
            size=0x20,
            snes_start=0x410000,
            kind="palette",
            owner="schala-field-palette",
            evidence="verified-static",
            source_artifact_sha256="4" * 64,
            consumers=("write-schala-field-palette",),
            alignment=0x10,
            no_bank_cross=True,
        )
        before = b"\xFF" * 0x20
        after = bytes(range(0x20))
        intent = write(
            write_id="write-schala-field-palette",
            classification="named-expanded-allocation",
            start=allocation.file_start,
            before=before,
            after=after,
            owner=allocation.owner,
            payload_kind="palette",
            allocation_id=allocation.allocation_id,
        )
        allocation_metadata = dataclasses_asdict(allocation)
        good = manifest(
            [intent],
            mode="production",
            source_kind=TOOL.INERT_SOURCE_KIND,
            source_sha256=TOOL.INERT_SOURCE_SHA256,
            target_sha256="5" * 64,
            size=TOOL.scaffold.TARGET_SIZE,
            allocations=[allocation_metadata],
        )
        TOOL.validate_manifest(good, allocation_catalog=(allocation,))
        with self.assertRaisesRegex(TOOL.WriteIntentError, "trusted catalog"):
            TOOL.validate_manifest(good)

        bad = copy.deepcopy(good)
        bad["writes"][0]["file_start"] += 0x10
        with self.assertRaisesRegex(TOOL.WriteIntentError, "exceeds"):
            TOOL.validate_manifest(bad, allocation_catalog=(allocation,))

    def test_bank40_and_tail_cannot_be_claimed_as_allocations(self) -> None:
        for start in (0x400000, 0x7E0000):
            with self.subTest(start=start):
                allocation = TOOL.ApprovedAllocation(
                    allocation_id=f"invalid-{start:x}",
                    file_start=start,
                    size=0x10,
                    snes_start=start,
                    kind="code",
                    owner="invalid-owner",
                    evidence="verified-static",
                    source_artifact_sha256="6" * 64,
                    consumers=("invalid-write",),
                    alignment=0x10,
                )
                before = b"\xFF" * 0x10
                after = b"\x00" * 0x10
                intent = write(
                    write_id="invalid-write",
                    classification="named-expanded-allocation",
                    start=start,
                    before=before,
                    after=after,
                    owner=allocation.owner,
                    payload_kind="code",
                    allocation_id=allocation.allocation_id,
                )
                bad = manifest(
                    [intent],
                    mode="production",
                    source_kind=TOOL.INERT_SOURCE_KIND,
                    source_sha256=TOOL.INERT_SOURCE_SHA256,
                    target_sha256="7" * 64,
                    size=TOOL.scaffold.TARGET_SIZE,
                    allocations=[dataclasses_asdict(allocation)],
                )
                with self.assertRaisesRegex(
                    TOOL.WriteIntentError, "outside approved expanded banks"
                ):
                    TOOL.validate_manifest(
                        bad, allocation_catalog=(allocation,)
                    )

    def test_only_exact_managed_header_fields_are_exempt(self) -> None:
        before = b"\x00\x00\x00\x00"
        after = b"\xFF\xFF\x12\x34"
        field = next(
            item
            for item in TOOL.HEADER_FIELDS
            if item.field_id == "exhirom_checksum_pair"
        )
        intent = write(
            write_id="finalize-exhirom-checksum",
            classification="managed-header-field",
            start=field.span.start,
            before=before,
            after=after,
            owner="rom_checksum_finalizer",
            payload_kind="header",
            header_field_id=field.field_id,
        )
        good = manifest(
            [intent],
            mode="production",
            source_kind=TOOL.INERT_SOURCE_KIND,
            source_sha256=TOOL.INERT_SOURCE_SHA256,
            target_sha256="8" * 64,
            size=TOOL.scaffold.TARGET_SIZE,
        )
        TOOL.validate_manifest(good)
        bad = copy.deepcopy(good)
        bad["writes"][0]["size"] = 3
        with self.assertRaisesRegex(TOOL.WriteIntentError, "span is not exact"):
            TOOL.validate_manifest(bad)

    def test_overlapping_and_unknown_schema_fields_fail_closed(self) -> None:
        good = self.diagnostic_manifest()
        second = copy.deepcopy(good["writes"][0])
        second["write_id"] = "overlap"
        second["file_start"] += 1
        good["writes"].append(second)
        good["writes"].sort(
            key=lambda item: (item["file_start"], item["write_id"])
        )
        with self.assertRaisesRegex(TOOL.WriteIntentError, "overlaps"):
            TOOL.validate_manifest(good)

        bad = self.diagnostic_manifest()
        bad["allow_free_space_scan"] = True
        with self.assertRaisesRegex(TOOL.WriteIntentError, "unknown keys"):
            TOOL.validate_manifest(bad)


def dataclasses_asdict(
    allocation: TOOL.ApprovedAllocation,
) -> dict[str, object]:
    return {
        "allocation_id": allocation.allocation_id,
        "file_start": allocation.file_start,
        "size": allocation.size,
        "snes_start": allocation.snes_start,
        "kind": allocation.kind,
        "owner": allocation.owner,
        "evidence": allocation.evidence,
        "source_artifact_sha256": allocation.source_artifact_sha256,
        "consumers": list(allocation.consumers),
        "alignment": allocation.alignment,
        "no_bank_cross": allocation.no_bank_cross,
    }


class ReadOnlyArtifactAuditTests(unittest.TestCase):
    def test_observed_managed_checksum_must_match_the_image(self) -> None:
        source = bytearray(TOOL.scaffold.EXPECTED_SOURCE_SIZE)
        source_hash = hash_bytes(bytes(source))
        old_contract = TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND]
        TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND] = (
            len(source),
            source_hash,
        )
        try:
            start = (
                TOOL.scaffold.HIROM_HEADER
                + TOOL.scaffold.HEADER_COMPLEMENT
            )
            target = bytearray(source)
            target[start : start + 4] = b"\x00\x00\x01\x00"
            intent = write(
                write_id="bad-checksum",
                classification="managed-header-field",
                start=start,
                before=bytes(source[start : start + 4]),
                after=bytes(target[start : start + 4]),
                owner="rom_checksum_finalizer",
                payload_kind="header",
                header_field_id="hirom_checksum_pair",
            )
            bad = manifest(
                [intent],
                mode="private-diagnostic",
                source_kind=TOOL.CANONICAL_SOURCE_KIND,
                source_sha256=source_hash,
                target_sha256=hash_bytes(bytes(target)),
                size=len(source),
            )
            with self.assertRaisesRegex(
                TOOL.WriteIntentError,
                "checksum pair is invalid",
            ):
                TOOL.audit_images(bad, bytes(source), bytes(target))
        finally:
            TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND] = old_contract

    def test_complete_diff_coverage_rejects_undeclared_byte(self) -> None:
        source = bytearray(TOOL.scaffold.EXPECTED_SOURCE_SIZE)
        source_hash = hash_bytes(bytes(source))
        # This test uses a synthetic source kind by temporarily matching the
        # canonical contract; no local ROM is read.
        old_contract = TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND]
        TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND] = (
            len(source),
            source_hash,
        )
        try:
            target = bytearray(source)
            target[0x1000:0x1004] = b"TEST"
            intent = write(
                write_id="declared",
                classification="private-diagnostic-replacement",
                start=0x1000,
                before=b"\x00" * 4,
                after=b"TEST",
                owner="synthetic-audit",
                payload_kind="graphics",
            )
            good = manifest(
                [intent],
                mode="private-diagnostic",
                source_kind=TOOL.CANONICAL_SOURCE_KIND,
                source_sha256=source_hash,
                target_sha256=hash_bytes(bytes(target)),
                size=len(source),
            )
            report = TOOL.audit_images(good, bytes(source), bytes(target))
            self.assertTrue(report["complete_diff_coverage"])
            self.assertEqual(report["changed_byte_count"], 4)

            target[0x2000] = 1
            bad = copy.deepcopy(good)
            bad["target_sha256"] = hash_bytes(bytes(target))
            with self.assertRaisesRegex(
                TOOL.WriteIntentError, "undeclared changed byte"
            ):
                TOOL.audit_images(bad, bytes(source), bytes(target))
        finally:
            TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND] = old_contract

    def test_observed_preimage_and_replacement_hashes_are_exact(self) -> None:
        source = bytearray(TOOL.scaffold.EXPECTED_SOURCE_SIZE)
        source_hash = hash_bytes(bytes(source))
        old_contract = TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND]
        TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND] = (
            len(source),
            source_hash,
        )
        try:
            target = bytearray(source)
            target[0x1000:0x1004] = b"TEST"
            intent = write(
                write_id="declared",
                classification="private-diagnostic-replacement",
                start=0x1000,
                before=b"\x01" * 4,
                after=b"TEST",
                owner="synthetic-audit",
                payload_kind="graphics",
            )
            bad = manifest(
                [intent],
                mode="private-diagnostic",
                source_kind=TOOL.CANONICAL_SOURCE_KIND,
                source_sha256=source_hash,
                target_sha256=hash_bytes(bytes(target)),
                size=len(source),
            )
            with self.assertRaisesRegex(
                TOOL.WriteIntentError, "preimage hash mismatch"
            ):
                TOOL.audit_images(bad, bytes(source), bytes(target))
        finally:
            TOOL.SOURCE_KINDS[TOOL.CANONICAL_SOURCE_KIND] = old_contract

    @unittest.skipUnless(
        (
            ROOT
            / "private"
            / "test_runs"
            / "schala_supported_slot_sprite_smoke_v0"
            / "schala_lucca_slot_sprite_smoke_v0.sfc"
        ).exists(),
        "private Schala supported-slot diagnostic is unavailable",
    )
    def test_current_schala_supported_slot_artifact_has_full_coverage(
        self,
    ) -> None:
        source_path = (
            ROOT
            / "private"
            / "input"
            / "rom_archive"
            / "Chrono Trigger (USA).sfc"
        )
        run_dir = (
            ROOT
            / "private"
            / "test_runs"
            / "schala_supported_slot_sprite_smoke_v0"
        )
        target_path = run_dir / "schala_lucca_slot_sprite_smoke_v0.sfc"
        report_path = target_path.with_suffix(".manifest.json")
        source = source_path.read_bytes()
        target = target_path.read_bytes()
        old_report = json.loads(report_path.read_text(encoding="utf-8"))

        writes = []
        for index, change in enumerate(old_report["changes"]):
            label = change["label"]
            start = change["file_start"]
            end = change["file_end_exclusive"]
            before = source[start:end]
            after = target[start:end]
            classification = "private-diagnostic-replacement"
            payload_kind = "graphics"
            owner = "schala-supported-slot-smoke"
            table_id = None
            header_field_id = None
            if "animation" in label.lower():
                payload_kind = "table"
                table_id = "lucca_animation"
            elif "palette" in label.lower():
                payload_kind = "palette"
            elif "checksum complement" in label.lower():
                classification = "managed-header-field"
                payload_kind = "header"
                owner = "rom_checksum_finalizer"
                header_field_id = "hirom_checksum_pair"
                # The old builder reports the pair as two adjacent writes.
                # Merge is handled after this loop.
            elif label == "SNES checksum":
                continue
            writes.append(
                write(
                    write_id=f"smoke-write-{index:02d}",
                    classification=classification,
                    start=start,
                    before=before,
                    after=after,
                    owner=owner,
                    payload_kind=payload_kind,
                    table_id=table_id,
                    header_field_id=header_field_id,
                )
            )

        checksum = next(
            item
            for item in writes
            if item["header_field_id"] == "hirom_checksum_pair"
        )
        checksum["size"] = 4
        checksum["preimage_sha256"] = hash_bytes(
            source[TOOL.scaffold.HIROM_HEADER + TOOL.scaffold.HEADER_COMPLEMENT :
                   TOOL.scaffold.HIROM_HEADER + TOOL.scaffold.HEADER_CHECKSUM + 2]
        )
        checksum["replacement_sha256"] = hash_bytes(
            target[TOOL.scaffold.HIROM_HEADER + TOOL.scaffold.HEADER_COMPLEMENT :
                   TOOL.scaffold.HIROM_HEADER + TOOL.scaffold.HEADER_CHECKSUM + 2]
        )

        current = manifest(
            writes,
            mode="private-diagnostic",
            source_kind=TOOL.CANONICAL_SOURCE_KIND,
            source_sha256=hash_bytes(source),
            target_sha256=hash_bytes(target),
            size=len(source),
        )
        current["manifest_id"] = "schala-supported-slot-smoke-v0-audit"
        current["output_path"] = (
            "private/test_runs/schala_supported_slot_sprite_smoke_v0/"
            "schala_lucca_slot_sprite_smoke_v0.sfc"
        )
        result = TOOL.audit_images(current, source, target)
        self.assertTrue(result["complete_diff_coverage"])
        self.assertTrue(result["preimages_verified"])
        self.assertEqual(
            result["target_sha256"],
            "6c45548175ed77c93eb17e0461dba344669e0af3b3239eab949b63fe1044e355",
        )


if __name__ == "__main__":
    unittest.main()
