"""Synthetic artifact-contract checks; no ROM, SRAM input, or emulator needed."""
import argparse
from pathlib import Path
import tempfile
import unittest

from tools.run_mesen_load_entry_checkpoint_v1 import parse_cpu, sha256_argument, validate_capture


CPU = {"k": 255, "pc": 0xFAA3, "sp": 0x0A78, "ps": 0x31,
       "d": 0, "dbr": 0x7E, "a": 0, "x": 0, "y": 1}


def row(kind, pc, *, bank=255, **fields):
    values = {"cpu." + key: str(value) for key, value in CPU.items()}
    values.update({"cpu.k": str(bank), "cpu.pc": str(pc), "slot": "0"})
    values.update({key.replace("_", ".", 1) if key.startswith("cpu_") else key: str(value)
                   for key, value in fields.items()})
    return "\t".join([kind, "2450", *(key + "=" + value for key, value in values.items())])


class LoadEntryArtifactContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        sram = bytearray(8192)
        sram[0x1FF0:0x1FF2] = b"\x34\x12"
        sram[0x1FF8:0x1FFA] = b"\x1b\xe4"
        self.sram = bytes(sram)
        wram = bytearray(0x20000)
        wram[0xA79:0xA7C] = b"\x5a\xe6\xc2"
        (self.directory / "entry_wram.bin").write_bytes(wram)
        (self.directory / "entry_sram.bin").write_bytes(self.sram)
        (self.directory / "load_entry.mss").write_bytes(b"synthetic state identity, not a Mesen state")
        cpu = "\n".join(key + "=" + str(value) for key, value in CPU.items()) + "\nemulationMode=false\n"
        (self.directory / "entry_cpu.txt").write_text(cpu, encoding="ascii")
        self.validation = [
            row("validation-entry", 0xF9C4, return_frame="70d1c2"),
            row("validation-compare", 0xF9E3, cpu_a=0x1234, cpu_dbr=0x30,
                cpu_ps=1, stored_checksum=0x1234, magic=0xE41B),
            row("validation-return", 0xF9FA, result=0, return_frame="70d1c2"),
        ]
        self.tail = [row("load-entry", 0xFAA3, return_frame="5ae6c2"), row("success", 0xFAA3)]
        self.write_trace(self.validation + [row("load-caller", 0xE657, bank=194)] + self.tail)

    def write_trace(self, rows):
        (self.directory / "checkpoint.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    def validate(self, replay=False):
        return validate_capture(self.directory, self.sram, replay=replay)

    def test_valid_cold_boot_is_narrow_native_entry_contract(self):
        result = self.validate()
        self.assertEqual((result["mode"], result["checkpoint_pc"], result["entry_pc"],
                          result["caller_stored_return"]), ("load", "C2E657", "FFFAA3", "C2E65A"))
        self.assertTrue(result["cold_boot"])
        self.assertEqual(len(result["native_validation_sequences"]), 1)

    def test_replay_requires_restore_and_claims_no_new_validation(self):
        self.write_trace([row("checkpoint-restored", 0xE657, bank=194)] + self.tail)
        result = self.validate(replay=True)
        self.assertFalse(result["cold_boot"])
        self.assertFalse(result["validation_observed_this_process"])
        self.assertEqual(result["native_validation_sequences"], [])
        with self.assertRaises(ValueError):
            self.validate(replay=False)

    def test_cold_boot_cannot_masquerade_as_replay(self):
        with self.assertRaises(ValueError):
            self.validate(replay=True)

    def test_replay_must_restore_the_declared_caller(self):
        self.write_trace([row("checkpoint-restored", 0xFAA3)] + self.tail)
        with self.assertRaises(ValueError):
            self.validate(replay=True)

    def test_native_validation_must_be_complete_ordered_and_before_caller(self):
        caller = row("load-caller", 0xE657, bank=194)
        for prefix in ([], self.validation[:2], list(reversed(self.validation)),
                       [caller] + self.validation, self.validation + [self.validation[0]]):
            with self.subTest(prefix=prefix):
                self.write_trace(prefix + [caller] + self.tail)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_boot_dp0400_validation_is_logged_but_cannot_qualify(self):
        # Absolute $0079 is deliberately zero, while actual DP $79 is slot 2.
        boot = row("outside-scope-validation", 0xF9C4, cpu_d=0x400,
                   absolute_0079=0, dp79_address=0x479, dp79_value=2,
                   scope="outside-D0", emulationMode="false", return_frame="718dc2")
        boot = boot.replace("\tslot=0", "")
        caller = row("load-caller", 0xE657, bank=194)
        self.write_trace([boot] + self.validation + [caller] + self.tail)
        self.assertEqual(len(self.validate()["native_validation_sequences"]), 1)
        self.write_trace([boot, caller] + self.tail)
        with self.assertRaises(ValueError):
            self.validate()
        for malformed in (boot.replace("cpu.d=1024", "cpu.d=0"), boot + "\tslot=0"):
            with self.subTest(malformed=malformed):
                self.write_trace([malformed] + self.validation + [caller] + self.tail)
                with self.assertRaises(ValueError):
                    self.validate()
        for prefix in (self.validation[:1] + [boot] + self.validation[1:], self.validation + [boot]):
            with self.subTest(prefix=prefix):
                self.write_trace(prefix + [caller] + self.tail)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_checksum_snapshot_result_and_restored_frame_each_matter(self):
        for old, new in (("stored_checksum=4660", "stored_checksum=4661"),
                         ("cpu.a=4660", "cpu.a=0"), ("result=0", "result=32896"),
                         ("cpu.dbr=48", "cpu.dbr=126"), ("magic=58395", "magic=0")):
            with self.subTest(old=old):
                altered = [line.replace(old, new) for line in self.validation]
                self.write_trace(altered + [row("load-caller", 0xE657, bank=194)] + self.tail)
                with self.assertRaises(ValueError):
                    self.validate()
        altered = self.validation[:2] + [self.validation[2].replace("return_frame=70d1c2", "return_frame=000000")]
        self.write_trace(altered + [row("load-caller", 0xE657, bank=194)] + self.tail)
        with self.assertRaises(ValueError):
            self.validate()

    def test_exact_sram_and_physical_caller_frame_are_required(self):
        path = self.directory / "entry_sram.bin"
        damaged = bytearray(self.sram)
        damaged[4096] ^= 1
        path.write_bytes(damaged)
        with self.assertRaises(ValueError):
            self.validate()
        path.write_bytes(self.sram)
        path = self.directory / "entry_wram.bin"
        damaged = bytearray(path.read_bytes())
        damaged[0xA79] = 0x54  # The save caller is not the load caller.
        path.write_bytes(damaged)
        with self.assertRaises(ValueError):
            self.validate()

    def test_cpu_text_cannot_disagree_with_entry_trace(self):
        path = self.directory / "entry_cpu.txt"
        path.write_text(path.read_text().replace("a=0\n", "a=256\n"), encoding="ascii")
        with self.assertRaises(ValueError):
            self.validate()

    def test_duplicate_entry_or_late_failure_is_rejected(self):
        prefix = self.validation + [row("load-caller", 0xE657, bank=194)]
        for suffix in (self.tail[:1] + self.tail, self.tail + [row("failure:late", 0xFAA3)],
                       [row("failure:early", 0xFAA3)] + self.tail):
            with self.subTest(suffix=suffix):
                self.write_trace(prefix + suffix)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_native_tuple_rejects_unproved_stack_alias_and_mode(self):
        raw = (self.directory / "entry_cpu.txt").read_bytes()
        for altered in (raw.replace(b"emulationMode=false", b"emulationMode=true"),
                        raw.replace(b"sp=2680", b"sp=65534"), raw.replace(b"ps=49", b"ps=33"),
                        raw.replace(b"d=0", b"d=256"), raw.replace(b"k=255", b"k=511")):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                parse_cpu(altered)

    def test_explicit_hash_argument_is_exact(self):
        self.assertEqual(sha256_argument("A" * 64), "a" * 64)
        for bad in ("", "a" * 63, "g" * 64, "a" * 64 + " "):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                sha256_argument(bad)


if __name__ == "__main__":
    unittest.main()
