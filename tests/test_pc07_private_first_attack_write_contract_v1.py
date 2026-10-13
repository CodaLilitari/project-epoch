"""Focused adversarial first-Attack contract tests: synthetic images, no ROMs.

Reuse the existing synthetic scaffold fixture and original donor machine code.
Literal pins are substituted only inside tests, never exposed as caller inputs.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]
import pc07_private_first_attack_write_contract_v1 as c
import validate_rom_write_intents as guard
from test_pc07_private_expanded_write_contract_v1 import HELPER, COMPAT, _synthetic_source, _checksum

BATTLE = bytes.fromhex(
    "08c907f00728a88a99beb16b28a88a6bbdffaec907d002a9ffc9ff6b0848c980d022e00a00d01d"
    "a502c902d017ad8229c907d010ad0cafc907d009a9209f4c1c0068286b689f4c1c00286b08b98029"
    "c907d002a900480a186301aa680a2818b86b08e00700d00528a9021a6b28bdbeb11a6b08e00000d035"
    "ad92aec901d02ead8cb1c975d027ad8bb1c902d020ad91aec902d019ad8229c907d012ad01afc907d00b"
    "ad0cafc907d00428a9076b28bf9f24cc6b08e00700d00628a902c9ff6b28bdbeb1c9ff6b08e00700d005"
    "28a902aa6b28bdbeb1aa6b")
# Independently spelled destination CPU addresses, whole spans and final bytes.
PATCHES = (
    (0x3DB298, "a88a99beb1", "22000141ea"), (0x01C975, "bdffaec9ff", "22100141ea"),
    (0x01CA29, "bdffaec9ff", "22100141ea"), (0x01CCDA, "bdffaec9ff", "22100141ea"),
    (0x3DAF55, "9f4c1c00", "221c0141"), (0x0CE616, "bf46f8cc", "22310041"),
    (0x0CE980, "b980290a4818798029aa", "224b0141488aeaeaeaea"),
    (0x018050, "bdbeb11a", "22610141"), (0x01BFFF, "bf8325cc", "22430041"),
    (0x01D55E, "bf9f24cc", "22720141"), (0x01D605, "bdbeb1c9ff", "22b30141ea"),
    (0x01D760, "bdbeb1aa", "22c60141"), (0x014A44, "bf3cf6cc", "22550041"),
    (0x0143C4, "bf0040cd", "22670041"), (0x0143F8, "bf0740cd", "22790041"),
    (0x01438B, "bf0e40cd", "228b0041"), (0x01C9A9, "bd3728", "bda72c"),
    (0x01CA56, "bd3e28", "bdae2c"), (0x01CB26, "bd3e28", "bdae2c"),
    (0x01CD08, "bd4d28", "bdbd2c"), (0x01CDEE, "bd4d28", "bdbd2c"),
)


class LiteralTests(unittest.TestCase):
    def test_fixed_private_declarations_and_original_payload(self):
        self.assertEqual(len(c._fixed_spans()), 34)
        self.assertEqual((len(BATTLE), c.sha(BATTLE), sum(BATTLE)), (215,
            "39410b2ccdc09a9ad3667f363d7358bf91f552ee20d145d33c8cfc3c76a9849b", 23694))
        self.assertEqual(c.TARGET_SHA256, "6d420e3daa6761a6ca2b0dd6bfc9119aa15967124f92c5d731a431f76726eefa")
        self.assertEqual(c.TARGET_HEADER_PAIR, bytes.fromhex("91b26e4d"))
        self.assertEqual((c.ALLOCATIONS[1]["file_start"], c.ALLOCATIONS[1]["size"],
                          c.ALLOCATIONS[1]["source"]), (0x410100, 215, "asm/pc07_first_attack_adapters_v1.asm"))
        self.assertEqual(guard.APPROVED_PRODUCTION_ALLOCATIONS, ())
        self.assertEqual(guard.APPROVED_PRODUCTION_HOOKS, ())


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = bytearray(_synthetic_source())
        for start, old, _ in PATCHES:
            source[start:start + len(bytes.fromhex(old))] = bytes.fromhex(old)
        source[0x100000:0x100101] = b"\0" * 257
        delta = (0x396E - sum(source)) & 65535
        for start in range(0x100000, 0x100101):
            source[start] = min(delta, 255)
            delta -= source[start]
        assert delta == 0 and _checksum(source) == 0x396E
        cls.source = bytes(source)
        prior = bytearray(source)
        for start, _, new in COMPAT:
            prior[start:start + 3] = bytes.fromhex(new)
        for start in (0x448D, 0x40448D):
            prior[start:start + 6] = bytes.fromhex("22000041eaea")
        prior[0x410000:0x41009D] = HELPER
        assert _checksum(prior) == 0xDD67
        cls.prior = bytes(prior)
        target = bytearray(prior)
        for start, _, new in PATCHES:
            target[start:start + len(bytes.fromhex(new))] = bytes.fromhex(new)
        target[0x410100:0x4101D7] = BATTLE
        assert _checksum(target) == 0x4D6E
        cls.target = bytes(target)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        pins = []
        for name, _, _ in c.SOURCE_PINS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = ("synthetic original source: " + name).encode()
            path.write_bytes(data)
            pins.append((name, len(data), c.sha(data)))
        self.enterContext(patch.object(c, "SOURCE_PINS", tuple(pins)))
        self.enterContext(patch.object(c, "SOURCE_SHA256", c.sha(self.source)))
        self.enterContext(patch.object(c, "TARGET_SHA256", c.sha(self.target)))
        self.enterContext(patch.object(c, "PRIOR_FIELD_SHA256", c.sha(self.prior)))
        context = copy.deepcopy(c.CONTEXT)
        context["accepted_field_reconstruction_sha256"] = c.sha(self.prior)
        self.enterContext(patch.object(c, "CONTEXT", context))
        self.output = "private/test_runs/first-attack-test/diagnostic.sfc"
        self.manifest = c._template(self.output)

    def audit(self, target=None, source=None, manifest=None):
        return guard.audit_pc07_private_first_attack_images(
            self.manifest if manifest is None else manifest,
            self.source if source is None else source,
            self.target if target is None else target, workspace_root=self.root)

    def reject(self, target, pattern="."):
        # Bypass only the aggregate target identity to exercise the complete
        # section/diff guard; no caller-visible rehash mechanism exists.
        with patch.object(c, "TARGET_SHA256", c.sha(target)):
            with self.assertRaisesRegex(ValueError, pattern):
                self.audit(target=bytes(target), manifest=c._template(self.output))

    def test_valid_complete_image_shared_forwarders_and_readonly_reaudit(self):
        report = self.audit()
        self.assertEqual(report["changed_byte_count"], 481)
        self.assertEqual(report["compatibility_changed_bytes"], 24)
        self.assertEqual(len(report["changed_bytes_by_section"]), 34)
        self.assertTrue(report["accepted_field_reconstruction_verified"])
        self.assertTrue(report["complete_diff_coverage"])
        self.assertFalse(report["runtime_proof"])
        path = self.root / self.output
        path.parent.mkdir()
        self.assertFalse(path.exists())
        path.write_bytes(self.target)  # Synthetic fixture, never a game image.
        self.assertEqual(self.audit(), report)
        with self.assertRaisesRegex(ValueError, "existing destination"):
            c.output_path(self.output, self.root)

    def test_each_hook_operand_opcode_and_tail_is_fixed(self):
        for start, _, new in PATCHES:
            for delta in (0, len(bytes.fromhex(new)) - 1):
                bad = bytearray(self.target)
                bad[start + delta] ^= 1
                with self.subTest(start=hex(start), delta=delta):
                    self.reject(bad, "exact replacement")

    def test_wrong_helper_destination_and_payload_placement(self):
        bad = bytearray(self.target)
        bad[0x1D55F:0x1D562] = bytes.fromhex("720101")
        self.reject(bad, "exact replacement")
        for start in (0x410031, 0x410100, 0x4101D6):
            bad = bytearray(self.target)
            bad[start] ^= 1
            self.reject(bad, "immutable component")
        bad = bytearray(self.target)
        bad[0x410100:0x4101D7] = b"\xff" * 215
        bad[0x420100:0x4201D7] = BATTLE
        self.reject(bad, "immutable component")

    def test_extra_writes_even_with_compensated_checksum(self):
        for start in (0, 0x28319, 0x7FF00, 0x41009D, 0x4101D7, 0x7FFFFF):
            bad = bytearray(self.target)
            if bad[start] == 255:
                bad[start] -= 1
                bad[0x100200] += 1
            else:
                bad[start] += 1
                bad[0x700001] -= 1
            self.assertEqual(sum(bad) & 65535, 0x4D6E)
            self.reject(bad, "undeclared")

    def test_prior_field_mirror_headers_and_source_preimages(self):
        for start in (0x448D, 0x40448D, 0xFFDC, 0x40FFDC, 0xFFD5, 0x282E5):
            bad = bytearray(self.target)
            bad[start] ^= 1
            self.reject(bad)
        bad = bytearray(self.source)
        bad[0x1D55E] ^= 1
        bad[0x100200] += 1  # Keep the scaffold checksum valid to reach preimage checking.
        with patch.object(c, "SOURCE_SHA256", c.sha(bad)):
            with self.assertRaisesRegex(ValueError, "preimage"):
                self.audit(source=bytes(bad), manifest=c._template(self.output))
        with patch.object(c, "PRIOR_FIELD_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "field reconstruction"):
                self.audit()

    def test_manifest_cannot_approve_new_namespace_span_or_payload(self):
        edits = [lambda m: m.update(build_mode="production"), lambda m: m.update(catalog=[]),
                 lambda m: m["target"].update(sha256="0" * 64),
                 lambda m: m["sections"].pop(), lambda m: m["sections"][0].update(size=True),
                 lambda m: m["allocations"][1].update(file_start=0x420100),
                 lambda m: m["allocations"][1].update(source="caller.asm"),
                 lambda m: m["hooks"][0].update(helper_entry=0x410101),
                 lambda m: m["context"].update(runtime_proof=True),
                 lambda m: m["context"]["battle_entry_abi"].update(DBR=0)]
        for edit in edits:
            manifest = copy.deepcopy(self.manifest)
            edit(manifest)
            with self.assertRaises(ValueError):
                guard.validate_pc07_private_first_attack_manifest(manifest, workspace_root=self.root)

    def test_source_drift_type_size_and_mapping_reject(self):
        for source, target in ((bytearray(self.source), self.target), (self.source[:-1], self.target),
                               (self.source, bytearray(self.target)), (self.source, self.target[:-1])):
            with self.assertRaises(ValueError):
                self.audit(source=source, target=target)
        original = c.scaffold.exhirom_snes_to_file
        with patch.object(c.scaffold, "exhirom_snes_to_file", lambda bus: 0x010100 if bus == 0x410100 else original(bus)):
            with self.assertRaisesRegex(ValueError, "mapping"):
                self.audit()
        path = self.root / c.SOURCE_PINS[0][0]
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "source identity drift"):
            self.audit()

    def test_output_paths_existing_mismatch_and_alias_reject(self):
        for output in ("private/test_runs/x/other.sfc", "private/test_runs/../diagnostic.sfc",
                       "private/test_runs/NUL/diagnostic.sfc", "private/test_runs/x./diagnostic.sfc"):
            manifest = copy.deepcopy(self.manifest)
            manifest["output"] = output
            with self.assertRaises(ValueError):
                c.validate_manifest(manifest, workspace_root=self.root)
        path = self.root / self.output
        path.parent.mkdir()
        path.write_bytes(b"private sentinel")
        with self.assertRaisesRegex(ValueError, "existing target"):
            self.audit()
        self.assertEqual(path.read_bytes(), b"private sentinel")
        original = Path.lstat
        def alias(p, *args, **kwargs):
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400) if p == path.parent else original(p, *args, **kwargs)
        with patch.object(Path, "lstat", alias):
            with self.assertRaisesRegex(ValueError, "aliases"):
                self.audit()

    def test_builder_calls_both_shared_audits_and_never_emits_during_plan(self):
        location = ROOT / "private/research/pc07_first_attack_builder_20261013/build_first_attack_v1.py"
        spec = importlib.util.spec_from_file_location("first_attack_builder_test", location)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with patch.object(builder, "ROOT", self.root), patch.object(builder, "bundle", return_value={"sha256": "synthetic"}), \
             patch.object(builder.scaffold, "expand_exhirom_scaffold", return_value=self.source), \
             patch.object(builder.scaffold, "validate_exhirom_scaffold", return_value={}), \
             patch.object(guard, "validate_pc07_private_first_attack_manifest", wraps=lambda m: c.validate_manifest(m, workspace_root=self.root)) as intent, \
             patch.object(guard, "audit_pc07_private_first_attack_images", wraps=lambda m, s, t: c.audit_images(m, s, t, workspace_root=self.root)) as audit, \
             patch.object(builder.contract, "build_manifest", wraps=lambda s, t, o: c._template(o)), \
             patch.object(builder.assembler, "exclusive", side_effect=AssertionError("no output allowed")):
            image, report = builder.build_image(b"original synthetic fixture", HELPER, BATTLE, self.root / self.output)
            self.assertEqual(image, self.target)
            self.assertFalse(report["emitted"])
            intent.assert_called_once()
            audit.assert_called_once()
            self.assertFalse((self.root / self.output).exists())

    def test_emit_audit_refusal_precedes_directory_assembly_and_output(self):
        location = ROOT / "private/research/pc07_first_attack_builder_20261013/build_first_attack_v1.py"
        spec = importlib.util.spec_from_file_location("first_attack_emit_test", location)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        destination = self.root / self.output
        sentinel = self.root / "untouched-sentinel.txt"
        sentinel.write_bytes(b"preserve this existing file")
        with patch.object(builder, "ROOT", self.root), patch.object(builder, "bundle", return_value={"sha256": "reviewed"}), \
             patch.object(builder, "components", return_value=(HELPER, BATTLE)), \
             patch.object(builder.contract, "output_path", side_effect=lambda value: c.field.output_path(value, self.root)), \
             patch.object(builder.scaffold, "expand_exhirom_scaffold", return_value=self.source), \
             patch.object(builder.scaffold, "validate_exhirom_scaffold", return_value={}), \
             patch.object(builder.contract, "build_manifest", side_effect=lambda s, t, o: c._template(o)), \
             patch.object(guard, "validate_pc07_private_first_attack_manifest", side_effect=ValueError("shared intent refusal")) as intent, \
             patch.object(guard, "audit_pc07_private_first_attack_images") as audit, \
             patch.object(builder.assembler, "verify_asar") as verify, \
             patch.object(builder.assembler, "assemble_raw") as assemble, \
             patch.object(builder.assembler, "exclusive") as exclusive:
            with self.assertRaisesRegex(ValueError, "reviewed builder bundle"):
                builder.emit(b"synthetic canonical stub", destination, "unreviewed")
            intent.assert_not_called()
            with self.assertRaisesRegex(ValueError, "shared intent refusal"):
                builder.emit(b"synthetic canonical stub", destination, "reviewed")
            intent.assert_called_once()
            for operation in (audit, verify, assemble, exclusive):
                operation.assert_not_called()
            self.assertFalse(destination.parent.exists())
            self.assertEqual(sentinel.read_bytes(), b"preserve this existing file")


if __name__ == "__main__":
    unittest.main()
