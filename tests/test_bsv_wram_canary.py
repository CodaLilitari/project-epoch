from __future__ import annotations

import importlib.util
import pathlib
import struct
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "inject_bsv_wram_canary.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("bsv_wram_canary", TOOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def make_inputs(
    *,
    save_slot: int = 1,
    duplicate_pair: bool = False,
    occupied_target: bool = False,
) -> tuple[bytes, bytes, int]:
    sram = bytearray(TOOL.SAVE_SLOT_LENGTH * 3)
    slot_base = (save_slot - 1) * TOOL.SAVE_SLOT_LENGTH
    lucca = bytes(range(TOOL.RECORD_LENGTH))
    magus = bytes(reversed(range(TOOL.RECORD_LENGTH)))
    sram[
        slot_base
        + TOOL.LUCCA_SAVE_OFFSET :
        slot_base
        + TOOL.LUCCA_SAVE_OFFSET
        + TOOL.RECORD_LENGTH
    ] = lucca
    sram[
        slot_base
        + TOOL.MAGUS_SAVE_OFFSET :
        slot_base
        + TOOL.MAGUS_SAVE_OFFSET
        + TOOL.RECORD_LENGTH
    ] = magus

    state = bytearray(0x9000)
    bases = (0x0200, 0x1000) if duplicate_pair else (0x1000,)
    for wram_base in bases:
        state[
            wram_base
            + TOOL.LUCCA_WRAM_OFFSET :
            wram_base
            + TOOL.LUCCA_WRAM_OFFSET
            + TOOL.RECORD_LENGTH
        ] = lucca
        state[
            wram_base
            + TOOL.MAGUS_WRAM_OFFSET :
            wram_base
            + TOOL.MAGUS_WRAM_OFFSET
            + TOOL.RECORD_LENGTH
        ] = magus
    live_base = bases[-1]
    if occupied_target:
        state[live_base + TOOL.TARGET_WRAM_OFFSET] = 1

    header = b"BSV1" + struct.pack("<III", 0, 0, len(state))
    return header + bytes(state) + bytes(48), bytes(sram), live_base


class BsvWramCanaryTests(unittest.TestCase):
    def test_changes_only_candidate_block(self) -> None:
        movie, sram, wram_base = make_inputs()
        patched, found_base, target_offset = TOOL.inject_canary(movie, sram)
        self.assertEqual(found_base, wram_base)
        self.assertEqual(target_offset, wram_base + TOOL.TARGET_WRAM_OFFSET)

        absolute = TOOL.BSV_HEADER_SIZE + target_offset
        self.assertEqual(
            patched[absolute : absolute + TOOL.TARGET_LENGTH],
            TOOL.make_canary(),
        )
        self.assertEqual(movie[:absolute], patched[:absolute])
        self.assertEqual(
            movie[absolute + TOOL.TARGET_LENGTH :],
            patched[absolute + TOOL.TARGET_LENGTH :],
        )

    def test_uses_last_matching_pair_as_live_wram(self) -> None:
        movie, sram, wram_base = make_inputs(duplicate_pair=True)
        _, found_base, _ = TOOL.inject_canary(movie, sram)
        self.assertEqual(found_base, wram_base)

    def test_locates_selected_save_slot_records(self) -> None:
        movie, sram, wram_base = make_inputs(save_slot=3)
        _, found_base, _ = TOOL.inject_canary(movie, sram, save_slot=3)
        self.assertEqual(found_base, wram_base)

    def test_rejects_occupied_candidate(self) -> None:
        movie, sram, _ = make_inputs(occupied_target=True)
        with self.assertRaisesRegex(RuntimeError, "not all zero"):
            TOOL.inject_canary(movie, sram)

    def test_can_accept_exact_existing_canary_for_chained_replay(self) -> None:
        movie, sram, _ = make_inputs()
        patched, _, _ = TOOL.inject_canary(movie, sram)
        unchanged, _, _ = TOOL.inject_canary(
            patched,
            sram,
            allow_existing=True,
        )
        self.assertEqual(unchanged, patched)

    def test_existing_canary_requires_explicit_option(self) -> None:
        movie, sram, _ = make_inputs()
        patched, _, _ = TOOL.inject_canary(movie, sram)
        with self.assertRaisesRegex(RuntimeError, "not all zero"):
            TOOL.inject_canary(patched, sram)

    def test_uses_pinned_layout_for_cold_state_without_live_records(self) -> None:
        movie, sram, _ = make_inputs()
        state = bytearray(TOOL.PINNED_STATE_LENGTH)
        header = b"BSV1" + struct.pack("<III", 0, 0, len(state))
        cold_movie = header + bytes(state)
        patched, found_base, target_offset = TOOL.inject_canary(
            cold_movie,
            sram,
        )
        self.assertEqual(found_base, TOOL.PINNED_WRAM_STATE_OFFSET)
        self.assertEqual(
            target_offset,
            TOOL.PINNED_WRAM_STATE_OFFSET + TOOL.TARGET_WRAM_OFFSET,
        )
        self.assertNotEqual(patched, cold_movie)

    def test_rejects_invalid_slot(self) -> None:
        movie, sram, _ = make_inputs()
        with self.assertRaisesRegex(RuntimeError, "slot"):
            TOOL.inject_canary(movie, sram, save_slot=0)

    def test_rejects_non_bsv(self) -> None:
        _, sram, _ = make_inputs()
        with self.assertRaisesRegex(RuntimeError, "BSV1"):
            TOOL.inject_canary(b"not a movie", sram)

    def test_replaces_only_equal_sized_embedded_state(self) -> None:
        movie, _, _ = make_inputs()
        start, end = TOOL.locate_embedded_state(movie)
        replacement = bytes([0xA5]) * (end - start)
        replaced = TOOL.replace_embedded_state(movie, replacement)
        self.assertEqual(replaced[start:end], replacement)
        self.assertEqual(replaced[:start], movie[:start])
        self.assertEqual(replaced[end:], movie[end:])

    def test_rejects_wrong_sized_replacement_state(self) -> None:
        movie, _, _ = make_inputs()
        with self.assertRaisesRegex(RuntimeError, "size"):
            TOOL.replace_embedded_state(movie, bytes(3))


if __name__ == "__main__":
    unittest.main()
