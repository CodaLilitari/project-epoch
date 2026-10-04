"""Bounded Mesen Exec projection with explicit callback premises.

This is original source-conditional host analysis, not a CPU or DMA emulator.
Clock-consuming DMA work may call this kernel, but its bus side effects are
not simulated. Unknown callbacks never receive a deadline certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from schala_irq_transition_core_v1 import IrqState, TickContext, process_irq_counters


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Premises:
    """Caller hypotheses, never certificates. Inert callbacks includes every
    omitted renderer/control/SPC/debugger/memory-handler subordinate call;
    it excludes both IRQ-state mutation and further Exec reentry. The only
    ordinary nested work here is the pinned DRAM refresh body. Synthetic
    NestedEvent scripts explicitly override this hypothesis for counterexamples.
    """
    fixed_timers_and_enables: bool
    no_reset_or_state_restore: bool
    no_irq_acknowledgement: bool
    no_external_irq_source: bool
    inert_debugger_and_ppu_callbacks: bool
    absent_coprocessors: bool
    dma_bus_effects_excluded: bool
    valid_source_cache_and_zero_extras: bool

    def validate(self):
        for name, value in vars(self).items():
            require(value is True, 'unclosed premise: '+name)


CONDITIONAL_PREMISES = Premises(*([True]*8))


@dataclass(frozen=True)
class NestedEvent:
    """Explicit adversarial event callback, not a captured Mesen callback.

    Runs after the selected event body but before outer Exec phase dispatch.
    Only recursively executes the same kernel. It cannot write a register,
    restore state, reset, or alter the event queue directly.
    """
    line: int
    hclock: int
    clocks: int

    def __post_init__(self):
        require(type(self.line) is int and 1 <= self.line <= 224, 'callback line')
        require(type(self.hclock) is int and 0 <= self.hclock <= 1364 and self.hclock % 2 == 0, 'callback H')
        require(type(self.clocks) is int and 0 < self.clocks <= 80 and self.clocks % 2 == 0, 'bounded nested clocks')


class ExecModel:
    """Exec's event-before-phase order, including real 40-clock refresh.

    Source line mode is limited to lines 1..224 before VBlank/frame callbacks.
    1360 mode is a deliberately shortened comparison model, not a legal
    all-1360 raster. Explicit test callbacks cannot support the conditional
    fixed-callback result. Every output preserves this distinction.
    """

    def __init__(self, state: IrqState, *, clock: int, line: int, hclock: int,
                 premises: Premises, line_clocks: int = 1364,
                 next_event: str = 'hdma', next_event_h: int = 1104,
                 hdma_channels: int = 255, callbacks: tuple[NestedEvent, ...] = ()):
        require(type(state) is IrqState, 'exact IRQ state')
        require(type(premises) is Premises, 'explicit premises')
        premises.validate()
        require(type(clock) is int and 0 <= clock < 2**64 and clock % 2 == 0, 'even uint64 master clock')
        require(type(line) is int and 1 <= line <= 224, 'pre-VBlank line scope')
        require(type(line_clocks) is int and line_clocks in (1360, 1364), 'line model')
        require(type(hclock) is int and 0 <= hclock < line_clocks and hclock % 2 == 0, 'even H')
        require(next_event in ('hdma', 'refresh', 'end'), 'known event')
        require(type(next_event_h) is int and hclock < next_event_h <= 1364 and next_event_h % 2 == 0, 'future event')
        require(clock >= hclock, 'nonnegative line-start clock')
        refresh_h = 538-((clock-hclock) & 7)
        if next_event == 'refresh':
            require(next_event_h == refresh_h, 'source refresh phase')
        elif next_event == 'hdma':
            require(next_event_h == 1104 and hclock >= refresh_h+40, 'source HDMA phase')
        else:
            require(hclock >= 1104 and next_event_h == (1360 if hclock < 1360 else hclock+2), 'source end-line retry phase')
        require(type(hdma_channels) is int and 0 <= hdma_channels <= 255, 'HDMA byte')
        require(type(callbacks) is tuple and all(type(x) is NestedEvent for x in callbacks), 'explicit callback script')
        require(len({(x.line, x.hclock) for x in callbacks}) == len(callbacks), 'unique callback sites')
        self.state = state
        self.start_clock = self.clock = clock
        self.line, self.hclock = line, hclock
        self.line_clocks = line_clocks
        self.next_event, self.next_event_h = next_event, next_event_h
        self.hdma_channels = hdma_channels
        self.hdma_pending = self.dma_start_delay = self.need_to_process = False
        self.callbacks = {(x.line, x.hclock): x.clocks for x in callbacks}
        self.scripted = bool(callbacks)
        self.used_callbacks = set()
        self.depth = self.max_depth = self.calls = 0
        self.failed = False
        self.run_deadline = None
        self.ticks = []
        self.changes = []
        self.events = []

    def _event(self):
        event = self.next_event
        self.events.append((self.clock, self.line, self.hclock, event))
        if event == 'refresh':
            # The old event remains selected until all nested Exec calls return.
            # Equality will not re-trigger it as the H clock advances.
            for _ in range(20):
                self.exec()
            self.next_event, self.next_event_h = 'hdma', 1104
        elif event == 'hdma':
            if self.hdma_channels:
                self.hdma_pending = self.dma_start_delay = self.need_to_process = True
            self.next_event, self.next_event_h = 'end', 1360
        else:
            if self.hclock >= self.line_clocks:
                require(self.line < 224, 'VBlank/frame callback closure required')
                self.line += 1
                self.hclock = 0
                self.next_event, self.next_event_h = 'refresh', 538-(self.clock & 7)
            else:
                self.next_event_h += 2
        site = (self.line, self.hclock)
        if site in self.callbacks and site not in self.used_callbacks:
            self.used_callbacks.add(site)
            for _ in range(self.callbacks[site]//2):
                self.exec()

    def exec(self):
        require(not self.failed, 'model poisoned by earlier refusal')
        require(self.calls < 200000, 'finite Exec budget')
        require(self.depth < 8, 'finite callback depth')
        self.calls += 1
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        try:
            require(self.clock+2 < 2**64, 'uint64 clock wrap refused')
            require(self.run_deadline is None or self.clock+2 <= self.run_deadline, 'nested duration budget exhausted')
            self.clock += 2
            self.hclock += 2
            if self.hclock == self.next_event_h:
                self._event()
            if self.hclock & 3 == 0:
                pass  # ProcessPpuCycle: explicit inert-callback premise.
            elif self.hclock & 2:
                before = self.state
                result = process_irq_counters(before, TickContext(
                    h_clock=self.hclock, scanline=self.line,
                    nmi_scanline=225, in_overclocked_scanline=False))
                self.state = result.state
                self.ticks.append((self.clock, self.line, self.hclock, self.depth,
                                   self.state.h_counter, self.state.v_counter))
                for name in ('need_irq', 'irq_flag', 'ppu_irq_source', 'irq_level'):
                    a, b = getattr(before, name), getattr(self.state, name)
                    if a != b:
                        self.changes.append({'clock': self.clock, 'offset': self.clock-self.start_clock,
                            'line': self.line, 'hclock': self.hclock, 'field': name, 'before': a, 'after': b})
            # SyncCoprocessors: explicit absent-coprocessor premise.
        except Exception:
            self.failed = True
            raise
        finally:
            self.depth -= 1

    def run_until(self, predicate, *, max_clocks=130000):
        require(not self.failed, 'model poisoned by earlier refusal')
        require(type(max_clocks) is int and 0 <= max_clocks <= 260000, 'bounded duration')
        self.run_deadline = self.clock+max_clocks
        try:
            while not predicate(self):
                self.exec()
            require(self.used_callbacks == set(self.callbacks), 'unreached callback script')
            return self.summary()
        except Exception:
            self.failed = True
            raise
        finally:
            self.run_deadline = None

    def summary(self):
        require(not self.failed, 'model poisoned by earlier refusal')
        raw = (json.dumps(self.ticks, separators=(',', ':'))+'\n').encode('utf-8')
        return {'line_model': 'source-1364-pre-VBlank' if self.line_clocks == 1364 else 'shortened-1360-comparison',
            'scripted_adversarial_callbacks': self.scripted,
            'ordinary_callback_hypothesis_applies': not self.scripted,
            'clock': self.clock, 'line': self.line, 'hclock': self.hclock,
            'counter_h': self.state.h_counter, 'counter_v': self.state.v_counter,
            'exec_calls': self.calls, 'max_exec_depth': self.max_depth,
            'irq_counter_calls': len(self.ticks),
            'distinct_tick_clocks': len({t[0] for t in self.ticks}),
            'tick_ledger_sha256': hashlib.sha256(raw).hexdigest(),
            'changes': self.changes,
            'hdma_request_pending': self.hdma_pending,
            'hdma_service_or_bus_effects_simulated': False,
            'callback_premises_authenticated': False,
            'cpu_acceptance_clock': None, 'handler_entry_clock': None,
            'game_request_deadline_certified': False, 'helper_admitted': False}


def game_deadline(*, callback_closure=None, reset_write_closure=None, cpu_schedule=None):
    """No v1 input authenticates these premises; never promote caller claims."""
    raise ValueError('v1 has no game callback/reset/register/CPU closure certificate')
