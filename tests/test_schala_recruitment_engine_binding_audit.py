from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "audit_schala_recruitment_engine_bindings.py"
DOCUMENT_PATH = ROOT / "docs" / "schala_recruitment_engine_binding_audit.md"
SPEC = importlib.util.spec_from_file_location(
    "audit_schala_recruitment_engine_bindings", TOOL_PATH
)
assert SPEC and SPEC.loader
TOOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TOOL
SPEC.loader.exec_module(TOOL)

ROM_PATH = (
    ROOT
    / "private"
    / "input"
    / "rom_archive"
    / "Chrono Trigger (USA).sfc"
)


def make_metadata_rom() -> bytearray:
    rom = bytearray(TOOL.CANONICAL_ROM_SIZE)
    for opcode, target in TOOL.EXPECTED_EVENT_TARGETS.items():
        offset = TOOL.EVENT_COMMAND_TABLE_FILE + opcode * 2
        rom[offset : offset + 2] = target.to_bytes(2, "little")
    for operation, target in enumerate(TOOL.EXPECTED_PARTY_TARGETS):
        offset = TOOL.PARTY_OPERATION_TABLE_FILE + operation * 2
        rom[offset : offset + 2] = target.to_bytes(2, "little")
    start = TOOL.CHAR_PARTY_FLAG_TABLE_FILE
    rom[start : start + len(TOOL.EXPECTED_CHAR_PARTY_FLAGS)] = (
        TOOL.EXPECTED_CHAR_PARTY_FLAGS
    )
    for pc_id, address in enumerate(TOOL.EXPECTED_PC_NAME_ADDRS):
        offset = TOOL.PC_NAME_ADDR_TABLE_FILE + pc_id * 2
        rom[offset : offset + 2] = address.to_bytes(2, "little")
    return rom


class SchalaRecruitmentEngineBindingAuditTests(unittest.TestCase):
    def test_content_inventory_stays_null_and_fully_classified(self) -> None:
        result = TOOL.validate_content()
        self.assertEqual(result["binding_count"], 29)
        self.assertEqual(result["null_binding_count"], 29)
        self.assertEqual(
            set(TOOL.BINDING_CLASSIFICATIONS),
            set(TOOL.REQUIRED_BINDING_IDS),
        )

    def test_content_validation_rejects_installed_binding(self) -> None:
        content = json.loads(TOOL.CONTENT_PATH.read_text(encoding="utf-8"))
        changed = copy.deepcopy(content)
        changed["runtime_bindings"][0]["mapping_status"] = "verified-static"
        changed["runtime_bindings"][0]["event_opcode"] = 0x81
        encoded = json.dumps(changed).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "changed.json"
            path.write_bytes(encoded)
            with mock.patch.object(TOOL, "CONTENT_SHA256", TOOL._sha256(encoded)):
                with self.assertRaisesRegex(
                    TOOL.AuditError, "authoring mapping is no longer null"
                ):
                    TOOL.validate_content(path)

    def test_pinned_disassembly_hashes_and_anchors(self) -> None:
        result = TOOL.validate_disassembly_sources()
        self.assertEqual(
            result["commit"], TOOL.PINNED_DISASSEMBLY_COMMIT
        )
        self.assertEqual(set(result["files"]), set(TOOL.PINNED_SOURCE_HASHES))

    def test_audit_document_covers_every_binding_in_order(self) -> None:
        text = DOCUMENT_PATH.read_text(encoding="utf-8")
        for index, binding_id in enumerate(TOOL.REQUIRED_BINDING_IDS, 1):
            self.assertIn(f"| {index} | `{binding_id}` |", text)

    def test_metadata_tables_prove_pc7_flag_and_name_collision(self) -> None:
        rom = make_metadata_rom()
        save_slice = bytes(
            rom[
                TOOL.SAVE_REGION_TABLE_FILE:
                TOOL.SAVE_REGION_TABLE_FILE + TOOL.SAVE_REGION_TABLE_LENGTH
            ]
        )
        ng_plus_slice = bytes(
            rom[
                TOOL.NG_PLUS_LOADER_FILE:
                TOOL.NG_PLUS_LOADER_FILE + TOOL.NG_PLUS_LOADER_LENGTH
            ]
        )
        with (
            mock.patch.object(
                TOOL,
                "EXPECTED_SAVE_REGION_TABLE_SHA256",
                TOOL._sha256(save_slice),
            ),
            mock.patch.object(
                TOOL,
                "EXPECTED_NG_PLUS_LOADER_SHA256",
                TOOL._sha256(ng_plus_slice),
            ),
        ):
            result = TOOL.audit_rom_metadata(rom)
        self.assertEqual(result["logical_pc_07_party_flag"], "$01")
        self.assertEqual(
            result["logical_pc_07_dialogue_name_entry"], "$0000"
        )
        self.assertEqual(
            result["vanilla_name_entry_id_07_target"], "$7E:2C4D"
        )

    def test_metadata_audit_rejects_party_dispatch_drift(self) -> None:
        rom = make_metadata_rom()
        rom[TOOL.PARTY_OPERATION_TABLE_FILE] ^= 1
        with self.assertRaisesRegex(TOOL.AuditError, "party operation"):
            TOOL.audit_rom_metadata(rom)

    def test_rom_gate_rejects_unpinned_input(self) -> None:
        with self.assertRaisesRegex(TOOL.AuditError, "SHA-1 mismatch"):
            TOOL.validate_canonical_rom(bytes(TOOL.CANONICAL_ROM_SIZE))

    @unittest.skipUnless(ROM_PATH.exists(), "local canonical ROM unavailable")
    def test_canonical_rom_audit_has_no_installed_bindings(self) -> None:
        result = TOOL.audit(ROM_PATH)
        self.assertEqual(result["installed_binding_count"], 0)
        self.assertEqual(result["content"]["binding_count"], 29)
        self.assertIn("metadata only", result["copyright_boundary"])


if __name__ == "__main__":
    unittest.main()
