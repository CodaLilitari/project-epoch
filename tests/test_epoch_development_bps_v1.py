"""Small format/guard boundaries; no historical builders or emulator runs."""
from pathlib import Path
import copy
import sys
import unittest
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import epoch_bps_v1 as bps
import epoch_development_bps_export_contract_v1 as contract
import export_epoch_development_bps_v1 as exporter
import validate_rom_write_intents as guard


def footer(body, source, target):
    body += zlib.crc32(source).to_bytes(4, 'little') + zlib.crc32(target).to_bytes(4, 'little')
    return body + zlib.crc32(body).to_bytes(4, 'little')


class FormatTests(unittest.TestCase):
    def test_known_integer_encodings(self):
        for value, expected in ((0, '80'), (127, 'ff'), (128, '0080'), (255, '7f80'), (256, '0081')):
            self.assertEqual(bps.number(value), bytes.fromhex(expected))

    def test_hand_encoded_four_action_vector(self):
        # Independent fixed tokens: lengths3,3,1,7; source offset0;
        # target-copy offset6. The last copy overlaps its own output.
        source, target = b'ABCDEF', b'ABCABCXXXXXXXX'
        patch = footer(b'BPS1' + bytes.fromhex('868e80888a8081589b8c'), source, target)
        result, info = bps.apply(source, patch)
        self.assertEqual(result, target)
        self.assertEqual(info['action_output_bytes'], {0: 3, 1: 1, 2: 3, 3: 7})

    def test_negative_source_relative_copy(self):
        source, target = b'ABCDEF', b'DEFABC'
        patch = footer(b'BPS1' + bytes.fromhex('8686808a868a8d'), source, target)
        self.assertEqual(bps.apply(source, patch)[0], target)

    def test_deterministic_mixed_roundtrip(self):
        source = bytes(range(256)) * 4
        target = source[:300] + b'new' + source[303:] + source[120:300] + b'\xff' * 4000
        first, _ = bps.encode(source, target, b'<note>test</note>')
        self.assertEqual(first, bps.encode(source, target, b'<note>test</note>')[0])
        self.assertEqual(bps.apply(source, first)[0], target)

    def test_reject_corrupt_patch_wrong_source_and_target_limit(self):
        source, target = b'ABCDEF', b'ABCABCXXXXXXXX'
        patch = bps.encode(source, target)[0]
        with self.assertRaisesRegex(ValueError, 'patch CRC'):
            bps.apply(source, patch[:-1] + bytes([patch[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'source CRC'):
            bps.apply(b'BBCDEF', patch)
        with self.assertRaisesRegex(ValueError, 'target limit'):
            bps.apply(source, patch, maximum_target_size=3)

    def test_reject_forward_target_copy(self):
        patch = footer(b'BPS1' + bytes.fromhex('8081808380'), b'', b'X')
        with self.assertRaisesRegex(ValueError, 'earlier output'):
            bps.apply(b'', patch)

    def test_reject_trailing_data_with_valid_crc(self):
        patch = footer(b'BPS1' + bytes.fromhex('8181808080'), b'A', b'A')
        with self.assertRaisesRegex(ValueError, 'unused bytes'):
            bps.apply(b'A', patch)

    def test_zip_deterministic_and_exact(self):
        self.assertEqual(exporter.zip_bytes({'a.txt': b'a', 'b.txt': b'b'}),
                         exporter.zip_bytes({'b.txt': b'b', 'a.txt': b'a'}))
        with self.assertRaisesRegex(ValueError, 'unsafe ZIP'):
            exporter.zip_bytes({'../x': b'x'})


class PinnedExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = ('private/input/rom_archive/Chrono Trigger (USA).sfc',
                 'private/test_runs/pc07_menu_stats_portrait_v2/diagnostic.sfc',
                 'private/test_runs/pc07_menu_stats_portrait_v2/receipt.json')
        if not all((contract.ROOT / name).is_file() for name in paths):
            raise unittest.SkipTest('exact private release inputs unavailable')
        cls.raw = [(contract.ROOT / name).read_bytes() for name in paths]

    def test_wrong_source_target_and_receipt_refused_before_export(self):
        for index, label in enumerate(('source', 'target', 'receipt')):
            altered = list(self.raw)
            altered[index] = bytes([altered[index][0] ^ 1]) + altered[index][1:]
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'identity mismatch'):
                with contract.source_snapshot(*altered):
                    self.fail('bad input admitted')

    def test_guard_manifest_and_output_boundaries(self):
        output = 'private/research/epoch_update_20261020/release/test_boundary/' + contract.NAME
        with contract.source_snapshot(*self.raw):
            manifest = contract.template(output)
            self.assertEqual(guard.validate_epoch_development_bps_export_v1_manifest(manifest)['status'],
                             'metadata-valid')
            bad = copy.deepcopy(manifest); bad['target']['sha256'] = '0' * 64
            # deepcopy is essential: fixed schema constants must stay untouched.
            with self.assertRaisesRegex(ValueError, 'fixed development export'):
                guard.validate_epoch_development_bps_export_v1_manifest(bad)
            with self.assertRaisesRegex(ValueError, 'destination'):
                contract.template('public/diagnostic.sfc')
        self.assertFalse(guard.APPROVED_PRODUCTION_ALLOCATIONS)
        self.assertFalse(guard.APPROVED_PRODUCTION_HOOKS)


if __name__ == '__main__':
    unittest.main()
