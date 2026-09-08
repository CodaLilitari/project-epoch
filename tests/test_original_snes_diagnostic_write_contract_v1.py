"""Adversarial original-cartridge guard tests; no cartridge image is written."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import original_snes_diagnostic_write_contract_v1 as contract
import validate_rom_write_intents as guard


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name).resolve()
        sources = []
        for path in sorted(contract.SOURCE_PATHS):
            artifact = cls.root / path
            artifact.parent.mkdir(parents=True, exist_ok=True)
            payload = ("Original test identity for " + path + "\n").encode("ascii")
            artifact.write_bytes(payload)
            sources.append({"path": path, "size": len(payload), "sha256": contract.sha(payload),
                            "provenance": "reviewed-original-project-source"})
        cls.source = b"\xff" * contract.SIZE
        image = bytearray(cls.source)
        sections = []
        source_paths = sorted(contract.SOURCE_PATHS)
        for section_id, (start, capacity, kind) in contract.SECTIONS.items():
            size = 64 if "header" in section_id else 0x500 if section_id == "immutable-registry" else 0x100
            payload = bytes(size)
            if "header" in section_id:
                header = bytearray(64)
                header[:21] = contract.TITLE
                header[21:28] = bytes([0x35, 2, 13, 3, 1, 0x33, 0])
                header[28:32] = b"\xff\xff\x00\x00"
                header[32:64] = b"\x00\x80" * 16
                payload = bytes(header)
            image[start:start+size] = payload
            sections.append({"id": section_id, "file_start": start, "size": size,
                             "owner": contract.OWNER, "payload_kind": kind,
                             "evidence_level": "verified-static", "source_paths": source_paths,
                             "preimage_sha256": contract.sha(b"\xff"*size),
                             "replacement_sha256": contract.sha(payload)})
        cls.manifest = {"schema": contract.SCHEMA, "build_mode": contract.MODE,
                        "source": {"kind": "literal-all-ff-8mib", "size": contract.SIZE, "sha256": contract.BLANK_SHA256},
                        "target": {"size": contract.SIZE, "sha256": "0"*64},
                        "sources": sources, "sections": sections,
                        "output": "private/test_runs/guard-test/original.sfc"}
        cls.target = cls.finalize(image, cls.manifest)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @staticmethod
    def finalize(image, manifest):
        for start in (0xFFC0, 0x40FFC0):
            image[start+28:start+32] = b"\xff\xff\x00\x00"
        checksum = sum(image) & 0xffff
        for start in (0xFFC0, 0x40FFC0):
            image[start+28:start+32] = (checksum ^ 0xffff).to_bytes(2,"little") + checksum.to_bytes(2,"little")
        for section in manifest["sections"]:
            start = section["file_start"]
            section["replacement_sha256"] = contract.sha(image[start:start+section["size"]])
        manifest["target"]["sha256"] = contract.sha(image)
        return bytes(image)

    def reject_metadata(self, mutate):
        manifest = copy.deepcopy(self.manifest)
        mutate(manifest)
        with self.assertRaises(contract.OriginalDiagnosticIntentError):
            guard.validate_original_diagnostic_manifest(manifest, workspace_root=self.root)

    def test_positive_intent_and_complete_diff(self):
        result = guard.audit_original_diagnostic_images(self.manifest, self.source, self.target, workspace_root=self.root)
        self.assertTrue(result["complete_diff_coverage"])
        self.assertEqual(result["status"], "images-valid")
        self.assertFalse(result["production_approval"])
        self.assertFalse((self.root/self.manifest["output"]).exists())

    def test_legacy_catalogs_and_new_namespace_are_separate(self):
        self.assertEqual(set(guard.SOURCE_KINDS), {guard.CANONICAL_SOURCE_KIND, guard.INERT_SOURCE_KIND})
        self.assertFalse(guard.APPROVED_PRODUCTION_ALLOCATIONS)
        self.assertFalse(guard.APPROVED_PRODUCTION_HOOKS)
        with self.assertRaises(guard.WriteIntentError):
            guard.validate_manifest(self.manifest)

    def test_game_source_rejected(self):
        for kind, (size, digest) in guard.SOURCE_KINDS.items():
            with self.subTest(kind=kind):
                self.reject_metadata(lambda m: m.update(source={"kind":kind, "size":size, "sha256":digest}))

    def test_production_and_legacy_diagnostic_modes_rejected(self):
        for mode in ("production", "private-diagnostic", None, True):
            with self.subTest(mode=mode):
                self.reject_metadata(lambda m: m.update(build_mode=mode))

    def test_unknown_fields_and_catalogs_rejected(self):
        for field in ("allocation_catalog", "hook_catalog", "allow_unsafe", "production_approval"):
            with self.subTest(field=field):
                self.reject_metadata(lambda m: m.update({field: []}))

    def test_missing_extra_duplicate_or_reordered_sections_rejected(self):
        for change in (lambda m: m["sections"].pop(),
                       lambda m: m["sections"].append(copy.deepcopy(m["sections"][0])),
                       lambda m: m["sections"].__setitem__(1, copy.deepcopy(m["sections"][0])),
                       lambda m: m["sections"].reverse()):
            self.reject_metadata(change)

    def test_section_wrong_span_owner_kind_or_evidence_rejected(self):
        for field, value in (("file_start",0x8001),("file_start",True),("size",0),("size",0x1001),
                             ("size",True),("owner","game"),("payload_kind","code"),("evidence_level","hypothesis"),
                             ("id","production-allocation"),("extra",0)):
            with self.subTest(field=field,value=value):
                self.reject_metadata(lambda m: m["sections"][0].update({field:value}))

    def test_header_and_registry_exact_size_rejected(self):
        for index in (1,3,6):
            self.reject_metadata(lambda m: m["sections"][index].update(size=63))

    def test_preimage_and_unchanged_section_rejected(self):
        self.reject_metadata(lambda m: m["sections"][0].update(preimage_sha256="0"*64))
        self.reject_metadata(lambda m: m["sections"][0].update(replacement_sha256=m["sections"][0]["preimage_sha256"]))

    def test_source_inventory_rejected(self):
        for change in (lambda m:m["sources"].pop(),lambda m:m["sources"].reverse(),
                       lambda m:m["sources"][0].update(path="private/input/game.sfc"),
                       lambda m:m["sources"][0].update(size=True),
                       lambda m:m["sources"][0].update(provenance="extracted-game"),
                       lambda m:m["sections"][0].update(source_paths=[]),
                       lambda m:m["sections"][0].update(source_paths=["asm/../game.sfc"])):
            self.reject_metadata(change)

    def test_mirror_metadata_rejected(self):
        for field,value in (("size",0xff),("replacement_sha256","0"*64),
                            ("source_paths",[sorted(contract.SOURCE_PATHS)[0]])):
            self.reject_metadata(lambda m: m["sections"][2].update({field:value}))

    def test_invalid_output_paths_rejected(self):
        for path in ("game.sfc", "private/test_runs/x.sfc", "private/test_runs/x/game.srm",
                     "private/test_runs/../x/a.sfc", "/private/test_runs/x/a.sfc",
                     "C:/private/test_runs/x/a.sfc", "private\\test_runs\\x\\a.sfc",
                     "private/test_runs/x/a.sfc:stream", "private//test_runs/x/a.sfc",
                     "private/test_runs/x/a.sfc\x00", "private/test_runs/x/./a.sfc"):
            with self.subTest(path=path):
                self.reject_metadata(lambda m:m.update(output=path))

    def test_existing_output_refused_without_overwrite(self):
        path=self.root/self.manifest["output"]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b"preserve")
        try:
            self.reject_metadata(lambda m:None)
            self.assertEqual(path.read_bytes(),b"preserve")
        finally:
            path.unlink()

    def test_windows_reserved_and_aliasing_output_components_rejected(self):
        for tail in ("NUL.sfc", "CON.sfc", "AUX/game.sfc", "run./game.sfc", "run /game.sfc",
                     "COM1.sfc", "LPT9.sfc", "COM¹.sfc", "a\x01.sfc", "a?.sfc", "a*.sfc", 'a".sfc',
                     "CONIN$.sfc", "CONOUT$.sfc", "NUL .sfc", "COM1 .sfc", "LPT2 .sfc", "AUX .sfc"):
            with self.subTest(tail=tail):
                self.reject_metadata(lambda m:m.update(output="private/test_runs/guard-test/"+tail))

    def test_observed_source_or_target_identity_rejected(self):
        for source,target in ((self.source[:-1],self.target), (b"\0"+self.source[1:],self.target),
                              (self.source,self.target[:-1]), (self.source,b"\0"+self.target[1:])):
            with self.assertRaises(contract.OriginalDiagnosticIntentError):
                guard.audit_original_diagnostic_images(self.manifest, source, target, workspace_root=self.root)

    def test_stale_original_source_hash_rejected(self):
        path=self.root/self.manifest["sources"][0]["path"]
        original=path.read_bytes()
        try:
            path.write_bytes(original+b"drift")
            with self.assertRaises(contract.OriginalDiagnosticIntentError):
                guard.audit_original_diagnostic_images(self.manifest,self.source,self.target,workspace_root=self.root)
        finally:
            path.write_bytes(original)

    def test_uncovered_change_rejected_even_with_fresh_hashes_and_checksum(self):
        for address in (0,0x8100,0x10000,0x418000,0x7fffff):
            with self.subTest(address=address):
                image=bytearray(self.target);image[address]^=1
                manifest=copy.deepcopy(self.manifest);target=self.finalize(image,manifest)
                with self.assertRaisesRegex(contract.OriginalDiagnosticIntentError,"undeclared"):
                    guard.audit_original_diagnostic_images(manifest,self.source,target,workspace_root=self.root)

    def test_header_fields_and_vectors_rejected_with_fresh_hashes(self):
        for offset,value in ((0,ord("X")),(21,0x31),(22,0),(23,12),(24,0),(25,0),(26,0),(27,1),
                             (33,0x7f),(33,0x81),(61,0x7f),(61,0x81)):
            image=bytearray(self.target)
            for start in (0xffc0,0x40ffc0): image[start+offset]=value
            manifest=copy.deepcopy(self.manifest);target=self.finalize(image,manifest)
            with self.subTest(offset=offset),self.assertRaises(contract.OriginalDiagnosticIntentError):
                guard.audit_original_diagnostic_images(manifest,self.source,target,workspace_root=self.root)

    def test_invalid_checksum_with_fresh_hashes_rejected(self):
        image=bytearray(self.target)
        for start in (0xffc0,0x40ffc0): image[start+30]^=1
        manifest=copy.deepcopy(self.manifest)
        for section in manifest["sections"]:
            start=section["file_start"]
            section["replacement_sha256"]=contract.sha(image[start:start+section["size"]])
        manifest["target"]["sha256"]=contract.sha(image)
        with self.assertRaisesRegex(contract.OriginalDiagnosticIntentError,"checksum"):
            guard.audit_original_diagnostic_images(manifest,self.source,bytes(image),workspace_root=self.root)


if __name__ == "__main__":
    unittest.main()
