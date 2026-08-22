#!/usr/bin/env python3
"""Validate the separate optimized 65C816 SHA-256 profile-1 candidate.

The validator parses the optimized Asar source, interprets its authored macro
bodies, proves every fixed rotate/shift decomposition over deterministic
high-coverage 32-bit vectors, and drives a source-derived SHA model against
standard and Project Epoch profile vectors.

This remains source-only evidence.  The optional Asar invocation writes only a
deleted private ``norom`` syntax target; it never reads or writes a game ROM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from typing import Final


ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR: Final = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import validate_schala_sha256_65816 as baseline  # noqa: E402


ASM_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_fast.asm"
)
SYNTAX_WRAPPER_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_fast_syntax.asm"
)
DEFAULT_ASAR_PATH: Final = baseline.DEFAULT_ASAR_PATH
PRIVATE_TEMP_PARENT: Final = baseline.PRIVATE_TEMP_PARENT

SCRATCH_SIZE: Final = 0xC2
ENTRY_SAVE_FRAME_SIZE: Final = 10
MAX_NESTED_JSR_COUNT: Final = 2
MAX_STACK_GROWTH_AFTER_ENTRY: Final = 14
MAX_STACK_GROWTH_WITH_CALLER_JSL: Final = 17
INITIAL_TABLE_SIZE: Final = 0x20
K_TABLE_SIZE: Final = 0x100
ALGORITHM_TABLE_BYTES: Final = INITIAL_TABLE_SIZE + K_TABLE_SIZE
LOOKUP_TABLE_BYTES: Final = 0

BASELINE_BIT_STEPS_PER_BLOCK: Final = 8608
FAST_BIT_STEPS_PER_BLOCK: Final = 1408
PROFILE_BLOCK_COUNT: Final = 41
BASELINE_BIT_STEPS_PER_DIGEST: Final = (
    BASELINE_BIT_STEPS_PER_BLOCK * PROFILE_BLOCK_COUNT
)
FAST_BIT_STEPS_PER_DIGEST: Final = (
    FAST_BIT_STEPS_PER_BLOCK * PROFILE_BLOCK_COUNT
)

EXPECTED_BASELINE_HASHES: Final = {
    ROOT
    / "asm"
    / "schala_sidecar_sha256_profile1.asm": (
        "0c9636a6fbfdd79f14db83d90488552894d694da30632edd336dfebc78d169f0"
    ),
    ROOT
    / "asm"
    / "schala_sidecar_sha256_profile1_syntax.asm": (
        "ba270d5fc3aab7d1a18b24e36fa344c7766df717a3fb344c1c0a62965766c9a7"
    ),
    ROOT
    / "tools"
    / "validate_schala_sha256_65816.py": (
        "2693efbba44dc39fa5ad86a7049011179c24a2640878f43a5cffdfa92e74bb07"
    ),
    ROOT
    / "tests"
    / "test_schala_sha256_65816.py": (
        "b1ed0e48eb3c15a3a16a936068363bb140e1d85a9260250ca3ca86f9397637a1"
    ),
}

PRIMITIVE_EXPECTATIONS: Final = {
    "Rotr2": (
        "rotr",
        2,
        ("CopyInput", "Ror1", "Ror1"),
    ),
    "Rotr13": (
        "rotr",
        13,
        ("Swap16", "Rol1", "Rol1", "Rol1"),
    ),
    "Rotr22": (
        "rotr",
        22,
        ("Rotr24", "Rol1", "Rol1"),
    ),
    "Rotr6": (
        "rotr",
        6,
        ("Rotr8", "Rol1", "Rol1"),
    ),
    "Rotr11": (
        "rotr",
        11,
        ("Rotr8", "Ror1", "Ror1", "Ror1"),
    ),
    "Rotr25": (
        "rotr",
        25,
        ("Rotr24", "Ror1"),
    ),
    "Rotr7": (
        "rotr",
        7,
        ("Rotr8", "Rol1"),
    ),
    "Rotr18": (
        "rotr",
        18,
        ("Swap16", "Ror1", "Ror1"),
    ),
    "Shr3": (
        "shr",
        3,
        ("CopyInput", "Shr1", "Shr1", "Shr1"),
    ),
    "Rotr17": (
        "rotr",
        17,
        ("Swap16", "Ror1"),
    ),
    "Rotr19": (
        "rotr",
        19,
        ("Swap16", "Ror1", "Ror1", "Ror1"),
    ),
    "Shr10": (
        "shr",
        10,
        ("Shr8", "Shr1", "Shr1"),
    ),
}

SIGMA_PRIMITIVES: Final = {
    "BigSigma0": ("Rotr2", "Rotr13", "Rotr22"),
    "BigSigma1": ("Rotr6", "Rotr11", "Rotr25"),
    "SmallSigma0": ("Rotr7", "Rotr18", "Shr3"),
    "SmallSigma1": ("Rotr17", "Rotr19", "Shr10"),
}

MACRO_CANONICAL: Final = {
    "CopyInput": ("rotr", 0),
    "Swap16": ("rotr", 16),
    "Rotr8": ("rotr", 8),
    "Rotr24": ("rotr", 24),
    "Shr8": ("shr", 8),
    "Ror1": ("rotr", 1),
    "Rol1": ("rotl", 1),
    "Shr1": ("shr", 1),
}

_MACRO_BODY_RE: Final = re.compile(
    r"^macro\s+EpochSha256Fast_([A-Za-z0-9]+)\(\)\s*$"
    r"(.*?)"
    r"^endmacro\s*$",
    re.MULTILINE | re.DOTALL,
)
_MACRO_CALL_RE: Final = re.compile(
    r"%EpochSha256Fast_([A-Za-z0-9]+)\(\)"
)
_WORD_RE: Final = re.compile(
    r"\bdw\s+\$([0-9A-Fa-f]{4}),\$([0-9A-Fa-f]{4})"
)
_FORBIDDEN_DIRECTIVE_RE: Final = re.compile(
    r"^\s*(?:org|lorom|hirom|exhirom|norom|incbin|autoclean)\b",
    re.IGNORECASE | re.MULTILINE,
)
_BANK30_WRITE_RE: Final = re.compile(
    r"^\s*(?:sta|stx|sty|stz)\b[^;\r\n]*\$30[0-9A-Fa-f]{4}\b",
    re.IGNORECASE | re.MULTILINE,
)
_MEMORY_OPERAND_RE: Final = re.compile(
    r"!PE_SHA256_SCRATCH_LO\+!PE_SHA_(INPUT|ROT)(?:\+([0-3]))?$"
)


class FastSha256Error(ValueError):
    """Raised when the optimized source fails closed."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_comments(source: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in source.splitlines())


def _section(source: str, start: str, end: str) -> str:
    try:
        return source.split(f"{start}:", 1)[1].split(f"{end}:", 1)[0]
    except IndexError as exc:
        raise FastSha256Error(f"missing source section {start}/{end}") from exc


def parse_macro_bodies(source: str | None = None) -> dict[str, tuple[str, ...]]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    bodies: dict[str, tuple[str, ...]] = {}
    for name, body in _MACRO_BODY_RE.findall(_strip_comments(source)):
        lines = tuple(
            " ".join(line.strip().split())
            for line in body.splitlines()
            if line.strip()
        )
        bodies[name] = lines
    if set(bodies) != set(MACRO_CANONICAL):
        missing = sorted(set(MACRO_CANONICAL) - set(bodies))
        extra = sorted(set(bodies) - set(MACRO_CANONICAL))
        raise FastSha256Error(
            f"optimized macro set mismatch: missing={missing}, extra={extra}"
        )
    return bodies


def parse_primitive_sequences(
    source: str | None = None,
) -> dict[str, tuple[str, ...]]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    sequences: dict[str, tuple[str, ...]] = {}
    for name, (_, _, expected) in PRIMITIVE_EXPECTATIONS.items():
        body = _section(
            source,
            f"EpochSha256Fast_{name}_Start",
            f"EpochSha256Fast_{name}_End",
        )
        sequence = tuple(_MACRO_CALL_RE.findall(body))
        if sequence != expected:
            raise FastSha256Error(
                f"{name} sequence {sequence!r} != expected {expected!r}"
            )
        sequences[name] = sequence
    return sequences


def _parse_tables(
    source: str | None = None,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")

    def parse(start: str, end: str) -> tuple[int, ...]:
        body = _section(source, start, end)
        return tuple(
            (int(high, 16) << 16) | int(low, 16)
            for high, low in _WORD_RE.findall(body)
        )

    initial = parse(
        "EpochSha256Fast_InitialState",
        "EpochSha256Fast_InitialState_End",
    )
    constants = parse("EpochSha256Fast_K", "EpochSha256Fast_K_End")
    if len(initial) != 8 or len(constants) != 64:
        raise FastSha256Error("optimized SHA table cardinality mismatch")
    baseline_initial, baseline_constants = baseline.parse_assembly_constants()
    baseline_initial_u32 = tuple(
        (high << 16) | low for high, low in baseline_initial
    )
    baseline_constants_u32 = tuple(
        (high << 16) | low for high, low in baseline_constants
    )
    if initial != baseline_initial_u32 or constants != baseline_constants_u32:
        raise FastSha256Error("optimized algorithm tables differ from baseline")
    return initial, constants


def _rotr32(value: int, count: int) -> int:
    value &= 0xFFFFFFFF
    count &= 31
    if count == 0:
        return value
    return ((value >> count) | (value << (32 - count))) & 0xFFFFFFFF


def _rotl32(value: int, count: int) -> int:
    value &= 0xFFFFFFFF
    count &= 31
    if count == 0:
        return value
    return ((value << count) | (value >> (32 - count))) & 0xFFFFFFFF


def _canonical_transform(value: int, kind: str, count: int) -> int:
    if kind == "rotr":
        return _rotr32(value, count)
    if kind == "rotl":
        return _rotl32(value, count)
    if kind == "shr":
        return (value & 0xFFFFFFFF) >> count
    raise AssertionError(f"unknown transform {kind}")


def _memory_address(operand: str) -> int:
    match = _MEMORY_OPERAND_RE.fullmatch(operand)
    if match is None:
        raise FastSha256Error(f"unsupported macro memory operand {operand}")
    region, relative_text = match.groups()
    base = 0 if region == "INPUT" else 4
    return base + (int(relative_text) if relative_text else 0)


def _read(memory: bytearray, address: int, width: int) -> int:
    return int.from_bytes(memory[address : address + width], "little")


def _write(memory: bytearray, address: int, width: int, value: int) -> None:
    memory[address : address + width] = (
        value & ((1 << (width * 8)) - 1)
    ).to_bytes(width, "little")


def _execute_macro_lines(
    lines: tuple[str, ...],
    *,
    memory: bytearray,
    accumulator: int,
    carry: int,
    m8: bool,
) -> tuple[int, int, bool]:
    for line in lines:
        parts = line.split(maxsplit=1)
        opcode = parts[0].upper()
        operand = parts[1] if len(parts) == 2 else ""
        width = 1 if m8 else 2
        mask = (1 << (width * 8)) - 1
        top_bit = 1 << (width * 8 - 1)
        if opcode in {"LDA.W", "STA.W", "STZ.W"}:
            address = _memory_address(operand)
            if opcode == "LDA.W":
                accumulator = _read(memory, address, width)
            elif opcode == "STA.W":
                _write(memory, address, width, accumulator)
            else:
                _write(memory, address, width, 0)
        elif opcode == "SEP":
            if operand != "#$20":
                raise FastSha256Error(f"unsupported SEP operand {operand}")
            m8 = True
        elif opcode == "REP":
            if operand != "#$20":
                raise FastSha256Error(f"unsupported REP operand {operand}")
            m8 = False
        elif opcode == "LSR":
            if operand != "A":
                raise FastSha256Error(f"unsupported LSR operand {operand}")
            carry = accumulator & 1
            accumulator = (accumulator >> 1) & mask
        elif opcode == "ASL":
            if operand != "A":
                raise FastSha256Error(f"unsupported ASL operand {operand}")
            carry = 1 if accumulator & top_bit else 0
            accumulator = (accumulator << 1) & mask
        elif opcode == "ROR":
            if operand != "A":
                raise FastSha256Error(f"unsupported ROR operand {operand}")
            old_low = accumulator & 1
            accumulator = ((carry << (width * 8 - 1)) | (accumulator >> 1))
            accumulator &= mask
            carry = old_low
        elif opcode == "ROL":
            if operand != "A":
                raise FastSha256Error(f"unsupported ROL operand {operand}")
            old_high = 1 if accumulator & top_bit else 0
            accumulator = ((accumulator << 1) | carry) & mask
            carry = old_high
        else:
            raise FastSha256Error(f"unsupported macro instruction {line}")
    return accumulator, carry, m8


def execute_macro_from_source(
    name: str,
    value: int,
    *,
    macro_bodies: dict[str, tuple[str, ...]] | None = None,
) -> int:
    if macro_bodies is None:
        macro_bodies = parse_macro_bodies()
    if name not in macro_bodies:
        raise FastSha256Error(f"unknown optimized macro {name}")
    value &= 0xFFFFFFFF
    memory = bytearray(8)
    _write(memory, 0, 2, value >> 16)
    _write(memory, 2, 2, value)
    _write(memory, 4, 2, value >> 16)
    _write(memory, 6, 2, value)
    _, _, m8 = _execute_macro_lines(
        macro_bodies[name],
        memory=memory,
        accumulator=0,
        carry=0,
        m8=False,
    )
    if m8:
        raise FastSha256Error(f"macro {name} does not restore 16-bit M")
    return (_read(memory, 4, 2) << 16) | _read(memory, 6, 2)


def _apply_named_macro(value: int, name: str) -> int:
    kind, count = MACRO_CANONICAL[name]
    return _canonical_transform(value, kind, count)


def primitive_from_source(
    name: str,
    value: int,
    *,
    sequences: dict[str, tuple[str, ...]] | None = None,
) -> int:
    if sequences is None:
        sequences = parse_primitive_sequences()
    result = value & 0xFFFFFFFF
    for macro_name in sequences[name]:
        result = _apply_named_macro(result, macro_name)
    return result


def sigma_from_source(
    name: str,
    value: int,
    *,
    sequences: dict[str, tuple[str, ...]] | None = None,
) -> int:
    if sequences is None:
        sequences = parse_primitive_sequences()
    result = 0
    for primitive_name in SIGMA_PRIMITIVES[name]:
        result ^= primitive_from_source(
            primitive_name,
            value,
            sequences=sequences,
        )
    return result & 0xFFFFFFFF


def _high_coverage_values() -> Iterable[int]:
    # Each of the three passes exhausts one 16-bit lane.  The odd multiplier
    # in the coupled pass permutes every possible low lane while high exhausts.
    for lane in range(0x10000):
        yield lane
    for lane in range(0x10000):
        yield (lane << 16) | 0xA5A5
    for lane in range(0x10000):
        yield (lane << 16) | ((lane * 0x9E37 + 0xB7E1) & 0xFFFF)


def verify_macro_oracles() -> dict[str, object]:
    bodies = parse_macro_bodies()
    vector_count = 0x10000
    for name, (kind, count) in MACRO_CANONICAL.items():
        for lane in range(vector_count):
            value = (lane << 16) | ((lane * 0x9E37 + 0xB7E1) & 0xFFFF)
            actual = execute_macro_from_source(
                name,
                value,
                macro_bodies=bodies,
            )
            expected = _canonical_transform(value, kind, count)
            if actual != expected:
                raise FastSha256Error(
                    f"macro {name} failed at 0x{value:08X}: "
                    f"0x{actual:08X} != 0x{expected:08X}"
                )
    return {
        "macro_count": len(MACRO_CANONICAL),
        "vectors_per_macro": vector_count,
        "comparisons": len(MACRO_CANONICAL) * vector_count,
    }


def verify_primitive_and_sigma_oracles() -> dict[str, object]:
    sequences = parse_primitive_sequences()
    vector_count = 0
    for value in _high_coverage_values():
        vector_count += 1
        for name, (kind, count, _) in PRIMITIVE_EXPECTATIONS.items():
            actual = primitive_from_source(name, value, sequences=sequences)
            expected = _canonical_transform(value, kind, count)
            if actual != expected:
                raise FastSha256Error(
                    f"primitive {name} failed at 0x{value:08X}"
                )
        canonical_sigmas = {
            "BigSigma0": (
                _rotr32(value, 2)
                ^ _rotr32(value, 13)
                ^ _rotr32(value, 22)
            ),
            "BigSigma1": (
                _rotr32(value, 6)
                ^ _rotr32(value, 11)
                ^ _rotr32(value, 25)
            ),
            "SmallSigma0": (
                _rotr32(value, 7)
                ^ _rotr32(value, 18)
                ^ (value >> 3)
            ),
            "SmallSigma1": (
                _rotr32(value, 17)
                ^ _rotr32(value, 19)
                ^ (value >> 10)
            ),
        }
        for name, expected in canonical_sigmas.items():
            actual = sigma_from_source(name, value, sequences=sequences)
            if actual != expected & 0xFFFFFFFF:
                raise FastSha256Error(
                    f"sigma {name} failed at 0x{value:08X}"
                )
    return {
        "vectors": vector_count,
        "primitive_count": len(PRIMITIVE_EXPECTATIONS),
        "sigma_count": len(SIGMA_PRIMITIVES),
        "comparisons": vector_count
        * (len(PRIMITIVE_EXPECTATIONS) + len(SIGMA_PRIMITIVES)),
    }


def sha256_fast_source_model(message: bytes) -> bytes:
    if type(message) is not bytes:
        raise FastSha256Error("message must be exact immutable bytes")
    if len(message) >= 1 << 61:
        raise FastSha256Error("message length does not fit SHA-256")
    initial, constants = _parse_tables()
    sequences = parse_primitive_sequences()
    state = list(initial)
    padded = bytearray(message)
    padded.append(0x80)
    padded.extend(b"\x00" * ((56 - len(padded) % 64) % 64))
    padded.extend((len(message) * 8).to_bytes(8, "big"))

    for block_start in range(0, len(padded), 64):
        block = padded[block_start : block_start + 64]
        schedule = [
            int.from_bytes(block[offset : offset + 4], "big")
            for offset in range(0, 64, 4)
        ]
        a, b, c, d, e, f, g, h = state
        for round_index in range(64):
            circular = round_index & 15
            if round_index >= 16:
                schedule[circular] = (
                    schedule[circular]
                    + sigma_from_source(
                        "SmallSigma0",
                        schedule[(round_index + 1) & 15],
                        sequences=sequences,
                    )
                    + schedule[(round_index + 9) & 15]
                    + sigma_from_source(
                        "SmallSigma1",
                        schedule[(round_index + 14) & 15],
                        sequences=sequences,
                    )
                ) & 0xFFFFFFFF
            choice = g ^ (e & (f ^ g))
            majority = (a & b) | (c & (a | b))
            t1 = (
                h
                + sigma_from_source("BigSigma1", e, sequences=sequences)
                + choice
                + constants[round_index]
                + schedule[circular]
            ) & 0xFFFFFFFF
            t2 = (
                sigma_from_source("BigSigma0", a, sequences=sequences)
                + majority
            ) & 0xFFFFFFFF
            h, g, f = g, f, e
            e = (d + t1) & 0xFFFFFFFF
            d, c, b = c, b, a
            a = (t1 + t2) & 0xFFFFFFFF
        state = [
            (old + new) & 0xFFFFFFFF
            for old, new in zip(
                state,
                (a, b, c, d, e, f, g, h),
                strict=True,
            )
        ]
    return b"".join(word.to_bytes(4, "big") for word in state)


def profile1_digest_model(serialized_slot: bytes, slot_number: int) -> bytes:
    if type(serialized_slot) is not bytes or len(serialized_slot) != baseline.SLOT_SIZE:
        raise FastSha256Error("serialized slot must be exact $0A00 bytes")
    return sha256_fast_source_model(
        serialized_slot + baseline.binding_trailer(slot_number)
    )


def profile1_final_block_from_source(
    slot_number: int,
    source: str | None = None,
) -> bytes:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    adapted = source.replace(
        "EpochSha256Fast_LoadProfile1FinalBlock",
        "EpochSha256_LoadProfile1FinalBlock",
    ).replace(
        "EpochSha256Fast_CompressBlock",
        "EpochSha256_CompressBlock",
    )
    return baseline.profile1_final_block_from_source(slot_number, adapted)


def _normalized_core(source: str, *, fast: bool) -> tuple[str, ...]:
    prefix = "EpochSha256Fast_" if fast else "EpochSha256_"
    body = _section(
        source,
        f"{prefix}Profile1Digest",
        f"{prefix}BigSigma0",
    )
    if fast:
        body = body.replace("EpochSha256Fast_", "EpochSha256_")
    return tuple(
        " ".join(line.split())
        for line in _strip_comments(body).splitlines()
        if line.strip()
    )


def _normalized_emit(source: str, *, fast: bool) -> tuple[str, ...]:
    prefix = "EpochSha256Fast_" if fast else "EpochSha256_"
    end = f"{prefix}InitialState"
    body = _section(source, f"{prefix}EmitDigest", end)
    if fast:
        body = body.replace("EpochSha256Fast_", "EpochSha256_")
    return tuple(
        " ".join(line.split())
        for line in _strip_comments(body).splitlines()
        if line.strip()
    )


def validate_baseline_unchanged() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path, expected in EXPECTED_BASELINE_HASHES.items():
        actual = sha256(path.read_bytes())
        if actual != expected:
            raise FastSha256Error(f"proven baseline changed: {path}")
        hashes[path.relative_to(ROOT).as_posix()] = actual
    return hashes


def validate_source_contract(source: str | None = None) -> dict[str, object]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    code = _strip_comments(source)
    if _FORBIDDEN_DIRECTIVE_RE.search(code):
        raise FastSha256Error("optimized source contains placement directive")
    if _BANK30_WRITE_RE.search(code):
        raise FastSha256Error("optimized source contains bank-$30 write")
    if "$7E2CA0" in code.upper():
        raise FastSha256Error("optimized source claims compatibility WRAM")
    for token in (
        "EpochSha256Fast_Profile1Digest:",
        "EpochSha256Fast_CompressBlock:",
        "EpochSha256Fast_EmitDigest:",
        "!PE_SHA256_SCRATCH_SIZE = $00C2",
        "LDA.l $300000,X",
        "CMP.w #$0028",
        "LDA.w #$5080",
        "PHP",
        "CLD",
        "PLP",
    ):
        if token not in source:
            raise FastSha256Error(f"optimized source token missing: {token}")
    if "EpochSha256_RotateInputRight" in source or "EpochSha256_ShiftInputRight" in source:
        raise FastSha256Error("optimized source still invokes baseline loops")
    parse_macro_bodies(source)
    sequences = parse_primitive_sequences(source)
    _parse_tables(source)

    baseline_source = baseline.ASM_PATH.read_text(encoding="utf-8")
    if _normalized_core(source, fast=True) != _normalized_core(
        baseline_source,
        fast=False,
    ):
        raise FastSha256Error(
            "non-sigma optimized core differs from proven baseline"
        )
    if _normalized_emit(source, fast=True) != _normalized_emit(
        baseline_source,
        fast=False,
    ):
        raise FastSha256Error("optimized digest emitter differs from baseline")

    for slot_number in range(1, 4):
        final_block = profile1_final_block_from_source(slot_number, source)
        if final_block[:16] != baseline.binding_trailer(slot_number):
            raise FastSha256Error("optimized source trailer mismatch")
        if final_block[16:56] != b"\x80" + bytes(39):
            raise FastSha256Error("optimized source padding mismatch")
        if final_block[56:] != (baseline.PROFILE_MESSAGE_SIZE * 8).to_bytes(
            8,
            "big",
        ):
            raise FastSha256Error("optimized source length mismatch")

    bit_counts = {
        name: sum(
            token in {"Ror1", "Rol1", "Shr1"} for token in sequence
        )
        for name, sequence in sequences.items()
    }
    return {
        "source_sha256": sha256(source.encode("utf-8")),
        "scratch_size": SCRATCH_SIZE,
        "entry_save_frame_size": ENTRY_SAVE_FRAME_SIZE,
        "max_nested_jsr_count": MAX_NESTED_JSR_COUNT,
        "max_stack_growth_after_entry": MAX_STACK_GROWTH_AFTER_ENTRY,
        "max_stack_growth_with_caller_jsl": MAX_STACK_GROWTH_WITH_CALLER_JSL,
        "algorithm_table_bytes": ALGORITHM_TABLE_BYTES,
        "lookup_table_bytes": LOOKUP_TABLE_BYTES,
        "baseline_bit_steps_per_block": BASELINE_BIT_STEPS_PER_BLOCK,
        "fast_bit_steps_per_block": FAST_BIT_STEPS_PER_BLOCK,
        "baseline_bit_steps_per_digest": BASELINE_BIT_STEPS_PER_DIGEST,
        "fast_bit_steps_per_digest": FAST_BIT_STEPS_PER_DIGEST,
        "bit_step_reduction_percent": (
            100
            * (BASELINE_BIT_STEPS_PER_BLOCK - FAST_BIT_STEPS_PER_BLOCK)
            / BASELINE_BIT_STEPS_PER_BLOCK
        ),
        "primitive_bit_steps": bit_counts,
        "placed": False,
        "writes_bank_30": False,
    }


def verify_digest_vectors() -> dict[str, object]:
    standard = (b"", b"abc", b"a" * 55, b"a" * 56, bytes(range(256)))
    for message in standard:
        if sha256_fast_source_model(message) != hashlib.sha256(message).digest():
            raise FastSha256Error(
                f"optimized digest model mismatch at length {len(message)}"
            )
    zero = bytes(baseline.SLOT_SIZE)
    zero_vectors: dict[str, str] = {}
    for slot_number, expected in baseline.EXPECTED_ZERO_SLOT_DIGESTS.items():
        actual = profile1_digest_model(zero, slot_number).hex()
        if actual != expected:
            raise FastSha256Error(
                f"optimized zero-slot vector mismatch for {slot_number}"
            )
        zero_vectors[str(slot_number)] = actual
    pattern = bytes(index & 0xFF for index in range(baseline.SLOT_SIZE))
    pattern_vectors: dict[str, str] = {}
    for slot_number in range(1, 4):
        actual = profile1_digest_model(pattern, slot_number)
        expected = hashlib.sha256(
            pattern + baseline.binding_trailer(slot_number)
        ).digest()
        if actual != expected:
            raise FastSha256Error(
                f"optimized pattern vector mismatch for {slot_number}"
            )
        pattern_vectors[str(slot_number)] = actual.hex()
    return {
        "standard_vectors": len(standard),
        "profile_vectors": 6,
        "all_zero": zero_vectors,
        "incrementing_pattern": pattern_vectors,
    }


def run_asar_syntax(
    asar_path: pathlib.Path = DEFAULT_ASAR_PATH,
) -> dict[str, object]:
    asar_path = asar_path.resolve()
    if not asar_path.is_file():
        raise FastSha256Error(f"Asar executable not found: {asar_path}")
    PRIVATE_TEMP_PARENT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="sha256_65816_fast_syntax_",
        dir=PRIVATE_TEMP_PARENT,
    ) as temporary:
        output_path = pathlib.Path(temporary) / "fast_syntax_probe.bin"
        result = subprocess.run(
            (
                str(asar_path),
                "--no-title-check",
                "--fix-checksum=off",
                "-werror",
                str(SYNTAX_WRAPPER_PATH),
                str(output_path),
            ),
            cwd=SYNTAX_WRAPPER_PATH.parent,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise FastSha256Error(
                "optimized Asar syntax failed:\n"
                + result.stdout
                + result.stderr
            )
        assembled = output_path.read_bytes()
        probe = {
            "asar_sha256": sha256(asar_path.read_bytes()),
            "assembled_size": len(assembled),
            "assembled_sha256": sha256(assembled),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    if output_path.exists():
        raise FastSha256Error("optimized syntax probe was not deleted")
    return probe


def validate(
    asar_path: pathlib.Path | None = None,
    *,
    full_oracle: bool = True,
) -> dict[str, object]:
    result: dict[str, object] = {
        "evidence": "source-only-host-model",
        "baseline_unchanged": validate_baseline_unchanged(),
        "source": validate_source_contract(),
        "digests": verify_digest_vectors(),
    }
    if full_oracle:
        result["macro_oracle"] = verify_macro_oracles()
        result["primitive_sigma_oracle"] = (
            verify_primitive_and_sigma_oracles()
        )
    if asar_path is not None:
        result["asar_syntax"] = run_asar_syntax(asar_path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asar", type=pathlib.Path)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="skip exhaustive/high-coverage primitive oracles",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(
        json.dumps(
            validate(args.asar, full_oracle=not args.quick),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
