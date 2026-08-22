from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_mesen_event11c_relocated_trace.py"


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_module("validate_mesen_event11c_relocated_trace", TOOL_PATH)

PINNED_SOURCE_COMPATIBILITY_SHA256 = (
    TOOL.EXPECTED_SOURCE_COMPATIBILITY_SHA256
)
SOURCE_COMPATIBILITY = (
    bytes.fromhex("08080808080808ffffffffffffff")
    + bytes((index * 37 + 11) & 0xFF for index in range(66))
)
TOOL.EXPECTED_SOURCE_COMPATIBILITY_SHA256 = hashlib.sha256(
    SOURCE_COMPATIBILITY
).hexdigest()

CALLBACK_ROWS = {
    "crono-marle-lucca": (
        (0x05C0, 0x4C, 793, "write", 0x7E2CA0, 0x03),
        (0x05C5, 0x48, 793, "read", 0x7E2CA7, 0x1F),
        (0x05CD, 0x4C, 793, "write", 0x7E2CA7, 0xFF),
        (0x0609, 0x4C, 1086, "write", 0x7E2CA1, 0x03),
        (0x060E, 0x48, 1090, "read", 0x7E2CA8, 0x1F),
        (0x0616, 0x4C, 1090, "write", 0x7E2CA8, 0xFF),
        (0x0652, 0x4C, 1875, "write", 0x7E2CA2, 0x03),
        (0x0657, 0x48, 1879, "read", 0x7E2CA9, 0x1F),
        (0x065F, 0x4C, 1879, "write", 0x7E2CA9, 0xFF),
    ),
    "frog-robo": (
        (0x06B4, 0x4C, 985, "write", 0x7E2CA4, 0x03),
        (0x06B9, 0x48, 989, "read", 0x7E2CAB, 0x1F),
        (0x06C1, 0x4C, 989, "write", 0x7E2CAB, 0xFF),
    ),
}


def prepared_candidate(profile: str) -> bytes:
    result = bytearray(SOURCE_COMPATIBILITY)
    if profile == "crono-marle-lucca":
        count_indices = (0, 1, 2)
        mask_indices = (0, 1, 2)
    else:
        count_indices = (4,)
        mask_indices = (4,)
    for index in count_indices:
        result[index] = 0
    for index in mask_indices:
        result[7 + index] &= 0x1F
    return bytes(result)


def terminal_candidate(profile: str) -> bytes:
    result = bytearray(prepared_candidate(profile))
    if profile == "crono-marle-lucca":
        count_indices = (0, 1, 2)
        mask_indices = (0, 1, 2)
    else:
        count_indices = (4,)
        mask_indices = (4,)
    for index in count_indices:
        result[index] = 3
    for index in mask_indices:
        result[7 + index] = 0xFF
    return bytes(result)


def expected_old_block(variant: str) -> bytes:
    result = bytearray(SOURCE_COMPATIBILITY)
    result[:12] = (
        bytes(12)
        if variant == "zero"
        else bytes.fromhex("471eea9705fecea2040cc7e0")
    )
    return bytes(result)


def packet() -> dict[str, object]:
    return {
        "base_wram_offset": 0x12000,
        "length": 0x0C6B,
        "source_sha256": (
            "31d5b222828eca6c1c91a309f1543a8f"
            "dccf2e2f5deea7a4074b7376eaa70d8a"
        ),
        "transformed_sha256": (
            "8e2952bd5e8c25eaf0ad4244dece929b"
            "6f4fc1eea8317ea707fcd782c898e50b"
        ),
        "changed_byte_count": 24,
        "edit_count": 12,
        "edits": [copy.deepcopy(edit) for edit in TOOL.EXPECTED_PACKET_EDITS],
        "live_source_match_before": True,
        "exact_expected_diff": True,
        "live_transformed_match_after_prepare": True,
        "live_transformed_match_at_end": True,
    }


def observer() -> dict[str, object]:
    return {
        "read_pc24": 0xC06797,
        "read_mapped_address": 0x6797,
        "read_mapping_is_prg_rom": True,
        "write_pc24": 0xC06822,
        "write_mapped_address": 0x6822,
        "write_mapping_is_prg_rom": True,
        "mechanism": "broad-exec-callback-exact-pc-router",
        "checkpoint_direct_page": 0x0100,
    }


def callbacks(profile: str) -> list[dict[str, object]]:
    records = []
    for seq, (
        command_offset,
        opcode,
        frame,
        access,
        address,
        value,
    ) in enumerate(CALLBACK_ROWS[profile]):
        records.append(
            {
                "seq": seq,
                "frame": frame,
                "access": access,
                "address": address,
                "raw_wram_offset": address - 0x7E0000,
                "value": value,
                "pc24": 0xC06797 if access == "read" else 0xC06822,
                "cpu_y": command_offset,
                "command_offset": command_offset,
                "opcode_offset": command_offset + 1,
                "opcode": opcode,
                "operand_offset": command_offset + 2,
                "operand_address": address,
                "direct_page": 0x0100,
                "memory_flag_set": True,
                "accumulator": None if access == "read" else value,
                "deferred_value": None if access == "read" else value,
            }
        )
    return records


def snapshot(
    profile: str,
    variant: str,
    *,
    post: bool,
) -> dict[str, object]:
    if profile == "crono-marle-lucca":
        active_party = "000102"
        pre_magic = 0x18
        post_dialog = 2
        pre_counts = "00000008080808"
        post_counts = "03030308080808"
        pre_masks = "1f1f1fffffffff"
    else:
        active_party = "060403"
        pre_magic = 0x47
        post_dialog = 0
        pre_counts = "08080808000808"
        post_counts = "08080808030808"
        pre_masks = "ffffffff1fffff"
    candidate = (
        terminal_candidate(profile) if post else prepared_candidate(profile)
    )
    return {
        "location": 0x01D1,
        "storyline": 0x4D if post else 0x4C,
        "lap_scratch": 3,
        "magic_flags": 0x5F if post else pre_magic,
        "robo_flags": 0,
        "explore_mode": 0 if post else 1,
        "dialog_state": post_dialog if post else 0,
        "leader_x": 1925 if post else 1568,
        "leader_y": 3061 if post else 2623,
        "active_party_hex": active_party,
        "candidate_tech_counts_hex": (
            post_counts if post else pre_counts
        ),
        "candidate_learned_masks_hex": (
            "ffffffffffffff" if post else pre_masks
        ),
        "old_block_hex": expected_old_block(variant).hex(),
        "candidate_hex": candidate.hex(),
        "old_block_matches_variant": True,
        "candidate_non_target_preserved": True,
        "front_guard_hex": "00000000",
        "rear_guard_hex": "00000000000000000000000000000000",
        "epoch_name_hex": "a4c9c8bcc100",
    }


def make_trace(profile: str, variant: str) -> dict[str, object]:
    return {
        "schema": "project-epoch-mesen-event11c-relocated-trace-v2",
        "collector_version": 2,
        "profile": profile,
        "variant": variant,
        "collector_explicit_write_scope": (
            "snes-work-ram-via-write8-write16-only"
        ),
        "source_compatibility_hex": SOURCE_COMPATIBILITY.hex(),
        "candidate_copy_match_before_profile": True,
        "packet": packet(),
        "observer": observer(),
        "pre": snapshot(profile, variant, post=False),
        "callbacks": callbacks(profile),
        "post": snapshot(profile, variant, post=True),
        "termination": {
            "collector_stopped": True,
            "success": True,
            "overflow": False,
            "observer_error": None,
            "screenshot_phase_mod16": 0,
            "spekkio_sprite_frame": (
                4 if profile == "crono-marle-lucca" else 22
            ),
            "unexpected_accesses": 0,
        },
    }


def make_trace_set() -> list[dict[str, object]]:
    return [
        make_trace(profile, variant)
        for profile in ("crono-marle-lucca", "frog-robo")
        for variant in ("zero", "canary")
    ]


class MesenEvent11CRelocatedTraceTests(unittest.TestCase):
    def test_pins_checkpoint_source_hash_without_raw_block(self) -> None:
        self.assertEqual(
            PINNED_SOURCE_COMPATIBILITY_SHA256,
            "6007023eefa73f3f9c70da546f921dce"
            "866d3131e8c98ba978785f7ac28f82c1",
        )
        source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "08080808080808ffffffffffffffe0e0",
            source,
        )

    def test_accepts_exact_four_trace_contract(self) -> None:
        report = TOOL.validate_trace_documents(make_trace_set())
        self.assertEqual(report["trace_count"], 4)
        self.assertTrue(report["candidate_pairs_identical"])

    def test_rejects_packet_identity_or_flag_drift(self) -> None:
        mutations = (
            ("base_wram_offset", 0x10400),
            ("length", 0x0C6A),
            ("source_sha256", "0" * 64),
            ("transformed_sha256", "f" * 64),
            ("changed_byte_count", 23),
            ("edit_count", 11),
            ("live_source_match_before", False),
            ("exact_expected_diff", False),
            ("live_transformed_match_after_prepare", False),
            ("live_transformed_match_at_end", False),
        )
        for field, replacement in mutations:
            trace = make_trace("frog-robo", "zero")
            trace["packet"][field] = replacement
            with self.subTest(field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_any_packet_edit_metadata_drift(self) -> None:
        for field, replacement in (
            ("event_data_command_offset", 0x05BF),
            ("opcode_offset", 0x05C0),
            ("opcode", 0x48),
            ("operand_offset", 0x05C3),
            ("old_address", 0x7E2831),
            ("new_address", 0x7E2CA1),
            ("changed_offsets", [0x05C2, 0x05C4]),
        ):
            trace = make_trace("frog-robo", "zero")
            trace["packet"]["edits"][0][field] = replacement
            with self.subTest(field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_callback_binding_or_old_block_access(self) -> None:
        mutations = (
            ("address", 0x7E2834),
            ("pc24", 0xC06821),
            ("cpu_y", 0x06B5),
            ("command_offset", 0x06B5),
            ("opcode_offset", 0x06B4),
            ("opcode", 0x48),
            ("operand_offset", 0x06C3),
            ("operand_address", 0x7E2834),
            ("direct_page", 0),
            ("memory_flag_set", False),
            ("deferred_value", 2),
        )
        for field, replacement in mutations:
            trace = make_trace("frog-robo", "zero")
            trace["callbacks"][0][field] = replacement
            with self.subTest(field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

        trace = make_trace("frog-robo", "zero")
        trace["callbacks"][0]["accumulator"] = 2
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "accumulator",
        ):
            TOOL.validate_trace_document(trace)

    def test_rejects_source_copy_or_candidate_diff_drift(self) -> None:
        trace = make_trace("frog-robo", "zero")
        trace["source_compatibility_hex"] = "00" * 80
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "does not match checkpoint",
        ):
            TOOL.validate_trace_document(trace)

        for phase, index in (("pre", 20), ("post", 20), ("post", 4)):
            trace = make_trace("frog-robo", "zero")
            candidate = bytearray.fromhex(trace[phase]["candidate_hex"])
            candidate[index] ^= 0x01
            trace[phase]["candidate_hex"] = candidate.hex()
            with self.subTest(phase=phase, index=index):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_old_block_guard_or_epoch_drift(self) -> None:
        mutations = (
            ("pre", "old_block_hex", "00" * 79 + "01"),
            ("post", "old_block_hex", "00" * 79 + "01"),
            ("post", "front_guard_hex", "01000000"),
            ("post", "rear_guard_hex", "00" * 15 + "01"),
            ("post", "epoch_name_hex", "000000000000"),
        )
        for phase, field, replacement in mutations:
            trace = make_trace("frog-robo", "zero")
            trace[phase][field] = replacement
            with self.subTest(phase=phase, field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_pair_callback_or_candidate_difference(self) -> None:
        traces = make_trace_set()
        canary = next(
            trace
            for trace in traces
            if trace["profile"] == "frog-robo"
            and trace["variant"] == "canary"
        )
        canary["callbacks"][0]["accumulator"] ^= 1
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_documents(traces)

        traces = make_trace_set()
        canary = next(
            trace
            for trace in traces
            if trace["profile"] == "frog-robo"
            and trace["variant"] == "canary"
        )
        candidate = bytearray.fromhex(canary["post"]["candidate_hex"])
        candidate[20] ^= 1
        canary["post"]["candidate_hex"] = candidate.hex()
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_documents(traces)

    def test_rejects_semantic_or_termination_drift(self) -> None:
        mutations = (
            ("pre", "active_party_hex", "000102"),
            ("post", "storyline", 0x4C),
            ("post", "candidate_tech_counts_hex", "08080808000808"),
            ("termination", "success", False),
            ("termination", "overflow", True),
            ("termination", "observer_error", "observer failed"),
            ("termination", "unexpected_accesses", 1),
        )
        for section, field, replacement in mutations:
            trace = make_trace("frog-robo", "zero")
            trace[section][field] = replacement
            with self.subTest(section=section, field=field):
                with self.assertRaises(TOOL.TraceValidationError):
                    TOOL.validate_trace_document(trace)

    def test_rejects_schema_unknown_fields_and_bool_as_int(self) -> None:
        trace = make_trace("frog-robo", "zero")
        trace["packet"]["untrusted"] = True
        with self.assertRaisesRegex(TOOL.TraceValidationError, "extra"):
            TOOL.validate_trace_document(trace)

        trace = make_trace("frog-robo", "zero")
        trace["collector_version"] = True
        with self.assertRaises(TOOL.TraceValidationError):
            TOOL.validate_trace_document(trace)

    def test_loader_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "trace.json"
            path.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            with self.assertRaisesRegex(
                TOOL.TraceValidationError,
                "duplicate JSON key",
            ):
                TOOL.load_trace(path)

    def test_rejects_duplicate_combination(self) -> None:
        traces = copy.deepcopy(make_trace_set())
        traces[-1] = copy.deepcopy(traces[-2])
        with self.assertRaisesRegex(
            TOOL.TraceValidationError,
            "duplicate trace combination",
        ):
            TOOL.validate_trace_documents(traces)


if __name__ == "__main__":
    unittest.main()
