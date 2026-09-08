from __future__ import annotations

import base64
import contextlib
import copy
import dataclasses
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import audit_schala_symbolic_high_package_v0 as TOOL

TOOL_PATH = TOOLS / "audit_schala_symbolic_high_package_v0.py"


class SymbolicHighPackageSourceTests(unittest.TestCase):
    def test_closed_byte_pinned_reference(self) -> None:
        raw = TOOL.REFERENCE_PATH.read_bytes()
        self.assertEqual(len(raw), TOOL.REFERENCE_SIZE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), TOOL.REFERENCE_SHA256)
        contract = TOOL.load_reference_contract()
        self.assertEqual(contract["schema"], TOOL.REFERENCE_SCHEMA)
        self.assertEqual(contract["gate"], "BA-SYMBOLIC-HIGH-PACKAGE")
        self.assertEqual(contract["evidence_level"], "verified-static")
        self.assertEqual(contract["donor_contract"]["row_file_offset"], "0D45AD")
        self.assertEqual(contract["donor_contract"]["changed_byte_offsets"], [0])
        self.assertFalse(contract["scope"]["production_installable"])

    def test_reference_append_same_length_mutation_and_missing_file_fail(self) -> None:
        raw = TOOL.REFERENCE_PATH.read_bytes()
        for changed in (raw + b" ", raw.replace(b"01", b"02", 1)):
            with self.subTest(size=len(changed)):
                ref = mock.Mock()
                ref.read_bytes.return_value = changed
                with mock.patch.object(TOOL, "REFERENCE_PATH", ref):
                    with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "reference identity"):
                        TOOL.load_reference_contract()
        ref = mock.Mock()
        ref.read_bytes.side_effect = FileNotFoundError("missing reference")
        with mock.patch.object(TOOL, "REFERENCE_PATH", ref):
            with self.assertRaises(FileNotFoundError):
                TOOL.load_reference_contract()

    def test_reference_extra_fields_changed_limits_and_bool_integer_confusion_fail(self) -> None:
        original = TOOL.load_reference_contract()
        for mode in ("extra", "donor", "boolean", "scope", "nonclaims"):
            changed = copy.deepcopy(original)
            if mode == "extra":
                changed["unreviewed"] = 1
            elif mode == "donor":
                changed["donor_contract"]["physical_action_config_row"] = "02"
            elif mode == "boolean":
                changed["expected_symbolic_source"]["repeated_pointer_alias_count"] = True
            elif mode == "scope":
                changed["scope"]["production_installable"] = True
            else:
                changed["nonclaims"] = []
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "reference content"):
                    TOOL._validate_reference_contract(changed)

    def test_exact_dependency_source_and_reference_identities(self) -> None:
        deps = TOOL.dependency_identities()
        self.assertEqual(deps["command_policy_source"]["sha256"], TOOL.POLICY_SOURCE_SHA256)
        self.assertEqual(deps["command_policy_reference"]["sha256"], TOOL.POLICY_REFERENCE_SHA256)
        interpreter = deps["transitive_closed_dependencies"]["interpreter_identities"]
        self.assertEqual(interpreter["grammar_token_shape_profile"]["row_count"], 511)
        for value in interpreter.values():
            self.assertEqual(len(value["sha256"]), 64)

    def test_policy_source_drift_and_import_path_fail_closed(self) -> None:
        with mock.patch.object(TOOL, "POLICY_SOURCE_SHA256", "0" * 64):
            with self.assertRaisesRegex(TOOL.policy.ExpandedPackageCommandPolicyError, "source identity"):
                TOOL.dependency_identities()
        with mock.patch.object(TOOL.policy, "__file__", str(ROOT / "unexpected.py")):
            with self.assertRaisesRegex(TOOL.policy.ExpandedPackageCommandPolicyError, "unexpected path"):
                TOOL.dependency_identities()

    def test_policy_reference_dependency_drift_fails_closed(self) -> None:
        with mock.patch.object(TOOL.policy, "REFERENCE_SHA256", "0" * 64):
            with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "dependency pin"):
                TOOL.dependency_identities()

    def test_unexecuted_grammar_opcode_interpreter_drift_fails_closed(self) -> None:
        original = TOOL.policy.grammar.token_shape

        def changed(opcode, first_payload=None):
            shape = original(opcode, first_payload)
            if opcode == 0x02:
                return dataclasses.replace(shape, owned_width=shape.owned_width + 1)
            return shape

        with mock.patch.object(TOOL.policy.grammar, "token_shape", side_effect=changed):
            with self.assertRaisesRegex(TOOL.policy.ExpandedPackageCommandPolicyError, "interpreter profile drifted"):
                TOOL.load_reference_contract()

    def test_original_exact_dual_mask_alias_and_terminal_stream(self) -> None:
        image, layout = TOOL.build_symbolic_source()
        self.assertIs(type(image), bytes)
        self.assertEqual(len(image), 65536)
        self.assertEqual(image[0x2000:0x2008], b"\x80\x00\x80\x00\x00\x30\x00\x30")
        self.assertEqual(image[0x3000:0x3001], b"\x00")
        self.assertEqual(layout.source.selector, 0x80)
        self.assertEqual(layout.source.bank, 0x42)
        self.assertEqual(layout.source.source_kind, "synthetic-test")
        self.assertEqual(layout.descriptor_span.name, "EPOCH_PKG80_SYMBOLIC_DESCRIPTOR_V0")
        self.assertEqual(layout.stream_spans[0].name, "EPOCH_PKG80_SYMBOLIC_STREAM_V0")
        result = TOOL.validate_symbolic_source(image, layout)
        self.assertEqual(result["descriptor_pointer_occurrence_count"], 2)
        self.assertEqual(result["distinct_direct_entrypoint_count"], 1)
        self.assertEqual(result["repeated_pointer_alias_count"], 1)
        self.assertEqual(result["policy_proof"]["source_content_size"], 9)
        self.assertEqual(result["policy_proof"]["mask0_relation_count"], 1)
        self.assertEqual(result["policy_proof"]["mask1_relation_count"], 1)
        # Duplicate relations select one independently decoded entry, not two traces.
        self.assertEqual(result["policy_proof"]["total_entrypoint_traversal_token_count"], 1)
        self.assertEqual(result["policy_proof"]["shared_token_start_count"], 0)

    def test_every_layout_identity_and_exact_span_is_pinned(self) -> None:
        image, layout = TOOL.build_symbolic_source()
        variants = [
            dataclasses.replace(layout, source=dataclasses.replace(layout.source, selector=0x81)),
            dataclasses.replace(layout, source=dataclasses.replace(layout.source, bank=0x43)),
            dataclasses.replace(layout, source=dataclasses.replace(layout.source, root_offset=0x2001)),
            dataclasses.replace(layout, source=dataclasses.replace(layout.source, source_kind="canonical")),
            dataclasses.replace(layout, descriptor_span=dataclasses.replace(layout.descriptor_span, name="OTHER_DESCRIPTOR")),
            dataclasses.replace(layout, descriptor_span=dataclasses.replace(layout.descriptor_span, end_exclusive=0x2009)),
            dataclasses.replace(layout, stream_spans=()),
            dataclasses.replace(layout, stream_spans=(dataclasses.replace(layout.stream_spans[0], start=0x2FFF),)),
            dataclasses.replace(layout, stream_spans=(dataclasses.replace(layout.stream_spans[0], end_exclusive=0x3002),)),
        ]
        for changed in variants:
            with self.subTest(layout=changed):
                with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "named symbolic layout"):
                    TOOL.validate_symbolic_source(image, changed)

    def test_mutable_truncated_descriptor_stream_and_unnamed_content_refused(self) -> None:
        image, layout = TOOL.build_symbolic_source()
        variants = [bytearray(image), image[:-1]]
        for offset in (0x2000, 0x2002, 0x2004, 0x2006, 0x3000, 0, 0xFFFF):
            changed = bytearray(image)
            changed[offset] ^= 1
            variants.append(bytes(changed))
        for changed in variants:
            with self.subTest(type=type(changed), size=len(changed)):
                with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "immutable symbolic bank"):
                    TOOL.validate_symbolic_source(changed, layout)
        self.assertEqual(image, TOOL.build_symbolic_source()[0])

    def test_all_flag_inputs_preserve_both_branch_transport(self) -> None:
        image, layout = TOOL.build_symbolic_source()
        result = TOOL.validate_branch_transport(image, layout.source)
        self.assertEqual(result["a0b3_flag_byte_inputs_checked"], 256)
        self.assertEqual(result["mask0_input_count"], 1)
        self.assertEqual(result["mask1_input_count"], 255)
        self.assertFalse(result["runtime_write_performed"])
        for flag, branch, cursor in ((0, 0, 0x2006), (1, 1, 0x2008), (255, 1, 0x2008)):
            state = TOOL.adapter.simulate_descriptor_install(image, layout.source, a0b3=flag)
            self.assertEqual(state.selected_branch, branch)
            self.assertEqual(state.x_final, cursor)
            self.assertEqual(state.a0b3_final, 0)
            self.assertEqual(len(state.publications), 1)
            self.assertEqual(state.publications[0].bank_word, 0x42)
            self.assertEqual(state.publications[0].script_offset, 0x3000)

    def test_host_transport_drift_outside_first_two_flag_inputs_refused(self) -> None:
        image, layout = TOOL.build_symbolic_source()
        original = TOOL.adapter.simulate_descriptor_install

        def changed(*args, **kwargs):
            state = original(*args, **kwargs)
            return dataclasses.replace(state, stack_delta=2) if kwargs["a0b3"] == 255 else state

        with mock.patch.object(TOOL.adapter, "simulate_descriptor_install", side_effect=changed):
            with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "branch transport"):
                TOOL.validate_branch_transport(image, layout.source)

    def test_rom_size_hash_and_mutability_fail_closed_before_donor_access(self) -> None:
        for rom in (b"", bytes(4194304), bytearray(4194304)):
            with self.subTest(type=type(rom), size=len(rom)):
                with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "pinned immutable"):
                    TOOL.reconstruct_config_pair(rom)
                with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "pinned immutable"):
                    TOOL.build_report(rom)

    def test_cli_has_no_output_patch_or_install_option(self) -> None:
        for option in ("--output", "--patch", "--install"):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    TOOL.build_parser().parse_args([option, "forbidden"])
            self.assertEqual(raised.exception.code, 2)

    def test_cli_failure_produces_no_stdout(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = TOOL.main(["--rom", str(ROOT / "private/nonexistent-symbolic-proof-input.sfc")])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("symbolic high package audit failed", err.getvalue())


class SymbolicHighPackageCanonicalInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TOOL.DEFAULT_ROM_PATH.is_file():
            raise unittest.SkipTest("private canonical ROM is unavailable")
        cls.rom = TOOL.DEFAULT_ROM_PATH.read_bytes()
        TOOL._require_canonical_rom(cls.rom)
        cls.donor, cls.candidate = TOOL.reconstruct_config_pair(cls.rom)
        cls.canonical = TOOL.adapter.build_canonical_sources(cls.rom)
        cls.image, cls.layout = TOOL.build_symbolic_source()

    def test_real_config_is_only_byte_zero_substitution(self) -> None:
        before = hashlib.sha256(self.rom).hexdigest()
        result = TOOL.validate_config_pair(self.donor, self.candidate)
        self.assertEqual(self.donor, self.rom[0xD45AD:0xD45B4])
        self.assertEqual(self.candidate[0], 0x80)
        self.assertNotEqual(self.donor[0], 0x80)
        self.assertEqual(self.donor[1:], self.candidate[1:])
        self.assertEqual(result["changed_byte_offsets"], [0])
        self.assertTrue(all(result["preserved_byte_equalities"]))
        self.assertEqual(hashlib.sha256(self.rom).hexdigest(), before)

    def test_each_nonprimary_config_mutation_refused(self) -> None:
        for offset in range(1, 7):
            changed = bytearray(self.candidate)
            changed[offset] ^= 1
            with self.subTest(offset=offset):
                with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "preserved config bytes"):
                    TOOL.validate_config_pair(self.donor, bytes(changed))

    def test_wrong_selector_donor_size_mutability_and_self_consistent_wrong_donor_refused(self) -> None:
        variants = [
            (self.donor, bytes((0x81,)) + self.candidate[1:]),
            (self.donor[:-1], self.candidate),
            (self.donor, self.candidate + b"\x00"),
            (bytearray(self.donor), self.candidate),
            (self.donor, bytearray(self.candidate)),
        ]
        other = self.rom[0xD45B4:0xD45BB]
        variants.append((other, bytes((0x80,)) + other[1:]))
        for donor, candidate in variants:
            with self.subTest(donor_type=type(donor), candidate_size=len(candidate)):
                with self.assertRaises(TOOL.SymbolicHighPackageError):
                    TOOL.validate_config_pair(donor, candidate)

    def test_actual_rom_single_byte_drift_refused(self) -> None:
        changed = bytearray(self.rom)
        changed[0xD45AD] ^= 1
        with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "pinned immutable"):
            TOOL.build_report(bytes(changed))

    def test_all_default_high_selectors_stay_unbound_and_vanilla_matches(self) -> None:
        result = TOOL.validate_namespace(self.canonical, self.layout.source)
        self.assertEqual(result["canonical_selector_equivalence_count"], 128)
        self.assertEqual(result["default_high_selector_refusal_count"], 16)
        self.assertEqual(result["production_high_selector_bound_count"], 0)
        self.assertEqual(result["explicit_synthetic_mapping_selectors"], ["80"])
        self.assertEqual(result["remaining_explicit_high_selector_refusal_count"], 15)
        self.assertFalse(result["schala_action_mapping_bound"])
        self.assertTrue(result["command_1e_refusal_preserved"])

    def test_default_high_binding_drift_refused(self) -> None:
        original = TOOL.adapter.resolve_package_source

        def changed(selector, canonical_sources, extended_bindings=None):
            if selector == 0x80 and extended_bindings is None:
                return self.layout.source
            return original(selector, canonical_sources, extended_bindings)

        with mock.patch.object(TOOL.adapter, "resolve_package_source", side_effect=changed):
            with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "default high package selector"):
                TOOL.validate_namespace(self.canonical, self.layout.source)

    def test_namespace_refuses_nonempty_default_registry_and_nested_handler_drift(self) -> None:
        original = TOOL.adapter.validate_extended_bindings

        def changed(bindings):
            return {0x80: self.layout.source} if bindings is None else original(bindings)

        with mock.patch.object(TOOL.adapter, "validate_extended_bindings", side_effect=changed):
            with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "registry is not empty"):
                TOOL.validate_namespace(self.canonical, self.layout.source)
        with mock.patch.object(TOOL.adapter, "resolve_command_1e_subscript", return_value=None):
            with self.assertRaisesRegex(TOOL.SymbolicHighPackageError, "command 1E refusal"):
                TOOL.validate_namespace(self.canonical, self.layout.source)

    def test_report_binds_implementation_reference_inputs_and_payload_free_results(self) -> None:
        report = TOOL.build_report(self.rom)
        self.assertEqual(report["status"], TOOL.STATUS)
        self.assertEqual(report["evidence_level"], "verified-static")
        self.assertEqual(report["reproduction"]["auditor_source"]["sha256"], hashlib.sha256(TOOL_PATH.read_bytes()).hexdigest())
        self.assertEqual(report["reproduction"]["reference_contract"]["sha256"], TOOL.REFERENCE_SHA256)
        self.assertEqual(len(report["results"]["canonical_spans_verified"]), 7)
        identity = report.pop("artifact_identity")
        self.assertEqual(identity["canonical_json_sha256_excluding_artifact_identity"], TOOL._metadata_sha256(report))
        emitted = json.dumps(report)
        for payload in (self.donor, self.candidate):
            self.assertNotIn(payload.hex(), emitted)
            self.assertNotIn(base64.b64encode(payload).decode("ascii"), emitted)
            self.assertNotIn(json.dumps(list(payload)), emitted)
        for field in ("action_mapping_bound", "allocation_or_hook_approved", "runtime_performed", "rom_save_state_trace_mutation_performed", "canonical_payload_emitted", "patch_rom_or_output_file_emitted"):
            self.assertIs(report["gates"][field], False)

    def test_compact_stdout_reproduces_exactly_and_rom_disk_remains_immutable(self) -> None:
        before = TOOL.DEFAULT_ROM_PATH.stat()
        before_hash = hashlib.sha256(TOOL.DEFAULT_ROM_PATH.read_bytes()).hexdigest()
        command = [sys.executable, "-B", str(TOOL_PATH), "--rom", str(TOOL.DEFAULT_ROM_PATH), "--compact"]
        first = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
        second = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)
        for result in (first, second):
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(result.stderr, b"")
            self.assertEqual(json.loads(result.stdout)["status"], TOOL.STATUS)
        self.assertEqual(first.stdout, second.stdout)
        after = TOOL.DEFAULT_ROM_PATH.stat()
        self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
        self.assertEqual(hashlib.sha256(TOOL.DEFAULT_ROM_PATH.read_bytes()).hexdigest(), before_hash)


if __name__ == "__main__":
    unittest.main()
