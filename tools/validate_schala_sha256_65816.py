#!/usr/bin/env python3
"""Validate the source-only 65C816 SHA-256 profile-1 prototype.

The host model mirrors the assembly's 16-bit high/low lane arithmetic and
16-word circular schedule.  It is deterministic source evidence, not proof
that the assembled routine executes correctly or meets a runtime cycle budget.

No Chrono Trigger ROM is read or written.  The optional Asar check assembles
only the raw ``norom`` syntax wrapper into a temporary private binary and
deletes that binary before returning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile
from collections.abc import Sequence
from typing import Final


ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
ASM_PATH: Final = ROOT / "asm" / "schala_sidecar_sha256_profile1.asm"
SYNTAX_WRAPPER_PATH: Final = (
    ROOT / "asm" / "schala_sidecar_sha256_profile1_syntax.asm"
)
DEFAULT_ASAR_PATH: Final = (
    ROOT / "private" / "tools" / "asar-1.91" / "asar.exe"
)
PRIVATE_TEMP_PARENT: Final = ROOT / "private" / "build"

SLOT_SIZE: Final = 0x0A00
PROFILE_MESSAGE_SIZE: Final = 0x0A10
PROFILE_BLOCK_COUNT: Final = 41
BINDING_TRAILER_TAG: Final = b"PE07BIND"
VERSION: Final = 2
BINDING_PROFILE: Final = 1
SCRATCH_SIZE: Final = 0x00C2
ENTRY_SAVE_FRAME_SIZE: Final = 10
MAX_NESTED_JSR_COUNT: Final = 3
MAX_STACK_GROWTH_AFTER_ENTRY: Final = 16
MAX_STACK_GROWTH_WITH_CALLER_JSL: Final = 19

EXPECTED_ZERO_SLOT_DIGESTS: Final = {
    1: "878829ba5210cd4d1defacbedb6c485407a25dc8be2cf46ae2bd90636b9ebdbd",
    2: "45351b0ff714359ed22d687605b843658bf8ce3e2d997199ce0077323cde00b5",
    3: "716b7eb41aa41f3febfb7843cb18174a01ba869cf2a634b0fe53f0d58cdd59b2",
}

_WORD_RE: Final = re.compile(r"\bdw\s+\$([0-9A-Fa-f]{4}),\$([0-9A-Fa-f]{4})")
_SCRATCH_RE: Final = re.compile(
    r"^!PE_SHA256_SCRATCH_SIZE\s*=\s*\$([0-9A-Fa-f]{4})\s*$",
    re.MULTILINE,
)
_FINAL_LITERAL_STORE_RE: Final = re.compile(
    r"LDA\.w\s+#\$([0-9A-Fa-f]{4})\s*"
    r"STA\.w\s+!PE_SHA256_SCRATCH_LO\+!PE_SHA_W\+\$([0-9A-Fa-f]{2})",
    re.MULTILINE,
)
_FORBIDDEN_DIRECTIVE_RE: Final = re.compile(
    r"^\s*(?:org|lorom|hirom|exhirom|norom|incbin|autoclean)\b",
    re.IGNORECASE | re.MULTILINE,
)
_BANK30_WRITE_RE: Final = re.compile(
    r"^\s*(?:sta|stx|sty|stz)\b[^;\r\n]*\$30[0-9A-Fa-f]{4}\b",
    re.IGNORECASE | re.MULTILINE,
)


class Sha256PrototypeError(ValueError):
    """Raised when source or vector invariants fail closed."""


Word = tuple[int, int]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def binding_trailer(slot_number: int) -> bytes:
    if type(slot_number) is not int or not 1 <= slot_number <= 3:
        raise Sha256PrototypeError("slot_number must be exact integer 1..3")
    trailer = (
        BINDING_TRAILER_TAG
        + bytes((VERSION, BINDING_PROFILE, slot_number, 0))
        + SLOT_SIZE.to_bytes(2, "little")
        + b"\x00\x00"
    )
    if len(trailer) != 0x10:
        raise AssertionError("profile-1 trailer must be 16 bytes")
    return trailer


def _strip_comments(source: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in source.splitlines())


def _table_words(source: str, start_label: str, end_label: str) -> tuple[Word, ...]:
    try:
        body = source.split(f"{start_label}:", 1)[1].split(
            f"{end_label}:", 1
        )[0]
    except IndexError as exc:
        raise Sha256PrototypeError(
            f"missing assembly table bounds {start_label}/{end_label}"
        ) from exc
    return tuple(
        (int(high, 16), int(low, 16))
        for high, low in _WORD_RE.findall(body)
    )


def parse_assembly_constants(
    source: str | None = None,
) -> tuple[tuple[Word, ...], tuple[Word, ...]]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    initial = _table_words(
        source,
        "EpochSha256_InitialState",
        "EpochSha256_InitialState_End",
    )
    constants = _table_words(
        source,
        "EpochSha256_K",
        "EpochSha256_K_End",
    )
    if len(initial) != 8:
        raise Sha256PrototypeError(
            f"assembly initial state has {len(initial)} words, expected 8"
        )
    if len(constants) != 64:
        raise Sha256PrototypeError(
            f"assembly K table has {len(constants)} words, expected 64"
        )
    return initial, constants


def profile1_final_block_from_source(
    slot_number: int,
    source: str | None = None,
) -> bytes:
    """Reconstruct conceptual SHA bytes from the source's numeric W halves."""

    binding_trailer(slot_number)
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    try:
        body = source.split(
            "EpochSha256_LoadProfile1FinalBlock:",
            1,
        )[1].split("EpochSha256_CompressBlock:", 1)[0]
    except IndexError as exc:
        raise Sha256PrototypeError(
            "missing final-block assembly routine bounds"
        ) from exc
    halves = [0] * 32
    for value_hex, offset_hex in _FINAL_LITERAL_STORE_RE.findall(body):
        offset = int(offset_hex, 16)
        if offset & 1 or not 0 <= offset < 64:
            raise Sha256PrototypeError(
                f"invalid final-block half offset 0x{offset:02X}"
            )
        halves[offset // 2] = int(value_hex, 16)

    # The only dynamic half is bytes {physical_slot, $00}.  The assembly
    # realizes this numeric big-endian half with LDA slot / XBA / STA W+$0A.
    dynamic_tokens = (
        "LDA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_SLOT",
        "XBA",
        "STA.w !PE_SHA256_SCRATCH_LO+!PE_SHA_W+$0A",
    )
    position = 0
    for token in dynamic_tokens:
        position = body.find(token, position)
        if position < 0:
            raise Sha256PrototypeError(
                "final block does not encode slot/zero through XBA"
            )
        position += len(token)
    halves[0x0A // 2] = slot_number << 8
    return b"".join(value.to_bytes(2, "big") for value in halves)


def validate_source_contract(source: str | None = None) -> dict[str, object]:
    if source is None:
        source = ASM_PATH.read_text(encoding="utf-8")
    code = _strip_comments(source)
    match = _SCRATCH_RE.search(code)
    if match is None or int(match.group(1), 16) != SCRATCH_SIZE:
        raise Sha256PrototypeError("assembly scratch-size contract is not $00C2")
    if _FORBIDDEN_DIRECTIVE_RE.search(code):
        raise Sha256PrototypeError(
            "relocatable SHA source contains a placement/write directive"
        )
    if _BANK30_WRITE_RE.search(code):
        raise Sha256PrototypeError("SHA source contains a bank-$30 write")
    if "$7E2CA0" in code.upper():
        raise Sha256PrototypeError("SHA source claims the compatibility candidate")
    for token in (
        "EpochSha256_Profile1Digest:",
        "EpochSha256_CompressBlock:",
        "EpochSha256_EmitDigest:",
        "PHP",
        "CLD",
        "PHB",
        "PHD",
        "PLD",
        "PLB",
        "PLP",
        "LDA.l $300000,X",
        "CMP.w #$0028",
        "LDA.w #$5080",
    ):
        if token not in source:
            raise Sha256PrototypeError(f"assembly contract token missing: {token}")
    prologue = re.compile(
        r"EpochSha256_Profile1Digest:\s*PHP\s*REP\s+#\$30\s*CLD",
        re.MULTILINE,
    )
    if prologue.search(code) is None:
        raise Sha256PrototypeError(
            "entry must force binary arithmetic after preserving caller P"
        )
    initial, constants = parse_assembly_constants(source)
    for slot_number in range(1, 4):
        final_block = profile1_final_block_from_source(slot_number, source)
        if final_block[:0x10] != binding_trailer(slot_number):
            raise Sha256PrototypeError(
                f"source final-block trailer mismatch for slot {slot_number}"
            )
        if final_block[0x10:0x38] != b"\x80" + bytes(0x27):
            raise Sha256PrototypeError(
                "source final block has incorrect padding prefix"
            )
        if final_block[0x38:] != (PROFILE_MESSAGE_SIZE * 8).to_bytes(
            8,
            "big",
        ):
            raise Sha256PrototypeError(
                "source final block has incorrect 64-bit message length"
            )
    return {
        "source_sha256": sha256(source.encode("utf-8")),
        "scratch_size": SCRATCH_SIZE,
        "initial_word_count": len(initial),
        "round_constant_count": len(constants),
        "profile_block_count": PROFILE_BLOCK_COUNT,
        "entry_save_frame_size": ENTRY_SAVE_FRAME_SIZE,
        "max_nested_jsr_count": MAX_NESTED_JSR_COUNT,
        "max_stack_growth_after_entry": MAX_STACK_GROWTH_AFTER_ENTRY,
        "max_stack_growth_with_caller_jsl": MAX_STACK_GROWTH_WITH_CALLER_JSL,
        "writes_bank_30": False,
        "placed": False,
    }


def _require_word(word: Word) -> Word:
    high, low = word
    if not 0 <= high <= 0xFFFF or not 0 <= low <= 0xFFFF:
        raise Sha256PrototypeError("16-bit lane is out of range")
    return high, low


def _add32(*words: Word) -> Word:
    high = 0
    low = 0
    for operand_high, operand_low in map(_require_word, words):
        low_total = low + operand_low
        low = low_total & 0xFFFF
        high = (high + operand_high + (low_total >> 16)) & 0xFFFF
    return high, low


def _rotr(word: Word, count: int) -> Word:
    high, low = _require_word(word)
    for _ in range(count):
        old_low_bit = low & 1
        old_high_bit = high & 1
        high = (high >> 1) | (old_low_bit << 15)
        low = (low >> 1) | (old_high_bit << 15)
    return high, low


def _shr(word: Word, count: int) -> Word:
    high, low = _require_word(word)
    for _ in range(count):
        old_high_bit = high & 1
        high >>= 1
        low = (low >> 1) | (old_high_bit << 15)
    return high, low


def _xor(*words: Word) -> Word:
    high = 0
    low = 0
    for operand_high, operand_low in map(_require_word, words):
        high ^= operand_high
        low ^= operand_low
    return high, low


def _choice(e: Word, f: Word, g: Word) -> Word:
    return (
        g[0] ^ (e[0] & (f[0] ^ g[0])),
        g[1] ^ (e[1] & (f[1] ^ g[1])),
    )


def _majority(a: Word, b: Word, c: Word) -> Word:
    return (
        (a[0] & b[0]) | (c[0] & (a[0] | b[0])),
        (a[1] & b[1]) | (c[1] & (a[1] | b[1])),
    )


def _big_sigma0(word: Word) -> Word:
    return _xor(_rotr(word, 2), _rotr(word, 13), _rotr(word, 22))


def _big_sigma1(word: Word) -> Word:
    return _xor(_rotr(word, 6), _rotr(word, 11), _rotr(word, 25))


def _small_sigma0(word: Word) -> Word:
    return _xor(_rotr(word, 7), _rotr(word, 18), _shr(word, 3))


def _small_sigma1(word: Word) -> Word:
    return _xor(_rotr(word, 17), _rotr(word, 19), _shr(word, 10))


def _word_from_bytes(data: bytes) -> Word:
    if len(data) != 4:
        raise Sha256PrototypeError("SHA word source must be four bytes")
    return int.from_bytes(data[:2], "big"), int.from_bytes(data[2:], "big")


def _word_to_bytes(word: Word) -> bytes:
    high, low = _require_word(word)
    return high.to_bytes(2, "big") + low.to_bytes(2, "big")


def sha256_16bit_lane_model(message: bytes) -> bytes:
    """Return SHA-256 using the assembly prototype's 16-bit lane structure."""

    if type(message) is not bytes:
        raise Sha256PrototypeError("message must be exact immutable bytes")
    if len(message) >= 1 << 61:
        raise Sha256PrototypeError("message length does not fit SHA-256 field")
    initial, constants = parse_assembly_constants()
    state = list(initial)
    bit_length = len(message) * 8
    padded = bytearray(message)
    padded.append(0x80)
    padded.extend(b"\x00" * ((56 - len(padded) % 64) % 64))
    padded.extend(bit_length.to_bytes(8, "big"))

    for block_start in range(0, len(padded), 64):
        block = bytes(padded[block_start : block_start + 64])
        schedule = [
            _word_from_bytes(block[index : index + 4])
            for index in range(0, 64, 4)
        ]
        a, b, c, d, e, f, g, h = state
        for round_index in range(64):
            circular_index = round_index & 15
            if round_index >= 16:
                schedule[circular_index] = _add32(
                    schedule[circular_index],
                    _small_sigma0(schedule[(round_index + 1) & 15]),
                    schedule[(round_index + 9) & 15],
                    _small_sigma1(schedule[(round_index + 14) & 15]),
                )
            t1 = _add32(
                h,
                _big_sigma1(e),
                _choice(e, f, g),
                constants[round_index],
                schedule[circular_index],
            )
            t2 = _add32(_big_sigma0(a), _majority(a, b, c))
            h, g, f = g, f, e
            e = _add32(d, t1)
            d, c, b = c, b, a
            a = _add32(t1, t2)
        state = [
            _add32(old, new)
            for old, new in zip(
                state,
                (a, b, c, d, e, f, g, h),
                strict=True,
            )
        ]
    return b"".join(map(_word_to_bytes, state))


def profile1_digest_model(serialized_slot: bytes, slot_number: int) -> bytes:
    if type(serialized_slot) is not bytes or len(serialized_slot) != SLOT_SIZE:
        raise Sha256PrototypeError("serialized_slot must be exact $0A00 bytes")
    message = serialized_slot + binding_trailer(slot_number)
    if len(message) != PROFILE_MESSAGE_SIZE:
        raise AssertionError("profile-1 message length drifted")
    return sha256_16bit_lane_model(message)


def verify_vectors() -> dict[str, object]:
    standard_messages = (b"", b"abc", bytes(range(256)))
    for message in standard_messages:
        modeled = sha256_16bit_lane_model(message)
        expected = hashlib.sha256(message).digest()
        if modeled != expected:
            raise Sha256PrototypeError(
                f"lane model disagrees with hashlib for {message[:8]!r}"
            )

    zero_slot = bytes(SLOT_SIZE)
    zero_vectors: dict[str, str] = {}
    for slot_number in range(1, 4):
        modeled = profile1_digest_model(zero_slot, slot_number).hex()
        direct = hashlib.sha256(
            zero_slot + binding_trailer(slot_number)
        ).hexdigest()
        if modeled != direct or modeled != EXPECTED_ZERO_SLOT_DIGESTS[slot_number]:
            raise Sha256PrototypeError(
                f"profile-1 all-zero vector mismatch for slot {slot_number}"
            )
        zero_vectors[str(slot_number)] = modeled

    pattern = bytes(index & 0xFF for index in range(SLOT_SIZE))
    patterned_vectors: dict[str, str] = {}
    for slot_number in range(1, 4):
        modeled = profile1_digest_model(pattern, slot_number).hex()
        direct = hashlib.sha256(
            pattern + binding_trailer(slot_number)
        ).hexdigest()
        if modeled != direct:
            raise Sha256PrototypeError(
                f"profile-1 patterned vector mismatch for slot {slot_number}"
            )
        patterned_vectors[str(slot_number)] = modeled

    return {
        "standard_vector_count": len(standard_messages),
        "profile_vector_count": 6,
        "all_zero": zero_vectors,
        "incrementing_pattern": patterned_vectors,
    }


def run_asar_syntax(asar_path: pathlib.Path = DEFAULT_ASAR_PATH) -> dict[str, object]:
    """Assemble the norom wrapper to a deleted private temporary binary."""

    asar_path = asar_path.resolve()
    if not asar_path.is_file():
        raise Sha256PrototypeError(f"Asar executable not found: {asar_path}")
    PRIVATE_TEMP_PARENT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="sha256_65816_syntax_",
        dir=PRIVATE_TEMP_PARENT,
    ) as temporary:
        output_path = pathlib.Path(temporary) / "syntax_probe.bin"
        result = subprocess.run(
            (
                str(asar_path),
                "--no-title-check",
                "--fix-checksum=off",
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
            raise Sha256PrototypeError(
                "Asar syntax assembly failed:\n"
                + result.stdout
                + result.stderr
            )
        assembled = output_path.read_bytes()
        if not assembled:
            raise Sha256PrototypeError("Asar syntax probe emitted no bytes")
        probe = {
            "asar_sha256": sha256(asar_path.read_bytes()),
            "assembled_size": len(assembled),
            "assembled_sha256": sha256(assembled),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    if output_path.exists():
        raise Sha256PrototypeError("private syntax probe was not deleted")
    return probe


def validate(asar_path: pathlib.Path | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "evidence": "source-only-host-model",
        "source": validate_source_contract(),
        "vectors": verify_vectors(),
    }
    if asar_path is not None:
        result["asar_syntax"] = run_asar_syntax(asar_path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--asar",
        type=pathlib.Path,
        help="optional Asar executable for a private temporary norom probe",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(validate(args.asar), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
