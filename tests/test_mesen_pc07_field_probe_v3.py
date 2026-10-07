"""Bounded host-helper evidence tests; no ROM, assembly, emulator or file writes.

Only the two binary-input readers are mocked. This hand-authored three-window
fixture records the known stack operations and paths, not a general CPU model.
The canonical descriptor is an arbitrary five-byte stub in a synthetic buffer.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_mesen_pc07_field_probe_v3 as runner
import validate_pc07_native_field_v3_stack_bus_v1 as validator


COMPONENT = bytes.fromhex(
    "0848c907d022bf01117ec907d01abf00117ec902d012af82297ec907d00aec9b01d005"
    "68a9008001688d024228c8a9056b08e00700d00628af46f8cc6b28bf46f8cc6b"
    "08e00700d00628af8325cc6b28bf8325cc6b08e00700d00628af3cf6cc6b28bf3cf6cc6b"
    "08e00700d00628af0040cd6b28bf0040cd6b08e00700d00628af0740cd6b28bf0740cd6b"
    "08e00700d00628af0e40cd6b28bf0e40cd6b")
DESCRIPTOR = bytes.fromhex("a1b2c3d4e5")
PRG_MEMORY_TYPE = 17  # Opaque synthetic enum; each mapping must agree with it.


def _mapping(kind):
    return {"kind": kind, "prg_size": 0x800000, "prg_memory_type": PRG_MEMORY_TYPE,
            "entries": {f"{bus:06X}": {"address": bus, "physical": physical,
                                        "memType": PRG_MEMORY_TYPE, "bytes_hex": data.hex()}
                        for bus, physical, data in (
                            (0xC0448D, 0x448D, bytes.fromhex("22000041eaea")),
                            (0x410000, 0x410000, COMPONENT),
                            (0xC2E657, 0x2E657, bytes.fromhex("22a3faff")),
                            (0xE4F000, 0x24F000, DESCRIPTOR))}}


def _fixture():
    rows = []

    def emit(row):
        row["n"] = len(rows) + 1
        row["poll"] = 0
        rows.append(row)

    emit(_mapping("postload-mapping"))
    # The exact native contexts are fixed by the runner's selected observation.
    cases = (("original00", 0x0000, 2, 0x2E2, 0x27, 0x42B7),
             ("original01", 0x0001, 4, 0x381, 0x24, 0x432B),
             ("candidate07", 0x0107, 16, 0x734, 0x24, 0x43DE))
    for window, (which, accumulator, x, y, ps, caller) in enumerate(cases, 1):
        before = {"a": accumulator, "x": x, "y": y, "d": 0x100, "dbr": 0,
                  "sp": 0x6F7, "ps": ps, "k": 0xC0, "pc": 0x448D,
                  "emulationMode": False, "clock": window * 10000}
        cpu = dict(before)
        sp, base, coverage_low = 0x6F7, 0x6F3, 0x6B7
        ledger = bytearray((0x31 + 17 * i + window) & 255 for i in range(81))
        ledger[65:67] = caller.to_bytes(2, "little")
        original = bytes(ledger[60:])
        exec_index, last_pc = window * 100, 0xC0448D
        emit(_mapping("helper-mapping"))
        emit({"kind": "helper-window-start", "window": window, "which": which,
              "cpu": dict(before), "exec_index": exec_index, "stack_base": base,
              "stack_hex": original.hex(), "stack_coverage_low": coverage_low,
              "stack_coverage_high": sp + 16, "stack_coverage_hex": ledger.hex()})

        def access(kind, address, value):
            emit({"kind": "helper-stack-" + kind, "window": window, "which": which,
                  "address": address, "physical": address, "value": value,
                  "preceding_exec_pc": last_pc, "exec_index": exec_index,
                  "cpu": dict(cpu), "stack_base": base, "stack_hex": ledger[60:].hex(),
                  "snapshot_phase": "prewrite" if kind == "write" else "read-callback"})
            if kind == "write":
                ledger[address - coverage_low] = value

        # JSL publishes bank, return high, return low before the first helper PC.
        for value in (0xC0, 0x44, 0x90):
            access("write", cpu["sp"], value)
            cpu["sp"] -= 1
        path = ([0, 1, 2, 4, 40, 41, 44, 45, 46, 48] if window < 3 else
                [0, 1, 2, 4, 6, 10, 12, 14, 18, 20, 22, 26, 28, 30,
                 33, 35, 36, 38, 41, 44, 45, 46, 48])

        def nz(value, width=8):
            cpu["ps"] = ((cpu["ps"] & 0x7D) | (2 if value == 0 else 0)
                         | (0x80 if value & (1 << (width - 1)) else 0))

        # Only the known path's effects needed to write accurate snapshots are
        # listed. No opcode decoding, arbitrary addressing, or CPU execution.
        for offset in path:
            last_pc = 0x410000 + offset
            exec_index += 1
            cpu.update(k=0x41, pc=offset, clock=cpu["clock"] + 12)
            emit({"kind": "helper-exec", "window": window, "which": which,
                  "address": last_pc, "exec_index": exec_index, "cpu": dict(cpu),
                  "stack_base": base, "stack_hex": ledger[60:].hex()})
            if offset in (0, 1):
                access("write", cpu["sp"], ps if offset == 0 else accumulator & 255)
                cpu["sp"] -= 1
            elif offset in (2, 10, 18, 26, 30):
                # CMP/CPX: selected candidate equal; original A00/01 < 07.
                equal = window == 3
                cpu["ps"] = (cpu["ps"] & 0x7C) | (3 if equal else 0x80)
            elif offset in (6, 14, 22, 36):
                low = {6: 7, 14: 2, 22: 7, 36: 0}[offset]
                cpu["a"] = (cpu["a"] & 0xFF00) | low
                nz(low)
            elif offset in (35, 40):  # Actual PLA operand read, not a snapshot.
                cpu["sp"] += 1
                access("read", cpu["sp"], accumulator & 255)
                cpu["a"] = accumulator
                nz(accumulator & 255)
            elif offset == 41:
                emit({"kind": "helper-hardware-write", "window": window, "which": which,
                      "address": 0x4202, "value": cpu["a"] & 255,
                      "preceding_exec_pc": last_pc, "exec_index": exec_index,
                      "cpu": dict(cpu)})
            elif offset == 44:  # PLP restores carry, including the candidate's C0.
                cpu["sp"] += 1
                access("read", cpu["sp"], ps)
                cpu["ps"] = ps
            elif offset == 45:
                cpu["y"] += 1
                nz(cpu["y"], 16)
            elif offset == 46:
                cpu["a"] = (cpu["a"] & 0xFF00) | 5
                nz(5)
            elif offset == 48:
                for value in (0x90, 0x44, 0xC0):
                    cpu["sp"] += 1
                    access("read", cpu["sp"], value)
        for address in (0xC04491, 0xC04492):
            exec_index += 1
            cpu.update(k=0xC0, pc=address & 0xFFFF, clock=cpu["clock"] + 12)
            emit({"kind": "helper-exec", "window": window, "which": which,
                  "address": address, "exec_index": exec_index, "cpu": dict(cpu),
                  "stack_base": base, "stack_hex": ledger[60:].hex()})
        cpu.update(pc=0x4493, clock=cpu["clock"] + 12)
        emit({"kind": "helper-window-end", "window": window, "which": which,
              "before": dict(before), "after": dict(cpu), "stack_base": base,
              "stack_before_hex": original.hex(), "stack_hex": ledger[60:].hex(),
              "min_sp": sp - 5, "write_count": 5, "selector_count": 1,
              "interrupt_observed": False, "exec_index": exec_index + 1})
    return rows


def _find(rows, kind, window=3, **fields):
    return next(row for row in rows if row["kind"] == kind and row.get("window") == window
                and all(row.get(key) == value for key, value in fields.items()))


class NativeHelperEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rows = _fixture()
        stub = bytearray(0x400000)
        stub[0x24F000:0x24F005] = DESCRIPTOR
        self.canonical_stub = bytes(stub)
        self.component_reader = self.enterContext(patch.object(runner.native_builder, "component", return_value=COMPONENT))
        self.rom_reader = self.enterContext(patch.object(runner.runtime, "read_regular", side_effect=self.read_stub))

    def read_stub(self, path, **kwargs):
        self.assertEqual(path, runner.baseline.ROM)
        self.assertEqual(kwargs, {"size": 0x400000, "digest": runner.baseline.ROM_SHA})
        return self.canonical_stub

    def reject(self, rows, message):
        with self.assertRaisesRegex(ValueError, message):
            validator.validate_native_helper(rows)

    def test_explicit_three_windows_reconcile_native_stack_and_abi(self):
        self.assertEqual(len(COMPONENT), 157)
        self.assertEqual(runner.sha(COMPONENT), runner.native_builder.COMPONENT_SHA)
        result = validator.validate_native_helper(self.rows)
        self.assertEqual([row["which"] for row in result["windows"]],
                         ["original00", "original01", "candidate07"])
        self.assertEqual([row["instructions"] for row in result["windows"]], [12, 12, 25])
        for window in result["windows"]:
            self.assertEqual((window["stack_writes"], window["stack_reads"]), (5, 5))
            self.assertEqual((window["entry_sp"], window["minimum_observed_sp"]), (0x6F7, 0x6F2))
            self.assertEqual(window["live_caller_bytes_preserved"], 16)
        self.assertTrue(result["actual_rom_helper"])
        self.assertFalse(result["interrupt_safety_proved"])
        self.assertFalse(result["global_stack_ownership_proved"])
        self.assertEqual(result["stack_bus_contract"]["checked_stack_events"], 30)
        self.assertTrue(result["stack_bus_contract"]["physical_equals_bus"])
        self.assertFalse(result["stack_bus_contract"]["other_mirrors_admitted"])
        self.assertEqual(_find(self.rows, "helper-window-end")["after"]["a"], 0x0105)
        self.component_reader.assert_called_once_with()
        self.assertEqual(self.rom_reader.call_count, 1)

    def test_hidden_b_and_carry_corruption_refuse(self):
        for window, field, value in ((3, "a", 5), (1, "ps", 0x24), (3, "ps", 0x25)):
            rows = copy.deepcopy(self.rows)
            _find(rows, "helper-window-end", window)["after"][field] = value
            with self.subTest(window=window, field=field):
                self.reject(rows, "replacement result/context")

    def test_missing_y_increment_and_wrong_return_refuse(self):
        for field, value in (("y", 0x734), ("pc", 0x4491), ("sp", 0x6F4)):
            rows = copy.deepcopy(self.rows)
            _find(rows, "helper-window-end")["after"][field] = value
            with self.subTest(field=field):
                self.reject(rows, "replacement result/context")

    def test_every_real_pop_read_is_required_even_with_correct_snapshots(self):
        reads = [row for row in self.rows if row["kind"] == "helper-stack-read" and row["window"] == 3]
        for omitted in reads:
            rows = [copy.deepcopy(row) for row in self.rows if row["n"] != omitted["n"]]
            with self.subTest(address=omitted["address"], owner=omitted["preceding_exec_pc"]):
                self.reject(rows, "missing actual stack pop read")

    def test_forged_stack_publication_and_owner_refuse(self):
        for field, value in (("value", 0), ("preceding_exec_pc", 0x410001),
                             ("exec_index", 9999), ("snapshot_phase", "postwrite")):
            rows = copy.deepcopy(self.rows)
            write = _find(rows, "helper-stack-write", address=0x6F7)
            write[field] = value
            with self.subTest(field=field):
                self.reject(rows, "stack|write ledger")

    def test_stack_read_must_match_last_actual_writer(self):
        rows = copy.deepcopy(self.rows)
        _find(rows, "helper-stack-read", address=0x6F3)["value"] = 0
        self.reject(rows, "native stack read value")
        rows = copy.deepcopy(self.rows)
        write = _find(rows, "helper-stack-write", address=0x6F3)
        # Forge both the write and every later sampled cell/read consistently.
        # The exact native PHA publication must still reject this substitute.
        write["value"] = 0
        for row in rows:
            if row.get("window") == 3 and row["n"] > write["n"]:
                if "stack_hex" in row:
                    data = bytearray.fromhex(row["stack_hex"])
                    data[0] = 0
                    row["stack_hex"] = data.hex()
                if row["kind"] == "helper-stack-read" and row["address"] == 0x6F3:
                    row["value"] = 0
        self.reject(rows, "native JSL/PHP/PHA write ledger")

    def test_stack_preimage_and_live_caller_preservation_refuse(self):
        rows = copy.deepcopy(self.rows)
        start = _find(rows, "helper-window-start")
        start["stack_coverage_hex"] = start["stack_coverage_hex"][:-2]
        self.reject(rows, "watched stack preimage")
        rows = copy.deepcopy(self.rows)
        end = _find(rows, "helper-window-end")
        data = bytearray.fromhex(end["stack_hex"])
        data[5] ^= 1
        end["stack_hex"] = data.hex()
        self.reject(rows, "final stack")

    def test_native_rom_mapping_and_content_cannot_be_substituted(self):
        for key, field, value in (("410000", "physical", 0x010000),
                                  ("C0448D", "physical", 0x40448D),
                                  ("E4F000", "memType", PRG_MEMORY_TYPE + 1),
                                  ("C2E657", "address", 0xC2E658),
                                  ("C0448D", "bytes_hex", "8d0242c8a905"),
                                  ("E4F000", "bytes_hex", "0000000000")):
            rows = copy.deepcopy(self.rows)
            rows[0]["entries"][key][field] = value
            with self.subTest(key=key, field=field):
                self.reject(rows, "mapping/content")

    def test_missing_mapping_invocation_or_instruction_refuse(self):
        for kind in ("helper-mapping", "helper-window-start", "helper-exec"):
            rows = copy.deepcopy(self.rows)
            index = next(i for i, row in enumerate(rows) if row["kind"] == kind)
            rows.pop(index)
            with self.subTest(kind=kind):
                self.reject(rows, "mapping|windows|instruction sequence")

    def test_cpu_edit_and_unexpected_interrupt_refuse(self):
        for kind in ("cpu-edit", "helper-interrupt"):
            rows = copy.deepcopy(self.rows)
            rows.insert(2, {"kind": kind, "n": 2, "window": 1,
                            "cause": "unexpected-execution", "address": 0xC00020})
            with self.subTest(kind=kind):
                self.reject(rows, "CPU edit or interrupt")
        rows = copy.deepcopy(self.rows)
        _find(rows, "helper-window-end")["interrupt_observed"] = True
        self.reject(rows, "final stack or interrupt")

    def test_wrong_selector_and_last_writer_refuse(self):
        rows = copy.deepcopy(self.rows)
        _find(rows, "helper-hardware-write")["value"] = 7
        self.reject(rows, "multiply selector publication")
        rows = copy.deepcopy(self.rows)
        _find(rows, "helper-hardware-write")["preceding_exec_pc"] = 0xC0448D
        self.reject(rows, "hardware write ownership")

    def test_old_mask_only_check_accepts_false_rom_alias_but_wrapper_refuses(self):
        rows = copy.deepcopy(self.rows)
        _find(rows, "helper-stack-write", address=0x6F7)["address"] = 0x4006F7
        # Preserve the historical acceptance gap without altering the frozen
        # runtime bundle or silently calling its predicate fixed.
        self.assertTrue(runner.validate_native_helper(rows)["actual_rom_helper"])
        self.reject(rows, "stack|physical|alias")

    def test_selected_stack_contract_refuses_other_mirrors_types_and_mismatches(self):
        for field, value in (("address", 0x7E06F7), ("address", 0x8006F7),
                             ("address", 0x0026F7), ("address", True),
                             ("physical", 0x6F6), ("physical", float(0x6F7))):
            rows = copy.deepcopy(self.rows)
            _find(rows, "helper-stack-write", address=0x6F7)[field] = value
            with self.subTest(field=field, value=value):
                self.reject(rows, "native stack bus")


if __name__ == "__main__":
    unittest.main()
