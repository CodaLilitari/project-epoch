#!/usr/bin/env python3
"""Read-only configuration/destination proof for IRQ-requested channel-7 DMA.

This extends neither the frozen IRQ interpreter nor its claims. A separate
finite value projection follows the leaf field-DMA service; it checks the
configuration before every manual request, then derives the B-bus write set
from pinned emulator semantics. Source data, timing and other DMA stay open.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import argparse
import hashlib
import json
from pathlib import Path
import sys

import audit_schala_package_irq_memory_contract_v2 as irq

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-irq-requested-dma7-destination-contract-v3"
SOURCE = "tools/audit_schala_package_irq_dma7_contract_v3.py"
TESTS = "tests/test_schala_package_irq_dma7_contract_v3.py"
ENTRY, END = 0xFDE022, 0xFDE275
REQUESTS = (0xFDE076, 0xFDE0A2, 0xFDE0CE, 0xFDE0FA, 0xFDE126, 0xFDE152,
            0xFDE18B, 0xFDE1B7, 0xFDE1E3, 0xFDE20F, 0xFDE23B, 0xFDE267)
REGISTERS = (0x4370, 0x4371, 0x4375, 0x4376)
IRQ_REFERENCE = "references/schala_package_irq_memory_contract_v2.json"
IRQ_REFERENCE_SHA256 = "6a6cc3ac65cc2e9ae5d5fe92a313a7a716f31cdbc1256fc18d38a4731eaadc31"
PINS = (
    ("tools/audit_schala_package_irq_memory_contract_v2.py",
     "cd7ce6b278bcbce5b9293a813640b0cc3a90dc95fb0a655957e295363e00c1a6"),
    ("private/research/mesen_nmi_request_2_1_1/SnesDmaController.cpp",
     "f0bd85d5a3001cb3c847980922d6cf2aa19ef294a562a9c827f189328a1cfae6"),
    ("private/research/mesen_timing_api_2_1_1/SnesMemoryManager.cpp",
     "2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58"),
    ("private/research/mesen_timing_api_2_1_1/SnesPpu.cpp",
     "5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180"),
    ("private/research/mesen_irq_dma7_2_1_1/RegisterHandlerB.h",
     "709fb56c99d894650c4a0c55fbcf1c6714cac59fa85fe8518e486302d2519e20"),
    ("private/research/mesen_irq_dma7_2_1_1/RegisterHandlerB.cpp",
     "a3ebaecac6e6fe2d2bdfc04f072e77a9ba47251cdc5ae9d4b6fcdd4618af7ea7"),
    ("private/research/mesen_nmi_request_2_1_1/RegisterHandlerA.h",
     "782f34e6b68d6b247d37a5142f8071fad85b2dd13bd33a96d3f5bb085f176f3c"),
    (IRQ_REFERENCE, IRQ_REFERENCE_SHA256),
)
SEMANTIC_SPANS = (
    (PINS[1][0], 8, 11, "manual mode transfer offsets"),
    (PINS[1][0], 46, 98, "direction, source/destination bus and manual iteration"),
    (PINS[1][0], 408, 451, "manual enable and channel configuration decoding"),
    (PINS[1][0], 474, 489, "transfer-count low and high byte assignments"),
    (PINS[2][0], 55, 69, "WRAM and hardware-register bank mirrors"),
    (PINS[6][0], 55, 65, "CPU write routes to DMA after 16-bit register mask"),
    (PINS[2][0], 360, 383, "DMA destination write routing"),
    (PINS[5][0], 60, 85, "bus-B distinguishes WRAM port from PPU registers"),
    (PINS[3][0], 2046, 2073, "2118 and 2119 write VRAM when accessible"),
)


class DmaContractError(ValueError):
    pass


def require(ok, message):
    if not ok: raise DmaContractError(message)


def byte(value, label):
    require(type(value) is int and 0 <= value <= 255, "exact byte required: " + label)


def verify_irq_reference(previous):
    """Require the exact accepted prerequisite, not just a computed digest."""
    try:
        raw = (ROOT / IRQ_REFERENCE).read_bytes()
    except OSError as exc:
        raise DmaContractError("accepted IRQ reference unavailable") from exc
    require(hashlib.sha256(raw).hexdigest() == IRQ_REFERENCE_SHA256,
            "accepted IRQ reference byte identity differs")
    regenerated = (json.dumps(previous, indent=2) + "\n").encode("utf-8")
    require(regenerated == raw, "accepted IRQ reference no longer reproduces")
    return hashlib.sha256(regenerated).hexdigest()


def requested_destination(control, destination, request, size):
    """Source-derived narrow manual-DMA request; no actual transfer claim."""
    for value, label in ((control, "DMAP7"), (destination, "BBAD7"), (request, "MDMAEN")):
        byte(value, label)
    require(type(size) is int and size == 128, "exact 128-byte request required")
    require(control == 0x41 and destination == 0x18 and request == 0x80,
            "request differs from reviewed forward mode-1 channel-7 configuration")
    # Mesen's mode1 transfer offsets repeat 0,1,0,1. Direction bit7 is clear;
    # bit6 selects HDMA indirect addressing, not manual-DMA direction.
    addresses = tuple(0x2100 | (destination + (i & 1)) for i in range(size))
    return {"channel": 7, "control": control, "bbad": destination,
            "request_mask": request, "byte_count": size,
            "direction": "A-to-B", "transfer_mode": 1,
            "unique_bus_write_addresses": sorted(set(addresses)),
            "ordered_bus_write_addresses_sha256": hashlib.sha256(
                b"".join(a.to_bytes(2, "little") for a in addresses)).hexdigest(),
            "contains_wram_port_2180": 0x2180 in addresses,
            "actual_transfer_completed": False}


@dataclass(frozen=True)
class State:
    pc: int
    m8: bool
    x8: bool
    masked: bool
    a: irq.Word
    x: irq.Word
    y: irq.Word
    d: irq.Word
    dbr: irq.Byte
    stack: tuple[irq.Saved, ...]
    # value and last ordinary CPU writer for DMAP7, BBAD7, DAS7L, DAS7H.
    registers: tuple[tuple[irq.Byte, int | None], ...]


def project(read, *, entry=ENTRY, end=END, budget=30000):
    require(type(entry) is int and type(end) is int and 0xC00000 <= entry < end <= 0x1000000,
            "exact canonical-like source extent")
    require(type(budget) is int and 1 <= budget <= 100000, "finite budget")
    frame = (irq.Saved("long", "caller"),) * 3
    start = State(entry, True, False, True, ("A", "B"), ("XL", "XH"), ("YL", "YH"),
                  ("DL", "DH"), "DBR", frame, ((None, None),) * 4)
    queue, seen = deque([start]), set()
    owners, lengths, contexts, requests, writes, exits = {}, {}, set(), set(), set(), set()
    while queue:
        state = queue.popleft()
        if state in seen: continue
        seen.add(state); require(len(seen) <= budget, "value state budget exceeded")
        pc = state.pc
        require(pc not in owners or owners[pc] == pc, "control enters operand")
        op, raw, _ = irq.decode(read, state, ((entry, end),))
        require(pc not in lengths or lengths[pc] == len(raw), "incompatible instruction widths")
        lengths[pc] = len(raw)
        for address in range(pc, pc + len(raw)):
            require(address not in owners or owners[address] == pc, "overlapping instruction ownership")
            owners[address] = pc
        contexts.add((pc, state.m8, state.x8))
        a, x, y, d, dbr = state.a, state.x, state.y, state.d, state.dbr
        m8, x8, masked = state.m8, state.x8, state.masked
        stack, registers = list(state.stack), list(state.registers)
        next_pc = (pc & 0xFF0000) | ((pc + len(raw)) & 65535)
        successors = [next_pc]

        def push(value, width):
            stack.extend(irq.Saved("data", v) for v in reversed(value[:width]))

        def pop(width):
            require(len(stack) >= 3 + width and all(s.kind == "data" for s in stack[-width:]),
                    "data pull consumes typed frame")
            values = tuple(stack.pop().value for _ in range(width))
            return values[0], values[1] if width == 2 else None

        if op in (0xC2, 0xE2):
            on = op == 0xE2
            if raw[1] & 0x20: m8 = on
            if raw[1] & 0x10:
                x8 = on
                if x8: x, y = (x[0], 0), (y[0], 0)
            if raw[1] & 4: masked = on
        elif op == 0x08:
            stack.append(irq.Saved("status", (m8, x8, masked)))
        elif op == 0x28:
            require(stack and stack[-1].kind == "status", "typed PHP required")
            m8, x8, masked = stack.pop().value
            if x8: x, y = (x[0], 0), (y[0], 0)
        elif op in (0x48, 0xDA, 0x0B, 0x8B):
            value = {0x48: a, 0xDA: x, 0x0B: d, 0x8B: (dbr, None)}[op]
            width = (1 if m8 else 2) if op == 0x48 else (
                (1 if x8 else 2) if op == 0xDA else 2 if op == 0x0B else 1)
            push(value, width)
        elif op in (0xAB, 0x2B):
            value = pop(1 if op == 0xAB else 2)
            if op == 0xAB: dbr = value[0]
            else: d = value
        elif op in (0xA9, 0xA2, 0xA0):
            value = irq.word(int.from_bytes(raw[1:], "little"))
            if op == 0xA9: a = irq.load_word(value, a, m8)
            elif op == 0xA2: x = (value[0], 0) if x8 else value
            else: y = (value[0], 0) if x8 else value
        elif op in (0xA5, 0xAF, 0xAD, 0xBF):
            a = irq.load_word((None, None), a, m8)
        elif op == 0xA6:
            x = (None, 0) if x8 else (None, None)
        elif op == 0xAA:
            x = (a[0], 0) if x8 else a
        elif op == 0xEB:
            a = a[1], a[0]
        elif op in (0x29, 0x4A, 0x6D, 0x7F, 0x69):
            a = irq.load_word((None, None), a, m8)
        elif op == 0x18:
            pass
        elif op in (0x85, 0xE6, 0x8C, 0x8D, 0x8E, 0x9C):
            width = (1 if x8 else 2) if op in (0x8C, 0x8E) else (1 if m8 else 2)
            if op in (0x85, 0xE6):
                base_d = irq.number(d); require(base_d is not None, "known D before direct write")
                address, mask = (base_d + raw[1]) & 65535, 65535
            else:
                require(type(dbr) is int, "known DBR before absolute write")
                address, mask = (dbr << 16) | int.from_bytes(raw[1:], "little"), 0xFFFFFF
            value = {0x85: a, 0xE6: (None, None), 0x8C: y, 0x8D: a,
                     0x8E: x, 0x9C: (0, 0)}[op]
            ordered = list(range(width))
            if op == 0xE6 and width == 2: ordered.reverse()
            for i in ordered:
                bus = (address + i) & mask
                writes.add((pc, bus, width, bool(m8), bool(x8)))
                bank, offset = bus >> 16, bus & 65535
                hardware_mirror = (bank <= 0x3F or 0x80 <= bank <= 0xBF) and (
                    0x2000 <= offset <= 0x2FFF or 0x4000 <= offset <= 0x4FFF)
                require(not hardware_mirror or bank == 0,
                        "unmodeled nonzero-bank hardware register mirror")
                if bus in REGISTERS:
                    registers[REGISTERS.index(bus)] = value[i], pc
                elif bus == 0x420B:
                    require(width == 1 and op == 0x8C and x8, "request must be exact 8-bit STY")
                    control, dest, size_low, size_high = [r[0] for r in registers]
                    require(all(type(b) is int for b in (size_low, size_high)), "size bytes not established")
                    size = size_low | size_high << 8
                    requested_destination(control, dest, value[i], size)
                    requests.add((pc, control, dest, value[i], size, tuple(r[1] for r in registers)))
                    # A request may be delayed or interrupted. Do not assume its
                    # hardware size counter's post-transfer state or completion.
                    registers[2:] = [(None, None), (None, None)]
                elif 0x4300 <= bus <= 0x437F and bus not in (0x4372, 0x4373, 0x4374):
                    raise DmaContractError("write to unreviewed DMA configuration byte")
                elif bus == 0x420C:
                    raise DmaContractError("service writes HDMA enable; separate interference contract needed")
        elif op == 0x4C:
            successors = [(pc & 0xFF0000) | int.from_bytes(raw[1:], "little")]
        elif op in irq.prior.BRANCHES or op == 0x80:
            target = (pc & 0xFF0000) | ((next_pc + int.from_bytes(raw[1:], "little", signed=True)) & 65535)
            successors = [target] if op == 0x80 else [next_pc, target]
        elif op == 0x6B:
            require(tuple(stack) == frame and m8 and not x8 and masked, "exact original long frame/status at return")
            require(d == start.d and dbr == start.dbr, "saved D/DBR identities at return")
            exits.add(pc); continue
        else:
            raise DmaContractError(f"unsupported service value effect {op:02X} at {pc:06X}")
        require(masked, "IRQ unmasking")
        require(len(stack) <= 32, "service stack budget")
        queue.extend(State(target, m8, x8, masked, a, x, y, d, dbr, tuple(stack), tuple(registers))
                     for target in successors)
    require(exits, "no balanced service return")
    rows = []
    for pc, control, destination, request, size, writers in sorted(requests):
        row = requested_destination(control, destination, request, size)
        row.update({"request_site": f"${pc:06X}",
                    "last_cpu_configuration_writers": {f"${r:06X}": f"${p:06X}"
                                                       for r, p in zip(REGISTERS, writers)}})
        rows.append(row)
    return {"abstract_states": len(seen), "entry": f"${entry:06X}",
            "entry_width_contract": {"native": True, "m8": True, "x8": False, "irq_masked": True},
            "incoming_a_x_y_d_dbr_values_are_symbolic": True,
            "contexts": [{"pc": f"${pc:06X}", "m8": m, "x8": x} for pc, m, x in sorted(contexts)],
            "ordinary_cpu_write_contexts": [{"pc": f"${pc:06X}", "bus_address": f"${bus:06X}",
                                             "instruction_width": width, "m8": m, "x8": x}
                                            for pc, bus, width, m, x in sorted(writes)],
            "request_contracts": rows, "return_sites": [f"${pc:06X}" for pc in sorted(exits)],
            "all_branches_follow_both_edges": True, "memory_read_values": "unknown",
            "dma_source_bank_offset_data_validity_proved": False,
            "post_request_size_and_completion_assumed": False}


def collect():
    sources = [irq.identity(path) for path, _ in PINS]
    require(all(row["sha256"] == digest for row, (_, digest) in zip(sources, PINS)), "pinned source drift")
    own = [irq.identity(path) for path in (SOURCE, TESTS)]
    semantic_spans = []
    for path, first, last, purpose in SEMANTIC_SPANS:
        lines = (ROOT/path).read_bytes().splitlines(keepends=True)
        require(0 < first <= last <= len(lines), "semantic source line extent")
        excerpt = b"".join(lines[first-1:last])
        semantic_spans.append({"path":path,"first_line":first,"last_line_inclusive":last,
                               "size":len(excerpt),"sha256":hashlib.sha256(excerpt).hexdigest(),
                               "role":purpose,"interpretation":"reviewer-derived source semantics"})
    previous = irq.collect()
    previous_sha256 = verify_irq_reference(previous)
    rom = (ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc").read_bytes()
    require(len(rom) == 0x400000 and hashlib.sha256(rom).hexdigest() == irq.prior.ROM_SHA256, "canonical ROM")
    def read(pc, count):
        require(type(pc) is int and type(count) is int and count > 0
                and 0xC00000 <= pc < pc + count <= 0x1000000, "canonical source bounds")
        return rom[pc - 0xC00000:pc - 0xC00000 + count]
    result = project(read)
    expected_contexts = [row for row in previous["irq_contract"]["instruction_contexts"]
                         if ENTRY <= int(row["pc"][1:], 16) < END]
    require(result["contexts"] == expected_contexts, "exact prior field-service instruction contexts differ")
    expected_writes = sorted({(row["pc"], bus, len(row["bus_addresses_in_write_order"]), row["m8"], row["x8"])
        for row in previous["irq_contract"]["ordinary_cpu_write_contexts"]
        if ENTRY <= int(row["pc"][1:], 16) < END for bus in row["bus_addresses_in_write_order"]})
    current_writes = sorted((row["pc"], row["bus_address"], row["instruction_width"], row["m8"], row["x8"])
        for row in result["ordinary_cpu_write_contexts"])
    require(current_writes == expected_writes, "exact prior field-service ordinary CPU writes differ")
    require([int(row["request_site"][1:], 16) for row in result["request_contracts"]] == list(REQUESTS),
            "exact twelve request sites or per-site configuration differs")
    require(result["return_sites"] == ["$FDE15F", "$FDE274"], "exact two service return sites")
    for row, site in zip(result["request_contracts"], REQUESTS):
        require(row["last_cpu_configuration_writers"] == {
            "$004370": "$FDE030", "$004371": "$FDE035",
            "$004375": f"${site-3:06X}", "$004376": f"${site-6:06X}"},
            "exact dominating control/BBAD/size writers differ")
    inherited = previous["sources"] + previous["cpu_semantic_sources"] + previous["helper_context_identity_only"]
    require(sources == [irq.identity(path) for path, _ in PINS]
            and own == [irq.identity(path) for path in (SOURCE, TESTS)]
            and inherited == [irq.identity(row["path"]) for row in inherited], "source changed during audit")
    return {"schema": SCHEMA, "evidence_level": "verified-static",
            "canonical_rom": previous["canonical_rom"], "sources": sources, "owned_sources": own,
            "reviewed_primary_semantic_spans": semantic_spans,
            "reused_irq_contract_sources": inherited,
            "reproduced_irq_memory_contract_sha256": previous_sha256,
            "field_service_source": {"start": f"${ENTRY:06X}", "end_exclusive": f"${END:06X}",
                                     "sha256": hashlib.sha256(read(ENTRY, END-ENTRY)).hexdigest()},
            "service": result,
            "source_interpretation": {"requested_writes_are_only_2118_2119": True,
                                      "register_handler_routes_these_to_ppu": True,
                                      "ppu_destination_is_vram_or_no_write_when_inaccessible": True,
                                      "requested_destination_is_wram": False},
            "premises": ["Exact native M1/X0/I1 entry from the reproduced IRQ graph.",
                         "Ordinary writable typed stack; no nonstack alias changes saved cells.",
                         "No other actor changes the DMA channel configuration while the request executes.",
                         "No debugger or cheat callback changes modeled register writes or memory routing."],
            "open": ["DMA source-bank/offset bytes and read side effects", "graphics and PPU correctness",
                     "other active or pending DMA/HDMA", "NMI/IRQ interleaving and nesting",
                     "request completion, elapsed time and raster phase", "whole-game stack ownership",
                     "production hook, allocation, selector binding or eighth playable PC"],
            "native_execution": False, "rom_or_patch_emitted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.parse_args()
    sys.stdout.buffer.write((json.dumps(collect(), indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
