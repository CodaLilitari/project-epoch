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

AUDIT_PATH = TOOLS_DIR / "audit_battle_action_package_topology_v0.py"
REFERENCE_PATH = (
    ROOT / "references" / "battle_action_package_topology_v0.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_battle_action_package_topology_v0",
    AUDIT_PATH,
)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def _synthetic_descriptor_rom(
    *,
    bank: int = 0xCE,
    root: int = 0x0100,
    mask0: int = 0x8001,
    mask1: int = 0x4000,
    pointers: tuple[int, ...] = (0x0200, 0x0210, 0x0220),
) -> bytes:
    size = ((bank & 0x3F) << 16) + root + 4 + len(pointers) * 2
    rom = bytearray(max(size, 0x1000))
    offset = ((bank & 0x3F) << 16) + root
    rom[offset : offset + 4] = bytes(
        (
            mask0 >> 8,
            mask0 & 0xFF,
            mask1 >> 8,
            mask1 & 0xFF,
        )
    )
    cursor = offset + 4
    for pointer in pointers:
        rom[cursor : cursor + 2] = pointer.to_bytes(2, "little")
        cursor += 2
    return bytes(rom)


class BattleActionPackageTopologyV0Tests(unittest.TestCase):
    def test_reference_contract_is_byte_pinned_and_closed(self) -> None:
        source = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(source), AUDIT.REFERENCE_SIZE)
        self.assertEqual(
            hashlib.sha256(source).hexdigest(),
            AUDIT.REFERENCE_SHA256,
        )
        contract = AUDIT.load_reference_contract()
        self.assertEqual(contract["schema"], AUDIT.REFERENCE_SCHEMA)
        self.assertEqual(contract["evidence_level"], "verified-static")
        self.assertEqual(
            [row["name"] for row in contract["route_contracts"]],
            list(AUDIT.ROUTE_SPECS),
        )
        self.assertEqual(
            set(contract["expected_results"]["routes"]),
            set(AUDIT.ROUTE_SPECS),
        )
        self.assertEqual(contract["limitations"], list(AUDIT.LIMITATIONS))
        self.assertEqual(contract["nonclaims"], list(AUDIT.NONCLAIMS))

    def test_all_built_in_hashes_and_extents_have_exact_geometry(self) -> None:
        self.assertEqual(len(AUDIT.REFERENCE_SHA256), 64)
        self.assertEqual(len(AUDIT.CANONICAL_ROM_SHA256), 64)
        self.assertEqual(len(AUDIT.MACHINE_SPANS), 20)
        self.assertEqual(len(AUDIT.TABLE_SPECS), 11)
        for span in (*AUDIT.MACHINE_SPANS, *AUDIT.TABLE_SPECS):
            with self.subTest(span=span.name):
                self.assertLess(span.start, span.end_exclusive)
                self.assertEqual(len(span.expected_sha256), 64)
        for name, digest in AUDIT.SELECTOR_VECTOR_HASHES.items():
            with self.subTest(selector_vector=name):
                self.assertEqual(len(digest), 64)
        self.assertEqual(len(AUDIT.PC_NAMED_SELECTOR_VECTOR_SHA256), 64)

        tables = {spec.name: spec for spec in AUDIT.TABLE_SPECS}
        self.assertEqual(
            tables["pc_action_configs"].end_exclusive,
            tables["enemy_attack_param_zero_configs"].start,
        )
        self.assertEqual(
            tables["enemy_attack_param_zero_configs"].end_exclusive,
            tables["enemy_attack_param_nonzero_configs"].start,
        )
        self.assertEqual(
            tables["enemy_attack_param_nonzero_configs"].end_exclusive,
            tables["enemy_tech_configs"].start,
        )
        self.assertEqual(
            tables["enemy_tech_configs"].end_exclusive,
            tables["item_configs"].start,
        )
        self.assertEqual(
            tables["item_configs"].end_exclusive,
            tables["pc_normal_attack_package_resolver"].start,
        )

    def test_descriptor_parser_preserves_endianness_slots_and_mask_passes(
        self,
    ) -> None:
        rom = _synthetic_descriptor_rom()
        descriptor = AUDIT.parse_package_descriptor(
            rom,
            bank=0xCE,
            root_offset=0x0100,
            allowed_offset_start=0,
            allowed_offset_end_exclusive=0xE000,
        )
        self.assertEqual(descriptor.mask0, 0x8001)
        self.assertEqual(descriptor.mask1, 0x4000)
        self.assertEqual(descriptor.end_offset_exclusive, 0x010A)
        self.assertEqual(
            [
                (entry.branch, entry.owner_slot, entry.script_offset)
                for entry in descriptor.entries
            ],
            [
                (0, 0, 0x0200),
                (0, 15, 0x0210),
                (1, 1, 0x0220),
            ],
        )
        self.assertNotEqual(
            descriptor.mask0,
            int.from_bytes(bytes((0x80, 0x01)), "little"),
        )

    def test_descriptor_parser_fails_before_invalid_target_access(self) -> None:
        rom = _synthetic_descriptor_rom()
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "FFFF",
        ):
            AUDIT.parse_package_descriptor(
                rom,
                bank=0xCE,
                root_offset=0xFFFF,
                allowed_offset_start=0,
                allowed_offset_end_exclusive=0xE000,
            )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "outside the audited bank region",
        ):
            AUDIT.parse_package_descriptor(
                rom,
                bank=0xCE,
                root_offset=0xE000,
                allowed_offset_start=0,
                allowed_offset_end_exclusive=0xE000,
            )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "truncated",
        ):
            AUDIT.parse_package_descriptor(
                rom,
                bank=0xCE,
                root_offset=0x0100,
                allowed_offset_start=0,
                allowed_offset_end_exclusive=0x0109,
            )

        near_end = bytearray(((0xCE & 0x3F) << 16) + 0x0300)
        exact_header_offset = ((0xCE & 0x3F) << 16) + 0x01FC
        near_end[exact_header_offset : exact_header_offset + 4] = b"\0\0\0\0"
        exact_header = AUDIT.parse_package_descriptor(
            bytes(near_end),
            bank=0xCE,
            root_offset=0x01FC,
            allowed_offset_start=0,
            allowed_offset_end_exclusive=0x0200,
        )
        self.assertEqual(exact_header.end_offset_exclusive, 0x0200)
        for root in (0x01FD, 0x01FE, 0x01FF):
            with self.subTest(root=f"{root:04X}"), self.assertRaisesRegex(
                AUDIT.BattlePackageTopologyAuditError,
                "header is truncated",
            ):
                AUDIT.parse_package_descriptor(
                    bytes(near_end),
                    bank=0xCE,
                    root_offset=root,
                    allowed_offset_start=0,
                    allowed_offset_end_exclusive=0x0200,
                )

        outside_script = _synthetic_descriptor_rom(
            mask0=0x8000,
            mask1=0,
            pointers=(0xE000,),
        )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "script entrypoint is outside",
        ):
            AUDIT.parse_package_descriptor(
                outside_script,
                bank=0xCE,
                root_offset=0x0100,
                allowed_offset_start=0,
                allowed_offset_end_exclusive=0xE000,
            )

    def test_bank_is_part_of_descriptor_and_script_identity(self) -> None:
        ce = AUDIT.PackageDescriptor(
            0xCE,
            0x0100,
            0x0106,
            0x0080,
            0,
            (AUDIT.DescriptorEntry(0, 8, 0x1234),),
        )
        cd = AUDIT.PackageDescriptor(
            0xCD,
            0x0100,
            0x0106,
            0x0080,
            0,
            (AUDIT.DescriptorEntry(0, 8, 0x1234),),
        )
        result = AUDIT._validate_descriptor_geometry(
            {"ce": {ce.root_offset: ce}, "cd": {cd.root_offset: cd}},
            route_names=("ce", "cd"),
        )
        self.assertEqual(result["distinct_descriptor_count"], 2)
        self.assertEqual(
            result["distinct_physical_script_entrypoint_count"],
            2,
        )
        self.assertEqual(result["descriptor_count_by_bank"], {"CD": 1, "CE": 1})
        self.assertEqual(
            result["script_entrypoint_count_by_bank"],
            {"CD": 1, "CE": 1},
        )

    def test_overlaps_and_script_targets_inside_descriptors_fail_closed(
        self,
    ) -> None:
        left = AUDIT.PackageDescriptor(
            0xCE,
            0x0100,
            0x010A,
            0x0080,
            0,
            (AUDIT.DescriptorEntry(0, 8, 0x0200),),
        )
        overlap = AUDIT.PackageDescriptor(
            0xCE,
            0x0108,
            0x0110,
            0x0080,
            0,
            (AUDIT.DescriptorEntry(0, 8, 0x0210),),
        )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "descriptor spans overlap",
        ):
            AUDIT._validate_descriptor_geometry(
                {"left": {0x0100: left}, "right": {0x0108: overlap}},
                route_names=("left", "right"),
            )

        self_target = AUDIT.PackageDescriptor(
            0xCE,
            0x0100,
            0x010A,
            0x0080,
            0,
            (AUDIT.DescriptorEntry(0, 8, 0x0106),),
        )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "targets descriptor bytes",
        ):
            AUDIT._validate_descriptor_geometry(
                {"self": {0x0100: self_target}},
                route_names=("self",),
            )

        forbidden_owner_bit = AUDIT.PackageDescriptor(
            0xCE,
            0x0100,
            0x0106,
            0x0400,
            0,
            (AUDIT.DescriptorEntry(0, 5, 0x0200),),
        )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "owner bits 05-07",
        ):
            AUDIT._validate_descriptor_geometry(
                {"slot": {0x0100: forbidden_owner_bit}},
                route_names=("slot",),
            )

    def test_typed_input_domains_reject_namespace_collisions(self) -> None:
        for logical_pc_id in range(7):
            self.assertEqual(
                AUDIT.require_vanilla_pc_normal_attack_id(logical_pc_id),
                logical_pc_id,
            )
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "outside vanilla domain",
        ):
            AUDIT.require_vanilla_pc_normal_attack_id(0x07)

        self.assertEqual(AUDIT.require_named_pc_tech_action_id(0x01), 0x01)
        self.assertEqual(AUDIT.require_named_pc_tech_action_id(0x74), 0x74)
        for value in (0x00, 0x75, 0x7C, 0x7F, 0x80, 0x90):
            with self.subTest(pc_tech_action=f"{value:02X}"), self.assertRaises(
                AUDIT.BattlePackageTopologyAuditError
            ):
                AUDIT.require_named_pc_tech_action_id(value)

        self.assertEqual(AUDIT.battle_item_record_index(0xBC), 0)
        self.assertEqual(AUDIT.battle_item_record_index(0xDB), 0x1F)
        for value in (0xBB, 0xDC, 0xE8, 0xEE, 0xF1, 0xFF):
            with self.subTest(item=f"{value:02X}"), self.assertRaisesRegex(
                AUDIT.BattlePackageTopologyAuditError,
                "outside canonical battle-package domain",
            ):
                AUDIT.battle_item_record_index(value)

    def test_action_item_and_opcode_namespaces_remain_separate(self) -> None:
        contract = AUDIT.load_reference_contract()
        rows = {row["name"]: row for row in contract["route_contracts"]}
        self.assertFalse(
            rows["pc_normal_attack"]["action_parameter_AE93_selects_package"]
        )
        self.assertFalse(rows["enemy_attack"]["AE93_is_enemy_record_index"])
        self.assertFalse(
            rows["pc_internal_type2_config"][
                "player_command_namespace_claimed"
            ]
        )
        self.assertTrue(
            rows["pc_internal_type2_config"]["config_index_7E_unclaimed"]
        )
        self.assertIn(
            "$3A != 04",
            rows["pc_internal_type2_config"][
                "fixed_7B_7D_static_condition"
            ],
        )
        self.assertEqual(
            rows["pc_internal_type2_config"][
                "fixed_7B_7D_interpretation"
            ],
            "participant-arity-shaped no-target fallback; inference only",
        )
        self.assertFalse(
            rows["pc_named_tech"]["player_command_ids_7C_7F_included"]
        )
        self.assertTrue(
            rows["pc_named_tech"][
                "same_numeric_values_may_exist_in_other_namespaces"
            ]
        )
        self.assertEqual(rows["battle_item"]["physical_span_rows"], 96)
        self.assertEqual(rows["battle_item"]["byte_input_addressable_rows"], 68)
        self.assertEqual(rows["battle_item"]["canonical_battle_item_rows"], 32)
        self.assertFalse(
            rows["battle_item"][
                "focus_ids_E8_EE_accepted_as_battle_item_packages"
            ]
        )
        serialized = json.dumps(contract, sort_keys=True)
        self.assertIn("Action IDs", serialized)
        self.assertIn("battle-script opcodes", serialized)
        self.assertNotIn('"EnemyTechAnimRecords"', serialized)

    def test_cli_and_auditor_source_have_no_write_destination(self) -> None:
        parser = AUDIT.build_parser()
        self.assertEqual(
            {action.dest for action in parser._actions},
            {"help", "rom", "compact"},
        )
        source = AUDIT_PATH.read_text(encoding="utf-8")
        for forbidden_write in (
            ".write_bytes(",
            ".write_text(",
            "open(\"wb\"",
            "open('wb'",
            "open(\"w\"",
            "open('w'",
            "open(\"a\"",
            "open('a'",
            "shutil.copy",
            "subprocess.",
        ):
            self.assertNotIn(forbidden_write, source)
        for forbidden_cli in (
            "--output",
            "--patch",
            "--save",
            "--state",
            "--trace",
        ):
            self.assertNotIn(forbidden_cli, source)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_route_contexts_preserve_the_ordered_pc_permutation(
        self,
    ) -> None:
        rom = ROM_PATH.read_bytes()
        contexts = AUDIT._build_route_contexts(rom)
        named = contexts["pc_named_tech"]
        selectors = bytes(int(row[-1]) for row in named)
        self.assertEqual(len(named), 116)
        self.assertEqual(set(selectors), set(range(0x01, 0x75)))
        self.assertEqual(
            hashlib.sha256(selectors).hexdigest(),
            AUDIT.PC_NAMED_SELECTOR_VECTOR_SHA256,
        )
        self.assertEqual(
            sum(int(row[0]) != int(row[-1]) for row in named),
            27,
        )
        self.assertEqual(contexts["battle_item"][0][0], 0xBC)
        self.assertEqual(contexts["battle_item"][-1][0], 0xDB)
        self.assertEqual(contexts["pc_action_physical"][-1][0], 0x7F)
        internal = contexts["pc_internal_type2_config"]
        self.assertEqual(len(internal), 7)
        self.assertEqual(
            sorted({int(row[-2]) for row in internal}),
            [0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7F],
        )
        self.assertEqual(
            [int(row[-2]) for row in internal].count(0x7F),
            2,
        )
        self.assertTrue(
            all(int(row[-2]) == int(row[-1]) for row in internal)
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_report_matches_exact_topology_and_identity(self) -> None:
        rom = ROM_PATH.read_bytes()
        report = AUDIT.audit_rom(rom)
        self.assertEqual(report["schema"], AUDIT.SCHEMA)
        self.assertEqual(report["status"], AUDIT.STATUS)
        self.assertEqual(report["evidence"]["level"], "verified-static")
        self.assertFalse(report["evidence"]["runtime"])
        self.assertFalse(report["gates"]["battle_command_decoder_complete"])
        self.assertFalse(report["gates"]["allocation_or_hook_approved"])
        self.assertTrue(
            report["gates"][
                "encoded_operand_ae93_opcode_candidate_census_matched"
            ]
        )

        routes = report["package_topology"]["routes"]
        self.assertEqual(
            (
                routes["pc_normal_attack"]["distinct_descriptor_count"],
                routes["pc_named_tech"]["distinct_descriptor_count"],
                routes["pc_internal_type2_config"][
                    "distinct_descriptor_count"
                ],
                routes["enemy_attack"]["distinct_descriptor_count"],
                routes["enemy_tech"]["distinct_descriptor_count"],
                routes["battle_item"]["distinct_descriptor_count"],
            ),
            (19, 116, 6, 122, 174, 15),
        )
        self.assertEqual(
            (
                routes["pc_normal_attack"][
                    "physical_script_pointer_occurrence_count"
                ],
                routes["pc_named_tech"][
                    "physical_script_pointer_occurrence_count"
                ],
                routes["pc_internal_type2_config"][
                    "physical_script_pointer_occurrence_count"
                ],
                routes["enemy_attack"][
                    "physical_script_pointer_occurrence_count"
                ],
                routes["enemy_tech"][
                    "physical_script_pointer_occurrence_count"
                ],
                routes["battle_item"][
                    "physical_script_pointer_occurrence_count"
                ],
            ),
            (116, 1095, 20, 678, 1221, 89),
        )
        selected = report["package_topology"]["declared_context_union"]
        self.assertEqual(selected["distinct_descriptor_count"], 452)
        self.assertEqual(
            selected["physical_script_pointer_occurrence_count"],
            3219,
        )
        self.assertEqual(
            selected["distinct_physical_script_entrypoint_count"],
            2146,
        )
        self.assertEqual(
            selected["script_entrypoint_count_by_bank"],
            {"CD": 1211, "CE": 935},
        )
        self.assertEqual(
            selected["included_routes"],
            [
                "pc_normal_attack",
                "pc_named_tech",
                "pc_internal_type2_config",
                "enemy_attack",
                "enemy_tech",
                "battle_item",
            ],
        )
        self.assertEqual(
            selected["union_semantics"],
            "declared structural union, not runtime reachability",
        )
        physical = report["package_topology"][
            "config_selected_structural_union"
        ]
        self.assertEqual(
            (
                physical["distinct_descriptor_count"],
                physical["physical_script_pointer_occurrence_count"],
                physical["distinct_physical_script_entrypoint_count"],
            ),
            (455, 3249, 2173),
        )
        self.assertEqual(
            physical["union_semantics"],
            "config-selected structural supplement union, not runtime "
            "reachability",
        )
        self.assertTrue(selected["descriptor_slots_05_07_unset"])
        self.assertTrue(selected["descriptor_owner_bits_08_15_present"])
        self.assertEqual(
            report["script_topology"]["cross_route_same_bank_aliases"],
            [
                {
                    "left": "enemy_attack",
                    "right": "enemy_tech",
                    "same_bank_physical_script_entrypoint_count": 7,
                    "count_by_bank": {"CD": 7},
                }
            ],
        )
        self.assertEqual(
            report["script_topology"][
                "config_selected_cross_bank_same_low_negative_controls"
            ],
            {
                "descriptor_low_offsets_present_in_both_CD_and_CE": [
                    "8171"
                ],
                "script_low_offsets_present_in_both_CD_and_CE": [
                    "6E56",
                    "76F9",
                    "7750",
                    "81CE",
                ],
                "bank_omission_would_merge_distinct_nodes": True,
            },
        )

        canonical = AUDIT._canonical_json_bytes(report)
        self.assertEqual(len(canonical), 36390)
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            "7b201b7af2e6ec48459b802631b62495"
            "b2859ac09f5258ec61dd969f7a88871f",
        )
        self.assertEqual(
            report["artifact_identity"]["semantic_payload_sha256"],
            "dd9fdca3df71093873e723276778d066d"
            "162447e138a65ba3491fc214a6585c6",
        )
        self.assertEqual(
            report["artifact_identity"]["schema_shape_sha256"],
            "e4937373bb7961684ef085a9513a3c63"
            "298297bc608cd285fd67fc6d8e311e4b",
        )
        self.assertEqual(
            report["reproduction"]["auditor_source"],
            {
                "path": "tools/audit_battle_action_package_topology_v0.py",
                "size": 73179,
                "sha256": (
                    "2760e8bc3b2bf56cdeeb985a69a69abe"
                    "bb7f8120ee7b76e344593f0c59246952"
                ),
            },
        )

        census = report["ae93_encoded_operand_opcode_census"]
        self.assertEqual(census["candidate_ledger_size"], 464)
        self.assertEqual(
            census["candidate_ledger_sha256"],
            AUDIT.AE93_DIRECT_WRITER_CENSUS_SHA256,
        )
        self.assertEqual(
            census["fixed_pc_type02_config_indices"],
            ["79", "7A", "7B", "7C", "7D", "7F"],
        )
        self.assertFalse(
            census["config_index_7E_fixed_encoded_operand_writer_found"]
        )
        self.assertFalse(census["complete_writer_cfg_claimed"])
        self.assertEqual(
            census["fixed_helper_reference_candidates"]["jsr_abs"],
            ["C1820F", "C18945", "C18BB1"],
        )
        self.assertTrue(
            all(
                not values
                for name, values in census[
                    "fixed_helper_reference_candidates"
                ].items()
                if name != "jsr_abs"
            )
        )
        self.assertFalse(census["helper_entry_cfg_complete_claimed"])
        accepted = set(
            census["pc_type02_encoded_operand_ae93_writers"]
        )
        excluded = {
            pc
            for pcs in census[
                "excluded_encoded_operand_ae93_candidates"
            ].values()
            for pc in pcs
        }
        candidates = set(census["candidates"]["sta_abs"]) | set(
            census["candidates"]["stz_abs"]
        )
        self.assertTrue(
            census["encoded_operand_ae93_candidate_partition_complete"]
        )
        self.assertFalse(accepted & excluded)
        self.assertEqual(accepted | excluded, candidates)
        self.assertFalse(census["all_effective_writes_to_ae93_claimed"])
        self.assertFalse(
            census["adjacent_ae92_effective_write_to_ae93_proved"]
        )
        self.assertEqual(
            census["adjacent_ae92_encoded_operand_candidates"][
                "sta_abs"
            ],
            [
                "C18963",
                "C19F38",
                "C1ACFF",
                "C1B362",
                "C1BADC",
                "C1BB17",
                "C1BBA6",
                "C1BBED",
                "C1BFDC",
                "C1C676",
                "FDAA8C",
            ],
        )
        self.assertTrue(
            all(
                not values
                for name, values in census[
                    "adjacent_ae92_encoded_operand_candidates"
                ].items()
                if name != "sta_abs"
            )
        )
        self.assertTrue(
            all(
                not values
                for name, values in census["candidates"].items()
                if name not in {"sta_abs", "stz_abs"}
            )
        )
        self.assertEqual(
            report["package_topology"][
                "pc_internal_type2_index_selector_descriptor_summary"
            ],
            [
                {
                    "config_index": "79",
                    "package_selector": "79",
                    "package_bank": "CE",
                    "descriptor_root": "81D0",
                    "descriptor_relation_count": 2,
                    "distinct_direct_script_count": 1,
                },
                {
                    "config_index": "7A",
                    "package_selector": "7A",
                    "package_bank": "CE",
                    "descriptor_root": "81E0",
                    "descriptor_relation_count": 4,
                    "distinct_direct_script_count": 2,
                },
                {
                    "config_index": "7B",
                    "package_selector": "7B",
                    "package_bank": "CE",
                    "descriptor_root": "821F",
                    "descriptor_relation_count": 2,
                    "distinct_direct_script_count": 1,
                },
                {
                    "config_index": "7C",
                    "package_selector": "7C",
                    "package_bank": "CE",
                    "descriptor_root": "8234",
                    "descriptor_relation_count": 4,
                    "distinct_direct_script_count": 2,
                },
                {
                    "config_index": "7D",
                    "package_selector": "7D",
                    "package_bank": "CE",
                    "descriptor_root": "8250",
                    "descriptor_relation_count": 6,
                    "distinct_direct_script_count": 2,
                },
                {
                    "config_index": "7F",
                    "package_selector": "7F",
                    "package_bank": "CE",
                    "descriptor_root": "8288",
                    "descriptor_relation_count": 2,
                    "distinct_direct_script_count": 1,
                },
            ],
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_machine_and_resolver_negative_controls_are_pinned(
        self,
    ) -> None:
        report = AUDIT.audit_rom(ROM_PATH.read_bytes())
        self.assertEqual(
            [row["target_pc"] for row in report["action_type_contract"]["targets"]],
            ["C1475A", "C1432C", "C145A0", "C1475B"],
        )
        tables = {row["name"]: row for row in report["table_contract"]}
        for name, expected in AUDIT.EXPECTED_RESOLVER_INVENTORY.items():
            with self.subTest(resolver=name):
                observed = tables[name]
                for key, value in expected.items():
                    self.assertEqual(observed[key], value)
                self.assertTrue(observed["selected_targets_are_non_ffff"])
                self.assertFalse(
                    observed["engine_local_ffff_rejection_proved"]
                )
        self.assertEqual(
            tables["item_configs"]["distinct_selector_count"],
            33,
        )
        self.assertEqual(tables["item_configs"]["selector_max"], "FF")
        self.assertEqual(
            tables["enemy_attack_param_nonzero_configs"]["role"],
            "selector_source",
        )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_report_is_closed_metadata_only_and_rom_is_unchanged(self) -> None:
        before_stat = ROM_PATH.stat()
        before = ROM_PATH.read_bytes()
        before_sha256 = hashlib.sha256(before).hexdigest()
        report = AUDIT.audit_rom(before)
        report_again = AUDIT.audit_rom(ROM_PATH.read_bytes())
        self.assertEqual(report, report_again)

        self.assertEqual(
            set(report),
            {
                "schema",
                "version",
                "auditor_version",
                "status",
                "evidence_ceiling",
                "scope",
                "inputs",
                "action_type_contract",
                "ae93_encoded_operand_opcode_census",
                "machine_code_contract",
                "table_contract",
                "selector_namespaces",
                "package_topology",
                "script_topology",
                "descriptor_contract",
                "hazards",
                "gates",
                "evidence",
                "reproduction",
                "limitations",
                "nonclaims",
                "artifact_identity",
            },
        )

        identity = report["artifact_identity"]
        semantic_report = dict(report)
        del semantic_report["artifact_identity"]
        semantic_bytes = AUDIT._canonical_json_bytes(semantic_report)
        self.assertEqual(identity["semantic_payload_size"], len(semantic_bytes))
        self.assertEqual(
            identity["semantic_payload_sha256"],
            hashlib.sha256(semantic_bytes).hexdigest(),
        )
        self.assertFalse(identity["full_report_self_hash_included"])
        self.assertFalse(report["reproduction"]["output_file_option_available"])
        self.assertEqual(report["reproduction"]["expected_side_effects"], "none")

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
            "raw_rom",
            "rom_bytes",
            "table_bytes",
            "payload_bytes",
            "script_bytes",
            "script_stream",
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
    def test_rom_and_each_bounded_preimage_drift_fail_closed(self) -> None:
        canonical = ROM_PATH.read_bytes()
        mutated = bytearray(canonical)
        mutated[0x100] ^= 1
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "ROM hash does not match",
        ):
            AUDIT.audit_rom(bytes(mutated))
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "expected 0x400000 ROM bytes",
        ):
            AUDIT.audit_rom(canonical[:-1])
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "expected 0x400000 ROM bytes",
        ):
            AUDIT.audit_rom(canonical + bytes(0x200))

        for span in (*AUDIT.MACHINE_SPANS, *AUDIT.TABLE_SPECS):
            with self.subTest(span=span.name):
                changed = bytearray(canonical)
                changed[AUDIT.snes_hirom_to_file(span.start)] ^= 1
                with self.assertRaisesRegex(
                    AUDIT.BattlePackageTopologyAuditError,
                    f"bounded preimage drifted: {span.name}",
                ):
                    AUDIT._observe_span(bytes(changed), span)

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_caller_cannot_replace_the_pinned_reference_contract(self) -> None:
        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["scope"]["production_installable"] = True
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "differs from pinned file",
        ):
            AUDIT.audit_rom(ROM_PATH.read_bytes(), contract=contract)

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["expected_results"]["routes"]["enemy_tech"][
            "distinct_descriptor_count"
        ] = 175
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "differs from pinned file",
        ):
            AUDIT.audit_rom(ROM_PATH.read_bytes(), contract=contract)

    def test_duplicate_json_keys_and_root_shape_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "duplicate JSON key",
        ):
            AUDIT._reject_duplicate_keys([("scope", 1), ("scope", 2)])

        contract = copy.deepcopy(AUDIT.load_reference_contract())
        contract["unexpected"] = True
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "reference root keys drifted",
        ):
            AUDIT._validate_reference_contract(contract)

        pinned = AUDIT.load_reference_contract()
        nested = copy.deepcopy(pinned)
        nested["scope"]["unexpected"] = True
        with self.assertRaisesRegex(
            AUDIT.BattlePackageTopologyAuditError,
            "nested keys drifted",
        ):
            AUDIT._require_same_json_shape(
                nested,
                pinned,
                "reference",
            )

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_cli_is_stdout_only_deterministic_and_has_empty_stderr(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
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
