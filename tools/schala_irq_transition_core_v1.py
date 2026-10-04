"""Pure Mesen 2.1.1 IRQ register transitions; no execution or admission claim.

Source revision: 137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1.
InternalRegisters.h:81-102 (level), 104-162 (one counter invocation).
InternalRegisters.cpp:180-187 (flag), 246-254 (TIMEUP), 299-329
(NMITIMEN), 352-375 (timer writes). Source URLs are in SOURCE_CITATIONS.

This module does not schedule counter invocations, recurse through Exec,
execute callbacks, accept CPU interrupts, enter handlers, or reset hardware.
Every caller supplies the instantaneous raster/overclock inputs. In particular,
one invocation does not imply four elapsed clocks: recursive Exec can change
the h-clock seen by a later invocation. NMI latch assignments and CPU NMI
request calls are represented as events, not as accepted CPU interrupts.

The cached IRQ enable and the two register enable bits are separate inputs.
Ordinary source state keeps them coherent; hostile inconsistent states remain
representable and must not acquire a valid-source-state certificate here.
Timers and counters have their source uint16 widths, even though ordinary
timer-register writes produce only nine-bit timer values. The source PPU IRQ
bit is isolated from other CPU IRQ sources, which this model never changes.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace


SOURCE_REVISION = "137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1"
_SOURCE_BASE = f"https://github.com/SourMesen/Mesen2/blob/{SOURCE_REVISION}/Core/SNES/"
SOURCE_CITATIONS = {
    "level_and_counter": _SOURCE_BASE + "InternalRegisters.h#L81-L162",
    "flag": _SOURCE_BASE + "InternalRegisters.cpp#L180-L187",
    "timeup": _SOURCE_BASE + "InternalRegisters.cpp#L246-L254",
    "nmitimen": _SOURCE_BASE + "InternalRegisters.cpp#L299-L329",
    "timers": _SOURCE_BASE + "InternalRegisters.cpp#L352-L375",
}


class RefusedPremise(ValueError):
    """A caller asked this bounded model to cross an unclosed premise."""


def _uint(name: str, value: int, bits: int) -> None:
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ValueError(f"{name} must be an exact uint{bits} integer")


def _bool(name: str, value: bool) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be an exact bool")


@dataclass(frozen=True, slots=True)
class IrqState:
    h_counter: int = 0
    v_counter: int = 0
    h_timer: int = 0x1FF
    v_timer: int = 0x1FF
    need_irq: int = 0
    irq_flag: bool = False
    irq_level: bool = False
    ppu_irq_source: bool = False
    h_enabled: bool = False
    v_enabled: bool = False
    irq_enabled_cache: bool = False
    nmi_enabled: bool = False
    nmi_flag: bool = False
    auto_joy_enabled: bool = False

    def __post_init__(self) -> None:
        for name in ("h_counter", "v_counter", "h_timer", "v_timer"):
            _uint(name, getattr(self, name), 16)
        _uint("need_irq", self.need_irq, 8)
        for field in fields(self):
            if field.name not in {"h_counter", "v_counter", "h_timer", "v_timer", "need_irq"}:
                _bool(field.name, getattr(self, field.name))

    @property
    def enable_cache_coherent(self) -> bool:
        return self.irq_enabled_cache == (self.h_enabled or self.v_enabled)


@dataclass(frozen=True, slots=True)
class TickContext:
    h_clock: int
    scanline: int
    nmi_scanline: int
    in_overclocked_scanline: bool

    def __post_init__(self) -> None:
        for name in ("h_clock", "scanline", "nmi_scanline"):
            _uint(name, getattr(self, name), 16)
        _bool("in_overclocked_scanline", self.in_overclocked_scanline)


@dataclass(frozen=True, slots=True)
class Event:
    """An ordered assignment or call, including writes of the same value.

    cpu-nmi-request has before=None and after equal to the requested delay.
    This is a call event, not the state of the CPU's pending NMI latch.
    """

    kind: str
    before: int | bool | None
    after: int | bool

    def __post_init__(self) -> None:
        if type(self.kind) is not str or not self.kind:
            raise ValueError("event kind must be a nonempty exact string")
        if self.before is not None and type(self.before) not in (int, bool):
            raise ValueError("event before must be int, bool, or None")
        if type(self.after) not in (int, bool):
            raise ValueError("event after must be int or bool")


@dataclass(frozen=True, slots=True)
class Transition:
    state: IrqState
    events: tuple[Event, ...]
    read_value: int | None = None

    def __post_init__(self) -> None:
        _state(self.state)
        if type(self.events) is not tuple or any(type(e) is not Event for e in self.events):
            raise ValueError("events must be an exact tuple of Event objects")
        if self.read_value is not None:
            _uint("read_value", self.read_value, 8)


def _state(state: IrqState) -> None:
    if type(state) is not IrqState:
        raise ValueError("state must be an exact IrqState")
    state.__post_init__()


def _flag(state: IrqState, value: bool) -> tuple[IrqState, tuple[Event, ...]]:
    flag = value and (state.h_enabled or state.v_enabled)
    events = [Event("irq-flag", state.irq_flag, flag)]
    new = replace(state, irq_flag=flag)
    if not flag:
        events.append(Event("ppu-source-clear", state.ppu_irq_source, False))
        new = replace(new, ppu_irq_source=False)
    return new, tuple(events)


def set_irq_flag(state: IrqState, value: bool) -> Transition:
    """SetIrqFlag: a true effective flag never asserts the CPU source."""
    _state(state)
    _bool("value", value)
    new, events = _flag(state, value)
    return Transition(new, events)


def _level(state: IrqState, h_clock: int) -> tuple[IrqState, tuple[Event, ...]]:
    if not state.irq_enabled_cache:
        return replace(state, irq_level=False), (Event("irq-level", state.irq_level, False),)
    level = ((not state.h_enabled or state.h_timer == state.h_counter)
             and (not state.v_enabled or state.v_timer == state.v_counter))
    events = []
    if not state.irq_level and level:
        events.append(Event("timer-match", False, True))
        pending = 3 if state.h_enabled and h_clock == 6 else 2
        events.append(Event("pending-arm", state.need_irq, pending))
        state = replace(state, need_irq=pending)
    events.append(Event("irq-level", state.irq_level, level))
    return replace(state, irq_level=level), tuple(events)


def update_irq_level(state: IrqState, h_clock: int) -> Transition:
    """Evaluate enables/timers at the supplied current H clock, without a tick."""
    _state(state)
    _uint("h_clock", h_clock, 16)
    new, events = _level(state, h_clock)
    return Transition(new, events)


def process_irq_counters(state: IrqState, context: TickContext) -> Transition:
    """Execute one complete source-order ProcessIrqCounters invocation.

    This deliberately accepts every uint16 H clock. The C++ body itself has
    no tick-phase assertion; whether Exec can call it there is the scheduler's
    separate obligation. Pending is consumed before H/V update and rearming.
    """
    _state(state)
    if type(context) is not TickContext:
        raise ValueError("context must be an exact TickContext")
    context.__post_init__()
    events: list[Event] = []
    if state.need_irq:
        pending = state.need_irq - 1
        events.append(Event("pending-consume", state.need_irq, pending))
        state = replace(state, need_irq=pending)
        if pending == 1:
            state, flag_events = _flag(state, True)
            events.extend(flag_events)
        elif pending == 0:
            source = state.irq_flag
            kind = "ppu-source-set" if source else "ppu-source-clear"
            events.append(Event(kind, state.ppu_irq_source, source))
            state = replace(state, ppu_irq_source=source)

    h = context.h_clock
    if h > 10 or h == 2:
        new_h = (state.h_counter + 1) & 0xFFFF
        events.append(Event("h-counter", state.h_counter, new_h))
        state = replace(state, h_counter=new_h)
    elif h in (6, 10):
        events.append(Event("h-counter", state.h_counter, 0))
        state = replace(state, h_counter=0)
    if h == 6:
        if context.scanline > 0 and not context.in_overclocked_scanline:
            new_v = (state.v_counter + 1) & 0xFFFF
            events.append(Event("v-counter", state.v_counter, new_v))
            state = replace(state, v_counter=new_v)
        if state.nmi_enabled and context.scanline == context.nmi_scanline:
            events.append(Event("cpu-nmi-request", None, 1))
    elif h == 2:
        if context.scanline == context.nmi_scanline:
            events.append(Event("nmi-flag", state.nmi_flag, True))
            state = replace(state, nmi_flag=True)
        elif context.scanline == 0:
            events.append(Event("nmi-flag", state.nmi_flag, False))
            events.append(Event("v-counter", state.v_counter, 0))
            state = replace(state, nmi_flag=False, v_counter=0)
    state, level_events = _level(state, h)
    events.extend(level_events)
    return Transition(state, tuple(events))


def write_timer(state: IrqState, address: int, value: int, h_clock: int) -> Transition:
    """Model only $4207-$420A writes and their immediate level evaluation."""
    _state(state)
    _uint("address", address, 16)
    _uint("value", value, 8)
    _uint("h_clock", h_clock, 16)
    if address not in (0x4207, 0x4208, 0x4209, 0x420A):
        raise RefusedPremise("only timer registers $4207-$420A are covered")
    horizontal = address in (0x4207, 0x4208)
    field = "h_timer" if horizontal else "v_timer"
    old = getattr(state, field)
    timer = ((old & 0x100) | value) if address in (0x4207, 0x4209) else ((old & 0xFF) | ((value & 1) << 8))
    state = replace(state, **{field: timer})
    state, events = _level(state, h_clock)
    return Transition(state, (Event(field.replace("_", "-"), old, timer),) + events)


def write_nmitimen(state: IrqState, value: int) -> Transition:
    """Model $4200 only when auto-joypad enable is unchanged.

    A changed bit 0 calls ProcessAutoJoypad and possibly controller strobe
    callbacks; their closure is outside this core and is explicitly refused.
    This operation does not call UpdateIrqLevel or clear pending IRQ count.
    """
    _state(state)
    _uint("value", value, 8)
    auto_joy = bool(value & 1)
    if auto_joy != state.auto_joy_enabled:
        raise RefusedPremise("changing auto-joypad enable requires callback closure")
    h_enabled = bool(value & 0x10)
    v_enabled = bool(value & 0x20)
    nmi_enabled = bool(value & 0x80)
    events = [Event("v-enabled", state.v_enabled, v_enabled),
              Event("h-enabled", state.h_enabled, h_enabled),
              Event("auto-joy-enabled", state.auto_joy_enabled, auto_joy),
              Event("irq-enabled-cache", state.irq_enabled_cache, h_enabled or v_enabled)]
    if state.nmi_flag and nmi_enabled and not state.nmi_enabled:
        events.append(Event("cpu-nmi-request", None, 2))
    events.append(Event("nmi-enabled", state.nmi_enabled, nmi_enabled))
    state = replace(state, h_enabled=h_enabled, v_enabled=v_enabled,
                    irq_enabled_cache=h_enabled or v_enabled, nmi_enabled=nmi_enabled)
    if not state.irq_enabled_cache:
        state, flag_events = _flag(state, False)
        events.extend(flag_events)
    return Transition(state, tuple(events))


def read_timeup(state: IrqState, open_bus: int) -> Transition:
    """$4211 returns the old flag before optional acknowledgement/clear."""
    _state(state)
    _uint("open_bus", open_bus, 8)
    value = (0x80 if state.irq_flag else 0) | (open_bus & 0x7F)
    events = ()
    if state.irq_flag and not state.need_irq:
        state, events = _flag(state, False)
    return Transition(state, events, value)
