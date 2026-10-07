"""Adversarial fixed-contract tests, using synthetic images only.

The synthetic source identity and tiny source-artifact identities are substituted
with unittest.mock inside each test. The shipped literal pins are tested
separately and are never made configurable through the public API. No game ROM,
image output, private source corpus, assembler or emulator is needed.
"""
from __future__ import annotations

import copy
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import pc07_private_expanded_write_contract_v1 as contract


# Original project-authored component, independently fixed here; no game bytes.
HELPER = bytes.fromhex(
    "0848c907d022bf01117ec907d01abf00117ec902d012af82297ec907d00aec9b01d005"
    "68a9008001688d024228c8a9056b08e00700d00628af46f8cc6b28bf46f8cc6b"
    "08e00700d00628af8325cc6b28bf8325cc6b08e00700d00628af3cf6cc6b28bf3cf6cc6b"
    "08e00700d00628af0040cd6b28bf0040cd6b08e00700d00628af0740cd6b28bf0740cd6b"
    "08e00700d00628af0e40cd6b28bf0e40cd6b")
COMPAT = (
    (0x3FF86D, "bd3728", "bda72c"), (0x3FF9A2, "393728", "39a72c"),
    (0x0282E4, "9c5728", "9cc72c"), (0x0282E7, "a25728", "a2c72c"),
    (0x0282EA, "a05928", "a0c92c"), (0x02830E, "99a927", "99192c"),
    (0x02B9AF, "a25728", "a2c72c"),
)


def _checksum(image):
    # Independent standard pair calculation, not the contract's delta formula.
    for offset in (0xFFDC, 0x40FFDC):
        image[offset:offset + 4] = bytes.fromhex("ffff0000")
    checksum = sum(image) & 0xFFFF
    pair = (checksum ^ 0xFFFF).to_bytes(2, "little") + checksum.to_bytes(2, "little")
    for offset in (0xFFDC, 0x40FFDC):
        image[offset:offset + 4] = pair
    return checksum


def _synthetic_source():
    image = bytearray(0x400000) + bytearray(b"\xff" * 0x400000)
    for offset, original, _ in COMPAT:
        image[offset:offset + 3] = bytes.fromhex(original)
    image[0x448D:0x4493] = bytes.fromhex("8d0242c8a905")
    image[0xFFD5], image[0xFFD7] = 0x35, 0x0D
    image[0xFFDC:0xFFE0] = bytes.fromhex("91c66e39")
    image[0x400000:0x410000] = image[:0x10000]
    # Set an otherwise arbitrary synthetic lower-bank area so the source has
    # the fixed scaffold's checksum. No canonical game data is reconstructed.
    delta = (0x396E - sum(image)) & 0xFFFF
    for offset in range(0x100000, 0x100101):
        value = min(delta, 255)
        image[offset] = value
        delta -= value
    assert delta == 0 and _checksum(image) == 0x396E
    return bytes(image)


class LiteralPinsTests(unittest.TestCase):
    def test_shipped_pins_mapping_and_component(self):
        self.assertEqual(contract.SCAFFOLD_SHA256,
                         "26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93")
        self.assertEqual((len(HELPER), contract.sha(HELPER), sum(HELPER)),
                         (157, "315f409ece80e84c656930c47bc5a0d6e0f97d83aecc95b7c474abc2056750e7", 15951))
        self.assertEqual(contract.SOURCE_PINS[0],
                         ("asm/pc07_donor_read_adapters_v2.asm", 2541,
                          "df0584a820d3b6b4994298cc1f0d6b3ffc4089797b42c5d6c6217d02a4e5a914"))
        self.assertEqual(contract.TARGET_HEADER_PAIR, bytes.fromhex("982267dd"))
        self.assertEqual(contract.scaffold.exhirom_snes_to_file(0x410000), 0x410000)
        self.assertEqual(contract.scaffold.exhirom_snes_to_file(0xC0448D), 0x448D)
        self.assertEqual(contract.scaffold.exhirom_snes_to_file(0x40448D), 0x40448D)
        self.assertIsNone(contract.scaffold.exhirom_snes_to_file(0x00448D))


class FixedImageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = _synthetic_source()
        target = bytearray(cls.source)
        for offset, _, replacement in COMPAT:
            target[offset:offset + 3] = bytes.fromhex(replacement)
        for offset in (0x448D, 0x40448D):
            target[offset:offset + 6] = bytes.fromhex("22000041eaea")
        target[0x410000:0x41009D] = HELPER
        assert _checksum(target) == 0xDD67
        cls.target = bytes(target)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        synthetic_pins = []
        for relative, _, _ in contract.SOURCE_PINS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = ("Synthetic original source identity: " + relative).encode("utf-8")
            path.write_bytes(data)
            synthetic_pins.append((relative, len(data), contract.sha(data)))
        self.enterContext(patch.object(contract, "SOURCE_PINS", tuple(synthetic_pins)))
        self.enterContext(patch.object(contract, "SCAFFOLD_SHA256", contract.sha(self.source)))
        self.output = "private/test_runs/field-contract-test/diagnostic.sfc"
        self.manifest = contract._template(contract.sha(self.target), self.output)

    def audit(self, target=None, source=None, manifest=None):
        return contract.audit_images(self.manifest if manifest is None else manifest,
                                     self.source if source is None else source,
                                     self.target if target is None else target,
                                     workspace_root=self.root)

    def reject_target(self, data, message=None):
        manifest = copy.deepcopy(self.manifest)
        manifest["target"]["sha256"] = contract.sha(data)
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, message or "."):
            self.audit(target=bytes(data), manifest=manifest)

    def test_valid_fixed_image_and_existing_assembly_parent(self):
        parent = (self.root / self.output).parent
        parent.mkdir()
        (parent / "assembly-note.txt").write_text("assembly staging may already exist", encoding="utf-8")
        manifest = contract.build_manifest(self.source, self.target, self.output, workspace_root=self.root)
        self.assertEqual(manifest, self.manifest)
        receipt = self.audit(manifest=manifest)
        self.assertEqual(receipt["changed_byte_count"], 191)
        self.assertEqual(receipt["compatibility_changed_bytes"], 14)
        self.assertTrue(receipt["complete_diff_coverage"])
        self.assertTrue(receipt["full_boot_mirror_verified"])
        for field in ("production_approval", "playable_pc_proof", "game_allocation_proof", "runtime_proof", "rom_modified"):
            self.assertIs(receipt[field], False)
        self.assertFalse((self.root / self.output).exists())
        self.assertEqual(contract.validate_manifest(manifest, workspace_root=self.root)["status"], "metadata-valid")

    def test_schema_catalog_provenance_and_typed_metadata_refuse(self):
        changes = [lambda m: m.update(build_mode="production"),
                   lambda m: m.update(schema="project-epoch-original-snes-diagnostic-intents-v1"),
                   lambda m: m.update(approval=True), lambda m: m.update(hook_catalog=[]),
                   lambda m: m["source"].update(kind="canonical-rom"),
                   lambda m: m["source"].update(sha256="0" * 64),
                   lambda m: m["context"].update(runtime_proof=True),
                   lambda m: m["context"].update(production_approval=0),
                   lambda m: m["context"].update(hook_snes=float(0xC0448D)),
                   lambda m: m["target"].update(size=True),
                   lambda m: m["target"].update(sha256="AB" * 32),
                   lambda m: m["sources"][0].update(sha256="0" * 64),
                   lambda m: m["sources"][0].update(provenance="caller-approved")]
        for change in changes:
            manifest = copy.deepcopy(self.manifest)
            change(manifest)
            with self.subTest(change=changes.index(change)), self.assertRaises(contract.PrivateExpandedIntentError):
                contract.validate_manifest(manifest, workspace_root=self.root)

    def test_sections_are_exact_not_a_caller_allocation_catalog(self):
        changes = [lambda m: m["sections"].pop(), lambda m: m["sections"].reverse(),
                   lambda m: m["sections"].append(copy.deepcopy(m["sections"][0])),
                   lambda m: m["sections"][0].update(file_start=0x448E),
                   lambda m: m["sections"][0].update(size=5),
                   lambda m: m["sections"][0].update(replacement_sha256="0" * 64),
                   lambda m: m["sections"][0].update(owner="production"),
                   lambda m: m["sections"][0].update(evidence_level="verified-runtime")]
        for change in changes:
            manifest = copy.deepcopy(self.manifest)
            change(manifest)
            with self.subTest(change=changes.index(change)), self.assertRaises(contract.PrivateExpandedIntentError):
                contract.validate_manifest(manifest, workspace_root=self.root)

    def test_canonical_preimages_are_checked_after_source_identity(self):
        source = bytearray(self.source)
        source[0x282E4] ^= 1
        source[0x100000] -= 1  # Compensate checksum; source mirror/fill stay valid.
        self.assertEqual(sum(source) & 0xFFFF, 0x396E)
        with patch.object(contract, "SCAFFOLD_SHA256", contract.sha(source)):
            manifest = contract._template(contract.sha(self.target), self.output)
            with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "preimage"):
                self.audit(source=bytes(source), manifest=manifest)

    def test_canonical_opcode_operand_and_hook_drift_refuse(self):
        for address in (0x282E4, 0x282E5, 0x448D, 0x4491, 0x4492):
            target = bytearray(self.target)
            target[address] ^= 1
            with self.subTest(address=hex(address)):
                self.reject_target(target, "exact replacement")

    def test_mirror_hook_is_required_not_a_second_arbitrary_hook(self):
        target = bytearray(self.target)
        target[0x40448D:0x404493] = self.source[0x40448D:0x404493]
        self.reject_target(target, "exact replacement.*mirror")

    def test_extra_writes_refuse_even_when_checksum_and_target_hash_match(self):
        for address in (0, 0x28319, 0x400005, 0x4282E4, 0x420000, 0x7FFFFF):
            target = bytearray(self.target)
            if target[address] == 255:
                target[address] -= 1
                target[0x100200] += 1
            else:
                target[address] += 1
                target[0x700001] -= 1
            self.assertEqual(sum(target) & 0xFFFF, 0xDD67)
            with self.subTest(address=hex(address)):
                self.reject_target(target, "undeclared")

    def test_payload_drift_and_wrong_expanded_mapping_refuse(self):
        target = bytearray(self.target)
        target[0x41009C] ^= 1
        self.reject_target(target, "immutable helper")
        target = bytearray(self.target)
        target[0x410000:0x41009D] = b"\xff" * 157
        target[0x010000:0x01009D] = HELPER
        self.reject_target(target, "undeclared")

    def test_header_pair_and_header_fields_cannot_be_reapproved(self):
        for address in (0xFFDC, 0xFFDF, 0x40FFDC, 0x40FFDF, 0xFFD5, 0x40FFD7):
            target = bytearray(self.target)
            target[address] ^= 1
            with self.subTest(address=hex(address)):
                self.reject_target(target)
        # A valid complement with a wrong checksum still cannot pass.
        target = bytearray(self.target)
        for address in (0xFFDC, 0x40FFDC):
            target[address:address + 4] = bytes.fromhex("972268dd")
        self.reject_target(target, "exact replacement")

    def test_source_scaffold_invariants_independent_of_identity(self):
        for address in (0xFFD5, 0x400123, 0x420000):
            source = bytearray(self.source)
            source[address] ^= 1
            with patch.object(contract, "SCAFFOLD_SHA256", contract.sha(source)):
                manifest = contract._template(contract.sha(self.target), self.output)
                with self.subTest(address=hex(address)), self.assertRaisesRegex(contract.PrivateExpandedIntentError, "scaffold invariants"):
                    self.audit(source=bytes(source), manifest=manifest)

    def test_image_size_type_and_unpinned_source_refuse(self):
        for source, target in ((self.source[:-1], self.target),
                               (b"x" + self.source[1:], self.target),
                               (bytearray(self.source), self.target),
                               (self.source, self.target[:-1]),
                               (self.source, bytearray(self.target))):
            with self.assertRaises(contract.PrivateExpandedIntentError):
                self.audit(source=source, target=target)

    def test_path_scope_alias_spellings_and_filename_refuse(self):
        for output in ("private/test_runs/run/other.sfc", "private/test_runs/diagnostic.sfc",
                       "private/test_runs/run/nested/diagnostic.sfc", "private/test_runs/../diagnostic.sfc",
                       "private/test_runs/run./diagnostic.sfc", "private/test_runs/run /diagnostic.sfc",
                       "private/test_runs/NUL/diagnostic.sfc", "private/test_runs/COM1 .x/diagnostic.sfc",
                       "private/test_runs/LPT¹/diagnostic.sfc", "private/test_runs/x\x00/diagnostic.sfc",
                       "C:/private/test_runs/run/diagnostic.sfc", "private\\test_runs\\run\\diagnostic.sfc",
                       "/private/test_runs/run/diagnostic.sfc", "private/test_runs//diagnostic.sfc"):
            with self.subTest(output=repr(output)), self.assertRaises(contract.PrivateExpandedIntentError):
                contract.output_path(output, self.root)

    def test_existing_destination_is_preserved(self):
        path = self.root / self.output
        path.parent.mkdir()
        path.write_bytes(b"existing sentinel, not a ROM")
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "existing destination"):
            contract.output_path(self.output, self.root)
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "existing target"):
            contract.validate_manifest(self.manifest, workspace_root=self.root)
        self.assertEqual(path.read_bytes(), b"existing sentinel, not a ROM")

    def test_existing_matching_synthetic_image_can_be_reaudited_but_not_created(self):
        path = self.root / self.output
        path.parent.mkdir()
        path.write_bytes(self.target)  # Synthetic fixture only, never a game ROM.
        self.assertEqual(self.audit()["status"], "images-valid")
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "existing destination"):
            contract.output_path(self.output, self.root)
        corrupt = bytearray(self.target)
        corrupt[0] ^= 1
        path.write_bytes(corrupt)
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "existing target identity"):
            self.audit()
        self.assertEqual(path.read_bytes(), bytes(corrupt))

    def test_symlink_and_windows_junction_attributes_refuse_inward_aliases(self):
        parent = (self.root / self.output).parent
        parent.mkdir()
        original = Path.lstat
        for mode, attributes in ((stat.S_IFLNK | 0o777, 0), (stat.S_IFDIR | 0o755, 0x400)):
            def observed(path, *args, **kwargs):
                if path == parent:
                    return SimpleNamespace(st_mode=mode, st_file_attributes=attributes)
                return original(path, *args, **kwargs)
            with patch.object(Path, "lstat", observed), self.subTest(mode=mode), self.assertRaisesRegex(contract.PrivateExpandedIntentError, "aliases"):
                contract.output_path(self.output, self.root)

    def test_source_artifact_drift_cannot_be_caller_rehashed(self):
        path = self.root / contract.SOURCE_PINS[0][0]
        path.write_bytes(path.read_bytes() + b"drift")
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "source artifact identity"):
            contract.validate_manifest(self.manifest, workspace_root=self.root)
        manifest = copy.deepcopy(self.manifest)
        manifest["sources"][0]["sha256"] = contract.sha(path.read_bytes())
        manifest["sources"][0]["size"] = path.stat().st_size
        with self.assertRaisesRegex(contract.PrivateExpandedIntentError, "fixed value"):
            contract.validate_manifest(manifest, workspace_root=self.root)


if __name__ == "__main__":
    unittest.main()
