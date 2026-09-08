#!/usr/bin/env python3
"""Read-only canonical IRQ CPU-write and symbolic save/restore contract.

This is a finite abstract interpreter of the already closed IRQ corpus. It
models ordinary CPU-addressed writes (including complete MVN destinations),
not DMA/HDMA transfers or another interrupt. Memory loads are unknown values;
only byte identity, explicit constants, widths, bank/direct-page selection,
typed stack frames and bounded block moves are interpreted. No ROM is emitted.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable

import audit_schala_package_interrupt_closure_v1 as prior

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-package-irq-memory-contract-v2"
SOURCE_PATH = "tools/audit_schala_package_irq_memory_contract_v2.py"
TEST_PATH = "tests/test_schala_package_irq_memory_contract_v2.py"
PRIOR_PATH = "references/schala_package_interrupt_closure_v1.json"
PRIOR_SOURCE_SHA256 = "727264d7c6e2de635eb6c32b53977a3f83464a85919c72e3bb2cf04f68d96ea9"
PRIOR_REFERENCE_SHA256 = "8ae0108d9412b404e461e4a17d95713e6a5b950308693efec69eef0c90bd2b04"
HELPER_CONTEXT_FILES = (
    ("asm/schala_package_helper_v2_stack.asm",
     "7ee849f04444567ae6a67f5642edc0ec0b7ef09f41c7ea5f2b1773e6373fdb5f"),
    ("references/schala_package_helper_v2_stack.json",
     "a095a1e18e97bd7f9746f3bc21affc90e30d76de10a34a2ffdff164e4b3c423f"),
    ("references/package_resolver_observation_v0.json",
     "a9685b37bb3cc13e61593730ff74fa5f0288b4dc00572c756559e388915ef1c1"),
)
CPU_SOURCE_FILES = (
    ("private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h",
     "dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f"),
    ("private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h",
     "9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd"),
)

Byte = int | str | None
Word = tuple[Byte, Byte]  # Low, high; None is unconstrained, not zero.


class ContractError(ValueError):
    """Refuse unsupported or contradictory semantics rather than infer safety."""


def word(value: int) -> Word:
    return value & 255, (value >> 8) & 255


def number(value: Word) -> int | None:
    return value[0] | value[1] << 8 if all(type(b) is int for b in value) else None


def load_word(value: Word, incoming: Word, narrow: bool) -> Word:
    return (value[0], incoming[1]) if narrow else value


def physical_wram(address: int) -> int | None:
    """Physical WRAM byte index for native SNES bus banks, otherwise None."""
    bank, offset = address >> 16, address & 65535
    if bank in (0x7E, 0x7F):
        return address - 0x7E0000
    if (bank <= 0x3F or 0x80 <= bank <= 0xBF) and offset < 0x2000:
        return offset
    return None


@dataclass(frozen=True)
class Saved:
    kind: str
    value: object


@dataclass(frozen=True)
class State:
    pc: int
    m8: bool
    x8: bool
    masked: bool
    a: Word
    x: Word
    y: Word
    d: Word
    dbr: Byte
    stack: tuple[Saved, ...]
    calls: tuple[tuple[int, str], ...]
    entry_m8: bool
    entry_x8: bool


def initial_state(entry: int, m8: bool, x8: bool) -> State:
    # Native hardware has already pushed PBR/PCH/PCL/P; saved status is opaque.
    hardware = tuple(Saved("hardware", v) for v in ("PBR", "PCH", "PCL", "P"))
    return State(entry, m8, x8, True, ("A", "B"),
                 ("XL", 0 if x8 else "XH"), ("YL", 0 if x8 else "YH"),
                 ("DL", "DH"), "DBR", hardware, (), m8, x8)


def decode(read: Callable[[int, int], bytes], state: State,
           bounds: tuple[tuple[int, int], ...]) -> tuple[int, bytes, str]:
    pc = state.pc
    if not any(start <= pc < end for start, end in bounds):
        raise ContractError(f"control leaves bounds at {pc:06X}")
    first = read(pc, 1)
    if type(first) is not bytes or len(first) != 1:
        raise ContractError("short opcode read")
    op = first[0]
    if op in prior.M_IMMEDIATES:
        name, length = prior.M_IMMEDIATES[op], 2 if state.m8 else 3
    elif op in prior.X_IMMEDIATES:
        name, length = prior.X_IMMEDIATES[op], 2 if state.x8 else 3
    elif op in prior.BRANCHES or op == 0x80:
        name, length = "branch", 2
    elif op in prior.FIXED:
        name, length = prior.FIXED[op]
    else:
        raise ContractError(f"unsupported opcode {op:02X} at {pc:06X}")
    if (pc & 65535) + length > 65536:
        raise ContractError("instruction crosses program-bank boundary")
    if not any(start <= pc and pc + length <= end for start, end in bounds):
        raise ContractError("instruction crosses declared extent")
    raw = read(pc, length)
    if type(raw) is not bytes or len(raw) != length:
        raise ContractError("short instruction read")
    return op, raw, name


def walk_memory(read: Callable[[int, int], bytes], *, entry: int = 0xD1FE97,
                bounds: tuple[tuple[int, int], ...] = prior.IRQ_BOUNDS,
                interrupted_sp: int = 0x06A4,
                protected: tuple[tuple[int, int], ...] = ((0x06A5, 0x06DE),),
                state_budget: int = 50000) -> dict:
    """Prove a conditional non-nested IRQ at one explicit physical stack SP.

    protected ranges use physical WRAM indices and half-open endpoints. The
    default covers the deepest hypothetical helper frame plus the five known
    caller bytes at the observed $06D8 resolver entry; it is no ownership grant.
    """
    if type(interrupted_sp) is not int or not 4 <= interrupted_sp < 0x2000:
        raise ContractError("interrupted stack requires native bank-zero WRAM")
    if type(state_budget) is not int or not 1 <= state_budget <= 100000:
        raise ContractError("invalid finite state budget")
    if any(type(a) is not int or type(b) is not int or not 0 <= a < b <= 0x20000
           for a, b in protected):
        raise ContractError("invalid physical protected range")
    if any(a <= byte < b for byte in range(interrupted_sp - 3, interrupted_sp + 1)
           for a, b in protected):
        raise ContractError("initial native hardware frame aliases protected bytes")
    queue = deque(initial_state(entry, m8, x8) for m8 in (False, True)
                  for x8 in (False, True))
    seen: set[State] = set()
    instructions: set[tuple[int, bool, bool]] = set()
    byte_owners: dict[int, int] = {}
    instruction_lengths: dict[int, int] = {}
    writes: set[tuple[int, str, tuple[int, ...], int, int, int]] = set()
    calls_seen: set[tuple[int, int, str]] = set()
    exits: set[tuple[int, bool, bool]] = set()
    peak = 4

    def check_alias(addresses: tuple[int, ...], depth: int) -> None:
        # Every byte already pushed is live at entry-SP-depth+1..entry-SP.
        live_first = interrupted_sp - depth + 1
        for address in addresses:
            physical = physical_wram(address)
            if physical is not None and (live_first <= physical <= interrupted_sp
                    or any(a <= physical < b for a, b in protected)):
                raise ContractError(f"ordinary CPU write aliases live/protected stack at {address:06X}")

    while queue:
        state = queue.popleft()
        if state in seen:
            continue
        seen.add(state)
        if len(seen) > state_budget:
            raise ContractError("finite state budget exceeded")
        pc = state.pc
        if pc in byte_owners and byte_owners[pc] != pc:
            raise ContractError("control enters another instruction's operand bytes")
        op, raw, name = decode(read, state, bounds)
        if pc in instruction_lengths and instruction_lengths[pc] != len(raw):
            raise ContractError("same PC has incompatible width-dependent instruction lengths")
        instruction_lengths[pc] = len(raw)
        for address in range(pc, pc + len(raw)):
            if address in byte_owners and byte_owners[address] != pc:
                raise ContractError("overlapping instruction byte ownership")
            byte_owners[address] = pc
        instructions.add((pc, state.m8, state.x8))
        a, x, y, d, dbr = state.a, state.x, state.y, state.d, state.dbr
        m8, x8, masked = state.m8, state.x8, state.masked
        stack, calls = list(state.stack), list(state.calls)
        next_pc = (pc & 0xFF0000) | ((pc + len(raw)) & 65535)
        destinations = [next_pc]

        def push(value: Word, width: int) -> None:
            stack.extend(Saved("data", b) for b in reversed(value[:width]))

        def pop(width: int) -> Word:
            if len(stack) < 4 + width or any(s.kind != "data" for s in stack[-width:]):
                raise ContractError(f"data pop consumes typed frame at {pc:06X}")
            result = tuple(stack.pop().value for _ in range(width))
            return (result[0], result[1] if width == 2 else None)

        def emit(addresses: tuple[int, ...], mode: str) -> None:
            check_alias(addresses, len(stack))
            writes.add((pc, mode, addresses, len(stack), int(m8), int(x8)))

        if op in (0xC2, 0xE2):
            set_bit = op == 0xE2
            if raw[1] & 0x20: m8 = set_bit
            if raw[1] & 0x10:
                x8 = set_bit
                if x8: x, y = (x[0], 0), (y[0], 0)
            if raw[1] & 4: masked = set_bit
        elif op == 0x08:
            stack.append(Saved("status", (m8, x8, masked)))
        elif op == 0x28:
            if len(stack) <= 4 or stack[-1].kind != "status":
                raise ContractError("PLP requires typed PHP")
            m8, x8, masked = stack.pop().value
            if x8: x, y = (x[0], 0), (y[0], 0)
        elif op in (0x48, 0xDA, 0x5A, 0x0B, 0x8B):
            value = {0x48: a, 0xDA: x, 0x5A: y, 0x0B: d, 0x8B: (dbr, None)}[op]
            width = (1 if m8 else 2) if op == 0x48 else (
                (1 if x8 else 2) if op in (0xDA, 0x5A) else 2 if op == 0x0B else 1)
            push(value, width)
        elif op in (0x68, 0xFA, 0x7A, 0x2B, 0xAB):
            width = (1 if m8 else 2) if op == 0x68 else (
                (1 if x8 else 2) if op in (0xFA, 0x7A) else 2 if op == 0x2B else 1)
            value = pop(width)
            if op == 0x68: a = load_word(value, a, m8)
            elif op == 0xFA: x = (value[0], 0) if x8 else value
            elif op == 0x7A: y = (value[0], 0) if x8 else value
            elif op == 0x2B: d = value
            else: dbr = value[0]
        elif op in (0x20, 0x22):
            target = int.from_bytes(raw[1:], "little")
            kind = "near" if op == 0x20 else "long"
            if op == 0x20: target |= pc & 0xFF0000
            stack.extend(Saved(kind, next_pc) for _ in range(2 if op == 0x20 else 3))
            calls.append((next_pc, kind))
            calls_seen.add((pc, target, kind))
            destinations = [target]
        elif op in (0x60, 0x6B):
            kind, count = ("near", 2) if op == 0x60 else ("long", 3)
            if not calls or calls[-1][1] != kind:
                raise ContractError("return lacks matching call kind")
            return_pc, _ = calls.pop()
            if kind == "near" and (return_pc >> 16) != (pc >> 16):
                raise ContractError("near return changes program bank")
            if stack[-count:] != [Saved(kind, return_pc)] * count:
                raise ContractError("return lacks exact typed frame")
            del stack[-count:]
            destinations = [return_pc]
        elif op == 0x40:
            expected = initial_state(entry, state.entry_m8, state.entry_x8)
            if calls or tuple(stack) != expected.stack:
                raise ContractError("RTI hardware frame changed or software frame remains")
            # The hardware RTI restores P and PC/PBR; X/Y highs are zero in X8.
            restored_x = (x[0], 0) if state.entry_x8 else x
            restored_y = (y[0], 0) if state.entry_x8 else y
            if (a, restored_x, restored_y, d, dbr) != (
                    expected.a, expected.x, expected.y, expected.d, expected.dbr):
                raise ContractError(f"symbolic register restoration fails at {pc:06X}")
            exits.add((pc, state.entry_m8, state.entry_x8))
            continue
        elif op == 0x4C:
            destinations = [(pc & 0xFF0000) | int.from_bytes(raw[1:], "little")]
        elif op in prior.BRANCHES or op == 0x80:
            target = (pc & 0xFF0000) | ((next_pc + int.from_bytes(raw[1:], "little", signed=True)) & 65535)
            destinations = [target] if op == 0x80 else [next_pc, target]
        elif op in (0xA9, 0xA2, 0xA0):
            value = word(int.from_bytes(raw[1:], "little"))
            if op == 0xA9: a = load_word(value, a, m8)
            elif op == 0xA2: x = (value[0], 0) if x8 else value
            else: y = (value[0], 0) if x8 else value
        elif op in (0xA5, 0xAD, 0xAF, 0xBF):
            a = load_word((None, None), a, m8)
        elif op == 0xA6:
            x = (None, 0) if x8 else (None, None)
        elif op == 0xAA:
            x = (a[0], 0) if x8 else a
        elif op == 0x5B:
            d = a
        elif op == 0x7B:
            a = d
        elif op == 0xEB:
            a = a[1], a[0]
        elif op == 0x54:
            count, destination = number(a), number(y)
            if count is None or destination is None or x8:
                raise ContractError("MVN requires known full A/Y and 16-bit indices")
            count += 1
            if count > 4096:
                raise ContractError("MVN extent exceeds bounded contract")
            dbr = raw[1]
            emit(tuple((dbr << 16) | ((destination + i) & 65535) for i in range(count)), "MVN")
            x_value = number(x)
            x = word(x_value + count) if x_value is not None else (None, None)
            y, a = word(destination + count), word(65535)
        elif op in (0x64, 0x85, 0xE6, 0x8C, 0x8D, 0x8E, 0x8F, 0x9C):
            width = (1 if x8 else 2) if op in (0x8C, 0x8E) else (1 if m8 else 2)
            if op in (0x64, 0x85, 0xE6):
                direct = number(d)
                if direct is None: raise ContractError("DP write has unknown D")
                base, mask, mode = (direct + raw[1]) & 65535, 65535, "direct"
            elif op == 0x8F:
                base, mask, mode = int.from_bytes(raw[1:], "little"), 0xFFFFFF, "long"
            else:
                if type(dbr) is not int: raise ContractError("absolute write has unknown DBR")
                base, mask, mode = (dbr << 16) | int.from_bytes(raw[1:], "little"), 0xFFFFFF, "absolute"
            addresses = tuple((base + i) & mask for i in range(width))
            if op == 0xE6 and width == 2: addresses = tuple(reversed(addresses))
            emit(addresses, mode)
        elif op in (0x0A, 0x4A, 0x1A, 0x09, 0x29, 0x49):
            # Exact constants and bitwise per-byte identities; unknown arithmetic
            # loses information. No branch is pruned from these values.
            width = 1 if m8 else 2
            value = number((a[0], 0) if m8 else a)
            mask = (1 << (8 * width)) - 1
            immediate = int.from_bytes(raw[1:], "little")
            if value is not None:
                result = {0x0A: lambda: value << 1, 0x4A: lambda: value >> 1,
                          0x1A: lambda: value + 1, 0x09: lambda: value | immediate,
                          0x29: lambda: value & immediate, 0x49: lambda: value ^ immediate}[op]() & mask
                a = load_word(word(result), a, m8)
            else:
                a = load_word((None, None), a, m8)
        elif op in (0x69, 0xE9, 0x6D, 0x7F):
            # Carry/decimal/value details are outside address and save identity.
            a = load_word((None, None), a, m8)
        elif op in (0x18, 0x89, 0xC9, 0xC0, 0xE0, 0xCD):
            pass  # Flag-only; all data-conditional branches remain included.
        else:
            raise ContractError(f"decoded instruction lacks explicit transfer: {name}")

        if not masked:
            raise ContractError("IRQ unmasking needs a nesting contract")
        if len(stack) > interrupted_sp:
            raise ContractError("stack pushes leave writable bank-zero WRAM")
        # Stack instructions must also avoid the caller's declared protected span.
        if any(lo <= physical < hi for physical in range(interrupted_sp - len(stack) + 1,
                                                           interrupted_sp + 1)
               for lo, hi in protected):
            raise ContractError("IRQ push aliases a protected byte")
        peak = max(peak, len(stack))
        queue.extend(State(target, m8, x8, masked, a, x, y, d, dbr, tuple(stack),
                           tuple(calls), state.entry_m8, state.entry_x8) for target in destinations)
    if {modes[1:] for modes in exits} != {(m8, x8) for m8 in (False, True) for x8 in (False, True)}:
        raise ContractError("every native entry-width context must reach a proved RTI")
    rows = [{"pc": f"${pc:06X}", "mode": mode,
             "bus_addresses_in_write_order": [f"${address:06X}" for address in addresses],
             "physical_wram_byte_indices": [p for address in addresses
                                             if (p := physical_wram(address)) is not None],
             "stack_depth_including_hardware": depth, "m8": bool(m8), "x8": bool(x8)}
            for pc, mode, addresses, depth, m8, x8 in sorted(writes)]
    physical = sorted({p for row in rows for p in row["physical_wram_byte_indices"]})
    return {"abstract_state_count": len(seen), "instruction_context_count": len(instructions),
            "unique_instruction_start_count": len({pc for pc, _, _ in instructions}),
            "maximum_depth_including_hardware": peak, "interrupted_sp": interrupted_sp,
            "lowest_sp": interrupted_sp - peak,
            "protected_physical_ranges": [list(r) for r in protected],
            "all_four_native_width_contexts_restore_symbolic_registers": True,
            "restored_registers": ["A/B", "X", "Y", "D", "DBR", "SP", "P", "PC/PBR"],
            "balanced_rti_contexts": [{"pc": f"${pc:06X}", "entry_m8": m8, "entry_x8": x8}
                                      for pc, m8, x8 in sorted(exits)],
            "ordinary_cpu_write_contexts": rows, "physical_wram_write_bytes": physical,
            "direct_calls": [{"site": f"${site:06X}", "target": f"${target:06X}", "kind": kind}
                             for site, target, kind in sorted(calls_seen)],
            "instruction_contexts": [{"pc": f"${pc:06X}", "m8": m8, "x8": x8}
                                     for pc, m8, x8 in sorted(instructions)]}


def identity(path: str) -> dict:
    data = (ROOT / path).read_bytes()
    return {"path": path, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def collect(rom_path: Path | None = None) -> dict:
    source_before = [identity(path) for path in (SOURCE_PATH, TEST_PATH,
                      "tools/audit_schala_package_interrupt_closure_v1.py", PRIOR_PATH)]
    if source_before[2]["sha256"] != PRIOR_SOURCE_SHA256:
        raise ContractError("accepted IRQ source drift")
    if source_before[3]["sha256"] != PRIOR_REFERENCE_SHA256:
        raise ContractError("accepted IRQ reference drift")
    helper_context = [identity(path) for path, _ in HELPER_CONTEXT_FILES]
    if any(expected is not None and item["sha256"] != expected
           for item, (_, expected) in zip(helper_context, HELPER_CONTEXT_FILES)):
        raise ContractError("accepted helper context drift")
    cpu_sources = [identity(path) for path, _ in CPU_SOURCE_FILES]
    if any(item["sha256"] != expected for item, (_, expected) in zip(cpu_sources, CPU_SOURCE_FILES)):
        raise ContractError("pinned CPU semantic source drift")
    rom = (rom_path or ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc").read_bytes()
    previous = prior.audit(rom)
    if previous != json.loads((ROOT / PRIOR_PATH).read_text(encoding="utf-8")):
        raise ContractError("accepted IRQ reference does not reproduce")
    def read(pc: int, count: int) -> bytes:
        if not 0xC00000 <= pc < pc + count <= 0x1000000:
            raise ContractError("canonical read outside exact ROM")
        return rom[pc - 0xC00000:pc - 0xC00000 + count]
    result = walk_memory(read)
    old = previous["irq_abstract_walk"]
    for key in ("instruction_context_count", "unique_instruction_start_count", "direct_calls"):
        if result[key] != old[key]: raise ContractError(f"graph coverage drift: {key}")
    if result["maximum_depth_including_hardware"] != old["maximum_depth_including_native_hardware_frame"]:
        raise ContractError("IRQ stack-depth drift")
    wram = set(result["physical_wram_write_bytes"])
    protected_outputs = ((0x80, 0x84), (0x9876, 0x987C), (0xA0B3, 0xA0B5),
                         (0x5DAC, 0x5DBD), (0x5DBD, 0x5DFD), (0x5D9B, 0x5D9C))
    intersections = [p for p in sorted(wram) if any(lo <= p < hi for lo, hi in protected_outputs)]
    if intersections: raise ContractError("ordinary CPU write reaches a package publication/control byte")
    result["checked_package_physical_ranges"] = [list(pair) for pair in protected_outputs]
    result["package_write_intersections"] = intersections
    combined_envelope = (0x06D8 - 52 - 35 + 1, 0x06D8 + 5 + 1)
    if any(combined_envelope[0] <= byte < combined_envelope[1] for byte in wram):
        raise ContractError("ordinary CPU write aliases combined hypothetical stack envelope")
    result["arithmetic_envelope_for_helper_depths_zero_through_52_and_irq_up_to_35"] = list(combined_envelope)
    result["combined_stack_envelope_write_intersections"] = []
    result["ordinary_cpu_hardware_write_addresses"] = sorted({address
        for row in result["ordinary_cpu_write_contexts"] for address in row["bus_addresses_in_write_order"]
        if 0x002000 <= int(address[1:], 16) <= 0x0043FF})
    after = [identity(item["path"]) for item in source_before + cpu_sources + helper_context]
    if after != source_before + cpu_sources + helper_context:
        raise ContractError("source changed during collection")
    return {"schema": SCHEMA, "evidence_level": "verified-static",
            "status": "conditional-cpu-write-and-symbolic-irq-register-contract",
            "canonical_rom": previous["canonical_rom"], "sources": source_before,
            "cpu_semantic_sources": cpu_sources, "canonical_spans": previous["spans"][:4],
            "helper_context_identity_only": helper_context,
            "planning_geometry": {"previously_observed_resolver_entry_sp": 0x06D8,
                                  "previously_proved_helper_additional_depth": 52,
                                  "chosen_hypothetical_irq_interrupted_sp": 0x06A4,
                                  "known_five_caller_bytes": [0x06D9, 0x06DE],
                                  "prior_native_traces_reexecuted_or_revalidated_here": False},
            "irq_contract": result,
            "premises": {"native_irq_hardware_frame_is_intact_at_entry": True,
                         "ordinary_bank_zero_stack_is_writable": True,
                         "dma_hdma_or_other_interrupts_do_not_modify_live_frames": True,
                         "all_data_condition_outcomes_are_included": True},
            "not_proved": {"dma_transfer_reads_or_writes": True, "dma_register_semantics": True,
                           "cpu_read_source_nonalias": True, "nmi_or_irq_nesting": True,
                           "termination_or_timing": True, "global_game_stack_floor": True,
                           "installed_handler_lifetime": True, "publication_read_visibility": True,
                           "production_hook_or_allocation": True, "native_runtime_execution": True}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path)
    args = parser.parse_args()
    try:
        sys.stdout.buffer.write((json.dumps(collect(args.rom), indent=2) + "\n").encode("utf-8"))
    except (OSError, ValueError, prior.ClosureError) as exc:
        parser.exit(1, f"IRQ memory contract refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
