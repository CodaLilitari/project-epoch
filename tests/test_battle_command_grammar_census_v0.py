from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

AUDIT_PATH = TOOLS_DIR / "audit_battle_command_grammar_census_v0.py"
REFERENCE_PATH = (
    ROOT / "references" / "battle_command_grammar_census_v0.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_battle_command_grammar_census_v0",
    AUDIT_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def _token(
    *,
    offset: int,
    opcode: int = 0x02,
    width: int = 2,
    flow: str = "eventual-sequential-fallthrough",
) -> object:
    return AUDIT.DecodedToken(
        bank=0xCE,
        offset=offset,
        opcode=opcode,
        owned_width=width,
        width_rule="synthetic-test",
        flow=flow,
        handler_family="H000",
        known_lookahead_offsets=(),
    )


class BattleCommandGrammarCensusV0Tests(unittest.TestCase):
    def test_reference_contract_is_byte_pinned_and_closed(self) -> None:
        source = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(source), AUDIT.REFERENCE_SIZE)
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            AUDIT.REFERENCE_SHA256,
        )
        contract = AUDIT.load_reference_contract()
        self.assertEqual(contract["schema"], AUDIT.REFERENCE_SCHEMA)
        self.assertEqual(contract["version"], 1)
        self.assertEqual(contract["evidence_level"], "verified-static")
        self.assertEqual(
            set(contract["expected_results"]),
            {"grammar", "direct_roots", "stream_census"},
        )
        self.assertEqual(contract["limitations"], list(AUDIT.LIMITATIONS))
        self.assertEqual(contract["nonclaims"], list(AUDIT.NONCLAIMS))

    def test_machine_witnesses_and_width_vector_have_exact_geometry(self) -> None:
        self.assertEqual(len(AUDIT.REFERENCE_SHA256), 64)
        self.assertEqual(len(AUDIT.MACHINE_SPANS), 11)
        for span in AUDIT.MACHINE_SPANS:
            with self.subTest(span=span.name):
                self.assertLess(span.start, span.end_exclusive)
                self.assertEqual(len(span.expected_sha256), 64)
        self.assertEqual(
            len(AUDIT.FIXED_TOKEN_WIDTHS),
            AUDIT.DISPATCHED_OPCODE_END_EXCLUSIVE,
        )
        self.assertIsNone(AUDIT.FIXED_TOKEN_WIDTHS[0x80])
        self.assertEqual(
            sum(width is None for width in AUDIT.FIXED_TOKEN_WIDTHS),
            1,
        )
        expected_corrections = {
            0x15: 3,
            0x18: 2,
            0x3B: 2,
            0x3C: 2,
            0x9B: 2,
            0xC5: 2,
            0xDA: 1,
        }
        self.assertEqual(
            {
                int(row["opcode"], 16): row["verified_owned_width"]
                for row in AUDIT.CORRECTION_WITNESSES
            },
            expected_corrections,
        )
        for opcode, width in expected_corrections.items():
            self.assertEqual(AUDIT.FIXED_TOKEN_WIDTHS[opcode], width)

    def test_variable_and_lookahead_token_shapes_are_lossless(self) -> None:
        zero = AUDIT.token_shape(0x80, 0x00)
        self.assertEqual(zero.owned_width, 1)
        self.assertEqual(zero.known_lookahead_offsets, tuple(range(1, 257)))
        one = AUDIT.token_shape(0x80, 0xF1)
        self.assertEqual(one.owned_width, 2)
        self.assertEqual(one.known_lookahead_offsets, ())
        fifteen = AUDIT.token_shape(0x80, 0x0F)
        self.assertEqual(fifteen.owned_width, 16)

        lookahead = AUDIT.token_shape(0xDA)
        self.assertEqual(lookahead.owned_width, 1)
        self.assertEqual(lookahead.known_lookahead_offsets, (1,))
        marker = AUDIT.token_shape(0xDB)
        self.assertEqual(marker.owned_width, 1)
        self.assertEqual(marker.width_rule, "undispatched-marker-byte")

        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "requires its first payload byte",
        ):
            AUDIT.token_shape(0x80)
        for value in (-1, 0x100, "80"):
            with self.subTest(value=value), self.assertRaises(
                AUDIT.BattleCommandGrammarAuditError
            ):
                AUDIT.token_shape(value)  # type: ignore[arg-type]

    def test_flow_classes_keep_calls_returns_conditionals_and_markers_apart(
        self,
    ) -> None:
        handlers = list(range(AUDIT.DISPATCHED_OPCODE_END_EXCLUSIVE))
        handlers[0x10] = AUDIT.DEFAULT_HANDLER_OFFSET
        self.assertEqual(
            AUDIT.flow_for_opcode(0x00, handlers),
            "stop-current-script",
        )
        self.assertEqual(
            AUDIT.flow_for_opcode(0x10, handlers),
            "default-handler-sticky",
        )
        self.assertEqual(
            AUDIT.flow_for_opcode(0x1E, handlers),
            "fixed-ce-subscript-call-with-parent-continuation",
        )
        self.assertEqual(
            AUDIT.flow_for_opcode(0x1F, handlers),
            "restore-saved-parent",
        )
        self.assertEqual(
            AUDIT.flow_for_opcode(0x21, handlers),
            "conditional-fallthrough-or-restore-saved-parent",
        )
        self.assertEqual(
            AUDIT.flow_for_opcode(0x25, handlers),
            "conditional-fallthrough-or-stop",
        )
        self.assertEqual(
            AUDIT.flow_for_opcode(0xDB, handlers),
            "undispatched-sticky-marker",
        )

    def test_token_registration_accepts_aliases_but_rejects_conflicts(self) -> None:
        tokens: dict[tuple[int, int], object] = {}
        coverage: dict[tuple[int, int], tuple[int, int]] = {}
        first = _token(offset=0x2000)
        AUDIT._register_token(first, tokens=tokens, coverage=coverage)
        AUDIT._register_token(first, tokens=tokens, coverage=coverage)
        self.assertEqual(len(tokens), 1)
        self.assertEqual(len(coverage), 2)

        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "decoded inconsistently",
        ):
            AUDIT._register_token(
                _token(offset=0x2000, opcode=0x03),
                tokens=tokens,
                coverage=coverage,
            )
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "extents overlap",
        ):
            AUDIT._register_token(
                _token(offset=0x2001),
                tokens=tokens,
                coverage=coverage,
            )

    def test_closed_reference_captures_the_complete_static_census(self) -> None:
        result = AUDIT.load_reference_contract()["expected_results"]
        grammar = result["grammar"]
        self.assertEqual(grammar["opcode_domain_count"], 256)
        self.assertEqual(grammar["dispatch_table_opcode_count"], 219)
        self.assertEqual(grammar["distinct_handler_family_count"], 115)
        self.assertEqual(grammar["shared_handler_family_count"], 13)
        self.assertEqual(
            grammar["handler_family_with_multiple_owned_width_count"],
            0,
        )
        self.assertEqual(grammar["default_handler_opcode_count"], 70)
        self.assertEqual(grammar["undispatched_marker_opcode_count"], 37)
        self.assertEqual(grammar["fixed_width_opcode_count"], 255)
        self.assertEqual(grammar["variable_width_opcode_count"], 1)
        self.assertEqual(
            grammar["width_derivation_mode"],
            "reviewer-encoded canonical-handler static analysis",
        )
        self.assertEqual(
            grammar["community_parser_role"],
            "comparison lead only; not authority",
        )
        self.assertEqual(
            grammar["fixed_owned_width_counts"],
            {"1": 168, "2": 56, "3": 20, "4": 9, "5": 2},
        )

        roots = result["direct_roots"]
        self.assertEqual(roots["declared_direct_root_count"], 2_146)
        self.assertEqual(
            roots["declared_direct_root_count_by_bank"],
            {"CD": 1_211, "CE": 935},
        )
        self.assertEqual(roots["config_selected_direct_root_count"], 2_173)
        self.assertEqual(
            roots["config_selected_direct_root_count_by_bank"],
            {"CD": 1_211, "CE": 962},
        )
        self.assertEqual(roots["config_supplement_only_root_count"], 27)
        self.assertTrue(roots["declared_is_strict_subset_of_config_selected"])
        self.assertEqual(roots["selected_descriptor_span_count"], 455)

        stream = result["stream_census"]
        expected_counts = {
            "direct_entrypoint_count": 2_173,
            "nested_entrypoint_count": 59,
            "closure_entrypoint_count": 2_232,
            "unique_token_start_count": 31_655,
            "unique_owned_byte_count": 58_960,
            "total_entrypoint_traversal_token_count": 31_659,
            "minimum_tokens_per_entrypoint": 1,
            "maximum_tokens_per_entrypoint": 147,
            "distinct_observed_opcode_count": 127,
            "unobserved_dispatched_opcode_count": 92,
            "command_1e_site_count": 742,
            "command_1e_distinct_operand_count": 59,
            "command_1e_distinct_target_count": 59,
            "command_1e_operand_to_target_alias_count": 0,
            "command_1f_site_count": 59,
            "nested_entrypoint_with_command_1e_count": 0,
            "nested_command_21_conditional_return_site_count": 24,
            "nested_command_25_conditional_stop_site_count": 0,
            "maximum_transitive_command_1e_depth": 1,
            "command_21_conditional_return_site_count": 24,
            "command_25_conditional_stop_site_count": 70,
            "command_80_site_count": 289,
            "command_80_zero_nibble_site_count": 0,
            "command_da_lookahead_site_count": 88,
            "default_handler_sticky_site_count": 448,
            "undispatched_marker_site_count": 0,
            "token_extent_overlap_conflict_count": 0,
        }
        for key, value in expected_counts.items():
            with self.subTest(key=key):
                self.assertEqual(stream[key], value)
        self.assertEqual(
            stream["command_80_owned_width_frequency"],
            {"2": 34, "3": 200, "6": 55},
        )
        self.assertEqual(
            stream["direct_entrypoint_terminal_counts"],
            {"default-handler-sticky": 449, "stop-current-script": 1_724},
        )
        self.assertEqual(
            stream["nested_entrypoint_terminal_counts"],
            {"restore-saved-parent": 59},
        )
        self.assertTrue(
            stream["all_nested_fallthrough_traces_end_in_restore_parent"]
        )

    def test_descriptor_suffix_alias_is_exactly_bounded_not_free_space(self) -> None:
        stream = AUDIT.load_reference_contract()["expected_results"][
            "stream_census"
        ]
        self.assertEqual(stream["token_start_inside_selected_descriptor_count"], 2)
        self.assertEqual(
            stream["owned_token_byte_inside_selected_descriptor_count"],
            4,
        )
        self.assertEqual(
            stream["selected_descriptor_span_reached_by_token_count"],
            1,
        )
        self.assertEqual(
            stream["entrypoint_reaching_selected_descriptor_count"],
            1,
        )
        self.assertEqual(
            len(stream["descriptor_token_intersection_ledger_sha256"]),
            64,
        )
        self.assertEqual(
            len(stream["entrypoint_reaching_descriptor_ledger_sha256"]),
            64,
        )

    def test_cross_boundary_token_counts_as_reaching_a_descriptor(self) -> None:
        token = _token(offset=0x0FFE, width=3)
        token_key = (0xCE, 0x0FFE)
        entry = (0xCE, 0x0800)
        summary = AUDIT._descriptor_intersection_summary(
            tokens={token_key: token},
            entry_traces={entry: (token_key,)},
            descriptor_spans=((0xCE, 0x1000, 0x1004),),
        )
        self.assertEqual(summary.token_starts_inside, frozenset())
        self.assertEqual(summary.intersecting_token_keys, {token_key})
        self.assertEqual(summary.owned_bytes_inside, {(0xCE, 0x1000)})
        self.assertEqual(summary.entrypoints_reaching, {entry})

    def test_nested_depth_and_cycle_detection_fail_closed(self) -> None:
        first = (0xCE, 0x1000)
        second = (0xCE, 0x1100)
        third = (0xCE, 0x1200)
        self.assertEqual(
            AUDIT._maximum_nested_depth(
                {
                    first: frozenset({second}),
                    second: frozenset({third}),
                    third: frozenset(),
                },
                frozenset({first}),
            ),
            2,
        )
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "contains a cycle",
        ):
            AUDIT._maximum_nested_depth(
                {
                    first: frozenset({second}),
                    second: frozenset({first}),
                },
                frozenset({first}),
            )

    def test_reference_shape_and_caller_replacement_fail_closed(self) -> None:
        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["unexpected"] = True
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "top-level shape drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["evidence_level"] = "verified-runtime"
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "evidence level drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["limitations"] = None
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "limitations are invalid",
        ):
            AUDIT._validate_reference_contract(contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["nonclaims"] = [1]
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "nonclaims are invalid",
        ):
            AUDIT._validate_reference_contract(contract)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_rom_matches_the_closed_reference(self) -> None:
        observed = AUDIT.observe_rom(ROM_PATH.read_bytes())
        expected = AUDIT.load_reference_contract()["expected_results"]
        self.assertEqual(observed, expected)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_report_is_deterministic_metadata_only_and_rom_is_unchanged(
        self,
    ) -> None:
        before_stat = ROM_PATH.stat()
        before = ROM_PATH.read_bytes()
        before_sha256 = hashlib.sha256(before).hexdigest()
        report = AUDIT.audit_rom(before)
        self.assertEqual(report, AUDIT.audit_rom(ROM_PATH.read_bytes()))
        self.assertEqual(report["schema"], AUDIT.SCHEMA)
        self.assertEqual(report["evidence"]["level"], "verified-static")
        self.assertTrue(report["evidence"]["canonical_rom_read_only"])
        self.assertTrue(report["evidence"]["metadata_only"])
        self.assertEqual(len(report["grammar"]["rows"]), 256)
        self.assertFalse(report["grammar"]["handler_addresses_emitted"])
        self.assertFalse(report["grammar"]["raw_dispatch_words_emitted"])
        self.assertFalse(report["reproduction"]["output_file_option_available"])
        self.assertEqual(report["reproduction"]["command"][1], "-B")
        self.assertEqual(report["reproduction"]["expected_side_effects"], "none")
        self.assertTrue(
            report["gates"]["canonical_descriptor_token_alias_is_exactly_pinned"]
        )
        self.assertTrue(
            report["gates"][
                "all_nested_fallthrough_traces_end_in_command_1f"
            ]
        )
        self.assertFalse(report["gates"]["expanded_command_1e_policy_approved"])
        self.assertFalse(report["gates"]["symbolic_high_package_bound"])
        self.assertFalse(report["gates"]["allocation_or_hook_approved"])

        semantic = dict(report)
        identity = semantic.pop("artifact_identity")
        self.assertEqual(
            identity["canonical_json_sha256_excluding_artifact_identity"],
            hashlib.sha256(AUDIT._canonical_json_bytes(semantic)).hexdigest(),
        )

        def inspect(value: object) -> None:
            self.assertNotIsInstance(value, bytes)
            self.assertNotIsInstance(value, bytearray)
            if isinstance(value, dict):
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        inspect(report)
        serialized = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn(str(ROM_PATH).lower(), serialized)
        for forbidden in (
            ".sfc",
            ".smc",
            "private/",
            "private\\",
            "rom_bytes",
            "script_bytes",
            "script_offsets",
            "pointer_list",
            "output_path",
        ):
            self.assertNotIn(forbidden, serialized)

        self.assertEqual(
            hashlib.sha256(ROM_PATH.read_bytes()).hexdigest(),
            before_sha256,
        )
        after_stat = ROM_PATH.stat()
        self.assertEqual(after_stat.st_size, before_stat.st_size)
        self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_rom_machine_witness_and_contract_drift_fail_closed(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        mutated[0x100] ^= 1
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "ROM hash does not match",
        ):
            AUDIT.audit_rom(bytes(mutated))
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "expected 0x400000 ROM bytes",
        ):
            AUDIT.audit_rom(canonical[:-1])

        for span in AUDIT.MACHINE_SPANS:
            with self.subTest(span=span.name):
                changed = bytearray(canonical)
                changed[AUDIT.topology.snes_hirom_to_file(span.start)] ^= 1
                with self.assertRaisesRegex(
                    AUDIT.BattleCommandGrammarAuditError,
                    f"machine witness drifted: {span.name}",
                ):
                    AUDIT._observe_span(bytes(changed), span)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["scope"]["production_installable"] = True
        with self.assertRaisesRegex(
            AUDIT.BattleCommandGrammarAuditError,
            "differs from pinned file",
        ):
            AUDIT.audit_rom(canonical, contract=contract)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_cli_is_stdout_only_deterministic_and_has_empty_stderr(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(AUDIT_PATH),
                str(ROM_PATH),
                "--compact",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(report, AUDIT.audit_rom(ROM_PATH.read_bytes()))


if __name__ == "__main__":
    unittest.main()
