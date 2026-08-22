from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "audit_location_event_animation_operands_v0.py"
REPORT_PATH = (
    ROOT / "references" / "location_event_animation_operands_v0.json"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_location_event_animation_operands_v0", TOOL_PATH
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


def make_group(
    function_rows: tuple[tuple[int, ...], ...],
    source: bytes,
    *,
    parse: bool = True,
) -> object:
    object_count = len(function_rows)
    if any(len(row) != 16 for row in function_rows):
        raise ValueError("each object requires sixteen function pointers")
    pointer_table = b"".join(
        pointer.to_bytes(2, "little")
        for row in function_rows
        for pointer in row
    )
    decoded = bytes([object_count]) + pointer_table + source
    commands = (
        tuple(TOOL.PARSER.parse_event(0, decoded)) if parse else tuple()
    )
    return TOOL.DecodedPacketGroup(
        snes_pointer=0xC08000,
        file_pointer=0x008000,
        event_aliases=(0,),
        location_aliases=(0,),
        object_count=object_count,
        compressed_size=0,
        decompressed_size=len(decoded),
        decompressed_sha256=hashlib.sha256(decoded).hexdigest(),
        addendum_count=0,
        decoded_data=decoded,
        commands=commands,
    )


def command(opcode: int, operand_bytes: bytes = b"") -> object:
    return TOOL.PARSER.Command(0, 0, 0, opcode, operand_bytes)


class LocationEventAnimationOperandPureTests(unittest.TestCase):
    def test_cross_owner_topology_is_separate_from_physical_ownership(self) -> None:
        table_size = 2 * 32
        first = table_size
        second = table_size + 3
        rows = (
            (first, second) + (first,) * 14,
            (second, first) + (second,) * 14,
        )
        group = make_group(rows, bytes.fromhex("57 AA 02 82 03 AE"))
        topology = TOOL.analyze_packet_topology(group)
        self.assertEqual(
            topology.target_source_owners,
            ((0, 1), (0, 1)),
        )
        self.assertEqual(
            topology.counts["forward_cross_owner_entries"], 1
        )
        self.assertEqual(
            topology.counts["backward_cross_owner_entries"], 1
        )
        self.assertEqual(
            topology.counts["nonmonotone_function_pointer_objects"], 2
        )
        self.assertEqual(
            topology.counts["same_start_alias_occurrences"], 28
        )

        commands_by_owner: dict[int, list[object]] = {0: [], 1: []}
        for row in group.commands:
            commands_by_owner[row.object_id].append(row)
        marker_union = TOOL.direct_entry_marker_commands(
            commands_by_owner,
            topology,
            0,
        )
        classification = TOOL.classify_object(marker_union)
        self.assertEqual(
            classification.scope,
            "pc_and_nonpc_loader_markers",
        )
        self.assertEqual(classification.pc_operand_ids, (0,))

    def test_incoming_pc_context_fixes_outgoing_only_false_negative(self) -> None:
        table_size = 2 * 32
        first = table_size
        second = table_size + 1
        rows = (
            (first,) * 16,
            (second, first) + (second,) * 14,
        )
        group = make_group(rows, bytes.fromhex("AE 57"))
        topology = TOOL.analyze_packet_topology(group)
        commands_by_owner: dict[int, list[object]] = {0: [], 1: []}
        for row in group.commands:
            commands_by_owner[row.object_id].append(row)

        outgoing_only = TOOL.classify_object(commands_by_owner[0])
        incoming_closure = TOOL.classify_object(
            TOOL.direct_entry_marker_commands(
                commands_by_owner,
                topology,
                0,
            )
        )
        self.assertEqual(outgoing_only.scope, "no_pc_markers")
        self.assertEqual(
            topology.incoming_logical_owners[0],
            (0, 1),
        )
        self.assertEqual(
            topology.direct_entry_context_source_owners[0],
            (0, 1),
        )
        self.assertEqual(
            incoming_closure.scope,
            "pc_without_nonpc_loader_markers",
        )

    def test_forward_incoming_pc_context_is_included(self) -> None:
        table_size = 2 * 32
        first = table_size
        second = table_size + 1
        rows = (
            (first, second) + (first,) * 14,
            (second,) * 16,
        )
        group = make_group(rows, bytes.fromhex("57 AE"))
        topology = TOOL.analyze_packet_topology(group)
        commands_by_owner: dict[int, list[object]] = {0: [], 1: []}
        for row in group.commands:
            commands_by_owner[row.object_id].append(row)
        classification = TOOL.classify_object(
            TOOL.direct_entry_marker_commands(
                commands_by_owner,
                topology,
                1,
            )
        )
        self.assertEqual(
            classification.scope,
            "pc_without_nonpc_loader_markers",
        )

    def test_incoming_pc_and_npc_contexts_become_mixed_once(self) -> None:
        table_size = 3 * 32
        first = table_size
        second = table_size + 1
        third = table_size + 2
        rows = (
            (first,) * 16,
            (second, first) + (second,) * 14,
            (third, first) + (third,) * 14,
        )
        group = make_group(rows, bytes.fromhex("AE 57 82 00"))
        topology = TOOL.analyze_packet_topology(group)
        commands_by_owner: dict[int, list[object]] = {0: [], 1: [], 2: []}
        for row in group.commands:
            commands_by_owner[row.object_id].append(row)
        marker_commands = TOOL.direct_entry_marker_commands(
            commands_by_owner,
            topology,
            0,
        )
        classification = TOOL.classify_object(marker_commands)
        self.assertEqual(
            classification.scope,
            "pc_and_nonpc_loader_markers",
        )
        self.assertEqual(
            sum(row.opcode == 0x57 for row in marker_commands),
            1,
        )

    def test_repeated_aliases_and_graphics_override_do_not_inflate_or_mix(self) -> None:
        table_size = 2 * 32
        first = table_size
        second = table_size + 1
        rows = (
            (first, second) + (first,) * 14,
            (second,) * 16,
        )
        group = make_group(rows, bytes.fromhex("57 87 7F"))
        topology = TOOL.analyze_packet_topology(group)
        commands_by_owner: dict[int, list[object]] = {0: [], 1: []}
        for row in group.commands:
            commands_by_owner[row.object_id].append(row)
        marker_commands = TOOL.direct_entry_marker_commands(
            commands_by_owner,
            topology,
            0,
        )
        classification = TOOL.classify_object(marker_commands)
        self.assertEqual(
            classification.scope,
            "pc_without_nonpc_loader_markers",
        )
        self.assertEqual(
            sum(row.opcode == 0x87 for row in marker_commands),
            1,
        )

    def test_exact_packet_end_target_adds_no_source_owner(self) -> None:
        table_size = 32
        end = table_size + 1
        group = make_group(
            ((table_size,) + (end,) * 15,),
            bytes.fromhex("AE"),
        )
        topology = TOOL.analyze_packet_topology(group)
        self.assertEqual(topology.counts["packet_end_sentinels"], 15)
        self.assertEqual(
            topology.counts["in_owner_open_range_entries"], 1
        )
        self.assertEqual(topology.target_source_owners, ((0,),))

    def test_pointer_into_operand_fails_closed(self) -> None:
        table_size = 32
        group = make_group(
            ((table_size, table_size + 1) + (table_size,) * 14,),
            bytes.fromhex("AA 02"),
        )
        with self.assertRaisesRegex(
            TOOL.AnimationOperandAuditError,
            "command boundary",
        ):
            TOOL.analyze_packet_topology(group)

    def test_non_strict_function_zero_starts_fail_closed(self) -> None:
        table_size = 64
        group = make_group(
            ((table_size,) * 16, (table_size,) * 16),
            bytes.fromhex("AE"),
            parse=False,
        )
        with self.assertRaisesRegex(
            TOOL.AnimationOperandAuditError,
            "strictly increasing",
        ):
            TOOL.analyze_packet_topology(group)

    def test_pc_npc_and_graphics_markers_stay_in_distinct_roles(self) -> None:
        pc_with_graphics = TOOL.classify_object(
            (command(0x57), command(0x87, b"\x7f"))
        )
        self.assertEqual(
            pc_with_graphics.scope,
            "pc_without_nonpc_loader_markers",
        )
        self.assertIn("graphics_override", pc_with_graphics.alternate_markers)

        pc_with_npc = TOOL.classify_object(
            (command(0x57), command(0x82, b"\x00"))
        )
        self.assertEqual(
            pc_with_npc.scope,
            "pc_and_nonpc_loader_markers",
        )

    def test_generic_pc_domain_never_promotes_id_seven(self) -> None:
        valid = TOOL.classify_object((command(0x81, b"\x06"),))
        self.assertEqual(valid.pc_operand_ids, (6,))
        self.assertTrue(valid.has_pc_loader)

        candidate = TOOL.classify_object((command(0x81, b"\x07"),))
        self.assertFalse(candidate.has_pc_loader)
        self.assertEqual(candidate.pc_operand_ids, ())
        self.assertEqual(candidate.invalid_generic_markers, ((0x81, 7),))
        self.assertEqual(candidate.scope, "no_pc_markers")

    def test_animation_selector_namespaces_are_closed(self) -> None:
        self.assertEqual(TOOL._effective_selector(0xAA, b"\x22"), 0x22)
        self.assertEqual(TOOL._effective_selector(0xAB, b"\x23"), 0x23)
        self.assertEqual(
            TOOL._effective_selector(0xB7, b"\x24\xff"), 0x24
        )
        self.assertEqual(TOOL._effective_selector(0xAE, b""), 0)
        self.assertEqual(TOOL._effective_selector(0xB3, b""), 0)
        self.assertEqual(TOOL._effective_selector(0xB4, b""), 1)
        self.assertIsNone(TOOL._effective_selector(0xAC, b"\x24"))

    def test_relevant_command_widths_include_83_and_b7_second_operands(self) -> None:
        expected = {
            0x80: 2,
            0x81: 2,
            0x82: 2,
            0x83: 3,
            0x87: 2,
            0xAA: 2,
            0xAB: 2,
            0xAC: 2,
            0xAE: 1,
            0xB3: 1,
            0xB4: 1,
            0xB7: 3,
        }
        for opcode, width in expected.items():
            with self.subTest(opcode=opcode):
                self.assertEqual(TOOL.EXPECTED_COMMAND_SIZES[opcode], width)
                self.assertEqual(TOOL.PARSER.FIXED_COMMAND_SIZES[opcode], width)

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

    def test_tool_has_no_file_write_api(self) -> None:
        source = TOOL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            ".write_bytes(",
            ".write_text(",
            "open(\"w",
            "open('w",
            "--output",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("sys.stdout.buffer.write", source)

    def test_checked_report_schema_is_closed_and_public_safe(self) -> None:
        report = json.loads(REPORT_PATH.read_text(encoding="ascii"))
        TOOL.validate_public_report(report)
        serialized = json.dumps(report, sort_keys=True).lower()
        self.assertNotIn("/private/", serialized.replace("\\", "/"))
        self.assertNotIn(".sfc", serialized)
        self.assertNotIn(".smc", serialized)

        mutations: list[tuple[str, object]] = []
        unknown = copy.deepcopy(report)
        unknown["context_classification"]["unexpected"] = 1
        mutations.append(("unknown nested key", unknown))

        raw = copy.deepcopy(report)
        raw["coverage"]["ROM_BYTES"] = [0, 1, 2]
        mutations.append(("forbidden raw key", raw))

        tuple_value = copy.deepcopy(report)
        tuple_value["coverage"]["tuple_value"] = (1, 2)
        mutations.append(("non-JSON tuple", tuple_value))

        private_path = copy.deepcopy(report)
        private_path["nonclaims"][0] = "private/input/example"
        mutations.append(("private path", private_path))

        protected_extension = copy.deepcopy(report)
        protected_extension["nonclaims"][0] = "example.sfc"
        mutations.append(("protected extension", protected_extension))

        wrong_receipt = copy.deepcopy(report)
        wrong_receipt["reproduction"]["schema_shape_sha256"] = "0" * 64
        mutations.append(("wrong schema receipt", wrong_receipt))

        semantic_mutations = (
            ("read-only false", ("scope", "read_only"), False),
            ("runtime true", ("scope", "runtime_performed"), True),
            ("metadata false", ("evidence", "metadata_only"), False),
            ("installable true", ("evidence", "rom_installable"), True),
            ("wrong evidence", ("evidence", "label"), "hypothesis"),
            ("wrong status", ("status",), "pass-production-ready"),
        )
        for label, path, new_value in semantic_mutations:
            mutation = copy.deepcopy(report)
            target = mutation
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = new_value
            mutations.append((label, mutation))

        for label, mutation in mutations:
            with self.subTest(label=label), self.assertRaises(
                TOOL.AnimationOperandAuditError
            ):
                TOOL.validate_public_report(mutation)


@unittest.skipUnless(
    ROM_AVAILABLE,
    "set CT_US_REV0_ROM to the private canonical headerless ROM",
)
class LocationEventAnimationOperandRomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert ROM_PATH is not None
        cls.before_sha256 = hashlib.sha256(ROM_PATH.read_bytes()).hexdigest()
        cls.rom = ROM_PATH.read_bytes()
        cls.report = TOOL.build_report(cls.rom)
        cls.report_bytes = TOOL.canonical_report_bytes(cls.report)

    @classmethod
    def tearDownClass(cls) -> None:
        assert ROM_PATH is not None
        after_sha256 = hashlib.sha256(ROM_PATH.read_bytes()).hexdigest()
        if after_sha256 != cls.before_sha256:
            raise AssertionError("canonical ROM changed during read-only tests")

    def test_canonical_report_matches_checked_metadata_only_artifact(self) -> None:
        expected = REPORT_PATH.read_bytes()
        self.assertEqual(self.report_bytes, expected)
        self.assertEqual(len(expected), 31_731)
        self.assertEqual(
            hashlib.sha256(expected).hexdigest(),
            "d170c0d5771b84e0fbcb394dcd4151cc"
            "ef3e8c96f4bd6a80a6cc9c498f78f2c4",
        )

    def test_canonical_coverage_and_topology_are_exact(self) -> None:
        coverage = self.report["coverage"]
        self.assertEqual(coverage["decoded_packet_groups"], 462)
        self.assertEqual(coverage["objects_parsed"], 7_254)
        self.assertEqual(coverage["animation_objects"], 2_744)
        self.assertEqual(coverage["animation_commands"], 10_637)
        self.assertEqual(coverage["non_script_event_id_entries"], 24)
        self.assertEqual(
            self.report["alias_topology"]["counts"],
            dict(sorted(TOOL.EXPECTED_TOPOLOGY_COUNTS.items())),
        )
        self.assertEqual(
            self.report["alias_topology"][
                "direct_function_entry_context_counts"
            ],
            dict(sorted(TOOL.EXPECTED_DIRECT_ENTRY_CONTEXT_COUNTS.items())),
        )

    def test_canonical_marker_union_is_explicitly_not_runtime_proof(self) -> None:
        context = self.report["context_classification"]
        self.assertEqual(
            context["marker_union_counts"],
            {
                "direct_entry_pc_without_nonpc_loader_source_owners": 927,
                "direct_entry_pc_and_nonpc_loader_marker_source_owners": 23,
                "direct_entry_no_pc_marker_source_owners": 1_794,
                "direct_entry_pc_marker_union_source_owners": 950,
                "direct_entry_generic_pc_marker_union_source_owners": 422,
            },
        )
        self.assertFalse(context["runtime_reachability_resolved"])
        self.assertEqual(
            context["animation_source_owners_with_graphics_override"],
            461,
        )
        self.assertEqual(
            context["direct_entry_contexts_with_graphics_override"],
            485,
        )
        self.assertEqual(
            context["direct_entry_graphics_override_command_associations"],
            745,
        )
        self.assertFalse(
            self.report["scope"]["runtime_context_classification_complete"]
        )
        self.assertEqual(
            self.report["evidence"]["label"],
            "verified-static",
        )

    def test_one_byte_rom_drift_fails_before_corpus_decode(self) -> None:
        mutated = bytearray(self.rom)
        mutated[0] ^= 1
        with self.assertRaises(TOOL.PARSER.AuditError):
            TOOL.build_report(bytes(mutated))


if __name__ == "__main__":
    unittest.main()
