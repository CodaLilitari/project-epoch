#!/usr/bin/env python3

from __future__ import annotations

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

TOOL_PATH = TOOLS_DIR / "schala_sidecar_load_plan.py"
SPEC = importlib.util.spec_from_file_location(
    "schala_sidecar_load_plan", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

import inspect_ct_srm
import schala_recruitment_transaction
import schala_save_layout
import schala_sidecar
import schala_sidecar_v2


EPOCH_BYTES = bytes.fromhex("A4 C9 C8 BC C1 00")
SCHALA_NAME = bytes.fromhex("9C A2 9B 8A A5 AA")


def serialized_slot() -> bytes:
    result = bytearray(
        (index * 29 + 17) & 0xFF
        for index in range(inspect_ct_srm.SLOT_SIZE)
    )
    ranges = schala_save_layout.destination_ranges(
        schala_save_layout.PROJECT_EPOCH_REGIONS
    )
    compatibility_start, compatibility_end, compatibility_region = ranges[1]
    assert compatibility_region.label == "relocated_compatibility"
    result[compatibility_start:compatibility_end] = bytes(
        (index * 7 + 3) & 0xFF
        for index in range(compatibility_end - compatibility_start)
    )
    result[
        inspect_ct_srm.EPOCH_NAME_OFFSET:
        inspect_ct_srm.EPOCH_NAME_OFFSET + inspect_ct_srm.NAME_LENGTH
    ] = EPOCH_BYTES
    result[
        inspect_ct_srm.ACTIVE_PARTY_OFFSET:
        inspect_ct_srm.ACTIVE_PARTY_OFFSET + inspect_ct_srm.ROSTER_LENGTH
    ] = bytes.fromhex("00 01 02 07 83 84 85 86 80")
    result[
        schala_recruitment_transaction.SERIALIZED_JOINED_FLAGS_OFFSET
    ] |= schala_recruitment_transaction.JOINED_FLAG
    return bytes(result)


def pc07_record(seed: int = 5) -> bytes:
    return bytes((0x07,)) + bytes(
        (index * 11 + seed) & 0xFF for index in range(0x4F)
    )


def identity(
    record: bytes | None = None,
) -> schala_recruitment_transaction.PreparedPc07Identity:
    return schala_recruitment_transaction.prepare_pc07_identity(
        pc07_record() if record is None else record,
        gate_id="synthetic-non-installable-load-plan-fixture",
        evidence_level=(
            schala_recruitment_transaction.READINESS_HOST_FIXTURE
        ),
    )


def encoded_sidecar(
    slot: bytes,
    *,
    slot_number: int = 1,
    record: bytes | None = None,
    name: bytes = SCHALA_NAME,
    checksum: int | None = None,
    recruited: bool = True,
) -> bytes:
    tech_progress = 3 if recruited else 0
    quest_state = schala_sidecar.encode_quest_state(
        schala_sidecar.QuestStateV1(
            quest_unlocked=recruited,
            anchor_count=3 if recruited else 0,
            ward_resolved=recruited,
            schala_recruited=recruited,
            join_grant_applied=recruited,
        )
    )
    value = schala_sidecar_v2.prepare_sidecar_v2(
        character_record=pc07_record() if record is None else record,
        name=name,
        tech_progress=tech_progress,
        learned_mask=schala_sidecar.learned_mask_for_count(
            tech_progress
        ),
        combo_state=bytes((index * 13 + 1) & 0xFF for index in range(0x10)),
        quest_state=quest_state,
        flags=schala_sidecar.FLAG_INITIALIZED,
        sequence=0x1234,
        serialized_vanilla_slot=slot,
        slot_number=slot_number,
    )
    encoded = schala_sidecar_v2.encode_sidecar_v2(value, slot)
    if checksum is None:
        return encoded
    result = bytearray(encoded)
    result[0x0C:0x0E] = checksum.to_bytes(2, "little")
    result[
        schala_sidecar.CHECKSUM_OFFSET:
        schala_sidecar.CHECKSUM_OFFSET + 2
    ] = b"\x00\x00"
    crc = schala_sidecar.crc16_ccitt_false(result)
    result[
        schala_sidecar.CHECKSUM_OFFSET:
        schala_sidecar.CHECKSUM_OFFSET + 2
    ] = crc.to_bytes(2, "little")
    return bytes(result)


def encoded_v1_sidecar(slot: bytes) -> bytes:
    tech_progress = 3
    value = schala_sidecar.SchalaSidecarV1(
        character_record=pc07_record(),
        name=SCHALA_NAME,
        tech_progress=tech_progress,
        learned_mask=schala_sidecar.learned_mask_for_count(
            tech_progress
        ),
        combo_state=bytes((index * 13 + 1) & 0xFF for index in range(0x10)),
        quest_state=schala_sidecar.encode_quest_state(
            schala_sidecar.QuestStateV1(
                quest_unlocked=True,
                anchor_count=3,
                ward_resolved=True,
                schala_recruited=True,
                join_grant_applied=True,
            )
        ),
        flags=schala_sidecar.FLAG_INITIALIZED,
        sequence=0x1234,
        vanilla_slot_checksum=inspect_ct_srm.slot_checksum(slot),
    )
    return schala_sidecar.encode_sidecar(value)


def source_image(
    *,
    slot_number: int = 1,
    slot: bytes | None = None,
    payload: bytes | None = None,
    stored_checksum: int | None = None,
    magic: int = inspect_ct_srm.SLOT_MAGIC,
) -> bytes:
    slot = serialized_slot() if slot is None else slot
    result = bytearray(b"\xFF" * inspect_ct_srm.SRAM_SIZE)
    slot_base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    result[slot_base : slot_base + inspect_ct_srm.SLOT_SIZE] = slot
    metadata_index = (slot_number - 1) * 2
    checksum = (
        inspect_ct_srm.slot_checksum(slot)
        if stored_checksum is None
        else stored_checksum
    )
    result[
        inspect_ct_srm.CHECKSUM_TABLE_OFFSET
        + metadata_index : inspect_ct_srm.CHECKSUM_TABLE_OFFSET
        + metadata_index
        + 2
    ] = checksum.to_bytes(2, "little")
    result[
        inspect_ct_srm.MAGIC_TABLE_OFFSET
        + metadata_index : inspect_ct_srm.MAGIC_TABLE_OFFSET
        + metadata_index
        + 2
    ] = magic.to_bytes(2, "little")
    if payload is not None:
        sidecar_start = schala_sidecar.slot_file_offset(slot_number)
        result[
            sidecar_start : sidecar_start + schala_sidecar.SIDECAR_SIZE
        ] = payload
    return bytes(result)


def preclear_witness(
    image: bytes, slot_number: int = 1
) -> TOOL.PreclearCompletionWitness:
    return TOOL.prepare_preclear_completion_witness(
        image,
        slot_number,
        all_live_pc07_state_cleared=True,
    )


def plan_load(
    image: bytes,
    slot_number: int,
    **kwargs: object,
) -> TOOL.SidecarLoadPlan:
    return TOOL.plan_sidecar_load(
        image,
        slot_number,
        preclear_witness=preclear_witness(image, slot_number),
        **kwargs,
    )


def validate_plan(
    value: TOOL.SidecarLoadPlan,
    image: bytes,
    slot_number: int,
) -> TOOL.SidecarLoadPlan:
    return TOOL.validate_load_plan(
        value,
        image,
        slot_number,
        preclear_witness=preclear_witness(image, slot_number),
    )


class SchalaSidecarLoadPlanTests(unittest.TestCase):
    def test_preclear_completion_witness_is_required_and_source_bound(
        self,
    ) -> None:
        slot = serialized_slot()
        image = source_image(slot=slot)
        witness = preclear_witness(image)

        self.assertEqual(witness.source_image_sha256, TOOL.sha256(image))
        self.assertEqual(witness.slot_number, 1)
        self.assertTrue(witness.all_live_pc07_state_cleared)
        self.assertEqual(
            witness.evidence_level,
            TOOL.PRECLEAR_EVIDENCE_CALLER_ASSERTED,
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            witness.slot_number = 2

        with self.assertRaisesRegex(
            TOOL.SidecarLoadPlanError, "preclear completion witness"
        ):
            TOOL.plan_sidecar_load(image, 1)
        for incomplete in (False, 1):
            with self.subTest(incomplete=incomplete):
                with self.assertRaisesRegex(
                    TOOL.SidecarLoadPlanError, "explicit complete"
                ):
                    TOOL.prepare_preclear_completion_witness(
                        image,
                        1,
                        all_live_pc07_state_cleared=incomplete,
                    )

        altered = bytearray(image)
        altered[0] ^= 0x01
        forged = dataclasses.replace(
            witness,
            source_image_sha256=TOOL.sha256(bytes(altered)),
            seal="",
        )
        forged = dataclasses.replace(
            forged, seal=TOOL._preclear_witness_seal(forged)
        )
        wrong_evidence = dataclasses.replace(
            witness,
            evidence_level="verified-runtime",
            seal="",
        )
        wrong_evidence = dataclasses.replace(
            wrong_evidence,
            seal=TOOL._preclear_witness_seal(wrong_evidence),
        )

        class WitnessSubclass(TOOL.PreclearCompletionWitness):
            pass

        polymorphic = WitnessSubclass(**dataclasses.asdict(witness))
        for source, selected_slot, candidate in (
            (bytes(altered), 1, witness),
            (image, 2, witness),
            (image, 1, forged),
            (image, 1, wrong_evidence),
            (image, 1, polymorphic),
        ):
            with self.subTest(
                source_sha=TOOL.sha256(source),
                selected_slot=selected_slot,
                candidate_type=type(candidate).__name__,
            ):
                with self.assertRaises(TOOL.SidecarLoadPlanError):
                    TOOL.plan_sidecar_load(
                        source,
                        selected_slot,
                        preclear_witness=candidate,
                    )

        plan = TOOL.plan_sidecar_load(
            image, 1, preclear_witness=witness
        )
        with self.assertRaises(TOOL.SidecarLoadPlanError):
            TOOL.validate_load_plan(plan, image, 1)
        with self.assertRaises(TOOL.SidecarLoadPlanError):
            TOOL.validate_load_plan(
                plan,
                image,
                1,
                preclear_witness=forged,
            )

    def test_uninitialized_is_exact_immutable_safe_empty(self) -> None:
        slot = serialized_slot()
        image = source_image(slot=slot)
        image_before = bytes(image)

        plan = plan_load(image, 1)

        self.assertIs(type(plan), TOOL.SafeEmpty)
        self.assertEqual(plan.classification, "uninitialized")
        self.assertEqual(image, image_before)
        self.assertEqual(plan.slot_number, 1)
        self.assertEqual(plan.source_image_sha256, TOOL.sha256(image))
        self.assertTrue(plan.preclear_required)
        self.assertTrue(plan.postload_party_required)
        self.assertEqual(
            plan.postload_party_boundary, TOOL.POSTLOAD_PARTY_BOUNDARY
        )
        self.assertEqual(
            plan.postload_party_action, TOOL.POSTLOAD_ACTION_SAFE_EMPTY
        )
        self.assertIn(
            schala_recruitment_transaction.LOGICAL_PC_ID,
            plan.serialized_party_slots,
        )
        self.assertNotIn(
            schala_recruitment_transaction.LOGICAL_PC_ID,
            plan.postload_party_slots,
        )
        self.assertEqual(
            plan.postload_joined_flags
            & schala_recruitment_transaction.JOINED_FLAG,
            0,
        )
        self.assertTrue(plan.seal)
        self.assertIs(validate_plan(plan, image, 1), plan)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.classification = "valid"

    def test_safe_empty_types_publish_no_schala_state(self) -> None:
        slot = serialized_slot()
        valid = encoded_sidecar(slot)
        invalid = bytearray(valid)
        invalid[-1] ^= 0x01
        stale_checksum = (inspect_ct_srm.slot_checksum(slot) + 1) & 0xFFFF
        cases = (
            (None, "uninitialized"),
            (bytes(invalid), "invalid"),
            (encoded_sidecar(slot, checksum=stale_checksum), "stale"),
        )
        forbidden = (
            "prepared_identity",
            "character_record",
            "schala_name",
            "tech_progress",
            "learned_mask",
            "combo_state",
            "quest_state",
            "flags",
            "sequence",
        )

        for payload, expected_status in cases:
            with self.subTest(status=expected_status):
                image = source_image(slot=slot, payload=payload)
                plan = plan_load(
                    image,
                    1,
                    prepared_identity=object(),
                )
                self.assertIs(type(plan), TOOL.SafeEmpty)
                self.assertEqual(plan.classification, expected_status)
                self.assertTrue(plan.preclear_required)
                validate_plan(plan, image, 1)
                for field in forbidden:
                    self.assertFalse(hasattr(plan, field), field)

    def test_invalid_vanilla_magic_or_checksum_is_safe_empty(self) -> None:
        slot = serialized_slot()
        payload = encoded_sidecar(slot)
        computed = inspect_ct_srm.slot_checksum(slot)
        cases = (
            source_image(slot=slot, payload=payload, magic=0),
            source_image(
                slot=slot,
                payload=payload,
                stored_checksum=(computed + 1) & 0xFFFF,
            ),
        )
        for image in cases:
            with self.subTest(image_sha=TOOL.sha256(image)):
                with mock.patch.object(
                    TOOL.schala_sidecar_v2,
                    "classify_versioned_sidecar",
                    side_effect=AssertionError(
                        "invalid vanilla must not classify a sidecar"
                    ),
                ):
                    plan = plan_load(
                        image, 1, prepared_identity=identity()
                    )
                    self.assertIs(type(plan), TOOL.SafeEmpty)
                    self.assertEqual(
                        plan.classification, "invalid-vanilla"
                    )
                    self.assertTrue(plan.preclear_required)
                    self.assertFalse(plan.postload_party_required)
                    self.assertEqual(
                        plan.postload_party_boundary,
                        TOOL.NO_PARTY_WRITE_BOUNDARY,
                    )
                    self.assertEqual(
                        plan.postload_party_action,
                        TOOL.POSTLOAD_ACTION_NO_COPY,
                    )
                    self.assertIsNone(plan.postload_party_slots)
                    self.assertIsNone(plan.postload_joined_flags)
                    self.assertFalse(hasattr(plan, "character_record"))
                    validate_plan(plan, image, 1)

    def test_invalid_vanilla_never_emits_an_actionable_party_target(
        self,
    ) -> None:
        slot = bytearray(serialized_slot())
        start = inspect_ct_srm.ACTIVE_PARTY_OFFSET
        slot[start:start + inspect_ct_srm.ROSTER_LENGTH] = bytes.fromhex(
            "FF 08 07 83 84 85 86 81 82"
        )
        slot = bytes(slot)
        image = source_image(slot=slot, magic=0)

        plan = plan_load(image, 1)

        self.assertIs(type(plan), TOOL.SafeEmpty)
        self.assertEqual(plan.classification, "invalid-vanilla")
        self.assertFalse(plan.postload_party_required)
        self.assertIsNone(plan.postload_party_slots)
        self.assertIsNone(plan.postload_joined_flags)
        self.assertEqual(
            plan.postload_party_action, TOOL.POSTLOAD_ACTION_NO_COPY
        )
        validate_plan(plan, image, 1)

    def test_valid_v2_with_roster_disagreement_is_safe_empty(self) -> None:
        slot = bytearray(serialized_slot())
        roster_start = inspect_ct_srm.ACTIVE_PARTY_OFFSET
        roster_end = roster_start + inspect_ct_srm.ROSTER_LENGTH
        slot[roster_start:roster_end] = bytes.fromhex(
            "00 01 02 87 83 84 85 86 80"
        )
        slot[
            schala_recruitment_transaction.SERIALIZED_JOINED_FLAGS_OFFSET
        ] &= ~schala_recruitment_transaction.JOINED_FLAG
        slot = bytes(slot)
        payload = encoded_sidecar(slot)
        image = source_image(slot=slot, payload=payload)

        plan = plan_load(
            image, 1, prepared_identity=object()
        )

        self.assertIs(type(plan), TOOL.SafeEmpty)
        self.assertEqual(plan.classification, "state-inconsistent")
        self.assertIn("requires exact PC $07 once", plan.detail)
        self.assertEqual(
            plan.postload_party_action, TOOL.POSTLOAD_ACTION_SAFE_EMPTY
        )
        self.assertNotIn(0x07, plan.postload_party_slots)
        self.assertEqual(
            plan.postload_joined_flags
            & schala_recruitment_transaction.JOINED_FLAG,
            0,
        )
        self.assertFalse(hasattr(plan, "character_record"))
        validate_plan(plan, image, 1)

    def test_valid_unrecruited_v2_requires_empty_pc07_party_state(
        self,
    ) -> None:
        slot = bytearray(serialized_slot())
        roster_start = inspect_ct_srm.ACTIVE_PARTY_OFFSET
        roster_end = roster_start + inspect_ct_srm.ROSTER_LENGTH
        slot[roster_start:roster_end] = bytes.fromhex(
            "00 01 02 87 83 84 85 86 80"
        )
        slot[
            schala_recruitment_transaction.SERIALIZED_JOINED_FLAGS_OFFSET
        ] &= ~schala_recruitment_transaction.JOINED_FLAG
        slot = bytes(slot)
        payload = encoded_sidecar(slot, recruited=False)
        image = source_image(slot=slot, payload=payload)

        plan = plan_load(
            image, 1, prepared_identity=identity()
        )

        self.assertIs(type(plan), TOOL.PreparedLoad)
        self.assertEqual(plan.tech_progress, 0)
        self.assertEqual(plan.learned_mask, 0)
        self.assertNotIn(0x07, plan.postload_party_slots)
        self.assertEqual(
            plan.postload_joined_flags
            & schala_recruitment_transaction.JOINED_FLAG,
            0,
        )
        validate_plan(plan, image, 1)

    def test_valid_v2_rejects_malformed_serialized_party_shape(
        self,
    ) -> None:
        cases = (
            bytes.fromhex("00 00 02 07 83 84 85 86 80"),
            bytes.fromhex("00 01 40 07 83 84 85 86 80"),
        )
        for roster in cases:
            with self.subTest(roster=roster.hex()):
                slot = bytearray(serialized_slot())
                start = inspect_ct_srm.ACTIVE_PARTY_OFFSET
                slot[start:start + inspect_ct_srm.ROSTER_LENGTH] = roster
                slot = bytes(slot)
                image = source_image(
                    slot=slot, payload=encoded_sidecar(slot)
                )

                plan = plan_load(
                    image, 1, prepared_identity=identity()
                )

                self.assertIs(type(plan), TOOL.SafeEmpty)
                self.assertEqual(plan.classification, "state-inconsistent")
                self.assertFalse(hasattr(plan, "character_record"))
                validate_plan(plan, image, 1)

    def test_protection_hashes_bind_epoch_and_compatibility_without_data(self) -> None:
        slot = serialized_slot()
        image = source_image(slot=slot)
        ranges = schala_save_layout.destination_ranges(
            schala_save_layout.PROJECT_EPOCH_REGIONS
        )
        compatibility_start, compatibility_end, _ = ranges[1]
        epoch_end = (
            inspect_ct_srm.EPOCH_NAME_OFFSET + inspect_ct_srm.NAME_LENGTH
        )

        plan = plan_load(image, 1)

        self.assertEqual(
            plan.protected_compatibility_sha256,
            TOOL.sha256(slot[compatibility_start:compatibility_end]),
        )
        self.assertEqual(
            plan.protected_epoch_sha256,
            TOOL.sha256(
                slot[inspect_ct_srm.EPOCH_NAME_OFFSET:epoch_end]
            ),
        )
        self.assertNotIn(EPOCH_BYTES, dataclasses.astuple(plan))
        self.assertFalse(hasattr(plan, "compatibility_bytes"))
        self.assertFalse(hasattr(plan, "epoch_name"))

    def test_valid_requires_prepared_identity(self) -> None:
        slot = serialized_slot()
        image = source_image(
            slot=slot, payload=encoded_sidecar(slot)
        )
        with self.assertRaisesRegex(
            TOOL.SidecarLoadPlanError, "exact immutable prepared PC7"
        ):
            plan_load(image, 1)

    def test_valid_rejects_identity_bound_to_another_record(self) -> None:
        slot = serialized_slot()
        other_record = pc07_record(seed=19)
        image = source_image(
            slot=slot, payload=encoded_sidecar(slot)
        )
        token = dataclasses.replace(
            identity(),
            record_sha256=schala_recruitment_transaction.sha256(
                other_record
            ),
            seal="",
        )
        token = dataclasses.replace(
            token,
            seal=schala_recruitment_transaction._prepared_identity_seal(
                token
            ),
        )
        with self.assertRaisesRegex(TOOL.SidecarLoadPlanError, "not bound"):
            plan_load(
                image,
                1,
                prepared_identity=token,
            )

    def test_valid_rejects_forged_or_polymorphic_identity(self) -> None:
        slot = serialized_slot()
        payload = encoded_sidecar(slot)
        image = source_image(slot=slot, payload=payload)
        forged = dataclasses.replace(
            identity(), record_sha256="0" * 64
        )

        class IdentitySubclass(
            schala_recruitment_transaction.PreparedPc07Identity
        ):
            pass

        polymorphic = IdentitySubclass(
            **dataclasses.asdict(identity())
        )
        arbitrary = (
            schala_recruitment_transaction.PreparedPc07Identity(
                record_sha256=(
                    schala_recruitment_transaction.sha256(pc07_record())
                ),
                gate_id="made-up-host-fixture-gate",
                evidence_level=(
                    schala_recruitment_transaction.READINESS_HOST_FIXTURE
                ),
                seal="",
            )
        )
        arbitrary = dataclasses.replace(
            arbitrary,
            seal=(
                schala_recruitment_transaction._prepared_identity_seal(
                    arbitrary
                )
            ),
        )
        for token in (forged, polymorphic, arbitrary):
            with self.subTest(token=type(token).__name__):
                with self.assertRaises(TOOL.SidecarLoadPlanError):
                    plan_load(
                        image,
                        1,
                        prepared_identity=token,
                    )

    def test_valid_returns_exact_immutable_prepared_load(self) -> None:
        slot = serialized_slot()
        record = pc07_record()
        payload = encoded_sidecar(slot, record=record)
        image = source_image(slot=slot, payload=payload)
        prepared_identity = identity(record)
        decoded = schala_sidecar_v2.decode_sidecar_v2(
            payload,
            serialized_vanilla_slot=slot,
            expected_slot_number=1,
        )

        plan = plan_load(
            image,
            1,
            prepared_identity=prepared_identity,
        )

        self.assertIs(type(plan), TOOL.PreparedLoad)
        self.assertEqual(plan.classification, "valid")
        self.assertIs(plan.prepared_identity, prepared_identity)
        self.assertEqual(plan.character_record, decoded.character_record)
        self.assertEqual(plan.schala_name, decoded.name)
        self.assertEqual(plan.tech_progress, decoded.tech_progress)
        self.assertEqual(plan.learned_mask, decoded.learned_mask)
        self.assertEqual(plan.combo_state, decoded.combo_state)
        self.assertEqual(plan.quest_state, decoded.quest_state)
        self.assertEqual(plan.flags, decoded.flags)
        self.assertEqual(plan.sequence, decoded.sequence)
        self.assertEqual(plan.sidecar_version, schala_sidecar_v2.VERSION)
        self.assertEqual(plan.binding_profile, decoded.binding_profile)
        self.assertEqual(plan.binding_digest, decoded.binding_digest)
        self.assertTrue(plan.postload_party_required)
        self.assertEqual(
            plan.postload_party_action, TOOL.POSTLOAD_ACTION_PREPARED
        )
        self.assertEqual(
            plan.postload_party_slots, plan.serialized_party_slots
        )
        self.assertEqual(
            plan.postload_joined_flags, plan.serialized_joined_flags
        )
        self.assertEqual(plan.source_image_sha256, TOOL.sha256(image))
        self.assertEqual(
            plan.serialized_vanilla_slot_sha256, TOOL.sha256(slot)
        )
        self.assertEqual(
            plan.stored_vanilla_checksum,
            inspect_ct_srm.slot_checksum(slot),
        )
        self.assertEqual(
            plan.computed_vanilla_checksum,
            inspect_ct_srm.slot_checksum(slot),
        )
        self.assertEqual(plan.vanilla_magic, inspect_ct_srm.SLOT_MAGIC)
        self.assertTrue(plan.preclear_required)
        self.assertEqual(plan.preclear_witness, preclear_witness(image))
        self.assertIs(validate_plan(plan, image, 1), plan)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            plan.character_record = bytes(0x50)

    def test_equal_schala_and_epoch_bytes_remain_separate(self) -> None:
        slot = serialized_slot()
        payload = encoded_sidecar(slot, name=EPOCH_BYTES)
        image = source_image(slot=slot, payload=payload)
        plan = plan_load(
            image,
            1,
            prepared_identity=identity(),
        )

        self.assertIs(type(plan), TOOL.PreparedLoad)
        self.assertEqual(plan.schala_name, EPOCH_BYTES)
        self.assertEqual(
            plan.protected_epoch_sha256, TOOL.sha256(EPOCH_BYTES)
        )
        self.assertFalse(hasattr(plan, "epoch_name"))

    def test_inputs_require_exact_immutable_bytes_and_lengths(self) -> None:
        slot = serialized_slot()
        image = source_image(slot=slot)

        class IntSubclass(int):
            pass

        class BytesSubclass(bytes):
            pass

        cases = (
            (bytearray(image), 1),
            (image[:-1], 1),
            (BytesSubclass(image), 1),
            (image, True),
            (image, IntSubclass(1)),
            (image, 0),
            (image, 4),
        )
        for image_value, slot_value in cases:
            with self.subTest(
                image_type=type(image_value).__name__,
                image_size=len(image_value),
                slot_type=type(slot_value).__name__,
                slot_value=slot_value,
            ):
                with self.assertRaises(TOOL.SidecarLoadPlanError):
                    plan_load(image_value, slot_value)

    def test_sidecar_is_selected_by_exact_slot(self) -> None:
        slot = serialized_slot()
        slot1_image = source_image(slot=slot)
        payload = encoded_sidecar(slot)
        sidecar2_start = schala_sidecar.slot_file_offset(2)
        sidecar2_image_mutable = bytearray(slot1_image)
        sidecar2_image_mutable[
            sidecar2_start:
            sidecar2_start + schala_sidecar.SIDECAR_SIZE
        ] = payload
        sidecar2_image = bytes(sidecar2_image_mutable)

        plan = plan_load(
            sidecar2_image, 1, prepared_identity=identity()
        )

        self.assertIs(type(plan), TOOL.SafeEmpty)
        self.assertEqual(plan.classification, "uninitialized")
        self.assertFalse(hasattr(plan, "character_record"))

    def test_v1_checksum_collision_does_not_prove_slot_provenance(self) -> None:
        slot1 = serialized_slot()
        slot2 = bytearray(slot1)
        slot2[0:2], slot2[2:4] = slot2[2:4], slot2[0:2]
        slot2 = bytes(slot2)
        self.assertNotEqual(slot1, slot2)
        self.assertEqual(
            inspect_ct_srm.slot_checksum(slot1),
            inspect_ct_srm.slot_checksum(slot2),
        )

        copied_payload = encoded_v1_sidecar(slot1)
        image = source_image(
            slot_number=2,
            slot=slot2,
            payload=copied_payload,
        )
        plan = plan_load(
            image,
            2,
            prepared_identity=identity(),
        )

        self.assertIs(type(plan), TOOL.SafeEmpty)
        self.assertEqual(
            plan.classification, "legacy-v1-migration-required"
        )
        self.assertFalse(hasattr(plan, "character_record"))

    def test_v2_checksum_collision_cannot_publish_after_slot_copy(
        self,
    ) -> None:
        slot1 = serialized_slot()
        slot2 = bytearray(slot1)
        slot2[0:2], slot2[2:4] = slot2[2:4], slot2[0:2]
        slot2 = bytes(slot2)
        self.assertNotEqual(slot1, slot2)
        self.assertEqual(
            inspect_ct_srm.slot_checksum(slot1),
            inspect_ct_srm.slot_checksum(slot2),
        )

        copied = bytearray(encoded_sidecar(slot1, slot_number=1))
        copied[schala_sidecar_v2.SLOT_IDENTITY_OFFSET] = 2
        copied[
            schala_sidecar.CHECKSUM_OFFSET:
            schala_sidecar.CHECKSUM_OFFSET + 2
        ] = b"\x00\x00"
        crc = schala_sidecar.crc16_ccitt_false(copied)
        copied[
            schala_sidecar.CHECKSUM_OFFSET:
            schala_sidecar.CHECKSUM_OFFSET + 2
        ] = crc.to_bytes(2, "little")
        image = source_image(
            slot_number=2,
            slot=slot2,
            payload=bytes(copied),
        )
        plan = plan_load(
            image, 2, prepared_identity=identity()
        )

        self.assertIs(type(plan), TOOL.SafeEmpty)
        self.assertEqual(plan.classification, "stale")
        self.assertIn("SHA-256", plan.detail)
        self.assertFalse(hasattr(plan, "character_record"))

    def test_validator_rejects_forged_resealed_or_polymorphic_plans(self) -> None:
        slot = serialized_slot()
        image = source_image(
            slot=slot, payload=encoded_sidecar(slot)
        )
        plan = plan_load(
            image, 1, prepared_identity=identity()
        )
        forged = dataclasses.replace(plan, tech_progress=4)
        resealed = dataclasses.replace(
            forged, seal=TOOL._plan_seal(forged)
        )

        class PreparedSubclass(TOOL.PreparedLoad):
            pass

        polymorphic = PreparedSubclass(**dataclasses.asdict(plan))
        wrong_int_type = dataclasses.replace(
            plan, slot_number=True, seal=""
        )
        wrong_bytes_type = dataclasses.replace(
            plan, character_record=bytearray(plan.character_record), seal=""
        )
        reshaped_party = bytearray(plan.serialized_party_slots)
        reshaped_party[0], reshaped_party[1] = (
            reshaped_party[1],
            reshaped_party[0],
        )
        resealed_party = dataclasses.replace(
            plan,
            serialized_party_slots=bytes(reshaped_party),
            postload_party_slots=bytes(reshaped_party),
            seal="",
        )
        resealed_party = dataclasses.replace(
            resealed_party, seal=TOOL._plan_seal(resealed_party)
        )
        preclear_not_required = dataclasses.replace(
            plan, preclear_required=False, seal=""
        )
        preclear_not_required = dataclasses.replace(
            preclear_not_required,
            seal=TOOL._plan_seal(preclear_not_required),
        )
        unknown_identity = (
            schala_recruitment_transaction.PreparedPc07Identity(
                record_sha256=plan.prepared_identity.record_sha256,
                gate_id="made-up-host-fixture-gate",
                evidence_level=(
                    schala_recruitment_transaction.READINESS_HOST_FIXTURE
                ),
                seal="",
            )
        )
        unknown_identity = dataclasses.replace(
            unknown_identity,
            seal=(
                schala_recruitment_transaction._prepared_identity_seal(
                    unknown_identity
                )
            ),
        )
        resealed_unknown_identity = dataclasses.replace(
            plan, prepared_identity=unknown_identity, seal=""
        )
        resealed_unknown_identity = dataclasses.replace(
            resealed_unknown_identity,
            seal=TOOL._plan_seal(resealed_unknown_identity),
        )
        for candidate in (
            forged,
            resealed,
            polymorphic,
            wrong_int_type,
            wrong_bytes_type,
            resealed_party,
            preclear_not_required,
            resealed_unknown_identity,
        ):
            with self.subTest(candidate=type(candidate).__name__):
                with self.assertRaises(TOOL.SidecarLoadPlanError):
                    validate_plan(candidate, image, 1)

        empty_image = source_image(slot=slot)
        empty = plan_load(empty_image, 1)
        forged_empty = dataclasses.replace(
            empty, detail="forged", seal=""
        )
        forged_empty = dataclasses.replace(
            forged_empty, seal=TOOL._plan_seal(forged_empty)
        )
        with self.assertRaises(TOOL.SidecarLoadPlanError):
            validate_plan(forged_empty, empty_image, 1)

    def test_plan_fields_expose_no_runtime_or_storage_addresses(self) -> None:
        forbidden_fragments = ("address", "offset", "pointer", "wram")
        for plan_type in (TOOL.SafeEmpty, TOOL.PreparedLoad):
            with self.subTest(plan_type=plan_type.__name__):
                for field in dataclasses.fields(plan_type):
                    lowered = field.name.lower()
                    self.assertFalse(
                        any(
                            fragment in lowered
                            for fragment in forbidden_fragments
                        ),
                        field.name,
                    )


if __name__ == "__main__":
    unittest.main()
