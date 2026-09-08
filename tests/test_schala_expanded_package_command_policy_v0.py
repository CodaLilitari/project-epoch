from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

TOOL_PATH = TOOLS_DIR / "audit_schala_expanded_package_command_policy_v0.py"
REFERENCE_PATH = (
    ROOT / "references" / "schala_expanded_package_command_policy_v0.json"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_expanded_package_command_policy_v0",
    TOOL_PATH,
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def _mask_for_count(count: int) -> int:
    return sum(1 << (15 - index) for index in range(count))


def _fixture(
    stream: bytes,
    *,
    pointer_relatives: tuple[int, ...] = (0,),
    mask0_count: int | None = None,
    mask1_count: int = 0,
    bank: int = 0x40,
    descriptor_root: int = 0x1000,
    stream_start: int = 0x2000,
) -> tuple[bytes, object]:
    if mask0_count is None:
        mask0_count = len(pointer_relatives) - mask1_count
    if mask0_count + mask1_count != len(pointer_relatives):
        raise ValueError("pointer/mask fixture geometry mismatch")
    image = bytearray(TOOL.BANK_SIZE)
    mask0 = _mask_for_count(mask0_count)
    mask1 = _mask_for_count(mask1_count)
    image[descriptor_root : descriptor_root + 4] = (
        mask0.to_bytes(2, "big") + mask1.to_bytes(2, "big")
    )
    cursor = descriptor_root + 4
    for relative in pointer_relatives:
        pointer = stream_start + relative
        image[cursor : cursor + 2] = pointer.to_bytes(2, "little")
        cursor += 2
    image[stream_start : stream_start + len(stream)] = stream
    source = TOOL.adapter.make_package_source(
        selector=0x80,
        bank=bank,
        root_offset=descriptor_root,
        allocation_name="EPOCH_POLICY_TEST_DESCRIPTOR",
        source_kind="synthetic-test",
    )
    layout = TOOL.ExpandedPackageLayout(
        source=source,
        descriptor_span=TOOL.NamedSpan(
            "EPOCH_POLICY_TEST_DESCRIPTOR",
            bank,
            descriptor_root,
            cursor,
        ),
        stream_spans=(
            TOOL.NamedSpan(
                "EPOCH_POLICY_TEST_STREAM",
                bank,
                stream_start,
                stream_start + len(stream),
            ),
        ),
    )
    return bytes(image), layout


class SchalaExpandedPackageCommandPolicyV0Tests(unittest.TestCase):
    def test_reference_contract_is_byte_pinned_and_closed(self) -> None:
        source = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(source), TOOL.REFERENCE_SIZE)
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            TOOL.REFERENCE_SHA256,
        )
        contract = TOOL.load_reference_contract()
        self.assertEqual(contract["schema"], TOOL.REFERENCE_SCHEMA)
        self.assertEqual(contract["version"], 0)
        self.assertEqual(contract["evidence_level"], "verified-static")
        self.assertEqual(contract["limitations"], list(TOOL.LIMITATIONS))
        self.assertEqual(contract["nonclaims"], list(TOOL.NONCLAIMS))
        self.assertEqual(contract["decision"]["policy_id"], TOOL.POLICY_ID)
        self.assertTrue(contract["decision"]["final_for_profile_v0"])
        self.assertFalse(
            contract["decision"]["command_1e_handler_adaptation"]
        )

    def test_dependencies_and_strict_opcode_profile_are_exact(self) -> None:
        grammar_contract, adapter_contract = TOOL._validate_dependency_contracts()
        self.assertEqual(
            grammar_contract["schema"],
            TOOL.grammar.REFERENCE_SCHEMA,
        )
        self.assertEqual(adapter_contract["schema"], TOOL.adapter.SCHEMA)
        allowed = TOOL.allowed_opcode_profile()
        self.assertEqual(len(allowed), TOOL.ALLOWED_OPCODE_COUNT)
        self.assertEqual(
            hashlib.sha256(bytes(sorted(allowed))).hexdigest(),
            TOOL.ALLOWED_OPCODE_VECTOR_SHA256,
        )
        self.assertIn(0x00, allowed)
        self.assertIn(0x25, allowed)
        self.assertIn(0x80, allowed)
        self.assertIn(0xDA, allowed)
        self.assertTrue(
            set(TOOL.BANNED_OBSERVED_OPCODE_REASONS).isdisjoint(allowed)
        )
        identities = TOOL._dependency_interpreter_identities()
        self.assertEqual(
            identities["grammar_auditor_source"]["sha256"],
            TOOL.GRAMMAR_AUDITOR_SOURCE_SHA256,
        )
        self.assertEqual(
            identities["package_bank_adapter_source"]["sha256"],
            TOOL.ADAPTER_AUDITOR_SOURCE_SHA256,
        )
        self.assertEqual(
            identities["grammar_token_shape_profile"],
            {
                "row_count": TOOL.GRAMMAR_TOKEN_SHAPE_PROFILE_ROW_COUNT,
                "sha256": TOOL.GRAMMAR_TOKEN_SHAPE_PROFILE_SHA256,
            },
        )

    def test_unexercised_allowed_opcode_interpreter_drift_fails_closed(
        self,
    ) -> None:
        allowed = TOOL.allowed_opcode_profile()
        candidate = next(
            opcode
            for opcode in sorted(allowed)
            if opcode not in (0x00, 0x02, TOOL.VARIABLE_OPCODE)
        )
        original = TOOL.grammar.token_shape

        def drifted_shape(opcode: int, first_payload: int | None = None):
            shape = original(opcode, first_payload)
            if opcode == candidate:
                return dataclasses.replace(
                    shape,
                    owned_width=shape.owned_width + 1,
                )
            return shape

        with mock.patch.object(
            TOOL.grammar,
            "token_shape",
            side_effect=drifted_shape,
        ):
            with self.assertRaisesRegex(
                TOOL.ExpandedPackageCommandPolicyError,
                "token-shape interpreter profile drifted",
            ):
                TOOL._dependency_interpreter_identities()

    def test_conformance_vector_accepts_raw_operand_1e_and_shared_suffix(
        self,
    ) -> None:
        image, layout = TOOL._build_conformance_vector()
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertTrue(result["expanded_source_1e_absence_proved"])
        self.assertFalse(result["command_1e_cross_bank_subscripts_resolved"])
        self.assertEqual(result["decoded_command_1e_site_count"], 0)
        self.assertEqual(
            result["raw_byte_equal_1e_inside_stream_span_count"],
            1,
        )
        self.assertEqual(result["descriptor_relation_count"], 2)
        self.assertEqual(result["distinct_direct_entrypoint_count"], 2)
        self.assertEqual(result["shared_token_start_count"], 1)
        self.assertEqual(result["unique_token_start_count"], 2)
        self.assertEqual(result["unique_owned_byte_count"], 3)
        self.assertEqual(result["unowned_stream_byte_count"], 0)
        self.assertEqual(result["token_extent_conflict_count"], 0)
        self.assertEqual(result, TOOL.expected_results()["conformance_vector"])

    def test_decoded_command_1e_is_rejected_at_root_middle_and_alternate_mask(
        self,
    ) -> None:
        for label, stream, pointers, mask1_count in (
            ("root", bytes((0x1E, 0x00)), (0,), 0),
            ("middle", bytes((0x02, 0x10, 0x1E, 0x00)), (0,), 0),
            ("alternate-mask", bytes((0x00, 0x1E, 0x00)), (0, 1), 1),
        ):
            with self.subTest(case=label):
                image, layout = _fixture(
                    stream,
                    pointer_relatives=pointers,
                    mask1_count=mask1_count,
                )
                with self.assertRaisesRegex(
                    TOOL.ExpandedPackageCommandPolicyError,
                    "decoded command 1E is forbidden",
                ):
                    TOOL.validate_expanded_package_command_policy(
                        image,
                        layout,
                    )

    def test_parent_return_default_marker_and_unobserved_opcodes_are_rejected(
        self,
    ) -> None:
        cases = (
            (0x1F, "command 1F requires a saved parent"),
            (0x21, "command 21 may restore a saved parent"),
            (0x01, "default-handler sticky terminal"),
            (0xDB, "outside the strict observed authoring profile"),
            (0x04, "outside the strict observed authoring profile"),
        )
        for opcode, message in cases:
            with self.subTest(opcode=f"{opcode:02X}"):
                image, layout = _fixture(bytes((opcode, 0x00, 0x00)))
                with self.assertRaisesRegex(
                    TOOL.ExpandedPackageCommandPolicyError,
                    message,
                ):
                    TOOL.validate_expanded_package_command_policy(
                        image,
                        layout,
                    )

    def test_command_25_requires_a_bounded_fallthrough_to_command_00(self) -> None:
        image, layout = _fixture(bytes((0x25, 0x99, 0x00)))
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertEqual(result["command_25_site_count"], 1)
        self.assertEqual(result["command_00_terminal_count"], 1)

        image, layout = _fixture(bytes((0x25, 0x99)))
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "forced fallthrough left",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

    def test_command_80_nonzero_is_allowed_but_zero_and_crossing_fail(self) -> None:
        image, layout = _fixture(bytes((0x80, 0x01, 0x00)))
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertEqual(result["command_80_site_count"], 1)

        image, layout = _fixture(bytes((0x80, 0x00, 0x00)))
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "low-nibble-zero wrap is forbidden",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

        image, layout = _fixture(bytes((0x80, 0x0F)))
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "command token crosses",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

    def test_command_da_lookahead_must_remain_inside_the_stream_span(self) -> None:
        image, layout = _fixture(bytes((0xDA, 0x00)))
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertEqual(result["command_da_site_count"], 1)

        image, layout = _fixture(bytes((0xDA,)))
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "read-lookahead crosses",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

    def test_shared_suffix_must_begin_at_a_real_token_boundary(self) -> None:
        image, layout = _fixture(
            bytes((0x02, 0x00, 0x00)),
            pointer_relatives=(0, 1),
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "begins inside another token",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

    def test_both_descriptor_masks_are_validated(self) -> None:
        image, layout = _fixture(
            bytes((0x00, 0x00)),
            pointer_relatives=(0, 1),
            mask0_count=1,
            mask1_count=1,
        )
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertTrue(result["both_descriptor_masks_validated"])
        self.assertEqual(result["mask0_relation_count"], 1)
        self.assertEqual(result["mask1_relation_count"], 1)
        self.assertEqual(result["distinct_direct_entrypoint_count"], 2)

    def test_descriptor_stream_overlap_and_unowned_padding_fail(self) -> None:
        image, layout = _fixture(bytes((0x00,)))
        overlapping = dataclasses.replace(
            layout,
            stream_spans=(
                TOOL.NamedSpan(
                    "EPOCH_POLICY_TEST_STREAM",
                    layout.source.bank,
                    layout.descriptor_span.start,
                    0x2001,
                ),
            ),
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "pairwise disjoint",
        ):
            TOOL.validate_expanded_package_command_policy(image, overlapping)

        image, layout = _fixture(bytes((0x00, 0x77)))
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "unowned bytes or unreachable padding",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

    def test_layout_names_banks_descriptor_extent_and_span_use_fail_closed(
        self,
    ) -> None:
        image, layout = _fixture(bytes((0x00,)))
        bad_name = dataclasses.replace(
            layout,
            stream_spans=(
                dataclasses.replace(layout.stream_spans[0], name="bad-name"),
            ),
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "uppercase symbolic name",
        ):
            TOOL.validate_expanded_package_command_policy(image, bad_name)

        bad_bank = dataclasses.replace(
            layout,
            stream_spans=(
                dataclasses.replace(
                    layout.stream_spans[0],
                    bank=layout.source.bank + 1,
                ),
            ),
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "inherit the package bank",
        ):
            TOOL.validate_expanded_package_command_policy(image, bad_bank)

        bad_descriptor = dataclasses.replace(
            layout,
            descriptor_span=dataclasses.replace(
                layout.descriptor_span,
                end_exclusive=layout.descriptor_span.end_exclusive + 1,
            ),
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "exactly own the parsed descriptor",
        ):
            TOOL.validate_expanded_package_command_policy(
                image,
                bad_descriptor,
            )

        unused_span = dataclasses.replace(
            layout,
            stream_spans=(
                *layout.stream_spans,
                TOOL.NamedSpan(
                    "EPOCH_POLICY_UNUSED_STREAM",
                    layout.source.bank,
                    0x3000,
                    0x3001,
                ),
            ),
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "every declared stream span",
        ):
            TOOL.validate_expanded_package_command_policy(image, unused_span)

    def test_bank_end_and_immutable_input_are_enforced(self) -> None:
        image, layout = _fixture(
            bytes((0x25, 0x99)),
            stream_start=0xFFFE,
        )
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "forced fallthrough left",
        ):
            TOOL.validate_expanded_package_command_policy(image, layout)

        image, layout = _fixture(bytes((0x00,)))
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "immutable 64 KiB",
        ):
            TOOL.validate_expanded_package_command_policy(
                bytearray(image),  # type: ignore[arg-type]
                layout,
            )

    def test_content_proof_changes_for_operand_and_bank_identity(self) -> None:
        image, layout = TOOL._build_conformance_vector()
        baseline = TOOL.validate_expanded_package_command_policy(image, layout)
        changed = bytearray(image)
        changed[layout.stream_spans[0].start + 1] = 0x2A
        changed_result = TOOL.validate_expanded_package_command_policy(
            bytes(changed),
            layout,
        )
        self.assertNotEqual(
            baseline["source_content_ledger_sha256"],
            changed_result["source_content_ledger_sha256"],
        )
        self.assertNotEqual(
            baseline["command_exclusion_proof_sha256"],
            changed_result["command_exclusion_proof_sha256"],
        )
        self.assertEqual(
            baseline["token_ledger_sha256"],
            changed_result["token_ledger_sha256"],
        )

        image40, layout40 = _fixture(bytes((0x00,)), bank=0x40)
        image41, layout41 = _fixture(bytes((0x00,)), bank=0x41)
        result40 = TOOL.validate_expanded_package_command_policy(
            image40,
            layout40,
        )
        result41 = TOOL.validate_expanded_package_command_policy(
            image41,
            layout41,
        )
        self.assertNotEqual(
            result40["source_content_ledger_sha256"],
            result41["source_content_ledger_sha256"],
        )
        self.assertNotEqual(
            result40["command_exclusion_proof_sha256"],
            result41["command_exclusion_proof_sha256"],
        )
        self.assertNotEqual(
            result40["token_ledger_sha256"],
            result41["token_ledger_sha256"],
        )

    def test_valid_descriptor_and_source_identity_changes_rebind_proof(
        self,
    ) -> None:
        image_a, layout_a = _fixture(
            bytes((0x00, 0x00)),
            pointer_relatives=(0, 1),
        )
        image_b, layout_b = _fixture(
            bytes((0x00, 0x00)),
            pointer_relatives=(1, 0),
        )
        result_a = TOOL.validate_expanded_package_command_policy(
            image_a,
            layout_a,
        )
        result_b = TOOL.validate_expanded_package_command_policy(
            image_b,
            layout_b,
        )
        self.assertEqual(result_a["distinct_direct_entrypoint_count"], 2)
        self.assertEqual(result_b["distinct_direct_entrypoint_count"], 2)
        self.assertNotEqual(
            result_a["descriptor_entry_ledger_sha256"],
            result_b["descriptor_entry_ledger_sha256"],
        )
        self.assertNotEqual(
            result_a["command_exclusion_proof_sha256"],
            result_b["command_exclusion_proof_sha256"],
        )

        source_b = dataclasses.replace(layout_a.source, selector=0x81)
        selector_layout = dataclasses.replace(layout_a, source=source_b)
        selector_result = TOOL.validate_expanded_package_command_policy(
            image_a,
            selector_layout,
        )
        self.assertEqual(
            result_a["source_content_ledger_sha256"],
            selector_result["source_content_ledger_sha256"],
        )
        self.assertNotEqual(
            result_a["command_exclusion_proof_sha256"],
            selector_result["command_exclusion_proof_sha256"],
        )

    def test_duplicate_pointer_across_masks_keeps_relation_distinction(
        self,
    ) -> None:
        image, layout = _fixture(
            bytes((0x00,)),
            pointer_relatives=(0, 0),
            mask0_count=1,
            mask1_count=1,
        )
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertEqual(result["descriptor_relation_count"], 2)
        self.assertEqual(result["mask0_relation_count"], 1)
        self.assertEqual(result["mask1_relation_count"], 1)
        self.assertEqual(result["distinct_direct_entrypoint_count"], 1)
        self.assertEqual(result["unique_token_start_count"], 1)

    def test_exact_bank_end_preserves_extent_and_native_index_width(self) -> None:
        image, layout = _fixture(
            bytes((0x00,)),
            pointer_relatives=(0, 0),
            mask0_count=1,
            mask1_count=1,
            descriptor_root=0xFFF8,
        )
        result = TOOL.validate_expanded_package_command_policy(image, layout)
        self.assertTrue(result["both_descriptor_masks_validated"])
        self.assertEqual(result["descriptor_relation_count"], 2)
        self.assertEqual(layout.descriptor_span.end_exclusive, 0x10000)
        for flag, physical_end, native_x in ((0, 0xFFFE, 0xFFFE), (1, 0x10000, 0)):
            with self.subTest(a0b3=flag):
                state = TOOL.adapter.simulate_descriptor_install(
                    image, layout.source, a0b3=flag
                )
                self.assertEqual(state.pointer_cursor_final, physical_end)
                self.assertEqual(state.x_final, native_x)
                self.assertTrue(state.indexes_are_16_bit)
                self.assertEqual(state.flag_n_final, 0)
                self.assertEqual(state.flag_z_final, 1)
                self.assertEqual(state.flag_c_final, 1)

    def test_out_of_span_mutation_does_not_rebind_proof(self) -> None:
        image, layout = TOOL._build_conformance_vector()
        baseline = TOOL.validate_expanded_package_command_policy(image, layout)
        changed = bytearray(image)
        changed[0x3000] ^= 0x5A
        result = TOOL.validate_expanded_package_command_policy(
            bytes(changed),
            layout,
        )
        self.assertEqual(
            baseline["source_content_ledger_sha256"],
            result["source_content_ledger_sha256"],
        )
        self.assertEqual(
            baseline["command_exclusion_proof_sha256"],
            result["command_exclusion_proof_sha256"],
        )

    def test_descriptor_and_terminal_mutations_invalidate_the_proof(self) -> None:
        image, layout = TOOL._build_conformance_vector()
        changed_descriptor = bytearray(image)
        changed_descriptor[layout.descriptor_span.start] ^= 0x20
        with self.assertRaises(TOOL.ExpandedPackageCommandPolicyError):
            TOOL.validate_expanded_package_command_policy(
                bytes(changed_descriptor),
                layout,
            )

        changed_terminal = bytearray(image)
        changed_terminal[layout.stream_spans[0].end_exclusive - 1] = 0x02
        with self.assertRaises(TOOL.ExpandedPackageCommandPolicyError):
            TOOL.validate_expanded_package_command_policy(
                bytes(changed_terminal),
                layout,
            )

    def test_existing_cross_bank_subscript_resolver_still_refuses(self) -> None:
        with self.assertRaises(TOOL.adapter.NestedSubscriptUnresolvedError):
            TOOL.adapter.resolve_command_1e_subscript()

    def test_reference_tampering_fails_closed(self) -> None:
        contract = copy.deepcopy(TOOL.load_reference_contract())
        contract["decision"]["command_1e_handler_adaptation"] = True
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "decision contract drifted",
        ):
            TOOL._validate_reference_contract(contract)

        contract = copy.deepcopy(TOOL.load_reference_contract())
        contract["expected_results"]["strict_allowed_opcode_count"] += 1
        with self.assertRaisesRegex(
            TOOL.ExpandedPackageCommandPolicyError,
            "expected results drifted",
        ):
            TOOL._validate_reference_contract(contract)

    def test_report_is_deterministic_metadata_only_and_unbound(self) -> None:
        report = TOOL.build_report()
        self.assertEqual(report, TOOL.build_report())
        self.assertEqual(report["schema"], TOOL.SCHEMA)
        self.assertEqual(report["evidence"]["level"], "verified-static")
        self.assertTrue(report["evidence"]["source_only"])
        self.assertFalse(report["evidence"]["canonical_rom_accessed"])
        self.assertTrue(
            report["gates"][
                "conformance_vector_decoded_command_1e_excluded"
            ]
        )
        self.assertTrue(
            report["gates"][
                "conformance_vector_raw_operand_byte_equal_1e_accepted"
            ]
        )
        self.assertTrue(
            report["gates"][
                "conformance_vector_every_selected_entrypoint_validated"
            ]
        )
        self.assertTrue(
            report["gates"]["dependency_interpreters_exactly_pinned"]
        )
        self.assertFalse(
            report["gates"]["command_1e_handler_adaptation_approved"]
        )
        self.assertFalse(report["gates"]["symbolic_high_package_bound"])
        self.assertFalse(report["gates"]["allocation_or_hook_approved"])
        self.assertFalse(report["gates"]["runtime_performed"])
        self.assertFalse(
            report["results"]["conformance_vector"][
                "raw_stream_or_descriptor_bytes_emitted"
            ]
        )
        self.assertFalse(
            report["reproduction"]["output_file_option_available"]
        )
        self.assertEqual(report["reproduction"]["command"][1], "-B")

        semantic = dict(report)
        identity = semantic.pop("artifact_identity")
        self.assertEqual(
            identity["canonical_json_sha256_excluding_artifact_identity"],
            hashlib.sha256(TOOL._canonical_json_bytes(semantic)).hexdigest(),
        )
        serialized = json.dumps(report, sort_keys=True).lower()
        for forbidden in (
            ".sfc",
            ".smc",
            ".srm",
            "private/",
            "private\\",
            "rom_bytes",
            "output_path",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_cli_is_stdout_only_deterministic_and_has_empty_stderr(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(TOOL_PATH), "--compact"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        self.assertEqual(json.loads(completed.stdout), TOOL.build_report())


if __name__ == "__main__":
    unittest.main()
