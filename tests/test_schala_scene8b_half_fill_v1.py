"""Original loop specimens, boundary expectations and fail-closed mutations."""
import importlib.util
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import audit_schala_scene8b_half_fill_v1 as a


def specimen(raw, start=0xCD8000):
    memory = bytearray(raw)
    def read(pc, n):
        if not start <= pc < pc+n <= start+len(memory):
            raise ValueError('outside original specimen')
        return bytes(memory[pc-start:pc-start+n])
    return memory, read, start, start+len(memory)


def loop(*, target=4, initial=0, base=0xC161, fill=0xA55A, stride=4):
    # Authored independently from the canonical prefix and its parity branch.
    # Directly initialize X and target; exercise the actual store-before-test loop.
    raw = b'\xA9'+target.to_bytes(2, 'little')+b'\x85\x45'
    raw += b'\xA9'+initial.to_bytes(2, 'little')+b'\xAA'
    raw += b'\xA9'+fill.to_bytes(2, 'little')
    body = b'\x9D'+base.to_bytes(2, 'little')+b'\xE8'*stride+b'\xE4\x45'
    raw += body+b'\xD0'+bytes([(256-len(body)-2)&255])+b'\x7B\xE2\x20\x60'
    return specimen(raw)


def run(spec, **kwargs):
    _, read, start, end = spec
    return a.execute(read, kwargs.pop('q', 0), kwargs.pop('s', 0), kwargs.pop('frame_word', 0),
                     start=start, end=end, **kwargs)


class OriginalLoops(unittest.TestCase):
    def test_positive_one_stores_before_testing(self):
        v = run(loop(target=4))
        self.assertEqual([(p, h, x) for _, p, h, x in v['indexed_writes']], [(0x7EC161, 0x7EC162, 0xA55A)])
        self.assertEqual((v['a'], v['x'], v['m8'], v['x_wraps']), (0, 4, True, 0))

    def test_zero_target_full_period_does_not_skip(self):
        v = run(loop(target=0))
        self.assertEqual(len(v['indexed_writes']), 16384)
        self.assertEqual(v['indexed_writes'][0][1:3], (0x7EC161, 0x7EC162))
        self.assertEqual(v['indexed_writes'][-1][1:3], (0x7FC15D, 0x7FC15E))
        self.assertEqual((v['x'], v['x_wraps']), (0, 1))

    def test_zero_target_odd_slot_wraps_to_two(self):
        v = run(loop(target=2, initial=2, base=0xC4E1))
        self.assertEqual(len(v['indexed_writes']), 16384)
        self.assertEqual(v['indexed_writes'][0][1:3], (0x7EC4E3, 0x7EC4E4))
        self.assertEqual(v['indexed_writes'][-1][1:3], (0x7FC4DF, 0x7FC4E0))
        self.assertEqual((v['x'], v['x_wraps']), (2, 1))

    def test_absolute_x_addition_carries_into_next_bank(self):
        v = run(loop(initial=0x4000, target=0x4004))
        self.assertEqual(v['indexed_writes'][0][1:3], (0x7F0161, 0x7F0162))

    def test_word_high_byte_crosses_bank_boundary(self):
        v = run(loop(initial=0x3E9E, target=0x3EA2))
        self.assertEqual(v['indexed_writes'][0][1:3], (0x7EFFFF, 0x7F0000))

    def test_independent_224_and_225_comparison_boundary(self):
        safe = run(loop(target=896))['indexed_writes']
        unsafe = run(loop(target=900))['indexed_writes']
        self.assertEqual(len(safe), 224)
        self.assertEqual(safe[-1][1:3], (0x7EC4DD, 0x7EC4DE))
        self.assertEqual(unsafe[224][1:3], (0x7EC4E1, 0x7EC4E2))

    def test_226_odd_slot_reaches_known_source_use(self):
        v = run(loop(initial=2, target=906, base=0xC4E1))
        self.assertEqual(len(v['indexed_writes']), 226)
        self.assertEqual(v['indexed_writes'][225][1:3], (0x7EC867, 0x7EC868))

    def test_reachable_target_with_wrap_has_first_positive_solution(self):
        v = run(loop(initial=0xFFFE, target=2, base=0))
        self.assertEqual(len(v['indexed_writes']), 1)
        self.assertEqual(v['indexed_writes'][0][1:3], (0x7EFFFE, 0x7EFFFF))
        self.assertEqual((v['x'], v['x_wraps']), (2, 1))

    def test_target_wrong_modulo_class_never_certifies_termination(self):
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            run(loop(target=1), step_limit=100)

    def test_full_word_cpx_does_not_match_equal_low_byte(self):
        v = run(loop(target=0x0104))
        self.assertEqual(len(v['indexed_writes']), 65)
        self.assertEqual(v['x'], 260)

    def test_word_fill_preserves_both_bytes(self):
        v = run(loop(fill=0x0080))
        self.assertEqual(v['indexed_writes'][0][3], 0x0080)
        v = run(loop(fill=0xFF01))
        self.assertEqual(v['indexed_writes'][0][3], 0xFF01)


class InstructionMeaning(unittest.TestCase):
    def test_source_word_mask_discards_every_unknown_high(self):
        # Different authored program: load q, mask its low bit, transfer X, return.
        program = specimen(bytes.fromhex('AD AA CA 29 01 00 0A AA 60'))
        for q in (0, 1, 128, 129, 254, 255):
            for high in range(256):
                self.assertEqual(run(program, q=q, unknown_high=high)['x'], 2*(q&1))

    def test_mutated_word_mask_exposes_unknown_high(self):
        program = specimen(bytes.fromhex('AD AA CA 29 01 01 0A AA 60'))
        self.assertEqual(run(program, q=1, unknown_high=0)['x'], 2)
        self.assertEqual(run(program, q=1, unknown_high=1)['x'], 514)

    def test_asl_word_retains_high_bits_and_supplies_carry(self):
        # DP47=1; 8001<<1 => 0002,C1; ADC dp47 => 4.
        program = specimen(bytes.fromhex('A9 01 80 0A 65 47 AA 60'))
        self.assertEqual(run(program, s=1)['x'], 4)

    def test_clc_clears_the_prior_asl_carry(self):
        program = specimen(bytes.fromhex('A9 01 80 0A 18 65 47 AA 60'))
        self.assertEqual(run(program, s=1)['x'], 3)

    def test_adc_word_wrap_is_not_host_integer_addition(self):
        program = specimen(bytes.fromhex('A9 FF FF 18 65 47 AA 60'))
        self.assertEqual(run(program, s=1)['x'], 0)

    def test_branch_consumes_actual_zero_from_and(self):
        program = specimen(bytes.fromhex('A5 7C 29 01 00 F0 03 A9 34 12 AA 60'))
        self.assertEqual(run(program, frame_word=0xFFFE)['x'], 0)
        self.assertEqual(run(program, frame_word=0xFFFF)['x'], 0x1234)

    def test_undefined_branch_flag_refuses(self):
        with self.assertRaisesRegex(ValueError, 'undefined branch'):
            run(specimen(bytes.fromhex('F0 00 60')))

    def test_direct_page_write_high_byte_is_recorded(self):
        v = run(specimen(bytes.fromhex('A9 23 81 85 45 A5 45 AA 60')))
        self.assertEqual(v['dp'][0x45], 0x8123)
        self.assertEqual(v['dp_writes'][0][1:], (0x7E0045, 0x8123))

    def test_own_q_write_followed_by_reload_refuses_stale_input_fiction(self):
        p = specimen(bytes.fromhex('A9 00 00 AA A9 55 AA 9D AA CA AD AA CA 60'))
        with self.assertRaisesRegex(ValueError, 'external reload aliases'):
            run(p)


class Refusals(unittest.TestCase):
    def test_preserved_four_q_aliases(self):
        for q in (2, 3, 6, 7):
            with self.subTest(q=q), self.assertRaisesRegex(ValueError, 'aliases'):
                run(loop(), q=q)

    def test_nonbyte_nonword_and_boolean_inputs_refuse(self):
        for kw in ({'q': True}, {'q': 256}, {'s': -1}, {'s': 1.0}, {'unknown_high': 256},
                   {'unknown_high': True}, {'frame_word': 65536}, {'fill': -1}, {'fill': False}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                run(loop(), **kw)

    def test_mode_decimal_and_lifetime_premises_refuse(self):
        for kw in ({'m8': True}, {'m8': 0}, {'x8': True}, {'d': 1}, {'d': False},
                   {'dbr': 0}, {'decimal': True}, {'decimal': 0}, {'stable_target': False}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                run(loop(), **kw)

    def test_alias_to_live_dp_word_high_byte_refuses(self):
        with self.assertRaisesRegex(ValueError, 'aliases local live input'):
            run(loop(base=0x44))

    def test_alias_to_fill_source_high_byte_refuses(self):
        with self.assertRaisesRegex(ValueError, 'aliases local live input'):
            run(loop(base=0xB9FF))

    def test_unknown_opcode_refuses(self):
        with self.assertRaisesRegex(ValueError, 'unmodeled opcode'):
            run(specimen(b'\xEA\x60'))

    def test_unknown_external_read_refuses(self):
        with self.assertRaisesRegex(ValueError, 'external read'):
            run(specimen(bytes.fromhex('AD 00 C0 60')))

    def test_undefined_accumulator_refuses(self):
        with self.assertRaisesRegex(ValueError, 'undefined A'):
            run(specimen(bytes.fromhex('0A 60')))

    def test_early_width_change_cannot_reuse_word_decode(self):
        with self.assertRaisesRegex(ValueError, 'after final SEP20'):
            run(specimen(bytes.fromhex('E2 20 A9 00 00 60')))

    def test_unmodeled_status_change_refuses(self):
        with self.assertRaisesRegex(ValueError, 'only SEP20'):
            run(specimen(bytes.fromhex('E2 10 60')))

    def test_branch_outside_specimen_refuses(self):
        with self.assertRaisesRegex(ValueError, 'outside exact code interval'):
            run(specimen(bytes.fromhex('80 7F 60')))

    def test_truncated_instruction_refuses(self):
        with self.assertRaisesRegex(ValueError, 'instruction crosses'):
            run(specimen(bytes.fromhex('A9 00')))

    def test_inconsistent_instruction_read_refuses(self):
        calls = []
        def read(pc, n):
            calls.append((pc, n))
            return b'\xA9' if n == 1 else b'\x29\x00\x00'
        with self.assertRaisesRegex(ValueError, 'stable instruction'):
            a.execute(read, 0, 0, 0, start=0x1000, end=0x1003)


class ArtifactGuards(unittest.TestCase):
    def test_earlier_open_obligation_and_typed_frame_are_preserved(self):
        control = {'entry_m8': False, 'entry_x8': False,
                   'maximum_additional_bytes_below_callee_entry': 0,
                   'maximum_counted_bytes_including_root_call_frame': 2,
                   'decoded_byte_intervals': [{'start': '$CD34F1', 'end_exclusive': '$CD352D',
                                              'sha256': a.FILL_SPANS[0][2]}]}
        previous = {'schema': 'project-epoch-scene8b-copy-producers-v1',
                    'q_alias_cases_unresolved': [2, 3, 6, 7],
                    'producers': [{'entry': '$CD347D', 'shape': 'half',
                        'postcopy': {'entry': '$CD34F1', 'termination_proved': False,
                                     'memory_effects_proved': False, 'control': control}}]}
        self.assertEqual(a.preserved_copy_contract(previous)['inherited_near_frame_bytes'], 2)
        for change in ('termination', 'frame', 'alias', 'span'):
            bad = copy.deepcopy(previous)
            post = bad['producers'][0]['postcopy']
            if change == 'termination': post['termination_proved'] = True
            if change == 'frame': post['control']['maximum_counted_bytes_including_root_call_frame'] = 11
            if change == 'alias': bad['q_alias_cases_unresolved'] = []
            if change == 'span': post['control']['decoded_byte_intervals'][0]['end_exclusive'] = '$CD352C'
            with self.subTest(change=change), self.assertRaises(ValueError):
                a.preserved_copy_contract(bad)

    def test_import_does_not_read_rom_or_prerequisites(self):
        spec = importlib.util.spec_from_file_location('half_fill_pure_import_fixture', a.__file__)
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected file read')):
            spec.loader.exec_module(module)
        self.assertEqual(module.START, 0xCD34F1)

    def test_source_span_mutation_refuses(self):
        _, read, start, end = specimen(bytes.fromhex('A9 00 00 60'))
        digest = a.sha(read(start, end-start))
        self.assertEqual(a.pin_spans(read, ((start, end, digest),))[0]['size'], 4)
        with self.assertRaisesRegex(ValueError, 'span drift'):
            a.pin_spans(read, ((start, end, '0'*64),))

    def test_noncanonical_rom_refuses_before_any_prefix_replay(self):
        with self.assertRaisesRegex(ValueError, 'canonical ROM identity'):
            a.audit(b'not a cartridge', mock.Mock(side_effect=AssertionError('unexpected replay')))

    def test_serialization_is_binary_utf8_lf_with_one_newline(self):
        raw = a.serial({'test': [1, 2]})
        self.assertIsInstance(raw, bytes)
        self.assertNotIn(b'\r', raw)
        self.assertTrue(raw.endswith(b'\n'))
        self.assertFalse(raw.endswith(b'\n\n'))


if __name__ == '__main__':
    unittest.main()
