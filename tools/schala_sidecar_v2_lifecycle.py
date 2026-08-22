#!/usr/bin/env python3
"""Execute the fail-closed Project Epoch v2 sidecar lifecycle on host bytes.

This module is an immutable, source-only proof model.  It neither patches a
ROM nor approves an SRAM or WRAM address for production.  Its constants pin
the audited vanilla boundaries so that future hook code has a small,
executable ordering contract:

* normal save invalidates the selected sidecar first;
* the vanilla writer then finalizes its exact 0x834-byte serialized prefix and
  metadata epilogue;
* v2 binds the complete 0xA00-byte slot, including the untouched tail;
* sidecar bytes 1..0x9F are written while byte 0 remains invalid; and
* byte 0 of ``PE07`` is the final commit write.

Full loads validate vanilla metadata before the sidecar and never publish
legacy, invalid, stale, or party-inconsistent state.  SafeEmpty normalization
removes only exact logical ID $07 entries and joined bit $01 after the vanilla
load.  New Game+ produces an unbound staged state; only a later normal save
may increment its sequence and bind it to finalized destination bytes.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Final, TypeAlias

import schala_sidecar_load_plan


# The lifecycle is an adapter around the registered load planner. Bind its
# dependency modules through that planner so exact immutable security types
# remain one coherent graph even when external test harnesses reload canonical
# module names.
inspect_ct_srm = schala_sidecar_load_plan.inspect_ct_srm
schala_recruitment_transaction = (
    schala_sidecar_load_plan.schala_recruitment_transaction
)
sidecar_v1 = schala_sidecar_load_plan.schala_sidecar
sidecar_v2 = schala_sidecar_load_plan.schala_sidecar_v2


SRAM_SIZE: Final = inspect_ct_srm.SRAM_SIZE
SLOT_SIZE: Final = inspect_ct_srm.SLOT_SIZE
SLOT_COUNT: Final = inspect_ct_srm.SLOT_COUNT
VANILLA_SERIALIZED_LENGTH: Final = 0x0834
SLOT_TAIL_OFFSET: Final = VANILLA_SERIALIZED_LENGTH

GLOBAL_METADATA_OFFSET: Final = sidecar_v1.GLOBAL_METADATA_OFFSET
GLOBAL_METADATA_SIZE: Final = SRAM_SIZE - GLOBAL_METADATA_OFFSET
LAST_SLOT_SAVED_OFFSET: Final = GLOBAL_METADATA_OFFSET
GLOBAL_SAVE_COUNTER_OFFSET: Final = GLOBAL_METADATA_OFFSET + 1

PROTECTED_COMPATIBILITY_START: Final = 0x0430
PROTECTED_COMPATIBILITY_END: Final = 0x0480
EPOCH_NAME_OFFSET: Final = inspect_ct_srm.EPOCH_NAME_OFFSET
EPOCH_NAME_END: Final = EPOCH_NAME_OFFSET + inspect_ct_srm.NAME_LENGTH

PARTY_OFFSET: Final = inspect_ct_srm.ACTIVE_PARTY_OFFSET
PARTY_SIZE: Final = inspect_ct_srm.ROSTER_LENGTH
JOINED_FLAGS_OFFSET: Final = (
    schala_recruitment_transaction.SERIALIZED_JOINED_FLAGS_OFFSET
)
LOGICAL_PC_ID: Final = schala_recruitment_transaction.LOGICAL_PC_ID
INACTIVE_PC07: Final = 0x87
JOINED_FLAG: Final = schala_recruitment_transaction.JOINED_FLAG
STARTING_TECH_COUNT: Final = (
    schala_recruitment_transaction.STARTING_TECH_COUNT
)

# Conceptual post-load WRAM destinations.  These are trace labels only.
LIVE_PARTY_WRAM_OFFSET: Final = 0x2980
LIVE_JOINED_FLAGS_WRAM_OFFSET: Final = 0x29AF

SAVE_PHASE_PREINVALIDATE: Final = "preinvalidate"
SAVE_PHASE_VANILLA_FINALIZED: Final = "vanilla-finalized"
SAVE_PHASE_BODY_WRITTEN: Final = "body-written"
SAVE_PHASE_BODY_PARTIAL: Final = "body-partial"
SAVE_PHASE_COMMITTED: Final = "committed"
SAVE_FAILURE_PHASES: Final = frozenset(
    {
        SAVE_PHASE_PREINVALIDATE,
        SAVE_PHASE_VANILLA_FINALIZED,
        SAVE_PHASE_BODY_WRITTEN,
        SAVE_PHASE_COMMITTED,
    }
)

ERASE_PHASE_SIDECAR_INVALIDATED: Final = "sidecar-invalidated"
ERASE_PHASE_BODY_CLEARED: Final = "sidecar-body-cleared"
ERASE_PHASE_BODY_PARTIAL: Final = "sidecar-body-partial"
ERASE_PHASE_NATIVE_INVALIDATED: Final = "native-invalidated"
ERASE_FAILURE_PHASES: Final = frozenset(
    {
        ERASE_PHASE_SIDECAR_INVALIDATED,
        ERASE_PHASE_BODY_CLEARED,
        ERASE_PHASE_NATIVE_INVALIDATED,
    }
)

ORIGIN_NORMAL_LIVE: Final = "normal-live"
ORIGIN_NG_PLUS_RETAIN: Final = "new-game-plus-retain"
ORIGIN_NG_PLUS_RESET: Final = "new-game-plus-reset"
PENDING_ORIGINS: Final = frozenset(
    {
        ORIGIN_NORMAL_LIVE,
        ORIGIN_NG_PLUS_RETAIN,
        ORIGIN_NG_PLUS_RESET,
    }
)

_VALID_CLASSIFICATION: Final = "valid"
PreparedPc07Identity = (
    schala_recruitment_transaction.PreparedPc07Identity
)
PreclearCompletionWitness = (
    schala_sidecar_load_plan.PreclearCompletionWitness
)


class SidecarLifecycleError(ValueError):
    """Raised before an ambiguous or unsafe lifecycle result is emitted."""


@dataclasses.dataclass(frozen=True, slots=True)
class TraceEntry:
    """One exact modeled read, write, or prerequisite assertion."""

    phase: str
    operation: str
    address_space: str
    offset: int
    before: bytes
    after: bytes
    label: str


@dataclasses.dataclass(frozen=True, slots=True)
class PartyState:
    """The exact nine serialized party bytes and one joined-flags byte."""

    slots: bytes
    joined_flags: int


@dataclasses.dataclass(frozen=True, slots=True)
class UnboundSidecarState:
    """Validated live fields with no slot checksum, identity, or digest."""

    character_record: bytes
    name: bytes
    tech_progress: int
    learned_mask: int
    combo_state: bytes
    quest_state: bytes
    flags: int
    previous_sequence: int
    origin: str
    prepared_identity: PreparedPc07Identity


@dataclasses.dataclass(frozen=True, slots=True)
class NormalSaveResult:
    """One complete or deliberately interrupted normal-save execution."""

    sram: bytes
    trace: tuple[TraceEntry, ...]
    stopped_after_phase: str | None
    committed: bool
    value: sidecar_v2.SchalaSidecarV2 | None
    encoded_sidecar: bytes | None


@dataclasses.dataclass(frozen=True, slots=True)
class SafeEmptyLoad:
    """A full-load result that publishes no Schala payload fields."""

    classification: str
    detail: str
    slot_number: int
    source_sram_sha256: str
    serialized_slot_sha256: str
    sidecar_sha256: str | None
    preclear_witness: PreclearCompletionWitness
    postload_party_required: bool
    party_action: str
    post_vanilla_party: PartyState | None
    normalized_party: PartyState | None
    trace: tuple[TraceEntry, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedLoadV2:
    """A valid, identity- and party-consistent v2 full-load result."""

    classification: str
    detail: str
    slot_number: int
    source_sram_sha256: str
    serialized_slot_sha256: str
    sidecar_sha256: str
    preclear_witness: PreclearCompletionWitness
    prepared_identity: PreparedPc07Identity
    postload_party_required: bool
    party_action: str
    value: sidecar_v2.SchalaSidecarV2
    post_vanilla_party: PartyState
    trace: tuple[TraceEntry, ...]


FullLoadResult: TypeAlias = SafeEmptyLoad | PreparedLoadV2


@dataclasses.dataclass(frozen=True, slots=True)
class NewGamePlusStage:
    """Unbound retain/reset state captured at the partial-load boundary."""

    pending: UnboundSidecarState
    retained: bool
    source_slot_number: int
    source_sram_sha256: str
    source_slot_sha256: str
    source_sidecar_sha256: str
    source_binding_digest: bytes
    source_sequence: int
    source_prepared_identity: PreparedPc07Identity
    trace: tuple[TraceEntry, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class PreviewValidation:
    """A preview publication token bound to exact selected persisted state."""

    slot_number: int
    source_sram_sha256: str
    serialized_slot_sha256: str
    sidecar_sha256: str
    binding_digest: bytes
    sequence: int
    protected_compatibility_sha256: str
    protected_epoch_sha256: str
    slot_tail_sha256: str
    schala_name: bytes
    prepared_identity: PreparedPc07Identity


@dataclasses.dataclass(frozen=True, slots=True)
class EraseResult:
    """One complete or interrupted exact-slot erase execution."""

    sram: bytes
    slot_number: int
    trace: tuple[TraceEntry, ...]
    stopped_after_phase: str | None
    sidecar_invalidated: bool
    sidecar_cleared: bool
    native_magic_invalidated: bool


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_exact_bytes(value: object, size: int, field: str) -> bytes:
    if type(value) is not bytes or len(value) != size:
        raise SidecarLifecycleError(
            f"{field} must be immutable bytes of exact length 0x{size:X}"
        )
    return value


def _require_exact_int(
    value: object, minimum: int, maximum: int, field: str
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SidecarLifecycleError(
            f"{field} must be an exact integer from {minimum} through "
            f"{maximum}"
        )
    return value


def _require_slot_number(value: object) -> int:
    return _require_exact_int(value, 1, SLOT_COUNT, "slot_number")


def _slot_bounds(slot_number: int) -> tuple[int, int]:
    slot_number = _require_slot_number(slot_number)
    start = (slot_number - 1) * SLOT_SIZE
    return start, start + SLOT_SIZE


def _sidecar_bounds(slot_number: int) -> tuple[int, int]:
    slot_number = _require_slot_number(slot_number)
    start = sidecar_v1.slot_file_offset(slot_number)
    return start, start + sidecar_v2.SIDECAR_SIZE


def _require_party_shape(
    value: object,
    field: str = "party",
) -> PartyState:
    if type(value) is not PartyState:
        raise SidecarLifecycleError(
            f"{field} must use the exact immutable PartyState type"
        )
    _require_exact_bytes(value.slots, PARTY_SIZE, f"{field}.slots")
    _require_exact_int(value.joined_flags, 0, 0xFF, f"{field}.joined_flags")
    return value


def _require_party(
    value: object,
    field: str = "party",
    *,
    allow_duplicate_pc07: bool = False,
) -> PartyState:
    value = _require_party_shape(value, field)
    slots = value.slots
    for entry in slots:
        if not (0x00 <= entry <= 0x07 or 0x80 <= entry <= 0x87):
            raise SidecarLifecycleError(
                f"{field} entries must be IDs $00-$07 or inactive $80-$87"
            )
    if type(allow_duplicate_pc07) is not bool:
        raise SidecarLifecycleError(
            "allow_duplicate_pc07 must use an exact boolean"
        )
    active_ids = tuple(entry for entry in slots if entry < 0x80)
    duplicate_ids = {
        entry for entry in active_ids if active_ids.count(entry) > 1
    }
    if duplicate_ids and not (
        allow_duplicate_pc07 and duplicate_ids == {LOGICAL_PC_ID}
    ):
        raise SidecarLifecycleError(
            f"{field} contains duplicate exact active logical IDs"
        )
    return value


def party_from_serialized_slot(
    serialized_slot: bytes,
    *,
    allow_duplicate_pc07: bool = False,
) -> PartyState:
    """Extract only the party state restored by the vanilla full loader."""

    serialized_slot = _require_exact_bytes(
        serialized_slot, SLOT_SIZE, "serialized_slot"
    )
    value = PartyState(
        slots=serialized_slot[PARTY_OFFSET : PARTY_OFFSET + PARTY_SIZE],
        joined_flags=serialized_slot[JOINED_FLAGS_OFFSET],
    )
    return _require_party(
        value,
        "serialized party",
        allow_duplicate_pc07=allow_duplicate_pc07,
    )


def _validate_prepared_identity(
    character_record: bytes,
    value: PreparedPc07Identity | None,
) -> PreparedPc07Identity:
    if type(value) is not PreparedPc07Identity:
        raise SidecarLifecycleError(
            "publication requires the exact immutable prepared PC7 "
            "identity token"
        )
    try:
        expected = schala_recruitment_transaction.prepare_pc07_identity(
            character_record,
            gate_id=value.gate_id,
            evidence_level=value.evidence_level,
        )
    except schala_recruitment_transaction.RecruitmentTransactionError as exc:
        raise SidecarLifecycleError(
            "prepared PC7 identity is not a registered host-fixture token"
        ) from exc
    if expected != value:
        raise SidecarLifecycleError(
            "prepared PC7 identity is forged, stale, or bound to a "
            "different character record"
        )
    return value


def prepare_preclear_completion_witness(
    source_sram: bytes,
    slot_number: int,
    *,
    all_live_pc07_state_cleared: bool,
) -> PreclearCompletionWitness:
    """Use the registered load-plan gate for an exact preclear assertion."""

    try:
        return schala_sidecar_load_plan.prepare_preclear_completion_witness(
            source_sram,
            slot_number,
            all_live_pc07_state_cleared=all_live_pc07_state_cleared,
        )
    except schala_sidecar_load_plan.SidecarLoadPlanError as exc:
        raise SidecarLifecycleError(
            f"preclear completion witness was refused: {exc}"
        ) from exc


def _validate_pending(value: object) -> UnboundSidecarState:
    if type(value) is not UnboundSidecarState:
        raise SidecarLifecycleError(
            "pending state must use the exact immutable "
            "UnboundSidecarState type"
        )
    if type(value.origin) is not str or value.origin not in PENDING_ORIGINS:
        raise SidecarLifecycleError("pending state origin is not canonical")
    previous_sequence = _require_exact_int(
        value.previous_sequence, 0, 0xFFFF, "previous_sequence"
    )
    try:
        validated = sidecar_v2.prepare_sidecar_v2(
            character_record=value.character_record,
            name=value.name,
            tech_progress=value.tech_progress,
            learned_mask=value.learned_mask,
            combo_state=value.combo_state,
            quest_state=value.quest_state,
            flags=value.flags,
            sequence=min(previous_sequence + 1, 0xFFFF),
            serialized_vanilla_slot=bytes(SLOT_SIZE),
            slot_number=1,
        )
    except (sidecar_v2.SidecarV2Error, sidecar_v1.SidecarError) as exc:
        raise SidecarLifecycleError(
            f"pending sidecar fields are invalid: {exc}"
        ) from exc
    if validated.character_record[0] != LOGICAL_PC_ID:
        raise SidecarLifecycleError(
            "pending character record byte 0 must be logical PC $07"
        )
    _validate_prepared_identity(
        validated.character_record, value.prepared_identity
    )
    return value


def prepare_unbound_sidecar_state(
    *,
    character_record: bytes,
    name: bytes,
    tech_progress: int,
    learned_mask: int,
    combo_state: bytes,
    quest_state: bytes,
    flags: int,
    previous_sequence: int,
    prepared_identity: PreparedPc07Identity,
    origin: str = ORIGIN_NORMAL_LIVE,
) -> UnboundSidecarState:
    """Create exact live state that can only bind during a normal save."""

    value = UnboundSidecarState(
        character_record=character_record,
        name=name,
        tech_progress=tech_progress,
        learned_mask=learned_mask,
        combo_state=combo_state,
        quest_state=quest_state,
        flags=flags,
        previous_sequence=previous_sequence,
        origin=origin,
        prepared_identity=prepared_identity,
    )
    return _validate_pending(value)


def _consistency_error(
    *,
    character_record: bytes,
    tech_progress: int,
    learned_mask: int,
    quest_state: bytes,
    party: PartyState,
) -> str | None:
    party = _require_party(
        party, allow_duplicate_pc07=True
    )
    if character_record[0] != LOGICAL_PC_ID:
        return "character record byte 0 is not logical PC $07"
    try:
        quest = sidecar_v1.decode_quest_state(quest_state)
    except sidecar_v1.SidecarError as exc:
        return f"quest state is invalid: {exc}"

    pc07_count = party.slots.count(LOGICAL_PC_ID)
    joined = bool(party.joined_flags & JOINED_FLAG)
    if quest.schala_recruited:
        if not quest.join_grant_applied:
            return "recruited state lacks the one-time join-grant guard"
        if pc07_count != 1 or not joined:
            return (
                "recruited state requires exact PC $07 once and joined "
                "bit $01 set"
            )
        if tech_progress < STARTING_TECH_COUNT:
            return "recruited state lacks the three starting single techs"
        return None

    if quest.join_grant_applied:
        return "unrecruited state carries the one-time join-grant guard"
    if pc07_count or joined:
        return "unrecruited state conflicts with exact PC $07 or joined bit $01"
    if tech_progress != 0 or learned_mask != 0:
        return "unrecruited state carries Schala single-tech progress"
    return None


def _trace_read(
    image: bytes | bytearray,
    trace: list[TraceEntry],
    *,
    phase: str,
    address_space: str,
    offset: int,
    size: int,
    label: str,
) -> bytes:
    end = offset + size
    if type(offset) is not int or type(size) is not int or (
        offset < 0 or size < 0 or end > len(image)
    ):
        raise SidecarLifecycleError("trace read lies outside its image")
    value = bytes(image[offset:end])
    trace.append(
        TraceEntry(
            phase=phase,
            operation="read",
            address_space=address_space,
            offset=offset,
            before=value,
            after=value,
            label=label,
        )
    )
    return value


def _trace_write(
    image: bytearray,
    trace: list[TraceEntry],
    *,
    phase: str,
    address_space: str,
    offset: int,
    payload: bytes,
    label: str,
) -> None:
    if type(payload) is not bytes:
        raise SidecarLifecycleError("trace write payload must be exact bytes")
    end = offset + len(payload)
    if type(offset) is not int or offset < 0 or end > len(image):
        raise SidecarLifecycleError("trace write lies outside its image")
    before = bytes(image[offset:end])
    image[offset:end] = payload
    trace.append(
        TraceEntry(
            phase=phase,
            operation="write",
            address_space=address_space,
            offset=offset,
            before=before,
            after=payload,
            label=label,
        )
    )


def _metadata_offset(base: int, slot_number: int) -> int:
    return base + (slot_number - 1) * 2


def _validate_finalized_metadata(
    source_metadata: bytes,
    finalized_metadata: bytes,
    finalized_slot: bytes,
    slot_number: int,
) -> None:
    source_metadata = _require_exact_bytes(
        source_metadata, GLOBAL_METADATA_SIZE, "source metadata"
    )
    finalized_metadata = _require_exact_bytes(
        finalized_metadata, GLOBAL_METADATA_SIZE, "finalized_metadata"
    )
    finalized_slot = _require_exact_bytes(
        finalized_slot, SLOT_SIZE, "finalized_vanilla_slot"
    )
    slot_number = _require_slot_number(slot_number)
    relative_checksum = (
        inspect_ct_srm.CHECKSUM_TABLE_OFFSET
        - GLOBAL_METADATA_OFFSET
        + (slot_number - 1) * 2
    )
    relative_magic = (
        inspect_ct_srm.MAGIC_TABLE_OFFSET
        - GLOBAL_METADATA_OFFSET
        + (slot_number - 1) * 2
    )
    modeled = {
        0,
        1,
        relative_checksum,
        relative_checksum + 1,
        relative_magic,
        relative_magic + 1,
    }
    for index, (before, after) in enumerate(
        zip(source_metadata, finalized_metadata, strict=True)
    ):
        if index not in modeled and before != after:
            raise SidecarLifecycleError(
                "finalized metadata changes an unmodeled byte at "
                f"$1FE0+0x{index:02X}"
            )

    if finalized_metadata[0] != slot_number - 1:
        raise SidecarLifecycleError(
            "finalized last-slot metadata does not identify the selected slot"
        )
    counter = source_metadata[1]
    if finalized_metadata[1] not in (counter, (counter + 1) & 0xFF):
        raise SidecarLifecycleError(
            "finalized global save counter is neither unchanged nor "
            "incremented once"
        )
    expected_checksum = inspect_ct_srm.slot_checksum(finalized_slot)
    stored_checksum = int.from_bytes(
        finalized_metadata[relative_checksum : relative_checksum + 2],
        "little",
    )
    if stored_checksum != expected_checksum:
        raise SidecarLifecycleError(
            "finalized metadata checksum does not match the complete "
            "0xA00-byte slot"
        )
    magic = int.from_bytes(
        finalized_metadata[relative_magic : relative_magic + 2], "little"
    )
    if magic != inspect_ct_srm.SLOT_MAGIC:
        raise SidecarLifecycleError(
            "finalized metadata does not contain the vanilla slot magic"
        )


def _validate_normal_save_inputs(
    source_sram: bytes,
    slot_number: int,
    finalized_vanilla_slot: bytes,
    finalized_metadata: bytes,
    pending: UnboundSidecarState,
) -> tuple[int, PartyState]:
    source_sram = _require_exact_bytes(source_sram, SRAM_SIZE, "source_sram")
    slot_number = _require_slot_number(slot_number)
    finalized_vanilla_slot = _require_exact_bytes(
        finalized_vanilla_slot, SLOT_SIZE, "finalized_vanilla_slot"
    )
    finalized_metadata = _require_exact_bytes(
        finalized_metadata, GLOBAL_METADATA_SIZE, "finalized_metadata"
    )
    pending = _validate_pending(pending)

    slot_start, slot_end = _slot_bounds(slot_number)
    source_slot = source_sram[slot_start:slot_end]
    if (
        finalized_vanilla_slot[SLOT_TAIL_OFFSET:]
        != source_slot[SLOT_TAIL_OFFSET:]
    ):
        raise SidecarLifecycleError(
            "vanilla normal save cannot change untouched slot tail "
            "$0834-$09FF"
        )

    source_metadata = source_sram[GLOBAL_METADATA_OFFSET:]
    _validate_finalized_metadata(
        source_metadata,
        finalized_metadata,
        finalized_vanilla_slot,
        slot_number,
    )
    party = party_from_serialized_slot(finalized_vanilla_slot)
    error = _consistency_error(
        character_record=pending.character_record,
        tech_progress=pending.tech_progress,
        learned_mask=pending.learned_mask,
        quest_state=pending.quest_state,
        party=party,
    )
    if error is not None:
        raise SidecarLifecycleError(
            f"finalized vanilla party is inconsistent with pending state: "
            f"{error}"
        )

    candidate = bytearray(source_sram)
    candidate[slot_start:slot_end] = finalized_vanilla_slot
    candidate[GLOBAL_METADATA_OFFSET:] = finalized_metadata
    info = inspect_ct_srm.inspect_slot(bytes(candidate), slot_number)
    if type(info) is not dict or info.get("valid") is not True:
        raise SidecarLifecycleError(
            "supplied finalized vanilla slot fails checksum or magic"
        )
    return slot_start, party


def _normal_result(
    image: bytearray,
    trace: list[TraceEntry],
    *,
    stopped_after_phase: str | None,
    committed: bool,
    value: sidecar_v2.SchalaSidecarV2 | None = None,
    encoded: bytes | None = None,
) -> NormalSaveResult:
    return NormalSaveResult(
        sram=bytes(image),
        trace=tuple(trace),
        stopped_after_phase=stopped_after_phase,
        committed=committed,
        value=value if committed else None,
        encoded_sidecar=encoded if committed else None,
    )


def execute_normal_save(
    source_sram: bytes,
    slot_number: int,
    finalized_vanilla_slot: bytes,
    finalized_metadata: bytes,
    pending: UnboundSidecarState,
    *,
    fail_after_phase: str | None = None,
    body_bytes_before_failure: int | None = None,
) -> NormalSaveResult:
    """Execute or interrupt the audited magic-byte-last normal-save order.

    ``body_bytes_before_failure`` accepts 0 through 0x9F and models a torn
    write of that many bytes beginning at sidecar byte 1.  It is mutually
    exclusive with ``fail_after_phase``.  Every interrupted precommit result
    withholds the encoded value and remains non-publishable.
    """

    slot_start, _ = _validate_normal_save_inputs(
        source_sram,
        slot_number,
        finalized_vanilla_slot,
        finalized_metadata,
        pending,
    )
    source_sram = _require_exact_bytes(source_sram, SRAM_SIZE, "source_sram")
    slot_number = _require_slot_number(slot_number)
    pending = _validate_pending(pending)
    if fail_after_phase is not None and (
        type(fail_after_phase) is not str
        or fail_after_phase not in SAVE_FAILURE_PHASES
    ):
        raise SidecarLifecycleError("unknown normal-save failure phase")
    if body_bytes_before_failure is not None:
        if fail_after_phase is not None:
            raise SidecarLifecycleError(
                "body tear injection and phase failure are mutually exclusive"
            )
        _require_exact_int(
            body_bytes_before_failure,
            0,
            sidecar_v2.SIDECAR_SIZE - 1,
            "body_bytes_before_failure",
        )

    image = bytearray(source_sram)
    trace: list[TraceEntry] = []
    sidecar_start, _ = _sidecar_bounds(slot_number)

    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_PREINVALIDATE,
        address_space="SRAM",
        offset=sidecar_start,
        payload=b"\xFF",
        label="selected-sidecar-magic-byte-0",
    )
    if fail_after_phase == SAVE_PHASE_PREINVALIDATE:
        return _normal_result(
            image,
            trace,
            stopped_after_phase=SAVE_PHASE_PREINVALIDATE,
            committed=False,
        )

    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_VANILLA_FINALIZED,
        address_space="SRAM",
        offset=slot_start,
        payload=finalized_vanilla_slot[:VANILLA_SERIALIZED_LENGTH],
        label="vanilla-contiguous-serialized-prefix",
    )
    checksum_offset = _metadata_offset(
        inspect_ct_srm.CHECKSUM_TABLE_OFFSET, slot_number
    )
    magic_offset = _metadata_offset(
        inspect_ct_srm.MAGIC_TABLE_OFFSET, slot_number
    )
    finalized_checksum = finalized_metadata[
        checksum_offset - GLOBAL_METADATA_OFFSET:
        checksum_offset - GLOBAL_METADATA_OFFSET + 2
    ]
    finalized_magic = finalized_metadata[
        magic_offset - GLOBAL_METADATA_OFFSET:
        magic_offset - GLOBAL_METADATA_OFFSET + 2
    ]
    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_VANILLA_FINALIZED,
        address_space="SRAM",
        offset=checksum_offset,
        payload=finalized_checksum,
        label="vanilla-selected-slot-checksum",
    )
    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_VANILLA_FINALIZED,
        address_space="SRAM",
        offset=magic_offset,
        payload=finalized_magic,
        label="vanilla-selected-slot-magic",
    )
    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_VANILLA_FINALIZED,
        address_space="SRAM",
        offset=LAST_SLOT_SAVED_OFFSET,
        payload=finalized_metadata[0:1],
        label="vanilla-last-slot-saved",
    )
    _trace_read(
        image,
        trace,
        phase=SAVE_PHASE_VANILLA_FINALIZED,
        address_space="SRAM",
        offset=GLOBAL_SAVE_COUNTER_OFFSET,
        size=1,
        label="vanilla-global-save-counter",
    )
    if image[GLOBAL_SAVE_COUNTER_OFFSET] != finalized_metadata[1]:
        _trace_write(
            image,
            trace,
            phase=SAVE_PHASE_VANILLA_FINALIZED,
            address_space="SRAM",
            offset=GLOBAL_SAVE_COUNTER_OFFSET,
            payload=finalized_metadata[1:2],
            label="vanilla-global-save-counter-increment",
        )
    if bytes(image[GLOBAL_METADATA_OFFSET:]) != finalized_metadata:
        raise AssertionError("modeled vanilla metadata epilogue is incomplete")
    if (
        bytes(image[slot_start : slot_start + SLOT_SIZE])
        != finalized_vanilla_slot
    ):
        raise AssertionError(
            "modeled vanilla finalization did not preserve the caller's "
            "exact complete slot image"
        )
    if fail_after_phase == SAVE_PHASE_VANILLA_FINALIZED:
        return _normal_result(
            image,
            trace,
            stopped_after_phase=SAVE_PHASE_VANILLA_FINALIZED,
            committed=False,
        )

    serialized_slot = _trace_read(
        image,
        trace,
        phase="binding-input",
        address_space="SRAM",
        offset=slot_start,
        size=SLOT_SIZE,
        label="complete-finalized-vanilla-slot",
    )
    value = sidecar_v2.prepare_sidecar_v2(
        character_record=pending.character_record,
        name=pending.name,
        tech_progress=pending.tech_progress,
        learned_mask=pending.learned_mask,
        combo_state=pending.combo_state,
        quest_state=pending.quest_state,
        flags=pending.flags,
        sequence=min(pending.previous_sequence + 1, 0xFFFF),
        serialized_vanilla_slot=serialized_slot,
        slot_number=slot_number,
    )
    encoded = sidecar_v2.encode_sidecar_v2(value, serialized_slot)

    if body_bytes_before_failure is not None:
        body_count = body_bytes_before_failure
        if body_count:
            _trace_write(
                image,
                trace,
                phase=SAVE_PHASE_BODY_PARTIAL,
                address_space="SRAM",
                offset=sidecar_start + 1,
                payload=encoded[1 : 1 + body_count],
                label="torn-v2-sidecar-body",
            )
        return _normal_result(
            image,
            trace,
            stopped_after_phase=SAVE_PHASE_BODY_PARTIAL,
            committed=False,
        )

    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_BODY_WRITTEN,
        address_space="SRAM",
        offset=sidecar_start + 1,
        payload=encoded[1:],
        label="v2-sidecar-bytes-1-through-0x9f",
    )
    if fail_after_phase == SAVE_PHASE_BODY_WRITTEN:
        return _normal_result(
            image,
            trace,
            stopped_after_phase=SAVE_PHASE_BODY_WRITTEN,
            committed=False,
        )

    _trace_write(
        image,
        trace,
        phase=SAVE_PHASE_COMMITTED,
        address_space="SRAM",
        offset=sidecar_start,
        payload=encoded[:1],
        label="v2-sidecar-magic-byte-0-commit",
    )
    output = bytes(image)
    output_slot = output[slot_start : slot_start + SLOT_SIZE]
    if (
        output_slot[
            PROTECTED_COMPATIBILITY_START:PROTECTED_COMPATIBILITY_END
        ]
        != finalized_vanilla_slot[
            PROTECTED_COMPATIBILITY_START:PROTECTED_COMPATIBILITY_END
        ]
        or output_slot[EPOCH_NAME_OFFSET:EPOCH_NAME_END]
        != finalized_vanilla_slot[EPOCH_NAME_OFFSET:EPOCH_NAME_END]
    ):
        raise AssertionError(
            "sidecar commit changed caller-finalized compatibility or "
            "Epoch bytes"
        )
    loaded = sidecar_v2.load_sidecar_v2_from_sram(output, slot_number)
    if loaded.status != _VALID_CLASSIFICATION or loaded.value != value:
        raise AssertionError("committed v2 sidecar failed exact reload")
    stopped = (
        SAVE_PHASE_COMMITTED
        if fail_after_phase == SAVE_PHASE_COMMITTED
        else None
    )
    return _normal_result(
        image,
        trace,
        stopped_after_phase=stopped,
        committed=True,
        value=value,
        encoded=encoded,
    )


def _classification_with_trace(
    sram: bytes, slot_number: int
) -> tuple[
    sidecar_v2.VersionedSidecarLoadResult,
    bytes,
    bytes | None,
    tuple[TraceEntry, ...],
]:
    sram = _require_exact_bytes(sram, SRAM_SIZE, "sram")
    slot_number = _require_slot_number(slot_number)
    trace: list[TraceEntry] = []
    slot_start, _ = _slot_bounds(slot_number)
    sidecar_start, _ = _sidecar_bounds(slot_number)
    serialized_slot = sram[slot_start : slot_start + SLOT_SIZE]
    magic = _trace_read(
        sram,
        trace,
        phase="vanilla-validation",
        address_space="SRAM",
        offset=_metadata_offset(inspect_ct_srm.MAGIC_TABLE_OFFSET, slot_number),
        size=2,
        label="selected-vanilla-magic",
    )
    if int.from_bytes(magic, "little") == inspect_ct_srm.SLOT_MAGIC:
        serialized_slot = _trace_read(
            sram,
            trace,
            phase="vanilla-validation",
            address_space="SRAM",
            offset=slot_start,
            size=SLOT_SIZE,
            label="selected-complete-vanilla-slot-checksum-input",
        )
        _trace_read(
            sram,
            trace,
            phase="vanilla-validation",
            address_space="SRAM",
            offset=_metadata_offset(
                inspect_ct_srm.CHECKSUM_TABLE_OFFSET, slot_number
            ),
            size=2,
            label="selected-vanilla-checksum",
        )
    result = sidecar_v2.load_sidecar_v2_from_sram(sram, slot_number)
    sidecar = None
    if result.status != "invalid-vanilla":
        sidecar = _trace_read(
            sram,
            trace,
            phase="sidecar-classification",
            address_space="SRAM",
            offset=sidecar_start,
            size=sidecar_v2.SIDECAR_SIZE,
            label="selected-versioned-sidecar",
        )
    return result, serialized_slot, sidecar, tuple(trace)


def _safe_empty_party(
    party: PartyState,
    trace: list[TraceEntry],
) -> PartyState:
    party = _require_party_shape(party, "post_vanilla_party")
    slots = bytearray(party.slots)
    for index, entry in enumerate(tuple(slots)):
        if entry == LOGICAL_PC_ID:
            before = bytes((entry,))
            after = bytes((INACTIVE_PC07,))
            slots[index] = INACTIVE_PC07
            trace.append(
                TraceEntry(
                    phase="safe-empty-normalization",
                    operation="write",
                    address_space="WRAM",
                    offset=LIVE_PARTY_WRAM_OFFSET + index,
                    before=before,
                    after=after,
                    label="replace-exact-pc07-with-inactive-87",
                )
            )
    joined = party.joined_flags & ~JOINED_FLAG
    if joined != party.joined_flags:
        trace.append(
            TraceEntry(
                phase="safe-empty-normalization",
                operation="write",
                address_space="WRAM",
                offset=LIVE_JOINED_FLAGS_WRAM_OFFSET,
                before=bytes((party.joined_flags,)),
                after=bytes((joined,)),
                label="clear-pc07-joined-bit-01",
            )
        )
    return PartyState(bytes(slots), joined)


def execute_full_load(
    sram: bytes,
    slot_number: int,
    post_vanilla_party: PartyState | None,
    *,
    preclear_witness: PreclearCompletionWitness | None = None,
    prepared_identity: PreparedPc07Identity | None = None,
) -> FullLoadResult:
    """Execute the gated full-load decision after an asserted live preclear.

    Invalid vanilla metadata aborts before the vanilla copy.  That result has
    no post-load party target and performs no WRAM normalization.
    """

    sram = _require_exact_bytes(sram, SRAM_SIZE, "sram")
    slot_number = _require_slot_number(slot_number)
    try:
        plan = schala_sidecar_load_plan.plan_sidecar_load(
            sram,
            slot_number,
            preclear_witness=preclear_witness,
            prepared_identity=prepared_identity,
        )
    except schala_sidecar_load_plan.SidecarLoadPlanError as exc:
        raise SidecarLifecycleError(
            f"registered full-load gate refused execution: {exc}"
        ) from exc
    if type(preclear_witness) is not PreclearCompletionWitness:
        raise AssertionError("registered planner accepted a non-exact witness")

    result, serialized_slot, encoded, initial_trace = (
        _classification_with_trace(sram, slot_number)
    )
    trace = [
        TraceEntry(
            phase="preclear-witness",
            operation="assertion",
            address_space="HOST",
            offset=0,
            before=b"",
            after=b"",
            label="source-slot-bound-complete-live-pc07-preclear",
        )
    ]
    trace.extend(initial_trace)

    if (
        type(plan) is schala_sidecar_load_plan.SafeEmpty
        and plan.classification == "invalid-vanilla"
    ):
        if result.status != "invalid-vanilla":
            raise AssertionError(
                "registered plan and v2 classifier disagree on vanilla "
                "validity"
            )
        if encoded is not None:
            raise AssertionError(
                "invalid vanilla classification read the selected sidecar"
            )
        if post_vanilla_party is not None:
            raise SidecarLifecycleError(
                "invalid vanilla aborts before copy; post_vanilla_party "
                "must be None"
            )
        return SafeEmptyLoad(
            classification=plan.classification,
            detail=plan.detail,
            slot_number=slot_number,
            source_sram_sha256=sha256(sram),
            serialized_slot_sha256=sha256(serialized_slot),
            sidecar_sha256=None,
            preclear_witness=preclear_witness,
            postload_party_required=False,
            party_action=schala_sidecar_load_plan.POSTLOAD_ACTION_NO_COPY,
            post_vanilla_party=None,
            normalized_party=None,
            trace=tuple(trace),
        )

    post_vanilla_party = _require_party_shape(
        post_vanilla_party, "post_vanilla_party"
    )
    expected_party = PartyState(
        slots=plan.serialized_party_slots,
        joined_flags=plan.serialized_joined_flags,
    )
    expected_party = _require_party_shape(expected_party, "serialized party")
    if post_vanilla_party != expected_party:
        raise SidecarLifecycleError(
            "post_vanilla_party is not the exact party restored from "
            "the selected slot"
        )
    if type(encoded) is not bytes:
        raise AssertionError(
            "valid vanilla classification did not read the selected sidecar"
        )

    if type(plan) is schala_sidecar_load_plan.PreparedLoad:
        _require_party(post_vanilla_party, "post_vanilla_party")
        if (
            result.status != _VALID_CLASSIFICATION
            or type(result.value) is not sidecar_v2.SchalaSidecarV2
        ):
            raise AssertionError(
                "registered prepared plan and v2 classifier disagree"
            )
        identity = _validate_prepared_identity(
            result.value.character_record, prepared_identity
        )
        return PreparedLoadV2(
            classification=plan.classification,
            detail=plan.detail,
            slot_number=slot_number,
            source_sram_sha256=sha256(sram),
            serialized_slot_sha256=sha256(serialized_slot),
            sidecar_sha256=sha256(encoded),
            preclear_witness=preclear_witness,
            prepared_identity=identity,
            postload_party_required=True,
            party_action=(
                schala_sidecar_load_plan.POSTLOAD_ACTION_PREPARED
            ),
            value=result.value,
            post_vanilla_party=post_vanilla_party,
            trace=tuple(trace),
        )

    if type(plan) is not schala_sidecar_load_plan.SafeEmpty:
        raise AssertionError("registered planner returned an unknown type")
    normalized = _safe_empty_party(post_vanilla_party, trace)
    expected_normalized = PartyState(
        slots=plan.postload_party_slots,
        joined_flags=plan.postload_joined_flags,
    )
    if normalized != expected_normalized:
        raise AssertionError(
            "lifecycle normalization disagrees with registered load plan"
        )
    return SafeEmptyLoad(
        classification=plan.classification,
        detail=plan.detail,
        slot_number=slot_number,
        source_sram_sha256=sha256(sram),
        serialized_slot_sha256=sha256(serialized_slot),
        sidecar_sha256=sha256(encoded),
        preclear_witness=preclear_witness,
        postload_party_required=True,
        party_action=schala_sidecar_load_plan.POSTLOAD_ACTION_SAFE_EMPTY,
        post_vanilla_party=post_vanilla_party,
        normalized_party=normalized,
        trace=tuple(trace),
    )


def _require_publishable_source(
    sram: bytes,
    slot_number: int,
    prepared_identity: PreparedPc07Identity | None,
) -> tuple[
    sidecar_v2.SchalaSidecarV2,
    bytes,
    bytes,
    PartyState,
    tuple[TraceEntry, ...],
]:
    result, serialized_slot, encoded, trace = _classification_with_trace(
        sram, slot_number
    )
    if (
        result.status != _VALID_CLASSIFICATION
        or type(result.value) is not sidecar_v2.SchalaSidecarV2
    ):
        raise SidecarLifecycleError(
            f"selected source is not publishable v2 state: {result.status}: "
            f"{result.detail}"
        )
    if type(encoded) is not bytes:
        raise AssertionError(
            "publishable source classification omitted its sidecar read"
        )
    value = result.value
    _validate_prepared_identity(value.character_record, prepared_identity)
    party = party_from_serialized_slot(
        serialized_slot, allow_duplicate_pc07=True
    )
    error = _consistency_error(
        character_record=value.character_record,
        tech_progress=value.tech_progress,
        learned_mask=value.learned_mask,
        quest_state=value.quest_state,
        party=party,
    )
    if error is not None:
        raise SidecarLifecycleError(
            f"selected source is party-inconsistent: {error}"
        )
    return value, serialized_slot, encoded, party, trace


def stage_new_game_plus(
    source_sram: bytes,
    source_slot_number: int,
    *,
    prepared_identity: PreparedPc07Identity | None,
    reset_character_record: bytes,
    reset_name: bytes,
    reset_prepared_identity: PreparedPc07Identity | None = None,
) -> NewGamePlusStage:
    """Stage retain/reset live fields without a destination rebind."""

    source_sram = _require_exact_bytes(
        source_sram, SRAM_SIZE, "source_sram"
    )
    source_slot_number = _require_slot_number(source_slot_number)
    reset_character_record = _require_exact_bytes(
        reset_character_record,
        sidecar_v2.CHARACTER_RECORD_SIZE,
        "reset_character_record",
    )
    reset_name = _require_exact_bytes(
        reset_name, sidecar_v2.NAME_SIZE, "reset_name"
    )
    if reset_character_record[0] != LOGICAL_PC_ID:
        raise SidecarLifecycleError(
            "reset character record byte 0 must be logical PC $07"
        )
    value, serialized_slot, encoded, _, trace = _require_publishable_source(
        source_sram, source_slot_number, prepared_identity
    )
    retained = bool(value.flags & sidecar_v1.FLAG_NG_PLUS_RETAIN)
    if retained:
        staged_identity = _validate_prepared_identity(
            value.character_record, prepared_identity
        )
        fields = {
            "character_record": value.character_record,
            "name": value.name,
            "tech_progress": value.tech_progress,
            "learned_mask": value.learned_mask,
            "combo_state": value.combo_state,
            "quest_state": value.quest_state,
            "flags": value.flags,
            "origin": ORIGIN_NG_PLUS_RETAIN,
        }
    else:
        staged_identity = _validate_prepared_identity(
            reset_character_record, reset_prepared_identity
        )
        fields = {
            "character_record": reset_character_record,
            "name": reset_name,
            "tech_progress": 0,
            "learned_mask": 0,
            "combo_state": bytes(sidecar_v2.COMBO_STATE_SIZE),
            "quest_state": sidecar_v1.encode_quest_state(
                sidecar_v1.QuestStateV1()
            ),
            "flags": sidecar_v1.FLAG_INITIALIZED,
            "origin": ORIGIN_NG_PLUS_RESET,
        }
    pending = prepare_unbound_sidecar_state(
        **fields,
        previous_sequence=value.sequence,
        prepared_identity=staged_identity,
    )
    return NewGamePlusStage(
        pending=pending,
        retained=retained,
        source_slot_number=source_slot_number,
        source_sram_sha256=sha256(source_sram),
        source_slot_sha256=sha256(serialized_slot),
        source_sidecar_sha256=sha256(encoded),
        source_binding_digest=value.binding_digest,
        source_sequence=value.sequence,
        source_prepared_identity=_validate_prepared_identity(
            value.character_record, prepared_identity
        ),
        trace=trace,
    )


def prepare_preview_validation(
    sram: bytes,
    slot_number: int,
    *,
    prepared_identity: PreparedPc07Identity | None,
) -> PreviewValidation:
    """Prepare a preview token only from exact publishable selected state."""

    sram = _require_exact_bytes(sram, SRAM_SIZE, "sram")
    slot_number = _require_slot_number(slot_number)
    value, serialized_slot, encoded, _, _ = _require_publishable_source(
        sram, slot_number, prepared_identity
    )
    return PreviewValidation(
        slot_number=slot_number,
        source_sram_sha256=sha256(sram),
        serialized_slot_sha256=sha256(serialized_slot),
        sidecar_sha256=sha256(encoded),
        binding_digest=value.binding_digest,
        sequence=value.sequence,
        protected_compatibility_sha256=sha256(
            serialized_slot[
                PROTECTED_COMPATIBILITY_START:PROTECTED_COMPATIBILITY_END
            ]
        ),
        protected_epoch_sha256=sha256(
            serialized_slot[EPOCH_NAME_OFFSET:EPOCH_NAME_END]
        ),
        slot_tail_sha256=sha256(serialized_slot[SLOT_TAIL_OFFSET:]),
        schala_name=value.name,
        prepared_identity=_validate_prepared_identity(
            value.character_record, prepared_identity
        ),
    )


def validate_preview_validation(
    token: PreviewValidation,
    sram: bytes,
    slot_number: int,
    *,
    prepared_identity: PreparedPc07Identity | None,
) -> PreviewValidation:
    """Re-derive a preview token and reject every stale cache dimension."""

    if type(token) is not PreviewValidation:
        raise SidecarLifecycleError(
            "preview token must use the exact immutable host type"
        )
    expected = prepare_preview_validation(
        sram, slot_number, prepared_identity=prepared_identity
    )
    if token != expected:
        raise SidecarLifecycleError(
            "preview token is not bound to this exact slot, digest, "
            "sequence, sidecar, and source image"
        )
    return token


def execute_erase(
    source_sram: bytes,
    slot_number: int,
    *,
    fail_after_phase: str | None = None,
    body_bytes_before_failure: int | None = None,
) -> EraseResult:
    """Break sidecar magic, clear its body, then run native invalidation.

    ``body_bytes_before_failure`` accepts 0 through 0x9F and models a torn
    erase after the one-byte magic invalidation but before native slot erase.
    It is mutually exclusive with ``fail_after_phase``.
    """

    source_sram = _require_exact_bytes(
        source_sram, SRAM_SIZE, "source_sram"
    )
    slot_number = _require_slot_number(slot_number)
    if fail_after_phase is not None and (
        type(fail_after_phase) is not str
        or fail_after_phase not in ERASE_FAILURE_PHASES
    ):
        raise SidecarLifecycleError("unknown erase failure phase")
    if body_bytes_before_failure is not None:
        if fail_after_phase is not None:
            raise SidecarLifecycleError(
                "erase body tear and phase failure are mutually exclusive"
            )
        _require_exact_int(
            body_bytes_before_failure,
            0,
            sidecar_v2.SIDECAR_SIZE - 1,
            "body_bytes_before_failure",
        )

    image = bytearray(source_sram)
    trace: list[TraceEntry] = []
    sidecar_start, _ = _sidecar_bounds(slot_number)
    _trace_write(
        image,
        trace,
        phase=ERASE_PHASE_SIDECAR_INVALIDATED,
        address_space="SRAM",
        offset=sidecar_start,
        payload=b"\xFF",
        label="erase-selected-sidecar-magic-byte-0-first",
    )
    if fail_after_phase == ERASE_PHASE_SIDECAR_INVALIDATED:
        return EraseResult(
            sram=bytes(image),
            slot_number=slot_number,
            trace=tuple(trace),
            stopped_after_phase=ERASE_PHASE_SIDECAR_INVALIDATED,
            sidecar_invalidated=True,
            sidecar_cleared=False,
            native_magic_invalidated=False,
        )

    if body_bytes_before_failure is not None:
        body_count = body_bytes_before_failure
        if body_count:
            _trace_write(
                image,
                trace,
                phase=ERASE_PHASE_BODY_PARTIAL,
                address_space="SRAM",
                offset=sidecar_start + 1,
                payload=b"\xFF" * body_count,
                label="torn-selected-sidecar-body-clear",
            )
        return EraseResult(
            sram=bytes(image),
            slot_number=slot_number,
            trace=tuple(trace),
            stopped_after_phase=ERASE_PHASE_BODY_PARTIAL,
            sidecar_invalidated=True,
            sidecar_cleared=(
                body_count == sidecar_v2.SIDECAR_SIZE - 1
            ),
            native_magic_invalidated=False,
        )

    _trace_write(
        image,
        trace,
        phase=ERASE_PHASE_BODY_CLEARED,
        address_space="SRAM",
        offset=sidecar_start + 1,
        payload=b"\xFF" * (sidecar_v2.SIDECAR_SIZE - 1),
        label="erase-selected-sidecar-bytes-1-through-0x9f",
    )
    if fail_after_phase == ERASE_PHASE_BODY_CLEARED:
        return EraseResult(
            sram=bytes(image),
            slot_number=slot_number,
            trace=tuple(trace),
            stopped_after_phase=ERASE_PHASE_BODY_CLEARED,
            sidecar_invalidated=True,
            sidecar_cleared=True,
            native_magic_invalidated=False,
        )

    native_magic_offset = _metadata_offset(
        inspect_ct_srm.MAGIC_TABLE_OFFSET, slot_number
    )
    _trace_write(
        image,
        trace,
        phase=ERASE_PHASE_NATIVE_INVALIDATED,
        address_space="SRAM",
        offset=native_magic_offset,
        payload=bytes(((slot_number - 1) * 2,)),
        label="vanilla-erase-selected-magic-low-byte",
    )
    stopped = (
        ERASE_PHASE_NATIVE_INVALIDATED
        if fail_after_phase == ERASE_PHASE_NATIVE_INVALIDATED
        else None
    )
    return EraseResult(
        sram=bytes(image),
        slot_number=slot_number,
        trace=tuple(trace),
        stopped_after_phase=stopped,
        sidecar_invalidated=True,
        sidecar_cleared=True,
        native_magic_invalidated=True,
    )
