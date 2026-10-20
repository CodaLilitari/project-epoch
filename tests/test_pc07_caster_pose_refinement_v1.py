"""Focused sparse ownership, field fence, and current-parent delta checks."""
import copy, shutil, struct, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import native_pc07_caster_pose_codec_v2 as codec
import native_pc07_pose_codec_v1 as base
import pc07_caster_pose_refinement_write_contract_v1 as contract
import validate_rom_write_intents as guard


class SparseCodecTests(unittest.TestCase):
    def setUp(self):
        tile = [0]*64
        tile[0] = 3
        self.graphics = bytes(32) + base.encode_tile(tile) + bytes(120*32)
        blank = struct.pack('<16H8b', *([0]*16), *([0]*8))
        outside = struct.pack('<16H8b', *([1]+[0]*15), -40, -40, 0, 0, 0, 0, 0, 0)
        self.assembly = blank*31 + outside
        self.rows = [[0]*48 for _ in range(48)]
        self.rows[24][16] = 4

    def test_sparse_id_append_and_old_physical_prefix(self):
        graphics, assembly, report = codec.append_frames(self.graphics, self.assembly, [{'role': 'new', 'rows': self.rows}])
        self.assertEqual(assembly[:len(self.assembly)], self.assembly)
        self.assertEqual(report[0]['frame_id'], 32)
        self.assertEqual(report[0]['appended_tile_ids'], [384])
        self.assertEqual(codec.decode_sparse(self.graphics, graphics, assembly[-40:]), {(0, -16): 4})

    def test_gap_and_end_refuse_even_with_plausible_decode_padding(self):
        for index in (122, 127, 128, 256, 383, 385, 511):
            with self.subTest(index=index):
                record = struct.pack('<16H8b', *([index]+[0]*15), *([0]*8))
                with self.assertRaises(ValueError):
                    codec.decode_sparse(self.graphics, bytes(32), record)

    def test_input_extent_palette_and_shape_refuse(self):
        for graphics, assembly in ((self.graphics[:-32], self.assembly), (self.graphics, self.assembly[:-40])):
            with self.assertRaises(ValueError):
                codec.append_frames(graphics, assembly, [])
        for rows in (self.rows[:-1], [[0]*47 for _ in range(48)]):
            with self.assertRaises(ValueError):
                codec.append_frames(self.graphics, self.assembly, [{'role': 'bad', 'rows': rows}])
        rows = copy.deepcopy(self.rows)
        rows[24][16] = 13
        with self.assertRaises(ValueError):
            codec.append_frames(self.graphics, self.assembly, [{'role': 'bad', 'rows': rows}])


def execute_fence(code, value):
    """Independent bounded interpreter for the actual new gate bytes.

    X is16-bit and A is8-bit as required by the unchanged caller contract.
    Stop at .original (refuse) or the restored-context PLA (accept).
    """
    pc, carry, zero, low_a = 81, False, False, 0
    for _ in range(16):
        if pc == 107:
            return False
        if pc == 101:
            return True
        opcode = code[pc]
        if opcode == 0xE0:
            immediate = int.from_bytes(code[pc+1:pc+3], 'little')
            carry, zero, pc = value >= immediate, value == immediate, pc+3
        elif opcode in (0x90, 0xB0, 0xD0):
            take = (not carry) if opcode == 0x90 else carry if opcode == 0xB0 else not zero
            displacement = int.from_bytes(code[pc+1:pc+2], 'little', signed=True)
            pc += 2 + (displacement if take else 0)
        elif opcode == 0x8A:
            low_a, pc = value & 255, pc+1
        elif opcode == 0x29:
            low_a &= code[pc+1]
            zero, pc = low_a == 0, pc+2
        else:
            raise AssertionError(f'unexpected fence opcode {opcode:02x} at {pc}')
    raise AssertionError('fence did not terminate')


class RefinementContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (contract.ROOT/contract.SOURCE['path']).is_file():
            raise unittest.SkipTest('private current image is not distributed')
        parent = (contract.ROOT/'private/test_runs').resolve()
        cls.temporary = Path(tempfile.mkdtemp(prefix='pc07_caster_pose_refinement_unit_', dir=parent)).resolve()
        if cls.temporary.parent != parent:
            raise ValueError('private test directory required')
        def cleanup():
            target = cls.temporary.resolve()
            if target.parent != parent or not target.name.startswith('pc07_caster_pose_refinement_unit_'):
                raise ValueError('unsafe cleanup target')
            shutil.rmtree(target)
        cls.addClassCleanup(cleanup)
        cls.context = contract.source_snapshot(cls.temporary/'assembly')
        cls.snap = cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__, None, None, None)
        cls.manifest = contract.template('private/test_runs/pc07_caster_pose_refinement_test/diagnostic.sfc')

    def test_exact_guard_and_all1024_stream_entrypoints(self):
        result = guard.audit_pc07_caster_pose_refinement_images(self.manifest, self.snap['source'], self.snap['target'])
        self.assertTrue(result['complete_diff_coverage'])
        self.assertTrue(result['inverse_restores_parent'])
        self.assertTrue(result['all_caster_and_KO_helpers_unchanged'])
        self.assertEqual(result['original_frame_prefix_preserved'], 32)
        self.assertEqual(self.snap['streams']['entrypoints_checked'], 1024)
        self.assertEqual(self.snap['streams']['changed_directional_entries'], 6)

    def test_actual_sparse_fence_all65536_offsets(self):
        code = self.snap['target'][0x413000:0x4130EC]
        accepted = []
        for value in range(65536):
            expected = value % 32 == 0 and (value <= 0x0F20 or 0x3000 <= value <= 0x31A0)
            actual = execute_fence(code, value)
            if actual:
                accepted.append(value)
            self.assertEqual(actual, expected, hex(value))
        self.assertEqual(len(accepted), 136)

    def test_unrelated_and_existing_art_mutations_refuse(self):
        for at in (0x19E2CE, 0x240C00, 0x420000, 0x420F20, 0x421000, 0x4214D8,
                   0x421578, 0x422000, 0x4231C0, 0x4251C4, 0x480400, 0x490000, 0x490100,
                   0x161EF, 0x161F9, 0x500000):
            with self.subTest(at=hex(at)):
                target = bytearray(self.snap['target'])
                target[at] ^= 1
                with self.assertRaises(ValueError):
                    guard.audit_pc07_caster_pose_refinement_images(self.manifest, self.snap['source'], bytes(target))

    def test_manifest_and_parent_forgery_refuse(self):
        for key, value in (('production_approval', True), ('native_execution', True), ('new_tile_ids', [128]),
                           ('original_frame_prefix_preserved', 30), ('sections', self.manifest['sections']+[{'id': 'extra'}])):
            manifest = copy.deepcopy(self.manifest)
            manifest[key] = value
            with self.assertRaises(ValueError):
                guard.validate_pc07_caster_pose_refinement_manifest(manifest)
        source = bytearray(self.snap['source'])
        source[0x480400] ^= 1
        with self.assertRaises(ValueError):
            guard.audit_pc07_caster_pose_refinement_images(self.manifest, bytes(source), self.snap['target'])

    def test_horizontal_movement_KO_and_timing_stay_unchanged(self):
        for at in (contract.PRIMARY + 2*contract.STRIDE + 0x31*4,
                   contract.PRIMARY + 3*contract.STRIDE + 9*4,
                   contract.PRIMARY + 6*4, contract.PRIMARY + 0xF0*4,
                   contract.TIMING + 0x31*4):
            target = bytearray(self.snap['target'])
            target[at] ^= 1
            with self.assertRaises(ValueError):
                contract.stream_audit(self.snap['source'], bytes(target))

    def test_frozen_adapter_and_output_escape_refuse(self):
        old = bytearray(self.snap['source'][0x413000:0x4130E2])
        old[9] ^= 1
        with self.assertRaises(ValueError):
            contract.expected_adapter(bytes(old))
        for path in ('diagnostic.sfc', 'private/test_runs/pc07_caster_pose_refinement_test/../diagnostic.sfc',
                     'private/test_runs/pc07_caster_pose_refinement_test/link/diagnostic.sfc'):
            with self.assertRaises(ValueError):
                contract.output_path(path)


if __name__ == '__main__':
    unittest.main()
