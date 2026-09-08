#!/usr/bin/env python3
"""Read-only, metadata-only normal battle IRQ closure and stack audit.

This is deliberately a small, fail-closed abstract CPU walker, not a general
65816 emulator or a whole-game interrupt proof. It follows both outcomes of
conditional branches, tracks M/X/I and typed saved status bytes, and accounts
for the real near/long call frames and temporary pushes. Data conditions and
timing are not modeled. NMI closure, nesting and DMA source ownership remain
separate obligations. No game bytes are emitted.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
ROM_SHA256 = "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
SCHEMA = "project-epoch-package-interrupt-closure-v1"
SPANS = (
    ("irq_and_direct_services", 0xD1FE4C, 0xD1FEF4,
     "f86e45704580f7a8c879ff075ee2c58543913da28a10eb445a53d56bafa77e1c"),
    ("irq_display_table_loader", 0xCEEE6E, 0xCEEF11,
     "8456e61e3b3230c2c98593561fb66e7a675df5b58fbd5e04d56dd45fdcf0e177"),
    ("irq_field_vram_dma_service", 0xFDE022, 0xFDE275,
     "710683e30da8a2b55b5c7865cbc61161b200618537bb5ccdacffe33d4a07cf61"),
    ("irq_field_vram_dma_stub", 0xFDFFFD, 0xFE0000,
     "10d81620264acc80f485880aaae6aca618776d72c5233de85b9a7c994b08e68d"),
    ("normal_nmi", 0xD1E77C, 0xD1E899,
     "3c6995513ccffd360ecba0594ea3c16c72104cac046999a673f72fc3c8932b4c"),
    ("normal_nmi_dispatch", 0xCD0C83, 0xCD0C9D,
     "9b5bbb390982840a7ab010ed1ad4ebd7d0603ff290e8917c159838a80b50ee0e"),
    ("normal_nmi_mode_1_2_body", 0xCD088D, 0xCD09CE,
     "375ef0e5bacfa712d55a80ac5fd75dd04c5206aa9e3d055cb10bdf7a85f5cf55"),
    ("normal_nmi_scene_interpreter", 0xCD1609, 0xCD16B5,
     "4ed9769ba6946b9400ecaf48bb604aaf77c5bb7fbc0d1a43dffc187700e6f77e"),
    ("alternate_nmi", 0xD1F4C0, 0xD1F559,
     "d92f1c6960851bf54a8ee2ade314be437335f285c1f3086034a0113f0357449b"),
    ("alternate_nmi_early_cgram_service", 0xCD09CE, 0xCD09F1,
     "65c3e12a3d48afac4a9167badfb85aa13ec374901293b443e7c55e1d636752f6"),
    ("field_dma_width_correction_1", 0xFDE21B, 0xFDE220,
     "ea507cc8d6ab6f2681420c5099a90369d6f0ef195c8e1b6a82b3075464391a4a"),
    ("field_dma_width_correction_2", 0xFDE247, 0xFDE24C,
     "ea507cc8d6ab6f2681420c5099a90369d6f0ef195c8e1b6a82b3075464391a4a"),
)
IRQ_BOUNDS = tuple((start, end) for _, start, end, _ in SPANS[:4])


class ClosureError(ValueError):
    """Unsupported or inconsistent evidence must not become a proof."""


# Generic instruction semantics, authored for the bounded corpus. Unsupported
# instructions refuse rather than guessing from an upstream annotation.
FIXED = {
    0x0B: ("PHD", 1), 0x18: ("CLC", 1), 0x1A: ("INC A", 1),
    0x20: ("JSR", 3), 0x22: ("JSL", 4), 0x28: ("PLP", 1),
    0x2B: ("PLD", 1), 0x40: ("RTI", 1), 0x48: ("PHA", 1),
    0x4A: ("LSR A", 1), 0x4C: ("JMP", 3), 0x54: ("MVN", 3),
    0x5A: ("PHY", 1), 0x5B: ("TCD", 1), 0x60: ("RTS", 1),
    0x64: ("STZ dp", 2), 0x68: ("PLA", 1), 0x6B: ("RTL", 1),
    0x6D: ("ADC abs", 3), 0x7A: ("PLY", 1), 0x7B: ("TDC", 1),
    0x7F: ("ADC long,X", 4), 0x85: ("STA dp", 2),
    0x8B: ("PHB", 1), 0x8C: ("STY abs", 3), 0x8D: ("STA abs", 3),
    0x8E: ("STX abs", 3), 0x8F: ("STA long", 4), 0x9C: ("STZ abs", 3),
    0xA5: ("LDA dp", 2), 0xA6: ("LDX dp", 2), 0xAA: ("TAX", 1),
    0xAB: ("PLB", 1), 0xAD: ("LDA abs", 3), 0xAF: ("LDA long", 4),
    0xBF: ("LDA long,X", 4), 0xC2: ("REP", 2), 0xCD: ("CMP abs", 3),
    0xDA: ("PHX", 1), 0xE2: ("SEP", 2), 0xE6: ("INC dp", 2),
    0xEB: ("XBA", 1), 0xFA: ("PLX", 1), 0x08: ("PHP", 1),
    0x0A: ("ASL A", 1),
}
BRANCHES = {0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0}
M_IMMEDIATES = {0x09: "ORA #", 0x29: "AND #", 0x49: "EOR #",
                0x69: "ADC #", 0x89: "BIT #", 0xA9: "LDA #",
                0xC9: "CMP #", 0xE9: "SBC #"}
X_IMMEDIATES = {0xA0: "LDY #", 0xA2: "LDX #", 0xC0: "CPY #", 0xE0: "CPX #"}


@dataclass(frozen=True)
class State:
    pc: int
    m8: bool
    x8: bool
    irq_masked: bool
    # None is an uninterpreted saved byte; tuple is a saved PHP value;
    # integer is one byte of the paired call frame identified by return PC.
    stack: tuple[tuple[bool, bool, bool] | int | None, ...]
    calls: tuple[tuple[int, str], ...] = ()


def walk_irq(read: Callable[[int, int], bytes], entry: int = 0xD1FE97,
             bounds: tuple[tuple[int, int], ...] = IRQ_BOUNDS) -> dict:
    queue = deque(State(entry, m8, x8, True, (None,) * 4)
                  for m8 in (False, True) for x8 in (False, True))
    seen: set[State] = set()
    instructions: dict[tuple[int, bool, bool], tuple[str, int]] = {}
    calls_seen: set[tuple[int, int, str]] = set()
    peaks: set[int] = set()
    peak_depth = 4
    exits = 0
    while queue:
        state = queue.popleft()
        if state in seen:
            continue
        seen.add(state)
        if len(seen) > 20000:
            raise ClosureError("state budget exceeded; closure is not proved")
        pc = state.pc
        if not any(start <= pc < end for start, end in bounds):
            raise ClosureError(f"control flow leaves declared bounds at {pc:06X}")
        opcode = read(pc, 1)[0]
        if opcode in M_IMMEDIATES:
            name, length = M_IMMEDIATES[opcode], 2 if state.m8 else 3
        elif opcode in X_IMMEDIATES:
            name, length = X_IMMEDIATES[opcode], 2 if state.x8 else 3
        elif opcode in BRANCHES or opcode == 0x80:
            name, length = "conditional branch" if opcode != 0x80 else "BRA", 2
        elif opcode in FIXED:
            name, length = FIXED[opcode]
        else:
            raise ClosureError(f"unsupported opcode {opcode:02X} at {pc:06X}")
        if not any(start <= pc and pc + length <= end for start, end in bounds):
            raise ClosureError(f"instruction crosses declared span at {pc:06X}")
        raw = read(pc, length)
        if len(raw) != length:
            raise ClosureError("short instruction read")
        instructions[(pc, state.m8, state.x8)] = (name, length)
        m8, x8, masked = state.m8, state.x8, state.irq_masked
        stack = list(state.stack)
        callstack = list(state.calls)
        destinations = [pc + length]

        def pop(count: int, return_pc: int | None = None) -> None:
            if len(stack) < count + 4:
                raise ClosureError(f"software stack consumes hardware frame at {pc:06X}")
            if return_pc is None and any(isinstance(item, int) for item in stack[-count:]):
                raise ClosureError(f"software pop consumes a return frame at {pc:06X}")
            if return_pc is not None and stack[-count:] != [return_pc] * count:
                raise ClosureError(f"return instruction lacks its exact frame at {pc:06X}")
            del stack[-count:]

        if opcode in (0xC2, 0xE2):
            value = opcode == 0xE2
            if raw[1] & 0x20: m8 = value
            if raw[1] & 0x10: x8 = value
            if raw[1] & 0x04: masked = value
        elif opcode == 0x08:
            stack.append((m8, x8, masked))
        elif opcode == 0x28:
            if len(stack) <= 4 or not isinstance(stack[-1], tuple):
                raise ClosureError(f"PLP lacks a known saved status at {pc:06X}")
            m8, x8, masked = stack[-1]
            pop(1)
        elif opcode in (0x48, 0xDA, 0x5A, 0x8B, 0x0B):
            width = (1 if m8 else 2) if opcode == 0x48 else (
                (1 if x8 else 2) if opcode in (0xDA, 0x5A) else
                1 if opcode == 0x8B else 2)
            stack.extend([None] * width)
        elif opcode in (0x68, 0xFA, 0x7A, 0xAB, 0x2B):
            width = (1 if m8 else 2) if opcode == 0x68 else (
                (1 if x8 else 2) if opcode in (0xFA, 0x7A) else
                1 if opcode == 0xAB else 2)
            pop(width)
        elif opcode in (0x20, 0x22):
            target = int.from_bytes(raw[1:], "little")
            if opcode == 0x20: target |= pc & 0xFF0000
            kind = "near" if opcode == 0x20 else "long"
            stack.extend([pc + length] * (2 if kind == "near" else 3))
            callstack.append((pc + length, kind))
            calls_seen.add((pc, target, kind))
            destinations = [target]
        elif opcode in (0x60, 0x6B):
            expected = "near" if opcode == 0x60 else "long"
            if not callstack or callstack[-1][1] != expected:
                raise ClosureError(f"unpaired {name} at {pc:06X}")
            destinations = [callstack.pop()[0]]
            pop(2 if expected == "near" else 3, destinations[0])
        elif opcode == 0x40:
            if callstack or len(stack) != 4:
                raise ClosureError(f"unbalanced RTI at {pc:06X}")
            exits += 1
            continue
        elif opcode == 0x4C:
            destinations = [(pc & 0xFF0000) | int.from_bytes(raw[1:], "little")]
        elif opcode in BRANCHES or opcode == 0x80:
            target = pc + length + int.from_bytes(raw[1:], "little", signed=True)
            destinations = [target] if opcode == 0x80 else [pc + length, target]
        if not masked:
            raise ClosureError(f"IRQ unmasking found at {pc:06X}; nesting model required")
        if len(stack) > peak_depth:
            peak_depth, peaks = len(stack), {pc + length}
        elif len(stack) == peak_depth:
            peaks.add(pc + length)
        queue.extend(State(next_pc, m8, x8, masked, tuple(stack), tuple(callstack))
                     for next_pc in destinations)
    if not exits:
        raise ClosureError("no balanced RTI exit")
    return {
        "abstract_state_count": len(seen),
        "instruction_context_count": len(instructions),
        "unique_instruction_start_count": len({key[0] for key in instructions}),
        "maximum_depth_including_native_hardware_frame": peak_depth,
        "maximum_depth_software_only": peak_depth - 4,
        "balanced_rti_context_count": exits,
        "peak_successor_watchpoints": [f"${pc:06X}" for pc in sorted(peaks)],
        "all_modeled_paths_keep_irq_masked": True,
        "direct_calls": [{"site": f"${site:06X}", "target": f"${target:06X}",
                          "kind": kind} for site, target, kind in sorted(calls_seen)],
        "mnemonic_context_counts": dict(sorted(Counter(v[0] for v in instructions.values()).items())),
        "width_correction_witnesses": [
            {"address": f"${pc:06X}", "m8": m8, "x8": x8,
             "mnemonic": name, "length": length}
            for (pc, m8, x8), (name, length) in sorted(instructions.items())
            if 0xFDE21B <= pc < 0xFDE220 or 0xFDE247 <= pc < 0xFDE24C
        ],
    }


def audit(rom: bytes) -> dict:
    if len(rom) != 0x400000 or hashlib.sha256(rom).hexdigest() != ROM_SHA256:
        raise ClosureError("requires exact canonical headerless US Rev0 ROM")
    def read(pc: int, size: int) -> bytes:
        if not 0xC00000 <= pc < pc + size <= 0x1000000:
            raise ClosureError("read outside canonical high ROM")
        return rom[pc - 0xC00000:pc - 0xC00000 + size]
    spans = []
    for role, start, end, expected in SPANS:
        digest = hashlib.sha256(read(start, end - start)).hexdigest()
        if expected is not None and digest != expected:
            raise ClosureError(f"pinned span drift: {role}")
        spans.append({"role": role, "cpu_start": f"${start:06X}",
                      "cpu_end_exclusive": f"${end:06X}", "size": end - start,
                      "sha256": digest})
    closure = walk_irq(read)
    if closure["maximum_depth_including_native_hardware_frame"] != 35:
        raise ClosureError("reviewed IRQ maximum changed")
    return {
        "schema": SCHEMA, "evidence_level": "verified-static",
        "status": "pass-bounded-non-nested-irq-closure-nmi-remains-open",
        "canonical_rom": {"size": len(rom), "sha256": ROM_SHA256},
        "source": {"path": "tools/audit_schala_package_interrupt_closure_v1.py",
                   "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "spans": spans, "irq_abstract_walk": closure,
        "nmi_mode_table_bounded_entries": [
            {"mode": mode, "target": f"$CD{int.from_bytes(read(0xCD0C83 + mode * 2, 2), 'little'):04X}"}
            for mode in range(3)],
        "nmi_lifecycle_shared_state": {
            "effect_latch": "$7E5D9B", "read_site": "$CD160E",
            "clear_site": "$CD164D", "scene_command_indirect_call": "$CD16AF"},
        "interpretation": {
            "data_conditions": "both conditional outcomes; some combinations may be infeasible",
            "register_values_and_dma_sources": "not modeled",
            "non_stack_instruction_writes_to_stack": "not modeled; canonical direct destinations reviewed separately",
            "nmi_nesting": "not included in the 35-byte bound",
            "global_stack_headroom": "not established",
            "production_hook_or_allocation_approved": False,
            "production_scratch_approved": False,
            "game_rom_mutated": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path,
                        default=ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc")
    args = parser.parse_args()
    try:
        result = audit(args.rom.read_bytes())
    except (OSError, ClosureError) as exc:
        parser.exit(1, f"interrupt closure audit refused: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
