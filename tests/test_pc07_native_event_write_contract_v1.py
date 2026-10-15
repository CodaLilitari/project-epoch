"""Focused private-recipe adversaries; no ROM or event payload is emitted.

The exact recipe tests require the ignored owned canonical input and pinned
research dependencies. Filesystem tests write only original synthetic bytes to
a temporary workspace. Tests deliberately bypass aggregate recipe equality in
two cases to exercise the independent section and complete-gap guards.
"""
import copy
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import pc07_native_event_write_contract_v1 as c
import validate_rom_write_intents as guard


class NativeEventContractTests(unittest.TestCase):
    OUTPUT = "private/test_runs/native_event_contract_tests_no_emission/diagnostic.sfc"

    @classmethod
    def setUpClass(cls):
        if not (ROOT / c.CANONICAL_PATH).is_file():
            raise unittest.SkipTest("exact private canonical input is unavailable")
        cls.canonical = c.read_checked(c.CANONICAL_PATH, 0x400000, c.CANONICAL_SHA256)
        cls.source, cls.target, cls.spec = c.recipe(cls.canonical)
        cls.events = c.compile_events(cls.canonical)
        cls.base = c._base(cls.source, cls.spec)
        cls.manifest = c._template(cls.spec, cls.OUTPUT)

    def test_exact_recipe_both_decoders_and_prior_inverse(self):
        report = c.audit_images(self.manifest, self.source, self.target)
        self.assertEqual((report["declared_sections"], report["changed_bytes"]), (37, 5507))
        self.assertTrue(report["both_host_decoders_exact"])
        self.assertEqual(c.sha(self.base), c.prior.TARGET_SHA256)
        self.assertEqual(self.target[c.POINTER_START:c.POINTER_START + 6], bytes.fromhex("000044001044"))
        self.assertEqual([len(row["decoded"]) for row in self.events], [2553, 1917])
        self.assertEqual([len(row["encoded"]) for row in self.events], [2879, 2163])
        self.assertEqual(self.target[0xFFDC:0xFFE0], bytes.fromhex("06daf925"))
        self.assertEqual(self.target[:0x10000], self.target[0x400000:0x410000])
        self.assertFalse(report["native_execution"])
        self.assertFalse((ROOT / self.OUTPUT).parent.exists())

    def test_shared_forwarders_and_production_catalogs_stay_empty(self):
        self.assertEqual(guard.validate_pc07_native_event_manifest(self.manifest)["status"], "metadata-valid")
        report = guard.audit_pc07_native_event_images(self.manifest, self.source, self.target)
        self.assertTrue(report["complete_diff_coverage"])
        self.assertFalse(guard.APPROVED_PRODUCTION_ALLOCATIONS)
        self.assertFalse(guard.APPROVED_PRODUCTION_HOOKS)

    def test_exact_manifest_schema_types_paths_and_no_caller_approval(self):
        mutations = [lambda m: m.update(production_approval=True),
            lambda m: m.update(schema="project-epoch-production"),
            lambda m: m.update(caller_approved=True),
            lambda m: m["source"].update(kind="accepted-first-attack-image"),
            lambda m: m["target"].update(bytes=float(c.SIZE)),
            lambda m: m["events"][1].update(decoded_bytes=1914),
            lambda m: m["sections"][0].update(owner="caller"),
            lambda m: m["sections"].pop(),
            lambda m: m["sections"].append(copy.deepcopy(m["sections"][0]))]
        for mutate in mutations:
            value = copy.deepcopy(self.manifest)
            mutate(value)
            with self.subTest(value=value.get("schema")):
                with self.assertRaises(ValueError):
                    c.validate_manifest(value)
        for output in ["diagnostic.sfc", "private/test_runs/../diagnostic.sfc",
                       "private/test_runs/NUL/diagnostic.sfc", "private/test_runs/x/other.sfc",
                       "private/test_runs/x./diagnostic.sfc", "private\\test_runs\\x\\diagnostic.sfc"]:
            with self.subTest(output=output), self.assertRaises(ValueError):
                c.validate_manifest({**self.manifest, "output": output})

    def test_canonical_preimage_size_and_exact_source_kind_refuse(self):
        changed = bytearray(self.canonical)
        changed[c.POINTER_START] ^= 1
        with self.assertRaises(ValueError):
            c.recipe(bytes(changed))
        with patch.object(c, "CANONICAL_SHA256", c.sha(changed)):
            with self.assertRaisesRegex(ValueError, "six-byte canonical pointer"):
                c._canonical(bytes(changed))
        for source in [self.base, self.source[:-1], bytearray(self.source)]:
            with self.assertRaisesRegex(ValueError, "exact inert scaffold"):
                c.audit_images(self.manifest, source, self.target)

    def test_compiled_payload_and_tail_header_drift_refuse(self):
        for index, offset in [(0, 0), (1, -1), (1, -7)]:
            # The final five-literal addendum header is E0 at encoded[-7].
            events = copy.deepcopy(self.events)
            encoded = bytearray(events[index]["encoded"])
            encoded[offset] ^= 1
            events[index]["encoded"] = bytes(encoded)
            with self.subTest(index=index, offset=offset), self.assertRaisesRegex(ValueError, "preimage/payload"):
                c._target(self.base, events)
        self.assertEqual(self.events[1]["encoded"][-7], 0xE0)

    def test_new_allocation_or_pointer_preimage_drift_refuse(self):
        for at in [c.POINTER_START, c.POINTER_START + 5, 0x440000, 0x441872]:
            base = bytearray(self.base)
            base[at] ^= 1
            with self.subTest(at=at), self.assertRaisesRegex(ValueError, "preimage/payload"):
                c._target(bytes(base), self.events)

    def test_existing_compat_helpers_or_prior_image_cannot_be_substituted(self):
        for at in [0x282E4, 0x1C9A9, 0x410000, 0x410100]:
            target = bytearray(self.target)
            target[at] ^= 1
            with self.subTest(at=at), self.assertRaisesRegex(ValueError, "complete image"):
                c.audit_images(self.manifest, self.source, bytes(target))
        with patch.object(c.prior, "TARGET_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "reconstruction mismatch"):
                c._base(self.source, self.spec)

    def test_mapping_and_fixed_placement_refuse(self):
        for key, value in [("source_cpu", 0x44FFFF), ("file_start", 0x450000),
                           ("encoded_bytes", 0x10001), ("source_cpu", 0x7E0000)]:
            spec = copy.deepcopy(self.spec)
            spec["events"][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                c._validate_spec(spec)
        with patch.object(c.scaffold, "exhirom_snes_to_file", return_value=0x040000):
            with self.assertRaisesRegex(ValueError, "ExHiROM event extent"):
                c._validate_spec(self.spec)

    def test_complete_gap_guard_survives_bypassed_aggregate_comparison(self):
        for at in [0x100000, 0x440B3F, 0x441873, c.SIZE - 1]:
            target = bytearray(self.target)
            target[at] ^= 1
            target = bytes(target)
            # Bypass only expected-whole-image comparison, not the fixed section
            # or gap declarations. This is not a supported caller capability.
            with self.subTest(at=at), patch.object(c, "recipe", return_value=(self.source, target, self.spec)):
                with self.assertRaisesRegex(ValueError, "undeclared image"):
                    c.audit_images(self.manifest, self.source, target)

    def test_section_guard_survives_bypassed_aggregate_comparison(self):
        for at in [c.POINTER_START, 0x440000, 0x441000, 0xFFDC, 0x40FFDC, 0x40448D]:
            target = bytearray(self.target)
            target[at] ^= 1
            target = bytes(target)
            with self.subTest(at=at), patch.object(c, "recipe", return_value=(self.source, target, self.spec)):
                with self.assertRaisesRegex(ValueError, "section preimage/replacement"):
                    c.audit_images(self.manifest, self.source, target)

    def test_mirror_and_sealed_target_identity_refuse(self):
        base = bytearray(self.base)
        base[0x40448D] ^= 1
        with self.assertRaisesRegex(ValueError, "boot mirror"):
            c._target(bytes(base), self.events)
        changed = bytearray(self.target)
        changed[0x440000] ^= 1
        with patch.object(c, "_target", return_value=(bytes(changed), self.spec["target_checksum"])):
            with self.assertRaisesRegex(ValueError, "sealed complete"):
                c.recipe(self.canonical)

    def test_source_and_reference_drift_refuse_without_output(self):
        with patch.object(c, "REFERENCE_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "reference drift"):
                c.reference()
        reader = c.read_checked
        component = self.spec["prior_components"][0]["path"]
        def refuse_component(path, size, digest):
            if str(path) == component:
                raise ValueError("component source drift")
            return reader(path, size, digest)
        with patch.object(c, "read_checked", side_effect=refuse_component):
            with self.assertRaisesRegex(ValueError, "component source drift"):
                c.reference()
        self.assertFalse((ROOT / self.OUTPUT).parent.exists())


class SyntheticFilesystemTests(unittest.TestCase):
    def test_exact_existing_image_read_only_and_creation_exclusivity(self):
        # Original synthetic zeros are not a ROM or copyrighted payload.
        data = bytes(c.SIZE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            relative = "private/test_runs/synthetic/diagnostic.sfc"
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(data)
            spec = {"target_sha256": c.sha(data)}
            with patch.object(c, "ROOT", root), patch.object(c, "_sections", return_value=[]):
                spec["events"] = []
                c._template(spec, relative)
                with self.assertRaises(ValueError):
                    c.prior.field.output_path(relative, root)
                path.write_bytes(b"wrong-existing-content")
                with self.assertRaises(ValueError):
                    c._template(spec, relative)
            self.assertEqual(path.read_bytes(), b"wrong-existing-content")

    def test_input_outside_root_parent_traversal_and_alias_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "original.bin"
            path.write_bytes(b"authored-test-data")
            digest = c.sha(path.read_bytes())
            with patch.object(c, "ROOT", root):
                self.assertEqual(c.read_checked(path, 18, digest), b"authored-test-data")
                for candidate in [root.parent / "elsewhere.bin", root / ".." / "elsewhere.bin"]:
                    with self.assertRaises(ValueError):
                        c.read_checked(candidate, 18, digest)
                with self.assertRaises(ValueError):
                    c.read_checked(path, True, digest)
                original = Path.lstat
                def alias(item, *args, **kwargs):
                    if item == path:
                        return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
                    return original(item, *args, **kwargs)
                with patch.object(Path, "lstat", alias):
                    with self.assertRaisesRegex(ValueError, "aliases"):
                        c.read_checked(path, 18, digest)


if __name__ == "__main__":
    unittest.main()
