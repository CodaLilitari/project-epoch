from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

TOOL_PATH = TOOLS_DIR / "schala_sidecar_v2.py"
SPEC = importlib.util.spec_from_file_location("schala_sidecar_v2", TOOL_PATH)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

import inspect_ct_srm
import schala_sidecar as V1


SCHALA_NAME = bytes.fromhex("9C A2 9B 8A A5 AA")


def serialized_slot(seed: int = 17) -> bytes:
    return bytes(
        (index * 29 + seed) & 0xFF
        for index in range(inspect_ct_srm.SLOT_SIZE)
    )


def pc07_record(seed: int = 5) -> bytes:
    return bytes((0x07,)) + bytes(
        (index * 11 + seed) & 0xFF
        for index in range(TOOL.CHARACTER_RECORD_SIZE - 1)
    )


def recruited_quest_state() -> bytes:
    return V1.encode_quest_state(
        V1.QuestStateV1(
            quest_unlocked=True,
            anchor_count=3,
            ward_resolved=True,
            schala_recruited=True,
            join_grant_applied=True,
        )
    )


def sample_v2(
    slot: bytes,
    slot_number: int = 1,
    *,
    sequence: int = 0x1234,
    retain: bool = True,
) -> TOOL.SchalaSidecarV2:
    flags = V1.FLAG_INITIALIZED
    if retain:
        flags |= V1.FLAG_NG_PLUS_RETAIN
    return TOOL.prepare_sidecar_v2(
        character_record=pc07_record(),
        name=SCHALA_NAME,
        tech_progress=3,
        learned_mask=0xE0,
        combo_state=bytes(range(0x10, 0x20)),
        quest_state=recruited_quest_state(),
        flags=flags,
        sequence=sequence,
        serialized_vanilla_slot=slot,
        slot_number=slot_number,
    )


def sample_v1(
    slot: bytes,
    *,
    sequence: int = 0x1234,
    retain: bool = True,
) -> V1.SchalaSidecarV1:
    flags = V1.FLAG_INITIALIZED
    if retain:
        flags |= V1.FLAG_NG_PLUS_RETAIN
    return V1.SchalaSidecarV1(
        character_record=pc07_record(),
        name=SCHALA_NAME,
        tech_progress=3,
        learned_mask=0xE0,
        combo_state=bytes(range(0x10, 0x20)),
        quest_state=recruited_quest_state(),
        reserved=bytes(V1.RESERVED_SIZE),
        flags=flags,
        sequence=sequence,
        vanilla_slot_checksum=inspect_ct_srm.slot_checksum(slot),
    )


def valid_sram(slot: bytes, slot_number: int = 1) -> bytes:
    result = bytearray(
        (index * 13 + 5) & 0xFF
        for index in range(inspect_ct_srm.SRAM_SIZE)
    )
    slot_base = (slot_number - 1) * inspect_ct_srm.SLOT_SIZE
    result[slot_base : slot_base + inspect_ct_srm.SLOT_SIZE] = slot
    metadata_index = (slot_number - 1) * 2
    result[
        inspect_ct_srm.CHECKSUM_TABLE_OFFSET
        + metadata_index : inspect_ct_srm.CHECKSUM_TABLE_OFFSET
        + metadata_index
        + 2
    ] = inspect_ct_srm.slot_checksum(slot).to_bytes(2, "little")
    result[
        inspect_ct_srm.MAGIC_TABLE_OFFSET
        + metadata_index : inspect_ct_srm.MAGIC_TABLE_OFFSET
        + metadata_index
        + 2
    ] = inspect_ct_srm.SLOT_MAGIC.to_bytes(2, "little")
    return bytes(result)


def reseal_crc(encoded: bytes) -> bytes:
    result = bytearray(encoded)
    result[TOOL.CHECKSUM_OFFSET : TOOL.CHECKSUM_OFFSET + 2] = b"\x00\x00"
    crc = V1.crc16_ccitt_false(result)
    result[
        TOOL.CHECKSUM_OFFSET : TOOL.CHECKSUM_OFFSET + 2
    ] = crc.to_bytes(2, "little")
    return bytes(result)


def v1_source_sram(
    slot: bytes,
    slot_number: int = 1,
    *,
    sequence: int = 0x1234,
) -> tuple[bytes, bytes, V1.SchalaSidecarV1]:
    source = valid_sram(slot, slot_number)
    value = sample_v1(slot, sequence=sequence)
    encoded = V1.encode_sidecar(value)
    return V1.install_sidecar(source, slot_number, encoded), encoded, value


class SchalaSidecarV2Tests(unittest.TestCase):
    def test_layout_trailer_and_all_zero_digest_vector(self) -> None:
        self.assertEqual(TOOL.SIDECAR_SIZE, 0xA0)
        self.assertEqual(TOOL.SLOT_IDENTITY_OFFSET, 0x0E)
        self.assertEqual(TOOL.BINDING_PROFILE_OFFSET, 0x0F)
        self.assertEqual(TOOL.BINDING_DIGEST_OFFSET, 0x80)
        self.assertEqual(TOOL.BINDING_DIGEST_SIZE, 0x20)

        trailer = TOOL.binding_trailer(1)
        self.assertEqual(len(trailer), 0x10)
        self.assertEqual(
            trailer.hex(), "5045303742494e4402010100000a0000"
        )
        self.assertEqual(
            TOOL.slot_binding_digest(bytes(inspect_ct_srm.SLOT_SIZE), 1).hex(),
            "878829ba5210cd4d1defacbedb6c485407a25dc8be2cf46a"
            "e2bd90636b9ebdbd",
        )
        self.assertNotEqual(
            TOOL.slot_binding_digest(bytes(inspect_ct_srm.SLOT_SIZE), 1),
            TOOL.slot_binding_digest(bytes(inspect_ct_srm.SLOT_SIZE), 2),
        )

    def test_round_trip_and_exact_offsets(self) -> None:
        slot = serialized_slot()
        value = sample_v2(slot)
        encoded = TOOL.encode_sidecar_v2(value, slot)

        self.assertEqual(len(encoded), 0xA0)
        self.assertEqual(encoded[0x00:0x04], V1.MAGIC)
        self.assertEqual(encoded[0x04], 2)
        self.assertEqual(encoded[0x05], value.flags)
        self.assertEqual(
            int.from_bytes(encoded[0x06:0x08], "little"), V1.PAYLOAD_LENGTH
        )
        self.assertEqual(
            int.from_bytes(encoded[0x08:0x0A], "little"), value.sequence
        )
        self.assertEqual(
            int.from_bytes(encoded[0x0C:0x0E], "little"),
            inspect_ct_srm.slot_checksum(slot),
        )
        self.assertEqual(encoded[0x0E], 1)
        self.assertEqual(encoded[0x0F], 1)
        self.assertEqual(encoded[0x10:0x60], value.character_record)
        self.assertEqual(encoded[0x60:0x66], value.name)
        self.assertEqual(encoded[0x66], 3)
        self.assertEqual(encoded[0x67], 0xE0)
        self.assertEqual(encoded[0x68:0x78], value.combo_state)
        self.assertEqual(encoded[0x78:0x80], value.quest_state)
        self.assertEqual(encoded[0x80:0xA0], value.binding_digest)

        crc_input = bytearray(encoded)
        stored_crc = int.from_bytes(encoded[0x0A:0x0C], "little")
        crc_input[0x0A:0x0C] = b"\x00\x00"
        self.assertEqual(stored_crc, V1.crc16_ccitt_false(crc_input))
        self.assertEqual(TOOL.decode_sidecar_v2(encoded), value)
        self.assertEqual(
            TOOL.decode_sidecar_v2(
                encoded,
                serialized_vanilla_slot=slot,
                expected_slot_number=1,
            ),
            value,
        )
        classified = TOOL.classify_versioned_sidecar(encoded, slot, 1)
        self.assertEqual(classified.status, "valid")
        self.assertEqual(classified.version, 2)
        self.assertEqual(classified.value, value)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            value.slot_number = 2

    def test_crc_and_structural_header_corruption_are_invalid(self) -> None:
        slot = serialized_slot()
        encoded = TOOL.encode_sidecar_v2(sample_v2(slot), slot)

        corrupt_crc = bytearray(encoded)
        corrupt_crc[0x0A] ^= 0x01
        with self.assertRaisesRegex(TOOL.SidecarV2Error, "CRC mismatch"):
            TOOL.decode_sidecar_v2(bytes(corrupt_crc))

        cases = (
            (0x00, encoded[0x00] ^ 0x01, "magic"),
            (0x05, 0x81, "unknown header"),
            (0x06, encoded[0x06] ^ 0x01, "payload length"),
            (0x0E, 0x00, "slot_number"),
            (0x0F, 0x02, "binding profile"),
        )
        for offset, replacement, message in cases:
            with self.subTest(offset=offset):
                corrupt = bytearray(encoded)
                corrupt[offset] = replacement
                corrupt = reseal_crc(bytes(corrupt))
                with self.assertRaisesRegex(TOOL.SidecarV2Error, message):
                    TOOL.decode_sidecar_v2(corrupt)
                result = TOOL.classify_versioned_sidecar(corrupt, slot, 1)
                self.assertEqual(result.status, "invalid")
                self.assertIsNone(result.value)

    def test_digest_corruption_requires_both_crc_and_sha_validation(self) -> None:
        slot = serialized_slot()
        encoded = TOOL.encode_sidecar_v2(sample_v2(slot), slot)
        corrupt = bytearray(encoded)
        corrupt[0x80] ^= 0x80

        with self.assertRaisesRegex(TOOL.SidecarV2Error, "CRC mismatch"):
            TOOL.decode_sidecar_v2(bytes(corrupt))

        resealed = reseal_crc(bytes(corrupt))
        structurally_decoded = TOOL.decode_sidecar_v2(resealed)
        self.assertNotEqual(
            structurally_decoded.binding_digest,
            TOOL.slot_binding_digest(slot, 1),
        )
        with self.assertRaisesRegex(TOOL.SidecarV2Error, "SHA-256"):
            TOOL.decode_sidecar_v2(
                resealed,
                serialized_vanilla_slot=slot,
                expected_slot_number=1,
            )
        classified = TOOL.classify_sidecar_v2(resealed, slot, 1)
        self.assertEqual(classified.status, "stale")
        self.assertIsNone(classified.value)

    def test_wrong_slot_profile_and_unknown_version_never_fall_back(self) -> None:
        slot = serialized_slot()
        encoded = TOOL.encode_sidecar_v2(sample_v2(slot), slot)

        wrong_slot = TOOL.classify_versioned_sidecar(encoded, slot, 2)
        self.assertEqual(wrong_slot.status, "stale")
        self.assertIsNone(wrong_slot.value)
        with self.assertRaisesRegex(TOOL.SidecarV2Error, "physical slot"):
            TOOL.decode_sidecar_v2(
                encoded,
                serialized_vanilla_slot=slot,
                expected_slot_number=2,
            )

        wrong_profile = bytearray(encoded)
        wrong_profile[0x0F] = 2
        wrong_profile = reseal_crc(bytes(wrong_profile))
        profile_result = TOOL.classify_versioned_sidecar(
            wrong_profile, slot, 1
        )
        self.assertEqual(profile_result.status, "invalid")
        self.assertIsNone(profile_result.value)

        unknown_version = bytearray(encoded)
        unknown_version[0x04] = 3
        unknown_version = reseal_crc(bytes(unknown_version))
        unknown = TOOL.classify_versioned_sidecar(
            unknown_version, slot, 1
        )
        self.assertEqual(unknown.status, "invalid")
        self.assertEqual(unknown.version, 3)
        self.assertIsNone(unknown.value)
        self.assertIn("unsupported sidecar version 3", unknown.detail)

        v2_disguised_as_v1 = bytearray(encoded)
        v2_disguised_as_v1[0x04] = V1.VERSION
        v2_disguised_as_v1 = reseal_crc(bytes(v2_disguised_as_v1))
        disguised = TOOL.classify_versioned_sidecar(
            v2_disguised_as_v1, slot, 1
        )
        self.assertEqual(disguised.status, "invalid")
        self.assertEqual(disguised.version, V1.VERSION)
        self.assertIsNone(disguised.value)

    def test_slot_byte_flip_and_vanilla_checksum_collision_are_stale(self) -> None:
        slot1 = serialized_slot()
        encoded = TOOL.encode_sidecar_v2(sample_v2(slot1), slot1)

        flipped = bytearray(slot1)
        flipped[0x42] ^= 0x80
        flipped_result = TOOL.classify_sidecar_v2(
            encoded, bytes(flipped), 1
        )
        self.assertEqual(flipped_result.status, "stale")
        self.assertIsNone(flipped_result.value)

        collision = bytearray(slot1)
        collision[0:2], collision[2:4] = collision[2:4], collision[0:2]
        collision = bytes(collision)
        self.assertNotEqual(slot1, collision)
        self.assertEqual(
            inspect_ct_srm.slot_checksum(slot1),
            inspect_ct_srm.slot_checksum(collision),
        )
        self.assertNotEqual(
            TOOL.slot_binding_digest(slot1, 1),
            TOOL.slot_binding_digest(collision, 1),
        )
        collision_result = TOOL.classify_sidecar_v2(
            encoded, collision, 1
        )
        self.assertEqual(collision_result.status, "stale")
        self.assertIsNone(collision_result.value)
        self.assertIn("SHA-256", collision_result.detail)

        copied_to_slot2 = TOOL.classify_sidecar_v2(
            encoded, collision, 2
        )
        self.assertEqual(copied_to_slot2.status, "stale")
        self.assertIsNone(copied_to_slot2.value)
        self.assertIn("physical slot", copied_to_slot2.detail)

    def test_identical_slot_bodies_remain_cross_slot_bound(self) -> None:
        slot = serialized_slot()
        value1 = sample_v2(slot, 1)
        value2 = sample_v2(slot, 2)
        encoded1 = TOOL.encode_sidecar_v2(value1, slot)

        self.assertNotEqual(value1.binding_digest, value2.binding_digest)
        self.assertEqual(
            TOOL.classify_sidecar_v2(encoded1, slot, 2).status, "stale"
        )

        changed_identity = bytearray(encoded1)
        changed_identity[0x0E] = 2
        changed_identity = reseal_crc(bytes(changed_identity))
        result = TOOL.classify_sidecar_v2(changed_identity, slot, 2)
        self.assertEqual(result.status, "stale")
        self.assertIsNone(result.value)
        self.assertIn("SHA-256", result.detail)

    def test_install_preserves_every_byte_outside_selected_record(self) -> None:
        slot = serialized_slot(31)
        source = valid_sram(slot, 2)
        value = sample_v2(slot, 2)
        encoded = TOOL.encode_sidecar_v2(value, slot)
        start = V1.slot_file_offset(2)
        end = start + TOOL.SIDECAR_SIZE

        installed = TOOL.install_sidecar_v2(source, 2, encoded)
        self.assertEqual(installed[:start], source[:start])
        self.assertEqual(installed[start:end], encoded)
        self.assertEqual(installed[end:], source[end:])
        loaded = TOOL.load_sidecar_v2_from_sram(installed, 2)
        self.assertEqual(loaded.status, "valid")
        self.assertEqual(loaded.value, value)

        wrong_slot_record = TOOL.encode_sidecar_v2(
            sample_v2(slot, 1), slot
        )
        with self.assertRaisesRegex(TOOL.SidecarV2Error, "installation refused"):
            TOOL.install_sidecar_v2(source, 2, wrong_slot_record)

        invalid_metadata = bytearray(source)
        invalid_metadata[inspect_ct_srm.MAGIC_TABLE_OFFSET + 2] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.SidecarV2Error, "checksum and magic"
        ):
            TOOL.install_sidecar_v2(
                bytes(invalid_metadata), 2, encoded
            )

    def test_full_sram_loader_refuses_invalid_vanilla_metadata(self) -> None:
        """A high-level SRAM load must not bypass vanilla validity."""

        slot = serialized_slot()
        source = valid_sram(slot, 1)
        encoded = TOOL.encode_sidecar_v2(sample_v2(slot), slot)
        installed = TOOL.install_sidecar_v2(source, 1, encoded)

        cases = []
        bad_magic = bytearray(installed)
        bad_magic[inspect_ct_srm.MAGIC_TABLE_OFFSET] ^= 0x01
        cases.append(bytes(bad_magic))
        bad_checksum = bytearray(installed)
        bad_checksum[inspect_ct_srm.CHECKSUM_TABLE_OFFSET] ^= 0x01
        cases.append(bytes(bad_checksum))

        for invalid_sram in cases:
            with self.subTest(
                source_sha256=hashlib.sha256(invalid_sram).hexdigest()
            ):
                result = TOOL.load_sidecar_v2_from_sram(invalid_sram, 1)
                self.assertNotEqual(result.status, "valid")
                self.assertIsNone(result.value)

    def test_v1_requires_explicit_migration_authorization(self) -> None:
        slot = serialized_slot()
        source, encoded_v1, legacy = v1_source_sram(slot)
        classified = TOOL.load_sidecar_v2_from_sram(source, 1)
        self.assertEqual(
            classified.status, "legacy-v1-migration-required"
        )
        self.assertEqual(classified.version, V1.VERSION)
        self.assertIsNone(classified.value)
        self.assertEqual(encoded_v1[0x0E:0x10], b"\x00\x00")
        self.assertEqual(encoded_v1[0x80:0xA0], bytes(0x20))

        for reviewed in (False, 1):
            with self.subTest(reviewed=reviewed):
                with self.assertRaisesRegex(
                    TOOL.SidecarV2Error, "explicit selected-slot"
                ):
                    TOOL.prepare_v1_migration_authorization(
                        source,
                        1,
                        selected_slot_provenance_reviewed=reviewed,
                    )
        with self.assertRaisesRegex(
            TOOL.SidecarV2Error, "exact authorization"
        ):
            TOOL.migrate_v1_sidecar_in_sram(source, 1, object())

        authorization = TOOL.prepare_v1_migration_authorization(
            source, 1, selected_slot_provenance_reviewed=True
        )
        self.assertEqual(
            authorization.source_sram_sha256, TOOL.sha256(source)
        )
        self.assertEqual(
            authorization.source_v1_sha256, TOOL.sha256(encoded_v1)
        )
        self.assertEqual(
            authorization.serialized_slot_sha256, TOOL.sha256(slot)
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            authorization.slot_number = 2

        migrated = TOOL.migrate_v1_sidecar_in_sram(
            source, 1, authorization
        )
        start = V1.slot_file_offset(1)
        end = start + TOOL.SIDECAR_SIZE
        self.assertEqual(migrated[:start], source[:start])
        self.assertEqual(migrated[end:], source[end:])
        loaded = TOOL.load_sidecar_v2_from_sram(migrated, 1)
        self.assertEqual(loaded.status, "valid")
        self.assertIsNotNone(loaded.value)
        assert loaded.value is not None
        self.assertEqual(loaded.value.character_record, legacy.character_record)
        self.assertEqual(loaded.value.name, legacy.name)
        self.assertEqual(loaded.value.tech_progress, legacy.tech_progress)
        self.assertEqual(loaded.value.learned_mask, legacy.learned_mask)
        self.assertEqual(loaded.value.combo_state, legacy.combo_state)
        self.assertEqual(loaded.value.quest_state, legacy.quest_state)
        self.assertEqual(loaded.value.flags, legacy.flags)
        self.assertEqual(loaded.value.sequence, legacy.sequence + 1)
        self.assertEqual(loaded.value.slot_number, 1)

    def test_migration_authorization_is_source_bound_and_exact_type(self) -> None:
        slot = serialized_slot()
        source, _, _ = v1_source_sram(slot)
        authorization = TOOL.prepare_v1_migration_authorization(
            source, 1, selected_slot_provenance_reviewed=True
        )

        altered_source = bytearray(source)
        altered_source[inspect_ct_srm.SLOT_SIZE] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.SidecarV2Error, "not bound to this source"
        ):
            TOOL.migrate_v1_sidecar_in_sram(
                bytes(altered_source), 1, authorization
            )

        forged = dataclasses.replace(
            authorization, evidence_level="verified-runtime", seal=""
        )
        forged = dataclasses.replace(
            forged, seal=TOOL._migration_authorization_seal(forged)
        )
        with self.assertRaises(TOOL.SidecarV2Error):
            TOOL.migrate_v1_sidecar_in_sram(source, 1, forged)

        class AuthorizationSubclass(TOOL.V1MigrationAuthorization):
            pass

        polymorphic = AuthorizationSubclass(
            **dataclasses.asdict(authorization)
        )
        with self.assertRaisesRegex(TOOL.SidecarV2Error, "exact"):
            TOOL.migrate_v1_sidecar_in_sram(source, 1, polymorphic)

        stale_source, _, _ = v1_source_sram(slot)
        stale = bytearray(stale_source)
        start = V1.slot_file_offset(1)
        stale[start + 0x0C] ^= 0x01
        stale[start : start + TOOL.SIDECAR_SIZE] = reseal_crc(
            bytes(stale[start : start + TOOL.SIDECAR_SIZE])
        )
        with self.assertRaisesRegex(
            TOOL.SidecarV2Error, "valid legacy record"
        ):
            TOOL.prepare_v1_migration_authorization(
                bytes(stale),
                1,
                selected_slot_provenance_reviewed=True,
            )

    def test_migration_sequence_saturates(self) -> None:
        slot = serialized_slot()
        source, _, _ = v1_source_sram(slot, sequence=0xFFFF)
        authorization = TOOL.prepare_v1_migration_authorization(
            source, 1, selected_slot_provenance_reviewed=True
        )
        migrated = TOOL.migrate_v1_sidecar_in_sram(
            source, 1, authorization
        )
        loaded = TOOL.load_sidecar_v2_from_sram(migrated, 1)
        self.assertEqual(loaded.status, "valid")
        assert loaded.value is not None
        self.assertEqual(loaded.value.sequence, 0xFFFF)

    def test_new_game_plus_retain_and_reset_rebind_destination(self) -> None:
        source_slot = serialized_slot(17)
        destination_slot = serialized_slot(43)
        retained_source = sample_v2(source_slot, 1, retain=True)
        reset_record = pc07_record(29)
        reset_name = b"RESET!"

        retained = TOOL.prepare_new_game_plus_v2_for_serialized_save(
            retained_source,
            source_serialized_slot=source_slot,
            destination_serialized_slot=destination_slot,
            destination_slot_number=3,
            reset_character_record=reset_record,
            reset_name=reset_name,
        )
        self.assertEqual(retained.character_record, retained_source.character_record)
        self.assertEqual(retained.name, retained_source.name)
        self.assertEqual(retained.tech_progress, retained_source.tech_progress)
        self.assertEqual(retained.learned_mask, retained_source.learned_mask)
        self.assertEqual(retained.combo_state, retained_source.combo_state)
        self.assertEqual(retained.quest_state, retained_source.quest_state)
        self.assertEqual(retained.flags, retained_source.flags)
        self.assertEqual(retained.sequence, retained_source.sequence + 1)
        self.assertEqual(retained.slot_number, 3)
        self.assertEqual(
            retained.binding_digest,
            TOOL.slot_binding_digest(destination_slot, 3),
        )
        retained_encoded = TOOL.encode_sidecar_v2(
            retained, destination_slot
        )
        self.assertEqual(
            TOOL.decode_sidecar_v2(
                retained_encoded,
                serialized_vanilla_slot=destination_slot,
                expected_slot_number=3,
            ),
            retained,
        )

        reset_source = sample_v2(source_slot, 1, retain=False)
        reset = TOOL.prepare_new_game_plus_v2_for_serialized_save(
            reset_source,
            source_serialized_slot=source_slot,
            destination_serialized_slot=destination_slot,
            destination_slot_number=2,
            reset_character_record=reset_record,
            reset_name=reset_name,
        )
        self.assertEqual(reset.character_record, reset_record)
        self.assertEqual(reset.name, reset_name)
        self.assertEqual(reset.tech_progress, 0)
        self.assertEqual(reset.learned_mask, 0)
        self.assertEqual(reset.combo_state, bytes(TOOL.COMBO_STATE_SIZE))
        self.assertEqual(
            V1.decode_quest_state(reset.quest_state), V1.QuestStateV1()
        )
        self.assertEqual(reset.flags, V1.FLAG_INITIALIZED)
        self.assertEqual(reset.sequence, reset_source.sequence + 1)
        self.assertEqual(reset.slot_number, 2)
        self.assertEqual(
            reset.binding_digest,
            TOOL.slot_binding_digest(destination_slot, 2),
        )

        saturated_source = sample_v2(
            source_slot, 1, sequence=0xFFFF, retain=True
        )
        saturated = TOOL.prepare_new_game_plus_v2_for_serialized_save(
            saturated_source,
            source_serialized_slot=source_slot,
            destination_serialized_slot=destination_slot,
            destination_slot_number=2,
            reset_character_record=reset_record,
            reset_name=reset_name,
        )
        self.assertEqual(saturated.sequence, 0xFFFF)

    def test_new_game_plus_rejects_stale_source_binding(self) -> None:
        source_slot = serialized_slot()
        destination_slot = serialized_slot(41)
        source = sample_v2(source_slot, 1)
        collision = bytearray(source_slot)
        collision[0:2], collision[2:4] = collision[2:4], collision[0:2]
        collision = bytes(collision)
        self.assertEqual(
            inspect_ct_srm.slot_checksum(source_slot),
            inspect_ct_srm.slot_checksum(collision),
        )

        with self.assertRaisesRegex(TOOL.SidecarV2Error, "SHA-256"):
            TOOL.prepare_new_game_plus_v2_for_serialized_save(
                source,
                source_serialized_slot=collision,
                destination_serialized_slot=destination_slot,
                destination_slot_number=2,
                reset_character_record=pc07_record(23),
                reset_name=b"RESET!",
            )

    def test_new_game_plus_is_a_value_transform_not_physical_source_proof(
        self,
    ) -> None:
        """Pin the exposed boundary: callers must supply a validated source."""

        identical_body = serialized_slot()
        destination_slot = serialized_slot(61)
        source_for_slot1 = sample_v2(identical_body, 1)
        source_for_slot2 = sample_v2(identical_body, 2)
        result1 = TOOL.prepare_new_game_plus_v2_for_serialized_save(
            source_for_slot1,
            source_serialized_slot=identical_body,
            destination_serialized_slot=destination_slot,
            destination_slot_number=3,
            reset_character_record=pc07_record(31),
            reset_name=b"RESET!",
        )
        result2 = TOOL.prepare_new_game_plus_v2_for_serialized_save(
            source_for_slot2,
            source_serialized_slot=identical_body,
            destination_serialized_slot=destination_slot,
            destination_slot_number=3,
            reset_character_record=pc07_record(31),
            reset_name=b"RESET!",
        )
        self.assertEqual(result1, result2)

    def test_exact_type_rejection(self) -> None:
        slot = serialized_slot()
        value = sample_v2(slot)
        encoded = TOOL.encode_sidecar_v2(value, slot)

        class IntSubclass(int):
            pass

        class BytesSubclass(bytes):
            pass

        class ValueSubclass(TOOL.SchalaSidecarV2):
            pass

        polymorphic_value = ValueSubclass(**dataclasses.asdict(value))
        calls = (
            lambda: TOOL.binding_trailer(True),
            lambda: TOOL.binding_trailer(IntSubclass(1)),
            lambda: TOOL.slot_binding_digest(bytearray(slot), 1),
            lambda: TOOL.slot_binding_digest(BytesSubclass(slot), 1),
            lambda: TOOL.prepare_sidecar_v2(
                character_record=value.character_record,
                name=value.name,
                tech_progress=value.tech_progress,
                learned_mask=value.learned_mask,
                combo_state=value.combo_state,
                quest_state=value.quest_state,
                flags=value.flags,
                sequence=True,
                serialized_vanilla_slot=slot,
                slot_number=1,
            ),
            lambda: TOOL.prepare_sidecar_v2(
                character_record=value.character_record,
                name=value.name,
                tech_progress=value.tech_progress,
                learned_mask=value.learned_mask,
                combo_state=value.combo_state,
                quest_state=value.quest_state,
                flags=value.flags,
                sequence=value.sequence,
                serialized_vanilla_slot=slot,
                slot_number=True,
            ),
            lambda: TOOL.encode_sidecar_v2(polymorphic_value, slot),
            lambda: TOOL.decode_sidecar_v2(BytesSubclass(encoded)),
            lambda: TOOL.decode_sidecar_v2(
                encoded, serialized_vanilla_slot=slot
            ),
            lambda: TOOL.install_sidecar_v2(
                bytearray(valid_sram(slot)), 1, encoded
            ),
        )
        for index, call in enumerate(calls):
            with self.subTest(index=index):
                with self.assertRaises(TOOL.SidecarV2Error):
                    call()

    def test_torn_or_precommit_magic_last_records_never_publish(self) -> None:
        slot = serialized_slot()
        encoded = TOOL.encode_sidecar_v2(sample_v2(slot), slot)

        for cut in (1, 4, 0x10, 0x80, 0xA0):
            torn = bytearray(b"\xFF" * TOOL.SIDECAR_SIZE)
            torn[0] = 0
            torn[1:cut] = encoded[1:cut]
            with self.subTest(cut=cut):
                result = TOOL.classify_versioned_sidecar(
                    bytes(torn), slot, 1
                )
                self.assertNotEqual(result.status, "valid")
                self.assertIsNone(result.value)

        staged = bytearray(encoded)
        staged[0] = 0
        precommit = TOOL.classify_versioned_sidecar(
            bytes(staged), slot, 1
        )
        self.assertEqual(precommit.status, "invalid")
        self.assertIsNone(precommit.value)

        staged[0] = encoded[0]
        committed = TOOL.classify_versioned_sidecar(
            bytes(staged), slot, 1
        )
        self.assertEqual(committed.status, "valid")
        self.assertEqual(committed.value, sample_v2(slot))


if __name__ == "__main__":
    unittest.main()
