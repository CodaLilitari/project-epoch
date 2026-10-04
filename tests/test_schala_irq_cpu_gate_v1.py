"""Adversarial source-bound tests; these are not native execution claims."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import schala_irq_cpu_gate_v1 as gate


def sample(state, lock=False):
    return gate.sample_cpu_cycle(state, dma_irq_lock=lock, callbacks_closed=True)


def decide(state):
    return gate.instruction_boundary(state, callbacks_closed=True)


def halted(state, lock=False):
    return gate.halted_step(
        state, dma_irq_lock=lock, callbacks_closed=True,
        idle_clock_signals_unchanged=True,
    )


class CpuGateTests(unittest.TestCase):
    def test_source_assertion_after_sample_does_not_retroactively_accept(self):
        state = sample(gate.CpuGateState())
        state = gate.set_irq_source(state, gate.PPU_IRQ)
        self.assertEqual(decide(state).selected, "none")
        self.assertEqual(decide(sample(state)).selected, "irq")

    def test_sampled_irq_survives_sei(self):
        state = sample(gate.CpuGateState(irq_source=gate.PPU_IRQ, ps=0xA1))
        state = gate.set_interrupt_disable(state, True)
        result = decide(state)
        self.assertEqual(state.ps, 0xA5)
        self.assertEqual(result.selected, "irq")
        self.assertFalse(result.handler_entry_proved)
        self.assertEqual(decide(sample(state)).selected, "none")

    def test_cli_does_not_retroactively_sample(self):
        state = sample(gate.CpuGateState(irq_source=1, ps=0xFF))
        state = gate.set_interrupt_disable(state, False)
        self.assertEqual(state.ps, 0xFB)
        self.assertEqual(decide(state).selected, "none")
        self.assertEqual(decide(sample(state)).selected, "irq")

    def test_source_clear_does_not_cancel_previous_sample(self):
        state = gate.clear_irq_source(sample(gate.CpuGateState(irq_source=1)), 1)
        self.assertEqual(state.irq_source, 0)
        self.assertEqual(decide(state).selected, "irq")
        self.assertEqual(decide(sample(state)).selected, "none")

    def test_clearing_ppu_preserves_coprocessor_source(self):
        for source in range(256):
            state = gate.CpuGateState(irq_source=source, prev_irq_source=1)
            cleared = gate.clear_irq_source(state, 1)
            self.assertEqual(cleared.irq_source, source & 0xFE)
            self.assertEqual(cleared.prev_irq_source, 1)
        self.assertEqual(sample(gate.clear_irq_source(gate.CpuGateState(irq_source=3), 1)).prev_irq_source, 1)

    def test_exhaustive_status_and_byte_source_sample(self):
        for ps in range(256):
            for source in range(256):
                sampled = sample(gate.CpuGateState(irq_source=source, ps=ps))
                self.assertEqual(sampled.prev_irq_source, int(source != 0 and not ps & 4))
                self.assertEqual(sampled.ps, ps)
                self.assertEqual(sampled.wai_over, source != 0)

    def test_dma_lock_suppresses_sample_then_is_cleared(self):
        state = gate.CpuGateState(irq_source=3, prev_irq_source=255)
        locked = sample(state, True)
        self.assertEqual(locked.prev_irq_source, 0)
        self.assertFalse(locked.irq_lock)
        self.assertFalse(locked.wai_over)
        self.assertEqual(decide(locked).selected, "none")
        self.assertEqual(decide(sample(locked)).selected, "irq")

    def test_incoming_lock_is_replaced_by_closed_dma_result(self):
        state = gate.CpuGateState(irq_source=1, irq_lock=True)
        self.assertEqual(sample(state, False).prev_irq_source, 1)

    def test_nmi_priority_is_acceptance_only(self):
        state = gate.CpuGateState(need_nmi=True, prev_irq_source=1, irq_source=1)
        result = decide(state)
        self.assertEqual(result.selected, "nmi")
        self.assertFalse(result.state_at_selection.need_nmi)
        self.assertEqual(result.state_at_selection.prev_irq_source, 1)
        self.assertFalse(result.handler_entry_proved)
        self.assertEqual(result.state_at_selection.ps, 0)  # Entry has not set I.

    def test_nmi_counter_dma_retry_and_nonexpiry_preservation(self):
        for count in range(256):
            for need in (False, True):
                state = gate.CpuGateState(nmi_flag_counter=count, need_nmi=need)
                clear = sample(state)
                locked = sample(state, True)
                self.assertEqual(clear.nmi_flag_counter, max(count - 1, 0))
                self.assertEqual(locked.nmi_flag_counter, 1 if count == 1 else max(count - 1, 0))
                self.assertEqual(clear.need_nmi, True if count == 1 else need)
                self.assertEqual(locked.need_nmi, False if count == 1 else need)
                self.assertEqual(clear.wai_over, count == 1)
                self.assertFalse(locked.wai_over)

    def test_every_nonzero_serialized_previous_byte_selects_irq(self):
        for previous in range(256):
            result = decide(gate.CpuGateState(prev_irq_source=previous, ps=4))
            self.assertEqual(result.selected, "irq" if previous else "none")

    def test_wai_wake_is_delayed_by_pre_idle_snapshot(self):
        waiting = gate.CpuGateState(irq_source=1, stop_state=gate.StopState.WAITING_FOR_IRQ)
        first = halted(waiting)
        self.assertTrue(first.state_at_selection.wai_over)
        self.assertEqual(first.state_at_selection.stop_state, gate.StopState.WAITING_FOR_IRQ)
        self.assertFalse(first.check_reached)
        second = halted(first.state_at_selection)
        self.assertTrue(second.check_reached)
        self.assertEqual(second.selected, "irq")
        self.assertEqual(second.state_at_selection.stop_state, gate.StopState.RUNNING)

    def test_wai_wakes_with_i_set_without_irq_acceptance(self):
        waiting = gate.CpuGateState(irq_source=1, ps=4, stop_state=gate.StopState.WAITING_FOR_IRQ)
        second = halted(halted(waiting).state_at_selection)
        self.assertTrue(second.check_reached)
        self.assertEqual(second.selected, "none")
        self.assertEqual(second.state_at_selection.stop_state, gate.StopState.RUNNING)

    def test_wai_prior_wake_survives_dma_lock(self):
        waiting = gate.CpuGateState(
            irq_source=1, wai_over=True, stop_state=gate.StopState.WAITING_FOR_IRQ
        )
        result = halted(waiting, True)
        self.assertTrue(result.check_reached)
        self.assertEqual(result.selected, "none")
        self.assertTrue(result.state_at_selection.wai_over)

    def test_stp_transition_instruction_and_later_stopped_exec_differ(self):
        stopped = gate.CpuGateState(prev_irq_source=1, stop_state=gate.StopState.STOPPED)
        self.assertEqual(decide(stopped).selected, "irq")
        with self.assertRaisesRegex(gate.CpuGateRefusal, "stopped CPU"):
            halted(stopped)

    def test_refuse_unclosed_effects(self):
        state = gate.CpuGateState()
        for value in (None, False, 1, "closed"):
            with self.assertRaises(gate.CpuGateRefusal):
                gate.sample_cpu_cycle(state, dma_irq_lock=False, callbacks_closed=value)
            with self.assertRaises(gate.CpuGateRefusal):
                gate.instruction_boundary(state, callbacks_closed=value)
        for lock in (None, 0, 1, "false"):
            with self.assertRaises(gate.CpuGateRefusal):
                sample(state, lock)
        waiting = replace(state, stop_state=gate.StopState.WAITING_FOR_IRQ)
        with self.assertRaisesRegex(gate.CpuGateRefusal, "idle clock"):
            gate.halted_step(waiting, dma_irq_lock=False, callbacks_closed=True, idle_clock_signals_unchanged=False)
        with self.assertRaisesRegex(gate.CpuGateRefusal, "requires WAI"):
            halted(state)

    def test_exact_input_types_and_ranges(self):
        for field in ("irq_source", "prev_irq_source", "nmi_flag_counter", "ps"):
            for invalid in (True, False, -1, 256, 1.0, None):
                with self.subTest(field=field, invalid=invalid):
                    with self.assertRaises(gate.CpuGateRefusal):
                        gate.CpuGateState(**{field: invalid})
        for field in ("need_nmi", "irq_lock", "wai_over"):
            for invalid in (0, 1, None, "false"):
                with self.assertRaises(gate.CpuGateRefusal):
                    gate.CpuGateState(**{field: invalid})
        for invalid in (0, 1, 2, 3, True, "running"):
            with self.assertRaises(gate.CpuGateRefusal):
                gate.CpuGateState(stop_state=invalid)
        for invalid in (4, 255, True, -1):
            with self.assertRaises(gate.CpuGateRefusal):
                gate.clear_irq_source(gate.CpuGateState(), invalid)
        with self.assertRaises(gate.CpuGateRefusal):
            sample({})
        with self.assertRaises(gate.CpuGateRefusal):
            gate.set_interrupt_disable(gate.CpuGateState(), 1)


if __name__ == "__main__":
    unittest.main()
