"""Conditional DMA/HDMA bus-address domains; no emulator or game proof.

This original model reads no ROM, table data, trace or process. Fixed channel
configuration and the mapping premises are caller hypotheses, not certificates.
Unknown table bytes are abstracted by supersets: a future indirect reload can
select any uint16 payload pointer; table pointers stay in their source bank.
The unions have no ordering, value, clock, handler-completion or reachability
claim. In particular an IRQ candidate is a possibly dispatched address, not an
observed acknowledgment, register mutation, CPU acceptance or handler entry.

Mesen source revision 137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1. See citations.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


SOURCE_REVISION = "137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1"
_BASE = f"https://github.com/SourMesen/Mesen2/blob/{SOURCE_REVISION}/Core/SNES/"
SOURCE_CITATIONS = {
    "types": _BASE + "DmaControllerTypes.h#L5-L28",
    "offsets_and_copy": _BASE + "SnesDmaController.cpp#L8-L65",
    "manual": _BASE + "SnesDmaController.cpp#L68-L102",
    "initialization": _BASE + "SnesDmaController.cpp#L104-L172",
    "payload": _BASE + "SnesDmaController.cpp#L174-L204",
    "service": _BASE + "SnesDmaController.cpp#L230-L323",
    "base_mapping_then_cartridge": _BASE + "SnesMemoryManager.cpp#L57-L70",
    "read_dispatch": _BASE + "SnesMemoryManager.cpp#L293-L328",
    "write_dispatch": _BASE + "SnesMemoryManager.cpp#L360-L386",
    "work_ram_query": _BASE + "SnesMemoryManager.cpp#L462-L466",
    "register_a_dispatch": _BASE + "RegisterHandlerA.h#L23-L63",
}

# The addition in the C++ call is integer-promoted, not uint8 arithmetic.
# OR with 0x2100 absorbs bit 8 for this 0..258 range; b_address preserves that.
TRANSFER_OFFSETS = (
    (0, 0, 0, 0), (0, 1, 0, 1), (0, 0, 0, 0), (0, 0, 1, 1),
    (0, 1, 2, 3), (0, 1, 0, 1), (0, 0, 0, 0), (0, 0, 1, 1),
)
TRANSFER_BYTE_COUNTS = (1, 2, 2, 4, 4, 4, 2, 4)
MAX_SERVICES = 65536
IRQ_WRITE_REGISTERS = (0x4200, 0x4207, 0x4208, 0x4209, 0x420A)


class RefusedPremise(ValueError):
    """An unknown or false premise lies outside this conditional model."""


def _uint(name: str, value: int, bits: int) -> None:
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f"{name} must be an exact uint{bits} integer")


def _bool(name: str, value: bool) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be an exact bool")


@dataclass(frozen=True, slots=True)
class ChannelConfig:
    source_bank: int
    source_address: int
    transfer_size: int
    dest_address: int
    transfer_mode: int
    invert_direction: bool
    decrement: bool
    fixed_transfer: bool
    dma_active: bool
    hdma_bank: int
    hdma_table_address: int
    hdma_line_counter: int
    do_transfer: bool
    hdma_finished: bool
    hdma_indirect: bool
    hdma_enabled: bool

    def __post_init__(self) -> None:
        words = {"source_address", "transfer_size", "hdma_table_address"}
        bytes_ = {"source_bank", "dest_address", "transfer_mode", "hdma_bank", "hdma_line_counter"}
        for field in fields(self):
            name, value = field.name, getattr(self, field.name)
            if name in words:
                _uint(name, value, 16)
            elif name in bytes_:
                _uint(name, value, 8)
            else:
                _bool(name, value)
        if self.transfer_mode >= 8:
            raise ValueError("transfer_mode must be in the source table domain 0..7")


@dataclass(frozen=True, slots=True)
class DomainPremises:
    # Exact RegisterHandlerA aliases after cartridge initialization are NOT
    # established by the base registrations at MemoryManager.cpp:62-63.
    base_register_a_aliases_exact: bool
    fixed_channel_configuration: bool
    no_external_pointer_or_lifecycle_mutation: bool
    no_nested_dma_hdma_service: bool
    no_reset_or_state_load: bool

    def require(self) -> None:
        for field in fields(self):
            if getattr(self, field.name) is not True:
                raise RefusedPremise(f"explicit true hypothesis required: {field.name}")


@dataclass(frozen=True, slots=True)
class AddressDomain:
    """A bank and sorted disjoint closed uint16 intervals; no bank carry."""

    bank: int
    intervals: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        _uint("bank", self.bank, 8)
        if type(self.intervals) is not tuple:
            raise ValueError("intervals must be an exact tuple")
        previous = -2
        for interval in self.intervals:
            if type(interval) is not tuple or len(interval) != 2:
                raise ValueError("each interval must be an exact pair tuple")
            lo, hi = interval
            _uint("lo", lo, 16)
            _uint("hi", hi, 16)
            if lo > hi or lo <= previous + 1:
                raise ValueError("intervals must be ordered, disjoint and nonadjacent")
            previous = hi

    def contains(self, address: int) -> bool:
        _uint("address", address, 24)
        return address >> 16 == self.bank and any(
            lo <= (address & 0xFFFF) <= hi for lo, hi in self.intervals
        )

    @property
    def cardinality(self) -> int:
        return sum(hi - lo + 1 for lo, hi in self.intervals)

    def to_dict(self) -> dict:
        return {"bank": self.bank, "intervals_inclusive": [list(x) for x in self.intervals],
                "address_count": self.cardinality}


def circular_domain(bank: int, start: int, count: int, step: int = 1) -> AddressDomain:
    _uint("bank", bank, 8)
    _uint("start", start, 16)
    if type(count) is not int or not 0 <= count <= 4 * MAX_SERVICES + 4:
        raise ValueError("count exceeds the declared address-domain bound")
    if type(step) is not int or step not in (-1, 0, 1):
        raise ValueError("step must be exact -1, 0 or 1")
    if count == 0:
        return AddressDomain(bank, ())
    if step == 0:
        return AddressDomain(bank, ((start, start),))
    if count >= 65536:
        return AddressDomain(bank, ((0, 65535),))
    lo = (start - count + 1) & 0xFFFF if step == -1 else start
    hi = lo + count - 1
    intervals = ((lo, hi),) if hi <= 65535 else ((0, hi & 0xFFFF), (lo, 65535))
    return AddressDomain(bank, intervals)


def _point_domain(bank: int, offsets: tuple[int, ...]) -> AddressDomain:
    values = sorted(set(offsets))
    spans: list[tuple[int, int]] = []
    for value in values:
        if spans and value == spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], value)
        else:
            spans.append((value, value))
    return AddressDomain(bank, tuple(spans))


def b_address(dest_address: int, transfer_offset: int) -> int:
    _uint("dest_address", dest_address, 8)
    if type(transfer_offset) is not int or not 0 <= transfer_offset <= 3:
        raise ValueError("transfer_offset must be exact 0..3")
    return 0x2100 | (dest_address + transfer_offset)


@dataclass(frozen=True, slots=True)
class BusAccess:
    bus: str
    operation: str
    address: int


def copy_bus_accesses(address_a: int, address_b: int, invert_direction: bool,
                     *, a_is_wram: bool) -> tuple[BusAccess, ...]:
    """Exact logical ReadDma/WriteDma call order under known IsWorkRam result.

    This models neither the four-clock pre-dispatch callbacks nor handlers.
    In the reverse WRAM/$2180 exception, the write has constant value $FF;
    ordinary copied values remain unmodeled.
    """
    _uint("address_a", address_a, 24)
    _uint("address_b", address_b, 16)
    _bool("invert_direction", invert_direction)
    _bool("a_is_wram", a_is_wram)
    if not 0x2100 <= address_b <= 0x21FF:
        raise ValueError("address_b must be in the derived B-bus domain")
    collision = a_is_wram and address_b == 0x2180
    if invert_direction:
        write = BusAccess("A", "write", address_a)
        return (write,) if collision else (BusAccess("B", "read", address_b), write)
    return () if collision else (BusAccess("A", "read", address_a),
                                 BusAccess("B", "write", address_b))


@dataclass(frozen=True, slots=True)
class BusDomain:
    role: str
    bus: str
    operation: str
    addresses: AddressDomain

    def contains(self, access: BusAccess) -> bool:
        return (access.bus == self.bus and access.operation == self.operation
                and self.addresses.contains(access.address))

    def to_dict(self) -> dict:
        return {"role": self.role, "bus": self.bus, "operation": self.operation,
                "addresses": self.addresses.to_dict()}


def _base_a_bank(bank: int) -> bool:
    return bank <= 0x3F or 0x80 <= bank <= 0xBF


def dispatch_route(address: int, bus: str, operation: str,
                   premises: DomainPremises) -> str:
    """Conditional memory-manager/handler-A route, without side-effect closure."""
    _uint("address", address, 24)
    if type(bus) is not str or bus not in ("A", "B"):
        raise ValueError("bus must be exact A or B")
    if type(operation) is not str or operation not in ("read", "write"):
        raise ValueError("operation must be exact read or write")
    _require_premises(premises)
    bank, reg = address >> 16, address & 0xFFFF
    if not _base_a_bank(bank) or not 0x4000 <= reg <= 0x4FFF:
        # No promise about ROM, RAM, open bus, other handler aliases or their
        # own callback behavior follows from excluding RegisterHandlerA.
        return "outside-assumed-register-a-map"
    if reg in (0x420B, 0x420C) or 0x4300 <= reg <= 0x437F:
        return "dma-register-open-bus" if operation == "read" else "dma-register-write-suppressed"
    if reg == 0x4016 or (reg == 0x4017 and operation == "read"):
        return "control-handler"
    if reg >= 0x4300:
        return "dma-controller-handler"
    return "internal-register-handler"


@dataclass(frozen=True, slots=True)
class DomainReport:
    kind: str
    domains: tuple[BusDomain, ...]
    service_bound: int | None
    includes_initialization: bool

    def contains(self, access: BusAccess) -> bool:
        return any(domain.contains(access) for domain in self.domains)

    def irq_candidates(self) -> dict:
        result: dict[str, list[dict]] = {"timeup_reads": [], "irq_register_writes": []}
        for domain in self.domains:
            if not _base_a_bank(domain.addresses.bank):
                continue
            registers = (0x4211,) if domain.operation == "read" else IRQ_WRITE_REGISTERS
            key = "timeup_reads" if domain.operation == "read" else "irq_register_writes"
            for register in registers:
                address = (domain.addresses.bank << 16) | register
                if domain.addresses.contains(address):
                    result[key].append({"role": domain.role, "bus": domain.bus,
                                        "address": address, "register": register})
        return result

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "evidence_level": "conditional-address-domain-overapproximation",
            "source_revision": SOURCE_REVISION, "service_bound": self.service_bound,
            "includes_initialization": self.includes_initialization,
            "domains": [domain.to_dict() for domain in self.domains],
            "irq_candidates": self.irq_candidates(),
            "hypotheses_verified": False, "mapping_identity_proved": False,
            "handler_side_effects_closed": False, "callback_closure_proved": False,
            "game_duration_bound": False, "runtime_observation": False,
            "production_approval": False,
            "limits": [
                "Address unions can include infeasible paths and suppressed WRAM/$2180 payload calls.",
                "Table contents may vary independently at every read; table reads are always A-bus reads.",
                "Exact RegisterHandlerA aliases after cartridge initialization are an explicit hypothesis.",
                "Outside RegisterHandlerA does not classify another memory handler or its effects.",
                "Callback state mutation, reset/load and nested DMA/HDMA service are excluded hypotheses.",
                "No order, values, timing, completion or IRQ acceptance follows from these unions.",
            ],
        }


def _require_premises(premises: DomainPremises) -> None:
    if type(premises) is not DomainPremises:
        raise RefusedPremise("an exact DomainPremises instance is required")
    premises.require()


def _require(channel: ChannelConfig, premises: DomainPremises) -> None:
    if type(channel) is not ChannelConfig:
        raise ValueError("an exact ChannelConfig instance is required")
    _require_premises(premises)


def _payload_domains(channel: ChannelConfig, a_domain: AddressDomain,
                     count: int, role: str) -> tuple[BusDomain, ...]:
    if not count:
        return ()
    offsets = TRANSFER_OFFSETS[channel.transfer_mode][:min(count, 4)]
    b_domain = _point_domain(0, tuple(b_address(channel.dest_address, x) for x in offsets))
    operation_a, operation_b = ("write", "read") if channel.invert_direction else ("read", "write")
    return (BusDomain(role, "A", operation_a, a_domain),
            BusDomain("b-payload", "B", operation_b, b_domain))


def dma_domains(channel: ChannelConfig, premises: DomainPremises) -> DomainReport:
    """One uninterrupted RunDma call; zero transfer size means 65536 bytes.

    The source invokes ProcessPendingTransfers before and within its loop.
    Excluding nested DMA/HDMA service is a substantial unproved hypothesis.
    """
    _require(channel, premises)
    if not channel.dma_active:
        return DomainReport("manual-dma", (), None, False)
    count = channel.transfer_size or 65536
    step = 0 if channel.fixed_transfer else (-1 if channel.decrement else 1)
    domain = circular_domain(channel.source_bank, channel.source_address, count, step)
    return DomainReport("manual-dma", _payload_domains(channel, domain, count, "manual-payload"),
                        None, False)


def hdma_domains(channel: ChannelConfig, max_services: int, premises: DomainPremises,
                 *, include_init: bool = False) -> DomainReport:
    """At most max_services future calls, with optional preceding initialization.

    The service count is supplied by the caller (0..65536), never inferred
    from raster time or a helper envelope. No subsequent frame init is included.
    With unknown table bytes this is a conservative finite set, not an exact
    enumerator. Even a zero-transfer service reads its current table counter.
    """
    _require(channel, premises)
    _bool("include_init", include_init)
    if type(max_services) is not int or not 0 <= max_services <= MAX_SERVICES:
        raise ValueError("max_services must be exact 0..65536")
    if not channel.hdma_enabled or (channel.hdma_finished and not include_init):
        return DomainReport("hdma", (), max_services, include_init)
    if not max_services and not include_init:
        return DomainReport("hdma", (), max_services, include_init)

    size = TRANSFER_BYTE_COUNTS[channel.transfer_mode]
    start = channel.source_address if include_init else channel.hdma_table_address
    init_advance = (3 if channel.hdma_indirect else 1) if include_init else 0
    stride = 3 if channel.hdma_indirect else size + 1
    # Last service reads a counter, and a reload can read two more table
    # bytes. Direct payload moves the same table pointer by <=size first.
    extent = min(65536, init_advance + max_services * stride)
    domains: list[BusDomain] = []
    if extent:
        domains.append(BusDomain("hdma-table-and-indirect-address", "A", "read",
                                 circular_domain(channel.source_bank, start, extent)))

    # Current DoTransfer is exact for the first service. Initialization sets
    # it true, though an arbitrary zero table byte may finish the channel.
    payload_possible = max_services > 0 and (include_init or channel.do_transfer or max_services > 1)
    if payload_possible:
        if channel.hdma_indirect:
            # A fresh initialization or any possible later reload may choose
            # any pointer. For one existing service use its observed pointer.
            if include_init or max_services > 1:
                a_domain = circular_domain(channel.hdma_bank, 0, 65536)
            else:
                a_domain = circular_domain(channel.hdma_bank, channel.transfer_size, size)
        else:
            # Includes starts belonging only to counter reads; this intentional
            # overapproximation remains sound even with reverse table writes.
            a_domain = circular_domain(channel.source_bank, start, extent)
        domains.extend(_payload_domains(channel, a_domain, size, "hdma-payload"))
    return DomainReport("hdma", tuple(domains), max_services, include_init)
