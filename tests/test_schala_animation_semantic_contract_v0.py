from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "audit_schala_animation_semantic_contract_v0.py"
REPORT_PATH = ROOT / "references" / "schala_animation_semantic_contract_v0.json"

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_animation_semantic_contract_v0", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

ROM_ENV = os.environ.get("CT_US_REV0_ROM")
ROM_PATH = pathlib.Path(ROM_ENV).resolve() if ROM_ENV else None
if ROM_ENV and (ROM_PATH is None or not ROM_PATH.is_file()):
    raise RuntimeError(
        f"CT_US_REV0_ROM does not name a regular file: {ROM_PATH}"
    )
ROM_AVAILABLE = ROM_PATH is not None


class SchalaAnimationSemanticContractPureTests(unittest.TestCase):
    def test_engine_orders_and_minimum_anchor_sets_are_exact(self) -> None:
        self.assertEqual(
            TOOL.ENGINE_FACING_ORDER,
            ("up", "down", "left", "right"),
        )
        self.assertEqual(
            TOOL.BATTLE_FIXED_ENTRYPOINTS,
            (0x00, 0x03, 0x08, 0x0A, 0x0C, 0x12, 0x1A, 0x23),
        )
        self.assertEqual(
            TOOL.MENU_ENTRYPOINTS,
            (0x00, 0x01, 0x0B),
        )
        self.assertEqual(
            tuple(role["entrypoint"] for role in TOOL.MENU_CONSUMER_ROLES),
            TOOL.MENU_ENTRYPOINTS,
        )
        self.assertEqual(len(TOOL.EXPECTED_AUX_POINTERS), 9)
        self.assertEqual(TOOL.EXPECTED_AUX_POINTERS[-2:], (0xB600, 0xB614))
        self.assertEqual(
            tuple(value for _, value in TOOL.EXPECTED_ANIMATION_ROOTS),
            (0x2000, 0x2300, 0x2600, 0x2800, 0x2A00, 0x3000),
        )

    def test_overlap_ledger_accepts_shared_suffix_when_tokens_agree(self) -> None:
        result = TOOL.validate_overlap_ledger(
            [
                {
                    "entrypoint": 0,
                    "primary_tokens": ("p0", "p1", "p2", "p3", "p4"),
                    "auxiliary_tokens": ("t0", "t1", "t2", "t3", "t4"),
                },
                {
                    "entrypoint": 1,
                    "primary_tokens": ("p4", "p5"),
                    "auxiliary_tokens": ("t4", "t5"),
                },
            ]
        )
        self.assertEqual(result["primary_token_count"], 6)
        self.assertEqual(result["auxiliary_token_count"], 6)

    def test_overlap_ledger_fails_closed_on_conflict(self) -> None:
        with self.assertRaisesRegex(
            TOOL.AnimationContractError,
            "conflicting primary token",
        ):
            TOOL.validate_overlap_ledger(
                [
                    {
                        "entrypoint": 0,
                        "primary_tokens": ("a", "b", "c", "d", "e"),
                        "auxiliary_tokens": (1, 1, 1, 1, 1),
                    },
                    {
                        "entrypoint": 1,
                        "primary_tokens": ("not-e",),
                        "auxiliary_tokens": (1,),
                    },
                ]
            )

    def test_cli_has_one_read_only_input_and_no_output_destination(self) -> None:
        parser = TOOL.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions},
            {"help", "rom"},
        )
        for forbidden in (
            ["--output", "report.json"],
            ["--output-dir", "build"],
            ["--allocation", "E5:0000"],
        ):
            with self.subTest(arguments=forbidden), contextlib.redirect_stderr(
                io.StringIO()
            ), self.assertRaises(SystemExit):
                parser.parse_args(forbidden)

    def test_fixed_bank_setup_and_reader_census_is_explicit(self) -> None:
        actual = tuple(
            (reader["context"], tuple(reader["sites"]))
            for reader in TOOL.FIXED_BANK_SETUP_AND_READ_SITES
        )
        self.assertEqual(
            actual,
            (
                (
                    "field auxiliary timing",
                    ("$C0:CA35", "$C0:CA3D"),
                ),
                (
                    "field primary frame tile path",
                    ("$C0:CBEE",),
                ),
                (
                    "battle state-transition reads",
                    ("$C1:2EBA", "$C1:2EEB"),
                ),
                (
                    "battle pre-animation eight-step copies",
                    ("$C1:3639", "$C1:3650"),
                ),
                (
                    "battle auxiliary and primary animation tick",
                    ("$C1:42D0", "$C1:4300"),
                ),
                (
                    "battle PC pointer setup",
                    (
                        "$CC:E9BC",
                        "$CC:E9C5",
                        "$CC:E9CE",
                        "$CC:E9D3",
                        "$CC:E9DC",
                        "$CC:E9E5",
                        "$CC:E9EF",
                        "$CC:E9F5",
                        "$CC:E9FB",
                        "$CC:EA01",
                    ),
                ),
                (
                    "menu PC pointer setup",
                    (
                        "$C2:F42D",
                        "$C2:F431",
                        "$C2:F4C3",
                        "$C2:F4C8",
                        "$C2:F4E1",
                        "$C2:F4E6",
                    ),
                ),
            ),
        )

    def test_explicit_missing_rom_environment_fails_instead_of_skipping(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["CT_US_REV0_ROM"] = str(
            ROOT / "private" / "definitely-missing-project-epoch-rom.sfc"
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.test_schala_animation_semantic_contract_v0",
            ],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "CT_US_REV0_ROM does not name a regular file",
            completed.stderr,
        )

    def test_closed_nested_schema_rejects_raw_or_unknown_shapes(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        TOOL.validate_metadata_only_report(report)

        mutations: list[tuple[str, object]] = []

        integer_stream = copy.deepcopy(report)
        integer_stream["canonical_profiles"][0]["stream_dump"] = list(range(256))
        mutations.append(("integer stream", integer_stream))

        tuple_stream = copy.deepcopy(report)
        tuple_stream["canonical_profiles"][0]["stream_dump"] = tuple(range(256))
        mutations.append(("tuple stream", tuple_stream))

        long_hex = copy.deepcopy(report)
        long_hex["nonclaims"][0] = "ab" * 1024
        mutations.append(("long encoded string", long_hex))

        case_variant = copy.deepcopy(report)
        case_variant["scope"]["ROM_BYTES"] = [0, 1, 2, 3]
        mutations.append(("case-variant raw key", case_variant))

        nested_mapping = copy.deepcopy(report)
        nested_mapping["engine_contract"]["unexpected"] = {"value": 1}
        mutations.append(("unexpected nested mapping", nested_mapping))

        for label, mutation in mutations:
            with self.subTest(label=label), self.assertRaises(
                TOOL.AnimationContractError
            ):
                TOOL.validate_metadata_only_report(mutation)


@unittest.skipUnless(
    ROM_AVAILABLE,
    "set CT_US_REV0_ROM to the private canonical headerless ROM",
)
class SchalaAnimationSemanticContractRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert ROM_PATH is not None
        cls.rom = ROM_PATH.read_bytes()
        cls.report = TOOL.build_report(cls.rom)

    def test_canonical_identity_and_all_preimage_spans_are_pinned(self) -> None:
        identity = self.report["inputs"]["canonical_rom"]
        self.assertEqual(identity["size"], 0x400000)
        self.assertEqual(identity["sha1"], TOOL.CANONICAL_ROM_SHA1)
        self.assertEqual(identity["sha256"], TOOL.CANONICAL_ROM_SHA256)
        spans = self.report["engine_contract"]["canonical_preimage_spans"]
        self.assertEqual(len(spans), len(TOOL.ENGINE_SPANS))
        self.assertTrue(all(row["evidence"] == "verified-static" for row in spans))
        self.assertIn(
            "bank_e4_animation_root_table",
            {row["label"] for row in spans},
        )
        self.assertIn(
            "menu_party_animation_roles",
            {row["label"] for row in spans},
        )
        self.assertIn(
            "field_facing_value_order",
            {row["label"] for row in spans},
        )

    def test_disassembly_is_truthfully_separate_from_machine_inputs(self) -> None:
        self.assertEqual(
            frozenset(self.report["inputs"]),
            {"canonical_rom", "current_body_report"},
        )
        reference = self.report["interpretive_reference"]
        self.assertFalse(reference["auditor_reads_checkout"])
        self.assertFalse(reference["project_epoch_clone_contains_checkout"])
        self.assertEqual(reference["evidence"], "documented")
        self.assertEqual(reference["expected_commit"], TOOL.DISASSEMBLY_COMMIT)

    def test_facing_contract_does_not_reorder_source_art(self) -> None:
        engine = self.report["engine_contract"]
        self.assertEqual(engine["facing_order"], ["up", "down", "left", "right"])
        self.assertEqual(engine["facing_numeric_values"], [0, 1, 2, 3])
        self.assertEqual(
            engine["facing_order_evidence"]["numeric_immediate_order"],
            "verified-static",
        )
        self.assertEqual(
            engine["facing_order_evidence"]["direction_names"],
            "documented",
        )
        self.assertEqual(
            engine["current_body_cardinal_source_role_order"],
            ["down", "up", "left", "right"],
        )
        self.assertFalse(engine["source_role_order_is_engine_facing_order"])
        self.assertFalse(
            self.report["scope"]["source_ordinals_are_native_animation_ids"]
        )

    def test_primary_and_auxiliary_roots_and_fixed_bank_gate_are_exact(self) -> None:
        engine = self.report["engine_contract"]
        roots = engine["bank_e4_roots"]
        self.assertEqual(roots["primary_root_address"], "$E4:FFE4")
        self.assertEqual(roots["primary_root_value"], "$E4:2600")
        self.assertEqual(roots["auxiliary_root_address"], "$E4:FFE6")
        self.assertEqual(roots["auxiliary_root_value"], "$E4:2800")
        self.assertEqual(len(roots["entries"]), 6)
        fixed = engine["fixed_bank_setup_and_reader_contract"]
        self.assertEqual(len(fixed["sites"]), 7)
        self.assertIn("fixed bank E4", fixed["claim"])
        self.assertIn("no expanded-bank reader adapter", fixed["nonclaim"])

    def test_auxiliary_contract_is_one_facing_and_b600_is_not_magus_end(self) -> None:
        for profile in self.report["canonical_profiles"]:
            with self.subTest(pc=profile["name"]):
                self.assertEqual(profile["auxiliary_size"], profile["facing_span"])
                self.assertTrue(
                    all(
                        row["primary_auxiliary_terminators_aligned"]
                        for row in profile["declared_anchor_sequences"]
                    )
                )
        magus = self.report["canonical_profiles"][6]
        self.assertEqual(magus["auxiliary_contract_end_exclusive"], "$E4:AFB4")
        self.assertEqual(magus["next_table_pointer"], "$E4:B600")
        self.assertEqual(magus["occupied_next_pointer_successor"], "$E4:B614")
        self.assertFalse(magus["next_pointer_is_contract_end"])
        self.assertIn("tail remains unclassified", magus["auxiliary_end_basis"])

    def test_entrypoints_are_n_times_four_and_may_overlap(self) -> None:
        engine = self.report["engine_contract"]
        self.assertEqual(engine["entrypoint_stride"], 4)
        self.assertIn("N * 4", engine["entrypoint_rule"])
        self.assertIn("overlapping or suffix", engine["overlap_policy"])
        for profile in self.report["canonical_profiles"]:
            actual = tuple(
                row["entrypoint"] for row in profile["declared_anchor_sequences"]
            )
            self.assertEqual(actual, TOOL.DECLARED_ANCHORS)
            self.assertIn(0x0B, actual)

    def test_state_table_decodes_all_records_and_special_paths(self) -> None:
        table = self.report["consumer_roles"]["battle"]["state_selector_table"]
        self.assertEqual(table["record_count"], 16)
        self.assertEqual(table["record_size"], 4)
        self.assertEqual(table["table_terminator"], 0xFF)
        self.assertEqual(
            table["decoded_records"],
            [dict(record) for record in TOOL.EXPECTED_BATTLE_STATE_RECORDS],
        )
        self.assertTrue(
            table["decoded_records"][0][
                "record0_forced_match_when_slot_$A119_nonzero"
            ]
        )
        self.assertTrue(
            table["record0_special_case"]["requested_state_write_suppressed"]
        )
        self.assertEqual(
            table["no_record_match_default"]["when_per_slot_$A09B_nonzero"],
            0x00,
        )
        self.assertEqual(
            table["no_record_match_default"]["when_per_slot_$A09B_zero"],
            0x03,
        )
        self.assertFalse(table["selector_ff_dispatches_literally"])
        self.assertEqual(
            table["selector_ff_resolution"]["when_$A0A7_zero"],
            "resolve selector to entrypoint $03",
        )
        self.assertEqual(
            table["selector_ff_resolution"]["when_$A0A7_nonzero"],
            "skip matched record",
        )

    def test_battle_and_menu_consumer_conditions_are_not_visual_guesses(self) -> None:
        consumers = self.report["consumer_roles"]
        battle = consumers["battle"]
        self.assertEqual(
            tuple(row["entrypoint"] for row in battle["fixed_entrypoints"]),
            TOOL.BATTLE_FIXED_ENTRYPOINTS,
        )
        transitions = {row["entrypoint"]: row for row in battle["transition_calls"]}
        self.assertIn("$96F5", transitions[0x08]["condition"])
        self.assertIn("EventCommandD8Settings bit 0", transitions[0x0A]["condition"])
        self.assertIn("$A09B clear", transitions[0x0A]["condition"])
        self.assertIn("$A09B clear", transitions[0x0C]["condition"])
        self.assertIn(
            "$A09B clear",
            battle["critical_hp_override"]["condition"],
        )
        self.assertTrue(
            all(row["visual_semantics"] == "unresolved" for row in transitions.values())
        )
        menu = consumers["menu"]["entrypoints"]
        self.assertEqual(tuple(row["entrypoint"] for row in menu), (0x00, 0x01, 0x0B))
        self.assertEqual(
            tuple(row["consumer"] for row in menu),
            (
                "reset sweep before party-exchange highlighting",
                "hovered party-exchange slot",
                "picked party-exchange slot",
            ),
        )

    def test_current_sixteen_frames_remain_metadata_only_and_unbound(self) -> None:
        coverage = self.report["authoring_coverage"]
        ids = [
            frame_id
            for role in coverage
            for frame_id in role["current_frame_ids"]
        ]
        self.assertEqual(len(ids), 16)
        self.assertEqual(len(set(ids)), 16)
        self.assertTrue(all(role["native_binding"] is None for role in coverage))
        self.assertTrue(all(role["timing_binding"] is None for role in coverage))
        self.assertTrue(
            all(role["binding_state"] == "source-role-only-unbound" for role in coverage)
        )

    def test_static_evidence_is_sufficient_only_for_v0_authoring(self) -> None:
        evidence = self.report["evidence"]
        self.assertTrue(evidence["static_evidence_sufficient_for_metadata_contract_v0"])
        self.assertTrue(evidence["static_evidence_sufficient_for_source_role_authoring"])
        self.assertFalse(evidence["static_evidence_sufficient_for_animation_blob_or_install"])
        self.assertEqual(evidence["new_runtime_evidence"], "not performed")
        self.assertEqual(
            self.report["status"],
            "pass-metadata-only-with-open-gates",
        )

    def test_report_contains_no_raw_stream_or_production_binding(self) -> None:
        TOOL.validate_metadata_only_report(self.report)
        encoded = TOOL.canonical_report_bytes(self.report).lower()
        for forbidden in (
            b".sfc",
            b".smc",
            b"private/",
            b"private\\",
            str(ROM_PATH).encode("utf-8").lower(),
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.report["scope"]["rom_installable"])
        self.assertFalse(self.report["scope"]["production_hook_assigned"])
        self.assertFalse(self.report["scope"]["production_allocation_assigned"])
        joined = " ".join(self.report["nonclaims"])
        self.assertIn("fixed-bank E4 setup/reader sites", joined)
        self.assertIn("not free space", joined)

    def test_every_canonical_drift_gate_rejects_before_claim(self) -> None:
        wrong_identity = bytearray(self.rom)
        wrong_identity[0] ^= 1
        with self.assertRaisesRegex(
            TOOL.AnimationContractError,
            "SHA-1 mismatch",
        ):
            TOOL.validate_canonical_rom(bytes(wrong_identity))

        wrong_aux = bytearray(self.rom)
        wrong_aux[TOOL.AUX_POINTER_TABLE_FILE] ^= 1
        with self.assertRaisesRegex(
            TOOL.AnimationContractError,
            "auxiliary animation pointer table drifted",
        ):
            TOOL.verify_pointer_tables(bytes(wrong_aux))

        wrong_root = bytearray(self.rom)
        wrong_root[TOOL.ANIMATION_ROOT_TABLE_FILE + 4] ^= 1
        with self.assertRaisesRegex(
            TOOL.AnimationContractError,
            "bank E4 animation root table drifted",
        ):
            TOOL.verify_pointer_tables(bytes(wrong_root))

        wrong_state = bytearray(self.rom)
        wrong_state[TOOL.BATTLE_STATE_TABLE_FILE_START + 3] ^= 1
        with self.assertRaisesRegex(
            TOOL.AnimationContractError,
            "battle state animation table drifted",
        ):
            TOOL.analyze_battle_state_table(bytes(wrong_state))

        wrong_span = bytearray(self.rom)
        wrong_span[0x02C973] ^= 1
        with self.assertRaisesRegex(
            TOOL.AnimationContractError,
            "menu_party_animation_roles: canonical preimage drifted",
        ):
            TOOL.verify_engine_spans(bytes(wrong_span))

        for label, offset, expected_message in (
            (
                "battle preload final BNE displacement",
                0x01365C,
                "battle_preload_eight_step_copy: canonical preimage drifted",
            ),
            (
                "menu tick final direct-page operand",
                0x02F706,
                "menu_animation_tick: canonical preimage drifted",
            ),
            (
                "facing-order immediate",
                0x005536,
                "field_facing_value_order: canonical preimage drifted",
            ),
        ):
            mutated = bytearray(self.rom)
            mutated[offset] ^= 1
            with self.subTest(label=label), self.assertRaisesRegex(
                TOOL.AnimationContractError,
                expected_message,
            ):
                TOOL.verify_engine_spans(bytes(mutated))

    def test_report_generation_uses_no_explicit_artifact_write_call(self) -> None:
        with mock.patch.object(
            pathlib.Path,
            "write_bytes",
            side_effect=AssertionError("binary write attempted"),
        ), mock.patch.object(
            pathlib.Path,
            "write_text",
            side_effect=AssertionError("text write attempted"),
        ):
            rebuilt = TOOL.build_report(self.rom)
        self.assertEqual(rebuilt, self.report)

    def test_pinned_report_and_cli_are_byte_identical(self) -> None:
        expected = REPORT_PATH.read_bytes()
        self.assertEqual(expected, TOOL.canonical_report_bytes(self.report))
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        assert ROM_PATH is not None
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--rom", str(ROM_PATH)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(completed.stdout, expected)
        self.assertEqual(json.loads(expected), json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
