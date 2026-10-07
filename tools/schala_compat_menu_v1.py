"""Bounded seven-site compatibility relocation for a private menu experiment.

This defines operand substitutions, not ownership of WRAM or a playable PC07.
The observer must prepare the full compatibility copy after native loading.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-compat-menu-v1"
DEFAULT_ROM = ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc"
ROM_SIZE = 0x400000
ROM_SHA256 = "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
OLD_START, NEW_START, BLOCK_SIZE = 0x2830, 0x2CA0, 0x50
DELTA = NEW_START - OLD_START
FRONT_GUARD = (0x2C9C, 4)
REAR_GUARD = (0x2CF0, 16)
MARKER = bytes((19 + 73 * i) & 255 for i in range(BLOCK_SIZE))
PREPARATION_PC = 0xC2E65B

# File offsets, complete instruction preimages, complete replacement witnesses.
# The builder writes only bytes +1/+2, never the instruction opcode.
PATCHES = (
    (0x3FF86D, bytes.fromhex("bd3728"), bytes.fromhex("bda72c")),
    (0x3FF9A2, bytes.fromhex("393728"), bytes.fromhex("39a72c")),
    (0x0282E4, bytes.fromhex("9c5728"), bytes.fromhex("9cc72c")),
    (0x0282E7, bytes.fromhex("a25728"), bytes.fromhex("a2c72c")),
    (0x0282EA, bytes.fromhex("a05928"), bytes.fromhex("a0c92c")),
    (0x02830E, bytes.fromhex("99a927"), bytes.fromhex("99192c")),
    (0x02B9AF, bytes.fromhex("a25728"), bytes.fromhex("a2c72c")),
)
OPERAND_PATCHES = tuple((start + 1, old[1:], new[1:]) for start, old, new in PATCHES)
SITE_ROLES = (
    "learned-mask read; derived mirror at 7E7F00+X stays in place",
    "rock prerequisite learned-mask AND; its temporary D0400 remains unchanged",
    "16-bit STZ of the first two relocated rock flags",
    "rock-clear MVN source pointer",
    "rock-clear MVN destination pointer",
    "rock-item-indexed STA; item AE..B2 maps to relocated 2CC7..2CCB",
    "five-byte relocated rock source copied to the existing 7E7F20 mirror",
)
UNCHANGED_WITNESSES = (
    (0x028319, bytes.fromhex("c93028"), "exclusive seven-record limit, not a compatibility base"),
    (0x0282F0, bytes.fromhex("547e7e"), "three-byte overlapping rock-clear MVN"),
    (0x02B9B7, bytes.fromhex("547e7e"), "five-byte rock mirror MVN"),
    (0x02E657, bytes.fromhex("22a3faff"), "native load caller remains unchanged"),
    (0x02E65B, bytes.fromhex("8037"), "observer preparation before native post-load BRA"),
)
PINNED_SOURCES = {
    "references/ct_disassembly/bank_C2.asm": "d96c0d9707d9150dbdb3ad7d995f7ae135e87ebb6329691cab2eb86447611032",
    "references/ct_disassembly/bank_FF.asm": "18f30c2a4f547722f30934bde43eb6a638d9467aa064e21340aa2065ab71829e",
    "tools/validate_rom_write_intents.py": "8bc61538b20da7a316048326059fe71de685264355a4db3410256cf6aee4369b",
    "tools/schala_rom_scaffold.py": "a517ad5c9d5a1f6b19a3050dfcc4903e2e177abe685ecaf78a60ca6884a9ed4a",
}
SOURCE_SPANS = (
    (0x3FF813, 325, "b149ce824dde99ffe689f087c1640c22deb23f1c32f42e044c0adfebd685efd3"),
    (0x3FF958, 99, "b2b30c3c0b0918a05bea0e8c78478af1063f47c691487617bc5d8830883f6c67"),
    (0x0282E1, 63, "5a6e82f4fbedc8fcfdfc53931a24296026f3463b43402735f6bf08a205ab02b9"),
    (0x02B9AB, 15, "26f7233592be91ad098c836dc083443b3e1400d4eabff7a95a246fc1194fa8b0"),
    (0x0282B2, 47, "eddad602745fddcc1085a9432acb7570be4d92bcc027aed977dc2b9d05b90ffb"),
    (0x02834D, 56, "47a27f1f264f2543a8f368662978ff8e7ceb6094f24c9b69eff91bd034bf5061"),
    (0x029973, 4, "d5d969e2af75ec1a8bacf46568176606ca1881e7e773de47ffa5fa39a363361b"),
)
BUNDLE_FILES = (
    "tools/schala_compat_menu_v1.py", "tools/build_schala_compat_menu_v1.py",
    "tests/test_schala_compat_menu_v1.py", *PINNED_SOURCES,
)


class ContractError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def private_path(path: Path, *, must_not_exist: bool = False) -> Path:
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve()
    private = (ROOT / "private").resolve()
    require(resolved.is_relative_to(private) and resolved != private, "output must remain below private/")
    require(not candidate.is_symlink(), "symlink output refused")
    if must_not_exist:
        require(not resolved.exists(), "existing output refused")
    return resolved


def source_contract(rom: bytes) -> dict:
    require(type(rom) is bytes and len(rom) == ROM_SIZE and sha256(rom) == ROM_SHA256,
            "canonical ROM identity mismatch")
    for path, digest in PINNED_SOURCES.items():
        require(sha256((ROOT / path).read_bytes()) == digest, "source drift: " + path)
    require(DELTA == 0x470 and len(PATCHES) == 7 and len(OPERAND_PATCHES) == 7,
            "relocation shape drift")
    for start, size, digest in SOURCE_SPANS:
        require(sha256(rom[start:start + size]) == digest, "menu source-span drift")
    sites = []
    for (start, old, new), role in zip(PATCHES, SITE_ROLES):
        require(len(old) == len(new) == 3 and old[0] == new[0], "instruction shape/opcode drift")
        require(rom[start:start + 3] == old, "instruction preimage drift")
        require(int.from_bytes(new[1:], "little") - int.from_bytes(old[1:], "little") == DELTA,
                "operand must be exact compatibility delta")
        require(all(a != b for a, b in zip(old[1:], new[1:])), "expected fourteen changed operand bytes")
        sites.append({"pc": start | 0xC00000, "file_start": start, "instruction_size": 3,
                      "preimage_hex": old.hex(), "replacement_hex": new.hex(),
                      "operand_file_start": start + 1, "operand_size": 2, "role": role})
    for start, original, _role in UNCHANGED_WITNESSES:
        require(rom[start:start + len(original)] == original, "unchanged instruction witness drift")
    require(0x27A9 + DELTA + 0xAE == NEW_START + 0x27 and
            0x27A9 + DELTA + 0xB2 == NEW_START + 0x2B, "indexed rock destination relation")
    return {
        "schema": SCHEMA, "evidence": "verified-static", "source_size": ROM_SIZE,
        "source_sha256": ROM_SHA256, "pinned_sources": PINNED_SOURCES,
        "sites": sites, "changed_operand_bytes": 14,
        "source_spans": [{"file_start": start, "size": size, "sha256": digest}
                         for start, size, digest in SOURCE_SPANS],
        "unchanged_witnesses": [{"file_start": start, "size": len(data), "sha256": sha256(data), "role": role}
                                for start, data, role in UNCHANGED_WITNESSES],
        "preparation_pc": PREPARATION_PC, "old_wram_start": 0x7E0000 + OLD_START,
        "candidate_wram_start": 0x7E0000 + NEW_START, "block_size": BLOCK_SIZE,
        "marker_sha256": sha256(MARKER), "requires_observer_preparation": True,
        "preparation": "after native load, copy all 80 original compatibility bytes to the zero candidate, then mark the old span; PC07 remains absent",
        "production_approved": False, "playable_pc07": False, "wram_ownership_proved": False,
        "header_checksum_unchanged": True,
        "scope": "one predeclared field/menu/Tech/field path; no battle, event grant, persistence, reset, or attract coverage",
        "mirrors_unchanged": ["7E7F00-7E7F24 learned/availability mirror", "7E04A4-7E04A8 rock eligibility", "7E7F20-7E7F24 Tech-page rock mirror"],
    }


def bundle_identity() -> dict:
    rows = [{"path": path, "bytes": (ROOT / path).stat().st_size,
             "sha256": sha256((ROOT / path).read_bytes())} for path in BUNDLE_FILES]
    payload = "".join(row["path"] + "\0" + row["sha256"] + "\n" for row in rows).encode("utf-8")
    return {"sha256": sha256(payload), "sources": rows}
