#!/usr/bin/env python3
"""Validate the separate round8/table 65C816 SHA-256 candidate.

This validator binds the authored assembly to the generated mathematical
sigma tables, the pinned SHA-256 constants, the eight-round symbolic mapping,
and standard/profile digest oracles.  Its optional Asar run targets only a
deleted private ``norom`` probe.  It does not read or write a game ROM.
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
from collections.abc import Sequence
from typing import Final


ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR: Final = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import generate_schala_sha256_65816_sigma_tables as sigma_tables  # noqa: E402
import validate_schala_sha256_65816 as baseline  # noqa: E402
import validate_schala_sha256_65816_fast as fast  # noqa: E402


ASM_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_round8.asm"
)
SYNTAX_WRAPPER_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_round8_syntax.asm"
)
BENCHMARK_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_round8_benchmark.asm"
)
TABLE_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_sigma_tables.asm"
)
FAST_BENCHMARK_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_fast_benchmark.asm"
)
DEFAULT_ASAR_PATH: Final = baseline.DEFAULT_ASAR_PATH
PRIVATE_TEMP_PARENT: Final = baseline.PRIVATE_TEMP_PARENT

SCRATCH_SIZE: Final = 0x00C2
CODE_LIMIT: Final = 0x6000
TABLE_SIZE: Final = 0x4000
ENTRY_SAVE_FRAME_SIZE: Final = 10
MAX_NESTED_JSR_COUNT: Final = 2
MAX_STACK_GROWTH_AFTER_ENTRY: Final = 14
MAX_STACK_GROWTH_WITH_CALLER_JSL: Final = 17
ROUND_COUNT: Final = 64
GROUP_COUNT: Final = 8
ROUNDS_PER_GROUP: Final = 8
WORD_MASK: Final = 0xFFFFFFFF

FROZEN_INPUT_HASHES: Final = {
    ROOT
    / "asm"
    / "schala_sidecar_sha256_profile1_fast.asm": (
        "f4244a5f4c5586a0f096f5f12baf3400bf0402af1136cb73b115147e9e4e0f86"
    ),
    ROOT
    / "asm"
    / "schala_sidecar_sha256_profile1_fast_syntax.asm": (
        "6c64ab446088613e7f659bd0cd0fddf80182c5c0544a9c77836f13f91c48eaf7"
    ),
    FAST_BENCHMARK_PATH: (
        "9a19c389d71e9f2f0cd6a80815b5f501923892e4efb4941660ac50fd12c9965a"
    ),
    ROOT
    / "tools"
    / "build_sha256_65816_standalone_benchmark.py": (
        "b07fc0f3f62714aeaa52c37c32a1ab3f41111e94d8de2ac96ddbf9dae1982ab1"
    ),
}

_FORBIDDEN_DIRECTIVE_RE: Final = re.compile(
    r"^\s*(?:org|lorom|hirom|exhirom|norom|incbin|autoclean)\b",
    re.IGNORECASE | re.MULTILINE,
)
_BANK30_WRITE_RE: Final = re.compile(
    r"^\s*(?:sta|stx|sty|stz)\b[^;\r\n]*\$30[0-9A-Fa-f]{4}\b",
    re.IGNORECASE | re.MULTILINE,
)
_GROUP_CALL_RE: Final = re.compile(
    r"^\s*%EpochSha256Round8_Group\((?P<args>[^)\r\n]+)\)\s*$",
    re.MULTILINE,
)
_ROUND_CALL_RE: Final = re.compile(
    r"^\s*%EpochSha256Round8_Round\((?P<args>[^)\r\n]+)\)\s*$",
    re.MULTILINE,
)
_HEX_RE: Final = re.compile(r"^\$([0-9A-Fa-f]{1,4})$")
_SYMBOL_RE: Final = re.compile(
    r"^(?P<address>[0-9A-Fa-f]{8})\s+"
    r"(?P<label>[A-Za-z_:?.][A-Za-z0-9_:?.]*)$"
)


class Round8Sha256Error(ValueError):
    """Raised when the round8/table source violates its bounded contract."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_comments(source: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in source.splitlines())


def _section(source: str, start: str, end: str) -> str:
    try:
        return source.split(f"{start}:", 1)[1].split(f"{end}:", 1)[0]
    except IndexError as exc:
        raise Round8Sha256Error(
            f"missing source section {start}/{end}"
        ) from exc


def _macro_body(source: str, name: str) -> str:
    pattern = re.compile(
        rf"^macro\s+{re.escape(name)}\([^)]*\)\s*$"
        rf"(?P<body>.*?)^endmacro\s*$",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(source)
    if match is None:
        raise Round8Sha256Error(f"missing macro {name}")
    return match.group("body")


def _parse_hex(token: str, field: str) -> int:
    match = _HEX_RE.fullmatch(token.strip())
    if match is None:
        raise Round8Sha256Error(f"{field} is not an exact hex literal")
    return int(match.group(1), 16)


def validate_frozen_inputs() -> dict[str, str]:
    result = fast.validate_baseline_unchanged()
    for path, expected in FROZEN_INPUT_HASHES.items():
        actual = sha256(path.read_bytes())
        if actual != expected:
            raise Round8Sha256Error(f"frozen input changed: {path}")
        result[path.relative_to(ROOT).as_posix()] = actual
    return result


def parse_round_constants(
    source: str | None = None,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    calls = _GROUP_CALL_RE.findall(_strip_comments(source))
    if len(calls) != GROUP_COUNT:
        raise Round8Sha256Error(
            f"expected {GROUP_COUNT} group calls, got {len(calls)}"
        )
    bases: list[int] = []
    constants: list[int] = []
    for group_index, call in enumerate(calls):
        args = tuple(item.strip() for item in call.split(","))
        if len(args) != 17:
            raise Round8Sha256Error(
                f"group {group_index} has {len(args)} arguments"
            )
        base_value = _parse_hex(args[0], f"group {group_index} base")
        bases.append(base_value)
        for pair in range(8):
            high = _parse_hex(
                args[1 + pair * 2],
                f"group {group_index} K{pair} high",
            )
            low = _parse_hex(
                args[2 + pair * 2],
                f"group {group_index} K{pair} low",
            )
            constants.append((high << 16) | low)
    expected_bases = tuple(range(0, ROUND_COUNT, ROUNDS_PER_GROUP))
    if tuple(bases) != expected_bases:
        raise Round8Sha256Error("eight-round group bases changed")
    _, baseline_constants = baseline.parse_assembly_constants()
    expected_constants = tuple(
        (high << 16) | low for high, low in baseline_constants
    )
    if tuple(constants) != expected_constants:
        raise Round8Sha256Error("compile-time K constants differ from baseline")
    return tuple(bases), tuple(constants)


def validate_symbolic_group_mapping(
    source: str | None = None,
) -> tuple[tuple[str, ...], ...]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    body = _macro_body(source, "EpochSha256Round8_Group")
    calls = _ROUND_CALL_RE.findall(_strip_comments(body))
    if len(calls) != ROUNDS_PER_GROUP:
        raise Round8Sha256Error("group macro must emit exactly eight rounds")
    states = (
        ("!PE_SHA_A", "!PE_SHA_B", "!PE_SHA_C", "!PE_SHA_D",
         "!PE_SHA_E", "!PE_SHA_F", "!PE_SHA_G", "!PE_SHA_H"),
        ("!PE_SHA_H", "!PE_SHA_A", "!PE_SHA_B", "!PE_SHA_C",
         "!PE_SHA_D", "!PE_SHA_E", "!PE_SHA_F", "!PE_SHA_G"),
        ("!PE_SHA_G", "!PE_SHA_H", "!PE_SHA_A", "!PE_SHA_B",
         "!PE_SHA_C", "!PE_SHA_D", "!PE_SHA_E", "!PE_SHA_F"),
        ("!PE_SHA_F", "!PE_SHA_G", "!PE_SHA_H", "!PE_SHA_A",
         "!PE_SHA_B", "!PE_SHA_C", "!PE_SHA_D", "!PE_SHA_E"),
        ("!PE_SHA_E", "!PE_SHA_F", "!PE_SHA_G", "!PE_SHA_H",
         "!PE_SHA_A", "!PE_SHA_B", "!PE_SHA_C", "!PE_SHA_D"),
        ("!PE_SHA_D", "!PE_SHA_E", "!PE_SHA_F", "!PE_SHA_G",
         "!PE_SHA_H", "!PE_SHA_A", "!PE_SHA_B", "!PE_SHA_C"),
        ("!PE_SHA_C", "!PE_SHA_D", "!PE_SHA_E", "!PE_SHA_F",
         "!PE_SHA_G", "!PE_SHA_H", "!PE_SHA_A", "!PE_SHA_B"),
        ("!PE_SHA_B", "!PE_SHA_C", "!PE_SHA_D", "!PE_SHA_E",
         "!PE_SHA_F", "!PE_SHA_G", "!PE_SHA_H", "!PE_SHA_A"),
    )
    parsed_states: list[tuple[str, ...]] = []
    for index, call in enumerate(calls):
        args = tuple(item.strip() for item in call.split(","))
        if len(args) != 11:
            raise Round8Sha256Error(
                f"round mapping {index} has {len(args)} arguments"
            )
        if args[0] != f"<base>+${index:02X}":
            raise Round8Sha256Error(f"round {index} compile-time index changed")
        if args[1:9] != states[index]:
            raise Round8Sha256Error(f"round {index} symbolic mapping changed")
        if args[9:] != (f"<k{index}h>", f"<k{index}l>"):
            raise Round8Sha256Error(f"round {index} K mapping changed")
        parsed_states.append(args[1:9])
    return tuple(parsed_states)


def _normalized_section(
    source: str,
    start: str,
    end: str,
    prefix: str,
) -> tuple[str, ...]:
    body = _section(source, start, end).replace(
        "EpochSha256Round8_", prefix
    )
    return tuple(
        " ".join(line.split())
        for line in _strip_comments(body).splitlines()
        if line.strip()
    )


def validate_table_consumer(source: str | None = None) -> dict[str, object]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    body = _strip_comments(
        _macro_body(source, "EpochSha256Round8_TableSigma")
    )
    indexed_loads = re.findall(
        r"LDA\.w\s+!PE_SHA256_SCRATCH_LO"
        r"(?P<offset>\+\$0000|\+\$0002),Y",
        body,
    )
    if indexed_loads != ["+$0000", "+$0000", "+$0002", "+$0002"]:
        raise Round8Sha256Error("table consumer byte-source order changed")
    if body.count("XBA") != 2:
        raise Round8Sha256Error("table consumer must swap Byte0 and Byte2")
    for token, count in (
        ("AND.w #$00FF", 4),
        ("ASL A", 8),
        ("TAX", 4),
        ("LDA.l <byte0>,X", 1),
        ("LDA.l <byte0>+$0002,X", 1),
        ("LDA.l <byte1>,X", 1),
        ("LDA.l <byte1>+$0002,X", 1),
        ("LDA.l <byte2>,X", 1),
        ("LDA.l <byte2>+$0002,X", 1),
        ("LDA.l <byte3>,X", 1),
        ("LDA.l <byte3>+$0002,X", 1),
    ):
        if body.count(token) != count:
            raise Round8Sha256Error(
                f"table consumer token count changed: {token}"
            )
    expected_calls = {
        name: (
            f"%EpochSha256Round8_TableSigma("
            f"EpochSha256SigmaTables_{name}_Byte0, "
            f"EpochSha256SigmaTables_{name}_Byte1, "
            f"EpochSha256SigmaTables_{name}_Byte2, "
            f"EpochSha256SigmaTables_{name}_Byte3)"
        )
        for name, _ in sigma_tables.TRANSFORMS
    }
    for name, token in expected_calls.items():
        if source.count(token) != 1:
            raise Round8Sha256Error(f"{name} table binding changed")
    report = sigma_tables.check_include(TABLE_PATH)
    if report["binary_table_size"] != TABLE_SIZE:
        raise Round8Sha256Error("generated table payload size changed")
    return {
        "include_sha256": report["output_sha256"],
        "table_bytes": report["binary_table_size"],
        "transform_count": len(sigma_tables.TRANSFORMS),
        "basis_entries": (
            len(sigma_tables.TRANSFORMS)
            * sigma_tables.BYTE_COUNT
            * sigma_tables.BYTE_VALUES
        ),
    }


def profile1_final_block_from_source(
    slot_number: int,
    source: str | None = None,
) -> bytes:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    adapted = source.replace(
        "EpochSha256Round8_LoadProfile1FinalBlock",
        "EpochSha256_LoadProfile1FinalBlock",
    ).replace(
        "EpochSha256Round8_CompressBlock",
        "EpochSha256_CompressBlock",
    )
    return baseline.profile1_final_block_from_source(slot_number, adapted)


def validate_source_contract(source: str | None = None) -> dict[str, object]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    code = _strip_comments(source)
    if _FORBIDDEN_DIRECTIVE_RE.search(code):
        raise Round8Sha256Error("round8 core contains placement directive")
    if _BANK30_WRITE_RE.search(code):
        raise Round8Sha256Error("round8 core contains bank-$30 write")
    if "$7E2CA0" in code.upper():
        raise Round8Sha256Error("round8 core claims compatibility WRAM")
    for token in (
        "EpochSha256Round8_Profile1Digest:",
        "EpochSha256Round8_CompressBlock:",
        "EpochSha256Round8_BigSigma0:",
        "EpochSha256Round8_BigSigma1:",
        "EpochSha256Round8_SmallSigma0:",
        "EpochSha256Round8_SmallSigma1:",
        "!PE_SHA256_SCRATCH_SIZE = $00C2",
        "LDA.l $300000,X",
        "CMP.w #$0028",
        "LDA.w #$5080",
        "PHP",
        "CLD",
        "PLP",
        "assert EpochSha256Round8_SourceEnd-"
        "EpochSha256Round8_SourceStart <= $6000",
    ):
        if token not in source:
            raise Round8Sha256Error(f"round8 source token missing: {token}")
    if "EpochSha256Round8_K:" in source:
        raise Round8Sha256Error("round8 source retains runtime K table")
    if re.search(r"\b(?:INC|STA|LDA)\.w[^\r\n]*!PE_SHA_ROUND\b", code):
        raise Round8Sha256Error("round8 source retains runtime round traffic")

    bases, constants = parse_round_constants(source)
    states = validate_symbolic_group_mapping(source)
    for group in range(GROUP_COUNT):
        start = f"EpochSha256Round8_Group{group:02d}_Start:"
        end = f"EpochSha256Round8_Group{group:02d}_End:"
        if source.count(start) != 1 or source.count(end) != 1:
            raise Round8Sha256Error(f"group {group} labels changed")
        if source.index(start) >= source.index(end):
            raise Round8Sha256Error(f"group {group} label order changed")

    baseline_source = baseline.ASM_PATH.read_text(encoding="utf-8")
    entry = _normalized_section(
        source,
        "EpochSha256Round8_Profile1Digest",
        "EpochSha256Round8_CompressBlock",
        "EpochSha256_",
    )
    baseline_entry = _normalized_section(
        baseline_source,
        "EpochSha256_Profile1Digest",
        "EpochSha256_CompressBlock",
        "EpochSha256_",
    )
    if entry != baseline_entry:
        raise Round8Sha256Error(
            "entry, validation, load, or final-block code differs from baseline"
        )
    emitter = _normalized_section(
        source,
        "EpochSha256Round8_EmitDigest",
        "EpochSha256Round8_InitialState",
        "EpochSha256_",
    )
    baseline_emitter = _normalized_section(
        baseline_source,
        "EpochSha256_EmitDigest",
        "EpochSha256_InitialState",
        "EpochSha256_",
    )
    if emitter != baseline_emitter:
        raise Round8Sha256Error("round8 digest emitter differs from baseline")
    initial = baseline._table_words(  # noqa: SLF001
        source,
        "EpochSha256Round8_InitialState",
        "EpochSha256Round8_InitialState_End",
    )
    baseline_initial, _ = baseline.parse_assembly_constants()
    if initial != baseline_initial:
        raise Round8Sha256Error("round8 initial state differs from baseline")

    for slot_number in range(1, 4):
        final_block = profile1_final_block_from_source(slot_number, source)
        if final_block[:16] != baseline.binding_trailer(slot_number):
            raise Round8Sha256Error("round8 source trailer mismatch")
        if final_block[16:56] != b"\x80" + bytes(39):
            raise Round8Sha256Error("round8 source padding mismatch")
        if final_block[56:] != (
            baseline.PROFILE_MESSAGE_SIZE * 8
        ).to_bytes(8, "big"):
            raise Round8Sha256Error("round8 source length mismatch")

    table_report = validate_table_consumer(source)
    return {
        "source_sha256": sha256(source.encode("utf-8")),
        "scratch_size": SCRATCH_SIZE,
        "code_limit": CODE_LIMIT,
        "table_bytes": table_report["table_bytes"],
        "entry_save_frame_size": ENTRY_SAVE_FRAME_SIZE,
        "max_nested_jsr_count": MAX_NESTED_JSR_COUNT,
        "max_stack_growth_after_entry": MAX_STACK_GROWTH_AFTER_ENTRY,
        "max_stack_growth_with_caller_jsl": (
            MAX_STACK_GROWTH_WITH_CALLER_JSL
        ),
        "rounds": len(constants),
        "groups": len(bases),
        "rounds_per_group": len(states),
        "runtime_k_table_bytes": 0,
        "runtime_round_counter_traffic": False,
        "placed": False,
        "writes_bank_30": False,
        "table_include_sha256": table_report["include_sha256"],
    }


def validate_benchmark_wrapper() -> dict[str, object]:
    baseline_source = FAST_BENCHMARK_PATH.read_text(encoding="utf-8")
    round8_source = BENCHMARK_PATH.read_text(encoding="utf-8")
    normalized = round8_source
    replacements = (
        (
            "; Project Epoch standalone round8/table SHA-256 "
            "profile-1 benchmark.",
            "; Project Epoch standalone optimized SHA-256 "
            "profile-1 benchmark.",
        ),
        ("EPOCH SHA256 R8TABLE ", "EPOCH SHA256 FAST    "),
        (
            "EpochSha256Round8_Profile1Digest",
            "EpochSha256Fast_Profile1Digest",
        ),
        (
            "schala_sidecar_sha256_profile1_round8.asm",
            "schala_sidecar_sha256_profile1_fast.asm",
        ),
        ("assert Benchmark_CoreEnd <= $416000",
         "assert Benchmark_CoreEnd <= $420000"),
        ("assert Benchmark_DataEnd-Benchmark_DataStart == $4060",
         "assert Benchmark_DataEnd-Benchmark_DataStart == $0060"),
    )
    for old, new in replacements:
        if old not in normalized:
            raise Round8Sha256Error(
                f"benchmark normalization token missing: {old}"
            )
        normalized = normalized.replace(old, new)
    table_block = (
        "\nBenchmark_SigmaTablesStart:\n"
        'incsrc "schala_sidecar_sha256_sigma_tables.asm"\n'
        "Benchmark_SigmaTablesEnd:\n"
    )
    if normalized.count(table_block) != 1:
        raise Round8Sha256Error("benchmark table include block changed")
    normalized = normalized.replace(table_block, "")
    table_asserts = (
        "assert Benchmark_SigmaTablesEnd-"
        "Benchmark_SigmaTablesStart == $4000\n"
        "assert bank(Benchmark_SigmaTablesStart) == $42\n"
        "assert bank(Benchmark_SigmaTablesEnd-1) == $42\n"
    )
    if normalized.count(table_asserts) != 1:
        raise Round8Sha256Error("benchmark table assertions changed")
    normalized = normalized.replace(table_asserts, "")
    if normalized != baseline_source:
        raise Round8Sha256Error(
            "round8 benchmark differs outside approved substitutions"
        )
    if round8_source.count("JSL EpochSha256Round8_Profile1Digest") != 2:
        raise Round8Sha256Error("benchmark must contain exactly two entry calls")
    return {
        "source_sha256": sha256(round8_source.encode("utf-8")),
        "entry_calls": 2,
        "result_address": 0x7E5F00,
        "expected_vector_bytes": 0x60,
        "sigma_table_bytes": TABLE_SIZE,
        "data_span_bytes": 0x4060,
        "equivalent_after_approved_substitutions": True,
    }


def _add32(*values: int) -> int:
    return sum(values) & WORD_MASK


def sha256_round8_source_model(message: bytes) -> bytes:
    if type(message) is not bytes:
        raise Round8Sha256Error("message must be exact bytes")
    source = ASM_PATH.read_text(encoding="utf-8")
    _, constants = parse_round_constants(source)
    initial_words = baseline._table_words(  # noqa: SLF001
        source,
        "EpochSha256Round8_InitialState",
        "EpochSha256Round8_InitialState_End",
    )
    state = [((high << 16) | low) for high, low in initial_words]
    tables = sigma_tables.generate_tables()

    bit_length = len(message) * 8
    padded = bytearray(message)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0)
    padded.extend(bit_length.to_bytes(8, "big"))

    for block_start in range(0, len(padded), 64):
        block = padded[block_start : block_start + 64]
        schedule = [
            int.from_bytes(block[index : index + 4], "big")
            for index in range(0, 64, 4)
        ]
        work = list(state)
        for round_number, constant in enumerate(constants):
            if round_number >= 16:
                target = round_number & 0x0F
                schedule[target] = _add32(
                    schedule[target],
                    sigma_tables.reconstruct(
                        "SmallSigma0",
                        schedule[(round_number + 1) & 0x0F],
                        tables,
                    ),
                    schedule[(round_number + 9) & 0x0F],
                    sigma_tables.reconstruct(
                        "SmallSigma1",
                        schedule[(round_number + 14) & 0x0F],
                        tables,
                    ),
                )
            a, b, c, d, e, f, g, h = work
            choose = ((e & f) ^ ((~e) & g)) & WORD_MASK
            majority = ((a & b) ^ (a & c) ^ (b & c)) & WORD_MASK
            t1 = _add32(
                h,
                sigma_tables.reconstruct("BigSigma1", e, tables),
                choose,
                constant,
                schedule[round_number & 0x0F],
            )
            t2 = _add32(
                sigma_tables.reconstruct("BigSigma0", a, tables),
                majority,
            )
            work = [
                _add32(t1, t2),
                a,
                b,
                c,
                _add32(d, t1),
                e,
                f,
                g,
            ]
        state = [_add32(left, right) for left, right in zip(state, work)]
    return b"".join(value.to_bytes(4, "big") for value in state)


def profile1_digest_model(serialized_slot: bytes, slot_number: int) -> bytes:
    if type(serialized_slot) is not bytes:
        raise Round8Sha256Error("serialized_slot must be exact bytes")
    if len(serialized_slot) != baseline.SLOT_SIZE:
        raise Round8Sha256Error("serialized_slot must be exactly $0A00 bytes")
    return sha256_round8_source_model(
        serialized_slot + baseline.binding_trailer(slot_number)
    )


def verify_digest_vectors() -> dict[str, object]:
    standard = (b"", b"abc", b"a" * 55, b"a" * 56, bytes(range(256)))
    for message in standard:
        if sha256_round8_source_model(message) != hashlib.sha256(
            message
        ).digest():
            raise Round8Sha256Error(
                f"round8 digest model mismatch at length {len(message)}"
            )
    patterns = (
        bytes(baseline.SLOT_SIZE),
        bytes(index & 0xFF for index in range(baseline.SLOT_SIZE)),
        bytes(
            (index * 73 + 19) & 0xFF
            for index in range(baseline.SLOT_SIZE)
        ),
    )
    profile_vectors: dict[str, tuple[str, ...]] = {}
    for pattern_index, serialized in enumerate(patterns):
        digests = []
        for slot_number in range(1, 4):
            actual = profile1_digest_model(serialized, slot_number)
            expected = hashlib.sha256(
                serialized + baseline.binding_trailer(slot_number)
            ).digest()
            if actual != expected:
                raise Round8Sha256Error(
                    f"profile vector mismatch pattern {pattern_index}, "
                    f"slot {slot_number}"
                )
            digests.append(actual.hex())
        if len(set(digests)) != 3:
            raise Round8Sha256Error("profile digests are not slot-bound")
        profile_vectors[str(pattern_index)] = tuple(digests)
    return {
        "standard_vectors": len(standard),
        "profile_vectors": len(patterns) * 3,
        "profiles": profile_vectors,
    }


def _parse_symbols(source: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in source.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("[")
            or stripped.startswith(";")
        ):
            continue
        match = _SYMBOL_RE.fullmatch(stripped)
        if match is None:
            raise Round8Sha256Error(f"unrecognized symbol line: {stripped}")
        label = match.group("label")
        if label in result:
            raise Round8Sha256Error(f"duplicate Asar symbol: {label}")
        result[label] = int(match.group("address"), 16)
    return result


def run_asar_syntax(
    asar_path: pathlib.Path = DEFAULT_ASAR_PATH,
) -> dict[str, object]:
    asar_path = asar_path.resolve()
    if not asar_path.is_file():
        raise Round8Sha256Error(f"Asar executable not found: {asar_path}")
    PRIVATE_TEMP_PARENT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="sha256_65816_round8_syntax_",
        dir=PRIVATE_TEMP_PARENT,
    ) as temporary:
        temporary_path = pathlib.Path(temporary)
        output_path = temporary_path / "round8_syntax_probe.bin"
        symbol_path = temporary_path / "round8_syntax_probe.sym"
        result = subprocess.run(
            (
                str(asar_path),
                "--no-title-check",
                "--fix-checksum=off",
                "--symbols=nocash",
                f"--symbols-path={symbol_path}",
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
            raise Round8Sha256Error(
                "round8 Asar syntax failed:\n"
                + result.stdout
                + result.stderr
            )
        assembled = output_path.read_bytes()
        symbols = _parse_symbols(symbol_path.read_text(encoding="ascii"))
        code_start = symbols["EpochSha256Round8_SourceStart"]
        code_end = symbols["EpochSha256Round8_SourceEnd"]
        table_start = symbols["EpochSha256SigmaTables_Start"]
        table_end = symbols["EpochSha256SigmaTables_End"]
        if not 0 < code_end - code_start <= CODE_LIMIT:
            raise Round8Sha256Error("assembled round8 code exceeds bound")
        if table_end - table_start != TABLE_SIZE:
            raise Round8Sha256Error("assembled sigma tables have wrong size")
        if code_start >> 16 != (code_end - 1) >> 16:
            raise Round8Sha256Error("assembled round8 code crosses bank")
        if table_start >> 16 != (table_end - 1) >> 16:
            raise Round8Sha256Error("assembled sigma tables cross bank")
        for group in range(GROUP_COUNT):
            start = symbols[f"EpochSha256Round8_Group{group:02d}_Start"]
            end = symbols[f"EpochSha256Round8_Group{group:02d}_End"]
            if not start < end:
                raise Round8Sha256Error(f"assembled group {group} is empty")
        probe = {
            "asar_sha256": sha256(asar_path.read_bytes()),
            "assembled_size": len(assembled),
            "assembled_sha256": sha256(assembled),
            "code_size": code_end - code_start,
            "table_size": table_end - table_start,
            "code_start": code_start,
            "table_start": table_start,
            "group_sizes": tuple(
                symbols[f"EpochSha256Round8_Group{group:02d}_End"]
                - symbols[f"EpochSha256Round8_Group{group:02d}_Start"]
                for group in range(GROUP_COUNT)
            ),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    if output_path.exists() or symbol_path.exists():
        raise Round8Sha256Error("round8 syntax artifacts were not deleted")
    return probe


def validate(
    asar_path: pathlib.Path | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "evidence": "source-only-host-model",
        "frozen_inputs": validate_frozen_inputs(),
        "source": validate_source_contract(),
        "benchmark_wrapper": validate_benchmark_wrapper(),
        "digests": verify_digest_vectors(),
    }
    if asar_path is not None:
        result["asar_syntax"] = run_asar_syntax(asar_path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asar", type=pathlib.Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(validate(args.asar), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
