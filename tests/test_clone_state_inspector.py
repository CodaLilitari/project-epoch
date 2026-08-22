from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "inspect_clone_state_records.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("state_inspector", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def make_inputs(cloned: bool) -> tuple[bytes, bytes, bytes]:
    save = bytearray(0x500)
    lucca = bytes(range(TOOL.RECORD_LENGTH))
    magus = bytes(reversed(range(TOOL.RECORD_LENGTH)))
    save[
        TOOL.LUCCA_SAVE_OFFSET : TOOL.LUCCA_SAVE_OFFSET + TOOL.RECORD_LENGTH
    ] = lucca
    save[
        TOOL.MAGUS_SAVE_OFFSET : TOOL.MAGUS_SAVE_OFFSET + TOOL.RECORD_LENGTH
    ] = magus

    static_state = bytearray([0xEE] * 1200)
    for destination in (100, 600):
        static_state[destination : destination + TOOL.RECORD_LENGTH] = lucca
        source = destination + TOOL.WRAM_RECORD_DELTA
        static_state[source : source + TOOL.RECORD_LENGTH] = magus

    runtime_state = bytearray(static_state)
    if cloned:
        runtime_state[600 : 600 + TOOL.RECORD_LENGTH] = magus
    return bytes(save), bytes(static_state), bytes(runtime_state)


class CloneStateInspectorTests(unittest.TestCase):
    def test_detects_cloned_live_record(self) -> None:
        result = TOOL.inspect_states(*make_inputs(cloned=True))
        self.assertEqual(result["live_lucca_state_offset"], 600)
        self.assertEqual(result["live_magus_state_offset"], 920)
        self.assertEqual(result["runtime_lucca_record_status"], "cloned")

    def test_detects_unchanged_live_record(self) -> None:
        result = TOOL.inspect_states(*make_inputs(cloned=False))
        self.assertEqual(result["runtime_lucca_record_status"], "unchanged")

    def test_rejects_identical_source_records(self) -> None:
        save, static_state, runtime_state = make_inputs(cloned=False)
        changed = bytearray(save)
        changed[
            TOOL.MAGUS_SAVE_OFFSET : TOOL.MAGUS_SAVE_OFFSET + TOOL.RECORD_LENGTH
        ] = changed[
            TOOL.LUCCA_SAVE_OFFSET : TOOL.LUCCA_SAVE_OFFSET
            + TOOL.RECORD_LENGTH
        ]
        with self.assertRaisesRegex(RuntimeError, "inconclusive"):
            TOOL.inspect_states(bytes(changed), static_state, runtime_state)

    def test_locates_records_from_second_save_slot(self) -> None:
        save = bytearray(TOOL.SAVE_SLOT_LENGTH * 3)
        slot_base = TOOL.SAVE_SLOT_LENGTH
        lucca = bytes(range(TOOL.RECORD_LENGTH))
        magus = bytes(reversed(range(TOOL.RECORD_LENGTH)))
        save[
            slot_base
            + TOOL.LUCCA_SAVE_OFFSET : slot_base
            + TOOL.LUCCA_SAVE_OFFSET
            + TOOL.RECORD_LENGTH
        ] = lucca
        save[
            slot_base
            + TOOL.MAGUS_SAVE_OFFSET : slot_base
            + TOOL.MAGUS_SAVE_OFFSET
            + TOOL.RECORD_LENGTH
        ] = magus

        state = bytearray([0xEE] * 0x1000)
        state[0x200 : 0x200 + TOOL.RECORD_LENGTH] = lucca
        magus_state_offset = 0x200 + TOOL.WRAM_RECORD_DELTA
        state[
            magus_state_offset : magus_state_offset + TOOL.RECORD_LENGTH
        ] = magus

        result = TOOL.inspect_states(
            bytes(save),
            bytes(state),
            bytes(state),
            save_slot=2,
        )
        self.assertEqual(result["save_slot"], 2)
        self.assertEqual(result["live_lucca_state_offset"], 0x200)
        self.assertEqual(result["runtime_lucca_record_status"], "unchanged")


if __name__ == "__main__":
    unittest.main()
