from __future__ import annotations

import copy
import dataclasses
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "schala_focus_attack_descriptors.py"
SPEC = importlib.util.spec_from_file_location(
    "schala_focus_attack_descriptors",
    TOOL_PATH,
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)


class SchalaFocusAttackDescriptorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.attack, cls.visuals = TOOL.build_unbound_descriptors()
        cls.attack_bytes = TOOL.encode_pc_attack_descriptor(cls.attack)
        cls.visual_table = TOOL.encode_focus_visual_table(cls.visuals)

    def test_source_identities_are_cross_validated(self) -> None:
        self.assertEqual(self.attack.logical_pc_id, 0x07)
        self.assertEqual(self.attack.basic_action_id, 0x90)
        self.assertEqual(
            [value.item_id for value in self.visuals],
            [0xE8, 0xE9, 0xEA, 0xEB],
        )
        self.assertEqual(
            [value.focus_visual_id for value in self.visuals],
            [0, 1, 2, 3],
        )

    def test_boolean_authoring_identity_is_rejected_not_coerced(self):
        content = copy.deepcopy(TOOL.items.load_content())
        content["items"][0]["focus_visual_id"] = False
        with mock.patch.object(
            TOOL.items,
            "load_content",
            return_value=content,
        ):
            with self.assertRaisesRegex(
                TOOL.FocusDescriptorError,
                "strict integers",
            ):
                TOOL.build_unbound_descriptors()

    def test_pc_attack_layout_and_hash_are_frozen(self) -> None:
        self.assertEqual(len(self.attack_bytes), 0x10)
        self.assertEqual(
            self.attack_bytes,
            bytes.fromhex("01079000000000000000000000000000"),
        )
        self.assertEqual(
            TOOL.sha256(self.attack_bytes),
            "04fe0da97fe577ce1139d4ec550e793332cc14fca2770e4d9e8c6dbf61665c70",
        )

    def test_pc_attack_round_trips(self) -> None:
        self.assertEqual(
            TOOL.decode_pc_attack_descriptor(self.attack_bytes),
            self.attack,
        )

    def test_focus_visual_layout_and_table_hash_are_frozen(self) -> None:
        self.assertEqual(len(self.visuals), 4)
        self.assertEqual(
            all(
                len(TOOL.encode_focus_visual_descriptor(value)) == 0x18
                for value in self.visuals
            ),
            True,
        )
        self.assertEqual(len(self.visual_table), 0x60)
        self.assertEqual(
            TOOL.sha256(self.visual_table),
            "087736c36206aa1c3937ac823817c1f2924ab6a662b2bdc6a19af801ee31047f",
        )

    def test_every_focus_visual_round_trips(self) -> None:
        for value in self.visuals:
            encoded = TOOL.encode_focus_visual_descriptor(value)
            self.assertEqual(
                TOOL.decode_focus_visual_descriptor(encoded),
                value,
            )

    def test_proved_branch_and_destination_order_are_explicit(self) -> None:
        self.assertEqual(
            TOOL.FOCUS_BRANCH_ORDER,
            (
                "noncritical_9930_zero",
                "noncritical_9930_nonzero",
                "critical_ae9b_bit80",
            ),
        )
        self.assertEqual(
            TOOL.FOCUS_WRAM_DESTINATION_ORDER,
            ("7E987A", "7E987B", "7E987E", "7E9881", "7E9884"),
        )

    def test_focus_visual_table_round_trips_and_rejects_shape_drift(self):
        self.assertEqual(
            TOOL.decode_focus_visual_table(self.visual_table),
            self.visuals,
        )
        bad_tables = (
            self.visuals[:-1],
            self.visuals + (self.visuals[-1],),
            tuple(reversed(self.visuals)),
            (
                self.visuals[0],
                self.visuals[0],
                self.visuals[2],
                self.visuals[3],
            ),
        )
        for values in bad_tables:
            with self.subTest(values=values):
                with self.assertRaises(TOOL.FocusDescriptorError):
                    TOOL.encode_focus_visual_table(values)
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_focus_visual_table(list(self.visuals))

    def test_boundary_contracts_are_hash_gated_and_cross_validated(self):
        self.assertEqual(
            TOOL.validate_boundary_contracts(),
            {
                "pc7_attack_adapter_boundaries_sha256": (
                    "f89bbfce542bb16944b62bc00822e7f8348acb794bedd149"
                    "f38e7dd02c78caf7"
                ),
                "schala_focus_pulse_adapter_boundaries_sha256": (
                    "544ae648957407e2992e1e780f5831e55243a4cb88413727"
                    "269bda40ce605318"
                ),
            },
        )
        with mock.patch.object(
            TOOL,
            "FOCUS_BOUNDARY_SHA256",
            "0" * 64,
        ):
            with self.assertRaisesRegex(
                TOOL.FocusDescriptorError,
                "hash drifted",
            ):
                TOOL.validate_boundary_contracts()

    def test_pc_attack_rejects_every_runtime_scalar(self) -> None:
        mutations = (
            {"binding_state": 1},
            {"approach_c14a48_value": 1},
            {"selector_9877_noncritical_9930_zero": 1},
            {"selector_9877_noncritical_9930_nonzero": 1},
            {"selector_9877_critical_ae9b_bit80": 1},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(TOOL.FocusDescriptorError):
                    TOOL.encode_pc_attack_descriptor(
                        dataclasses.replace(self.attack, **mutation)
                    )

    def test_pc_attack_rejects_bound_or_invalid_pointers(self) -> None:
        for field in (
            "expanded_action_record_ptr",
            "expanded_selector_binding_ptr",
        ):
            with self.subTest(field=field, value=1):
                with self.assertRaisesRegex(
                    TOOL.FocusDescriptorError,
                    "remain zero",
                ):
                    TOOL.encode_pc_attack_descriptor(
                        dataclasses.replace(self.attack, **{field: 1})
                    )
            with self.subTest(field=field, value=0x1000000):
                with self.assertRaisesRegex(
                    TOOL.FocusDescriptorError,
                    "three bytes",
                ):
                    TOOL.encode_pc_attack_descriptor(
                        dataclasses.replace(
                            self.attack,
                            **{field: 0x1000000},
                        )
                    )

    def test_focus_visual_rejects_runtime_values_and_pointer(self) -> None:
        base = self.visuals[0]
        mutations = (
            {"binding_state": 1},
            {"noncritical_9930_zero_values": b"\x01" + bytes(4)},
            {"noncritical_9930_nonzero_values": b"\x01" + bytes(4)},
            {"critical_ae9b_bit80_values": b"\x01" + bytes(4)},
            {"expanded_downstream_binding_ptr": 1},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(TOOL.FocusDescriptorError):
                    TOOL.encode_focus_visual_descriptor(
                        dataclasses.replace(base, **mutation)
                    )
        with self.assertRaisesRegex(
            TOOL.FocusDescriptorError,
            "three bytes",
        ):
            TOOL.encode_focus_visual_descriptor(
                dataclasses.replace(
                    base,
                    expanded_downstream_binding_ptr=0x1000000,
                )
            )

    def test_unknown_identity_reserved_and_length_drift_fail_closed(self):
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_pc_attack_descriptor(
                dataclasses.replace(self.attack, version=2)
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_pc_attack_descriptor(
                dataclasses.replace(self.attack, logical_pc_id=0x06)
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_pc_attack_descriptor(
                dataclasses.replace(self.attack, basic_action_id=0x91)
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_pc_attack_descriptor(
                dataclasses.replace(self.attack, reserved=b"\x00\x01")
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_focus_visual_descriptor(
                dataclasses.replace(self.visuals[0], version=2)
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_focus_visual_descriptor(
                dataclasses.replace(self.visuals[0], item_id=0xE9)
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.encode_focus_visual_descriptor(
                dataclasses.replace(
                    self.visuals[0],
                    reserved=b"\x00\x01",
                )
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.decode_pc_attack_descriptor(self.attack_bytes + b"\x00")
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.decode_focus_visual_descriptor(
                TOOL.encode_focus_visual_descriptor(self.visuals[0])
                + b"\x00"
            )

    def test_boolean_numeric_and_short_records_fail_closed(self) -> None:
        bad_attacks = (
            dataclasses.replace(self.attack, version=True),
            dataclasses.replace(self.attack, binding_state=False),
            dataclasses.replace(self.attack, logical_pc_id=-1),
            dataclasses.replace(self.attack, approach_c14a48_value=0x100),
            dataclasses.replace(
                self.attack,
                expanded_action_record_ptr=-1,
            ),
        )
        for value in bad_attacks:
            with self.subTest(value=value):
                with self.assertRaises(TOOL.FocusDescriptorError):
                    TOOL.encode_pc_attack_descriptor(value)
        bad_visuals = (
            dataclasses.replace(self.visuals[0], focus_visual_id=False),
            dataclasses.replace(self.visuals[0], item_id=0x100),
            dataclasses.replace(
                self.visuals[0],
                noncritical_9930_zero_values=bytearray(5),
            ),
            dataclasses.replace(
                self.visuals[0],
                expanded_downstream_binding_ptr=-1,
            ),
        )
        for value in bad_visuals:
            with self.subTest(value=value):
                with self.assertRaises(TOOL.FocusDescriptorError):
                    TOOL.encode_focus_visual_descriptor(value)
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.decode_pc_attack_descriptor(self.attack_bytes[:-1])
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.decode_focus_visual_descriptor(
                TOOL.encode_focus_visual_descriptor(self.visuals[0])[:-1]
            )
        with self.assertRaises(TOOL.FocusDescriptorError):
            TOOL.decode_focus_visual_table(self.visual_table[:-1])

    def test_zero_placeholders_are_never_reported_as_bound(self) -> None:
        result = TOOL.manifest()
        self.assertFalse(result["pc_attack"]["approach_value_bound"])
        self.assertFalse(result["pc_attack"]["selector_values_bound"])
        self.assertFalse(
            result["pc_attack"][
                "expanded_action_record_pointer_bound"
            ]
        )
        self.assertFalse(
            result["focus_visuals"]["branch_values_bound"]
        )
        self.assertFalse(
            result["focus_visuals"][
                "expanded_downstream_binding_pointers_bound"
            ]
        )
        self.assertEqual(
            result["runtime_use_policy"],
            "reject-before-any-wram-write",
        )

    def test_manifest_proves_source_only_uninstallable_provenance(self):
        result = TOOL.manifest()
        self.assertEqual(
            result["schema_status"],
            "selected-source-only-proposal",
        )
        self.assertEqual(result["evidence_level"], "verified-static")
        self.assertIn("layouts remain proposals", result["evidence_scope"])
        self.assertEqual(result["allocation_status"], "unbound")
        self.assertFalse(result["binary_files_emitted"])
        self.assertFalse(result["rom_installable"])
        self.assertEqual(
            result["provenance"],
            {
                "project_epoch_original_identity_data_only": True,
                "canonical_rom_accessed": False,
                "rom_bytes_imported": False,
                "npc_sprite_or_animation_bytes_imported": False,
                "copied_vanilla_records": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
