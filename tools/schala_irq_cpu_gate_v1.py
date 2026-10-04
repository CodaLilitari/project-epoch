"""Pure, conditional CPU IRQ/NMI gates for pinned Mesen 2.1.1.

Source commit: 137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1.
SnesCpu.cpp:29-83,121-130; SnesCpu.Shared.h:315-365;
SnesCpu.Instructions.h:241-264,505-534,1157-1168.

This is a decision model, not a CPU, instruction/timing emulator or proof of
handler entry. callbacks_closed=True asserts omitted callbacks leave these
modeled fields unchanged; it is a conditional premise, not a validated runtime
certificate. DMA effects must already be reflected in the supplied state,
and its exact returned irqLock value is a separate mandatory input.
Byte-valued state accepts adversarial serialized values, not just reachable
source states; the sampling operation narrows PrevIrqSource to zero or one.
"""

from dataclasses import dataclass, replace
from enum import IntEnum


SOURCE_COMMIT = "137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1"
IRQ_DISABLE = 0x04
PPU_IRQ = 0x01
COPROCESSOR_IRQ = 0x02


class CpuGateRefusal(ValueError):
    """The input or an explicitly required source premise is not closed."""


class StopState(IntEnum):
    RUNNING = 0
    STOPPED = 1
    WAITING_FOR_IRQ = 2


def _byte(name: str, value: int) -> None:
    if type(value) is not int or not 0 <= value <= 0xFF:
        raise CpuGateRefusal(f"{name} must be an exact uint8 integer")


def _bool(name: str, value: bool) -> None:
    if type(value) is not bool:
        raise CpuGateRefusal(f"{name} must be an exact boolean")


def _closed(name: str, value: bool) -> None:
    if value is not True:
        raise CpuGateRefusal(f"unknown or unclosed {name}")


@dataclass(frozen=True)
class CpuGateState:
    irq_source: int = 0
    prev_irq_source: int = 0
    nmi_flag_counter: int = 0
    need_nmi: bool = False
    ps: int = 0
    irq_lock: bool = False
    wai_over: bool = False
    stop_state: StopState = StopState.RUNNING

    def __post_init__(self) -> None:
        for name in ("irq_source", "prev_irq_source", "nmi_flag_counter", "ps"):
            _byte(name, getattr(self, name))
        for name in ("need_nmi", "irq_lock", "wai_over"):
            _bool(name, getattr(self, name))
        if type(self.stop_state) is not StopState:
            raise CpuGateRefusal("stop_state must be a known StopState")


@dataclass(frozen=True)
class CpuGateDecision:
    # State immediately after selection, BEFORE ProcessInterrupt side effects.
    state_at_selection: CpuGateState
    selected: str
    check_reached: bool

    @property
    def handler_entry_proved(self) -> bool:
        return False


def _state(value: CpuGateState) -> None:
    if type(value) is not CpuGateState:
        raise CpuGateRefusal("state must be an exact CpuGateState")


def _source_mask(mask: int) -> None:
    _byte("source mask", mask)
    if mask & ~(PPU_IRQ | COPROCESSOR_IRQ):
        raise CpuGateRefusal("source mask contains undefined source bits")


def set_irq_source(state: CpuGateState, mask: int) -> CpuGateState:
    """Set source bits; do not rewrite the prior CPU sample."""
    _state(state)
    _source_mask(mask)
    return replace(state, irq_source=state.irq_source | mask)


def clear_irq_source(state: CpuGateState, mask: int) -> CpuGateState:
    """Clear only the named source bits, retaining any previous sample."""
    _state(state)
    _source_mask(mask)
    return replace(state, irq_source=state.irq_source & (~mask & 0xFF))


def set_interrupt_disable(state: CpuGateState, disabled: bool) -> CpuGateState:
    """The status mutation of SEI/CLI, without their addressing or cycles."""
    _state(state)
    _bool("disabled", disabled)
    ps = state.ps | IRQ_DISABLE if disabled else state.ps & ~IRQ_DISABLE
    return replace(state, ps=ps)


def sample_cpu_cycle(
    state: CpuGateState, *, dma_irq_lock: bool | None, callbacks_closed: bool
) -> CpuGateState:
    """Model DetectNmiSignalEdge after the caller's closed DMA service.

    ProcessCpuCycle assigns irqLock from ProcessPendingTransfers, or false
    when no transfer is pending. Therefore the incoming irq_lock is replaced,
    not assumed to describe that service. Clock progression and bus accesses
    occur after this sample and are outside this function.
    """
    _state(state)
    _closed("callbacks", callbacks_closed)
    _bool("DMA irqLock result", dma_irq_lock)
    count, need, wake = state.nmi_flag_counter, state.need_nmi, state.wai_over
    if count:
        count -= 1
        if count == 0:
            if not dma_irq_lock:
                need, wake = True, True
            else:
                count, need = 1, False
    if not dma_irq_lock:
        previous = int(bool(state.irq_source) and not bool(state.ps & IRQ_DISABLE))
        if state.irq_source:
            wake = True
    else:
        previous = 0
    return replace(
        state, nmi_flag_counter=count, need_nmi=need, wai_over=wake,
        prev_irq_source=previous, irq_lock=False,
    )


def instruction_boundary(
    state: CpuGateState, *, callbacks_closed: bool
) -> CpuGateDecision:
    """Select the CheckForInterrupts branch, not its interrupt frame/vector.

    This is the actual post-RunOp call site, including the transition
    instruction that just set WAI/STP. It does not filter by StopState.
    Subsequent halted Exec calls instead follow halted_step below.
    """
    _state(state)
    _closed("callbacks", callbacks_closed)
    if state.need_nmi:
        return CpuGateDecision(replace(state, need_nmi=False), "nmi", True)
    if state.prev_irq_source:
        return CpuGateDecision(state, "irq", True)
    return CpuGateDecision(state, "none", True)


def halted_step(
    state: CpuGateState, *, dma_irq_lock: bool | None, callbacks_closed: bool,
    idle_clock_signals_unchanged: bool,
) -> CpuGateDecision:
    """Bounded WAI gate with no signal changes during post-sample Idle clocks.

    The premise covers the omitted IncMasterClock6 and ProcessIdleCycle
    effects. It is not inferred from endpoint equality. Without it, use a
    separately closed event composition; this function refuses the step.
    Already-stopped execution never reaches this modeled CPU sample/check;
    reset and the stopped branch's IncMasterClock4 are outside this model.
    """
    _state(state)
    _closed("callbacks", callbacks_closed)
    if state.stop_state == StopState.STOPPED:
        raise CpuGateRefusal("stopped CPU has no IRQ check; reset/clock step unmodeled")
    if state.stop_state != StopState.WAITING_FOR_IRQ:
        raise CpuGateRefusal("halted_step requires WAI state")
    _closed("idle clock signal stability", idle_clock_signals_unchanged)
    over_before_idle = state.wai_over
    sampled = sample_cpu_cycle(
        state, dma_irq_lock=dma_irq_lock, callbacks_closed=callbacks_closed
    )
    if over_before_idle:
        running = replace(sampled, stop_state=StopState.RUNNING)
        return instruction_boundary(running, callbacks_closed=callbacks_closed)
    return CpuGateDecision(sampled, "none", False)
