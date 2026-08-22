#!/usr/bin/env python3

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import schala_sidecar_v2_lifecycle as TOOL


# Use the exact dependency module objects captured by the lifecycle executor.
# Several older focused suites reload modules under the same sys.modules names;
# binding through TOOL keeps these exact-type security tests order-independent.
inspect_ct_srm = TOOL.inspect_ct_srm
RECRUIT = TOOL.schala_recruitment_transaction
V1 = TOOL.sidecar_v1
LOAD_PLAN = TOOL.schala_sidecar_load_plan
V2 = TOOL.sidecar_v2


SCHALA_NAME = bytes.fromhex("9C A2 9B 8A A5 AA")
RESET_NAME = b"RESET!"
IDENTITY_GATE = "synthetic-non-installable-test-record"


def pc07_record() -> bytes:
    """Return the registered synthetic, non-installable PC7 fixture."""

    return bytes((0x07,)) + bytes(
        (index * 11 + 5) & 0xFF
        for index in range(V2.CHARACTER_RECORD_SIZE - 1)
    )


def identity() -> RECRUIT.PreparedPc07Identity:
    return RECRUIT.prepare_pc07_identity(
        pc07_record(),
        gate_id=IDENTITY_GATE,
        evidence_level=RECRUIT.READINESS_HOST_FIXTURE,
    )


def quest_state(recruited: bool) -> bytes:
    if not recruited:
        return V1.encode_quest_state(V1.QuestStateV1())
    return V1.encode_quest_state(
        V1.QuestStateV1(
            quest_unlocked=True,
            anchor_count=3,
            ward_resolved=True,
            schala_recruited=True,
            join_grant_applied=True,
        )
    )


def party_bytes(recruited: bool) -> tuple[bytes, int]:
    if recruited:
        return bytes((0, 1, 2, 3, 4, 5, 7, 0x86, 0x80)), 0xA5
    return bytes((0, 1, 2, 3, 4, 5, 6, 0x87, 0x80)), 0xA4


def serialized_slot(
    slot_number: int,
    *,
    recruited: bool = True,
    duplicate_pc07: bool = False,
) -> bytes:
    result = bytearray(
        (index * (17 + slot_number * 2) + slot_number * 29) & 0xFF
        for index in range(inspect_ct_srm.SLOT_SIZE)
    )
    party, joined = party_bytes(recruited)
    if duplicate_pc07:
        party = bytes((7, 1, 2, 3, 4, 5, 7, 0x86, 0x80))
        joined |= 1
    result[
        inspect_ct_srm.ACTIVE_PARTY_OFFSET:
        inspect_ct_srm.ACTIVE_PARTY_OFFSET
        + inspect_ct_srm.ROSTER_LENGTH
    ] = party
    result[RECRUIT.SERIALIZED_JOINED_FLAGS_OFFSET] = joined
    result[
        TOOL.PROTECTED_COMPATIBILITY_START:
        TOOL.PROTECTED_COMPATIBILITY_END
    ] = bytes(
        (slot_number * 23 + index * 7) & 0xFF
        for index in range(
            TOOL.PROTECTED_COMPATIBILITY_END
            - TOOL.PROTECTED_COMPATIBILITY_START
        )
    )
    result[
        inspect_ct_srm.EPOCH_NAME_OFFSET:
        inspect_ct_srm.EPOCH_NAME_OFFSET + inspect_ct_srm.NAME_LENGTH
    ] = bytes(
        (0xB0 + slot_number * 3 + index) & 0xFF
        for index in range(inspect_ct_srm.NAME_LENGTH)
    )
    result[TOOL.SLOT_TAIL_OFFSET:] = bytes(
        (slot_number * 41 + index * 13) & 0xFF
        for index in range(
            inspect_ct_srm.SLOT_SIZE - TOOL.SLOT_TAIL_OFFSET
        )
    )
    return bytes(result)


def valid_sram(
    *,
    slot_overrides: dict[int, bytes] | None = None,
) -> bytes:
    slot_overrides = {} if slot_overrides is None else slot_overrides
    result = bytearray(
        (index * 5 + 0x31) & 0xFF
        for index in range(inspect_ct_srm.SRAM_SIZE)
    )
    result[
        V1.SIDECAR_AREA_OFFSET:V1.GLOBAL_METADATA_OFFSET
    ] = b"\xFF" * (
        V1.GLOBAL_METADATA_OFFSET - V1.SIDECAR_AREA_OFFSET
    )
    metadata = bytearray(
        (0x70 + index * 3) & 0xFF
        for index in range(TOOL.GLOBAL_METADATA_SIZE)
    )
    metadata[0] = 0
    metadata[1] = 0x42
    for slot_number in range(1, inspect_ct_srm.SLOT_COUNT + 1):
        slot = slot_overrides.get(
            slot_number, serialized_slot(slot_number)
        )
        base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
        result[base : base + inspect_ct_srm.SLOT_SIZE] = slot
        index = (slot_number - 1) * 2
        checksum_relative = (
            inspect_ct_srm.CHECKSUM_TABLE_OFFSET
            - V1.GLOBAL_METADATA_OFFSET
            + index
        )
        magic_relative = (
            inspect_ct_srm.MAGIC_TABLE_OFFSET
            - V1.GLOBAL_METADATA_OFFSET
            + index
        )
        metadata[
            checksum_relative : checksum_relative + 2
        ] = inspect_ct_srm.slot_checksum(slot).to_bytes(2, "little")
        metadata[
            magic_relative : magic_relative + 2
        ] = inspect_ct_srm.SLOT_MAGIC.to_bytes(2, "little")
    result[V1.GLOBAL_METADATA_OFFSET:] = metadata
    return bytes(result)


def pending_state(
    *,
    recruited: bool = True,
    retain: bool = True,
    previous_sequence: int = 0x1200,
) -> TOOL.UnboundSidecarState:
    flags = V1.FLAG_INITIALIZED
    if retain:
        flags |= V1.FLAG_NG_PLUS_RETAIN
    tech_progress = 3 if recruited else 0
    return TOOL.prepare_unbound_sidecar_state(
        character_record=pc07_record(),
        name=SCHALA_NAME,
        tech_progress=tech_progress,
        learned_mask=V1.learned_mask_for_count(tech_progress),
        combo_state=bytes(range(0x10, 0x20)),
        quest_state=quest_state(recruited),
        flags=flags,
        previous_sequence=previous_sequence,
        prepared_identity=identity(),
    )


def install_v2(
    sram: bytes,
    slot_number: int,
    *,
    recruited: bool = True,
    retain: bool = True,
    sequence: int = 0x1200,
    combo_state: bytes | None = None,
) -> bytes:
    start = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    slot = sram[start : start + inspect_ct_srm.SLOT_SIZE]
    flags = V1.FLAG_INITIALIZED
    if retain:
        flags |= V1.FLAG_NG_PLUS_RETAIN
    tech_progress = 3 if recruited else 0
    value = V2.prepare_sidecar_v2(
        character_record=pc07_record(),
        name=SCHALA_NAME,
        tech_progress=tech_progress,
        learned_mask=V1.learned_mask_for_count(tech_progress),
        combo_state=(
            bytes(range(0x10, 0x20))
            if combo_state is None
            else combo_state
        ),
        quest_state=quest_state(recruited),
        flags=flags,
        sequence=sequence,
        serialized_vanilla_slot=slot,
        slot_number=slot_number,
    )
    encoded = V2.encode_sidecar_v2(value, slot)
    return V2.install_sidecar_v2(sram, slot_number, encoded)


def install_all_v2(sram: bytes) -> bytes:
    result = sram
    for slot_number in range(1, inspect_ct_srm.SLOT_COUNT + 1):
        result = install_v2(
            result, slot_number, sequence=0x1200 + slot_number
        )
    return result


def finalized_save_inputs(
    source: bytes,
    slot_number: int,
    *,
    recruited: bool = True,
    change_protected: bool = True,
) -> tuple[bytes, bytes]:
    base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    slot = bytearray(source[base : base + inspect_ct_srm.SLOT_SIZE])
    slot[0x20] ^= 0x5A
    party, joined = party_bytes(recruited)
    slot[
        inspect_ct_srm.ACTIVE_PARTY_OFFSET:
        inspect_ct_srm.ACTIVE_PARTY_OFFSET
        + inspect_ct_srm.ROSTER_LENGTH
    ] = party
    slot[RECRUIT.SERIALIZED_JOINED_FLAGS_OFFSET] = joined
    if change_protected:
        slot[
            TOOL.PROTECTED_COMPATIBILITY_START:
            TOOL.PROTECTED_COMPATIBILITY_END
        ] = bytes(
            (0xE1 + index * 9 + slot_number) & 0xFF
            for index in range(
                TOOL.PROTECTED_COMPATIBILITY_END
                - TOOL.PROTECTED_COMPATIBILITY_START
            )
        )
        slot[
            inspect_ct_srm.EPOCH_NAME_OFFSET:
            inspect_ct_srm.EPOCH_NAME_OFFSET
            + inspect_ct_srm.NAME_LENGTH
        ] = b"EPOCH!"

    metadata = bytearray(source[V1.GLOBAL_METADATA_OFFSET:])
    metadata[0] = slot_number - 1
    metadata[1] = (metadata[1] + 1) & 0xFF
    index = (slot_number - 1) * 2
    checksum_relative = (
        inspect_ct_srm.CHECKSUM_TABLE_OFFSET
        - V1.GLOBAL_METADATA_OFFSET
        + index
    )
    magic_relative = (
        inspect_ct_srm.MAGIC_TABLE_OFFSET
        - V1.GLOBAL_METADATA_OFFSET
        + index
    )
    metadata[
        checksum_relative : checksum_relative + 2
    ] = inspect_ct_srm.slot_checksum(bytes(slot)).to_bytes(2, "little")
    metadata[
        magic_relative : magic_relative + 2
    ] = inspect_ct_srm.SLOT_MAGIC.to_bytes(2, "little")
    return bytes(slot), bytes(metadata)


def witness(
    sram: bytes, slot_number: int
) -> LOAD_PLAN.PreclearCompletionWitness:
    return TOOL.prepare_preclear_completion_witness(
        sram,
        slot_number,
        all_live_pc07_state_cleared=True,
    )


def persisted_party(sram: bytes, slot_number: int) -> TOOL.PartyState:
    base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    slot = sram[base : base + inspect_ct_srm.SLOT_SIZE]
    return TOOL.PartyState(
        slots=slot[
            inspect_ct_srm.ACTIVE_PARTY_OFFSET:
            inspect_ct_srm.ACTIVE_PARTY_OFFSET
            + inspect_ct_srm.ROSTER_LENGTH
        ],
        joined_flags=slot[RECRUIT.SERIALIZED_JOINED_FLAGS_OFFSET],
    )


def crc16_collision(encoded: bytes) -> bytes:
    """Flip a nonempty combo-state bit subset with zero CRC delta."""

    base = bytearray(encoded)
    checksum_input = bytearray(base)
    checksum_input[V2.CHECKSUM_OFFSET : V2.CHECKSUM_OFFSET + 2] = b"\x00\x00"
    base_crc = V1.crc16_ccitt_false(checksum_input)
    deltas: list[int] = []
    for bit_index in range(17):
        candidate = bytearray(checksum_input)
        offset = 0x68 + bit_index // 8
        candidate[offset] ^= 1 << (bit_index % 8)
        deltas.append(V1.crc16_ccitt_false(candidate) ^ base_crc)

    basis: dict[int, tuple[int, int]] = {}
    dependency = 0
    for index, delta in enumerate(deltas):
        reduced = delta
        combination = 1 << index
        while reduced:
            pivot = reduced.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (reduced, combination)
                break
            basis_value, basis_combination = basis[pivot]
            reduced ^= basis_value
            combination ^= basis_combination
        if reduced == 0:
            dependency = combination
            break
    if not dependency:
        raise AssertionError("17 CRC deltas did not produce a dependency")

    collision = bytearray(base)
    for bit_index in range(17):
        if dependency & (1 << bit_index):
            offset = 0x68 + bit_index // 8
            collision[offset] ^= 1 << (bit_index % 8)
    check = bytearray(collision)
    check[V2.CHECKSUM_OFFSET : V2.CHECKSUM_OFFSET + 2] = b"\x00\x00"
    if V1.crc16_ccitt_false(check) != base_crc:
        raise AssertionError("constructed payload is not a CRC16 collision")
    return bytes(collision)


class SchalaSidecarV2LifecycleTests(unittest.TestCase):
    def test_normal_save_all_slots_order_and_exact_preservation(self) -> None:
        source = install_all_v2(valid_sram())

        for slot_number in range(1, inspect_ct_srm.SLOT_COUNT + 1):
            with self.subTest(slot=slot_number):
                finalized_slot, finalized_metadata = finalized_save_inputs(
                    source, slot_number
                )
                base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
                source_slot = source[
                    base : base + inspect_ct_srm.SLOT_SIZE
                ]
                self.assertNotEqual(
                    source_slot[
                        TOOL.PROTECTED_COMPATIBILITY_START:
                        TOOL.PROTECTED_COMPATIBILITY_END
                    ],
                    finalized_slot[
                        TOOL.PROTECTED_COMPATIBILITY_START:
                        TOOL.PROTECTED_COMPATIBILITY_END
                    ],
                )
                self.assertNotEqual(
                    source_slot[
                        inspect_ct_srm.EPOCH_NAME_OFFSET:
                        inspect_ct_srm.EPOCH_NAME_OFFSET
                        + inspect_ct_srm.NAME_LENGTH
                    ],
                    finalized_slot[
                        inspect_ct_srm.EPOCH_NAME_OFFSET:
                        inspect_ct_srm.EPOCH_NAME_OFFSET
                        + inspect_ct_srm.NAME_LENGTH
                    ],
                )

                result = TOOL.execute_normal_save(
                    source,
                    slot_number,
                    finalized_slot,
                    finalized_metadata,
                    pending_state(previous_sequence=0x2200),
                )
                self.assertTrue(result.committed)
                self.assertIsNone(result.stopped_after_phase)
                self.assertEqual(result.value.sequence, 0x2201)
                self.assertEqual(
                    result.sram[
                        base : base + inspect_ct_srm.SLOT_SIZE
                    ],
                    finalized_slot,
                )
                self.assertEqual(
                    result.sram[V1.GLOBAL_METADATA_OFFSET:],
                    finalized_metadata,
                )
                self.assertEqual(
                    finalized_slot[TOOL.SLOT_TAIL_OFFSET:],
                    source_slot[TOOL.SLOT_TAIL_OFFSET:],
                )

                for other in range(
                    1, inspect_ct_srm.SLOT_COUNT + 1
                ):
                    if other == slot_number:
                        continue
                    other_base = (
                        other - 1
                    ) * inspect_ct_srm.SLOT_SIZE
                    self.assertEqual(
                        result.sram[
                            other_base:
                            other_base + inspect_ct_srm.SLOT_SIZE
                        ],
                        source[
                            other_base:
                            other_base + inspect_ct_srm.SLOT_SIZE
                        ],
                    )
                    sidecar_start = V1.slot_file_offset(other)
                    self.assertEqual(
                        result.sram[
                            sidecar_start:
                            sidecar_start + V2.SIDECAR_SIZE
                        ],
                        source[
                            sidecar_start:
                            sidecar_start + V2.SIDECAR_SIZE
                        ],
                    )

                writes = [
                    entry
                    for entry in result.trace
                    if entry.operation == "write"
                ]
                selected_sidecar = V1.slot_file_offset(slot_number)
                self.assertEqual(
                    (writes[0].phase, writes[0].offset, writes[0].after),
                    (
                        TOOL.SAVE_PHASE_PREINVALIDATE,
                        selected_sidecar,
                        b"\xFF",
                    ),
                )
                self.assertEqual(
                    writes[-2].phase, TOOL.SAVE_PHASE_BODY_WRITTEN
                )
                self.assertEqual(len(writes[-2].after), 0x9F)
                self.assertEqual(
                    (writes[-1].phase, writes[-1].offset),
                    (TOOL.SAVE_PHASE_COMMITTED, selected_sidecar),
                )
                self.assertEqual(writes[-1].after, b"P")
                loaded = V2.load_sidecar_v2_from_sram(
                    result.sram, slot_number
                )
                self.assertEqual(loaded.status, "valid")
                self.assertEqual(loaded.value, result.value)

    def test_normal_save_phase_and_body_tears_never_publish(self) -> None:
        source = install_v2(valid_sram(), 1, sequence=0x1000)
        finalized_slot, finalized_metadata = finalized_save_inputs(source, 1)
        pending = pending_state(previous_sequence=0x1000)

        for phase in (
            TOOL.SAVE_PHASE_PREINVALIDATE,
            TOOL.SAVE_PHASE_VANILLA_FINALIZED,
            TOOL.SAVE_PHASE_BODY_WRITTEN,
        ):
            with self.subTest(phase=phase):
                result = TOOL.execute_normal_save(
                    source,
                    1,
                    finalized_slot,
                    finalized_metadata,
                    pending,
                    fail_after_phase=phase,
                )
                self.assertFalse(result.committed)
                self.assertIsNone(result.value)
                self.assertIsNone(result.encoded_sidecar)
                self.assertEqual(result.stopped_after_phase, phase)
                loaded = V2.load_sidecar_v2_from_sram(result.sram, 1)
                self.assertNotEqual(loaded.status, "valid")
                self.assertIsNone(loaded.value)

        for body_count in (0, 1, 3, 4, 0x40, 0x9F):
            with self.subTest(body_count=body_count):
                result = TOOL.execute_normal_save(
                    source,
                    1,
                    finalized_slot,
                    finalized_metadata,
                    pending,
                    body_bytes_before_failure=body_count,
                )
                self.assertFalse(result.committed)
                self.assertEqual(
                    result.stopped_after_phase,
                    TOOL.SAVE_PHASE_BODY_PARTIAL,
                )
                self.assertEqual(
                    result.sram[V1.slot_file_offset(1)], 0xFF
                )
                self.assertNotEqual(
                    V2.load_sidecar_v2_from_sram(
                        result.sram, 1
                    ).status,
                    "valid",
                )

        committed_then_stopped = TOOL.execute_normal_save(
            source,
            1,
            finalized_slot,
            finalized_metadata,
            pending,
            fail_after_phase=TOOL.SAVE_PHASE_COMMITTED,
        )
        self.assertTrue(committed_then_stopped.committed)
        self.assertEqual(
            committed_then_stopped.stopped_after_phase,
            TOOL.SAVE_PHASE_COMMITTED,
        )
        self.assertEqual(
            V2.load_sidecar_v2_from_sram(
                committed_then_stopped.sram, 1
            ).status,
            "valid",
        )

    def test_save_rejects_tail_metadata_and_identity_violations(self) -> None:
        source = install_v2(valid_sram(), 1)
        finalized_slot, finalized_metadata = finalized_save_inputs(source, 1)
        pending = pending_state()

        changed_tail = bytearray(finalized_slot)
        changed_tail[0x900] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "untouched slot tail"
        ):
            TOOL.execute_normal_save(
                source,
                1,
                bytes(changed_tail),
                finalized_metadata,
                pending,
            )

        changed_metadata = bytearray(finalized_metadata)
        changed_metadata[0x05] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "unmodeled byte"
        ):
            TOOL.execute_normal_save(
                source,
                1,
                finalized_slot,
                bytes(changed_metadata),
                pending,
            )

        token = identity()
        forged = dataclasses.replace(
            token, record_sha256="0" * 64
        )

        class IdentitySubclass(RECRUIT.PreparedPc07Identity):
            pass

        polymorphic = IdentitySubclass(**dataclasses.asdict(token))
        altered_record = bytearray(pc07_record())
        altered_record[-1] ^= 0x01
        bad_pending = (
            dataclasses.replace(pending, prepared_identity=None),
            dataclasses.replace(pending, prepared_identity=forged),
            dataclasses.replace(pending, prepared_identity=polymorphic),
            dataclasses.replace(
                pending, character_record=bytes(altered_record)
            ),
        )
        for candidate in bad_pending:
            with self.subTest(candidate=repr(candidate.prepared_identity)):
                with self.assertRaisesRegex(
                    TOOL.SidecarLifecycleError, "identity"
                ):
                    TOOL.execute_normal_save(
                        source,
                        1,
                        finalized_slot,
                        finalized_metadata,
                        candidate,
                    )

    def test_full_load_valid_requires_exact_preclear_and_identity(self) -> None:
        source = install_v2(valid_sram(), 1)
        party = persisted_party(source, 1)
        clear = witness(source, 1)
        token = identity()

        prepared = TOOL.execute_full_load(
            source,
            1,
            party,
            preclear_witness=clear,
            prepared_identity=token,
        )
        self.assertIs(type(prepared), TOOL.PreparedLoadV2)
        self.assertEqual(prepared.classification, "valid")
        self.assertEqual(prepared.preclear_witness, clear)
        self.assertEqual(prepared.prepared_identity, token)
        self.assertEqual(
            prepared.trace[0].label,
            "source-slot-bound-complete-live-pc07-preclear",
        )
        self.assertEqual(prepared.trace[0].operation, "assertion")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            prepared.classification = "invalid"

        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "preclear"
        ):
            TOOL.execute_full_load(
                source,
                1,
                party,
                prepared_identity=token,
            )
        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "identity"
        ):
            TOOL.execute_full_load(
                source,
                1,
                party,
                preclear_witness=clear,
            )

        altered = bytearray(source)
        altered[inspect_ct_srm.SLOT_SIZE] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "preclear"
        ):
            TOOL.execute_full_load(
                bytes(altered),
                1,
                party,
                preclear_witness=clear,
                prepared_identity=token,
            )

        forged = dataclasses.replace(token, seal="0" * 64)

        class IdentitySubclass(RECRUIT.PreparedPc07Identity):
            pass

        polymorphic = IdentitySubclass(**dataclasses.asdict(token))
        for candidate in (forged, polymorphic):
            with self.subTest(candidate_type=type(candidate).__name__):
                with self.assertRaisesRegex(
                    TOOL.SidecarLifecycleError, "identity"
                ):
                    TOOL.execute_full_load(
                        source,
                        1,
                        party,
                        preclear_witness=clear,
                        prepared_identity=candidate,
                    )

        class WitnessSubclass(LOAD_PLAN.PreclearCompletionWitness):
            pass

        polymorphic_clear = WitnessSubclass(**dataclasses.asdict(clear))
        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "preclear"
        ):
            TOOL.execute_full_load(
                source,
                1,
                party,
                preclear_witness=polymorphic_clear,
                prepared_identity=token,
            )

    def test_full_load_safe_empty_normalizes_every_exact_pc07(self) -> None:
        slot = serialized_slot(1, duplicate_pc07=True)
        source = valid_sram(slot_overrides={1: slot})
        party = persisted_party(source, 1)
        result = TOOL.execute_full_load(
            source,
            1,
            party,
            preclear_witness=witness(source, 1),
        )
        self.assertIs(type(result), TOOL.SafeEmptyLoad)
        self.assertEqual(result.classification, "uninitialized")
        self.assertTrue(result.postload_party_required)
        self.assertEqual(
            result.party_action, LOAD_PLAN.POSTLOAD_ACTION_SAFE_EMPTY
        )
        self.assertEqual(result.normalized_party.slots.count(7), 0)
        self.assertEqual(
            result.normalized_party.slots,
            bytes((0x87, 1, 2, 3, 4, 5, 0x87, 0x86, 0x80)),
        )
        self.assertEqual(result.normalized_party.joined_flags & 1, 0)
        wram_writes = [
            entry
            for entry in result.trace
            if entry.address_space == "WRAM"
        ]
        self.assertEqual(
            [entry.offset for entry in wram_writes],
            [
                TOOL.LIVE_PARTY_WRAM_OFFSET,
                TOOL.LIVE_PARTY_WRAM_OFFSET + 6,
                TOOL.LIVE_JOINED_FLAGS_WRAM_OFFSET,
            ],
        )
        self.assertEqual(source, bytes(source))
        for field in (
            "value",
            "character_record",
            "schala_name",
            "tech_progress",
            "quest_state",
        ):
            self.assertFalse(hasattr(result, field), field)

    def test_full_load_safe_empty_sanitizes_pc07_amid_malformed_roster(
        self,
    ) -> None:
        malformed_parties = (
            bytes((0, 0, 7, 3, 4, 5, 6, 0x81, 0x82)),
            bytes((0, 8, 7, 3, 4, 5, 6, 0x81, 0x82)),
        )
        for malformed_party in malformed_parties:
            with self.subTest(party=malformed_party.hex()):
                slot = bytearray(serialized_slot(1))
                slot[
                    inspect_ct_srm.ACTIVE_PARTY_OFFSET:
                    inspect_ct_srm.ACTIVE_PARTY_OFFSET
                    + inspect_ct_srm.ROSTER_LENGTH
                ] = malformed_party
                slot[RECRUIT.SERIALIZED_JOINED_FLAGS_OFFSET] |= 1
                source = valid_sram(slot_overrides={1: bytes(slot)})
                source = install_v2(source, 1)
                result = TOOL.execute_full_load(
                    source,
                    1,
                    persisted_party(source, 1),
                    preclear_witness=witness(source, 1),
                    prepared_identity=identity(),
                )
                self.assertIs(type(result), TOOL.SafeEmptyLoad)
                self.assertEqual(
                    result.classification, "state-inconsistent"
                )
                expected = bytearray(malformed_party)
                expected[2] = 0x87
                self.assertEqual(
                    result.normalized_party.slots, bytes(expected)
                )
                self.assertEqual(
                    result.normalized_party.joined_flags & 1, 0
                )

    def test_invalid_vanilla_aborts_without_party_target_or_write(self) -> None:
        malformed = bytearray(serialized_slot(1))
        malformed[
            inspect_ct_srm.ACTIVE_PARTY_OFFSET:
            inspect_ct_srm.ACTIVE_PARTY_OFFSET
            + inspect_ct_srm.ROSTER_LENGTH
        ] = b"\xFF" * inspect_ct_srm.ROSTER_LENGTH
        source = bytearray(valid_sram(slot_overrides={1: bytes(malformed)}))
        source[inspect_ct_srm.MAGIC_TABLE_OFFSET] ^= 0x01
        source = bytes(source)
        result = TOOL.execute_full_load(
            source,
            1,
            None,
            preclear_witness=witness(source, 1),
            prepared_identity=identity(),
        )
        self.assertIs(type(result), TOOL.SafeEmptyLoad)
        self.assertEqual(result.classification, "invalid-vanilla")
        self.assertFalse(result.postload_party_required)
        self.assertEqual(
            result.party_action, LOAD_PLAN.POSTLOAD_ACTION_NO_COPY
        )
        self.assertIsNone(result.post_vanilla_party)
        self.assertIsNone(result.normalized_party)
        self.assertIsNone(result.sidecar_sha256)
        self.assertFalse(
            any(
                entry.address_space == "WRAM"
                for entry in result.trace
            )
        )
        self.assertFalse(
            any(
                entry.label == "selected-versioned-sidecar"
                for entry in result.trace
            )
        )

        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "must be None"
        ):
            TOOL.execute_full_load(
                source,
                1,
                TOOL.PartyState(bytes(9), 0),
                preclear_witness=witness(source, 1),
            )

    def test_party_inconsistent_valid_v2_becomes_safe_empty(self) -> None:
        source = valid_sram()
        source = install_v2(
            source, 1, recruited=False, sequence=0x3300
        )
        result = TOOL.execute_full_load(
            source,
            1,
            persisted_party(source, 1),
            preclear_witness=witness(source, 1),
            prepared_identity=identity(),
        )
        self.assertIs(type(result), TOOL.SafeEmptyLoad)
        self.assertEqual(result.classification, "state-inconsistent")
        self.assertEqual(result.normalized_party.slots.count(7), 0)
        self.assertEqual(result.normalized_party.joined_flags & 1, 0)

    def test_ng_plus_stages_unbound_then_later_save_binds_once(self) -> None:
        token = identity()
        retained_source = install_v2(
            valid_sram(), 1, retain=True, sequence=0x4400
        )
        before = bytes(retained_source)
        retained = TOOL.stage_new_game_plus(
            retained_source,
            1,
            prepared_identity=token,
            reset_character_record=pc07_record(),
            reset_name=RESET_NAME,
        )
        self.assertTrue(retained.retained)
        self.assertEqual(retained_source, before)
        self.assertEqual(retained.pending.previous_sequence, 0x4400)
        self.assertEqual(
            retained.pending.origin, TOOL.ORIGIN_NG_PLUS_RETAIN
        )
        self.assertFalse(hasattr(retained.pending, "slot_number"))
        self.assertFalse(hasattr(retained.pending, "binding_digest"))

        destination = valid_sram()
        final_slot, final_metadata = finalized_save_inputs(destination, 2)
        saved = TOOL.execute_normal_save(
            destination,
            2,
            final_slot,
            final_metadata,
            retained.pending,
        )
        self.assertEqual(saved.value.sequence, 0x4401)
        self.assertEqual(saved.value.slot_number, 2)
        self.assertEqual(
            saved.value.binding_digest,
            V2.slot_binding_digest(final_slot, 2),
        )
        self.assertEqual(
            saved.value.character_record,
            retained.pending.character_record,
        )
        self.assertEqual(saved.value.name, retained.pending.name)
        self.assertEqual(
            saved.value.tech_progress, retained.pending.tech_progress
        )
        self.assertEqual(
            saved.value.learned_mask, retained.pending.learned_mask
        )
        self.assertEqual(
            saved.value.combo_state, retained.pending.combo_state
        )
        self.assertEqual(
            saved.value.quest_state, retained.pending.quest_state
        )
        self.assertEqual(saved.value.flags, retained.pending.flags)

        reset_source = install_v2(
            valid_sram(), 1, retain=False, sequence=0x5500
        )
        reset = TOOL.stage_new_game_plus(
            reset_source,
            1,
            prepared_identity=token,
            reset_character_record=pc07_record(),
            reset_name=RESET_NAME,
            reset_prepared_identity=token,
        )
        self.assertFalse(reset.retained)
        self.assertEqual(reset.pending.origin, TOOL.ORIGIN_NG_PLUS_RESET)
        self.assertEqual(reset.pending.tech_progress, 0)
        self.assertEqual(reset.pending.learned_mask, 0)
        self.assertEqual(
            reset.pending.combo_state, bytes(V2.COMBO_STATE_SIZE)
        )
        self.assertEqual(reset.pending.name, RESET_NAME)
        self.assertEqual(reset.pending.flags, V1.FLAG_INITIALIZED)
        self.assertEqual(
            reset.pending.flags & V1.FLAG_NG_PLUS_RETAIN, 0
        )
        self.assertEqual(
            V1.decode_quest_state(reset.pending.quest_state),
            V1.QuestStateV1(),
        )

        destination = valid_sram(
            slot_overrides={3: serialized_slot(3, recruited=False)}
        )
        final_slot, final_metadata = finalized_save_inputs(
            destination, 3, recruited=False
        )
        reset_saved = TOOL.execute_normal_save(
            destination,
            3,
            final_slot,
            final_metadata,
            reset.pending,
        )
        self.assertEqual(reset_saved.value.sequence, 0x5501)
        self.assertEqual(reset_saved.value.slot_number, 3)
        self.assertEqual(reset_saved.value.name, RESET_NAME)
        self.assertEqual(
            reset_saved.value.combo_state, bytes(V2.COMBO_STATE_SIZE)
        )
        self.assertEqual(reset_saved.value.flags, V1.FLAG_INITIALIZED)

        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "identity"
        ):
            TOOL.stage_new_game_plus(
                retained_source,
                1,
                prepared_identity=None,
                reset_character_record=pc07_record(),
                reset_name=RESET_NAME,
            )

    def test_preview_rejects_cross_slot_sequence_and_tail_collision(self) -> None:
        source = install_all_v2(valid_sram())
        token = identity()
        preview = TOOL.prepare_preview_validation(
            source, 1, prepared_identity=token
        )
        epoch_name = source[
            inspect_ct_srm.EPOCH_NAME_OFFSET:
            inspect_ct_srm.EPOCH_NAME_OFFSET + inspect_ct_srm.NAME_LENGTH
        ]
        self.assertEqual(preview.schala_name, SCHALA_NAME)
        self.assertNotEqual(preview.schala_name, epoch_name)
        self.assertIs(
            TOOL.validate_preview_validation(
                preview,
                source,
                1,
                prepared_identity=token,
            ),
            preview,
        )

        with self.assertRaises(TOOL.SidecarLifecycleError):
            TOOL.validate_preview_validation(
                preview,
                source,
                2,
                prepared_identity=token,
            )

        changed_sequence = install_v2(
            source, 1, sequence=preview.sequence + 1
        )
        with self.assertRaises(TOOL.SidecarLifecycleError):
            TOOL.validate_preview_validation(
                preview,
                changed_sequence,
                1,
                prepared_identity=token,
            )

        collision = bytearray(source)
        collision[0x900:0x902], collision[0x902:0x904] = (
            collision[0x902:0x904],
            collision[0x900:0x902],
        )
        collision = bytes(collision)
        original_slot = source[:inspect_ct_srm.SLOT_SIZE]
        collision_slot = collision[:inspect_ct_srm.SLOT_SIZE]
        self.assertNotEqual(original_slot, collision_slot)
        self.assertEqual(
            inspect_ct_srm.slot_checksum(original_slot),
            inspect_ct_srm.slot_checksum(collision_slot),
        )
        self.assertNotEqual(
            V2.slot_binding_digest(original_slot, 1),
            V2.slot_binding_digest(collision_slot, 1),
        )
        collision = install_v2(
            collision, 1, sequence=preview.sequence
        )
        collided_preview = TOOL.prepare_preview_validation(
            collision, 1, prepared_identity=token
        )
        self.assertEqual(collided_preview.sequence, preview.sequence)
        self.assertNotEqual(
            collided_preview.binding_digest, preview.binding_digest
        )
        with self.assertRaises(TOOL.SidecarLifecycleError):
            TOOL.validate_preview_validation(
                preview,
                collision,
                1,
                prepared_identity=token,
            )

        with self.assertRaisesRegex(
            TOOL.SidecarLifecycleError, "identity"
        ):
            TOOL.prepare_preview_validation(
                source, 1, prepared_identity=None
            )

    def test_preview_token_rejects_valid_sidecar_crc16_collision(self) -> None:
        source = install_v2(valid_sram(), 1, sequence=0x6600)
        token = identity()
        preview = TOOL.prepare_preview_validation(
            source, 1, prepared_identity=token
        )
        start = V1.slot_file_offset(1)
        encoded = source[start : start + V2.SIDECAR_SIZE]
        collision = crc16_collision(encoded)
        self.assertNotEqual(encoded, collision)
        self.assertEqual(
            encoded[V2.CHECKSUM_OFFSET : V2.CHECKSUM_OFFSET + 2],
            collision[V2.CHECKSUM_OFFSET : V2.CHECKSUM_OFFSET + 2],
        )
        slot = source[:inspect_ct_srm.SLOT_SIZE]
        self.assertEqual(
            V2.decode_sidecar_v2(
                collision,
                serialized_vanilla_slot=slot,
                expected_slot_number=1,
            ).sequence,
            preview.sequence,
        )
        collided_sram = V2.install_sidecar_v2(source, 1, collision)
        collided_preview = TOOL.prepare_preview_validation(
            collided_sram, 1, prepared_identity=token
        )
        self.assertEqual(
            collided_preview.binding_digest, preview.binding_digest
        )
        self.assertEqual(collided_preview.sequence, preview.sequence)
        self.assertNotEqual(
            collided_preview.sidecar_sha256, preview.sidecar_sha256
        )
        with self.assertRaises(TOOL.SidecarLifecycleError):
            TOOL.validate_preview_validation(
                preview,
                collided_sram,
                1,
                prepared_identity=token,
            )

    def test_exact_slot_erase_order_isolated_for_all_slots(self) -> None:
        source = install_all_v2(valid_sram())
        for slot_number in range(1, inspect_ct_srm.SLOT_COUNT + 1):
            with self.subTest(slot=slot_number):
                start = V1.slot_file_offset(slot_number)
                end = start + V2.SIDECAR_SIZE
                magic_offset = (
                    inspect_ct_srm.MAGIC_TABLE_OFFSET
                    + (slot_number - 1) * 2
                )
                interrupted = TOOL.execute_erase(
                    source,
                    slot_number,
                    fail_after_phase=(
                        TOOL.ERASE_PHASE_SIDECAR_INVALIDATED
                    ),
                )
                expected_interrupted = bytearray(source)
                expected_interrupted[start] = 0xFF
                self.assertEqual(
                    interrupted.sram, bytes(expected_interrupted)
                )
                self.assertTrue(interrupted.sidecar_invalidated)
                self.assertFalse(interrupted.sidecar_cleared)
                self.assertFalse(interrupted.native_magic_invalidated)
                self.assertNotEqual(
                    V2.load_sidecar_v2_from_sram(
                        interrupted.sram, slot_number
                    ).status,
                    "valid",
                )

                for body_count in (0, 1, 3, 0x40, 0x9F):
                    with self.subTest(
                        slot=slot_number, body_count=body_count
                    ):
                        torn = TOOL.execute_erase(
                            source,
                            slot_number,
                            body_bytes_before_failure=body_count,
                        )
                        expected_torn = bytearray(source)
                        expected_torn[start] = 0xFF
                        expected_torn[
                            start + 1:start + 1 + body_count
                        ] = b"\xFF" * body_count
                        self.assertEqual(torn.sram, bytes(expected_torn))
                        self.assertTrue(torn.sidecar_invalidated)
                        self.assertEqual(
                            torn.sidecar_cleared,
                            body_count == V2.SIDECAR_SIZE - 1,
                        )
                        self.assertFalse(
                            torn.native_magic_invalidated
                        )
                        self.assertNotEqual(
                            V2.load_sidecar_v2_from_sram(
                                torn.sram, slot_number
                            ).status,
                            "valid",
                        )

                cleared = TOOL.execute_erase(
                    source,
                    slot_number,
                    fail_after_phase=TOOL.ERASE_PHASE_BODY_CLEARED,
                )
                expected_cleared = bytearray(source)
                expected_cleared[start:end] = (
                    b"\xFF" * V2.SIDECAR_SIZE
                )
                self.assertEqual(cleared.sram, bytes(expected_cleared))
                self.assertTrue(cleared.sidecar_cleared)
                self.assertFalse(cleared.native_magic_invalidated)

                erased = TOOL.execute_erase(source, slot_number)
                expected = bytearray(expected_cleared)
                expected[magic_offset] = (slot_number - 1) * 2
                self.assertEqual(erased.sram, bytes(expected))
                self.assertTrue(erased.sidecar_invalidated)
                self.assertTrue(erased.sidecar_cleared)
                self.assertTrue(erased.native_magic_invalidated)
                self.assertEqual(
                    [
                        entry.phase
                        for entry in erased.trace
                        if entry.operation == "write"
                    ],
                    [
                        TOOL.ERASE_PHASE_SIDECAR_INVALIDATED,
                        TOOL.ERASE_PHASE_BODY_CLEARED,
                        TOOL.ERASE_PHASE_NATIVE_INVALIDATED,
                    ],
                )
                self.assertFalse(
                    inspect_ct_srm.inspect_slot(
                        erased.sram, slot_number
                    )["valid"]
                )
                for other in range(
                    1, inspect_ct_srm.SLOT_COUNT + 1
                ):
                    if other == slot_number:
                        continue
                    other_start = V1.slot_file_offset(other)
                    self.assertEqual(
                        erased.sram[
                            other_start:
                            other_start + V2.SIDECAR_SIZE
                        ],
                        source[
                            other_start:
                            other_start + V2.SIDECAR_SIZE
                        ],
                    )


if __name__ == "__main__":
    unittest.main()
