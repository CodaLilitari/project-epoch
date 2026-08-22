#!/usr/bin/env python3

from __future__ import annotations

import dataclasses
import importlib.util
import itertools
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

TOOL_PATH = TOOLS_DIR / "schala_recruitment_transaction.py"
SPEC = importlib.util.spec_from_file_location(
    "schala_recruitment_transaction", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

import schala_sidecar
import inspect_ct_srm


VANILLA_NAMES = tuple(
    bytes(((index * 13 + column * 7 + 1) & 0xFF) for column in range(6))
    for index in range(7)
)
EPOCH_NAME = bytes.fromhex("A4 C9 C8 BC C1 00")
SCHALA_NAME = bytes.fromhex("9C A2 9B 8A A5 AA")
CHECKSUM = 0x91D6
SERIALIZED_ROSTER = bytes.fromhex("00 01 07 83 84 85 86 82 87")


def serialized_slot(
    *,
    roster: bytes = SERIALIZED_ROSTER,
    joined_flags: int = 0xFF,
) -> bytes:
    result = bytearray(
        (index * 17 + 9) & 0xFF for index in range(inspect_ct_srm.SLOT_SIZE)
    )
    result[
        inspect_ct_srm.ACTIVE_PARTY_OFFSET :
        inspect_ct_srm.ACTIVE_PARTY_OFFSET + inspect_ct_srm.ROSTER_LENGTH
    ] = roster
    result[TOOL.SERIALIZED_JOINED_FLAGS_OFFSET] = joined_flags
    return bytes(result)


SERIALIZED_SLOT = serialized_slot()


def synthetic_pc07_record() -> bytes:
    """Return an identity-correct but explicitly non-installable test record."""

    return bytes((0x07,)) + bytes(
        (index * 11 + 5) & 0xFF for index in range(0x4F)
    )


def identity(record: bytes | None = None) -> TOOL.PreparedPc07Identity:
    return TOOL.prepare_pc07_identity(
        synthetic_pc07_record() if record is None else record,
        gate_id="synthetic-non-installable-test-record",
        evidence_level=TOOL.READINESS_HOST_FIXTURE,
    )


def sidecar(
    *,
    recruited: bool = False,
    grant_applied: bool = False,
    checksum: int = CHECKSUM,
    record: bytes | None = None,
    name: bytes = SCHALA_NAME,
    sequence: int = 0x1234,
) -> schala_sidecar.SchalaSidecarV1:
    quest = schala_sidecar.QuestStateV1(
        quest_unlocked=True,
        anchor_count=3,
        ward_resolved=True,
        schala_recruited=recruited,
        join_grant_applied=grant_applied,
    )
    tech_count = 3 if grant_applied else 0
    return schala_sidecar.SchalaSidecarV1(
        character_record=(
            synthetic_pc07_record() if record is None else record
        ),
        name=name,
        tech_progress=tech_count,
        learned_mask=schala_sidecar.learned_mask_for_count(tech_count),
        quest_state=schala_sidecar.encode_quest_state(quest),
        flags=schala_sidecar.FLAG_INITIALIZED,
        sequence=sequence,
        vanilla_slot_checksum=checksum,
    )


def encoded(**kwargs) -> bytes:
    return schala_sidecar.encode_sidecar(sidecar(**kwargs))


def complete_witness() -> TOOL.JoinGrantCompletionWitness:
    return TOOL.JoinGrantCompletionWitness(True, True, True)


class SchalaRecruitmentTransactionTests(unittest.TestCase):
    def begin(
        self,
        party: TOOL.PartyState,
        payload: bytes | None = None,
        *,
        prepared_identity: TOOL.PreparedPc07Identity | None = None,
        vanilla_names: tuple[bytes, ...] = VANILLA_NAMES,
        epoch_name: bytes = EPOCH_NAME,
    ) -> TOOL.RecruitmentStage:
        return TOOL.begin_recruitment(
            encoded() if payload is None else payload,
            expected_vanilla_checksum=CHECKSUM,
            party=party,
            prepared_identity=(
                identity() if prepared_identity is None else prepared_identity
            ),
            vanilla_pc_names=vanilla_names,
            epoch_name=epoch_name,
        )

    def test_open_slot_stage_commit_finalize_and_save_are_separate(self):
        original = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        persisted = sidecar()
        stage = self.begin(original, schala_sidecar.encode_sidecar(persisted))
        self.assertEqual(stage.mode, TOOL.MODE_PENDING_ACTIVE)
        self.assertEqual(stage.staged_party.active, original.active)
        self.assertEqual(stage.staged_party.slots[8], 0x07)
        self.assertEqual(stage.staging_effects, (TOOL.EFFECT_STAGE_RESERVE,))
        self.assertEqual(stage.persisted_sidecar_preimage, persisted)

        accepted = bytes.fromhex("00 EF 00 EF 00 EF")
        plan = TOOL.prepare_recruitment_commit(stage, accepted)
        self.assertEqual(plan.outcome, TOOL.OUTCOME_ACTIVE)
        self.assertEqual(plan.target_party.active, bytes.fromhex("00 01 07"))
        self.assertEqual(plan.target_party.slots[8], 0x87)
        self.assertEqual(
            plan.required_effects,
            (
                TOOL.EFFECT_STARTING_TECHS,
                TOOL.EFFECT_GLASS_FOCUS,
                TOOL.EFFECT_REGENT_MANTLE,
                TOOL.EFFECT_ACTIVE,
            ),
        )
        self.assertEqual(plan.post_commit_actions, ())
        self.assertFalse(
            schala_sidecar.decode_quest_state(
                stage.persisted_sidecar_preimage.quest_state
            ).schala_recruited
        )

        live = TOOL.finalize_recruitment_commit(plan, complete_witness())
        self.assertEqual(live.name, accepted)
        self.assertEqual(live.tech_progress, 3)
        self.assertEqual(live.learned_mask, 0xE0)
        self.assertEqual(live.epoch_name, EPOCH_NAME)
        self.assertEqual(live.vanilla_pc_names, VANILLA_NAMES)
        live_quest = schala_sidecar.decode_quest_state(live.quest_state)
        self.assertTrue(live_quest.schala_recruited)
        self.assertTrue(live_quest.join_grant_applied)
        self.assertEqual(live.persisted_sidecar_preimage, persisted)

        prepared = TOOL.prepare_sidecar_for_save(
            live, serialized_vanilla_slot=SERIALIZED_SLOT
        )
        expected_checksum = inspect_ct_srm.slot_checksum(SERIALIZED_SLOT)
        self.assertEqual(prepared.previous_sequence, 0x1234)
        self.assertEqual(prepared.value.sequence, 0x1235)
        self.assertEqual(
            prepared.value.vanilla_slot_checksum, expected_checksum
        )
        self.assertEqual(prepared.computed_vanilla_checksum, expected_checksum)
        self.assertEqual(
            prepared.serialized_vanilla_slot_sha256,
            TOOL.sha256(SERIALIZED_SLOT),
        )
        self.assertEqual(prepared.value.name, accepted)
        self.assertEqual(
            schala_sidecar.decode_sidecar(
                prepared.encoded,
                expected_vanilla_checksum=expected_checksum,
            ),
            prepared.value,
        )

    def test_full_party_commit_preserves_active_and_exchange_is_next_action(self):
        original = TOOL.PartyState(
            bytes.fromhex("00 01 02 03 04 05 06 80 87"), 0xFE
        )
        stage = self.begin(original)
        self.assertEqual(stage.mode, TOOL.MODE_PENDING_RESERVE)
        self.assertEqual(stage.staged_party.active, original.active)
        self.assertEqual(stage.staged_party.slots[8], 0x07)

        plan = TOOL.prepare_recruitment_commit(stage, SCHALA_NAME)
        self.assertEqual(plan.target_party.active, original.active)
        self.assertNotIn(TOOL.EFFECT_STAGE_RESERVE, plan.required_effects)
        self.assertNotIn(TOOL.EFFECT_EXCHANGE, plan.required_effects)
        self.assertEqual(plan.post_commit_actions, (TOOL.EFFECT_EXCHANGE,))

        live = TOOL.finalize_recruitment_commit(plan, complete_witness())
        self.assertEqual(live.outcome, TOOL.OUTCOME_RESERVE)
        self.assertEqual(live.party.active, original.active)
        self.assertEqual(live.party.slots[8], 0x07)
        self.assertEqual(live.post_commit_actions, (TOOL.EFFECT_EXCHANGE,))

    def test_abort_returns_exact_party_and_leaves_persistence_unchanged(self):
        original = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        payload = encoded()
        stage = self.begin(original, payload)
        self.assertEqual(TOOL.abort_recruitment(stage), original)
        self.assertEqual(
            schala_sidecar.encode_sidecar(stage.persisted_sidecar_preimage),
            payload,
        )
        self.assertEqual(self.begin(original, payload), stage)

    def test_invalid_uninitialized_and_stale_sidecars_refuse_staging(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        cases = (
            b"\xFF" * schala_sidecar.SIDECAR_SIZE,
            b"\x00" * schala_sidecar.SIDECAR_SIZE,
            encoded(checksum=0x1234),
        )
        for payload in cases:
            with self.subTest(prefix=payload[:4]):
                with self.assertRaisesRegex(
                    TOOL.RecruitmentTransactionError,
                    "refused",
                ):
                    self.begin(party, payload)
                self.assertEqual(
                    party,
                    TOOL.PartyState(
                        bytes.fromhex("00 01 82 03 04 05 06 80 87"),
                        0xFE,
                    ),
                )

        class EvilChecksum(int):
            def __eq__(self, other: object) -> bool:
                return True

            def __ne__(self, other: object) -> bool:
                return False

        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "exact two-byte integer"
        ):
            TOOL.begin_recruitment(
                encoded(),
                expected_vanilla_checksum=EvilChecksum(0x1234),
                party=party,
                prepared_identity=identity(),
                vanilla_pc_names=VANILLA_NAMES,
                epoch_name=EPOCH_NAME,
            )

    def test_name_values_are_opaque_and_may_equal_protected_buffers(self):
        original = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        duplicate_names = (EPOCH_NAME,) * 7
        payload = encoded(name=EPOCH_NAME)
        stage = self.begin(
            original,
            payload,
            vanilla_names=duplicate_names,
            epoch_name=EPOCH_NAME,
        )
        plan = TOOL.prepare_recruitment_commit(stage, EPOCH_NAME)
        live = TOOL.finalize_recruitment_commit(plan, complete_witness())
        self.assertEqual(live.name, EPOCH_NAME)
        self.assertEqual(live.epoch_name, EPOCH_NAME)
        self.assertEqual(live.vanilla_pc_names, duplicate_names)

        class EvilNames(tuple):
            def __iter__(self):
                return iter(VANILLA_NAMES)

        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "seven protected"
        ):
            self.begin(
                original,
                vanilla_names=EvilNames((b"BAD",) * 7),
            )

    def test_only_exact_name_length_is_enforced(self):
        original = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        stage = self.begin(original)
        for invalid in (b"", b"SHORT", b"TOO-LONG"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(
                    TOOL.RecruitmentTransactionError, "exact length six"
                ):
                    TOOL.prepare_recruitment_commit(stage, invalid)

    def test_record_identity_and_explicit_readiness_are_both_required(self):
        wrong_record = bytes((0x03,)) + synthetic_pc07_record()[1:]
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "logical PC \\$07"
        ):
            identity(wrong_record)

        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        other_record = bytes((0x07,)) + bytes([0xAA] * 0x4F)
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "trusted host-fixture catalog"
        ):
            identity(other_record)
        wrong_token = dataclasses.replace(
            identity(),
            record_sha256=TOOL.sha256(other_record),
            seal="",
        )
        wrong_token = dataclasses.replace(
            wrong_token, seal=TOOL._prepared_identity_seal(wrong_token)
        )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "not bound"
        ):
            self.begin(party, prepared_identity=wrong_token)
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "trusted host-fixture catalog"
        ):
            TOOL.prepare_pc07_identity(
                synthetic_pc07_record(),
                gate_id="made-up-host-fixture-gate",
                evidence_level=TOOL.READINESS_HOST_FIXTURE,
            )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "unsupported"
        ):
            TOOL.prepare_pc07_identity(
                synthetic_pc07_record(),
                gate_id="made-up-runtime-gate",
                evidence_level="verified-runtime",
            )
        self.assertIsInstance(TOOL.READINESS_LEVELS, frozenset)
        with self.assertRaises(AttributeError):
            TOOL.READINESS_LEVELS.add("verified-runtime")

        class EvilEvidence(str):
            def __hash__(self) -> int:
                return hash(TOOL.READINESS_HOST_FIXTURE)

            def __eq__(self, other: object) -> bool:
                return True

        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "unsupported"
        ):
            TOOL.prepare_pc07_identity(
                synthetic_pc07_record(),
                gate_id="made-up-runtime-gate",
                evidence_level=EvilEvidence("verified-runtime"),
            )

        class EvilGate(str):
            def strip(self, chars: str | None = None) -> str:
                return "forged-nonempty"

        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "gate_id"
        ):
            TOOL.prepare_pc07_identity(
                synthetic_pc07_record(),
                gate_id=EvilGate(""),
                evidence_level=TOOL.READINESS_HOST_FIXTURE,
            )

        direct_forgery = TOOL.PreparedPc07Identity(
            record_sha256=TOOL.sha256(synthetic_pc07_record()),
            gate_id="made-up-host-fixture-gate",
            evidence_level=TOOL.READINESS_HOST_FIXTURE,
            seal="",
        )
        direct_forgery = dataclasses.replace(
            direct_forgery,
            seal=TOOL._prepared_identity_seal(direct_forgery),
        )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "trusted host-fixture catalog"
        ):
            self.begin(party, prepared_identity=direct_forgery)

        self.assertIsInstance(TOOL.TRUSTED_HOST_FIXTURE_GATES, frozenset)
        with self.assertRaises(AttributeError):
            TOOL.TRUSTED_HOST_FIXTURE_GATES.add(
                (
                    "forged",
                    TOOL.sha256(synthetic_pc07_record()),
                )
            )

    def test_party_rejects_out_of_namespace_inactive_bytes(self):
        for bad in (0x88, 0xFF):
            slots = bytearray.fromhex("00 01 82 03 04 05 06 80 87")
            slots[7] = bad
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                    TOOL.RecruitmentTransactionError, "\\$80-\\$87"
                ):
                    self.begin(TOOL.PartyState(bytes(slots), 0xFE))

        class EvilJoined(int):
            def __and__(self, other: object) -> int:
                return 1

        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "exact integer host type"
        ):
            self.begin(
                TOOL.PartyState(
                    bytes.fromhex("00 01 82 03 04 05 06 80 87"),
                    EvilJoined(0xFE),
                )
            )

    def test_unrecruited_roster_or_joined_bit_conflict_is_rejected(self):
        cases = (
            TOOL.PartyState(
                bytes.fromhex("00 01 82 03 04 05 06 07 87"), 0xFE
            ),
            TOOL.PartyState(
                bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFF
            ),
        )
        for party in cases:
            with self.subTest(party=party):
                with self.assertRaisesRegex(
                    TOOL.RecruitmentTransactionError, "conflicts"
                ):
                    self.begin(party)

    def test_already_recruited_entry_is_effect_free_and_idempotent(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 02 03 04 05 06 07 80"), 0xFF
        )
        persisted = sidecar(recruited=True, grant_applied=True)
        stage = self.begin(party, schala_sidecar.encode_sidecar(persisted))
        self.assertEqual(stage.mode, TOOL.MODE_ALREADY_RECRUITED)
        self.assertEqual(stage.staging_effects, ())
        plan = TOOL.prepare_recruitment_commit(stage, None)
        self.assertEqual(plan.outcome, TOOL.OUTCOME_ALREADY)
        self.assertEqual(plan.required_effects, ())
        live = TOOL.finalize_recruitment_commit(plan, None)
        self.assertEqual(live.party, party)
        self.assertEqual(live.persisted_sidecar_preimage, persisted)
        self.assertIsNone(live.grant_witness)
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "must not reopen naming"
        ):
            TOOL.prepare_recruitment_commit(stage, SCHALA_NAME)

    def test_recruited_sidecar_requires_synced_live_roster(self):
        payload = encoded(recruited=True, grant_applied=True)
        party = TOOL.PartyState(
            bytes.fromhex("00 01 02 03 04 05 06 80 87"), 0xFE
        )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "not synchronized"
        ):
            self.begin(party, payload)

    def test_every_partial_grant_witness_is_rejected(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        plan = TOOL.prepare_recruitment_commit(
            self.begin(party), SCHALA_NAME
        )
        for values in itertools.product((False, True), repeat=3):
            if all(values):
                continue
            with self.subTest(values=values):
                with self.assertRaisesRegex(
                    TOOL.RecruitmentTransactionError,
                    "all three",
                ):
                    TOOL.finalize_recruitment_commit(
                        plan, TOOL.JoinGrantCompletionWitness(*values)
                    )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "explicit booleans"
        ):
            TOOL.finalize_recruitment_commit(
                plan, TOOL.JoinGrantCompletionWitness(1, True, True)
            )

        class ForgedWitness(TOOL.JoinGrantCompletionWitness):
            @property
            def complete(self) -> bool:
                return True

        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "exact"
        ):
            TOOL.finalize_recruitment_commit(
                plan, ForgedWitness(False, True, True)
            )

    def test_forged_stage_fields_fail_revalidation(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        stage = self.begin(party)
        forged_values = (
            dataclasses.replace(stage, mode=TOOL.MODE_PENDING_RESERVE),
            dataclasses.replace(stage, schala_live_name=b"FORGED"),
            dataclasses.replace(
                stage,
                staged_party=dataclasses.replace(
                    stage.staged_party,
                    slots=bytes.fromhex("00 01 07 03 04 05 06 80 87"),
                ),
            ),
            dataclasses.replace(stage, seal="0" * 64),
        )
        for forged in forged_values:
            with self.subTest(field=forged):
                with self.assertRaises(TOOL.RecruitmentTransactionError):
                    TOOL.prepare_recruitment_commit(forged, SCHALA_NAME)
                with self.assertRaises(TOOL.RecruitmentTransactionError):
                    TOOL.abort_recruitment(forged)

    def test_forged_plan_fails_before_grant_finalization(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        plan = TOOL.prepare_recruitment_commit(
            self.begin(party), SCHALA_NAME
        )
        forged = dataclasses.replace(
            plan, required_effects=plan.required_effects[:-1]
        )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "exact sealed derivation"
        ):
            TOOL.finalize_recruitment_commit(forged, complete_witness())

        class ForgedPlan(TOOL.RecruitmentCommitPlan):
            def __eq__(self, other: object) -> bool:
                return True

            def __ne__(self, other: object) -> bool:
                return False

        forged_subclass = ForgedPlan(
            **{
                field.name: getattr(plan, field.name)
                for field in dataclasses.fields(plan)
            }
        )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "exact sealed host type"
        ):
            TOOL.finalize_recruitment_commit(
                forged_subclass, complete_witness()
            )

    def test_forged_live_fields_cannot_reach_sidecar_save_preparation(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        plan = TOOL.prepare_recruitment_commit(
            self.begin(party), SCHALA_NAME
        )
        live = TOOL.finalize_recruitment_commit(plan, complete_witness())
        alternate_party = dataclasses.replace(
            live.party,
            slots=bytes.fromhex("01 00 07 03 04 05 06 80 87"),
        )
        alternate_record = bytes((0x07,)) + bytes([0xAA] * 0x4F)
        alternate_preimage = dataclasses.replace(
            live.persisted_sidecar_preimage,
            sequence=live.persisted_sidecar_preimage.sequence + 1,
        )
        forged_values = (
            dataclasses.replace(live, outcome="forged-outcome"),
            dataclasses.replace(live, party=alternate_party),
            dataclasses.replace(live, character_record=alternate_record),
            dataclasses.replace(
                live, persisted_sidecar_preimage=alternate_preimage
            ),
            dataclasses.replace(live, quest_state=bytes(8)),
            dataclasses.replace(live, name=b"FORGED"),
            dataclasses.replace(live, tech_progress=4, learned_mask=0xF0),
        )
        for forged in forged_values:
            forged = dataclasses.replace(forged, seal="")
            forged = dataclasses.replace(
                forged, seal=TOOL._live_seal(forged)
            )
            with self.subTest(forged=forged):
                with self.assertRaises(TOOL.RecruitmentTransactionError):
                    TOOL.prepare_sidecar_for_save(
                        forged, serialized_vanilla_slot=SERIALIZED_SLOT
                    )

        class ForgedLive(TOOL.LivePc07State):
            def __eq__(self, other: object) -> bool:
                return True

            def __ne__(self, other: object) -> bool:
                return False

        forged_subclass = ForgedLive(
            **{
                field.name: (
                    b"FORGED"
                    if field.name == "name"
                    else getattr(live, field.name)
                )
                for field in dataclasses.fields(live)
            }
        )
        with self.assertRaisesRegex(
            TOOL.RecruitmentTransactionError, "exact sealed host type"
        ):
            TOOL.prepare_sidecar_for_save(
                forged_subclass, serialized_vanilla_slot=SERIALIZED_SLOT
            )

    def test_sidecar_save_requires_exact_serialized_slot_bytes(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        plan = TOOL.prepare_recruitment_commit(
            self.begin(party), SCHALA_NAME
        )
        live = TOOL.finalize_recruitment_commit(plan, complete_witness())

        class ForgedSlot(bytes):
            def __getitem__(self, key: object) -> object:
                if key == slice(
                    inspect_ct_srm.ACTIVE_PARTY_OFFSET,
                    inspect_ct_srm.ACTIVE_PARTY_OFFSET
                    + inspect_ct_srm.ROSTER_LENGTH,
                ):
                    return SERIALIZED_ROSTER
                if key == TOOL.SERIALIZED_JOINED_FLAGS_OFFSET:
                    return 0xFF
                return super().__getitem__(key)

        for invalid in (
            b"",
            SERIALIZED_SLOT[:-1],
            bytearray(SERIALIZED_SLOT),
            ForgedSlot(bytes(inspect_ct_srm.SLOT_SIZE)),
        ):
            with self.subTest(kind=type(invalid), length=len(invalid)):
                with self.assertRaisesRegex(
                    TOOL.RecruitmentTransactionError, "exact immutable"
                ):
                    TOOL.prepare_sidecar_for_save(
                        live, serialized_vanilla_slot=invalid
                    )

    def test_sidecar_save_rejects_serialized_party_disagreement(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        live = TOOL.finalize_recruitment_commit(
            TOOL.prepare_recruitment_commit(
                self.begin(party), SCHALA_NAME
            ),
            complete_witness(),
        )
        cases = {
            "zero_slot": bytes(inspect_ct_srm.SLOT_SIZE),
            "unmapped_party_bytes": bytes(
                (index * 17 + 9) & 0xFF
                for index in range(inspect_ct_srm.SLOT_SIZE)
            ),
            "missing_pc07": serialized_slot(
                roster=bytes.fromhex("00 01 82 03 04 05 06 80 87")
            ),
            "joined_bit_clear": serialized_slot(joined_flags=0xFE),
            "duplicate_pc07": serialized_slot(
                roster=bytes.fromhex("00 01 07 83 84 85 06 07 87")
            ),
        }
        for label, invalid in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(TOOL.RecruitmentTransactionError):
                    TOOL.prepare_sidecar_for_save(
                        live, serialized_vanilla_slot=invalid
                    )

    def test_save_sequence_saturates_and_source_preimage_is_unchanged(self):
        party = TOOL.PartyState(
            bytes.fromhex("00 01 82 03 04 05 06 80 87"), 0xFE
        )
        persisted = sidecar(sequence=0xFFFF)
        stage = self.begin(party, schala_sidecar.encode_sidecar(persisted))
        plan = TOOL.prepare_recruitment_commit(stage, SCHALA_NAME)
        live = TOOL.finalize_recruitment_commit(plan, complete_witness())
        prepared = TOOL.prepare_sidecar_for_save(
            live, serialized_vanilla_slot=SERIALIZED_SLOT
        )
        self.assertEqual(prepared.value.sequence, 0xFFFF)
        self.assertEqual(live.persisted_sidecar_preimage, persisted)
        self.assertEqual(persisted.vanilla_slot_checksum, CHECKSUM)


if __name__ == "__main__":
    unittest.main()
