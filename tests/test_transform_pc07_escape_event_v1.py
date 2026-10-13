"""Checks the exact packet and its one-byte authored derivative, without writes."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import transform_pc07_escape_event_v1 as t


class EscapeEvent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = t.parent().transform_from_rom(
            (ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc").read_bytes()).packet

    def test_exact_derivative_and_inverse(self):
        out = t.derive(self.source)
        self.assertEqual(t.sha(out.packet), t.TARGET_SHA256)
        self.assertEqual([i for i, (a, b) in enumerate(zip(self.source, out.packet)) if a != b], [0x547])
        restored = bytearray(out.packet)
        restored[0x547] = 0x93
        self.assertEqual(bytes(restored), self.source)

    def test_foreign_size_flags_or_payload_fail_closed(self):
        for candidate in (self.source[:-1], self.source + b"\0", t.derive(self.source).packet,
                          self.source[:100] + bytes([self.source[100] ^ 1]) + self.source[101:],
                          bytearray(self.source)):
            with self.subTest(kind=type(candidate), size=len(candidate)):
                with self.assertRaises(t.TransformError):
                    t.derive(candidate)


if __name__ == "__main__":
    unittest.main()
