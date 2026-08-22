from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

TOOL_PATH = TOOLS_DIR / "audit_schala_player_tech_package_bank_adapter_v0.py"
REFERENCE_PATH = (
    ROOT / "references" / "schala_player_tech_package_bank_adapter_v0.json"
)
ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)

SPEC = importlib.util.spec_from_file_location(
    "audit_schala_player_tech_package_bank_adapter_v0",
    TOOL_PATH,
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


def _canonical_sources() -> tuple[TOOL.PackageSource, ...]:
    return tuple(
        TOOL.make_package_source(
            selector=selector,
            bank=0xCE,
            root_offset=0x0100 + selector * 2,
            allocation_name="CANONICAL_CD5EF0_TECH_PACKAGE",
            source_kind="canonical",
        )
        for selector in range(0x80)
    )


def _extended_source(
    selector: int = 0x80,
    *,
    bank: int = 0x42,
    root: int = 0x2000,
    name: str = "EPOCH_SYNTHETIC_PACKAGE",
) -> TOOL.PackageSource:
    return TOOL.make_package_source(
        selector=selector,
        bank=bank,
        root_offset=root,
        allocation_name=name,
        source_kind="synthetic-test",
    )


def _descriptor_bank(
    *,
    root: int = 0x2000,
    mask0: int = 0x8001,
    mask1: int = 0x4000,
    pointers: tuple[int, ...] = (0x3000, 0x3010, 0x3020),
) -> bytes:
    image = bytearray(0x10000)
    image[root : root + 4] = bytes(
        (mask0 >> 8, mask0 & 0xFF, mask1 >> 8, mask1 & 0xFF)
    )
    cursor = root + 4
    for pointer in pointers:
        image[cursor : cursor + 2] = pointer.to_bytes(2, "little")
        cursor += 2
    return bytes(image)


class SchalaPlayerTechPackageBankAdapterV0Tests(unittest.TestCase):
    def test_reference_contract_is_byte_pinned_and_closed(self) -> None:
        encoded = REFERENCE_PATH.read_bytes()
        self.assertEqual(len(encoded), TOOL.REFERENCE_SIZE)
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), TOOL.REFERENCE_SHA256)
        contract = TOOL.load_reference_contract()
        self.assertEqual(contract["schema"], TOOL.SCHEMA)
        self.assertFalse(contract["scope"]["production_installable"])
        self.assertFalse(contract["scope"]["allocation_or_hook_approval"])
        self.assertFalse(contract["scope"]["upstream_machine_code_imported"])
        self.assertEqual(
            contract["nested_script_contract"]["command_1e_status"],
            "unresolved-and-refused-for-expanded-packages",
        )

    def test_contract_rejects_duplicate_keys_and_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            duplicate = b'{"schema":"x","schema":"y"}'
            path.write_bytes(duplicate)
            with (
                mock.patch.object(TOOL, "REFERENCE_PATH", path),
                mock.patch.object(TOOL, "REFERENCE_SIZE", len(duplicate)),
                mock.patch.object(
                    TOOL,
                    "REFERENCE_SHA256",
                    hashlib.sha256(duplicate).hexdigest(),
                ),
                self.assertRaisesRegex(
                    TOOL.PackageBankAdapterError,
                    "duplicate JSON key",
                ),
            ):
                TOOL.load_reference_contract()

            drifted = REFERENCE_PATH.read_bytes() + b"\n"
            path.write_bytes(drifted)
            with (
                mock.patch.object(TOOL, "REFERENCE_PATH", path),
                self.assertRaisesRegex(
                    TOOL.PackageBankAdapterError,
                    "byte identity drifted",
                ),
            ):
                TOOL.load_reference_contract()

    def test_contract_semantic_gates_fail_closed(self) -> None:
        contract = TOOL.load_reference_contract()
        mutations = (
            ("scope", "production_installable", True),
            ("scope", "runtime_performed", True),
            ("scope", "upstream_machine_code_imported", True),
            ("namespace_contract", "selector_80_8f_binding_state", "bound"),
            ("nested_script_contract", "command_1e_status", "resolved"),
            ("candidate_helper_abi", "scratch_policy", "borrow DP 40-42"),
            ("expected_results", "candidate_epoch_package_bound_count", 1),
            (
                "expected_results",
                "host_descriptor_install_state_model_complete",
                False,
            ),
        )
        for section, key, value in mutations:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(contract)
                changed[section][key] = value
                with self.assertRaises(TOOL.PackageBankAdapterError):
                    TOOL._validate_reference_contract(changed)

    def test_strict_integer_and_symbolic_name_rules(self) -> None:
        invalid = (
            {"selector": True},
            {"bank": False},
            {"root_offset": True},
            {"selector": -1},
            {"selector": 0x100},
            {"bank": 0x100},
            {"root_offset": 0x10000},
            {"root_offset": 0xFFFF},
            {"allocation_name": ""},
            {"allocation_name": "not/a/symbol"},
            {"source_kind": "upstream-machine-code"},
            {"source_kind": "project-epoch-source"},
        )
        base = {
            "selector": 0x80,
            "bank": 0x42,
            "root_offset": 0x2000,
            "allocation_name": "EPOCH_SYNTHETIC_PACKAGE",
            "source_kind": "synthetic-test",
        }
        for mutation in invalid:
            with self.subTest(mutation=mutation):
                values = {**base, **mutation}
                with self.assertRaises(TOOL.PackageBankAdapterError):
                    TOOL.make_package_source(**values)

    def test_canonical_and_extended_source_namespaces_are_separate(self) -> None:
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "canonical package-source identity drifted",
        ):
            TOOL.make_package_source(
                selector=0x80,
                bank=0xCE,
                root_offset=0x2000,
                allocation_name="CANONICAL_CD5EF0_TECH_PACKAGE",
                source_kind="canonical",
            )
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "outside candidate Epoch package selectors",
        ):
            TOOL.make_package_source(
                selector=0x7F,
                bank=0x42,
                root_offset=0x2000,
                allocation_name="EPOCH_SYNTHETIC_PACKAGE",
                source_kind="synthetic-test",
            )

    def test_all_128_canonical_selectors_resolve_without_flattening(self) -> None:
        canonical = _canonical_sources()
        for selector in range(0x80):
            with self.subTest(selector=f"{selector:02X}"):
                source = TOOL.resolve_package_source(selector, canonical)
                self.assertEqual(source.selector, selector)
                self.assertEqual(source.bank, 0xCE)
                self.assertEqual(source.root_offset, 0x0100 + selector * 2)
                self.assertEqual(source.source_kind, "canonical")

    def test_schala_80_8f_are_explicitly_unbound_by_default(self) -> None:
        canonical = _canonical_sources()
        for selector in range(0x80, 0x90):
            with self.subTest(selector=f"{selector:02X}"), self.assertRaisesRegex(
                TOOL.UnboundPackageSelectorError,
                "explicitly unbound",
            ):
                TOOL.resolve_package_source(selector, canonical)

    def test_one_synthetic_extended_source_propagates_bank_and_root(self) -> None:
        canonical = _canonical_sources()
        extended = _extended_source(selector=0x8F, bank=0x53, root=0x4567)
        resolved = TOOL.resolve_package_source(
            0x8F,
            canonical,
            {0x8F: extended},
        )
        self.assertEqual(resolved, extended)
        self.assertEqual((resolved.bank, resolved.root_offset), (0x53, 0x4567))

    def test_extended_binding_map_rejects_wrong_domain_and_identity(self) -> None:
        canonical = _canonical_sources()
        source = _extended_source(0x80)
        bad_maps = (
            {0x7F: source},
            {0x90: source},
            {0x81: source},
            {True: source},
        )
        for bindings in bad_maps:
            with self.subTest(bindings=bindings), self.assertRaises(
                TOOL.PackageBankAdapterError
            ):
                TOOL.resolve_package_source(0x80, canonical, bindings)

    def test_focus_pulse_and_unknown_high_ids_never_alias_tech_packages(self) -> None:
        canonical = _canonical_sources()
        cases = {
            0x90: "numeric equality to Focus Pulse action ID 90 creates no mapping",
            0x91: "unassigned and refused",
            0xFE: "unassigned and refused",
            0xFF: "separate action-ID reservation is not package-selector evidence",
        }
        for selector, message in cases.items():
            with self.subTest(selector=f"{selector:02X}"), self.assertRaisesRegex(
                TOOL.PackageBankAdapterError,
                message,
            ):
                TOOL.resolve_package_source(selector, canonical)

    def test_descriptor_parser_preserves_mask_and_pointer_endianness(self) -> None:
        source = _extended_source()
        descriptor = TOOL.parse_package_descriptor(_descriptor_bank(), source)
        self.assertEqual(descriptor.mask0, 0x8001)
        self.assertEqual(descriptor.mask1, 0x4000)
        self.assertEqual(descriptor.end_offset_exclusive, 0x200A)
        self.assertEqual(
            [
                (entry.branch, entry.owner_slot, entry.bank, entry.script_offset)
                for entry in descriptor.entries
            ],
            [
                (0, 0, 0x42, 0x3000),
                (0, 15, 0x42, 0x3010),
                (1, 1, 0x42, 0x3020),
            ],
        )
        self.assertNotEqual(
            descriptor.mask0,
            int.from_bytes(bytes((0x80, 0x01)), "little"),
        )

    def test_same_low_script_offset_in_different_banks_is_distinct(self) -> None:
        image = _descriptor_bank(
            mask0=0x8000,
            mask1=0,
            pointers=(0x3456,),
        )
        first = TOOL.parse_package_descriptor(
            image,
            _extended_source(bank=0x42),
        )
        second = TOOL.parse_package_descriptor(
            image,
            _extended_source(bank=0x53),
        )
        self.assertEqual(first.entries[0].script_offset, second.entries[0].script_offset)
        self.assertNotEqual(first.entries[0].bank, second.entries[0].bank)
        self.assertNotEqual(first.entries[0], second.entries[0])

    def test_install_model_preserves_primary_and_alternate_mask_semantics(self) -> None:
        source = _extended_source(bank=0x53)
        image = _descriptor_bank()
        primary = TOOL.simulate_descriptor_install(image, source, a0b3=0)
        alternate = TOOL.simulate_descriptor_install(image, source, a0b3=0xFF)

        self.assertEqual(primary.selected_branch, 0)
        self.assertEqual(primary.pointer_cursor_final, 0x2008)
        self.assertEqual(
            [(value.owner_slot, value.script_offset) for value in primary.publications],
            [(0, 0x3000), (15, 0x3010)],
        )
        self.assertEqual(alternate.selected_branch, 1)
        self.assertEqual(alternate.pointer_cursor_final, 0x200A)
        self.assertEqual(
            [(value.owner_slot, value.script_offset) for value in alternate.publications],
            [(1, 0x3020)],
        )
        for state in (primary, alternate):
            with self.subTest(branch=state.selected_branch):
                self.assertEqual(state.descriptor_root_word, 0x2000)
                self.assertEqual(state.mask0_initial, 0x8001)
                self.assertEqual(state.mask1_initial, 0x4000)
                self.assertEqual(state.dp80_word_final, 0)
                self.assertEqual(state.dp82_word_final, 0x4000)
                self.assertEqual(state.a0b3_final, 0)
                self.assertEqual(state.accumulator_word_final, 0)
                self.assertEqual(state.x_final, state.pointer_cursor_final)
                self.assertEqual(state.y_final, 0x10)
                self.assertTrue(state.accumulator_is_8_bit)
                self.assertTrue(state.indexes_are_16_bit)
                self.assertEqual(state.direct_page_final, 0)
                self.assertEqual(state.data_bank_final, 0x7E)
                self.assertEqual(state.stack_delta, 0)
                self.assertEqual(
                    (state.flag_n_final, state.flag_z_final, state.flag_c_final),
                    (0, 1, 1),
                )

    def test_install_model_uses_exact_word_write_footprints_and_stride_four(self) -> None:
        source = _extended_source(bank=0x42)
        image = _descriptor_bank(
            mask0=0xA001,
            mask1=0,
            pointers=(0x3000, 0x3010, 0x3020),
        )
        state = TOOL.simulate_descriptor_install(image, source, a0b3=0)
        self.assertEqual(
            [
                (
                    value.owner_slot,
                    value.activation_address,
                    value.activation_word,
                    value.script_address,
                    value.bank_address,
                    value.bank_word,
                )
                for value in state.publications
            ],
            [
                (0, 0x5DAC, 0x0001, 0x5DBD, 0x5DBF, 0x0042),
                (2, 0x5DAE, 0x0001, 0x5DC5, 0x5DC7, 0x0042),
                (15, 0x5DBB, 0x0001, 0x5DF9, 0x5DFB, 0x0042),
            ],
        )

    def test_install_model_covers_every_owner_bit_and_maximum_selected_list(self) -> None:
        source = _extended_source()
        pointers = tuple(0x3000 + index * 0x10 for index in range(16))
        image = _descriptor_bank(
            mask0=0xFFFF,
            mask1=0,
            pointers=pointers,
        )
        state = TOOL.simulate_descriptor_install(image, source, a0b3=0)
        self.assertEqual(len(state.publications), 16)
        self.assertEqual(
            [value.owner_slot for value in state.publications],
            list(range(16)),
        )
        self.assertEqual(
            [value.script_offset for value in state.publications],
            list(pointers),
        )
        self.assertEqual(state.pointer_cursor_final, 0x2024)

    def test_install_model_rejects_non_integer_a0b3_and_preserves_aliases(self) -> None:
        source = _extended_source()
        image = _descriptor_bank(
            mask0=0xC000,
            mask1=0,
            pointers=(0x3456, 0x3456),
        )
        state = TOOL.simulate_descriptor_install(image, source, a0b3=0)
        self.assertEqual(
            [value.script_offset for value in state.publications],
            [0x3456, 0x3456],
        )
        for invalid in (False, True, -1, 0x100, 0xFFFF, None, "0"):
            with self.subTest(invalid=invalid), self.assertRaises(
                TOOL.PackageBankAdapterError
            ):
                TOOL.simulate_descriptor_install(image, source, a0b3=invalid)

    def test_descriptor_exact_bank_end_is_allowed_without_wrap(self) -> None:
        image = bytearray(0x10000)
        image[0xFFFC:0x10000] = b"\0\0\0\0"
        source = _extended_source(root=0xFFFC)
        descriptor = TOOL.parse_package_descriptor(bytes(image), source)
        self.assertEqual(descriptor.end_offset_exclusive, 0x10000)
        self.assertEqual(descriptor.entries, ())

    def test_descriptor_header_and_pointer_list_bank_crossing_fail_closed(self) -> None:
        image = bytes(0x10000)
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "header crosses its bank",
        ):
            TOOL.parse_package_descriptor(
                image,
                _extended_source(root=0xFFFD),
            )

        pointer_cross = bytearray(0x10000)
        pointer_cross[0xFFFC:0x10000] = bytes((0x80, 0, 0, 0))
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "pointer list crosses its bank",
        ):
            TOOL.parse_package_descriptor(
                bytes(pointer_cross),
                _extended_source(root=0xFFFC),
            )

    def test_selected_ffff_and_descriptor_overlap_fail_closed(self) -> None:
        ffff = _descriptor_bank(
            mask0=0x8000,
            mask1=0,
            pointers=(0xFFFF,),
        )
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "offset FFFF",
        ):
            TOOL.parse_package_descriptor(ffff, _extended_source())

        overlap = _descriptor_bank(
            mask0=0x8000,
            mask1=0,
            pointers=(0x2002,),
        )
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "overlaps its package descriptor",
        ):
            TOOL.parse_package_descriptor(overlap, _extended_source())

    def test_descriptor_input_must_be_one_immutable_bank(self) -> None:
        source = _extended_source()
        invalid = (bytearray(0x10000), bytes(0xFFFF), bytes(0x10001), memoryview(bytes(0x10000)))
        for image in invalid:
            with self.subTest(kind=type(image).__name__, length=len(image)):
                with self.assertRaises(TOOL.PackageBankAdapterError):
                    TOOL.parse_package_descriptor(image, source)

    def test_command_1e_is_unconditionally_refused_in_this_model(self) -> None:
        for args in ((), (0,), (_extended_source(), 0x12)):
            with self.subTest(args=args), self.assertRaisesRegex(
                TOOL.NestedSubscriptUnresolvedError,
                "fixed-bank CE",
            ):
                TOOL.resolve_command_1e_subscript(*args)

    @unittest.skipUnless(ROM_PATH.is_file(), "private canonical ROM unavailable")
    def test_canonical_preimages_and_all_128_real_sources_are_verified(self) -> None:
        contract = TOOL.load_reference_contract()
        rom = TOOL.read_canonical_rom(ROM_PATH)
        spans = TOOL.verify_canonical_spans(rom, contract)
        self.assertEqual(len(spans), 7)
        sources = TOOL.build_canonical_sources(rom)
        self.assertEqual(len(sources), 128)
        self.assertEqual(
            TOOL.canonical_identity_hashes(sources),
            {
                "bank_vector_sha256": TOOL.EXPECTED_CANONICAL_BANK_VECTOR_SHA256,
                "root_vector_sha256": TOOL.EXPECTED_CANONICAL_ROOT_VECTOR_SHA256,
                "selector_bank_root_ledger_sha256": TOOL.EXPECTED_CANONICAL_LEDGER_SHA256,
            },
        )
        self.assertTrue(all(source.bank == 0xCE for source in sources))
        self.assertEqual(
            TOOL.canonical_descriptor_geometry(rom, sources),
            TOOL.EXPECTED_CANONICAL_DESCRIPTOR_GEOMETRY,
        )

    @unittest.skipUnless(ROM_PATH.is_file(), "private canonical ROM unavailable")
    def test_metadata_report_emits_no_pointer_payload_or_binding(self) -> None:
        contract = TOOL.load_reference_contract()
        rom = TOOL.read_canonical_rom(ROM_PATH)
        report = TOOL.build_report(rom, contract)
        encoded = json.dumps(report, sort_keys=True)
        self.assertEqual(report["status"], "pass-source-only-unbound-no-installation")
        self.assertEqual(
            report["epoch_candidate_package_sources"]["bound_count"],
            0,
        )
        self.assertFalse(
            report["epoch_candidate_package_sources"][
                "same_numbered_action_mapping"
            ]
        )
        self.assertFalse(report["scope"]["production_installable"])
        self.assertFalse(report["scope"]["upstream_machine_code_imported"])
        self.assertTrue(
            report["host_descriptor_install_state"][
                "complete_for_declared_geometry"
            ]
        )
        self.assertFalse(
            report["host_descriptor_install_state"]["runtime_performed"]
        )
        self.assertNotIn("root_offset", encoded)
        self.assertNotIn("script_offset", encoded)
        self.assertNotIn(str(ROM_PATH), encoded)

    @unittest.skipUnless(ROM_PATH.is_file(), "private canonical ROM unavailable")
    def test_cli_is_deterministic_read_only_and_stdout_only(self) -> None:
        before = hashlib.sha256(ROM_PATH.read_bytes()).hexdigest()
        command = [sys.executable, str(TOOL_PATH), "--rom", str(ROM_PATH)]
        first = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        second = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = hashlib.sha256(ROM_PATH.read_bytes()).hexdigest()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stderr, "")
        self.assertEqual(second.stderr, "")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, TOOL.CANONICAL_ROM_SHA256)
        self.assertEqual(after, before)

    def test_wrong_rom_and_span_drift_fail_before_report(self) -> None:
        contract = TOOL.load_reference_contract()
        with self.assertRaisesRegex(
            TOOL.PackageBankAdapterError,
            "pinned canonical ROM",
        ):
            TOOL.build_report(bytes(TOOL.CANONICAL_ROM_SIZE), contract)

        if ROM_PATH.is_file():
            rom = bytearray(TOOL.read_canonical_rom(ROM_PATH))
            rom[0x014612] ^= 0x01
            with self.assertRaisesRegex(
                TOOL.PackageBankAdapterError,
                "canonical span drifted",
            ):
                TOOL.verify_canonical_spans(bytes(rom), contract)


if __name__ == "__main__":
    unittest.main()
