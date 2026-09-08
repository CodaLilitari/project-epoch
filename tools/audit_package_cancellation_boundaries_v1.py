"""Read-only, canonical-ROM-pinned audit of package refusal boundaries.

This is a reviewed static contract, not a disassembler or a game patch. It
checks the named control-flow edges and source spans that support the linked
cancellation design. It emits metadata only and writes no files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROM_SHA256 = "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
ROM_SIZE = 0x400000
SOURCE_REVISION = "eeae27acdb6565e96d1d796a3d60792c250c0aa1"

# Half-open CPU ranges. Labels are reviewer interpretations; hashes do not
# automatically derive semantics. No canonical byte payload is distributed.
SPANS = (
    ("queued-tech-preparation", 0xC1BB49, 0xC1BBD4, "4449dcbfa74ed8d603426f98e639b727a9be43608f1f9b3a88f2947c19ba5b8b"),
    ("prepare-charge-and-commit", 0xC1BBD4, 0xC1BC21, "8b3c37b61d5c6455f6bb01bd1befcd18337bd557ff54c363aa3de55f1c2b5570"),
    ("shared-success-failure-tail", 0xC1BC4A, 0xC1BC60, "2258622ba95551f41347b852f03148795064fb55c5932ae7b92b40f3fa6e4f70"),
    ("queue-and-partner-release", 0xC1BCF8, 0xC1BD6F, "6ce9e5574a0c6892a773ed1da81b03069c5ba47c68cb9b53e257eac9830c1aab"),
    ("participant-atb-finalizer", 0xC1BDB3, 0xC1BF46, "b3281d8212fb9d53d70068adff23d3281d86defa936fc07174fb07c79f4c15bc"),
    ("effect-preparation-wrapper", 0xC1BF79, 0xC1BF81, "2bf3698eedf41dbd69881491d760c0be9c3f01306442fd1e8b02e427cc6f18a9"),
    ("animation-and-result-commit-wrapper", 0xC1AC57, 0xC1AC5E, "d46f35d4a2da30eb6ba1b9e286d34b944fb853ee0ec9b5eedc8fcc7742122499"),
    ("result-commit-wrapper", 0xC1AC85, 0xC1AC89, "53804b9808e9f29231fa2f9c58ec92413ae5223679b3730f1678e89bbaac9cd2"),
    ("animation-service-4-wrapper", 0xC1BFA4, 0xC1BFAA, "922c4c8dff971adfd1a66a5a58c1125e5432cefa9b6b4fb25d34c106b5396a1c"),
    ("direct-participant-mp-deductions", 0xC1CC71, 0xC1CCCB, "a244c0b228a6f66df81db5c4fb32bf3c98d9c0d2c9f7e98193264648ac0d93bc"),
    ("participant-and-mp-validation", 0xC1D523, 0xC1D584, "ae9d9c2c8a0d1357665b898c7883a3c2c720479a213582e5d0e8ee725e86e5bc"),
    ("pending-hp-result-write", 0xC1EC7F, 0xC1ECA3, "4fd8fb28635325d22bd8c0dae9a942bfa420ee78b9e0b2f8bf464555fe35004c"),
    ("animation-phase-setup", 0xC14058, 0xC140B0, "fd8b1591cbdf8250416d0e64aa21ae8e03e79b776f0f7878183c6f98269d3943"),
    ("animation-waits-and-cleanup", 0xC140B0, 0xC141BE, "1ad3a83e7d9eced0d19bc50e08c386d453e84e91e4f212c0b7a2c20883d0e4e9"),
    ("animation-work-reset", 0xCCF06B, 0xCCF102, "80831e2419fc9425538ac36ddb83d979266a158a392ecba1e0bc6e009a1788ae"),
    ("scene-latch-owner", 0xCD1609, 0xCD1654, "dce62d3d48a939537e1f9976e6177b9fda6f39e9076b72c4f4fc0e2af798fca9"),
    ("stop-and-sync-handlers", 0xC14CF0, 0xC14D04, "5e3e65e7fc683da6fa456fbe499b2cab80825745a86db42c2f5b3ec82aa7cc7c"),
    ("type-zero-rts", 0xC1475A, 0xC1475B, "8d33f520a3c4cef80d2453aef81b612bfe1cb44c8b2025630ad38662763f13d3"),
    ("service-dispatch-and-table", 0xC10045, 0xC10065, "0ac26cab8ecb85df3b1478299f8e6a719847011892ca2d7bb74da7cbefeb9097"),
)

NEAR_CALLS = (
    (0xC1BB88, 0xC1C1DD), (0xC1BBD4, 0xC1BF79),
    (0xC1BF7D, 0xC1D523), (0xC1D573, 0xC1D74F),
    (0xC1BC01, 0xC1CC71), (0xC1BC0E, 0xC1CC71),
    (0xC1BC1B, 0xC1CC71), (0xC1BC1E, 0xC1AC57),
    (0xC1AC57, 0xC1BFA4), (0xC1AC5A, 0xC1AC85),
    (0xC1AC85, 0xC1EC7F), (0xC1BFA6, 0xC10003),
    (0xC1BC5A, 0xC1BDB3), (0xC140AD, 0xC14310),
    (0xC140CB, 0xC14BBE),
)
NEAR_JUMPS = ((0xC1BB90, 0xC1BC5A), (0xC1BC5D, 0xC1BCF8))
BRANCHES = (
    (0xC1BB8E, "BEQ", 0xC1BB93),
    (0xC1BBDA, "BNE", 0xC1BC5A),
    (0xC1BBDF, "BNE", 0xC1BC5A),
    (0xC1BC4F, "BCC", 0xC1BC56),
    (0xC140D1, "BEQ", 0xC140B0),
    (0xC140EA, "BNE", 0xC140E1),
)
ABSOLUTE_WRITES = (
    (0xC1CC8C, "STA", 0x5E34),
    (0xC1CCA9, "STA", 0x5EB4),
    (0xC1CCC2, "STA", 0x5F34),
    (0xCCF0E9, "STZ", 0x9876),
    (0xCD164D, "STZ", 0x5D9B),
    (0xC14D00, "INC", 0x9876),
)


def audit(rom: bytes) -> dict:
    digest = hashlib.sha256(rom).hexdigest()
    if len(rom) != ROM_SIZE or digest != ROM_SHA256:
        raise ValueError("canonical US Rev0 ROM identity required")

    def at(address: int, size: int) -> bytes:
        offset = address & 0x3FFFFF
        return rom[offset : offset + size]

    spans = []
    for role, start, end, expected in SPANS:
        actual = hashlib.sha256(at(start, end - start)).hexdigest()
        if actual != expected:
            raise ValueError(f"pinned span mismatch: {role}")
        spans.append({"role": role, "cpu_start": f"{start:06X}",
                      "cpu_end_exclusive": f"{end:06X}", "size": end - start,
                      "sha256": actual})

    checks = []

    def check(address: int, instruction: str, target: int, opcode: int) -> None:
        data = at(address, 3)
        actual_target = (address & 0xFF0000) | int.from_bytes(data[1:], "little")
        if data[0] != opcode or actual_target != target:
            raise ValueError(f"{instruction} target mismatch at {address:06X}")
        checks.append({"address": f"{address:06X}", "instruction": instruction,
                       "target": f"{target:06X}"})

    for address, target in NEAR_CALLS:
        check(address, "JSR", target, 0x20)
    for address, target in NEAR_JUMPS:
        check(address, "JMP", target, 0x4C)
    for address, mnemonic, target in BRANCHES:
        opcode = {"BEQ": 0xF0, "BNE": 0xD0, "BCC": 0x90}[mnemonic]
        data = at(address, 2)
        destination = (address & 0xFF0000) | ((address + 2 + int.from_bytes(data[1:], "little", signed=True)) & 0xFFFF)
        if data[0] != opcode or destination != target:
            raise ValueError(f"branch mismatch at {address:06X}")
        checks.append({"address": f"{address:06X}", "instruction": mnemonic,
                       "target": f"{target:06X}"})
    for address, mnemonic, operand in ABSOLUTE_WRITES:
        data = at(address, 3)
        if data[0] != {"STA": 0x8D, "STZ": 0x9C, "INC": 0xEE}[mnemonic] or int.from_bytes(data[1:], "little") != operand:
            raise ValueError(f"write operand mismatch at {address:06X}")
        checks.append({"address": f"{address:06X}", "instruction": mnemonic,
                       "absolute_operand": f"{operand:04X}"})

    # A successful queued Tech's result-table clear returns straight into the
    # same finalization tail used by failure branches. It is not a failure-only
    # routine. A long call's width is four, so BC56 + 4 == BC5A.
    data = at(0xC1BC56, 4)
    if data[0] != 0x22 or int.from_bytes(data[1:], "little") != 0xFDACEE:
        raise ValueError("successful result-clear long call mismatch")
    checks.append({"address": "C1BC56", "instruction": "JSL", "target": "FDACEE",
                   "return_continuation": "C1BC5A"})
    if at(0xC1475A, 1)[0] != 0x60:
        raise ValueError("type-zero near return mismatch")
    checks.append({"address": "C1475A", "instruction": "RTS"})
    if int.from_bytes(at(0xC10051 + 4 * 2, 2), "little") != 0x4058:
        raise ValueError("service-four vector mismatch")
    checks.append({"address": "C10059", "table_entry": "service 4", "target": "C14058"})

    return {
        "schema": "project-epoch-package-cancellation-boundaries-v1",
        "evidence_level": "verified-static",
        "scope": "reviewer-named canonical spans and selected control-flow/write assertions",
        "limitations": ["not a complete control-flow closure", "not runtime cancellation evidence",
                        "no hook, scratch, allocation, or production package binding approved",
                        "semantic labels are reviewed interpretations, not derived from hashes"],
        "rom": {"size": len(rom), "sha256": digest},
        "navigation_source": {"repository": "https://github.com/dscotton/ct_disassembly",
                              "revision": SOURCE_REVISION,
                              "bank_C1_asm_sha256": "298ad8f0ef01097b1018e1cdd154a4e63d52b6debaa1d94dd85ecf2b8aaa15aa"},
        "spans": spans, "instruction_checks": checks,
        "span_count": len(spans), "instruction_check_count": len(checks),
        "conclusions": {
            "resolver_refusal_is_semantic_action_cancellation": False,
            "queued_tech_mp_calls_precede_animation": True,
            "normal_animation_return_reaches_pending_result_application": True,
            "successful_and_failed_queued_tech_paths_share_finalization": True,
            "proposed_pre_effect_check_boundary": "before C1BBD4; hypothesis pending caller and finalizer proof",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=Path(__file__).resolve().parents[1] / "private/input/rom_archive/Chrono Trigger (USA).sfc")
    args = parser.parse_args()
    print(json.dumps(audit(args.rom.read_bytes()), indent=2))


if __name__ == "__main__":
    main()
