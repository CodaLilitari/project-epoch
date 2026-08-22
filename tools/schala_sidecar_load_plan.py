#!/usr/bin/env python3
"""Prepare fail-closed, source-only plans for loading a Schala sidecar.

The planner accepts one immutable full SRAM image and an exact slot number,
validates that slot's stored checksum and magic, and then classifies only that
slot's sidecar.  It never writes the input and emits no runtime or storage
address.  Invalid vanilla slots, legacy v1 records, and uninitialized, invalid,
stale, or party-inconsistent v2 records become ``SafeEmpty`` without
publishing character, name, tech, combo, or quest data.  A valid v2 record
becomes ``PreparedLoad`` only when an existing host-fixture
``PreparedPc07Identity`` token is bound to its exact character record.

Both plan types require an exact caller-asserted completion witness bound to
the full source image and selected slot for the pre-load PC7 clear.  Because
the vanilla full loader subsequently restores roster and joined bytes, every
plan also carries an exact post-load party target.  ``SafeEmpty`` removes exact
ID $07 and clears joined bit $01; ``PreparedLoad`` is emitted only when the
serialized party already agrees with the v2 quest state.  The post-load target
must be applied after the vanilla copy and before any party consumer.

The serialized vanilla compatibility block and Epoch name remain protected
source data.  Plans bind to their hashes only; neither is exposed as Schala
state.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Final, TypeAlias

import inspect_ct_srm
import schala_recruitment_transaction
import schala_save_layout
import schala_sidecar
import schala_sidecar_v2


SAFE_EMPTY_CLASSIFICATIONS: Final = frozenset(
    {
        "invalid-vanilla",
        "uninitialized",
        "invalid",
        "stale",
        "legacy-v1-migration-required",
        "state-inconsistent",
    }
)
_VALID_CLASSIFICATION: Final = "valid"
_COMPATIBILITY_LABEL: Final = "relocated_compatibility"
_EXPECTED_COMPATIBILITY_RANGE: Final = (0x0430, 0x0480)
_SEAL_DOMAIN: Final = b"project-epoch-sidecar-load-plan-v2"
_PRECLEAR_SEAL_DOMAIN: Final = (
    b"project-epoch-sidecar-preclear-witness-v1"
)
PRECLEAR_EVIDENCE_CALLER_ASSERTED: Final = "caller-asserted-unverified"
POSTLOAD_PARTY_BOUNDARY: Final = (
    "after-vanilla-slot-copy-before-party-consumers"
)
NO_PARTY_WRITE_BOUNDARY: Final = "vanilla-validation-failed-before-copy"
POSTLOAD_ACTION_SAFE_EMPTY: Final = "sanitize-exact-pc07"
POSTLOAD_ACTION_PREPARED: Final = "preserve-sidecar-consistent-party"
POSTLOAD_ACTION_NO_COPY: Final = "abort-without-party-write"


class SidecarLoadPlanError(ValueError):
    """Raised before an unsafe or structurally ambiguous plan can be emitted."""


@dataclasses.dataclass(frozen=True, slots=True)
class PreclearCompletionWitness:
    """Caller assertion that the entire live PC7 footprint was cleared."""

    source_image_sha256: str
    slot_number: int
    all_live_pc07_state_cleared: bool
    evidence_level: str
    seal: str


@dataclasses.dataclass(frozen=True, slots=True)
class SafeEmpty:
    """A classification that authorizes no Schala state publication."""

    classification: str
    detail: str
    slot_number: int
    source_image_sha256: str
    serialized_vanilla_slot_sha256: str
    stored_vanilla_checksum: int
    computed_vanilla_checksum: int
    vanilla_magic: int
    preclear_required: bool
    preclear_witness: PreclearCompletionWitness
    protected_compatibility_sha256: str
    protected_epoch_sha256: str
    postload_party_required: bool
    postload_party_boundary: str
    serialized_party_slots: bytes
    serialized_joined_flags: int
    postload_party_slots: bytes | None
    postload_joined_flags: int | None
    postload_party_action: str
    seal: str


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedLoad:
    """Immutable Schala fields from one valid, identity-bound sidecar."""

    classification: str
    detail: str
    slot_number: int
    source_image_sha256: str
    serialized_vanilla_slot_sha256: str
    stored_vanilla_checksum: int
    computed_vanilla_checksum: int
    vanilla_magic: int
    preclear_required: bool
    preclear_witness: PreclearCompletionWitness
    protected_compatibility_sha256: str
    protected_epoch_sha256: str
    postload_party_required: bool
    postload_party_boundary: str
    serialized_party_slots: bytes
    serialized_joined_flags: int
    postload_party_slots: bytes
    postload_joined_flags: int
    postload_party_action: str
    prepared_identity: (
        schala_recruitment_transaction.PreparedPc07Identity
    )
    sidecar_version: int
    binding_profile: int
    binding_digest: bytes
    character_record: bytes
    schala_name: bytes
    tech_progress: int
    learned_mask: int
    combo_state: bytes
    quest_state: bytes
    flags: int
    sequence: int
    seal: str


SidecarLoadPlan: TypeAlias = SafeEmpty | PreparedLoad


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_exact_bytes(value: object, size: int, field: str) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise SidecarLoadPlanError(
            f"{field} must be immutable bytes of exact length 0x{size:X}"
        )
    return value


def _compatibility_range() -> tuple[int, int]:
    """Resolve and pin the non-PC compatibility range from the save layout."""

    try:
        schala_save_layout.validate_layout()
    except RuntimeError as exc:
        raise SidecarLoadPlanError(
            "Project Epoch save layout does not validate"
        ) from exc

    matches = tuple(
        (start, end)
        for start, end, region in schala_save_layout.destination_ranges(
            schala_save_layout.PROJECT_EPOCH_REGIONS
        )
        if region.label == _COMPATIBILITY_LABEL
    )
    if matches != (_EXPECTED_COMPATIBILITY_RANGE,):
        raise SidecarLoadPlanError(
            "relocated compatibility destination is not the exact protected "
            "$0430-$047F vanilla range"
        )
    return matches[0]


def _protection_hashes(serialized_vanilla_slot: bytes) -> tuple[str, str]:
    compatibility_start, compatibility_end = _compatibility_range()
    epoch_end = inspect_ct_srm.EPOCH_NAME_OFFSET + inspect_ct_srm.NAME_LENGTH
    if (
        inspect_ct_srm.SLOT_SIZE != schala_save_layout.SLOT_SIZE
        or compatibility_end > len(serialized_vanilla_slot)
        or epoch_end > len(serialized_vanilla_slot)
    ):
        raise SidecarLoadPlanError(
            "vanilla slot and Project Epoch save-layout boundaries disagree"
        )
    return (
        sha256(
            serialized_vanilla_slot[
                compatibility_start:compatibility_end
            ]
        ),
        sha256(
            serialized_vanilla_slot[
                inspect_ct_srm.EPOCH_NAME_OFFSET:epoch_end
            ]
        ),
    )


def _serialized_party(
    serialized_vanilla_slot: bytes,
) -> tuple[bytes, int]:
    start = inspect_ct_srm.ACTIVE_PARTY_OFFSET
    end = start + inspect_ct_srm.ROSTER_LENGTH
    joined_offset = (
        schala_recruitment_transaction.SERIALIZED_JOINED_FLAGS_OFFSET
    )
    if (
        end > len(serialized_vanilla_slot)
        or joined_offset >= len(serialized_vanilla_slot)
    ):
        raise SidecarLoadPlanError(
            "serialized party lies outside the selected vanilla slot"
        )
    return (
        serialized_vanilla_slot[start:end],
        serialized_vanilla_slot[joined_offset],
    )


def _safe_empty_party_target(
    serialized_party_slots: bytes,
    serialized_joined_flags: int,
) -> tuple[bytes, int]:
    """Remove only live ID $07 references restored by the vanilla loader."""

    serialized_party_slots = _require_exact_bytes(
        serialized_party_slots,
        inspect_ct_srm.ROSTER_LENGTH,
        "serialized party slots",
    )
    if (
        type(serialized_joined_flags) is not int
        or not 0 <= serialized_joined_flags <= 0xFF
    ):
        raise SidecarLoadPlanError(
            "serialized joined flags must use one exact byte"
        )
    sanitized = bytes(
        0x87
        if entry == schala_recruitment_transaction.LOGICAL_PC_ID
        else entry
        for entry in serialized_party_slots
    )
    return (
        sanitized,
        serialized_joined_flags
        & ~schala_recruitment_transaction.JOINED_FLAG,
    )


def _state_consistency_error(
    value: schala_sidecar_v2.SchalaSidecarV2,
    serialized_party_slots: bytes,
    serialized_joined_flags: int,
) -> str | None:
    """Return why a valid v2 payload cannot agree with its vanilla roster."""

    if type(value) is not schala_sidecar_v2.SchalaSidecarV2:
        raise SidecarLoadPlanError(
            "party consistency requires the exact v2 sidecar type"
        )
    invalid_entries = tuple(
        entry
        for entry in serialized_party_slots
        if not (0x00 <= entry <= 0x07 or 0x80 <= entry <= 0x87)
    )
    if invalid_entries:
        return (
            "serialized party contains values outside logical IDs $00-$07 "
            "and inactive $80-$87"
        )
    exact_ids = tuple(
        entry for entry in serialized_party_slots if entry < 0x80
    )
    if len(exact_ids) != len(set(exact_ids)):
        return "serialized party contains duplicate exact playable IDs"
    try:
        quest = schala_sidecar.decode_quest_state(value.quest_state)
    except schala_sidecar.SidecarError as exc:
        return f"v2 quest state is invalid: {exc}"

    pc07_count = serialized_party_slots.count(
        schala_recruitment_transaction.LOGICAL_PC_ID
    )
    joined = bool(
        serialized_joined_flags
        & schala_recruitment_transaction.JOINED_FLAG
    )
    if quest.schala_recruited:
        if not quest.join_grant_applied:
            return "recruited v2 state lacks the one-time join-grant guard"
        if pc07_count != 1 or not joined:
            return (
                "recruited v2 state requires exact PC $07 once and joined "
                "bit $01 set in the serialized vanilla roster"
            )
        if (
            value.tech_progress
            < schala_recruitment_transaction.STARTING_TECH_COUNT
        ):
            return (
                "recruited v2 state lacks the three starting single techs"
            )
        return None

    if quest.join_grant_applied:
        return "unrecruited v2 state carries the one-time join-grant guard"
    if pc07_count or joined:
        return (
            "unrecruited v2 state conflicts with serialized PC $07 roster "
            "or joined state"
        )
    if value.tech_progress != 0 or value.learned_mask != 0:
        return "unrecruited v2 state carries Schala single-tech progress"
    return None


def _validate_prepared_identity(
    character_record: bytes,
    prepared_identity: (
        schala_recruitment_transaction.PreparedPc07Identity | None
    ),
) -> schala_recruitment_transaction.PreparedPc07Identity:
    if (
        type(prepared_identity)
        is not schala_recruitment_transaction.PreparedPc07Identity
    ):
        raise SidecarLoadPlanError(
            "valid sidecar requires the exact immutable prepared PC7 "
            "identity type"
        )
    try:
        expected = schala_recruitment_transaction.prepare_pc07_identity(
            character_record,
            gate_id=prepared_identity.gate_id,
            evidence_level=prepared_identity.evidence_level,
        )
    except schala_recruitment_transaction.RecruitmentTransactionError as exc:
        raise SidecarLoadPlanError(
            "prepared PC7 identity is not a supported host-fixture token"
        ) from exc
    if expected != prepared_identity:
        raise SidecarLoadPlanError(
            "prepared PC7 identity is not bound to the sidecar character "
            "record"
        )
    return prepared_identity


def _hash_bytes(digest: object, value: bytes) -> None:
    if type(value) is not bytes:
        raise SidecarLoadPlanError("load plan byte field has an invalid type")
    digest.update(len(value).to_bytes(4, "little"))
    digest.update(value)


def _hash_text(digest: object, value: str) -> None:
    if type(value) is not str:
        raise SidecarLoadPlanError("load plan text field has an invalid type")
    _hash_bytes(digest, value.encode("utf-8"))


def _hash_int(digest: object, value: int) -> None:
    if type(value) is not int or not 0 <= value < 1 << 64:
        raise SidecarLoadPlanError("load plan integer field has an invalid type")
    digest.update(value.to_bytes(8, "little", signed=False))


def _preclear_witness_seal(value: PreclearCompletionWitness) -> str:
    if type(value) is not PreclearCompletionWitness:
        raise SidecarLoadPlanError(
            "preclear witness must use the exact immutable host type"
        )
    if (
        type(value.source_image_sha256) is not str
        or len(value.source_image_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value.source_image_sha256
        )
    ):
        raise SidecarLoadPlanError(
            "preclear witness source hash must be lowercase SHA-256 text"
        )
    if type(value.slot_number) is not int:
        raise SidecarLoadPlanError(
            "preclear witness slot must use an exact integer"
        )
    if type(value.all_live_pc07_state_cleared) is not bool:
        raise SidecarLoadPlanError(
            "preclear completion assertion must use an exact boolean"
        )
    if type(value.evidence_level) is not str:
        raise SidecarLoadPlanError(
            "preclear witness evidence level must use exact text"
        )
    digest = hashlib.sha256()
    _hash_bytes(digest, _PRECLEAR_SEAL_DOMAIN)
    _hash_text(digest, value.source_image_sha256)
    _hash_int(digest, value.slot_number)
    _hash_int(digest, int(value.all_live_pc07_state_cleared))
    _hash_text(digest, value.evidence_level)
    return digest.hexdigest()


def _plan_seal(value: SidecarLoadPlan) -> str:
    if type(value) not in (SafeEmpty, PreparedLoad):
        raise SidecarLoadPlanError(
            "load plan must use an exact immutable result type"
        )
    digest = hashlib.sha256()
    _hash_bytes(digest, _SEAL_DOMAIN)
    _hash_text(digest, type(value).__name__)
    _hash_text(digest, value.classification)
    _hash_text(digest, value.detail)
    _hash_int(digest, value.slot_number)
    _hash_text(digest, value.source_image_sha256)
    _hash_text(digest, value.serialized_vanilla_slot_sha256)
    _hash_int(digest, value.stored_vanilla_checksum)
    _hash_int(digest, value.computed_vanilla_checksum)
    _hash_int(digest, value.vanilla_magic)
    if type(value.preclear_required) is not bool:
        raise SidecarLoadPlanError(
            "load plan preclear policy has an invalid type"
        )
    _hash_int(digest, int(value.preclear_required))
    if (
        type(value.preclear_witness) is not PreclearCompletionWitness
        or type(value.preclear_witness.seal) is not str
        or value.preclear_witness.seal
        != _preclear_witness_seal(value.preclear_witness)
    ):
        raise SidecarLoadPlanError(
            "load plan preclear witness integrity failed"
        )
    if (
        value.preclear_witness.source_image_sha256
        != value.source_image_sha256
        or value.preclear_witness.slot_number != value.slot_number
        or value.preclear_witness.all_live_pc07_state_cleared is not True
        or value.preclear_witness.evidence_level
        != PRECLEAR_EVIDENCE_CALLER_ASSERTED
    ):
        raise SidecarLoadPlanError(
            "load plan preclear witness is not its exact complete derivation"
        )
    _hash_text(digest, value.preclear_witness.source_image_sha256)
    _hash_int(digest, value.preclear_witness.slot_number)
    _hash_int(
        digest, int(value.preclear_witness.all_live_pc07_state_cleared)
    )
    _hash_text(digest, value.preclear_witness.evidence_level)
    _hash_text(digest, value.preclear_witness.seal)
    _hash_text(digest, value.protected_compatibility_sha256)
    _hash_text(digest, value.protected_epoch_sha256)
    if type(value.postload_party_required) is not bool:
        raise SidecarLoadPlanError(
            "load plan post-load party policy has an invalid type"
        )
    serialized_party_slots = _require_exact_bytes(
        value.serialized_party_slots,
        inspect_ct_srm.ROSTER_LENGTH,
        "serialized party slots",
    )
    if (
        type(value.serialized_joined_flags) is not int
        or not 0 <= value.serialized_joined_flags <= 0xFF
    ):
        raise SidecarLoadPlanError(
            "serialized joined flags must use one exact byte"
        )
    no_copy = (
        type(value) is SafeEmpty
        and value.classification == "invalid-vanilla"
    )
    if no_copy:
        if (
            value.postload_party_required is not False
            or value.postload_party_boundary != NO_PARTY_WRITE_BOUNDARY
            or value.postload_party_action != POSTLOAD_ACTION_NO_COPY
            or value.postload_party_slots is not None
            or value.postload_joined_flags is not None
        ):
            raise SidecarLoadPlanError(
                "invalid-vanilla plan must abort without a party write"
            )
        postload_party_slots = None
        postload_joined_flags = None
    else:
        if (
            value.postload_party_required is not True
            or value.postload_party_boundary != POSTLOAD_PARTY_BOUNDARY
        ):
            raise SidecarLoadPlanError(
                "load plan post-load party boundary is not canonical"
            )
        postload_party_slots = _require_exact_bytes(
            value.postload_party_slots,
            inspect_ct_srm.ROSTER_LENGTH,
            "post-load party slots",
        )
        if (
            type(value.postload_joined_flags) is not int
            or not 0 <= value.postload_joined_flags <= 0xFF
        ):
            raise SidecarLoadPlanError(
                "post-load joined flags must use one exact byte"
            )
        postload_joined_flags = value.postload_joined_flags

    if type(value) is SafeEmpty and not no_copy:
        expected_slots, expected_joined = _safe_empty_party_target(
            serialized_party_slots, value.serialized_joined_flags
        )
        if (
            value.classification not in SAFE_EMPTY_CLASSIFICATIONS
            or value.postload_party_action != POSTLOAD_ACTION_SAFE_EMPTY
            or postload_party_slots != expected_slots
            or postload_joined_flags != expected_joined
        ):
            raise SidecarLoadPlanError(
                "safe-empty post-load party target is not canonical"
            )
    elif type(value) is PreparedLoad:
        if (
            value.classification != _VALID_CLASSIFICATION
            or value.postload_party_action != POSTLOAD_ACTION_PREPARED
            or postload_party_slots != serialized_party_slots
            or postload_joined_flags != value.serialized_joined_flags
        ):
            raise SidecarLoadPlanError(
                "prepared post-load party target is not canonical"
            )
    _hash_int(digest, int(value.postload_party_required))
    _hash_text(digest, value.postload_party_boundary)
    _hash_bytes(digest, serialized_party_slots)
    _hash_int(digest, value.serialized_joined_flags)
    if postload_party_slots is None or postload_joined_flags is None:
        _hash_int(digest, 0)
    else:
        _hash_int(digest, 1)
        _hash_bytes(digest, postload_party_slots)
        _hash_int(digest, postload_joined_flags)
    _hash_text(digest, value.postload_party_action)
    if type(value) is PreparedLoad:
        if (
            type(value.prepared_identity)
            is not schala_recruitment_transaction.PreparedPc07Identity
        ):
            raise SidecarLoadPlanError(
                "prepared load identity has an invalid type"
            )
        _hash_text(digest, value.prepared_identity.record_sha256)
        _hash_text(digest, value.prepared_identity.gate_id)
        _hash_text(digest, value.prepared_identity.evidence_level)
        _hash_text(digest, value.prepared_identity.seal)
        if (
            type(value.sidecar_version) is not int
            or value.sidecar_version != schala_sidecar_v2.VERSION
            or type(value.binding_profile) is not int
            or value.binding_profile
            != schala_sidecar_v2.BINDING_PROFILE_SHA256_SLOT_TRAILER
        ):
            raise SidecarLoadPlanError(
                "prepared load has an unsupported v2 binding identity"
        )
        _hash_int(digest, value.sidecar_version)
        _hash_int(digest, value.binding_profile)
        _hash_bytes(
            digest,
            _require_exact_bytes(
                value.binding_digest,
                schala_sidecar_v2.BINDING_DIGEST_SIZE,
                "prepared v2 binding digest",
            ),
        )
        _hash_bytes(digest, value.character_record)
        _hash_bytes(digest, value.schala_name)
        _hash_int(digest, value.tech_progress)
        _hash_int(digest, value.learned_mask)
        _hash_bytes(digest, value.combo_state)
        _hash_bytes(digest, value.quest_state)
        _hash_int(digest, value.flags)
        _hash_int(digest, value.sequence)
    return digest.hexdigest()


def _seal_plan(value: SidecarLoadPlan) -> SidecarLoadPlan:
    if value.seal:
        raise SidecarLoadPlanError("provisional load plan is already sealed")
    return dataclasses.replace(value, seal=_plan_seal(value))


def _require_slot_number(value: object) -> int:
    if type(value) is not int or value not in range(
        1, inspect_ct_srm.SLOT_COUNT + 1
    ):
        raise SidecarLoadPlanError("slot number must be exact int 1, 2, or 3")
    return value


def prepare_preclear_completion_witness(
    source_image: bytes,
    slot_number: int,
    *,
    all_live_pc07_state_cleared: bool,
) -> PreclearCompletionWitness:
    """Bind an explicit, caller-asserted preclear completion to one load."""

    source_image = _require_exact_bytes(
        source_image,
        inspect_ct_srm.SRAM_SIZE,
        "source SRAM image",
    )
    slot_number = _require_slot_number(slot_number)
    if (
        type(all_live_pc07_state_cleared) is not bool
        or all_live_pc07_state_cleared is not True
    ):
        raise SidecarLoadPlanError(
            "preclear witness requires an explicit complete PC7 live-state "
            "assertion"
        )
    provisional = PreclearCompletionWitness(
        source_image_sha256=sha256(source_image),
        slot_number=slot_number,
        all_live_pc07_state_cleared=True,
        evidence_level=PRECLEAR_EVIDENCE_CALLER_ASSERTED,
        seal="",
    )
    return dataclasses.replace(
        provisional, seal=_preclear_witness_seal(provisional)
    )


def _validate_preclear_witness(
    source_image: bytes,
    slot_number: int,
    value: PreclearCompletionWitness | None,
) -> PreclearCompletionWitness:
    if type(value) is not PreclearCompletionWitness:
        raise SidecarLoadPlanError(
            "load planning requires the exact immutable preclear completion "
            "witness"
        )
    if type(value.seal) is not str or value.seal != _preclear_witness_seal(
        value
    ):
        raise SidecarLoadPlanError("preclear witness integrity seal failed")
    try:
        expected = prepare_preclear_completion_witness(
            source_image,
            slot_number,
            all_live_pc07_state_cleared=(
                value.all_live_pc07_state_cleared
            ),
        )
    except SidecarLoadPlanError as exc:
        raise SidecarLoadPlanError(
            "preclear witness is not a complete source-bound assertion"
        ) from exc
    if expected != value:
        raise SidecarLoadPlanError(
            "preclear witness is not bound to the exact source image and slot"
        )
    return value


def plan_sidecar_load(
    source_image: bytes,
    slot_number: int,
    *,
    preclear_witness: PreclearCompletionWitness | None = None,
    prepared_identity: (
        schala_recruitment_transaction.PreparedPc07Identity | None
    ) = None,
) -> SidecarLoadPlan:
    """Return an exact ``SafeEmpty`` or identity-gated ``PreparedLoad`` plan."""

    source_image = _require_exact_bytes(
        source_image,
        inspect_ct_srm.SRAM_SIZE,
        "source SRAM image",
    )
    slot_number = _require_slot_number(slot_number)
    preclear_witness = _validate_preclear_witness(
        source_image, slot_number, preclear_witness
    )
    slot_base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    serialized_vanilla_slot = source_image[
        slot_base : slot_base + inspect_ct_srm.SLOT_SIZE
    ]
    slot_info = inspect_ct_srm.inspect_slot(source_image, slot_number)
    if (
        type(slot_info) is not dict
        or type(slot_info.get("stored_checksum")) is not int
        or type(slot_info.get("computed_checksum")) is not int
        or type(slot_info.get("magic")) is not int
        or type(slot_info.get("valid")) is not bool
    ):
        raise SidecarLoadPlanError(
            "vanilla slot inspector returned an unsupported result"
        )

    stored_checksum = slot_info["stored_checksum"]
    computed_checksum = slot_info["computed_checksum"]
    vanilla_magic = slot_info["magic"]
    protected_compatibility_sha256, protected_epoch_sha256 = (
        _protection_hashes(serialized_vanilla_slot)
    )
    serialized_party_slots, serialized_joined_flags = _serialized_party(
        serialized_vanilla_slot
    )
    safe_party_slots, safe_joined_flags = _safe_empty_party_target(
        serialized_party_slots, serialized_joined_flags
    )
    common = {
        "slot_number": slot_number,
        "source_image_sha256": sha256(source_image),
        "serialized_vanilla_slot_sha256": sha256(
            serialized_vanilla_slot
        ),
        "stored_vanilla_checksum": stored_checksum,
        "computed_vanilla_checksum": computed_checksum,
        "vanilla_magic": vanilla_magic,
        "preclear_required": True,
        "preclear_witness": preclear_witness,
        "protected_compatibility_sha256": (
            protected_compatibility_sha256
        ),
        "protected_epoch_sha256": protected_epoch_sha256,
        "serialized_party_slots": serialized_party_slots,
        "serialized_joined_flags": serialized_joined_flags,
    }
    safe_postload = {
        "postload_party_required": True,
        "postload_party_boundary": POSTLOAD_PARTY_BOUNDARY,
        "postload_party_slots": safe_party_slots,
        "postload_joined_flags": safe_joined_flags,
        "postload_party_action": POSTLOAD_ACTION_SAFE_EMPTY,
    }
    prepared_postload = {
        "postload_party_required": True,
        "postload_party_boundary": POSTLOAD_PARTY_BOUNDARY,
        "postload_party_slots": serialized_party_slots,
        "postload_joined_flags": serialized_joined_flags,
        "postload_party_action": POSTLOAD_ACTION_PREPARED,
    }
    invalid_vanilla_postload = {
        "postload_party_required": False,
        "postload_party_boundary": NO_PARTY_WRITE_BOUNDARY,
        "postload_party_slots": None,
        "postload_joined_flags": None,
        "postload_party_action": POSTLOAD_ACTION_NO_COPY,
    }

    if slot_info["valid"] is not True:
        provisional = SafeEmpty(
            classification="invalid-vanilla",
            detail=(
                "selected vanilla slot failed checksum or magic validation"
            ),
            **common,
            **invalid_vanilla_postload,
            seal="",
        )
        return _seal_plan(provisional)

    sidecar_start = schala_sidecar.slot_file_offset(slot_number)
    encoded_sidecar = source_image[
        sidecar_start : sidecar_start + schala_sidecar.SIDECAR_SIZE
    ]
    classified = schala_sidecar_v2.classify_versioned_sidecar(
        encoded_sidecar, serialized_vanilla_slot, slot_number
    )

    if (
        type(classified)
        is not schala_sidecar_v2.VersionedSidecarLoadResult
        or type(classified.status) is not str
        or type(classified.detail) is not str
    ):
        raise SidecarLoadPlanError(
            "sidecar classifier returned an unsupported result"
        )

    classification = {
        "classification": classified.status,
        "detail": classified.detail,
    }

    if classified.status in SAFE_EMPTY_CLASSIFICATIONS:
        if classified.value is not None:
            raise SidecarLoadPlanError(
                "safe-empty classification unexpectedly published sidecar "
                "state"
            )
        return _seal_plan(
            SafeEmpty(
                **classification,
                **common,
                **safe_postload,
                seal="",
            )
        )

    if (
        classified.status != _VALID_CLASSIFICATION
        or classified.version != schala_sidecar_v2.VERSION
        or type(classified.value)
        is not schala_sidecar_v2.SchalaSidecarV2
    ):
        raise SidecarLoadPlanError(
            "sidecar classifier returned an unknown classification"
        )

    value = classified.value
    consistency_error = _state_consistency_error(
        value, serialized_party_slots, serialized_joined_flags
    )
    if consistency_error is not None:
        return _seal_plan(
            SafeEmpty(
                classification="state-inconsistent",
                detail=consistency_error,
                **common,
                **safe_postload,
                seal="",
            )
        )
    identity = _validate_prepared_identity(
        value.character_record, prepared_identity
    )
    return _seal_plan(
        PreparedLoad(
            **classification,
            **common,
            **prepared_postload,
            prepared_identity=identity,
            sidecar_version=classified.version,
            binding_profile=value.binding_profile,
            binding_digest=value.binding_digest,
            character_record=value.character_record,
            schala_name=value.name,
            tech_progress=value.tech_progress,
            learned_mask=value.learned_mask,
            combo_state=value.combo_state,
            quest_state=value.quest_state,
            flags=value.flags,
            sequence=value.sequence,
            seal="",
        )
    )


def validate_load_plan(
    value: SidecarLoadPlan,
    source_image: bytes,
    slot_number: int,
    *,
    preclear_witness: PreclearCompletionWitness | None = None,
) -> SidecarLoadPlan:
    """Re-derive a sealed plan from its immutable source before consumption."""

    if type(value) not in (SafeEmpty, PreparedLoad):
        raise SidecarLoadPlanError(
            "load plan must use an exact immutable result type"
        )
    if type(value.seal) is not str or value.seal != _plan_seal(value):
        raise SidecarLoadPlanError("load plan integrity seal failed")
    identity = (
        value.prepared_identity if type(value) is PreparedLoad else None
    )
    try:
        expected = plan_sidecar_load(
            source_image,
            slot_number,
            preclear_witness=preclear_witness,
            prepared_identity=identity,
        )
    except SidecarLoadPlanError as exc:
        raise SidecarLoadPlanError(
            "load plan cannot be re-derived from the supplied source"
        ) from exc
    if expected != value:
        raise SidecarLoadPlanError(
            "load plan is not the exact derivation of the supplied source"
        )
    return value
