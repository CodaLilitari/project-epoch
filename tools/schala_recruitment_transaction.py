#!/usr/bin/env python3
"""Model Schala recruitment as a reversible, source-only host transaction.

This module emits no ROM bytes, selects no WRAM allocation, and does not make
logical PC $07 runtime-ready.  It separates four states that must not be
conflated:

* a checksum-bound persisted sidecar preimage;
* reversible live reserve staging before name acceptance;
* a caller-asserted complete join-grant commit in live state;
* a later sidecar save image rebound to the newly serialized vanilla slot.

The model is deterministic and deliberately stricter than the unsafe vanilla
full-party insertion behavior.  Runtime hooks remain unimplemented.
"""

from __future__ import annotations

import dataclasses
import hashlib
import struct
from typing import Final

import inspect_ct_srm
import schala_sidecar


LOGICAL_PC_ID: Final = 0x07
JOINED_FLAG: Final = 0x01
INACTIVE_MASK: Final = 0x80
ACTIVE_SLOT_COUNT: Final = 3
ROSTER_SLOT_COUNT: Final = 9
NAME_SIZE: Final = 6
STARTING_TECH_COUNT: Final = 3

MODE_PENDING_ACTIVE: Final = "pending-active"
MODE_PENDING_RESERVE: Final = "pending-reserve"
MODE_ALREADY_RECRUITED: Final = "already-recruited"

OUTCOME_ACTIVE: Final = "recruited-into-active-party"
OUTCOME_RESERVE: Final = "recruited-into-reserve"
OUTCOME_ALREADY: Final = "already-recruited-noop"

EFFECT_STAGE_RESERVE: Final = "stage_logical_pc_07_in_reserve"
EFFECT_STARTING_TECHS: Final = (
    "unlock_astral_pin_veil_and_crescent_wake"
)
EFFECT_GLASS_FOCUS: Final = "grant_original_glass_focus"
EFFECT_REGENT_MANTLE: Final = "grant_original_regent_mantle"
EFFECT_ACTIVE: Final = "add_logical_pc_07_to_active_party"
EFFECT_EXCHANGE: Final = "open_party_exchange_for_optional_swap"

READINESS_HOST_FIXTURE: Final = "host-fixture"
READINESS_LEVELS: Final = frozenset({READINESS_HOST_FIXTURE})
_PREPARED_IDENTITY_SEAL_DOMAIN: Final = (
    b"project-epoch-prepared-pc07-identity-v1"
)
_SYNTHETIC_PC07_TEST_RECORD_SHA256: Final = (
    "716c6468017974c190d020ba829a1966fbbc4b41590c99585904aa950247eb56"
)
TRUSTED_HOST_FIXTURE_GATES: Final = frozenset(
    {
        (
            "synthetic-non-installable-test-record",
            _SYNTHETIC_PC07_TEST_RECORD_SHA256,
        ),
        (
            "synthetic-non-installable-load-plan-fixture",
            _SYNTHETIC_PC07_TEST_RECORD_SHA256,
        ),
    }
)
SERIALIZED_JOINED_FLAGS_OFFSET: Final = 0x05AF


class RecruitmentTransactionError(ValueError):
    """Raised before a malformed or unsafe transition can be accepted."""


@dataclasses.dataclass(frozen=True)
class PartyState:
    """The vanilla nine-byte active/reserve workspace plus joined flags."""

    slots: bytes
    joined_flags: int

    @property
    def active(self) -> bytes:
        return self.slots[:ACTIVE_SLOT_COUNT]


@dataclasses.dataclass(frozen=True)
class PreparedPc07Identity:
    """Explicit evidence boundary for a particular synthetic/live PC7 record.

    ``host-fixture`` tokens allow source-model tests only.  They are not
    production approvals.  No verified-runtime PC7 record token exists yet.
    """

    record_sha256: str
    gate_id: str
    evidence_level: str
    seal: str


@dataclasses.dataclass(frozen=True)
class JoinGrantCompletionWitness:
    """Caller assertion that every one-time grant adapter completed.

    The host model can require all three assertions, but it cannot observe
    inventory, tech state, or runtime adapter success by itself.
    """

    starting_techs_applied: bool
    glass_focus_granted: bool
    regent_mantle_granted: bool

    @property
    def complete(self) -> bool:
        return (
            self.starting_techs_applied
            and self.glass_focus_granted
            and self.regent_mantle_granted
        )


@dataclasses.dataclass(frozen=True)
class RecruitmentStage:
    """A sealed, reversible live stage; never a serializable save state."""

    mode: str
    expected_vanilla_checksum: int
    original_party: PartyState
    staged_party: PartyState
    persisted_sidecar_preimage: schala_sidecar.SchalaSidecarV1
    prepared_identity: PreparedPc07Identity
    vanilla_pc_names: tuple[bytes, ...]
    epoch_name: bytes
    schala_live_name: bytes
    staging_effects: tuple[str, ...]
    seal: str


@dataclasses.dataclass(frozen=True)
class RecruitmentCommitPlan:
    """A sealed live-state target whose grant effects are not yet complete."""

    stage: RecruitmentStage
    accepted_name: bytes | None
    outcome: str
    target_party: PartyState
    required_effects: tuple[str, ...]
    post_commit_actions: tuple[str, ...]
    seal: str


@dataclasses.dataclass(frozen=True)
class LivePc07State:
    """A committed live snapshot, separate from the persisted sidecar."""

    plan: RecruitmentCommitPlan
    outcome: str
    party: PartyState
    character_record: bytes
    name: bytes
    tech_progress: int
    learned_mask: int
    combo_state: bytes
    quest_state: bytes
    persisted_sidecar_preimage: schala_sidecar.SchalaSidecarV1
    prepared_identity: PreparedPc07Identity
    vanilla_pc_names: tuple[bytes, ...]
    epoch_name: bytes
    grant_witness: JoinGrantCompletionWitness | None
    post_commit_actions: tuple[str, ...]
    seal: str


@dataclasses.dataclass(frozen=True)
class PreparedSidecarSave:
    """A host-prepared sidecar bound to supplied serialized slot bytes."""

    value: schala_sidecar.SchalaSidecarV1
    encoded: bytes
    previous_sequence: int
    serialized_vanilla_slot_sha256: str
    computed_vanilla_checksum: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_opaque_name(value: bytes, field: str) -> None:
    if type(value) is not bytes or len(value) != NAME_SIZE:
        raise RecruitmentTransactionError(
            f"{field} must be opaque bytes of exact length six"
        )


def _validate_grant_witness(value: JoinGrantCompletionWitness) -> None:
    if type(value) is not JoinGrantCompletionWitness or any(
        type(component) is not bool
        for component in (
            value.starting_techs_applied,
            value.glass_focus_granted,
            value.regent_mantle_granted,
        )
    ):
        raise RecruitmentTransactionError(
            "join-grant witness must use the exact host type and three "
            "explicit booleans"
        )


def _validate_protected_names(
    vanilla_pc_names: tuple[bytes, ...], epoch_name: bytes
) -> None:
    if type(vanilla_pc_names) is not tuple or len(vanilla_pc_names) != 7:
        raise RecruitmentTransactionError(
            "exactly seven protected vanilla PC name buffers are required"
        )
    for index, name in enumerate(vanilla_pc_names):
        _require_opaque_name(name, f"vanilla PC {index} name")
    _require_opaque_name(epoch_name, "Epoch name")


def _prepared_identity_seal(value: PreparedPc07Identity) -> str:
    if type(value) is not PreparedPc07Identity:
        raise RecruitmentTransactionError(
            "prepared PC7 identity must use the exact sealed host type"
        )
    digest = hashlib.sha256(_PREPARED_IDENTITY_SEAL_DOMAIN)
    for field in (
        value.record_sha256,
        value.gate_id,
        value.evidence_level,
    ):
        if type(field) is not str:
            raise RecruitmentTransactionError(
                "prepared PC7 identity fields must use exact text values"
            )
        encoded = field.encode("utf-8")
        digest.update(struct.pack("<H", len(encoded)))
        digest.update(encoded)
    return digest.hexdigest()


def prepare_pc07_identity(
    character_record: bytes,
    *,
    gate_id: str,
    evidence_level: str,
) -> PreparedPc07Identity:
    """Bind an explicit readiness claim to one exact PC7 record.

    This does not validate unresolved record bytes.  The only accepted level
    is ``host-fixture``.  A future production level must be backed by an
    explicit trusted hash/gate catalog before this function may accept it.
    """

    if (
        type(character_record) is not bytes
        or len(character_record) != schala_sidecar.CHARACTER_RECORD_SIZE
    ):
        raise RecruitmentTransactionError(
            "PC7 character record must be exactly $50 bytes"
        )
    if character_record[0] != LOGICAL_PC_ID:
        raise RecruitmentTransactionError(
            "prepared character record identity byte must be logical PC $07"
        )
    if type(gate_id) is not str or not gate_id.strip():
        raise RecruitmentTransactionError("record readiness gate_id is required")
    if (
        type(evidence_level) is not str
        or evidence_level != READINESS_HOST_FIXTURE
    ):
        raise RecruitmentTransactionError(
            "record readiness evidence level is unsupported"
        )
    record_sha256 = sha256(character_record)
    if (gate_id, record_sha256) not in TRUSTED_HOST_FIXTURE_GATES:
        raise RecruitmentTransactionError(
            "record readiness gate and record hash are not in the trusted "
            "host-fixture catalog"
        )
    provisional = PreparedPc07Identity(
        record_sha256=record_sha256,
        gate_id=gate_id,
        evidence_level=evidence_level,
        seal="",
    )
    return dataclasses.replace(
        provisional, seal=_prepared_identity_seal(provisional)
    )


def _validate_prepared_identity(
    character_record: bytes, value: PreparedPc07Identity
) -> None:
    if type(value) is not PreparedPc07Identity:
        raise RecruitmentTransactionError(
            "prepared PC7 identity must use the exact sealed host type"
        )
    if type(value.seal) is not str or value.seal != _prepared_identity_seal(
        value
    ):
        raise RecruitmentTransactionError(
            "prepared PC7 identity integrity seal failed"
        )
    expected = prepare_pc07_identity(
        character_record,
        gate_id=value.gate_id,
        evidence_level=value.evidence_level,
    )
    if expected != value:
        raise RecruitmentTransactionError(
            "prepared PC7 identity is not bound to this character record"
        )


def _validate_party(value: PartyState) -> None:
    if type(value) is not PartyState:
        raise RecruitmentTransactionError(
            "party state must use the exact sealed host type"
        )
    if type(value.slots) is not bytes or len(value.slots) != ROSTER_SLOT_COUNT:
        raise RecruitmentTransactionError(
            "party workspace must contain exactly nine bytes"
        )
    if type(value.joined_flags) is not int:
        raise RecruitmentTransactionError(
            "joined_flags must use the exact integer host type"
        )
    if not 0 <= value.joined_flags <= 0xFF:
        raise RecruitmentTransactionError("joined_flags must fit in one byte")

    for slot in value.slots:
        if not (0x00 <= slot <= 0x07 or 0x80 <= slot <= 0x87):
            raise RecruitmentTransactionError(
                "party bytes must be logical IDs $00-$07 or inactive $80-$87"
            )
    exact_ids = [slot for slot in value.slots if not slot & INACTIVE_MASK]
    if len(exact_ids) != len(set(exact_ids)):
        raise RecruitmentTransactionError(
            "active roster entries must not contain duplicate logical PC IDs"
        )


def _register_in_reserve(value: PartyState) -> PartyState:
    """Register exact PC7 in reserve, preferring its stale inactive cell."""

    slots = bytearray(value.slots)
    if LOGICAL_PC_ID in slots:
        return PartyState(bytes(slots), value.joined_flags | JOINED_FLAG)

    reserve_indices = range(ACTIVE_SLOT_COUNT, ROSTER_SLOT_COUNT)
    preferred = next(
        (index for index in reserve_indices if slots[index] == 0x87),
        None,
    )
    if preferred is None:
        preferred = next(
            (
                index
                for index in range(ACTIVE_SLOT_COUNT, ROSTER_SLOT_COUNT)
                if slots[index] & INACTIVE_MASK
            ),
            None,
        )
    if preferred is None:
        raise RecruitmentTransactionError(
            "no inactive reserve slot is available for logical PC $07"
        )
    slots[preferred] = LOGICAL_PC_ID
    return PartyState(bytes(slots), value.joined_flags | JOINED_FLAG)


def _move_staged_pc07_to_open_active_slot(value: PartyState) -> PartyState:
    slots = bytearray(value.slots)
    exact_indices = [
        index for index, slot in enumerate(slots) if slot == LOGICAL_PC_ID
    ]
    if len(exact_indices) != 1:
        raise RecruitmentTransactionError(
            "staged party must contain exact PC $07 exactly once"
        )
    staged_index = exact_indices[0]
    if staged_index < ACTIVE_SLOT_COUNT:
        raise RecruitmentTransactionError(
            "logical PC $07 was active before guarded insertion"
        )

    open_index = next(
        (
            index
            for index in range(ACTIVE_SLOT_COUNT)
            if slots[index] & INACTIVE_MASK
        ),
        None,
    )
    if open_index is None:
        raise RecruitmentTransactionError(
            "guarded active insertion lost its open slot"
        )
    slots[staged_index] = 0x87
    slots[open_index] = LOGICAL_PC_ID
    return PartyState(bytes(slots), value.joined_flags | JOINED_FLAG)


def _sidecar_bytes(value: schala_sidecar.SchalaSidecarV1) -> bytes:
    try:
        return schala_sidecar.encode_sidecar(value)
    except schala_sidecar.SidecarError as exc:
        raise RecruitmentTransactionError(
            f"persisted sidecar preimage is invalid: {exc}"
        ) from exc


def _hash_text(digest: "hashlib._Hash", value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(struct.pack("<H", len(encoded)))
    digest.update(encoded)


def _stage_seal(value: RecruitmentStage) -> str:
    digest = hashlib.sha256(b"project-epoch-recruitment-stage-v1")
    _hash_text(digest, value.mode)
    digest.update(struct.pack("<H", value.expected_vanilla_checksum))
    digest.update(value.original_party.slots)
    digest.update(bytes((value.original_party.joined_flags,)))
    digest.update(value.staged_party.slots)
    digest.update(bytes((value.staged_party.joined_flags,)))
    digest.update(_sidecar_bytes(value.persisted_sidecar_preimage))
    _hash_text(digest, value.prepared_identity.record_sha256)
    _hash_text(digest, value.prepared_identity.gate_id)
    _hash_text(digest, value.prepared_identity.evidence_level)
    _hash_text(digest, value.prepared_identity.seal)
    for name in value.vanilla_pc_names:
        digest.update(name)
    digest.update(value.epoch_name)
    digest.update(value.schala_live_name)
    for effect in value.staging_effects:
        _hash_text(digest, effect)
    return digest.hexdigest()


def _validate_stable_sidecar_party(
    sidecar: schala_sidecar.SchalaSidecarV1,
    party: PartyState,
) -> bool:
    """Validate stable recruited/unrecruited agreement and return recruited."""

    quest = schala_sidecar.decode_quest_state(sidecar.quest_state)
    pc07_count = party.slots.count(LOGICAL_PC_ID)
    joined = bool(party.joined_flags & JOINED_FLAG)
    if quest.schala_recruited:
        if not quest.join_grant_applied:
            raise RecruitmentTransactionError(
                "recruited sidecar lacks the one-time join-grant guard"
            )
        if pc07_count != 1 or not joined:
            raise RecruitmentTransactionError(
                "recruited sidecar is not synchronized with exact PC7 and bit $01"
            )
        if sidecar.tech_progress < STARTING_TECH_COUNT:
            raise RecruitmentTransactionError(
                "recruited sidecar lacks the three starting single techs"
            )
        return True

    if quest.join_grant_applied:
        raise RecruitmentTransactionError(
            "unrecruited sidecar carries the join-grant guard"
        )
    if pc07_count or joined:
        raise RecruitmentTransactionError(
            "unrecruited sidecar conflicts with a live PC7 roster state"
        )
    if sidecar.tech_progress != 0 or sidecar.learned_mask != 0:
        raise RecruitmentTransactionError(
            "unrecruited sidecar must not carry Schala single-tech progress"
        )
    return False


def _validate_stage(value: RecruitmentStage) -> None:
    if type(value) is not RecruitmentStage:
        raise RecruitmentTransactionError(
            "recruitment stage must use the exact sealed host type"
        )
    _validate_party(value.original_party)
    _validate_party(value.staged_party)
    _validate_protected_names(value.vanilla_pc_names, value.epoch_name)
    _require_opaque_name(value.schala_live_name, "Schala live name")
    if (
        type(value.expected_vanilla_checksum) is not int
        or not 0 <= value.expected_vanilla_checksum <= 0xFFFF
    ):
        raise RecruitmentTransactionError(
            "expected vanilla checksum must be an exact two-byte integer"
        )
    encoded = _sidecar_bytes(value.persisted_sidecar_preimage)
    loaded = schala_sidecar.classify_sidecar(
        encoded, value.expected_vanilla_checksum
    )
    if loaded.status != "valid" or loaded.value != value.persisted_sidecar_preimage:
        raise RecruitmentTransactionError(
            "stage sidecar preimage is no longer valid and checksum-bound"
        )
    _validate_prepared_identity(
        value.persisted_sidecar_preimage.character_record,
        value.prepared_identity,
    )
    if value.schala_live_name != value.persisted_sidecar_preimage.name:
        raise RecruitmentTransactionError(
            "staged Schala name must equal the persisted default preimage"
        )

    recruited = _validate_stable_sidecar_party(
        value.persisted_sidecar_preimage, value.original_party
    )
    quest = schala_sidecar.decode_quest_state(
        value.persisted_sidecar_preimage.quest_state
    )
    if recruited:
        expected_mode = MODE_ALREADY_RECRUITED
        expected_staged = value.original_party
        expected_effects: tuple[str, ...] = ()
    else:
        if not (
            quest.quest_unlocked
            and quest.anchor_count == 3
            and quest.ward_resolved
        ):
            raise RecruitmentTransactionError(
                "recruitment prerequisites are not complete"
            )
        has_open_slot = any(
            slot & INACTIVE_MASK for slot in value.original_party.active
        )
        expected_mode = (
            MODE_PENDING_ACTIVE if has_open_slot else MODE_PENDING_RESERVE
        )
        expected_staged = _register_in_reserve(value.original_party)
        expected_effects = (EFFECT_STAGE_RESERVE,)

    if value.mode != expected_mode:
        raise RecruitmentTransactionError(
            "stage mode does not match the original capacity/recruited state"
        )
    if value.staged_party != expected_staged:
        raise RecruitmentTransactionError(
            "staged party is not the exact reversible reserve derivation"
        )
    if value.staging_effects != expected_effects:
        raise RecruitmentTransactionError(
            "stage effect inventory does not match its derivation"
        )
    if not recruited:
        if value.staged_party.active != value.original_party.active:
            raise RecruitmentTransactionError(
                "reserve staging changed the active formation"
            )
        if (
            value.original_party.joined_flags ^ value.staged_party.joined_flags
        ) != JOINED_FLAG:
            raise RecruitmentTransactionError(
                "reserve staging may change only joined-mask bit $01"
            )
    if value.seal != _stage_seal(value):
        raise RecruitmentTransactionError("recruitment stage integrity seal failed")


def begin_recruitment(
    encoded_sidecar: bytes,
    *,
    expected_vanilla_checksum: int,
    party: PartyState,
    prepared_identity: PreparedPc07Identity,
    vanilla_pc_names: tuple[bytes, ...],
    epoch_name: bytes,
) -> RecruitmentStage:
    """Validate and stage live reserve state without changing persistence."""

    if type(encoded_sidecar) is not bytes:
        raise RecruitmentTransactionError(
            "encoded sidecar must use exact immutable bytes"
        )
    if (
        type(expected_vanilla_checksum) is not int
        or not 0 <= expected_vanilla_checksum <= 0xFFFF
    ):
        raise RecruitmentTransactionError(
            "expected vanilla checksum must be an exact two-byte integer"
        )
    _validate_party(party)
    _validate_protected_names(vanilla_pc_names, epoch_name)
    loaded = schala_sidecar.classify_sidecar(
        encoded_sidecar, expected_vanilla_checksum
    )
    if loaded.status != "valid" or loaded.value is None:
        raise RecruitmentTransactionError(
            f"sidecar is {loaded.status}; recruitment staging is refused"
        )
    sidecar = loaded.value
    _validate_prepared_identity(sidecar.character_record, prepared_identity)
    _require_opaque_name(sidecar.name, "persisted Schala name")

    recruited = _validate_stable_sidecar_party(sidecar, party)
    quest = schala_sidecar.decode_quest_state(sidecar.quest_state)
    if recruited:
        mode = MODE_ALREADY_RECRUITED
        staged = party
        effects: tuple[str, ...] = ()
    else:
        if not (
            quest.quest_unlocked
            and quest.anchor_count == 3
            and quest.ward_resolved
        ):
            raise RecruitmentTransactionError(
                "recruitment prerequisites are not complete"
            )
        has_open_slot = any(slot & INACTIVE_MASK for slot in party.active)
        mode = MODE_PENDING_ACTIVE if has_open_slot else MODE_PENDING_RESERVE
        staged = _register_in_reserve(party)
        effects = (EFFECT_STAGE_RESERVE,)

    provisional = RecruitmentStage(
        mode=mode,
        expected_vanilla_checksum=expected_vanilla_checksum,
        original_party=party,
        staged_party=staged,
        persisted_sidecar_preimage=sidecar,
        prepared_identity=prepared_identity,
        vanilla_pc_names=vanilla_pc_names,
        epoch_name=epoch_name,
        schala_live_name=sidecar.name,
        staging_effects=effects,
        seal="",
    )
    sealed = dataclasses.replace(provisional, seal=_stage_seal(provisional))
    _validate_stage(sealed)
    return sealed


def abort_recruitment(stage: RecruitmentStage) -> PartyState:
    """Validate the stage and return the exact live-party preimage."""

    _validate_stage(stage)
    return stage.original_party


def _plan_seal(value: RecruitmentCommitPlan) -> str:
    digest = hashlib.sha256(b"project-epoch-recruitment-plan-v1")
    _hash_text(digest, value.stage.seal)
    digest.update(b"\x00" if value.accepted_name is None else b"\x01")
    if value.accepted_name is not None:
        digest.update(value.accepted_name)
    _hash_text(digest, value.outcome)
    digest.update(value.target_party.slots)
    digest.update(bytes((value.target_party.joined_flags,)))
    for effect in value.required_effects:
        _hash_text(digest, effect)
    digest.update(b"\xFF")
    for action in value.post_commit_actions:
        _hash_text(digest, action)
    return digest.hexdigest()


def _derive_commit_plan(
    stage: RecruitmentStage, accepted_name: bytes | None
) -> RecruitmentCommitPlan:
    _validate_stage(stage)
    if stage.mode == MODE_ALREADY_RECRUITED:
        if accepted_name is not None:
            raise RecruitmentTransactionError(
                "idempotent recruited-state entry must not reopen naming"
            )
        outcome = OUTCOME_ALREADY
        target_party = stage.original_party
        required: tuple[str, ...] = ()
        post: tuple[str, ...] = ()
    else:
        if accepted_name is None:
            raise RecruitmentTransactionError(
                "pending recruitment requires an accepted independent name"
            )
        _require_opaque_name(accepted_name, "accepted Schala name")
        common = (
            EFFECT_STARTING_TECHS,
            EFFECT_GLASS_FOCUS,
            EFFECT_REGENT_MANTLE,
        )
        if stage.mode == MODE_PENDING_ACTIVE:
            outcome = OUTCOME_ACTIVE
            target_party = _move_staged_pc07_to_open_active_slot(
                stage.staged_party
            )
            required = common + (EFFECT_ACTIVE,)
            post = ()
        elif stage.mode == MODE_PENDING_RESERVE:
            outcome = OUTCOME_RESERVE
            target_party = stage.staged_party
            required = common
            post = (EFFECT_EXCHANGE,)
        else:
            raise RecruitmentTransactionError(
                f"unsupported recruitment stage mode {stage.mode!r}"
            )
    provisional = RecruitmentCommitPlan(
        stage=stage,
        accepted_name=accepted_name,
        outcome=outcome,
        target_party=target_party,
        required_effects=required,
        post_commit_actions=post,
        seal="",
    )
    return dataclasses.replace(provisional, seal=_plan_seal(provisional))


def _validate_plan(value: RecruitmentCommitPlan) -> None:
    if type(value) is not RecruitmentCommitPlan:
        raise RecruitmentTransactionError(
            "recruitment plan must use the exact sealed host type"
        )
    expected = _derive_commit_plan(value.stage, value.accepted_name)
    if value != expected:
        raise RecruitmentTransactionError(
            "recruitment commit plan is not the exact sealed derivation"
        )
    _validate_party(value.target_party)
    if value.seal != _plan_seal(value):
        raise RecruitmentTransactionError("recruitment plan integrity seal failed")


def prepare_recruitment_commit(
    stage: RecruitmentStage, accepted_name: bytes | None
) -> RecruitmentCommitPlan:
    """Build a target plan without claiming that any grant has happened."""

    plan = _derive_commit_plan(stage, accepted_name)
    _validate_plan(plan)
    return plan


def _live_seal(value: LivePc07State) -> str:
    digest = hashlib.sha256(b"project-epoch-live-pc07-v1")
    _hash_text(digest, value.plan.seal)
    _hash_text(digest, value.outcome)
    digest.update(value.party.slots)
    digest.update(bytes((value.party.joined_flags,)))
    digest.update(value.character_record)
    digest.update(value.name)
    digest.update(bytes((value.tech_progress, value.learned_mask)))
    digest.update(value.combo_state)
    digest.update(value.quest_state)
    digest.update(_sidecar_bytes(value.persisted_sidecar_preimage))
    _hash_text(digest, value.prepared_identity.record_sha256)
    _hash_text(digest, value.prepared_identity.gate_id)
    _hash_text(digest, value.prepared_identity.evidence_level)
    _hash_text(digest, value.prepared_identity.seal)
    for name in value.vanilla_pc_names:
        digest.update(name)
    digest.update(value.epoch_name)
    if value.grant_witness is None:
        digest.update(b"\x00")
    else:
        digest.update(
            bytes(
                (
                    value.grant_witness.starting_techs_applied,
                    value.grant_witness.glass_focus_granted,
                    value.grant_witness.regent_mantle_granted,
                )
            )
        )
    for action in value.post_commit_actions:
        _hash_text(digest, action)
    return digest.hexdigest()


def _derive_live_state(
    plan: RecruitmentCommitPlan,
    grant_witness: JoinGrantCompletionWitness | None,
) -> LivePc07State:
    _validate_plan(plan)
    if plan.outcome not in {OUTCOME_ACTIVE, OUTCOME_RESERVE, OUTCOME_ALREADY}:
        raise RecruitmentTransactionError("commit plan has an unknown outcome")

    sidecar = plan.stage.persisted_sidecar_preimage
    if plan.stage.mode == MODE_ALREADY_RECRUITED:
        if grant_witness is not None:
            raise RecruitmentTransactionError(
                "idempotent entry must not claim a new grant witness"
            )
        name = sidecar.name
        tech_progress = sidecar.tech_progress
        learned_mask = sidecar.learned_mask
        quest_state = sidecar.quest_state
    else:
        if grant_witness is None:
            raise RecruitmentTransactionError(
                "all three join-grant assertions are required before commit"
            )
        _validate_grant_witness(grant_witness)
        if not all(
            (
                grant_witness.starting_techs_applied,
                grant_witness.glass_focus_granted,
                grant_witness.regent_mantle_granted,
            )
        ):
            raise RecruitmentTransactionError(
                "all three join-grant assertions are required before commit"
            )
        assert plan.accepted_name is not None
        name = plan.accepted_name
        tech_progress = STARTING_TECH_COUNT
        learned_mask = schala_sidecar.learned_mask_for_count(tech_progress)
        quest = schala_sidecar.decode_quest_state(sidecar.quest_state)
        quest_state = schala_sidecar.encode_quest_state(
            dataclasses.replace(
                quest,
                schala_recruited=True,
                join_grant_applied=True,
            )
        )

    provisional = LivePc07State(
        plan=plan,
        outcome=plan.outcome,
        party=plan.target_party,
        character_record=sidecar.character_record,
        name=name,
        tech_progress=tech_progress,
        learned_mask=learned_mask,
        combo_state=sidecar.combo_state,
        quest_state=quest_state,
        persisted_sidecar_preimage=sidecar,
        prepared_identity=plan.stage.prepared_identity,
        vanilla_pc_names=plan.stage.vanilla_pc_names,
        epoch_name=plan.stage.epoch_name,
        grant_witness=grant_witness,
        post_commit_actions=plan.post_commit_actions,
        seal="",
    )
    return dataclasses.replace(provisional, seal=_live_seal(provisional))


def _validate_live_state(value: LivePc07State) -> None:
    if type(value) is not LivePc07State:
        raise RecruitmentTransactionError(
            "live PC7 state must use the exact sealed host type"
        )
    if value.outcome not in {OUTCOME_ACTIVE, OUTCOME_RESERVE, OUTCOME_ALREADY}:
        raise RecruitmentTransactionError("live state has an unknown outcome")
    expected = _derive_live_state(value.plan, value.grant_witness)
    if value != expected:
        raise RecruitmentTransactionError(
            "live PC7 state is not the exact sealed commit-plan derivation"
        )
    _validate_party(value.party)
    _validate_prepared_identity(value.character_record, value.prepared_identity)
    _validate_protected_names(value.vanilla_pc_names, value.epoch_name)
    _require_opaque_name(value.name, "live Schala name")
    quest = schala_sidecar.decode_quest_state(value.quest_state)
    if not quest.schala_recruited or not quest.join_grant_applied:
        raise RecruitmentTransactionError(
            "live committed quest flags are incomplete"
        )
    committed_sidecar_view = dataclasses.replace(
        value.persisted_sidecar_preimage,
        character_record=value.character_record,
        name=value.name,
        tech_progress=value.tech_progress,
        learned_mask=value.learned_mask,
        combo_state=value.combo_state,
        quest_state=value.quest_state,
    )
    _validate_stable_sidecar_party(committed_sidecar_view, value.party)
    if value.seal != _live_seal(value):
        raise RecruitmentTransactionError("live PC7 state integrity seal failed")


def finalize_recruitment_commit(
    plan: RecruitmentCommitPlan,
    grant_witness: JoinGrantCompletionWitness | None,
) -> LivePc07State:
    """Finalize from a complete caller-supplied grant-completion witness."""

    live_state = _derive_live_state(plan, grant_witness)
    _validate_live_state(live_state)
    return live_state


def prepare_sidecar_for_save(
    live_state: LivePc07State,
    *,
    serialized_vanilla_slot: bytes,
) -> PreparedSidecarSave:
    """Bind a committed live snapshot to exact serialized vanilla-slot bytes."""

    _validate_live_state(live_state)
    if (
        type(serialized_vanilla_slot) is not bytes
        or len(serialized_vanilla_slot) != inspect_ct_srm.SLOT_SIZE
    ):
        raise RecruitmentTransactionError(
            "serialized vanilla slot must be exact immutable $A00 bytes"
        )
    serialized_party = PartyState(
        slots=serialized_vanilla_slot[
            inspect_ct_srm.ACTIVE_PARTY_OFFSET :
            inspect_ct_srm.ACTIVE_PARTY_OFFSET
            + inspect_ct_srm.ROSTER_LENGTH
        ],
        joined_flags=serialized_vanilla_slot[SERIALIZED_JOINED_FLAGS_OFFSET],
    )
    _validate_party(serialized_party)
    new_vanilla_checksum = inspect_ct_srm.slot_checksum(
        serialized_vanilla_slot
    )
    source = live_state.persisted_sidecar_preimage
    value = dataclasses.replace(
        source,
        character_record=live_state.character_record,
        name=live_state.name,
        tech_progress=live_state.tech_progress,
        learned_mask=live_state.learned_mask,
        combo_state=live_state.combo_state,
        quest_state=live_state.quest_state,
        sequence=min(source.sequence + 1, 0xFFFF),
        vanilla_slot_checksum=new_vanilla_checksum,
    )
    _validate_stable_sidecar_party(value, serialized_party)
    encoded = schala_sidecar.encode_sidecar(value)
    decoded = schala_sidecar.decode_sidecar(
        encoded, expected_vanilla_checksum=new_vanilla_checksum
    )
    if decoded != value:
        raise AssertionError("prepared sidecar save failed canonical round trip")
    return PreparedSidecarSave(
        value=value,
        encoded=encoded,
        previous_sequence=source.sequence,
        serialized_vanilla_slot_sha256=sha256(serialized_vanilla_slot),
        computed_vanilla_checksum=new_vanilla_checksum,
    )
