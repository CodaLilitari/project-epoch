"""Boundary/truth-table tests of the separate source-only IRQ register core."""

from dataclasses import FrozenInstanceError, fields, replace
from itertools import product
import unittest

from tools.schala_irq_transition_core_v1 import (
    Event, IrqState, RefusedPremise, TickContext, Transition,
    process_irq_counters, read_timeup, set_irq_flag, update_irq_level,
    write_nmitimen, write_timer,
)


def tick(state, h=14, line=120, nmi=225, overclock=False):
    return process_irq_counters(state, TickContext(h, line, nmi, overclock))


def kinds(result):
    return tuple(event.kind for event in result.events)


class PendingTruthTableTests(unittest.TestCase):
    def test_all_256_pending_counts_with_independent_flag_source_enable_states(self):
        # No new match is possible. Three exceptional input count classes
        # have independently specified outputs; all others retain flag/source.
        cases = 0
        for count, flag, source, h_enable, v_enable, cache, level in product(
            range(256), (False, True), (False, True), (False, True),
            (False, True), (False, True), (False, True)
        ):
            before = IrqState(need_irq=count, irq_flag=flag,
                              ppu_irq_source=source, h_enabled=h_enable,
                              v_enabled=v_enable, irq_enabled_cache=cache,
                              irq_level=level, h_timer=600, v_timer=601)
            # Incoherent true cache + disabled H/V makes unconditional match.
            # Keep a high old level in that one case to isolate consumption.
            if cache and not (h_enable or v_enable):
                before = replace(before, irq_level=True)
            result = tick(before)
            expected_flag = (h_enable or v_enable) if count == 2 else flag
            expected_source = flag if count == 1 else (
                False if count == 2 and not (h_enable or v_enable) else source
            )
            self.assertEqual(result.state.need_irq, max(0, count - 1))
            self.assertIs(result.state.irq_flag, expected_flag)
            self.assertIs(result.state.ppu_irq_source, expected_source)
            self.assertEqual(kinds(result).count("pending-consume"), int(count > 0))
            self.assertEqual(kinds(result).count("irq-flag"), int(count == 2))
            self.assertNotIn("timer-match", kinds(result))
            cases += 1
        self.assertEqual(cases, 16384)

    def test_count_one_false_flag_clears_source_and_does_not_set_flag(self):
        state = IrqState(need_irq=1, ppu_irq_source=True, v_enabled=True,
                         irq_enabled_cache=True)
        result = tick(state)
        self.assertFalse(result.state.ppu_irq_source)
        self.assertFalse(result.state.irq_flag)
        self.assertEqual(result.events[:2], (
            Event("pending-consume", 1, 0), Event("ppu-source-clear", True, False)))

    def test_two_tick_flag_then_source_are_distinct_events(self):
        state = IrqState(need_irq=2, v_enabled=True, irq_enabled_cache=True)
        flag_tick = tick(state)
        source_tick = tick(flag_tick.state, h=18)
        self.assertTrue(flag_tick.state.irq_flag)
        self.assertFalse(flag_tick.state.ppu_irq_source)
        self.assertNotIn("ppu-source-set", kinds(flag_tick))
        self.assertTrue(source_tick.state.ppu_irq_source)
        self.assertNotIn("irq-flag", kinds(source_tick))

    def test_consumed_source_clear_precedes_counter_match_and_rearm(self):
        state = IrqState(h_counter=7, h_timer=8, h_enabled=True,
                         irq_enabled_cache=True, need_irq=1, ppu_irq_source=True)
        result = tick(state)
        self.assertEqual(kinds(result), (
            "pending-consume", "ppu-source-clear", "h-counter",
            "timer-match", "pending-arm", "irq-level"))
        self.assertEqual(result.state.need_irq, 2)
        self.assertFalse(result.state.ppu_irq_source)

    def test_consumed_source_assertion_can_precede_new_arm(self):
        state = IrqState(h_counter=7, h_timer=8, h_enabled=True,
                         irq_enabled_cache=True, need_irq=1, irq_flag=True)
        result = tick(state)
        self.assertEqual(kinds(result)[1], "ppu-source-set")
        self.assertTrue(result.state.ppu_irq_source)
        self.assertEqual(result.state.need_irq, 2)

    def test_fresh_match_can_overwrite_hostile_large_pending_after_consumption(self):
        state = IrqState(h_counter=7, h_timer=8, h_enabled=True,
                         irq_enabled_cache=True, need_irq=255)
        result = tick(state)
        self.assertEqual(result.events[0], Event("pending-consume", 255, 254))
        self.assertIn(Event("pending-arm", 254, 2), result.events)


class CounterAndNmiTests(unittest.TestCase):
    def test_exact_h2_h6_h10_and_other_branches(self):
        expected = {0: (9, 3), 1: (9, 3), 2: (10, 3), 3: (9, 3),
                    4: (9, 3), 5: (9, 3), 6: (0, 4), 7: (9, 3),
                    8: (9, 3), 9: (9, 3), 10: (0, 3), 11: (10, 3),
                    14: (10, 3), 65535: (10, 3)}
        for h, counters in expected.items():
            with self.subTest(h=h):
                result = tick(IrqState(h_counter=9, v_counter=3), h=h)
                self.assertEqual((result.state.h_counter, result.state.v_counter), counters)

    def test_uint16_h_and_v_wrap_independently(self):
        for h in (2, 14, 65535):
            self.assertEqual(tick(IrqState(h_counter=65535), h=h).state.h_counter, 0)
        self.assertEqual(tick(IrqState(v_counter=65535), h=6).state.v_counter, 0)

    def test_h6_overclock_or_line_zero_suppresses_only_v_increment(self):
        for line, overclock in ((0, False), (0, True), (3, True)):
            result = tick(IrqState(h_counter=55, v_counter=9), h=6,
                          line=line, overclock=overclock)
            self.assertEqual((result.state.h_counter, result.state.v_counter), (0, 9))
        self.assertEqual(tick(IrqState(v_counter=9), h=6, line=3).state.v_counter, 10)

    def test_h2_line_zero_resets_v_and_nmi_latch_before_level_evaluation(self):
        before = IrqState(v_counter=91, v_timer=0, v_enabled=True,
                          irq_enabled_cache=True, nmi_flag=True)
        result = tick(before, h=2, line=0)
        self.assertEqual(kinds(result), (
            "h-counter", "nmi-flag", "v-counter", "timer-match", "pending-arm", "irq-level"))
        self.assertEqual(result.state.v_counter, 0)
        self.assertFalse(result.state.nmi_flag)
        self.assertEqual(result.state.need_irq, 2)

    def test_h2_nmi_scanline_zero_condition_has_source_priority(self):
        result = tick(IrqState(v_counter=91), h=2, line=0, nmi=0)
        self.assertTrue(result.state.nmi_flag)
        self.assertEqual(result.state.v_counter, 91)

    def test_nmi_latch_h2_and_request_h6_are_distinct(self):
        before = IrqState(nmi_enabled=True, v_counter=224)
        h2 = tick(before, h=2, line=225)
        self.assertTrue(h2.state.nmi_flag)
        self.assertNotIn("cpu-nmi-request", kinds(h2))
        h6 = tick(h2.state, h=6, line=225)
        self.assertIn(Event("cpu-nmi-request", None, 1), h6.events)
        self.assertLess(kinds(h6).index("v-counter"), kinds(h6).index("cpu-nmi-request"))
        self.assertNotIn("cpu-nmi-request", kinds(tick(IrqState(), h=6, line=225)))

    def test_h6_overclock_does_not_suppress_separate_nmi_request_branch(self):
        result = tick(IrqState(nmi_enabled=True, v_counter=224), h=6,
                      line=225, overclock=True)
        self.assertEqual(result.state.v_counter, 224)
        self.assertIn(Event("cpu-nmi-request", None, 1), result.events)


class LevelAndFlagTests(unittest.TestCase):
    def test_match_requires_each_enabled_comparison(self):
        for eh, ev, mh, mv in product((False, True), repeat=4):
            state = IrqState(h_enabled=eh, v_enabled=ev,
                             irq_enabled_cache=eh or ev,
                             h_counter=1, v_counter=2,
                             h_timer=1 if mh else 9, v_timer=2 if mv else 9)
            result = update_irq_level(state, 14)
            expected = (eh or ev) and (not eh or mh) and (not ev or mv)
            self.assertIs(result.state.irq_level, expected)
            self.assertEqual(result.state.need_irq, 2 if expected else 0)

    def test_h6_three_tick_arm_requires_horizontal_enable(self):
        for h in (2, 6, 10, 14):
            horizontal = IrqState(h_enabled=True, irq_enabled_cache=True,
                                  h_timer=0, h_counter=0)
            vertical = IrqState(v_enabled=True, irq_enabled_cache=True,
                                v_timer=0, v_counter=0)
            self.assertEqual(update_irq_level(horizontal, h).state.need_irq, 3 if h == 6 else 2)
            self.assertEqual(update_irq_level(vertical, h).state.need_irq, 2)

    def test_h6_horizontal_match_flag_and_source_delayed_to_h14_h18(self):
        state = IrqState(h_enabled=True, irq_enabled_cache=True, h_timer=0)
        rows = []
        for h in (6, 10, 14, 18):
            result = tick(state, h=h)
            state = result.state
            rows.append((state.need_irq, state.irq_flag, state.ppu_irq_source))
        self.assertEqual(rows, [(3, False, False), (2, False, False), (1, True, False), (0, True, True)])

    def test_high_level_does_not_rearm_until_a_falling_edge(self):
        state = IrqState(v_enabled=True, irq_enabled_cache=True,
                         v_timer=7, v_counter=7, irq_level=True, need_irq=99)
        self.assertEqual(update_irq_level(state, 14).state.need_irq, 99)
        fallen = update_irq_level(replace(state, v_counter=8), 14).state
        risen = update_irq_level(replace(fallen, v_counter=7), 14)
        self.assertEqual(risen.state.need_irq, 2)

    def test_false_enable_cache_suppresses_match_without_touching_pending_flag_source(self):
        state = IrqState(v_enabled=True, irq_enabled_cache=False,
                         v_timer=7, v_counter=7, irq_level=True,
                         need_irq=99, irq_flag=True, ppu_irq_source=True)
        result = update_irq_level(state, 14)
        self.assertFalse(result.state.irq_level)
        self.assertEqual(result.state.need_irq, 99)
        self.assertTrue(result.state.irq_flag)
        self.assertTrue(result.state.ppu_irq_source)
        self.assertFalse(state.enable_cache_coherent)

    def test_set_flag_uses_enables_and_never_asserts_source(self):
        for requested, eh, ev, source in product((False, True), repeat=4):
            state = IrqState(h_enabled=eh, v_enabled=ev,
                             irq_enabled_cache=not (eh or ev), ppu_irq_source=source)
            result = set_irq_flag(state, requested)
            expected = requested and (eh or ev)
            self.assertIs(result.state.irq_flag, expected)
            self.assertIs(result.state.ppu_irq_source, source if expected else False)
            self.assertNotIn("ppu-source-set", kinds(result))


class RegisterTests(unittest.TestCase):
    def test_every_byte_for_all_timer_registers(self):
        # Start with hostile high timer bits to prove the C++ masks truncate
        # them, while updating the chosen timer preserves the other timer.
        for addr, value in product(range(0x4207, 0x420B), range(256)):
            state = IrqState(h_timer=0xFEDC, v_timer=0xABCD)
            result = write_timer(state, addr, value, 14)
            if addr == 0x4207:
                expected = (value, 0xABCD)
            elif addr == 0x4208:
                expected = (0xDC + 256 * (value % 2), 0xABCD)
            elif addr == 0x4209:
                expected = (0xFEDC, 0x100 + value)
            else:
                expected = (0xFEDC, 0xCD + 256 * (value % 2))
            self.assertEqual((result.state.h_timer, result.state.v_timer), expected)

    def test_timer_write_recalculates_level_without_counter_tick_or_pending_consumption(self):
        state = IrqState(v_enabled=True, irq_enabled_cache=True,
                         v_counter=119, v_timer=211, need_irq=255)
        result = write_timer(state, 0x4209, 119, 754)
        self.assertEqual(result.state.need_irq, 2)
        self.assertEqual(result.state.v_counter, 119)
        self.assertNotIn("pending-consume", kinds(result))
        self.assertIn("timer-match", kinds(result))

    def test_disable_clears_flag_source_but_preserves_level_pending_and_counters(self):
        state = IrqState(v_enabled=True, irq_enabled_cache=True,
                         irq_level=True, need_irq=2, irq_flag=True,
                         ppu_irq_source=True, h_counter=30, v_counter=4)
        result = write_nmitimen(state, 0)
        self.assertFalse(result.state.irq_flag)
        self.assertFalse(result.state.ppu_irq_source)
        self.assertTrue(result.state.irq_level)
        self.assertEqual(result.state.need_irq, 2)
        self.assertEqual((result.state.h_counter, result.state.v_counter), (30, 4))
        self.assertTrue(result.state.enable_cache_coherent)

    def test_enable_nmitimen_does_not_immediately_evaluate_equal_timer(self):
        state = IrqState(v_counter=119, v_timer=119)
        result = write_nmitimen(state, 0x20)
        self.assertEqual(result.state.need_irq, 0)
        self.assertFalse(result.state.irq_level)
        self.assertNotIn("timer-match", kinds(result))
        self.assertEqual(update_irq_level(result.state, 754).state.need_irq, 2)

    def test_nmitimen_nmi_rising_enable_requests_two_only_if_latch_set(self):
        for enabled, flag, new_enabled in product((False, True), repeat=3):
            state = IrqState(nmi_enabled=enabled, nmi_flag=flag)
            result = write_nmitimen(state, 0x80 if new_enabled else 0)
            expected = flag and new_enabled and not enabled
            self.assertEqual(kinds(result).count("cpu-nmi-request"), int(expected))
            if expected:
                self.assertIn(Event("cpu-nmi-request", None, 2), result.events)

    def test_all_nmitimen_values_with_stable_autojoy_have_exact_enables(self):
        for value in range(256):
            state = IrqState(auto_joy_enabled=bool(value & 1))
            result = write_nmitimen(state, value)
            self.assertEqual(result.state.h_enabled, bool(value & 0x10))
            self.assertEqual(result.state.v_enabled, bool(value & 0x20))
            self.assertEqual(result.state.nmi_enabled, bool(value & 0x80))
            self.assertTrue(result.state.enable_cache_coherent)

    def test_unclosed_autojoy_transition_refuses_before_any_output(self):
        for old in (False, True):
            with self.assertRaisesRegex(RefusedPremise, "callback closure"):
                write_nmitimen(IrqState(auto_joy_enabled=old), 0 if old else 1)

    def test_timeup_all_pending_and_flag_source_combinations(self):
        for pending, flag, source in product(range(256), (False, True), (False, True)):
            state = IrqState(need_irq=pending, irq_flag=flag, ppu_irq_source=source)
            result = read_timeup(state, 0xD5)
            self.assertEqual(result.read_value, 0xD5 if flag else 0x55)
            acknowledged = flag and pending == 0
            self.assertIs(result.state.irq_flag, False if acknowledged else flag)
            self.assertIs(result.state.ppu_irq_source, False if acknowledged else source)
            self.assertEqual(result.state.need_irq, pending)


class ValidationTests(unittest.TestCase):
    def test_every_uint_state_field_refuses_out_of_range_and_nonexact_types(self):
        for name, maximum in (("h_counter", 65535), ("v_counter", 65535),
                              ("h_timer", 65535), ("v_timer", 65535), ("need_irq", 255)):
            for bad in (-1, maximum + 1, True, False, 1.0, "1", None):
                with self.subTest(name=name, bad=bad), self.assertRaises(ValueError):
                    IrqState(**{name: bad})
            IrqState(**{name: maximum})

    def test_every_boolean_state_field_refuses_integer_and_other_coercions(self):
        state = IrqState()
        for field in fields(state):
            if type(getattr(state, field.name)) is bool:
                for bad in (0, 1, "true", None):
                    with self.subTest(field=field.name, bad=bad), self.assertRaises(ValueError):
                        replace(state, **{field.name: bad})

    def test_context_validation_is_strict(self):
        for name in ("h_clock", "scanline", "nmi_scanline"):
            for bad in (-1, 65536, True, 1.0, None):
                values = dict(h_clock=14, scanline=2, nmi_scanline=225,
                              in_overclocked_scanline=False)
                values[name] = bad
                with self.assertRaises(ValueError):
                    TickContext(**values)
        with self.assertRaises(ValueError):
            TickContext(14, 2, 225, 0)

    def test_public_functions_refuse_invalid_objects_and_scalar_types(self):
        for bad in (None, {}, 0):
            for call in (lambda: tick(bad), lambda: update_irq_level(bad, 14),
                         lambda: set_irq_flag(bad, True), lambda: read_timeup(bad, 0),
                         lambda: write_timer(bad, 0x4207, 0, 14),
                         lambda: write_nmitimen(bad, 0)):
                with self.assertRaises(ValueError):
                    call()
        for call in (lambda: set_irq_flag(IrqState(), 1),
                     lambda: update_irq_level(IrqState(), True),
                     lambda: read_timeup(IrqState(), 256),
                     lambda: write_nmitimen(IrqState(), False),
                     lambda: write_timer(IrqState(), 0x4207, -1, 14),
                     lambda: write_timer(IrqState(), 0x4207, 0, 65536),
                     lambda: process_irq_counters(IrqState(), {})):
            with self.assertRaises(ValueError):
                call()

    def test_uncovered_register_refuses(self):
        for address in (0, 0x4200, 0x4206, 0x420B, 0xFFFF):
            with self.assertRaises(RefusedPremise):
                write_timer(IrqState(), address, 0, 14)

    def test_input_state_is_immutable_and_events_preserve_same_value_calls(self):
        before = IrqState(irq_flag=True, need_irq=1, ppu_irq_source=True)
        result = tick(before)
        self.assertEqual(before.need_irq, 1)
        self.assertEqual(result.events[1], Event("ppu-source-set", True, True))
        with self.assertRaises(FrozenInstanceError):
            before.need_irq = 9

    def test_result_and_event_constructors_refuse_invalid_payload_types(self):
        for args in (("", 0, 0), (1, 0, 0), ("x", "0", 0), ("x", None, None)):
            with self.assertRaises(ValueError):
                Event(*args)
        for args in (({}, ()), (IrqState(), []), (IrqState(), ("x",)), (IrqState(), (), True)):
            with self.assertRaises(ValueError):
                Transition(*args)


if __name__ == "__main__":
    unittest.main()
